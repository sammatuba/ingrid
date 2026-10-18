"""ericka-desk slice 7: the event desk (src/grid/event-desk.js).

The module's rules are pure functions it exposes as `GridEventDesk`; these tests run them on node
over a small synthetic event written here (no company data):

- the lead line starts with the trigger notice (E15);
- the rules flag comes from the record's Rules facts, and a fact with no value is "No data" (E13);
- the outcome trail runs from the first notice to the price, each step with a source, and hides
  steps after the as-of clock (E16);
- the AI explanation card says whether the ranking holds across the views, from records only (E19);
- the audit lists unclear matches by their words, never as a link or a count (E18, E20);
- peso impact is never invented: "Needs your portfolio";
- "At a glance": every summary card and both graphs read the records, and a figure they do not
  carry says "Not in the record";
- CORP-5: a passage the view's first cutoff does not place keeps its text off the page.
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

DRIVER = r"""
import { readFileSync } from 'fs';
import vm from 'vm';
const sandbox = {};
vm.runInNewContext(readFileSync(process.argv[process.argv.length - 1], 'utf8'), sandbox);
const O = sandbox.GridEventDesk;
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const [name, call] of Object.entries(input)) out[name] = O[call.fn](...call.args);
process.stdout.write(JSON.stringify(out));
"""


def run(calls):
    result = subprocess.run([NODE, '--input-type=module', '-e', DRIVER, '--', str(GRID / 'event-desk.js')],
                            input=json.dumps(calls), capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-800:])
    return json.loads(result.stdout)


# Synthetic: a made-up unit "SYN U1" in a made-up hour; figures chosen for the tests.
VIEW = {
    'id': 'syn-unit-1', 'grid_name': 'Visayas', 'event_at': '2026-09-21T10:04',
    'advisory': {'id': 'S1', 't': '2026-09-21T10:06:00', 'text': 'Visayas Grid-09/21/2026 10:06: SYN U1 Tripped at 1004H (Unplanned Outage)'},
    'timeline': [
        {'t': '2026-09-21T10:06:00', 'kind': 'trip', 'text': 'SYN U1 Tripped at 1004H', 'src': 'S1'},
        {'t': '2026-09-21T10:30', 'kind': 'market', 'text': 'reserve short', 'src': 'WESM RTD'},
        {'t': '2026-09-21T11:20:00', 'kind': 'online', 'text': 'SYN U1 online at 1115H', 'src': 'S2'},
    ],
    'market': {'t': ['2026-09-21T10:00', '2026-09-21T10:05', '2026-09-21T10:10', '2026-09-21T10:15'],
               'lmp': [5000, 6000, 32000, None]},
    'judgment': {'by': 'synthetic-model', 'receipt': 'max flip rate 0 · synthetic', 'unstable': False},
}


def rules_fact(predicate, value_num=None, value_text=None):
    return {'family': 'Rules', 'predicate': predicate, 'value_num': value_num, 'value_text': value_text,
            'source_table': 'syn.rules'}


ONTO = {
    't': '2026-09-21T10:10:00+08:00', 'source': 'synthetic ontology record',
    'heading': 'Likely drivers (synthetic)',
    'summary': {'relationship_trail': 'SYN U1 (message) -> region -> price', 'confidence': 'Low',
                'confidence_reason': 'synthetic', 'severity': 'High', 'severity_reason': 'synthetic',
                'financial_impact': 'Not available: needs portfolio data', 'what_to_check': ['check the return']},
    'paragraph': {'text': 'Synthetic paragraph.', 'kind': 'phrased, verified', 'model': 'syn-model-1'},
    'modes': {
        'assumed': {'cutoff_utc': '2026-09-21 02:15:00', 'facts': [rules_fact('n_nodes_ap', '0.0'), rules_fact('admin_priced')],
                    'withheld': [{}, {}], 'unconfirmed': []},
        'strict': {'facts': [], 'withheld': [{}], 'unconfirmed': []},
        'hindsight': {'facts': [], 'withheld': [], 'unconfirmed': [{'object_label': 'SYN-X or SYN-Y'},
                                                                         {'plant_text': 'SYN SOLAR', 'reason': 'two plants'}]},
    },
    'drivers': {
        'assumed': [{'rank': '1', 'family': 'S', 'status': 'scored'}, {'rank': '2', 'family': 'D', 'status': 'scored'}],
        'strict': [{'rank': '1', 'family': 'S', 'status': 'scored'}],
    },
}


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Lead(unittest.TestCase):
    def test_the_lead_starts_with_the_trigger_notice(self):
        out = run({'l': {'fn': 'lead', 'args': [VIEW]}, 'none': {'fn': 'lead', 'args': [{}]}})
        self.assertTrue(out['l']['text'].startswith('Trigger: NGCP S1 at 10:06: SYN U1 Tripped at 10:04'))
        self.assertIn('₱5,000/MWh at 10:00', out['l']['text'], 'the price of the last interval at or before the trip')
        self.assertIn('₱32,000/MWh at 10:10, the ₱32,000 offer cap.', out['l']['text'])
        self.assertIn('No data', out['none']['text'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Rules(unittest.TestCase):
    def test_null_rules_facts_are_no_data_and_the_cap_comes_from_the_market(self):
        r = run({'r': {'fn': 'rulesFlag', 'args': [ONTO, VIEW]}})['r']
        items = {i['key']: i['value'] for i in r['items']}
        self.assertEqual('No data', items['admin_priced'])
        self.assertEqual('0', items['n_nodes_ap'])
        self.assertEqual('No data', items['cap_bound'], 'a fact the record does not carry is No data')
        self.assertEqual('warn', r['level'])
        self.assertIn('offer cap', r['headline'])

    def test_true_false_text_reads_yes_no_and_a_bound_cap_is_a_warning_not_administered(self):
        onto = json.loads(json.dumps(ONTO))
        onto['modes']['assumed']['facts'] = [rules_fact('cap_bound', value_text='true'), rules_fact('admin_priced', value_text='false')]
        r = run({'r': {'fn': 'rulesFlag', 'args': [onto, None]}})['r']
        items = {i['key']: i['value'] for i in r['items']}
        self.assertEqual(('Yes', 'No'), (items['cap_bound'], items['admin_priced']))
        self.assertEqual(('warn', 'On record: Offer cap bound'), (r['level'], r['headline']))

    def test_a_count_above_zero_flags_and_nothing_known_is_no_data(self):
        onto = json.loads(json.dumps(ONTO))
        onto['modes']['assumed']['facts'] = [rules_fact('n_nodes_ap', '3.0')]
        out = run({'bad': {'fn': 'rulesFlag', 'args': [onto, None]},
                   'none': {'fn': 'rulesFlag', 'args': [None, None]}})
        self.assertEqual('bad', out['bad']['level'])
        self.assertEqual('On record: Nodes under administered price', out['bad']['headline'])
        self.assertEqual('none', out['none']['level'])
        self.assertEqual('Pricing rules: No data', out['none']['headline'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Trail(unittest.TestCase):
    def test_the_trail_runs_from_the_first_notice_to_the_price_with_a_source_per_step(self):
        steps = run({'s': {'fn': 'trail', 'args': [VIEW, ONTO]}})['s']
        self.assertEqual('trip', steps[0]['kind'])
        self.assertEqual([s['t'] for s in steps], sorted(s['t'] for s in steps))
        self.assertIn('price', [s['kind'] for s in steps])
        self.assertIn('drivers', [s['kind'] for s in steps])
        for s in steps:
            self.assertTrue(s['source'], s)
        self.assertEqual('NGCP notice S1', steps[0]['source'])
        self.assertIn('price before: ₱5,000/MWh at 10:00', steps[0]['detail'])

    def test_steps_after_the_clock_are_hidden_and_counted(self):
        steps = run({'s': {'fn': 'trail', 'args': [VIEW, ONTO]}})['s']
        cut = run({'c': {'fn': 'upTo', 'args': [steps, '2026-09-21T10:30']}})['c']
        self.assertTrue(all(s['t'] <= '2026-09-21T10:30' for s in cut['shown']))
        self.assertEqual(1, cut['later'])

    def test_utc_cutoffs_read_in_manila_time(self):
        out = run({'m': {'fn': 'manilaFromUtc', 'args': ['2026-09-21 05:45:00']},
                   'z': {'fn': 'manilaFromUtc', 'args': ['2026-09-21T13:40:00+08:00']}})
        self.assertEqual('2026-09-21T13:45', out['m'])
        self.assertEqual('2026-09-21T13:40', out['z'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Explanation(unittest.TestCase):
    def test_holds_across_views_reports_the_missing_view_as_no_data(self):
        e = run({'e': {'fn': 'explanation', 'args': [ONTO, VIEW]}})['e']
        self.assertEqual('Synthetic paragraph.', e['text'])
        self.assertEqual('syn-model-1', e['model'])
        self.assertTrue(e['holds'].startswith('Yes in 2 of 3 views: Supply and interconnection ranks first'))
        self.assertIn('Hindsight: No data', e['holds'])
        self.assertEqual('2026-09-21T10:10', e['knownAt'])
        self.assertIn('recorded grid data', e['sources'], 'a table name reads in plain words, never as the name')

    def test_views_that_rank_differently_are_a_disagreement(self):
        onto = json.loads(json.dumps(ONTO))
        onto['drivers']['strict'] = [{'rank': '1', 'family': 'D', 'status': 'scored'}]
        e = run({'e': {'fn': 'explanation', 'args': [onto, VIEW]}})['e']
        self.assertTrue(e['holds'].startswith('No'))
        self.assertIn('Strict: Demand', ' '.join(e['disagreement']))

    def test_no_record_means_no_data(self):
        e = run({'e': {'fn': 'explanation', 'args': [None, None]}})['e']
        self.assertIsNone(e['text'])
        self.assertTrue(e['holds'].startswith('Cannot tell'))


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Audit(unittest.TestCase):
    def test_unclear_matches_are_listed_by_their_words_and_peso_impact_needs_the_portfolio(self):
        a = run({'a': {'fn': 'audit', 'args': [ONTO, VIEW]}})['a']
        self.assertEqual([{'view': 'Hindsight', 'text': 'SYN-X or SYN-Y', 'reason': None},
                          {'view': 'Hindsight', 'text': 'Name not shown (it names a technology)', 'reason': 'two plants'}],
                         a['unclear'], 'a name with a fuel word is withheld')
        self.assertIn('Peso impact: Needs your portfolio', a['calculation'])
        self.assertEqual({'As known at the time': 2, 'Strict': 1, 'Hindsight': 0}, a['withheld'])
        self.assertIn('NGCP notices S1, S2', a['sources'][0])
        self.assertIn('AI reader: synthetic-model', a['models'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Withheld(unittest.TestCase):
    def test_technology_words_in_notice_text_are_withheld(self):
        v = json.loads(json.dumps(VIEW))
        v['advisory']['text'] = 'Visayas Grid-09/21/2026 10:06: SYN SOLAR U1 Tripped at 1004H'
        v['timeline'][0]['text'] = 'SYN HEPP U1 Tripped at 1004H'
        out = run({'l': {'fn': 'lead', 'args': [v]}, 's': {'fn': 'trail', 'args': [v, ONTO]},
                   'w': {'fn': 'withheld', 'args': ['SYN Wind and BESS U1']}})
        self.assertIn('SYN […] U1 Tripped at 10:04', out['l']['text'])
        self.assertNotRegex(json.dumps(out), r'(?i)solar|hepp|wind|bess')
        self.assertEqual('SYN […] and […] U1', out['w'])


@unittest.skipUnless(NODE, 'the shell runs on node; this interpreter has none')
class TickerWithheld(unittest.TestCase):
    def test_the_ticker_withholds_technology_words(self):
        script = (GRID / 'shell.js').read_text(encoding='utf-8')
        self.assertIn("const opText = (s) => withheld(s)", script)


# The ontology rows "At a glance" reads: the price row's usual and three scored families.
SCORED = json.loads(json.dumps(ONTO))
SCORED['drivers']['assumed'] = [
    {'rank': None, 'family': 'P', 'status': 'context', 'indicator': 'price_capped_median',
     'value_at_t': 29000.0, 'baseline_median': 7250.0, 'unit': 'PHP/MWh'},
    {'rank': '2', 'family': 'D', 'status': 'scored', 'family_score': 0.61},
    {'rank': '1', 'family': 'S', 'status': 'scored', 'family_score': 0.9},
    {'rank': '1', 'family': 'S', 'status': 'scored', 'family_score': 0.9, 'indicator': 'second row'},
    {'rank': None, 'family': 'O', 'status': 'no_data'},
]


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Glance(unittest.TestCase):
    def tiles(self, view, onto, mode='assumed', as_of=None):
        out = run({'g': {'fn': 'glance', 'args': [view, onto, mode, as_of]}})['g']
        return {t['key']: t for t in out}

    def test_each_card_reads_its_figure_from_the_records(self):
        t = self.tiles(VIEW, SCORED)
        self.assertEqual(['trigger', 'peak', 'usual', 'lag', 'steps', 'facts', 'top'], list(t))
        self.assertEqual(('₱5,000', '/MWh'), (t['trigger']['value'], t['trigger']['unit']))
        self.assertIn('10:00', t['trigger']['note'])
        self.assertEqual('₱32,000', t['peak']['value'])
        self.assertIn('offer cap, first at 10:10', t['peak']['note'])
        self.assertIn('6.4× the price at the trigger', t['peak']['note'])
        self.assertEqual('₱7,250', t['usual']['value'], "the price row's 28-day median at this hour")
        self.assertIn('₱29,000, 4.0× usual', t['usual']['note'])
        self.assertEqual('6 min', t['lag']['value'])
        self.assertEqual('2 shown', t['facts']['value'])
        self.assertEqual('Supply and interconnection', t['top']['value'])
        self.assertIn('Higher than 90%', t['top']['note'])
        for k in t.values():
            self.assertTrue(k['label'] and k['value'] and k['note'], k)

    def test_a_figure_the_records_do_not_carry_is_not_in_the_record(self):
        t = self.tiles({}, None)
        for key in ('trigger', 'peak', 'usual', 'lag', 'steps', 'facts', 'top'):
            self.assertEqual('Not in the record', t[key]['value'], key)
        # Without the price row and the scores, those two say so and nothing is estimated.
        t = self.tiles(VIEW, ONTO)
        self.assertEqual('Not in the record', t['usual']['value'])
        self.assertEqual('Not in the record', t['top']['value'])
        self.assertEqual('₱5,000', t['trigger']['value'])

    def test_steps_after_the_clock_are_counted_on_the_card(self):
        t = self.tiles(VIEW, SCORED, 'assumed', '2026-09-21T10:30')
        self.assertIn('more after the as-of clock (10:30)', t['steps']['note'])

    def test_no_card_names_a_peso_figure_the_records_do_not_carry(self):
        out = json.dumps(run({'g': {'fn': 'glance', 'args': [VIEW, SCORED, 'assumed', None]},
                              'b': {'fn': 'brief', 'args': [VIEW, SCORED, 'assumed']}}), ensure_ascii=False)
        recorded = {'₱5,000', '₱6,000', '₱32,000', '₱7,250', '₱29,000'}
        shown = set(re.findall(r'₱\d{1,3}(?:,\d{3})*', out))
        self.assertTrue(shown, 'the cards show the recorded prices')
        self.assertLessEqual(shown, recorded, 'every peso figure is a recorded price or the offer cap')
        self.assertNotRegex(out, r'(?i)forecast|will (rise|fall)|expected to')


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Graphs(unittest.TestCase):
    def test_the_price_line_marks_the_trigger_the_highest_price_and_the_cap(self):
        v = json.loads(json.dumps(VIEW))
        v['market']['marks'] = [{'t': '2026-09-21T10:04', 'kind': 'trip'}, {'t': '2026-09-21T10:15', 'kind': 'online'}]
        d = run({'d': {'fn': 'priceSeries', 'args': [v]}})['d']
        self.assertEqual(3, len(d['pts']), 'an interval with no price is left out, not drawn as zero')
        self.assertEqual('2026-09-21T10:04', d['at'])
        self.assertEqual({'t': '2026-09-21T10:10', 'value': 32000}, d['peak'])
        self.assertEqual(32000, d['cap'])
        self.assertEqual([{'t': '2026-09-21T10:15', 'kind': 'online', 'label': 'Back online'}], d['marks'],
                         'the trigger is drawn once, as the trigger')

    def test_the_bars_rank_each_scored_family_once_and_name_the_unscored(self):
        r = run({'r': {'fn': 'ranked', 'args': [SCORED, 'assumed']}, 'n': {'fn': 'ranked', 'args': [None, 'assumed']}})
        self.assertEqual([('S', 1, 90), ('D', 2, 61)], [(x['family'], x['rank'], x['pct']) for x in r['r']['rows']])
        self.assertEqual(['Outages'], r['r']['unscored'])
        self.assertEqual({'rows': [], 'unscored': []}, r['n'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Brief(unittest.TestCase):
    def test_the_short_explanation_is_composed_from_the_records(self):
        b = run({'b': {'fn': 'brief', 'args': [VIEW, SCORED, 'assumed']},
                 'n': {'fn': 'brief', 'args': [{}, None, 'assumed']}})
        self.assertEqual(3, len(b['b']))
        self.assertTrue(b['b'][0].startswith('Visayas price was ₱29,000/MWh at 10:10, against a usual ₱7,250'))
        self.assertIn('Supply and interconnection stood out most', b['b'][1])
        self.assertIn('then demand (61%)', b['b'][1])
        self.assertIn('not proven causes', b['b'][1])
        self.assertEqual('How sure the record is: Low.', b['b'][2])
        self.assertEqual([], b['n'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class CutoffText(unittest.TestCase):
    def test_a_passage_the_first_cutoff_does_not_place_keeps_its_text_off_the_page(self):
        v = json.loads(json.dumps(VIEW))
        v['rules'] = {'states': [{'announcements': [
            {'claim_ref': 'S1', 'status': 'not_yet_effective', 'quote': None, 'status_reason': 'not yet published'},
            {'claim_ref': 'S2', 'status': 'placed', 'quote': 'SYN U1 online at 1115H'}]}]}
        out = run({'l': {'fn': 'lead', 'args': [v]}, 's': {'fn': 'trail', 'args': [v, ONTO]},
                   'h': {'fn': 'heldBack', 'args': [v, 'S1']}, 'p': {'fn': 'heldBack', 'args': [v, 'S2']}})
        self.assertEqual('not yet published', out['h'])
        self.assertIsNone(out['p'])
        self.assertNotIn('Tripped', out['l']['text'])
        self.assertIn('Text not shown', out['l']['text'])
        trip = [x for x in out['s'] if x['source'] == 'NGCP notice S1'][0]
        self.assertNotIn('Tripped', trip['detail'])
        online = [x for x in out['s'] if x['source'] == 'NGCP notice S2'][0]
        self.assertIn('online at 11:15', online['detail'])
        self.assertIsNone(run({'n': {'fn': 'heldBack', 'args': [VIEW, 'S1']}})['n'], 'no rules block, nothing held')



# "More detail" and "What stood out": synthetic records (no company data).
MORE = json.loads(json.dumps(ONTO))
MORE['modes']['assumed']['facts'] = [
    {'family': 'O', 'predicate': 'scheduled_outage', 'subject_label': '09SYNA_U01', 'value_num': 50,
     'valid_from_utc': '2026-09-20 16:00:00', 'known_by_utc': '2026-09-20 01:00:00', 'source_table': 'syn.sched'},
    {'family': 'O', 'predicate': 'scheduled_outage', 'subject_label': '09SYNSPP_U01', 'value_num': 20,
     'valid_from_utc': '2026-09-20 16:00:00', 'known_by_utc': '2026-09-20 01:00:00', 'source_table': 'syn.sched'},
    {'family': 'O', 'predicate': 'mention_tripped', 'value_text': 'SYN U1', 'match_confidence': 'confirmed',
     'valid_from_utc': '2026-09-21 02:04:00', 'known_by_utc': '2026-09-21 02:06:00', 'source_table': 'syn.mentions'},
    {'family': 'O', 'predicate': 'mention_tripped', 'value_text': 'SYN U9', 'match_confidence': 'confirmed',
     'valid_from_utc': '2026-09-21 03:25:00', 'known_by_utc': '2026-09-21 03:30:00', 'source_table': 'syn.mentions'},
    {'family': 'S', 'predicate': 'hvdc_flow_mw', 'subject_label': 'SYNLINK1', 'value_num': -50,
     'valid_from_utc': '2026-09-21 02:05:00', 'known_by_utc': '2026-09-21 02:05:00', 'source_table': 'syn.hvdc'},
    {'family': 'S', 'predicate': 'hvdc_congested', 'subject_label': 'SYNLINK1', 'value_text': 'Y',
     'valid_from_utc': '2026-09-21 02:05:00', 'known_by_utc': '2026-09-21 02:05:00', 'source_table': 'syn.hvdc'},
]
MORE['modes']['assumed']['unconfirmed'] = [
    {'plant_text': 'SYN-Z', 'kind': 'mention_tripped', 'known_by_utc': '2026-09-21 02:20:00', 'reason': 'two plants'},
    {'plant_text': 'SYN SOLAR', 'kind': 'mention_tripped', 'known_by_utc': '2026-09-21 02:20:00', 'reason': 'two plants'},
]
TECH = re.compile(r'\b(solar|coal|hydro|geothermal|diesel|bunker|wind|gas)\b', re.I)


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class MoreDetail(unittest.TestCase):
    def more(self, as_of='2026-09-21T11:00'):
        return run({'m': {'fn': 'moreDetail', 'args': [VIEW, MORE, 'assumed', as_of]}})['m']

    def group(self, out, key):
        return [g for g in out['groups'] if g['key'] == key][0]['rows']

    def test_the_trigger_links_its_notice_and_names_its_unit(self):
        trig = self.group(self.more(), 'trigger')
        self.assertEqual('Trigger notice', trig[0]['rel'])
        self.assertEqual('/notices?at=2026-09-21T10%3A06#adv-S1', trig[0]['href'])
        self.assertIn('Not scheduled: the notice says unplanned', trig[0]['evidence'])
        self.assertIn('Posted 2 min after the time it states (10:04)', trig[0]['evidence'])
        self.assertEqual('Unit named in the trigger', trig[1]['rel'])
        self.assertEqual('SYN U1', trig[1]['title'])
        self.assertIsNone(trig[1]['href'], 'no unit code in the record: no page to open')

    def test_the_trigger_unit_links_the_site_only_when_the_event_record_states_it(self):
        view = dict(VIEW, assumption={'kv': [['Unit', '09SYNB_U02 · SYNB']]},
                    judgment=dict(VIEW['judgment'], questions=[{'id': 'q1', 'modal': '09SYNB_U02', 'agree': [True, True, True, True]}]))
        out = run({'m': {'fn': 'moreDetail', 'args': [view, MORE, 'assumed', '2026-09-21T11:00']}})['m']
        unit = self.group(out, 'trigger')[1]
        self.assertEqual('/plant/09SYNB', unit['href'])
        self.assertIn('Site 09SYNB from the event record (unit 09SYNB_U02)', unit['evidence'])
        self.assertIn('AI reading names 09SYNB_U02 (4 of 4 phrasings agree)', unit['evidence'])
        site_only = run({'m': {'fn': 'moreDetail', 'args': [dict(VIEW, site='09SYNC'), MORE, 'assumed', None]}})['m']
        self.assertEqual('/plant/09SYNC', self.group(site_only, 'trigger')[1]['href'])
        for bad in (dict(VIEW, assumption={'kv': [['Unit', 'SYN U1']]}), dict(VIEW, site='09SYNSPP')):
            out = run({'m': {'fn': 'moreDetail', 'args': [bad, MORE, 'assumed', None]}})['m']
            self.assertIsNone(self.group(out, 'trigger')[1]['href'], 'never guessed from a name or shown when it names a technology')

    def test_a_unit_links_its_site_page_only_when_the_record_codes_it_and_the_code_names_no_technology(self):
        rows = self.group(self.more(), 'supply')
        coded = [r for r in rows if r['href']]
        self.assertEqual(['/plant/09SYNA'], [r['href'] for r in coded])
        hidden = [r for r in rows if r['title'].startswith('Name not shown')]
        self.assertEqual(1, len(hidden))
        self.assertIsNone(hidden[0]['href'])
        self.assertNotIn('09SYNSPP', json.dumps(rows))

    def test_unclear_names_are_flagged_never_linked_and_technology_names_are_not_shown(self):
        out = self.more()
        rows = self.group(out, 'unclear')
        self.assertEqual(2, len(rows))
        for r in rows:
            self.assertIn('not matched', r['flag'])
            self.assertIsNone(r['href'])
        self.assertIsNone(TECH.search(json.dumps(out)), 'no shown string names a technology')

    def test_records_known_after_the_clock_are_left_out_and_counted(self):
        out = self.more()
        self.assertEqual({'facts': 1, 'notices': 1, 'unclear': 0}, out['later'])
        self.assertNotIn('SYN U9', json.dumps(out))
        self.assertNotIn('S2', [n['id'] for n in out['notices']])
        later = self.more(None)
        self.assertIn('SYN U9', json.dumps(later))
        self.assertIn('Supply back', [r['rel'] for r in self.group(later, 'response')])

    def test_island_links_and_lines_are_fact_rows_and_a_missing_figure_says_so(self):
        out = self.more()
        link = self.group(out, 'links')[0]
        self.assertIsNone(link['href'])
        self.assertIn('Congestion flag: raised', link['text'])
        self.assertIn('Limit: Not in the record', link['text'])
        lines = self.group(out, 'lines')[0]
        self.assertEqual('Congested nodes: Not in the record', lines['title'])
        self.assertIn('Island link flagged congested: SYNLINK1', lines['text'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class RelatedAlerts(unittest.TestCase):
    def test_a_linked_alert_and_one_around_the_same_time_and_nothing_else(self):
        view = dict(VIEW, grid='CVIS')
        alert = lambda **k: dict({'region': 'CVIS', 'first': '2026-09-21T10:05', 'last': '2026-09-21T10:20',
                                  'price_php_mwh': 32000, 'severity': 'extreme', 'main_driver': 'SYN U1 tripped'}, **k)
        inbox = {'groups': [{'alerts': [
            alert(key='0a1b2c3d4e5f', cause={'id': 'syn-unit-1'}, href='/event/syn-unit-1'),
            alert(key='b', cause={'id': 'other'}, href='/event/syn-other', first='2026-09-21T10:10', last='2026-09-21T10:40'),
            alert(key='c', region='CLUZ', href='/event/syn-luzon'),
            alert(key='d', href='/event/syn-late', first='2026-09-21T11:30', last='2026-09-21T11:40'),
            alert(key='e', href='/event/syn-before', first='2026-09-21T08:00', last='2026-09-21T09:00'),
            alert(key='f', href='javascript:alert(1)', first='2026-09-21T10:15', last='2026-09-21T10:30'),
        ]}]}
        out = run({'r': {'fn': 'relatedAlerts', 'args': [view, inbox, '2026-09-21T11:00']}})['r']
        self.assertEqual(['This event · price alert, linked by the record', 'Around the same time (not linked)',
                          'Around the same time (not linked)'], [r['rel'] for r in out])
        self.assertEqual(['/alerts?alert=0a1b2c3d4e5f', '/event/syn-other', None], [r['href'] for r in out],
                         'no link back to this page: the alert opens in the inbox')
        linked_elsewhere = dict(inbox['groups'][0]['alerts'][0], key='not-hex', href='/event/syn-unit-1')
        own = run({'r': {'fn': 'relatedAlerts', 'args': [view, {'groups': [{'alerts': [linked_elsewhere]}]}, None]}})['r']
        self.assertIsNone(own[0]['href'])
        self.assertEqual([], run({'r': {'fn': 'relatedAlerts', 'args': [view, None, None]}})['r'])


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class InboxAnswerAtTheCutoff(unittest.TestCase):
    """DM-5 (review of PERF-6): the shared inbox answer is drawn only when it was read at or before
    the clock, so moving the clock back never shows an alert's later end, peak or severity."""

    def test_an_answer_read_later_than_the_clock_is_withheld(self):
        cases = {
            'same': ['2026-09-21T13:05', '2026-09-21T13:05'],
            'earlier_read': ['2026-09-21T12:40', '2026-09-21T13:05'],
            'later_read': ['2026-09-21T15:00', '2026-09-21T13:05'],
            'other_day_later': ['2026-09-22T00:05', '2026-09-21T23:55'],
            'never_read': [None, '2026-09-21T13:05'],
            'no_clock': ['2026-09-21T15:00', None],
        }
        out = run({name: {'fn': 'inboxFits', 'args': args} for name, args in cases.items()})
        self.assertEqual({'same': True, 'earlier_read': True, 'later_read': False, 'other_day_later': False,
                          'never_read': False, 'no_clock': True}, out)

    def test_the_list_the_ticker_and_the_dashboard_apply_the_same_rule(self):
        desk = (ROOT / 'src' / 'grid' / 'event-desk.js').read_text(encoding='utf-8')
        self.assertIn("!inboxFits(state.inboxAt, asOf)", desk)
        self.assertIn("state.inboxAt = asOf;", desk)
        shell = (ROOT / 'src' / 'grid' / 'shell.js').read_text(encoding='utf-8')
        self.assertIn("alertItemsAt !== null && alertItemsAt <= asOf ? alertItems : []", shell)
        dash = (ROOT / 'src' / 'grid' / 'dash-alerts.js').read_text(encoding='utf-8')
        self.assertIn("at >= state.drawnAt) return;", dash)


STAND = json.loads(json.dumps(ONTO))
STAND['drivers']['assumed'] = [
    {'rank': None, 'family': 'P', 'status': 'context', 'indicator': 'price_capped_median', 'indicator_score': 0.97,
     'value_at_t': 29000.0, 'baseline_median': 7250.0, 'unit': 'PHP/MWh', 'source_table': 'syn.price'},
    {'rank': '2', 'family': 'D', 'status': 'scored', 'family_score': 0.61, 'indicator': 'demand_mw', 'indicator_score': 0.61,
     'value_at_t': 2400, 'baseline_median': 2300, 'unit': 'MW', 'source_table': 'syn.demand'},
    {'rank': '1', 'family': 'S', 'status': 'scored', 'family_score': 0.9, 'indicator': 'reserve_shortfall_mw', 'indicator_score': 0.9,
     'value_at_t': 100, 'baseline_median': 20, 'unit': 'MW', 'source_table': 'syn.reserve'},
    {'rank': None, 'family': 'Rules', 'status': 'present', 'indicator': 'admin_priced', 'source_table': 'syn.rules'},
    {'rank': None, 'family': 'Rules', 'status': 'absent', 'indicator': 'cap_bound', 'source_table': 'syn.rules'},
]


@unittest.skipUnless(NODE, 'the event desk module runs on node; this interpreter has none')
class Standout(unittest.TestCase):
    def test_one_row_per_family_ranked_first_each_with_a_state_and_its_detail(self):
        out = run({'s': {'fn': 'standout', 'args': [STAND, 'assumed', None]}})['s']
        rows = {r['family']: r for r in out['rows']}
        self.assertEqual(['S', 'D'], [r['family'] for r in out['rows'][:2]])
        self.assertEqual(6, len(out['rows']))
        self.assertEqual(('1', 'Unusual', 'warn'), (rows['S']['rank'], rows['S']['state'], rows['S']['cls']))
        self.assertEqual(('2', 'A bit high'), (rows['D']['rank'], rows['D']['state']))
        self.assertEqual(('–', 'Context'), (rows['P']['rank'], rows['P']['state']))
        self.assertEqual('Listed, not scored', rows['Rules']['state'])
        self.assertIn('Administered price set', rows['Rules']['text'])
        for fam in ('O', 'F'):
            self.assertEqual(('–', 'No data', 0), (rows[fam]['rank'], rows[fam]['state'], rows[fam]['bar']))
        self.assertIn('Reserve shortfall 100 MW vs about 20 MW usual', rows['S']['text'])
        self.assertTrue(rows['S']['detail']['signals'])
        self.assertEqual(['recorded grid data'], rows['S']['detail']['sources'], 'a table name reads in plain words')
        self.assertIsNone(TECH.search(json.dumps(out)))


class Page(unittest.TestCase):
    def test_the_page_carries_the_desk_and_the_summary_and_none_of_the_old_cards(self):
        """Platform polish (PP-B2) moves this pin: the event page is a decision workspace. The
        head is the anchor (breadcrumb, title, trigger, the price move and one unknowns line);
        the wide column says what happened (chart and timeline in one card), then what stood
        out, the explanation and the records behind the event as tabs; the side column is the
        decision region. Ericka's layout is restored there (the team's agreement, 18 October,
        reverting SHELL-1's return of Sam's cards): the AI reader's conclusion, the assumption,
        the person's decision in the journal box and their journal receipts, in order. The
        invariants hold: the desk's ids are on the page, the old cards are not (the desk line,
        the price outlook, the impact card, the decision form and the history among them: their
        renderers stay in event.js and are tested against tests/fixtures/grid/event/legacy-cards.html,
        which holds one copy of each id), no peso figure is offered without a portfolio, and the
        page carries no inline code or style."""
        html = (GRID / 'event.html').read_text(encoding='utf-8')
        legacy = (ROOT / 'tests' / 'fixtures' / 'grid' / 'event' / 'legacy-cards.html').read_text(encoding='utf-8')
        for ident in ('ed-lead', 'ed-rules', 'ed-desk', 'ed-trail', 'ed-trail-note', 'ed-ai', 'ed-ai-body',
                      'ed-audit-body', 'ed-journal-box', 'ed-glance', 'ed-kpis', 'ed-price', 'ed-view',
                      'ed-ranked', 'ed-ranked-rows', 'ed-more', 'ed-more-body', 'ed-cost', 'ed-read', 'ed-read-body',
                      'ed-unknowns', 'ev-crumb', 'ev-decide', 'ev-ai', 'ev-you', 'ev-receipts'):
            self.assertIn(f'id="{ident}"', html)
        for ident in ('rail', 'adv-quote', 'timeline', 'cutoff', 'mk-card',
                      'rules', 'as-value', 'jd-table', 'drivers', 'ed-drv'):
            self.assertNotIn(f'id="{ident}"', html, ident)
        # Sam's DESK-7 cards: off the live page, once each in the legacy fixture.
        for ident in ('dc-form', 'decision', 'desk-ai', 'desk-person', 'impact', 'history', 'price-outlook',
                      'dl-run', 'dl-proposal', 'dp-line', 'dp-receipt', 'po-plain', 'im-plain', 'hist-list'):
            self.assertNotIn(f'id="{ident}"', html, ident)
            self.assertEqual(1, legacy.count(f'id="{ident}"'), ident)
        self.assertIsNone(re.search(r'id="(?:dl|dp|po|im|dc|hist)-', html), 'no DESK-7 child id on the live page')
        self.assertNotIn('Record decision', html)
        side = html[html.index('<aside class="ev-col-side'):html.index('</aside>')]
        for ident in ('ev-ai', 'ev-assume', 'ev-you', 'ed-journal-box', 'ev-receipts', 'ev-journal-list'):
            self.assertIn(f'id="{ident}"', side, ident)
        # The region reads in order: the AI proposes, the assumption, the person decides in the
        # journal, the record. The numbered steps run 1, 2, 3 with no gap.
        steps = [side.index(f'id="{i}"') for i in ('ev-ai', 'ev-assume', 'ev-you', 'ev-receipts')]
        self.assertEqual(steps, sorted(steps), 'decision region order')
        self.assertEqual(['1', '2', '3'], re.findall(r'<span class="ev-step-n" aria-hidden="true">(\d)</span>', side))
        # The head is a breadcrumb under Alerts, and the anchor comes before the matrix.
        self.assertIn('<nav class="gn-crumbs" aria-label="Breadcrumb"><a href="/alerts">Alerts</a>', html)
        self.assertLess(html.index('class="ev-anchor"'), html.index('class="gn-grid gn-grid--main-side ev-cols"'))
        self.assertNotIn('ev-review', html)
        # The records behind the event are tabs, alternatives rather than a sequence.
        self.assertIn('<div class="gn-tabs ev-tabs" role="tablist" data-tabs="records"', html)
        for panel in ('ed-more', 'ed-prules', 'ed-read', 'ed-audit'):
            self.assertRegex(html, rf'id="{panel}" role="tabpanel"', panel)
        order = [html.index(f'id="{i}"') for i in ('ed-view', 'ed-glance', 'ed-desk', 'ed-ranked', 'ed-ai',
                                                   'ed-more', 'ed-prules', 'ed-read', 'ed-audit', 'ask')]
        self.assertEqual(order, sorted(order), 'page order')
        self.assertNotIn('Keep / Change', html)
        self.assertNotIn('Upload portfolio', html)
        self.assertNotIn('synthetic example', html.lower())
        self.assertIn('Needs your portfolio', html)
        self.assertEqual(1, html.count('<section id="ask" data-context="event"'))
        self.assertIsNone(re.search(r'\son[a-z]+=', html), 'no inline handlers')
        for name in ('event-desk.js', 'event-desk.css', 'journal-box.js', 'journal.css', 'ui.css'):
            self.assertIn(f'/grid/__NOWCAST_STAMP__/{name}', html)
        self.assertLess(html.index('/ui.css'), html.index('/shell.css'))
        self.assertLess(html.index('shell.js'), html.index('journal-box.js'))
        self.assertNotIn('style="', html)

    def test_the_module_writes_text_only_and_fetches_through_the_adapter(self):
        script = (GRID / 'event-desk.js').read_text(encoding='utf-8')
        self.assertNotIn('innerHTML', script)
        self.assertNotIn('fetch(', script)
        shown = '\n'.join(line for line in script.splitlines() if 'TECH_WORDS = new RegExp' not in line)
        self.assertIsNone(re.search(r"'[^'\n]*\b(solar|coal|hydro|geothermal|diesel|bunker)\b[^'\n]*'", shown, re.I),
                          'no shown string names a technology (the withheld list itself is the one exception)')


if __name__ == '__main__':
    unittest.main()
