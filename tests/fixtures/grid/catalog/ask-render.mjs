/* Run the desk assistant's own script (src/grid/ask.js) against one baked plan set and print
   what it rendered, as one JSON object on stdout. Offline: no browser, no network, no library.

   The shim below implements exactly the DOM surface ask.js uses and throws on anything else,
   so a gap is a failure rather than a silent pass. It is an approximation of a browser: it
   proves the script loads the plan set and fills the mount from its fields, not that the
   layout looks right. The browser check is the orchestrator's.

     node tests/fixtures/grid/catalog/ask-render.mjs --root . --data <dir with views/> \
          [--stamp <16 hex>] [--page src/grid/ask.html] [--path /event/<id>] [--missing]

   --data is a bake directory (`tests/fixtures/grid/catalog/bake`, or a built `build/grid-data`)
   that carries `views/<key>.json`. --missing makes every fetch answer 404, proving the absent
   line. --path sets location.pathname, so the event page's key (the event's own id) is read
   the way the browser reads it; --search sets location.search (`?event=<id>` on the ask page).

   DOCK-2 adds three options, all offline:
     --session <file>  preloads the browser session's storage with that JSON (the dock's
                       threads, as a previous page left them); the report carries the storage
                       as the run left it (`session`).
     --agent <file>    a labelled fixture of the agent service (contract section 4): a signed-in
                       identity, given to the dock through a stand-in for the Firebase app the
                       alerts page starts, and the answers of GET threads, GET queue,
                       POST ask and POST confirm/{id}. Without it every /api/agent request
                       answers 404, as on a site where DOCK-5 has not mounted the routes.
                       With it the run also asks the fixture's question, records the first
                       screen, the answered turn, every agent request, and clicks the first
                       confirmation card's Confirm button the way a person clicks it
                       (--click decline clicks Decline). A fixture with "absent": true keeps
                       the person signed in and answers 404, as before DOCK-5 mounts; one with
                       "confirm_fails": true answers the confirm with 500. A confirm answer
                       carries the fixture's `confirm_receipt` (done, or refused with a key).
     --ask-text <q>    the unmatched free-text question the run asks (default: a question no
                       recorded question shares a word with). */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import vm from 'node:vm';

function fail(message) {
  console.log(JSON.stringify({ok: false, error: String(message)}));
  process.exit(1);
}

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const DATA = path.resolve(arg('data', path.join(ROOT, 'tests/fixtures/grid/catalog/bake')));
const STAMP = arg('stamp', '');
const PAGE = path.resolve(arg('page', path.join(ROOT, 'src/grid/ask.html')));
const PATHNAME = arg('path', '/ask');
const MISSING = argv.includes('--missing');
const SEARCH = arg('search', '');
const SESSION_FILE = arg('session', '');
const AGENT_FILE = arg('agent', '');
const CLICK = arg('click', 'confirm') === 'decline' ? 'decline' : 'confirm';
const ASK_TEXT = arg('ask-text', 'When will the synthetic sun rise?');
const AGENT_FIXTURE = AGENT_FILE ? JSON.parse(readFileSync(path.resolve(AGENT_FILE), 'utf8')) : null;

function attributes(source) {
  const attrs = {};
  const re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*"([^"]*)"/g;
  let found;
  while ((found = re.exec(source)) !== null) attrs[found[1]] = found[2];
  return attrs;
}

class Shim {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.attrs = {...attrs};
    this.children = [];
    this.listeners = {};
    this.dataset = {};
    this.html = '';
    this.value = '';
    for (const [key, value] of Object.entries(attrs)) this.setAttribute(key, value);
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
    if (name.startsWith('data-')) this.dataset[name.slice(5)] = String(value);
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  appendChild(child) { this.children.push(child); return child; }
  get innerHTML() { return this.html; }
  set innerHTML(value) { this.html = String(value); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatch(type, event = {}) { for (const fn of this.listeners[type] || []) fn(event); }
}

const page = readFileSync(PAGE, 'utf8');
const byId = new Map();
const all = [];
const tagRe = /<([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|[^>"])*)\/?>/g;
let match;
while ((match = tagRe.exec(page)) !== null) {
  const node = new Shim(match[1], attributes(match[2]));
  all.push(node);
  if (node.getAttribute('id')) byId.set(node.getAttribute('id'), node);
}
const mount = byId.get('ask');
if (!mount) fail('the page carries no #ask mount point');
if (STAMP) {
  const meta = byId.get('nowcast-build');
  if (!meta) fail('the page carries no nowcast-build meta element for the stamp');
  meta.setAttribute('content', STAMP);
}

const document = {
  getElementById: (id) => byId.get(id) || null,
  createElement: (tag) => new Shim(tag),
  addEventListener: () => {},
};

/* ---------- the browser session's storage ---------- */
const sessionData = new Map();
if (SESSION_FILE) {
  for (const [name, value] of Object.entries(JSON.parse(readFileSync(path.resolve(SESSION_FILE), 'utf8')))) {
    sessionData.set(name, typeof value === 'string' ? value : JSON.stringify(value));
  }
}
const sessionStorage = {
  getItem: (name) => (sessionData.has(name) ? sessionData.get(name) : null),
  setItem: (name, value) => { sessionData.set(name, String(value)); },
  removeItem: (name) => { sessionData.delete(name); },
};

/* ---------- the agent service, from the labelled fixture only ---------- */
const agentCalls = [];
function agentAnswer(wanted, init) {
  const method = (init && init.method) || 'GET';
  const body = init && init.body ? JSON.parse(init.body) : null;
  const auth = (init && init.headers && init.headers.Authorization) || null;
  const route = wanted.slice('/api/agent/'.length);
  agentCalls.push({method, route, body, auth});
  const answer = (status, payload) => Promise.resolve({ok: status >= 200 && status < 300, status,
                                                       json: async () => payload});
  if (!AGENT_FIXTURE || MISSING || AGENT_FIXTURE.absent === true) {
    return answer(404, {code: 'NOT_FOUND'});
  }
  if (method === 'GET' && route === 'threads') return answer(200, AGENT_FIXTURE.threads);
  if (method === 'GET' && route === 'queue') return answer(200, AGENT_FIXTURE.queue);
  if (method === 'POST' && route === 'ask') return answer(200, AGENT_FIXTURE.turn);
  if (method === 'POST' && route.startsWith('confirm/')) {
    if (AGENT_FIXTURE.confirm_fails === true) return answer(500, {code: 'STORE_UNAVAILABLE'});
    const id = decodeURIComponent(route.slice('confirm/'.length));
    const decision = body && body.decision;
    /* DOCK-3's answer: a confirmed decision carries the write's receipt (the fixture's
       `confirm_receipt`, done or refused); a declined one carries none. */
    const confirmed = decision === 'confirm';
    return answer(200, {confirmation_id: id, decided_at: AGENT_FIXTURE.decided_at,
                        state: confirmed ? 'confirmed' : 'declined',
                        receipt: confirmed && AGENT_FIXTURE.confirm_receipt
                          ? {...AGENT_FIXTURE.confirm_receipt, confirmation_id: id} : null});
  }
  return answer(404, {code: 'NOT_FOUND'});
}

/* ---------- fetching one baked plan set ---------- */
const fetched = [];
function fetchData(url, init) {
  const wanted = decodeURIComponent(String(url));
  fetched.push(wanted);
  if (wanted.startsWith('/api/agent/')) return agentAnswer(wanted, init);
  if (MISSING) return Promise.resolve({ok: false, status: 404});
  const name = wanted.replace(/^\/grid-data\/(?:[0-9a-f]{16}\/)?/, '');
  try {
    const payload = JSON.parse(readFileSync(path.join(DATA, name), 'utf8'));
    return Promise.resolve({ok: true, status: 200, json: async () => payload});
  } catch {
    return Promise.resolve({ok: false, status: 404});
  }
}

/* The signed-in identity, given the way the alerts page's Firebase app gives it: a started app
   whose auth reports one user. Present only with --agent. */
const firebase = AGENT_FIXTURE ? {
  auth: {},
  apps: [{}],
  app: () => ({auth: () => ({onAuthStateChanged: (callback) => {
    setTimeout(() => callback({email: AGENT_FIXTURE.identity.email, isAnonymous: false,
                               providerData: [{providerId: 'password'}],
                               getIdToken: async () => AGENT_FIXTURE.identity.token}), 0);
  }})}),
} : undefined;

const sandbox = {
  document,
  window: {addEventListener: () => {}, sessionStorage, firebase},
  sessionStorage,
  location: {pathname: PATHNAME, hash: '', search: SEARCH},
  fetch: fetchData,
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  console: {log: () => {}, warn: () => {}, error: () => {}},
};

try {
  vm.runInNewContext(readFileSync(path.join(ROOT, 'src/grid/ask.js'), 'utf8'), sandbox,
                     {filename: 'src/grid/ask.js'});
} catch (error) {
  fail('the panel script threw: ' + (error && error.stack ? error.stack : error));
}

const until = async (predicate, turns = 500) => {
  for (let turn = 0; turn < turns && !predicate(); turn += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
};
await until(() => sandbox.window.DeskAsk && sandbox.window.DeskAsk.state.present);
const W = sandbox.window.DeskAsk;
if (!W) fail('the panel never loaded: ' + fetched.join(', '));
await W.ready;
await until(() => W.state.present || (mount.innerHTML || '').includes('No recorded questions'));

const questions = () => {
  const html = mount.innerHTML || '';
  const re = /<button type="button" class="ak-q" data-q="(\d+)"[^>]*>([^<]*)<\/button>/g;
  const found = [];
  let hit;
  while ((hit = re.exec(html)) !== null) found.push({index: Number(hit[1]), question: hit[2]});
  return found;
};
const textOf = (name) => {
  const html = mount.innerHTML || '';
  const re = new RegExp('<p class="' + name + '"[^>]*>([\\s\\S]*?)<\\/p>');
  const hit = re.exec(html);
  return hit ? hit[1] : null;
};
const parts = () => {
  const html = mount.innerHTML || '';
  const re = /data-component="([a-z_]+)"/g;
  const found = [];
  let hit;
  while ((hit = re.exec(html)) !== null) found.push(hit[1]);
  return found;
};

const section = (html, name) => {
  const hit = new RegExp('<section class="' + name + '"[\\s\\S]*?<\\/section>').exec(html || '');
  return hit ? hit[0] : null;
};
const pClass = (html, name) => {
  const hit = new RegExp('<p class="' + name + '"[^>]*>([\\s\\S]*?)<\\/p>').exec(html || '');
  return hit ? hit[1] : null;
};
const dockOf = (html) => ({
  heading: /<h2>Ask Ingrid<\/h2>/.test(html || ''),
  who: pClass(html, 'ak-who'),
  cases: section(html, 'ak-cases'),
  queue: section(html, 'ak-queue'),
  threads: section(html, 'ak-threads'),
  budget: pClass(html, 'ak-budget'),
  form: /<form class="ak-form" data-ask-form>/.test(html || ''),
});

const report = {ok: true, page: PAGE, pathname: PATHNAME, stamp: STAMP || null, fetched,
                key: W.key, state: {missing: !W.state.present, views: W.state.views.length},
                questions: questions(), html: mount.innerHTML || '',
                absent: (mount.innerHTML || '')
                  .includes('No recorded questions for this page yet')};
report.dock = dockOf(report.html);

const cardsOf = (html) => (html.match(/<article class="ak-action(?: [^"]*)?"[\s\S]*?<\/article>/g) || [])
  .map((card) => ({action: (/data-action="([^"]+)"/.exec(card) || [])[1],
                   outcome: (/data-outcome="([^"]+)"/.exec(card) || [])[1],
                   name: pClass(card, 'ak-action-name'),
                   receipt: pClass(card, 'ak-action-receipt'),
                   html: card}));

/* The agent fixture's run: the first screen once the sign-in and the service answered, the
   fixture's question asked in the box, then the first confirmation card's Confirm clicked. */
if (AGENT_FIXTURE) {
  await until(() => W.state.api === 'present' || W.state.api === 'absent'
    || W.state.api === 'unauthorized');
  await W.settled();
  const first = mount.innerHTML || '';
  report.agent = {api: W.state.api, firstScreen: first, firstDock: dockOf(first)};
  await W.ask(AGENT_FIXTURE.ask);
  await W.settled();
  const answered = mount.innerHTML || '';
  report.agent.answered = answered;
  report.agent.actions = cardsOf(answered);
  report.agent.confirmCards = (answered.match(/<article class="ak-confirm"[\s\S]*?<\/article>/g) || [])
    .map((card) => ({id: (/data-confirmation="([^"]+)"/.exec(card) || [])[1],
                     state: (/data-state="([^"]+)"/.exec(card) || [])[1],
                     name: pClass(card, 'ak-action-name'),
                     buttons: (card.match(/data-(?:confirm|decline)="[^"]+"/g) || [])}));
  report.agent.text = pClass(answered, 'ak-text');
  report.agent.callsBeforeClick = agentCalls.map((call) => ({...call}));
  const card = report.agent.confirmCards.find((item) => item.id === AGENT_FIXTURE.click_id)
    || report.agent.confirmCards[0];
  if (card) {
    mount.dispatch('click', {target: {getAttribute: (name) => (name === 'data-' + CLICK ? card.id : null)}});
    await W.settled();
    report.agent.afterClick = mount.innerHTML || '';
    report.agent.actionsAfter = cardsOf(report.agent.afterClick);
  }
  report.agent.calls = agentCalls;
}

/* One answer per recorded question, selected the way a click selects it. */
report.answers = [];
for (let index = 0; index < W.state.views.length; index += 1) {
  W.select(index);
  const html = mount.innerHTML || '';
  report.answers.push({
    index,
    question: W.state.views[index].question,
    status: W.state.views[index].status,
    parts: parts(),
    text: textOf('ak-text'),
    cutoff: textOf('ak-cutoff'),
    insufficient: textOf('ak-insufficient'),
    receiptFolded: /<details class="ak-receipt">/.test(html) && !/<details class="ak-receipt" open>/.test(html),
    notShownFolded: /<details class="ak-not-shown">/.test(html),
    stability: textOf('ak-stability'),
    labels: textOf('ak-labels'),
    asof: (html.match(/<p class="ak-asof">[\s\S]*?<\/p>/g) || []),
    recordRefs: (html.match(/Record [a-z_]+ <span class="mono">[^<]+<\/span>/g) || []),
    html,
  });
}

/* The free text box answers with the recorded question it matches, or insufficient. With the
   agent fixture the box asks the service instead, which the run above records. */
if (!AGENT_FIXTURE) {
W.ask('What was the price doing around the trip?');
report.matched = {selected: W.state.selected, status: W.state.status,
                  question: W.state.selected === null ? null
                    : W.state.views[W.state.selected].question};
W.ask(ASK_TEXT);
report.unmatched = {selected: W.state.selected, status: W.state.status,
                    offer: W.state.offer, html: mount.innerHTML || ''};
}
report.session = Object.fromEntries(sessionData);

/* A compiled plan set is not assumed: the report carries the file's own answer shape. */
console.log(JSON.stringify(report, null, 1));
