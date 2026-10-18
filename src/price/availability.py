"""The availability term (OUT-3): the method ``seasonal_plus_availability``.

The third November 2026 vintage is the second vintage's band plus the availability
response (OUT-2) applied to the outage records known at the information cutoff for
the vintage's window. Decision: ``docs/work/desk-agent-and-book-2026-10-18/strategy.md``,
decisions 4 and 12 and section 2; the orchestrator's decisions (a) to (g) in the OUT-3
note of ``docs/work/tasks.json``. The task record is
``docs/work/desk-agent-and-book-2026-10-18/out-3.md``.

What it reads
=============

* **The predecessor's values file**, by digest, through :class:`OutlookArchive`: the
  vintage named by id, its ``values_ref.path_hint`` read and its SHA-256 compared with
  ``values_ref.sha256`` and its row count with ``values_ref.rows``. A row carries a
  point ``value`` and either all of ``p10``, ``p50`` and ``p90`` or none; a row
  without them is a zero-width band (``p10 = p50 = p90 = value``), the rule of
  :mod:`src.outlook.scoring`. The real second vintage carries the point value only.
* **The response record** (``.local/price/response.json`` for the real run), validated
  by :func:`src.price.response.validate` and cited by its SHA-256.
* **The known outages** (:data:`KNOWN_OUTAGES_HEADER`, the export of
  ``scripts/outlook/known_outages.sql``): forced and planned outage records known at
  the cutoff whose ``[start, end)`` intersects the window, with region, MW lost (the
  unit's rated ``p_max``), start and end in Manila civil time. Every row must have
  been first seen at or before the cutoff (A-RUN), or the file is refused: it is then
  not the known-at export.
* **The regional demand** (:data:`DEMAND_HEADER`, OUT-2's demand export), for the
  denominator of the response.

The arithmetic
==============

For one known outage ``o`` in region ``r`` with MW lost ``m``, the response cell ``c``
is the record's cell for ``r`` and ``m`` (:func:`src.price.response.find_cell`). Its
hours are the whole clock hours of the window inside the outage: an hour ``h`` counts
when ``h >= start`` and ``h + 1 h <= end`` (OUT-2's measured-hours rule). For each of
those hours, at each quantile::

    shift_q(o) = c_q x m / D_r(o) x w_r      q = p10, p50 (the cell's median), p90

and the hour's band level moves by the sum of the shifts of every outage covering it.
Hours without a known outage keep the predecessor's band, byte for byte. The values
file's point ``value`` is the new ``p50``. The issue's delta block is the mean over
the window's hours (744 for November) of ``new - previous`` on the point value, so a
shift on ``k`` hours moves the mean by ``shift x k / 744``: the dilution is exactly
that mean, and :func:`src.price.response.apply` is called per hour with no
``window_hours`` so nothing is diluted twice.

``D_r(o)`` is the regional mean demand over the outage's hours. The demand export ends
before the cutoff (it is a snapshot), so the demand of a November hour is not known at
the cutoff. The method uses a known-at proxy: for each outage hour, the mean demand of
the same region at the same clock hour on every day of the same weekday class
(Monday to Friday, or Saturday and Sunday) in the :data:`DEMAND_WEEKS` weeks before the
cutoff's local date, never a row at or after the cutoff; at least
:data:`MIN_DEMAND_HOURS` such hours, else ``DEMAND_THIN``. ``D_r(o)`` is the mean of
those per-hour values over the outage's hours. The weeks before a mid-October cutoff stand
for November hours: a seasonal change in demand between those months is not in the
denominator (the run record's rules say so).

``w_r`` is the region's known-at load share when the vintage predicts the whole-system
series: the region's demand over the three regions' demand in the same four weeks before the
cutoff (:func:`load_shares`, review round 1 decision k), so a regional price move reaches the
system price in proportion to the region's load and the other regions' prices are read as
unmoved. On a regional vintage ``w_r`` is 1, and an outage of another region does not apply.
The run record states each region's share and the factor an unweighted shift would carry.

Only the known outages of one class apply: ``outage_class`` is ``forced`` by default (decision
b; the response was measured on forced outages), ``planned`` only as a second, labelled run.
The rows of the other class are listed as not applied and counted; the class travels into the
run record, the label and the method version (:func:`method_version_of`).

Stated extensions of the measurement (the run record says each):

* The response was measured on forced outages over 6 hours, outages that overlapped
  another were left out. Here a planned outage, an outage longer than 6 hours and two
  outages in one hour (the shifts sum) are extensions; each applied outage carries
  its class and its hours beyond the measured ones.
* A unit's hour counts once: when two kept records of one unit cover the same hour,
  the record first seen last applies and the other is skipped for that hour.

Labels travel
=============

An exploratory cell (``small_sample``) applies only with ``allow_exploratory=True``;
otherwise its outage is listed as not applied and counted (decision j). When one applies, the label goes
into the values file, into the run record (the values file's sidecar) and into the
method version the vintage carries (:data:`EXPLORATORY_SUFFIX`). A synthetic input
(the response, the outages or the demand labelled synthetic, or a synthetic
predecessor) makes the run synthetic, one way. The run record states in words
whether the response is distinguishable from zero at p10 and p90 in each applied cell
(:func:`zero_statement`; a cell of one event, or any small-sample cell, has no spread and is
never counted as distinguishable) and names the response record by digest; the label always
carries a zero clause (:func:`zero_clause`).

The values file states every header fact the site's data build requires
(:data:`BAKE_HEADER_KEYS` and ``input``; :data:`HEADER_RULE` says what each means), and the
method record carries the predecessor's input citations forward under their own names, first
(:func:`carried_inputs`, decision l): the new values rest on the predecessor's band and so on
the export it was built from.

What it writes
==============

:func:`write_run` writes two files under a given directory, each with an exclusive
create (an existing file is never replaced): the values file ``<outlook id>.json`` and
its sidecar, the run record ``<outlook id>.availability.json``. Neither carries a path
or a unit name: inputs are named by file name and digest, outages by their line in the
export, so the two digests do not depend on where the files sit.
:func:`method_record` builds the issue command's method record (the closed shape of
:mod:`src.outlook.reissue`), and :func:`write_method_record` writes it once. The
command is ``scripts/outlook/availability.py``.

A run in which no known outage shifts any hour is refused ``REPEATS_PREDECESSOR``
before anything is written: its values would repeat the predecessor's.

:func:`compare_vintages` composes the vintage comparison (the two vintages, the delta,
the changed beliefs, the stale marks, the reason and the labels) from an archive.

Standard library and this package only (the rule of ``tests/test_price_baselines.py`` for
``src/price``): the archive is passed in as an object with the
:class:`src.outlook.records.OutlookArchive` interface (``outlook(id)``, raising a
``ValueError`` with a ``code``), so this module never imports the outlook package. No clock,
no network, no model call.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import response as response_module

ROOT = Path(__file__).resolve().parents[2]

METHOD = "seasonal_plus_availability"
METHOD_VERSION = "seasonal_plus_availability out-3.2"
#: Named in the method version the vintage carries when an exploratory cell applied.
EXPLORATORY_SUFFIX = ", exploratory cells applied"
VALUES_KIND = "availability-values"
RUN_KIND = "availability-method-run"
RUN_VERSION = "out-3.2"
#: The outage class a run applies; forced is the default (decision b), planned only as a second,
#: labelled run (review round 1, decision i).
DEFAULT_OUTAGE_CLASS = "forced"

KNOWN_OUTAGES_HEADER = (
    "run", "resource_name", "region_code", "status", "outage_class", "mw_lost", "start_manila",
    "end_manila", "start_utc", "end_utc", "first_seen_manila", "first_seen_utc", "last_seen_manila",
    "revision_no", "n_revisions",
)
#: OUT-2's demand export header (``scripts/price/event_study.sql`` query 2), exactly.
DEMAND_HEADER = ("region_name", "hour_start", "n5", "demand_mw_mean")
REGIONS = ("CLUZ", "CVIS", "CMIN")
CLASSES = ("forced", "planned")
RUNS = ("RTD", "HAP", "DAP", "WAP")
#: File-name words that mark a real-time price file (OUT-2's list); refused before the header.
REAL_TIME_NAME_MARKS = ("rtd", "realtime", "real_time", "real-time", "fivemin_rt")
LABEL_SIDECAR = "synthetic-label.json"
UTC_OFFSET = timedelta(hours=8)
HOUR = timedelta(hours=1)
DEMAND_WEEKS = 4
MIN_DEMAND_HOURS = 3
PLACES = 6

BAND_KEYS = ("p10", "p50", "p90")
#: The predecessor values file's header keys the new values file keeps as they are: the window, the
#: series and the baseline the band was built with.
VALUES_HEADER_KEYS = ("baseline", "baseline_version", "billing_month", "horizon", "series", "series_label",
                      "window_start_hour_local", "window_end_hour_local")
#: The header facts the site's data build requires of every values file (scripts/grid/build_data.py,
#: VALUES_HEADER_TEXT), plus ``input`` {file, sha256}; the new values file states each (decision h).
BAKE_HEADER_KEYS = ("series", "series_label", "billing_month", "horizon", "origin", "cutoff_local",
                    "window_start_hour_local", "window_end_hour_local", "baseline", "baseline_version",
                    "source")
HEADER_RULE = (
    "origin is the predecessor's origin (the window's first local day); cutoff_local is this run's "
    "information cutoff in Manila time, and predecessor_cutoff_local the cutoff the baseline band was "
    "read at; source and input name the predecessor's values file, by file name and SHA-256, the band "
    "these values rest on"
)
CELL_KEYS = {"p10": "p10", "p50": "median", "p90": "p90"}

BASIS_SYSTEM = (
    "the response cells are regional (CLUZ, CVIS, CMIN) and this vintage predicts the whole-system "
    "series; the regional shift is weighted by the region's known-at load share, its demand over the "
    "three regions' demand in the %d weeks before the cutoff (load_shares), so the other regions' prices "
    "are read as unmoved" % DEMAND_WEEKS
)
BASIS_REGIONAL = "the response cell's region is the vintage's series"
DEMAND_RULE = (
    "the regional mean demand over the outage's hours, each hour's demand the mean of the same region, "
    "clock hour and weekday class on the days of the %d weeks before the cutoff's local date, from rows "
    "before the cutoff only (the demand of a window hour is not known at the cutoff); a seasonal limit: "
    "the weeks before a mid-October cutoff stand for November hours, so a change in demand between "
    "those months is not in the denominator" % DEMAND_WEEKS
)
HOURS_RULE = (
    "the whole clock hours of the window inside the outage: an hour counts when it starts at or after "
    "the outage start and ends by the outage end"
)
SHIFT_RULE = (
    "per outage hour, each band level moves by the cell's matching quantile (p10 by p10, p50 by the "
    "median, p90 by p90) times the MW lost over the regional mean demand, times the region's load share "
    "on a system band; the shifts of outages covering "
    "one hour sum; hours without a known outage keep the predecessor's band; the point value is the new "
    "p50; the monthly delta is the mean over the window's hours, so the shift is diluted by the share of "
    "the window the outage covers"
)
EXTENSIONS = (
    "the response was measured on forced outages over %s hours, leaving out outages that overlapped "
    "another; applying it to a planned outage, to hours beyond the measured ones, or to two outages in "
    "one hour (the shifts sum) extends the measurement"
)
UNIT_HOUR_RULE = "a unit's hour counts once: the record first seen last applies"

MESSAGES = {
    "REAL_TIME_REFUSED": "a real-time price file is refused: the level comes from the final series",
    "NOT_KNOWN_OUTAGES": "the file is not the known-outages export (header)",
    "NOT_DEMAND_EXPORT": "the file is not the demand export (header)",
    "MALFORMED_EXPORT": "a row of the export does not keep its rules",
    "MISSING_EXPORT": "an input file does not exist",
    "UNKNOWN_REGION": "a row names a region outside CLUZ, CVIS and CMIN",
    "CLOCK_MISMATCH": "a UTC column is not its Manila column minus 8 hours",
    "DUPLICATE_OUTAGE": "two rows carry the same unit and start",
    "DUPLICATE_HOUR": "two demand rows carry the same region and hour",
    "OUTAGE_AFTER_CUTOFF": "a row was first seen after the cutoff, so the file is not the known-at export",
    "UNLABELLED_SYNTHETIC": "a file named synthetic is not listed by a label sidecar beside it",
    "MALFORMED_LABEL": "a label sidecar is malformed, or the inputs carry two labels",
    "RESPONSE_INVALID": "the response record does not validate",
    "PREDECESSOR_UNKNOWN": "no vintage with that identifier is issued in this archive",
    "PREDECESSOR_INVALID": "the vintage does not read back clean from the archive",
    "VALUES_UNREADABLE": "the predecessor's values file could not be read",
    "VALUES_DIGEST_MISMATCH": "the predecessor's values file is not the one its record cites by digest",
    "VALUES_SHAPE": "the predecessor's values file does not carry one band per whole local hour",
    "CUTOFF_INVALID": "the cutoff is not an offset-bearing instant",
    "CUTOFF_BEFORE_PREDECESSOR": "the cutoff is earlier than the predecessor's information cutoff",
    "CUTOFF_INSIDE_WINDOW": "the cutoff is after the start of the vintage's window",
    "EXPLORATORY_CELL": "an exploratory cell would apply; pass allow_exploratory and carry the label",
    "OUTAGE_CLASS_INVALID": "the outage class is forced or planned",
    "PREDECESSOR_INPUT_MISSING": "an input the predecessor cites is not given by file and digest, so it cannot be carried forward",
    "REGION_NOT_SERIES": "the vintage predicts a region other than the outage's and not the system",
    "DEMAND_THIN": "too few demand hours before the cutoff for an outage hour's denominator",
    "REPEATS_PREDECESSOR": "no known outage shifts any hour, so the values would repeat the predecessor's",
    "OUTPUT_EXISTS": "an output file already exists; nothing is replaced",
    "OUTPUT_INVALID": "an output path is not usable",
}


class AvailabilityError(ValueError):
    """A refusal of the availability method; :data:`MESSAGES` owns the text."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        text = MESSAGES[code]
        ValueError.__init__(self, f"{text} ({detail})" if detail else text)


# --- small helpers ----------------------------------------------------------


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path):
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        raise AvailabilityError("MISSING_EXPORT", Path(path).name) from None


def _refuse_real_time(path):
    lowered = Path(path).name.lower()
    if any(mark in lowered for mark in REAL_TIME_NAME_MARKS):
        raise AvailabilityError("REAL_TIME_REFUSED", Path(path).name)


def _header(path):
    path = Path(path)
    if not path.is_file():
        raise AvailabilityError("MISSING_EXPORT", path.name)
    with path.open(newline="", encoding="utf-8") as handle:
        first = next(csv.reader(handle), None)
    return tuple(first or ())


def _stamp(text, where, column):
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise AvailabilityError("MALFORMED_EXPORT", f"{where}: {column}") from None
    if moment.tzinfo is not None:
        raise AvailabilityError("MALFORMED_EXPORT", f"{where}: {column} carries a zone")
    return moment


def _round(value):
    return round(float(value), PLACES) + 0.0


def instant(text):
    """One offset-bearing instant (``...Z`` or ``...+08:00``) as an aware UTC datetime."""
    if type(text) is not str or "T" not in text:
        raise AvailabilityError("CUTOFF_INVALID")
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise AvailabilityError("CUTOFF_INVALID") from None
    if moment.tzinfo is None:
        raise AvailabilityError("CUTOFF_INVALID")
    return moment.astimezone(timezone.utc)


def local_cutoff(cutoff):
    """The cutoff instant as naive Manila civil time (the exports' clock)."""
    return (instant(cutoff) + UTC_OFFSET).replace(tzinfo=None)


def outlook_of(archive, outlook_id):
    """One issued vintage read back through the archive object (it re-verifies its digest)."""
    try:
        return archive.outlook(outlook_id)
    except ValueError as error:
        if getattr(error, "code", None) == "OUTLOOK_UNKNOWN":
            raise AvailabilityError("PREDECESSOR_UNKNOWN", str(outlook_id)) from None
        raise AvailabilityError("PREDECESSOR_INVALID", str(outlook_id)) from None


# --- the readers --------------------------------------------------------------


def read_label(paths):
    """The label of the ``synthetic-label.json`` sidecar that lists an input, or ``None``.

    OUT-2's rule: a file whose name says ``synthetic`` must be listed by the sidecar
    beside it, and two inputs may not carry two labels.
    """
    label = None
    for path in paths:
        path = Path(path)
        sidecar = path.parent / LABEL_SIDECAR
        listed = False
        if sidecar.is_file():
            try:
                loaded = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
                raise AvailabilityError("MALFORMED_LABEL", sidecar.name) from None
            if type(loaded) is dict and path.name in loaded.get("files", ()):
                listed = True
                if type(loaded.get("label")) is not str or not loaded["label"].strip():
                    raise AvailabilityError("MALFORMED_LABEL", sidecar.name)
                if label is not None and label != loaded["label"]:
                    raise AvailabilityError("MALFORMED_LABEL", "two labels")
                label = loaded["label"]
        if "synthetic" in path.name.lower() and not listed:
            raise AvailabilityError("UNLABELLED_SYNTHETIC", path.name)
    return label


def check_outage_class(outage_class):
    if outage_class not in CLASSES:
        raise AvailabilityError("OUTAGE_CLASS_INVALID", repr(outage_class))
    return outage_class


def read_known_outages(path, outage_class=None):
    """The known-outages export, refused unless its header and every row keep the SQL's rules.

    Returns one dict per row: ``line`` (its line in the file), ``unit`` (kept in memory
    for the unit-hour rule, never written), ``region``, ``outage_class``, ``mw_lost``,
    ``start``, ``end``, ``known_at``, ``last_seen`` (naive Manila civil time) and
    ``selected``: whether the row is of ``outage_class`` (every row when it is ``None``).
    Both classes are read and kept, so the rows of the other class are counted, not lost.
    """
    if outage_class is not None:
        check_outage_class(outage_class)
    path = Path(path)
    _refuse_real_time(path)
    if _header(path) != KNOWN_OUTAGES_HEADER:
        raise AvailabilityError("NOT_KNOWN_OUTAGES", path.name)
    outages, seen = [], set()
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            where = f"{path.name} line {number}"
            if None in row or any(value is None for value in row.values()):
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: column count")
            if row["run"] not in RUNS or row["status"] != "OUT" or row["outage_class"] not in CLASSES:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: run, status or class")
            if row["region_code"] not in REGIONS:
                raise AvailabilityError("UNKNOWN_REGION", where)
            if not row["resource_name"].strip():
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: resource_name")
            try:
                mw = float(row["mw_lost"])
                revision = int(row["revision_no"])
                revisions = int(row["n_revisions"])
            except ValueError:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: a number") from None
            if not math.isfinite(mw) or mw <= 0 or revision < 1 or revisions < revision:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: mw_lost or revision")
            stamps = {name: _stamp(row[name], where, name) for name in (
                "start_manila", "end_manila", "start_utc", "end_utc", "first_seen_manila",
                "first_seen_utc", "last_seen_manila")}
            for manila, utc in (("start_manila", "start_utc"), ("end_manila", "end_utc"),
                                ("first_seen_manila", "first_seen_utc")):
                if stamps[manila] - UTC_OFFSET != stamps[utc]:
                    raise AvailabilityError("CLOCK_MISMATCH", f"{where}: {utc}")
            if stamps["end_manila"] <= stamps["start_manila"]:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: end not after start")
            if row["outage_class"] == "forced" and stamps["first_seen_manila"] < stamps["start_manila"]:
                # forced means no run carried it before its start, so it was first seen at or after it
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: forced but seen before its start")
            if stamps["last_seen_manila"] < stamps["first_seen_manila"]:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: last seen before first seen")
            key = (row["resource_name"], stamps["start_manila"])
            if key in seen:
                raise AvailabilityError("DUPLICATE_OUTAGE", where)
            seen.add(key)
            outages.append({
                "line": number,
                "unit": row["resource_name"],
                "region": row["region_code"],
                "outage_class": row["outage_class"],
                "mw_lost": mw,
                "start": stamps["start_manila"],
                "end": stamps["end_manila"],
                "known_at": stamps["first_seen_manila"],
                "last_seen": stamps["last_seen_manila"],
                "selected": outage_class is None or row["outage_class"] == outage_class,
            })
    return outages


def read_demand(path):
    """OUT-2's hourly mean regional demand export: ``{(region, hour): MW}``; no price is read."""
    path = Path(path)
    _refuse_real_time(path)
    if _header(path) != DEMAND_HEADER:
        raise AvailabilityError("NOT_DEMAND_EXPORT", path.name)
    demand = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            where = f"{path.name} line {number}"
            if None in row or any(value is None for value in row.values()):
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: column count")
            if row["region_name"] not in REGIONS:
                raise AvailabilityError("UNKNOWN_REGION", where)
            hour = _stamp(row["hour_start"], where, "hour_start")
            try:
                value = float(row["demand_mw_mean"])
                intervals = int(row["n5"])
            except ValueError:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: a number") from None
            if (hour.minute, hour.second, hour.microsecond) != (0, 0, 0) or intervals <= 0 \
                    or not math.isfinite(value) or value <= 0:
                raise AvailabilityError("MALFORMED_EXPORT", f"{where}: not an hour, or no demand")
            key = (row["region_name"], hour)
            if key in demand:
                raise AvailabilityError("DUPLICATE_HOUR", where)
            demand[key] = value
    return demand


def read_response(path):
    """The response record, validated; returns ``(record, SHA-256 of its bytes)``."""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise AvailabilityError("MISSING_EXPORT", Path(path).name) from None
    try:
        record = json.loads(raw.decode("utf-8"))
        response_module.validate(record)
    except (UnicodeDecodeError, ValueError):
        raise AvailabilityError("RESPONSE_INVALID", "not JSON") from None
    except response_module.ResponseError as error:
        raise AvailabilityError("RESPONSE_INVALID", error.code) from None
    return record, sha256_bytes(raw)


def _resolve(path_text, root=ROOT):
    path = Path(path_text)
    return path if path.is_absolute() else Path(root) / path


def predecessor_band(archive, outlook_id, root=ROOT):
    """The predecessor vintage and its band, read by digest through the archive.

    ``archive`` is an :class:`~src.outlook.records.OutlookArchive`. Returns ``(outlook,
    payload, rows, zero_width)``: the record, the values file's parsed payload, a list of
    ``(hour_start text, hour, row)`` in file order (``row`` the original mapping, its
    numbers untouched) and whether every row is a zero-width band.
    """
    outlook = outlook_of(archive, outlook_id)
    values_ref = outlook["values_ref"]
    try:
        raw = _resolve(values_ref["path_hint"], root).read_bytes()
    except OSError:
        raise AvailabilityError("VALUES_UNREADABLE") from None
    if sha256_bytes(raw) != values_ref["sha256"]:
        raise AvailabilityError("VALUES_DIGEST_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise AvailabilityError("VALUES_UNREADABLE") from None
    if type(payload) is not dict or type(payload.get("hours")) is not list or not payload["hours"]:
        raise AvailabilityError("VALUES_SHAPE", "no hours")
    if len(payload["hours"]) != values_ref["rows"]:
        raise AvailabilityError("VALUES_SHAPE", "row count")
    rows, seen, zero_width = [], set(), True
    for row in payload["hours"]:
        if type(row) is not dict or type(row.get("hour_start")) is not str:
            raise AvailabilityError("VALUES_SHAPE", "a row")
        try:
            hour = datetime.fromisoformat(row["hour_start"])
        except ValueError:
            raise AvailabilityError("VALUES_SHAPE", "an hour") from None
        if hour.tzinfo is not None or (hour.minute, hour.second, hour.microsecond) != (0, 0, 0) \
                or hour in seen:
            raise AvailabilityError("VALUES_SHAPE", "an hour")
        seen.add(hour)
        numbers = [row.get("value")] + [row[key] for key in BAND_KEYS if key in row]
        if any(type(n) not in (int, float) or not math.isfinite(n) for n in numbers):
            raise AvailabilityError("VALUES_SHAPE", "a value")
        present = [key for key in BAND_KEYS if key in row]
        if present and len(present) != len(BAND_KEYS):
            raise AvailabilityError("VALUES_SHAPE", "part of a band")
        if present:
            zero_width = False
            if not row["p10"] <= row["p50"] <= row["p90"]:
                raise AvailabilityError("VALUES_SHAPE", "band order")
        rows.append((row["hour_start"], hour, row))
    return outlook, payload, rows, zero_width


def _band_of(row):
    if "p10" in row:
        return {key: row[key] for key in BAND_KEYS}
    return {key: row["value"] for key in BAND_KEYS}


# --- the method -----------------------------------------------------------------


def outage_hours(outage, window_hours):
    """The whole clock hours of ``window_hours`` inside the outage (OUT-2's rule)."""
    return [hour for hour in window_hours if outage["start"] <= hour and hour + HOUR <= outage["end"]]


def _weekend(day):
    return day.weekday() >= 5


def demand_at(demand, region, hour, cutoff_local, weeks=DEMAND_WEEKS):
    """The known-at proxy of one hour's regional demand (:data:`DEMAND_RULE`); ``None`` when thin."""
    cut_day = cutoff_local.date()
    samples = []
    for back in range(1, 7 * weeks + 1):
        day = cut_day - timedelta(days=back)
        if _weekend(day) != _weekend(hour.date()):
            continue
        moment = datetime.combine(day, hour.time())
        if moment >= cutoff_local:
            continue
        value = demand.get((region, moment))
        if value is not None:
            samples.append(value)
    if len(samples) < MIN_DEMAND_HOURS:
        return None
    return sum(samples) / len(samples)


def distinguishable(cell):
    """Whether a cell's p10 to p90 lies wholly on one side of zero, with a spread to show it.

    A small-sample cell, a cell of one event or a cell whose p10 equals its p90 has no spread,
    so it cannot show that the response differs from zero: it is never counted as
    distinguishable (review round 1, finding 4).
    """
    if cell.get("small_sample") or cell.get("count", 0) < 2 or not cell["p10"] < cell["p90"]:
        return False
    return cell["p10"] > 0 or cell["p90"] < 0


def _too_few(cell):
    return bool(cell.get("small_sample") or cell.get("count", 0) < 2 or not cell["p10"] < cell["p90"])


def _name(cell):
    return f"{cell['region']} {cell['size_class']}"


def zero_statement(cells):
    """The words on whether each applied cell's response is distinguishable from zero at p10 and p90."""
    if not cells:
        return "No response cell applied."
    yes = [c for c in cells if distinguishable(c)]
    few = [c for c in cells if _too_few(c)]
    straddle = [c for c in cells if c not in yes and c not in few]
    parts = []
    if straddle:
        parts.append("in " + ", ".join(_name(c) for c in straddle) + " the p10 is below zero and the p90 "
                     "above it, so the sign of the shift is not settled")
    if few:
        parts.append(", ".join(f"{_name(c)} ({c.get('count')} event{'' if c.get('count') == 1 else 's'})"
                               for c in few)
                     + " has too few events to tell, so it is not counted as distinguishable")
    if not yes:
        return ("The response is not distinguishable from zero at p10 and p90 in any applied cell: "
                + "; ".join(parts) + ".")
    return ("The response is distinguishable from zero at p10 and p90 only in "
            + ", ".join(_name(c) for c in yes) + "; " + "; ".join(parts) + ".")


def zero_clause(cells):
    """The label's zero clause, always written."""
    yes = [c for c in cells if distinguishable(c)]
    if not yes:
        return "response not distinguishable from zero at p10 and p90"
    return "response distinguishable from zero at p10 and p90 only in " + ", ".join(_name(c) for c in yes)


def load_shares(demand, cutoff_local, weeks=DEMAND_WEEKS):
    """Each region's share of the three regions' demand in the weeks before the cutoff (known at it).

    Only the hours that carry all three regions count, and never a row at or after the cutoff.
    """
    start = datetime.combine(cutoff_local.date() - timedelta(days=7 * weeks), datetime.min.time())
    hours = {}
    for (region, hour), value in demand.items():
        if start <= hour < cutoff_local:
            hours.setdefault(hour, {})[region] = value
    totals = {region: 0.0 for region in REGIONS}
    used = 0
    for row in hours.values():
        if len(row) == len(REGIONS):
            used += 1
            for region in REGIONS:
                totals[region] += row[region]
    if used < MIN_DEMAND_HOURS:
        raise AvailabilityError("DEMAND_THIN", "load shares")
    whole = sum(totals.values())
    return {region: totals[region] / whole for region in REGIONS}, used


def _cell_key(cell):
    return (cell["region"], cell["size_class"])


def method_version_of(outage_class, exploratory):
    """The method version the vintage carries: the class it applied and the exploratory mark."""
    return f"{METHOD_VERSION} ({outage_class} outages{EXPLORATORY_SUFFIX if exploratory else ''})"


def carried_inputs(predecessor, predecessor_inputs):
    """The predecessor's input citations carried forward, each matched to a given file by name and digest.

    The new values rest on the predecessor's band, and so on what that band rests on (decision l):
    every input the predecessor cites must be given as a file with the same name and SHA-256.
    """
    given = {}
    for path in predecessor_inputs or ():
        given.setdefault(Path(path).name, []).append(Path(path))
    carried = []
    for item in predecessor["inputs"]:
        match = [path for path in given.get(item["name"], []) if sha256_file(path) == item["digest"]]
        if not match:
            raise AvailabilityError("PREDECESSOR_INPUT_MISSING", item["name"])
        carried.append({"name": item["name"], "path": match[0], "file": item["name"],
                        "sha256": item["digest"]})
    return carried


def _left_out(outage, reason):
    return {"line": outage["line"], "region": outage["region"], "outage_class": outage["outage_class"],
            "mw_lost": outage["mw_lost"], "reason": reason}


def run_method(*, archive, predecessor_id, response_path, known_outages_path, demand_path, cutoff,
               outage_class=DEFAULT_OUTAGE_CLASS, allow_exploratory=False, predecessor_inputs=(),
               root=ROOT):
    """One method run: the new band per hour and the record of what was applied; nothing is written.

    ``outage_class`` (``forced`` by default, decision b) selects the known outages that apply; the
    rows of the other class are listed as not applied and counted. An outage whose cell is
    exploratory is listed as not applied and counted unless ``allow_exploratory`` (decision j).
    ``predecessor_inputs`` are the files the predecessor cites, carried forward (decision l).

    Returns a dict with ``values`` (the values file payload), ``run`` (the run record, the
    values file's sidecar), ``predecessor`` (the record) and ``inputs`` (file name, path and
    SHA-256 of each input, the carried ones first).
    """
    check_outage_class(outage_class)
    predecessor, payload, rows, zero_width = predecessor_band(archive, predecessor_id, root)
    carried = carried_inputs(predecessor, predecessor_inputs)
    cut_local = local_cutoff(cutoff)
    if instant(cutoff) < instant(predecessor["information_cutoff"]):
        raise AvailabilityError("CUTOFF_BEFORE_PREDECESSOR")
    window = [hour for _text, hour, _row in rows]
    if cut_local > min(window):
        raise AvailabilityError("CUTOFF_INSIDE_WINDOW")
    response, response_digest = read_response(response_path)
    outages = read_known_outages(known_outages_path, outage_class)
    demand = read_demand(demand_path)
    label = read_label([Path(known_outages_path), Path(demand_path)])
    response_synthetic = response["label"].startswith("synthetic")
    for outage in outages:
        if outage["known_at"] > cut_local:
            raise AvailabilityError("OUTAGE_AFTER_CUTOFF", f"line {outage['line']}")
    series = payload.get("series")
    system = series == "SYSTEM"
    shares, share_hours = load_shares(demand, cut_local) if system else ({}, 0)

    shifts = {hour: {key: 0.0 for key in BAND_KEYS} for hour in window}
    covered = {}  # (unit, hour) -> line of the record that applied there
    applied, not_applied, cells_used = [], [], {}
    other_class = exploratory_left = 0
    # The record first seen last applies first, so a unit's hour goes to the latest knowledge.
    order = sorted(outages, key=lambda o: (o["known_at"], o["line"]), reverse=True)
    for outage in order:
        if not outage["selected"]:
            other_class += 1
            not_applied.append(_left_out(outage, (
                "planned: this run applies forced outages, the class the response was measured on"
                if outage_class == "forced" else "forced: this run applies planned outages only")))
            continue
        if not system and outage["region"] != series:
            not_applied.append(_left_out(outage, "the vintage predicts another region"))
            continue
        hours = outage_hours(outage, window)
        if not hours:
            not_applied.append(_left_out(outage, "no whole clock hour inside the window"))
            continue
        try:
            cell = response_module.find_cell(response, outage["region"], outage["mw_lost"])
        except response_module.ResponseError:
            not_applied.append(_left_out(outage, "no response cell for the region and size"))
            continue
        if cell["small_sample"] and not allow_exploratory:
            exploratory_left += 1
            not_applied.append(_left_out(outage, (
                f"exploratory cell {cell['region']} {cell['size_class']} ({cell['count']} events, below "
                f"the minimum): not applied without allow_exploratory")))
            continue
        own = [hour for hour in hours if (outage["unit"], hour) not in covered]
        dropped = len(hours) - len(own)
        if not own:
            not_applied.append(_left_out(outage, "every hour already counted for the unit by a later record"))
            continue
        per_hour = []
        for hour in own:
            value = demand_at(demand, outage["region"], hour, cut_local)
            if value is None:
                raise AvailabilityError("DEMAND_THIN", f"line {outage['line']} {outage['region']}")
            per_hour.append(value)
        demand_mw = sum(per_hour) / len(per_hour)
        weight = shares[outage["region"]] if system else 1.0
        # One call of OUT-2's apply per outage on a unit band: the per-hour regional shift, share 1.
        result = response_module.apply((0.0, 0.0, 0.0), cell, outage["mw_lost"], 1,
                                       demand_mw=demand_mw, allow_exploratory=allow_exploratory)
        shift = {key: result["shift"][key] * weight for key in BAND_KEYS}
        for hour in own:
            covered[(outage["unit"], hour)] = outage["line"]
            for key in BAND_KEYS:
                shifts[hour][key] += shift[key]
        cells_used[_cell_key(cell)] = cell
        applied.append({
            "line": outage["line"],
            "region": outage["region"],
            "outage_class": outage["outage_class"],
            "mw_lost": outage["mw_lost"],
            "start": outage["start"].isoformat(),
            "end": outage["end"].isoformat(),
            "known_at": outage["known_at"].isoformat(),
            "hours_in_window": len(own),
            "hours_already_counted_for_the_unit": dropped,
            "hours_beyond_measured": max(0, len(own) - cell["measured_hours"]),
            "demand_mw": _round(demand_mw),
            "size": _round(outage["mw_lost"] / demand_mw),
            "load_share": _round(weight),
            "cell": {"region": cell["region"], "size_class": cell["size_class"], "count": cell["count"],
                     "median": cell["median"], "p10": cell["p10"], "p90": cell["p90"],
                     "label": cell["label"]},
            "label": result["label"],
            "regional_shift_per_hour": {key: _round(result["shift"][key]) for key in BAND_KEYS},
            "shift_per_hour": {key: _round(shift[key]) for key in BAND_KEYS},
        })
    applied.sort(key=lambda item: item["line"])
    not_applied.sort(key=lambda item: item["line"])
    shifted = [hour for hour in window if any(shifts[hour][key] != 0 for key in BAND_KEYS)]
    if not shifted or all(shifts[hour]["p50"] == 0 for hour in window):
        raise AvailabilityError("REPEATS_PREDECESSOR")

    hours_out = []
    shifted_set = set(shifted)
    for text, hour, row in rows:
        band = _band_of(row)
        if hour in shifted_set:
            new = {key: _round(band[key] + shifts[hour][key]) for key in BAND_KEYS}
            hours_out.append({"hour_start": text, "value": new["p50"], **new})
        else:
            # untouched: the predecessor's numbers, as they were
            hours_out.append({"hour_start": text, "value": row["value"], **band})

    exploratory = [cell for cell in cells_used.values() if cell["small_sample"]]
    cells = sorted(cells_used.values(), key=_cell_key)
    synthetic = bool(predecessor["synthetic"] or response_synthetic or label)
    total_p50 = sum(shifts[hour]["p50"] for hour in window)
    expected = {key: _round(sum(shifts[hour][key] for hour in window) / len(window)) for key in BAND_KEYS}
    method_version = method_version_of(outage_class, bool(exploratory))
    statement = zero_statement(cells)
    words = [
        f"Method {METHOD}: the band of {predecessor['outlook_id']} plus the availability response "
        f"(response record sha256 {response_digest}) applied to the {outage_class} outage records known "
        f"at {cutoff}.",
        statement,
        "The vintage states the delta, not a finding that outages move the price.",
    ]
    if outage_class == "planned":
        words.append("Planned outages: the response was measured on forced outages, so this run extends it "
                     "to announced ones, whose effect the market may already price.")
    if exploratory:
        words.append("Exploratory cells applied (fewer events than the record's minimum): "
                     + ", ".join(f"{c['region']} {c['size_class']} ({c['count']} events)" for c in exploratory)
                     + ".")
    if exploratory_left:
        words.append(f"{exploratory_left} outage(s) in exploratory cells not applied.")
    if synthetic:
        words.append("Synthetic: an input is a labelled synthetic fixture; every figure is a method "
                     "demonstration, not a measurement.")
    run_label = "; ".join([
        "synthetic fixture run, a method demonstration" if synthetic else "real inputs by digest",
        f"{outage_class} outages",
        "exploratory cells applied" if exploratory else (
            f"measured cells only, {exploratory_left} exploratory outage(s) not applied"
            if exploratory_left else "measured cells only"),
        zero_clause(cells),
    ])
    predecessor_file = Path(predecessor["values_ref"]["path_hint"]).name
    inputs = carried + [
        _input("predecessor_values", _resolve(predecessor["values_ref"]["path_hint"], root),
               predecessor["values_ref"]["sha256"]),
        _input("response", response_path, response_digest),
        _input("known_outages", known_outages_path, sha256_file(known_outages_path)),
        _input("demand", demand_path, sha256_file(demand_path)),
    ]
    counts = {
        "known_outages": len(outages),
        "selected_class": sum(1 for o in outages if o["selected"]),
        "applied": len(applied),
        "not_applied": len(not_applied),
        "not_applied_other_class": other_class,
        "not_applied_exploratory": exploratory_left,
        "applied_forced": sum(1 for a in applied if a["outage_class"] == "forced"),
        "applied_planned": sum(1 for a in applied if a["outage_class"] == "planned"),
        "window_hours": len(window),
        "shifted_hours": len(shifted),
    }
    run_record = {
        "kind": RUN_KIND,
        "version": RUN_VERSION,
        "method": METHOD,
        "method_version": method_version,
        "outage_class": outage_class,
        "label": run_label,
        "synthetic": synthetic,
        "exploratory": bool(exploratory),
        "statement": " ".join(words),
        "zero_statement": statement,
        "predecessor": {"outlook_id": predecessor["outlook_id"],
                        "values_sha256": predecessor["values_ref"]["sha256"],
                        "model_version": predecessor["model_version"],
                        "series": series,
                        "band": "zero-width (point value only)" if zero_width else "p10, p50 and p90"},
        "information_cutoff": cutoff,
        "cutoff_local": cut_local.isoformat(),
        "inputs": [{"name": item["name"], "file": item["file"], "sha256": item["sha256"]} for item in inputs],
        "response": {"sha256": response_digest, "kind": response["kind"], "version": response["version"],
                     "label": response["label"], "units": response["units"],
                     "normalization": response["normalization"]},
        "load_shares": {"shares": {region: _round(value) for region, value in shares.items()},
                        "hours": share_hours,
                        "factor_without_weight": {region: _round(1 / value) for region, value in shares.items()}}
        if system else None,
        "rules": {"hours": HOURS_RULE, "shift": SHIFT_RULE, "demand": DEMAND_RULE,
                  "basis": BASIS_SYSTEM if system else BASIS_REGIONAL,
                  "extensions": EXTENSIONS % _measured(cells), "unit_hour": UNIT_HOUR_RULE,
                  "outage_class": f"only {outage_class} records apply; the other class is listed as not applied",
                  "exploratory": "an outage in an exploratory cell applies only with allow_exploratory; "
                                 "otherwise it is listed as not applied and counted",
                  "header": HEADER_RULE,
                  "known_at": "every row first seen at or before the cutoff (A-RUN); a later row refuses the file"},
        "cells": [{"region": c["region"], "size_class": c["size_class"], "count": c["count"],
                   "median": c["median"], "p10": c["p10"], "p90": c["p90"], "label": c["label"],
                   "straddles_zero": c["p10"] < 0 < c["p90"], "distinguishable": distinguishable(c)}
                  for c in cells],
        "counts": counts,
        "applied": applied,
        "not_applied": not_applied,
        "expected_delta": {"hours": len(window), "mean_shift": expected,
                           "sum_p50_shift_over_hours": _round(total_p50)},
        "input_label": label,
    }
    values = {key: payload[key] for key in VALUES_HEADER_KEYS if key in payload}
    values.update({
        "origin": payload["origin"] if isinstance(payload.get("origin"), str) else min(window).date().isoformat(),
        "cutoff_local": cut_local.isoformat(),
        "source": f"{METHOD}: {predecessor_file} plus the availability response {Path(response_path).name}",
        "input": {"file": predecessor_file, "sha256": predecessor["values_ref"]["sha256"]},
        "predecessor_cutoff_local": payload.get("cutoff_local"),
        "kind": VALUES_KIND,
        "method": METHOD,
        "method_version": method_version,
        "outage_class": outage_class,
        "label": run_label,
        "synthetic": synthetic,
        "exploratory": bool(exploratory),
        "statement": statement,
        "predecessor": {"outlook_id": predecessor["outlook_id"],
                        "values_sha256": predecessor["values_ref"]["sha256"]},
        "response_sha256": response_digest,
        "information_cutoff": cutoff,
        "hours": hours_out,
    })
    return {"values": values, "run": run_record, "predecessor": predecessor, "inputs": inputs,
            "method_version": method_version, "synthetic": synthetic}


def _measured(cells):
    hours = sorted({str(c.get("measured_hours", 6)) for c in cells}) or ["6"]
    return " or ".join(hours)


def _input(name, path, digest):
    return {"name": name, "path": Path(path), "file": Path(path).name, "sha256": digest}


# --- writing --------------------------------------------------------------------


def _dump(payload):
    return (json.dumps(payload, indent=1, sort_keys=False, ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def _create(path, raw):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
    except FileExistsError:
        raise AvailabilityError("OUTPUT_EXISTS", path.name) from None
    except OSError:
        raise AvailabilityError("OUTPUT_INVALID", path.name) from None
    return path


def write_run(result, out_dir, outlook_id):
    """Write the values file and its sidecar once each under ``out_dir``; returns their references."""
    out_dir = Path(out_dir)
    values_path = out_dir / f"{outlook_id}.json"
    run_path = out_dir / f"{outlook_id}.availability.json"
    for path in (values_path, run_path):
        if path.exists():
            raise AvailabilityError("OUTPUT_EXISTS", path.name)
    values_raw = _dump(result["values"])
    run_raw = _dump(result["run"])
    _create(values_path, values_raw)
    _create(run_path, run_raw)
    return {
        "values": {"path": values_path, "sha256": sha256_bytes(values_raw),
                   "rows": len(result["values"]["hours"])},
        "run": {"path": run_path, "sha256": sha256_bytes(run_raw)},
    }


def path_text(path, root=ROOT):
    """A path as a method record names it: relative to the repository root when under it."""
    absolute = Path(path) if Path(path).is_absolute() else Path.cwd() / path
    try:
        return str(absolute.relative_to(Path(root)))
    except ValueError:
        return str(absolute)


def method_record(result, written, *, cutoff, root=ROOT):
    """The issue command's method record (:data:`src.outlook.reissue.METHOD_KEYS`, closed)."""
    predecessor = result["predecessor"]
    # The carried citations first, under the predecessor's own names (decision l), then this run's.
    inputs = [{"name": item["file"] if item["name"] != "predecessor_values" else
               "predecessor values " + item["file"],
               "path": path_text(item["path"], root), "digest": item["sha256"]}
              for item in result["inputs"]]
    inputs.append({"name": "availability run " + Path(written["run"]["path"]).name,
                   "path": path_text(written["run"]["path"], root), "digest": written["run"]["sha256"]})
    return {
        "method_version": result["method_version"],
        "target_series_ref": dict(predecessor["target_series_ref"]),
        "horizon": dict(predecessor["horizon"]),
        "information_cutoff": cutoff,
        "assumption_ids": list(predecessor["assumption_ids"]),
        "inputs": inputs,
        "values": {"path": path_text(written["values"]["path"], root),
                   "sha256": written["values"]["sha256"]},
        "synthetic": bool(result["synthetic"]),
    }


def write_method_record(record, path):
    """Write the method record once (exclusive create); returns its SHA-256."""
    raw = _dump(record)
    _create(path, raw)
    return sha256_bytes(raw)


# --- the vintage comparison -------------------------------------------------------


def compare_vintages(archive, outlook_id, root=ROOT):
    """The vintage comparison for a re-issued vintage, composed from the archive only.

    ``archive`` is an :class:`~src.outlook.records.OutlookArchive`.
    The two vintages (id, digest, method version, cutoff, issue instant, provenance), the
    reason, the stale marks and changed beliefs the re-issue answers, the delta block as
    stored, and the labels of the availability run when the successor cites one by digest
    (the run file is read back and its SHA-256 compared with the cited one).
    """
    after = outlook_of(archive, outlook_id)
    block = after.get("supersedes")
    if block is None:
        raise AvailabilityError("PREDECESSOR_UNKNOWN", "the vintage supersedes none")
    before = outlook_of(archive, block["outlook_id"])
    labels = None
    for item in after["inputs"]:
        if item["name"].startswith("availability run "):
            labels = {"run_sha256": item["digest"]}
            hint = Path(after["values_ref"]["path_hint"]).parent / item["name"][len("availability run "):]
            try:
                raw = _resolve(str(hint), root).read_bytes()
            except OSError:
                labels["read"] = False
                break
            if sha256_bytes(raw) == item["digest"]:
                run = json.loads(raw.decode("utf-8"))
                labels.update({"read": True, "label": run["label"], "exploratory": run["exploratory"],
                               "synthetic": run["synthetic"], "statement": run["zero_statement"],
                               "response_sha256": run["response"]["sha256"],
                               "applied": run["counts"]["applied"],
                               "not_applied": run["counts"]["not_applied"]})
            else:
                labels["read"] = False
            break

    def side(record):
        return {"outlook_id": record["outlook_id"], "outlook_digest": record["content_digest"],
                "model_version": record["model_version"], "information_cutoff": record["information_cutoff"],
                "issued_at": record["issued_at"], "values_sha256": record["values_ref"]["sha256"],
                "synthetic": record["synthetic"]}

    return {
        "component": "vintage_comparison",
        "before": side(before),
        "after": side(after),
        "reason": block["reason"],
        "stale_marks": [dict(mark) for mark in block["stale_marks"]],
        "changed_assumption_ids": list(block["changed_assumption_ids"]),
        "delta": block["delta"],
        "confirmation_ref": block["confirmation_ref"],
        "availability": labels,
        "synthetic": bool(after["synthetic"]),
    }


__all__ = [
    "AvailabilityError",
    "DEMAND_HEADER",
    "EXPLORATORY_SUFFIX",
    "KNOWN_OUTAGES_HEADER",
    "MESSAGES",
    "METHOD",
    "METHOD_VERSION",
    "compare_vintages",
    "carried_inputs",
    "demand_at",
    "distinguishable",
    "instant",
    "load_shares",
    "local_cutoff",
    "method_record",
    "method_version_of",
    "outage_hours",
    "outlook_of",
    "predecessor_band",
    "read_demand",
    "read_known_outages",
    "read_label",
    "read_response",
    "run_method",
    "write_method_record",
    "write_run",
    "zero_clause",
    "zero_statement",
]
