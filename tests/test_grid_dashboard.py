"""ericka-desk: the dashboard follows the design canvas's Main board.

- "Grid now": a status pill per grid from the reserve and the operator's own alert notice only;
- the alerts beside the notices: one card per risk event, the peso impact never computed
  ("Needs your portfolio"), a cause linked only when an event is on record;
- the older blocks keep their markup (the scripts and their tests use the ids) but are folded away.

Synthetic inputs written here; no company data.
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

OVERVIEW = r"""
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

ALERTS = r"""
import { readFileSync } from 'fs';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const A = require(process.argv[process.argv.length - 1]);
const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};
for (const [name, call] of Object.entries(input)) out[name] = A[call.fn](...call.args);
process.stdout.write(JSON.stringify(out));
"""

MAP_MATH = r"""
import { readFileSync } from 'fs';
import vm from 'vm';
const sandbox = {};
sandbox.window = sandbox;
vm.runInNewContext(readFileSync(process.argv[process.argv.length - 1], 'utf8'), sandbox);
const M = sandbox.GridMap;
const fit = M.math.fitTransform(1200, 700);
const out = { fit, box: M.GRID_BOX, none: M.math.scopeTransform(1200, 700, null), odd: M.math.scopeTransform(1200, 700, 'XX') };
for (const g of ['CLUZ', 'CVIS', 'CMIN']) {
  const t = M.math.scopeTransform(1200, 700, g);
  out[g] = { t };
}
process.stdout.write(JSON.stringify(out));
"""


def run(driver, path, calls):
    result = subprocess.run([NODE, '--input-type=module', '-e', driver, '--', str(path)],
                            input=json.dumps(calls), capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-800:])
    return json.loads(result.stdout)


NOTES = [
    {'id': 'S1', 't': '2026-09-21T10:00:00', 'grid': 'CVIS', 'kind': 'yellow', 'text': 'synthetic yellow'},
    {'id': 'S2', 't': '2026-09-21T10:30:00', 'grid': 'CVIS', 'kind': 'trip', 'text': 'synthetic trip'},
    {'id': 'S3', 't': '2026-09-21T11:00:00', 'grid': 'CVIS', 'kind': 'mld', 'text': 'synthetic load drop'},
    {'id': 'S4', 't': '2026-09-21T10:00:00', 'grid': 'CLUZ', 'kind': 'red', 'text': 'synthetic red'},
]


@unittest.skipUnless(NODE, 'the modules run on node; this interpreter has none')
class Status(unittest.TestCase):
    def test_the_status_comes_from_the_reserve_and_the_operator_notice_only(self):
        out = run(OVERVIEW, GRID / 'overview.js', {
            'before': {'fn': 'gridAlertAt', 'args': ['2026-09-21T10:45', NOTES, 'CVIS']},
            'after': {'fn': 'gridAlertAt', 'args': ['2026-09-21T11:05', NOTES, 'CVIS']},
            'stale': {'fn': 'gridAlertAt', 'args': ['2026-09-21T15:05', NOTES, 'CVIS']},
            'early': {'fn': 'gridAlertAt', 'args': ['2026-09-21T09:55', NOTES, 'CVIS']},
            'ok': {'fn': 'statusOf', 'args': [{'dr_short_mw': 0}, None]},
            'short': {'fn': 'statusOf', 'args': [{'dr_short_mw': 40}, {'kind': 'yellow'}]},
            'yellow': {'fn': 'statusOf', 'args': [{'dr_short_mw': 0}, {'kind': 'yellow'}]},
            'red': {'fn': 'statusOf', 'args': [{'dr_short_mw': 0}, {'kind': 'red'}]},
            'none': {'fn': 'statusOf', 'args': [None, None]},
        })
        self.assertEqual('S1', out['before']['id'])
        self.assertEqual('mld', out['after']['kind'], 'the latest notice up to the clock')
        self.assertIsNone(out['stale'], 'older than four hours')
        self.assertIsNone(out['early'], 'nothing after the clock')
        self.assertEqual(('ok', 'Normal'), (out['ok']['level'], out['ok']['text']))
        self.assertEqual('Reserves short', out['short']['text'])
        self.assertEqual('Yellow alert', out['yellow']['text'])
        self.assertEqual('Red alert', out['red']['text'])
        self.assertEqual('No data', out['none']['text'])


GROUP = {
    'id': 'event:syn', 'severity': 'extreme', 'regions': ['CVIS'], 'first': '2026-09-21T09:35', 'last': '2026-09-21T14:05',
    'cause': {'kind': 'event', 'id': 'syn', 'title': 'SYN U1 tripped', 'advisory': 'S2', 'known_at': '2026-09-21T10:30', 'href': '/event/syn'},
    'financial_impact': {'status': 'Needs your portfolio'}, 'next_step': 'Open the event.',
    'alerts': [{'region': 'CVIS', 'direction': 'spike', 'first': '2026-09-21T09:35', 'interval_manila': '2026-09-21T11:00',
                'price_php_mwh': 32000, 'threshold_text': 'price at or above 15,000 PHP/MWh', 'severity_reason': 'at the offer cap',
                'main_driver': 'SYN U1 tripped (notice S2 at 10:30)', 'href': '/event/syn',
                'financial_impact': {'status': 'Needs your portfolio'}}],
}
LONE = {
    'id': 'alert:x', 'severity': 'high', 'regions': ['CLUZ'], 'first': '2026-09-21T15:15', 'last': '2026-09-21T15:15', 'cause': None,
    'alerts': [{'region': 'CLUZ', 'direction': 'spike', 'first': '2026-09-21T15:15', 'interval_manila': '2026-09-21T15:15',
                'href': 'https://elsewhere.example/x', 'financial_impact': {'status': 'Needs your portfolio'}}],
}


@unittest.skipUnless(NODE, 'the modules run on node; this interpreter has none')
class AlertCards(unittest.TestCase):
    def test_a_risk_event_card_follows_the_canvas_and_invents_no_peso_figure(self):
        out = run(ALERTS, GRID / 'dash-alerts.js', {'c': {'fn': 'card', 'args': [GROUP]}, 'l': {'fn': 'card', 'args': [LONE]}})
        c, lone = out['c'], out['l']
        self.assertEqual('SYN U1 tripped', c['title'])
        self.assertEqual('21 Sep 09:35–14:05', c['window'])
        self.assertEqual('Needs your portfolio', c['cost'])
        self.assertIn('Linked to notice S2', c['sure'])
        self.assertEqual('/event/syn', c['open'])
        self.assertEqual('/event/syn#ed-journal-box', c['journal'])
        self.assertEqual(['09:35 Visayas price over its level (price at or above 15,000 PHP/MWh)',
                          '10:30 Notice S2: SYN U1 tripped', '11:00 Visayas price reached ₱32,000/MWh'], c['steps'])
        self.assertEqual('Luzon price spike', lone['title'])
        self.assertIn('not linked', lone['sure'], 'no cause on record: no link is guessed')
        self.assertEqual('/alerts', lone['open'], 'a foreign link is never followed')
        self.assertEqual('Needs your portfolio', lone['cost'])
        self.assertEqual('Open event', c['openText'])
        self.assertFalse(c['noCause'])

    def test_a_card_has_no_assignee_line(self):
        # Alert assignment was removed: no "Unassigned" / "Assigned to" on a card, even if an
        # older answer still carried an assignee.
        stale = dict(GROUP, alerts=[dict(GROUP['alerts'][0], assignee={'email': 'someone@example.invalid'})])
        out = run(ALERTS, GRID / 'dash-alerts.js', {'c': {'fn': 'card', 'args': [stale]}})
        self.assertNotIn('assignee', out['c'])
        self.assertNotIn('someone@example.invalid', json.dumps(out['c']))
        script = (GRID / 'dash-alerts.js').read_text(encoding='utf-8')
        for word in ('assignee', 'Unassigned', 'Assigned to', 'da-assignee'):
            self.assertNotIn(word, script)
        self.assertNotIn('da-assignee', (GRID / 'dashboard.css').read_text(encoding='utf-8'))

    def test_alerts_keep_the_clock_day_as_the_notices_do(self):
        # The notices beside the panel show from the clock's day 00:00 up to the clock; the alerts
        # did not (every alert of the replay so far showed at 00:00). Same gate now.
        older = dict(LONE, id='alert:old', first='2026-09-20T16:00', last='2026-09-20T22:45',
                     alerts=[dict(LONE['alerts'][0], first='2026-09-20T16:00', last='2026-09-20T22:45',
                                  interval_manila='2026-09-20T22:45')])
        overnight = dict(LONE, id='alert:night', first='2026-09-20T23:50', last='2026-09-21T00:10',
                         alerts=[dict(LONE['alerts'][0], first='2026-09-20T23:50', last='2026-09-21T00:10')])
        later = dict(LONE, id='alert:late', first='2026-09-21T16:00', last='2026-09-21T16:00',
                     alerts=[dict(LONE['alerts'][0], first='2026-09-21T16:00', last='2026-09-21T16:00',
                                  interval_manila='2026-09-21T16:00')])
        no_time = dict(LONE, id='alert:none', first=None, last=None,
                       alerts=[dict(LONE['alerts'][0], first=None, last=None, interval_manila=None)])
        groups = [GROUP, LONE, older, overnight, later, no_time]
        out = run(ALERTS, GRID / 'dash-alerts.js', {
            'start': {'fn': 'sinceDayStart', 'args': [groups, '2026-09-21T00:00']},
            'noon': {'fn': 'sinceDayStart', 'args': [groups, '2026-09-21T15:30']},
            'none': {'fn': 'sinceDayStart', 'args': [groups, None]},
        })
        ids = lambda k: [g['id'] for g in out[k]]
        self.assertEqual([], ids('start'), 'at 00:00 no alert of an earlier day is shown')
        self.assertEqual(['event:syn', 'alert:x', 'alert:night'], ids('noon'))
        self.assertEqual([], ids('none'), 'no clock, no alert')
        script = (GRID / 'dash-alerts.js').read_text(encoding='utf-8')
        self.assertIn('const groups = sinceDayStart(r.groups, at);', script)

    def test_an_alert_with_no_recorded_event_opens_its_own_alert_page(self):
        # ericka-desk: `/alert/<key>` for an alert no event explains; `/event/` is for recorded events.
        key = '5e7' + '0' * 21
        own = dict(LONE, alerts=[dict(LONE['alerts'][0], href='/alert/' + key)])
        bad = dict(LONE, alerts=[dict(LONE['alerts'][0], href='/alert/' + key.upper())])
        out = run(ALERTS, GRID / 'dash-alerts.js', {'a': {'fn': 'card', 'args': [own]}, 'b': {'fn': 'card', 'args': [bad]}})
        a, b = out['a'], out['b']
        self.assertEqual('/alert/' + key, a['open'])
        self.assertEqual('Open alert', a['openText'])
        self.assertTrue(a['noCause'], 'the no-cause pill stays')
        self.assertEqual('/alert/' + key + '#sp-journal', a['journal'])
        self.assertEqual('/alerts', b['open'], 'only a 24-hex lowercase key is an alert page')


class Page(unittest.TestCase):
    HTML = (GRID / 'index.html').read_text(encoding='utf-8')

    def test_the_canvas_sections_are_on_the_page_and_the_hvdc_card_stays_its_own(self):
        for ident in ('now-h', 'ov-links', 'map-h', 'da-list', 'da-count', 'da-filters', 'outages', 'detail', 'feed'):
            self.assertIn(f'id="{ident}"', self.HTML)
        self.assertIn('<h3 id="ov-links-title">HVDC links</h3>', self.HTML)
        self.assertIn('>Operator notices</h2>', self.HTML)
        for name in ('dash-alerts.js', 'dashboard.css'):
            self.assertIn(f'/grid/__NOWCAST_STAMP__/{name}', self.HTML)
        # UX-3: the map is the page. The state card, the pills, the replay and the detail drawer
        # float inside the map section; the outage tracker and the scope summary (E6) follow
        # under it, beside the alerts and the notices.
        desk_map = self.HTML[self.HTML.index('<section class="map-wrap desk-map"'):self.HTML.index('<div class="desk-below gn-page">')]
        for ident in ('map', 'overview', 'map-toolbar', 'map-replay'):
            self.assertIn(f'id="{ident}"', desk_map, ident)
        # the detail drawer follows the map in the markup: over its left column on a wide screen,
        # under it on a phone (dashboard.css), so it never covers the map a phone reader taps
        side = self.HTML[self.HTML.index('<aside class="dash-side"'):self.HTML.index('</aside>')]
        self.assertIn('id="detail"', side, 'the detail drawer')
        self.assertLess(self.HTML.index('<section class="map-wrap desk-map"'), self.HTML.index('<aside class="dash-side"'))
        self.assertLess(self.HTML.index('<aside class="dash-side"'), self.HTML.index('<div class="desk-below gn-page">'))
        below = self.HTML[self.HTML.index('<div class="desk-below gn-page">'):self.HTML.index('<section class="col left"')]
        for ident in ('outages', 'ov-scope', 'dash-alerts', 'feed'):
            self.assertIn(f'id="{ident}"', below, ident)
        self.assertNotIn('style="', self.HTML)
        self.assertNotIn('id="ov-status"', self.HTML, 'the HVDC card has the second row to itself')
        self.assertNotIn("' on'", (GRID / 'overview.js').read_text(encoding='utf-8'), 'no grid card is highlighted')

    def test_the_older_blocks_are_folded_away_by_the_layout(self):
        css = (GRID / 'dashboard.css').read_text(encoding='utf-8')
        self.assertIn('.desk > .front, .desk > #ask, .desk > .col.left, .desk > .chart-wrap', css)
        # UX-3: the map fills the first screen under the shared bar, full-bleed, and the rest
        # follows under it in one band
        self.assertIn('height: calc(100vh - var(--bar-h, var(--gn-bar-h, 96px))); min-height: 560px;', css)
        # PP-B5: the band is the design system's matrix, the decisions in the 2/3, the context in
        # the 1/3 (ui.css lays it out; the page adds no grid of its own)
        html = (GRID / 'index.html').read_text(encoding='utf-8')
        below = html[html.index('<div class="desk-below gn-page">'):html.index('<section class="col left"')]
        self.assertIn('<div class="gn-grid gn-grid--main-side">', below)
        main = below[below.index('<div class="below-main">'):below.index('<aside class="below-side"')]
        side = below[below.index('<aside class="below-side"'):]
        for ident in ('dash-alerts', 'notices', 'feed'):
            self.assertIn(f'id="{ident}"', main, ident)
        for ident in ('outages', 'ov-scope'):
            self.assertIn(f'id="{ident}"', side, ident)
        # each section has its head and its sources, collapsed
        self.assertEqual(3, below.count('<footer class="gn-sources"><details><summary>Sources and method</summary>'))
        self.assertNotIn('<details open', below)
        self.assertNotIn('grid-template-areas', css)

    def test_the_alerts_module_writes_text_only(self):
        script = (GRID / 'dash-alerts.js').read_text(encoding='utf-8')
        self.assertNotIn('innerHTML', script)
        self.assertIsNone(re.search(r"'[^']*\b(solar|coal|hydro|geothermal|diesel|bunker)\b[^']*'", script, re.I))


@unittest.skipUnless(NODE, 'the modules run on node; this interpreter has none')
class MapZoom(unittest.TestCase):
    """Picking a grid on the dashboard map zooms to that grid; All grids fits the whole country."""

    def test_a_grid_zooms_in_and_centres_on_its_box(self):
        out = run(MAP_MATH, GRID / 'map.js', {})
        fit = out['fit']
        self.assertEqual(out['none'], fit)
        self.assertEqual(out['odd'], fit)
        for g in ('CLUZ', 'CVIS', 'CMIN'):
            t = out[g]['t']
            self.assertGreater(t['k'], fit['k'] * 1.2, g)
            self.assertNotEqual((t['fx'], t['fy']), (fit['fx'], fit['fy']), g)
        # Luzon is the north: its centre sits above Mindanao's on the plane (y grows south)
        self.assertLess(out['CLUZ']['t']['fy'], out['CMIN']['t']['fy'])


@unittest.skipUnless(NODE, 'the modules run on node; this interpreter has none')
class MapLayers(unittest.TestCase):
    """The "Show on map" list: one row per layer with its count for the grid in view."""

    SITES = [
        {'s': 'A', 'g': 'CLUZ', 'k': 'G'}, {'s': 'B', 'g': 'CLUZ', 'k': 'NL'},
        {'s': 'C', 'g': 'CVIS', 'k': 'G'}, {'s': 'D', 'g': 'CLUZ', 'k': 'G', 'p': 'placeholder'},
    ]

    def test_counts_follow_the_scope_and_an_off_layer_says_off(self):
        # UX-3: the pills at the top of the map. Events counts the notice marks the map drew
        # (a mark of several notices counts each), Congestion the links congested at the clock.
        snap = {'price': {'drawn': 3}, 'markers': [{'n': 1}, {'n': 2}],
                'links': [{'congested': True}, {'congested': None}]}
        out = run(ALERTS, GRID / 'dash-map.js', {
            'all': {'fn': 'rows', 'args': [self.SITES, None, snap, None]},
            'luz': {'fn': 'rows', 'args': [self.SITES, 'CLUZ', snap, {'loads': False, 'messages': False}]},
            'sub': {'fn': 'shownText', 'args': [self.SITES, 'CLUZ', None, '2026-09-21T14:05']},
        })
        allc = {r['key']: r['count'] for r in out['all']}
        self.assertEqual(allc, {'prices': '3', 'congestion': '1', 'events': '3', 'plants': '2', 'loads': '1'})
        # PP-B5: the lower-priority layer sits in the "More" popover, so the toolbar is one row
        self.assertEqual(['loads'], [r['key'] for r in out['all'] if r['more']])
        luz = {r['key']: (r['on'], r['count']) for r in out['luz']}
        self.assertEqual(luz['plants'], (True, '1'))
        self.assertEqual(luz['loads'], (False, 'off'))
        self.assertEqual(luz['events'], (False, 'off'), 'the Events pill is off when either of its layers is')
        chips = {r['key']: r['chips'] for r in out['all']}
        self.assertEqual(['events', 'messages'], chips['events'])
        self.assertEqual(['interconnectors'], chips['congestion'])
        self.assertTrue(out['sub'].startswith('14:05 · 2 sites shown'))
        for r in out['all']:
            self.assertLessEqual(len(r['label']), 16, r['label'])

    def test_an_approximate_site_counts_in_its_layer_and_never_in_the_unplaced_chip(self):
        sites = self.SITES + [{'s': 'E', 'g': 'CLUZ', 'k': 'G', 'p': 'approximate'},
                              {'s': 'F', 'g': 'CLUZ', 'k': 'NL', 'p': 'approximate'}]
        out = run(ALERTS, GRID / 'dash-map.js', {
            'all': {'fn': 'rows', 'args': [sites, None, None, None]},
            'sub': {'fn': 'shownText', 'args': [sites, 'CLUZ', None, '2026-09-21T14:05']},
        })
        rows = {r['key']: r for r in out['all']}
        self.assertEqual(('3', 1), (rows['plants']['count'], rows['plants']['approx']))
        self.assertEqual(('2', 1), (rows['loads']['count'], rows['loads']['approx']))
        self.assertTrue(out['sub'].startswith('14:05 · 4 sites shown, 2 at approximate positions'), out['sub'])
        # the chip counts the snapshot's pending rows, which the map builds from placeholders only
        self.assertIn("s.p === 'placeholder' && (!scope || s.g === scope)", (GRID / 'map.js').read_text(encoding='utf-8'))

    def test_the_unplaced_list_is_by_grid_in_the_grids_order(self):
        # PP-B5: the sites with no position are never drawn; the chip over the legend lists the
        # rows the map's snapshot carries, grouped by grid
        pending = [{'code': 'M1', 'grid': 'CMIN'}, {'code': 'L1', 'grid': 'CLUZ'}, {'code': 'L2', 'grid': 'CLUZ'}]
        out = run(ALERTS, GRID / 'dash-map.js', {'g': {'fn': 'unplacedGroups', 'args': [pending]},
                                                 'none': {'fn': 'unplacedGroups', 'args': [[]]}})
        self.assertEqual([('CLUZ', 'Luzon', ['L1', 'L2']), ('CMIN', 'Mindanao', ['M1'])],
                         [(g['grid'], g['name'], [r['code'] for r in g['rows']]) for g in out['g']])
        self.assertEqual([], out['none'])
        html = (GRID / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="ml-unplaced"', html)
        self.assertIn('id="unplaced-pop" role="dialog"', html)
        self.assertIn('id="ml-more" aria-expanded="false" aria-controls="ml-more-pop"', html)

    def test_the_scope_is_kept_in_the_address_for_the_way_back(self):
        # flow F1 (platform polish): a grid row or scope pill scopes the map and the address gains
        # ?grid=, so Back from a plant page restores the scope; All grids drops the parameter and
        # every other parameter (the shell's ?at) stays
        script = (GRID / 'dash-map.js').read_text(encoding='utf-8')
        self.assertIn("if (scope) u.searchParams.set('grid', scope); else u.searchParams.delete('grid');", script)
        self.assertIn('history.replaceState(history.state', script)
        self.assertNotIn('pushState', script)
        self.assertIn("const g = q.get('grid'), link = q.get('link');", script, 'and the address is read on load')

    def test_the_page_has_the_grid_chips_and_the_layer_list_and_writes_text_only(self):
        html = (GRID / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="map-regions"', html)
        for g in ('all', 'CLUZ', 'CVIS', 'CMIN'):
            self.assertIn(f'data-scope="{g}"', html)
        # UX-3: the scope and the layer pills share one toolbar at the top of the map (PP-B5:
        # one row, the lower-priority layers under "More")
        toolbar = html[html.index('<div class="map-toolbar"'):html.index('<!-- The replay, inside the map')]
        self.assertIn('id="map-regions"', toolbar)
        self.assertIn('id="ml-list"', toolbar)
        self.assertIn('/grid/__NOWCAST_STAMP__/dash-map.js', html)
        self.assertNotIn('innerHTML', (GRID / 'dash-map.js').read_text(encoding='utf-8'))
        css = (GRID / 'dashboard.css').read_text(encoding='utf-8')
        self.assertIn('.desk .gmap-chips { display: none !important; }', css)
        self.assertIn('.map-toolbar {\n  position: absolute; top: 14px;', css, 'the pills float on the map')
        # The pinned two-row bar is the shell's on every page now (no dashboard-only bar script):
        # page grid tabs hidden, and the live strip and As of on the second row (UX-4).
        shell_css = (GRID / 'shell.css').read_text(encoding='utf-8')
        self.assertIn('.gn-bar > .grids { display: none !important; }', shell_css)
        self.assertIn('.gn-row2', shell_css, 'the live strip and As of share the pinned bar row')
        self.assertFalse((GRID / 'dash-bar.js').exists())
        self.assertNotIn('dash-bar.js', html)
        # UX-3: the desk's replay is inside the map; the page tells the shell (UX-4) not to draw
        # one in its bar, and hides the shell's own replay here until that lands
        self.assertIn('<body data-replay="page">', html)
        bar = html[html.index('<header class="bar">'):html.index('</header>')]
        self.assertNotIn('class="clock', bar, 'no replay in the static bar on this page')
        replay = html[html.index('<div class="clock map-replay"'):html.index('<!-- The detail drawer')]
        for needle in ('data-step="-1"', 'id="play"', 'id="play-glyph"', 'data-step="1"', 'id="clock-time"',
                       'id="scrub"', 'id="scrub-ticks"', 'id="play-speed"'):
            self.assertIn(needle, replay, needle)
        self.assertIn('body[data-replay="page"] .gn-replay { display: none !important; }', css)
        shell = (GRID / 'shell.js').read_text(encoding='utf-8')
        # UX-4: the scrolling ticker gave way to the sectioned live strip; its newest items take
        # turns calmly (one every six seconds, held on hover or focus, none with reduced motion).
        self.assertNotIn('TICKER_PX_PER_S', shell)
        self.assertIn('const CYCLE_MS = 6000;', shell, 'the strip changes item at a calm pace')
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", shell)
        self.assertIn('.desk > .dash-side > .detail { pointer-events: auto; margin: 0; max-height: 100%; overflow: auto;', css,
                      'the drawer scrolls inside itself, never squashed to its heading')


class AlertsAndNotices(unittest.TestCase):
    def test_five_alerts_then_view_all_and_notices_have_their_own_grid_filter(self):
        html = (GRID / 'index.html').read_text(encoding='utf-8')
        alerts = (GRID / 'dash-alerts.js').read_text(encoding='utf-8')
        self.assertIn('const SHOWN = 5;', alerts)
        self.assertIn('for (const g of shown)', alerts)
        self.assertIn('id="da-more" href="/alerts"', html)
        feed = html[html.index('aria-label="Notice grid filter"'):html.index('<tbody id="feed">')]
        for g in ('all', 'CLUZ', 'CVIS', 'CMIN'):
            self.assertIn(f'data-filter="{g}"', feed)
        grid = (GRID / 'grid.js').read_text(encoding='utf-8')
        self.assertIn("a.grid === state.filter", grid, 'the notices filter by their own grid, not the page grid')
        self.assertNotIn("state.filter === 'grid'", grid)
        css = (GRID / 'dashboard.css').read_text(encoding='utf-8')
        # PP-B5: the notices are a dense table under the alerts; their long list scrolls inside
        # its card, so it never sets the band's height, with its header kept in view
        self.assertIn('.feed-wrap { max-height: 420px; overflow: auto;', css)
        self.assertIn('.desk-below .feed-table thead th { top: 0; }', css)
        # the kind is the shared badge, the same word and style as on every page
        self.assertIn("if (ui && typeof ui.badgeHtml === 'function') return ui.badgeHtml(kind);", grid)
        self.assertIn('data-entity="event:', grid)


if __name__ == '__main__':
    unittest.main()
