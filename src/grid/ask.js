/* The desk dock. Design file: the governed generative view as a native panel (VIEW-1), grown
   into the persistent shell every page carries (DOCK-2, strategy 2026-10-18 section 1, agent
   contract sections 1, 3 and 4). One component, mounted into the `<section id="ask">` ROUTES-1
   put on every page; no page loads anything new for it.

   What the dock shows, top to bottom, and where every word comes from:
   * the sign-in state: who is signed in, or "Sign in to ask live" for an anonymous visitor.
     Sign-in is the alerts page's Firebase sign-in: the dock reads the Firebase app a page has
     already started and never starts one itself;
   * the open cases: the signed-in person's case threads from the agent service, or, for an
     anonymous visitor and wherever the service does not answer, the cases opened in this
     browser session, from an empty, labelled state;
   * the queue: the items the agent service says await the person's decision (pending
     confirmations, outlook vintages that rest on a changed belief, drafts), or an empty,
     labelled state;
   * the threads: one per case and one desk thread, with a switch between them. Opening an
     event switches the dock to that case's thread. An anonymous visitor's threads live in
     this browser session only (sessionStorage), never on the server;
   * the suggested questions: the recorded questions of this page's plan set, one button each;
   * a free-text ask box. Signed in with the agent service present, a question goes to
     `POST /api/agent/ask`; otherwise it matches a recorded question or any of its four
     recorded wordings, or answers with the insufficient sentence below and offers the
     nearest recorded answer;
   * the answer, skeleton first (the parts the plan shows, and the parts it left out with
     their reasons), then the components, each from its record fields with the record's
     identifier, digest and cutoff basis beside it, then the folded receipt;
   * the action cards: each action the agent ran, named from its arguments ("Opened page
     ...", "Ran exposure for ...", "Drafted ..."), with its receipt line;
   * the confirmation cards: a write action stops at a card that says what will be written,
     where and under which receipt, with one click each way. The dock never confirms for the
     person; only a click on the card's own button sends `POST /api/agent/confirm/{id}`;
   * the budget line: the agent service's day meter as it states it.

   Plan sets arrive in shape view.v3 (the composer filled `text`) or view.v4 (no `text`,
   `actions`, reason keys). For view.v4 the dock composes one sentence per shown component
   from a template over that component's record fields. The dock does no arithmetic and
   invents no figure: every figure it prints is a record field as the record states it.

   The event page's key is the event's own id (views/<id>.json, BAKE-1's key); every other
   page reads views/<data-context>.json. The page reads one baked file and, only for a
   signed-in person, the agent service's routes. No clock. */
(() => {
  'use strict';
  const mount = document.getElementById('ask');
  if (!mount) return;
  /* The build stamp the page was served under, as grid.js reads it: the plan set is asked for
     under the same build as this script. A page served without a stamp (a fixture harness
     serving the source HTML) reads the unversioned name, which is never cached. */
  const STAMP = (() => {
    const meta = document.getElementById('nowcast-build');
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP;
  /* The agent service's routes (contract section 4), mounted by DOCK-5. */
  const AGENT = '/api/agent/';
  const context = mount.getAttribute('data-context') || '';
  /* The event page's plan set is keyed by the event's own id; every other page by its key. */
  const pathId = (() => {
    const parts = String((typeof location !== 'undefined' && location.pathname) || '')
      .split('/').filter(Boolean);
    if (!parts.length) return '';
    /* A malformed escape in the path (`/event/%E0%A4`) reads as no key; it never stops the dock. */
    try { return decodeURIComponent(parts[parts.length - 1]); } catch (error) { return ''; }
  })();
  const key = context === 'event' && pathId ? pathId : context;
  /* The case this page opens: the event page's own event, or the event the ask page was
     opened for (`/ask?event=<id>`, the event page's link). */
  const caseEvent = (() => {
    if (context === 'event' && pathId) return pathId;
    const search = String((typeof location !== 'undefined' && location.search) || '');
    const found = /[?&]event=([^&]+)/.exec(search);
    if (!found) return '';
    /* A malformed escape (`?event=%E0%A4`) opens no case; it never stops the dock. */
    try { return decodeURIComponent(found[1]); } catch (error) { return ''; }
  })();

  const INSUFFICIENT_TEXT = 'Insufficient: no recorded plan answers this question; '
    + 'the site makes no live model call';
  const STORE_KEY = 'nowcast.dock.v1';
  const DESK = 'desk';
  /* The write actions of the contract's catalogue, section 2: each stops at a confirmation
     card and never runs from the dock. */
  const WRITES = ['mark_stale', 'reissue_outlook', 'save_decision', 'share'];

  const state = {key: key, views: [], selected: null, status: '', present: false, offer: null,
                 user: null, api: 'off', cases: [], queue: [], serverThreads: [],
                 budget: null, budgetRefused: false, turn: null, pending: false, inflight: null,
                 session: null,
                 decided: {}};

  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"]/g,
    (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const short = (value) => (value ? String(value).slice(0, 16) + '…' : '—');
  const list = (value) => (Array.isArray(value) ? value : (value == null ? [] : [value]));

  /* One value as the record states it: booleans in words, objects as their named fields. */
  function valueHtml(value) {
    if (value === null || value === undefined) return '—';
    if (Array.isArray(value)) return value.map(valueHtml).join(' · ');
    if (typeof value === 'boolean') return value ? 'yes' : 'no';
    if (typeof value === 'object') {
      return Object.keys(value).map((name) =>
        '<span class="ak-k">' + esc(name) + '</span> ' + valueHtml(value[name])).join(' · ');
    }
    return esc(value);
  }

  /* ---------- the browser session's threads (anonymous and signed-in alike) ---------- */

  function storage() {
    try {
      const store = (typeof window !== 'undefined' && window.sessionStorage)
        || (typeof sessionStorage !== 'undefined' ? sessionStorage : null);
      return store || null;
    } catch (error) {
      return null;
    }
  }

  function readSession() {
    const empty = {active: DESK, threads: {}};
    empty.threads[DESK] = {ref: DESK, turns: []};
    const store = storage();
    if (!store) return empty;
    try {
      const saved = JSON.parse(store.getItem(STORE_KEY) || 'null');
      if (!saved || typeof saved !== 'object' || !saved.threads
          || typeof saved.threads !== 'object' || Array.isArray(saved.threads)) return empty;
      /* A stored thread of any other shape is reset, never trusted: a thread is a ref and a
         list of turns, each turn an object. */
      Object.keys(saved.threads).forEach((id) => {
        const thread = saved.threads[id];
        if (!thread || typeof thread !== 'object' || !Array.isArray(thread.turns)) {
          saved.threads[id] = {ref: id === DESK ? DESK : String(id).replace(/^event:/, ''),
                               turns: []};
          return;
        }
        if (typeof thread.ref !== 'string') thread.ref = String(id).replace(/^event:/, '');
        thread.turns = thread.turns.filter((turn) => turn && typeof turn === 'object');
      });
      if (!saved.threads[DESK]) saved.threads[DESK] = {ref: DESK, turns: []};
      if (typeof saved.active !== 'string' || !saved.threads[saved.active]) saved.active = DESK;
      return saved;
    } catch (error) {
      return empty;
    }
  }

  function writeSession() {
    const store = storage();
    if (!store) return;
    try { store.setItem(STORE_KEY, JSON.stringify(state.session)); } catch (error) { /* full */ }
  }

  function caseThreadId(eventId) { return 'event:' + eventId; }

  /* A page that opens a case switches the dock to that case's thread; every other page asks
     in the desk thread. */
  function openCaseThread() {
    if (!caseEvent) {
      state.session.active = DESK;
      writeSession();
      return;
    }
    const id = caseThreadId(caseEvent);
    if (!state.session.threads[id]) state.session.threads[id] = {ref: caseEvent, turns: []};
    state.session.active = id;
    writeSession();
  }

  function remember(question, status) {
    const thread = state.session.threads[state.session.active]
      || state.session.threads[DESK];
    thread.turns = thread.turns.concat([{key: state.key, question: question, status: status}])
      .slice(-12);
    writeSession();
  }

  /* ---------- record references and the components ---------- */

  /* One record reference from the receipt, by record kind: its identifier, digest and the
     basis under which the cutoff was (or was not) applied. */
  function recordRef(view, kind) {
    const refs = (view.receipt && view.receipt.records) || [];
    return refs.find((ref) => ref && ref.record === kind) || null;
  }

  function asofLine(view, part) {
    if (!part.record) return '';
    const ref = recordRef(view, part.record);
    if (!ref) return '<p class="ak-asof">Record: ' + esc(part.record) + '.</p>';
    return '<p class="ak-asof">Record ' + esc(part.record) + ' <span class="mono">'
      + esc(ref.record_id) + '</span> · content digest <span class="mono">'
      + esc(short(ref.content_digest)) + '</span> · ' + esc(ref.basis) + '.</p>';
  }

  const TITLES = {
    belief_card: 'Belief',
    event_timeline: 'Event timeline',
    impact_band: 'Impact band',
    outlook_vintages: 'Outlook vintages',
    scorecard: 'Scorecard',
    judgment: 'Judgment',
    decision_form_and_history: 'Decision and history',
    receipt: 'Receipt',
  };
  const titleOf = (component) => TITLES[component]
    || String(component || '').replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

  function beliefBody(fields) {
    let html = '<p class="ak-figure"><span class="mono">' + esc(fields.value) + '</span> '
      + '<span class="ak-unit">' + esc(fields.unit) + '</span></p>'
      + '<p>' + esc(fields.proposition) + '</p>';
    if (fields.accepted) {
      html += '<p class="ak-asof">Accepted at <span class="mono">'
        + esc(fields.accepted.at) + '</span> by ' + esc(fields.accepted.by)
        + ' · source ' + esc(fields.accepted.source) + ' · revision '
        + esc(fields.accepted.revision) + '.</p>';
    }
    if (fields.kv && fields.kv.length) {
      html += '<dl class="ak-kv">' + fields.kv.map((row) =>
        '<dt>' + esc(row[0]) + '</dt><dd>' + esc(row[1]) + '</dd>').join('') + '</dl>';
    }
    return html;
  }

  function timelineBody(fields) {
    const advisory = fields.advisory || {};
    let html = '<p class="ak-asof">Event at <span class="mono">' + esc(fields.event_at)
      + '</span> · advisory <span class="mono">' + esc(advisory.id) + '</span> posted '
      + '<span class="mono">' + esc(advisory.t) + '</span>.</p>';
    html += '<ol class="ak-timeline">' + (fields.timeline || []).map((row) =>
      '<li><span class="mono">' + esc(row.t) + '</span> ' + esc(row.kind)
      + ' <span class="ak-src">' + esc(row.src) + '</span></li>').join('') + '</ol>';
    return html;
  }

  function impactBody(fields) {
    const materiality = fields.materiality || {};
    const direction = fields.direction_check || {};
    const comparator = materiality.comparator === 'at_or_above'
      ? 'at or above' : esc(materiality.comparator);
    return '<p>The materiality line is <span class="mono">'
      + esc(materiality.threshold_php) + '</span> pesos, ' + comparator
      + ', by the record\'s stated rule.</p>'
      + '<p>' + esc(direction.changes_compared) + ' changes compared, '
      + esc(direction.material_changes) + ' material changes, and '
      + esc(direction.nodes_with_a_material_change) + ' nodes with a material change.</p>'
      + '<p class="ak-label">' + esc(fields.label) + '</p>'
      + (fields.unit ? '<p>' + esc(fields.unit.statement) + '</p>' : '');
  }

  function outlookBody(fields) {
    let html = '';
    if (fields.assumption && fields.assumption.text) {
      html += '<p>This view\'s assumption: ' + esc(fields.assumption.text) + '.</p>';
    }
    html += '<ul class="ak-vintages">' + (fields.outlooks || []).map((vintage) =>
      '<li><b>' + esc(vintage.outlook_id) + '</b> · issued <span class="mono">'
      + esc(vintage.issued_at) + '</span> · information cutoff <span class="mono">'
      + esc(vintage.information_cutoff) + '</span> · horizon '
      + esc(vintage.horizon && vintage.horizon.label)
      + (vintage.synthetic === true ? ' · synthetic record' : '')
      + '.</li>').join('') + '</ul>';
    html += '<p>Rests on this assumption: '
      + (fields.rests_on_this_assumption === true ? 'yes' : 'no') + '.</p>';
    return html;
  }

  function scorecardBody(fields) {
    return '<p>Scorecard <span class="mono">' + esc(fields.record_id) + '</span> · '
      + esc(short(fields.content_digest)) + (fields.synthetic === true
        ? ' · synthetic record' : '') + '.</p>'
      + (fields.summary ? '<p>' + valueHtml(fields.summary) + '</p>' : '');
  }

  function judgmentBody(fields) {
    let html = '<p><b>' + esc(fields.label) + '</b> · rule <span class="mono">'
      + esc(fields.rule) + '</span> · ' + esc(fields.by) + '.</p>';
    if (fields.questions && fields.questions.length) {
      html += '<table class="ak-probes"><thead><tr><th scope="col">Question</th>'
        + '<th scope="col">Answer</th></tr></thead><tbody>'
        + fields.questions.map((question) =>
          '<tr><td>' + esc(question.label) + '</td><td>' + esc(question.modal) + '</td></tr>')
          .join('') + '</tbody></table>';
    }
    if (fields.unstable === true) {
      html += '<p class="ak-unstable">The reading is unstable across wordings.</p>';
    }
    if (fields.disagreement) {
      html += '<p>Unresolved disagreement: ' + esc(fields.disagreement.statement) + '</p>';
    }
    html += '<p class="ak-asof">' + esc(fields.receipt) + '.</p>';
    return html;
  }

  function decisionBody(fields) {
    const decision = fields.decision;
    let html = '';
    if (decision) {
      const at = decision.at || decision.t || decision.recorded_at;
      html += '<p>Decision: ' + esc(decision.decision || decision.what || decision.disposition)
        + ' at <span class="mono">' + esc(at) + '</span> by ' + esc(decision.by)
        + '. Reason: ' + esc(decision.reason) + '.</p>';
    } else {
      html += '<p>The records hold no decision at or before the view cutoff.</p>';
    }
    const history = fields.history || [];
    if (history.length) {
      html += '<ol class="ak-history">' + history.map((row) =>
        '<li><span class="mono">' + esc(row.t) + '</span> ' + esc(row.what)
        + ' · ' + esc(row.who) + ' · ' + esc(row.reason) + '</li>').join('') + '</ol>';
    }
    return html;
  }

  function receiptBody(fields) {
    return '<p>The full receipt sits under its own fold below. Receipt digest <span class="mono">'
      + esc(short(fields.receipt_digest)) + '</span>.</p>';
  }

  /* A component outside the composer's first catalogue (the book's tables, the case summary,
     a labelled fake until its contract lands): its fields by name, as the record states them. */
  function genericBody(fields) {
    let html = '<dl class="ak-kv">' + Object.keys(fields).map((name) =>
      '<dt>' + esc(name) + '</dt><dd>' + valueHtml(fields[name]) + '</dd>').join('') + '</dl>';
    if (fields.synthetic === true) html += '<p class="ak-label">Synthetic record.</p>';
    return html;
  }

  const BODIES = {
    belief_card: beliefBody,
    event_timeline: timelineBody,
    impact_band: impactBody,
    outlook_vintages: outlookBody,
    scorecard: scorecardBody,
    judgment: judgmentBody,
    decision_form_and_history: decisionBody,
    receipt: receiptBody,
  };

  function componentHtml(view, part) {
    const body = BODIES[part.component] || genericBody;
    return '<article class="ak-part" data-component="' + esc(part.component) + '">'
      + '<h3>' + esc(titleOf(part.component)) + '</h3>'
      + body(part.fields || {}) + asofLine(view, part) + '</article>';
  }

  /* ---------- view.v4: reasons by key, sentences by template over record fields ---------- */

  /* The composer's reason catalogue (`REASONS` in src/judgment/view.py, DOCK-1), word for word;
     a test pins the copy. The composer already writes the sentence for a part not shown; the
     dock needs the catalogue for an action's reason key and a part that carries only its key.
     A key the dock does not know is shown as its key, never as a sentence the dock made up.
     One key is left out: the composer's `proposes_a_change` sentence is passive ("before
     anything is written"), which the copy rules refuse; the dock shows that key as its key
     until DOCK-1 rewords it. */
  const REASONS = {
    'not_asked': 'The question does not ask for this part.',
    'no_record': 'The record is not among this view inputs.',
    'not_in_cutoff': 'No record of this part exists at or before the view cutoff.',
    'covered_elsewhere': 'Another part of this view already carries what this part would show.',
    'needs_sign_in': 'This needs a signed-in person.',
    'opens_the_page': 'Opens the page that holds the records this answer reads.',
    'runs_the_query': 'Runs the read the question asks for.',
    'looks_for_a_source': 'Looks for a source the records do not hold yet.',
    'drafts_for_signing': 'Prepares a draft in your own copy for you to read and sign.',
    'not_in_catalogue': 'The action is not in the action catalogue.',
    'argument_not_in_manifest': 'An argument names something the manifest does not offer.',
  };

  /* The keys each slot may carry, as the composer splits them (DOCK-1 rework round 1):
     `LEFT_OUT_REASONS` for a part left out, `ACTION_REASONS` for an action proposed, and the
     action catalogue's `REFUSALS` for an action the composer refused. A key in the wrong slot
     is outside that slot's catalogue: the dock shows it as its key. */
  const SLOTS = {
    'left_out': ['not_asked', 'no_record', 'not_in_cutoff', 'covered_elsewhere', 'needs_sign_in'],
    'action': ['opens_the_page', 'runs_the_query', 'looks_for_a_source', 'drafts_for_signing',
               'proposes_a_change'],
    'refusal': ['not_in_catalogue', 'argument_not_in_manifest', 'needs_sign_in'],
  };

  /* The agent service's own refusal keys (src/agent/service.py and budget.py, DOCK-3), which a
     receipt of an action the service ran may carry. DOCK-3 ships keys, not sentences, so these
     sentences are the dock's: each says only what the key names. A test pins the key set
     against the service's source. */
  const SERVICE_REASONS = {
    'write_failed': 'The service could not write the record.',
    'draft_not_open': 'The draft is no longer open for signing.',
    'draft_invalid': 'The draft does not pass its record\'s own check.',
    'no_write_path': 'This site has no write path for this action yet.',
    'not_found': 'The service holds no such record.',
    'unknown_route': 'The route is not a page of this site.',
    'no_drafter': 'The service has no drafter for this kind of draft.',
    'no_record': 'The record is not among this view inputs.',
    'request_refused': 'The composer refused the request.',
    'plan_refused': 'The composer refused the plan.',
    'budget_exhausted': 'The dock reached the day\'s live budget.',
    'budget_unavailable': 'The budget meter did not answer, so no live call ran.',
  };

  function reasonText(item, slot) {
    if (item && typeof item.reason === 'string') return esc(item.reason);
    const reasonKey = item && item.reason_key;
    const allowed = SLOTS[slot] || [];
    if (reasonKey && allowed.indexOf(reasonKey) >= 0 && REASONS[reasonKey]) {
      return esc(REASONS[reasonKey]);
    }
    /* A refusal may also carry one of the service's own keys. */
    if (slot === 'refusal' && reasonKey && SERVICE_REASONS[reasonKey]) {
      return esc(SERVICE_REASONS[reasonKey]);
    }
    return 'Reason key <span class="mono">' + esc(reasonKey) + '</span>.';
  }

  /* The answer's sentences are the composer's own: view.v3's filled text, or view.v4's
     template sentences over the records (DOCK-1). A view that carries no text shows none: the
     dock holds no second sentence set for the same records (DOCK-2 review, finding 7). */
  function textHtml(view) {
    if (typeof view.text === 'string' && view.text) {
      return '<p class="ak-text">' + esc(view.text) + '</p>';
    }
    return '';
  }

  /* ---------- skeleton, receipt and the lines around an answer ---------- */

  function skeletonHtml(view) {
    const shown = (view.components || []).map((part) => esc(titleOf(part.component)));
    const left = view.not_shown || [];
    let html = '<div class="ak-skeleton"><p class="ak-skel-shown">This answer shows: '
      + shown.join(', ') + '.</p>';
    if (left.length) {
      html += '<p class="ak-skel-left">It leaves out: '
        + left.map((part) => esc(titleOf(part.component))).join(', ') + '.</p>'
        + '<details class="ak-not-shown"><summary>Parts not shown, and why</summary><ul>'
        + left.map((part) => '<li><b>' + esc(part.component) + '</b> '
          + reasonText(part, 'left_out') + '</li>').join('') + '</ul></details>';
    }
    return html + '</div>';
  }

  function stabilityHtml(view) {
    const stability = view.receipt && view.receipt.stability;
    if (!stability || typeof stability !== 'object') return '';
    /* A free-text answer planned once: the receipt's own statement ("single plan, stability
       not measured"), and never a stable or unstable word for `stable: null`. */
    if (stability.measured === false || stability.stable === null) {
      return '<p class="ak-stability">Stability: ' + esc(stability.statement
        || stability.sentence || 'not measured') + '.</p>';
    }
    if (stability.stable === true) {
      return '<p class="ak-stability">Stable across ' + esc(stability.forms)
        + ' wordings: the plan keeps the same parts in each.</p>';
    }
    const unstable = (stability.unstable_wordings || []).join(', ');
    return '<p class="ak-stability">Unstable across wordings: ' + esc(unstable)
      + '. The receipt keeps every plan.</p>';
  }

  /* A view the agent service planned for a signed-in person just now is not a replay, so
     its line does not say the site makes no model call. */
  const plannedLive = (view) => Boolean(view && view.fromAgent
    && view.receipt && view.receipt.execution_mode === 'live_inference');

  function labelsHtml(view) {
    const labels = (view.labels || []).filter((label) => label && label.synthetic === true);
    if (!labels.length) return '';
    const named = labels.map((label) => esc(label.record)
      + (label.label ? ' (' + esc(label.label) + ')' : '')).join(', ');
    return '<p class="ak-labels">Synthetic records on this view: ' + named
      + (plannedLive(view) || state.budgetRefused ? '.' : '. The site makes no live model call.')
      + '</p>';
  }

  function receiptLines(receipt) {
    if (!receipt || typeof receipt !== 'object') return '';
    const lines = [];
    if (receipt.question) lines.push('Question: ' + esc(receipt.question));
    if (receipt.wordings) lines.push('Wordings: ' + esc(receipt.wordings.join(' · ')));
    if (receipt.plan && typeof receipt.plan === 'object') {
      const shown = (receipt.plan.parts || receipt.plan.components || [])
        .map((part) => part.component).join(', ');
      const left = (receipt.plan.not_shown || []).map((part) => part.component).join(', ');
      lines.push('Plan: ' + esc(shown) + (left ? ' · left out: ' + esc(left) : ''));
      if (!receipt.actions) {
        const actions = (receipt.plan.actions || []).map((item) => item.action).join(', ');
        if (actions) lines.push('Actions proposed: ' + esc(actions));
      }
    }
    /* The receipt's actions block (view.v4): proposed, refused with its reason, run. */
    if (receipt.actions && typeof receipt.actions === 'object') {
      const block = receipt.actions;
      lines.push('Actions proposed: ' + (list(block.proposed).map((item) =>
        esc(actionName(item.action, item.resolved || item.args, 'now'))).join(' · ') || 'none'));
      lines.push('Actions refused: ' + (list(block.refused).map((item) =>
        esc(item.action) + ' (' + reasonText(item, 'refusal') + ')').join(' · ') || 'none'));
      lines.push('Actions run: ' + (list(block.run).map((item) =>
        esc(actionName(item.action, item.resolved || item.args, 'past'))).join(' · ') || 'none'));
    }
    if (receipt.records) {
      lines.push('Records: ' + receipt.records.map((ref) =>
        esc(ref.record) + ' ' + esc(ref.record_id) + ' (' + esc(short(ref.content_digest))
        + ', ' + esc(ref.basis) + ')').join(' · '));
    }
    if (receipt.cutoff) lines.push('Cutoff: ' + esc(receipt.cutoff));
    if (receipt.model_version) lines.push('Model version: ' + esc(receipt.model_version));
    if (receipt.backend) lines.push('Backend: ' + esc(receipt.backend));
    if (receipt.execution_mode) lines.push('Execution mode: ' + esc(receipt.execution_mode));
    if (receipt.stability) {
      const stability = receipt.stability;
      lines.push('Stability: ' + (stability.measured === false || stability.stable === null
        ? esc(stability.statement || 'not measured')
        : esc(stability.stable === true ? 'stable' : 'unstable') + ' across '
          + esc(stability.forms) + ' wordings'));
    }
    if (receipt.request_digest) {
      lines.push('Request digest: <span class="mono">' + esc(short(receipt.request_digest))
        + '</span>');
    }
    if (receipt.plan_digest) {
      lines.push('Plan digest: <span class="mono">' + esc(short(receipt.plan_digest))
        + '</span>');
    }
    if (receipt.missing) lines.push('Missing record: ' + esc(receipt.missing));
    return lines.map((line) => '<p class="ak-receipt-line">' + line + '</p>').join('');
  }

  function receiptHtml(view) {
    return '<details class="ak-receipt"><summary>Show the receipt</summary>'
      + receiptLines(view.receipt) + '</details>';
  }

  /* The line above the questions. It may never say a plan was replayed unless the answer's
     own receipt records the mode of the backend that planned it: an insufficient answer the
     composer answered before any plan existed carries no mode, so the line says no plan
     stands behind that answer (VIEW-1 review, finding 1). */
  function provenanceWord(view) {
    const mode = view.receipt && view.receipt.execution_mode;
    /* After the meter refused a live call, the dock may not say the site makes none. */
    if (state.budgetRefused) {
      return (mode === 'synthetic_fixture' ? 'Fixture plans, labelled synthetic. ' : '')
        + 'The dock reached the day\'s live budget and answers from recorded plans.';
    }
    if (mode === 'synthetic_fixture') {
      return 'Fixture plans, labelled synthetic. The site makes no live model call.';
    }
    if (mode === 'live_inference') {
      return 'Recorded live plans, replayed. The site makes no live model call.';
    }
    return 'This answer carries no plan. The site makes no live model call.';
  }

  function turnProvenance(view) {
    if (plannedLive(view)) {
      return 'The agent planned this answer for you. Every figure comes from a record.';
    }
    return provenanceWord(view);
  }

  /* ---------- the nearest recorded answer ---------- */

  function normalize(value) {
    return String(value == null ? '' : value).toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ').trim();
  }

  const COMMON = ['the', 'what', 'was', 'were', 'does', 'did', 'this', 'that', 'how', 'why',
                  'when', 'where', 'which', 'who', 'are', 'for', 'and', 'with', 'around'];

  /* The composed recorded answer that shares the most words with the question, or -1 when no
     recorded question shares a word (then the dock says no recorded answer is near). It orders
     questions, never figures. */
  function nearest(question, except) {
    const words = new Set(normalize(question).split(' ')
      .filter((word) => word.length > 2 && COMMON.indexOf(word) < 0));
    let best = null;
    let bestShared = -1;
    state.views.forEach((view, index) => {
      if (index === except || view.status !== 'composed') return;
      const shared = normalize(view.question).split(' ')
        .filter((word) => words.has(word)).length;
      if (shared > bestShared) { best = index; bestShared = shared; }
    });
    return bestShared > 0 ? best : -1;
  }

  function offerHtml(index) {
    if (index === -1) {
      return '<p class="ak-offer">No recorded answer is near this question. The suggested'
        + ' questions are the recorded ones.</p>';
    }
    if (index === null || index === undefined || !state.views[index]) return '';
    return '<p class="ak-offer">The nearest recorded answer: <button type="button"'
      + ' class="ak-offer-q" data-offer="' + index + '">' + esc(state.views[index].question)
      + '</button></p>';
  }

  function answerHtml(view, index) {
    const head = '<h3 class="ak-q-head">' + esc(view.question) + '</h3>';
    if (view.status === 'insufficient') {
      return head + '<p class="ak-insufficient">Insufficient: ' + esc(view.missing)
        + '. The site makes no live model call.</p>'
        + offerHtml(nearest(view.question, index)) + receiptHtml(view);
    }
    return head
      + '<p class="ak-cutoff">Information cutoff <span class="mono">' + esc(view.cutoff)
      + '</span>.</p>'
      + skeletonHtml(view)
      + textHtml(view)
      + (view.components || []).map((part) => componentHtml(view, part)).join('')
      + proposedHtml(view)
      + stabilityHtml(view) + labelsHtml(view) + receiptHtml(view);
  }

  /* ---------- actions and confirmations ---------- */

  const DRAFT_KINDS = {'case': 'case', 'decision_reason': 'decision reason',
                       'reissue': 're-issue'};

  /* What one action does, from its arguments alone: [past, imperative, object]. */
  function actionWords(action, args) {
    const a = args || {};
    const ids = (value) => list(value).join(', ');
    switch (action) {
      case 'open':
        return ['Opened', 'Open', 'page ' + (a.route || '—')
          + (a.record_id ? ' at record ' + a.record_id : '')];
      case 'query_exposure':
        return ['Ran', 'Run', 'exposure for ' + ids(a.account_ids)
          + (list(a.node_ids).length ? ' at nodes ' + ids(a.node_ids) : '')
          + (a.window ? ' over ' + (typeof a.window === 'object'
            ? [a.window.start, a.window.end].filter(Boolean).join(' to ') : a.window) : '')
          + (a.cutoff ? ' under cutoff ' + a.cutoff : '')];
      case 'query_impact':
        return ['Ran', 'Run', 'impact for ' + ids(a.account_ids)
          + (a.outlook_id ? ' on outlook ' + a.outlook_id : '')];
      case 'search_web':
        return ['Searched', 'Search', 'the web for question ' + (a.question_id || '—')];
      case 'pin':
        return ['Pinned', 'Pin', (a.record_id || a.passage_id || '—')
          + (a.thread_id ? ' to thread ' + a.thread_id : '')];
      case 'draft':
        return ['Drafted', 'Draft', 'a ' + (DRAFT_KINDS[a.kind] || a.kind || 'draft')
          + (list(a.record_ids).length ? ' on ' + ids(a.record_ids) : '')];
      case 'mark_stale':
        return ['Marked', 'Mark', 'the vintages that rest on ' + (a.assumption_id || '—')
          + (a.revision ? ' at revision ' + a.revision : '')];
      case 'reissue_outlook':
        return ['Re-issued', 'Re-issue', 'the outlook from draft ' + (a.draft_id || '—')];
      case 'save_decision':
        return ['Saved', 'Save', 'the decision in draft ' + (a.draft_id || '—')
          + ((a.event_id || a.case_id) ? ' on ' + (a.event_id || a.case_id) : '')];
      case 'share':
        return ['Shared', 'Share', a.thread_id ? 'thread ' + a.thread_id
          : 'view ' + (a.view_id || '—')];
      default:
        return null;
    }
  }

  const KNOWN = ['open', 'query_exposure', 'query_impact', 'search_web', 'pin', 'draft',
                 'mark_stale', 'reissue_outlook', 'save_decision', 'share'];
  const UNKNOWN_ACTION = 'Proposed an action the catalogue does not know';

  /* An action's name from its arguments; an action outside the catalogue is never named by
     what it claims to do, only as unknown (its name stays in the receipt line). */
  function actionName(action, args, tense) {
    const words = KNOWN.indexOf(action) >= 0 ? actionWords(action, args) : null;
    if (!words) return UNKNOWN_ACTION;
    return (tense === 'past' ? words[0] : words[1]) + ' ' + words[2];
  }

  /* Where the dock knows a confirmation stands: the person's own click answered by the
     service, else the turn's confirmations, else the queue. Unknown is not confirmed. */
  function confirmationState(id, turn) {
    if (!id) return 'none';
    const decided = state.decided[id];
    if (decided && decided.state && decided.state !== 'sending' && decided.state !== 'failed') {
      return decided.state;
    }
    const known = list(turn && turn.confirmations).concat(state.queue)
      .find((item) => item && item.confirmation_id === id);
    return known && known.state ? known.state : 'unknown';
  }

  /* A link only to a page of this site: one leading slash, then path characters. A second
     slash or a backslash would leave the site (`//host/x`). */
  const SITE_PATH = /^\/(?![\/\\])[a-z0-9/_-]*$/i;

  function actionReceiptLine(run) {
    const parts = ['Receipt: ' + esc(run.action), esc(run.outcome)];
    if (run.started_at) parts.push('started <span class="mono">' + esc(run.started_at) + '</span>');
    if (run.ended_at) parts.push('ended <span class="mono">' + esc(run.ended_at) + '</span>');
    const refs = list(run.record_refs).map((ref) => (typeof ref === 'object'
      ? (ref.record_id || ref.id || valueHtml(ref)) : ref));
    if (refs.length) parts.push('records <span class="mono">' + refs.map(esc).join(', ') + '</span>');
    if (run.confirmation_id) {
      parts.push('confirmation <span class="mono">' + esc(run.confirmation_id) + '</span>');
    }
    return '<p class="ak-action-receipt">' + parts.join(' · ') + '</p>';
  }

  function unconfirmedHtml(run, sentence) {
    return '<article class="ak-action ak-unconfirmed" data-action="' + esc(run.action)
      + '" data-outcome="unconfirmed"><p class="ak-action-name">' + esc(sentence) + '</p>'
      + actionReceiptLine(run) + '</article>';
  }

  /* One action the agent ran, named as it ran, with its receipt line. A write shows as done
     only when the dock knows its confirmation is confirmed; a write the service reports done
     while its confirmation is pending, unknown or absent is named as such (DOCK-2 review,
     finding 1). An action outside the catalogue is named only as unknown. */
  function actionCardHtml(run, turn) {
    if (KNOWN.indexOf(run.action) < 0) {
      return unconfirmedHtml(run, 'The service reports an action outside the catalogue. '
        + 'The dock cannot say what it did.');
    }
    if (WRITES.indexOf(run.action) >= 0) {
      const now = actionName(run.action, run.args, 'now');
      if (!run.confirmation_id) {
        return unconfirmedHtml(run, 'The service reports a write without your confirmation: '
          + now + '. The dock sent no confirmation for it.');
      }
      const standing = confirmationState(run.confirmation_id, turn);
      const decided = state.decided[run.confirmation_id] || {};
      const written = decided.receipt && decided.receipt.outcome ? decided.receipt : run;
      if (standing === 'confirmed' && written.outcome === 'done') {
        return '<article class="ak-action" data-action="' + esc(run.action)
          + '" data-outcome="done"><p class="ak-action-name">'
          + esc(actionName(run.action, run.args, 'past') + '.') + '</p>'
          + actionReceiptLine(Object.assign({}, run, written)) + '</article>';
      }
      /* Confirmed, but the service's own receipt says the write did not happen (DOCK-2
         review R2-1): the catalogue name, the refusal's reason and that receipt's line. */
      if (standing === 'confirmed' && written.outcome === 'refused') {
        return '<article class="ak-action" data-action="' + esc(run.action)
          + '" data-outcome="refused"><p class="ak-action-name">You confirmed '
          + esc(run.action) + '. The service did not write it. '
          + reasonText(written, 'refusal') + '</p>'
          + actionReceiptLine(Object.assign({}, run, written)) + '</article>';
      }
      if (standing === 'declined') {
        return unconfirmedHtml(run, run.outcome === 'done'
          ? 'The service reports this write as done, but you declined it.'
          : now + '. You declined it.');
      }
      if (run.outcome === 'done') {
        return unconfirmedHtml(run, 'The service reports this write as done, but your'
          + ' confirmation is not recorded: ' + now + '.');
      }
      if (standing === 'confirmed') {
        return '<article class="ak-action" data-action="' + esc(run.action)
          + '" data-outcome="confirmed"><p class="ak-action-name">' + esc(now
            + '. You confirmed it.') + '</p>' + actionReceiptLine(run) + '</article>';
      }
      return '<article class="ak-action" data-action="' + esc(run.action) + '" data-outcome="'
        + esc(run.outcome) + '"><p class="ak-action-name">' + esc(now
          + '. It waits for your confirmation.') + '</p>' + actionReceiptLine(run) + '</article>';
    }
    let name;
    if (run.outcome === 'done') {
      name = actionName(run.action, run.args, 'past') + '.';
      if (run.action === 'draft') name += ' It is in your copy.';
    } else if (run.outcome === 'refused') {
      /* A refusal by its catalogue name and reason only; its arguments stay in the receipt. */
      return '<article class="ak-action" data-action="' + esc(run.action)
        + '" data-outcome="refused"><p class="ak-action-name">The service refused '
        + esc(run.action) + '. ' + reasonText(run, 'refusal') + '</p>'
        + actionReceiptLine(run) + '</article>';
    } else {
      name = actionName(run.action, run.args, 'now') + '. It waits for your confirmation.';
    }
    const link = run.action === 'open' && run.outcome === 'done' && run.args
      && SITE_PATH.test(run.args.route || '')
      ? ' <a href="' + esc(run.args.route) + '">Go there</a>' : '';
    return '<article class="ak-action" data-action="' + esc(run.action) + '" data-outcome="'
      + esc(run.outcome) + '"><p class="ak-action-name">' + esc(name) + link + '</p>'
      + (run.reason_key ? '<p class="ak-action-why">' + reasonText(run, 'action') + '</p>' : '')
      + actionReceiptLine(run) + '</article>';
  }

  /* The actions a recorded view.v4 plan proposes: the receipt's `actions.proposed` (DOCK-1),
     named by their resolved arguments, or a view's own `actions`. A replay runs none. */
  function proposedHtml(view) {
    const block = view.receipt && view.receipt.actions;
    const actions = list(view.actions).length ? list(view.actions)
      : list(block && block.proposed);
    if (!actions.length || view.fromAgent) return '';
    /* The composer's refusals, by the proposed action's index: the reason key it recorded. */
    const refusals = {};
    list(block && block.refused).forEach((item) => { refusals[item.index] = item; });
    /* A refused proposal shows its catalogue name and the refusal's reason only; its arguments
       stay in the receipt fold (DOCK-1 review R2-1). */
    return '<div class="ak-proposed"><p class="ak-skel-shown">The plan proposes these actions.'
      + ' A recorded answer runs none of them.</p><ul>' + actions.map((item, index) =>
        '<li>' + (refusals[index]
          ? (KNOWN.indexOf(item.action) >= 0 ? 'The composer refused ' + esc(item.action) + '.'
            : 'The composer refused an action outside the catalogue.') + ' '
            + reasonText(refusals[index], 'refusal')
          : esc(actionName(item.action, item.resolved || item.args, 'now')) + '. '
            + reasonText(item, 'action')
            + (item.confirm === true || WRITES.indexOf(item.action) >= 0
              ? ' It needs your confirmation.' : ''))
        + '</li>').join('') + '</ul></div>';
  }

  function confirmationCardHtml(item) {
    const id = item.confirmation_id;
    const decided = state.decided[id] || null;
    const current = decided ? decided.state : (item.state || 'pending');
    const preview = item.preview || {};
    let html = '<article class="ak-confirm" data-confirmation="' + esc(id) + '" data-state="'
      + esc(current) + '"><h4>Confirm before writing</h4>'
      + '<p class="ak-action-name">' + esc(actionName(item.action, item.args, 'now')) + '.</p>'
      + '<p>Writes ' + esc(preview.what) + ' into ' + esc(preview.where) + ' under receipt '
      + '<span class="mono">' + esc(preview.receipt) + '</span>.</p>'
      + '<p class="ak-asof">Confirmation <span class="mono">' + esc(id)
      + '</span>. Your click is your recorded decision. Nothing runs until you confirm.</p>';
    const buttons = '<button type="button" class="ak-yes" data-confirm="' + esc(id)
      + '">Confirm</button> <button type="button" class="ak-no" data-decline="' + esc(id)
      + '">Decline</button>';
    if (current === 'pending') {
      html += '<p class="ak-confirm-row">' + buttons + '</p>';
    } else if (current === 'sending') {
      html += '<p class="ak-confirm-row">Sending your answer.</p>';
    } else if (current === 'confirmed') {
      /* "The record cites" only when the service's receipt says the write was done; a refused
         receipt says the write did not happen, with its reason (DOCK-2 review R2-1). */
      const receipt = (decided && decided.receipt) || item.receipt || null;
      html += '<p class="ak-confirm-row">You confirmed this at <span class="mono">'
        + esc(decided && decided.decided_at || item.decided_at) + '</span>.';
      if (receipt && receipt.outcome === 'done') {
        html += ' The record cites confirmation <span class="mono">' + esc(id) + '</span>.';
      } else if (receipt && receipt.outcome === 'refused') {
        html += ' The service could not write it. ' + reasonText(receipt, 'refusal');
      } else {
        html += ' The dock holds no receipt of the write yet.';
      }
      html += '</p>';
    } else if (current === 'declined') {
      html += '<p class="ak-confirm-row">You declined this. The dock wrote nothing.</p>';
    } else {
      /* A failed answer keeps both buttons: one click each way, again. */
      html += '<p class="ak-confirm-row">The agent service did not record your answer.'
        + ' Try again. ' + buttons + '</p>';
    }
    return html + '</article>';
  }

  function pendingConfirmations(turn) {
    const own = list(turn && turn.confirmations);
    const ids = new Set(own.map((item) => item.confirmation_id));
    list(turn && turn.confirmations_pending).forEach((id) => {
      if (ids.has(id)) return;
      const queued = state.queue.find((item) => item && item.confirmation_id === id);
      if (queued) { own.push(queued); ids.add(id); }
    });
    return own;
  }

  /* One turn of the agent service: the question as the person asked it, the actions as they
     ran, the cards that wait for a click, then the answer, skeleton first. */
  function turnHtml(turn) {
    const view = turn.view || turn.answer || null;
    const runs = list(turn.actions_run).map((run) => actionCardHtml(run, turn)).join('');
    const confirms = pendingConfirmations(turn).map(confirmationCardHtml).join('');
    return '<div class="ak-turn" data-turn="' + esc(turn.turn_id) + '">'
      + '<p class="ak-asked">You asked: ' + esc(turn.question) + '</p>'
      + (runs ? '<section class="ak-actions" aria-label="What the agent did">'
        + '<h3>What the agent did</h3>' + runs + '</section>' : '')
      + confirms
      + (view ? answerHtml(view, -1) : '')
      + (turn.synthetic === true ? '<p class="ak-labels">Synthetic turn: '
        + esc(turn.label) + '.</p>' : '') + '</div>';
  }

  /* ---------- the dock's header, cases, queue, threads and budget ---------- */

  function whoHtml() {
    if (state.user) {
      return '<p class="ak-who">Signed in as <b>' + esc(state.user.email
        || state.user.displayName || 'your account') + '</b></p>';
    }
    return '<p class="ak-who"><a class="ak-signin" href="/alerts">Sign in to ask live</a>'
      + ' <span class="ak-hint">Anonymous answers replay recorded plans.</span></p>';
  }

  function apiNote() {
    if (!state.user) return '';
    if (state.api === 'present') return '';
    if (state.api === 'checking') return '<p class="ak-hint">Reaching the agent service.</p>';
    return '<p class="ak-hint">The agent service does not answer on this site.'
      + ' The dock answers from recorded plans.</p>';
  }

  function casesHtml() {
    let items = [];
    let note = '';
    if (state.api === 'present') {
      items = state.cases.map((item) => ({id: item.case_id || item.case_ref || item.thread_id,
        event: item.event_id || null, label: item.label, synthetic: item.synthetic === true,
        thread: item.thread_id}));
      note = items.length ? '' : '<p class="ak-hint">No open cases in your copy.</p>';
    } else {
      items = Object.keys(state.session.threads).filter((id) => id !== DESK)
        .map((id) => ({id: state.session.threads[id].ref, event: state.session.threads[id].ref,
          thread: id, session: true}));
      note = items.length ? '<p class="ak-hint">Cases opened in this browser session.</p>'
        : '<p class="ak-hint">No open cases in this browser session. Open an event to start'
          + ' its case thread.</p>';
    }
    /* A case links to its event page only when the record names the event. */
    const rows = items.map((item) => '<li>' + (item.event ? '<a href="/event/'
      + esc(encodeURIComponent(item.event)) + '">' + esc(item.id) + '</a>'
      : '<span class="mono">' + esc(item.id) + '</span>') + (item.synthetic ? ' <span class="ak-hint">synthetic '
        + esc(item.label || 'record') + '</span>' : '') + '</li>').join('');
    return '<section class="ak-cases" aria-label="Open cases"><h3>Open cases</h3>'
      + (rows ? '<ul class="ak-list">' + rows + '</ul>' : '') + note + '</section>';
  }

  function queueItemHtml(item) {
    if (item && item.confirmation_id) return confirmationCardHtml(item);
    if (item && item.draft_id) {
      return '<li>Draft <span class="mono">' + esc(item.draft_id) + '</span> · '
        + esc(DRAFT_KINDS[item.kind] || item.kind) + ' · waits for your signature.</li>';
    }
    if (item && item.outlook_id) {
      return '<li>Outlook <span class="mono">' + esc(item.outlook_id) + '</span> rests on a'
        + ' changed belief <span class="mono">' + esc(item.assumption_id) + '</span>.</li>';
    }
    return '<li>' + valueHtml(item) + '</li>';
  }

  function queueHtml() {
    let body;
    if (state.api === 'present') {
      const items = state.queue;
      const cards = items.filter((item) => item && item.confirmation_id).map(queueItemHtml);
      const rows = items.filter((item) => !(item && item.confirmation_id)).map(queueItemHtml);
      body = cards.join('') + (rows.length ? '<ul class="ak-list">' + rows.join('') + '</ul>' : '')
        + (items.length ? '' : '<p class="ak-hint">Nothing waits for your decision.</p>');
    } else {
      body = '<p class="ak-hint">Nothing waits for your decision in this browser session.'
        + (state.user ? '' : ' Sign in to see your drafts and confirmations.') + '</p>';
    }
    return '<section class="ak-queue" aria-label="Awaiting your decision">'
      + '<h3>Awaiting your decision</h3>' + body + '</section>';
  }

  function threadLabel(id) {
    return id === DESK ? 'Desk thread' : 'Case ' + state.session.threads[id].ref;
  }

  function threadsHtml() {
    const ids = Object.keys(state.session.threads);
    const buttons = ids.map((id) => '<li><button type="button" class="ak-thread" data-thread="'
      + esc(id) + '" aria-pressed="' + (state.session.active === id ? 'true' : 'false') + '">'
      + esc(threadLabel(id)) + '</button></li>').join('');
    const active = state.session.threads[state.session.active] || state.session.threads[DESK];
    const turns = active.turns.map((turn) => '<li>' + esc(turn.question)
      + ' <span class="ak-hint">on the ' + esc(turn.key) + ' page</span></li>').join('');
    const saved = state.api === 'present' && state.serverThreads.length
      ? '<p class="ak-hint">Your copy holds threads ' + state.serverThreads.map((thread) =>
        '<span class="mono">' + esc(thread.thread_id) + '</span>').join(', ') + '.</p>' : '';
    return '<section class="ak-threads" aria-label="Threads"><h3>Threads</h3>'
      + '<ul class="ak-switch">' + buttons + '</ul>'
      + (turns ? '<ol class="ak-turns">' + turns + '</ol>'
        : '<p class="ak-hint">This thread holds no question yet.</p>') + saved + '</section>';
  }

  function budgetHtml() {
    const budget = state.budget;
    if (budget && budget.refused === true) {
      return '<p class="ak-budget">The dock reached the day\'s live budget. It answers from'
        + ' recorded plans until the next day.</p>';
    }
    if (budget && budget.day) {
      return '<p class="ak-budget">Budget for <span class="mono">' + esc(budget.day)
        + '</span>: ' + esc(budget.calls) + ' live calls, about ' + esc(budget.usd_estimate)
        + ' USD by the meter' + (budget.line_usd !== undefined ? ' against a line of '
          + esc(budget.line_usd) + ' USD' : '') + '.</p>';
    }
    return '<p class="ak-budget">Recorded answers make no model call and use no budget.</p>';
  }

  function statusHtml() {
    if (state.status) return '<p class="ak-answer" role="status">' + esc(state.status) + '</p>';
    return '<p class="ak-answer" role="status"></p>';
  }

  function questionsHtml() {
    if (!state.present) {
      return '<p class="ak-empty">No recorded questions for this page yet. <a href="/ask">The'
        + ' desk assistant’s recorded questions are on the ask page.</a></p>';
    }
    return '<ul class="ak-questions" aria-label="Recorded questions">' + state.views.map(
      (view, index) => '<li><button type="button" class="ak-q" data-q="' + index
        + '" aria-pressed="' + (state.selected === index ? 'true' : 'false') + '">'
        + esc(view.question) + '</button></li>').join('') + '</ul>';
  }

  function render() {
    const turnView = state.turn && (state.turn.view || state.turn.answer);
    let status;
    if (turnView) status = turnProvenance(turnView);
    else if (state.present) {
      status = provenanceWord(state.views[state.selected] || state.views[0] || {});
    } else status = 'No recorded plans for this page. The site makes no live model call.';
    let answer = '';
    if (state.pending) answer = '<p class="ak-hint">The agent plans your question.</p>';
    else if (state.turn) answer = turnHtml(state.turn);
    else if (state.selected !== null && state.views[state.selected]) {
      answer = answerHtml(state.views[state.selected], state.selected);
    }
    mount.innerHTML = '<div class="ak-panel ak-dock">'
      + '<header class="ak-dock-head"><h2>Ask Ingrid</h2>' + whoHtml() + '</header>'
      + '<p class="ak-status">' + esc(status) + '</p>'
      + apiNote()
      + '<div class="ak-dock-lists">' + casesHtml() + queueHtml() + threadsHtml() + '</div>'
      + '<h3 class="ak-suggested">Suggested questions</h3>'
      + questionsHtml()
      + '<form class="ak-form" data-ask-form>'
      + '<label for="ak-text">Ask in your own words</label>'
      + '<input id="ak-text" name="q" type="text" autocomplete="off"'
      + ' placeholder="Type a question">'
      + '<button type="submit" class="ak-submit">Ask</button></form>'
      + statusHtml() + offerHtml(state.offer)
      + '<div class="ak-view" aria-live="polite">' + answer + '</div>'
      + budgetHtml()
      + '</div>';
  }

  /* ---------- choosing, asking and confirming ---------- */

  function select(index) {
    if (typeof index !== 'number' || index < 0 || index >= state.views.length) return;
    state.selected = index;
    state.status = '';
    state.offer = null;
    state.turn = null;
    remember(state.views[index].question, state.views[index].status);
    render();
  }

  function matchQuestion(value) {
    const wanted = normalize(value);
    if (!wanted) return null;
    return state.views.find((view) => {
      const wordings = [view.question].concat(
        (view.receipt && view.receipt.wordings) || []);
      return wordings.some((wording) => normalize(wording) === wanted);
    }) || null;
  }

  function askRecorded(value) {
    const view = matchQuestion(value);
    if (view) {
      select(state.views.indexOf(view));
      return;
    }
    state.selected = null;
    state.turn = null;
    /* VIEW-1's sentence says the site makes no live model call; after the meter refused one,
       the dock says what happened instead. */
    state.status = state.budgetRefused
      ? 'The dock reached the day\'s live budget. No recorded plan answers this question.'
      : INSUFFICIENT_TEXT;
    state.offer = state.present ? nearest(value, -1) : null;
    render();
  }

  /* The agent service's transport: one route under /api/agent, the signed-in person's ID token
     in the header as the alerts page sends it. Every answer is read as data, never thrown. */
  async function agentCall(method, path, body) {
    const headers = {'Accept': 'application/json'};
    if (state.user && typeof state.user.getIdToken === 'function') {
      headers.Authorization = 'Bearer ' + await state.user.getIdToken();
    }
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    try {
      const response = await fetch(AGENT + path, {method: method, headers: headers,
        body: body === undefined ? undefined : JSON.stringify(body), credentials: 'same-origin'});
      let data = null;
      try { data = await response.json(); } catch (error) { data = null; }
      return {ok: Boolean(response && response.ok), status: response && response.status, data: data};
    } catch (error) {
      return {ok: false, status: 0, data: null};
    }
  }

  async function askLive(value) {
    state.pending = true;
    state.status = '';
    state.offer = null;
    state.selected = null;
    render();
    /* The service's `thread` is the case reference: `desk` or the event's own id (DOCK-3). */
    const active = state.session.threads[state.session.active] || {ref: DESK};
    const answer = await agentCall('POST', 'ask', {question: value,
      thread: active.ref || DESK, page_key: state.key});
    state.pending = false;
    const data = answer.data || {};
    if (data.budget) state.budget = data.budget;
    state.budgetRefused = Boolean(data.budget && data.budget.refused === true);
    if (answer.ok && data && (data.view || data.answer || data.actions_run)) {
      const view = data.view || data.answer;
      if (view && typeof view === 'object') view.fromAgent = true;
      state.turn = data;
      remember(value, (data.view || data.answer || {}).status || 'turn');
      render();
      return;
    }
    if (!answer.ok && answer.status !== 401 && answer.status !== 403
        && !(data.budget && data.budget.refused)) {
      state.api = 'absent';
    }
    askRecorded(value);
  }

  function ask(value) {
    if (state.user && state.api === 'present') {
      state.inflight = askLive(String(value == null ? '' : value));
      return state.inflight;
    }
    askRecorded(value);
    return Promise.resolve();
  }

  async function decide(id, decision) {
    if (!id || (state.decided[id] && state.decided[id].state !== 'failed')) return;
    state.decided[id] = {state: 'sending'};
    render();
    const answer = await agentCall('POST', 'confirm/' + encodeURIComponent(id),
      {decision: decision});
    const data = answer.data || {};
    if (answer.ok && (data.state === 'confirmed' || data.state === 'declined')) {
      state.decided[id] = {state: data.state, decided_at: data.decided_at,
                           receipt: data.receipt && typeof data.receipt === 'object'
                             ? data.receipt : null};
    } else {
      state.decided[id] = {state: 'failed'};
    }
    render();
  }

  function switchThread(id) {
    if (!state.session.threads[id]) return;
    state.session.active = id;
    writeSession();
    render();
  }

  /* ---------- loading: the plan set, the sign-in state, the agent service ---------- */

  function absent() {
    state.present = false;
    state.views = [];
    render();
  }

  function load() {
    return fetch(DATA + 'views/' + encodeURIComponent(key) + '.json')
      .then((response) => {
        if (!response || !response.ok) { absent(); return; }
        return response.json().then((document) => {
          const views = (document && Array.isArray(document.views)) ? document.views : [];
          if (!views.length) { absent(); return; }
          state.views = views;
          state.present = true;
          restore();
          render();
        });
      }).catch(() => absent());
  }

  /* The thread survives navigation: when this thread's last question belongs to this page's
     plan set, the dock opens on its answer again. */
  function restore() {
    const thread = state.session.threads[state.session.active];
    const last = thread && thread.turns[thread.turns.length - 1];
    if (!last || last.key !== state.key) return;
    const index = state.views.findIndex((view) => view.question === last.question);
    if (index >= 0) state.selected = index;
  }

  async function refreshAgent() {
    if (!state.user) { state.api = 'off'; render(); return; }
    state.api = 'checking';
    render();
    const threads = await agentCall('GET', 'threads');
    if (!threads.ok || !threads.data) {
      state.api = threads.status === 401 || threads.status === 403 ? 'unauthorized' : 'absent';
      render();
      return;
    }
    const queue = await agentCall('GET', 'queue');
    state.api = 'present';
    const listed = list(threads.data.threads || threads.data);
    state.serverThreads = listed;
    state.cases = list(threads.data.cases).length ? list(threads.data.cases)
      : listed.filter((thread) => thread && thread.case_ref && thread.case_ref !== DESK);
    state.queue = queue.ok && queue.data ? list(queue.data.items || queue.data) : [];
    if (threads.data.budget) state.budget = threads.data.budget;
    else if (queue.ok && queue.data && queue.data.budget) state.budget = queue.data.budget;
    render();
  }

  /* The alerts page's Firebase sign-in, read where a page has already started it. The dock
     starts no Firebase app and loads no script; a page without the SDK stays anonymous. */
  function watchSignIn(tries) {
    const firebase = typeof window !== 'undefined' ? window.firebase : null;
    if (!firebase || !firebase.auth) return;
    if (!firebase.apps || !firebase.apps.length) {
      if (tries > 0) setTimeout(() => watchSignIn(tries - 1), 400);
      return;
    }
    let auth;
    try { auth = firebase.app().auth(); } catch (error) { return; }
    auth.onAuthStateChanged((user) => {
      const usable = user && !user.isAnonymous && (user.providerData || []).some((p) =>
        p && (p.providerId === 'google.com' || p.providerId === 'password'));
      state.user = usable ? user : null;
      state.inflight = refreshAgent();
    });
  }

  mount.addEventListener('click', (event) => {
    const target = event.target;
    if (!target || typeof target.getAttribute !== 'function') return;
    const index = target.getAttribute('data-q');
    if (index !== null && index !== '') { select(Number(index)); return; }
    const offer = target.getAttribute('data-offer');
    if (offer !== null && offer !== '') { select(Number(offer)); return; }
    const thread = target.getAttribute('data-thread');
    if (thread) { switchThread(thread); return; }
    const yes = target.getAttribute('data-confirm');
    if (yes) { state.inflight = decide(yes, 'confirm'); return; }
    const no = target.getAttribute('data-decline');
    if (no) { state.inflight = decide(no, 'decline'); }
  });
  mount.addEventListener('submit', (event) => {
    if (event.preventDefault) event.preventDefault();
    const input = document.getElementById('ak-text');
    ask(input ? input.value : '');
  });

  /* ---------- the command bar's hooks (UX-1, UX-2) ----------
     The floating side dock (SHELL-1) is gone. On every page but /ask, command.js moves this
     mount into its sheet's "Cases and threads" panel and renders this module's answers in its
     own thread through the four functions below. /ask keeps the full-page form in its flow. */

  /* The answer this module holds now: an agent turn, else the selected recorded view. */
  function current() {
    if (state.turn) {
      const turnView = state.turn.view || state.turn.answer || {};
      return {kind: 'live', html: turnHtml(state.turn), basis: turnProvenance(turnView)};
    }
    if (state.selected !== null && state.views[state.selected]) {
      const view = state.views[state.selected];
      return {kind: 'recorded', html: answerHtml(view, state.selected), basis: provenanceWord(view)};
    }
    return null;
  }

  /* A question the desk API could not match: the agent service for a signed-in person, else a
     recorded question or one of its wordings. Without either, the nearest recorded question. */
  async function answerFor(value) {
    const text = String(value == null ? '' : value);
    state.turn = null;
    state.selected = null;
    if (state.user && state.api === 'present') {
      state.inflight = askLive(text);
      await state.inflight;
    } else {
      const view = matchQuestion(text);
      if (view) select(state.views.indexOf(view));
    }
    const found = current();
    if (found) return found;
    const near = state.present ? nearest(text, -1) : -1;
    return {kind: 'none', html: '', basis: '',
            nearest: near >= 0 && state.views[near] ? state.views[near].question : ''};
  }

  function pick(index) {
    select(index);
    return current();
  }

  state.session = readSession();
  openCaseThread();
  watchSignIn(15);

  /* The harness and the browser's own console read this module's state through one name. */
  const DeskAsk = {state: state, select: select, ask: ask, render: render, ready: load(),
                   key: key, mount: mount, current: current, answer: answerFor, pick: pick,
                   decide: decide, settled: () => Promise.resolve(state.inflight)};
  if (typeof window !== 'undefined') window.DeskAsk = DeskAsk;
})();
