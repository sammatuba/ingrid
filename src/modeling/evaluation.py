"""Rolling-origin evaluation, aligned scoring and the private report.

Pipeline for one evaluation call
================================
1. Parse/validate the synthetic input (one entity, one unit, isolated history
   and truth partitions).
2. For each explicit origin, build the as-of context: history rows with
   ``timestamp <= origin`` and known ``availability <= origin``.  Unknown and
   late rows are counted with reasons; future rows are never shown.
3. Ask every provider to predict.  Provider failures and malformed output are
   preserved as explicit excluded origins.
4. Find complete-horizon truth for the target times ``origin + lead*step``.
5. Score each model only on the intersection of origins where truth is complete
   and **all** compared models succeeded, so no model gains a different
   denominator.  MAE/RMSE are reported overall and per lead on the same pairs.

The report is an immutable, tuple-backed structure with an explicit
JSON-compatible ``to_dict``/``to_json``.  It is never written to disk here and
does not reuse the shared artifact envelope.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import math
from typing import Sequence

from .errors import (
    INVALID_PROVIDER,
    INVALID_TYPE,
    INVALID_VALUE,
    MALFORMED_PREDICTION,
    MESSAGES,
    MISSING_TRUTH,
    ModelingError,
    NON_FINITE_PREDICTION,
    OVERFLOW,
    WRONG_HORIZON,
    issue,
)
from .providers import (
    BaselineProvider,
    ContextObservation,
    ContextView,
    Prediction,
    ProviderError,
    default_providers,
)
from .records import (
    EvaluationConfig,
    EvaluationInput,
    Partition,
    build_input,
    compute_input_digest,
    is_mapping,
    is_utf8_text,
    revalidate_input,
    safe_finite_float,
)


# --- report records -------------------------------------------------------


@dataclass(frozen=True)
class ContextCounts:
    """As-of history accounting for one origin."""

    total: int
    eligible: int
    excluded_unknown: int
    excluded_late: int
    excluded_future: int


@dataclass(frozen=True)
class Forecast:
    """One provider's result (or exclusion) at one origin."""

    model: str
    version: str
    ok: bool
    values: tuple[float, ...] | None
    used: tuple[ContextObservation, ...]
    exclusion_code: str | None
    exclusion_message: str | None


@dataclass(frozen=True)
class OriginReport:
    """Everything recorded for one forecast origin."""

    origin: datetime
    targets: tuple[datetime, ...]
    context: tuple[ContextObservation, ...]
    counts: ContextCounts
    forecasts: tuple[Forecast, ...]
    truth_ok: bool
    truth_code: str | None
    truth_values: tuple[float, ...] | None
    in_common: bool


@dataclass(frozen=True)
class ModelInfo:
    name: str
    version: str
    formula: str


@dataclass(frozen=True)
class ExclusionCount:
    code: str
    message: str
    count: int


@dataclass(frozen=True)
class LeadMetric:
    lead: int
    count: int
    mae: float | None
    rmse: float | None


@dataclass(frozen=True)
class ModelSummary:
    """Per-model raw exclusions plus metrics on the common scored set."""

    model: str
    version: str
    formula: str
    called_origins: int
    successful_origins: int
    exclusions: tuple[ExclusionCount, ...]
    scored_origins: int
    scored_pairs: int
    mae: float | None
    rmse: float | None
    per_lead: tuple[LeadMetric, ...]


@dataclass(frozen=True)
class EvaluationReport:
    """Immutable private evaluation report (not a shared artifact envelope)."""

    synthetic: bool
    input_digest: str
    config: EvaluationConfig
    models: tuple[ModelInfo, ...]
    origins: tuple[OriginReport, ...]
    summaries: tuple[ModelSummary, ...]
    common_origin_count: int
    total_origin_count: int
    coverage: float

    def to_dict(self) -> dict:
        return report_to_dict(self)

    def to_json(self) -> str:
        return json.dumps(
            report_to_dict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )


@dataclass(frozen=True)
class EvaluationOutcome:
    """Either a report or the structured errors that prevented one."""

    report: EvaluationReport | None
    errors: tuple[ModelingError, ...] = ()

    @property
    def ok(self) -> bool:
        return self.report is not None and not self.errors

    def codes(self) -> tuple[str, ...]:
        return tuple(error.code for error in self.errors)


# --- context --------------------------------------------------------------


def filter_context(
    config: EvaluationConfig, history: Partition, origin: datetime
) -> tuple[ContextView, ContextCounts]:
    """Return the eligible as-of history for one origin and its accounting."""
    eligible: list[ContextObservation] = []
    unknown = late = future = 0
    for row in history.observations:
        if row.timestamp > origin:
            future += 1
            continue
        if row.availability is None:
            unknown += 1
            continue
        if row.availability > origin:
            late += 1
            continue
        age = int((origin - row.timestamp) // config.step)
        eligible.append(
            ContextObservation(
                timestamp=row.timestamp,
                value=row.value,
                source_revision=row.source_revision,
                availability=row.availability,
                age_steps=age,
            )
        )
    counts = ContextCounts(
        total=len(history.observations),
        eligible=len(eligible),
        excluded_unknown=unknown,
        excluded_late=late,
        excluded_future=future,
    )
    view = ContextView(
        entity_type=config.entity_type,
        entity_id=config.entity_id,
        unit=config.unit,
        origin=origin,
        horizon=config.horizon,
        step=config.step,
        seasonal_lag=config.seasonal_lag,
        observations=tuple(eligible),
    )
    return view, counts


def _validated_prediction(
    prediction, horizon: int, eligible: dict
) -> tuple[tuple[float, ...] | None, tuple[ContextObservation, ...] | None, str | None]:
    """Validate a provider result, including the provenance it declares.

    Returns ``(values, used, code)``.  ``used`` maps every declared timestamp to
    the eligible context row; a timestamp that is mistyped, duplicated or absent
    from the eligible context is a malformed prediction, never silently dropped.
    """
    if not isinstance(prediction, Prediction):
        return None, None, MALFORMED_PREDICTION
    values = prediction.values
    if not isinstance(values, tuple):
        return None, None, MALFORMED_PREDICTION
    if len(values) != horizon:
        return None, None, WRONG_HORIZON
    checked: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, None, MALFORMED_PREDICTION
        converted = safe_finite_float(value)
        if converted is None:
            return None, None, NON_FINITE_PREDICTION
        checked.append(converted)
    if not isinstance(prediction.used_timestamps, tuple):
        return None, None, MALFORMED_PREDICTION
    used: list[ContextObservation] = []
    seen: set[datetime] = set()
    for moment in prediction.used_timestamps:
        if (
            not isinstance(moment, datetime)
            or moment.tzinfo is None
            or moment.utcoffset() is None
        ):
            return None, None, MALFORMED_PREDICTION
        if moment in seen:
            return None, None, MALFORMED_PREDICTION
        seen.add(moment)
        row = eligible.get(moment)
        if row is None:
            return None, None, MALFORMED_PREDICTION
        used.append(row)
    return tuple(checked), tuple(used), None


# --- metrics --------------------------------------------------------------


class _MetricOverflow(Exception):
    """Internal marker for a non-finite metric accumulation."""


def _metrics(pairs: Sequence[tuple[float, float]]) -> tuple[int, float | None, float | None]:
    if not pairs:
        return 0, None, None
    absolute = 0.0
    squared = 0.0
    for predicted, actual in pairs:
        difference = predicted - actual
        absolute += abs(difference)
        squared += difference * difference
    if not math.isfinite(absolute) or not math.isfinite(squared):
        raise _MetricOverflow()
    count = len(pairs)
    mae = absolute / count
    rmse = math.sqrt(squared / count)
    if not math.isfinite(mae) or not math.isfinite(rmse):
        raise _MetricOverflow()
    return count, mae, rmse


# --- provider handling ----------------------------------------------------


class _DefaultProviders:
    """Sentinel type: "the caller omitted ``providers``".

    ``None`` is a real, rejected value for the ``providers`` slot, so the
    default cannot be spelled as ``None``.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<default providers>"


_DEFAULT_PROVIDERS = _DefaultProviders()


def _coerce_providers(providers) -> tuple[object, ...]:
    """Normalize the provider argument into a tuple of candidates.

    The caller distinguishes an omitted argument (the module sentinel) from an
    explicit ``None`` before calling this.  This helper never returns ``None``,
    so the result cannot be mistaken for "use the default providers".
    """
    if isinstance(providers, (list, tuple)):
        return tuple(providers)
    if hasattr(providers, "predict"):
        return (providers,)
    return ()


def _validate_providers(providers: Sequence[object]) -> list[ModelingError]:
    errors: list[ModelingError] = []
    seen: set[str] = set()
    for index, provider in enumerate(providers):
        path = f"$.models[{index}]"
        name = getattr(provider, "name", None)
        version = getattr(provider, "version", None)
        formula = getattr(provider, "formula", None)
        if not isinstance(name, str) or not name or not is_utf8_text(name):
            errors.append(issue(INVALID_PROVIDER, f"{path}.name"))
            continue
        if not isinstance(version, str) or not version or not is_utf8_text(version):
            errors.append(issue(INVALID_PROVIDER, f"{path}.version"))
        if not isinstance(formula, str) or not formula or not is_utf8_text(formula):
            errors.append(issue(INVALID_PROVIDER, f"{path}.formula"))
        if not callable(getattr(provider, "predict", None)):
            errors.append(issue(INVALID_PROVIDER, f"{path}.predict"))
        if name in seen:
            errors.append(issue(INVALID_VALUE, "$.models"))
        seen.add(name)
    return errors


# --- evaluation -----------------------------------------------------------


def _evaluate(input_: EvaluationInput, providers: Sequence[BaselineProvider]) -> EvaluationReport:
    config = input_.config
    truth_index = {row.timestamp: row.value for row in input_.truth.observations}

    staged: list[tuple[datetime, tuple[datetime, ...], ContextView, ContextCounts, tuple[Forecast, ...], bool, tuple[float, ...] | None]] = []
    for origin in config.origins:
        context, counts = filter_context(config, input_.history, origin)
        eligible_by_timestamp = {row.timestamp: row for row in context.observations}
        forecasts: list[Forecast] = []
        for provider in providers:
            try:
                prediction = provider.predict(context)
            except ProviderError as exc:
                forecasts.append(
                    Forecast(provider.name, provider.version, False, None, (), exc.code, exc.error.message)
                )
                continue
            values, used, code = _validated_prediction(
                prediction, config.horizon, eligible_by_timestamp
            )
            if code is not None:
                forecasts.append(
                    Forecast(provider.name, provider.version, False, None, (), code, MESSAGES[code])
                )
                continue
            forecasts.append(
                Forecast(provider.name, provider.version, True, values, used, None, None)
            )

        targets = tuple(origin + config.step * lead for lead in range(1, config.horizon + 1))
        truth_values: list[float] = []
        truth_ok = True
        for target in targets:
            if target in truth_index:
                truth_values.append(truth_index[target])
            else:
                truth_ok = False
                break
        staged.append(
            (
                origin,
                targets,
                context,
                counts,
                tuple(forecasts),
                truth_ok,
                tuple(truth_values) if truth_ok else None,
            )
        )

    common = [
        item
        for item in staged
        if item[5] and all(forecast.ok for forecast in item[4])
    ]

    origins: list[OriginReport] = []
    for origin, targets, context, counts, forecasts, truth_ok, truth_values in staged:
        origins.append(
            OriginReport(
                origin=origin,
                targets=targets,
                context=context.observations,
                counts=counts,
                forecasts=forecasts,
                truth_ok=truth_ok,
                truth_code=None if truth_ok else MISSING_TRUTH,
                truth_values=truth_values,
                in_common=(truth_ok and all(forecast.ok for forecast in forecasts)),
            )
        )

    summaries: list[ModelSummary] = []
    for index, provider in enumerate(providers):
        successful = sum(1 for item in staged if item[4][index].ok)
        exclusion_counter: Counter[str] = Counter()
        for item in staged:
            forecast = item[4][index]
            if not forecast.ok and forecast.exclusion_code is not None:
                exclusion_counter[forecast.exclusion_code] += 1
        exclusions = tuple(
            ExclusionCount(code=code, message=MESSAGES[code], count=count)
            for code, count in sorted(exclusion_counter.items())
        )

        overall_pairs: list[tuple[float, float]] = []
        per_lead_pairs: dict[int, list[tuple[float, float]]] = {
            lead: [] for lead in range(1, config.horizon + 1)
        }
        for item in common:
            forecast = item[4][index]
            assert forecast.values is not None and item[6] is not None
            for offset, lead in enumerate(range(1, config.horizon + 1)):
                pair = (forecast.values[offset], item[6][offset])
                overall_pairs.append(pair)
                per_lead_pairs[lead].append(pair)

        count, mae, rmse = _metrics(overall_pairs)
        per_lead = []
        for lead in range(1, config.horizon + 1):
            lead_count, lead_mae, lead_rmse = _metrics(per_lead_pairs[lead])
            per_lead.append(LeadMetric(lead, lead_count, lead_mae, lead_rmse))

        summaries.append(
            ModelSummary(
                model=provider.name,
                version=provider.version,
                formula=provider.formula,
                called_origins=len(staged),
                successful_origins=successful,
                exclusions=exclusions,
                scored_origins=len(common),
                scored_pairs=count,
                mae=mae,
                rmse=rmse,
                per_lead=tuple(per_lead),
            )
        )

    models = tuple(
        ModelInfo(provider.name, provider.version, provider.formula) for provider in providers
    )
    total = len(config.origins)
    coverage = len(common) / total if total else 0.0
    return EvaluationReport(
        synthetic=input_.synthetic,
        input_digest=compute_input_digest(
            config,
            input_.history,
            input_.truth,
            tuple((provider.name, provider.version) for provider in providers),
        ),
        config=config,
        models=models,
        origins=tuple(origins),
        summaries=tuple(summaries),
        common_origin_count=len(common),
        total_origin_count=total,
        coverage=coverage,
    )


def run_evaluation(source, providers=_DEFAULT_PROVIDERS) -> EvaluationOutcome:
    """Validate ``source`` and evaluate it against the bounded provider port.

    ``source`` may be an :class:`EvaluationInput` or an arbitrary mapping; a
    malformed shape yields structured errors rather than a ``TypeError``.

    ``providers`` is optional, not nullable: omitting it selects the default
    built-in comparison, while an explicit ``None`` is rejected with
    ``INVALID_PROVIDER``.  An unknown model name is therefore never silently
    replaced by the default set.  Only expected :class:`ProviderError` failures
    are converted to exclusions; unexpected provider exceptions propagate as
    programmer error.
    """
    if isinstance(source, EvaluationInput):
        rebuilt = revalidate_input(source)
        if not rebuilt.ok:
            return EvaluationOutcome(None, rebuilt.errors)
        input_ = rebuilt.value
    elif is_mapping(source):
        built = build_input(source)
        if not built.ok:
            return EvaluationOutcome(None, built.errors)
        input_ = built.value
    else:
        return EvaluationOutcome(None, (issue(INVALID_TYPE, "$"),))

    if providers is _DEFAULT_PROVIDERS:
        providers = default_providers()
    elif providers is None:
        return EvaluationOutcome(None, (issue(INVALID_PROVIDER, "$.models"),))
    providers_tuple = _coerce_providers(providers)
    if not providers_tuple:
        if isinstance(providers, (list, tuple)):
            return EvaluationOutcome(None, (issue(INVALID_VALUE, "$.models"),))
        return EvaluationOutcome(None, (issue(INVALID_PROVIDER, "$.models"),))
    provider_errors = _validate_providers(providers_tuple)
    if provider_errors:
        return EvaluationOutcome(None, tuple(provider_errors))

    try:
        report = _evaluate(input_, providers_tuple)
    except _MetricOverflow:
        return EvaluationOutcome(None, (issue(OVERFLOW, "$.summaries"),))
    return EvaluationOutcome(report, ())


# --- serialization --------------------------------------------------------


def _context_payload(row: ContextObservation) -> dict:
    return row.as_dict()


def _forecast_payload(forecast: Forecast) -> dict:
    return {
        "model": forecast.model,
        "version": forecast.version,
        "ok": forecast.ok,
        "values": list(forecast.values) if forecast.values is not None else None,
        "used": [_context_payload(row) for row in forecast.used],
        "exclusion": (
            {"code": forecast.exclusion_code, "message": forecast.exclusion_message}
            if forecast.exclusion_code is not None
            else None
        ),
    }


def _origin_payload(origin: OriginReport) -> dict:
    return {
        "origin": origin.origin.isoformat(),
        "targets": [target.isoformat() for target in origin.targets],
        "leads": list(range(1, len(origin.targets) + 1)),
        "in_common": origin.in_common,
        "history_counts": {
            "total": origin.counts.total,
            "eligible": origin.counts.eligible,
            "excluded_unknown": origin.counts.excluded_unknown,
            "excluded_late": origin.counts.excluded_late,
            "excluded_future": origin.counts.excluded_future,
        },
        "context": [_context_payload(row) for row in origin.context],
        "forecasts": [_forecast_payload(forecast) for forecast in origin.forecasts],
        "truth": {
            "complete": origin.truth_ok,
            "exclusion_code": origin.truth_code,
            "values": list(origin.truth_values) if origin.truth_values is not None else None,
        },
    }


def _summary_payload(summary: ModelSummary) -> dict:
    return {
        "model": summary.model,
        "version": summary.version,
        "formula": summary.formula,
        "called_origins": summary.called_origins,
        "successful_origins": summary.successful_origins,
        "exclusions": [
            {"code": item.code, "message": item.message, "count": item.count}
            for item in summary.exclusions
        ],
        "scored_origins": summary.scored_origins,
        "scored_pairs": summary.scored_pairs,
        "mae": summary.mae,
        "rmse": summary.rmse,
        "per_lead": [
            {"lead": item.lead, "count": item.count, "mae": item.mae, "rmse": item.rmse}
            for item in summary.per_lead
        ],
    }


def report_to_dict(report: EvaluationReport) -> dict:
    """Explicit pure JSON-compatible dict for the private report."""
    return {
        "synthetic": report.synthetic,
        "input_digest": report.input_digest,
        "config": report.config.as_dict(),
        "models": [
            {"name": model.name, "version": model.version, "formula": model.formula}
            for model in report.models
        ],
        "metric_formulas": {
            "mae": "sum(abs(predicted - actual)) / n",
            "rmse": "sqrt(sum((predicted - actual) ** 2) / n)",
            "scope": "common scored origins only; identical pairs for every model",
        },
        "coverage": {
            "common_origins": report.common_origin_count,
            "total_origins": report.total_origin_count,
            "fraction": report.coverage,
        },
        "origins": [_origin_payload(origin) for origin in report.origins],
        "summaries": [_summary_payload(summary) for summary in report.summaries],
    }


__all__ = [
    "ContextCounts",
    "EvaluationOutcome",
    "EvaluationReport",
    "ExclusionCount",
    "Forecast",
    "LeadMetric",
    "ModelInfo",
    "ModelSummary",
    "OriginReport",
    "filter_context",
    "report_to_dict",
    "run_evaluation",
]
