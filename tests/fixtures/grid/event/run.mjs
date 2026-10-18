/* Run the event adapter (src/grid/event-api.js) and print what it did, as one JSON object on
   stdout. Offline by default: the transport replays the recorded flow (flow.json) and refuses
   a request body that differs from the recorded one, so the calls the adapter makes are the
   calls the real review core accepted when the fixture was built. With --base it talks to a
   running server instead (the container's demo mode, or
   `NOWCAST_ENV=demo .local/h1-venv/bin/python -m uvicorn src.api.hosted:app --factory`), and
   the same script proves the judge's path end to end over HTTP.

     node tests/fixtures/grid/event/run.mjs --root .
       [--fixture tests/fixtures/grid/event] [--base http://127.0.0.1:PORT]

   The recorded flow runs three decisions — retain, revise, then retain, so a decision after a
   revision is covered — and prints the history after each. Each decision is one `POST
   .../prepare` (heads, snapshot and compiled task together, PERF-3) and one `POST .../reviews`.
   Without --base it also runs a deployment without `/demo/session` (local mode), a route
   refusal, a prepare the case moved under, the three history failures the page must show rather
   than hide (an expired session 401, an unavailable store 503 and an answer that is not a list
   200), and the three read-back failures that follow a saved decision: an HTTP refusal (503), a
   transport error and a malformed body. In each of those, the save's receipt must survive with
   the failure beside it, and the next decision must re-read the accepted outlook before
   anything is sent — a stale cutoff never reaches the routes. `--base` replaces the recorded
   answers with the live ones and skips the injected scenarios, which a live server cannot be
   asked for. */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import vm from 'node:vm';

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.lastIndexOf('--' + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback;
};
const ROOT = path.resolve(arg('root', '.'));
const FIXTURE = path.resolve(arg('fixture', path.join(ROOT, 'tests/fixtures/grid/event')));
const BASE = arg('base', '');
const EVENT = arg('event', '');

const SOURCE = readFileSync(path.join(ROOT, 'src/grid/event-api.js'), 'utf8');
const view = JSON.parse(readFileSync(path.join(FIXTURE, 'view.json'), 'utf8'));
// The flow file carries both the recorded answers and the decisions' choices; a live run
// takes only the choices from it.
const flow = JSON.parse(readFileSync(path.join(FIXTURE, 'flow.json'), 'utf8'));
const eventId = EVENT || view.id;
const problems = [];

/* ---------- small helpers ---------- */
const canonical = (value) => {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  }
  return JSON.stringify(value === undefined ? null : value);
};
const parse = (body) => {
  if (body === undefined || body === null) return null;
  try { return JSON.parse(body); } catch (err) { return String(body); }
};
const pick = (body, keys) => {
  const out = {};
  for (const key of keys) out[key] = body ? body[key] : undefined;
  return out;
};

/* What the adapter sends to `POST .../reviews`: the fields the frozen `ReviewBody` carries
   from the client. The recorded review request also holds the case, the times and the
   optional judgment reference, which the route adds, so only these keys are compared. */
const REVIEW_KEYS = ['request_id', 'idempotency_key', 'task_ref', 'snapshot_digest',
  'expected_assumption_head', 'expected_outlook_head', 'disposition', 'rationale', 'new_value'];

function record(calls, method, url, options) {
  const entry = {method, path: String(url).replace(BASE, ''),
    auth: ((options.headers || {}).authorization || '').replace(/^Bearer .+$/, 'Bearer <token>'),
    body: parse(options.body)};
  calls.push(entry);
  return entry;
}

/* ---------- one adapter instance per scenario ---------- */
async function adapter(transport) {
  const sandbox = {window: {}, fetch: transport, console: {log: () => {}, warn: () => {}, error: () => {}}};
  vm.runInNewContext(SOURCE, sandbox, {filename: 'src/grid/event-api.js'});
  return sandbox.window.EventAPI;
}

const answer = (status, body) => ({ok: status < 400, status, json: async () => body});

/* The recorded transport: the answers are the recorded ones, and each request body must be
   the body the recorded run sent, so a drifting adapter fails here rather than passing on a
   transport that answers anything. `settings.readFailure` answers the first `/read` — the one
   that follows the first save — with that failure instead of the recorded acceptance; every
   later read, the retry the next decision makes included, is answered normally. */
function recordedTransport(calls, settings = {}) {
  const history = [];
  let step = 0;
  let readFailed = false;
  return async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase();
    const target = String(url);
    const entry = record(calls, method, url, options);
    if (target === '/demo/session') return answer(200, flow.session);
    if (target.startsWith('/grid-data/events/')) {
      return target === '/grid-data/events/' + eventId + '.json' ? answer(200, view) : answer(404, null);
    }
    if (method === 'GET' && target.endsWith('/history')) return answer(200, history.slice());
    const step_ = flow.decisions[step];
    if (method === 'GET') {
      problems.push('a case read the adapter does not make: ' + method + ' ' + target);
      return answer(500, null);
    }
    if (target.endsWith('/read')) {
      // The read that follows a save names the outlook that save was accepted as; a later
      // decision audits that record's own instant.
      const saved = flow.decisions[step - 1];
      if (!saved) { problems.push('a read does not follow a recorded decision: ' + target); return answer(500, null); }
      if (canonical(entry.body) !== canonical({ref: saved.receipt.outlook_ref})) {
        problems.push('the read body is not the accepted outlook: ' + JSON.stringify(entry.body));
      }
      if (settings.readFailure && !readFailed) { readFailed = true; return settings.readFailure(); }
      return answer(200, saved.acceptance);
    }
    if (!step_) { problems.push('unexpected request after the recorded decisions: ' + method + ' ' + target); return answer(500, null); }
    if (target.endsWith('/prepare')) {
      // The one call that answers heads, snapshot and compiled task. The audit cutoff moves with
      // the accepted state and the information cutoff stays the event's historical posting time;
      // the recorded body per decision is what the adapter must send.
      if (canonical(entry.body) !== canonical(step_.prepare)) {
        problems.push('the prepare body is not the recorded one: ' + JSON.stringify(entry.body));
      }
      return answer(200, {heads: step_.heads, snapshot: step_.snapshot, task: step_.compile});
    }
    if (target.endsWith('/snapshots') || target.endsWith('/compile')) {
      problems.push('a call the adapter no longer makes: ' + method + ' ' + target);
      return answer(500, null);
    }
    if (target.endsWith('/reviews')) {
      if (canonical(pick(entry.body, REVIEW_KEYS)) !== canonical(pick(step_.review, REVIEW_KEYS))) {
        problems.push('the review body differs from the recorded one: ' + JSON.stringify(entry.body));
      }
      history.push(flow.history[step]);
      step += 1;
      return answer(200, step_.receipt);
    }
    problems.push('the recorded transport has no answer for ' + method + ' ' + target);
    return answer(500, null);
  };
}

const liveTransport = (calls) => async (url, options = {}) => {
  const response = await fetch(BASE + url, options);
  record(calls, (options.method || 'GET').toUpperCase(), url, options);
  const text = await response.text();
  return answer(response.status, text ? JSON.parse(text) : null);
};

/* ---------- the scenarios ---------- */
async function flowScenario() {
  const calls = [];
  const api = await adapter(BASE ? liveTransport(calls) : recordedTransport(calls));
  const loaded = await api.load(eventId);
  const decisions = [await api.decide(flow.decisions[0].choice)];
  const first = await api.history();
  decisions.push(await api.decide(flow.decisions[1].choice));
  const second = await api.history();
  decisions.push(await api.decide(flow.decisions[2].choice));
  const third = await api.history();
  return {view: {id: loaded.id, advisory: loaded.advisory && loaded.advisory.t},
    decisions, history: [first, second, third], calls};
}

async function localScenario() {
  const calls = [];
  const transport = async (url, options = {}) => {
    record(calls, (options.method || 'GET').toUpperCase(), url, options);
    if (String(url).startsWith('/grid-data/events/')) return answer(200, view);
    return answer(404, null);
  };
  const api = await adapter(transport);
  const loaded = await api.load(eventId);
  const decided = await api.decide(flow.decisions[0].choice);
  const history = await api.history();
  return {view: loaded.id, decision: decided, history, calls};
}

/* The review route refuses the decision: the case moved, so the recorded receipt is never
   handed back and the page must show the refusal's code and sentence. The prepare call
   still answers the recorded state, so the refusal comes from the post, exactly as it does
   when another writer moves the case between the two calls. */
async function refusalScenario() {
  const calls = [];
  const step = flow.decisions[0];
  const transport = async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase();
    const target = String(url);
    record(calls, method, url, options);
    if (target === '/demo/session') return answer(200, flow.session);
    if (target.startsWith('/grid-data/events/')) return answer(200, view);
    if (method === 'GET' && target.endsWith('/history')) return answer(500, null);
    if (target.endsWith('/prepare')) {
      return answer(200, {heads: step.heads, snapshot: step.snapshot, task: step.compile});
    }
    return answer(409, {code: 'STALE_HEAD'});
  };
  const api = await adapter(transport);
  await api.load(eventId);
  const decided = await api.decide(step.choice);
  const history = await api.history();
  return {decision: decided, history, calls};
}

/* The one call refuses — the state the case is in cannot be decided from, so the endpoint
   answers its own code rather than naming an assumption — and nothing is posted: the refusal
   reaches the page as that code and its sentence. */
async function prepareRefusalScenario() {
  const calls = [];
  const step = flow.decisions[0];
  const transport = async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase();
    const target = String(url);
    record(calls, method, url, options);
    if (target === '/demo/session') return answer(200, flow.session);
    if (target.startsWith('/grid-data/events/')) return answer(200, view);
    if (target.endsWith('/prepare')) {
      return answer(422, {code: 'PREPARE_ASSUMPTION_COUNT'});
    }
    return answer(500, null);
  };
  const api = await adapter(transport);
  await api.load(eventId);
  const decided = await api.decide(step.choice);
  return {decision: decided, calls};
}

/* A history read that fails is shown, not hidden: one scenario per failure the review named.
   The session is opened by a first decision, exactly as the page opens it, and the history
   route then answers the failure. */
async function historyFailureScenario(failure) {
  const calls = [];
  const step = flow.decisions[0];
  const transport = async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase();
    const target = String(url);
    record(calls, method, url, options);
    if (target === '/demo/session') return answer(200, flow.session);
    if (target.startsWith('/grid-data/events/')) return answer(200, view);
    if (method === 'GET' && target.endsWith('/history')) return failure();
    if (target.endsWith('/prepare')) {
      return answer(200, {heads: step.heads, snapshot: step.snapshot, task: step.compile});
    }
    if (target.endsWith('/reviews')) return answer(200, step.receipt);
    if (target.endsWith('/read')) return answer(200, step.acceptance);
    return answer(500, null);
  };
  const api = await adapter(transport);
  await api.load(eventId);
  const decided = await api.decide(step.choice);
  const history = await api.history();
  return {decision: decided, history, calls};
}

/* The read that follows a saved decision can fail three ways. In each, the first decision's
   answer must keep its receipt and name the failure, and the second decision must re-read the
   accepted outlook before it sends anything: the retry appears in `calls`, and the transport
   refuses a prepare body whose audit cutoff is not the instant that read named. */
async function refreshFailureScenario(failure) {
  const calls = [];
  const api = await adapter(recordedTransport(calls, {readFailure: failure}));
  await api.load(eventId);
  const first = await api.decide(flow.decisions[0].choice);
  const second = await api.decide(flow.decisions[1].choice);
  const history = await api.history();
  return {decisions: [first, second], history, calls};
}

const report = {ok: true, transport: BASE ? 'live' : 'recorded', event: eventId,
  base: BASE || null, problems};
try {
  report.flow = await flowScenario();
  if (!BASE) {
    report.local = await localScenario();
    report.refusal = await refusalScenario();
    report.prepare_refusal = await prepareRefusalScenario();
    report.history_failures = {
      unauthorized: await historyFailureScenario(() => answer(401, {code: 'UNAUTHENTICATED'})),
      storage: await historyFailureScenario(() => answer(503, {code: 'STORAGE_UNAVAILABLE'})),
      malformed: await historyFailureScenario(() => ({ok: true, status: 200,
        json: async () => { throw new Error('the answer was not JSON'); }})),
    };
    report.refresh_failures = {
      storage: await refreshFailureScenario(() => answer(503, {code: 'STORAGE_UNAVAILABLE'})),
      transport: await refreshFailureScenario(() => { throw new Error('the connection was dropped'); }),
      malformed: await refreshFailureScenario(() => ({ok: true, status: 200,
        json: async () => { throw new Error('the answer was not JSON'); }})),
      no_instant: await refreshFailureScenario(() => answer(200, {})),
    };
  }
} catch (error) {
  report.ok = false;
  report.error = String((error && error.stack) || error);
}
if (problems.length) report.ok = false;
console.log(JSON.stringify(report, null, 1));
if (!report.ok) process.exit(1);
