"""Fuel features for the PRICE-3 challengers, read strictly as of a forecast's cutoff.

The history file is written by ``scripts/fuel/pull_history.py``: public series only (EIA daily
Brent spot, ECB USD/PHP, IMF monthly coal, LNG and Dubai). Trading Economics quotes have no
history and a demo-only licence, so they never enter a feature.

A value is readable only once it was published. The lags are conservative:

* EIA daily spot for day ``d``: from ``d + 2 days`` (EIA posts about two working days late);
* ECB reference rate for day ``d``: from ``d + 1 day`` (published 16:00 CET on ``d``);
* IMF monthly average for month ``m``: from the 15th of month ``m + 1``.

A feature whose latest published value is older than its staleness limit is absent, never
carried forward. All dates are calendar dates compared with the cutoff's date, so a value that
becomes readable on the cutoff's own date is used only if the cutoff is at or after midnight of
that date (the cutoff is a naive Manila datetime, as everywhere in ``src/price``).
"""
from __future__ import annotations

import csv
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

#: Names of the features :meth:`FuelFeatures.__call__` returns, in order.
FUEL_FEATURES: tuple[str, ...] = (
    "brent_usd", "brent_change_28d", "usdphp", "coal_au_usd", "lng_jp_usd", "dubai_usd",
)

EIA_LAG = timedelta(days=2)
ECB_LAG = timedelta(days=1)
DAILY_STALE = timedelta(days=10)   # a daily value older than this at the cutoff is absent
MONTHLY_STALE = timedelta(days=80)  # a monthly value published longer ago than this is absent


class FuelError(ValueError):
    pass


def imf_published(month: str) -> date:
    """The day an IMF monthly value for ``YYYY-MM`` becomes readable: the 15th of the next month."""
    year, mon = (int(x) for x in month.split("-"))
    return date(year + (mon == 12), mon % 12 + 1, 15)


@dataclass(frozen=True)
class _AsOf:
    """One series as (readable_from, value) pairs, sorted by readable_from."""

    readable: tuple[date, ...]
    values: tuple[float, ...]
    observed: tuple[date, ...]

    def latest(self, on: date) -> tuple[date, float] | None:
        """The last value readable on ``on``, with its observation date."""
        i = bisect_right(self.readable, on)
        if i == 0:
            return None
        return self.observed[i - 1], self.values[i - 1]


def _daily(points: dict[str, float], lag: timedelta) -> _AsOf:
    items = sorted((date.fromisoformat(d), v) for d, v in points.items())
    return _AsOf(tuple(d + lag for d, _ in items), tuple(v for _, v in items), tuple(d for d, _ in items))


def _monthly(points: dict[str, float]) -> _AsOf:
    items = sorted((imf_published(m), v, date.fromisoformat(m + "-01")) for m, v in points.items())
    return _AsOf(tuple(p for p, _, _ in items), tuple(v for _, v, _ in items), tuple(o for _, _, o in items))


def load_history(path: str | Path) -> dict[str, dict[str, float]]:
    """``{series_id: {period: value}}`` from the history CSV."""
    out: dict[str, dict[str, float]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        need = {"series_id", "period", "value"}
        if not need <= set(reader.fieldnames or ()):
            raise FuelError(f"{path}: header lacks {sorted(need)}")
        for row in reader:
            out.setdefault(row["series_id"], {})[row["period"]] = float(row["value"])
    return out


class FuelFeatures:
    """Callable ``cutoff -> feature tuple | None`` for :class:`src.price.challengers.OriginContext`."""

    names = FUEL_FEATURES

    def __init__(self, history: dict[str, dict[str, float]]) -> None:
        missing = [s for s in ("RBRTE", "USDPHP_CALC", "PCOALAU", "PNGASJP", "POILDUB") if s not in history]
        if missing:
            raise FuelError(f"fuel history lacks {missing}")
        self.brent = _daily(history["RBRTE"], EIA_LAG)
        self.usdphp = _daily(history["USDPHP_CALC"], ECB_LAG)
        self.coal = _monthly(history["PCOALAU"])
        self.lng = _monthly(history["PNGASJP"])
        self.dubai = _monthly(history["POILDUB"])
        self._cache: dict[date, tuple[float, ...] | None] = {}

    @classmethod
    def from_csv(cls, path: str | Path) -> "FuelFeatures":
        return cls(load_history(path))

    def __call__(self, cutoff: datetime) -> tuple[float, ...] | None:
        on = cutoff.date() if isinstance(cutoff, datetime) else cutoff
        if on not in self._cache:
            self._cache[on] = self._compute(on)
        return self._cache[on]

    def _daily_value(self, series: _AsOf, on: date) -> float | None:
        hit = series.latest(on)
        if hit is None or on - hit[0] > DAILY_STALE:
            return None
        return hit[1]

    def _monthly_value(self, series: _AsOf, on: date) -> float | None:
        i = bisect_right(series.readable, on)
        if i == 0 or on - series.readable[i - 1] > MONTHLY_STALE:
            return None
        return series.values[i - 1]

    def _compute(self, on: date) -> tuple[float, ...] | None:
        brent = self._daily_value(self.brent, on)
        brent_before = self._daily_value(self.brent, on - timedelta(days=28))
        usdphp = self._daily_value(self.usdphp, on)
        coal = self._monthly_value(self.coal, on)
        lng = self._monthly_value(self.lng, on)
        dubai = self._monthly_value(self.dubai, on)
        values = (brent, brent_before, usdphp, coal, lng, dubai)
        if any(v is None for v in values):
            return None
        change = (brent - brent_before) / brent_before
        return (brent, change, usdphp, coal, lng, dubai)
