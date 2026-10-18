/* InGRID journal page (`/journal`, ericka-desk slice 8: E26, E27, E28, D2; platform polish
   PP-B2).

   Signed out: an empty state that says what the journal holds, one sign-in action
   (GNShell.signIn()) and a link to an example event. Signed in: one filter bar, a dense table of
   entries (as of, what it is about, the decision, the reason, the price then and what happened
   after) and the chosen entry beside it, with its "known then" snapshot, the notices that came
   after and, for your own entries, an editor. The side column also holds the new-entry box.

   The decision is the entry text's first word ("Retain: …", "Change: …"; GNJournal.decisionOf),
   so the journal's record and routes are unchanged. "What happened after" is the notices after
   the entry's time, up to the shared replay clock, that mention the plant, else the ones in its
   region ("No data" when the notices file is missing).

   The filters live in the address (`?q=&plant=&event=&region=&since=&until=&scope=&sort=
   &decision=&entry=`), so a filtered view can be shared and comes back on load; `?plant=` and
   `?event=` are the prefilters the plant and event pages link with. The table lists entries at or
   before the replay clock, like every other view.

   No inline style and no markup insertion: every value is written as text. A failed call shows
   its error in place and keeps what the user typed. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const J = () => window.GNJournal;
  const S = () => window.GNShell;
  const AFTER_MAX = 5;

  function make(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }
  const fmtPrice = (v) => Math.round(v).toLocaleString('en-US');
  const DECISION_WORD = { retain: 'Retain', change: 'Change' };
  const decisionBadge = (d) => make('span', 'gn-badge' + (d === 'retain' ? ' gn-badge--ok' : d === 'change' ? ' gn-badge--warning' : ''),
    d ? DECISION_WORD[d] : 'Note');

  // ---------- the address ----------
  const params = (() => { try { return new URLSearchParams(window.location.search); } catch (e) { return new URLSearchParams(); } })();
  const pick = (k) => (params.get(k) || '').trim();
  const state = {
    event: pick('event'), decision: ['retain', 'change', 'note'].includes(pick('decision')) ? pick('decision') : '',
    scope: pick('scope') === 'desk' ? 'desk' : 'mine', entry: /^[0-9a-f]{32}$/.test(pick('entry')) ? pick('entry') : '',
    seq: 0, data: null, view: null, entries: [], box: null, started: false,
  };
  if (state.event && !J().validTarget('event', state.event)) state.event = '';

  function writeAddress() {
    const q = new URLSearchParams();
    const put = (k, v) => { if (v) q.set(k, v); };
    put('q', $('f-q').value.trim());
    put('plant', $('f-plant').value.trim());
    put('event', state.event);
    put('region', $('f-region').value);
    put('since', minuteOf($('f-since').value));
    put('until', minuteOf($('f-until').value));
    if (state.scope === 'desk') q.set('scope', 'desk');
    if ($('f-sort').value === 'oldest') q.set('sort', 'oldest');
    put('decision', state.decision);
    put('entry', state.entry);
    const s = q.toString();
    try { history.replaceState(null, '', location.pathname + (s ? '?' + s : '') + location.hash); } catch (e) { /* a sandboxed frame */ }
  }
  function readAddress() {
    $('f-q').value = pick('q').slice(0, 200);
    const plant = pick('plant');
    if (plant && J().validTarget('plant', plant)) $('f-plant').value = plant;
    if (['CLUZ', 'CVIS', 'CMIN'].includes(pick('region'))) $('f-region').value = pick('region');
    if (minuteOf(pick('since'))) $('f-since').value = minuteOf(pick('since'));
    if (minuteOf(pick('until'))) $('f-until').value = minuteOf(pick('until'));
    if (pick('sort') === 'oldest') $('f-sort').value = 'oldest';
    if ($('f-plant').value || $('f-region').value || $('f-since').value || $('f-until').value || $('f-sort').value !== 'newest') $('f-more').open = true;
  }

  // ---------- the filters ----------
  const minuteOf = (v) => (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(v || '') ? v.slice(0, 16) : '');
  function filters() {
    const clock = S().asOf();
    let until = minuteOf($('f-until').value) || clock;
    if (until > clock) until = clock; // never past the replay clock
    let since = minuteOf($('f-since').value);
    if (since && since > until) since = until;
    const out = { scope: state.scope, sort: $('f-sort').value, until };
    const q = $('f-q').value.trim();
    if (q) out.q = q.slice(0, 200);
    const plant = $('f-plant').value.trim();
    if (plant) out.plant = plant;
    if ($('f-region').value) out.region = $('f-region').value;
    if (since) out.since = since;
    if (state.event) out.event = state.event;
    return out;
  }
  const filtered = () => !!($('f-q').value.trim() || $('f-plant').value.trim() || $('f-region').value || $('f-since').value
    || $('f-until').value || $('f-sort').value !== 'newest' || state.event || state.decision || state.scope !== 'mine');
  function syncSegs() {
    for (const b of $('f-scope').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === state.scope));
    for (const b of $('f-decision').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === state.decision));
    $('f-reset').hidden = !filtered();
    $('f-event-row').hidden = !state.event;
  }

  // ---------- "what happened after" ----------
  function afterFor(entry, d) {
    if (!d || !d.advisories) return null;
    const site = J().siteOf(entry.target.kind, entry.target.id, d);
    const region = (entry.snapshot && entry.snapshot.region) || J().regionOf(entry.target.kind, entry.target.id, d);
    const from = entry.as_of + ':59';
    const until = S().asOf() + ':59';
    const later = d.advisories.filter((a) => a && typeof a.t === 'string' && a.t > from && a.t <= until);
    const atPlant = site ? later.filter((a) => J().mentions(String(a.text), site)) : [];
    if (atPlant.length) return { how: 'Notices that mention ' + site, short: 'at ' + site, rows: atPlant.slice(0, AFTER_MAX), total: atPlant.length };
    const inRegion = region ? later.filter((a) => a.grid === region) : [];
    return { how: region ? 'Notices in ' + (J().REGIONS[region] || region) + (site ? ' (none mention ' + site + ')' : '') : 'No region on this entry',
      short: region ? 'in ' + (J().REGIONS[region] || region) : '', rows: inRegion.slice(0, AFTER_MAX), total: inRegion.length, region };
  }

  // ---------- the parts of an entry ----------
  function targetLink(entry, d, cls) {
    const t = entry.target;
    const a = make('a', cls || 'j-target');
    if (t.kind === 'event') {
      a.href = '/event/' + encodeURIComponent(t.id);
      a.setAttribute('data-entity', 'event:' + t.id);
      const ev = d && d.events.get(t.id);
      a.textContent = ev && ev.title ? String(ev.title) : 'Event ' + t.id;
    } else {
      a.href = '/plant/' + encodeURIComponent(t.id);
      a.setAttribute('data-entity', 'plant:' + t.id);
      a.textContent = 'Plant ' + t.id;
    }
    return a;
  }

  function knownThen(entry) {
    const box = make('section', 'j-known');
    box.appendChild(make('h3', 'gn-label', 'Known then'));
    const snap = entry.snapshot || {};
    const dl = make('dl', 'j-facts');
    const row = (k, v, nodata) => {
      dl.appendChild(make('dt', null, k));
      dl.appendChild(make('dd', nodata ? 'gn-nodata' : null, v));
    };
    const region = snap.region ? (J().REGIONS[snap.region] || snap.region) : null;
    row('Region', region || 'No data', !region);
    row('Price', typeof snap.price === 'number' ? '₱' + fmtPrice(snap.price) + '/MWh' : 'No data', typeof snap.price !== 'number');
    row('Latest notice', snap.latest_notice || 'No data', !snap.latest_notice);
    box.appendChild(dl);
    const facts = Array.isArray(snap.known_facts) ? snap.known_facts : [];
    if (facts.length) {
      const ul = make('ul', 'j-known-facts');
      facts.forEach((f) => ul.appendChild(make('li', null, f)));
      box.appendChild(ul);
    }
    return box;
  }

  function happenedAfter(entry, d) {
    const box = make('section', 'j-after');
    box.appendChild(make('h3', 'gn-label', 'What happened after'));
    const after = afterFor(entry, d);
    if (!after) { box.appendChild(make('p', 'gn-nodata', 'No data')); return box; }
    if (!after.rows.length) {
      box.appendChild(make('p', 'gn-nodata', entry.as_of >= S().asOf() ? 'The clock is at the entry\'s time, so nothing is later yet.' : 'No later notices.'));
      return box;
    }
    box.appendChild(make('p', 'gn-meta', after.how + ', after ' + J().asOfWords(entry.as_of) + ' up to ' + J().asOfWords(S().asOf()) + '.'));
    const ul = make('ul', 'j-after-list');
    after.rows.forEach((a) => {
      const li = make('li');
      li.appendChild(make('span', 'mono j-t', J().asOfWords(a.t)));
      li.appendChild(make('span', null, J().opText(a.text)));
      ul.appendChild(li);
    });
    box.appendChild(ul);
    if (after.total > after.rows.length) box.appendChild(make('p', 'gn-meta', (after.total - after.rows.length) + ' more after these.'));
    return box;
  }

  function editor(entry, onDone) {
    const wrap = make('form', 'j-edit');
    const d = J().decisionOf(entry.text);
    let choice = d.decision || 'note';
    const seg = make('div', 'gn-seg');
    seg.setAttribute('role', 'group');
    seg.setAttribute('aria-label', 'Decision');
    const buttons = [['retain', 'Retain'], ['change', 'Change'], ['note', 'Note only']].map(([v, l]) => {
      const b = make('button', null, l);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(v === choice));
      b.addEventListener('click', () => { choice = v; buttons.forEach((x, i) => x.setAttribute('aria-pressed', String(['retain', 'change', 'note'][i] === choice))); });
      seg.appendChild(b);
      return b;
    });
    const area = make('textarea', 'gn-textarea');
    area.value = d.reason;
    area.maxLength = J().LIMITS.text - 8;
    area.setAttribute('aria-label', 'Edit the reason');
    const row = make('div', 'jb-row');
    const vis = make('label', 'jb-vis');
    const share = make('input');
    share.type = 'checkbox';
    share.checked = entry.visibility === 'desk';
    vis.append(share, make('span', null, 'Share with the desk'));
    const save = make('button', 'gn-btn gn-btn--primary gn-btn--sm', 'Save');
    save.type = 'submit';
    const cancel = make('button', 'gn-btn gn-btn--sm gn-btn--ghost', 'Cancel');
    cancel.type = 'button';
    row.append(vis, save, cancel);
    const status = make('p', 'jb-status');
    status.setAttribute('role', 'status');
    wrap.append(seg, area, row, status);
    cancel.addEventListener('click', () => onDone(false));
    wrap.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!area.value.trim()) { status.className = 'jb-status jb-error'; status.textContent = 'The reason cannot be empty.'; return; }
      save.disabled = true;
      status.className = 'jb-status';
      status.textContent = 'Saving…';
      const text = DECISION_WORD[choice] ? DECISION_WORD[choice] + ': ' + area.value : area.value;
      const res = await J().api('PUT', '/api/journal/' + encodeURIComponent(entry.id),
        { text, visibility: share.checked ? 'desk' : 'private' });
      save.disabled = false;
      if (!res.ok) {
        status.className = 'jb-status jb-error';
        status.textContent = 'Not saved: ' + J().failure(res); // the edited text stays in the box
        return;
      }
      Object.assign(entry, res.body);
      onDone(true);
    });
    return wrap;
  }

  // ---------- the chosen entry ----------
  function renderDetail() {
    const card = $('j-detail');
    const entry = state.entries.find((e) => e.id === state.entry);
    card.hidden = !entry;
    for (const tr of $('j-list').children) {
      const on = tr.dataset.id === state.entry;
      tr.classList.toggle('is-sel', on);
      tr.setAttribute('aria-selected', String(on));
    }
    if (!entry) return;
    const d = state.view;
    const dec = J().decisionOf(entry.text);
    const body = $('j-detail-body');
    const actions = $('j-detail-actions');
    body.textContent = '';
    actions.textContent = '';
    const head = make('div', 'j-detail-head');
    head.appendChild(targetLink(entry, d, 'j-detail-target'));
    const meta = make('div', 'j-detail-meta');
    meta.appendChild(decisionBadge(dec.decision));
    meta.appendChild(make('span', 'gn-meta mono', 'As of ' + J().asOfWords(entry.as_of)));
    meta.appendChild(make('span', 'gn-badge' + (entry.visibility === 'desk' ? ' gn-badge--info' : ''), entry.visibility === 'desk' ? 'Shared with the desk' : 'Private'));
    meta.appendChild(make('span', 'gn-meta', entry.mine ? 'You' : (entry.author && entry.author.email) || 'Someone on the desk'));
    if (entry.updated_at && entry.updated_at !== entry.created_at) meta.appendChild(make('span', 'gn-meta', 'edited'));
    head.appendChild(meta);
    body.appendChild(head);
    const text = make('p', 'j-text', dec.reason || entry.text); // text, never markup
    body.appendChild(text);
    body.appendChild(knownThen(entry));
    body.appendChild(happenedAfter(entry, d));
    if (entry.mine) {
      const edit = make('button', 'gn-btn gn-btn--sm gn-btn--ghost', 'Edit');
      edit.type = 'button';
      edit.addEventListener('click', () => {
        if (body.querySelector('.j-edit')) return;
        text.hidden = true;
        const form = editor(entry, (saved) => {
          form.remove();
          text.hidden = false;
          if (saved) { renderRows(); renderDetail(); }
        });
        body.insertBefore(form, text.nextSibling);
        form.querySelector('textarea').focus();
      });
      actions.appendChild(edit);
    }
    const close = make('button', 'gn-icon-btn', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close the entry');
    close.addEventListener('click', () => { const id = state.entry; state.entry = ''; writeAddress(); renderDetail(); const tr = $('j-list').querySelector(`tr[data-id="${id}"] .j-open`); if (tr) tr.focus(); });
    actions.appendChild(close);
  }
  function choose(id, focus) {
    state.entry = state.entry === id ? '' : id;
    writeAddress();
    renderDetail();
    if (state.entry && focus && window.matchMedia && window.matchMedia('(max-width: 1099px)').matches) {
      $('j-detail').scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
  }

  // ---------- the table ----------
  function renderRows() {
    const d = state.view;
    const list = $('j-list');
    list.textContent = '';
    const shown = state.entries.filter((e) => {
      if (!state.decision) return true;
      const x = J().decisionOf(e.text).decision;
      return state.decision === 'note' ? !x : x === state.decision;
    });
    shown.forEach((entry) => {
      const dec = J().decisionOf(entry.text);
      const tr = make('tr');
      tr.dataset.id = entry.id;
      const t = make('td', 'mono j-c-time', J().asOfWords(entry.as_of));
      t.setAttribute('data-value', entry.as_of);
      tr.appendChild(t);
      const about = make('td', 'trunc');
      const link = targetLink(entry, d);
      about.title = link.textContent;
      about.appendChild(link);
      tr.appendChild(about);
      const dc = make('td');
      dc.setAttribute('data-value', dec.decision ? DECISION_WORD[dec.decision] : 'Note');
      dc.appendChild(decisionBadge(dec.decision));
      tr.appendChild(dc);
      const reason = make('td', 'trunc j-c-reason');
      reason.title = dec.reason;
      const open = make('button', 'j-open', dec.reason || entry.text);
      open.type = 'button';
      open.setAttribute('aria-label', 'Open the entry: ' + (dec.reason || entry.text).slice(0, 80));
      open.addEventListener('click', (e) => { e.stopPropagation(); choose(entry.id, true); });
      reason.appendChild(open);
      if (!entry.mine) reason.appendChild(make('span', 'gn-meta j-by', (entry.author && entry.author.email) || 'desk'));
      tr.appendChild(reason);
      const price = entry.snapshot && typeof entry.snapshot.price === 'number' ? entry.snapshot.price : null;
      const p = make('td', 'num', price === null ? '–' : fmtPrice(price));
      p.setAttribute('data-value', price === null ? '' : String(price));
      if (price === null) p.title = 'No price in the snapshot';
      tr.appendChild(p);
      const after = afterFor(entry, d);
      const a = make('td');
      a.setAttribute('data-value', after ? String(after.total) : '-1');
      if (!after) a.appendChild(make('span', 'gn-nodata', 'No data'));
      else if (!after.total) a.appendChild(make('span', 'gn-badge', 'Nothing yet'));
      else a.appendChild(make('span', 'gn-badge gn-badge--info', `${after.total} ${after.total === 1 ? 'notice' : 'notices'} ${after.short}`.trim()));
      tr.appendChild(a);
      tr.addEventListener('click', (e) => { if (e.target && e.target.closest && e.target.closest('a, button')) return; choose(entry.id, true); });
      list.appendChild(tr);
    });
    $('j-table-wrap').hidden = !shown.length;
    if (window.GNUI && typeof window.GNUI.resort === 'function') window.GNUI.resort($('j-table'));
    const total = state.entries.length;
    $('j-count').textContent = !total ? '' : shown.length === total ? `${total} ${total === 1 ? 'entry' : 'entries'}` : `${shown.length} of ${total}`;
    renderEmpty(shown.length, total);
    if (state.entry && !shown.some((e) => e.id === state.entry)) state.entry = '';
    renderDetail();
  }

  function renderEmpty(shown, total) {
    const host = $('j-empty');
    host.textContent = '';
    if (shown) return;
    const box = make('div', 'gn-empty');
    box.setAttribute('role', 'status');
    const actions = make('div', 'gn-empty-actions');
    if (filtered() && (total || state.scope === 'mine')) {
      box.append(make('p', 'gn-empty-title', 'No entries match these filters'),
        make('p', 'gn-empty-body', 'Nothing at or before the replay clock fits them. Clear the filters to see every entry.'));
      const clear = make('button', 'gn-btn', 'Clear filters');
      clear.type = 'button';
      clear.addEventListener('click', resetFilters);
      actions.appendChild(clear);
    } else if (state.scope === 'desk') {
      box.append(make('p', 'gn-empty-title', 'Nothing is shared with the desk yet'),
        make('p', 'gn-empty-body', 'Entries appear here when someone ticks Share with the desk.'));
    } else {
      box.append(make('p', 'gn-empty-title', 'No decisions in your journal yet'),
        make('p', 'gn-empty-body', 'Open an alert or an event, decide, and save. Each entry keeps what you knew then.'));
      const alerts = make('a', 'gn-btn', 'Open alerts');
      alerts.href = '/alerts';
      actions.appendChild(alerts);
      const ex = exampleEvent();
      if (ex) { const a = make('a', 'gn-btn gn-btn--ghost', 'See an example'); a.href = ex; actions.appendChild(a); }
    }
    if (actions.children.length) box.appendChild(actions);
    host.appendChild(box);
  }

  function exampleEvent() {
    const d = state.data;
    if (!d || !d.events || !d.events.size) return null;
    const clock = S().asOf();
    const ids = [...d.events.values()].filter((e) => e && e.id && (!e.t || String(e.t).slice(0, 16) <= clock)).map((e) => e.id);
    const id = ids[0] || [...d.events.keys()][0];
    return id ? '/event/' + encodeURIComponent(id) : null;
  }

  // ---------- loading ----------
  async function load() {
    const seq = ++state.seq;
    const status = $('j-status');
    status.className = 'j-status gn-loading';
    status.textContent = 'Loading your journal…';
    const f = filters();
    $('j-clock').textContent = 'Entries up to the replay clock, ' + J().asOfWords(S().asOf());
    const qs = new URLSearchParams(f).toString();
    const [res, d] = await Promise.all([J().api('GET', '/api/journal?' + qs), J().data()]);
    if (seq !== state.seq) return; // a newer request is on its way
    state.data = d;
    if (!res.ok) {
      if (res.status === 401) { showSignedOut(); return; }
      status.className = 'j-status gn-error';
      status.textContent = 'The journal could not be loaded: ' + J().failure(res) + ' ';
      const retry = make('button', 'gn-btn gn-btn--sm', 'Retry');
      retry.type = 'button';
      retry.addEventListener('click', load);
      status.appendChild(retry);
      return; // the table and the filters stay as they were
    }
    const entries = Array.isArray(res.body.entries) ? res.body.entries : [];
    /* replay-year: a year bake holds its notices by month; "what happened after" reads the
       months from the earliest entry shown up to the clock. */
    let view = d;
    if (d && d.year && entries.length && S().notices) {
      const times = entries.map((e) => String(e.as_of || '')).filter((t) => S().validAt(t)).sort();
      if (times.length) {
        const advisories = await S().notices(S().monthOf(times[0]), S().monthOf(S().asOf()));
        if (seq !== state.seq) return;
        view = Object.assign({}, d, { advisories: Array.isArray(advisories) ? advisories : null });
      }
    }
    state.entries = entries;
    state.view = view;
    status.className = 'j-status';
    status.textContent = res.body.truncated ? `Showing the first ${entries.length} of ${res.body.total}. Narrow the filters to see the rest.` : '';
    if (state.event) {
      const ev = d && d.events.get(state.event);
      $('f-event').textContent = 'Event: ' + (ev && ev.title ? ev.title : state.event);
    }
    renderRows();
  }

  let timer = null;
  const reload = () => { clearTimeout(timer); timer = setTimeout(() => { writeAddress(); syncSegs(); load(); }, 250); };
  function resetFilters() {
    $('j-filter-form').reset();
    state.event = '';
    state.decision = '';
    state.scope = 'mine';
    syncSegs();
    writeAddress();
    load();
  }

  // ---------- the new-entry card ----------
  function mount(kind, id) {
    if (state.box) state.box.destroy();
    state.box = J().mountBox($('j-box'), { kind, id, title: null, onSaved: () => load() });
    $('j-pick').hidden = true;
    $('j-new-hint').textContent = 'Writing on ' + (kind === 'event' ? 'event ' : 'plant ') + id + '.';
    const other = make('button', 'gn-btn gn-btn--sm gn-btn--ghost j-other', 'Something else');
    other.type = 'button';
    other.addEventListener('click', () => {
      if (state.box) state.box.destroy();
      state.box = null;
      other.remove();
      $('j-pick').hidden = false;
      $('j-new-hint').textContent = 'Write on an event or a plant. Event and alert pages carry the same box.';
    });
    $('j-box').appendChild(other);
  }

  async function fillPickList() {
    const d = await J().data();
    const list = $('j-pick-list');
    list.textContent = '';
    const kind = $('j-pick-kind').value;
    // Codes only: a plant's name can give away its technology, so the list never shows names.
    const values = kind === 'event' ? [...d.events.keys()] : [...d.sites.keys()];
    values.slice(0, 600).forEach((v) => { const o = make('option'); o.value = v; list.appendChild(o); });
    $('j-pick-id').placeholder = kind === 'event' ? (values[0] || 'pedc-u2-2026-09-21') : '08PEDC';
  }

  // ---------- signed in / out ----------
  async function showSignedOut() {
    $('j-signed').hidden = true;
    $('j-new-btn').hidden = true;
    $('j-signin').hidden = false;
    const unavailable = S().authState() === 'unavailable';
    $('j-signin-text').textContent = unavailable
      ? 'Sign-in is not set up on this server, so the journal cannot open here. Each entry is a decision you made on an event or a plant.'
      : 'Each entry is a decision you made on an event or a plant. Entries are private unless you share them with the desk.';
    $('j-signin-btn').hidden = unavailable;
    $('j-clock').textContent = '';
    state.data = await J().data();
    const ex = exampleEvent();
    if (ex) { $('j-example').href = ex; $('j-example').textContent = 'See an example event'; }
  }
  function showSignedIn() {
    $('j-signin').hidden = true;
    $('j-signed').hidden = false;
    $('j-new-btn').hidden = false;
    if (!state.started) {
      state.started = true;
      if (state.event) mount('event', state.event);
      else if ($('f-plant').value) mount('plant', $('f-plant').value);
      fillPickList();
    }
    load();
  }
  function onAuth() {
    const s = S();
    if (s.authState() === 'starting') return;
    if (s.user()) showSignedIn(); else showSignedOut();
  }

  function start() {
    if (!S() || !J()) return;
    readAddress();
    syncSegs();
    $('j-signin-btn').addEventListener('click', () => S().signIn());
    $('j-new-btn').addEventListener('click', () => { $('j-new').scrollIntoView({ block: 'start', behavior: 'smooth' }); const f = $('j-pick-id'); if (f && !$('j-pick').hidden) f.focus(); });
    $('j-filter-form').addEventListener('input', reload);
    $('j-filter-form').addEventListener('change', reload);
    $('j-filter-form').addEventListener('submit', (e) => { e.preventDefault(); writeAddress(); load(); });
    $('f-scope').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-value]');
      if (!b || b.dataset.value === state.scope) return;
      state.scope = b.dataset.value; state.entry = ''; syncSegs(); writeAddress(); load();
    });
    $('f-decision').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-value]');
      if (!b) return;
      state.decision = b.dataset.value; syncSegs(); writeAddress(); renderRows();
    });
    $('f-event-clear').addEventListener('click', () => { state.event = ''; syncSegs(); writeAddress(); load(); });
    $('f-reset').addEventListener('click', resetFilters);
    $('j-pick-kind').addEventListener('change', fillPickList);
    $('j-pick').addEventListener('submit', (e) => {
      e.preventDefault();
      const kind = $('j-pick-kind').value;
      const id = $('j-pick-id').value.trim();
      const err = $('j-pick-error');
      if (!J().validTarget(kind, id)) { err.textContent = 'Enter an event id or a plant code: letters, digits, dot or dash.'; return; }
      err.textContent = '';
      mount(kind, id);
    });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.entry && !e.target.closest('input, textarea, select')) { state.entry = ''; writeAddress(); renderDetail(); } });
    S().onUser(onAuth);
    S().onAsOf(() => { if (S().user()) load(); });
    onAuth();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
