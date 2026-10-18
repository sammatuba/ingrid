/* InGRID decision box (ericka-desk slice 8, E26; platform polish PP-B2): the compact box any
   page can mount to keep a decision in the journal, plus the helpers the journal page shares.

   Load after shell.js (which defines window.GNShell) and before the page script that mounts it:
     <script src="/grid/__NOWCAST_STAMP__/journal-box.js" defer></script>
   and load journal.css for its look. No inline style and no markup insertion: every value is written as text.

   CONTRACT

     const box = window.GNJournal.mountBox(hostElement, {kind, id, snapshot, onSaved});

   - hostElement  an Element; the box replaces its children.
   - kind         'event' or 'plant'.
   - id           the event id (as in /event/<id>) or the plant code (as in /plant/<code>):
                  letters, digits, dot, dash, underscore, at most 80. Anything else shows an error
                  in the box and nothing is saved.
   - snapshot     optional, what was known when the entry is written:
                    {price: number|null (PHP/MWh), region: 'CLUZ'|'CVIS'|'CMIN'|null,
                     latest_notice: string|null, known_facts: [string]}
                  either that object, or a function (asOf) => object or Promise of it. Omitted, the
                  box builds it from the baked replay files at the clock (region of the plant or the
                  event's plant, the region's median price at the clock, the region's latest notice
                  at or before the clock, the event title and the plant's earlier notices). Long
                  values are cut to the server's limits (notice 500 characters; at most 20 facts of
                  300). The box shows it as the evidence pinned to the entry, and the person can
                  unpin any line before saving.
   - onSaved      optional function (entry) called with the saved entry as the server returns it.
   Optional, added by PP-B2 (a caller that names none gets the defaults):
   - decision     true (the default) shows the choice Retain, Change or Note only. The choice is
                  kept in the entry's own text as its first word ("Retain: <reason>"), so the
                  journal's record and routes are unchanged; `GNJournal.decisionOf(text)` reads it.
                  false keeps the box a plain note.
   - title        the box's heading; null for none. Defaults to "Add to journal".

   The entry is posted to POST /api/journal with `Authorization: Bearer <GNShell.idToken()>`,
   `as_of` = GNShell.asOf() at the moment of saving, the text as typed (after the decision word),
   and the visibility the toggle shows: private (default) or shared with the desk (decision D2).
   The author is never sent; the server takes it from the token. Signed out, the box is one line
   with a sign-in action (GNShell.signIn()) and follows GNShell.onUser. A failed save shows the
   error in the box and keeps the text. A saved entry shows its receipt in place of the form.

   Returns {element, destroy()}: `destroy()` empties the host.

   Also exposed for the journal page: GNJournal.data() (the baked files, cached),
   GNJournal.api(method, path, body) (an authorised JSON call that resolves {ok, status, body}),
   GNJournal.snapshotAt(kind, id, asOf), GNJournal.siteOf(kind, id, data), GNJournal.opText(text),
   GNJournal.asOfWords(t), GNJournal.decisionOf(text), GNJournal.REGIONS,
   GNJournal.validTarget(kind, id). */
(() => {
  'use strict';
  const TARGET_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;
  const REGIONS = { CLUZ: 'Luzon', CVIS: 'Visayas', CMIN: 'Mindanao' };
  const LIMITS = { text: 4000, notice: 500, facts: 20, fact: 300 };
  const DECISIONS = { retain: 'Retain', change: 'Change' };
  const shell = () => window.GNShell || null;

  function make(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }

  const validTarget = (kind, id) => (kind === 'event' || kind === 'plant') && typeof id === 'string' && TARGET_ID.test(id);
  const opText = (s) => String(s).replace(/\b([01]\d|2[0-3])([0-5]\d)H\b/g, '$1:$2').replace(/\s{2,}/g, ' ').trim();
  const asOfWords = (t) => {
    if (!t || t.length < 16) return String(t || '');
    const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(t.slice(5, 7)) - 1];
    if (!m || !/^\d{4}-\d{2}-\d{2}/.test(t)) return t;
    return Number(t.slice(8, 10)) + ' ' + m + ' ' + t.slice(11, 16);
  };
  const cut = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
  /* The decision an entry's text opens with, and the rest of it: {decision: 'retain'|'change'|null, reason}. */
  function decisionOf(text) {
    const s = String(text == null ? '' : text);
    const m = /^(Retain|Change):[ \t]*/.exec(s);
    return m ? { decision: m[1].toLowerCase(), reason: s.slice(m[0].length) } : { decision: null, reason: s };
  }

  // ---------- the baked replay files, fetched once ----------
  let loaded = null;
  function data() {
    if (loaded) return loaded;
    const prefix = (shell() && shell().data) || '/grid-data/';
    const get = (name) => fetch(prefix + name, { headers: { Accept: 'application/json' } })
      .then((r) => (r.ok ? r.json() : null)).catch(() => null);
    /* replay-year: a year bake (replay.json) is read by day and month at the snapshot's own time
       (`atTime` below); the whole-window files are read only for a bake without it. */
    const S = shell();
    const year = S && S.ready ? S.ready : Promise.resolve(null);
    loaded = year.then((index) => Promise.all([index ? null : get('advisories.json'), get('events.json'), get('sites.json'),
      index ? null : get('regions.json'), index]))
      .then(([advisories, events, sites, regions, index]) => ({
        year: !!index,
        advisories: Array.isArray(advisories) ? advisories : null,
        events: new Map((Array.isArray(events) ? events : []).filter((e) => e && e.id).map((e) => [e.id, e])),
        sites: new Map((Array.isArray(sites) ? sites : []).filter((s) => s && s.s).map((s) => [s.s, s])),
        regions: regions && Array.isArray(regions.t) && regions.grids ? regions : null,
      }));
    return loaded;
  }
  /* The replay as of `asOf`: the static files, plus (in a year bake) the day file of the as-of's
     day as `regions` and the notices of its month and the one before as `advisories`. A missing
     day has no day file: its price is No data. */
  async function atTime(asOf) {
    const d = await data();
    if (!d.year) return d;
    const S = shell();
    const month = S.monthOf(asOf);
    const [day, advisories] = await Promise.all([S.dayFile(asOf.slice(0, 10)), S.notices(S.monthPlus(month, -1), month)]);
    return Object.assign({}, d, {
      regions: day && Array.isArray(day.t) && day.grids ? day : null,
      advisories: Array.isArray(advisories) ? advisories : null,
    });
  }

  /* The plant code a target is about: the plant itself, or the event's plant. */
  function siteOf(kind, id, d) {
    if (kind === 'plant') return id;
    const ev = d && d.events.get(id);
    return ev && typeof ev.site === 'string' ? ev.site : null;
  }
  function regionOf(kind, id, d) {
    const site = siteOf(kind, id, d);
    const s = site && d.sites.get(site);
    return s && REGIONS[s.g] ? s.g : null;
  }
  /* A plant's short name as notices write it: the code without its leading grid digits. */
  const plantToken = (code) => (code ? code.replace(/^\d+/, '') : '');
  function mentions(text, code) {
    const token = plantToken(code);
    if (token.length < 3) return false;
    return new RegExp('(^|[^A-Za-z0-9])' + token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^A-Za-z0-9])', 'i').test(text);
  }

  function priceAt(d, region, asOf) {
    if (!d.regions || !region || !d.regions.grids[region]) return null;
    const t = d.regions.t;
    let i = -1;
    for (let k = 0; k < t.length && t[k] <= asOf; k += 1) i = k;
    const series = d.regions.grids[region].lmp_median;
    const v = i >= 0 && Array.isArray(series) ? series[i] : null;
    return typeof v === 'number' && Number.isFinite(v) ? v : null;
  }

  async function snapshotAt(kind, id, asOf) {
    const d = await atTime(asOf);
    const region = regionOf(kind, id, d);
    const until = asOf + ':59';
    const site = siteOf(kind, id, d);
    let latest = null;
    const facts = [];
    if (kind === 'event') {
      const ev = d.events.get(id);
      if (ev && ev.t <= until && ev.title) facts.push(String(ev.title));
    }
    if (d.advisories) {
      const before = d.advisories.filter((a) => a && typeof a.t === 'string' && a.t <= until);
      const inRegion = before.filter((a) => a.grid === region);
      const last = inRegion[inRegion.length - 1];
      if (last) latest = asOfWords(last.t) + ' · ' + opText(last.text);
      if (site) before.filter((a) => mentions(String(a.text), site)).slice(-3)
        .map((a) => asOfWords(a.t) + ' · ' + opText(a.text))
        .forEach((line) => { if (line !== latest) facts.push(line); });  // the latest notice is its own field
    }
    return { price: priceAt(d, region, asOf), region, latest_notice: latest, known_facts: facts };
  }

  function clean(snap) {
    const s = snap && typeof snap === 'object' ? snap : {};
    const price = typeof s.price === 'number' && Number.isFinite(s.price) ? s.price : null;
    const region = typeof s.region === 'string' && REGIONS[s.region] ? s.region : null;
    const notice = typeof s.latest_notice === 'string' && s.latest_notice.trim() ? cut(s.latest_notice, LIMITS.notice) : null;
    const facts = (Array.isArray(s.known_facts) ? s.known_facts : [])
      .filter((f) => typeof f === 'string' && f.trim()).slice(0, LIMITS.facts).map((f) => cut(f, LIMITS.fact));
    return { price, region, latest_notice: notice, known_facts: facts };
  }

  // ---------- the authorised JSON call ----------
  async function api(method, path, body) {
    const s = shell();
    const token = s ? await s.idToken().catch(() => null) : null;
    const headers = { Accept: 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let r;
    try {
      r = await fetch(path, { method, headers, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (e) {
      return { ok: false, status: 0, body: { message: 'The server could not be reached. Check the connection and try again.' } };
    }
    let parsed = null;
    try { parsed = await r.json(); } catch (e) { parsed = null; }
    return { ok: r.ok, status: r.status, body: parsed || { message: 'The server answered ' + r.status + '.' } };
  }
  const failure = (res) => (res.body && typeof res.body.message === 'string' ? res.body.message : 'The journal call failed (' + res.status + ').');
  const fmtPrice = (v) => '₱' + Math.round(v).toLocaleString('en-US') + '/MWh';

  // ---------- the box ----------
  let seq = 0;
  function mountBox(host, opts) {
    const o = opts || {};
    const decide = o.decision !== false;
    const root = make('div', 'jb' + (decide ? ' jb--decide' : ''));
    host.textContent = '';
    host.appendChild(root);
    const listeners = { alive: true };

    if (!validTarget(o.kind, o.id)) {
      root.appendChild(make('p', 'jb-error', 'This journal box has no valid event or plant to write about.'));
      return { element: root, destroy() { host.textContent = ''; } };
    }
    const uid = 'jb' + (seq += 1);
    const title = o.title === null ? null : make('h3', 'jb-title', o.title || 'Add to journal');
    if (title) root.appendChild(title);

    // Signed out: one line and the sign-in action.
    const out = make('div', 'jb-out');
    const prompt = make('p', 'jb-prompt');
    const signBtn = make('button', 'gn-btn gn-btn--sm', 'Sign in');
    signBtn.type = 'button';
    signBtn.addEventListener('click', () => { if (shell()) shell().signIn(); });
    out.append(prompt, signBtn);

    // Signed in: the form.
    const form = make('form', 'jb-form');
    form.noValidate = true;
    let choice = null;
    const seg = make('div', 'gn-seg jb-seg');
    seg.setAttribute('role', 'group');
    seg.setAttribute('aria-label', 'Decision');
    const segButtons = [['retain', 'Retain'], ['change', 'Change'], ['note', 'Note only']].map(([value, label]) => {
      const b = make('button', null, label);
      b.type = 'button';
      b.dataset.value = value;
      b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', () => { choice = value; syncSeg(); status.textContent = ''; });
      seg.appendChild(b);
      return b;
    });
    const segHint = make('p', 'jb-hint', 'Retain keeps the accepted position. Change says it should move.');
    const syncSeg = () => segButtons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.value === choice)));
    const label = make('label', 'jb-label', decide ? 'Reason' : 'Note');
    const area = make('textarea', 'gn-textarea jb-text');
    area.maxLength = LIMITS.text;
    area.rows = 3;
    area.placeholder = decide ? 'Why, in a sentence or two. What would change your mind?' : 'What you see, what you expect, what you would do.';
    area.id = uid + '-text';
    label.htmlFor = area.id;
    // The evidence pinned to the entry: the snapshot at the clock, one line each.
    const pins = make('div', 'jb-pins');
    const pinsHead = make('div', 'jb-pins-head');
    pinsHead.append(make('span', 'gn-label', 'Pinned with it'), make('span', 'gn-meta jb-when mono'));
    const pinList = make('ul', 'jb-pin-list');
    pins.append(pinsHead, pinList);
    const row = make('div', 'jb-row');
    const vis = make('label', 'jb-vis');
    const share = make('input');
    share.type = 'checkbox';
    vis.append(share, make('span', null, 'Share with the desk'));
    const save = make('button', decide ? 'gn-btn gn-btn--primary jb-save' : 'gn-btn jb-save', decide ? 'Save decision' : 'Save note');
    save.type = 'submit';
    row.append(vis, save);
    const status = make('p', 'jb-status');
    status.setAttribute('role', 'status');
    if (decide) form.append(seg, segHint);
    form.append(label, area, pins, row, status);

    // Saved: the receipt in place of the form.
    const done = make('div', 'jb-done');
    done.setAttribute('role', 'status');
    done.hidden = true;

    root.append(out, form, done);

    let snap = null;
    const unpinned = new Set();
    function pinLines() {
      const s = clean(snap);
      const lines = [];
      if (s.price !== null) lines.push({ key: 'price', text: 'Price at the clock ' + fmtPrice(s.price) + (s.region ? ', ' + REGIONS[s.region] : '') });
      else if (s.region) lines.push({ key: 'region', text: 'Region ' + REGIONS[s.region] });
      if (s.latest_notice) lines.push({ key: 'notice', text: 'Latest notice ' + s.latest_notice });
      s.known_facts.forEach((f) => lines.push({ key: 'fact:' + f, text: f }));
      return lines;
    }
    function renderPins() {
      pinList.textContent = '';
      const lines = pinLines();
      let kept = 0;
      lines.forEach((p) => {
        const li = make('li', unpinned.has(p.key) ? 'jb-pin jb-pin--off' : 'jb-pin');
        li.appendChild(make('span', 'jb-pin-t', p.text));
        const b = make('button', 'gn-icon-btn jb-unpin', unpinned.has(p.key) ? '+' : '×');
        b.type = 'button';
        b.setAttribute('aria-label', (unpinned.has(p.key) ? 'Pin again: ' : 'Unpin: ') + p.text);
        b.addEventListener('click', () => { if (unpinned.has(p.key)) unpinned.delete(p.key); else unpinned.add(p.key); renderPins(); });
        li.appendChild(b);
        pinList.appendChild(li);
        if (!unpinned.has(p.key)) kept += 1;
      });
      if (!lines.length) pinList.appendChild(make('li', 'jb-pin-none gn-meta', 'Nothing on record at this clock to pin.'));
      pins.dataset.kept = String(kept);
    }
    function pinned() {
      const s = clean(snap);
      return {
        price: unpinned.has('price') ? null : s.price,
        region: s.region,
        latest_notice: unpinned.has('notice') ? null : s.latest_notice,
        known_facts: s.known_facts.filter((f) => !unpinned.has('fact:' + f)),
      };
    }
    let ticket = 0;
    async function loadSnapshot() {
      const s = shell();
      const asOf = s ? s.asOf() : null;
      pinsHead.lastChild.textContent = asOf ? 'Known at ' + asOfWords(asOf) : '';
      const mine = (ticket += 1);
      let next = null;
      try {
        next = typeof o.snapshot === 'function' ? await o.snapshot(asOf) : o.snapshot ? o.snapshot : await snapshotAt(o.kind, o.id, asOf);
      } catch (e) { next = null; }
      if (mine !== ticket || !listeners.alive) return;
      snap = next;
      renderPins();
    }

    function renderAuth() {
      if (!listeners.alive) return;
      const s = shell();
      const user = s ? s.user() : null;
      const state = s ? s.authState() : 'unavailable';
      form.hidden = !user || !done.hidden;
      out.hidden = Boolean(user) || state === 'starting';
      prompt.textContent = state === 'unavailable'
        ? 'Sign-in is not set up on this server, so the journal is read only here.'
        : decide ? 'Sign in to keep this decision in your journal.' : 'Sign in to add this to your journal.';
      signBtn.hidden = state === 'unavailable';
      if (user && !snap) loadSnapshot();
    }

    function showDone(entry, decision) {
      done.textContent = '';
      done.appendChild(make('p', 'jb-done-title', decide ? 'Decision saved to your journal' : 'Saved to your journal'));
      const facts = (entry.snapshot && Array.isArray(entry.snapshot.known_facts)) ? entry.snapshot.known_facts.length : 0;
      const parts = [decision ? DECISIONS[decision] : (decide ? 'Note' : null), 'as of ' + asOfWords(entry.as_of),
        entry.visibility === 'desk' ? 'shared with the desk' : 'private', facts + (facts === 1 ? ' fact pinned' : ' facts pinned')].filter(Boolean);
      done.appendChild(make('p', 'jb-receipt mono', parts.join(' · ')));
      const actions = make('div', 'jb-row');
      const open = make('a', 'gn-btn gn-btn--sm', 'Open in journal');
      open.href = '/journal?' + o.kind + '=' + encodeURIComponent(o.id);
      const again = make('button', 'gn-btn gn-btn--sm gn-btn--ghost', 'Write another');
      again.type = 'button';
      again.addEventListener('click', () => { done.hidden = true; renderAuth(); area.focus(); });
      actions.append(open, again);
      done.appendChild(actions);
      done.hidden = false;
      form.hidden = true;
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const s = shell();
      const words = area.value;
      if (decide && !choice) { status.className = 'jb-status jb-error'; status.textContent = 'Pick Retain, Change or Note only first.'; return; }
      if (!words.trim()) { status.className = 'jb-status jb-error'; status.textContent = decide ? 'Write a reason first.' : 'Write a note first.'; return; }
      if (!s || !s.user()) { renderAuth(); return; }
      save.disabled = true;
      status.className = 'jb-status';
      status.textContent = 'Saving…';
      const asOf = s.asOf();
      if (!snap) await loadSnapshot();
      const decision = decide && DECISIONS[choice] ? choice : null;
      const text = decision ? DECISIONS[decision] + ': ' + words : words;
      const res = await api('POST', '/api/journal', {
        as_of: asOf, target: { kind: o.kind, id: o.id }, text, snapshot: pinned(),
        visibility: share.checked ? 'desk' : 'private',
      });
      save.disabled = false;
      if (!listeners.alive) return;
      if (!res.ok) {
        // Keep the text: the trader's words are never lost to a failed call.
        status.className = 'jb-status jb-error';
        status.textContent = 'Not saved: ' + failure(res);
        return;
      }
      area.value = '';
      share.checked = false;
      choice = null;
      syncSeg();
      status.textContent = '';
      showDone(res.body, decision);
      if (typeof o.onSaved === 'function') { try { o.onSaved(res.body); } catch (err) { /* the caller's own fault */ } }
    });

    const s = shell();
    if (s) {
      s.onUser(renderAuth);
      s.onAsOf(() => { if (s.user()) loadSnapshot(); });
    }
    // GNShell calls onUser on every sign-in state change, including 'starting' -> 'unavailable'.
    renderAuth();

    return {
      element: root,
      destroy() { listeners.alive = false; host.textContent = ''; },
    };
  }

  window.GNJournal = {
    mountBox, data, api, failure, snapshotAt, siteOf, regionOf, mentions, opText, asOfWords,
    decisionOf, validTarget, REGIONS, LIMITS,
  };
})();
