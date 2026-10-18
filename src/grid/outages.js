/* ericka-desk E9, E10: the outage and derating tracker card and the schedule-lag note on the
   operator messages, on the dashboard.

   Reads `outages.json` (scripts/grid/build_outages.py) from the page's build-stamped data
   prefix. It follows the dashboard's own clock and grid (`window.GridDesk`), or the shell's
   as-of time on a page without the dashboard, and shows only what was known at that time:
   a record appears at its `first_seen`, and a schedule outage leaves when it ends.

   Rules kept here: a match under 0.5 is shown as "Unclear", is never linked and is not
   counted; no technology or fuel is shown (the bake carries none); a missing file reads
   "No data". The lag is the bake's own figure (RTD schedule against the operator notice);
   this file computes none and reads no forecast.

   The pure part (`visible`, `lagWords`) is exported for node when `module` exists. */
(function (root) {
  'use strict';

  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  /* The shared badge words and tones (ui.js `GNUI.badge`); a scheduled outage has no kind word
     there, so it is a neutral badge of its own. */
  const KIND = {
    trip: ['Trip', 'alert'], derate: ['Derate', 'warning'], outage: ['Scheduled out', null],
    online: ['Back online', 'info'],
  };
  const SHORT = { CLUZ: 'LUZ', CVIS: 'VIS', CMIN: 'MIN' };
  const UNCLEAR = 0.5;
  const LIMIT = 40;

  /* The records known at `t` ("YYYY-MM-DDTHH:MM"), newest first; `grid` null keeps every grid.
     A schedule outage that ended at or before `t` is gone. */
  function visible(records, t, grid) {
    const cut = String(t).slice(0, 16) + ':59';
    const now = String(t).slice(0, 16);
    return (records || []).filter((r) => r.first_seen <= cut
      && (!grid || r.grid === grid)
      && !(r.end && r.end.slice(0, 16) <= now))
      .slice().sort((a, b) => (a.first_seen < b.first_seen ? 1 : a.first_seen > b.first_seen ? -1 : 0));
  }

  /* The short words for the notices table's Lag column (PP-B5): the same figure. */
  function lagShort(r) {
    const w = lagWords(r);
    if (!w) return null;
    if (w.none) return { text: 'No data', title: w.text, none: true };
    const n = Math.abs(r.lag_min);
    return { text: r.lag_min > 0 ? n + ' min early' : r.lag_min < 0 ? n + ' min late' : 'Same minute', title: w.text, none: false };
  }

  /* The words for one notice's lag, or null when the record carries no lag question. */
  function lagWords(r) {
    if (!r || r.source !== 'operator notice' || r.kind !== 'trip') return null;
    if (r.lag_min == null) return { text: 'Official schedule: No data', none: true };
    const n = Math.abs(r.lag_min);
    const min = n === 1 ? '1 min' : n + ' min';
    if (r.lag_min > 0) return { text: min + ' earlier than the official schedule', none: false };
    if (r.lag_min < 0) return { text: 'The official schedule had it ' + min + ' earlier', none: false };
    return { text: 'Same minute as the official schedule', none: false };
  }

  const unclear = (r) => !(r.match_confidence >= UNCLEAR);

  if (typeof module === 'object' && module && module.exports) {
    module.exports = { visible, lagWords, lagShort, unclear };
  }
  if (!root || typeof document === 'undefined' || !document.getElementById) return;

  // ---------- the page ----------
  const stamp = (() => {
    const meta = document.getElementById('nowcast-build');
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = (root.GNShell && root.GNShell.data) || ('/grid-data/' + stamp);
  let bake;          // undefined while loading, null when missing, else the payload
  const byAdvisory = new Map();

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const hhmm = (s) => (s ? s.slice(11, 16) : '—');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  /* the clock's own day reads as its time only; another day as "26 Sep 09:12" */
  function when(s, t) {
    if (!s) return '—';
    if (t && s.slice(0, 10) === String(t).slice(0, 10)) return hhmm(s);
    return Number(s.slice(8, 10)) + ' ' + MONTHS[Number(s.slice(5, 7)) - 1] + ' ' + hhmm(s);
  }

  function clock() {
    const G = root.GridDesk;
    if (G && G.D && G.D.t && G.D.t.length) {
      /* beside the map, so it follows the map's grid scope */
      const snap = G.mapPanel && G.mapPanel.snapshot ? G.mapPanel.snapshot() : null;
      return { t: G.D.t[G.state.i], grid: snap && snap.scope ? snap.scope : null };
    }
    const t = root.GNShell && root.GNShell.asOf ? root.GNShell.asOf() : null;
    return { t, grid: null };
  }

  function badge(kind) {
    const [label, tone] = KIND[kind] || [kind, null];
    const ui = root.GNUI;
    if (tone && ui && typeof ui.badge === 'function') return ui.badge(kind, label);
    return el('span', 'gn-badge' + (tone ? ' gn-badge--' + tone + ' gn-sev' : ''), label);
  }
  /* One dense line per record (PP-B5): the kind as the shared badge, the unit (linked to its plant
     page when the match is sure), the grid, and since when. When it was first known, and from
     what, is the row's title; the schedule lag sits beside its notice in the notices table. */
  function row(r, t) {
    const li = el('li', 'o-item');
    li.appendChild(badge(r.kind));
    if (unclear(r)) {
      const u = el('span', 'o-unit o-unclear', 'Unclear');
      u.title = 'The notice names no unit the desk can match with confidence. Not linked and not counted.';
      li.appendChild(u);
    } else if (r.site) {
      const a = el('a', 'o-unit', r.unit || r.site);
      a.href = '/plant/' + encodeURIComponent(r.site);
      a.dataset.entity = 'plant:' + r.site;
      li.appendChild(a);
    } else {
      li.appendChild(el('span', 'o-unit', r.unit || '—'));
    }
    const grid = el('span', 'o-grid', SHORT[r.grid] || r.grid || '');
    grid.title = GRIDS[r.grid] || '';
    li.appendChild(grid);
    li.appendChild(el('span', 'o-when mono', when(r.start, t)));
    li.title = (r.kind === 'online' ? 'Back ' : 'From ') + when(r.start, t) + (r.end ? ' to ' + when(r.end, t) : '')
      + '. First known ' + when(r.first_seen, t) + ' via ' + r.source + (r.advisory ? ' ' + r.advisory : '') + '.';
    return li;
  }
  function emptyLine(list, title, body) {
    const li = el('li', 'o-empty');
    const e = el('div', 'gn-empty');
    e.setAttribute('role', 'status');
    e.appendChild(el('p', 'gn-empty-title', title));
    if (body) e.appendChild(el('p', 'gn-empty-body', body));
    li.appendChild(e);
    list.appendChild(li);
  }

  function renderCard() {
    const card = document.getElementById('outages');
    if (!card) return;
    const list = document.getElementById('outages-list');
    const count = document.getElementById('outages-count');
    const note = document.getElementById('outages-asof');
    list.textContent = '';
    if (bake === undefined) { count.textContent = ''; note.textContent = 'Loading…'; return; }
    if (bake === null) {
      count.textContent = '';
      note.textContent = '';
      emptyLine(list, 'No outage record in this build', 'This build carries no outage file, so the tracker has No data.');
      return;
    }
    const { t, grid } = clock();
    if (!t) { emptyLine(list, 'No data', 'The replay clock is not set.'); return; }
    const shown = visible(bake.records, t, grid);
    const named = shown.filter((r) => !unclear(r)).length;
    const vague = shown.length - named;
    count.textContent = named + (vague ? ' · ' + vague + ' unclear' : '');
    count.title = vague ? 'Unclear items are listed but not counted.' : '';
    const where = grid ? GRIDS[grid] : 'All grids';
    note.textContent = where + ' · known by ' + when(t + ':00', null) + ' PHT'
      + (bake.blocker ? '. Official schedule not read, so lag is No data.' : '');
    if (!shown.length) {
      emptyLine(list, 'Nothing reported yet at ' + hhmm(t + ':00'), 'Trips, deratings and scheduled outages show here once first known.');
      return;
    }
    for (const r of shown.slice(0, LIMIT)) list.appendChild(row(r, t));
    if (shown.length > LIMIT) list.appendChild(el('li', 'o-more gn-meta', (shown.length - LIMIT) + ' earlier not shown'));
  }

  /* The schedule lag of each operator message the bake has a trip for, in the notices table's
     Lag cell. The table is redrawn by grid.js; the cell is filled after every redraw. */
  function annotateFeed() {
    if (!bake) return;
    for (const tr of document.querySelectorAll('#feed > tr[id^="adv-"]')) {
      const cell = tr.querySelector('.f-sched');
      if (!cell || cell.firstChild) continue;
      const lag = lagShort(byAdvisory.get(tr.id.slice(4)));
      if (!lag) continue;
      const span = el('span', lag.none ? 'f-lag gn-nodata' : 'f-lag mono', lag.text);
      cell.title = lag.title;
      cell.appendChild(span);
    }
  }

  function render() { renderCard(); annotateFeed(); }

  let hooked = false;
  function hook() {
    if (hooked || !root.GridDesk || typeof root.GridDesk.onRender !== 'function') return;
    hooked = true;
    root.GridDesk.onRender(render);
    const feed = document.getElementById('feed');
    if (feed && typeof MutationObserver === 'function') new MutationObserver(annotateFeed).observe(feed, { childList: true });
    for (const b of document.querySelectorAll('.filters button')) b.addEventListener('click', () => setTimeout(renderCard, 0));
    render();
  }

  function load() {
    fetch(DATA + 'outages.json')
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .then((payload) => {
        bake = payload && Array.isArray(payload.records) ? payload : null;
        byAdvisory.clear();
        if (bake) for (const r of bake.records) if (r.advisory && r.kind === 'trip' && !byAdvisory.has(r.advisory)) byAdvisory.set(r.advisory, r);
        render();
      });
  }

  function start() {
    renderCard();
    root.addEventListener('grid-desk-ready', hook);
    hook();
    if (root.GNShell && typeof root.GNShell.onAsOf === 'function') root.GNShell.onAsOf(() => { if (!root.GridDesk) renderCard(); });
    load();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})(typeof window !== 'undefined' ? window : null);
