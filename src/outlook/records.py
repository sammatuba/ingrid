"""Outlook archive records: an outlook issued once, and the receipt that scores it later.

The archive is a directory of JSON documents, each written once and never edited:

* ``<root>/outlooks/<outlook_id>.json`` — one ``OutlookRecord`` per issue.
* ``<root>/receipts/<outlook_id>.<version_key>.json`` — one ``ScoringReceipt``
  per scored run of one outlook against one final series version. The file name
  is that ``(outlook_id, final_series_version)`` pair, so the exclusive create
  of the file is what makes a pair scoring-once.
* ``<root>/attributions/<key>.json`` — one ``Attribution`` per statement about
  a miss, appended beside the sealed receipt it explains and never inside it.
  The key is derived from the record's own content (the receipt's digest, the
  cause and its reference, the author, the statement and the provenance), so a
  duplicate is refused by the exclusive create of one file rather than by a
  scan: there is no sequence number and no "next" to compute.

An ``OutlookRecord`` fixes what an outlook said and what it rested on at the
moment it was issued: the information cutoff, the target series (table, column,
version), the inputs by name and digest, the accepted assumption ids, the model
version, the horizon (label from the price target contract, and the half-open
interval the outlook predicts), the values file by path hint, digest and row
count — the values themselves never live in Git — and the issuer. An outlook is
issued once: :meth:`OutlookArchive.issue` refuses a second write for the same
``outlook_id`` and nothing in this module updates an issued document. A stored
document is read back through its canonical ``content_digest``, so an edit made
outside this API is reported by :meth:`OutlookArchive.verify`; and a receipt
cites the issued bytes by digest, so replacing an outlook after issue breaks its
receipts and the mismatch is reported. Content identity is not truth: the
digest proves the bytes did not change, not that the outlook was any good.

A ``ScoringReceipt`` records one scoring run once the final settlement prices
for a window inside the outlook's horizon have settled. It names the final
series version it was scored against (``final_series_version``) and that
series' bytes (``final_series_digest``); it carries the settled ``window`` —
the whole predicted interval or any slice of it, never a window that reaches
outside it, so no interval the outlook never predicted is scored against it —
the metric rows per horizon and slice (administered-pricing intervals are a
separate slice, per the price target contract), and the coverage: intervals
scored, and intervals skipped with their reasons. The receipt is written after
the window it scores ended, so "once prices settle" is a checked relation on
the record, not a claim. One receipt per ``(outlook_id, final_series_version)``
pair: scoring the same settled series twice is refused as a duplicate. The pair
is the receipt's file name too, so that rule is the exclusive create of one
file and not a scan of stored receipts — two concurrent writers race on the
same path and exactly one of them can create it.
Provenance follows the evidence, one way: a receipt that declares real results
is refused against an outlook issued from synthetic inputs, so synthetic
forecast results never appear as a real score; a receipt that declares itself
``synthetic`` is honest about its own metrics and may score either outlook.

An ``Attribution`` records one author's statement that a named part of a miss is
owed to a belief that was wrong, a signal that arrived late, or the method. It
names the exact receipt bytes it explains and the receipt's outlook, so it can
never be read against another run; its ``cause`` is one of the three the
foundation page fixes, and the cause carries its own reference (a belief the
outlook rested on, a signal dated after the outlook's information cutoff and
effective before the scored window ended, or the outlook's own model version).
The author is a process rule, not a validator rule: the validator checks
``attributed_by`` is non-blank, and the only write path is the person-driven
command under ``scripts/outlook/`` — no model path calls ``append_attribution``.
The shares of one receipt are not refused at write time (one exclusive create
cannot see its siblings); :meth:`OutlookArchive.verify` reports a sum above one
as a problem, and the desk shows that problem beside the receipt.

A re-issued ``OutlookRecord`` (OUT-1) carries one optional key more,
``supersedes``: the predecessor it replaces by id and exact issued bytes, the
reason (``belief_changed``, answering stale marks; or ``method_changed`` or
``inputs_refreshed``, without a mark), the stale marks that made the predecessor
stale (digest, assumption, provenance; none for the two mark-free reasons),
the changed assumption ids, the ``delta`` block (the predecessor's values
digest, the new values digest, and the difference per horizon computed from the
two values files) and the confirmation the issue rests on (non-blank text: no
re-issue record exists without a recorded decision). A record without the
key is the first-issue shape, byte for byte, so every vintage issued before the
key existed keeps its digest. :meth:`OutlookArchive.issue` checks the block
against the stored predecessor before the exclusive create, and
:meth:`OutlookArchive.verify` checks it again on read. A vintage whose values
digest equals its predecessor's is refused ``REPEATS_PREDECESSOR``. Provenance
runs one way here too: a successor that rests on a synthetic predecessor or on a
demonstration mark must itself be ``synthetic``; a synthetic successor may
supersede either. The marks themselves live in :mod:`src.outlook.dependency`,
which imports this module, so the mark store is read by
:mod:`src.outlook.reissue` and only the mark's identity travels in the record.

Digests are lowercase SHA-256 hex over the canonical JSON of the record with the
top-level ``content_digest`` key removed (:mod:`src.contracts.jsonutil`), the
convention the h0 review records use. The builders write timestamps in UTC
``Z`` form, so the same instants give the same bytes whatever offset was typed.
This module imports only the standard library and that repository module, which
is itself standard-library only.

Frozen elsewhere: the h0 record kinds in :mod:`src.review.records` and the
judgment contracts are not this archive and are not touched here.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.contracts.jsonutil import (
    CanonicalizationError,
    canonical_dumps,
    compute_content_digest,
    parse_json,
)

SCHEMA_VERSION = "outlook.v1"
OUTLOOK_KIND = "OutlookRecord"
RECEIPT_KIND = "ScoringReceipt"
#: The third record kind the archive holds beside the two of ``KINDS``: a statement
#: about a miss, appended beside the receipt it explains. ``KINDS`` is the two the
#: archive was opened with and stays as it was; this kind is its own name.
ATTRIBUTION_KIND = "Attribution"
KINDS = (OUTLOOK_KIND, RECEIPT_KIND)

#: The foundation page's three causes, closed: a belief that was wrong, a signal
#: that arrived late, or the method. A fourth cause is a reviewed change to the
#: intent, never a free text value.
CAUSES = ("belief", "signal", "method")

#: The horizon labels of the price target contract (PRICE-0, "Horizons scored").
HORIZONS = ("day", "week", "month")

#: Metric rows are scored in the market slice (non-administered) or, separately,
#: in the administered-pricing slice; AP intervals are never mixed into "market
#: skill" (PRICE-0, "Administered pricing").
SLICES = ("market", "ap")

OUTLOOK_KEYS = frozenset({
    "schema_version", "kind", "outlook_id", "issued_at", "information_cutoff",
    "horizon", "target_series_ref", "inputs", "assumption_ids", "model_version",
    "values_ref", "issuer", "synthetic", "content_digest",
})
#: The one optional key of a re-issued outlook (OUT-1). A first issue carries
#: :data:`OUTLOOK_KEYS` exactly; a re-issue carries those and this key.
SUPERSEDES_KEY = "supersedes"
SUPERSEDES_KEYS = frozenset({
    "outlook_id", "outlook_digest", "reason", "stale_marks", "changed_assumption_ids", "delta",
    "confirmation_ref",
})
#: Why a vintage is re-issued, closed. ``belief_changed`` answers stale marks (at
#: least one); ``method_changed`` and ``inputs_refreshed`` re-issue without a mark
#: and need, respectively, another model version or another input digest than
#: the predecessor's (OUT-1 rework round 1, the orchestrator's decision).
REASONS = ("belief_changed", "method_changed", "inputs_refreshed")
SUPERSEDES_MARK_KEYS = frozenset({"content_digest", "assumption_id", "synthetic"})
DELTA_KEYS = frozenset({"previous_values_digest", "new_values_digest", "horizons"})
#: One horizon's difference, new minus previous, over the hours both values files
#: carry: the count of hours and four decimal strings.
DELTA_HORIZON_KEYS = frozenset({
    "label", "start", "end", "hours", "mean_difference", "mean_abs_difference",
    "min_difference", "max_difference",
})
RECEIPT_KEYS = frozenset({
    "schema_version", "kind", "outlook_id", "outlook_digest", "scored_at",
    "final_series_version", "final_series_digest", "window", "metrics",
    "coverage", "synthetic", "content_digest",
})
#: An attribution's keys, exactly. The three reference fields are always present;
#: the two the cause does not use are ``None``, so the record's shape does not
#: depend on its cause and the key dict can carry every absent reference as null.
ATTRIBUTION_KEYS = frozenset({
    "schema_version", "kind", "outlook_id", "outlook_digest", "receipt_digest",
    "cause", "assumption_id", "signal_ref", "method_ref", "share", "statement",
    "attributed_by", "attributed_at", "synthetic", "content_digest",
})
SIGNAL_KEYS = frozenset({"source", "available_at", "effective_at"})
HORIZON_KEYS = frozenset({"label", "start", "end"})
SERIES_KEYS = frozenset({"table", "column", "version"})
INPUT_KEYS = frozenset({"name", "digest"})
VALUES_KEYS = frozenset({"path_hint", "sha256", "rows"})
WINDOW_KEYS = frozenset({"start", "end"})
#: The scorecard metrics the price target contract fixes (bias, MAE, RMSE and
#: pinball at p10, p50, p90). A new metric is a reviewed change to this kind.
METRIC_KEYS = frozenset({
    "horizon", "slice", "intervals", "bias", "mae", "rmse",
    "pinball_p10", "pinball_p50", "pinball_p90",
})
NONNEGATIVE_METRICS = ("mae", "rmse", "pinball_p10", "pinball_p50", "pinball_p90")
COVERAGE_KEYS = frozenset({"scored", "skipped"})
SKIP_KEYS = frozenset({"count", "reason"})

DIGEST = re.compile(r"^[0-9a-f]{64}$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
DECIMAL = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
#: An outlook id doubles as a file name, so it is restricted to one safe path
#: segment; ``..`` can never appear because the first character is alphanumeric
#: and the set excludes ``/``.
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
#: An assumption id is a register id (``<family>:<slug>``; ARCH-2's own validator
#: fixes that shape). The one separator the register uses is allowed in this
#: field and nowhere else, because an assumption id never names a file — the
#: archive's directory-safety rule is about ``outlook_id``, which keeps
#: :data:`IDENTIFIER` alone.
ASSUMPTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

#: Stable refusal codes with fixed, non-disclosing text; nothing here echoes
#: caller input or a raw exception.
MESSAGES = {
    "OUTLOOK_INVALID": "the outlook record does not satisfy the archive contract",
    "RECEIPT_INVALID": "the scoring receipt does not satisfy the archive contract",
    "ATTRIBUTION_INVALID": "the attribution does not satisfy the archive contract",
    "OUTLOOK_IMMUTABLE": "an outlook is issued once and cannot be replaced or edited",
    "OUTLOOK_UNKNOWN": "no outlook with that identifier is in the archive",
    "OUTLOOK_DIGEST_MISMATCH": "the receipt cites an outlook other than the one stored under that identifier",
    "RECEIPT_DUPLICATE": "that outlook is already scored against this final series version",
    "RECEIPT_UNKNOWN": "no receipt with that digest is in the archive",
    "ATTRIBUTION_DUPLICATE": "that statement is already attributed to that receipt",
    "SHARE_OVER_ONE": "the shares attributed to one receipt sum above one",
    "ARCHIVE_TAMPERED": "a stored record does not match its own content digest or the record contract",
    "ARCHIVE_IO": "the archive file could not be written or read",
    "SUPERSEDES_INVALID": "the re-issued outlook does not match the predecessor it names",
    "REPEATS_PREDECESSOR": "the new vintage's values repeat its predecessor's, so it is not issued",
}


class OutlookError(ValueError):
    """An archive refusal whose text :data:`MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, MESSAGES[code])


def _require(condition, code="OUTLOOK_INVALID"):
    if not condition:
        raise OutlookError(code)


def _text(value):
    return type(value) is str and bool(value.strip())


def _digest_text(value):
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _identifier(value):
    return type(value) is str and IDENTIFIER.fullmatch(value) is not None


def _assumption_id(value):
    """A register id: the ``<family>:<slug>`` shape of :mod:`src.outlook.register`."""
    return type(value) is str and ASSUMPTION_ID.fullmatch(value) is not None


def _instant(value, code="OUTLOOK_INVALID"):
    """Parse one offset-bearing timestamp to an aware UTC datetime."""
    _require(type(value) is str and INSTANT.fullmatch(value) is not None, code)
    if not value.endswith("Z"):
        _require(int(value[-5:-3]) <= 23 and int(value[-2:]) <= 59, code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise OutlookError(code) from None
    return parsed.astimezone(timezone.utc)


def _decimal_text(value, nonnegative=False, code="OUTLOOK_INVALID"):
    _require(type(value) is str and DECIMAL.fullmatch(value) is not None, code)
    try:
        number = Decimal(value)
    except InvalidOperation:  # unreachable behind DECIMAL; kept for safety
        raise OutlookError(code) from None
    _require(number.is_finite(), code)
    if nonnegative:
        _require(number >= 0, code)
    return number


def _utc(value):
    """One timestamp in UTC ``Z`` form when it parses; anything else passes through."""
    if type(value) is str and INSTANT.fullmatch(value) is not None:
        return _instant(value).isoformat().replace("+00:00", "Z")
    return value


def _utc_edges(scope):
    """The ``start``/``end`` pair of one nested object, in UTC ``Z`` form."""
    for edge in ("start", "end"):
        if type(scope.get(edge)) is str and INSTANT.fullmatch(scope[edge]) is not None:
            scope[edge] = _utc(scope[edge])
    return scope


def _seal(record):
    """Attach the canonical ``content_digest`` of everything else in the record."""
    try:
        record["content_digest"] = compute_content_digest(record)
    except CanonicalizationError:
        raise OutlookError("OUTLOOK_INVALID") from None
    return record


def _check_stored_digest(record, code):
    _require(_digest_text(record["content_digest"]), code)
    try:
        recomputed = compute_content_digest(record)
    except CanonicalizationError:
        raise OutlookError(code) from None
    _require(recomputed == record["content_digest"], code)


def _copy_supersedes(block):
    """A deep enough copy of one ``supersedes`` block, its horizon edges in UTC ``Z`` form."""
    if type(block) is not dict:
        return block
    block = dict(block)
    if type(block.get("stale_marks")) is list:
        block["stale_marks"] = [dict(item) if type(item) is dict else item
                                for item in block["stale_marks"]]
    if type(block.get("changed_assumption_ids")) is list:
        block["changed_assumption_ids"] = list(block["changed_assumption_ids"])
    delta = block.get("delta")
    if type(delta) is dict:
        delta = dict(delta)
        if type(delta.get("horizons")) is list:
            delta["horizons"] = [_utc_edges(dict(item)) if type(item) is dict else item
                                 for item in delta["horizons"]]
        block["delta"] = delta
    return block


def build_outlook(*, outlook_id, issued_at, information_cutoff, horizon, target_series_ref,
                  inputs, assumption_ids, model_version, values_ref, issuer, synthetic,
                  supersedes=None):
    """Seal and validate one ``OutlookRecord``; the record is issued through the archive.

    Timestamps are normalized to UTC ``Z`` form here, as the time contract
    requires, so two records that name the same instants have the same bytes and
    the same digest whatever offset the caller typed. The validator on its own
    accepts any offset-bearing timestamp and never rewrites stored content.

    ``supersedes`` is the re-issue block (OUT-1); ``None`` leaves the key out, so
    a first issue has exactly the shape and bytes it always had.
    """
    horizon = _utc_edges(dict(horizon)) if type(horizon) is dict else horizon
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": OUTLOOK_KIND,
        "outlook_id": outlook_id,
        "issued_at": _utc(issued_at),
        "information_cutoff": _utc(information_cutoff),
        "horizon": horizon,
        "target_series_ref": dict(target_series_ref) if type(target_series_ref) is dict else target_series_ref,
        "inputs": [dict(item) if type(item) is dict else item for item in inputs] if type(inputs) is list else inputs,
        "assumption_ids": list(assumption_ids) if type(assumption_ids) is list else assumption_ids,
        "model_version": model_version,
        "values_ref": dict(values_ref) if type(values_ref) is dict else values_ref,
        "issuer": issuer,
        "synthetic": synthetic,
    }
    if supersedes is not None:
        record[SUPERSEDES_KEY] = _copy_supersedes(supersedes)
    return validate_outlook(_seal(record))


def validate_outlook(record):
    """Validate one ``OutlookRecord`` envelope, its content digest included."""
    _require(type(record) is dict)
    _require(set(record) == OUTLOOK_KEYS or set(record) == OUTLOOK_KEYS | {SUPERSEDES_KEY})
    _require(record["schema_version"] == SCHEMA_VERSION and record["kind"] == OUTLOOK_KIND)
    _check_stored_digest(record, "OUTLOOK_INVALID")
    _require(_identifier(record["outlook_id"]))
    issued = _instant(record["issued_at"])
    cutoff = _instant(record["information_cutoff"])
    # The time contract: evidence has a cutoff and an outlook cannot cite
    # information from after it was issued, so the cutoff precedes the issue.
    _require(cutoff <= issued)
    horizon = record["horizon"]
    _require(type(horizon) is dict and set(horizon) == HORIZON_KEYS)
    _require(type(horizon["label"]) is str and horizon["label"] in HORIZONS)
    start, end = _instant(horizon["start"]), _instant(horizon["end"])
    _require(start < end)
    # The horizon is forecast forward from the origin: its first interval is not
    # before the issue (PRICE-2 scores baselines by rolling origin).
    _require(issued <= start)
    series = record["target_series_ref"]
    _require(type(series) is dict and set(series) == SERIES_KEYS)
    _require(all(_text(series[key]) for key in SERIES_KEYS))
    inputs = record["inputs"]
    _require(type(inputs) is list and inputs)
    names = []
    for item in inputs:
        _require(type(item) is dict and set(item) == INPUT_KEYS)
        _require(_text(item["name"]) and _digest_text(item["digest"]))
        names.append(item["name"])
    # A name twice over is one ambiguous input: the digest would not say which.
    _require(len(set(names)) == len(names))
    assumptions = record["assumption_ids"]
    _require(type(assumptions) is list and assumptions and all(_assumption_id(value) for value in assumptions))
    _require(len(set(assumptions)) == len(assumptions))
    _require(_text(record["model_version"]))
    values = record["values_ref"]
    _require(type(values) is dict and set(values) == VALUES_KEYS)
    _require(_text(values["path_hint"]) and _digest_text(values["sha256"]))
    _require(type(values["rows"]) is int and values["rows"] >= 0)
    _require(_text(record["issuer"]))
    _require(type(record["synthetic"]) is bool)
    if SUPERSEDES_KEY in record:
        _validate_supersedes(record)
    return record


def _validate_supersedes(record):
    """The record-only rules of a re-issue block; the predecessor is checked by the archive."""
    block = record[SUPERSEDES_KEY]
    _require(type(block) is dict and set(block) == SUPERSEDES_KEYS)
    _require(_identifier(block["outlook_id"]) and block["outlook_id"] != record["outlook_id"])
    _require(_digest_text(block["outlook_digest"]))
    _require(type(block["reason"]) is str and block["reason"] in REASONS)
    marks = block["stale_marks"]
    _require(type(marks) is list)
    # A belief change is answered from its marks, and only a belief change carries
    # marks: the two mark-free reasons carry none.
    _require(bool(marks) == (block["reason"] == "belief_changed"))
    for mark in marks:
        _require(type(mark) is dict and set(mark) == SUPERSEDES_MARK_KEYS)
        _require(_digest_text(mark["content_digest"]) and _assumption_id(mark["assumption_id"]))
        _require(type(mark["synthetic"]) is bool)
        # One way: a demonstration mark cannot make a real vintage.
        _require(record["synthetic"] or not mark["synthetic"])
    _require(len({mark["content_digest"] for mark in marks}) == len(marks))
    changed = block["changed_assumption_ids"]
    _require(type(changed) is list and all(_assumption_id(value) for value in changed))
    # The changed beliefs are exactly the ones the marks name, each once, sorted
    # (none when a re-issue carries no mark).
    _require(changed == sorted({mark["assumption_id"] for mark in marks}))
    # A re-issue is written on a recorded decision: the confirmation reference is
    # non-blank text on every record that carries this block.
    _require(_text(block["confirmation_ref"]))
    delta = block["delta"]
    _require(type(delta) is dict and set(delta) == DELTA_KEYS)
    _require(_digest_text(delta["previous_values_digest"]) and _digest_text(delta["new_values_digest"]))
    _require(delta["new_values_digest"] == record["values_ref"]["sha256"])
    if delta["previous_values_digest"] == delta["new_values_digest"]:
        raise OutlookError("REPEATS_PREDECESSOR")
    horizons = delta["horizons"]
    _require(type(horizons) is list and horizons)
    labels = []
    for item in horizons:
        _require(type(item) is dict and set(item) == DELTA_HORIZON_KEYS)
        _require(type(item["label"]) is str and item["label"] in HORIZONS)
        labels.append(item["label"])
        _require(_instant(item["start"]) == _instant(record["horizon"]["start"])
                 and _instant(item["end"]) == _instant(record["horizon"]["end"]))
        _require(type(item["hours"]) is int and item["hours"] >= 1)
        low = _decimal_text(item["min_difference"])
        high = _decimal_text(item["max_difference"])
        mean = _decimal_text(item["mean_difference"])
        _decimal_text(item["mean_abs_difference"], nonnegative=True)
        _require(low <= mean <= high)
    _require(len(set(labels)) == len(labels) and record["horizon"]["label"] in labels)


def check_supersedes(record, predecessor):
    """The link rules of a re-issue against the stored predecessor it names.

    The predecessor is the issued record under ``supersedes.outlook_id``: its
    bytes are the ones the block cites, its values digest is the block's
    ``previous_values_digest``, it predicts the same target series (table and
    column) over the same horizon, it rests on every changed assumption, and it
    was issued before the successor with a cutoff no later than the successor's.
    Provenance runs one way: a synthetic predecessor makes only a synthetic
    successor. ``None`` for a record that supersedes nothing.
    """
    validate_outlook(record)
    if SUPERSEDES_KEY not in record:
        return None
    validate_outlook(predecessor)
    block = record[SUPERSEDES_KEY]
    _require(predecessor["outlook_id"] == block["outlook_id"], "SUPERSEDES_INVALID")
    _require(predecessor["content_digest"] == block["outlook_digest"], "OUTLOOK_DIGEST_MISMATCH")
    _require(predecessor["values_ref"]["sha256"] == block["delta"]["previous_values_digest"],
             "SUPERSEDES_INVALID")
    if predecessor["values_ref"]["sha256"] == record["values_ref"]["sha256"]:
        raise OutlookError("REPEATS_PREDECESSOR")
    same_series = all(predecessor["target_series_ref"][key] == record["target_series_ref"][key]
                      for key in ("table", "column"))
    same_horizon = (predecessor["horizon"]["label"] == record["horizon"]["label"]
                    and _instant(predecessor["horizon"]["start"]) == _instant(record["horizon"]["start"])
                    and _instant(predecessor["horizon"]["end"]) == _instant(record["horizon"]["end"]))
    _require(same_series and same_horizon, "SUPERSEDES_INVALID")
    _require(set(block["changed_assumption_ids"]) <= set(predecessor["assumption_ids"]),
             "SUPERSEDES_INVALID")
    _require(_instant(predecessor["issued_at"]) < _instant(record["issued_at"]), "SUPERSEDES_INVALID")
    # A re-issue without a mark states what else moved, and it must have moved.
    if block["reason"] == "method_changed":
        _require(record["model_version"] != predecessor["model_version"], "SUPERSEDES_INVALID")
    elif block["reason"] == "inputs_refreshed":
        before = {item["name"]: item["digest"] for item in predecessor["inputs"]}
        after = {item["name"]: item["digest"] for item in record["inputs"]}
        _require(before != after, "SUPERSEDES_INVALID")
    _require(_instant(predecessor["information_cutoff"]) <= _instant(record["information_cutoff"]),
             "SUPERSEDES_INVALID")
    _require(record["synthetic"] or not predecessor["synthetic"], "SUPERSEDES_INVALID")
    return record


def build_receipt(outlook, *, scored_at, final_series_version, final_series_digest,
                  window, metrics, coverage, synthetic):
    """Seal and validate one ``ScoringReceipt`` against the outlook it scores.

    ``outlook`` is the issued record being scored; the receipt's
    ``outlook_id`` and ``outlook_digest`` are read from it, so a receipt that
    names some other revision cannot be built by accident.
    """
    validate_outlook(outlook)
    window = _utc_edges(dict(window)) if type(window) is dict else window
    receipt = validate_receipt(_seal({
        "schema_version": SCHEMA_VERSION,
        "kind": RECEIPT_KIND,
        "outlook_id": outlook["outlook_id"],
        "outlook_digest": outlook["content_digest"],
        "scored_at": _utc(scored_at),
        "final_series_version": final_series_version,
        "final_series_digest": final_series_digest,
        "window": window,
        "metrics": [dict(row) if type(row) is dict else row for row in metrics] if type(metrics) is list else metrics,
        "coverage": dict(coverage) if type(coverage) is dict else coverage,
        "synthetic": synthetic,
    }))
    _check_receipt_against_outlook(receipt, outlook)
    return receipt


def validate_receipt(record):
    """Validate one ``ScoringReceipt`` envelope; the outlook link is checked separately."""
    _require(type(record) is dict, "RECEIPT_INVALID")
    _require(set(record) == RECEIPT_KEYS, "RECEIPT_INVALID")
    _require(record["schema_version"] == SCHEMA_VERSION and record["kind"] == RECEIPT_KIND,
             "RECEIPT_INVALID")
    _check_stored_digest(record, "RECEIPT_INVALID")
    _require(_identifier(record["outlook_id"]), "RECEIPT_INVALID")
    # The receipt names the exact issued bytes it was scored against.
    _require(_digest_text(record["outlook_digest"]), "RECEIPT_INVALID")
    scored = _instant(record["scored_at"], "RECEIPT_INVALID")
    # The acceptance item itself: a scoring receipt names the final series
    # version it was scored against, and that version is its own bytes too.
    _require(_text(record["final_series_version"]), "RECEIPT_INVALID")
    _require(_digest_text(record["final_series_digest"]), "RECEIPT_INVALID")
    window = record["window"]
    _require(type(window) is dict and set(window) == WINDOW_KEYS, "RECEIPT_INVALID")
    window_start, window_end = _instant(window["start"], "RECEIPT_INVALID"), _instant(window["end"], "RECEIPT_INVALID")
    _require(window_start < window_end, "RECEIPT_INVALID")
    # "Once prices settle": the settled window is closed before the receipt is
    # written. No clock is read here; the relation is between the two fields.
    _require(scored >= window_end, "RECEIPT_INVALID")
    metrics = record["metrics"]
    _require(type(metrics) is list and metrics, "RECEIPT_INVALID")
    rows = set()
    for row in metrics:
        _require(type(row) is dict and set(row) == METRIC_KEYS, "RECEIPT_INVALID")
        _require(type(row["horizon"]) is str and row["horizon"] in HORIZONS
                 and type(row["slice"]) is str and row["slice"] in SLICES, "RECEIPT_INVALID")
        _require((row["horizon"], row["slice"]) not in rows, "RECEIPT_INVALID")
        rows.add((row["horizon"], row["slice"]))
        _require(type(row["intervals"]) is int and row["intervals"] >= 1, "RECEIPT_INVALID")
        for key in METRIC_KEYS - {"horizon", "slice", "intervals"}:
            _decimal_text(row[key], nonnegative=key in NONNEGATIVE_METRICS, code="RECEIPT_INVALID")
    coverage = record["coverage"]
    _require(type(coverage) is dict and set(coverage) == COVERAGE_KEYS, "RECEIPT_INVALID")
    _require(type(coverage["scored"]) is int and coverage["scored"] >= 0, "RECEIPT_INVALID")
    _require(type(coverage["skipped"]) is list, "RECEIPT_INVALID")
    for item in coverage["skipped"]:
        _require(type(item) is dict and set(item) == SKIP_KEYS, "RECEIPT_INVALID")
        # A skipped interval carries its reason; a silent skip is not coverage.
        _require(type(item["count"]) is int and item["count"] >= 1 and _text(item["reason"]),
                 "RECEIPT_INVALID")
    _require(type(record["synthetic"]) is bool, "RECEIPT_INVALID")
    return record


def _check_receipt_against_outlook(receipt, outlook):
    """The link rules that need both records: identity, bytes, provenance, window."""
    validate_outlook(outlook)
    _require(receipt["outlook_id"] == outlook["outlook_id"], "RECEIPT_INVALID")
    _require(receipt["outlook_digest"] == outlook["content_digest"], "OUTLOOK_DIGEST_MISMATCH")
    # Provenance is inherited: a receipt that declares real results cannot be
    # linked to an outlook issued from synthetic inputs, or a fixture forecast
    # would be scored as if it were real. The other direction is honest by its
    # own declaration — a synthetic receipt says so about its metrics — and is
    # allowed, so only the false claim is refused.
    _require(not outlook["synthetic"] or receipt["synthetic"], "RECEIPT_INVALID")
    # A receipt scores a settled window of the horizon the outlook predicted;
    # the window lies inside the predicted half-open interval, so no interval
    # the outlook never predicted is scored against it. Scoring after the issue
    # needs no separate check: the record rules already put ``scored_at`` at or
    # after the window end and the window end at or before the horizon end,
    # which the outlook rules place at or after its issue.
    a, b = _instant(receipt["window"]["start"], "RECEIPT_INVALID"), _instant(receipt["window"]["end"], "RECEIPT_INVALID")
    c, d = _instant(outlook["horizon"]["start"]), _instant(outlook["horizon"]["end"])
    _require(c <= a and b <= d, "RECEIPT_INVALID")


def build_attribution(receipt, outlook, *, cause, statement, attributed_by, attributed_at,
                      synthetic, assumption_id=None, signal_ref=None, method_ref=None,
                      share=None):
    """Seal and validate one ``Attribution`` against the receipt and outlook it explains.

    ``receipt`` is the stored scoring receipt (the exact bytes the statement is
    about) and ``outlook`` the issued record the receipt scored. The
    attribution's ``outlook_id``, ``outlook_digest`` and ``receipt_digest`` are
    read from the receipt, so an attribution cannot name some other run by
    accident. The cause's reference is passed as its own keyword — a belief's
    ``assumption_id``, a signal's ``signal_ref`` (``source``, ``available_at``,
    ``effective_at``) or a method's ``method_ref`` — and the other two stay
    ``None``; ``share`` is an optional decimal string in [0, 1] and
    ``attributed_at`` is caller-supplied, as every instant here is. Timestamps
    are normalized to UTC ``Z`` form at build time only.
    """
    validate_outlook(outlook)
    validate_receipt(receipt)
    if type(signal_ref) is dict:
        signal_ref = dict(signal_ref)
        for field in ("available_at", "effective_at"):
            if field in signal_ref:
                signal_ref[field] = _utc(signal_ref[field])
    attribution = validate_attribution(_seal({
        "schema_version": SCHEMA_VERSION,
        "kind": ATTRIBUTION_KIND,
        "outlook_id": receipt["outlook_id"],
        "outlook_digest": receipt["outlook_digest"],
        "receipt_digest": receipt["content_digest"],
        "cause": cause,
        "assumption_id": assumption_id,
        "signal_ref": signal_ref,
        "method_ref": method_ref,
        "share": share,
        "statement": statement,
        "attributed_by": attributed_by,
        "attributed_at": _utc(attributed_at),
        "synthetic": synthetic,
    }))
    _check_attribution_against_records(attribution, receipt, outlook)
    return attribution


def validate_attribution(record):
    """Validate one ``Attribution`` envelope, its content digest included.

    The record-only rules live here: the closed key set and kind, the sealed
    digest, the three causes, exactly the cause's own reference (the others
    null), a non-blank statement and author, an optional decimal share in
    [0, 1] written as text, and instants where the schema says instants —
    including ``available_at`` at or before ``attributed_at``. The rules that
    need the receipt and the outlook are in
    :func:`_check_attribution_against_records`.
    """
    _require(type(record) is dict, "ATTRIBUTION_INVALID")
    _require(set(record) == ATTRIBUTION_KEYS, "ATTRIBUTION_INVALID")
    _require(record["schema_version"] == SCHEMA_VERSION and record["kind"] == ATTRIBUTION_KIND,
             "ATTRIBUTION_INVALID")
    _check_stored_digest(record, "ATTRIBUTION_INVALID")
    _require(_identifier(record["outlook_id"]), "ATTRIBUTION_INVALID")
    _require(_digest_text(record["outlook_digest"]), "ATTRIBUTION_INVALID")
    _require(_digest_text(record["receipt_digest"]), "ATTRIBUTION_INVALID")
    cause = record["cause"]
    _require(type(cause) is str and cause in CAUSES, "ATTRIBUTION_INVALID")
    assumption_id, signal_ref, method_ref = (record["assumption_id"], record["signal_ref"],
                                             record["method_ref"])
    if cause == "belief":
        # A belief cause names a register row and nothing else; the other two
        # references are the record's nulls, never a second claim beside it.
        _require(_assumption_id(assumption_id), "ATTRIBUTION_INVALID")
        _require(signal_ref is None and method_ref is None, "ATTRIBUTION_INVALID")
    elif cause == "signal":
        _require(assumption_id is None and method_ref is None, "ATTRIBUTION_INVALID")
        _require(type(signal_ref) is dict and set(signal_ref) == SIGNAL_KEYS,
                 "ATTRIBUTION_INVALID")
        _require(_text(signal_ref["source"]), "ATTRIBUTION_INVALID")
        available = _instant(signal_ref["available_at"], "ATTRIBUTION_INVALID")
        _instant(signal_ref["effective_at"], "ATTRIBUTION_INVALID")
        _require(available <= _instant(record["attributed_at"], "ATTRIBUTION_INVALID"),
                 "ATTRIBUTION_INVALID")
    else:  # method
        _require(assumption_id is None and signal_ref is None, "ATTRIBUTION_INVALID")
        _require(_text(method_ref), "ATTRIBUTION_INVALID")
    share = record["share"]
    if share is not None:
        number = _decimal_text(share, code="ATTRIBUTION_INVALID")
        _require(number >= 0 and number <= 1, "ATTRIBUTION_INVALID")
    _require(_text(record["statement"]), "ATTRIBUTION_INVALID")
    _require(_text(record["attributed_by"]), "ATTRIBUTION_INVALID")
    _instant(record["attributed_at"], "ATTRIBUTION_INVALID")
    _require(type(record["synthetic"]) is bool, "ATTRIBUTION_INVALID")
    return record


def _check_attribution_against_records(attribution, receipt, outlook):
    """The link rules that need all three records: receipt bytes, provenance, dates, reference."""
    validate_outlook(outlook)
    validate_receipt(receipt)
    _check_receipt_against_outlook(receipt, outlook)
    # The attribution names the exact receipt bytes and the receipt's outlook;
    # the builder reads both from the receipt, so only a hand-edited record can
    # reach this refusal.
    _require(attribution["outlook_id"] == receipt["outlook_id"], "ATTRIBUTION_INVALID")
    _require(attribution["outlook_digest"] == receipt["outlook_digest"], "ATTRIBUTION_INVALID")
    _require(attribution["receipt_digest"] == receipt["content_digest"], "ATTRIBUTION_INVALID")
    # Provenance is inherited one way, as for receipts: a real attribution
    # cannot be linked to a synthetic receipt; a synthetic attribution is honest
    # about itself and may sit on either.
    _require(not receipt["synthetic"] or attribution["synthetic"], "ATTRIBUTION_INVALID")
    # A statement is written after the run it explains was scored.
    _require(_instant(attribution["attributed_at"], "ATTRIBUTION_INVALID")
             >= _instant(receipt["scored_at"], "ATTRIBUTION_INVALID"), "ATTRIBUTION_INVALID")
    if attribution["cause"] == "belief":
        # An attribution cannot blame a belief the outlook did not rest on.
        _require(attribution["assumption_id"] in outlook["assumption_ids"], "ATTRIBUTION_INVALID")
    elif attribution["cause"] == "signal":
        signal = attribution["signal_ref"]
        # A late signal is one the outlook could not have read: it became
        # available after the information cutoff. It also cannot become
        # available after the statement that names it, and a signal that takes
        # effect after the scored window ended cannot explain the miss.
        _require(_instant(signal["available_at"], "ATTRIBUTION_INVALID")
                 > _instant(outlook["information_cutoff"], "ATTRIBUTION_INVALID"),
                 "ATTRIBUTION_INVALID")
        _require(_instant(signal["effective_at"], "ATTRIBUTION_INVALID")
                 < _instant(receipt["window"]["end"], "ATTRIBUTION_INVALID"),
                 "ATTRIBUTION_INVALID")
    else:  # method
        # A named rule is not a closed set and is not accepted: the only method
        # an attribution may name is the outlook's own model version.
        _require(attribution["method_ref"] == outlook["model_version"], "ATTRIBUTION_INVALID")
    return attribution


def attribution_key(record):
    """The content-derived storage key of one attribution, as its file stem.

    The key is the SHA-256 of the canonical JSON of the record's own identity:
    the receipt digest, the cause, the cause's reference (a belief's
    ``assumption_id``, a signal's ``source`` and ``available_at``, or a
    ``method_ref``), the author, the statement and the provenance. Every absent
    reference field is present as null, exactly as the stale mark's ``_key_of``
    carries its identity, so two statements that differ in one word are two
    records and a second append of the same identity is refused by ``O_EXCL``.
    """
    signal = record["signal_ref"] if type(record["signal_ref"]) is dict else {}
    key = canonical_dumps({
        "receipt_digest": record["receipt_digest"],
        "cause": record["cause"],
        "assumption_id": record["assumption_id"],
        "signal_source": signal.get("source"),
        "signal_available_at": signal.get("available_at"),
        "method_ref": record["method_ref"],
        "attributed_by": record["attributed_by"],
        "statement": record["statement"],
        "synthetic": record["synthetic"],
    })
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def outlook_reference(record):
    """The two fields that name one issued outlook elsewhere (for the dependency walk)."""
    validate_outlook(record)
    return {"outlook_id": record["outlook_id"], "outlook_digest": record["content_digest"]}


def receipt_stem(record):
    """The exclusive storage key of one validated receipt, as its file stem.

    The key is the ``(outlook_id, final_series_version)`` pair. The identifier
    is already one safe path segment; the version is arbitrary text, so it
    enters the name as the SHA-256 of its UTF-8 bytes, which no text can turn
    into a path separator. Two receipts of one pair therefore name one file
    whatever their content, and the exclusive create decides which is stored.
    """
    version_key = hashlib.sha256(record["final_series_version"].encode("utf-8")).hexdigest()
    return f"{record['outlook_id']}.{version_key}"


def _write_once(path, record, duplicate_code):
    """Write one sealed record with ``O_EXCL``; an existing path is a refusal."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise OutlookError("ARCHIVE_IO") from None
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_text(record))
            handle.write("\n")
    except FileExistsError:
        raise OutlookError(duplicate_code) from None
    except OSError:
        raise OutlookError("ARCHIVE_IO") from None
    return record


def _canonical_text(record):
    try:
        return canonical_dumps(record)
    except CanonicalizationError:
        raise OutlookError("ARCHIVE_IO") from None


def _read_record(path, validator, name_of):
    """Read one stored record; any mismatch with its own bytes is ``ARCHIVE_TAMPERED``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise OutlookError("ARCHIVE_IO") from None
    value, error = parse_json(text)
    if error is not None:
        raise OutlookError("ARCHIVE_TAMPERED")
    try:
        record = validator(value)
    except OutlookError:
        raise OutlookError("ARCHIVE_TAMPERED") from None
    if name_of(record) != path.stem:
        raise OutlookError("ARCHIVE_TAMPERED")
    return record


class OutlookArchive:
    """One directory of issued outlooks, their scoring receipts and attributions.

    The root is a runtime directory (``.local/outlook-archive/`` for real
    records), never the repository tree; nothing here creates a file that Git
    tracks. All writes are once-only: an outlook is issued once per identifier,
    a receipt once per ``(outlook_id, final_series_version)`` pair and an
    attribution once per content key, each under a file name derived from the
    record itself. There is no update, edit, replace, amend or delete method.
    """

    OUTLOOKS = "outlooks"
    RECEIPTS = "receipts"
    ATTRIBUTIONS = "attributions"

    def __init__(self, root):
        self.root = Path(root)

    @property
    def outlooks_dir(self):
        return self.root / self.OUTLOOKS

    @property
    def receipts_dir(self):
        return self.root / self.RECEIPTS

    @property
    def attributions_dir(self):
        return self.root / self.ATTRIBUTIONS

    def issue(self, record):
        """Issue one validated outlook; a second issue for the id is refused.

        A re-issue (a record with ``supersedes``) is checked against the stored
        predecessor first (:func:`check_supersedes`); a predecessor that is not
        stored is ``OUTLOOK_UNKNOWN`` and nothing is written.
        """
        outlook = validate_outlook(record)
        if SUPERSEDES_KEY in outlook:
            check_supersedes(outlook, self.outlook(outlook[SUPERSEDES_KEY]["outlook_id"]))
        path = self.outlooks_dir / f"{outlook['outlook_id']}.json"
        return _write_once(path, outlook, "OUTLOOK_IMMUTABLE")

    def outlook(self, outlook_id):
        """The issued outlook with this id, re-verified against its digest."""
        _require(_identifier(outlook_id), "OUTLOOK_UNKNOWN")
        path = self.outlooks_dir / f"{outlook_id}.json"
        if not path.exists():
            raise OutlookError("OUTLOOK_UNKNOWN")
        return _read_record(path, validate_outlook, lambda record: record["outlook_id"])

    def issue_ids(self):
        """The ids of every issued outlook, sorted."""
        return tuple(sorted(path.stem for path in self.outlooks_dir.glob("*.json")))

    def append_receipt(self, record):
        """Append one validated receipt under its exclusive storage key.

        The path is the ``(outlook_id, final_series_version)`` pair itself, so
        a second receipt for a pair already scored fails the exclusive create:
        the duplicate check and the write are one atomic operation, and two
        concurrent writers for one pair cannot both store.
        """
        receipt = validate_receipt(record)
        outlook = self.outlook(receipt["outlook_id"])
        _check_receipt_against_outlook(receipt, outlook)
        path = self.receipts_dir / f"{receipt_stem(receipt)}.json"
        return _write_once(path, receipt, "RECEIPT_DUPLICATE")

    def receipts(self, outlook_id=None):
        """Every stored receipt, or those of one outlook, ordered by file name."""
        found = []
        for path in sorted(self.receipts_dir.glob("*.json")):
            record = _read_record(path, validate_receipt, receipt_stem)
            if outlook_id is None or record["outlook_id"] == outlook_id:
                found.append(record)
        return tuple(found)

    def _receipt_of(self, record):
        """The stored receipt an attribution cites, by its own digest; ``None`` if absent.

        The receipt is read to check the attribution against it — a read, not a
        duplicate test: an attribution's duplicate rule is the exclusive create
        of its content-derived name and never a scan.
        """
        for receipt in self.receipts(record["outlook_id"]):
            if receipt["content_digest"] == record["receipt_digest"]:
                return receipt
        return None

    def append_attribution(self, record):
        """Append one validated attribution under its content-derived key.

        The path is the SHA-256 of the record's own identity
        (:func:`attribution_key`), so a second statement of the same identity
        fails the exclusive create — ``ATTRIBUTION_DUPLICATE`` — rather than a
        scan: there is no sequence number and no "next" to compute, and two
        concurrent writers race on one path. The stored receipt and outlook are
        re-read and the cross-record rules checked before anything is written.
        """
        attribution = validate_attribution(record)
        outlook = self.outlook(attribution["outlook_id"])
        receipt = self._receipt_of(attribution)
        _require(receipt is not None, "RECEIPT_UNKNOWN")
        _check_attribution_against_records(attribution, receipt, outlook)
        path = self.attributions_dir / (attribution_key(attribution) + ".json")
        return _write_once(path, attribution, "ATTRIBUTION_DUPLICATE")

    def attributions(self, outlook_id=None):
        """Every stored attribution, or those of one outlook, ordered by file name."""
        found = []
        for path in sorted(self.attributions_dir.glob("*.json")):
            record = _read_record(path, validate_attribution, attribution_key)
            if outlook_id is None or record["outlook_id"] == outlook_id:
                found.append(record)
        return tuple(found)

    def verify(self):
        """Re-read the whole archive; report counts and every problem found.

        Returns ``{"outlooks": n, "receipts": n, "attributions": n,
        "problems": [...]}`` with each problem a ``"<file>: <CODE>"`` line. A
        record that fails its own digest or contract, a record stored under a
        file name other than its own key, a receipt whose outlook is missing, a
        receipt that cites different bytes than the stored outlook, an
        attribution whose receipt or outlook is missing or that breaks the
        cross-record rules, and the shares of one receipt summing above one are
        all reported — so an outlook edited after issue is visible even though
        the file itself cannot be locked. A share sum above one is reported as
        ``SHARE_OVER_ONE`` on the receipt's file: it is a problem of the desk's
        arithmetic, not evidence that a record was edited, and the desk shows it
        beside the receipt rather than refusing to read the archive.
        """
        report = {"outlooks": 0, "receipts": 0, "attributions": 0, "problems": []}
        outlooks = {}
        for path in sorted(self.outlooks_dir.glob("*.json")):
            try:
                record = _read_record(path, validate_outlook, lambda value: value["outlook_id"])
            except OutlookError as error:
                report["problems"].append(f"{path.name}: {error.code}")
                continue
            outlooks[record["outlook_id"]] = record
            report["outlooks"] += 1
        # A re-issue names its predecessor's exact bytes; a predecessor missing or
        # replaced after the successor was issued is reported on the successor.
        for outlook_id in sorted(outlooks):
            record = outlooks[outlook_id]
            if SUPERSEDES_KEY not in record:
                continue
            predecessor = outlooks.get(record[SUPERSEDES_KEY]["outlook_id"])
            if predecessor is None:
                report["problems"].append(f"{outlook_id}.json: OUTLOOK_UNKNOWN")
                continue
            try:
                check_supersedes(record, predecessor)
            except OutlookError as error:
                report["problems"].append(f"{outlook_id}.json: {error.code}")
        receipts = {}
        for path in sorted(self.receipts_dir.glob("*.json")):
            try:
                record = _read_record(path, validate_receipt, receipt_stem)
            except OutlookError as error:
                report["problems"].append(f"{path.name}: {error.code}")
                continue
            report["receipts"] += 1
            receipts[record["content_digest"]] = (path.name, record)
            target = outlooks.get(record["outlook_id"])
            if target is None:
                report["problems"].append(f"{path.name}: OUTLOOK_UNKNOWN")
                continue
            try:
                _check_receipt_against_outlook(record, target)
            except OutlookError as error:
                report["problems"].append(f"{path.name}: {error.code}")
        shares = {}
        for path in sorted(self.attributions_dir.glob("*.json")):
            try:
                record = _read_record(path, validate_attribution, attribution_key)
            except OutlookError as error:
                report["problems"].append(f"{path.name}: {error.code}")
                continue
            report["attributions"] += 1
            target = outlooks.get(record["outlook_id"])
            if target is None:
                report["problems"].append(f"{path.name}: OUTLOOK_UNKNOWN")
                continue
            found = receipts.get(record["receipt_digest"])
            if found is None:
                report["problems"].append(f"{path.name}: RECEIPT_UNKNOWN")
                continue
            try:
                _check_attribution_against_records(record, found[1], target)
            except OutlookError as error:
                report["problems"].append(f"{path.name}: {error.code}")
                continue
            if record["share"] is not None:
                shares.setdefault(record["receipt_digest"], []).append(Decimal(record["share"]))
        for digest, values in sorted(shares.items(), key=lambda item: receipts[item[0]][0]):
            if sum(values) > 1:
                report["problems"].append(f"{receipts[digest][0]}: SHARE_OVER_ONE")
        return report
