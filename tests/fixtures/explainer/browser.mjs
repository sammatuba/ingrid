/* DOC-3: the explainer page under the application's own header policy, in a real browser.
   DOC-4: the systems map chapter (DOC-5: it closes the ideas tier), control by control: a node of
   the systems map, a status filter, a done mark of the path and the two-roles toggle, plus one
   load with storage blocked.
   DOC-4 rework: the served page follows no record link (the site serves no Markdown), so the node
   click is also read for the record's repository path and the page for its count of links.

   Serves src/grid/explain.html with a build stamp written in, explain.css and explain.js under
   /grid/<stamp>/, with the content security policy the application sends (no inline script or
   style), opens it headless, walks every chapter, touches one control of every widget and one
   answer of every quiz, and reports console errors, page errors, failed requests and what it saw.

     node tests/fixtures/explainer/browser.mjs --root . --width 1280 --stamp 0123456789abcdef \
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
const PLAYWRIGHT = arg('playwright', ''), CHROMIUM = arg('chromium', ''), SHOT = arg('shot', '');
const report = (payload, code) => { process.exitCode = code; process.stdout.write(JSON.stringify(payload, null, 1) + '\n', () => process.exit(code)); };  // exit once the write has drained; a payload past 64 KiB was cut
if (!PLAYWRIGHT || !CHROMIUM) report({ok: false, ran: false, reason: 'no browser given'}, 3);

const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
  + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
const SERVED = [];
/* VIEW-1: the desk assistant on the page fetches its plan set from the bake. The committed
   plan sets live in the catalog fixture; the explainer's key has none, so it gets a
   well-formed empty set and the panel draws its own absent line. */
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
  const headers = {'Content-Security-Policy': CSP, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'};
  if (name === '/explain') {
    const page = readFileSync(path.join(ROOT, 'src/grid/explain.html'), 'utf8').replaceAll('__NOWCAST_STAMP__', STAMP);
    response.writeHead(200, {...headers, 'content-type': 'text/html', 'Cache-Control': 'no-cache'}).end(page); return;
  }
  const m = name.match(new RegExp('^/grid/' + STAMP + '/((?:explain|ask|shell|command|ui)\\.(css|js))$'));
  if (m) {
    response.writeHead(200, {...headers, 'content-type': m[2] === 'css' ? 'text/css' : 'text/javascript', 'Cache-Control': 'public, max-age=31536000, immutable'})
      .end(readFileSync(path.join(ROOT, 'src/grid', m[1]))); return;
  }
  // SHELL-1: the shell's vendored fonts (shell.css names them beside itself).
  const font = name.match(new RegExp('^/grid/' + STAMP + '/fonts/([a-z0-9][a-z0-9._-]*\\.woff2)$'));
  if (font) {
    response.writeHead(200, {...headers, 'content-type': 'font/woff2', 'Cache-Control': 'public, max-age=31536000, immutable'})
      .end(readFileSync(path.join(ROOT, 'src/grid/fonts', font[1]))); return;
  }
  const plans = planSet(name);
  if (plans) {
    response.writeHead(200, {...headers, 'content-type': 'application/json',
                             'Cache-Control': 'public, max-age=31536000, immutable'}).end(plans);
    return;
  }
  // SHELL-1: the shared bar's own reads (shell.js), answered empty: no notice for its ticker,
  // sign-in not configured (no key), and an empty alerts list.
  const empty = {['/grid-data/' + STAMP + '/advisories.json']: '[]', ['/grid-data/' + STAMP + '/events.json']: '[]',
                 ['/grid-data/' + STAMP + '/replay.json']: '{}',  // no span: the shell keeps its own window
                 '/api/alerts/client-config': '{}', '/api/alerts/inbox': '{"alerts": []}'};
  if (empty[name]) { response.writeHead(200, {...headers, 'content-type': 'application/json', 'Cache-Control': 'no-store'}).end(empty[name]); return; }
  if (BRAND[name]) {
    response.writeHead(200, {...headers, 'content-type': BRAND[name], 'Cache-Control': 'no-cache'})
      .end(readFileSync(path.join(ROOT, 'src/grid', name.slice(1)))); return;
  }
  response.writeHead(404, {...headers, 'content-type': 'application/json'}).end('{"code":"NOT_FOUND"}');
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
  await page.goto(base + '/explain', {waitUntil: 'load'});
  await page.waitForFunction(() => document.querySelectorAll('.chapter').length > 0, null, {timeout: 15000});
  const chapters = await page.evaluate(() => document.querySelectorAll('.chapter').length);
  const walked = [];
  for (let i = 0; i < chapters; i++) {
    await page.evaluate((n) => document.querySelectorAll('.ex-rail button')[n].click(), i);
    const info = await page.evaluate(() => {
      const c = document.querySelector('.chapter.active');
      return {id: c.id, title: c.querySelector('h2').textContent, widgets: [...c.querySelectorAll('[data-widget]')].map((w) => w.dataset.widget), quizzes: c.querySelectorAll('.quiz').length, terms: c.querySelectorAll('.term').length};
    });
    // one control of every widget: the first button, select, range or checkbox inside it
    for (const w of info.widgets) {
      const sel = `.chapter.active [data-widget="${w}"]`;
      const kind = await page.evaluate((s) => { const el = document.querySelector(s); const c = el.querySelector('button, select, input[type=range], input[type=checkbox], .questions li, .layer, .pt'); return c ? c.tagName + (c.type ? ':' + c.type : '') : null; }, sel);
      if (kind && kind.startsWith('SELECT')) await page.evaluate((s) => { const c = document.querySelector(s + ' select'); c.selectedIndex = (c.selectedIndex + 1) % c.options.length; c.dispatchEvent(new Event('change', {bubbles: true})); }, sel);
      else if (kind && kind.startsWith('INPUT:range')) await page.evaluate((s) => { const c = document.querySelector(s + ' input[type=range]'); c.value = Math.floor(Number(c.max) * 0.7); c.dispatchEvent(new Event('input', {bubbles: true})); }, sel);
      else if (kind) await page.evaluate((s) => { const c = document.querySelector(s).querySelector('button, input[type=checkbox], .questions li, .layer, .pt'); c.click(); }, sel);
    }
    await page.evaluate(() => { const b = document.querySelector('.chapter.active .quiz-opt[data-right="1"]'); if (b) b.click(); });
    const after = await page.evaluate(() => ({quizWhy: (document.querySelector('.chapter.active .quiz-why') || {}).textContent || '', overflow: document.documentElement.scrollWidth - window.innerWidth}));
    walked.push({...info, quizWhy: after.quizWhy.slice(0, 40), overflow: after.overflow});
  }
  // DOC-4: the systems map chapter (DOC-5: the last chapter of the first tier), control by control
  await page.evaluate(() => {
    const i = [...document.querySelectorAll('.chapter')].findIndex((s) => s.getAttribute('data-source') === '00-system.md');
    document.querySelectorAll('.ex-rail button')[i].click();
  });
  const mapChapter = await page.evaluate(() => {
    const out = {id: document.querySelector('.chapter.active').id};
    const map = document.querySelector('.chapter.active [data-widget="systems-map"]');
    const detail = map.querySelector('[data-detail]');
    const before = detail.textContent;
    map.querySelector('.band .node[data-node="compiler"]').click();
    const text = detail.textContent;
    out.node = {clicked: 'compiler', changed: text !== before && text.includes('Known-then'),
      ref: text.includes('src/review/README.md'), links: detail.querySelectorAll('a').length, text: text.slice(0, 40)};
    const filter = map.querySelector('[data-filter="built"]');
    filter.click();
    out.filter = {clicked: 'built', pressed: filter.getAttribute('aria-pressed'), dimmed: map.querySelectorAll('.node.dim').length};
    const rows = document.querySelector('.chapter.active [data-widget="path"]');
    const marker = rows.querySelectorAll('[data-done]')[1];
    const beforeMark = marker.getAttribute('aria-pressed');
    marker.click();
    let stored = 'none';
    try { stored = window.localStorage.getItem('nowcast-explainer-done'); } catch (e) { stored = 'blocked'; }
    out.pathMarker = {file: marker.getAttribute('data-done'), before: beforeMark, after: marker.getAttribute('aria-pressed'), stored};
    const roles = document.querySelector('.chapter.active [data-widget="ai-roles"]');
    const toggle = roles.querySelector('[data-act="example"]');
    const box = roles.querySelector('[data-example]');
    const hidden = box.hidden;
    toggle.click();
    out.roles = {before: hidden, after: box.hidden, changed: hidden !== box.hidden, shown: !box.hidden, text: box.textContent.slice(0, 160)};
    /* the served page: no dead record link anywhere, and the one note that says where records live */
    const href = (a) => a.getAttribute('href') || '';
    out.document = {mdLinks: document.querySelectorAll('a[href*=".md"]').length,
      refLinks: [...document.querySelectorAll('a')].filter((a) => !/^(https?:|\/|#)/.test(href(a))).length,
      refNote: document.querySelectorAll('[data-ref-note]').length,
      paths: [...document.querySelectorAll('.ref-path')].length};
    return out;
  });
  // DOC-4: the same page with storage blocked: the done mark still works and nothing reaches the console
  const blockedPage = await context.newPage();
  const blockedErrors = [];
  blockedPage.on('console', (m) => { if (m.type() === 'error') blockedErrors.push(m.text()); });
  blockedPage.on('pageerror', (e) => blockedErrors.push(String(e)));
  await blockedPage.addInitScript(() => { Object.defineProperty(window, 'localStorage', {configurable: true, get() { throw new Error('storage is blocked'); }}); });
  await blockedPage.goto(base + '/explain', {waitUntil: 'load'});
  const blocked = await blockedPage.evaluate(() => {
    const marker = document.querySelector('[data-widget="path"] [data-done]');
    const before = marker.getAttribute('aria-pressed');
    marker.click();
    let storage = 'readable';
    try { window.localStorage.getItem('x'); } catch (e) { storage = 'blocked'; }
    return {before, after: marker.getAttribute('aria-pressed'), storage};
  });
  blocked.errors = blockedErrors;
  blocked.ok = blockedErrors.length === 0 && blocked.storage === 'blocked' && blocked.before !== blocked.after;
  await blockedPage.close();
  seen = {chapters, walked, mapChapter, blockedStorage: blocked, served: SERVED.filter((n) => !BRAND[n])};
  if (SHOT) { await page.evaluate(() => document.querySelectorAll('.ex-rail button')[7].click()); await page.screenshot({path: SHOT, fullPage: true}); }
} catch (error) { thrown = String(error); }
await browser.close(); server.close();
const ok = thrown === null && consoleErrors.length === 0 && pageErrors.length === 0 && failedRequests.length === 0 && badResponses.length === 0 && seen !== null && seen.walked.every((w) => w.overflow <= 0) && seen.blockedStorage.ok;
report({ok, ran: true, width: WIDTH, stamp: STAMP, thrown, consoleErrors, pageErrors, failedRequests, badResponses, seen}, ok ? 0 : 1);
