/* InGRID "How we got this" (data-flow modal, part 1: the event page).

   A "?" on a card header opens one shared dialog that shows how that card was produced, as a
   flow of stages from the recorded sources to this page. Each stage names the tools it used
   (BigQuery, Gemini on Vertex AI, code checks, the hosting) and says what it did in plain words;
   its figures are read at runtime from the records this page already loaded (the event view and
   the ontology record, with its optional `provenance` block). A figure they do not carry says
   "Not in the record"; nothing is estimated.

   Only references a reader can open are named: pages of this site and public outside sources.
   Private file names, table names, build stamps and internal ids never reach the text (every
   string passes `clean`). No forecast, no unit technology or fuel type (fuel is only "fuel
   context available"), no peso figure ("Needs your portfolio").

   `GridFlow.stages(card, V, onto, page)` is pure and runs on node for the tests;
   `GridFlow.mount(ctx)` wires the "?" buttons (`button[data-flow]`) and the dialog. */
(function () {
  'use strict';

  const NOT = 'Not in the record';
  const has = (v) => v !== undefined && v !== null && v !== '';
  const uniq = (a) => Array.from(new Set(a.filter(has)));
  const num = (v) => (has(v) && Number.isFinite(Number(v)) ? Number(v) : null);
  const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;

  /* Private names never shown: SQL tables and views, script, query and data file names, long
     hex ids, build stamps. A safety net over every string the stages produce. */
  const PRIVATE = /\b(?:grid_[a-z]+(?:\.[a-z_]+)?|[\w./-]+\.(?:sh|py|sql|json|mjs|js))\b|\b[0-9a-f]{12,}\b|(?:request|probe|digest)[\s:][^·]*/gi;
  const clean = (s) => (s === null || s === undefined ? s : String(s).replace(PRIVATE, '').replace(/\(\s*\)/g, '')
    .replace(/\s+·\s+(?=·|$)/g, '').replace(/\s{2,}/g, ' ').replace(/[\s·,;]+$/, '').trim());

  const FAMILY = { D: 'Demand', S: 'Supply and interconnection', P: 'Price', O: 'Outages',
    F: 'Fuel cost baseline', Rules: 'Rules and grid constraints' };
  const VIEW = { strict: 'What we can prove we knew', assumed: 'What we likely knew', hindsight: 'Everything we know now' };
  /* What each recorded table holds, in plain words (the table name itself stays private). */
  const KIND = {
    intervals: 'five-minute market intervals', labels: 'price bands and pricing flags', labels_reserve: 'reserve readings',
    interval_pricing: 'pricing per interval', outage_events: 'outage schedule records',
    outage_mentions: 'unit names in operator notices', ext_rtd_hvdc_schedules: 'HVDC link schedules',
    advisories_parsed: 'operator notices read by code', grid_congestions: 'congestion records',
  };
  const ASSUME = {
    'A-RT': ['real-time value taken as known at the end of its interval', 'real-time values taken as known at the end of their interval'],
    'A-RUN': ['schedule record taken as known from the first snapshot that carries it', 'schedule records taken as known from the first snapshot that carries them'],
  };
  const T = {
    bq: 'BigQuery', gemini: 'Gemini on Vertex AI', py: 'Python code', checks: 'Code checks',
    host: 'Cloud Run and Firebase Hosting', browser: 'Your browser',
  };
  const tool = (key, role, ai) => ({ name: T[key], role, kind: ai ? 'ai' : 'det' });
  const ref = (label, href) => ({ label, href: href || null });
  const PAPER_METHODS = ref('Working paper: methods and models', '/paper#ch0-4-methods-and-models');

  const CARDS = {
    glance: { name: 'What happened', stages: ['S1', 'S2', 'S4', 'S7', 'S9'],
      what: () => 'The key figures, the price chart and the steps, read from the event record and the ontology record.' },
    ai: { name: 'AI explanation', stages: ['S4', 'S5', 'S6', 'S8', 'S9'],
      what: (isAI) => (isAI ? 'A paragraph written by code from the record, reworded by Gemini, then checked by code.'
        : 'A paragraph written by code from the record. No AI rewording is in this record.') },
    ranked: { name: 'What stood out, ranked', stages: ['S1', 'S2', 'S3', 'S4', 'S5', 'S7', 'S9'],
      what: () => 'The ontology ranking: each family scored by how unusual it was against the same hour on the days before.' },
    rules: { name: 'Price rules', stages: ['S1', 'S2', 'S3', 'S7', 'S9'],
      what: () => 'Pricing flags observed on the interval. Listed as set or not set, never scored.' },
  };
  const ORDER = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'];

  /* A UTC record time as Manila time, "2026-09-21 13:45". */
  function manila(s) {
    if (!has(s)) return null;
    let x = String(s).trim().replace(' ', 'T');
    if (!/(Z|[+-]\d\d:?\d\d)$/.test(x)) x += 'Z';
    const d = new Date(x);
    if (Number.isNaN(d.getTime())) return null;
    return new Date(d.getTime() + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ');
  }
  const local = (s) => (has(s) ? String(s).slice(0, 16).replace('T', ' ') : null);

  /* The receipt of the recorded second opinion, without request, probe or digest ids. */
  const receipt = (s) => (has(s) ? String(s).split(' · ').filter((p) => !/request|probe|digest|[0-9a-f]{10,}/i.test(p)).join(' · ') || null : null);

  const FAM_ORDER = Object.keys(FAMILY);
  const byFamily = (a, b) => FAM_ORDER.indexOf(a) - FAM_ORDER.indexOf(b);
  /* The ranked families of one view, in rank order (the record's own rank, then family order). */
  function families(rows) {
    const by = {}, rank = {};
    rows.forEach((r) => {
      if (!r || !r.family || r.family === 'P') return;
      (by[r.family] = by[r.family] || []).push(String(r.status || ''));
      if (num(r.rank) !== null) rank[r.family] = Math.min(rank[r.family] || Infinity, num(r.rank));
    });
    const ranked = Object.keys(by).sort((a, b) => (rank[a] || Infinity) - (rank[b] || Infinity) || byFamily(a, b)).filter((f) => by[f].some((s) => s === 'scored' || s === 'no data'));
    return { ranked, scored: ranked.filter((f) => by[f].includes('scored')), nodata: ranked.filter((f) => !by[f].includes('scored')) };
  }

  /* The stages for one card, each built from the loaded records. A missing value is NOT. */
  function stages(card, V, onto, page) {
    const c = CARDS[card] || CARDS.glance;
    page = page || {};
    const mode = page.mode || 'assumed';
    const m = (onto && onto.modes && onto.modes[mode]) || null;
    const fx = m && Array.isArray(m.facts) ? m.facts : [];
    const dr = (onto && onto.drivers && Array.isArray(onto.drivers[mode])) ? onto.drivers[mode] : null;
    const pv = (onto && onto.provenance) || {};
    const pp = pv.paragraph || null;
    const para = (onto && onto.paragraph) || null;
    const ex = (onto && onto.explanations) || null;
    const j = (V && V.judgment) || null;
    const isAI = !!(para && /gemini/i.test(String(para.kind || '')));
    const days = pv.baseline && num(pv.baseline.days);

    const notices = ((V && V.timeline) || []).filter((x) => x && x.src && x.src !== 'WESM RTD');
    const nIds = uniq(notices.map((x) => x.src));
    const nTimes = notices.map((x) => local(x.t)).filter(has).sort();
    const mt = (V && V.market && Array.isArray(V.market.t)) ? V.market.t : null;
    const fam = dr ? families(dr) : null;
    const bn = (dr || []).filter((r) => r.status === 'scored' && r.family !== 'F').map((r) => num(r.baseline_n)).filter((n) => n !== null);
    const kinds = uniq(fx.map((f) => { const k = String(f.source_table || '').split('.').pop(); return KIND[k] || (k ? 'other recorded data' : null); }));
    const ev = fx.filter((f) => f.availability_at_cutoff === 'evidenced').length;
    const asm = fx.filter((f) => f.availability_at_cutoff === 'assumed');
    const asmBy = {};
    asm.forEach((f) => { const k = f.availability_assumption || '?'; asmBy[k] = (asmBy[k] || 0) + 1; });
    const asmText = Object.keys(asmBy).map((k) => (ASSUME[k] ? `${asmBy[k]} ${asmBy[k] === 1 ? ASSUME[k][0] : ASSUME[k][1]}` : `${asmBy[k]} by another named assumption`)).join('; ');
    const held = m && Array.isArray(m.withheld) ? m.withheld : null;
    const heldBy = {};
    (held || []).forEach((w) => { const why = String((w && w.reason) || 'reason not recorded').replace(/\s*\(A-[A-Z]+\)/g, ''); heldBy[why] = (heldBy[why] || 0) + (num(w && w.n) !== null ? num(w.n) : 1); });
    const heldN = Object.values(heldBy).reduce((a, b) => a + b, 0);
    const unclear = m && Array.isArray(m.unconfirmed) ? m.unconfirmed.length : null;
    const rulesFacts = fx.filter((f) => f.family === 'Rules').length;

    const S = {
      S1: { name: 'Sources', kind: 'det',
        what: 'Only recorded data goes in: the WESM five-minute market data (our company copy), the NGCP system operator’s notices, the IEMOP list of registered units and their capacity, the HVDC link schedules and public cost series. Nothing is fetched live.',
        tools: [tool('bq', 'holds the recorded copies as tables')],
        fields: [
          ['Operator notices in this event', nIds.length ? `${nIds.length}${nTimes.length ? `, from ${nTimes[0]} to ${nTimes[nTimes.length - 1]} Manila` : ''}` : null],
          ['Market data around the event', mt && mt.length ? `${plural(mt.length, 'five-minute point')}, ${local(mt[0])} to ${local(mt[mt.length - 1])} Manila` : null],
          ['Fuel', m && has(m.fuel_context) ? (num(m.fuel_context) ? `fuel context available (${plural(num(m.fuel_context), 'row')}), no value shown` : 'none in this view') : null]],
        refs: [ref('Operator notices', '/notices'), ref('Data catalog', '/data'), ref('Assets: registered units', '/assets'),
          ref('NGCP system-operator notices (public)'), ref('IEMOP registered capacity and WESM market reports (public)')] },
      S2: { name: 'Cleaned five-minute data', kind: 'det',
        what: 'SQL cleans each five-minute interval into one row per region: demand, reserve, imports and the price, with its price band and pricing flags. Outage schedules are kept as recorded, and unit names in operator notices are matched to registered units by their known names only.',
        tools: [tool('bq', 'SQL that cleans and labels each interval')],
        fields: [['Kinds of record behind this view', kinds.length ? kinds.join(', ') : null],
          ['Facts in this view', m ? String(fx.length) : null]],
        refs: [ref('Data catalog', '/data')] },
      S3: { name: 'Facts with the time they were known (ontology)', kind: 'det',
        what: 'Every reading becomes a fact in one of six families (D demand, S supply and interconnection, P price, O outages, F fuel cost baseline, Rules) with the moment it became known. Things are linked only by plain relations (located in, part of, connects, refers to); there is no “causes” link. Each view keeps only the facts known by its cutoff.',
        tools: [tool('bq', 'SQL views that turn rows into facts with known-by times')],
        fields: [['Families with facts', m ? (uniq(fx.map((f) => f.family)).sort(byFamily).join(', ') || 'none') : null],
          ['Known with evidence', m ? String(ev) : null],
          ['Known by a named assumption', m ? (asm.length ? `${asm.length}: ${asmText}` : '0') : null],
          ['Held back', held ? (heldN ? `${heldN}: ${Object.keys(heldBy).map((k) => `${heldBy[k]} ${k}`).join('; ')}` : '0') : null],
          ['Unclear names', unclear === null ? null : (unclear ? `${unclear}, flagged: not linked, not counted` : '0')],
          ['Pricing-flag facts in this view', m ? String(rulesFacts) : null]],
        refs: [ref('InGRID, explained', '/explain')] },
      S4: { name: 'Ranking: what stood out', kind: 'det', how: true,
        what: 'A ranking query compares each indicator at the interval with the same Manila hour on the days before, and ranks the families by how unusual they were. Evidence, not proof.',
        tools: [tool('bq', 'the ranking query (a SQL table function)')],
        fields: [['Region and interval', onto && (onto.region || onto.t) ? `${onto.region || NOT} · ${local(onto.t) || NOT} Manila` : null],
          ['View', VIEW[mode] || null],
          ['Market data up to (cutoff)', m && manila(m.cutoff_utc) ? `${manila(m.cutoff_utc)} Manila` : null],
          ['Compared with', days ? `the same Manila hour on each of the ${days} days before${pv.baseline.excludes_t ? '; the interval itself is left out' : ''}` : null],
          ['Past intervals compared', bn.length ? (Math.min(...bn) === Math.max(...bn) ? `${Math.min(...bn)} per indicator` : `${Math.min(...bn)} to ${Math.max(...bn)} per indicator`) : null],
          ['Families scored', fam ? `${fam.scored.length} of ${fam.ranked.length}${fam.scored.length ? ` (${fam.scored.join(', ')})` : ''}${fam.nodata.length ? `; no data: ${fam.nodata.join(', ')}` : ''}` : null]],
        refs: [PAPER_METHODS] },
      S5: { name: 'Check and record', kind: 'det',
        what: 'Before anything reaches a page, SQL checks compare each card with expected answers and with the ontology’s own rules. Only cards that pass are recorded, and pages read that recorded copy.',
        tools: [tool('bq', 'SQL checks against expected answers'), tool('checks', 'keep only the cards that pass, then export them')],
        fields: [['Recorded at', manila(pv.recorded_at_utc) ? `${manila(pv.recorded_at_utc)} Manila` : null],
          ['Severity', (onto && onto.summary && onto.summary.severity) || null],
          ['Confidence', (onto && onto.summary && onto.summary.confidence) || null],
          ['Peso impact', 'Needs your portfolio']] },
      S6: { name: isAI ? 'AI rewording, then a code check' : 'Paragraph by template (no AI)', kind: isAI ? 'ai' : 'det',
        what: isAI ? 'Code writes the paragraph from the record. Gemini only rewords it. Code then checks that every figure and name is kept, nothing is added, and no cause words (caused, because, due to, drove, led to, triggered, resulted in) are used. If the check fails, the code’s own paragraph is shown.'
          : 'This record has no AI rewording: the paragraph shown is the one code wrote from the record.',
        tools: [tool('py', 'writes the paragraph from the record (template)')]
          .concat(isAI ? [tool('gemini', 'rewords it; a recorded run', true), tool('checks', 'Python verification: figures and names kept, none added, no cause words')] : []),
        fields: [['Result', para ? (para.kind || null) : null],
          ['Model', para ? (para.model || (isAI ? null : 'none')) : null],
          ['Attempt', isAI ? (pp && has(pp.attempt) ? `${pp.attempt} of ${has(pp.max_attempts) ? pp.max_attempts : NOT}` : null) : 'none'],
          ['Run at', isAI ? (pp && manila(pp.run_at_utc) ? `${manila(pp.run_at_utc)} Manila` : null) : 'none'],
          ['Problems the check found', isAI ? (pp && has(pp.problems_n) ? String(pp.problems_n) : null) : 'none'],
          ['Per-family explanations', ex && ex.items ? `${Object.keys(ex.items).length} kept${pv.explanations && has(pv.explanations.dropped_n) ? `, ${pv.explanations.dropped_n} dropped by the check` : ''}${ex.model ? ` (${ex.model})` : ''}` : null]],
        refs: [PAPER_METHODS] },
      S7: { name: 'Bake the files this page reads', kind: 'det',
        what: 'Code writes the files this page reads: fuel is reduced to a count, internal rows are dropped, unclear name matches keep only their words and the reason, and explanations are checked again against today’s facts.',
        tools: [tool('py', 'bakes the public files from the recorded copy')],
        fields: [['Baked at', manila(pv.baked_at_utc) ? `${manila(pv.baked_at_utc)} Manila` : null],
          ['Replay points around the event', mt ? String(mt.length) : null],
          ['Event and ontology records loaded', `${V ? 'event record' : 'no event record'}, ${onto ? 'ontology record' : 'no ontology record'}`]] },
      S8: { name: 'AI second opinion (recorded)', kind: 'ai',
        what: 'A recorded Gemini run read the trigger notice in several phrasings and answered the same fixed questions each time. Code kept the answer the phrasings agreed on and marks it unstable when they differ. Not re-run on this page.',
        tools: [tool('gemini', 'answered fixed questions on the trigger notice; a recorded run', true), tool('checks', 'Python stability check across phrasings')],
        fields: [['Model', j ? (j.by || null) : null],
          ['Questions', j && Array.isArray(j.questions) ? String(j.questions.length) : null],
          ['Receipt', j ? receipt(j.receipt) : null],
          ['Same answer across phrasings', j && typeof j.unstable === 'boolean' ? (j.unstable ? 'No (unstable)' : 'Yes') : null]],
        refs: [ref('Working paper: Appendix C, the recorded judgment', '/paper#ch0-appendix-c-the-recorded-judgment-passages-questions-thresholds-and-rules')] },
      S9: { name: 'This page', kind: 'det',
        what: 'This page reads the baked files, then hides anything known after the as-of clock and applies the chosen view. No model is called here.',
        tools: [tool('host', 'serve the baked files'), tool('browser', 'JavaScript draws the cards and applies the clock and view')],
        fields: [['As-of clock', page.asOf ? `${local(page.asOf)} Manila` : null], ['View', VIEW[mode] || null],
          ['Notice cutoffs in the record', V && Array.isArray(V.cutoffs) ? String(V.cutoffs.length) : null],
          ['Limits stated', V && Array.isArray(V.limits) ? String(V.limits.length) : null],
          ['Model calls on this page', 'none']] },
    };

    const how = days ? [
      `For the region and the five-minute interval, each indicator is compared with every interval in the same Manila hour over the ${days} days before. The interval itself is not in the baseline.`,
      'score = (past values below the value now + half of the past values equal to it) / number of past values',
      'D demand: the region’s market requirement.', 'S supply: reserve shortfall, import share, congested HVDC links.',
      'O outages: capacity scheduled out; derated capacity linked by an accepted name only.',
      'Rules: congested transmission elements and their overload. Pricing flags are listed, never scored.',
      'F fuel cost baseline: against its own monthly history. Ranked after the rest when any other family scores 80% or more.',
      'A family’s score is its strongest indicator. Highest first; ties by family name. A missing value is “No data”, never 0. This is a percentile, not a cause.',
    ] : null;

    const list = ORDER.map((id) => {
      const s = S[id];
      const fields = s.fields.map(([label, v]) => {
        const value = has(v) ? clean(v) : NOT;
        return { label, value: has(value) ? value : NOT, missing: !has(v) || !has(value), flag: /flagged/.test(String(v || '')) };
      });
      return { id, name: s.name, kind: s.kind, on: c.stages.includes(id), what: clean(s.what), tools: s.tools.map((t) => Object.assign({}, t, { role: clean(t.role) })),
        fields, refs: (s.refs || []).map((r) => ({ label: clean(r.label), href: r.href })), how: s.how ? (how ? how.map(clean) : null) : null };
    });
    const built = [['Event', V && V.title], ['View', VIEW[mode]], ['As of', page.asOf ? local(page.asOf) + ' Manila' : null],
      ['Recorded', manila(pv.recorded_at_utc)], ['Baked', manila(pv.baked_at_utc)]]
      .map(([label, v]) => ({ label, value: has(v) ? clean(v) : NOT, missing: !has(v) }));
    const mine = list.filter((s) => s.on);
    return { card, name: c.name, what: c.what(isAI), built, stages: list,
      missing: mine.reduce((a, s) => a + s.fields.filter((f) => f.missing).length, 0) + (mine.some((s) => s.id === 'S4') && !how ? 1 : 0) };
  }

  const api = { stages, clean, manila, CARDS, ORDER, NOT };
  (typeof globalThis !== 'undefined' ? globalThis : window).GridFlow = api;
  if (typeof document === 'undefined') return;

  // ------------------------------------------------------------------ the dialog
  const el = (tag, cls, text, parent) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  let ctx = null, current = null, full = false, opener = null, dom = null;

  function build() {
    const scrim = el('div', 'gf-scrim', null, document.body);
    scrim.hidden = true;
    const dlg = el('div', 'gf-dlg', null, scrim);
    dlg.setAttribute('role', 'dialog');
    dlg.setAttribute('aria-modal', 'true');
    dlg.setAttribute('aria-labelledby', 'gf-t');
    dlg.setAttribute('aria-describedby', 'gf-d');
    const head = el('div', 'gf-h', null, dlg);
    const ht = el('div', 'gf-ht', null, head);
    const t = el('h2', null, 'How we got this', ht);
    t.id = 'gf-t';
    t.tabIndex = -1;
    const d = el('p', null, null, ht);
    d.id = 'gf-d';
    const x = el('button', 'gf-x', '×', head);
    x.type = 'button';
    x.setAttribute('aria-label', 'Close');
    const body = el('div', 'gf-b', null, dlg);
    const built = el('div', 'gf-built', null, body);
    built.setAttribute('aria-label', 'Built from');
    const map = el('div', 'gf-map', null, body);
    map.setAttribute('aria-hidden', 'true');
    const bar = el('div', 'gf-bar', null, body);
    const legend = el('div', 'gf-legend', null, bar);
    el('span', 'gf-pill det', 'Deterministic: code or SQL', legend);
    el('span', 'gf-pill ai', 'AI: recorded run, then checked by code', legend);
    const all = el('button', 'gf-tog', 'Show the full flow', bar);
    all.type = 'button';
    all.setAttribute('aria-pressed', 'false');
    const flow = el('ol', 'gf-flow', null, body);
    const rules = el('details', 'gf-how', null, body);
    el('summary', null, 'Rules this view keeps', rules);
    const ul = el('ul', 'gf-rules', null, rules);
    ['Recorded data only. Nothing here is a forecast, and no model is called when the page opens.',
      'Unit technology and fuel are never shown. Fuel appears only as “fuel context available”.',
      'Notice text is shown through the page’s notice filter, as posted.',
      'A name matched with less than 50% certainty stays flagged as unclear: not linked, not counted.',
      'No peso figure is made up. Without portfolio data the answer is “Needs your portfolio”.',
      'Only pages of this site and public sources are named as references.'].forEach((s) => el('li', null, s, ul));
    const foot = el('div', 'gf-f', null, dlg);
    x.addEventListener('click', close);
    all.addEventListener('click', () => { full = !full; render(); });
    scrim.addEventListener('click', (e) => { if (e.target === scrim) close(); });
    document.addEventListener('keydown', onKey);
    return { scrim, dlg, t, d, built, map, all, flow, foot };
  }

  function render() {
    const page = { mode: ctx.mode ? ctx.mode() : 'assumed', asOf: ctx.asOf ? ctx.asOf() : null };
    const r = stages(current, ctx.V, ctx.onto, page);
    dom.t.textContent = 'How we got this: ' + r.name;
    dom.d.textContent = r.what;
    dom.built.replaceChildren();
    r.built.forEach((b) => {
      const p = el('span', 'gf-pill' + (b.missing ? ' gf-na' : ''), null, dom.built);
      el('b', null, b.label + ' ', p);
      p.appendChild(document.createTextNode(b.value));
    });
    const list = r.stages.filter((s) => full || s.on);
    dom.map.replaceChildren();
    list.forEach((s, i) => {
      el('span', 'gf-st' + (s.on ? ' on' : '') + (s.kind === 'ai' ? ' ai' : ''), s.id, dom.map);
      if (i < list.length - 1) el('i', null, '→', dom.map);
    });
    dom.flow.replaceChildren();
    list.forEach((s) => {
      const li = el('li', (s.on ? 'on' : 'off') + (s.kind === 'ai' ? ' ai' : ''), null, dom.flow);
      el('span', 'gf-dot', s.id, li);
      const h = el('div', 'gf-sh', null, li);
      el('b', null, s.name, h);
      el('span', 'gf-pill ' + s.kind, s.kind === 'ai' ? 'AI' : 'Deterministic', h);
      if (!s.on) el('span', 'gf-pill', 'not used by this card', h);
      const tl = el('div', 'gf-tools', null, li);
      el('span', 'gf-tools-k', 'Tools', tl);
      s.tools.forEach((t) => {
        const c = el('span', 'gf-tool ' + t.kind, null, tl);
        el('b', null, t.name, c);
        el('span', null, t.role, c);
      });
      el('p', 'gf-what', s.what, li);
      if (!s.on) return;
      const dl = el('dl', 'gf-kv', null, li);
      s.fields.forEach((f) => {
        el('dt', null, f.label, dl);
        const dd = el('dd', f.missing ? 'gf-na' : null, f.value, dl);
        if (f.flag) dd.prepend(el('span', 'gf-pill unc', 'Unclear'), ' ');
      });
      if (s.refs.length) {
        const rp = el('p', 'gf-refs', null, li);
        el('span', 'gf-tools-k', 'See for yourself', rp);
        s.refs.forEach((x) => {
          if (x.href) { const a = el('a', null, x.label, rp); a.href = x.href; } else el('span', 'gf-ext', x.label, rp);
        });
      }
      if (s.how !== null && s.how !== undefined || s.id === 'S4') {
        const d = el('details', 'gf-how', null, li);
        if (current === 'ranked') d.open = true;
        el('summary', null, 'How the ranking works', d);
        if (!s.how) { el('p', 'gf-na', NOT + ': the baseline window.', d); return; }
        el('p', null, s.how[0], d);
        el('div', 'gf-formula', s.how[1], d);
        const ul = el('ul', null, null, d);
        s.how.slice(2).forEach((t) => el('li', null, t, ul));
      }
    });
    dom.foot.textContent = `Built from the records loaded on this page, for this card. ${r.missing ? plural(r.missing, 'field') + ' not in the record.' : 'Every field is in the record.'}`;
    dom.all.setAttribute('aria-pressed', String(full));
    dom.all.textContent = full ? 'Show only this card’s stages' : 'Show the full flow';
  }

  const focusables = () => Array.from(dom.dlg.querySelectorAll('button, summary, a[href], [tabindex]:not([tabindex="-1"])'))
    .filter((n) => !n.closest('[hidden]') && !(n.closest('details:not([open])') && n.tagName !== 'SUMMARY'));
  function onKey(e) {
    if (!dom || dom.scrim.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); close(); return; }
    if (e.key !== 'Tab') return;
    const f = focusables();
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === dom.t)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  const behind = () => Array.from(document.body.children).filter((n) => n !== dom.scrim);
  function open(card, btn) {
    current = card; full = false; opener = btn;
    render();
    dom.scrim.hidden = false;
    behind().forEach((n) => { n.inert = true; });
    document.body.classList.add('gf-lock');
    dom.t.focus();
  }
  function close() {
    dom.scrim.hidden = true;
    behind().forEach((n) => { n.inert = false; });
    document.body.classList.remove('gf-lock');
    if (opener) opener.focus();
  }

  /* ctx: { V, onto, mode: () => view key, asOf: () => 'YYYY-MM-DDTHH:MM' }. */
  function mount(c) {
    ctx = c || {};
    if (!dom) dom = build();
    document.querySelectorAll('button[data-flow]').forEach((b) => {
      if (!CARDS[b.dataset.flow] || b.dataset.flowOn) return;
      b.dataset.flowOn = '1';
      b.hidden = false;
      b.addEventListener('click', () => open(b.dataset.flow, b));
    });
  }
  api.mount = mount;
})();
