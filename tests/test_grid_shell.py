"""SHELL-1: one top bar on every page. UX-1 (docs/work/ui-refinement-2026-10-18/intent.md,
outcome 1) replaced SHELL-1's floating side dock with one command bar in the lower middle of every
page but /ask; the tests that pinned the side dock now pin the bar, with the same invariants: present
on every page but /ask, the mount held for ask.js, inside the window, no sideways overflow, and the
open state kept from page to page.

The page source checks run everywhere. The browser check opens every page at 390, 1280 and 1440
pixels through tests/fixtures/grid/shell/browser.mjs when this machine has Chromium and
playwright-core (the pair tests/test_grid_outlooks_page.py finds), and skips otherwise.
"""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / 'src' / 'grid'
HARNESS = ROOT / 'tests' / 'fixtures' / 'grid' / 'shell' / 'browser.mjs'
NODE = shutil.which('node')
SHELL_JS = (GRID / 'shell.js').read_text(encoding='utf-8')
SHELL_CSS = (GRID / 'shell.css').read_text(encoding='utf-8')
ASK_JS = (GRID / 'ask.js').read_text(encoding='utf-8')
ASK_CSS = (GRID / 'ask.css').read_text(encoding='utf-8')
COMMAND_JS = (GRID / 'command.js').read_text(encoding='utf-8')
COMMAND_CSS = (GRID / 'command.css').read_text(encoding='utf-8')
UI_JS = (GRID / 'ui.js').read_text(encoding='utf-8')
UI_CSS = (GRID / 'ui.css').read_text(encoding='utf-8')

#: Every page the application serves from src/grid, at one of its routes (the harness's list).
PAGES = {
    '/': 'index.html', '/event/syn-bay-unit-2-trip': 'event.html', '/book': 'book.html',
    '/outlooks': 'outlooks.html', '/register': 'register.html', '/models': 'models.html',
    '/work': 'work.html', '/map': 'map.html', '/ask': 'ask.html', '/alerts': 'alerts.html',
    '/settings': 'settings.html', '/assets': 'assets.html', '/asset/syn-node-1': 'asset.html',
    '/data': 'catalog.html', '/explain': 'explain.html', '/paper': 'paper.html',
    '/journal': 'journal.html', '/notices': 'notices.html', '/alert/0123456789abcdef01234567': 'spike.html',
}
#: The bar's links in order (platform polish, intent.md "Primary navigation"): the four primary
#: links, then the Decisions, Evidence and About menus. Ask has no item: the command bar is its way in.
SHELL_NAV = [('/', 'Desk'), ('/alerts', 'Alerts'), ('/notices', 'Notices'), ('/plants', 'Plants'),
             ('/journal', 'Journal'), ('/outlooks', 'Outlooks'), ('/register', 'Assumption register'), ('/book', 'Book'),
             ('/data', 'Data catalog'), ('/models', 'Models'),
             ('/paper', 'Research paper'), ('/explain', 'How it works'), ('/work', 'The future of work case'),
             ('/map', 'Project map')]
#: The section each page sits under (intent.md "The current section and breadcrumbs").
SECTION = {'/': 'Desk', '/alerts': 'Alerts', '/notices': 'Notices', '/assets': 'Plants', '/asset/syn-node-1': 'Plants',
           '/event/syn-bay-unit-2-trip': 'Alerts', '/alert/0123456789abcdef01234567': 'Alerts', '/settings': 'Alerts',
           '/journal': 'Decisions', '/outlooks': 'Decisions', '/register': 'Decisions', '/book': 'Decisions',
           '/data': 'Evidence', '/models': 'Evidence', '/paper': 'About', '/explain': 'About', '/work': 'About', '/map': 'About'}
WIDTHS = (390, 1280, 1440)


def browser():
    """Chromium and playwright-core, if this machine has them (as tests/test_grid_outlooks_page.py)."""
    chromium = os.environ.get('GRID_BROWSER_CHROMIUM', '')
    playwright = os.environ.get('GRID_BROWSER_PLAYWRIGHT', '')
    if not chromium:
        found = sorted((p.parent.parent.name, str(p))
                       for p in (Path.home() / '.cache' / 'ms-playwright').glob('chromium-*/chrome-linux*/chrome'))
        chromium = found[-1][1] if found else ''
    if not playwright:
        linked = ROOT / '.local' / 'deckcheck' / 'node_modules' / 'playwright-core' / 'index.mjs'
        playwright = str(linked) if linked.is_file() else ''
    return chromium, playwright


BROWSER = browser()


class ThePageSources(unittest.TestCase):
    def test_every_page_loads_the_shell_in_its_head_after_its_base_stylesheets(self):
        for route, name in PAGES.items():
            html = (GRID / name).read_text(encoding='utf-8')
            head = html[:html.index('</head>')]
            sheets = re.findall(r'<link rel="stylesheet" href="/grid/__NOWCAST_STAMP__/([a-z-]+\.css)">', head)
            # The shell's tokens and bar rules come after each base sheet a page carries (the
            # site's grid.css and catalog.css, the paper's and the explainer's own) and ask.css.
            self.assertIn('shell.css', sheets, name)
            for base in ('grid.css', 'catalog.css', 'paper.css', 'explain.css', 'ask.css'):
                if base in sheets:
                    self.assertLess(sheets.index(base), sheets.index('shell.css'), (name, sheets))
            self.assertIn('<script src="/grid/__NOWCAST_STAMP__/shell.js"></script>', head, name)

    def test_the_shell_builds_one_bar_from_its_own_menu(self):
        self.assertIn("bar = make('header', 'gn-bar');", SHELL_JS)
        self.assertIn("bar.id = 'gn-bar';", SHELL_JS)
        self.assertIn('document.body.prepend(bar);', SHELL_JS)
        self.assertIn("root.classList.add('gn-shell');", SHELL_JS)
        menu = re.findall(r"\['(/[a-z]*)', '([^']+)'(?:, '[^']*')?\]", SHELL_JS[SHELL_JS.index('const MAIN = ['):SHELL_JS.index('const SETTINGS')])
        self.assertEqual(SHELL_NAV, menu)
        # Every menu item says in one line what it is for, within the copy rules.
        for label, desc in re.findall(r"\['/[a-z]+', '([^']+)', '([^']+)'\]", SHELL_JS):
            self.assertLessEqual(len(desc.split()), 20, desc)
            self.assertNotIn('—', desc)
            self.assertNotIn(';', desc)
        for group in ("label: 'Decisions'", "label: 'Evidence'", "label: 'About'"):
            self.assertIn(group, SHELL_JS)
        # The current section: an event, an alert and the settings sit under Alerts, a plant under Plants.
        body = SHELL_JS[SHELL_JS.index('function currentPath() {'):SHELL_JS.index('function sectionLabel() {')]
        self.assertIn("p.startsWith('/event/') || p.startsWith('/alert/') || p === SETTINGS) return '/alerts';", body)
        self.assertIn("p.startsWith('/plant/')", body)
        # The bar goes in before the first paint: a mutation observer waits for the body.
        self.assertIn('new MutationObserver(', SHELL_JS)

    def test_the_static_bars_are_hidden_while_the_shell_runs_and_the_bar_sets_its_own_type(self):
        self.assertIn(':root.gn-shell body > header.bar, :root.gn-shell .bk-top > header.bar,', SHELL_CSS)
        self.assertIn(':root.gn-shell .gn-page-bar[hidden] { display: none !important; }', SHELL_CSS)
        self.assertRegex(SHELL_CSS, r'#gn-bar \{ font: 400 13px/1\.45 var\(--sans\);')

    def test_the_second_row_is_a_live_strip_and_the_replay_sits_behind_as_of(self):
        """UX-4: the scrolling ticker is gone; the strip has three sections and the replay opens
        from the As of control. The desk's mark keeps the bar's replay out (UX-3 contract)."""
        self.assertNotIn('gn-ticker', SHELL_JS)
        self.assertNotIn('gn-ticker', SHELL_CSS)
        self.assertNotIn('@keyframes gn-scroll', SHELL_CSS)
        for label in ("'Prices'", "'HVDC congestion'", "'Alerts and notices'"):
            self.assertIn(label, SHELL_JS)
        self.assertIn("document.body.dataset.replay === 'page'", SHELL_JS)
        self.assertIn("if (clock && !deskReplay() && asOfSlot && asOfBtn)", SHELL_JS,
                      "the desk's clock is never adopted into the bar")
        self.assertIn("asOfBtn.setAttribute('aria-haspopup', 'dialog');", SHELL_JS)
        self.assertIn("asOfPop.setAttribute('role', 'dialog');", SHELL_JS)
        # A page that opts out asks for nothing: the strip, its notices and the inbox all check it.
        self.assertIn("document.body.dataset.ticker !== 'off'", SHELL_JS)
        self.assertIn("if (!row2Left || !stripOn()) return;", SHELL_JS)
        self.assertIn("if (!alertsApi || !stripOn()) return;", SHELL_JS)
        # One fixed row height, so the bar is the same on every page.
        self.assertIn('height: var(--gn-strip-h);', SHELL_CSS)
        self.assertIn('--gn-strip-h: 40px;', SHELL_CSS)
        # Shared tokens for the other slices.
        for token in ('--sev-alert:', '--sev-warning:', '--sev-info:', '--p-none:'):
            self.assertIn(token, SHELL_CSS)
        # The public clock is unchanged; the price colour and severity are shared.
        for name in ('asOf:', 'setAsOf,', 'onAsOf:', 'span: SPAN,', 'ready,', 'dayFile,', 'priceTone,', 'severityOf,'):
            self.assertIn(name, SHELL_JS[SHELL_JS.index('window.GNShell = {'):])

    def test_the_strip_reads_the_desks_data_and_asks_for_nothing_twice(self):
        # Day files through the shared cache. A bake without them is read on the desk only, from
        # the page's own copy (GridDesk.D): the whole-window files are never asked for again.
        self.assertIn('const files = await Promise.all(days.map((d) => dayFile(d)));', SHELL_JS)
        self.assertNotIn("getJson('regions.json')", SHELL_JS)
        self.assertNotIn("getJson('hvdc.json')", SHELL_JS)
        self.assertIn("document.querySelector('script[src$=\"/grid.js\"]')", SHELL_JS)
        self.assertIn("window.addEventListener('grid-desk-ready', take, { once: true });", SHELL_JS)

    def test_the_strip_links_where_the_desk_map_listens(self):
        # The desk map reads ?grid= and ?link=; a notice opens on the notices page, an event on
        # its own page. On the desk itself the address changes in place and a popstate follows.
        self.assertIn("a.href = '/?grid=' + g;", SHELL_JS)
        self.assertIn("a.href = '/?link=' + id;", SHELL_JS)
        self.assertIn("'/notices?at=' + tkey(a.t) + '#adv-' + encodeURIComponent(a.id)", SHELL_JS)
        self.assertIn("'/event/' + encodeURIComponent(ev.id)", SHELL_JS)
        self.assertIn("history.pushState(null, '', e.currentTarget.getAttribute('href'));", SHELL_JS)
        self.assertIn("window.dispatchEvent(new PopStateEvent('popstate', { state: null }));", SHELL_JS)

    def test_the_bar_copy_keeps_the_copy_rules(self):
        # Button labels of 16 characters or fewer, no em dash and no semicolon in the bar's words
        # (the bar and its second row, and the live strip; the sign-in screen has its own copy).
        bar = SHELL_JS[:SHELL_JS.index('// ---------- sign-in (decision D1)')]
        bar += SHELL_JS[SHELL_JS.index('// ---------- notices and alerts'):SHELL_JS.index('// ---------- the replay index')]
        strings = re.findall(r"make\('(?:button|a|span|summary)', '[^']*', '([^']+)'\)", bar)
        strings += re.findall(r"setAttribute\('aria-label', '([^']+)'\)", bar)
        for text in strings:
            self.assertNotIn('—', text)
            self.assertNotIn(';', text)
        for label in re.findall(r"make\('button', '[^']*', '([^']+)'\)", bar):
            self.assertLessEqual(len(label), 16, label)
        self.assertNotIn('—', SHELL_JS[SHELL_JS.index('// ---------- the live strip'):SHELL_JS.index('// ---------- the replay index')])

    def test_the_command_bar_loads_on_every_page_and_is_the_ask_page(self):
        # UX-1 moves this pin: the side dock (`#gn-dock`, its launcher and the 400px body padding)
        # is gone, and shell.js loads the command bar's two files on every page but /ask.
        for gone in ('gn-dock', 'floatDock', "matchMedia('(min-width: 1400px)')"):
            self.assertNotIn(gone, ASK_JS)
        self.assertNotIn('gn-dock', ASK_CSS)
        self.assertNotIn('padding-right: 400px', ASK_CSS)
        self.assertNotIn('padding-right', COMMAND_CSS)
        body = SHELL_JS[SHELL_JS.index('function ensureDock() {'):SHELL_JS.index('function start() {')]
        # Platform polish moves this pin: /ask loads the bar too, as the page's conversation.
        self.assertNotIn("if (parts[0] === 'ask') return;", body)
        self.assertIn("sheet('command.css');", body)
        self.assertIn("loadScript('command.js')", body)
        # A page without a mount still gets one from the shell, with ask.js from this build.
        self.assertIn("loadScript('ask.js')", body)
        self.assertIn("const WORKSPACE = PARTS[0] === 'ask';", COMMAND_JS)
        self.assertIn('id="ask-main"', (GRID / 'ask.html').read_text(encoding='utf-8'))
        for route, name in PAGES.items():
            html = (GRID / name).read_text(encoding='utf-8')
            if 'id="ask"' not in html:
                self.assertIn(name, ('journal.html', 'notices.html', 'spike.html'), name)
            # The bar ships only through the shell: no page names its files.
            self.assertNotIn('command.js', html, name)
            self.assertNotIn('command.css', html, name)

    def test_the_command_bar_is_one_accessible_combobox_with_a_planned_mic(self):
        self.assertIn('role="combobox"', COMMAND_JS)
        self.assertIn('aria-controls="gc-list"', COMMAND_JS)
        self.assertIn('role="listbox"', COMMAND_JS)
        self.assertIn('aria-activedescendant', COMMAND_JS)
        self.assertIn('aria-live="polite"', COMMAND_JS)
        # The assistant's name comes from the shell's one constant (GNShell.agent).
        self.assertIn("aria-label=\"' + esc('Search or ask ' + AGENT) + '\"", COMMAND_JS)
        self.assertIn("placeholder=\"' + esc('Search plants, events, data, or ask ' + AGENT) + '\"", COMMAND_JS)
        # Voice input is shown and planned, not wired: no speech API is touched.
        self.assertIn('aria-disabled="true" aria-label="Voice input, coming soon"', COMMAND_JS)
        for api in ('SpeechRecognition', 'getUserMedia', 'webkitSpeech'):
            self.assertNotIn(api, COMMAND_JS)
        # Keyboard first: "/" and Ctrl or Cmd with K focus the bar, Esc collapses it.
        self.assertIn("key === '/'", COMMAND_JS)
        self.assertIn("(key === 'k' || key === 'K') && (event.metaKey || event.ctrlKey)", COMMAND_JS)
        self.assertIn("key === 'Escape'", COMMAND_JS)

    def test_the_command_bar_reads_only_the_desk_api_and_keeps_the_thread_in_the_session(self):
        self.assertIn("const API = '/api/desk/';", COMMAND_JS)
        self.assertEqual(1, COMMAND_JS.count('fetch('))
        for route in ("API + 'prompts?'", "API + 'search?'", "API + 'answer'"):
            self.assertIn(route, COMMAND_JS)
        # Platform polish: the preview card and its one cache moved to ui.js, shared site-wide.
        self.assertIn("API + 'preview/'", UI_JS)
        self.assertEqual(1, UI_JS.count('fetch('))
        self.assertIn('UI().preview(anchor, kind, id', COMMAND_JS)
        for forbidden in ('EventSource', 'XMLHttpRequest', 'WebSocket', 'eval(', 'import(',
                          "createElement('script", 'document.write', 'localStorage'):
            self.assertNotIn(forbidden, COMMAND_JS)
        self.assertIn("const STORE_KEY = 'nowcast.command.v1';", COMMAND_JS)
        self.assertIn('window.sessionStorage', COMMAND_JS)
        # Signed in, the desk API learns who asks (live Gemini answers) from the shell's token.
        self.assertIn("headers.Authorization = 'Bearer ' + token;", COMMAND_JS)
        # CSP: no inline style attribute or handler in the markup the bar writes.
        self.assertNotRegex(COMMAND_JS, r'style="|\son[a-z]+="')


    def test_the_bar_names_gemini_only_for_a_gemini_run(self):
        # The model badge and the trace header claim Gemini only when the answer's `model` says a
        # Gemini run (live or recorded) wrote it. A composed answer says so, never Gemini. The bar
        # names Ingrid, the agent, never the model (owner, 19 October: "Ask Ingrid", no "Ask Gemini").
        self.assertNotRegex(COMMAND_JS, r"'[^'\n]*\bAsk Gemini\b")
        self.assertNotIn("'Gemini is reading", COMMAND_JS)
        self.assertIn("const GEMINI_MODES = ['live', 'recorded'];", COMMAND_JS)
        self.assertIn("isGemini(answer.model) ? AGENT + ' traced ' + count : 'Traced ' + count", COMMAND_JS)
        self.assertIn("badgeHtml('composed', 'Composed from records', reason, 'composed')", COMMAND_JS)
        self.assertIn("AGENT + ' · recorded run'", COMMAND_JS)
        # The placeholder names Gemini only after the server reported a Gemini run for prompts.
        self.assertIn("if (state.gemini) words =", COMMAND_JS)
        self.assertIn("const gemini = isGemini(prompts.model);", COMMAND_JS)
        # No fake progress before the answer: the pending line waits, and the trace steps fire
        # only from the trace the server returned.
        self.assertIn("esc(AGENT) + ' is reading the records at '", COMMAND_JS)
        self.assertIn("const steps = list(turn.answer && turn.answer.trace);", COMMAND_JS)

    def test_the_pending_answer_moves_and_counts_the_seconds(self):
        # Patch of 18 October (owner: no feedback while a live answer is on its way, so it felt
        # frozen). The pending line is a status region with a ring and a seconds counter, the
        # send button carries aria-busy, the ring stands still under reduced motion, and no step
        # is invented: the trace still comes only from the server's answer.
        self.assertIn('<p class="gc-wait">', COMMAND_JS)
        self.assertIn('<span class="gc-spin" aria-hidden="true"></span>', COMMAND_JS)
        # The counter is visual only: the thread is already a live region, and a line re-announced
        # every second would be noise.
        self.assertIn('<span class="gc-elapsed" aria-hidden="true" data-since="', COMMAND_JS)
        self.assertIn("root.classList.toggle('gc-busy', busy);", COMMAND_JS)
        self.assertIn("setAttribute('aria-busy', busy ? 'true' : 'false')", COMMAND_JS)
        self.assertIn("if (!busy && ticker) { clearInterval(ticker); ticker = null; }", COMMAND_JS)
        css = (GRID / 'command.css').read_text(encoding='utf-8')
        self.assertIn('@keyframes gc-spin', css)
        self.assertIn('.gc-spin { flex: none; width: 14px; height: 14px;', css)
        # One slow ring (the design brief's exception for the pending answer); the send button's
        # ring is still, drawn on ::before so the tooltip's ::after is untouched.
        self.assertIn('animation: gc-spin 1.4s linear infinite', css)
        self.assertIn('.gc-busy .gc-send::before {', css)
        self.assertNotIn('.gc-busy .gc-send::after', css)
        reduced = css[css.index('@media (prefers-reduced-motion: reduce)'):]
        self.assertIn('.gc-spin', reduced.split('}')[0])

    def test_a_live_answer_streams_its_steps_as_they_run(self):
        # STREAM-1 (owner, 18 October: show Gemini's tool calls while it works). For a live run the
        # bar reads `/api/desk/answer/stream` with fetch and a reader (no other streaming API). Each
        # `step` event is a tool call the server says has run, drawn with the final trace's own
        # markup under the pending line. The `answer` event is the plain route's body and builds the
        # turn as before. Without a stream, or on any failure, the plain route answers.
        self.assertIn("let answer = turn.live ? await askStream(turn, asked) : null;", COMMAND_JS)
        self.assertIn("const send = (url, init) => fetch(url,", COMMAND_JS)
        self.assertIn("await send(API + 'answer/stream', {method: 'POST',", COMMAND_JS)
        self.assertIn("'Accept': 'text/event-stream'", COMMAND_JS)
        self.assertIn("response.body.getReader()", COMMAND_JS)
        self.assertIn("if (typeof ReadableStream !== 'function' || typeof TextDecoder !== 'function') return null;",
                      COMMAND_JS)
        self.assertIn("type.indexOf('text/event-stream') !== 0) return null;", COMMAND_JS)
        self.assertIn("if (!event || event.event === 'error') throw new Error('stream');", COMMAND_JS)
        self.assertIn("return {ok: true, status: 200, data: event.answer};", COMMAND_JS)
        self.assertIn("if (chunk.done) return null;", COMMAND_JS)
        # the fallback: the plain route, the same body, when the stream gave no answer
        fallback = COMMAND_JS[COMMAND_JS.index('let answer = turn.live'):]
        self.assertIn("if (!answer) {", fallback.split('getJson(')[0])
        self.assertIn("answer = await getJson(API + 'answer', {method: 'POST',", COMMAND_JS)
        # the live steps reuse the trace's step markup, and only a server event adds one
        self.assertIn("if (event.event === 'step') liveStep(turn, event.step);", COMMAND_JS)
        self.assertIn("box.insertAdjacentHTML('beforeend', stepHtml(step));", COMMAND_JS)
        self.assertIn('\'<ol class="gc-steps gc-trace-live" aria-label="Steps \' + esc(AGENT) + \' has run so far"\'', COMMAND_JS)
        self.assertIn("list(turn.steps).map(stepHtml).join('')", COMMAND_JS)
        self.assertEqual(2, COMMAND_JS.count('liveStep('), 'one definition, one call: the step event')
        # the answer's own trace still comes only from the server's answer
        self.assertIn("const steps = list(turn.answer && turn.answer.trace);", COMMAND_JS)
        css = (GRID / 'command.css').read_text(encoding='utf-8')
        self.assertIn('.gc-trace-live .gc-step { animation: gc-rise .18s ease-out; }', css)
        reduced = css[css.index('@media (prefers-reduced-motion: reduce)'):]
        self.assertIn('.gc-step,', reduced.split('}')[0], 'an arriving step does not move under reduced motion')

    def test_the_product_and_agent_names_are_written_once(self):
        # design-system.md, "Renaming the product": a rename is one line in shell.js. Outside the
        # two constants no script writes either name (comments aside).
        import re as _re
        self.assertIn("const BRAND = 'InGRID';", SHELL_JS)
        self.assertIn("const AGENT = 'Ingrid';", SHELL_JS)
        self.assertIn('brand: BRAND,', SHELL_JS)
        self.assertIn('agent: AGENT,', SHELL_JS)
        for name, source in (('shell.js', SHELL_JS), ('command.js', COMMAND_JS), ('ui.js', UI_JS)):
            code = _re.sub(r'/\*.*?\*/', '', source, flags=_re.S)
            code = _re.sub(r'(?m)//[^\n]*$', '', code)
            literals = _re.findall(r"'((?:[^'\\]|\\.)*)'", code)
            # The brand files (ingrid-mark.svg, ingrid-logo.svg) are file names, not the name.
            names = [_re.sub(r'ingrid-(?:mark|logo)\.svg', '', x) for x in literals]
            hits = [x for x in names if 'InGRID' in x or 'ingrid' in x.lower()]
            expected = ['InGRID', 'Ingrid'] if name == 'shell.js' else []
            self.assertEqual(expected, hits, name)
            # The old names are gone from every script: the desk is a page, never the assistant.
            self.assertFalse([x for x in literals if 'Grid Nowcast' in x or 'ask the desk' in x.lower()], name)
        # The copy reads as well with a proper name: no possessive of the agent.
        for source in (SHELL_JS, COMMAND_JS):
            self.assertNotIn("AGENT + '\\'s", source)

    def test_the_bars_own_sentences_follow_the_copy_rules(self):
        code = re.sub(r'/\*.*?\*/', '', COMMAND_JS, flags=re.S)
        code = re.sub(r'(?m)^\s*//[^\n]*', '', code)
        sentences = []
        for literal in re.findall(r"'((?:[^'\\]|\\.)*)'", code):
            text = re.sub(r'<[^>]*>', ' ', literal)
            if '<' in text or '>' in text:
                continue
            text = re.sub(r'\s+', ' ', text).strip()
            for sentence in re.split(r'(?<=[.!?])\s+', text):
                if sentence.endswith(('.', '?')) and len(sentence.split()) >= 3 and sentence[0].isupper():
                    sentences.append(sentence)
        self.assertGreater(len(sentences), 10)
        for sentence in sentences:
            self.assertLessEqual(len(sentence.split()), 20, sentence)
            self.assertNotIn(';', sentence)
            self.assertNotIn('—', sentence)
        for filler in ('Unlock', 'Powered by', 'intelligent assistant', 'AI-powered'):
            self.assertNotIn(filler, COMMAND_JS)


@unittest.skipUnless(NODE and BROWSER[0] and BROWSER[1], 'needs node, Chromium and playwright-core')
class EveryPageInTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run([NODE, str(HARNESS), '--root', str(ROOT), '--playwright', BROWSER[1],
                              '--chromium', BROWSER[0], '--widths', ','.join(map(str, WIDTHS))],
                             capture_output=True, text=True, cwd=ROOT, timeout=600)
        try:
            cls.report = json.loads(run.stdout)
        except ValueError:
            raise AssertionError('the shell harness printed no report: %s %s' % (run.stdout[-400:], run.stderr[-800:]))

    def each(self):
        for width in WIDTHS:
            yield width, self.report['widths'][str(width)]

    def test_every_page_carries_one_bar_first_and_no_static_bar(self):
        for width, run in self.each():
            self.assertEqual([], run['errors'], width)
            for route, seen in run['seen'].items():
                where = (width, route)
                self.assertEqual(1, seen['bars'], where)
                self.assertTrue(seen['barFirst'], where)
                self.assertFalse(seen['staticNavShown'], where)
                self.assertEqual([], seen['staticBarsShown'], where)
                self.assertLessEqual(seen['barOverflow'], 0, where)
                self.assertEqual('13px Inter', seen['barFont'], where)

    def test_the_bar_is_the_same_on_every_page(self):
        for width, run in self.each():
            heights = {seen['bar']['height'] for seen in run['seen'].values()}
            self.assertEqual(1, len(heights), (width, heights))
            for route, seen in run['seen'].items():
                self.assertEqual(SHELL_NAV, [(href, label) for href, label, _ in seen['nav']], (width, route))
                # One current section per page, and the right one.
                if route in SECTION:
                    self.assertEqual([SECTION[route]], seen['here'], (width, route))
                # A phone gets the Menu button in place of the links.
                if width <= 760:
                    self.assertFalse(seen['navShown'], (width, route))
                    self.assertEqual('Menu', seen['menuButton']['label'], (width, route))
                    self.assertGreaterEqual(seen['menuButton']['box']['height'], 24, (width, route))
                else:
                    self.assertTrue(seen['navShown'], (width, route))
                    self.assertIsNone(seen['menuButton'], (width, route))
                # Specific titles: the page's words, then the section, then the product.
                # (A title in the older "InGRID · Alerts" form is read into the new one.)
                self.assertFalse(seen['title'].startswith('InGRID ·'), (route, seen['title']))
                if '<title>InGRID · ' in (GRID / PAGES[route]).read_text(encoding='utf-8'):
                    self.assertTrue(seen['title'].endswith(' · InGRID'), (route, seen['title']))
                self.assertEqual(0, seen['bar']['left'], (width, route))
                self.assertEqual(seen['view']['width'], seen['bar']['right'], (width, route))

    def test_every_page_carries_the_live_strip_at_one_row_height(self):
        for width, run in self.each():
            heights = {seen['row2']['box']['height'] for seen in run['seen'].values()}
            self.assertEqual(1, len(heights), (width, heights))
            for route, seen in run['seen'].items():
                where = (width, route)
                row2 = seen['row2']
                self.assertEqual(['Prices', 'HVDC congestion', 'Alerts and notices'], row2['sections'], where)
                self.assertFalse(row2['ticker'], where)
                if route != '/':
                    # Every page but the desk opens the replay from its As of control.
                    self.assertTrue(row2['asOfButton'], where)
                    self.assertRegex(row2['asOfText'], r'\d{1,2} [A-Z][a-z]{2} \d{2}:\d{2}', where)
                    self.assertEqual(0, row2['replayInBar'], f'{where}: the replay stays in its popover')
                for target in row2['targets']:
                    self.assertGreaterEqual(target['box']['height'], 24, (where, target['label']))
                    self.assertTrue(target['label'], where)
                self.assertTrue(seen['theme']['label'].startswith('Switch to '), where)
                self.assertEqual('', seen['theme']['text'], f'{where}: the theme switch is an icon button')
                self.assertGreaterEqual(min(seen['theme']['box']['width'], seen['theme']['box']['height']), 24, where)

    def test_the_desk_mark_keeps_the_replay_out_of_the_bar(self):
        for width, run in self.each():
            desk = run['desk']
            self.assertEqual(run['seen']['/notices']['bar']['height'], desk['bar']['height'], width)
            self.assertFalse(desk['row2']['asOfButton'], width)
            self.assertTrue(desk['row2']['asOfLabel'], width)
            self.assertFalse(desk['row2']['pageClockInBar'], f"{width}: the desk's clock is not adopted")
            self.assertEqual(0, desk['row2']['replayInBar'], width)
            self.assertEqual(['Prices', 'HVDC congestion', 'Alerts and notices'], desk['row2']['sections'], width)

    def test_the_as_of_control_opens_the_replay_and_steps_the_shared_clock(self):
        for width, run in self.each():
            pop = run['popover']
            self.assertFalse(pop['closed']['open'], width)
            self.assertEqual('false', pop['closed']['expanded'], width)
            opened = pop['opened']
            self.assertTrue(opened['open'], width)
            self.assertEqual('true', opened['expanded'], width)
            self.assertEqual('dialog', opened['role'], width)
            labels = [c['label'] for c in opened['controls']]
            for name in ('Back five minutes', 'Play', 'Forward five minutes', 'Replay day', 'Replay time of day'):
                self.assertIn(name, labels, width)
            self.assertGreaterEqual(opened['box']['left'], 0, width)
            self.assertLessEqual(opened['box']['right'], opened['view']['width'], width)
            for control in opened['controls']:
                box = control['box']
                self.assertGreaterEqual(box['left'], 0, (width, control['label']))
                self.assertLessEqual(box['right'], opened['view']['width'], (width, control['label']))
                if control['label'] in ('Back five minutes', 'Play', 'Forward five minutes'):
                    self.assertGreaterEqual(min(box['width'], box['height']), 24, (width, control['label']))
            self.assertEqual('13:40 PHT', opened['time'], width)
            self.assertEqual('13:45 PHT', pop['stepped']['time'], width)
            self.assertTrue(pop['stepped']['asOf'].endswith('13:45'), 'the As of control follows the clock')
            self.assertFalse(pop['escaped']['open'], f'{width}: Esc closes the popover')
            self.assertTrue(pop['focusBack'], f'{width}: focus returns to the As of control')

    def test_the_command_bar_rests_in_the_lower_middle_of_every_page_and_fills_the_ask_page(self):
        for width, run in self.each():
            for route, seen in run['seen'].items():
                where = (width, route)
                self.assertFalse(seen['sideDock'], where)
                self.assertEqual('0px', seen['bodyPadRight'], where)
                self.assertLessEqual(seen['pageOverflow'], 0, where)
                if route == '/ask':
                    # Platform polish: /ask is the conversation itself. The bar fills the
                    # workspace's centre and ask.js's panel stays in the left rail, in the flow.
                    self.assertIsNotNone(seen['cmd'], where)
                    self.assertTrue(seen['cmd']['workspace'], where)
                    self.assertFalse(seen['cmd']['holdsMount'], where)
                    self.assertTrue(seen['cmd']['mountInRail'], where)
                    self.assertTrue(seen['cmd']['open'], where)
                    continue
                cmd = seen['cmd']
                self.assertIsNotNone(cmd, where)
                # ask.js's mount lives in the sheet's panel, out of the page's flow.
                self.assertTrue(cmd['holdsMount'], where)
                self.assertFalse(cmd['open'], where)
                self.assertEqual('Search or ask Ingrid', cmd['input']['label'], where)
                self.assertEqual('combobox', cmd['input']['role'], where)
                self.assertEqual({'label': 'Voice input, coming soon', 'disabled': 'true'}, cmd['mic'], where)
                view = seen['view']
                if cmd['reading']:
                    # A reading page (.gn-page--read) starts with the compact pill at the lower
                    # right, so the bar never sits over its prose.
                    self.assertTrue(cmd['compact'], where)
                    self.assertLessEqual(view['width'] - cmd['pillBox']['right'], 24, where)
                    self.assertLessEqual(view['height'] - cmd['pillBox']['bottom'], 24, where)
                    continue
                self.assertFalse(cmd['compact'], where)
                pill = cmd['pill']
                # Centred, inside the window, and lifted off the bottom edge.
                self.assertLessEqual(abs(pill['left'] + pill['right'] - view['width']), 2, where)
                self.assertGreaterEqual(pill['left'], 16, where)
                self.assertLessEqual(pill['right'], view['width'] - 16, where)
                self.assertGreaterEqual(view['height'] - pill['bottom'], 12, where)
                if width > 640:
                    self.assertGreaterEqual(view['height'] - pill['bottom'], 60, 'lower middle, not the bottom edge')
                self.assertGreater(pill['top'], seen['bar']['bottom'], where)
                for control in cmd['controls']:
                    self.assertGreaterEqual(control['box']['width'], 24, (where, control['name']))
                    self.assertGreaterEqual(control['box']['height'], 24, (where, control['name']))

    def test_asking_opens_the_sheet_and_the_thread_holds_from_page_to_page(self):
        for width, run in self.each():
            toggled = run['toggled']
            self.assertTrue(toggled['focused']['cmd']['focused'], width)
            self.assertTrue(toggled['focused']['cmd']['listShown'], 'the empty bar lists its suggestions')
            self.assertTrue(toggled['typed']['cmd']['options'][0].startswith('Ask Ingrid: “synthetic sun”'), width)
            asked = toggled['asked']
            self.assertTrue(asked['cmd']['open'], width)
            self.assertEqual(1, asked['cmd']['turns'], width)
            box, view, bar = asked['cmd']['box'], asked['view'], asked['bar']
            self.assertGreaterEqual(box['left'], 0, width)
            self.assertLessEqual(box['right'], view['width'], width)
            self.assertLessEqual(box['bottom'], view['height'], width)
            self.assertGreaterEqual(box['top'], bar['bottom'], width)
            if width <= 640:
                self.assertEqual(view['width'], box['width'], 'a phone gets the full-width bottom sheet')
            # A long answer grows the sheet, which stops under the bar and inside the window.
            long_box, long_bar = toggled['longAnswer']['cmd']['box'], toggled['longAnswer']['bar']
            self.assertGreaterEqual(long_box['top'], long_bar['bottom'], width)
            self.assertLessEqual(long_box['bottom'], view['height'], width)
            self.assertGreater(long_box['height'], box['height'], 'the long answer grew the sheet')
            # The open sheet and its thread follow the person to the next page; Esc collapses it,
            # and the collapsed bar keeps the thread one click away on the page after.
            self.assertTrue(toggled['nextPage']['cmd']['open'], width)
            self.assertEqual(1, toggled['nextPage']['cmd']['turns'], width)
            self.assertFalse(toggled['afterEsc']['cmd']['open'], width)
            self.assertFalse(toggled['afterClose']['cmd']['open'], width)
            self.assertEqual('1 answer', toggled['afterClose']['cmd']['resume'], width)

    def test_the_menus_open_by_click_and_keyboard_with_descriptions(self):
        for width, run in self.each():
            ia = run['ia']
            if width <= 760:
                sheet = ia['sheet']
                self.assertIsNotNone(sheet, width)
                for label in [label for _, label in SHELL_NAV]:
                    self.assertIn(label, sheet['links'], label)
                self.assertEqual('true', sheet['modal'])
                self.assertTrue(sheet['full'], 'a full-height sheet on a phone')
                self.assertTrue(sheet['focusIn'])
                self.assertEqual('true', sheet['expanded'])
                self.assertLessEqual(sheet['overflow'], 0)
                self.assertEqual({'open': False, 'focusBack': True}, ia['sheetEsc'])
                continue
            menu = ia['menuOpen']
            self.assertTrue(menu['open'], width)
            self.assertEqual('true', menu['expanded'])
            self.assertEqual('menu', menu['role'])
            self.assertEqual(['Journal', 'Outlooks', 'Assumption register', 'Book'], [t for t, _ in menu['items']])
            for _, desc in menu['items']:
                self.assertTrue(desc.endswith('.'), desc)
            self.assertTrue(menu['inView'], width)
            self.assertEqual('Journal', ia['menuFirst']['text'])
            self.assertEqual('Outlooks', ia['menuNext']['text'])
            self.assertEqual({'evidence': True, 'decisions': False}, ia['menuSide'], 'the side arrows move to the next menu')
            self.assertFalse(ia['menuEsc']['open'])
            self.assertEqual('gn-nav-evidence', ia['menuEsc']['focus'], 'Esc returns focus to its menu button')
            self.assertTrue(ia['menuClick'])
            self.assertFalse(ia['menuOutside'], 'a click outside closes the menu')

    def test_the_shortcuts_sheet_and_keys(self):
        for width, run in self.each():
            ia = run['ia']
            keys = ia['keys']
            self.assertIsNotNone(keys, width)
            self.assertEqual('true', keys['modal'])
            self.assertTrue(keys['focusIn'])
            for words in ('Show these shortcuts', 'Go to Desk', 'Go to Alerts', 'Go to Notices', 'Go to Plants',
                          'Go to Journal', 'Go to Data catalog', 'Replay clock back five minutes'):
                self.assertIn(words, keys['rows'])
            self.assertTrue(ia['keysTrap']['inSheet'], 'focus stays in the sheet')
            self.assertTrue(ia['keysEsc'])
            self.assertTrue(ia['stepFwd'].endswith('13:45'), ia['stepFwd'])
            self.assertTrue(ia['stepBack'].endswith('13:40'), ia['stepBack'])
            self.assertEqual({'asOf': ia['stepBack'], 'sheet': False, 'path': '/notices', 'value': 'g]?'}, ia['typed'],
                             'no shortcut fires while typing')
            self.assertEqual('/alerts', ia['goto'], 'g then a goes to Alerts')

    def test_breadcrumbs_and_titles(self):
        for width, run in self.each():
            crumbs = run['ia']['crumbs']
            self.assertTrue(crumbs['first'], 'the crumbs open the page head')
            self.assertEqual('Breadcrumb', crumbs['label'])
            self.assertEqual([['A', 'Alerts', '/alerts', None], ['SPAN', 'Visayas price spike', None, 'page']], crumbs['parts'])
            self.assertEqual('Visayas price spike · Notices · InGRID', crumbs['title'])

    def test_the_command_bar_rests_as_a_pill_past_the_first_screen(self):
        for width, run in self.each():
            ia = run['ia']
            self.assertFalse(ia['cmdTop']['compact'], width)
            self.assertIsNotNone(ia['cmdTop']['bar'])
            scrolled = ia['cmdScrolled']
            self.assertTrue(scrolled['compact'], width)
            self.assertIsNone(scrolled['bar'], 'the full bar steps aside')
            pill, view = scrolled['pill'], scrolled['view']
            self.assertEqual('Search or ask Ingrid', scrolled['label'])
            self.assertLessEqual(view['width'] - pill['right'], 24, 'at the right edge')
            self.assertLessEqual(view['height'] - pill['bottom'], 24, 'at the bottom edge')
            self.assertGreaterEqual(view['width'] - pill['right'], 8)
            self.assertLess(pill['width'], 140, 'a small pill, out of the reading column')
            self.assertGreaterEqual(pill['height'], 32)
            self.assertFalse(ia['cmdSlash']['compact'], '"/" brings the bar back')
            self.assertTrue(ia['cmdSlash']['focused'])
            self.assertTrue(ia['cmdAfter']['compact'], 'and it steps aside again once left')
            self.assertFalse(ia['cmdPillClick']['compact'])
            self.assertTrue(ia['cmdPillClick']['focused'])
            self.assertFalse(ia['cmdBack']['compact'], 'the full bar at the top of the page')


if __name__ == '__main__':
    unittest.main()
