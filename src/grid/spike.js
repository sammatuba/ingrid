/* InGRID alert page (ericka-desk, platform polish PP-B1): every alert opens at
   `/alert/<alert key>` (flow F2: inbox, alert, event, decision). Built on request from the baked
   replay by GET /api/alerts/alert/<key>?at= (src/alerts/service.py `alert`): the alert as the
   inbox shows it, the region's five-minute series two hours either side, and the region's
   operator notices in that window.

   Rules carried here:
   * a cause is shown only when the server matched a recorded event (`alert.cause`); the notices
     are "Around this time", not claimed as the cause;
   * nothing after the shared replay clock (GNShell.asOf()) is shown; the server cuts the window
     at the clock and an alert that starts later says so;
   * a figure the record does not carry gets no tile: it is named once on the unknowns line;
     no peso figure, no forecast;
   * notice text goes through GNShell.opText (technology words withheld);
   * text only (textContent, DOM and SVG APIs), no inline style: the page policy forbids it.

   The pure helpers are exported for node when `module` exists. */
(function () {
  'use strict';
  const KEY = /^[0-9a-f]{24}$/;
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const KIND = { trip: 'Trip', online: 'Back online', red: 'Red alert', yellow: 'Yellow alert', mld: 'Load dropping', notice: 'Notice' };
  const NA = 'Not in the record';

  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const num = (v, digits) => Number(v).toLocaleString('en-US', { maximumFractionDigits: digits || 0, minimumFractionDigits: 0 });
  const day = (t) => `${Number(t.slice(8, 10))} ${MONTHS[Number(t.slice(5, 7)) - 1]}`;
  const when = (t) => `${day(t)} ${t.slice(11, 16)}`;
  const span = (a, b) => (!b || a === b ? when(a) : a.slice(0, 10) === b.slice(0, 10) ? `${when(a)}–${b.slice(11, 16)}` : `${when(a)} – ${when(b)}`);
  const minutes = (n) => (n < 60 ? `${n} min` : `${Math.floor(n / 60)} h${n % 60 ? ' ' + (n % 60) + ' min' : ''}`);

  /* The page's figures from one answer: each stat the record holds, and the ones it does not hold
     named once on the unknowns line (never a tile of their own). Nothing is computed beyond a
     ratio of two recorded prices and a count of intervals. */
  function summary(answer) {
    const a = answer.alert;
    const w = answer.around || {};
    const spike = a.direction !== 'collapse';
    const i = (w.t || []).indexOf(a.interval_manila);
    const at = (name) => (i >= 0 && isNum((w[name] || [])[i]) ? w[name][i] : null);
    const usual = isNum(a.usual_php_mwh) ? a.usual_php_mwh : null;
    const n = isNum(a.intervals) ? a.intervals : null;
    const head = `${a.region_label || a.region} price ${spike ? 'spike' : 'collapse'}`;
    const tiles = [
      { k: spike ? 'Peak price' : 'Lowest price', v: isNum(a.price_php_mwh) ? num(a.price_php_mwh) : null, u: '₱/MWh', n: `at ${when(a.interval_manila)}`, key: true, gap: 'the price' },
      { k: 'Usual', v: usual !== null ? num(usual) : null, u: '₱/MWh', n: 'same hour, earlier days',
        gap: 'usual price for this hour (the first replay day has no earlier day)' },
      { k: 'Multiple of usual', v: usual && usual > 0 && isNum(a.price_php_mwh) ? num(a.price_php_mwh / usual, 1) : null, u: '×', gap: 'multiple of usual' },
      { k: 'Duration', v: n !== null ? minutes(n * 5) : null, u: '', n: n !== null ? `${n} five-minute interval${n === 1 ? '' : 's'}` : '', gap: 'duration' },
      { k: 'Reserve short', v: at('reserve_short_mw') !== null ? num(at('reserve_short_mw')) : null, u: 'MW', n: 'at the peak', gap: 'reserve short at the peak' },
      { k: 'Curtailed', v: at('curtailed_mw') !== null ? num(at('curtailed_mw')) : null, u: 'MW', n: 'at the peak', gap: 'curtailment at the peak' },
      { k: 'Demand', v: at('demand_mw') !== null ? num(at('demand_mw')) : null, u: 'MW', n: 'at the peak', gap: 'demand at the peak' },
    ];
    const unknowns = tiles.filter((t) => t.v == null).map((t) => t.gap);
    return {
      head,
      title: `${head} · ${isNum(a.price_php_mwh) ? num(a.price_php_mwh) + ' PHP/MWh' : NA}`,
      tiles: tiles.filter((t) => t.v != null),
      unknowns,
      unknownLine: unknowns.length ? `Not on record: ${unknowns.join(', ')}.` : '',
    };
  }

  /* Whether the price is still past the level at the replay time: its last interval is the clock's own. */
  function status(answer) {
    const a = answer.alert;
    const clock = String((answer.around || {}).clock || answer.at || '').slice(0, 16);
    const m = clock.match(/^(.*T\d{2}):(\d{2})$/);
    const now = m ? `${m[1]}:${String(Math.floor(Number(m[2]) / 5) * 5).padStart(2, '0')}` : '';
    const live = Boolean(now && String(a.last || '') >= now);
    return { live, text: live ? 'Still past the level' : `Ended ${a.last ? when(a.last) : ''}`.trim() };
  }

  /* The steps for "Around this time": the alert's own moments and the region's notices, by time.
     A notice is context only; `claimed` is always false. */
  function steps(answer) {
    const a = answer.alert;
    const w = answer.around || {};
    const out = [{ t: a.first, kind: 'alert', label: 'Alert', text: `Price first ${a.direction === 'collapse' ? 'fell to' : 'reached'} the level (${a.threshold_text || 'the saved level'})` }];
    if (a.interval_manila && a.interval_manila !== a.first) {
      out.push({ t: a.interval_manila, kind: 'alert', label: 'Alert', text: `${a.direction === 'collapse' ? 'Lowest' : 'Peak'} price ${isNum(a.price_php_mwh) ? num(a.price_php_mwh) + ' PHP/MWh' : ''}`.trim() });
    }
    if (a.last && a.last !== a.first && a.last !== a.interval_manila) out.push({ t: a.last, kind: 'alert', label: 'Alert', text: 'Last interval past the level' });
    for (const x of w.notices || []) out.push({ t: x.t, kind: x.kind in KIND ? x.kind : 'notice', label: KIND[x.kind] || 'Notice', id: x.id, text: x.text, notice: true, claimed: false });
    out.sort((p, q) => (p.t < q.t ? -1 : p.t > q.t ? 1 : (p.notice ? 1 : 0) - (q.notice ? 1 : 0)));
    return out;
  }

  /* "Notices around this alert" from the server's `notices_around`: the region's
     outage, trip and grid notices from six hours before the alert to its last interval, posted by the
     replay time. None is a confirmed cause; each says how sure its plant match is and why, and an
     Unclear one links no plant. Links only to the desk's own notice and plant pages. */
  const NOTICE_HREF = /^\/notices\?at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}#adv-[A-Za-z0-9._-]{1,64}$/;
  const PLANT_HREF = /^\/plant\/[A-Za-z0-9._-]{1,64}$/;
  const MATCH_TONE = { plant: 'info', link: '', region: '', none: '', unclear: 'unclear' };
  function related(answer) {
    const a = (answer && answer.alert) || {};
    const n = a.notices_around;
    if (!n) return { note: 'The notices around this alert could not be read. No data.', rows: [], rule: '' };
    const c = n.counts || {};
    const region = a.region_label || a.region || 'the region';
    const rows = (n.items || []).slice().reverse().map((x) => ({
      t: x.t, id: x.id || '', kind: x.kind_label || 'Notice', text: x.text || '',
      match: x.match_label || 'Unclear', tone: MATCH_TONE[x.match] == null ? 'unclear' : MATCH_TONE[x.match],
      reason: x.reason || '', rule: x.rule_text || '',
      timing: x.timing === 'during' ? 'during the alert' : 'before the alert',
      notice: NOTICE_HREF.test(x.notice_href || '') ? x.notice_href : null,
      plant: x.match === 'plant' && PLANT_HREF.test(x.plant_href || '') ? { href: x.plant_href, code: x.plant } : null,
    }));
    const note = !n.count
      ? `No ${region} outage, trip or grid notice from ${when(n.from || a.first)} to ${when(n.to || a.last)}, up to the replay time.`
      : `${n.count} ${region} notice${n.count === 1 ? '' : 's'} from ${when(n.from)} to ${when(n.to)}: `
        + `${c.plant || 0} name${c.plant === 1 ? 's' : ''} a plant in this region, ${c.unclear || 0} unclear`
        + (c.link ? `, ${c.link} name${c.link === 1 ? 's' : ''} an interconnection link` : '')
        + (c.region ? `, ${c.region} region-wide` : '')
        + (c.none ? `, ${c.none} with no plant matched` : '')
        + '. None is confirmed as the cause: '
        + 'no recorded event links any of them to this alert.'
        + (n.shown < n.count ? ` The ${n.shown} nearest the alert are listed.` : '');
    return { note, rows, rule: n.rule || '' };
  }

  /* Chart geometry: x by interval index (five minutes apart), y from the values that are present. */
  function scale(values, height, pad) {
    const present = values.filter(isNum);
    if (!present.length) return null;
    let lo = Math.min(0, ...present);  // prices start the axis at zero, or below it for a collapse
    let hi = Math.max(...present);
    if (hi === lo) hi = lo + 1;
    const step = Math.max(1, niceStep((hi - lo) / 4));  // MW and PHP/MWh are whole numbers: no 0.25 ticks
    lo = Math.floor(lo / step) * step;
    hi = Math.ceil(hi / step) * step;
    const ticks = [];
    for (let v = lo; v <= hi + step / 2; v += step) ticks.push(v);
    return { lo, hi, ticks, y: (v) => pad.top + (height - pad.top - pad.bottom) * (1 - (v - lo) / (hi - lo)) };
  }
  function niceStep(raw) {
    const p = Math.pow(10, Math.floor(Math.log10(raw || 1)));
    const m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }

  /* "What stood out" and "AI explanation" from one /api/alerts/explain answer, computed by the server
     from the replay data when the alert is opened. Families keep the server's order (ranked first, then
     the rest, each saying why it has no score); nothing is recomputed here. */
  const RK_TONE = (p) => (p === null ? 'none' : p >= 90 ? 'warn' : p >= 75 ? 'amber' : 'plain');
  const RK_PILL = { warn: 'bad', amber: 'warn', plain: '', none: '' };
  const RK_STATE = { 'not enough history': 'Not enough history', 'not in replay': 'Not in replay', 'no data': 'No data' };
  function explainView(body) {
    const b = body || {};
    const rows = (b.drivers || []).map((d) => {
      const pct = isNum(d.percentile) ? d.percentile : null;
      const cls = RK_TONE(pct);
      return {
        family: d.family, rank: isNum(d.rank) ? String(d.rank) : '–', name: d.name || d.family,
        text: d.text || 'No data', pct, bar: pct === null ? 0 : pct, cls, pill: RK_PILL[cls],
        state: pct !== null ? `Percentile ${pct}` : RK_STATE[d.status] || 'No data',
      };
    });
    const any = rows.some((r) => r.pct !== null);
    const at = b.interval_manila ? when(b.interval_manila) : null;
    const s = b.summary || {};
    const phrased = !!(b.phrased_by && b.phrased_by.model);
    const c = b.context;
    return {
      line: (at ? `At ${at} Manila, ${(c || {}).direction === 'collapse' ? 'the alert’s lowest price interval' : 'the alert’s peak price interval'}, against the same hour over the 28 days before. ` : '')
        + (any ? 'Ranked by how unusual each was.' : 'Nothing could be ranked for this interval from the replay data. Each family says why.'),
      rows,
      context: c && isNum(c.value) ? `Price at the interval (context, never a driver): ${num(c.value)} PHP/MWh`
        + (isNum(c.median) ? ` against a median of ${num(c.median)}` : '') + (isNum(c.percentile) ? `, percentile ${c.percentile}.` : '.') : null,
      basis: b.basis || 'Computed from the replay data when the alert is opened. Evidence, not proof.',
      paragraph: b.paragraph || 'No data.',
      note: phrased ? null : (b.note || 'The AI phrasing is not available yet. The text is composed by code.'),
      kv: [
        ['Severity (alert rule)', s.severity ? `${s.severity} · ${s.severity_reason || ''}`.replace(/ · $/, '') : 'No data'],
        ['Confidence', s.confidence ? `${s.confidence} · ${s.confidence_reason || ''}`.replace(/ · $/, '') : 'No data'],
        ['Financial impact', s.financial_impact || 'Not available: needs portfolio data'],
        ['Model', phrased ? `${b.phrased_by.model}, ${b.phrased_by.kind || 'phrased'}` : 'None: composed by code (no AI wording saved for these facts)'],
        ['Worded', b.as_of ? `${b.as_of.slice(0, 16).replace('T', ' ')} UTC` : 'Not worded by AI'],
      ],
      foot: phrased ? 'AI explanation · reworded from the code-composed facts and checked against them. It cannot add figures, names or a cause.'
        : 'Composed by code from the replay figures when the alert was opened. The paragraph claims no cause.',
    };
  }

  /* The full ontology card (/api/alerts/explain `ontology`, saved per alert by the batch and read from
     the deploy data; src/alerts/ontology.py holds the schema): the event page's likely-drivers card for
     this alert's peak interval and region, in three views. Everything is read from the card; nothing is
     ranked or scored here. A family the card leaves unscored says "No data", never a value. No table or
     script name, no fuel value, no peso figure; plant text keeps its words except technology words. */
  const OT_FAMILY = { D: 'Demand', S: 'Supply and interconnection', O: 'Outages', Rules: 'Rules and grid constraints', F: 'Fuel cost baseline' };
  const OT_ORDER = ['D', 'S', 'O', 'Rules', 'F'];
  const OT_MODES = [['assumed', 'As known at the time'], ['strict', 'Strict'], ['hindsight', 'Hindsight']];
  const OT_MODE_NOTE = {
    assumed: 'As known at the time: each market run is taken as published by its own interval (an assumption, not evidence).',
    strict: 'Strict: only facts with evidence of when they were known.',
    hindsight: 'Hindsight: everything recorded later is shown too, including facts nobody had at the time.',
  };
  const OT_IND = { demand_mw: 'demand', import_share: 'import share', hvdc_links_congested: 'HVDC links congested',
    reserve_shortfall_mw: 'reserve shortfall', scheduled_outage_mw: 'capacity scheduled out', linked_derated_mw: 'linked derated capacity',
    price_capped_median: 'capped median price', cap_bound: 'offer cap bound', admin_priced: 'administered price',
    price_mitigated: 'price mitigated', price_substituted: 'price substituted', secondary_cap: 'secondary cap',
    congested_elements: 'congested transmission elements', congestion_overload_mw: 'congestion overload',
    unlinked_congested_elements: 'congested elements not linked to a region', 'fuel cost baseline': 'fuel cost baseline' };
  const TECH = /\b(?:geo-?thermal\w*|thermal|solar|photo-?voltaic|pv|hydro\w*|hepp?|coal(?:-fired)?|diesel|bunker|fuel(?![- ]cost)|oil|gas|lng|ccgt|combined[- ]cycle|wind|biomass|bio\w*|battery|bess|nuclear|pumped[- ]storage|steam|hfo|cfpp|[dgsw]ppi?)\b/gi;
  const plainText = (s) => String(s == null ? '' : s).replace(TECH, '[…]').replace(/\[…\](?:[\s-]*\[…\])+/g, '[…]');
  const indName = (k) => OT_IND[k] || String(k || 'signal').replace(/_/g, ' ');
  const otVal = (v, unit) => {
    if (!isNum(v)) return null;
    if (unit === 'fraction') return num(v * 100, 1) + '%';
    if (unit === 'flag') return v ? 'set' : 'not set';
    const u = unit === 'links' ? (v === 1 ? ' link' : ' links') : unit === 'elements' ? (v === 1 ? ' element' : ' elements') : unit && unit !== 'count' ? ' ' + unit : '';
    return num(v, Math.abs(v) < 10 && v % 1 ? 1 : 0) + u;
  };
  const otState = (p) => (p === null ? ['No data', 'none', ''] : p >= 80 ? ['Unusual', 'warn', 'bad'] : p >= 55 ? ['Higher than usual', 'amber', 'warn']
    : p > 45 ? ['About usual', 'plain', ''] : ['Lower than usual', 'plain', 'info']);
  const otWords = (p, fam) => {
    const base = fam === 'F' ? 'its own monthly history' : 'the same hour on the 28 days before';
    return p >= 55 ? `higher than ${p}% of ${base}` : p <= 45 ? `lower than usual: only ${p}% of ${base} were lower` : `about usual (${p}%, in the middle of ${base})`;
  };
  /* '2026-10-05 05:40:00' (UTC, as the ontology records it) -> '5 Oct 13:40' Manila. */
  const manila = (s) => {
    const d = new Date(String(s || '').trim().replace(' ', 'T') + (/Z|[+-]\d\d:?\d\d$/.test(String(s || '')) ? '' : 'Z'));
    return Number.isNaN(d.getTime()) ? null : when(new Date(d.getTime() + 8 * 3600 * 1000).toISOString().slice(0, 16));
  };
  function ontologyModes(card) {
    const c = card || {};
    return OT_MODES.filter(([k]) => (c.modes || {})[k] || (c.drivers || {})[k]).map(([key, label]) => ({ key, label }));
  }
  function ontologyView(card, mode) {
    const c = card || {};
    const modes = ontologyModes(c);
    const m = modes.some((x) => x.key === mode) ? mode : (modes[0] || {}).key || 'assumed';
    const rows = Array.isArray((c.drivers || {})[m]) ? c.drivers[m].filter(Boolean) : [];
    const info = (c.modes || {})[m] || {};
    const families = OT_ORDER.map((fam) => {
      const mine = rows.filter((r) => r.family === fam);
      const scored = mine.filter((r) => r.status === 'scored' && isNum(r.rank) && isNum(r.family_score));
      const pct = scored.length ? Math.round(scored[0].family_score * 100) : null;
      const lead = scored.slice().sort((a, b) => (isNum(b.indicator_score) ? b.indicator_score : -1) - (isNum(a.indicator_score) ? a.indicator_score : -1))[0] || null;
      let text = 'No data at this cutoff';
      if (fam === 'F' && pct !== null) text = `Fuel cost baseline ${otWords(pct, 'F')}. Values not shown.`;
      else if (lead) {
        const v = otVal(lead.value_at_t, lead.unit), b = otVal(lead.baseline_median, lead.unit);
        text = `${indName(lead.indicator)} ${v || NA}${b ? ` against a 28-day median of ${b}` : ''}`;
      } else if (!mine.length) text = 'No data';
      const [state, cls, pill] = otState(pct);
      const signals = mine.filter((r) => r !== lead && ['scored', 'no data'].includes(r.status) && r.indicator && !(fam === 'F' && pct !== null)).map((r) => {
        if (fam === 'F') return `${indName(r.indicator)}: ${isNum(r.indicator_score) ? otWords(Math.round(r.indicator_score * 100), 'F') + ' (values not shown)' : 'No data at this cutoff'}.`;
        const v = otVal(r.value_at_t, r.unit), b = otVal(r.baseline_median, r.unit);
        const p = isNum(r.indicator_score) ? Math.round(r.indicator_score * 100) : null;
        return `${indName(r.indicator)}: ${v || 'No data at this cutoff'}${v && b ? ` against a 28-day median of ${b}` : ''}${p !== null && v ? `, ${otWords(p, fam)}` : ''}${isNum(r.baseline_n) && v ? ` (${num(r.baseline_n)} past intervals)` : ''}.`;
      });
      const flags = fam === 'Rules' ? mine.filter((r) => r.status === 'present' || r.status === 'absent') : [];
      const set = flags.filter((r) => r.status === 'present').map((r) => indName(r.indicator));
      const notSet = flags.length - set.length;
      if (flags.length) signals.push(`Pricing flags at the interval (listed, not scored): ${set.length ? set.join(', ') + ' set' : 'no flag set'}${notSet ? `, and ${notSet} other flag${notSet === 1 ? '' : 's'} not set` : ''}.`);
      const unlinked = mine.find((r) => r.status === 'flag count');
      if (unlinked && isNum(unlinked.value_at_t) && unlinked.value_at_t > 0) signals.push(`${num(unlinked.value_at_t)} congested elements at stations with no area code: not linked to a region, not counted.`);
      if (fam === 'O') signals.push('Counts planned outages only. A sudden trip is not in the outage schedule. It shows in the operator notices.');
      return { family: fam, name: OT_FAMILY[fam], rank: scored.length ? String(scored[0].rank) : '–', rankN: scored.length ? scored[0].rank : null,
        pct, bar: pct === null ? 0 : pct, cls, pill, state, text, signals };
    }).sort((a, b) => (a.rankN === null) - (b.rankN === null) || (a.rankN || 0) - (b.rankN || 0));
    const price = rows.find((r) => r.family === 'P' && r.indicator === 'price_capped_median');
    const facts = Array.isArray(info.facts) ? info.facts : [];
    const evidenced = facts.filter((f) => f.availability_at_cutoff === 'evidenced').length;
    const assumed = facts.filter((f) => f.availability_at_cutoff === 'assumed').length;
    const later = facts.filter((f) => f.availability_at_cutoff === 'after_cutoff').length;
    const withheld = (Array.isArray(info.withheld) ? info.withheld : []).reduce((n, w) => n + (isNum(Number(w.n)) ? Number(w.n) : 0), 0);
    const unconfirmed = (Array.isArray(info.unconfirmed) ? info.unconfirmed : []).map((u) => `${plainText(u.plant_text)}: ${plainText(u.reason)}`);
    const s = ((c.summaries || {})[m]) || (m === 'assumed' ? c.summary : null) || null;
    const ranked = families.some((f) => f.pct !== null);
    const cutoff = info.cutoff_utc ? manila(info.cutoff_utc) : null;
    return {
      mode: m, modes,
      heading: c.heading || 'Likely drivers (evidence, not proof)',
      line: `${c.interval_manila ? `At ${when(c.interval_manila)} Manila, ${c.direction === 'collapse' ? 'the alert’s lowest price interval' : 'the alert’s peak price interval'}` : 'At the alert’s peak interval'}`
        + `${cutoff ? `, what was known by ${cutoff}` : ''}. ${ranked ? 'Ranked by how unusual each was.' : 'Nothing could be ranked in this view. Each family says why.'}`,
      note: OT_MODE_NOTE[m] || '',
      families,
      context: price && isNum(price.value_at_t) ? `Price at the interval (context, never a driver): ${num(price.value_at_t)} PHP/MWh`
        + (isNum(price.baseline_median) ? ` against a 28-day median of ${num(price.baseline_median)} PHP/MWh` : '') + '.' : null,
      facts: `${facts.length} fact${facts.length === 1 ? '' : 's'} in this view: ${evidenced} with evidence of when known, ${assumed} assumed known by the cutoff`
        + `${later ? `, ${later} known only later` : ''}, ${withheld} held back as not yet known${isNum(info.fuel_context) && info.fuel_context ? `, ${info.fuel_context} fuel cost baseline row${info.fuel_context === 1 ? '' : 's'} (values not shown)` : ''}.`,
      unconfirmed,
      confidence: s && s.confidence ? `${s.confidence} (${facts.length ? Math.round((evidenced / facts.length) * 100) : 0}% of the facts with evidence of when known, ${withheld} held back, ${unconfirmed.length} unclear name${unconfirmed.length === 1 ? '' : 's'})` : 'No data',
      trail: s && s.relationship_trail && s.relationship_trail !== 'no ranked driver in this mode' ? plainText(s.relationship_trail) : null,
      check: s && Array.isArray(s.what_to_check) ? s.what_to_check.map(plainText) : [],
      basis: c.basis ? plainText(c.basis).replace(/\s*Evidence, not proof\.?$/, '') : 'Ontology record, checked by code before it was saved.',
    };
  }

  /* The full driver card's state (the explanation's `ontology_status`, src/alerts/ontology_live.py); the
     card itself is `ontology`, drawn by the likely-drivers card. The server's note is shown as given; a
     missing status reads as not available, never as computed. A baked card needs no line. */
  const ONTO_POLLS = 60;
  function ontologyStatus(status) {
    const o = status || { state: 'unavailable', note: 'Full driver card not available right now.' };
    const at = o.computed_at ? ' (' + String(o.computed_at).slice(0, 16).replace('T', ' ') + ' UTC)' : '';
    const lines = {
      ready: o.origin === 'computed' ? 'Full driver card: computed when this alert was first opened, and saved for everyone.'
        : o.origin === 'saved' ? `Full driver card: computed when this alert was first opened${at}, and saved.` : '',
      computing: o.note || 'Computing the full driver card…',
      sign_in: o.note || 'The full driver card has not been computed for this alert yet. Sign in to compute it.',
      unavailable: o.note || 'Full driver card not available right now.',
    };
    const state = o.state in lines ? o.state : 'unavailable';
    return { state, line: lines[state], poll: state === 'computing',
      wait: Math.max(2, Math.min(10, isNum(o.retry_after_s) ? o.retry_after_s : 3)) * 1000 };
  }

  const api = { summary, status, steps, related, scale, niceStep, explainView, ontologyView, ontologyModes, ontologyStatus, plainText, KEY };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  window.SpikePage = api;

  // ---------------------------------------------------------------- the page
  const $ = (id) => document.getElementById(id);
  const shell = () => window.GNShell || {};
  const SVG = 'http://www.w3.org/2000/svg';
  function el(tag, cls, text, parent) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = String(text);
    if (parent) parent.appendChild(n);
    return n;
  }
  function svg(tag, attrs, parent) {
    const n = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) n.setAttribute(k, String(v));
    if (parent) parent.appendChild(n);
    return n;
  }
  /* Notice text as the desk shows it; without the shell's redaction the text is not shown at all. */
  const noticeText = (s) => (typeof shell().opText === 'function' ? shell().opText(s) : 'Notice text unavailable.');

  const key = (() => {
    const last = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
    return KEY.test(last) ? last : null;
  })();
  const state = { answer: null, timer: null, ask: 0, ontMode: 'assumed' };

  const SEV_BADGE = { extreme: 'alert', high: 'alert', medium: 'warning', low: 'info' };
  const KIND_BADGE = { trip: 'alert', red: 'alert', yellow: 'warning', mld: 'warning', online: 'info', notice: 'info' };
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  function badge(cls, text, parent, title) {
    const b = el('span', 'gn-badge' + (cls ? ' ' + cls : ''), text, parent);
    if (title) b.title = title;
    return b;
  }
  /* The shared badge for a notice kind (GNUI.badge), or the same markup without ui.js. */
  function kindBadge(kind, parent) {
    const UI = window.GNUI;
    const node = UI && typeof UI.badge === 'function' ? UI.badge(kind in KIND ? kind : 'notice')
      : el('span', 'gn-badge gn-sev' + (KIND_BADGE[kind] ? ' gn-badge--' + KIND_BADGE[kind] : ' gn-badge--info'), KIND[kind] || 'Notice');
    parent.appendChild(node);
    return node;
  }
  const noticeHref = (id, t) => `/notices${/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(String(t || '')) ? '?at=' + String(t).slice(0, 16) : ''}#adv-${encodeURIComponent(id)}`;
  /* The recorded event the server matched, as a same-origin path, or null. */
  const eventPath = (c) => (c && typeof c.href === 'string' && /^\/event\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(c.href) ? c.href : null);

  /* A state the page cannot draw the alert in: what is missing and why, and the next action. */
  function show(title, body, action) {
    $('sp-body').hidden = true;
    const box = $('sp-state');
    box.hidden = false;
    box.textContent = '';
    const empty = el('div', 'gn-empty', null, box);
    el('p', 'gn-empty-title', title, empty);
    if (body) el('p', 'gn-empty-body', body, empty);
    if (action) {
      const row = el('div', 'gn-empty-actions', null, empty);
      const a = el('a', 'gn-btn', action.text, row);
      a.href = action.href;
    }
  }

  async function load() {
    if (!key) { show('This alert is not in the current alert rules', 'The address does not name an alert key.', { href: '/alerts', text: 'Open alerts' }); return; }
    const at = shell().asOf ? shell().asOf() : null;
    const ask = ++state.ask;
    let r = null, body = null;
    try {
      const headers = { Accept: 'application/json' };
      const token = shell().idToken ? await shell().idToken().catch(() => null) : null;
      if (token) headers.Authorization = 'Bearer ' + token;
      r = await fetch('/api/alerts/alert/' + key + (at ? '?at=' + encodeURIComponent(at) : ''), { headers, credentials: 'same-origin' });
      body = await r.json().catch(() => null);
    } catch (e) { r = null; }
    if (ask !== state.ask) return;  // the clock moved on; the newer request draws the page
    if (r && r.ok && body && body.status === 'ok') loadExplain(at, ask);
    if (!r) { show('The alert could not be read', 'Check the connection, then reload the page.', { href: location.pathname + location.search, text: 'Reload' }); return; }
    if (r.status === 404) { show('This alert is not in the current alert rules', 'The rules or the replay changed since this link was made.', { href: '/alerts', text: 'Open alerts' }); return; }
    if (!r.ok || !body) { show('The alert could not be read', `The server answered ${r.status}. Try again later.`, { href: '/alerts', text: 'Open alerts' }); return; }
    if (body.status === 'after_clock') {
      show(`This ${body.region_label || ''} alert starts after the replay time`.replace(/\s+/g, ' '),
        `It starts at ${when(body.first)}. The replay time is ${when(at || body.first)}, and nothing later is shown.`,
        { href: `/alert/${key}?at=${body.first}`, text: 'Go to its start' });
      return;
    }
    state.answer = body;
    render(body);
  }

  /* The explanation (never a model call on a page view): a failure leaves the cards saying so. The sign-in
     token goes with it: only a signed-in open may compute the full driver card, and while it computes
     the page asks again every few seconds (at most ONTO_POLLS times). */
  async function loadExplain(at, ask, polls) {
    let body = null;
    try {
      const headers = { Accept: 'application/json' };
      const token = shell().idToken ? await shell().idToken().catch(() => null) : null;
      if (token) headers.Authorization = 'Bearer ' + token;
      const r = await fetch('/api/alerts/explain/' + key + (at ? '?at=' + encodeURIComponent(at) : ''), { headers, credentials: 'same-origin' });
      body = r.ok ? await r.json().catch(() => null) : null;
    } catch (e) { body = null; }
    if (ask !== state.ask) return;
    const ok = body && body.status === 'ok' ? body : null;
    let v = ontologyStatus(ok ? ok.ontology_status : null);
    if (v.poll && (polls || 0) >= ONTO_POLLS) {
      v = ontologyStatus({ state: 'unavailable', note: 'Full driver card not available right now. The likely drivers above are computed from the replay data.' });
    }
    // the explanation once; again only when a card computed while the page waited has arrived
    if (!polls || (ok && ok.ontology && v.state === 'ready')) renderExplain(ok);
    renderOntologyStatus(v);
    if (v.poll) setTimeout(() => { if (ask === state.ask) loadExplain(at, ask, (polls || 0) + 1); }, v.wait);
  }

  /* One plain status line under the likely drivers: computing, sign in, not available, or saved. */
  function renderOntologyStatus(v) {
    const line = $('sp-onto-state');
    if (!line) return;
    line.textContent = v.line;
    line.hidden = !v.line;
    line.classList.toggle('sp-onto-busy', v.poll);
  }

  /* The saved ontology card, in the view the trader picked (as known at the time first). */
  function renderOntology(card) {
    const v = ontologyView(card, state.ontMode);
    state.ontMode = v.mode;
    $('sp-ranked-h').textContent = 'Likely drivers';
    $('sp-ranked-line').textContent = v.line;
    const modes = $('sp-ont-modes');
    modes.textContent = '';
    modes.hidden = v.modes.length < 2;
    for (const m of v.modes) {
      const b = el('button', null, m.label, modes);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(m.key === v.mode));
      b.addEventListener('click', () => { state.ontMode = m.key; renderOntology(card); });
    }
    const note = $('sp-ont-note');
    note.hidden = !v.note;
    note.textContent = v.note;
    const host = $('sp-ranked-rows');
    host.textContent = '';
    for (const x of v.families) {
      const row = el('div', 'sp-rk-row', null, host);
      const nm = el('span', 'sp-rk-name', null, row);
      el('span', 'sp-rk-n mono', x.rank, nm);
      el('b', null, x.name, nm);
      const mid = el('span', 'sp-rk-mid', null, row);
      el('span', 'sp-rk-text' + (x.pct === null ? ' sp-nodata' : ''), x.text, mid);
      const bar = el('progress', 'sp-rk-bar ' + x.cls, null, mid);
      bar.max = 100; bar.value = x.bar;
      bar.setAttribute('aria-label', x.pct === null ? `${x.name}: no score` : `${x.name}: ${x.pct}%`);
      if (x.signals.length) {
        const ul = el('ul', 'sp-rk-sig', null, mid);
        for (const t of x.signals) el('li', null, t, ul);
      }
      badge('sp-rk-pill' + (x.pill === 'bad' ? ' gn-badge--alert' : x.pill === 'warn' ? ' gn-badge--warning' : x.pill === 'info' ? ' gn-badge--info' : ''),
        x.pct === null ? x.state : `${x.state} · ${x.pct}%`, row);
    }
    const ctx = $('sp-ranked-ctx');
    ctx.hidden = !v.context;
    ctx.textContent = v.context || '';
    const more = $('sp-ont-more');
    more.textContent = '';
    const moreBox = $('sp-ont-more-box');
    if (moreBox) moreBox.hidden = false;
    const line = (k, t) => { const p = el('p', null, null, more); el('b', null, k + ': ', p); p.appendChild(document.createTextNode(t)); };
    if (v.trail) line('Relationship trail', noticeText(v.trail));
    line('Confidence', v.confidence);
    line('Facts', v.facts);
    if (v.unconfirmed.length) {
      line('Names not matched (under half sure, not counted)', String(v.unconfirmed.length));
      const ul = el('ul', null, null, more);
      for (const t of v.unconfirmed) el('li', null, noticeText(t), ul);
    }
    if (v.check.length) {
      line('What to check', '');
      const ul = el('ul', null, null, more);
      for (const t of v.check) el('li', null, noticeText(t), ul);
    }
    $('sp-ranked-src').textContent = v.basis + ' Evidence, not proof.';
  }

  function renderExplain(body) {
    if (body && body.ontology && typeof body.ontology === 'object') { renderOntology(body.ontology); renderAi(body); return; }
    const v = explainView(body);
    $('sp-ranked-line').textContent = body ? v.line : 'The likely drivers could not be read. No data.';
    const host = $('sp-ranked-rows');
    host.textContent = '';
    for (const x of body ? v.rows : []) {
      const row = el('div', 'sp-rk-row', null, host);
      const nm = el('span', 'sp-rk-name', null, row);
      el('span', 'sp-rk-n mono', x.rank, nm);
      el('b', null, x.name, nm);
      const mid = el('span', 'sp-rk-mid', null, row);
      el('span', 'sp-rk-text' + (x.pct === null ? ' sp-nodata' : ''), x.text, mid);
      const bar = el('progress', 'sp-rk-bar ' + x.cls, null, mid);
      bar.max = 100; bar.value = x.bar;
      bar.setAttribute('aria-label', x.pct === null ? `${x.name}: no score` : `${x.name}: ${x.pct}%`);
      badge('sp-rk-pill' + (x.pill === 'bad' ? ' gn-badge--alert' : x.pill === 'warn' ? ' gn-badge--warning' : ''), x.state, row);
    }
    const ctx = $('sp-ranked-ctx');
    ctx.hidden = !(body && v.context);
    ctx.textContent = body && v.context ? v.context : '';
    $('sp-ranked-src').textContent = body ? v.basis + ' Evidence, not proof.' : 'Ranked against the same hour over the 28 days before, at the peak interval. Evidence, not proof.';
    renderAi(body);
  }

  function renderAi(body) {
    const v = explainView(body);
    $('sp-ai-para').textContent = body ? v.paragraph : 'No data: the explanation could not be read.';
    const note = $('sp-ai-note');
    note.hidden = !(body && v.note);
    note.textContent = body && v.note ? v.note : '';
    const kv = $('sp-ai-kv');
    kv.textContent = '';
    for (const [k, val] of body ? v.kv : []) { el('dt', null, k, kv); el('dd', null, val, kv); }
    $('sp-ai-foot').textContent = v.foot;
  }

  function render(answer) {
    const a = answer.alert;
    const w = answer.around || {};
    const s = summary(answer);
    const st = status(answer);
    const sev = String(a.severity || 'unrated').toLowerCase();
    const region = a.region_label || a.region;
    const cause = a.cause && a.cause.title ? a.cause : null;
    const evPath = eventPath(cause);
    $('sp-state').hidden = true;
    $('sp-body').hidden = false;
    document.title = `${s.head} · Alerts · InGRID`;

    // the head: the anchor
    $('sp-title').textContent = s.head;
    $('sp-crumb').textContent = s.head;
    const n = isNum(a.intervals) ? a.intervals : null;
    $('sp-trigger').textContent = `${cap(a.threshold_text || 'past the saved level')}${n !== null ? ` for ${minutes(n * 5)}` : ''}.`;
    const pills = $('sp-pills');
    pills.textContent = '';
    badge('gn-sev gn-badge--' + (SEV_BADGE[sev] || 'info'), cap(sev), pills, a.severity_reason ? 'Severity: ' + a.severity_reason : null);
    const grid = el('a', 'sp-grid-link', region, pills);
    grid.href = '/?grid=' + encodeURIComponent(a.region || '');
    grid.setAttribute('data-entity', 'grid:' + (a.region || ''));
    el('span', 'gn-meta mono', span(a.first, a.last), pills);
    badge(st.live ? 'sp-live' : '', st.text, pills, st.live ? 'The last interval past the level is the replay time.' : null);
    const actions = $('sp-actions');
    actions.textContent = '';
    if (evPath) { const go = el('a', 'gn-btn gn-btn--primary', 'Open the event', actions); go.href = evPath; }
    const note = el('a', 'gn-btn' + (evPath ? '' : ' gn-btn--primary'), 'Add a note', actions);
    note.href = '#sp-journal';

    // the figures, unknowns on one line
    const kpis = $('sp-kpis');
    kpis.textContent = '';
    for (const t of s.tiles) {
      const box = el('div', 'gn-stat' + (t.key ? ' gn-stat--key' : ''), null, kpis);
      el('span', 'gn-label', t.k, box);
      const v = el('span', 'gn-value' + (t.key ? ' gn-value--lg' : ''), t.v, box);
      if (t.u) el('span', 'gn-unit', t.u, v);
      if (t.n) el('span', 'gn-meta', t.n, box);
    }
    drawAll();

    // the cause: only a recorded event the server matched
    const cb = $('sp-cause-body');
    cb.textContent = '';
    $('sp-cause-meta').textContent = cause ? 'recorded event' : 'none on record';
    if (cause) {
      const p = el('p', 'sp-cause-title', null, cb);
      if (evPath) { const link = el('a', null, cause.title, p); link.href = evPath; link.setAttribute('data-entity', 'event:' + evPath.slice(7)); }
      else p.textContent = cause.title;
      const meta = el('p', 'gn-meta sp-cause-meta', null, cb);
      meta.appendChild(document.createTextNode(cause.known_at ? `Known at ${when(cause.known_at)}` : 'Recorded event'));
      if (cause.advisory) {
        meta.appendChild(document.createTextNode(' from notice '));
        const id = el('a', 'mono', cause.advisory, meta);
        id.href = noticeHref(cause.advisory, cause.known_at);
        id.setAttribute('data-entity', 'notice:' + cause.advisory);
      }
      el('p', 'gn-meta', 'The event record matches this alert in region and time. Its own page holds the timeline and the decision.', cb);
    } else {
      el('p', 'sp-cause-none', 'No recorded event explains this alert.', cb);
      el('p', 'gn-meta', 'The notices below happened around the same time. None is claimed as the cause.', cb);
    }

    // around this time: the alert's own moments and the region's notices
    $('sp-around-note').textContent = `${region} notices from ${when(w.from || a.first)} to ${when(w.to || a.last)}, with the alert's own moments.`;
    const list = $('sp-steps');
    list.textContent = '';
    for (const x of steps(answer)) {
      const li = el('li', 'sp-step' + (x.notice ? '' : ' sp-step-alert'), null, list);
      const head = el('div', 'sp-step-head', null, li);
      el('span', 'sp-step-t mono', when(x.t), head);
      if (x.notice) kindBadge(x.kind, head); else badge('gn-badge--outline', x.label, head);
      if (x.id) {
        const id = el('a', 'sp-step-id mono', x.id, head);
        id.href = noticeHref(x.id, x.t);
        id.setAttribute('data-entity', 'notice:' + x.id);
      }
      if (x.id && cause && x.id === cause.advisory) el('span', 'gn-meta', 'opened the event', head);
      const text = el('div', 'sp-step-text', x.notice ? noticeText(x.text) : x.text, li);
      if (x.notice) text.title = noticeText(x.text);
    }
    if (!(w.notices || []).length) el('li', 'sp-none', `No ${region} notice in this window.`, list);
    renderRelated(answer);

    const made = $('sp-made');
    made.textContent = '';
    for (const line of [
      'Price: the region’s five-minute median price from the WESM replay.',
      'Usual: the same-hour median of the earlier replay days only. The first day has none.',
      answer.default_levels ? 'Level: the desk’s default levels. No alert rules are saved yet.' : `Level: the saved alert rules, version ${answer.rules_version}.`,
      `Window: ${w.minutes_either_side || 120} minutes either side of the alert, cut at the replay time (${when(w.clock || a.last)}).`,
      'Cause: shown only when a recorded event matches the alert in region and time.',
      'Notices: the system operator’s messages for this region, as posted. Technology words are withheld.',
      'Notices around this alert: the region’s outage, trip and grid notices from six hours before it, each labelled by how sure its plant match is. Under 50% sure is Unclear, and no plant is picked. None is a confirmed cause.',
      answer.ontology
        ? 'Likely drivers: the ontology card for this alert’s peak interval and region. Every fact carries the time it was known, ranked against the same hour over the 28 days before. It was computed once and checked by code before it was saved. The page never asks a model or the warehouse. Evidence, not proof.'
        : 'What stood out: the likely-drivers ranking at the peak interval, computed when this page opens. Evidence, not proof.',
      'Full driver card: the same ranking and facts from the full data warehouse, computed once when a signed-in user first opens the alert, then saved for everyone.',
      'AI explanation: composed by code. A Gemini wording shows only if one was saved and checked for exactly these facts.',
      'No forecast and no peso figure on this page.',
    ]) el('li', null, line, made);

    // The inbox wording sends the trader here ('Open the event to …'); on this page, drop that lead.
    const next = String(a.next_step || 'Review the interval and the notices around it.')
      .replace(/^Open the alert (?:to|and) (\w)/, (m, c) => c.toUpperCase());
    $('sp-next').textContent = next;
    mountJournal(answer);
  }

  function renderRelated(answer) {
    const host = $('sp-related-list');
    if (!host) return;
    const v = related(answer);
    $('sp-related-note').textContent = v.note;
    $('sp-related-rule').textContent = v.rule;
    host.textContent = '';
    for (const r of v.rows) {
      const li = el('li', 'sp-step sp-rel', null, host);
      const head = el('div', 'sp-step-head', null, li);
      el('span', 'sp-step-t mono', when(r.t), head);
      badge('', r.kind, head);
      badge(r.tone === 'info' ? 'gn-badge--info' : 'gn-badge--outline', r.match, head,
        r.tone === 'unclear' ? 'Under half sure of one plant: no plant is linked.' : null);
      badge('gn-badge--outline sp-rel-nc', 'Not confirmed as the cause', head);
      if (r.id) {
        const id = el(r.notice ? 'a' : 'span', 'sp-step-id mono', r.id, head);
        if (r.notice) { id.href = r.notice; id.setAttribute('data-entity', 'notice:' + r.id); }
      }
      const text = el('div', 'sp-step-text', noticeText(r.text), li);
      text.title = noticeText(r.text);
      el('div', 'sp-rel-why', `Why this label: ${r.reason}. ${r.timing[0].toUpperCase() + r.timing.slice(1)}.` + (r.rule ? ` ${r.rule}.` : ''), li);
      if (r.notice || r.plant) {
        const links = el('div', 'sp-rel-links', null, li);
        if (r.notice) { const x = el('a', null, 'Open the notice', links); x.href = r.notice; }
        if (r.plant) { const x = el('a', null, `Plant ${r.plant.code}`, links); x.href = r.plant.href; x.setAttribute('data-entity', 'plant:' + r.plant.code); }
      }
    }
    if (!v.rows.length) el('li', 'sp-none', 'Nothing to list.', host);
  }

  let journalFor = null;
  function mountJournal(answer) {
    if (journalFor === key) return;
    const host = $('sp-journal-box');
    if (!window.GNJournal || !window.GNJournal.mountBox) { host.textContent = 'The journal could not be loaded.'; return; }
    journalFor = key;
    window.GNJournal.mountBox(host, {
      kind: 'event', id: key, title: null,  // the card's own heading ("Your decision") names it
      snapshot: () => {
        const cur = state.answer || answer;
        const a = cur.alert;
        const notices = ((cur.around || {}).notices || []);
        const last = notices[notices.length - 1];
        return {
          price: isNum(a.price_php_mwh) ? a.price_php_mwh : null, region: a.region,
          latest_notice: last ? when(last.t) + ' · ' + noticeText(last.text) : null,
          known_facts: [summary(cur).title, `${a.threshold_text || ''} · ${span(a.first, a.last)}`,
            a.cause && a.cause.title ? `Recorded event: ${a.cause.title}` : 'No recorded event: no cause claimed'],
        };
      },
    });
  }

  // ---------------------------------------------------------------- charts
  function drawAll() {
    const answer = state.answer;
    if (!answer) return;
    const a = answer.alert;
    const w = answer.around || {};
    const t = w.t || [];
    const first = t.indexOf(a.first);
    const last = t.indexOf(a.last);
    const peak = t.indexOf(a.interval_manila);
    const legend = $('sp-price-legend');
    legend.textContent = '';
    const item = (cls, label) => { const s = el('span', 'sp-key', null, legend); el('i', 'sp-sw ' + cls, null, s); s.appendChild(document.createTextNode(label)); };
    item('sp-sw-price', 'Price');
    if ((w.level || []).some(isNum)) item('sp-sw-level', 'Alert level');
    if ((w.usual || []).some(isNum)) item('sp-sw-usual', 'Usual');
    item('sp-sw-span', 'Alert');
    chart($('sp-price'), t, [
      { values: w.price || [], cls: 'sp-line-price', name: 'Price', unit: 'PHP/MWh' },
      { values: w.level || [], cls: 'sp-line-level', name: 'Level', unit: 'PHP/MWh' },
      { values: w.usual || [], cls: 'sp-line-usual', name: 'Usual', unit: 'PHP/MWh' },
    ], { first, last, peak, height: 240 });
    const priceNote = !t.length ? 'No price in the record for this window.'
      : `Five-minute price, ${when(t[0])} to ${when(t[t.length - 1])}. The band is the alert. The dot is the ${a.direction === 'collapse' ? 'lowest' : 'peak'} price.`;
    $('sp-price-note').textContent = priceNote;
    const gaps = summary(answer).unknowns.slice();

    for (const [id, name, label] of [['short', 'reserve_short_mw', 'Reserve short'], ['demand', 'demand_mw', 'Demand']]) {
      const values = w[name] || [];
      const fig = $('sp-' + id + '-fig');
      const svgEl = $('sp-' + id);
      // A series the record does not carry gets no empty chart: it joins the unknowns line.
      fig.hidden = !values.some(isNum);
      if (fig.hidden) {
        svgEl.textContent = '';
        // one gap for the whole window, in place of the same series at the peak
        const atPeak = gaps.findIndex((g) => g.startsWith(label.toLowerCase() + ' at the peak'));
        if (atPeak >= 0) gaps.splice(atPeak, 1);
        gaps.push(`${label.toLowerCase()} in this window`);
        continue;
      }
      chart(svgEl, t, [{ values, cls: 'sp-line-' + id, name: label, unit: 'MW' }], { first, last, peak, height: 140, zero: true });
      const p = peak >= 0 && isNum(values[peak]) ? `${num(values[peak])} MW at the ${a.direction === 'collapse' ? 'lowest' : 'peak'} price.` : '';
      $('sp-' + id + '-note').textContent = `WESM five-minute data. ${p}`.trim();
    }
    $('sp-short-fig').parentNode.classList.toggle('sp-minis-one', $('sp-short-fig').hidden !== $('sp-demand-fig').hidden);
    const line = $('sp-unknowns');
    line.hidden = !gaps.length;
    line.textContent = gaps.length ? `Not on record: ${gaps.join(', ')}.` : '';
  }

  function chart(node, times, series, o) {
    node.textContent = '';
    const width = Math.max(260, Math.round(node.getBoundingClientRect().width || node.parentNode.clientWidth || 600));
    const height = o.height;
    const pad = { top: 12, right: 12, bottom: 24, left: 52 };
    node.setAttribute('viewBox', `0 0 ${width} ${height}`);
    node.setAttribute('height', String(height));
    const n = times.length;
    if (!n) return;
    const values = [].concat(...series.map((s) => s.values));
    const sc = scale(o.zero ? values.concat([0]) : values, height, pad);
    if (!sc) return;
    const x = (i) => pad.left + (n === 1 ? 0 : (width - pad.left - pad.right) * i / (n - 1));
    const grid = svg('g', { class: 'sp-grid' }, node);
    for (const v of sc.ticks) {
      svg('line', { x1: pad.left, x2: width - pad.right, y1: sc.y(v), y2: sc.y(v) }, grid);
      const label = svg('text', { x: pad.left - 6, y: sc.y(v) + 4, 'text-anchor': 'end', class: 'sp-axis' }, grid);
      label.textContent = Math.abs(v) >= 1000 ? num(v / 1000, 1) + 'k' : num(v);
    }
    // hour ticks along the bottom, thinned so labels never overlap
    const hours = [];
    for (let i = 0; i < n; i += 1) if (times[i].slice(14, 16) === '00') hours.push(i);
    const every = Math.max(1, Math.ceil(hours.length / Math.max(1, Math.floor((width - pad.left - pad.right) / 56))));
    hours.forEach((i, k) => {
      if (k % every) return;
      const label = svg('text', { x: x(i), y: height - 6, 'text-anchor': 'middle', class: 'sp-axis' }, grid);
      label.textContent = times[i].slice(11, 16);
    });
    if (o.first >= 0) {
      const x0 = x(o.first), x1 = o.last >= 0 ? x(o.last) : x0;
      svg('rect', { x: x0 - 2, y: pad.top, width: Math.max(4, x1 - x0 + 4), height: height - pad.top - pad.bottom, class: 'sp-span', rx: 2 }, node);
    }
    for (const s of series.slice().reverse()) {
      let d = '';
      let pen = false;
      s.values.forEach((v, i) => {
        if (!isNum(v)) { pen = false; return; }
        d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + sc.y(v).toFixed(1);
        pen = true;
      });
      if (d) svg('path', { d, class: 'sp-line ' + s.cls }, node);
    }
    const main = series[0];
    if (o.peak >= 0 && isNum(main.values[o.peak])) {
      svg('circle', { cx: x(o.peak), cy: sc.y(main.values[o.peak]), r: 4.5, class: 'sp-peak' }, node);
    }
    // hover: a crosshair and a small readout drawn in the chart itself
    const hover = svg('g', { class: 'sp-hover', visibility: 'hidden' }, node);
    const cross = svg('line', { y1: pad.top, y2: height - pad.bottom }, hover);
    const box = svg('rect', { rx: 4, class: 'sp-tip' }, hover);
    const lines = [svg('text', { class: 'sp-tip-t' }, hover)].concat(series.map(() => svg('text', { class: 'sp-tip-v' }, hover)));
    const hit = svg('rect', { x: pad.left, y: 0, width: Math.max(1, width - pad.left - pad.right), height, class: 'sp-hit' }, node);
    const move = (evt) => {
      const r = node.getBoundingClientRect();
      const px = (evt.clientX - r.left) * (width / (r.width || width));
      const i = Math.max(0, Math.min(n - 1, Math.round((px - pad.left) / ((width - pad.left - pad.right) / Math.max(1, n - 1)))));
      const xi = x(i);
      cross.setAttribute('x1', xi); cross.setAttribute('x2', xi);
      lines[0].textContent = when(times[i]);
      series.forEach((s, k) => { lines[k + 1].textContent = `${s.name}: ${isNum(s.values[i]) ? num(s.values[i]) + ' ' + s.unit : NA}`; });
      const tw = 170, th = 16 * lines.length + 8;
      const bx = xi + 10 + tw > width ? xi - 10 - tw : xi + 10;
      box.setAttribute('x', bx); box.setAttribute('y', pad.top); box.setAttribute('width', tw); box.setAttribute('height', th);
      lines.forEach((ln, k) => { ln.setAttribute('x', bx + 8); ln.setAttribute('y', pad.top + 16 + k * 16); });
      hover.setAttribute('visibility', 'visible');
    };
    hit.addEventListener('pointermove', move);
    hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', () => hover.setAttribute('visibility', 'hidden'));
  }

  function start() {
    if (!$('sp-state')) return;
    load();
    if (shell().onAsOf) shell().onAsOf(() => { clearTimeout(state.timer); state.timer = setTimeout(load, 300); });
    let resize = null;
    window.addEventListener('resize', () => { clearTimeout(resize); resize = setTimeout(drawAll, 150); });
    if (shell().onTheme) shell().onTheme(drawAll);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
