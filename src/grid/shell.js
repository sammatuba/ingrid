/* InGRID shell (ericka-desk slice 1): the one top bar, theme, replay clock and live strip
   shared by every page.

   UX-4: the bar's second row is a sectioned live strip at the shared clock (prices with
   sparklines, HVDC congestion, alerts and notices), and the replay sits behind a compact "As of"
   control. The desk (`<body data-replay="page">`) keeps its own replay inside its map, so there
   the bar shows the time only and adopts no clock.

   Loaded in <head> without `defer`, so the theme is set before the first paint (no flash). The
   rest waits for the DOM. The page's own static `<nav class="sites">` stays in the markup as the
   no-script fallback; this script rebuilds it into the main links plus a "More" menu.

   The replay clock ("as of") is shared by every page: `?at=YYYY-MM-DDTHH:MM` in the URL wins, then
   the stored value, then the default. Every view filters its records to times at or before it.
   The span is the bake's own (`replay.json`: first and last interval, the days, the missing days,
   the node days and the notice months; replay-year, 18 Oct 2025 on). Until it is read, and for a
   bake without it, the span below is the 21-29 Sep 2026 window the clock started with.
   No library, no network beyond this origin, no inline style (the page policy forbids it). */
(() => {
  'use strict';
  /* The product's name and its assistant's, the only place either is written in the scripts
     (design-system.md, "Renaming the product"). The agent's name reads inside a sentence ("Ask
     Ingrid"), with no leading "the" and no possessive. */
  const BRAND = 'InGRID';
  const AGENT = 'Ingrid';
  const THEME_KEY = 'gn-theme';
  const ASOF_KEY = 'gn-asof';
  /* Mutated in place once replay.json lands, so a page holding `GNShell.span` sees the bake's span. */
  const SPAN = { first: '2026-09-21T00:00', last: '2026-09-29T23:55', days: null, missing: [], nodeDays: null, months: null };
  /* The default as-of stays 21 Sep 2026 13:40, a product rule (the PEDC trip the demo and the
     alerts case open on); clamped into the span when a bake does not carry it. */
  const DEFAULT_ASOF = '2026-09-21T13:40';
  const AT_SHAPE = /^(\d{4})-(\d{2})-(\d{2})T([01]\d|2[0-3]):[0-5]\d$/;
  const AT = { test(t) {
    const m = AT_SHAPE.exec(String(t));
    if (!m) return false;
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
  } };
  let spanKnown = false;  // until replay.json is read (or found absent) a time is held as asked

  const store = {
    get(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ } },
  };

  // ---------- theme: dark by default, remembered ----------
  const root = document.documentElement;
  const savedTheme = store.get(THEME_KEY);
  root.dataset.theme = savedTheme === 'light' ? 'light' : 'dark';
  /* SHELL-1: the shell runs, so shell.css hides each page's own static bar from the first paint;
     the one bar below replaces it on every page. */
  root.classList.add('gn-shell');
  /* The sign-in screen (app design, screen 0): until the server says whether sign-in is on, a
     returning user (the `gn-signed` hint) sees nothing rather than a flash of the sign-in screen,
     and anyone else sees that screen at once. */
  const SIGNED_HINT = 'gn-signed';
  root.classList.add(store.get(SIGNED_HINT) === '1' ? 'gn-gate-wait' : 'gn-gate-early');
  const themeListeners = [];
  function setTheme(theme) {
    root.dataset.theme = theme === 'light' ? 'light' : 'dark';
    store.set(THEME_KEY, root.dataset.theme);
    themeListeners.forEach((fn) => { try { fn(root.dataset.theme); } catch (e) { /* a listener's own fault */ } });
  }

  // ---------- the shared replay clock ----------
  const clamp = (t) => (!spanKnown ? t : t < SPAN.first ? SPAN.first : t > SPAN.last ? SPAN.last : t);
  function initialAsOf() {
    let fromUrl = null;
    try { fromUrl = new URLSearchParams(window.location.search).get('at'); } catch (e) { fromUrl = null; }
    if (fromUrl && AT.test(fromUrl)) return fromUrl;
    const saved = store.get(ASOF_KEY);
    if (saved && AT.test(saved)) return saved;
    return DEFAULT_ASOF;
  }
  let asOf = initialAsOf();
  const asOfListeners = [];
  function setAsOf(t, quiet) {
    if (!t || !AT.test(t.slice(0, 16))) return;
    const next = clamp(t.slice(0, 16));
    if (next === asOf) return;
    asOf = next;
    store.set(ASOF_KEY, asOf);
    renderAsOf();
    if (!quiet) asOfListeners.forEach((fn) => { try { fn(asOf); } catch (e) { /* a listener's own fault */ } });
  }
  store.set(ASOF_KEY, asOf);

  const stamp = (() => {
    const meta = document.getElementById('nowcast-build');
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + stamp;

  /* Platform polish: the shared component layer. ui.css comes before this file's own sheet (a
     page links it there; one that does not yet gets it here, in the same place), and ui.js, the
     behaviours, loads at once. `GNUI.ready` exists from now on, so a page script can wait on it
     before ui.js has arrived. */
  if (!window.GNUI) {
    let done = null;
    const ready = new Promise((resolve) => { done = resolve; });
    window.GNUI = { ready, _resolve: done };
  }
  (function loadUi() {
    const base = '/grid/' + stamp;
    if (!document.querySelector('link[href$="/ui.css"]')) {
      const css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = base + 'ui.css';
      const shellSheet = document.querySelector('link[href$="/shell.css"]');
      if (shellSheet && shellSheet.parentNode) shellSheet.parentNode.insertBefore(css, shellSheet);
      else document.head.appendChild(css);
    }
    if (!document.querySelector('script[src$="/ui.js"]') && !window.GNUI.version) {
      const js = document.createElement('script');
      js.src = base + 'ui.js';
      js.async = false;
      document.head.appendChild(js);
    }
  })();

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const asOfWords = (t) => `${Number(t.slice(8, 10))} ${MONTHS[Number(t.slice(5, 7)) - 1] || ''} ${t.slice(11, 16)}`;

  // ---------- the menu (platform polish: the information architecture) ----------
  /* Four primary links, then three menus. Each menu item says in one line what it is for. Ask has
     no item of its own: the command bar is the way in, and /ask opens from its sheet. */
  const MAIN = [
    ['/', 'Desk'],
    ['/alerts', 'Alerts'],
    ['/notices', 'Notices'],
    ['/plants', 'Plants'],
  ];
  const GROUPS = [
    { id: 'decisions', label: 'Decisions', items: [
      ['/journal', 'Journal', 'Your decisions and the reasons, entry by entry.'],
      ['/outlooks', 'Outlooks', 'Issued price outlooks set against what happened.'],
      ['/register', 'Assumption register', 'The assumptions behind each position, with their evidence.'],
      ['/book', 'Book', 'Positions and exposure, and the records each rests on.'],
    ] },
    { id: 'evidence', label: 'Evidence', items: [
      ['/data', 'Data catalog', 'Every dataset, its lineage and the pages that read it.'],
      ['/models', 'Models', 'Model records, their runs and how each one scored.'],
    ] },
    { id: 'about', label: 'About', items: [
      ['/paper', 'Research paper', 'The question, the method and the findings in full.'],
      ['/explain', 'How it works', 'A guided tour of the product, chapter by chapter.'],
      ['/work', 'The future of work case', 'How an analyst’s working day changes.'],
      ['/map', 'Project map', 'Every part of the project and how the parts connect.'],
    ] },
  ];
  const SETTINGS = '/settings';

  /* The section a page belongs to: an event, an alert and the alert settings sit under Alerts,
     a plant under Plants. */
  function currentPath() {
    const p = window.location.pathname.replace(/\/+$/, '') || '/';
    if (p.startsWith('/plant/') || p.startsWith('/asset/') || p === '/assets') return '/plants';
    if (p.startsWith('/event/') || p.startsWith('/alert/') || p === SETTINGS) return '/alerts';
    if (p === '/desk') return '/';
    return p;
  }
  /* The words of the current section, for page titles ("Visayas price spike · Alerts · InGRID"). */
  function sectionLabel() {
    const here = currentPath();
    const main = MAIN.find(([href]) => href === here);
    if (main) return main[1];
    for (const g of GROUPS) { const hit = g.items.find(([href]) => href === here); if (hit) return hit[1]; }
    return '';
  }

  function make(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }
  function link(href, label, here) {
    const a = make('a', null, label);
    a.href = href;
    if (href === here) a.setAttribute('aria-current', 'page');
    return a;
  }

  let accountSlot = null;
  let asOfWhen = null;  // the time the As of control (or the desk's label) shows
  let asOfBtn = null;   // the control that opens the replay popover (every page but the desk)
  let deskLink = null;  // "Open the desk at this time" in the popover

  function renderAsOf() {
    if (asOfWhen) { asOfWhen.textContent = asOfWords(asOf); asOfWhen.dateTime = asOf; }
    if (deskLink) deskLink.href = '/?at=' + asOf;
    if (replayShow) replayShow();
  }
  /* The desk keeps its replay inside its own map (UX-3): the bar draws none there. */
  const deskReplay = () => Boolean(document.body && document.body.dataset.replay === 'page');

  /* SHELL-1: the one top bar. Every page used to carry its own copy of the bar (`header.bar`, or
     the plain `div.bar` of the paper and the explainer), each styled by its own stylesheet, so the
     bar changed from page to page. Now the shell builds a fresh `<header id="gn-bar">` as the
     body's first child, as soon as the body exists and before the first paint, from this file's
     own menu. The page's static bar stays in the markup as the no-script fallback; shell.css hides
     it while the shell runs, and `adoptPage` keeps the parts of it a page still needs. */
  let bar = null;
  const SVG = 'http://www.w3.org/2000/svg';
  /* 16px line glyphs (stroke 1.5, currentColor), used only where they carry meaning. */
  const GLYPH = {
    sun: 'M8 5.3a2.7 2.7 0 1 0 0 5.4 2.7 2.7 0 1 0 0-5.4ZM8 1.6v1.3M8 13.1v1.3M1.6 8h1.3M13.1 8h1.3M3.5 3.5l.9.9M11.6 11.6l.9.9M3.5 12.5l.9-.9M11.6 4.4l.9-.9',
    moon: 'M13.4 9.6A5.6 5.6 0 0 1 6.4 2.6a5.6 5.6 0 1 0 7 7Z',
    clock: 'M8 2.2a5.8 5.8 0 1 0 0 11.6A5.8 5.8 0 1 0 8 2.2ZM8 4.8V8l2.2 1.4',
    chevron: 'm4.5 6.5 3.5 3.5 3.5-3.5',
    alert: 'M8 2.3 14.2 13.2H1.8ZM8 6.4v3.2M8 11.4v.1',
    warning: 'M8 1.9 14.1 8 8 14.1 1.9 8Z',
    info: 'M8 2.2a5.8 5.8 0 1 0 0 11.6A5.8 5.8 0 1 0 8 2.2ZM8 7.3v3.9M8 5v.1',
    menu: 'M2.5 4.5h11M2.5 8h11M2.5 11.5h11',
    close: 'm4 4 8 8M12 4l-8 8',
  };
  function glyph(d, cls) {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 16 16');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('class', 'gn-glyph' + (cls ? ' ' + cls : ''));
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', d);
    [['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', '1.5'], ['stroke-linecap', 'round'], ['stroke-linejoin', 'round']]
      .forEach(([k, v]) => path.setAttribute(k, v));
    svg.appendChild(path);
    return svg;
  }
  function brandMark() {
    const a = make('a', 'gn-brand');
    a.href = '/';
    a.setAttribute('aria-label', BRAND + ' home');
    // The InGRID mark (src/grid/ingrid-mark.svg, docs/brand/README.md): a reasoning path through a
    // 3x3 node grid, drawn in currentColor so it follows the theme.
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 32 32');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('class', 'gn-mark');
    svg.setAttribute('fill', 'currentColor');
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', 'M6 6H16V26H26');
    [['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', '4'], ['stroke-linecap', 'round'], ['stroke-linejoin', 'round']]
      .forEach(([k, v]) => path.setAttribute(k, v));
    svg.appendChild(path);
    [[6, 6, 3.5], [26, 26, 4.75], [26, 6, 2.5], [6, 26, 2.5]].forEach(([cx, cy, r]) => {
      const node = document.createElementNS(SVG, 'circle');
      node.setAttribute('cx', cx);
      node.setAttribute('cy', cy);
      node.setAttribute('r', r);
      svg.appendChild(node);
    });
    a.append(svg, make('span', null, BRAND));
    return a;
  }

  /* The bar's height, for anything a page pins under it (the book's label line, the explainer's
     chapter list, a table's sticky header): `--gn-bar-h` and `--bar-h` on the root, kept current. */
  function trackHeight() {
    const set = () => {
      const h = Math.round(bar.getBoundingClientRect().height) + 'px';
      root.style.setProperty('--gn-bar-h', h);
      root.style.setProperty('--bar-h', h);  // the design system's name (ui.css: sticky table headers)
    };
    set();
    if (typeof ResizeObserver === 'function') new ResizeObserver(set).observe(bar);
    else window.addEventListener('resize', set);
  }

  /* One menu of the bar: a button that opens a list of links, each with its line of description.
     It opens on click or the keyboard (Enter, Space, the down arrow), never on hover alone. The
     arrows move through it, the side arrows to the next menu, and Esc or a click outside close it. */
  let openNav = null;  // {button, list}
  function closeNav(focusBack) {
    if (!openNav) return;
    const { button, list } = openNav;
    openNav = null;
    list.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (focusBack) button.focus();
  }
  function navMenu(group, here) {
    const wrap = make('div', 'gn-navgroup');
    const button = make('button', 'gn-navbtn', group.label);
    button.type = 'button';
    button.id = 'gn-nav-' + group.id;
    button.setAttribute('aria-haspopup', 'menu');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-controls', 'gn-navmenu-' + group.id);
    button.appendChild(glyph(GLYPH.chevron, 'gn-navbtn-chev'));
    const list = make('div', 'gn-navmenu');
    list.id = 'gn-navmenu-' + group.id;
    list.setAttribute('role', 'menu');
    list.setAttribute('aria-labelledby', button.id);
    list.hidden = true;
    group.items.forEach(([href, label, desc]) => {
      const a = make('a', 'gn-navitem');
      a.href = href;
      a.setAttribute('role', 'menuitem');
      a.tabIndex = -1;
      a.append(make('span', 'gn-navitem-t', label), make('span', 'gn-navitem-d', desc));
      if (href === here) { a.setAttribute('aria-current', 'page'); button.classList.add('gn-here'); }
      list.appendChild(a);
    });
    const items = () => Array.from(list.querySelectorAll('[role="menuitem"]'));
    const open = (last) => {
      if (openNav && openNav.list !== list) closeNav(false);
      list.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      openNav = { button, list };
      const all = items();
      const target = last ? all[all.length - 1] : all[0];
      if (target) target.focus();
    };
    button.addEventListener('click', () => { if (openNav && openNav.list === list) closeNav(false); else open(false); });
    button.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); open(e.key === 'ArrowUp'); }
    });
    list.addEventListener('keydown', (e) => {
      const all = items();
      const i = all.indexOf(document.activeElement);
      let next = null;
      if (e.key === 'ArrowDown') next = all[(i + 1) % all.length];
      else if (e.key === 'ArrowUp') next = all[(i - 1 + all.length) % all.length];
      else if (e.key === 'Home') next = all[0];
      else if (e.key === 'End') next = all[all.length - 1];
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeNav(true); return; }
      else if (e.key === 'Tab') { closeNav(false); return; }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const menus = Array.from(document.querySelectorAll('#gn-bar .gn-navbtn'));
        const j = menus.indexOf(button);
        const other = menus[(j + (e.key === 'ArrowRight' ? 1 : -1) + menus.length) % menus.length];
        e.preventDefault();
        closeNav(false);
        if (other) { other.focus(); other.click(); }
        return;
      }
      if (next) { e.preventDefault(); next.focus(); }
    });
    wrap.append(button, list);
    return wrap;
  }
  document.addEventListener('click', (e) => { if (openNav && !openNav.button.parentNode.contains(e.target)) closeNav(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && openNav) closeNav(openNav.list.contains(document.activeElement)); });

  /* A modal sheet (the phone menu, the shortcuts): focus moves in and is held there. Esc, the close
     button or a click outside shuts it, and focus goes back to what opened it. */
  let openSheet = null;
  function showSheet(sheet, opener) {
    if (openSheet) hideSheet(false);
    document.body.appendChild(sheet);
    sheet.hidden = false;
    openSheet = { sheet, opener, before: document.activeElement };
    if (opener) opener.setAttribute('aria-expanded', 'true');
    root.classList.add('gn-sheet-open');
    const first = sheet.querySelector('[data-autofocus]') || sheet.querySelector('a[href], button');
    if (first) first.focus();
  }
  function hideSheet(focusBack) {
    if (!openSheet) return;
    const { sheet, opener, before } = openSheet;
    openSheet = null;
    sheet.remove();
    root.classList.remove('gn-sheet-open');
    if (opener) opener.setAttribute('aria-expanded', 'false');
    const back = opener || before;
    if (focusBack && back && back.isConnected && typeof back.focus === 'function') back.focus();
  }
  document.addEventListener('keydown', (e) => {
    if (!openSheet) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); hideSheet(true); return; }
    if (e.key !== 'Tab') return;
    const stops = Array.from(openSheet.sheet.querySelectorAll('a[href], button:not([disabled]), input, select, textarea'))
      .filter((n) => n.getClientRects().length);
    if (!stops.length) return;
    const first = stops[0];
    const last = stops[stops.length - 1];
    if (!openSheet.sheet.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }, true);
  function sheetFrame(cls, title) {
    const sheet = make('div', 'gn-sheet ' + cls);
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    const id = cls + '-title';
    sheet.setAttribute('aria-labelledby', id);
    const panel = make('div', 'gn-sheet-panel');
    const head = make('div', 'gn-sheet-head');
    const h = make('h2', 'gn-sheet-title', title);
    h.id = id;
    const close = make('button', 'gn-sheet-x');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close');
    close.appendChild(glyph(GLYPH.close));
    close.addEventListener('click', () => hideSheet(true));
    head.append(h, close);
    const body = make('div', 'gn-sheet-body');
    panel.append(head, body);
    sheet.appendChild(panel);
    sheet.addEventListener('click', (e) => { if (e.target === sheet) hideSheet(true); });
    return { sheet, body };
  }
  function openNavSheet(opener) {
    const here = currentPath();
    const { sheet, body } = sheetFrame('gn-navsheet', 'Menu');
    const main = make('nav', 'gn-sheet-main');
    main.setAttribute('aria-label', 'Sections');
    MAIN.forEach(([href, label]) => main.appendChild(link(href, label, here)));
    body.appendChild(main);
    GROUPS.forEach((group) => {
      const sec = make('section', 'gn-sheet-group');
      sec.setAttribute('aria-label', group.label);
      sec.appendChild(make('h3', 'gn-sheet-group-h', group.label));
      group.items.forEach(([href, label, desc]) => {
        const a = make('a', 'gn-navitem');
        a.href = href;
        a.append(make('span', 'gn-navitem-t', label), make('span', 'gn-navitem-d', desc));
        if (href === here) a.setAttribute('aria-current', 'page');
        sec.appendChild(a);
      });
      body.appendChild(sec);
    });
    const foot = make('div', 'gn-sheet-foot');
    const settings = make('a', 'gn-sheet-link', 'Settings');
    settings.href = SETTINGS;
    const ask = make('a', 'gn-sheet-link', 'Ask ' + AGENT);
    ask.href = '/ask';
    const keys = make('button', 'gn-sheet-link', 'Shortcuts');
    keys.type = 'button';
    keys.addEventListener('click', () => { hideSheet(false); openKeys(opener); });
    foot.append(settings, ask, keys);
    body.appendChild(foot);
    showSheet(sheet, opener);
  }

  // ---------- keyboard: the shortcuts sheet, go-to keys and the replay steps ----------
  const GOTO = { d: ['/', 'Desk'], a: ['/alerts', 'Alerts'], n: ['/notices', 'Notices'], p: ['/plants', 'Plants'],
    j: ['/journal', 'Journal'], c: ['/data', 'Data catalog'] };
  function keyCap(text) { return make('kbd', 'gn-kbd', text); }
  function openKeys(opener) {
    const { sheet, body } = sheetFrame('gn-keysheet', 'Keyboard shortcuts');
    const rows = [
      [['/'], 'Search or ask ' + AGENT],
      [[MAC_KEYS ? '⌘' : 'Ctrl', 'K'], 'Search or ask, from anywhere'],
      [['?'], 'Show these shortcuts'],
      [['Esc'], 'Close what is open'],
      [['['], 'Replay clock back five minutes'],
      [[']'], 'Replay clock forward five minutes'],
    ];
    Object.keys(GOTO).forEach((k) => rows.push([['g', k], 'Go to ' + GOTO[k][1]]));
    const groups = [['General', rows.slice(0, 4)], ['Replay', rows.slice(4, 6)], ['Go to', rows.slice(6)]];
    groups.forEach(([title, list]) => {
      const sec = make('section', 'gn-keys-group');
      sec.appendChild(make('h3', 'gn-sheet-group-h', title));
      const dl = make('dl', 'gn-keys');
      list.forEach(([keys, words]) => {
        const row = make('div', 'gn-keys-row');
        const dt = make('dt');
        keys.forEach((k, i) => { if (i) dt.appendChild(make('span', 'gn-keys-then', k.length > 1 || keys[0] === 'g' ? 'then' : '+')); dt.appendChild(keyCap(k)); });
        row.append(make('dd', null, words), dt);
        dl.appendChild(row);
      });
      sec.appendChild(dl);
      body.appendChild(sec);
    });
    body.appendChild(make('p', 'gn-keys-note', 'Shortcuts wait while you type in a field.'));
    showSheet(sheet, opener);
  }
  const MAC_KEYS = /Mac|iPhone|iPad/.test(String(navigator.platform || navigator.userAgent || ''));
  let goPending = 0;
  function typing(target) {
    if (!target || target === document.body) return false;
    const tag = String(target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || Boolean(target.isContentEditable)
      || Boolean(target.closest && target.closest('[contenteditable="true"], [role="combobox"], [role="textbox"]'));
  }
  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.isComposing || typing(e.target)) return;
    if (openSheet && e.key !== '?') return;
    const key = e.key;
    if (goPending) {
      const hit = GOTO[key.toLowerCase()];
      clearTimeout(goPending);
      goPending = 0;
      if (hit) { e.preventDefault(); window.location.assign(hit[0] + (hit[0] === '/' ? '' : '')); }
      return;
    }
    if (key === '?') { e.preventDefault(); if (openSheet && openSheet.sheet.classList.contains('gn-keysheet')) hideSheet(true); else openKeys(null); return; }
    if (key === 'g' || key === 'G') { goPending = setTimeout(() => { goPending = 0; }, 1200); return; }
    if ((key === '[' || key === ']') && !deskReplay()) {
      e.preventDefault();
      setAsOf(stepped(asOf, key === ']' ? 1 : -1));
    }
  });

  // ---------- page titles and breadcrumbs ----------
  /* "Visayas price spike · Alerts · InGRID": the page's own words, then its section, then
     the product. `parts` is a string or a list, most specific first. */
  function setTitle(parts) {
    const list = [].concat(parts == null ? [] : parts).map((x) => String(x == null ? '' : x).trim()).filter(Boolean);
    /* The section is left out when the page's words already name it ("Synthetic book" on /book). */
    const sec = sectionLabel();
    if (sec && !list.some((part) => part.toLowerCase().includes(sec.toLowerCase()))) list.push(sec);
    list.push(BRAND);
    document.title = list.join(' · ');
    return document.title;
  }
  /* Breadcrumbs into the page head, for a page without static ones: `[{href, label}, …]`, the
     last entry the current page (its href is ignored). `where` is the head to draw into (by
     default the page's first `.gn-page-head`, else its `main`). */
  function setCrumbs(items, where) {
    const draw = () => {
      const list = [].concat(items || []).filter((x) => x && x.label);
      if (!list.length) return null;
      const head = where || document.querySelector('.gn-page-head') || document.querySelector('main');
      if (!head) return null;
      let nav = head.querySelector(':scope > nav.gn-crumbs');
      if (nav && !nav.hasAttribute('data-shell')) return nav;  // the page's own, static ones
      if (!nav) {
        nav = make('nav', 'gn-crumbs');
        nav.setAttribute('aria-label', 'Breadcrumb');
        nav.setAttribute('data-shell', '');
        head.prepend(nav);
      }
      nav.replaceChildren();
      list.forEach((item, i) => {
        const last = i === list.length - 1;
        if (!last && item.href) { const a = make('a', null, item.label); a.href = item.href; nav.appendChild(a); }
        else { const span = make('span', null, item.label); if (last) span.setAttribute('aria-current', 'page'); nav.appendChild(span); }
      });
      return nav;
    };
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', draw, { once: true }); return null; }
    return draw();
  }

  function buildBar() {
    if (bar || !document.body) return;
    bar = make('header', 'gn-bar');
    bar.id = 'gn-bar';
    const here = currentPath();
    const nav = make('nav', 'gn-nav');
    nav.setAttribute('aria-label', 'Main');
    MAIN.forEach(([href, label]) => nav.appendChild(link(href, label, here)));
    GROUPS.forEach((group) => nav.appendChild(navMenu(group, here)));
    /* A phone gets one Menu button and a full-height sheet with the same groups. */
    const menuBtn = make('button', 'gn-menu-btn');
    menuBtn.type = 'button';
    menuBtn.setAttribute('aria-haspopup', 'dialog');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.append(glyph(GLYPH.menu), make('span', null, 'Menu'));
    menuBtn.addEventListener('click', () => openNavSheet(menuBtn));
    bar.append(brandMark(), nav, menuBtn);

    const tools = make('div', 'gn-tools');

    /* The theme switch is an icon button: a sun in dark mode (to light), a moon in light mode. */
    const toggle = make('button', 'gn-theme gn-icon-btn');
    toggle.type = 'button';
    const label = () => {
      const dark = root.dataset.theme !== 'light';
      const words = dark ? 'Switch to light mode' : 'Switch to dark mode';
      toggle.replaceChildren(glyph(dark ? GLYPH.sun : GLYPH.moon));
      toggle.setAttribute('aria-label', words);
      toggle.setAttribute('aria-pressed', String(!dark));
      toggle.title = words;
    };
    label();
    toggle.addEventListener('click', () => { setTheme(root.dataset.theme === 'light' ? 'dark' : 'light'); label(); });
    tools.appendChild(toggle);

    accountSlot = make('div', 'gn-account');
    const settings = make('a', 'gn-settings', 'Settings');
    settings.href = SETTINGS;
    /* The settings page sits under Alerts in the menu, and its own link is the current one. */
    if ((window.location.pathname.replace(/\/+$/, '') || '/') === SETTINGS) settings.setAttribute('aria-current', 'page');
    accountSlot.appendChild(settings);
    tools.appendChild(accountSlot);
    bar.appendChild(tools);
    renderAccount();
    buildRow2(bar);
    document.body.prepend(bar);
    trackHeight();
  }

  /* After the page is parsed: each static bar loses its section links and brand (the bar above
     carries them), and a static bar left with nothing to show is hidden. A bar that still holds
     page content (the explainer's title and toggles, the paper's draft line) stays as the page's
     own line. The desk (`data-replay="page"`) keeps its clock in its map, so it is never adopted
     there. A page that still carries its clock in its static bar, without that mark, has it moved
     into the bar in place of the As of control (the page's clock is then the replay). */
  function adoptPage() {
    if (!bar) buildBar();
    if (!bar) return;
    const old = Array.from(document.querySelectorAll('header.bar, div.bar')).filter((node) => node !== bar);
    old.forEach((node) => {
      const clock = node.querySelector(':scope > .clock');
      if (clock && !deskReplay() && asOfSlot && asOfBtn) {
        closePop();
        stopReplay();
        asOfSlot.replaceChildren(clock);
        asOfBtn = null; asOfPop = null; asOfWhen = null; deskLink = null; replayShow = null;
      }
      node.querySelectorAll(':scope > nav.sites, :scope > .brand').forEach((part) => part.remove());
      const shown = Array.from(node.children).some((child) => !child.hidden && !child.matches('.grids, script, template'))
        || Array.from(node.childNodes).some((child) => child.nodeType === 3 && child.textContent.trim());
      node.classList.add('gn-page-bar');
      if (!shown) node.hidden = true;
    });
  }

  // ---------- the bar's second row: the live strip at the left, the As of control at the right ----------
  /* Every page: the live strip (prices, HVDC congestion, alerts and notices) at the left; at the
     right the "As of" control, which opens the replay in a small popover. The desk shows the time
     there as a plain label: its replay lives in its map. The row has one fixed height, so the bar
     is the same height on every page. Grid tabs a page puts in its bar are hidden by shell.css:
     grid filters belong to the page, not the top bar. */
  let row2Left = null;
  let asOfSlot = null;   // the row's right end: the As of control, the desk's label, or an adopted clock
  let asOfPop = null;    // the replay popover
  let replayShow = null; // redraws the shell's replay controls (also on a quiet as-of change)
  let stopReplay = () => {};
  function buildRow2(host) {
    const row = make('div', 'gn-row2');
    row2Left = make('div', 'gn-row2-left');
    asOfSlot = make('div', 'gn-row2-right');
    if (deskReplay()) {
      const label = make('span', 'gn-asof gn-asof-static');
      label.title = 'Replay time shared by every page. The replay controls are in the map.';
      label.append(glyph(GLYPH.clock), make('span', 'gn-asof-lead', 'As of'));
      asOfWhen = make('time', 'gn-asof-when mono');
      label.appendChild(asOfWhen);
      asOfSlot.appendChild(label);
    } else {
      asOfSlot.appendChild(buildAsOfControl());
    }
    renderAsOf();
    row.append(row2Left, asOfSlot);
    host.appendChild(row);
  }

  function closePop(focusBack) {
    if (!asOfPop || asOfPop.hidden) return;
    asOfPop.hidden = true;
    asOfBtn.setAttribute('aria-expanded', 'false');
    if (focusBack) asOfBtn.focus();
  }
  /* "As of 21 Sep 13:40": a button that opens the replay controls in a popover under it. The
     popover is not modal: Tab walks into it, Esc or a click outside closes it. */
  function buildAsOfControl() {
    const wrap = make('div', 'gn-asof-wrap');
    asOfBtn = make('button', 'gn-asof');
    asOfBtn.type = 'button';
    asOfBtn.setAttribute('aria-haspopup', 'dialog');
    asOfBtn.setAttribute('aria-expanded', 'false');
    asOfBtn.setAttribute('aria-controls', 'gn-asof-pop');
    asOfBtn.title = 'Replay time shared by every page';
    asOfWhen = make('time', 'gn-asof-when mono');
    asOfBtn.append(glyph(GLYPH.clock), make('span', 'gn-asof-lead', 'As of'), asOfWhen, glyph(GLYPH.chevron, 'gn-asof-chev'));
    asOfPop = make('div', 'gn-asof-pop');
    asOfPop.id = 'gn-asof-pop';
    asOfPop.setAttribute('role', 'dialog');
    asOfPop.setAttribute('aria-label', 'Replay clock');
    asOfPop.hidden = true;
    const head = make('div', 'gn-pop-head');
    head.append(make('span', 'gn-pop-title', 'Replay'), make('span', 'gn-pop-note', 'One clock for every page'));
    deskLink = make('a', 'gn-pop-desk', 'Open the desk at this time');
    deskLink.href = '/?at=' + asOf;
    asOfPop.append(head, buildReplay(), deskLink);
    asOfBtn.addEventListener('click', () => {
      const open = asOfPop.hidden;
      asOfPop.hidden = !open;
      asOfBtn.setAttribute('aria-expanded', String(open));
      if (open) placePop();
    });
    document.addEventListener('click', (e) => { if (asOfPop && !wrap.contains(e.target)) closePop(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && asOfPop && !asOfPop.hidden) closePop(wrap.contains(document.activeElement)); });
    wrap.append(asOfBtn, asOfPop);
    return wrap;
  }
  /* On a phone the popover spans the window under the bar's row (shell.css), placed in JS (CSSOM). */
  function placePop() {
    if (!window.matchMedia('(max-width: 760px)').matches) { asOfPop.style.top = ''; return; }
    asOfPop.style.top = Math.round(asOfBtn.getBoundingClientRect().bottom + 6) + 'px';
  }

  const STEP_MIN = 5;
  const pad = (n) => String(n).padStart(2, '0');
  /* Calendar arithmetic on the day key (UTC dates, Manila civil time is never converted). */
  const dayPlus = (day, n) => {
    const d = new Date(day + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  };
  const minuteOf = (t) => Number(t.slice(11, 13)) * 60 + Number(t.slice(14, 16));
  const atMinute = (day, m) => `${day}T${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
  /* the as-of moved by n five-minute steps, across days, kept inside the span */
  function stepped(t, n) {
    let day = t.slice(0, 10);
    let m = Math.floor(minuteOf(t) / STEP_MIN) * STEP_MIN + n * STEP_MIN;
    while (m < 0) { day = dayPlus(day, -1); m += 1440; }
    while (m >= 1440) { day = dayPlus(day, 1); m -= 1440; }
    return clamp(atMinute(day, m));
  }
  const svgIcon = (d, fill) => {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 16 16');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', d);
    if (fill) path.setAttribute('fill', 'currentColor');
    else { path.setAttribute('fill', 'none'); path.setAttribute('stroke', 'currentColor'); path.setAttribute('stroke-width', '1.6'); }
    svg.appendChild(path);
    return svg;
  };
  /* The replay controls of the popover: the day and the time on the first line, the steps, play
     and the time-of-day slider on the second. */
  function buildReplay() {
    const box = make('div', 'gn-replay');
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', 'Replay controls');
    const btn = (label, icon) => {
      const b = make('button', 'gn-rp-btn');
      b.type = 'button';
      b.setAttribute('aria-label', label);
      b.title = label;
      b.appendChild(icon);
      return b;
    };
    const back = btn('Back five minutes', svgIcon('M10 3 5 8l5 5'));
    const play = btn('Play', svgIcon('M5 3v10l8-5z', true));
    const fwd = btn('Forward five minutes', svgIcon('m6 3 5 5-5 5'));
    /* A date input over the whole span (a year: no list of days). A missing day can be picked;
       the pages say "No data" for it. */
    const day = make('input', 'gn-rp-day mono');
    day.type = 'date';
    day.setAttribute('aria-label', 'Replay day');
    day.required = true;
    const time = make('time', 'gn-rp-time mono');
    const scrub = make('input', 'gn-rp-scrub');
    scrub.type = 'range';
    scrub.min = '0';
    scrub.max = String(1440 / STEP_MIN - 1);
    scrub.step = '1';
    scrub.setAttribute('aria-label', 'Replay time of day');
    let timer = null;
    const stop = () => {
      clearInterval(timer); timer = null;
      play.setAttribute('aria-label', 'Play'); play.title = 'Play';
      play.replaceChildren(svgIcon('M5 3v10l8-5z', true));
      if (asOfBtn) asOfBtn.classList.remove('gn-playing');
    };
    stopReplay = stop;
    const show = () => {
      day.min = SPAN.first.slice(0, 10);
      day.max = SPAN.last.slice(0, 10);
      day.value = asOf.slice(0, 10);
      const gap = SPAN.missing.includes(asOf.slice(0, 10));
      day.title = gap ? 'No data for this day in the company copy' : 'Replay day';
      box.classList.toggle('gn-rp-gap', gap);
      time.textContent = asOf.slice(11, 16) + ' PHT';
      time.dateTime = asOf;
      scrub.value = String(Math.floor(minuteOf(asOf) / STEP_MIN));
    };
    back.addEventListener('click', () => { stop(); setAsOf(stepped(asOf, -1)); });
    fwd.addEventListener('click', () => { stop(); setAsOf(stepped(asOf, 1)); });
    play.addEventListener('click', () => {
      if (timer) { stop(); return; }
      play.setAttribute('aria-label', 'Pause'); play.title = 'Pause';
      play.replaceChildren(svgIcon('M5 3h2v10H5zM9 3h2v10H9z', true));
      if (asOfBtn) asOfBtn.classList.add('gn-playing');
      timer = setInterval(() => {
        const next = stepped(asOf, 1);
        if (next === asOf) { stop(); return; }
        setAsOf(next);
      }, 1500);
    });
    day.addEventListener('change', () => {
      stop();
      if (AT.test(day.value + 'T00:00')) setAsOf(atMinute(day.value, minuteOf(asOf)));
      else show();
    });
    scrub.addEventListener('input', () => { stop(); setAsOf(atMinute(asOf.slice(0, 10), Number(scrub.value) * STEP_MIN)); });
    replayShow = show;
    show();
    const top = make('div', 'gn-rp-line');
    top.append(day, time);
    const steps = make('div', 'gn-rp-line');
    steps.append(back, play, fwd, scrub);
    box.append(top, steps);
    return box;
  }

  // ---------- sign-in (decision D1): one account chip on every page ----------
  // The vendored Firebase SDK is loaded only when the server says sign-in is configured
  // (`/api/alerts/client-config`). Pages stay readable signed out. The alerts page loads the SDK
  // itself and both scripts share the one Firebase app (`firebase.apps.length` first).
  const ASSET = '/grid/' + stamp;
  const auth = { state: 'starting', user: null, handle: null, listeners: [] };
  function usable(user) {
    return Boolean(user && !user.isAnonymous && (user.providerData || []).some((p) => p && (p.providerId === 'google.com' || p.providerId === 'password')));
  }
  function loadScript(name) {
    return new Promise((resolve, reject) => {
      const found = document.querySelector('script[src$="/' + name + '"]');
      if (found && (window.firebase && (name.includes('auth') ? window.firebase.auth : true))) { resolve(); return; }
      const s = document.createElement('script');
      s.src = ASSET + name;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('could not load ' + name));
      document.head.appendChild(s);
    });
  }
  function setAuth(state, user) {
    auth.state = state;
    auth.user = user || null;
    if (state === 'ready') store.set(SIGNED_HINT, auth.user ? '1' : '0');
    renderAccount();
    renderGate();
    auth.listeners.forEach((fn) => { try { fn(auth.user); } catch (e) { /* a listener's own fault */ } });
  }
  /* The sign-in configuration is asked for as soon as this script runs (in the head), not when
     the page is parsed: its answer lifts the sign-in screen, and a page that measures itself
     while that screen still hides it (the desk's map canvas) would measure nothing. One request. */
  let configAsk = null;
  function askConfig() {
    if (!configAsk) {
      configAsk = fetch('/api/alerts/client-config', { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
        .then(async (r) => {
          alertsApi = r.status !== 404;
          return r.ok ? r.json() : (await r.text(), null);  // an unread error body stays pending in Chrome
        })
        .catch(() => null);
    }
    return configAsk;
  }
  async function startAuth() {
    renderGate();
    // A slow sign-in service (a cold server) never leaves a returning user on a blank page.
    setTimeout(() => { if (auth.state === 'starting') { root.classList.replace('gn-gate-wait', 'gn-gate-early'); renderGate(); } }, 6000);
    const cfg = await askConfig();
    loadAlerts();
    if (!cfg || !cfg.apiKey) { setAuth('unavailable'); return; }
    try {
      if (!window.firebase || !window.firebase.auth) {
        await loadScript('firebase-app-compat.js');
        await loadScript('firebase-auth-compat.js');
      }
      const fb = window.firebase;
      const app = fb.apps.length ? fb.app() : fb.initializeApp({ apiKey: cfg.apiKey, authDomain: cfg.authDomain, projectId: cfg.projectId });
      auth.handle = app.auth();
    } catch (e) { setAuth('unavailable'); return; }
    auth.handle.onAuthStateChanged((user) => setAuth('ready', usable(user) ? user : null));
  }
  async function signIn() {
    if (!auth.handle) { window.location.href = '/settings#sign-in'; return; }
    try {
      const provider = new window.firebase.auth.GoogleAuthProvider();
      provider.setCustomParameters({ prompt: 'select_account' });
      await auth.handle.signInWithPopup(provider);
    } catch (e) {
      if (e && e.code === 'auth/popup-closed-by-user') return;
      window.location.href = '/settings#sign-in';
    }
  }
  function signOut() { if (auth.handle) auth.handle.signOut(); }

  // ---------- the sign-in screen: one sign-in for the whole app ----------
  // Covers every page while signed out, wherever sign-in is configured. Where it is not (a local
  // run, a static copy) the pages stay readable, as before. The password is never shown or kept.
  const GATE_ERRORS = {
    'auth/invalid-credential': 'Email or password is wrong.',
    'auth/invalid-login-credentials': 'Email or password is wrong.',
    'auth/wrong-password': 'Email or password is wrong.',
    'auth/user-not-found': 'Email or password is wrong.',
    'auth/invalid-email': 'That email address is not valid.',
    'auth/missing-password': 'Enter the password.',
    'auth/user-disabled': 'This account is turned off.',
    'auth/too-many-requests': 'Too many attempts. Wait a few minutes, then try again.',
    'auth/network-request-failed': 'No connection to the sign-in service. Check the network and try again.',
    'auth/operation-not-allowed': 'This way of signing in is not turned on for this site.',
    'auth/popup-blocked': 'The browser blocked the Google window. Allow pop-ups for this site, then try again.',
  };
  const gateError = (e) => GATE_ERRORS[e && e.code] || 'Sign-in did not complete. Try again.';
  let gate = null;
  function bolt() {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    [['width', '28'], ['height', '28'], ['viewBox', '0 0 24 24'], ['fill', 'none'], ['stroke', 'currentColor'],
      ['stroke-width', '2'], ['stroke-linecap', 'round'], ['stroke-linejoin', 'round'], ['aria-hidden', 'true']]
      .forEach(([k, v]) => svg.setAttribute(k, v));
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M13 2 4 14h7l-1 8 9-12h-7z');
    svg.appendChild(path);
    return svg;
  }
  function field(label, type, auto, id) {
    const wrap = make('label', 'gn-gate-field', label);
    wrap.htmlFor = id;
    const input = make('input');
    input.type = type; input.id = id; input.autocomplete = auto; input.required = true;
    wrap.appendChild(input);
    return { wrap, input };
  }
  function buildGate() {
    const box = make('div', 'gn-gate');
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-labelledby', 'gn-gate-title');
    const form = make('form', 'gn-gate-card');
    form.noValidate = true;
    const brand = make('div', 'gn-gate-brand');
    brand.append(bolt(), make('h1', null, BRAND));
    brand.lastChild.id = 'gn-gate-title';
    const lede = make('p', 'gn-gate-lede', 'One sign-in for the whole app. Your alerts, portfolio and journal stay private to you.');
    const email = field('Email', 'email', 'email', 'gn-gate-email');
    const pw = field('Password', 'password', 'current-password', 'gn-gate-password');
    const status = make('p', 'gn-gate-status');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    const submit = make('button', 'gn-gate-primary', 'Sign in');
    submit.type = 'submit';
    const or = make('div', 'gn-gate-or', 'or');
    const google = make('button', 'gn-gate-google', 'Continue with Google');
    google.type = 'button';
    const forgot = make('button', 'gn-gate-link', 'Forgot password?');
    forgot.type = 'button';
    // Google sign-in is not used by the desk: the card offers email and password only.
    form.append(brand, lede, email.wrap, pw.wrap, status, submit, forgot);
    box.appendChild(form);
    const say = (text, bad) => { status.textContent = text; status.classList.toggle('gn-gate-bad', Boolean(bad)); };
    const busy = (on) => { [submit, google, forgot].forEach((b) => { b.disabled = on || !auth.handle; }); };
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const address = email.input.value.trim();
      const secret = pw.input.value;
      pw.input.value = '';  // emptied on every submit, before any early return
      if (!auth.handle) return;
      if (!address || !secret) { say('Enter the email and the password.', true); return; }
      busy(true); say('Signing in…');
      try { await auth.handle.signInWithEmailAndPassword(address, secret); say(''); }
      catch (e) { say(gateError(e), true); }
      finally { busy(false); }
    });
    google.addEventListener('click', async () => {
      if (!auth.handle) return;
      busy(true); say('');
      try {
        const provider = new window.firebase.auth.GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });
        await auth.handle.signInWithPopup(provider);
      } catch (e) {
        if (!(e && (e.code === 'auth/popup-closed-by-user' || e.code === 'auth/cancelled-popup-request'))) say(gateError(e), true);
      } finally { busy(false); }
    });
    forgot.addEventListener('click', async () => {
      const address = email.input.value.trim();
      if (!address) { say('Enter your email above, then choose Forgot password again.', true); email.input.focus(); return; }
      if (!auth.handle) return;
      busy(true);
      try {
        await auth.handle.sendPasswordResetEmail(address);
        say('If that address has an account, a reset link is on its way.');
      } catch (e) {
        if (e && e.code === 'auth/user-not-found') say('If that address has an account, a reset link is on its way.');
        else say(gateError(e), true);
      } finally { busy(false); }
    });
    gate = { box, say, busy, email: email.input };
    return box;
  }
  function renderGate() {
    if (!document.body) return;
    const locked = auth.state === 'ready' ? !auth.user : auth.state === 'starting' && !root.classList.contains('gn-gate-wait');
    if (auth.state !== 'starting') root.classList.remove('gn-gate-wait', 'gn-gate-early');
    root.classList.toggle('gn-gated', locked);
    if (!locked) {
      if (gate) { gate.box.remove(); gate = null; }
      return;
    }
    const fresh = !gate;
    if (fresh) document.body.appendChild(buildGate());
    gate.busy(auth.state !== 'ready');
    if (auth.state === 'starting') gate.say('Checking sign-in…');
    else if (gate.box.querySelector('.gn-gate-status').textContent === 'Checking sign-in…') gate.say('');
    if (fresh || auth.state === 'ready') { try { gate.email.focus({ preventScroll: true }); } catch (e) { /* older browsers */ } }
  }

  function renderAccount() {
    if (!accountSlot) return;
    accountSlot.querySelectorAll('.gn-acct').forEach((n) => n.remove());
    const settings = accountSlot.querySelector('.gn-settings');
    const add = (node) => { node.classList.add('gn-acct'); accountSlot.insertBefore(node, settings); };
    if (auth.state === 'starting') return;
    if (auth.state === 'unavailable') {
      const note = make('span', 'gn-user gn-muted', 'Sign-in off');
      note.title = 'Sign-in is not configured on this server. Pages stay readable.';
      add(note);
      return;
    }
    if (auth.user) {
      const who = make('span', 'gn-user', auth.user.email || auth.user.displayName || 'Signed in');
      who.title = 'Signed in as ' + (auth.user.email || 'this account');
      add(who);
      const out = make('button', null, 'Sign out');
      out.type = 'button';
      out.addEventListener('click', signOut);
      add(out);
      return;
    }
    const menu = make('details', 'gn-signin');
    const sum = make('summary', null, 'Sign in');
    menu.appendChild(sum);
    const box = make('div', 'gn-menu gn-menu-right');
    const google = make('button', 'gn-menu-item', 'Continue with Google');
    google.type = 'button';
    google.addEventListener('click', () => { menu.open = false; signIn(); });
    const email = make('a', 'gn-menu-item', 'Email and password');
    email.href = '/settings#sign-in';
    box.append(email);
    menu.appendChild(box);
    document.addEventListener('click', (e) => { if (!menu.contains(e.target)) menu.open = false; });
    add(menu);
  }

  // ---------- notices and alerts, as the strip reads them ----------
  const KIND = { trip: 'Trip', online: 'Back online', red: 'Red alert', yellow: 'Yellow alert', mld: 'Load drop', derate: 'Derate', notice: 'Notice' };
  // Notice text can name a plant's technology ("... SOLAR", "... HEPP"); those words are withheld,
  // the same list and marker as asset.js.
  const TECH_WORDS = new RegExp('\\b(?:geo-?thermal\\w*|thermal|solar|photo-?voltaic|pv|hydro\\w*|hepp?|coal(?:-fired)?|diesel|bunker|fuel|oil|gas|lng|ccgt|combined[- ]cycle|wind|biomass|bio\\w*|battery|bess|nuclear|pumped[- ]storage|steam|hfo|cfpp|[dgsw]ppi?)\\b', 'gi');
  const withheld = (s) => String(s == null ? '' : s).replace(TECH_WORDS, '[…]').replace(/\[…\](?:[\s-]*\[…\])+/g, '[…]');
  const opText = (s) => withheld(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');
  const GRID = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  /* A record's time as the clock's key: the bake writes `2026-09-21T13:40` (an older bake
     `2026-09-21 13:40:00`); both read as `2026-09-21T13:40`. */
  const tkey = (t) => { const s = String(t == null ? '' : t); return s.length >= 16 ? s.slice(0, 10) + 'T' + s.slice(11, 16) : s; };
  const minutesAt = (t) => Date.parse(tkey(t) + ':00Z') / 60000;
  /* Severity, shared with the map and the desk API (desk-api.md): an advisory's kind, an event
     takes its advisory's, and an inbox price alert's own severity. */
  const SEVERITY = { red: 'alert', trip: 'alert', yellow: 'warning', mld: 'warning', derate: 'warning', online: 'info', notice: 'info' };
  const ALERT_SEVERITY = { extreme: 'alert', high: 'alert', medium: 'warning', low: 'info' };
  const severityOf = (kind) => {
    const k = String(kind || '');
    if (k.startsWith('alert-')) return ALERT_SEVERITY[k.slice(6)] || 'warning';
    return SEVERITY[k] || 'info';
  };
  let tickerData = null;
  const extraItems = [];

  /* The newest notices, events and alerts up to the strip's clock, newest first. */
  function tickerItems(at) {
    if (!tickerData && !extraItems.length && !alertItems.length) return [];
    const cut = at || asOf;
    const eventsBy = new Map(((tickerData && tickerData.events) || []).map((e) => [e.advisory, e]));
    const rows = ((tickerData && tickerData.advisories) || []).filter((a) => tkey(a.t) <= cut).slice(-40).map((a) => {
      const ev = eventsBy.get(a.id);
      return {
        t: tkey(a.t), kind: a.kind, label: KIND[a.kind] || 'Notice', grid: GRID[a.grid] || a.grid || '',
        text: ev && ev.title ? opText(ev.title) : opText(a.text),
        href: ev ? '/event/' + encodeURIComponent(ev.id) : '/notices?at=' + tkey(a.t) + '#adv-' + encodeURIComponent(a.id),
      };
    });
    // DM-5: alert items read at a later clock than this one are withheld (they carry the alert's
    // later peak price); items read at an earlier clock state nothing after this cutoff.
    const alerts = alertItemsAt !== null && alertItemsAt <= asOf ? alertItems : [];
    return extraItems.concat(alerts).map((x) => Object.assign({}, x, { t: tkey(x.t) })).filter((x) => x.t <= cut)
      .concat(rows).sort((a, b) => (a.t < b.t ? 1 : a.t > b.t ? -1 : 0));
  }

  // ---------- the alert inbox: one reader for the whole page (PERF-6) ----------
  /* `inbox(at, {view, user, fresh})` resolves to the inbox answer up to the clock
     (`/api/alerts/inbox?view=<view>&at=<at>`, the signed-in token along), or rejects with the
     server's own message (`status`, `code` and `field` on the error). The ticker, the dashboard's
     alerts, the event desk and the alerts list all read it here: asks for the same query and user
     share one request, an answer is kept for a minute and a failure is never kept. The server
     reads no view as `all`, so every reader of the whole inbox sends `view=all`. `fresh` asks
     again (after the reader saved something). */
  const INBOX_KEEP_MS = 60000;
  const INBOX_KEEP = 12;
  const inboxCache = new Map();
  function inbox(at, opts) {
    const o = opts || {};
    const user = o.user === undefined ? auth.user : o.user;
    const q = 'view=' + encodeURIComponent(o.view || 'all') + (at ? '&at=' + encodeURIComponent(String(at).slice(0, 16)) : '');
    const key = q + '|' + (user && user.uid ? user.uid : '');
    const hit = inboxCache.get(key);
    if (hit && !o.fresh && Date.now() - hit.t < INBOX_KEEP_MS) return hit.answer;
    const entry = { t: Date.now(), answer: null };
    entry.answer = (async () => {
      const headers = { Accept: 'application/json' };
      if (user) {
        try { headers.Authorization = 'Bearer ' + await user.getIdToken(); } catch (e) { entry.signedOut = true; }
      }
      const r = await fetch('/api/alerts/inbox?' + q, { headers, credentials: 'same-origin' });
      let data = null;
      try { data = await r.json(); } catch (e) { data = null; }  // the body is read either way (Chrome keeps an unread one pending)
      if (!r.ok) {
        const message = (data && (data.message || data.reason || data.code)) || `The server answered ${r.status}.`;
        const err = new Error(typeof message === 'string' ? message : JSON.stringify(message));
        err.status = r.status;
        err.code = data && data.code;
        err.field = data && data.field;
        throw err;
      }
      return data;
    })();
    inboxCache.delete(key);
    inboxCache.set(key, entry);
    while (inboxCache.size > INBOX_KEEP) inboxCache.delete(inboxCache.keys().next().value);
    const forget = () => { if (inboxCache.get(key) === entry) inboxCache.delete(key); };
    entry.answer.then((data) => { if (data === null || entry.signedOut) forget(); }, forget);
    return entry.answer;
  }
  /* When the readers ask again: 400 ms after the clock moves (as each reader waited before), and
     while it plays (the dashboard's clock ticks every 450 ms, this bar's every 1.5 s) at most once
     every 2.5 s. A read that is already due takes the clock as it then stands, so the last read is
     always the time where the clock stopped. */
  const INBOX_SETTLE_MS = 400;
  const INBOX_EVERY_MS = 2500;
  const inboxListeners = [];
  let inboxTimer = null;
  let inboxLast = -Infinity;
  function inboxDue() {
    inboxTimer = null;
    inboxLast = Date.now();
    inboxListeners.forEach((fn) => { try { fn(asOf); } catch (e) { /* a listener's own fault */ } });
  }
  asOfListeners.push(() => {
    if (inboxTimer) return;
    inboxTimer = setTimeout(inboxDue, Math.max(INBOX_SETTLE_MS, inboxLast + INBOX_EVERY_MS - Date.now()));
  });


  // ---------- alerts in the strip (ericka-desk E21) ----------
  // The alert inbox up to the as-of clock (the shared `inbox` above, PERF-6), newest six. Asked only
  // where the alerts API answers (its client-config was not a 404), so a static copy of a page asks nothing.
  const alertItems = [];
  let alertItemsAt = null;  // DM-5: the clock the alert items were read at
  let alertsApi = false;
  const SAFE_HREF = /^\/(event\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}|\?at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}|alerts\?alert=[0-9a-f]{8,64})$/;
  const ALERT_LABEL = { extreme: 'Extreme alert', high: 'High alert', medium: 'Alert', low: 'Low alert' };
  const money = (v) => (typeof v === 'number' && Number.isFinite(v) ? Math.round(v).toLocaleString('en-US') + ' PHP/MWh' : '');
  function alertItemsFrom(inbox) {
    const out = [];
    ((inbox && inbox.groups) || []).forEach((g) => (g.alerts || []).forEach((a) => {
      const t = String(a.first || a.interval_manila || '');
      if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(t)) return;
      const sev = String(a.severity || '').toLowerCase();
      const what = a.direction === 'collapse' ? 'Price collapse' : 'Price spike';
      out.push({
        t, kind: 'alert-' + (ALERT_LABEL[sev] ? sev : 'medium'), label: ALERT_LABEL[sev] || 'Alert',
        grid: GRID[a.region] || a.region || '',
        text: `${what} ${money(a.price_php_mwh)}${a.cause && a.cause.title ? ' · ' + a.cause.title : ''}`,
        href: SAFE_HREF.test(a.href || '') ? a.href : '/alerts',
      });
    }));
    return out.sort((a, b) => (a.t < b.t ? 1 : -1)).slice(0, 6);
  }
  async function loadAlerts(fresh) {
    if (!alertsApi || !stripOn()) return;
    const at = asOf;
    let answer = null;
    try { answer = await inbox(at, { fresh: fresh === true }); } catch (e) { answer = null; }
    if (at !== asOf) return;  // the clock moved on; the newer request fills the strip
    alertItems.length = 0;
    alertItems.push(...alertItemsFrom(answer));
    alertItemsAt = at;
    renderStrip();
  }
  inboxListeners.push(() => loadAlerts());

  // ---------- the live strip (UX-4): prices, HVDC congestion, alerts and notices ----------
  /* Three sections at the strip's clock, split by hairline rules:
     - Prices: each grid's median price (₱/MWh), its change against the usual price of the hour
       (or against an hour before when the usual is unknown), a six-hour sparkline ending in a
       dot in the price colour, and a cue at the offer cap or with reserves short.
     - HVDC: each link's flow and direction, and how long it has been congested.
     - Alerts and notices: counts by severity over the last six hours, and the newest items, one
       line at a time (a calm crossfade every six seconds, held on hover or focus, none with
       reduced motion), with "View all".
     The figures come from the day files the desk reads (`GNShell.dayFile`, cached per day, about
     12 kB gzipped). A bake without day files has only the whole-window `regions.json` and
     `hvdc.json`: the strip reads them on the desk, from the page's own copy (`GridDesk.D`), and
     asks for nothing more anywhere (they can be a year long); other pages then say "No data".
     Unknown stays "No data". A page with `<body data-ticker="off">` gets no strip and asks for
     nothing. */
  const CAP = 32000;
  const STRIP_GRIDS = [['CLUZ', 'Luzon', 'LUZ'], ['CVIS', 'Visayas', 'VIS'], ['CMIN', 'Mindanao', 'MIN']];
  // flow sign: positive = the first grid in the name to the second
  const STRIP_LINKS = [
    ['VISLUZ1', 'Leyte–Luzon', 'LEY–LUZ', 'Visayas', 'Luzon'],
    ['MINVIS1', 'Mindanao–Visayas', 'MIN–VIS', 'Mindanao', 'Visayas'],
  ];
  const SPARK_STEPS = 72;  // six hours of five-minute intervals
  const WINDOW_MIN = 360;
  const CYCLE_MS = 6000;
  const SHOWN_ITEMS = 5;
  const stripOn = () => Boolean(document.body) && document.body.dataset.ticker !== 'off';
  const fmt = (v) => Math.round(v).toLocaleString('en-US');
  const hhmm = (t) => t.slice(11, 16);
  const durWords = (min) => (min >= 60 ? `${Math.floor(min / 60)}h${min % 60 ? ' ' + (min % 60) + 'm' : ''}` : `${min}m`);
  const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
  const flag = (v) => (v == null ? null : v === true || v === 1 || v === 'Y' || v === 'y' ? true
    : v === false || v === 0 || v === 'N' || v === 'n' ? false : null);

  /* The price colour (design brief): below the usual is cool (--p0/--p1), about the usual is
     neutral (--p2), above is warm through to the cap (--p3/--p4). Returns the token's class
     suffix; the same stops colour the map's and the state card's dots. */
  function priceTone(v, usual) {
    if (num(v) == null) return 'pn';
    if (v >= CAP * 0.97) return 'p4';
    if (num(usual) == null || usual <= 0) return 'p2';
    const r = v / usual;
    return r < 0.75 ? 'p0' : r < 0.92 ? 'p1' : r <= 1.1 ? 'p2' : r < 1.6 ? 'p3' : 'p4';
  }

  /* The strip's source for one clock day: the grids' and the links' series by time key, and the
     usual table. The day before is read too when the clock is inside the first six hours. */
  const stripSources = new Map();
  let deskSeries = null;
  function onDesk() { return Boolean(document.querySelector('script[src$="/grid.js"]')); }
  function legacySeries() {
    if (!deskSeries) {
      deskSeries = onDesk()
        ? new Promise((resolve) => {
          const take = () => { const G = window.GridDesk; resolve(G && G.D && G.D.regions ? { regions: G.D.regions, hvdc: G.D.hvdc } : null); };
          if (window.GridDesk && window.GridDesk.D) { take(); return; }
          window.addEventListener('grid-desk-ready', take, { once: true });
          setTimeout(() => resolve(null), 20000);
        })
        : Promise.resolve(null);
    }
    return deskSeries;
  }
  function indexParts(parts) {
    const grids = new Map(), links = new Map();
    parts.forEach((p) => {
      (p.t || []).forEach((t, i) => grids.set(tkey(t), [p.grids || {}, i]));
      (p.lt || p.t || []).forEach((t, i) => links.set(tkey(t), [p.links || {}, i]));
    });
    return { grids, links };
  }
  function stripSource(at) {
    const day = at.slice(0, 10);
    const early = minuteOf(at) < WINDOW_MIN;
    const key = day + (early ? '+' : '');
    if (!stripSources.has(key)) {
      stripSources.set(key, ready.then(async (index) => {
        if (index) {
          const days = early ? [dayPlus(day, -1), day] : [day];
          const files = await Promise.all(days.map((d) => dayFile(d)));
          const cur = files[files.length - 1];
          if (!cur) return null;
          const src = indexParts(files.filter(Boolean));
          src.usual = cur.usual || null;
          return src;
        }
        const got = await legacySeries();
        if (!got || !got.regions || !Array.isArray(got.regions.t)) return null;
        const hv = got.hvdc || {};
        const src = indexParts([{ t: got.regions.t, grids: got.regions.grids, lt: hv.t || got.regions.t, links: hv.links }]);
        src.usual = null;
        src.whole = true;  // a one-window bake: the usual is the same-hour median of the earlier days in it
        return src;
      }).catch(() => null));
    }
    return stripSources.get(key);
  }
  const gridVal = (src, g, field, key) => {
    const hit = src.grids.get(key);
    const s = hit && hit[0][g] && hit[0][g][field];
    return s ? num(s[hit[1]]) : null;
  };
  const linkVal = (src, id, field, key) => {
    const hit = src.links.get(key);
    const s = hit && hit[0][id] && hit[0][id][field];
    return s ? s[hit[1]] : null;
  };
  /* The usual price at `key`: the day file's table, or (a one-window bake) the median of the
     same clock hour on the earlier days it holds. Nothing from the clock's own day is used. */
  const usualCache = new Map();
  function usualAt(src, g, key) {
    const hour = key.slice(11, 13);
    if (src.usual) {
      const row = src.usual[g] && src.usual[g][hour];
      return row && num(row[0]) != null ? { value: row[0], days: row[1] } : null;
    }
    if (!src.whole) return null;
    const ck = g + key.slice(0, 13);
    if (!usualCache.has(ck)) {
      const vals = [], days = new Set();
      src.grids.forEach((hit, t) => {
        if (t.slice(0, 10) >= key.slice(0, 10) || t.slice(11, 13) !== hour) return;
        const v = gridVal(src, g, 'lmp_median', t);
        if (v != null) { vals.push(v); days.add(t.slice(0, 10)); }
      });
      vals.sort((a, b) => a - b);
      const m = vals.length >> 1;
      usualCache.set(ck, vals.length ? { value: vals.length % 2 ? vals[m] : (vals[m - 1] + vals[m]) / 2, days: days.size } : null);
    }
    return usualCache.get(ck);
  }
  const keyBefore = (key, steps) => {
    const m = minuteOf(key) - steps * STEP_MIN;
    let day = key.slice(0, 10), mm = m;
    while (mm < 0) { day = dayPlus(day, -1); mm += 1440; }
    return atMinute(day, mm);
  };

  /* One grid at the clock: price, change, sparkline values, status. */
  function gridAt(src, g, key) {
    const v = gridVal(src, g, 'lmp_median', key);
    const usual = usualAt(src, g, key);
    const spark = [];
    for (let k = SPARK_STEPS - 1; k >= 0; k -= 1) spark.push(gridVal(src, g, 'lmp_median', keyBefore(key, k)));
    let delta = null;
    if (v != null && usual && usual.value) delta = { pct: Math.round(((v - usual.value) / usual.value) * 100), vs: 'usual', usual };
    else {
      const before = gridVal(src, g, 'lmp_median', keyBefore(key, 12));
      if (v != null && before) delta = { pct: Math.round(((v - before) / before) * 100), vs: 'hour' };
    }
    const short = gridVal(src, g, 'dr_short_mw', key);
    const max = gridVal(src, g, 'lmp_max', key);
    let status = null;
    if (v != null && v >= CAP) status = { level: 'bad', text: 'Cap', words: 'median at the ₱32,000 offer cap' };
    else if (short != null && short > 0) status = { level: 'bad', text: 'Short', words: `reserves short by ${fmt(short)} MW` };
    else if (max != null && max >= CAP) status = { level: 'warn', text: 'Node cap', words: 'a node at the ₱32,000 offer cap' };
    if (status && status.text === 'Cap' && short != null && short > 0) status.words += `, reserves short by ${fmt(short)} MW`;
    return { v, usual: usual ? usual.value : null, delta, spark, status };
  }
  /* One link at the clock: flow and direction, and the run of its congested state. */
  function linkAt(src, id, key) {
    const flow = num(linkVal(src, id, 'flow', key));
    const cong = flag(linkVal(src, id, 'congested', key));
    let run = null;
    if (cong != null) {
      let k = 0, cut = false;
      for (;;) {
        const prev = keyBefore(key, k + 1);
        if (!src.links.has(prev)) { cut = true; break; }
        if (flag(linkVal(src, id, 'congested', prev)) !== cong) break;
        k += 1;
        if (k > 2 * 288) { cut = true; break; }
      }
      run = { since: keyBefore(key, k), minutes: (k + 1) * STEP_MIN, cut };
    }
    return { flow, cong, run };
  }

  /* A sparkline: no axes, a faint baseline at the usual price, the line in --text-2 and an end
     dot in the price colour. Inline SVG with a viewBox, no inline style. */
  const SPARK_W = 36, SPARK_H = 18;
  function sparkline(svg, values, usual, tone) {
    svg.replaceChildren();
    const known = values.filter((v) => v != null);
    if (known.length < 2) { svg.classList.add('gn-spark-empty'); return; }
    svg.classList.remove('gn-spark-empty');
    let lo = Math.min(...known), hi = Math.max(...known);
    if (num(usual) != null) { lo = Math.min(lo, usual); hi = Math.max(hi, usual); }
    if (hi - lo < 1) { hi += 1; lo -= 1; }
    const pad = 2.5;
    const x = (i) => pad + (i / (values.length - 1)) * (SPARK_W - 2 * pad);
    const y = (v) => pad + (1 - (v - lo) / (hi - lo)) * (SPARK_H - 2 * pad);
    if (num(usual) != null) {
      const base = document.createElementNS(SVG, 'line');
      [['x1', pad], ['x2', SPARK_W - pad], ['y1', y(usual).toFixed(1)], ['y2', y(usual).toFixed(1)], ['class', 'gn-spark-usual']]
        .forEach(([k, v]) => base.setAttribute(k, v));
      svg.appendChild(base);
    }
    let d = '', pen = false;
    values.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1);
      pen = true;
    });
    const line = document.createElementNS(SVG, 'path');
    line.setAttribute('d', d);
    line.setAttribute('class', 'gn-spark-line');
    svg.appendChild(line);
    const last = values[values.length - 1];
    if (last != null) {
      const dot = document.createElementNS(SVG, 'circle');
      [['cx', x(values.length - 1).toFixed(1)], ['cy', y(last).toFixed(1)], ['r', '2.2'], ['class', 'gn-spark-dot gn-' + tone]]
        .forEach(([k, v]) => dot.setAttribute(k, v));
      svg.appendChild(dot);
    }
  }

  let strip = null;  // the strip's nodes, built once and refreshed in place (focus survives a redraw)
  /* On the desk itself a grid or a link opens in place: the address changes (pushState) and the
     map, which reads `?grid=` and `?link=`, hears a popstate. Elsewhere the link loads the desk. */
  function inPlace(e) {
    if (window.location.pathname !== '/' || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (typeof history.pushState !== 'function' || typeof PopStateEvent !== 'function') return;
    e.preventDefault();
    history.pushState(null, '', e.currentTarget.getAttribute('href'));
    window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
  }
  function section(cls, label, head) {
    const sec = make('section', 'gn-sec ' + cls);
    sec.setAttribute('aria-label', label);
    if (head) sec.appendChild(make('span', 'gn-sec-h', head));
    return sec;
  }
  function buildStrip() {
    if (!row2Left || !stripOn()) return;
    const view = make('div', 'gn-strip');
    view.setAttribute('role', 'region');
    view.setAttribute('aria-label', 'Prices, congestion and alerts at the replay time');

    const prices = section('gn-sec-prices', 'Prices', 'Price');
    const unit = make('span', 'gn-sec-unit', '₱/MWh');
    const basis = make('span', 'gn-sec-basis');
    prices.append(unit, basis);
    const cells = {};
    STRIP_GRIDS.forEach(([g, name, code]) => {
      const a = make('a', 'gn-px');
      a.href = '/?grid=' + g;
      a.dataset.grid = g;
      const codeEl = make('span', 'gn-px-code', code);
      codeEl.title = name;
      const v = make('span', 'gn-px-v mono');
      const spark = document.createElementNS(SVG, 'svg');
      spark.setAttribute('viewBox', `0 0 ${SPARK_W} ${SPARK_H}`);
      spark.setAttribute('width', String(SPARK_W));
      spark.setAttribute('height', String(SPARK_H));
      spark.setAttribute('aria-hidden', 'true');
      spark.setAttribute('class', 'gn-spark');
      const d = make('span', 'gn-px-d mono');
      const st = make('span', 'gn-px-flag');
      a.append(codeEl, v, spark, d, st);
      a.addEventListener('click', inPlace);
      prices.appendChild(a);
      cells[g] = { a, v, spark, d, st, name };
    });

    const links = section('gn-sec-links', 'HVDC congestion', 'HVDC');
    const lcells = {};
    STRIP_LINKS.forEach(([id, name, short, from, to]) => {
      const a = make('a', 'gn-ln');
      a.href = '/?link=' + id;
      const dot = make('span', 'gn-ln-dot');
      const nm = make('span', 'gn-ln-name');
      nm.append(make('span', 'gn-long', name), make('span', 'gn-short', short));
      const flow = make('span', 'gn-ln-flow mono');
      const st = make('span', 'gn-ln-state');
      a.append(dot, nm, flow, st);
      a.addEventListener('click', inPlace);
      links.appendChild(a);
      lcells[id] = { a, dot, flow, st, name, from, to };
    });

    const notes = section('gn-sec-notes', 'Alerts and notices');
    const counts = make('a', 'gn-sev-counts');
    counts.href = '/notices';
    const sev = {};
    ['alert', 'warning', 'info'].forEach((k) => {
      const c = make('span', 'gn-sev gn-sev-' + k);
      c.append(glyph(GLYPH[k]), make('span', 'gn-sev-n mono', '0'));
      counts.appendChild(c);
      sev[k] = c;
    });
    const line = make('div', 'gn-note-line');
    const note = make('a', 'gn-note');
    const noteKind = make('span', 'gn-note-kind');
    const noteTime = make('span', 'gn-note-time mono');
    const noteText = make('span', 'gn-note-text');
    const noteGrid = make('span', 'gn-note-grid');
    const noteGlyph = make('span', 'gn-note-glyph');
    note.append(noteGlyph, noteKind, noteTime, noteGrid, noteText);
    line.appendChild(note);
    const all = make('a', 'gn-viewall', 'View all');
    all.href = '/notices';
    notes.append(counts, line, all);

    view.append(prices, links, notes);
    row2Left.appendChild(view);
    strip = { view, cells, lcells, sev, counts, basis, line, note, noteGlyph, noteGrid, noteKind, noteTime, noteText, all, items: [], pos: 0, at: null };
    /* The newest items take turns, one line at a time; held while the reader is on the line. */
    const hold = () => { strip.held = true; };
    const release = () => { strip.held = false; };
    line.addEventListener('mouseenter', hold);
    line.addEventListener('mouseleave', release);
    line.addEventListener('focusin', hold);
    line.addEventListener('focusout', release);
    setInterval(cycleNote, CYCLE_MS);
    /* On a legacy desk (no replay index) the page's own clock leads: the strip follows its renders. */
    window.addEventListener('grid-desk-ready', () => {
      const G = window.GridDesk;
      if (G && typeof G.onRender === 'function') G.onRender(() => { if (!spanIndexed) renderStrip(); });
    });
    renderStrip();
    loadTicker();
  }
  let spanIndexed = false;
  const reducedMotion = () => Boolean(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  /* The strip's clock: the shared as-of; a legacy desk's own clock while it leads. */
  function stripAt() {
    const G = window.GridDesk;
    if (!spanIndexed && G && G.D && Array.isArray(G.D.t) && G.state && G.D.t[G.state.i]) return tkey(G.D.t[G.state.i]);
    return asOf;
  }
  function renderStrip() {
    if (!strip) return;
    const at = stripAt();
    const key = atMinute(at.slice(0, 10), Math.floor(minuteOf(at) / STEP_MIN) * STEP_MIN);
    strip.at = key;
    stripSource(key).then((src) => { if (strip.at === key) drawFigures(src, key); });
    drawNotes(key);
  }
  function drawFigures(src, key) {
    const when = hhmm(key);
    const bases = new Set();
    STRIP_GRIDS.forEach(([g, name]) => {
      const c = strip.cells[g];
      const r = src ? gridAt(src, g, key) : null;
      const tone = r ? priceTone(r.v, r.usual) : 'pn';
      c.a.className = 'gn-px gn-tone-' + tone + (r && r.status ? ' gn-px-' + r.status.level : '');
      c.v.textContent = r && r.v != null ? fmt(r.v) : 'No data';
      c.v.classList.toggle('gn-nodata-v', !(r && r.v != null));
      sparkline(c.spark, r ? r.spark : [], r ? r.usual : null, tone);
      const d = r && r.delta;
      if (d) bases.add(d.vs);
      c.d.textContent = d ? `${d.pct > 0 ? '+' : d.pct < 0 ? '−' : '±'}${Math.abs(d.pct)}%` : '';
      c.d.className = 'gn-px-d mono' + (d ? (d.pct > 2 ? ' gn-up' : d.pct < -2 ? ' gn-down' : ' gn-flat') : '');
      c.st.textContent = r && r.status ? r.status.text : '';
      c.st.hidden = !(r && r.status);
      let words = `${name}: `;
      if (!r || r.v == null) words += `No data at ${when}.`;
      else {
        words += `₱${fmt(r.v)} per MWh at ${when}`;
        if (d && d.vs === 'usual') words += `, ${Math.abs(d.pct)}% ${d.pct >= 0 ? 'above' : 'below'} the usual ₱${fmt(d.usual.value)}`;
        else if (d) words += `, ${Math.abs(d.pct)}% ${d.pct >= 0 ? 'up' : 'down'} on an hour before`;
        if (r.status) words += `, ${r.status.words}`;
        words += '.';
      }
      c.a.setAttribute('aria-label', words + ' Open the desk for this grid.');
      c.a.title = words;
    });
    /* The change's basis, said once for the section: against the usual price, or an hour before. */
    strip.basis.textContent = bases.size === 1 ? (bases.has('usual') ? 'vs usual' : 'vs 1h') : bases.size ? 'vs usual or 1h' : '';
    strip.basis.title = bases.size ? 'Change against the usual price of the hour (the median of the same hour on earlier days), or against an hour before when the usual is unknown.' : '';
    STRIP_LINKS.forEach(([id]) => {
      const c = strip.lcells[id];
      const r = src ? linkAt(src, id, key) : null;
      const known = r && r.flow != null;
      c.flow.textContent = '';
      if (known) {
        const arrow = r.flow > 0 ? '→' : r.flow < 0 ? '←' : '·';
        c.flow.append(make('span', 'gn-ln-arrow', arrow), document.createTextNode(fmt(Math.abs(r.flow))), make('span', 'gn-unit', ' MW'));
      } else c.flow.textContent = 'No data';
      c.flow.classList.toggle('gn-nodata-v', !known);
      const hot = r && r.cong === true;
      c.a.className = 'gn-ln' + (hot ? ' gn-ln-hot' : r && r.cong === false ? ' gn-ln-ok' : '');
      c.st.textContent = '';
      if (hot) c.st.append(make('span', 'gn-long', 'Congested '), document.createTextNode(durWords(r.run.minutes) + (r.run.cut ? '+' : '')));
      c.st.hidden = !hot;
      let words = `${c.name} HVDC: `;
      if (!known) words += `No flow data at ${when}`;
      else if (r.flow === 0) words += `no flow at ${when}`;
      else words += `${fmt(Math.abs(r.flow))} MW from ${r.flow > 0 ? c.from : c.to} to ${r.flow > 0 ? c.to : c.from} at ${when}`;
      if (hot) words += `, congested since ${hhmm(r.run.since)}${r.run.cut ? ' or earlier' : ''}`;
      else if (r && r.cong === false) words += ', not congested';
      words += '.';
      c.a.setAttribute('aria-label', words);
      c.a.title = words;
    });
  }
  function drawNotes(key) {
    const items = tickerItems(key);
    const from = minutesAt(key) - WINDOW_MIN;
    const n = { alert: 0, warning: 0, info: 0 };
    items.forEach((it) => { if (minutesAt(it.t) > from) n[severityOf(it.kind)] += 1; });
    Object.keys(n).forEach((k) => {
      strip.sev[k].lastChild.textContent = String(n[k]);
      strip.sev[k].classList.toggle('gn-sev-zero', !n[k]);
    });
    const say = (k, one, many) => `${n[k]} ${n[k] === 1 ? one : many}`;
    const words = `Last 6 h to ${hhmm(key)}: ${say('alert', 'alert', 'alerts')}, ${say('warning', 'warning', 'warnings')}, ${say('info', 'notice', 'notices')}.`;
    strip.counts.title = words + ' View all notices.';
    strip.counts.setAttribute('aria-label', words + ' View all notices.');
    strip.counts.href = '/notices?at=' + key;
    const shown = items.slice(0, SHOWN_ITEMS);
    const same = shown.length === strip.items.length && shown.every((it, i) => it.href === strip.items[i].href && it.t === strip.items[i].t);
    strip.items = shown;
    if (!same) strip.pos = 0;
    strip.all.href = '/notices?at=' + key;
    showNote();
  }
  function showNote() {
    const it = strip.items[strip.pos];
    const { note, noteGlyph, noteGrid, noteKind, noteTime, noteText } = strip;
    noteGrid.textContent = '';
    noteGlyph.replaceChildren();
    if (!it) {
      note.href = '/notices?at=' + (strip.at || asOf);
      note.className = 'gn-note gn-note-empty';
      noteKind.textContent = '';
      noteTime.textContent = '';
      noteText.textContent = tickerData ? 'No notices yet at this time.' : 'No data';
      note.setAttribute('aria-label', noteText.textContent + ' Open the notices.');
      note.removeAttribute('title');
      return;
    }
    note.href = it.href;
    note.className = 'gn-note gn-note-' + severityOf(it.kind);
    noteGlyph.appendChild(glyph(GLYPH[severityOf(it.kind)]));
    noteKind.textContent = it.label;
    noteTime.textContent = hhmm(it.t);
    noteGrid.textContent = it.grid || '';
    noteText.textContent = it.text;
    note.title = `${it.label}, ${asOfWords(it.t)}${it.grid ? ', ' + it.grid : ''}: ${it.text}`;
    note.setAttribute('aria-label', `${it.label}, ${asOfWords(it.t)}${it.grid ? ', ' + it.grid : ''}. ${it.text}`);
  }
  function cycleNote() {
    if (!strip || strip.held || strip.items.length < 2 || reducedMotion() || document.hidden) return;
    strip.line.classList.add('gn-fade');
    setTimeout(() => {
      strip.pos = (strip.pos + 1) % strip.items.length;
      showNote();
      strip.line.classList.remove('gn-fade');
    }, 180);
  }
  /* The strip's notices: the clock's month and the one before it (a year bake keeps one file per
     month); a bake without replay.json has the one advisories.json. Reloaded when the clock
     changes month. */
  let tickerMonths = null;
  function loadTicker() {
    if (!strip) return;
    const key = monthOf(asOf);
    if (tickerMonths === key) return;
    tickerMonths = key;
    Promise.all([notices(monthPlus(key, -1), key), getJson('events.json')]).then(([advisories, events]) => {
      if (tickerMonths !== key) return;
      tickerData = advisories ? { advisories, events: events || [] } : null;
      if (!advisories || advisories.partial) tickerMonths = null;  // PERF-6: a failed read is asked again at the next clock change
      renderStrip();
    });
  }

  // ---------- the replay index and its day and month files ----------
  const getJson = (name) => fetch(DATA + name).then((r) => (r.ok ? r.json() : r.text().then(() => null))).catch(() => null);
  const monthOf = (t) => String(t).slice(0, 7);
  const monthPlus = (month, n) => {
    const d = new Date(month + '-01T00:00:00Z');
    d.setUTCMonth(d.getUTCMonth() + n);
    return d.toISOString().slice(0, 7);
  };
  const ready = getJson('replay.json').then((index) => {
    const ok = index && index.v === 1 && AT.test(String(index.first)) && AT.test(String(index.last)) && Array.isArray(index.days);
    if (ok) {
      SPAN.first = index.first; SPAN.last = index.last; SPAN.days = index.days;
      SPAN.missing = Array.isArray(index.missing) ? index.missing : [];
      SPAN.nodeDays = Array.isArray(index.node_days) ? index.node_days : [];
      SPAN.months = Array.isArray(index.months) ? index.months : [];
    }
    spanKnown = true;
    spanIndexed = Boolean(ok);
    const before = asOf;
    asOf = clamp(asOf);
    store.set(ASOF_KEY, asOf);
    renderAsOf();
    if (asOf !== before) asOfListeners.forEach((fn) => { try { fn(asOf); } catch (e) { /* a listener's own fault */ } });
    return ok ? index : null;
  });
  /* PERF-6: a read kept in `cache` under `key`; one that came back null (a failed read, or nothing
     to read) is forgotten after RETRY_MS, so a passing fault does not leave a page empty until a
     reload, and a page asking again at once does not hammer a failing server. */
  const RETRY_MS = 5000;
  function kept(cache, key, read) {
    if (!cache.has(key)) {
      const answer = read();
      cache.set(key, answer);
      answer.then((value) => {
        if (value === null) setTimeout(() => { if (cache.get(key) === answer) cache.delete(key); }, RETRY_MS);
      });
    }
    return cache.get(key);
  }
  const dayCache = new Map();
  /* One day's file (`days/<day>.json`: its axis, the grids' series, the links and the usual table),
     or null for a missing day or a bake without day files. */
  function dayFile(day) {
    return kept(dayCache, day, () => ready.then((index) => (index && index.days.includes(day) ? getJson('days/' + day + '.json') : null)));
  }
  const monthCache = new Map();
  /* The notices of the months from..to (YYYY-MM, inclusive) in time order: the month files of a
     year bake, or the whole advisories.json of a bake without them. Null when nothing could be read. */
  function notices(from, to) {
    return ready.then((index) => {
      if (!index) return getJson('advisories.json');
      const months = (index.months || []).filter((m) => m >= from && m <= to);
      return Promise.all(months.map((m) => kept(monthCache, m, () => getJson('advisories/' + m + '.json'))))
        .then((parts) => {
          const out = [].concat(...parts.map((x) => x || []));
          if (parts.includes(null)) out.partial = true;  // PERF-6: a month could not be read; ask again later
          return out;
        });
    });
  }

  // ---------- pagination (alerts, notices, plants) ----------
  /* The page to show of `total` rows at `size` a page: clamped, with the row range [from, to). */
  function pageOf(total, page, size) {
    const pages = Math.max(1, Math.ceil(total / size));
    const p = Math.min(Math.max(1, Math.floor(Number(page) || 1)), pages);
    return { page: p, pages, from: (p - 1) * size, to: Math.min(total, p * size) };
  }
  /* The page numbers to offer: the first, the last and two either side of the current one;
     null marks a gap. */
  function pageNumbers(page, pages) {
    const out = [];
    for (let i = 1; i <= pages; i += 1) {
      if (i === 1 || i === pages || Math.abs(i - page) <= 2) out.push(i);
      else if (out[out.length - 1] !== null) out.push(null);
    }
    return out;
  }
  /* Draws the pager into `box` and calls `go(page)` when a page is picked. Hidden on one page. */
  function pager(box, total, page, size, go, noun) {
    if (!box) return;
    box.textContent = '';
    const at = pageOf(total, page, size);
    box.hidden = total <= size;
    if (box.hidden) return;
    box.classList.add('gn-pager');
    const label = make('span', 'gn-pager-range mono', `${at.from + 1}–${at.to} of ${total.toLocaleString('en-US')}${noun ? ' ' + noun : ''}`);
    const btn = (text, p, current, aria) => {
      const b = make('button', 'gn-pager-btn' + (current ? ' on' : ''), text);
      b.type = 'button';
      if (aria) b.setAttribute('aria-label', aria);
      if (current) b.setAttribute('aria-current', 'page');
      if (p == null) b.disabled = true;
      else b.addEventListener('click', () => go(p));
      return b;
    };
    box.appendChild(label);
    box.appendChild(btn('‹ Prev', at.page > 1 ? at.page - 1 : null, false, 'Previous page'));
    for (const n of pageNumbers(at.page, at.pages)) {
      if (n === null) box.appendChild(make('span', 'gn-pager-gap', '…'));
      else box.appendChild(btn(String(n), n === at.page ? null : n, n === at.page, 'Page ' + n));
    }
    box.appendChild(btn('Next ›', at.page < at.pages ? at.page + 1 : null, false, 'Next page'));
  }

  // ---------- public surface ----------
  window.GNShell = {
    span: SPAN,
    data: DATA,
    /* replay-year: `ready` resolves to the bake's replay.json (or null for a bake without one,
       whose span stays the 21-29 Sep window); `dayFile(day)` and `notices(fromMonth, toMonth)`
       read only the days and months a page needs. */
    ready,
    dayFile,
    notices,
    monthOf,
    monthPlus,
    dayPlus,
    validAt: (t) => AT.test(String(t).slice(0, 16)),
    asOf: () => asOf,
    setAsOf,
    onAsOf: (fn) => { asOfListeners.push(fn); },
    theme: () => root.dataset.theme,
    onTheme: (fn) => { themeListeners.push(fn); },
    /* Other scripts (alerts) may add strip items: {t, kind, label, grid, text, href}. */
    addTickerItems: (items) => { extraItems.push(...items); renderStrip(); },
    /* UX-4, shared with the map and the state card: the price colour's token suffix for a price
       against its usual (`p0`..`p4`, `pn` unknown), and the severity of an advisory kind. */
    priceTone,
    severityOf,
    /* The strip's alert items (E21), mapped from an inbox answer; `refreshAlerts()` asks again. */
    alertItemsFrom,
    /* Operator notice text as the desk shows it: technology words withheld, 1405H as 14:05. */
    opText,
    /* One pager for every long list: `pageOf(total, page, size)`, `pager(box, total, page, size, go, noun)`. */
    pageOf,
    pageNumbers,
    pager,
    refreshAlerts: () => loadAlerts(true),
    /* PERF-6: the one alert-inbox reader (`inbox(at, {view, user, fresh})`, see above) and the
       moments a reader should ask it again (`onInboxDue(fn)`: called with the as-of, at most once
       every 2.5 s while the clock plays and always where it stops). */
    inbox,
    onInboxDue: (fn) => { inboxListeners.push(fn); },
    accountSlot: () => accountSlot,
    /* Sign-in: `user()` is the signed-in Firebase user or null; `onUser(fn)` is called on every
       change; `idToken()` resolves to a bearer token or null; `signIn()` opens Google sign-in. */
    user: () => auth.user,
    authState: () => auth.state,
    onUser: (fn) => { auth.listeners.push(fn); },
    idToken: () => (auth.user ? auth.user.getIdToken() : Promise.resolve(null)),
    signIn,
    signOut,
    /* Platform polish: `title(parts)` sets "Visayas price spike · Alerts · InGRID";
       `crumbs([{href, label}, …])` draws the page head's breadcrumbs when the page has none;
       `section()` is the current section's name; `shortcuts()` opens the keyboard sheet. */
    title: setTitle,
    crumbs: setCrumbs,
    /* The product's and the assistant's names (design-system.md, "Renaming the product"). */
    brand: BRAND,
    agent: AGENT,
    section: sectionLabel,
    shortcuts: () => openKeys(null),
  };
  /* A title in the older form ("InGRID · Alerts"), static or set later by a page script,
     is read into the new one ("Alerts · InGRID"), with the section after the page's words. */
  function normaliseTitle() {
    const t = String(document.title || '');
    const m = new RegExp('^' + BRAND.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*·\\s*(.+)$').exec(t);
    if (m) setTitle(m[1]);
  }
  normaliseTitle();
  if (typeof MutationObserver === 'function') {
    const watchTitle = () => {
      const node = document.querySelector('head > title');
      if (node) new MutationObserver(normaliseTitle).observe(node, { childList: true, characterData: true, subtree: true });
    };
    if (document.querySelector('head > title')) watchTitle();
    else document.addEventListener('DOMContentLoaded', () => { normaliseTitle(); watchTitle(); }, { once: true });
  }
  asOfListeners.push(() => { loadTicker(); renderStrip(); });

  /* SHELL-1: the desk dock on every page. ask.js floats the `<section id="ask">` mount each page
     carries; a page without one (the journal, the notices, an alert's own page) gets the mount
     here, named after its section, and the dock's two files are loaded from this build. */
  function ensureDock() {
    /* UX-1: the side dock is gone. The command bar (command.js, command.css) loads on every page
       and holds the mount in its sheet; on /ask it is the page's conversation (platform polish). */
    const parts = window.location.pathname.split('/').filter(Boolean);
    const sheet = (name) => {
      if (document.querySelector('link[href$="/' + name + '"]')) return;
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = ASSET + name;
      document.head.appendChild(link);
    };
    if (!document.getElementById('ask')) {
      const mount = make('section');
      mount.id = 'ask';
      mount.dataset.context = parts[0] || 'home';
      mount.setAttribute('aria-label', 'Ask ' + AGENT);
      document.body.appendChild(mount);
      sheet('ask.css');
      loadScript('ask.js').catch(() => { /* the page reads without the dock */ });
    }
    /* On /ask the bar is the page itself: command.js fills the workspace's centre (#ask-main). */
    sheet('command.css');
    /* The bar draws its previews and citations in ui.js's shared card: it loads once ui.js is in
       (or after four seconds without it, when the bar runs without its cards). */
    const uiReady = window.GNUI && window.GNUI.ready ? window.GNUI.ready : Promise.resolve();
    Promise.race([uiReady, new Promise((resolve) => setTimeout(resolve, 4000))])
      .then(() => loadScript('command.js')).catch(() => { /* the page reads without the bar */ });
  }

  askConfig();
  function start() {
    adoptPage();
    buildStrip();
    startAuth();
    ensureDock();
  }
  /* The bar goes in as soon as the parser opens the body: a mutation observer's callback runs
     before the browser paints, so no page shows its old bar first. */
  if (document.body) buildBar();
  else if (typeof MutationObserver === 'function') {
    const watch = new MutationObserver(() => { if (document.body) { watch.disconnect(); buildBar(); } });
    watch.observe(document.documentElement, { childList: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
