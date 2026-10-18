"""Bounded in-process prediction port and the two built-in baselines.

Trust boundary
==============
This port is a pure in-process function call for deterministic synthetic
evaluation.  It is **not** an external execution adapter, does not contact any
model SDK or network, and does not authorize running a forecasting system.
Providers receive only the as-of filtered history for one origin; they never
receive evaluation truth or future history.

Expected provider failures use :class:`ProviderError` with a fixed safe code.
Any other exception is treated as programmer error and is not swallowed by the
harness.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from .errors import (
    INVALID_PROVIDER,
    MISSING_SEASON_SLOT,
    NO_ELIGIBLE_HISTORY,
    ModelingError,
    issue,
)


@dataclass(frozen=True)
class ContextObservation:
    """One eligible as-of history row, with staleness in whole steps."""

    timestamp: datetime
    value: float
    source_revision: str
    availability: datetime | None
    age_steps: int

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "source_revision": self.source_revision,
            "availability": self.availability.isoformat() if self.availability is not None else None,
            "age_steps": self.age_steps,
        }


@dataclass(frozen=True)
class ContextView:
    """The only history a provider may see for one origin."""

    entity_type: str
    entity_id: str
    unit: str
    origin: datetime
    horizon: int
    step: timedelta
    seasonal_lag: int
    observations: tuple[ContextObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observations, tuple):
            object.__setattr__(self, "observations", tuple(self.observations))


@dataclass(frozen=True)
class Prediction:
    """Provider output: horizon-aligned values plus the provenance used."""

    values: tuple[float, ...]
    used_timestamps: tuple[datetime, ...]

    def __post_init__(self) -> None:
        # Only a list is normalized to a tuple.  A non-iterable such as a scalar
        # ``values`` (a realistic horizon-1 mistake) is left untouched so the
        # harness can reject it as ``MALFORMED_PREDICTION`` for that origin
        # instead of raising ``TypeError`` here and aborting the comparison.
        if isinstance(self.values, list):
            object.__setattr__(self, "values", tuple(self.values))
        if isinstance(self.used_timestamps, list):
            object.__setattr__(self, "used_timestamps", tuple(self.used_timestamps))


class ProviderError(Exception):
    """Expected, declared provider failure that excludes one origin."""

    def __init__(self, code: str) -> None:
        self.error: ModelingError = issue(code)
        self.code = code
        super().__init__(self.error.message)


class ProviderLookupError(Exception):
    """Raised by :func:`builtin_providers_by_name` for an unknown model name.

    Returning ``None`` here previously let a typo fall through into
    ``run_evaluation(..., providers=None)``, where ``None`` selects the default
    comparison.  The lookup now fails loudly and carries the structured error
    the caller should surface.
    """

    def __init__(self, name: object) -> None:
        self.name = name
        self.error: ModelingError = issue(INVALID_PROVIDER, "$.models")
        super().__init__(self.error.message)


@runtime_checkable
class BaselineProvider(Protocol):
    """Pure in-process prediction port (not an execution authorization)."""

    name: str
    version: str
    formula: str

    def predict(self, context: ContextView) -> Prediction:
        ...


class PersistenceProvider:
    """Repeat the latest eligible value at every lead."""

    name = "persistence"
    version = "m0.1"
    formula = "prediction(lead) = value at the latest eligible history timestamp <= origin"

    def predict(self, context: ContextView) -> Prediction:
        if not context.observations:
            raise ProviderError(NO_ELIGIBLE_HISTORY)
        latest = context.observations[-1]
        values = tuple(latest.value for _ in range(context.horizon))
        return Prediction(values=values, used_timestamps=(latest.timestamp,))


class SeasonalNaiveProvider:
    """Repeat the last complete eligible season with modulo indexing."""

    name = "seasonal_naive"
    version = "m0.1"
    formula = (
        "prediction(lead) = season[(lead-1) % lag]; season = eligible values at "
        "origin-(lag-1)*step ... origin in chronological order"
    )

    def predict(self, context: ContextView) -> Prediction:
        lag = context.seasonal_lag
        by_timestamp = {row.timestamp: row for row in context.observations}
        season: list[float] = []
        used: list[datetime] = []
        for index in range(lag):
            slot = context.origin - context.step * (lag - 1 - index)
            row = by_timestamp.get(slot)
            if row is None:
                raise ProviderError(MISSING_SEASON_SLOT)
            season.append(row.value)
            used.append(slot)
        values = tuple(season[(lead - 1) % lag] for lead in range(1, context.horizon + 1))
        return Prediction(values=values, used_timestamps=tuple(used))


def default_providers() -> tuple[BaselineProvider, ...]:
    """Return one fresh instance of each built-in baseline."""
    return (PersistenceProvider(), SeasonalNaiveProvider())


def builtin_providers_by_name(names) -> tuple[BaselineProvider, ...]:
    """Map fixture model names to fresh built-in provider instances.

    An unknown name raises :class:`ProviderLookupError`; this helper never
    returns ``None``, so its result cannot be silently interpreted downstream as
    "use the default providers".
    """
    registry = {
        PersistenceProvider.name: PersistenceProvider,
        SeasonalNaiveProvider.name: SeasonalNaiveProvider,
    }
    providers: list[BaselineProvider] = []
    for name in names:
        factory = registry.get(name)
        if factory is None:
            raise ProviderLookupError(name)
        providers.append(factory())
    return tuple(providers)


__all__ = [
    "BaselineProvider",
    "ContextObservation",
    "ContextView",
    "PersistenceProvider",
    "Prediction",
    "ProviderError",
    "ProviderLookupError",
    "SeasonalNaiveProvider",
    "builtin_providers_by_name",
    "default_providers",
]
