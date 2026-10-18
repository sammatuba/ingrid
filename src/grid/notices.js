/* InGRID notices page (ericka-desk, platform polish PP-B1): every operator notice up to the
   shared as-of clock, newest first, grouped by day. The anchor counts the last six hours by kind;
   one filter bar (grid, kind, period, search) narrows the table and keeps its state in the
   address (GNUI.filters, or the same wiring here without ui.js). A row opens the notice in full
   in the side panel, or in a row under it on a narrow screen, with its event and the plant it
   names. `#adv-<id>` scrolls to and marks one notice. Text only (textContent); the notice text
   goes through the shell's `opText`, so technology words are withheld as on every other page.

   The pure parts (`pick`, `kindOf`, `recent`, `plantMatcher`) are exported for node when `module`
   exists. */
(function () {
  const KIND = { trip: 'Trip', derate: 'Derate', online: 'Back online', red: 'Red alert', yellow: 'Yellow alert', mld: 'Load dropping', notice: 'Notice' };
  const BADGE = { trip: 'alert', red: 'alert', derate: 'warning', yellow: 'warning', mld: 'warning', online: 'info', notice: 'info' };
  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const ALERT_KINDS = new Set(['yellow', 'red', 'mld']);
  const DEFAULTS = { grid: 'all', kind: 'all', period: 'all', q: '' };
  const VALUES = { grid: ['all', 'CLUZ', 'CVIS', 'CMIN'], kind: ['all', 'trip', 'derate', 'alert', 'online', 'notice'], period: ['all', 'day', '6h'] };

  /* A notice's kind word: the advisory's own kind, and a derate where a plain notice's text says so. */
  function kindOf(a) {
    const k = a && a.kind;
    if (k === 'trip' || k === 'online' || k === 'red' || k === 'yellow' || k === 'mld') return k;
    return /derat/i.test(String((a && a.text) || '')) ? 'derate' : 'notice';
  }

  /* Minutes since the epoch for a Manila wall time (`2026-09-21T13:40`), for the six-hour window. */
  function minutesOf(t) {
    const m = String(t || '').match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) / 60000 : NaN;
  }

  /* The notices to show: at or before `at` (minute precision); on its day (`period: 'day'`, or the
     older `days: 'day'`), in the six hours to it (`period: '6h'`), or every day; in the grid and kind
     asked for; matching the search (text or ID); newest first. */
  function pick(list, f) {
    const at = String(f.at || '').slice(0, 16);
    const cut = at + ':59';
    const day = at.slice(0, 10);
    const period = f.period || (f.days === 'day' ? 'day' : 'all');
    const from = minutesOf(at) - 360;
    const q = String(f.q || '').trim().toLowerCase();
    return (list || []).filter((a) => a && a.t <= cut
      && (period !== 'day' || a.t.slice(0, 10) === day)
      && (period !== '6h' || minutesOf(a.t) > from)
      && (!f.grid || f.grid === 'all' || a.grid === f.grid)
      && (!f.kind || f.kind === 'all' || (f.kind === 'alert' ? ALERT_KINDS.has(a.kind) : kindOf(a) === f.kind))
      && (!q || String(a.text || '').toLowerCase().includes(q) || String(a.id || '').toLowerCase().includes(q)))
      .slice().sort((x, y) => (x.t < y.t ? 1 : x.t > y.t ? -1 : 0));
  }

  /* The last six hours to `at`, counted by kind word, in a fixed order (alerts first). */
  function recent(list, at) {
    const rows = pick(list, { at, period: '6h' });
    const counts = {};
    for (const a of rows) { const k = kindOf(a); counts[k] = (counts[k] || 0) + 1; }
    const order = ['red', 'trip', 'yellow', 'mld', 'derate', 'online', 'notice'];
    return { total: rows.length, latest: rows[0] || null, kinds: order.filter((k) => counts[k]).map((k) => ({ kind: k, n: counts[k] })) };
  }

  /* Which plant a notice names (the plant page's rule, src/grid/asset.js): the event record's site
     when one maps it, else the one plant of that grid whose code letters appear in the text. Two or
     more fit: unclear, no link. */
  function plantMatcher(sites, events) {
    const known = new Map((sites || []).map((s) => [s.s, s]));
    const eventOf = new Map();
    for (const e of events || []) if (e && e.advisory != null && !eventOf.has(e.advisory)) eventOf.set(e.advisory, e);
    const tokens = (code) => (String(code).match(/[A-Za-z]{3,}/g) || []).map((t) => new RegExp('(^|[^A-Z])' + t.toUpperCase() + '($|[^A-Z])'));
    const tests = (sites || []).map((s) => ({ s, re: tokens(s.s) }));
    const memo = new Map();
    return (a) => {
      if (!a) return { how: 'none', site: null, candidates: [] };
      if (memo.has(a.id)) return memo.get(a.id);
      const ev = eventOf.get(a.id);
      let out;
      if (ev && known.has(ev.site)) out = { how: 'the event record', site: known.get(ev.site), candidates: [known.get(ev.site)] };
      else {
        const up = String(a.text || '').toUpperCase();
        const hits = tests.filter((x) => (a.grid == null || x.s.g === a.grid) && x.re.length && x.re.some((re) => re.test(up))).map((x) => x.s);
        out = { how: hits.length === 1 ? 'its code in the text' : hits.length ? 'unclear' : 'none', site: hits.length === 1 ? hits[0] : null, candidates: hits };
      }
      memo.set(a.id, out);
      return out;
    };
  }

  /* The filters an address asks for (`?grid=CVIS&kind=trip&period=day&q=pedc`); others fall back. */
  function fromSearch(search) {
    const p = new URLSearchParams(String(search || '').replace(/^\?/, ''));
    const out = Object.assign({}, DEFAULTS);
    for (const k of Object.keys(VALUES)) { const v = p.get(k); if (v && VALUES[k].includes(v)) out[k] = v; }
    out.q = String(p.get('q') || '').slice(0, 120);
    return out;
  }

  const api = { pick, kindOf, recent, plantMatcher, fromSearch, KIND, DEFAULTS };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  window.Notices = api;

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text, parent) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const shell = () => window.GNShell || {};
  const text = (s) => (shell().opText ? shell().opText(s) : String(s || ''));
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const when = (t) => `${Number(t.slice(8, 10))} ${MONTHS[Number(t.slice(5, 7)) - 1]} ${t.slice(11, 16)}`;
  const dayText = (t) => {
    const d = new Date(Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10)));
    return `${WEEKDAYS[d.getUTCDay()]} ${Number(t.slice(8, 10))} ${MONTHS[Number(t.slice(5, 7)) - 1]}`;
  };
  const noticeHref = (a) => `/notices?at=${String(a.t).slice(0, 16)}#adv-${encodeURIComponent(a.id)}`;
  function badge(kind, word, parent) {
    const UI = window.GNUI;
    const node = UI && typeof UI.badge === 'function' ? UI.badge(kind, word) : el('span', 'gn-badge gn-sev gn-badge--' + (BADGE[kind] || 'info'), word || KIND[kind] || 'Notice');
    if (parent) parent.appendChild(node);
    return node;
  }
  function link(href, label, entity, cls, parent) {
    const a = el('a', cls || null, label, parent);
    a.href = href;
    if (entity) a.setAttribute('data-entity', entity);
    return a;
  }

  const SIZE = 25;
  const media = (q, dflt) => (typeof window.matchMedia === 'function' ? window.matchMedia(q) : { matches: dflt, addEventListener() {} });
  const WIDE = media('(min-width: 1100px)', true);
  /* A phone shows three of the six columns (notices.css): a full-width row spans those three. */
  const PHONE = media('(max-width: 760px)', false);
  const span = () => (PHONE.matches ? 3 : 6);
  const state = Object.assign({ page: 1, data: null, events: new Map(), plant: () => ({ how: 'none', site: null, candidates: [] }),
    selected: null, picked: false, focused: false, ctl: null }, fromSearch(location.search));
  const hashId = () => (location.hash.startsWith('#adv-') ? decodeURIComponent(location.hash.slice(5)) : null);

  function render() {
    const body = $('nt-list');
    const at = shell().asOf ? shell().asOf() : null;
    $('nt-asof').textContent = at ? `Up to ${when(at)} Manila` : '';
    body.textContent = '';
    const empty = $('nt-empty');
    empty.textContent = '';
    empty.hidden = true;
    const pagerBox = $('nt-pager');
    renderGlance(at);
    if (!state.data) {
      setCount('No data');
      $('nt-table-card').hidden = true;
      empty.hidden = false;
      const err = el('div', 'gn-error', null, empty);
      err.setAttribute('role', 'alert');
      el('span', null, 'The operator notices could not be read.', err);
      const retry = el('button', 'gn-btn gn-btn--sm', 'Retry', err);
      retry.type = 'button';
      retry.addEventListener('click', () => location.reload());
      if (pagerBox) pagerBox.hidden = true;
      renderDetail(null);
      return;
    }
    const all = pick(state.data, { at });
    const rows = pick(state.data, { at, grid: state.grid, kind: state.kind, period: state.period, q: state.q });
    setCount(rows.length, all.length);
    /* a link names one notice (#adv-<id>): open the page it is on, once */
    const target = hashId();
    const linkedHidden = target && !rows.some((a) => String(a.id) === target) && all.some((a) => String(a.id) === target);
    linkedNote(linkedHidden ? target : null);
    if (!rows.length) {
      $('nt-table-card').hidden = true;
      empty.hidden = false;
      empty.appendChild(all.length ? emptyFiltered(all.length) : emptyNone(at));
      if (pagerBox) pagerBox.hidden = true;
      renderDetail(null);
      return;
    }
    $('nt-table-card').hidden = false;
    if (target && !state.focused) {
      const i = rows.findIndex((a) => String(a.id) === target);
      if (i >= 0) { state.page = Math.floor(i / SIZE) + 1; state.selected = target; state.picked = true; }
    }
    const pg = shell().pageOf ? shell().pageOf(rows.length, state.page, SIZE) : { page: 1, from: 0, to: rows.length };
    state.page = pg.page;
    const shown = rows.slice(pg.from, pg.to);
    /* the selection: a picked notice while it is in view, else the newest one shown (not marked) */
    if (!state.picked || !rows.some((a) => String(a.id) === state.selected)) { state.selected = String(shown[0].id); state.picked = false; }
    let day = null;
    for (const a of shown) {
      const d = a.t.slice(0, 10);
      if (d !== day) {
        day = d;
        const n = rows.filter((x) => x.t.slice(0, 10) === d).length;
        const tr = el('tr', 'nt-day', null, body);
        const th = el('th', null, null, tr);
        th.colSpan = span();
        th.scope = 'colgroup';
        el('span', 'nt-day-label', dayText(d), th);
        el('span', 'gn-meta', `${n} notice${n === 1 ? '' : 's'}`, th);
      }
      body.appendChild(row(a));
    }
    if (shell().pager) shell().pager(pagerBox, rows.length, state.page, SIZE, (n) => { state.page = n; state.picked = false; render(); $('nt-table-card').scrollIntoView({ block: 'start' }); }, 'notices');
    renderDetail(state.data.find((a) => String(a.id) === state.selected) || null);
    if (target && !state.focused) {
      const node = document.getElementById('adv-' + target);
      if (node) { state.focused = true; node.scrollIntoView({ block: 'center' }); }
    }
  }

  function setCount(shown, total) {
    if (state.ctl && typeof shown === 'number') state.ctl.count(shown, total);
    else $('nt-count').textContent = typeof shown === 'number' ? (shown === total ? `${shown} notices` : `${shown} of ${total} notices`) : shown;
  }

  function row(a) {
    const kind = kindOf(a);
    const id = String(a.id);
    const tr = el('tr', 'nt-row' + (id === state.selected ? ' is-selected' : '') + (id === state.selected && state.picked ? ' is-picked' : ''));
    tr.id = 'adv-' + id;
    tr.dataset.id = id;
    if (id === state.selected && state.picked) tr.setAttribute('aria-current', 'true');
    el('td', 'mono nt-time', a.t.slice(11, 16), tr).title = when(a.t);
    badge(kind, null, el('td', null, null, tr));
    el('td', 'nt-grid nt-wide', GRIDS[a.grid] || 'System', tr);
    el('td', 'mono nt-id nt-wide', id, tr);
    /* The text is the row's own link: it opens the notice in full, and keeps a real address
       (a new tab opens this notice). */
    const t = text(a.text);
    const cell = el('td', 'trunc nt-text', null, tr);
    cell.title = t;
    link(noticeHref(a), t, null, 'nt-open', cell);
    const rel = el('td', 'trunc nt-rel nt-wide', null, tr);
    const ev = state.events.get(a.id);
    if (ev) link('/event/' + encodeURIComponent(ev.id), 'Event', 'event:' + ev.id, 'nt-ev', rel);
    const p = state.plant(a);
    if (p.site) { if (ev) rel.appendChild(document.createTextNode(' ')); link('/plant/' + encodeURIComponent(p.site.s), p.site.s, 'plant:' + p.site.s, 'mono nt-plant', rel); }
    else if (p.how === 'unclear') el('span', 'gn-meta', 'Unclear', rel).title = `Fits ${p.candidates.length} plants. None is linked.`;
    return tr;
  }

  /* The panel (or, narrow, the row under the selected one): the full text, the event, the plant. */
  function renderDetail(a) {
    for (const old of document.querySelectorAll('#nt-list tr.nt-inline')) old.remove();
    const host = $('nt-detail-body');
    host.textContent = '';
    $('nt-detail-h').textContent = !a ? 'Notice' : state.picked ? 'Selected notice' : 'Latest notice';
    if (!a) { el('p', 'gn-meta', 'No notice to show with these filters.', host); return; }
    const box = WIDE.matches ? host : null;
    const frag = document.createDocumentFragment();
    const head = el('div', 'nt-d-head', null, frag);
    badge(kindOf(a), null, head);
    el('span', 'mono', when(a.t), head);
    el('span', 'gn-meta', `${GRIDS[a.grid] || 'System'} · ${a.id}`, head);
    el('p', 'nt-d-text', text(a.text), frag);
    const dl = el('dl', 'nt-d-facts', null, frag);
    const fact = (k) => { el('dt', 'gn-label', k, dl); return el('dd', null, null, dl); };
    const ev = state.events.get(a.id);
    const evCell = fact('Event');
    if (ev) link('/event/' + encodeURIComponent(ev.id), text(ev.title || ev.id), 'event:' + ev.id, null, evCell);
    else evCell.appendChild(el('span', 'gn-meta', 'None opened by this notice'));
    const p = state.plant(a);
    const plantCell = fact('Plant');
    if (p.site) {
      link('/plant/' + encodeURIComponent(p.site.s), p.site.name || p.site.s, 'plant:' + p.site.s, null, plantCell);
      el('span', 'gn-meta', `${p.site.name ? ' ' + p.site.s + ' ·' : ''} from ${p.how}`, plantCell);
    } else if (p.how === 'unclear') {
      el('span', 'gn-meta', `Unclear: fits ${p.candidates.map((s) => s.s).join(', ')}. None is linked.`, plantCell);
    } else el('span', 'gn-meta', 'Names no plant in the register', plantCell);
    const acts = el('div', 'nt-d-acts', null, frag);
    const desk = link(`/?at=${String(a.t).slice(0, 16)}${a.grid ? '&grid=' + a.grid : ''}`, 'Open on the desk', null, 'gn-btn gn-btn--sm', acts);
    desk.title = 'The desk at the time this notice was posted';
    const copy = link(noticeHref(a), 'Link to notice', null, 'gn-btn gn-btn--sm gn-btn--ghost', acts);
    copy.title = 'A link that opens this notice';
    if (box) { box.appendChild(frag); return; }
    // narrow: the same content in a row under the selected one, only once a row was picked
    el('p', 'gn-meta', state.picked ? 'Shown under the row.' : 'Pick a row to read a notice in full.', host);
    const tr = document.getElementById('adv-' + a.id);
    if (!tr || !state.picked) return;
    const detail = el('tr', 'gn-row-detail nt-inline');
    const td = el('td', null, null, detail);
    td.colSpan = span();
    el('div', 'nt-inline-body', null, td).appendChild(frag);
    tr.after(detail);
  }

  function select(id, opts) {
    state.selected = String(id);
    state.picked = true;
    if (!opts || opts.address !== false) {
      try { history.replaceState(history.state, '', location.pathname + location.search + '#adv-' + encodeURIComponent(id)); } catch (e) { /* the panel still shows it */ }
    }
    for (const tr of document.querySelectorAll('#nt-list tr.nt-row')) {
      const on = tr.dataset.id === state.selected;
      tr.classList.toggle('is-selected', on);
      tr.classList.toggle('is-picked', on);
      if (on) tr.setAttribute('aria-current', 'true'); else tr.removeAttribute('aria-current');
    }
    renderDetail((state.data || []).find((a) => String(a.id) === state.selected) || null);
  }

  function renderGlance(at) {
    const r = state.data && at ? recent(state.data, at) : null;
    $('nt-recent-count').textContent = r ? String(r.total) : '–';
    const box = $('nt-recent');
    box.textContent = '';
    if (r && r.kinds.length) for (const k of r.kinds) badge(k.kind, `${k.n} ${KIND[k.kind]}`, box);
    else if (r) el('span', 'gn-meta', 'No notice in the six hours to the replay time.', box);
    $('nt-latest').textContent = r && r.latest ? `Latest ${r.latest.t.slice(11, 16)}, ${GRIDS[r.latest.grid] || 'System'}` : '';
    $('nt-glance').classList.toggle('is-quiet', Boolean(r && !r.total));
  }

  function emptyState(title, body, action) {
    const box = el('div', 'gn-empty');
    box.setAttribute('role', 'status');
    el('p', 'gn-empty-title', title, box);
    el('p', 'gn-empty-body', body, box);
    if (action) el('div', 'gn-empty-actions', null, box).appendChild(action);
    return box;
  }
  function emptyFiltered(total) {
    const b = el('button', 'gn-btn', 'Clear filters');
    b.type = 'button';
    b.addEventListener('click', clearFilters);
    return emptyState('No notice matches these filters', `${total} notice${total === 1 ? ' is' : 's are'} hidden by the filters or the search.`, b);
  }
  function emptyNone(at) {
    const S = shell();
    const last = S.span && S.span.last;
    const canMove = Boolean(last && S.setAsOf && at && last > at);
    let b = null;
    if (canMove) { b = el('button', 'gn-btn', 'Go to the latest'); b.type = 'button'; b.addEventListener('click', () => S.setAsOf(last)); }
    return emptyState(at ? `No notice up to ${when(at)}` : 'No notice up to this time',
      canMove ? 'The operator posted nothing before the replay time. Move the clock later to see more.' : 'The replay holds no operator notice.', b);
  }
  function linkedNote(id) {
    const box = $('nt-linked');
    box.textContent = '';
    box.hidden = !id;
    if (!id) return;
    box.appendChild(document.createTextNode(`Notice ${id} is hidden by the filters. `));
    const b = el('button', 'gn-link nt-linked-clear', 'Clear filters', box);
    b.type = 'button';
    b.addEventListener('click', clearFilters);
  }

  function clearFilters() {
    if (state.ctl) { state.ctl.clear(); return; }
    Object.assign(state, DEFAULTS, { page: 1 });
    writeAddress();
    syncControls();
    render();
  }
  /* Without ui.js: the same controls, the same address. */
  function writeAddress() {
    const p = new URLSearchParams(location.search);
    for (const k of Object.keys(DEFAULTS)) { const v = String(state[k] || '').trim(); if (v && v !== DEFAULTS[k]) p.set(k, v); else p.delete(k); }
    const s = p.toString();
    try { history.replaceState(history.state, '', location.pathname + (s ? '?' + s : '') + location.hash); } catch (e) { /* the view still filters */ }
  }
  function syncControls() {
    for (const g of document.querySelectorAll('#nt-filters .gn-seg[data-filter]')) {
      for (const b of g.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === state[g.dataset.filter]));
    }
    const q = $('nt-q');
    if (q.value !== state.q && document.activeElement !== q) q.value = state.q;
    $('nt-clear').hidden = !Object.keys(DEFAULTS).some((k) => String(state[k] || '').trim() !== DEFAULTS[k]);
  }
  function wireFilters() {
    const bar = $('nt-filters');
    const own = () => {
      for (const g of bar.querySelectorAll('.gn-seg[data-filter]')) {
        for (const b of g.querySelectorAll('button')) b.addEventListener('click', () => { state[g.dataset.filter] = b.dataset.value; state.page = 1; writeAddress(); syncControls(); render(); });
      }
      $('nt-q').addEventListener('input', (e) => { state.q = e.target.value; state.page = 1; writeAddress(); syncControls(); render(); });
      $('nt-clear').addEventListener('click', clearFilters);
      syncControls();
    };
    const UI = window.GNUI;
    if (!UI || !UI.ready) { own(); return Promise.resolve(); }
    return UI.ready.then(() => {
      if (typeof UI.filters !== 'function') { own(); return; }
      state.ctl = UI.filters(bar, {
        defaults: DEFAULTS, noun: 'notices',
        onChange: (s) => { Object.assign(state, s, { page: 1 }); render(); },
      });
      Object.assign(state, state.ctl.get());
    }, own);
  }

  function start() {
    if (!$('nt-list')) return;
    syncControls();
    const ready = wireFilters();
    /* A row opens its notice: a click anywhere on it (not on its event or plant link), or Enter
       on its text link. The text link keeps a real address for a new tab. */
    $('nt-list').addEventListener('click', (event) => {
      const tr = event.target.closest && event.target.closest('tr.nt-row');
      if (!tr) return;
      const a = event.target.closest('a');
      if (a && !a.classList.contains('nt-open')) return;
      if (a && (event.ctrlKey || event.metaKey || event.shiftKey || event.button === 1)) return;
      event.preventDefault();
      select(tr.dataset.id);
    });
    window.addEventListener('hashchange', () => {
      const id = hashId();
      if (!id || id === state.selected) return;
      state.focused = false;
      render();
    });
    for (const m of [WIDE, PHONE]) if (typeof m.addEventListener === 'function') m.addEventListener('change', () => render());
    const base = shell().data || '/grid-data/';
    const get = (name) => fetch(base + name).then((r) => (r.ok ? r.json() : r.text().then(() => null))).catch(() => null);
    /* replay-year: a year bake keeps one notice file per month. The clock's month and the one
       before it are read and drawn first, then every month from the span's first up to the
       clock's ("All days"); a later clock month reads its own on the way. A bake without
       month files reads the one advisories.json. */
    let loaded = null;
    const load = () => {
      const S = shell();
      const at = S.asOf ? S.asOf() : null;
      if (!S.notices || !at) {
        return get('advisories.json').then((advisories) => { state.data = Array.isArray(advisories) ? advisories : null; render(); });
      }
      const month = S.monthOf(at);
      if (loaded && month <= loaded) return Promise.resolve(render());
      const mark = loaded = month;
      return S.notices(S.monthPlus(month, -1), month).then((recentRows) => {
        if (loaded !== mark) return null;
        if (!state.data || state.data.length < (recentRows || []).length) { state.data = Array.isArray(recentRows) ? recentRows : null; render(); }
        return S.notices(S.monthOf(S.span.first), month).then((all) => {
          if (loaded !== mark) return;
          state.data = Array.isArray(all) ? all : state.data;
          render();
        });
      });
    };
    if (shell().onAsOf) shell().onAsOf(() => { load(); });
    const records = Promise.all([get('events.json'), get('sites.json')]).then(([events, sites]) => {
      const evs = Array.isArray(events) ? events : [];
      state.events = new Map(evs.map((e) => [e.advisory, e]));
      state.plant = plantMatcher(Array.isArray(sites) ? sites : [], evs);
    });
    (shell().ready || Promise.resolve()).then(() => Promise.all([records, ready])).then(load);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
