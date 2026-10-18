/* DESK-5: the register page (`/register`) under the application's own header policy, in a real
   browser. Serves src/grid/register.html with a build stamp written in, its stylesheet, its
   script and grid.css under /grid/<stamp>/, the vendored fonts, and one baked
   /grid-data/<stamp>/register/index.json — the real builder's output over a fixture register
   and archive supplied by the test with --index. Opens the page headless, reads what it drew,
   exercises the family filter once, and reports console errors, page errors, failed requests,
   bad responses and the answer statuses.

     node tests/fixtures/grid/register/browser.mjs --root . --width 1280 \
          --stamp 0123456789abcdef --index <path/to/index.json> \
          --playwright <playwright-core/index.mjs> --chromium <chrome executable> [--shot out.png]

   Exit 0 when the page is clean, 1 when not, 3 when no browser is given. Loopback only. */
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
const INDEX = path.resolve(arg('index', ''));
const PLAYWRIGHT = arg('playwright', ''), CHROMIUM = arg('chromium', ''), SHOT = arg('shot', '');
const report = (payload, code) => { process.exitCode = code; process.stdout.write(JSON.stringify(payload, null, 1) + '\n', () => process.exit(code)); };  // exit once the write has drained; a payload past 64 KiB was cut
if (!PLAYWRIGHT || !CHROMIUM) report({ok: false, ran: false, reason: 'no browser given'}, 3);
if (!INDEX) report({ok: false, ran: false, reason: 'no index file given'}, 3);

const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
  + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
const SERVED = [];
const STATUS = {};
const DESIGN = new Set(['register.css', 'register.js', 'ask.css', 'ask.js', 'grid.css', 'shell.css', 'shell.js',
                        'command.css', 'command.js',  // UX-1: the command bar the shell loads
                        'ui.css', 'ui.js']);  // platform polish: the shared components
// SHELL-1: the shared bar (ericka-desk)
/* VIEW-1: the desk assistant on the page fetches its plan set from the bake. The committed
   plan sets live in the catalog fixture; a key the fixture bakes none for gets a well-formed
   empty set, and the panel draws its own absent line. */
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
  if (name === '/register') {
    const page = readFileSync(path.join(ROOT, 'src/grid/register.html'), 'utf8')
      .replaceAll('__NOWCAST_STAMP__', STAMP);
    answer(200, 'text/html', page, 'no-cache'); return;
  }
  const design = name.match(new RegExp('^/grid/' + STAMP + '/(register\\.(?:css|js)|ask\\.(?:css|js)|shell\\.(?:css|js)|command\\.(?:css|js)|ui\\.(?:css|js)|grid\\.css)$'));
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
  if (name === `/grid-data/${STAMP}/register/index.json`) {
    answer(200, 'application/json', readFileSync(INDEX), 'public, max-age=31536000, immutable');
    return;
  }
  const plans = planSet(name);
  if (plans) {
    answer(200, 'application/json', plans, 'public, max-age=31536000, immutable');
    return;
  }
  // SHELL-1: the shared bar's own reads (shell.js), answered empty: no notice for its ticker,
  // sign-in not configured (no key), and an empty alerts list.
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
const read = () => page.evaluate(() => {
  const text = (node) => (node ? node.textContent.replace(/\s+/g, ' ').trim() : '');
  const segs = (id) => [...document.querySelectorAll('#' + id + ' button')].map((b) => text(b));
  return {
    title: document.title,
    summary: text(document.querySelector('#rg-summary')),
    plain: (() => {
      const clone = document.body.cloneNode(true);
      clone.querySelectorAll('details, [hidden], script, style, template').forEach((n) => n.remove());
      return text(clone);
    })(),
    gaps: text(document.querySelector('#rg-gaps')),
    gapActions: [...document.querySelectorAll('#rg-gap-actions button')].map((b) => text(b)),
    empty: {hidden: document.querySelector('#rg-empty').hidden, text: text(document.querySelector('#rg-empty'))},
    filters: {
      hidden: document.querySelector('#rg-filters').hidden,
      family: segs('rg-family'), layer: segs('rg-layer'), state: segs('rg-state'),
      shown: text(document.querySelector('#rg-shown')),
    },
    headers: [...document.querySelectorAll('.rg-table thead th')].map((th) => text(th)),
    // Platform polish: one table, one row per assumption, each opening a detail row.
    rows: [...document.querySelectorAll('tr.rg-row')].map((row) => {
      const toggle = row.querySelector('[aria-expanded]');
      const detail = toggle ? document.getElementById(toggle.getAttribute('aria-controls')) : null;
      return {
        id: row.id,
        family: row.dataset.family,
        cells: [...row.querySelectorAll('td')].map(text),
        hidden: row.hidden,
        expanded: toggle ? toggle.getAttribute('aria-expanded') : null,
        detail: detail ? {
          hidden: detail.hidden,
          statement: text(detail.querySelector('.rg-statement')),
          line: text(detail.querySelector('.rg-line')),
          evidence: [...detail.querySelectorAll('.rg-evidence li')].map(text),
          outlooks: [...detail.querySelectorAll('.rg-outlooks a')].map((a) => text(a.parentNode)),
          marks: [...detail.querySelectorAll('.rg-mark')].map(text),
          links: [...detail.querySelectorAll('a')].map((a) => a.getAttribute('href')),
        } : null,
      };
    }),
    caption: text(document.querySelector('#caption')),
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    hrefs: [...document.querySelectorAll('a')].map((a) => a.getAttribute('href')),
  };
});
let thrown = null, seen = null, filtered = null, expanded = null, restored = null;
try {
  await page.goto(base + '/register', {waitUntil: 'load'});
  await page.waitForFunction(() => {
    const empty = document.querySelector('#rg-empty');
    return document.querySelectorAll('tr.rg-row').length > 0 || (empty && !empty.hidden);
  }, null, {timeout: 15000});
  seen = await read();
  const first = seen.rows.length ? seen.rows[0].family : null;
  if (first) {
    // Platform polish: the family filter is a segmented control; its first family is picked.
    await page.click(`#rg-family button[data-value="${first}"]`);
    await page.waitForFunction(() => {
      const shown = document.querySelector('#rg-shown');
      return /family=/.test(window.location.search) && shown && /\d+ (?:of \d+ )?rows? shown/.test(shown.textContent || '');
    }, null, {timeout: 5000});
    filtered = await read();
    filtered.address = await page.evaluate(() => window.location.search);
    // A row opens its statement and evidence.
    await page.click('tr.rg-row:not([hidden]) .gn-row-toggle');
    expanded = await read();
    // The address restores the filter on load, and `#<id>` opens that row.
    await page.goto(base + '/register?family=' + encodeURIComponent(first) + '#' + encodeURIComponent(seen.rows[0].id), {waitUntil: 'load'});
    await page.waitForFunction(() => document.querySelectorAll('tr.rg-row').length > 0, null, {timeout: 15000});
    await page.waitForTimeout(300);
    restored = await read();
  }
  if (SHOT) await page.screenshot({path: SHOT, fullPage: true});
} catch (error) { thrown = String(error); }
await browser.close(); server.close();
const ok = thrown === null && consoleErrors.length === 0 && pageErrors.length === 0
  && failedRequests.length === 0 && badResponses.length === 0 && seen !== null && seen.overflow <= 0;
report({ok, ran: true, width: WIDTH, stamp: STAMP, thrown, consoleErrors, pageErrors,
  failedRequests, badResponses, seen, filtered, expanded, restored, status: STATUS,
  served: SERVED.filter((name) => !BRAND[name])}, ok ? 0 : 1);
