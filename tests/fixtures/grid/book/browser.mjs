/* BOOK-3: the book page (`/book`) under the application's own header policy, served by this
   harness alone: the page has no route in the application until DOCK-5 stages it. Serves
   src/grid/book.html with a build stamp written in, its stylesheet and script, ask.css, ask.js
   and grid.css under /grid/<stamp>/, the vendored fonts, and the two baked files
   /grid-data/<stamp>/book/index.json and book/exposure.json from --data (the real builder's
   output, scripts/book/bake_book.py --out). Follows tests/fixtures/grid/outlooks/browser.mjs.

     node tests/fixtures/grid/book/browser.mjs --root . --data tests/fixtures/grid/book/bake \
          --stamp 0123456789abcdef --serve
         # serve only: print {"port": N} on one line, answer until the process is stopped

     node tests/fixtures/grid/book/browser.mjs --root . --data <dir> --width 1280 \
          --stamp 0123456789abcdef --playwright <playwright-core/index.mjs> --chromium <chrome>
         # open the page headless, read what it drew, report one JSON object

   Exit 0 when the page is clean, 1 when not, 3 when no browser or data is given. Loopback only. */
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const arg = (name, fallback) => { const i = argv.indexOf('--' + name); return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback; };
const ROOT = path.resolve(arg('root', '.'));
const WIDTH = Number(arg('width', '1280'));
const STAMP = arg('stamp', '0123456789abcdef');
const DATA_DIR = arg('data', '') ? path.resolve(arg('data', '')) : '';
const SERVE = argv.includes('--serve');
const PLAYWRIGHT = arg('playwright', ''), CHROMIUM = arg('chromium', ''), SHOT = arg('shot', '');
const report = (payload, code) => { process.exitCode = code; process.stdout.write(JSON.stringify(payload, null, 1) + '\n', () => process.exit(code)); };
if (!DATA_DIR) report({ok: false, ran: false, reason: 'no data directory given'}, 3);
else if (!SERVE && (!PLAYWRIGHT || !CHROMIUM)) report({ok: false, ran: false, reason: 'no browser given'}, 3);

const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
  + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
const SERVED = [];
const STATUS = {};
const DESIGN = new Set(['book.css', 'book.js', 'ask.css', 'ask.js', 'grid.css', 'shell.css', 'shell.js',
                        'command.css', 'command.js',  // UX-1: the command bar the shell loads
                        'ui.css', 'ui.js']);  // platform polish: the shared components
// SHELL-1: the shared bar
const DATA_FILES = new Set(['book/index.json', 'book/exposure.json']);
/* The desk assistant fetches views/book.json from the bake. The committed plan sets live in the
   catalog fixture; a key it bakes none for gets a well-formed empty set, as on the outlooks page. */
const PLAN_SETS = path.join(ROOT, 'tests/fixtures/grid/catalog/bake/views');
function planSet(name) {
  const hit = name.match(/^\/grid-data\/(?:[0-9a-f]{16}\/)?views\/([A-Za-z0-9][A-Za-z0-9._-]{0,127})\.json$/);
  if (!hit) return null;
  try {
    return readFileSync(path.join(PLAN_SETS, hit[1] + '.json'));
  } catch (error) {
    return Buffer.from(JSON.stringify({key: hit[1], views: []}));
  }
}
// InGRID brand: the icons and manifest every page's head links, answered at the root as the
// application's own routes answer them (src/api BRAND_ROOT_FILES).
const BRAND = {'/favicon.ico': 'image/x-icon', '/favicon.svg': 'image/svg+xml', '/apple-touch-icon.png': 'image/png',
  '/icon-192.png': 'image/png', '/icon-512.png': 'image/png', '/icon-maskable-512.png': 'image/png',
  '/site.webmanifest': 'application/manifest+json'};
const server = createServer((request, response) => {
  const name = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
  SERVED.push(name);
  const headers = {'Content-Security-Policy': CSP, 'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer'};
  const answer = (status, type, body, cache) => {
    STATUS[name] = status;
    response.writeHead(status, {...headers, 'content-type': type, 'Cache-Control': cache}).end(body);
  };
  if (name === '/book') {
    const page = readFileSync(path.join(ROOT, 'src/grid/book.html'), 'utf8')
      .replaceAll('__NOWCAST_STAMP__', STAMP);
    answer(200, 'text/html', page, 'no-cache'); return;
  }
  const design = name.match(new RegExp('^/grid/' + STAMP + '/(book\\.(?:css|js)|ask\\.(?:css|js)|shell\\.(?:css|js)|command\\.(?:css|js)|ui\\.(?:css|js)|grid\\.css)$'));
  if (design && DESIGN.has(design[1])) {
    answer(200, design[1].endsWith('.css') ? 'text/css' : 'text/javascript',
      readFileSync(path.join(ROOT, 'src/grid', design[1])), 'public, max-age=31536000, immutable');
    return;
  }
  const font = name.match(new RegExp('^/grid/' + STAMP + '/fonts/([a-z0-9][a-z0-9._-]*\\.woff2)$'));
  if (font) {
    try {
      answer(200, 'font/woff2', readFileSync(path.join(ROOT, 'src/grid/fonts', font[1])),
        'public, max-age=31536000, immutable');
    } catch (error) { answer(404, 'application/json', '{"code":"NOT_FOUND"}', 'no-store'); }
    return;
  }
  const data = name.match(new RegExp('^/grid-data/' + STAMP + '/(book/[a-z]+\\.json)$'));
  if (data && DATA_FILES.has(data[1])) {
    answer(200, 'application/json', readFileSync(path.join(DATA_DIR, data[1])), 'public, max-age=31536000, immutable');
    return;
  }
  const plans = planSet(name);
  if (plans) {
    answer(200, 'application/json', plans, 'public, max-age=31536000, immutable');
    return;
  }
  // SHELL-1: the shared bar's own reads, answered empty: no notice for its ticker, sign-in not
  // configured (no key), and an empty alerts list.
  if (name === '/grid-data/' + STAMP + '/advisories.json' || name === '/grid-data/' + STAMP + '/events.json') {
    answer(200, 'application/json', '[]', 'public, max-age=31536000, immutable'); return;
  }
  // The replay index (replay.json) answered with no span: the shell keeps its own 21-29 Sep window.
  if (name === '/grid-data/' + STAMP + '/replay.json') { answer(200, 'application/json', '{}', 'public, max-age=31536000, immutable'); return; }
  if (name === '/api/alerts/client-config') { answer(200, 'application/json', '{}', 'no-store'); return; }
  if (name === '/api/alerts/inbox') { answer(200, 'application/json', '{"alerts": []}', 'no-store'); return; }
  if (BRAND[name]) { answer(200, BRAND[name], readFileSync(path.join(ROOT, 'src/grid', name.slice(1))), 'no-cache'); return; }
  answer(404, 'application/json', '{"code":"NOT_FOUND"}', 'no-store');
});

if (DATA_DIR && SERVE) {
  server.listen(0, '127.0.0.1', () => {
    process.stdout.write(JSON.stringify({port: server.address().port}) + '\n');
  });
  const stop = () => { server.close(); process.exit(0); };
  process.on('SIGTERM', stop);
  process.on('SIGINT', stop);
  process.stdin.on('end', stop);
  process.stdin.resume();
} else if (DATA_DIR && PLAYWRIGHT && CHROMIUM) {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
  const browser = await chromium.launch({executablePath: CHROMIUM, headless: true, args: ['--no-sandbox']});
  const context = await browser.newContext({viewport: {width: WIDTH, height: 900}});
  const page = await context.newPage();
  const consoleErrors = [], pageErrors = [], failedRequests = [], badResponses = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('requestfailed', (r) => failedRequests.push(r.url()));
  page.on('response', (r) => { if (r.status() >= 400) badResponses.push(r.status() + ' ' + r.url()); });
  let thrown = null, seen = null, screens = [];
  try {
    await page.goto(base + '/book', {waitUntil: 'load'});
    await page.waitForFunction(() => {
      const empty = document.querySelector('#bk-empty');
      return document.querySelectorAll('.bk-section').length > 0 || (empty && !empty.hidden);
    }, null, {timeout: 15000});
    seen = await page.evaluate(() => {
      const text = (node) => (node ? node.textContent.replace(/\s+/g, ' ').trim() : '');
      const tables = {};
      document.querySelectorAll('table[data-table]').forEach((table) => {
        const wrap = table.closest('.bk-wrap');
        const before = wrap ? wrap.previousElementSibling : null;
        tables[table.dataset.table] = {
          headers: [...table.querySelectorAll('thead th')].map((cell) => text(cell)),
          rows: [...table.querySelectorAll('tbody tr')].map((row) => ({
            key: row.dataset.row,
            cells: [...row.querySelectorAll('td')].map((cell) => text(cell)),
            shades: [...row.querySelectorAll('td[data-shade]')].map((cell) => ({
              shade: cell.dataset.shade, cls: cell.className})),
          })),
          caption: before && before.classList.contains('bk-cap') ? text(before) : null,
          wrapWidth: wrap ? wrap.getBoundingClientRect().width : null,
        };
      });
      const sections = [...document.querySelectorAll('.bk-section')].map((section) => ({
        key: section.dataset.section,
        title: text(section.querySelector('h2')),
        texts: [...section.querySelectorAll('.bk-text')].map((item) => text(item)),
        order: [...section.children].map((child) => child.className || child.tagName.toLowerCase()),
      }));
      // SHELL-1: the section links are the shared bar's (shell.js); the page's static block is
      // the no-script fallback, which the shell removes.
      // Platform polish (PP-A): four links, then menus whose items carry a title and a line of
      // description; the label is the title.
      const nav = [...document.querySelectorAll('#gn-bar .gn-nav > a, #gn-bar .gn-navmenu a')].map((a) => ({
        href: a.getAttribute('href'), label: text(a.querySelector('.gn-navitem-t') || a), current: a.getAttribute('aria-current')}));
      return {
        title: document.title,
        flag: text(document.querySelector('#bk-flag')),
        summary: text(document.querySelector('#bk-summary')),
        empty: {hidden: document.querySelector('#bk-empty').hidden, text: text(document.querySelector('#bk-empty'))},
        says: [...document.querySelectorAll('.bk-say')].filter((n) => !n.hidden).map((n) => text(n)),
        caption: text(document.querySelector('#caption')),
        ask: (() => { const mount = document.querySelector('#ask');
          return mount ? {context: mount.getAttribute('data-context')} : null; })(),
        sections,
        tables,
        nav,
        plain: (() => {
          const clone = document.body.cloneNode(true);
          // A tab panel is shown text (one click away, never a fold); a closed fold is not.
          clone.querySelectorAll('details, [hidden]:not([role="tabpanel"]), script, style, template, table').forEach((n) => n.remove());
          return text(clone);
        })(),
        overflow: document.documentElement.scrollWidth - window.innerWidth,
        scrollHeight: document.documentElement.scrollHeight,
        hrefs: [...document.querySelectorAll('a')].map((a) => a.getAttribute('href')),
      };
    });
    /* Every screen: scroll one viewport at a time to the bottom and read where the header line
       sits, and whether the topmost element at its centre is the line itself. */
    const total = seen.scrollHeight;
    for (let top = 0; ; top += 800) {
      await page.evaluate((y) => window.scrollTo(0, y), top);
      screens.push(await page.evaluate(() => {
        const flag = document.querySelector('#bk-flag');
        const rect = flag.getBoundingClientRect();
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        return {y: window.scrollY, top: rect.top, bottom: rect.bottom, height: window.innerHeight,
          onTop: hit === flag || flag.contains(hit), text: flag.textContent.trim()};
      }));
      if (top >= total) break;
    }
    if (SHOT) await page.screenshot({path: SHOT, fullPage: true});
  } catch (error) { thrown = String(error); }
  await browser.close(); server.close();
  const ok = thrown === null && consoleErrors.length === 0 && pageErrors.length === 0
    && failedRequests.length === 0 && badResponses.length === 0 && seen !== null && seen.overflow <= 0;
  report({ok, ran: true, width: WIDTH, stamp: STAMP, thrown, consoleErrors, pageErrors,
    failedRequests, badResponses, seen, screens, status: STATUS,
    served: SERVED.filter((name) => !BRAND[name])}, ok ? 0 : 1);
}
