/* InGRID public desk. Reads the baked replay data under the page's build-stamped prefix and
   draws everything with SVG except the map, which is ATG-6's canvas module
   (`src/grid/map.js`, mounted here by ATG-8); no library, no network beyond same origin.

   The page draws in two stages. The six small files carry the whole of its words and figures —
   `regions.json` fixes the interval axis every series is keyed by, and with `hvdc.json`,
   `advisories.json`, `sites.json`, `ph.geojson` and `events.json` that is the brief, the figures
   table, the feed, the review list, the chart and the map outline, its sites and its links. The
   node file (one price and one MW figure per site per five-minute interval, ~1.85 MB raw) is
   the heavy read and is asked for at the same moment; it adds the one thing only it carries, the
   site layer — the prices the dots are coloured by. Until it lands a site's price and MW are
   unknown, and the page shows them as unknown (`—`), never as a figure. The canvas is mounted
   at stage one with the six files and handed the node file's layer when it lands
   (`mapPanel.setNodes`), so it is mounted once: the reader's own map state — the layer chips,
   the scope, the pan and zoom, an open tooltip — survives the arrival rather than being
   rebuilt. That is the same two-stage draw the site layer had.

   The design is the orchestrator's; the staged draw above is PERF-4
   (docs/work/performance/perf-4.md), the map canvas ATG-6 (docs/work/atg/map.md), both
   implemented against their task briefs. */
(() => {
  'use strict';
  /* The build stamp the page was served under: the application writes it into the asset URLs and
     into `meta#nowcast-build`, so the replay files are read from the same build as this script.
     A page served without a stamp (a fixture harness serving the source HTML) reads the
     unversioned names, which are never cached. */
  const STAMP = (() => {
    const meta = typeof document !== 'undefined' && document.getElementById
      ? document.getElementById('nowcast-build') : null;
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP;
  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const START = '13:40';
  const CAP = 32000;
  // Converter stations of the two HVDC links (public, approximate to the town); flow sign: positive = first grid in the name to the second.
  const LINKS = {
    VISLUZ1: { name: 'Leyte–Luzon HVDC', a: [124.61, 11.01], b: [123.18, 13.62], from: 'Visayas', to: 'Luzon' },
    MINVIS1: { name: 'Mindanao–Visayas HVDC', a: [123.75, 7.97], b: [123.48, 10.05], from: 'Mindanao', to: 'Visayas' },
  };

  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => {
    const node = document.createElementNS(svgNS, tag);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  };
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const peso = (v) => (v == null ? '—' : '₱' + fmt(v));
  const hhmm = (t) => t.slice(11, 16);
  const day = (t) => new Date(t.slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  /* FRONT-1: the span the chart's axis covers, as its title names it — "21 to 29 Sept 2026" when
     both ends share a month, the two dated ends when they do not, and the one day of a one-day
     axis. The axis carries a missing day (25 September is not on it); the title names the span's
     first and last interval and does not pretend the span is shorter. */
  const dayShort = (t) => new Date(t.slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  const spanWords = (times) => {
    const a = times[0], b = times[times.length - 1];
    if (a.slice(0, 10) === b.slice(0, 10)) return dayShort(a);
    if (a.slice(0, 4) === b.slice(0, 4) && a.slice(5, 7) === b.slice(5, 7)) return `${Number(a.slice(8, 10))} to ${dayShort(b)}`;
    return `${dayShort(a)} to ${dayShort(b)}`;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const opText = (s) => esc(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');

  function band(v) {
    if (v == null) return 'bn';
    return v < 6400 ? 'b0' : v < 12800 ? 'b1' : v < 22400 ? 'b2' : v < 30000 ? 'b3' : 'b4';
  }

  /* The map's own layers (prices, interconnectors, generators, loads, pending, messages, events)
     are the canvas module's chips and its own state; the page carries no layer switch of its own. */
  const state = { grid: 'CVIS', i: 0, playing: false, timer: null, filter: 'all', seen: new Set(), series: 'price' };
  /* The one heavy file, asked for first so it travels while the small ones settle. A bake without
     replay.json has the one node day, 21 Sep; a year bake keeps `nodes-<day>.json` for its
     `node_days` only, and an older day has no site prices (the map says No data). */
  let NODES = 'nodes-2026-09-21.json';
  let D = null;
  const SHELL = typeof window !== 'undefined' ? window.GNShell : null;
  const get = (name, optional) => fetch(DATA + name).then((r) => (r.ok ? r.json() : optional ? null : Promise.reject(new Error(name))));
  /* The node file's own layer, resolved to `null` when it cannot be read: the page keeps the
     outline it can draw and says in the caption that the site prices are unavailable — a page
     that cannot show a price says nothing about it rather than guessing one. */
  const readNodeLayer = (name) => get(name).then((file) => ({
    file, siteIndex: new Map(file.sites.map((s, i) => [s, i])),
    rowIndex: new Map(file.t.map((t, i) => [t, i])),
  }), () => null);
  /* PERF-6: the last NODE_DAYS_KEPT node files' layers, by name (the most recent last), so a
     clock crossing midnight and back reads each day's ~2 MB file once; a read in flight is shared,
     and one that failed (null) is not kept, so the next crossing asks again. */
  const NODE_DAYS_KEPT = 3;
  const nodeLayers = new Map();
  const nodeLayer = (name) => {
    if (!name) return Promise.resolve(null);
    let layer = nodeLayers.get(name);
    if (layer) nodeLayers.delete(name);
    else {
      layer = readNodeLayer(name);
      layer.then((got) => { if (!got && nodeLayers.get(name) === layer) nodeLayers.delete(name); });
    }
    nodeLayers.set(name, layer);
    while (nodeLayers.size > NODE_DAYS_KEPT) nodeLayers.delete(nodeLayers.keys().next().value);
    return layer;
  };

  /* replay-year: the day mode. With replay.json the page holds one day — `days/<day>.json` (its
     axis, the grids' series, the links and the usual-price table) and the notices of that month
     and the one before — and swaps it when the clock crosses midnight or the shared as-of moves
     to another day. The objects the map holds (`D.hvdc`, `D.advisories`) are swapped in place. */
  const REPLAY = { index: null, day: null, loading: null };
  const STEP = 5;
  const dayAxis = (d) => { const out = []; for (let m = 0; m < 1440; m += STEP) out.push(`${d}T${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`); return out; };
  /* A missing day keeps the five-minute axis so the clock can stand on it; every value is null
     (No data), nothing is filled in. */
  function emptyDay(d) {
    const t = dayAxis(d), none = () => t.map(() => null);
    const grids = {};
    for (const g of Object.keys(GRIDS)) grids[g] = { demand_mw: none(), gen_mw: none(), import_mw: none(), export_mw: none(), curtailed_mw: none(), dr_req_mw: none(), dr_short_mw: none(), lmp_median: none(), lmp_max: none() };
    const links = {};
    for (const id of Object.keys(LINKS)) links[id] = { flow: none(), congested: none() };
    return { day: d, t, grids, links, usual: {}, missing: true };
  }
  async function readDay(d) {
    const month = d.slice(0, 7);
    const [file, advisories] = await Promise.all([SHELL.dayFile(d), SHELL.notices(SHELL.monthPlus(month, -1), month)]);
    return { file: file || emptyDay(d), advisories: advisories || [] };
  }
  function adoptDay(d, got) {
    const f = got.file;
    REPLAY.day = d;
    D.day = d;
    D.missing = !!f.missing;
    D.regions.t = f.t; D.regions.grids = f.grids;
    D.hvdc.t = f.t; D.hvdc.links = f.links;
    D.advisories.splice(0, D.advisories.length, ...got.advisories);
    D.usual = f.usual || {};
    D.t = f.t;
    D.rIndex = new Map(f.t.map((t, i) => [t, i]));
    NODES = REPLAY.index.node_days.includes(d) ? `nodes-${d}.json` : null;
  }
  async function load() {
    const index = SHELL && SHELL.ready ? await SHELL.ready : null;
    if (index) {
      REPLAY.index = index;
      const at = SHELL.asOf();
      const d = at.slice(0, 10);
      NODES = index.node_days.includes(d) ? `nodes-${d}.json` : null;
      const nodes = nodeLayer(NODES);
      const [got, sites, geo, events] = await Promise.all([readDay(d), get('sites.json'), get('ph.geojson'), get('events.json', true)]);
      D = {
        regions: { t: [], grids: {} }, hvdc: { t: [], links: {} }, advisories: [], sites, geo, events: events || [], t: [],
        rIndex: new Map(), nodes: null, siteIndex: null, rowIndex: null, vectors: null, usual: {}, day: null,
        span: SHELL.span,
      };
      adoptDay(d, got);
      return { nodes, get };
    }
    const nodes = nodeLayer(NODES);

    /* Stage 1's six files. `regions.json` fixes the interval axis every series is keyed by
       (scripts/grid/build_data.py), so the replay clock, the chart, the feed and the figures are
       readable without the node file. */
    const [regions, hvdc, advisories, sites, geo, events] = await Promise.all([
      get('regions.json'), get('hvdc.json'), get('advisories.json'), get('sites.json'), get('ph.geojson'), get('events.json', true),
    ]);
    D = {
      regions, hvdc, advisories, sites, geo, events: events || [], t: regions.t,
      rIndex: new Map(regions.t.map((t, i) => [t, i])), nodes: null, siteIndex: null, rowIndex: null, vectors: null,
    };
    /* Wrapped in an object on purpose: `async` adopts a returned promise, which would hold
       stage 1 until the node file had landed — the one wait this staging exists to remove. */
    return { nodes, get };
  }

  // ---------- map (ATG-6's canvas, mounted here) ----------
  /* The canvas module `src/grid/map.js` draws the map — the country and its provinces, the sites
     by kind and capacity coloured by the price at the clock, the two links with their congestion
     marks, the messages at the clock, and the events — with pan, zoom, hit
     testing and its own layer and scope chips, legend and tooltip (the unlocated sites are listed
     apart, PP-B5). This page mounts it from the
     baked files it has already read and hands it the page's own openers (EXPL-1), so a click on
     a site or a link opens exactly what the same element opens anywhere else on the page.
     Nothing here fetches, and no figure is drawn that the bake does not carry. */
  let mapPanel = null;
  function mountMap() {
    const host = $('map');
    if (!host || !window.GridMap) return;
    /* One mount: the node file's layer is handed to this same instance with `setNodes` when it
       lands (stage 2 below), so the reader's chips, scope, pan, zoom and open tooltip are never
       thrown away (ATG-8's correction of the reviewed remount). */
    if (mapPanel) return;
    const explore = () => window.GridExplore || {};
    /* The map's scope is the module's own chips and opens on All grids — the page's SVG map drew
       every grid whatever the switch was set to, and the page's grid switch scopes the brief, the
       figures, the feed and the chart, never the map. So no `grid` is handed over and the scope
       is never reset by the page's render: the reader's own choice stands. */
    mapPanel = window.GridMap.mount(host, {
      geo: D.geo, sites: D.sites, hvdc: D.hvdc, advisories: D.advisories, events: D.events,
      nodes: D.nodes, clock: D.t[state.i],
    }, {
      onSite: (code) => { const e = explore(); if (e.site) e.site(code); },
      onLink: (id) => { const e = explore(); if (e.link) e.link(id); },
    });
  }
  /* The page's own render drives the canvas the same as every other element on the page: one
     clock, never a second one. The scope is the module's own chip row (see `mountMap`). */
  function renderMapPanel() {
    if (!mapPanel) return;
    mapPanel.setClock(D.t[state.i]);
  }
  /* A canvas holds no element per site, so the page draws its one own mark — the ring on the
     site or the link the reader opened, and on the site a message names — on the `map-marks`
     overlay beside the canvas, at the spot the module's own record says it painted that one
     (`snapshot()`). The module's own message and event layers are the map's readings; this ring
     is the page's answer to "which one did I open". */
  function markMap(sel) {
    const host = $('map-marks');
    if (!host) return;
    while (host.lastChild) host.removeChild(host.lastChild);
    const snap = mapPanel && mapPanel.snapshot ? mapPanel.snapshot() : null;
    if (!snap) return;
    const canvas = mapPanel.canvas;
    const marks = host.getBoundingClientRect ? host.getBoundingClientRect() : { left: 0, top: 0 };
    const box = canvas && canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : { left: 0, top: 0 };
    const ox = box.left - marks.left, oy = box.top - marks.top;
    const ring = (x, y, r, cls, code) => {
      const dot = document.createElement('span');
      dot.setAttribute('class', 'map-mark ' + cls);
      dot.setAttribute('data-code', code);
      dot.style.width = (2 * r).toFixed(1) + 'px';
      dot.style.height = (2 * r).toFixed(1) + 'px';
      dot.style.left = (ox + x).toFixed(1) + 'px';
      dot.style.top = (oy + y).toFixed(1) + 'px';
      host.appendChild(dot);
    };
    const site = !sel ? null : sel.kind === 'site' ? sel.id : sel.kind === 'message' ? sel.site : null;
    /* A site with no position is never drawn (PP-B5: it is listed under Unplaced), so it gets
       no ring. UX-3: a located site is drawn as part of its place's mark, so the ring circles it. */
    const row = site ? (snap.located || []).find((r) => r.code === site) : null;
    const place = row ? (snap.clusters || []).find((c) => c.codes.indexOf(site) >= 0) : null;
    if (place) ring(place.x, place.y, place.r + 3, 'site', row.code);
    else if (row) ring(row.x, row.y, row.r + 3, 'site', row.code);
    const link = sel && sel.kind === 'link' ? (snap.links || []).find((l) => l.id === sel.id) : null;
    if (link) ring(link.x, link.y, 8, 'link', link.id);
  }
  const minutes = (t) => Date.parse(t.slice(0, 16) + ':00Z') / 60000;

  // ---------- left column ----------
  function regionAt(g, t) {
    const i = D.rIndex.get(t);
    const r = D.regions.grids[g];
    if (i == null || !r) return null;
    const o = {};
    for (const k in r) o[k] = r[k][i];
    return o;
  }
  function renderBrief() {
    const t = D.t[state.i];
    const g = state.grid, name = GRIDS[g];
    const r = regionAt(g, t);
    const lz = regionAt('CLUZ', t);
    $('brief-title').textContent = `What's happening in ${name}`;
    if (!r) { $('brief-text').textContent = ''; return; }
    const parts = [];
    const at = `<span class="num">${hhmm(t)}</span>`;
    const known = (v) => v != null;
    const net = known(r.import_mw) && known(r.export_mw) ? r.import_mw - r.export_mw : null;
    let flowNote = '';
    const ri = D.rIndex.get(t);
    if (g === 'CVIS') {
      const mv = D.hvdc.links.MINVIS1 && D.hvdc.links.MINVIS1.flow[ri];
      const vl = D.hvdc.links.VISLUZ1 && D.hvdc.links.VISLUZ1.flow[ri];
      const bits = [];
      if (mv > 0) bits.push(`<span class="num">${fmt(mv)}</span> MW from <span class="ent" data-link="MINVIS1">Mindanao</span>`);
      if (vl < 0) bits.push(`<span class="num">${fmt(-vl)}</span> MW from <span class="ent" data-link="VISLUZ1">Luzon</span>`);
      if (bits.length) flowNote = ', ' + bits.join(' and ');
    }
    if (known(r.demand_mw)) {
      let s1 = `<span class="ent" data-figure="${g}:demand">${name} demand</span> is <b class="num">${fmt(r.demand_mw)}</b> MW at ${at}`;
      if (known(r.gen_mw)) s1 += `, with <span class="num">${fmt(r.gen_mw)}</span> MW generated on the grid`;
      if (net > 0) s1 += ` and <span class="num">${fmt(net)}</span> MW imported${flowNote}`;
      else if (net < 0) s1 += ` and <span class="num">${fmt(-net)}</span> MW exported`;
      parts.push(s1 + '.');
    }
    if (known(r.lmp_median)) {
      let p = `At ${at} the median <span class="ent" data-figure="${g}:price">${name} generator price</span> is <b class="num${r.lmp_median >= CAP * 0.97 ? ' hot' : ''}">${peso(r.lmp_median)}</b>/MWh`;
      if (r.lmp_median >= CAP) p += ', at the <span class="num">₱32,000</span> offer cap';
      else if (r.lmp_median >= CAP * 0.97) p += ', within 3% of the <span class="num">₱32,000</span> offer cap';
      if (g !== 'CLUZ' && lz && known(lz.lmp_median)) p += `; <span class="ent" data-figure="CLUZ:price">Luzon</span> clears at <span class="num">${peso(lz.lmp_median)}</span>`;
      parts.push(p + '.');
    }
    if (known(r.dr_short_mw) && r.dr_short_mw > 0) parts.push(`At ${at} <span class="ent" data-figure="${g}:reserve">${name} dispatchable reserve</span> is <b class="num hot">${fmt(r.dr_short_mw)}</b> MW short of the <span class="num">${fmt(r.dr_req_mw)}</span> MW requirement.`);
    else if (known(r.dr_short_mw) && known(r.dr_req_mw) && r.dr_req_mw > 0) parts.push(`At ${at} the <span class="num">${fmt(r.dr_req_mw)}</span> MW <span class="ent" data-figure="${g}:reserve">${name} dispatchable reserve</span> requirement is met.`);
    if (known(r.curtailed_mw) && r.curtailed_mw > 0) parts.push(`At ${at}, <b class="num hot">${fmt(r.curtailed_mw)}</b> MW of ${name} load is being curtailed.`);
    const recent = D.advisories.filter((a) => a.grid === g && a.t <= t && minutes(t) - minutes(a.t) <= 240 && a.kind !== 'notice').slice(-3);
    for (const a of recent) {
      parts.push(`NGCP <span class="ent" data-adv="${esc(a.id)}">${esc(a.id)}</span> at <span class="num">${hhmm(a.t)}</span>: ${opText(a.text).replace(/\s*\((Unplanned|Planned) Outage\)/, '')}.`);
    }
    $('brief-text').innerHTML = parts.join(' ').replace(/\.\./g, '.');
    $('brief-asof').textContent = `Replay of ${day(t)}, ${hhmm(t)} Manila time · written by code from the figures above`;
    /* Every entity in the narrative is a link to its element: a message to its detail (EXPL-1 wires
       `.ent[data-adv]`, `[data-link]` and `[data-figure]` after each render), with the feed scroll
       the page always did for a message. */
    for (const n of $('brief-text').querySelectorAll('.ent[data-adv]')) n.addEventListener('click', () => focusAdvisory(n.dataset.adv));
  }

  function renderFigures() {
    const t = D.t[state.i];
    const tb = $('figures').tBodies[0];
    tb.innerHTML = '';
    for (const g of ['CLUZ', 'CVIS', 'CMIN']) {
      const r = regionAt(g, t);
      const tr = document.createElement('tr');
      tr.dataset.grid = g;
      if (g === state.grid) tr.className = 'on';
      const net = r && r.import_mw != null && r.export_mw != null ? r.import_mw - r.export_mw : null;
      const reserve = !r || r.dr_short_mw == null ? '—' : r.dr_short_mw > 0 ? `<span class="bad">−${fmt(r.dr_short_mw)}</span>` : '<span class="ok">met</span>';
      tr.innerHTML = `<td><span class="dot ${band(r && r.lmp_median)}"></span>${GRIDS[g]}</td>` +
        `<td class="num" data-series="demand" title="Demand at ${hhmm(t)}, MW: the load the grid serves">${fmt(r && r.demand_mw)}</td>` +
        `<td class="num" data-series="price" title="Median generator price at ${hhmm(t)}, ₱/MWh">${r ? fmt(r.lmp_median) : '—'}</td>` +
        `<td class="num" data-series="flow" title="Net flow at ${hhmm(t)}, MW: + import into the grid, − export">${net == null ? '—' : (net > 0 ? '+' : '') + fmt(net)}</td>` +
        `<td class="num" data-series="reserve" title="Dispatchable reserve against its requirement at ${hhmm(t)}">${reserve}</td>`;
      tr.addEventListener('click', () => setGrid(g));
      tr.style.cursor = 'pointer';
      tb.appendChild(tr);
    }
    $('figures-asof').textContent = `At ${hhmm(t)} · demand MW · median generator price · flow MW, + import`;
  }

  function renderReviews() {
    const t = D.t[state.i];
    const open = D.events.filter((e) => e.t <= t);
    $('reviews').hidden = !open.length;
    $('review-list').innerHTML = open.map((e) => `<li><a href="/event/${esc(e.id)}"><div class="r-title">${esc(e.title)}</div>` +
      `<div class="r-meta">${esc(e.assumption)} · NGCP ${esc(e.advisory)} at ${hhmm(e.t)}</div><div class="r-go">Review impact →</div></a></li>`).join('');
  }

  // ---------- feed ----------
  /* PP-B5: the notices are a dense table under the map, newest first: time, the kind as the
     shared badge (the same word and style on every page), the grid, the text truncated on one
     line with its whole in the title, and the schedule lag (outages.js fills it). A row opens the
     notice on the map; a notice the desk made an event from leads with a link to that event. */
  const KIND_BADGE = { trip: ['Trip', 'alert'], red: ['Red alert', 'alert'], yellow: ['Yellow alert', 'warning'],
    mld: ['Load dropping', 'warning'], derate: ['Derate', 'warning'], online: ['Back online', 'info'], notice: ['Notice', 'info'] };
  const kindBadge = (kind) => {
    const ui = window.GNUI;
    if (ui && typeof ui.badgeHtml === 'function') return ui.badgeHtml(kind);
    const b = KIND_BADGE[kind];
    return b ? `<span class="gn-badge gn-badge--${b[1]} gn-sev">${b[0]}</span>` : `<span class="gn-badge">${esc(kind)}</span>`;
  };
  function renderFeed() {
    const t = D.t[state.i];
    const list = D.advisories.filter((a) => a.t <= t && a.t >= D.t[0] && (state.filter === 'all' || a.grid === state.filter)).slice(-60).reverse();
    const reviewFor = new Map(D.events.map((e) => [e.advisory, e]));
    const body = $('feed');
    body.innerHTML = list.map((a) => {
      const fresh = !state.seen.has(a.id) && minutes(t) - minutes(a.t) <= 5;
      const ev = reviewFor.get(a.id);
      const kind = a.kind === 'trip' && /derat/i.test(a.text) ? 'derate' : a.kind;
      const text = opText(a.text);
      return `<tr id="adv-${esc(a.id)}" class="f-row${fresh ? ' new' : ''}" tabindex="0" title="${esc(GRIDS[a.grid] || 'System')} · ${esc(a.kind)} · ${esc(a.id)} posted ${hhmm(a.t)}">` +
        `<td class="gn-num ft-time">${hhmm(a.t)}</td><td class="ft-kind">${kindBadge(kind)}</td>` +
        `<td class="trunc ft-grid">${GRIDS[a.grid] || 'System'}</td>` +
        `<td class="trunc ft-text" title="${text}">${ev ? `<a class="ft-event" href="/event/${esc(ev.id)}" data-entity="event:${esc(ev.id)}">Event</a>` : ''}${text}</td>` +
        `<td class="f-sched trunc"></td></tr>`;
    }).join('');
    for (const a of list) state.seen.add(a.id);
    $('feed-count').textContent = `${list.length} since 00:00`;
    /* An empty list says what is missing and why, and offers the next step: the other grids
       when a grid filter is on, a later clock otherwise. */
    const none = $('feed-empty');
    if (none) {
      none.hidden = list.length > 0;
      none.textContent = '';
      const wrap = $('feed-wrap');
      if (wrap) wrap.hidden = !list.length;
      if (!list.length) {
        const mk = (tag, cls, text) => { const n = document.createElement(tag); n.className = cls; if (text) n.textContent = text; return n; };
        const which = state.filter === 'all' ? '' : GRIDS[state.filter] + ' ';
        const box = mk('div', 'gn-empty');
        box.setAttribute('role', 'status');
        box.appendChild(mk('p', 'gn-empty-title', `No ${which}operator notice since 00:00`));
        box.appendChild(mk('p', 'gn-empty-body', `Nothing was posted by ${hhmm(t)}. Move the replay clock to see later hours.`));
        if (which) {
          const acts = mk('div', 'gn-empty-actions');
          const all = mk('button', 'gn-btn gn-btn--sm', 'Show all grids');
          all.setAttribute('type', 'button');
          all.addEventListener('click', () => setFeedFilter('all'));
          acts.appendChild(all);
          box.appendChild(acts);
        }
        none.appendChild(box);
      }
    }
  }
  /* The notices' own filter (All, Luzon, Visayas, Mindanao); the page grid and the map scope do
     not change it. */
  function setFeedFilter(f) {
    state.filter = f;
    for (const o of document.querySelectorAll('.filters button')) o.setAttribute('aria-pressed', String(o.dataset.filter === f));
    renderFeed();
  }
  function focusAdvisory(id) {
    const a = D.advisories.find((x) => x.id === id);
    /* the notices keep their own grid filter: if the message is filtered out, show all grids */
    if (a && state.filter !== 'all' && a.grid !== state.filter) setFeedFilter('all');
    const node = document.getElementById('adv-' + id);
    if (node) { node.scrollIntoView({ block: 'center', behavior: 'smooth' }); node.classList.remove('new'); void node.offsetWidth; node.classList.add('new'); }
  }

  // ---------- chart ----------
  function renderChart() {
    const svg = $('chart');
    const box = svg.getBoundingClientRect();
    const W = Math.max(300, box.width), H = Math.max(140, box.height);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = '';
    const g = state.grid, r = D.regions.grids[g];
    const times = D.t;
    const idx = times.map((t) => D.rIndex.get(t));
    const dem = idx.map((i) => (i == null ? null : r.demand_mw[i]));
    /* EXPL-1: the line is the selected series — the price by default, or net flow, reserve
       shortfall (with its requirement dashed) or one link's flow after a click on a figure cell
       or a link; the demand area stays, since every other series is read against it. */
    const series = state.series || 'price';
    const linkId = series.startsWith('link:') ? series.slice(5) : null;
    const pr = idx.map((i) => (i == null ? null : r.lmp_median[i]));
    const lineVals = linkId ? idx.map((i) => (i == null || !D.hvdc.links[linkId] ? null : D.hvdc.links[linkId].flow[i]))
      : series === 'flow' ? idx.map((i) => (i == null || r.import_mw[i] == null || r.export_mw[i] == null ? null : r.import_mw[i] - r.export_mw[i]))
      : series === 'reserve' ? idx.map((i) => (i == null ? null : r.dr_short_mw[i]))
      : series === 'demand' ? dem : pr;
    const reqVals = series === 'reserve' ? idx.map((i) => (i == null ? null : r.dr_req_mw[i])) : null;
    const L = 44, R = 52, T = 14, B = 20;
    const x = (i) => L + (i / (times.length - 1)) * (W - L - R);
    const knownDem = dem.filter((v) => v != null);
    // A positive, finite range whatever the data: empty, all-zero or tiny series still draw finite geometry.
    const dmax = Math.max(1, knownDem.length ? Math.max(...knownDem) * 1.12 : 1), dmin = 0;
    const yd = (v) => T + (1 - (v - dmin) / (dmax - dmin)) * (H - T - B);
    const knownLine = lineVals.filter((v) => v != null);
    const lmax = Math.max(1, ...knownLine.map(Math.abs), ...(reqVals ? reqVals.filter((v) => v != null) : [])) * 1.1;
    const signed = knownLine.some((v) => v < 0);
    const yp = series === 'price' ? ((v) => T + (1 - Math.min(v, CAP) / CAP) * (H - T - B))
      : series === 'demand' ? ((v) => yd(v))
      : signed ? ((v) => T + (1 - (v + lmax) / (2 * lmax)) * (H - T - B))
      : ((v) => T + (1 - v / lmax) * (H - T - B));
    el('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, class: 'axis' }, svg);
    /* The time axis: three-hourly ticks over one day; one tick per day when the replay axis spans
       several days (EXPL-1: the bake carries 21 to 29 September, and a day's ticks drawn over
       nine days collided at the left edge). */
    const days = Math.max(1, Math.round(times.length / 288));
    if (days === 1) {
      for (let h = 0; h <= 24; h += 3) {
        const i = Math.min(times.length - 1, h * 12);
        el('text', { x: x(i), y: H - 5, class: 'tick', 'text-anchor': 'middle' }, svg).textContent = h === 24 ? '24:00' : String(h).padStart(2, '0') + ':00';
      }
    } else {
      for (let d = 0; d < days; d++) {
        const i = Math.min(times.length - 1, d * 288);
        el('text', { x: x(i), y: H - 5, class: 'tick', 'text-anchor': 'start' }, svg).textContent = new Date(times[i].slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
      }
    }
    [0, 0.5, 1].forEach((f) => {
      const v = dmin + f * (dmax - dmin);
      el('text', { x: L - 6, y: yd(v) + 3, class: 'tick', 'text-anchor': 'end' }, svg).textContent = fmt(Math.round(v / 100) * 100);
      if (series === 'price') el('text', { x: W - R + 6, y: yp(f * CAP) + 3, class: 'tick' }, svg).textContent = (f * 32).toFixed(0) + 'k';
      else if (series !== 'demand') { const v = signed ? -lmax + f * 2 * lmax : f * lmax; el('text', { x: W - R + 6, y: yp(v) + 3, class: 'tick' }, svg).textContent = fmt(Math.round(v)); }
    });
    // Paths break at missing samples: a gap is drawn as a gap, never bridged.
    const segments = (series, y) => {
      const out = []; let cur = [];
      series.forEach((v, i) => { if (v == null) { if (cur.length) out.push(cur); cur = []; } else cur.push([x(i), y(v)]); });
      if (cur.length) out.push(cur);
      return out;
    };
    const line = (seg) => seg.map(([px, py], k) => (k ? 'L' : 'M') + px.toFixed(1) + ',' + py.toFixed(1)).join('');
    for (const seg of segments(dem, yd)) {
      el('path', { d: line(seg) + `L${seg[seg.length - 1][0].toFixed(1)},${H - B}L${seg[0][0].toFixed(1)},${H - B}Z`, class: 'area' }, svg);
      el('path', { d: line(seg), class: 'area-line' }, svg);
    }
    if (series !== 'demand') for (const seg of segments(lineVals, yp)) el('path', { d: line(seg), class: series === 'price' ? 'price' : series === 'reserve' ? 'reserve' : 'flow' }, svg);
    /* A link's congested intervals, as marks along the baseline under its flow (the hvdc file's
       `congested` flag per interval), so the chart carries what the map's label says at one time. */
    if (linkId && D.hvdc.links[linkId]) {
      const cong = D.hvdc.links[linkId].congested;
      idx.forEach((ri, i) => { if (ri != null && cong[ri]) el('rect', { x: x(i) - 1, y: H - B - 5, width: 2, height: 5, class: 'congested-mark' }, svg); });
    }
    if (reqVals) for (const seg of segments(reqVals, yp)) el('path', { d: line(seg), class: 'req' }, svg);
    const last = times.length - 1;
    let lastDem = -1;
    for (let i = dem.length - 1; i >= 0; i--) if (dem[i] != null) { lastDem = i; break; }
    if (lastDem >= 0) {
      const dl = el('text', { x: x(lastDem) - 4, y: yd(dem[lastDem]) - 6, class: 'label', 'text-anchor': 'end', fill: 'rgba(143,211,255,.85)' }, svg);
      dl.textContent = `Demand ${fmt(dem[lastDem])} MW at ${hhmm(times[lastDem])}`;
    }
    for (const adv of D.advisories) {
      if (adv.grid !== g || !['trip', 'mld', 'yellow', 'red'].includes(adv.kind) || !adv.t.startsWith(times[0].slice(0, 10))) continue;
      const i = Math.round((minutes(adv.t) - minutes(times[0])) / 5);
      if (i < 0 || i > last) continue;
      el('rect', { x: x(i) - 1, y: T - 2, width: 2, height: 6, class: 'mark' }, svg);
    }
    const ni = state.i;
    el('line', { x1: x(ni), x2: x(ni), y1: T - 4, y2: H - B, class: 'now' }, svg);
    const pv = series === 'demand' ? null : lineVals[ni];
    if (pv != null) {
      const t = el('text', { x: x(ni) + 6, y: yp(pv) - 6, class: 'label', fill: series === 'price' ? '#f2b134' : series === 'reserve' ? '#ff5a5a' : '#8fd3ff' }, svg);
      t.textContent = `${series === 'price' ? peso(pv) : fmt(pv) + ' MW'} at ${hhmm(times[ni])}`;
    }
    const what = linkId ? `${LINKS[linkId].name} flow` : series === 'flow' ? 'net flow' : series === 'reserve' ? 'reserve shortfall' : series === 'demand' ? 'demand' : 'price';
    /* FRONT-1: the title names the span the axis shows — the whole replay, not the clock's day —
       and the subtitle carries the clock's own day, so the two never contradict each other. */
    $('chart-title').textContent = series === 'demand' ? `${GRIDS[g]} demand, ${spanWords(times)}` : `${GRIDS[g]} demand and ${what}, ${spanWords(times)}`;
    const unit = series === 'price' ? 'median generator price ₱/MWh (line)' : series === 'demand' ? 'demand MW (area)' : series === 'reserve' ? 'dispatchable reserve shortfall MW (line) and requirement (dashed)' : linkId ? `${LINKS[linkId].name} flow MW (line, + ${LINKS[linkId].from} → ${LINKS[linkId].to})` : 'net flow MW (line, + import)';
    $('chart-asof').textContent = `Replay of ${day(times[state.i])}, ${hhmm(times[state.i])} Manila time · five-minute intervals · demand MW (area) · ${unit}`;
    chartGeometry = { x, times, series, linkId, lineVals, dem };
  }

  // ---------- EXPL-2: the day as a path ----------
  /* The selected grid's messages of the clock's day, in order, up to the clock; their vectors
     added one by one (clipped at `max_norm`, as the spike trained) and projected onto the two
     learned directions. An exploratory view: no score, no probability, no risk colour. */
  const pathPlane = { ready: false };
  function pathProject(v) {
    const P = D.vectors.plane, mean = pathPlane.mean;
    let x = 0, y = 0;
    for (let j = 0; j < v.length; j++) { x += (v[j] - mean[j]) * P[j][0]; y += (v[j] - mean[j]) * P[j][1]; }
    return [x, y];
  }
  function preparePath() {
    const E = D.vectors.E, dim = E[0].length;
    const mean = new Array(dim).fill(0);
    for (const row of E) for (let j = 0; j < dim; j++) mean[j] += row[j] / E.length;
    pathPlane.mean = mean;
    const pts = E.map((row) => pathProject(row));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    pathPlane.scale = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) * 0.6 || 1;
    pathPlane.center = [cx, cy];
    pathPlane.types = pts;
    pathPlane.ready = true;
  }
  function renderPath() {
    const wrap = $('path-wrap');
    if (!D.vectors || !pathPlane.ready) { wrap.hidden = true; return; }
    wrap.hidden = false;
    const svg = $('path');
    const box = svg.getBoundingClientRect();
    const W = Math.max(160, box.width), H = Math.max(120, box.height);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = '';
    const now = D.t[state.i], today = now.slice(0, 10);
    const steps = D.advisories.filter((a) => a.grid === state.grid && a.t.slice(0, 10) === today && a.t <= now);
    /* The running sum, one typed message at a time, projected; the panel is scaled to the
       day's own path so a short path is still readable, with the vocabulary's dots faint behind. */
    let h = new Array(D.vectors.E[0].length).fill(0);
    const raw = [pathProject(h)];
    const drawn = [];
    for (const a of steps) {
      const k = D.vectors.types[a.id];
      if (k == null) continue;
      const e = D.vectors.E[k];
      h = h.map((v, j) => v + e[j]);
      const n = Math.hypot(...h);
      if (n > D.vectors.max_norm) h = h.map((v) => (v * D.vectors.max_norm) / n);
      raw.push(pathProject(h));
      drawn.push({ a, p: raw[raw.length - 1], type: D.vectors.vocab[k] });
    }
    const xs = raw.map((p) => p[0]), ys = raw.map((p) => p[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), pathPlane.scale * 0.15);
    const S = Math.min(W, H) * 0.42;
    const X = (x) => W / 2 + ((x - cx) / span) * S * 2, Y = (y) => H / 2 - ((y - cy) / span) * S * 2;
    const [ox, oy] = pathPlane.center;
    el('line', { x1: 0, x2: W, y1: Y(oy).toFixed(1), y2: Y(oy).toFixed(1), class: 'p-axis' }, svg);
    el('line', { x1: X(ox).toFixed(1), x2: X(ox).toFixed(1), y1: 0, y2: H, class: 'p-axis' }, svg);
    for (const p of pathPlane.types) {
      const px = X(p[0]), py = Y(p[1]);
      if (px >= 0 && px <= W && py >= 0 && py <= H) el('circle', { cx: px.toFixed(1), cy: py.toFixed(1), r: 1.6, class: 'p-type' }, svg);
    }
    const points = raw.map(([px, py]) => [X(px), Y(py)]);
    for (const d of drawn) { d.x = X(d.p[0]); d.y = Y(d.p[1]); }
    if (points.length > 1) el('path', { d: points.map(([x, y], i) => (i ? 'L' : 'M') + x.toFixed(1) + ',' + y.toFixed(1)).join(''), class: 'p-line' }, svg);
    for (const d of drawn) {
      const c = el('circle', { cx: d.x.toFixed(1), cy: d.y.toFixed(1), r: 3.2, class: 'p-step ' + d.a.kind, 'data-adv': d.a.id }, svg);
      el('title', {}, c).textContent = `${hhmm(d.a.t)} · ${d.type}`;
    }
    if (drawn.length) el('circle', { cx: drawn[drawn.length - 1].x.toFixed(1), cy: drawn[drawn.length - 1].y.toFixed(1), r: 2, class: 'p-now' }, svg);
    el('text', { x: 4, y: H - 4, class: 'p-label' }, svg).textContent = `${drawn.length} of ${steps.length} messages typed`;
    $('path-title').textContent = `${GRIDS[state.grid]} on ${day(now)} as a path, to ${hhmm(now)}`;
    $('path-asof').textContent = `Exploratory view: each message adds its learned vector; the two axes are the learned plane. Learned from ${fmt(D.vectors.corpus.messages)} operator messages, ${D.vectors.corpus.span}. Not a forecast; no score.`;
  }

  // ---------- clock ----------
  /* FRONT-1: the front strip is open in the markup, so the first visit reads all of it. On a
     later visit it folds to its one-line summary; the only thing stored is that flag, and a
     browser that refuses storage keeps the strip open rather than losing it. */
  function foldFront() {
    const front = $('front-details');
    if (!front) return;
    try {
      if (!window.localStorage) return;
      if (window.localStorage.getItem('nowcast-front-seen')) front.open = false;
      else window.localStorage.setItem('nowcast-front-seen', '1');
    } catch (err) { /* storage refused: the strip stays open, and the page loses nothing */ }
  }
  /* UX-3: the replay's scrub track carries a tick for each alert and warning notice of the span
     it covers, by severity, so a reader can see where the day turned. Rebuilt when the span or
     its notices change. */
  let ticksKey = null;
  function renderTicks() {
    const host = $('scrub-ticks');
    if (!host || !D.t.length) return;
    const first = minutes(D.t[0]), span = Math.max(5, minutes(D.t[D.t.length - 1]) - first);
    const key = D.t[0] + '|' + D.t.length + '|' + D.advisories.length;
    if (key === ticksKey) return;
    ticksKey = key;
    while (host.lastChild) host.removeChild(host.lastChild);
    const sevOf = window.GridMap && window.GridMap.math && window.GridMap.math.severityOf;
    for (const a of D.advisories) {
      const sev = sevOf ? sevOf(a) : (a.kind === 'red' || a.kind === 'trip' ? 'alert' : a.kind === 'yellow' || a.kind === 'mld' ? 'warning' : 'info');
      if (sev === 'info') continue;
      const at = (minutes(a.t) - first) / span;
      if (!(at >= 0 && at <= 1)) continue;
      const tick = document.createElement('span');
      tick.setAttribute('class', 'rp-tick ' + sev);
      tick.style.left = (at * 100).toFixed(2) + '%';
      host.appendChild(tick);
    }
  }
  function renderClock() {
    const t = D.t[state.i];
    $('clock-time').textContent = `${hhmm(t)} PHT` + (D.missing ? ' · No data' : '');
    const date = $('clock-date');
    if (date) date.textContent = $('clock-day') ? '' : day(t);
    renderTicks();
    const pick = $('clock-day');
    if (pick) {
      pick.min = D.span.first.slice(0, 10); pick.max = D.span.last.slice(0, 10); pick.value = t.slice(0, 10);
      pick.title = D.missing ? 'No data for this day in the company copy' : 'Replay day';
    }
    $('scrub').value = state.i;
    history.replaceState(null, '', `#t=${hhmm(t)}&g=${state.grid}` + (REPLAY.index ? `&d=${t.slice(0, 10)}` : ''));
  }
  let chartGeometry = null;
  let briefsPanel = null;
  const renderListeners = [];
  /* ATG-8: the briefing and the findings feed follow the same clock and the same grid as the
     rest of the page — one panel, redrawn by the page's own render, never a second clock. */
  function renderBriefs() {
    if (!briefsPanel) return;
    briefsPanel.setGrid(state.grid);
    briefsPanel.setClock(D.t[state.i]);
  }
  function render() { renderClock(); renderMapPanel(); renderBrief(); renderFigures(); renderReviews(); renderFeed(); renderChart(); renderPath(); renderBriefs(); for (const f of renderListeners) f(); }
  /* EXPL-1: the public surface grid-explore.js wires the clicks to. Everything here is the
     page's own state and renderers; nothing new is fetched through it. */
  function expose() {
    window.GridDesk = {
      get D() { return D; }, state, GRIDS, LINKS, setTime, setGrid, play, renderChart, regionAt, day,
      get mapPanel() { return mapPanel; }, markMap,
      indexAt, goto, get replay() { return REPLAY.index; },
      seriesValueAt: (i) => {
        if (!chartGeometry) return null;
        const v = chartGeometry.series === 'demand' ? chartGeometry.dem[i] : chartGeometry.lineVals[i];
        return v == null ? null : chartGeometry.series === 'price' ? peso(v) + '/MWh' : fmt(v) + ' MW';
      },
      onRender: (f) => { renderListeners.push(f); },
    };
    // A DOM shim without `Event` (the offline render harness) gets the surface and no signal.
    if (typeof Event === 'function' && typeof window.dispatchEvent === 'function') window.dispatchEvent(new Event('grid-desk-ready'));
  }
  function setTime(i) {
    if (REPLAY.index && (i < 0 || i >= D.t.length)) {
      const d = SHELL.dayPlus(D.day, i < 0 ? -1 : 1);
      if (d < D.span.first.slice(0, 10) || d > D.span.last.slice(0, 10)) { if (state.playing) play(false); return; }
      const m = i < 0 ? 1440 - STEP : 0;
      goto(`${d}T${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`);
      return;
    }
    state.i = Math.max(0, Math.min(D.t.length - 1, i));
    render();
  }
  const indexAt = (t) => { const key = String(t).slice(0, 16); const i = D.t.findIndex((x) => x >= key); return i < 0 ? D.t.length - 1 : i; };
  /* Any time in the span: the same day moves the clock; another day is read first, then drawn.
     The latest request wins when several are in flight. */
  function goto(t) {
    const key = String(t).slice(0, 16);
    if (!REPLAY.index || key.slice(0, 10) === D.day) { const i = indexAt(key); if (i !== state.i) setTime(i); return Promise.resolve(); }
    const d = key.slice(0, 10);
    const ticket = REPLAY.loading = {};
    const hadNodes = NODES;
    return readDay(d).then((got) => {
      if (REPLAY.loading !== ticket) return;
      adoptDay(d, got);
      $('scrub').max = D.t.length - 1;
      state.i = indexAt(key);
      for (const a of D.advisories) if (a.t < D.t[state.i]) state.seen.add(a.id);
      if (NODES !== hadNodes || !NODES) {
        D.nodes = null; D.siteIndex = null; D.rowIndex = null;
        if (mapPanel && mapPanel.setNodes) mapPanel.setNodes(null);
        if (NODES) nodeLayer(NODES).then((layer) => { if (REPLAY.loading === ticket && layer) takeNodes(layer); });
      }
      setCaption();
      render();
    });
  }
  function takeNodes(layer) {
    D.nodes = layer.file;
    D.siteIndex = layer.siteIndex;
    D.rowIndex = layer.rowIndex;
    if (mapPanel && mapPanel.setNodes) mapPanel.setNodes(D.nodes);
    renderMapPanel();
    if (window.GridExplore && window.GridExplore.refresh) window.GridExplore.refresh();
    for (const f of renderListeners) f();
  }
  function setCaption() {
    const pending = D.sites.filter((s) => s.p === 'placeholder').length;
    const approx = D.sites.filter((s) => s.p === 'approximate').length;
    const span = REPLAY.index ? `replay ${dayShort(D.span.first)} to ${dayShort(D.span.last)}, showing ${day(D.t[0])}${D.missing ? ' (No data for this day)' : ''}` : `replay of ${day(D.t[0])}`;
    $('caption').textContent = `Source: WESM five-minute market data (company copy) and NGCP system-operator messages · ${span}, Manila time · prices in ₱/MWh · ${D.sites.length - pending - approx} of ${D.sites.length} sites located${approx ? `, ${approx} at approximate positions` : ''}, ${pending} with no position listed under Unplaced` +
      (REPLAY.index && !NODES ? ' · site prices: No data for this day (node prices are kept for the latest days only)' : '');
  }
  function setGrid(g) {
    state.grid = g;
    for (const b of document.querySelectorAll('.grids button')) b.setAttribute('aria-pressed', String(b.dataset.grid === g));
    render();
  }
  /* UX-3: the replay's speed, 1x, 2x or 4x of the 450 ms step. */
  const SPEEDS = [1, 2, 4];
  let speed = 1;
  function play(on) {
    state.playing = on;
    $('play').setAttribute('aria-label', on ? 'Pause' : 'Play');
    $('play-glyph').setAttribute('d', on ? 'M4 3h3v10H4zM9 3h3v10H9z' : 'M5 3v10l8-5z');
    clearInterval(state.timer);
    if (on) state.timer = setInterval(() => {
      if (REPLAY.loading && REPLAY.day !== D.day) return;
      if (state.i >= D.t.length - 1 && !REPLAY.index) play(false); else setTime(state.i + 1);
    }, 450 / speed);
  }
  function setSpeed(next) {
    speed = next;
    const b = $('play-speed');
    if (b) { b.textContent = speed + '×'; b.setAttribute('aria-label', `Replay speed ${speed} times`); }
    if (state.playing) play(true);
  }

  function wire() {
    for (const b of document.querySelectorAll('.grids button')) b.addEventListener('click', () => setGrid(b.dataset.grid));
    for (const b of document.querySelectorAll('[data-step]')) b.addEventListener('click', () => { play(false); setTime(state.i + Number(b.dataset.step)); });
    $('play').addEventListener('click', () => play(!state.playing));
    if ($('play-speed')) $('play-speed').addEventListener('click', () => setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]));
    $('scrub').max = D.t.length - 1;
    /* replay-year: a date input over the whole span beside the dashboard's own clock. */
    if (REPLAY.index && !$('clock-day') && $('clock-time')) {
      const pick = document.createElement('input');
      pick.type = 'date'; pick.id = 'clock-day'; pick.className = 'gn-rp-day mono'; pick.required = true;
      pick.setAttribute('aria-label', 'Replay day');
      pick.addEventListener('change', () => {
        play(false);
        if (SHELL.validAt(pick.value + 'T00:00')) goto(pick.value + 'T' + hhmm(D.t[state.i]));
      });
      $('clock-time').parentElement.insertBefore(pick, $('clock-time'));
    }
    $('scrub').addEventListener('input', (e) => { play(false); setTime(Number(e.target.value)); });
    for (const b of document.querySelectorAll('.filters button')) b.addEventListener('click', () => setFeedFilter(b.dataset.filter));
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;
      if (e.key === 'ArrowRight') setTime(state.i + 1);
      else if (e.key === 'ArrowLeft') setTime(state.i - 1);
      else if (e.key === ' ') { e.preventDefault(); play(!state.playing); }
    });
    /* The canvas redraws itself at its own box (the module re-fits on a box change); the page
       only has to repeat its render, which drives the canvas with the clock and the grid. */
    let pending = null;
    window.addEventListener('resize', () => { clearTimeout(pending); pending = setTimeout(() => { render(); }, 150); });
  }

  function initialState() {
    const h = new URLSearchParams(location.hash.slice(1));
    const g = h.get('g');
    if (g && GRIDS[g]) state.grid = g;
    const want = REPLAY.index ? (h.get('t') || SHELL.asOf().slice(11, 16)) : (h.get('t') || START);
    const i = D.t.findIndex((t) => hhmm(t) === want);
    state.i = i >= 0 ? i : 0;
    for (const b of document.querySelectorAll('.grids button')) b.setAttribute('aria-pressed', String(b.dataset.grid === state.grid));
  }

  const loading = 'Loading the replay…';
  $('brief-text').textContent = loading;
  const wrap = document.querySelector('.map-wrap');
  wrap.classList.add('loading');
  load().then(({ nodes, get }) => {
    /* Stage 1: everything the six small files carry — the brief, the figures table, the review
       list, the operator-message feed, the chart, and the map outline with its sites, links and
       sites listed under Unplaced. Nothing here waits on the node file. `pricing` marks the map as drawn but
       not yet priced, which is the state the site layer below ends. */
    wrap.classList.remove('loading');
    wrap.classList.add('pricing');
    initialState();
    foldFront();
    for (const a of D.advisories) if (a.t < D.t[state.i]) state.seen.add(a.id);
    mountMap();
    wire();
    render();
    try { expose(); } catch (err) { /* a DOM shim without the surface: the page is drawn, the clicks are not wired */ }
    setCaption();
    /* The page is drawn: one fire-and-forget `GET /health` after this first paint wakes a cold
       Cloud Run instance while the judge reads, before any decision call. It is sent once,
       never awaited, and changes nothing on the page if it fails — the replay is already drawn
       and the request is not part of it, so the rejection is caught and the answer is ignored. */
    requestAnimationFrame(() => setTimeout(() => { fetch('/health').catch(() => {}); }, 0));
    /* Stage 2: the site layer, which is the node file's own — one price and one MW figure per
       site, the values the dots are coloured by and the tooltip reads. Until this lands `pricing`
       is on the map: the outline is drawn and the prices are not. Returning the promise here is
       what makes this a second stage: the callback below runs when the node file arrives, or
       with `null` when it cannot be read. */
    /* EXPL-2: the vector table is optional and asked for only after the first paint, with the
       warm-up: the first screen's seven files are unchanged, and a bake without the table
       leaves the path panel hidden. */
    requestAnimationFrame(() => setTimeout(() => {
      get('vectors.json', true).then((table) => {
        if (!table || !table.E || !table.plane || !table.types) return;
        D.vectors = table;
        try { preparePath(); renderPath(); } catch (err) { D.vectors = null; }
      }, () => {});
    }, 0));
    /* ATG-8: the briefing and the findings feed (ATG-5), mounted beside the operator messages.
       The two composed files are read in the same after-the-first-paint stage as the table
       above, so the first screen makes no new request (PERF-5); both are optional, and a bake
       without them leaves the mount point hidden rather than drawing an empty panel. `links`
       hands the panel the page's own openers (EXPL-1), so a reference inside the panel opens
       exactly what the same reference opens elsewhere on the page.
       PERF-6: on the one-year bake the two files are 55 MB (findings.json) and 4.6 MB
       (briefs.json), and the dashboard folds the panel away (dashboard.css hides the mount). So
       they are read only when the mount would be drawn, and once: checked after the first paint
       and again when the window is resized, one read in flight at most. */
    let briefsRead = null;
    const briefsDrawn = (mount) => {
      if (typeof mount.getClientRects !== 'function') return true;  // a DOM shim without layout draws everything
      const was = mount.hidden;
      mount.hidden = false;  // the mount stays hidden until the panel lands: ask whether it would be drawn
      const drawn = mount.getClientRects().length > 0;
      mount.hidden = was;
      return drawn;
    };
    const readBriefs = () => {
      const mount = $('briefs-mount');
      if (briefsRead || !mount || !briefsDrawn(mount)) return;
      briefsRead = Promise.all([get('briefs.json', true), get('findings.json', true)]).then(([briefs, findings]) => {
        if (!briefs || !findings || !window.GridBriefs) return;
        const mount = $('briefs-mount');
        const explore = () => window.GridExplore || {};
        if (!mount) return;
        briefsPanel = window.GridBriefs.mount(mount, { briefs, findings }, {
          grid: state.grid, clock: D.t[state.i],
          figure: (ref) => { const [g, k] = String(ref).split(':'); if (explore().figure) explore().figure(g, k); },
          link: (id) => { if (explore().link) explore().link(id); },
          message: (id) => { if (explore().message) explore().message(id); },
          site: (code) => { if (explore().site) explore().site(code); },
        });
        mount.hidden = false;
      }, () => {});
    };
    requestAnimationFrame(() => setTimeout(readBriefs, 0));
    if (typeof window.addEventListener === 'function') window.addEventListener('resize', readBriefs);
    return nodes;
  }).then((layer) => {
    if (!layer) {
      wrap.classList.remove('pricing');
      if (NODES) $('caption').textContent += ` · site prices unavailable (${NODES})`;
      return;
    }
    if (REPLAY.index && NODES !== `nodes-${layer.file.t[0].slice(0, 10)}.json`) { wrap.classList.remove('pricing'); return; }
    D.nodes = layer.file;
    D.siteIndex = layer.siteIndex;
    D.rowIndex = layer.rowIndex;
    /* The node file's layer is handed to the canvas that is already mounted (`setNodes`), not a
       new one: the draw it makes is the page's staged draw finishing, and everything the reader
       chose before it landed — the layer chips, the scope, the pan and zoom, the open tooltip —
       stays exactly as it was (ATG-8's correction of the reviewed remount). The page's own ring
       is re-placed at the spot the new draw painted. */
    if (mapPanel && mapPanel.setNodes) mapPanel.setNodes(D.nodes);
    renderMapPanel();
    if (window.GridExplore && window.GridExplore.refresh) window.GridExplore.refresh();
    wrap.classList.remove('pricing');
    /* UX-3: the state card's dots and the layer counts read the map's price scale, which the
       node file has just given it. */
    for (const f of renderListeners) f();
  }).catch((err) => {
    document.querySelector('.desk').innerHTML = `<p class="card load-error">The replay data could not be loaded (${esc(err.message)}).</p>`;
  });
})();

/* EXPL-1: every element on the grid page explorable (second module of this file; the asset
   allowlist names grid.js, so it lives here). The first module exposes the page's state, data
   and renderers on `window.GridDesk` once the first stage has drawn; this one wires the clicks
   and draws the detail card. It reads the same baked
   files, makes no request of its own and never calls a model.

   Interactions (docs/work/explore/intent.md):
     figure cell  -> that series on the chart for that grid; the cell stays marked
     site dot     -> detail: name, code, grid, capacity, position, two sparklines, its messages
     feed message -> clock to its time; the site it names is marked and its detail opens
     link         -> detail: flow now, direction, congestion, block/de-block messages; chart shows the flow
     chart point  -> clock to that time; hover shows value and time
     Escape       -> close the detail */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => {
    const node = document.createElementNS(svgNS, tag);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const peso = (v) => (v == null ? '—' : '₱' + fmt(v));
  const hhmm = (t) => (t || '').slice(11, 16);
  const opText = (s) => esc(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');
  const KIND = { trip: 'Trip', mld: 'Load dropping', yellow: 'Yellow alert', red: 'Red alert', online: 'Back online', notice: 'Notice' };
  const SERIES = {
    demand: { label: 'demand', unit: 'MW', def: 'Demand: the load the grid serves, MW, every five minutes.' },
    price: { label: 'median generator price', unit: '₱/MWh', def: 'Price: the median of the five-minute locational prices at the grid\'s generator nodes, ₱/MWh.' },
    flow: { label: 'net flow', unit: 'MW', def: 'Flow: import minus export over the undersea links, MW; positive is power coming into the grid.' },
    reserve: { label: 'dispatchable reserve shortfall', unit: 'MW', def: 'Reserve: the dispatchable reserve the operator requires, and the shortfall against it, MW.' },
  };
  const FIELD_OF = { demand: 'demand_mw', price: 'lmp_median' };
  let G = null;            // window.GridDesk, set by grid.js
  let sel = null;          // { kind, id }

  /* ---------- tokens: the words of a site code that an operator message would use ---------- */
  function siteTokens(code) {
    // Real codes carry letters after a numeric prefix ("08PEDC" -> PEDC); fixture codes are
    // letter groups ("SYN-BAY-1" -> SYN, BAY). Groups shorter than three letters name nothing.
    return (String(code).match(/[A-Za-z]{3,}/g) || []).map((t) => t.toUpperCase());
  }
  function mentions(text, tokens) {
    const up = String(text).toUpperCase();
    return tokens.some((t) => new RegExp('(^|[^A-Z])' + t + '($|[^A-Z])').test(up));
  }
  function messagesNaming(site) {
    const tokens = siteTokens(site.s);
    const named = G.D.advisories.filter((a) => mentions(a.text, tokens));
    const viaEvent = G.D.events.filter((e) => e.site === site.s).map((e) => e.advisory);
    return { tokens, list: G.D.advisories.filter((a) => named.includes(a) || viaEvent.includes(a.id)) };
  }
  /* Which site a message names: the event spec's explicit mapping (events.json) first; otherwise a
     site whose code tokens the text contains, and only when exactly one site matches. Several
     matches are returned as candidates and shown as such — a name token does not establish
     identity, so the page never picks one for the reader. */
  function sitesNamedBy(message) {
    const text = String(message.text);
    const ev = G.D.events.find((e) => e.advisory === message.id);
    if (ev) { const s = G.D.sites.find((x) => x.s === ev.site); if (s) return { site: s, candidates: [s], how: 'the event record' }; }
    const hits = G.D.sites.filter((s) => (message.grid == null || s.g === message.grid) && mentions(text, siteTokens(s.s)));
    return { site: hits.length === 1 ? hits[0] : null, candidates: hits, how: hits.length === 1 ? 'its code in the text' : null };
  }

  /* ---------- the detail card ---------- */
  function open(title, html) {
    $('d-title').textContent = title;
    $('d-body').innerHTML = html;
    $('detail').hidden = false;
    /* UX-3: on a phone the detail follows the map in the page; bring it into view, except when
       the tap pinned the list of a place of several assets (the list is the answer, and the
       reader taps again there to step through them) */
    const pinnedList = G.mapPanel && G.mapPanel.pinnedOpen && G.mapPanel.pinnedOpen();
    if (!pinnedList && window.matchMedia && window.matchMedia('(max-width: 760px)').matches && $('detail').scrollIntoView) $('detail').scrollIntoView({ block: 'nearest' });
    for (const n of $('d-body').querySelectorAll('[data-adv]')) n.addEventListener('click', () => selectMessage(n.dataset.adv));
    for (const n of $('d-body').querySelectorAll('[data-site]')) n.addEventListener('click', () => selectSite(n.dataset.site));
    for (const n of $('d-body').querySelectorAll('[data-link]')) n.addEventListener('click', () => selectLink(n.dataset.link));
    for (const n of $('d-body').querySelectorAll('[data-t]')) n.addEventListener('click', () => G.setTime(G.indexAt(n.dataset.t)));
    for (const n of $('d-body').querySelectorAll('[data-span]')) n.addEventListener('click', () => { showSpan = n.dataset.span === 'all'; reopen(); });
  }
  function reopen() {
    if (!sel) return;
    if (sel.kind === 'site') selectSite(sel.id); else if (sel.kind === 'link') selectLink(sel.id); else if (sel.kind === 'message') selectMessage(sel.id);
  }
  function close() {
    sel = null;
    $('detail').hidden = true;
    mark();
    G.renderChart();
  }
  function mark() {
    /* The map's own mark is the page's canvas section's (a canvas holds no element per site):
       `markMap` draws the ring on the site or the link this selection opened. */
    if (G.markMap) G.markMap(sel);
    for (const li of $('feed').children) li.classList.toggle('sel', !!sel && sel.kind === 'message' && li.id === 'adv-' + sel.id);
    for (const td of $('figures').querySelectorAll('td.num')) td.classList.toggle('sel', !!sel && sel.kind === 'figure' && td.dataset.series === G.state.series && td.parentElement.dataset.grid === G.state.grid);
  }
  /* The messages of the clock's own day, newest first, at most twelve; the rest of the span is
     counted, never listed — a link's block and de-block notices alone run to hundreds. */
  /* The messages of the clock's own day first, newest first; "Show all" lists the whole replay span,
     grouped by day, so every message the detail counts can be opened. */
  let showSpan = false;
  function msgRow(a, withDay) {
    return `<li data-adv="${esc(a.id)}"><span class="t">${withDay ? esc(a.t.slice(5, 10)) + ' ' : ''}${hhmm(a.t)}</span><span class="k ${esc(a.kind)}">${esc(KIND[a.kind] || a.kind)}</span>${opText(a.text).replace(/\s*\((Unplanned|Planned) Outage\)/, '')}</li>`;
  }
  function msgList(list, empty) {
    if (showSpan && list.length) {
      const all = list.slice().reverse();
      return `<ul class="d-msgs">${all.map((a) => msgRow(a, true)).join('')}</ul><p class="d-source">All ${all.length} in the replay span. <span class="d-link" data-span="day">Show this day only</span></p>`;
    }
    const today = G.D.t[G.state.i].slice(0, 10);
    const sameDay = list.filter((a) => a.t.slice(0, 10) === today).reverse();
    if (!sameDay.length) return `<p class="d-source">${esc(empty)}${list.length ? ` <span class="d-link" data-span="all">Show all ${list.length} in the replay span</span>` : ''}</p>`;
    return '<ul class="d-msgs">' + sameDay.map((a) => msgRow(a, false)).join('') + '</ul>' +
      (list.length > sameDay.length ? `<p class="d-source"><span class="d-link" data-span="all">Show all ${list.length} in the replay span</span></p>` : '');
  }
  function sparkline(values, cls, now, fmtv) {
    const W = 300, H = 40, n = values.length;
    const known = values.filter((v) => v != null);
    const max = known.length ? Math.max(...known) : 1, min = known.length ? Math.min(0, ...known) : 0;
    const x = (i) => (i / Math.max(1, n - 1)) * W, y = (v) => 2 + (1 - (v - min) / Math.max(1e-9, max - min)) * (H - 4);
    let d = '';
    values.forEach((v, i) => { if (v == null) { d += ' '; return; } d += (d.endsWith(' ') || !d ? 'M' : 'L') + x(i).toFixed(1) + ',' + y(v).toFixed(1); });
    const vnow = values[now];
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><line class="sp-axis" x1="0" x2="${W}" y1="${H - 2}" y2="${H - 2}"/><path class="${cls}" d="${d.trim()}"/><line class="sp-now" x1="${x(now).toFixed(1)}" x2="${x(now).toFixed(1)}" y1="0" y2="${H}"/></svg>` +
      `<div class="sp-label"><span>00:00</span><span>${fmtv(vnow)} at ${hhmm(G.D.t[now])}</span><span>24:00</span></div>`;
  }

  function selectSite(code) {
    const site = G.D.sites.find((s) => s.s === code);
    if (!site) return;
    sel = { kind: 'site', id: code };
    const kind = site.k === 'NL' ? 'load node' : site.k === 'PS' ? 'pumped storage' : 'generator';
    const pos = site.p === 'placeholder' ? 'no position on record, so it is listed under Unplaced'
      : site.p === 'approximate' ? `approximate position, placed near other ${esc((site.approx && site.approx.prefix) || String(site.s).slice(0, 2))} sites. No surveyed location`
        : `located to the ${esc(site.p)}`;
    const j = G.D.siteIndex ? G.D.siteIndex.get(code) : null;
    let series = '';
    if (G.D.nodes && j != null) {
      const rows = G.D.t.map((t) => G.D.rowIndex.get(t));
      const lmp = rows.map((r) => (r == null ? null : G.D.nodes.lmp[r][j]));
      const mw = rows.map((r) => (r == null ? null : G.D.nodes.mw[r][j]));
      series = `<div class="sp-label"><span>price ₱/MWh</span></div>` + sparkline(lmp, 'sp-lmp', G.state.i, peso) +
        `<div class="sp-label"><span>scheduled MW</span></div>` + sparkline(mw, 'sp-mw', G.state.i, (v) => fmt(v, 1) + ' MW');
    } else {
      series = '<p class="d-source">Site prices loading…</p>';
    }
    const named = messagesNaming(site);
    const ev = G.D.events.find((e) => e.site === code);
    /* DESKFIX-1: a place of several assets draws one mark, and a click opens one card. The card
       names the others at the same position, each a button that opens its own card, so the
       reader steps through them here (open() wires every [data-site]). */
    const here = site.lon != null && site.p !== 'placeholder'
      ? G.D.sites.filter((o) => o.s !== code && o.p !== 'placeholder' && o.lon === site.lon && o.lat === site.lat) : [];
    const also = here.length
      ? `<p class="d-source d-also">Also at this place: ${here.map((o) => `<button type="button" class="d-link d-also-site" data-site="${esc(o.s)}">${esc(o.s)}${o.name && o.name !== o.s ? ' ' + esc(o.name) : ''}</button>`).join(', ')}.</p>`
      : '';
    open(site.name || code,
      `<dl class="kv"><dt>Code</dt><dd><b>${esc(code)}</b></dd><dt>Kind</dt><dd>${kind} · ${esc(G.GRIDS[site.g] || '')}</dd>` +
      (site.cap ? `<dt>Registered</dt><dd><b>${fmt(site.cap)}</b> MW</dd>` : '') +
      `<dt>Position</dt><dd>${pos}</dd></dl>` + also + series +
      `<p class="d-source">Operator messages of ${esc(G.day(G.D.t[G.state.i]))} naming ${named.tokens.map(esc).join(' or ') || 'this site'}:</p>` +
      msgList(named.list, 'None this day.') +
      (ev ? `<a class="d-go" href="/event/${esc(ev.id)}">Review impact →</a>` : '') +
      `<p class="d-source">Source: WESM five-minute node data and the site register (company copy); position from the plant crosswalk.</p>`);
    mark();
  }

  function selectLink(id) {
    const L = G.LINKS[id], link = G.D.hvdc.links[id];
    if (!L) return;
    sel = { kind: 'link', id };
    G.state.series = 'link:' + id;
    const ri = G.D.rIndex.get(G.D.t[G.state.i]);
    const f = link && ri != null ? link.flow[ri] : null, cong = link && ri != null ? link.congested[ri] : 0;
    const dir = f == null ? '—' : f === 0 ? 'no flow' : f > 0 ? `${L.from} → ${L.to}` : `${L.to} → ${L.from}`;
    /* The link's own messages: HVDC notices that name the endpoint only this link has (both links
       touch Visayas, so Visayas alone names neither). */
    const own = (L.from === 'Visayas' ? L.to : L.from).toUpperCase();
    const msgs = G.D.advisories.filter((a) => /HVDC/i.test(a.text) && a.text.toUpperCase().includes(own));
    open(L.name,
      `<div class="d-row"><span>${f == null ? '—' : fmt(Math.abs(f))}<small>MW at ${hhmm(G.D.t[G.state.i])}</small></span><span>${esc(dir)}</span>${cong ? '<span>congested</span>' : ''}</div>` +
      `<p class="d-def">Undersea direct-current link ${esc(L.from)}–${esc(L.to)}, scheduled by the market every five minutes. Chart: ${esc(L.name)} flow, MW, ${esc(G.day(G.D.t[0]))} to ${esc(G.day(G.D.t[G.D.t.length - 1]))}, WESM HVDC schedules.</p>` +
      `<p class="d-source">Operator messages about this link on ${esc(G.day(G.D.t[G.state.i]))}:</p>` + msgList(msgs, 'None this day.') +
      `<p class="d-source">Source: WESM HVDC schedules (company copy); converter positions approximate to the town.</p>`);
    mark();
    G.renderChart();
  }

  function selectMessage(id) {
    const a = G.D.advisories.find((x) => x.id === id);
    if (!a) return;
    sel = { kind: 'message', id };
    if (a.grid && a.grid !== G.state.grid) G.setGrid(a.grid);
    G.setTime(G.indexAt(a.t));
    const named = sitesNamedBy(a);
    const site = named.site;
    const ev = G.D.events.find((e) => e.advisory === a.id);
    const others = site ? messagesNaming(site).list.filter((x) => x.id !== a.id) : [];
    const candidates = named.candidates.map((c) => `<span class="d-link" data-site="${esc(c.s)}">${esc(c.name || c.s)}</span>`).join(', ');
    open(`${KIND[a.kind] || a.kind} · ${a.id}`,
      `<p class="d-quote">${opText(a.text)}</p>` +
      `<dl class="kv"><dt>Posted</dt><dd><b>${hhmm(a.t)}</b> Manila, ${esc(G.day(a.t))}</dd><dt>Grid</dt><dd>${esc(G.GRIDS[a.grid] || 'System')}</dd>` +
      (site ? `<dt>Names</dt><dd><span class="d-link" data-site="${esc(site.s)}">${esc(site.name || site.s)}</span>${site.cap ? ` · ${fmt(site.cap)} MW registered` : ''} <small>(${esc(named.how)})</small></dd>` :
        named.candidates.length ? `<dt>May name</dt><dd>${candidates} <small>(${named.candidates.length} sites share the words; none is selected)</small></dd>` : '') +
      `</dl>` +
      (site ? `<p class="d-source">Other messages naming it on ${esc(G.day(a.t))}:</p>${msgList(others, 'None this day.')}` :
        named.candidates.length ? '<p class="d-source">The text does not establish which site; pick one above to open it.</p>' : '<p class="d-source">The message names no plant site in the register.</p>') +
      (ev ? `<a class="d-go" href="/event/${esc(ev.id)}">Review impact →</a>` : '') +
      `<p class="d-source">Source: NGCP system-operator message ${esc(a.id)}, as received.</p>`);
    if (site) { sel = { kind: 'message', id, site: site.s }; }
    mark();
    const node = document.getElementById('adv-' + id);
    if (node) node.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function selectFigure(grid, series) {
    sel = { kind: 'figure', id: series };
    if (grid !== G.state.grid) G.setGrid(grid);
    G.state.series = series;
    const t = G.D.t[G.state.i], r = G.regionAt(grid, t);
    const S = SERIES[series];
    let now = '—';
    if (r) {
      if (series === 'demand') now = `${fmt(r.demand_mw)} MW`;
      else if (series === 'price') now = `${peso(r.lmp_median)}/MWh`;
      else if (series === 'flow') now = r.import_mw == null || r.export_mw == null ? '—' : `${fmt(r.import_mw - r.export_mw)} MW net`;
      else if (series === 'reserve') now = r.dr_short_mw == null ? '—' : r.dr_short_mw > 0 ? `${fmt(r.dr_short_mw)} MW short of ${fmt(r.dr_req_mw)} MW` : `requirement of ${fmt(r.dr_req_mw)} MW met`;
    }
    open(`${G.GRIDS[grid]} ${S.label}`,
      `<div class="d-row"><span>${esc(now)}<small>at ${hhmm(t)}</small></span></div>` +
      `<p class="d-def">${esc(S.def)}</p>` +
      `<p class="d-source">The chart shows this series for ${esc(G.GRIDS[grid])} over the replay day. Source: WESM five-minute market data (company copy), replay of ${esc(G.day(t))}.</p>`);
    mark();
    G.renderChart();
  }

  /* ---------- the chart's hover and click, drawn over grid.js's chart ---------- */
  function wireChart() {
    const svg = $('chart');
    let cursor = null;
    const indexFor = (e) => {
      const box = svg.getBoundingClientRect();
      const W = Math.max(300, box.width), L = 44, R = 52;
      const frac = (e.clientX - box.left - L) / (W - L - R);
      return Math.max(0, Math.min(G.D.t.length - 1, Math.round(frac * (G.D.t.length - 1))));
    };
    svg.addEventListener('mousemove', (e) => {
      const i = indexFor(e);
      const box = svg.getBoundingClientRect();
      const W = Math.max(300, box.width), H = Math.max(140, box.height), L = 44, R = 52, T = 14, B = 20;
      const x = L + (i / (G.D.t.length - 1)) * (W - L - R);
      if (cursor) cursor.remove();
      cursor = el('g', { class: 'cursor-g' }, svg);
      el('line', { x1: x, x2: x, y1: T - 4, y2: H - B, class: 'cursor' }, cursor);
      const v = G.seriesValueAt(i);
      const label = el('text', { x: x + 6, y: T + 10, class: 'cursor-label' }, cursor);
      label.textContent = `${v == null ? '—' : v} at ${hhmm(G.D.t[i])}`;
    });
    svg.addEventListener('mouseleave', () => { if (cursor) { cursor.remove(); cursor = null; } });
    svg.addEventListener('click', (e) => { G.play(false); G.setTime(indexFor(e)); });
  }

  /* ---------- wiring ---------- */
  function wire() {
    $('d-close').addEventListener('click', close);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('detail').hidden) close(); });
    $('figures').addEventListener('click', (e) => {
      const td = e.target.closest('td');
      if (!td || !td.dataset.series) return;
      e.stopPropagation();
      selectFigure(td.parentElement.dataset.grid, td.dataset.series);
    });
    $('feed').addEventListener('click', (e) => {
      if (e.target.closest('a')) return;
      const row = e.target.closest('tr');
      if (row && row.id.startsWith('adv-')) selectMessage(row.id.slice(4));
    });
    /* a row is focusable: Enter opens it on the map, as a click does */
    $('feed').addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || e.target.closest('a')) return;
      const row = e.target.closest('tr');
      if (row && row.id.startsWith('adv-')) { e.preventDefault(); selectMessage(row.id.slice(4)); }
    });
    $('path').addEventListener('click', (e) => {
      const adv = e.target && e.target.getAttribute && e.target.getAttribute('data-adv');
      if (adv) selectMessage(adv);
    });
    /* The map's own clicks are resolved by the canvas module, which calls the two openers it was
       mounted with (grid.js's `mountMap`): a site or a link under the pointer opens exactly what
       the same element opens anywhere else on the page. */
    wireChart();
    const bindNarrative = () => {
      for (const n of $('brief-text').querySelectorAll('.ent[data-adv]')) n.addEventListener('click', () => selectMessage(n.dataset.adv));
      for (const n of $('brief-text').querySelectorAll('.ent[data-link]')) n.addEventListener('click', () => selectLink(n.dataset.link));
      for (const n of $('brief-text').querySelectorAll('.ent[data-figure]')) n.addEventListener('click', () => { const [g, k] = n.dataset.figure.split(':'); selectFigure(g, k); });
    };
    bindNarrative();
    G.onRender(() => { bindNarrative(); mark(); if (sel && sel.kind === 'site') selectSite(sel.id); else if (sel && sel.kind === 'link') selectLink(sel.id); });
  }

  /* The wiring runs inside a guard: the DOM shims other suites run this file under lack parts
     of the DOM the clicks need; the real browser run in tests/test_grid_page.py reads every
     interaction, so a defect there fails that run and is never hidden here. */
  const start = () => {
    G = window.GridDesk;
    /* ATG-8: the same openers the page's own clicks use, so the briefing and findings panel
       (mounted by the first module) passes them as its callbacks and a reference inside the
       panel opens what the same reference opens anywhere else on the page. */
    window.GridExplore = { figure: selectFigure, link: selectLink, message: selectMessage, site: selectSite,
      refresh: () => mark() };
    try { wire(); } catch (err) { if (typeof console !== 'undefined' && console.debug) console.debug('explorable wiring skipped: ' + err); }
    /* A notice named in the hash (`#adv=<id>`, the notices page's "Open on the desk") opens on
       the desk as a click on its feed row would: the grid, the clock and the detail panel. */
    try {
      const adv = new URLSearchParams(location.hash.slice(1)).get('adv');
      if (adv) selectMessage(adv);
    } catch (err) { /* no hash, or a DOM shim without location */ }
  };
  if (typeof window.addEventListener === 'function') window.addEventListener('grid-desk-ready', start);
  if (window.GridDesk) start();
})();
