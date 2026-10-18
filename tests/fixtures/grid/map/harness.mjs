/* Run the map canvas module (src/grid/map.js) against a baked-data directory and print what it
   drew and what its gestures did, as one JSON object on stdout. Offline: no browser, no
   network, no library.

   The shim below implements exactly the DOM and canvas-2D surface `map.js` uses and throws on
   anything else, so a gap in the shim is a failure rather than a silent pass. It is an
   approximation of a browser: it proves the module executes, paints the layers it claims, and
   resolves its gestures under the transform it reports — not that the drawing looks right. The
   math checks re-run `GridMap.math` directly, and tests/test_grid_map.py compares its output
   with the same formulas re-derived in Python.

     node tests/fixtures/grid/map/harness.mjs --root . --data tests/fixtures/grid/map/data \
          --width 1280 --height 700 [--clock '2026-09-21 13:40:00'] [--no-canvas]

   `--no-canvas` gives the document a canvas element with no `getContext`, which is the text
   fallback's path: the report then carries `fallback.lines` and no painting.
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
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/map/data')));
const WIDTH = Number(arg('width', '1280'));
const HEIGHT = Number(arg('height', '700'));
const CLOCK = arg('clock', '2026-09-21 13:40:00');
const NO_CANVAS = argv.lastIndexOf('--no-canvas') >= 0;

const read = (name) => JSON.parse(readFileSync(path.join(DATA, name), 'utf8'));
const data = {
  geo: read('ph.geojson'), sites: read('sites.json'), hvdc: read('hvdc.json'),
  advisories: read('advisories.json'), events: read('events.json'),
  nodes: read('nodes-2026-09-21.json'), clock: CLOCK, grid: null,
};

/* ---------- a small DOM, canvas included ---------- */
const escapeText = (text) => String(text).replace(/[&<>"]/g, (c) =>
  ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

class Shim {
  constructor(tag, doc) {
    this.tagName = tag.toUpperCase();
    this.attrs = {};
    this.children = [];
    this.parentNode = null;
    this.listeners = {};
    this.style = {};
    this.text = '';
    this.html = null;
    this.ownerDocument = doc;
    this.rect = {left: 0, top: 0, width: 0, height: 0};
  }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  removeAttribute(name) { delete this.attrs[name]; }
  hasAttribute(name) { return name in this.attrs; }
  get hidden() { return 'hidden' in this.attrs; }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  removeChild(child) {
    const at = this.children.indexOf(child);
    if (at >= 0) this.children.splice(at, 1);
    return child;
  }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  removeEventListener(type, fn) {
    const list = this.listeners[type] || [];
    const at = list.indexOf(fn);
    if (at >= 0) list.splice(at, 1);
  }
  dispatch(type, event = {}) {
    const e = Object.assign({type, target: this}, event);
    for (const fn of (this.listeners[type] || []).slice()) fn(e);
  }
  get textContent() { return this.text + this.children.map((child) => child.textContent).join(''); }
  set textContent(value) { this.text = String(value); this.html = null; this.children = []; }
  get innerHTML() { return this.html === null ? escapeText(this.text) : this.html; }
  set innerHTML(value) { this.html = String(value); this.children = []; }
  getBoundingClientRect() { return this.rect; }
  descendants() { return this.children.flatMap((child) => [child, ...child.descendants()]); }
}

/* The 2D context records every paint call; a member the module does not need is an error, so
   the shim cannot silently swallow a method the module starts to use. */
const STYLE = ['fillStyle', 'strokeStyle', 'lineWidth', 'globalAlpha', 'font', 'textAlign', 'textBaseline', 'lineJoin'];
function makeContext() {
  const style = {fillStyle: '#000', strokeStyle: '#000', lineWidth: 1, globalAlpha: 1,
    font: '10px sans-serif', textAlign: 'start', textBaseline: 'alphabetic', lineJoin: 'miter'};
  const ops = [];
  const impl = {
    setTransform: (...a) => ops.push({op: 'setTransform', args: a}),
    clearRect: (...a) => ops.push({op: 'clearRect', args: a}),
    fillRect: (...a) => ops.push({op: 'fillRect', fill: style.fillStyle, args: a}),
    beginPath: () => ops.push({op: 'beginPath'}),
    moveTo: (...a) => ops.push({op: 'moveTo', args: a}),
    lineTo: (...a) => ops.push({op: 'lineTo', args: a}),
    closePath: () => ops.push({op: 'closePath'}),
    quadraticCurveTo: (...a) => ops.push({op: 'quadraticCurveTo', args: a}),
    arc: (x, y, r, a0, a1) => ops.push({op: 'arc', x, y, r, args: [x, y, r, a0, a1]}),
    fill: () => ops.push({op: 'fill', fill: style.fillStyle}),
    stroke: () => ops.push({op: 'stroke', stroke: style.strokeStyle, lineWidth: style.lineWidth}),
    fillText: (text, x, y) => ops.push({op: 'fillText', text: String(text), x, y, fill: style.fillStyle}),
    setLineDash: (dash) => ops.push({op: 'setLineDash', args: [dash]}),
  };
  const context = new Proxy(impl, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop in style) return style[prop];
      throw new Error('shim: canvas context member not implemented: ' + String(prop));
    },
    set(target, prop, value) {
      if (prop in style) { style[prop] = value; return true; }
      throw new Error('shim: canvas context property not implemented: ' + String(prop));
    },
  });
  return {context, ops};
}

const canvases = [];
const contexts = new Map();
const document = {
  createElement(tag) {
    const node = new Shim(tag, document);
    if (tag === 'canvas') {
      node.rect = {left: 0, top: 0, width: WIDTH, height: HEIGHT};
      if (!NO_CANVAS) {
        const made = makeContext();
        contexts.set(node, made);
        node.getContext = (kind) => (kind === '2d' ? made.context : null);
      }
      canvases.push(node);
    }
    return node;
  },
};

/* ---------- the module under test ---------- */
const fetches = [];
const sandbox = {
  window: {devicePixelRatio: 1},
  fetch: (url) => { fetches.push(String(url)); throw new Error('the map module may not fetch: ' + url); },
  console: {log: () => {}, warn: () => {}, error: (m) => errors.push(String(m))},
};
let GridMap = null;
try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/map.js'), 'utf8'), sandbox, {filename: 'src/grid/map.js'});
  GridMap = sandbox.GridMap;
} catch (error) {
  fail('the module threw while loading: ' + (error && error.stack ? error.stack : error));
}
if (!GridMap || typeof GridMap.mount !== 'function') fail('the module did not expose GridMap.mount');

const math = GridMap.math;
const clicked = {sites: [], links: []};
const container = new Shim('div', document);
container.rect = {left: 0, top: 0, width: WIDTH, height: HEIGHT};

let map = null;
try {
  map = GridMap.mount(container, data, {
    onSite: (code) => clicked.sites.push(code),
    onLink: (id) => clicked.links.push(id),
  });
} catch (error) {
  fail('mount threw: ' + (error && error.stack ? error.stack : error));
}

/* ---------- finding the elements the module built ---------- */
const hasClass = (node, name) => String(node.getAttribute('class') || '').split(/\s+/).includes(name);
const byClass = (parent, name) => parent.children.find((n) => hasClass(n, name)) || null;
const root = map.root;
const chipsRow = byClass(root, 'gmap-chips');
const stage = byClass(root, 'gmap-stage');
const chip = (name, value) => chipsRow.children.find((b) => (b.getAttribute(name) || '') === value);
const zoomButton = (label) => byClass(stage, 'gmap-zoom').children.find((b) => b.textContent === label);
const canvas = canvases[0] || null;
const paintOf = () => (canvas && contexts.has(canvas) ? contexts.get(canvas).ops : []);
const tipNode = byClass(stage, 'gmap-tip');
// UX-3: a click on a place of several assets pins their list in its own element
const pinNode = byClass(stage, 'gmap-pin');
const legendNode = byClass(stage, 'gmap-legend');
// UX-3: the legend nests its title in a head row and its readings behind a key toggle, so a part
// is looked for anywhere inside it.
const legendPart = (name) => (legendNode ? legendNode.descendants().find((n) => hasClass(n, name)) || null : null);

/* ---------- the helpers the script uses ---------- */
const screenOf = (code) => {
  const site = data.sites.find((s) => s.s === code);
  const T = map.transform();
  const p = math.toScreen(T, math.plane(site.lon, site.lat));
  return {x: p[0], y: p[1]};
};
const pointer = (type, x, y, id = 1) => canvas.dispatch(type, {pointerId: id, button: 0, clientX: x, clientY: y});
const clickAt = (x, y) => { pointer('pointerdown', x, y); pointer('pointerup', x, y); };
const clickSite = (code) => {
  const p = screenOf(code);
  const t = transformOf();
  clickAt(p.x, p.y);
  return {at: [Number(p.x.toFixed(3)), Number(p.y.toFixed(3))], got: clicked.sites[clicked.sites.length - 1] || null, t};
};
const round = (v) => Number(v.toFixed(9));
const transformOf = () => {
  const T = map.transform();
  return T && {k: round(T.k), fx: round(T.fx), fy: round(T.fy), w: T.w, h: T.h};
};
const legendReport = () => ({
  title: (() => { const t = legendPart('gmap-legend-title'); return t ? t.textContent : null; })(),
  ticks: (() => { const t = legendPart('gmap-ticks'); return t ? t.children.map((n) => n.textContent) : []; })(),
  ramp: (() => { const r = legendPart('gmap-ramp'); return r ? r.style.background : null; })(),
  range: (() => { const r = legendPart('gmap-range'); return r ? r.textContent : null; })(),
  asof: (() => { const a = legendPart('gmap-asof'); return a ? a.textContent : null; })(),
  kinds: (() => { const k = legendPart('gmap-kinds'); return k ? k.children.filter((li) => !hasClass(li, 'gmap-asof') && !hasClass(li, 'gmap-explain')).map((li) => li.textContent) : []; })(),
});

/* ---------- the scripted run (only with a canvas) ---------- */
const report = {ok: true, width: WIDTH, height: HEIGHT, clock: CLOCK, noCanvas: NO_CANVAS, fetches};
if (!NO_CANVAS) {
  const arcs = () => paintOf().filter((o) => o.op === 'arc');
  const opened = map.snapshot();

  /* the drawing as the module reports it, and the paint calls the context recorded (the whole
     log: the module drew once inside mount() before this script could watch a single call) */
  report.draw = {
    land: opened.land, priced: opened.priced, price: opened.price,
    located: opened.located, pending: opened.pending, links: opened.links,
    messages: opened.messages, events: opened.events, clusters: opened.clusters, markers: opened.markers,
    notices: opened.notices, severity: opened.severity, scale: opened.scale, geo: opened.geo,
    arcs: arcs().map((o) => ({x: round(o.x), y: round(o.y), r: round(o.r)})),
    texts: paintOf().filter((o) => o.op === 'fillText').map((o) => o.text),
    /* UX-3: the paints of the place marks, the pending cells and the notice glyphs, read as the
       arcs each layer drew (a clipped arc count would hide a layer that stopped drawing) */
    arcsAt: arcs().map((o) => [round(o.x), round(o.y)]),
    fills: paintOf().filter((o) => o.op === 'fill').map((o) => o.fill),
    legend: legendReport(),
    snapshotLegend: opened.legend,
  };

  /* the transform under each control and gesture */
  const transforms = {open: transformOf()};
  zoomButton('+').dispatch('click');
  transforms.zoomIn = transformOf();
  zoomButton('+').dispatch('click');
  transforms.zoomIn2 = transformOf();
  zoomButton('−').dispatch('click');
  transforms.zoomOut = transformOf();
  zoomButton('Fit').dispatch('click');
  transforms.fit = transformOf();
  canvas.dispatch('wheel', {deltaY: -240, clientX: WIDTH / 2, clientY: HEIGHT / 2});
  transforms.wheel = transformOf();
  pointer('pointerdown', 100, 100); pointer('pointermove', 130, 120); pointer('pointerup', 130, 120);
  transforms.pan = transformOf();
  /* pinch: two pointers 100 px apart, drawn to 200 px apart (two moves, so two anchored steps) */
  pointer('pointerdown', 300, 300, 1); pointer('pointerdown', 400, 300, 2);
  pointer('pointermove', 250, 300, 1); pointer('pointermove', 450, 300, 2);
  pointer('pointerup', 250, 300, 1); pointer('pointerup', 450, 300, 2);
  transforms.pinch = transformOf();
  zoomButton('Fit').dispatch('click');
  /* pinch → one finger: the survivor's own travel pans, not the distance back to where the
     pinch was last measured (round 2 of the review: 51 px of pan for 1 px of movement) */
  pointer('pointerdown', 300, 300, 1); pointer('pointerdown', 400, 300, 2);
  pointer('pointermove', 250, 300, 1); pointer('pointermove', 450, 300, 2);
  pointer('pointerup', 250, 300, 1);
  const pinchLift = {afterLift: transformOf()};
  pointer('pointermove', 451, 300, 2);
  pinchLift.afterOne = transformOf();
  pointer('pointerup', 451, 300, 2);
  zoomButton('Fit').dispatch('click');
  /* a two-finger tap is never a click, even with a site under the fingers: both taps land on
     the site's own dot, so whichever finger lifts last would open it if the gesture counted */
  const clickLeyre = screenOf('SYN-LEY-1');
  const clicksBeforeTap = clicked.sites.length;
  pointer('pointerdown', clickLeyre.x, clickLeyre.y, 1);
  pointer('pointerdown', clickLeyre.x + 6, clickLeyre.y, 2);
  pointer('pointerup', clickLeyre.x, clickLeyre.y, 1);
  pointer('pointerup', clickLeyre.x + 6, clickLeyre.y, 2);
  pinchLift.clicksAfterTwoFingerTap = clicked.sites.length - clicksBeforeTap;
  pinchLift.twoFingerTapPoint = [round(clickLeyre.x), round(clickLeyre.y)];
  zoomButton('Fit').dispatch('click');
  /* one finger, one click: the same point tapped alone still opens the site */
  pinchLift.oneFingerTap = clickSite('SYN-LEY-1').got;
  zoomButton('Fit').dispatch('click');

  /* a click on a drawn site resolves to that site after each transform */
  zoomButton('+').dispatch('click');
  const clickZoomIn = clickSite('SYN-LUZ-1');
  zoomButton('−').dispatch('click');
  const clickZoomOut = clickSite('SYN-MIN-1');
  zoomButton('Fit').dispatch('click');
  const clickFit = clickSite('SYN-LEY-1');
  pointer('pointerdown', 200, 200); pointer('pointermove', 260, 240); pointer('pointerup', 260, 240);
  const clickPan = clickSite('SYN-CALACA-1');
  zoomButton('Fit').dispatch('click');

  /* the shared position: one click each opens the stack in order */
  const stack = [clickSite('SYN-BAY-1'), clickSite('SYN-BAY-1'), clickSite('SYN-BAY-1')];
  /* the list those clicks pinned; Escape on it closes it (the keyboard's way out) */
  const pinStack = pinNode && !pinNode.hidden ? pinNode.innerHTML : null;
  pinNode.dispatch('keydown', {key: 'Escape'});
  const pinAfterEscape = pinNode.hidden;
  /* a click on a lone site opens it and pins nothing */
  clickSite('SYN-LEY-1');
  const pinAfterLone = pinNode.hidden;

  /* the tooltip */
  const sitePoint = screenOf('SYN-LEY-1');
  canvas.dispatch('pointermove', {clientX: sitePoint.x, clientY: sitePoint.y});
  const tipSite = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  const stackPoint = screenOf('SYN-STA-1');
  canvas.dispatch('pointermove', {clientX: stackPoint.x, clientY: stackPoint.y});
  const tipStack = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  canvas.dispatch('pointermove', {clientX: 1, clientY: HEIGHT - 1});
  const tipBlank = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  canvas.dispatch('pointermove', {clientX: sitePoint.x, clientY: sitePoint.y});

  /* a click on a link: the midpoint of its curve */
  const curve = math.linkCurve(math.LINK_DEFS.VISLUZ1);
  const mid = math.toScreen(map.transform(), math.curvePoint(curve, 0.5));
  const linkProbe = map.hitTest(mid[0], mid[1]);
  canvas.dispatch('pointermove', {clientX: mid[0], clientY: mid[1]});
  const tipLink = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  clickAt(mid[0], mid[1]);
  const clickLink = clicked.links[clicked.links.length - 1] || null;
  report.linkProbe = {mid: mid.map(round), hit: linkProbe.link ? linkProbe.link.id : null,
    sites: linkProbe.sites.map((d) => d.code), click: clickLink, tip: tipLink};

  /* a drag is not a click; a nudge under 3 px is */
  const sitesBeforeDrag = clicked.sites.length;
  pointer('pointerdown', 120, 120); pointer('pointermove', 140, 120); pointer('pointerup', 140, 120);
  const dragLong = clicked.sites.length - sitesBeforeDrag;
  zoomButton('Fit').dispatch('click');
  const leyre = screenOf('SYN-LEY-1');
  pointer('pointerdown', leyre.x, leyre.y); pointer('pointermove', leyre.x + 2, leyre.y); pointer('pointerup', leyre.x + 2, leyre.y);
  const dragShort = clicked.sites[clicked.sites.length - 1] || null;

  /* the chips */
  const chipCounts = () => {
    const s = map.snapshot();
    return {located: s.located.length, pending: s.pending.length, messages: s.messages.length, events: s.events.length,
      fills: s.located.map((d) => d.fill)};
  };
  const chips = {on: {layers: map.snapshot().layers, ...chipCounts()}};
  /* each layer is turned off and back on alone, so one chip's measurement is never another
     chip's state */
  const chipOff = (key) => {
    chip('data-layer', key).dispatch('click');
    const off = {pressed: chip('data-layer', key).getAttribute('aria-pressed'), ...chipCounts()};
    chip('data-layer', key).dispatch('click');
    return off;
  };
  for (const key of ['generators', 'loads', 'messages', 'events', 'interconnectors', 'prices']) {
    chips['off_' + key] = chipOff(key);
  }
  chips.restored = chipCounts();

  /* the scope chips */
  chip('data-scope', 'CLUZ').dispatch('click');
  chips.scopeLuzon = {located: map.snapshot().located.map((d) => d.code), pending: map.snapshot().pending.length,
    pressed: chip('data-scope', 'CLUZ').getAttribute('aria-pressed'), all: chip('data-scope', 'all').getAttribute('aria-pressed')};
  chip('data-scope', 'all').dispatch('click');
  chips.scopeAll = map.snapshot().located.map((d) => d.code);

  /* the clock: another priced interval, then a day the node file does not carry. At 14:00 the
     fixture states MINVIS1's flag (0: a known "not congested") and leaves VISLUZ1's unstated
     (null: unknown) — the two readings the module must keep apart. */
  const linkMidOf = (id) => {
    const c = math.linkCurve(math.LINK_DEFS[id]);
    return math.toScreen(map.transform(), math.curvePoint(c, 0.5));
  };
  map.setClock('2026-09-21 14:00:00');
  const at1400 = map.snapshot();
  const midMinvis = linkMidOf('MINVIS1');
  canvas.dispatch('pointermove', {clientX: midMinvis[0], clientY: midMinvis[1]});
  const tipLinkKnown = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  const midVisluz = linkMidOf('VISLUZ1');
  canvas.dispatch('pointermove', {clientX: midVisluz[0], clientY: midVisluz[1]});
  const tipLinkUnknown = tipNode && !tipNode.hidden ? tipNode.innerHTML : null;
  map.setClock('2026-09-22 07:30:00');
  const atSep22 = map.snapshot();
  const legendSep22 = legendReport();
  map.setClock(CLOCK);
  const backToClock = map.snapshot();

  report.gestures = {transforms, pinchLift, clicks: {zoomIn: clickZoomIn, zoomOut: clickZoomOut, fit: clickFit, pan: clickPan,
    stack: stack.map((s) => s.got), link: clickLink, dragLongClicks: dragLong, dragShort: dragShort}};
  report.pin = {stack: pinStack, closedByEscape: pinAfterEscape, loneClickPins: !pinAfterLone};
  report.hover = {site: tipSite, stack: tipStack, blank: tipBlank, link: tipLink,
    link1400Known: tipLinkKnown, link1400Unknown: tipLinkUnknown};
  report.chips = chips;
  report.clocks = {
    at1340: {priced: opened.priced, price: opened.price, fills: opened.located.map((d) => d.fill),
      messages: opened.messages.length, events: opened.events.length, legendRange: opened.legend.range, legendAsOf: opened.legend.asof},
    at1400: {priced: at1400.priced, price: at1400.price, fills: at1400.located.map((d) => d.fill),
      messages: at1400.messages.map((m) => m.id), events: at1400.events.map((e) => e.id), legendRange: at1400.legend.range,
      legendAsOf: at1400.legend.asof,
      links: at1400.links.map((l) => ({id: l.id, congested: l.congested, marks: l.marks, flow: l.flow, label: l.label}))},
    atSep22: {priced: atSep22.priced, price: atSep22.price, fills: atSep22.located.map((d) => d.fill),
      allUnknown: atSep22.located.every((d) => d.fill === math.UNKNOWN_FILL),
      messages: atSep22.messages.length, events: atSep22.events.length,
      legendRange: atSep22.legend.range, legendTicks: legendSep22.ticks},
    back: {priced: backToClock.priced, clock: backToClock.clock},
  };

  /* the modules' own math, called directly */
  const T = math.fitTransform(1280, 700);
  const anchorPoint = [420, 260];
  const anchorBefore = math.worldOf(T, anchorPoint[0], anchorPoint[1]);
  const zoomed = math.zoomAt(T, 1.25, anchorPoint[0], anchorPoint[1]);
  const anchorAfter = math.worldOf(zoomed, anchorPoint[0], anchorPoint[1]);
  const target = data.sites.find((s) => s.s === 'SYN-LUZ-1');
  const at = math.toScreen(T, math.plane(target.lon, target.lat));
  const stackPointMath = math.toScreen(T, math.plane(123.42, 10.90));
  const linkMid = math.toScreen(T, math.curvePoint(math.linkCurve(math.LINK_DEFS.MINVIS1), 0.5));
  report.math = {
    fit1280x700: {k: round(T.k), fx: round(T.fx), fy: round(T.fy), w: T.w, h: T.h},
    fit390x585: (() => { const F = math.fitTransform(390, 585); return {k: round(F.k), fx: round(F.fx), fy: round(F.fy), w: F.w, h: F.h}; })(),
    roundTrip: (() => { const p = math.plane(121.0, 14.6); const s = math.toScreen(T, p); const back = math.worldOf(T, s[0], s[1]); return {world: p.map(round), screen: s.map(round), back: back.map(round)}; })(),
    anchor: {before: anchorBefore.map(round), after: anchorAfter.map(round)},
    /* the pinch anchor: the world point under the pair's previous midpoint lands under the new
       midpoint (zoom about the previous midpoint, then the midpoint's travel as a pan) */
    pinchAnchor: (() => {
      const prev = {d: 100, mid: [350, 300]}, next = {d: 200, mid: [325, 300]};
      const moved = math.pinchTransform(T, prev, next);
      return {was: math.worldOf(T, prev.mid[0], prev.mid[1]).map(round),
        now: math.worldOf(moved, next.mid[0], next.mid[1]).map(round), k: round(moved.k)};
    })(),
    /* the pointer bookkeeping, called directly: the review's own sequence's drag positions —
       down at (300,300), second down at (400,300), the pair drawn out to (250,300)/(450,300),
       then the survivor's drag re-anchored where that finger is */
    drag: {
      afterFirstDown: math.dragDown(null, [300, 300], 1),
      afterSecondDown: math.dragDown(math.dragDown(null, [300, 300], 1), [400, 300], 2),
      afterLift: math.dragUp(math.dragDown(math.dragDown(null, [300, 300], 1), [400, 300], 2), [450, 300]),
      liftedWithNoSurvivor: math.dragUp(math.dragDown(null, [100, 100], 1), null),
      dragKeptAcrossASecondPointer: math.dragDown({x: 100, y: 100, moved: 20, last: {x: 100, y: 100}}, [150, 150], 2),
    },
    /* one link's readings at one interval: true/false are the record's states, null its silence */
    congestion: {
      atClock: [math.congestionAt(data.hvdc.links.MINVIS1, data.hvdc.t.indexOf(CLOCK)),
        math.congestionAt(data.hvdc.links.VISLUZ1, data.hvdc.t.indexOf(CLOCK))],
      at1400: [math.congestionAt(data.hvdc.links.MINVIS1, data.hvdc.t.indexOf('2026-09-21 14:00:00')),
        math.congestionAt(data.hvdc.links.VISLUZ1, data.hvdc.t.indexOf('2026-09-21 14:00:00'))],
      knownTrue: math.congestionAt({flow: [1], congested: [1]}, 0),
      knownFalse: math.congestionAt({flow: [1], congested: [0]}, 0),
      nullFlag: math.congestionAt({flow: [1], congested: [null]}, 0),
      shortFlags: math.congestionAt({flow: [1], congested: []}, 0),
      noFlags: math.congestionAt({flow: [1]}, 0),
      noLink: math.congestionAt(null, 0),
      noInterval: math.congestionAt(data.hvdc.links.MINVIS1, null),
      fixtureUnknowns: (() => {
        const out = [];
        for (const id of ['MINVIS1', 'VISLUZ1']) {
          const link = data.hvdc.links[id];
          data.hvdc.t.forEach((stamp, i) => { if (math.congestionAt(link, i) === null) out.push(id + '@' + stamp); });
        }
        return out;
      })(),
    },
    flow: {
      zero: math.flowAt({flow: [0]}, 0),
      nullCell: math.flowAt({flow: [null]}, 0),
      shortList: math.flowAt({flow: []}, 0),
      noList: math.flowAt({congested: [0]}, 0),
      noLink: math.flowAt(null, 0),
      noInterval: math.flowAt(data.hvdc.links.MINVIS1, null),
    },
    siteAtLuzon: math.siteAt(T, data.sites, at[0], at[1]).map((d) => d.code),
    siteAtStack: math.siteAt(T, data.sites, stackPointMath[0], stackPointMath[1]).map((d) => d.code),
    /* PP-B5: the unlocated sites are listed apart, never drawn: the module's own order, and the
       hit test's shape (no pending key: nothing on the canvas stands for one) */
    unplacedCodes: math.unplacedSites(data.sites, null).map((s) => s.s),
    unplacedLuzon: math.unplacedSites(data.sites, 'CLUZ').map((s) => s.s),
    hitKeys: Object.keys(math.hitTest(T, data, {scope: null, layers: {generators: true, loads: true, interconnectors: true}}, 10, 10)),
    linkAtMid: math.linkAt(T, math.LINK_DEFS, linkMid[0], linkMid[1]).id,
    linkAtFar: math.linkAt(T, math.LINK_DEFS, linkMid[0] + 40, linkMid[1] + 40),
    namedBy: data.advisories.map((a) => ({id: a.id, site: (math.sitesNamedBy(a, data.sites, data.events).site || {}).s || null,
      candidates: math.sitesNamedBy(a, data.sites, data.events).candidates.length})),
    radiusOf: data.sites.filter((s) => s.p !== 'placeholder').map((s) => ({code: s.s, r: round(math.radiusOf(s))})),
    /* UX-3: the price scale of the drawn prices at the clock, and the scale's own functions on
       the inputs the Python file re-derives */
    scaleAtClock: (() => {
      const row = data.nodes.t.indexOf(CLOCK);
      const values = data.sites.filter((s) => s.p !== 'placeholder').map((s) => data.nodes.lmp[row][data.nodes.sites.indexOf(s.s)]).filter((v) => v != null);
      const sc = math.priceScale(values);
      return {knots: sc.knots, median: sc.median, n: sc.n, atCeil: sc.atCeil,
        colours: values.map((v) => [v, math.colorAt(sc, v)]), ramp: math.rampGradient(sc), ticks: sc.knots.map(math.tickLabel)};
    })(),
    scales: {
      flat: math.priceScale([4000, 4000, 4000]).knots,
      capped: math.priceScale([32000, 32000, 32000, 32000, 50000]).knots,
      negative: math.priceScale([-2000, -500, 100, 300, 900, 1500]).knots,
      empty: math.priceScale([]),
      mix: [[math.P_DARK[2], math.P_DARK[3], 0.5], [math.P_DARK[0], math.P_DARK[4], 0.25], [math.P_DARK[1], math.P_DARK[2], 0.8]]
        .map(([a, b, t]) => math.mixOklab(a, b, t)),
    },
    colorNull: math.colorAt(null, null),
    clustersFit: math.clusterSites(T, data.sites).map((c) => ({codes: c.codes, r: round(c.r), x: round(c.x), y: round(c.y)})),
    regionInfo: ['Central Luzon (Region III)', 'CALABARZON (Region IV-A)', 'MIMAROPA (Region IV-B)', 'Western Visayas (Region VI)',
      'Dinagat Islands (Region XIII)', 'Northern Mindanao (Region X)', 'National Capital Region',
      'Cordillera Administrative Region (CAR)', 'Autonomous Region in Muslim Mindanao (ARMM)', 'Nowhere', null].map((r) => math.regionInfo(r)),
    severity: data.advisories.map((a) => [a.id, math.severityOf(a)]).concat([['derate', math.severityOf({kind: 'trip', text: 'Unit derated to 40 MW'})]]),
  };
} else {
  /* the text fallback */
  const part = byClass(stage, 'gmap-fallback');
  report.fallback = {lines: part ? part.children.map((n) => n.textContent) : []};
  /* there is no canvas and so no transform: a hit test answers with nothing rather than throwing */
  report.fallbackHit = map.hitTest(10, 10);
  report.fallbackAfterClock = (() => {
    map.setClock('2026-09-22 07:30:00');
    const p = byClass(stage, 'gmap-fallback');
    return p ? p.children.map((n) => n.textContent) : [];
  })();
}

report.clicks = {sites: clicked.sites, links: clicked.links};
report.errors = errors;
console.log(JSON.stringify(report, null, 1));
