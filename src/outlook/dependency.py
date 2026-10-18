"""The dependency walk and stale marking: outlook -> assumptions -> evidence.

An issued outlook names the assumptions it rests on (``assumption_ids``, ARCH-1);
the register (ARCH-2) carries each assumption's proposition, its state and the
evidence it was read from; this module ties the two together and keeps the tie
when an assumption changes.

The walk
========

:func:`walk` follows one issued outlook's ``assumption_ids`` into the register and
returns, per assumption, its family, layer, state and *evidence refs* — the
``source_locator`` citations (path, line, verbatim quote) the register record was
read from — plus the ``affected_code`` paths its value flows through. An
assumption id the register does not carry is reported under ``unknown`` rather
than resolved or dropped: the walk never invents the evidence of a name it cannot
read. :func:`walk_archive` walks every issued outlook of an archive. The walk also
reports, per outlook, the scoring receipts that name its exact issued bytes and,
beside each receipt, the attributions that cite its own digest grouped by cause —
the desk's review reads them to answer what the desk believed and what explains a
miss.

Stale marking
=============

A change to an assumption is a register edit made at a revision. When the change
lands, every outlook that rests on that assumption is stale: it was issued from a
value that no longer holds. :func:`mark_stale` finds those outlooks — every issued
outlook whose ``assumption_ids`` contain the changed assumption and whose issue
precedes the marking instant, because an outlook issued after the change already
cites the changed register — and appends one :class:`StaleMark` record per
affected outlook to ``<root>/stale/``. It erases nothing: no outlook file is
written on this path, the stored bytes and their digest stay exactly as issued,
and the mark is a new file beside them.

A mark names the assumption, the revision the change landed at, the exact issued
bytes it affects (``outlook_id`` and ``outlook_digest``), the state the assumption
carried in the register when the change was marked, and the instant of marking.
A mark's identity is the change it records together with the provenance it
declares — ``(assumption_id, new_revision, outlook_digest, synthetic)`` — and the
file name is the digest of that key, so a duplicate is refused atomically by
``O_EXCL`` rather than by a scan that a concurrent write could slip past.
Provenance is part of the identity because it is part of what a mark asserts: a
demonstration and a real mark of one change are different statements, so they
stand in separate files, and a labelled demonstration can never refuse the real
mark a change lands.

Provenance follows the archive's rule, one way. A mark whose ``synthetic`` is
``False`` declares a real change; a mark whose ``synthetic`` is ``True`` declares
itself a demonstration (and is written by a labelled exercise, never by an
evidence event). :func:`stale_outlooks` reports the real stale set — an outlook
marked only by demonstrations is *not* stale — while :func:`marks_of` and
:meth:`StaleMarks.marks` read every mark back, demonstrations included, so a
demonstration is visible and labelled rather than hidden. No clock is read
anywhere: ``marked_at`` is a caller-supplied instant, like every other timestamp
in this archive.

The direction check (ARCH-3, as restated 2026-10-16)
====================================================

:func:`direction_share` records the ARCH-3 direction check — the count of
assumptions changed between two monthly outlooks of the same target series. The
changes it counts are the real marks whose ``marked_at`` falls in the interval
between the two issues; the denominator is the union of the assumption ids the
two outlooks cite. It refuses a pair that is not two month-horizon outlooks of
the same series, or that is not ordered, rather than reporting a count over
records that cannot carry one.

The check was restated on 2026-10-16 (``docs/work/price-outlook/intent.md``,
"Direction checks"; ``docs/work/thesis-challenge-2026-10-16/problem-and-thesis.md``,
"Direction checks, restated in pesos"): what decides is whether an accepted
assumption change moves the portfolio impact past the stated materiality
threshold at least once in the scored months, and that measurement is IMPACT-1's.
The "one assumption in ten" count this function returns stays recorded but no
longer decides; the first monthly pair it can be read over is 2026-11 -> 2026-12.

Module rules: standard library only, plus this package's own record kinds, the
register and the repository's canonical JSON. The archive and the register are
read, never edited here; the only writes are new mark files under ``stale/``.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from src.contracts.jsonutil import (
    CanonicalizationError,
    canonical_dumps,
    compute_content_digest,
    parse_json,
)
from src.outlook import register as register_module
from src.outlook.records import (
    CAUSES,
    OutlookArchive,
    OutlookError,
    validate_outlook,
)

#: The archive's schema version, carried by the mark records this module writes.
SCHEMA_VERSION = "outlook.v1"
MARK_KIND = "StaleMark"
#: The directory of marks, beside ``outlooks/`` and ``receipts/`` under the root.
MARKS_DIR = "stale"

#: The mark's keys, exactly; a mark with another key is refused rather than read.
MARK_KEYS = frozenset({
    "schema_version", "kind", "assumption_id", "new_revision", "outlook_id",
    "outlook_digest", "assumption_state", "marked_at", "synthetic", "content_digest",
})

DIGEST = re.compile(r"^[0-9a-f]{64}$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
#: A commit id, shortened or full — the register's own revision form.
REVISION = re.compile(r"^[0-9a-f]{7,40}$")
#: A register id: ``<family>:<slug>``, one safe token (the register's own shape).
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

MESSAGES = {
    "STALE_INVALID": "the stale mark does not satisfy the dependency contract",
    "STALE_DUPLICATE": "that change is already marked for that outlook revision",
    "ASSUMPTION_UNKNOWN": "the register carries no assumption with that identifier",
    "DEPENDENCY_IO": "the mark could not be written or read",
    "NOT_MONTHLY": "the direction check compares two month-horizon outlooks of one target series",
    "NOT_ORDERED": "the second outlook of a direction check is not issued after the first",
}


class DependencyError(ValueError):
    """A dependency refusal whose text :data:`MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, MESSAGES[code])


def _require(condition, code="STALE_INVALID"):
    if not condition:
        raise DependencyError(code)


def _instant(value, code="STALE_INVALID"):
    """Parse one offset-bearing timestamp to an aware UTC datetime."""
    _require(type(value) is str and INSTANT.fullmatch(value) is not None, code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise DependencyError(code) from None
    return parsed.astimezone(timezone.utc)


def _seal(record):
    try:
        record["content_digest"] = compute_content_digest(record)
    except CanonicalizationError:
        raise DependencyError("STALE_INVALID") from None
    return record


def _canonical_text(record):
    try:
        return canonical_dumps(record)
    except CanonicalizationError:
        raise DependencyError("DEPENDENCY_IO") from None


def _key_of(assumption_id, new_revision, outlook_digest, synthetic):
    """The unique key of one mark, as a file name: the marked triple and its provenance.

    The key is hashed so the file name is fixed by the marked
    ``(assumption_id, new_revision, outlook_digest)`` and by the provenance the
    mark declares. A second append of the same triple *with the same
    provenance* therefore collides on the name and is refused by ``O_EXCL``,
    whatever the mark's own ``marked_at`` would hash to. The two provenances do
    not collide: a demonstration and a real mark of one change are separate
    records in separate files, so a demonstration can never refuse the real
    mark, nor the real mark the demonstration.
    """
    key = canonical_dumps({
        "assumption_id": assumption_id,
        "new_revision": new_revision,
        "outlook_digest": outlook_digest,
        "synthetic": synthetic,
    })
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# --- the register, read for the walk -------------------------------------


def _load(register_payload):
    """A validated register: the caller's payload, or the committed file."""
    if register_payload is None:
        return register_module.load_register()
    return register_module.register(register_payload)


def assumption_of(register_payload, assumption_id):
    """The register record for one id, or ``None``; the payload is validated first."""
    payload = _load(register_payload)
    for item in payload["assumptions"]:
        if item["assumption_id"] == assumption_id:
            return dict(item)
    return None


def evidence_refs(record):
    """The citations one register record was read from, as a list of copies."""
    return [dict(locator) for locator in record["source_locator"]]


# --- the walk --------------------------------------------------------------


def walk(outlook, *, register_payload=None, marks=(), receipts=(), attributions=()):
    """One outlook, its assumptions, the evidence each cites, and its receipts' attributions.

    Returns ``{"outlook_id", "outlook_digest", "issued_at", "information_cutoff",
    "horizon", "target_series_ref", "assumptions", "unknown", "stale", "receipts"}``.
    Each entry of ``assumptions`` is ``{"assumption_id", "known", "family", "layer",
    "state", "proposition", "evidence", "affected_code"}``; ``known`` is ``False``
    and the record carries an empty evidence list when the register does not
    carry the id, which is also reported in ``unknown``. ``stale`` holds the
    marks naming this outlook's exact issued bytes — each with its ``synthetic``
    flag, so a demonstration is read as a demonstration.

    ``receipts`` and ``attributions`` are the lists the caller read from the
    archive (:meth:`~src.outlook.records.OutlookArchive.receipts` and
    :meth:`~src.outlook.records.OutlookArchive.attributions`). ``receipts`` in
    the result holds the receipts naming this outlook's exact issued bytes, each
    as ``{"receipt": {...}, "attributions": {"belief": [...], "signal": [...],
    "method": [...]}}`` — the statement the desk's review reads beside the
    score. Every existing field is unchanged; an outlook with no receipt carries
    an empty list.
    """
    validate_outlook(outlook)
    payload = _load(register_payload)
    by_id = {item["assumption_id"]: item for item in payload["assumptions"]}
    assumptions, unknown = [], []
    for assumption_id in outlook["assumption_ids"]:
        item = by_id.get(assumption_id)
        if item is None:
            unknown.append(assumption_id)
            assumptions.append({"assumption_id": assumption_id, "known": False, "evidence": []})
            continue
        assumptions.append({
            "assumption_id": assumption_id,
            "known": True,
            "family": item["family"],
            "layer": item["layer"],
            "state": item["state"],
            "proposition": item["proposition"],
            "evidence": evidence_refs(item),
            "affected_code": list(item["affected_code"]),
        })
    # The receipts naming this outlook's exact issued bytes, each beside the
    # attributions that cite its own digest; the three causes are always present
    # as keys, so a cause with no statement reads as an empty list and not as a
    # missing one. The lists are the archive's own order.
    scored = []
    for receipt in receipts:
        if (receipt["outlook_id"] != outlook["outlook_id"]
                or receipt["outlook_digest"] != outlook["content_digest"]):
            continue
        grouped = {cause: [] for cause in CAUSES}
        for attribution in attributions:
            if attribution["receipt_digest"] == receipt["content_digest"]:
                grouped[attribution["cause"]].append(dict(attribution))
        scored.append({"receipt": dict(receipt), "attributions": grouped})
    return {
        "outlook_id": outlook["outlook_id"],
        "outlook_digest": outlook["content_digest"],
        "issued_at": outlook["issued_at"],
        "information_cutoff": outlook["information_cutoff"],
        "horizon": dict(outlook["horizon"]),
        "target_series_ref": dict(outlook["target_series_ref"]),
        "assumptions": assumptions,
        "unknown": unknown,
        "stale": [dict(mark) for mark in marks
                  if mark["outlook_digest"] == outlook["content_digest"]],
        "receipts": scored,
    }


def walk_archive(archive, *, register_payload=None):
    """Every issued outlook of an archive, walked; ordered by outlook id."""
    store = StaleMarks(archive.root)
    marks = store.marks()
    receipts = archive.receipts()
    attributions = archive.attributions()
    payload = _load(register_payload)
    return [walk(archive.outlook(outlook_id), register_payload=payload, marks=marks,
                 receipts=receipts, attributions=attributions)
            for outlook_id in archive.issue_ids()]


# --- the mark record -------------------------------------------------------


def build_mark(*, assumption_id, new_revision, outlook, assumption_state, marked_at, synthetic):
    """Seal and validate one ``StaleMark`` against the outlook it marks.

    ``outlook`` is the issued record whose bytes the change reaches; its id and
    digest are read from the record, so a mark cannot name some other revision
    by accident. ``assumption_state`` is the state the register gave the
    assumption when the change was marked (``accepted`` for an accepted
    assumption); ``marked_at`` is caller-supplied, as every instant is here.
    """
    validate_outlook(outlook)
    return validate_mark(_seal({
        "schema_version": SCHEMA_VERSION,
        "kind": MARK_KIND,
        "assumption_id": assumption_id,
        "new_revision": new_revision,
        "outlook_id": outlook["outlook_id"],
        "outlook_digest": outlook["content_digest"],
        "assumption_state": assumption_state,
        "marked_at": marked_at,
        "synthetic": synthetic,
    }))


def validate_mark(record):
    """Validate one ``StaleMark`` envelope, its content digest included.

    The mark is a record of the same archive as the outlooks and receipts, so it
    is checked the same way: a closed key set, a sealed digest over everything
    else, and vocabularies the register owns (a state is not invented here).
    """
    _require(type(record) is dict)
    _require(set(record) == MARK_KEYS)
    _require(record["schema_version"] == SCHEMA_VERSION and record["kind"] == MARK_KIND)
    _require(type(record["content_digest"]) is str and DIGEST.fullmatch(record["content_digest"]) is not None)
    try:
        recomputed = compute_content_digest(record)
    except CanonicalizationError:
        raise DependencyError("STALE_INVALID") from None
    _require(recomputed == record["content_digest"])
    _require(type(record["assumption_id"]) is str and IDENTIFIER.fullmatch(record["assumption_id"]) is not None)
    _require(type(record["new_revision"]) is str and REVISION.fullmatch(record["new_revision"]) is not None)
    _require(type(record["outlook_id"]) is str and IDENTIFIER.fullmatch(record["outlook_id"]) is not None)
    _require(type(record["outlook_digest"]) is str and DIGEST.fullmatch(record["outlook_digest"]) is not None)
    # The state vocabulary is the register's own; a mark cannot name a state the
    # register would refuse. The type is checked before membership, so a list or
    # a number is refused as a mark rather than raising out of the contract.
    _require(type(record["assumption_state"]) is str and record["assumption_state"] in register_module.STATES)
    _instant(record["marked_at"])
    _require(type(record["synthetic"]) is bool)
    return record


def _read_mark(path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise DependencyError("DEPENDENCY_IO") from None
    value, error = parse_json(text)
    if error is not None:
        raise DependencyError("STALE_INVALID")
    try:
        mark = validate_mark(value)
    except DependencyError:
        raise DependencyError("STALE_INVALID") from None
    if _key_of(mark["assumption_id"], mark["new_revision"], mark["outlook_digest"],
               mark["synthetic"]) != path.stem:
        raise DependencyError("STALE_INVALID")
    return mark


class StaleMarks:
    """One directory of stale marks: ``<root>/stale/<key>.json``.

    The store is directory-backed like :class:`~src.outlook.records.OutlookArchive`
    and lives beside it. Writes are once-only per ``(assumption_id, new_revision,
    outlook_digest, synthetic)``; there is no update, edit or delete method, and
    nothing on this path writes an outlook.
    """

    def __init__(self, root):
        self.root = Path(root)

    @property
    def marks_dir(self):
        return self.root / MARKS_DIR

    def append(self, record):
        """Write one validated mark; the same change of the same provenance is refused."""
        mark = validate_mark(record)
        path = self.marks_dir / (
            _key_of(mark["assumption_id"], mark["new_revision"], mark["outlook_digest"],
                    mark["synthetic"]) + ".json")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise DependencyError("DEPENDENCY_IO") from None
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_text(mark))
                handle.write("\n")
        except FileExistsError:
            raise DependencyError("STALE_DUPLICATE") from None
        except OSError:
            raise DependencyError("DEPENDENCY_IO") from None
        return mark

    def marks(self, outlook_id=None):
        """Every stored mark, or those naming one outlook, ordered by file name."""
        found = []
        for path in sorted(self.marks_dir.glob("*.json")):
            mark = _read_mark(path)
            if outlook_id is None or mark["outlook_id"] == outlook_id:
                found.append(mark)
        return tuple(found)

    def verify(self, archive):
        """Re-read every mark against the archive it marks.

        Returns ``{"marks": n, "problems": [...]}``. A mark whose outlook is not
        issued, or whose ``outlook_digest`` names other bytes than the stored
        outlook, is reported: an outlook replaced after issue breaks the marks
        that cite it, exactly as it breaks its receipts.
        """
        report = {"marks": 0, "problems": []}
        for path in sorted(self.marks_dir.glob("*.json")):
            try:
                mark = _read_mark(path)
            except DependencyError as error:
                report["problems"].append(f"{path.name}: {error.code}")
                continue
            report["marks"] += 1
            try:
                outlook = archive.outlook(mark["outlook_id"])
            except OutlookError:
                report["problems"].append(f"{path.name}: OUTLOOK_UNKNOWN")
                continue
            if mark["outlook_digest"] != outlook["content_digest"]:
                report["problems"].append(f"{path.name}: OUTLOOK_DIGEST_MISMATCH")
        return report


# --- stale marking ---------------------------------------------------------


def mark_stale(archive, assumption_id, new_revision, *, marked_at,
               register_payload=None, synthetic=False):
    """Mark every outlook that rests on a changed assumption stale.

    ``archive`` is the issued outlooks; ``assumption_id`` must be one the
    register carries (an unknown id is refused, never marked) and
    ``new_revision`` is the revision the change landed at. One
    :class:`StaleMark` is appended per affected outlook — every issued outlook
    whose ``assumption_ids`` contain the changed assumption — and the tactic
    returns their ids, sorted. Nothing is erased: the outlooks are read only,
    and their bytes and digests stay as issued.

    ``synthetic=True`` writes a labelled demonstration mark instead of a real
    one; :func:`stale_outlooks` counts only real marks, so a demonstration never
    makes a healthy outlook read as stale.

    The scan covers the outlooks that exist at the marking instant: an outlook
    issued after ``marked_at`` already cites the changed register and is not
    invalidated by the change, so it is left unmarked. The desk marks when the
    change lands, which is what keeps the two instants — the change and its
    marking — the same event.
    """
    payload = _load(register_payload)
    item = None
    for row in payload["assumptions"]:
        if row["assumption_id"] == assumption_id:
            item = row
            break
    _require(item is not None, "ASSUMPTION_UNKNOWN")
    marked = _instant(marked_at, "STALE_INVALID")
    store = StaleMarks(archive.root)
    affected = []
    for outlook_id in archive.issue_ids():
        outlook = archive.outlook(outlook_id)
        if assumption_id not in outlook["assumption_ids"]:
            continue
        if _instant(outlook["issued_at"]) > marked:
            continue
        store.append(build_mark(
            assumption_id=assumption_id,
            new_revision=new_revision,
            outlook=outlook,
            assumption_state=item["state"],
            marked_at=marked_at,
            synthetic=synthetic,
        ))
        affected.append(outlook_id)
    return tuple(affected)


def marks_of(archive, outlook_id=None):
    """Every mark stored for an archive, or for one outlook; demonstrations included."""
    return StaleMarks(archive.root).marks(outlook_id)


def stale_outlooks(archive):
    """The outlooks a *real* mark names, sorted: the archive's current stale set.

    A mark whose ``synthetic`` is ``True`` is a demonstration and is not counted
    here — the one-way provenance rule the archive keeps for receipts, kept for
    marks: a demonstration may sit beside a real outlook without asserting that
    something real changed, and it stays readable through :func:`marks_of`.
    """
    return tuple(sorted({mark["outlook_id"] for mark in marks_of(archive) if not mark["synthetic"]}))


def demonstration_outlooks(archive):
    """The outlooks marked by demonstrations only, sorted."""
    real = set(stale_outlooks(archive))
    return tuple(sorted({mark["outlook_id"] for mark in marks_of(archive)
                         if mark["synthetic"] and mark["outlook_id"] not in real}))


# --- the direction check ---------------------------------------------------


def direction_share(first, second, marks=(), *, register_payload=None):
    """The share of assumptions changed between two monthly outlooks.

    ``first`` and ``second`` are two *distinct* issued outlooks of the same
    target series (table and column) with the month horizon, ``second`` issued
    strictly after ``first``; anything else is refused, because a share over
    another pair would answer a different question. An outlook compared with
    itself is not a pair, and two outlooks issued at one instant carry no
    interval to measure between, so both are refused rather than answered with
    an unsupported zero. The denominator is the union of the assumption ids the
    two outlooks cite. The numerator is the assumptions whose change is *real* —
    a mark with ``synthetic=False`` whose ``marked_at`` falls in
    ``(first.issued_at, second.issued_at]`` — so a demonstration never moves the
    check. Returns ``{"changed", "union", "changed_count", "union_count",
    "share"}`` with the ids in their stored order and the share a float over the
    union (``0.0`` for an empty union).

    The count is recorded, not deciding: the check was restated on 2026-10-16
    and the measurement that decides — portfolio impact past the stated
    materiality threshold, in pesos — is IMPACT-1's (module docstring).
    """
    validate_outlook(first)
    validate_outlook(second)
    # A monthly pair is two issues: one outlook twice, or two issues sharing an
    # id, is not one — the archive never issues two records under one id.
    _require(first["outlook_id"] != second["outlook_id"], "NOT_MONTHLY")
    # The series is compared by table and column, not by version: consecutive
    # monthly outlooks name the series version of their own month.
    _require(first["horizon"]["label"] == "month" and second["horizon"]["label"] == "month"
             and {key: first["target_series_ref"][key] for key in ("table", "column")}
             == {key: second["target_series_ref"][key] for key in ("table", "column")},
             "NOT_MONTHLY")
    start = _instant(first["issued_at"], "NOT_ORDERED")
    end = _instant(second["issued_at"], "NOT_ORDERED")
    # Strictly ordered: the second issue must follow the first, so the interval
    # the numerator is counted over is never empty.
    _require(start < end, "NOT_ORDERED")
    union = sorted(set(first["assumption_ids"]) | set(second["assumption_ids"]))
    changed = sorted({mark["assumption_id"] for mark in marks
                      if not mark["synthetic"] and mark["assumption_id"] in union
                      and start < _instant(mark["marked_at"], "STALE_INVALID") <= end})
    return {
        "changed": changed,
        "union": union,
        "changed_count": len(changed),
        "union_count": len(union),
        "share": (len(changed) / len(union)) if union else 0.0,
    }


__all__ = [
    "DependencyError",
    "MARK_KIND",
    "MARK_KEYS",
    "MESSAGES",
    "SCHEMA_VERSION",
    "StaleMarks",
    "assumption_of",
    "build_mark",
    "demonstration_outlooks",
    "direction_share",
    "evidence_refs",
    "mark_stale",
    "marks_of",
    "stale_outlooks",
    "validate_mark",
    "walk",
    "walk_archive",
]
