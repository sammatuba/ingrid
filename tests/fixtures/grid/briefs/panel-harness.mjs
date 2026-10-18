/* Run `src/grid/briefs.js`'s own click handling against the composed fixture, offline: no
   browser, no network, no library. The shim below implements exactly the DOM surface the module
   uses and throws on a selector it does not know, so a gap in the shim is a failure rather than a
   silent pass. It is an approximation of a browser, not a browser: it proves the panel's handlers
   are wired the way the code says, not that the panel looks right.

   It mounts the panel over the two composed files, then exercises the two things a handler bound
   per node gets wrong:
     - the chips persist across redraws, so repeated filtering and clock changes must not stack
       handlers: one click on a chip must draw the feed exactly once, however many redraws ran
       before it;
     - `setGrid` replaces the briefing paragraph, so an entity and the event link in the replaced
       paragraph must still reach the page's callbacks.

     node tests/fixtures/grid/briefs/panel-harness.mjs --module src/grid/briefs.js \
          --briefs <briefs.json> --findings <findings.json>

   Exit 0 with one JSON line `{"problems": [], ...}` when everything holds, exit 1 naming each
   problem otherwise. */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const problems = [];
const problem = (message) => problems.push(message);
const args = process.argv.slice(2);
const arg = (name, fallback) => {
  const at = args.lastIndexOf('--' + name);
  return at >= 0 && args[at + 1] !== undefined ? args[at + 1] : fallback;
};
const MODULE = path.resolve(arg('module', 'src/grid/briefs.js'));
const BRIEFS = path.resolve(arg('briefs', ''));
const FINDINGS = path.resolve(arg('findings', ''));

/* ---------- a small DOM ---------- */
const camel = (name) => name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
const escapeText = (text) => String(text).replace(/[&<>"]/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const attributes = (source) => {
  const attrs = [];
  const re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"/g;
  let found;
  while ((found = re.exec(source)) !== null) attrs.push([found[1], found[2]]);
  return attrs;
};

class Shim {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase();
    this.attrs = {};
    this.dataset = {};
    this.classes = new Set();
    this.children = [];
    this.parentNode = null;
    this.listeners = {};
    this.text = '';
    this.html = null;
    this.htmlSets = 0;               // how often innerHTML was assigned: a redraw counter
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name === 'class') this.classes = new Set(String(value).split(/\s+/).filter(Boolean));
    if (name.startsWith('data-')) this.dataset[camel(name.slice(5))] = String(value);
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  get className() { return [...this.classes].join(' '); }
  set className(value) { this.setAttribute('class', value); }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  get textContent() {
    return this.children.length ? this.children.map((child) => child.textContent).join('') : this.text;
  }
  set textContent(value) { this.text = String(value); this.children = []; this.html = null; }
  get innerHTML() { return this.html === null ? escapeText(this.text) : this.html; }
  set innerHTML(value) {
    this.htmlSets += 1;
    this.html = String(value);
    this.text = '';
    this.children = parse(this.html);
    for (const child of this.children) child.parentNode = this;
  }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  descendants() { return this.children.flatMap((child) => [child, ...child.descendants()]); }
  querySelectorAll(selector) { return this.descendants().filter((node) => matches(node, selector)); }
  querySelector(selector) {
    const found = this.querySelectorAll(selector);
    return found.length ? found[0] : null;
  }
  matches(selector) { return matches(this, selector); }
  closest(selector) {
    for (let node = this; node; node = node.parentNode) if (node.matches(selector)) return node;
    return null;
  }
  /* A click bubbles from the target through its ancestors, so a listener delegated on the panel
     is reached the way a browser reaches it. Each node's listeners are copied before they run:
     the DOM spec clones the listener list at dispatch, so a handler that binds another listener
     does not run it for the same click — it runs it for the *next* one. That is what makes
     stacked handlers observable over repeated clicks instead of a single runaway dispatch. */
  click() {
    const event = { target: this, defaultPrevented: false,
                    preventDefault() { event.defaultPrevented = true; } };
    for (let node = this; node; node = node.parentNode) {
      for (const fn of [...(node.listeners.click || [])]) fn(event);
    }
    return event;
  }
}

/* The one selector shape the module and this harness use: `tag`, `.class`, `tag.class`,
   `[attr]`, `tag[attr]`. Anything else throws, so an unsupported selector cannot pass. */
const SELECTOR = /^([a-zA-Z][a-zA-Z0-9]*)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$/;
function matches(node, selector) {
  const shape = SELECTOR.exec(selector);
  if (!shape) throw new Error('shim: unsupported selector ' + selector);
  if (shape[1] && node.tagName !== shape[1].toUpperCase()) return false;
  for (const name of shape[2].split('.').filter(Boolean)) if (!node.classes.has(name)) return false;
  for (const attr of shape[3].matchAll(/\[([^\]]+)\]/g)) if (!(attr[1] in node.attrs)) return false;
  return true;
}

const TAG = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*?)(\/?)>|([^<]+)/g;
function parse(html) {
  const root = new Shim('#root');
  const stack = [root];
  TAG.lastIndex = 0;
  let found;
  while ((found = TAG.exec(html)) !== null) {
    const [, close, tag, attrText, selfClose, text] = found;
    const parent = stack[stack.length - 1];
    if (text !== undefined) {
      const node = new Shim('#text');
      node.text = text;
      parent.appendChild(node);
      continue;
    }
    if (close) { if (stack.length > 1) stack.pop(); continue; }
    const node = new Shim(tag);
    for (const [name, value] of attributes(attrText)) node.setAttribute(name, value);
    parent.appendChild(node);
    if (!selfClose) stack.push(node);
  }
  return root.children;
}

globalThis.document = { createElement: (tag) => new Shim(tag) };
globalThis.window = {};
await import('file://' + MODULE);
const { mount } = globalThis.window.GridBriefs;

/* ---------- mount the panel over the composed fixture ---------- */
const data = { briefs: JSON.parse(readFileSync(BRIEFS, 'utf8')),
               findings: JSON.parse(readFileSync(FINDINGS, 'utf8')) };
const calls = [];
const links = {
  grid: 'CVIS', clock: '2026-09-21T13:55',
  figure: (ref) => calls.push('figure:' + ref),
  link: (id) => calls.push('link:' + id),
  message: (id) => calls.push('message:' + id),
  site: (code) => calls.push('site:' + code),
  event: (id) => calls.push('event:' + id),
};
const container = new Shim('div');
const controller = mount(container, data, links);
const panel = container.children[0];
if (!panel || !panel.classes.has('briefs')) problem('mount appended no .briefs panel');
const chips = panel.querySelector('.b-chips').querySelectorAll('button');
const list = panel.querySelector('.b-entries');
const count = panel.querySelector('.b-count');
const titleNode = panel.querySelector('.b-title');
if (chips.length !== 5) problem('the panel drew ' + chips.length + ' chips, expected 5');
const price = chips.find((chip) => chip.dataset.kind === 'price');
if (!price) problem('the panel drew no Prices chip');
const draws = () => list.htmlSets;

/* One chip click, one feed draw. */
let before = draws();
price.click();
if (draws() - before !== 1) {
  problem('one chip click drew the feed ' + (draws() - before) + ' times, expected 1');
}

/* The chips persist across redraws: after many kind changes and clock changes one click must
   still draw the feed exactly once. A handler bound per redraw would run once per redraw. */
controller.setKind('all');
controller.setKind('link');
controller.setKind('message');
controller.setClock('2026-09-21T13:40');
controller.setClock('2026-09-21T13:55');
controller.setKind('event');
controller.setKind('price');
before = draws();
price.click();
if (draws() - before !== 1) {
  problem('after kind and clock changes one chip click drew the feed ' + (draws() - before) +
          ' times, expected 1');
}
const pressed = chips.filter((chip) => chip.getAttribute('aria-pressed') === 'true');
if (pressed.length !== 1 || pressed[0].dataset.kind !== 'price') {
  problem('the chips carry ' + pressed.length + ' pressed states after one click, expected Prices alone');
}
const shownKinds = list.querySelectorAll('.b-entry').map((row) => row.dataset.kind);
if (!shownKinds.length || shownKinds.some((kind) => kind !== 'price')) {
  problem('the Prices chip left rows of kinds ' + JSON.stringify([...new Set(shownKinds)]));
}
if (!count.textContent.includes('findings')) problem('the caption was not drawn');

/* An entry's entity reaches the page's callback, once. */
const entryEntity = list.querySelectorAll('.ent')[0];
if (!entryEntity) problem('the feed drew no entry entity to click');
else {
  before = calls.length;
  entryEntity.click();
  if (calls.length - before !== 1) {
    problem('one entry entity click produced ' + (calls.length - before) + ' callbacks, expected 1');
  }
}

/* setGrid replaces the paragraph: its own entities and the event link must still work. */
for (const [grid, expected] of [['CLUZ', 'figure:CLUZ:demand'], ['CMIN', 'figure:CMIN:demand']]) {
  controller.setGrid(grid);
  const text = panel.querySelector('.b-text');
  const entity = text.querySelectorAll('.ent')[0];
  if (!entity) problem('the ' + grid + ' briefing carries no entity to click');
  else {
    before = calls.length;
    entity.click();
    if (calls.length - before !== 1) {
      problem('after setGrid(' + grid + ') one entity click produced ' + (calls.length - before) +
              ' callbacks, expected 1');
    } else if (calls[calls.length - 1] !== expected) {
      problem('after setGrid(' + grid + ') the entity click called ' + calls[calls.length - 1] +
              ', expected ' + expected);
    }
  }
  const anchor = text.querySelectorAll('a.b-event')[0];
  if (!anchor) problem('the ' + grid + ' briefing carries no event link to click');
  else {
    before = calls.length;
    const event = anchor.click();
    if (calls.length - before !== 1) {
      problem('after setGrid(' + grid + ') the event link produced ' + (calls.length - before) +
              ' callbacks, expected 1');
    } else if (calls[calls.length - 1] !== 'event:syn-bay-unit-2-trip') {
      problem('the event link called ' + calls[calls.length - 1] +
              ', expected event:syn-bay-unit-2-trip');
    }
    if (!event.defaultPrevented) problem('the panel did not take the event click for ' + grid);
  }
}

/* FRONT-1: what the panel says and how it arranges the rows — the closing brief's heading and
   the runs the Prices chip leaves (the fixture's five price findings of 13:55, the two Luzon
   cap rows of one family among them). This is read before the rework's synthetic rows below,
   so the composed fixture's own figures are reported unchanged. */
const runs = list.children.filter((row) => row.classes.has('b-group'));
const composed = { drawn: list.children.length,
                   findings: list.querySelectorAll('.b-entry').length,
                   groups: runs.length,
                   groupSizes: runs.map((row) => row.querySelectorAll('.b-entry').length) };

/* FRONT-1 rework, finding 2: a row that carries a review link is its own row, never folded
   behind a run's disclosure. The Messages chip holds the fixture's one such message. */
const message = chips.find((chip) => chip.dataset.kind === 'message');
message.click();
const topReview = list.children.filter((row) => row.classes.has('b-entry')
  && row.querySelectorAll('a.b-review').length);
const foldedReview = list.children.filter((row) => row.classes.has('b-group'))
  .flatMap((row) => row.querySelectorAll('a.b-review')).length;
if (topReview.length !== 1 || foldedReview !== 0) {
  problem('the review row is not drawn alone: ' + topReview.length + ' top-level, ' +
          foldedReview + ' folded behind a run');
}

/* FRONT-1 rework, finding 1: the run rule breaks. Synthetic rows go into the mounted data in
   memory — the composed files are untouched — at their chronological places, so the feed's
   newest-first order still holds. Rows 1 and 2 are 77 minutes apart and must be two rows; rows
   2 and 3 are five minutes apart and must be one run. On SYNY, a price row of another family
   stands between the two cap rows, so they stay apart too. */
const synthetic = (grid, rule, t) => ({
  kind: 'price', grid, grid_name: 'Synthetic test grid', rule, t,
  headline: 'Synthetic ' + rule + ' row at ' + t.slice(11) + ' with 1.',
  why: 'Synthetic ' + rule + ' row at ' + t.slice(11) + '.',
  entity: { type: 'grid', code: grid, name: 'Synthetic test grid', ref: grid + ':price' },
  review: null,
});
const addRow = (row) => {
  const rows = data.findings.findings;
  const at = rows.findIndex((x) => x.t.replace('T', ' ') > row.t.replace('T', ' '));
  rows.splice(at < 0 ? rows.length : at, 0, row);
};
for (const [grid, rule, t] of [
  ['SYNX', 'F1', '2026-09-21T13:47'], ['SYNX', 'F1', '2026-09-21T12:30'],
  ['SYNX', 'F1', '2026-09-21T12:25'], ['SYNY', 'F1', '2026-09-21T12:00'],
  ['SYNY', 'F5', '2026-09-21T11:55'], ['SYNY', 'F1', '2026-09-21T11:50'],
]) addRow(synthetic(grid, rule, t));
price.click();
controller.setClock('2026-09-21T13:55');
const rowsOf = (grid) => list.children.filter((row) => row.dataset.grid === grid);
const [far, near] = rowsOf('SYNX');
if (!far || !near || rowsOf('SYNX').length !== 2) {
  problem('the gapped rows drew ' + rowsOf('SYNX').length + ' rows, expected 2');
} else {
  if (!far.classes.has('b-entry')) problem('the row 77 minutes from the next is not its own row');
  if (!near.classes.has('b-group')) problem('the rows five minutes apart are not one run');
  else if (near.querySelectorAll('.b-entry').length !== 2) {
    problem('the near run holds ' + near.querySelectorAll('.b-entry').length + ' rows, expected 2');
  }
}
const interrupted = rowsOf('SYNY');
if (interrupted.length !== 3 || interrupted.some((row) => row.classes.has('b-group'))) {
  problem('a row of another family between two cap rows did not break the run: ' +
          interrupted.length + ' rows');
}

/* FRONT-1 rework, finding 4: a run the reader opened stays open across a redraw. */
const openGroup = list.children.find((row) => row.classes.has('b-group')
  && row.dataset.run === 'price|CLUZ|cap');
let reopened = false;
if (!openGroup) problem('the composed fixture draws no Luzon cap run to open');
else {
  openGroup.querySelector('details').setAttribute('open', '');
  controller.setClock('2026-09-21T13:55');
  const again = list.children.find((row) => row.classes.has('b-group')
    && row.dataset.run === 'price|CLUZ|cap');
  reopened = Boolean(again && again.querySelector('details').getAttribute('open') !== null);
  if (!reopened) problem('an open run folded again on the next redraw');
}

console.log(JSON.stringify({ problems, chips: chips.map((chip) => chip.dataset.kind),
                             feedDraws: draws(), callbacks: calls,
                             briefTitle: titleNode ? titleNode.textContent : '',
                             drawn: composed.drawn, findings: composed.findings,
                             groups: composed.groups, groupSizes: composed.groupSizes,
                             reviewAlone: topReview.length === 1 && foldedReview === 0,
                             gapped: { far: Boolean(far), near: Boolean(near) && near.classes.has('b-group'),
                                       interrupted: interrupted.length },
                             reopened }));
process.exit(problems.length ? 1 : 0);
