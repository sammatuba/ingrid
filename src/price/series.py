"""The PRICE-1 export read back: hourly rows, the billing clock, and the marks.

Inputs
======
Two files written by the orchestrator seat under the ignored ``.local/price/``
(see ``docs/work/price-outlook/export.md``), each cited by SHA-256:

* ``lwap_final_hourly.csv`` — the public regional load-weighted final price
  (``PMR_LWAP_Final``) by hour: ``byear, bmonth, region_name, hour_start, n5,
  lwap_mean, lwap_min, lwap_max`` for ``CLUZ``, ``CVIS``, ``CMIN`` and
  ``SYSTEM``. It carries no pricing flag.
* ``portfolio_nodal_hourly_deid.csv`` — the final settlement price
  (``PMR_Settlement_Prices.lmp``) by hour for twelve de-identified load nodes
  ``N01`` to ``N12``: adds ``region, mw_mean, ap5, sec5, psm5``.

The clock is the billing month of the price target contract: a billing month
``YYYY-MM`` runs from the 26th of the month before to the 25th, and an hour is
keyed by ``hour_start``, the hour that begins at that timestamp. An hour is
known only once it has ended.

Marks, never fills
==================
Three kinds of mark are derived from the exported bytes, not from a promise:

* **absent months** — billing months inside the export's own range with no row;
* **short months** — billing months whose interval count is below the clock's;
* **irregular days** — dates whose interval count is not the 288 a complete
  day has. A merged hour (``n5`` above 12) and a one-row day are both this.

A fourth mark is recorded from the price target contract, because the regional
file has no flag of its own: **administered pricing months** (``pricing_flag =
AP``), which are scored as a separate slice and never as market skill.

Nothing in this module fills a mark. A missing hour is missing: consumers either
use a present row or exclude the origin, and :func:`derive_marks` only reports
what the bytes say.
"""
from __future__ import annotations

import csv
import hashlib
import json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Sequence

HOUR = timedelta(hours=1)
HOURS_PER_DAY = 24
INTERVALS_PER_HOUR = 12
INTERVALS_PER_DAY = INTERVALS_PER_HOUR * HOURS_PER_DAY
WEEK_HOURS = 7 * HOURS_PER_DAY

REGIONAL_KEYS = ("CLUZ", "CVIS", "CMIN", "SYSTEM")
REGIONAL_LABELS = {
    "CLUZ": "Luzon load-weighted average",
    "CVIS": "Visayas load-weighted average",
    "CMIN": "Mindanao load-weighted average",
    "SYSTEM": "whole-system load-weighted average",
}

#: Administered pricing by billing month, from
#: ``docs/work/thesis-challenge-2026-10-16/coverage.md`` (share of rows with
#: ``pricing_flag = AP`` above five per cent). ``all`` months settled entirely at
#: administered prices; ``mixed`` months carry both flags and reach no score.
#: The nodal file overrides this with its own per-hour counts.
ADMINISTERED_PRICING_MONTHS: tuple[tuple[str, str], ...] = (
    ("2026-04", "all"),
    ("2026-05", "mixed"),
    ("2022-01", "mixed"),
    ("2024-06", "mixed"),
    ("2021-12", "mixed"),
    ("2024-05", "mixed"),
)

REGIONAL_CSV = "lwap_final_hourly.csv"
NODAL_CSV = "portfolio_nodal_hourly_deid.csv"


class SeriesError(Exception):
    """A read failure, a malformed row or a digest that does not match."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --- the billing clock ----------------------------------------------------


def billing_month_of(moment: date | datetime) -> tuple[int, int]:
    """The billing month a calendar date belongs to (26th to the 25th).

    Billing month ``YYYY-MM`` runs from the 26th of the month before to the 25th
    of ``MM``, so a date maps to the month *after* the one 25 days earlier:
    2026-03-26 opens billing month 2026-04, and billing month 2021-07 opens at
    2021-06-26, the first ``hour_start`` of the regional export.
    """
    shifted = moment.date() if isinstance(moment, datetime) else moment
    shifted = shifted - timedelta(days=25)
    year, month = shifted.year, shifted.month + 1
    if month == 13:
        year, month = year + 1, 1
    return year, month


def billing_month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_of_label(label: str) -> tuple[int, int]:
    year, _, month = label.partition("-")
    return int(year), int(month)


def billing_month_start(year: int, month: int) -> date:
    """The first day of a billing month: the 26th of the month before."""
    if month == 1:
        return date(year - 1, 12, 26)
    return date(year, month - 1, 26)


def billing_month_end(year: int, month: int) -> date:
    """The last day of a billing month: the 25th of the month itself."""
    return date(year, month, 25)


def billing_month_days(year: int, month: int) -> int:
    return (billing_month_end(year, month) - billing_month_start(year, month)).days + 1


def billing_day_hours(day: date) -> tuple[datetime, ...]:
    """The 24 hour starts of one billing day (billing days are calendar days)."""
    midnight = datetime(day.year, day.month, day.day)
    return tuple(midnight + HOUR * step for step in range(HOURS_PER_DAY))


def billing_month_hours(year: int, month: int) -> tuple[datetime, ...]:
    """Every hour start of one billing month, in order."""
    hours: list[datetime] = []
    day = billing_month_start(year, month)
    end = billing_month_end(year, month)
    while day <= end:
        hours.extend(billing_day_hours(day))
        day += timedelta(days=1)
    return tuple(hours)


def shift_years(moment: datetime, years: int) -> datetime | None:
    """The same clock time ``years`` earlier, or ``None`` when it does not exist.

    ``29 February`` has no counterpart in a common year; the sample is skipped
    and counted, never moved to a neighbouring date.
    """
    try:
        return moment.replace(year=moment.year - years)
    except ValueError:
        return None


# --- rows and series ------------------------------------------------------


@dataclass(frozen=True)
class HourRow:
    """One exported hour: its interval count, mean price and administered share."""

    hour_start: datetime
    intervals: int
    mean: float
    ap_intervals: int
    ap_known: bool

    @property
    def billing_month(self) -> str:
        year, month = billing_month_of(self.hour_start)
        return billing_month_label(year, month)


@dataclass(frozen=True)
class Series:
    """One price series: the regional reference or one de-identified load node."""

    key: str
    kind: str
    label: str
    region: str
    source: str
    rows: Mapping[datetime, HourRow]
    hours: tuple[datetime, ...] = ()
    has_ap_flags: bool = False

    def __post_init__(self) -> None:
        if not self.hours:
            object.__setattr__(self, "hours", tuple(sorted(self.rows)))
        if not self.has_ap_flags:
            object.__setattr__(
                self, "has_ap_flags", any(row.ap_known for row in self.rows.values())
            )

    def latest_at_or_before(self, limit: datetime) -> HourRow | None:
        """The newest exported row whose hour ended at or before ``limit``."""
        index = bisect_right(self.hours, limit) - 1
        if index < 0:
            return None
        return self.rows[self.hours[index]]

    @property
    def first_day(self) -> date:
        return min(self.rows).date()

    @property
    def last_day(self) -> date:
        return max(self.rows).date()

    def row(self, hour_start: datetime) -> HourRow | None:
        return self.rows.get(hour_start)

    def present(self, hours: Iterable[datetime]) -> tuple[HourRow, ...]:
        """The rows that exist for these hours; a missing hour is simply absent."""
        found = []
        for hour in hours:
            row = self.rows.get(hour)
            if row is not None:
                found.append(row)
        return tuple(found)

    def intervals(self, hours: Iterable[datetime]) -> int:
        return sum(row.intervals for row in self.present(hours))

    def expected_intervals(self, hours: Iterable[datetime]) -> int:
        return INTERVALS_PER_HOUR * len(tuple(hours))

    def missing_hours(self, hours: Iterable[datetime]) -> tuple[datetime, ...]:
        """The hours of a window with no exported row; they are never filled."""
        return tuple(hour for hour in hours if hour not in self.rows)

    def is_complete(self, hours: Sequence[datetime]) -> bool:
        """True when every hour is present and the window carries every interval.

        A day whose rows cover 564 intervals, or a month short by 84, fails this
        and is excluded as a whole: scoring the part that is there would compare
        a partial window against a full-horizon forecast.
        """
        return not self.missing_hours(hours) and (
            self.intervals(hours) == INTERVALS_PER_HOUR * len(hours)
        )

    def window_mean(self, hours: Sequence[datetime]) -> float:
        """The interval-weighted mean over the present rows of a window.

        Weighting by the five-minute intervals each row carries makes the result
        exact for a complete window and honest for a partial one; no row is
        invented for an hour that is not there.
        """
        rows = self.present(hours)
        weight = sum(row.intervals for row in rows)
        if not weight:
            raise SeriesError("EMPTY_WINDOW", "no exported row inside the window")
        return sum(row.mean * row.intervals for row in rows) / weight


@dataclass(frozen=True)
class Marks:
    """What the bytes say about the series, and the recorded pricing marks."""

    absent_months: tuple[str, ...]
    short_months: tuple[str, ...]
    irregular_days: tuple[str, ...]
    ap_all_months: tuple[str, ...]
    ap_mixed_months: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "absent_months": list(self.absent_months),
            "short_months": list(self.short_months),
            "irregular_days": list(self.irregular_days),
            "administered_pricing": {
                "all": list(self.ap_all_months),
                "mixed": list(self.ap_mixed_months),
            },
        }


# --- loading --------------------------------------------------------------


def _check_header(reader: csv.DictReader, path: Path, required: Sequence[str]) -> None:
    missing = [name for name in required if name not in (reader.fieldnames or ())]
    if missing:
        raise SeriesError("MALFORMED_EXPORT", f"{path.name} has no column {missing[0]}")


def _load(path: Path, value_column: str, key_column: str) -> dict[str, list[dict]]:
    if not path.exists():
        raise SeriesError("MISSING_EXPORT", str(path))
    grouped: dict[str, list[dict]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _check_header(reader, path, ("byear", "bmonth", key_column, "hour_start", "n5", value_column))
        for row in reader:
            try:
                byear, bmonth = int(row["byear"]), int(row["bmonth"])
                hour_start = datetime.fromisoformat(row["hour_start"])
                intervals = int(row["n5"])
                mean = float(row[value_column])
            except (KeyError, ValueError) as error:
                raise SeriesError("MALFORMED_EXPORT", f"{path.name}: {error}") from error
            if intervals <= 0:
                raise SeriesError("MALFORMED_EXPORT", f"{path.name}: non-positive n5")
            if billing_month_of(hour_start) != (byear, bmonth):
                raise SeriesError(
                    "CLOCK_MISMATCH",
                    f"{path.name}: {row['hour_start']} is not in billing month "
                    f"{billing_month_label(byear, bmonth)}",
                )
            item = {
                "hour_start": hour_start,
                "intervals": intervals,
                "mean": mean,
                "ap": int(row.get("ap5", 0) or 0),
                "ap_known": "ap5" in row,
                "region": (row.get("region") or "").strip(),
            }
            grouped.setdefault(row[key_column], []).append(item)
    return grouped


def load_regional(path: str | Path) -> tuple[Series, ...]:
    """Read the regional load-weighted export into one series per region."""
    path = Path(path)
    grouped = _load(path, "lwap_mean", "region_name")
    series = []
    for key in REGIONAL_KEYS:
        items = grouped.get(key)
        if not items:
            raise SeriesError("MISSING_REGION", f"{path.name} has no rows for {key}")
        rows = {}
        for item in items:
            if item["hour_start"] in rows:
                raise SeriesError("DUPLICATE_HOUR", f"{path.name}: {item['hour_start']} twice")
            rows[item["hour_start"]] = HourRow(
                hour_start=item["hour_start"],
                intervals=item["intervals"],
                mean=item["mean"],
                ap_intervals=0,  # the regional export carries no pricing flag
                ap_known=False,
            )
        series.append(
            Series(key=key, kind="regional", label=REGIONAL_LABELS[key], region=key,
                   source=path.name, rows=rows)
        )
    return tuple(series)


def load_nodal(path: str | Path) -> tuple[Series, ...]:
    """Read the de-identified load-node export into one series per node alias."""
    path = Path(path)
    grouped = _load(path, "lmp_mean", "resource_name")
    series = []
    for key in sorted(grouped):
        rows = {}
        region = ""
        for item in grouped[key]:
            if item["hour_start"] in rows:
                raise SeriesError("DUPLICATE_HOUR", f"{path.name}: {item['hour_start']} twice")
            region = region or item.get("region", "")
            rows[item["hour_start"]] = HourRow(
                hour_start=item["hour_start"],
                intervals=item["intervals"],
                mean=item["mean"],
                ap_intervals=item["ap"],
                ap_known=bool(item["ap_known"]),
            )
        series.append(
            Series(key=key, kind="nodal", label=f"load node {key} (de-identified)",
                   region=region, source=path.name, rows=rows)
        )
    return tuple(series)


def row_count(path: str | Path) -> int:
    """Data rows in an export (header not counted)."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


# --- digests --------------------------------------------------------------


def digest_file(path: str | Path) -> str:
    """Lowercase SHA-256 hex of a file's bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_digests(path: str | Path) -> dict[str, str]:
    """The ``{path: sha256}`` record written beside the exports."""
    with Path(path).open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in loaded.items()
    ):
        raise SeriesError("MALFORMED_DIGESTS", str(path))
    return loaded


def verify_inputs(paths: Sequence[str | Path], digests: Mapping[str, str]) -> list[dict]:
    """Check each file against the digest record; a mismatch raises.

    The record's keys are the repository-relative hints of the export record;
    the comparison accepts either the hint or the file's own path, so a run in a
    task worktree (where ``.local/price`` is linked) checks the same bytes.
    """
    report = []
    for entry in paths:
        path = Path(entry)
        actual = digest_file(path)
        expected = None
        for hint, wanted in digests.items():
            if Path(hint).name == path.name:
                expected = wanted
                break
        if expected is None:
            raise SeriesError("DIGEST_NOT_RECORDED", str(path))
        if expected != actual:
            raise SeriesError("DIGEST_MISMATCH", f"{path.name}: {actual} != {expected}")
        report.append({"file": path.name, "sha256": actual, "rows": row_count(path)})
    return report


# --- marks ----------------------------------------------------------------


def derive_marks(
    series: Series,
    administered: Sequence[tuple[str, str]] = ADMINISTERED_PRICING_MONTHS,
) -> Marks:
    """Report the absent months, short months and irregular days of one series.

    The month range is the series' own first to last present month, so the marks
    describe the export and not an assumption about when prices began. A nodal
    series marks administered pricing from its own per-hour flag counts; a
    regional series uses the recorded month table, because it has no flag.
    """
    present = {}
    for row in series.rows.values():
        label = row.billing_month
        entry = present.setdefault(label, [0, 0])
        entry[0] += row.intervals
        entry[1] += 1
    labels = sorted(present)
    first_year, first_month = month_of_label(labels[0])
    last_year, last_month = month_of_label(labels[-1])
    absent, short = [], []
    year, month = first_year, first_month
    while (year, month) <= (last_year, last_month):
        label = billing_month_label(year, month)
        expected = INTERVALS_PER_DAY * billing_month_days(year, month)
        if label not in present:
            absent.append(label)
        elif present[label][0] != expected:
            short.append(label)
        month += 1
        if month == 13:
            year, month = year + 1, 1

    by_day: dict[str, int] = {}
    for row in series.rows.values():
        day = row.hour_start.date().isoformat()
        by_day[day] = by_day.get(day, 0) + row.intervals
    irregular = sorted(day for day, count in by_day.items() if count != INTERVALS_PER_DAY)

    if series.has_ap_flags:
        by_month: dict[str, list[int]] = {}
        for row in series.rows.values():
            entry = by_month.setdefault(row.billing_month, [0, 0])
            entry[0] += row.ap_intervals
            entry[1] += row.intervals
        ap_all = sorted(
            label for label, (ap, total) in by_month.items() if total and ap == total
        )
        ap_mixed = sorted(
            label for label, (ap, total) in by_month.items() if 0 < ap < total
        )
    else:
        ap_all = sorted(label for label, state in administered if state == "all")
        ap_mixed = sorted(label for label, state in administered if state == "mixed")
    return Marks(
        absent_months=tuple(absent),
        short_months=tuple(short),
        irregular_days=tuple(irregular),
        ap_all_months=tuple(ap_all),
        ap_mixed_months=tuple(ap_mixed),
    )


__all__ = [
    "ADMINISTERED_PRICING_MONTHS",
    "HOURS_PER_DAY",
    "HOUR",
    "INTERVALS_PER_DAY",
    "INTERVALS_PER_HOUR",
    "Marks",
    "NODAL_CSV",
    "REGIONAL_CSV",
    "REGIONAL_KEYS",
    "REGIONAL_LABELS",
    "Series",
    "SeriesError",
    "WEEK_HOURS",
    "HourRow",
    "billing_day_hours",
    "billing_month_days",
    "billing_month_end",
    "billing_month_hours",
    "billing_month_label",
    "billing_month_of",
    "billing_month_start",
    "derive_marks",
    "digest_file",
    "load_digests",
    "load_nodal",
    "load_regional",
    "month_of_label",
    "row_count",
    "shift_years",
    "verify_inputs",
]
