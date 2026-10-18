/* Run the data catalog page's own script (src/grid/catalog.js) against a built catalog payload
   and print what it rendered, as one JSON object on stdout. Offline: no browser, no network,
   no library.

   The shim below implements exactly the DOM surface `catalog.js` uses and throws on anything
   else, so a gap in the shim is a failure rather than a silent pass. It is an approximation of
   a browser: it proves the script executes and fills the page from the payload, not that the
   layout looks right. The browser check is the orchestrator's.

     node tests/fixtures/grid/catalog/render.mjs --root . --data <dir with catalog.json> \
          [--stamp <16 hex>]

   The data directory is a built bake (the fixture's `bake/` after
   `scripts/grid/build_catalog.py --bake tests/fixtures/grid/catalog/bake` has written
   `catalog.json` beside the baked files, or the real `build/grid-data`).
*/
import {readFileSync} from 'node:fs';
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
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/catalog/bake')));
/* With --stamp the shim's page carries the build stamp the application writes in, so the report
   shows the versioned URL the page asks for; without it the source page's token stays and the
   unversioned name is read. */
const STAMP = arg('stamp', '');

const PAGE = readFileSync(path.join(ROOT, 'src/grid/catalog.html'), 'utf8');

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

class Shim {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = {...attrs};
    this.children = [];
    this.parentNode = null;
    this.listeners = {};
    this.hidden = false;
    this.dataset = {};
    this.classes = new Set();
    this.text = '';
    this.html = null;
    this.value = '';
    this.rect = {left: 0, top: 0, width: 1280, height: 0};
    /* DATA-1: the CSSOM the page sets a bar's place and a lineage indent through; a style
       attribute in markup is refused by the site's policy, so the page must not need one. */
    const props = {};
    this.style = {
      setProperty: (name, value) => { props[name] = String(value); },
      getPropertyValue: (name) => (name in props ? props[name] : ''),
      props,
    };
    for (const [key, value] of Object.entries(attrs)) this.setAttribute(key, value);
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name === 'class') this.classes = new Set(String(value).split(/\s+/).filter(Boolean));
    if (name.startsWith('data-')) this.dataset[camel(name.slice(5))] = String(value);
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  removeChild(child) {
    const at = this.children.indexOf(child);
    if (at >= 0) this.children.splice(at, 1);
    return child;
  }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  get parentElement() { return this.parentNode; }
  get textContent() { return this.text; }
  set textContent(value) { this.text = String(value); this.html = escapeText(this.text); }
  get innerHTML() { return this.html === null ? escapeText(this.text) : this.html; }
  /* Setting innerHTML parses the one thing the page reaches for afterwards: the elements that
     carry the wire-up attributes (`data-set`, `data-set-link`), which in a browser would be
     queryable and clickable. Everything else is kept as markup, as the page only reads it. */
  set innerHTML(value) {
    this.html = String(value);
    this.children = [];
    const re = /<([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*)\/?>/g;
    let found;
    while ((found = re.exec(this.html)) !== null) {
      const attrs = attributes(found[2]);
      /* DATA-1: and the nodes the page places through the CSSOM (`data-left`, `data-depth`). */
      if (!('data-set' in attrs) && !('data-set-link' in attrs) && !('data-left' in attrs)
          && !('data-depth' in attrs)) continue;
      this.appendChild(new Shim(found[1], attrs));
    }
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatch(type, event = {}) { for (const fn of this.listeners[type] || []) fn(event); }
  get offsetWidth() { return this.rect.width; }
  get classList() {
    const classes = this.classes;
    return {
      add: (...names) => names.forEach((name) => classes.add(name)),
      remove: (...names) => names.forEach((name) => classes.delete(name)),
      contains: (name) => classes.has(name),
    };
  }
  get className() { return [...this.classes].join(' '); }
  set className(value) { this.classes = new Set(String(value).split(/\s+/).filter(Boolean)); }
  descendants() { return this.children.flatMap((child) => [child, ...child.descendants()]); }
  querySelectorAll(selector) {
    const wanted = selector.replace(/^\./, '');
    const isClass = selector.startsWith('.');
    return this.descendants().filter((node) => isClass ? node.classes.has(wanted)
                                                        : node.tagName === selector.toUpperCase());
  }
}

const byId = new Map();
const all = [];
const tagRe = /<([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*)\/?>/g;
let match;
while ((match = tagRe.exec(PAGE)) !== null) {
  const node = new Shim(match[1], attributes(match[2]));
  all.push(node);
  if (node.getAttribute('id')) byId.set(node.getAttribute('id'), node);
}
if (STAMP) {
  const meta = byId.get('nowcast-build');
  if (!meta) fail('the page carries no nowcast-build meta element for the stamp');
  meta.attrs.content = STAMP;
}

const document = {
  title: (PAGE.match(/<title>([^<]*)<\/title>/) || [null, ''])[1],
  body: new Shim('body'),
  getElementById: (id) => byId.get(id) || null,
  createElement: (tag) => new Shim(tag),
  addEventListener: () => {},
};

/* ---------- fetching the built catalog ---------- */
const fetched = [];
const cache = new Map();
function fetchData(url) {
  const wanted = decodeURIComponent(String(url));
  fetched.push(wanted);
  const name = wanted.replace(/^\/grid-data\/(?:[0-9a-f]{16}\/)?/, '');
  if (!cache.has(name)) {
    try {
      cache.set(name, {ok: true, status: 200,
                       json: JSON.parse(readFileSync(path.join(DATA, name), 'utf8'))});
    } catch {
      cache.set(name, {ok: false, status: 404});
    }
  }
  const payload = cache.get(name);
  return Promise.resolve(payload.ok ? {...payload, json: async () => payload.json} : payload);
}

/* PP-B4: the page keeps its filter in the address (`?family=&q=`) and the open dataset in the
   hash, so the shim carries the address the page reads and records what it writes back. */
const written = [];
const sandbox = {
  document,
  window: {addEventListener: () => {}},
  location: {hash: '', search: '', pathname: '/data'},
  history: {state: null, replaceState: (_state, _title, url) => { written.push(String(url)); }},
  URLSearchParams,
  fetch: fetchData,
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  console: {log: () => {}, warn: (m) => errors.push(String(m)), error: (m) => errors.push(String(m))},
};

try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/catalog.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/catalog.js'});
} catch (error) {
  fail('the page script threw: ' + (error && error.stack ? error.stack : error));
}

const until = async (predicate, turns = 500) => {
  for (let turn = 0; turn < turns && !predicate(); turn += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
};
await until(() => sandbox.window.DataCatalog && sandbox.window.DataCatalog.D);

const W = sandbox.window.DataCatalog;
if (!W || !W.D) fail('the page never received the catalog payload: ' + fetched.join(', '));

const text = (id) => (byId.get(id) ? byId.get(id).innerHTML : null);
const tiles = () => byId.get('tiles').children.map((node) => ({
  family: node.getAttribute('data-family'), pressed: node.getAttribute('aria-pressed'),
  text: node.innerHTML,
}));
/* PP-B4: one table for every dataset. Its head is static in the page; its body is the page's
   own rows, one `tr[data-set]` per dataset the filter keeps. */
const HEAD = (PAGE.match(/<thead>([\s\S]*?)<\/thead>/) || [null, ''])[1];
const rows = () => byId.get('list').children.filter((node) => node.tagName === 'TR')
  .map((node) => ({id: node.getAttribute('data-set'), href: node.getAttribute('data-href')}));
const rowHtml = () => byId.get('list').innerHTML;
/* DATA-1: each coverage bar's markup values and what the page set through the CSSOM. */
const fills = () => byId.get('list').children.filter((node) => node.classes.has('fill')).map((node) => ({
  left: node.getAttribute('data-left'), width: node.getAttribute('data-width'),
  style: {...node.style.props},
}));
const detail = () => {
  const body = byId.get('detail-body').innerHTML || '';
  return {
    open: !byId.get('detail').hidden,
    title: byId.get('detail-title').textContent,
    schemaRows: (body.match(/<tr><td class="mono">/g) || []).length,
    chain: byId.get('detail-body').children.filter((node) => node.getAttribute('data-set-link'))
      .map((node) => node.getAttribute('data-set-link')),
    steps: byId.get('detail-body').children.filter((node) => node.classes.has('chain-step'))
      .map((node) => ({depth: node.getAttribute('data-depth'), style: {...node.style.props}})),
    hasSample: body.includes('Sample row'),
    sampleFile: (body.match(/<p class="src">([^<]*)<\/p>/) || [null, null])[1],
    body,
  };
};

const report = {ok: true, stamp: STAMP || null, fetched, errors,
                count: text('count'), tiles: tiles(), head: HEAD, rows: rows(), rowHtml: rowHtml(), fills: fills(),
                stats: text('stats'), caption: text('caption'), detail: null, searched: null,
                family: null, address: null};

/* One dataset's detail, opened the way a click opens it. */
W.open('bake-regions');
report.detail = detail();
report.detail.selected = (rowHtml().match(/<tr data-set="([^"]+)"[^>]*aria-selected="true"/) || [null, null])[1];
report.address = {opened: written[written.length - 1]};
W.close();
report.address.closed = written[written.length - 1];
report.address.closedPanel = byId.get('detail').hidden;
/* The search filters the tables by name, publisher and category. */
W.search('register');
report.searched = {q: W.state.q, count: text('count'), rows: rows().map((row) => row.id),
                   address: written[written.length - 1]};
W.search('');
/* A tile filters by category. */
W.setFamily('bake');
report.family = {family: W.state.family, rows: rows().map((row) => row.id),
                 address: written[written.length - 1],
                 pressed: tiles().filter((tile) => tile.pressed === 'true').map((tile) => tile.family)};
/* A dataset outside the filter clears the filter, so a link always lands on its row. */
W.open('grid-ref-resources');
report.family.afterOpen = {family: W.state.family, open: W.state.open, rows: rows().length};

const rendered = byId.get('list').innerHTML;
if (/could not be loaded/.test(rendered)) fail('the page reported a load failure: ' + rendered);

console.log(JSON.stringify(report, null, 1));
