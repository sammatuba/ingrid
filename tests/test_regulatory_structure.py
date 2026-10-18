"""Synthetic R0 behavior, evidence preservation and failure checks."""
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
import unittest

from src.regulatory import (
    DateMetadata, Locator, Source, StructureError, parse, validate_locator,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'regulatory'


def source(raw, **kwargs):
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    return Source('synthetic-document', 'v1', hashlib.sha256(raw).hexdigest(), raw, **kwargs)


class RegulatoryStructureTests(unittest.TestCase):
    def assert_exact(self, src):
        result = parse(src)
        self.assertEqual(result, parse(src))
        self.assertEqual(''.join(s.quoted_text for s in result.spans), src.text)
        self.assertEqual(result.source.original_bytes, src.original_bytes)
        position = 0
        for span in result.spans:
            self.assertEqual(span.locator.start, position)
            validate_locator(src, span.locator, span.quoted_text)
            position = span.locator.end
        self.assertEqual(position, len(src.text))
        return result

    def test_fixtures_exact_content_and_expected_boundaries(self):
        for name in ('synthetic_lf.txt', 'synthetic_crlf.txt'):
            with self.subTest(name=name):
                src = source((FIXTURES / name).read_bytes())
                result = self.assert_exact(src)
                self.assertEqual([s.kind for s in result.spans],
                                 ['preamble', 'section', 'section', 'section', 'annex'])
                self.assertEqual([s.label for s in result.spans],
                                 [None, 'Section 1', 'Section 2', 'Section 1', 'Annex A'])
                self.assertIn('Except during fictional maintenance', result.spans[1].quoted_text)
                self.assertIn('α | 10 MW', result.spans[2].quoted_text)
                self.assertIn('[1] Fictional footnote.', result.spans[2].quoted_text)
                self.assertIn('unrecognized_heading', [d.code for d in result.spans[2].diagnostics])
                self.assertEqual([d.code for d in result.spans[3].diagnostics], ['duplicate_label'])
                self.assertEqual(result.spans[1].locator.start, src.text.index('Section 1.'))
                self.assertNotEqual(result.spans[1].locator.start,
                                    src.original_bytes.index(b'Section 1.'))

    def test_no_heading_unknown_formats_and_whitespace(self):
        for text in ('SYNTHETIC\nSection IV. Roman\nbody', ' \t\r\n',
                     'section 1. lower\nAnnex aa. title', '\ufeffSection 1. BOM',
                     'Section 0. zero', 'Section 01. padded', 'SECTION 1. ',
                     'Annex a. lower', ' Section 1. indented', 'Section 1. title\r'):
            with self.subTest(text=text):
                result = self.assert_exact(source(text))
                self.assertEqual(result.spans[0].kind, 'unclassified')
                self.assertIn('no_recognized_heading', [d.code for d in result.spans[0].diagnostics])

    def test_heading_grammar_and_unicode_line_separators(self):
        result = self.assert_exact(source('SECTION 12. Café 😀\r\ntext\u2028Section 3. embedded\nAnnex Z. End'))
        self.assertEqual([s.label for s in result.spans], ['Section 12', 'Annex Z'])
        self.assertEqual(result.spans[0].title, 'Café 😀')
        self.assertEqual(result.spans[1].quoted_text, 'Annex Z. End')

    def test_metadata_is_supplied_only(self):
        unknown = DateMetadata(None, None, 'not supplied by source custodian')
        published = DateMetadata('2026-10', 'month', None)
        src = source('Section 1. Effective immediately\nApproved forever.',
                     publication=published, effectivity=unknown)
        result = parse(src)
        self.assertIs(result.source.publication, published)
        self.assertIs(result.source.effectivity, unknown)
        self.assertIsNone(parse(source(src.text)).source.effectivity)

    def test_invalid_sources(self):
        for raw in (b'', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(StructureError):
                source(raw)
        good = source('Section 1. Valid')
        for changes in ({'digest': '0' * 64}, {'original_bytes': good.original_bytes + b'x'},
                        {'source_id': ''}, {'source_revision': None},
                        {'source_id': '\ud800'}, {'publication': {}}, {'original_bytes': bytearray(b'x')}):
            with self.subTest(changes=changes), self.assertRaises(StructureError):
                replace(good, **changes)
        with self.assertRaises(StructureError):
            parse('not a Source')

    def test_invalid_date_metadata(self):
        for values in ((None, None, None), (None, 'day', 'unknown'),
                       ('2026', None, None), ('2026', 'year', 'unknown')):
            with self.subTest(values=values), self.assertRaises(StructureError):
                DateMetadata(*values)

    def test_locator_rejects_tampering(self):
        src = source('Section 1. 😀\nbody')
        span = parse(src).spans[0]
        for changes in ({'source_id': 'other'}, {'source_revision': 'v2'}, {'digest': '0' * 64},
                        {'start': -1}, {'start': True}, {'end': 1.0}, {'end': 1000},
                        {'start': 2, 'end': 1}, {'end': 0}, {'end': len(src.original_bytes)}):
            with self.subTest(changes=changes), self.assertRaises(StructureError):
                validate_locator(src, replace(span.locator, **changes), span.quoted_text)
        with self.assertRaises(StructureError):
            validate_locator(src, span.locator, 'changed quote')

    def test_reparse_preserves_original_and_previous_extraction(self):
        src = source('Section 1. Original')
        first = parse(src)
        second = parse(src)
        self.assertIsNot(first, second)
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.parser_revision = 'overwrite'
        with self.assertRaises(FrozenInstanceError):
            src.original_bytes = b'overwrite'

    def test_deterministic_reconstruction_combinations(self):
        # Exercise mixed newlines, non-BMP offsets, trailing newline and blank lines.
        import itertools
        for pieces in itertools.product(('😀\n', 'Section 1. A\r\n', 'Annex B. B\n',
                                         'Section IV. Unknown\n', '\r\n'), repeat=3):
            self.assert_exact(source(''.join(pieces)))
