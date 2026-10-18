"""The agent's labelled fakes and its import boundary (DOCK-3, acceptance line 4).

Every fake carries `synthetic: true` and a label, down to each claim and each adapter result, and
no fake carries a figure. Nothing in src/agent imports the web layer (src/api, src/grid) or another
lane's internals: the imports are read from each module's syntax tree, top level and inside
functions, against an allowlist.
"""
import ast
import unittest
from pathlib import Path

from src.agent import fakes

ROOT = Path(__file__).resolve().parents[1]

#: The modules src/agent may import beyond the standard library and itself.
ALLOWED = {
    'src.contracts.jsonutil',
    'src.judgment', 'src.judgment.view', 'src.judgment.actions',  # the composer and DOCK-1's catalogue
    'src.outlook.records', 'src.outlook.dependency',               # the archive's own write paths
    'src.alerts.auth',                                              # the sign-in pattern
    'google.api_core.exceptions', 'google.cloud', 'fastapi', 'fastapi.responses',  # lazy, hosted only
}
BANNED_PREFIXES = ('src.api', 'src.grid', 'src.book', 'src.alerts.service', 'src.alerts.model',
                   'src.review', 'src.price', 'src.workspace', 'scripts')
STDLIB = {'copy', 'hashlib', 'threading', 'datetime', 're', 'uuid', 'json', 'importlib'}


def imports_of(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.add('src.agent' + ('.' + node.module if node.module else ''))
            else:
                found.add(node.module)
    return found


def every_fake():
    yield 'cases', fakes.FAKE_CASES
    for case in fakes.FAKE_CASES:
        yield 'case ' + case['case_id'], case
    yield 'claim_chain', fakes.FAKE_CLAIM_CHAIN
    for claim in fakes.FAKE_CLAIM_CHAIN['claims']:
        yield 'claim ' + claim['claim_id'], claim
    yield 'model_card', fakes.MODEL_CARD
    yield 'search_receipt', fakes.fake_search_receipt('q', '2026-10-14T23:59:59+08:00')
    yield 'search adapter result', fakes.FakeSearch().search('q', '2026-10-14T23:59:59+08:00')
    yield 'book exposure', fakes.FakeBook().exposure(['a'], ['n'], 'w', '2026-10-14T23:59:59+08:00')
    yield 'book impact', fakes.FakeBook().impact(['a'], 'o')
    yield 'search adapter', fakes.FakeSearch
    yield 'book adapter', fakes.FakeBook


def numbers_in(value):
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [n for k, v in value.items() if k not in ('position',) for n in numbers_in(v)]
    if isinstance(value, (list, tuple)):
        return [n for v in value for n in numbers_in(v)]
    return []


class Labelled(unittest.TestCase):
    def test_every_fake_carries_synthetic_true_and_a_label(self):
        for name, value in every_fake():
            if isinstance(value, tuple):
                continue  # the cases tuple; each case is checked on its own
            synthetic = value['synthetic'] if isinstance(value, dict) else getattr(value, 'synthetic', None)
            label = value['label'] if isinstance(value, dict) else getattr(value, 'label', None)
            self.assertIs(synthetic, True, name)
            self.assertIsInstance(label, str, name)
            self.assertTrue(label.startswith(fakes.LABEL_PREFIX), name)

    def test_labels_are_plain_words_without_lane_codes_or_semicolons(self):
        import re
        codes = re.compile(r'\b(CASE|EVIDENCE|MODELS|BOOK|WATCH|LEDGER|DOCK)\b|\b[A-Z]{1,6}-?\d\b')
        texts = [fakes.MODEL_CARD['status_line']]
        for name, value in every_fake():
            if isinstance(value, tuple):
                continue
            texts.append(value['label'] if isinstance(value, dict) else value.label)
        for text in texts:
            self.assertNotIn(';', text)
            self.assertIsNone(codes.search(text), text)
            self.assertNotIn('stale', text.lower())

    def test_two_cases_one_empty_and_a_two_claim_chain(self):
        self.assertEqual(len(fakes.FAKE_CASES), 2)
        self.assertEqual([c['event_id'] is None for c in fakes.FAKE_CASES], [False, True])
        self.assertEqual(len(fakes.FAKE_CLAIM_CHAIN['claims']), 2)
        self.assertEqual(fakes.FAKE_CLAIM_CHAIN['case_id'], fakes.FAKE_CASES[0]['case_id'])
        self.assertEqual(len(fakes.open_cases('anyone')), 2)

    def test_no_fake_carries_a_figure(self):
        for name, value in every_fake():
            if isinstance(value, (dict, tuple)):
                self.assertEqual(numbers_in(value), [], name)

    def test_the_fakes_are_reachable_by_name(self):
        self.assertEqual(set(fakes.FAKES), {'cases', 'claim_chain', 'model_card', 'search_receipt', 'search', 'book'})
        self.assertIs(fakes.fake('search'), fakes.FakeSearch)
        copy = fakes.fake('claim_chain')
        copy['claims'].clear()
        self.assertEqual(len(fakes.FAKE_CLAIM_CHAIN['claims']), 2)

    def test_the_search_receipt_names_its_fields_and_is_stable(self):
        a = fakes.fake_search_receipt('q', 'c')
        self.assertEqual(a, fakes.fake_search_receipt('q', 'c'))
        self.assertNotEqual(a['receipt_id'], fakes.fake_search_receipt('q2', 'c')['receipt_id'])
        self.assertTrue({'receipt_id', 'question_id', 'cutoff', 'engine_id', 'results', 'bytes', 'cost_usd'} <= set(a))
        self.assertTrue(all(r['url'].startswith('https://example.invalid/') for r in a['results']))

    def test_the_model_card_has_the_models_page_fields(self):
        self.assertTrue({'name', 'status_word', 'status_line', 'method', 'inputs', 'figures', 'as_of'}
                        <= set(fakes.MODEL_CARD))


class ImportBoundary(unittest.TestCase):
    def test_nothing_in_src_agent_imports_the_web_layer_or_another_lanes_internals(self):
        paths = sorted((ROOT / 'src/agent').glob('*.py'))
        self.assertTrue(paths)
        for path in paths:
            for module in imports_of(path):
                self.assertFalse(module.startswith(BANNED_PREFIXES), f'{path.name} imports {module}')
                if module.startswith('src.agent') or module in STDLIB:
                    continue
                self.assertIn(module, ALLOWED, f'{path.name} imports {module}')

    def test_src_judgment_actions_is_not_created_here(self):
        # DOCK-1 owns the file; this task reads it lazily by name (src/agent/catalogue.py).
        tracked = (ROOT / 'src/agent/catalogue.py').read_text(encoding='utf-8')
        self.assertIn("MODULE = 'src.judgment.actions'", tracked)


if __name__ == '__main__':
    unittest.main()
