/* InGRID dashboard overview (ericka-desk slice 3: E3, E4, E5, E6, E11, E12, E13).

   Runs after grid.js on the dashboard and reads only what the page already loaded, through
   `window.GridDesk`. It fetches nothing and draws (UX-3: as the "Grid now" card on the map):
     - one row per grid: status, price with its dot in the map's price colour, the day's price
       line up to the clock against the usual, the change against the usual, demand, reserve,
       imports and exports, and a pricing-rules flag (E3, E4, E13); a row scopes the map;
     - the two HVDC links and their congestion (E11, E12);
     - the notices in force by severity, as the map counts them;
     - the trip list (E5, folded: the map draws each notice by severity) and a summary of the
       scope the map shows (E6).
   It also keeps the page's replay clock and the shell's shared "as of" time in step.

   Rules: every figure is at or before the clock. "Usual" uses earlier replay days only, never
   later ones. A plant is ringed only when exactly one site matches the notice; any other notice
   is listed as "Unclear", is not linked and is not counted. Technology and fuel are never shown,
   and a site name that reveals them is replaced by its code. */
(function () {
  'use strict';

  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const CAP = 32000;
  const WINDOW_MIN = 240;
  const FUEL = /\b(solar|wind|hydro|hepp?|geo(thermal)?|coal|diesel|bunker|oil|gas|lng|biomass|bio|nuclear|thermal|thermo|therma|battery|bess|dpp|cfpp|ccgt|gtpp|pv)\b/i;
  const LINE = /\b(\d+\s*kV|line|lines|svc|substation|ss|bus|transformer|capacitor|reactor|feeder)\b/i;

  // ---------- pure helpers (exposed for the tests) ----------
  const median = (xs) => {
    const v = xs.filter((x) => x != null && Number.isFinite(Number(x))).map(Number).sort((a, b) => a - b);
    if (!v.length) return null;
    const m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  };
  const minutes = (t) => Date.parse(String(t).slice(0, 16) + ':00Z') / 60000;

  /* E4: the usual price at clock index `i`: the median of the same clock hour on every replay
     day before the clock's own day. Nothing from the clock's day or a later day is used. */
  function usualAt(times, series, i) {
    const t = times[i];
    if (!t) return { value: null, days: 0 };
    const date = t.slice(0, 10), hour = t.slice(11, 13);
    const vals = [], days = new Set();
    for (let k = 0; k < times.length; k += 1) {
      const u = times[k];
      if (u.slice(0, 10) >= date) continue;
      if (u.slice(11, 13) !== hour) continue;
      if (series[k] == null) continue;
      vals.push(series[k]);
      days.add(u.slice(0, 10));
    }
    return { value: median(vals), days: days.size };
  }
  /* replay-year: a year bake carries the same rule precomputed per day (`days/<day>.json`'s
     `usual`: per grid and clock hour, [median, days] of the earlier days; build_data.usual_by_day),
     so the page holding one day reads it instead of scanning a year it does not hold. */
  function usualFrom(table, t) {
    const row = table && t ? table[t.slice(11, 13)] : null;
    return row ? { value: row[0], days: row[1] } : { value: null, days: 0 };
  }

  /* E13: what the baked figures say about pricing rules at this interval. The bake carries the
     median and the highest node price only, so "capped" is the one rule it can show. Administered
     and mitigated prices are not in this bake and are said to be unknown, never assumed absent. */
  function rulesFlag(r) {
    if (!r || r.lmp_median == null) return { level: 'none', text: 'No price data' };
    if (r.lmp_median >= CAP) return { level: 'bad', text: 'Median at the ₱32,000 offer cap' };
    if (r.lmp_max != null && r.lmp_max >= CAP) return { level: 'warn', text: 'A node at the ₱32,000 offer cap' };
    if (r.lmp_median >= CAP * 0.97) return { level: 'warn', text: 'Median within 3% of the offer cap' };
    return { level: 'ok', text: 'Below the offer cap' };
  }

  const siteTokens = (code) => (String(code).match(/[A-Za-z]{3,}/g) || []).map((x) => x.toUpperCase());
  const mentions = (text, tokens) => {
    const up = String(text).toUpperCase();
    return tokens.some((tok) => new RegExp('(^|[^A-Z])' + tok + '($|[^A-Z])').test(up));
  };
  /* The one site a notice names: the event record first, then the site code in the text. Two or
     more matches, or none, resolve to no site (the uncertain-match rule). */
  function siteOf(note, sites, events) {
    const ev = (events || []).find((e) => e.advisory === note.id);
    if (ev) {
      const site = sites.find((s) => s.s === ev.site);
      if (site) return { site, candidates: [site] };
    }
    const hits = sites.filter((s) => s.k === 'G' && (note.grid == null || s.g === note.grid) && mentions(note.text, siteTokens(s.s)));
    return { site: hits.length === 1 ? hits[0] : null, candidates: hits };
  }
  const isDerate = (n) => /derat/i.test(n.text);
  const isPlantNotice = (n) => (n.kind === 'trip' || isDerate(n)) && !LINE.test(n.text);

  /* E5: plant trip and derate notices in force at the clock: issued at or before it, within the
     last WINDOW_MIN minutes, and not followed by an "online" notice for the same site. */
  function tripsAt(clock, advisories, sites, events) {
    const now = minutes(clock);
    const known = advisories.filter((a) => a.t.slice(0, 16) <= clock.slice(0, 16));
    const online = known.filter((a) => a.kind === 'online');
    const out = { matched: [], unclear: [] };
    for (const n of known) {
      if (!isPlantNotice(n) || now - minutes(n.t) > WINDOW_MIN) continue;
      const m = siteOf(n, sites, events);
      const kind = isDerate(n) ? 'derate' : 'trip';
      if (!m.site) { out.unclear.push({ id: n.id, t: n.t, grid: n.grid, kind, candidates: m.candidates.length }); continue; }
      const back = online.some((o) => o.t > n.t && siteOf(o, sites, events).site === m.site);
      if (!back) out.matched.push({ id: n.id, t: n.t, grid: n.grid, kind, code: m.site.s, name: m.site.name });
    }
    return out;
  }
  const safeName = (code, name) => (!name || FUEL.test(name) ? code : name);

  /* E11: a link's direction in words from the flow sign (positive = first grid to second). */
  const LINKS = {
    VISLUZ1: { name: 'Leyte–Luzon', from: 'Visayas', to: 'Luzon' },
    MINVIS1: { name: 'Mindanao–Visayas', from: 'Mindanao', to: 'Visayas' },
  };
  function linkAt(id, link, ri) {
    const def = LINKS[id] || { name: id, from: '?', to: '?' };
    const flow = link && link.flow ? link.flow[ri] : null;
    const cong = link && link.congested ? link.congested[ri] : null;
    let direction = 'No data';
    if (flow != null) direction = flow > 0 ? `${def.from} → ${def.to}` : flow < 0 ? `${def.to} → ${def.from}` : 'No flow';
    return {
      id, name: def.name, flow: flow == null ? null : Math.abs(flow), direction,
      congested: cong == null ? null : !!cong, limit: null,
    };
  }

  /* The latest operator Yellow, Red or load-dropping (MLD) notice for a grid in the last
     WINDOW_MIN minutes up to the clock, or null. Only the notice's own kind is read; nothing is
     inferred from prices. */
  function gridAlertAt(clock, advisories, grid) {
    const now = minutes(clock);
    let last = null;
    for (const a of advisories || []) {
      if (a.grid !== grid || !['yellow', 'red', 'mld'].includes(a.kind)) continue;
      if (a.t.slice(0, 16) > clock.slice(0, 16) || now - minutes(a.t) > WINDOW_MIN) continue;
      if (!last || a.t > last.t) last = a;
    }
    return last ? { id: last.id, t: last.t, kind: last.kind } : null;
  }

  /* A grid card's status pill, from the reserve and the operator's own alert at the clock. */
  function statusOf(r, alert) {
    if (alert && alert.kind === 'red') return { level: 'bad', text: 'Red alert' };
    if (alert && alert.kind === 'mld') return { level: 'bad', text: 'Load dropping' };
    if (r && r.dr_short_mw > 0) return { level: 'bad', text: 'Reserves short' };
    if (alert && alert.kind === 'yellow') return { level: 'warn', text: 'Yellow alert' };
    if (!r || r.dr_short_mw == null) return { level: 'none', text: 'No data' };
    return { level: 'ok', text: 'Normal' };
  }

  const api = { usualAt, usualFrom, rulesFlag, tripsAt, siteOf, linkAt, safeName, median, gridAlertAt, statusOf, FUEL };
  if (typeof globalThis !== 'undefined') globalThis.GridOverview = api;
  if (typeof document === 'undefined' || typeof window === 'undefined') return;
  window.GridOverview = api;

  // ---------- drawing ----------
  const $ = (id) => document.getElementById(id);
  const SVGNS = 'http://www.w3.org/2000/svg';
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const make = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const svg = (tag, attrs, parent) => {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const hhmm = (t) => String(t).slice(11, 16);
  const SHORT = { CLUZ: 'LUZ', CVIS: 'VIS', CMIN: 'MIN' };
  /* A status level to the shared badge's tone (design system: muted background, strong text). */
  const BADGE = { ok: 'ok', warn: 'warning', bad: 'alert' };
  /* The price colour of the map's own function at this draw, on its scale of every located price
     whatever the map's scope (so the three grids compare on one scale); the theme's unknown colour
     when the map has no price. */
  const priceColour = (G, v) => {
    const m = G.mapPanel;
    if (v != null && m && typeof m.gridColor === 'function') return m.gridColor(v);
    return getComputedStyle(document.documentElement).getPropertyValue('--rule-strong').trim() || '#3a4552';
  };
  /* Severity glyphs, 12px line drawings in currentColor (design brief: triangle, diamond, "i"). */
  function sevGlyph(kind) {
    const s = svg('svg', { viewBox: '0 0 12 12', class: 'ov-sev-g ' + kind, 'aria-hidden': 'true' });
    if (kind === 'alert') svg('path', { d: 'M6 1.5 11 10.5H1z', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linejoin': 'round' }, s);
    else if (kind === 'warning') svg('path', { d: 'M6 1 11 6 6 11 1 6z', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linejoin': 'round' }, s);
    else {
      svg('circle', { cx: '6', cy: '6', r: '4.6', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, s);
      svg('path', { d: 'M6 5.4v3.2M6 3.4v.1', stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linecap': 'round' }, s);
    }
    return s;
  }

  /* The usual price for each clock hour of the clock's day (earlier days only), or null. */
  function usualByHour(D, g, i) {
    const out = [];
    const t = D.t[i];
    for (let h = 0; h < 24; h += 1) {
      const hh = String(h).padStart(2, '0');
      if (D.usual) { const u = usualFrom(D.usual[g], t.slice(0, 11) + hh + ':00'); out.push(u.value); continue; }
      const k = D.t.findIndex((x) => x.slice(0, 10) === t.slice(0, 10) && x.slice(11, 13) === hh);
      out.push(k < 0 ? null : usualAt(D.t, D.regions.grids[g].lmp_median, k).value);
    }
    return out;
  }
  /* The day's price up to the clock as a line over the whole day (nothing after the clock is
     drawn), the usual price per hour as a faint step, and the clock's price as the end dot in the
     map's price colour. Inline SVG, no axes. */
  function sparkline(G, g, i) {
    const D = G.D, W = 112, H = 26, PADY = 3;
    const t = D.t[i], today = t.slice(0, 10);
    const series = D.regions.grids[g] ? D.regions.grids[g].lmp_median : [];
    const pts = [];
    for (let k = 0; k <= i; k += 1) {
      if (D.t[k].slice(0, 10) !== today) continue;
      const m = Number(D.t[k].slice(11, 13)) * 60 + Number(D.t[k].slice(14, 16));
      pts.push([m, series[k]]);
    }
    const usual = usualByHour(D, g, i);
    const known = pts.map((p) => p[1]).filter((v) => v != null).concat(usual.filter((v) => v != null));
    const s = svg('svg', { class: 'ov-spark', viewBox: `0 0 ${W} ${H}`, width: String(W), height: String(H), 'aria-hidden': 'true' });
    if (!known.length) { svg('line', { x1: 0, x2: W, y1: H - PADY, y2: H - PADY, class: 'ov-sp-none' }, s); return s; }
    let lo = Math.min(...known), hi = Math.max(...known);
    if (hi - lo < 1) { lo -= 1; hi += 1; }
    const x = (m) => (m / 1435) * (W - 3) + 1;
    const y = (v) => PADY + (1 - (v - lo) / (hi - lo)) * (H - 2 * PADY);
    let ud = '';
    usual.forEach((v, h) => {
      if (v == null) return;
      ud += `M${x(h * 60).toFixed(1)},${y(v).toFixed(1)}H${x(h * 60 + 59).toFixed(1)}`;
    });
    if (ud) svg('path', { d: ud, class: 'ov-sp-usual' }, s);
    let d = '', pen = false;
    for (const [m, v] of pts) {
      if (v == null) { pen = false; continue; }
      d += (pen ? 'L' : 'M') + x(m).toFixed(1) + ',' + y(v).toFixed(1);
      pen = true;
    }
    if (d) svg('path', { d, class: 'ov-sp-line' }, s);
    const last = pts.length ? pts[pts.length - 1] : null;
    if (last && last[1] != null) {
      svg('circle', { cx: x(last[0]).toFixed(1), cy: y(last[1]).toFixed(1), r: '3', class: 'ov-sp-halo' }, s);
      svg('circle', { cx: x(last[0]).toFixed(1), cy: y(last[1]).toFixed(1), r: '2.2', fill: priceColour(G, last[1]), class: 'ov-sp-end' }, s);
    }
    return s;
  }

  function mapScope(G) {
    const snap = G.mapPanel && G.mapPanel.snapshot ? G.mapPanel.snapshot() : null;
    return snap ? snap.scope || null : null;
  }

  function renderCards(G) {
    const host = $('ov-cards');
    if (!host) return;
    const D = G.D, i = G.state.i, t = D.t[i];
    const scope = mapScope(G);
    host.textContent = '';
    const mini = $('ov-mini');
    if (mini) mini.textContent = '';
    const noUsual = [];
    for (const g of ['CLUZ', 'CVIS', 'CMIN']) {
      const r = G.regionAt(g, t);
      const row = make('button', 'ov-row');
      row.type = 'button';
      row.dataset.grid = g;
      row.setAttribute('aria-pressed', String(scope === g));
      row.title = scope === g ? `Show every grid on the map` : `Zoom the map to ${GRIDS[g]}`;
      const st = statusOf(r, gridAlertAt(t, D.advisories, g));
      const price = r ? r.lmp_median : null;
      // name, status
      const name = make('span', 'ov-r-name');
      const dot = make('span', 'ov-dot');
      dot.style.background = priceColour(G, price);
      name.appendChild(dot);
      name.appendChild(make('strong', null, GRIDS[g]));
      row.appendChild(name);
      row.appendChild(make('span', 'gn-badge ov-flag ov-r-status ' + st.level + (BADGE[st.level] ? ' gn-badge--' + BADGE[st.level] : ''), st.text));
      // the day's line
      const spark = make('span', 'ov-r-spark');
      spark.appendChild(sparkline(G, g, i));
      row.appendChild(spark);
      // price and its change against the usual
      const fig = make('span', 'ov-r-price');
      fig.appendChild(make('span', 'num big', price == null ? 'No data' : '₱' + fmt(price)));
      row.appendChild(fig);
      const usual = D.usual ? usualFrom(D.usual[g], t) : usualAt(D.t, D.regions.grids[g] ? D.regions.grids[g].lmp_median : [], i);
      /* An unknown usual gets no cell of its own: the card says it once, under the rows. */
      let vs = '', vsCls = 'none';
      let vsTitle = 'Usual = median of the same hour on earlier replay days. None before this day priced this hour.';
      if (usual.value == null || !usual.value) noUsual.push(GRIDS[g]);
      if (usual.value != null && price != null && usual.value) {
        const pct = Math.round(((price - usual.value) / usual.value) * 100);
        vs = `${pct >= 0 ? '+' : '−'}${Math.abs(pct)}% vs usual`;
        vsCls = pct >= 50 ? 'bad' : pct >= 15 ? 'warn' : pct <= -15 ? 'cool' : 'ok';
        vsTitle = `Usual ₱${fmt(usual.value)}: median of the ${hhmm(t).slice(0, 2)}:00 hour on ${usual.days} earlier replay day${usual.days === 1 ? '' : 's'}.`;
      }
      const delta = make('span', 'ov-r-delta mono ' + vsCls, vs);
      delta.title = vsTitle;
      row.appendChild(delta);
      // demand, reserves, imports, and the one pricing rule the bake can show
      const meta = make('span', 'ov-r-meta');
      /* meta tier: a muted word, its figure in mono */
      const fact = (label, value, unit, cls) => {
        const f = make('span', 'ov-fact' + (cls ? ' ' + cls : ''));
        if (label) f.appendChild(make('span', 'ov-fact-l', label));
        f.appendChild(make('span', 'num', value));
        if (unit) f.appendChild(make('span', 'ov-fact-u', unit));
        return f;
      };
      if (!r) meta.appendChild(make('span', null, 'No data'));
      else {
        meta.appendChild(r.demand_mw == null ? fact('Demand', 'No data') : fact('Demand', fmt(r.demand_mw), 'MW'));
        if (r.dr_short_mw == null) meta.appendChild(fact('Reserves', 'No data'));
        else if (r.dr_short_mw > 0) meta.appendChild(fact('Reserves', fmt(r.dr_short_mw), 'MW short', 'bad'));
        else meta.appendChild(make('span', 'ov-fact ok', 'Reserves met'));
        const net = r.import_mw == null && r.export_mw == null ? null : (r.import_mw || 0) - (r.export_mw || 0);
        if (net != null) meta.appendChild(fact('', fmt(Math.abs(net)), net >= 0 ? 'MW in' : 'MW out'));
        const flag = rulesFlag(r);
        if (flag.level === 'bad' || flag.level === 'warn') {
          const chip = make('span', 'ov-rules ' + flag.level, flag.text);
          chip.title = 'Pricing rules at ' + hhmm(t) + '. Administered and mitigated prices are not in this bake: No data.';
          meta.appendChild(chip);
        }
      }
      row.appendChild(meta);
      row.setAttribute('aria-label', `${GRIDS[g]}: ${st.text}, ${price == null ? 'price No data' : '₱' + fmt(price) + ' per MWh'}${vs ? ', ' + vs : ''}. ${row.title}.`);
      row.addEventListener('click', () => {
        const m = G.mapPanel;
        if (m && m.setScope) m.setScope(mapScope(G) === g ? null : g);
        G.setGrid(g);
      });
      const hl = (on) => { const m = G.mapPanel; if (m && m.setHighlight) m.setHighlight(on ? g : null); };
      row.addEventListener('mouseenter', () => hl(true));
      row.addEventListener('mouseleave', () => hl(false));
      row.addEventListener('focus', () => hl(true));
      row.addEventListener('blur', () => hl(false));
      host.appendChild(row);
      if (mini) {
        const chip = make('span', 'ov-mini-g ' + st.level);
        const d2 = make('span', 'ov-dot');
        d2.style.background = priceColour(G, price);
        chip.appendChild(d2);
        chip.appendChild(make('span', 'ov-mini-name', SHORT[g]));
        chip.appendChild(make('span', 'num', price == null ? '—' : '₱' + fmt(price)));
        mini.appendChild(chip);
      }
    }
    const asof = $('ov-asof');
    if (asof) asof.textContent = `${hhmm(t)} PHT · ${G.day(t)}`;
    const unknown = $('ov-unknowns');
    if (unknown) {
      const parts = [];
      if (noUsual.length) parts.push(`usual price for ${hhmm(t).slice(0, 2)}:00${noUsual.length < 3 ? ' in ' + noUsual.join(' and ') : ''}`);
      parts.push('line-level congestion');
      unknown.textContent = 'Not on record: ' + parts.join(', ') + '.';
      unknown.title = noUsual.length ? 'Usual = median of the same hour on earlier replay days. No earlier day priced this hour.' : '';
    }
  }

  function renderLinks(G) {
    const host = $('ov-links');
    if (!host) return;
    const D = G.D, t = D.t[G.state.i];
    const ri = D.hvdc.t ? D.hvdc.t.indexOf(t) : D.rIndex.get(t);
    host.textContent = '';
    const rows = Object.keys(LINKS).map((id) => linkAt(id, D.hvdc.links[id], ri));
    for (const l of rows) {
      /* DESKFIX-1: each row is the link's entity link (design-system.md "Entity links and
         previews": `/?link=<id>`, `data-entity="link:<id>"`, so ui.js previews it on hover and
         focus). Its click scopes the map to the link the way a grid row scopes it to a grid:
         the map zooms to the link and pins its popover, and the address gains `?link=`. With no
         map panel the address itself opens the link on load (dash-map.js deepLink). */
      const row = make('a', 'ov-link' + (l.congested ? ' hot' : ''));
      row.dataset.link = l.id;
      row.href = '/?link=' + encodeURIComponent(l.id);
      row.setAttribute('data-entity', 'link:' + l.id);
      row.title = `Show the ${l.name} HVDC link on the map`;
      const glyph = svg('svg', { viewBox: '0 0 16 16', class: 'ov-link-g', 'aria-hidden': 'true' }, row);
      svg('path', { d: 'M2 11c3-6 9-6 12 0', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', 'stroke-linecap': 'round' }, glyph);
      row.appendChild(make('span', 'ov-link-name', l.name));
      row.addEventListener('click', (e) => {
        const m = G.mapPanel;
        if (!m || !m.focusLink || e.defaultPrevented) return;
        e.preventDefault();
        m.focusLink(l.id);
        linkToUrl(l.id);
      });
      const flow = make('span', 'num ov-link-mw', l.flow == null ? 'No data' : fmt(l.flow) + ' MW');
      flow.title = 'No limit on record';
      row.appendChild(flow);
      row.appendChild(make('span', 'ov-dir', l.direction === 'No data' || l.direction === 'No flow' ? l.direction : '→ ' + l.direction.split(' → ')[1]));
      const tone = l.congested == null ? 'none' : l.congested ? 'bad' : 'ok';
      row.appendChild(make('span', 'gn-badge ov-flag ' + tone + (BADGE[tone] ? ' gn-badge--' + BADGE[tone] : ''),
        l.congested == null ? 'No data' : l.congested ? 'Congested' : 'Clear'));
      host.appendChild(row);
    }
    const cong = $('ov-congestion');
    if (cong) {
      const hot = rows.filter((l) => l.congested);
      cong.textContent = '';
      /* The badges say each link's state; the card's unknowns line says line-level congestion is
         not on record. Only a link the record is silent on gets a sentence here. */
      if (rows.some((l) => l.congested == null)) cong.appendChild(make('p', 'ov-muted', `Congestion at ${hhmm(t)}: No data for some links.`));
      cong.title = `${hot.length} of ${rows.length} links congested at ${hhmm(t)}`;
    }
  }

  /* DESKFIX-1: the address names the link the map is scoped to (`?link=VISLUZ1`), as dash-map.js
     writes `?grid=` for a grid scope. The other parameters and the hash are kept. */
  function linkToUrl(id) {
    try {
      const u = new URL(location.href);
      if (u.searchParams.get('link') === id) return;
      u.searchParams.set('link', id);
      history.replaceState(history.state, '', u.pathname + u.search.replace(/%3A/gi, ':') + u.hash);
    } catch (e) { /* an address that cannot be rewritten keeps the scope on the map only */ }
  }

  /* The notices in force at the clock by severity, as the map counts them (one count for the map
     and the card). DESKFIX-1: each count is a link to the notices page at the clock. The counts
     are notice severities (map.js severityOf: red and trip are alerts, yellow, load dropping and
     derate are warnings, the rest information), which no filter of /notices or /alerts names
     one to one, so the page opens unfiltered rather than under a filter that shows another count. */
  function renderSeverity(G) {
    const host = $('ov-sev');
    if (!host) return;
    const snap = G.mapPanel && G.mapPanel.snapshot ? G.mapPanel.snapshot() : null;
    const c = snap && snap.severity ? snap.severity : null;
    const t = G.D.t[G.state.i];
    host.textContent = '';
    host.appendChild(make('span', 'ov-sev-label', `In force at ${hhmm(t)}`));
    if (!c) { host.appendChild(make('span', 'ov-muted', 'No data')); return; }
    const words = { alert: ['alert', 'alerts'], warning: ['warning', 'warnings'], info: ['information notice', 'information notices'] };
    for (const k of ['alert', 'warning', 'info']) {
      const n = c[k] || 0;
      const chip = make('a', 'ov-sev-c ' + k + (n ? '' : ' zero'));
      /* the shell's own clock form (`2026-09-21T13:40`), whatever axis the replay carries */
      chip.href = '/notices?at=' + String(t || '').replace(' ', 'T').slice(0, 16);
      chip.dataset.severity = k;
      chip.appendChild(sevGlyph(k));
      chip.appendChild(make('span', 'num', String(n)));
      chip.title = `${n} ${words[k][n === 1 ? 0 : 1]} in force. Open the notices at ${hhmm(t)}.`;
      chip.setAttribute('aria-label', chip.title);
      host.appendChild(chip);
    }
  }

  function renderTrips(G) {
    const D = G.D, t = D.t[G.state.i];
    const res = tripsAt(t, D.advisories, D.sites, D.events);
    const host = $('ov-trips');
    if (host) {
      host.textContent = '';
      if (!res.matched.length && !res.unclear.length) host.appendChild(make('li', 'ov-muted', `No plant trip or derate notice in the 4 hours to ${hhmm(t)}.`));
      for (const m of res.matched) {
        const li = make('li', 'ov-trip ' + m.kind);
        const a = make('a', null, safeName(m.code, m.name));
        a.href = '/plant/' + encodeURIComponent(m.code);
        li.appendChild(make('span', 'ov-flag ' + (m.kind === 'trip' ? 'bad' : 'warn'), m.kind === 'trip' ? 'Trip' : 'Derate'));
        li.appendChild(a);
        li.appendChild(make('span', 'num ov-muted', GRIDS[m.grid] + ' · ' + hhmm(m.t)));
        host.appendChild(li);
      }
      for (const u of res.unclear) {
        const li = make('li', 'ov-trip unclear');
        li.appendChild(make('span', 'ov-flag none', 'Unclear'));
        li.appendChild(make('span', null, `${u.kind === 'trip' ? 'Trip' : 'Derate'} notice ${u.id}: ` +
          (u.candidates ? `${u.candidates} possible plants, none picked` : 'no plant matched')));
        li.appendChild(make('span', 'num ov-muted', GRIDS[u.grid] + ' · ' + hhmm(u.t)));
        li.title = 'Less than 50% sure which plant this is, so it is not linked or counted.';
        host.appendChild(li);
      }
    }
    return res;
  }

  function renderScope(G, trips) {
    const host = $('ov-scope');
    if (!host) return;
    const D = G.D, t = D.t[G.state.i];
    const scope = mapScope(G);
    const grids = scope ? [scope] : ['CLUZ', 'CVIS', 'CMIN'];
    const sites = D.sites.filter((s) => grids.includes(s.g));
    const gens = sites.filter((s) => s.k === 'G').length;
    let demand = 0, gen = 0, any = false;
    for (const g of grids) {
      const r = G.regionAt(g, t);
      if (r && r.demand_mw != null) { demand += r.demand_mw; any = true; }
      if (r && r.gen_mw != null) gen += r.gen_mw;
    }
    const prices = grids.map((g) => { const r = G.regionAt(g, t); return r ? r.lmp_median : null; }).filter((v) => v != null);
    const notes = D.advisories.filter((a) => grids.includes(a.grid) && a.t.slice(0, 16) <= t && minutes(t) - minutes(a.t) <= WINDOW_MIN);
    host.textContent = '';
    /* PP-B5: the design system's section and stats: a label, the figure in mono with its unit,
       and a faint meta line. */
    const head = make('header', 'gn-section-head');
    const h = make('h2', null, (scope ? GRIDS[scope] : 'All grids') + ' on the map');
    h.id = 'ov-scope-h';
    head.appendChild(h);
    head.appendChild(make('span', 'gn-section-meta mono', hhmm(t)));
    host.setAttribute('aria-labelledby', 'ov-scope-h');
    host.appendChild(head);
    const card = make('div', 'gn-card');
    const stats = make('div', 'gn-stats ov-stats');
    const stat = (label, value, unit, meta) => {
      const box = make('div', 'gn-stat');
      box.appendChild(make('span', 'gn-label', label));
      const v = make('span', 'gn-value', value);
      if (unit) v.appendChild(make('span', 'gn-unit', unit));
      box.appendChild(v);
      if (meta) box.appendChild(make('span', 'gn-meta', meta));
      stats.appendChild(box);
    };
    stat('Sites', fmt(sites.length), null, `${fmt(gens)} gen · ${fmt(sites.length - gens)} load`);
    stat('Demand', any ? fmt(demand) : 'No data', any ? 'MW' : null);
    stat('Generation', any ? fmt(gen) : 'No data', any ? 'MW' : null);
    if (scope) stat('Median price', prices.length ? '₱' + fmt(prices[0]) : 'No data', prices.length ? '/MWh' : null);
    else {
      const top = grids.map((g) => { const r = G.regionAt(g, t); return { g, v: r ? r.lmp_median : null }; })
        .filter((x) => x.v != null).sort((a, b) => b.v - a.v)[0];
      stat('Highest median', top ? '₱' + fmt(top.v) : 'No data', top ? '/MWh' : null, top ? GRIDS[top.g] : null);
    }
    stat('Notices, last 4 h', fmt(notes.length));
    const inScope = trips.matched.filter((m) => grids.includes(m.grid)).length;
    const unclear = trips.unclear.filter((m) => grids.includes(m.grid)).length;
    stat('Trips and derates', fmt(inScope), null, unclear ? `${unclear} unclear, not counted` : null);
    card.appendChild(stats);
    host.appendChild(card);
  }

  function renderAll(G) {
    try { renderCards(G); } catch (e) { const h = $('ov-cards'); if (h) h.textContent = 'No data'; }
    try { renderLinks(G); } catch (e) { const h = $('ov-links'); if (h) h.textContent = 'No data'; }
    try { renderSeverity(G); } catch (e) { const h = $('ov-sev'); if (h) h.textContent = 'No data'; }
    let trips = { matched: [], unclear: [] };
    try { trips = renderTrips(G); } catch (e) { const h = $('ov-trips'); if (h) h.textContent = 'No data'; }
    try { renderScope(G, trips); } catch (e) { const h = $('ov-scope'); if (h) h.textContent = 'No data'; }
  }

  /* The card folds to its title and a one-line strip of the three prices; on a phone it opens
     folded, so the map keeps the screen. */
  function wireFold() {
    const card = $('overview'), btn = $('ov-fold'), body = $('ov-body');
    if (!card || !btn || !body) return;
    const set = (open) => {
      btn.setAttribute('aria-expanded', String(open));
      btn.setAttribute('aria-label', open ? 'Fold the card' : 'Open the card');
      btn.title = btn.getAttribute('aria-label');
      card.classList.toggle('folded', !open);
      body.hidden = !open;
      window.dispatchEvent(new Event('grid-overlay-change'));
    };
    const phone = window.matchMedia && window.matchMedia('(max-width: 760px)').matches;
    set(!phone);
    btn.addEventListener('click', () => set(btn.getAttribute('aria-expanded') !== 'true'));
    const mini = $('ov-mini');
    if (mini) mini.addEventListener('click', () => set(true));
  }

  function start() {
    const G = window.GridDesk;
    if (!G || !G.D || start.done) return;
    start.done = true;
    const shell = window.GNShell;
    // The shared "as of" time: a link with ?at= or a time set on another page opens the
    // dashboard at that time, unless the page's own address names a time.
    const hash = new URLSearchParams(location.hash.slice(1));
    let at = null;
    try { at = new URLSearchParams(location.search).get('at'); } catch (e) { at = null; }
    if (!at && !hash.get('t') && shell && shell.asOf) at = shell.asOf();
    if (at && G.goto && G.replay && String(at).slice(0, 10) !== G.D.t[0].slice(0, 10)) G.goto(at);
    else if (at) {
      const i = G.indexAt(at);
      if (G.D.t[i] && G.D.t[i].slice(0, 16) === String(at).slice(0, 16)) G.setTime(i);
    }
    G.onRender(() => {
      renderAll(G);
      if (shell && shell.setAsOf) shell.setAsOf(G.D.t[G.state.i]);
    });
    if (shell && shell.onAsOf) shell.onAsOf((t) => {
      if (G.goto) { G.goto(t); return; }  // replay-year: another day is read first
      const i = G.indexAt(t);
      if (i !== G.state.i) G.setTime(i);
    });
    // The theme changes the price colours: the card's dots follow the map's redraw.
    if (shell && shell.onTheme) shell.onTheme(() => setTimeout(() => renderAll(G), 0));
    wireFold();
    renderAll(G);
    if (shell && shell.setAsOf) shell.setAsOf(G.D.t[G.state.i]);
  }
  window.addEventListener('grid-desk-ready', start);
  if (window.GridDesk) start();
})();
