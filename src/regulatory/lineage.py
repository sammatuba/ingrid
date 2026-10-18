"""Amendment lineage: the clause text in force at a cutoff, reached by supplied records.

A baseline document parsed by a family grammar yields one ``RuleVersion`` per
clause span.  An amending document plus supplied metadata — its effective date,
its first availability and the clauses it names, each with an exact locator into
the amending document and the ``version_id`` of the version it replaces — yields
one new ``RuleVersion`` per named clause, linked to the version the record says
it replaces.  ``RuleRegister.in_force(clause_label, cutoff)`` returns the
version that both dates place at the cutoff, with its chain and the versions
excluded from the answer.

No word in any document is read as authority.  The register never parses "is
hereby amended", never infers that an amendment changed a clause it does not
name, never turns an effectivity phrase into a date, and never treats the order
in which versions were registered as precedence: every change must name the
version it replaces, and that version must be the one the register holds as the
head of the clause's chain.  A change that names any other version, or none at
all, is refused as conflicting or unresolved rather than guessed at, and a
chain returned for a cutoff never points at a version the cutoff excluded.

Dates are the R0 ``DateMetadata``: a value of ``YYYY``, ``YYYY-MM`` or
``YYYY-MM-DD`` with the matching precision, or an explicit unknown reason.  A
coarse value denotes its whole period, ending on the real calendar last day of
that period.  A version is in force at a cutoff only
when the register can place both its first availability — what was known by the
cutoff — and its supplied effectivity — what had legal effect by the cutoff —
and every version it replaces was in force there too.  A version whose dates
are unknown, or coarser than the cutoff and overlapping it, is excluded with
that reason rather than assumed into force.  Resubmitting an amendment is
idempotent only when every supplied field is identical; a changed record is
refused as a corrected record that needs its own reference.
"""
from dataclasses import dataclass
import calendar
import datetime
import hashlib
import re

from .grammars import FAMILIES, parse
from .structure import DateMetadata, Locator, Source, StructureError, validate_locator

__all__ = ['ADMITTED', 'AFTER_CUTOFF', 'ANCESTOR_NOT_IN_FORCE', 'AVAILABILITY_IMPRECISE',
           'AVAILABILITY_UNKNOWN', 'Amendment', 'AmendmentChange', 'ClauseInForce',
           'EFFECTIVITY_IMPRECISE', 'EFFECTIVITY_UNKNOWN', 'EXCLUSION_REASONS', 'Exclusion',
           'NOT_YET_EFFECTIVE', 'RuleRegister', 'RuleVersion']

_VALUE = re.compile(r'(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?\Z')
_PRECISION_OF = {1: 'year', 2: 'month', 3: 'day'}

ADMITTED = 'admitted'
AVAILABILITY_UNKNOWN = 'availability_unknown'
AFTER_CUTOFF = 'after_cutoff'
AVAILABILITY_IMPRECISE = 'availability_imprecise'
EFFECTIVITY_UNKNOWN = 'effectivity_unknown'
NOT_YET_EFFECTIVE = 'not_yet_effective'
EFFECTIVITY_IMPRECISE = 'effectivity_imprecise'
ANCESTOR_NOT_IN_FORCE = 'ancestor_not_in_force'

EXCLUSION_REASONS = (AVAILABILITY_UNKNOWN, AFTER_CUTOFF, AVAILABILITY_IMPRECISE,
                     EFFECTIVITY_UNKNOWN, NOT_YET_EFFECTIVE, EFFECTIVITY_IMPRECISE,
                     ANCESTOR_NOT_IN_FORCE)


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise StructureError(f'{name} must be a nonempty string')


def _span_of(metadata, name) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    """(start, end) civil-date keys of a supplied DateMetadata; None if unknown."""
    if not isinstance(metadata, DateMetadata):
        raise StructureError(f'{name} must be DateMetadata')
    if metadata.value is None:
        return None
    match = _VALUE.fullmatch(metadata.value)
    if not match:
        raise StructureError(
            f'{name} value {metadata.value!r} is not an ISO year, month or day')
    parts = [int(part) for part in match.groups() if part]
    if metadata.precision != _PRECISION_OF[len(parts)]:
        raise StructureError(
            f'{name} precision {metadata.precision!r} does not match value {metadata.value!r}')
    if len(parts) == 2 and not 1 <= parts[1] <= 12:
        raise StructureError(f'{name} value {metadata.value!r} has no such month')
    if len(parts) == 3:
        try:
            datetime.date(*parts)
        except ValueError as exc:
            raise StructureError(f'{name} value {metadata.value!r} is not a date') from exc
    start = tuple((parts + [1, 1])[:3])
    if len(parts) == 1:
        end = (parts[0], 12, 31)
    elif len(parts) == 2:
        # The real calendar last day of the month: a month-precision value ends
        # on the 28th, 29th, 30th or 31st its own year gives it, never a guess.
        end = (parts[0], parts[1], calendar.monthrange(parts[0], parts[1])[1])
    else:
        end = tuple(parts)
    return start, end


def _version_id(locator, clause_label, amendment_ref):
    payload = '\x1f'.join((clause_label, amendment_ref or '', locator.digest,
                           str(locator.start), str(locator.end)))
    return 'rv-' + hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


@dataclass(frozen=True)
class RuleVersion:
    """One version of one clause, anchored to an exact quotation of its source."""
    version_id: str
    clause_label: str
    text: str
    locator: Locator
    replaces: str | None
    amendment_ref: str | None
    effective: DateMetadata
    first_availability: DateMetadata

    def __post_init__(self):
        _identity(self.version_id, 'version_id')
        _identity(self.clause_label, 'clause_label')
        _identity(self.text, 'text')
        if not isinstance(self.locator, Locator):
            raise StructureError('locator must be a Locator')
        for value, name in ((self.replaces, 'replaces'), (self.amendment_ref, 'amendment_ref')):
            if value is not None:
                _identity(value, name)
        if self.replaces == self.version_id:
            raise StructureError('a version cannot replace itself')
        _span_of(self.effective, 'effective')
        _span_of(self.first_availability, 'first_availability')


@dataclass(frozen=True)
class AmendmentChange:
    """One clause an amending record names, with the text it substitutes.

    ``replaces`` is the supplied ``version_id`` of the version this change
    supersedes; it is required unless the change records a clause the register
    does not hold yet (``adds_clause``).  It is metadata a reviewer supplied,
    never a guess from the order amendments arrive in.
    """
    clause_label: str
    locator: Locator
    quoted_text: str
    replaces: str | None = None
    adds_clause: bool = False

    def __post_init__(self):
        _identity(self.clause_label, 'clause label')
        if not isinstance(self.locator, Locator):
            raise StructureError('change locator must be a Locator')
        _identity(self.quoted_text, 'quoted text')
        if type(self.adds_clause) is not bool:
            raise StructureError('adds_clause must be a boolean')
        if self.replaces is not None:
            _identity(self.replaces, 'replaces')
        if self.adds_clause and self.replaces is not None:
            raise StructureError(
                'a new clause cannot replace a version; drop replaces or adds_clause')
        if not self.adds_clause and self.replaces is None:
            raise StructureError(
                f'change for clause {self.clause_label!r} names no version it '
                f'replaces; supply replaces, or adds_clause for a new clause')


@dataclass(frozen=True)
class Amendment:
    """An amending document with the metadata a reviewer supplied for it.

    ``changes`` names the clauses it revises; each change carries the exact
    quotation and the ``version_id`` it replaces, so the lineage is a record,
    not a reading of the amending text.
    """
    source: Source
    amendment_ref: str
    effective: DateMetadata
    first_availability: DateMetadata
    changes: tuple[AmendmentChange, ...]

    def __post_init__(self):
        if not isinstance(self.source, Source):
            raise StructureError('amendment source must be a Source')
        _identity(self.amendment_ref, 'amendment_ref')
        _span_of(self.effective, 'effective')
        _span_of(self.first_availability, 'first_availability')
        if not isinstance(self.changes, tuple) or not self.changes:
            raise StructureError('an amendment must name at least one clause')
        labels = set()
        for change in self.changes:
            if not isinstance(change, AmendmentChange):
                raise StructureError('changes must be AmendmentChange records')
            if change.clause_label in labels:
                raise StructureError(
                    f'amendment {self.amendment_ref!r} names clause '
                    f'{change.clause_label!r} more than once')
            labels.add(change.clause_label)
            # The substituted text is exactly the thing at those offsets.
            validate_locator(self.source, change.locator, change.quoted_text)


@dataclass(frozen=True)
class Exclusion:
    """A version the cutoff query did not admit, and why."""
    version: RuleVersion
    reason: str


@dataclass(frozen=True)
class ClauseInForce:
    """The clause version admitted at a cutoff, its chain, and what was excluded."""
    clause_label: str
    cutoff: DateMetadata
    version: RuleVersion | None
    chain: tuple[RuleVersion, ...]
    excluded: tuple[Exclusion, ...]

    def __post_init__(self):
        _identity(self.clause_label, 'clause_label')
        _span_of(self.cutoff, 'cutoff')
        if self.version is not None and (not self.chain or self.chain[-1] is not self.version):
            raise StructureError('the chain must end at the version in force')
        if self.version is None and self.chain:
            raise StructureError('a chain requires a version in force')
        for item in self.excluded:
            if item.reason not in EXCLUSION_REASONS:
                raise StructureError(f'unknown exclusion reason {item.reason!r}')
        # The chain is auditable: every link is the supplied replacement of the
        # version before it, and it begins where the lineage begins.
        if self.chain and self.chain[0].replaces is not None:
            raise StructureError('a chain begins at a version that replaces nothing')
        for earlier, later in zip(self.chain, self.chain[1:]):
            if later.replaces != earlier.version_id:
                raise StructureError(
                    'each chain version must replace the version before it')


_UNKNOWN = 'unknown'
_AFTER = 'after'
_IMPRECISE = 'imprecise'


def _placement(metadata: DateMetadata, cutoff_span, name: str) -> str:
    """Where one supplied date places a version against a cutoff period.

    A coarse value denotes its whole period: it is admitted only once the whole
    period has elapsed by the cutoff, and reported as imprecise before that.
    """
    span = _span_of(metadata, name)
    if span is None:
        return _UNKNOWN
    if span[1] <= cutoff_span[1]:
        return ADMITTED
    if span[0] > cutoff_span[1]:
        return _AFTER
    return _IMPRECISE


_AVAILABILITY_REASON = {_UNKNOWN: AVAILABILITY_UNKNOWN, _AFTER: AFTER_CUTOFF,
                        _IMPRECISE: AVAILABILITY_IMPRECISE}
_EFFECTIVITY_REASON = {_UNKNOWN: EFFECTIVITY_UNKNOWN, _AFTER: NOT_YET_EFFECTIVE,
                       _IMPRECISE: EFFECTIVITY_IMPRECISE}


def _exclusion_reason(version: 'RuleVersion', cutoff_span) -> str | None:
    """Why a version is not in force at a cutoff; None when both dates place it.

    Both supplied dates constrain the answer: first availability says what the
    register could know at the cutoff, effectivity says what had legal effect.
    """
    placement = _placement(version.first_availability, cutoff_span, 'first_availability')
    if placement != ADMITTED:
        return _AVAILABILITY_REASON[placement]
    placement = _placement(version.effective, cutoff_span, 'effective')
    if placement != ADMITTED:
        return _EFFECTIVITY_REASON[placement]
    return None


def _require_replacement(change: 'AmendmentChange', expected: str | None,
                         amendment: 'Amendment') -> None:
    """Refuse a change whose supplied replacement is not the version it must name."""
    if change.replaces == expected:
        return
    if expected is None:
        raise StructureError(
            f'amendment {amendment.amendment_ref!r} supplies replaces '
            f'{change.replaces!r} for clause {change.clause_label!r}, which is '
            f'recorded as a new clause that replaces nothing')
    raise StructureError(
        f'amendment {amendment.amendment_ref!r} supplies replaces '
        f'{change.replaces!r} for clause {change.clause_label!r}, but the register '
        f'holds {expected!r} as the version that change supersedes; the replacement '
        f'relationship is a supplied record, never the order amendments arrive in')


def _check_replacement_available(amendment: 'Amendment', clause_label: str,
                                 replaced: 'RuleVersion') -> None:
    """Refuse a replacement whose supplied availability predates the replaced one."""
    new = _span_of(amendment.first_availability, 'first_availability')
    old = _span_of(replaced.first_availability, 'first_availability')
    if new is None or old is None or new[1] >= old[0]:
        return
    raise StructureError(
        f'amendment {amendment.amendment_ref!r} is supplied as first available '
        f'{amendment.first_availability.value!r} but names clause {clause_label!r} '
        f'version {replaced.version_id!r} first available '
        f'{replaced.first_availability.value!r}; a document cannot replace one '
        f'that was not yet available')


def _described(value) -> str:
    """A supplied value written the way the record holds it."""
    if isinstance(value, DateMetadata):
        return (f'unknown ({value.unknown_reason!r})' if value.value is None
                else repr(value.value))
    return repr(value)


def _require_identical_resubmission(version: 'RuleVersion', change: 'AmendmentChange',
                                    amendment: 'Amendment') -> None:
    """Refuse a resubmission whose supplied record differs from the stored version.

    Repeating an amendment is idempotent only when every supplied field matches the
    version already registered: the same quote, the same version it replaces (which
    ``_require_replacement`` has just checked) and the same two supplied dates.  A
    changed field is a corrected record, not a repetition, and it is refused rather
    than silently resolved to the version already stored.
    """
    for supplied, stored, name in (
            (change.quoted_text, version.text, 'quoted text'),
            (amendment.effective, version.effective, 'effective date'),
            (amendment.first_availability, version.first_availability, 'first availability')):
        if supplied != stored:
            raise StructureError(
                f'amendment {amendment.amendment_ref!r} is already registered for clause '
                f'{change.clause_label!r} with {name} {_described(stored)}, but this '
                f'resubmission supplies {_described(supplied)}; repeating a record must '
                f'repeat all of it, and a correction needs a new amendment_ref')


class RuleRegister:
    """An append-only register of clause versions for one document family.

    Every chain is built from supplied replacement records: a change names the
    version it supersedes, and the register refuses a change that names any
    version other than the head of that clause's chain.  Nothing is reordered,
    inferred or deleted, and registration order is never precedence.
    """

    def __init__(self, family: str):
        if family not in FAMILIES:
            raise StructureError(
                f'unknown family {family!r}; expected one of {", ".join(FAMILIES)}')
        self.family = family
        self._chains: dict[str, list[RuleVersion]] = {}

    def labels(self) -> tuple[str, ...]:
        return tuple(self._chains)

    def versions(self, clause_label: str) -> tuple[RuleVersion, ...]:
        return tuple(self._chains.get(clause_label, ()))

    def add_baseline(self, source: Source, first_availability: DateMetadata, *,
                     effective: DateMetadata | None = None, kinds=('clause',),
                     exclude_toc: bool = True) -> tuple[RuleVersion, ...]:
        """Register one version per clause span of a baseline document.

        ``kinds`` selects which span kinds are clauses for this register.  A
        span that carries a ``toc_entry`` diagnostic is a contents-list line
        referring to a heading, not the provision itself, and is skipped while
        ``exclude_toc`` is true.  Two spans for one label in the same document
        are refused, and so is a label the register already holds: a register
        needs one text per label, and one lineage per clause.
        """
        if not isinstance(source, Source):
            raise StructureError('baseline must be a Source')
        _span_of(first_availability, 'first_availability')
        if effective is None:
            effective = source.effectivity or DateMetadata(
                None, None, 'no effectivity metadata was supplied with the source')
        _span_of(effective, 'effective')
        if isinstance(kinds, str):
            raise StructureError('kinds must be a sequence of span kinds')
        structure = parse(source, self.family)
        selected = []
        seen = set()
        for span in structure.spans:
            if span.kind not in kinds:
                continue
            if exclude_toc and any(d.code == 'toc_entry' for d in span.diagnostics):
                continue
            if span.label is None:
                raise StructureError(f'a {span.kind} span carries no label')
            if span.label in seen:
                raise StructureError(
                    f'baseline holds more than one {span.kind} labelled '
                    f'{span.label!r}; the register needs one text per label')
            seen.add(span.label)
            selected.append(span)
        if not selected:
            raise StructureError(
                f'baseline {source.source_id!r} holds no clause span of kinds {tuple(kinds)}')
        versions = tuple(
            RuleVersion(_version_id(span.locator, span.label, None), span.label,
                        span.quoted_text, span.locator, None, None,
                        effective, first_availability)
            for span in selected)
        held = tuple(version.clause_label for version in versions
                     if version.clause_label in self._chains)
        if held:
            # A second baseline would branch the lineage: the register refuses it
            # rather than keeping two versions that replace nothing.
            raise StructureError(
                f'the register already holds clause {held[0]!r}; a second baseline '
                f'cannot enter one lineage, supply the replacement record instead')
        for version in versions:
            self._chains.setdefault(version.clause_label, []).append(version)
        return versions

    def apply(self, amendment: Amendment) -> tuple[RuleVersion, ...]:
        """Append one new version per clause the amendment names.

        Each change supplies the ``version_id`` it replaces, and that version
        must be the head of the clause's chain: a change naming an older version
        would branch the lineage and is refused as conflicting, one naming a
        version the register does not hold as unresolved.  A supplied first
        availability that ends before the replaced version became available is
        contradictory and is refused too.  Repeating an amendment already
        registered is idempotent only when every supplied field — the quote, the
        replaced version and both dates — is identical; a resubmission that
        changes any of them is refused as a corrected record that needs its own
        ``amendment_ref``.
        """
        if not isinstance(amendment, Amendment):
            raise StructureError('expected an Amendment')
        prepared = []
        for change in amendment.changes:
            chain = self._chains.get(change.clause_label)
            if chain is None and not change.adds_clause:
                raise StructureError(
                    f'amendment {amendment.amendment_ref!r} names clause '
                    f'{change.clause_label!r}, which the register does not hold; '
                    f'supply adds_clause to record it as a new clause')
            if chain is not None and change.adds_clause:
                raise StructureError(
                    f'amendment {amendment.amendment_ref!r} marks clause '
                    f'{change.clause_label!r} as new, but the register already holds it')
            identity = _version_id(change.locator, change.clause_label, amendment.amendment_ref)
            replacement = None
            if chain:
                head = chain[-1]
                if head.version_id == identity:
                    # Identical registration is idempotent only when every supplied
                    # field is identical too: same quote, same replaced version and
                    # the same two supplied dates.  A changed record is refused, never
                    # silently resolved to the version already stored.
                    _require_replacement(
                        change, chain[-2].version_id if len(chain) > 1 else None, amendment)
                    _require_identical_resubmission(head, change, amendment)
                    prepared.append(head)
                    continue
                if any(version.version_id == identity for version in chain):
                    raise StructureError(
                        f'amendment {amendment.amendment_ref!r} repeats an earlier '
                        f'revision of clause {change.clause_label!r}; the register '
                        f'never resurrects a superseded revision')
                _require_replacement(change, head.version_id, amendment)
                _check_replacement_available(amendment, change.clause_label, head)
                replacement = head.version_id
            prepared.append(RuleVersion(
                identity, change.clause_label, change.quoted_text, change.locator,
                replacement, amendment.amendment_ref, amendment.effective,
                amendment.first_availability))
        for version in prepared:
            chain = self._chains.setdefault(version.clause_label, [])
            if not chain or chain[-1] is not version:
                chain.append(version)
        return tuple(prepared)

    def in_force(self, clause_label: str, cutoff: DateMetadata) -> ClauseInForce:
        """The clause version in force at a known cutoff, with its chain.

        A version is in force only when both supplied dates place it at the
        cutoff and every version it replaces is in force there too, so the chain
        returned ends at the version in force and never points at an excluded
        version.  A version after the first one the cutoff cannot place is
        reported as ``ancestor_not_in_force``; every exclusion carries the
        reason, never a guess.
        """
        chain = self._chains.get(clause_label)
        if chain is None:
            raise StructureError(f'the register holds no clause labelled {clause_label!r}')
        cutoff_span = _span_of(cutoff, 'cutoff')
        if cutoff_span is None:
            raise StructureError('the cutoff must be a known date')
        admitted = []
        excluded = []
        for version in chain:
            reason = _exclusion_reason(version, cutoff_span)
            if reason is None and excluded:
                reason = ANCESTOR_NOT_IN_FORCE
            if reason is None:
                admitted.append(version)
            else:
                excluded.append(Exclusion(version, reason))
        # The chains are linear by construction, so the versions in force are the
        # prefix the cutoff places; the rest are excluded, nearest first.
        return ClauseInForce(clause_label, cutoff,
                             admitted[-1] if admitted else None,
                             tuple(admitted), tuple(reversed(excluded)))
