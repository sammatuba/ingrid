"""Score an issued outlook against the settled final series and build its receipt.

An issued outlook predicted one horizon once; this module takes that record, the
outlook's own values file and the *final* regional price export, and returns the
``ScoringReceipt`` (ARCH-1's :func:`src.outlook.records.build_receipt`) that
scores the window once it has settled. Appending the receipt is the command's
job (``scripts/outlook/score.py``), not this module's; nothing here writes.

The final series, and only the final series
===========================================
``regional_export`` is checked against the digest record first
(:func:`src.price.series.verify_inputs`), and the bytes are read only after they
match. A real-time copy of the price is not in the digest record, so it has no
path through this function: a caller cannot score an outlook against the
known-then observation by naming it on the command line. ``final_series_digest``
on the receipt is the SHA-256 of the export's bytes, and
``final_series_version`` is the caller's text — the settled vintage's name.

The series is the one the outlook names: ``target_series_ref`` must be the price
target contract's regional reference series (``grid_raw.ext_pmr_lwap_final``,
column ``lwap``), and the values file's ``series`` key selects the region
(``CLUZ``, ``CVIS``, ``CMIN`` or ``SYSTEM``) inside that export. An outlook on
another series is refused ``SERIES_UNSUPPORTED`` rather than scored against the
wrong bytes.

When the window has settled
===========================
Two relations, both checked before any metric is computed:

* ``scored_at`` is at or after ``horizon.end`` (the receipt's own rule); and
* the export's last hour reaches the horizon's end — a final series that stops
  before the window closes has not settled it.

Either failure is :class:`ScoringError` ``WINDOW_NOT_SETTLED``. No clock is read
here; ``scored_at`` is caller-supplied.

The values file
===============
The outlook cites its values by ``values_ref`` (``path_hint``, ``sha256`` and
``rows``); the file is read only when its bytes match that digest, and its row
count must match too. Each row is ``{"hour_start", "value"}`` — the shape
PRICE-2's baseline runner writes — with ``hour_start`` a naive Asia/Manila hour
(the price target contract's clock; the Philippines has no daylight saving time,
so one fixed offset is used). A row may also carry ``p10``, ``p50`` and ``p90``;
all three or none.

* **With a band:** the three values are read, put in ascending order (the
  scorecard's rearrangement rule) and scored as the quantiles; ``value`` stays
  the point forecast that bias, MAE and RMSE score.
* **Without a band:** the scorecard's quantile rule is applied with an empty
  residual fan, which yields the point forecast at all three quantiles — a
  zero-width band. Nothing is invented: the first vintage's values carry only
  the mid value, and the record says so. Pinball at p50 is then exactly half the
  MAE for the scored hours.

The values file must cover the outlook's horizon exactly: one value per hour,
no duplicates, nothing outside the window. A different shape is
``VALUES_INCOMPLETE`` or ``VALUES_SHAPE`` — a hand-back, never a fill.

Marks, never fills
==================
The marks are :func:`src.price.series.derive_marks` on the final series, the
same marks the PRICE-2 scorecard uses. An hour is classified once:

* a day whose interval count is not the 288 a complete day has
  (``marks.irregular_days``) — skipped as ``irregular day <date>``;
* a billing month administered on every row (``marks.ap_all_months``) — skipped
  as ``administered pricing <month>``;
* a billing month carrying both administered and market intervals
  (``marks.ap_mixed_months``) — skipped as ``administered pricing mixed
  <month>``, because the regional export carries no per-hour flag to separate
  them.

Every skipped hour is counted in ``coverage.skipped`` under its reason; no
interval is ever filled, interpolated or moved. The remaining hours are the
market slice: one metrics row per horizon label and slice, with the six metrics
the price target contract fixes (bias, MAE, RMSE and pinball at p10, p50, p90)
computed by :func:`src.price.scorecard.metrics_from` on the same
``(realized, point, p10, p50, p90)`` rows. ``coverage.scored`` counts the hourly
values scored; a window with nothing left to score is ``WINDOW_EMPTY`` rather
than a receipt with no metric row.

The receipt's ``synthetic`` is inherited from the outlook (one way, as the
archive's link rule requires), so a fixture forecast can never be recorded as a
real score and a real outlook's receipt stays real.

This module imports only the standard library and the repository's price and
archive modules, which are themselves standard-library only. It reads no clock,
no network, no model and no credential.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.outlook.records import build_receipt, validate_outlook
from src.price.scorecard import (
    AP,
    MARKET,
    METRIC_DECIMALS,
    metrics_from,
    ordered_quantiles,
)
from src.price.series import (
    HOUR,
    REGIONAL_KEYS,
    SeriesError,
    billing_month_label,
    billing_month_of,
    derive_marks,
    digest_file,
    load_regional,
    verify_inputs,
)

#: The price target contract's regional reference series: the table and column
#: the regional export is written from. This command reads that export, so an
#: outlook that targets another series cannot be scored from it.
REGIONAL_TARGET_TABLE = "grid_raw.ext_pmr_lwap_final"
REGIONAL_TARGET_COLUMN = "lwap"

#: The export's ``hour_start`` values are Asia/Manila local time, naive in the
#: files (the target contract's "Interval" row). The archive's instants are UTC.
#: The Philippines has observed no daylight saving time since 1978, so this one
#: fixed offset is exact and no time-zone table is consulted.
LOCAL_UTC_OFFSET = timedelta(hours=8)

#: The three band keys a values row may carry, all or none.
BAND_KEYS = ("p10", "p50", "p90")

#: The six metrics the receipt row carries, in the order the scorecard reports.
METRIC_NAMES = ("bias", "mae", "rmse", "pinball_p10", "pinball_p50", "pinball_p90")

#: Stable refusal codes with fixed, non-disclosing text; nothing echoes caller
#: input, a file path or a raw exception.
MESSAGES = {
    "WINDOW_NOT_SETTLED": "the final series has not settled the outlook's window",
    "WINDOW_UNALIGNED": "the outlook's horizon is not whole local hours",
    "WINDOW_EMPTY": "no interval of the window is left to score under its marks",
    "SCORED_AT_INVALID": "scored_at is not an offset-bearing instant",
    "VALUES_UNREADABLE": "the outlook's values file could not be read",
    "VALUES_DIGEST_MISMATCH": "the values file does not match the digest the outlook cites",
    "VALUES_ROWS_MISMATCH": "the values file's row count does not match the outlook's record",
    "VALUES_SHAPE": "the values file does not carry the shape the metrics need",
    "VALUES_INCOMPLETE": "the values file does not cover the outlook's horizon exactly",
    "SERIES_UNSUPPORTED": "the outlook does not target the regional final series this command reads",
    "EXPORT_UNREADABLE": "the final regional export could not be read",
    "EXPORT_DIGEST_NOT_RECORDED": "the final export has no recorded digest",
    "EXPORT_DIGEST_MISMATCH": "the final export does not match its recorded digest",
}

#: The export reader's own codes, mapped onto this module's vocabulary so a
#: caller sees one closed set.
_EXPORT_CODES = {
    "DIGEST_MISMATCH": "EXPORT_DIGEST_MISMATCH",
    "DIGEST_NOT_RECORDED": "EXPORT_DIGEST_NOT_RECORDED",
}


class ScoringError(ValueError):
    """A scoring refusal whose text :data:`MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, MESSAGES[code])


def _parse_instant(value, code):
    """One offset-bearing instant as an aware UTC datetime; anything else refuses."""
    if type(value) is not str:
        raise ScoringError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ScoringError(code) from None
    if parsed.tzinfo is None:
        raise ScoringError(code)
    return parsed.astimezone(timezone.utc)


def _local_hour(value):
    """One naive whole local hour from the values file; anything else refuses."""
    if type(value) is not str:
        raise ScoringError("VALUES_SHAPE")
    try:
        hour = datetime.fromisoformat(value)
    except ValueError:
        raise ScoringError("VALUES_SHAPE") from None
    if hour.tzinfo is not None or (hour.minute, hour.second, hour.microsecond) != (0, 0, 0):
        raise ScoringError("VALUES_SHAPE")
    return hour


def _finite(value):
    """One finite JSON number as a float; booleans and non-numbers refuse."""
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ScoringError("VALUES_SHAPE")
    number = float(value)
    if not math.isfinite(number):
        raise ScoringError("VALUES_SHAPE")
    return number


def _horizon_hours(outlook):
    """The outlook's horizon as whole naive local hours, and its UTC edges.

    The horizon is stored in UTC; the final export and the values file use the
    billing clock's naive local hours. An hour is scored only when the whole
    hour lies inside the half-open horizon, so a horizon whose edges are not
    whole local hours is refused rather than rounded.
    """
    start = _parse_instant(outlook["horizon"]["start"], "WINDOW_UNALIGNED")
    end = _parse_instant(outlook["horizon"]["end"], "WINDOW_UNALIGNED")
    start_local = (start + LOCAL_UTC_OFFSET).replace(tzinfo=None)
    end_local = (end + LOCAL_UTC_OFFSET).replace(tzinfo=None)
    for edge in (start_local, end_local):
        if (edge.minute, edge.second, edge.microsecond) != (0, 0, 0):
            raise ScoringError("WINDOW_UNALIGNED")
    count = int((end_local - start_local).total_seconds() // 3600)
    if count <= 0:
        raise ScoringError("WINDOW_UNALIGNED")
    return tuple(start_local + HOUR * step for step in range(count)), end, end_local


def _read_values(outlook, values_file):
    """The values file, checked against the outlook's digest and row count.

    Returns ``(series key, {local hour: (point, band or None)})``. The bytes are
    read once; the digest is of those exact bytes, the same convention the
    archive uses for every input it cites.
    """
    path = Path(values_file)
    try:
        raw = path.read_bytes()
    except OSError:
        raise ScoringError("VALUES_UNREADABLE") from None
    if hashlib.sha256(raw).hexdigest() != outlook["values_ref"]["sha256"]:
        raise ScoringError("VALUES_DIGEST_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ScoringError("VALUES_UNREADABLE") from None
    if type(payload) is not dict:
        raise ScoringError("VALUES_SHAPE")
    rows = payload.get("hours")
    if type(rows) is not list:
        raise ScoringError("VALUES_SHAPE")
    if len(rows) != outlook["values_ref"]["rows"]:
        raise ScoringError("VALUES_ROWS_MISMATCH")
    series_key = payload.get("series")
    if type(series_key) is not str or series_key not in REGIONAL_KEYS:
        raise ScoringError("SERIES_UNSUPPORTED")
    points = {}
    for row in rows:
        if type(row) is not dict or "hour_start" not in row or "value" not in row:
            raise ScoringError("VALUES_SHAPE")
        hour = _local_hour(row["hour_start"])
        if hour in points:
            raise ScoringError("VALUES_SHAPE")
        point = _finite(row["value"])
        present = [key for key in BAND_KEYS if key in row]
        band = None
        if present:
            if len(present) != len(BAND_KEYS):
                raise ScoringError("VALUES_SHAPE")
            band = tuple(sorted(_finite(row[key]) for key in BAND_KEYS))
        points[hour] = (point, band)
    if not points:
        raise ScoringError("VALUES_SHAPE")
    return series_key, points


def _skip_reason(hour, marks, irregular):
    """The one mark an hour carries, or ``None`` when it is scorable.

    The day mark is tested before the pricing marks: it is what the bytes say
    about the day itself, and it is the mark that changes the coverage count
    most often. Each skipped hour is counted once, under one reason.
    """
    day = hour.date().isoformat()
    if day in irregular:
        return "irregular day %s" % day
    month = billing_month_label(*billing_month_of(hour))
    if month in marks.ap_all_months:
        return "administered pricing %s" % month
    if month in marks.ap_mixed_months:
        return "administered pricing mixed %s" % month
    return None


def _decimal(value):
    """One metric as the plain decimal string the receipt stores."""
    return format(value + 0.0, ".%df" % METRIC_DECIMALS)


def _metric_row(label, slice_name, metrics):
    """One receipt metric row, its six numbers as decimal strings."""
    row = {"horizon": label, "slice": slice_name, "intervals": metrics.count}
    for name in METRIC_NAMES:
        row[name] = _decimal(getattr(metrics, name))
    return row


def score_outlook(outlook, values_file, regional_export, digests, *, scored_at,
                  final_series_version):
    """Score one issued outlook against the settled final series; return its receipt.

    ``outlook`` is the issued record (re-validated here), ``values_file`` the
    file its ``values_ref`` cites, ``regional_export`` the final regional price
    export and ``digests`` the export digest record
    (:func:`src.price.series.load_digests`). ``scored_at`` is the caller's
    instant and ``final_series_version`` the settled vintage's name; both enter
    the receipt. The window is the whole horizon the outlook predicted. The
    receipt is sealed and validated by :func:`src.outlook.records.build_receipt`
    but not written; the command appends it through the archive.
    """
    validate_outlook(outlook)
    hours, window_end, window_end_local = _horizon_hours(outlook)
    scored = _parse_instant(scored_at, "SCORED_AT_INVALID")
    if scored < window_end:
        raise ScoringError("WINDOW_NOT_SETTLED")

    reference = outlook["target_series_ref"]
    if (reference["table"] != REGIONAL_TARGET_TABLE
            or reference["column"] != REGIONAL_TARGET_COLUMN):
        raise ScoringError("SERIES_UNSUPPORTED")
    series_key, points = _read_values(outlook, values_file)
    if set(points) != set(hours):
        raise ScoringError("VALUES_INCOMPLETE")

    export = Path(regional_export)
    if not export.is_file():
        raise ScoringError("EXPORT_UNREADABLE")
    try:
        verify_inputs([export], digests)
        series_list = load_regional(export)
    except SeriesError as error:
        raise ScoringError(_EXPORT_CODES.get(error.code, "EXPORT_UNREADABLE")) from None
    final_digest = digest_file(export)
    series = next((entry for entry in series_list if entry.key == series_key), None)
    if series is None:
        raise ScoringError("SERIES_UNSUPPORTED")
    # The settled-window relation: the export's own last hour must reach the
    # horizon's end. A final series that stops earlier has not settled it.
    if not series.hours or max(series.hours) + HOUR < window_end_local:
        raise ScoringError("WINDOW_NOT_SETTLED")

    marks = derive_marks(series)
    irregular = frozenset(marks.irregular_days)
    skipped = {}
    pairs = []
    for hour in hours:
        reason = _skip_reason(hour, marks, irregular)
        if reason is not None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        row = series.rows.get(hour)
        if row is None:
            # Unreachable behind the day mark (a missing hour makes its day
            # irregular); kept so a missing value is never filled.
            reason = "missing hour %s" % hour.isoformat()
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        point, band = points[hour]
        if band is None:
            # The scorecard's quantile rule with an empty residual fan: the
            # point forecast at all three quantiles, a zero-width band.
            p10, p50, p90 = ordered_quantiles(point, 0.0, 0.0)
        else:
            p10, p50, p90 = band
        pairs.append((row.mean, point, p10, p50, p90))
    if not pairs:
        raise ScoringError("WINDOW_EMPTY")

    # One row per horizon label and slice. The market slice holds the scored
    # hours; the AP slice is empty because this command skips administered-pricing
    # intervals with their reasons (the brief's rule), and the regional export
    # carries no per-hour flag that could separate them inside a mixed month.
    scored_by_slice = {MARKET: pairs, AP: []}
    metrics = [_metric_row(outlook["horizon"]["label"], name, metrics_from(scored_by_slice[name]))
               for name in (MARKET, AP) if scored_by_slice[name]]
    coverage = {
        "scored": len(pairs),
        "skipped": [{"count": count, "reason": reason}
                    for reason, count in sorted(skipped.items())],
    }
    return build_receipt(
        outlook,
        scored_at=scored_at,
        final_series_version=final_series_version,
        final_series_digest=final_digest,
        window={"start": outlook["horizon"]["start"], "end": outlook["horizon"]["end"]},
        metrics=metrics,
        coverage=coverage,
        synthetic=outlook["synthetic"],
    )


__all__ = [
    "BAND_KEYS",
    "LOCAL_UTC_OFFSET",
    "MESSAGES",
    "METRIC_NAMES",
    "REGIONAL_TARGET_COLUMN",
    "REGIONAL_TARGET_TABLE",
    "ScoringError",
    "score_outlook",
]
