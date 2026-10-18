/* DESK-3: the outlooks page (`/outlooks`) under the application's own header policy, in a real
   browser. Serves src/grid/outlooks.html with a build stamp written in, its stylesheet, its
   script and grid.css under /grid/<stamp>/, the vendored fonts, and one baked
   /grid-data/<stamp>/outlook/index.json — the real builder's output over a fixture archive
   supplied by the test with --index. Opens the page headless, reads what it drew, and reports
   console errors, page errors, failed requests, bad responses and the two answer statuses.

     node tests/fixtures/grid/outlooks/browser.mjs --root . --width 1280 \
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
const DESIGN = new Set(['outlooks.css', 'outlooks.js', 'ask.css', 'ask.js', 'grid.css', 'shell.css', 'shell.js',
                        'command.css', 'command.js',  // UX-1: the command bar the shell loads
                        'ui.css', 'ui.js']);  // platform polish: the shared components
// SHELL-1: the shared bar (ericka-desk)
/* VIEW-1: the desk assistant on the page fetches its plan set from the bake. The committed
   plan sets live in the catalog fixture, so the harness serves the one this page's key names;
   a key the fixture bakes none for gets a well-formed empty set, and the panel draws its own
   absent line. */
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
  if (name === '/outlooks') {
    const page = readFileSync(path.join(ROOT, 'src/grid/outlooks.html'), 'utf8')
      .replaceAll('__NOWCAST_STAMP__', STAMP);
    answer(200, 'text/html', page, 'no-cache'); return;
  }
  const design = name.match(new RegExp('^/grid/' + STAMP + '/(outlooks\\.(?:css|js)|ask\\.(?:css|js)|shell\\.(?:css|js)|command\\.(?:css|js)|ui\\.(?:css|js)|grid\\.css)$'));
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
  if (name === `/grid-data/${STAMP}/outlook/index.json`) {
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
let thrown = null, seen = null;
try {
  await page.goto(base + '/outlooks', {waitUntil: 'load'});
  await page.waitForFunction(() => {
    const empty = document.querySelector('#ol-empty');
    return document.querySelectorAll('.ol-target').length > 0 || (empty && !empty.hidden);
  }, null, {timeout: 15000});
  seen = await page.evaluate(() => {
    const text = (node) => (node ? node.textContent.replace(/\s+/g, ' ').trim() : '');
    const targets = [...document.querySelectorAll('.ol-target')].map((block) => {
      const records = block.querySelector('.ol-records');
      return {
      /* OUTLOOK-7: the plain answer each target opens with, composed from the baked values. */
      first: block.firstElementChild ? block.firstElementChild.className : '',
      answer: (() => {
        const answer = block.querySelector('.ol-answer');
        if (!answer) return null;
        return {
          month: text(answer.querySelector('.ol-answer-month')),
          sentences: [...answer.querySelectorAll('.ol-answer-text')].map((item) => text(item)),
          asof: text(answer.querySelector('.ol-answer-asof')),
        };
      })(),
      /* OUTLOOK-7: the chart of the vintages' values, with each point's direct labels. */
      chart: (() => {
        const chart = block.querySelector('.ol-chart');
        if (!chart) return null;
        return {
          title: text(chart.querySelector('title')),
          source: text(chart.querySelector('.ol-chart-source')),
          points: [...chart.querySelectorAll('.ol-chart-point')].map((point) => {
            const circle = point.querySelector('circle');
            const whisker = point.querySelector('.ol-chart-band');
            return {
              value: text(point.querySelector('.ol-chart-value')),
              bandLabel: text(point.querySelector('.ol-chart-bandtext')),
              date: text(point.querySelector('.ol-chart-date')),
              record: text(point.querySelector('.ol-chart-record')),
              cx: circle.getAttribute('cx'), cy: circle.getAttribute('cy'),
              band: whisker ? {y1: whisker.getAttribute('y1'),
                                y2: whisker.getAttribute('y2')} : null,
            };
          }),
        };
      })(),
      /* OUTLOOK-7: the records fold — the target line and every vintage stay in the DOM, behind
         the one summary control, so the page opens on the answer and not the audit log. */
      records: records ? {
        summary: text(records.querySelector('summary')),
        open: records.hasAttribute('open'),
        series: text(records.querySelector('.ol-series')),
        line: text(records.querySelector('.asof')),
        text: text(records),
        foldsAnswer: !!records.querySelector('.ol-answer'),
        foldsChart: !!records.querySelector('.ol-chart'),
      } : null,
      series: text(block.querySelector('.ol-series')),
      line: text(block.querySelector('.ol-records .asof')),
      /* DESK-6: the baseline track record under the target, when the index carries it. */
      score: (() => {
        const score = block.querySelector('.ol-score');
        if (!score) return null;
        return {
          title: text(score.querySelector('h3')),
          inputs: text(score.querySelector('.ol-score-inputs')),
          horizons: [...score.querySelectorAll('.ol-score-horizon')].map((group) => ({
            slice: text(group.querySelector('.ol-score-slice')),
            headers: [...group.querySelectorAll('th')].map((cell) => text(cell)),
            rows: [...group.querySelectorAll('tbody tr')].map((row) =>
              [...row.querySelectorAll('td')].map((cell) => text(cell))),
          })),
        };
      })(),
      /* Platform polish: the vintages as a table, with the chosen vintage's record beside it. */
      table: [...block.querySelectorAll('.ol-vtable tbody tr')].map((row) => ({
        id: text(row.querySelector('.ol-pick')), selected: row.getAttribute('aria-selected'),
        cells: [...row.querySelectorAll('td')].map((cell) => text(cell))})),
      panels: [...block.querySelectorAll('.ol-detail .ol-vintage')].map((item) => ({
        id: text(item.querySelector('.ol-headline b')), hidden: item.hidden})),
      vintages: [...block.querySelectorAll('.ol-vintage')].map((item) => ({
        id: text(item.querySelector('.ol-headline b')),
        headline: text(item.querySelector('.ol-headline')),
        text: text(item),
        change: text(item.querySelector('.ol-change')),
        causes: [...item.querySelectorAll('.ol-cause')].map((cause) => text(cause)),
        attributions: [...item.querySelectorAll('.ol-attribution')].map((row) => text(row)),
        links: [...item.querySelectorAll('.ol-links a')].map((a) => a.getAttribute('href')),
        linkText: text(item.querySelector('.ol-links')),
      })),
      };
    });
    return {
      title: document.title,
      summary: text(document.querySelector('#ol-summary')),
      plain: (() => {
        const clone = document.body.cloneNode(true);
        clone.querySelectorAll('details, [hidden], script, style, template').forEach((n) => n.remove());
        return text(clone);
      })(),
      empty: {hidden: document.querySelector('#ol-empty').hidden, text: text(document.querySelector('#ol-empty'))},
      caption: text(document.querySelector('#caption')),
      targets,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      hrefs: [...document.querySelectorAll('a')].map((a) => a.getAttribute('href')),
    };
  });
  if (SHOT) await page.screenshot({path: SHOT, fullPage: true});
} catch (error) { thrown = String(error); }
await browser.close(); server.close();
const ok = thrown === null && consoleErrors.length === 0 && pageErrors.length === 0
  && failedRequests.length === 0 && badResponses.length === 0 && seen !== null && seen.overflow <= 0;
report({ok, ran: true, width: WIDTH, stamp: STAMP, thrown, consoleErrors, pageErrors,
  failedRequests, badResponses, seen, status: STATUS,
  served: SERVED.filter((name) => !BRAND[name])}, ok ? 0 : 1);
