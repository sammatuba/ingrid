/* Run the asset pages' own script (`src/grid/asset.js`) against a built payload under a small
   DOM shim and print one JSON report on stdout. Offline: no browser, no network, no library,
   nothing written. The shim implements exactly the DOM surface asset.js uses and throws on
   anything else, so a gap is a failure rather than a silent pass. It is an approximation of a
   browser: it proves the page executes and fills every block from the payload — the counts,
   the tiles, the lists, the search, the figures, both charts, the register, the location, the
   messages, the events, the catalog block and the not-known lines — not that the layout looks
   right. The real browser run at 390 and 1280 is the orchestrator's and belongs in the task
   record, not here.

     node tests/fixtures/grid/asset/render.mjs --root .
       [--data DIR] [--page assets|asset] [--code CODE] [--stamp <16 hex>] [--query TEXT]
       [--bake DIR] [--at YYYY-MM-DDTHH:MM] [--then YYYY-MM-DDTHH:MM] [--only] [--qs QUERY]

   --data names the directory holding `assets/index.json` and `assets/<code>.json` (default:
   this fixture's `payload`). --query types into the collection page's search box and the
   report carries the filtered list. --stamp writes the build stamp into the page's meta
   element, so the report's `calls` show the versioned URL the page asked for.

   ericka-desk slice 6: the pages also read the shared records `advisories.json`, `sites.json`,
   `events.json` and `outages.json` from --bake (default: --data when it holds `sites.json`,
   else the catalog fixture's bake, which has no `outages.json`); a name the directory does not
   hold is a 404, as on the server. --at stands in for the shell's shared "as of" clock
   (`window.GNShell`); --then moves that clock afterwards through the shell's `onAsOf` listeners
   and the report carries what the page drew at the second time under `then`. --only opens the
   collection page with its "With a notice" filter on (`?notice=1` in the address, as a shared
   link would); --qs opens either page with any other query string (`grid=CVIS&status=trip`).
   Platform polish: the filters are read from the address, so the shim's location carries a
   search string and the report carries the filter bar's count and controls. */
import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import vm from 'node:vm';

const errors = [];
function fail(message) {
  console.log(JSON.stringify({ok: false, error: String(message), errors}));
  process.exit(1);
}

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/asset/payload')));
const PAGE = arg('page', 'assets');
const CODE = arg('code', '08PEDC');
const STAMP = arg('stamp', '');
const QUERY = arg('query', '');
const AT = arg('at', '');
const THEN = arg('then', '');
const ONLY = argv.includes('--only');
const QS = [arg('qs', ''), ONLY ? 'notice=1' : ''].filter(Boolean).join('&');
const WIDTH = 1280;

const html = readFileSync(path.join(ROOT, 'src/grid', PAGE === 'asset' ? 'asset.html' : 'assets.html'), 'utf8');

/* ---------- a small DOM, built from the page's own HTML ---------- */
function attributes(source) {
  const attrs = {};
  const re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"/g;
  let found;
  while ((found = re.exec(source)) !== null) attrs[found[1]] = found[2];
  return attrs;
}
const camel = (name) => name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
const VOID = new Set(['meta', 'link', 'input', 'br', 'img', 'hr', 'source']);

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
    this.value = '';
    this.rect = {left: 0, top: 0, width: WIDTH, height: 190};
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
  get innerHTML() { return this.html === null ? this.text : this.html; }
  set innerHTML(value) { this.html = String(value); this.children = []; }
  get className() { return [...this.classes].join(' '); }
  set className(value) { this.classes = new Set(String(value).split(/\s+/).filter(Boolean)); }
  get classList() {
    const classes = this.classes;
    return {contains: (name) => classes.has(name), add: (name) => classes.add(name),
            remove: (name) => classes.delete(name), toggle: (name, on) => (on ? classes.add(name) : classes.delete(name))};
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatch(type, event = {}) { for (const fn of this.listeners[type] || []) fn(event); }
  getBoundingClientRect() { return this.rect; }
}

const byId = new Map();
const all = [];
const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*?)>/g;
const stack = [];
let match;
while ((match = tagRe.exec(html)) !== null) {
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
if (STAMP) {
  const meta = byId.get('nowcast-build');
  if (!meta) fail('the page carries no nowcast-build meta element for the stamp');
  meta.attrs.content = STAMP;
}
const body = all.find((node) => node.tagName === 'BODY');
const document = {
  title: (html.match(/<title>([^<]*)<\/title>/) || [null, ''])[1],
  readyState: 'complete',   // main() runs as soon as the page's script does
  body,
  getElementById: (id) => byId.get(id) || null,
  createElementNS: (_ns, tag) => new Shim(tag),
  addEventListener: () => {},
};

/* ---------- the payload, and the one request the page makes ---------- */
const calls = [];
const BAKE = path.resolve(arg('bake', existsSync(path.join(DATA, 'sites.json')) ? DATA
  : path.join(ROOT, 'tests/fixtures/grid/catalog/bake')));
const SHARED = new Set(['advisories.json', 'sites.json', 'events.json', 'outages.json']);
const payloadFor = (url) => {
  const name = String(url).replace(/^\/grid-data\/(?:[0-9a-f]{16}\/)?/, '');
  if (SHARED.has(name)) return existsSync(path.join(BAKE, name)) ? JSON.parse(readFileSync(path.join(BAKE, name), 'utf8')) : null;
  if (name === 'assets/index.json') return JSON.parse(readFileSync(path.join(DATA, 'assets/index.json'), 'utf8'));
  const found = /^assets\/([A-Za-z0-9._-]+)\.json$/.exec(name);
  if (found) return JSON.parse(readFileSync(path.join(DATA, 'assets', found[1] + '.json'), 'utf8'));
  return null;
};
function transport(url) {
  calls.push(String(url));
  const body = payloadFor(url);
  if (body === null) return Promise.resolve({ok: false, status: 404, json: async () => null});
  return Promise.resolve({ok: true, status: 200, json: async () => body});
}

/* ---------- run the page's own script ---------- */
const sandbox = {
  document,
  location: {pathname: PAGE === 'asset' ? '/plant/' + encodeURIComponent(CODE) : '/plants', hash: '',
             search: QS ? '?' + QS : ''},
  URLSearchParams,
  fetch: transport,
  addEventListener: () => {},          // the profile page's resize listener; there is no layout here
  console: {log: () => {}, warn: () => {}, error: (m) => errors.push(String(m))},
};
sandbox.window = sandbox;
/* The shell's shared clock, as far as the page uses it: asOf() and onAsOf(). */
const asOfListeners = [];
let shellAt = AT || '2026-09-29T23:55';
if (AT) {
  sandbox.GNShell = {span: {first: '2026-09-21T00:00', last: '2026-09-29T23:55'},
                     asOf: () => shellAt, onAsOf: (fn) => { asOfListeners.push(fn); }};
}
if (ONLY && !byId.get('only-notice')) fail('the page carries no only-notice control');
try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/asset.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/asset.js'});
} catch (error) {
  fail('the page script threw: ' + (error && error.stack ? error.stack : error));
}

/* ---------- what it rendered ---------- */
const content = (id) => {
  const node = byId.get(id);
  if (!node) return null;
  return {text: node.textContent, html: node.innerHTML, hidden: node.hidden};
};
const settle = async (done) => {
  for (let turn = 0; turn < 500 && !done(); turn += 1) await new Promise((resolve) => setTimeout(resolve, 0));
  if (!done()) fail('the page never finished what it was doing');
};
const filled = () => {
  const box = byId.get(PAGE === 'asset' ? 'figures' : 'tiles');
  return box !== null && box.innerHTML !== null && box.innerHTML !== '';
};
const plantView = () => (PAGE === 'asset'
  ? {at: content('activity-at').text, status: content('activity-status').html,
     latest: content('activity-latest').html, facts: content('activity-facts').html, watch: content('watch').html, next: content('next').html,
     unclear: content('activity-unclear').html, src: content('activity-src').text,
     messages: content('messages').html, events: content('events').html}
  : {at: content('as-of').text, sum: content('status-sum').html, list: content('status-list').html,
     unclear: content('unclear-list').html, lists: content('lists').html, found: content('found').text,
     only: byId.get('only-notice') && byId.get('only-notice').children[0]
       ? byId.get('only-notice').children[0].getAttribute('aria-pressed') : ''});
await settle(filled);

const report = {ok: true, page: PAGE, code: PAGE === 'asset' ? CODE : null, stamp: STAMP || null,
                title: document.title, calls, errors};
if (PAGE === 'asset') {
  const svg = (id) => {
    const node = byId.get(id);
    return {children: node.children.length,
            paths: node.children.filter((c) => c.tagName === 'PATH').map((c) => c.attrs.d || ''),
            labels: node.children.filter((c) => c.tagName === 'TEXT').map((c) => c.textContent)};
  };
  report.profile = {
    name: content('name'), meta: content('meta'),
    figures: content('figures').html,
    charts: {price: svg('price'), mw: svg('mw')},
    chart_asof: content('chart-asof').text, chart_src: content('chart-src').text,
    register: content('register').html, location: content('location').html,
    messages: content('messages').html, events: content('events').html,
    catalog: content('catalog').html, not_known: content('not-known').html,
    back: byId.get('back').getAttribute('href'),
    crumb: content('crumb').text, readout: content('readout').text,
    messages_filter: content('messages-filter').html,
    position_src: content('position-src'),
  };
} else {
  report.collection = {
    count: content('count').text, as_of: content('as-of').text,
    tiles: content('tiles').html, lists: content('lists').html,
    found: content('found').text, cap_src: content('cap-src').text,
  };
  if (QUERY) {
    const search = byId.get('search');
    search.value = QUERY;
    search.dispatch('input');
    report.collection.filtered = {query: QUERY, lists: content('lists').html,
                                  found: content('found').text};
  }
}
report.plants = plantView();
if (THEN) {
  if (!asOfListeners.length) fail('the page registered no as-of listener (pass --at)');
  shellAt = THEN;
  for (const fn of asOfListeners) fn(THEN);
  report.then = plantView();
}
console.log(JSON.stringify(report, null, 1));
