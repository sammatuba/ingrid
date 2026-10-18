"""ericka-desk slice 3: the dashboard overview (src/grid/overview.js).

The module's rules are pure functions it exposes as `GridOverview`; these tests run them on node
over small synthetic inputs written here (no company data):

- "usual" is the median of the same clock hour on earlier replay days only (E4);
- a plant trip or derate is ringed only when exactly one site matches it; any other notice is
  Unclear, unlinked and uncounted; line trips and later "online" notices clear it (E5);
- the pricing-rules flag says "capped" from the baked prices only (E13);
- a link's direction comes from the flow sign and its limit is never invented (E11);
- a site name that reveals technology or fuel is replaced by its code.
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
const O = sandbox.GridOverview;
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const [name, call] of Object.entries(input)) out[name] = O[call.fn](...call.args);
process.stdout.write(JSON.stringify(out));
"""


def run(calls):
    result = subprocess.run([NODE, '--input-type=module', '-e', DRIVER, '--', str(GRID / 'overview.js')],
                            input=json.dumps(calls), capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-800:])
    return json.loads(result.stdout)


def times(days, hours=('13',)):
    return [f'2026-09-{d}T{h}:{m:02d}' for d in days for h in hours for m in range(0, 60, 5)]


SITES = [
    {'s': '08PEDC', 'k': 'G', 'g': 'CVIS', 'name': 'Sample Plant A'},
    {'s': '05KSPC', 'k': 'G', 'g': 'CVIS', 'name': 'Sample Plant B'},
    {'s': '03TWIN', 'k': 'G', 'g': 'CLUZ', 'name': 'Twin North'},
    {'s': '03TWINB', 'k': 'G', 'g': 'CLUZ', 'name': 'Twin South'},
    {'s': '04LOAD', 'k': 'L', 'g': 'CLUZ', 'name': 'A load'},
]


@unittest.skipUnless(NODE, 'the overview module runs on node; this interpreter has none')
class Usual(unittest.TestCase):
    def test_usual_uses_earlier_days_only(self):
        t = times(['21', '22', '23'])
        base = [100.0] * 12 + [200.0] * 12 + [9000.0] * 12
        later = [100.0] * 12 + [200.0] * 12 + [1.0] * 12
        out = run({
            'day1': {'fn': 'usualAt', 'args': [t, base, 0]},
            'day2': {'fn': 'usualAt', 'args': [t, base, 12]},
            'day2_later_changed': {'fn': 'usualAt', 'args': [t, later, 12]},
            'day3': {'fn': 'usualAt', 'args': [t, base, 30]},
        })
        self.assertIsNone(out['day1']['value'], 'the first replay day has no usual price')
        self.assertEqual(0, out['day1']['days'])
        self.assertEqual(100.0, out['day2']['value'])
        self.assertEqual(out['day2'], out['day2_later_changed'], 'a later day never moves the usual price')
        self.assertEqual(150.0, out['day3']['value'])
        self.assertEqual(2, out['day3']['days'])

    def test_usual_compares_the_same_clock_hour(self):
        t = times(['21', '22'], hours=('12', '13'))
        series = [5.0] * 12 + [50.0] * 12 + [0.0] * 24
        out = run({'at13': {'fn': 'usualAt', 'args': [t, series, 36]}})
        self.assertEqual(50.0, out['at13']['value'])


@unittest.skipUnless(NODE, 'the overview module runs on node; this interpreter has none')
class Trips(unittest.TestCase):
    ADV = [
        {'id': 'V1', 't': '2026-09-21T13:00:00', 'grid': 'CVIS', 'kind': 'trip', 'text': 'PEDC U2 tripped at 1258H'},
        {'id': 'V2', 't': '2026-09-21T13:10:00', 'grid': 'CVIS', 'kind': 'trip', 'text': 'KSPC Unit 2 tripped at 1309H'},
        {'id': 'V3', 't': '2026-09-21T13:20:00', 'grid': 'CVIS', 'kind': 'online', 'text': 'KSPC Unit 2 online at 1319H'},
        {'id': 'L1', 't': '2026-09-21T13:05:00', 'grid': 'CLUZ', 'kind': 'trip', 'text': 'TWIN TWINB 230kV Line tripped'},
        {'id': 'L2', 't': '2026-09-21T13:06:00', 'grid': 'CLUZ', 'kind': 'trip', 'text': 'TWIN and TWINB units tripped'},
        {'id': 'M1', 't': '2026-09-21T13:07:00', 'grid': 'CMIN', 'kind': 'notice', 'text': 'XYZ declared deration from 100MW to 80MW'},
        {'id': 'V4', 't': '2026-09-21T14:00:00', 'grid': 'CVIS', 'kind': 'trip', 'text': 'PEDC U1 tripped at 1359H'},
    ]

    def trips(self, clock):
        return run({'r': {'fn': 'tripsAt', 'args': [clock, self.ADV, SITES, []]}})['r']

    def test_only_a_single_match_is_ringed(self):
        r = self.trips('2026-09-21T13:30')
        self.assertEqual(['08PEDC'], [m['code'] for m in r['matched']])
        unclear = {u['id']: u for u in r['unclear']}
        self.assertEqual(2, unclear['L2']['candidates'], 'two possible plants: none is picked')
        self.assertEqual(0, unclear['M1']['candidates'])
        self.assertEqual('derate', unclear['M1']['kind'])
        self.assertNotIn('code', unclear['L2'], 'an unclear notice names no plant')

    def test_a_line_trip_is_not_a_plant_trip(self):
        r = self.trips('2026-09-21T13:30')
        ids = [m['id'] for m in r['matched']] + [u['id'] for u in r['unclear']]
        self.assertNotIn('L1', ids)

    def test_an_online_notice_clears_the_trip(self):
        self.assertIn('05KSPC', [m['code'] for m in self.trips('2026-09-21T13:15')['matched']])
        self.assertNotIn('05KSPC', [m['code'] for m in self.trips('2026-09-21T13:30')['matched']])

    def test_nothing_after_the_clock(self):
        r = self.trips('2026-09-21T13:30')
        self.assertNotIn('V4', [m['id'] for m in r['matched']])

    def test_the_event_record_names_the_site_first(self):
        events = [{'advisory': 'L2', 'site': '03TWIN'}]
        r = run({'r': {'fn': 'tripsAt', 'args': ['2026-09-21T13:30', self.ADV, SITES, events]}})['r']
        self.assertIn('03TWIN', [m['code'] for m in r['matched']])


@unittest.skipUnless(NODE, 'the overview module runs on node; this interpreter has none')
class Flags(unittest.TestCase):
    def test_rules_flag_from_the_baked_prices(self):
        out = run({
            'cap': {'fn': 'rulesFlag', 'args': [{'lmp_median': 32000, 'lmp_max': 32000}]},
            'node': {'fn': 'rulesFlag', 'args': [{'lmp_median': 9000, 'lmp_max': 32000}]},
            'near': {'fn': 'rulesFlag', 'args': [{'lmp_median': 31500, 'lmp_max': 31600}]},
            'ok': {'fn': 'rulesFlag', 'args': [{'lmp_median': 5000, 'lmp_max': 7000}]},
            'none': {'fn': 'rulesFlag', 'args': [None]},
        })
        self.assertEqual(['bad', 'warn', 'warn', 'ok', 'none'],
                         [out[k]['level'] for k in ('cap', 'node', 'near', 'ok', 'none')])

    def test_link_direction_and_no_invented_limit(self):
        link = {'flow': [120, -80, None, 0], 'congested': [1, 0, None, 0]}
        out = {i: run({'r': {'fn': 'linkAt', 'args': ['MINVIS1', link, i]}})['r'] for i in range(4)}
        self.assertEqual('Mindanao → Visayas', out[0]['direction'])
        self.assertTrue(out[0]['congested'])
        self.assertEqual('Visayas → Mindanao', out[1]['direction'])
        self.assertEqual(80, out[1]['flow'])
        self.assertEqual('No data', out[2]['direction'])
        self.assertIsNone(out[2]['congested'])
        self.assertEqual('No flow', out[3]['direction'])
        for row in out.values():
            self.assertIsNone(row['limit'], 'no limit is on record in the bake')

    def test_a_name_that_reveals_fuel_is_replaced_by_the_code(self):
        out = run({
            'fuel': {'fn': 'safeName', 'args': ['01ABC', 'Sample Solar Farm']},
            'geo': {'fn': 'safeName', 'args': ['02DEF', 'Sample Geothermal B']},
            'plain': {'fn': 'safeName', 'args': ['03GHI', 'Concepcion']},
            'none': {'fn': 'safeName', 'args': ['04JKL', None]},
        })
        self.assertEqual({'fuel': '01ABC', 'geo': '02DEF', 'plain': 'Concepcion', 'none': '04JKL'}, out)


class Page(unittest.TestCase):
    def test_the_page_carries_the_overview_and_loads_it_under_the_stamp(self):
        html = (GRID / 'index.html').read_text(encoding='utf-8')
        for ident in ('overview', 'ov-cards', 'ov-asof', 'ov-links', 'ov-congestion', 'ov-trips', 'ov-scope', 'map-trips'):
            self.assertIn(f'id="{ident}"', html)
        self.assertIn('/grid/__NOWCAST_STAMP__/overview.js', html)
        self.assertIn('/grid/__NOWCAST_STAMP__/overview.css', html)
        self.assertNotIn('style="', html)

    def test_the_module_fetches_nothing_and_writes_no_html(self):
        script = (GRID / 'overview.js').read_text(encoding='utf-8')
        self.assertNotIn('fetch(', script)
        self.assertNotIn('innerHTML', script, 'every figure is set as text')
        self.assertIsNone(re.search(r"'(No limit|Usual)[^']*\b(solar|coal|hydro|geothermal|diesel)\b", script, re.I))


class StateCardLinks(unittest.TestCase):
    """DESKFIX-1: the HVDC rows are entity links that scope the map to the link, the counts in
    force are links to the notices page. The module renders with the DOM (no HTML strings), so
    these pin the source; tests/test_grid_page.py walks the rows in the browser."""

    @classmethod
    def setUpClass(cls):
        cls.script = (GRID / 'overview.js').read_text(encoding='utf-8')
        cls.css = (GRID / 'overview.css').read_text(encoding='utf-8')

    def test_an_hvdc_row_is_the_links_entity_link(self):
        self.assertIn("const row = make('a', 'ov-link' + (l.congested ? ' hot' : ''));", self.script)
        self.assertIn("row.href = '/?link=' + encodeURIComponent(l.id);", self.script)
        self.assertIn("row.setAttribute('data-entity', 'link:' + l.id);", self.script)
        self.assertNotIn("make('button', 'ov-link-name'", self.script, 'the name is no longer a button of its own')

    def test_a_pressed_row_scopes_the_map_and_names_the_link_in_the_address(self):
        self.assertIn("m.focusLink(l.id);", self.script)
        self.assertIn("linkToUrl(l.id);", self.script)
        self.assertIn("u.searchParams.set('link', id);", self.script)
        self.assertNotIn("e.link(l.id)", self.script, 'the row opens no drawer over the card')

    def test_each_count_in_force_links_to_the_notices_at_the_clock(self):
        self.assertIn("const chip = make('a', 'ov-sev-c ' + k + (n ? '' : ' zero'));", self.script)
        self.assertIn("chip.href = '/notices?at=' + String(t || '').replace(' ', 'T').slice(0, 16);", self.script)
        self.assertIn("chip.dataset.severity = k;", self.script)
        self.assertNotIn("/alerts?level=", self.script, 'the counts are notice severities, not the price-alert levels')

    def test_the_targets_are_at_least_24px_and_no_inline_style(self):
        self.assertIn('.overview a.ov-link, .overview a.ov-link:hover {', self.css)
        self.assertRegex(self.css, r'\.overview a\.ov-link[^\n]*min-height: 24px')
        self.assertRegex(self.css, r'\.ov-sev-c \{[^\n]*height: 24px')
        self.assertIn('.overview a.ov-link:focus-visible {', self.css)
        self.assertIn('.overview a.ov-sev-c:focus-visible {', self.css)
        self.assertNotIn('.style.', self.script.split('function renderLinks')[1].split('function renderTrips')[0].replace('dot.style.background', ''))


if __name__ == '__main__':
    unittest.main()
