/* Dashboard alerts (ericka-desk, the design canvas's Main board): the alert inbox above the
   operator notices, one table row per risk event (PP-B5), its story behind the row's chevron.
   It reads `/api/alerts/inbox` at the shared as-of
   clock through the shell's one inbox reader (`GNShell.inbox`, PERF-6: the ticker's read of the
   same time is the same request, and a played clock is read at most every 2.5 s and where it
   stops), so nothing after that time shows, and keeps the clock's own day, as the notices beside
   it do ("since 00:00"): a risk event shows once one of its alerts falls between that day's
   00:00 and the clock. Text only; the peso impact is the server's word
   ("Needs your portfolio") and is never computed here.

   The pure part (`card`, `steps`, `windowText`, `sureText`, `sinceDayStart`) is exported for node when `module`
   exists, and as `window.DashAlerts` in the page. */
(function () {
  const NAMES = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const region = (c) => NAMES[c] || c || '';
  const hhmm = (t) => String(t || '').slice(11, 16);
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const day = (t) => {
    const m = String(t || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]}` : '';
  };
  const peso = (v) => (typeof v === 'number' && isFinite(v) ? '₱' + Math.round(v).toLocaleString('en-US') : 'price unknown');
  const EVENT = /^\/event\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
  // an alert no recorded event explains has its own page, /alert/<key> (spike.html)
  const ALERT_PAGE = /^\/alert\/[0-9a-f]{24}$/;
  const AT = /^\/\?at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

  function windowText(first, last) {
    if (!first) return '';
    return `${day(first)} ${hhmm(first)}` + (last && last !== first ? `–${hhmm(last)}` : '');
  }

  /* The operator notices around a group's alerts (the server's `notices_around`): never a cause.
     count: how many the server found; items: the nearest ones it sent; plant / unclear: how many
     name one plant of the region, and how many fit more than one (or a station, not a plant). */
  function noticesAround(g) {
    const out = { count: 0, plant: 0, unclear: 0, items: [] };
    for (const a of (g && g.alerts) || []) {
      const n = a && a.notices_around;
      if (!n) continue;
      out.count += n.count || 0;
      out.plant += (n.counts && n.counts.plant) || 0;
      out.unclear += (n.counts && n.counts.unclear) || 0;
      for (const x of n.items || []) out.items.push(Object.assign({ first: a.first || a.interval_manila }, x));
    }
    return out;
  }
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  /* How sure the link to a cause is: only a recorded event counts; no guess is made. */
  function sureText(g) {
    if (g && g.cause) return `Linked to notice ${g.cause.advisory || 'on record'}, known at ${hhmm(g.cause.known_at)}`;
    const n = noticesAround(g);
    if (!n.count) return 'No recorded cause: not linked to any plant';
    const parts = [n.plant ? `${n.plant} name${n.plant === 1 ? 's' : ''} a plant` : '', n.unclear ? `${n.unclear} unclear` : ''].filter(Boolean);
    return `No recorded cause: not linked to any plant. ${plural(n.count, 'notice', 'notices')} around it, none confirmed`
      + (parts.length ? ` (${parts.join(', ')})` : '');
  }

  /* "How we got here": the cause notice, the notices around an alert with no recorded cause (each
     marked not confirmed, with how sure its plant match is), then each alert's first interval over
     its level, in time order. */
  function steps(g) {
    const out = [];
    if (g && g.cause && g.cause.known_at) {
      out.push({ t: g.cause.known_at, text: `${hhmm(g.cause.known_at)} Notice ${g.cause.advisory || ''}: ${g.cause.title}`.replace(/ +/g, ' ') });
    }
    if (!(g && g.cause)) {
      for (const x of noticesAround(g).items) {
        const at = String(x.t || '').slice(0, 10) !== String(x.first || '').slice(0, 10) ? `${day(x.t)} ${hhmm(x.t)}` : hhmm(x.t);
        out.push({ t: x.t, notice: true,
          text: `${at} Notice ${x.id || ''} (not confirmed as the cause · ${x.match_label || 'Unclear'}): ${x.kind_label ? x.kind_label + ' · ' : ''}${x.text || ''}`.replace(/ +/g, ' ').trim() });
      }
    }
    for (const a of (g && g.alerts) || []) {
      const verb = a.direction === 'collapse' ? 'fell to' : 'reached';
      out.push({ t: a.first || a.interval_manila,
        text: `${hhmm(a.first || a.interval_manila)} ${region(a.region)} price over its level (${a.threshold_text || 'no level'})` });
      if (a.interval_manila && a.interval_manila !== a.first) {
        out.push({ t: a.interval_manila, text: `${hhmm(a.interval_manila)} ${region(a.region)} price ${verb} ${peso(a.price_php_mwh)}/MWh` });
      }
    }
    out.sort((x, y) => (String(x.t) < String(y.t) ? -1 : String(x.t) > String(y.t) ? 1 : 0));
    return out;
  }

  function card(g) {
    const alerts = (g && g.alerts) || [];
    const a0 = alerts[0] || {};
    const sev = String((g && g.severity) || 'unrated').toLowerCase();
    const title = g && g.cause ? g.cause.title
      : `${region((g && g.regions || [])[0])} price ${a0.direction === 'collapse' ? 'collapse' : 'spike'}`;
    const n = alerts.length;
    const href = g && g.cause && EVENT.test(g.cause.href || '') ? g.cause.href
      : EVENT.test(a0.href || '') || ALERT_PAGE.test(a0.href || '') || AT.test(a0.href || '') ? a0.href : '/alerts';
    const fi = (g && g.financial_impact) || a0.financial_impact || {};
    return {
      sev, title,
      window: windowText(g && g.first, g && g.last),
      grouped: `${n} alert${n === 1 ? '' : 's'} grouped · ${((g && g.regions) || []).map(region).join(', ')}`,
      driver: a0.main_driver || 'None on record',
      serious: a0.severity_reason || sev,
      cost: typeof fi.php === 'number' ? null : (fi.hidden ? 'Hidden until you sign in' : 'Needs your portfolio'),
      sure: sureText(g),
      next: (g && g.next_step) || a0.next_step || '',
      steps: steps(g).map((s) => s.text).concat((() => {
        const n = g && g.cause ? null : noticesAround(g);
        const more = n ? n.count - n.items.length : 0;
        return more > 0 ? [`${plural(more, 'earlier notice', 'earlier notices')} around it on the alert page (not confirmed as the cause)`] : [];
      })()),
      open: href,
      openText: EVENT.test(href) ? 'Open event' : ALERT_PAGE.test(href) ? 'Open alert'
        : AT.test(href) ? 'No event on record · jump to this time' : 'Open the inbox',
      // an alert with no recorded event has its own page (/alert/<alert key>, spike.html)
      noCause: !(g && g.cause) && ALERT_PAGE.test(href),
      // the notices around it, none confirmed: the pill says how many so the card is not empty
      noticesAround: g && g.cause ? 0 : noticesAround(g).count,
      journal: ALERT_PAGE.test(href) && !(g && g.cause) ? href + '#sp-journal' : EVENT.test(href) ? href + '#ed-journal-box' : '/journal',
    };
  }

  /* The groups on the clock's day, up to the clock: the notices' own gate (grid.js renderFeed keeps
     a notice from the day's 00:00 up to the clock). A group's time is its latest alert interval
     (the server cuts it at the clock); a group with no readable time is never shown. */
  const STAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
  function sinceDayStart(groups, at) {
    const clock = STAMP.test(String(at || '')) ? String(at).slice(0, 16) : null;
    if (!clock) return [];
    const dayStart = clock.slice(0, 10) + 'T00:00';
    return (groups || []).filter((g) => {
      const times = [g && g.last].concat(((g && g.alerts) || []).map((a) => a && (a.last || a.interval_manila)))
        .map((t) => String(t || '')).filter((t) => STAMP.test(t)).map((t) => t.slice(0, 16));
      const t = times.sort().pop();
      return !!t && t >= dayStart && t <= clock;
    });
  }

  const api = { card, steps, windowText, sureText, sinceDayStart, noticesAround };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  window.DashAlerts = api;

  // ---------- drawing (PP-B5: one dense row per risk event, its story behind the chevron) ----------
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  /* The shared badge for a level word (ui.js), so the word and its style match every page; the
     same classes by hand until GNUI has loaded. */
  const LEVEL_TONE = { extreme: 'alert', high: 'alert', medium: 'warning', low: 'info' };
  function levelBadge(sev) {
    const ui = window.GNUI;
    if (ui && typeof ui.badge === 'function' && LEVEL_TONE[sev]) return ui.badge(sev);
    const word = LEVEL_TONE[sev] ? sev.charAt(0).toUpperCase() + sev.slice(1) : 'Unrated';
    return el('span', 'gn-badge' + (LEVEL_TONE[sev] ? ' gn-badge--' + LEVEL_TONE[sev] + ' gn-sev' : ''), word);
  }
  const pair = (label, value) => {
    const box = el('div', 'da-pair');
    box.appendChild(el('span', 'gn-label', label));
    box.appendChild(el('span', 'da-pair-v', value));
    return box;
  };
  const spanOf = (g) => {
    const a = g && g.first, b = g && g.last;
    if (!a) return '';
    return hhmm(a) + (b && hhmm(b) !== hhmm(a) ? '–' + hhmm(b) : '');
  };

  let rowSeq = 0;
  function rows(g) {
    const c = card(g);
    const id = 'da-d' + (++rowSeq);
    const tr = el('tr', 'da-row sev-' + c.sev);
    tr.setAttribute('data-href', c.open);
    tr.title = c.grouped;
    const sev = el('td');
    sev.appendChild(levelBadge(c.sev));
    tr.appendChild(sev);
    const name = el('td', 'trunc da-title');
    const toggle = el('button', 'gn-row-toggle');
    toggle.type = 'button';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', id);
    toggle.setAttribute('aria-label', 'How this alert came about');
    name.appendChild(toggle);
    const link = el('a', null, c.title);
    link.href = c.open;
    const ev = c.open.match(/^\/event\/(.+)$/), al = c.open.match(/^\/alert\/([0-9a-f]{24})$/);
    if (ev) link.setAttribute('data-entity', 'event:' + ev[1]);
    else if (al) link.setAttribute('data-entity', 'alert:' + al[1]);
    name.appendChild(link);
    name.title = c.title;
    tr.appendChild(name);
    tr.appendChild(el('td', 'gn-num da-when', spanOf(g)));
    tr.appendChild(el('td', 'trunc', ((g && g.regions) || []).map(region).join(', ')));
    const cause = el('td', 'trunc da-cause');
    if (g && g.cause) {
      const adv = g.cause.advisory;
      const at = String(g.cause.known_at || '').slice(0, 16);
      if (adv && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(at)) {
        const a = el('a', null, 'Notice ' + adv);
        a.href = '/notices?at=' + at + '#adv-' + encodeURIComponent(adv);
        a.setAttribute('data-entity', 'notice:' + adv);
        cause.appendChild(a);
        cause.appendChild(el('span', 'gn-meta da-at', ' ' + hhmm(at)));
      } else cause.appendChild(el('span', null, 'On record'));
      cause.title = c.sure;
    } else {
      // main 0929fb5: the notices around it are counted, none claimed as the cause
      cause.appendChild(el('span', 'da-none', 'No recorded cause'
        + (c.noticesAround ? ` · ${plural(c.noticesAround, 'notice', 'notices')} around it` : '')));
      cause.title = c.sure;
    }
    tr.appendChild(cause);
    const act = el('td', 'gn-row-actions');
    const more = el('button', 'gn-icon-btn');
    more.type = 'button';
    more.setAttribute('aria-label', 'More options');
    more.setAttribute('data-menu', '');
    const dots = el('span', 'gn-dots');
    dots.setAttribute('aria-hidden', 'true');
    more.appendChild(dots);
    const menu = el('div', 'gn-menu');
    menu.setAttribute('role', 'menu');
    menu.hidden = true;
    const open = el('a', null, c.openText); open.href = c.open; open.setAttribute('role', 'menuitem');
    const jr = el('a', null, 'Add to journal'); jr.href = c.journal; jr.setAttribute('role', 'menuitem');
    menu.appendChild(open); menu.appendChild(jr);
    act.appendChild(more); act.appendChild(menu);
    tr.appendChild(act);

    const detail = el('tr', 'gn-row-detail da-detail');
    detail.id = id;
    detail.hidden = true;
    const td = el('td');
    td.colSpan = 6;
    const grid = el('div', 'da-pairs');
    grid.appendChild(pair('Main driver', c.driver));
    grid.appendChild(pair('How serious', c.serious));
    grid.appendChild(pair('Cost to us', c.cost || 'See the inbox'));
    grid.appendChild(pair('Next step', c.next || 'Open the inbox'));
    td.appendChild(grid);
    if (c.steps.length) {
      const how = el('div', 'da-how');
      how.appendChild(el('span', 'gn-label', 'How we got here'));
      const ol = el('ol');
      for (const s of c.steps) ol.appendChild(el('li', null, s));
      how.appendChild(ol);
      td.appendChild(how);
    }
    td.appendChild(el('p', 'gn-meta da-grouped', c.grouped));
    detail.appendChild(td);
    return [tr, detail];
  }

  /* The four kinds of empty the design system names; this list has three of them. */
  function empty(box, title, body, action) {
    box.textContent = '';
    const e = el('div', 'gn-empty');
    e.setAttribute('role', 'status');
    e.appendChild(el('p', 'gn-empty-title', title));
    e.appendChild(el('p', 'gn-empty-body', body));
    if (action) {
      const acts = el('div', 'gn-empty-actions');
      acts.appendChild(action);
      e.appendChild(acts);
    }
    box.appendChild(e);
    box.hidden = false;
  }

  /* The dashboard shows the newest few; the rest are in the inbox at /alerts. */
  const SHOWN = 5;
  const state = { view: 'all', ticket: 0, timer: null, drawnAt: null, pendingAt: null };

  async function load() {
    const box = $('da-list');
    const note = $('da-count');
    const none = $('da-empty');
    const table = $('da-table');
    if (!box) return;
    const shell = window.GNShell;
    const at = shell && shell.asOf ? shell.asOf() : null;
    const ticket = ++state.ticket;
    state.pendingAt = at;
    let r = null;
    try {
      r = shell && shell.inbox ? await shell.inbox(at, { view: state.view }) : null;
    } catch (e) { r = null; }
    if (ticket !== state.ticket) return;
    state.pendingAt = null;
    /* DM-5 round 2: an answer that lands after the clock moved back before its time is never
       drawn (it states later ends and peaks); the read at the new time follows. */
    const now = shell && shell.asOf ? shell.asOf() : at;
    if (now && at && at > now) { withhold(); return; }
    box.textContent = '';
    const show = (on) => { if (table) table.hidden = !on; if (none && on) none.hidden = true; };
    state.drawnAt = at;  // DM-5: the cutoff this list was read at
    if (!r) {
      note.textContent = 'No data';
      show(false);
      const retry = el('button', 'gn-btn gn-btn--sm', 'Retry');
      retry.type = 'button';
      retry.addEventListener('click', load);
      if (none) empty(none, 'The alert inbox could not be read', 'The desk asked for the alerts at this time and got no answer.', retry);
      return;
    }
    const groups = sinceDayStart(r.groups, at);
    const shown = groups.slice(0, SHOWN);
    const count = groups.reduce((n, g) => n + ((g.alerts || []).length), 0);
    note.textContent = (groups.length > SHOWN ? `Newest ${SHOWN} of ` : '')
      + `${groups.length} risk event${groups.length === 1 ? '' : 's'} · ${count} alert${count === 1 ? '' : 's'} since 00:00`
      + (r.default_levels ? ' · default levels' : '');
    const more = $('da-more');
    if (more) more.textContent = groups.length > SHOWN ? `All ${groups.length} alerts` : 'All alerts';
    if (!groups.length) {
      show(false);
      const clock = at ? String(at).slice(11, 16) : 'this time';
      if (state.view === 'high') {
        const all = el('button', 'gn-btn gn-btn--sm', 'Show all levels');
        all.type = 'button';
        all.addEventListener('click', () => setView('all'));
        if (none) empty(none, 'No high or extreme alert since 00:00', `None reached those levels by ${clock}.`, all);
      } else {
        const inbox = el('a', 'gn-btn gn-btn--sm', 'Open the inbox');
        inbox.href = '/alerts';
        if (none) empty(none, 'No alert since 00:00', `No price crossed its alert level by ${clock}. Move the replay clock to see later hours.`, inbox);
      }
      return;
    }
    show(true);
    for (const g of shown) for (const row of rows(g)) box.appendChild(row);
  }

  function setView(view) {
    state.view = view;
    for (const o of document.querySelectorAll('#da-filters button')) o.setAttribute('aria-pressed', String(o.dataset.view === view));
    load();
  }

  /* DM-5: the list read at a later time than the clock is taken down until the read at the
     clock lands. */
  function withhold() {
    const box = $('da-list');
    state.drawnAt = null;
    if (!box) return;
    box.textContent = '';
    // the rows' table stays, with one quiet line in place of the rows read later
    const table = $('da-table'), none = $('da-empty');
    if (table) table.hidden = false;
    if (none) none.hidden = true;
    const tr = el('tr', 'da-reading');
    const td = el('td');
    td.colSpan = 6;
    td.appendChild(el('p', 'gn-loading', 'Reading the alert inbox…'));
    tr.appendChild(td);
    box.appendChild(tr);
  }

  function later() {
    clearTimeout(state.timer);
    state.timer = setTimeout(load, 400);
  }

  function start() {
    if (!$('da-list')) return;
    for (const b of document.querySelectorAll('#da-filters button')) b.addEventListener('click', () => setView(b.dataset.view));
    const shell = window.GNShell;
    if (shell && shell.onInboxDue) shell.onInboxDue(load);  // PERF-6: was onAsOf(later), a read per clock tick
    /* DM-5: when the clock moves back before the time this list was read at, the list is
       withheld until the read at the new time lands: it would show alerts' later peaks and ends. */
    if (shell && shell.onAsOf) shell.onAsOf((at) => {
      if (state.pendingAt && at < state.pendingAt) { state.ticket++; state.pendingAt = null; }  // drop the late read
      if (state.drawnAt === null || at >= state.drawnAt) return;  // earlier reads state nothing later
      withhold();
    });
    if (shell && shell.onUser) shell.onUser(later);
    load();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
