"""Rolling-origin windows and the three PRICE-2 baselines.

The windows
===========
The price target contract scores three horizons, each the window that begins at
the origin: the **day** (one billing day, 24 hours), the **week** (seven billing
days, 168 hours) and the **month** (the billing month that begins at the origin,
26th 00:00 to 25th 23:00). A billing day is a calendar day, so the day and week
origins are days; a month origin is a billing-month start (the 26th).

The baselines
=============
Every baseline is a pure function of the exported rows that ended at or before
the history cutoff (``origin - embargo``), and each returns one value per target
hour. The scorecard aggregates those values over the window exactly as it
aggregates the realized prices, so the two sides are comparable.

* **persistence** — repeat the latest exported value. This is the persistence
  provider of the M0 harness (``src/modeling/providers.py``) at the hourly step,
  with an added staleness bound: a value older than ``max_age_hours`` is refused
  rather than forecast across a four-month gap.
* **last week same interval** — repeat the same clock hour the smallest whole
  number of weeks earlier whose hour ended at or before the cutoff. This is M0's
  seasonal-naive provider with a weekly season, and it is the standard "same
  interval last week" benchmark: for the day horizon every lead reads the same
  clock hour seven days earlier, and a lead that would reach past the cutoff
  steps back another week, so the weekly pattern repeats over a longer horizon.
* **seasonal average by billing month** — the mean of the same clock hour in the
  same billing month of earlier years, which is the load-weighted history of
  that month at that hour of the day. The average needs at least
  ``min_samples`` exported hours from at least ``min_seasons`` earlier years;
  below either floor the origin is excluded, never padded with a neighbouring
  hour or year.

A missing hour is never filled: a baseline that needs one raises
:class:`BaselineError` with a fixed code and the scorecard records the origin as
excluded under that code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .series import (
    HOUR,
    HOURS_PER_DAY,
    INTERVALS_PER_HOUR,
    WEEK_HOURS,
    Series,
    billing_day_hours,
    billing_month_end,
    billing_month_label,
    billing_month_of,
    billing_month_start,
)

HORIZONS = ("day", "week", "month")


class BaselineError(Exception):
    """A declared, expected baseline failure that excludes one origin."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class Window:
    """One horizon's target hours, the window that begins at the origin."""

    horizon: str
    start: datetime
    hours: tuple[datetime, ...]

    @property
    def origin(self) -> date:
        return self.start.date()

    @property
    def end(self) -> datetime:
        """The exclusive end: the first instant after the last target hour."""
        return self.hours[-1] + HOUR

    @property
    def days(self) -> int:
        return len(self.hours) // HOURS_PER_DAY

    def label(self) -> str:
        if self.horizon == "month":
            year, month = billing_month_of(self.start)
            return billing_month_label(year, month)
        return self.start.date().isoformat()


def window_for(horizon: str, origin: date) -> Window:
    """The target window of one horizon that begins at ``origin``.

    For the month horizon the window is the billing month containing ``origin``,
    so the caller passes a billing-month start (the 26th); the day and week
    windows begin on the origin date itself.
    """
    if horizon == "day":
        return Window(horizon, datetime(origin.year, origin.month, origin.day),
                      billing_day_hours(origin))
    if horizon == "week":
        hours: list[datetime] = []
        day = origin
        for _ in range(7):
            hours.extend(billing_day_hours(day))
            day += timedelta(days=1)
        return Window(horizon, hours[0], tuple(hours))
    if horizon == "month":
        year, month = billing_month_of(origin)
        start = billing_month_start(year, month)
        hours = []
        day = start
        end = billing_month_end(year, month)
        while day <= end:
            hours.extend(billing_day_hours(day))
            day += timedelta(days=1)
        return Window(horizon, hours[0], tuple(hours))
    raise BaselineError("UNKNOWN_HORIZON", horizon)


def candidate_origins(horizon: str, first_day: date, last_day: date) -> tuple[date, ...]:
    """Every origin whose window fits inside the series' own first and last day.

    Candidates are enumerated over the whole span, gaps included, so an origin
    that falls in a marked month is excluded with a recorded reason instead of
    quietly disappearing from the denominator.
    """
    if horizon == "day":
        days = (last_day - first_day).days
        return tuple(first_day + timedelta(days=step) for step in range(days + 1))
    if horizon == "week":
        days = (last_day - first_day).days - 6
        return tuple(first_day + timedelta(days=step) for step in range(max(days, 0) + 1))
    if horizon == "month":
        origins: list[date] = []
        year, month = billing_month_of(first_day)
        while True:
            start = billing_month_start(year, month)
            if billing_month_end(year, month) > last_day:
                break
            if start >= first_day:
                origins.append(start)
            month += 1
            if month == 13:
                year, month = year + 1, 1
        return tuple(origins)
    raise BaselineError("UNKNOWN_HORIZON", horizon)


def history_cutoff(origin: date, embargo_hours: int) -> datetime:
    """The last instant whose value a forecast at ``origin`` may have seen.

    The embargo stands in for first availability: a final settlement price is
    known only after its billing month closes (the target contract records the
    arrival rule), so a value is not treated as knowable the moment its hour
    ends. The plan note fixes a one-day embargo for the blocked rolling origin.
    """
    midnight = datetime(origin.year, origin.month, origin.day)
    return midnight - timedelta(hours=embargo_hours)


def last_ended_hour(cutoff: datetime) -> datetime:
    """The latest hour start whose hour has ended at or before ``cutoff``."""
    floored = cutoff.replace(minute=0, second=0, microsecond=0)
    if floored == cutoff:
        floored -= HOUR
    return floored


@dataclass(frozen=True)
class Forecast:
    """One baseline's window forecast: a value per target hour, and its inputs."""

    values: tuple[float, ...]
    detail: Mapping[str, object]


@runtime_checkable
class Baseline(Protocol):
    """A pure in-process forecast function over exported rows.

    ``index`` carries a per-series seasonal index when the caller has already
    built one (:meth:`SeasonalAverageByBillingMonth.index_series`); baselines
    that do not use it accept and ignore it, so every baseline is called the
    same way.
    """

    name: str
    version: str
    formula: str

    def forecast(
        self,
        series: Series,
        window: Window,
        cutoff: datetime,
        index: Mapping[tuple[str, int], Sequence[float]] | None = None,
    ) -> Forecast:
        ...


def aggregate(values: Sequence[float], weights: Sequence[int]) -> float:
    """Weighted mean, the same rule the scorecard uses on realized prices.

    One weight per value, in order; a length mismatch is a programming error and
    raises rather than silently scoring a shorter window.
    """
    if len(values) != len(weights):
        raise BaselineError("WINDOW_MISMATCH", f"{len(values)} values, {len(weights)} weights")
    weight = sum(weights)
    if not weight:
        raise BaselineError("EMPTY_WINDOW")
    return sum(value * count for value, count in zip(values, weights)) / weight


class Persistence:
    """Repeat the latest exported value at every target hour."""

    name = "persistence"
    version = "price-2.1"
    formula = (
        "forecast(hour) = mean of the latest exported hour that ended at or before the "
        "cutoff; refused when that hour is more than max_age_hours old"
    )

    def __init__(self, max_age_hours: int = 24) -> None:
        self.max_age_hours = max_age_hours

    def forecast(
        self,
        series: Series,
        window: Window,
        cutoff: datetime,
        index: Mapping[tuple[str, int], Sequence[float]] | None = None,
    ) -> Forecast:
        last = last_ended_hour(cutoff)
        row = series.latest_at_or_before(last)
        if row is None:
            raise BaselineError("NO_HISTORY", "no exported hour at or before the cutoff")
        age = (cutoff - (row.hour_start + HOUR)).total_seconds() / 3600
        if age > self.max_age_hours:
            raise BaselineError(
                "STALE_HISTORY",
                f"{row.hour_start.isoformat()} is {age:.0f}h older than the cutoff",
            )
        return Forecast((row.mean,) * len(window.hours),
                        {"used": row.hour_start.isoformat(), "age_hours": round(age, 3)})


class LastWeekSameInterval:
    """Repeat the same clock hour the smallest whole number of weeks earlier.

    With the one-day embargo the same clock hour seven days before a target hour
    has already ended at the cutoff, so the day window reads exactly the clock
    intervals of the previous week. A week or month window reaches past the
    cutoff; for those target hours the weekly pattern steps back another week
    until the sampled hour ended at or before the cutoff, so every target hour
    reads its own clock hour of an earlier week.
    """

    name = "last_week_same_interval"
    version = "price-2.2"
    formula = (
        "forecast(hour) = the exported value at the same clock hour the smallest whole "
        "number of weeks earlier whose hour ended at or before the cutoff; every sampled "
        "hour must be one complete exported hour"
    )

    def forecast(
        self,
        series: Series,
        window: Window,
        cutoff: datetime,
        index: Mapping[tuple[str, int], Sequence[float]] | None = None,
    ) -> Forecast:
        last = last_ended_hour(cutoff)
        samples: list[datetime] = []
        weeks = 1
        for hour in window.hours:
            sample = hour - HOUR * WEEK_HOURS
            steps = 1
            while sample > last:
                sample -= HOUR * WEEK_HOURS
                steps += 1
            weeks = max(weeks, steps)
            samples.append(sample)
        sample = tuple(samples)
        rows = series.present(sample)
        if len(rows) != len(sample) or series.intervals(sample) != len(sample) * INTERVALS_PER_HOUR:
            missing = len(sample) - len(rows)
            wrong = sum(1 for row in rows if row.intervals != INTERVALS_PER_HOUR)
            raise BaselineError(
                "INCOMPLETE_WEEK",
                f"{missing} of {len(sample)} sampled hours absent and {wrong} not of "
                f"{INTERVALS_PER_HOUR} intervals before {last.isoformat()}",
            )
        return Forecast(
            tuple(row.mean for row in rows),
            {"sample_start": sample[0].isoformat(), "sample_end": sample[-1].isoformat(),
             "weeks": weeks},
        )


class SeasonalAverageByBillingMonth:
    """Average the same clock hour over the same billing month of earlier years."""

    name = "seasonal_average_billing_month"
    version = "price-2.1"
    formula = (
        "forecast(hour) = mean of the exported values at the same hour of day in the same "
        "billing month of earlier years, at or before the cutoff; needs at least "
        "min_samples hours from at least min_seasons years"
    )

    def __init__(self, min_samples: int = 21, min_seasons: int = 1, years_back: int = 8) -> None:
        self.min_samples = min_samples
        self.min_seasons = min_seasons
        self.years_back = years_back

    @staticmethod
    def index_series(series: Series) -> dict[tuple[str, int], list[int]]:
        """``(billing month label, hour of day) -> [sum of means, count]``.

        Built from the exported rows only: an absent month adds nothing here, and
        no value is carried over from another hour or another year.
        """
        index: dict[tuple[str, int], list[int | float]] = {}
        for row in series.rows.values():
            key = (row.billing_month, row.hour_start.hour)
            entry = index.setdefault(key, [0.0, 0])
            entry[0] += row.mean
            entry[1] += 1
        return index

    def forecast(
        self,
        series: Series,
        window: Window,
        cutoff: datetime,
        index: Mapping[tuple[str, int], Sequence[float]] | None = None,
    ) -> Forecast:
        index = self.index_series(series) if index is None else index
        values, samples, seasons = [], 0, 0
        for hour in window.hours:
            year, month = billing_month_of(hour)
            total, count, used = 0.0, 0, 0
            for back in range(1, self.years_back + 1):
                entry = index.get((billing_month_label(year - back, month), hour.hour))
                if entry:
                    total += entry[0]
                    count += int(entry[1])
                    used += 1
            if count < self.min_samples or used < self.min_seasons:
                hour_label = hour.isoformat()
                raise BaselineError(
                    "INSUFFICIENT_SEASON_SAMPLES",
                    f"{hour_label}: {count} hours from {used} earlier seasons",
                )
            values.append(total / count)
            samples, seasons = max(samples, count), max(seasons, used)
        return Forecast(tuple(values), {"samples": samples, "seasons": seasons})


def default_baselines() -> tuple[Baseline, ...]:
    """One fresh instance of each PRICE-2 baseline, in a fixed order."""
    return (Persistence(), LastWeekSameInterval(), SeasonalAverageByBillingMonth())


__all__ = [
    "HORIZONS",
    "Baseline",
    "BaselineError",
    "Forecast",
    "LastWeekSameInterval",
    "Persistence",
    "SeasonalAverageByBillingMonth",
    "Window",
    "aggregate",
    "candidate_origins",
    "default_baselines",
    "history_cutoff",
    "last_ended_hour",
    "window_for",
]
