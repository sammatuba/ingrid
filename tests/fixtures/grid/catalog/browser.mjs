/* DATA-1: the data catalog page (`/data`) under the application's own header policy, in a real
   browser. The policy is `style-src 'self'`, which refuses a style attribute written in markup;
   before DATA-1 the page wrote its coverage bars and its lineage indent that way and the browser
   logged one refusal per bar. Serves src/grid/catalog.html with a build stamp written in, its
   design files under /grid/<stamp>/, the vendored fonts, and the built
   /grid-data/<stamp>/catalog.json from --data. Opens the page headless, opens one dataset's
   detail, and reports what the bars and the lineage steps were drawn with, the caption, the
   console errors, page errors, failed requests and bad responses.

     node tests/fixtures/grid/catalog/browser.mjs --root . --data <dir with catalog.json> \
          --stamp 0123456789abcdef --playwright <playwright-core/index.mjs> \
          --chromium <chrome executable> [--width 1280]

   Exit 0 when the page is clean, 1 when not, 3 when no browser is given. Loopback only. */
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const arg = (name, fallback) => { const i = argv.indexOf('--' + name); return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback; };
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', ''));
const WIDTH = Number(arg('width', '1280'));
const STAMP = arg('stamp', '0123456789abcdef');
const PLAYWRIGHT = arg('playwright', ''), CHROMIUM = arg('chromium', '');
const report = (payload, code) => { process.exitCode = code; process.stdout.write(JSON.stringify(payload, null, 1) + '\n', () => process.exit(code)); };
if (!PLAYWRIGHT || !CHROMIUM) report({ok: false, ran: false, reason: 'no browser given'}, 3);

/* The application's own policy (src/api/__init__.py, CONTENT_SECURITY_POLICY). */
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
  + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
const DESIGN = new Set(['catalog.css', 'catalog.js', 'ask.css', 'ask.js', 'shell.css', 'shell.js',
                        'command.css', 'command.js',  // UX-1: the command bar the shell loads
                        'ui.css', 'ui.js']);  // PP-A: the shared design layer the shell loads
const PLAN_SETS = path.join(ROOT, 'tests/fixtures/grid/catalog/bake/views');
const IMMUTABLE = 'public, max-age=31536000, immutable';
const STATUS = {};
// InGRID brand: the icons and manifest every page's head links, answered at the root as the
// application's own routes answer them (src/api BRAND_ROOT_FILES).
const BRAND = {'/favicon.ico': 'image/x-icon', '/favicon.svg': 'image/svg+xml', '/apple-touch-icon.png': 'image/png',
  '/icon-192.png': 'image/png', '/icon-512.png': 'image/png', '/icon-maskable-512.png': 'image/png',
  '/site.webmanifest': 'application/manifest+json'};
const server = createServer((request, response) => {
  const name = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
  const headers = {'Content-Security-Policy': CSP, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'};
  const answer = (status, type, body, cache) => {
    STATUS[name] = status;
    response.writeHead(status, {...headers, 'content-type': type, 'Cache-Control': cache}).end(body);
  };
  const json = (body) => answer(200, 'application/json', body, IMMUTABLE);
  if (name === '/data') {
    answer(200, 'text/html', readFileSync(path.join(ROOT, 'src/grid/catalog.html'), 'utf8')
      .replaceAll('__NOWCAST_STAMP__', STAMP), 'no-cache');
    return;
  }
  const design = name.match(new RegExp('^/grid/' + STAMP + '/([a-z]+\\.(?:css|js))$'));
  if (design && DESIGN.has(design[1])) {
    answer(200, design[1].endsWith('.css') ? 'text/css' : 'text/javascript',
      readFileSync(path.join(ROOT, 'src/grid', design[1])), IMMUTABLE);
    return;
  }
  const font = name.match(new RegExp('^/grid/' + STAMP + '/fonts/([a-z0-9][a-z0-9._-]*\\.woff2)$'));
  if (font) {
    try { answer(200, 'font/woff2', readFileSync(path.join(ROOT, 'src/grid/fonts', font[1])), IMMUTABLE); }
    catch (error) { answer(404, 'application/json', '{"code":"NOT_FOUND"}', 'no-store'); }
    return;
  }
  if (name === `/grid-data/${STAMP}/catalog.json`) { json(readFileSync(path.join(DATA, 'catalog.json'))); return; }
  // The desk assistant's plan set: the catalog fixture's own, else a well-formed empty set.
  const plan = name.match(/^\/grid-data\/(?:[0-9a-f]{16}\/)?views\/([A-Za-z0-9][A-Za-z0-9._-]{0,127})\.json$/);
  if (plan) {
    try { json(readFileSync(path.join(PLAN_SETS, plan[1] + '.json'))); }
    catch (error) { json(JSON.stringify({key: plan[1], views: []})); }
    return;
  }
  // The shared bar's own reads (shell.js), answered empty, as the register harness does.
  if (name === `/grid-data/${STAMP}/advisories.json` || name === `/grid-data/${STAMP}/events.json`) { json('[]'); return; }
  if (name === `/grid-data/${STAMP}/replay.json`) { json('{}'); return; }
  if (name === '/api/alerts/client-config') { answer(200, 'application/json', '{}', 'no-store'); return; }
  if (name === '/api/alerts/inbox') { answer(200, 'application/json', '{"alerts": []}', 'no-store'); return; }
  if (BRAND[name]) { answer(200, BRAND[name], readFileSync(path.join(ROOT, 'src/grid', name.slice(1))), 'no-cache'); return; }
  answer(404, 'application/json', '{"code":"NOT_FOUND"}', 'no-store');
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
const browser = await chromium.launch({executablePath: CHROMIUM, headless: true, args: ['--no-sandbox']});
const page = await (await browser.newContext({viewport: {width: WIDTH, height: 900}})).newPage();
const consoleErrors = [], pageErrors = [], failedRequests = [], badResponses = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', (e) => pageErrors.push(String(e)));
page.on('requestfailed', (r) => failedRequests.push(r.url()));
page.on('response', (r) => { if (r.status() >= 400) badResponses.push(r.status() + ' ' + r.url()); });
let thrown = null, seen = null;
try {
  await page.goto(base + '/data', {waitUntil: 'load'});
  await page.waitForFunction(() => document.querySelectorAll('#list tr[data-set]').length > 0, null, {timeout: 15000});
  await page.click('#list tr[data-set="bake-regions"] a');
  await page.waitForFunction(() => !document.querySelector('#detail').hidden, null, {timeout: 5000});
  seen = await page.evaluate(() => {
    const text = (node) => (node ? node.textContent.replace(/\s+/g, ' ').trim() : '');
    return {
      fills: [...document.querySelectorAll('#list .span .fill')].map((node) => ({
        left: node.getAttribute('data-left'), width: node.getAttribute('data-width'),
        styleLeft: node.style.getPropertyValue('left'), styleWidth: node.style.getPropertyValue('width'),
        drawn: node.getBoundingClientRect().width, track: node.parentElement.getBoundingClientRect().width,
        inner: node.parentElement.clientWidth,
      })),
      // PP-B4: the lineage is a nested list; a step's depth is how many lists it sits in.
      steps: [...document.querySelectorAll('#detail-body .cat-tree li')].map((node) => {
        let depth = 0;
        for (let up = node.parentElement; up && !up.classList.contains('cat-tree'); up = up.parentElement) if (up.tagName === 'UL') depth += 1;
        const link = node.querySelector('a');
        return {depth: String(depth), left: (link || node).getBoundingClientRect().left, style: node.getAttribute('style') || ''};
      }),
      // A style attribute the page's markup wrote would show up as one here; the CSSOM's own
      // values serialise as one too, so only the nodes the page places are allowed to have it.
      styled: [...document.querySelectorAll('#list [style], #detail-body [style]')]
        .filter((node) => !node.matches('.fill')).map((node) => node.outerHTML.slice(0, 120)),
      caption: text(document.querySelector('#caption')),
    };
  });
} catch (error) { thrown = String(error); }
await browser.close(); server.close();
const ok = thrown === null && consoleErrors.length === 0 && pageErrors.length === 0
  && failedRequests.length === 0 && badResponses.length === 0 && seen !== null;
report({ok, ran: true, width: WIDTH, stamp: STAMP, thrown, consoleErrors, pageErrors,
  failedRequests, badResponses, seen, status: STATUS}, ok ? 0 : 1);
