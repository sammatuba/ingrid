"""The notices around a replay alert, never claimed as its cause (src/alerts/notices.py).

Owner rule: under 50% sure a name matches, do not match; flag and show the uncertainty. Every
notice, site and price here is SYNTHETIC (made up for the test); nothing is read from the real bake.
The front-end checks run the pure parts of dash-alerts.js and spike.js on node, skipped without it.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from src.alerts import notices, replay  # noqa: E402
from src.alerts.service import AlertService  # noqa: E402
from src.alerts.store import MemoryAlertStore  # noqa: E402
from test_alerts_desk import synthetic_bake  # noqa: E402

NODE = shutil.which('node')
GRID = ROOT / 'src' / 'grid'
SITES = [{'s': '08ABCD', 'g': 'CVIS'}, {'s': '08QRS1', 'g': 'CVIS'}, {'s': '08QRS2', 'g': 'CVIS'},
         {'s': '08STAX', 'g': 'CVIS'}, {'s': '01LUZA', 'g': 'CLUZ'}]
SPIKE_AT = '2026-09-22T13:40'
NOTICES = [
    # (id, region, posted, kind, text)
    ('N-OLD', 'CVIS', '2026-09-22T06:30:00', 'trip', 'ABCD Unit 1 tripped at 0630H'),          # 7h10 before: out
    ('N-ONE', 'CVIS', '2026-09-22T13:20:00', 'trip', 'ABCD Unit 2 tripped at 1318H with 80 MW'),  # names one plant
    ('N-TWO', 'CVIS', '2026-09-22T12:00:00', 'trip', 'QRS Unit 3 tripped at 1158H'),           # fits two plants
    ('N-SS', 'CVIS', '2026-09-22T11:00:00', 'notice', 'STAX SS 100MVA Power Transformer No. 1 de-energized at 1100H (Planned Outage)'),
    ('N-NONE', 'CVIS', '2026-09-22T10:00:00', 'trip', 'Zeta Unit 1 tripped at 1000H'),          # names no plant
    ('N-LINK', 'CLUZ', '2026-09-22T09:05:00', 'notice', 'Ormoc-Naga 350kV HVDC (Visayas-Luzon) blocked at 0903H from forward power direction'),
    ('N-LINK2', 'CVIS', '2026-09-22T09:06:00', 'notice', 'Ormoc-Naga 350kV HVDC (Visayas-Luzon) blocked at 0903H from forward power direction'),
    ('N-BACK', 'CVIS', '2026-09-22T12:30:00', 'online', 'QRS1 Unit 1 online at 1230H'),          # a return: not listed
    ('N-TECH', 'CVIS', '2026-09-22T12:40:00', 'trip', 'Alpha Solar Geothermal U1 tripped at 1240H'),
    ('N-LATE', 'CVIS', '2026-09-22T14:10:00', 'trip', 'ABCD Unit 3 tripped at 1335H'),          # posted after 13:40
    ('N-AFTER', 'CVIS', '2026-09-22T13:50:00', 'trip', 'ABCD Unit 4 tripped at 1350H'),        # after the alert's last
]


def bake(directory, sites=SITES):
    synthetic_bake(directory, spikes=[('CVIS', SPIKE_AT, 32000)], notices=NOTICES)
    if sites is not None:
        (Path(directory) / 'sites.json').write_text(json.dumps(sites))


class AroundAnAlert(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        bake(self.tmp.name)
        self.replay = replay.Replay(self.tmp.name)
        self.rules = replay.DEFAULT_RULES

    def alert(self, at=None):
        return next(a for a in self.replay.alerts(self.rules, at) if a['region'] == 'CVIS' and a['first'] == SPIKE_AT)

    def items(self, a):
        return {i['id']: i for i in a['notices_around']['items']}

    def test_the_window_is_six_hours_before_to_the_last_interval_and_returns_are_left_out(self):
        got = self.items(self.alert())
        self.assertEqual({'N-ONE', 'N-TWO', 'N-SS', 'N-NONE', 'N-TECH', 'N-LATE'} | {'N-LINK'}, set(got))
        self.assertNotIn('N-OLD', got)    # 7 hours 10 minutes before
        self.assertNotIn('N-BACK', got)   # back online is not an outage
        self.assertNotIn('N-AFTER', got)  # after the alert's last interval

    def test_no_look_ahead_a_notice_posted_after_the_clock_is_not_listed(self):
        early = self.items(self.alert('2026-09-22T13:40'))
        self.assertNotIn('N-LATE', early)  # its event time is 13:35 but it was posted at 14:10
        self.assertIn('N-LATE', self.items(self.alert('2026-09-22T14:10')))
        # an earlier clock cuts both the alert and its notices
        for at in ('2026-09-22T12:39', '2026-09-22T13:19'):
            cut = [a for a in self.replay.alerts(self.rules, at) if a['region'] == 'CVIS' and a['first'] == SPIKE_AT]
            self.assertEqual([], cut)  # the alert itself starts at 13:40
        page = self.replay.notices_around({'region': 'CVIS', 'direction': 'spike', 'first': SPIKE_AT, 'last': SPIKE_AT},
                                          '2026-09-22T13:00')
        self.assertTrue(all(i['posted'] <= '2026-09-22T13:00' for i in page['items']))
        self.assertNotIn('N-ONE', {i['id'] for i in page['items']})

    def test_labels_say_how_sure_the_plant_match_is(self):
        got = self.items(self.alert())
        one = got['N-ONE']
        self.assertEqual(('plant', 'Names a plant in this region', '08ABCD', '/plant/08ABCD'),
                         (one['match'], one['match_label'], one['plant'], one['plant_href']))
        two = got['N-TWO']
        self.assertEqual(('unclear', 'Unclear', None, None), (two['match'], two['match_label'], two['plant'], two['plant_href']))
        self.assertIn('fit 2 Visayas plants (08QRS1, 08QRS2)', two['reason'])
        station = got['N-SS']  # a substation sharing a plant's letters is not that plant
        self.assertEqual(('unclear', None), (station['match'], station['plant_href']))
        self.assertIn('no plant is matched', station['reason'])
        self.assertEqual('none', got['N-NONE']['match'])
        link = got['N-LINK']
        self.assertEqual('link', link['match'])
        self.assertIn('filed under Luzon', link['reason'])
        counts = self.alert()['notices_around']['counts']
        self.assertEqual('08ABCD', got['N-LATE']['plant'])
        self.assertEqual({'plant': 2, 'unclear': 2, 'link': 1, 'none': 2}, {k: v for k, v in counts.items() if v})

    def test_never_the_cause_and_every_item_says_so(self):
        a = self.alert()
        self.assertIsNone(a['cause'])
        self.assertEqual('/alert/' + a['key'], a['href'])
        self.assertFalse(a['notices_around']['confirmed'])
        self.assertTrue(all(i['claimed'] is False for i in a['notices_around']['items']))
        self.assertTrue(a['main_driver'].startswith('None on record; 7 outage, trip or grid notices'))
        self.assertIn('(not confirmed as the cause)', a['main_driver'])

    def test_the_trigger_rule_score_is_stated_and_never_confirms(self):
        # at 13:40 the later ABCD notice is not posted yet: 0.35 + 0.25 (20 minutes) + 0.10 (80 MW) - 0.10 (one Unclear)
        one = self.items(self.alert('2026-09-22T13:40'))['N-ONE']
        self.assertEqual(0.6, one['rule_score'])
        self.assertIn('no event is recorded for it: not confirmed', one['rule_text'])
        # once it is posted it competes (-0.15) and the score falls under 0.50: not matched
        later = self.items(self.alert())['N-ONE']
        self.assertEqual(0.45, later['rule_score'])
        self.assertIn('under 0.50: not matched', later['rule_text'])
        self.assertNotIn('rule_score', self.items(self.alert())['N-TWO'])  # Unclear: no plant, no score

    def test_one_link_notice_filed_under_both_regions_is_listed_once(self):
        ids = [i['id'] for i in self.alert()['notices_around']['items']]
        self.assertEqual(1, sum(1 for i in ids if i.startswith('N-LINK')))

    def test_no_technology_or_fuel_words(self):
        text = json.dumps(self.replay.alerts(self.rules)).lower()
        for word in ('solar', 'geothermal', 'coal', 'hydro', 'diesel', 'fuel'):
            self.assertNotIn(word, text)
        self.assertIn('Alpha […] U1 tripped at 12:40', self.items(self.alert())['N-TECH']['text'])

    def test_without_a_site_list_nothing_is_matched_to_a_plant(self):
        with tempfile.TemporaryDirectory() as d:
            bake(d, sites=None)
            a = next(x for x in replay.Replay(d).alerts(self.rules) if x['region'] == 'CVIS' and x['first'] == SPIKE_AT)
        got = {i['id']: i for i in a['notices_around']['items']}
        self.assertEqual('unclear', got['N-ONE']['match'])
        self.assertIsNone(got['N-ONE']['plant_href'])
        self.assertFalse(a['notices_around']['sites_read'])


class Service(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        bake(self.tmp.name)
        self.svc = AlertService(MemoryAlertStore(), replay=replay.Replay(self.tmp.name), clock=lambda: '2026-10-18T00:00:00Z')

    def test_the_inbox_carries_the_nearest_three_and_the_page_all(self):
        lead = next(a for g in self.svc.inbox(None)['groups'] for a in g['alerts']
                    if a['region'] == 'CVIS' and a['first'] == SPIKE_AT)
        self.assertIsNone(lead['cause'])
        self.assertEqual(7, lead['notices_around']['count'])
        self.assertEqual(3, len(lead['notices_around']['items']))
        self.assertEqual(['N-TECH', 'N-ONE', 'N-LATE'], [i['id'] for i in lead['notices_around']['items']])
        self.assertNotIn('rule', lead['notices_around'])  # the reasons and the rule stay on the alert page
        self.assertNotIn('reason', lead['notices_around']['items'][0])
        self.assertFalse(lead['notices_around']['confirmed'])
        page = self.svc.alert(None, lead['key'])
        self.assertEqual(7, len(page['alert']['notices_around']['items']))
        self.assertTrue(all(i['reason'] for i in page['alert']['notices_around']['items']))
        early = self.svc.alert(None, lead['key'], '2026-09-22T13:40')
        self.assertNotIn('N-LATE', [i['id'] for i in early['alert']['notices_around']['items']])


DRIVER = r"""
import { readFileSync } from 'fs';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const A = require(process.argv[process.argv.length - 1]);
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const [name, call] of Object.entries(input)) out[name] = A[call.fn](...call.args);
process.stdout.write(JSON.stringify(out));
"""


def run(path, calls):
    result = subprocess.run([NODE, '--input-type=module', '-e', DRIVER, '--', str(path)],
                            input=json.dumps(calls), capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-800:])
    return json.loads(result.stdout)


@unittest.skipUnless(NODE, 'the modules run on node; this interpreter has none')
class FrontEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            bake(d)
            svc = AlertService(MemoryAlertStore(), replay=replay.Replay(d), clock=lambda: '2026-10-18T00:00:00Z')
            cls.group = next(g for g in svc.inbox(None)['groups'] if g['alerts'][0]['first'] == SPIKE_AT
                             and g['alerts'][0]['region'] == 'CVIS')
            cls.page = svc.alert(None, cls.group['alerts'][0]['key'])

    def test_the_dashboard_card_lists_notices_marked_not_confirmed(self):
        c = run(GRID / 'dash-alerts.js', {'c': {'fn': 'card', 'args': [self.group]}})['c']
        self.assertTrue(c['noCause'])
        self.assertEqual(7, c['noticesAround'])
        self.assertIn('7 notices around it, none confirmed (2 name a plant, 2 unclear)', c['sure'])
        lines = [s for s in c['steps'] if 'Notice N-' in s]
        self.assertEqual(3, len(lines))
        self.assertTrue(all('not confirmed as the cause' in s for s in lines))
        self.assertTrue(any('Names a plant in this region' in s for s in lines))
        self.assertIn('4 earlier notices around it on the alert page (not confirmed as the cause)', c['steps'])

    def test_the_alert_page_section_links_only_a_confident_plant(self):
        v = run(GRID / 'spike.js', {'r': {'fn': 'related', 'args': [self.page]}})['r']
        self.assertIn('2 name a plant in this region, 2 unclear, 1 names an interconnection link, 2 with no plant matched', v['note'])
        self.assertIn('None is confirmed as the cause', v['note'])
        rows = {r['id']: r for r in v['rows']}
        self.assertEqual({'href': '/plant/08ABCD', 'code': '08ABCD'}, rows['N-ONE']['plant'])
        self.assertIsNone(rows['N-TWO']['plant'])
        self.assertEqual('unclear', rows['N-TWO']['tone'])
        self.assertTrue(rows['N-TWO']['notice'].startswith('/notices?at=2026-09-22T12:00#adv-N-TWO'))


if __name__ == '__main__':
    unittest.main()
