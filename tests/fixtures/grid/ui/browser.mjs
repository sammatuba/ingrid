/* The design system's behaviours (ui.js) in a real browser, on the reference page
   tests/fixtures/grid/ui/kitchen-sink.html.

   Serves the page at /ui (and the shell's assets under /grid/<stamp>/), with a small fake desk
   API: /api/desk/preview/<kind>/<id> answers a card for 08PEDC and 404 for anything else, and
   counts the requests. Every other read answers 404. Prints one JSON object.

     node tests/fixtures/grid/ui/browser.mjs --root . --playwright <playwright-core/index.mjs> \
          --chromium <chrome> [--widths 1440,390] [--shots <dir>] [--serve <port>]

   `--shots` also saves full-page screenshots of the reference page in both themes; `--serve`
   only serves (for a person to look at it) until stopped. Exit 0 when it ran, 3 when no browser
   is given. Loopback only. */
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
const WIDTHS = arg('widths', '1440,390').split(',').map(Number);
const SHOTS = arg('shots', '');
const SERVE = arg('serve', '');
const STAMP = '0123456789abcdef';
const TYPES = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
const FIXTURE = path.join(ROOT, 'tests/fixtures/grid/ui');

const requests = [];
const CARD = {
  kind: 'plant', id: '08PEDC', title: 'Synthetic geothermal 2', subtitle: 'Visayas · 08PEDC', href: '/plant/08PEDC',
  facts: [{label: 'Price', value: 31513, unit: '₱/MWh', at: '2026-09-21T13:40'}, {label: 'Dispatch', value: 0, unit: 'MW', at: '2026-09-21T13:40'}],
  sparks: [{label: 'Price, 24 h', unit: '₱/MWh', t: ['2026-09-21T12:00', '2026-09-21T13:00', '2026-09-21T13:40'], v: [5200, 6100, 31513]}],
  summary: 'Latest notice naming it, 13:38: Unit 2 tripped.',
  sources: [{title: 'Node prices', dataset_id: 'bake-nodes', href: '/data#bake-nodes'}],
};

const server = createServer((request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1');
  const name = decodeURIComponent(url.pathname);
  const answer = (status, type, body) => response.writeHead(status, {'content-type': type}).end(body);
  if (name === '/ui' || name === '/ui/') {
    answer(200, 'text/html', readFileSync(path.join(FIXTURE, 'kitchen-sink.html'), 'utf8').replaceAll('__NOWCAST_STAMP__', STAMP));
    return;
  }
  if (name === '/ui-fixture/kitchen-sink.js') { answer(200, 'text/javascript', readFileSync(path.join(FIXTURE, 'kitchen-sink.js'))); return; }
  const preview = name.match(/^\/api\/desk\/preview\/([a-z]+)\/(.+)$/);
  if (preview) {
    requests.push({kind: preview[1], id: preview[2], at: url.searchParams.get('at')});
    if (preview[1] === 'plant' && preview[2] === '08PEDC') answer(200, 'application/json', JSON.stringify(CARD));
    else answer(404, 'application/json', '{"error":"NOT_FOUND"}');
    return;
  }
  const asset = name.match(new RegExp('^/grid/' + STAMP + '/((?:fonts/)?[a-z0-9][a-z0-9._-]*\\.(?:css|js|woff2))$'));
  if (asset) {
    try { answer(200, TYPES[path.extname(asset[1])], readFileSync(path.join(ROOT, 'src/grid', asset[1]))); }
    catch (error) { answer(404, 'application/json', '{"code":"NOT_FOUND"}'); }
    return;
  }
  if (/^\/(plant|event|notices|alerts|settings|register|data)/.test(name)) { answer(200, 'text/html', '<!doctype html><title>elsewhere</title><p>elsewhere</p>'); return; }
  answer(404, 'application/json', '{"code":"NOT_FOUND"}');
});

if (SERVE) {
  server.listen(Number(SERVE), '127.0.0.1', () => process.stdout.write(`serving http://127.0.0.1:${SERVE}/ui\n`));
} else {
  if (!PLAYWRIGHT || !CHROMIUM) {
    process.stdout.write(JSON.stringify({ran: false, reason: 'no browser given'}) + '\n');
    process.exit(3);
  }
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
  const browser = await chromium.launch({executablePath: CHROMIUM, headless: true, args: ['--no-sandbox']});
  const report = {ran: true, widths: {}};

  const rowsOf = () => [...document.querySelectorAll('#ks-table tbody tr')].map((tr) => tr.id || (tr.cells[1] && tr.cells[1].textContent.trim()));
  for (const width of WIDTHS) {
    const context = await browser.newContext({viewport: {width, height: 900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(String(e && e.stack || e)));
    const out = {};
    const open = async (suffix) => { await page.goto(base + '/ui' + (suffix || ''), {waitUntil: 'load'}); await page.evaluate(() => window.GNUI.ready); await page.waitForTimeout(120); };
    await open();
    out.loaded = await page.evaluate(() => ({
      version: window.GNUI.version,
      api: ['sort', 'resort', 'filters', 'preview', 'previewHtml', 'badge', 'enhance', 'selectTab'].filter((k) => typeof window.GNUI[k] === 'function'),
      sortButtons: document.querySelectorAll('#ks-table th[data-sort] > button.gn-sort').length,
      barH: getComputedStyle(document.documentElement).getPropertyValue('--bar-h').trim(),
      bar: Math.round(document.getElementById('gn-bar').getBoundingClientRect().height),
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      uiCssBeforeShell: (() => { const l = [...document.querySelectorAll('link[rel=stylesheet]')].map((n) => n.getAttribute('href').split('/').pop()); return l.indexOf('ui.css') < l.indexOf('shell.css'); })(),
      badges: [...document.querySelectorAll('#ks-badges-js .gn-badge')].map((n) => [n.textContent, n.className]),
      targets: [...document.querySelectorAll('main button, main .gn-crumbs a, main a.gn-btn, main input, main select')].filter((n) => n.getClientRects().length && !n.closest('[hidden]'))
        .map((n) => { const r = n.getBoundingClientRect(); return {name: n.getAttribute('aria-label') || n.textContent.trim().slice(0, 30), w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right), scrolls: Boolean(n.closest('.gn-table-wrap'))}; }),
      view: window.innerWidth,
      headingLabel: (() => { const c = getComputedStyle(document.getElementById('ks-label-h')); return [c.fontSize, c.textTransform, c.fontWeight]; })(),
    }));
    /* Sorting: MW descending first, then ascending; a row without a value stays last; the detail row follows its row. */
    await page.click('#ks-table th:nth-child(4) .gn-sort');
    out.sortDesc = await page.evaluate((f) => ({rows: eval(f)(), sort: document.querySelector('#ks-table th:nth-child(4)').getAttribute('aria-sort'),
      others: [...document.querySelectorAll('#ks-table th[aria-sort]')].length}), rowsOf.toString());
    await page.click('#ks-table th:nth-child(4) .gn-sort');
    out.sortAsc = await page.evaluate((f) => ({rows: eval(f)(), sort: document.querySelector('#ks-table th:nth-child(4)').getAttribute('aria-sort')}), rowsOf.toString());
    /* A page redraws the rows in another order: the observer (and GNUI.resort) puts the sort back. */
    out.resorted = await page.evaluate(async (f) => {
      const tbody = document.querySelector('#ks-table tbody');
      /* the rows drawn again in the opposite order, each detail row still after its own row */
      const groups = [];
      [...tbody.rows].forEach((tr) => { if (tr.classList.contains('gn-row-detail')) groups[groups.length - 1].push(tr); else groups.push([tr]); });
      tbody.replaceChildren(...groups.reverse().flat());
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const auto = eval(f)();
      const again = [];
      [...tbody.rows].forEach((tr) => { if (tr.classList.contains('gn-row-detail')) again[again.length - 1].push(tr); else again.push([tr]); });
      tbody.replaceChildren(...again.reverse().flat());
      window.GNUI.resort(document.getElementById('ks-table'));
      return {auto, manual: eval(f)()};
    }, rowsOf.toString());
    out.textSort = await page.evaluate((f) => { window.GNUI.sort(document.getElementById('ks-table'), 1, 'asc'); return eval(f)(); }, rowsOf.toString());
    /* Expandable row. */
    await page.click('button.gn-row-toggle');
    out.expanded = await page.evaluate(() => ({hidden: document.getElementById('ks-d1').hidden, expanded: document.querySelector('button.gn-row-toggle').getAttribute('aria-expanded'), url: location.pathname}));
    await page.click('button.gn-row-toggle');
    out.collapsed = await page.evaluate(() => document.getElementById('ks-d1').hidden);
    /* Menu: opens, focus on its first item, arrows move, Esc closes and focus returns. */
    await page.click('#ks-table tbody tr[data-href="/plant/08PEDC"] [data-menu]');
    out.menuOpen = await page.evaluate(() => { const m = document.querySelector('main .gn-menu[role=menu]:not([hidden])'); const r = m && m.getBoundingClientRect();
      return {open: Boolean(m), focus: document.activeElement && document.activeElement.textContent, role: m && m.getAttribute('role'), inView: r ? r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight : false,
        expanded: document.querySelector('#ks-table tbody tr[data-href="/plant/08PEDC"] [data-menu]').getAttribute('aria-expanded'), url: location.pathname}; });
    await page.keyboard.press('ArrowDown');
    out.menuMoved = await page.evaluate(() => document.activeElement && document.activeElement.textContent);
    await page.keyboard.press('Escape');
    out.menuClosed = await page.evaluate(() => ({open: Boolean(document.querySelector('main .gn-menu[role=menu]:not([hidden])')), focusBack: document.activeElement && document.activeElement.matches('[data-menu]')}));
    /* Tabs: click, keyboard, and the address. */
    await page.click('#ks-t2');
    out.tabClicked = await page.evaluate(() => ({sel: document.getElementById('ks-t2').getAttribute('aria-selected'), p1: document.getElementById('ks-p1').hidden, p2: document.getElementById('ks-p2').hidden, hash: location.hash}));
    await page.keyboard.press('ArrowRight');
    out.tabKey = await page.evaluate(() => ({sel: document.getElementById('ks-t3').getAttribute('aria-selected'), focus: document.activeElement.id, p3: document.getElementById('ks-p3').hidden}));
    await page.keyboard.press('Home');
    out.tabHome = await page.evaluate(() => document.activeElement.id);
    await open('#tab=ks:dispatch');
    out.tabFromHash = await page.evaluate(() => ({sel: document.getElementById('ks-t2').getAttribute('aria-selected'), p2: document.getElementById('ks-p2').hidden}));
    /* Filters and the address query. */
    await open();
    await page.click('#ks-filters [data-filter="grid"] button[data-value="CVIS"]');
    out.filtered = await page.evaluate(() => ({search: location.search, count: document.querySelector('.gn-filters-count').textContent, clear: !document.querySelector('.gn-clear').hidden,
      shown: [...document.querySelectorAll('#ks-table tbody tr[data-href]')].filter((tr) => !tr.hidden).length}));
    await open('?grid=CVIS&kind=trip&sev=alert');
    out.restored = await page.evaluate(() => ({state: window.ksFilters.get(), count: document.querySelector('.gn-filters-count').textContent,
      more: document.querySelector('.gn-more-filters > summary').getAttribute('data-active')}));
    await page.click('.gn-clear');
    out.cleared = await page.evaluate(() => ({search: location.search, clear: !document.querySelector('.gn-clear').hidden, state: window.ksFilters.get()}));
    /* A same-page row (#target) sets the hash and scrolls to its target. */
    await page.click('#ks-table tbody tr[data-href="#ks-tabs-h"] td:nth-child(3)');
    await page.waitForTimeout(150);
    out.hashRow = await page.evaluate(() => ({hash: location.hash, path: location.pathname, inView: (() => { const r = document.getElementById('ks-tabs-h').getBoundingClientRect(); const bar = document.getElementById('gn-bar').getBoundingClientRect().bottom; return r.top >= bar && r.top < innerHeight; })(), top: Math.round(document.getElementById('ks-tabs-h').getBoundingClientRect().top)}));
    await open();
    /* Row link: a click on a plain cell opens the row's page; a click on its toggle does not. */
    await page.click('#ks-table tbody tr[data-href="/plant/06CEBU"] td:nth-child(3)');
    await page.waitForLoadState('load');
    out.rowLink = new URL(page.url()).pathname;
    await open();
    /* Entity previews: hover after the delay, the clock in the request, one request for two hovers, Esc. */
    requests.length = 0;
    const link = width > 640 ? 'a[data-entity="plant:08PEDC"]' : null;
    if (link) {
      await page.hover(link);
      await page.waitForTimeout(80);
      out.previewEarly = await page.evaluate(() => Boolean(document.querySelector('#gn-pcard:not([hidden])')));
      await page.waitForTimeout(450);
      out.preview = await page.evaluate(() => { const c = document.querySelector('#gn-pcard:not([hidden])'); const r = c && c.getBoundingClientRect();
        return c ? {title: (c.querySelector('.gn-pcard-title') || {}).textContent, open: (c.querySelector('.gn-pcard-open') || {}).getAttribute && c.querySelector('.gn-pcard-open').getAttribute('href'),
          spark: Boolean(c.querySelector('svg.gn-pcard-svg path.ln')), inView: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight,
          expanded: document.querySelector('a[data-entity="plant:08PEDC"]').getAttribute('aria-expanded')} : null; });
      await page.mouse.move(5, 890);
      await page.waitForTimeout(300);
      out.previewGone = await page.evaluate(() => !document.querySelector('#gn-pcard:not([hidden])'));
      await page.hover(link);
      await page.waitForTimeout(450);
      await page.keyboard.press('Escape');
      out.previewEsc = await page.evaluate(() => !document.querySelector('#gn-pcard:not([hidden])'));
      out.previewRequests = requests.map((r) => r.kind + '/' + r.id + '@' + r.at);
      /* Content drawn after load previews too (delegated). */
      await page.evaluate(() => { const a = document.createElement('a'); a.href = '/plant/08PEDC'; a.dataset.entity = 'plant:08PEDC'; a.id = 'late'; a.textContent = 'late link'; document.getElementById('ks-note').appendChild(a); });
      await page.hover('#late');
      await page.waitForTimeout(450);
      out.previewLate = await page.evaluate(() => Boolean(document.querySelector('#gn-pcard:not([hidden])')));
      await page.mouse.move(5, 890);
      await page.waitForTimeout(300);
    }
    /* The info affordance pins a card (a 404 one here); a click outside closes it. */
    await page.click('.gn-entity-info');
    await page.waitForTimeout(250);
    out.pinned = await page.evaluate(() => { const c = document.querySelector('#gn-pcard:not([hidden])');
      return c ? {pinned: c.classList.contains('is-pinned'), close: Boolean(c.querySelector('.gn-pcard-x')), quiet: (c.querySelector('.gn-pcard-quiet') || {}).textContent} : null; });
    await page.mouse.click(5, 300);
    out.pinnedGone = await page.evaluate(() => !document.querySelector('#gn-pcard:not([hidden])'));
    /* The sticky header: under the bar once the table scrolls up, with its shadow. */
    if (width > 760) {
      await page.evaluate(() => { const t = document.getElementById('ks-table'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 40); });
      await page.waitForTimeout(150);
      out.sticky = await page.evaluate(() => ({th: Math.round(document.querySelector('#ks-table thead th').getBoundingClientRect().top),
        bar: Math.round(document.getElementById('gn-bar').getBoundingClientRect().bottom), stuck: document.getElementById('ks-table').classList.contains('is-stuck')}));
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(100);
      out.unstuck = await page.evaluate(() => document.getElementById('ks-table').classList.contains('is-stuck'));
    }
    if (SHOTS) {
      for (const theme of ['dark', 'light']) {
        await page.evaluate((t) => { localStorage.setItem('gn-theme', t); }, theme);
        await open();
        await page.waitForTimeout(300);
        await page.screenshot({path: path.join(SHOTS, `kitchen-${width}-${theme}.png`), fullPage: true});
      }
      await page.evaluate(() => localStorage.removeItem('gn-theme'));
    }
    out.errors = errors;
    report.widths[width] = out;
    await context.close();
  }
  await browser.close();
  server.close();
  process.stdout.write(JSON.stringify(report) + '\n');
}
