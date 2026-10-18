"""The store's records: one shape per table, the derived availability interval, and JSONL.

Six tables — ``entities``, ``source_versions``, ``passages``, ``claims``, ``relations`` and
``rule_versions`` — typed and append-only. Every table carries the ontology profile's five
time fields, spelled the same way everywhere:

| Field | Columns | Meaning here |
|---|---|---|
| event time | ``event_time_start``, ``event_time_end``, ``event_value``, ``event_precision``, ``event_unknown_reason`` | when the described condition applies; for a rule version this is its supplied effective period |
| publication time | ``published_on`` or ``published_at``, ``published_value``, ``published_precision``, ``published_unknown_reason`` | what the issuer states. A date stays a date: a date-precision value fills ``published_on`` and never ``published_at``, so no midnight is fabricated |
| first availability | ``availability_from``, ``availability_until``, ``availability_value``, ``availability_precision``, ``availability_basis``, ``availability_unknown_reason`` | the half-open interval of first availability; the single column a cutoff query compares is ``availability_until`` |
| recorded time | ``recorded_at`` | when this row was written |
| review time | ``reviewed_at``, ``review_state`` | when a decision was taken, and the record's state |

**One cutoff rule, one comparison.** ``known then`` means the whole availability interval has
ended by the end of the cutoff period. Code — never a SQL expression — turns a supplied value
into the interval, because a coarse value denotes its whole period: a date ``2026-10-15``
becomes ``[2026-10-15T00:00:00Z, 2026-10-16T00:00:00Z)``, a month ``2026-10`` becomes
``[2026-10-01, 2026-11-01)``, and an instant ``t`` becomes ``[t, t+1µs)`` — the next
representable instant is the half-open end of a point. A cutoff is turned into the same kind
of interval by :func:`cutoff_interval`, and every query is then the single predicate
``availability_until <= @cutoff_until`` (with ``availability_until IS NOT NULL``, because an
unknown availability is excluded, never backfilled). The three-way exclusion reason the
lineage register uses — ``after_cutoff`` when the interval has not started by the cutoff,
``availability_imprecise`` when it straddles the cutoff's end — is readable from
``availability_from`` beside ``availability_until``; :func:`availability_reason` and
:func:`effectivity_reason` are that classification, and ``local.py`` and the SQL files use it.

**Identity.** ``passage_id`` and ``relation_id`` are derived from the row's own content, so
the same passage or edge always has the same id; ``source_id``, ``source_version``,
``entity_id``, ``claim_id`` + ``claim_revision`` and ``version_id`` are supplied by the
producer, and a repeated key with different content is refused rather than overwritten.

**What is refused.** A relation kind outside the ontology profile's list, and the profile's
two forbidden kinds (``relatedTo``, ``causes``) by name; a claim whose citation does not name
a passage the store holds; a passage whose source version is not held, or is ``excluded``
because its first availability is unknown; a rule version whose provenance is neither resolved
from the source version it names nor stated, because a real document must not be recorded as a
synthetic one; an embedding of a different length from the ones already loaded. Nothing is
inferred: no date is read out of the text, and an unknown time keeps its reason. The store's
own gates are in ``local.py``: a claim and its citation must name one document version, and a
claim is never first available before the evidence it rests on, at both ends of its
availability interval — the end is the column the cutoff compares.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone

from .. import acquire as acq

TABLES = ("entities", "source_versions", "passages", "claims", "relations", "rule_versions")

#: The columns that identify a row. Append-only: a repeated key never overwrites a row, and
#: the same key with different content is refused rather than merged.
KEYS = {
    "entities": ("entity_id",),
    "source_versions": ("source_id", "source_version"),
    "passages": ("passage_id",),
    "claims": ("claim_id", "claim_revision"),
    "relations": ("relation_id",),
    "rule_versions": ("version_id",),
}

#: The relations the ontology profile allows. ``relatedTo`` and ``causes`` are refused by name.
RELATION_KINDS = ("refersTo", "attributedTo", "reports", "derivedFrom", "supports", "challenges",
                  "qualifiedBy", "copiedFrom", "represents", "usesAssumption", "effectiveDuring",
                  "comparedWith", "reviewedBy", "dependsOn")

#: The profile forbids a generic ``relatedTo`` edge and a default ``causes`` edge.
FORBIDDEN_KINDS = {
    "relatedTo": "the ontology profile forbids a generic relatedTo edge; name the relation",
    "causes": "the ontology profile forbids a default causes edge; a mechanism is a Hypothesis",
}

REVIEW_STATES = ("proposed", "accepted", "rejected", "withdrawn", "registered", "not_reviewed")

#: Which states each table may carry. A source version or a passage is a record of bytes,
#: not a reviewed proposition; a rule version is a supplied register record; a claim, a
#: relation and an entity mapping are proposed by a model or an analyst and accepted by one.
TABLE_REVIEW_STATES = {
    "entities": ("proposed", "accepted", "rejected", "withdrawn"),
    "source_versions": ("not_reviewed",),
    "passages": ("not_reviewed",),
    "claims": ("proposed", "accepted", "rejected", "withdrawn"),
    "relations": ("proposed", "accepted", "rejected", "withdrawn"),
    "rule_versions": ("registered",),
}

#: Modalities a claim may carry, from the profile: a report, a target, a proposal, a
#: conditional intention, a forecast or a denial. Never a probability.
MODALITIES = ("actual", "target", "proposal", "conditional_intention", "forecast", "denial")

#: Date precisions a supplied value may carry. ``day`` is the lineage's spelling, ``date``
#: the acquisition record's; both mean the same period and both are kept as stated.
COARSE_PRECISIONS = ("year", "month", "day", "date")
INSTANT_PRECISIONS = ("second", "fraction")
PRECISIONS = COARSE_PRECISIONS + INSTANT_PRECISIONS

_MOMENT = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?$")
_YEAR = re.compile(r"^(\d{4})$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

UTC = timezone.utc
MICROSECOND = timedelta(microseconds=1)

TIME_COLUMNS = ("event_time_start", "event_time_end", "event_value", "event_precision",
                "event_unknown_reason", "published_on", "published_at", "published_value",
                "published_precision", "published_unknown_reason", "availability_from",
                "availability_until", "availability_value", "availability_precision",
                "availability_basis", "availability_unknown_reason", "recorded_at",
                "reviewed_at", "review_state")

_CORPUS_RECORD = acq.RECORD


class RowError(ValueError):
    """A refused row. The code is stable; the detail names the cause."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


# --------------------------------------------------------------------------------------
# Time: supplied values to half-open UTC intervals. No clock is read anywhere in this file.
# --------------------------------------------------------------------------------------

def instant_precision(value):
    """The precision a supplied instant carries: ``fraction`` when it has one, else ``second``."""
    if type(value) is not str or not _MOMENT.fullmatch(value):
        raise RowError("MALFORMED_TIME", "not an offset-bearing instant: %r" % (value,))
    body = value.strip().replace(" ", "T").split("T", 1)[1]
    return "fraction" if "." in body.split("+")[0].split("-")[0] else "second"


def instant_text(moment):
    """One instant as ``YYYY-MM-DDTHH:MM:SS.ffffffZ``, the one spelling every row uses."""
    if isinstance(moment, str):
        moment = parse_instant(moment, "instant")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def parse_instant(value, name):
    """An offset-bearing instant as a UTC ``datetime``; a date without an offset is refused."""
    if type(value) is not str or not _MOMENT.fullmatch(value):
        raise RowError("MALFORMED_TIME", "%s is not an offset-bearing instant: %r" % (name, value))
    text = value.strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise RowError("MALFORMED_TIME", "%s is not a calendar instant: %r" % (name, value)) from None
    if parsed.tzinfo is None:
        raise RowError("MALFORMED_TIME", "%s carries no UTC offset, so its period is unknown: %r"
                       % (name, value))
    return parsed.astimezone(UTC)


def coarse_bounds(value, precision, name):
    """``(start, end)`` civil-date bounds of a supplied year, month or day value.

    The end is exclusive, so ``2026-02`` is ``2026-02-01`` to ``2026-03-01`` and a leap year
    needs no special case. The period is the value's own; nothing is guessed.
    """
    if type(value) is not str:
        raise RowError("MALFORMED_TIME", "%s value must be a string: %r" % (name, value))
    text = value.strip()
    year, month = _YEAR.fullmatch(text), _MONTH.fullmatch(text)
    day = _DAY.fullmatch(text)
    if precision == "year":
        if not year:
            raise RowError("MALFORMED_TIME", "%s year-precision value is not YYYY: %r" % (name, value))
        return date(int(year.group(1)), 1, 1), date(int(year.group(1)) + 1, 1, 1)
    if precision == "month":
        if not month:
            raise RowError("MALFORMED_TIME", "%s month-precision value is not YYYY-MM: %r" % (name, value))
        first = date(int(month.group(1)), int(month.group(2)), 1)
        return first, (date(first.year + 1, 1, 1) if first.month == 12
                       else date(first.year, first.month + 1, 1))
    if precision in ("day", "date"):
        if not day:
            raise RowError("MALFORMED_TIME", "%s day-precision value is not YYYY-MM-DD: %r"
                           % (name, value))
        try:
            first = date(int(day.group(1)), int(day.group(2)), int(day.group(3)))
        except ValueError:
            raise RowError("MALFORMED_TIME", "%s is not a calendar date: %r" % (name, value)) from None
        return first, first + timedelta(days=1)
    raise RowError("MALFORMED_TIME", "%s precision %r is not one of %s"
                   % (name, precision, PRECISIONS))


def interval(value, precision, name="time"):
    """The half-open UTC interval of one supplied value, as ``(from, until)`` text.

    A coarse value denotes its whole period; an instant denotes the point it is, whose
    half-open end is the next representable instant (one microsecond on).
    """
    if precision in COARSE_PRECISIONS:
        start, end = coarse_bounds(value, precision, name)
        return (start.strftime("%Y-%m-%dT00:00:00.000000Z"),
                end.strftime("%Y-%m-%dT00:00:00.000000Z"))
    if precision in INSTANT_PRECISIONS:
        moment = parse_instant(value, name)
        return instant_text(moment), instant_text(moment + MICROSECOND)
    raise RowError("MALFORMED_TIME", "%s precision %r is not one of %s"
                   % (name, precision, PRECISIONS))


def cutoff_interval(value, precision):
    """A cutoff as the same half-open interval every query compares against.

    A date cutoff ``2026-10-15`` runs to ``2026-10-16T00:00:00Z``: the cutoff names the whole
    day, and what was known then is what was known by the end of it. An instant cutoff ``t``
    ends one microsecond on, so a record first available exactly at ``t`` is inside it.
    """
    return interval(value, precision, "cutoff")


def availability_reason(row, cutoff_until):
    """Why a row's first availability does not place it at a cutoff, or ``None``.

    The reasons are the lineage register's own: an unknown availability is excluded with its
    reason; an interval that has not started by the cutoff is ``after_cutoff``; one that
    straddles the cutoff's end is ``availability_imprecise``, never assumed into force.
    """
    until, start = row.get("availability_until"), row.get("availability_from")
    if until is None:
        return "availability_unknown"
    if start is not None and start >= cutoff_until:
        return "after_cutoff"
    if until > cutoff_until:
        return "availability_imprecise"
    return None


def effectivity_reason(row, cutoff_until):
    """Why a row's supplied effective period does not place it at a cutoff, or ``None``."""
    start, end = row.get("event_time_start"), row.get("event_time_end")
    if end is None:
        return "effectivity_unknown"
    if start is not None and start >= cutoff_until:
        return "not_yet_effective"
    if end > cutoff_until:
        return "effectivity_imprecise"
    return None


def placed(row, cutoff_until):
    """Whether a rule version is in force at a cutoff on both supplied dates."""
    return availability_reason(row, cutoff_until) is None and effectivity_reason(row, cutoff_until) is None


def known_by(row, cutoff_until):
    """Whether a row's first availability places it at a cutoff (the passages/claims rule)."""
    return row.get("availability_until") is not None and row["availability_until"] <= cutoff_until


# --------------------------------------------------------------------------------------
# Row construction
# --------------------------------------------------------------------------------------

def _text(value, name, code="INVALID_ROW", allow_none=False):
    """A non-blank string; ``allow_none`` also reads an absent or blank value as absent.

    A blank optional value is the same as an omitted one: the store records what a record
    states, and "stated as empty" is not a fact about a document.
    """
    if value is None or (type(value) is str and not value.strip()):
        if allow_none:
            return None
        raise RowError(code, "%s must be a non-blank string" % name)
    if type(value) is not str:
        raise RowError(code, "%s must be a non-blank string" % name)
    return value.strip() if name not in ("quote", "text") else value


def _integer(value, name, minimum=None):
    if type(value) is not int or isinstance(value, bool):
        raise RowError("INVALID_ROW", "%s must be an integer" % name)
    if minimum is not None and value < minimum:
        raise RowError("INVALID_ROW", "%s must be at least %s" % (name, minimum))
    return value


def _flag(value, name):
    if type(value) is not bool:
        raise RowError("INVALID_ROW", "%s must be a boolean" % name)
    return value


def _review(row, table):
    state = row.get("review_state")
    if state not in TABLE_REVIEW_STATES[table]:
        raise RowError("INVALID_REVIEW_STATE",
                       "%s review_state %r is not one of %s"
                       % (table, state, TABLE_REVIEW_STATES[table]))
    return state


def _provenance(row):
    synthetic = _flag(row.get("synthetic"), "synthetic")
    permission = row.get("permission_ref")
    if synthetic:
        if permission not in (None, ""):
            raise RowError("INVALID_ROW", "a synthetic row carries no permission_ref")
        permission = None
    else:
        _text(permission, "permission_ref")
    return synthetic, permission


def _refuse_reason_beside_value(row, reason_name):
    """A stated value and a reason it is unknown are two different records; a row is one.

    A reason beside a stated value is neither dropped nor guessed at: the row is refused, so a
    record can never carry both a date and the statement that no date is known. A blank reason
    is an absent one, as everywhere else.
    """
    reason = row.get(reason_name)
    if reason is None or (type(reason) is str and not reason.strip()):
        return
    raise RowError("INVALID_ROW",
                   "%s is stated beside a stated value; a row states the value or the "
                   "reason it is unknown, never both" % reason_name)


def _event_block(row, out, unknown_reason, name="event"):
    """Fill the event columns from a supplied value, or record the reason it is absent.

    The stated value and its precision are kept beside the derived interval, so a normalized
    row normalizes to itself and the statement a record makes is never replaced by the
    arithmetic run on it.
    """
    value, precision = row.get("event_value"), row.get("event_precision")
    end_value, end_precision = row.get("event_end_value"), row.get("event_end_precision")
    if value is None or precision is None:
        if value is None and precision is None and end_value is None and end_precision is None:
            out["event_value"] = out["event_precision"] = None
            out["event_end_value"] = out["event_end_precision"] = None
            out["event_time_start"] = out["event_time_end"] = None
            out["event_unknown_reason"] = unknown_reason
            return
        raise RowError("MALFORMED_TIME", "%s_value and %s_precision must be supplied together"
                       % (name, name))
    _refuse_reason_beside_value(row, "event_unknown_reason")
    start, end = interval(value, precision, name)
    if end_value is not None or end_precision is not None:
        if end_value is None or end_precision is None:
            raise RowError("MALFORMED_TIME",
                           "%s_end_value and %s_end_precision must be supplied together"
                           % (name, name))
        # The stated end day is inclusive, so its half-open end is the day after it.
        _, stated_end = interval(end_value, end_precision, name + "_end")
        if stated_end <= start:
            raise RowError("MALFORMED_TIME",
                           "the stated %s end is not after its start" % name)
        end = stated_end
    out["event_value"], out["event_precision"] = value, precision
    out["event_end_value"], out["event_end_precision"] = end_value, end_precision
    out["event_time_start"], out["event_time_end"] = start, end
    out["event_unknown_reason"] = None


def _publication_block(row, out, unknown_reason):
    """Fill the publication columns; a date-precision value never becomes an instant."""
    value, precision = row.get("published_value"), row.get("published_precision")
    out["published_on"] = out["published_at"] = None
    if value is None or precision is None:
        if value is None and precision is None:
            out["published_value"] = out["published_precision"] = None
            out["published_unknown_reason"] = unknown_reason
            return
        raise RowError("MALFORMED_TIME", "published_value and published_precision must be supplied together")
    _refuse_reason_beside_value(row, "published_unknown_reason")
    out["published_value"], out["published_precision"] = value, precision
    out["published_unknown_reason"] = None
    start, _ = interval(value, precision, "publication")
    if precision in COARSE_PRECISIONS:
        # The first day of the stated period; ``published_value`` and ``published_precision``
        # say how coarse the statement is, and an instant never lands here.
        out["published_on"] = start[:10]
    else:
        out["published_at"] = start


def _availability_block(row, out, default_reason):
    """Fill the availability interval from a supplied value, or the recorded unknown."""
    value, precision = row.get("availability_value"), row.get("availability_precision")
    out["availability_basis"] = row.get("availability_basis")
    if value is None or precision is None:
        if value is None and precision is None:
            out["availability_value"] = out["availability_precision"] = None
            out["availability_from"] = out["availability_until"] = None
            out["availability_unknown_reason"] = _text(
                row.get("availability_unknown_reason") or default_reason,
                "availability_unknown_reason")
            return
        raise RowError("MALFORMED_TIME",
                       "availability_value and availability_precision must be supplied together")
    _refuse_reason_beside_value(row, "availability_unknown_reason")
    start, end = interval(value, precision, "availability")
    out["availability_value"], out["availability_precision"] = value, precision
    out["availability_from"], out["availability_until"] = start, end
    out["availability_unknown_reason"] = None


def _base(row, table, unknown_event, unknown_publication, unknown_availability):
    out = {"recorded_at": instant_text(_text(row.get("recorded_at"), "recorded_at"))}
    out["review_state"] = _review(row, table)
    reviewed = row.get("reviewed_at")
    out["reviewed_at"] = None if reviewed is None else instant_text(reviewed)
    _event_block(row, out, unknown_event)
    _publication_block(row, out, unknown_publication)
    _availability_block(row, out, unknown_availability)
    synthetic, permission = _provenance(row)
    out["synthetic"], out["permission_ref"] = synthetic, permission
    return out


def _digest(*parts):
    return hashlib.sha256("\x1f".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def passage_id(source_id, source_version, start, end):
    """One passage's id from the version and the exact span it names."""
    return "p-" + _digest(source_id, source_version, start, end)[:16]


def relation_id(kind, from_ref, to_ref):
    """One edge's id from its kind and its two ends; the same edge keeps its id."""
    return "r-" + _digest(kind, from_ref, to_ref)[:16]


def entity_row(row):
    """One typed entity or mapping record, validated and time-normalized."""
    out = {"entity_id": _text(row.get("entity_id"), "entity_id"),
           "entity_type": _text(row.get("entity_type"), "entity_type"),
           "label": _text(row.get("label"), "label"),
           "canonical_ref": _text(row.get("canonical_ref"), "canonical_ref", allow_none=True),
           "issuer": _text(row.get("issuer"), "issuer", allow_none=True),
           "evidence_passage_id": _text(row.get("evidence_passage_id"), "evidence_passage_id",
                                        allow_none=True),
           "notes": _text(row.get("notes"), "notes", allow_none=True) or ""}
    out.update(_base(row, "entities",
                     "an entity record states no event time of its own; a claim carries the "
                     "condition it describes",
                     "the record states no publication time",
                     "the record states no first-availability evidence"))
    return out


def source_version_row(record):
    """One row from an acquisition :class:`~src.adapters.corpus.acquire.SourceVersion`."""
    if not isinstance(record, acq.SourceVersion):
        raise RowError("INVALID_ROW", "expected a SourceVersion record")
    payload = record.payload()
    return normalize("source_versions", {
        "source_id": payload["source_id"], "source_version": payload["source_version"],
        "lineage_id": payload["lineage_id"], "issuer": payload["issuer"],
        "locator": payload["locator"], "content_type": payload["content_type"],
        "content_type_source": payload["content_type_source"],
        "document_length": payload["document_length"],
        "document_sha256": payload["document_sha256"], "licence_ref": payload["licence_ref"],
        "access_policy_ref": payload["access_policy_ref"], "state": payload["state"],
        "corpus_record": payload["record"],
        "published_value": payload["publication"]["value"],
        "published_precision": payload["publication"]["precision"],
        "published_unknown_reason": payload["publication"]["unknown_reason"],
        "availability_value": payload["known_at"],
        "availability_precision": (None if payload["known_at"] is None else
                                   instant_precision(payload["known_at"])),
        "availability_basis": payload["availability_basis"],
        "availability_unknown_reason": payload["unknown_reason"],
        "recorded_at": payload["recorded_at"], "review_state": "not_reviewed",
        "synthetic": payload["synthetic"], "permission_ref": payload["permission_ref"]})


def passage_row(payload, source_row):
    """One row from a review-core ``Passage`` payload, with its source version's times.

    The issuer and the availability interval are derived from the source version the passage
    belongs to and are carried on the row so the cutoff and issuer filters read one table; the
    ``source_versions`` row stays the authority for both.

    Either spelling of the span is read: the review core's payload, which names it ``start``
    and ``end``, or a stored row, which names it ``start_offset`` and ``end_offset`` because
    ``END`` is a SQL keyword.
    """
    if type(payload) is dict and payload.get("record_kind") == "Passage":
        payload = payload["payload"]
    if type(payload) is not dict:
        raise RowError("INVALID_ROW", "expected a Passage payload object")
    payload = dict(payload)
    if payload.get("start") is None:
        payload["start"] = payload.get("start_offset")
    if payload.get("end") is None:
        payload["end"] = payload.get("end_offset")
    for key in ("source_id", "source_version", "start", "end", "quote", "quote_digest"):
        if payload.get(key) is None:
            raise RowError("INVALID_ROW", "a passage payload must carry %s" % key)
    if source_row is None:
        raise RowError("UNKNOWN_SOURCE", "no source version row for %s %s"
                       % (payload["source_id"], payload["source_version"]))
    if (source_row["source_id"], source_row["source_version"]) != (payload["source_id"],
                                                                  payload["source_version"]):
        raise RowError("SOURCE_MISMATCH", "the passage names another source version than the row")
    if source_row["state"] != "compilable":
        raise RowError("SOURCE_EXCLUDED",
                       "%s %s is excluded from every cutoff: %s"
                       % (source_row["source_id"], source_row["source_version"],
                          source_row["availability_unknown_reason"]))
    return {
        "passage_id": passage_id(payload["source_id"], payload["source_version"],
                                 payload["start"], payload["end"]),
        "source_id": payload["source_id"], "source_version": payload["source_version"],
        "issuer": source_row["issuer"], "page": payload.get("page"),
        "page_start": payload.get("page_start"), "page_end": payload.get("page_end"),
        # The review core's Passage payload names the span ``start``/``end``; the table
        # spells them ``start_offset``/``end_offset`` because ``END`` is a SQL keyword.
        "start_offset": payload["start"], "end_offset": payload["end"],
        "quote": payload["quote"], "quote_digest": payload["quote_digest"],
        # An incoming row may already carry its embedding; the loader attaches supplied vectors
        # to the rows that have none. A payload has neither key and gets both as NULL.
        "embedding": payload.get("embedding"), "embedding_model": payload.get("embedding_model"),
        "availability_value": source_row["availability_value"],
        "availability_precision": source_row["availability_precision"],
        "availability_basis": source_row["availability_basis"],
        "availability_unknown_reason": None,
        "availability_from": source_row["availability_from"],
        "availability_until": source_row["availability_until"],
        "published_value": source_row["published_value"],
        "published_precision": source_row["published_precision"],
        "published_on": source_row["published_on"], "published_at": source_row["published_at"],
        "published_unknown_reason": source_row["published_unknown_reason"],
        "event_time_start": None, "event_time_end": None, "event_value": None,
        "event_precision": None,
        "event_unknown_reason": ("a passage has no event time; the claim that cites it "
                                 "carries the condition it describes"),
        "recorded_at": source_row["recorded_at"], "reviewed_at": None,
        "review_state": "not_reviewed", "synthetic": source_row["synthetic"],
        "permission_ref": source_row["permission_ref"]}


def claim_row(row):
    """One proposed or accepted claim, validated and time-normalized."""
    predicate = row.get("predicate")
    if predicate in FORBIDDEN_KINDS:
        raise RowError("FORBIDDEN_RELATION", FORBIDDEN_KINDS[predicate])
    if predicate not in RELATION_KINDS:
        raise RowError("UNKNOWN_RELATION", "predicate %r is not one of %s"
                       % (predicate, RELATION_KINDS))
    modality = row.get("modality")
    if modality not in MODALITIES:
        raise RowError("UNKNOWN_MODALITY", "modality %r is not one of %s" % (modality, MODALITIES))
    out = {"claim_id": _text(row.get("claim_id"), "claim_id"),
           "claim_revision": _integer(row.get("claim_revision"), "claim_revision", 1),
           "subject_ref": _text(row.get("subject_ref"), "subject_ref"),
           "subject_type": _text(row.get("subject_type"), "subject_type"),
           "predicate": predicate,
           "object_ref": _text(row.get("object_ref"), "object_ref", allow_none=True),
           "object_type": _text(row.get("object_type"), "object_type", allow_none=True),
           "object_value": _text(row.get("object_value"), "object_value", allow_none=True),
           "object_unit": _text(row.get("object_unit"), "object_unit", allow_none=True),
           "object_quantity_kind": _text(row.get("object_quantity_kind"),
                                         "object_quantity_kind", allow_none=True),
           "modality": modality,
           "attributed_to": _text(row.get("attributed_to"), "attributed_to"),
           "source_id": _text(row.get("source_id"), "source_id"),
           "source_version": _text(row.get("source_version"), "source_version"),
           "passage_id": _text(row.get("passage_id"), "passage_id", allow_none=True),
           "locator_start": row.get("locator_start"), "locator_end": row.get("locator_end"),
           "quote_digest": row.get("quote_digest"),
           "extraction_method": _text(row.get("extraction_method"), "extraction_method",
                                      allow_none=True),
           "extraction_version": _text(row.get("extraction_version"), "extraction_version",
                                       allow_none=True)}
    if out["object_ref"] is None and out["object_value"] is None:
        raise RowError("INVALID_ROW", "a claim carries an object reference or a typed value")
    for key in ("locator_start", "locator_end"):
        if out[key] is not None:
            out[key] = _integer(out[key], key, 0)
    if out["quote_digest"] is not None and not _HEX64.fullmatch(str(out["quote_digest"])):
        raise RowError("INVALID_ROW", "quote_digest must be a SHA-256 hex digest")
    out.update(_base(row, "claims",
                     "the claim states no valid time of its own",
                     "the claim states no publication time",
                     "the claim states no first-availability evidence"))
    return out


def relation_row(row):
    """One typed edge between two references, validated and time-normalized."""
    kind = row.get("relation_kind")
    if kind in FORBIDDEN_KINDS:
        raise RowError("FORBIDDEN_RELATION", FORBIDDEN_KINDS[kind])
    if kind not in RELATION_KINDS:
        raise RowError("UNKNOWN_RELATION", "relation_kind %r is not one of %s"
                       % (kind, RELATION_KINDS))
    from_ref, to_ref = _text(row.get("from_ref"), "from_ref"), _text(row.get("to_ref"), "to_ref")
    out = {"relation_id": _text(row.get("relation_id"), "relation_id", allow_none=True)
           or relation_id(kind, from_ref, to_ref),
           "relation_kind": kind, "from_ref": from_ref,
           "from_type": _text(row.get("from_type"), "from_type"),
           "to_ref": to_ref, "to_type": _text(row.get("to_type"), "to_type"),
           "claim_ref": _text(row.get("claim_ref"), "claim_ref", allow_none=True),
           "passage_id": _text(row.get("passage_id"), "passage_id", allow_none=True),
           "source_id": _text(row.get("source_id"), "source_id", allow_none=True),
           "source_version": _text(row.get("source_version"), "source_version", allow_none=True),
           "notes": _text(row.get("notes"), "notes", allow_none=True) or ""}
    if out["from_ref"] == out["to_ref"]:
        raise RowError("INVALID_ROW", "a relation cannot join a reference to itself")
    out.update(_base(row, "relations",
                     "the relation states no effective period",
                     "the relation states no publication time",
                     "the relation states no first-availability evidence"))
    return out


def rule_version_row(version, family, recorded_at, *, synthetic=None, permission_ref=None,
                     source_row=None):
    """One row from a lineage :class:`~src.regulatory.lineage.RuleVersion`.

    ``recorded_at`` is the write's own time and is required: a ``RuleVersion`` carries no
    recorded time, and this module reads no clock. Both supplied dates travel whole — the
    stated value and its precision, and the half-open interval code derives from them.
    Nothing is read out of the clause text.

    **Provenance is resolved or stated, never assumed.** A rule version read out of a
    synthetic fixture and one read out of a real document are different records, and this
    function may not label either as the other. Pass the resolved ``source_versions`` row the
    version's locator names as ``source_row`` and the pair is taken from it; or state
    ``synthetic`` directly, with ``permission_ref`` when it is not synthetic. A stated flag
    that disagrees with the resolved row is refused rather than honoured, and a call that
    states neither is refused too — a default here would be the fabrication the pair exists
    to prevent.
    """
    locator = getattr(version, "locator", None)
    if locator is None:
        raise RowError("INVALID_ROW", "expected a RuleVersion with a locator")
    if source_row is not None:
        resolved = source_row.get("synthetic")
        if type(resolved) is not bool:
            raise RowError("PROVENANCE_REQUIRED",
                           "the row supplied as the source version of the rule version of %s "
                           "states no synthetic flag, so it is not a resolved source version"
                           % version.version_id)
        if synthetic is not None and synthetic != resolved:
            raise RowError("SOURCE_MISMATCH",
                           "the rule version of %s is stated synthetic=%r where the source "
                           "version it names records synthetic=%r"
                           % (version.version_id, synthetic, resolved))
        resolved_permission = source_row.get("permission_ref")
        if permission_ref is not None and permission_ref != resolved_permission:
            raise RowError("SOURCE_MISMATCH",
                           "the rule version of %s is stated under permission_ref %r where the "
                           "source version it names records %r; a stated permission is the "
                           "resolved one or it disagrees"
                           % (version.version_id, permission_ref, resolved_permission))
        synthetic, permission_ref = resolved, resolved_permission
    if synthetic is None:
        raise RowError("PROVENANCE_REQUIRED",
                       "the provenance of the rule version of %s is the resolved source "
                       "version's, or it is stated: pass source_row, or synthetic= with "
                       "permission_ref when it is not synthetic; it is never assumed"
                       % version.version_id)
    return normalize("rule_versions", {
        "version_id": version.version_id, "clause_label": version.clause_label,
        "family": family, "text": version.text,
        "source_id": locator.source_id, "source_revision": locator.source_revision,
        "source_digest": locator.digest, "locator_start": locator.start,
        "locator_end": locator.end, "replaces": version.replaces,
        "amendment_ref": version.amendment_ref,
        "event_value": version.effective.value, "event_precision": version.effective.precision,
        "event_unknown_reason": version.effective.unknown_reason,
        "availability_value": version.first_availability.value,
        "availability_precision": version.first_availability.precision,
        "availability_unknown_reason": version.first_availability.unknown_reason,
        "recorded_at": recorded_at,
        "review_state": "registered",
        "synthetic": synthetic, "permission_ref": permission_ref})


def normalize(table, row):
    """The complete row for a table: the table's own builder plus the shared time block."""
    if table not in TABLES:
        raise RowError("UNKNOWN_TABLE", "no table named %r; expected one of %s" % (table, TABLES))
    if type(row) is not dict:
        raise RowError("INVALID_ROW", "a row is a JSON object")
    builder = _BUILDERS[table]
    out = builder(row)
    missing = [name for name in REQUIRED[table] if out.get(name) in (None, "")]
    if missing:
        raise RowError("INVALID_ROW", "%s row is missing %s" % (table, ", ".join(missing)))
    return out


def _entities(row):
    return entity_row(row)


def _source_versions(row):
    out = {"source_id": _text(row.get("source_id"), "source_id"),
           "source_version": _text(row.get("source_version"), "source_version"),
           "lineage_id": _text(row.get("lineage_id"), "lineage_id"),
           "issuer": _text(row.get("issuer"), "issuer"),
           "locator": _text(row.get("locator"), "locator"),
           "content_type": _text(row.get("content_type"), "content_type"),
           "content_type_source": _text(row.get("content_type_source"), "content_type_source"),
           "document_length": _integer(row.get("document_length"), "document_length", 1),
           "document_sha256": _text(row.get("document_sha256"), "document_sha256"),
           "licence_ref": _text(row.get("licence_ref"), "licence_ref"),
           "access_policy_ref": _text(row.get("access_policy_ref"), "access_policy_ref"),
           "state": _text(row.get("state"), "state"),
           "corpus_record": row.get("corpus_record", _CORPUS_RECORD)}
    if not _HEX64.fullmatch(out["document_sha256"]):
        raise RowError("INVALID_ROW", "document_sha256 must be a SHA-256 hex digest")
    if out["state"] not in ("compilable", "excluded"):
        raise RowError("INVALID_ROW", "state must be compilable or excluded")
    out.update(_base(row, "source_versions",
                     "a document version has no single event time; a claim carries it",
                     "the register states no publication for this version",
                     "availability_unknown: no first-availability evidence was supplied"))
    if out["state"] == "compilable" and out["availability_until"] is None:
        raise RowError("INVALID_ROW", "a compilable version needs a first availability")
    if out["state"] == "excluded" and out["availability_until"] is not None:
        raise RowError("INVALID_ROW", "an excluded version carries no first availability")
    return out


def _passages(row):
    out = {"passage_id": _text(row.get("passage_id"), "passage_id"),
           "source_id": _text(row.get("source_id"), "source_id"),
           "source_version": _text(row.get("source_version"), "source_version"),
           "issuer": _text(row.get("issuer"), "issuer"),
           "page": _integer(row["page"], "page", 1) if row.get("page") is not None else None,
           "page_start": row.get("page_start"), "page_end": row.get("page_end"),
           "start_offset": _integer(row.get("start_offset"), "start_offset", 0),
           "end_offset": _integer(row.get("end_offset"), "end_offset", 0),
           "quote": _text(row.get("quote"), "quote"),
           "quote_digest": _text(row.get("quote_digest"), "quote_digest"),
           "embedding": row.get("embedding"), "embedding_model": row.get("embedding_model")}
    if out["end_offset"] <= out["start_offset"]:
        raise RowError("INVALID_ROW", "a passage's end offset must be after its start")
    if not _HEX64.fullmatch(out["quote_digest"]):
        raise RowError("INVALID_ROW", "quote_digest must be a SHA-256 hex digest")
    _embedding(out["embedding"])
    out.update(_base(row, "passages",
                     "a passage has no event time; the claim that cites it carries it",
                     "a passage's publication is its source version's",
                     "availability_unknown: the source version carries no first availability"))
    return out


def _embedding(value):
    """A vector, or ``None``; every component is a finite float and the list is not empty."""
    if value is None:
        return None
    if type(value) is not list or not value:
        raise RowError("INVALID_EMBEDDING", "an embedding is a non-empty JSON array of numbers")
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise RowError("INVALID_EMBEDDING", "an embedding component is a number")
        if component != component or component in (float("inf"), float("-inf")):
            raise RowError("INVALID_EMBEDDING", "an embedding component is finite")
    return [float(component) for component in value]


def _claims(row):
    return claim_row(row)


def _relations(row):
    return relation_row(row)


def _rule_versions(row):
    locator_start, locator_end = row.get("locator_start"), row.get("locator_end")
    out = {"version_id": _text(row.get("version_id"), "version_id"),
           "clause_label": _text(row.get("clause_label"), "clause_label"),
           "family": _text(row.get("family"), "family"),
           "text": _text(row.get("text"), "text"),
           "source_id": _text(row.get("source_id"), "source_id"),
           "source_revision": _text(row.get("source_revision"), "source_revision"),
           "source_digest": _text(row.get("source_digest"), "source_digest"),
           "locator_start": _integer(locator_start, "locator_start", 0),
           "locator_end": _integer(locator_end, "locator_end", 0),
           "replaces": _text(row.get("replaces"), "replaces", allow_none=True),
           "amendment_ref": _text(row.get("amendment_ref"), "amendment_ref", allow_none=True)}
    if out["locator_end"] <= out["locator_start"]:
        raise RowError("INVALID_ROW", "a rule version's locator end must be after its start")
    if out["replaces"] == out["version_id"]:
        raise RowError("INVALID_ROW", "a version cannot replace itself")
    out.update(_base(row, "rule_versions",
                     "the register states no effective period for this version",
                     "the register states no publication for this version",
                     "the register states no first availability for this version"))
    return out


_BUILDERS = {"entities": _entities, "source_versions": _source_versions, "passages": _passages,
             "claims": _claims, "relations": _relations, "rule_versions": _rule_versions}

REQUIRED = {
    "entities": ("entity_id", "entity_type", "label", "review_state", "recorded_at"),
    "source_versions": ("source_id", "source_version", "issuer", "document_sha256", "state",
                        "recorded_at"),
    "passages": ("passage_id", "source_id", "source_version", "issuer", "quote", "quote_digest",
                 "recorded_at"),
    "claims": ("claim_id", "claim_revision", "subject_ref", "subject_type", "predicate",
               "modality", "attributed_to", "source_id", "source_version", "recorded_at"),
    "relations": ("relation_id", "relation_kind", "from_ref", "from_type", "to_ref", "to_type",
                  "recorded_at"),
    "rule_versions": ("version_id", "clause_label", "family", "text", "source_id",
                      "source_revision", "source_digest", "recorded_at"),
}


# --------------------------------------------------------------------------------------
# JSONL
# --------------------------------------------------------------------------------------

def to_jsonl(rows):
    """Rows as newline-delimited JSON: one compact sorted object per line, keys stable."""
    return "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)


def from_jsonl(text):
    """Rows from newline-delimited JSON; a blank line is skipped, a malformed one refused."""
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise RowError("MALFORMED_JSONL", "line %d is not JSON: %s" % (number, exc)) from None
        if type(row) is not dict:
            raise RowError("MALFORMED_JSONL", "line %d is not a JSON object" % number)
        rows.append(row)
    return rows
