"""DM-5 round 2 (review of the shared inbox, PERF-6): moving the replay clock back never shows an
alert read at a later time.

Two paths the review found, each driven through the real script in node with a minimal page:
the dashboard's alert list (`src/grid/dash-alerts.js`) when an answer read at 15:00 lands after
the clock moved back to 13:00 (a delayed response) and when the list drawn at 15:00 is on the
page as the clock moves back; and the alerts page's rule (`AlertsLogic.readFits` in
`src/grid/alerts.js`), which its list applies on every clock move and to every late answer.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')

# A minimal page: elements with children and text, the shell's clock, inbox and two signals.
DASH_HARNESS = r"""
const fs = require('fs'); const vm = require('vm');
function node(tag) {
  return { tag, children: [], className: '', href: '', _text: '',
    set textContent(v) { this.children = []; this._text = String(v); },
    get textContent() { return this._text + this.children.map((c) => c.textContent).join(' '); },
    appendChild(c) { this.children.push(c); return c; }, setAttribute() {}, addEventListener() {} };
}
const ids = {}; for (const id of ['da-list', 'da-count', 'da-more', 'da-filters']) ids[id] = node('div');
const document = { readyState: 'complete', getElementById: (id) => ids[id] || null,
  createElement: (t) => node(t), querySelectorAll: () => [], addEventListener() {} };
let clock = '2026-09-21T15:00'; const asOf = []; const due = []; let pending = null;
const GNShell = { asOf: () => clock, onAsOf: (fn) => asOf.push(fn), onInboxDue: (fn) => due.push(fn), onUser() {},
  inbox: (at) => new Promise((resolve) => { pending = { at, resolve }; }) };
const ANSWER = { groups: [{ alerts: [{ key: 'k1', region: 'CVIS', direction: 'spike', severity: 'extreme',
  first: '2026-09-21T14:00', last: '2026-09-21T15:00', interval_manila: '2026-09-21T14:00',
  price_php_mwh: 99999, peak_php_mwh: 99999, main_driver: 'LATER PEAK', href: '/alerts?alert=k1' }] }] };
const window = { GNShell }; const ctx = vm.createContext({ window, document, console, setTimeout, clearTimeout });
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const tick = () => new Promise((r) => setTimeout(r, 0));
const list = () => ids['da-list'].textContent;
(async () => {
  const out = {};
  // 1. a delayed response: read at 15:00, the clock moves back to 13:00, then the answer lands.
  await tick();
  out.first_request_at = pending && pending.at;
  clock = '2026-09-21T13:00'; asOf.forEach((fn) => fn(clock));
  pending.resolve(ANSWER); await tick(); await tick();
  out.delayed = list();
  // 2. the list drawn at 15:00 is on the page as the clock moves back.
  clock = '2026-09-21T15:00'; due.forEach((fn) => fn()); await tick();
  pending.resolve(ANSWER); await tick(); await tick();
  out.drawn_at_15 = list();
  clock = '2026-09-21T13:00'; asOf.forEach((fn) => fn(clock)); await tick();
  out.after_rewind = list();
  // 3. moving forward keeps an earlier read: 13:00 read, clock to 13:30.
  due.forEach((fn) => fn()); await tick();
  const early = { groups: [] }; pending.resolve(early); await tick(); await tick();
  clock = '2026-09-21T13:30'; asOf.forEach((fn) => fn(clock)); await tick();
  out.forward = list();
  process.stdout.write(JSON.stringify(out));
})();
"""

LOGIC_HARNESS = r"""
const L = require(process.argv[1]);
const cases = { same: ['2026-09-21T13:05', '2026-09-21T13:05'], earlier: ['2026-09-21T12:40', '2026-09-21T13:05'],
  later: ['2026-09-21T15:00', '2026-09-21T13:05'], never: [null, '2026-09-21T13:05'], no_clock: ['2026-09-21T15:00', null] };
const out = {}; for (const [k, [a, b]] of Object.entries(cases)) out[k] = L.readFits(a, b);
process.stdout.write(JSON.stringify(out));
"""


def node_run(script, path):
    run = subprocess.run([NODE, '-e', script, str(path)], capture_output=True, text=True, cwd=ROOT, timeout=60)
    if run.returncode:
        raise AssertionError(run.stderr[-1500:])
    return json.loads(run.stdout)


@unittest.skipUnless(NODE, 'the page scripts run on node; this interpreter has none')
class TheDashboardList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = node_run(DASH_HARNESS, ROOT / 'src' / 'grid' / 'dash-alerts.js')

    def test_the_first_read_is_at_the_clock(self):
        self.assertEqual('2026-09-21T15:00', self.out['first_request_at'])

    def test_a_late_answer_after_a_rewind_is_never_drawn(self):
        self.assertNotIn('99,999', self.out['delayed'])
        self.assertNotIn('LATER PEAK', self.out['delayed'])

    def test_the_list_drawn_later_is_taken_down_when_the_clock_moves_back(self):
        self.assertIn('LATER PEAK', self.out['drawn_at_15'], 'the harness draws the alert at 15:00')
        self.assertNotIn('LATER PEAK', self.out['after_rewind'])
        self.assertIn('Reading the alert inbox', self.out['after_rewind'])

    def test_an_earlier_read_stays_when_the_clock_moves_forward(self):
        self.assertNotIn('Reading the alert inbox', self.out['forward'])


@unittest.skipUnless(NODE, 'the page scripts run on node; this interpreter has none')
class TheAlertsPageRule(unittest.TestCase):
    def test_an_answer_read_later_than_the_clock_does_not_fit(self):
        out = node_run(LOGIC_HARNESS, ROOT / 'src' / 'grid' / 'alerts.js')
        self.assertEqual({'same': True, 'earlier': True, 'later': False, 'never': False, 'no_clock': True}, out)

    def test_the_list_applies_it_on_every_clock_move_and_to_every_late_answer(self):
        js = (ROOT / 'src' / 'grid' / 'alerts.js').read_text(encoding='utf-8')
        self.assertIn('shell.onAsOf(inboxClock)', js)
        self.assertIn("if (list.rowsAt && !L.readFits(list.rowsAt, at)) withholdInbox();", js)
        self.assertIn("if (!L.readFits(at, asOfNow())) { withholdInbox(); return; }", js)
        self.assertIn("if (state.inboxPendingAt && !L.readFits(state.inboxPendingAt, at)) {", js)


if __name__ == '__main__':
    unittest.main()
