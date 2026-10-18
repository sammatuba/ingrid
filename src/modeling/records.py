"""Immutable typed records and strict parsing for the M0 baseline harness.

Scope
=====
One entity and one unit per evaluation call.  History/context candidates and
evaluation truth are separate partitions.  Rows are explicit
``(timestamp, value, source_revision, availability|unknown_reason)`` records.

All collection-valued fields are tuples, so the frozen dataclasses are deeply
immutable (a frozen dataclass wrapping a list would not be).  Public
``build_*`` functions accept arbitrary mapping shapes and return structured
errors instead of raising ``TypeError``.

Only labeled synthetic input is accepted for this starter slice; real data
ingestion is a separate, unprovided contract.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math

from .errors import (
    BOOLEAN_AS_NUMBER,
    DUPLICATE_TIMESTAMP,
    INVALID_TIMESTAMP,
    INVALID_TYPE,
    INVALID_VALUE,
    MISSING_FIELD,
    MIXED_ENTITIES,
    MIXED_UNITS,
    ModelingError,
    ModelingValidationError,
    NAIVE_TIMESTAMP,
    NON_FINITE_NUMBER,
    ORIGIN_ORDER,
    REAL_INPUT_UNSUPPORTED,
    UNORDERED_TIMESTAMPS,
    issue,
)


# --- shallow helpers ------------------------------------------------------


def is_mapping(value) -> bool:
    return isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray))


def is_sequence(value) -> bool:
    return isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray))


def is_utf8_text(value) -> bool:
    """True for a string that encodes as valid UTF-8 (no lone surrogates).

    Canonical serialization and hashing require encodable text; a lone surrogate
    such as ``"\\ud800"`` otherwise fails later with ``UnicodeEncodeError``.
    """
    if not isinstance(value, str):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def safe_finite_float(value) -> float | None:
    """Return ``value`` as a finite float, or ``None`` when it cannot be one.

    Oversized integers (for example ``10**400``) raise ``OverflowError`` from
    ``float`` and are not representable; NaN, Infinity and non-numeric shapes
    also return ``None``.  This never raises for the numeric shapes accepted by
    :func:`parse_number`.
    """
    try:
        converted = float(value)
    except (OverflowError, ValueError, TypeError):
        return None
    if not math.isfinite(converted):
        return None
    return converted


def _as_tuple(value, path: str) -> tuple:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    raise ModelingValidationError(issue(INVALID_TYPE, path))


def _reject_unknown(obj: Mapping, allowed: frozenset, path: str, errors: list) -> None:
    for key in obj:
        if not isinstance(key, str) or key not in allowed:
            errors.append(issue(INVALID_TYPE, path))
            return


def _get_string(obj: Mapping, key: str, path: str, errors: list) -> str | None:
    field_path = f"{path}.{key}"
    if key not in obj:
        errors.append(issue(MISSING_FIELD, field_path))
        return None
    value = obj[key]
    if not isinstance(value, str):
        errors.append(issue(INVALID_TYPE, field_path))
        return None
    if not value:
        errors.append(issue(INVALID_VALUE, field_path))
        return None
    if not is_utf8_text(value):
        errors.append(issue(INVALID_VALUE, field_path))
        return None
    return value


def parse_timestamp(value, path: str, errors: list) -> datetime | None:
    """Parse an offset-bearing datetime or ISO-8601 string."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            errors.append(issue(INVALID_TIMESTAMP, path))
            return None
    else:
        errors.append(issue(INVALID_TIMESTAMP, path))
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(issue(NAIVE_TIMESTAMP, path))
        return None
    return parsed


def parse_number(value, path: str, errors: list) -> float | None:
    """Parse a finite real number; booleans are not numbers."""
    if isinstance(value, bool):
        errors.append(issue(BOOLEAN_AS_NUMBER, path))
        return None
    if not isinstance(value, (int, float)):
        errors.append(issue(INVALID_TYPE, path))
        return None
    converted = safe_finite_float(value)
    if converted is None:
        errors.append(issue(NON_FINITE_NUMBER, path))
        return None
    return converted


def parse_positive_int(value, path: str, errors: list) -> int | None:
    if isinstance(value, bool):
        errors.append(issue(BOOLEAN_AS_NUMBER, path))
        return None
    if not isinstance(value, int):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if value <= 0:
        errors.append(issue(INVALID_VALUE, path))
        return None
    return value


def parse_step(value, path: str, errors: list) -> timedelta | None:
    """Parse a positive step duration: a ``timedelta`` or positive seconds."""
    if isinstance(value, timedelta):
        if value <= timedelta(0):
            errors.append(issue(INVALID_VALUE, path))
            return None
        return value
    seconds = parse_number(value, path, errors)
    if seconds is None:
        return None
    if not seconds > 0:
        errors.append(issue(INVALID_VALUE, path))
        return None
    try:
        step = timedelta(seconds=seconds)
    except OverflowError:
        errors.append(issue(INVALID_VALUE, path))
        return None
    if step <= timedelta(0):
        # A small positive float rounds to a zero timedelta; a zero step would
        # later divide by zero.
        errors.append(issue(INVALID_VALUE, path))
        return None
    return step


# --- records --------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    """One explicit synthetic history/truth row."""

    timestamp: datetime
    value: float
    source_revision: str
    availability: datetime | None = None
    unknown_reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "source_revision": self.source_revision,
            "availability": self.availability.isoformat() if self.availability is not None else None,
            "unknown_reason": self.unknown_reason,
        }


@dataclass(frozen=True)
class Partition:
    """One entity/unit partition of observations (history or truth)."""

    entity_type: str
    entity_id: str
    unit: str
    observations: tuple[Observation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", _as_tuple(self.observations, "$.observations"))

    def as_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "unit": self.unit,
            "observations": [row.as_dict() for row in self.observations],
        }


@dataclass(frozen=True)
class EvaluationConfig:
    """Ordered origins, horizon, step and seasonal lag for one entity/unit."""

    entity_type: str
    entity_id: str
    unit: str
    origins: tuple[datetime, ...]
    horizon: int
    step: timedelta
    seasonal_lag: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "origins", _as_tuple(self.origins, "$.origins"))

    def as_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "unit": self.unit,
            "origins": [origin.isoformat() for origin in self.origins],
            "horizon": self.horizon,
            "step_seconds": self.step.total_seconds(),
            "seasonal_lag": self.seasonal_lag,
        }


@dataclass(frozen=True)
class EvaluationInput:
    """Validated synthetic input: config plus isolated history/truth partitions."""

    config: EvaluationConfig
    history: Partition
    truth: Partition
    synthetic: bool = True


@dataclass(frozen=True)
class BuildResult:
    """Result of parsing a mapping into one immutable record."""

    value: object | None
    errors: tuple[ModelingError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


# --- observation parsing --------------------------------------------------

_OBSERVATION_FIELDS = frozenset(
    {"timestamp", "value", "source_revision", "availability", "unknown_reason"}
)


def _parse_observation(value, path: str, errors: list) -> Observation | None:
    if not is_mapping(value):
        errors.append(issue(INVALID_TYPE, path))
        return None
    _reject_unknown(value, _OBSERVATION_FIELDS, path, errors)

    timestamp = None
    if "timestamp" in value:
        timestamp = parse_timestamp(value["timestamp"], f"{path}.timestamp", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.timestamp"))

    numeric = None
    if "value" in value:
        numeric = parse_number(value["value"], f"{path}.value", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.value"))

    revision = _get_string(value, "source_revision", path, errors)

    availability = None
    unknown_reason = None
    if "availability" not in value:
        errors.append(issue(MISSING_FIELD, f"{path}.availability"))
    else:
        raw = value["availability"]
        if raw is None:
            reason = value.get("unknown_reason")
            if not isinstance(reason, str) or not reason:
                errors.append(issue(MISSING_FIELD, f"{path}.unknown_reason"))
            elif not is_utf8_text(reason):
                errors.append(issue(INVALID_VALUE, f"{path}.unknown_reason"))
            else:
                unknown_reason = reason
        else:
            availability = parse_timestamp(raw, f"{path}.availability", errors)
            if value.get("unknown_reason") is not None:
                errors.append(issue(INVALID_VALUE, f"{path}.unknown_reason"))

    if None in (timestamp, numeric, revision):
        return None
    return Observation(
        timestamp=timestamp,
        value=numeric,
        source_revision=revision,
        availability=availability,
        unknown_reason=unknown_reason,
    )


# --- partition / config / input parsing -----------------------------------

_PARTITION_FIELDS = frozenset({"entity_type", "entity_id", "unit", "observations"})
_CONFIG_FIELDS = frozenset(
    {
        "entity_type",
        "entity_id",
        "unit",
        "origins",
        "horizon",
        "step",
        "step_seconds",
        "seasonal_lag",
    }
)
_INPUT_FIELDS = frozenset({"synthetic", "config", "history", "truth"})


def _parse_identity(obj: Mapping, path: str, errors: list) -> tuple[str, str, str] | None:
    entity_type = _get_string(obj, "entity_type", path, errors)
    entity_id = _get_string(obj, "entity_id", path, errors)
    unit = _get_string(obj, "unit", path, errors)
    if None in (entity_type, entity_id, unit):
        return None
    return entity_type, entity_id, unit


def _parse_ordered_timestamps(
    value, path: str, errors: list, *, duplicate_code: str, order_code: str
) -> tuple[datetime, ...] | None:
    if not is_sequence(value):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if not value:
        errors.append(issue(INVALID_VALUE, path))
        return None
    parsed: list[datetime] = []
    for index, item in enumerate(value):
        moment = parse_timestamp(item, f"{path}[{index}]", errors)
        if moment is None:
            return None
        parsed.append(moment)
    for previous, current in zip(parsed, parsed[1:]):
        if current == previous:
            errors.append(issue(duplicate_code, path))
            return None
        if current < previous:
            errors.append(issue(order_code, path))
            return None
    return tuple(parsed)


def build_partition(value, path: str = "$") -> BuildResult:
    """Parse one entity/unit observation partition without raising."""
    errors: list[ModelingError] = []
    if not is_mapping(value):
        return BuildResult(None, (issue(INVALID_TYPE, path),))
    _reject_unknown(value, _PARTITION_FIELDS, path, errors)
    identity = _parse_identity(value, path, errors)

    rows: tuple[Observation, ...] = ()
    if "observations" not in value:
        errors.append(issue(MISSING_FIELD, f"{path}.observations"))
    elif not is_sequence(value["observations"]):
        errors.append(issue(INVALID_TYPE, f"{path}.observations"))
    else:
        parsed: list[Observation] = []
        for index, raw in enumerate(value["observations"]):
            row = _parse_observation(raw, f"{path}.observations[{index}]", errors)
            if row is not None:
                parsed.append(row)
        rows = tuple(parsed)
        for previous, current in zip(parsed, parsed[1:]):
            if current.timestamp == previous.timestamp:
                errors.append(issue(DUPLICATE_TIMESTAMP, f"{path}.observations"))
                break
            if current.timestamp < previous.timestamp:
                errors.append(issue(UNORDERED_TIMESTAMPS, f"{path}.observations"))
                break

    if errors or identity is None:
        return BuildResult(None, tuple(errors))
    return BuildResult(Partition(*identity, rows))


def _parse_origins(value, path: str, errors: list) -> tuple[datetime, ...] | None:
    return _parse_ordered_timestamps(
        value, path, errors, duplicate_code=DUPLICATE_TIMESTAMP, order_code=ORIGIN_ORDER
    )


def _checked_step_product(step: timedelta, count: int) -> timedelta | None:
    """Multiply a step by a count, returning ``None`` when timedelta overflows."""
    try:
        return step * count
    except (OverflowError, ValueError):
        return None


def _config_temporal_errors(config: EvaluationConfig, path: str) -> list[ModelingError]:
    """Reject a configuration whose spans cannot be represented as datetimes.

    The earliest seasonal slot is ``origin - step*(lag-1)`` and the latest
    horizon target is ``origin + step*horizon``.  Huge horizon/lag integers can
    overflow the ``timedelta`` product, and either span can push a datetime past
    ``datetime.min``/``datetime.max``.  Both are checked before any provider is
    invoked so the failure is a structured config error rather than a raw
    ``OverflowError``.
    """
    season_span = _checked_step_product(config.step, config.seasonal_lag - 1)
    horizon_span = _checked_step_product(config.step, config.horizon)
    if season_span is None or horizon_span is None:
        return [issue(INVALID_VALUE, path)]
    for origin in config.origins:
        try:
            origin - season_span
            origin + horizon_span
        except (OverflowError, ValueError):
            return [issue(INVALID_VALUE, f"{path}.origins")]
    return []


def build_config(value, path: str = "$.config") -> BuildResult:
    """Parse an evaluation configuration without raising."""
    errors: list[ModelingError] = []
    if not is_mapping(value):
        return BuildResult(None, (issue(INVALID_TYPE, path),))
    _reject_unknown(value, _CONFIG_FIELDS, path, errors)
    identity = _parse_identity(value, path, errors)

    origins = None
    if "origins" in value:
        origins = _parse_origins(value["origins"], f"{path}.origins", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.origins"))

    horizon = None
    if "horizon" in value:
        horizon = parse_positive_int(value["horizon"], f"{path}.horizon", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.horizon"))

    seasonal_lag = None
    if "seasonal_lag" in value:
        seasonal_lag = parse_positive_int(value["seasonal_lag"], f"{path}.seasonal_lag", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.seasonal_lag"))

    step = None
    has_step = "step" in value
    has_seconds = "step_seconds" in value
    if has_step and has_seconds:
        errors.append(issue(INVALID_VALUE, f"{path}.step"))
    elif has_step:
        raw = value["step"]
        if isinstance(raw, timedelta):
            step = parse_step(raw, f"{path}.step", errors)
        else:
            errors.append(issue(INVALID_TYPE, f"{path}.step"))
    elif has_seconds:
        step = parse_step(value["step_seconds"], f"{path}.step_seconds", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.step_seconds"))

    if errors or identity is None or origins is None or horizon is None or seasonal_lag is None or step is None:
        return BuildResult(None, tuple(errors))
    config = EvaluationConfig(*identity, origins, horizon, step, seasonal_lag)
    errors.extend(_config_temporal_errors(config, path))
    if errors:
        return BuildResult(None, tuple(errors))
    return BuildResult(config)


def _check_identity_match(
    config: EvaluationConfig, partition: Partition, path: str
) -> list[ModelingError]:
    """Report each identity mismatch at the field that actually mismatched.

    The path always names the offending leaf field (``entity_type``,
    ``entity_id`` or ``unit``) of the partition, rather than a fixed
    ``entity_id`` pointer for both the entity and the unit failure.
    """
    errors: list[ModelingError] = []
    if partition.entity_type != config.entity_type:
        errors.append(issue(MIXED_ENTITIES, f"{path}.entity_type"))
    if partition.entity_id != config.entity_id:
        errors.append(issue(MIXED_ENTITIES, f"{path}.entity_id"))
    if partition.unit != config.unit:
        errors.append(issue(MIXED_UNITS, f"{path}.unit"))
    return errors


def build_input(value, path: str = "$") -> BuildResult:
    """Parse the full synthetic evaluation input without raising."""
    errors: list[ModelingError] = []
    if not is_mapping(value):
        return BuildResult(None, (issue(INVALID_TYPE, path),))
    _reject_unknown(value, _INPUT_FIELDS, path, errors)

    synthetic = False
    if "synthetic" not in value:
        errors.append(issue(MISSING_FIELD, f"{path}.synthetic"))
    elif value["synthetic"] is not True:
        if isinstance(value["synthetic"], bool):
            errors.append(issue(REAL_INPUT_UNSUPPORTED, f"{path}.synthetic"))
        else:
            errors.append(issue(INVALID_TYPE, f"{path}.synthetic"))
    else:
        synthetic = True

    config_result = build_config(value.get("config"), f"{path}.config")
    errors.extend(config_result.errors)
    history_result = build_partition(value.get("history"), f"{path}.history")
    errors.extend(history_result.errors)
    truth_result = build_partition(value.get("truth"), f"{path}.truth")
    errors.extend(truth_result.errors)

    config = config_result.value
    history = history_result.value
    truth = truth_result.value

    if config is not None and history is not None:
        errors.extend(_check_identity_match(config, history, f"{path}.history"))
    if config is not None and truth is not None:
        errors.extend(_check_identity_match(config, truth, f"{path}.truth"))

    if errors or not synthetic or config is None or history is None or truth is None:
        return BuildResult(None, tuple(errors))
    return BuildResult(EvaluationInput(config=config, history=history, truth=truth, synthetic=True))


# --- revalidation of already-constructed records --------------------------


def _observation_to_source(observation, path: str, errors: list) -> dict | None:
    if not isinstance(observation, Observation):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if not isinstance(observation.timestamp, datetime):
        errors.append(issue(INVALID_TIMESTAMP, f"{path}.timestamp"))
        return None
    if observation.availability is not None and not isinstance(observation.availability, datetime):
        errors.append(issue(INVALID_TIMESTAMP, f"{path}.availability"))
        return None
    return {
        "timestamp": observation.timestamp,
        "value": observation.value,
        "source_revision": observation.source_revision,
        "availability": observation.availability,
        "unknown_reason": observation.unknown_reason,
    }


def _partition_to_source(partition, path: str, errors: list) -> dict | None:
    if not isinstance(partition, Partition):
        errors.append(issue(INVALID_TYPE, path))
        return None
    rows = partition.observations
    if not is_sequence(rows):
        errors.append(issue(INVALID_TYPE, f"{path}.observations"))
        return None
    projected: list[dict] = []
    for index, observation in enumerate(rows):
        source = _observation_to_source(observation, f"{path}.observations[{index}]", errors)
        if source is not None:
            projected.append(source)
    return {
        "entity_type": partition.entity_type,
        "entity_id": partition.entity_id,
        "unit": partition.unit,
        "observations": projected,
    }


def _config_to_source(config, path: str, errors: list) -> dict | None:
    if not isinstance(config, EvaluationConfig):
        errors.append(issue(INVALID_TYPE, path))
        return None
    origins = config.origins
    if not is_sequence(origins):
        errors.append(issue(INVALID_TYPE, f"{path}.origins"))
        return None
    projected_origins: list[datetime] = []
    for index, origin in enumerate(origins):
        if not isinstance(origin, datetime):
            errors.append(issue(INVALID_TIMESTAMP, f"{path}.origins[{index}]"))
            return None
        projected_origins.append(origin)
    if not isinstance(config.step, timedelta):
        errors.append(issue(INVALID_TYPE, f"{path}.step"))
        return None
    return {
        "entity_type": config.entity_type,
        "entity_id": config.entity_id,
        "unit": config.unit,
        "origins": projected_origins,
        "horizon": config.horizon,
        "step": config.step,
        "seasonal_lag": config.seasonal_lag,
    }


def revalidate_input(value, path: str = "$") -> BuildResult:
    """Re-validate an already-constructed :class:`EvaluationInput`.

    A typed record can be built directly or mutated with ``dataclasses.replace``,
    bypassing the ``build_*`` parsers.  This projects it back to a plain mapping
    through explicit type checks (never ``as_dict`` on unvalidated attributes)
    and runs the same :func:`build_input`, so malformed nested records become
    structured errors and accepted records are normalized back into deeply
    immutable tuple-backed records.
    """
    errors: list[ModelingError] = []
    if not isinstance(value, EvaluationInput):
        return BuildResult(None, (issue(INVALID_TYPE, path),))
    config_source = _config_to_source(value.config, f"{path}.config", errors)
    history_source = _partition_to_source(value.history, f"{path}.history", errors)
    truth_source = _partition_to_source(value.truth, f"{path}.truth", errors)
    if errors or config_source is None or history_source is None or truth_source is None:
        return BuildResult(None, tuple(errors))
    return build_input(
        {
            "synthetic": value.synthetic,
            "config": config_source,
            "history": history_source,
            "truth": truth_source,
        },
        path,
    )


# --- canonical digest -----------------------------------------------------


def canonical_dumps(value) -> str:
    """Deterministic canonical JSON used for the input digest."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _observation_payload(observation: Observation) -> dict:
    return observation.as_dict()


def compute_input_digest(
    config: EvaluationConfig,
    history: Partition,
    truth: Partition,
    models: Sequence[tuple[str, str]],
) -> str:
    """SHA-256 over config, both partitions, provenance and model identities.

    Any change to a value, revision, availability, unknown reason, origin,
    horizon, step, lag or compared baseline changes the digest.
    """
    payload = {
        "synthetic": True,
        "config": config.as_dict(),
        "history": history.as_dict(),
        "truth": truth.as_dict(),
        "models": [{"name": name, "version": version} for name, version in models],
    }
    encoded = canonical_dumps(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "Observation",
    "Partition",
    "EvaluationConfig",
    "EvaluationInput",
    "BuildResult",
    "build_partition",
    "build_config",
    "build_input",
    "canonical_dumps",
    "compute_input_digest",
    "is_mapping",
    "is_sequence",
    "is_utf8_text",
    "parse_number",
    "parse_positive_int",
    "parse_step",
    "parse_timestamp",
    "revalidate_input",
    "safe_finite_float",
]
