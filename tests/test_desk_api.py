"""UX-B: the desk API (src/desk) over the committed page fixture, and the `/grid-data` views fix.

Contract: docs/work/ui-refinement-2026-10-18/desk-api.md. Every record here is SYNTHETIC: the page
fixture (tests/fixtures/grid/page/data: seven sites, one day, Visayas at 32,000 from 13:40) and the
catalog fixture bake (tests/fixtures/grid/catalog/bake: the year bake's shape, days/ and
advisories/ and replay.json). Offline and fast. The HTTP checks need FastAPI and skip without it;
the composer checks run on the standard library alone.

What is held:
* the four routes answer the contract's shapes, `no-store`, and 404 `{"error": "NOT_FOUND"}` for
  an unknown preview;
* nothing later than `at` is returned: no record, interval, spark point or citation;
* every `num` part cites a citation whose table shows the same figure, and every table block's
  cells are the cited table's cells;
* the authored copy keeps the repository's rules (20 words or fewer, no em dash, no semicolon);
* every offered prompt has a substantive answer at the clock;
* free text reaches the right intent;
* a data directory missing the optional files answers empty sections, never a 500;
* `/grid-data/views/<key>.json` (the ask dock's recorded plan sets) is served (regression).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.desk import answer as answers  # noqa: E402
from src.desk import search as searching  # noqa: E402
from src.desk.bake import Bake  # noqa: E402

try:
    from fastapi.testclient import TestClient
    FASTAPI = True
except ImportError:
    FASTAPI = False

PAGE = ROOT / 'tests' / 'fixtures' / 'grid' / 'page' / 'data'
CATALOG_BAKE = ROOT / 'tests' / 'fixtures' / 'grid' / 'catalog' / 'bake'
# The showcase bake is local only (never committed): here, or wherever DESK_SHOWCASE_DIR names it.
SHOWCASE = Path(os.environ.get('DESK_SHOWCASE_DIR') or ROOT / '.local' / 'showcase' / 'grid-data')
AT = '2026-09-21T13:40'
EARLY = '2026-09-21T13:00'
CLOCKS = ('2026-09-21T00:00', '2026-09-21T09:30', EARLY, AT, '2026-09-21T14:30', '2026-09-21T23:55')
TIME = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}')
NUMBER = re.compile(r'-?\d[\d,]*(?:\.\d+)?')
INTENT_CALLS = (('region_price_why', 'CLUZ'), ('region_price_why', 'CVIS'), ('region_price_why', 'CMIN'),
                ('unusual_nodes', None), ('hvdc_congestion', None), ('plant_status', 'SYN-BAY-2'),
                ('plant_status', 'SYN-LUZ-1'), ('recent_events', None), ('recent_events', 'CVIS'),
                ('grid_overview', None))


def times_in(value):
    """Every `YYYY-MM-DDTHH:MM` the payload carries, anywhere, normalised."""
    text = json.dumps(value, ensure_ascii=False)
    return [m.replace(' ', 'T') for m in TIME.findall(text)]


def cells(citation):
    return {cell for row in citation['table']['rows'] for cell in row}


class Invariants:
    """The checks every answer is held to, on any bake."""

    def check_answer(self, result, at):
        by_n = {c['n']: c for c in result['citations']}
        self.assertEqual(list(range(1, len(by_n) + 1)), sorted(by_n), 'citations are numbered 1..n')
        for c in result['citations']:
            self.assertTrue(c['dataset_id'] and c['href'] == '/data#' + c['dataset_id'], c)
            self.assertLessEqual(c['at'], at, c)
            self.assertTrue(all(len(row) == len(c['table']['columns']) for row in c['table']['rows']), c)
        for block in result['blocks']:
            if block['type'] == 'p':
                for part in block['parts']:
                    if part['t'] == 'num':
                        self.assertTrue(part['cite'], part)
                        figure = NUMBER.search(part['v']).group(0)
                        self.assertTrue(any(figure in cells(by_n[n]) for n in part['cite']),
                                        f"{part['v']} is not in the table of citation {part['cite']}")
                    elif part['t'] == 'text':
                        self.assertNotRegex(part['v'], r'\d{3,}|\d,\d', 'a figure in prose must be a num part')
                self.check_copy(''.join(p.get('v') or p.get('label') or '' for p in block['parts']))
            else:
                self.assertEqual('table', block['type'])
                self.assertTrue(block['cite'], block)
                cited = set().union(*(cells(by_n[n]) for n in block['cite']))
                for row in block['rows']:
                    self.assertEqual(len(block['columns']), len(row))
                    for cell in row:
                        label = cell['label'] if isinstance(cell, dict) else cell
                        self.assertIn(label, cited, f'{label!r} of {block["caption"]!r} is not in its citations')
        entities = {(e['kind'], e['id']) for e in result['entities']}
        for block in result['blocks']:
            parts = block.get('parts') or [c for row in block.get('rows', []) for c in row if isinstance(c, dict)]
            for part in parts:
                if isinstance(part, dict) and part.get('t') == 'entity':
                    self.assertIn((part['kind'], part['id']), entities, part)
        for step in result['trace']:
            self.assertIn(step['op'], ('resolve', 'read', 'relate', 'compare'), step)
            if step['op'] == 'relate':
                self.assertIn(step['relation'], ('locatedIn', 'partOf', 'connects', 'refersTo'), step)
            if step.get('type'):
                self.assertIn(step['type'], ('Region', 'Plant', 'MarketResource', 'NetworkElement', 'Evidence'), step)
        self.assertNotIn('tool', json.dumps(result['trace']).lower(), 'the trace names no tool')
        for t in times_in(result):
            self.assertLessEqual(t, at, 'nothing later than the clock')
        self.assertIn('No model call', result['basis'])

    def check_copy(self, sentence_block):
        self.assertNotIn('—', sentence_block)
        self.assertNotIn(';', sentence_block)
        for sentence in re.split(r'(?<=[.?!])\s+', sentence_block.strip()):
            self.assertLessEqual(len(sentence.split()), 20, sentence)


class Composer(Invariants, unittest.TestCase):
    """The composer over the page fixture, without HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.bake = Bake(PAGE)

    def test_every_intent_at_every_clock_keeps_the_invariants(self):
        for at in CLOCKS:
            for intent, entity in INTENT_CALLS:
                with self.subTest(at=at, intent=intent, entity=entity):
                    result = answers.compose(self.bake, at, 'q', intent, entity).result()
                    self.assertEqual('answered', result['status'])
                    self.assertTrue(result['blocks'])
                    self.check_answer(result, at)

    def test_visayas_at_the_cap(self):
        result = answers.answer(self.bake, AT, 'why is visayas so expensive')
        self.assertEqual(('answered', 'region_price_why'), (result['status'], result['intent']))
        first = result['blocks'][0]['parts']
        self.assertEqual({'t': 'entity', 'kind': 'region', 'id': 'CVIS', 'label': 'Visayas'}, first[0])
        self.assertEqual('₱32,000/MWh', [p for p in first if p['t'] == 'num'][0]['v'])
        self.assertEqual(['resolve', 'read'], [s['op'] for s in result['trace'][:2]])
        self.assertEqual('Region', result['trace'][0]['type'])
        relations = [s['relation'] for s in result['trace'] if s['op'] == 'relate']
        self.assertEqual(['connects', 'refersTo', 'locatedIn'], relations)
        # the trip at 13:40 is named in prose, and the notice after the clock is not there
        kinds = {(e['kind'], e['id']) for e in result['entities']}
        self.assertIn(('event', 'syn-bay-unit-2-trip'), kinds)
        self.assertNotIn(('notice', 'SYN-ADV-0003'), kinds)  # 13:45
        # the trip's own notice (SYN-ADV-0002) is carried by the event's row, not listed twice
        self.assertNotIn(('notice', 'SYN-ADV-0002'), kinds)
        self.assertEqual({'bake-regions', 'bake-hvdc', 'bake-events', 'bake-nodes'},
                         {c['dataset_id'] for c in result['citations']})

    def test_unknown_stays_unknown(self):
        early = answers.answer(self.bake, '2026-09-20T13:40', 'why is visayas so expensive')
        self.assertEqual('No price is on record for Visayas at 13:40.',
                         early['blocks'][0]['parts'][0]['v'])
        self.assertFalse(any(p['t'] == 'num' for b in early['blocks'] for p in b.get('parts', [])))
        first_day = answers.answer(self.bake, AT, 'why is visayas so expensive')
        words = ' '.join(p['v'] for b in first_day['blocks'] for p in b.get('parts', []) if p['t'] == 'text')
        self.assertIn('No usual price is on record for 13:00 yet.', words)

    def test_the_cut_off_holds_at_an_earlier_clock(self):
        result = answers.answer(self.bake, EARLY, 'what happened recently')
        ids = {e['id'] for e in result['entities']}
        self.assertIn('SYN-ADV-0005', ids)  # 09:10, inside six hours
        self.assertFalse(ids & {'SYN-ADV-0002', 'SYN-ADV-0003', 'syn-bay-unit-2-trip'}, ids)
        self.check_answer(result, EARLY)

    def test_free_text_reaches_the_intent(self):
        cases = {
            'which nodes have unusual prices and what is causing them': ('unusual_nodes', None),
            'why is visayas so expensive': ('region_price_why', 'CVIS'),
            'Why is Mindanao priced like this?': ('region_price_why', 'CMIN'),
            'what is congested on the HVDC links?': ('hvdc_congestion', None),
            'how is SYN-LUZ-1 doing': ('plant_status', 'SYN-LUZ-1'),
            'synthetic leyte geothermal status': ('plant_status', 'SYN-LEY-1'),
            'any trips in the last hours?': ('recent_events', None),
            'notices for luzon': ('recent_events', 'CLUZ'),
            'which grid is cheapest right now': ('grid_overview', None),
            'tell me a joke': (None, None),
        }
        for question, expected in cases.items():
            self.assertEqual(expected, answers.match(self.bake, question), question)

    def test_an_ambiguous_plant_name_is_not_guessed(self):
        # SYN-BAY-1 and SYN-BAY-2 share the word BAY: the desk does not pick one for the reader.
        self.assertIsNone(answers.match_plant(self.bake, 'what about bay'))

    def test_no_match_offers_the_prompts(self):
        result = answers.answer(self.bake, AT, 'tell me a joke')
        self.assertEqual('no_match', result['status'])
        self.assertEqual([p['id'] for p in answers.prompts(self.bake, AT)],
                         [f['prompt_id'] for f in result['followups']])
        self.check_copy(result['blocks'][0]['parts'][0]['v'])

    def test_prompts_each_answer_at_the_clock(self):
        for at in CLOCKS:
            offered = answers.prompts(self.bake, at)
            with self.subTest(at=at):
                self.assertTrue(3 <= len(offered) <= 5, offered)
                for prompt in offered:
                    result = answers.answer(self.bake, at, '', prompt['id'])
                    self.assertEqual('answered', result['status'], prompt)
                    self.assertEqual(prompt['text'], result['question'])
                    self.assertTrue(any(p['t'] == 'num' for b in result['blocks'] for p in b.get('parts', []))
                                    or any(b['type'] == 'table' for b in result['blocks']), prompt)
                    self.check_answer(result, at)
                    self.check_copy(prompt['text'])
        self.assertEqual('why-visayas-price', answers.prompts(self.bake, AT)[0]['id'],
                         'at 13:40 the Visayas price at the cap is the most telling')

    def test_a_prompt_without_substance_is_not_offered(self):
        # every location sits on its grid median in the fixture, so "unusual" has nothing to say
        self.assertNotIn('unusual-nodes', [p['id'] for p in answers.prompts(self.bake, AT)])

    def test_search(self):
        self.assertEqual([], searching.search(self.bake, '', AT)['groups'])
        self.assertEqual([], searching.search(self.bake, '   ', AT)['groups'])
        result = searching.search(self.bake, 'synthetic', AT)
        kinds = [g['kind'] for g in result['groups']]
        self.assertEqual(sorted(kinds, key=searching.KINDS.index), kinds, 'groups in the contract order')
        plant = searching.search(self.bake, 'SYN-LUZ', AT)['groups'][0]['items'][0]
        self.assertEqual({'kind': 'plant', 'id': 'SYN-LUZ-1', 'title': 'Synthetic Luzon Combined Cycle',
                          'subtitle': 'Luzon · generator · 600 MW', 'href': '/plant/SYN-LUZ-1', 'grid': 'CLUZ',
                          'badge': None}, plant)
        visayas = searching.search(self.bake, 'VISAYAS', AT)
        self.assertEqual('CVIS', [g for g in visayas['groups'] if g['kind'] == 'region'][0]['items'][0]['id'])
        # case and accent insensitive
        self.assertEqual(searching.search(self.bake, 'visayas', AT), dict(visayas, q='visayas'))
        self.assertTrue(searching.search(self.bake, 'Vísayas', AT)['groups'])
        # nothing later than the clock: the 13:40 trip is not found at 13:00
        early = searching.search(self.bake, 'tripped', EARLY)
        self.assertFalse([i for g in early['groups'] for i in g['items'] if i['kind'] in ('notice', 'event')])
        later = searching.search(self.bake, 'tripped', AT)
        self.assertEqual(['SYN-ADV-0002'], [i['id'] for g in later['groups'] if g['kind'] == 'notice'
                                            for i in g['items']])
        self.assertEqual('alert', [g for g in later['groups'] if g['kind'] == 'notice'][0]['items'][0]['badge'])
        # prefix matches rank first, and the limit holds
        pages = [g for g in searching.search(self.bake, 'a', AT, limit=3)['groups'] if g['kind'] == 'page'][0]
        self.assertEqual(3, len(pages['items']))
        self.assertEqual('Alerts', pages['items'][0]['title'])

    def test_previews(self):
        plant = searching.preview(self.bake, 'plant', 'SYN-BAY-1', AT)
        self.assertEqual(['Price', 'Dispatch'], [f['label'] for f in plant['facts']])
        self.assertEqual(32000, plant['facts'][0]['value'])
        self.assertEqual(AT, plant['facts'][0]['at'])
        spark = plant['sparks'][0]
        self.assertEqual(len(spark['t']), len(spark['v']))
        self.assertEqual(AT, spark['t'][-1])
        self.assertEqual(1 + 13 * 12 + 8, len(spark['t']), 'every interval from 00:00 to 13:40, nothing later')
        region = searching.preview(self.bake, 'region', 'CVIS', AT)
        self.assertEqual(32000, region['facts'][0]['value'])
        self.assertIn('Net import', [f['label'] for f in region['facts']])
        event = searching.preview(self.bake, 'event', 'syn-bay-unit-2-trip', AT)
        self.assertEqual(('/event/syn-bay-unit-2-trip', 'alert'), (event['href'], event['facts'][1]['value']))
        self.assertIn('Assumption', [f['label'] for f in event['facts']])
        self.assertIn('tripped', event['summary'])
        link = searching.preview(self.bake, 'link', 'VISLUZ1', AT)
        self.assertEqual(['Flow', 'Congested'], [f['label'] for f in link['facts']])
        notice = searching.preview(self.bake, 'notice', 'SYN-ADV-0005', AT)
        self.assertEqual('warning', notice['facts'][1]['value'])
        dataset = searching.preview(self.bake, 'dataset', 'bake-regions', AT)
        self.assertEqual('bake-regions', dataset['sources'][0]['dataset_id'])
        for kind, ident, at in (('plant', 'NOPE', AT), ('region', 'CXYZ', AT), ('event', 'nope', AT),
                                ('notice', 'nope', AT), ('link', 'NOPE1', AT), ('dataset', 'nope', AT),
                                ('elephant', 'x', AT),
                                # not yet known at the clock
                                ('event', 'syn-bay-unit-2-trip', EARLY), ('notice', 'SYN-ADV-0002', EARLY)):
            self.assertIsNone(searching.preview(self.bake, kind, ident, at), (kind, ident, at))
        for kind, ident in (('plant', 'SYN-BAY-1'), ('region', 'CVIS'), ('link', 'MINVIS1')):
            card = searching.preview(self.bake, kind, ident, EARLY)
            for t in times_in(card):
                self.assertLessEqual(t, EARLY, (kind, ident))


class RealShapedBake(Invariants, unittest.TestCase):
    """The catalog fixture: replay.json, days/, advisories/<month>.json and an event with no view."""

    def test_the_year_shape_reads(self):
        bake = Bake(CATALOG_BAKE)
        at = '2026-09-21T13:45'
        self.assertTrue(bake.index()['by_day'])
        for intent, entity in (('region_price_why', 'CVIS'), ('unusual_nodes', None), ('hvdc_congestion', None),
                               ('plant_status', '08PEDC'), ('recent_events', None), ('grid_overview', None)):
            result = answers.compose(bake, at, 'q', intent, entity).result()
            self.check_answer(result, at)
        offered = answers.prompts(bake, at)
        self.assertTrue(offered)
        for prompt in offered:
            self.check_answer(answers.answer(bake, at, '', prompt['id']), at)
        # the event's view is missing: it still previews from events.json and its advisory
        card = searching.preview(bake, 'event', 'sample-event-2026-09-21', at)
        self.assertEqual('CVIS', card['grid'])
        self.assertEqual('alert', card['facts'][1]['value'])
        self.assertEqual('Sample Geothermal B', searching.preview(bake, 'plant', '08PEDC', at)['title'])
        self.assertEqual('pedc', fold_q(searching.search(bake, 'pedc', at)))
        # an approximate position (08SAMPLE is drawn near 08PEDC) is never a location
        self.assertTrue(bake.site('08PEDC')['located'])
        for code in ('08SAMPLE', '08PLACE', '04GEN'):
            self.assertFalse(bake.site(code)['located'], code)
        card = searching.preview(bake, 'plant', '08SAMPLE', at)
        self.assertNotIn('located', str(card).lower())


def fold_q(result):
    return result['q']


@unittest.skipUnless(SHOWCASE.is_dir(), 'the synthetic showcase bake is not built here')
class Showcase(Invariants, unittest.TestCase):
    """The synthetic showcase bake (scripts/grid/build_showcase.py), when one is built locally."""

    def test_every_prompt_and_intent_keeps_the_invariants(self):
        bake = Bake(SHOWCASE)
        for at in ('2026-09-21T13:40', '2026-09-24T19:00', '2026-09-29T23:55'):
            for prompt in answers.prompts(bake, at):
                self.check_answer(answers.answer(bake, at, '', prompt['id']), at)
            for intent, entity in (('unusual_nodes', None), ('hvdc_congestion', None), ('grid_overview', None)):
                self.check_answer(answers.compose(bake, at, 'q', intent, entity).result(), at)


def partial_dirs(root):
    """Data directories that miss optional files: each must answer, never 500."""
    out = {'empty': [], 'regions only': ['regions.json'], 'sites only': ['sites.json'],
           'no nodes': ['regions.json', 'hvdc.json', 'sites.json', 'advisories.json', 'events.json'],
           'no advisories': ['regions.json', 'hvdc.json', 'sites.json', 'nodes-2026-09-21.json', 'events.json'],
           'no hvdc or events': ['regions.json', 'sites.json', 'nodes-2026-09-21.json', 'advisories.json']}
    paths = {}
    for label, names in out.items():
        target = Path(root) / label.replace(' ', '-')
        target.mkdir()
        for name in names:
            shutil.copy(PAGE / name, target / name)
        paths[label] = target
    broken = Path(root) / 'broken'
    broken.mkdir()
    for name in ('regions.json', 'sites.json', 'events.json', 'advisories.json', 'replay.json'):
        (broken / name).write_text('{not json', encoding='utf-8')
    paths['broken'] = broken
    year = Path(root) / 'year-without-days'
    shutil.copytree(CATALOG_BAKE, year)
    shutil.rmtree(year / 'days')
    shutil.rmtree(year / 'advisories')
    paths['replay.json without its day files'] = year
    return paths


class MissingFiles(Invariants, unittest.TestCase):
    def test_partial_directories_answer_without_error(self):
        with tempfile.TemporaryDirectory() as root:
            for label, directory in partial_dirs(root).items():
                bake = Bake(directory)
                with self.subTest(label=label):
                    for at in (AT, '2026-09-21T13:45'):
                        searching.search(bake, 'syn', at)
                        for kind, ident in (('plant', 'SYN-BAY-1'), ('region', 'CVIS'), ('link', 'VISLUZ1'),
                                            ('event', 'syn-bay-unit-2-trip'), ('notice', 'SYN-ADV-0002'),
                                            ('dataset', 'bake-regions')):
                            searching.preview(bake, kind, ident, at)
                        for prompt in answers.prompts(bake, at):
                            self.check_answer(answers.answer(bake, at, '', prompt['id']), at)
                        for intent, entity in INTENT_CALLS:
                            if intent == 'plant_status' and bake.site(entity) is None:
                                continue
                            self.check_answer(answers.compose(bake, at, 'q', intent, entity).result(), at)
                        self.assertIn(answers.answer(bake, at, 'why is visayas expensive')['status'],
                                      ('answered', 'no_match'))


def demo_client(data_dir):
    from src.api import hosted
    runtime = hosted.demo_runtime({})
    with patch.dict(os.environ, {'GRID_DATA_DIR': str(data_dir)}):
        return TestClient(runtime.application())


@unittest.skipUnless(FASTAPI, 'needs FastAPI (run in the image)')
class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = demo_client(PAGE)

    def get(self, path):
        response = self.client.get(path)
        self.assertEqual('no-store', response.headers['cache-control'], path)
        return response

    def test_search_route(self):
        r = self.get(f'/api/desk/search?q=bay&at={AT}&limit=4')
        self.assertEqual(200, r.status_code)
        body = r.json()
        self.assertEqual(('bay', AT), (body['q'], body['at']))
        self.assertEqual({'kind', 'label', 'items'}, set(body['groups'][0]))
        self.assertEqual({'kind', 'id', 'title', 'subtitle', 'href', 'grid', 'badge'},
                         set(body['groups'][0]['items'][0]))
        self.assertEqual([], self.get(f'/api/desk/search?q=&at={AT}').json()['groups'])
        self.assertEqual([], self.get('/api/desk/search').json()['groups'])
        self.assertEqual(422, self.get('/api/desk/search?q=x&at=13:40').status_code)
        self.assertEqual(422, self.get('/api/desk/search?q=x&limit=lots').status_code)

    def test_preview_route(self):
        r = self.get(f'/api/desk/preview/plant/SYN-BAY-1?at={AT}')
        self.assertEqual(200, r.status_code)
        self.assertEqual({'kind', 'id', 'title', 'subtitle', 'href', 'grid', 'facts', 'sparks', 'summary', 'sources'},
                         set(r.json()))
        missing = self.get(f'/api/desk/preview/plant/NOPE?at={AT}')
        self.assertEqual((404, {'error': 'NOT_FOUND'}), (missing.status_code, missing.json()))
        self.assertEqual(404, self.get(f'/api/desk/preview/event/syn-bay-unit-2-trip?at={EARLY}').status_code)
        self.assertEqual(404, self.get(f'/api/desk/preview/unicorn/x?at={AT}').status_code)

    def test_prompts_and_answer_routes(self):
        prompts = self.get(f'/api/desk/prompts?at={AT}&page=home').json()['prompts']
        self.assertTrue(3 <= len(prompts) <= 5)
        self.assertEqual({'id', 'text', 'hint'}, set(prompts[0]))
        for prompt in prompts:
            r = self.client.post('/api/desk/answer', json={'question': prompt['text'], 'prompt_id': prompt['id'],
                                                            'at': AT, 'page': 'home'})
            self.assertEqual((200, 'no-store'), (r.status_code, r.headers['cache-control']))
            body = r.json()
            self.assertEqual({'status', 'question', 'at', 'intent', 'trace', 'blocks', 'citations', 'entities',
                              'followups', 'basis', 'model'}, set(body))
            self.assertEqual('answered', body['status'])
            # the demo has no live path: every answer is composed and says why
            self.assertEqual({'provider': 'Vertex AI', 'name': 'gemini-3.8-flash', 'mode': 'composed',
                              'latency_ms': None, 'tokens': None, 'recorded_at': None,
                              'fallback_reason': 'not_configured',
                              'label': 'Composed from the records. No model call.'}, body['model'])
        free = self.client.post('/api/desk/answer', json={'question': 'why is visayas so expensive', 'at': AT,
                                                          'prompt_id': None, 'page': 'home'}).json()
        self.assertEqual('region_price_why', free['intent'])
        none = self.client.post('/api/desk/answer', json={'question': 'hello', 'at': AT}).json()
        self.assertEqual('no_match', none['status'])
        for bad in ({'question': 'x' * 501, 'at': AT}, {'question': 3}, {'question': 'x', 'at': 'noon'}, []):
            self.assertEqual(422, self.client.post('/api/desk/answer', json=bad).status_code, bad)
        self.assertEqual(422, self.client.post('/api/desk/answer', content=b'{not json').status_code)

    def test_a_partial_directory_never_answers_500(self):
        with tempfile.TemporaryDirectory() as root:
            for label, directory in partial_dirs(root).items():
                client = demo_client(directory)
                for path in (f'/api/desk/search?q=syn&at={AT}', f'/api/desk/prompts?at={AT}',
                             f'/api/desk/preview/plant/SYN-BAY-1?at={AT}', f'/api/desk/preview/region/CVIS?at={AT}',
                             '/api/desk/search?q=syn', '/api/desk/prompts'):
                    self.assertIn(client.get(path).status_code, (200, 404), (label, path))
                for question in ('why is visayas expensive', 'unusual nodes', 'hvdc', 'events', 'overview', 'x'):
                    r = client.post('/api/desk/answer', json={'question': question, 'at': AT})
                    self.assertEqual(200, r.status_code, (label, question))


@unittest.skipUnless(FASTAPI, 'needs FastAPI (run in the image)')
class ViewsServed(unittest.TestCase):
    """Regression: the ask dock fetches `/grid-data/<stamp>/views/<key>.json` (src/grid/ask.js).

    The allow-list in src/api/__init__.py named every baked subdirectory but `views/`, so the
    recorded plan sets were baked and staged for Hosting, and answered 404 from the application.
    """

    def test_views_are_served_unversioned_and_under_the_stamp(self):
        from src.api import build_stamp, create_app
        app = create_app(type('Repository', (), {'store': None})(), None, data_dir=CATALOG_BAKE)
        client = TestClient(app)
        stamp = build_stamp(CATALOG_BAKE)
        expected = json.loads((CATALOG_BAKE / 'views' / 'home.json').read_text(encoding='utf-8'))
        plain = client.get('/grid-data/views/home.json')
        self.assertEqual((200, 'no-store'), (plain.status_code, plain.headers['cache-control']))
        self.assertEqual(expected, plain.json())
        stamped = client.get(f'/grid-data/{stamp}/views/home.json')
        self.assertEqual((200, 'public, max-age=31536000, immutable'),
                         (stamped.status_code, stamped.headers['cache-control']))
        self.assertEqual(200, client.get(f'/grid-data/{stamp}/views/index.json').status_code)
        # (a `..` segment is normalised by the client before it is sent; the allow-list test holds it)
        for refused in ('/grid-data/views/missing.json', '/grid-data/views/nested/home.json',
                        '/grid-data/views/.hidden.json', '/grid-data/views/home.html'):
            self.assertEqual(404, client.get(refused).status_code, refused)

    def test_the_allow_list_names_views(self):
        from src.api import GRID_DATA_NAME
        for name in ('views/home.json', 'views/index.json', 'views/pedc-u2-2026-09-21.json'):
            self.assertTrue(GRID_DATA_NAME.fullmatch(name), name)
        for name in ('views/../x.json', 'views/a/b.json', 'views/.x.json', 'views/x.html'):
            self.assertFalse(GRID_DATA_NAME.fullmatch(name), name)


if __name__ == '__main__':
    unittest.main()
