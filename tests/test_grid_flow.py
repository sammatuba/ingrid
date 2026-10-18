"""The "How we got this" data-flow dialog (src/grid/flow.js), part 1: the event page.

`GridFlow.stages(card, V, onto, page)` is pure; these tests run it on node over a small synthetic
event and ontology record written here (no company data):

- the stages are built from the record: counts, the cutoff, the baseline window, the past
  intervals, the families scored, the AI run details, the as-of clock and the view;
- a field the record does not carry says "Not in the record";
- no private name reaches the text: no table, script, query or data file name, no build stamp,
  no request or probe id;
- every stage lists its tools, and only an AI stage lists Gemini;
- unclear matches stay flagged; no peso figure; fuel only as "fuel context available".
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / 'src' / 'grid'
NODE = shutil.which('node')
NOT = 'Not in the record'

DRIVER = r"""
import { readFileSync } from 'fs';
import vm from 'vm';
const sandbox = {};
vm.runInNewContext(readFileSync(process.argv[process.argv.length - 1], 'utf8'), sandbox);
const F = sandbox.GridFlow;
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const [name, a] of Object.entries(input)) out[name] = F.stages(a.card, a.V, a.onto, a.page);
process.stdout.write(JSON.stringify(out));
"""

STAMP = '0123456789abcdef'
VIEW = {
    'id': 'syn-unit-1', 'title': 'SYN U1 tripped', 'grid_name': 'Visayas', 'event_at': '2026-09-21T10:04',
    'timeline': [{'t': '2026-09-21T10:06:00', 'src': 'S1'}, {'t': '2026-09-21T10:30', 'src': 'WESM RTD'},
                 {'t': '2026-09-21T11:20:00', 'src': 'S2'}],
    'market': {'t': ['2026-09-21T10:00', '2026-09-21T10:05', '2026-09-21T10:10']},
    'judgment': {'by': 'synthetic-model · Vertex AI · live', 'questions': [{}, {}, {}], 'unstable': False,
                 'receipt': '4 phrasings × 3 questions · max flip rate 0 · request 512a7faa6554ab · probe:e575d3c9e91a6e'},
    'cutoffs': [{}, {}], 'limits': ['a', 'b', 'c'],
}


def facts():
    return [
        {'family': 'D', 'source_table': 'grid_curated.intervals', 'availability_at_cutoff': 'assumed', 'availability_assumption': 'A-RT'},
        {'family': 'O', 'source_table': 'grid_curated.outage_events', 'availability_at_cutoff': 'assumed', 'availability_assumption': 'A-RUN'},
        {'family': 'O', 'source_table': 'grid_curated.outage_mentions', 'availability_at_cutoff': 'evidenced', 'availability_assumption': None},
        {'family': 'Rules', 'source_table': 'grid_curated.labels', 'availability_at_cutoff': 'assumed', 'availability_assumption': 'A-RT'},
    ]


ONTO = {
    'case': 'syn-unit-1', 'region': 'Visayas', 't': '2026-09-21T10:05:00+08:00',
    'source': 'grid_ontology.driver_card, likely_drivers (recorded and checked by scripts/ontology/record_cards.sh)',
    'heading': 'Likely drivers (ranked by how unusual each was against the last 28 days at this hour; evidence, not proof)',
    'modes': {'assumed': {'cutoff_utc': '2026-09-21 02:10:00', 'facts': facts(), 'fuel_context': 1,
                          'unconfirmed': [{'plant_text': 'SYN PLANT', 'reason': 'uncertain'}],
                          'withheld': [{'family': 'O', 'reason': 'known only after the cutoff', 'n': 3},
                                       {'family': 'S', 'reason': 'availability assumed, not evidenced (A-RT)', 'n': 2}]}},
    'drivers': {'assumed': [
        {'family': 'P', 'status': 'context', 'baseline_n': '336'},
        {'family': 'S', 'status': 'scored', 'rank': '1', 'baseline_n': '336', 'source_table': 'grid_curated.intervals'},
        {'family': 'D', 'status': 'scored', 'rank': '2', 'baseline_n': '330'},
        {'family': 'F', 'status': 'scored', 'rank': '3', 'baseline_n': None, 'source_table': 'grid_curated.fuel_series'},
        {'family': 'O', 'status': 'no data', 'rank': '4', 'baseline_n': '325'},
        {'family': 'Rules', 'status': 'present'}]},
    'summary': {'severity': 'High', 'confidence': 'Low', 'financial_impact': 'Not available: needs portfolio data'},
    'paragraph': {'text': 'x', 'kind': 'phrased by Gemini, verified', 'model': 'synthetic-model'},
    'explanations': {'mode': 'assumed', 'items': {'S': 'a', 'D': 'b'}, 'model': 'synthetic-model'},
    'provenance': {'baseline': {'days': 28, 'hour': 'same Manila hour of day', 'excludes_t': True},
                   'recorded_at_utc': '2026-10-17T07:17:00Z', 'baked_at_utc': '2026-10-18T03:46:20Z',
                   'paragraph': {'result': 'phrased', 'attempt': 2, 'max_attempts': 2, 'run_at_utc': '2026-10-17T07:09:17+00:00',
                                 'instruction_version': 1, 'problems_n': 0, 'api': 'vertex_ai'},
                   'explanations': {'run_at_utc': '2026-10-17T07:12:00+00:00', 'kept_n': 2, 'dropped_n': 1}},
}
PAGE = {'mode': 'assumed', 'asOf': '2026-09-21T11:30', 'stamp': STAMP}


def run(calls):
    result = subprocess.run([NODE, '--input-type=module', '-e', DRIVER, '--', str(GRID / 'flow.js')],
                            input=json.dumps(calls), capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-800:])
    return json.loads(result.stdout)


def field(out, sid, label):
    s = next(x for x in out['stages'] if x['id'] == sid)
    return next(f for f in s['fields'] if f['label'] == label)


@unittest.skipUnless(NODE, 'node is needed to run src/grid/flow.js')
class Stages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bare = json.loads(json.dumps(ONTO))
        for k in ('provenance', 'explanations'):
            bare.pop(k)
        template = json.loads(json.dumps(ONTO))
        template['paragraph'] = {'text': 'x', 'kind': 'composed by code (template)', 'model': None}
        no_view = dict(VIEW, judgment=None)
        calls = {c: {'card': c, 'V': VIEW, 'onto': ONTO, 'page': PAGE} for c in ('glance', 'ai', 'ranked', 'rules')}
        calls['bare'] = {'card': 'ranked', 'V': no_view, 'onto': bare, 'page': {'mode': 'assumed'}}
        calls['bare_ai'] = {'card': 'ai', 'V': no_view, 'onto': bare, 'page': {'mode': 'assumed'}}
        calls['template'] = {'card': 'ai', 'V': VIEW, 'onto': template, 'page': PAGE}
        calls['nothing'] = {'card': 'glance', 'V': None, 'onto': None, 'page': {}}
        cls.out = run(calls)

    def test_stages_are_built_from_the_record(self):
        r = self.out['ranked']
        self.assertEqual('2026-09-21 10:10 Manila', field(r, 'S4', 'Market data up to (cutoff)')['value'])
        self.assertIn('each of the 28 days before', field(r, 'S4', 'Compared with')['value'])
        self.assertEqual('330 to 336 per indicator', field(r, 'S4', 'Past intervals compared')['value'])
        self.assertEqual('3 of 4 (S, D, F); no data: O', field(r, 'S4', 'Families scored')['value'])
        self.assertEqual('1', field(r, 'S3', 'Known with evidence')['value'])
        self.assertTrue(field(r, 'S3', 'Known by a named assumption')['value'].startswith('3: 2 real-time values'))
        self.assertEqual('5: 3 known only after the cutoff; 2 availability assumed, not evidenced', field(r, 'S3', 'Held back')['value'])
        self.assertEqual('2026-09-21 11:30 Manila', field(r, 'S9', 'As-of clock')['value'])
        self.assertEqual('What we likely knew', field(r, 'S9', 'View')['value'])
        self.assertEqual('2, from 2026-09-21 10:06 to 2026-09-21 11:20 Manila', field(r, 'S1', 'Operator notices in this event')['value'])
        a = self.out['ai']
        self.assertEqual('2 of 2', field(a, 'S6', 'Attempt')['value'])
        self.assertEqual('2026-10-17 15:09 Manila', field(a, 'S6', 'Run at')['value'])
        self.assertEqual('2 kept, 1 dropped by the check (synthetic-model)', field(a, 'S6', 'Per-family explanations')['value'])
        self.assertEqual('3', field(a, 'S8', 'Questions')['value'])
        self.assertEqual('2026-10-17 15:17 Manila', field(a, 'S5', 'Recorded at')['value'])
        self.assertEqual(0, a['missing'])
        self.assertEqual({'Event': 'SYN U1 tripped', 'Baked': '2026-10-18 11:46'},
                         {b['label']: b['value'] for b in a['built'] if b['label'] in ('Event', 'Baked')})

    def test_each_card_highlights_its_own_stages(self):
        on = {c: [s['id'] for s in self.out[c]['stages'] if s['on']] for c in ('glance', 'ai', 'ranked', 'rules')}
        self.assertEqual({'glance': ['S1', 'S2', 'S4', 'S7', 'S9'], 'ai': ['S4', 'S5', 'S6', 'S8', 'S9'],
                          'ranked': ['S1', 'S2', 'S3', 'S4', 'S5', 'S7', 'S9'], 'rules': ['S1', 'S2', 'S3', 'S7', 'S9']}, on)

    def test_missing_fields_say_not_in_the_record(self):
        b = self.out['bare']
        for sid, label in (('S4', 'Compared with'), ('S5', 'Recorded at'), ('S7', 'Baked at')):
            f = field(b, sid, label)
            self.assertEqual(NOT, f['value'], label)
            self.assertTrue(f['missing'])
        self.assertIsNone(next(s for s in b['stages'] if s['id'] == 'S4')['how'])  # no window: no ranking text
        self.assertEqual(NOT, field(b, 'S9', 'As-of clock')['value'])
        self.assertGreater(b['missing'], 0)
        ai = self.out['bare_ai']
        for label in ('Attempt', 'Run at', 'Problems the check found', 'Per-family explanations'):
            self.assertEqual(NOT, field(ai, 'S6', label)['value'], label)
        for label in ('Model', 'Questions', 'Receipt', 'Same answer across phrasings'):
            self.assertEqual(NOT, field(ai, 'S8', label)['value'], label)
        n = self.out['nothing']
        self.assertTrue(all(f['value'] == NOT for s in n['stages'] if s['id'] in ('S1', 'S4') for f in s['fields']
                            if f['label'] != 'View'))

    def test_no_private_name_appears(self):
        text = json.dumps(self.out)
        for word in ('grid_curated', 'grid_ontology', 'grid_raw', 'grid_ref', 'record_cards', 'bake_panel', '.sh', '.py',
                     '.sql', '.json', STAMP, '512a7faa', 'e575d3c9', 'probe', 'request', 'ontology/', 'events/'):
            self.assertNotIn(word, text, word)
        self.assertIsNone(re.search(r'\b[0-9a-f]{12,}\b', text))
        self.assertEqual('4 phrasings × 3 questions · max flip rate 0', field(self.out['ai'], 'S8', 'Receipt')['value'])
        refs = [r for c in ('glance', 'ai', 'ranked', 'rules') for s in self.out[c]['stages'] for r in s['refs']]
        self.assertTrue(refs)
        self.assertTrue(all(r['href'] is None or re.match(r'/(data|notices|assets|explain|paper)\b', r['href']) for r in refs))

    def test_every_stage_lists_its_tools(self):
        for c in ('glance', 'ai', 'ranked', 'rules', 'template'):
            for s in self.out[c]['stages']:
                self.assertTrue(s['tools'], (c, s['id']))
                gem = any(t['name'] == 'Gemini on Vertex AI' for t in s['tools'])
                self.assertEqual(s['kind'] == 'ai', gem, (c, s['id']))
        tools = {s['id']: [t['name'] for t in s['tools']] for s in self.out['ai']['stages']}
        self.assertIn('BigQuery', tools['S4'])
        self.assertEqual(['Python code', 'Gemini on Vertex AI', 'Code checks'], tools['S6'])
        self.assertIn('Cloud Run and Firebase Hosting', tools['S9'])
        t6 = next(s for s in self.out['template']['stages'] if s['id'] == 'S6')
        self.assertEqual('det', t6['kind'])
        self.assertEqual('Paragraph by template (no AI)', t6['name'])
        self.assertEqual('none', field(self.out['template'], 'S6', 'Attempt')['value'])

    def test_desk_rules_hold(self):
        text = json.dumps(self.out)
        self.assertNotIn('₱', text)
        self.assertNotIn('PHP', text)
        self.assertEqual('Needs your portfolio', field(self.out['ai'], 'S5', 'Peso impact')['value'])
        f = field(self.out['ranked'], 'S3', 'Unclear names')
        self.assertTrue(f['flag'])
        self.assertEqual('1, flagged: not linked, not counted', f['value'])
        self.assertIn('fuel context available', field(self.out['ranked'], 'S1', 'Fuel')['value'])
        self.assertIsNone(re.search(r'\b(coal|lng|diesel|solar|geothermal|hydro|wind|gas|oil|battery|thermal)\b', text, re.I))
        self.assertIsNone(re.search(r'\bforecast', text, re.I))


class Page(unittest.TestCase):
    def test_the_event_page_loads_the_dialog_and_each_card_has_its_button(self):
        html = (GRID / 'event.html').read_text(encoding='utf-8')
        self.assertIn('/grid/__NOWCAST_STAMP__/flow.css', html)
        self.assertLess(html.index('flow.js'), html.index('event-desk.js" defer'))
        # PP-B2: "At a glance" is the "What happened" card now; its button names it so.
        for card, name in (('glance', 'What happened'), ('ai', 'AI explanation'), ('ranked', 'What stood out, ranked'),
                           ('rules', 'Price rules')):
            self.assertRegex(html, rf'<button class="gf-q" type="button" data-flow="{card}" aria-haspopup="dialog" '
                                   rf'aria-label="How we got this: {re.escape(name)}" hidden>\?</button>')
        self.assertIn('the same hour on each of the 28 days before', html)
        self.assertNotIn('last 4 weeks', html)
        self.assertIn("aria-modal', 'true'", (GRID / 'flow.js').read_text(encoding='utf-8'))
        self.assertIn('GridFlow.mount(', (GRID / 'event-desk.js').read_text(encoding='utf-8'))
        self.assertNotRegex((GRID / 'flow.js').read_text(encoding='utf-8'), r'\.style\b|setAttribute\(.style')



DESK_DRIVER = r"""
import { readFileSync } from 'fs';
import vm from 'vm';
const sandbox = {};
vm.runInNewContext(readFileSync(process.argv[process.argv.length - 1], 'utf8'), sandbox);
const D = sandbox.GridEventDesk;
const { V, onto, asOf } = JSON.parse(readFileSync(0, 'utf8'));
const out = { lead: D.lead(V), rules: D.rulesFlag(onto, V), trail: D.trail(V, onto), explanation: D.explanation(onto, V),
  audit: D.audit(onto, V), views: D.views(onto), brief: D.brief(V, onto, 'assumed') };
for (const m of ['assumed', 'strict', 'hindsight']) {
  out['ranked_' + m] = D.ranked(onto, m);
  out['glance_' + m] = D.glance(V, onto, m, asOf);
  out['more_' + m] = D.moreDetail(V, onto, m, asOf);
  out['standout_' + m] = D.standout(onto, m, asOf);
}
process.stdout.write(JSON.stringify(out));
"""
# A table, file or script name, a request or probe id: none may reach the page's text.
PRIVATE = re.compile(r'grid_(raw|curated|ontology|alert|ref)\b|\b[\w/.-]+\.(sql|sh|py|json|csv)\b|record_cards|driver_card|'
                     r'\b(interval_pricing|outage_mentions|outage_events|labels_reserve|ext_rtd_hvdc_schedules|likely_drivers|card_summary)\b|'
                     r'request [0-9a-f]{6}|probe:[0-9a-f]{6}')


@unittest.skipUnless(NODE, 'node is needed to run src/grid/event-desk.js')
class PageText(unittest.TestCase):
    """The rest of the event page: every text the desk draws, over the PEDC view fixture and an
    ontology record shaped like the recorded one (its source line and table names included)."""

    def setUp(self):
        view = json.loads((ROOT / 'tests' / 'fixtures' / 'grid' / 'event' / 'view.json').read_text(encoding='utf-8'))
        view['judgment'] = dict(view.get('judgment') or {}, by='synthetic-model · Vertex AI · live',
                                receipt='4 phrasings × 8 questions · max flip rate 0 · request 512a7faa6554… · probe:e575d3c9e91a6e… · tests/fixtures/x/case.json')
        onto = json.loads(json.dumps(ONTO))
        onto['source'] = 'grid_ontology.driver_card, likely_drivers, card_summary (recorded and checked by scripts/ontology/record_cards.sh)'
        for m in ('strict', 'hindsight'):
            onto['modes'][m] = json.loads(json.dumps(onto['modes']['assumed']))
            onto['drivers'][m] = json.loads(json.dumps(onto['drivers']['assumed']))
        result = subprocess.run([NODE, '--input-type=module', '-e', DESK_DRIVER, '--', str(GRID / 'event-desk.js')],
                                input=json.dumps({'V': view, 'onto': onto, 'asOf': '2026-09-21T23:59'}),
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr[-800:])
        self.out = json.loads(result.stdout)
        self.text = json.dumps(self.out, ensure_ascii=False)

    def test_no_table_file_or_script_name_and_no_request_id_reaches_the_page(self):
        self.assertIsNone(PRIVATE.search(self.text), PRIVATE.search(self.text) and
                          self.text[max(0, PRIVATE.search(self.text).start() - 80):PRIVATE.search(self.text).end() + 40])

    def test_sources_read_in_plain_words(self):
        self.assertIn('Ontology record (facts with the time each was known), checked by code before it was recorded',
                      self.out['explanation']['sources'])
        self.assertIn('five-minute market intervals', self.out['explanation']['sources'])
        self.assertIn('Receipt: 4 phrasings × 8 questions · max flip rate 0', self.out['audit']['models'])

    def test_the_page_markup_and_render_code_carry_no_private_name(self):
        html = (GRID / 'event.html').read_text(encoding='utf-8')
        visible = re.sub(r'<!--.*?-->|<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)
        visible = re.sub(r'<[^>]+>', ' ', visible)
        self.assertIsNone(PRIVATE.search(visible), PRIVATE.search(visible) and PRIVATE.search(visible).group(0))
        desk = (GRID / 'event-desk.js').read_text(encoding='utf-8')
        self.assertNotRegex(desk, r'String\((onto\.source|f\.source_table|nc\.source_table)')
        self.assertIn('Source: ${plainSrc(onto.source)}', desk)
        for href in ('/data', '/notices', '/explain', '/paper'):
            self.assertIn(f"['{href}', ", desk)

if __name__ == '__main__':
    unittest.main()
