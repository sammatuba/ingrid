/* InGRID map canvas (ATG-6, reworked by UX-3 for the map-first desk). One self-contained
   module with no library: it draws the country, its regions and provinces, the sites, the two
   undersea links, the operator notices and the events on a canvas 2D element, and it owns pan,
   zoom, fit, pinch, hit testing, the popover, the layer chips and the legend. It reads only the
   baked data its caller hands to `mount` — it makes no request of its own, calls no model and no
   service, and hard-codes no figure the bake does not carry.

   Contract (docs/work/atg/map.md records the first version; the page mounts it once and hands
   the node file's layer over with `setNodes`):

     const map = GridMap.mount(container, data, callbacks);

   `data` — the baked files the page already fetched, passed by reference:
     { geo, sites, hvdc, advisories, events, nodes, clock, grid }
       geo        ph.geojson            (the country outline and the provinces; a province may
                                         carry `region`, which draws the region boundaries)
       sites      sites.json            (every site: code, kind, grid, capacity, position)
       hvdc       hvdc.json             (the two links: flow and congestion per interval)
       advisories advisories.json       (the operator messages; optional)
       events     events.json           (the reviewable events; optional)
       nodes      nodes-<day>.json      (the one day of per-site prices; optional)
       clock      'YYYY-MM-DD HH:MM:SS' the replay interval to draw (optional)
       grid       null | 'CLUZ' | 'CVIS' | 'CMIN'   the initial map scope (optional)
   `callbacks` — the page's own openers: { onSite(code), onLink(id) }, both optional.
   A click resolves under the current transform; on a position several sites share, the click
   cycles that position's stack, so every site standing there can be opened (research §2.4a: 401
   of the real bake's 492 located sites stand on a shared position). The same click pins the
   popover that lists every asset of that place.

   The returned object (nothing here fetches):
     setClock(stamp)  redraw at another replay interval      setScope(grid|null)  (eased)
     setNodes(nodes)  hand over the node file's layer after the mount; layers, scope, transform
                      and an open popover all stay
     setInsets({left, top, right, bottom})  the px the page's overlays cover: Fit and a scope
                      centre the country in the box that stays visible
     fit()  zoomIn()  zoomOut()  panBy(dx, dy)               resize()  (a box change redraws too)
     transform()      the current {k, fx, fy, w, h}          legend()  the legend's readings
     scale()          the price scale of the last draw       priceColor(v)  its colour for v
     hitTest(sx, sy)  {sites, link} under the transform, in the drawn set
     snapshot()       the read-only record of the last draw (counts, positions and fills of
                      everything painted) — the surface the fixture harness and tests read
     destroy()        removes every listener and the element it built
     canvas, root     the elements it built inside `container`

   Pure math: `GridMap.math` carries the transform, the pointer bookkeeping, the hit testing, the
   price scale and the clustering as pure functions. tests/test_grid_map.py re-derives them in
   Python from the same constants and compares the two implementations.

   Decisions, with their reasons:
     - An unlocated site is never drawn at a coordinate, at any zoom (PP-B5). The canvas paints
       located sites only; the unlocated ones are carried in the snapshot as `pending` rows (code,
       kind, grid, capacity, price and its colour, no position), and the page lists them apart,
       by grid (the desk's "Unplaced" chip). The matrix in open sea that drew them before sat
       over the page's overlays and pushed the country right of centre, so it is gone.
     - An approximate site (`p: "approximate"`, build_data's display placement near the most
       central located site of its area prefix and grid) is drawn, never as a location: a hollow
       ring with a dashed outline in its price colour, sized by capacity like a dot. It joins the
       place its position falls in only after every located site is placed, so the located
       clustering never changes. The hover and the list say it is approximate. Nothing that reads a
       position as a fact (the province grid fallback, the state card's every-located scale) reads
       it. The Plants and Load nodes layers count it, and the legend's key says so.
     - Fit frames the archipelago itself (FIT, the outline's own extent), not BOUNDS, which is
       the plane's origin only. With the page's insets the country is centred in the part of the
       map its overlays leave free.
     - One price scale, data-adaptive (UX-3): the five knots are the 5th, 25th, 50th, 75th and
       95th percentiles of the drawn located prices at the clock, clamped to 0 and 32,000, and the
       five colours are the theme's --p0 to --p4. Between knots the colour is interpolated in
       OKLab, a perceptual space, so equal steps look equal. The median is the neutral centre, so
       a grid's internal spread shows (the fixed 0 to 32,000 stops drew Luzon all one colour).
       The dots, the cluster marks, the legend ramp, the legend ticks and the page's state-card
       dots all come from that one scale object.
     - The top tick is a saturation point, not a cap: the node series is uncapped (research
       §2.4c, ₱753,290 on the real bake), so a knot at 32,000 prints `32,000+`.
     - Sites at one place cluster into one mark sized by the place's registered generating MW and
       coloured by the median price there, with a count badge. The click still resolves the
       per-site stack (siteAt), so the reviewed stack order holds.
     - The congestion mark sits at the curve's midpoint and means "congested at the clock
       interval". A flag the record does not state stays unknown: no mark, and the label, the
       popover and the fallback say the congestion is unknown rather than "not congested".
     - Notices are drawn by severity (alert triangle, warning diamond, info circle) at the one site
       they name, or at their grid when they name none. Only an alert carries the one slow ring.
     - Pinch zooms about the pair's previous midpoint; the drag re-anchors whenever the set of
       pointers changes (the reviewed rounds' fixes, unchanged).
*/
(() => {
  'use strict';

  // ------------------------------------------------------------------ constants
  const BOUNDS = { w: 112.9, e: 127.2, s: 4.4, n: 21.2 };
  const COSLAT = Math.cos((12.5 * Math.PI) / 180);
  const PAD = 14;                 // px kept clear around the fitted country, as the page does
  const KMAX_FACTOR = 64;         // the ceiling, in fitted scales (research §3.2: 64 x fit)
  const WHEEL_SCALE = 480;        // k *= 2 ** (-deltaY / 480), per wheel event
  const BUTTON_FACTOR = 1.25;     // the + and - buttons, about the canvas centre
  const DRAG_CLICK_PX = 3;        // a drag shorter than this is a click
  const HIT_SLOP = 4;             // px added to a dot's own drawn radius
  const LINK_HIT = 6;             // px: a link is hit within this of its sampled curve
  const LINK_SAMPLES = 32;        // the quadratic is sampled, not projected
  // The box Fit frames: the archipelago's own extent with a hair of sea (the outline runs from
  // 116.96 to 126.62 E and 4.66 to 21.12 N). BOUNDS stays the plane's origin.
  const FIT = { w: 116.9, e: 126.7, s: 4.6, n: 21.2 };
  const MSG_WINDOW_MIN = 60;      // a message marks its site for 60 minutes after it is posted
  const EVENT_WINDOW_MIN = 90;    // an event marks its site for 90 minutes (the page's window)
  const GRID_NOTICE_MIN = 240;    // a grid alert or warning stands 4 hours (the overview's window)
  const LOAD_RADIUS = 1.8;
  const CLUSTER_PX = 9;           // sites closer than this on screen share one mark
  // The price scale: knots at these quantiles of the drawn prices, clamped to [PRICE_FLOOR, PRICE_CEIL].
  const SCALE_Q = [0.05, 0.25, 0.5, 0.75, 0.95];
  const PRICE_FLOOR = 0;
  const PRICE_CEIL = 32000;
  const MIN_SPAN = 200;           // ₱: a flatter spread is widened about its median
  // --p0 .. --p4 of the dark theme; the theme's own tokens replace them at draw time.
  const P_DARK = ['#3b6fd9', '#6fb0e8', '#d9e2ea', '#f2b134', '#ff5a5a'];
  const UNKNOWN_FILL = '#3a4552';    // a price the node file does not state
  const PRICES_OFF_FILL = '#6b7785'; // the prices layer is off
  // The base map follows the shell's theme: every colour below is read from its tokens at draw
  // time (the dark values stay as the fallback where no shell is loaded).
  const T0 = {
    sea: '#0c1219', land: '#161e28', landEdge: '#263243', province: '#1d2733', label: '#e6ebf1',
    text2: '#b4bfcc', muted: '#7d8a99', faint: '#556170', panel: '#10151c', accent: '#7cc4ff',
    bad: '#ff6b6b', warn: '#f2b134', ok: '#3ccf8e', unknown: UNKNOWN_FILL, p: P_DARK.slice(),
  };
  let C = Object.assign({}, T0);
  function readTheme() {
    if (typeof document === 'undefined' || typeof getComputedStyle !== 'function' || !document.documentElement) return;
    const cs = getComputedStyle(document.documentElement);
    const v = (name, fallback) => (cs.getPropertyValue(name) || '').trim() || fallback;
    C = {
      sea: v('--sea', T0.sea), land: v('--land', v('--panel', T0.land)), landEdge: v('--land-edge', v('--rule-strong', T0.landEdge)),
      province: v('--rule', T0.province), label: v('--text', T0.label), text2: v('--text-2', T0.text2),
      muted: v('--muted', T0.muted), faint: v('--faint', T0.faint), panel: v('--panel', T0.panel),
      accent: v('--accent', T0.accent), bad: v('--bad', T0.bad), warn: v('--warn', T0.warn), ok: v('--ok', T0.ok),
      unknown: v('--rule-strong', T0.unknown),
      p: [0, 1, 2, 3, 4].map((i) => v('--p' + i, P_DARK[i])),
    };
  }
  const GRID_NAMES = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const KIND_NAME = { G: 'generator', NL: 'load node', PS: 'pumped storage' };
  // The box each grid's scope zooms to (degrees, with the islands' coasts inside).
  const GRID_BOX = {
    CLUZ: { w: 119.4, e: 124.5, s: 12.3, n: 18.8 },
    CVIS: { w: 121.7, e: 126.2, s: 8.9, n: 12.8 },
    CMIN: { w: 121.7, e: 126.8, s: 5.4, n: 10.1 },
  };
  // Grid names sit in open sea beside each grid, clear of the sites.
  const GRID_NAME_AT = { CLUZ: [118.7, 16.4], CVIS: [120.55, 11.3], CMIN: [126.95, 8.0] };
  // Which side of its curve a link's label reads on (-1 west, 1 east), clear of the busiest coasts.
  const LINK_LABEL_SIDE = { VISLUZ1: -1, MINVIS1: 1 };
  // Where a notice that names no single site is drawn: open sea beside each grid.
  const GRID_NOTICE_AT = { CLUZ: [119.3, 17.2], CVIS: [121.0, 10.2], CMIN: [121.4, 8.25] };
  // Converter stations of the two links (public, approximate to the town); flow sign: positive
  // is the first grid in the name sending to the second.
  const LINK_DEFS = {
    VISLUZ1: { name: 'Leyte–Luzon HVDC', a: [124.61, 11.01], b: [123.18, 13.62], from: 'Visayas', to: 'Luzon' },
    MINVIS1: { name: 'Mindanao–Visayas HVDC', a: [123.75, 7.97], b: [123.48, 10.05], from: 'Mindanao', to: 'Visayas' },
  };
  const CHIPS = [['prices', 'Prices'], ['interconnectors', 'Interconnectors'], ['generators', 'Generators'],
    ['loads', 'Load nodes'], ['messages', 'Messages'], ['events', 'Events']];
  // Severity, shared with the strip and the desk (docs/work/ui-refinement-2026-10-18/desk-api.md).
  const SEVERITY_OF = { red: 'alert', trip: 'alert', yellow: 'warning', mld: 'warning', derate: 'warning', online: 'info', notice: 'info' };
  const SEVERITY_RANK = { alert: 3, warning: 2, info: 1 };
  const KIND_LABEL = { trip: 'Trip', mld: 'Load dropping', yellow: 'Yellow alert', red: 'Red alert', online: 'Back online', notice: 'Notice', derate: 'Derate' };
  // Region names as the province layer carries them, to the grid and to a short label.
  const ROMAN = {
    'I': ['CLUZ', 'Ilocos'], 'II': ['CLUZ', 'Cagayan Valley'], 'III': ['CLUZ', 'Central Luzon'],
    'IV-A': ['CLUZ', 'CALABARZON'], 'IV-B': ['CLUZ', 'MIMAROPA'], 'V': ['CLUZ', 'Bicol'],
    'VI': ['CVIS', 'Western Visayas'], 'VII': ['CVIS', 'Central Visayas'], 'VIII': ['CVIS', 'Eastern Visayas'],
    'IX': ['CMIN', 'Zamboanga Peninsula'], 'X': ['CMIN', 'Northern Mindanao'], 'XI': ['CMIN', 'Davao'],
    'XII': ['CMIN', 'SOCCSKSARGEN'], 'XIII': ['CMIN', 'Caraga'],
  };
  const TECH = /\b(solar|wind|hydro\w*|hepp?|geo-?thermal\w*|coal|diesel|bunker|oil|gas|lng|biomass|bio\w*|nuclear|thermal|thermo|therma|battery|bess|dpp|cfpp|ccgt|gtpp|pv|combined[- ]cycle|pumped[- ]storage|steam)\b/i;

  // ------------------------------------------------------------------ small helpers
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const peso = (v) => (v == null ? '—' : '₱' + fmt(v));
  const hhmm = (t) => String(t == null ? '' : t).slice(11, 16);
  const day = (t) => String(t == null ? '' : t).slice(0, 10);
  const minutes = (t) => Date.parse(String(t).slice(0, 16).replace(' ', 'T') + ':00Z') / 60000;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  /* A plant's name only when it does not reveal technology or fuel (the overview's rule). */
  const safeName = (site) => (site && site.name && !TECH.test(site.name) ? site.name : '');
  function noticeText(text) {
    const shell = typeof window !== 'undefined' ? window.GNShell : null;
    if (shell && typeof shell.opText === 'function') return shell.opText(text);
    return String(text == null ? '' : text).replace(new RegExp(TECH.source, 'gi'), '[…]')
      .replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');
  }

  // ------------------------------------------------------------------ pure math
  /* The plane: lon/lat to flat plane units — one cosine at 12.5 N, no library. */
  function plane(lon, lat) { return [(lon - BOUNDS.w) * COSLAT, BOUNDS.n - lat]; }
  const SPAN_X = (BOUNDS.e - BOUNDS.w) * COSLAT;
  const SPAN_Y = BOUNDS.n - BOUNDS.s;
  const FIT_NW = plane(FIT.w, FIT.n), FIT_SE = plane(FIT.e, FIT.s);
  const FIT_X = FIT_SE[0] - FIT_NW[0], FIT_Y = FIT_SE[1] - FIT_NW[1];

  /* The whole of the fitted view: the archipelago (FIT) inside the padding, its centre under the
     canvas centre. */
  function fitTransform(w, h) {
    const k = Math.min(Math.max(1e-6, w - 2 * PAD) / FIT_X, Math.max(1e-6, h - 2 * PAD) / FIT_Y);
    return { k, fx: FIT_NW[0] + FIT_X / 2, fy: FIT_NW[1] + FIT_Y / 2, w, h };
  }
  /* A scope's view: the grid's box fitted to the canvas, never past the zoom ceiling;
     no scope (or an unknown one) is the whole country. */
  function scopeTransform(w, h, g) {
    const b = GRID_BOX[g];
    if (!b) return fitTransform(w, h);
    const p1 = plane(b.w, b.n), p2 = plane(b.e, b.s);
    const sx = p2[0] - p1[0], sy = p2[1] - p1[1];
    const fk = fitTransform(w, h).k;
    const k = Math.min(KMAX_FACTOR * fk, Math.max(fk, Math.min(Math.max(1e-6, w - 2 * PAD) / sx, Math.max(1e-6, h - 2 * PAD) / sy)));
    return { k, fx: p1[0] + sx / 2, fy: p1[1] + sy / 2, w, h };
  }
  function toScreen(T, p) { return [T.w / 2 + T.k * (p[0] - T.fx), T.h / 2 + T.k * (p[1] - T.fy)]; }
  function worldOf(T, sx, sy) { return [T.fx + (sx - T.w / 2) / T.k, T.fy + (sy - T.h / 2) / T.k]; }
  function fitK(T) { return fitTransform(T.w, T.h).k; }
  function clampK(T) {
    const k = Math.min(Math.max(T.k, fitK(T)), KMAX_FACTOR * fitK(T));
    return { k, fx: T.fx, fy: T.fy, w: T.w, h: T.h };
  }
  /* Zoom about a screen point: the world point under it before the zoom stays under it after —
     including when the clamp bites, because `fx` is derived from that point, not from the old k. */
  function zoomAt(T, factor, sx, sy) {
    const w = worldOf(T, sx, sy);
    const k = Math.min(Math.max(T.k * factor, fitK(T)), KMAX_FACTOR * fitK(T));
    return { k, fx: w[0] - (sx - T.w / 2) / k, fy: w[1] - (sy - T.h / 2) / k, w: T.w, h: T.h };
  }
  function panBy(T, dx, dy) { return { k: T.k, fx: T.fx - dx / T.k, fy: T.fy - dy / T.k, w: T.w, h: T.h }; }
  /* A two-finger move: zoom about the pair's *previous* midpoint, then translate by the
     midpoint's own travel, so the world point that was under the fingers lands under the new
     midpoint. The anchor survives the clamp. */
  function pinchTransform(T, prev, next) {
    const factor = prev.d > 0 ? next.d / prev.d : 1;
    const zoomed = zoomAt(T, factor, prev.mid[0], prev.mid[1]);
    return panBy(zoomed, next.mid[0] - prev.mid[0], next.mid[1] - prev.mid[1]);
  }
  /* The single-pointer drag and how the two-pointer transitions rewrite it. Two pointers are a
     gesture, never a click; a pointer that lifts out of a pinch leaves the drag re-anchored on
     the survivor where it is now. */
  function dragDown(prev, p, count) {
    const moved = prev ? prev.moved : 0;
    return { x: p[0], y: p[1], moved: count >= 2 ? Math.max(moved, DRAG_CLICK_PX) : moved,
      last: { x: p[0], y: p[1] } };
  }
  function dragUp(prev, survivor) {
    if (!prev || !survivor) return null;
    return { x: survivor[0], y: survivor[1],
      moved: Math.max(prev.moved, DRAG_CLICK_PX), last: { x: survivor[0], y: survivor[1] } };
  }
  /* A box change keeps the reader's pan and zoom: the focus stays, k follows the fit ratio. */
  function resizeTransform(T, w, h) {
    const ratio = fitTransform(w, h).k / fitK(T);
    return clampK({ k: T.k * ratio, fx: T.fx, fy: T.fy, w, h });
  }
  /* A transform shifted so the box the overlays leave free is centred on what was centred. */
  function insetTransform(T, insets) {
    const i = insets || {};
    const dx = ((i.left || 0) - (i.right || 0)) / 2, dy = ((i.top || 0) - (i.bottom || 0)) / 2;
    return { k: T.k, fx: T.fx - dx / T.k, fy: T.fy - dy / T.k, w: T.w, h: T.h };
  }
  /* Drawn size by kind and registered capacity: a generator (and pumped storage, drawn as a
     generator) grows with capacity; a load node is the small fixed circle. */
  function radiusOf(site) {
    if (site.k === 'NL') return LOAD_RADIUS;
    return Math.min(7, 2 + Math.sqrt(site.cap || 1) / 6);
  }

  // ---- colour: OKLab, the perceptual space the scale interpolates in
  const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
  function hexRgb(hex) {
    const h = String(hex).trim().replace('#', '');
    const full = h.length === 3 ? h.split('').map((x) => x + x).join('') : h.slice(0, 6);
    return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) / 255);
  }
  function oklab(hex) {
    const [r, g, b] = hexRgb(hex).map(toLinear);
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function fromOklab(lab) {
    const [L, a, b] = lab;
    const l = Math.pow(L + 0.3963377774 * a + 0.2158037573 * b, 3);
    const m = Math.pow(L - 0.1055613458 * a - 0.0638541728 * b, 3);
    const s = Math.pow(L - 0.0894841775 * a - 1.2914855480 * b, 3);
    const rgb = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
    return '#' + rgb.map((c) => Math.round(clamp01(toGamma(clamp01(c))) * 255).toString(16).padStart(2, '0')).join('');
  }
  function mixOklab(a, b, t) {
    const pa = oklab(a), pb = oklab(b);
    return fromOklab([0, 1, 2].map((i) => pa[i] + (pb[i] - pa[i]) * t));
  }
  /* A quantile of a sorted list, linear between ranks (the usual "type 7"). */
  function quantile(sorted, p) {
    if (!sorted.length) return null;
    const h = (sorted.length - 1) * p, lo = Math.floor(h), hi = Math.ceil(h);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (h - lo);
  }
  /* The price scale of one draw: five knots from the drawn prices, clamped to [0, 32,000],
     strictly increasing (a flat spread is widened to MIN_SPAN about its median), and five
     colours. `null` when no price is drawn. */
  function priceScale(values, colours) {
    const v = (values || []).filter((x) => x != null && Number.isFinite(Number(x))).map(Number).sort((a, b) => a - b);
    if (!v.length) return null;
    const cut = (x) => Math.max(PRICE_FLOOR, Math.min(PRICE_CEIL, x));
    let knots = SCALE_Q.map((p) => cut(quantile(v, p)));
    if (knots[4] - knots[0] < MIN_SPAN) {
      const m = knots[2], s = MIN_SPAN / 4;
      knots = [m - 2 * s, m - s, m, m + s, m + 2 * s].map(cut);
    }
    for (let i = 1; i < 5; i++) if (knots[i] <= knots[i - 1]) knots[i] = knots[i - 1] + 1;
    if (knots[4] > PRICE_CEIL) {
      knots[4] = PRICE_CEIL;
      for (let i = 3; i >= 0; i--) if (knots[i] >= knots[i + 1]) knots[i] = knots[i + 1] - 1;
    }
    return { knots, colours: (colours || P_DARK).slice(0, 5), n: v.length, min: v[0], max: v[v.length - 1],
      median: quantile(v, 0.5), atCeil: v.filter((x) => x >= PRICE_CEIL).length };
  }
  /* The colour the scale gives a price: clamped to the end knots, OKLab between two knots. */
  function colorAt(scale, value) {
    if (value == null || !scale) return UNKNOWN_FILL;
    const k = scale.knots, c = scale.colours;
    if (value <= k[0]) return mixOklab(c[0], c[0], 0);
    if (value >= k[4]) return mixOklab(c[4], c[4], 0);
    let i = 0;
    while (i < 3 && value > k[i + 1]) i++;
    return mixOklab(c[i], c[i + 1], (value - k[i]) / (k[i + 1] - k[i]));
  }
  /* The legend ramp: the knots stand evenly along it (a quantile axis), so its 17 stops are the
     OKLab mixes between neighbouring colours — the same function the dots use. */
  function rampGradient(scale) {
    const c = (scale && scale.colours) || P_DARK;
    const stops = [];
    for (let j = 0; j <= 16; j++) {
      const pos = j / 16, seg = Math.min(3, Math.floor(pos * 4));
      stops.push(`${mixOklab(c[seg], c[seg + 1], pos * 4 - seg)} ${(pos * 100).toFixed(2)}%`);
    }
    return 'linear-gradient(90deg, ' + stops.join(', ') + ')';
  }
  /* A tick label: the knot as a plain number, and a knot at 32,000 with a `+` — the node series
     is uncapped, so the label names what happens above it instead of calling it a cap. */
  function tickLabel(v) {
    return fmt(v) + (v >= PRICE_CEIL ? '+' : '');
  }
  /* A surveyed location, and an approximate display placement (build_data's area rule). Only
     the first is ever read as where a site is; both are drawn. */
  const isLocated = (s) => !!s && (s.p === 'plant' || s.p === 'municipality') && s.lon != null && s.lat != null;
  const isApprox = (s) => !!s && s.p === 'approximate' && s.lon != null && s.lat != null;
  const approxPrefix = (s) => String((s && s.approx && s.approx.prefix) || String((s && s.s) || '').slice(0, 2));
  /* The words an approximate position carries wherever it is shown. */
  function approxWords(list) {
    const prefixes = Array.from(new Set(list.map(approxPrefix))).sort();
    const where = prefixes.length > 1 ? prefixes.slice(0, -1).join(', ') + ' and ' + prefixes[prefixes.length - 1] : prefixes[0];
    return list.length > 1
      ? `${list.length} approximate positions, placed near other ${where} sites. No surveyed location.`
      : `Approximate position, placed near other ${where} sites. No surveyed location.`;
  }
  /* Every drawn site whose own drawn radius (plus the slop) reaches the point, top of the
     stack first: radius descending, then code. */
  function siteAt(T, sites, sx, sy) {
    const out = [];
    for (const site of sites || []) {
      if (site.p === 'placeholder' || site.lon == null || site.lat == null) continue;
      const p = toScreen(T, plane(site.lon, site.lat));
      const r = radiusOf(site);
      const dx = p[0] - sx, dy = p[1] - sy, reach = r + HIT_SLOP;
      if (dx * dx + dy * dy <= reach * reach) out.push({ code: site.s, site, x: p[0], y: p[1], r });
    }
    return laterOnTop(out);
  }
  function laterOnTop(list) {
    return list.sort((a, b) => (b.r - a.r) || (a.code < b.code ? -1 : a.code > b.code ? 1 : 0));
  }
  /* The places of one draw: located sites, largest registered MW first (then code), each joining
     the first place whose anchor is within CLUSTER_PX on screen, else starting one. A place of one
     site is that site's own dot; a place of several is drawn at their mean position, sized by
     their generating MW. */
  function clusterRadius(members) {
    if (members.length === 1) return radiusOf(members[0]);
    const gen = members.filter((s) => s.k !== 'NL').reduce((a, s) => a + (s.cap || 0), 0);
    const biggest = Math.max.apply(null, members.map(radiusOf));
    const r = gen > 0 ? Math.min(13, 2.5 + Math.sqrt(gen) / 6) : Math.min(4.5, LOAD_RADIUS + 0.7 * (members.length - 1));
    return Math.max(r, biggest + 1);
  }
  /* A place's two marks: the filled disc of its located sites (clusterRadius, as before) and the
     dashed ring of its approximate ones, around the disc when both stand there. */
  function placeMarks(members) {
    const core = members.filter((s) => !isApprox(s)), approx = members.filter(isApprox);
    const coreR = core.length ? clusterRadius(core) : 0;
    const ringR = !approx.length ? 0 : core.length ? Math.max(clusterRadius(approx), coreR + 2.5) : Math.max(3, clusterRadius(approx));
    return { core: coreR, ring: ringR, r: Math.max(coreR, ringR), approx: approx.length };
  }
  function clusterSites(T, sites) {
    /* located sites first, so an approximate site only ever joins a place or starts its own:
       the located places are exactly what they were without it */
    const order = (sites || []).filter((s) => s.p !== 'placeholder' && s.lon != null && s.lat != null)
      .sort((a, b) => (isApprox(a) - isApprox(b)) || (b.cap || 0) - (a.cap || 0) || (a.s < b.s ? -1 : a.s > b.s ? 1 : 0));
    const out = [];
    for (const s of order) {
      const p = toScreen(T, plane(s.lon, s.lat));
      let hit = null;
      for (const c of out) {
        const dx = c.ax - p[0], dy = c.ay - p[1];
        if (dx * dx + dy * dy <= CLUSTER_PX * CLUSTER_PX) { hit = c; break; }
      }
      const located = !isApprox(s);
      if (hit) {
        hit.members.push(s);
        if (located) { hit.sx += p[0]; hit.sy += p[1]; hit.k += 1; } else if (!hit.k) { hit.qx += p[0]; hit.qy += p[1]; hit.q += 1; }
      } else {
        out.push(located ? { ax: p[0], ay: p[1], sx: p[0], sy: p[1], k: 1, qx: 0, qy: 0, q: 0, members: [s] }
          : { ax: p[0], ay: p[1], sx: 0, sy: 0, k: 0, qx: p[0], qy: p[1], q: 1, members: [s] });
      }
    }
    /* the mark stands at the mean of its located sites; a place of approximate sites only, at
       theirs */
    return out.map((c) => {
      const n = c.members.length, marks = placeMarks(c.members);
      const x = n === 1 ? c.ax : c.k ? (c.k === 1 ? c.sx : c.sx / c.k) : c.qx / c.q;
      const y = n === 1 ? c.ay : c.k ? (c.k === 1 ? c.sy : c.sy / c.k) : c.qy / c.q;
      return { x, y, n, r: marks.r, core: marks.core, ring: marks.ring, approx: marks.approx,
        members: c.members, codes: c.members.map((s) => s.s) };
    });
  }
  /* The place under a point: the largest whose mark (plus the slop) covers it. */
  function clusterAt(clusters, sx, sy) {
    let best = null;
    for (const c of clusters || []) {
      const dx = c.x - sx, dy = c.y - sy, reach = c.r + HIT_SLOP;
      if (dx * dx + dy * dy <= reach * reach && (!best || c.r > best.r)) best = c;
    }
    return best;
  }
  /* One link's readings at one interval, each the record's own value or `null`: `false` means
     the record says "not congested", `null` means it does not say. */
  function flowAt(link, ri) {
    if (!link || ri == null) return null;
    const flow = link.flow;
    if (!flow || ri >= flow.length) return null;
    return flow[ri] == null ? null : flow[ri];
  }
  function congestionAt(link, ri) {
    if (!link || ri == null) return null;
    const flags = link.congested;
    if (!flags || ri >= flags.length) return null;
    return flags[ri] == null ? null : !!flags[ri];
  }
  function linkCurve(def) {
    const p1 = plane(def.a[0], def.a[1]), p2 = plane(def.b[0], def.b[1]);
    const dx = p2[0] - p1[0], dy = p2[1] - p1[1];
    return { p1, c: [(p1[0] + p2[0]) / 2 + dy * 0.18, (p1[1] + p2[1]) / 2 - dx * 0.18], p2 };
  }
  function curvePoint(curve, t) {
    const a = (1 - t) * (1 - t), b = 2 * (1 - t) * t, c = t * t;
    return [a * curve.p1[0] + b * curve.c[0] + c * curve.p2[0], a * curve.p1[1] + b * curve.c[1] + c * curve.p2[1]];
  }
  function segmentDistance(x, y, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1, len2 = dx * dx + dy * dy;
    const t = len2 ? Math.min(1, Math.max(0, ((x - x1) * dx + (y - y1) * dy) / len2)) : 0;
    return { distance: Math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)), x: x1 + t * dx, y: y1 + t * dy };
  }
  /* The nearest link within LINK_HIT of the point: sample the quadratic at LINK_SAMPLES segments. */
  function linkAt(T, defs, sx, sy) {
    let best = null;
    for (const id in defs) {
      const curve = linkCurve(defs[id]);
      let prev = toScreen(T, curvePoint(curve, 0));
      for (let i = 1; i <= LINK_SAMPLES; i++) {
        const pt = toScreen(T, curvePoint(curve, i / LINK_SAMPLES));
        const near = segmentDistance(sx, sy, prev[0], prev[1], pt[0], pt[1]);
        if (near.distance <= LINK_HIT && (!best || near.distance < best.distance)) {
          best = { id, s: i / LINK_SAMPLES, x: near.x, y: near.y, distance: near.distance };
        }
        prev = pt;
      }
    }
    return best;
  }
  /* Which site a message names: the event record's explicit mapping first; otherwise a site
     whose code words the text contains, and only when exactly one site matches. */
  function siteTokens(code) { return (String(code).match(/[A-Za-z]{3,}/g) || []).map((t) => t.toUpperCase()); }
  function mentions(text, tokens) {
    const up = String(text).toUpperCase();
    return tokens.some((t) => new RegExp('(^|[^A-Z])' + t + '($|[^A-Z])').test(up));
  }
  function sitesNamedBy(message, sites, events) {
    const ev = (events || []).find((e) => e.advisory === message.id);
    if (ev) {
      const site = (sites || []).find((x) => x.s === ev.site);
      if (site) return { site, candidates: [site], how: 'the event record' };
    }
    const hits = (sites || []).filter((s) => (message.grid == null || s.g === message.grid)
      && mentions(message.text, siteTokens(s.s)));
    return { site: hits.length === 1 ? hits[0] : null, candidates: hits, how: hits.length === 1 ? 'its code in the text' : null };
  }
  /* A notice's severity: the advisory kind, with a trip notice that reads as a derating drawn as
     a warning (desk-api.md: derate is a warning). */
  function severityOf(a) {
    if (!a) return 'info';
    if (a.kind === 'trip' && /derat/i.test(String(a.text || ''))) return 'warning';
    return SEVERITY_OF[a.kind] || 'info';
  }
  /* The set a draw paints and a click resolves: the scope and the layer chips decide it once,
     so nothing is painted that cannot be hit and nothing hit that is not painted. */
  function viewSites(sites, view) {
    return (sites || []).filter((s) => (view.scope ? s.g === view.scope : true)
      && s.p !== 'placeholder' && s.lon != null && s.lat != null
      && (s.k === 'NL' ? view.layers.loads : view.layers.generators));
  }
  /* The unlocated sites of the scope, largest registered MW first: listed apart, never drawn. */
  function unplacedSites(sites, scope) {
    return (sites || []).filter((s) => s.p === 'placeholder' && (!scope || s.g === scope))
      .sort((a, b) => (a.g < b.g ? -1 : a.g > b.g ? 1 : 0) || (b.cap || 0) - (a.cap || 0) || (a.s < b.s ? -1 : a.s > b.s ? 1 : 0));
  }
  function hitTest(T, data, view, sx, sy) {
    const drawn = viewSites(data.sites, view);
    return {
      sites: siteAt(T, drawn, sx, sy),
      link: view.layers.interconnectors ? linkAt(T, LINK_DEFS, sx, sy) : null,
    };
  }
  /* The grid and the short label of a region name ("Central Luzon (Region III)", "National
     Capital Region", "... (CAR)", "... (ARMM)"); null for a name it does not know. */
  function regionInfo(name) {
    const s = String(name || '');
    if (!s) return null;
    if (/national capital/i.test(s) || /\(NCR\)/.test(s)) return { grid: 'CLUZ', short: 'Metro Manila' };
    if (/\(CAR\)|cordillera/i.test(s)) return { grid: 'CLUZ', short: 'Cordillera' };
    if (/\(B?ARMM\)|bangsamoro|muslim mindanao/i.test(s)) return { grid: 'CMIN', short: /bangsamoro|BARMM/i.test(s) ? 'BARMM' : 'ARMM' };
    const roman = s.match(/Region\s+([IVX]+(?:-[AB])?)\b/i);
    if (roman && ROMAN[roman[1].toUpperCase()]) { const r = ROMAN[roman[1].toUpperCase()]; return { grid: r[0], short: r[1] }; }
    if (/mimaropa/i.test(s)) return { grid: 'CLUZ', short: 'MIMAROPA' };
    if (/calabarzon/i.test(s)) return { grid: 'CLUZ', short: 'CALABARZON' };
    if (/caraga/i.test(s)) return { grid: 'CMIN', short: 'Caraga' };
    return null;
  }

  const math = {
    BOUNDS, COSLAT, PAD, KMAX_FACTOR, WHEEL_SCALE, BUTTON_FACTOR, DRAG_CLICK_PX, HIT_SLOP,
    LINK_HIT, LINK_SAMPLES, FIT, MSG_WINDOW_MIN, EVENT_WINDOW_MIN,
    GRID_NOTICE_MIN, LOAD_RADIUS, CLUSTER_PX, SCALE_Q, PRICE_FLOOR, PRICE_CEIL, MIN_SPAN, P_DARK,
    UNKNOWN_FILL, PRICES_OFF_FILL, SPAN_X, SPAN_Y, FIT_X, FIT_Y, LINK_DEFS,
    plane, fitTransform, scopeTransform, toScreen, worldOf, fitK, clampK, zoomAt, panBy, pinchTransform,
    dragDown, dragUp, insetTransform,
    resizeTransform, radiusOf, oklab, fromOklab, mixOklab, quantile, priceScale, colorAt, rampGradient,
    tickLabel, siteAt, unplacedSites, clusterSites, clusterRadius, clusterAt, placeMarks, isLocated, isApprox, approxWords,
    linkCurve, curvePoint, linkAt, flowAt, congestionAt, sitesNamedBy, siteTokens, mentions, severityOf,
    viewSites, hitTest, regionInfo,
  };

  // ------------------------------------------------------------------ the base map, prepared once
  /* The provinces in plane units with their grid and region, and the boundary lines classified
     by what they separate: a coast (one province), a region border (two provinces of different
     regions) and a province border (two of one region). A province without `region` takes the
     grid of the nearest located site, and draws no region border. */
  function prepareGeo(geo, sites) {
    const features = (geo && geo.features) || [];
    // a surveyed location only: an approximate placement never decides a province's grid
    const located = (sites || []).filter(isLocated).map((s) => ({ p: plane(s.lon, s.lat), g: s.g }));
    const provinces = [], country = [];
    for (const f of features) {
      const g = f.geometry;
      if (!g) continue;
      const polys = (g.type === 'Polygon' ? [g.coordinates] : g.coordinates).map((poly) => poly.map((ring) => ring.map((pt) => plane(pt[0], pt[1]))));
      const kind = f.properties && f.properties.kind;
      if (kind === 'country') { country.push(polys); continue; }
      let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
      for (const poly of polys) for (const pt of poly[0] || []) {
        if (pt[0] < minx) minx = pt[0]; if (pt[0] > maxx) maxx = pt[0];
        if (pt[1] < miny) miny = pt[1]; if (pt[1] > maxy) maxy = pt[1];
      }
      const region = f.properties && f.properties.region ? String(f.properties.region) : null;
      const info = regionInfo(region);
      const centre = [(minx + maxx) / 2, (miny + maxy) / 2];
      let grid = info ? info.grid : null;
      if (!grid && located.length) {
        let best = Infinity;
        for (const s of located) { const d = (s.p[0] - centre[0]) ** 2 + (s.p[1] - centre[1]) ** 2; if (d < best) { best = d; grid = s.g; } }
      }
      provinces.push({ polys, region, short: info ? info.short : null, grid, name: (f.properties && f.properties.name) || null,
        box: [minx, miny, maxx, maxy], centre, area: (maxx - minx) * (maxy - miny) });
    }
    // edges keyed by their two ends, to find what each separates
    const key = (a, b) => { const ka = a[0].toFixed(5) + ',' + a[1].toFixed(5), kb = b[0].toFixed(5) + ',' + b[1].toFixed(5); return ka < kb ? ka + '|' + kb : kb + '|' + ka; };
    const users = new Map();
    provinces.forEach((pr, i) => {
      for (const poly of pr.polys) for (const ring of poly) for (let j = 1; j < ring.length; j++) {
        const k = key(ring[j - 1], ring[j]);
        const u = users.get(k);
        if (!u) users.set(k, [i]); else if (u[u.length - 1] !== i) u.push(i);
      }
    });
    const lines = { region: [], province: [], coast: {} };
    provinces.forEach((pr, i) => {
      for (const poly of pr.polys) for (const ring of poly) {
        let run = null, runKind = null;
        const flush = () => {
          if (run && run.length > 1) {
            if (runKind === 'coast') (lines.coast[pr.grid] = lines.coast[pr.grid] || []).push(run);
            else lines[runKind].push(run);
          }
          run = null; runKind = null;
        };
        for (let j = 1; j < ring.length; j++) {
          const u = users.get(key(ring[j - 1], ring[j])) || [i];
          let kind = null;
          if (u.length >= 2 && u[0] === i) {
            const other = provinces[u[1]];
            kind = pr.region && other.region && pr.region !== other.region ? 'region' : 'province';
          } else if (u.length === 1) kind = 'coast';
          if (kind !== runKind) { flush(); if (kind) { run = [ring[j - 1]]; runKind = kind; } }
          if (kind) run.push(ring[j]);
        }
        flush();
      }
    });
    // one label per region, at the area-weighted centre of its provinces' boxes
    const byRegion = new Map();
    for (const pr of provinces) {
      if (!pr.short) continue;
      const r = byRegion.get(pr.short) || { short: pr.short, grid: pr.grid, wx: 0, wy: 0, w: 0 };
      const w = Math.max(1e-6, pr.area);
      r.wx += pr.centre[0] * w; r.wy += pr.centre[1] * w; r.w += w;
      byRegion.set(pr.short, r);
    }
    const regions = Array.from(byRegion.values()).map((r) => ({ short: r.short, grid: r.grid, at: [r.wx / r.w, r.wy / r.w], area: r.w }));
    return { provinces, country, lines, regions, features: features.length };
  }

  // ------------------------------------------------------------------ glyphs
  /* The kind and severity glyphs the popover rows carry: 12px inline SVG, 1.5 stroke,
     currentColor; the price dot is an SVG fill attribute (no inline style under the policy). */
  const SVG = (inner, cls) => `<svg class="${cls}" viewBox="0 0 12 12" aria-hidden="true">${inner}</svg>`;
  const KIND_GLYPH = {
    G: SVG('<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.5"/>', 'gt-kind'),
    PS: SVG('<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3.5 6h5" stroke="currentColor" stroke-width="1.5"/>', 'gt-kind'),
    NL: SVG('<rect x="3" y="3" width="6" height="6" fill="none" stroke="currentColor" stroke-width="1.5"/>', 'gt-kind'),
  };
  const dotSvg = (fill) => `<svg class="gt-dot" viewBox="0 0 8 8" aria-hidden="true"><circle cx="4" cy="4" r="4" fill="${esc(fill)}"/></svg>`;
  const SEV_WORD = { alert: 'Alert', warning: 'Warning', info: 'Information' };
  /* A notice's kind as the shared badge (ui.js `GNUI.badgeHtml`), so the word and style match
     every page; the same markup by hand where GNUI is absent (the fixture harness). */
  function kindBadge(a) {
    const kind = a.kind === 'trip' && /derat/i.test(String(a.text || '')) ? 'derate' : a.kind;
    const ui = typeof window !== 'undefined' ? window.GNUI : null;
    if (ui && typeof ui.badgeHtml === 'function') return ui.badgeHtml(kind);
    const sev = SEVERITY_OF[kind];
    return sev ? `<span class="gn-badge gn-badge--${sev} gn-sev">${esc(KIND_LABEL[kind] || kind)}</span>` : `<span class="gn-badge">${esc(kind)}</span>`;
  }
  const POPOVER_ROWS = 6;

  // ------------------------------------------------------------------ mount
  let mounts = 0;
  function mount(container, data, callbacks) {
    if (!container) throw new Error('map canvas: a container is required');
    data = data || {};
    callbacks = callbacks || {};
    const doc = container.ownerDocument || (typeof document !== 'undefined' ? document : null);
    if (!doc) throw new Error('map canvas: no document to build the map in');
    const win = typeof window !== 'undefined' ? window : null;

    /* The link axis, rebuilt when the page hands over another day's links. */
    let rAxis = null, rMap = new Map();
    const rIndex = { get(t) {
      const axis = (data.hvdc && data.hvdc.t) || [];
      if (axis !== rAxis) { rAxis = axis; rMap = new Map(axis.map((x, i) => [x, i])); }
      return rMap.get(t);
    } };
    /* The node file's own indexes, read from `data.nodes` and rebuilt whenever it changes. */
    const nodeIndex = new Map();
    const nodeRow = new Map();
    function indexNodes(nodes) {
      nodeIndex.clear();
      nodeRow.clear();
      if (!nodes) return;
      (nodes.sites || []).forEach((code, i) => nodeIndex.set(code, i));
      (nodes.t || []).forEach((t, i) => nodeRow.set(t, i));
    }
    indexNodes(data.nodes);
    let base = null, baseGeo = null;
    const baseMap = () => {
      if (!base || baseGeo !== data.geo) { baseGeo = data.geo; base = prepareGeo(data.geo, data.sites); }
      return base;
    };
    const state = {
      layers: { prices: true, interconnectors: true, generators: true, loads: true, messages: true, events: true },
      scope: data.grid || null,
      clock: data.clock || null,
      transform: null,
      insets: { left: 0, top: 0, right: 0, bottom: 0 },
      stack: { key: null, index: 0 },
      drag: null,
      pinch: null,
      pointers: new Map(),
      highlight: null,
    };
    let snapshot = null;
    let legendText = null;
    let tipMark = null;       // the hover: a screen point
    let pinned = null;        // the pinned popover: { kind: 'site'|'marker'|'link', key }
    let scale = null;
    let scaleAll = null;
    let drawn = { clusters: [], markers: [] };
    let anim = null;
    let pendingLink = null;

    // ---- the HTML the module builds inside the container
    const root = doc.createElement('div'); root.setAttribute('class', 'gmap');
    const chips = doc.createElement('div');
    chips.setAttribute('class', 'gmap-chips'); chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', 'Map layers and scope');
    const stage = doc.createElement('div'); stage.setAttribute('class', 'gmap-stage');
    root.appendChild(chips); root.appendChild(stage); container.appendChild(root);

    const chipButtons = {};
    for (const [key, label] of CHIPS) {
      const b = doc.createElement('button');
      b.setAttribute('type', 'button'); b.setAttribute('class', 'gmap-chip'); b.setAttribute('data-layer', key);
      b.setAttribute('aria-pressed', 'true'); b.textContent = label;
      b.addEventListener('click', () => {
        state.layers[key] = !state.layers[key];
        b.setAttribute('aria-pressed', String(state.layers[key]));
        draw();
      });
      chips.appendChild(b);
      chipButtons[key] = b;
    }
    const scopeButtons = {};
    for (const g of [null, 'CLUZ', 'CVIS', 'CMIN']) {
      const b = doc.createElement('button');
      b.setAttribute('type', 'button'); b.setAttribute('class', 'gmap-chip gmap-scope');
      b.setAttribute('data-scope', g || 'all'); b.setAttribute('aria-pressed', String(state.scope === g));
      b.textContent = g ? GRID_NAMES[g] : 'All grids';
      b.addEventListener('click', () => setScope(g));
      chips.appendChild(b);
      scopeButtons[g || 'all'] = b;
    }

    let canvas = null, ctx = null, fallback = null, tip = null, pinBox = null, legend = null, rangeLine = null, asofLine = null;
    let ramp = null, ticks = null, quants = null, rings = null, kindsBox = null, keyButton = null;
    try {
      canvas = doc.createElement('canvas');
      canvas.setAttribute('class', 'gmap-canvas');
      canvas.setAttribute('role', 'img');
      canvas.setAttribute('aria-label', 'Philippine grid sites coloured by the price at the replay clock. Arrow keys pan, plus and minus zoom, Enter lists the assets at the centre.');
      ctx = canvas.getContext ? canvas.getContext('2d') : null;
    } catch (err) { ctx = null; canvas = null; }
    const canvasOk = !!(canvas && ctx);

    if (canvasOk) {
      canvas.setAttribute('tabindex', '0');
      stage.appendChild(canvas);
      rings = doc.createElement('div'); rings.setAttribute('class', 'gmap-rings'); rings.setAttribute('aria-hidden', 'true');
      stage.appendChild(rings);
      const zoom = doc.createElement('div');
      zoom.setAttribute('class', 'gmap-zoom'); zoom.setAttribute('role', 'group'); zoom.setAttribute('aria-label', 'Zoom');
      for (const [label, aria, action] of [['+', 'Zoom in', () => zoomIn()], ['−', 'Zoom out', () => zoomOut()], ['Fit', 'Fit the country', () => fit()]]) {
        const b = doc.createElement('button');
        b.setAttribute('type', 'button'); b.setAttribute('class', 'gmap-chip'); b.setAttribute('aria-label', aria);
        b.setAttribute('title', aria);
        b.textContent = label;
        b.addEventListener('click', action);
        zoom.appendChild(b);
      }
      stage.appendChild(zoom);

      legend = doc.createElement('div'); legend.setAttribute('class', 'gmap-legend');
      const head = doc.createElement('div'); head.setAttribute('class', 'gmap-legend-head');
      const title = doc.createElement('span'); title.setAttribute('class', 'gmap-legend-title');
      title.textContent = 'Node price, ₱/MWh'; head.appendChild(title);
      keyButton = doc.createElement('button');
      keyButton.setAttribute('type', 'button'); keyButton.setAttribute('class', 'gmap-key');
      keyButton.setAttribute('aria-expanded', 'false'); keyButton.textContent = 'Key';
      head.appendChild(keyButton);
      legend.appendChild(head);
      ramp = doc.createElement('span'); ramp.setAttribute('class', 'gmap-ramp');
      ramp.style.background = rampGradient(scale);   // one scale: the dots' own function draws the ramp
      legend.appendChild(ramp);
      ticks = doc.createElement('span'); ticks.setAttribute('class', 'gmap-ticks mono');
      legend.appendChild(ticks);
      quants = doc.createElement('span'); quants.setAttribute('class', 'gmap-quants');
      for (const q of ['p5', 'p25', 'median', 'p75', 'p95']) {
        const s = doc.createElement('span'); s.textContent = q; quants.appendChild(s);
      }
      legend.appendChild(quants);
      /* PP-B5: the legend at rest is the domain only (the ramp, its five knots and what they are).
         The sentence that explains the range opens with the key, and is the legend's title. */
      kindsBox = doc.createElement('ul'); kindsBox.setAttribute('class', 'gmap-kinds'); kindsBox.setAttribute('hidden', '');
      kindsBox.id = 'gmap-key-' + (++mounts);
      keyButton.setAttribute('aria-controls', kindsBox.id);
      const explain = doc.createElement('li'); explain.setAttribute('class', 'gmap-explain');
      rangeLine = doc.createElement('span'); rangeLine.setAttribute('class', 'gmap-range');
      explain.appendChild(rangeLine);
      kindsBox.appendChild(explain);
      for (const [cls, text] of [['gen', 'Generator · circle sized by registered MW'],
        ['load', 'Load node · small circle'], ['ps', 'Pumped storage · drawn as a generator'],
        ['clu', 'Several assets at one place · one mark with their count'],
        ['approx', 'Approximate position · dashed ring near other sites of its area code. Counted in Plants and Load nodes.'],
        ['cong', 'Congested link · red, with a mark at the clock'],
        ['alert', 'Alert · red alert or trip notice'],
        ['warning', 'Warning · yellow alert, load dropping or derating'],
        ['info', 'Information · notice or back online']]) {
        const li = doc.createElement('li');
        const mark = doc.createElement('span'); mark.setAttribute('class', 'gmap-mark ' + cls);
        li.appendChild(mark);
        const text_ = doc.createElement('span'); text_.textContent = text;
        li.appendChild(text_);
        kindsBox.appendChild(li);
      }
      asofLine = doc.createElement('li'); asofLine.setAttribute('class', 'gmap-asof');
      kindsBox.appendChild(asofLine);
      legend.appendChild(kindsBox);
      keyButton.addEventListener('click', () => {
        const open = keyButton.getAttribute('aria-expanded') !== 'true';
        keyButton.setAttribute('aria-expanded', String(open));
        if (open) kindsBox.removeAttribute('hidden'); else kindsBox.setAttribute('hidden', '');
        /* DESKFIX-1: the key opens upwards from the bottom-left corner, into the column a page's
           state card or detail drawer stands in. The open legend says so on its box, and map.css
           stacks it above them, so the Key button stays under the pointer and closes the key. */
        legend.classList.toggle('is-open', open);
      });
      stage.appendChild(legend);

      tip = doc.createElement('div');
      tip.setAttribute('class', 'gmap-tip'); tip.setAttribute('role', 'status'); tip.setAttribute('hidden', '');
      stage.appendChild(tip);
      /* the pinned list: its own element, so the hover tip still works while one is pinned */
      pinBox = doc.createElement('div');
      pinBox.setAttribute('class', 'gmap-pin'); pinBox.setAttribute('role', 'dialog'); pinBox.setAttribute('tabindex', '-1');
      pinBox.setAttribute('aria-label', 'Assets and notices at this place'); pinBox.setAttribute('hidden', '');
      stage.appendChild(pinBox);
    } else {
      /* No canvas: the same readings as text, every row a code with its figures. */
      fallback = doc.createElement('div');
      fallback.setAttribute('class', 'gmap-fallback');
      fallback.setAttribute('role', 'group');
      fallback.setAttribute('aria-label', 'The map as text: canvas is unavailable');
      stage.appendChild(fallback);
    }

    // ---- reading the data
    const inWindow = (when, windowMin) => state.clock != null && String(when) <= String(state.clock)
      && minutes(state.clock) - minutes(when) <= windowMin;
    function siteByCode(code) { return (data.sites || []).find((s) => s.s === code) || null; }
    function nodeValue(site, field) {
      if (!data.nodes || state.clock == null) return null;
      const j = nodeIndex.get(site.s), row = nodeRow.get(state.clock);
      if (j == null || row == null) return null;
      return data.nodes[field][row][j];
    }
    const valueOf = (site) => nodeValue(site, 'lmp');
    const mwOf = (site) => nodeValue(site, 'mw');
    const pricedAtClock = () => !!(data.nodes && state.clock != null && nodeRow.has(state.clock));
    const median = (xs) => { const v = xs.filter((x) => x != null).sort((a, b) => a - b); return v.length ? quantile(v, 0.5) : null; };

    /* Where a site is drawn: its place's mark. Null when the drawn set does not include it, which
       is always so for an unlocated site. */
    function drawnPosition(T, site, drawnSet, clusterOf) {
      if (!drawnSet.has(site.s) || site.p === 'placeholder') return null;
      const c = clusterOf && clusterOf.get(site.s);
      if (c) return { x: c.x, y: c.y, r: c.r };
      const p = toScreen(T, plane(site.lon, site.lat));
      return { x: p[0], y: p[1], r: radiusOf(site) };
    }
    function fillFor(v, priced) {
      return !state.layers.prices ? PRICES_OFF_FILL : priced ? colorAt(scale, v) : C.unknown;
    }
    const unknownFill = () => (C.unknown === T0.unknown ? UNKNOWN_FILL : C.unknown);

    /* The notices in force at the clock, by severity: the one site a message names (60 minutes),
       an event's site (90 minutes), or the grid for a message that names no single site (alerts
       and warnings 4 hours, information 60 minutes). An "online" notice for the same site or grid
       ends an alert drawn there. */
    /* Which site a notice names is a text match over every site, so it is worked out once per
       notice and kept (the draw runs on every pointer move of a pan). */
    const namedCache = new Map();
    let namedSites = null;
    function namedBy(a) {
      if (namedSites !== data.sites) { namedCache.clear(); namedSites = data.sites; }
      const key = a.id + '|' + a.t;
      let got = namedCache.get(key);
      if (!got) { got = sitesNamedBy(a, data.sites, data.events); namedCache.set(key, got); }
      return got;
    }
    function noticesInForce() {
      const out = { site: [], grid: [], events: [] };
      if (state.clock == null) return out;
      const now = minutes(state.clock);
      const known = (data.advisories || []).filter((a) => String(a.t) <= String(state.clock) && now - minutes(a.t) <= GRID_NOTICE_MIN);
      const evByAdv = new Map((data.events || []).map((e) => [e.advisory, e]));
      for (const a of known) {
        const sev = severityOf(a);
        const named = namedBy(a);
        if (named.site && named.site.p !== 'placeholder') {
          if (!inWindow(a.t, MSG_WINDOW_MIN)) continue;
          out.site.push({ a, site: named.site, severity: sev, event: evByAdv.get(a.id) || null });
        } else if (named.site) {
          /* a site with no position: its notice stands at its grid, for a site notice's window */
          const g = a.grid || named.site.g;
          if (!inWindow(a.t, MSG_WINDOW_MIN) || !GRID_NAMES[g]) continue;
          out.grid.push({ a, severity: sev, grid: g, unplaced: named.site, event: evByAdv.get(a.id) || null });
        } else {
          if (!inWindow(a.t, sev === 'info' ? MSG_WINDOW_MIN : GRID_NOTICE_MIN)) continue;
          if (!a.grid || !GRID_NAMES[a.grid]) continue;
          const back = sev !== 'info' && known.some((o) => o.kind === 'online' && o.grid === a.grid && String(o.t) > String(a.t) && !namedBy(o).site);
          if (back) continue;
          out.grid.push({ a, severity: sev, grid: a.grid, unplaced: null, event: null });
        }
      }
      for (const ev of data.events || []) {
        if (!inWindow(ev.t, EVENT_WINDOW_MIN)) continue;
        const site = siteByCode(ev.site);
        if (!site) continue;
        const a = (data.advisories || []).find((x) => x.id === ev.advisory) || null;
        out.events.push({ ev, site, severity: a ? severityOf(a) : 'alert', a });
      }
      return out;
    }

    // ---- painting
    function path(points, T) {
      for (let i = 0; i < points.length; i++) {
        const p = points[i], x = T.w / 2 + T.k * (p[0] - T.fx), y = T.h / 2 + T.k * (p[1] - T.fy);
        if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      }
    }
    function polyPath(polys, T) {
      for (const poly of polys) for (const ring of poly) { path(ring, T); ctx.closePath(); }
    }
    /* Dark or light ink, whichever reads on a fill (its OKLab lightness). */
    function inkOn(fill) { try { return oklab(fill)[0] > 0.62 ? '#0b1018' : '#f4f7fb'; } catch (err) { return C.label; } }
    /* A label with a plate behind it, so it reads over dots and coastlines. */
    function plate(text, x, y, font, ink, align) {
      ctx.font = font;
      const w = ('measureText' in ctx) ? ctx.measureText(text).width : text.length * 6;
      const W = state.transform ? state.transform.w : Infinity;
      let left = align === 'right' ? x - w : x;
      // a label that would run off the canvas reads on the other side of its anchor
      if (left + w > W - 4) left = Math.max(4, x - 28 - w);
      else if (left < 4) left = Math.min(x + 28, W - 4 - w);
      ctx.globalAlpha = 0.86; ctx.fillStyle = C.panel; ctx.fillRect(left - 3, y - 7, w + 6, 14); ctx.globalAlpha = 1;
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillStyle = ink;
      ctx.fillText(text, left, y + 0.5);
    }
    function glyph(sev, x, y, s) {
      ctx.beginPath();
      if (sev === 'alert') { ctx.moveTo(x, y - s); ctx.lineTo(x + s * 0.95, y + s * 0.72); ctx.lineTo(x - s * 0.95, y + s * 0.72); ctx.closePath(); }
      else if (sev === 'warning') { ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath(); }
      else ctx.arc(x, y, s * 0.85, 0, 2 * Math.PI);
      ctx.fillStyle = C.panel; ctx.fill();
      ctx.strokeStyle = sev === 'alert' ? C.bad : sev === 'warning' ? C.warn : C.accent;
      ctx.lineWidth = 1.6; ctx.stroke();
      ctx.fillStyle = ctx.strokeStyle;
      ctx.font = '700 ' + Math.round(s * 1.05) + 'px Inter, ui-sans-serif, sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(sev === 'info' ? 'i' : '!', x, y + (sev === 'alert' ? s * 0.18 : 0.5));
    }

    function draw() {
      if (fallback) { drawFallback(); return; }
      const box = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : { width: 0, height: 0 };
      const W = Math.max(1, Math.round(box.width || 0)), H = Math.max(1, Math.round(box.height || 0));
      const dpr = (win && win.devicePixelRatio) || 1;
      if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) {
        canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      }
      if (!state.transform) { state.transform = viewFor(W, H, state.scope); state.fitted = true; }
      else if (state.transform.w !== W || state.transform.h !== H) {
        state.transform = state.fitted && !anim ? viewFor(W, H, state.scope) : resizeTransform(state.transform, W, H);
      }
      const T = state.transform;
      if (pendingLink && W >= 60 && H >= 60) { const id = pendingLink; pendingLink = null; if (typeof setTimeout === 'function') setTimeout(() => focusLink(id), 0); }
      const z = T.k / fitK(T);
      const view = { scope: state.scope, layers: state.layers };
      const drawnSites = viewSites(data.sites, view);
      const drawnSet = new Set(drawnSites.map((s) => s.s));
      const priced = pricedAtClock();
      readTheme();
      const B = baseMap();

      // the scale of this draw: the drawn located prices at the clock
      const located = drawnSites;
      const values = [];
      for (const s of located) { const v = valueOf(s); if (v != null) values.push(v); }
      scale = priced && values.length ? priceScale(values, C.p) : null;
      // every located site's price at the clock, whatever the scope and layers: the state card's
      // dots compare the three grids on this one scale
      const everyPrice = [];
      if (priced) for (const s of data.sites || []) { if (isLocated(s)) { const v = valueOf(s); if (v != null) everyPrice.push(v); } }
      scaleAll = everyPrice.length ? priceScale(everyPrice, C.p) : null;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = C.sea; ctx.fillRect(0, 0, W, H);
      ctx.lineJoin = 'round';

      // the land: the country filled, the grid in view or under the reader's pointer kept
      // bright and the others dimmed, then the boundaries by what they separate
      for (const polys of B.country) { ctx.beginPath(); polyPath(polys, T); ctx.fillStyle = C.land; ctx.fill(); }
      if (!B.country.length) for (const pr of B.provinces) { ctx.beginPath(); polyPath(pr.polys, T); ctx.fillStyle = C.land; ctx.fill(); }
      const focus = state.highlight || state.scope;
      if (focus) {
        ctx.globalAlpha = 0.62;
        for (const pr of B.provinces) {
          if (pr.grid === focus) continue;
          ctx.beginPath(); polyPath(pr.polys, T); ctx.fillStyle = C.sea; ctx.fill();
        }
        ctx.globalAlpha = 1;
      }
      const provinceAlpha = 0.45 + 0.55 * clamp01((z - 2.4) / 1.6);
      ctx.globalAlpha = provinceAlpha;
      ctx.beginPath();
      for (const line of B.lines.province) path(line, T);
      ctx.strokeStyle = C.province; ctx.lineWidth = 0.5; ctx.stroke();
      const regionAlpha = 0.3 + 0.5 * clamp01((z - 1.2) / 0.9);
      ctx.globalAlpha = regionAlpha;
      ctx.beginPath();
      for (const line of B.lines.region) path(line, T);
      ctx.strokeStyle = C.muted; ctx.lineWidth = z > 2 ? 1 : 0.8;
      if ('setLineDash' in ctx) ctx.setLineDash([4, 3]);
      ctx.stroke();
      if ('setLineDash' in ctx) ctx.setLineDash([]);
      ctx.globalAlpha = 1;
      for (const polys of B.country) {
        ctx.beginPath(); polyPath(polys, T);
        ctx.strokeStyle = C.landEdge; ctx.lineWidth = 0.8; ctx.stroke();
      }
      if (focus) {
        // the grid in view, outlined along its own coast
        ctx.beginPath();
        for (const line of B.lines.coast[focus] || []) path(line, T);
        ctx.globalAlpha = 0.7; ctx.strokeStyle = C.accent; ctx.lineWidth = 1; ctx.stroke(); ctx.globalAlpha = 1;
      }
      if (!B.provinces.length && !B.country.length) {
        // a geo layer with no recognised features: nothing to draw, nothing claimed
      }

      // the labels: the grid names while the whole country is in view, region names as the
      // reader zooms in, province names closer still
      const gridLabelAlpha = 1 - clamp01((z - 2.2) / 1.0);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      if (gridLabelAlpha > 0) {
        ctx.globalAlpha = gridLabelAlpha;
        ctx.fillStyle = C.muted; ctx.font = '600 11px Inter, ui-sans-serif, sans-serif';
        if ('letterSpacing' in ctx) ctx.letterSpacing = '1.5px';
        for (const g in GRID_NAME_AT) {
          const s = toScreen(T, plane(GRID_NAME_AT[g][0], GRID_NAME_AT[g][1]));
          ctx.fillText(GRID_NAMES[g].toUpperCase(), s[0], s[1]);
        }
        if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
        ctx.globalAlpha = 1;
      }
      const regionLabelAlpha = clamp01((z - 1.35) / 0.6) * (1 - clamp01((z - 7) / 2));
      let regionLabels = 0;
      if (regionLabelAlpha > 0) {
        ctx.globalAlpha = regionLabelAlpha * 0.95;
        ctx.fillStyle = C.muted; ctx.font = '600 10px Inter, ui-sans-serif, sans-serif';
        for (const r of B.regions) {
          if (focus && r.grid !== focus) continue;
          const s = toScreen(T, r.at);
          if (s[0] < -40 || s[1] < -10 || s[0] > W + 40 || s[1] > H + 10) continue;
          ctx.fillText(r.short.toUpperCase(), s[0], s[1]);
          regionLabels += 1;
        }
        ctx.globalAlpha = 1;
      }
      const provinceLabelAlpha = clamp01((z - 4.5) / 1.5);
      if (provinceLabelAlpha > 0) {
        ctx.globalAlpha = provinceLabelAlpha;
        ctx.fillStyle = C.faint; ctx.font = '400 10px Inter, ui-sans-serif, sans-serif';
        for (const pr of B.provinces) {
          if (!pr.name) continue;
          const a = toScreen(T, [pr.box[0], pr.box[1]]), b = toScreen(T, [pr.box[2], pr.box[3]]);
          if (b[0] - a[0] < 46 || b[0] < 0 || a[0] > W || b[1] < 0 || a[1] > H) continue;
          const s = toScreen(T, pr.centre);
          ctx.fillText(pr.name, s[0], s[1] + 12);
        }
        ctx.globalAlpha = 1;
      }

      // the two undersea links: the flow's direction as chevrons, congestion in red with its mark
      const linkRows = [];
      if (state.layers.interconnectors) {
        const ri = state.clock != null ? rIndex.get(state.clock) : null;
        for (const id in LINK_DEFS) {
          const def = LINK_DEFS[id], curve = linkCurve(def);
          const link = data.hvdc && data.hvdc.links ? data.hvdc.links[id] : null;
          const flow = flowAt(link, ri);
          const congested = congestionAt(link, ri);   // true, false, or null (the record is silent)
          const p1 = toScreen(T, curve.p1), c = toScreen(T, curve.c), p2 = toScreen(T, curve.p2);
          const stroke = () => { ctx.beginPath(); ctx.moveTo(p1[0], p1[1]); ctx.quadraticCurveTo(c[0], c[1], p2[0], p2[1]); };
          const colour = congested === true ? C.bad : C.accent;
          stroke(); ctx.globalAlpha = 0.18; ctx.strokeStyle = colour; ctx.lineWidth = 7; ctx.stroke();
          ctx.globalAlpha = flow == null ? 0.35 : 1;
          stroke(); ctx.strokeStyle = colour; ctx.lineWidth = congested === true ? 2.2 : 1.6; ctx.stroke();
          if (flow) {
            // chevrons along the curve, pointing the way the power flows
            const dir = flow > 0 ? 1 : -1;
            for (const t of [0.28, 0.72]) {
              const m = toScreen(T, curvePoint(curve, t));
              const a = toScreen(T, curvePoint(curve, t - 0.02 * dir)), b = toScreen(T, curvePoint(curve, t + 0.02 * dir));
              const dx = b[0] - a[0], dy = b[1] - a[1], n = Math.hypot(dx, dy) || 1, ux = dx / n, uy = dy / n;
              ctx.beginPath();
              ctx.moveTo(m[0] - ux * 4 + uy * 4, m[1] - uy * 4 - ux * 4);
              ctx.lineTo(m[0] + ux * 2, m[1] + uy * 2);
              ctx.lineTo(m[0] - ux * 4 - uy * 4, m[1] - uy * 4 + ux * 4);
              ctx.lineWidth = 1.6; ctx.stroke();
            }
          }
          ctx.globalAlpha = 1;
          let marks = 0;
          if (congested === true) {
            /* The mark means "congested at the clock interval"; it sits at the curve's midpoint,
               so it is a state, not a position in time. */
            const mid = toScreen(T, curvePoint(curve, 0.5));
            const a = toScreen(T, curvePoint(curve, 0.49)), b = toScreen(T, curvePoint(curve, 0.51));
            const dx = b[0] - a[0], dy = b[1] - a[1], n = Math.hypot(dx, dy) || 1;
            ctx.beginPath();
            ctx.moveTo(mid[0] - (dy / n) * 6, mid[1] + (dx / n) * 6);
            ctx.lineTo(mid[0] + (dy / n) * 6, mid[1] - (dx / n) * 6);
            ctx.strokeStyle = C.bad; ctx.lineWidth = 2.4; ctx.stroke();
            marks = 1;
          }
          const mid = toScreen(T, curvePoint(curve, 0.5));
          const cong = congested === true ? ' · congested' : congested === null ? ' · congestion unknown' : '';
          const text = flow == null ? '—' + cong + ' at ' + hhmm(state.clock)
            : flow === 0 ? '0 MW' + cong + ' at ' + hhmm(state.clock)
            : `${fmt(Math.abs(flow))} MW ${flow > 0 ? def.from + '→' + def.to : def.to + '→' + def.from}${cong} at ${hhmm(state.clock)}`;
          const short = flow == null ? '— MW' : `${fmt(Math.abs(flow))} MW → ${flow > 0 ? def.to : flow < 0 ? def.from : '—'}`;
          const side = LINK_LABEL_SIDE[id] || 1, lx = mid[0] + side * 14, align = side < 0 ? 'right' : 'left';
          // a narrow canvas drops the word: the red line and its mark already say congested
          plate(short + (congested === true && W >= 600 ? ' · congested' : ''), lx, mid[1] - 8, '500 10.5px Plex, ui-monospace, monospace', congested === true ? C.bad : C.label, align);
          if (W >= 600) plate(def.name, lx, mid[1] + 7, '400 9.5px Inter, sans-serif', C.muted, align);
          linkRows.push({ id, congested, marks, flow, x: mid[0], y: mid[1], label: text });
        }
      }

      // the places: located sites clustered on screen, larger marks painted later
      const rows = [];
      const clusters = clusterSites(T, located);
      const clusterOf = new Map();
      for (const c of clusters) {
        const vals = c.members.map((s) => valueOf(s));
        c.value = median(vals);
        const core = c.members.filter((s) => !isApprox(s)), approx = c.members.filter(isApprox);
        c.fill = core.length === c.members.length ? fillFor(c.value, priced)
          : fillFor(median((core.length ? core : approx).map((s) => valueOf(s))), priced);
        c.ringFill = approx.length ? fillFor(median(approx.map((s) => valueOf(s))), priced) : null;
        for (const code of c.codes) clusterOf.set(code, c);
      }
      for (const s of located) {
        const p = toScreen(T, plane(s.lon, s.lat)), v = valueOf(s);
        rows.push({ code: s.s, kind: s.k, grid: s.g, cap: s.cap == null ? null : s.cap,
          value: v, mw: mwOf(s), fill: fillFor(v, priced), x: p[0], y: p[1], r: radiusOf(s), pending: false,
          approximate: isApprox(s) });
      }
      rows.sort((a, b) => (a.r - b.r) || (a.code > b.code ? -1 : a.code < b.code ? 1 : 0));
      const paintOrder = clusters.slice().sort((a, b) => (a.r - b.r) || (a.codes[0] > b.codes[0] ? -1 : 1));
      for (const c of paintOrder) {
        if (c.core) {
          const several = c.n - c.approx > 1;
          ctx.beginPath(); ctx.arc(c.x, c.y, c.core, 0, 2 * Math.PI);
          ctx.fillStyle = c.fill; ctx.fill();
          ctx.strokeStyle = several ? C.label : C.sea; ctx.globalAlpha = several ? 0.7 : 0.8;
          ctx.lineWidth = several ? 1.1 : 0.8; ctx.stroke(); ctx.globalAlpha = 1;
        }
        if (c.ring) {
          /* an approximate position: hollow, a dashed outline in its price colour over a quiet
             plate line, so it reads on land and sea in both themes */
          ctx.beginPath(); ctx.arc(c.x, c.y, c.ring, 0, 2 * Math.PI);
          ctx.strokeStyle = C.panel; ctx.globalAlpha = 0.75; ctx.lineWidth = 3.2; ctx.stroke(); ctx.globalAlpha = 1;
          if ('setLineDash' in ctx) ctx.setLineDash([2.6, 2]);
          ctx.strokeStyle = c.ringFill; ctx.lineWidth = 1.6; ctx.stroke();
          if ('setLineDash' in ctx) ctx.setLineDash([]);
        }
      }
      // count badges on places of several assets
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      for (const c of paintOrder) {
        if (c.n < 2) continue;
        if ((c.core || c.ring) >= 7.5) {
          // the count inside a mark large enough to hold it, in the ink that reads on its fill
          ctx.fillStyle = c.core ? inkOn(c.fill) : C.label; ctx.font = '600 9px Plex, ui-monospace, monospace';
          ctx.fillText(String(c.n), c.x, c.y + 0.5);
        } else if (z >= 2.6) {
          const bx = c.x + c.r * 0.72 + 3, by = c.y - c.r * 0.72 - 3, br = c.n > 9 ? 6.5 : 5.5;
          c.badge = { x: bx, y: by, r: br };
          ctx.beginPath(); ctx.arc(bx, by, br, 0, 2 * Math.PI);
          ctx.fillStyle = C.panel; ctx.fill(); ctx.strokeStyle = C.landEdge; ctx.lineWidth = 0.8; ctx.stroke();
          ctx.fillStyle = C.label; ctx.font = '600 8.5px Plex, ui-monospace, monospace';
          ctx.fillText(String(c.n), bx, by + 0.5);
        }
      }

      // the unlocated sites of the scope: never painted, listed by the page with their prices
      const pendingRows = unplacedSites(data.sites, state.scope).map((site) => {
        const v = valueOf(site);
        return { code: site.s, kind: site.k, grid: site.g, cap: site.cap == null ? null : site.cap, name: safeName(site) || null,
          value: v, mw: mwOf(site), fill: fillFor(v, priced), pending: true };
      });

      // the notices and events in force, as severity glyphs beside the place they name
      const notices = noticesInForce();
      const messageRows = [], eventRows = [], markers = [], gridRows = [];
      const glyphAt = new Map();   // one glyph per place: the most severe of what stands there
      const addGlyph = (pos, item) => {
        const k = pos.x.toFixed(1) + ',' + pos.y.toFixed(1);
        const g = glyphAt.get(k) || { x: pos.x, y: pos.y, r: pos.r, items: [] };
        // a notice and the event made from it are one item: the event's, which links its page
        const adv = item.a ? item.a.id : null;
        const same = adv ? g.items.findIndex((x) => x.a && x.a.id === adv) : -1;
        if (same < 0) g.items.push(item);
        else if (item.kind === 'event') g.items[same] = item;
        glyphAt.set(k, g);
      };
      if (state.layers.messages) {
        for (const n of notices.site) {
          const pos = drawnPosition(T, n.site, drawnSet, clusterOf);
          if (!pos) continue;
          messageRows.push({ id: n.a.id, code: n.site.s, x: pos.x, y: pos.y, severity: n.severity });
          addGlyph(pos, { kind: 'message', id: n.a.id, a: n.a, severity: n.severity, site: n.site, event: n.event });
        }
      }
      if (state.layers.events) {
        for (const n of notices.events) {
          const pos = drawnPosition(T, n.site, drawnSet, clusterOf);
          if (!pos) continue;
          eventRows.push({ id: n.ev.id, code: n.site.s, x: pos.x, y: pos.y, severity: n.severity });
          addGlyph(pos, { kind: 'event', id: n.ev.id, ev: n.ev, a: n.a, severity: n.severity, site: n.site });
        }
      }
      for (const g of glyphAt.values()) {
        g.items.sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] || (a.kind === 'event' ? -1 : 1));
        const sev = g.items[0].severity;
        // beside a place's mark, up and to the right
        const gx = g.x + g.r * 0.7 + 7, gy = g.y - g.r * 0.7 - 8;
        markers.push({ key: 'p:' + g.items.map((i) => i.id).join(','), level: 'site', severity: sev, x: g.x, y: g.y, gx, gy,
          items: g.items, code: g.items[0].site.s, n: g.items.length, event: (g.items.find((i) => i.kind === 'event' || i.event) || {}).id || null });
      }
      if (state.layers.messages) {
        const byGrid = {};
        for (const n of notices.grid) {
          if (state.scope && n.grid !== state.scope) continue;
          (byGrid[n.grid] = byGrid[n.grid] || []).push(n);
        }
        for (const g in byGrid) {
          const list = byGrid[g].sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] || (a.a.t < b.a.t ? 1 : -1));
          const at = toScreen(T, plane(GRID_NOTICE_AT[g][0], GRID_NOTICE_AT[g][1]));
          // kept inside the part of the map the overlays leave visible, its label to its left
          const ins = state.insets;
          at[0] = Math.min(Math.max(at[0], ins.left + 130), W - ins.right - 16);
          at[1] = Math.min(Math.max(at[1], ins.top + 16), H - ins.bottom - 16);
          for (const n of list) gridRows.push({ id: n.a.id, grid: g, severity: n.severity, x: at[0], y: at[1] });
          markers.push({ key: 'g:' + g, level: 'grid', grid: g, severity: list[0].severity, x: at[0], y: at[1], gx: at[0], gy: at[1],
            items: list.map((n) => ({ kind: 'message', id: n.a.id, a: n.a, severity: n.severity, site: null, unplaced: n.unplaced, event: n.event })),
            n: list.length, event: (list.find((n) => n.event) || { event: { id: null } }).event.id });
        }
      }
      for (const m of markers) {
        glyph(m.severity, m.gx, m.gy, m.level === 'grid' ? 7.5 : 6.5);
        if (m.n > 1) {
          ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
          ctx.fillStyle = C.text2; ctx.font = '600 9px Plex, ui-monospace, monospace';
          ctx.fillText('×' + m.n, m.gx + 9, m.gy);
        }
        if (m.level === 'grid' && W >= 600) plate(GRID_NAMES[m.grid] + ' grid notice' + (m.n > 1 ? 's' : ''), m.gx - 11, m.gy, '500 9.5px Inter, sans-serif', C.text2, 'right');
      }
      placeRings(markers);

      // the readings
      const clockText = state.clock ? `${day(state.clock)} ${hhmm(state.clock)}` : 'no clock';
      const min = values.length ? Math.min.apply(null, values) : null;
      const max = values.length ? Math.max.apply(null, values) : null;
      const atCeil = values.filter((v) => v >= PRICE_CEIL).length;
      const range = !state.layers.prices
        ? 'Prices layer off: every dot is drawn at the uncoloured value.'
        : priced
          ? values.length
            ? `At ${clockText} the ${values.length} drawn prices run ${peso(min)} to ${peso(max)}. Centre: their median.`
            : `At ${clockText} the node file states no price for the drawn sites`
          : !data.nodes
            ? `Node prices: No data for ${clockText} (the bake keeps node prices for its latest days only); every dot is drawn at the unknown value`
            : `No price for ${clockText} in the node file (its only day is ${day(((data.nodes && data.nodes.t) || [])[0])}); every dot is drawn at the unknown value`;
      const tickList = scale ? scale.knots.map(tickLabel) : [];
      legendText = {
        title: 'Node price, ₱/MWh',
        ticks: tickList,
        knots: scale ? scale.knots.slice() : [],
        ramp: rampGradient(scale),
        range,
        above: priced && atCeil ? `${atCeil} of ${values.length} at ₱32,000 or above` : '',
        asof: `Replay ${clockText} · ${rows.filter((r) => !r.approximate).length} sites located` +
          `${rows.some((r) => r.approximate) ? ` and ${rows.filter((r) => r.approximate).length} approximate` : ''} in ${clusters.length} places` +
          `${pendingRows.length ? `, ${pendingRows.length} unplaced and listed apart` : ''}` +
          `${linkRows.filter((l) => l.congested === true).length ? ` · ${linkRows.filter((l) => l.congested === true).length} links congested` : ''}` +
          `${linkRows.filter((l) => l.congested === null).length ? ` · ${linkRows.filter((l) => l.congested === null).length} link${linkRows.filter((l) => l.congested === null).length === 1 ? '' : 's'} with unknown congestion` : ''}` +
          `${markers.length ? ` · ${markers.length} notice marks` : ''}`,
      };
      updateLegend(legendText);

      drawn = { clusters, markers, links: linkRows };
      // the notices in force by severity, whatever the scope and the layers (the state card's count)
      const counts = { alert: 0, warning: 0, info: 0 };
      const seen = new Set();
      for (const it of notices.site.concat(notices.grid, notices.events)) {
        const id = it.a ? it.a.id : it.ev.id;
        if (seen.has(id)) continue;
        seen.add(id); counts[it.severity] += 1;
      }
      snapshot = {
        width: W, height: H, transform: { k: T.k, fx: T.fx, fy: T.fy, w: T.w, h: T.h }, zoom: z,
        clock: state.clock, scope: state.scope, layers: Object.assign({}, state.layers),
        priced, land: B.features,
        located: rows, pending: pendingRows, links: linkRows, messages: messageRows, events: eventRows,
        notices: gridRows, severity: counts,
        clusters: clusters.map((c) => ({ x: c.x, y: c.y, r: c.r, n: c.n, codes: c.codes.slice(), fill: c.fill, value: c.value, badge: c.badge || null,
          approx: c.approx, core: c.core, ring: c.ring, ringFill: c.ringFill })),
        markers: markers.map((m) => ({ key: m.key, level: m.level, severity: m.severity, code: m.code || null, grid: m.grid || null,
          x: m.x, y: m.y, gx: m.gx, gy: m.gy, n: m.n, ids: m.items.map((i) => i.id), event: m.event })),
        geo: { provinces: B.provinces.length, regions: B.regions.length, regionLines: B.lines.region.length,
          provinceLines: B.lines.province.length, regionLabels },
        price: { min, max, atCeil, drawn: values.length },
        scale: scale ? { knots: scale.knots.slice(), colours: scale.colours.slice(), median: scale.median, n: scale.n } : null,
        chips: Object.assign({}, state.layers),
        legend: legendText,
      };
      if (pinned) showPinned();
      if (tipMark) showTip(tipMark.x, tipMark.y);
    }

    /* The one slow ring, on an alert's glyph only (CSS animation; reduced motion stills it). */
    function placeRings(markers) {
      if (!rings) return;
      while (rings.lastChild) rings.removeChild(rings.lastChild);
      for (const m of markers) {
        if (m.severity !== 'alert') continue;
        const ring = doc.createElement('span');
        ring.setAttribute('class', 'gmap-ring');
        ring.style.left = m.gx.toFixed(1) + 'px';
        ring.style.top = m.gy.toFixed(1) + 'px';
        rings.appendChild(ring);
      }
    }

    function updateLegend(text) {
      if (!legend) return;
      ramp.style.background = text.ramp;
      ticks.textContent = '';
      for (const label of text.ticks) { const s = doc.createElement('span'); s.textContent = label; ticks.appendChild(s); }
      /* an unpriced draw states no domain: the rows stay, empty and unread, so the legend (and the
         fit its height feeds) never jumps when the prices land */
      for (const row of [ticks, quants]) {
        row.setAttribute('class', row.getAttribute('class').replace(' is-empty', '') + (text.ticks.length ? '' : ' is-empty'));
        if (text.ticks.length) row.removeAttribute('aria-hidden'); else row.setAttribute('aria-hidden', 'true');
      }
      rangeLine.textContent = text.range + (text.above ? ` ${text.above}.` : '');
      legend.setAttribute('title', rangeLine.textContent);
      asofLine.textContent = text.asof;
    }

    /* The fallback: the same readings as text. */
    function drawFallback() {
      const priced = pricedAtClock();
      const lines = [];
      const drawnSites = viewSites(data.sites, { scope: state.scope, layers: state.layers });
      const located = drawnSites.filter((s) => s.p !== 'placeholder')
        .sort((a, b) => (a.g < b.g ? -1 : a.g > b.g ? 1 : a.s < b.s ? -1 : 1));
      for (const s of located) {
        const v = valueOf(s);
        lines.push(`${s.name || s.s} · ${s.s} · ${KIND_NAME[s.k] || s.k} · ${GRID_NAMES[s.g] || s.g}` +
          (isApprox(s) ? ` · approximate position near other ${approxPrefix(s)} sites, no surveyed location` : '') +
          (s.cap ? ` · ${fmt(s.cap)} MW registered` : '') +
          ` · ${!state.layers.prices ? 'prices layer off' : priced ? peso(v) + '/MWh' : 'no price for this day'} at ${hhmm(state.clock)}`);
      }
      if (state.layers.interconnectors) {
        const ri = state.clock != null ? rIndex.get(state.clock) : null;
        for (const id in LINK_DEFS) {
          const def = LINK_DEFS[id], link = data.hvdc && data.hvdc.links ? data.hvdc.links[id] : null;
          const flow = flowAt(link, ri);
          const congested = congestionAt(link, ri);
          lines.push(`${def.name} · ${flow == null ? '—' : fmt(Math.abs(flow)) + ' MW ' + (flow > 0 ? def.from + '→' + def.to : def.to + '→' + def.from)}` +
            `${congested === true ? ' · congested at ' + hhmm(state.clock)
              : congested === null ? ' · congestion unknown at ' + hhmm(state.clock) : ''}`);
        }
      }
      const pending = (data.sites || []).filter((s) => s.p === 'placeholder' && (!state.scope || s.g === state.scope));
      if (pending.length) {
        lines.push(`${pending.length} sites with no position on record (never drawn at a coordinate): ${pending.map((s) => s.s).join(', ')}`);
      }
      fallback.textContent = '';
      const head = doc.createElement('p');
      head.textContent = `The map as text: canvas is not available here. Replay ${state.clock ? day(state.clock) + ' ' + hhmm(state.clock) : 'no clock'}.`;
      fallback.appendChild(head);
      for (const line of lines) {
        const p = doc.createElement('p');
        p.setAttribute('class', 'gmap-line');
        p.textContent = line;
        fallback.appendChild(p);
      }
    }

    // ---- the popover
    /* One asset row: kind glyph, code and the name when it reveals no technology, registered MW,
       price at the clock with its dot. A pinned row links to the plant's own page. */
    function assetRow(site, link) {
      const v = valueOf(site), name = safeName(site);
      const fill = state.layers.prices && pricedAtClock() && v != null ? colorAt(scale, v) : C.unknown;
      const label = `<b>${esc(site.s)}</b>${name ? ` <span class="gt-sub">${esc(name)}</span>` : ''}` +
        (isApprox(site) ? ' <span class="gn-badge gn-badge--outline gt-approx" title="Approximate position">Approx.</span>' : '');
      return `<li class="gt-row"><span class="gt-k" title="${esc(KIND_NAME[site.k] || site.k)}">${KIND_GLYPH[site.k] || KIND_GLYPH.G}</span>` +
        (link ? `<a class="gt-name" href="/plant/${encodeURIComponent(site.s)}" data-entity="plant:${esc(site.s)}">${label}</a>` : `<span class="gt-name">${label}</span>`) +
        `<span class="gt-cap mono">${site.cap ? fmt(site.cap) + ' MW' : '—'}</span>` +
        `<span class="gt-price mono">${dotSvg(fill)}${state.layers.prices ? peso(v) : '—'}</span></li>`;
    }
    function clusterHtml(members, opts) {
      const list = members.slice().sort((a, b) => (b.cap || 0) - (a.cap || 0) || (a.s < b.s ? -1 : 1));
      const grids = Array.from(new Set(list.map((s) => GRID_NAMES[s.g] || s.g)));
      const one = list.length === 1 ? list[0] : null;
      const head = one
        ? `<span class="gt-title">${esc(KIND_NAME[one.k] || one.k)} · ${esc(grids.join(', '))}</span>`
        : `<span class="gt-title">${list.length} assets at this place · ${esc(grids.join(', '))}</span>`;
      const shown = list.slice(0, POPOVER_ROWS);
      let html = `<div class="gt-head">${head}<span class="gt-time mono">${hhmm(state.clock)}</span>` +
        (opts.pinned ? '<button type="button" class="gt-close" aria-label="Close the list">×</button>' : '') + '</div>' +
        `<ul class="gt-rows">${shown.map((s) => assetRow(s, opts.pinned)).join('')}</ul>`;
      if (list.length > shown.length) html += `<p class="gt-more">+${list.length - shown.length} more</p>`;
      if (one) html += `<p class="gt-meta"><span class="mono">${fmt(mwOf(one), 1)}</span> MW scheduled · ${state.layers.prices ? 'price' : 'prices layer off'} at <span class="mono">${hhmm(state.clock)}</span> replay</p>`;
      const approx = list.filter(isApprox);
      if (approx.length) html += `<p class="gt-meta gt-approx-note">${esc(approxWords(approx))}</p>`;
      html += `<p class="gt-foot">${opts.pinned ? 'Each row opens its plant page.' : 'Click to pin the list.'}</p>`;
      return html;
    }
    function markerHtml(m, opts) {
      const items = m.items.slice(0, POPOVER_ROWS);
      const where = m.level === 'grid' ? `${GRID_NAMES[m.grid]} grid` : (m.items[0].site ? m.items[0].site.s : '');
      let html = `<div class="gt-head"><span class="gn-badge gn-badge--${m.severity} gn-sev gt-badge">${esc(SEV_WORD[m.severity])}</span>` +
        `<span class="gt-title">${esc(where)}</span>` +
        `<span class="gt-time mono">${hhmm(state.clock)}</span>` +
        (opts.pinned ? '<button type="button" class="gt-close" aria-label="Close the list">×</button>' : '') + '</div><ul class="gt-notes">';
      for (const it of items) {
        const a = it.a, ev = it.kind === 'event' ? it.ev : it.event;
        const title = ev ? ev.title : a ? `Notice ${a.id}` : it.id;
        html += `<li class="gt-note"><div class="gt-note-head">${a ? kindBadge(a) : ''}<b>${esc(title)}</b>` +
          `<span class="gt-when mono">${a ? hhmm(a.t) : ev ? hhmm(ev.t) : ''}</span></div><div>` +
          (a ? `<p class="gt-text">${esc(noticeText(a.text))}</p>` : '') +
          (it.unplaced ? `<p class="gt-unplaced">Names <b class="mono">${esc(it.unplaced.s)}</b>, which has no position on record.</p>` : '') +
          (it.site && isApprox(it.site) ? `<p class="gt-unplaced">Names <b class="mono">${esc(it.site.s)}</b>, drawn at an approximate position. No surveyed location.</p>` : '') +
          (ev ? `<a class="gt-go" href="/event/${encodeURIComponent(ev.id)}" data-entity="event:${esc(ev.id)}">Open the event</a>` : '') + '</div></li>';
      }
      html += '</ul>';
      if (m.items.length > items.length) html += `<p class="gt-more">+${m.items.length - items.length} more</p>`;
      return html;
    }
    function linkHtml(id, pinnedNow) {
      const def = LINK_DEFS[id], link = data.hvdc && data.hvdc.links ? data.hvdc.links[id] : null;
      if (!def) return null;
      const ri = state.clock != null ? rIndex.get(state.clock) : null;
      const flow = flowAt(link, ri);
      const congested = congestionAt(link, ri);
      const dir = flow == null ? '—' : flow === 0 ? 'no flow' : flow > 0 ? `${def.from} → ${def.to}` : `${def.to} → ${def.from}`;
      return `<div class="gt-head"><span class="gt-title"><b>${esc(def.name)}</b></span><span class="gt-time mono">${hhmm(state.clock)}</span>` +
        (pinnedNow ? '<button type="button" class="gt-close" aria-label="Close the list">×</button>' : '') + '</div>' +
        `<p class="gt-meta"><span class="mono">${flow == null ? '—' : fmt(Math.abs(flow))}</span> MW · ${dir} at <span class="mono">${hhmm(state.clock)}</span></p>` +
        `<p class="gt-meta ${congested === true ? 'bad' : ''}">${congested === true ? 'congested at the clock' : congested === false ? 'not congested at the clock' : 'congestion unknown at the clock'}</p>`;
    }
    function markerAt(sx, sy) {
      let best = null, bestD = Infinity;
      for (const m of drawn.markers || []) {
        const d = Math.hypot(m.gx - sx, m.gy - sy);
        if (d <= 9 && d < bestD) { best = m; bestD = d; }
      }
      return best;
    }
    /* What stands under a point, most specific first: a notice glyph, a site or its place, a link. */
    function targetAt(sx, sy) {
      if (!state.transform) return null;
      const hit = hitTest(state.transform, data, { scope: state.scope, layers: state.layers }, sx, sy);
      // a glyph drawn over a neighbouring site: the nearer centre wins
      const m = markerAt(sx, sy);
      const site = hit.sites[0] || null;
      if (m && (!site || Math.hypot(m.gx - sx, m.gy - sy) <= Math.hypot(site.x - sx, site.y - sy))) return { kind: 'marker', marker: m };
      if (hit.sites.length) {
        const c = (drawn.clusters || []).find((cl) => cl.codes.includes(hit.sites[0].code));
        return { kind: 'site', hit, cluster: c || null, members: c ? c.members : [hit.sites[0].site] };
      }
      const c = clusterAt(drawn.clusters, sx, sy);
      if (c) return { kind: 'site', hit, cluster: c, members: c.members };
      if (hit.link) return { kind: 'link', hit, id: hit.link.id };
      return null;
    }
    function place(box, x, y, r) {
      const W = state.transform ? state.transform.w : 0, H = state.transform ? state.transform.h : 0;
      const b = box.getBoundingClientRect ? box.getBoundingClientRect() : { width: 0, height: 0 };
      const w = b.width || 0, h = b.height || 0;
      /* beside the place, right then left; where neither side has room (a phone), below it or
         above it. The box never covers the place itself, so the place stays clickable. */
      let left = x + r + 12, top = y - 16;
      if (W && left + w > W - 8) {
        if (x - r - 12 - w >= 8) left = x - r - 12 - w;
        else {
          left = Math.min(Math.max(8, x - w / 2), Math.max(8, W - 8 - w));
          top = H && y + r + 10 + h > H - 8 && y - r - 10 - h >= 8 ? y - r - 10 - h : y + r + 10;
        }
      }
      if (H && top + h > H - 8 && top < y) top = Math.max(8, H - 8 - h);
      box.style.left = Math.max(4, left).toFixed(0) + 'px';
      box.style.top = Math.max(4, top).toFixed(0) + 'px';
    }
    /* What a target is, as the key a pinned list is found again by. */
    const keyOf = (target) => (!target ? null : target.kind === 'marker' ? 'm:' + target.marker.key
      : target.kind === 'site' ? 's:' + (target.cluster ? target.cluster.codes[0] : target.members[0].s) : 'l:' + target.id);
    function render(target, pinnedNow) {
      let html = null, x = 0, y = 0, r = 0;
      if (target.kind === 'marker') { html = markerHtml(target.marker, { pinned: pinnedNow }); x = target.marker.gx; y = target.marker.gy; r = 8; }
      else if (target.kind === 'site') {
        html = clusterHtml(target.members, { pinned: pinnedNow });
        if (target.cluster) { x = target.cluster.x; y = target.cluster.y; r = target.cluster.r; }
        else if (target.hit && target.hit.sites[0]) { x = target.hit.sites[0].x; y = target.hit.sites[0].y; r = target.hit.sites[0].r; }
      } else if (target.kind === 'link') { html = linkHtml(target.id, pinnedNow); x = target.hit.link.x; y = target.hit.link.y; r = 6; }
      if (!html) return false;
      const box = pinnedNow ? pinBox : tip;
      box.innerHTML = html;
      box.removeAttribute('hidden');
      place(box, x, y, r);
      return true;
    }
    function showTip(sx, sy) {
      if (!tip) return;
      const target = targetAt(sx, sy);
      tipMark = target ? { x: sx, y: sy } : null;
      // the place whose list is pinned shows that list only
      const same = target && pinned && keyOf(target) === pinned.key;
      if (!target || same || !render(target, false)) { tip.setAttribute('hidden', ''); if (!target) tipMark = null; }
    }
    function hideTip() { tipMark = null; if (tip) tip.setAttribute('hidden', ''); }
    /* A pinned popover is re-found after every draw by what it lists, so a pan, a zoom or a clock
       step keeps it on the same place with the new figures. */
    function showPinned() {
      if (!pinBox || !pinned) return;
      let target = null;
      if (pinned.kind === 'marker') {
        const m = (drawn.markers || []).find((x) => x.key === pinned.ref);
        target = m ? { kind: 'marker', marker: m } : null;
      } else if (pinned.kind === 'link') {
        const def = LINK_DEFS[pinned.ref];
        if (def && state.layers.interconnectors) {
          const mid = toScreen(state.transform, curvePoint(linkCurve(def), 0.5));
          target = { kind: 'link', id: pinned.ref, hit: { link: { x: mid[0], y: mid[1] } } };
        }
      } else if (pinned.kind === 'site') {
        const c = (drawn.clusters || []).find((cl) => cl.codes.includes(pinned.ref));
        if (c) target = { kind: 'site', cluster: c, members: c.members };
      }
      if (!target) { unpin(false); return; }
      pinned.key = keyOf(target);
      render(target, true);
    }
    function pin(target) {
      if (!pinBox || !target) return;
      pinned = { kind: target.kind, key: keyOf(target),
        ref: target.kind === 'marker' ? target.marker.key : target.kind === 'link' ? target.id : (target.cluster ? target.cluster.codes[0] : target.members[0].s) };
      if (tip) tip.setAttribute('hidden', '');
      if (render(target, true) && pinBox.focus) { try { pinBox.focus({ preventScroll: true }); } catch (err) { /* focus is a nicety */ } }
    }
    function unpin(refocus) {
      pinned = null;
      if (pinBox) pinBox.setAttribute('hidden', '');
      if (refocus && canvas && canvas.focus) { try { canvas.focus({ preventScroll: true }); } catch (err) { /* nothing to restore */ } }
    }

    // ---- the interactions
    function local(e) {
      const b = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : { left: 0, top: 0 };
      return { x: (e.clientX || 0) - (b.left || 0), y: (e.clientY || 0) - (b.top || 0) };
    }
    function clickAt(sx, sy) {
      const target = targetAt(sx, sy);
      if (!target) { if (pinned) unpin(false); return null; }
      if (target.kind === 'marker') { pin(target); return target.marker.key; }
      if (target.kind === 'site') {
        const hit = target.hit;
        const all = hit && hit.sites.length ? hit.sites
          : laterOnTop(target.members.map((s) => ({ code: s.s, site: s, r: radiusOf(s) })));
        const key = all.map((d) => d.code).join(',');
        if (state.stack.key === key) state.stack.index = (state.stack.index + 1) % all.length;
        else { state.stack.key = key; state.stack.index = 0; }
        const pick = all[state.stack.index];
        if (target.members.length > 1) pin(target); else if (pinned) unpin(false);
        if (callbacks.onSite) callbacks.onSite(pick.code);
        return pick.code;
      }
      if (target.kind === 'link') { if (pinned) unpin(false); if (callbacks.onLink) callbacks.onLink(target.id); return target.id; }
      return null;
    }
    function pointerId(e) { return e && e.pointerId != null ? e.pointerId : 'p'; }
    function pinchOf() {
      const pts = [];
      state.pointers.forEach((p) => pts.push(p));
      if (pts.length < 2) return null;
      return { d: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
        mid: [(pts[0].x + pts[1].x) / 2, (pts[0].y + pts[1].y) / 2] };
    }
    function restPointer() {
      const pts = [];
      state.pointers.forEach((p) => pts.push([p.x, p.y]));
      return pts[0] || null;
    }
    const onDown = (e) => {
      if (e && e.button != null && e.button !== 0) return;
      stopAnim();
      const p = local(e);
      state.pointers.set(pointerId(e), p);
      if (canvas.setPointerCapture && e && e.pointerId != null) {
        try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* no capture: the drag still works */ }
      }
      state.drag = dragDown(state.drag, [p.x, p.y], state.pointers.size);
      state.pinch = state.pointers.size === 2 ? pinchOf() : null;
    };
    const onMove = (e) => {
      const p = local(e);
      const id = pointerId(e);
      if (!state.pointers.has(id)) { showTip(p.x, p.y); setCursor(p.x, p.y); return; }
      state.pointers.set(id, p);
      if (state.pointers.size >= 2) {
        const pinch = pinchOf();
        if (state.pinch && pinch) state.transform = pinchTransform(state.transform, state.pinch, pinch);
        state.pinch = pinch;
        if (state.drag) state.drag.moved = DRAG_CLICK_PX;
        state.fitted = false;
        draw();
        return;
      }
      if (state.drag) {
        const dx = p.x - state.drag.last.x, dy = p.y - state.drag.last.y;
        state.drag.last = p;
        state.drag.moved += Math.hypot(dx, dy);
        state.transform = panBy(state.transform, dx, dy);
        if (state.drag.moved >= DRAG_CLICK_PX) state.fitted = false;
        draw();
      }
    };
    const onUp = (e) => {
      const p = local(e);
      const wasDrag = state.drag;
      state.pointers.delete(pointerId(e));
      if (state.pointers.size === 0) {
        state.drag = null; state.pinch = null;
        if (wasDrag && wasDrag.moved < DRAG_CLICK_PX) clickAt(p.x, p.y);
        showTip(p.x, p.y);
      } else {
        state.pinch = state.pointers.size >= 2 ? pinchOf() : null;
        state.drag = dragUp(state.drag, restPointer());
      }
    };
    const onWheel = (e) => {
      if (e && e.preventDefault) e.preventDefault();
      stopAnim();
      const p = local(e);
      const factor = Math.pow(2, -(e && e.deltaY ? e.deltaY : 0) / WHEEL_SCALE);
      state.transform = zoomView(state.transform, factor, p.x, p.y);
      state.fitted = false;
      draw();
    };
    const onLeave = () => { hideTip(); if (canvas.style) canvas.style.cursor = ''; };
    const onContext = (e) => { if (e && e.preventDefault) e.preventDefault(); };
    function setCursor(sx, sy) {
      if (!canvas.style || state.drag) return;
      canvas.style.cursor = targetAt(sx, sy) ? 'pointer' : '';
    }
    /* The keyboard: arrows pan, + and - zoom, 0 fits, Enter pins the list of the place nearest
       the centre, Escape closes it. The keys stay on the map while it has focus. */
    const onKey = (e) => {
      const k = e && e.key;
      const T = state.transform;
      if (!T) return;
      const handled = () => { if (e.preventDefault) e.preventDefault(); if (e.stopPropagation) e.stopPropagation(); };
      if (k === 'ArrowLeft' || k === 'ArrowRight' || k === 'ArrowUp' || k === 'ArrowDown') {
        const d = 60;
        state.transform = panBy(T, k === 'ArrowLeft' ? d : k === 'ArrowRight' ? -d : 0, k === 'ArrowUp' ? d : k === 'ArrowDown' ? -d : 0);
        state.fitted = false;
        draw(); handled();
      } else if (k === '+' || k === '=') { zoomIn(); handled(); }
      else if (k === '-' || k === '_') { zoomOut(); handled(); }
      else if (k === '0') { fit(); handled(); }
      else if (k === 'Enter' || k === ' ') {
        const [cx, cy] = centre();
        let best = null, bd = Infinity;
        for (const c of drawn.clusters || []) { const d = Math.hypot(c.x - cx, c.y - cy); if (d < bd) { bd = d; best = c; } }
        if (best) pin({ kind: 'site', cluster: best, members: best.members });
        handled();
      } else if (k === 'Escape' && pinned) { unpin(true); handled(); }
    };
    const onTipKey = (e) => { if (e && e.key === 'Escape') { unpin(true); if (e.stopPropagation) e.stopPropagation(); } };
    const onTipClick = (e) => {
      const t = e && e.target;
      if (t && t.closest && t.closest('.gt-close')) unpin(true);
    };

    if (canvasOk) {
      canvas.addEventListener('pointerdown', onDown);
      canvas.addEventListener('pointermove', onMove);
      canvas.addEventListener('pointerup', onUp);
      canvas.addEventListener('pointercancel', onUp);
      canvas.addEventListener('pointerleave', onLeave);
      canvas.addEventListener('wheel', onWheel, { passive: false });
      canvas.addEventListener('contextmenu', onContext);
      canvas.addEventListener('keydown', onKey);
      pinBox.addEventListener('keydown', onTipKey);
      pinBox.addEventListener('click', onTipClick);
    }

    // Redraw when the shell's dark/light toggle changes the theme.
    if (canvasOk && win && win.GNShell && win.GNShell.onTheme) win.GNShell.onTheme(() => draw());

    // ---- the eased moves (scope and fit), skipped where motion is reduced or no frame exists
    const reduced = () => !!(win && win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);
    function stopAnim() { if (anim) { anim.stop = true; anim = null; } }
    function moveTo(target, done) {
      stopAnim();
      const from = state.transform;
      const raf = win && typeof win.requestAnimationFrame === 'function' ? win.requestAnimationFrame.bind(win) : null;
      if (!from || !raf || reduced() || !canvasOk) { state.transform = target; draw(); if (done) done(); return; }
      const job = { stop: false };
      anim = job;
      const t0 = Date.now(), DUR = 360;
      const c0 = worldOf(from, from.w / 2, from.h / 2), c1 = worldOf(target, target.w / 2, target.h / 2);
      const step = () => {
        if (job.stop) return;
        const u = clamp01((Date.now() - t0) / DUR), e = 1 - Math.pow(1 - u, 3);
        const k = Math.exp(Math.log(from.k) + (Math.log(target.k) - Math.log(from.k)) * e);
        state.transform = { k, fx: c0[0] + (c1[0] - c0[0]) * e, fy: c0[1] + (c1[1] - c0[1]) * e, w: target.w, h: target.h };
        if (u >= 1) { state.transform = target; anim = null; }
        draw();
        if (u < 1) raf(step); else if (done) done();
      };
      raf(step);
    }
    /* The view a fit or a scope eases to: the box the overlays leave free, centred. A fit there
       can sit below the canvas's own fit scale; `floorK` keeps the + and - buttons and the wheel
       from snapping back up past it. */
    function viewFor(W, H, g) {
      const i = state.insets;
      const full = fitTransform(W, H);
      const innerFit = fitTransform(Math.max(80, W - i.left - i.right), Math.max(80, H - i.top - i.bottom));
      state.floorK = Math.min(full.k, innerFit.k);
      if (!g) return insetTransform({ k: state.floorK, fx: full.fx, fy: full.fy, w: W, h: H }, i);
      const inner = scopeTransform(Math.max(80, W - i.left - i.right), Math.max(80, H - i.top - i.bottom), g);
      const k = Math.min(Math.max(inner.k, fitTransform(W, H).k), KMAX_FACTOR * fitTransform(W, H).k);
      return insetTransform({ k, fx: inner.fx, fy: inner.fy, w: W, h: H }, i);
    }

    // ---- the returned surface
    /* The centre of the part of the map the overlays leave visible (the canvas centre with no insets). */
    function centre() {
      const T = state.transform || fitTransform(1, 1), i = state.insets;
      return [(i.left + T.w - i.right) / 2, (i.top + T.h - i.bottom) / 2];
    }
    function fit() { stopAnim(); const T = state.transform || fitTransform(1, 1); state.fitted = true; moveTo(viewFor(T.w, T.h, null)); }
    /* zoomAt, with the floor lowered to the inset fit when the overlays cover part of the map
       (with no insets the floor is the canvas's own fit and this is zoomAt exactly). */
    function zoomView(T, factor, sx, sy) {
      const floor = Math.min(fitK(T), state.floorK || Infinity);
      const want = T.k * factor;
      if (want >= fitK(T) || floor >= fitK(T)) return zoomAt(T, factor, sx, sy);
      const w = worldOf(T, sx, sy), k = Math.max(want, floor);
      return { k, fx: w[0] - (sx - T.w / 2) / k, fy: w[1] - (sy - T.h / 2) / k, w: T.w, h: T.h };
    }
    function zoomIn() { stopAnim(); state.transform = zoomView(state.transform || fitTransform(1, 1), BUTTON_FACTOR, centre()[0], centre()[1]); state.fitted = false; draw(); }
    function zoomOut() { stopAnim(); state.transform = zoomView(state.transform || fitTransform(1, 1), 1 / BUTTON_FACTOR, centre()[0], centre()[1]); state.fitted = false; draw(); }
    function panByScreen(dx, dy) { stopAnim(); state.fitted = false; state.transform = panBy(state.transform || fitTransform(1, 1), dx, dy); draw(); }
    function setClock(stamp) { state.clock = stamp == null ? null : String(stamp); draw(); }
    /* A scope filters the sites and eases to that grid; All grids eases back to the country. */
    function setScope(g) {
      state.scope = g || null;
      const T = state.transform || fitTransform(1, 1);
      for (const key in scopeButtons) scopeButtons[key].setAttribute('aria-pressed', String((key === 'all' ? null : key) === state.scope));
      state.fitted = true;
      moveTo(viewFor(T.w, T.h, state.scope));
    }
    /* The grid the reader points at in the page's state card: the others dim, nothing moves. */
    /* A deep link to one HVDC link (`/?link=VISLUZ1`): the congestion layer on, an eased zoom to
       the link with both converter towns in view, and its popover pinned. */
    function focusLink(id) {
      const def = LINK_DEFS[id];
      if (!def) return false;
      if (!state.layers.interconnectors) {
        state.layers.interconnectors = true;
        if (chipButtons.interconnectors) chipButtons.interconnectors.setAttribute('aria-pressed', 'true');
      }
      draw();   // the transform follows the canvas's current box before the target is measured
      const T = state.transform || fitTransform(1, 1), i = state.insets;
      // a deep link on load can arrive before the map has its box: it waits for the first real one
      if (!T || T.w < 60 || T.h < 60) { pendingLink = id; return true; }
      const curve = linkCurve(def);
      const xs = [curve.p1[0], curve.c[0], curve.p2[0]], ys = [curve.p1[1], curve.c[1], curve.p2[1]];
      const pad = 1.4;   // plane units of sea and coast kept around the link
      const w = Math.max(...xs) - Math.min(...xs) + 2 * pad, h = Math.max(...ys) - Math.min(...ys) + 2 * pad;
      const fk = fitTransform(T.w, T.h).k;
      const k = Math.min(KMAX_FACTOR * fk, Math.max(state.floorK || fk, Math.min(Math.max(80, T.w - i.left - i.right) / w, Math.max(80, T.h - i.top - i.bottom) / h)));
      const mid = curvePoint(curve, 0.5);
      const target = insetTransform({ k, fx: mid[0], fy: mid[1], w: T.w, h: T.h }, i);
      state.fitted = false;
      moveTo(target, () => {
        const m = toScreen(state.transform, mid);
        pin({ kind: 'link', id, hit: { link: { x: m[0], y: m[1] } } });
      });
      return true;
    }
    function setHighlight(g) { const next = g && GRID_NAMES[g] ? g : null; if (next !== state.highlight) { state.highlight = next; draw(); } }
    function setInsets(i) {
      const next = { left: Math.max(0, +i.left || 0), top: Math.max(0, +i.top || 0), right: Math.max(0, +i.right || 0), bottom: Math.max(0, +i.bottom || 0) };
      const same = ['left', 'top', 'right', 'bottom'].every((k) => next[k] === state.insets[k]);
      state.insets = next;
      if (!same && state.transform && state.fitted && !anim) { state.transform = viewFor(state.transform.w, state.transform.h, state.scope); draw(); }
    }
    /* The node file's layer arrives after the first paint; handing it over here rebuilds its
       indexes and redraws the same instance — the layers, the scope, the transform and an open
       popover are untouched. */
    function setNodes(nodes) {
      data.nodes = nodes || null;
      indexNodes(data.nodes);
      draw();
    }
    function transform() { return state.transform ? { k: state.transform.k, fx: state.transform.fx, fy: state.transform.fy, w: state.transform.w, h: state.transform.h } : null; }
    function hitTestAt(sx, sy) {
      /* The fallback draws no canvas and holds no transform: there is nothing to hit. */
      if (!state.transform) return { sites: [], link: null };
      return hitTest(state.transform, data, { scope: state.scope, layers: state.layers }, sx, sy);
    }
    function destroy() {
      stopAnim();
      if (canvasOk) {
        canvas.removeEventListener('pointerdown', onDown);
        canvas.removeEventListener('pointermove', onMove);
        canvas.removeEventListener('pointerup', onUp);
        canvas.removeEventListener('pointercancel', onUp);
        canvas.removeEventListener('pointerleave', onLeave);
        canvas.removeEventListener('wheel', onWheel);
        canvas.removeEventListener('keydown', onKey);
      }
      if (root.parentNode && root.parentNode.removeChild) root.parentNode.removeChild(root);
    }

    draw();
    return {
      setClock, setScope, fit, zoomIn, zoomOut, panBy: panByScreen, resize: draw,
      transform, hitTest: hitTestAt, snapshot: () => snapshot, legend: () => legendText,
      scale: () => scale, priceColor: (v) => (scale ? colorAt(scale, v) : unknownFill()),
      gridColor: (v) => (scaleAll ? colorAt(scaleAll, v) : unknownFill()),
      setInsets, setHighlight, focusLink, unpin: () => unpin(false), pinnedOpen: () => !!pinned,
      setNodes, destroy, canvas, root, fallback, chips: chipButtons, scopeChips: scopeButtons,
    };
  }

  const GridMap = { mount, math, GRID_BOX, PRICE_CEIL, BOUNDS, COSLAT, GRID_NAMES, KIND_NAME, LINK_DEFS, FIT, CHIPS, SEVERITY_OF };
  if (typeof window !== 'undefined') window.GridMap = GridMap;
  if (typeof globalThis !== 'undefined') globalThis.GridMap = GridMap;
})();
