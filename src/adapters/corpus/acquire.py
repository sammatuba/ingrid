"""The acquisition contract: immutable document versions with a fingerprint and five times.

One call turns exact bytes plus supplied metadata into one :class:`SourceVersion` record:
the issuer, the URL or path, the publication date with its precision or its unknown
reason, the fetch time, the licence. The module is standard library only. It opens no
socket, reads no file, consults no clock and calls no model; the caller brings the bytes
and every time.

**The five-field time contract** of the ontology profile, on this record:

1. *event time* — absent on purpose. A document version has no single event time; a claim
   carries the time of the condition it describes.
2. *publication time* — ``publication``: the value the issuer states, with its precision,
   or unknown with the reason. The record never reads a date out of the text.
3. *first availability* — ``known_at`` with a typed ``availability_basis``, or unknown
   with a reason. Publication is not availability, and a basis says where first
   availability was observed, never when.
4. *recorded time* — ``recorded_at``: when this acquisition record was written.
5. *review/audit time* — absent on purpose: acquisition precedes any review decision.

**Identity.** ``source_id`` is derived from the normalized locator alone, so the same URL
always names the same source. ``source_version`` is the ordinal of the bytes first seen at
that locator: the same bytes there always give the same version, and changed bytes give a
new one. Given the records already held for that locator — which the caller passes as
``prior``, and which the fetch tool reads back from its own acquisition payloads — the
same bytes give the same record too, in any order of calls; a later capture of known bytes
is evidence for the fetch log, not a change to the record. A caller that drops the priors
still gets the same version, with its own capture facts, and the review core then refuses
to register both: one version with two contents is a conflict, not a second version.

**What is excluded.** A version whose publication instant the issuer does not state is
recorded with no first availability and a reason, and it has no projection into the review
core, so no compiled context can cite it. The same holds for a version with no supplied
first-availability evidence. This is the conservative reading the register and the
ontology profile ask for: the desk cannot say which revision of a rule was knowable at a
cutoff when the version's own publication instant is unknown, and a capture time proves
the bytes were reachable then without proving the version was knowable at the cutoff. An
excluded version keeps its fingerprint, length, licence and text layer, so a later task
can cite it as an explicit unknown rather than lose it. When the missing fact arrives — a
register that states the publication, evidence that dates first availability — the same
bytes give the same version with the record repaired: an excluded record was never
projected, so nothing downstream can depend on the unknown it declared. A *stated* fact is
never repaired this way; that is a reviewed correction, and a re-acquisition is refused.

**Storage.** Document bytes and extracted text stay outside Git: the fetch tool writes
them under ``.local/corpus/`` and the orchestrator uploads them to the company bucket with
``scripts/corpus/upload.sh``. The repository keeps this code, the tests and the records.
"""
from __future__ import annotations

import hashlib
import posixpath
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from src.contracts.jsonutil import compute_content_digest
from src.review.records import make_record, reference

from .text import sniff_content_type, validate_locator

#: The four typed availability bases of the h0.v2 contract. A register row's
#: ``first_availability_rule`` names the evidence kind its family is read with, and the
#: supplied evidence must be of that kind: the rule the register states is the rule used.
BASIS_KINDS = ("feed_logged_at", "capture_logged_at", "archive_snapshot", "attested")

PUBLICATION_PRECISIONS = ("date", "second", "fraction")

#: The record marker written into every acquisition payload.
RECORD = "corpus-source-version.v1"

#: Suffix for the fetched bytes, from the content type; the fallback is ``.bin``.
EXTENSIONS = {
    "application/pdf": "pdf",
    "text/html": "html",
    "application/xhtml+xml": "html",
    "text/plain": "txt",
    "text/xml": "xml",
    "application/xml": "xml",
    "application/json": "json",
    "text/csv": "csv",
    "application/octet-stream": "bin",
}

INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONTENT_TYPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*/[A-Za-z0-9][A-Za-z0-9.+-]*$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

#: The payload keys that state a fact about the version itself. A re-observation is
#: refused when it contradicts one of them; ``capture_time`` and ``recorded_at`` are
#: properties of one observation and one write, so they are not in this set.
STATED_FACTS = ("source_id", "source_version", "lineage_id", "issuer", "locator",
                "content_type", "content_type_source", "document_length",
                "document_sha256", "licence_ref", "access_policy_ref",
                "first_availability_rule", "publication", "synthetic", "permission_ref")


class CorpusError(ValueError):
    """A refused document, locator, metadata value or projection.

    The code is stable and machine-readable; the detail names the cause. Nothing here is
    a data-quality repair: a document that does not satisfy the contract is refused or
    recorded with its unknown, never adjusted.
    """

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


def _nonblank(value, name, code="INVALID_METADATA"):
    if type(value) is not str or not value.strip():
        raise CorpusError(code, "%s must be a non-blank string" % name)
    return value.strip()


def _moment(value, name):
    """An offset-bearing instant as a UTC ``datetime``; date-only input is refused here."""
    if type(value) is not str or not INSTANT.fullmatch(value):
        raise CorpusError("MALFORMED_TIME", "%s is not an offset-bearing instant: %r" % (name, value))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise CorpusError("MALFORMED_TIME", "%s is not a calendar instant: %r" % (name, value)) from None
    return parsed.astimezone(timezone.utc)


def _instant(value, name):
    """An offset-bearing instant normalized to UTC ``Z``, as the record stores it."""
    return _moment(value, name).isoformat().replace("+00:00", "Z")


def _earlier(first, second):
    """Whether instant ``first`` precedes instant ``second``; both are stored as UTC ``Z``."""
    return _moment(first, "instant") < _moment(second, "instant")


@dataclass(frozen=True)
class SuppliedDate:
    """A date the caller supplies: a stated value with its precision, or an unknown reason.

    The precision is the caller's claim about the value and must match its shape: ``date``
    is ``YYYY-MM-DD`` (a date, never midnight), ``second`` an offset-bearing instant
    without a fraction, ``fraction`` one with. Nothing here reads a date out of a document.
    """

    value: str | None
    precision: str | None
    unknown_reason: str | None

    def __post_init__(self):
        if self.value is None:
            if self.precision is not None:
                raise CorpusError("INVALID_METADATA", "an unknown date cannot carry a precision")
            _nonblank(self.unknown_reason, "unknown_reason")
            return
        if self.precision not in PUBLICATION_PRECISIONS:
            raise CorpusError("INVALID_METADATA",
                              "precision must be one of %s" % (PUBLICATION_PRECISIONS,))
        if self.unknown_reason is not None:
            raise CorpusError("INVALID_METADATA", "a stated date cannot also carry an unknown reason")
        if self.precision == "date":
            if not DATE_ONLY.fullmatch(self.value):
                raise CorpusError("MALFORMED_TIME", "a date-precision value must be YYYY-MM-DD: %r" % self.value)
            try:
                datetime.fromisoformat(self.value)
            except ValueError:
                raise CorpusError("MALFORMED_TIME", "not a calendar date: %r" % self.value) from None
        else:
            _moment(self.value, "publication")
            fraction = "." in self.value.split("T", 1)[-1]
            if fraction != (self.precision == "fraction"):
                raise CorpusError("MALFORMED_TIME",
                                  "precision %s does not match the value %r" % (self.precision, self.value))

    @classmethod
    def unknown(cls, reason):
        """The issuer states no publication instant, and this says how that is known."""
        return cls(None, None, reason)

    @classmethod
    def stated(cls, value, precision):
        """A stated publication value with the caller's precision claim."""
        return cls(value, precision, None)

    @property
    def unknown_value(self):
        return self.value is None

    def payload(self):
        return {"value": self.value, "precision": self.precision,
                "unknown_reason": self.unknown_reason}

    @classmethod
    def from_payload(cls, data):
        if type(data) is not dict:
            raise CorpusError("INVALID_RECORD", "publication must be an object")
        return cls(data.get("value"), data.get("precision"), data.get("unknown_reason"))


@dataclass(frozen=True)
class Availability:
    """First-availability evidence: the instant it establishes and where it was observed.

    ``at`` is the instant at which this version first became available to this workflow,
    ``basis_kind`` is the evidence kind (a register row's ``first_availability_rule``
    names it), ``basis_ref`` names the log, archive or person, and ``note`` is free text
    that never changes the instant.
    """

    basis_kind: str
    basis_ref: str
    at: str
    note: str = ""

    def __post_init__(self):
        if self.basis_kind not in BASIS_KINDS:
            raise CorpusError("INVALID_METADATA", "basis_kind must be one of %s" % (BASIS_KINDS,))
        _nonblank(self.basis_ref, "basis_ref")
        if type(self.note) is not str:
            raise CorpusError("INVALID_METADATA", "note must be a string")
        object.__setattr__(self, "at", _instant(self.at, "availability.at"))

    def basis(self):
        """The typed ``availability_basis`` object the h0.v2 payload carries."""
        return {"basis_kind": self.basis_kind, "basis_ref": self.basis_ref, "note": self.note}


@dataclass(frozen=True)
class SuppliedMetadata:
    """Everything the acquisition is told, and nothing it invents.

    ``issuer`` names the organisation the document is attributed to, ``locator`` the
    absolute URL or the path it was read from, ``licence_ref`` the stated terms, and
    ``capture_time`` the instant this workflow fetched the bytes. ``availability`` may
    carry other evidence (an attested upload, a dated archive). ``synthetic`` and
    ``permission_ref`` are the h0.v2 pair every record declares; a real version names a
    signed permission.
    """

    issuer: str
    locator: str
    publication: SuppliedDate
    licence_ref: str
    capture_time: str | None = None
    availability: Availability | None = None
    content_type: str | None = None
    first_availability_rule: str | None = None
    access_policy_ref: str | None = None
    synthetic: bool = True
    permission_ref: str | None = None

    def __post_init__(self):
        _nonblank(self.issuer, "issuer")
        _nonblank(self.locator, "locator")
        _nonblank(self.licence_ref, "licence_ref")
        if not isinstance(self.publication, SuppliedDate):
            raise CorpusError("INVALID_METADATA", "publication must be a SuppliedDate")
        if self.capture_time is not None:
            object.__setattr__(self, "capture_time", _instant(self.capture_time, "capture_time"))
        if self.availability is not None and not isinstance(self.availability, Availability):
            raise CorpusError("INVALID_METADATA", "availability must be an Availability")
        if self.content_type is not None:
            if not CONTENT_TYPE.fullmatch(self.content_type.strip()):
                raise CorpusError("INVALID_METADATA",
                                  "content_type is not a media type: %r" % self.content_type)
            object.__setattr__(self, "content_type", self.content_type.strip())
        if self.first_availability_rule is not None and self.first_availability_rule not in BASIS_KINDS:
            raise CorpusError("INVALID_METADATA",
                              "first_availability_rule must be one of %s" % (BASIS_KINDS,))
        if self.access_policy_ref is not None:
            _nonblank(self.access_policy_ref, "access_policy_ref")
        if type(self.synthetic) is not bool:
            raise CorpusError("INVALID_METADATA", "synthetic must be a boolean")
        if not self.synthetic:
            _nonblank(self.permission_ref, "permission_ref")


@dataclass(frozen=True)
class SourceVersion:
    """One immutable document version: identity, fingerprint, five times, licence, state.

    ``known_at`` and ``availability_basis`` follow the h0.v2 pair: a version with a known
    first availability carries the typed basis of the evidence, a version without one
    carries no basis and a non-blank ``unknown_reason``. ``capture_time`` is this
    workflow's own observation instant, kept even when the version is excluded, so the
    bytes are never unmoored from when they were seen.
    """

    source_id: str
    source_version: str
    lineage_id: str
    issuer: str
    locator: str
    content_type: str
    content_type_source: str
    document_length: int
    document_sha256: str
    licence_ref: str
    access_policy_ref: str
    publication: SuppliedDate
    recorded_at: str
    first_availability_rule: str | None = None
    known_at: str | None = None
    availability_basis: dict | None = None
    unknown_reason: str | None = None
    capture_time: str | None = None
    synthetic: bool = True
    permission_ref: str | None = None

    @property
    def state(self):
        """``compilable`` when the version can enter a compiled context, else ``excluded``."""
        return "compilable" if self.known_at is not None else "excluded"

    def time_contract(self):
        """The ontology's five time fields for this version, each with its source."""
        return {
            "event_time": {"value": None,
                           "reason": "a document version has no single event time; a claim carries it"},
            "publication_time": {"value": self.publication.value, "precision": self.publication.precision,
                                 "unknown_reason": self.publication.unknown_reason},
            "first_availability": {"value": self.known_at, "basis": self.availability_basis,
                                   "unknown_reason": self.unknown_reason},
            "recorded_at": {"value": self.recorded_at},
            "review_time": {"value": None, "reason": "acquisition precedes any review decision"},
        }

    def payload(self):
        """The record as JSON-safe data: what the fetch tool writes beside the bytes."""
        return {
            "record": RECORD,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "lineage_id": self.lineage_id,
            "issuer": self.issuer,
            "locator": self.locator,
            "content_type": self.content_type,
            "content_type_source": self.content_type_source,
            "document_length": self.document_length,
            "document_sha256": self.document_sha256,
            "licence_ref": self.licence_ref,
            "access_policy_ref": self.access_policy_ref,
            "first_availability_rule": self.first_availability_rule,
            "publication": self.publication.payload(),
            "known_at": self.known_at,
            "availability_basis": self.availability_basis,
            "unknown_reason": self.unknown_reason,
            "capture_time": self.capture_time,
            "recorded_at": self.recorded_at,
            "state": self.state,
            "synthetic": self.synthetic,
            "permission_ref": self.permission_ref,
        }

    @classmethod
    def from_payload(cls, data):
        """The record a stored payload holds; its state is re-derived and must agree."""
        if type(data) is not dict or data.get("record") != RECORD:
            raise CorpusError("INVALID_RECORD", "payload is not a %s record" % RECORD)
        try:
            record = cls(
                source_id=_nonblank(data["source_id"], "source_id", "INVALID_RECORD"),
                source_version=_nonblank(data["source_version"], "source_version", "INVALID_RECORD"),
                lineage_id=_nonblank(data["lineage_id"], "lineage_id", "INVALID_RECORD"),
                issuer=_nonblank(data["issuer"], "issuer", "INVALID_RECORD"),
                locator=_nonblank(data["locator"], "locator", "INVALID_RECORD"),
                content_type=_nonblank(data["content_type"], "content_type", "INVALID_RECORD"),
                content_type_source=data["content_type_source"],
                document_length=data["document_length"],
                document_sha256=data["document_sha256"],
                licence_ref=_nonblank(data["licence_ref"], "licence_ref", "INVALID_RECORD"),
                access_policy_ref=_nonblank(data["access_policy_ref"], "access_policy_ref", "INVALID_RECORD"),
                publication=SuppliedDate.from_payload(data["publication"]),
                recorded_at=_instant(data["recorded_at"], "recorded_at"),
                first_availability_rule=data.get("first_availability_rule"),
                known_at=None if data.get("known_at") is None else _instant(data["known_at"], "known_at"),
                availability_basis=data.get("availability_basis"),
                unknown_reason=data.get("unknown_reason"),
                capture_time=(None if data.get("capture_time") is None
                              else _instant(data["capture_time"], "capture_time")),
                synthetic=data.get("synthetic") is True,
                permission_ref=data.get("permission_ref"),
            )
        except (KeyError, TypeError):
            raise CorpusError("INVALID_RECORD", "payload is missing a key this record needs") from None
        if not HEX64.fullmatch(record.document_sha256) or type(record.document_length) is not int:
            raise CorpusError("INVALID_RECORD", "document_sha256 must be a SHA-256 hex digest")
        if record.state != data.get("state"):
            raise CorpusError("INVALID_RECORD", "state does not follow from known_at")
        if record.known_at is None:
            _nonblank(record.unknown_reason, "unknown_reason", "INVALID_RECORD")
            if record.availability_basis is not None:
                raise CorpusError("INVALID_RECORD", "an unknown first availability carries no basis")
        elif record.availability_basis is None or record.unknown_reason is not None:
            raise CorpusError("INVALID_RECORD",
                              "a known first availability carries a basis and no unknown reason")
        return record


def normalize_locator(locator):
    """The canonical form of a URL or path, so one resource has one source id.

    An HTTP(S) URL is lower-cased in scheme and host, loses a default port and its
    fragment, and is refused when it carries credentials, which are never recorded; its
    path and query are kept exactly. Anything else is read as a path with ``/`` separators.
    """
    if type(locator) is not str or not locator.strip():
        raise CorpusError("INVALID_METADATA", "locator must be a non-blank string")
    value = locator.strip()
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme in ("http", "https"):
        if parsed.username or parsed.password:
            raise CorpusError("CREDENTIALED_LOCATOR", "a locator carrying credentials is never recorded")
        if not parsed.hostname:
            raise CorpusError("INVALID_METADATA", "URL has no host: %r" % value)
        try:
            port = parsed.port
        except ValueError:
            raise CorpusError("INVALID_METADATA", "URL port is not a number: %r" % value) from None
        default = 80 if scheme == "http" else 443
        netloc = parsed.hostname.lower() + (":%d" % port if port and port != default else "")
        return urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))
    if scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            raise CorpusError("UNSUPPORTED_SCHEME",
                              "a file URL naming another host is not read here: %r" % value)
        return posixpath.normpath(parsed.path.replace("\\", "/"))
    if scheme and "://" in value:
        raise CorpusError("UNSUPPORTED_SCHEME",
                          "only http, https and file locators are read here: %r" % value)
    return posixpath.normpath(value.replace("\\", "/"))


def source_id_for(locator):
    """One normalized locator, one source id; derived from the locator and nothing else."""
    return "corpus:" + hashlib.sha256(normalize_locator(locator).encode("utf-8")).hexdigest()[:16]


def extension_for(content_type):
    """The filename suffix for a content type; ``bin`` when the type has no known one."""
    return EXTENSIONS.get(content_type, "bin")


def _evidence(metadata, locator):
    """The first-availability evidence for this acquisition, or ``None`` when there is none.

    Explicit evidence is used as given. A fetch time on its own is capture evidence only
    when the register asks for that kind (or names no rule yet), because the register's
    rule is the family's own statement of how first availability is known.
    """
    if metadata.availability is not None:
        return metadata.availability
    if metadata.capture_time is not None and metadata.first_availability_rule in (None, "capture_logged_at"):
        return Availability("capture_logged_at", "corpus fetch log: %s" % locator,
                            metadata.capture_time, "the fetch time of this workflow")
    return None


def _unknown_reason(publication):
    if publication.unknown_value:
        return ("publication_unknown: %s; a version with no publication instant cannot be "
                "placed in known-then context" % publication.unknown_reason)
    return ("availability_unknown: no first-availability evidence was supplied for this "
            "version, so it is excluded from every compiled context")


def _build(content, metadata, *, source_id, source_version, recorded_at):
    """One candidate record; the caller decides whether it is new, known or refused."""
    digest = hashlib.sha256(content).hexdigest()
    content_type = metadata.content_type or sniff_content_type(content)
    type_source = "supplied" if metadata.content_type else "sniffed"
    locator = normalize_locator(metadata.locator)
    evidence = _evidence(metadata, locator)
    rule = metadata.first_availability_rule
    if evidence is not None:
        if rule is not None and rule != evidence.basis_kind:
            raise CorpusError("RULE_EVIDENCE_MISMATCH",
                              "the register's rule %r is not the evidence kind %r supplied"
                              % (rule, evidence.basis_kind))
        rule = rule or evidence.basis_kind
    # A version with no stated publication instant has no first availability either: the
    # capture would place the *bytes*, not the revision, and a cutoff asks about the
    # revision. This is the exclusion the acceptance check names.
    known_at = None
    if not metadata.publication.unknown_value and evidence is not None:
        known_at = evidence.at
        if metadata.publication.precision != "date" and _earlier(known_at, metadata.publication.value):
            raise CorpusError("AVAILABILITY_BEFORE_PUBLICATION",
                              "first availability %s precedes the stated publication %s"
                              % (known_at, metadata.publication.value))
    return SourceVersion(
        source_id=source_id, source_version=source_version, lineage_id=source_id,
        issuer=metadata.issuer.strip(), locator=locator,
        content_type=content_type, content_type_source=type_source,
        document_length=len(content), document_sha256=digest,
        licence_ref=metadata.licence_ref.strip(),
        access_policy_ref=(metadata.access_policy_ref or metadata.licence_ref).strip(),
        publication=metadata.publication, recorded_at=_instant(recorded_at, "recorded_at"),
        first_availability_rule=rule, known_at=known_at,
        availability_basis=None if known_at is None else evidence.basis(),
        unknown_reason=None if known_at is not None else _unknown_reason(metadata.publication),
        capture_time=metadata.capture_time,
        synthetic=metadata.synthetic, permission_ref=metadata.permission_ref)


def agreement(record, candidate):
    """The stated facts on which a re-observation contradicts a recorded version.

    Two exemptions, and nothing else: a fact the record declared *unknown* may be filled
    in later (a publication the register states, a rule that arrives with the evidence),
    because filling a declared unknown contradicts nothing. Everything else is compared
    exactly. Availability is compared by its instant: a later observation of the same
    bytes is not a contradiction — the recorded first availability stands and the new
    capture belongs to the fetch log — while an earlier one on a compilable record would
    move a stated first availability and is refused here, where the record is immutable.
    """
    prior, other = record.payload(), candidate.payload()
    problems = []
    for key in STATED_FACTS:
        if prior[key] == other[key]:
            continue
        if key == "first_availability_rule" and prior[key] is None:
            continue
        if key == "publication" and prior[key]["value"] is None:
            # The same declared unknown, described afresh, or a publication the caller can
            # now state. A stated publication may never change or be withdrawn.
            continue
        problems.append(key)
    if record.known_at == candidate.known_at or record.known_at is None:
        return problems
    if candidate.known_at is None or _earlier(candidate.known_at, record.known_at):
        problems.append("known_at")
    return problems


def acquire(content, metadata, *, recorded_at, prior=()):
    """One document version from exact bytes and supplied metadata.

    ``prior`` is every record already held for the same source id — the caller reads them
    from the acquisition payloads it stored. When the bytes are already recorded, the
    recorded version is returned unchanged, with one exception and one refusal: an
    excluded record that now carries the facts it had declared unknown is returned
    repaired, because an excluded version was never projected into the review core and
    nothing downstream can depend on it; and supplied metadata that contradicts a stated
    fact is refused as ``VERSION_CONFLICT``, because a version's stated facts are what a
    reviewed correction has to change, not a re-acquisition. Nothing is inferred: no date
    is read out of the content, and a missing publication or a missing availability
    instant is recorded as an unknown with its reason, never filled in.
    """
    if type(content) is not bytes:
        raise CorpusError("INVALID_CONTENT", "content must be bytes")
    if not content:
        raise CorpusError("EMPTY_CONTENT", "a zero-byte response is not a document version")
    if not isinstance(metadata, SuppliedMetadata):
        raise CorpusError("INVALID_METADATA", "expected SuppliedMetadata")
    locator = normalize_locator(metadata.locator)
    source_id = source_id_for(locator)
    digest = hashlib.sha256(content).hexdigest()
    known = [item if isinstance(item, SourceVersion) else SourceVersion.from_payload(item)
             for item in prior]
    for item in known:
        if item.source_id == source_id and item.document_sha256 == digest:
            candidate = _build(content, metadata, source_id=source_id,
                               source_version=item.source_version, recorded_at=recorded_at)
            problems = agreement(item, candidate)
            if problems:
                raise CorpusError("VERSION_CONFLICT",
                                  "%s %s is already recorded and the supplied metadata changes %s"
                                  % (source_id, item.source_version, ", ".join(problems)))
            if item.payload() == candidate.payload():
                return item
            if item.state == "excluded" and candidate.state == "compilable":
                return candidate
            return item
    versions = [int(item.source_version) for item in known
                if item.source_id == source_id and item.source_version.isdigit()]
    return _build(content, metadata, source_id=source_id,
                  source_version=str(max(versions, default=0) + 1), recorded_at=recorded_at)


def source_record(record, layer, tenant_id, case_id, recorded_at, *, permissions=None):
    """Project one compilable version into the review core's ``h0.v2`` SourceVersion.

    The review core stores text sources, so ``original_text`` is the version's text layer
    and ``source_byte_digest`` fingerprints *that text*. The document's own fingerprint,
    length, type, locator and licence travel in the additive keys this module adds, which
    the h0 validator does not know and the compiler never reads. An excluded version has
    no projection: this raises, so no passage and no compiled context can name it.
    """
    if not isinstance(record, SourceVersion):
        raise CorpusError("INVALID_RECORD", "expected a SourceVersion record")
    if record.state != "compilable":
        raise CorpusError("SOURCE_EXCLUDED", "%s %s is excluded from compiled contexts: %s"
                          % (record.source_id, record.source_version, record.unknown_reason))
    text = getattr(layer, "text", None)
    if type(text) is not str or not text:
        raise CorpusError("EMPTY_TEXT_LAYER", "a compilable version needs a text layer with text")
    if getattr(layer, "sha256", None) != record.document_sha256:
        raise CorpusError("LAYER_MISMATCH", "the text layer was extracted from other bytes")
    payload = {
        "source_id": record.source_id, "source_version": record.source_version,
        "lineage_id": record.lineage_id, "publisher": record.issuer,
        "access_policy_ref": record.access_policy_ref,
        "original_text": text,
        "source_byte_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "published_at": record.publication.value,
        "known_at": record.known_at, "availability_basis": record.availability_basis,
        "unknown_reason": None, "copied_from": None,
        "synthetic": record.synthetic, "permission_ref": record.permission_ref,
        # Additive acquisition facts; the h0 rules ignore them and the compiler never reads them.
        "document_sha256": record.document_sha256, "document_length": record.document_length,
        "content_type": record.content_type, "locator": record.locator,
        "licence_ref": record.licence_ref, "first_availability_rule": record.first_availability_rule,
        "text_layer": {"method": getattr(layer, "method", None),
                       "method_version": getattr(layer, "method_version", None),
                       "page_count": getattr(layer, "page_count", None),
                       "charset": getattr(layer, "charset", None)},
    }
    return make_record("SourceVersion", tenant_id, case_id, record.source_id,
                       record.source_version, recorded_at, payload, permissions=permissions)


def passage_record(source, layer, locator, record_id, recorded_at, *, permissions=None):
    """One page locator of a text layer as a review-core ``Passage`` of its source.

    ``locator`` is what :meth:`src.adapters.corpus.text.TextLayer.locator` returns: a page
    number, page-relative offsets, layer-wide offsets, the exact quote and its digest. The
    locator is re-checked against the layer in every part — page offsets, layer offsets,
    quote, digest — and the layer must be the one extracted from the source version's own
    bytes and text, so a passage is refused rather than recorded when any part of it cites
    anything else. The review core re-checks the passage against the source's registered
    text, so a record this function emits is one the core can register.
    """
    if type(source) is not dict or source.get("record_kind") != "SourceVersion":
        raise CorpusError("INVALID_RECORD", "expected a SourceVersion record")
    if compute_content_digest({key: value for key, value in source.items() if key != "content_digest"}) \
            != source.get("content_digest"):
        raise CorpusError("INVALID_RECORD", "the source record's content digest does not match its payload")
    validate_locator(layer, locator, locator.get("quote"))
    if layer.sha256 != source["payload"].get("document_sha256"):
        raise CorpusError("LAYER_MISMATCH",
                          "the text layer was extracted from other bytes than this source version")
    if hashlib.sha256(layer.text.encode("utf-8")).hexdigest() != source["payload"].get("source_byte_digest"):
        raise CorpusError("LAYER_MISMATCH",
                          "the text layer's text is not this source version's original_text")
    payload = {
        "source_ref": reference(source),
        "source_id": source["payload"]["source_id"],
        "source_version": source["payload"]["source_version"],
        "source_byte_digest": source["payload"]["source_byte_digest"],
        "start": locator["start"], "end": locator["end"],
        "quote": locator["quote"], "quote_digest": locator["quote_digest"],
        # Parser metadata: the page and the page-relative offsets the passage came from.
        "page": locator["page"], "page_start": locator["page_start"], "page_end": locator["page_end"],
        "synthetic": source["payload"]["synthetic"],
        "permission_ref": source["payload"]["permission_ref"],
    }
    return make_record("Passage", source["tenant_id"], source["case_id"], record_id, "1",
                       recorded_at, payload, permissions=permissions)
