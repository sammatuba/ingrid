/* Event data adapter: the judge's own copy of the real PEDC event case.
   The design file (src/grid/event.js) renders the view model this module returns:
     load(id) -> { id, title, grid, event_at, advisory{id,t,text}, timeline[{t,kind,text,src}],
                   market{t[],lmp[],short[],imp[],marks[{t,kind}]}, figures[{k,v,unit,d,up}],
                   assumption{value,unit,proposition,kv[[k,v]]},
                   judgment|null{label,rule,by,questions[{id,label,answers[4],modal,agree[4],key}],receipt} }
     decide({decision,value,reason}) -> { ok, message }      history() -> [{t,what,reason,who}]

   `load` reads the baked view model; the recorded judgment is in that file, so no model call
   happens on a page load. `priceOutlook` (DESK-1) reads the event's register-and-price-outlook
   view from the same bake — the event's assumption looked up in the assumption register, and
   the issued price outlooks of the archive. That is the PRICE outlook of the archive; the
   review core's own accepted outlook (the record `decide` re-reads after a save, named by
   `outlook_ref` and read by `adopt`) is a different record on a different copy and keeps its
   own name. `decide` creates the judge's sandbox session once per page load
   (`POST /demo/session`, an empty body and no credentials), prepares the decision in one call
   (`POST .../prepare`, which answers the case heads, the snapshot of the accepted state and the
   review task compiled at the event's recorded information cutoff) and posts the decision to
   the session's own copy of the case; after a save it reads the accepted outlook back, so a
   later decision snapshots the state the case is actually in while the compile keeps the
   event's historical cutoff. The decision is therefore two round trips: prepare, then post.
   The review itself still carries the heads it was prepared against, so the route refuses a
   decision whose case moved since the page loaded (`STALE_HEAD`).
   `history` reads that case's history, newest first. Nothing is swallowed: a refusal from any
   route comes back as its code and a sentence, and the page shows it — a history read that
   fails is the one marked row below, carrying that code and sentence, never an empty list; a
   read-back that fails keeps the save's receipt and names the failure, and the session stays
   behind the accepted state until the next decision re-reads it, so a stale cutoff is never
   sent. */
window.EventAPI = (() => {
  'use strict';
  /* The build stamp the page was served under: the application writes it into the asset URLs and
     into `meta#nowcast-build`, so the baked view model is read from the same build as this
     script. A page served without a stamp (a fixture harness serving the source HTML, or a run
     with no document at all) reads the unversioned name, which is never cached. */
  const STAMP = (() => {
    const meta = typeof document !== 'undefined' && document.getElementById
      ? document.getElementById('nowcast-build') : null;
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP;
  const JUDGE_TENANT = 'demo-judge';
  const LOCAL = { ok: false, message: 'Decisions are recorded on the hosted demo.' };
  // One sentence per refusal code this flow can produce; the code itself is always shown
  // verbatim, and an unknown code or a non-JSON answer is shown as HTTP <status>.
  const SENTENCES = {
    UNAUTHENTICATED: 'the judge session is no longer valid; reload the page',
    SESSION_UNAVAILABLE: 'the demo sandbox is full; try again later',
    STORAGE_UNAVAILABLE: 'the demo store is unavailable; try again',
    MALFORMED_TIME: 'the recorded times do not line up for this decision',
    INVALID_RECORD: 'the decision was not accepted as a record',
    ACCESS_DENIED: 'this session may not act on that case',
    NOT_FOUND: 'the case or route was not found',
    MISSING_INPUT: 'the case is missing something the decision needs',
    UNRESOLVED_MAPPING: 'the mapping does not resolve at that cutoff',
    STALE_HEAD: 'the case moved since this page loaded, so reload the page and decide again',
    STALE_DEPENDENCY: 'the case moved since this page loaded, so reload the page and decide again',
    PREPARE_ASSUMPTION_COUNT: 'the case does not hold exactly one assumption to decide on',
    REVISION_CONFLICT: 'the case already holds a different revision of that record',
    IDEMPOTENCY_CONFLICT: 'that decision key was already used with different contents',
    BLOCKED_TASK: 'the compiled task is blocked; its decision cannot be recorded',
    JUDGMENT_TASK_MISMATCH: 'the named judgment belongs to another task',
  };
  let view = null, session = null, local = false, decisions = 0;

  const manila = (iso) => {
    const at = new Date(iso);
    if (!iso || Number.isNaN(at.getTime())) return String(iso || '');
    return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Manila', day: 'numeric', month: 'short',
      year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(at) + ' Manila';
  };
  const ref = (record) => ({ record_kind: record.record_kind, record_id: record.record_id,
    revision_id: record.revision_id, content_digest: record.content_digest });
  const refusal = (result) => ({ ok: false, message: (result.code || 'HTTP ' + result.status) +
    (SENTENCES[result.code] ? ': ' + SENTENCES[result.code] : '') });
  /* The history card's row for a read that failed. The page's renderer (src/grid/event.js)
     draws `who`, `t`, `what` and `reason` for every row, so the refusal is visible in the list
     the page writes, with the route's own code and sentence; `who` marks the row as a state
     and not an entry, and no timestamp or reason is invented for it. */
  const problem = (message) => [{ t: '', who: 'History unavailable', what: message, reason: '' }];

  async function request(path, options) {
    const response = await fetch(path, options);
    let body = null;
    try { body = await response.json(); } catch (err) { body = null; }
    return { ok: response.ok, status: response.status, code: body && body.code, body };
  }

  const casePath = (suffix) => '/v1/tenants/' + encodeURIComponent(session.tenant) +
    '/cases/' + encodeURIComponent(session.case) + (suffix || '');

  /* The information cutoff is the event's own recorded posting time, read from the baked view
     model (Manila civil time, as every advisory time is stored). A view model without one is a
     refusal: the cutoff is never guessed. */
  function informationCutoff() {
    const text = String((view && view.advisory && view.advisory.t) || '').trim();
    const stamp = text.replace(' ', 'T');
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(stamp)) return null;
    return (stamp.length === 16 ? stamp + ':00' : stamp) + '+08:00';
  }

  async function open() {
    const created = await request('/demo/session', { method: 'POST' });
    if (created.status === 404) { local = true; return LOCAL; }
    const body = created.body || {};
    if (!created.ok) return refusal(created);
    if (!body.id_token || !body.event_case || !body.event_seeded_at) {
      return { ok: false, message: 'This session carries no event case, so the decision was not recorded.' };
    }
    /* `state_at` is the instant of the accepted state the next snapshot audits: the seeding
       instant until this page records a decision, then the instant that decision was accepted
       (`adopt`). It is always a server instant; the browser's clock decides nothing.
       `pending` is the outlook a save accepted and this page has still to adopt — the session
       is behind the case while it is set, and no decision may be sent until the re-read works. */
    session = { token: body.id_token, tenant: body.tenant || JUDGE_TENANT, case: body.event_case,
      state_at: body.event_seeded_at, pending: null };
    return { ok: true };
  }

  /* The decision just recorded becomes the state the next one audits: its accepted outlook is
     read back from the case and its own `recorded_at` — the server's clock — becomes the next
     snapshot's audit cutoff. Only the audit moves; the compile keeps the event's historical
     information cutoff, so the judge still decides on the evidence as it stood at the advisory.
     A read that fails — an HTTP refusal, a transport error, an answer that names no accepted
     instant — is not swallowed: it is returned as its code and a sentence, and the outlook
     stays `pending`, so the page can show the save's receipt beside the failure and the next
     decision re-reads that outlook before anything else. `pending.ref` is null when a receipt
     named no outlook at all: the accepted state is then unknown, and the session stays behind
     until a re-read can place it — a cutoff the case has moved past is never sent. */
  async function adopt(headers, pending) {
    const accepted = pending && pending.ref;
    if (!accepted) {
      session.pending = { ref: null };
      return { ok: false, message: 'the saved receipt names no accepted outlook to re-read' };
    }
    let read;
    try {
      read = await request(casePath('/read'), { method: 'POST', headers,
        body: JSON.stringify({ ref: accepted }) });
    } catch (err) {
      session.pending = { ref: accepted };
      return { ok: false, message: 'The demo could not be reached: ' + (err && err.message ? err.message : err) };
    }
    if (!read.ok) {
      session.pending = { ref: accepted };
      return { ok: false, message: refusal(read).message };
    }
    if (!read.body || !read.body.recorded_at) {
      session.pending = { ref: accepted };
      return { ok: false, message: 'HTTP ' + read.status + ': the read answer names no accepted instant' };
    }
    session.state_at = read.body.recorded_at;
    session.pending = null;
    return { ok: true };
  }

  async function record(choice) {
    if (!view) return { ok: false, message: 'The event is not loaded yet; reload the page.' };
    if (!session) {
      const opened = await open();
      if (!opened.ok) return opened;
    }
    const headers = { 'authorization': 'Bearer ' + session.token, 'content-type': 'application/json' };
    /* A decision is never sent on a cutoff the case has moved past. When the read that followed
       the previous save failed, the accepted outlook is re-read here, before anything else; if
       it still cannot be read, the decision is refused with that failure's code and sentence. */
    if (session.pending) {
      const refreshed = await adopt(headers, session.pending);
      if (!refreshed.ok) {
        return { ok: false, message: 'The accepted state could not be re-read, so the decision ' +
          'was not sent: ' + refreshed.message };
      }
    }
    const cutoff = informationCutoff();
    if (!cutoff) {
      return { ok: false, message: 'The event carries no recorded posting time, so the decision was not recorded.' };
    }
    /* The decision is prepared in one call: the case heads, the snapshot of the accepted state
       and the task compiled at the event's recorded cutoff come back together, so this page
       spends one round trip here and one on the post. The review that follows still carries the
       heads and the snapshot it was prepared against — and the route re-checks them — so a case
       that moved since the page loaded is still refused (`STALE_HEAD`). The audit cutoff is the
       accepted state this decision audits, and the information cutoff stays the event's own
       posting time; the endpoint's own guards apply to both. */
    const prepared = await request(casePath('/prepare'), { method: 'POST', headers,
      body: JSON.stringify({ audit_cutoff: session.state_at, information_cutoff: cutoff }) });
    if (!prepared.ok) return refusal(prepared);
    const prepared_body = prepared.body || {};
    const heads = prepared_body.heads || {};
    const task = prepared_body.task;
    if (!task || !task.payload || !task.payload.snapshot_ref || !task.payload.assumption_ref) {
      return { ok: false, message: 'HTTP ' + prepared.status + ': the prepare answer names no compiled task' };
    }
    const payload = task.payload;
    const definition = (payload.assumption_definition || {}).value || {};
    decisions += 1;
    const key = 'event:' + view.id + ':' + choice.decision + ':' + decisions;
    const saved = await request(casePath('/reviews'), { method: 'POST', headers,
      body: JSON.stringify({
        request_id: key, idempotency_key: key, task_ref: ref(task),
        snapshot_digest: payload.snapshot_ref.content_digest,
        expected_assumption_head: payload.assumption_ref,
        expected_outlook_head: heads.outlook || null,
        disposition: choice.decision, rationale: choice.reason,
        new_value: choice.decision === 'revise'
          ? { value: String(choice.value), quantity_kind: definition.quantity_kind, unit: definition.unit }
          : null,
      }) });
    if (!saved.ok) return refusal(saved);
    /* The decision is recorded, so the answer is `ok` and the receipt is kept whatever the
       read-back does; a failed read-back is named beside it, in the same code and sentence the
       page shows for any refusal. */
    const refreshed = await adopt(headers, { ref: (saved.body && saved.body.outlook_ref) || null });
    return { ok: true, message: 'Saved · receipt ' + key + (refreshed.ok ? ''
      : ' · the accepted state could not be re-read: ' + refreshed.message) };
  }

  /* PERF-6: event.js and event-desk.js both read the event's view and its drivers card; one
     request for each serves both. Each caller gets its own copy of the answer, as two requests
     gave it before; a read that failed (a dropped connection, a malformed body, a status other
     than 404) is forgotten, so the next caller asks again. */
  const reads = new Map();
  const copy = (x) => (x === null || x === undefined ? x : JSON.parse(JSON.stringify(x)));
  function readOnce(url) {
    if (!reads.has(url)) {
      const answer = fetch(url).then(async (response) => {
        if (!response.ok) {
          if (response.status !== 404) reads.delete(url);
          return { ok: false, status: response.status };
        }
        return { ok: true, body: await response.json() };
      });
      answer.catch(() => reads.delete(url));
      reads.set(url, answer);
    }
    return reads.get(url).then((r) => (r.ok ? { ok: true, body: copy(r.body) } : r));
  }

  function describe(outlook) {
    const difference = outlook.difference || {};
    const value = (difference.new_value || difference.old_value || {});
    if (difference.kind === 'revised') return 'Revised to ' + value.value + ' ' + value.unit;
    if (difference.kind === 'no_change') return 'Retained ' + value.value + ' ' + value.unit;
    const issue = (outlook.open_issues || [])[0] || {};
    if (issue.disposition === 'investigate') return 'Left open for investigation';
    return 'Left open (' + (issue.disposition || 'open') + ')';
  }

  return {
    async load(id) {
      const read = await readOnce(DATA + 'events/' + encodeURIComponent(id) + '.json');
      if (!read.ok) throw new Error('no such event');
      view = read.body;
      return view;
    },
    /* DESK-1: the event's register-and-price-outlook view, from the same bake as the view
       model and under the same stamped `/grid-data/` prefix — no route of its own. A file that
       cannot be read is answered as null rather than thrown: the page then shows nothing for
       the section (copy rule 4), and a page served without the file stays usable. */
    async priceOutlook(id) {
      try {
        const response = await fetch(DATA + 'outlook/' + encodeURIComponent(id) + '.json');
        if (!response.ok) return null;
        const body = await response.json();
        return body && typeof body === 'object' && !Array.isArray(body) ? body : null;
      } catch (err) {
        return null;
      }
    },
    /* The alert inbox at the as-of clock (`/api/alerts/inbox?view=all&at=`), for the event's
       "More detail" rows: alerts the record links to the event and those around the same time.
       Read through the shell's one inbox reader (`GNShell.inbox`, PERF-6), so the ticker's read
       of the same time is the same request; the signed-in token goes along where there is one,
       and a read that fails is null. */
    async alerts(at) {
      try {
        const shell = window.GNShell;
        const body = shell && shell.inbox ? await shell.inbox(at, { view: 'all' }) : null;
        return body && typeof body === 'object' && Array.isArray(body.groups) ? body : null;
      } catch (err) {
        return null;
      }
    },
    /* O5 (ontology): the event's likely-drivers card, baked by scripts/ontology/bake_panel.py
       into `ontology/<id>.json` under the same stamped prefix. As for the price outlook, a file
       that cannot be read is answered as null, and the page then leaves the card off. */
    async drivers(id) {
      try {
        const read = await readOnce(DATA + 'ontology/' + encodeURIComponent(id) + '.json');
        if (!read.ok) return null;
        const body = read.body;
        /* The whole public shape is checked before the page draws anything: a bake that does not
           match it is answered as null, so the card stays off rather than half drawn. */
        const isObject = (v) => !!v && typeof v === 'object' && !Array.isArray(v);
        const listOrAbsent = (v) => v === undefined || v === null || Array.isArray(v);
        const modeOk = (m) => isObject(m) && ['facts', 'withheld', 'unconfirmed', 'fuel_timing'].every((k) => listOrAbsent(m[k]));
        const ok = isObject(body) && isObject(body.modes) && Object.keys(body.modes).length > 0
          && Object.values(body.modes).every(modeOk)
          && (body.drivers === undefined || body.drivers === null
              || (isObject(body.drivers) && Object.values(body.drivers).every((rows) => Array.isArray(rows) && rows.every(isObject))))
          && (body.summary === undefined || body.summary === null || (isObject(body.summary) && listOrAbsent(body.summary.what_to_check)))
          && (body.paragraph === undefined || body.paragraph === null || isObject(body.paragraph))
          /* how the record was made, read by the "How we got this" modal (flow.js); optional */
          && (body.provenance === undefined || body.provenance === null || isObject(body.provenance));
        return ok ? body : null;
      } catch (err) {
        return null;
      }
    },
    async decide(choice) {
      try {
        return await record(choice);
      } catch (err) {
        // A transport failure is a refusal too, and it is named rather than swallowed.
        return { ok: false, message: 'The demo could not be reached: ' + (err && err.message ? err.message : err) };
      }
    },
    async history() {
      // No session means no action has opened the judge's sandbox, so this session has
      // recorded nothing: an empty list, not a failure to report.
      if (!session) return [];
      let result;
      try {
        result = await request(casePath('/history'),
          { headers: { 'authorization': 'Bearer ' + session.token } });
      } catch (err) {
        // A transport failure is a refusal too, and it is named rather than swallowed.
        return problem('The demo could not be reached: ' + (err && err.message ? err.message : err));
      }
      if (!result.ok || !Array.isArray(result.body)) {
        return problem(result.ok && !result.code
          ? 'HTTP ' + result.status + ': the history answer is not a list of entries'
          : refusal(result).message);
      }
      return result.body.map((outlook) => {
        const payload = outlook.payload || {};
        return { t: manila(payload.reviewed_at), what: describe(payload),
          reason: (payload.difference || {}).rationale || '', who: 'You (this session)',
          decision_ref: payload.decision_ref || null };
      }).reverse();
    },
    /* EXPL-1: the decision record an outlook names (`decision_ref`), read from the judge's own
       copy, so what an entry shows about its judgment comes from the record: the task it was
       compiled against and the judgment reference it carries, which is null when the decision
       named no judgment artifact. A read that fails is returned as its code and sentence. */
    async decision(ref) {
      if (!session || !ref) return { ok: false, message: 'no decision record to read' };
      let result;
      try {
        result = await request(casePath('/read'), { method: 'POST',
          headers: { 'authorization': 'Bearer ' + session.token, 'content-type': 'application/json' },
          body: JSON.stringify({ ref }) });
      } catch (err) {
        return { ok: false, message: 'The demo could not be reached: ' + (err && err.message ? err.message : err) };
      }
      if (!result.ok || !result.body) return { ok: false, message: refusal(result).message };
      const payload = result.body.payload || {};
      return { ok: true, record_id: result.body.record_id || ref.record_id,
        task: payload.task_ref ? payload.task_ref.record_id : null,
        judgment: payload.judgment_ref ? payload.judgment_ref.record_id : null,
        disposition: payload.disposition || null, reviewed_at: manila(payload.reviewed_at) };
    },
  };
})();
