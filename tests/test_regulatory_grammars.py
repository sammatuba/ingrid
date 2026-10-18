"""Family grammars: synthetic fixtures and short cited excerpts of the real rules.

The excerpts are the ones ``scripts/corpus/excerpt.py`` takes from the PEMC
compendium; only their quoted text is committed, never document bytes.
"""
import hashlib
import json
import unittest
from pathlib import Path

from src.regulatory.grammars import FAMILIES, GRAMMAR_REVISIONS, parse
from src.regulatory.structure import Source, StructureError, validate_locator

FIXTURES = Path(__file__).parent / 'fixtures' / 'regulatory'
EXCERPTS = FIXTURES / 'excerpts.json'

EXCERPT_EXPECTATIONS = {
    'wesm-rules-contents-chapters': None,
    'wesm-rules-chapter-3': (
        ('chapter', 'Chapter 3', 'THE MARKET'),
        ('section', '3.1', 'SCOPE OF CHAPTER 3'),
    ),
    'wesm-rules-subsection-3-5-4': (
        ('subsection', '3.5.4', 'Load Forecasting'),
        ('clause', '3.5.4.1', None),
    ),
    'wesm-rules-appendix-a1': (
        ('appendix', 'Appendix A', 'APPENDICES TO CHAPTER 3'),
        ('appendix', 'Appendix A1', 'Information to be Supplied with Offers to Supply and to Buy'),
        ('appendix_section', 'A1.1', 'Generation Offers'),
    ),
    'manual-bsm-section-1': (
        ('section', 'Section 1', 'INTRODUCTION'),
        ('subsection', '1.1', 'BACKGROUND'),
        ('subsection', '1.2', 'PURPOSE'),
    ),
    'manual-dp-section-1': (
        ('section', 'Section 1', 'INTRODUCTION'),
        ('subsection', '1.1', 'Overview of WESM Operations'),
        ('clause', '1.1.1', None),
    ),
    'manual-msp-appendix-c': (
        ('appendix', 'Appendix C', 'GOVERNING PROVISIONS OF THE WESM RULES'),
    ),
    'manual-msp-annex-a': (
        ('annex', 'Annex "A"', None),
    ),
}

EXCERPT_FAMILIES = {
    'wesm-rules-contents-chapters': 'wesm_rules',
    'wesm-rules-chapter-3': 'wesm_rules',
    'wesm-rules-subsection-3-5-4': 'wesm_rules',
    'wesm-rules-appendix-a1': 'wesm_rules',
    'manual-bsm-section-1': 'market_manual',
    'manual-dp-section-1': 'market_manual',
    'manual-msp-appendix-c': 'market_manual',
    'manual-msp-annex-a': 'market_manual',
}

SYNTHETIC_FIXTURES = (
    'synthetic_wesm_rules.txt', 'synthetic_market_manual.txt',
    'synthetic_erc_resolution.txt', 'synthetic_doe_circular.txt',
)


def source(raw, **kwargs):
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    return Source('synthetic-document', 'v1', hashlib.sha256(raw).hexdigest(), raw, **kwargs)


def fixture(name):
    return source((FIXTURES / name).read_bytes())


class GrammarTestCase(unittest.TestCase):
    def assert_exact(self, src, family):
        """Spans tile the text, locators validate, reparsing is identical."""
        result = parse(src, family)
        self.assertEqual(result, parse(src, family))
        self.assertEqual(result.parser_revision, GRAMMAR_REVISIONS[family])
        self.assertEqual(result.source.original_bytes, src.original_bytes)
        self.assertEqual(''.join(span.quoted_text for span in result.spans), src.text)
        position = 0
        for span in result.spans:
            self.assertEqual(span.locator.start, position)
            validate_locator(src, span.locator, span.quoted_text)
            position = span.locator.end
        self.assertEqual(position, len(src.text))
        return result

    def outline(self, structure):
        return [(span.kind, span.label, span.title) for span in structure.spans]

    def codes(self, structure):
        return [d.code for span in structure.spans for d in span.diagnostics]


class SyntheticFixtureTests(GrammarTestCase):
    def test_wesm_rules_fixture(self):
        src = fixture('synthetic_wesm_rules.txt')
        result = self.assert_exact(src, 'wesm_rules')
        self.assertEqual(
            [span.kind for span in result.spans],
            ['preamble', 'chapter', 'section', 'subsection', 'subsection', 'subsection',
             'section', 'subsection', 'clause', 'appendix', 'appendix',
             'appendix_section', 'appendix_section', 'chapter', 'section',
             'subsection', 'subsection'])
        self.assertEqual(
            [span.label for span in result.spans],
            [None, 'Chapter 1', '1.1', '1.1.1', '1.1.2', '1.1.3', '1.2', '1.2.1',
             '1.2.1.1', 'Appendix A', 'Appendix A1', 'A1.1', 'A1.2', 'Chapter 2',
             '2.1', '2.1.1', '2.1.1'])
        titles = [span.title for span in result.spans]
        self.assertEqual(titles[1], 'GENERAL PROVISIONS')
        self.assertEqual(titles[2], 'SCOPE')
        self.assertEqual(titles[10], 'Fictional forms')
        self.assertEqual(titles[11], 'Fictional notice form')
        self.assertIsNone(titles[8])  # a clause carries provision text, not a title
        self.assertEqual(titles[13], 'REGISTRATION')
        codes = self.codes(result)
        self.assertEqual(codes.count('duplicate_label'), 1)
        self.assertEqual(codes.count('unrecognized_heading'), 4)
        # The unsupported heading, the wrapped cross-reference and the zero
        # component stay content inside the span they fall in.
        appendix_body = result.spans[12].quoted_text
        self.assertIn('Section 3. An unsupported heading stays content', appendix_body)
        self.assertIn('2.2 as either the fictional old cover', appendix_body)
        self.assertIn('1.0 A zero component is not a unit number', appendix_body)
        self.assertEqual(result.spans[16].diagnostics[0].code, 'duplicate_label')

    def test_market_manual_fixture(self):
        src = fixture('synthetic_market_manual.txt')
        result = self.assert_exact(src, 'market_manual')
        self.assertEqual(
            self.outline(result),
            [('preamble', None, None),
             ('section', 'Section 1', 'INTRODUCTION'),
             ('subsection', '1.1', 'SCOPE'),
             ('clause', '1.1.1', None),
             ('clause', '1.1.2', None),
             ('section', 'Section 2', 'DEFINITIONS'),
             ('subsection', '2.1', 'Fictional terms'),
             ('clause', '2.1.1', None),
             ('section', 'Section 3', 'FICTIONAL APPENDIX'),
             ('appendix', 'Appendix A', 'Fictional timetable'),
             ('part', 'Part 1', 'Fictional steps'),
             ('annex', 'Annex "A"', None),
             ('annex', 'Annex "B"', None)])
        codes = self.codes(result)
        self.assertEqual(codes.count('toc_entry'), 1)
        self.assertEqual(codes.count('unrecognized_heading'), 1)
        self.assertIn('Annex “A” and shown in the fictional diagram',
                      result.spans[12].quoted_text)
        self.assertIn('.................................. 12', result.spans[8].quoted_text)

    def test_erc_resolution_fixture(self):
        src = fixture('synthetic_erc_resolution.txt')
        result = self.assert_exact(src, 'erc_resolution')
        self.assertEqual(
            self.outline(result),
            [('preamble', None, None),
             ('whereas', 'WHEREAS', None),
             ('whereas', 'WHEREAS', None),
             ('section', 'Section 1', 'Fictional scope'),
             ('section', 'Section 2', 'Fictional orders'),
             ('clause', '1', None),
             ('clause', '2', None),
             ('clause', '3.1', None)])
        whereases = [span for span in result.spans if span.kind == 'whereas']
        self.assertTrue(whereases[0].quoted_text.startswith('WHEREAS, the fictional Commission'))
        self.assertTrue(whereases[1].quoted_text.startswith('WHEREAS, a second fictional recital'))
        self.assertEqual(self.codes(result).count('duplicate_label'), 1)

    def test_doe_circular_fixture(self):
        src = fixture('synthetic_doe_circular.txt')
        result = self.assert_exact(src, 'doe_circular')
        self.assertEqual(
            self.outline(result),
            [('preamble', None, None),
             ('section', 'Section 1', 'FICTIONAL TITLE'),
             ('section', 'Section 2', 'FICTIONAL SCOPE'),
             ('clause', '2.1', None),
             ('clause', '2.2', None),
             ('section', 'Section 3', 'FICTIONAL EFFECTIVITY'),
             ('clause', '3', None)])
        self.assertIn('the fictional sentence from the line above.',
                      result.spans[4].quoted_text)

    def test_fixtures_do_not_claim_authority(self):
        for name in SYNTHETIC_FIXTURES:
            with self.subTest(name=name):
                text = (FIXTURES / name).read_text(encoding='utf-8')
                self.assertTrue(text.startswith('SYNTHETIC'))
                self.assertIn('no legal authority', text)


class NumberedLineRuleTests(GrammarTestCase):
    def test_continuations_zero_components_and_padding_stay_content(self):
        text = ('1.1 SCOPE\n'
                '1.1.1.1 The fictional provision stands.\n'
                '2.3.5 or 2.4 as either the fictional cover\n'
                '3.1.1 (a) (1) and as authorized\n'
                '2.2 , and 2.4 other than the fiction\n'
                '1.0 A zero component is not a unit number\n'
                '01.2 A padded component is not a unit number\n'
                '4.1.1 shall be amended in accordance with the fiction\n')
        src = source(text)
        result = self.assert_exact(src, 'wesm_rules')
        self.assertEqual([span.label for span in result.spans], ['1.1', '1.1.1.1'])
        self.assertEqual([d.code for d in result.spans[1].diagnostics],
                         ['unrecognized_heading'] * 6)
        for line in ('2.3.5 or 2.4', '3.1.1 (a) (1)', '2.2 , and 2.4', '1.0 A zero',
                     '01.2 A padded', '4.1.1 shall be amended'):
            self.assertIn(line, result.spans[1].quoted_text)

    def test_indented_numbered_lines_are_candidates(self):
        text = '1.1 SCOPE\n 1.1.1 An indented line\n\t2.1 An indented line\n'
        result = self.assert_exact(source(text), 'wesm_rules')
        self.assertEqual([span.label for span in result.spans], ['1.1'])
        self.assertEqual([d.code for d in result.spans[0].diagnostics],
                         ['unrecognized_heading', 'unrecognized_heading'])

    def test_toc_lines_and_label_repeats(self):
        text = ('1.1 SCOPE\n'
                '1.1.1 Fictional clause\n'
                '2.1 DEFINITIONS ................. 12\n'
                '2.1 DEFINITIONS\n'
                '2.1.1 Fictional definition\n')
        result = self.assert_exact(source(text), 'market_manual')
        self.assertEqual([span.title for span in result.spans],
                         ['SCOPE', None, 'DEFINITIONS', 'DEFINITIONS', None])
        self.assertEqual([d.code for d in result.spans[2].diagnostics], ['toc_entry'])
        self.assertEqual([d.code for d in result.spans[3].diagnostics], ['duplicate_label'])
        self.assertIn('.................', result.spans[2].quoted_text)

    def test_title_reported_only_when_the_line_is_a_title(self):
        text = ('CHAPTER 4\n'
                'A chapter title with lower case stays content\n'
                '4.1 SCOPE\n'
                'APPENDIX C\n'
                'APPENDICES TO CHAPTER 4\n'
                'CHAPTER 5\n'
                '5.1 SCOPE\n')
        result = self.assert_exact(source(text), 'wesm_rules')
        self.assertEqual([span.label for span in result.spans],
                         ['Chapter 4', '4.1', 'Appendix C', 'Chapter 5', '5.1'])
        self.assertIsNone(result.spans[0].title)
        self.assertEqual(result.spans[2].title, 'APPENDICES TO CHAPTER 4')
        # A heading is never taken as the title of the heading above it.
        self.assertIsNone(result.spans[3].title)

    def test_crlf_and_character_offsets(self):
        lf = 'CHAPTER 1\nGENERAL \U0001f600\n1.1 SCOPE\n1.1.1.1 The fictional provision.\n'
        result = self.assert_exact(source(lf), 'wesm_rules')
        self.assertEqual([span.label for span in result.spans],
                         ['Chapter 1', '1.1', '1.1.1.1'])
        self.assertEqual(result.spans[0].title, 'GENERAL \U0001f600')
        crlf_result = self.assert_exact(source(lf.replace('\n', '\r\n')), 'wesm_rules')
        self.assertEqual([span.kind for span in result.spans],
                         [span.kind for span in crlf_result.spans])
        self.assertEqual([span.label for span in result.spans],
                         [span.label for span in crlf_result.spans])
        self.assertEqual([span.title for span in result.spans],
                         [span.title for span in crlf_result.spans])
        clause = result.spans[2]
        self.assertEqual(clause.locator.start, lf.index('1.1.1.1'))
        self.assertNotEqual(clause.locator.start, lf.encode('utf-8').index(b'1.1.1.1'))

    def test_no_recognised_heading(self):
        result = self.assert_exact(source('Just a fictional note.\n'), 'doe_circular')
        self.assertEqual(result.spans[0].kind, 'unclassified')
        self.assertIsNone(result.spans[0].label)
        self.assertEqual([d.code for d in result.spans[0].diagnostics],
                         ['no_recognized_heading'])

    def test_family_and_source_validation(self):
        src = source('1.1 SCOPE\n')
        for family in ('', 'wesm', 'WESM_RULES', None, 7):
            with self.subTest(family=family), self.assertRaises(StructureError):
                parse(src, family)
        with self.assertRaises(StructureError):
            parse('not a Source', 'wesm_rules')
        self.assertEqual(set(FAMILIES),
                         {'wesm_rules', 'market_manual', 'erc_resolution', 'doe_circular'})
        self.assertEqual(set(GRAMMAR_REVISIONS), set(FAMILIES))
        for family in FAMILIES:
            self.assertTrue(GRAMMAR_REVISIONS[family].startswith('corp2-'))


class CitedExcerptTests(GrammarTestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(EXCERPTS.read_text(encoding='utf-8'))

    def excerpt(self, identifier):
        for entry in self.fixture['excerpts']:
            if entry['id'] == identifier:
                return entry
        raise AssertionError(f'no excerpt {identifier!r} in the fixture')

    def test_fixture_shape_and_hashes(self):
        self.assertEqual(self.fixture['excerpt_limit'], 400)
        self.assertEqual(len(self.fixture['excerpts']), len(EXCERPT_FAMILIES))
        self.assertEqual(set(EXCERPT_FAMILIES), set(EXCERPT_EXPECTATIONS))
        self.assertEqual(len(self.fixture['compendium']['zip_sha256']), 64)
        sources = {}
        for entry in self.fixture['sources']:
            self.assertEqual(len(entry['sha256']), 64)
            self.assertTrue(entry['file'].endswith('.pdf'))
            sources[entry['file']] = entry
        self.assertEqual(len(sources), 4)
        for entry in self.fixture['excerpts']:
            with self.subTest(excerpt=entry['id']):
                self.assertLessEqual(len(entry['text']), 400)
                self.assertEqual(entry['end'] - entry['start'], len(entry['text']))
                self.assertGreaterEqual(entry['start'], 0)
                self.assertIn(entry['file'], sources)
                self.assertIn(entry['page'], range(1, sources[entry['file']]['pages'] + 1))
                self.assertEqual(hashlib.sha256(entry['text'].encode('utf-8')).hexdigest(),
                                 entry['text_sha256'])
                self.assertEqual(len(entry['page_text_sha256']), 64)

    def test_real_excerpts_are_recognised(self):
        for identifier, expected in EXCERPT_EXPECTATIONS.items():
            with self.subTest(excerpt=identifier):
                entry = self.excerpt(identifier)
                result = self.assert_exact(source(entry['text']),
                                           EXCERPT_FAMILIES[identifier])
                if expected is None:
                    self.assertEqual(len(result.spans), 1)
                    self.assertEqual(result.spans[0].kind, 'unclassified')
                    codes = self.codes(result)
                    self.assertEqual(codes.count('no_recognized_heading'), 1)
                    self.assertIn('Chapter 1. Introduction', result.spans[0].quoted_text)
                    self.assertGreaterEqual(codes.count('unrecognized_heading'), 5)
                    continue
                self.assertEqual(self.outline(result), list(expected))
                for span in result.spans:
                    if span.label is not None:
                        self.assertEqual(span.locator.start,
                                         entry['text'].index(span.quoted_text[:24]))

    def test_excerpts_are_short_citations(self):
        for entry in self.fixture['excerpts']:
            with self.subTest(excerpt=entry['id']):
                self.assertTrue(entry['text'].strip())
                self.assertEqual(entry['text'][:1], entry['text'][:1])
                self.assertLessEqual(len(entry['text']), 400)


if __name__ == '__main__':
    unittest.main()
