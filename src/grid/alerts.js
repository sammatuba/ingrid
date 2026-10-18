/* Alerts page (`/alerts`) and alert settings page (`/settings`). Contract:
   docs/work/alerts-portfolio-2026-10-17. One script drives both: `/alerts` holds the list of alerts
   (its search, filters and pages), `/settings` the one-off check, the email rules and levels, the
   alert history and the sign-in card. Each part is drawn only when its card is on the page.
   Sign-in is Firebase Auth (the vendored compat SDK): Google, or email and password (accounts the
   team creates, such as the judges'); every /api/alerts/* call carries
   `Authorization: Bearer <ID token>` when a user is signed in. With no signed-in user the
   page is read-only and the server withholds portfolio values and recipients.

   The first block (`AlertsLogic`) is pure: parsing, validation and the words the page shows.
   It touches no DOM, so tests/test_grid_alerts.py runs it under node. Everything the page
   writes is set as text (textContent), never as markup. */
(function (root) {
  'use strict';

  const REGIONS = [['CLUZ', 'Luzon'], ['CVIS', 'Visayas'], ['CMIN', 'Mindanao']];
  const REGION_CODES = REGIONS.map((r) => r[0]);
  const SEVERITIES = ['low', 'medium', 'high', 'extreme'];
  const FAMILY_NAMES = {D: 'Demand', S: 'Supply', P: 'Price', O: 'Outage', F: 'Fuel', R: 'Rules', B: 'Bids'};
  const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const DATE = /^\d{4}-\d{2}-\d{2}$/;

  const regionName = (code) => (REGIONS.find((r) => r[0] === code) || [code, code])[1];

  /* One row of 24 numbers from a spreadsheet paste: tabs, commas, semicolons or spaces. */
  function parseDemandPaste(text) {
    const parts = String(text || '').trim().split(/[\t,;\s]+/).filter((p) => p !== '');
    if (parts.length !== 24) return {error: `expected 24 values, found ${parts.length}`};
    const values = parts.map((p) => Number(p.replace(/_/g, '')));
    const bad = values.findIndex((v) => !Number.isFinite(v) || v < 0);
    if (bad >= 0) return {error: `hour ${bad} is not a non-negative number`};
    return {values};
  }

  /* "0-23", "18-21", "8,9,10" or "6-9,17-22" -> sorted unique hours 0..23. */
  function parseHours(text) {
    const s = String(text || '').trim();
    if (!s) return {error: 'hours are empty'};
    const hours = new Set();
    for (const part of s.split(',')) {
      const m = part.trim().match(/^(\d{1,2})(?:\s*-\s*(\d{1,2}))?$/);
      if (!m) return {error: `"${part.trim()}" is not an hour or a range`};
      const a = Number(m[1]); const b = m[2] === undefined ? a : Number(m[2]);
      if (a > 23 || b > 23 || b < a) return {error: `"${part.trim()}" is outside 0 to 23`};
      for (let h = a; h <= b; h += 1) hours.add(h);
    }
    return {hours: [...hours].sort((x, y) => x - y)};
  }

  /* The compact form of an hour list: [0..23] -> "0-23", [6,7,8,17] -> "6-8,17". */
  function formatHours(hours) {
    const sorted = [...(hours || [])].sort((a, b) => a - b);
    const out = [];
    for (let i = 0; i < sorted.length; i += 1) {
      let j = i;
      while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j += 1;
      out.push(i === j ? String(sorted[i]) : `${sorted[i]}-${sorted[j]}`);
      i = j;
    }
    return out.join(',');
  }

  const isNumber = (v) => typeof v === 'number' && Number.isFinite(v);

  /* The contract's portfolio validation, so a bad version is refused before it is sent. */
  function validatePortfolio(p) {
    const errors = [];
    if (!DATE.test(p.effective_from || '')) errors.push('Effective from needs a date.');
    if (!isNumber(p.benchmark_php_mwh) || p.benchmark_php_mwh < 0) errors.push('Benchmark needs a non-negative price.');
    const regions = p.regions || {};
    for (const [code, entry] of Object.entries(regions)) {
      if (!REGION_CODES.includes(code)) errors.push(`Unknown region ${code}.`);
      const d = entry && entry.demand_mw_by_hour;
      if (!Array.isArray(d) || d.length !== 24) errors.push(`${regionName(code)} demand needs 24 hourly values.`);
      else if (d.some((v) => !isNumber(v) || v < 0)) errors.push(`${regionName(code)} demand values must be non-negative numbers.`);
      const c = entry && entry.contracted_mw_by_hour;
      if (c === undefined) continue;
      if (!Array.isArray(c) || c.length !== 24) errors.push(`${regionName(code)} contracted by hour needs 24 hourly values.`);
      else if (c.some((v) => !isNumber(v) || v < 0)) errors.push(`${regionName(code)} contracted values must be non-negative numbers.`);
    }
    (p.contracts || []).forEach((c, i) => {
      const n = `Contract ${i + 1}${c.name ? ` (${c.name})` : ''}`;
      if (!String(c.name || '').trim()) errors.push(`${n}: name is empty.`);
      if (!REGION_CODES.includes(c.region)) errors.push(`${n}: choose a region.`);
      if (!isNumber(c.mw) || c.mw <= 0) errors.push(`${n}: MW must be above zero.`);
      if (!isNumber(c.price_php_mwh) || c.price_php_mwh < 0) errors.push(`${n}: price must be non-negative.`);
      if (!Array.isArray(c.hours) || !c.hours.length || c.hours.some((h) => !Number.isInteger(h) || h < 0 || h > 23)) errors.push(`${n}: hours must be between 0 and 23.`);
      if (!DATE.test(c.start || '') || !DATE.test(c.end || '')) errors.push(`${n}: start and end need dates.`);
      else if (c.start > c.end) errors.push(`${n}: start is after end.`);
    });
    (p.nodes || []).forEach((nd, i) => {
      if (!String(nd.code || '').trim()) errors.push(`Node ${i + 1}: code is empty.`);
      if (!REGION_CODES.includes(nd.region)) errors.push(`Node ${i + 1}: choose a region.`);
    });
    if (!Object.keys(regions).length && !(p.contracts || []).length) errors.push('Enter demand for at least one region or at least one contract.');
    return errors;
  }

  function validateRules(r) {
    const errors = [];
    const t = r.threshold || {};
    if (!['absolute', 'ratio_to_baseline'].includes(t.mode)) errors.push('Choose how the threshold is set.');
    if (!isNumber(t.value) || t.value <= 0) errors.push('The threshold value must be above zero.');
    if (!Array.isArray(r.regions) || !r.regions.length || r.regions.some((c) => !REGION_CODES.includes(c))) errors.push('Choose at least one region.');
    if (!SEVERITIES.includes(r.min_severity)) errors.push('Choose the lowest severity.');
    errors.push(...validateLevels(r.levels, t));
    const seen = new Set();
    (r.recipients || []).forEach((x, i) => {
      const n = `Recipient ${i + 1}`;
      const email = String(x.email || '').trim().toLowerCase();
      if (!EMAIL.test(email)) errors.push(`${n}: "${x.email || ''}" is not an email address.`);
      else if (seen.has(email)) errors.push(`${n}: ${email} is listed twice.`);
      seen.add(email);
      if (!Array.isArray(x.regions) || !x.regions.length || x.regions.some((c) => !REGION_CODES.includes(c))) errors.push(`${n}: choose at least one region.`);
      if (!SEVERITIES.includes(x.min_severity)) errors.push(`${n}: choose the lowest severity.`);
    });
    return errors;
  }

  /* Per-region levels (E22), as the server checks them: a spike multiple above 1 (at most 100), a
     collapse multiple between 0 and 1, a spike price above 0; in the same mode the collapse level
     must sit below the spike level (the region's own, or the shared rule). Returns error lines. */
  function validateLevels(levels, threshold) {
    const errors = [];
    if (levels === undefined) return errors;
    if (!levels || typeof levels !== 'object' || Array.isArray(levels)) return ['Levels must be set per region.'];
    for (const [code, entry] of Object.entries(levels)) {
      if (!REGION_CODES.includes(code)) { errors.push(`Unknown region ${code}.`); continue; }
      const name = regionName(code);
      const check = (lv, dir) => {
        if (lv === null || lv === undefined) return null;
        if (!['absolute', 'ratio_to_baseline'].includes(lv.mode)) { errors.push(`${name} ${dir}: choose a price or a multiple of usual.`); return null; }
        const v = lv.value;
        if (!isNumber(v)) { errors.push(`${name} ${dir}: enter a number.`); return null; }
        if (lv.mode === 'ratio_to_baseline' && dir === 'spike' && !(v > 1 && v <= 100)) errors.push(`${name} spike: a multiple of usual above 1 and at most 100.`);
        else if (lv.mode === 'ratio_to_baseline' && dir === 'collapse' && !(v > 0 && v < 1)) errors.push(`${name} collapse: a multiple of usual above 0 and below 1.`);
        else if (lv.mode === 'absolute' && dir === 'spike' && !(v > 0 && v <= 1e6)) errors.push(`${name} spike: a price above 0 PHP/MWh.`);
        else if (lv.mode === 'absolute' && dir === 'collapse' && !(v >= -1e6 && v <= 1e6)) errors.push(`${name} collapse: a price in PHP/MWh.`);
        else return lv;
        return null;
      };
      const spike = check(entry && entry.spike, 'spike');
      const collapse = check(entry && entry.collapse, 'collapse');
      const effective = spike || threshold;
      if (collapse && effective && collapse.mode === effective.mode && !(collapse.value < effective.value)) errors.push(`${name} collapse: below the spike level.`);
    }
    return errors;
  }

  /* The levels a region uses, in words, for the inbox and the rules table. */
  function levelText(direction, lv) {
    if (!lv) return direction === 'collapse' ? 'no collapse level' : '';
    const side = direction === 'collapse' ? 'at or below' : 'at or above';
    return lv.mode === 'ratio_to_baseline' ? `${side} ${lv.value}× usual` : `${side} ${Math.round(lv.value).toLocaleString('en-US')} PHP/MWh`;
  }

  /* The alerts list (ericka-desk): every alert up to the as-of clock, one row each, from the
     inbox answer. An alert keeps its own cause, or its group's; none is claimed otherwise. */
  function flattenInbox(r) {
    const out = [];
    for (const g of (r && r.groups) || []) {
      for (const a of g.alerts || []) out.push(Object.assign({}, a, {cause: a.cause || (g.alerts.length === 1 ? g.cause : null) || null}));
    }
    return out;
  }

  /* The replay time floored to its five-minute interval, the grain an alert's `last` is kept at. */
  function intervalOf(at) {
    const m = String(at || '').match(/^(\d{4}-\d{2}-\d{2}T\d{2}):(\d{2})/);
    return m ? `${m[1]}:${String(Math.floor(Number(m[2]) / 5) * 5).padStart(2, '0')}` : '';
  }

  /* In force: the alert's last interval past the level is the replay time's own interval (or later,
     which the server never sends past the clock). An alert that ended earlier is history. */
  function inForce(a, at) {
    const now = intervalOf(at);
    return Boolean(now && a && String(a.last || '').slice(0, 16) >= now);
  }

  /* The glance band: alerts in force by severity, the replay day's and all days' counts, and the one
     to look at first (the worst in force, else the latest). Counts only: no figure is computed. */
  function glance(list, at) {
    const rows = (list || []).filter(Boolean);
    const now = rows.filter((a) => inForce(a, at));
    const bySeverity = {};
    for (const a of now) { const s = String(a.severity || 'unrated').toLowerCase(); bySeverity[s] = (bySeverity[s] || 0) + 1; }
    const day = pickAlerts(rows, {days: 'day', at}).length;
    const worst = pickAlerts(now, {sort: 'worst'})[0] || null;
    const latest = pickAlerts(rows, {sort: 'newest'})[0] || null;
    return {now: now.length, bySeverity, day, all: rows.length, focus: worst || latest, focusInForce: Boolean(worst)};
  }

  /* The list's groups, in the order the rows come: by the day the alert started, by its recorded
     cause (alerts with none share one group), or one group with no heading. */
  function groupAlerts(rows, by) {
    if (by !== 'day' && by !== 'cause') return [{key: 'all', label: null, rows: (rows || []).slice()}];
    const groups = new Map();
    for (const a of rows || []) {
      const day = String(a.first || a.interval_manila || '').slice(0, 10);
      const key = by === 'day' ? day : (a.cause && a.cause.id ? 'event:' + a.cause.id : 'none');
      if (!groups.has(key)) {
        groups.set(key, {key, rows: [], cause: by === 'cause' ? (a.cause || null) : null,
          label: by === 'day' ? dayText(day) : (a.cause && a.cause.title ? a.cause.title : 'No recorded cause')});
      }
      groups.get(key).rows.push(a);
    }
    return [...groups.values()];
  }

  const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function dayText(day) {
    const m = String(day || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return String(day || '');
    const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${WEEKDAYS[d.getUTCDay()]} ${Number(m[3])} ${months[Number(m[2]) - 1]}`;
  }

  /* The list's filters as the address keeps them (`?grid=CVIS&level=high&q=trip`): defaults are left
     out, unknown values fall back to the default, and other parameters (`at`, `alert`) are kept. */
  const LIST_DEFAULTS = {grid: 'all', level: 'all', dir: 'all', cause: 'all', days: 'all', group: 'day', sort: 'newest', q: ''};
  const LIST_VALUES = {grid: ['all', ...REGION_CODES], level: ['all', ...SEVERITIES], dir: ['all', 'spike', 'collapse'],
    cause: ['all', 'yes', 'no'], days: ['all', 'day'], group: ['day', 'cause', 'none'], sort: ['newest', 'worst']};
  const LIST_FILTERS = ['grid', 'level', 'dir', 'cause', 'days', 'q'];
  function listFromSearch(search) {
    const p = new URLSearchParams(String(search || '').replace(/^\?/, ''));
    const out = Object.assign({}, LIST_DEFAULTS);
    for (const k of Object.keys(LIST_VALUES)) { const v = p.get(k); if (v && LIST_VALUES[k].includes(v)) out[k] = v; }
    out.q = String(p.get('q') || '').slice(0, 120);
    return out;
  }
  function listToSearch(f, search) {
    const p = new URLSearchParams(String(search || '').replace(/^\?/, ''));
    for (const k of Object.keys(LIST_DEFAULTS)) {
      const v = k === 'q' ? String(f[k] || '').trim() : f[k];
      if (v && v !== LIST_DEFAULTS[k]) p.set(k, v); else p.delete(k);
    }
    const s = p.toString();
    return s ? '?' + s : '';
  }
  /* How many filters differ from their defaults (view options, grouping and order, are not filters). */
  function activeFilters(f, keys) {
    return (keys || LIST_FILTERS).filter((k) => (k === 'q' ? String(f.q || '').trim() !== '' : f[k] !== LIST_DEFAULTS[k])).length;
  }

  const SEVERITY_RANK = {extreme: 0, high: 1, medium: 2, low: 3};
  /* The alerts to show: in the grid, level and direction asked for, on the as-of day when
     days = 'day', with or without a recorded cause, matching the search; newest or worst first. */
  function pickAlerts(list, f) {
    f = f || {};
    const q = String(f.q || '').trim().toLowerCase();
    const day = String(f.at || '').slice(0, 10);
    const any = (v) => !v || v === 'all';
    const rows = (list || []).filter((a) => a
      && (any(f.grid) || a.region === f.grid)
      && (any(f.level) || String(a.severity || 'unrated').toLowerCase() === f.level)
      && (any(f.dir) || (a.direction === 'collapse' ? 'collapse' : 'spike') === f.dir)
      && (f.days !== 'day' || !day || String(a.first || a.interval_manila || '').slice(0, 10) === day
        || String(a.last || '').slice(0, 10) === day)
      && (any(f.cause) || (f.cause === 'yes' ? Boolean(a.cause) : !a.cause))
      && (!q || [regionName(a.region), a.region, a.direction, a.severity, a.severity_reason, a.threshold_text, a.main_driver,
        a.cause && a.cause.title, a.cause && a.cause.advisory, intervalText(a.first || a.interval_manila), ...(a.facts || [])]
        .some((v) => String(v || '').toLowerCase().includes(q))));
    const t = (a) => String(a.last || a.first || a.interval_manila || '');
    const newest = (x, y) => (t(x) < t(y) ? 1 : t(x) > t(y) ? -1 : 0);
    const worst = (x, y) => ((SEVERITY_RANK[x.severity] ?? 9) - (SEVERITY_RANK[y.severity] ?? 9)) || newest(x, y);
    return rows.sort(f.sort === 'worst' ? worst : newest);
  }

  const peso = (v) => '₱' + Math.round(Math.abs(v)).toLocaleString('en-US');
  const price = (v) => (isNumber(v) ? Math.round(v).toLocaleString('en-US') + ' PHP/MWh' : 'price unknown');

  /* The impact line, from the server's figure only: the page never computes one. */
  function impactText(fi) {
    if (!fi) return 'Not available';
    if (fi.hidden) return 'Hidden until you sign in';
    if (!isNumber(fi.php)) return fi.status || 'Not available: no portfolio entered';
    const over = isNumber(fi.over_contracted_mw) && fi.over_contracted_mw > 0
      ? fi.over_contracted_mw : (isNumber(fi.unhedged_mw) && fi.unhedged_mw < 0 ? -fi.unhedged_mw : 0);
    const volume = over > 0 ? `over-contracted by ${over.toFixed(1)} MW`
      : (isNumber(fi.unhedged_mw) ? `unhedged ${fi.unhedged_mw.toFixed(1)} MW` : '');
    const word = fi.php > 0 ? 'cost above benchmark' : (fi.php < 0 ? 'gain against benchmark' : 'no difference from benchmark');
    const sign = fi.php < 0 ? '−' : '';
    return `${sign}${peso(fi.php)} ${word}${volume ? ` (${volume})` : ''}${fi.basis ? ` · ${fi.basis}` : ''}`;
  }

  function thresholdText(t) {
    if (!t) return '';
    return t.mode === 'ratio_to_baseline' ? `${t.value}× the 28-day same-hour median` : `${price(t.value)}`;
  }

  function intervalText(iso) {
    const m = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    if (!m) return String(iso || '');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${Number(m[3])} ${months[Number(m[2]) - 1]} ${m[1]} ${m[4]}:${m[5]}`;
  }

  /* The grid page's address (`#t=HH:MM&g=CVIS`, the replay day 21 Sep 2026; `d=YYYY-MM-DD` may name
     another day) -> the check's region and interval; anything else -> the PEDC case. */
  function checkDefaults(hash) {
    const h = new URLSearchParams(String(hash || '').replace(/^#/, ''));
    const g = h.get('g'); const t = h.get('t'); const d = h.get('d');
    const region = REGION_CODES.includes(g) ? g : 'CVIS';
    const day = DATE.test(d || '') ? d : '2026-09-21';
    const time = /^([01]\d|2[0-3]):[0-5]\d$/.test(t || '') && Number(t.slice(3)) % 5 === 0 ? t : '13:40';
    return {region, interval: `${day}T${time}`};
  }

  /* The link an alert may carry, as a same-origin path: a recorded event (`/event/<id>`), the
     alert's own page when no event explains it (`/alert/<24-hex key>`), or the public site's own
     absolute form of either. Anything else (another host, a scheme, a query) gives no link. */
  function safeEventPath(url) {
    let s = String(url || '').trim();
    const own = s.match(/^https:\/\/(?:ingrid-desk|grid-nowcast)\.web\.app(\/.*)$/);
    if (own) s = own[1];
    if (/^\/event\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(s)) return s;
    if (/^\/alert\/[0-9a-f]{24}$/.test(s)) return s;
    if (/^\/alerts\?alert=[0-9a-f]{8,64}$/.test(s)) return s;
    return null;
  }

  /* Where an alert that is not in the list is found: its row in the settings page's history. */
  function settingsHistoryHref(key) {
    return /^[0-9a-f]{8,64}$/.test(String(key || '')) ? `/settings?alert=${key}#history-card` : '/settings#history-card';
  }

  /* The alert a page address names (`/alerts?alert=<key>`), or null. */
  function alertFromSearch(search) {
    const key = new URLSearchParams(String(search || '').replace(/^\?/, '')).get('alert');
    return key && /^[0-9a-f]{8,64}$/.test(key) ? key : null;
  }

  /* The alert's own page (`/alert/<24-hex key>`), where every alert opens (flow F2: the inbox, then
     the alert, then its event). An alert without a page key keeps the link it carries, if safe. */
  function alertPagePath(a) {
    if (a && /^[0-9a-f]{24}$/.test(String(a.key || ''))) return '/alert/' + a.key;
    return a ? safeEventPath(a.href) : null;
  }

  /* An alert's window in words: `28 Sep 18:35–19:00`, or both days when it crosses midnight. */
  function windowText(a) {
    const first = String((a && (a.first || a.interval_manila)) || '');
    const last = String((a && a.last) || '');
    const start = intervalText(first).replace(/ \d{4} /, ' ');
    if (!last || last === first) return start;
    return start + '–' + (last.slice(0, 10) === first.slice(0, 10) ? last.slice(11, 16) : intervalText(last).replace(/ \d{4} /, ' '));
  }

  /* A refusal's field (`benchmark_php_mwh`, `regions.CVIS.demand_mw_by_hour`, `contracts[2].mw`,
     `recipients[0].email`, `threshold.value`, ...) -> where it is on the page: an element id, or a
     table row / demand block to mark. */
  function fieldTarget(field) {
    const f = String(field || '');
    const ids = {effective_from: 'pf-effective', benchmark_php_mwh: 'pf-benchmark', note: 'pf-note',
      enabled: 'rl-enabled', regions: 'rl-regions', min_severity: 'rl-severity',
      interval_manila: 'check-interval', region: 'check-region'};
    if (ids[f]) return {id: ids[f]};
    if (/^threshold\./.test(f)) return {id: 'rl-value'};
    if (/^levels\b/.test(f)) return {id: 'rl-levels'};
    let m = f.match(/^regions\.(CLUZ|CVIS|CMIN)\.contracted_mw_by_hour\b/);
    if (m) return {contracted: m[1]};
    m = f.match(/^regions\.(CLUZ|CVIS|CMIN)\b/);
    if (m) return {demand: m[1]};
    m = f.match(/^(contracts|nodes|recipients)\[(\d+)\]/);
    if (m) return {table: {contracts: 'pf-contracts', nodes: 'pf-nodes', recipients: 'rl-recipients'}[m[1]], row: Number(m[2])};
    return null;
  }

  /* The portfolio import's draft in words: its window, the units and who stated them, and what was
     left out. Region totals only; the draft carries no name, ID or node. */
  function draftSummary(d) {
    if (!d || !d.window || !d.units) return '';
    const u = d.units;
    const left = d.left_out || {};
    const parts = [`Imported from the contract (BCQ) and meter (MQ) data, ${d.window.first} to ${d.window.last} (${d.window.days} days): the hourly average.`,
      `Units: meters ${u.mq}, contracts ${u.bcq} per 5 minutes, ${u.stated_by ? `stated by ${u.stated_by}` : 'unconfirmed'}.`];
    if (left.bcq_nodes_without_meters) {
      const mw = isNumber(left.bcq_mw_without_meters) ? ` (${left.bcq_mw_without_meters.toFixed(1)} MW on average)` : '';
      parts.push(`Left out: contracts at ${left.bcq_nodes_without_meters} node${left.bcq_nodes_without_meters === 1 ? '' : 's'} with no meter data${mw}, so unhedged MW may read higher than it is.`);
    }
    if (left.unmapped_nodes) parts.push(`${left.unmapped_nodes} node${left.unmapped_nodes === 1 ? '' : 's'} outside the region list, not counted.`);
    if ((left.regions_missing_hours || []).length) parts.push(`Not filled (an hour with no meter data): ${left.regions_missing_hours.map(regionName).join(', ')}.`);
    return parts.join(' ');
  }

  /* How long to wait before the next poll of a running check: the poll interval, cut to the time left
     before the limit; null once the limit is reached (no request is sent past it). */
  function nextPollDelay(startedMs, nowMs, intervalMs, limitMs) {
    const left = limitMs - (nowMs - startedMs);
    return left <= 0 ? null : Math.min(intervalMs, left);
  }

  const logic = {nextPollDelay, safeEventPath, alertFromSearch, settingsHistoryHref, fieldTarget, checkDefaults, REGIONS, REGION_CODES, SEVERITIES, FAMILY_NAMES, regionName, parseDemandPaste, parseHours,
    formatHours, draftSummary, validatePortfolio, validateRules, validateLevels, levelText, flattenInbox, pickAlerts,
    impactText, thresholdText, intervalText, price, intervalOf, inForce, glance, groupAlerts, dayText,
    listFromSearch, listToSearch, activeFilters, LIST_DEFAULTS, alertPagePath, windowText};
  /* DM-5 round 2: an inbox answer read at `readAt` may be shown at the clock `clock` only when it
     was read at or before the clock: an answer read later states alerts' later ends and peaks. */
  logic.readFits = (readAt, clock) => !clock || (typeof readAt === 'string' && readAt <= clock);
  root.AlertsLogic = logic;
  if (typeof module !== 'undefined' && module.exports) module.exports = logic;
})(typeof window !== 'undefined' ? window : globalThis);

(function () {
  'use strict';
  if (typeof document === 'undefined') return;
  const L = window.AlertsLogic;
  const $ = (id) => document.getElementById(id);
  /* Which page this is: the list (`/alerts`) or the settings (`/settings`). */
  const HAS_LIST = Boolean($('inbox-card'));
  const HAS_SETTINGS = Boolean($('rules-card'));
  // The portfolio card (Sam's, alerts-portfolio-2026-10-17) sits on the settings page.
  const HAS_PORTFOLIO = Boolean($('portfolio-card'));
  const state = {user: null, auth: null, config: null, editable: false, loadError: null, authNote: '', running: false, importSource: null, view: 'all'};
  const POLL_MS = 3000;
  const POLL_LIMIT_MS = 180000;
  let fieldCount = 0;

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of children) if (c !== null && c !== undefined) node.append(c);
    if ((tag === 'input' || tag === 'select') && !node.name && !node.id) node.name = 'f' + (++fieldCount);
    return node;
  }
  const clear = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };
  const notice = (text, kind) => { const n = $('notice'); if (!n) return; n.textContent = text || ''; n.className = 'notice' + (kind ? ' ' + kind : ''); };

  /* ---- API ---------------------------------------------------------------------------- */
  async function call(method, path, body) {
    const headers = {'Accept': 'application/json'};
    if (state.user) headers.Authorization = 'Bearer ' + await state.user.getIdToken();
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch('/api/alerts/' + path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: 'same-origin'});
    let data = null;
    try { data = await response.json(); } catch (e) { data = null; }
    if (!response.ok) {
      const message = (data && (data.message || data.reason || data.code)) || `The server answered ${response.status}.`;
      const err = new Error(typeof message === 'string' ? message : JSON.stringify(message));
      err.status = response.status;
      err.code = data && data.code;
      err.field = data && data.field;
      throw err;
    }
    return data;
  }

  /* ---- sign-in ------------------------------------------------------------------------ */
  async function startAuth() {
    if (!window.firebase || !window.firebase.auth) { state.authNote = 'Sign-in could not load on this page.'; return render(); }
    let cfg;
    try { cfg = await call('GET', 'client-config'); } catch (e) {
      state.authNote = e.status === 503 ? 'Sign-in is not set up on this server.' : `Sign-in is unavailable here (${e.message.replace(/\.$/, '')}).`;
      return render();
    }
    try {
      const app = window.firebase.apps.length ? window.firebase.app() : window.firebase.initializeApp({apiKey: cfg.apiKey, authDomain: cfg.authDomain, projectId: cfg.projectId});
      state.auth = app.auth();
    } catch (e) { state.authNote = 'Sign-in could not start.'; return render(); }
    if ($('sign-in')) $('sign-in').hidden = false;
    state.auth.onAuthStateChanged((user) => {
      const usable = user && !user.isAnonymous &&
        (user.providerData || []).some((p) => p && (p.providerId === 'google.com' || p.providerId === 'password'));
      const was = state.user;
      state.user = usable ? user : null;
      if (state.user) startSession(state.user);
      else if (was) endSession();
      load();
    });
  }

  /* DOCK-5: the same-origin session every other page reads (GET /api/agent/whoami). After a
     sign-in this page posts the ID token once to POST /api/agent/session, which answers with an
     HttpOnly cookie no script can read; on sign-out it asks POST /api/agent/session/end to clear
     it. This page's own sign-in never waits on either, and a failure changes nothing here. */
  async function startSession(user) {
    try {
      const token = await user.getIdToken();
      await fetch('/api/agent/session', {method: 'POST', credentials: 'same-origin',
        headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
        body: JSON.stringify({id_token: token})});
    } catch (e) { /* the other pages stay signed out; this page is unchanged */ }
  }

  async function endSession() {
    try {
      await fetch('/api/agent/session/end', {method: 'POST', credentials: 'same-origin',
        headers: {'Accept': 'application/json'}});
    } catch (e) { /* the cookie expires on its own */ }
  }

  async function signIn() {
    if (!state.auth) return;
    try {
      const provider = new window.firebase.auth.GoogleAuthProvider();
      provider.setCustomParameters({prompt: 'select_account'});
      await state.auth.signInWithPopup(provider);
    } catch (e) {
      if (e && e.code === 'auth/popup-closed-by-user') return;
      notice('Sign-in did not complete: ' + ((e && e.message) || 'unknown error'), 'bad');
    }
  }

  /* Email and password: Firebase's error codes in plain words; the password is never shown or kept. */
  const PASSWORD_ERRORS = {
    'auth/invalid-credential': 'Email or password is wrong.',
    'auth/invalid-login-credentials': 'Email or password is wrong.',
    'auth/wrong-password': 'Email or password is wrong.',
    'auth/user-not-found': 'Email or password is wrong.',
    'auth/invalid-email': 'That email address is not valid.',
    'auth/missing-password': 'Enter the password.',
    'auth/user-disabled': 'This account is turned off.',
    'auth/too-many-requests': 'Too many attempts. Wait a few minutes, then try again.',
    'auth/network-request-failed': 'No connection to the sign-in service. Check the network and try again.',
    'auth/operation-not-allowed': 'Email and password sign-in is not turned on for this site.',
  };
  function passwordError(e) {
    return PASSWORD_ERRORS[e && e.code] || 'Sign-in did not complete. Try again.';
  }

  async function signInPassword(ev) {
    ev.preventDefault();
    const email = $('pw-email').value.trim();
    const pw = $('pw-password').value;
    $('pw-password').value = '';  // emptied on every submit, before any early return
    $('pw-error').textContent = '';
    if (!state.auth) return;
    if (!email || !pw) { $('pw-error').textContent = 'Enter the email and the password.'; return; }
    $('pw-submit').disabled = true;
    try {
      await state.auth.signInWithEmailAndPassword(email, pw);
    } catch (e) {
      $('pw-error').textContent = passwordError(e);
    } finally {
      $('pw-password').value = '';
      $('pw-submit').disabled = false;
    }
  }

  /* ---- load and render ---------------------------------------------------------------- */
  async function load() {
    renderAccount();
    if (HAS_SETTINGS) {
      try {
        state.config = await call('GET', 'config');
        state.loadError = null;
      } catch (e) {
        state.config = null;
        state.loadError = 'Could not load the settings: ' + e.message;
      }
      state.editable = Boolean(state.user && state.config && state.config.signed_in);
    }
    render();
    if (HAS_SETTINGS) loadHistory();
    if (HAS_LIST) loadInbox(true);
  }

  function renderAccount() {
    if ($('who')) $('who').textContent = state.user ? (state.user.email || 'Signed in') : '';
    if ($('sign-in')) $('sign-in').hidden = !state.auth || Boolean(state.user);
    if ($('sign-out')) $('sign-out').hidden = !state.user;
    if (state.user && $('pw-error')) $('pw-error').textContent = '';
    renderBanner();
  }

  /* Signed out on /settings: one banner says the page is read only, and offers the one sign-in
     action when this server has sign-in. Where it has none, the banner says so and offers nothing. */
  function renderBanner() {
    const card = $('signin-card');
    if (!card) return;
    card.hidden = Boolean(state.user);
    if (state.user) return;
    const can = Boolean(state.auth);
    const line = $('signin-line');
    if (line) {
      line.textContent = can ? 'Signed out, the rules show without recipients. Sign in to save rules and run checks.'
        : state.authNote ? `${state.authNote} The rules show without recipients. Nothing can be saved here.`
          : 'Signed out, the rules show without recipients. Checking whether sign-in is available.';
    }
    if ($('signin-title')) $('signin-title').textContent = can || !state.authNote ? 'Sign in to change these settings' : 'No sign-in on this server';
    if ($('signin-open')) $('signin-open').hidden = !can;
    if (!can && $('pw-form')) $('pw-form').hidden = true;
  }

  function openSignIn() {
    const form = $('pw-form');
    if (!form || !state.auth) return;
    form.hidden = !form.hidden;
    $('signin-open').setAttribute('aria-expanded', String(!form.hidden));
    if (!form.hidden) $('pw-email').focus();
  }

  function render() {
    renderAccount();
    if (!HAS_SETTINGS) return;  // the list page has no settings to draw
    const cfg = state.config || {};
    $('rules-fields').disabled = !state.editable;
    if (HAS_PORTFOLIO) $('portfolio-fields').disabled = !state.editable;
    $('check-run').disabled = !state.editable || state.running || cfg.checks_available === false;
    if (state.loadError) {
      notice(state.loadError, 'bad');
    } else if (!state.editable) {
      // Signed out, the banner says it all; signed in without the right, the notice says so.
      notice(state.user ? 'This account cannot change the alert settings.' : '', state.user ? 'warn' : '');
    } else if (cfg.checks_available === false) {
      notice('Checks are not available on this server: the settings can be saved, but no check runs.', 'warn');
    } else if (cfg.email_status && cfg.email_status !== 'configured') {
      notice('Email sending is not configured on the server yet: checks run, but no email is sent.', 'warn');
    } else notice('');
    if (HAS_PORTFOLIO) {
      renderPortfolio(cfg.portfolio);
      $('pf-import').hidden = !(state.editable && cfg.import_available);
    }
    renderRules(cfg.rules);
  }

  /* Portfolio ------------------------------------------------------------------------- */
  function renderPortfolio(p) {
    const box = $('portfolio-versions'); clear(box);
    const latest = p && p.latest;
    if (!p) $('portfolio-current').textContent = 'No portfolio entered yet';
    else if (latest) $('portfolio-current').textContent = `Version ${latest.version}, effective ${latest.effective_from}`;
    else if (p.present) $('portfolio-current').textContent = `Version ${p.version}, effective ${p.effective_from} · values hidden until you sign in`;
    if (p && Array.isArray(p.versions) && p.versions.length) {
      const rows = p.versions.slice().sort((a, b) => b.version - a.version).map((v) =>
        el('tr', {}, el('td', {class: 'num', text: String(v.version)}), el('td', {class: 'mono', text: v.effective_from}),
          el('td', {text: v.saved_by || ''}), el('td', {class: 'mono', text: (v.saved_at || '').replace('T', ' ').slice(0, 16)})));
      box.append(el('div', {class: 'table-wrap'}, el('table', {class: 'list'},
        el('caption', {text: 'Versions'}),
        el('thead', {}, el('tr', {}, ...['Version', 'Effective from', 'Saved by', 'Saved at (UTC)'].map((h) => el('th', {scope: 'col', text: h})))),
        el('tbody', {}, ...rows))));
    }
    fillPortfolioForm(latest || null);
  }

  function demandBlock(code, values, kind) {
    const what = kind === 'contracted' ? 'contracted' : 'demand';
    const inputs = [];
    const grid = el('div', {class: 'hours'});
    for (let h = 0; h < 24; h += 1) {
      const input = el('input', {type: 'number', min: '0', step: 'any', inputmode: 'decimal', 'aria-label': `${L.regionName(code)} ${what}, hour ${h}`, 'data-region': code, 'data-hour': String(h)});
      if (values && typeof values[h] === 'number') input.value = String(values[h]);
      inputs.push(input);
      grid.append(el('label', {class: 'hour'}, el('span', {class: 'mono', text: String(h).padStart(2, '0')}), input));
    }
    const paste = el('input', {type: 'text', class: 'paste', placeholder: 'Paste 24 values', 'aria-label': `Paste ${L.regionName(code)} ${what}, 24 values`});
    const msg = el('span', {class: 'hint', 'aria-live': 'polite'});
    paste.addEventListener('input', () => {
      if (!paste.value.trim()) { msg.textContent = ''; return; }
      const r = L.parseDemandPaste(paste.value);
      if (r.error) { msg.textContent = r.error; msg.className = 'hint bad'; return; }
      r.values.forEach((v, h) => { inputs[h].value = String(v); });
      paste.value = ''; msg.textContent = '24 values filled'; msg.className = 'hint ok';
    });
    const clearBtn = el('button', {type: 'button', class: 'btn ghost small', text: 'Clear', onclick: () => { inputs.forEach((i) => { i.value = ''; }); msg.textContent = ''; }});
    return el('div', {class: 'region-demand', 'data-region': code},
      el('div', {class: 'rd-head'}, el('strong', {text: L.regionName(code)}), paste, clearBtn, msg), grid);
  }

  function regionSelect(value, label) {
    const s = el('select', {'aria-label': label});
    s.append(el('option', {value: '', text: 'Region'}));
    for (const [code, name] of L.REGIONS) { const o = el('option', {value: code, text: name}); if (code === value) o.selected = true; s.append(o); }
    return s;
  }

  function removeButton(label, row) {
    return el('button', {type: 'button', class: 'gn-icon-btn st-remove', 'aria-label': label, title: label, onclick: () => row.remove()}, '×');
  }

  function contractRow(c) {
    c = c || {};
    const row = el('tr');
    const cell = (node) => el('td', {}, node);
    const n = el('input', {type: 'text', 'aria-label': 'Contract name', value: c.name || ''});
    const mw = el('input', {type: 'number', min: '0', step: 'any', 'aria-label': 'Contract MW', value: c.mw ?? ''});
    const pr = el('input', {type: 'number', min: '0', step: 'any', 'aria-label': 'Contract price, PHP/MWh', value: c.price_php_mwh ?? ''});
    const hr = el('input', {type: 'text', class: 'mono', 'aria-label': 'Contract hours', placeholder: '0-23', value: c.hours ? L.formatHours(c.hours) : ''});
    const st = el('input', {type: 'date', 'aria-label': 'Contract start', value: c.start || ''});
    const en = el('input', {type: 'date', 'aria-label': 'Contract end', value: c.end || ''});
    row.append(cell(n), cell(regionSelect(c.region, 'Contract region')), cell(mw), cell(pr), cell(hr), cell(st), cell(en));
    row.append(cell(removeButton('Remove contract', row)));
    return row;
  }

  function nodeRow(nd) {
    nd = nd || {};
    const row = el('tr');
    row.append(el('td', {}, el('input', {type: 'text', class: 'mono', 'aria-label': 'Node code', value: nd.code || ''})),
      el('td', {}, regionSelect(nd.region, 'Node region')),
      el('td', {}, el('input', {type: 'text', 'aria-label': 'Node label', value: nd.label || ''})));
    row.append(el('td', {}, removeButton('Remove node', row)));
    return row;
  }

  function fillPortfolioForm(p) {
    $('pf-effective').value = (p && p.effective_from) || new Date().toISOString().slice(0, 10);
    $('pf-benchmark').value = p && typeof p.benchmark_php_mwh === 'number' ? String(p.benchmark_php_mwh) : '';
    $('pf-note').value = '';
    const demand = $('pf-demand'); clear(demand);
    for (const [code] of L.REGIONS) demand.append(demandBlock(code, p && p.regions && p.regions[code] && p.regions[code].demand_mw_by_hour));
    fillContracted(p && p.regions);
    state.importSource = (p && p.source) || null;
    $('pf-import-note').textContent = state.importSource ? `This version was filled from the import (BCQ/MQ to ${state.importSource.window.last}).` : '';
    const ct = $('pf-contracts').tBodies[0]; clear(ct);
    for (const c of (p && p.contracts) || []) ct.append(contractRow(c));
    const nt = $('pf-nodes').tBodies[0]; clear(nt);
    for (const nd of (p && p.nodes) || []) nt.append(nodeRow(nd));
    if (p && p.nodes && p.nodes.length) $('pf-nodes-box').open = true;
    clear($('pf-errors'));
  }

  /* Contracted MW by hour: shown only when the import is on or the version carries a profile, so a
     portfolio typed by hand looks as before. */
  function fillContracted(regions) {
    const box = $('pf-contracted'); clear(box);
    const any = regions && Object.values(regions).some((r) => r && Array.isArray(r.contracted_mw_by_hour));
    for (const [code] of L.REGIONS) box.append(demandBlock(code, regions && regions[code] && regions[code].contracted_mw_by_hour, 'contracted'));
    $('pf-contracted-box').hidden = !(any || (state.config && state.config.import_available));
  }

  async function fillFromImport() {
    if (!state.editable) return;
    $('pf-import').disabled = true;
    try {
      const d = await call('GET', 'portfolio/draft');
      const regions = d.regions || {};
      const demand = $('pf-demand'); clear(demand);
      for (const [code] of L.REGIONS) demand.append(demandBlock(code, regions[code] && regions[code].demand_mw_by_hour));
      fillContracted(regions);
      $('pf-contracted-box').hidden = false;
      $('pf-contracts').tBodies[0].replaceChildren();
      state.importSource = {kind: 'import', built_at: d.built_at, window: {first: d.window.first, last: d.window.last, days: d.window.days},
        units: {mq: d.units.mq, bcq: d.units.bcq, stated_by: d.units.stated_by || null}};
      $('pf-import-note').textContent = L.draftSummary(d) + ' Check the numbers, set the benchmark and the date, then save. Nothing is saved yet.';
      if (!$('pf-note').value.trim()) $('pf-note').value = `Imported BCQ/MQ ${d.window.first} to ${d.window.last}`;
      notice('Filled from the imported data. Nothing is saved until you press Save.', 'ok');
    } catch (e) {
      notice('Could not fill from the import: ' + e.message, 'bad');
    } finally { $('pf-import').disabled = false; }
  }

  const num = (input) => (input.value.trim() === '' ? NaN : Number(input.value));

  function readPortfolio() {
    const errors = [];
    const regions = {};
    for (const block of $('pf-demand').querySelectorAll('.region-demand')) {
      const code = block.getAttribute('data-region');
      const inputs = [...block.querySelectorAll('input[data-hour]')];
      const filled = inputs.filter((i) => i.value.trim() !== '');
      if (!filled.length) continue;
      regions[code] = {demand_mw_by_hour: inputs.map(num)};
    }
    if (!$('pf-contracted-box').hidden) {
      for (const block of $('pf-contracted').querySelectorAll('.region-demand')) {
        const code = block.getAttribute('data-region');
        const inputs = [...block.querySelectorAll('input[data-hour]')];
        if (!inputs.some((i) => i.value.trim() !== '')) continue;
        if (!regions[code]) { errors.push(`${L.regionName(code)}: contracted by hour needs that region's demand too.`); continue; }
        regions[code].contracted_mw_by_hour = inputs.map(num);
      }
    }
    const contracts = [...$('pf-contracts').tBodies[0].rows].map((row) => {
      const [n, rg, mw, pr, hr, st, en] = row.querySelectorAll('input, select');
      const h = L.parseHours(hr.value);
      if (h.error) errors.push(`Contract "${n.value || '?'}": ${h.error}.`);
      return {name: n.value.trim(), region: rg.value, mw: num(mw), price_php_mwh: num(pr), hours: h.hours || [], start: st.value, end: en.value};
    });
    const nodes = [...$('pf-nodes').tBodies[0].rows].map((row) => {
      const [code, rg, label] = row.querySelectorAll('input, select');
      return {code: code.value.trim(), region: rg.value, label: label.value.trim()};
    });
    const p = {effective_from: $('pf-effective').value, benchmark_php_mwh: num($('pf-benchmark')), note: $('pf-note').value.trim(), regions, contracts};
    if (nodes.length) p.nodes = nodes;
    if (state.importSource) p.source = state.importSource;
    return {portfolio: p, errors: errors.concat(L.validatePortfolio(p))};
  }

  function showErrors(id, errors) {
    const ul = $(id); clear(ul);
    for (const e of errors) ul.append(el('li', {text: e}));
  }

  function clearMarks() {
    for (const n of document.querySelectorAll('.invalid')) { n.classList.remove('invalid'); n.removeAttribute('aria-invalid'); }
  }

  /* A refusal (`{code, message, field?, reason?}`): its message said where the form is, and for a
     422 the field it names marked and focused. */
  function refused(listId, e) {
    showErrors(listId, [e.message]);
    if (e.status !== 422) return;
    const t = L.fieldTarget(e.field);
    let node = null;
    if (t && t.id) node = $(t.id);
    else if (t && t.demand) node = document.querySelector(`#pf-demand .region-demand[data-region="${t.demand}"]`);
    else if (t && t.contracted) node = document.querySelector(`#pf-contracted .region-demand[data-region="${t.contracted}"]`);
    else if (t && t.table) node = $(t.table).tBodies[0].rows[t.row] || null;
    if (!node) return;
    node.classList.add('invalid'); node.setAttribute('aria-invalid', 'true');
    const focus = node.matches('input, select') ? node : node.querySelector('input, select');
    if (focus) focus.focus();
  }

  async function savePortfolio(event) {
    event.preventDefault();
    if (!state.editable) return;
    const {portfolio, errors} = readPortfolio();
    clearMarks();
    showErrors('pf-errors', errors);
    if (errors.length) return;
    $('pf-save').disabled = true;
    try {
      const r = await call('PUT', 'portfolio', portfolio);
      await load();
      notice(`Portfolio version ${r.version} saved.`, 'ok');
    } catch (e) { refused('pf-errors', e); }
    finally { $('pf-save').disabled = false; }
  }

  /* Rules ------------------------------------------------------------------------------ */
  function regionChecks(selected, name) {
    const box = el('div', {class: 'checks'});
    for (const [code, label] of L.REGIONS) {
      const input = el('input', {type: 'checkbox', value: code, 'aria-label': `${name}: ${label}`});
      input.checked = !selected || selected.includes(code);
      box.append(el('label', {class: 'st-check'}, input, ' ' + label));
    }
    return box;
  }

  function severitySelect(value, label) {
    const s = el('select', {class: 'gn-select', 'aria-label': label});
    for (const v of L.SEVERITIES) { const o = el('option', {value: v, text: v[0].toUpperCase() + v.slice(1)}); if (v === (value || 'high')) o.selected = true; s.append(o); }
    return s;
  }

  function recipientRow(x) {
    x = x || {};
    const row = el('tr');
    row.append(el('td', {}, el('input', {type: 'email', class: 'gn-input st-email', 'aria-label': 'Recipient email', autocomplete: 'off', value: x.email || ''})),
      el('td', {}, regionChecks(x.regions, 'Recipient region')),
      el('td', {}, severitySelect(x.min_severity, 'Recipient lowest severity')));
    row.append(el('td', {}, removeButton('Remove recipient', row)));
    return row;
  }

  function renderRules(r) {
    const latest = r && (r.version !== undefined ? r : r.latest);
    $('rules-current').textContent = latest && latest.version !== undefined
      ? `Version ${latest.version}${latest.saved_by ? `, saved by ${latest.saved_by}` : ''}${latest.enabled === false ? ' · emails off' : ''}`
      : 'No rules saved yet';
    $('rl-enabled').checked = !latest || latest.enabled !== false;
    const mode = (latest && latest.threshold && latest.threshold.mode) || 'absolute';
    for (const radio of document.querySelectorAll('input[name="rl-mode"]')) radio.checked = radio.value === mode;
    $('rl-value').value = latest && latest.threshold ? String(latest.threshold.value) : '15000';
    const regions = $('rl-regions'); clear(regions); regions.append(regionChecks(latest && latest.regions, 'Rule region'));
    $('rl-severity').value = (latest && latest.min_severity) || 'high';
    renderLevels(latest && latest.levels);
    const tb = $('rl-recipients').tBodies[0]; clear(tb);
    if (latest && Array.isArray(latest.recipients) && latest.recipients.length) for (const x of latest.recipients) tb.append(recipientRow(x));
    else if (!(latest && typeof latest.recipients_count === 'number')) tb.append(el('tr', {class: 'st-none'}, el('td', {colspan: '4', class: 'st-empty-cell', text: 'No recipients yet.'})));
    else if (latest && typeof latest.recipients_count === 'number') tb.append(el('tr', {}, el('td', {colspan: '4', class: 'st-empty-cell', text: `${latest.recipients_count} recipient${latest.recipients_count === 1 ? '' : 's'} (hidden until you sign in)`})));
    clear($('rl-errors'));
  }

  /* Levels by region (E22): one row per region; "Shared" spike uses the rule above, "Off" collapse has none. */
  function levelCells(code, dir, lv) {
    const modes = dir === 'spike' ? [['', 'Shared'], ['absolute', 'Price'], ['ratio_to_baseline', 'Multiple of usual']]
      : [['', 'Off'], ['absolute', 'Price'], ['ratio_to_baseline', 'Multiple of usual']];
    const name = `${L.regionName(code)} ${dir}`;
    const select = el('select', {class: 'lv-mode gn-select', 'data-region': code, 'data-dir': dir, 'aria-label': `${name}: how`});
    for (const [v, label] of modes) { const o = el('option', {value: v, text: label}); if (v === ((lv && lv.mode) || '')) o.selected = true; select.append(o); }
    const value = el('input', {class: 'lv-value gn-input st-num', type: 'number', step: 'any', inputmode: 'decimal', 'aria-label': `${name}: value`, value: lv ? String(lv.value) : ''});
    value.disabled = !lv;
    select.addEventListener('change', () => { value.disabled = !select.value; if (!select.value) value.value = ''; });
    return [el('td', {}, select), el('td', {class: 'num'}, value)];
  }

  function renderLevels(levels) {
    const tb = $('rl-levels').tBodies[0]; clear(tb);
    for (const [code, label] of L.REGIONS) {
      const own = (levels || {})[code] || {};
      tb.append(el('tr', {'data-region': code}, el('th', {scope: 'row', text: label}),
        ...levelCells(code, 'spike', own.spike), ...levelCells(code, 'collapse', own.collapse)));
    }
  }

  function readLevels() {
    const out = {};
    for (const row of $('rl-levels').tBodies[0].rows) {
      const code = row.dataset.region;
      const entry = {spike: null, collapse: null};
      for (const select of row.querySelectorAll('select.lv-mode')) {
        if (!select.value) continue;
        const input = select.closest('td').nextElementSibling.querySelector('input');
        entry[select.dataset.dir] = {mode: select.value, value: num(input)};
      }
      if (entry.spike || entry.collapse) out[code] = entry;
    }
    return Object.keys(out).length ? out : undefined;
  }

  function readRules() {
    const checked = (box) => [...box.querySelectorAll('input[type=checkbox]')].filter((i) => i.checked).map((i) => i.value);
    const mode = (document.querySelector('input[name="rl-mode"]:checked') || {}).value;
    const recipients = [...$('rl-recipients').tBodies[0].rows].filter((row) => row.querySelector('input[type=email]')).map((row) => ({
      email: row.querySelector('input[type=email]').value.trim(), regions: checked(row), min_severity: row.querySelector('select').value}));
    const rules = {enabled: $('rl-enabled').checked, threshold: {mode, value: num($('rl-value'))}, regions: checked($('rl-regions')), min_severity: $('rl-severity').value, recipients};
    const levels = readLevels();
    if (levels) rules.levels = levels;
    return {rules, errors: L.validateRules(rules)};
  }

  async function saveRules(event) {
    event.preventDefault();
    if (!state.editable) return;
    const {rules, errors} = readRules();
    clearMarks();
    showErrors('rl-errors', errors);
    if (errors.length) return;
    $('rl-save').disabled = true;
    try {
      const r = await call('PUT', 'rules', rules);
      await load();
      notice(`Notification rules version ${r.version} saved.`, 'ok');
    } catch (e) { refused('rl-errors', e); }
    finally { $('rl-save').disabled = false; }
  }

  async function testEmail() {
    if (!state.editable) return;
    $('rl-test').disabled = true;
    try {
      const r = await call('POST', 'test-email', {});
      const sent = (r && r.sent_to) || [];
      if (r && r.email === 'not configured') notice('Email sending is not configured on the server yet.', 'warn');
      else notice(sent.length ? `Test email sent to ${sent.join(', ')}.` : 'No recipients to send to. Add one and save the rules first.', sent.length ? 'ok' : 'warn');
    } catch (e) { notice('Test email failed: ' + e.message, 'bad'); }
    finally { $('rl-test').disabled = !state.editable; }
  }

  /* Run check -------------------------------------------------------------------------- */
  function alertCard(a) {
    const drivers = el('ol', {class: 'drivers'});
    for (const d of a.likely_drivers || []) {
      const score = typeof d.score === 'number' ? d.score : null;
      const bar = el('span', {class: 'bar-track', 'aria-hidden': 'true'}, el('span', {class: 'bar-fill w' + (score === null ? 0 : Math.round(Math.max(0, Math.min(1, score)) * 20))}));
      drivers.append(el('li', {},
        el('span', {class: 'fam', text: d.family_label || L.FAMILY_NAMES[d.family] || d.family || '?'}),
        el('span', {class: 'num', text: score === null ? 'no data' : score.toFixed(2)}), bar,
        d.why ? el('span', {class: 'why', text: d.why}) : null));
    }
    const sev = String(a.severity || 'unrated').toLowerCase();
    const checks = el('ul', {class: 'to-check'});
    for (const c of [].concat(a.what_to_check || [])) checks.append(el('li', {text: c}));
    const fields = el('dl', {class: 'fields'},
      el('dt', {text: 'Confidence'}), el('dd', {text: a.confidence || 'Not stated'}),
      el('dt', {text: 'Relationship trail'}), el('dd', {text: a.relationship_trail || 'Not stated'}),
      el('dt', {text: 'What to check'}), el('dd', {}, checks),
      el('dt', {text: 'Threshold'}), el('dd', {text: a.threshold_text || L.thresholdText(a.threshold) || 'Not stated'}));
    const eventPath = L.safeEventPath(a.event_url);
    const emailed = Array.isArray(a.emailed_to) && a.emailed_to.length ? `Emailed to ${a.emailed_to.join(', ')}`
      : (typeof a.emailed_to === 'number' && a.emailed_to > 0 ? `Emailed to ${a.emailed_to} recipient${a.emailed_to === 1 ? '' : 's'}` : (a.sent_at ? 'Emailed' : 'Not emailed'));
    return el('article', {class: 'st-alert sev-' + sev},
      el('header', {class: 'st-alert-head'},
        badge(sev),
        el('strong', {text: `${L.regionName(a.region)} · ${L.price(a.price_php_mwh)}`}),
        el('span', {class: 'gn-meta mono', text: L.intervalText(a.interval_manila)})),
      el('h3', {class: 'gn-label', text: 'Likely drivers, evidence not proof'}), drivers, fields,
      el('p', {class: 'gn-meta'}, emailed, eventPath ? ' · ' : '', eventPath ? el('a', {href: eventPath, text: eventPath.startsWith('/alerts') ? 'Link to this alert' : eventPath.startsWith('/alert/') ? 'Open the alert' : 'Open the event'}) : null));
  }

  function runSummary(r) {
    const alerts = (r && r.alerts) || [];
    return `${r.checked ?? 0} interval${r.checked === 1 ? '' : 's'} checked · ${alerts.length} alert${alerts.length === 1 ? '' : 's'} · ${r.emailed ?? 0} email${r.emailed === 1 ? '' : 's'} sent${typeof r.bytes_billed === 'number' ? ` · ${(r.bytes_billed / 1e6).toFixed(1)} MB of BigQuery` : ''}`;
  }

  function showRun(out, r) {
    clear(out);
    const alerts = (r && r.alerts) || [];
    out.append(el('p', {class: 'gn-meta st-run-summary', text: runSummary(r)}));
    if (!alerts.length) {
      const c = ((r && r.candidates) || [])[0];
      out.append(el('p', {text: c && c.price !== undefined && c.price !== null
        ? `No alert. The price was ${L.price(c.price)}.${c.threshold_text ? ` The rule is ${c.threshold_text}.` : ''}${c.crossed === false ? ' It was not crossed.' : ''}`
        : 'No alert. The interval did not cross the level, or its severity is below the lowest level set.'}));
    }
    for (const note of (r && r.notes) || []) out.append(el('p', {class: 'gn-meta', text: String(note)}));
    for (const a of alerts) out.append(alertCard(a));
  }

  async function runCheck(event) {
    event.preventDefault();
    if (!state.editable || state.running) return;
    const out = $('check-result'); clear(out);
    clearMarks(); showErrors('check-errors', []);
    const interval = $('check-interval').value;
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(interval) || Number(interval.slice(-2)) % 5 !== 0) {
      out.append(el('p', {class: 'st-bad', text: 'Choose an interval on a five-minute mark, for example 13:40.'})); return;
    }
    state.running = true; $('check-run').disabled = true;
    const status = el('p', {class: 'gn-meta running', role: 'status', text: 'Checking… about 30 to 60 s while BigQuery builds the driver card.'});
    out.append(status);
    const started = Date.now();
    const tick = setInterval(() => { status.textContent = `Checking… ${Math.round((Date.now() - started) / 1000)} s of about 30 to 60 while BigQuery builds the driver card.`; }, 1000);
    try {
      let r = await call('POST', 'run', {region: $('check-region').value, interval_manila: interval, send: $('check-send').checked});
      const stillRunning = () => {
        clear(out); out.append(el('p', {class: 'st-warn', text: 'The check is still running after 3 minutes. Its result will appear in the recent alerts when it finishes.'}));
      };
      while (r && r.status === 'running') {
        const delay = L.nextPollDelay(started, Date.now(), POLL_MS, POLL_LIMIT_MS);
        if (delay === null) { stillRunning(); return; }
        await new Promise((res) => setTimeout(res, delay));
        if (L.nextPollDelay(started, Date.now(), POLL_MS, POLL_LIMIT_MS) === null) { stillRunning(); return; }
        r = await call('GET', 'runs/' + encodeURIComponent(r.id));
      }
      showRun(out, r);
      loadHistory();
    } catch (e) {
      clear(out); out.append(el('p', {class: 'st-bad', text: 'The check failed: ' + e.message}));
      if (e.status === 422) refused('check-errors', e);
    } finally {
      clearInterval(tick);
      state.running = false;
      $('check-run').disabled = !state.editable || (state.config && state.config.checks_available === false);
    }
  }

  /* History ---------------------------------------------------------------------------- */
  async function loadHistory() {
    const tb = $('history').tBodies[0];
    let items = [];
    try { const r = await call('GET', 'history'); items = Array.isArray(r) ? r : ((r && r.alerts) || []); } catch (e) { items = null; }
    clear(tb);
    if (items === null) { tb.append(el('tr', {}, el('td', {colspan: '7', class: 'st-empty-cell st-bad', text: 'History is unavailable. The server did not answer.'}))); return; }
    if (!items.length) { tb.append(el('tr', {}, el('td', {colspan: '7', class: 'st-empty-cell', text: 'No alerts yet. A check or a replay alert lands here.'}))); return; }
    for (const a of items) {
      const top = (a.likely_drivers || [])[0];
      tb.append(el('tr', {id: a.key && /^[0-9a-f]{8,64}$/.test(a.key) ? 'alert-' + a.key : null, 'data-key': a.key || null},
        el('td', {class: 'mono', text: L.intervalText(a.interval_manila)}),
        el('td', {text: L.regionName(a.region)}),
        el('td', {class: 'num', text: typeof a.price_php_mwh === 'number' ? Math.round(a.price_php_mwh).toLocaleString('en-US') : ''}),
        el('td', {}, badge(a.severity)),
        el('td', {class: 'trunc', text: top ? `${top.family_label || L.FAMILY_NAMES[top.family] || top.family} ${typeof top.score === 'number' ? top.score.toFixed(2) : ''}` : ''}),
        el('td', {class: 'num', text: Array.isArray(a.emailed_to) ? String(a.emailed_to.length) : (typeof a.emailed_to === 'number' ? String(a.emailed_to) : (a.sent_at ? 'yes' : 'no'))}),
        el('td', {class: 'gn-meta', text: a.source || ''})));
    }
    highlightLinked();
  }

  /* The alerts list (ericka-desk, platform polish PP-B1): every alert up to the shared as-of clock.
     The glance band says what is in force; one filter bar (Grid and Level shown, the rest under
     More filters) narrows the table, and its state is kept in the address and restored on load. */
  const asOfNow = () => (window.GNShell && window.GNShell.asOf ? window.GNShell.asOf() : null);
  const PAGE_SIZE = 20;
  const list = Object.assign({rows: null, error: null, page: 1, linked: false, levels: ''}, L.listFromSearch(location.search));
  const SEV_BADGE = {extreme: 'alert', high: 'alert', medium: 'warning', low: 'info'};
  const SEV_RANK = {extreme: 0, high: 1, medium: 2, low: 3};
  const sevWord = (s) => { const v = String(s || 'unrated').toLowerCase(); return v[0].toUpperCase() + v.slice(1); };
  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const fmt = (v) => Math.round(v).toLocaleString('en-US');

  /* The shared badge for a level word (GNUI.badge), or the same markup where ui.js is absent. */
  function badge(severity, extra) {
    const s = String(severity || 'unrated').toLowerCase();
    const UI = window.GNUI;
    const node = UI && typeof UI.badge === 'function' && SEV_BADGE[s] ? UI.badge(s)
      : el('span', {class: `gn-badge gn-sev gn-badge--${SEV_BADGE[s] || 'info'}`, text: sevWord(s)});
    if (extra) node.classList.add(...extra.split(' '));
    return node;
  }
  const alertTitle = (a) => `${L.regionName(a.region)} price ${a.direction === 'collapse' ? 'collapse' : 'spike'}`;
  const noticeHref = (id, t) => `/notices${/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(String(t || '')) ? '?at=' + String(t).slice(0, 16) : ''}#adv-${encodeURIComponent(id)}`;

  /* The cause, only as recorded: the event's link (and its notice), or plain words that none is. */
  /* main 0929fb5: the notices the server finds around an alert (`notices_around`) are counted,
     never claimed as its cause; the alert page lists them with their reasons. */
  const aroundText = (n) => `${n} notice${n === 1 ? '' : 's'} around it`;
  function causeNodes(a, compact) {
    const path = a.cause && L.safeEventPath(a.cause.href);
    const around = (a.notices_around || {}).count || 0;
    if (!a.cause) {
      return [el('span', {class: 'gn-meta', text: 'None on record' + (around ? ' · ' + aroundText(around) : ''),
        title: around ? 'Notices in the same region and time, not confirmed as the cause. The alert page lists them.' : null})];
    }
    const id = path && path.startsWith('/event/') ? path.slice(7) : null;
    const out = [path ? el('a', {href: path, class: 'al-cause', 'data-entity': id ? 'event:' + id : null, text: a.cause.title || 'Recorded event'})
      : el('span', {text: a.cause.title || 'Recorded event'})];
    if (a.cause.advisory && !compact) {
      out.push(' ', el('a', {class: 'al-notice mono', href: noticeHref(a.cause.advisory, a.cause.known_at),
        'data-entity': 'notice:' + a.cause.advisory, title: 'The notice that opened the event', text: a.cause.advisory}));
    }
    return out;
  }

  /* PERF-6: read through the shell's one inbox reader (`GNShell.inbox`: the ticker's read of the
     same time is the same request) with this page's own signed-in user; `fresh` after a save or a
     sign-in change, which the server answers differently. */
  const showInboxAsOf = (at) => { $('inbox-asof').textContent = at ? `Up to ${L.intervalText(at)} Manila` : ''; };
  /* DM-5 round 2: the rows read at a later time than the clock are taken down at once when the
     clock moves back, a read still on its way for a later time is dropped, and the read at the new
     time follows (the shell's inbox-due signal). */
  function withholdInbox() {
    list.reading = true; list.rowsAt = null;
    renderInbox();
  }
  function inboxClock(at) {
    showInboxAsOf(at);
    if (state.inboxPendingAt && !L.readFits(state.inboxPendingAt, at)) {
      state.inboxTicket = (state.inboxTicket || 0) + 1; state.inboxPendingAt = null;
    }
    if (list.rowsAt && !L.readFits(list.rowsAt, at)) withholdInbox();
  }
  async function loadInbox(fresh) {
    const at = asOfNow();
    showInboxAsOf(at);
    const ticket = (state.inboxTicket = (state.inboxTicket || 0) + 1);
    state.inboxPendingAt = at;
    const shell = window.GNShell;
    let r;
    try {
      if (!shell || !shell.inbox) throw new Error('the page shell is not loaded');
      r = await shell.inbox(at, {view: 'all', user: state.user, fresh: fresh === true});
    } catch (e) {
      if (ticket !== state.inboxTicket) return;
      state.inboxPendingAt = null;
      list.rows = null; list.error = e.message; list.reading = false; renderInbox(); return;
    }
    if (ticket !== state.inboxTicket) return;
    state.inboxPendingAt = null;
    if (!L.readFits(at, asOfNow())) { withholdInbox(); return; }  // DM-5: landed after a rewind
    list.rows = L.flattenInbox(r); list.error = null; list.reading = false; list.rowsAt = at;
    list.levels = r && r.default_levels ? 'Default levels: spike at 15,000 PHP/MWh or more, collapse at 0 or less'
      : (r && r.rules_version ? `Levels from rules version ${r.rules_version}` : '');
    renderInbox();
  }

  /* The glance band, from the same rows the list shows (before its filters). */
  function renderGlance() {
    const box = $('al-glance');
    if (!box) return;
    const at = asOfNow();
    const g = list.rows && !list.reading ? L.glance(list.rows, at) : null;  // DM-5: no later read in the glance
    box.setAttribute('aria-busy', String(!g));
    $('al-now-count').textContent = g ? String(g.now) : '–';
    box.classList.toggle('is-quiet', Boolean(g && !g.now));
    const sev = $('al-now-sev'); clear(sev);
    if (g && g.now) {
      for (const s of L.SEVERITIES.slice().reverse()) if (g.bySeverity[s]) { const n = badge(s); n.textContent = `${g.bySeverity[s]} ${sevWord(s)}`; sev.append(n); }
    } else if (g) sev.append(el('span', {class: 'gn-meta', text: at ? `Nothing past the level at ${at.slice(11, 16)}` : 'Nothing past the level'}));
    $('al-day-count').textContent = g ? String(g.day) : '–';
    $('al-day-label').textContent = at ? L.dayText(at.slice(0, 10)) : '';
    $('al-all-count').textContent = g ? String(g.all) : '–';
    $('al-all-label').textContent = g && g.all ? `Since ${L.dayText(String(list.rows.reduce((m, a) => (String(a.first || '') < m ? String(a.first) : m), '9999')).slice(0, 10))}` : '';
    const worst = $('al-worst'); clear(worst);
    if (!g || !g.focus) {
      worst.append(el('span', {class: 'gn-label', text: 'Worst in force'}), el('p', {class: 'gn-meta', text: g ? 'No alert up to this time.' : 'Loading the alerts…'}));
      return;
    }
    const a = g.focus;
    const path = L.alertPagePath(a);
    const head = el('div', {class: 'al-worst-head'}, el('span', {class: 'gn-label', text: g.focusInForce ? 'Worst in force' : 'Latest alert'}), badge(a.severity),
      g.focusInForce ? el('span', {class: 'gn-badge al-live', text: 'Still past the level'}) : el('span', {class: 'gn-meta', text: 'Ended'}));
    const title = el('p', {class: 'al-worst-title'}, path ? el('a', {href: path, 'data-entity': /^[0-9a-f]{24}$/.test(a.key || '') ? 'alert:' + a.key : null, text: alertTitle(a)}) : alertTitle(a));
    const fig = el('p', {class: 'al-worst-fig'},
      el('span', {class: 'gn-value', text: isNum(a.price_php_mwh) ? fmt(a.price_php_mwh) : '–'}), el('span', {class: 'gn-unit', text: '₱/MWh'}),
      el('span', {class: 'gn-meta mono', text: L.windowText(a)}));
    const cause = el('p', {class: 'al-worst-cause gn-meta'}, 'Cause: ', ...causeNodes(a, true));
    worst.append(el('div', {class: 'al-worst-text'}, head, title, fig, cause),
      path ? el('a', {class: 'gn-btn gn-btn--primary al-worst-go', href: path, text: 'Open alert'}) : null);
  }

  function renderInbox() {
    const body = $('inbox'); clear(body);
    const pagerBox = $('inbox-pager');
    const empty = $('inbox-empty'); clear(empty); empty.hidden = true;
    const tableCard = $('inbox-table-card');
    const table = $('inbox-table');
    renderGlance();
    $('inbox-levels').textContent = list.levels || '';
    syncControls();
    if (list.reading) {  // DM-5: rows read at a later time are withheld until the read at this time lands
      $('inbox-note').textContent = '';
      if (pagerBox) pagerBox.hidden = true;
      tableCard.hidden = true;
      empty.hidden = false;
      empty.append(el('p', {class: 'gn-loading', role: 'status', text: 'Reading the alerts at this time…'}));
      return;
    }
    if (list.rows === null) {
      $('inbox-note').textContent = '';
      if (pagerBox) pagerBox.hidden = true;
      tableCard.hidden = true;
      empty.hidden = false;
      empty.append(el('div', {class: 'gn-error', role: 'alert'},
        el('span', {text: 'The alerts could not be loaded' + (list.error ? ': ' + list.error : '.')}),
        el('button', {type: 'button', class: 'gn-btn gn-btn--sm', text: 'Retry', onclick: () => loadInbox()})));
      return;
    }
    const at = asOfNow();
    const ordered = L.pickAlerts(list.rows, {at, grid: list.grid, level: list.level, dir: list.dir, cause: list.cause, days: list.days, sort: list.sort, q: list.q});
    /* The groups decide the reading order; the pages cut that order, and each page shows its own
       group headings. */
    const rows = [].concat(...L.groupAlerts(ordered, list.group).map((x) => x.rows));
    if (filterCtl) filterCtl.count(rows.length, list.rows.length); else $('inbox-note').textContent = `${rows.length} of ${list.rows.length} alerts`;
    $('inbox-note').title = `${rows.length} of ${list.rows.length} alert${list.rows.length === 1 ? '' : 's'} shown`;
    const key = L.alertFromSearch(location.search);
    if (!rows.length) {
      if (pagerBox) pagerBox.hidden = true;
      tableCard.hidden = true;
      empty.hidden = false;
      empty.append(list.rows.length ? emptyFiltered(list.rows.length) : emptyNone(at));
      linkedNote(key);
      return;
    }
    tableCard.hidden = false;
    /* `/alerts?alert=<key>` (an alert email's link): open the page that alert is on, once */
    const jump = key && !list.linked;
    /* Ungrouped, the table holds up to 200 rows on one page, so a column sort covers them all. */
    const size = list.group === 'none' ? 200 : PAGE_SIZE;
    if (jump) { const i = rows.findIndex((a) => a.key === key); if (i >= 0) list.page = Math.floor(i / size) + 1; }
    linkedNote(key && !rows.some((a) => a.key === key) ? key : null);
    const S = window.GNShell || {};
    const pg = S.pageOf ? S.pageOf(rows.length, list.page, size) : {page: 1, from: 0, to: rows.length};
    list.page = pg.page;
    /* Column sorting (ui.js) needs no group headings in the way: grouped, no column holds a sort. */
    if (list.group !== 'none') for (const th of table.tHead.rows[0].cells) th.removeAttribute('aria-sort');
    for (const grp of L.groupAlerts(rows.slice(pg.from, pg.to), list.group)) {
      if (grp.label) body.append(groupRow(grp));
      for (const a of grp.rows) body.append(alertRow(a, a.key === key, at));
    }
    if (S.pager) S.pager(pagerBox, rows.length, list.page, size, (n) => { list.page = n; renderInbox(); tableCard.scrollIntoView({block: 'start'}); }, 'alerts');
    if (jump) {
      const node = document.getElementById('al-' + key);
      if (node) { list.linked = true; node.scrollIntoView({block: 'center'}); }
    }
  }

  function groupRow(grp) {
    const count = el('span', {class: 'gn-meta', text: `${grp.rows.length} alert${grp.rows.length === 1 ? '' : 's'}`});
    const cause = grp.cause && L.safeEventPath(grp.cause.href);
    const label = cause ? el('a', {href: cause, 'data-entity': 'event:' + cause.slice(7), text: grp.label}) : grp.label;
    /* A phone shows five of the seven columns (alerts.css): the heading spans those five. */
    const phone = typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 760px)').matches;
    return el('tr', {class: 'al-group-row'}, el('th', {scope: 'colgroup', colspan: phone ? '5' : '7'}, el('span', {class: 'al-group-label'}, label), ' ', count));
  }

  function emptyState(title, bodyText, action) {
    return el('div', {class: 'gn-empty', role: 'status'},
      el('p', {class: 'gn-empty-title', text: title}), el('p', {class: 'gn-empty-body', text: bodyText}),
      action ? el('div', {class: 'gn-empty-actions'}, action) : null);
  }
  function emptyFiltered(total) {
    return emptyState('No alert matches these filters', `${total} alert${total === 1 ? ' is' : 's are'} hidden by the filters or the search.`,
      el('button', {type: 'button', class: 'gn-btn', text: 'Clear filters', onclick: clearFilters}));
  }
  function emptyNone(at) {
    const S = window.GNShell || {};
    const last = S.span && S.span.last;
    const canMove = Boolean(last && S.setAsOf && at && last > at);
    return emptyState(at ? `No alert up to ${L.intervalText(at)}` : 'No alert up to this time',
      canMove ? 'No price crossed the alert level before the replay time. Move the clock later to see more.'
        : 'No price crossed the alert level in the replay so far.',
      canMove ? el('button', {type: 'button', class: 'gn-btn', text: 'Go to the latest', onclick: () => S.setAsOf(last)}) : null);
  }

  /* `/alerts?alert=<key>` for an alert the list does not show (not up to this time, filtered out, or
     a one-off check's): say so, and link to its row in the settings page's alert history. */
  function linkedNote(key) {
    const box = $('inbox-linked');
    if (!box) return;
    clear(box);
    box.hidden = !key;
    if (!key) return;
    box.append('The linked alert is not in this list. ',
      el('a', {href: L.settingsHistoryHref(key), text: 'Find it in the alert history'}));
  }

  function alertRow(a, linked, at) {
    const sev = String(a.severity || 'unrated').toLowerCase();
    const path = L.alertPagePath(a);
    const own = /^[0-9a-f]{24}$/.test(a.key || '');
    const live = L.inForce(a, at);
    const usual = isNum(a.usual_php_mwh) && a.usual_php_mwh > 0 && isNum(a.price_php_mwh) ? a.price_php_mwh / a.usual_php_mwh : null;
    const n = isNum(a.intervals) ? a.intervals : null;
    const title = alertTitle(a);
    const reason = [a.threshold_text, a.severity_reason].filter(Boolean).join(' · ');
    const around = (a.notices_around || {}).count || 0;
    const row = el('tr', {class: 'al-row sev-' + sev + (linked ? ' is-linked is-selected' : '') + (live ? ' is-live' : ''),
      id: /^[0-9a-f]{8,64}$/.test(a.key || '') ? 'al-' + a.key : null, 'data-key': a.key || null,
      'data-href': path || null, 'aria-current': linked ? 'true' : null},
      el('td', {'data-value': String(SEV_RANK[sev] ?? 9)}, badge(sev)),
      el('td', {class: 'trunc al-title', title: reason || null},
        path ? el('a', {href: path, 'data-entity': own ? 'alert:' + a.key : null, text: title}) : el('span', {text: title}),
        live ? el('span', {class: 'gn-badge al-live', title: 'Still past the level at the replay time', text: 'In force'}) : null),
      el('td', {class: 'num', 'data-value': isNum(a.price_php_mwh) ? String(a.price_php_mwh) : '', title: a.direction === 'collapse' ? 'Lowest price' : 'Peak price',
        text: isNum(a.price_php_mwh) ? fmt(a.price_php_mwh) : '–'}),
      el('td', {class: 'num al-c-x al-wide' + (usual === null ? ' al-na' : ''), 'data-value': usual === null ? '' : usual.toFixed(2),
        title: usual === null ? 'No usual price on record for this hour' : `Usual ${fmt(a.usual_php_mwh)} PHP/MWh`,
        text: usual === null ? '–' : usual.toFixed(1) + '×'}),
      el('td', {class: 'mono al-when', 'data-value': String(a.first || a.interval_manila || ''),
        title: n !== null ? `${n} five-minute interval${n === 1 ? '' : 's'} (${n * 5} min)` : null, text: L.windowText(a)}),
      el('td', {class: 'trunc al-cause-cell', title: a.cause ? `${a.cause.title || ''}${a.cause.advisory ? ' · notice ' + a.cause.advisory : ''}`
        : 'No recorded event explains this alert' + (around ? ` · ${aroundText(around)}, not confirmed as the cause (see the alert)` : '')},
        ...causeNodes(a)),
      el('td', {class: 'gn-row-actions al-wide'}, path ? el('a', {class: 'gn-btn gn-btn--sm gn-btn--ghost al-go', href: path,
        'aria-label': `Open alert: ${title}, ${L.windowText(a)}`, text: 'Open'}) : null));
    return row;
  }

  /* The filter bar. The filters (grid, level, direction, cause, period, search) are the shared
     controller's (GNUI.filters: pressed state, Clear, More filters' count and the address). The
     two view options under More filters (group and order) are this page's own buttons, kept in
     the address the same way. Without ui.js the page wires the same controls itself. */
  let filterCtl = null;
  const FILTER_KEYS = ['grid', 'level', 'dir', 'cause', 'days', 'q'];
  function syncControls() {
    for (const g of document.querySelectorAll('#inbox-card [data-view]')) {
      for (const b of g.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === list[g.dataset.view]));
    }
    if (filterCtl) return;
    for (const g of document.querySelectorAll('#inbox-card .gn-seg[data-filter]')) {
      for (const b of g.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === list[g.dataset.filter]));
    }
    const q = $('inbox-q');
    if (q && q.value !== list.q && document.activeElement !== q) q.value = list.q;
    $('inbox-clear').hidden = L.activeFilters(list) === 0;
  }

  function writeAddress() {
    const next = L.listToSearch(list, location.search);
    if (next !== location.search && typeof history.replaceState === 'function') {
      try { history.replaceState(history.state, '', location.pathname + next + location.hash); } catch (e) { /* the view still filters */ }
    }
  }

  function clearFilters() {
    if (filterCtl) { filterCtl.clear(); return; }  // its onChange redraws
    for (const k of FILTER_KEYS) list[k] = L.LIST_DEFAULTS[k];
    list.page = 1;
    writeAddress();
    renderInbox();
  }

  function listFilters() {
    for (const g of document.querySelectorAll('#inbox-card [data-view]')) {
      const key = g.dataset.view;
      for (const b of g.querySelectorAll('button')) b.addEventListener('click', () => {
        list[key] = b.dataset.value; list.page = 1;
        writeAddress();
        renderInbox();
      });
    }
    /* A column header click on a grouped table first drops the groups, then ui.js sorts. */
    const table = $('inbox-table');
    if (table) table.addEventListener('click', (event) => {
      const th = event.target.closest && event.target.closest('th[data-sort]');
      if (!th || list.group === 'none') return;
      list.group = 'none'; list.page = 1; writeAddress(); renderInbox();
    }, true);
    if (typeof window.matchMedia === 'function') {
      const phone = window.matchMedia('(max-width: 760px)');
      if (typeof phone.addEventListener === 'function') phone.addEventListener('change', () => { if (list.rows) renderInbox(); });
    }
    const bar = document.querySelector('#inbox-card .gn-filters');
    const own = () => {
      for (const g of document.querySelectorAll('#inbox-card .gn-seg[data-filter]')) {
        const key = g.dataset.filter;
        for (const b of g.querySelectorAll('button')) b.addEventListener('click', () => {
          list[key] = b.dataset.value; list.page = 1; writeAddress(); renderInbox();
        });
      }
      const q = $('inbox-q');
      if (q) { q.value = list.q; q.addEventListener('input', () => { list.q = q.value; list.page = 1; writeAddress(); renderInbox(); }); }
      const clearBtn = $('inbox-clear');
      if (clearBtn) clearBtn.addEventListener('click', clearFilters);
      syncControls();
    };
    const UI = window.GNUI;
    if (!UI || !UI.ready || !bar) { own(); return; }
    UI.ready.then(() => {
      if (typeof UI.filters !== 'function') { own(); return; }
      filterCtl = UI.filters(bar, {
        defaults: Object.fromEntries(FILTER_KEYS.map((k) => [k, L.LIST_DEFAULTS[k]])),
        noun: 'alerts',
        onChange: (s) => { Object.assign(list, s); list.page = 1; renderInbox(); },
      });
      Object.assign(list, filterCtl.get());
      renderInbox();
    }, own);
    syncControls();
  }

  /* `/settings?alert=<key>` (the list's link for an alert it does not show): that alert's history
     row, scrolled to and marked. */
  function highlightLinked() {
    const key = L.alertFromSearch(location.search);
    if (!key) return;
    const row = document.getElementById('alert-' + key);
    for (const r of document.querySelectorAll('#history tr.linked')) { r.classList.remove('linked'); r.removeAttribute('aria-current'); }
    if (!row) { $('history-note').textContent = 'The linked alert is not among the last 50.'; return; }
    row.classList.add('linked'); row.setAttribute('aria-current', 'true');
    $('history-note').textContent = 'The linked alert is marked below.';
    if (!state.scrolled) { state.scrolled = true; row.scrollIntoView({block: 'center'}); }
  }

  /* The bar's region tabs and the check's region select are one choice. */
  function setRegion(code) {
    if ($('check-region')) $('check-region').value = code;
    for (const b of document.querySelectorAll('.grids button')) b.setAttribute('aria-pressed', String(b.dataset.grid === code));
  }

  /* The shell's email sign-in (`/settings#sign-in`) scrolls to the sign-in card. */
  function signInFromHash() {
    const card = $('signin-card');
    if (!card || card.hidden || location.hash !== '#sign-in') return;
    if (state.auth && $('pw-form') && $('pw-form').hidden) openSignIn();
    card.scrollIntoView({block: 'start'});
  }

  function init() {
    const on = (id, type, fn) => { const node = $(id); if (node) node.addEventListener(type, fn); };
    on('sign-in', 'click', signIn);
    on('sign-in-google', 'click', signIn);
    on('pw-form', 'submit', signInPassword);
    on('signin-open', 'click', openSignIn);
    on('sign-out', 'click', () => state.auth && endSession().then(() => state.auth.signOut()));
    if (HAS_SETTINGS) {
      on('rules-form', 'submit', saveRules);
      on('check-form', 'submit', runCheck);
      on('rl-test', 'click', testEmail);
      on('rl-add-recipient', 'click', () => { const tb = $('rl-recipients').tBodies[0]; for (const r of tb.querySelectorAll('tr.st-none')) r.remove(); tb.append(recipientRow()); });
      if (HAS_PORTFOLIO) {
        on('portfolio-form', 'submit', savePortfolio);
        on('pf-add-contract', 'click', () => $('pf-contracts').tBodies[0].append(contractRow({hours: [...Array(24).keys()]})));
        on('pf-import', 'click', fillFromImport);
        on('pf-add-node', 'click', () => $('pf-nodes').tBodies[0].append(nodeRow()));
      }
      const start = L.checkDefaults(location.hash);
      setRegion(start.region);
      $('check-interval').value = start.interval;
      on('check-region', 'change', () => setRegion($('check-region').value));
      window.addEventListener('hashchange', signInFromHash);
    }
    if (HAS_LIST) {
      listFilters();
      // PERF-6: the line saying which time the list is read at follows every clock move; the list
      // itself is read when the shell says the clock settled (at most every 2.5 s while it plays).
      const shell = window.GNShell;
      if (shell && shell.onAsOf) shell.onAsOf(inboxClock);  // DM-5: also withholds rows read later
      if (shell && shell.onInboxDue) shell.onInboxDue(() => loadInbox());
    }
    render();
    load().then(startAuth).then(signInFromHash);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
