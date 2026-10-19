"""PP-B1 monitor pages: the notices page (`/notices`) and an alert's own page (`/alert/<key>`).

What is held here:
- the page sources: the shared frame (`gn-page`, the page head, breadcrumbs on the alert page),
  the shared component sheet linked just before shell.css, one `gn-filters` bar whose filters
  live in the address, method text only under the collapsed `gn-sources`, no inline script,
  style or handler, and text written only as text;
- the pure parts under node: which notices a filter keeps (grid, kind, period, search, never
  past the clock), the kind words (a derate is a notice whose text says so), the six-hour
  counts, which plant a notice names (the event record, else one plant's code in the text;
  two or more fit is unclear and links none), and the alert page's figures (unknowns named once,
  never a tile) and its in-force status;
- both pages in a real headless browser (`tests/fixtures/grid/monitor/browser.mjs`) against
  SYNTHETIC replay files and a SYNTHETIC alert API: the notices table grouped by day with its
  panel, the filters in the address and restored from it, Clear, the empty states and their
  actions, `#adv-<id>` scrolled to and marked, the phone layout; the alert page's anchor head,
  cause only when an event is recorded, related notices as entity links, the unknowns line,
  the after-clock and unknown-alert states; no page error and no sideways scroll.
  Skipped, with the reason, where node, playwright-core or Chromium is not found.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / 'src' / 'grid'
NOTICES_HTML = (GRID / 'notices.html').read_text(encoding='utf-8')
NOTICES_JS = (GRID / 'notices.js').read_text(encoding='utf-8')
SPIKE_HTML = (GRID / 'spike.html').read_text(encoding='utf-8')
SPIKE_JS = (GRID / 'spike.js').read_text(encoding='utf-8')
NODE = shutil.which('node')
FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'monitor'


def browser():
    """Chromium and playwright-core, if this machine has them (as tests/test_grid_shell.py)."""
    chromium = os.environ.get('GRID_BROWSER_CHROMIUM', '')
    playwright = os.environ.get('GRID_BROWSER_PLAYWRIGHT', '')
    if not chromium:
        found = sorted(str(p) for p in (Path.home() / '.cache' / 'ms-playwright').glob('chromium-*/chrome-linux*/chrome'))
        chromium = found[-1] if found else ''
    if not playwright:
        linked = ROOT / '.local' / 'deckcheck' / 'node_modules' / 'playwright-core' / 'index.mjs'
        playwright = str(linked) if linked.is_file() else ''
    return chromium, playwright


CHROMIUM, PLAYWRIGHT = browser()


class Sources(unittest.TestCase):
    def test_both_pages_link_the_shared_sheet_just_before_the_shell(self):
        for name, html in (('notices', NOTICES_HTML), ('spike', SPIKE_HTML)):
            sheets = re.findall(r'<link rel="stylesheet" href="/grid/__NOWCAST_STAMP__/([a-z-]+\.css)">', html)
            self.assertEqual(['ui.css', 'shell.css'], sheets[-2:], name)
            self.assertIn(name + '.css', sheets, name)

    def test_no_inline_script_style_or_handler_and_text_only(self):
        for name, html in (('notices', NOTICES_HTML), ('spike', SPIKE_HTML)):
            self.assertNotRegex(html, r'<script(?![^>]*\bsrc=)[^>]*>', name)
            self.assertNotIn('<style', html, name)
            self.assertNotRegex(html, r'\sstyle="', name)
            self.assertNotRegex(html, r'\son[a-z]+="', name)
        for name, js in (('notices', NOTICES_JS), ('spike', SPIKE_JS)):
            for banned in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval('):
                self.assertNotIn(banned, js, (name, banned))
        self.assertIn('opText', NOTICES_JS, 'notice text goes through the shell redaction')

    def test_the_notices_page_is_one_frame_with_one_filter_bar_in_the_address(self):
        main = NOTICES_HTML[NOTICES_HTML.index('<main'):NOTICES_HTML.index('</main>')]
        self.assertRegex(main, r'^<main class="gn-page nt-page"')
        self.assertIn('<header class="gn-page-head">', main)
        self.assertEqual(1, main.count('class="gn-filters"'))
        self.assertEqual(['grid', 'kind', 'period', 'q'], re.findall(r'data-filter="([a-z]+)"', main))
        self.assertIn('class="gn-filters-count"', main)
        self.assertIn('class="gn-clear"', main)
        # the dense table, then the panel: the 2/3 + 1/3 matrix
        self.assertLess(main.index('id="nt-table"'), main.index('id="nt-detail"'))
        self.assertIn('gn-grid--main-side', main)
        # method text sits only under the collapsed sources footer
        sources = main[main.index('<footer class="gn-sources">'):]
        self.assertIn('<details>', sources)
        self.assertNotIn('<details open', sources)
        self.assertIn('A notice that fits two or more plants links none.', sources)

    def test_the_alert_page_opens_on_its_anchor_head_with_breadcrumbs(self):
        main = SPIKE_HTML[SPIKE_HTML.index('<main'):SPIKE_HTML.index('</main>')]
        self.assertRegex(main, r'(?s)^<main class="gn-page sp-page"[^>]*>\s*<header class="gn-page-head">\s*'
                               r'<nav class="gn-crumbs" aria-label="Breadcrumb"><a href="/alerts">Alerts</a>')
        # the price chart leads the main column; the cause, the notices and the decision the side
        grid = main[main.index('gn-grid--main-side'):]
        self.assertLess(grid.index('id="sp-price"'), grid.index('class="sp-side"'))
        side = grid[grid.index('class="sp-side"'):]
        self.assertLess(side.index('id="sp-cause"'), side.index('id="sp-steps"'))
        self.assertLess(side.index('id="sp-steps"'), side.index('id="sp-journal"'))
        self.assertIn('<p class="gn-unknowns" id="sp-unknowns" hidden>', main)
        self.assertIn('<footer class="gn-sources">', main)
        # the decision box gets no second heading: the card names it
        self.assertIn("title: null", SPIKE_JS)

    def test_copy_has_no_em_dash_or_semicolon_in_shown_text(self):
        for name, html in (('notices', NOTICES_HTML), ('spike', SPIKE_HTML)):
            shown = re.sub(r'<!--.*?-->|<[^>]+>', ' ', html, flags=re.S)
            self.assertNotIn('—', shown, name)
            self.assertNotIn(';', shown.replace('&amp;', '&'), name)
        for name, js in (('notices', NOTICES_JS), ('spike', SPIKE_JS)):
            code = re.sub(r'/\*.*?\*/|^\s*//.*$', ' ', js, flags=re.S | re.M)
            strings = ' '.join(m.group(2) for m in re.finditer(r"(['`])((?:\\.|(?!\1).)*)\1", code))
            self.assertNotIn('—', strings, name)


LOGIC = r"""
const N = require(process.argv[1]);
const S = require(process.argv[2]);
const out = {};
const list = [
  {t: '2026-09-21T06:00:00', id: 'L1', grid: 'CLUZ', kind: 'notice', text: 'A unit on planned outage'},
  {t: '2026-09-21T09:00:00', id: 'V2', grid: 'CVIS', kind: 'notice', text: '05SYNBETA derated to 25 MW (Derating)'},
  {t: '2026-09-21T13:39:00', id: 'V3', grid: 'CVIS', kind: 'trip', text: '08SYNGAMA U2 Tripped'},
  {t: '2026-09-21T13:51:00', id: 'V4', grid: 'CVIS', kind: 'red', text: 'Red Alert declared'},
  {t: '2026-09-21T14:30:00', id: 'V5', grid: 'CVIS', kind: 'online', text: '08SYNGAMA U2 back online'},
  {t: '2026-09-20T22:00:00', id: 'M6', grid: 'CMIN', kind: 'mld', text: 'Manual load dropping'}];
const ids = (rows) => rows.map((a) => a.id);
out.all = ids(N.pick(list, {at: '2026-09-21T14:00'}));
out.day = ids(N.pick(list, {at: '2026-09-21T14:00', period: 'day'}));
out.oldDay = ids(N.pick(list, {at: '2026-09-21T14:00', days: 'day'}));
out.six = ids(N.pick(list, {at: '2026-09-21T14:00', period: '6h'}));
out.grid = ids(N.pick(list, {at: '2026-09-21T14:00', grid: 'CVIS'}));
out.trip = ids(N.pick(list, {at: '2026-09-21T14:00', kind: 'trip'}));
out.derate = ids(N.pick(list, {at: '2026-09-21T14:00', kind: 'derate'}));
out.notice = ids(N.pick(list, {at: '2026-09-21T14:00', kind: 'notice'}));
out.alert = ids(N.pick(list, {at: '2026-09-21T14:00', kind: 'alert'}));
out.q = [ids(N.pick(list, {at: '2026-09-21T14:00', q: 'gama'})), ids(N.pick(list, {at: '2026-09-21T14:00', q: 'v4'}))];
out.kinds = list.map(N.kindOf);
out.recent = N.recent(list, '2026-09-21T14:00');
out.recent.latest = out.recent.latest && out.recent.latest.id;
const sites = [{s: '05SYNBETA', g: 'CVIS', name: 'Beta'}, {s: '08SYNGAMA', g: 'CVIS', name: 'Gamma'},
  {s: '10SYNDUP', g: 'CMIN'}, {s: '11SYNDUP', g: 'CMIN'}, {s: '12SYNGAMA', g: 'CMIN'}];
const plant = N.plantMatcher(sites, [{advisory: 'V3', site: '08SYNGAMA', id: 'e1'}]);
const name = (r) => [r.how, r.site && r.site.s, r.candidates.length];
out.plants = [plant(list[2]), plant(list[1]), plant({id: 'M9', grid: 'CMIN', text: 'SYNDUP units on test'}),
  plant({id: 'X', grid: 'CVIS', text: 'Visayas grid notice'}), plant({id: 'V7', grid: 'CVIS', text: '08SYNGAMA U1 back'})].map(name);
out.fromSearch = [N.fromSearch('?grid=CVIS&kind=trip&period=6h&q=gama&at=x'), N.fromSearch('?grid=XX&kind=all&period=week')];
const answer = {at: '2026-09-21T14:00', alert: {region: 'CVIS', region_label: 'Visayas', direction: 'spike', first: '2026-09-21T13:00',
  last: '2026-09-21T14:00', interval_manila: '2026-09-21T13:40', intervals: 13, price_php_mwh: 31000, usual_php_mwh: null},
  around: {clock: '2026-09-21T14:03', t: ['2026-09-21T13:40'], reserve_short_mw: [120], curtailed_mw: [null], demand_mw: [2700]}};
const sum = S.summary(answer);
out.summary = {head: sum.head, tiles: sum.tiles.map((t) => [t.k, t.v]), unknowns: sum.unknownLine, key: sum.tiles.filter((t) => t.key).map((t) => t.k)};
out.status = [S.status(answer), S.status(Object.assign({}, answer, {around: Object.assign({}, answer.around, {clock: '2026-09-21T14:05'})}))];
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, 'node is not installed in this environment')
class Logic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([NODE, '-e', LOGIC, str(GRID / 'notices.js'), str(GRID / 'spike.js')],
                                capture_output=True, text=True, timeout=60, check=True)
        cls.out = json.loads(result.stdout)

    def test_the_filters_keep_the_clock_and_read_grid_kind_period_and_search(self):
        o = self.out
        self.assertEqual(['V4', 'V3', 'V2', 'L1', 'M6'], o['all'])  # newest first, V5 is after the clock
        self.assertEqual(['V4', 'V3', 'V2', 'L1'], o['day'])
        self.assertEqual(o['day'], o['oldDay'])
        self.assertEqual(['V4', 'V3', 'V2'], o['six'])  # 08:00 to 14:00
        self.assertEqual(['V4', 'V3', 'V2'], o['grid'])
        self.assertEqual(['V3'], o['trip'])
        self.assertEqual(['V2'], o['derate'])
        self.assertEqual(['L1'], o['notice'])  # a derate is not an "other" notice
        self.assertEqual(['V4', 'M6'], o['alert'])
        self.assertEqual([['V3'], ['V4']], o['q'])

    def test_the_kind_words_and_the_six_hour_counts(self):
        self.assertEqual(['notice', 'derate', 'trip', 'red', 'online', 'mld'], self.out['kinds'])
        self.assertEqual({'total': 3, 'latest': 'V4', 'kinds': [{'kind': 'red', 'n': 1}, {'kind': 'trip', 'n': 1}, {'kind': 'derate', 'n': 1}]},
                         self.out['recent'])

    def test_a_notice_names_a_plant_only_when_the_record_or_one_code_says_so(self):
        self.assertEqual([['the event record', '08SYNGAMA', 1], ['its code in the text', '05SYNBETA', 1],
                          ['unclear', None, 2], ['none', None, 0], ['its code in the text', '08SYNGAMA', 1]], self.out['plants'])

    def test_the_address_brings_the_filters_back(self):
        self.assertEqual([{'grid': 'CVIS', 'kind': 'trip', 'period': '6h', 'q': 'gama'},
                          {'grid': 'all', 'kind': 'all', 'period': 'all', 'q': ''}], self.out['fromSearch'])

    def test_the_alert_figures_name_unknowns_once_and_never_tile_them(self):
        s = self.out['summary']
        self.assertEqual('Visayas price spike', s['head'])
        self.assertEqual([['Peak price', '31,000'], ['Duration', '1 h 5 min'], ['Reserve short', '120'], ['Demand', '2,700']], s['tiles'])
        self.assertEqual(['Peak price'], s['key'])
        self.assertEqual('Not on record: usual price for this hour (the first replay day has no earlier day), multiple of usual, '
                         'curtailment at the peak.', s['unknowns'])

    def test_still_past_the_level_only_in_the_clocks_own_interval(self):
        live, ended = self.out['status']
        self.assertEqual({'live': True, 'text': 'Still past the level'}, live)
        self.assertEqual({'live': False, 'text': 'Ended 21 Sep 14:00'}, ended)


@unittest.skipUnless(NODE and CHROMIUM and PLAYWRIGHT, 'node, playwright-core or Chromium is not installed here '
                     '(set GRID_BROWSER_PLAYWRIGHT and GRID_BROWSER_CHROMIUM)')
class Browser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([NODE, str(FIXTURE / 'browser.mjs'), '--root', str(ROOT), '--playwright', PLAYWRIGHT,
                                 '--chromium', CHROMIUM], capture_output=True, text=True, timeout=300, cwd=ROOT)
        if result.returncode:
            raise AssertionError(result.stderr[-2000:])
        cls.report = json.loads(result.stdout)
        cls.n = cls.report['notices']
        cls.a = cls.report['alert']

    def test_no_page_error_and_nothing_past_this_machine(self):
        self.assertEqual([], self.report['errors'])

    def test_the_notices_table_is_grouped_by_day_newest_first_with_its_kinds(self):
        f = self.n['first']
        self.assertEqual(['M135800', 'V135120', 'V133937', 'V124803', 'V090215', 'L061241', 'L221000'], f['ids'])
        self.assertEqual(['Mon 21 Sep', 'Sun 20 Sep'], f['days'])
        self.assertEqual(['Notice', 'Red alert', 'Trip', 'Yellow alert', 'Derate', 'Notice', 'Notice'], f['kinds'])
        self.assertEqual('7 notices', f['count'])
        # related records: the event and the plant as entity links; a notice fitting two plants links none
        self.assertEqual(['event:syn-gama-u2-trip', 'plant:08SYNGAMA'], f['related']['V133937'])
        self.assertEqual(['plant:05SYNBETA'], f['related']['V090215'])
        self.assertEqual(['Unclear'], f['related']['M135800'])
        # hostile text stays text
        self.assertIsNone(f['pwned'])
        self.assertEqual(0, f['images'])
        self.assertTrue(f['textShown'])

    def test_the_anchor_counts_the_last_six_hours_by_kind(self):
        self.assertEqual({'n': '5', 'badges': ['1 Red alert', '1 Trip', '1 Yellow alert', '1 Derate', '1 Notice'],
                          'latest': 'Latest 13:58, Mindanao'}, self.n['first']['glance'])

    def test_the_panel_shows_the_latest_notice_then_the_one_picked(self):
        f = self.n['first']
        self.assertTrue(self.n['firstInView'])
        self.assertEqual(('Latest notice', ['M135800'], []), (f['detailHead'], f['selected'], f['picked']))
        self.assertEqual('Unclear: fits 10SYNDUP, 11SYNDUP. None is linked.', f['detailPlant'])
        p = self.n['picked']
        self.assertEqual(('Selected notice', ['V090215'], '#adv-V090215'), (p['detailHead'], p['picked'], p['hash']))
        self.assertEqual([['plant:05SYNBETA', '/plant/05SYNBETA']], p['detailLinks'])

    def test_the_filters_narrow_the_table_live_in_the_address_and_clear(self):
        v = self.n['visayas']
        self.assertEqual(['V135120', 'V133937', 'V124803', 'V090215'], v['ids'])
        self.assertEqual(('4 of 7 notices', True), (v['count'], v['clearShown']))
        self.assertTrue(v['search'].endswith('&grid=CVIS'))
        self.assertEqual(['V133937'], self.n['trips']['ids'])
        self.assertTrue(self.n['trips']['search'].endswith('&grid=CVIS&kind=trip'))
        self.assertEqual(['V090215'], self.n['derates']['ids'])
        self.assertEqual((7, False), (len(self.n['cleared']['ids']), self.n['cleared']['clearShown']))
        self.assertEqual(['M135800', 'V135120', 'V133937', 'V124803', 'V090215'], self.n['sixHours']['ids'])
        # a shared address opens the same view
        self.assertEqual(['L061241', 'L221000'], self.n['restored']['ids'])
        self.assertEqual(['CLUZ', 'notice', 'all'], self.n['restoredPressed'])

    def test_every_empty_state_says_why_and_offers_the_next_action(self):
        self.assertIn('No notice matches these filters', self.n['none']['empty'])
        self.assertIn('7 notices are hidden by the filters or the search.', self.n['none']['empty'])
        self.assertEqual(7, len(self.n['afterEmptyClear']['ids']))
        self.assertIn('No notice up to 20 Sep 06:00', self.n['early']['empty'])
        self.assertEqual(['Go to the latest'], self.n['earlyActions'])
        # an anchor the filters hide is said, with Clear
        self.assertEqual('Notice V133937 is hidden by the filters. Clear filters', self.n['hiddenNote'])

    def test_an_anchor_scrolls_to_its_notice_marks_it_and_opens_it(self):
        a = self.n['anchor']
        self.assertEqual(('#adv-V133937', ['V133937'], ['V133937']), (a['hash'], a['selected'], a['picked']))
        self.assertTrue(self.n['anchorInView'])
        self.assertEqual('08SYNGAMA U2 Tripped at 13:34 (Unplanned Outage)', a['detailText'])
        self.assertEqual([['event:syn-gama-u2-trip', '/event/syn-gama-u2-trip'], ['plant:08SYNGAMA', '/plant/08SYNGAMA']], a['detailLinks'])

    def test_open_on_the_desk_carries_the_notice_where_the_desk_reads_it(self):
        # Bug of 19 October (owner): "Open on the desk" landed on the plain dashboard. The desk
        # reads the grid and the selection from the hash (`g`, `t`, `adv`) and the clock from
        # `at`; the link used to put the grid in the query, which nothing read, and named no notice.
        grid_js = (GRID / 'grid.js').read_text(encoding='utf-8')
        self.assertIn("const desk = link(`/?at=${String(a.t).slice(0, 16)}#${a.grid ? 'g=' + encodeURIComponent(a.grid) + '&' : ''}"
                      "adv=${encodeURIComponent(a.id)}`,", NOTICES_JS)
        self.assertNotIn("'&grid=' + a.grid", NOTICES_JS)
        # The first render rewrites the hash (`#t=…&g=…`) before the explorable module starts, so
        # the id is kept on the state at initialState and read back from there (headless run of
        # 19 October: the hash alone lost it and the desk landed with nothing selected).
        self.assertIn("state.openAdv = h.get('adv') || null;", grid_js)
        self.assertIn("const adv = new URLSearchParams(location.hash.slice(1)).get('adv') || (G.state && G.state.openAdv) || null;", grid_js)
        self.assertIn("if (adv) selectMessage(adv);", grid_js)

    def test_a_phone_keeps_three_columns_and_opens_the_notice_under_its_row(self):
        self.assertEqual(['Time', 'Kind', 'Text'], self.n['phoneColumns'])
        self.assertEqual({'inline': True, 'after': 'adv-V133937', 'text': '08SYNGAMA U2 Tripped at 13:34 (Unplanned Outage)'},
                         {k: self.n['phone'][k] for k in ('inline', 'after', 'text')})
        self.assertLessEqual(self.n['phoneOverflow'], 0)
        self.assertLessEqual(self.n['overflow'], 0)

    def test_the_alert_page_anchor_head_and_its_recorded_cause(self):
        c = self.a['caused']
        self.assertEqual('Visayas price spike · Alerts · InGRID', c['title'])
        self.assertEqual('Visayas price spike', c['h1'])
        self.assertEqual(['Alerts', 'Visayas price spike'], c['crumbs'])
        self.assertEqual(['High', 'Visayas', '21 Sep 13:00–14:00', 'Still past the level'], c['meta'])
        self.assertEqual([['Open the event', '/event/syn-gama-u2-trip'], ['Add a note', '#sp-journal']], c['actions'])
        self.assertEqual('31,000₱/MWh', c['keyStat'])
        self.assertEqual([['event:syn-gama-u2-trip', '/event/syn-gama-u2-trip'], ['notice:V133937', '/notices?at=2026-09-21T13:39#adv-V133937']],
                         c['causeLinks'])
        self.assertEqual(['V133937'], c['opened'])
        for nid, entity, href in c['steps']:
            self.assertEqual(('notice:' + nid, f'#adv-{nid}'), (entity, href[href.index('#'):]))

    def test_the_alert_page_names_unknowns_on_one_line_and_never_tiles_them(self):
        c = self.a['caused']
        self.assertEqual(0, c['naTiles'])
        self.assertEqual(['Peak price', 'Duration', 'Reserve short', 'Demand'], c['stats'])
        self.assertTrue(c['unknowns'].startswith('Not on record: usual price for this hour'))
        lone = self.a['lone']
        # a series the record lacks gets no chart: it joins the line once
        self.assertEqual([False, True], lone['minis'])
        self.assertEqual(1, lone['unknowns'].count('reserve short'))
        self.assertTrue(c['pricePath'])
        self.assertEqual([True, True], c['minis'])
        self.assertTrue(c['sources'])
        self.assertEqual(2, c['ranked'])
        self.assertEqual('Cost to us Not available · Needs your portfolio', c['cost'])
        self.assertGreaterEqual(c['pageBottomRoom'], 112, 'the page leaves the command bar its room')

    def test_no_cause_is_claimed_without_a_recorded_event(self):
        lone = self.a['lone']
        self.assertEqual(['Add a note'], lone['actions'])
        self.assertEqual(0, lone['eventLinks'])
        self.assertIn('No recorded event explains this alert.', lone['cause'])
        self.assertIn('None is claimed as the cause.', lone['cause'])

    def test_an_alert_after_the_clock_or_gone_says_why_with_the_next_action(self):
        self.assertFalse(self.a['later']['body'])
        self.assertEqual('This Visayas alert starts after the replay time', self.a['later']['title'])
        self.assertEqual([['Go to its start', '/alert/' + 'c' * 24 + '?at=2026-09-21T18:00']], self.a['later']['action'])
        self.assertEqual('This alert is not in the current alert rules', self.a['gone']['title'])
        self.assertEqual([['Open alerts', '/alerts']], self.a['gone']['action'])
        self.assertLessEqual(self.a['causedOverflow'], 0)
        self.assertLessEqual(self.a['phoneOverflow'], 0)


if __name__ == '__main__':
    unittest.main()
