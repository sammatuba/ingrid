/* The real check the page's acceptance names: serve the grid page and its baked data over
   loopback under the application's own header policy (content security policy included) and
   load it in a headless browser at one viewport width, then report every console error, page
   error and failed request, plus what the page rendered, where it reaches past the viewport,
   which headers it was served with and which URLs the browser asked for.

     node tests/fixtures/grid/page/browser.mjs --root . --data tests/fixtures/grid/page/data \
          --width 390 --stamp <16 hex> \
          --playwright <playwright-core/index.mjs> --chromium <chrome executable>

   With --stamp (the value `src/api.build_stamp` derives) the harness serves the page, its
   assets and the replay data under the build-stamped URLs the image serves, and `served`
   records what the browser requested. Without it the source page is served unversioned.

   With --hold-node (PERF-4) the node file's answer is kept in flight until the page has drawn
   everything the six small files carry; the report then carries `stage1`, that state as the
   browser rendered it, next to `rendered`, the finished page.

   Exit codes: 0 the page loaded with no console or page error and no sideways overflow, 1 it
   did not, 3 no browser is installed for this machine (the caller decides what to do; this
   packet's test skips).

   Nothing here reaches the network beyond 127.0.0.1, needs a credential or writes to Git: the
   server reads only src/grid and the data directory, and the browser is closed before exit. */
import {createServer} from 'node:http';
import {readFileSync, statSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/page/data')));
/* EXPL-1: the event views (`events/<id>.json`) can live apart from the seven data files; the
   fixture keeps them in `views/` so other suites can copy `data/` untouched. */
const VIEWS = path.resolve(arg('views', path.join(DATA, '..', 'views')));
const WIDTH = Number(arg('width', '1280'));
const HASH = arg('hash', '');
const PLAYWRIGHT = arg('playwright', '');
const CHROMIUM = arg('chromium', '');
/* The build stamp the caller computes (`src/api.build_stamp`). With it the harness serves the
   page and its files the way the application does — the stamp written into the page, the
   assets and the replay data under the stamped prefix — and reports what the browser asked
   for. Without it the source page is served as it lies, unversioned, which is the path a
   fixture-only server takes. */
const STAMP = arg('stamp', '');
const STAMPED = /^[0-9a-f]{16}$/;
/* PERF-4: --hold-node keeps the node file's answer in flight until this harness has read the
   page as it stands without it — the brief, figures, feed, chart and map outline the six small
   files carry, drawn while the one heavy file is still arriving. The report then carries
   `stage1` (that state, tooltip included) next to `rendered` (the finished page). */
const HOLD_NODE = argv.lastIndexOf('--hold-node') >= 0;
/* EXPL-1: --interact clicks through every interaction the plan note lists on the grid page and
   reports what each one changed; --event <id> loads the event page for that id instead (the
   judge's session route answers 404 here, so the page stays in its local mode) and clicks
   through its interactions. */
const INTERACT = argv.lastIndexOf('--interact') >= 0;
const EVENT = arg('event', '');
/* CORP-5: --rules walks the event page's 'rules in force' card instead of the PEDC-shaped
   interactions (the two events differ: one is an outage review, the other a market action). */
const RULES = argv.lastIndexOf('--rules') >= 0;
/* SHELL-1 (merge follow-up): --legacy-cards serves the event page with the markup of the cards
   the redesign took off the live page (tests/fixtures/grid/event/legacy-cards.html: the advisory
   and timeline, the cutoff block, the rules card, the assumption, the judgment) appended before
   `</main>`, the way tests/fixtures/grid/event/render.mjs --legacy-cards does: src/grid/event.js
   still draws each wherever its element exists, so the EXPL-1 and CORP-5 walks keep exercising
   that code in a real browser. The report's `liveIds` says which walked ids the live page itself
   carries, so the test pins the split. Never the page the application serves. */
const LEGACY = argv.lastIndexOf('--legacy-cards') >= 0;
const LIVE_EVENT_IDS = new Set([...readFileSync(path.join(ROOT, 'src/grid/event.html'), 'utf8')
  .replace(/<!--[\s\S]*?-->/g, '').matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]));
const WALKED_EVENT_IDS = ['ev-title', 'timeline', 'cutoff', 'as-big', 'as-more', 'jd-table', 'limits-btn', 'limits',
  'dc-form', 'dc-reason', 'dc-submit', 'dc-status', 'hist-list', 'rules', 'ru-note', 'ru-governs', 'ru-tabs',
  'ru-state', 'adv-quote', 'adv-asof', 'caption'];
/* --shot <path> saves a full-page screenshot after the interactions (for the owner's review). */
const SHOT = arg('shot', '');
/* PERF-6: --play <ticks> presses the dashboard's own Play, lets the clock run that many of its
   450 ms ticks, pauses it and waits for the reads a pause owes; the report's `play` carries the
   alert-inbox requests made while it ran and after it stopped. --cross-days <d1>,<d2> moves the
   page's clock to the other day and back, twice (`GridDesk.goto`, each move awaited until that
   day's node file is drawn); `cross` carries the node and day files asked for meanwhile. Every
   alert-inbox request is listed in `inbox` with its query (`served` keeps the path alone). */
const PLAY = Number(arg('play', '0'));
const CROSS = arg('cross-days', '');
/* --day-steps presses the replay's Next day and Previous day buttons and Shift+arrow keys (the
   day mode only); `days` carries the clock, the day and each button's state after every press,
   and the boxes of the replay's head and day-row controls so the caller can check they fit. */
const DAY_STEPS = argv.lastIndexOf('--day-steps') >= 0;
// DESKFIX-1: open one site's detail card and step to the other assets at its place.
const SIBLINGS = arg('siblings', '');
/* PERF-6: --probe asks the shell's own readers directly (`GNShell.inbox`, `GNShell.dayFile`) on
   the loaded page: the inbox at 00:05 answers 503 with a message, and the first read of
   `days/<PROBE_DAY>.json` answers 500, so the report's `probe` shows what is shared, what is kept
   and that a failure is asked again. */
const PROBE = argv.lastIndexOf('--probe') >= 0;
/* PERF-6: the dashboard folds the briefing panel away (dashboard.css hides `.desk .briefs-mount`),
   so the page does not read its two large files. --show-briefs serves dashboard.css without that
   one selector, the page a layout that draws the panel, so the panel's own run is still walked. */
const SHOW_BRIEFS = argv.lastIndexOf('--show-briefs') >= 0;
const FOLDED_BRIEFS = ', .desk .briefs-mount { display: none !important; }';
const PROBE_DAY = '2026-09-22';
let probeDayFailed = false;
const INBOX = [];
const NODE_FILE = /\/nodes-\d{4}-\d{2}-\d{2}\.json$/;
let releaseNode = null;
const nodeHeld = new Promise((resolve) => { releaseNode = resolve; });

const TYPES = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
               '.json': 'application/json', '.geojson': 'application/geo+json',
               '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png',
               '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json'};
// InGRID brand: the icons and manifest every page's head links, served at the root from the
// design tree and revalidating, as the application's own routes do (src/api BRAND_ROOT_FILES).
const BRAND = new Set(['/favicon.ico', '/favicon.svg', '/apple-touch-icon.png', '/icon-192.png',
                       '/icon-512.png', '/icon-maskable-512.png', '/site.webmanifest']);

function report(payload, code) {
  /* The payload can pass 64 KiB; a pipe takes that much before the write blocks, and
     process.exit() right after console.log() drops the rest. Exit only once the write
     has drained. */
  process.exitCode = code;
  process.stdout.write(JSON.stringify(payload, null, 1) + '\n', () => process.exit(code));
}

if (!PLAYWRIGHT || !CHROMIUM) {
  report({ok: false, ran: false, reason: 'no browser given: pass --playwright and --chromium'},
         3);
}

/* ---------- the header policy, as the application applies it ---------- */
/* A clean console only means something under the policy production serves with: the content
   security policy admits no inline script or style, so a page that writes one logs here the
   way it logs in the image. The application's rule is `src/api/__init__.py` (`cache_control`,
   from the class each route declares on its answer); this file has no Python, so it restates
   the classes — and the report below carries what it sent, so tests/test_grid_page.py
   compares each reported path with the answer the application's own route produces for it and
   fails if either side drifts. The three classes are the application's: a file under the
   build stamp is immutable, the HTML pages revalidate, everything else — the unversioned
   names the image still serves included — is no-store. Unlike the application this harness is
   its own allow-list: it answers 200 only for a file it has just stat'ed, so with --stamp a
   stamped URL it serves is a versioned file by construction. */
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
  + "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
/* SHELL-1 (merge follow-up): since ericka-desk D1 every grid page the application renders with
   `page_response` (`/` and `/event/<id>` here) carries SIGN_IN_POLICY, so the shared shell can
   sign in on any page; `/desk` (a plain file answer), the data, the design files and the API
   answers keep CSP. The policy check below compares both with the application's own answers. */
const SIGN_IN_CSP = "default-src 'self'; script-src 'self' https://apis.google.com; style-src 'self'; "
  + "connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com "
  + "https://apis.google.com; frame-src https://*.firebaseapp.com https://apis.google.com "
  + "https://accounts.google.com; img-src 'self'; object-src 'none'; base-uri 'none'; "
  + "frame-ancestors 'none'; form-action 'self'";
const IMMUTABLE = 'public, max-age=31536000, immutable';

function cacheClassFor(name, status = 200) {
  if (status !== 200) return 'no-store';
  /* `/desk` is not served here; it is reported so the caller compares the application's own
     class for its page route too. */
  if (name === '/' || name === '/desk' || name.startsWith('/event/') || BRAND.has(name)) return 'no-cache';
  const first = name.split('/')[2] || '';
  const family = name.startsWith('/grid/') || name.startsWith('/grid-data/');
  return family && STAMPED.test(first) ? IMMUTABLE : 'no-store';
}

function policyFor(name, status = 200) {
  return {
    'Cache-Control': cacheClassFor(name, status),
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': status === 200 && (name === '/' || name.startsWith('/event/'))
      ? SIGN_IN_CSP : CSP,
  };
}

/* The paths the report carries the policy for; the test compares each with the app's own.
   `/health` is the page's own warm-up request (PERF-5): the application answers it `no-store`,
   and it is listed here so the comparison covers what the browser asked for. */
const POLICY_PATHS = ['/', '/desk', '/health', '/grid/grid.js', '/grid-data/regions.json'];
// SHELL-1 (merge follow-up): the event page is a page_response too (SIGN_IN_POLICY), so its policy
// is compared with the application's own answer as well.
POLICY_PATHS.push('/event/syn-bay-unit-2-trip');
if (STAMP) {
  POLICY_PATHS.push(`/grid/${STAMP}/grid.js`, `/grid/${STAMP}/fonts/inter-latin-400-normal.woff2`,
                    `/grid-data/${STAMP}/regions.json`);
}

/* ---------- the page, over loopback, exactly as the image serves it ---------- */
/* What the browser asked for, so the caller can prove the page fetched the stamped files. */
const SERVED = [];
const STUB = {saved: 0};
const stampedGrid = STAMP ? new RegExp('^/grid/' + STAMP + '/') : null;
const stampedData = STAMP ? new RegExp('^/grid-data/' + STAMP + '/') : null;
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

const server = createServer(async (request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1');
  const name = decodeURIComponent(url.pathname);
  SERVED.push(name);
  if (name === '/api/alerts/inbox') INBOX.push(url.search);
  /* VIEW-1: the desk assistant's plan set, served from the committed plan sets. */
  const plans = planSet(name);
  if (plans) {
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'application/json'})
      .end(plans);
    return;
  }
  /* SHELL-1 (merge follow-up): the shared shell's own reads and the dashboard's new ones, answered
     the way tests/fixtures/grid/book/browser.mjs answers them, but only where this fixture bakes
     no file of that name: the replay index (replay.json) with no span, so the shell keeps its own
     21-29 Sep window; the outage tracker's bake (outages.json) well formed with no record, so its
     card lists none; sign-in not configured (no key); and an empty alert inbox. */
  const stampedName = STAMP && name.startsWith('/grid-data/' + STAMP + '/') ? name.slice(('/grid-data/' + STAMP + '/').length) : null;
  const empty = {
    'replay.json': {},
    'outages.json': {schema: 'outages/1', source: 'advisories', blocker: 'harness: no outage bake in this fixture',
                     span: [], lag_basis: '', records: []},
  };
  if (stampedName && Object.hasOwn(empty, stampedName) && !statSafe(path.join(DATA, stampedName))) {
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'application/json'})
      .end(JSON.stringify(empty[stampedName]));
    return;
  }
  if (PROBE && name === '/api/alerts/inbox' && url.searchParams.get('at') === '2026-09-21T00:05') {
    response.writeHead(503, {...policyFor(name, 503), 'content-type': 'application/json'})
      .end('{"message": "harness: the inbox is down at 00:05"}');
    return;
  }
  if (PROBE && !probeDayFailed && name.endsWith('/days/' + PROBE_DAY + '.json')) {
    probeDayFailed = true;
    response.writeHead(500, {...policyFor(name, 500), 'content-type': 'application/json'}).end('{"code":"HARNESS"}');
    return;
  }
  if (name === '/api/alerts/client-config' || name === '/api/alerts/inbox') {
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'application/json'})
      .end(name === '/api/alerts/inbox' ? '{"alerts": []}' : '{}');
    return;
  }
  /* DESKFIX-1: the entity preview card ui.js asks for when the pointer rests on an entity link
     (the state card's HVDC rows): the application's `/api/desk/preview/<kind>/<id>` (src/desk),
     answered here in its shape with no figures, so a hover after a click is not a 404. */
  const preview = name.match(/^\/api\/desk\/preview\/([a-z]+)\/([^/]+)$/);
  if (preview) {
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'application/json'})
      .end(JSON.stringify({kind: preview[1], id: decodeURIComponent(preview[2]), title: decodeURIComponent(preview[2]), subtitle: 'harness',
                           href: '/?' + preview[1] + '=' + preview[2], grid: null, facts: [], sparks: [], sources: []}));
    return;
  }
  /* The node file is held here, not at the page: with --hold-node the browser renders the page
     the six small files draw while this answer is still on its way. */
  if (HOLD_NODE && NODE_FILE.test(name)) await nodeHeld;
  let file = null, body = null;
  if (name === '/') {
    // The application serves this page with the build stamp written in; the harness makes the
    // same substitution on the source page when a stamp is given, so the browser asks for the
    // same versioned URLs the image's page does.
    const page = readFileSync(path.join(ROOT, 'src/grid/index.html'), 'utf8');
    body = STAMP ? page.replaceAll('__NOWCAST_STAMP__', STAMP) : page;
  } else if (name.startsWith('/event/')) {
    let page = readFileSync(path.join(ROOT, 'src/grid/event.html'), 'utf8');
    if (LEGACY) {
      page = page.replace('</main>', readFileSync(path.join(ROOT, 'tests/fixtures/grid/event/legacy-cards.html'), 'utf8') + '</main>');
    }
    body = STAMP ? page.replaceAll('__NOWCAST_STAMP__', STAMP) : page;
  } else if (name === '/demo/session' || name.startsWith('/v1/tenants/')) {
    /* EXPL-1: a stub of the judge's routes, enough for the page's own flow to save one decision
       and read it back, so the history card is populated and its click can be read. The shapes
       are the ones src/grid/event-api.js reads; nothing here is the review API. */
    const json = (status, body) => response.writeHead(status, {...policyFor(name, status), 'content-type': 'application/json'}).end(JSON.stringify(body));
    if (name === '/demo/session') return json(200, {id_token: 'stub', tenant: 'demo-judge', event_case: 'stub-case', event_seeded_at: '2026-09-21T00:10:00+08:00'});
    if (name.endsWith('/prepare')) return json(200, {heads: {outlook: null}, task: {record_kind: 'ReviewTask', record_id: 't1', revision_id: 'r1', content_digest: 'd1',
      payload: {snapshot_ref: {content_digest: 's1'}, assumption_ref: {record_id: 'a1'}, assumption_definition: {value: {quantity_kind: 'available_capacity', unit: 'MW'}}}}});
    if (name.endsWith('/reviews')) { STUB.saved += 1; return json(200, {outlook_ref: {record_kind: 'OutlookRevision', record_id: 'o1', revision_id: 'r1', content_digest: 'o1'}}); }
    if (name.endsWith('/read')) {
      let body = '';
      request.on('data', (chunk) => { body += chunk; });
      request.on('end', () => {
        let ref = null;
        try { ref = JSON.parse(body).ref; } catch (e) { ref = null; }
        if (ref && ref.record_kind === 'ReviewDecision') {
          json(200, {record_kind: 'ReviewDecision', record_id: ref.record_id, payload: {disposition: 'retain', reviewed_at: '2026-10-15T10:00:00+00:00',
            task_ref: {record_kind: 'CompiledTask', record_id: 'task-stub-1'}, judgment_ref: null}});
        } else json(200, {recorded_at: '2026-10-15T10:00:00+00:00'});
      });
      return;
    }
    if (name.endsWith('/history')) return json(200, Array.from({length: STUB.saved}, (_, i) => ({payload: {reviewed_at: '2026-10-15T10:0' + i + ':00+00:00',
      decision_ref: {record_kind: 'ReviewDecision', record_id: 'decision-stub-' + (i + 1), revision_id: 'r1', content_digest: 'd' + (i + 1)},
      difference: {kind: 'no_change', old_value: {value: '180', unit: 'MW'}, rationale: 'stub reason ' + (i + 1)}}})));
    return json(404, {code: 'NOT_FOUND'});
  } else if (stampedGrid && stampedGrid.test(name)) {
    file = path.join(ROOT, 'src/grid', name.slice(('/grid/' + STAMP + '/').length));
  } else if (name.startsWith('/grid/')) {
    file = path.join(ROOT, 'src/grid', name.slice(6));
  } else if (stampedData && stampedData.test(name)) {
    const rest = name.slice(('/grid-data/' + STAMP + '/').length);
    file = path.join(!statSafe(path.join(DATA, rest)) && statSafe(path.join(VIEWS, rest)) ? VIEWS : DATA, rest);
  } else if (name.startsWith('/grid-data/')) {
    const rest = name.slice(11);
    file = path.join(!statSafe(path.join(DATA, rest)) && statSafe(path.join(VIEWS, rest)) ? VIEWS : DATA, rest);
  }
  // InGRID brand: the root icons and manifest are design files answered at the root.
  if (BRAND.has(name)) file = path.join(ROOT, 'src/grid', name.slice(1));
  // The page's own warm-up (PERF-5): the application's `/health`, answered here so the browser
  // run covers the request the real page makes and its console stays clean.
  if (name === '/health') {
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'application/json'})
      .end('{"status":"ok","mode":"local","storage_checked":false}');
    return;
  }
  if (body === null && (file === null || !(file.startsWith(ROOT) || file.startsWith(VIEWS)) || !statSafe(file))) {
    response.writeHead(404, {...policyFor(name, 404), 'content-type': 'application/json'})
      .end('{"code":"NOT_FOUND"}');
    return;
  }
  if (SHOW_BRIEFS && body === null && file && file.endsWith(path.join('src', 'grid', 'dashboard.css'))) {
    const css = readFileSync(file, 'utf8');
    if (!css.includes(FOLDED_BRIEFS)) throw new Error('--show-briefs: dashboard.css no longer folds the panel with ' + FOLDED_BRIEFS);
    body = css.replace(FOLDED_BRIEFS, ' { display: none !important; }');
    response.writeHead(200, {...policyFor(name, 200), 'content-type': 'text/css'}).end(body);
    return;
  }
  response.writeHead(200, {...policyFor(name, 200),
                           'content-type': body !== null ? 'text/html'
                             : TYPES[path.extname(file)] || 'application/octet-stream'})
    .end(body !== null ? body : readFileSync(file));
});
function statSafe(file) {
  try {
    return statSync(file).isFile();
  } catch {
    return false;
  }
}
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;

/* ---------- the browser ---------- */
const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
const browser = await chromium.launch({
  executablePath: CHROMIUM, headless: true,
  // The harness runs inside a container-like sandbox; the browser is throwaway and reads only
  // loopback. Chromium's own sandbox needs privileges this seat does not have.
  args: ['--no-sandbox'],
});
const context = await browser.newContext({viewport: {width: WIDTH, height: 900}});
const page = await context.newPage();
const consoleErrors = [], pageErrors = [], failedRequests = [], badResponses = [];
page.on('console', (message) => {
  if (message.type() === 'error') {
    const at = message.location();
    consoleErrors.push(at && at.url ? `${message.text()} (${at.url})` : message.text());
  }
});
page.on('pageerror', (error) => pageErrors.push(String(error)));
/* PERF-6: every request the page made, as the browser saw it — including the ones its HTTP cache
   answered (a stamped file is immutable, so a repeat never reaches the server and `served`
   alone would not show it). */
const REQUESTED = [];
page.on('request', (request) => { const u = new URL(request.url()); if (u.host === new URL(base).host) REQUESTED.push(u.pathname); });
page.on('requestfailed', (request) => failedRequests.push(`${request.url()} ${request.failure()?.errorText}`));
page.on('response', (response) => {
  if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`);
});

let rendered = null;
let stage1 = null;
let thrown = null;
/* ATG-8: the map is ATG-6's canvas, mounted by the page. A canvas holds no element per site, so
   the map's readings are the module's own record of what it drew (`GridDesk.mapPanel`, its
   `snapshot()`) and the page's own ring overlay; the pointer is put on a site or a link at the
   spot the module painted it, which is what a reader touches. Nothing here re-derives the
   drawing: the paints themselves are the module's own harness' business
   (tests/fixtures/grid/map/harness.mjs). */
const MAP_READ = `(() => {
  const panel = window.GridDesk && window.GridDesk.mapPanel;
  const s = panel && panel.snapshot ? panel.snapshot() : null;
  const rows = s ? (s.located || []) : [];   // PP-B5: the unlocated sites are listed apart, never drawn
  const tip = document.querySelector('#map .gmap-tip');
  const canvas = panel && panel.canvas ? panel.canvas.getBoundingClientRect() : null;
  return {
    mounted: !!panel, land: s ? s.land : 0, sites: rows.length, pending: s ? (s.pending || []).length : 0,
    siteFills: rows.map((r) => r.fill), links: s ? (s.links || []) : [],
    linkLabels: s ? (s.links || []).map((l) => l.label) : [],
    messages: s ? (s.messages || []).map((m) => m.code) : [],
    clock: s ? s.clock : null, scope: s ? s.scope : null,
    tip: tip && !tip.hidden ? tip.innerHTML : null,
    // ATG-8 rework: the panel a held run read at stage 1 — the finished page must still be that
    // same panel (the node file's layer is handed over with setNodes, never remounted). Null
    // when no stage-1 read was taken.
    sameAsStage1: window.__stage1Panel === undefined ? null : window.__stage1Panel === panel,
    marks: [...document.querySelectorAll('#map-marks .map-mark')].map((n) => n.className),
    canvas: canvas ? {left: canvas.left, top: canvas.top, width: canvas.width, height: canvas.height} : null,
    rows: rows.map((r) => ({code: r.code, kind: r.kind, x: r.x, y: r.y, r: r.r, pending: r.pending, value: r.value})),
  };
})()`;
const mapRead = () => page.evaluate(MAP_READ);
/* What the page's own document shows at one moment; the map's block is merged in from the
   module's record, so the staged state and the finished page are read the same way. */
const PAGE_READ = () => ({
  title: document.title,
  clock: document.getElementById('clock-time').textContent,
  briefTitle: document.getElementById('brief-title').textContent,
  briefText: document.getElementById('brief-text').textContent,
  briefAsOf: document.getElementById('brief-asof').textContent,
  figuresAsOf: document.getElementById('figures-asof').textContent,
  figureRows: [...document.querySelectorAll('#figures tbody tr')].map((row) => row.innerText.replace(/\s+/g, ' ').trim()),
  feedCount: document.getElementById('feed-count').textContent,
  feedItems: document.querySelectorAll('#feed tr').length,
  feedText: document.getElementById('feed').innerText.replace(/\s+/g, ' ').trim().slice(0, 400),
  reviews: document.querySelectorAll('#review-list li').length,
  // FRONT-1: the findings feed drawn by src/grid/briefs.js. Each child of the list is what the
  // reader sees: a single finding, or one row for a run that names its span and its count with
  // its members behind the native `<details>`; `findings` counts every member drawn.
  findings: (() => {
    const list = document.querySelector('.briefs .b-entries');
    if (!list) return null;
    const rows = [...list.children];
    const countNode = document.querySelector('.briefs .b-count');
    const titleNode = document.querySelector('.briefs .b-title');
    return {
      count: countNode ? countNode.textContent : '',
      title: titleNode ? titleNode.textContent : '',
      drawn: rows.length,
      findings: list.querySelectorAll('.b-entry').length,
      singles: rows.filter((row) => row.classList.contains('b-entry')).length,
      groups: rows.filter((row) => row.classList.contains('b-group')).map((row) => {
        const summary = row.querySelector('summary');
        const box = row.querySelector('details');
        return {text: summary ? summary.textContent.replace(/\s+/g, ' ').trim() : '',
                open: !!(box && box.open), rows: row.querySelectorAll('.b-entry').length};
      }),
      // FRONT-1 rework, finding 2: a row that carries a review link is drawn as its own row,
      // so its link is on screen and never behind a run's disclosure.
      reviewRows: rows.filter((row) => row.classList.contains('b-entry')
        && row.querySelector('a.b-review')).length,
      foldedReviews: rows.filter((row) => row.classList.contains('b-group'))
        .reduce((n, row) => n + row.querySelectorAll('a.b-review').length, 0),
    };
  })(),
  mapLoading: document.querySelector('.map-wrap').classList.contains('loading'),
  mapPricing: document.querySelector('.map-wrap').classList.contains('pricing'),
  chartPoints: document.querySelectorAll('#chart path').length,
  chartLabels: [...document.querySelectorAll('#chart text.label')].map((node) => node.textContent),
  caption: document.getElementById('caption').textContent,
  csv: getComputedStyle(document.body).backgroundColor,
  viewport: window.innerWidth,
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  // The replay control, so the caller can check it stays inside the viewport and usable.
  // SHELL-1 (merge follow-up): on a phone the shared bar gives the slider's room to the step
  // buttons and the clock (shell.css and dashboard.css hide `#scrub` at 760px and below, by
  // design), so `shown` says whether the slider is drawn and `steps` carries the boxes of the
  // controls that replace it there.
  scrub: (() => {
    const node = document.getElementById('scrub');
    const box = node.getBoundingClientRect();
    return {left: Math.round(box.left), right: Math.round(box.right), width: Math.round(box.width),
            shown: node.checkVisibility()};
  })(),
  steps: [...document.querySelectorAll('.clock [data-step], .clock #play, #clock-time')].map((node) => {
    const box = node.getBoundingClientRect();
    return {name: node.id || 'step' + node.dataset.step, shown: node.checkVisibility(), left: Math.round(box.left),
            right: Math.round(box.right), top: Math.round(box.top), width: Math.round(box.width), height: Math.round(box.height)};
  }),
  // Which elements reach past the viewport, widest first: empty when nothing does.
  // SHELL-1 (merge follow-up): an element inside a container that clips or scrolls sideways
  // (computed overflow-x other than visible) whose own box ends inside the viewport cannot widen
  // the document: the shared bar's section list scrolls sideways on a phone by design
  // (`.gn-nav { overflow-x: auto }`) and its notice ticker runs inside a clipped track. Those are
  // listed in `clipped` with the container that holds them, so the caller pins which containers
  // these are; everything else still counts, and `overflow` (the document's own sideways scroll)
  // is the hard check.
  ...(() => {
    const label = (node) => `${node.tagName.toLowerCase()}${node.id ? '#' + node.id : ''}${node.className && typeof node.className === 'string' ? '.' + node.className.split(/\s+/).join('.') : ''}`;
    const holder = (node) => {
      for (let up = node.parentElement; up && up !== document.body; up = up.parentElement) {
        if (getComputedStyle(up).overflowX !== 'visible' && up.getBoundingClientRect().right <= window.innerWidth + 1) return up;
      }
      return null;
    };
    const past = [...document.querySelectorAll('body *')]
      .filter((node) => node.getBoundingClientRect().right > window.innerWidth + 1)
      .sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right);
    const wide = [], clipped = new Set();
    for (const node of past) {
      const box = holder(node);
      if (box) clipped.add(label(box));
      else wide.push(`${label(node)} right=${Math.round(node.getBoundingClientRect().right)}`);
    }
    return {wide: wide.slice(0, 6), clipped: [...clipped].sort()};
  })(),
  // SHELL-1 (merge follow-up): the blocks the redesigned dashboard folds away (dashboard.css:
  // the front strip, the brief and grids table, the chart and its day path, the briefing panel)
  // keep their markup for the scripts; which of them, and of the cards that replace them, the
  // reader sees. (The ask mount floats in the shared dock: tests/test_grid_shell.py reads it.)
  shown: Object.fromEntries(['front', 'brief-text', 'figures', 'chart', 'path-wrap', 'briefs-mount',
                             'feed', 'map', 'outages', 'overview', 'dash-alerts', 'clock-time']
    .map((id) => { const node = document.getElementById(id); return [id, node ? node.checkVisibility() : null]; })),
  mapWidth: Math.round(document.getElementById('map').getBoundingClientRect().width),
  // EXPL-2: the path panel, hidden without a vector table
  path: (() => {
    const wrap = document.getElementById('path-wrap');
    return {hidden: !wrap || wrap.hidden, steps: document.querySelectorAll('#path circle.p-step').length,
            types: document.querySelectorAll('#path circle.p-type').length,
            title: wrap && !wrap.hidden ? document.getElementById('path-title').textContent : null,
            asof: wrap && !wrap.hidden ? document.getElementById('path-asof').textContent : null};
  })(),
});
async function snapshot() {
  const base = await page.evaluate(PAGE_READ);
  const map = await mapRead();
  return Object.assign(base, {
    map, mapSites: map.sites, siteFills: map.siteFills, landPaths: map.land,
    pendingSites: map.pending, linkLabels: map.linkLabels, tip: map.tip,
  });
}
/* Reading one site's tooltip means putting the pointer on its dot: the tooltip is the module's
   own claim about that site, and it is what must stay unknown while the node file has not
   arrived. A canvas holds no element per site, so the pointer is moved to the spot the module's
   own record says it painted the first located site. */
async function hoverFirstSite() {
  // SHELL-1 (merge follow-up): the redesigned dashboard opens on its "Grid now" cards, so the map
  // starts below the first screen; it is scrolled into view first, as a reader would, and the
  // canvas is read after the scroll.
  await page.evaluate(() => document.getElementById('map').scrollIntoView({block: 'center'}));
  const map = await mapRead();
  const target = map.rows.find((row) => !row.pending);
  if (!target || !map.canvas) return;
  await page.mouse.move(map.canvas.left + target.x, map.canvas.top + target.y);
}
/* A click on the canvas at the spot the module painted a site or a link: the module resolves it
   under the current transform and calls the page's own openers. Where several sites share one
   position the module cycles that stack on repeated clicks, so a site is asked for by clicking
   until the panel it opened on names it — what a reader tapping the same spot gets. */
async function clickMapTarget(kind, id) {
  // SHELL-1 (merge follow-up): centred, so the shared bar pinned at the top never covers the spot.
  await page.evaluate(() => document.getElementById('map').scrollIntoView({block: 'center'}));
  const map = await mapRead();
  const target = kind === 'site' ? map.rows.find((row) => row.code === id)
    : (map.links || []).find((link) => link.id === id);
  if (!target || !map.canvas) return false;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await page.mouse.click(map.canvas.left + target.x, map.canvas.top + target.y);
    const body = (await text('#d-body')) || '';
    if (body.includes(id)) return true;
  }
  return false;
}
let interactions = null;
let siblings = null;
let step = null;
let play = null;
let cross = null;
let days = null;
let probe = null;
const text = (selector) => page.evaluate((sel) => { const n = document.querySelector(sel); return n ? n.textContent.replace(/\s+/g, ' ').trim() : null; }, selector);
const count = (selector) => page.evaluate((sel) => document.querySelectorAll(sel).length, selector);
const hidden = (selector) => page.evaluate((sel) => { const n = document.querySelector(sel); return n ? n.hidden : null; }, selector);
/* SHELL-1 (merge follow-up): the redesigned dashboard folds the brief, the grids table and the
   chart with its day path away (dashboard.css) and keeps their markup and handlers for the
   scripts. A reader cannot press what is not drawn, so a step on one of them is the element's own
   click dispatched in the page (the same handler a pointer reaches), and the selector is recorded
   in `dispatched`; the test pins that list to exactly the folded elements, so a block that comes
   back on screen is walked with the real pointer again. Everything drawn keeps its real click. */
const dispatched = [];
async function press(selector) {
  const shown = await page.evaluate((sel) => { const n = document.querySelector(sel); return !!n && n.checkVisibility(); }, selector);
  if (shown) { await page.click(selector); return; }
  dispatched.push(selector);
  await page.evaluate((sel) => document.querySelector(sel).click(), selector);
}
/* The chart's own handlers place the pointer by its x against the drawn box (grid.js wireChart);
   folded, the box is empty and the handler falls back to its 300 px minimum width, so the event is
   dispatched at the same fraction of that width the pointer used on the drawn chart. */
async function pointAtChart(type, fraction) {
  const shown = await page.evaluate(() => document.getElementById('chart').checkVisibility());
  if (shown) {
    await page.locator('#chart').scrollIntoViewIfNeeded();
    const box = await page.locator('#chart').boundingBox();
    if (type === 'click') await page.mouse.click(box.x + box.width * fraction, box.y + box.height * 0.5);
    else await page.mouse.move(box.x + box.width * fraction, box.y + box.height * 0.5);
    return;
  }
  dispatched.push('#chart ' + type);
  await page.evaluate(([kind, frac]) => {
    const svg = document.getElementById('chart');
    const box = svg.getBoundingClientRect();
    const width = Math.max(300, box.width), height = Math.max(140, box.height);
    svg.dispatchEvent(new MouseEvent(kind, {bubbles: true, clientX: box.left + width * frac, clientY: box.top + height * 0.5}));
  }, [type, fraction]);
}
async function interactGrid() {
  const out = {};
  // 1. a message in the feed: the clock moves to the message's time (so the clock is first put
  //    elsewhere, at 14:30, where the feed still lists the trip), the site it names is marked
  //    on the map, its detail opens
  await page.evaluate(() => { const s = document.getElementById('scrub'); s.value = 174; s.dispatchEvent(new Event('input', {bubbles: true})); });
  const clockBefore = await text('#clock-time');
  await page.evaluate(() => { const li = [...document.querySelectorAll('#feed tr')].find((n) => n.textContent.includes('Trip')); li.click(); });
  out.message = {detail: await text('#d-title'), clock: await text('#clock-time'), clockBefore, focused: await count('#map-marks .map-mark.site'),
                 selected: await count('#feed tr.sel'), body: (await text('#d-body')).slice(0, 300)};
  // 1a2. hover and focus: the titles the plan note's hover column promises
  out.hover = {
    figure: await page.getAttribute('#figures tbody tr[data-grid="CVIS"] td[data-series="price"]', 'title'),
    feed: await page.getAttribute('#feed tr >> nth=0', 'title'),
    header: await page.getAttribute('#figures thead th.num >> nth=0', 'title'),
  };
  // 1b. the narrative: each entity is a link to its element (a figure, a link, a message)
  await page.evaluate(() => { const b = document.querySelector('.grids button[data-grid="CVIS"]'); if (b) b.click(); });
  out.narrative = {entities: await count('#brief-text .ent')};
  if (await count('#brief-text .ent[data-figure]')) {
    await press('#brief-text .ent[data-figure]');
    out.narrative.figure = {detail: await text('#d-title'), chartTitle: await text('#chart-title')};
  }
  if (await count('#brief-text .ent[data-link]')) {
    await press('#brief-text .ent[data-link]');
    out.narrative.link = await text('#d-title');
  }
  if (await count('#brief-text .ent[data-adv]')) {
    await press('#brief-text .ent[data-adv]');
    out.narrative.message = await text('#d-title');
  }
  // 1c. a message whose words fit two sites: the page names both and selects neither
  const ambiguous = await page.evaluate(() => { const li = [...document.querySelectorAll('#feed tr')].find((n) => n.textContent.includes('planned outage until')); return li ? li.id.slice(4) : null; });
  if (ambiguous) {
    await press('#feed tr#adv-' + ambiguous);
    out.ambiguous = {detail: await text('#d-title'), body: (await text('#d-body')).slice(0, 260), focused: await count('#map-marks .map-mark.site'), candidates: await count('#d-body .d-link[data-site]')};
  }
  // 2. a figure cell: the chart shows that series for that grid, the cell stays marked
  await press('#figures tbody tr[data-grid="CLUZ"] td[data-series="flow"]');
  out.figure = {chartTitle: await text('#chart-title'), chartAsOf: await text('#chart-asof'), detail: await text('#d-title'),
                marked: await count('#figures td.sel'), grid: await page.evaluate(() => document.querySelector('.grids button[aria-pressed="true"]').dataset.grid)};
  // 3. a site dot: name, code, sparklines, its messages. A canvas holds no element per site, so
  //    the click is a real pointer click at the spot the module painted the site — and where
  //    sites share a position the module cycles its stack, which the helper walks.
  await clickMapTarget('site', 'SYN-BAY-1');
  out.site = {detail: await text('#d-title'), body: (await text('#d-body')).slice(0, 300), sparks: await count('#d-body .spark'),
              messages: await count('#d-body .d-msgs li'), focused: await count('#map-marks .map-mark.site')};
  // 4. a link: flow now and direction, the chart shows the flow. The click is a real pointer
  //    click at the spot the module painted the link's own midpoint mark, within its hit slack.
  await clickMapTarget('link', 'VISLUZ1');
  out.link = {detail: await text('#d-title'), chartTitle: await text('#chart-title'), body: (await text('#d-body')).slice(0, 200),
              congestedMarks: await count('#chart rect.congested-mark')};
  // the whole replay span on request: the site detail lists every message that names the site
  await clickMapTarget('site', 'SYN-BAY-1');
  out.span = {day: await count('#d-body .d-msgs li'), hasShowAll: await count('#d-body [data-span="all"]')};
  if (out.span.hasShowAll) {
    await press('#d-body [data-span="all"]');
    out.span.all = await count('#d-body .d-msgs li');
    out.span.note = await text('#d-body .d-source');
    // open the message of another day from that list
    await page.evaluate(() => { const li = [...document.querySelectorAll('#d-body .d-msgs li')].find((n) => n.textContent.includes('09-22')); if (li) li.click(); });
    out.span.otherDay = {detail: await text('#d-title'), clock: await text('#clock-time')};
  }
  if (SHOT) await page.screenshot({path: SHOT, fullPage: WIDTH < 800});
  // 5. EXPL-2: the day's path per grid, moving with the clock; a real pointer click on the latest
  //    point (the one the current-point overlay sits on) opens its message
  out.path = {perGrid: {}, hidden: await hidden('#path-wrap')};
  for (const grid of ['CLUZ', 'CVIS', 'CMIN']) {
    await page.evaluate((g) => document.querySelector('.grids button[data-grid="' + g + '"]').click(), grid);
    await page.evaluate(() => { const s = document.getElementById('scrub'); s.value = 0; s.dispatchEvent(new Event('input', {bubbles: true})); });
    const atStart = await count('#path circle.p-step');
    await page.evaluate(() => { const s = document.getElementById('scrub'); s.value = s.max; s.dispatchEvent(new Event('input', {bubbles: true})); });
    const atEnd = await count('#path circle.p-step');
    const title = await text('#path-title');
    out.path.perGrid[grid] = {atStart, atEnd, title};
  }
  await page.evaluate(() => document.querySelector('.grids button[data-grid="CVIS"]').click());
  const pathShown = await page.evaluate(() => document.getElementById('path').checkVisibility());
  let last = null;
  if (pathShown) {
    await page.locator('#path').scrollIntoViewIfNeeded();
    last = await page.locator('#path circle.p-step').last().boundingBox();
    if (last) await page.mouse.click(last.x + last.width / 2, last.y + last.height / 2);
  } else if (await count('#path circle.p-step')) {
    // Folded: the latest point's own click, which the path's handler reads off its target.
    dispatched.push('#path circle.p-step:last');
    await page.evaluate(() => { const steps = document.querySelectorAll('#path circle.p-step'); steps[steps.length - 1].dispatchEvent(new MouseEvent('click', {bubbles: true})); });
    last = true;
  }
  out.path.clicked = {detail: last ? await text('#d-title') : null, steps: await count('#path circle.p-step')};
  // 6. the chart: hover shows value and time, a click moves the clock
  await pointAtChart('mousemove', 0.5);
  out.chart = {cursor: await text('#chart .cursor-label')};
  await pointAtChart('click', 0.25);
  out.chart.clockAfterClick = await text('#clock-time');
  // 7. Escape closes the detail
  await page.keyboard.press('Escape');
  out.escape = {detailHidden: await hidden('#detail')};
  // 8. DESKFIX-1: the legend's Key, pressed twice with the real pointer at the button's centre.
  //    The open key rises into the state card's column; the report says what stands under the
  //    pointer there, and whether the second press closed it.
  await page.evaluate(() => document.getElementById('map').scrollIntoView({block: 'center'}));
  // the list step 3 pinned on the map is closed first: pinned, it stands above everything else
  await page.evaluate(() => { const c = document.querySelector('.gmap-pin .gt-close'); if (c) c.click(); });
  const keyState = () => page.evaluate(() => {
    const k = document.querySelector('.gmap-key'), kinds = document.querySelector('.gmap-kinds'), legend = document.querySelector('.gmap-legend');
    if (!k || !kinds || !legend) return null;
    const r = k.getBoundingClientRect(), top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {expanded: k.getAttribute('aria-expanded'), hidden: kinds.hasAttribute('hidden'), open: legend.classList.contains('is-open'),
            underPointer: top ? top.tagName + '.' + String(top.className).split(' ')[0] : null};
  });
  const keyCentre = () => page.evaluate(() => { const r = document.querySelector('.gmap-key').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
  out.key = {rest: await keyState()};
  if (out.key.rest) {
    let c = await keyCentre(); await page.mouse.click(c[0], c[1]); await page.waitForTimeout(150);
    out.key.opened = await keyState();
    c = await keyCentre(); await page.mouse.click(c[0], c[1]); await page.waitForTimeout(150);
    out.key.closed = await keyState();
  }
  // 9. DESKFIX-1: the state card's HVDC rows and "In force" counts are links. The first row,
  //    pressed, scopes the map to its link (the pinned popover names it, the address gains
  //    `?link=`) and the card stays; the counts link to the notices page at the clock.
  out.card = await page.evaluate(() => ({
    links: [...document.querySelectorAll('#ov-links .ov-link')].map((a) => ({tag: a.tagName, href: a.getAttribute('href'), entity: a.getAttribute('data-entity'),
      height: Math.round(a.getBoundingClientRect().height), style: !!a.getAttribute('style')})),
    counts: [...document.querySelectorAll('#ov-sev .ov-sev-c')].map((a) => ({tag: a.tagName, href: a.getAttribute('href'), severity: a.dataset.severity,
      height: Math.round(a.getBoundingClientRect().height), title: a.title})),
  }));
  if (out.card.links.length) {
    // a folded card (the phone strip) is not on screen: its row's own click is dispatched and
    // the report says so (not in `dispatched`, which pins the folded blocks of the old desk)
    const shown = await page.evaluate(() => document.querySelector('#ov-links .ov-link').checkVisibility());
    if (shown) await page.click('#ov-links .ov-link');
    else await page.evaluate(() => document.querySelector('#ov-links .ov-link').click());
    out.card.pressedHow = shown ? 'pointer' : 'dispatched';
    await page.waitForTimeout(700);   // the map's move to the link
    out.card.pressed = await page.evaluate(() => {
      const pin = document.querySelector('.gmap-pin');
      return {search: location.search, pinOpen: !!pin && !pin.hasAttribute('hidden'), pinTitle: pin ? (pin.querySelector('.gt-title') || {}).textContent || '' : '',
              detailHidden: document.getElementById('detail').hidden, cardVisible: getComputedStyle(document.getElementById('overview')).visibility};
    });
  }
  out.overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  out.dispatched = dispatched;
  return out;
}
/* DESKFIX-1: one site's detail card, opened by the page's own opener, names the other assets at
   its place as buttons; pressing the first opens that asset's card. */
async function walkSiblings(code) {
  const out = {};
  await page.waitForFunction(() => !!(window.GridExplore && window.GridExplore.site), null, {timeout: 15000});
  await page.evaluate((c) => window.GridExplore.site(c), code);
  const card = () => page.evaluate(() => {
    const b = document.querySelector('#d-body dd b'), also = document.querySelector('#d-body .d-also');
    return {code: b ? b.textContent : null, also: also ? also.textContent.replace(/\s+/g, ' ').trim() : null,
            buttons: [...document.querySelectorAll('#d-body button.d-also-site')].map((x) => ({site: x.dataset.site, height: Math.round(x.getBoundingClientRect().height)}))};
  });
  out.first = await card();
  if (out.first.buttons.length) {
    await press('#d-body button.d-also-site');
    out.second = await card();
  }
  return out;
}
async function interactEvent() {
  const out = {};
  await page.waitForFunction(() => document.querySelectorAll('#timeline li').length > 0, null, {timeout: 15000});
  out.chips = await page.evaluate(() => [...document.querySelectorAll('#timeline .tl-label')].map((n) => n.textContent));
  await page.click('#timeline li >> nth=0');
  out.cutoff = {hidden: await hidden('#cutoff'), text: (await text('#cutoff')).slice(0, 300), rows: await count('#cutoff .c-row')};
  await page.click('#timeline li >> nth=1');
  out.cutoffNone = (await text('#cutoff')).slice(0, 200);
  await page.click('.ev-assumption .big');
  out.assumption = {more: await text('#as-more')};
  await page.click('#jd-table tbody tr >> nth=1');
  out.question = {detailRows: await count('#jd-table tr.detail'), text: (await text('#jd-table tr.detail')).slice(0, 200)};
  await page.click('#limits-btn');
  // DESK-1: the last line is where the price-outlook caption lands when the section is drawn —
  // read from the shown records' own `synthetic` flags, so this fixture's synthetic outlook is
  // labelled as such in the caption (copy rule 7), which tests/test_grid_page.py asserts.
  out.limits = {hidden: await hidden('#limits'), items: await count('#limits li'),
                last: await page.evaluate(() => { const li = document.querySelector('#limits li:last-child'); return li ? li.textContent : ''; })};
  out.hover = {
    timeline: await page.getAttribute('#timeline li >> nth=0', 'title'),
    question: await page.getAttribute('#jd-table tbody tr >> nth=1', 'title'),
    assumption: await page.getAttribute('#as-big', 'title'),
  };
  // a decision through the page's own form against the stub routes, then the history entry opens
  await page.click('#dc-form input[value="retain"]');
  await page.fill('#dc-reason', 'harness: the unit returned');
  await page.click('#dc-submit');
  await page.waitForFunction(() => document.querySelectorAll('#hist-list li').length > 0, null, {timeout: 15000});
  out.history = {entries: await count('#hist-list li'), status: await text('#dc-status')};
  out.hover.history = await page.getAttribute('#hist-list li >> nth=0', 'title');
  await page.click('#hist-list li >> nth=0');
  await page.waitForFunction(() => { const m = document.querySelector('#hist-list li .h-more'); return m && !m.textContent.startsWith('Reading'); }, null, {timeout: 10000});
  out.history.more = await text('#hist-list li .h-more');
  out.overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  return out;
}
/* CORP-5: the 'rules in force' block, walked in the browser: the card is on the page, the
   cutoff tabs switch the state, a clause row opens its record detail, and the statuses the
   store returned are the ones shown. The view is served from --views, like the PEDC one.
   The selected cutoff governs the whole page, not only the card, so each state is read with
   what the advisory card, the timeline and the page's whole body text held at that moment:
   `body` is the acceptance's own check that a passage the cutoff does not place is absent
   from the rendered page, not merely from one card. */
async function interactRules() {
  const out = {};
  const stateOf = async () => page.evaluate(() => ({
    cut: document.querySelector('#ru-state .ru-cut').textContent,
    clauseCount: document.querySelectorAll('#ru-state li[data-rule^="clause:"]').length,
    noticeCount: document.querySelectorAll('#ru-state li[data-rule^="claim:"]').length,
    statuses: [...document.querySelectorAll('#ru-state .ru-chip')].map((c) => c.textContent),
    clauses: [...document.querySelectorAll('#ru-state li[data-rule^="clause:"]')].slice(0, 2).map((li) => li.textContent.slice(0, 340)),
    sources: [...document.querySelectorAll('#ru-state li[data-rule^="clause:"] .ru-src')].map((n) => n.textContent),
    noticeSources: [...document.querySelectorAll('#ru-state li[data-rule^="claim:"] .ru-src')].map((n) => n.textContent),
    amendments: document.querySelector('#ru-state .ru-amend') ? document.querySelector('#ru-state .ru-amend').textContent : null,
    amends: [...document.querySelectorAll('#ru-state .ru-amend')].map((n) => n.textContent),
    notices: [...document.querySelectorAll('#ru-state li[data-rule^="claim:"]')].map((li) => li.textContent.slice(0, 260)),
    withheld: document.querySelector('#ru-state .ru-withheld') ? document.querySelector('#ru-state .ru-withheld').textContent : null,
    dependents: document.querySelector('#ru-state .ru-dep') ? document.querySelector('#ru-state .ru-dep').textContent : null,
    quote: document.querySelector('#adv-quote').textContent,
    quoteWithheld: !!document.querySelector('#adv-quote .withheld'),
    timeline: [...document.querySelectorAll('#timeline li')].map((li) => li.textContent.slice(0, 260)),
    timelineWithheld: document.querySelectorAll('#timeline .withheld').length,
    body: document.body.textContent,
  }));
  await page.waitForFunction(() => document.querySelectorAll('#ru-tabs button').length > 0, null, {timeout: 15000});
  out.card = {hidden: await hidden('#rules'), note: (await text('#ru-note')).slice(0, 160),
              governs: await text('#ru-governs')};
  out.heading = await text('#ev-title');
  out.advisory = await text('#adv-asof');
  out.limits = {hidden: await hidden('#limits'), items: await count('#limits li'),
                first: await page.evaluate(() => { const li = document.querySelector('#limits li'); return li ? li.textContent : ''; })};
  out.tabs = await page.evaluate(() => [...document.querySelectorAll('#ru-tabs button')].map((b) => ({text: b.textContent.trim(), pressed: b.getAttribute('aria-pressed')})));
  out.first = await stateOf();
  await page.click('#ru-tabs button >> nth=1');
  await page.waitForFunction(() => document.querySelector('#ru-tabs button[aria-pressed="true"]').textContent.includes('after'), null, {timeout: 10000});
  out.second = await stateOf();
  await page.click('#ru-state li[data-rule^="clause:"] >> nth=0');
  out.detail = {rows: await count('#ru-state .ru-detail'), text: (await text('#ru-state .ru-detail')).slice(0, 200)};
  out.overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  return out;
}
try {
  if (RULES) {
    await page.goto(base + '/event/' + EVENT, {waitUntil: 'load'});
    await page.waitForFunction(() => document.getElementById('ev-title').textContent !== '—', null, {timeout: 15000});
    interactions = await interactRules();
    if (SHOT) await page.screenshot({path: SHOT, fullPage: true});
    rendered = await page.evaluate(() => ({
      title: document.title, clock: '00:00 PHT', briefTitle: '', briefText: '', briefAsOf: '', figuresAsOf: '', figureRows: [], feedCount: '', feedItems: 0,
      feedText: '', reviews: 0, mapCircles: 0, mapSites: 0, siteFills: [], mapLoading: false, mapPricing: false, landPaths: 0, pendingSites: 0,
      linkLabels: [], tip: null, chartPoints: 0, chartLabels: [], caption: document.getElementById('caption').textContent,
      csv: '', viewport: window.innerWidth, overflow: document.documentElement.scrollWidth - window.innerWidth,
      scrub: {left: 0, right: 0, width: 999}, wide: [], mapWidth: 0,
    }));
    throw null;
  }
  if (EVENT) {
    await page.goto(base + '/event/' + EVENT, {waitUntil: 'load'});
    await page.waitForFunction(() => document.getElementById('ev-title').textContent !== '—', null, {timeout: 15000});
    interactions = await interactEvent();
    if (SHOT) await page.screenshot({path: SHOT, fullPage: true});
    rendered = await page.evaluate(() => ({
      title: document.title, clock: '00:00 PHT', briefTitle: '', briefText: '', briefAsOf: '', figuresAsOf: '', figureRows: [], feedCount: '', feedItems: 0,
      feedText: '', reviews: 0, mapCircles: 0, mapSites: 0, siteFills: [], mapLoading: false, mapPricing: false, landPaths: 0, pendingSites: 0,
      linkLabels: [], tip: null, chartPoints: document.querySelectorAll('#mk-chart path').length, chartLabels: [], caption: document.getElementById('caption').textContent,
      csv: '', viewport: window.innerWidth, overflow: document.documentElement.scrollWidth - window.innerWidth,
      scrub: {left: 0, right: 0, width: 999}, wide: [], mapWidth: 0,
    }));
    throw null;
  }
  await page.goto(base + '/' + (HASH ? '#' + HASH : ''), {waitUntil: 'load'});
  if (HOLD_NODE) {
    /* Stage 1: the page's own loading marker is gone and the outline is on the map, with the
       node file still on its way. */
    await page.waitForFunction(() => {
      const wrap = document.querySelector('.map-wrap');
      return !!wrap && !wrap.classList.contains('loading')
        && !!(window.GridDesk && window.GridDesk.mapPanel && window.GridDesk.mapPanel.snapshot())
        && window.GridDesk.mapPanel.snapshot().located.length > 0
        && document.getElementById('brief-text').textContent.trim().length > 0;
    }, null, {timeout: 15000});
    await hoverFirstSite();
    // ATG-8 rework: the panel the page has mounted at stage 1, before the node file lands; the
    // finished page must still be this same panel (see MAP_READ's `sameAsStage1`).
    await page.evaluate(() => {
      window.__stage1Panel = window.GridDesk && window.GridDesk.mapPanel;
    });
    stage1 = await snapshot();
    releaseNode();
    /* Stage 2: the page's pricing marker is gone when the site layer has been drawn. */
    await page.waitForFunction(() =>
      !document.querySelector('.map-wrap').classList.contains('pricing'), null, {timeout: 15000});
  } else {
    await page.waitForFunction(() => {
      const clock = document.getElementById('clock-time');
      return clock && clock.textContent.includes('PHT');
    }, null, {timeout: 15000});
    // EXPL-2: the vector table arrives after stage 1; give it the same bounded wait the node file gets.
    await page.waitForFunction(() => !document.querySelector('.map-wrap').classList.contains('pricing'), null, {timeout: 15000}).catch(() => {});
    // FRONT-1: the findings panel is mounted from the two composed files after the first paint;
    // read it once it has drawn its rows (bounded: a bake without them draws no panel).
    await page.waitForFunction(() => {
      const list = document.querySelector('.briefs .b-entries');
      return !!list && list.children.length > 0;
    }, null, {timeout: 5000}).catch(() => {});
    await page.waitForTimeout(150);
    await hoverFirstSite();
  }
  rendered = await snapshot();
  /* SHELL-1 (merge follow-up): the replay control in use, read with a real pointer: one press of
     "forward five minutes" in the clock the shared bar carries moves the clock. On a phone this is
     the control the reader has, the slider giving way to it. */
  if (PLAY > 0) {
    /* PERF-6: the reads the page made while it loaded have settled first, so the count below is
       the played clock's own. */
    await page.waitForTimeout(3000);
    const mark = INBOX.length;
    const clockBefore = await text('#clock-time');
    await page.evaluate(() => document.getElementById('play').click());
    await page.waitForTimeout(PLAY * 450);
    await page.evaluate(() => document.getElementById('play').click());
    const clockAfter = await text('#clock-time');
    const paused = INBOX.length;
    await page.waitForTimeout(4000);
    play = {ticks: PLAY, clockBefore, clockAfter, whilePlaying: INBOX.slice(mark, paused), afterPause: INBOX.slice(paused),
            asOf: await page.evaluate(() => window.GNShell.asOf()),
            ticker: await text('.gn-ticker-track'), alerts: await text('#da-count')};
  }
  if (CROSS) {
    const [first, second] = CROSS.split(',');
    const markServed = SERVED.length, markRequested = REQUESTED.length;
    const moves = [];
    for (const at of [second, first, second, first].map((d) => d + 'T13:40')) {
      await page.evaluate((t) => window.GridDesk.goto(t), at);
      await page.waitForFunction((d) => {
        const D = window.GridDesk && window.GridDesk.D;
        return !!D && D.day === d && !!D.nodes && String(D.nodes.t[0]).slice(0, 10) === d;
      }, at.slice(0, 10), {timeout: 15000});
      moves.push({at, clock: await text('#clock-time'), day: await page.evaluate(() => window.GridDesk.D.day)});
    }
    const since = SERVED.slice(markServed), asked = REQUESTED.slice(markRequested);
    const dayFile = (name) => /\/days\/\d{4}-\d{2}-\d{2}\.json$/.test(name);
    cross = {moves, nodeFiles: since.filter((name) => NODE_FILE.test(name)), dayFiles: since.filter(dayFile),
             nodeRequests: asked.filter((name) => NODE_FILE.test(name)), dayRequests: asked.filter(dayFile)};
  }
  if (DAY_STEPS) {
    const look = (label) => page.evaluate((label) => {
      const box = (node) => { const b = node.getBoundingClientRect(); return {left: Math.round(b.left), right: Math.round(b.right), top: Math.round(b.top), bottom: Math.round(b.bottom), width: Math.round(b.width)}; };
      const panel = document.getElementById('map-replay');
      const btn = (n) => document.querySelector(`.rp-daystep[data-day="${n}"]`);
      return {label, day: window.GridDesk.D.day, clock: document.getElementById('clock-time').textContent,
              pick: document.getElementById('clock-day').value, hash: location.hash,
              prev: {label: btn(-1).getAttribute('aria-label'), disabled: btn(-1).disabled},
              next: {label: btn(1).getAttribute('aria-label'), disabled: btn(1).disabled},
              panel: box(panel), viewport: window.innerWidth,
              head: [...panel.querySelectorAll('.rp-head > *, .rp-when > *, .rp-days > *')].filter((n) => n.checkVisibility()).map((n) => ({name: n.id || n.className, ...box(n)}))};
    }, label);
    const settle = (d) => page.waitForFunction((d) => window.GridDesk && window.GridDesk.D.day === d, d, {timeout: 15000});
    await page.evaluate(() => window.GridDesk.goto('2026-09-21T13:40'));
    await settle('2026-09-21');
    const seen = [await look('start')];
    await page.click('.rp-daystep[data-day="1"]');
    await settle('2026-09-22');
    seen.push(await look('next'));
    await page.evaluate(() => document.querySelector('.rp-daystep[data-day="1"]').click());
    await page.waitForTimeout(500);
    seen.push(await look('next at the end'));
    await page.click('.rp-daystep[data-day="-1"]');
    await settle('2026-09-21');
    seen.push(await look('previous'));
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.keyboard.press('Shift+ArrowRight');
    await settle('2026-09-22');
    seen.push(await look('shift right'));
    await page.keyboard.press('Shift+ArrowLeft');
    await settle('2026-09-21');
    seen.push(await look('shift left'));
    days = seen;
  }
  if (PROBE) {
    await page.waitForTimeout(1500);  // the page's own first reads have settled
    const mark = INBOX.length, markRequested = REQUESTED.length;
    probe = await page.evaluate(async (day) => {
      const S = window.GNShell, out = {};
      const fail = (p) => p.then(() => null, (e) => ({message: e.message, status: e.status}));
      const a = S.inbox('2026-09-21T10:00'), b = S.inbox('2026-09-21T10:00');
      out.shared = a === b;
      out.answer = await a;
      out.kept = S.inbox('2026-09-21T10:00') === a;
      out.fresh = S.inbox('2026-09-21T10:00', {fresh: true}) !== a;
      out.failed = [await fail(S.inbox('2026-09-21T00:05')), await fail(S.inbox('2026-09-21T00:05'))];
      out.day = [await S.dayFile(day), await S.dayFile(day)].map((f) => (f ? f.day : null));
      await new Promise((resolve) => setTimeout(resolve, 5500));
      const again = await S.dayFile(day);
      out.day.push(again ? again.day : null);
      return out;
    }, PROBE_DAY);
    probe.inbox = INBOX.slice(mark);
    probe.dayRequests = REQUESTED.slice(markRequested).filter((name) => name.endsWith('/days/' + PROBE_DAY + '.json'));
  }
  if (!INTERACT && !HOLD_NODE && !PLAY && !CROSS && !PROBE && !SIBLINGS && !DAY_STEPS) {
    const before = await text('#clock-time');
    await page.click('.clock [data-step="1"]');
    step = {before, after: await text('#clock-time')};
  }
  if (INTERACT && !EVENT) interactions = await interactGrid();
  else if (SIBLINGS) siblings = await walkSiblings(SIBLINGS);
  else if (SHOT) await page.screenshot({path: SHOT, fullPage: WIDTH < 800});
} catch (error) {
  if (error !== null) thrown = String(error);
  // Never leave the node file's answer held when the wait for stage 1 failed: the server would
  // keep the request open and this process would not exit. Releasing twice is a no-op.
  releaseNode();
}
// The page's warm-up `GET /health` is fire-and-forget after the first paint (PERF-5): wait,
// bounded, until the server has seen it, so the report's counts and the failure lists below
// are read after the request settled rather than while it is in flight.
const healthDeadline = Date.now() + (EVENT ? 0 : 5000);
while (!SERVED.includes('/health') && Date.now() < healthDeadline) {
  await new Promise((resolve) => setTimeout(resolve, 25));
}
await browser.close();
server.close();

// A page that scrolls sideways on a phone is a failed check here, not a footnote: the
// reviewed defect was exactly that, and the caller should not have to read the report to see it.
const ok = thrown === null && pageErrors.length === 0 && consoleErrors.length === 0
  && failedRequests.length === 0 && rendered !== null && rendered.overflow <= 0;
report({ok, ran: true, width: WIDTH, hash: HASH, url: base + '/', stamp: STAMP || null, held: HOLD_NODE,
        thrown, consoleErrors, pageErrors, failedRequests, badResponses, stage1, rendered, served: SERVED, interactions, siblings, step,
        inbox: INBOX, play, cross, days, probe, requested: REQUESTED,
        legacyCards: LEGACY, liveIds: EVENT ? WALKED_EVENT_IDS.filter((id) => LIVE_EVENT_IDS.has(id)) : null,
        health: SERVED.filter((name) => name === '/health').length,
        policy: Object.fromEntries(POLICY_PATHS.map((name) => [name, policyFor(name)]))}, ok ? 0 : 1);
