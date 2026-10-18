/* PP-B1 monitor pages in a real headless browser: the notices page (`/notices`) and an alert's own
   page (`/alert/<key>`), served with a build stamp written in from src/grid, against SYNTHETIC
   replay files and a SYNTHETIC alert API held here. Prints one JSON report on stdout;
   tests/test_grid_notices.py reads it.

     node tests/fixtures/grid/monitor/browser.mjs --root . --playwright <playwright-core/index.mjs> \
          --chromium <chrome>

   Every value below is made up: the plant codes, the notices, the event and the alert figures.
   Exit 0 when it ran, 3 when no browser is given. Loopback only: any other host is aborted and
   listed. Nothing is written. */
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
const STAMP = '0123456789abcdef';
if (!PLAYWRIGHT || !CHROMIUM) { process.stdout.write(JSON.stringify({ran: false, reason: 'no browser given'}) + '\n'); process.exit(3); }

const CAUSED = 'a'.repeat(24);
const LONE = 'b'.repeat(24);
const LATER = 'c'.repeat(24);
const GONE = 'd'.repeat(24);

/* ---- synthetic replay files ---- */
const NOTICES = [
  {t: '2026-09-20T22:10:00', id: 'L221000', grid: 'CLUZ', kind: 'notice', text: 'Synthetic informational notice for the Luzon Grid'},
  {t: '2026-09-21T06:12:41', id: 'L061241', grid: 'CLUZ', kind: 'notice', text: '01SYNALPA U1 on planned outage from 0600H (Planned Outage)'},
  {t: '2026-09-21T09:02:15', id: 'V090215', grid: 'CVIS', kind: 'notice', text: '05SYNBETA derated to 25 MW due to inverter fault (Derating)'},
  {t: '2026-09-21T12:48:03', id: 'V124803', grid: 'CVIS', kind: 'yellow', text: 'Yellow Alert declared for the Visayas Grid effective 1245H'},
  {t: '2026-09-21T13:39:37', id: 'V133937', grid: 'CVIS', kind: 'trip', text: '08SYNGAMA U2 Tripped at 1334H (Unplanned Outage)'},
  {t: '2026-09-21T13:51:20', id: 'V135120', grid: 'CVIS', kind: 'red', text: 'Red Alert declared for the Visayas Grid effective 1350H'},
  {t: '2026-09-21T13:58:00', id: 'M135800', grid: 'CMIN', kind: 'notice', text: '<img src=x onerror="window.__pwned=1"> SYNDUP and SYNDUP units on test'},
  {t: '2026-09-21T16:12:00', id: 'V161200', grid: 'CVIS', kind: 'online', text: '08SYNGAMA U2 back online at 1610H'},
];
const SITES = [
  {s: '01SYNALPA', g: 'CLUZ', name: 'Synthetic Alpha Power'},
  {s: '05SYNBETA', g: 'CVIS', name: 'Synthetic Beta Solar'},
  {s: '08SYNGAMA', g: 'CVIS', name: 'Synthetic Gamma Coal'},
  {s: '10SYNDUP', g: 'CMIN', name: 'Synthetic Dup One'},
  {s: '11SYNDUP', g: 'CMIN', name: 'Synthetic Dup Two'},
];
const EVENTS = [{id: 'syn-gama-u2-trip', t: '2026-09-21T13:39:37', advisory: 'V133937', site: '08SYNGAMA', title: 'Synthetic: 08SYNGAMA U2 trip · Visayas'}];
const DATA = {
  'replay.json': {v: 1, first: '2026-09-20T00:00', last: '2026-09-21T23:55', days: ['2026-09-20', '2026-09-21'], missing: [], node_days: [], months: ['2026-09'], intervals: 576},
  'advisories.json': NOTICES, 'advisories/2026-09.json': NOTICES, 'events.json': EVENTS, 'sites.json': SITES,
  'days/2026-09-20.json': null, 'days/2026-09-21.json': null, 'views/alerts.json': {views: []},
};

/* ---- the synthetic alert API (the backend's shapes, src/alerts/service.py `alert` and `explain`) ---- */
function around(first, last, peak, opts) {
  const t = [];
  for (let m = 12 * 60 + 40; m <= 14 * 60 + 40; m += 5) t.push(`2026-09-21T${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`);
  const inAlert = (x) => x >= first && x <= last;
  return {from: t[0], to: t[t.length - 1], clock: opts.clock, minutes_either_side: 60, level_mode: 'absolute', t,
    price: t.map((x) => (inAlert(x) ? (x === peak ? 31000 : 22000) : 6000)), usual: t.map(() => null), level: t.map(() => 15000),
    reserve_short_mw: opts.noReserve ? t.map(() => null) : t.map((x) => (inAlert(x) ? 120 : 0)),
    curtailed_mw: t.map(() => null), demand_mw: t.map(() => 2700),
    notices: NOTICES.filter((n) => n.grid === 'CVIS' && n.t.slice(0, 16) >= t[0] && n.t.slice(0, 16) <= t[t.length - 1]).map((n) => ({t: n.t.slice(0, 16), id: n.id, kind: n.kind, text: n.text}))};
}
const ALERT = {
  key: CAUSED, source: 'replay', region: 'CVIS', region_label: 'Visayas', direction: 'spike', first: '2026-09-21T13:00', last: '2026-09-21T14:00',
  intervals: 13, interval_manila: '2026-09-21T13:40', price_php_mwh: 31000, usual_php_mwh: null, threshold_text: 'price at or above 15,000 PHP/MWh',
  severity: 'high', severity_reason: '13 intervals above the level', facts: [], href: '/event/syn-gama-u2-trip',
  cause: {kind: 'event', id: 'syn-gama-u2-trip', title: 'Synthetic: 08SYNGAMA U2 trip · Visayas', advisory: 'V133937', known_at: '2026-09-21T13:39', href: '/event/syn-gama-u2-trip'},
  next_step: 'Open the event (Synthetic: 08SYNGAMA U2 trip · Visayas) and check its timeline against your position.',
};
function alertAnswer(key, at) {
  const clock = at || '2026-09-21T13:40';
  if (key === CAUSED) return [200, {status: 'ok', at: clock, default_levels: true, rules_version: null, alert: ALERT, around: around(ALERT.first, ALERT.last, ALERT.interval_manila, {clock})}];
  if (key === LONE) {
    const a = Object.assign({}, ALERT, {key: LONE, cause: null, href: '/alert/' + LONE, first: '2026-09-21T13:20', last: '2026-09-21T13:40', intervals: 5,
      next_step: 'Open the alert to review the interval and the notices around it.'});
    return [200, {status: 'ok', at: clock, default_levels: true, rules_version: null, alert: a, around: around(a.first, a.last, a.interval_manila, {clock, noReserve: true})}];
  }
  if (key === LATER) return [200, {status: 'after_clock', region_label: 'Visayas', first: '2026-09-21T18:00'}];
  return [404, {code: 'NOT_FOUND', message: 'No such alert.'}];
}
const EXPLAIN = {status: 'ok', interval_manila: '2026-09-21T13:40', drivers: [
  {family: 'S', rank: 1, name: 'Supply', text: 'reserve shortfall 120 MW against a median of 0 MW', percentile: 99, status: 'scored'},
  {family: 'R', name: 'Rules', text: 'Not in the replay data', percentile: null, status: 'not in replay'}],
  summary: {severity: 'high'}, paragraph: 'Composed by code from synthetic figures.', basis: 'Synthetic basis.'};

const TYPES = {'.css': 'text/css', '.js': 'text/javascript', '.woff2': 'font/woff2'};
const PAGES = {'/notices': 'notices.html'};
const json = (res, status, body) => res.writeHead(status, {'content-type': 'application/json'}).end(JSON.stringify(body));
const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  const name = decodeURIComponent(url.pathname);
  const page = PAGES[name] || (/^\/alert\/[0-9a-f]{24}$/.test(name) ? 'spike.html' : null);
  if (page) {
    res.writeHead(200, {'content-type': 'text/html'}).end(readFileSync(path.join(ROOT, 'src/grid', page), 'utf8').replaceAll('__NOWCAST_STAMP__', STAMP));
    return;
  }
  const asset = name.match(new RegExp('^/grid/' + STAMP + '/((?:fonts/)?[a-z0-9][a-z0-9._-]*\\.(?:css|js|woff2))$'));
  if (asset) {
    try { res.writeHead(200, {'content-type': TYPES[path.extname(asset[1])]}).end(readFileSync(path.join(ROOT, 'src/grid', asset[1]))); }
    catch (e) { json(res, 404, {code: 'NOT_FOUND'}); }
    return;
  }
  const data = name.match(new RegExp('^/grid-data/' + STAMP + '/(.+)$'));
  if (data && Object.prototype.hasOwnProperty.call(DATA, data[1])) { json(res, 200, DATA[data[1]]); return; }
  let m = name.match(/^\/api\/alerts\/alert\/([0-9a-f]{24})$/);
  if (m) { const [status, body] = alertAnswer(m[1], url.searchParams.get('at')); json(res, status, body); return; }
  m = name.match(/^\/api\/alerts\/explain\/([0-9a-f]{24})$/);
  if (m) { json(res, 200, EXPLAIN); return; }
  if (name === '/api/alerts/inbox') { json(res, 200, {groups: [], count: 0}); return; }
  if (name === '/api/alerts/client-config') { json(res, 503, {code: 'SIGN_IN_UNAVAILABLE', message: 'Sign-in is not configured here.'}); return; }
  json(res, 404, {code: 'NOT_FOUND'});
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const {chromium} = await import(pathToFileURL(PLAYWRIGHT).href);
const browser = await chromium.launch({executablePath: CHROMIUM, headless: true, args: ['--no-sandbox']});
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];

async function open(url, width, theme) {
  const context = await browser.newContext({viewport: {width, height: 900}});
  await context.addInitScript((t) => { try { localStorage.setItem('gn-theme', t); } catch (e) { /* none */ } }, theme || 'dark');
  await context.route('**/*', (route) => {
    const u = new URL(route.request().url());
    if (/^https?:$/.test(u.protocol) && u.hostname !== '127.0.0.1') { errors.push({blocked: u.origin}); route.abort(); } else route.continue();
  });
  const page = await context.newPage();
  page.on('pageerror', (e) => errors.push({url, error: String(e && e.message || e)}));
  await page.goto(base + url, {waitUntil: 'networkidle'});
  await wait(500);
  return {page, context};
}
const tap = async (page, sel) => {
  await page.evaluate((s) => document.querySelector(s).scrollIntoView({block: 'center'}), sel);
  await page.click(sel);
  await wait(350);
};
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
const readNotices = (page) => page.evaluate(() => ({
  ids: [...document.querySelectorAll('#nt-list tr.nt-row')].map((tr) => tr.dataset.id),
  days: [...document.querySelectorAll('#nt-list tr.nt-day .nt-day-label')].map((n) => n.textContent),
  kinds: [...document.querySelectorAll('#nt-list tr.nt-row td:nth-child(2) .gn-badge')].map((n) => n.textContent),
  count: document.getElementById('nt-count').textContent,
  search: location.search, hash: location.hash,
  selected: [...document.querySelectorAll('#nt-list tr.nt-row.is-selected')].map((tr) => tr.dataset.id),
  picked: [...document.querySelectorAll('#nt-list tr.nt-row[aria-current="true"]')].map((tr) => tr.dataset.id),
  detailHead: document.getElementById('nt-detail-h').textContent,
  detailText: (document.querySelector('#nt-detail-body .nt-d-text') || {}).textContent || null,
  detailLinks: [...document.querySelectorAll('#nt-detail-body a[data-entity]')].map((a) => [a.getAttribute('data-entity'), a.getAttribute('href')]),
  detailPlant: (document.querySelector('#nt-detail-body .nt-d-facts dd:nth-of-type(2)') || {}).textContent || null,
  related: Object.fromEntries([...document.querySelectorAll('#nt-list tr.nt-row')].map((tr) => [tr.dataset.id,
    [...tr.querySelectorAll('td.nt-rel a, td.nt-rel span')].map((n) => n.getAttribute('data-entity') || n.textContent)])),
  glance: {n: document.getElementById('nt-recent-count').textContent, badges: [...document.querySelectorAll('#nt-recent .gn-badge')].map((b) => b.textContent),
    latest: document.getElementById('nt-latest').textContent},
  empty: document.getElementById('nt-empty').hidden ? null : document.getElementById('nt-empty').innerText,
  clearShown: !document.getElementById('nt-clear').hidden,
  pwned: window.__pwned || null, images: document.querySelectorAll('#nt-list img, #nt-detail img').length,
  textShown: [...document.querySelectorAll('#nt-list .nt-open')].some((a) => a.textContent.includes('<img src=x')),
}));

const report = {notices: {}, alert: {}};
/* ---- notices, wide ---- */
{
  const {page, context} = await open('/notices?at=2026-09-21T14:00', 1440);
  const N = report.notices;
  N.first = await readNotices(page);
  N.firstInView = await page.evaluate(() => { const d = document.getElementById('nt-detail'); const r = d.getBoundingClientRect(); return r.width > 0 && getComputedStyle(d).display !== 'none'; });
  await tap(page, '#nt-filters [data-filter="grid"] button[data-value="CVIS"]');
  N.visayas = await readNotices(page);
  await tap(page, '#nt-filters [data-filter="kind"] button[data-value="trip"]');
  N.trips = await readNotices(page);
  await tap(page, '#nt-filters [data-filter="kind"] button[data-value="derate"]');
  N.derates = await readNotices(page);
  await tap(page, '#nt-clear');
  N.cleared = await readNotices(page);
  await tap(page, '#nt-filters [data-filter="period"] button[data-value="6h"]');
  N.sixHours = await readNotices(page);
  await tap(page, '#nt-filters [data-filter="period"] button[data-value="all"]');
  await page.fill('#nt-q', 'nothing like this'); await wait(450);
  N.none = await readNotices(page);
  await tap(page, '#nt-empty button');
  N.afterEmptyClear = await readNotices(page);
  // a row click opens it in the panel and gives the address its anchor
  await tap(page, '#adv-V090215 td.nt-text');
  N.picked = await readNotices(page);
  N.overflow = await overflow(page);
  await context.close();
}
{
  // an anchor (the command bar's and the strip's links): scrolled to, marked, open in the panel
  const {page, context} = await open('/notices?at=2026-09-21T14:00#adv-V133937', 1440);
  const N = report.notices;
  N.anchor = await readNotices(page);
  N.anchorInView = await page.evaluate(() => { const r = document.getElementById('adv-V133937').getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight; });
  await context.close();
}
{
  // a filtered address restores the filter; an anchor hidden by the filters says so, with Clear
  const {page, context} = await open('/notices?at=2026-09-21T14:00&grid=CLUZ&kind=notice#adv-V133937', 1440);
  const N = report.notices;
  N.restored = await readNotices(page);
  N.restoredPressed = await page.evaluate(() => [...document.querySelectorAll('#nt-filters .gn-seg button[aria-pressed="true"]')].map((b) => b.dataset.value));
  N.hiddenNote = await page.evaluate(() => { const n = document.getElementById('nt-linked'); return n.hidden ? null : n.textContent; });
  await context.close();
}
{
  // nothing up to the clock: what is missing, and the way to move the clock
  const {page, context} = await open('/notices?at=2026-09-20T06:00', 1440);
  report.notices.early = await readNotices(page);
  report.notices.earlyActions = await page.evaluate(() => [...document.querySelectorAll('#nt-empty button')].map((b) => b.textContent));
  await context.close();
}
{
  // a phone: three columns, the row opens its notice under it, no sideways scroll
  const {page, context} = await open('/notices?at=2026-09-21T14:00', 390, 'light');
  const N = report.notices;
  N.phoneColumns = await page.evaluate(() => [...document.querySelectorAll('#nt-table thead th')].filter((th) => getComputedStyle(th).display !== 'none').map((th) => th.textContent));
  await tap(page, '#adv-V133937 td.nt-text');
  N.phone = await page.evaluate(() => {
    const row = document.querySelector('#nt-list tr.nt-inline');
    return {inline: Boolean(row), after: row ? row.previousElementSibling.id : null, text: row ? row.querySelector('.nt-d-text').textContent : null,
      width: row ? Math.round(row.getBoundingClientRect().width) : 0};
  });
  N.phoneOverflow = await overflow(page);
  await context.close();
}

/* ---- an alert's own page ---- */
{
  const {page, context} = await open('/alert/' + CAUSED + '?at=2026-09-21T14:00', 1440);
  report.alert.caused = await page.evaluate(() => ({
    title: document.title, h1: document.querySelector('main h1').textContent,
    crumbs: [...document.querySelectorAll('main .gn-crumbs a, main .gn-crumbs [aria-current]')].map((n) => n.textContent),
    meta: [...document.querySelectorAll('#sp-pills > *')].map((n) => n.textContent),
    actions: [...document.querySelectorAll('#sp-actions a')].map((a) => [a.textContent, a.getAttribute('href')]),
    stats: [...document.querySelectorAll('#sp-kpis .gn-stat .gn-label')].map((n) => n.textContent),
    keyStat: (document.querySelector('#sp-kpis .gn-stat--key .gn-value') || {}).textContent,
    unknowns: document.getElementById('sp-unknowns').hidden ? null : document.getElementById('sp-unknowns').textContent,
    naTiles: [...document.querySelectorAll('#sp-kpis .gn-stat')].filter((n) => /Not in the record|No usual price/.test(n.textContent)).length,
    cause: document.getElementById('sp-cause-body').innerText,
    causeLinks: [...document.querySelectorAll('#sp-cause-body a')].map((a) => [a.getAttribute('data-entity'), a.getAttribute('href')]),
    steps: [...document.querySelectorAll('#sp-steps .sp-step-id')].map((a) => [a.textContent, a.getAttribute('data-entity'), a.getAttribute('href')]),
    opened: [...document.querySelectorAll('#sp-steps .sp-step-head')].filter((n) => n.textContent.includes('opened the event')).map((n) => n.querySelector('.sp-step-id').textContent),
    pricePath: Boolean(document.querySelector('#sp-price path.sp-line-price')),
    minis: ['sp-short-fig', 'sp-demand-fig'].map((id) => !document.getElementById(id).hidden),
    sources: Boolean(document.querySelector('main footer.gn-sources details:not([open]) #sp-made li')),
    ranked: document.querySelectorAll('#sp-ranked-rows .sp-rk-row').length,
    journal: Boolean(document.getElementById('sp-journal')),
    cost: document.querySelector('.sp-cost').textContent,
    pageBottomRoom: parseFloat(getComputedStyle(document.querySelector('main.gn-page')).paddingBottom),
  }));
  report.alert.causedOverflow = await overflow(page);
  await context.close();
}
{
  const {page, context} = await open('/alert/' + LONE + '?at=2026-09-21T13:40', 1440, 'light');
  report.alert.lone = await page.evaluate(() => ({
    h1: document.querySelector('main h1').textContent,
    meta: [...document.querySelectorAll('#sp-pills > *')].map((n) => n.textContent),
    actions: [...document.querySelectorAll('#sp-actions a')].map((a) => a.textContent),
    cause: document.getElementById('sp-cause-body').innerText,
    eventLinks: document.querySelectorAll('main a[href^="/event/"]').length,
    unknowns: document.getElementById('sp-unknowns').textContent,
    minis: ['sp-short-fig', 'sp-demand-fig'].map((id) => !document.getElementById(id).hidden),
  }));
  await context.close();
}
for (const [name, key] of [['later', LATER], ['gone', GONE]]) {
  const {page, context} = await open('/alert/' + key + '?at=2026-09-21T13:40', 390);
  report.alert[name] = await page.evaluate(() => ({
    body: !document.getElementById('sp-body').hidden,
    title: (document.querySelector('#sp-state .gn-empty-title') || {}).textContent || null,
    text: document.getElementById('sp-state').innerText,
    action: [...document.querySelectorAll('#sp-state .gn-empty-actions a')].map((a) => [a.textContent, a.getAttribute('href')]),
  }));
  await context.close();
}
{
  const {page, context} = await open('/alert/' + CAUSED + '?at=2026-09-21T14:00', 390, 'light');
  report.alert.phoneOverflow = await overflow(page);
  await context.close();
}

await browser.close();
server.close();
report.errors = errors;
process.stdout.write(JSON.stringify(report) + '\n');
