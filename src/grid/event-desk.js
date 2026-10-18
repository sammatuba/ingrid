/* InGRID event desk (ericka-desk slice 7, E13 and E15 to E20; platform polish PP-B2).

   Draws the event page's decision workspace beside what src/grid/event.js writes (the title, the
   AI reader's sentences, the person's line, the case's decision form and its history):
   - the head's status badges: the AI reader's proposal and the person's decision, apart, with
     the synthetic label and the severity when the record carries one;
   - the anchor: the trigger notice, the price move as the key figure (price at the trigger, the
     highest after it and the minutes between), the view's other figures, and one line for every
     value the record does not carry (E13, E15);
   - "What happened": the price chart with the trigger, the highest price, each notice, the
     reserve shortfall and the as-of clock, then "How we got here" as one compact list (E16);
   - "What stood out" and the explanation, from the ontology record, when it is baked (E19);
   - the records behind the event as tabs: related records, price rules, what the system read
     and the audit trail (E18, E20);
   - in the decision region: the reader's label, cutoff, run record and answers, the assumption
     it touches, the decision box (journal-box.js) and this person's journal entries as receipts.
   Every figure is read from the baked event view or the ontology record; a figure they do not
   carry is said once on an unknowns line, and nothing is estimated.

   The rules are pure functions exposed as `GridEventDesk` so tests can run them on node. Every
   value is written as text; the page reads the same baked files event.js reads, through
   window.EventAPI, and the journal through GNJournal.api, and nothing else. */
(function () {
  'use strict';

  const CAP = 32000;
  const MANILA_MS = 8 * 3600 * 1000;
  const FAMILY = { D: 'Demand', S: 'Supply and interconnection', P: 'Price', O: 'Outages',
    F: 'Fuel cost baseline', Rules: 'Rules and grid constraints' };
  const MODES = [['assumed', 'As known at the time'], ['strict', 'Strict'], ['hindsight', 'Hindsight']];
  const KIND = { trip: 'Trip', mld: 'Load dropping', yellow: 'Yellow alert', red: 'Red alert',
    online: 'Back online', notice: 'Notice', market: 'Market', price: 'Price', drivers: 'Drivers' };
  /* [label, type, weight]: 'bad' facts are an administered, mitigated or substituted price;
     'cap' facts say a cap bound the price. */
  const RULES = {
    admin_priced: ['Administered price', 'flag', 'bad'],
    price_mitigated: ['Price mitigated', 'flag', 'bad'],
    price_substituted: ['Price substituted', 'flag', 'bad'],
    cap_bound: ['Offer cap bound', 'flag', 'cap'],
    secondary_cap: ['Secondary cap', 'flag', 'cap'],
    n_nodes_ap: ['Nodes under administered price', 'count', 'bad'],
    n_nodes_sec: ['Nodes under secondary cap', 'count', 'cap'],
    n_nodes_psm: ['Nodes with price substitution', 'count', 'bad'],
  };
  /* No table, file or script name reaches the page: a record source reads in plain words (the
     data catalog at /data lists the public sources), and a receipt drops its request ids. */
  const TABLE = { intervals: 'five-minute market intervals', labels: 'price bands and pricing flags',
    labels_reserve: 'reserve readings', interval_pricing: 'pricing per interval', outage_events: 'outage schedule records',
    outage_mentions: 'unit names in operator notices', ext_rtd_hvdc_schedules: 'HVDC link schedules',
    advisories_parsed: 'operator notices read by code', grid_congestions: 'congestion records' };
  const plainSrc = (s) => {
    const x = String(s || '').trim();
    if (/grid_ontology|record_cards|driver_card/.test(x)) return 'Ontology record (facts with the time each was known), checked by code before it was recorded';
    const t = /^[\w-]+\.(\w+)$/.exec(x);
    if (t) return TABLE[t[1]] || 'recorded grid data';
    return /grid_\w|\.(sql|sh|py|json|csv)\b/.test(x) ? 'recorded grid data' : x;
  };
  const plainReceipt = (r) => String(r).split(' · ').filter((p) => !/request|probe|digest|[0-9a-f]{10,}|[\w/]+\.(json|py|sh|sql)\b/i.test(p)).join(' · ');
  /* A plant name that reveals technology or fuel is never shown. */
  const FUEL = { test: (x) => new RegExp(TECH_WORDS.source, 'i').test(x) };

  const hhmm = (t) => String(t || '').slice(11, 16);
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const when = (t) => (t ? `${Number(String(t).slice(8, 10))} ${MONTHS[Number(String(t).slice(5, 7)) - 1] || ''} ${hhmm(t)}` : 'No data');
  const peso = (v) => '₱' + Math.round(Number(v)).toLocaleString('en-US');
  const TECH_WORDS = new RegExp('\\b(?:geo-?thermal\\w*|thermal|solar|photo-?voltaic|pv|hydro\\w*|hepp?|coal(?:-fired)?|diesel|bunker|fuel|oil|gas|lng|ccgt|combined[- ]cycle|wind|biomass|bio\\w*|battery|bess|nuclear|pumped[- ]storage|steam|hfo|cfpp|[dgsw]ppi?)\\b', 'gi');
  /* Notice text keeps its words except technology words, withheld as in asset.js. */
  const withheld = (s) => String(s == null ? '' : s).replace(TECH_WORDS, '[…]').replace(/\[…\](?:[\s-]*\[…\])+/g, '[…]');
  /* The shell's own notice filter when the page has it (window.GNShell.opText); the same rule here otherwise. */
  const shellOp = (s) => {
    const g = typeof window !== 'undefined' && window.GNShell && typeof window.GNShell.opText === 'function' ? window.GNShell.opText : null;
    return g ? String(g(s)) : withheld(s);
  };
  const opText = (s) => shellOp(s)
    .replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ').trim();
  const num = (v) => (v === null || v === undefined || v === '' ? null : (Number.isFinite(Number(v)) ? Number(v) : null));

  /* '2026-09-21 05:45:00' (UTC, as the ontology records it) -> '2026-09-21T13:45' Manila. */
  function manilaFromUtc(s) {
    if (!s) return null;
    const d = new Date(String(s).trim().replace(' ', 'T').replace(/(Z|[+-]\d\d:\d\d)?$/, (m) => m || 'Z'));
    if (Number.isNaN(d.getTime())) return null;
    return new Date(d.getTime() + MANILA_MS).toISOString().slice(0, 16);
  }

  /* The operator text without its "Visayas Grid-09/21/2026 13:40:" prefix. */
  const noticeBody = (text) => opText(String(text || '').replace(/^[^:]*?\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\s*/, ''));

  function priceAt(m, t) {
    if (!m || !Array.isArray(m.t) || !Array.isArray(m.lmp)) return null;
    let hit = null;
    m.t.forEach((x, i) => { if (x <= t && num(m.lmp[i]) !== null) hit = { t: x, value: num(m.lmp[i]) }; });
    return hit;
  }
  function peakFrom(m, t) {
    if (!m || !Array.isArray(m.t) || !Array.isArray(m.lmp)) return null;
    let best = null;
    m.t.forEach((x, i) => {
      const v = num(m.lmp[i]);
      if (x >= t && v !== null && (!best || v > best.value)) best = { t: x, value: v };
    });
    return best;
  }

  /* CORP-5 on the canvas: a view with a rules block names, per cutoff, the announcements the
     corpus store places. The page has no cutoff switch, so the view's first state governs: a
     passage that state does not place is named by its record with the store's reason, and its
     text is not shown anywhere on the page. */
  function heldBack(V, ref) {
    const st = V && V.rules && Array.isArray(V.rules.states) ? V.rules.states[0] : null;
    if (!st || !ref) return null;
    const n = (Array.isArray(st.announcements) ? st.announcements : []).find((x) => x && x.claim_ref === ref);
    if (!n || (n.status === 'placed' && n.quote)) return null;
    return String(n.status_reason || 'not placed');
  }
  const heldText = (ref, why) => `Text not shown: the record's cutoff does not place this passage (${why}). Record ${ref}.`;

  /* E15: one line, trigger first. */
  function lead(V) {
    const a = V && V.advisory;
    if (!a || !a.text) return { trigger: null, text: 'Trigger: No data. No operator notice is on record for this event.' };
    const at = String(V.event_at || a.t || '').slice(0, 16);
    const region = V.grid_name || 'the region';
    const held = heldBack(V, a.id);
    let text = held ? `Trigger: ${a.id} at ${hhmm(a.t)}: ${heldText(a.id, held)}` : `Trigger: NGCP ${a.id} at ${hhmm(a.t)}: ${noticeBody(a.text)}.`;
    const before = priceAt(V.market, at);
    const peak = peakFrom(V.market, at);
    if (before && peak) {
      text += ` ${region} price ${peso(before.value)}/MWh at ${hhmm(before.t)}; highest after the trigger ${peso(peak.value)}/MWh at ${hhmm(peak.t)}`;
      text += peak.value >= CAP ? ', the ₱32,000 offer cap.' : '.';
    } else {
      text += ` ${region} price around the trigger: No data.`;
    }
    return { trigger: a.id, text };
  }

  /* E13: the Rules facts of the "as known at the time" view. A fact with no value is No data. */
  function rulesFlag(onto, V) {
    const facts = (((onto || {}).modes || {}).assumed || {}).facts || [];
    const items = [];
    const on = { bad: [], cap: [] };
    let known = 0;
    Object.keys(RULES).forEach((key) => {
      const f = facts.find((x) => x && x.family === 'Rules' && x.predicate === key);
      const [label, type, weight] = RULES[key];
      const v = f ? num(f.value_num) : null;
      const vt = f && f.value_text != null ? String(f.value_text).trim() : null;
      let value = 'No data', yes = false;
      if (v !== null) {
        known += 1;
        value = type === 'count' ? String(v) : (v ? 'Yes' : 'No');
        yes = v > 0;
      } else if (vt) {
        known += 1;
        if (/^(true|yes)$/i.test(vt)) { value = 'Yes'; yes = true; }
        else if (/^(false|no)$/i.test(vt)) value = 'No';
        else value = vt;
      }
      if (yes) on[weight].push(label);
      items.push({ key, label, value });
    });
    const peak = V ? peakFrom(V.market, String(V.event_at || '').slice(0, 16)) : null;
    let level = 'none', headline = 'Pricing rules: No data';
    if (on.bad.length) { level = 'bad'; headline = `On record: ${on.bad.join(', ')}`; }
    else if (on.cap.length) { level = 'warn'; headline = `On record: ${on.cap.join(', ')}`; }
    else if (peak && peak.value >= CAP) { level = 'warn'; headline = `Price at the ₱32,000 offer cap at ${hhmm(peak.t)}`; }
    else if (known) { level = 'ok'; headline = 'No administered, mitigated or capped price on record'; }
    return { level, headline, items, known };
  }

  /* E16: the trail, first notice to price. Each step carries its data and source. */
  function trail(V, onto) {
    const steps = [];
    (V && Array.isArray(V.timeline) ? V.timeline : []).forEach((x) => {
      if (!x || !x.t) return;
      const held = heldBack(V, x.src);
      steps.push({ t: String(x.t).slice(0, 16), kind: x.kind || 'notice', title: KIND[x.kind] || 'Notice',
        detail: held ? heldText(x.src, held) : opText(x.text), source: x.src === 'WESM RTD' ? 'WESM real-time dispatch (company copy)' : `NGCP notice ${x.src}` });
    });
    const at = V ? String(V.event_at || '').slice(0, 16) : '';
    const region = (V && V.grid_name) || 'Region';
    const before = V ? priceAt(V.market, at) : null;
    const peak = V ? peakFrom(V.market, at) : null;
    /* The trail opens with the first notice; the price just before it is part of that step. */
    const first = steps.find((x) => x.kind !== 'market');
    if (first && before) first.detail += ` (${region} price before: ${peso(before.value)}/MWh at ${hhmm(before.t)}, WESM real-time dispatch)`;
    if (peak && (!before || peak.t !== before.t)) steps.push({ t: peak.t, kind: 'price', title: 'Highest price after the trigger',
      detail: `${region} price ${peso(peak.value)}/MWh${peak.value >= CAP ? ', the ₱32,000 offer cap' : ''}`,
      source: 'WESM real-time dispatch (company copy)' });
    const s = onto && onto.summary;
    if (s && s.relationship_trail) steps.push({ t: manilaFromUtc(onto.t) || String(onto.t || '').slice(0, 16), kind: 'drivers',
      title: 'How the drivers connect', detail: String(s.relationship_trail), source: onto.source ? plainSrc(onto.source) : 'Ontology record' });
    steps.sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0));
    return steps;
  }

  /* Split the trail at the shared "as of" clock: later steps are hidden, and counted. */
  function upTo(steps, asOf) {
    if (!asOf) return { shown: steps, later: 0 };
    const shown = steps.filter((x) => x.t <= asOf);
    return { shown, later: steps.length - shown.length };
  }

  function topFamily(onto, mode) {
    const rows = ((onto || {}).drivers || {})[mode];
    if (!Array.isArray(rows)) return null;
    const ranked = rows.filter((r) => r && r.status === 'scored' && num(r.rank) !== null)
      .sort((a, b) => num(a.rank) - num(b.rank));
    return ranked.length ? (FAMILY[ranked[0].family] || ranked[0].family) : null;
  }

  /* E19: everything on the card comes from the records. */
  function explanation(onto, V) {
    const p = (onto && onto.paragraph) || null;
    const views = MODES.map(([key, label]) => ({ key, label, top: topFamily(onto, key) }));
    const ranked = views.filter((v) => v.top);
    const tops = Array.from(new Set(ranked.map((v) => v.top)));
    let holds;
    if (ranked.length < 2) holds = 'Cannot tell: fewer than two views carry ranked drivers.';
    else if (tops.length === 1) holds = `Yes in ${ranked.length} of 3 views: ${tops[0]} ranks first` + (ranked.length < 3 ? '; ' + views.filter((v) => !v.top).map((v) => v.label).join(', ') + ': No data.' : '.');
    else holds = 'No: the views rank different drivers first.';
    const disagreement = [];
    if (tops.length > 1) disagreement.push('Top driver by view: ' + ranked.map((v) => `${v.label}: ${v.top}`).join('; ') + '.');
    const j = V && V.judgment;
    if (j && j.unstable) disagreement.push('The AI reader changed its answer across phrasings (unstable).');
    const flip = j && /max flip rate ([\d.]+)/.exec(String(j.receipt || ''));
    const summary = (onto && onto.summary) || {};
    const facts = (((onto || {}).modes || {}).assumed || {}).facts || [];
    const tables = Array.from(new Set(facts.map((f) => f && f.source_table).filter(Boolean).map(plainSrc))).sort();
    return {
      text: p && p.text ? String(p.text) : null,
      kind: p && p.kind ? String(p.kind) : null,
      model: p && p.model ? String(p.model) : null,
      knownAt: manilaFromUtc(onto && onto.t),
      cutoff: manilaFromUtc((((onto || {}).modes || {}).assumed || {}).cutoff_utc),
      views, holds,
      disagreement: disagreement.length ? disagreement
        : [flip ? `None recorded: the ranked views agree and the AI reader's flip rate was ${flip[1]}.` : 'None recorded between the ranked views.'],
      confidence: summary.confidence ? `${summary.confidence}${summary.confidence_reason ? ': ' + summary.confidence_reason : ''}` : 'No data',
      sources: [onto && onto.source ? plainSrc(onto.source) : null].concat(tables).filter(Boolean),
      reader: j && j.by ? String(j.by) : null,
    };
  }

  /* E18 and E20. Unclear matches are listed by their own words, never linked or counted. */
  function audit(onto, V) {
    const modes = (onto && onto.modes) || {};
    const unclear = [];
    const withheld = {};
    MODES.forEach(([key, label]) => {
      const m = modes[key] || {};
      withheld[label] = Array.isArray(m.withheld) ? m.withheld.reduce((a, w) => a + (num(w && w.n) !== null ? num(w.n) : 1), 0) : null;
      (Array.isArray(m.unconfirmed) ? m.unconfirmed : []).forEach((u) => {
        const name = u && (u.plant_text || u.object_label || u.subject_label || u.value_text);
        const shown = !name ? 'Name not in the record' : (FUEL.test(String(name)) ? 'Name not shown (it names a technology)' : String(name));
        unclear.push({ view: label, text: shown, reason: u && u.reason ? String(u.reason) : null });
      });
    });
    const notices = (V && Array.isArray(V.timeline) ? V.timeline : []).map((x) => x && x.src).filter((s) => s && s !== 'WESM RTD');
    const summary = (onto && onto.summary) || {};
    const j = V && V.judgment;
    const impact = String(summary.financial_impact || '');
    return {
      sources: [`NGCP notices ${notices.join(', ') || 'none'}`, 'WESM real-time dispatch (company copy)']
        .concat(onto && onto.source ? [plainSrc(onto.source)] : []),
      calculation: [onto && onto.heading ? String(onto.heading) : null,
        summary.severity ? `Severity ${summary.severity}: ${summary.severity_reason || 'no reason recorded'}` : null,
        `Peso impact: ${/portfolio/i.test(impact) || !impact ? 'Needs your portfolio' : impact}`].filter(Boolean),
      models: [onto && onto.paragraph && onto.paragraph.model ? `Paragraph: ${onto.paragraph.model} (${onto.paragraph.kind || 'kind not recorded'})` : null,
        j && j.by ? `AI reader: ${j.by}` : null, j && j.receipt && plainReceipt(j.receipt) ? `Receipt: ${plainReceipt(j.receipt)}` : null].filter(Boolean),
      withheld, unclear,
      check: Array.isArray(summary.what_to_check) ? summary.what_to_check.map(String) : [],
    };
  }

  /* The three views as the canvas names them: what each shows and what it leaves out, by the
     record's own reasons. A withheld entry counts its `n` facts, or one when it carries none. */
  const VIEW = {
    strict: ['What we can prove we knew', 'Strict: only facts with evidence of when they were known.'],
    assumed: ['What we likely knew', 'As known at the time (default): each market run is assumed available at the end of its interval.'],
    hindsight: ['Everything we know now', 'Hindsight: everything, including facts recorded later. Not what anyone knew at the time.'],
  };
  function views(onto) {
    const modes = (onto && onto.modes) || {};
    return ['strict', 'assumed', 'hindsight'].filter((k) => modes[k]).map((key) => {
      const m = modes[key] || {};
      const by = new Map();
      (Array.isArray(m.withheld) ? m.withheld : []).forEach((w) => {
        const why = (w && w.reason) ? String(w.reason) : 'reason not recorded';
        by.set(why, (by.get(why) || 0) + (num(w && w.n) !== null ? num(w.n) : 1));
      });
      const hidden = Array.from(by.values()).reduce((a, b) => a + b, 0);
      const shown = Array.isArray(m.facts) ? m.facts.length : null;
      const unconfirmed = Array.isArray(m.unconfirmed) ? m.unconfirmed.length : 0;
      return { key, label: VIEW[key][0], line: `${VIEW[key][1]} ${shown === null ? 'No data' : shown} shown, ${hidden} hidden.`,
        shown, hidden, byReason: Array.from(by.entries()).map(([why, n]) => ({ n, why })), unconfirmed };
    });
  }

  /* At a glance. The ranked families of one view, most unusual first: one row per family, with
     the family's own score from the record (a percent of the same hour on the last 28 days; fuel
     against its own monthly history). A family the record leaves unscored is named, not drawn. */
  function ranked(onto, mode) {
    const rows = ((onto || {}).drivers || {})[mode];
    if (!Array.isArray(rows)) return { rows: [], unscored: [] };
    const by = new Map();
    rows.forEach((r) => {
      if (!r || r.status !== 'scored' || num(r.rank) === null || num(r.family_score) === null || by.has(r.family)) return;
      by.set(r.family, { family: r.family, label: FAMILY[r.family] || String(r.family), rank: num(r.rank),
        pct: Math.round(num(r.family_score) * 100) });
    });
    const out = Array.from(by.values()).sort((a, b) => a.rank - b.rank);
    const unscored = Array.from(new Set(rows.filter((r) => r && r.family && r.family !== 'P' && r.family !== 'Rules'
      && !by.has(r.family)).map((r) => FAMILY[r.family] || String(r.family))));
    return { rows: out, unscored };
  }
  /* The record's own "usual" for the price: the price row's 28-day median at this hour. */
  function usualPrice(onto, mode) {
    const rows = ((onto || {}).drivers || {})[mode];
    const r = Array.isArray(rows) ? rows.find((x) => x && x.family === 'P' && x.indicator === 'price_capped_median') : null;
    if (!r) return null;
    const base = num(r.baseline_median), at = num(r.value_at_t);
    return base === null ? null : { usual: base, at, unit: r.unit || 'PHP/MWh' };
  }
  const minutes = (a, b) => {
    const x = Date.parse(String(a).slice(0, 16) + ':00Z'), y = Date.parse(String(b).slice(0, 16) + ':00Z');
    return Number.isFinite(x) && Number.isFinite(y) ? Math.round((y - x) / 60000) : null;
  };
  const NOT = 'Not in the record';
  const pctWords = (p, fam) => `Higher than ${p}% of ${fam === 'F' ? 'its own monthly history' : 'the same hour on the last 28 days'}`;

  /* The summary cards: each is a label, one figure and one plain line, all from the records. */
  function glance(V, onto, mode, asOf) {
    const at = String((V && V.event_at) || '').slice(0, 16);
    const m = V && V.market;
    const before = at ? priceAt(m, at) : null;
    const peak = at ? peakFrom(m, at) : null;
    const tiles = [];
    tiles.push({ key: 'trigger', label: 'Price at the trigger', value: before ? peso(before.value) : NOT, unit: before ? '/MWh' : '',
      note: before ? `Five-minute price at ${hhmm(before.t)}, the last interval before the trigger at ${hhmm(at)}.` : 'No market price is recorded around the trigger.' });
    let peakNote = 'No market price is recorded after the trigger.';
    if (peak) {
      peakNote = peak.value >= CAP ? `At the ₱32,000 offer cap, first at ${hhmm(peak.t)}.` : `First reached at ${hhmm(peak.t)}.`;
      if (before && peak.value === before.value) peakNote += ' The price was already there before the trigger.';
      else if (before && before.value > 0) peakNote += ` ${(peak.value / before.value).toFixed(1)}× the price at the trigger.`;
    }
    tiles.push({ key: 'peak', label: 'Highest after the trigger', value: peak ? peso(peak.value) : NOT, unit: peak ? '/MWh' : '', note: peakNote });
    const u = usualPrice(onto, mode);
    const ot = manilaFromUtc(onto && onto.t);
    tiles.push({ key: 'usual', label: 'Usual price for this hour', value: u ? peso(u.usual) : NOT, unit: u ? '/MWh' : '',
      note: u ? `28-day median of the capped median price at ${ot ? hhmm(ot) : 'this hour'}${u.at !== null ? `; at the event it was ${peso(u.at)}${u.usual > 0 ? `, ${(u.at / u.usual).toFixed(1)}× usual` : ''}` : ''}.`
        : 'The record carries no usual price for this hour.' });
    const lag = peak ? minutes(at, peak.t) : null;
    const a = V && V.advisory;
    tiles.push({ key: 'lag', label: 'Trigger to highest price', value: lag === null ? NOT : `${lag} min`, unit: '',
      note: lag === null ? 'Needs a trigger time and a market price after it.'
        : `Trigger at ${hhmm(at)}, highest at ${hhmm(peak.t)}.${before && before.value >= peak.value ? ` The price was already ${peso(before.value)} at ${hhmm(before.t)}, before the trigger.` : ''}${a && a.t ? ` Operator notice posted at ${hhmm(a.t)}.` : ''}` });
    const all = trail(V, onto);
    const cut = upTo(all, asOf);
    tiles.push({ key: 'steps', label: 'Steps in How we got here', value: all.length ? String(cut.shown.length) : NOT, unit: '',
      note: !all.length ? 'The record carries no steps.' : cut.later ? `${cut.later} more after the as-of clock (${hhmm(asOf)}).` : 'From the first notice to the price, each with its source.' });
    const cur = views(onto).find((x) => x.key === mode) || null;
    tiles.push({ key: 'facts', label: 'Facts in this view', value: cur && cur.shown !== null ? `${cur.shown} shown` : NOT, unit: '',
      note: cur ? `${cur.hidden} left out in this view (see What do you want to see?).${cur.unconfirmed ? ` ${cur.unconfirmed} unclear name${cur.unconfirmed === 1 ? '' : 's'}, not counted.` : ''}` : 'No ontology record for this event.' });
    const r = ranked(onto, mode).rows[0] || null;
    tiles.push({ key: 'top', label: 'Stood out most', value: r ? r.label : NOT, unit: '',
      note: r ? `${pctWords(r.pct, r.family)}. Evidence, not proof.` : 'No ranked drivers in this view.' });
    return tiles;
  }

  /* The price line's data: the recorded five-minute series, the trigger, the marks the view
     carries, the highest price after the trigger and the offer cap. */
  function priceSeries(V) {
    const m = (V && V.market) || {};
    const t = Array.isArray(m.t) ? m.t : [];
    const pts = t.map((x, i) => ({ t: String(x).slice(0, 16), v: num(Array.isArray(m.lmp) ? m.lmp[i] : null) })).filter((p) => p.v !== null);
    const at = String((V && V.event_at) || '').slice(0, 16) || null;
    const marks = (Array.isArray(m.marks) ? m.marks : []).filter((x) => x && x.t && String(x.t).slice(0, 16) !== at)
      .map((x) => ({ t: String(x.t).slice(0, 16), kind: x.kind, label: KIND[x.kind] || 'Mark' }));
    return { pts, at, marks, peak: at ? peakFrom(m, at) : null, before: at ? priceAt(m, at) : null, cap: CAP };
  }

  /* The AI explanation in short: two or three plain lines composed from the record's own figures
     (the price and its usual, the top families, how sure the record is). Nothing is added. */
  function brief(V, onto, mode) {
    const lines = [];
    const region = (V && V.grid_name) || 'The region';
    const u = usualPrice(onto, mode);
    const ot = manilaFromUtc(onto && onto.t);
    const peak = V ? peakFrom(V.market, String(V.event_at || '').slice(0, 16)) : null;
    if (u && u.at !== null) lines.push(`${region} price was ${peso(u.at)}/MWh at ${ot ? hhmm(ot) : 'the event'}, against a usual ${peso(u.usual)} for that hour.`);
    else if (peak) lines.push(`${region} price reached ${peso(peak.value)}/MWh at ${hhmm(peak.t)}${peak.value >= CAP ? ', the ₱32,000 offer cap' : ''}.`);
    const r = ranked(onto, mode).rows;
    if (r.length) lines.push(`${r[0].label} stood out most (${pctWords(r[0].pct, r[0].family).toLowerCase()})${r[1] ? `, then ${r[1].label.toLowerCase()} (${r[1].pct}%)` : ''}. Present, not proven causes.`);
    const s = (onto && onto.summary) || {};
    if (s.confidence) lines.push(`How sure the record is: ${s.confidence}.`);
    return lines;
  }

  /* "More detail: what is related, and why". The records behind the event, grouped by how each
     relates to it, every one with its evidence (source, time, when it was known) and a link to the
     record's own page where there is one: a notice opens on /notices, a unit the record codes opens
     on /plant/<code>. The ontology record carries no edge list, so the groups follow the record's
     own kinds: the trigger notice and its unit, supply lost, the operator's response, island links,
     power lines. Anything known after the as-of clock is left out and counted; a name that reveals
     technology is not shown (and not linked); a mention the record does not confirm is flagged
     "unclear name · not matched", never linked or counted; a missing figure reads "Not in the record". */
  const PLANT_CODE = /(?:C?F|[DGSWH]|HE|BIO)PPI?|BESS|HEP/i;
  const TECH_NAME = 'Name not shown (it names a technology)';
  const nameOf = (x) => (!x ? NOT : (FUEL.test(String(x)) || PLANT_CODE.test(String(x)) ? TECH_NAME : String(x)));
  const CODE = /^[0-9]{2}[A-Z0-9]+_[A-Z0-9]+$/;
  const OUT_KIND = { scheduled_outage: 'Scheduled out', mention_tripped: 'Tripped', mention_derated: 'Running below capacity',
    mention_returned: 'Back in service' };
  const LINE = /\b\d+\s*kV\b|\bline\b|\bSS\b|\bsubstation\b|\btransformer\b|\bTR\d\b/i;
  /* Manila time to the second ('2026-09-21T13:39:37'), for tying a mention to its notice. */
  const manilaSec = (s) => {
    if (!s) return null;
    const d = new Date(String(s).trim().replace(' ', 'T').replace(/(Z|[+-]\d\d:\d\d)?$/, (m) => m || 'Z'));
    return Number.isNaN(d.getTime()) ? null : new Date(d.getTime() + MANILA_MS).toISOString().slice(0, 19);
  };
  const knownAt = (f) => manilaFromUtc(f && (f.known_by_utc || f.assumed_known_by_utc));
  const knownWord = (f) => (f.known_by_utc ? 'known' : f.assumed_known_by_utc ? 'assumed known' : 'known-by time not recorded');
  const mw = (v) => (num(v) === null ? null : `${Number(num(v).toFixed(2)).toLocaleString('en-US')} MW`);
  const noticeHref = (id, t) => `/notices?at=${encodeURIComponent(String(t).slice(0, 16))}#adv-${encodeURIComponent(id)}`;
  const isoMin = (t) => String(t || '').replace(' ', 'T').slice(0, 16);

  /* The event's own unit and site, only as the event record states them: its `site` field, or the
     unit code in the record's "Unit" line (e.g. "08PEDC_U02 · PEDC"). Never guessed from a name. */
  const SITE = /^[0-9]{2}[A-Z0-9]+$/;
  function eventSite(V) {
    const kv = V && V.assumption && Array.isArray(V.assumption.kv) ? V.assumption.kv : [];
    const line = kv.find((r) => Array.isArray(r) && /^unit$/i.test(String(r[0] || '')));
    const unit = line ? String(line[1] || '').trim().split(/[\s·]+/)[0] : '';
    const code = CODE.test(unit) ? unit : null;
    const own = V && typeof V.site === 'string' && SITE.test(V.site.trim()) ? V.site.trim() : null;
    const site = own || (code ? code.split('_')[0] : null);
    if (!site || nameOf(site) === TECH_NAME || (code && code.split('_')[0] !== site)) return null;
    return { site, unit: code };
  }

  function moreDetail(V, onto, mode, asOf) {
    const m = (((onto || {}).modes || {})[mode]) || null;
    const facts = m && Array.isArray(m.facts) ? m.facts.filter(Boolean) : [];
    const late = (t) => !!(asOf && t && String(t).slice(0, 16) > asOf);
    const later = { facts: 0, notices: 0, unclear: 0 };
    const live = facts.filter((f) => { if (late(knownAt(f))) { later.facts += 1; return false; } return true; });
    const region = (V && V.grid_name) || 'The region';
    const trigger = V && V.advisory && V.advisory.id ? String(V.advisory.id) : null;

    /* Every operator notice of the event, up to the clock. */
    const list = (V && Array.isArray(V.timeline) ? V.timeline : []).filter((x) => x && x.t && x.src && x.src !== 'WESM RTD');
    const a = V && V.advisory;
    if (a && a.t && a.id && !list.some((x) => x.src === a.id)) list.push({ t: a.t, kind: 'notice', text: noticeBody(a.text), src: a.id });
    const notices = list.filter((x) => { if (late(x.t)) { later.notices += 1; return false; } return true; })
      .sort((x, y) => (x.t < y.t ? -1 : 1)).map((x) => {
        const raw = String(x.text || '');
        const held = heldBack(V, x.src);
        /* The timeline line can be shorter than the notice; the trigger's full text says whether it was planned. */
        const full = a && a.text && String(x.src) === String(a.id) ? `${raw} ${a.text}` : raw;
        const st = /\bat\s+([01]\d|2[0-3])([0-5]\d)H\b/i.exec(raw);
        const lag = st ? minutes(`${String(x.t).slice(0, 10)}T${st[1]}:${st[2]}`, x.t) : null;
        return {
          id: String(x.src), t: String(x.t), kind: x.kind || 'notice', title: KIND[x.kind] || 'Notice',
          text: held ? heldText(x.src, held) : opText(raw),
          scheduled: /\bunplanned\b|\bforced\b/i.test(full) ? 'Not scheduled: the notice says unplanned'
            : /\b(planned|scheduled)\b/i.test(full) ? 'Scheduled: the notice says so' : 'Scheduled or not: Not in the record',
          lag: lag !== null && lag >= 0 && lag < 24 * 60 ? `Posted ${lag} min after the time it states (${st[1]}:${st[2]})` : 'Lag: Not in the record',
        };
      });
    const bySec = new Map(notices.map((n) => [String(n.t).slice(0, 19), n]));
    const noticeRow = (n, rel) => ({
      rel, title: `${n.title} · notice ${n.id}`, text: n.text, href: noticeHref(n.id, n.t), flag: null,
      evidence: [`NGCP notice ${n.id}`, `posted ${hhmm(n.t)}`, n.scheduled, n.lag],
    });

    const groups = { trigger: [], supply: [], response: [], links: [], lines: [], unclear: [] };
    if (trigger) {
      const n = notices.find((x) => x.id === trigger);
      if (n) groups.trigger.push(noticeRow(n, 'Trigger notice'));
    }
    notices.filter((n) => n.id !== trigger).forEach((n) => {
      if (n.kind === 'trip' && n.t > String((V && V.event_at) || '')) groups.supply.push(noticeRow(n, 'Notice of more supply lost'));
      else groups.response.push(noticeRow(n, n.kind === 'online' ? 'Supply back' : 'Operator response'));
    });

    /* Units and lines in the outage records: one row per name, kind and start; repeated schedule
       rows are folded. A mention is tied to the notice posted at the same second. */
    const seen = new Set();
    live.filter((f) => f.family === 'O' && OUT_KIND[f.predicate]).forEach((f) => {
      const sched = f.predicate === 'scheduled_outage';
      const raw = sched ? f.subject_label : f.value_text;
      const key = [f.predicate, raw, f.valid_from_utc].join('|');
      if (seen.has(key)) return;
      seen.add(key);
      const name = nameOf(raw);
      const from = manilaFromUtc(f.valid_from_utc);
      const k = knownAt(f);
      const via = !sched ? bySec.get(manilaSec(f.known_by_utc) || '') : null;
      const confirmed = sched || f.match_confidence === 'confirmed';
      const isLine = !sched && LINE.test(String(raw || ''));
      /* A link only when the record codes the unit: the schedule row's code, or a matched mention
         whose own text is a unit code. */
      const code = (sched || confirmed) && CODE.test(String(raw || '')) && name !== TECH_NAME ? String(raw) : null;
      const row = {
        rel: sched ? 'Already out on the outage schedule' : `${OUT_KIND[f.predicate]}${isLine ? ' (power line or substation)' : ''}`,
        title: `${name}${mw(f.value_num) ? ' · ' + mw(f.value_num) : ''}`,
        text: sched ? `Out${mw(f.value_num) ? ' ' + mw(f.value_num) : ''} from ${from ? when(from) : NOT}` : `${OUT_KIND[f.predicate]} from ${from ? when(from) : NOT}`,
        href: code ? '/plant/' + encodeURIComponent(code.split('_')[0]) : null,
        flag: !confirmed && !isLine ? 'Unclear name · not matched: shown, not linked or counted' : null,
        evidence: [sched ? 'Outage schedule' : (via ? `Operator notice ${via.id}` : 'Operator notice'),
          (f.source_table ? plainSrc(f.source_table) : NOT), k ? `${knownWord(f)} ${when(k)}` : 'Known: Not in the record',
          code ? `Unit code in the record: ${code} (site ${code.split('_')[0]})` : sched ? null : (confirmed ? 'Matched to a plant, no unit code in the record: no page to open' : null)].filter(Boolean),
      };
      if (!sched && via && via.id === trigger && f.predicate === 'mention_tripped') {
        row.rel = 'Unit named in the trigger';
        const es = !row.href && confirmed ? eventSite(V) : null;
        if (es) {
          row.href = '/plant/' + encodeURIComponent(es.site);
          row.evidence = row.evidence.filter((x) => !/^Matched to a plant/.test(x));
          row.evidence.push(`Site ${es.site} from the event record${es.unit ? ` (unit ${es.unit})` : ''}`);
          const q1 = V && V.judgment && Array.isArray(V.judgment.questions) ? V.judgment.questions.find((q) => q && q.id === 'q1') : null;
          if (q1 && es.unit && q1.modal === es.unit && Array.isArray(q1.agree)) row.evidence.push(`AI reading names ${es.unit} (${q1.agree.filter(Boolean).length} of ${q1.agree.length} phrasings agree)`);
        }
        groups.trigger.push(row);
      }
      else if (isLine) groups.lines.push(row);
      else if (f.predicate === 'mention_returned') groups.response.push(row);
      else groups.supply.push(row);
    });

    (m && Array.isArray(m.unconfirmed) ? m.unconfirmed : []).forEach((u) => {
      if (!u) return;
      if (late(manilaFromUtc(u.known_by_utc))) { later.unclear += 1; return; }
      const k = manilaFromUtc(u.known_by_utc);
      groups.unclear.push({ rel: OUT_KIND[u.kind] || 'Mention', title: nameOf(u.plant_text || u.object_label || u.subject_label || u.value_text),
        text: u.reason ? String(u.reason) : 'Reason: Not in the record', href: null,
        flag: 'Unclear name · not matched: not linked and not counted',
        evidence: ['Operator notice', k ? `known ${when(k)}` : 'Known: Not in the record'] });
    });

    /* Island links: flow and congestion flag per link, at the interval the record carries. */
    const links = new Map();
    live.filter((f) => f.predicate === 'hvdc_flow_mw' || f.predicate === 'hvdc_congested').forEach((f) => {
      const key = String(f.subject_label || NOT);
      const l = links.get(key) || { name: nameOf(key), at: manilaFromUtc(f.valid_from_utc), flow: NOT, flag: NOT,
        source: (f.source_table ? plainSrc(f.source_table) : NOT), known: f };
      if (f.predicate === 'hvdc_flow_mw' && num(f.value_num) !== null) l.flow = `${mw(f.value_num)} scheduled${num(f.value_num) < 0 ? ' (negative in the record: the reverse direction)' : ''}`;
      if (f.predicate === 'hvdc_congested') l.flag = /^(y|yes|true)$/i.test(String(f.value_text)) ? 'raised' : /^(n|no|false)$/i.test(String(f.value_text)) ? 'not raised' : NOT;
      links.set(key, l);
    });
    links.forEach((l) => groups.links.push({ rel: 'Island link', title: l.name, text: `Flow ${l.flow} · Congestion flag: ${l.flag} · Limit: ${NOT}`,
      href: null, flag: null, evidence: [l.source, l.at ? `interval ${when(l.at)}` : 'Interval: Not in the record', `${knownWord(l.known)} ${when(knownAt(l.known)) }`] }));
    const fact = (p) => live.find((x) => x.predicate === p) || null;
    [['import_mw', `${region} imports`], ['export_mw', `${region} exports`]].forEach(([p, label]) => {
      const f = fact(p);
      if (f && num(f.value_num) !== null) groups.links.push({ rel: 'Island links, total', title: `${label} · ${mw(f.value_num)}`, text: 'Over all island links at the interval',
        href: null, flag: null, evidence: [(f.source_table ? plainSrc(f.source_table) : NOT), `interval ${when(manilaFromUtc(f.valid_from_utc))}`] });
    });

    /* Power lines: the record's congestion count; which lines it does not carry. */
    const nc = fact('n_nodes_congested');
    const raised = Array.from(links.values()).filter((l) => l.flag === 'raised').map((l) => l.name);
    groups.lines.unshift({ rel: 'Congestion at the interval',
      title: nc && num(nc.value_num) !== null ? `${num(nc.value_num)} node${num(nc.value_num) === 1 ? '' : 's'} flagged congested in ${region}` : `Congested nodes: ${NOT}`,
      text: `${raised.length ? `Island link flagged congested: ${raised.join(', ')}` : links.size ? 'No island link flagged congested' : 'Island links: Not in the record'}. Which lines: ${NOT}.`,
      href: null, flag: null,
      evidence: nc ? [(nc.source_table ? plainSrc(nc.source_table) : NOT), `interval ${when(manilaFromUtc(nc.valid_from_utc))}`] : [NOT] });

    const TITLES = [['trigger', 'Trigger'], ['supply', 'Supply lost'], ['response', 'Operator response'],
      ['links', 'Imports and island links'], ['lines', 'Power lines'], ['unclear', 'Unclear names (not matched, not counted)']];
    const out = TITLES.map(([key, title]) => ({ key, title, rows: groups[key] })).filter((g) => g.rows.length || g.key === 'trigger' || g.key === 'supply');

    /* AI second opinion: the saved reading of the trigger notice, phrased four ways. */
    const j = V && V.judgment;
    const e = explanation(onto, V);
    let second = null;
    if (j) {
      const qs = Array.isArray(j.questions) ? j.questions : [];
      const split = qs.filter((q) => Array.isArray(q.agree) && q.agree.some((x) => !x));
      const flip = /max flip rate ([\d.]+)/.exec(String(j.receipt || ''));
      second = {
        known: e.cutoff ? `Using only what was known at ${when(e.cutoff)} Manila`
          : (reader(V) && reader(V).cutoff ? reader(V).cutoff.text : `When it was read: ${NOT}`),
        label: j.label ? String(j.label) : NOT,
        rule: j.rule ? withheld(j.rule) : NOT,
        answers: qs.map((q) => ({ q: withheld(q.plain || q.label || NOT), a: nameOf(q.modal), key: !!q.key,
          agree: Array.isArray(q.agree) ? `${q.agree.filter(Boolean).length} of ${q.agree.length} phrasings agree` : NOT })),
        steady: !qs.length ? `Agreement: ${NOT}` : split.length ? `Phrasings disagreed on ${split.length} of ${qs.length} questions` : `All phrasings agreed on all ${qs.length} questions${flip ? ` (max flip rate ${flip[1]})` : ''}`,
        unstable: !!j.unstable, holds: e.holds, disagreement: e.disagreement.join(' '), by: j.by ? String(j.by) : NOT,
      };
    }
    return { groups: out, notices, second, later };
  }

  /* Price alerts beside the event, from the alert inbox at the clock: an alert the record ties to
     this event is "Linked by the record"; another in the same region whose window overlaps the
     event's is "Around the same time (not linked)". Other regions are left out. */
  function relatedAlerts(V, inbox, asOf) {
    const groups = inbox && Array.isArray(inbox.groups) ? inbox.groups : [];
    const start = String((V && V.event_at) || '').slice(0, 16);
    const ts = (V && Array.isArray(V.timeline) ? V.timeline : []).map((x) => x && String(x.t || '').slice(0, 16)).filter(Boolean);
    const end = [start].concat(ts).filter((t) => !asOf || t <= asOf).sort().pop() || start;
    const out = [];
    // a recorded event's page, or an alert's own page when no event explains it (/alert/<key>)
    const safe = (h) => (/^\/event\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$|^\/alert\/[0-9a-f]{24}$/.test(String(h || '')) ? String(h) : null);
    groups.forEach((g) => (Array.isArray(g && g.alerts) ? g.alerts : []).forEach((x) => {
      if (!x || !V || x.region !== V.grid) return;
      const linked = !!(x.cause && x.cause.id === V.id);
      const first = String(x.first || '').slice(0, 16), last = String(x.last || '').slice(0, 16);
      if (asOf && first > asOf) return;
      if (!linked && !(first && last && first <= end && last >= start)) return;
      /* An alert whose page is this event links to the alert in the inbox instead (no self-link). */
      const self = !!(V.id && safe(x.href) === `/event/${V.id}`);
      const inboxHref = /^[0-9a-f]{8,64}$/.test(String(x.key || '')) ? `/alerts?alert=${x.key}` : null;
      out.push({ rel: self ? 'This event · price alert, linked by the record' : linked ? 'Price alert, linked by the record' : 'Around the same time (not linked)',
        title: `${x.direction === 'collapse' ? 'Price collapse' : 'Price spike'}${num(x.price_php_mwh) !== null ? ' · ' + peso(x.price_php_mwh) + '/MWh' : ''}${x.severity ? ' · ' + x.severity : ''}`,
        text: x.main_driver ? opText(x.main_driver) : `Cause: ${NOT}`,
        href: self ? inboxHref : safe(x.href), flag: null, linked,
        evidence: [self ? (inboxHref ? 'Opens the alert in the inbox (this page is its event)' : 'This event: no other page to open') : null, 'Alert inbox (replay)', `${hhmm(first)} to ${hhmm(last)}`, x.threshold_text ? String(x.threshold_text) : null].filter(Boolean) });
    }));
    return out;
  }

  /* "What stood out, ranked": one row per family, as on the canvas. The rank, score and status are
     the record's own (the page ranks nothing): a scored family reads its percent against the same
     hour on the last 28 days (fuel against its own monthly history) as a state, "Unusual" at 80% or
     more and "A bit high" at 55% or more; price is context and rules are listed, never scored; a
     family the record leaves without a score is "No data". Each row opens its detail: the signals
     with their value against the 28-day median, the notes, the facts with when each was known, the
     facts held back and the sources. */
  const IND = { demand_mw: 'Demand', import_share: 'Import share', hvdc_links_congested: 'Island links congested',
    reserve_shortfall_mw: 'Reserve shortfall', scheduled_outage_mw: 'Capacity scheduled out', linked_derated_mw: 'Linked capacity running below',
    price_capped_median: 'Capped median price', cap_bound: 'Price cap bound', admin_priced: 'Administered price',
    price_mitigated: 'Price mitigated', price_substituted: 'Price substituted', secondary_cap: 'Secondary cap',
    congested_elements: 'Congested power-line elements at the region\'s stations', congestion_overload_mw: 'Congestion overload',
    'fuel cost baseline': 'Fuel cost baseline' };
  const indName = (k) => IND[k] || String(k || 'Signal').replace(/_/g, ' ');
  const val = (v, unit) => {
    const n = num(v);
    if (n === null) return null;
    if (unit === 'fraction') return `${(n * 100).toFixed(1)}%`;
    if (unit === 'PHP/MWh') return peso(n);
    if (unit === 'links') return `${n} link${n === 1 ? '' : 's'}`;
    return `${Math.round(n).toLocaleString('en-US')}${unit && unit !== 'flag' && unit !== 'count' ? ' ' + unit : ''}`;
  };
  const stateOf = (p) => (p === null ? ['No data', 'none'] : p >= 80 ? ['Unusual', 'warn'] : p >= 55 ? ['A bit high', 'amber']
    : p > 45 ? ['About usual', 'plain'] : ['Lower than usual', 'low']);
  const vsWords = (p, fam) => {
    const base = fam === 'F' ? 'its own monthly history' : 'the same hour on the last 28 days';
    return p >= 55 ? `higher than ${p}% of ${base}` : p <= 45 ? `lower than usual: only ${p}% of ${base} were lower` : `about usual (${p}%, in the middle of ${base})`;
  };
  const FAM_ORDER = ['P', 'O', 'S', 'D', 'F', 'Rules'];
  const FAM_NOTE = { O: 'The score counts planned outages only. A sudden trip is not in the outage schedule; it shows in the operator notices.',
    F: 'Fuel is compared with its own monthly history. Fuel values are not shown.',
    P: 'The price is context: shown for reference and never ranked.',
    Rules: 'Pricing flags at the interval are listed as set or not set and never scored. See Price rules.' };
  function standout(onto, mode, asOf) {
    const rows = ((onto || {}).drivers || {})[mode];
    const m = (((onto || {}).modes || {})[mode]) || {};
    const all = Array.isArray(rows) ? rows.filter(Boolean) : [];
    const facts = Array.isArray(m.facts) ? m.facts.filter(Boolean) : [];
    const late = (t) => !!(asOf && t && String(t).slice(0, 16) > asOf);
    const out = FAM_ORDER.map((fam) => {
      const mine = all.filter((r) => r.family === fam);
      const scored = mine.filter((r) => r.status === 'scored' && num(r.rank) !== null && num(r.family_score) !== null);
      const rank = scored.length ? num(scored[0].rank) : null;
      const pct = scored.length ? Math.round(num(scored[0].family_score) * 100) : null;
      const sigs = mine.filter((r) => r.family !== 'Rules');
      /* The line: the strongest signal with a value, against its usual. */
      const lead = sigs.filter((r) => val(r.value_at_t, r.unit) !== null)
        .sort((a, b) => (num(b.indicator_score) || 0) - (num(a.indicator_score) || 0))[0] || null;
      let text = NOT;
      if (fam === 'Rules') {
        const set = mine.filter((r) => r.status === 'present').map((r) => indName(r.indicator));
        const not = mine.filter((r) => r.status === 'absent').length;
        text = mine.length ? `${set.length ? `${set.join(', ')} set` : 'No rule flag set'}${not ? `; ${not} other flag${not === 1 ? '' : 's'} not set` : ''}. See Price rules.` : `No rule flag in the record. See Price rules.`;
      } else if (fam === 'F') {
        text = mine.length ? (pct !== null ? `Fuel cost baseline ${vsWords(pct, 'F')}. Values not shown.` : 'Fuel context in the record; not compared for this hour.') : NOT;
      } else if (lead) {
        text = `${fam === 'D' || fam === 'P' ? '' : indName(lead.indicator) + ' '}${val(lead.value_at_t, lead.unit)}${val(lead.baseline_median, lead.unit) ? ` vs about ${val(lead.baseline_median, lead.unit)} usual` : ''}`;
      }
      if (fam === 'O') {
        const trips = facts.filter((f) => f.predicate === 'mention_tripped' && f.match_confidence === 'confirmed' && !late(manilaFromUtc(f.known_by_utc || f.assumed_known_by_utc)));
        if (trips.length) text = `${text === NOT ? '' : text + '; '}${trips.length} unit${trips.length === 1 ? '' : 's'} tripped in the operator notices`;
      }
      const ctx = fam === 'P' && mine.some((r) => r.status === 'context');
      const [state, cls] = ctx ? ['Context', 'ctx'] : fam === 'Rules' ? [mine.length ? 'Listed, not scored' : 'No data', 'none'] : stateOf(pct);
      const barPct = ctx && lead && num(lead.indicator_score) !== null ? Math.round(num(lead.indicator_score) * 100) : pct;

      /* The detail under the row. */
      const signals = sigs.filter((r) => r.indicator).map((r) => {
        const v = val(r.value_at_t, r.unit), b = val(r.baseline_median, r.unit);
        const p = num(r.indicator_score) !== null ? Math.round(num(r.indicator_score) * 100) : null;
        return `${indName(r.indicator)}: ${fam === 'F' ? 'fuel context (monthly series, values not shown)' : v || NOT}${b && v && fam !== 'F' ? ` against a 28-day median of ${b}` : ''}${p !== null ? `, ${vsWords(p, fam)}` : ''}${r.status === 'no data' ? ' (No data at this cutoff)' : ''}.`;
      });
      const flags = fam === 'Rules' ? mine.map((r) => `${indName(r.indicator)}: ${r.status === 'present' ? 'set' : r.status === 'absent' ? 'not set' : r.status === 'flag count' ? `${val(r.value_at_t, 'count') || NOT} (not linked to a region, not counted)` : NOT}`) : [];
      let laterFacts = 0;
      const fFacts = facts.filter((f) => f.family === fam).filter((f) => {
        const k = manilaFromUtc(f.known_by_utc || f.assumed_known_by_utc);
        if (late(k)) { laterFacts += 1; return false; } return true;
      }).map((f) => {
        const k = manilaFromUtc(f.known_by_utc || f.assumed_known_by_utc);
        const v = fam === 'F' ? 'value not shown' : (val(f.value_num, f.unit) || (f.value_text ? nameOf(f.value_text) : NOT));
        return `${nameOf(f.subject_label)} · ${indName(f.predicate)}: ${v} · ${f.known_by_utc ? 'known' : 'assumed known'} ${k ? when(k) : NOT}${f.availability_at_cutoff === 'after_cutoff' ? ' (after the cutoff)' : ''}`;
      });
      const held = (Array.isArray(m.withheld) ? m.withheld : []).filter((w) => w && w.family === fam)
        .map((w) => `${num(w.n) !== null ? num(w.n) : 1} fact${num(w.n) === 1 ? '' : 's'} held back: ${w.reason || 'reason not recorded'}`);
      if (laterFacts) held.push(`${laterFacts} fact${laterFacts === 1 ? '' : 's'} known after the as-of clock (${hhmm(asOf)}), not shown`);
      const unclear = fam === 'O' ? (Array.isArray(m.unconfirmed) ? m.unconfirmed : []).filter((u) => u && !late(manilaFromUtc(u.known_by_utc)))
        .map((u) => `${nameOf(u.plant_text || u.object_label)}: ${u.reason || 'reason not recorded'}`) : [];
      const sources = Array.from(new Set(mine.map((r) => r.source_table).concat(facts.filter((f) => f.family === fam).map((f) => f.source_table)).filter(Boolean).map(plainSrc))).sort();
      return { family: fam, name: FAMILY[fam], rank: rank === null ? '–' : String(rank), sort: rank, pct, bar: barPct === null ? 0 : Math.max(0, Math.min(100, barPct)),
        state, cls, text,
        detail: { signals, flags, note: FAM_NOTE[fam] || null, facts: fFacts, held, unclear, sources } };
    });
    out.sort((a, b) => (a.sort === null) - (b.sort === null) || (a.sort || 0) - (b.sort || 0) || FAM_ORDER.indexOf(a.family) - FAM_ORDER.indexOf(b.family));
    return { rows: out, cutoff: manilaFromUtc(m.cutoff_utc), any: all.length > 0 };
  }

  /* RAG-5: "What the system read". The event view's optional `retrieval` block (written by the
     RAG-4 recorder, copied byte for byte by the bake; its shape is the retrieval-block contract in
     docs/work/retrieval-2026-10-18/intent.md) names, per cutoff state, the passages the retrieval
     ranked closest to the case question. The card repeats the record: every figure is a field of
     the block (rank, distance, counts, model, dimension, bytes, digests), never computed here;
     the distance is only rounded to six places, the contract's presentation rule. A view
     without the block has no card. The states follow the page's view: "Hindsight" reads the
     hindsight state, the two known-then views read the known-then state (the CORP-5 cutoff),
     and the card's own tabs switch the card alone. */
  const RT_NO = 'No data';
  const RT_WHY = { later_availability: 'first available after this cutoff', availability_unknown: 'first availability unknown',
    no_embedding: 'no embedding' };
  const RT_EXCERPT_MAX = 200;
  const RT_MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const rtText = (v) => (v === null || v === undefined || String(v).trim() === '' ? null : String(v));
  const rtInstant = (s) => {
    const t = rtText(s);
    if (!t) return null;
    const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(t) ? t + 'T00:00:00+08:00' : t.replace(' ', 'T').replace(/(Z|[+-]\d\d:\d\d)?$/, (m) => m || 'Z'));
    return Number.isNaN(d.getTime()) ? null : d.getTime();
  };
  /* A stated date stays a date; an instant reads in Manila time. */
  function rtWhen(s) {
    const t = rtText(s);
    if (!t) return RT_NO;
    const date = (x) => `${Number(x.slice(8, 10))} ${RT_MONTH[Number(x.slice(5, 7)) - 1] || x.slice(5, 7)} ${x.slice(0, 4)}`;
    if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return `${date(t)} (date only)`;
    const m = manilaFromUtc(t);
    return m ? `${date(m.slice(0, 10))} ${m.slice(11, 16)} Manila` : t;
  }
  const rtStateFor = (mode) => (mode === 'hindsight' ? 'hindsight' : 'known-then');
  function retrieval(V, mode, pick) {
    const R = V && V.retrieval;
    if (!R || typeof R !== 'object' || !Array.isArray(R.states)) return null;
    const states = R.states.filter((s) => s && typeof s === 'object');
    if (!states.length) return null;
    const want = pick || rtStateFor(mode);
    const cur = states.find((s) => s.id === want) || states[0];
    const cutMs = rtInstant(cur.cutoff);
    const rows = [], late = [];
    (Array.isArray(cur.ranked) ? cur.ranked : []).forEach((r) => {
      if (!r || typeof r !== 'object') return;
      const issuer = rtText(r.issuer), label = rtText(r.label);
      const identity = [issuer || RT_NO, label ? withheld(label) : RT_NO].concat(rtText(r.passage_id) ? [`passage ${r.passage_id}`] : []).join(' · ');
      /* The store withholds a passage first available after the cutoff; a row the block ranks
         anyway is named by its record and not drawn, never shown as known on that day. */
      const from = rtInstant(r.available_from);
      if (cutMs !== null && from !== null && from > cutMs) { late.push(identity); return; }
      const ex = rtText(r.excerpt);
      const d = num(r.distance);
      rows.push({
        rank: num(r.rank) === null ? RT_NO : String(num(r.rank)),
        issuer: issuer || RT_NO,
        label: label ? withheld(label) : RT_NO,
        available: rtWhen(r.available_from),
        basis: rtText(r.basis) || RT_NO,
        distance: d === null ? RT_NO : d.toFixed(6),
        excerpt: ex && ex.length <= RT_EXCERPT_MAX ? opText(ex) : null,
        identity,
        cited: r.cited === true,
      });
    });
    const w = cur.withheld && typeof cur.withheld === 'object' ? cur.withheld : null;
    const held = w ? Object.keys(w).map((k) => ({ reason: k, why: RT_WHY[k] || k.replace(/_/g, ' '), n: num(w[k]) === null ? RT_NO : String(num(w[k])) })) : null;
    const rc = R.receipt && typeof R.receipt === 'object' ? R.receipt : {};
    const bytes = num(rc.bytes_billed);
    const receipt = [
      ['Embedding model', rtText(rc.embedding_model) || RT_NO],
      ['Dimension', num(rc.dimension) === null ? RT_NO : String(num(rc.dimension))],
      ['Backend', rtText(rc.backend) || RT_NO],
      ['Agreement', rtText(rc.agreement) || RT_NO],
      ['Bytes billed', bytes === null ? RT_NO : bytes.toLocaleString('en-US')],
      ['Receipt', rtText(cur.receipt_digest) || RT_NO],
      ['Run record', rtText(rc.run) || RT_NO],
    ];
    const j = R.judgment && typeof R.judgment === 'object' ? R.judgment : null;
    let judgment;
    if (!j || typeof j.used !== 'boolean') judgment = { used: null, text: `Whether a judgment used this retrieval: ${RT_NO}.` };
    else if (j.used) {
      const ranks = Array.isArray(j.cited_ranks) ? j.cited_ranks.map(num).filter((x) => x !== null).map(String) : [];
      judgment = { used: true, text: `The recorded judgment used this retrieval${ranks.length ? ` and cited rank${ranks.length === 1 ? '' : 's'} ${ranks.join(', ')}` : '; the ranks it cited: ' + RT_NO}.`,
        receipt: rtText(j.receipt_digest) || RT_NO };
    } else {
      const n = num(j.attempts);
      judgment = { used: false, text: `No judgment used this retrieval${n !== null ? ` (${n} attempt${n === 1 ? '' : 's'} recorded)` : ''}.`, receipt: rtText(j.receipt_digest) };
    }
    return {
      question: rtText(R.question) || RT_NO,
      tabs: states.map((s) => ({ id: String(s.id || ''), label: `${rtText(s.label) || RT_NO} · ${rtWhen(s.cutoff)}`, on: s === cur })),
      state: { id: String(cur.id || ''), label: rtText(cur.label) || RT_NO, cutoff: rtWhen(cur.cutoff) },
      rows, late, held, receipt, judgment,
    };
  }

  /* DM-5 (review of PERF-6): may an inbox answer read at `readAt` be drawn at the clock `clock`?
     Only when it was read at or before the clock: an answer read at a later clock carries the
     alerts' later ends, peaks and severities. An unknown clock draws whatever was read. */
  function inboxFits(readAt, clock) {
    if (!clock) return true;
    return typeof readAt === 'string' && readAt <= clock;
  }

  /* PP-B2: the anchor's key figure. The price at the trigger, the highest price after it and the
     minutes between, all read from the recorded five-minute series; null without a series. */
  function keyFigure(V) {
    const at = String((V && V.event_at) || '').slice(0, 16);
    const m = V && V.market;
    const before = at ? priceAt(m, at) : null;
    const peak = at ? peakFrom(m, at) : null;
    if (!before && !peak) return null;
    const lag = peak ? minutes(at, peak.t) : null;
    return {
      before: before ? { value: before.value, t: before.t, text: peso(before.value) } : null,
      peak: peak ? { value: peak.value, t: peak.t, text: peso(peak.value), cap: peak.value >= CAP } : null,
      lag, trigger: at || null,
      same: !!(before && peak && before.value === peak.value),
      ratio: before && peak && before.value > 0 && peak.value !== before.value ? `${(peak.value / before.value).toFixed(1)}×` : null,
    };
  }

  /* PP-B2: the AI reader's record, in the decision region: the label, the cutoff it read at, the
     run record and each answer, all from the baked judgment. The cutoff is the trip pair's
     "after" instant when the view carries one, else the trigger notice's posting time (the
     information cutoff the adapter files a decision at). Nothing is added. */
  function reader(V) {
    const j = V && V.judgment;
    if (!j) return null;
    const pair = (Array.isArray(V.cutoffs) ? V.cutoffs : []).find((c) => c && c.advisory === (V.advisory && V.advisory.id) && c.after)
      || (Array.isArray(V.cutoffs) ? V.cutoffs : []).find((c) => c && c.pair === 'trip' && c.after) || null;
    const posted = V.advisory && V.advisory.t ? String(V.advisory.t).replace(' ', 'T') : null;
    const cutoff = pair
      ? { t: String(pair.after), text: `It read only what was known at ${String(pair.after).slice(11, 19)}, one second after the trigger notice.` }
      : posted ? { t: posted, text: `It read only what was known at ${hhmm(posted)}, when the trigger notice was posted.` } : null;
    const qs = Array.isArray(j.questions) ? j.questions : [];
    return {
      label: j.label ? String(j.label) : null,
      tone: j.label === 'challenges' ? 'warning' : j.label === 'supports' ? 'ok' : '',
      by: j.by ? String(j.by) : null,
      cutoff,
      receipt: j.receipt ? plainReceipt(j.receipt) : null,
      unstable: j.unstable === true,
      answers: qs.map((q) => {
        const agree = Array.isArray(q.agree) ? q.agree : [];
        return { q: withheld(q.plain || q.label || NOT), short: withheld(q.label || q.plain || NOT), a: nameOf(q.modal), key: !!q.key,
          agree: agree.filter(Boolean).length, of: agree.length, pips: agree.map((x) => x === true) };
      }),
    };
  }

  /* PP-B2: what the record does not carry, said once on one line instead of a tile each. */
  function unknowns(V, onto, mode, asOf) {
    const out = [];
    const s = (onto && onto.summary) || {};
    if (!s.severity) out.push('severity');
    if (!rulesFlag(onto, V).known) out.push('pricing flags');
    glance(V, onto, mode, asOf).forEach((t) => {
      if (t.value !== NOT) return;
      const word = { trigger: 'price at the trigger', peak: 'price after the trigger', usual: 'usual price for this hour',
        lag: 'time to the highest price', steps: 'notice steps', top: 'ranked drivers' }[t.key];
      if (word && out.indexOf(word) < 0) out.push(word);
    });
    return out;
  }

  /* The reserve shortfall beside the price, from the same five-minute series. */
  function reserveSeries(V) {
    const m = (V && V.market) || {};
    const t = Array.isArray(m.t) ? m.t : [];
    const pts = t.map((x, i) => ({ t: String(x).slice(0, 16), v: num(Array.isArray(m.short) ? m.short[i] : null) })).filter((p) => p.v !== null);
    const peak = pts.reduce((b, p) => (!b || p.v > b.v ? p : b), null);
    return { pts, peak: peak && peak.v > 0 ? peak : null };
  }

  const api = { inboxFits, lead, rulesFlag, trail, upTo, explanation, audit, views, manilaFromUtc, noticeBody, withheld, CAP,
    heldBack, ranked, usualPrice, glance, priceSeries, brief, moreDetail, relatedAlerts, standout, retrieval,
    keyFigure, reader, unknowns, reserveSeries };
  (typeof globalThis !== 'undefined' ? globalThis : window).GridEventDesk = api;
  if (typeof document === 'undefined') return;

  // ------------------------------------------------------------------ rendering
  const $ = (id) => document.getElementById(id);
  const node = (tag, cls, text, parent) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const shell = () => window.GNShell || null;
  const asOfNow = () => (shell() && shell().asOf ? shell().asOf() : null);
  const pill = (cls, text, parent) => node('span', 'gn-pill' + (cls ? ' ' + cls : ''), text, parent);
  const badge = (tone, text, parent) => node('span', 'gn-badge' + (tone ? ' gn-badge--' + tone : ''), text, parent);
  const kv = (parent, rows) => {
    const dl = node('dl', 'ed-kv', null, parent);
    rows.forEach(([k, v]) => { node('dt', null, k, dl); node('dd', v === 'No data' || v === 'Not available' ? 'ed-nodata' : null, v, dl); });
    return dl;
  };
  const link = (parent, cls, text, href, entity) => {
    const a = node('a', cls, text, parent);
    a.href = href;
    if (entity) a.setAttribute('data-entity', entity);
    return a;
  };
  const state = { mode: 'assumed', open: null, alertTicket: 0, readPick: null, decided: null, journal: null };
  api.renderRetrieval = (V) => renderRetrieval(V);

  /* The kind words used across the site, and the status tone each carries. */
  const TONE = { trip: 'alert', red: 'alert', yellow: 'warning', mld: 'warning', online: 'info', notice: 'info' };
  /* The site's kind badge (ui.js GNUI.badge): the same word and look everywhere. */
  const kindBadge = (kind, word, parent) => { const b = badge(TONE[kind] || '', word, parent); if (TONE[kind]) b.className += ' gn-sev'; return b; };
  const synthetic = (V) => /synthetic/i.test([V && V.title, V && V.source_label, (V && V.limits || [])[0], V && V.fixture_note].join(' '));

  /* Head: the breadcrumb's last item, the badges that say where the decision stands (the AI
     reader's proposal and the person's decision, apart), the synthetic label and the severity. */
  function renderPills(V, onto) {
    const crumb = $('ev-crumb');
    if (crumb && V && V.title) crumb.textContent = V.title;
    const host = $('ed-pills');
    if (!host) return;
    host.replaceChildren();
    const j = V && V.judgment;
    const ai = node('span', 'ev-status', null, host);
    node('span', 'gn-label', 'AI reader', ai);
    badge(j ? (j.label === 'challenges' ? 'warning' : j.label === 'supports' ? 'ok' : '') : '', j ? `Proposes: ${j.label}` : 'No reading recorded', ai);
    const you = node('span', 'ev-status', null, host);
    node('span', 'gn-label', 'You', you);
    const d = state.decided;
    badge(d ? 'ok' : '', d ? d.text : 'No decision on record', you).id = 'ev-status-you';
    const sev = onto && onto.summary && onto.summary.severity ? String(onto.summary.severity) : null;
    if (sev) badge(/high|critical|extreme/i.test(sev) ? 'alert' : /medium/i.test(sev) ? 'warning' : '', `Severity ${sev}`, host);
    if (synthetic(V)) badge('', 'Synthetic data', host).title = String((V.limits || [])[0] || V.fixture_note || 'Synthetic records');
  }

  /* The anchor: the trigger notice, the price move as the key figure, the other figures the record
     carries, and one line for everything it does not. */
  function renderHead(V, onto) {
    const l = lead(V);
    const host = $('ed-lead');
    if (host) {
      host.replaceChildren();
      const a = V && V.advisory;
      const held = a ? heldBack(V, a.id) : null;
      if (!a || !a.text) node('span', 'ed-nodata', 'No operator notice is on record for this event.', host);
      else {
        node('q', 'ed-quote', held ? heldText(a.id, held) : noticeBody(a.text), host);
        const src = node('span', 'ed-lead-src', null, host);
        src.appendChild(document.createTextNode(`${(V.source_label || 'NGCP')} notice `));
        link(src, 'mono', String(a.id), noticeHref(a.id, String(a.t).replace(' ', 'T')), `notice:${a.id}`);
        src.appendChild(document.createTextNode(` posted ${hhmm(String(a.t).replace(' ', 'T'))}`));
      }
      host.title = l.text;
    }
    const r = rulesFlag(onto, V);
    const flag = $('ed-rules');
    if (flag) {
      flag.replaceChildren();
      if (r.level !== 'none') badge(r.level === 'bad' ? 'alert' : r.level === 'warn' ? 'warning' : 'ok', r.headline, flag);
    }
    const tiles = $('ed-tiles');
    if (tiles) {
      tiles.replaceChildren();
      const dl = node('dl', 'ed-kv ed-rules-kv', null, tiles);
      r.items.forEach((it) => { node('dt', null, it.label, dl); node('dd', it.value === 'No data' ? 'ed-nodata' : 'mono', it.value === 'No data' ? 'Not in the record' : it.value, dl); });
    }
    const rulesTab = $('ev-tab-rules');
    if (rulesTab) rulesTab.hidden = !r.known;
  }

  function stat(parent, label, value, unit, meta, cls) {
    const s = node('div', 'gn-stat' + (cls ? ' ' + cls : ''), null, parent);
    node('span', 'gn-label', label, s);
    const v = node('span', 'gn-value' + (cls && /key/.test(cls) ? ' gn-value--lg' : ''), value, s);
    if (unit) node('span', 'gn-unit', unit, v);
    if (meta) node('span', 'gn-meta', meta, s);
    return s;
  }

  function renderStats(V, onto) {
    const host = $('ed-kpis');
    if (!host) return;
    const asOf = asOfNow();
    host.replaceChildren();
    const k = keyFigure(V);
    if (k && k.before && k.peak) {
      const s = node('div', 'gn-stat gn-stat--key ev-move', null, host);
      node('span', 'gn-label', k.same ? 'Price at the trigger' : 'Price move after the trigger', s);
      const v = node('span', 'gn-value gn-value--lg', null, s);
      if (!k.same) {
        node('span', 'ev-move-from', k.before.text, v);
        node('span', 'ev-move-arrow', ' → ', v).setAttribute('aria-hidden', 'true');
      }
      node('span', 'ev-move-to', k.peak.text, v);
      node('span', 'gn-unit', '/MWh', v);
      node('span', 'gn-meta', k.same
        ? `Already there at ${hhmm(k.before.t)}, before the trigger. No higher price after it.`
        : `${hhmm(k.before.t)} to ${hhmm(k.peak.t)}, highest ${k.lag} min after the trigger${k.ratio ? ` (${k.ratio})` : ''}.`, s);
      if (k.peak.cap) badge('warning', 'At the offer cap', s);
    } else if (k && k.peak) {
      stat(host, 'Highest after the trigger', k.peak.text, '/MWh', `First at ${hhmm(k.peak.t)}.`, 'gn-stat--key');
    }
    const tiles = glance(V, onto, state.mode, asOf);
    const t = (key) => tiles.find((x) => x.key === key);
    const usual = t('usual');
    if (usual && usual.value !== NOT) stat(host, 'Usual for this hour', usual.value, usual.unit, '28-day median at this hour');
    /* The view's own figures, as baked, except the price ones the key figure already states. */
    /* A baked figure names its interval in its label ("Import at 14:30"); under a clock on the
       event's day, one after the clock is not shown, as the timeline hides its later steps. */
    const clockNow = asOf || asOfNow();
    const eventDay = V && V.advisory && V.advisory.t ? String(V.advisory.t).slice(0, 10) : '';
    const afterClock = (f) => {
      const m = /\bat (\d\d:\d\d)\b/.exec(String(f.k || ''));
      if (!m || !clockNow || String(clockNow).slice(0, 10) !== eventDay) return false;
      return m[1] > String(clockNow).slice(11, 16);
    };
    (Array.isArray(V && V.figures) ? V.figures : []).filter((f) => f && f.v !== undefined && f.v !== null && f.v !== '' && !/price/i.test(String(f.k || '')) && !afterClock(f))
      .slice(0, 3).forEach((f) => stat(host, String(f.k), String(f.v), f.unit ? String(f.unit) : '', f.d ? String(f.d) : ''));
    const top = t('top');
    if (top && top.value !== NOT) stat(host, 'Stood out most', top.value, '', top.note.replace(/\. Evidence, not proof\.$/, ''));
    host.hidden = !host.children.length;
    const line = $('ed-unknowns');
    if (line) {
      const u = unknowns(V, onto, state.mode, asOf);
      line.textContent = u.length ? `Not on record: ${u.join(', ')}.` : '';
      line.hidden = !u.length;
    }
  }

  /* The ontology's three views as one segmented control. Choosing one redraws every view-bound
     section. Off the page without the record. */
  function renderView(V, onto) {
    const card = $('ed-view');
    const all = views(onto);
    if (document.body) document.body.classList.toggle('ed-has-view', !!(card && all.length));
    if (!card || !all.length) { if (card) card.hidden = true; return; }
    if (!all.some((v) => v.key === state.mode)) state.mode = all[0].key;
    const modes = $('ed-modes');
    modes.replaceChildren();
    all.forEach((v) => {
      const b = node('button', 'ed-mode', v.label, modes);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(v.key === state.mode));
      b.addEventListener('click', () => pickMode(V, onto, v.key));
    });
    const cur = all.find((v) => v.key === state.mode);
    $('ed-mode-line').textContent = cur.line;
    const hid = $('ed-hidden');
    hid.replaceChildren();
    if (cur.hidden) {
      node('span', 'ed-hidden-t', 'Held back:', hid);
      cur.byReason.forEach((h) => { const p = badge('', null, hid); node('b', 'mono', String(h.n), p); p.appendChild(document.createTextNode(' ' + h.why)); });
    }
    if (cur.unconfirmed) badge('warning', `${cur.unconfirmed} unclear name${cur.unconfirmed === 1 ? '' : 's'}, not counted`, hid);
    card.hidden = false;
  }
  function pickMode(V, onto, key) {
    state.mode = key;
    renderView(V, onto);
    renderStats(V, onto);
    renderGlance(V, onto);
    renderRanked(V, onto);
    renderExplanation(V, onto);
    renderMore(V, onto);
    state.readPick = null;
    renderRetrieval(V);
  }

  /* "How we got here": the notices and readings in order, one compact row each, up to the clock. */
  function renderTrail(V, onto) {
    const list = $('ed-trail');
    if (!list) return;
    const asOf = asOfNow();
    const all = trail(V, onto);
    const { shown, later } = upTo(all, asOf);
    list.replaceChildren();
    const trigger = V && V.advisory ? String(V.advisory.id || '') : '';
    shown.forEach((s) => {
      const li = node('li', `ed-step ${s.kind}`, null, list);
      node('time', 'ed-step-t mono', hhmm(s.t), li).setAttribute('datetime', s.t);
      node('span', 'ed-step-dot', null, li).setAttribute('aria-hidden', 'true');
      const body = node('div', 'ed-step-body', null, li);
      const head = node('div', 'ed-step-head', null, body);
      kindBadge(s.kind, s.title, head);
      const id = /^NGCP notice (.+)$/.exec(s.source);
      if (id && id[1] === trigger) badge('', 'Trigger', head);
      if (id) link(head, 'ed-step-src mono', id[1], noticeHref(id[1], s.t), `notice:${id[1]}`);
      else node('span', 'ed-step-src', s.source, head);
      node('p', 'ed-step-text', s.detail, body);
    });
    const note = $('ed-trail-note');
    if (note) {
      note.textContent = !all.length ? 'The record carries no notices or readings for this event.'
        : later ? `${later} later step${later === 1 ? '' : 's'} hidden after the as-of clock, ${when(asOf)}. Move the clock forward to see ${later === 1 ? 'it' : 'them'}.`
          : `${shown.length} steps, from the first notice to the price. Each names its source.`;
    }
    const root = $('ed-desk');
    if (root) root.hidden = false;
    const unc = $('ed-uncertain');
    if (unc) {
      unc.replaceChildren();
      const a = audit(onto, V);
      const seen = new Set();
      const items = a.unclear.filter((u) => { const k = u.text + '|' + (u.reason || ''); if (seen.has(k)) return false; seen.add(k); return true; });
      unc.hidden = !items.length;
      if (items.length) {
        node('b', null, 'Left out as uncertain', unc);
        const ul = node('ul', 'ed-list', null, unc);
        items.forEach((u) => node('li', null, `“${u.text}”${u.reason ? ': ' + u.reason : ''}. Not linked and not counted.`, ul));
      }
    }
  }

  function renderExplanation(V, onto) {
    const card = $('ed-ai');
    if (!card) return;
    if (!onto) { card.hidden = true; if ($('ev-ai-more')) $('ev-ai-more').hidden = true; return; }
    const e = explanation(onto, V);
    const body = $('ed-ai-body');
    body.replaceChildren();
    const short = brief(V, onto, state.mode);
    const sum = node('div', 'ed-brief', null, body);
    if (short.length) short.forEach((l) => node('p', null, l, sum));
    else node('p', 'ed-nodata', 'Not in the record: no recorded figures to sum up for this event.', sum);
    const vp = node('div', 'ed-vpills', null, body);
    node('span', 'gn-label', 'Holds in each view', vp);
    e.views.forEach((v) => {
      const on = v.key === state.mode;
      badge(on ? 'info' : '', `${v.label}: ${v.top ? v.top + ' first' : 'No data'}`, vp);
    });
    const fold = node('details', 'gn-disclosure ed-ai-more', null, body);
    node('summary', null, 'Read the full explanation', fold);
    const full = node('div', 'ed-ai-full', null, fold);
    node('p', 'gn-meta', e.knownAt ? `Judged with what was known at ${when(e.knownAt)} Manila${e.cutoff ? ` (market runs to ${hhmm(e.cutoff)})` : ''}. Not a forecast.` : 'When it was judged: No data. Not a forecast.', full);
    node('p', 'ed-para', e.text || 'No data: no recorded explanation for this event.', full);
    kv(full, [
      ['Holds across views', e.holds],
      ['Confidence', e.confidence],
      ['Sources used', e.sources.length ? e.sources.join(' · ') : 'No data'],
      ['Model version', [e.model ? `${e.model}${e.kind ? ', ' + e.kind : ''}` : null, e.reader ? `AI reader ${e.reader}` : null].filter(Boolean).join(' · ') || 'No data'],
    ]);
    const d = node('p', 'ed-dispute', null, full);
    node('b', null, 'Disagreement: ', d);
    d.appendChild(document.createTextNode(e.disagreement.join(' ')));
    node('p', 'gn-meta ed-foot', 'Checked against the records. It cannot add facts that are not in them.', body);
    card.hidden = false;
    const more = $('ev-ai-more');  // the decision region's step 1 points to this card
    if (more) more.hidden = false;
  }

  /* What happened: the stats in the anchor, then the price chart. */
  const SVG = 'http://www.w3.org/2000/svg';
  const sv = (tag, attrs, parent, text) => {
    const n = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach((k) => n.setAttribute(k, String(attrs[k])));
    if (text !== undefined && text !== null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const kshort = (v) => (v >= 1000 ? `₱${Math.round(v / 1000)}k` : `₱${Math.round(v)}`);
  const width = (el, min) => Math.max(min, Math.round((el.getBoundingClientRect && el.getBoundingClientRect().width) || el.clientWidth || 0) || 560);

  function renderGlance(V, onto) {
    const card = $('ed-glance');
    if (!card) return;
    card.hidden = false;
    renderPriceChart(V);
  }

  /* The price around the event: the recorded five-minute series, the trigger and the highest price
     after it marked, the offer cap, each notice as a tick, the reserve shortfall as a band under it,
     and the stretch after the as-of clock drawn faint. Every mark is a record; nothing is smoothed. */
  function renderPriceChart(V) {
    const svg = $('ed-price');
    const note = $('ed-price-note');
    const legend = $('ed-legend');
    if (!svg) return;
    svg.replaceChildren();
    if (legend) legend.replaceChildren();
    const d = priceSeries(V);
    if (d.pts.length < 2) {
      svg.setAttribute('viewBox', '0 0 320 40');
      svg.setAttribute('height', '40');
      sv('text', { x: 0, y: 24, class: 'ed-c-na' }, svg, 'Not in the record: no market prices for this event.');
      if (note) note.textContent = '';
      return;
    }
    const res = reserveSeries(V);
    const band = res.peak ? 46 : 0;
    const W = width(svg, 280), narrow = W < 480;
    const PH = narrow ? 170 : 210;
    const L = 46, R = 14, T = 26, B = 24, G = band ? 14 : 0;
    const H = T + PH + G + band + B;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('height', String(H));
    const ms = (t) => Date.parse(t + ':00Z');
    const t0 = ms(d.pts[0].t), t1 = ms(d.pts[d.pts.length - 1].t);
    const top = Math.max(d.cap, ...d.pts.map((p) => p.v)) * 1.1;
    const x = (t) => L + ((ms(t) - t0) / Math.max(1, t1 - t0)) * (W - L - R);
    const y = (v) => T + (1 - Math.max(0, v) / top) * PH;
    const inRange = (t) => t && ms(t) >= t0 && ms(t) <= t1;
    const asOf = asOfNow();
    const cut = asOf && inRange(asOf) ? asOf : null;
    // grid and scale
    [0, d.cap / 2, d.cap].forEach((v) => {
      sv('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), class: v === d.cap ? 'ed-c-cap' : 'ed-c-grid' }, svg);
      sv('text', { x: L - 8, y: y(v) + 4, class: 'ed-c-tick', 'text-anchor': 'end' }, svg, kshort(v));
    });
    sv('text', { x: L + 4, y: y(d.cap) - 5, class: 'ed-c-caplbl' }, svg, 'Offer cap ₱32,000');
    const hours = d.pts.filter((p) => p.t.slice(14, 16) === '00');
    const step = narrow && hours.length > 4 ? 2 : 1;
    hours.forEach((p, i) => { if (i % step === 0) sv('text', { x: x(p.t), y: H - 7, class: 'ed-c-tick', 'text-anchor': 'middle' }, svg, hhmm(p.t)); });
    // after the clock
    if (cut) {
      sv('rect', { x: x(cut), y: T - 6, width: Math.max(0, W - R - x(cut)), height: PH + G + band + 6, class: 'ed-c-later' }, svg);
      sv('line', { x1: x(cut), x2: x(cut), y1: T - 6, y2: T + PH + G + band, class: 'ed-c-asof' }, svg);
      const right = x(cut) > W * 0.78;
      sv('text', { x: x(cut) + (right ? -4 : 4), y: T + PH - 24, class: 'ed-c-asoflbl', 'text-anchor': right ? 'end' : 'start' }, svg, `As of ${hhmm(cut)}`);
    }
    // the series: solid up to the clock, faint after it
    const path = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
    const known = cut ? d.pts.filter((p) => p.t <= cut) : d.pts;
    const after = cut ? d.pts.filter((p, i) => p.t >= cut || (d.pts[i + 1] && d.pts[i + 1].t > cut)) : [];
    if (after.length > 1) sv('path', { d: path(after), class: 'ed-c-line ed-c-line-later' }, svg);
    if (known.length > 1) sv('path', { d: path(known), class: 'ed-c-line' }, svg);
    // notices as ticks on the time axis, each with its time and kind on hover
    d.marks.filter((m) => inRange(m.t)).forEach((m) => {
      const g = sv('g', { class: 'ed-c-mark ' + (m.kind || '') }, svg);
      sv('line', { x1: x(m.t), x2: x(m.t), y1: T + PH - 8, y2: T + PH, class: 'ed-c-tickmark' }, g);
      sv('circle', { cx: x(m.t), cy: T + PH - 11, r: 3 }, g);
      sv('title', {}, g, `${m.label} ${hhmm(m.t)}`);
    });
    // the trigger
    if (inRange(d.at)) {
      const tx = x(d.at);
      sv('line', { x1: tx, x2: tx, y1: T - 10, y2: T + PH, class: 'ed-c-trig' }, svg);
      const right = tx > W * 0.72;
      sv('text', { x: tx + (right ? -5 : 5), y: T - 12, class: 'ed-c-triglbl', 'text-anchor': right ? 'end' : 'start' }, svg, `Trigger ${hhmm(d.at)}`);
    }
    // the price at the trigger and the highest after it
    if (d.before && inRange(d.before.t) && !(d.peak && d.peak.t === d.before.t)) {
      sv('circle', { cx: x(d.before.t), cy: y(d.before.value), r: 3.5, class: 'ed-c-dot' }, svg);
    }
    if (d.peak) {
      const px = x(d.peak.t), py = y(d.peak.value);
      sv('circle', { cx: px, cy: py, r: 4.5, class: 'ed-c-peak' }, svg);
      const right = px > W * 0.6;
      const lbl = sv('text', { x: px + (right ? -9 : 9), y: py + 16, class: 'ed-c-peaklbl', 'text-anchor': right ? 'end' : 'start' }, svg);
      sv('tspan', { class: 'ed-c-peakv' }, lbl, peso(d.peak.value));
      sv('tspan', {}, lbl, ` highest, ${hhmm(d.peak.t)}`);
    }
    // the reserve shortfall band
    if (band) {
      const b0 = T + PH + G, b1 = b0 + band;
      const ry = (v) => b1 - (Math.max(0, v) / res.peak.v) * (band - 6);
      sv('line', { x1: L, x2: W - R, y1: b1, y2: b1, class: 'ed-c-grid' }, svg);
      const area = res.pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${ry(p.v).toFixed(1)}`).join(' ')
        + `L${x(res.pts[res.pts.length - 1].t).toFixed(1)},${b1}L${x(res.pts[0].t).toFixed(1)},${b1}Z`;
      sv('path', { d: area, class: 'ed-c-short' }, svg);
      sv('text', { x: L - 8, y: b0 + 10, class: 'ed-c-tick', 'text-anchor': 'end' }, svg, `${Math.round(res.peak.v)}`);
      sv('text', { x: L - 8, y: b1, class: 'ed-c-tick', 'text-anchor': 'end' }, svg, '0');
      sv('text', { x: L + 4, y: b0 + 10, class: 'ed-c-bandlbl' }, svg, `Reserve short, MW · most ${Math.round(res.peak.v)} at ${hhmm(res.peak.t)}`);
    }
    if (legend) {
      const item = (cls, text) => { const s = node('span', 'ed-lg', null, legend); node('i', 'ed-lg-k ' + cls, null, s); s.appendChild(document.createTextNode(text)); };
      item('line', 'Price, ₱/MWh');
      if (inRange(d.at)) item('trig', 'Trigger');
      if (d.marks.length) item('mark', 'Notice');
      if (band) item('short', 'Reserve shortfall');
      if (cut) item('later', 'After the as-of clock');
    }
    if (note) {
      const lo = Math.min(...d.pts.map((p) => p.v)), hi = Math.max(...d.pts.map((p) => p.v));
      note.textContent = `Recorded five-minute price, ${hhmm(d.pts[0].t)} to ${hhmm(d.pts[d.pts.length - 1].t)} Manila, from ${peso(lo)} to ${peso(hi)}/MWh.`
        + (d.before && d.peak && d.before.value === d.peak.value ? ' It was already at this level before the trigger.' : '');
    }
  }

  function renderAudit(V, onto) {
    const body = $('ed-audit-body');
    if (!body) return;
    const a = audit(onto, V);
    body.replaceChildren();
    const grid = node('dl', 'ed-kv ed-arows', null, body);
    const row = (k, items, cls) => {
      node('dt', null, k, grid);
      const v = node('dd', 'ed-av' + (cls ? ' ' + cls : ''), null, grid);
      if (!items.length) node('span', 'ed-nodata', 'No data', v);
      items.forEach((s) => node('p', null, s, v));
      return v;
    };
    row('Source data', a.sources);
    const see = row('See for yourself', []);
    see.replaceChildren();
    [['/data', 'Data catalog'], ['/notices', 'Operator notices'], ['/explain', 'How the ontology works'], ['/paper', 'Working paper']]
      .forEach(([href, label], i) => { if (i) see.appendChild(document.createTextNode(' · ')); const l = node('a', null, label, see); l.href = href; });
    row('Steps', [`${trail(V, onto).length} steps in “How we got here”, each with its source`]);
    row('Calculation', a.calculation);
    row('Model version', a.models, 'mono');
    row('Withheld as not yet known', Object.entries(a.withheld).map(([k, v]) => `${k}: ${v === null ? 'No data' : v}`));
    const u = row('Unclear matches', a.unclear.length ? [] : ['None listed in the record.']);
    if (a.unclear.length) u.replaceChildren();
    a.unclear.forEach((x) => {
      const p = node('p', 'ed-unclear', null, u);
      badge('warning', 'Unclear', p);
      p.appendChild(document.createTextNode(` ${x.text} (${x.view})${x.reason ? ', ' + x.reason : ''}: not linked and not counted.`));
    });
    if (a.check.length) row('What to check next', a.check);
  }

  /* "What stood out": one row per family; each row is a button that opens its detail right under
     it (one open at a time). */
  const PILL_OF = { warn: 'alert', amber: 'warning', plain: '', low: 'info', ctx: '', none: '' };
  function renderRanked(V, onto) {
    const card = $('ed-ranked');
    if (!card) return;
    const asOf = asOfNow();
    const r = standout(onto, state.mode, asOf);
    if (!onto || !onto.drivers) { card.hidden = true; return; }
    const cur = views(onto).find((v) => v.key === state.mode);
    $('ed-ranked-line').textContent = `${cur ? cur.label : 'This view'}${r.cutoff ? ` · market runs to ${hhmm(r.cutoff)} Manila` : ''}${r.any ? '' : ' · the record carries no ranking for this view'}.`;
    const host = $('ed-ranked-rows');
    host.replaceChildren();
    /* A family the record leaves without a score gets no row: it joins one line under the rows. */
    const shownRows = r.rows.filter((x) => x.state !== 'No data');
    const blank = r.rows.filter((x) => x.state === 'No data').map((x) => x.name);
    if (!shownRows.length) { card.hidden = true; return; }
    if (!shownRows.some((x) => x.family === state.open)) state.open = null;
    shownRows.forEach((x) => {
      const id = 'ed-rk-d-' + x.family.toLowerCase();
      const open = state.open === x.family;
      const b = node('button', 'ed-rk-row' + (open ? ' open' : ''), null, host);
      b.type = 'button';
      b.setAttribute('aria-expanded', String(open));
      b.setAttribute('aria-controls', id);
      const nm = node('span', 'ed-rk-name', null, b);
      node('span', 'ed-rk-n mono', x.rank, nm);
      node('b', null, x.name, nm);
      const mid = node('span', 'ed-rk-mid', null, b);
      node('span', 'ed-rk-text' + (x.text === NOT ? ' ed-nodata' : ''), x.text, mid);
      const bar = node('progress', 'ed-rk-bar ' + x.cls, null, mid);
      bar.max = 100; bar.value = x.bar;
      bar.setAttribute('aria-label', x.pct === null ? `${x.name}: no score` : `${x.name}: ${x.pct}%`);
      node('span', 'gn-badge ed-rk-pill' + (PILL_OF[x.cls] ? ' gn-badge--' + PILL_OF[x.cls] : ''), x.state, b);
      const d = node('div', 'ed-rk-detail', null, host);
      d.id = id;
      d.hidden = !open;
      if (open) {
        const sec = (title, items, cls) => {
          if (!items.length) return;
          node('h4', 'gn-label ed-mini', title, d);
          const ul = node('ul', 'ed-list' + (cls ? ' ' + cls : ''), null, d);
          items.forEach((s) => node('li', null, s, ul));
        };
        if (x.detail.note) node('p', 'ed-sub', x.detail.note, d);
        sec('Signals', x.detail.signals.length ? x.detail.signals : (x.family === 'Rules' ? [] : [`${NOT}: no signal for this family in this view.`]));
        sec('Flags', x.detail.flags);
        sec('Facts in this view, with when each was known', x.detail.facts);
        sec('Held back', x.detail.held);
        if (x.detail.unclear.length) {
          node('h4', 'gn-label ed-mini', 'Unclear names (not linked, not counted)', d);
          const ul = node('ul', 'ed-list', null, d);
          x.detail.unclear.forEach((s) => { const li = node('li', null, null, ul); badge('warning', 'Unclear', li); li.appendChild(document.createTextNode(' ' + s)); });
        }
        sec('Sources', x.detail.sources.length ? x.detail.sources : [NOT], 'mono');
      }
      b.addEventListener('click', () => { state.open = open ? null : x.family; renderRanked(V, onto); const nb = $(id); if (nb && nb.previousSibling) nb.previousSibling.focus(); });
    });
    if (blank.length) node('p', 'gn-unknowns ed-rk-blank', `No score in the record: ${blank.join(', ')}.`, host);
    $('ed-ranked-src').textContent = onto.source ? `Source: ${plainSrc(onto.source)}. Evidence, not proof.` : 'Evidence, not proof.';
    card.hidden = false;
  }

  /* "Related records". */
  function relRow(parent, r) {
    const li = node('li', 'ed-rel' + (r.flag ? ' unc' : ''), null, parent);
    node('span', 'gn-label ed-rel-k', r.rel, li);
    const body = node('div', 'ed-rel-v', null, li);
    const head = node('div', 'ed-rel-h', null, body);
    if (r.href) {
      const a = node('a', 'ed-rel-a', r.title, head);
      a.href = r.href;
      const ent = /^\/plant\/([^/?#]+)$/.exec(r.href) || null;
      const notice = /#adv-(.+)$/.exec(r.href);
      const ev = /^\/event\/([^/?#]+)$/.exec(r.href);
      if (ent) a.setAttribute('data-entity', 'plant:' + decodeURIComponent(ent[1]));
      else if (notice) a.setAttribute('data-entity', 'notice:' + decodeURIComponent(notice[1]));
      else if (ev) a.setAttribute('data-entity', 'event:' + decodeURIComponent(ev[1]));
    } else node('b', null, r.title, head);
    if (r.flag) badge('warning', r.flag, head);
    if (r.text) node('p', 'ed-rel-t', r.text, body);
    if (r.evidence && r.evidence.length) node('p', 'gn-meta ed-rel-e', r.evidence.join(' · '), body);
  }
  function renderMore(V, onto) {
    const body = $('ed-more-body');
    if (!body) return;
    const asOf = asOfNow();
    const d = moreDetail(V, onto, state.mode, asOf);
    body.replaceChildren();
    const lat = d.later.facts + d.later.notices + d.later.unclear;
    if (lat) node('p', 'gn-meta', `${lat} record${lat === 1 ? '' : 's'} known after the as-of clock (${hhmm(asOf)}) left out: ${d.later.notices} notice${d.later.notices === 1 ? '' : 's'}, ${d.later.facts} fact${d.later.facts === 1 ? '' : 's'}${d.later.unclear ? `, ${d.later.unclear} unclear name${d.later.unclear === 1 ? '' : 's'}` : ''}.`, body);
    const grid = node('div', 'ed-rel-groups', null, body);
    const empty = [];
    /* A row that is all unknowns (the congestion line when the record carries none) folds into
       the one unknowns line under the groups. */
    const blank = (r) => !r.href && String(r.title).indexOf(NOT) >= 0 && String(r.text || '').indexOf(NOT) >= 0;
    d.groups.forEach((g) => {
      const rows = g.rows.filter((r) => !blank(r));
      if (rows.length < g.rows.length) empty.push(g.key === 'lines' ? 'power line congestion' : g.title.toLowerCase());
      if (!rows.length) { if (rows.length === g.rows.length) empty.push(g.title.toLowerCase()); return; }
      g = Object.assign({}, g, { rows });
      const box = node('section', 'ed-rel-g', null, grid);
      node('h3', 'ed-mini', g.title, box);
      const ul = node('ul', 'ed-rel-list', null, box);
      g.rows.forEach((r) => relRow(ul, r));
    });
    /* Price alerts beside the event, read from the alert inbox at the clock. PERF-6: a redraw
       (a clock move, a view tab) draws them from the last answer at the clock as it now stands;
       the inbox is read once at the start and again when the shell says the clock settled
       (`GNShell.onInboxDue`, see `readAlerts`), not at every tick. */
    const al = node('section', 'ed-rel-g', null, grid);
    node('h3', 'ed-mini', 'Price alerts around the same time', al);
    state.alertBox = node('ul', 'ed-rel-list', null, al);
    drawAlerts(V);
    if (state.inbox === undefined && !state.alertTicket) readAlerts(V);
    /* AI second opinion: only when one is saved; the decision region carries the reader's answers. */
    const s = d.second;
    if (s) {
      const box = node('section', 'ed-rel-g ed-second', null, grid);
      node('h3', 'ed-mini', 'AI second opinion', box);
      node('p', 'gn-meta', `${s.known}. It reads the trigger notice four ways and keeps the answer most of them gave.`, box);
      kv(box, [['Reading', s.label], ['Rule', s.rule], ['Agreement', s.steady + (s.unstable ? ' · unstable' : '')], ['Holds in each view', s.holds], ['Open disagreement', s.disagreement], ['Model', s.by]]);
    } else empty.push('AI second opinion');
    if (empty.length) node('p', 'gn-unknowns', `Not on record for this view: ${empty.join(', ')}.`, body);
  }

  /* The price alerts list of "More detail", from the last inbox answer (`state.inbox`: undefined
     until the first read lands, null when it could not be read) at the clock as it now stands.
     DM-5 (review of PERF-6): an answer read at a later clock than this one (`state.inboxAt`) is
     withheld until the read at this time lands: it would show an alert's later end, peak and
     severity. An answer read earlier states nothing after this cutoff and is drawn. */
  function drawAlerts(V) {
    const box = state.alertBox;
    if (!box) return;
    const asOf = shell() && shell().asOf ? shell().asOf() : null;
    box.replaceChildren();
    if (state.inbox === undefined || (state.inbox && !inboxFits(state.inboxAt, asOf))) {
      node('li', 'gn-loading', 'Reading the alert inbox…', box); return;
    }
    if (!state.inbox) { node('li', 'ed-nodata', `${NOT}: the alert inbox could not be read here.`, box); return; }
    const rows = relatedAlerts(V, state.inbox, asOf);
    if (!rows.length) node('li', 'ed-nodata', `No price alert in ${V.grid_name || 'the region'} up to this time.`, box);
    rows.forEach((r) => relRow(box, r));
  }
  /* Reads the inbox at the clock (EventAPI.alerts, the shell's one reader) and redraws the list;
     the latest read wins. */
  function readAlerts(V) {
    const asOf = shell() && shell().asOf ? shell().asOf() : null;
    const ticket = (state.alertTicket = (state.alertTicket || 0) + 1);
    const E = window.EventAPI;
    Promise.resolve(E && E.alerts ? E.alerts(asOf) : null).then((inbox) => {
      if (ticket !== state.alertTicket) return;
      state.inbox = inbox || null;
      state.inboxAt = asOf;  // DM-5: the cutoff this answer was read at
      drawAlerts(V);
    });
  }

  /* RAG-5: "What the system read", from the view's retrieval block. Without the block the panel
     keeps its hidden, empty markup and its tab stays hidden; with it, the tab appears and the
     panel opens through its tab. */
  function renderRetrieval(V) {
    const card = $('ed-read');
    const body = $('ed-read-body');
    if (!card || !body) return;
    const r = retrieval(V, state.mode, state.readPick);
    if (!r) return;
    body.replaceChildren();
    const q = node('p', 'ed-rt-q', null, body);
    node('b', 'gn-label', 'Question', q);
    q.appendChild(document.createTextNode(' ' + r.question));
    const tabs = node('div', 'gn-seg ed-rt-tabs', null, body);
    tabs.setAttribute('role', 'group');
    tabs.setAttribute('aria-label', 'Cutoff');
    r.tabs.forEach((t) => {
      const b = node('button', 'ed-rt-tab' + (t.on ? ' on' : ''), t.label, tabs);
      b.type = 'button';
      b.dataset.rt = t.id;
      b.setAttribute('aria-pressed', String(t.on));
      b.addEventListener('click', () => { state.readPick = t.id; renderRetrieval(V); });
    });
    const follows = !!(document.body && document.body.className && /\bed-has-view\b/.test(document.body.className));
    node('p', 'gn-meta ed-rt-cut', `${r.state.label}: only passages first available by ${r.state.cutoff} are ranked.${follows ? ' The view above picks the cutoff. These tabs switch this card only.' : ''}`, body);
    const hid = node('div', 'ed-hidden ed-rt-held', null, body);
    if (!r.held) node('span', 'ed-hidden-t ed-nodata', `Withheld by reason: ${RT_NO}`, hid);
    else {
      node('span', 'ed-hidden-t', 'Withheld by reason:', hid);
      r.held.forEach((h) => { const p = pill('', null, hid); p.dataset.reason = h.reason; node('b', 'mono', h.n, p); p.appendChild(document.createTextNode(' ' + h.why)); });
    }
    const ol = node('ol', 'ed-rt-list', null, body);
    if (!r.rows.length) node('li', 'ed-nodata', `No passage is ranked at this cutoff (${RT_NO}).`, ol);
    r.rows.forEach((x) => {
      const li = node('li', 'ed-rt-row' + (x.cited ? ' cited' : ''), null, ol);
      const head = node('div', 'ed-rt-h', null, li);
      node('span', 'ed-rt-rank mono', '#' + x.rank, head);
      node('b', null, x.issuer, head);
      node('span', 'ed-rt-label', x.label, head);
      if (x.cited) pill('ok', 'cited', head);
      node('p', 'gn-meta ed-rel-e', `First available ${x.available} · basis ${x.basis} · distance ${x.distance}`, li);
      if (x.excerpt) node('blockquote', 'ed-rt-ex', x.excerpt, li);
      else node('p', 'ed-rt-id', `Text not shown: record identity only. ${x.identity}`, li);
    });
    if (r.late.length) node('p', 'ed-sub ed-rt-late', `${r.late.length} ranked row${r.late.length === 1 ? '' : 's'} first available after this cutoff not shown: ${r.late.join('; ')}.`, body);
    const j = node('p', 'ed-rt-j' + (r.judgment.used === true ? '' : ' ed-nodata'), r.judgment.text, body);
    if (r.judgment.receipt) { j.appendChild(document.createTextNode(' Judgment receipt ')); node('span', 'mono', r.judgment.receipt, j); }
    node('h3', 'ed-mini', 'Receipt', body);
    const dl = kv(body, r.receipt);
    dl.className += ' ed-rt-receipt';
    const tab = $('ev-tab-read');
    if (tab) tab.hidden = false;
    else card.hidden = false;
  }

  /* "What to check next": the record's first thing to check, and how sure the record is. */
  function renderNext(V, onto) {
    const card = $('ed-next');
    const s = (onto && onto.summary) || null;
    if (!card || !s) return;
    const body = $('ed-next-body');
    body.replaceChildren();
    const check = Array.isArray(s.what_to_check) ? s.what_to_check.map(String) : [];
    node('p', 'ed-next-a', check.length ? check[0].charAt(0).toUpperCase() + check[0].slice(1) : 'No data: the record names nothing to check.', body);
    if (check.length > 1) {
      const ul = node('ul', 'ed-list', null, body);
      check.slice(1).forEach((c) => node('li', null, c, ul));
    }
    const sure = node('p', 'gn-meta ed-sure', null, body);
    sure.appendChild(document.createTextNode('How sure: '));
    node('b', null, s.confidence ? String(s.confidence) : 'No data', sure);
    if (s.confidence_reason) sure.appendChild(document.createTextNode('. ' + String(s.confidence_reason)));
    card.hidden = false;
  }

  /* Step 1 of the decision region: the AI reader's recorded conclusion (its label, what the
     desk's rule proposes from it, the cutoff, the run record and the answers), or an empty state
     that says why nothing is proposed. Every word is the baked judgment's own. */
  const PROPOSES = { challenges: 'opening the assumption for review', supports: 'retaining the assumption',
    mixed: 'investigating the assumption', insufficient: 'investigating the assumption' };
  function renderReader(V) {
    const box = $('ev-ai');
    if (!box) return;
    const r = reader(V);
    box.setAttribute('data-state', r ? 'recorded' : 'none');
    const label = $('ev-ai-label');
    const line = $('ev-ai-line');
    const cut = $('ev-ai-cutoff');
    const hint = $('ev-ai-hint');
    const answers = $('ev-answers');
    if (!r) {
      if (label) label.hidden = true;
      if (line) line.hidden = true;
      if (cut) cut.hidden = true;
      if (answers) answers.hidden = true;
      if (hint) {
        hint.textContent = 'No AI reading is recorded for this event, so nothing is proposed. Your decision rests on the evidence on this page.';
        hint.hidden = false;
      }
      return;
    }
    if (hint) hint.hidden = true;
    if (line) {
      line.textContent = r.label
        ? `It labelled the trigger notice ${r.label}. In the desk's rule that proposes ${PROPOSES[r.label] || 'no change to this assumption'}.`
        : 'The record names no label for this reading.';
      line.hidden = false;
    }
    if (label) {
      label.replaceChildren();
      badge(r.tone, r.label || NOT, label).className += ' ev-ai-badge';
      if (r.unstable) badge('warning', 'Unstable across wordings', label);
      node('span', 'gn-meta', (r.by ? r.by + '. ' : '') + 'Recorded run, not re-run on this page', label);
      label.hidden = false;
    }
    if (cut) { cut.textContent = r.cutoff ? r.cutoff.text : 'The cutoff it read at is not in the record.'; cut.hidden = false; }
    if (answers) {
      answers.replaceChildren();
      const fold = node('details', 'gn-disclosure', null, answers);
      node('summary', null, `Show the ${r.answers.length} answers`, fold);
      const table = node('table', 'gn-table gn-table--compact ev-answers-t', null, fold);
      const head = node('tr', null, null, node('thead', null, null, table));
      [['Question', ''], ['Answer', ''], ['Wordings agree', 'num']].forEach(([h, c]) => { const th = node('th', c || null, h, head); th.setAttribute('scope', 'col'); });
      const tb = node('tbody', null, null, table);
      r.answers.forEach((a) => {
        const tr = node('tr', a.key ? 'key' : null, null, tb);
        const q = node('td', 'trunc', a.short, tr);
        q.title = a.q;
        if (a.key) badge('', 'Decided it', q);
        node('td', 'mono', a.a, tr);
        const ag = node('td', 'num', null, tr);
        const pips = node('span', 'ev-pips', null, ag);
        pips.setAttribute('aria-hidden', 'true');
        a.pips.forEach((ok) => node('i', ok ? 'ok' : 'off', null, pips));
        node('span', 'mono', ` ${a.agree}/${a.of}`, ag);
      });
      if (r.receipt) node('p', 'gn-meta', `Run record: ${r.receipt}`, fold);
      answers.hidden = false;
    }
  }

  /* Step 2: the assumption the event touches, with its value, unit and record. */
  function renderAssumption(V) {
    const body = $('ev-assume-body');
    if (!body) return;
    body.replaceChildren();
    const a = V && V.assumption;
    if (!a || num(a.value) === null) {
      node('p', 'ed-nodata', 'No register assumption is named for this event.', body);
      return;
    }
    const fig = node('div', 'ev-assume-fig', null, body);
    const v = node('span', 'gn-value gn-value--lg', Number(num(a.value)).toLocaleString('en-US', { maximumFractionDigits: 1 }), fig);
    if (a.unit) node('span', 'gn-unit', String(a.unit), v);
    node('span', 'gn-meta', 'Accepted value', fig);
    if (a.proposition) node('p', 'ev-assume-prop', withheld(a.proposition), body);
    const rows = (Array.isArray(a.kv) ? a.kv : []).filter((r) => Array.isArray(r) && r.length > 1);
    const site = eventSite(V);
    if (rows.length || (a.accepted && a.accepted.at)) {
      const dl = node('dl', 'ed-kv ev-assume-kv', null, body);
      rows.forEach(([k, val]) => {
        node('dt', null, String(k), dl);
        const dd = node('dd', null, null, dl);
        const text = withheld(String(val));
        if (site && /^site$/i.test(String(k)) && String(val).trim() === site.site) link(dd, 'mono', site.site, '/plant/' + encodeURIComponent(site.site), 'plant:' + site.site);
        else dd.textContent = text;
      });
      if (a.accepted && a.accepted.at) { node('dt', null, 'Accepted', dl); node('dd', null, `${a.accepted.at}${a.accepted.by ? ' by ' + a.accepted.by : ''}`, dl); }
    }
  }

  /* The person's status in the head, after a decision is saved on the case or in the journal. */
  function setDecided(V, onto, text) {
    state.decided = text ? { text } : null;
    renderPills(V, onto);
  }

  /* Step 4: this person's journal entries on the event, newest first, as receipts. */
  async function renderJournalList(V, onto) {
    const host = $('ev-journal-list');
    if (!host) return;
    const J = window.GNJournal;
    const S = shell();
    const user = S && S.user ? S.user() : null;
    host.replaceChildren();
    const none = () => node('p', 'gn-meta', 'Nothing is on the record for you yet. A saved decision appears here with its receipt.', host);
    if (!J || !user) { none(); return; }
    const res = await J.api('GET', '/api/journal?' + new URLSearchParams({ event: V.id, scope: 'mine', sort: 'newest' }).toString());
    host.replaceChildren();
    if (!res.ok) { node('p', 'gn-error', 'Your journal entries could not be read: ' + J.failure(res), host); return; }
    const entries = Array.isArray(res.body && res.body.entries) ? res.body.entries : [];
    if (!entries.length) { none(); return; }
    const ol = node('ol', 'ev-jlist', null, host);
    entries.slice(0, 4).forEach((e) => {
      const d = J.decisionOf ? J.decisionOf(e.text) : { decision: null, reason: e.text };
      const li = node('li', null, null, ol);
      const head = node('div', 'ev-jlist-h', null, li);
      badge(d.decision === 'retain' ? 'ok' : d.decision === 'change' ? 'warning' : '', d.decision ? (d.decision === 'retain' ? 'Retain' : 'Change') : 'Note', head);
      node('span', 'gn-meta mono', `As of ${J.asOfWords(e.as_of)}`, head);
      node('span', 'gn-meta', e.visibility === 'desk' ? 'Shared with the desk' : 'Private', head);
      node('p', 'ev-jlist-t', d.reason || e.text, li);
    });
    const more = node('p', 'ev-jlist-more', null, host);
    link(more, 'gn-link', entries.length > 4 ? `All ${entries.length} entries in your journal` : 'Open your journal', '/journal?event=' + encodeURIComponent(V.id));
    const last = entries.map((e) => (J.decisionOf ? J.decisionOf(e.text) : { decision: null })).find((x) => x.decision);
    if (last && !state.caseDecided) setDecided(V, onto, `Decided: ${last.decision === 'retain' ? 'Retain' : 'Change'}`);
  }

  /* The decision box: the person's decision is the journal entry (Retain, Change or Note, a
     reason and the pinned evidence), on every event. The step's own heading names it. */
  function mountJournal(V, onto) {
    const host = $('ed-journal-box');
    if (!host) return;
    const card = $('ed-journal');
    if (card) card.hidden = false;
    if (!window.GNJournal || !window.GNJournal.mountBox) { host.textContent = 'The journal could not be loaded.'; return; }
    window.GNJournal.mountBox(host, {
      kind: 'event', id: V.id,
      decision: true,
      title: null,
      snapshot: (asOf) => snapshotFor(V, asOf),
      onSaved: () => { renderJournalList(V, onto); },
    });
  }

  /* What was known when the entry is saved, from this page's own records at the clock: the region,
     the price at the clock, the latest notice and the facts a later reader needs. */
  function snapshotFor(V, asOf) {
    const at = asOf || String(V.event_at || '').slice(0, 16);
    const p = priceAt(V.market, at);
    const notices = (Array.isArray(V.timeline) ? V.timeline : []).filter((x) => x && x.src && x.src !== 'WESM RTD' && String(x.t).slice(0, 16) <= at);
    const last = notices[notices.length - 1];
    const facts = [];
    if (V.title) facts.push(String(V.title));
    const k = keyFigure(V);
    if (k && k.before) facts.push(`Price at the trigger ${k.before.text}/MWh at ${hhmm(k.before.t)}`);
    if (k && k.peak && k.peak.t <= at) facts.push(`Highest after the trigger ${k.peak.text}/MWh at ${hhmm(k.peak.t)}`);
    const j = V.judgment;
    facts.push(j ? `AI reader proposed: ${j.label} (${plainReceipt(j.receipt || '') || 'recorded run'})` : 'No AI reading recorded');
    if (V.assumption && num(V.assumption.value) !== null) facts.push(`Assumption: ${withheld(V.assumption.proposition || '')} ${V.assumption.value} ${V.assumption.unit || ''}`.trim());
    if (synthetic(V)) facts.push('Synthetic data');
    return {
      price: p ? p.value : null,
      region: /^C(LUZ|VIS|MIN)$/.test(String(V.grid || '')) ? V.grid : null,
      latest_notice: last ? `${when(String(last.t).slice(0, 16))} · ${opText(last.text)}` : null,
      known_facts: facts,
    };
  }

  async function start() {
    const id = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
    const E = window.EventAPI;
    if (!E) return;
    let V = null, onto = null;
    try { V = await E.load(id); } catch (err) { return; }
    try { onto = await E.drivers(id); } catch (err) { onto = null; }
    renderPills(V, onto);
    renderHead(V, onto);
    renderView(V, onto);
    renderStats(V, onto);
    renderGlance(V, onto);
    renderTrail(V, onto);
    renderRanked(V, onto);
    renderExplanation(V, onto);
    renderMore(V, onto);
    renderRetrieval(V);
    renderAudit(V, onto);
    renderNext(V, onto);
    renderReader(V);
    renderAssumption(V);
    mountJournal(V, onto);
    renderJournalList(V, onto);
    if (window.GridFlow) window.GridFlow.mount({ V, onto, mode: () => state.mode, asOf: asOfNow });
    /* event.js says when the case form saved a decision; the head follows. */
    document.addEventListener('gn:decided', (ev) => {
      state.caseDecided = true;
      setDecided(V, onto, ev && ev.detail && ev.detail.what ? String(ev.detail.what) : 'Decision recorded');
      renderJournalList(V, onto);
    });
    const s = shell();
    if (s && s.onAsOf) s.onAsOf(() => { renderTrail(V, onto); renderStats(V, onto); renderGlance(V, onto); renderRanked(V, onto); renderMore(V, onto); if (!s.onInboxDue) readAlerts(V); });
    if (s && s.onInboxDue) s.onInboxDue(() => readAlerts(V));  // PERF-6: was a read at every clock move
    if (s && s.onUser) s.onUser(() => renderJournalList(V, onto));
    let lastW = 0, timer = null;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const svg = $('ed-price');
        const w = svg ? width(svg, 0) : 0;
        if (w && w !== lastW) { lastW = w; renderPriceChart(V); }
      }, 120);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
