"""Family grammars over the R0 parser contract; ``structure.py`` is unchanged.

``parse(source, family)`` returns the same ordered ``DocumentStructure`` the R0
starter returns, using one heading grammar per document family: the WESM Rules,
the market manuals, ERC resolutions and DOE circulars.  A grammar recognises a
line by its shape only.  It decides nothing about effectivity, applicability,
precedence or approval, it invents no page number and no date, and a heading-like
line it does not know stays content with an ``unrecognized_heading`` diagnostic.

Line handling follows ``structure.py``: only LF and CRLF delimit lines, offsets
count Unicode characters of the decoded original text, and the spans tile the
text without gaps or overlaps.

Recognised shapes (the evidence on the real documents is recorded in
``docs/work/corpus/structure.md``):

wesm_rules
    ``CHAPTER <n>`` alone on a line (the chapter title is the next non-blank
    line when that line holds no lower-case letter); ``X.Y`` upper-titled
    sections; ``X.Y.Z`` subsections; ``X.Y.Z.W...`` clauses whose text follows
    the label; ``APPENDIX <letter>`` alone or ``Appendix <letter><n>.`` with an
    inline title; ``A1.1`` appendix sub-units with an inline title.
market_manual
    ``SECTION <n> <title>``; ``X.Y`` subsections; ``X.Y.Z...`` clauses;
    ``APPENDIX <letter>`` alone or ``Appendix <letter><n>.`` with an inline
    title; ``Annex "<letter>"`` alone.
erc_resolution
    ``WHEREAS`` and ``RESOLVED`` paragraph starts; ``Section <n>. <title>``
    headings; numbered clauses (``1.`` paragraphs and dotted ``X.Y`` units).
doe_circular
    ``SECTION <n>. <title>`` headings; numbered clauses (``1.`` paragraphs and
    dotted ``X.Y`` units).

In every family a numbered line is recognised only when the text after the
number starts a unit rather than continuing a sentence: a lower-case first
letter, or a leading ``,;:.()``, marks a line that wrapped out of the previous
sentence, and such a line is reported as an unrecognized candidate instead.  A
label whose components are zero-padded or contain a zero is not a unit number
and is likewise reported.  Grammar revisions are per family; reparsing a source
returns an equal extraction and never rewrites an earlier one.
"""
from dataclasses import dataclass
import re

from .structure import (
    Diagnostic, DocumentStructure, Source, Span, StructureError, Locator,
    validate_locator,
)

FAMILIES = ('wesm_rules', 'market_manual', 'erc_resolution', 'doe_circular')

GRAMMAR_REVISIONS = {
    'wesm_rules': 'corp2-wesm-rules-v1',
    'market_manual': 'corp2-market-manual-v1',
    'erc_resolution': 'corp2-erc-resolution-v1',
    'doe_circular': 'corp2-doe-circular-v1',
}

__all__ = ['FAMILIES', 'GRAMMAR_REVISIONS', 'Heading', 'parse']

# A unit number: positive, unpadded components; at least one dot; an optional
# single trailing period (the chapter-10 and market-manual clause style).
_NUMBERED = re.compile(r'([1-9][0-9]*(?:\.[1-9][0-9]*)+)\.?[ \t]+(\S.*)\Z')
# A numbered paragraph: the dot is required and followed by a space.
_PARAGRAPH = re.compile(r'([1-9][0-9]*)\.[ \t]+(\S.*)\Z')
_LEADER_TAIL = re.compile(r'[ \t]*\.{4,}[ \t.]*\d{0,4}[ \t]*\Z')
_GLUED_PAGE_TAIL = re.compile(r'[a-z]\d{1,4}\Z')
_UPPERCASE_LINE = re.compile(r'[^a-z]{2,90}\Z')
_CONTINUATION_FIRST = ',;:.()'

# A heading keyword the family knows but this shape did not match, or a dotted
# number at line start, is reported when it stays content.
_DOTTED_START = re.compile(r'[ \t]*\d+(?:\.\d+)+\.?(?=[ \t])')
_PARAGRAPH_START = re.compile(r'[ \t]*\d+\.[ \t]')
_CANDIDATE_KEYWORDS = {
    'wesm_rules': re.compile(
        r'[ \t]*(?:CHAPTER|APPENDICES?|ANNEX(?:ES)?|SECTIONS?|SCHEDULE|PART)\b',
        re.IGNORECASE),
    'market_manual': re.compile(
        r'[ \t]*(?:CHAPTER|APPENDICES?|ANNEX(?:ES)?|SECTIONS?|PART)\b', re.IGNORECASE),
    'erc_resolution': re.compile(
        r'[ \t]*(?:WHEREAS|RESOLVED|WHEREFORE|NOW THEREFORE|SECTIONS?|ARTICLES?)\b',
        re.IGNORECASE),
    'doe_circular': re.compile(
        r'[ \t]*(?:SECTIONS?|ARTICLES?|WHEREAS|RESOLVED)\b', re.IGNORECASE),
}
_PARAGRAPH_FAMILIES = ('erc_resolution', 'doe_circular')


@dataclass(frozen=True)
class Heading:
    """One recognised heading line: kind, label, and what the grammar knows."""
    kind: str
    label: str
    title: str | None = None
    title_from_next_line: bool = False
    toc_entry: bool = False


def _continues_sentence(rest: str) -> bool:
    """True when the text after a number continues the previous sentence."""
    first = rest.lstrip()[:1]
    return bool(first) and (first.islower() or first in _CONTINUATION_FIRST)


def _toc_tail(rest: str) -> tuple[str, bool]:
    """Split a contents-list dot leader (and any page number on it) off a title.

    Only a run of four or more dots, or a page number glued to a word, is taken
    as evidence of a contents line: a title that merely ends in a number (the
    WESM Rules' own ``3.1 SCOPE OF CHAPTER 3``) keeps it.
    """
    match = _LEADER_TAIL.search(rest)
    if match:
        return rest[:match.start()].rstrip(), True
    match = _GLUED_PAGE_TAIL.search(rest)
    if match:
        return rest[:match.start() + 1].rstrip(), True
    return rest.rstrip(), False


def _leader_present(rest: str) -> bool:
    return _LEADER_TAIL.search(rest) is not None


def _unit(body: str):
    """``(label, rest)`` for a dotted unit line that starts a unit, else None."""
    match = _NUMBERED.fullmatch(body)
    if not match:
        return None
    label, rest = match.groups()
    return None if _continues_sentence(rest) else (label, rest)


def _titled(kind: str, label: str, rest: str) -> Heading:
    title, toc = _toc_tail(rest)
    return Heading(kind, label, title or None, toc_entry=toc)


def _clause(kind: str, label: str, rest: str) -> Heading:
    return Heading(kind, label, None, toc_entry=_leader_present(rest))


def _paragraph(body: str) -> Heading | None:
    match = _PARAGRAPH.fullmatch(body)
    if not match:
        return None
    label, rest = match.groups()
    return None if _continues_sentence(rest) else _clause('clause', label, rest)


def _appendix(label_pattern: re.Pattern, body: str) -> Heading | None:
    """``APPENDIX <letter><n>`` alone, with an inline title, or with a leader."""
    match = label_pattern.fullmatch(body)
    if not match:
        return None
    label, rest = match.groups()
    rest = rest.strip()
    if rest.startswith('.'):
        rest = rest[1:].strip()
    core, toc = _toc_tail(rest) if rest else ('', False)
    if not core:
        return Heading('appendix', f'Appendix {label}', title_from_next_line=True,
                       toc_entry=toc)
    if _continues_sentence(core):
        return None
    return Heading('appendix', f'Appendix {label}', core, toc_entry=toc)


_CHAPTER = re.compile(r'CHAPTER[ \t]+([1-9][0-9]*)[ \t]*\Z')
_APPENDIX_LABEL = re.compile(r'[Aa][Pp][Pp][Ee][Nn][Dd][Ii][Xx][ \t]+([A-Z][0-9]*)(.*)\Z')
_WESM_APPENDIX_UNIT = re.compile(r'([A-Z][0-9]+(?:\.[1-9][0-9]*)+)\.?[ \t]+(\S.*)\Z')


def _wesm_rules_line(body: str) -> Heading | None:
    match = _CHAPTER.fullmatch(body)
    if match:
        return Heading('chapter', f'Chapter {match.group(1)}', title_from_next_line=True)
    appendix = _appendix(_APPENDIX_LABEL, body)
    if appendix:
        return appendix
    match = _WESM_APPENDIX_UNIT.fullmatch(body)
    if match:
        label, rest = match.groups()
        if not _continues_sentence(rest):
            return _titled('appendix_section', label, rest)
        return None
    unit = _unit(body)
    if unit:
        label, rest = unit
        depth = label.count('.') + 1
        if depth == 2:
            return _titled('section', label, rest)
        if depth == 3:
            return _titled('subsection', label, rest)
        return _clause('clause', label, rest)
    return None


_SECTION_TITLE = re.compile(r'SECTION[ \t]+([1-9][0-9]*)\.?[ \t]+(\S.*)\Z')
_ANNEX = re.compile(r'Annex[ \t]+[“"]([A-Z])[”"][ \t]*\Z')
_PART = re.compile(r'[Pp][Aa][Rr][Tt][ \t]+([1-9][0-9]*)\.?[ \t]+(\S.*)\Z')


def _market_manual_line(body: str) -> Heading | None:
    match = _SECTION_TITLE.fullmatch(body)
    if match:
        number, rest = match.groups()
        return _titled('section', f'Section {number}', rest)
    appendix = _appendix(_APPENDIX_LABEL, body)
    if appendix:
        return appendix
    match = _PART.fullmatch(body)
    if match:
        number, rest = match.groups()
        if not _continues_sentence(rest):
            return _titled('part', f'Part {number}', rest)
        return None
    match = _ANNEX.fullmatch(body)
    if match:
        return Heading('annex', f'Annex "{match.group(1)}"')
    unit = _unit(body)
    if unit:
        label, rest = unit
        if label.count('.') + 1 == 2:
            return _titled('subsection', label, rest)
        return _clause('clause', label, rest)
    return None


_WHEREAS = re.compile(r'WHEREAS\b')
_RESOLVED = re.compile(r'RESOLVED\b')
_SECTION_WORD = re.compile(r'[Ss][Ee][Cc][Tt][Ii][Oo][Nn][ \t]+([1-9][0-9]*)\.?[ \t]+(\S.*)\Z')


def _erc_resolution_line(body: str) -> Heading | None:
    if _WHEREAS.match(body):
        return Heading('whereas', 'WHEREAS')
    if _RESOLVED.match(body):
        return Heading('resolved', 'RESOLVED')
    match = _SECTION_WORD.fullmatch(body)
    if match:
        return _titled('section', f'Section {match.group(1)}', match.group(2))
    paragraph = _paragraph(body)
    if paragraph:
        return paragraph
    unit = _unit(body)
    if unit:
        label, rest = unit
        return _clause('clause', label, rest)
    return None


_DOE_SECTION = re.compile(r'[Ss][Ee][Cc][Tt][Ii][Oo][Nn][ \t]+([1-9][0-9]*)\.?[ \t]+(\S.*)\Z')


def _doe_circular_line(body: str) -> Heading | None:
    match = _DOE_SECTION.fullmatch(body)
    if match:
        return _titled('section', f'Section {match.group(1)}', match.group(2))
    paragraph = _paragraph(body)
    if paragraph:
        return paragraph
    unit = _unit(body)
    if unit:
        label, rest = unit
        return _clause('clause', label, rest)
    return None


_RECOGNISERS = {
    'wesm_rules': _wesm_rules_line,
    'market_manual': _market_manual_line,
    'erc_resolution': _erc_resolution_line,
    'doe_circular': _doe_circular_line,
}


def _candidate(family: str, body: str) -> bool:
    if _CANDIDATE_KEYWORDS[family].match(body):
        return True
    if _DOTTED_START.match(body):
        return True
    return family in _PARAGRAPH_FAMILIES and _PARAGRAPH_START.match(body) is not None


def _lines(text: str) -> tuple[tuple[int, str], ...]:
    """Line bodies with their character offsets; only LF and CRLF delimit."""
    lines = []
    offset = 0
    for line in text.split('\n'):
        body = line[:-1] if line.endswith('\r') else line
        lines.append((offset, body))
        offset += len(line) + 1
    return tuple(lines)


def _next_line_title(lines, index, recognise):
    """The next non-blank line when it is a title and not itself a heading.

    A title holds no lower-case letter (``THE MARKET``); a line the grammar
    recognises as another heading is never taken as a title.
    """
    for _, body in lines[index + 1:]:
        if not body.strip():
            continue
        stripped = body.strip()
        if recognise(body) is not None:
            return None
        return stripped if _UPPERCASE_LINE.fullmatch(stripped) else None
    return None


def parse(source: Source, family: str) -> DocumentStructure:
    """Segment a native-text source with the grammar of one document family."""
    if family not in _RECOGNISERS:
        raise StructureError(
            f'unknown family {family!r}; expected one of {", ".join(FAMILIES)}')
    if not isinstance(source, Source):
        raise StructureError('expected Source')
    lines = _lines(source.text)
    recognise = _RECOGNISERS[family]
    headings = []
    diagnostics = []
    seen = set()
    for index, (offset, body) in enumerate(lines):
        if not body.strip():
            continue
        heading = recognise(body)
        if heading is None:
            if _candidate(family, body):
                diagnostics.append(
                    Diagnostic('unrecognized_heading', offset, offset + len(body)))
            continue
        title = heading.title
        if title is None and heading.title_from_next_line:
            title = _next_line_title(lines, index, recognise)
        label = heading.label
        end = offset + len(body)
        if label in seen:
            diagnostics.append(Diagnostic('duplicate_label', offset, end))
        seen.add(label)
        if heading.toc_entry:
            diagnostics.append(Diagnostic('toc_entry', offset, end))
        headings.append((offset, heading.kind, label, title))
    if not headings:
        boundaries = [(0, 'unclassified', None, None)]
        diagnostics.append(Diagnostic('no_recognized_heading', 0, len(source.text)))
    else:
        boundaries = headings
        if headings[0][0] > 0:
            boundaries = [(0, 'preamble', None, None)] + boundaries
    spans = []
    for index, (start, kind, label, title) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(source.text)
        locator = Locator(source.source_id, source.source_revision, source.digest, start, end)
        quote = source.text[start:end]
        validate_locator(source, locator, quote)
        spans.append(Span(kind, label, title, locator, quote,
                          tuple(d for d in diagnostics if start <= d.start < end)))
    return DocumentStructure(source, GRAMMAR_REVISIONS[family], tuple(spans))
