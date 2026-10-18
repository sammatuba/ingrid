"""Issue and re-issue of outlook vintages: the method record, the preview and the confirmed issue (OUT-1).

Until OUT-1 the archive could only be written by hand through
:meth:`~src.outlook.records.OutlookArchive.issue`. This module is what the issue
command (``scripts/outlook/issue.py``) and the desk agent's ``draft(reissue)`` and
``reissue_outlook`` actions call. It has three parts.

The method record
=================

A method run leaves one JSON file that says what it ran and what it read::

    {"method_version": "...",
     "target_series_ref": {"table": "...", "column": "...", "version": "..."},
     "horizon": {"label": "month", "start": "...Z", "end": "...Z"},
     "information_cutoff": "...Z",
     "assumption_ids": ["price:...", ...],
     "inputs": [{"name": "...", "path": "...", "digest": "<sha256 of the file>"}],
     "values": {"path": "...", "sha256": "<sha256 of the values file>"},
     "synthetic": false}

The key set is closed. :func:`load_method_record` reads it and
:func:`verify_method_inputs` re-reads every input and the values file and
compares each file's SHA-256 with the digest the record names, before anything
is issued. A relative path is read from the repository root, the same rule
``scripts/outlook/score.py`` uses for a values ``path_hint``, so the values file
of an issued vintage is found again by the scorer at the path it was issued
from. Nothing here copies a values file; the method run writes it where it
belongs (``.local/outlook-archive/values/`` for a real vintage) before the issue.

The re-issue preview
====================

A changed belief marks every vintage that rests on it (ARCH-3,
:func:`src.outlook.dependency.mark_stale`). :func:`build_preview` turns one or
more stored marks of one vintage and a method record into a
``ReissuePreview``: what the dock's draft shows before the person confirms —
the predecessor by id and exact issued bytes (and its values digest), the marks
by digest with their assumption, revision, instant and provenance, the changed
assumption ids, the method record by path and digest, the information cutoff,
the candidate vintage (every field the issue will write except ``issued_at``,
which is the instant of the confirmed issue) and the computed ``delta``. The
preview is sealed with a ``content_digest`` like every archive record and
:func:`validate_preview` checks one. The preview carries the ``reason``:
``belief_changed`` when it answers stale marks.

A re-issue without a mark (rework round 1, the orchestrator's decision): a
method change or an input refresh writes no stale mark, so ``build_preview``
also takes ``supersedes=<outlook id>`` and ``reason`` in ``method_changed``
(the method version must differ from the predecessor's model version,
``METHOD_UNCHANGED`` otherwise) or ``inputs_refreshed`` (an input digest must
differ, ``INPUTS_UNCHANGED`` otherwise). The mark list and the changed
assumption ids are then empty; the newest-vintage rule, the delta,
``REPEATS_PREDECESSOR``, provenance and the confirmation are unchanged.

The delta rule. The two values files are read by digest: the predecessor's at
its ``values_ref.path_hint`` against its ``values_ref.sha256``, the new one at
the method record's path against the method record's digest; a file whose bytes
do not match is refused. When the two digests are equal the re-issue is refused
``REPEATS_PREDECESSOR`` before anything else is read. Otherwise both files must
carry the same set of ``hour_start`` keys (and the same ``series`` header when
they name one), and per horizon the delta states the hours compared and the
mean, mean absolute, minimum and maximum of ``new - previous`` over the point
``value`` of each hour, as decimal strings at six places. A file whose bytes
differ but whose every hourly value equals its predecessor's (only a header
moved, say the cutoff note) repeats its predecessor too and is refused
``REPEATS_PREDECESSOR``: the strategy record's rule is that a vintage that would
repeat its predecessor is not issued. Band levels (``p10``/``p50``/``p90``), when
a values file carries them, are not part of the delta; the point value is.

The confirmed issue
===================

:func:`issue_confirmed` is the only path from a preview to a vintage. It takes
the preview, the instant of the issue and ``confirmation_ref`` — the
identifier of the person's confirmation (the agent's confirmation record,
DOCK-3, or the reference a person gives the command's ``--confirm``); a blank
reference is refused, so there is no issue without a recorded decision. The
vintage id, the issuer, the method record path and the cutoff come from the
confirming call, not from the preview, and a preview that names others is
``PREVIEW_MISMATCH``. It does not trust the rest of the preview either: it
rebuilds the preview from the live archive with those four values (the
marks still stored, the predecessor still stored at the digest, the predecessor
still the newest vintage of its target, the method record and every input and
values file still matching their digests) and refuses ``PREVIEW_STALE`` when the
rebuilt digest differs from the confirmed one. The vintage is then built with
the ``supersedes`` block and issued through
:meth:`~src.outlook.records.OutlookArchive.issue`, which checks the block
against the stored predecessor once more before its exclusive create.

Provenance runs one way, as in :mod:`src.outlook.records`: a re-issue that rests
on a synthetic predecessor or on a demonstration mark must be declared
``synthetic`` by its method record (refused ``SYNTHETIC_ONE_WAY`` otherwise; the
flag is never upgraded silently); a synthetic method record may re-issue either.

Module rules: standard library only, plus this package's records, the
dependency module and the repository's canonical JSON. No clock is read: every
instant is caller-supplied. The only write is the issue itself, through the
archive.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.contracts.jsonutil import CanonicalizationError, compute_content_digest
from src.outlook import dependency
from src.outlook.records import (
    HORIZONS,
    REASONS,
    OutlookError,
    _instant as _record_instant,
    build_outlook,
    validate_outlook,
)

ROOT = Path(__file__).resolve().parents[2]

SCHEMA_VERSION = "outlook.v1"
PREVIEW_KIND = "ReissuePreview"

METHOD_KEYS = frozenset({
    "method_version", "target_series_ref", "horizon", "information_cutoff", "assumption_ids",
    "inputs", "values", "synthetic",
})
METHOD_INPUT_KEYS = frozenset({"name", "path", "digest"})
METHOD_VALUES_KEYS = frozenset({"path", "sha256"})

PREVIEW_KEYS = frozenset({
    "schema_version", "kind", "predecessor", "reason", "stale_marks", "changed_assumption_ids",
    "method_record", "information_cutoff", "outlook", "delta", "content_digest",
})
PREDECESSOR_KEYS = frozenset({"outlook_id", "outlook_digest", "values_digest", "issued_at"})
PREVIEW_MARK_KEYS = frozenset({
    "content_digest", "assumption_id", "new_revision", "marked_at", "synthetic",
})
METHOD_REF_KEYS = frozenset({"path_hint", "sha256", "method_version"})
#: The candidate vintage: every field the issue writes, except ``issued_at`` (the
#: instant of the confirmed issue) and the ``supersedes`` block (built from the
#: preview's own predecessor, marks and delta).
CANDIDATE_KEYS = frozenset({
    "outlook_id", "information_cutoff", "horizon", "target_series_ref", "inputs",
    "assumption_ids", "model_version", "values_ref", "issuer", "synthetic",
})

#: Six places: the archive's other decimal strings (the receipt metrics) use the
#: same plain fixed-point form.
DELTA_PLACES = Decimal("0.000001")

MESSAGES = {
    "METHOD_UNREADABLE": "the method record could not be read",
    "METHOD_INVALID": "the method record does not satisfy the issue contract",
    "CUTOFF_MISMATCH": "the cutoff given to the command is not the method record's information cutoff",
    "INPUT_UNREADABLE": "an input the method record names could not be read",
    "INPUT_DIGEST_MISMATCH": "an input does not match the digest the method record names",
    "VALUES_UNREADABLE": "a values file could not be read",
    "VALUES_DIGEST_MISMATCH": "a values file does not match the digest it is cited by",
    "VALUES_SHAPE": "a values file does not carry one finite value per hour",
    "HOURS_MISMATCH": "the two values files do not carry the same hours or series",
    "MARK_UNKNOWN": "the stale mark is not stored in this archive's mark store",
    "MARKS_DISAGREE": "the stale marks of one re-issue must name one vintage's exact bytes",
    "PREDECESSOR_CHANGED": "the marked vintage is no longer stored with the bytes the mark names",
    "NOT_LATEST_VINTAGE": "a newer vintage of the same target is issued; re-issue from that one",
    "TARGET_MISMATCH": "the method record does not predict the marked vintage's series and horizon",
    "SYNTHETIC_ONE_WAY": "a re-issue resting on synthetic records must be declared synthetic",
    "REPEATS_PREDECESSOR": "the new vintage's values repeat its predecessor's, so it is not issued",
    "PREVIEW_INVALID": "the re-issue preview does not satisfy its contract",
    "PREVIEW_STALE": "the archive or the method run changed since the preview was confirmed",
    "CONFIRMATION_MISSING": "a re-issue is written only on a recorded confirmation",
    "PREVIEW_MISMATCH": "the preview names another vintage id, issuer, method record or cutoff than the confirming call",
    "PREDECESSOR_UNKNOWN": "no vintage with that identifier is issued in this archive",
    "REASON_INVALID": "a belief change re-issues from stale marks; method_changed and inputs_refreshed re-issue without one",
    "METHOD_UNCHANGED": "a method_changed re-issue needs another method version than the predecessor's",
    "INPUTS_UNCHANGED": "an inputs_refreshed re-issue needs another input digest than the predecessor's",
}

#: The placeholder a preview's own check builds its vintage with; the records
#: layer requires a reference, and the real one exists only at confirmation.
PREVIEW_CHECK_REF = "preview-check: not a confirmation"


class ReissueError(ValueError):
    """An issue or re-issue refusal whose text :data:`MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, MESSAGES[code])


def _require(condition, code):
    if not condition:
        raise ReissueError(code)


def _text(value):
    return type(value) is str and bool(value.strip())


def _sha256(path, unreadable):
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise ReissueError(unreadable) from None
    return hashlib.sha256(raw).hexdigest(), raw


def resolve(path_text, root=ROOT):
    """A path as a record names it: absolute as written, else from the repository root."""
    path = Path(path_text)
    return path if path.is_absolute() else Path(root) / path


def _instant(value, code):
    try:
        return _record_instant(value)
    except OutlookError:
        raise ReissueError(code) from None


# --- the method record ------------------------------------------------------


def load_method_record(path):
    """Read one method record and check its shape; returns ``(record, sha256 of its bytes)``."""
    digest, raw = _sha256(path, "METHOD_UNREADABLE")
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ReissueError("METHOD_UNREADABLE") from None
    validate_method_record(record)
    return record, digest


def validate_method_record(record):
    """The method record's closed shape; the archive's own rules check the fields again at issue."""
    _require(type(record) is dict and set(record) == METHOD_KEYS, "METHOD_INVALID")
    _require(_text(record["method_version"]), "METHOD_INVALID")
    _require(type(record["target_series_ref"]) is dict, "METHOD_INVALID")
    horizon = record["horizon"]
    _require(type(horizon) is dict and horizon.get("label") in HORIZONS, "METHOD_INVALID")
    _instant(record["information_cutoff"], "METHOD_INVALID")
    _require(type(record["assumption_ids"]) is list and record["assumption_ids"], "METHOD_INVALID")
    inputs = record["inputs"]
    _require(type(inputs) is list and inputs, "METHOD_INVALID")
    for item in inputs:
        _require(type(item) is dict and set(item) == METHOD_INPUT_KEYS, "METHOD_INVALID")
        _require(_text(item["name"]) and _text(item["path"]) and type(item["digest"]) is str,
                 "METHOD_INVALID")
    values = record["values"]
    _require(type(values) is dict and set(values) == METHOD_VALUES_KEYS, "METHOD_INVALID")
    _require(_text(values["path"]) and type(values["sha256"]) is str, "METHOD_INVALID")
    _require(type(record["synthetic"]) is bool, "METHOD_INVALID")
    return record


def verify_method_inputs(record, root=ROOT):
    """Every input and the values file re-read and compared with the digests the record names.

    Returns ``(inputs, values_ref, hours)``: the inputs as the outlook cites them
    (name and digest), the values reference (path hint as written, digest, row
    count) and the values file's hours (:func:`read_values`).
    """
    validate_method_record(record)
    inputs = []
    for item in record["inputs"]:
        digest, _raw = _sha256(resolve(item["path"], root), "INPUT_UNREADABLE")
        _require(digest == item["digest"], "INPUT_DIGEST_MISMATCH")
        inputs.append({"name": item["name"], "digest": item["digest"]})
    values = record["values"]
    series, hours = read_values(resolve(values["path"], root), values["sha256"])
    values_ref = {"path_hint": values["path"], "sha256": values["sha256"], "rows": len(hours)}
    return inputs, values_ref, (series, hours)


def check_cutoff(record, cutoff):
    """The command's explicit ``--cutoff`` must name the method record's own cutoff instant."""
    _require(_text(cutoff), "CUTOFF_MISMATCH")
    _require(_instant(cutoff, "CUTOFF_MISMATCH")
             == _instant(record["information_cutoff"], "METHOD_INVALID"), "CUTOFF_MISMATCH")


def build_issue(record, *, outlook_id, issued_at, issuer, cutoff, archive=None, root=ROOT):
    """A first-issue ``OutlookRecord`` from a verified method record (no ``supersedes``).

    With ``archive``, a record whose values digest equals the newest issued
    vintage of the same target (series table and column, horizon) is refused
    ``REPEATS_PREDECESSOR``: issuing it again would say nothing new.
    """
    check_cutoff(record, cutoff)
    inputs, values_ref, _hours = verify_method_inputs(record, root)
    outlook = build_outlook(**_candidate(record, inputs, values_ref, outlook_id=outlook_id,
                                         issuer=issuer), issued_at=issued_at)
    if archive is not None:
        newest = newest_vintage(archive, outlook)
        _require(newest is None or newest["values_ref"]["sha256"] != values_ref["sha256"],
                 "REPEATS_PREDECESSOR")
    return outlook


def newest_vintage(archive, outlook):
    """The newest issued vintage of ``outlook``'s target, or ``None``; ``outlook`` itself excluded."""
    newest = None
    for other_id in archive.issue_ids():
        if other_id == outlook["outlook_id"]:
            continue
        other = archive.outlook(other_id)
        if _target(other) != _target(outlook):
            continue
        if newest is None or (_instant(other["issued_at"], "PREVIEW_INVALID"), other_id) > (
                _instant(newest["issued_at"], "PREVIEW_INVALID"), newest["outlook_id"]):
            newest = other
    return newest


def _candidate(record, inputs, values_ref, *, outlook_id, issuer):
    return {
        "outlook_id": outlook_id,
        "information_cutoff": record["information_cutoff"],
        "horizon": dict(record["horizon"]),
        "target_series_ref": dict(record["target_series_ref"]),
        "inputs": inputs,
        "assumption_ids": list(record["assumption_ids"]),
        "model_version": record["method_version"],
        "values_ref": values_ref,
        "issuer": issuer,
        "synthetic": record["synthetic"],
    }


# --- the values files and the delta -----------------------------------------


def read_values(path, sha256):
    """One values file read by digest: ``(series header or None, {hour_start: Decimal})``."""
    digest, raw = _sha256(path, "VALUES_UNREADABLE")
    _require(digest == sha256, "VALUES_DIGEST_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"), parse_float=Decimal, parse_int=Decimal)
    except (UnicodeDecodeError, ValueError, InvalidOperation):
        raise ReissueError("VALUES_UNREADABLE") from None
    _require(type(payload) is dict and type(payload.get("hours")) is list and payload["hours"],
             "VALUES_SHAPE")
    hours = {}
    for row in payload["hours"]:
        _require(type(row) is dict and _text(row.get("hour_start")), "VALUES_SHAPE")
        value = row.get("value")
        _require(isinstance(value, Decimal) and value.is_finite(), "VALUES_SHAPE")
        _require(row["hour_start"] not in hours, "VALUES_SHAPE")
        hours[row["hour_start"]] = value
    series = payload.get("series")
    return (series if type(series) is str else None), hours


def _fixed(number):
    return format(number.quantize(DELTA_PLACES), "f")


def compute_delta(predecessor, new_values_ref, *, root=ROOT, new_values=None):
    """The ``delta`` block: both values files read by digest, the difference per horizon.

    ``REPEATS_PREDECESSOR`` when the two digests are equal (checked first) or
    when every hourly value is equal.
    """
    previous_digest = predecessor["values_ref"]["sha256"]
    if previous_digest == new_values_ref["sha256"]:
        raise ReissueError("REPEATS_PREDECESSOR")
    old_series, old_hours = read_values(resolve(predecessor["values_ref"]["path_hint"], root),
                                        previous_digest)
    if new_values is None:
        new_values = read_values(resolve(new_values_ref["path_hint"], root), new_values_ref["sha256"])
    new_series, new_hours = new_values
    _require(set(old_hours) == set(new_hours), "HOURS_MISMATCH")
    _require(old_series is None or new_series is None or old_series == new_series, "HOURS_MISMATCH")
    differences = [new_hours[hour] - old_hours[hour] for hour in sorted(new_hours)]
    if all(item == 0 for item in differences):
        raise ReissueError("REPEATS_PREDECESSOR")
    count = Decimal(len(differences))
    horizon = predecessor["horizon"]
    return {
        "previous_values_digest": previous_digest,
        "new_values_digest": new_values_ref["sha256"],
        "horizons": [{
            "label": horizon["label"],
            "start": horizon["start"],
            "end": horizon["end"],
            "hours": len(differences),
            "mean_difference": _fixed(sum(differences) / count),
            "mean_abs_difference": _fixed(sum(abs(item) for item in differences) / count),
            "min_difference": _fixed(min(differences)),
            "max_difference": _fixed(max(differences)),
        }],
    }


# --- the marks and the predecessor ------------------------------------------


def stored_mark(archive, mark):
    """The stored mark with this record's digest; a mark outside the archive's store is refused."""
    try:
        dependency.validate_mark(mark)
    except dependency.DependencyError:
        raise ReissueError("MARK_UNKNOWN") from None
    for item in dependency.StaleMarks(archive.root).marks(mark["outlook_id"]):
        if item["content_digest"] == mark["content_digest"]:
            return item
    raise ReissueError("MARK_UNKNOWN")


def read_mark_file(path):
    """One mark file as JSON; the archive's store decides whether it is a mark (:func:`stored_mark`)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise ReissueError("MARK_UNKNOWN") from None


def _target(outlook):
    return (outlook["target_series_ref"]["table"], outlook["target_series_ref"]["column"],
            outlook["horizon"]["label"], _instant(outlook["horizon"]["start"], "PREVIEW_INVALID"),
            _instant(outlook["horizon"]["end"], "PREVIEW_INVALID"))


def _predecessor(archive, marks):
    """The one vintage every mark names, by its exact stored bytes, and the newest of its target."""
    _require(marks, "MARK_UNKNOWN")
    named = {(mark["outlook_id"], mark["outlook_digest"]) for mark in marks}
    _require(len(named) == 1, "MARKS_DISAGREE")
    outlook_id, outlook_digest = named.pop()
    try:
        predecessor = archive.outlook(outlook_id)
    except OutlookError:
        raise ReissueError("PREDECESSOR_CHANGED") from None
    _require(predecessor["content_digest"] == outlook_digest, "PREDECESSOR_CHANGED")
    return _newest_or_refuse(archive, predecessor)


def _named_predecessor(archive, outlook_id):
    """The vintage a mark-free re-issue names by id, and the newest of its target."""
    try:
        predecessor = archive.outlook(outlook_id)
    except OutlookError:
        raise ReissueError("PREDECESSOR_UNKNOWN") from None
    return _newest_or_refuse(archive, predecessor)


def _newest_or_refuse(archive, predecessor):
    # A re-issue replaces the current vintage; a mark on an older one (every vintage
    # resting on a changed belief is marked) is answered by re-issuing the newest.
    newest = newest_vintage(archive, predecessor)
    _require(newest is None or _instant(newest["issued_at"], "PREVIEW_INVALID")
             < _instant(predecessor["issued_at"], "PREVIEW_INVALID"), "NOT_LATEST_VINTAGE")
    return predecessor


# --- the preview ------------------------------------------------------------


def build_preview(archive, marks, method_record_path, *, outlook_id, issuer, cutoff,
                  supersedes=None, reason=None, root=ROOT):
    """The ``ReissuePreview`` the dock shows before the person confirms; nothing is written.

    Two ways to name the predecessor. With ``marks`` (stale-mark records read
    from files or from the store; each must be stored in ``archive``'s mark
    store and all must name one vintage) the reason is ``belief_changed``. With
    no mark, ``supersedes`` names the vintage by id and ``reason`` is
    ``method_changed`` (the method version must differ from the predecessor's)
    or ``inputs_refreshed`` (an input digest must differ). ``method_record_path``
    is the method run's record as the command names it.
    """
    if marks:
        _require(reason in (None, "belief_changed") and supersedes is None, "REASON_INVALID")
        reason = "belief_changed"
        stored = [stored_mark(archive, mark) for mark in marks]
        predecessor = _predecessor(archive, stored)
    else:
        _require(reason in REASONS and reason != "belief_changed" and _text(supersedes),
                 "REASON_INVALID")
        stored = []
        predecessor = _named_predecessor(archive, supersedes)
    record, method_digest = load_method_record(resolve(method_record_path, root))
    check_cutoff(record, cutoff)
    inputs, values_ref, new_values = verify_method_inputs(record, root)
    candidate = _candidate(record, inputs, values_ref, outlook_id=outlook_id, issuer=issuer)
    if reason == "method_changed":
        _require(candidate["model_version"] != predecessor["model_version"], "METHOD_UNCHANGED")
    elif reason == "inputs_refreshed":
        _require({item["name"]: item["digest"] for item in candidate["inputs"]}
                 != {item["name"]: item["digest"] for item in predecessor["inputs"]},
                 "INPUTS_UNCHANGED")
    # One way: a synthetic predecessor or a demonstration mark makes only a
    # synthetic re-issue, and the method record must say so itself.
    rests_on_synthetic = predecessor["synthetic"] or any(mark["synthetic"] for mark in stored)
    _require(candidate["synthetic"] or not rests_on_synthetic, "SYNTHETIC_ONE_WAY")
    series = (candidate["target_series_ref"].get("table"), candidate["target_series_ref"].get("column"))
    _require(series == (predecessor["target_series_ref"]["table"],
                        predecessor["target_series_ref"]["column"]), "TARGET_MISMATCH")
    horizon = candidate["horizon"]
    try:
        same_horizon = (horizon.get("label") == predecessor["horizon"]["label"]
                        and _record_instant(horizon.get("start")) == _record_instant(predecessor["horizon"]["start"])
                        and _record_instant(horizon.get("end")) == _record_instant(predecessor["horizon"]["end"]))
    except OutlookError:
        same_horizon = False
    _require(same_horizon, "TARGET_MISMATCH")
    delta = compute_delta(predecessor, values_ref, root=root, new_values=new_values)
    preview = {
        "schema_version": SCHEMA_VERSION,
        "kind": PREVIEW_KIND,
        "predecessor": {
            "outlook_id": predecessor["outlook_id"],
            "outlook_digest": predecessor["content_digest"],
            "values_digest": predecessor["values_ref"]["sha256"],
            "issued_at": predecessor["issued_at"],
        },
        "reason": reason,
        "stale_marks": sorted(({key: mark[key] for key in PREVIEW_MARK_KEYS} for mark in stored),
                              key=lambda item: item["content_digest"]),
        "changed_assumption_ids": sorted({mark["assumption_id"] for mark in stored}),
        "method_record": {"path_hint": str(method_record_path), "sha256": method_digest,
                          "method_version": record["method_version"]},
        "information_cutoff": record["information_cutoff"],
        "outlook": candidate,
        "delta": delta,
    }
    try:
        preview["content_digest"] = compute_content_digest(preview)
    except CanonicalizationError:
        raise ReissueError("PREVIEW_INVALID") from None
    return validate_preview(preview)


def validate_preview(record):
    """One preview's closed shape and sealed digest, and its parts consistent with each other."""
    _require(type(record) is dict and set(record) == PREVIEW_KEYS, "PREVIEW_INVALID")
    _require(record["schema_version"] == SCHEMA_VERSION and record["kind"] == PREVIEW_KIND,
             "PREVIEW_INVALID")
    try:
        _require(compute_content_digest(record) == record["content_digest"], "PREVIEW_INVALID")
    except CanonicalizationError:
        raise ReissueError("PREVIEW_INVALID") from None
    predecessor = record["predecessor"]
    _require(type(predecessor) is dict and set(predecessor) == PREDECESSOR_KEYS, "PREVIEW_INVALID")
    _require(type(record["reason"]) is str and record["reason"] in REASONS, "PREVIEW_INVALID")
    marks = record["stale_marks"]
    _require(type(marks) is list and (bool(marks) == (record["reason"] == "belief_changed")),
             "PREVIEW_INVALID")
    for mark in marks:
        _require(type(mark) is dict and set(mark) == PREVIEW_MARK_KEYS, "PREVIEW_INVALID")
    _require(record["changed_assumption_ids"] == sorted({mark["assumption_id"] for mark in marks}),
             "PREVIEW_INVALID")
    method = record["method_record"]
    _require(type(method) is dict and set(method) == METHOD_REF_KEYS, "PREVIEW_INVALID")
    candidate = record["outlook"]
    _require(type(candidate) is dict and set(candidate) == CANDIDATE_KEYS, "PREVIEW_INVALID")
    _require(candidate["information_cutoff"] == record["information_cutoff"], "PREVIEW_INVALID")
    _require(candidate["model_version"] == method["method_version"], "PREVIEW_INVALID")
    delta = record["delta"]
    _require(type(delta) is dict and delta.get("previous_values_digest") == predecessor["values_digest"]
             and delta.get("new_values_digest") == candidate["values_ref"]["sha256"], "PREVIEW_INVALID")
    # The record the confirmed issue would write must pass the archive's own rules;
    # the candidate's horizon start (the latest instant an issue may carry) stands
    # in for the issue instant, and a labelled placeholder for the confirmation.
    try:
        _vintage(record, issued_at=candidate["horizon"]["start"], confirmation_ref=PREVIEW_CHECK_REF)
    except OutlookError as error:
        if error.code == "REPEATS_PREDECESSOR":
            raise ReissueError("REPEATS_PREDECESSOR") from None
        raise ReissueError("PREVIEW_INVALID") from None
    return record


def _vintage(preview, *, issued_at, confirmation_ref):
    """The ``OutlookRecord`` a confirmed preview writes: the candidate plus ``supersedes``."""
    candidate = preview["outlook"]
    supersedes = {
        "outlook_id": preview["predecessor"]["outlook_id"],
        "outlook_digest": preview["predecessor"]["outlook_digest"],
        "reason": preview["reason"],
        "stale_marks": [{"content_digest": mark["content_digest"],
                         "assumption_id": mark["assumption_id"],
                         "synthetic": mark["synthetic"]} for mark in preview["stale_marks"]],
        "changed_assumption_ids": list(preview["changed_assumption_ids"]),
        "delta": preview["delta"],
        "confirmation_ref": confirmation_ref,
    }
    return build_outlook(**candidate, issued_at=issued_at, supersedes=supersedes)


def issue_confirmed(archive, preview, *, issued_at, confirmation_ref, outlook_id, issuer,
                    method_record, cutoff, root=ROOT):
    """Turn a confirmed preview into the issued vintage; the archive is re-read first.

    ``confirmation_ref`` names the person's recorded confirmation and is written
    into the vintage's ``supersedes`` block. ``outlook_id``, ``issuer``,
    ``method_record`` (a path) and ``cutoff`` are what the confirming call states
    — the command's own flags, or the dock's confirmation arguments — and not
    read from the preview: a preview that names another id, issuer, method
    record or cutoff is ``PREVIEW_MISMATCH``, so an edited and resealed preview
    cannot change who issues what. The preview is then rebuilt from the live
    archive with those four values; any difference in digest is
    ``PREVIEW_STALE`` and nothing is written.
    """
    _require(_text(confirmation_ref), "CONFIRMATION_MISSING")
    validate_preview(preview)
    _require(preview["outlook"]["outlook_id"] == outlook_id
             and preview["outlook"]["issuer"] == issuer, "PREVIEW_MISMATCH")
    _require(_text(cutoff) and _instant(cutoff, "PREVIEW_MISMATCH")
             == _instant(preview["information_cutoff"], "PREVIEW_INVALID"), "PREVIEW_MISMATCH")
    _require(resolve(str(method_record), root).resolve()
             == resolve(preview["method_record"]["path_hint"], root).resolve(), "PREVIEW_MISMATCH")
    marks = []
    for mark in preview["stale_marks"]:
        found = [item for item in dependency.StaleMarks(archive.root).marks(
            preview["predecessor"]["outlook_id"]) if item["content_digest"] == mark["content_digest"]]
        _require(found, "PREVIEW_STALE")
        marks.append(found[0])
    # A rebuild that is refused carries its own reason (a newer vintage, a moved
    # input); a rebuild that succeeds with other bytes is ``PREVIEW_STALE``.
    mark_free = preview["reason"] != "belief_changed"
    rebuilt = build_preview(archive, marks, preview["method_record"]["path_hint"],
                            outlook_id=outlook_id, issuer=issuer, cutoff=cutoff,
                            supersedes=preview["predecessor"]["outlook_id"] if mark_free else None,
                            reason=preview["reason"] if mark_free else None, root=root)
    _require(rebuilt["content_digest"] == preview["content_digest"], "PREVIEW_STALE")
    record = _vintage(rebuilt, issued_at=issued_at, confirmation_ref=confirmation_ref)
    return archive.issue(record)


__all__ = [
    "MESSAGES",
    "PREVIEW_KIND",
    "ReissueError",
    "build_issue",
    "build_preview",
    "check_cutoff",
    "compute_delta",
    "issue_confirmed",
    "load_method_record",
    "newest_vintage",
    "read_mark_file",
    "read_values",
    "stored_mark",
    "validate_method_record",
    "validate_preview",
    "verify_method_inputs",
]
