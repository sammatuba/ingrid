/* Dashboard map controls (UX-3, the map-first desk; PP-B5 polish). One toolbar row along the top
   of the map:
     - the scope pills (All grids, Luzon, Visayas, Mindanao): filter and ease to that grid;
     - the primary layer pills (Prices, Congestion, Events, Plants), each with its count;
     - "More", a popover with the lower-priority layers (Load nodes);
   and, above the map's legend, a chip that counts the sites with no position on record and opens
   their list, by grid, with their price at the clock. The map never draws them (map.js). A site
   at an approximate position (near other sites of its area code) is drawn as a dashed ring: it is
   counted in Plants or Load nodes, each pill's title says how many, and the chip leaves it out.
   All of it drives the map module's own state through its public surface; nothing is fetched.
   It also tells the map which part of it the page's overlays cover (`setInsets`), measured from
   the overlays themselves, so Fit and a scope centre the country in the part that stays visible.

   The pure part (`rows`, `shownText`, `unplacedGroups`) is exported for node when `module` exists. */
(function () {
  /* One pill per layer: its key, its label, its swatch, the map chips it switches, and whether
     it sits in the "More" popover. Events carries the notices and the events together: both are
     drawn by severity. */
  const LAYERS = [
    ['prices', 'Prices', 'sw-price', ['prices'], false],
    ['congestion', 'Congestion', 'sw-link', ['interconnectors'], false],
    ['events', 'Events', 'sw-event', ['events', 'messages'], false],
    ['plants', 'Plants', 'sw-gen', ['generators'], false],
    ['loads', 'Load nodes', 'sw-load', ['loads'], true],
  ];
  const GRIDS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };

  /* One row per pill: on or off, and how many it draws for the scope. Site counts come from the
     site list; prices, congested links and notices from what the map drew at the clock. */
  function rows(sites, scope, snap, layers) {
    const inScope = (sites || []).filter((s) => !scope || s.g === scope);
    const located = inScope.filter((s) => s.p !== 'placeholder');
    const approx = located.filter((s) => s.p === 'approximate');
    const approxOf = { plants: approx.filter((s) => s.k !== 'NL').length, loads: approx.filter((s) => s.k === 'NL').length };
    const count = {
      plants: located.filter((s) => s.k !== 'NL').length,
      loads: located.filter((s) => s.k === 'NL').length,
      congestion: snap && Array.isArray(snap.links) ? snap.links.filter((l) => l.congested === true).length : null,
      prices: snap && snap.price ? snap.price.drawn : null,
      events: snap && Array.isArray(snap.markers) ? snap.markers.reduce((n, m) => n + (m.n || 1), 0) : null,
    };
    return LAYERS.map(([key, label, swatch, chips, more]) => {
      const on = !layers || chips.every((c) => layers[c] !== false);
      const n = count[key];
      return { key, label, swatch, chips, more, on, count: on && n != null ? String(n) : on ? '' : 'off', approx: approxOf[key] || 0 };
    });
  }

  /* The unlocated sites of the map's last draw, by grid in the grids' order, each group with its
     rows as the map gave them (largest registered MW first). */
  function unplacedGroups(pending) {
    const out = [];
    for (const g of Object.keys(GRIDS)) {
      const list = (pending || []).filter((r) => r.grid === g);
      if (list.length) out.push({ grid: g, name: GRIDS[g], rows: list });
    }
    return out;
  }

  function shownText(sites, scope, layers, clock) {
    const on = (k) => !layers || layers[k] !== false;
    const shown = (sites || []).filter((s) => (!scope || s.g === scope) && s.p !== 'placeholder'
      && (s.k === 'NL' ? on('loads') : on('generators')));
    const approx = shown.filter((s) => s.p === 'approximate').length;
    return `${String(clock || '').slice(11, 16)} · ${shown.length.toLocaleString('en-US')} sites shown` +
      `${approx ? `, ${approx.toLocaleString('en-US')} at approximate positions` : ''} · mark size = registered MW at the place`;
  }

  const api = { rows, shownText, unplacedGroups, LAYERS };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  window.DashMap = api;

  const $ = (id) => document.getElementById(id);
  const SVGNS = 'http://www.w3.org/2000/svg';
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }));
  const dot = (fill) => {
    const s = document.createElementNS(SVGNS, 'svg');
    s.setAttribute('class', 'up-dot'); s.setAttribute('viewBox', '0 0 8 8'); s.setAttribute('aria-hidden', 'true');
    const c = document.createElementNS(SVGNS, 'circle');
    c.setAttribute('cx', '4'); c.setAttribute('cy', '4'); c.setAttribute('r', '4'); c.setAttribute('fill', fill || 'currentColor');
    s.appendChild(c);
    return s;
  };

  function start() {
    const G = window.GridDesk;
    const list = $('ml-list');
    const regions = $('map-regions');
    if (!G || !list || !regions || start.done) return;
    start.done = true;
    const panel = () => G.mapPanel;
    const wrap = $('desk-map');
    const moreBtn = $('ml-more'), morePop = $('ml-more-pop');
    const upBtn = $('ml-unplaced'), upPop = $('unplaced-pop');

    const pills = {};
    for (const [key, label, swatch, chips, more] of LAYERS) {
      const b = el('button', more ? 'ml-pill ml-pill--menu' : 'ml-pill');
      b.type = 'button';
      b.dataset.layer = key;
      b.appendChild(el('span', 'ml-sw ' + swatch));
      b.appendChild(el('span', 'ml-label', label));
      b.appendChild(el('span', 'ml-count mono'));
      if (more) b.appendChild(el('span', 'ml-state', ''));
      b.addEventListener('click', () => {
        const m = panel();
        if (!m || !m.chips) return;
        const on = b.getAttribute('aria-pressed') === 'true';
        for (const c of chips) {
          const chip = m.chips[c];
          if (chip && (chip.getAttribute('aria-pressed') === 'true') === on) chip.click();
        }
        sync();
      });
      (more && morePop ? morePop : list).appendChild(b);
      pills[key] = b;
    }

    // ---- the two popovers: one open at a time; Esc, a click outside or the trigger closes it
    let open = null;
    /* Under a toolbar trigger; above the chip over the legend (it opens upwards, toward the free
       sea). Never past the map's edges, scrolling inside itself when the list is long. */
    function place(btn, pop) {
      const host = wrap.getBoundingClientRect(), b = btn.getBoundingClientRect(), bar = $('map-toolbar').getBoundingClientRect();
      const w = pop.offsetWidth || 280;
      // clear of the zoom column on the right edge (52px with its margin)
      const left = Math.min(Math.max(8, b.left - host.left), Math.max(8, host.width - w - (btn === upBtn ? 8 : 60)));
      pop.style.left = Math.round(left) + 'px';
      const ceiling = bar.bottom - host.top + 6;
      if (btn === upBtn) {
        pop.style.top = 'auto';
        pop.style.bottom = Math.round(host.bottom - b.top + 6) + 'px';
        pop.style.maxHeight = Math.max(160, Math.round(b.top - host.top - 6 - ceiling)) + 'px';
        return;
      }
      pop.style.top = Math.round(ceiling) + 'px';
      const replay = $('map-replay');
      const floor = replay && replay.offsetParent ? replay.getBoundingClientRect().top - host.top - 12 : host.height - 16;
      pop.style.maxHeight = Math.max(160, Math.round(floor - ceiling)) + 'px';
    }
    /* The chip stands 6px above the legend, whatever the legend's height (its key opens upwards). */
    function seatChip() {
      const legend = wrap && wrap.querySelector('.gmap-legend');
      if (!upBtn || !legend || !legend.offsetParent) return;
      const host = wrap.getBoundingClientRect(), l = legend.getBoundingClientRect();
      upBtn.style.left = Math.round(l.left - host.left) + 'px';
      upBtn.style.bottom = Math.round(host.bottom - l.top + 6) + 'px';
    }
    function setOpen(btn, pop, on, refocus) {
      if (!btn || !pop) return;
      if (on && open && open.btn !== btn) setOpen(open.btn, open.pop, false, false);
      btn.setAttribute('aria-expanded', String(on));
      pop.hidden = !on;
      open = on ? { btn, pop } : (open && open.btn === btn ? null : open);
      if (on) {
        if (pop === upPop) renderUnplaced();
        place(btn, pop);
        const first = pop.querySelector('button, a[href]');
        if (first && pop === morePop) first.focus({ preventScroll: true });
      } else if (refocus) btn.focus({ preventScroll: true });
    }
    for (const [btn, pop] of [[moreBtn, morePop], [upBtn, upPop]]) {
      if (!btn || !pop) continue;
      btn.addEventListener('click', () => setOpen(btn, pop, btn.getAttribute('aria-expanded') !== 'true', false));
    }
    if (upPop) upPop.addEventListener('click', (e) => { if (e.target.closest('.up-close')) setOpen(upBtn, upPop, false, true); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && open) { e.stopPropagation(); setOpen(open.btn, open.pop, false, true); }
    }, true);
    document.addEventListener('pointerdown', (e) => {
      if (open && !open.pop.contains(e.target) && !open.btn.contains(e.target)) setOpen(open.btn, open.pop, false, false);
    });

    /* The unplaced list: by grid, each site with its price dot (the map's own colour for its
       price), code, name when it reveals no technology, registered MW and price at the clock.
       Each row links to its plant page. */
    function renderUnplaced() {
      if (!upPop || upPop.hidden) return;
      const m = panel();
      const snap = m && m.snapshot ? m.snapshot() : null;
      const body = $('unplaced-body');
      const meta = $('unplaced-meta');
      if (!body) return;
      body.textContent = '';
      const pending = snap ? snap.pending || [] : [];
      const t = G.D.t[G.state.i] || '';
      if (meta) meta.textContent = `${pending.length} · prices at ${t.slice(11, 16)}`;
      if (!pending.length) {
        body.appendChild(el('p', 'up-empty', 'Every site in this scope has a position on the map.'));
        return;
      }
      for (const group of unplacedGroups(pending)) {
        const sec = el('section', 'up-group');
        const h = el('h4', 'up-grid');
        h.appendChild(el('span', null, group.name));
        h.appendChild(el('span', 'mono up-n', String(group.rows.length)));
        sec.appendChild(h);
        const ul = el('ul', 'up-list');
        for (const r of group.rows) {
          const li = el('li');
          const a = el('a', 'up-row');
          a.href = '/plant/' + encodeURIComponent(r.code);
          a.dataset.entity = 'plant:' + r.code;
          a.appendChild(dot(r.fill));
          const id = el('span', 'up-id');
          id.appendChild(el('span', 'mono up-code', r.code));
          const label = r.name || (r.kind === 'NL' ? 'load node' : r.kind === 'PS' ? 'pumped storage' : '');
          if (label) id.appendChild(el('span', 'up-name', label));
          id.title = r.code + (label ? ' · ' + label : '');
          a.appendChild(id);
          a.appendChild(el('span', 'mono up-cap', r.cap ? fmt(r.cap) + ' MW' : '—'));
          a.appendChild(el('span', 'mono up-price', r.value == null ? '—' : '₱' + fmt(r.value)));
          li.appendChild(a);
          ul.appendChild(li);
        }
        sec.appendChild(ul);
        body.appendChild(sec);
      }
    }

    /* The scope is in the address (`?grid=CVIS`, flow F1): a reader who opens a plant from a
       scoped map and comes back finds the same scope; All grids leaves the parameter out. The
       other parameters (`at`) and the hash the replay writes are kept. */
    let lastScope;
    let deepLinked = false;   // the address is written only once its own `?grid=` was read
    function scopeToUrl(scope) {
      if (scope === lastScope) return;
      lastScope = scope;
      try {
        const u = new URL(location.href);
        if ((u.searchParams.get('grid') || null) === scope) return;
        if (scope) u.searchParams.set('grid', scope); else u.searchParams.delete('grid');
        history.replaceState(history.state, '', u.pathname + u.search.replace(/%3A/gi, ':') + u.hash);
      } catch (e) { /* an address that cannot be rewritten keeps the scope on the page only */ }
    }

    function sync() {
      const m = panel();
      if (!m) return;
      const snap = m.snapshot ? m.snapshot() : null;
      const layers = snap ? snap.layers : null;
      const scope = snap ? snap.scope : null;
      if (snap && deepLinked) scopeToUrl(scope);
      for (const b of regions.querySelectorAll('button')) {
        b.setAttribute('aria-pressed', String((b.dataset.scope === 'all' ? null : b.dataset.scope) === scope));
      }
      let moreOff = 0;
      for (const r of rows(G.D.sites, scope, snap, layers)) {
        const b = pills[r.key];
        b.setAttribute('aria-pressed', String(r.on));
        b.querySelector('.ml-count').textContent = r.on ? r.count : '';
        const state = b.querySelector('.ml-state');
        if (state) state.textContent = r.on ? 'On' : 'Off';
        b.title = `${r.on ? 'Hide' : 'Show'} ${r.label.toLowerCase()} on the map` +
          (r.approx ? `. ${r.approx} at approximate positions, drawn as dashed rings.` : '');
        b.classList.toggle('hot', r.key === 'congestion' && r.on && Number(r.count) > 0);
        if (r.more && !r.on) moreOff += 1;
      }
      if (moreBtn) {
        moreBtn.classList.toggle('has-off', moreOff > 0);
        moreBtn.title = moreOff ? `${moreOff} more layer${moreOff === 1 ? '' : 's'} hidden` : 'More layers';
      }
      if (upBtn) {
        const n = snap && snap.pending ? snap.pending.length : 0;
        upBtn.hidden = !n;
        const count = $('ml-unplaced-n');
        if (count) count.textContent = String(n);
        upBtn.title = `${n} site${n === 1 ? '' : 's'} with no position on record. Open the list.`;
        seatChip();
        if (!n && open && open.pop === upPop) setOpen(upBtn, upPop, false, false);
      }
      renderUnplaced();
      const sub = $('map-sub');
      if (sub) sub.textContent = shownText(G.D.sites, scope, layers, G.D.t[G.state.i]);
    }

    for (const b of regions.querySelectorAll('button')) {
      b.addEventListener('click', () => {
        const m = panel();
        if (!m) return;
        const g = b.dataset.scope === 'all' ? null : b.dataset.scope;
        m.setScope(g);
        /* Zooms and filters the map only; the page's grid is left as it was. The page renders
           again so the state card and the scope summary follow. */
        G.setGrid(G.state.grid);
      });
    }

    /* What the overlays cover, in px from each edge of the map: the state card on the left (or
       above, on a phone, where it is a strip), the toolbar above (its real height, so a row that
       wraps is covered too), the zoom column on the right, and below the replay, the legend and
       the command bar's clear band (about 96px at the bottom centre, PP-A's floating bar). */
    const CMD_BAND = 104;
    function insets() {
      const m = panel();
      const host = $('map');
      if (!m || !m.setInsets || !host) return;
      const box = host.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const rect = (id) => { const n = typeof id === 'string' ? $(id) : id; return n && n.offsetParent !== null ? n.getBoundingClientRect() : null; };
      const card = rect('overview'), bar = rect('map-toolbar'), replay = rect('map-replay');
      const zoom = rect(host.querySelector('.gmap-zoom'));
      const phone = window.matchMedia && window.matchMedia('(max-width: 760px)').matches;
      const out = { left: 0, top: 0, right: 0, bottom: 0 };
      const below = (r) => (r ? r.bottom - box.top + 8 : 0);
      out.top = Math.max(below(bar), 0);
      if (card) {
        if (phone || card.height < 140 || card.width > box.width * 0.5) out.top = Math.max(out.top, below(card));
        else out.left = card.right - box.left + 12;
      }
      if (zoom && !phone) out.right = box.right - zoom.left + 8;
      const legend = rect(host.querySelector('.gmap-legend'));
      const lowest = phone && legend && replay ? Math.min(legend.top, replay.top) : replay ? replay.top : null;
      out.bottom = lowest != null ? Math.max(box.bottom - lowest + 8, phone ? 0 : CMD_BAND) : 0;
      m.setInsets(out);
    }
    let queued = false;
    const later = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; insets(); seatChip(); if (open) place(open.btn, open.pop); }); };

    /* Deep links from the command bar and the live strip, on load and on history moves:
       `?grid=CLUZ|CVIS|CMIN` scopes the map to that grid (its state-card row shows pressed), and
       `?link=VISLUZ1|MINVIS1` turns congestion on, zooms to that link and pins its popover.
       `?at=` is the shell's (overview.js reads it). Nothing is fetched. */
    function deepLink() {
      const m = panel();
      deepLinked = true;
      if (!m) return;
      let q = null;
      try { q = new URLSearchParams(location.search); } catch (e) { return; }
      const g = q.get('grid'), link = q.get('link');
      if (g && ['CLUZ', 'CVIS', 'CMIN'].includes(g)) { m.setScope(g); G.setGrid(g); }
      if (link && m.focusLink && window.GridMap && window.GridMap.LINK_DEFS[link]) { m.focusLink(link); sync(); }
    }
    window.addEventListener('popstate', deepLink);
    G.onRender(() => { sync(); });
    window.addEventListener('resize', later);
    window.addEventListener('grid-overlay-change', later);
    /* the site prices land after the first paint (the page drops the map's `pricing` class
       then); count again so Prices does not stay at 0 */
    if (wrap && window.MutationObserver) new MutationObserver(sync).observe(wrap, { attributes: true, attributeFilter: ['class'] });
    if (typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver(later);
      for (const id of ['overview', 'map-toolbar']) if ($(id)) ro.observe($(id));
      const legend = wrap && wrap.querySelector('.gmap-legend');
      if (legend) ro.observe(legend);
    }
    sync();
    insets();
    /* after the first insets, so the zoom frames the part of the map left visible */
    requestAnimationFrame(() => deepLink());
  }
  window.addEventListener('grid-desk-ready', start);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
