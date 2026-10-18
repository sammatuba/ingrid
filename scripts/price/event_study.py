#!/usr/bin/env python3
"""The OUT-2 event study, offline: forced outages against the final hourly regional price.

Reads up to three exports, each by SHA-256 (checked against a digest record when one is given):

* the forced outage records written by query 1 of ``scripts/price/event_study.sql``
  (``outages_forced.csv``);
* the final hourly regional series ``lwap_final_hourly.csv`` (PRICE-1, ``src/price/series.py``),
  the only source of a price level;
* optionally the hourly mean regional demand written by query 2 of the same file
  (``demand_hourly.csv``), used only as the response's denominator.

For each event, the regional final price at each of the first ``--hours-after`` clock hours of
the outage is compared with the same clock hour on days of the same weekday class (weekday or
weekend) in the ``--baseline-weeks`` ISO weeks around that hour's own week (half before, half
after, the hour's week excluded). An event that another forced outage of its region overlaps in
a measured hour is left out, because the two would share one price change. The event's response
is the mean of the hourly changes divided by the MW lost over the region's mean demand in those
hours (``--demand``), or by the MW lost alone without it. Responses pool per region and size
class into the median, p10, p90 and the count; a cell below ``--min-events`` is exploratory.

    /usr/bin/python3 scripts/price/event_study.py \\
        --outages .local/price/outages_forced.csv \\
        --final .local/price/lwap_final_hourly.csv \\
        --demand .local/price/demand_hourly.csv \\
        --digests .local/price/digests.json \\
        --out .local/price/response.json

The level comes from the final series only. The reader refuses a file whose header is not the
final export's, so a real-time file cannot be read for a level; the demand file has no price
column and is read only for the denominator. The record is written under ``.local/`` or outside
the repository, never into the tree: a path inside the repository that is not under ``.local/``
is refused, exactly as ``scripts/price/impact.py`` refuses. ``--series-only`` reads the final
series alone and prints counts and its digest, never a price. ``--print-query outages|demand``
prints one of the two export statements for ``bq query``.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.price.impact import ImpactError, refuse_output_inside_the_tree  # noqa: E402
from src.price.response import (  # noqa: E402
    BASIS,
    DEMAND_SOURCE,
    EXPECTATION,
    KIND,
    LABEL_EXPLORATORY,
    LABEL_MEASURED,
    MW_LOST_BASIS,
    NORMALIZATIONS,
    VERSION,
    ResponseError,
    record_digest,
    record_text,
    validate,
)
from src.price.scorecard import quantile  # noqa: E402
from src.price.series import (  # noqa: E402
    ADMINISTERED_PRICING_MONTHS,
    HOUR,
    Series,
    SeriesError,
    billing_month_label,
    billing_month_of,
    digest_file,
    load_digests,
    load_regional,
    row_count,
    verify_inputs,
)

SQL_PATH = ROOT / "scripts" / "price" / "event_study.sql"
OUTAGE_HEADER = (
    "run", "resource_name", "region_code", "status", "outage_class", "mw_lost", "start_manila",
    "end_manila", "start_utc", "end_utc", "first_seen_manila", "first_seen_utc",
    "first_seen_any_run_manila", "lead_hours", "duration_hours", "n_revisions",
)
FINAL_HEADER = ("byear", "bmonth", "region_name", "hour_start", "n5", "lwap_mean", "lwap_min",
                "lwap_max")
DEMAND_HEADER = ("region_name", "hour_start", "n5", "demand_mw_mean")
LABEL_SIDECAR = "synthetic-label.json"
EVENT_REGIONS = ("CLUZ", "CVIS", "CMIN")
UTC_OFFSET = timedelta(hours=8)
#: file-name words that mark a real-time file; such a file is refused before its header is read
REAL_TIME_NAME_MARKS = ("rtd", "realtime", "real_time", "real-time", "fivemin_rt")
#: a first sighting this close after the start is the least certain "forced" (finding 3, round 1)
NEAR_START_HOURS = 1.0

DEFAULTS = {
    "hours_after": 6,
    "baseline_weeks": 4,
    "min_baseline_hours": 3,
    "min_events_per_cell": 10,
    "min_mw": 50.0,
    "size_edges_mw": (50.0, 150.0, 300.0),
}


class StudyError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --- the export statements ---------------------------------------------------------


def export_query(name: str, path: Path = SQL_PATH) -> str:
    """One of the two statements of ``event_study.sql``, between its BEGIN and END markers."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^-- BEGIN {name}\n(.*?)^-- END {name}\n", text, re.M | re.S)
    if match is None:
        raise StudyError("NO_QUERY", name)
    return match.group(1)


# --- readers -------------------------------------------------------------------------


def _header(path: Path) -> tuple[str, ...]:
    if not path.exists():
        raise StudyError("MISSING_EXPORT", str(path))
    with path.open(newline="", encoding="utf-8") as handle:
        first = next(csv.reader(handle), None)
    return tuple(first or ())


def read_final_series(path: str | Path) -> tuple[Series, ...]:
    """The final hourly regional series, refused unless the file is the final export.

    The header must be exactly the PRICE-1 regional export's. Any other shape, the real-time
    interval files included, is refused before a row is read; so is a file whose name marks it
    real-time.
    """
    path = Path(path)
    lowered = path.name.lower()
    if any(mark in lowered for mark in REAL_TIME_NAME_MARKS):
        raise StudyError("REAL_TIME_REFUSED", f"{path.name}: the level comes from the final series")
    header = _header(path)
    if header != FINAL_HEADER:
        raise StudyError(
            "NOT_THE_FINAL_SERIES",
            f"{path.name}: header {','.join(header)!r} is not the final regional export's",
        )
    return load_regional(path)


def read_demand(path: str | Path) -> dict[tuple[str, datetime], float]:
    """The hourly mean regional demand of query 2; refused unless its header is exactly that.

    The file has no price column by construction; it is read only for the denominator.
    """
    path = Path(path)
    if _header(path) != DEMAND_HEADER:
        raise StudyError("MALFORMED_EXPORT", f"{path.name}: header is not the demand export's")
    demand: dict[tuple[str, datetime], float] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            where = f"{path.name} line {number}"
            if row["region_name"] not in EVENT_REGIONS:
                raise StudyError("UNKNOWN_REGION", f"{where}: {row['region_name']}")
            try:
                hour = datetime.fromisoformat(row["hour_start"])
                value = float(row["demand_mw_mean"])
                intervals = int(row["n5"])
            except ValueError as error:
                raise StudyError("MALFORMED_EXPORT", f"{where}: {error}") from error
            if hour.minute or hour.second or intervals <= 0 or value <= 0:
                raise StudyError("MALFORMED_EXPORT", f"{where}: not an hour, or no demand")
            key = (row["region_name"], hour)
            if key in demand:
                raise StudyError("DUPLICATE_HOUR", where)
            demand[key] = value
    return demand


def _stamp(text: str, path: Path, column: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except ValueError as error:
        raise StudyError("MALFORMED_EXPORT", f"{path.name}: {column} {text!r}") from error


def read_outages(path: str | Path) -> list[dict]:
    """The forced outage export, refused unless its header and every row keep the SQL's rules."""
    path = Path(path)
    header = _header(path)
    if header != OUTAGE_HEADER:
        raise StudyError("MALFORMED_EXPORT",
                         f"{path.name}: header is not the event_study.sql export's")
    events = []
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            where = f"{path.name} line {number}"
            if row["status"] != "OUT" or row["outage_class"] != "forced":
                raise StudyError("NOT_FORCED", where)
            if row["region_code"] not in EVENT_REGIONS:
                raise StudyError("UNKNOWN_REGION", f"{where}: {row['region_code']}")
            try:
                mw = float(row["mw_lost"])
            except ValueError as error:
                raise StudyError("MALFORMED_EXPORT", f"{where}: mw_lost") from error
            if mw <= 0:
                raise StudyError("MALFORMED_EXPORT", f"{where}: mw_lost not positive")
            stamps = {name: _stamp(row[name], path, name) for name in (
                "start_manila", "end_manila", "start_utc", "end_utc", "first_seen_manila",
                "first_seen_utc", "first_seen_any_run_manila")}
            for manila, utc in (("start_manila", "start_utc"), ("end_manila", "end_utc"),
                                ("first_seen_manila", "first_seen_utc")):
                if stamps[manila] - UTC_OFFSET != stamps[utc]:
                    raise StudyError("CLOCK_MISMATCH", f"{where}: {utc} is not {manila} - 8 h")
            if stamps["end_manila"] <= stamps["start_manila"]:
                raise StudyError("MALFORMED_EXPORT", f"{where}: end not after start")
            if stamps["first_seen_any_run_manila"] < stamps["start_manila"]:
                raise StudyError("NOT_FORCED", f"{where}: carried before its start")
            events.append({
                "line": number,
                "region": row["region_code"],
                "mw_lost": mw,
                "start": stamps["start_manila"],
                "end": stamps["end_manila"],
                "known_at": stamps["first_seen_manila"],
            })
    return events


def read_label(paths: Sequence[Path]) -> str | None:
    """The label of the sidecar ``synthetic-label.json`` beside an input that it lists.

    A file whose name says ``synthetic`` but that no sidecar beside it lists is refused: a
    fixture must carry its label, and a real export never says ``synthetic``.
    """
    label = None
    for path in paths:
        sidecar = path.parent / LABEL_SIDECAR
        listed = False
        if sidecar.exists():
            with sidecar.open(encoding="utf-8") as handle:
                loaded = json.load(handle)
            if path.name in loaded.get("files", ()):
                listed = True
                if not isinstance(loaded.get("label"), str) or not loaded["label"]:
                    raise StudyError("MALFORMED_LABEL", str(sidecar))
                if label is not None and label != loaded["label"]:
                    raise StudyError("MALFORMED_LABEL", "inputs carry two labels")
                label = loaded["label"]
        if "synthetic" in path.name.lower() and not listed:
            raise StudyError("UNLABELLED_SYNTHETIC", path.name)
    return label


# --- the method -------------------------------------------------------------------------


def size_classes(edges: Sequence[float]) -> list[tuple[str, float, float | None]]:
    classes = []
    for index, low in enumerate(edges):
        high = edges[index + 1] if index + 1 < len(edges) else None
        name = f"{low:g}+ MW" if high is None else f"{low:g} to {high:g} MW"
        classes.append((name, float(low), None if high is None else float(high)))
    return classes


def size_class_of(mw: float, classes) -> tuple[str, float, float | None] | None:
    for entry in classes:
        _, low, high = entry
        if mw >= low and (high is None or mw < high):
            return entry
    return None


def first_full_hour(moment: datetime) -> datetime:
    floor = moment.replace(minute=0, second=0, microsecond=0)
    return floor if floor == moment else floor + HOUR


def measured_hours(event: Mapping, hours_after: int) -> list[datetime]:
    """The clock hours measured for an event: whole hours from its start, inside the outage."""
    hours = []
    hour = first_full_hour(event["start"])
    while len(hours) < hours_after and hour + HOUR <= event["end"]:
        hours.append(hour)
        hour += HOUR
    return hours


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def baseline_days(hour_day: date, weeks: int, weekend: bool) -> list[date]:
    """Days of one weekday class in the ``weeks // 2`` ISO weeks either side of a day's week."""
    monday = hour_day - timedelta(days=hour_day.weekday())
    days = []
    half = weeks // 2
    for offset in list(range(-half, 0)) + list(range(1, half + 1)):
        start = monday + timedelta(weeks=offset)
        for step in range(7):
            day = start + timedelta(days=step)
            if is_weekend(day) == weekend:
                days.append(day)
    return days


def baseline_candidates(hour: datetime, weeks: int) -> list[datetime]:
    """The baseline hours of one measured hour, keyed to that hour's own date and ISO week.

    An outage that starts late on a Sunday measures its Monday hours against the weeks around
    that Monday's week, never against that Monday's own week (rework round 1, finding 2).
    """
    return [datetime(day.year, day.month, day.day, hour.hour)
            for day in baseline_days(hour.date(), weeks, is_weekend(hour.date()))]


def administered_months(table=ADMINISTERED_PRICING_MONTHS) -> frozenset[str]:
    """Billing months with any administered pricing; the regional file carries no flag."""
    return frozenset(label for label, _ in table)


def month_of(hour: datetime) -> str:
    return billing_month_label(*billing_month_of(hour))


def affected_hours(events) -> dict[str, set[datetime]]:
    """Per region, every clock hour that overlaps any forced outage; kept out of baselines."""
    hit: dict[str, set[datetime]] = {}
    for event in events:
        hour = event["start"].replace(minute=0, second=0, microsecond=0)
        while hour < event["end"]:
            hit.setdefault(event["region"], set()).add(hour)
            hour += HOUR
    return hit


def overlaps_another(event: Mapping, hours: Sequence[datetime], events: Sequence[Mapping]) -> bool:
    """True when another forced outage of the region is out during one of the measured hours."""
    for other in events:
        if other is event or other["region"] != event["region"]:
            continue
        if any(other["start"] < hour + HOUR and other["end"] > hour for hour in hours):
            return True
    return False


def baseline_for(series: Series, hour: datetime, weeks: int, excluded: set[datetime],
                 ap_months: frozenset[str]) -> list[float]:
    values = []
    for candidate in baseline_candidates(hour, weeks):
        if candidate in excluded or month_of(candidate) in ap_months:
            continue
        row = series.row(candidate)
        if row is not None:
            values.append(row.mean)
    return values


def event_response(event: Mapping, series: Series, params: Mapping, excluded: set[datetime],
                   ap_months: frozenset[str], demand: Mapping | None,
                   events: Sequence[Mapping] = ()) -> tuple[dict | None, str]:
    """One event's response, or ``None`` with the reason it was left out.

    ``events`` is every forced outage of the export; an event that another one of its region
    overlaps in a measured hour is left out as ``overlapping_outage``.
    """
    hours = measured_hours(event, params["hours_after"])
    if not hours:
        return None, "no_full_clock_hour"
    if overlaps_another(event, hours, events):
        return None, "overlapping_outage"
    hours = [hour for hour in hours if month_of(hour) not in ap_months]
    if not hours:
        return None, "administered_pricing"
    priced = [hour for hour in hours if series.row(hour) is not None]
    if not priced:
        return None, "outside_final_series"
    deltas, demands = [], []
    for hour in priced:
        base = baseline_for(series, hour, params["baseline_weeks"], excluded, ap_months)
        if len(base) < params["min_baseline_hours"]:
            continue
        deltas.append(series.row(hour).mean - sum(base) / len(base))
        if demand is not None:
            value = demand.get((event["region"], hour))
            if value is not None:
                demands.append(value)
    if not deltas:
        return None, "thin_baseline"
    delta = sum(deltas) / len(deltas)
    if demand is not None:
        if not demands:
            return None, "no_demand"
        mean_demand = sum(demands) / len(demands)
        response = delta / (event["mw_lost"] / mean_demand)
    else:
        mean_demand = None
        response = delta / event["mw_lost"]
    return {"delta": delta, "response": response, "hours_used": len(deltas),
            "demand_mw": mean_demand}, "used"


def _round(value: float) -> float:
    return round(value, 6)


def _spread(values: Sequence[float]) -> dict | None:
    if not values:
        return None
    ordered = sorted(values)
    return {"median": _round(quantile(ordered, 0.5)), "p10": _round(quantile(ordered, 0.1)),
            "p90": _round(quantile(ordered, 0.9)), "max": _round(ordered[-1])}


def known_at_limits(events: Sequence[Mapping]) -> dict:
    """From the export's known_at: how close to the start each event was first seen.

    The export holds no event first seen before its start (the forced rule). An event first seen
    less than ``NEAR_START_HOURS`` after its start is the least certain "forced": a planned
    outage whose start moved by minutes would land here. The lag is known_at minus start.
    """
    lags = [(event["known_at"] - event["start"]).total_seconds() / 3600.0 for event in events]
    near = sum(1 for lag in lags if lag < NEAR_START_HOURS)
    return {
        "events": len(lags),
        "first_seen_within_1h_of_start": near,
        "share_first_seen_within_1h_of_start": _round(near / len(lags)) if lags else None,
        "reporting_lag_hours": _spread(lags),
    }


def run_study(events: Sequence[Mapping], series: Sequence[Series], params: Mapping,
              demand: Mapping | None = None) -> tuple[list[dict], dict, str]:
    """Every event's response, pooled into cells; returns ``(cells, counts, normalization)``."""
    by_region = {item.key: item for item in series}
    classes = size_classes(params["size_edges_mw"])
    ap_months = administered_months()
    affected = affected_hours(events)
    pooled: dict[tuple[str, str], dict] = {}
    excluded_counts: dict[str, int] = {}
    used = 0
    for event in events:
        cls = size_class_of(event["mw_lost"], classes)
        if event["mw_lost"] < params["min_mw"] or cls is None:
            reason, result = "below_min_mw", None
        else:
            result, reason = event_response(event, by_region[event["region"]], params,
                                            affected.get(event["region"], set()), ap_months,
                                            demand, events)
        if result is None:
            excluded_counts[reason] = excluded_counts.get(reason, 0) + 1
            continue
        used += 1
        name, low, high = cls
        cell = pooled.setdefault((event["region"], name), {
            "low": low, "high": high, "responses": [], "deltas": [], "mws": [], "hours": [],
            "demand": []})
        cell["responses"].append(result["response"])
        cell["deltas"].append(result["delta"])
        cell["mws"].append(event["mw_lost"])
        cell["hours"].append(result["hours_used"])
        if result["demand_mw"] is not None:
            cell["demand"].append(result["demand_mw"])
    normalization = "per_share_of_demand" if demand is not None else "per_mw_lost"
    order = {name: index for index, (name, _, _) in enumerate(classes)}
    cells = []
    for region in EVENT_REGIONS:
        for name in sorted((key[1] for key in pooled if key[0] == region), key=order.get):
            data = pooled[(region, name)]
            responses = sorted(data["responses"])
            count = len(responses)
            small = count < params["min_events_per_cell"]
            deltas = _spread(data["deltas"])
            deltas.pop("max")
            cells.append({
                "region": region,
                "size_class": name,
                "mw_low": data["low"],
                "mw_high": data["high"],
                "count": count,
                "median": _round(quantile(responses, 0.5)),
                "p10": _round(quantile(responses, 0.1)),
                "p90": _round(quantile(responses, 0.9)),
                "small_sample": small,
                "min_events": params["min_events_per_cell"],
                "label": LABEL_EXPLORATORY if small else LABEL_MEASURED,
                "units": NORMALIZATIONS[normalization],
                "basis": BASIS,
                "measured_hours": params["hours_after"],
                "delta_php_mwh": deltas,
                "mw_lost_median": _round(quantile(sorted(data["mws"]), 0.5)),
                "demand_mw_median": (_round(quantile(sorted(data["demand"]), 0.5))
                                     if data["demand"] else None),
                "hours_used_median": _round(quantile(sorted(data["hours"]), 0.5)),
            })
    counts = {
        "events_read": len(events),
        "events_used": used,
        "events_excluded": dict(sorted(excluded_counts.items())),
    }
    return cells, counts, normalization


def input_path(path: Path, root: Path | None = None) -> str:
    """The input's path as the record stores it: the same in every checkout (rework round 2).

    Whatever the caller typed (relative, absolute, through a worktree's ``.local/price`` link or
    through the link's target), the record holds the path relative to the repository root:
    ``.local/price/<name>`` for an export, ``tests/fixtures/...`` for a fixture. A file outside
    every checkout is stored as ``external:<name>``, never by its machine path, so the record's
    digest depends on the bytes read and not on where the run happened.
    """
    root = Path(ROOT if root is None else root)
    absolute = Path(os.path.abspath(path))
    for base in (root, root.resolve()):
        try:
            return absolute.relative_to(base).as_posix()
        except ValueError:
            pass
    resolved = absolute.resolve()
    for relative in (Path(".local") / "price", Path(".local")):
        linked = root / relative
        if linked.exists():
            try:
                return (relative / resolved.relative_to(linked.resolve())).as_posix()
            except ValueError:
                pass
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"external:{absolute.name}"


def build_record(outages_path: str | Path, final_path: str | Path, params: Mapping,
                 digests: Mapping | None = None, demand_path: str | Path | None = None) -> dict:
    outages_path, final_path = Path(outages_path), Path(final_path)
    demand_path = Path(demand_path) if demand_path is not None else None
    if params["baseline_weeks"] < 2 or params["baseline_weeks"] % 2:
        raise StudyError("BAD_PARAMETER", "baseline_weeks must be even and at least 2")
    if params["hours_after"] < 1 or params["min_events_per_cell"] < 1:
        raise StudyError("BAD_PARAMETER", "hours_after and min_events_per_cell must be positive")
    if tuple(params["size_edges_mw"])[0] != params["min_mw"]:
        raise StudyError("BAD_PARAMETER", "the first size edge must equal min_mw")
    series = read_final_series(final_path)
    events = read_outages(outages_path)
    demand = read_demand(demand_path) if demand_path is not None else None
    roles = [("outages", outages_path), ("final_series", final_path)]
    if demand_path is not None:
        roles.append(("demand", demand_path))
    if digests is not None:
        verify_inputs([path for _, path in roles], digests)
    sidecar_label = read_label([path for _, path in roles])
    inputs = [{"role": role, "path": input_path(path), "file": path.name,
               "rows": row_count(path), "sha256": digest_file(path)} for role, path in roles]
    cells, counts, normalization = run_study(events, series, params, demand)
    label = sidecar_label or (
        "measured on the snapshot exports by digest: " + ", ".join(
            f"{entry['file']} ({entry['rows']} rows, {entry['sha256'][:8]})" for entry in inputs))
    record = {
        "kind": KIND,
        "version": VERSION,
        "label": label,
        "basis": BASIS,
        "normalization": normalization,
        "units": NORMALIZATIONS[normalization],
        "denominator": (f"the region's mean demand over the measured hours, from {demand_path.name} "
                        f"({DEMAND_SOURCE})" if demand_path is not None
                        else "none: the MW lost alone, no demand export was given"),
        "mw_lost_basis": MW_LOST_BASIS,
        "inputs": inputs,
        "parameters": {
            "hours_after": params["hours_after"],
            "baseline_weeks": params["baseline_weeks"],
            "baseline_rule": (
                "for each measured hour: the same clock hour on every day of the same weekday "
                "class (Monday to Friday, or Saturday and Sunday) in the baseline_weeks/2 ISO weeks "
                "before and after that hour's own ISO week, which is excluded; hours overlapping "
                "any forced outage of the region and administered-pricing months left out; plain "
                "mean of the hourly final prices"),
            "measured_hour_rule": (
                "the whole clock hours from the first hour starting at or after start_manila, "
                "while the hour ends at or before end_manila, at most hours_after"),
            "overlap_rule": (
                "an event that another forced outage of the same region overlaps in any measured "
                "hour is left out (overlapping_outage): the two would share one price change"),
            "min_baseline_hours": params["min_baseline_hours"],
            "min_events_per_cell": params["min_events_per_cell"],
            "min_mw": params["min_mw"],
            "size_edges_mw": list(params["size_edges_mw"]),
            "response_rule": (
                "the mean over the measured hours of (final price minus baseline), divided by "
                "the MW lost" + (" over the region's mean demand in those hours"
                                 if demand is not None else "")),
            "pooled_statistics": "median, p10, p90 (linear interpolation) and count per cell",
            "administered_pricing_months": sorted(administered_months()),
        },
        "counts": counts,
        "cells": cells,
        "limits": {
            "known_at": known_at_limits(events),
            "forced_rule": (
                "forced means no schedule run carried the same unit and the exact same start "
                "before that start; a planned outage whose start moved would count as forced, and "
                "the events first seen within one hour of their start are the least certain"),
            "mw_lost": MW_LOST_BASIS,
            "not_separated": "planned outages, public holidays and the real-time timing check",
        },
        "timing_check": ("not run: the real-time series may only check the timing of a response, "
                         "and this run did not read it"),
        "expectation": EXPECTATION,
    }
    return dict(validate(record))


# --- the series-only check -------------------------------------------------------------


def series_counts(final_path: str | Path, params: Mapping) -> dict:
    """Counts and the digest of the final series, and how many hours could carry a baseline.

    An hour "could carry a baseline" when at least ``min_baseline_hours`` same-class hours
    exist in the surrounding weeks outside administered-pricing months (no outage exclusion:
    the outage export is not read). Counts only.
    """
    final_path = Path(final_path)
    series = read_final_series(final_path)
    ap_months = administered_months()
    regions = {}
    for item in series:
        hours = item.hours
        ready = 0
        for hour in hours:
            if month_of(hour) in ap_months:
                continue
            base = baseline_for(item, hour, params["baseline_weeks"], set(), ap_months)
            if len(base) >= params["min_baseline_hours"]:
                ready += 1
        regions[item.key] = {
            "hours": len(hours),
            "first_hour": hours[0].isoformat(sep=" "),
            "last_hour": hours[-1].isoformat(sep=" "),
            "hours_with_baseline": ready,
        }
    return {"file": final_path.name, "rows": row_count(final_path),
            "sha256": digest_file(final_path), "regions": regions}


# --- command line ---------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outages", help="the forced outage export (event_study.sql query 1)")
    parser.add_argument("--final", help="the final hourly regional series")
    parser.add_argument("--demand", help="the hourly regional demand export (query 2), the denominator")
    parser.add_argument("--digests", help="the export digest record to check every file against")
    parser.add_argument("--out", help="write the response record here (under .local/ or outside)")
    parser.add_argument("--hours-after", type=int, default=DEFAULTS["hours_after"])
    parser.add_argument("--baseline-weeks", type=int, default=DEFAULTS["baseline_weeks"])
    parser.add_argument("--min-baseline-hours", type=int, default=DEFAULTS["min_baseline_hours"])
    parser.add_argument("--min-events", type=int, default=DEFAULTS["min_events_per_cell"])
    parser.add_argument("--min-mw", type=float, default=DEFAULTS["min_mw"])
    parser.add_argument("--size-edges", default=",".join(f"{v:g}" for v in DEFAULTS["size_edges_mw"]),
                        help="comma-separated MW edges; the first equals --min-mw")
    parser.add_argument("--series-only", action="store_true",
                        help="read the final series alone and print counts and its digest")
    parser.add_argument("--print-query", choices=("outages", "demand"),
                        help="print one export statement of event_study.sql for bq query")
    return parser.parse_args(argv)


def params_of(args: argparse.Namespace) -> dict:
    return {
        "hours_after": args.hours_after,
        "baseline_weeks": args.baseline_weeks,
        "min_baseline_hours": args.min_baseline_hours,
        "min_events_per_cell": args.min_events,
        "min_mw": args.min_mw,
        "size_edges_mw": tuple(float(part) for part in args.size_edges.split(",") if part),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    params = params_of(args)
    try:
        if args.print_query:
            sys.stdout.write(export_query(args.print_query))
            return 0
        if not args.final:
            raise StudyError("USAGE", "--final is required")
        if args.series_only:
            counts = series_counts(args.final, params)
            print(f"final series {counts['file']}: {counts['rows']} rows, sha256 {counts['sha256']}")
            for key, entry in counts["regions"].items():
                print(f"  {key}: {entry['hours']} hours, {entry['first_hour']} to "
                      f"{entry['last_hour']}, {entry['hours_with_baseline']} with a baseline")
            return 0
        if not args.outages or not args.out:
            raise StudyError("USAGE", "--outages and --out are required unless --series-only")
        out = refuse_output_inside_the_tree(args.out)
        digests = load_digests(args.digests) if args.digests else None
        record = build_record(args.outages, args.final, params, digests, args.demand)
    except (StudyError, SeriesError, ResponseError, ImpactError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    print(f"basis: {record['basis']}")
    print(f"label: {record['label']}")
    print(f"denominator: {record['denominator']}")
    counts = record["counts"]
    print(f"events read {counts['events_read']}, used {counts['events_used']}, "
          f"excluded {counts['events_excluded']}")
    for cell in record["cells"]:
        print(f"  {cell['region']} {cell['size_class']}: n={cell['count']} median "
              f"{cell['median']:.4f} p10 {cell['p10']:.4f} p90 {cell['p90']:.4f} "
              f"{record['units']} ({cell['label']})")
    out.parent.mkdir(parents=True, exist_ok=True)
    text = record_text(record)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out} ({len(text.encode('utf-8'))} bytes)")
    print(f"record digest {record_digest(record)} (the file's sha256)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
