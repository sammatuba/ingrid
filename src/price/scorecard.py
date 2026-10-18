"""The rolling-origin scorecard: bias, MAE, RMSE and pinball at p10/p50/p90.

One run per (series, horizon) walks the candidate origins in chronological
order. At each origin the window is checked before anything is scored:

* every target hour must be present and the window must carry every interval of
  the billing clock — otherwise the origin is excluded (``window_incomplete`` or
  ``window_short``) and nothing is filled in to complete it;
* an origin whose own billing month is marked short by :func:`derive_marks` is
  excluded as ``month_short``: a marked month never supplies a scored origin,
  even where the target window itself happens to be complete;
* every compared baseline must produce a forecast from rows that ended at or
  before the cutoff — otherwise the origin is excluded under the baseline's own
  code, so no baseline is ever scored on a different set of origins;
* a window that mixes administered-pricing hours with market hours
  (``slice_mixed``) is counted and reaches neither slice;
* the quantile fan below must have enough earlier errors (``no_error_fan``).

Scoring happens only on the intersection of those conditions, so every baseline
in a (series, horizon, slice) group has the same denominator.

Quantile forecasts
==================
The baselines are point forecasts, so the p10 and p90 arms come from the
baseline's own earlier residuals, never from the window being scored: the signed
residual ``realized − forecast`` of a settled origin joins an expanding fan once
its window ended at least one embargo before the current origin, and the raw arms
are that fan's 10 % and 90 % quantiles as offsets from the point forecast, so a
residual that settled above the forecast lifts both arms toward it. A fan with
fewer than ``min_fan_samples`` residuals excludes the origin: an interval nobody
could have computed is not scored.

The three reported quantiles of one origin are the **sorted** triple
``(point + q10, point, point + q90)`` (:func:`ordered_quantiles`). Where the
fan's residual quantiles both sit on one side of zero the raw triple would cross
— ``p10 > p50`` or ``p50 > p90`` — and a crossed triple describes no single
distribution, so the reported values are put in ascending order (the
rearrangement rule) and the record carries that rule verbatim in
``quantile_rule``. In the ordinary case the fan's 10 % and 90 % quantiles
straddle zero, the point forecast is the middle value, and pinball at p50 is
exactly half the MAE; where an arm does cross, the middle value is the nearer
arm and that identity holds only over the origins that do not cross.

``bias``, ``mae`` and ``rmse`` score the **unadjusted point forecast**, never a
quantile of the fan: the fan corrects no bias, the point forecast is the
baseline's own value, and every record says so in ``quantile_rule``.

The record is a deterministic JSON document: the same exported bytes and the
same configuration give the same bytes, and the run's content digest is the
SHA-256 of those bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
from bisect import insort
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

from .baselines import (
    HORIZONS,
    Baseline,
    BaselineError,
    SeasonalAverageByBillingMonth,
    Window,
    aggregate,
    candidate_origins,
    default_baselines,
    history_cutoff,
    window_for,
)
from .series import (
    ADMINISTERED_PRICING_MONTHS,
    INTERVALS_PER_DAY,
    Marks,
    Series,
    billing_month_label,
    billing_month_of,
    derive_marks,
)

VERSION = "price-2.3"
KIND = "price-baseline-scorecard"
METRIC_DECIMALS = 6
VALUE_DECIMALS = 4

MARKET = "market"
AP = "ap"
MIXED = "mixed"

QUANTILE_RULE = (
    "p10, p50 and p90 are one fan's three values reported in ascending order — the "
    "residual-adjusted arms and the point forecast, sorted — so the record never "
    "states p10 > p50 or p50 > p90; bias, MAE and RMSE are the unadjusted point "
    "forecast's own errors, never a quantile of the fan"
)


# --- metrics --------------------------------------------------------------


def quantile(ordered: Sequence[float], probability: float) -> float:
    """Linear interpolation between order statistics of an ascending sample.

    The definition is the usual one (``numpy``'s ``linear`` method): position
    ``q * (n - 1)`` read directly for a single sample, and interpolated between
    the two neighbouring order statistics otherwise.
    """
    if not ordered:
        raise ValueError("quantile of an empty sample")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability outside [0, 1]")
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def pinball(probability: float, realized: float, forecast: float) -> float:
    """The quantile (pinball) loss of one quantile forecast."""
    difference = realized - forecast
    if difference >= 0:
        return probability * difference
    return (1.0 - probability) * (-difference)


@dataclass(frozen=True)
class ScoredBand:
    """One scored origin's price band, as levels: the three values of one baseline.

    The record reports the band as the pinball losses of its three values and
    keeps the levels themselves out of its bytes. A consumer that needs the
    levels — IMPACT-1 prices a portfolio against the band — passes a
    ``band_sink`` to :func:`build_scorecard` and receives one row per scored
    (origin, baseline): exactly the triple :func:`ordered_quantiles` produced for
    that origin, beside the realized window mean and the point forecast. The sink
    changes no record byte; it is output only.
    """

    series: str
    kind: str
    horizon: str
    origin: str
    label: str
    slice: str
    baseline: str
    realized: float
    point: float
    p10: float
    p50: float
    p90: float


@dataclass(frozen=True)
class Metrics:
    """The scorecard row: the four required numbers and the sample size."""

    count: int
    bias: float | None = None
    mae: float | None = None
    rmse: float | None = None
    pinball_p10: float | None = None
    pinball_p50: float | None = None
    pinball_p90: float | None = None

    def to_dict(self) -> dict:
        rounded = {}
        for name in ("bias", "mae", "rmse", "pinball_p10", "pinball_p50", "pinball_p90"):
            value = getattr(self, name)
            rounded[name] = None if value is None else round(value, METRIC_DECIMALS)
        return {"count": self.count, **rounded}


def metrics_from(scored: Sequence[tuple[float, float, float, float, float]]) -> Metrics:
    """Metrics over ``(realized, point, p10, p50, p90)`` rows of one slice.

    ``bias``, ``mae`` and ``rmse`` score the unadjusted point forecast. The
    pinball losses score the reported quantiles, which the caller has already put
    in ascending order (:func:`ordered_quantiles`); in the ordinary case the
    middle value is the point forecast and ``pinball_p50`` is exactly half the
    MAE, but a crossed fan moves the middle value and the caller does not hide
    that.
    """
    if not scored:
        return Metrics(count=0)
    count = len(scored)
    errors = [point - realized for realized, point, _, _, _ in scored]
    bias = sum(errors) / count
    mae = sum(abs(error) for error in errors) / count
    rmse = math.sqrt(sum(error * error for error in errors) / count)
    return Metrics(
        count=count,
        bias=bias,
        mae=mae,
        rmse=rmse,
        pinball_p10=sum(pinball(0.10, r, p10) for r, _, p10, _, _ in scored) / count,
        pinball_p50=sum(pinball(0.50, r, p50) for r, _, _, p50, _ in scored) / count,
        pinball_p90=sum(pinball(0.90, r, p90) for r, _, _, _, p90 in scored) / count,
    )


def ordered_quantiles(point: float, low: float, high: float) -> tuple[float, float, float]:
    """The three reported quantiles of one origin, ascending.

    ``point`` is the baseline's own value and ``low``/``high`` are the fan's 10 %
    and 90 % residual quantiles as offsets from it. Where both offsets share a
    sign the raw triple crosses the point forecast, and no distribution has
    ``p10 > p50`` or ``p50 > p90``; the reported triple is therefore the sorted
    one (the rearrangement rule), which is the smallest correction that keeps the
    record coherent. The point forecast is *not* forced into the middle: where the
    fan has crossed it, the middle value is the nearer arm, and the record states
    the rule (``quantile_rule``).
    """
    p10, p50, p90 = sorted((point + low, point, point + high))
    return p10, p50, p90


# --- the as-of quantile fan ----------------------------------------------


class ErrorFan:
    """Signed residuals (realized − forecast) of settled origins, released after the embargo.

    Residuals are added in the order the origins are scored (the window end never
    goes backwards), so a cursor releases one exactly when its window ended at
    least one embargo before the origin being forecast. Nothing in the fan comes
    from the origin being scored.
    """

    def __init__(self, embargo_hours: int) -> None:
        self._embargo = timedelta(hours=embargo_hours)
        self._pending: list[tuple[datetime, float]] = []
        self._cursor = 0
        self._ready: list[float] = []

    def add(self, window_end: datetime, error: float) -> None:
        self._pending.append((window_end, error))

    def release(self, origin_start: datetime) -> None:
        while self._cursor < len(self._pending):
            window_end, error = self._pending[self._cursor]
            if window_end + self._embargo > origin_start:
                break
            insort(self._ready, error)
            self._cursor += 1

    def __len__(self) -> int:
        return len(self._ready)

    def arms(self) -> tuple[float, float]:
        """The 10 % and 90 % residual quantiles, as offsets from the point forecast.

        These are the raw arms: they may share a sign, and the reported triple is
        the sorted one (:func:`ordered_quantiles`).
        """
        if not self._ready:
            raise BaselineError("NO_ERROR_FAN")
        return quantile(self._ready, 0.10), quantile(self._ready, 0.90)


# --- the scorecard record -------------------------------------------------


@dataclass(frozen=True)
class BaselineReport:
    """One baseline's exclusions and metrics inside one (series, horizon)."""

    name: str
    version: str
    formula: str
    unavailable: tuple[tuple[str, int], ...]
    slices: Mapping[str, Metrics]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "formula": self.formula,
            "unavailable": [{"code": code, "count": count} for code, count in self.unavailable],
            "slices": {key: value.to_dict() for key, value in self.slices.items()},
        }


@dataclass(frozen=True)
class HorizonReport:
    """One horizon of one series: what was scored and what was excluded."""

    horizon: str
    window_hours: tuple[int, ...]
    candidates: int
    scored: tuple[tuple[str, int], ...]
    excluded: tuple[tuple[str, int], ...]
    baselines: tuple[BaselineReport, ...]
    origin_columns: tuple[str, ...]
    origin_rows: tuple[tuple, ...]
    excluded_rows: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict:
        scored = dict(self.scored)
        return {
            "horizon": self.horizon,
            "window_hours": list(self.window_hours),
            "candidate_origins": self.candidates,
            "scored": scored,
            "excluded": [{"code": code, "count": count} for code, count in self.excluded],
            "baselines": [report.to_dict() for report in self.baselines],
            "origin_rows": {"columns": list(self.origin_columns),
                            "rows": [list(row) for row in self.origin_rows]},
            "excluded_rows": [list(row) for row in self.excluded_rows],
        }


@dataclass(frozen=True)
class SeriesReport:
    key: str
    kind: str
    label: str
    region: str
    source: str
    rows: int
    marks: Marks
    horizons: tuple[HorizonReport, ...]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "kind": self.kind,
            "label": self.label,
            "region": self.region,
            "source": self.source,
            "rows": self.rows,
            "marks": self.marks.to_dict(),
            "horizons": [horizon.to_dict() for horizon in self.horizons],
        }


@dataclass(frozen=True)
class Scorecard:
    """The whole record: configuration, inputs by digest, and every series."""

    version: str
    embargo_hours: int
    min_fan_samples: int
    baselines: tuple[dict, ...]
    inputs: tuple[dict, ...]
    series: tuple[SeriesReport, ...]

    def to_dict(self) -> dict:
        return {
            "kind": KIND,
            "version": self.version,
            "embargo_hours": self.embargo_hours,
            "min_fan_samples": self.min_fan_samples,
            "quantile_rule": QUANTILE_RULE,
            "baselines": [dict(entry) for entry in self.baselines],
            "inputs": [dict(entry) for entry in self.inputs],
            "series": [report.to_dict() for report in self.series],
        }

    def to_json(self) -> str:
        """Canonical JSON: sorted keys, compact separators, no non-finite floats."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)

    def content_digest(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


# --- the run --------------------------------------------------------------


def slice_of(series: Series, window: Window, marks: Marks) -> str:
    """Classify a window as market, administered pricing, or a mix of both.

    A series with per-hour pricing counts (the nodal export, carried through
    ``ap5``) classifies by intervals; the regional export carries no flag, so its
    classification uses the billing months recorded in the target contract.
    """
    rows = series.present(window.hours)
    if series.has_ap_flags:
        total = sum(row.intervals for row in rows)
        administered = sum(row.ap_intervals for row in rows)
        if administered == 0:
            return MARKET
        return AP if administered == total else MIXED
    states = set()
    for row in rows:
        if row.billing_month in marks.ap_all_months:
            states.add(AP)
        elif row.billing_month in marks.ap_mixed_months:
            states.add(MIXED)
        else:
            states.add(MARKET)
    if states == {AP}:
        return AP
    return MARKET if states == {MARKET} else MIXED


def build_scorecard(
    series_list: Sequence[Series],
    baselines: Sequence[Baseline] | None = None,
    horizons: Sequence[str] = HORIZONS,
    inputs: Sequence[Mapping[str, object]] = (),
    embargo_hours: int = 24,
    min_fan_samples: int = 12,
    administered: Sequence[tuple[str, str]] = ADMINISTERED_PRICING_MONTHS,
    band_sink: list[ScoredBand] | None = None,
) -> Scorecard:
    """Score every baseline on every series and horizon, excluding what cannot be scored.

    ``band_sink``, when given, is a list one :class:`ScoredBand` is appended to
    for every scored origin and baseline. It is a read-only output for consumers
    that need the band levels (IMPACT-1); the record built here is unaffected.
    """
    baselines = tuple(default_baselines() if baselines is None else baselines)
    for horizon in horizons:
        if horizon not in HORIZONS:
            raise BaselineError("UNKNOWN_HORIZON", str(horizon))
    series_reports = []
    for series in series_list:
        marks = derive_marks(series, administered)
        index = None
        for baseline in baselines:
            if isinstance(baseline, SeasonalAverageByBillingMonth):
                index = baseline.index_series(series)
                break
        horizon_reports = [
            _score_horizon(series, marks, baselines, horizon, index, embargo_hours,
                           min_fan_samples, band_sink)
            for horizon in horizons
        ]
        series_reports.append(
            SeriesReport(key=series.key, kind=series.kind, label=series.label,
                         region=series.region, source=series.source, rows=len(series.rows),
                         marks=marks, horizons=tuple(horizon_reports))
        )
    return Scorecard(
        version=VERSION,
        embargo_hours=embargo_hours,
        min_fan_samples=min_fan_samples,
        baselines=tuple({"name": baseline.name, "version": baseline.version,
                         "formula": baseline.formula} for baseline in baselines),
        inputs=tuple(dict(entry) for entry in inputs),
        series=tuple(series_reports),
    )


def _score_horizon(
    series: Series,
    marks: Marks,
    baselines: Sequence[Baseline],
    horizon: str,
    index: Mapping[tuple[str, int], Sequence[float]] | None,
    embargo_hours: int,
    min_fan_samples: int,
    band_sink: list[ScoredBand] | None = None,
) -> HorizonReport:
    candidates = candidate_origins(horizon, series.first_day, series.last_day)
    short_months = frozenset(marks.short_months)
    fans = {baseline.name: ErrorFan(embargo_hours) for baseline in baselines}
    unavailable: dict[str, Counter] = {baseline.name: Counter() for baseline in baselines}
    excluded: Counter = Counter()
    excluded_rows: list[tuple[str, str]] = []
    scored: dict[str, dict[str, list[tuple[float, float, float, float, float]]]] = {
        name: {baseline.name: [] for baseline in baselines} for name in (MARKET, AP)
    }
    origin_rows: list[tuple] = []
    window_hours: set[int] = set()

    for origin in candidates:
        window = window_for(horizon, origin)
        window_hours.add(len(window.hours))
        cutoff = history_cutoff(origin, embargo_hours)
        label = window.label()
        missing = series.missing_hours(window.hours)
        if missing:
            excluded["window_incomplete"] += 1
            excluded_rows.append((origin.isoformat(), "window_incomplete"))
            continue
        if series.intervals(window.hours) != INTERVALS_PER_DAY * window.days:
            excluded["window_short"] += 1
            excluded_rows.append((origin.isoformat(), "window_short"))
            continue
        if billing_month_label(*billing_month_of(origin)) in short_months:
            excluded["month_short"] += 1
            excluded_rows.append((origin.isoformat(), "month_short"))
            continue

        weights = tuple(row.intervals for row in series.present(window.hours))
        realized = series.window_mean(window.hours)
        slice_name = slice_of(series, window, marks)
        points: dict[str, float] = {}
        for baseline in baselines:
            try:
                forecast = baseline.forecast(series, window, cutoff, index=index)
            except BaselineError as error:
                unavailable[baseline.name][error.code] += 1
            else:
                points[baseline.name] = aggregate(forecast.values, weights)
        if len(points) != len(baselines):
            excluded["baseline_unavailable"] += 1
            excluded_rows.append((origin.isoformat(), "baseline_unavailable"))
            continue
        if slice_name == MIXED:
            excluded["slice_mixed"] += 1
            excluded_rows.append((origin.isoformat(), "slice_mixed"))
            continue

        # The settled residual of this origin joins the fan whether or not the fan
        # was wide enough to score it: the residual is knowable from the settled
        # window, and without this the first origins of a series could never
        # seed the fan that later origins score against.
        ready = {baseline.name: fans[baseline.name] for baseline in baselines}
        for fan in ready.values():
            fan.release(window.start)
        for baseline in baselines:
            fans[baseline.name].add(window.end, realized - points[baseline.name])
        if any(len(fan) < min_fan_samples for fan in ready.values()):
            excluded["no_error_fan"] += 1
            excluded_rows.append((origin.isoformat(), "no_error_fan"))
            continue

        arms = {baseline.name: ready[baseline.name].arms() for baseline in baselines}
        for baseline in baselines:
            name = baseline.name
            point = points[name]
            p10, p50, p90 = ordered_quantiles(point, *arms[name])
            scored[slice_name][name].append((realized, point, p10, p50, p90))
            if band_sink is not None:
                band_sink.append(ScoredBand(
                    series=series.key, kind=series.kind, horizon=horizon,
                    origin=origin.isoformat(), label=label, slice=slice_name,
                    baseline=name, realized=realized, point=point,
                    p10=p10, p50=p50, p90=p90,
                ))
        origin_rows.append((origin.isoformat(), label, slice_name, round(realized, VALUE_DECIMALS))
                           + tuple(round(points[baseline.name], VALUE_DECIMALS)
                                   for baseline in baselines))

    reports = []
    for baseline in baselines:
        reports.append(BaselineReport(
            name=baseline.name,
            version=baseline.version,
            formula=baseline.formula,
            unavailable=tuple(sorted(unavailable[baseline.name].items())),
            slices={
                name: metrics_from(scored[name][baseline.name]) for name in (MARKET, AP)
            },
        ))
    return HorizonReport(
        horizon=horizon,
        window_hours=tuple(sorted(window_hours)),
        candidates=len(candidates),
        scored=tuple(
            (name, len(scored[name][baselines[0].name])) for name in (MARKET, AP)
        ),
        excluded=tuple(sorted(excluded.items())),
        baselines=tuple(reports),
        origin_columns=("origin", "label", "slice", "realized")
                        + tuple(baseline.name for baseline in baselines),
        origin_rows=tuple(origin_rows),
        excluded_rows=tuple(excluded_rows),
    )


__all__ = [
    "AP",
    "ErrorFan",
    "MARKET",
    "METRIC_DECIMALS",
    "MIXED",
    "QUANTILE_RULE",
    "BaselineReport",
    "HorizonReport",
    "Metrics",
    "Scorecard",
    "ScoredBand",
    "SeriesReport",
    "build_scorecard",
    "metrics_from",
    "ordered_quantiles",
    "pinball",
    "quantile",
    "slice_of",
]
