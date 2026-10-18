/* Event review page. Design file: written by the orchestrator; executor seats do not edit it.
   Renders the view model from window.EventAPI (event-api.js, which executors own):
   load(id) -> { id, title, grid, event_at,
                 advisory{id,t,text,published_basis,first_availability},
                 timeline[{t,t_basis,kind,text,src}], market{t[],lmp[],short[],imp[],marks[{t,kind}]},
                 figures[{k,v,unit,d,up}],
                 assumption{value,unit,proposition,kv[[k,v]]},
                 drivers() -> null | the baked ontology card (O5: modes, drivers, summary, paragraph),
                 judgment|null{label,rule,by,questions[{id,label,answers[4],modal,agree[4],key}],receipt},
                 rules|null{note, governs{series,assumption,dependency}, states[{id,label,why,cutoff,
                   clauses[{clause_label,title,why,text,source,effective,amendments,status,
                            status_reason,excluded}], announcements[{claim_ref,issuer,title,quote,
                   passage_id,source_ref,source_digest,first_availability,status,status_reason,
                   bears_on,locator}], dependents}]} }
   decide({decision,value,reason}) -> { ok, message }      history() -> [{t,what,reason,who}]

   A view with a rules block offers its cutoffs as tabs; the state the visitor selects governs
   every announcement the page shows — the advisory card, the timeline and the rules card alike
   — so a passage that cutoff does not place is named there, never quoted, and its text is
   absent from the whole page. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => { const n = document.createElementNS(svgNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const hhmm = (t) => (t || '').slice(11, 16);
  const day = (t) => new Date(t.slice(0, 10) + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  /* A stated date stays a date: the page never prints a midnight the record does not state. */
  const dateOnly = (t) => /^\d{4}-\d{2}-\d{2}$/.test(String(t || ''));
  const whenText = (t) => (dateOnly(t) ? `${day(t)} (date only)` : `${day(t)} ${hhmm(t)}`);
  const stampText = (t) => (dateOnly(t) ? day(t) : hhmm(t));
  const opText = (s) => esc(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ');
  const KIND = { trip: 'Trip', mld: 'Load dropping', yellow: 'Yellow alert', red: 'Red alert', online: 'Back online', notice: 'Notice', market: 'Market' };
  let V = null;
  /* EXPL-1's wiring runs inside this guard: the DOM shims other suites run this file under
     (tests/fixtures/grid/event/render.mjs, tests/test_cache_headers.py) lack parts of the DOM
     the clicks need, and the page's recorded flow must not depend on them. The real browser
     run in tests/test_grid_page.py reads every interaction; a guard that swallowed a defect
     there would fail that run. */
  function explorable(name, fn) {
    try { fn(); } catch (err) { if (typeof console !== 'undefined' && console.debug) console.debug('explorable ' + name + ' skipped: ' + err); }
  }

  function rail(stage) {
    const order = ['advisory', 'assumption', 'judgment', 'decision'];
    const at = order.indexOf(stage);
    if (!$('rail')) return;  // the event canvas carries the decision form without the rail
    for (const li of $('rail').children) {
      const i = order.indexOf(li.dataset.step);
      li.className = i < at || stage === 'done' ? 'done' : i === at ? 'now' : '';
    }
  }

  /* PP-B2: the page head. The title, then one line naming the grid, the event's own time and the
     trigger notice as a link to its record; the breadcrumb's last item; the page title in the
     site's order (page, section, site); and the way back to the grid at the notice's time. */
  function renderHead() {
    document.title = `${V.title} · Alerts · InGRID`;
    $('ev-title').textContent = V.title;
    if ($('ev-crumb')) $('ev-crumb').textContent = V.title;
    const posted = String(V.advisory.t || '').replace(' ', 'T');
    const notice = `/notices?at=${encodeURIComponent(posted.slice(0, 16))}#adv-${encodeURIComponent(V.advisory.id)}`;
    const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const date = (t) => `${Number(String(t).slice(8, 10))} ${MONTH[Number(String(t).slice(5, 7)) - 1] || ''} ${String(t).slice(0, 4)}`;
    const at = V.event_at ? `${dateOnly(V.event_at) ? date(V.event_at) : date(V.event_at) + ' ' + hhmm(V.event_at)}` : '';
    $('ev-meta').innerHTML = `${esc(V.grid_name)} ${esc(V.grid_kind || 'grid')}` +
      (at ? ` · event at <span class="mono">${esc(at)}</span>` : '') +
      ` · ${esc(V.source_label || 'NGCP')} notice <a class="mono" href="${esc(notice)}" data-entity="notice:${esc(V.advisory.id)}">${esc(V.advisory.id)}</a>` +
      ` posted <span class="mono">${esc(stampText(V.advisory.t))}</span>`;
    if (V.grid) { $('back').href = `/#t=${hhmm(V.advisory.t)}&g=${V.grid}`; $('back').textContent = 'Open on the desk'; }
    else { $('back').href = '/'; $('back').textContent = 'Open the desk'; }
  }

  /* DESK-7: the desk line, under the title and before the four tabs. The AI reader's card says
     in words what the recorded worker did on this case, and the person's card says what the
     person has decided. Every sentence is composed from the baked judgment's own fields and
     nothing else:
       * the run's `by` field, printed exactly as the view carries it (the model name is its
         first segment) — the page never adds a status word of its own, so the word "live"
         appears only when that field carries it;
       * the number of questions and the number of wordings each was put in, and the highest
         flip rate over the questions — the share of wordings whose answer differs from the
         modal one, read from the record's own `agree` booleans, the arithmetic the receipt
         states;
       * the label the rules composed and the rule that fired, verbatim.
     The label is a proposal, not a decision: the card says what the desk's rule would do with
     it. A view with no recorded judgment says so and proposes nothing. */
  const PROPOSAL = {
    challenges: 'opening the assumption for review',
    supports: 'retaining the assumption',
    mixed: 'investigating the assumption',
    insufficient: 'investigating the assumption',
    unrelated: 'no change to this assumption',
  };
  function maxFlipRate(questions) {
    let rate = 0;
    for (const q of questions) {
      const agree = Array.isArray(q.agree) ? q.agree : [];
      if (!agree.length) continue;
      rate = Math.max(rate, agree.filter((a) => a === false).length / agree.length);
    }
    return Math.round(rate * 100) / 100;
  }
  /* DESK-8: the two readings at the return cutoff, in words. The baked view's `cutoffs` list
     carries, for the return pair, the recorded Gemini reading and the scripted case reading at
     the same cutoff. When their labels differ the card says so and calls the difference
     unadjudicated — the evidence ledger's own grade — and never picks a side; when they agree
     it says that; a view with no return pair says nothing. Every word is read from the view. */
  function readingsAtReturn() {
    const none = {text: '', records: [], t: ''};
    const pair = (V.cutoffs || []).find((c) => c && c.pair === 'return');
    if (!pair || !Array.isArray(pair.judgments)) return none;
    const after = pair.judgments.filter((r) => r && r.at === 'after' && r.label);
    const ai = after.find((r) => /^Gemini/i.test(String(r.source || '')));
    const scripted = after.find((r) => /^case reading/i.test(String(r.source || '')));
    if (!ai || !scripted) return none;
    const when = hhmm(pair.t);
    /* The two readings' own receipts travel with the line, folded under their own disclosure
       (its class and summary are its own, so DESK-7's three records folds stay three). */
    const records = [ai, scripted].map((r) => ({
      source: String(r.source || ''), label: String(r.label || ''),
      rule: String(r.rule || ''), receipt: String(r.receipt || ''),
    }));
    if (ai.label === scripted.label) {
      return {records, t: String(pair.t || ''), text: `At the return cutoff (${when}) the AI reader and the scripted case reading both said ${ai.label}.`};
    }
    return {records, t: String(pair.t || ''), text: `At the return cutoff (${when}) the AI reader said ${ai.label}. ` +
      `The scripted case reading said ${scripted.label}. ` +
      'The two readings differ at the return cutoff. The difference is unadjudicated.'};
  }
  /* The decision region's step 1 (Ericka's layout, 18 October) carries the DESK-8 line too, so
     the live page keeps the disagreement, or the agreement, in words with both receipts folded
     under it. The desk line, when the legacy cards are present, draws the same line. */
  function renderReadingsStep() {
    const line = $('ev-ai-readings');
    if (!line) return;
    const readings = readingsAtReturn();
    /* Under a replay clock before the return cutoff, the later reading stays behind the clock,
       as the timeline's later steps do; the line says a later reading exists and nothing more. */
    const clock = window.GNShell && window.GNShell.asOf ? window.GNShell.asOf() : null;
    if (readings.text && readings.t && clock && String(readings.t) > String(clock)) {
      line.textContent = `A second reading exists at a later cutoff (${hhmm(readings.t)}). Move the clock past it to see the two readings.`;
      line.hidden = false;
      $('ev-ai-readings-fold').hidden = true;
      $('ev-ai-readings-list').innerHTML = '';
      return;
    }
    line.textContent = readings.text;
    line.hidden = !readings.text;
    $('ev-ai-readings-fold').hidden = !readings.text;
    $('ev-ai-readings-list').innerHTML = readings.records.map((r) =>
      `<li>${esc(r.source)} · ${esc(r.label)} · ${esc(r.rule)} · ${esc(r.receipt)}</li>`).join('');
  }
  function renderDesk() {
    const j = V.judgment;
    const readings = readingsAtReturn();
    /* ericka-desk: the desk event page has no desk line; the readings nodes may be absent. */
    if ($('dl-readings')) {
      $('dl-readings').textContent = readings.text;
      $('dl-readings-fold').hidden = !readings.text;
      $('dl-readings-list').innerHTML = readings.records.map((r) =>
        `<li>${esc(r.source)} · ${esc(r.label)} · ${esc(r.rule)} · ${esc(r.receipt)}</li>`).join('');
    }
    const readOnly = !!(V.decision && V.decision.mode === 'read_only');
    /* VIEW-1: the recorded plans of the composed view are a later bake input. The view carries
       `ask` true only once they are in the bake; absent (or false) means no link. */
    $('dl-ask').innerHTML = V.ask === true
      ? `<a href="/ask?event=${encodeURIComponent(V.id)}">Ask Ingrid</a>` : '';
    const you = readOnly ? '' : 'You decide below. <a href="#decision">Go to the decision form</a>';
    if (!j) {
      $('dl-by').textContent = '';
      $('dl-run').textContent = 'No judgment is recorded for this event.';
      $('dl-what').textContent = '';
      $('dl-label').textContent = '';
      $('dl-rule').textContent = '';
      if ($('dl-rule-fold')) $('dl-rule-fold').hidden = true;
      $('dl-proposal').textContent = readOnly ? '' : 'The desk has no recorded judgment to propose from.';
      $('dl-you').innerHTML = you;
      return;
    }
    const by = String(j.by || '');
    const model = by.split('·')[0].trim();
    const questions = Array.isArray(j.questions) ? j.questions : [];
    const counts = questions.map((q) => (Array.isArray(q.answers) ? q.answers.length : 0));
    const forms = counts.reduce((n, c) => Math.max(n, c), 0);
    /* "each" only when every question was put in the same number of wordings; otherwise the
       count is the most any question got, so the sentence says "up to N" rather than claiming
       a count the record does not give every question. */
    const formsText = counts.every((c) => c === forms)
      ? `${forms} wordings each` : `up to ${forms} wordings`;
    const rate = maxFlipRate(questions);
    $('dl-by').textContent = by;
    $('dl-run').textContent = model ? `The model is ${model}.` : 'The view names no model for this run.';
    $('dl-what').textContent = `It answered ${questions.length} questions in ${formsText}. ` +
      `The highest flip rate was ${String(rate)}.` +
      (j.unstable === true ? ' The record marks the judgment unstable.' : '');
    $('dl-label').textContent = `It gave the notice the label ${j.label}.`;
    $('dl-rule').textContent = `The rule that fired: ${j.rule}`;
    if ($('dl-rule-fold')) $('dl-rule-fold').hidden = false;
    $('dl-proposal').textContent = `In the desk's rule, ${j.label} proposes ${PROPOSAL[j.label] || 'no change to this assumption'}.`;
    $('dl-you').innerHTML = you;
  }
  /* DESK-7: the person's card beside the AI reader. Until this session records a decision it
     says what is true of the real case: no analyst decision is recorded on it, and what the
     visitor records goes to the visitor's own copy. After a save it says in words what the
     visitor recorded, with the save's own receipt. A view whose decisions are prepared in
     another case says what its own record says. */
  function renderPerson(entry, receipt) {
    const readOnly = !!(V.decision && V.decision.mode === 'read_only');
    if (entry) {
      /* The person's words are a record: they are quoted as they were written, and only a
         missing stop is supplied. */
      const said = String(entry.reason || '').trim();
      const reason = said && !/[.!?]$/.test(said) ? said + '.' : said;
      $('dp-line').textContent = `You recorded: ${entry.what}.` + (reason ? ` Your reason: ${reason}` : '');
      $('dp-receipt').textContent = receipt || '';
      return;
    }
    $('dp-line').textContent = readOnly
      ? (V.decision.note || 'No analyst decision is recorded on this case.')
      : 'No analyst decision is recorded on the real case. What you record goes to your own copy.';
    $('dp-receipt').textContent = '';
  }
  /* The words for a saved decision whose history read did not come back: the visitor's own
     choice, said plainly. The history entry's own sentence is used whenever it is there. */
  function decisionWords(choice, value) {
    if (choice === 'retain') return 'Retained the accepted value';
    if (choice === 'revise') return `Revised the value to ${value} MW`;
    return 'Left the assumption open for investigation';
  }

  /* EXPL-1: the judgment at one notice's cutoff pair. `V.cutoffs` (from the baked view) lists,
     per notice, the recorded readings just before and just after it became known; a notice
     with none says so. The label chip on each timeline row is the "after" reading of the
     recorded model run when there is one, else the scripted case reading, else none. */
  function cutoffFor(src) {
    return (V.cutoffs || []).find((c) => c.advisory === src) || null;
  }
  function labelAfter(c) {
    if (!c || !c.judgments.length) return null;
    const after = c.judgments.filter((j) => j.at === 'after' && j.label);
    return after.length ? after[0].label : null;
  }
  /* CORP-5: the line names each time with the meaning its own record gives it. An advisory
     whose record states a publication date says so and keeps the corpus's first read of the
     page as the separate record it is; one whose time is the instant it was received keeps
     that word. A receipt is never printed as a posting, and a posting is never printed as a
     receipt. */
  function advisoryAsOf(a) {
    const stated = a.published_basis
      ? `published ${whenText(a.t)} · ${a.published_basis}`
      : `as received ${whenText(a.t)} Manila time`;
    const read = a.first_availability;
    if (!read || read.state !== 'known') return `Message ${a.id} ${stated}`;
    return `Message ${a.id} ${stated} · first read by this corpus ${whenText(read.value)} UTC`;
  }
  /* CORP-5: one selected cutoff governs every announcement on the page, not only the rules
     card. The advisory and the timeline are drawn from the very state the visitor selected, so
     a passage that cutoff does not place is named there with its record and its reason while
     its text is absent from the whole page — a later announcement never appears on an earlier
     day, wherever the page would have shown it. A view with no rules block (an outage review,
     not a market action) has no cutoff to select and draws its message as the record holds it. */
  let RU_STATE = 0;      // the rules state the page is showing; 0 is the view's first
  let TL_SEL = null;     // the timeline row whose cutoff detail is open, by index
  function rulesState() { return ((V.rules && V.rules.states) || [])[RU_STATE] || null; }
  function withheldNotice(ref) {
    const state = rulesState();
    if (!state || !ref) return null;
    const notice = (state.announcements || []).find((n) => n.claim_ref === ref);
    if (!notice || (notice.status === 'placed' && notice.quote)) return null;
    return notice;
  }
  function withheldHtml(notice, ref) {
    return `<span class="withheld">${notice.issuer ? esc(notice.issuer) + ' · ' : ''}This cutoff does not place the passage, so its text is not shown here: <b>${esc(notice.status_reason || 'not placed')}</b>. The record <span class="mono">${esc(ref)}</span> is named and no more.</span>`;
  }
  function renderAdvisory() {
    const held = withheldNotice(V.advisory.id);
    $('adv-quote').innerHTML = held ? withheldHtml(held, V.advisory.id) : opText(V.advisory.text);
    $('adv-asof').textContent = advisoryAsOf(V.advisory);
    $('timeline').innerHTML = V.timeline.map((x, i) => {
      const c = cutoffFor(x.src), label = labelAfter(c);
      const chip = x.src && /^[A-Z]/.test(x.src) && x.kind !== 'market'
        ? `<span class="tl-label ${label || 'none'}">${label ? esc(label) : 'no judgment'}</span>` : '';
      const held = withheldNotice(x.src);
      return `<li data-i="${i}"${i === TL_SEL ? ' class="sel"' : ''} tabindex="0" title="${esc(x.src || KIND[x.kind] || x.kind)} · ${esc(x.t)}${x.t_basis ? ' · ' + esc(x.t_basis) : ''}"><span class="tl-t">${esc(stampText(x.t))}</span><span class="tl-dot ${x.kind}"></span>` +
        `<span class="tl-text"><b>${esc(KIND[x.kind] || x.kind)}</b> · ${held ? withheldHtml(held, x.src) : opText(x.text)} <span class="tl-src">${esc(x.src || '')}</span>${chip}</span></li>`;
    }).join('');
    explorable('timeline', () => {
      for (const li of $('timeline').children) {
        const show = () => renderCutoff(Number(li.dataset.i));
        li.addEventListener('click', show);
        li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(); } });
      }
    });
  }
  function renderCutoff(i) {
    const x = V.timeline[i], box = $('cutoff');
    TL_SEL = i;
    for (const li of $('timeline').children) li.classList.toggle('sel', Number(li.dataset.i) === i);
    const c = cutoffFor(x.src);
    if (!c) {
      box.innerHTML = `<h4>${esc(KIND[x.kind] || x.kind)} at ${hhmm(x.t)} · ${esc(x.src || '')}</h4><p class="c-note">No judgment is recorded at this entry; it is ${x.kind === 'market' ? 'a market reading' : 'a notice'} in the timeline, not a cutoff the desk compiled.</p>`;
      box.hidden = false; return;
    }
    const rows = c.judgments.length ? c.judgments.map((j) => `<div class="c-row"><span class="c-at">${j.at === 'before' ? 'before ' + hhmm(c.before) : 'after ' + hhmm(c.after)}</span>` +
      `<span><span class="c-label ${j.label || 'none'}">${j.label ? esc(j.label) : 'no label'}</span> <span class="c-src">· ${esc(j.source)}${j.stable === true ? ' · stable' : j.stable === false ? ' · unstable' : ''}</span><br><span class="c-rule">${esc(j.rule)} · ${esc(j.receipt)}</span></span></div>`).join('')
      : '<p class="c-note">No judgment is recorded at this notice\'s cutoff. The desk compiled the trip and the return pairs only.</p>';
    const pairNote = c.pair ? `<p class="c-note">Cutoff pair "${esc(c.pair)}": compiled one second before and one second after the notice was posted. Only evidence known before each cutoff enters its judgment.</p>` : '';
    box.innerHTML = `<h4>Judgment at the ${esc(KIND[x.kind] || x.kind).toLowerCase()} notice ${esc(c.advisory)}, posted ${hhmm(c.t)}</h4>${rows}${pairNote}`;
    box.hidden = false;
  }

  /* DESK-7: every figure tile names the interval its figure holds at, and the reserve tile,
     the timeline and the chart name the same interval with the same number.
       * A key that states a time (`Price at 14:30`) names its own interval. When the price at
         that interval also equals the highest price from the event onward, the record makes
         the tile a peak, and the key says so: `Price, peak after the trip, 14:30`.
       * A key that states no time takes the interval of the record's own market line in the
         timeline (the row of kind 'market'), and the tile's figure is the five-minute series
         at that interval — so the tile, that row and the chart's own peak label agree.
       * A tile the record cannot place keeps the baked words and names no interval.
     Nothing here is inferred: a key with no time and no series value for it stays as baked. */
  const ownTime = (f) => {
    const hit = String((f && f.k) || '').match(/\b([01]\d|2[0-3]):[0-5]\d\b/);
    return hit ? hit[0] : null;
  };
  const marketLine = () => (V.timeline || []).find((x) => x.kind === 'market') || null;
  const figureNumber = (v) => {
    const n = Number(String(v == null ? '' : v).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) && String(v).replace(/[^0-9.]/g, '') !== '' ? n : null;
  };
  const seriesAt = (series, interval) => {
    if (!Array.isArray(series)) return null;
    const i = V.market.t.findIndex((t) => hhmm(t) === interval);
    return i >= 0 && series[i] != null ? Number(series[i]) : null;
  };
  function pricePeak(f, interval) {
    if (!interval || !/price/i.test(String(f.k || ''))) return false;
    const value = figureNumber(f.v), at = seriesAt(V.market.lmp, interval);
    if (value == null || at == null || at !== value) return false;
    const eventAt = String(V.event_at || '').slice(0, 16);
    const after = V.market.lmp.filter((v, i) => v != null && String(V.market.t[i]).slice(0, 16) >= eventAt);
    return after.length > 0 && value === Math.max(...after);
  }
  function reserveFigure(f) {
    const line = marketLine();
    if (!line || ownTime(f) || !/reserve/i.test(String(f.k || ''))) return null;
    if (!Array.isArray(V.market.short)) return null;
    const i = V.market.t.findIndex((t) => String(t).slice(0, 16) === String(line.t).slice(0, 16));
    if (i < 0 || V.market.short[i] == null) return null;
    return { interval: hhmm(V.market.t[i]), value: V.market.short[i] };
  }
  function renderFigures() {
    $('mk-figs').innerHTML = V.figures.map((f) => {
      const reserve = reserveFigure(f);
      const interval = ownTime(f) || (reserve ? reserve.interval : null);
      const peak = pricePeak(f, interval);
      const key = peak
        ? `${String(f.k).replace(/\s+at\s+[0-2]\d:[0-5]\d.*$/i, '')}, peak after the trip, ${interval}`
        : f.k;
      const value = reserve ? fmt(reserve.value) : f.v;
      const note = reserve ? `${reserve.interval} interval` : '';
      const d = [note, f.d].filter(Boolean).join(' · ');
      return `<div><div class="k">${esc(key)}</div><div class="v">${esc(value)}<span class="unit"> ${esc(f.unit || '')}</span></div>` +
        `<div class="d${f.up ? ' up' : ''}">${esc(d)}</div></div>`;
    }).join('');
  }
  function renderMarket() {
    const m = V.market, svg = $('mk-chart');
    /* A view with no series (a market-wide action, not an outage) hides the card rather
       than drawing an empty chart with a fabricated scale. */
    if (!m.t.length) { $('mk-card').hidden = true; return; }
    const W = Math.max(320, svg.getBoundingClientRect().width), H = 210, L = 40, R = 46, T = 16, B = 20;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.innerHTML = '';
    const n = m.t.length, x = (i) => L + (i / (n - 1)) * (W - L - R);
    const pmax = 32000, smax = Math.max(200, ...m.short.filter((v) => v != null)), imax = Math.max(500, ...m.imp.filter((v) => v != null));
    const yp = (v) => T + (1 - Math.min(v, pmax) / pmax) * (H - T - B);
    const ys = (v) => H - B - (v / smax) * (H - T - B) * 0.45;
    const yi = (v) => T + (1 - v / imax) * (H - T - B);
    el('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, class: 'axis' }, svg);
    for (let i = 0; i < n; i += 12) el('text', { x: x(i), y: H - 5, class: 'tick', 'text-anchor': 'middle' }, svg).textContent = hhmm(m.t[i]);
    [0, 16000, 32000].forEach((v) => { el('text', { x: W - R + 6, y: yp(v) + 3, class: 'tick' }, svg).textContent = v / 1000 + 'k'; });
    let a = '';
    m.short.forEach((v, i) => { a += (a ? 'L' : 'M') + `${x(i).toFixed(1)},${ys(v || 0).toFixed(1)}`; });
    el('path', { d: a + `L${x(n - 1)},${H - B}L${L},${H - B}Z`, class: 'short' }, svg);
    let p = '', q = '';
    m.lmp.forEach((v, i) => { if (v != null) p += (p ? 'L' : 'M') + `${x(i).toFixed(1)},${yp(v).toFixed(1)}`; });
    m.imp.forEach((v, i) => { if (v != null) q += (q ? 'L' : 'M') + `${x(i).toFixed(1)},${yi(v).toFixed(1)}`; });
    el('path', { d: q, class: 'imp' }, svg);
    el('path', { d: p, class: 'price' }, svg);
    const idx = (t) => m.t.findIndex((s) => s >= t.slice(0, 16));
    for (const mk of m.marks) {
      const i = idx(mk.t); if (i < 0) continue;
      el('line', { x1: x(i), x2: x(i), y1: T - 6, y2: H - B, class: 'ev-line' + (mk.kind === 'online' ? ' online' : '') }, svg);
      el('text', { x: x(i) + 4, y: T - 2, class: 'lab', fill: mk.kind === 'online' ? '#3ccf8e' : '#ff5a5a' }, svg).textContent = `${KIND[mk.kind] || mk.kind} ${hhmm(mk.t)}`;
    }
    const last = n - 1;
    const firstP = m.lmp.findIndex((v) => v != null), firstI = m.imp.findIndex((v) => v != null);
    el('text', { x: x(firstP) + 4, y: yp(m.lmp[firstP]) - 8, class: 'lab', fill: '#f2b134' }, svg).textContent = 'Price ₱/MWh';
    el('text', { x: x(firstI) + 4, y: yi(m.imp[firstI]) + 16, class: 'lab', fill: '#8fd3ff' }, svg).textContent = 'Import MW';
    const peak = m.short.reduce((b, v, i) => ((v || 0) > (m.short[b] || 0) ? i : b), 0);
    /* DESK-7: the chart's own label names the interval it reads — the first interval at which
       the reserve shortfall reaches its highest value — so it agrees with the reserve tile and
       with the timeline's market row instead of leaving a bare number beside them. */
    if ((m.short[peak] || 0) > 0) el('text', { x: x(peak), y: ys(m.short[peak]) - 6, class: 'lab', fill: '#ff8a8a', 'text-anchor': 'middle' }, svg).textContent = `Reserve shortfall ${fmt(m.short[peak])} MW at ${hhmm(m.t[peak])}`;
    $('mk-title').textContent = `${V.grid_name} around the event`;
    $('mk-sub').textContent = `${hhmm(m.t[0])}–${hhmm(m.t[last])}, five-minute intervals`;
    renderFigures();
  }

  function renderAssumption() {
    const a = V.assumption;
    $('as-value').textContent = fmt(a.value, 1);
    $('as-big').setAttribute('title', `${a.value} ${a.unit}: the accepted position`);
    $('as-unit').textContent = a.unit;
    $('as-prop').textContent = a.proposition;
    $('as-kv').innerHTML = a.kv.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('');
    /* EXPL-1: the big value opens where the position came from and when it was accepted. */
    explorable('assumption', () => {
      const big = $('as-big');
      big.setAttribute('role', 'button'); big.setAttribute('tabindex', '0'); big.setAttribute('aria-expanded', 'false');
      let more = null;
      const toggle = () => {
        if (more) { more.remove(); more = null; big.setAttribute('aria-expanded', 'false'); return; }
        const acc = a.accepted || {};
        more = document.createElement('div'); more.id = 'as-more'; more.className = 'as-more';
        more.innerHTML = `<b>Where this value comes from.</b> ${esc(acc.source || a.kv.map((kv) => kv.join(': ')).join('; '))}` +
          (acc.at ? `<br><b>Accepted</b> ${esc(acc.at)}${acc.by ? ' by ' + esc(acc.by) : ''}.` : '') +
          `<br>The history card below lists every decision saved on your copy of this case, newest first.`;
        big.parentNode.appendChild(more); big.setAttribute('aria-expanded', 'true');
      };
      big.addEventListener('click', toggle);
      big.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
    });
  }

  /* DESK-1: the register and the price outlook, under the assumption block. The card shows the
     assumption's own words as they were looked up in the committed register, and every issued
     price outlook of the archive with the register rows it rests on, its record digest and the
     marks on its exact bytes — all of it read from the baked `outlook/<id>.json` (served by the
     same `/grid-data/` route as the replay data), every sentence composed from the file's own
     fields and no fact added. Elsewhere on
     this page 'outlook' is the review core's accepted outlook the judge's copy re-reads; this
     card is the PRICE outlook of the archive, and the two names stay apart. */
  const shortHex = (value) => `${String(value).slice(0, 16)}…`;
  /* DESK-2: an input digest in the vintage sentence, shortened the way the brief's own
     example states it (eight hex digits and an ellipsis); the full digest is the record's. */
  const shortDigest = (value) => `${String(value).slice(0, 8)}…`;
  const utcWhen = (t) => `${whenText(t)} UTC`;
  /* Copy rule 1: every sentence carries a time. The summary's facts are the baked file's own
     records — the register file's revision (its basis is the file's own word) and the event's
     recorded time; neither is derived here and no build instant is named anywhere. */
  function priceOutlookFacts(data) {
    const register = data.register || {};
    const facts = [];
    if (register.revision) facts.push(`register revision ${shortHex(register.revision)} (${register.revision_basis})`);
    if (data.event_at) facts.push(`event recorded ${whenText(data.event_at)} Manila time`);
    return facts.length ? ` · ${facts.join(' · ')}` : '';
  }
  /* Copy rule 1 for the outlook sentence: each outlook of the archive is named with its own
     issue instant and information cutoff — the record's own fields, never a page instant. */
  const outlookFacts = (o) => `${o.outlook_id} (issued ${utcWhen(o.issued_at)}, information cutoff ${utcWhen(o.information_cutoff)})`;
  /* DESK-5: a register row's id links to its own row on the register page. An id the register
     does not carry is not a row there, so it stays plain text — no link to a row that does not
     exist. */
  function outlookRow(row) {
    const facts = row.known ? `${row.layer} · ${row.state} · ${row.owner}` : 'not a register row';
    const id = row.known
      ? `<a class="mono" href="/register#${esc(row.assumption_id)}">${esc(row.assumption_id)}</a>`
      : `<span class="mono">${esc(row.assumption_id)}</span>`;
    return `<li>${id} <span class="unit">${esc(facts)}</span></li>`;
  }
  function outlookMark(mark) {
    const kind = mark.synthetic ? 'A labelled demonstration mark names this outlook'
      : 'A change mark names this outlook';
    return `<div class="po-mark">${kind} (${mark.synthetic ? 'synthetic' : 'synthetic false'}): <a class="mono" href="/register#${esc(mark.assumption_id)}">${esc(mark.assumption_id)}</a> at revision <span class="mono">${esc(mark.new_revision)}</span>, marked ${esc(utcWhen(mark.marked_at))} · record <span class="mono">${esc(shortHex(mark.content_digest))}</span></div>`;
  }
  /* ARCH-4: the attribution of a miss, beside the sealed receipt it explains. Each sentence is
     composed from the record's own fields only — the statement in the author's words, the cause
     and its reference (the belief, the signal's two clocks, or the model version), the share
     when the record states one, the author, and the attributed instant with its date in UTC.
     The record's own `synthetic` flag is printed when it is set (copy rule 7). */
  function attributionReference(a) {
    if (a.cause === 'belief') return `belief, assumption ${a.assumption_id}`;
    if (a.cause === 'signal') {
      return `signal, ${a.signal_ref.source} available ${utcWhen(a.signal_ref.available_at)}, `
        + `effective ${utcWhen(a.signal_ref.effective_at)}`;
    }
    return `method, ${a.method_ref}`;
  }
  function attributionSentence(a) {
    const share = a.share == null ? '' : `, share ${a.share} of the miss`;
    return `${a.statement} — ${attributionReference(a)}${share}; attributed by ${a.attributed_by} at ${utcWhen(a.attributed_at)}${a.synthetic ? ' (synthetic)' : ''}.`;
  }
  /* The receipt is named by its own fields, then its attributions follow; a receipt whose
     attributions' shares sum above one carries the archive's verify finding beside it, said in
     the archive's own code. */
  function receiptHtml(r) {
    return `<div class="po-receipt">Receipt for final series ${esc(r.final_series_version)}, scored ${esc(utcWhen(r.scored_at))} · record <span class="mono">${esc(shortHex(r.receipt_digest))}</span></div>`
      + r.attributions.map((a) => `<div class="po-attribution">${esc(attributionSentence(a))}</div>`).join('')
      + (r.share_problem
        ? '<div class="po-share-problem">The shares attributed to this receipt sum above one; the archive\'s verify reports SHARE_OVER_ONE.</div>'
        : '');
  }
  /* DESK-2: one sentence under each later vintage, composed from the baked `changes` and
     nothing else. Every time is the record's own instant, with its date and UTC; every
     digest is a record's own input digest, shortened. The two facts the diff states by
     absence — the model version and the assumption set — are said in words, so the
     sentence never asserts a sameness the two records do not state. */
  function vintageSentence(o) {
    const changes = o.changes || [];
    const parts = [];
    const cutoff = changes.find((c) => c.field === 'information_cutoff');
    if (cutoff) {
      parts.push(cutoff.from === cutoff.to
        ? `information cutoff unchanged at ${utcWhen(cutoff.from)}`
        : `information cutoff ${utcWhen(cutoff.from)} to ${utcWhen(cutoff.to)}`);
    }
    for (const c of changes.filter((x) => x.field === 'input')) {
      if (c.from && c.to) parts.push(`input ${c.name} ${shortDigest(c.from)} to ${shortDigest(c.to)}`);
      else if (c.to) parts.push(`input ${c.name} added ${shortDigest(c.to)}`);
      else parts.push(`input ${c.name} removed ${shortDigest(c.from)}`);
    }
    /* The values file's digest is the record's own field; the file itself is never read. */
    const values = changes.find((x) => x.field === 'values');
    if (values && values.from && values.to) {
      parts.push(`values ${shortDigest(values.from)} to ${shortDigest(values.to)}`);
    }
    const model = changes.find((c) => c.field === 'model_version');
    parts.push(model ? `model ${model.from} to ${model.to}` : 'same model');
    const assumptions = changes.find((c) => c.field === 'assumption_ids') || { added: [], removed: [] };
    const added = assumptions.added || [], removed = assumptions.removed || [];
    if (added.length || removed.length) {
      const said = [];
      if (added.length) said.push(`added ${added.join(', ')}`);
      if (removed.length) said.push(`removed ${removed.join(', ')}`);
      parts.push(`assumptions ${said.join(', ')}`);
    } else parts.push('same assumptions');
    for (const c of changes.filter((x) => x.field === 'horizon')) {
      parts.push(`horizon ${c.edge} ${utcWhen(c.from)} to ${utcWhen(c.to)}`);
    }
    return `${o.outlook_id} (issued ${utcWhen(o.issued_at)}) supersedes ${o.supersedes}: ${parts.join('; ')}.`;
  }
  function outlookHtml(o) {
    const rows = o.assumptions.map(outlookRow).concat(o.unknown_assumption_ids.map((id) =>
      `<li><span class="mono">${esc(id)}</span> <span class="unit">not a register row</span></li>`)).join('');
    /* The current vintage is said in words, not marked with a badge (copy rule 4); a
       single-vintage target carries no flag and reads exactly as DESK-1's card did. */
    const current = o.current === true ? 'current · ' : '';
    const sentence = o.supersedes && Array.isArray(o.changes)
      ? `<div class="po-change">${esc(vintageSentence(o))}</div>` : '';
    return `<li><div class="po-head"><b>${esc(o.outlook_id)}</b> <span class="unit">${current}issued ${esc(utcWhen(o.issued_at))} · cutoff ${esc(utcWhen(o.information_cutoff))}</span></div>` + sentence +
      `<div class="po-line">${esc(o.horizon.label)} horizon ${esc(utcWhen(o.horizon.start))} → ${esc(utcWhen(o.horizon.end))} · record <span class="mono">${esc(shortHex(o.content_digest))}</span></div>` +
      `<div class="po-line">Rests on</div><ul class="po-rows">${rows}</ul>` +
      o.marks.map(outlookMark).join('') + (o.receipts || []).map(receiptHtml).join('') + '</li>';
  }
  /* Copy rule 7: any synthetic record says so in the caption line. The line states the
     provenance the card's own records declare — every outlook carries its own `synthetic`
     flag — and never a standing the page asserts for them: a set whose records all declare
     `false` is the archive's recorded method run on pre-backfill exports, a set whose records
     all declare `true` is synthetic throughout, and a mixture names both counts. */
  const PO_CAPTION_REAL = 'The price-outlook archive is a recorded method run on pre-backfill exports (synthetic false); it makes no skill claim.';
  const PO_CAPTION_SYNTHETIC = 'Every price outlook shown is a synthetic record (synthetic true), not a run on pre-backfill exports; no skill claim is made.';
  function priceOutlookCaption(outlooks) {
    const shown = outlooks.length;
    const synthetic = outlooks.filter((o) => o.synthetic === true).length;
    if (!synthetic) return PO_CAPTION_REAL;
    if (synthetic === shown) return PO_CAPTION_SYNTHETIC;
    return `${synthetic} of ${shown} price outlooks shown are synthetic records (synthetic true); the rest are the archive's recorded method run on pre-backfill exports (synthetic false). No skill claim is made.`;
  }
  /* DESK-4: the portfolio impact record, under the price-outlook card. Every sentence is
     composed from the baked view's own `impact` fields and nothing else: the materiality
     line first (threshold, the record's own comparator and its own rule), then the counts,
     then the record's own label (synthetic portfolio, method demonstration, never a business
     number), then whether this event's unit is one of the record's portfolio nodes. Each
     sentence carries the record's content digest as its as-of; the record states no clock.
     Copy rule 4: a bake with no impact record leaves the card off the page. */
  /* The comparator's words are the record's own field: the record states `at_or_above` or
     `above`, and the sentence says the one it carries — never a page constant. */
  const COMPARATOR_WORDS = { at_or_above: 'at or above', above: 'above' };
  function renderImpact(data) {
    const card = $('impact');
    if (!card) return;
    card.hidden = true;
    if (!data || !data.impact) return;
    const i = data.impact;
    const record = `impact record ${shortHex(i.content_digest)}`;
    const m = i.materiality || {};
    const d = i.direction_check || {};
    const unit = i.unit || {};
    const nodes = Array.isArray(i.nodes) ? i.nodes : [];
    const comparator = COMPARATOR_WORDS[m.comparator] || m.comparator;
    /* DESK-7: one plain sentence opens the card — the materiality rule and the record's own
       standing, in words. Every count, digest and record id stays on the page, folded. A record
       that declares itself synthetic is said as the method demonstration it is; any other
       record is described by its own label, and the page never calls it synthetic. */
    const label = String(i.label || '').trim();
    const standing = i.synthetic === true
      ? 'This is a method demonstration on a synthetic portfolio, never a business number.'
      : (label ? `The record's own label: ${label}` : 'The record declares no synthetic label.');
    $('im-plain').textContent = `A change ${comparator} ${fmt(m.threshold_php)} PHP is material. ` + standing;
    $('im-line').textContent = `A change ${comparator} ${fmt(m.threshold_php)} PHP is material (comparator ${m.comparator}); the rule, in the record's words: ${m.rule} · ${record}.`;
    $('im-counts').textContent = `${fmt(d.material_changes)} of ${fmt(d.changes_compared)} changes compared are material, in ${fmt(d.nodes_with_a_material_change)} of ${fmt(nodes.length)} portfolio nodes · ${record}.`;
    $('im-label').textContent = `Label${i.synthetic === true ? '' : ' (synthetic false)'}: ${i.label} · ${record}.`;
    $('im-unit').textContent = `${unit.statement} · ${record}.`;
    card.hidden = false;
  }
  async function renderPriceOutlook() {
    const card = $('price-outlook');
    /* Copy rule 4: a feature that is not connected is not shown. A bake whose archive is
       absent (available: false), a bake that carries no view yet, or a file the page cannot
       read all leave the card off the page. The flag is set on every path, so a harness can
       read the card's state whether or not the section was drawn. DESK-4: the impact card
       rides the same baked view and is drawn from its own `impact` key whether or not the
       archive is there — the two records are independent. */
    const data = await window.EventAPI.priceOutlook(V.id);
    card.hidden = true;
    renderImpact(data);
    if (!data || data.available !== true || !data.assumption || !Array.isArray(data.outlooks)) return;
    const a = data.assumption;
    const facts = priceOutlookFacts(data);
    /* The lookup is stated only as the file resolves it: one row names its own layer, state and
       owner; no row is the register's unverified reading; several rows are named and no row is
       resolved, so nothing is asserted about what may rest on the proposition. */
    $('po-summary').textContent = a.ambiguous
      ? `${a.text} matches ${a.matches.length} register rows (${a.matches.join(', ')}): the register names more than one row for the proposition, so no single row is resolved${facts}.`
      : (a.registered
        ? `${a.text} is register row ${a.assumption_id}: ${a.layer}, ${a.state}, ${a.owner}${facts}.`
        : `${a.text} is not a register row: no owner, state unverified${facts}.`);
    /* DESK-7: one plain sentence opens the card — the outlook's month, its information cutoff
       and whether it rests on this assumption. The month is read from the record's own window
       (`horizon.start` to `horizon.end`), never from the horizon's label: `month` names the
       kind of horizon, not which month the outlook covers. The vintage named is the one that
       rests when one does, else the current vintage; every register row, record id and input
       digest stays on the page, folded under the disclosure. */
    const named = data.outlooks.filter((o) => o.rests_on_this_assumption)[0] ||
      data.outlooks.filter((o) => o.current === true)[0] ||
      data.outlooks[data.outlooks.length - 1];
    if (!data.outlooks.length) {
      $('po-plain').textContent = `The archive holds no issued price outlook, so no price outlook rests on ${a.text}.`;
    } else {
      const h = named.horizon || {};
      const window = h.start && h.end
        ? ` covers ${utcWhen(h.start)} to ${utcWhen(h.end)}` : ' has no recorded window';
      $('po-plain').textContent =
        `The price outlook${window}. ` +
        `Its information cutoff is ${utcWhen(named.information_cutoff)}. ` +
        (named.rests_on_this_assumption ? `It rests on ${a.text}.` : `It does not rest on ${a.text}.`);
    }
    $('po-list').innerHTML = data.outlooks.map(outlookHtml).join('');
    /* The chain sentence states the walk and nothing more: a dependency only where the file
       claims one, an explicit withheld claim where the register is ambiguous, and — where the
       walk returns none — the archive's own issued outlooks with their issue instants. */
    const issued = data.outlooks.map(outlookFacts);
    const resting = data.outlooks.filter((o) => o.rests_on_this_assumption);
    if (!data.outlooks.length) {
      $('po-chain').textContent = `The archive holds no issued price outlook, so none rests on ${a.text}.`;
    } else if (a.ambiguous) {
      $('po-chain').textContent = `No dependency is claimed: the register names more than one row for ${a.text}, so no single row is resolved. ` +
        `The archive's issued price outlooks are ${issued.join('; ')}.`;
    } else if (resting.length) {
      $('po-chain').textContent = `Issued price outlook ${resting.map(outlookFacts).join('; ')} ` +
        `${resting.length > 1 ? 'rest' : 'rests'} on ${a.text}.`;
    } else {
      $('po-chain').textContent = `No issued price outlook rests on ${a.text}: ` +
        `the archive's issued price outlooks are ${issued.join('; ')}.`;
    }
    $('price-outlook').hidden = false;
    /* DESK-3: the card ends with one link to the archive's own page, drawn only with it. */
    $('po-more').hidden = false;
    /* The caption line holds every disclaimer: the provenance the shown records declare for
       themselves, said once, only when there is an issued price outlook to say it about. */
    if (data.outlooks.length) {
      $('limits').innerHTML += `<li>${esc(priceOutlookCaption(data.outlooks))}</li>`;
    }
  }

  /* O5 (ontology): the likely-drivers card. Everything is read from the baked
     `ontology/<id>.json` (scripts/ontology/bake_panel.py over grid_ontology's recorded and
     checked rows); the page ranks nothing and computes no score. A mode is what the card may
     know at the cutoff: assumed (each run taken as published by its interval), hindsight
     (everything recorded later) or strict (only facts with evidence of when they were known).
     Unconfirmed plant matches are listed and never counted; financial impact is the bake's own
     sentence, never a figure. */
  const DV_FAMILY = { D: 'Demand', S: 'Supply and interconnection', P: 'Price', O: 'Outages', F: 'Fuel cost baseline', Rules: 'Rules and grid constraints' };
  const DV_MODE = { assumed: 'As known at the time', hindsight: 'Hindsight', strict: 'Strict' };
  const DV_MODE_NOTE = {
    assumed: 'Each market run is taken as published by its own interval (assumption, not evidence).',
    hindsight: 'Everything recorded later is shown too, including facts nobody had at the time.',
    strict: 'Only facts with evidence of when they were known.',
  };
  const DV_INDICATOR = { demand_mw: 'demand', import_share: 'import share', hvdc_links_congested: 'HVDC links congested',
    reserve_shortfall_mw: 'reserve shortfall', scheduled_outage_mw: 'capacity scheduled out', linked_derated_mw: 'linked derated capacity',
    price_capped_median: 'capped median price', cap_bound: 'price cap bound', admin_priced: 'administered price',
    price_mitigated: 'price mitigated', price_substituted: 'price substituted', secondary_cap: 'secondary cap',
    congested_elements: 'congested transmission elements at the region\'s stations', congestion_overload_mw: 'congestion overload' };
  /* A percentile in words, naming what it is compared with: the five-minute intervals of the same
     clock hour (Manila) on the 28 days before. F compares with its own monthly history instead. */
  const dvHour = (t) => {
    const m = /T(\d{2}):/.exec(String(t || ''));
    if (!m) return 'the same hour';
    const h = Number(m[1]);
    return `${String(h).padStart(2, '0')}:00 to ${String((h + 1) % 24).padStart(2, '0')}:00`;
  };
  const dvPct = (score) => Math.round(Number(score) * 100);
  const dvWords = (score, t, fam) => {
    const p = dvPct(score);
    const base = fam === 'F' ? 'its own monthly history' : `the five-minute intervals from ${dvHour(t)} on the last 28 days`;
    if (p >= 55) return `higher than ${p}% of ${base}`;
    if (p <= 45) return `lower than usual: only ${p}% of ${base} were lower`;
    return `about usual (${p}%, in the middle of ${base})`;
  };
  /* Recorded code-composed text still carries decimals ("score 0.78", "percentile 78", "import share
     0.105"); the page shows them as percentages in words. A model-phrased paragraph is left as verified. */
  const dvShare = (v) => fmt(Number(v) * 100, 1) + '%';
  const dvPlain = (text) => String(text || '')
    .replace(/top likely-driver score (\d*\.\d+)/g, (m, v) => `top likely driver ${dvPct(v)}% (how unusual it was against the same hour on the last 28 days)`)
    .replace(/(import share (?:was |of )?)(\d*\.\d+)( against a median of | \(28-day median )(\d*\.\d+)/gi, (m, pre, a, mid, b) => `${pre}${dvShare(a)}${mid}${dvShare(b)}`)
    .replace(/percentile (\d+)/g, (m, n) => {
      const p = Number(n);
      if (p >= 55) return `higher than ${p}% of its usual readings`;
      if (p <= 45) return `lower than usual, only ${p}% of its usual readings were lower`;
      return `about usual, ${p}%`;
    });
  /* A checked model explanation keeps its words; only the import share's decimals are shown as percents. */
  const dvShareOnly = (text) => String(text || '').replace(/(import share (?:was |of )?)(\d*\.\d+)( against a median of )(\d*\.\d+)/gi,
    (m, pre, a, mid, b) => `${pre}${dvShare(a)}${mid}${dvShare(b)}`);
  const DV_NOTE = { O: 'Counts planned outages only. A sudden trip is not in the outage schedule; it shows in the operator messages and the relationship trail below.' };
  const dvName = (k) => DV_INDICATOR[k] || String(k || '').replace(/_/g, ' ');
  const dvNum = (v, unit) => {
    if (v == null) return '—';
    const n = Number(v);
    if (unit === 'fraction') return fmt(n * 100, 1) + '%';
    return fmt(n, Math.abs(n) < 10 && n % 1 ? 1 : 0) + (unit && unit !== 'flag' && unit !== 'links' ? ' ' + unit : unit === 'links' ? ' links' : '');
  };
  /* The canvas's bar and state pill for a ranked family: the bar's length is the percent in
     tenths (a class, so no inline style), the pill names the same percent in words. */
  const dvMeter = (score) => {
    const p = dvPct(score);
    if (!Number.isFinite(p)) return '<div class="dv-meter"><span class="dv-bar"><i class="w0"></i></span><span class="gn-pill">No data</span></div>';
    const [cls, word] = p >= 80 ? ['warn', 'Unusual'] : p >= 55 ? ['amber', 'Higher than usual'] : p > 45 ? ['', 'About usual'] : ['info', 'Lower than usual'];
    return `<div class="dv-meter"><span class="dv-bar" aria-hidden="true"><i class="w${Math.max(0, Math.min(10, Math.round(p / 10)))}${cls ? ' ' + cls : ''}"></i></span>` +
      `<span class="gn-pill${cls ? ' ' + cls : ''}">${word}</span></div>`;
  };
  function driversModeHtml(data, mode) {
    const rows = dvList((data.drivers || {})[mode]);
    const info = (data.modes || {})[mode] || {};
    let html = `<p class="dv-note">${esc(DV_MODE_NOTE[mode] || '')}${info.cutoff_utc ? ` Cutoff ${esc(info.cutoff_utc)} UTC.` : ''}</p>`;
    if (!rows.length) {
      html += '<p class="dv-note">No ranking was recorded for this mode.</p>';
    } else {
      const expl = (data.explanations && data.explanations.mode === mode && data.explanations.items) || {};
      const explKind = (data.explanations && data.explanations.kind) || '';
      const explNotes = (data.explanations && data.explanations.notes) || {};
      const ranked = new Map();
      for (const r of rows) if (r.rank != null) { if (!ranked.has(r.family)) ranked.set(r.family, { rank: r.rank, score: r.family_score, items: [] }); ranked.get(r.family).items.push(r); }
      const order = [...ranked.entries()].sort((a, b) => a[1].rank - b[1].rank);
      html += '<ol class="dv-rank">' + order.map(([fam, g]) => `<li><div class="dv-fam"><span class="dv-n">${g.rank}</span><b>${esc(DV_FAMILY[fam] || fam)}</b>` +
        `<span class="dv-score mono">— ${dvPct(g.score)}%</span></div>` +
        `<p class="dv-words">${esc(dvWords(g.score, data.t, fam))}</p>` + dvMeter(g.score) +
        (DV_NOTE[fam] ? `<p class="dv-note">${esc(DV_NOTE[fam])}</p>` : '') +
        (expl[fam] ? `<p class="dv-expl">${esc(dvShareOnly(expl[fam]))} <span class="dv-why">${esc(explKind)}</span>` +
          (explNotes[fam] ? ` ${esc(explNotes[fam])} <span class="dv-why">${esc(data.explanations.notes_kind || '')}</span>` : '') + '</p>' : '') +
        '<ul class="dv-ind">' + g.items.map((r) => `<li>${esc(dvName(r.indicator))}` +
        (r.value_at_t != null ? `: <span class="mono">${esc(dvNum(r.value_at_t, r.unit))}</span>` + (r.baseline_median != null ? ` against a 28-day median of <span class="mono">${esc(dvNum(r.baseline_median, r.unit))}</span>` : '') : r.family === 'F' ? ': fuel context available (monthly series)' : ': no data') +
        (r.indicator_score != null ? ` <span class="dv-pct">${esc(dvWords(r.indicator_score, data.t, r.family))}</span>` : '') + '</li>').join('') + '</ul></li>').join('') + '</ol>';
      const missing = [...new Set(rows.filter((r) => r.status === 'no data' && !ranked.has(r.family)).map((r) => DV_FAMILY[r.family] || r.family))];
      if (missing.length) html += `<p class="dv-note">No data at this cutoff: ${esc(missing.join(', '))}.</p>`;
      const context = rows.filter((r) => r.status === 'context');
      if (context.length) html += `<p class="dv-note">Context, not ranked: ${context.map((r) => `${esc(dvName(r.indicator))} ${esc(dvNum(r.value_at_t, r.unit))}${r.baseline_median != null ? ` (28-day median ${esc(dvNum(r.baseline_median, r.unit))})` : ''}`).join('; ')}.</p>`;
      const present = rows.filter((r) => r.family === 'Rules' && r.status === 'present').map((r) => dvName(r.indicator));
      const absent = rows.filter((r) => r.family === 'Rules' && r.status === 'absent').length;
      if (present.length || absent) html += `<p class="dv-note">Rules flags at the interval (listed, not scored): ${present.length ? esc(present.join(', ')) : 'no rule flag set'}${absent ? `; ${absent} other rule flags not set` : ''}.</p>`;
      const unlinked = rows.find((r) => r.family === 'Rules' && r.status === 'flag count');
      if (unlinked && Number(unlinked.value_at_t) > 0) html += `<p class="dv-note">${esc(fmt(Number(unlinked.value_at_t), 0))} congested elements at stations with no area code (any region): not linked to a region and not counted.</p>`;
    }
    const withheld = dvList(info.withheld);
    const byFamily = new Map();
    for (const w of withheld) byFamily.set(w.family, (byFamily.get(w.family) || 0) + (Number(w.n) || 0));
    const nWithheld = [...byFamily.values()].reduce((a, b) => a + b, 0);
    if (nWithheld) html += `<p class="dv-note">${nWithheld} facts withheld as not yet known at the cutoff (${[...byFamily.entries()].map(([f, n]) => `${esc(DV_FAMILY[f] || f)} ${n}`).join(', ')}).</p>`;
    /* Every fact the mode may use, with when it was known: the evidence time where one exists,
       else the assumed time with its assumption id (A-RT, A-RUN, A-FUEL). Fuel stays a count. */
    const facts = dvList(info.facts);
    if (facts.length || info.fuel_context || dvList(info.fuel_timing).length) {
      /* The label follows the fact's own availability at the cutoff: evidence, an assumption (with its
         id, and any evidence recorded later named as such), or known only after the cutoff. */
      const known = (f) => {
        const id = f.availability_assumption;
        if (f.availability_at_cutoff === 'evidenced' && f.known_by_utc) return `known by ${f.known_by_utc} UTC (evidence)`;
        if (f.availability_at_cutoff === 'assumed') {
          return (f.assumed_known_by_utc ? `assumed known by ${f.assumed_known_by_utc} UTC` : 'assumed known, time not recorded') +
            ` (${id || 'assumption'})` + (f.known_by_utc ? `; evidence recorded ${f.known_by_utc} UTC` : '');
        }
        if (f.availability_at_cutoff === 'after_cutoff') {
          const t = f.known_by_utc || f.assumed_known_by_utc;
          return 'known only after the cutoff' + (t ? ` (${t} UTC)` : '') + (id ? ` (${id})` : '');
        }
        if (f.known_by_utc) return `known by ${f.known_by_utc} UTC (evidence)`;
        if (f.assumed_known_by_utc) return `assumed known by ${f.assumed_known_by_utc} UTC (${id || 'assumption'})`;
        return 'known-by time not recorded';
      };
      html += `<details class="dv-facts"><summary>${facts.length} facts at this cutoff, with when each was known</summary><ul>` +
        facts.map((f) => `<li><span class="dv-fam-tag">${esc(f.family)}</span> ${esc(f.subject_label || '')} · ${esc(dvName(f.predicate))}: ` +
          `<span class="mono">${esc(f.value_num != null ? dvNum(f.value_num, f.unit) : (f.value_text || '—'))}</span> <span class="dv-why">${esc(known(f))}</span></li>`).join('') +
        (dvList(info.fuel_timing).length ? dvList(info.fuel_timing).map((f) => `<li><span class="dv-fam-tag">F</span> fuel row (value not shown) <span class="dv-why">${esc(known(f))}</span></li>`).join('')
          : info.fuel_context ? `<li><span class="dv-fam-tag">F</span> fuel context: ${Number(info.fuel_context)} monthly fuel rows (values not shown)</li>` : '') +
        '</ul></details>';
    }
    const unconfirmed = dvList(info.unconfirmed);
    if (unconfirmed.length) {
      html += `<div class="dv-flag"><b>Unconfirmed matches (not counted)</b><ul>${unconfirmed.map((u) => `<li>${esc(u.plant_text)}: ${esc(u.reason)}</li>`).join('')}</ul></div>`;
    }
    return html;
  }
  /* The card is additive: a bake the renderer cannot read leaves it off, and the rest of the page
     goes on exactly as without the file. */
  async function renderDrivers() {
    try {
      await drawDrivers();
    } catch (err) {
      $('drivers').hidden = true;
      if (typeof console !== 'undefined' && console.debug) console.debug('drivers card skipped: ' + err);
    }
  }
  const dvList = (v) => (Array.isArray(v) ? v : []);
  async function drawDrivers() {
    const card = $('drivers');
    const data = await window.EventAPI.drivers(V.id);
    card.hidden = true;
    if (!data || !data.modes) return;
    const modes = ['assumed', 'hindsight', 'strict'].filter((m) => (data.modes || {})[m] || (data.drivers || {})[m]);
    if (!modes.length) return;
    $('dv-heading').textContent = (data.heading || 'Likely drivers') + (data.region ? ` · ${data.region}` : '') + (data.t ? ` · ${whenText(data.t)}` : '');
    $('dv-tabs').innerHTML = modes.map((m, i) => `<button type="button" class="dv-tab${i === 0 ? ' on' : ''}" data-dv="${m}" aria-pressed="${i === 0 ? 'true' : 'false'}">${esc(DV_MODE[m] || m)}</button>`).join('');
    const draw = (mode) => {
      for (const button of $('dv-tabs').children) {
        const on = button.dataset.dv === mode;
        button.className = 'dv-tab' + (on ? ' on' : '');
        button.setAttribute('aria-pressed', String(on));
      }
      $('dv-state').innerHTML = driversModeHtml(data, mode);
    };
    explorable('drivers tabs', () => {
      for (const button of $('dv-tabs').children) button.addEventListener('click', () => draw(button.dataset.dv));
    });
    draw(modes[0]);
    const s = (data.summary && typeof data.summary === 'object') ? data.summary : {};
    const item = (k, v, why) => `<dt>${esc(k)}</dt><dd>${esc(v || '—')}${why ? `<span class="dv-why">${esc(why)}</span>` : ''}</dd>`;
    $('dv-summary').innerHTML = item('Severity', s.severity, dvPlain(s.severity_reason)) +
      item('Financial impact', s.financial_impact || 'Not available: needs portfolio data') +
      item('Confidence', s.confidence, s.confidence_reason) +
      item('Relationship trail', dvPlain(s.relationship_trail)) +
      `<dt>What to check</dt><dd><ul>${dvList(s.what_to_check).map((w) => `<li>${esc(w)}</li>`).join('')}</ul></dd>`;
    const p = data.paragraph || null;
    const pText = p && p.text && !/Gemini/.test(p.kind || '') ? dvPlain(p.text) : (p && p.text);
    $('dv-para').innerHTML = p && p.text ? `${esc(pText)} <span class="dv-why">${esc(p.kind || '')}${p.model ? ` · ${esc(p.model)}` : ''}</span>` : '';
    $('dv-source').textContent = data.source ? 'Source: ' + data.source + '. No trading advice; financial impact needs portfolio data.' : '';
    card.hidden = false;
  }

  function renderJudgment() {
    const j = V.judgment;
    $('jd-by').textContent = j ? j.by : '';
    $('jd-verdict').hidden = !j; $('jd-table').hidden = !j; $('jd-pending').hidden = !!j;
    if (!j) { $('jd-pending').textContent = 'No judgment is saved for this event yet.'; $('jd-receipt').textContent = ''; return; }
    $('jd-label').textContent = j.label; $('jd-label').className = 'label ' + j.label;
    $('jd-rule').textContent = j.rule;
    $('jd-table').tBodies[0].innerHTML = j.questions.map((q, i) => `<tr data-q="${i}" tabindex="0" title="${esc(q.plain || q.label)} · allowed answers: ${esc((q.allowed || []).join(', ') || 'not recorded')}"${q.key ? ' class="key"' : ''}><td>${esc(q.label)}</td>` +
      `<td><span class="pips" title="${esc(q.answers.join(' · '))}">${q.agree.map((a) => `<span class="pip ${a ? 'agree' : 'differ'}"></span>`).join('')}</span></td>` +
      `<td class="ans">${esc(q.modal)}</td></tr>`).join('');
    $('jd-receipt').textContent = j.receipt;
    /* EXPL-1: a row opens the question in plain words and the four phrasings' answers. */
    explorable('judgment rows', () => {
      const body = $('jd-table').tBodies[0];
      let openTr = null, detail = null;
      for (const tr of [...body.children]) {
        const openRow = () => {
          const q = j.questions[Number(tr.dataset.q)];
          if (detail) { detail.remove(); openTr.classList.remove('open'); }
          if (openTr === tr) { openTr = null; detail = null; return; }
          const row = document.createElement('tr'); row.className = 'detail';
          row.innerHTML = `<td colspan="3">${esc(q.plain || q.label)}<div class="forms-list">${q.answers.map((a, k) => `<span title="phrasing ${k + 1}">${esc(a)}</span>`).join('')}</div>` +
            `<div class="c-note">Four phrasings of the same question; the answer shown is the one most of them gave${q.key ? '. This question decided the label' : ''}.</div></td>`;
          body.insertBefore(row, tr.nextSibling); tr.classList.add('open');
          openTr = tr; detail = row;
        };
        tr.addEventListener('click', openRow);
        tr.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openRow(); } });
      }
    });
  }

  /* CORP-5: the 'rules in force' block. The block is the corpus store's own answers at the
     event's two cutoffs: the clauses that govern the series or the assumption, the amendment
     each clause's own text names, and the announcements that bear on them — every item with
     its passage and its first availability, and a later amendment or announcement named as
     not yet available rather than shown. Nothing here is computed on the page. */
  /* A rule version is in force at a cutoff only when the corpus store places it there, and only
     then does a chip say so. A version the store does not place is reported as not placed with
     the store's own reason; when that reason is an unknown the records do not settle — an
     availability, an effective period or an interval that is not precise about the cutoff — the
     chip says the force is undetermined rather than asserting a negative no record supports. A
     passage's availability is a fact of its own record: it is available at the cutoff or it is
     not, with the reason. Availability is not force, so the two never share a word. */
  const UNDETERMINED = ['availability_unknown', 'availability_imprecise',
                        'effectivity_unknown', 'effectivity_imprecise'];
  function ruleStatusChip(status, reason, kind) {
    if (kind === 'clause') {
      if (status === 'in_force') return '<span class="ru-chip in_force">in force at this cutoff</span>';
      if (status !== 'not_placed') return `<span class="ru-chip ${esc(status)}">${esc(String(status))}</span>`;
      const text = UNDETERMINED.indexOf(String(reason)) >= 0
        ? `not placed; force undetermined · ${reason}`
        : `not placed at this cutoff · ${reason || 'no reason recorded'}`;
      return `<span class="ru-chip not_placed">${esc(text)}</span>`;
    }
    const text = status === 'placed' ? 'available at this cutoff'
      : status === 'not_placed' ? `not available at this cutoff · ${reason || 'no reason recorded'}` : String(status);
    return `<span class="ru-chip ${esc(status)}">${esc(text)}</span>`;
  }
  function availabilityLine(item) {
    const a = item.first_availability || (item.source && item.source.first_availability) || {};
    if (a.state === 'known') return `first available ${esc(a.value)} (${esc(a.basis_kind || '')})`;
    if (a.state === 'unknown') return `first availability unknown${a.upper_bound ? ' · upper bound ' + esc(a.upper_bound) : ''}${a.reason ? ' · ' + esc(a.reason) : ''}`;
    return 'first availability not recorded';
  }
  function locatorLine(locator) {
    if (!locator) return '';
    const page = locator.page ? 'page ' + esc(locator.page) + ', ' : '';
    return `${page}characters ${esc(locator.start)}–${esc(locator.end)}`;
  }
  function ruleClauseHtml(c) {
    const src = c.source || {};
    /* The amendment's availability is the record's own, never a sentence this page supplies:
       an amendment the case cannot show an access date for says exactly that, and one it can
       says when. */
    const amendments = (c.amendments || []).map((a) =>
      `<div class="ru-amend">Amendment that reached it: <b>${esc(a.ref)}</b> dated ${esc(a.dated)} (${esc(a.kind)} ${esc(a.reached)}): ${esc(a.note)} · ${locatorLine(a.locator)} of the same copy · ${availabilityLine(a)}</div>`).join('');
    const excluded = (c.excluded || []).map((e) =>
      `<div class="ru-amend">A later version${e.amendments && e.amendments.length ? ' (' + esc(e.amendments.join(', ')) + ')' : ''}${e.effective && e.effective.value ? ' effective ' + esc(e.effective.value) : ''} is not placed at this cutoff: <b>${esc(e.reason)}</b>${e.text_shown === false ? '; its text is not shown on this day' : ''}.</div>`).join('');
    return `<li data-rule="clause:${esc(c.clause_label)}" tabindex="0" title="clause ${esc(c.clause_label)} · ${esc(src.title || '')} · ${esc(c.status_reason || c.status)}">` +
      `<div class="ru-head"><b>${esc(c.clause_label)}</b> <span>${esc(c.title)}</span> ${ruleStatusChip(c.status, c.status_reason, 'clause')}</div>` +
      `<div class="ru-text">${esc(c.text)}</div>` +
      `<div class="ru-src">${esc(src.title || '')} · ${esc(src.issuer || '')} · copy ${esc(String(src.sha256 || '').slice(0, 16))} · ${locatorLine(c.locator)} · effective ${esc((c.effective || {}).value || 'not stated')} · ${availabilityLine(c)} · ${esc(c.text_basis || '')}</div>` +
      (c.why ? `<div class="ru-why">${esc(c.why)}</div>` : '') + amendments + excluded + '</li>';
  }
  /* A notice the cutoff does not place is named, never quoted: the passage's text is not
     shown on a day it was not available, and the row says which record it is and why. */
  function ruleNoticeHtml(n) {
    return `<li data-rule="${esc(n.claim_ref)}" tabindex="0" title="${esc(n.claim_ref)} · ${esc(n.issuer)} · ${esc(n.status_reason || n.status)}">` +
      `<div class="ru-head"><b>${esc(n.issuer)}</b> <span>${esc(n.title)}</span> ${ruleStatusChip(n.status, n.status_reason, 'passage')}</div>` +
      (n.status === 'placed' && n.quote
        ? `<div class="ru-text">${esc(n.quote)}</div>`
        : `<div class="ru-text ru-withheld">This cutoff does not place the passage, so its text is not shown here: <b>${esc(n.status_reason || 'not placed')}</b>. The row names the record and no more.</div>`) +
      `<div class="ru-src">${esc(n.claim_ref)} · passage ${esc(n.passage_id)} · record ${esc(n.source_ref)} · copy ${esc(String(n.source_digest || '').slice(0, 16))}${n.published ? ' · published ' + esc(n.published) + ' (' + esc(n.published_basis || 'stated') + ')' : ''} · ${availabilityLine(n)}` +
      (n.bears_on && n.bears_on.length ? ` · bears on clause${n.bears_on.length > 1 ? 's' : ''} ${esc(n.bears_on.join(', '))}` : '') + '</div></li>';
  }
  function renderRules() {
    const rules = V.rules;
    const card = $('rules');
    if (!rules) { card.hidden = true; return; }
    card.hidden = false;
    $('ru-by').textContent = 'corpus store';
    $('ru-note').textContent = rules.note || '';
    /* What the clauses govern, named before the cutoff states: the series and the assumption
       the case is about, each with the record it comes from. */
    const governs = rules.governs || {};
    const series = governs.series || {}, assumption = governs.assumption || {};
    $('ru-governs').innerHTML = `<b>Governs</b> ${esc(series.series_ref || '')} — ${esc(series.definition || '')} (${esc(series.source || '')})` +
      (assumption.proposition ? ` · and the assumption “${esc(assumption.proposition)}” (${esc(assumption.state || '')}; nobody has accepted it).` : '.');
    const states = rules.states || [];
    $('ru-tabs').innerHTML = states.map((s, i) =>
      `<button type="button" class="ru-tab${i === 0 ? ' on' : ''}" data-ru="${i}" aria-pressed="${i === 0 ? 'true' : 'false'}">${esc(s.label)} · ${esc(s.cutoff.value)}</button>`).join('');
    const draw = (index) => {
      const s = states[index];
      if (!s) return;
      const moved = index !== RU_STATE;
      RU_STATE = index;
      for (const button of $('ru-tabs').children) {
        const on = Number(button.dataset.ru) === index;
        button.className = 'ru-tab' + (on ? ' on' : '');
        button.setAttribute('aria-pressed', String(on));
      }
      const dep = s.dependents || {};
      $('ru-state').innerHTML =
        `<p class="ru-cut">Cutoff ${esc(s.cutoff.label)} — ${esc(s.why || '')}</p>` +
        `<h4>Clauses that govern</h4><ul class="ru-list">${(s.clauses || []).map(ruleClauseHtml).join('')}</ul>` +
        `<h4>Announcements that bear on them</h4><ul class="ru-list">${(s.announcements || []).map(ruleNoticeHtml).join('')}</ul>` +
        `<h4>What depends on the market at this cutoff</h4><p class="ru-dep">${dep.rows && dep.rows.length
          ? dep.rows.map((r) => `${esc(r.ref)} (${esc(r.ref_type)}) at depth ${r.depth}`).join(' · ')
          : esc(dep.note || 'No accepted record depends on the market at this cutoff.')}</p>`;
      /* The cutoff the visitor picked governs the advisory card and the timeline too, so the
         repaint is part of switching the state and not a courtesy to the rules card. */
      if (moved && $('adv-quote') && $('timeline')) renderAdvisory();
      explorable('rules rows', () => {
        for (const li of $('ru-state').querySelectorAll('[data-rule]')) {
          const toggle = () => {
            const open = li.classList.contains('open');
            for (const other of $('ru-state').querySelectorAll('[data-rule].open')) {
              other.classList.remove('open');
              const detail = other.querySelector('.ru-detail');
              if (detail) detail.remove();
            }
            if (open) return;
            li.classList.add('open');
            const row = document.createElement('div');
            row.className = 'ru-detail';
            row.textContent = 'Every line above names its record: the copy, the clause or claim, the passage and the availability evidence. The store decides what is placed at a cutoff; the page repeats the answer.';
            li.appendChild(row);
          };
          li.addEventListener('click', toggle);
          li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
        }
      });
    };
    explorable('rules tabs', () => {
      for (const button of $('ru-tabs').children) {
        button.addEventListener('click', () => draw(Number(button.dataset.ru)));
      }
    });
    draw(0);
  }

  function renderHistory(list, freshIndex) {
    $('history').hidden = !list.length;
    $('hist-list').innerHTML = list.map((h, i) => `<li${i === freshIndex ? ' class="new"' : ''} tabindex="0" title="${esc(h.who)} · ${esc(h.t)}"><div class="h-head"><span>${esc(h.who)}</span><span>${esc(h.t)}</span></div>` +
      `<div class="h-what">${esc(h.what)}</div><div>${esc(h.reason)}</div></li>`).join('');
    /* EXPL-1: an entry opens its decision record, read from the judge's own copy: the task the
       decision was compiled against and the judgment reference the record carries. A record
       that names no judgment artifact says so; nothing is inferred from what the page shows. */
    explorable('history', () => {
      list.forEach((h, i) => {
        const li = $('hist-list').children[i];
        if (!li) return;
        let more = null;
        const toggle = async () => {
          if (more) { more.remove(); more = null; li.classList.remove('open'); return; }
          more = document.createElement('div'); more.className = 'h-more';
          more.textContent = 'Reading the decision record…';
          li.appendChild(more); li.classList.add('open');
          const d = h.decision_ref ? await window.EventAPI.decision(h.decision_ref) : { ok: false, message: 'this entry names no decision record' };
          if (!more) return;
          more.textContent = d.ok
            ? `Decision record ${d.record_id}: ${d.disposition || 'decision'} at ${d.reviewed_at}, compiled against task ${d.task || 'unknown'}. ` +
              (d.judgment ? `It names judgment record ${d.judgment}.` : 'It names no judgment record: the judgment this page shows is a recording in the page, not a record in your copy.') +
              ' Saved on your own copy of the case; nobody else\'s copy changes.'
            : `The decision record could not be read (${d.message}). The history entry carries the decision, the reason and the time; nothing more is claimed.`;
        };
        li.addEventListener('click', toggle);
        li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
      });
    });
  }
  /* EXPL-1: the caption's limits line expands to the list the view carries. */
  function wireLimits() {
    explorable('limits', () => {
      const btn = $('limits-btn'), list = $('limits');
      if (!btn || !list) return;
      list.innerHTML = (V.limits || []).map((x) => `<li>${esc(x)}</li>`).join('');
      btn.setAttribute('aria-expanded', 'false');
      btn.addEventListener('click', () => { list.hidden = !list.hidden; btn.setAttribute('aria-expanded', String(!list.hidden)); });
    });
  }

  /* DESK-7: a refusal keeps the route's own code and sentence, then says plainly that the
     decision was not recorded and that it can be tried again — but only where the route's
     sentence does not already say it. The local preview records nothing here and offers
     nowhere to retry, so it keeps its own sentence alone. */
  function refusalText(message) {
    const text = String(message == null ? '' : message).trim();
    if (!text) return 'The decision was not recorded. Try again.';
    const said = /[.!?]$/.test(text) ? text : text + '.';
    if (/hosted demo/i.test(text)) return said;
    const notRecorded = /not (?:recorded|sent|accepted|saved)/i.test(text);
    const retry = /try again|reload|decide again/i.test(text);
    return said + (notRecorded ? '' : ' The decision was not recorded.') + (retry ? '' : ' Try again.');
  }

  function wireDecision() {
    /* CORP-5: a case whose decisions are prepared in the case pack, not filed through the
       judge's routes, says so and keeps the form off — so a click can never file a decision
       against another case. */
    if (V.decision && V.decision.mode === 'read_only') {
      $('dc-form').hidden = true;
      const note = $('dc-note');
      note.hidden = false;
      note.textContent = V.decision.note || 'Decisions for this event are not recorded here.';
      return;
    }
    const form = $('dc-form');
    /* DESK-7: the wait is said in words with a seconds count. A cold start can hold the first
       request for several seconds, and a bare "Saving…" looked like a dead form to a stranger —
       so the status line names the wait and counts the seconds while it lasts. The wording
       names the wait and promises no figure: the record measures the cold start at 3.6 s
       (docs/work/product-gap-2026-10-17/strategy.md, commit 74a78489). */
    const SAVE_WAIT = 'Saving… the service may need time to wake';
    const sync = () => {
      const d = form.querySelector('input[name="d"]:checked');
      $('dc-value-wrap').hidden = !d || d.value !== 'revise';
      const valueOk = !d || d.value !== 'revise' || /^\d+(\.\d+)?$/.test($('dc-value').value.trim());
      $('dc-submit').disabled = !d || !$('dc-reason').value.trim() || !valueOk;
    };
    form.addEventListener('input', sync); form.addEventListener('change', sync);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const d = form.querySelector('input[name="d"]:checked');
      const value = $('dc-value').value.trim();
      const reason = $('dc-reason').value.trim();
      $('dc-submit').disabled = true;
      const started = Date.now();
      const ticking = () => {
        const seconds = Math.max(0, Math.round((Date.now() - started) / 1000));
        $('dc-status').textContent = `${SAVE_WAIT} · ${seconds} s`;
      };
      ticking();
      const timer = typeof setInterval === 'function' ? setInterval(ticking, 1000) : null;
      let res;
      try {
        res = await window.EventAPI.decide({ decision: d.value, value: value || null, reason });
      } finally {
        if (timer !== null && typeof clearInterval === 'function') clearInterval(timer);
      }
      res = res || { ok: false, message: 'The demo did not answer' };
      /* DESK-7: a refusal names the route's code and sentence, then says plainly that the
         decision was not recorded and that it can be tried again — once, and only where the
         route's own sentence does not already say it. The saved receipt is shown exactly as
         the adapter wrote it. */
      $('dc-status').textContent = res.ok ? res.message : refusalText(res.message);
      if (res.ok) {
        rail('done');
        const history = await window.EventAPI.history();
        renderHistory(history, 0);
        const first = history[0];
        renderPerson(first && first.who !== 'History unavailable'
          ? first : { what: decisionWords(d.value, value), reason }, res.message);
        /* DESK-7: after a save the history card is the visitor's own copy of the case. */
        $('hist-title').textContent = 'Your copy';
        /* PP-B2: the page head follows the saved decision (event-desk.js listens). */
        if (typeof document.dispatchEvent === 'function' && typeof CustomEvent === 'function') {
          const words = first && first.who !== 'History unavailable' ? first.what : decisionWords(d.value, value);
          document.dispatchEvent(new CustomEvent('gn:decided', { detail: { what: words } }));
        }
        form.reset(); sync();
      } else sync();
    });
  }

  async function main() {
    const id = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
    try {
      V = await window.EventAPI.load(id);
    } catch (err) {
      document.querySelector('.ev').innerHTML = `<div class="gn-empty" role="status"><p class="gn-empty-title">This event could not be loaded</p>` +
        `<p class="gn-empty-body">The build holds no record for this address (${esc(err.message)}). Pick an event from the alerts.</p>` +
        '<div class="gn-empty-actions"><a class="gn-btn" href="/alerts">Open alerts</a><a class="gn-btn gn-btn--ghost" href="/">Open the desk</a></div></div>';
      return;
    }
    /* The event canvas (ericka-desk) no longer carries the advisory and timeline, the market
       chart, the desk line, the rules card, the impact and price-outlook cards or the review
       column (assumption, judgment, decision form, history): a renderer runs only when its
       card is on the page, so a page without one draws the rest and raises nothing. */
    const has = (id) => !!$(id);
    renderHead();
    if (has('adv-quote') && has('timeline')) renderAdvisory();
    if (has('as-value')) renderAssumption();
    if (has('jd-table')) renderJudgment();
    if (has('desk-ai')) renderDesk();
    if (has('ev-ai-readings')) {
      renderReadingsStep();
      if (window.GNShell && window.GNShell.onAsOf) window.GNShell.onAsOf(renderReadingsStep);
    }
    if (has('desk-person')) renderPerson();
    if (has('mk-chart')) renderMarket();
    if (has('rules')) renderRules();
    wireLimits();
    if (has('price-outlook')) await renderPriceOutlook();
    if (has('drivers')) await renderDrivers();
    if (has('rail')) rail(V.judgment ? 'decision' : 'judgment');
    if (has('dc-form')) wireDecision();
    if (has('history')) renderHistory(await window.EventAPI.history());
    if (has('mk-chart')) window.addEventListener('resize', () => renderMarket());
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
})();
