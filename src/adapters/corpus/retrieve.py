"""The retrieval receipt: what one ranking read, what it withheld and why, in one record.

A receipt (record ``corpus-retrieval.v1``, the contract in
`docs/work/retrieval-2026-10-18/intent.md`) is built from two things the caller supplies and
nothing else:

* the **pool**: every passage the question could have reached — the store's passage rows, and
  the stubs of passages whose source version is excluded (a store refuses those rows, so they
  arrive separately, carrying ``availability_until: null`` and their reason);
* the **ranked** rows one backend returned for the question, in its order, with its distances.

The receipt counts, it does not rank. Each pool row inside the issuer filter is either a
*candidate* (known by the cutoff and embedded: the set the backend ranks over) or *withheld*
under exactly one reason, checked in this order:

| Reason | When |
|---|---|
| ``availability_unknown`` | the row carries no first availability (``availability_until`` is null) |
| ``later_availability`` | its availability interval has not ended by the cutoff's end — after the cutoff, or straddling it (``records.availability_reason`` names which; both are "not known then") |
| ``no_embedding`` | known then, but no vector was supplied for it |

The rule is the store's own: :func:`records.known_by` compares ``availability_until`` with the
cutoff's exclusive end from :func:`records.cutoff_interval`, and nothing here re-derives it.
A backend that ranks a withheld row, a row outside the pool, a row twice, or rows out of
``(distance, passage_id)`` order is refused with :class:`ReceiptError`: a receipt never records
a ranking the cutoff rule forbids. A backend that returns fewer rows than ``min(top_k,
candidates)`` is refused too, because the count of candidates is then not the set it ranked.

Distances are kept as the backend computed them, unrounded; :func:`present_distance` is the
six-place presentation rule and is never applied inside the receipt.

:func:`passage_ids` turns a receipt into the ``passage_ids`` list ``compile_task`` takes, capped
so the compiled context stays within the compiler's 32 passages (and, if asked, within a budget
of distinct source versions, because each source adds dependency nodes to the compiler's other
32-item budget). :func:`agree` compares the receipts two backends wrote for one question.
"""
from __future__ import annotations

import hashlib
import math
import re

from src.contracts.jsonutil import compute_content_digest

from .store import records

RECORD = "corpus-retrieval.v1"

#: The compiler's passage budget (``POLICY["max_passages"]`` in ``src/review/repository.py``):
#: past it a compiled task is marked truncated and blocked.
COMPILER_MAX_PASSAGES = 32

#: The withheld reasons, in the order a pool row is tested against them.
WITHHELD_REASONS = ("availability_unknown", "later_availability", "no_embedding")

#: The modes a receipt records: ``strict`` is the case's own cutoff (known then), ``hindsight`` a
#: later one (everything now known). The cutoff rule is the same for both; the mode is a label.
MODES = ("strict", "hindsight")

#: The keys of a ranked entry, in the contract's order.
RANKED_KEYS = ("rank", "passage_id", "source_id", "source_version", "issuer", "label",
               "availability_until", "availability_basis", "distance", "quote_digest")

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ReceiptError(ValueError):
    """A ranking or an input the receipt refuses to record. The code is stable."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


def query_digest(text):
    """The SHA-256 of a question's text, exactly as supplied."""
    if type(text) is not str or not text.strip():
        raise ReceiptError("INVALID_QUERY", "a query is non-blank text")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cutoff_precision(value):
    """The precision a supplied cutoff value carries: ``date`` for a day, else the instant's."""
    if type(value) is not str:
        raise ReceiptError("INVALID_CUTOFF", "a cutoff is a date or an instant string")
    if _DATE.fullmatch(value):
        return "date"
    try:
        return records.instant_precision(value)
    except records.RowError as exc:
        raise ReceiptError("INVALID_CUTOFF", str(exc)) from None


def cutoff_until(value):
    """The cutoff's exclusive end, the one the store compares ``availability_until`` with."""
    try:
        return records.cutoff_interval(value, cutoff_precision(value))[1]
    except records.RowError as exc:
        raise ReceiptError("INVALID_CUTOFF", str(exc)) from None


def withheld_reason(row, until):
    """Why one pool row is not a candidate at a cutoff end, or ``None`` when it is one."""
    if row.get("availability_until") is None:
        return "availability_unknown"
    if not records.known_by(row, until):
        return "later_availability"
    if row.get("embedding") is None and not row.get("has_embedding"):
        return "no_embedding"
    return None


def basis_kind(row):
    """The availability basis as the receipt names it: the basis kind string, or ``None``."""
    basis = row.get("availability_basis")
    if type(basis) is dict:
        return basis.get("basis_kind")
    if type(basis) is str:
        return basis
    return None


def default_label(row):
    """A label from the row's own identity when the caller supplies none; never from its text."""
    if row.get("page") is not None:
        return "%s page %s" % (row.get("issuer") or row["source_id"], row["page"])
    return row["passage_id"]


def receipt(*, question_id, query, embedding_model, dimension, cutoff, mode, top_k, pool,
            ranked, backend, recorded_at, issuer=None, labels=None):
    """One ``corpus-retrieval.v1`` record, or a :class:`ReceiptError` naming what is wrong.

    ``pool`` is every passage row the question could reach (store rows and excluded-version
    stubs); ``ranked`` is the backend's answer in its own order, each row carrying at least
    ``passage_id`` and ``distance``. ``labels`` maps a passage id to the label the passages tool
    derived from its heading; a missing label falls back to :func:`default_label`.
    """
    _nonblank(question_id, "question_id")
    _nonblank(embedding_model, "embedding_model")
    _nonblank(backend, "backend")
    _nonblank(recorded_at, "recorded_at")
    if type(dimension) is not int or dimension < 1:
        raise ReceiptError("INVALID_DIMENSION", "dimension is a positive integer")
    if type(top_k) is not int or top_k < 1:
        raise ReceiptError("INVALID_TOP_K", "top_k is a positive integer")
    if mode not in MODES:
        raise ReceiptError("INVALID_MODE", "mode is one of %s" % (MODES,))
    if issuer is not None:
        _nonblank(issuer, "issuer")
    labels = labels or {}
    until = cutoff_until(cutoff)

    by_id, withheld, candidates = {}, {reason: 0 for reason in WITHHELD_REASONS}, set()
    for row in pool:
        passage_id = row.get("passage_id")
        _nonblank(passage_id, "passage_id")
        if passage_id in by_id:
            if _identity(by_id[passage_id]) != _identity(row):
                raise ReceiptError("POOL_CONFLICT",
                                   "passage %s appears twice with different content" % passage_id)
            continue
        by_id[passage_id] = row
        if issuer is not None and row.get("issuer") != issuer:
            continue
        reason = withheld_reason(row, until)
        if reason is None:
            candidates.add(passage_id)
        else:
            withheld[reason] += 1

    entries, seen, previous = [], set(), None
    for position, hit in enumerate(ranked, 1):
        passage_id = hit.get("passage_id")
        row = by_id.get(passage_id)
        if row is None:
            raise ReceiptError("RANKED_OUTSIDE_POOL",
                               "rank %d names %r, which is not in the pool" % (position, passage_id))
        if issuer is not None and row.get("issuer") != issuer:
            raise ReceiptError("RANKED_OUTSIDE_ISSUER",
                               "rank %d is issued by %r, not %r" % (position, row.get("issuer"), issuer))
        reason = withheld_reason(row, until)
        if reason is not None:
            raise ReceiptError("RANKED_WITHHELD",
                               "rank %d (%s) is withheld at this cutoff: %s"
                               % (position, passage_id, reason))
        if passage_id in seen:
            raise ReceiptError("RANKED_TWICE", "rank %d repeats %s" % (position, passage_id))
        seen.add(passage_id)
        distance = hit.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) \
                or not math.isfinite(distance):
            raise ReceiptError("INVALID_DISTANCE", "rank %d carries no finite distance" % position)
        key = (float(distance), passage_id)
        if previous is not None and key < previous:
            raise ReceiptError("RANK_ORDER",
                               "rank %d is nearer than rank %d; a ranking is ordered by "
                               "(distance, passage_id)" % (position, position - 1))
        previous = key
        for name in ("source_id", "source_version", "quote_digest"):
            if name in hit and hit[name] != row.get(name):
                raise ReceiptError("RANKED_MISMATCH",
                                   "rank %d's %s is not the pool row's" % (position, name))
        entries.append({
            "rank": position, "passage_id": passage_id, "source_id": row["source_id"],
            "source_version": row["source_version"], "issuer": row.get("issuer"),
            "label": labels.get(passage_id) or default_label(row),
            "availability_until": row["availability_until"],
            "availability_basis": basis_kind(row),
            "distance": float(distance), "quote_digest": row["quote_digest"]})
    if len(entries) > top_k:
        raise ReceiptError("RANKED_OVER_TOP_K", "%d rows ranked for top_k %d" % (len(entries), top_k))
    if len(entries) < min(top_k, len(candidates)):
        raise ReceiptError("RANKED_SHORT",
                           "%d rows ranked where %d candidates and top_k %d call for %d"
                           % (len(entries), len(candidates), top_k, min(top_k, len(candidates))))

    record = {
        "record": RECORD, "question_id": question_id, "query": query,
        "query_digest": query_digest(query), "embedding_model": embedding_model,
        "dimension": dimension, "cutoff": cutoff, "mode": mode, "issuer": issuer,
        "top_k": top_k, "candidates": len(candidates), "withheld": withheld,
        "ranked": entries, "backend": backend, "recorded_at": recorded_at}
    record["content_digest"] = compute_content_digest(record)
    return record


def check(receipt_record):
    """The receipt's own digest and shape, or a :class:`ReceiptError`."""
    if type(receipt_record) is not dict or receipt_record.get("record") != RECORD:
        raise ReceiptError("INVALID_RECEIPT", "not a %s record" % RECORD)
    if compute_content_digest(receipt_record) != receipt_record.get("content_digest"):
        raise ReceiptError("DIGEST_MISMATCH", "the receipt's content digest does not match it")
    for position, entry in enumerate(receipt_record.get("ranked", ()), 1):
        if entry.get("rank") != position:
            raise ReceiptError("INVALID_RECEIPT", "ranks are 1..n in order")
    return receipt_record


def passage_ids(receipt_record, limit=None, *, max_sources=None):
    """The ranked passage ids in order, capped for the compiler.

    The cap is the smallest of ``limit``, the receipt's own length and
    :data:`COMPILER_MAX_PASSAGES`. With ``max_sources``, ranks are taken in order and a rank
    whose source version would exceed that many distinct versions is skipped: each version
    adds dependency nodes to the compiler's 32-node budget, so a caller that knows its other
    dependencies can keep that budget too.
    """
    check(receipt_record)
    cap = COMPILER_MAX_PASSAGES if limit is None else min(int(limit), COMPILER_MAX_PASSAGES)
    if cap < 0:
        raise ReceiptError("INVALID_LIMIT", "limit is not negative")
    chosen, sources = [], set()
    for entry in receipt_record["ranked"]:
        if len(chosen) >= cap:
            break
        version = (entry["source_id"], entry["source_version"])
        if max_sources is not None and version not in sources and len(sources) >= max_sources:
            continue
        sources.add(version)
        chosen.append(entry["passage_id"])
    return chosen


def agree(receipt_a, receipt_b, tolerance=1e-6):
    """Whether two backends' receipts for one question rank the same passages the same way.

    Returns ``{"first_difference", "max_distance_delta", "reason", "compared"}``:
    ``first_difference`` is the first rank (1-based) where the passage ids differ, where one
    distance differs from the other by more than ``tolerance``, or where one ranking ends
    before the other — and ``None`` when they agree to the shorter of the two top-k's;
    ``max_distance_delta`` is the largest absolute distance difference over the ranks both
    hold with the same id; ``reason`` names the first difference (``passage_id``,
    ``distance``, ``length``, or a differing question, query, cutoff, issuer or model);
    ``compared`` is the number of ranks compared. Distances are compared unrounded.
    """
    check(receipt_a)
    check(receipt_b)
    for name in ("question_id", "query_digest", "cutoff", "issuer", "embedding_model",
                 "dimension"):
        if receipt_a.get(name) != receipt_b.get(name):
            return {"first_difference": 1, "max_distance_delta": None,
                    "reason": "%s differs" % name, "compared": 0}
    left, right = receipt_a["ranked"], receipt_b["ranked"]
    depth = min(receipt_a["top_k"], receipt_b["top_k"])
    left, right = left[:depth], right[:depth]
    first, reason, delta = None, None, 0.0
    for a, b in zip(left, right):
        if a["passage_id"] != b["passage_id"]:
            if first is None:
                first, reason = a["rank"], "passage_id"
            continue
        gap = abs(a["distance"] - b["distance"])
        delta = max(delta, gap)
        if gap > tolerance and first is None:
            first, reason = a["rank"], "distance"
    if first is None and len(left) != len(right):
        first, reason = min(len(left), len(right)) + 1, "length"
    return {"first_difference": first, "max_distance_delta": delta, "reason": reason,
            "compared": min(len(left), len(right))}


def present_distance(distance):
    """The presentation rule: six decimal places, applied only where a figure is shown."""
    return "%.6f" % distance


def _identity(row):
    return tuple(row.get(name) for name in ("source_id", "source_version", "start_offset",
                                            "end_offset", "quote_digest", "availability_until"))


def _nonblank(value, name):
    if type(value) is not str or not value.strip():
        raise ReceiptError("INVALID_RECEIPT", "%s is non-blank text" % name)


__all__ = ["COMPILER_MAX_PASSAGES", "MODES", "RANKED_KEYS", "RECORD", "ReceiptError",
           "WITHHELD_REASONS", "agree", "basis_kind", "check", "cutoff_until", "passage_ids",
           "present_distance", "query_digest", "receipt", "withheld_reason"]
