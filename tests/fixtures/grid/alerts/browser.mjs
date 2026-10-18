/* The alerts page (`/alerts`, the list) and the alert settings page (`/settings`: the check, the
   rules, the history, the signed-out banner) in a real headless browser against the fixture API
   (serve.py), one scenario per fixture server, reported as one JSON object on stdout.
   tests/test_grid_alerts.py starts the servers and reads the report.

     node tests/fixtures/grid/alerts/browser.mjs --playwright <playwright-core/index.mjs> --chrome <exe> \
          --anon <url> --signed <url> --hostile <url> --fail <url> [--width 390]

   Platform polish PP-B1 moved this driver from puppeteer-core to playwright-core (the driver the
   other page checks use), and to the inbox's new markup: the glance band, the shared filter bar
   (GNUI.filters: `data-filter` groups, More filters, the address), the table.

   Scenarios (each URL is a serve.py instance in that mode):
     anon     --seed --no-sign-in: not signed in, sign-in unavailable (503); what each page shows and
              must not show; the list page holds only the list and links to the settings page
     signed   --seed --signed-in: editing enabled on /settings; save the rules; run a check (202,
              then polled to done); open the alert link (the list sends it on to the history)
     hostile  --signed-in --hostile: a check answered with markup and a script link
     nochecks --signed-in --no-checks: checks unavailable on the server; the run button stays off
     fail     --signed-in --fail: every alerts call answers 500
     password --seed --password: signed out; the shell's sign-in screen offers email and password; a
              wrong password is refused in plain words and cleared; the right one signs in to edit
   Each scenario records console errors, page errors and sideways overflow at the given width.

   Exit codes: 0 the report was written, 3 no browser driver or executable given. Nothing reaches
   past 127.0.0.1 (requests to any other host are aborted and listed), nothing is written. */
import process from 'node:process';
import {pathToFileURL} from 'node:url';

const argv = process.argv.slice(2);
const arg = (name, fallback = '') => {
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const DRIVER = arg('playwright');
const CHROME = arg('chrome');
const WIDTH = Number(arg('width', '390'));
if (!DRIVER || !CHROME) { console.log(JSON.stringify({ok: false, error: 'no browser'})); process.exit(3); }
const {chromium} = await import(pathToFileURL(DRIVER).href);

const browser = await chromium.launch({executablePath: CHROME, headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--no-first-run', '--no-default-browser-check']});
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function open(url) {
  const context = await browser.newContext({viewport: {width: WIDTH, height: 900}});
  const page = await context.newPage();
  const log = {console: [], pageErrors: [], blocked: [], failed: [], local: [], refused: []};
  page.on('console', (m) => { if (m.type() === 'error') log.console.push(m.text()); });
  page.on('pageerror', (e) => log.pageErrors.push(String(e && e.message || e)));
  await context.route('**/*', (route) => {
    const u = new URL(route.request().url());
    if (!/^https?:$/.test(u.protocol)) { log.local.push(u.protocol); route.continue(); return; }  // data:, blob: (no network)
    if (u.hostname !== '127.0.0.1') { log.blocked.push(u.origin); route.abort(); } else route.continue();
  });
  page.on('response', (res) => { const u = new URL(res.url()); if (res.status() >= 400 && u.hostname === '127.0.0.1') log.refused.push(res.status() + ' ' + res.request().method() + ' ' + u.pathname); });
  page.on('requestfailed', (req) => { const u = new URL(req.url()); if (u.hostname === '127.0.0.1') log.failed.push(u.pathname); });
  await page.goto(url, {waitUntil: 'networkidle'});
  await wait(400);
  return {page, context, log};
}

const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
// The alert list as shown: the rows' keys, cause links and open links, the count and the pager.
const readList = (page) => page.evaluate(() => ({
  note: document.getElementById('inbox-note').textContent,
  text: document.getElementById('inbox').innerText + '\n' + document.getElementById('inbox-empty').innerText,
  keys: [...document.querySelectorAll('#inbox tr.al-row')].map((tr) => tr.dataset.key),
  causeLinks: [...document.querySelectorAll('#inbox tr.al-row')].map((tr) => {
    const a = tr.querySelector('td.al-cause-cell a.al-cause'); return a && a.getAttribute('href'); }),
  openLinks: [...document.querySelectorAll('#inbox tr.al-row .al-go')].map((a) => a.getAttribute('href')),
  rowLinks: [...document.querySelectorAll('#inbox tr.al-row')].map((tr) => tr.getAttribute('data-href')),
  openTexts: [...document.querySelectorAll('#inbox tr.al-row .al-go')].map((a) => a.textContent),
  noCause: [...document.querySelectorAll('#inbox tr.al-row td.al-cause-cell')].filter((td) => td.textContent.trim() === 'None on record').length,
  groups: [...document.querySelectorAll('#inbox tr.al-group-row')].map((tr) => tr.querySelector('.al-group-label').textContent),
  pagerHidden: document.getElementById('inbox-pager').hidden,
  emptyShown: !document.getElementById('inbox-empty').hidden,
  emptyActions: [...document.querySelectorAll('#inbox-empty button')].map((b) => b.textContent),
  search: location.search,
  assignButtons: document.querySelectorAll('#inbox button').length}));
/* The command bar floats over the bottom of the screen at phone width: bring a control to the
   middle of the screen before clicking it, as a person scrolls to it. */
const tap = async (page, sel) => {
  await page.evaluate((s) => document.querySelector(s).scrollIntoView({block: 'center'}), sel);
  await page.click(sel);
};
const pick = async (page, f, v) => {
  const sel = `#inbox-card [data-filter="${f}"] button[data-value="${v}"], #inbox-card [data-view="${f}"] button[data-value="${v}"]`;
  // the direction, cause, period, group and order controls sit under More filters
  if (!(await page.locator(sel).isVisible())) await tap(page, '#al-more > summary');
  await tap(page, sel); await wait(250);
  // close the fold again, as a click elsewhere would
  await page.evaluate(() => { const d = document.getElementById('al-more'); if (d) d.open = false; });
  const r = await readList(page);
  r.pressed = await page.evaluate((f) => [...document.querySelectorAll(`#inbox-card [data-filter="${f}"] button[aria-pressed="true"], #inbox-card [data-view="${f}"] button[aria-pressed="true"]`)].map((b) => b.dataset.value), f);
  return r;
};
const search = async (page, q) => {
  await page.fill('#inbox-q', q);
  await wait(400); return readList(page);
};
const report = {width: WIDTH};
// Which page parts are present: the list on /alerts, the settings cards on /settings.
const parts = (page) => page.evaluate(() => Object.fromEntries(
  ['inbox-card', 'check-card', 'rules-card', 'history-card', 'signin-card', 'settings']
    .map((id) => [id, Boolean(document.getElementById(id))])));
const joinLogs = (a, b) => Object.fromEntries(Object.keys(a).map((k) => [k, a[k].concat(b[k])]));

/* anon --------------------------------------------------------------------------------------- */
{
  const {page, context, log} = await open(arg('anon') + '/settings');
  report.anon = await page.evaluate(() => {
    const $ = (id) => document.getElementById(id);
    const values = [...document.querySelectorAll('input')].map((i) => i.value).join('|');
    const text = document.body.innerText;
    return {
      notice: $('notice').textContent,
      banner: {shown: !$('signin-card').hidden, title: $('signin-title').textContent, line: $('signin-line').textContent,
        action: !$('signin-open').hidden, form: !$('pw-form').hidden},
      portfolio: Boolean($('portfolio-card') || $('portfolio-fields')), rulesDisabled: $('rules-fields').disabled,
      runDisabled: $('check-run').disabled,
      rulesCurrent: $('rules-current').textContent, title: document.title,
      heading: document.querySelector('main h1') && document.querySelector('main h1').textContent,
      crumbs: [...document.querySelectorAll('main .gn-crumbs a, main .gn-crumbs [aria-current]')].map((n) => n.textContent),
      recipientsRow: $('rl-recipients').tBodies[0].textContent,
      historyRows: $('history').tBodies[0].rows.length, historyText: $('history').tBodies[0].innerText,
      leaks: ['6543', '6,543', '5222', '111', 'Fixture Seed BCQ', 'secret-recipient@example.test'].filter((v) => text.includes(v) || values.includes(v)),
      signInVisible: Boolean($('sign-in') && !$('sign-in').hidden),
      historyEmailed: $('history').tBodies[0].rows[0] && $('history').tBodies[0].rows[0].cells[5].textContent,
      historyCells: $('history').tBodies[0].rows[0] && $('history').tBodies[0].rows[0].cells.length,
    };
  });
  report.anon.settingsParts = await parts(page);
  report.anon.settingsOverflow = await overflow(page);
  report.anon.shellSettings = await page.evaluate(() => {
    const a = document.querySelector('.gn-settings'); return a && {href: a.getAttribute('href'), current: a.getAttribute('aria-current')}; });
  await context.close();
  const list = await open(arg('anon') + '/alerts');
  {
    const page = list.page;
    report.anon.listParts = await parts(page);
    report.anon.listPage = await page.evaluate(() => {
      const a = document.getElementById('settings-link');
      const text = document.body.innerText;
      return {settingsLink: a && {href: a.getAttribute('href'), text: a.textContent, inHead: Boolean(a.closest('#inbox-card .gn-page-head'))},
        shellSettings: document.querySelector('.gn-settings') && document.querySelector('.gn-settings').getAttribute('href'),
        leaks: ['secret-recipient@example.test', 'Fixture Seed BCQ'].filter((v) => text.includes(v)),
        glance: {now: document.getElementById('al-now-count').textContent,
          sev: [...document.querySelectorAll('#al-now-sev .gn-badge')].map((b) => b.textContent),
          day: document.getElementById('al-day-count').textContent, all: document.getElementById('al-all-count').textContent,
          worst: document.querySelector('#al-worst .al-worst-title') && document.querySelector('#al-worst .al-worst-title').textContent,
          worstLabel: document.querySelector('#al-worst .gn-label') && document.querySelector('#al-worst .gn-label').textContent,
          worstHref: document.querySelector('#al-worst .al-worst-go') && document.querySelector('#al-worst .al-worst-go').getAttribute('href')},
        sources: {inFooter: Boolean(document.querySelector('#inbox-card footer.gn-sources details')),
          open: Boolean(document.querySelector('#inbox-card footer.gn-sources details[open]'))}};
    });
    const L = {all: await readList(page), worst: await pick(page, 'sort', 'worst')};
    await pick(page, 'sort', 'newest');
    L.visayas = await pick(page, 'grid', 'CVIS');
    L.clearShown = await page.evaluate(() => !document.getElementById('inbox-clear').hidden);
    await pick(page, 'grid', 'all');
    L.medium = await pick(page, 'level', 'medium'); await pick(page, 'level', 'all');
    L.collapse = await pick(page, 'dir', 'collapse'); await pick(page, 'dir', 'all');
    L.withCause = await pick(page, 'cause', 'yes'); await pick(page, 'cause', 'all');
    L.byCause = await pick(page, 'group', 'cause'); await pick(page, 'group', 'day');
    L.searched = await search(page, 'reserve short');
    L.none = await search(page, 'nothing like this');
    // "Clear filters" in the empty state resets every filter
    await tap(page, '#inbox-empty button');
    await wait(400);
    L.cleared = await readList(page);
    // the address keeps the filters: a reload opens the same view
    await page.goto(arg('anon') + '/alerts?grid=CVIS&level=extreme', {waitUntil: 'networkidle'}); await wait(400);
    L.restored = await readList(page);
    L.restored.pressed = await page.evaluate(() => [...document.querySelectorAll('#inbox-card .gn-seg[data-filter] button[aria-pressed="true"]')].map((b) => b.dataset.value));
    report.anon.list = L;
    report.anon.overflow = Math.max(report.anon.settingsOverflow, await overflow(page));
  }
  report.anon.log = joinLogs(log, list.log);
  await list.context.close();
}

/* signed ------------------------------------------------------------------------------------- */
{
  const {page, context, log} = await open(arg('signed') + '/settings#t=15:05&g=CVIS');
  const r = {};
  r.start = await page.evaluate(() => ({who: document.getElementById('who').textContent,
    editable: !document.getElementById('rules-fields').disabled, region: document.getElementById('check-region').value,
    interval: document.getElementById('check-interval').value, banner: !document.getElementById('signin-card').hidden,
    recipients: [...document.querySelectorAll('#rl-recipients input[type=email]')].map((i) => i.value)}));
  await tap(page, '#rl-add-recipient');
  await page.evaluate(() => { const rows = document.querySelectorAll('#rl-recipients tbody tr'); rows[rows.length - 1].querySelector('input[type=email]').value = 'desk@example.test'; });
  await tap(page, '#rl-save'); await wait(500);
  r.rules = await page.evaluate(() => ({notice: document.getElementById('notice').textContent, current: document.getElementById('rules-current').textContent}));
  await tap(page, '#check-send'); await tap(page, '#check-run'); await wait(700);
  r.running = await page.evaluate(() => ({text: document.querySelector('#check-result .running') && document.querySelector('#check-result .running').textContent,
    disabled: document.getElementById('check-run').disabled}));
  await page.waitForSelector('#check-result .st-alert', {timeout: 30000});
  r.afterRun = await page.evaluate(() => ({disabled: document.getElementById('check-run').disabled}));
  // The history reloads after a run: wait for the new row before reading it.
  await page.waitForFunction(() => document.querySelectorAll('#history tbody tr[data-key]').length >= 2, undefined, {timeout: 10000});
  r.check = await page.evaluate(() => {
    const card = document.querySelector('#check-result .st-alert');
    return {summary: document.querySelector('#check-result p').textContent, severity: card && card.querySelector('.gn-badge').textContent,
      drivers: card ? [...card.querySelectorAll('.drivers li')].map((li) => li.querySelector('.fam').textContent + ' ' + li.querySelector('.num').textContent) : [],
      impact: card ? [...card.querySelectorAll('dt')].some((d) => d.textContent === 'Financial impact') : null,
      link: card && card.querySelector('a') && card.querySelector('a').getAttribute('href'),
      historyRows: document.querySelector('#history tbody').rows.length};
  });
  // A finished check with no alert says the price and the rule.
  await page.selectOption('#check-region', 'CMIN'); await tap(page, '#check-run');
  await page.waitForFunction(() => !document.querySelector('#check-result .running') && document.getElementById('check-result').innerText.includes('No alert'), undefined, {timeout: 30000});
  r.quiet = await page.evaluate(() => document.getElementById('check-result').innerText);
  r.overflow = await overflow(page);
  // The link in the card opens the list on that alert; a check's alert is not in the list, so the
  // list says so and links to its row in the settings page's history.
  await page.goto(new URL(r.check.link, arg('signed')).href, {waitUntil: 'networkidle'}); await wait(500);
  r.notInList = await page.evaluate(() => {
    const box = document.getElementById('inbox-linked'); const a = box && box.querySelector('a');
    return {hidden: box ? box.hidden : null, text: box && box.textContent, href: a && a.getAttribute('href'),
      history: Boolean(document.getElementById('history'))};
  });
  // That link opens the settings page with the alert's history row scrolled to and marked.
  await page.goto(new URL(r.notInList.href || '/settings', arg('signed')).href, {waitUntil: 'networkidle'}); await wait(500);
  r.linked = await page.evaluate(() => {
    const row = document.querySelector('#history tr.linked');
    const box = row && row.getBoundingClientRect();
    return {rows: document.querySelectorAll('#history tr.linked').length, current: row && row.getAttribute('aria-current'),
      key: row && row.dataset.key, inView: Boolean(box && box.top >= 0 && box.bottom <= window.innerHeight),
      note: document.getElementById('history-note').textContent};
  });
  // The list signed in, at the shell's clock (the fixture's latest notice, 13:40): no assign buttons.
  await page.goto(arg('signed') + '/alerts', {waitUntil: 'networkidle'}); await wait(500);
  r.list = await readList(page);
  // An email's link to an alert in the list opens the list on it, marked.
  await page.goto(arg('signed') + '/alerts?alert=' + 'c'.repeat(24), {waitUntil: 'networkidle'}); await wait(500);
  r.listLinked = await page.evaluate(() => {
    const row = document.querySelector('#inbox tr.al-row.is-linked');
    const box = row && row.getBoundingClientRect();
    return {rows: document.querySelectorAll('#inbox tr.is-linked').length, key: row && row.dataset.key,
      current: row && row.getAttribute('aria-current'), inView: Boolean(box && box.top >= 0 && box.bottom <= window.innerHeight)};
  });
  r.log = log;
  report.signed = r;
  await context.close();
}

/* hostile ------------------------------------------------------------------------------------ */
{
  const {page, context, log} = await open(arg('hostile') + '/settings');
  await tap(page, '#check-run');
  await page.waitForSelector('#check-result .st-alert', {timeout: 30000});
  report.hostile = await page.evaluate(() => ({
    pwned: window.__pwned || null,
    images: document.querySelectorAll('#check-result img, #history img').length,
    scripts: document.querySelectorAll('#check-result script, #history script').length,
    links: [...document.querySelectorAll('#check-result a')].map((a) => a.getAttribute('href')),
    shownAsText: document.getElementById('check-result').innerText.includes('<img src=x'),
  }));
  report.hostile.log = log;
  await context.close();
}

/* nochecks ----------------------------------------------------------------------------------- */
{
  const {page, context, log} = await open(arg('nochecks') + '/settings');
  report.nochecks = await page.evaluate(() => ({notice: document.getElementById('notice').textContent,
    runDisabled: document.getElementById('check-run').disabled, editable: !document.getElementById('rules-fields').disabled}));
  report.nochecks.log = log;
  await context.close();
}

/* fail --------------------------------------------------------------------------------------- */
{
  const {page, context, log} = await open(arg('fail') + '/settings');
  const before = await page.evaluate(() => ({notice: document.getElementById('notice').textContent,
    history: document.querySelector('#history tbody').textContent, editable: !document.getElementById('rules-fields').disabled}));
  await context.close();
  const list = await open(arg('fail') + '/alerts');
  before.inbox = await list.page.evaluate(() => document.getElementById('inbox-empty').innerText);
  before.retry = await list.page.evaluate(() => [...document.querySelectorAll('#inbox-empty button')].map((b) => b.textContent));
  report.fail = {before, log: joinLogs(log, list.log)};
  await list.context.close();
}

/* password ----------------------------------------------------------------------------------- */
/* Signed out where sign-in is configured: the shell's sign-in screen covers the page (app design,
   screen 0). Its email and password form is driven here, from refusal to a signed-in edit. */
if (arg('password')) {
  const {page, context, log} = await open(arg('password') + '/settings');
  const r = {};
  const state = () => page.evaluate(() => {
    const $ = (id) => document.getElementById(id);
    const gate = document.querySelector('.gn-gate');
    const pageShown = Array.from(document.body.children).filter((n) => !n.classList.contains('gn-gate'))
      .some((n) => getComputedStyle(n).display !== 'none');
    return {gateVisible: Boolean(gate), pageShown, googleInGate: Boolean(gate && gate.querySelector('.gn-gate-google')),
      editable: !$('rules-fields').disabled, who: $('who').textContent,
      error: gate ? gate.querySelector('.gn-gate-status').textContent : '',
      passwordValue: $('gn-gate-password') ? $('gn-gate-password').value : '', notice: $('notice').textContent};
  });
  r.before = await state();
  // A typed password with no email: refused, and the password is still emptied.
  await page.type('#gn-gate-password', 'typed-without-email');
  await page.click('.gn-gate-primary'); await wait(200);
  r.noEmail = await state();
  r.noEmailTextHasPassword = await page.evaluate(() => document.body.innerText.includes('typed-without-email'));
  await page.type('#gn-gate-email', 'judge@example.test');
  await page.type('#gn-gate-password', 'not-the-password');
  await page.click('.gn-gate-primary'); await wait(300);
  r.wrong = await state();
  r.wrongTextHasPassword = await page.evaluate(() => document.body.innerText.includes('not-the-password'));
  await page.click('.gn-gate-primary'); await wait(200);
  r.empty = await state();
  await page.type('#gn-gate-password', 'fixture-password');
  await page.click('.gn-gate-primary'); await wait(600);
  r.after = await state();
  r.afterTextHasPassword = await page.evaluate(() => document.body.innerText.includes('fixture-password'));
  r.overflow = await overflow(page);
  r.log = log;
  report.password = r;
  await context.close();
}

await browser.close();
console.log(JSON.stringify(report));
