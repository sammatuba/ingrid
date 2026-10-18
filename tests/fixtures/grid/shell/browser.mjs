/* SHELL-1: the shared bar on every page, and (UX-1) the command bar that replaced the floating
   dock, in a real browser.

   Serves each page of src/grid at its application route with a build stamp written in, the
   design files under /grid/<stamp>/, and the vendored fonts. Every replay read (/grid-data/...)
   and API read answers 404, so the check covers the frame every page shares (the bar and the
   command bar, whose desk API is then down), not a page's figures. Opens every page at each width and reports what it drew.

     node tests/fixtures/grid/shell/browser.mjs --root . --playwright <playwright-core/index.mjs> \
          --chromium <chrome> [--widths 1280,1440,390]

   Prints one JSON object. Exit 0 when it ran, 3 when no browser is given. Loopback only. */
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const arg = (name, fallback) => { const i = argv.indexOf('--' + name); return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback; };
const ROOT = path.resolve(arg('root', '.'));
const PLAYWRIGHT = arg('playwright', '');
const CHROMIUM = arg('chromium', '');
const WIDTHS = arg('widths', '1280,1440,390').split(',').map(Number);
const STAMP = '0123456789abcdef';

/* Each page at the route the application serves it under (src/api/hosted.py). */
export const PAGES = {
  '/': 'index.html', '/event/syn-bay-unit-2-trip': 'event.html', '/book': 'book.html',
  '/outlooks': 'outlooks.html', '/register': 'register.html', '/models': 'models.html',
  '/work': 'work.html', '/map': 'map.html', '/ask': 'ask.html', '/alerts': 'alerts.html',
  '/settings': 'settings.html', '/assets': 'assets.html', '/asset/syn-node-1': 'asset.html',
  '/data': 'catalog.html', '/explain': 'explain.html', '/paper': 'paper.html',
  '/journal': 'journal.html', '/notices': 'notices.html', '/alert/0123456789abcdef01234567': 'spike.html',
};
const TYPES = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};

const server = createServer((request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1');
  const name = decodeURIComponent(url.pathname);
  const answer = (status, type, body) => response.writeHead(status, {'content-type': type}).end(body);
  if (PAGES[name]) {
    let html = readFileSync(path.join(ROOT, 'src/grid', PAGES[name]), 'utf8').replaceAll('__NOWCAST_STAMP__', STAMP);
    /* UX-4: `?replay=page` serves the page with the desk's mark (`<body data-replay="page">`,
       which the map-first desk carries), so the bar's desk behaviour is read on any copy of the
       desk page, with or without the mark in its source. */
    if (url.searchParams.get('replay') === 'page' && !/<body[^>]*data-replay=/.test(html)) html = html.replace(/<body(?=[\s>])/, '<body data-replay="page"');
    answer(200, 'text/html', html);
    return;
  }
  const asset = name.match(new RegExp('^/grid/' + STAMP + '/((?:fonts/)?[a-z0-9][a-z0-9._-]*\\.(?:css|js|woff2))$'));
  if (asset) {
    try {
      answer(200, TYPES[path.extname(asset[1])], readFileSync(path.join(ROOT, 'src/grid', asset[1])));
    } catch (error) { answer(404, 'application/json', '{"code":"NOT_FOUND"}'); }
    return;
  }
  answer(404, 'application/json', '{"code":"NOT_FOUND"}');
});

if (!PLAYWRIGHT || !CHROMIUM) {
  process.stdout.write(JSON.stringify({ran: false, reason: 'no browser given'}) + '\n');
  process.exit(3);
}

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
const browser = await chromium.launch({executablePath: CHROMIUM, headless: true, args: ['--no-sandbox']});

/* What one page drew: the bar, the static bars, the command bar and where the mount sits. */
const read = () => {
  const box = (node) => { if (!node) return null; const r = node.getBoundingClientRect(); return {left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), width: Math.round(r.width), height: Math.round(r.height)}; };
  const shown = (node) => Boolean(node && node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden');
  const bar = document.getElementById('gn-bar');
  const cmd = document.getElementById('gn-cmd');
  const mount = document.getElementById('ask');
  const input = document.getElementById('gc-input');
  const mic = cmd && cmd.querySelector('.gc-mic');
  const sheet = document.getElementById('gc-sheet');
  const list = document.getElementById('gc-list');
  const resume = cmd && cmd.querySelector('.gc-resume');
  return {
    bars: document.querySelectorAll('#gn-bar').length,
    barFirst: document.body.firstElementChild === bar,
    bar: box(bar),
    barOverflow: bar ? bar.scrollWidth - bar.clientWidth : null,
    barFont: bar ? getComputedStyle(bar).fontSize + ' ' + getComputedStyle(bar).fontFamily.split(',')[0] : null,
    nav: bar ? [...bar.querySelectorAll('.gn-nav > a, .gn-navmenu a')].map((a) => [a.getAttribute('href'), (a.querySelector('.gn-navitem-t') || a).textContent.trim(), a.getAttribute('aria-current')]) : [],
    here: bar ? [...bar.querySelectorAll('.gn-nav > a[aria-current="page"], .gn-navbtn.gn-here')].map((n) => n.textContent.trim()) : [],
    navShown: Boolean(bar && bar.querySelector('.gn-nav') && bar.querySelector('.gn-nav').getClientRects().length),
    menuButton: (() => { const b = bar && bar.querySelector('.gn-menu-btn'); return b && b.getClientRects().length ? {label: b.textContent.trim(), box: box(b)} : null; })(),
    title: document.title,
    staticNavShown: [...document.querySelectorAll('nav.sites')].some(shown),
    staticBarsShown: [...document.querySelectorAll('header.bar, div.bar')].filter(shown).map((n) => n.textContent.trim().slice(0, 60)),
    sideDock: Boolean(document.getElementById('gn-dock') || document.querySelector('.gn-dock-fab')),
    cmd: cmd ? {
      box: box(cmd),
      pill: box(cmd.querySelector('.gc-bar')),
      holdsMount: cmd.contains(mount),
      workspace: cmd.classList.contains('gc-ws'),
      compact: cmd.classList.contains('gc-compact'),
      reading: Boolean(document.querySelector('.gn-page--read')),
      pillBox: box(cmd.querySelector('.gc-pill')),
      mountInRail: Boolean(mount && mount.closest('.ask-rail') && shown(mount)),
      input: input ? {label: input.getAttribute('aria-label'), role: input.getAttribute('role'), controls: input.getAttribute('aria-controls'), placeholder: input.getAttribute('placeholder')} : null,
      mic: mic ? {label: mic.getAttribute('aria-label'), disabled: mic.getAttribute('aria-disabled')} : null,
      controls: [...cmd.querySelectorAll('.gc-bar button, .gc-head .gc-tool')].filter(shown).map((n) => ({name: n.getAttribute('aria-label') || n.textContent.trim(), box: box(n)})),
      open: Boolean(sheet && !sheet.hidden),
      sheet: sheet && !sheet.hidden ? box(sheet) : null,
      listShown: Boolean(list && !list.hidden),
      options: list ? [...list.querySelectorAll('[role="option"]')].map((n) => n.textContent.trim().slice(0, 80)) : [],
      turns: cmd.querySelectorAll('.gc-turn').length,
      resume: resume && !resume.hidden ? resume.textContent.trim() : null,
      focused: document.activeElement === input,
    } : null,
    mountShown: shown(mount),
    mountExists: Boolean(mount),
    mountInFlow: Boolean(mount && !cmd && shown(mount)),
    bodyPadRight: getComputedStyle(document.body).paddingRight,
    pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
    view: {width: window.innerWidth, height: window.innerHeight},
    /* UX-4: the second row: its height, the live strip's sections, and what holds its right end. */
    row2: bar && bar.querySelector('.gn-row2') ? {
      box: box(bar.querySelector('.gn-row2')),
      sections: [...bar.querySelectorAll('.gn-strip > .gn-sec')].map((n) => n.getAttribute('aria-label')),
      asOfButton: Boolean(bar.querySelector('button.gn-asof')),
      asOfLabel: Boolean(bar.querySelector('.gn-asof-static')),
      asOfText: ((bar.querySelector('.gn-asof') || {}).textContent || '').trim(),
      replayInBar: [...bar.querySelectorAll('.gn-replay, .clock')].filter(shown).length,
      pageClockInBar: Boolean(bar.querySelector('.clock')),
      ticker: Boolean(bar.querySelector('.gn-ticker, .gn-ticker-view')),
      targets: [...bar.querySelectorAll('.gn-row2 a, .gn-row2 button')].filter(shown).map((n) => ({label: n.getAttribute('aria-label') || n.textContent.trim(), box: box(n)})),
    } : null,
    theme: (() => { const t = bar && bar.querySelector('.gn-theme'); return t ? {label: t.getAttribute('aria-label'), text: t.textContent.trim(), box: box(t)} : null; })(),
  };
};
/* UX-4: the As of popover, opened: its replay controls, and the clock after one step forward. */
const readPop = () => {
  const box = (node) => { if (!node) return null; const r = node.getBoundingClientRect(); return {left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), width: Math.round(r.width), height: Math.round(r.height)}; };
  const pop = document.getElementById('gn-asof-pop');
  const button = document.querySelector('button.gn-asof');
  return {
    open: Boolean(pop && !pop.hidden && pop.getClientRects().length),
    expanded: button ? button.getAttribute('aria-expanded') : null,
    role: pop ? pop.getAttribute('role') : null,
    box: box(pop),
    controls: pop ? [...pop.querySelectorAll('button, input')].map((n) => ({label: n.getAttribute('aria-label'), box: box(n)})) : [],
    time: ((pop && pop.querySelector('.gn-rp-time')) || {}).textContent || '',
    asOf: ((button && button.querySelector('.gn-asof-when')) || {}).textContent || '',
    view: {width: window.innerWidth, height: window.innerHeight},
  };
};

const report = {ran: true, widths: {}};
for (const width of WIDTHS) {
  const context = await browser.newContext({viewport: {width, height: 900}});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push({page: page.url(), error: String(e && e.stack || e)}));
  const seen = {};
  for (const route of Object.keys(PAGES)) {
    await page.goto(base + route, {waitUntil: 'load'});
    await page.waitForTimeout(150);
    seen[route] = await page.evaluate(read);
  }
  /* The command bar: "/" focuses it and lists suggestions; typing lists an "Ask Ingrid" row;
     Enter asks (the desk API answers 404 here, so the turn says the desk did not answer). The
     open sheet and its thread hold on the next page; Esc collapses it, and that holds too. */
  const toggled = {};
  await page.goto(base + '/outlooks', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  await page.keyboard.press('/');
  await page.waitForTimeout(150);
  toggled.focused = await page.evaluate(read);
  await page.keyboard.type('synthetic sun');
  await page.waitForTimeout(400);
  toggled.typed = await page.evaluate(read);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(400);
  toggled.asked = await page.evaluate(read);
  /* A long answer: the sheet grows to its limit and must still stay under the bar and in the window. */
  await page.evaluate(() => {
    const filler = document.createElement('div');
    filler.className = 'gn-test-filler';
    filler.textContent = 'A long recorded answer. '.repeat(600);
    document.getElementById('gc-thread').appendChild(filler);
  });
  toggled.longAnswer = await page.evaluate(read);
  await page.evaluate(() => document.querySelector('.gn-test-filler').remove());
  await page.goto(base + '/book', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  toggled.nextPage = await page.evaluate(read);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(100);
  toggled.afterEsc = await page.evaluate(read);
  await page.goto(base + '/models', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  toggled.afterClose = await page.evaluate(read);
  await page.evaluate(() => { try { sessionStorage.clear(); } catch (e) { /* none */ } });
  /* UX-4: the desk with its mark draws no replay in the bar; every other page opens the replay
     from the As of control. */
  await page.goto(base + '/?replay=page', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  const desk = await page.evaluate(read);
  const popover = {};
  await page.goto(base + '/notices', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  popover.closed = await page.evaluate(readPop);
  await page.click('button.gn-asof');
  popover.opened = await page.evaluate(readPop);
  await page.click('#gn-asof-pop button[aria-label="Forward five minutes"]');
  popover.stepped = await page.evaluate(readPop);
  await page.click('#gn-asof-pop button[aria-label="Back five minutes"]');
  await page.keyboard.press('Escape');
  popover.escaped = await page.evaluate(readPop);
  popover.focusBack = await page.evaluate(() => document.activeElement && document.activeElement.matches('button.gn-asof'));
  /* Platform polish: the menus, the phone sheet, the shortcuts sheet and keys, breadcrumbs,
     titles and the compact command bar. */
  const ia = {};
  const focusInfo = () => page.evaluate(() => { const a = document.activeElement; return a ? {text: ((a.querySelector && a.querySelector('.gn-navitem-t')) || a).textContent.trim().slice(0, 40), id: a.id, inSheet: Boolean(a.closest('.gn-sheet'))} : null; });
  await page.goto(base + '/notices', {waitUntil: 'load'});
  await page.waitForTimeout(150);
  if (width > 760) {
    await page.focus('#gn-nav-decisions');
    await page.keyboard.press('ArrowDown');
    ia.menuOpen = await page.evaluate(() => { const m = document.getElementById('gn-navmenu-decisions'); const r = m.getBoundingClientRect();
      return {open: !m.hidden, expanded: document.getElementById('gn-nav-decisions').getAttribute('aria-expanded'), role: m.getAttribute('role'),
        items: [...m.querySelectorAll('[role="menuitem"]')].map((a) => [a.querySelector('.gn-navitem-t').textContent, a.querySelector('.gn-navitem-d').textContent]),
        inView: r.left >= 0 && r.right <= innerWidth}; });
    ia.menuFirst = await focusInfo();
    await page.keyboard.press('ArrowDown');
    ia.menuNext = await focusInfo();
    await page.keyboard.press('ArrowRight');
    ia.menuSide = await page.evaluate(() => ({evidence: !document.getElementById('gn-navmenu-evidence').hidden, decisions: !document.getElementById('gn-navmenu-decisions').hidden}));
    await page.keyboard.press('Escape');
    ia.menuEsc = await page.evaluate(() => ({open: [...document.querySelectorAll('.gn-navmenu')].some((m) => !m.hidden), focus: document.activeElement && document.activeElement.id}));
    await page.click('#gn-nav-about');
    ia.menuClick = await page.evaluate(() => !document.getElementById('gn-navmenu-about').hidden);
    await page.mouse.click(Math.round(width / 2), 600);
    ia.menuOutside = await page.evaluate(() => [...document.querySelectorAll('.gn-navmenu')].some((m) => !m.hidden));
  } else {
    await page.click('.gn-menu-btn');
    await page.waitForTimeout(100);
    ia.sheet = await page.evaluate(() => { const s = document.querySelector('.gn-navsheet'); const r = s && s.querySelector('.gn-sheet-panel').getBoundingClientRect();
      return s ? {links: [...s.querySelectorAll('a')].map((a) => (a.querySelector('.gn-navitem-t') || a).textContent.trim()), modal: s.getAttribute('aria-modal'),
        full: Math.round(r.height) === innerHeight && Math.round(r.width) === innerWidth, focusIn: s.contains(document.activeElement),
        expanded: document.querySelector('.gn-menu-btn').getAttribute('aria-expanded'), overflow: document.documentElement.scrollWidth - innerWidth} : null; });
    await page.keyboard.press('Escape');
    ia.sheetEsc = await page.evaluate(() => ({open: Boolean(document.querySelector('.gn-navsheet')), focusBack: document.activeElement && document.activeElement.matches('.gn-menu-btn')}));
  }
  await page.keyboard.press('?');
  await page.waitForTimeout(80);
  ia.keys = await page.evaluate(() => { const s = document.querySelector('.gn-keysheet');
    return s ? {rows: [...s.querySelectorAll('.gn-keys-row dd')].map((n) => n.textContent), modal: s.getAttribute('aria-modal'), focusIn: s.contains(document.activeElement)} : null; });
  for (let i = 0; i < 6; i += 1) await page.keyboard.press('Tab');
  ia.keysTrap = await focusInfo();
  await page.keyboard.press('Escape');
  ia.keysEsc = await page.evaluate(() => !document.querySelector('.gn-keysheet'));
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  await page.keyboard.press(']');
  ia.stepFwd = await page.evaluate(() => window.GNShell.asOf());
  await page.keyboard.press('[');
  ia.stepBack = await page.evaluate(() => window.GNShell.asOf());
  /* None of the keys fire while typing in a field. */
  await page.evaluate(() => { const i = document.createElement('input'); i.id = 'gn-test-field'; document.body.appendChild(i); i.focus(); });
  await page.keyboard.type('g]?');
  ia.typed = await page.evaluate(() => ({asOf: window.GNShell.asOf(), sheet: Boolean(document.querySelector('.gn-sheet')), path: location.pathname, value: document.getElementById('gn-test-field').value}));
  await page.evaluate(() => { document.getElementById('gn-test-field').remove(); });
  ia.crumbs = await page.evaluate(() => {
    const head = document.createElement('header'); head.className = 'gn-page-head'; head.id = 'gn-test-head';
    head.innerHTML = '<div class="gn-page-title"><h1>Test</h1></div>';
    document.body.appendChild(head);
    window.GNShell.crumbs([{href: '/alerts', label: 'Alerts'}, {label: 'Visayas price spike'}], head);
    const nav = head.querySelector('nav.gn-crumbs');
    const out = nav ? {first: nav === head.firstElementChild, label: nav.getAttribute('aria-label'), parts: [...nav.children].map((n) => [n.tagName, n.textContent, n.getAttribute('href'), n.getAttribute('aria-current')])} : null;
    window.GNShell.title('Visayas price spike');
    out.title = document.title;
    head.remove();
    return out;
  });
  await page.keyboard.press('g');
  await page.keyboard.press('a');
  await page.waitForURL(/\/alerts$/, {timeout: 3000}).catch(() => {});
  ia.goto = new URL(page.url()).pathname;
  /* The command bar: full at the top; past 160px a pill at the lower right; "/" brings the bar back. */
  await page.goto(base + '/register', {waitUntil: 'load'});
  await page.waitForTimeout(200);
  await page.evaluate(() => { const f = document.createElement('div'); f.className = 'gn-test-tall'; f.textContent = 'tall'; f.style.height = '3000px'; document.body.appendChild(f); });
  const cmdRead = () => page.evaluate(() => { const c = document.getElementById('gn-cmd'); const pill = c.querySelector('.gc-pill'); const barEl = c.querySelector('.gc-bar');
    const box = (n) => { const r = n.getBoundingClientRect(); return {left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), width: Math.round(r.width), height: Math.round(r.height)}; };
    return {compact: c.classList.contains('gc-compact'), pill: pill.getClientRects().length ? box(pill) : null, bar: barEl.getClientRects().length ? box(barEl) : null,
      label: pill.getAttribute('aria-label'), focused: document.activeElement === document.getElementById('gc-input'), view: {width: innerWidth, height: innerHeight}}; });
  ia.cmdTop = await cmdRead();
  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(250);
  ia.cmdScrolled = await cmdRead();
  await page.keyboard.press('/');
  await page.waitForTimeout(150);
  ia.cmdSlash = await cmdRead();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await page.mouse.click(5, 500);
  await page.waitForTimeout(150);
  ia.cmdAfter = await cmdRead();
  await page.click('.gc-pill');
  await page.waitForTimeout(150);
  ia.cmdPillClick = await cmdRead();
  await page.mouse.click(5, 500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
  ia.cmdBack = await cmdRead();
  await page.evaluate(() => { try { sessionStorage.clear(); } catch (e) { /* none */ } });
  report.widths[width] = {seen, toggled, desk, popover, ia, errors: errors.filter((e) => /\/(shell|ask|command)\.js/.test(e.error))};
  await context.close();
}
await browser.close();
server.close();
process.stdout.write(JSON.stringify(report) + '\n');
