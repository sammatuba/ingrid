"""BOOK-3: the book page ``/book`` and the two baked files it reads.

What is proven here.

* ``scripts/book/bake_book.py`` builds ``book/index.json`` and ``book/exposure.json`` from the
  synthetic book (BOOK-1) and the synthetic vintages (BOOK-2, plus the Luzon and Mindanao vintages
  BOOK-3 adds) through the real modules, deterministically, into a given ``--out`` directory. The
  committed outputs under ``tests/fixtures/grid/book/bake`` are reconstruction-verified: the builder
  gives the same bytes, and every record in them recomputes from ``src.book`` (the exposure record,
  each impact record and its record id, the materiality block first, the vintage per region read
  through ``load_vintage``).
* The page is a design file: no inline code or style, the shared section block with no entry current
  and no Book entry, the ``#ask`` mount, the build stamp pattern, and two baked files read.
* The page has no route in the application: the harness ``tests/fixtures/grid/book/browser.mjs``
  serves it alone. With node, the serve-only scenario answers ``/book``, its design files and both
  data files. With a browser, the page is opened under the header policy at 390 and 1280, and every
  figure it draws is checked against the baked record that holds it. The synthetic label is in the
  title and in the header line on every screen, and beside every table. Every sentence follows copy
  rules 1 to 7 as the other page tests check them.
* Platform polish (2026-10-18): the tables no longer repeat the book record in an "As of" column
  on every row; each table's synthetic caption states the record and its cutoff once, and the
  impact table's vintage record sits in the region sentences and the vintage cell's title. The
  page opens on the exposure, with tabs for the exposure, the impact band and the book's records;
  a tab panel counts as shown text, a closed fold does not.

The browser classes skip with the reason the other page tests give where no browser is available.
Offline and stdlib-only: no model, network, credential or clock. No value from the owner's
``.local/price`` or ``.local/outlook-archive`` is read.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.book import impact as im  # noqa: E402
from src.book.exposure import Window, exposure, load_book  # noqa: E402
from src.book.records import LABEL, compute_content_digest, validate_book  # noqa: E402
from src.price.impact import DEFAULT_MATERIALITY  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BAKE = _load('book_page_bake', ROOT / 'scripts' / 'book' / 'bake_book.py')
VINTAGE_TOOL = _load('book_page_vintages', ROOT / 'scripts' / 'book' / 'vintages.py')
REPO = _load('book_page_repo_tool', ROOT / 'scripts' / 'repo.py')

FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'book'
OUT = FIXTURE / 'bake'
HARNESS = FIXTURE / 'browser.mjs'
BOOK_FIXTURE = ROOT / 'tests' / 'fixtures' / 'book' / 'book-v1.json'
VINTAGES = ROOT / 'tests' / 'fixtures' / 'book' / 'vintages'
GRID = ROOT / 'src' / 'grid'
NODE = shutil.which('node')
STAMP = '0123456789abcdef'
DAY = date(2026, 10, 19)
CUTOFF = '2026-10-18'
NAV = [('/', 'Grid'), ('/data', 'Data'), ('/plants', 'Plants'), ('/explain', 'Explain'),
       ('/outlooks', 'Outlooks'), ('/paper', 'Paper'), ('/models', 'Models'), ('/work', 'Work'),
       ('/map', 'Map'), ('/alerts', 'Alerts')]
#: DOCK-5: the Book entry, the pages that carry it, and the pages whose owners add it later.
BOOK_ENTRY = ('/book', 'Book')
#: SHELL-1: the shared bar's links, in order. Platform polish (PP-A): the one list lives in the
#: shell's own test (four links, then the Decisions, Evidence and About menus).
from tests.test_grid_shell import SHELL_NAV  # noqa: E402
#: Platform polish (flow F6: outlooks, then the register, then the book's exposure): the outlooks
#: and register pages link the book from their page actions.
BOOK_NAV_PAGES = {'index.html', 'catalog.html', 'assets.html', 'asset.html', 'alerts.html', 'book.html',
                  'outlooks.html', 'register.html'}
BOOK_NAV_WAITS = ('event.html', 'explain.html', 'paper.html', 'ask.html', 'models.html', 'work.html',
                  'map.html')
#: The BOOK-2 vintages keep their bytes when BOOK-3 adds the other regions (book-2.md pins these).
BOOK2_DIGESTS = {
    'book-demo-2026-10-19-cvis': '0ec50079326aa56f5a33f36d0da2326eab04d46b53aa66a677c05db5279c714c',
    'book-demo-2026-10-19-cvis-v2': 'bbaea560ed4340c137aa348a9dfaf7f00e6a2f522ff95cb84cfa72c28664b76f',
}
PLAIN = json.loads((ROOT / 'docs' / 'routes.json').read_text(encoding='utf-8'))['plain_language']
BANNED = [re.compile(pattern, re.I) for pattern in PLAIN['banned_words']]
MONTHS = ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def scratch_directory(prefix='book3-'):
    """The system temp dir, else an ignored repo path (a review sandbox may have no writable /tmp)."""
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / '.local' / 'test-scratch'
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def browser():
    """The Chromium and playwright-core a real check needs, as tests/test_grid_outlooks_page.py finds them."""
    chromium = os.environ.get('GRID_BROWSER_CHROMIUM', '')
    playwright = os.environ.get('GRID_BROWSER_PLAYWRIGHT', '')
    if not chromium:
        versions = []
        for path in (Path.home() / '.cache' / 'ms-playwright').glob('chromium-*/chrome-linux*/chrome'):
            versions.append((path.parent.parent.name, str(path)))
        if versions:
            chromium = max(versions)[1]
    if not playwright:
        linked = ROOT / '.local' / 'deckcheck' / 'node_modules' / 'playwright-core' / 'index.mjs'
        if linked.is_file():
            playwright = str(linked)
    return (chromium, playwright)


BROWSER = browser()


def baked(name):
    return json.loads((OUT / 'book' / name).read_text(encoding='utf-8'))


# --- the page's printing, mirrored: every figure at the precision its record holds -------------

def fig(value, digits):
    return format(value, ',.%df' % digits)


def day_text(text):
    return '%d %s %s' % (int(text[8:10]), MONTHS[int(text[5:7])], text[:4])


def utc_text(text):
    return '%s %s UTC' % (day_text(text), text[11:16])


def short(record_id):
    return record_id[:12] + '…'


def copy_problems(sentence):
    """The copy rules the other page tests apply to one sentence: under 20 words, active voice, no
    semicolon, no 'stale' and no word from the site's banned list (docs/routes.json)."""
    problems = []
    if ';' in sentence:
        problems.append('semicolon')
    if re.search(r'\bstale\b', sentence, re.I):
        problems.append('stale')
    for pattern in BANNED:
        if pattern.search(sentence):
            problems.append('banned ' + pattern.pattern)
    if len(sentence.split()) >= 20:
        problems.append('%d words' % len(sentence.split()))
    hit = next((m for m in REPO.PASSIVE.finditer(sentence)
                if m.group(1).lower() not in REPO.NOT_PARTICIPLES), None)
    if hit:
        problems.append('passive ' + hit.group(0))
    return problems


def figure_dicts(node, ancestor=False, quoted=False, key=None):
    """Every dict holding a numeric figure, with whether it carries the synthetic label.

    A figure dict is labelled when it says ``synthetic: true`` and carries the label, or sits inside a
    record that carries it (the book record labels its rows that way, BOOK-1). A covering contract and
    a band row are inputs quoted inside a labelled row (the BOOK-2 rule).
    """
    if isinstance(node, dict):
        own = node.get('synthetic') is True and str(node.get('label', '')).startswith(LABEL)
        if any(k.endswith(('_mwh', '_mw', '_php', '_php_mwh')) and type(v) in (int, float)
               for k, v in node.items()):
            yield key, node, own or quoted or (ancestor and node.get('synthetic') is True)
        for name, value in node.items():
            if name == 'materiality':
                continue  # the stated line is a policy, not a figure of the book
            yield from figure_dicts(value, ancestor or own,
                                    own and name in ('covering_contracts', 'band_php_mwh'), name)
    elif isinstance(node, list):
        for item in node:
            yield from figure_dicts(item, ancestor, quoted, key)


# ------------------------------------------------------------------------------- the builder

class TheBuilder(unittest.TestCase):
    """The committed outputs are the builder's bytes, and the builder writes only the two files."""

    def test_the_committed_outputs_reproduce_from_the_builder(self):
        built = BAKE.files()
        self.assertEqual(['book/exposure.json', 'book/index.json'], sorted(built))
        for name, data in built.items():
            self.assertEqual(data, (OUT / name).read_bytes(), name)
        self.assertEqual([], BAKE.check())
        self.assertEqual(['exposure.json', 'index.json'], sorted(p.name for p in (OUT / 'book').iterdir()))

    def test_out_writes_the_two_files_into_the_given_directory(self):
        with scratch_directory() as scratch:
            run = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'book' / 'bake_book.py'),
                                  '--out', scratch], capture_output=True, text=True, cwd=ROOT, timeout=300)
            self.assertEqual(0, run.returncode, run.stderr)
            written = sorted(str(p.relative_to(scratch)) for p in Path(scratch).rglob('*') if p.is_file())
            self.assertEqual(['book/exposure.json', 'book/index.json'], written)
            for name in written:
                self.assertEqual((OUT / name).read_bytes(), (Path(scratch) / name).read_bytes(), name)

    def test_check_mode_passes_and_writes_nothing(self):
        before = {p: p.read_bytes() for p in OUT.rglob('*') if p.is_file()}
        run = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'book' / 'bake_book.py'), '--check'],
                             capture_output=True, text=True, cwd=ROOT, timeout=300)
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn('OK: 2 book page files reproduce', run.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in OUT.rglob('*') if p.is_file()})

    def test_the_build_is_deterministic(self):
        self.assertEqual(BAKE.files(), BAKE.files())

    def test_the_inputs_are_the_synthetic_test_data_only(self):
        self.assertEqual(BOOK_FIXTURE, BAKE.BOOK_FIXTURE)
        self.assertEqual(VINTAGES, BAKE.VINTAGES)
        source = (ROOT / 'scripts' / 'book' / 'bake_book.py').read_text(encoding='utf-8')
        for word in ('.local', 'outlook-archive', 'urllib', 'socket', 'http'):
            self.assertNotIn(word, source.split('"""', 2)[2], word)
        for name in ('index.json', 'exposure.json'):
            self.assertNotIn('.local', (OUT / 'book' / name).read_text(encoding='utf-8'))

    def test_the_rules_the_files_state_follow_the_copy_rules(self):
        for text in (BAKE.SELECTION_RULE, BAKE.HEAT_RULE, BAKE.HOURS_RULE):
            for sentence in REPO.sentences(text):
                self.assertEqual([], copy_problems(sentence), sentence)


class TheVintages(unittest.TestCase):
    """BOOK-3 adds one Luzon and one Mindanao vintage through the real archive; BOOK-2's stay as they were."""

    def test_the_book2_vintages_keep_their_record_ids(self):
        for outlook_id, digest in BOOK2_DIGESTS.items():
            record = json.loads((VINTAGES / 'outlooks' / (outlook_id + '.json')).read_text(encoding='utf-8'))
            self.assertEqual(digest, record['content_digest'], outlook_id)

    def test_every_region_has_a_synthetic_vintage_tied_through_the_archive(self):
        self.assertEqual([], VINTAGE_TOOL.check())
        bands = BAKE.archive_bands(VINTAGES)
        self.assertEqual({'CLUZ', 'CVIS', 'CMIN'}, {band.series for band in bands})
        for band in bands:
            self.assertTrue(band.synthetic, band.outlook_id)
            self.assertFalse(band.zero_width, band.outlook_id)
            self.assertTrue(band.outlook_id.startswith('book-demo-2026-10-19-'), band.outlook_id)
            values = json.loads((VINTAGES / 'values' / (band.outlook_id + '.json')).read_text(encoding='utf-8'))
            self.assertIs(True, values['synthetic'])
            self.assertEqual(band.series, values['series'])


def band(outlook_id, series, issued_at):
    """A hand-built stand-in with the fields ``choose`` and ``as_of_block`` read; no levels."""
    return SimpleNamespace(outlook_id=outlook_id, series=series, issued_at=issued_at,
                           information_cutoff='2026-10-14T16:00:00Z')


class TheSelectionRule(unittest.TestCase):
    """Review round 1, finding 3: both halves of the rule the page states, on a hand-built band list.
    The cutoff ``2026-10-18`` is a date, so it closes at 2026-10-18T16:00:00Z."""

    def test_the_newest_regional_vintage_known_at_the_cutoff_is_picked(self):
        bands = [band('vis-early', 'CVIS', '2026-10-18T02:00:00Z'), band('vis-late', 'CVIS', '2026-10-18T06:00:00Z'),
                 band('vis-after', 'CVIS', '2026-10-18T16:00:00Z'), band('sys', 'SYSTEM', '2026-10-18T07:00:00Z'),
                 band('luz', 'CLUZ', '2026-10-18T08:00:00Z')]
        chosen, considered = BAKE.choose(bands, 'CVIS', CUTOFF)
        self.assertEqual('vis-late', chosen.outlook_id)
        # The vintage issued at the cutoff's close is not known at a date cutoff, so it is not considered.
        self.assertEqual(['vis-early', 'vis-late'], considered)

    def test_a_region_without_a_regional_vintage_takes_the_newest_system_one(self):
        bands = [band('vis', 'CVIS', '2026-10-18T02:00:00Z'), band('sys-early', 'SYSTEM', '2026-10-17T00:00:00Z'),
                 band('sys-late', 'SYSTEM', '2026-10-18T01:00:00Z'), band('sys-after', 'SYSTEM', '2026-10-19T00:00:00Z')]
        chosen, considered = BAKE.choose(bands, 'CMIN', CUTOFF)
        self.assertEqual('sys-late', chosen.outlook_id)
        self.assertEqual(['sys-early', 'sys-late'], considered)

    def test_two_vintages_issued_at_the_same_instant_are_refused(self):
        bands = [band('a', 'CLUZ', '2026-10-18T02:00:00Z'), band('b', 'CLUZ', '2026-10-18T02:00:00Z')]
        with self.assertRaises(BAKE.BakeError) as caught:
            BAKE.choose(bands, 'CLUZ', CUTOFF)
        self.assertEqual('VINTAGE_TIE', caught.exception.code)

    def test_a_region_with_no_vintage_known_at_the_cutoff_gets_none(self):
        bands = [band('vis', 'CVIS', '2026-10-18T02:00:00Z'), band('luz-after', 'CLUZ', '2026-10-19T00:00:00Z'),
                 band('sys-after', 'SYSTEM', '2026-10-20T00:00:00Z')]
        self.assertEqual((None, []), BAKE.choose(bands, 'CLUZ', CUTOFF))
        self.assertEqual((None, []), BAKE.choose(bands, 'CMIN', CUTOFF))


# ------------------------------------------------------------------------ the baked records

class TheBakedRecords(unittest.TestCase):
    """Every record in the two files recomputes from src.book; nothing in them is typed by hand."""

    @classmethod
    def setUpClass(cls):
        cls.index = baked('index.json')
        cls.page = baked('exposure.json')
        cls.book = load_book(BOOK_FIXTURE)

    def test_the_index_holds_the_book_record_unchanged(self):
        self.assertEqual(self.book, self.index['book'])
        validate_book(self.index['book'])
        self.assertEqual(self.index['book']['content_digest'], compute_content_digest(self.index['book']))
        self.assertIs(True, self.index['synthetic'])
        self.assertEqual(LABEL, self.index['label'])

    def test_each_contract_hour_run_gives_back_the_contracts_hours(self):
        runs = self.index['contract_hours']['runs']
        self.assertEqual({c['id'] for c in self.book['contracts']}, set(runs))
        for contract in self.book['contracts']:
            hours = [h for first, last in runs[contract['id']] for h in range(first, last + 1)]
            self.assertEqual(contract['hours'], hours, contract['id'])
        self.assertEqual([[0, 7], [22, 23]], runs['CT-LUZ02-2'])
        self.assertEqual([[8, 21]], runs['CT-VIS03-2'])

    def test_the_materiality_block_comes_first_and_every_impact_states_the_same_line(self):
        self.assertEqual('materiality', next(iter(self.page)))
        self.assertEqual(im.materiality_block(DEFAULT_MATERIALITY), self.page['materiality'])
        for record in self.page['impacts']:
            self.assertEqual('materiality', next(iter(record)))
            self.assertEqual(self.page['materiality'], record['materiality'])

    def test_the_exposure_record_is_src_book_s_for_the_day_and_the_cutoff(self):
        expected = exposure(self.book, Window(DAY, 0, 24), CUTOFF)
        self.assertEqual(expected, self.page['exposure'])
        self.assertEqual(expected['window'], self.page['window'])
        self.assertEqual(CUTOFF, self.page['cutoff'])
        self.assertEqual(14 * 24, len(self.page['exposure']['rows']))

    def test_the_vintage_per_region_is_the_newest_known_at_the_cutoff(self):
        regions = {entry['region']: entry for entry in self.page['selection']['regions']}
        self.assertEqual(['Luzon', 'Visayas', 'Mindanao'], list(regions))
        self.assertEqual('book-demo-2026-10-19-cluz', regions['Luzon']['outlook_id'])
        self.assertEqual('book-demo-2026-10-19-cmin', regions['Mindanao']['outlook_id'])
        # Visayas has two vintages known at the cutoff; the later issue (06:00Z) is the one used.
        self.assertEqual(['book-demo-2026-10-19-cvis', 'book-demo-2026-10-19-cvis-v2'],
                         regions['Visayas']['considered'])
        self.assertEqual('book-demo-2026-10-19-cvis-v2', regions['Visayas']['outlook_id'])
        self.assertEqual(BOOK2_DIGESTS['book-demo-2026-10-19-cvis-v2'], regions['Visayas']['outlook_digest'])
        self.assertEqual(BAKE.SELECTION_RULE, self.page['selection']['rule'])

    def test_each_impact_record_recomputes_through_load_vintage(self):
        """Review note C of BOOK-2: the band is reached only through load_vintage, by record id."""
        entries = [entry for entry in self.page['selection']['regions'] if entry['outlook_id']]
        self.assertEqual(3, len(entries))
        self.assertEqual(len(entries), len(self.page['impacts']))
        for entry, record in zip(entries, self.page['impacts']):
            band = im.load_vintage(VINTAGES, entry['outlook_id'], entry['outlook_digest'])
            expected = im.build_impact(self.book, band, Window(DAY, 0, 24), CUTOFF, DEFAULT_MATERIALITY,
                                       region=entry['region'])
            self.assertEqual(expected, record, entry['region'])
            self.assertEqual(im.record_digest(record), record['content_digest'])
            self.assertEqual(entry['impact_record_id'], record['content_digest'])
            self.assertEqual(entry['outlook_digest'], record['vintage']['outlook_digest'])
            self.assertEqual({entry['region']}, {a['region'] for a in record['accounts']})

    def test_every_account_of_the_book_has_one_impact_row(self):
        accounts = [a['account_id'] for record in self.page['impacts'] for a in record['accounts']]
        self.assertEqual([a['id'] for a in self.book['accounts']], accounts)

    def test_the_heat_shades_follow_the_stated_rule(self):
        heat = self.page['heat']
        rows = self.page['exposure']['rows']
        largest = max(r['uncovered_mwh'] for r in rows)
        self.assertEqual(largest, heat['largest_mwh'])
        self.assertEqual([round(largest * k / 4, 3) for k in (1, 2, 3)] + [largest], heat['edges_mwh'])
        self.assertEqual(BAKE.HEAT_RULE, heat['rule'])
        nodes = [n['id'] for n in self.book['nodes']]
        self.assertEqual(nodes, [h['node_id'] for h in heat['rows']])
        for row in heat['rows']:
            cells = [r for r in rows if r['node_id'] == row['node_id']]
            self.assertEqual([r['hour_start'] for r in cells], row['hours'])
            for cell, shade in zip(cells, row['shades']):
                value = cell['uncovered_mwh']
                if value <= 0:
                    self.assertEqual(0, shade)
                else:
                    self.assertLessEqual(value, heat['edges_mwh'][shade - 1])
                    if shade > 1:
                        self.assertGreater(value, heat['edges_mwh'][shade - 2])

    def test_every_figure_carries_the_synthetic_label(self):
        found = list(figure_dicts(self.page)) + list(figure_dicts(self.index))
        self.assertGreater(len(found), 1000)
        for key, node, labelled in found:
            self.assertTrue(labelled, (key, sorted(node)))
        for node in self.page['impacts']:
            self.assertTrue(node['label'].startswith(LABEL))
            self.assertIn('record id ' + node['vintage']['outlook_digest'][:12], node['label'])


# --------------------------------------------------------------------------- the page source

class ThePageSource(unittest.TestCase):
    """The design files: no inline code, the shared block, the mount, the stamp and two files read."""

    @classmethod
    def setUpClass(cls):
        cls.html = (GRID / 'book.html').read_text(encoding='utf-8')
        cls.js = (GRID / 'book.js').read_text(encoding='utf-8')
        cls.css = (GRID / 'book.css').read_text(encoding='utf-8')

    def test_the_page_carries_no_inline_code_and_no_external_reference(self):
        self.assertNotIn('<script>', self.html)
        self.assertNotIn('<style>', self.html)
        self.assertNotRegex(self.html, r' style="')
        self.assertNotRegex(self.html, r' on\w+="')
        for text in (self.html, self.js, self.css):
            self.assertNotRegex(text, r'(?:src|href)="(?:https?:)?//')
            self.assertNotIn('@import', text)
            self.assertNotRegex(text, r'url\(\s*["\']?https?:')
        for href in re.findall(r'href="([^"]+)"', self.html):
            self.assertTrue(href.startswith('/') and not href.startswith('//'), href)

    def test_the_build_stamp_pattern(self):
        self.assertIn('name="nowcast-build" content="__NOWCAST_STAMP__"', self.html)
        for asset in ('grid.css', 'book.css', 'ask.css'):
            self.assertIn('href="/grid/__NOWCAST_STAMP__/%s"' % asset, self.html)
        for asset in ('book.js', 'ask.js'):
            self.assertIn('src="/grid/__NOWCAST_STAMP__/%s" defer' % asset, self.html)
        self.assertIn("const DATA = '/grid-data/' + STAMP;", self.js)

    def test_the_ask_mount(self):
        self.assertIn('<section id="ask" data-context="book" aria-label="Ask Ingrid"></section>', self.html)

    def test_the_shared_section_block_with_no_entry_current_and_no_book_entry(self):
        """DOCK-5 moved this pin: the block is the ten entries and the Book entry after them, and
        the Book entry is the one marked current (it was BOOK-3's: no Book entry, none current)."""
        nav = re.search(r'<nav class="sites"[^>]*>(.*?)</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        links = re.findall(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', nav.group(1))
        self.assertEqual(NAV + [BOOK_ENTRY], [(href, label) for href, attrs, label in links])
        self.assertEqual(['/book'], [href for href, attrs, label in links if 'aria-current' in attrs])
        self.assertIn('<header class="bar">', self.html)

    def test_no_other_page_gains_a_book_entry(self):
        """DOCK-5 owns the navigation entry: exactly the pages no pending task owns link /book, and
        no page a pending task owns does (the event page is RAG-5's, the explainer and the paper are
        the docs lane's, the ask panel is DOCK-6's; COPY-1's outlooks and register pages stay as
        DOCK-5's acceptance requires; the models, work and map pages wait on their own page
        tests)."""
        linked = {page.name for page in GRID.glob('*.html')
                  if re.search(r'href="/book["/#?]', page.read_text(encoding='utf-8'))}
        self.assertEqual(BOOK_NAV_PAGES, linked)
        for name in BOOK_NAV_WAITS:
            self.assertNotIn(name, linked, name)

    def test_the_application_has_no_book_route_yet(self):
        """Replaced by DOCK-5 (BOOK-3's hand-back): the application serves `/book` the way it
        serves `/outlooks`, the stager carries the page's three design files, and the route is a
        site route the dock's `open` action may name."""
        api = (ROOT / 'src' / 'api' / '__init__.py').read_text(encoding='utf-8')
        self.assertIn("@app.get('/book')", api)
        self.assertIn("page_response(GRID_DIR / 'book.html', stamp), REVALIDATE_CACHE", api)
        self.assertIn("'book.html', 'book.css', 'book.js'", api)
        self.assertIn('|book/)?', api, 'the two baked files are served under book/')
        stage = (ROOT / 'scripts' / 'deploy' / 'stage_hosting.py').read_text(encoding='utf-8')
        self.assertIn('"book.html", "book.css", "book.js"', stage)
        from src.judgment.actions import SITE_ROUTES
        self.assertIn('/book', SITE_ROUTES)

    def test_the_page_reads_the_two_baked_files_only(self):
        self.assertEqual(['book/exposure.json', 'book/index.json'],
                         sorted(re.findall(r"read\('([^']+)'\)", self.js)))
        self.assertEqual(1, self.js.count('fetch('))
        for other in ("'regions.json'", "'outlook/", "'events/", '.local/', '.csv', "'values"):
            self.assertNotIn(other, self.js, other)

    def test_the_page_does_no_arithmetic_on_a_figure(self):
        """Sums, shades and hour runs come from the files. The code has no sum, product or quotient."""
        code = re.sub(r'/\*.*?\*/', '', self.js, flags=re.S)
        for needle in ('reduce(', 'Math.', 'parseFloat', ' * ', ' / ', ' - ', '+=', '-='):
            self.assertNotIn(needle, code, needle)

    def test_the_static_label_is_the_book_record_s_own(self):
        self.assertIn('<title>InGRID · Synthetic book</title>', self.html)
        flag = re.search(r'<p class="bk-flag" id="bk-flag" role="note">([^<]+)</p>', self.html)
        self.assertEqual(LABEL, flag.group(1))
        self.assertIn('$(\'bk-flag\').textContent = book.label;', self.js)

    def test_the_static_sentences_follow_the_copy_rules(self):
        caption = re.search(r'<footer class="caption" id="caption">([^<]+)</footer>', self.html).group(1)
        for text in (LABEL, caption):
            for sentence in REPO.sentences(text):
                self.assertEqual([], copy_problems(sentence), sentence)

    def test_the_fixed_fallback_sentences_follow_the_copy_rules(self):
        """Review round 1, finding 2: the sentences the browser run never shows (the empty line and
        the no-vintage line) and the line-scope sentence pass the same copy check."""
        empty = re.search(r"const EMPTY_LINE = '([^']+)';", self.js).group(1)
        scope = re.search(r"const LINE_SCOPE = '([^']+)';", self.js).group(1)
        template = re.search(r"const noVintage = \(region, when\) => `([^`]+)`;", self.js).group(1)
        no_vintage = template.replace('${region}', 'Luzon').replace('${when}', '18 Oct 2026')
        self.assertEqual('No vintage prices Luzon at the cutoff of 18 Oct 2026, so the page shows no band for it.',
                         no_vintage)
        self.assertIn('empty.textContent = EMPTY_LINE;', self.js)
        for text in (empty, scope, no_vintage):
            for sentence in REPO.sentences(text):
                self.assertEqual([], copy_problems(sentence), sentence)

    def test_no_status_word_stronger_than_the_records(self):
        """The impact records state a line and classify nothing, so the page names no verdict."""
        code = re.sub(r'/\*.*?\*/', '', self.js, flags=re.S).lower()
        for word in ('current', 'accepted', 'verified', 'is material', 'not material', 'badge'):
            self.assertNotIn(word, code, word)


# -------------------------------------------------------------------- the fixture server alone

@unittest.skipUnless(NODE, 'no node found: the book harness needs node to serve the page')
class TheFixtureServer(unittest.TestCase):
    """The harness's serve-only mode: the page and its files answer under a stamp, with no browser."""

    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(
            [NODE, str(HARNESS), '--root', str(ROOT), '--data', str(OUT), '--stamp', STAMP, '--serve'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, text=True)
        line = cls.process.stdout.readline()
        try:
            cls.base = 'http://127.0.0.1:%d' % json.loads(line)['port']
        except (ValueError, KeyError):
            cls.process.kill()
            raise AssertionError('the harness printed no port: %r %s' % (line, cls.process.stderr.read()[-400:]))

    @classmethod
    def tearDownClass(cls):
        cls.process.stdin.close()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait()
        cls.process.stdout.close()
        cls.process.stderr.close()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def test_the_page_answers_with_the_stamp_written_in(self):
        status, headers, body = self.get('/book')
        self.assertEqual(200, status)
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        page = body.decode('utf-8')
        self.assertNotIn('__NOWCAST_STAMP__', page)
        self.assertIn('content="%s"' % STAMP, page)
        self.assertIn('<title>InGRID · Synthetic book</title>', page)
        self.assertIn('src="/grid/%s/book.js"' % STAMP, page)

    def test_the_design_files_and_both_data_files_answer(self):
        for name in ('book.css', 'book.js', 'ask.css', 'ask.js', 'grid.css'):
            status, _, body = self.get('/grid/%s/%s' % (STAMP, name))
            self.assertEqual(200, status, name)
            self.assertEqual((GRID / name).read_bytes(), body, name)
        for name in ('index.json', 'exposure.json'):
            status, headers, body = self.get('/grid-data/%s/book/%s' % (STAMP, name))
            self.assertEqual(200, status, name)
            self.assertEqual('application/json', headers['content-type'])
            self.assertEqual((OUT / 'book' / name).read_bytes(), body, name)

    def test_nothing_else_is_served(self):
        for path in ('/grid-data/%s/book/other.json' % STAMP, '/grid/%s/outlooks.js' % STAMP,
                     '/grid-data/0000000000000000/book/index.json', '/outlooks'):
            self.assertEqual(404, self.get(path)[0], path)


# ------------------------------------------------------------------ the page, in a real browser

@unittest.skipUnless(all(BROWSER) and NODE, 'no browser found: name one with '
                                            'GRID_BROWSER_CHROMIUM and GRID_BROWSER_PLAYWRIGHT, '
                                            'or link .local/deckcheck')
class ThePageInTheBrowser(unittest.TestCase):
    """/book under the application's own header policy, in headless Chromium, at 390 and 1280."""

    @classmethod
    def setUpClass(cls):
        cls.index = baked('index.json')
        cls.page = baked('exposure.json')
        cls.book = cls.index['book']
        cls.reports = {}
        for width in (390, 1280):
            run = subprocess.run(
                [NODE, str(HARNESS), '--root', str(ROOT), '--data', str(OUT), '--width', str(width),
                 '--stamp', STAMP, '--playwright', BROWSER[1], '--chromium', BROWSER[0]],
                capture_output=True, text=True, cwd=ROOT, timeout=600)
            try:
                cls.reports[width] = json.loads(run.stdout)
            except ValueError:
                raise AssertionError('the book harness printed no report: %s %s'
                                     % (run.stdout[-400:], run.stderr[-800:]))

    def each(self):
        for width, report in self.reports.items():
            yield width, report['seen']

    def rows(self, seen, key):
        return [(row['key'], row['cells']) for row in seen['tables'][key]['rows']]

    def test_the_page_opens_clean_under_the_header_policy(self):
        for width, report in self.reports.items():
            self.assertTrue(report['ok'], (width, report['thrown'], report['consoleErrors'],
                                           report['pageErrors'], report['failedRequests'],
                                           report['badResponses']))
            self.assertEqual([], report['consoleErrors'], width)
            self.assertEqual([], report['pageErrors'], width)
            self.assertEqual([], report['failedRequests'], width)
            self.assertEqual([], report['badResponses'], width)
            self.assertLessEqual(report['seen']['overflow'], 0, width)
            self.assertEqual(200, report['status']['/book'], width)
            for name in ('index.json', 'exposure.json'):
                self.assertEqual(200, report['status']['/grid-data/%s/book/%s' % (STAMP, name)], width)
            self.assertTrue(report['seen']['empty']['hidden'], width)

    def test_the_synthetic_label_is_in_the_title_and_on_every_screen(self):
        for width, report in self.reports.items():
            seen = report['seen']
            # Platform polish (PP-A): the shell reads titles into the page-first form.
            self.assertEqual('Synthetic book · InGRID', seen['title'], width)
            self.assertIn('Synthetic', seen['title'])
            self.assertEqual(self.book['label'], seen['flag'], width)
            screens = report['screens']
            self.assertGreater(len(screens), 2, width)
            self.assertGreater(screens[-1]['y'], 0, width)
            for screen in screens:
                self.assertGreaterEqual(screen['top'], 0, (width, screen))
                self.assertLessEqual(screen['bottom'], screen['height'], (width, screen))
                self.assertTrue(screen['onTop'], (width, screen))
                self.assertEqual(self.book['label'], screen['text'], (width, screen))

    def test_the_synthetic_label_is_beside_every_table(self):
        for width, seen in self.each():
            self.assertEqual({'accounts', 'nodes', 'contracts', 'heat', 'exposure', 'impact'}, set(seen['tables']))
            for key, table in seen['tables'].items():
                self.assertIsNotNone(table['caption'], (width, key))
                self.assertTrue(table['caption'].startswith('Synthetic.'), (width, key, table['caption']))

    def test_the_shared_block_the_mount_and_same_origin_links(self):
        # DOCK-5's pin, on the page source: the static block (the no-script fallback) carries the
        # Book entry after the ten, and it is the one marked current.
        block = re.search(r'<nav class="sites"[^>]*>(.*?)</nav>', (GRID / 'book.html').read_text(encoding='utf-8'), flags=re.S).group(1)
        links = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', block)
        self.assertEqual(NAV + [BOOK_ENTRY], [(href, label) for href, _, label in links])
        self.assertEqual([''] * len(NAV) + [' aria-current="page"'], [current for _, current, _ in links])
        for width, seen in self.each():
            # SHELL-1 moved this pin: in the browser the links are the shared bar's, and Book is
            # the one marked current.
            self.assertEqual(SHELL_NAV, [(a['href'], a['label']) for a in seen['nav']], width)
            self.assertEqual(['page' if href == '/book' else None for href, _ in SHELL_NAV],
                             [a['current'] for a in seen['nav']], width)
            self.assertEqual({'context': 'book'}, seen['ask'], width)
            for href in seen['hrefs']:
                self.assertTrue(href.startswith('/') and not href.startswith('//'), (width, href))
            # DOCK-5 moved this pin: the page links itself once, from its own (current) Book entry.
            self.assertEqual(1, seen['hrefs'].count('/book'), width)

    def test_the_head_sentences_are_read_from_the_book_record(self):
        book = self.book
        for width, seen in self.each():
            self.assertEqual('Book %s, record %s, holds %d load nodes and %d contracts at the cutoff of %s.'
                             % (book['version'], short(book['content_digest']), book['counts']['nodes'],
                                book['counts']['contracts'], day_text(self.page['cutoff'])),
                             seen['summary'], width)
            accounts = next(s for s in seen['sections'] if s['key'] == 'accounts')
            self.assertEqual(['At the cutoff of 18 Oct 2026, %s holds %d accounts in Luzon, Visayas and Mindanao.'
                              % (book['version'], book['counts']['accounts'])], accounts['texts'], width)

    def test_every_account_node_and_contract_figure_is_the_book_record_s(self):
        book = self.book
        caption = 'Synthetic. Book record %s · %s · cutoff 18 Oct 2026.' % (short(book['content_digest']),
                                                                          book['version'])
        accounts = [(a['id'], [a['id'], a['name'], a['region'],
                               ', '.join(n['id'] for n in book['nodes'] if n['account_id'] == a['id']),
                               ', '.join(c['id'] for c in book['contracts'] if c['account_id'] == a['id'])])
                    for a in book['accounts']]
        nodes = []
        for n in book['nodes']:
            peak = next(p['peak_mw'] for p in book['profiles'] if p['node_id'] == n['id'])
            self.assertEqual(round(peak, 3), peak)
            nodes.append((n['id'], [n['id'], n['account_id'], n['region'], n['region_code'], fig(peak, 3)]))
        kinds = {'fixed_price': 'fixed price', 'tou_block': 'time-of-use block'}
        runs = self.index['contract_hours']['runs']
        contracts = []
        for c in book['contracts']:
            self.assertEqual(round(c['mw'], 1), c['mw'])
            self.assertEqual(round(c['price_php_mwh']), c['price_php_mwh'])
            hours = ', '.join('%02d:00 to %02d:00' % (a, b) for a, b in runs[c['id']])
            contracts.append((c['id'], [c['id'], c['account_id'], c['node_id'], kinds[c['kind']], fig(c['mw'], 1),
                                        fig(c['price_php_mwh'], 0), hours, day_text(c['term_start']),
                                        day_text(c['term_end'])]))
        for width, seen in self.each():
            self.assertEqual(accounts, self.rows(seen, 'accounts'), width)
            self.assertEqual(nodes, self.rows(seen, 'nodes'), width)
            self.assertEqual(contracts, self.rows(seen, 'contracts'), width)
            for key in ('accounts', 'nodes', 'contracts'):
                self.assertEqual(caption, seen['tables'][key]['caption'], (width, key))
            self.assertEqual(['Contract', 'Account', 'Node', 'Kind', 'Volume MW', 'Price PHP/MWh', 'Clock hours',
                              'Term start', 'Term end'], seen['tables']['contracts']['headers'], width)

    def test_every_heat_cell_is_the_exposure_record_s_with_the_baked_shade(self):
        record = self.page['exposure']
        heat = self.page['heat']
        expected, shades = [], []
        for row in heat['rows']:
            cells = [r for r in record['rows'] if r['node_id'] == row['node_id']]
            for r in cells:
                self.assertEqual(round(r['uncovered_mwh'], 3), r['uncovered_mwh'])
            expected.append((row['node_id'], [row['node_id'], row['account_id']]
                             + [fig(r['uncovered_mwh'], 3) for r in cells]))
            shades.append([{'shade': str(s), 'cls': 'num bk-heat bk-shade-%d' % s} for s in row['shades']])
        for width, seen in self.each():
            table = seen['tables']['heat']
            self.assertEqual(['Node', 'Account'] + ['%02d' % h for h in range(24)], table['headers'], width)
            self.assertEqual(expected, self.rows(seen, 'heat'), width)
            self.assertEqual(shades, [row['shades'] for row in table['rows']], width)
            self.assertEqual('Synthetic. Book record %s · cutoff 18 Oct 2026 · window 19 Oct 2026, 00:00 to 24:00 Manila.'
                             % short(record['book']['content_digest']), table['caption'], width)
            section = next(s for s in seen['sections'] if s['key'] == 'heat')
            edges = [fig(e, 3) for e in heat['edges_mwh']]
            self.assertEqual([
                'The table shows uncovered MWh per load node for each hour of 19 Oct 2026, Manila time.',
                'Darker cells hold more. The four shade steps end at %s and %s MWh.'
                % (', '.join(edges[:-1]), edges[-1]),
            ], section['texts'], width)

    def test_every_exposure_figure_per_account_is_the_exposure_record_s(self):
        record = self.page['exposure']
        expected = [(a['account_id'], [a['account_id'], a['region'], fig(a['demand_mwh'], 3), fig(a['covered_mwh'], 3),
                                       fig(a['uncovered_mwh'], 3)]) for a in record['accounts']]
        expected.append(('total', ['Book total', '', '', '', fig(record['totals']['uncovered_mwh'], 3)]))
        for width, seen in self.each():
            self.assertEqual(expected, self.rows(seen, 'exposure'), width)
            section = next(s for s in seen['sections'] if s['key'] == 'exposure')
            self.assertEqual(['On 19 Oct 2026 the book leaves %s MWh uncovered over %d node hours.'
                              % (fig(record['totals']['uncovered_mwh'], 3), record['totals']['rows'])],
                             section['texts'], width)

    def test_every_impact_figure_is_its_impact_record_s(self):
        expected = []
        for record in self.page['impacts']:
            vintage = record['vintage']['outlook_id']
            for a in record['accounts']:
                for key in ('p10_php', 'p50_php', 'p90_php'):
                    self.assertEqual(round(a[key], 2), a[key])
                expected.append((a['account_id'], [a['account_id'], a['region'], fig(a['uncovered_mwh'], 3),
                                                   fig(a['p10_php'], 2), fig(a['p50_php'], 2), fig(a['p90_php'], 2),
                                                   vintage]))
            totals = record['totals']
            expected.append(('total-' + record['vintage']['series'],
                             ['%s total' % record['accounts'][0]['region'], '', fig(totals['uncovered_mwh'], 3),
                              fig(totals['p10_php'], 2), fig(totals['p50_php'], 2), fig(totals['p90_php'], 2),
                              vintage]))
        for width, seen in self.each():
            self.assertEqual(expected, self.rows(seen, 'impact'), width)
            self.assertEqual(['Account', 'Region', 'Uncovered MWh', 'Low PHP', 'Middle PHP', 'High PHP', 'Vintage'],
                             seen['tables']['impact']['headers'], width)
        # One hand check against BOOK-2's worked figures: the Visayas p50 window sum differs, because
        # this page prices the whole day under the second vintage; the record is the source.
        visayas = next(r for r in self.page['impacts'] if r['vintage']['series'] == 'CVIS')
        self.assertEqual(BOOK2_DIGESTS['book-demo-2026-10-19-cvis-v2'], visayas['vintage']['outlook_digest'])

    def test_the_materiality_line_is_stated_above_the_impact_table(self):
        line = self.page['materiality']
        for width, seen in self.each():
            section = next(s for s in seen['sections'] if s['key'] == 'impact')
            self.assertEqual('The materiality line for the cutoff of 18 Oct 2026 is %s PHP, at or above.'
                             % fig(line['threshold_php'], 2), section['texts'][0], width)
            self.assertEqual('at_or_above', line['comparator'])
            # Review round 1, finding 1: right under the line, the page says what the line is
            # compared against (a change between two vintages, never a level in this table), then
            # the record's own rule in its words, then the basis.
            self.assertEqual('The line applies to a change between two vintages, not to the levels in this table.',
                             section['texts'][1], width)
            self.assertEqual(line['rule'], section['texts'][2], width)
            self.assertIn('later vintage minus the one under the earlier vintage', line['rule'])
            self.assertEqual(line['basis'], section['texts'][3], width)
            self.assertEqual(self.page['selection']['rule'], section['texts'][4], width)
            # The order inside the section: the title, the line and its rule, the vintages and
            # method under one closed fold, the synthetic line, the table.
            order = section['order']
            self.assertEqual('h2', order[0], width)
            self.assertIn('bk-wrap', order[-1].split(), width)
            self.assertEqual('bk-cap bk-say', order[-2], width)
            self.assertIn('bk-more', order[-3].split(), width)
            self.assertEqual(['bk-text bk-say'] * 3, order[1:-3], (width, order))
            self.assertEqual('Synthetic. Every peso figure is a method demonstration on the synthetic book. '
                             'Cutoff 18 Oct 2026 · window 19 Oct 2026.', seen['tables']['impact']['caption'], width)

    def test_each_region_names_its_vintage_by_id_and_record_id(self):
        for width, seen in self.each():
            section = next(s for s in seen['sections'] if s['key'] == 'impact')
            for entry in self.page['selection']['regions']:
                self.assertIn('%s accounts use vintage %s, record %s, issued %s.'
                              % (entry['region'], entry['outlook_id'], short(entry['outlook_digest']),
                                 utc_text(entry['issued_at'])), section['texts'], width)
            self.assertIn(self.page['impacts'][0]['method']['impact'], section['texts'], width)
            # Advisory B: the record's definition of the reference price follows the method sentence.
            method = self.page['impacts'][0]['method']
            self.assertEqual(section['texts'].index(method['impact']) + 1,
                             section['texts'].index(method['reference']), width)

    def test_every_sentence_follows_the_copy_rules(self):
        for width, seen in self.each():
            texts = list(seen['says'])
            for section in seen['sections']:
                texts += section['texts']
            texts.append(seen['caption'])
            self.assertGreater(len(texts), 15, width)
            for text in texts:
                for sentence in REPO.sentences(text):
                    self.assertEqual([], copy_problems(sentence), (width, sentence))

    def test_no_repository_word_or_stronger_status_word_on_the_page(self):
        for width, seen in self.each():
            plain = seen['plain']
            for pattern in BANNED:
                self.assertIsNone(pattern.search(plain), (width, pattern.pattern))
            for word in ('stale', 'current', 'accepted', 'verified'):
                self.assertNotRegex(plain.lower(), r'\b%s\b' % word, (width, word))
            # The record's own rule defines "material" for a change ("It is material when its size
            # reaches the threshold"). Outside that definition no verdict form appears.
            rule = self.page['materiality']['rule']
            self.assertEqual(1, plain.count(rule), width)
            rest = plain.replace(rule, '').lower()
            for verdict in ('is material', 'not material', 'are material', 'material change'):
                self.assertNotIn(verdict, rest, (width, verdict))
            for word in ('tests/', 'src/', '.py', 'synthetic_regional_price', 'BOOK-'):
                self.assertNotIn(word, plain, (width, word))


if __name__ == '__main__':
    unittest.main()
