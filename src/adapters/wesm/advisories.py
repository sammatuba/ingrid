"""Bounded reader for NGCP system-operator advisories in the company WESM copy.

Rows are JSON lines from ``grid_raw.ext_others_mpi_advisories``, exported by
``scripts/data/wesm/export.sh`` (orchestrator seat). This module reads local bytes
only: no network, credential, clock or calendar beyond what a row carries.

The rules are fixed by ``docs/work/real-sources/intent.md`` and the source profile
``docs/work/foundation-review-2026-10-13/sources/01-so-advisories.md``:

* every naive timestamp in the copy is Asia/Manila. The parser attaches ``+08:00``
  to ``interval_start`` and to the in-text header clock and refuses a row whose
  header clock is more than 15 minutes from the posting instant
  (``CLOCK_DISAGREEMENT``), listing it in the export report;
* ``known_at`` is the posting instant, ``published_at`` is the header clock; a
  grammar miss has no header clock, so its ``published_at`` keeps the posting
  instant and is labelled ``published_at_approximate: true`` — the stand-in is an
  approximation, never a stated publication (owner ruling, round 9);
  ``adv_sdate`` and ``adv_tran_type`` are read but not used (owner, 2026-10-13);
* identical body text within 24 hours is one lineage: the earliest ``source_id``
  carries the ``lineage_id``, and a byte-identical repost cites it through
  ``copied_from``. The same body text more than 24 hours later is a new lineage,
  not a repost;
* the passage is the body between the ``<Grid>-MM/DD/YYYY HH:MM: `` header and the
  trailing ``  [WEBSMS]`` tag, held as byte offsets into ``original_text``. One
  passage per advisory; a message that does not match the grammar yields its
  source version with no passage and is counted, never guessed. A header that
  matches the grammar but names no calendar instant is a refused row
  (``MALFORMED_ROW``), listed in the report like any other refusal;
* the event clock ``at HHMMH`` is on the header date unless it is later than the
  header clock, then on the previous day (midnight wrap); a header-to-event gap
  above six hours carries ``event_time_flag: "review"``. The event time is parser
  metadata on the passage, not a validated record field;
* the category is a deterministic keyword map to the bundle v5 event tokens
  (``docs/work/bundle-v5/intent.md``), recorded on the passage for selection only:
  the compiler never reads it and the model is never told it.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from src.review.records import make_record, reference

#: The signed permission record every record produced here cites.
#: ``docs/work/permissions/2026-10-13-wesm-company-copy.md``.
PERMISSION_REF = "perm:wesm-company-copy:2026-10-13"
PUBLISHER = "NGCP via IEMOP MPI message service"
BASIS_REF = "grid_raw.ext_others_mpi_advisories.interval_start"
BASIS_NOTE = "Asia/Manila, measured 2026-10-13"

MANILA = timezone(timedelta(hours=8))
CLOCK_TOLERANCE = timedelta(minutes=15)
LINEAGE_WINDOW = timedelta(hours=24)
EVENT_REVIEW_GAP = timedelta(hours=6)

COLUMNS = ("interval_start", "adv_id", "adv_sdate", "adv_tran_type", "adv_text_message")

#: The bundle v5 event tokens, in the intent's order. The compiler owns the
#: vocabulary; this module only maps free text onto it for passage selection.
EVENT_TOKENS = ("planned_outage", "forced_outage", "return_to_service", "derating",
                "grid_alert", "testing", "commercial_operation", "other")

#: First matching rule wins; every list is read on the lower-cased body. Returns
#: and test/commissioning notices carry a closing "(Planned/Unplanned Outage)"
#: parenthetical, so the test, alert, failure-to-synchronise and return phrases
#: are read before the outage words they mention as context.
CATEGORY_RULES = (
    ("testing", ("test", "commissioning")),
    ("grid_alert", ("alert", "mld", "manual load drop")),
    ("forced_outage", ("failed to synchron",)),
    ("return_to_service", ("online", "re-online", "energized", "restored", "synchronized")),
    ("forced_outage", ("trip", "shutdown", "unplanned", "forced outage")),
    ("planned_outage", ("planned", "maintenance", "scheduled")),
    ("derating", ("derat",)),
    ("commercial_operation", ("commercial operation",)),
)

NAIVE_STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$")
#: The message grammar, matched on the exported UTF-8 bytes so passage offsets are
#: byte offsets. ``.*`` is greedy, so the trailing tag is the message's own suffix.
GRAMMAR = re.compile(
    rb"^(?:\[NSO Advisory\] |\[NSO Update\] )?"
    rb"(?P<grid>Luzon|Visayas|Mindanao) Grid-"
    rb"(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<year>[0-9]{4}) "
    rb"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}): "
    rb"(?P<body>.*)  \[WEBSMS\]$")
EVENT_CLOCK = re.compile(rb"\bat ([0-9]{2})([0-9]{2})H\b")


class WesmSourceError(ValueError):
    """A refused row; the code is stable and the detail names the row."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code)


@dataclass(frozen=True)
class ParsedAdvisory:
    """One advisory: the two payloads plus the parser's own metadata.

    ``source`` is the SourceVersion payload; ``passage`` is the Passage payload,
    or ``None`` when the grammar did not match. ``repost_of`` names the
    ``source_id`` of the lineage head whose record a byte-identical repost cites
    through ``copied_from``; :func:`records` resolves it to a record reference.
    """

    row: dict
    source: dict
    passage: dict | None
    body: bytes | None
    posting: datetime
    header: datetime | None
    event_at: str | None
    event_time_flag: str | None
    category: str
    repost_of: str | None

    @property
    def grammar_miss(self):
        return self.passage is None

    @property
    def body_key(self):
        """The lineage key: the passage body bytes, or ``None`` on a grammar miss."""
        return self.body


@dataclass(frozen=True)
class RejectedRow:
    row: dict
    code: str
    detail: str


@dataclass(frozen=True)
class AdvisoryBatch:
    advisories: tuple
    rejected: tuple

    def counts(self):
        categories = {token: 0 for token in EVENT_TOKENS}
        for item in self.advisories:
            categories[item.category] += 1
        return {
            "rows": len(self.advisories) + len(self.rejected),
            "parsed": len(self.advisories),
            "rejected": len(self.rejected),
            "grammar_miss": sum(1 for item in self.advisories if item.grammar_miss),
            "lineages": len({item.source["lineage_id"] for item in self.advisories}),
            "reposts": sum(1 for item in self.advisories if item.repost_of is not None),
            "categories": categories,
        }

    def report(self):
        """The export report: row counts and the rejected rows, nothing else."""
        return {
            "source": "grid_raw.ext_others_mpi_advisories",
            "permission_ref": PERMISSION_REF,
            "counts": self.counts(),
            "rejected": [
                {"adv_id": item.row.get("adv_id"), "interval_start": item.row.get("interval_start"),
                 "code": item.code, "detail": item.detail}
                for item in self.rejected
            ],
        }


def moment(value):
    """A naive ``YYYY-MM-DD HH:MM:SS`` copy stamp read as Asia/Manila."""
    match = NAIVE_STAMP.fullmatch(value.strip()) if type(value) is str else None
    if match is None:
        raise WesmSourceError("MALFORMED_ROW", "timestamp is not a naive copy stamp: %r" % (value,))
    try:
        return datetime(*(int(part) for part in match.groups()), tzinfo=MANILA)
    except ValueError:
        raise WesmSourceError("MALFORMED_ROW", "timestamp is not a calendar instant: %r" % (value,)) from None


def category_of(body):
    """The bundle v5 token for one passage body; first matching rule wins."""
    text = body.decode("utf-8").lower()
    for token, needles in CATEGORY_RULES:
        if any(needle in text for needle in needles):
            return token
    return "other"


def event_time(body, header):
    """``(event_at, event_time_flag)`` for one body; both ``None`` when unstamped.

    The event clock is on the header date unless it is later than the header
    clock, then on the previous day (midnight wrap). A header-to-event gap above
    six hours is flagged for review; so is a stamped clock that is not a time.
    """
    match = EVENT_CLOCK.search(body)
    if match is None:
        return None, None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None, "review"
    event = header.replace(hour=hour, minute=minute, second=0)
    if event > header:
        event -= timedelta(days=1)
    flag = "review" if header - event > EVENT_REVIEW_GAP else None
    return event.isoformat(), flag


def parse_advisory_row(row, permission_ref=PERMISSION_REF):
    """One exported row to one :class:`ParsedAdvisory`; lineage stays its own."""
    if type(row) is not dict or any(column not in row for column in COLUMNS):
        raise WesmSourceError("MALFORMED_ROW", "row does not carry the export columns")
    if not row["adv_id"] or type(row["adv_id"]) is not str:
        raise WesmSourceError("MALFORMED_ROW", "adv_id is missing")
    if type(row["adv_text_message"]) is not str:
        raise WesmSourceError("MALFORMED_ROW", "adv_text_message is missing")
    posting = moment(row["interval_start"])
    data = row["adv_text_message"].encode("utf-8")
    source_id = "nso-advisory:" + posting.date().isoformat() + ":" + row["adv_id"]
    match = GRAMMAR.match(data)
    header = event_at = flag = None
    category = "other"
    passage = None
    if match is not None:
        try:
            header = datetime(int(match.group("year")), int(match.group("month")), int(match.group("day")),
                              int(match.group("hour")), int(match.group("minute")), tzinfo=MANILA)
        except ValueError:
            # The grammar fixes the shape, so every group is two or four digits and
            # only the calendar can fail here. The row is refused as data, never
            # repaired, and its neighbours still parse.
            raise WesmSourceError(
                "MALFORMED_ROW",
                "%s: header is not a calendar instant: %s" % (
                    source_id, data[match.start("month"):match.end("minute")].decode("utf-8"))) from None
        if abs(header - posting) > CLOCK_TOLERANCE:
            raise WesmSourceError("CLOCK_DISAGREEMENT",
                                  "%s: header %s against posting %s" % (source_id, header.isoformat(), posting.isoformat()))
        start, end = match.start("body"), match.end("body")
        body = match.group("body")
        quote = body.decode("utf-8")
        event_at, flag = event_time(body, header)
        category = category_of(body)
        passage = {
            # :func:`records` adds ``source_ref``: the built SourceVersion's reference.
            "source_id": source_id,
            "source_version": "1",
            "source_byte_digest": hashlib.sha256(data).hexdigest(),
            "start": start,
            "end": end,
            "quote": quote,
            "quote_digest": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            # Parser metadata, read by selection and the case packet only; the
            # validator does not know these keys and the model is never shown them.
            "event_at": event_at,
            "event_time_flag": flag,
            "category": category,
            # The h0.v2 pair: every real record carries it (h0-v2 intent).
            "synthetic": False,
            "permission_ref": permission_ref,
        }
    source = {
        "source_id": source_id,
        "source_version": "1",
        "lineage_id": source_id,
        "publisher": PUBLISHER,
        "access_policy_ref": permission_ref,
        "original_text": row["adv_text_message"],
        "source_byte_digest": hashlib.sha256(data).hexdigest(),
        # ``published_at`` is the message's own header clock when the grammar gives
        # one. A grammar miss has no header, so it keeps the posting instant as a
        # labelled stand-in: an approximation, never a stated publication.
        "published_at": (header or posting).isoformat(),
        "published_at_approximate": header is None,
        "known_at": posting.isoformat(),
        "availability_basis": {"basis_kind": "feed_logged_at", "basis_ref": BASIS_REF, "note": BASIS_NOTE},
        "unknown_reason": None,
        "copied_from": None,
        "synthetic": False,
        "permission_ref": permission_ref,
    }
    return ParsedAdvisory(row=row, source=source, passage=passage,
                          body=match.group("body") if match is not None else None,
                          posting=posting, header=header, event_at=event_at,
                          event_time_flag=flag, category=category, repost_of=None)


def parse_advisories(rows, permission_ref=PERMISSION_REF):
    """Parse an export in row order, group lineages, collect the refused rows.

    Lineage is assigned in posting order so the result never depends on input
    order: within one body text, a posting more than 24 hours after the current
    head opens a new lineage. Only a byte-identical message text is a repost with
    ``copied_from``; a cross-grid copy shares the lineage without one.
    """
    parsed, rejected = [], []
    for row in rows:
        try:
            parsed.append(parse_advisory_row(row, permission_ref))
        except WesmSourceError as exc:
            rejected.append(RejectedRow(row=row if type(row) is dict else {"row": row},
                                        code=exc.code, detail=exc.detail))
    heads = {}
    grouped = []
    for item in sorted(parsed, key=lambda entry: (entry.posting, entry.source["source_id"])):
        key = item.body_key
        head = heads.get(key) if key is not None else None
        if head is None or item.posting - head.posting > LINEAGE_WINDOW:
            if key is not None:
                heads[key] = item
            grouped.append(item)
            continue
        repost = item.source["original_text"] == head.source["original_text"]
        grouped.append(replace(
            item,
            source=dict(item.source, lineage_id=head.source["lineage_id"]),
            repost_of=head.source["source_id"] if repost else None))
    grouped.sort(key=lambda entry: (entry.posting, entry.source["source_id"]))
    return AdvisoryBatch(advisories=tuple(grouped), rejected=tuple(rejected))


def records(batch, tenant_id, case_id, recorded_at, *, permissions=None):
    """Build the h0.v2 records for a batch, in posting order.

    One ``SourceVersion`` per advisory and one ``Passage`` when the grammar
    matched; a repost's ``copied_from`` resolves to the head's record reference,
    so the head is always built first.
    """
    built, sources = [], {}
    for item in batch.advisories:
        payload = item.source
        if item.repost_of is not None:
            head = sources[item.repost_of]
            payload = dict(payload, copied_from=reference(head))
        source = make_record("SourceVersion", tenant_id, case_id, payload["source_id"], "1",
                             recorded_at, payload, permissions=permissions)
        built.append(source)
        sources[payload["source_id"]] = source
        if item.passage is not None:
            span = dict(item.passage, source_ref=reference(source))
            built.append(make_record("Passage", tenant_id, case_id, "passage:" + payload["source_id"], "1",
                                     recorded_at, span, permissions=permissions))
    return built


def main(argv=None):
    """``python3 -m src.adapters.wesm.advisories FILE.jsonl`` prints the report."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: advisories.py FILE.jsonl")
    with open(argv[0], encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    print(json.dumps(parse_advisories(rows).report(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
