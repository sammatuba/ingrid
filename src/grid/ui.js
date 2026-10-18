/* InGRID shared behaviours (platform polish, 2026-10-18). The contract is
   docs/work/platform-polish-2026-10-18/design-system.md. shell.js loads this file on every page,
   as early as it can, and sets up `window.GNUI.ready` first, so a page script can always write
   `GNUI.ready.then(...)`.

   Everything is bound by listeners delegated on the document, so a table, menu, tab list or
   entity link a page draws after load works with no setup call:
   * `table[data-sortable]` with `th[data-sort="text|num|time"]`: the header becomes a button,
     a click sorts the rows in place (a row's `tr.gn-row-detail` moves with it) and sets
     `aria-sort`. Sort keys read `td[data-value]` when present, else the cell's text.
     `GNUI.sort(table, col, dir)` and `GNUI.resort(table)` (after a page redraws a tbody).
   * the sticky header's shadow once the table scrolls under the bar;
   * `tr[data-href]`: the whole row opens its page, except a click on a link, button or field
     inside it; Enter on a focused row; Ctrl, Cmd or the middle button open a new tab;
   * `button[aria-expanded][aria-controls]` in a table row toggles its `tr.gn-row-detail`;
   * `[data-menu]` opens its `.gn-menu[role=menu]` (arrow keys, Home, End, Esc, click outside);
   * `[data-tabs]` tab lists: arrow keys, Home and End, and `#tab=name:panel` in the address;
   * `GNUI.filters(root, {defaults, onChange})`: pressed-button groups, search fields and
     selects kept in step with the address query, with the Clear button and the count;
   * `a[data-entity="kind:id"]` anywhere: the hover and focus preview card from
     `/api/desk/preview/<kind>/<id>?at=`, the one card and the one cache the command bar uses.

   No library, no network beyond this origin's desk API, no inline style in written markup (the
   page policy forbids it): placement is CSSOM writes only. */
(() => {
  'use strict';
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const G = window.GNUI || {};
  if (G.version) return;  // loaded twice: the first copy holds the listeners
  window.GNUI = G;

  const doc = document;
  const root = doc.documentElement;
  const API = '/api/desk/';
  const SITE_HREF = /^\/(?![/\\])[A-Za-z0-9/_\-.~%#?=&:,+]*$/;
  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"\x27]/g,
    (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\x27': '&#39;'}[c]));
  const list = (value) => (Array.isArray(value) ? value : []);
  const safeHref = (href) => (typeof href === 'string' && SITE_HREF.test(href) ? href : '');
  const hhmm = (t) => (/T\d\d:\d\d/.test(String(t || '')) ? String(t).slice(11, 16) : '');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const dayWords = (t) => {
    const found = /^(\d{4})-(\d\d)-(\d\d)/.exec(String(t || ''));
    return found ? Number(found[3]) + ' ' + MONTHS[Number(found[2]) - 1] : '';
  };
  const asOf = () => {
    try {
      const t = window.GNShell && typeof window.GNShell.asOf === 'function' && window.GNShell.asOf();
      if (t) return String(t).slice(0, 16);
    } catch (error) { /* no shell, no clock */ }
    return '';
  };
  const closest = (node, sel) => (node && typeof node.closest === 'function' ? node.closest(sel) : null);
  const plainClick = (event) => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  const INTERACTIVE = 'a[href], button, input, select, textarea, label, summary, details, [role="menu"], [role="menuitem"], [contenteditable], [data-no-row]';

  /* ---------- glyphs: 16px line icons (stroke 1.5, currentColor) ---------- */
  const PATHS = {
    plant: '<path d="M9 1.5 3.5 9H8l-1 5.5L12.5 7H8z"/>',
    event: '<path d="M1.5 8.5h3l1.5-4 3 8 1.5-4h4"/>',
    region: '<path d="M2 4.25 6 2.5l4 2 4-1.75v9.5L10 14l-4-2-4 1.75z"/><path d="M6 2.5V12M10 4.5V14"/>',
    link: '<circle cx="3.25" cy="8" r="1.75"/><circle cx="12.75" cy="8" r="1.75"/><path d="M5 8h6"/>',
    notice: '<path d="M4 1.5h5l3 3v10H4z"/><path d="M9 1.5v3h3M6.25 8h3.5M6.25 11h3.5"/>',
    dataset: '<ellipse cx="8" cy="3.75" rx="5" ry="2"/><path d="M3 3.75v8.5c0 1.1 2.24 2 5 2s5-.9 5-2v-8.5M3 8c0 1.1 2.24 2 5 2s5-.9 5-2"/>',
    alert: '<path d="M8 2.3 14.2 13.2H1.8ZM8 6.4v3.2M8 11.4v.1"/>',
    page: '<rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="M2 6h12"/>',
    arrow: '<path d="M3 8h10M9 4l4 4-4 4"/>',
    out: '<path d="M6 3.5h6.5V10M12.5 3.5 4 12"/>',
    copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5v-2A1.5 1.5 0 0 0 9 2H4a1.5 1.5 0 0 0-1.5 1.5V9A1.5 1.5 0 0 0 4 10.5h1.5"/>',
    close: '<path d="m4 4 8 8M12 4l-8 8"/>',
    empty: '<rect x="2" y="3" width="12" height="10" rx="1.5"/><path d="M2 9.5h3.5l1 1.5h3l1-1.5H14"/>',
    dot: '<circle cx="8" cy="8" r="2"/>',
  };
  const icon = (name, cls) => '<svg class="gn-pi' + (cls ? ' ' + cls : '') + '" viewBox="0 0 16 16"'
    + ' aria-hidden="true" focusable="false">' + (PATHS[name] || PATHS.dot) + '</svg>';

  /* ---------- kind words and badges: the same word and style on every page ---------- */
  const KIND_BADGE = {
    trip: ['Trip', 'alert'], red: ['Red alert', 'alert'], yellow: ['Yellow alert', 'warning'],
    mld: ['Load dropping', 'warning'], derate: ['Derate', 'warning'], online: ['Back online', 'ok'],
    notice: ['Notice', 'info'], extreme: ['Extreme', 'alert'], high: ['High', 'alert'],
    medium: ['Medium', 'warning'], low: ['Low', 'info'],
  };
  /* `GNUI.badge('trip')` is `<span class="gn-badge gn-badge--alert gn-sev">Trip</span>`;
     `GNUI.badgeHtml(kind)` is the same as markup. An unknown kind is a neutral badge of its own word. */
  function badgeParts(kind, word) {
    const hit = KIND_BADGE[String(kind || '').toLowerCase()];
    return hit ? {word: word || hit[0], cls: 'gn-badge gn-badge--' + hit[1] + ' gn-sev', sev: hit[1]}
      : {word: word || String(kind || ''), cls: 'gn-badge', sev: null};
  }
  function badge(kind, word) {
    const p = badgeParts(kind, word);
    const span = doc.createElement('span');
    span.className = p.cls;
    span.textContent = p.word;
    return span;
  }
  const badgeHtml = (kind, word) => { const p = badgeParts(kind, word); return '<span class="' + p.cls + '">' + esc(p.word) + '</span>'; };

  /* ============================================================
     Tables: sorting, sticky shadow, row links, expandable rows
     ============================================================ */
  const DIR = {asc: 'ascending', ascending: 'ascending', desc: 'descending', descending: 'descending'};
  const headCells = (table) => {
    const row = table.tHead && table.tHead.rows[table.tHead.rows.length - 1];
    return row ? Array.from(row.cells) : [];
  };
  function sortKey(cell, type) {
    if (!cell) return null;
    const raw = cell.hasAttribute('data-value') ? cell.getAttribute('data-value')
      : (cell.querySelector('time[datetime]') && type === 'time' ? cell.querySelector('time[datetime]').getAttribute('datetime') : cell.textContent);
    const text = String(raw == null ? '' : raw).trim();
    if (!text || text === '—' || text === '-') return null;
    if (type === 'num') {
      const n = parseFloat(text.replace(/[−–]/g, '-').replace(/[^\d.eE+-]/g, ''));
      return Number.isFinite(n) ? n : null;
    }
    if (type === 'time') {
      const iso = /^\d{4}-\d\d-\d\d[T ]\d\d:\d\d/.test(text) ? text.slice(0, 10) + 'T' + text.slice(11, 16) + ':00Z'
        : /^\d{4}-\d\d-\d\d$/.test(text) ? text + 'T00:00:00Z' : text;
      const t = Date.parse(iso);
      return Number.isFinite(t) ? t : null;
    }
    return text.toLowerCase();
  }
  const collator = typeof Intl !== 'undefined' && Intl.Collator ? new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'}) : null;
  const selfSorting = new WeakSet();

  /* Sorts `table` by column `col` (0-based, counted in the last header row) in `dir`
     ('ascending' or 'descending'). Rows without a value go last either way. Stable. */
  function sort(table, col, dir) {
    if (!table || !table.tBodies) return;
    const ths = headCells(table);
    const th = ths[col];
    if (!th) return;
    const type = th.getAttribute('data-sort') || 'text';
    const way = DIR[dir] || 'ascending';
    const sign = way === 'ascending' ? 1 : -1;
    selfSorting.add(table);
    Array.from(table.tBodies).forEach((tbody) => {
      const groups = [];
      Array.from(tbody.rows).forEach((tr) => {
        if (tr.classList.contains('gn-row-detail') && groups.length) groups[groups.length - 1].rows.push(tr);
        else groups.push({rows: [tr], fixed: tr.hasAttribute('data-sort-fixed')});
      });
      const movable = groups.filter((g) => !g.fixed);
      movable.forEach((g, i) => { g.i = i; g.k = sortKey(g.rows[0].cells[col], type); });
      movable.sort((a, b) => {
        if (a.k === null && b.k === null) return a.i - b.i;
        if (a.k === null) return 1;
        if (b.k === null) return -1;
        let d;
        if (type === 'text') d = collator ? collator.compare(a.k, b.k) : (a.k < b.k ? -1 : a.k > b.k ? 1 : 0);
        else d = a.k - b.k;
        return d ? d * sign : a.i - b.i;
      });
      const frag = doc.createDocumentFragment();
      movable.forEach((g) => g.rows.forEach((tr) => frag.appendChild(tr)));
      groups.filter((g) => g.fixed).forEach((g) => g.rows.forEach((tr) => frag.appendChild(tr)));
      tbody.appendChild(frag);
    });
    ths.forEach((cell) => { if (cell !== th) cell.removeAttribute('aria-sort'); });
    th.setAttribute('aria-sort', way);
    if (observer) observer.takeRecords();
    selfSorting.delete(table);
    table.dispatchEvent(new CustomEvent('gn-sort', {bubbles: true, detail: {col: col, dir: way, type: type}}));
  }
  /* Re-applies the active sort (the header with aria-sort), after a page redraws its rows. */
  function resort(table) {
    const ths = headCells(table);
    const i = ths.findIndex((th) => th.hasAttribute('data-sort') && /^(ascending|descending)$/.test(th.getAttribute('aria-sort') || ''));
    if (i >= 0) sort(table, i, ths[i].getAttribute('aria-sort'));
  }
  /* A sortable header becomes one button holding its words and the sort mark. */
  function enhanceTable(table) {
    if (!table || !table.matches || !table.matches('table[data-sortable]')) return;
    headCells(table).forEach((th) => {
      if (!th.hasAttribute('data-sort') || th.querySelector(':scope > .gn-sort')) return;
      const button = doc.createElement('button');
      button.type = 'button';
      button.className = 'gn-sort';
      const words = doc.createElement('span');
      while (th.firstChild) words.appendChild(th.firstChild);
      const mark = doc.createElement('span');
      mark.className = 'gn-sort-ind';
      mark.setAttribute('aria-hidden', 'true');
      button.append(words, mark);
      if (th.title) { button.title = th.title; th.removeAttribute('title'); }
      th.appendChild(button);
    });
  }
  function onSortClick(event) {
    const th = closest(event.target, 'table[data-sortable] th[data-sort]');
    if (!th || event.defaultPrevented) return;
    const table = th.closest('table');
    enhanceTable(table);
    const ths = headCells(table);
    const col = ths.indexOf(th);
    if (col < 0) return;
    const now = th.getAttribute('aria-sort');
    const type = th.getAttribute('data-sort');
    const first = type === 'text' ? 'ascending' : 'descending';
    const next = now === 'ascending' ? 'descending' : now === 'descending' ? 'ascending' : first;
    sort(table, col, next);
    const button = th.querySelector('.gn-sort');
    if (button && doc.activeElement !== button && event.detail === 0) button.focus();
  }

  /* The sticky header's shadow: on while the table runs under the bar. */
  let stuckFrame = 0;
  function checkStuck() {
    stuckFrame = 0;
    const tables = doc.querySelectorAll('table.gn-table');
    if (!tables.length) return;
    const barH = parseFloat(getComputedStyle(root).getPropertyValue('--bar-h')) || 0;
    tables.forEach((table) => {
      const head = table.tHead;
      if (!head) return;
      const th = head.rows[0] && head.rows[0].cells[0];
      const top = th ? parseFloat(getComputedStyle(th).top) : NaN;
      const at = Number.isFinite(top) ? top : barH;
      const r = table.getBoundingClientRect();
      const stuck = r.top < at - 0.5 && r.bottom > at + head.offsetHeight + 4;
      table.classList.toggle('is-stuck', stuck);
    });
  }
  const queueStuck = () => { if (!stuckFrame) stuckFrame = window.requestAnimationFrame(checkStuck); };

  /* Row links. */
  /* A row opens a page of this site (`/plant/08PEDC`) or a target on this page (`#bake-nodes`:
     the catalog's and the models' rows). A hash row sets the address's hash, so the browser
     scrolls to the target and the page hears `hashchange`. */
  const SAME_PAGE = /^#[A-Za-z0-9_\-.:~%=&,+]+$/;
  function rowHref(tr) {
    const raw = tr.getAttribute('data-href') || '';
    return SAME_PAGE.test(raw) ? raw : safeHref(raw);
  }
  function openRow(tr, newTab) {
    const href = rowHref(tr);
    if (!href) return;
    if (href.charAt(0) === '#') {
      if (newTab) { window.open(window.location.pathname + window.location.search + href, '_blank', 'noopener'); return; }
      if (window.location.hash === href) window.dispatchEvent(new HashChangeEvent('hashchange'));
      else window.location.hash = href;
      return;
    }
    if (newTab) window.open(href, '_blank', 'noopener');
    else window.location.assign(href);
  }
  function onRowClick(event) {
    const tr = closest(event.target, 'tr[data-href]');
    if (!tr || event.defaultPrevented) return;
    const inner = closest(event.target, INTERACTIVE);
    if (inner && tr.contains(inner) && inner !== tr) return;
    const sel = window.getSelection && window.getSelection();
    if (sel && String(sel).trim() && sel.anchorNode && tr.contains(sel.anchorNode)) return;
    if (event.button === 1 || event.metaKey || event.ctrlKey) { openRow(tr, true); return; }
    if (event.button !== 0 || event.shiftKey || event.altKey) return;
    openRow(tr, false);
  }
  function onRowAux(event) {
    if (event.button !== 1) return;
    const tr = closest(event.target, 'tr[data-href]');
    if (!tr || closest(event.target, 'a[href]')) return;
    event.preventDefault();
    openRow(tr, true);
  }
  function enhanceRows(scope) {
    const rows = scope.matches && scope.matches('tr[data-href]') ? [scope] : Array.from(scope.querySelectorAll ? scope.querySelectorAll('tr[data-href]') : []);
    rows.forEach((tr) => {
      if (!tr.hasAttribute('tabindex') && !tr.querySelector('a[href]')) tr.tabIndex = 0;
    });
  }

  /* Expandable rows: the toggle names the detail row in aria-controls. */
  function onExpand(event) {
    const button = closest(event.target, 'button[aria-expanded][aria-controls]');
    if (!button || event.defaultPrevented || !closest(button, 'tr')) return;
    const target = doc.getElementById(button.getAttribute('aria-controls'));
    if (!target || !target.matches('tr.gn-row-detail')) return;
    const open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    target.hidden = !open;
    event.stopPropagation();
    target.dispatchEvent(new CustomEvent('gn-expand', {bubbles: true, detail: {open: open, button: button}}));
  }

  /* ============================================================
     Menus
     ============================================================ */
  let openMenu = null;  // {button, menu}
  const menuItems = (menu) => Array.from(menu.querySelectorAll('[role^="menuitem"]'))
    .filter((n) => !n.hidden && n.getAttribute('aria-disabled') !== 'true' && !n.disabled);
  function menuFor(button) {
    const id = button.getAttribute('aria-controls');
    let menu = id ? doc.getElementById(id) : null;
    if (!menu) {
      const next = button.nextElementSibling;
      if (next && next.classList.contains('gn-menu')) menu = next;
    }
    if (!menu) return null;
    if (!menu.id) menu.id = 'gn-menu-' + Math.random().toString(36).slice(2, 9);
    menu.setAttribute('role', 'menu');
    Array.from(menu.children).forEach((child) => {
      if (child.matches('a[href], button') && !child.getAttribute('role')) child.setAttribute('role', 'menuitem');
    });
    menuItems(menu).forEach((item) => { item.tabIndex = -1; });
    button.setAttribute('aria-haspopup', 'menu');
    button.setAttribute('aria-controls', menu.id);
    if (!button.hasAttribute('aria-expanded')) button.setAttribute('aria-expanded', 'false');
    return menu;
  }
  function placeMenu(button, menu) {
    menu.style.left = '0px';
    menu.style.top = '0px';
    const r = button.getBoundingClientRect();
    const w = menu.offsetWidth;
    const h = menu.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left = r.right - w;
    if (left < 8) left = Math.min(r.left, vw - w - 8);
    let top = r.bottom + 4;
    if (top + h > vh - 8 && r.top - h - 4 > 8) top = r.top - h - 4;
    menu.style.left = Math.round(Math.max(8, left)) + 'px';
    menu.style.top = Math.round(Math.max(8, top)) + 'px';
  }
  function showMenu(button, focusLast) {
    const menu = menuFor(button);
    if (!menu) return;
    if (openMenu && openMenu.menu !== menu) closeMenu(false);
    menu.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    openMenu = {button: button, menu: menu};
    placeMenu(button, menu);
    const items = menuItems(menu);
    const first = focusLast ? items[items.length - 1] : items[0];
    if (first) first.focus({preventScroll: true});
    menu.dispatchEvent(new CustomEvent('gn-menu', {bubbles: true, detail: {open: true}}));
  }
  function closeMenu(focusBack) {
    if (!openMenu) return;
    const {button, menu} = openMenu;
    openMenu = null;
    menu.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (focusBack && button.isConnected) button.focus({preventScroll: true});
    menu.dispatchEvent(new CustomEvent('gn-menu', {bubbles: true, detail: {open: false}}));
  }
  function onMenuClick(event) {
    const button = closest(event.target, '[data-menu]');
    if (button && !event.defaultPrevented) {
      event.preventDefault();
      event.stopPropagation();
      if (openMenu && openMenu.button === button) closeMenu(true);
      else showMenu(button, false);
      return;
    }
    if (openMenu) {
      const item = closest(event.target, '[role^="menuitem"]');
      if (item && openMenu.menu.contains(item)) {
        if (item.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
        setTimeout(() => closeMenu(!item.matches('a[href]')), 0);
      }
    }
  }
  function onMenuKey(event) {
    const button = closest(event.target, '[data-menu]');
    if (button && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      event.preventDefault();
      showMenu(button, event.key === 'ArrowUp');
      return true;
    }
    if (!openMenu || !openMenu.menu.contains(event.target)) return false;
    const items = menuItems(openMenu.menu);
    const at = items.indexOf(doc.activeElement);
    let next = null;
    if (event.key === 'ArrowDown') next = items[(at + 1) % items.length];
    else if (event.key === 'ArrowUp') next = items[(at - 1 + items.length) % items.length];
    else if (event.key === 'Home') next = items[0];
    else if (event.key === 'End') next = items[items.length - 1];
    else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeMenu(true); return true; }
    else if (event.key === 'Tab') { closeMenu(false); return false; }
    else if ((event.key === ' ' || event.key === 'Enter') && doc.activeElement && doc.activeElement.matches('button[role^="menuitem"]')) return false;
    else if (event.key.length === 1 && /\S/.test(event.key)) {
      const ch = event.key.toLowerCase();
      next = items.slice(at + 1).concat(items.slice(0, at + 1)).find((n) => n.textContent.trim().toLowerCase().startsWith(ch)) || null;
    }
    if (next) { event.preventDefault(); next.focus(); }
    return Boolean(next);
  }

  /* ============================================================
     Tabs
     ============================================================ */
  const tabsOf = (list) => Array.from(list.querySelectorAll('[role="tab"]')).filter((t) => closest(t, '[data-tabs]') === list);
  const tabKey = (tab) => tab.getAttribute('data-tab') || tab.getAttribute('aria-controls') || '';
  function hashTabs() {
    const found = /(?:^#|[&,])tab=([^&]*)/.exec(window.location.hash || '');
    const out = {};
    if (!found) return out;
    decodeURIComponent(found[1]).split(',').forEach((pair) => {
      const i = pair.indexOf(':');
      if (i > 0) out[pair.slice(0, i)] = pair.slice(i + 1);
    });
    return out;
  }
  function writeHash(name, key) {
    const hash = window.location.hash || '';
    if (hash && !/^#tab=/.test(hash)) return;  // the page's own anchor (#adv-…) wins
    const tabs = hashTabs();
    tabs[name] = key;
    const value = Object.keys(tabs).map((k) => k + ':' + tabs[k]).join(',');
    try { history.replaceState(history.state, '', window.location.pathname + window.location.search + '#tab=' + value); } catch (error) { /* sandboxed */ }
  }
  function selectTab(list, tab, opts) {
    const o = opts || {};
    const tabs = tabsOf(list);
    if (typeof tab === 'string') tab = tabs.find((t) => tabKey(t) === tab) || null;
    if (!tab) return;
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      const panel = doc.getElementById(t.getAttribute('aria-controls') || '');
      if (panel) {
        panel.hidden = !on;
        if (!panel.hasAttribute('role')) panel.setAttribute('role', 'tabpanel');
        if (!panel.hasAttribute('tabindex')) panel.tabIndex = 0;
        if (t.id && !panel.hasAttribute('aria-labelledby')) panel.setAttribute('aria-labelledby', t.id);
      }
    });
    if (o.focus) tab.focus();
    const name = list.getAttribute('data-tabs');
    if (name && o.user) writeHash(name, tabKey(tab));
    list.dispatchEvent(new CustomEvent('gn-tab', {bubbles: true, detail: {tab: tab, key: tabKey(tab)}}));
  }
  function enhanceTabs(list) {
    if (list.hasAttribute('data-gn-tabs')) return;
    list.setAttribute('data-gn-tabs', '');
    if (!list.hasAttribute('role')) list.setAttribute('role', 'tablist');
    const tabs = tabsOf(list);
    if (!tabs.length) return;
    const wanted = hashTabs()[list.getAttribute('data-tabs')];
    const fromHash = wanted ? tabs.find((t) => tabKey(t) === wanted) : null;
    const chosen = fromHash || tabs.find((t) => t.getAttribute('aria-selected') === 'true') || tabs[0];
    selectTab(list, chosen, {});
  }
  function onTabClick(event) {
    const tab = closest(event.target, '[data-tabs] [role="tab"]');
    if (!tab || event.defaultPrevented) return;
    const list = closest(tab, '[data-tabs]');
    enhanceTabs(list);
    selectTab(list, tab, {user: true});
  }
  function onTabKey(event) {
    const tab = closest(event.target, '[data-tabs] [role="tab"]');
    if (!tab) return false;
    const list = closest(tab, '[data-tabs]');
    const tabs = tabsOf(list);
    const i = tabs.indexOf(tab);
    const vertical = list.getAttribute('aria-orientation') === 'vertical';
    let next = null;
    if (event.key === (vertical ? 'ArrowDown' : 'ArrowRight')) next = tabs[(i + 1) % tabs.length];
    else if (event.key === (vertical ? 'ArrowUp' : 'ArrowLeft')) next = tabs[(i - 1 + tabs.length) % tabs.length];
    else if (event.key === 'Home') next = tabs[0];
    else if (event.key === 'End') next = tabs[tabs.length - 1];
    if (!next) return false;
    event.preventDefault();
    selectTab(list, next, {user: true, focus: true});
    return true;
  }

  /* ============================================================
     Filters: pressed-button groups, fields and the address query
     ============================================================ */
  /* GNUI.filters(root, {defaults, onChange, url, immediate}) wires every `[data-filter="key"]`
     inside `root`: a `.gn-seg` of buttons (each `data-value`, else its words; `data-multi` lets
     several be pressed), a search or text input, a select, or a checkbox. The state is kept in
     the address query (`?grid=CVIS&kind=trip`), restored on load, and a key at its default is left
     out. `.gn-clear` shows while any filter differs from its default and resets them all;
     `.gn-filters-count` shows `ctl.count(shown, total)`. `onChange(state, ctl)` follows every
     change the person makes (and the first state, with `immediate: true`). */
  function filters(box, opts) {
    const o = opts || {};
    if (!box) return null;
    const controls = Array.from(box.querySelectorAll('[data-filter]'));
    const valueOf = (button) => (button.hasAttribute('data-value') ? button.getAttribute('data-value') : button.textContent.trim());
    const fields = controls.map((el) => {
      const key = el.getAttribute('data-filter');
      const multi = el.hasAttribute('data-multi');
      let kind = 'seg';
      if (el.matches('input[type="checkbox"]')) kind = 'check';
      else if (el.matches('input, textarea')) kind = 'text';
      else if (el.matches('select')) kind = 'select';
      const buttons = kind === 'seg' ? Array.from(el.querySelectorAll('button')) : [];
      const read = () => {
        if (kind === 'seg') {
          const on = buttons.filter((b) => b.getAttribute('aria-pressed') === 'true').map(valueOf);
          return multi ? on.join(',') : (on[0] != null ? on[0] : '');
        }
        if (kind === 'check') return el.checked ? '1' : '';
        return String(el.value || '').trim();
      };
      const write = (value) => {
        const v = String(value == null ? '' : value);
        if (kind === 'seg') {
          const wanted = multi ? v.split(',').filter(Boolean) : [v];
          let any = false;
          buttons.forEach((b) => { const on = wanted.indexOf(valueOf(b)) >= 0; any = any || on; b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
          return any || (multi && !v);
        }
        if (kind === 'check') { el.checked = v === '1' || v === 'true'; return true; }
        if (kind === 'select' && !Array.from(el.options).some((op) => op.value === v)) return false;
        el.value = v;
        return true;
      };
      buttons.forEach((b) => { if (!b.hasAttribute('aria-pressed')) b.setAttribute('aria-pressed', 'false'); if (!b.type) b.type = 'button'; });
      const initial = read();
      const def = o.defaults && Object.prototype.hasOwnProperty.call(o.defaults, key) ? String(o.defaults[key]) : initial;
      return {el, key, kind, multi, buttons, read, write, def};
    });
    const clearBtn = box.querySelector('.gn-clear');
    const countEl = box.querySelector('.gn-filters-count');
    const useUrl = o.url !== false;
    const get = () => {
      const out = {};
      fields.forEach((f) => { out[f.key] = f.read(); });
      return out;
    };
    const differs = () => fields.filter((f) => f.read() !== f.def);
    const show = () => {
      const changed = differs();
      if (clearBtn) clearBtn.hidden = !changed.length;
      box.querySelectorAll('details.gn-more-filters').forEach((more) => {
        const n = changed.filter((f) => more.contains(f.el)).length;
        const sum = more.querySelector(':scope > summary');
        if (!sum) return;
        if (n) sum.setAttribute('data-active', String(n)); else sum.removeAttribute('data-active');
      });
    };
    const writeUrl = () => {
      if (!useUrl) return;
      try {
        const url = new URL(window.location.href);
        fields.forEach((f) => {
          const v = f.read();
          if (v === f.def || (f.kind === 'text' && !v && !f.def)) url.searchParams.delete(f.key);
          else url.searchParams.set(f.key, v);
        });
        history.replaceState(history.state, '', url.pathname + url.search + url.hash);
      } catch (error) { /* sandboxed */ }
    };
    const ctl = {
      get: get,
      fields: fields,
      defaults: () => { const out = {}; fields.forEach((f) => { out[f.key] = f.def; }); return out; },
      active: () => differs().map((f) => f.key),
      set(partial, setOpts) {
        Object.keys(partial || {}).forEach((key) => fields.filter((f) => f.key === key).forEach((f) => f.write(partial[key])));
        changed(setOpts && setOpts.silent);
      },
      clear(setOpts) {
        fields.forEach((f) => f.write(f.def));
        changed(setOpts && setOpts.silent);
      },
      count(shown, total) {
        if (!countEl) return;
        const fmt = (n) => (typeof n === 'number' ? n.toLocaleString('en-US') : String(n == null ? '' : n));
        countEl.textContent = shown == null ? '' : total == null || shown === total ? fmt(shown) + (o.noun ? ' ' + o.noun : '')
          : fmt(shown) + ' of ' + fmt(total) + (o.noun ? ' ' + o.noun : '');
      },
    };
    function changed(silent) {
      show();
      writeUrl();
      if (!silent && typeof o.onChange === 'function') {
        try { o.onChange(get(), ctl); } catch (error) { if (window.console) console.error(error); }
      }
    }
    /* The address wins over the markup on load: a shared link opens the same view. */
    if (useUrl) {
      let params = null;
      try { params = new URLSearchParams(window.location.search); } catch (error) { params = null; }
      if (params) fields.forEach((f) => { if (params.has(f.key) && !f.write(params.get(f.key))) f.write(f.def); });
    }
    let typing = 0;
    box.addEventListener('click', (event) => {
      const button = closest(event.target, 'button');
      if (!button) return;
      if (button === clearBtn) { ctl.clear(); return; }
      const f = fields.find((x) => x.kind === 'seg' && x.buttons.indexOf(button) >= 0);
      if (!f) return;
      if (f.multi) {
        const on = button.getAttribute('aria-pressed') === 'true';
        button.setAttribute('aria-pressed', on ? 'false' : 'true');
      } else {
        if (button.getAttribute('aria-pressed') === 'true') return;
        f.buttons.forEach((b) => b.setAttribute('aria-pressed', b === button ? 'true' : 'false'));
      }
      changed(false);
    });
    box.addEventListener('input', (event) => {
      const f = fields.find((x) => x.el === event.target && x.kind === 'text');
      if (!f) return;
      clearTimeout(typing);
      typing = setTimeout(() => changed(false), 160);
    });
    box.addEventListener('change', (event) => {
      const f = fields.find((x) => x.el === event.target && (x.kind === 'select' || x.kind === 'check'));
      if (f) changed(false);
    });
    show();
    writeUrl();
    if (o.immediate && typeof o.onChange === 'function') o.onChange(get(), ctl);
    box.gnFilters = ctl;
    return ctl;
  }

  /* `details.gn-more-filters` (and any `details[data-popover]`) close on a click outside or Esc. */
  function closePopovers(except) {
    doc.querySelectorAll('details.gn-more-filters[open], details[data-popover][open]').forEach((d) => { if (d !== except && !d.contains(except)) d.open = false; });
  }

  /* ============================================================
     The preview card: entity previews site-wide, and the command bar's citations
     ============================================================ */
  const KIND_WORD = {plant: 'Plant', event: 'Event', region: 'Region', link: 'HVDC link', notice: 'Notice', dataset: 'Dataset', page: 'Page'};
  const KIND_ALIAS = {grid: 'region', hvdc: 'link'};
  const PREVIEWABLE = ['plant', 'event', 'region', 'link', 'notice', 'dataset'];
  /* Where an entity lives when the server gave no link for it. */
  function defaultHref(kind, id) {
    const key = encodeURIComponent(String(id || ''));
    if (kind === 'plant') return '/plant/' + key;
    if (kind === 'event') return '/event/' + key;
    if (kind === 'dataset') return '/data#' + key;
    if (kind === 'notice') return '/notices';
    if (kind === 'alert') return '/alert/' + key;
    if (kind === 'region' || kind === 'grid') return '/?grid=' + key;
    if (kind === 'link' || kind === 'hvdc') return '/?link=' + key;
    return '';
  }
  function parseEntity(value) {
    const text = String(value || '');
    const i = text.indexOf(':');
    if (i <= 0) return null;
    const raw = text.slice(0, i).toLowerCase();
    const kind = KIND_ALIAS[raw] || raw;
    const id = text.slice(i + 1);
    return id ? {kind: kind, id: id} : null;
  }

  const factValue = (fact) => {
    const v = fact.value;
    if (v === null || v === undefined || v === '') return '<span class="gn-pcard-unk">No data</span>';
    if (typeof v === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(v)) {
      return '<span class="mono">' + esc(hhmm(v)) + '</span> <span class="gn-pcard-unit">' + esc(dayWords(v)) + '</span>';
    }
    /* A word or a name, not a figure: the body face, so a long record name wraps as prose. */
    if (typeof v === 'string' && !/^[-−+]?[\d.,]+$/.test(v.trim())) return '<span class="gn-pcard-text">' + esc(v) + '</span>';
    const shown = typeof v === 'number' ? v.toLocaleString('en-US', {maximumFractionDigits: 1}) : String(v);
    return '<span class="mono">' + esc(shown) + '</span>' + (fact.unit ? ' <span class="gn-pcard-unit">' + esc(fact.unit) + '</span>' : '');
  };
  /* A sparkline from the preview's own series: no axes, a faint median line, an end dot. */
  function sparkSvg(spark) {
    const values = list(spark.v);
    const points = values.map((v, i) => (typeof v === 'number' && isFinite(v) ? [i, v] : null));
    const real = points.filter(Boolean);
    if (real.length < 2) return '<p class="gn-pcard-unk">Too few points to draw.</p>';
    const W = 240;
    const H = 32;
    const lo = Math.min(...real.map((p) => p[1]));
    const hi = Math.max(...real.map((p) => p[1]));
    const span = hi - lo || 1;
    const x = (i) => (values.length > 1 ? (i / (values.length - 1)) * (W - 4) + 2 : W / 2);
    const y = (v) => H - 3 - ((v - lo) / span) * (H - 6);
    let d = '';
    let pen = false;
    points.forEach((p) => {
      if (!p) { pen = false; return; }
      d += (pen ? 'L' : 'M') + x(p[0]).toFixed(1) + ' ' + y(p[1]).toFixed(1);
      pen = true;
    });
    const sorted = real.map((p) => p[1]).sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    const last = real[real.length - 1];
    let tone = 'mid';
    if (/₱/.test(String(spark.unit || ''))) {
      if (last[1] > median * 1.5 && last[1] > median + 1) tone = 'hot';
      else if (last[1] > median * 1.1) tone = 'warm';
      else if (last[1] < median * 0.9) tone = 'cool';
    }
    return '<svg class="gn-pcard-svg" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">'
      + '<path class="base" d="M2 ' + y(median).toFixed(1) + 'H' + (W - 2) + '"/>'
      + '<path class="ln" d="' + d + '"/>'
      + '<path class="end" data-tone="' + tone + '" d="M' + x(last[0]).toFixed(1) + ' ' + y(last[1]).toFixed(1) + 'h0"/></svg>';
  }
  function sparkHtml(spark) {
    const values = list(spark.v).filter((v) => typeof v === 'number' && isFinite(v));
    const last = values.length ? values[values.length - 1] : null;
    const times = list(spark.t);
    const lastT = times.length ? hhmm(times[times.length - 1]) : '';
    return '<div class="gn-pcard-spark"><p class="gn-pcard-spark-l"><span>' + esc(spark.label || '') + '</span>'
      + (last !== null ? '<span class="mono">' + esc(last.toLocaleString('en-US', {maximumFractionDigits: 1}))
        + (spark.unit ? ' <span class="gn-pcard-unit">' + esc(spark.unit) + '</span>' : '')
        + (lastT ? ' <span class="gn-pcard-unit">' + esc(lastT) + '</span>' : '') + '</span>' : '')
      + '</p>' + sparkSvg(spark) + '</div>';
  }
  /* One entity's card, from the desk API's preview answer. */
  function previewHtml(p) {
    const kind = String(p.kind || '');
    const href = safeHref(p.href) || defaultHref(kind, p.id);
    const facts = list(p.facts).filter((f) => f && f.label);
    const sources = list(p.sources).filter((s) => s && (s.title || s.dataset_id));
    return '<p class="gn-pcard-k">' + icon(kind) + '<span>' + esc(KIND_WORD[kind] || kind) + '</span></p>'
      + '<p class="gn-pcard-title" id="gn-pcard-title">' + esc(p.title || p.id) + '</p>'
      + (p.subtitle ? '<p class="gn-pcard-meta">' + esc(p.subtitle) + '</p>' : '')
      + (facts.length ? '<dl class="gn-pcard-facts">' + facts.slice(0, 4).map((f) => '<div><dt>' + esc(f.label)
        + (hhmm(f.at) ? ' <span class="mono">' + esc(hhmm(f.at)) + '</span>' : '') + '</dt><dd>'
        + factValue(f) + '</dd></div>').join('') + '</dl>' : '')
      + list(p.sparks).slice(0, 2).map(sparkHtml).join('')
      + (p.summary ? '<p class="gn-pcard-sum">' + esc(p.summary) + '</p>' : '')
      + (sources.length ? '<p class="gn-pcard-src">Source ' + sources.slice(0, 3).map((s) => {
        const to = safeHref(s.href);
        return to ? '<a href="' + esc(to) + '">' + esc(s.title || s.dataset_id) + '</a>' : esc(s.title || s.dataset_id);
      }).join(', ') + '</p>' : '')
      + (href ? '<div class="gn-pcard-acts"><a class="gn-pcard-open" href="' + esc(href) + '" data-go="1">'
        + 'Open page ' + icon('arrow') + '</a></div>' : '');
  }

  /* The one preview cache: kind/id at the clock. Each entry holds the request, then the answer. */
  const previews = new Map();
  async function getJson(url) {
    try {
      const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      let data = null;
      try { data = await response.json(); } catch (error) { data = null; }
      return {ok: Boolean(response && response.ok), status: response ? response.status : 0, data: data};
    } catch (error) {
      return {ok: false, status: 0, data: null};
    }
  }
  function fetchPreview(kind, id, at) {
    const when = at || asOf();
    const key = kind + '/' + id + '@' + when;
    let entry = previews.get(key);
    if (!entry) {
      entry = {pending: getJson(API + 'preview/' + encodeURIComponent(kind) + '/' + encodeURIComponent(id)
        + (when ? '?at=' + encodeURIComponent(when) : ''))};
      previews.set(key, entry);
      entry.pending.then((answer) => {
        if (answer.ok && answer.data) entry.data = answer.data;
        else previews.delete(key);
      });
    }
    return entry.pending;
  }
  const cachedPreview = (kind, id, at) => { const e = previews.get(kind + '/' + id + '@' + (at || asOf())); return e && e.data ? e.data : null; };

  /* The card element, made on first use. */
  const card = {el: null, anchor: null, pinned: false, key: '', showTimer: 0, hideTimer: 0, prefer: null, sideOf: null};
  function cardEl() {
    if (card.el) return card.el;
    const el = doc.createElement('div');
    el.id = 'gn-pcard';
    el.className = 'gn-pcard';
    el.hidden = true;
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'false');
    doc.body.appendChild(el);
    card.el = el;
    el.addEventListener('mouseenter', () => clearTimeout(card.hideTimer));
    el.addEventListener('mouseleave', (event) => {
      if (card.pinned) return;
      const next = event.relatedTarget;
      if (next && card.anchor && card.anchor.contains(next)) return;
      card.hideTimer = setTimeout(() => hideCard(false), 180);
    });
    /* A press inside an open card pins it, so the reader can use its links. */
    el.addEventListener('pointerdown', () => { if (!card.pinned) { card.pinned = true; el.classList.add('is-pinned'); } });
    el.addEventListener('click', (event) => {
      if (closest(event.target, '.gn-pcard-x')) {
        const anchor = card.anchor;
        hideCard(true);
        if (anchor && typeof anchor.focus === 'function') anchor.focus();
      }
    });
    el.addEventListener('keydown', (event) => {
      if (event.key !== 'Tab' || !card.pinned) return;
      const stops = Array.from(el.querySelectorAll('a[href], button:not([disabled])'));
      if (!stops.length) return;
      const first = stops[0];
      const last = stops[stops.length - 1];
      if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    return el;
  }
  function barBottom() {
    return Math.max(8, parseFloat(getComputedStyle(root).getPropertyValue('--bar-h')) || 8);
  }
  /* Beside a list (`sideOf`, the command bar's results), else above the anchor, else below. */
  function placeCard() {
    const el = card.el;
    const anchor = card.anchor;
    if (!el || !anchor) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    el.style.left = '0px';
    el.style.top = '0px';
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    const r = anchor.getBoundingClientRect();
    const top = barBottom();
    let left = null;
    let y = null;
    if (card.prefer === 'side' && card.sideOf) {
      const box = card.sideOf.getBoundingClientRect();
      if (box.right + 12 + w <= vw - 8) left = box.right + 12;
      else if (box.left - 12 - w >= 8) left = box.left - 12 - w;
      if (left !== null) y = Math.min(Math.max(top, r.top - 12), vh - h - 8);
    }
    if (left === null) {
      left = Math.min(Math.max(8, r.left - 12), vw - w - 8);
      if (card.prefer === 'below') {
        y = r.bottom + 8;
        if (y + h > vh - 8) y = r.top - h - 8;
      } else {
        y = r.top - h - 8;
        if (y < top) y = r.bottom + 8;
      }
      if (y + h > vh - 8) y = Math.max(top, vh - h - 8);
      if (y < top) y = top;
    }
    el.style.left = Math.round(left) + 'px';
    el.style.top = Math.round(y) + 'px';
  }
  /* Opens the card at `anchor` with `html` (already escaped markup). opts: pinned, prefer
     ('side', 'below' or above by default), sideOf (an element to sit beside), label, key. */
  function openCard(anchor, html, opts) {
    const o = opts || {};
    const el = cardEl();
    clearTimeout(card.hideTimer);
    clearTimeout(card.showTimer);
    if (card.anchor && card.anchor !== anchor) card.anchor.removeAttribute('aria-expanded');
    card.anchor = anchor;
    card.pinned = Boolean(o.pinned);
    card.prefer = o.prefer || null;
    card.sideOf = o.sideOf || null;
    if (o.key != null) card.key = o.key;
    el.innerHTML = '<div class="gn-pcard-in">' + html + '</div>' + (card.pinned
      ? '<button type="button" class="gn-pcard-x" aria-label="Close">' + icon('close') + '</button>' : '');
    el.setAttribute('aria-label', o.label || 'Details');
    el.classList.toggle('is-pinned', card.pinned);
    el.hidden = false;
    anchor.setAttribute('aria-expanded', 'true');
    placeCard();
    if (card.pinned && o.focus !== false) {
      const first = el.querySelector('a[href], button');
      if (first) first.focus({preventScroll: true});
    }
    return el;
  }
  function hideCard(force) {
    clearTimeout(card.showTimer);
    if (!card.el || card.el.hidden) { card.anchor = null; return; }
    if (!force && card.pinned) return;
    if (card.anchor) card.anchor.removeAttribute('aria-expanded');
    card.el.hidden = true;
    card.el.innerHTML = '';
    card.anchor = null;
    card.pinned = false;
    card.key = '';
  }
  const cardOpen = () => Boolean(card.el && !card.el.hidden);

  /* An entity's preview at `anchor`: the cached card at once, else a quiet line, then the card. */
  async function preview(anchor, kind, id, opts) {
    const o = Object.assign({}, opts || {});
    const at = asOf();
    const key = 'preview:' + kind + '/' + id + '@' + at;
    const label = (KIND_WORD[kind] || 'Record') + ' preview';
    const title = esc(String(anchor.textContent || id).trim().slice(0, 80));
    const head = '<p class="gn-pcard-k">' + icon(kind) + '<span>' + esc(KIND_WORD[kind] || kind) + '</span></p>';
    const cached = cachedPreview(kind, id, at);
    if (cached) { openCard(anchor, previewHtml(cached), Object.assign(o, {label: label, key: key})); return; }
    openCard(anchor, head + '<p class="gn-pcard-title">' + title + '</p><p class="gn-pcard-quiet">Reading the records.</p>',
      Object.assign({}, o, {label: label, key: key}));
    const answer = await fetchPreview(kind, id, at);
    if (card.key !== key || card.anchor !== anchor) return;
    const href = anchor.getAttribute('href');
    const html = answer.ok && answer.data ? previewHtml(answer.data)
      : head + '<p class="gn-pcard-title">' + title + '</p><p class="gn-pcard-quiet">'
        + (answer.status === 404 ? 'The records hold no preview for this.' : 'The preview did not load.') + '</p>'
        + (href && href !== '#' && safeHref(href) ? '<div class="gn-pcard-acts"><a class="gn-pcard-open" href="' + esc(href)
          + '" data-go="1">Open page ' + icon('arrow') + '</a></div>' : '');
    openCard(anchor, html, Object.assign({}, o, {pinned: card.pinned, label: label, key: key, focus: false}));
  }

  /* Site-wide: any a[data-entity] (and a .gn-entity-info button) previews on hover and focus. */
  const ENTITY = 'a[data-entity], .gn-entity-info[data-entity]';
  const canHover = () => !window.matchMedia || window.matchMedia('(hover: hover)').matches;
  function entityOf(node) {
    const found = parseEntity(node.getAttribute('data-entity'));
    return found && PREVIEWABLE.indexOf(found.kind) >= 0 ? found : null;
  }
  function onEntityOver(event) {
    if (!canHover()) return;
    const anchor = closest(event.target, ENTITY);
    if (!anchor) return;
    clearTimeout(card.hideTimer);
    if (card.anchor === anchor || (card.pinned && cardOpen())) return;
    const ent = entityOf(anchor);
    if (!ent) return;
    clearTimeout(card.showTimer);
    card.showTimer = setTimeout(() => preview(anchor, ent.kind, ent.id, {prefer: anchor.getAttribute('data-preview-at') || null}), 200);
  }
  function onEntityOut(event) {
    const anchor = closest(event.target, ENTITY);
    if (!anchor) return;
    const next = event.relatedTarget;
    if (next && (anchor.contains(next) || (card.el && card.el.contains(next)))) return;
    clearTimeout(card.showTimer);
    if (!card.pinned) card.hideTimer = setTimeout(() => hideCard(false), 180);
  }
  function onEntityFocus(event) {
    const anchor = closest(event.target, ENTITY);
    if (!anchor || (card.pinned && cardOpen()) || card.anchor === anchor) return;
    let keyboard = true;
    try { keyboard = anchor.matches(':focus-visible'); } catch (error) { keyboard = true; }
    if (!keyboard) return;
    const ent = entityOf(anchor);
    if (!ent) return;
    clearTimeout(card.showTimer);
    card.showTimer = setTimeout(() => preview(anchor, ent.kind, ent.id, {}), 200);
  }
  function onEntityBlur(event) {
    const anchor = closest(event.target, ENTITY);
    if (!anchor) return;
    clearTimeout(card.showTimer);
    const next = event.relatedTarget;
    if (next && card.el && card.el.contains(next)) return;
    if (!card.pinned && card.anchor === anchor) hideCard(false);
  }
  /* The info button pins the card; a long press does the same on a touch screen. */
  let press = {timer: 0, fired: false};
  function onEntityInfo(event) {
    const info = closest(event.target, '.gn-entity-info[data-entity]');
    if (info) {
      event.preventDefault();
      const ent = entityOf(info);
      if (!ent) return;
      if (card.anchor === info && card.pinned) hideCard(true);
      else preview(info, ent.kind, ent.id, {pinned: true, prefer: 'below'});
      return;
    }
    if (press.fired && closest(event.target, 'a[data-entity]')) {
      press.fired = false;
      event.preventDefault();
    }
  }
  function onPressStart(event) {
    if (event.pointerType !== 'touch') return;
    const anchor = closest(event.target, 'a[data-entity]');
    if (!anchor) return;
    const ent = entityOf(anchor);
    if (!ent) return;
    press.fired = false;
    clearTimeout(press.timer);
    press.timer = setTimeout(() => { press.fired = true; preview(anchor, ent.kind, ent.id, {pinned: true, prefer: 'below'}); }, 480);
  }
  const onPressEnd = () => clearTimeout(press.timer);

  /* ============================================================
     The document's listeners and the enhancement pass
     ============================================================ */
  doc.addEventListener('click', (event) => {
    onMenuClick(event);
    onSortClick(event);
    onExpand(event);
    onTabClick(event);
    onEntityInfo(event);
    onRowClick(event);
    const more = closest(event.target, 'details.gn-more-filters, details[data-popover]');
    closePopovers(more);
  });
  doc.addEventListener('auxclick', onRowAux);
  doc.addEventListener('keydown', (event) => {
    if (onMenuKey(event)) return;
    if (onTabKey(event)) return;
    if (event.key === 'Enter' && !event.defaultPrevented) {
      const tr = event.target && event.target.matches && event.target.matches('tr[data-href]') ? event.target : null;
      if (tr) { event.preventDefault(); openRow(tr, event.metaKey || event.ctrlKey); return; }
    }
    if (event.key === 'Escape') {
      if (cardOpen()) {
        const anchor = card.anchor;
        hideCard(true);
        if (anchor && typeof anchor.focus === 'function' && (anchor.matches(ENTITY) || card.el.contains(doc.activeElement) || doc.activeElement === doc.body)) anchor.focus();
        event.preventDefault();
        return;
      }
      if (openMenu) { closeMenu(true); event.preventDefault(); return; }
      const open = doc.querySelector('details.gn-more-filters[open], details[data-popover][open]');
      if (open) { open.open = false; const sum = open.querySelector('summary'); if (sum) sum.focus(); event.preventDefault(); }
    }
  });
  doc.addEventListener('pointerdown', (event) => {
    const target = event.target;
    if (openMenu && !openMenu.menu.contains(target) && !openMenu.button.contains(target)) closeMenu(false);
    if (cardOpen() && !card.el.contains(target) && !(card.anchor && card.anchor.contains(target))
        && !closest(target, '[data-card-anchor]')) hideCard(true);
    onPressStart(event);
  });
  doc.addEventListener('pointerup', onPressEnd);
  doc.addEventListener('pointercancel', onPressEnd);
  doc.addEventListener('mouseover', onEntityOver);
  doc.addEventListener('mouseout', onEntityOut);
  doc.addEventListener('focusin', onEntityFocus);
  doc.addEventListener('focusout', onEntityBlur);
  window.addEventListener('scroll', () => {
    queueStuck();
    if (openMenu) placeMenu(openMenu.button, openMenu.menu);
    if (cardOpen() && !card.pinned) hideCard(true);
    else if (cardOpen()) placeCard();
  }, {passive: true, capture: true});
  window.addEventListener('resize', () => {
    queueStuck();
    if (openMenu) closeMenu(false);
    if (cardOpen()) hideCard(true);
  });
  window.addEventListener('hashchange', () => {
    const tabs = hashTabs();
    doc.querySelectorAll('[data-tabs]').forEach((list) => {
      const want = tabs[list.getAttribute('data-tabs')];
      if (want) selectTab(list, want, {});
    });
  });

  /* Enhances what needs markup changes (sort buttons, focusable rows, tab state) under `scope`. */
  function enhance(scope) {
    const base = scope && scope.querySelectorAll ? scope : doc;
    const each = (sel, fn) => {
      if (base.matches && base.matches(sel)) fn(base);
      base.querySelectorAll(sel).forEach(fn);
    };
    each('table[data-sortable]', enhanceTable);
    each('[data-tabs]', enhanceTabs);
    enhanceRows(base);
    queueStuck();
  }

  /* Content drawn after load: enhanced on the next frame; a sortable table whose rows a page
     redrew keeps its active sort. */
  let observer = null;
  const pending = new Set();
  let frame = 0;
  function flush() {
    frame = 0;
    const items = Array.from(pending);
    pending.clear();
    items.forEach((item) => {
      if (item.resort) { if (item.node.isConnected && !selfSorting.has(item.node)) resort(item.node); return; }
      if (item.node.isConnected) enhance(item.node);
    });
  }
  function watch() {
    if (observer || typeof MutationObserver !== 'function' || !doc.body) return;
    observer = new MutationObserver((records) => {
      records.forEach((record) => {
        record.addedNodes.forEach((node) => {
          if (node.nodeType !== 1) return;
          if (node.matches('table[data-sortable], [data-tabs], tr[data-href]') || node.querySelector('table[data-sortable], [data-tabs], tr[data-href]')) {
            pending.add({node: node});
          }
        });
        const tbody = record.target && record.target.nodeName === 'TBODY' ? record.target : null;
        const table = tbody && tbody.parentNode;
        if (table && table.matches && table.matches('table[data-sortable]') && !selfSorting.has(table)
            && record.addedNodes.length && table.querySelector('th[aria-sort="ascending"], th[aria-sort="descending"]')) {
          const already = Array.from(pending).some((item) => item.resort && item.node === table);
          if (!already) pending.add({node: table, resort: true});
        }
      });
      if (pending.size && !frame) frame = window.requestAnimationFrame(flush);
    });
    observer.observe(doc.body, {childList: true, subtree: true});
  }

  /* ---------- public surface ---------- */
  Object.assign(G, {
    version: 1,
    esc: esc,
    icon: icon,
    safeHref: safeHref,
    defaultHref: defaultHref,
    parseEntity: parseEntity,
    badge: badge,
    badgeHtml: badgeHtml,
    kindWords: KIND_BADGE,
    sort: sort,
    resort: resort,
    enhance: enhance,
    filters: filters,
    selectTab: (listOrName, key) => {
      const list = typeof listOrName === 'string' ? doc.querySelector('[data-tabs="' + listOrName + '"]') : listOrName;
      if (list) { enhanceTabs(list); selectTab(list, key, {user: true}); }
    },
    openMenu: (button) => showMenu(button, false),
    closeMenu: () => closeMenu(false),
    /* The preview card, shared with the command bar. */
    previewHtml: previewHtml,
    fetchPreview: fetchPreview,
    preview: preview,
    previewable: (kind) => PREVIEWABLE.indexOf(KIND_ALIAS[kind] || kind) >= 0,
    card: {
      open: openCard,
      hide: hideCard,
      place: placeCard,
      isOpen: cardOpen,
      state: card,
      get el() { return cardEl(); },
    },
  });

  function start() {
    enhance(doc);
    watch();
    if (typeof G._resolve === 'function') { G._resolve(G); delete G._resolve; }
    else if (!G.ready) G.ready = Promise.resolve(G);
  }
  if (!G.ready) {
    let done = null;
    G.ready = new Promise((resolve) => { done = resolve; });
    G._resolve = done;
  }
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
