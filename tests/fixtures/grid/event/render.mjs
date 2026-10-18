/* Run the event page's own scripts (src/grid/event-api.js and the design file src/grid/event.js)
   against the recorded flow and print what the page rendered, as one JSON object on stdout.
   Offline: no browser, no network, no library, nothing written.

   The shim below implements exactly the DOM surface event.js uses and throws on anything else,
   so a gap in the shim is a failure rather than a silent pass. It is an approximation of a real
   browser: it proves the page executes, records a decision through its own form and fills the
   history card from what the adapter returned — including the failure that must be visible
   there rather than hidden. The real browser check is the orchestrator's walkthrough.

     node tests/fixtures/grid/event/render.mjs --root .
       [--fixture tests/fixtures/grid/event] [--event <id>] [--stamp <16 hex>]
       [--history-failure unauthorized|storage|malformed]
       [--refresh-failure storage|transport|malformed]
       [--decision-failure] [--local-preview] [--session-no-case] [--legacy-cards]

   Without --history-failure the history route answers the recorded history (one entry after the
   recorded first decision); with it, the route answers the named failure and the page must show
   the route's code and sentence in the history card. With --refresh-failure, the read that
   follows the saved decision fails instead, and the page must keep the saved receipt in its
   status line with the failure named beside it — the decision itself did save. DESK-1: the
   fixture directory's `outlook.json` (when it has one) answers the page's
   `/grid-data/outlook/<id>.json` read, and the report carries the register-and-price-outlook
   card as the page drew it. DESK-4: the same file may carry an `impact` key; the report's
   `impact` block is the page's four impact sentences, or the card's hidden state when the
   view has no impact record. O5: the fixture directory's `ontology.json` (when it has one)
   answers `/grid-data/ontology/<id>.json`, and the report carries the likely-drivers card.
   DESK-7: the report also carries the desk line as the page drew it (the AI reader's card and
   the person's card), the status line while the save is waiting (`saving`, read before the
   adapter answers), the `<details>` disclosure each record element sits under (`folds`), the
   figure tiles, the chart's own text labels, and the history heading. With
   `--decision-failure` the review route refuses the decision, so the page's refusal line and
   its retry sentence are read; with `--local-preview` the session route is absent and with
   `--session-no-case` it answers a session that carries no event case, so the page's two
   other refusal branches (the local copy and a session with nothing to file against) are
   read the same way.

   The live page no longer carries the cards event.js drew before the redesign (the desk line,
   the review rail, the advisory and timeline, the market chart, the rules card, the assumption,
   the price outlook, the impact card, the judgment, the decision form and the history).
   `--legacy-cards` appends that markup from tests/fixtures/grid/event/legacy-cards.html to the
   parsed page, so the renderer tests keep exercising event.js's own code for them. Without the
   flag the page is the live one: every report field whose element is gone reads null, and the
   report says which of those ids the page carries (`present`). */
import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import vm from 'node:vm';

const errors = [];
function fail(message) {
  console.log(JSON.stringify({ok: false, error: String(message), errors}));
  process.exit(1);
}

/* ---------- arguments ---------- */
const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const FIXTURE = path.resolve(arg('fixture', path.join(ROOT, 'tests/fixtures/grid/event')));
const FAILURE = arg('history-failure', '');
const REFRESH = arg('refresh-failure', '');
const DECISION_FAILURE = argv.includes('--decision-failure');
const LOCAL_PREVIEW = argv.includes('--local-preview');
const SESSION_NO_CASE = argv.includes('--session-no-case');
const LEGACY = argv.includes('--legacy-cards');
const WIDTH = 1280;
/* With --stamp the shim's page is the one the application serves: the build stamp is written
   into the `nowcast-build` meta element, so the adapter reads the baked view model under the
   versioned prefix. Without it the source page's token stays, the adapter sees no stamp, and
   the unversioned name is read — the recorded flow's own path. */
const STAMP = arg('stamp', '');

const view = JSON.parse(readFileSync(path.join(FIXTURE, 'view.json'), 'utf8'));
/* DESK-1: the event page's register-and-price-outlook view, built by the real builder for this
   event (`tests/fixtures/grid/event/build.py`). A fixture directory without one (the two rules
   views) answers 404, so the page's section stays off — the unconnected case, exactly as a
   bake with no archive shows it. */
const OUTLOOK_PATH = path.join(FIXTURE, 'outlook.json');
const outlook = existsSync(OUTLOOK_PATH) ? JSON.parse(readFileSync(OUTLOOK_PATH, 'utf8')) : null;
/* O5: the likely-drivers card's baked file (scripts/ontology/bake_panel.py); none in the committed
   fixtures, so the card stays off unless a test writes one beside the view. */
const ONTOLOGY_PATH = path.join(FIXTURE, 'ontology.json');
const ontology = existsSync(ONTOLOGY_PATH) ? JSON.parse(readFileSync(ONTOLOGY_PATH, 'utf8')) : null;
/* CORP-5: a view-only fixture (an event whose decisions are prepared in its case pack, not
   filed through the judge's routes) carries no recorded decision flow; the page is rendered
   and the rules block is reported, and no decision is driven. The PEDC fixture keeps its
   recorded flow, so every assertion about the form below still runs against it. */
const FLOW_PATH = path.join(FIXTURE, 'flow.json');
const flow = existsSync(FLOW_PATH) ? JSON.parse(readFileSync(FLOW_PATH, 'utf8')) : null;
const eventId = arg('event', view.id);
const step = flow ? flow.decisions[0] : null;

/* ---------- a small DOM, built from the page's own HTML ---------- */
// A browser ignores comments; the tokeniser below must too, or prose inside one that names a
// file as `<id>.json` would be read as an element and break the tree the page's elements hang
// from (DESK-7 walks that tree to read the records' disclosures).
const decomment = (source) => String(source).replace(/<!--[\s\S]*?-->/g, '');
const LIVE = decomment(readFileSync(path.join(ROOT, 'src/grid/event.html'), 'utf8'));
const PAGE = LEGACY
  ? LIVE.replace('</main>', decomment(readFileSync(path.join(ROOT, 'tests/fixtures/grid/event/legacy-cards.html'), 'utf8')) + '</main>')
  : LIVE;

function attributes(source) {
  const attrs = {};
  const re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"/g;
  let found;
  while ((found = re.exec(source)) !== null) attrs[found[1]] = found[2];
  return attrs;
}
const camel = (name) => name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
const escapeText = (text) => String(text).replace(/[&<>"]/g, (c) =>
  ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
// The tags the page's HTML leaves unclosed on purpose (HTML void elements).
const VOID = new Set(['meta', 'link', 'input', 'br', 'img', 'hr', 'source']);

/* The page writes its own HTML into elements (`innerHTML`). A browser parses that into nodes,
   and the page binds listeners to those nodes — the rules card's cutoff tabs are the clearest
   case, and a shim that kept the string could never reach the second state. The fragment is
   tokenised the same way the page itself was: real child nodes, each with its attributes and
   its text, registered in the document's own node list so the page's selectors find them. */
function parseFragment(parent, source) {
  const stack = [];
  let at = 0, found;
  tagRe.lastIndex = 0;
  while ((found = tagRe.exec(source)) !== null) {
    if (found.index > at) appendText(stack[stack.length - 1] || parent, source.slice(at, found.index));
    at = tagRe.lastIndex;
    const [, closing, tag, attrsSource] = found;
    if (closing) { stack.pop(); continue; }
    const node = new Shim(tag, attributes(attrsSource));
    (stack[stack.length - 1] || parent).appendChild(node);
    all.push(node);
    if (node.getAttribute('id')) byId.set(node.getAttribute('id'), node);
    if (!attrsSource.trimEnd().endsWith('/') && !VOID.has(tag)) stack.push(node);
  }
  if (at < source.length) appendText(stack[stack.length - 1] || parent, source.slice(at));
}
function appendText(parent, text) {
  // The page's own top-level tags have no parent in the static parse; their gap text is dropped.
  if (parent && text) parent.textContent += text;
}

class Shim {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = {...attrs};
    this.children = [];
    this.parentNode = null;
    this.listeners = {};
    this.dataset = {};
    this.classes = new Set();
    this.text = '';
    this.html = null;
    this.hidden = false;
    this.value = attrs.value === undefined ? '' : String(attrs.value);   // a form control's value
    this.checked = false;
    this.disabled = false;
    this.href = '';
    this.rect = {left: 0, top: 0, width: WIDTH, height: 0};
    for (const [key, value] of Object.entries(attrs)) this.setAttribute(key, value);
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name === 'class') this.classes = new Set(String(value).split(/\s+/).filter(Boolean));
    if (name.startsWith('data-')) this.dataset[camel(name.slice(5))] = String(value);
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  get textContent() { return this.text; }
  set textContent(value) { this.text = String(value); }
  get innerHTML() { return this.html === null ? escapeText(this.text) : this.html; }
  set innerHTML(value) { this.html = String(value); this.children = []; parseFragment(this, this.html); }
  get className() { return [...this.classes].join(' '); }
  set className(value) { this.classes = new Set(String(value).split(/\s+/).filter(Boolean)); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  /* Listeners are snapshotted at dispatch: a handler that binds more listeners on the same
     node must not loop forever through the array it is iterating. */
  dispatch(type, event = {}) { for (const fn of [...(this.listeners[type] || [])]) fn(event); }
  querySelectorAll(selector) { return findAll(selector); }
  querySelector(selector) {
    // The page reaches two things through an element query: the checked decision radio and
    // the `.ev` main column it replaces when the event cannot be loaded.
    if (selector === 'input[name="d"]:checked') {
      return all.find((node) => node.tagName === 'INPUT' && node.attrs.name === 'd' && node.checked) || null;
    }
    throw new Error('shim: unsupported selector ' + selector);
  }
  reset() {
    for (const node of all) {
      if (node.tagName === 'INPUT') { node.checked = false; node.value = ''; }
      if (node.tagName === 'TEXTAREA') node.value = '';
    }
  }
  getBoundingClientRect() { return this.rect; }
}

const byId = new Map();
const all = [];
const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*?)>/g;
const stack = [];
let match, at = 0;
while ((match = tagRe.exec(PAGE)) !== null) {
  /* The text between tags is the element's own, exactly as a browser parses it: the summary of
     a disclosure and the heading of a card carry their words here (DESK-7 reads them). */
  if (match.index > at) appendText(stack[stack.length - 1] || null, PAGE.slice(at, match.index));
  at = tagRe.lastIndex;
  const [, closing, tag, attrsSource] = match;
  if (closing) { stack.pop(); continue; }
  const selfClosing = attrsSource.trimEnd().endsWith('/');
  const node = new Shim(tag, attributes(attrsSource));
  const parent = stack[stack.length - 1];
  if (parent) parent.appendChild(node);
  all.push(node);
  if (node.getAttribute('id')) byId.set(node.getAttribute('id'), node);
  if (!selfClosing && !VOID.has(tag)) stack.push(node);
}
// The probes table's rows live in an implicit tbody the page reaches as `tBodies[0]`.
for (const table of all.filter((node) => node.tagName === 'TABLE')) table.tBodies = [new Shim('tbody')];
if (STAMP) {
  const meta = byId.get('nowcast-build');
  if (!meta) fail('the page carries no nowcast-build meta element for the stamp');
  meta.attrs.content = STAMP;
}

const findAll = (selector) => {
  if (selector === '[data-step]') return all.filter((node) => 'step' in node.dataset);
  if (/^\.[a-zA-Z][-\w]*$/.test(selector)) return all.filter((node) => node.classes.has(selector.slice(1)));
  throw new Error('shim: unsupported selector ' + selector);
};

const document = {
  title: (PAGE.match(/<title>([^<]*)<\/title>/) || [null, ''])[1],
  readyState: 'complete',   // main() runs as soon as the page's script does
  getElementById: (id) => byId.get(id) || null,
  createElementNS: (_ns, tag) => new Shim(tag),
  querySelectorAll: (selector) => findAll(selector),
  querySelector: (selector) => findAll(selector)[0] || null,
  addEventListener: () => {},
};

/* ---------- the recorded flow, with the one route the scenario changes ---------- */
function historyFailure() {
  if (FAILURE === 'unauthorized') return {ok: false, status: 401, json: async () => ({code: 'UNAUTHENTICATED'})};
  if (FAILURE === 'storage') return {ok: false, status: 503, json: async () => ({code: 'STORAGE_UNAVAILABLE'})};
  if (FAILURE === 'malformed') {
    return {ok: true, status: 200, json: async () => { throw new Error('the answer was not JSON'); }};
  }
  if (FAILURE) fail('unknown --history-failure ' + FAILURE);
  return null;
}

/* The read that follows the saved decision: the failures the review named, or null for the
   recorded acceptance. `transport` throws the way a dropped connection does. */
function refreshAnswer() {
  if (REFRESH === 'storage') return {ok: false, status: 503, json: async () => ({code: 'STORAGE_UNAVAILABLE'})};
  if (REFRESH === 'transport') return 'transport';
  if (REFRESH === 'malformed') {
    return {ok: true, status: 200, json: async () => { throw new Error('the answer was not JSON'); }};
  }
  if (REFRESH === 'no_instant') return {ok: true, status: 200, json: async () => ({})};
  if (REFRESH) fail('unknown --refresh-failure ' + REFRESH);
  return null;
}

const calls = [];
const record = (method, url, options) => calls.push({method, path: String(url),
  body: options.body ? JSON.parse(options.body) : null});
function transport(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const target = String(url);
  record(method, url, options);
  const ok = (status, body) => Promise.resolve({ok: status < 400, status, json: async () => body});
  /* DESK-7: the two refusals the adapter makes before a decision is posted. A deployment
     without the session route answers 404 and the adapter returns its local-copy sentence; a
     session with no event case answers 200 and an empty body, and the adapter says the
     decision was not recorded. */
  if (target === '/demo/session') {
    if (LOCAL_PREVIEW) return Promise.resolve({ok: false, status: 404, json: async () => ({})});
    if (SESSION_NO_CASE) return ok(200, {});
    return ok(200, flow ? flow.session : {id_token: 'stub', tenant: 'demo-judge'});
  }
  // The versioned and unversioned names read the same fixture file; the report's `calls` say
  // which one the adapter asked for, so the stamp's effect is visible and not assumed.
  if (/^\/grid-data\/(?:[0-9a-f]{16}\/)?events\//.test(target)) {
    return target.endsWith('/events/' + eventId + '.json') ? ok(200, view) : ok(404, null);
  }
  // DESK-1: the register-and-price-outlook view, from the same fixture directory; a directory
  // without one (the rules views) answers 404 and the page shows nothing for the section.
  if (/^\/grid-data\/(?:[0-9a-f]{16}\/)?outlook\//.test(target)) {
    return outlook && target.endsWith('/outlook/' + eventId + '.json')
      ? ok(200, outlook) : ok(404, null);
  }
  if (/^\/grid-data\/(?:[0-9a-f]{16}\/)?ontology\//.test(target)) {
    return ontology && target.endsWith('/ontology/' + eventId + '.json')
      ? ok(200, ontology) : ok(404, null);
  }
  if (method === 'GET' && target.endsWith('/history')) {
    // The route answers the history *after* the decision: the recorded flow's first entry.
    const failure = historyFailure();
    return failure ? Promise.resolve(failure) : ok(200, flow ? flow.history.slice(0, 1) : []);
  }
  // The one prepare call answers the heads, the snapshot and the compiled task (PERF-3).
  if (target.endsWith('/prepare')) {
    return ok(200, {heads: step.heads, snapshot: step.snapshot, task: step.compile});
  }
  if (target.endsWith('/reviews')) {
    // DESK-7: the refusal the page's status line must show with a plain retry sentence.
    if (DECISION_FAILURE) return Promise.resolve({ok: false, status: 409, json: async () => ({code: 'STALE_HEAD'})});
    return ok(200, step.receipt);
  }
  if (target.endsWith('/read')) {
    const failure = refreshAnswer();
    if (failure === 'transport') throw new Error('the connection was dropped');
    return failure || ok(200, step.acceptance);
  }
  return ok(500, null);
}

/* ---------- run the page's own scripts ---------- */
const sandbox = {
  document,
  location: {pathname: '/event/' + encodeURIComponent(eventId), hash: ''},
  fetch: transport,
  addEventListener: () => {},          // the page's resize listener; there is no layout here
  /* DESK-7: the save flow counts the seconds it waits; the shim supplies the same timers a
     browser does, and the page clears its interval when the answer arrives. */
  setTimeout, clearTimeout, setInterval, clearInterval,
  console: {log: () => {}, warn: () => {}, error: (m) => errors.push(String(m))},
};
sandbox.window = sandbox;   // `window.EventAPI` is the global the design file reads
try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/event-api.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/event-api.js'});
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/event.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/event.js'});
} catch (error) {
  fail('the page script threw: ' + (error && error.stack ? error.stack : error));
}

/* ---------- what it rendered ---------- */
const content = (id) => {
  const node = byId.get(id);
  if (!node) return null;
  return {text: node.textContent, html: node.innerHTML, hidden: node.hidden};
};
// The live page has no element for most of the old cards: those fields read null.
const text = (id) => (byId.get(id) ? byId.get(id).textContent : null);
const html = (id) => (byId.get(id) ? byId.get(id).innerHTML : null);
const hidden = (id) => (byId.get(id) ? byId.get(id).hidden : null);
const kids = (id) => (byId.get(id) ? byId.get(id).children : []);
const settle = async (done) => {
  for (let turn = 0; turn < 500 && !done(); turn += 1) await new Promise((resolve) => setTimeout(resolve, 0));
  if (!done()) fail('the page never finished what it was doing');
};
// renderHead fills the title from the view model; the page's own placeholder is the em dash.
await settle(() => content('ev-title').text !== '' && content('ev-title').text !== '—');
const afterLoad = {history: content('history'), list: content('hist-list'),
  status: text('dc-status'), rail: kids('rail').map((li) => li.className),
  person: text('dp-line'), ask: html('dl-ask'),
  history_title: text('hist-title')};

/* CORP-5: the rules card, as the page rendered it: whether the card is shown, its tabs, each
   cutoff state's own HTML (reached by clicking the page's own tab, as a visitor does), and the
   decision form's own state (off for a view-only event). The advisory card and the timeline are
   read in the same state walk: the selected cutoff governs them too, so a passage the state
   does not place must be absent from what they drew. */
const stateOf = () => ({
  cut: (String(html('ru-state') || '').match(/<p class="ru-cut">([^<]*)</) || [null, null])[1],
  html: html('ru-state'),
  statuses: [...String(html('ru-state') || '').matchAll(/ru-chip (\w+)">([^<]*)</g)]
    .map((entry) => ({status: entry[1], text: entry[2]})),
  quote: html('adv-quote'),
  timeline: html('timeline'),
});
const rules = {
  hidden: hidden('rules'),
  note: text('ru-note'),
  tab_count: (String(html('ru-tabs') || '').match(/<button/g) || []).length,
  tab_labels: [...String(html('ru-tabs') || '').matchAll(/data-ru="\d+" aria-pressed="(true|false)">([^<]*)</g)]
    .map((entry) => ({pressed: entry[1], text: entry[2]})),
  state: html('ru-state'),
  cut: (String(html('ru-state') || '').match(/<p class="ru-cut">([^<]*)</) || [null, null])[1],
  statuses: [...String(html('ru-state') || '').matchAll(/ru-chip (\w+)">([^<]*)</g)]
    .map((entry) => ({status: entry[1], text: entry[2]})),
  states: [],
};
rules.states.push(stateOf());
const ruleTabs = byId.get('ru-tabs') ? byId.get('ru-tabs').children : [];
for (let index = 1; index < ruleTabs.length; index += 1) {
  ruleTabs[index].dispatch('click', {});
  rules.states.push(stateOf());
}
const decisionForm = {hidden: hidden('dc-form'), note: text('dc-note'), noteHidden: hidden('dc-note')};
/* The caption's limits list is filled from the view and stays closed until the button opens it;
   its first line is where a labelled fixture says that it is one, and its last is where DESK-1's
   archive disclaimer lands when the price-outlook section is drawn. */
const limitItems = [...content('limits').html.matchAll(/<li>([^<]*)</g)].map((entry) => entry[1]);
const limits = {count: limitItems.length, first: limitItems[0] || '',
                last: limitItems[limitItems.length - 1] || ''};
/* DESK-1: the register-and-price-outlook card, as the page rendered it: off the page when the
   bake carries no archive or the fixture has no view, drawn from the view's own records
   otherwise. Nothing here is re-derived; the report carries what the page wrote. */
const priceOutlook = {hidden: hidden('price-outlook'), plain: text('po-plain'),
                      summary: text('po-summary'),
                      chain: text('po-chain'), html: html('po-list')};
/* DESK-4: the portfolio impact card, as the page rendered it: off the page unless the baked
   view carries an `impact` key, otherwise its four sentences in the order they are stated.
   The report carries the page's own text; nothing here is re-derived. */
const impactCard = content('impact');
const impact = {hidden: impactCard ? impactCard.hidden : true,
                plain: content('im-plain') ? content('im-plain').text : '',
                line: content('im-line') ? content('im-line').text : '',
                counts: content('im-counts') ? content('im-counts').text : '',
                label: content('im-label') ? content('im-label').text : '',
                unit: content('im-unit') ? content('im-unit').text : ''};
/* O5: the likely-drivers card as drawn, then with each mode tab clicked in turn. */
/* The live page no longer carries it (its place is "What stood out, ranked"); only the
   legacy-cards fixture does, so the report says absent rather than failing. */
const dvCard = content('drivers');
const dvGet = (id, k) => (content(id) ? content(id)[k] : '');
const drivers = {present: !!dvCard, hidden: dvCard ? dvCard.hidden : true, heading: dvGet('dv-heading', 'text'),
                 summary: dvGet('dv-summary', 'html'), paragraph: dvGet('dv-para', 'html'),
                 source: dvGet('dv-source', 'text'), modes: []};
const dvTabs = byId.get('dv-tabs') ? byId.get('dv-tabs').children : [];
for (const tab of dvTabs) {
  tab.dispatch('click', {});
  drivers.modes.push({mode: tab.dataset.dv, html: content('dv-state').html});
}
if (dvTabs.length) dvTabs[0].dispatch('click', {});
let saving = '';
if (flow && byId.get('dc-form')) {
  /* The judge picks Retain, gives the recorded reason and submits: the page's own form handler
     runs the adapter and the rail and history card follow. The status line is read once,
     synchronously, before the adapter answers: that is the waiting text the page shows. */
  all.find((node) => node.tagName === 'INPUT' && node.attrs.name === 'd' && node.attrs.value === 'retain').checked = true;
  byId.get('dc-reason').value = step.choice.reason;
  byId.get('dc-form').dispatch('submit', {preventDefault: () => {}});
  saving = content('dc-status').text;
  await settle(() => !/^Saving/.test(content('dc-status').text));
}

/* DESK-7: the desk line as the page drew it, and the disclosure every record element sits
   under. `foldedUnder` walks the element's ancestors to the nearest <details> and answers that
   disclosure's summary text (null where the element sits outside one). */
const foldedUnder = (id) => {
  let node = byId.get(id);
  while (node) {
    if (node.tagName === 'DETAILS') {
      const summary = node.children.find((child) => child.tagName === 'SUMMARY');
      return summary ? summary.textContent : '';
    }
    node = node.parentNode;
  }
  return null;
};
const folds = {outlook: foldedUnder('po-list'), impact: foldedUnder('im-line'),
               judgment: foldedUnder('jd-receipt')};
/* COPY-2: the page's text outside every disclosure and hidden element, as a stranger reads the
   first screen; the word-list tests check it for repository words. */
const plainOutsideFolds = () => {
  const skip = new Set(['DETAILS', 'SCRIPT', 'STYLE', 'TEMPLATE', 'HEAD', 'TITLE']);
  let out = '';
  const walk = (node) => {
    if (!node || skip.has(node.tagName) || node.hidden) return;
    if (node.text) out += ' ' + node.text;
    for (const child of node.children) walk(child);
  };
  for (const node of all) if (!node.parentNode) walk(node);
  return out.replace(/\s+/g, ' ').trim();
};
/* The desk line's cards (DESK-7) are off the ericka-desk event page; an absent part reads as null. */
const part = (id, k) => (content(id) ? content(id)[k] : null);
const desk = {
  ai: {by: part('dl-by', 'text'), run: part('dl-run', 'text'), what: part('dl-what', 'text'),
       label: part('dl-label', 'text'), rule: part('dl-rule', 'text'),
       proposal: part('dl-proposal', 'text'),
       /* The readings line sits on the desk line when the legacy cards are appended, and on the
          decision region's step 1 on the live page; the report reads whichever is present. */
       readings: part('dl-readings', 'text') !== null ? part('dl-readings', 'text') : part('ev-ai-readings', 'text'),
       readings_fold: byId.has('dl-readings-list') ? foldedUnder('dl-readings-list')
         : byId.has('ev-ai-readings-list') ? foldedUnder('ev-ai-readings-list') : '',
       rule_fold_hidden: !!(byId.get('dl-rule-fold') && byId.get('dl-rule-fold').hidden),
       readings_hidden: byId.has('dl-readings-fold') ? !!byId.get('dl-readings-fold').hidden
         : !!(byId.get('ev-ai-readings-fold') && byId.get('ev-ai-readings-fold').hidden),
       readings_records: part('dl-readings-list', 'html') !== null ? part('dl-readings-list', 'html') : part('ev-ai-readings-list', 'html'),
       you: part('dl-you', 'html'),
       ask: part('dl-ask', 'html')},
  person: {line: part('dp-line', 'text'), receipt: part('dp-receipt', 'text')},
  history_title: part('hist-title', 'text'),
};
const tiles = html('mk-figs');
/* The old cards' ids, and which of them the page carries: none on the live page. */
const OLD_IDS = ['desk-ai', 'desk-person', 'rail', 'adv-quote', 'timeline', 'cutoff', 'mk-card', 'mk-chart',
  'rules', 'as-value', 'price-outlook', 'impact', 'jd-table', 'decision', 'dc-form', 'history', 'drivers'];
const present = OLD_IDS.filter((id) => byId.has(id));
const chart = {labels: (byId.get('mk-chart') ? byId.get('mk-chart').children : [])
  .filter((node) => node.tagName === 'TEXT').map((node) => node.textContent)};

console.log(JSON.stringify({
  ok: true,
  failure: FAILURE || null,
  refresh_failure: REFRESH || null,
  decision_failure: DECISION_FAILURE,
  stamp: STAMP || null,
  event: eventId,
  title: document.title,
  legacy_cards: LEGACY,
  present,
  advisory: text('adv-asof'),
  afterLoad,
  desk,
  plain: plainOutsideFolds(),
  saving,
  folds,
  tiles,
  chart,
  rules,
  limits,
  priceOutlook,
  impact,
  drivers,
  decision_form: decisionForm,
  decision: flow && byId.get('dc-form') ? {status: text('dc-status'), rail: kids('rail').map((li) => li.className),
                    reason: byId.get('dc-reason').value} : null,
  history: {hidden: hidden('history'), html: html('hist-list')},
  assumption: {value: text('as-value'), unit: text('as-unit')},
  ask: byId.has('ask') ? {context: byId.get('ask').getAttribute('data-context')} : null,
  calls: calls.map((call) => call.method + ' ' + call.path),
  errors,
}, null, 1));
