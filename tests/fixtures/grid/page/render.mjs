/* Run the grid page's own script (src/grid/grid.js) against a baked-data directory and print
   what it rendered, as one JSON object on stdout. Offline: no browser, no network, no library.

   The shim below implements exactly the DOM surface `grid.js` and `map.js` (the canvas module
   the page mounts, ATG-8) use and throws on anything else, so a gap in the shim is a failure
   rather than a silent pass. It is an approximation of a real browser: it proves the scripts
   execute and fill the page from the data at a given viewport width, not that the drawing looks
   right — what the canvas paints is read from the module's own `snapshot()`, and the paints
   themselves from the module's own harness (`tests/fixtures/grid/map/harness.mjs`). The browser
   check (tests/fixtures/grid/page/browser.mjs) is the real one.

     node tests/fixtures/grid/page/render.mjs --root . --data tests/fixtures/grid/page/data \
          --width 1280 [--hash "t=13:40&g=CVIS"] [--stamp <16 hex>] \
          [--hold-node [--node-fail] [--stage-interact] [--stage-map]] [--no-briefs] [--step]
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

/* ---------- arguments ---------- */
const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.lastIndexOf('--' + name);   // a repeated flag is the caller's last word
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/page/data')));
const WIDTH = Number(arg('width', '1280'));
const HASH = arg('hash', '');
/* With --stamp the shim's page is the one the application serves: the build stamp is written
   into the `nowcast-build` meta element, so the script reads its replay files under the
   versioned prefix. Without it the source page's token stays, the script sees no stamp, and
   the unversioned names are read — the path a fixture-only page takes. */
const STAMP = arg('stamp', '');
/* --health-fail makes the page's one warm-up `GET /health` (PERF-5) fail, so a test can run
   the page the way a refused or unreachable health check leaves it: drawn, with no error. */
const HEALTH_FAIL = argv.lastIndexOf('--health-fail') >= 0;
/* --hold-node keeps the node file's answer in flight (PERF-4) until the harness has read the
   page as it stands without it: the report then carries `stage1`, the brief, figures, feed,
   map outline and tooltip that the six small files drew, next to the finished page. */
const HOLD_NODE = argv.lastIndexOf('--hold-node') >= 0;
/* --node-fail refuses the node file outright: the outline must stay drawn, with the site
   prices unknown and named as unavailable rather than shown as figures. */
const NODE_FAIL = argv.lastIndexOf('--node-fail') >= 0;
/* --stage-interact (with --hold-node) presses the Luzon grid button and steps the replay
   forward once while the node file is still in flight: the page must keep working, at a grid
   and a replay time the user chose, with the site layer still unknown. */
const STAGE_INTERACT = argv.lastIndexOf('--stage-interact') >= 0;
/* --stage-map (with --hold-node) sets the reader's own map state while the node file is still
   in flight: the Luzon scope chip, the Pending layer chip off and one zoom-in. The node file
   then lands without the canvas being remounted, so the finished page must still stand on that
   scope, that layer set and that transform, with the open tooltip showing the price (ATG-8's
   correction of the reviewed remount). */
const STAGE_MAP = argv.lastIndexOf('--stage-map') >= 0;
/* --no-briefs refuses the two composed files (ATG-5's briefs.json and findings.json), the way a
   bake that has not composed them answers: the page must draw and leave the panel's mount point
   hidden, never an empty panel and never an error. */
const NO_BRIEFS = argv.lastIndexOf('--no-briefs') >= 0;
/* --step presses the forward five-minute button and the Luzon grid button once on the finished
   page (ATG-8): the panel's controller must be driven by the page's own render, the same as
   every other element on it, and the calls it recorded are what the report's `briefs` block
   carries. */
const STEP = argv.lastIndexOf('--step') >= 0;

/* ---------- a small DOM, built from the page's own HTML ---------- */
const PAGE = readFileSync(path.join(ROOT, 'src/grid/index.html'), 'utf8');

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
    this.style = {};
    this.dataset = {};
    this.classes = new Set();
    this.text = '';
    this.html = null;
    this.rect = {left: 0, top: 0, width: WIDTH, height: 0};
    for (const [key, value] of Object.entries(attrs)) this.setAttribute(key, value);
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name === 'class') this.classes = new Set(String(value).split(/\s+/).filter(Boolean));
    if (name.startsWith('data-')) this.dataset[camel(name.slice(5))] = String(value);
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  removeAttribute(name) { delete this.attrs[name]; }
  /* `hidden` is the attribute, as the module and the page set it; the getter is what the report
     reads, so a tip the module has hidden is not reported as open. */
  get hidden() { return 'hidden' in this.attrs; }
  set hidden(value) { if (value) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  removeChild(child) {
    const at = this.children.indexOf(child);
    if (at >= 0) this.children.splice(at, 1);
    return child;
  }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  get parentElement() { return this.parentNode; }
  get textContent() { return this.text; }
  set textContent(value) { this.text = String(value); }
  get innerHTML() { return this.html === null ? escapeText(this.text) : this.html; }
  set innerHTML(value) { this.html = String(value); this.children = []; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  /* The map module's `destroy` unbinds its own canvas listeners, so the shim has to give it
     something to unbind (nothing calls it here: ATG-8's page mounts the canvas once and hands
     the node file's layer over with `setNodes`). */
  removeEventListener(type, fn) {
    const list = this.listeners[type] || [];
    const at = list.indexOf(fn);
    if (at >= 0) list.splice(at, 1);
  }
  dispatch(type, event = {}) { for (const fn of this.listeners[type] || []) fn(event); }
  getBoundingClientRect() { return this.rect; }
  get offsetWidth() { return this.rect.width; }
  scrollIntoView() {}
  get classList() {
    const classes = this.classes;
    return {
      add: (...names) => names.forEach((name) => classes.add(name)),
      remove: (...names) => names.forEach((name) => classes.delete(name)),
      contains: (name) => classes.has(name),
    };
  }
  descendants() { return this.children.flatMap((child) => [child, ...child.descendants()]); }
  querySelectorAll(selector) {
    const wanted = selector.replace(/^\./, '');
    return this.descendants().filter((node) => node.classes.has(wanted));
  }
}

/* ATG-8: the map is ATG-6's canvas (`src/grid/map.js`), mounted by the page from the files it
   has already read. The shim gives the module the canvas surface it uses — a 2D context that
   accepts the paints it claims (and throws on a member the module does not use, the same rule
   the rest of this shim holds) and a box — so the module runs its own drawing path and its own
   `snapshot()` is what the report reads. The paints themselves are read by the module's own
   harness (`tests/fixtures/grid/map/harness.mjs`); what is read here is the page's wiring. */
const PAINTS = ['setTransform', 'clearRect', 'fillRect', 'beginPath', 'moveTo', 'lineTo',
                'closePath', 'quadraticCurveTo', 'arc', 'fill', 'stroke', 'fillText', 'setLineDash'];
function makeContext() {
  const style = {fillStyle: '#000', strokeStyle: '#000', lineWidth: 1, globalAlpha: 1,
                 font: '10px sans-serif', textAlign: 'start', textBaseline: 'alphabetic', lineJoin: 'miter'};
  const ops = [];
  const impl = {ops};
  for (const name of PAINTS) impl[name] = () => { ops.push(name); };
  /* A style member is stored; anything else is a gap and is named. */
  const context = new Proxy(impl, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop in style) return style[prop];
      throw new Error('shim: the canvas context member ' + String(prop) + ' is not one this harness knows');
    },
    set(target, prop, value) {
      if (prop in style || prop in target) { style[prop] = value; return true; }
      throw new Error('shim: the canvas context member ' + String(prop) + ' is not one this harness knows');
    },
  });
  return context;
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
const buttons = (name) => all.filter((node) => node.tagName === 'BUTTON' && name in node.dataset);
// The groups the page reaches with querySelectorAll: its own data attributes select them.
const GROUPS = {
  '.grids button': buttons('grid'),
  '[data-step]': all.filter((node) => 'step' in node.dataset),
  '.filters button': buttons('filter'),
};
// A table's rows live in an implicit tbody the page reaches through `figures.tBodies[0]`.
for (const table of all.filter((node) => node.tagName === 'TABLE')) table.tBodies = [new Shim('tbody')];
if (STAMP) {
  const meta = byId.get('nowcast-build');
  if (!meta) fail('the page carries no nowcast-build meta element for the stamp');
  meta.attrs.content = STAMP;
}
// A viewport width is all the shim can know, so the two boxes are approximated from it
// (phone: the map takes the column; desk: the map sits between two columns).
const boxes = {
  map: {left: 0, top: 0, width: WIDTH < 600 ? WIDTH - 24 : WIDTH - 470, height: WIDTH < 600 ? 420 : 560},
  chart: {left: 0, top: 0, width: WIDTH - 40, height: 260},
};
byId.get('map').rect = boxes.map;
byId.get('chart').rect = boxes.chart;
// The page's own ring is drawn on the overlay beside the canvas, placed at the spot the module
// painted a site: the overlay and every canvas get the map's own box, so the arithmetic the page
// does (the canvas within the overlay) is the identity here.
byId.get('map-marks').rect = boxes.map;

const document = {
  // A browser takes the document title from the `<title>` element; the page never sets it.
  title: (PAGE.match(/<title>([^<]*)<\/title>/) || [null, ''])[1],
  getElementById: (id) => byId.get(id) || null,
  createElement: (tag) => {
    const node = new Shim(tag);
    if (String(tag).toLowerCase() === 'canvas') {
      node.rect = boxes.map;
      node.getContext = (kind) => (kind === '2d' ? makeContext() : null);
    }
    return node;
  },
  createElementNS: (_ns, tag) => new Shim(tag),
  querySelectorAll: (selector) => {
    if (!(selector in GROUPS)) throw new Error('shim: unsupported selector ' + selector);
    return GROUPS[selector];
  },
  querySelector: (selector) => {
    const found = all.filter((node) => node.classes.has(selector.replace(/^\./, '')));
    if (!found.length) return null;
    return selector === '.desk' ? found[0] : found[0];
  },
  addEventListener: () => {},
};

/* ---------- fetching the baked data ---------- */
const cache = new Map();
const fetched = [];
/* The node file is the one file the page can draw without (PERF-4); it is the one the two flags
   above act on. `--hold-node` parks its answer until the caller releases it. */
const NODE_NAME = /^nodes-\d{4}-\d{2}-\d{2}\.json$/;
/* ATG-8: the two files the briefing and findings panel is mounted from. */
const BRIEF_NAME = /^(briefs|findings)\.json$/;
let releaseNode = null;
const nodeHeld = new Promise((resolve) => { releaseNode = resolve; });
function fetchData(url) {
  const wanted = decodeURIComponent(String(url));
  fetched.push(wanted);
  // Both the versioned and the unversioned name read the same fixture file; the report says
  // which one the page asked for, so the stamp's effect is visible and not assumed.
  const name = wanted.replace(/^\/grid-data\/(?:[0-9a-f]{16}\/)?/, '');
  if (NODE_FAIL && NODE_NAME.test(name)) return Promise.resolve({ok: false, status: 404});
  if (NO_BRIEFS && BRIEF_NAME.test(name)) return Promise.resolve({ok: false, status: 404});
  if (!cache.has(name)) {
    try {
      cache.set(name, {ok: true, status: 200, json: JSON.parse(readFileSync(path.join(DATA, name), 'utf8'))});
    } catch {
      cache.set(name, {ok: false, status: 404});
    }
  }
  const payload = cache.get(name);
  const answer = payload.ok ? {...payload, json: async () => payload.json} : payload;
  return HOLD_NODE && NODE_NAME.test(name) ? nodeHeld.then(() => answer) : Promise.resolve(answer);
}

/* The page's one warm-up call (PERF-5) is not a replay fetch: it is recorded on its own, so
   the `fetched` list stays exactly the seven replay files, and the report says whether the page
   asked for it even when the check fails. */
const health = [];
function fetchHealth(url) {
  health.push(String(url));
  if (HEALTH_FAIL) return Promise.reject(new Error('the health check could not be reached'));
  return Promise.resolve({ok: true, status: 200, json: async () => ({status: 'ok'})});
}
function fetchAny(url) {
  return String(url) === '/health' ? fetchHealth(url) : fetchData(url);
}

const replaced = [];
/* ATG-8: the page mounts `src/grid/briefs.js` (ATG-5) over the two composed files. That module
   needs a richer DOM than this shim gives — it parses its own markup and reads node attributes
   — so the shim stands in for it: `window.GridBriefs.mount` records the container, the payloads
   and the callbacks the page passes, and the controller records every setGrid/setClock the
   page's own render makes. The panel itself is exercised by its own harness over a real DOM
   (tests/fixtures/grid/briefs/panel-harness.mjs), so this file proves the wiring, not the
   panel's drawing. */
const briefs = {mounts: [], calls: []};
function briefsMount(container, data, links) {
  const findings = (data && data.findings && data.findings.findings) || [];
  briefs.mounts.push({
    container: container.getAttribute('id'),
    briefs: !!(data && data.briefs), grids: Object.keys((data && data.briefs && data.briefs.grids) || {}),
    findings: findings.length,
    grid: links.grid, clock: links.clock,
    callbacks: Object.keys(links).filter((key) => typeof links[key] === 'function').sort(),
  });
  return {
    setGrid: (code) => briefs.calls.push('setGrid:' + code),
    setClock: (t) => briefs.calls.push('setClock:' + t),
    setKind: () => {}, select: () => [], element: container,
  };
}
/* ATG-8: the map is the real module (`src/grid/map.js`, ATG-6) mounted by the page. It runs in
   the same sandbox the page does, and the mount is wrapped so the report can read what the page
   handed it and what the module drew (`snapshot()`). */
const mounts = [];
function mountMap(host, data, callbacks) {
  const mounted = realGridMap.mount(host, data, callbacks);
  mounts.push({host, data, callbacks, panel: mounted});
  return mounted;
}
const sandbox = {
  document,
  window: {addEventListener: () => {}, GridBriefs: {mount: briefsMount}},
  location: {hash: HASH ? '#' + HASH : ''},
  history: {replaceState: (_a, _b, url) => replaced.push(url)},
  fetch: fetchAny,
  setInterval: () => 0,
  clearInterval: () => {},
  // The warm-up is scheduled after the first paint (`requestAnimationFrame` then a timer), so
  // the shim supplies both: a frame here is a timer tick, and the timer that follows it runs.
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  requestAnimationFrame: (fn) => setTimeout(() => fn(), 0),
  URLSearchParams,
  console: {log: () => {}, warn: () => {}, error: (m) => errors.push(String(m))},
};

/* ---------- run the canvas module, then the page's own script ---------- */
let realGridMap = null;
try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/map.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/map.js'});
  realGridMap = sandbox.window.GridMap;
  if (!realGridMap || typeof realGridMap.mount !== 'function') fail('map.js exposed no GridMap.mount');
  sandbox.window.GridMap = Object.assign({}, realGridMap, {mount: mountMap});
} catch (error) {
  fail('the map module threw: ' + (error && error.stack ? error.stack : error));
}
try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/grid.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/grid.js'});
} catch (error) {
  fail('the page script threw: ' + (error && error.stack ? error.stack : error));
}

/* ---------- what it rendered ---------- */
const content = (id) => {
  const node = byId.get(id);
  if (!node) return null;
  return {text: node.textContent, html: node.innerHTML};
};
/* The page's own state markers live on the `.map-wrap` section it parses from the HTML. */
const mapSection = all.find((node) => node.classes.has('map-wrap'));
const mapState = (name) => !!mapSection && mapSection.classes.has(name);
/* ATG-8: the map is the canvas module, so what it drew is its own `snapshot()`: the located
   sites (each with its code, value and the fill it was painted in; PP-B5: the unlocated ones are
   its `pending` rows, listed by the page and never painted, so they are counted apart), the
   two links with their label, the message marks and the event rings. The page mounts the canvas
   once (the node file's layer is handed over with `setNodes`), so this is that one mount. */
const mapPanel = () => (mounts.length ? mounts[mounts.length - 1].panel : null);
const mapSnap = () => { const p = mapPanel(); return p && p.snapshot ? p.snapshot() : null; };
const mapRows = () => { const s = mapSnap(); return s ? (s.located || []) : []; };
/* The module's tooltip is its own element inside the map host; the page holds no tooltip. */
const mapTip = () => {
  const host = byId.get('map');
  const tip = host ? host.querySelectorAll('.gmap-tip')[0] : null;
  return tip && !tip.hidden ? tip.innerHTML : null;
};
/* The tooltip is the module's own, shown under the pointer: a canvas holds no element per site,
   so the pointer is moved to the spot the module's own record says it painted the first located
   site — the same hover a reader makes, at the site's own coordinates. */
const hoverFirstSite = () => {
  const rows = mapRows();
  const p = mapPanel();
  if (!rows.length || !p || !p.canvas) return;
  p.canvas.dispatch('pointermove', {clientX: rows[0].x, clientY: rows[0].y, pointerId: 1});
};
/* ATG-8 rework: the reader's own map state, set while the node file is still arriving — the
   Luzon scope chip, the Load nodes layer chip off and one zoom-in — clicked on the module's own
   elements (`--stage-map`), so the finished page can be held to it: the node file's layer must
   arrive without the canvas being remounted and without any of it changing. */
const stageMapActions = () => {
  const p = mapPanel();
  if (!p || !p.root || !p.root.descendants) return;
  const nodes = p.root.descendants();
  const click = (node) => { if (node) node.dispatch('click'); };
  click(nodes.find((node) => node.dataset.scope === 'CLUZ'));
  click(nodes.find((node) => node.dataset.layer === 'loads'));
  click(nodes.find((node) => node.attrs && node.attrs['aria-label'] === 'Zoom in'));
};
/* Let the script's own promises and timers run until `predicate` holds (or the turn budget
   ends, which the report then shows as the state it reached). */
const until = async (predicate, turns = 500) => {
  for (let turn = 0; turn < turns && !predicate(); turn += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
};
const snapshot = () => ({
  clock: content('clock-time'),
  scrub: {max: byId.get('scrub').max, value: byId.get('scrub').value},
  brief: {title: content('brief-title'), text: content('brief-text'), asof: content('brief-asof')},
  figures: byId.get('figures').tBodies[0].children.map((row) => ({html: row.innerHTML, class: row.attrs.class || ''})),
  figuresAsOf: content('figures-asof'),
  reviews: {hidden: byId.get('reviews').hidden, list: content('review-list')},
  feed: {count: content('feed-count'), list: content('feed')},
  map: (() => {
    const s = mapSnap();
    const rows = mapRows();
    const marks = byId.get('map-marks');
    return {
      mounted: !!mapPanel(),
      viewBox: s ? `0 0 ${Math.round(s.width)} ${Math.round(s.height)}` : null,
      loading: mapState('loading'),
      pricing: mapState('pricing'),
      // ATG-8 rework: the page mounts the canvas once (the node file's layer is handed over,
      // never remounted), so this count is one — the reader's own map state, the scope, the
      // layer flags and the transform, is read beside it.
      mounts: mounts.length,
      scope: s ? s.scope : null,
      layerFlags: s ? s.layers : null,
      transform: s ? s.transform : null,
      // the module's own layers (its flags), the country and the provinces it drew, the links,
      // and the paints it recorded — read from its snapshot, never re-derived here
      layers: s && s.layers ? Object.keys(s.layers).length : 0,
      land: s ? s.land : 0,
      links: s ? (s.links || []).length : 0,
      circles: rows.length,
      sites: rows.length,
      fills: rows.map((row) => row.fill),
      siteFills: rows.map((row) => row.fill),
      labels: s ? (s.links || []).map((link) => link.label) : [],
      pending: s ? (s.pending || []).length : 0,
      messages: s ? (s.messages || []).map((mark) => mark.code) : [],
      events: s ? (s.events || []).map((ring) => ring.code) : [],
      price: s ? s.price : null,
      tip: mapTip(),
      // the page's own ring, on the overlay beside the canvas
      marks: marks ? marks.children.map((node) => `${node.getAttribute('class')}:${node.getAttribute('data-code')}`) : [],
    };
  })(),
  chart: {
    title: content('chart-title'),
    // FRONT-1: the subtitle carries the clock's own day, beside the title's axis span.
    asof: content('chart-asof'),
    children: byId.get('chart').children.length,
    labels: byId.get('chart').children.filter((n) => n.tagName === 'TEXT').map((n) => n.textContent),
  },
  caption: content('caption'),
  briefs: {mounts: briefs.mounts, calls: briefs.calls},
});

/* The state the page opens in, before any promise has run. */
const initial = {brief: content('brief-text').text, loading: mapState('loading'), pricing: mapState('pricing')};

let stage1 = null;
if (HOLD_NODE) {
  /* Stage 1: the node file is still in flight. The page has drawn when its own loading marker is
     gone and the outline is on the map; that is the state read here, tooltip included. */
  await until(() => !mapState('loading') && mapRows().length > 0 && !!content('brief-text').text);
  if (STAGE_INTERACT) {
    /* A user who acts before the node file lands: pick Luzon and step the replay on. */
    const luzon = GROUPS['.grids button'].find((node) => node.dataset.grid === 'CLUZ');
    if (luzon) luzon.dispatch('click');
    const forward = GROUPS['[data-step]'].find((node) => node.dataset.step === '1');
    if (forward) forward.dispatch('click');
  }
  if (STAGE_MAP) stageMapActions();
  hoverFirstSite();
  stage1 = snapshot();
  releaseNode();
  /* Stage 2: the page's own `pricing` marker is gone when the site layer has been drawn. */
  await until(() => !mapState('pricing'));
} else {
  await until(() => !!content('caption').text && health.length > 0);
}
/* The tooltip is the module's own and a canvas holds no element per site, so the pointer is put
   on the first site the module has painted. For a held run the pointer is moved once, at stage
   1, and never again: the page hands the node file's layer to the canvas it already mounted
   (`setNodes`), so the open tip is the page's own tooltip and must show the new figures itself —
   the report's final `tip` is that same tooltip, updated. A finished page that never held the
   node file gets the one hover here. */
if (!HOLD_NODE) hoverFirstSite();

const desk = document.querySelector('.desk');
// The page writes its own reason into the desk when a fetch fails; report that reason.
if (!desk || /could not be loaded/.test(desk.innerHTML)) {
  fail('the page did not finish loading the replay data: ' + (desk ? desk.innerHTML : 'no desk'));
}

/* ATG-8: the two composed files and the vector table are asked for after the first paint, so
   their answers settle after the state above was reached. A bounded settle (timers only, no
   waiting on anything external) lets that stage finish before the report is read, so what it
   records is the page as the user gets it and not a frame halfway through it. */
for (let turn = 0; turn < 20; turn += 1) await new Promise((resolve) => setTimeout(resolve, 0));

/* ATG-8: one step of the replay and one grid change on the finished page, before the state is
   read, so the calls the panel's controller received are in the report beside the page state
   they produced. */
if (STEP) {
  const forward = GROUPS['[data-step]'].find((node) => node.dataset.step === '1');
  if (forward) forward.dispatch('click');
  const luzon = GROUPS['.grids button'].find((node) => node.dataset.grid === 'CLUZ');
  if (luzon) luzon.dispatch('click');
}

console.log(JSON.stringify({
  ok: true,
  width: WIDTH,
  hash: HASH,
  stamp: STAMP || null,
  fetched,
  health,
  healthFailed: HEALTH_FAIL,
  nodeFailed: NODE_FAIL,
  held: HOLD_NODE,
  initial,
  stage1,
  ...snapshot(),
  title: document.title,
  replaced: replaced.slice(-1),
  errors,
}, null, 1));
