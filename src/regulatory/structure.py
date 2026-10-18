"""Immutable internal records. Offsets count Unicode characters, never bytes.

Only LF and CRLF delimit heading lines. Unsupported heading diagnostics are a
bounded heuristic for lines beginning with Section/Annex (case insensitive,
possibly indented); they do not claim to detect every regulatory heading.
"""
from dataclasses import dataclass
import hashlib
import re

PARSER_REVISION = 'r0-native-text-v1'
_HEADING = re.compile(r'(?:(Section|SECTION) ([1-9][0-9]*)|Annex ([A-Z]))\. ([^\r\n]+)')
_CANDIDATE = re.compile(r'^\s*(?:section|annex)\b', re.IGNORECASE)


class StructureError(ValueError):
    """Invalid source, metadata or exact locator."""


def _identity(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StructureError(f'{name} must be a nonempty string')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise StructureError(f'{name} must be valid Unicode') from exc


@dataclass(frozen=True)
class DateMetadata:
    """Supplied date value/precision, or explicit unknown reason; no inference."""
    value: str | None
    precision: str | None
    unknown_reason: str | None

    def __post_init__(self):
        if self.value is None:
            if self.precision is not None:
                raise StructureError('unknown date cannot have precision')
            _identity(self.unknown_reason, 'unknown_reason')
        else:
            _identity(self.value, 'date value')
            _identity(self.precision, 'date precision')
            if self.unknown_reason is not None:
                raise StructureError('known date cannot have unknown_reason')


@dataclass(frozen=True)
class Source:
    source_id: str
    source_revision: str
    digest: str
    original_bytes: bytes
    publication: DateMetadata | None = None
    effectivity: DateMetadata | None = None

    def __post_init__(self):
        _identity(self.source_id, 'source_id')
        _identity(self.source_revision, 'source_revision')
        if not isinstance(self.original_bytes, bytes) or not self.original_bytes:
            raise StructureError('source must contain nonempty original bytes')
        if self.digest != hashlib.sha256(self.original_bytes).hexdigest():
            raise StructureError('source SHA-256 digest mismatch (expected lowercase hex)')
        try:
            self.original_bytes.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise StructureError('source must be strict UTF-8') from exc
        for metadata in (self.publication, self.effectivity):
            if metadata is not None and not isinstance(metadata, DateMetadata):
                raise StructureError('dates must be DateMetadata or absent')

    @property
    def text(self) -> str:
        return self.original_bytes.decode('utf-8')


@dataclass(frozen=True)
class Locator:
    source_id: str
    source_revision: str
    digest: str
    start: int
    end: int


@dataclass(frozen=True)
class Diagnostic:
    code: str
    start: int
    end: int


@dataclass(frozen=True)
class Span:
    kind: str
    label: str | None
    title: str | None
    locator: Locator
    quoted_text: str
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class DocumentStructure:
    source: Source
    parser_revision: str
    spans: tuple[Span, ...]


def validate_locator(source: Source, locator: Locator, quoted_text: str) -> None:
    """Reject mismatched source identity, bounds or quotation explicitly."""
    if not isinstance(source, Source) or not isinstance(locator, Locator):
        raise StructureError('expected Source and Locator')
    if (locator.source_id, locator.source_revision, locator.digest) != (
        source.source_id, source.source_revision, source.digest
    ):
        raise StructureError('locator source mismatch')
    if (type(locator.start) is not int or type(locator.end) is not int
            or not 0 <= locator.start < locator.end <= len(source.text)):
        raise StructureError('invalid half-open character offsets')
    if source.text[locator.start:locator.end] != quoted_text:
        raise StructureError('locator quotation mismatch')


def parse(source: Source) -> DocumentStructure:
    """Return a new extraction without modifying evidence or previous results."""
    if not isinstance(source, Source):
        raise StructureError('expected Source')
    text = source.text
    headings = []
    diagnostics = []
    seen = set()
    offset = 0
    # split on LF explicitly: splitlines would treat Unicode separators as lines.
    for line in text.split('\n'):
        body = line[:-1] if line.endswith('\r') and offset + len(line) < len(text) else line
        match = _HEADING.fullmatch(body)
        if match and match.group(4).strip():
            section, number, annex, title = match.groups()
            kind = 'section' if section else 'annex'
            label = f'Section {number}' if section else f'Annex {annex}'
            headings.append((offset, kind, label, title))
            if label in seen:
                diagnostics.append(Diagnostic('duplicate_label', offset, offset + len(body)))
            seen.add(label)
        elif _CANDIDATE.match(body):
            diagnostics.append(Diagnostic('unrecognized_heading', offset, offset + len(body)))
        offset += len(line) + 1
    if not headings:
        boundaries = [(0, 'unclassified', None, None)]
        diagnostics.append(Diagnostic('no_recognized_heading', 0, len(text)))
    else:
        boundaries = headings
        if headings[0][0] > 0:
            boundaries = [(0, 'preamble', None, None)] + headings
    spans = []
    for index, (start, kind, label, title) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(text)
        locator = Locator(source.source_id, source.source_revision, source.digest, start, end)
        quote = text[start:end]
        validate_locator(source, locator, quote)
        spans.append(Span(kind, label, title, locator, quote,
                          tuple(d for d in diagnostics if start <= d.start < end)))
    return DocumentStructure(source, PARSER_REVISION, tuple(spans))
