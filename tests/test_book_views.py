"""BOOK-4: the synthetic book in the dock, offline and with no model.

The composer (``src/judgment/view.py``) gains two components, ``exposure_table`` and
``account_impact``, filled from the book's exposure and impact records (BOOK-2) exactly as it
fills the impact band: the plan arranges, the records fill, every figure is copied from a record
named by its record id, and the synthetic label travels with it. The two read actions,
``query_exposure`` and ``query_impact``, run through the book adapter (``src/book/adapter.py``),
which answers with identifiers and refuses with BOOK-2's stable codes.

Every figure here is a method demonstration on the synthetic book. The planner is the labelled
``FixtureView``; no live backend is built and no network, model or cloud call is made.
"""
import ast
import copy
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from src.book import adapter as book_adapter
from src.book.adapter import BookAdapter, parse_window, stamp_exposure, window_id
from src.book.exposure import Window, exposure, load_book
from src.book.impact import load_vintage, query_impact, verify_record
from src.book.records import LABEL as BOOK_LABEL
from src.contracts.jsonutil import canonical_dumps, compute_content_digest
from src.judgment import view
from src.judgment.actions import ACTIONS, check_action
from src.judgment.view import (BOOK_COMPONENTS, BOOK_TEXT_PATHS, BOOK_TEXT_TEMPLATES, CATALOGUE,
                               COMPONENTS, QUOTABLE_PATHS, FixtureView, PlanRefused,
                               answer_question, compose, fixture_backend, render_request,
                               validate_response)
from src.outlook.records import OutlookArchive, build_outlook
from src.price.impact import MaterialityPolicy
from tests.fixtures.grid.catalog import build

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'tests' / 'fixtures' / 'book' / 'vintages'
V1, V2 = 'book-demo-2026-10-19-cvis', 'book-demo-2026-10-19-cvis-v2'
WINDOW = '2026-10-19T13:00/2026-10-19T15:00'
#: A view cutoff on 18 October, Manila 23:00: both fixture vintages are issued by then (02:00Z
#: and 06:00Z) and the book reads it as the local date 2026-10-18.
LATE = '2026-10-18T15:00:00Z'
VISAYAS = "What is exposed in Visayas tomorrow 13:00 to 15:00?"
EXPOSURE_QUESTION = 'What is exposed?'
#: Figures of the book records that are not quotable, by their record keys.
UNQUOTABLE = ('demand_mw', 'contracted_mw', 'over_contracted_mw', 'price_php_mwh',
              'reference_php_mwh', 'band_php_mwh', 'demand_mwh', 'covered_mwh')


def scratch_directory(prefix='book4-'):
    """One test's scratch directory, with the ignored-repo fallback the other tests use."""
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / '.local' / 'test-scratch'
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def adapter():
    return BookAdapter(MaterialityPolicy())


def outlook(outlook_id):
    return json.loads((ARCHIVE / 'outlooks' / f'{outlook_id}.json').read_text(encoding='utf-8'))


def visayas_records(cutoff=LATE, impact=V1):
    """The bake's record set at a later cutoff, with the book's two records for Visayas.

    The outlook record lists the archive's two book vintages, so the manifest offers their ids
    to ``query_impact``. The exposure and impact records are the adapter's own, for the region,
    the window and the cutoff of the question.
    """
    records = build.plan_records()
    book = adapter()
    records['outlook'] = dict(records['outlook'], outlooks=book.vintages())
    records['exposure'] = book.exposure_record(WINDOW, cutoff, region='Visayas')
    if impact is not None:
        accounts = [block['account_id'] for block in records['exposure']['accounts']]
        records['book_impact'] = book.impact_record(impact, WINDOW, cutoff, accounts=accounts)
    return records


def components_of(answer):
    return {part['component']: part for part in answer['components']}


def numeric_paths(value, path=''):
    """Every number in a value, with its path (``[]`` for a list item)."""
    found = []
    if type(value) is dict:
        for key, child in value.items():
            found += numeric_paths(child, f'{path}.{key}' if path else key)
    elif type(value) is list:
        for child in value:
            found += numeric_paths(child, path + '[]')
    elif type(value) in (int, float) and type(value) is not bool:
        found.append(path)
    return found


def plans_for(plan, forms=4):
    return {f'f{index}': copy.deepcopy(plan) for index in range(forms)}


def by_cell(rows):
    return {(row['account_id'], row['node_id'], row['hour_start']): row for row in rows}


class TheComponentsRenderFromTheBook(unittest.TestCase):
    """Each component fills from the fixture book's records with the labelled fixture planner."""

    def setUp(self):
        self.records = visayas_records()
        self.answer = answer_question(EXPOSURE_QUESTION, self.records, LATE, fixture_backend(),
                                      ids=adapter().manifest_ids(self.records['exposure']))
        self.parts = components_of(self.answer)

    def test_the_two_components_sit_beside_the_first_catalogue(self):
        self.assertEqual(BOOK_COMPONENTS, ('exposure_table', 'account_impact'))
        self.assertEqual(COMPONENTS, CATALOGUE + BOOK_COMPONENTS)
        self.assertEqual(view.COMPONENT_RECORD['exposure_table'], 'exposure')
        self.assertEqual(view.COMPONENT_RECORD['account_impact'], 'book_impact')
        self.assertEqual(view.COMPONENT_ARGS['exposure_table'], {})
        self.assertEqual(view.COMPONENT_ARGS['account_impact'], {})

    def test_the_exposure_question_shows_the_book_first_with_no_model(self):
        self.assertEqual('composed', self.answer['status'])
        self.assertEqual('synthetic_fixture', self.answer['receipt']['execution_mode'])
        self.assertEqual(['exposure_table', 'account_impact', 'impact_band', 'belief_card',
                          'judgment', 'receipt'],
                         [part['component'] for part in self.answer['components']])
        self.assertIs(True, self.answer['receipt']['stability']['stable'])
        self.assertEqual(4, self.answer['receipt']['stability']['forms'])

    def test_the_exposure_table_is_the_book_records_rows_by_record_id(self):
        record = self.records['exposure']
        fields = self.parts['exposure_table']['fields']
        self.assertEqual(record['content_digest'], fields['record_id'])
        self.assertEqual(compute_content_digest(record), fields['record_id'])
        self.assertEqual('exposure', self.parts['exposure_table']['record'])
        rows = by_cell(record['rows'])
        self.assertEqual(len(record['rows']), len(fields['rows']))
        for row in fields['rows']:
            source = rows[(row['account_id'], row['node_id'], row['hour_start'])]
            self.assertEqual(source['uncovered_mwh'], row['uncovered_mwh'])
            self.assertEqual([item['id'] for item in source['covering_contracts']],
                             [item['id'] for item in row['covering_contracts']])
            self.assertTrue(row['covering_contracts'], row)
        self.assertEqual([(block['account_id'], block['uncovered_mwh']) for block in record['accounts']],
                         [(block['account_id'], block['uncovered_mwh']) for block in fields['accounts']])
        self.assertEqual(record['totals']['uncovered_mwh'], fields['totals']['uncovered_mwh'])
        # BOOK-2's worked example: the affected part of Visayas, 95.244 MWh over two hours.
        self.assertEqual(95.244, fields['totals']['uncovered_mwh'])

    def test_the_account_impact_states_the_materiality_line_first(self):
        record = self.records['book_impact']
        verify_record(record)
        fields = self.parts['account_impact']['fields']
        self.assertEqual('materiality', next(iter(fields)))
        self.assertEqual(record['materiality'], fields['materiality'])
        self.assertEqual(record['content_digest'], fields['record_id'])
        self.assertEqual(V1, fields['vintage']['outlook_id'])
        self.assertEqual(outlook(V1)['content_digest'], fields['vintage']['outlook_digest'])
        for shown, source in zip(fields['accounts'], record['accounts']):
            for key in ('account_id', 'uncovered_mwh', 'p10_php', 'p50_php', 'p90_php'):
                self.assertEqual(source[key], shown[key], key)
        # BOOK-2's worked example: ACC-VIS03 at p10, p50, p90 under the first vintage.
        vis03 = next(block for block in fields['accounts'] if block['account_id'] == 'ACC-VIS03')
        self.assertEqual((515.13, 8679.93, 26370.33),
                         (vis03['p10_php'], vis03['p50_php'], vis03['p90_php']))

    def test_every_block_carries_the_synthetic_label(self):
        exposure_fields = self.parts['exposure_table']['fields']
        impact_fields = self.parts['account_impact']['fields']
        self.assertEqual(BOOK_LABEL, exposure_fields['label'])
        self.assertTrue(impact_fields['label'].startswith(BOOK_LABEL))
        for fields in (exposure_fields, impact_fields):
            self.assertIs(True, fields['synthetic'])
            blocks = fields['accounts'] + [fields['totals']] + fields.get('rows', [])
            for block in blocks:
                self.assertIs(True, block['synthetic'], block)
                self.assertEqual(fields['label'], block['label'])
        for name in BOOK_COMPONENTS:
            self.assertIs(True, self.parts[name]['synthetic'])
            self.assertEqual(self.parts[name]['fields']['label'], self.parts[name]['label'])
        # Each component's own mandatory parts (BOOK_MANDATORY_FIELDS), whatever the plan.
        for name in BOOK_COMPONENTS:
            fields = self.parts[name]['fields']
            for path in view.BOOK_MANDATORY_FIELDS[name]:
                values = [fields]
                for step in path.split('.'):
                    many = step.endswith('[]')
                    key = step[:-2] if many else step
                    for value in values:
                        self.assertIn(key, value, (name, path))
                    values = [value[key] for value in values]
                    if many:
                        values = [item for value in values for item in value]
                        self.assertTrue(values, (name, path))
                for value in values:
                    self.assertIsNotNone(value, (name, path))
        self.assertEqual('materiality', next(iter(self.parts['account_impact']['fields'])))
        labels = {item['record']: item for item in self.answer['labels']}
        self.assertEqual(BOOK_LABEL, labels['exposure']['label'])
        self.assertIs(True, labels['book_impact']['synthetic'])

    def test_the_receipt_names_each_book_record_by_its_record_id(self):
        refs = {ref['record']: ref for ref in self.answer['receipt']['records']}
        self.assertEqual(self.records['exposure']['content_digest'], refs['exposure']['record_id'])
        self.assertEqual(self.records['book_impact']['content_digest'],
                         refs['book_impact']['content_digest'])
        for kind in ('exposure', 'book_impact'):
            self.assertRegex(refs[kind]['content_digest'], r'^[0-9a-f]{64}$')
            self.assertTrue(refs[kind]['under_cutoff'])

    def test_the_sentences_are_the_pages_templates_over_the_book_records(self):
        text = self.answer['text']
        self.assertIn(self.records['exposure']['content_digest'], text)
        self.assertIn('The uncovered volume in the window is 95.244 MWh.', text)
        self.assertIn(BOOK_LABEL, text)
        self.assertIn(self.records['book_impact']['materiality']['statement'], text)
        self.assertIn(V1, text)
        fields = canonical_dumps([part['fields'] for part in self.answer['components']])
        for figure in re.findall(r'\d+(?:\.\d+)?', text):
            self.assertIn(figure, fields, figure)

    def test_an_outlook_answer_rests_on_no_book_record(self):
        answer = answer_question('What does this trip do to the outlook?', self.records, LATE,
                                 fixture_backend())
        # One outlook reference per archive vintage the cutoff admits (BOOK-3 added the Luzon
        # and Mindanao vintages beside the two Visayas ones), and no book record.
        vintages = [vintage['outlook_id'] for vintage in self.records['outlook']['outlooks']]
        self.assertIn(V1, vintages)
        self.assertIn(V2, vintages)
        self.assertEqual(['event'] + ['outlook'] * len(vintages) + ['impact', 'judgment'],
                         [ref['record'] for ref in answer['receipt']['records']])
        self.assertFalse(set(BOOK_COMPONENTS) & {part['component'] for part in answer['components']})
        # The manifest still lists the book records the cutoff admits, so an action may name them.
        rendered = render_request('What does this trip do to the outlook?', self.records, LATE)
        self.assertEqual({'exposure', 'book_impact'},
                         {ref['record'] for ref in rendered['request']['manifest']['records']}
                         & {'exposure', 'book_impact'})


class QuotablePaths(unittest.TestCase):
    """A book figure reaches a view only through a quotable path, copied by code."""

    def setUp(self):
        self.records = visayas_records()
        self.rendered = render_request(EXPOSURE_QUESTION, self.records, LATE)
        self.request = self.rendered['request']
        self.plan = fixture_backend().decide(self.request)['plans']['f0']

    def refused(self, plan):
        with self.assertRaises(PlanRefused) as caught:
            validate_response(self.request, {'plans': plans_for(plan),
                                             'model_version': 'fixture-view-1'})
        return caught.exception.rule

    def test_every_figure_a_component_carries_is_at_a_quotable_path(self):
        parts = components_of(compose(self.records, self.request,
                                      *validate_response(self.request, {
                                          'plans': plans_for(self.plan),
                                          'model_version': 'fixture-view-1'}),
                                      fixture_backend()))
        for name in BOOK_COMPONENTS:
            allowed = set(QUOTABLE_PATHS[name])
            for path in numeric_paths(parts[name]['fields']):
                if path.startswith('window.') or path.startswith('vintage.'):
                    continue  # the window's hours and counts, never a book figure
                head = path.split('.')[0]
                self.assertTrue(path in allowed or head in allowed, (name, path))
            dumped = canonical_dumps(parts[name]['fields'])
            for key in UNQUOTABLE:
                self.assertNotIn('"' + key + '"', dumped, (name, key))

    def test_a_plan_that_quotes_a_book_figure_is_refused(self):
        # A quote of a book figure, quotable or not, has no slot in a plan: a reason key, a
        # component argument, an action argument or a component name are all refused.
        plan = copy.deepcopy(self.plan)
        plan['not_shown'][0]['reason_key'] = '{{exposure.rows.demand_mw}}'
        self.assertEqual('REASON_NOT_IN_CATALOGUE: {{exposure.rows.demand_mw}}', self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['not_shown'][0]['reason_key'] = '{{exposure.totals.uncovered_mwh}}'
        self.assertEqual('REASON_NOT_IN_CATALOGUE: {{exposure.totals.uncovered_mwh}}',
                         self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['components'][0]['args'] = {'quote': 'rows_demand_mw'}
        self.assertEqual('COMPONENT_ARGUMENT_NOT_IN_MANIFEST: exposure_table', self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['components'][1]['args'] = {'figure': 'band_php_mwh'}
        self.assertEqual('COMPONENT_ARGUMENT_NOT_IN_MANIFEST: account_impact', self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['components'][0]['args'] = {'uncovered_mwh': 'ninety five'}
        self.assertEqual('COMPONENT_ARGUMENT_NOT_IN_MANIFEST: exposure_table', self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['components'][0]['component'] = 'exposure_table.rows.demand_mw'
        self.assertEqual('COMPONENT_NOT_IN_CATALOGUE: exposure_table.rows.demand_mw',
                         self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['actions'] = [{'action': 'query_exposure', 'reason_key': 'runs_the_query',
                            'args': {'account_ids': ['{{exposure.totals.uncovered_mwh}}']}}]
        self.assertEqual('ARGUMENT_NOT_A_REFERENCE: account_ids', self.refused(plan))

    def test_a_book_figure_written_as_a_number_is_refused(self):
        plan = copy.deepcopy(self.plan)
        plan['components'][0]['args'] = {'uncovered_mwh': 95.244}
        self.assertEqual('NUMERAL_IN_PLAN: plan.components[].args.uncovered_mwh',
                         self.refused(plan))
        plan = copy.deepcopy(self.plan)
        plan['not_shown'][0]['reason_key'] = 'p50_php'
        self.assertEqual('NUMERAL_IN_PLAN: plan.not_shown[].reason_key', self.refused(plan))

    def test_the_book_sentences_quote_only_the_stated_paths(self):
        quote = re.compile(r'\{\{([a-z_]+)\.([a-z0-9_.]+)\}\}')
        used = {}
        for _component, template in BOOK_TEXT_TEMPLATES:
            for kind, path in quote.findall(template):
                used.setdefault(kind, set()).add(path)
        self.assertEqual({kind: set(paths) for kind, paths in BOOK_TEXT_PATHS.items()}, used)
        component_of = {'exposure': 'exposure_table', 'book_impact': 'account_impact'}
        for kind, paths in used.items():
            figures = {path for path in paths
                       if path not in ('content_digest', 'label', 'vintage.outlook_id')}
            quotable = {item.replace('[]', '') for item in QUOTABLE_PATHS[component_of[kind]]}
            for path in figures:
                self.assertTrue(path in quotable or path.split('.')[0] in quotable, path)

    def test_a_book_component_the_request_does_not_offer_is_refused(self):
        records = build.plan_records()
        del records['exposure']
        rendered = render_request(EXPOSURE_QUESTION, records, build.PLAN_CUTOFF)
        self.assertEqual(list(CATALOGUE), rendered['request']['catalogue'])
        plan = copy.deepcopy(view.FIXTURE_PLANS['exposure'])
        plan['components'].insert(0, {'component': 'exposure_table', 'args': {}})
        with self.assertRaises(PlanRefused) as caught:
            validate_response(rendered['request'], {'plans': plans_for(plan),
                                                    'model_version': 'fixture-view-1'})
        self.assertEqual('COMPONENT_NOT_IN_CATALOGUE: exposure_table', caught.exception.rule)
        # Without the book, the fixture planner's exposure plan is DOCK-1's, unchanged.
        response = fixture_backend().decide(rendered['request'])
        self.assertEqual(view.FIXTURE_PLANS['exposure'], response['plans']['f0'])

    def test_a_book_record_computed_after_the_view_cutoff_is_not_offered(self):
        early = '2026-10-15T00:00:00Z'
        records = build.plan_records()  # its exposure record is read at the plan cutoff, 17 October
        rendered = render_request(EXPOSURE_QUESTION, records, early)
        manifest = {item['component']: item for item in rendered['request']['manifest']['components']}
        self.assertFalse(manifest['exposure_table']['available'])
        self.assertEqual('not_in_cutoff', manifest['exposure_table']['reason_key'])
        plan = copy.deepcopy(view.FIXTURE_PLANS['exposure'])
        plan['components'].insert(0, {'component': 'exposure_table', 'args': {}})
        with self.assertRaises(PlanRefused) as caught:
            validate_response(rendered['request'], {'plans': plans_for(plan),
                                                    'model_version': 'fixture-view-1'})
        self.assertEqual('COMPONENT_UNAVAILABLE: exposure_table', caught.exception.rule)
        answer = answer_question(EXPOSURE_QUESTION, records, early, fixture_backend())
        self.assertEqual('composed', answer['status'])
        self.assertIn({'component': 'exposure_table',
                       'reason': 'No exposure record of the synthetic book exists at or before '
                                 'the view cutoff.'}, answer['not_shown'])
        self.assertNotIn('exposure', [ref['record'] for ref in answer['receipt']['records']])
        # A vintage issued after the view cutoff: the impact card is not offered either.
        records = visayas_records()
        rendered = render_request(EXPOSURE_QUESTION, records, '2026-10-18T03:00:00Z')
        manifest = {item['component']: item for item in rendered['request']['manifest']['components']}
        self.assertTrue(manifest['exposure_table']['available'])
        self.assertTrue(manifest['account_impact']['available'])  # V1 was issued at 02:00Z
        later = visayas_records(impact=V2)
        rendered = render_request(EXPOSURE_QUESTION, later, '2026-10-18T03:00:00Z')
        manifest = {item['component']: item for item in rendered['request']['manifest']['components']}
        self.assertFalse(manifest['account_impact']['available'])  # V2 was issued at 06:00Z

    def test_a_malformed_book_record_is_a_caller_error(self):
        records = visayas_records()
        records['exposure'] = dict(records['exposure'], label='')
        with self.assertRaises(ValueError):
            render_request(EXPOSURE_QUESTION, records, LATE)
        records = visayas_records()
        records['exposure']['rows'][0]['uncovered_mwh'] = 0.0
        with self.assertRaises(ValueError):  # the stamped digest no longer recomputes
            render_request(EXPOSURE_QUESTION, records, LATE)
        records = visayas_records()
        impact = dict(records['book_impact'])
        impact.pop('materiality')
        impact['materiality'] = records['book_impact']['materiality']
        records['book_impact'] = impact
        with self.assertRaises(ValueError):  # the materiality line is no longer first
            render_request(EXPOSURE_QUESTION, records, LATE)

    def test_a_changed_impact_figure_under_the_original_record_id_is_refused(self):
        # Rework round 1, review finding 1: the impact record id is recomputed, as the
        # exposure record's is, so a changed p50 cannot be shown under the original id.
        records = visayas_records()
        impact = copy.deepcopy(records['book_impact'])
        impact['accounts'][0]['p50_php'] = 999999.99
        impact['totals']['p50_php'] = 999999.99
        self.assertEqual(records['book_impact']['content_digest'], impact['content_digest'])
        records['book_impact'] = impact
        with self.assertRaises(ValueError) as caught:
            render_request(EXPOSURE_QUESTION, records, LATE)
        self.assertIn('does not match its content digest', str(caught.exception))
        with self.assertRaises(ValueError):
            answer_question(EXPOSURE_QUESTION, records, LATE, fixture_backend())


class TheManifestCarriesIdentifiersNeverValues(unittest.TestCase):

    def test_the_manifest_offers_the_accounts_nodes_windows_and_vintages_by_reference(self):
        records = visayas_records()
        ids = adapter().manifest_ids(records['exposure'])
        self.assertEqual({'accounts': ['ACC-VIS01', 'ACC-VIS02', 'ACC-VIS03'],
                          'nodes': ['NODE-VIS01', 'NODE-VIS02', 'NODE-VIS03', 'NODE-VIS04',
                                    'NODE-VIS05'],
                          'windows': [WINDOW]}, ids)
        rendered = render_request(EXPOSURE_QUESTION, records, LATE, ids=ids)
        offered = rendered['request']['manifest']['actions']['ids']
        self.assertEqual(ids['accounts'], [entry['id'] for entry in offered['accounts']])
        self.assertEqual(ids['nodes'], [entry['id'] for entry in offered['nodes']])
        self.assertEqual([WINDOW], [entry['id'] for entry in offered['windows']])
        # Every archive vintage is offered by reference, in the archive's order; the two Visayas
        # vintages are among them whatever other regions the archive holds (BOOK-3 added two).
        offered_vintages = [entry['id'] for entry in offered['outlooks']]
        self.assertEqual(list(OutlookArchive(ARCHIVE).issue_ids()), offered_vintages)
        self.assertLessEqual({V1, V2}, set(offered_vintages))
        self.assertEqual(list(COMPONENTS), rendered['request']['catalogue'])
        manifest = canonical_dumps(rendered['request']['manifest'])
        figures = set()
        for kind in ('exposure', 'book_impact'):
            figures |= {str(value) for value in _numbers(records[kind]) if value not in (0, 1, 2)}
        for figure in sorted(figures):
            self.assertNotIn(':' + figure + ',', manifest, figure)
            self.assertNotIn(':' + figure + '}', manifest, figure)
        self.assertNotIn('95.244', manifest)
        self.assertNotIn('8679.93', manifest)


def _numbers(value):
    if type(value) is dict:
        for child in value.values():
            yield from _numbers(child)
    elif type(value) is list:
        for child in value:
            yield from _numbers(child)
    elif type(value) in (int, float) and type(value) is not bool:
        yield value


class WindowIdentifiers(unittest.TestCase):
    """Rework round 1, review finding 4: a window reaches the manifest only as a window id."""

    HOSTILE = ('95.244 MWh uncovered', 'tomorrow-afternoon', '2026-10-19T13:00',
               '2026-10-19T15:00/2026-10-19T13:00', '2026-10-19T13:30/2026-10-19T15:00',
               '2026-10-19 13:00/2026-10-19 15:00', 'a/b', '2026-10-19T13:00/2026-10-19T15:00/x')

    def test_the_manifest_refuses_a_window_that_is_not_a_window_identifier(self):
        records = visayas_records()
        for hostile in self.HOSTILE:
            with self.subTest(window=hostile):
                with self.assertRaises(ValueError):
                    render_request(EXPOSURE_QUESTION, records, LATE,
                                   ids={'accounts': ['ACC-VIS01'], 'windows': [hostile]})
        rendered = render_request(EXPOSURE_QUESTION, records, LATE,
                                  ids={'accounts': ['ACC-VIS01'], 'windows': [WINDOW]})
        self.assertEqual([WINDOW], [entry['id'] for entry in
                                    rendered['request']['manifest']['actions']['ids']['windows']])

    def test_the_adapter_round_trips_every_window_it_offers(self):
        book = adapter()
        for hostile in self.HOSTILE:
            with self.subTest(window=hostile):
                with self.assertRaises(ValueError):
                    book.manifest_ids(windows=[hostile])
        self.assertEqual([WINDOW, '2026-10-19T00:00/2026-10-20T00:00'],
                         book.manifest_ids(windows=[WINDOW, Window(
                             Window.between('2026-10-19T00:00', '2026-10-20T00:00').day, 0, 24)])
                         ['windows'])


class TheVisayasExposureQuestion(unittest.TestCase):
    """The strategy's question composes the table from src/book, by record id, labelled."""

    PLAN = {
        'status': 'composed',
        'components': [{'component': 'exposure_table', 'args': {}},
                       {'component': 'account_impact', 'args': {}},
                       {'component': 'belief_card', 'args': {}},
                       {'component': 'receipt', 'args': {}}],
        'actions': [
            {'action': 'query_exposure', 'reason_key': 'runs_the_query',
             'args': {'account_ids': ['account-a', 'account-b', 'account-c'],
                      'node_ids': ['node-a', 'node-b', 'node-c', 'node-d', 'node-e'],
                      'window': 'window-a', 'cutoff': 'cutoff-a'}},
            {'action': 'query_impact', 'reason_key': 'runs_the_query',
             'args': {'account_ids': ['account-a', 'account-b', 'account-c'],
                      'outlook_id': 'outlook-a', 'window': 'window-a', 'cutoff': 'cutoff-a'}},
        ],
        'not_shown': [{'component': 'event_timeline', 'reason_key': 'not_asked'},
                      {'component': 'outlook_vintages', 'reason_key': 'covered_elsewhere'}],
    }

    def setUp(self):
        self.book = adapter()
        self.records = visayas_records()
        self.ids = self.book.manifest_ids(self.records['exposure'])
        # The plan names the Visayas vintage V1 by the handle the manifest gives it. The handles
        # follow the archive's order, so the letter depends on which other regions' vintages the
        # archive holds (BOOK-3 added two that sort before it); the plan reads it, never guesses.
        rendered = render_request(VISAYAS, self.records, LATE, free_text=True, repeats=3,
                                  ids=self.ids)
        handle = next(entry['ref'] for entry in
                      rendered['request']['manifest']['actions']['ids']['outlooks']
                      if entry['id'] == V1)
        self.plan = copy.deepcopy(self.PLAN)
        self.plan['actions'][1]['args']['outlook_id'] = handle
        self.answer = answer_question(VISAYAS, self.records, LATE, FixtureView({'free': self.plan}),
                                      free_text=True, repeats=3, ids=self.ids)
        self.parts = components_of(self.answer)

    def test_the_question_composes_the_table_with_no_model(self):
        self.assertEqual('composed', self.answer['status'])
        self.assertEqual(VISAYAS, self.answer['question'])
        self.assertEqual('repeats', self.answer['receipt']['stability']['basis'])
        self.assertIs(True, self.answer['receipt']['stability']['stable'])
        self.assertEqual('synthetic_fixture', self.answer['receipt']['execution_mode'])
        self.assertEqual(['exposure_table', 'account_impact', 'belief_card', 'receipt'],
                         [part['component'] for part in self.answer['components']])

    def test_every_figure_of_the_table_is_src_book_s_by_record_id(self):
        record = exposure(load_book(), parse_window(WINDOW), LATE, region='Visayas')
        record_id = compute_content_digest(record)
        fields = self.parts['exposure_table']['fields']
        self.assertEqual(record_id, fields['record_id'])
        refs = {ref['record']: ref for ref in self.answer['receipt']['records']}
        self.assertEqual(record_id, refs['exposure']['record_id'])
        rows = by_cell(record['rows'])
        self.assertEqual(10, len(fields['rows']))  # three accounts, five nodes, two hours
        for row in fields['rows']:
            self.assertEqual(rows[(row['account_id'], row['node_id'], row['hour_start'])]
                             ['uncovered_mwh'], row['uncovered_mwh'])
            self.assertEqual(BOOK_LABEL, row['label'])
        self.assertEqual({'ACC-VIS01': 51.602, 'ACC-VIS02': 36.838, 'ACC-VIS03': 6.804},
                         {block['account_id']: block['uncovered_mwh'] for block in fields['accounts']})
        self.assertEqual(record['totals']['uncovered_mwh'], fields['totals']['uncovered_mwh'])

    def test_the_impact_card_is_src_book_s_by_record_id(self):
        accounts = ['ACC-VIS01', 'ACC-VIS02', 'ACC-VIS03']
        record = query_impact(load_book(), ARCHIVE, V1, outlook(V1)['content_digest'],
                              parse_window(WINDOW), LATE, MaterialityPolicy(), accounts=accounts)
        fields = self.parts['account_impact']['fields']
        self.assertEqual(record['content_digest'], fields['record_id'])
        self.assertEqual({block['account_id']: (block['p10_php'], block['p50_php'], block['p90_php'])
                          for block in record['accounts']},
                         {block['account_id']: (block['p10_php'], block['p50_php'], block['p90_php'])
                          for block in fields['accounts']})
        self.assertEqual(80477.01, fields['totals']['p50_php'])  # BOOK-2's worked example

    def test_the_synthetic_label_is_on_the_view_and_in_the_receipt(self):
        self.assertIn(BOOK_LABEL, self.answer['text'])
        receipt_labels = {item['record']: item for item in self.answer['receipt']['labels']}
        self.assertEqual(BOOK_LABEL, receipt_labels['exposure']['label'])
        self.assertIs(True, receipt_labels['exposure']['synthetic'])
        self.assertIs(True, receipt_labels['book_impact']['synthetic'])
        self.assertEqual(self.answer['labels'], self.answer['receipt']['labels'])

    def test_the_proposed_queries_resolve_to_the_same_records_through_the_adapter(self):
        block = self.answer['receipt']['actions']
        self.assertEqual([], block['refused'])
        self.assertEqual([], block['run'])  # the composer runs nothing
        exposure_args = block['proposed'][0]['resolved']
        impact_args = block['proposed'][1]['resolved']
        self.assertEqual({'account_ids': ['ACC-VIS01', 'ACC-VIS02', 'ACC-VIS03'],
                          'node_ids': ['NODE-VIS01', 'NODE-VIS02', 'NODE-VIS03', 'NODE-VIS04',
                                       'NODE-VIS05'],
                          'window': WINDOW, 'cutoff': LATE}, exposure_args)
        self.assertEqual({'account_ids': ['ACC-VIS01', 'ACC-VIS02', 'ACC-VIS03'],
                          'outlook_id': V1, 'window': WINDOW, 'cutoff': LATE}, impact_args)
        ran = self.book.exposure(**exposure_args)
        self.assertEqual('answered', ran['status'])
        self.assertEqual(self.parts['exposure_table']['fields']['record_id'], ran['record_id'])
        priced = self.book.impact(**impact_args)
        self.assertEqual('answered', priced['status'])
        self.assertEqual(self.parts['account_impact']['fields']['record_id'], priced['record_id'])
        self.assertEqual(outlook(V1)['content_digest'], priced['vintage']['outlook_digest'])


class TheTwoActionsThroughTheAdapter(unittest.TestCase):
    """query_exposure and query_impact give identifiers and refuse BOOK-2's cases by code."""

    def setUp(self):
        self.book = adapter()

    def test_the_catalogue_entries_carry_what_book_two_needs(self):
        self.assertEqual({'account_ids', 'node_ids', 'window', 'cutoff'},
                         set(ACTIONS['query_exposure']['args']))
        self.assertEqual({'account_ids', 'outlook_id', 'window', 'cutoff'},
                         set(ACTIONS['query_impact']['args']))
        self.assertEqual(('account_ids', 'outlook_id', 'window', 'cutoff'),
                         ACTIONS['query_impact']['required'])
        for name in ('query_exposure', 'query_impact'):
            self.assertFalse(ACTIONS[name]['writes'])
            self.assertFalse(ACTIONS[name]['sign_in'])
        rendered = render_request(EXPOSURE_QUESTION, visayas_records(), LATE,
                                  ids=self.book.manifest_ids(visayas_records()['exposure']))
        manifest = rendered['request']['manifest']['actions']
        resolved, refusal = check_action(
            {'action': 'query_impact', 'reason_key': 'runs_the_query',
             'args': {'account_ids': ['account-a'], 'outlook_id': 'outlook-b'}}, manifest)
        self.assertEqual('argument_not_in_manifest', refusal)  # no window, no cutoff

    def test_an_exposure_answer_names_its_record_and_window(self):
        answer = self.book.exposure(['ACC-VIS03'], ['NODE-VIS03'], WINDOW, LATE)
        self.assertEqual('answered', answer['status'])
        self.assertEqual('BookExposure', answer['kind'])
        self.assertRegex(answer['record_id'], r'^[0-9a-f]{64}$')
        self.assertEqual(compute_content_digest(answer['record']), answer['record_id'])
        self.assertIs(True, answer['synthetic'])
        self.assertEqual(BOOK_LABEL, answer['label'])
        self.assertEqual(6.804, answer['record']['totals']['uncovered_mwh'])
        self.assertEqual(WINDOW, window_id(Window.between('2026-10-19T13:00', '2026-10-19T15:00')))

    def test_an_impact_answer_names_the_vintage_digest_window_cutoff_and_line(self):
        answer = self.book.impact(['ACC-VIS03'], V2, WINDOW, LATE)
        self.assertEqual('answered', answer['status'])
        self.assertEqual('BookImpact', answer['kind'])
        verify_record(answer['record'])
        self.assertEqual(answer['record']['content_digest'], answer['record_id'])
        self.assertEqual({'outlook_id': V2, 'outlook_digest': outlook(V2)['content_digest'],
                          'values_sha256': outlook(V2)['values_ref']['sha256']}, answer['vintage'])
        self.assertEqual(WINDOW, answer['window'])
        self.assertEqual(LATE, answer['cutoff'])
        self.assertEqual(1_000_000.0, answer['materiality']['threshold_php'])
        self.assertEqual('materiality', next(iter(answer['record'])))
        # The band is the archive's, tied by digest (BOOK-2 review, note C).
        band = load_vintage(ARCHIVE, V2, outlook(V2)['content_digest'])
        self.assertEqual(band.reference(), answer['record']['vintage'])

    def assertRefused(self, answer, code):
        self.assertEqual('refused', answer['status'], answer)
        self.assertEqual(code, answer['code'])
        self.assertEqual(code.lower(), answer['reason_key'])
        self.assertIsNone(answer['record_id'])
        self.assertIs(True, answer['synthetic'])
        self.assertEqual({'status', 'code', 'reason_key', 'record_id', 'synthetic', 'label'},
                         set(answer))

    def test_book_two_s_refusals_are_stable_codes(self):
        self.assertRefused(self.book.impact(['ACC-VIS03'], 'book-demo-none', WINDOW, LATE),
                           'VINTAGE_UNKNOWN')
        self.assertRefused(self.book.impact(['ACC-VIS03'], V1, '2026-10-20T13:00/2026-10-20T15:00',
                                            LATE), 'WINDOW_OUTSIDE_VINTAGE')
        self.assertRefused(self.book.impact(['ACC-VIS03'], V1, WINDOW, '2026-10-17T00:00:00Z'),
                           'VINTAGE_AFTER_CUTOFF')
        self.assertRefused(self.book.exposure(['ACC-VIS03'], ['NODE-VIS03'],
                                              '2026-10-19T23:00/2026-10-20T01:00', LATE),
                           'WINDOW_OUTSIDE_PROFILE')
        self.assertRefused(self.book.exposure(['ACC-VIS03'], ['NODE-VIS03'], WINDOW, '2020-01-01'),
                           'CUTOFF_BEFORE_TERM_START')
        self.assertRefused(self.book.impact(['ACC-VIS03'], V1, WINDOW, '2020-01-01'),
                           'VINTAGE_AFTER_CUTOFF')
        self.assertRefused(self.book.exposure(['ACC-NONE'], ['NODE-VIS03'], WINDOW, LATE),
                           'UNKNOWN_ACCOUNT')
        self.assertRefused(self.book.exposure([], ['NODE-VIS03'], WINDOW, LATE), 'ARGUMENT_INVALID')

    def test_a_window_or_cutoff_the_service_does_not_pass_is_refused_never_defaulted(self):
        # The agent service calls ``book.impact(account_ids, outlook_id)`` today (DOCK-3); the
        # adapter refuses rather than guess a window (hand-back to DOCK-5).
        self.assertRefused(self.book.impact(['ACC-VIS03'], V1), 'WINDOW_REQUIRED')
        self.assertRefused(self.book.impact(['ACC-VIS03'], V1, WINDOW), 'CUTOFF_REQUIRED')
        self.assertRefused(self.book.exposure(['ACC-VIS03'], ['NODE-VIS03'], None, LATE),
                           'WINDOW_REQUIRED')
        self.assertRefused(self.book.exposure(['ACC-VIS03'], ['NODE-VIS03'], 'tomorrow', LATE),
                           'WINDOW_INVALID')

    def test_a_band_that_does_not_tie_to_its_record_is_refused(self):
        with scratch_directory() as temp:
            where = Path(temp)
            tampered = where / 'values.json'
            data = bytearray((ARCHIVE / 'values' / f'{V1}.json').read_bytes())
            data[-2] = ord(' ') if data[-2] != ord(' ') else ord('\t')
            tampered.write_bytes(bytes(data))
            fields = {key: value for key, value in outlook(V1).items()
                      if key not in ('content_digest', 'schema_version', 'kind')}
            fields['values_ref'] = dict(fields['values_ref'], path_hint=str(tampered))
            OutlookArchive(where / 'archive').issue(build_outlook(**fields))
            book = BookAdapter(MaterialityPolicy(), archive_root=where / 'archive')
            self.assertRefused(book.impact(['ACC-VIS03'], V1, WINDOW, LATE), 'BAND_DIGEST_MISMATCH')
            self.assertRefused(book.impact(['ACC-VIS03'], V2, WINDOW, LATE), 'VINTAGE_UNKNOWN')

    def test_no_figure_is_written_without_a_stated_line(self):
        from src.book.impact import BookImpactError
        with self.assertRaises(BookImpactError) as caught:
            BookAdapter(None)
        self.assertEqual('POLICY_REQUIRED', caught.exception.code)

    def test_the_adapter_runs_under_the_agent_service(self):
        from src.agent.service import AgentService
        from src.agent.store import MemoryAgentStore
        records = visayas_records()
        plan = copy.deepcopy(view.FIXTURE_PLANS['exposure'])
        plan['actions'] = copy.deepcopy(TheVisayasExposureQuestion.PLAN['actions'][:1])
        backend = FixtureView(dict(view.FIXTURE_PLANS, exposure=plan),
                              book_kinds=view.FIXTURE_BOOK_KINDS)
        service = AgentService(MemoryAgentStore(), records=lambda case, page, cutoff: records,
                               recorded_backend=backend,
                               book=self.book,
                               ids=lambda owner, case, page: self.book.manifest_ids(records['exposure']))
        out = service.ask(None, {'question': EXPOSURE_QUESTION, 'thread': 'desk',
                                 'page_key': 'home', 'cutoff': LATE})
        self.assertEqual('composed', out['view']['status'])
        receipt = out['actions_run'][0]
        self.assertEqual(('query_exposure', 'done'), (receipt['action'], receipt['outcome']))
        result = out['results'][receipt['receipt_id']]
        self.assertEqual('answered', result['status'])
        table = components_of(out['view'])['exposure_table']['fields']
        self.assertEqual(table['record_id'], result['record_id'])
        self.assertEqual([{'kind': 'exposure', 'id': table['record_id'], 'synthetic': True}],
                         receipt['record_refs'])

    def test_the_adapter_imports_no_web_layer(self):
        tree = ast.parse(Path(book_adapter.__file__).read_text(encoding='utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(('.' * node.level) + (node.module or ''))
        allowed = {'__future__', 'datetime', 'pathlib', 'src.contracts.jsonutil',
                   'src.outlook.records', 'src.price.impact', '.exposure', '.impact', '.records'}
        self.assertEqual(set(), names - allowed)


class TheFixtureBake(unittest.TestCase):
    """Every page key's plan set carries the book's exposure answer, the composer's own."""

    def test_every_page_key_s_exposure_answer_shows_the_exposure_table(self):
        views = build.plan_views()
        exposure_answer = views[2]
        self.assertEqual(EXPOSURE_QUESTION, exposure_answer['question'])
        self.assertEqual('exposure_table', exposure_answer['components'][0]['component'])
        record = build.plan_exposure()
        self.assertEqual(record['content_digest'],
                         exposure_answer['components'][0]['fields']['record_id'])
        self.assertIn({'component': 'account_impact',
                       'reason': 'No impact record of the synthetic book is among this view '
                                 'inputs.'}, exposure_answer['not_shown'])
        for key in build.PLAN_KEYS:
            baked = json.loads((ROOT / 'tests' / 'fixtures' / 'grid' / 'catalog' / 'bake' / 'views'
                                / f'{key}.json').read_text(encoding='utf-8'))['views']
            self.assertEqual(canonical_dumps(views), canonical_dumps(baked), key)
            self.assertEqual(3, len(baked), key)

    def test_the_bake_reads_the_region_and_window_of_the_strategy_s_question(self):
        record = build.plan_exposure()
        self.assertEqual('2026-10-17', record['cutoff'])
        self.assertEqual(['ACC-VIS01', 'ACC-VIS02', 'ACC-VIS03'],
                         [block['account_id'] for block in record['accounts']])
        self.assertEqual(stamp_exposure(record), record)
        # No vintage is issued by the plan cutoff, so the bake prices no impact.
        self.assertEqual('VINTAGE_AFTER_CUTOFF',
                         build.book_adapter().impact(['ACC-VIS01'], V1, build.BOOK_WINDOW,
                                                     build.PLAN_CUTOFF)['code'])


if __name__ == '__main__':
    unittest.main()
