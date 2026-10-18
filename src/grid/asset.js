/* Asset collection and profile pages (`/plants`, `/plant/<code>`). Design file: written by the
   orchestrator's lane (ATG-7); it follows the event page's construction — the source carries
   `__NOWCAST_STAMP__`, the script reads the meta the server writes in and fetches its payload
   from the same build — and draws everything with SVG; no library, no network beyond same
   origin, no model call.

   Two payloads, one per page, both built by `scripts/grid/build_assets.py`:
     index.json            the collection: every site's code, name, grid, kind, registered
                           resources, capacity with its record, and located or placeholder
     assets/<code>.json    one site's profile: figures with the time each one holds at (the
                           stamp it was read at, or the replay window for a window count; a
                           figure whose record states no date says so), the register rows, the
                           location block, the price and schedule series of the baked day, the
                           messages naming it, its events and what is not known
   The collection also reads the clock's day of site series (`nodes-<day>.json`, the desk map's
   own file) after its table is drawn, for the price and schedule at the clock.

   Every figure the page prints carries the record it was read from (`rec.id` or `rec.file`);
   a cell a record does not state is drawn as unknown, never as a number. */
(() => {
  'use strict';
  /* The build stamp the page was served under (grid.js's own reading): a page served without
     one reads the unversioned names, which the server never caches. */
  const STAMP = (() => {
    const meta = typeof document !== 'undefined' && document.getElementById
      ? document.getElementById('nowcast-build') : null;
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP;
  const KINDS = { G: 'generator', NL: 'load node', PS: 'pumped storage' };
  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const MESSAGE_KINDS = { trip: 'Trip', mld: 'Load dropping', yellow: 'Yellow alert', red: 'Red alert',
                          online: 'Back online', notice: 'Notice', market: 'Market' };

  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => { const n = document.createElementNS(svgNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const peso = (v) => (v == null ? '—' : '₱' + fmt(v));
  const hhmm = (t) => String(t || '').slice(11, 16);
  /* A record date as "21 Sep 2026", read from the text (the same month words as `when`). */
  const day = (t) => `${Number(String(t).slice(8, 10))} ${MONTHS[Number(String(t).slice(5, 7)) - 1] || ''} ${String(t).slice(0, 4)}`;
  const opText = (s) => esc(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');
  const recName = (rec) => (rec && (rec.id || rec.file)) || '—';
  const srcLine = (rec, extra) => `Source: ${esc(recName(rec))}${rec && rec.file && rec.id ? ', ' + esc(rec.file) : ''}${extra ? ' · ' + esc(extra) : ''}`;
  /* When a figure holds. A figure read from the day's series carries the stamp it was read at;
     a count taken over the replay window carries that window; a figure whose record states no
     date at all (the register aggregation) says exactly that — no time is ever named that the
     records do not state. */
  const asOf = (f) => f.span
    ? (f.span.first.slice(0, 10) === f.span.last.slice(0, 10)
        ? `over the replay window ${day(f.span.first)}`
        : `over the replay window ${day(f.span.first)} to ${day(f.span.last)}`)
    : f.at ? `as of ${hhmm(f.at)}, ${day(f.at)}` : 'the record states no time';

  function fail(where, message) {
    const box = $(where);
    if (box) box.innerHTML = `<p class="gn-error">This page could not read ${esc(message)}. <a href="/plants">All plants</a></p>`;
  }
  /* ------------------------------------------- plants: matching, status and redaction (slice 6)

     ericka-desk slice 6 (E8, E18, E29; docs/work/ericka-desk-2026-10-18/intent.md). Three
     rules, the same on both pages:

     Naming. The grid page's own rule (`grid.js`, siteTokens / mentions / sitesNamedBy), not a
     looser one: a notice names a plant when the event record maps it to that plant, or when
     one of the plant code's letter groups (three letters or more) appears in its text as a whole
     word and no other plant of the notice's grid shares one. A notice whose words fit two or
     more plants is Unclear for each of them: listed, never linked to a plant, never counted, and
     the page never picks one of the candidates. A message the profile's bake lists by its code's
     letters that this rule does not give to the plant (another grid's message, or a site list
     that could not be read) is Unclear too.

     Time. Everything is filtered to the shared "as of" clock (`GNShell.asOf()`, Manila,
     `YYYY-MM-DDTHH:MM`): a record counts when its time is at or before that minute.

     No technology or fuel. A name or a notice text can name a unit's technology or fuel; the
     words are withheld from what is rendered, and a plant name that carries one is left out
     (the code stands in for it). The kind (`k`: generator, load node) is not a technology. */
  const SHELL = typeof window !== 'undefined' && window.GNShell ? window.GNShell : null;
  const SPAN_LAST = '2026-09-29T23:55';  // only when the shell is absent; the shell carries the bake's span
  const clockAt = () => (SHELL && typeof SHELL.asOf === 'function' && SHELL.asOf()) || (SHELL && SHELL.span && SHELL.span.last) || SPAN_LAST;
  const upTo = (t, at) => !!t && String(t).slice(0, 19) <= at + ':59';
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const when = (t) => (t ? `${Number(String(t).slice(8, 10))} ${MONTHS[Number(String(t).slice(5, 7)) - 1] || ''} ${hhmm(t)}` : '—');
  const TECH_WORDS = '\\b(?:geo-?thermal\\w*|thermal|solar|photo-?voltaic|pv|hydro\\w*|hepp?|coal(?:-fired)?|diesel|bunker|fuel|oil|gas|lng|ccgt|combined[- ]cycle|wind|biomass|bio\\w*|battery|bess|nuclear|pumped[- ]storage|steam|hfo|cfpp|[dgsw]ppi?)\\b';
  const TECH_ANY = new RegExp(TECH_WORDS, 'i');
  const withheld = (s) => String(s == null ? '' : s).replace(new RegExp(TECH_WORDS, 'gi'), '[…]').replace(/\[…\](?:[\s-]*\[…\])+/g, '[…]');
  const nameOf = (s) => (s && s.name && !TECH_ANY.test(s.name) ? s.name : null);
  const NOTICE = { trip: { label: 'Tripped', tone: 'alert' }, derate: { label: 'Derated', tone: 'warning' }, online: { label: 'Back online', tone: 'info' } };
  /* The notice kinds the plant status reads: the advisory's own trip and back-online kinds, and
     a derating, which the bake files as a notice whose text says so (`derat`, the advisory
     adapter's own token, src/adapters/wesm/advisories.py). A notice about grid equipment — a
     line, a transformer, a substation's equipment, the HVDC link — names the stations at its
     ends, not a unit: it never sets a plant's status (it still appears among the messages). */
  const EQUIPMENT = /\b(?:line|l\d|tr\d*|transformer|substation|ss|svc|hvdc|capacitor|reactor|bus|breaker)\b/i;
  const noticeKind = (a) => (EQUIPMENT.test(String(a.text)) ? null
    : a.kind === 'trip' ? 'trip' : a.kind === 'online' ? 'online' : /derat/i.test(String(a.text)) ? 'derate' : null);
  const journalHref = (code) => `/journal?plant=${encodeURIComponent(code)}`;
  const MATCH_RULE = 'A notice names a plant when the event record maps it, or when its code\'s letters appear in the text and no other plant of that grid shares them. A notice that fits two or more plants is Unclear: listed, not linked, not counted.';

  function siteTokens(code) {
    return (String(code).match(/[A-Za-z]{3,}/g) || []).map((t) => t.toUpperCase());
  }
  const tokenTests = (code) => siteTokens(code).map((t) => new RegExp('(^|[^A-Z])' + t + '($|[^A-Z])'));

  const getJSON = (name) => fetch(DATA + name).then((r) => (r && r.ok ? r.json() : null), () => null).catch(() => null);

  /* The shared records both pages read beside their own payload; a file that cannot be read is
     null, and its card says "No data" rather than breaking the page. */
  /* replay-year: a year bake keeps its notices by month (`GNShell.notices`); a plant's activity
     reads every month of the span (the record runs to the clock, wherever it is moved). A bake
     without month files reads advisories.json. */
  const allNotices = () => (SHELL && SHELL.notices && SHELL.ready
    ? SHELL.ready.then(() => SHELL.notices(SHELL.monthOf(SHELL.span.first), SHELL.monthOf(SHELL.span.last)))
    : getJSON('advisories.json'));
  function loadPlantRecords() {
    return Promise.all([allNotices(), ...['sites.json', 'events.json', 'outages.json'].map(getJSON)])
      .then(([advisories, sites, events, outages]) => plantIndex({ advisories, sites, events, outages }));
  }

  /* Which plants each notice names (grid.js's sitesNamedBy over every notice at once), and each
     plant's notices in time order. */
  function plantIndex(R) {
    const advisories = Array.isArray(R.advisories) ? R.advisories.slice().sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : a.id < b.id ? -1 : 1)) : null;
    const sites = Array.isArray(R.sites) ? R.sites : null;
    const events = Array.isArray(R.events) ? R.events : [];
    const outages = Array.isArray(R.outages) ? R.outages : (R.outages && Array.isArray(R.outages.records) ? R.outages.records : null);
    const known = new Map((sites || []).map((s) => [s.s, s]));
    const tests = (sites || []).map((s) => ({ s, re: tokenTests(s.s) }));
    const hitsFor = (text, grid) => {
      const up = String(text).toUpperCase();
      return tests.filter((x) => (grid == null || x.s.g === grid) && x.re.some((re) => re.test(up))).map((x) => x.s.s);
    };
    const named = new Map();
    const bySite = new Map();
    const unclear = [];
    /* Indexed once: a year of notices and outages read against every plant per lookup froze
       the page for minutes. */
    const eventOf = new Map();
    for (const e of events) if (e.advisory != null && !eventOf.has(e.advisory)) eventOf.set(e.advisory, e);
    const eventsBySite = new Map();
    for (const e of events) {
      if (!eventsBySite.has(e.site)) eventsBySite.set(e.site, []);
      eventsBySite.get(e.site).push(e);
    }
    for (const a of advisories || []) {
      const ev = eventOf.get(a.id);
      let n;
      if (ev && known.has(ev.site)) n = { how: 'the event record', candidates: [ev.site], event: ev };
      else {
        const hits = hitsFor(a.text, a.grid);
        n = { how: hits.length === 1 ? 'its code in the text' : hits.length ? 'unclear' : 'none', candidates: hits };
      }
      named.set(a.id, n);
      if (n.how === 'unclear') unclear.push({ a, n });
      for (const code of n.candidates) {
        if (!bySite.has(code)) bySite.set(code, []);
        bySite.get(code).push({ a, n });
      }
    }
    /* Each outage record matched once (the rule in outageFacts), kept per plant code. */
    const outagesBySite = new Map();
    for (const r of outages || []) {
      const hits = hitsFor(r.unit || '', r.grid == null ? null : r.grid);
      const conf = typeof r.match_confidence === 'number' ? r.match_confidence : null;
      const codes = new Set(hits);
      if (r.site != null) codes.add(r.site);
      if (r.unit != null) codes.add(r.unit);
      for (const code of codes) {
        const exact = r.site === code || r.unit === code;
        if (!exact && !hits.includes(code)) continue;
        const confident = exact ? (conf == null || conf >= 0.5) : (hits.length === 1 && conf != null && conf >= 0.5);
        if (!outagesBySite.has(code)) outagesBySite.set(code, []);
        outagesBySite.get(code).push({ r, confident });
      }
    }
    return { advisories, sites, events, outages, known, named, bySite, unclear, hitsFor, eventsBySite, outagesBySite, factsAt: null };
  }

  /* Every plant's facts at one clock time, worked out once and reused by the status table, the
     lists and the search until the clock moves. */
  function allFacts(P, X, at) {
    if (!X.factsAt || X.factsAt.at !== at) {
      X.factsAt = { at, map: new Map(P.sites.map((s) => [s.s, X.advisories ? plantFacts(X, s.s, at) : null])) };
    }
    return X.factsAt.map;
  }

  /* One plant's facts at the clock: the notices that name only it (counted), the ones that fit
     it and another plant (Unclear, not counted), its latest trip, derating or return, its events
     and its outage records. Only records at or before `at` are read. */
  function plantFacts(X, code, at) {
    const mine = (X.bySite.get(code) || []).filter((x) => upTo(x.a.t, at));
    const sure = mine.filter((x) => x.n.how !== 'unclear');
    /* The Unclear notices that would have moved the status: the trips, deratings and returns
       that fit this plant and another one. */
    const unclear = mine.filter((x) => x.n.how === 'unclear' && noticeKind(x.a));
    const status = sure.filter((x) => noticeKind(x.a));
    const count = (k) => status.filter((x) => noticeKind(x.a) === k).length;
    const latest = status.length ? status[status.length - 1] : null;
    const events = (X.eventsBySite.get(code) || []).filter((e) => upTo(e.t, at));
    return { at, sure, unclear, latest, kind: latest ? noticeKind(latest.a) : null,
             trips: count('trip'), derates: count('derate'), returns: count('online'), events,
             outages: outageFacts(X, code, at) };
  }

  /* The outage bake's records for one plant (`outages.json`, `{unit, grid, kind, start,
     first_seen, source, lag_min, match_confidence}`), by the same rule: a record names the
     plant by its code, or by the code's letters in the unit name with no other plant of the grid
     sharing them, and only with a stated match confidence of at least 50%. Anything else that
     fits the plant is Unclear. No file is "No data", never zero. */
  function outageFacts(X, code, at) {
    if (!X.outages) return null;
    const sure = [], unclear = [];
    for (const { r, confident } of X.outagesBySite.get(code) || []) {
      if (!upTo(r.first_seen || r.start, at)) continue;
      (confident ? sure : unclear).push(r);
    }
    sure.sort((a, b) => (String(a.first_seen || a.start) < String(b.first_seen || b.start) ? -1 : 1));
    const lagged = sure.filter((r) => typeof r.lag_min === 'number');
    return { sure, unclear, lag: lagged.length ? lagged[lagged.length - 1] : null };
  }

  /* ------------------------------------------------------------ shared pieces (platform polish)

     The markup follows the design system contract (docs/work/platform-polish-2026-10-18/
     design-system.md): `gn-badge` for a status, `gn-table` with `data-sortable` and row links,
     `gn-filters` reflected in the address, `data-entity` on every plant and event reference.
     ui.js (window.GNUI) sorts, opens menus and previews; this script only renders. */
  const GNUI = () => (typeof window !== 'undefined' && window.GNUI ? window.GNUI : null);
  const resort = (table) => { const ui = GNUI(); if (table && ui && typeof ui.resort === 'function') ui.resort(table); };
  /* Runs `fn(GNUI)` once ui.js is in (shell.js defines `GNUI.ready` before it arrives); never in
     a page stand-in without it (the node harness), where the page keeps its own plain wiring. */
  const withUI = (fn) => { const ui = GNUI(); if (ui && ui.ready && typeof ui.ready.then === 'function') ui.ready.then(() => { const G = GNUI(); if (G && G.filters) fn(G); }); return !!(ui && ui.ready); };
  const DASH = '<span class="gn-meta">–</span>';
  const KIND_WORDS = { G: 'Generator', NL: 'Load node', PS: 'Pumped storage' };
  const STATUS_RANK = { trip: 3, derate: 2, online: 1 };
  /* A plant status in the shared kind style (GNUI.badgeHtml's classes), in its state words. */
  const badge = (kind) => (kind ? `<span class="gn-badge gn-badge--${NOTICE[kind].tone} gn-sev">${NOTICE[kind].label}</span>` : '');
  const unclearMark = (n, title) => (n ? `<span class="gn-unclear" title="${esc(title)}">Unclear${n > 1 ? ' ×' + n : ''}</span>` : '');
  const plantLink = (code) => `<a class="mono" href="/plant/${encodeURIComponent(code)}" data-entity="plant:${esc(code)}">${esc(code)}</a>`;
  const eventLink = (e, label) => `<a href="/event/${encodeURIComponent(e.id)}" data-entity="event:${esc(e.id)}">${label}</a>`;
  const lagWords = (r) => (r.lag_min > 0 ? `${fmt(r.lag_min)} min before the schedule showed it`
    : r.lag_min < 0 ? `${fmt(-r.lag_min)} min after the schedule showed it` : 'at the same time as the schedule');
  /* Message kinds in the shared kind words, as badges: alert for a trip or a red alert, warning
     for a yellow alert or load dropping, ok for a return; a plain notice stays neutral. */
  const MESSAGE_TONE = { trip: 'alert', red: 'alert', yellow: 'warning', mld: 'warning', online: 'info', notice: 'info' };
  const messageBadge = (kind) => `<span class="gn-badge${MESSAGE_TONE[kind] ? ' gn-badge--' + MESSAGE_TONE[kind] + ' gn-sev' : ''}">${esc(MESSAGE_KINDS[kind] || kind)}</span>`;
  const GLYPH_MORE = '<span class="gn-dots" aria-hidden="true"></span>';

  /* "What to watch" and "Next steps": rule-based sentences from the facts above only. No
     forecast, no peso figure, nothing the records do not state. */
  function watchAndNext(code, F) {
    const watch = [], next = [];
    const L = F.latest;
    if (L && F.kind === 'trip') watch.push(`Tripped by the notice of ${when(L.a.t)}. No back-online notice names it after that, up to ${when(F.at)}.`);
    if (L && F.kind === 'derate') watch.push(`Derated by the notice of ${when(L.a.t)}. No later trip or return notice names it, up to ${when(F.at)}.`);
    if (L && F.kind === 'online') watch.push(`Back online by the notice of ${when(L.a.t)}${F.trips ? `, after ${fmt(F.trips)} trip${F.trips === 1 ? '' : 's'} earlier in the replay` : ''}.`);
    if (F.trips >= 2) watch.push(`${fmt(F.trips)} trips up to ${when(F.at)}: a repeated trip.`);
    if (F.unclear.length) watch.push(`${fmt(F.unclear.length)} notice${F.unclear.length === 1 ? ' fits' : 's fit'} this plant and another one. The page does not count ${F.unclear.length === 1 ? 'it' : 'them'} here.`);
    if (F.outages && F.outages.lag) watch.push(`The latest outage record for it came ${lagWords(F.outages.lag)}.`);
    if (!L && !F.unclear.length) watch.push(`No trip, derating or back-online notice names it up to ${when(F.at)}.`);
    F.events.forEach((e) => next.push(eventLink(e, `Open the event review: ${esc(withheld(e.title))}`)));
    if (F.kind === 'trip' || F.kind === 'derate') next.push('Look for its back-online notice as the clock moves on.');
    if (F.unclear.length) next.push('Read the Unclear notices yourself. The page picks no plant for them.');
    next.push(`<a href="${journalHref(code)}">Journal entries on this plant</a>`);
    return { watch, next };
  }

  /* The filter state in the address, so a filtered view can be shared and comes back on load.
     Only values that differ from the default are written. */
  function readQuery(defaults) {
    const out = Object.assign({}, defaults);
    let params = null;
    try { params = new URLSearchParams(typeof location !== 'undefined' ? location.search || '' : ''); } catch (e) { params = null; }
    if (params) for (const key of Object.keys(defaults)) if (params.has(key)) out[key] = params.get(key) || '';
    return out;
  }
  function writeQuery(state, defaults) {
    if (typeof history === 'undefined' || typeof location === 'undefined' || !history.replaceState) return;
    let params;
    try { params = new URLSearchParams(location.search || ''); } catch (e) { return; }
    for (const key of Object.keys(defaults)) {
      if (state[key] && state[key] !== defaults[key]) params.set(key, state[key]); else params.delete(key);
    }
    const query = params.toString();
    history.replaceState(history.state, '', location.pathname + (query ? '?' + query : '') + (location.hash || ''));
  }
  /* Every element under `node` (static markup only), depth first. */
  function walk(node, fn) {
    for (const child of Array.from((node && node.children) || [])) { fn(child); walk(child, fn); }
  }
  const closestWith = (node, attr, stop) => {
    for (let n = node; n && n !== stop; n = n.parentNode) if (n.getAttribute && n.getAttribute(attr) != null) return n;
    return null;
  };

  /* --------------------------------------------------------------- the collection page */

  function renderIndex() {
    const index = fetch(DATA + 'assets/index.json').then((r) => (r.ok ? r.json() : Promise.reject(new Error('assets/index.json'))));
    const records = loadPlantRecords();
    index.then((P) => records.then((X) => drawIndex(P, X)), (err) => fail('lists', err.message));
  }

  /* Price and schedule at the clock, from the day's site series (`nodes-<day>.json`, the file the
     desk map reads, so it is usually cached already). Read after the table is drawn, and only
     for a day the bake states a series for. A site the file does not list stays unknown. */
  const nodeDays = new Map();
  function nodesAt(at) {
    if (!SHELL || !SHELL.ready || typeof SHELL.ready.then !== 'function') return Promise.resolve(null);
    const d = String(at).slice(0, 10);
    return SHELL.ready.then(() => {
      const days = SHELL.span && SHELL.span.nodeDays;
      if (!Array.isArray(days) || !days.includes(d)) return null;
      if (!nodeDays.has(d)) nodeDays.set(d, getJSON(`nodes-${d}.json`));
      return nodeDays.get(d);
    }).then((file) => {
      if (!file || !Array.isArray(file.t) || !Array.isArray(file.sites)) return null;
      let i = -1;
      for (let k = 0; k < file.t.length; k += 1) if (String(file.t[k]).slice(0, 16) <= at) i = k;
      if (i < 0) return null;
      const col = new Map(file.sites.map((s, c) => [s, c]));
      return { t: file.t[i], price: (code) => (col.has(code) && file.lmp[i] ? file.lmp[i][col.get(code)] : null),
               mw: (code) => (col.has(code) && file.mw[i] ? file.mw[i][col.get(code)] : null) };
    }, () => null);
  }

  const FILTERS = { grid: 'all', kind: 'all', status: 'all', notice: '', pos: 'all', q: '' };
  /* The position filter: a surveyed location, an approximate display placement, or none. */
  const POS_OF = (s) => (s.p === 'plant' || s.p === 'municipality' ? 'located' : s.p === 'approximate' ? 'approximate' : 'none');
  const on = (v) => v && v !== 'all';

  function drawIndex(P, X) {
    const counts = P.counts;
    document.title = 'Plants · InGRID';
    const approxNote = counts.approximate ? ` · ${fmt(counts.approximate)} at approximate positions` : '';
    $('count').textContent = `${fmt(counts.total)} sites · ${fmt(counts.located)} located${approxNote}. Replay window ${day(P.window.first)} to ${day(P.window.last)} from ${recName(P.window.rec)}, ${P.window.rec.file}. Sites and counts from ${recName(P.records.sites)}, ${P.records.sites.file}.`;
    $('cap-src').textContent = `Registered MW: ${recName(P.records.cap)} (${P.records.cap.file}), the registered maximum summed over each site's own unit rows · position: ${recName(P.records.loc)} (${P.records.loc.file}) · price and schedule at the clock: ${recName(P.records.series || { id: 'bake-nodes' })}, the day's five-minute site series.`;
    $('match-rule').textContent = MATCH_RULE;
    const stat = (label, value, meta) => `<div class="gn-stat"><span class="gn-label">${esc(label)}</span><span class="gn-value">${fmt(value)}</span>${meta ? `<span class="gn-meta">${esc(meta)}</span>` : ''}</div>`;
    $('tiles').innerHTML = stat('Sites', counts.total, `${fmt(counts.located)} located${counts.approximate ? ` · ${fmt(counts.approximate)} approximate` : ''}`)
      + Object.keys(KINDS).map((k) => stat(KIND_WORDS[k], (counts.kinds[k] || { total: 0 }).total, `${fmt((counts.kinds[k] || { located: 0 }).located)} located`)).join('')
      + Object.keys(GRIDS).map((g) => stat(GRIDS[g], (counts.grids[g] || { total: 0 }).total, `${fmt((counts.grids[g] || { located: 0 }).located)} located`)).join('');

    let at = clockAt();
    let prices = null;
    /* The filter state. In the browser, ui.js's filter controller owns the bar and the address
       (`GNUI.filters`); without it (the node harness) the page reads the address once and keeps
       the controls itself. */
    let state = readQuery(FILTERS);
    let ctl = null;
    const search = $('search');
    if (search) search.value = state.q;

    const syncControls = () => {
      if (!ctl) {
        walk($('filters'), (n) => {
          const group = n.getAttribute && n.getAttribute('data-filter');
          if (group && group !== 'q') for (const b of Array.from(n.children || [])) b.setAttribute('aria-pressed', String((b.getAttribute('data-value') || '') === (state[group] || '')));
        });
        const busy = Object.keys(FILTERS).some((k) => (state[k] || '') !== FILTERS[k]);
        if ($('clear')) $('clear').hidden = !busy;
      }
      walk($('status-sum'), (n) => { const k = n.getAttribute && n.getAttribute('data-status'); if (k != null) n.setAttribute('aria-pressed', String(state.status === k)); });
    };

    const list = () => {
      const q = (state.q || '').trim().toUpperCase();
      const facts = allFacts(P, X, at);
      /* The search reads the name as shown: a withheld name is not searchable either. */
      const hit = (s) => !q || `${s.s} ${nameOf(s) || ''} ${GRIDS[s.g] || ''} ${KINDS[s.k] || ''}`.toUpperCase().includes(q);
      const F = (s) => facts.get(s.s);
      const shown = P.sites.filter((s) => hit(s)
        && (!on(state.grid) || s.g === state.grid)
        && (!on(state.kind) || s.k === state.kind)
        && (!on(state.pos) || POS_OF(s) === state.pos)
        && (!on(state.status) || (F(s) && F(s).kind === state.status))
        && (state.notice !== '1' || !!(F(s) && F(s).sure.length)));
      /* The default order puts the status in force first: tripped, derated, back online, each
         newest notice first, then the rest by code. A header sorts it another way (ui.js). */
      const rank = (s) => (F(s) && F(s).kind ? STATUS_RANK[F(s).kind] : 0);
      const latestT = (s) => (F(s) && F(s).latest ? F(s).latest.a.t : '');
      shown.sort((a, b) => rank(b) - rank(a) || (latestT(a) < latestT(b) ? 1 : latestT(a) > latestT(b) ? -1 : 0) || (a.s < b.s ? -1 : 1));
      if (ctl) ctl.count(shown.length, P.sites.length);
      else $('found').textContent = shown.length === P.sites.length ? `${fmt(shown.length)} sites` : `${fmt(shown.length)} of ${fmt(P.sites.length)} sites`;
      if (!shown.length) {
        $('lists').innerHTML = `<div class="gn-empty" role="status"><p class="gn-empty-title">No site matches these filters</p>`
          + `<p class="gn-empty-body">${q ? `No site code or name holds “${esc(state.q.trim())}” with the other filters on.` : 'Every filter is on its default except the ones you set.'}</p>`
          + `<div class="gn-empty-actions"><button type="button" class="gn-btn" data-clear>Clear filters</button></div></div>`;
        return;
      }
      const priced = prices ? ` Price and schedule from the interval at ${hhmm(prices.t)}.` : '';
      $('lists').innerHTML = `<p class="gn-meta pl-caption">Status, notices, price and schedule up to ${esc(when(at))}.${esc(priced)} Registered MW from the register.</p>`
        + `<div class="gn-table-wrap"><table class="gn-table gn-table--compact pl-table" data-sortable id="sites-table">`
        + '<colgroup><col class="w-code"><col class="pl-c-name"><col class="pl-c-kind"><col class="w-sm"><col class="w-sm"><col class="w-num"><col class="pl-c-sched"><col class="w-badge"><col class="w-num"><col class="w-xs"><col class="w-act"></colgroup>'
        + '<thead><tr><th scope="col" data-sort="text">Plant</th><th scope="col" data-sort="text">Name</th><th scope="col" data-sort="text">Kind</th>'
        + '<th scope="col" data-sort="text">Grid</th><th scope="col" class="num" data-sort="num">MW</th>'
        + `<th scope="col" class="num" data-sort="num" title="Price at the replay clock, ₱/MWh">₱/MWh</th>`
        + '<th scope="col" class="num" data-sort="num" title="Scheduled output at the replay clock, MW">Sched MW</th>'
        + '<th scope="col" data-sort="num">Status</th><th scope="col" class="num" data-sort="num" title="Notices that name only this plant, up to the clock">Notices</th>'
        + '<th scope="col" class="pl-pos-h" title="Position on record">Pos</th>'
        + '<th scope="col"><span class="sr-only">Actions</span></th></tr></thead>'
        + `<tbody>${shown.map((s) => siteRow(s, F(s), prices)).join('')}</tbody></table></div>`;
      resort($('sites-table'));
    };

    const redraw = () => { drawStatus(P, X, at); syncControls(); list(); };
    redraw();
    const priceAt = (t) => nodesAt(t).then((found) => { if (t === at) { prices = found; if (found) list(); } });
    priceAt(at);

    /* A change from the anchor's counts or an empty state's "Clear filters" goes through the
       controller when there is one, so the bar and the address follow. */
    const setState = (partial) => {
      if (ctl) { ctl.set(partial); return; }
      Object.assign(state, partial);
      if (search && 'q' in partial) search.value = state.q;
      writeQuery(state, FILTERS); syncControls(); list();
    };
    const clearAll = () => (ctl ? ctl.clear() : setState(Object.assign({}, FILTERS)));
    const wired = withUI((G) => {
      ctl = G.filters($('filters'), { defaults: FILTERS, noun: 'sites', onChange: (next) => { state = next; syncControls(); list(); } });
      state = ctl.get();
      syncControls();
      list();
    });
    if (!wired) {
      if ($('filters')) $('filters').addEventListener('click', (e) => {
        const target = e && e.target;
        if (!target) return;
        if (target === $('clear')) { clearAll(); return; }
        const b = closestWith(target, 'data-value', $('filters'));
        const group = b && closestWith(b.parentNode, 'data-filter', $('filters'));
        if (!b || !group) return;
        const key = group.getAttribute('data-filter');
        const value = b.getAttribute('data-value') || '';
        setState({ [key]: group.getAttribute('data-multi') != null && state[key] === value ? '' : value });
      });
      if (search) search.addEventListener('input', () => setState({ q: search.value || '' }));
    }
    if ($('status-sum')) $('status-sum').addEventListener('click', (e) => {
      const b = e && e.target && closestWith(e.target, 'data-status', $('status-sum'));
      if (!b) return;
      const k = b.getAttribute('data-status');
      setState({ status: state.status === k ? 'all' : k });
    });
    if ($('lists')) $('lists').addEventListener('click', (e) => {
      if (e && e.target && closestWith(e.target, 'data-clear', $('lists'))) clearAll();
    });
    if (SHELL && typeof SHELL.onAsOf === 'function') SHELL.onAsOf((t) => { at = t || clockAt(); prices = null; redraw(); priceAt(at); });
  }

  /* E29: the status in force at the clock: each plant's latest trip, derating or back-online
     notice at or before it, counted per kind, with the newest status notices beside the counts.
     A notice that fits more than one plant is Unclear: listed under the counts, never counted. */
  function drawStatus(P, X, at) {
    $('as-of').textContent = `As of ${when(at)}`;
    if (!X.advisories) {
      $('status-sum').innerHTML = '<p class="gn-error"><span class="gn-nodata">No data</span>: the operator messages (advisories.json) could not be read.</p>';
      $('status-list').innerHTML = '';
      $('unclear-list').innerHTML = '';
      return;
    }
    const facts = allFacts(P, X, at);
    const rows = P.sites.map((s) => ({ s, F: facts.get(s.s) }));
    const noted = rows.filter((r) => r.F.latest).sort((a, b) => (a.F.latest.a.t < b.F.latest.a.t ? 1 : -1));
    const tally = (k) => noted.filter((r) => r.F.kind === k).length;
    const unclear = X.unclear.filter((x) => upTo(x.a.t, at) && noticeKind(x.a));
    $('status-sum').innerHTML = ['trip', 'derate', 'online'].map((k) => `<button type="button" class="pl-fig" data-status="${k}" aria-pressed="false" title="Show the ${esc(NOTICE[k].label.toLowerCase())} plants">`
      + `<span class="gn-value gn-value--lg">${fmt(tally(k))}</span>${badge(k)}</button>`).join('')
      + `<p class="gn-meta pl-fig-note">By each plant's latest notice up to <span id="status-at">${esc(when(at))}</span>.</p>`;
    const feed = noted.slice(0, 5);
    $('status-list').innerHTML = noted.length
      ? '<ol class="pl-feed">' + feed.map(({ s, F }) => `<li><span class="mono pl-t">${esc(when(F.latest.a.t))}</span>${badge(F.kind)}`
          + `${plantLink(s.s)}<span class="pl-x" title="${esc(opText(withheld(F.latest.a.text)))}">${opText(withheld(F.latest.a.text))}</span></li>`).join('') + '</ol>'
        + (noted.length > feed.length ? `<p class="gn-meta">${fmt(noted.length - feed.length)} more in the table below.</p>` : '')
      : `<p class="gn-meta">No trip, derating or back-online notice names a plant up to ${esc(when(at))}.</p>`;
    $('unclear-list').innerHTML = unclear.length
      ? `<details class="gn-disclosure pl-unclear-box"><summary>${unclearMark(unclear.length, 'notices that fit more than one plant')} ${fmt(unclear.length)} status notice${unclear.length === 1 ? ' fits' : 's fit'} more than one plant</summary><ul class="pl-unclear">`
        + unclear.slice().reverse().map(({ a, n }) => `<li><span class="mono pl-t">${esc(when(a.t))}</span>`
          + `<span class="pl-x">${opText(withheld(a.text))}</span><span class="pl-why">Fits ${fmt(n.candidates.length)} plants (${n.candidates.map(esc).join(', ')}). None is picked, linked or counted.</span></li>`).join('') + '</ul></details>'
      : '';
  }

  /* One row of the sites table. The code is a real link (keyboard, middle click) and the row
     opens the plant page; the actions sit in one "More options" menu. */
  function siteRow(s, F, prices) {
    const name = nameOf(s);
    const nameCell = name ? `<td class="trunc" title="${esc(name)}">${esc(name)}</td>`
      : `<td class="trunc gn-meta" title="${s.name ? 'Name withheld: it names a technology or fuel' : 'The register states no name'}">${s.name ? 'not shown' : 'not stated'}</td>`;
    const cap = s.cap == null
      ? `<td class="num" data-value="-1">${s.k === 'NL' ? '<span class="gn-meta" title="A load node has no registered capacity">none</span>' : DASH}</td>`
      : `<td class="num" data-value="${esc(s.cap)}">${fmt(s.cap)}</td>`;
    const lmp = prices ? prices.price(s.s) : null;
    const mw = prices ? prices.mw(s.s) : null;
    const num = (v, d) => (v == null ? `<td class="num" data-value="">${DASH}</td>` : `<td class="num" data-value="${esc(v)}">${fmt(v, d)}</td>`);
    const statusTitle = F && F.latest ? `${NOTICE[F.kind].label} by the notice of ${when(F.latest.a.t)}` : 'No status notice up to the clock';
    const status = F
      ? `<td class="pl-status-cell" data-value="${F.kind ? STATUS_RANK[F.kind] : 0}" title="${esc(statusTitle)}">${badge(F.kind)}${unclearMark(F.unclear.length, 'notices that fit this plant and another. Not counted.')}</td>`
      : '<td data-value="0"><span class="gn-nodata">No data</span></td>';
    const notices = F ? (F.sure.length ? `<td class="num" data-value="${F.sure.length}">${fmt(F.sure.length)}</td>` : `<td class="num" data-value="0">${DASH}</td>`) : `<td class="num" data-value="">${DASH}</td>`;
    const approx = s.p === 'approximate' ? `Approximate position, near ${s.near}. No surveyed location` : '';
    const pos = s.p === 'placeholder'
      ? '<td class="pl-pos-cell"><span class="pl-pos pl-pos--none" title="Location not known"><span class="sr-only">Location not known</span></span></td>'
      : approx
        ? `<td class="pl-pos-cell"><span class="pl-pos pl-pos--approx" title="${esc(approx)}"><span class="sr-only">${esc(approx)}</span></span></td>`
        : `<td class="pl-pos-cell"><span class="pl-pos pl-pos--${s.p === 'plant' ? 'plant' : 'area'}" title="Located to the ${esc(s.p)}"><span class="sr-only">Located to the ${esc(s.p)}</span></span></td>`;
    const events = F ? F.events : [];
    const menu = `<td class="gn-row-actions"><button type="button" class="gn-icon-btn" aria-label="More options for ${esc(s.s)}" aria-haspopup="menu" aria-expanded="false" data-menu>${GLYPH_MORE}</button>`
      + '<div class="gn-menu" role="menu" hidden>'
      + `<a role="menuitem" href="/plant/${encodeURIComponent(s.s)}">Open the plant</a>`
      + events.map((e) => `<a role="menuitem" href="/event/${encodeURIComponent(e.id)}">Open the event</a>`).join('')
      + `<a role="menuitem" href="${journalHref(s.s)}">Journal entries</a></div></td>`;
    return `<tr data-href="/plant/${encodeURIComponent(s.s)}"><td>${plantLink(s.s)}</td>${nameCell}`
      + `<td>${esc(KIND_WORDS[s.k] || s.k)}</td><td>${esc(GRIDS[s.g] || s.g)}</td>${cap}${num(lmp, 0)}${num(mw, 1)}${status}${notices}${pos}${menu}</tr>`;
  }

  /* ---------------------------------------------------------------- the profile page */

  function codeFromPath() {
    const parts = location.pathname.split('/').filter(Boolean);
    return decodeURIComponent(parts[parts.length - 1] || '');
  }

  function renderProfile() {
    const code = codeFromPath();
    const profile = fetch(DATA + 'assets/' + encodeURIComponent(code) + '.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('assets/' + code + '.json'))));
    const records = loadPlantRecords();
    profile.then((P) => records.then((X) => drawProfile(P, X)), (err) => fail('activity', err.message));
  }

  /* E8: the anchor. The plant's status at the clock and the notice that set it, then the counts
     (trips, deratings, returns, the schedule lag from the outage bake or "No data"); E18's
     Unclear notices are listed under "What to watch", unlinked and uncounted. */
  function drawActivity(P, X, at) {
    $('activity-at').textContent = when(at);
    const fact = (k, v) => `<div class="pl-fact"><dt class="gn-label">${esc(k)}</dt><dd>${v}</dd></div>`;
    if (!X.advisories) {
      $('activity-status').innerHTML = '<span class="gn-nodata">No data</span>';
      $('activity-latest').innerHTML = '<p class="gn-error">The operator messages (advisories.json) could not be read.</p>';
      $('activity-facts').innerHTML = fact('Schedule lag', '<span class="gn-nodata">No data</span>');
      $('watch').innerHTML = '<li><span class="gn-nodata">No data</span></li>';
      $('next').innerHTML = `<li><a href="${journalHref(P.s)}">Journal entries on this plant</a></li>`;
      $('activity-unclear').innerHTML = '';
      $('activity-src').textContent = '';
      return;
    }
    const F = plantFacts(X, P.s, at);
    $('activity-status').innerHTML = (F.kind ? badge(F.kind) : '<span class="gn-badge">No status notice</span>')
      + unclearMark(F.unclear.length, 'notices that fit this plant and another. Not counted.');
    const L = F.latest;
    $('activity-latest').innerHTML = L
      ? `<p class="pl-latest-text">${opText(withheld(L.a.text))}</p><p class="gn-meta"><span class="mono">${esc(when(L.a.t))} · ${esc(L.a.id)}</span>`
        + (L.n.event ? ` · ${eventLink(L.n.event, 'Open the event')}` : '') + '</p>'
      : `<p class="pl-latest-text">No trip, derating or back-online notice names it.</p><p class="gn-meta">Up to ${esc(when(at))}</p>`;
    const O = F.outages;
    const lag = O && O.lag ? `<b class="mono" title="${esc(lagWords(O.lag))}">${fmt(O.lag.lag_min)} min</b>` : '<span class="gn-nodata">No data</span>';
    $('activity-facts').innerHTML = fact('Trips', `<b class="mono">${fmt(F.trips)}</b>`)
      + fact('Deratings', `<b class="mono">${fmt(F.derates)}</b>`)
      + fact('Back online', `<b class="mono">${fmt(F.returns)}</b>`)
      + fact('Schedule lag', lag);
    const W = watchAndNext(P.s, F);
    $('watch').innerHTML = W.watch.map((line) => `<li>${esc(line)}</li>`).join('');
    $('next').innerHTML = W.next.map((line) => `<li>${line}</li>`).join('');
    const outUnclear = O ? O.unclear : [];
    const nUnclear = F.unclear.length + outUnclear.length;
    $('activity-unclear').innerHTML = nUnclear
      ? `<details class="gn-disclosure"><summary>${unclearMark(nUnclear, 'records that fit this plant and another')} Unclear matches</summary><ul class="pl-unclear">`
        + F.unclear.map(({ a, n }) => `<li><span class="mono pl-t">${esc(when(a.t))}</span>`
          + `<span class="pl-x">${opText(withheld(a.text))}</span><span class="pl-why">Fits ${fmt(n.candidates.length)} plants (${n.candidates.map(esc).join(', ')}). Not linked, not counted.</span></li>`).join('')
        + outUnclear.map((r) => `<li><span class="mono pl-t">${esc(when(r.first_seen || r.start))}</span>`
          + `<span class="pl-x">outage record: ${esc(withheld(r.unit))}</span><span class="pl-why">Match confidence ${r.match_confidence == null ? 'not stated' : fmt(r.match_confidence * 100) + '%'}, or the unit name fits another plant. Not counted.</span></li>`).join('')
        + '</ul></details>'
      : '';
    $('activity-src').textContent = `Status: bake-advisories (advisories.json), the event records (events.json) and the outage bake (outages.json${O ? '' : ': not in this build'}), up to ${when(at)}. ${MATCH_RULE}`;
  }

  /* The stat row: the payload's figures in the person's words, each with the time it holds at.
     The figure's own description and record sit in its title and under Sources. */
  const FIGURE_LABELS = { 'Registered capacity': 'Capacity', 'Messages naming it': 'Notices', 'Events naming it': 'Events' };
  const figureMeta = (f) => (f.span ? 'Replay window' : f.at ? when(f.at) : 'Undated record');

  function drawProfile(P, X) {
    const name = nameOf(P);
    const codename = name || P.s;
    document.title = `${codename} · Plants · InGRID`;
    $('name').textContent = codename;
    $('crumb').textContent = P.s;
    if ($('journal')) $('journal').setAttribute('href', journalHref(P.s));
    const cap = P.figures.find((f) => f.k === 'Registered capacity');
    const pos = P.location.state === 'located' ? `located to the ${esc(P.location.p)}`
      : P.location.state === 'approximate' ? `Approximate position, near <a class="mono" href="/plant/${encodeURIComponent(P.location.near)}" data-entity="plant:${esc(P.location.near)}">${esc(P.location.near)}</a>`
        : 'position not known';
    $('meta').innerHTML = [name ? `<span class="mono">${esc(P.s)}</span>` : '', esc(KIND_WORDS[P.k] || P.kind),
      `<a href="/?grid=${esc(P.g)}" data-entity="grid:${esc(P.g)}">${esc(P.grid)} grid</a>`,
      cap && typeof cap.v === 'number' ? `<span class="mono">${fmt(cap.v)}</span> MW registered` : '', pos].filter(Boolean).join(' · ');
    /* E18: the bake's message count is by the code's letters alone. A message that fits another
       plant as well is not counted here, and the figure says how many it leaves out. */
    const unsure = P.messages.filter((m) => messageMatch(P, X, m).unclear).length;
    const figures = P.figures.map((f) => (f.k === 'Messages naming it' && unsure && typeof f.v === 'number'
      ? Object.assign({}, f, { v: f.v - unsure, d: `${f.d}. ${fmt(unsure)} Unclear (fit another plant too), not counted` }) : f));
    $('figures').innerHTML = figures.map((f) => `<div class="gn-stat${f.k === 'Peak price' ? ' gn-stat--key' : ''}" title="${esc(`${f.k}: ${f.d}, ${asOf(f)}. Record: ${recName(f.rec)}`)}">`
      + `<span class="gn-label">${esc(FIGURE_LABELS[f.k] || f.k)}</span>`
      + `<span class="gn-value gn-value--lg">${typeof f.v === 'number' ? fmt(f.v, f.unit === 'MW' && !Number.isInteger(f.v) ? 1 : 0) : esc(f.v)}${f.unit ? `<span class="gn-unit">${esc(f.unit)}</span>` : ''}</span>`
      + `<span class="gn-meta">${esc(figureMeta(f))}</span></div>`).join('');
    let at = clockAt();
    const charts = () => drawCharts(P, X, at);
    charts();
    $('chart-src').textContent = `Charts: ${recName(P.catalog.find((c) => c.key === 'series') || {})} · ${P.series.t.length ? `${fmt(P.series.t.length)} five-minute intervals, ${P.series.t[0].slice(0, 10)}` : 'no intervals in this build'}. Figures: ${figures.map((f) => `${f.k} from ${recName(f.rec)} (${f.d}, ${asOf(f)})`).join(' · ')}.`;
    renderRegister(P);
    renderLocation(P);
    renderCatalog(P);
    $('not-known').innerHTML = P.not_known.map((line) => `<li>${esc(line)}</li>`).join('');
    const timed = (t) => { at = t; drawActivity(P, X, at); renderMessages(P, X, at); renderEvents(P, at); charts(); };
    timed(clockAt());
    if (SHELL && typeof SHELL.onAsOf === 'function') SHELL.onAsOf((t) => timed(t || clockAt()));
    window.addEventListener('resize', charts);
    if ($('messages-filter')) $('messages-filter').addEventListener('click', (e) => {
      const b = e && e.target && closestWith(e.target, 'data-value', $('messages-filter'));
      if (!b) return;
      msgFilter = b.getAttribute('data-value');
      pages.messages = 1;
      renderMessages(P, X, at);
    });
  }

  /* How one of the profile's messages names this plant, by the shared rule above. */
  function messageMatch(P, X, m) {
    const n = X.named.get(m.id);
    if (!n && m.via === 'the event record') return { unclear: false, n: null };
    if (!X.advisories || !X.sites) return { unclear: true, why: 'The operator messages or the site list could not be read, so the match is not established. Not counted.' };
    if (!n) return { unclear: true, why: 'The operator messages file does not hold it, so the match is not established. Not counted.' };
    if (n.how !== 'unclear' && n.how !== 'none' && n.candidates.length === 1 && n.candidates[0] === P.s) return { unclear: false, n };
    if (n.how === 'unclear') return { unclear: true, why: `Fits ${n.candidates.length} plants (${n.candidates.join(', ')}). Not counted.` };
    if (n.how === 'the event record') return { unclear: true, why: `The event record maps it to ${n.candidates[0]}. Not counted here.` };
    return { unclear: true, why: X.sites ? 'Its code\'s letters appear, but it names no plant of the message\'s grid. Not counted.' : 'The site list (sites.json) could not be read, so the match is not established. Not counted.' };
  }

  /* The register rows as the aggregation states them: type, resources, summed capacity and the
     unit names. A fixed layout with its own column widths, so no header can overlap another. */
  function renderRegister(P) {
    const rows = P.register.rows;
    $('register').innerHTML = '<div class="gn-table-wrap"><table class="gn-table gn-table--compact a-reg">'
      + '<colgroup><col class="a-reg-type"><col class="a-reg-n"><col class="a-reg-mw"><col></colgroup>'
      + '<thead><tr><th scope="col">Type</th><th scope="col" class="num">Units</th><th scope="col" class="num">MW</th><th scope="col">Unit names</th></tr></thead><tbody>'
      + rows.map((r) => `<tr><td class="mono">${esc(r.t)}</td><td class="num">${fmt(r.n)}</td>`
        + `<td class="num">${r.cap == null ? DASH : fmt(r.cap, 1)}</td><td class="mono wrap a-reg-units">${r.units.length ? r.units.map((u) => `<span>${esc(u)}</span>`).join(' ') : '<span class="gn-meta">not stated</span>'}</td></tr>`).join('')
      + `</tbody></table></div><p class="gn-meta a-note">${srcLine(P.register.rec, 'the aggregation\'s own rows as read')}</p>`;
  }

  function renderLocation(P) {
    const L = P.location;
    /* The sources say how an approximate position was chosen, so it is never read as surveyed. */
    const how = $('position-src');
    if (how) {
      how.textContent = L.state === 'approximate'
        ? `Position: approximate, for display only. A site code's first two digits name its area. `
          + `This site has no surveyed location, so the map places it at ${L.near}. `
          + `That is the most central of the ${fmt(L.n)} located ${L.prefix} site${L.n === 1 ? '' : 's'} in its grid.`
        : '';
      how.hidden = L.state !== 'approximate';
    }
    if (L.state === 'located') {
      $('location').innerHTML = '<dl class="a-kv">'
        + `<dt>Precision</dt><dd>located to the ${esc(L.p)}</dd>`
        + `<dt>Position</dt><dd class="mono">${fmt(L.lat, 5)}, ${fmt(L.lon, 5)}</dd>`
        + `<dt>Source</dt><dd>${L.source ? (TECH_ANY.test(L.source) ? '<span class="gn-meta">link not shown: it names the technology</span>' : `<a href="${esc(L.source)}" rel="noreferrer">${esc(L.source)}</a>`) : '<span class="gn-meta">not stated</span>'}</dd>`
        + `<dt>Retrieved</dt><dd class="mono">${L.retrieved_at ? esc(L.retrieved_at) : '<span class="gn-meta">not stated</span>'}</dd></dl>`
        + `<p class="gn-meta a-note">${srcLine(L.rec, 'the row whose gates passed')}</p>`;
    } else if (L.state === 'approximate') {
      $('location').innerHTML = `<p class="a-unknown">Approximate position. No surveyed location.</p>`
        + '<dl class="a-kv">'
        + `<dt>Placed near</dt><dd><a class="mono" href="/plant/${encodeURIComponent(L.near)}" data-entity="plant:${esc(L.near)}">${esc(L.near)}</a></dd>`
        + `<dt>Area</dt><dd>${fmt(L.n)} located <span class="mono">${esc(L.prefix)}</span> site${L.n === 1 ? '' : 's'} in this grid</dd>`
        + `<dt>Display at</dt><dd class="mono">${fmt(L.lat, 5)}, ${fmt(L.lon, 5)}</dd></dl>`
        + `<p class="gn-meta a-note">${srcLine(L.rec)}</p>`;
    } else {
      $('location').innerHTML = `<p class="a-unknown">Location not known.</p><p class="gn-meta">${esc(String(L.why || '').charAt(0).toUpperCase() + String(L.why || '').slice(1))}.</p>`
        + `<p class="gn-meta a-note">${srcLine(L.rec)}</p>`;
    }
  }

  /* Every notice that names this plant over the whole span: the year's notices (the shared index,
     by the same match rule) plus the plant's own baked messages, once each, newest first. */
  function plantMessages(P, X) {
    const out = new Map();
    for (const { a, n } of X.bySite.get(P.s) || []) {
      out.set(a.id, { t: a.t, id: a.id, kind: a.kind || noticeKind(a) || 'notice', text: a.text,
                      via: n.how, rec: { id: 'bake-advisories', name: 'Operator messages', file: 'advisories' } });
    }
    for (const m of P.messages) if (!out.has(m.id)) out.set(m.id, m);
    return [...out.values()].sort((x, y) => (x.t < y.t ? 1 : x.t > y.t ? -1 : 0));
  }

  /* Which messages the table shows: all, only those that name the plant, or only the Unclear ones
     (fit another plant too). The Unclear stay one click away and always counted in the control. */
  let msgFilter = 'all';
  const MSG_FILTERS = [['all', 'All'], ['sure', 'Names it'], ['unclear', 'Unclear']];
  const PAGE = 25;
  const pages = {};
  const pageOf = (total, key) => {
    const pg = SHELL && SHELL.pageOf ? SHELL.pageOf(total, pages[key] || 1, PAGE) : { page: 1, from: 0, to: total };
    pages[key] = pg.page;
    return pg;
  };

  function renderMessages(P, X, at) {
    const all = plantMessages(P, X);
    const seg = (tally) => `<div class="gn-seg" role="group" aria-label="Which notices">` + MSG_FILTERS.map(([v, label]) =>
      `<button type="button" data-value="${v}" aria-pressed="${msgFilter === v}">${label} <span class="gn-num">${fmt(tally[v])}</span></button>`).join('') + '</div>';
    if (!all.length) {
      $('messages-filter').innerHTML = '';
      $('messages-meta').textContent = '';
      $('messages').innerHTML = `<div class="gn-empty" role="status"><p class="gn-empty-title">No notice names ${esc(P.s)}</p>`
        + `<p class="gn-empty-body">Its code's letter groups appear in no operator message, and no event record maps one to it.</p>`
        + `<div class="gn-empty-actions"><a class="gn-btn" href="/notices">Open all notices</a></div></div>`;
      return;
    }
    const shown = all.filter((m) => upTo(m.t, at));
    const later = all.length - shown.length;
    const laterLine = later ? `${fmt(later)} later notice${later === 1 ? '' : 's'} after ${when(at)} not shown` : '';
    if (!shown.length) {
      $('messages-filter').innerHTML = '';
      $('messages-meta').textContent = laterLine;
      $('messages').innerHTML = `<div class="gn-empty" role="status"><p class="gn-empty-title">No notice names ${esc(P.s)} up to ${esc(when(at))}</p>`
        + `<p class="gn-empty-body">${esc(laterLine)}. Move the replay clock later to read them.</p></div>`;
      return;
    }
    const marked = shown.map((m) => ({ m, match: messageMatch(P, X, m) }));
    const sure = marked.filter((x) => !x.match.unclear).length;
    const tally = { all: marked.length, sure, unclear: marked.length - sure };
    const listed = marked.filter((x) => msgFilter === 'all' || (msgFilter === 'sure') === !x.match.unclear);
    const pg = pageOf(listed.length, 'messages');
    $('messages-filter').innerHTML = seg(tally);
    $('messages-meta').textContent = `Newest first, up to ${when(at)}${later ? ' · ' + laterLine : ''}`;
    $('messages').innerHTML = (listed.length
      ? '<div class="gn-table-wrap"><table class="gn-table gn-table--compact a-msgs" data-sortable>'
        + '<colgroup><col class="a-m-time"><col class="a-m-id"><col class="a-m-kind"><col><col class="a-m-match"></colgroup>'
        + '<thead><tr><th scope="col" data-sort="time">Time</th><th scope="col" data-sort="text">Notice</th><th scope="col" data-sort="text">Kind</th><th scope="col">Text</th><th scope="col" data-sort="text">Match</th></tr></thead><tbody>'
        + listed.slice(pg.from, pg.to).map(({ m, match }) => `<tr${match.unclear ? ' class="is-unclear"' : ''}>`
          + `<td class="mono" data-value="${esc(m.t)}">${esc(when(m.t))}</td>`
          + `<td class="mono"><a href="/notices?at=${encodeURIComponent(String(m.t).slice(0, 16))}#adv-${esc(m.id)}" data-entity="notice:${esc(m.id)}">${esc(m.id)}</a></td>`
          + `<td>${messageBadge(m.kind)}</td><td class="wrap a-m-text">${opText(withheld(m.text))}</td>`
          + (match.unclear ? `<td class="wrap" title="${esc(match.why)}"><span class="gn-unclear">Unclear</span> <span class="gn-meta">${esc(match.why)}</span></td>`
            : `<td class="wrap gn-meta">names it via ${esc(m.via)}</td>`) + '</tr>').join('')
        + '</tbody></table></div>'
      : `<div class="gn-empty" role="status"><p class="gn-empty-title">No ${msgFilter === 'sure' ? 'notice names it alone' : 'Unclear notice'} up to ${esc(when(at))}</p>`
        + '<div class="gn-empty-actions"><button type="button" class="gn-btn" data-clear>Show all notices</button></div></div>')
      + '<nav class="gn-pager" aria-label="Notice pages" hidden></nav>'
      + `<p class="gn-meta a-note">${fmt(sure)} ${sure === 1 ? 'notice names' : 'notices name'} this site up to ${esc(when(at))}${shown.length > sure ? `. ${fmt(shown.length - sure)} Unclear, not counted` : ''}.</p>`;
    const pagerBox = $('messages').querySelector ? $('messages').querySelector('.gn-pager') : null;
    if (pagerBox && SHELL && SHELL.pager) {
      SHELL.pager(pagerBox, listed.length, pages.messages || 1, PAGE, (n) => {
        pages.messages = n;
        renderMessages(P, X, at);
        const head = $('messages-title');
        if (head && head.scrollIntoView) head.scrollIntoView({ block: 'start' });
      }, 'notices');
    }
    const clear = $('messages').querySelector ? $('messages').querySelector('[data-clear]') : null;
    if (clear) clear.addEventListener('click', () => { msgFilter = 'all'; pages.messages = 1; renderMessages(P, X, at); });
  }

  function renderEvents(P, at) {
    const shown = P.events.filter((e) => upTo(e.t, at));
    if (!shown.length) {
      $('events').innerHTML = `<p class="gn-meta">No reviewable event names <span class="mono">${esc(P.s)}</span>${P.events.length ? ` up to ${esc(when(at))}` : ''}.</p>`;
      return;
    }
    $('events').innerHTML = '<ul class="a-events">' + shown.map((e) => `<li>${eventLink(e, esc(withheld(e.title)))} `
      + `<span class="mono gn-meta">${esc(when(e.t))}</span> <span class="gn-meta">Assumption: ${esc(withheld(e.assumption))}</span></li>`).join('')
      + `</ul><p class="gn-meta">${srcLine(shown[0].rec, `the recorded view is read from ${recName(shown[0].view)}`)}</p>`;
  }

  function renderCatalog(P) {
    $('catalog').innerHTML = '<ul class="a-cat">' + P.catalog.map((c) => '<li>'
      + `<a class="mono" href="/data#${esc(c.id || c.file)}" data-entity="dataset:${esc(c.id || c.file)}">${esc(c.id || c.file)}</a> `
      + `<span>${esc(c.name || (c.id ? '' : 'named by file'))}</span> `
      + `<span class="mono gn-meta">${esc(c.file)}</span> <span class="gn-meta">${esc(c.role)}</span></li>`).join('') + '</ul>';
  }

  /* ------------------------------------------------------------------------- the charts

     Price above, schedule below, one shared time axis. The notices that name the plant and its
     events are marked on the price axis, the replay clock is a dashed line, and a hover (or the
     arrow keys on a focused chart) reads one interval in both series at once. */
  const MARK_TONE = { trip: 'alert', red: 'alert', yellow: 'warning', mld: 'warning', online: 'info' };

  function drawCharts(P, X, at) {
    const times = P.series.t;
    const marks = [];
    if (times.length) {
      const d = String(times[0]).slice(0, 10);
      for (const m of plantMessages(P, X)) {
        if (String(m.t).slice(0, 10) !== d || !upTo(m.t, at) || messageMatch(P, X, m).unclear) continue;
        marks.push({ t: String(m.t).slice(0, 16), kind: m.kind, label: `${hhmm(m.t)} ${MESSAGE_KINDS[m.kind] || m.kind}: ${withheld(m.text)}` });
      }
      for (const e of P.events) {
        if (String(e.t).slice(0, 10) === d && upTo(e.t, at)) marks.push({ t: String(e.t).slice(0, 16), kind: 'event', label: `${hhmm(e.t)} Event: ${withheld(e.title)}` });
      }
    }
    const clockOn = times.length && String(at).slice(0, 10) === String(times[0]).slice(0, 10) ? at : null;
    const a = drawChart('price', times, P.series.lmp, 'Price ₱/MWh', 'price', peso, { marks, clock: clockOn, h: 200 });
    const b = drawChart('mw', times, P.series.mw, 'Scheduled MW', 'mw', (v) => fmt(v, 1), { clock: clockOn, h: 130 });
    const readout = $('readout');
    const read = (i) => {
      if (!readout || i == null || i < 0 || i >= times.length) return;
      const lmp = P.series.lmp[i], mw = P.series.mw[i];
      readout.textContent = `${when(times[i])} · ${lmp == null ? 'price not stated' : peso(lmp) + '/MWh'} · ${mw == null ? 'schedule not stated' : fmt(mw, 1) + ' MW'}`;
      for (const c of [a, b]) if (c) c.at(i);
    };
    let rest = -1;
    if (times.length) {
      if (clockOn) for (let i = 0; i < times.length; i += 1) if (String(times[i]).slice(0, 16) <= clockOn) rest = i;
      if (rest < 0) rest = P.series.lmp.reduce((best, v, i) => (v != null && (best < 0 || v > P.series.lmp[best]) ? i : best), -1);
    }
    if (rest >= 0) read(rest);
    else if (readout) readout.textContent = '';
    const legend = $('chart-legend');
    if (legend) legend.innerHTML = `${clockOn ? '<span class="a-key a-key--clock"></span>Replay clock · ' : ''}`
      + '<span class="a-key a-key--alert"></span>Trip · <span class="a-key a-key--info"></span>Back online · <span class="a-key a-key--event"></span>Event';
    for (const c of [a, b]) {
      if (!c) continue;
      c.onIndex = (i) => (i == null ? read(rest) : read(i));
    }
  }

  function drawChart(where, times, values, label, cls, fmtv, opts) {
    const svg = $(where);
    if (!svg) return null;
    const o = opts || {};
    const W = Math.max(320, svg.getBoundingClientRect().width || 640), H = o.h || 200, L = 48, R = 14, T = o.marks ? 26 : 18, B = 20;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('height', String(H));
    svg.innerHTML = '';
    const n = times.length;
    if (!n) { el('text', { x: L, y: H / 2, class: 'tick' }, svg).textContent = 'No intervals in this build'; return null; }
    const known = values.filter((v) => v != null);
    if (!known.length) { el('text', { x: L, y: H / 2, class: 'tick' }, svg).textContent = `No interval states a ${label.toLowerCase()} figure`; return null; }
    const lo = Math.min(0, ...known), hi = Math.max(...known);
    const x = (i) => L + (i / Math.max(1, n - 1)) * (W - L - R);
    const y = (v) => T + (1 - (v - lo) / Math.max(1e-9, hi - lo)) * (H - T - B);
    const idxOf = (t) => { let k = -1; for (let i = 0; i < n; i += 1) if (String(times[i]).slice(0, 16) <= t) k = i; return k; };
    [lo, (lo + hi) / 2, hi].forEach((v) => {
      el('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: 'grid' }, svg);
      el('text', { x: L - 6, y: y(v) + 3, class: 'tick', 'text-anchor': 'end' }, svg).textContent = fmt(v, 0);
    });
    el('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, class: 'axis' }, svg);
    const step = W < 520 ? 72 : 36;
    for (let i = 0; i < n; i += step) el('text', { x: x(i), y: H - 5, class: 'tick', 'text-anchor': 'middle' }, svg).textContent = hhmm(times[i]);
    /* An unknown interval is a break, never a bridge: a null closes the current segment and
       the next known value opens a new one, so the line never crosses an interval no record
       states. */
    let d = '', open = false;
    values.forEach((v, i) => {
      if (v == null) { open = false; return; }
      d += (open ? 'L' : 'M') + `${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      open = true;
    });
    el('path', { d, class: cls }, svg);
    const peak = values.reduce((best, v, i) => (v != null && (best < 0 || v > values[best]) ? i : best), -1);
    if (peak >= 0) {
      el('circle', { cx: x(peak), cy: y(values[peak]), r: 2.5, class: 'peak-dot' }, svg);
      const right = x(peak) > W - 160;
      el('text', { x: right ? x(peak) - 6 : x(peak) + 6, y: Math.max(T + 8, y(values[peak]) + 4), class: 'lab', 'text-anchor': right ? 'end' : 'start' }, svg).textContent = `${fmtv(values[peak])} at ${hhmm(times[peak])}`;
    }
    el('text', { x: L, y: 11, class: 'lab lab-axis' }, svg).textContent = label;
    if (o.clock) {
      const k = idxOf(o.clock);
      if (k >= 0) el('line', { x1: x(k), x2: x(k), y1: T - 4, y2: H - B, class: 'clock-line' }, svg);
    }
    for (const m of o.marks || []) {
      const k = idxOf(m.t);
      if (k < 0) continue;
      const g = el('g', { class: `mark mark--${m.kind === 'event' ? 'event' : MARK_TONE[m.kind] || 'note'}` }, svg);
      const cx = x(k);
      el('line', { x1: cx, x2: cx, y1: T - 2, y2: H - B, class: 'mark-line' }, g);
      if (m.kind === 'event') el('path', { d: `M${cx},${T - 14} l5,5 l-5,5 l-5,-5 z`, class: 'mark-glyph' }, g);
      else el('path', { d: `M${cx - 5},${T - 13} h10 l-5,8 z`, class: 'mark-glyph' }, g);
      el('title', {}, g).textContent = m.label;
    }
    const hair = el('line', { x1: 0, x2: 0, y1: T - 4, y2: H - B, class: 'xhair', visibility: 'hidden' }, svg);
    const dot = el('circle', { cx: 0, cy: 0, r: 3, class: 'xhair-dot', visibility: 'hidden' }, svg);
    const chart = { onIndex: null, at: (i) => {
      const v = values[i];
      hair.setAttribute('x1', x(i)); hair.setAttribute('x2', x(i)); hair.setAttribute('visibility', 'visible');
      if (v == null) dot.setAttribute('visibility', 'hidden');
      else { dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(v)); dot.setAttribute('visibility', 'visible'); }
    } };
    let focusI = -1;
    const pick = (clientX) => {
      const box = svg.getBoundingClientRect();
      const px = ((clientX - box.left) / Math.max(1, box.width)) * W;
      return Math.max(0, Math.min(n - 1, Math.round(((px - L) / Math.max(1, W - L - R)) * (n - 1))));
    };
    svg.setAttribute('tabindex', '0');
    svg.onmousemove = (e) => { focusI = pick(e.clientX); if (chart.onIndex) chart.onIndex(focusI); };
    svg.onmouseleave = () => { focusI = -1; if (chart.onIndex) chart.onIndex(null); };
    svg.onkeydown = (e) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      focusI = Math.max(0, Math.min(n - 1, (focusI < 0 ? peak : focusI) + (e.key === 'ArrowLeft' ? -1 : 1)));
      if (chart.onIndex) chart.onIndex(focusI);
    };
    const span = `${day(times[0])}, ${hhmm(times[0])} to ${hhmm(times[n - 1])}, five-minute intervals`;
    $('chart-asof').textContent = span;
    return chart;
  }

  /* ------------------------------------------------------------------------- the entry */

  function main() {
    if (document.body.classList.contains('asset-page')) renderProfile();
    else renderIndex();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
})();
