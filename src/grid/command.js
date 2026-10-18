/* The command bar (UX-1) and its grounded answers (UX-2). Design file:
   docs/work/ui-refinement-2026-10-18/intent.md outcomes 1 and 2, design-brief.md, and the server
   contract desk-api.md.

   One floating bar in the lower middle of every page but /ask (shell.js `ensureDock()` loads this
   file). It combines search and questions:
   * focus on the empty bar lists the desk's suggested prompts for this page and clock
     (`GET /api/desk/prompts`), then the page's recorded questions (ask.js reads them);
   * typing searches the ontology (`GET /api/desk/search`) and lists plants, events, regions,
     HVDC links, notices, datasets and pages, with an "Ask Ingrid" row on top;
   * asking opens a sheet that grows upward from the bar. `POST /api/desk/answer` composes the
     answer from the baked records: Gemini on Vertex AI picks the desk tools and writes the prose
     (live for a signed-in person, a recorded run otherwise), and the server checks every number
     against the cited records, falling back to its deterministic composer. A question it cannot
     match goes to ask.js (a recorded plan, or the agent service for a signed-in person), and only
     then shows the desk's own no-match line.

   Every answer carries a model badge from the response's `model` field. The bar names Gemini only
   when that field says a Gemini run (live or recorded) wrote the answer. A composed answer says
   it was composed from records, with the fallback reason on hover.

   While a live Gemini answer is on its way, each tool step the server reports appears under the
   pending line as it runs (the answer stream). No step is drawn before the server sends it.

   An answer shows its ontology trace (collapsed, revealed step by step when it lands), prose
   whose figures carry numbered citations and whose entities are links with a preview card, and
   the basis line. The thread lives in this browser session (sessionStorage), so it follows the
   person from page to page. The page's `#ask` mount moves into the sheet's "Cases and threads"
   panel, where ask.js keeps the sign-in state, cases, queue, threads and confirmations.

   Every figure printed here is a field the server formatted. This file does no arithmetic on a
   figure except to draw a sparkline from the preview's own series. */
(() => {
  'use strict';
  if (typeof window === 'undefined' || typeof document === 'undefined' || window.GNCommand) return;
  const PARTS = String(window.location.pathname || '/').split('/').filter(Boolean);
  /* Platform polish: on /ask the bar is the page. The same conversation (trace, citations,
     previews, the model badge, follow-ups) fills the centre of the workspace, with the composer at
     its foot; ask.js's panel keeps the left rail (cases, the queue, threads). */
  const WORKSPACE = PARTS[0] === 'ask';
  /* The product's and the assistant's names come from the shell (GNShell.brand, GNShell.agent),
     so a rename is one line there. AGENT reads inside a sentence ("Ask Ingrid");
     AGENT_CAP opens one; AGENT_SHORT is a label ("Desk", "Ingrid"). */
  const SHELL = window.GNShell || {};
  const BRAND = String(SHELL.brand || '');
  const AGENT = String(SHELL.agent || 'the assistant');
  const AGENT_CAP = AGENT.charAt(0).toUpperCase() + AGENT.slice(1);
  const AGENT_SHORT = AGENT.replace(/^the\s+/i, '').replace(/^./, (c) => c.toUpperCase());
  const isOpen = () => WORKSPACE || state.open;

  const API = '/api/desk/';
  const STORE_KEY = 'nowcast.command.v1';
  const MAX_TURNS = 12;
  const STEP_MS = 90;
  const SITE_HREF = /^\/(?![/\\])[A-Za-z0-9/_\-.~%#?=&:,+]*$/;
  /* The mount ask.js renders into. A page that redraws its main area on a failed read can drop
     the mount from the document. ask.js keeps rendering into it, so the bar adopts it from there. */
  const findMount = () => document.getElementById('ask')
    || (window.DeskAsk && window.DeskAsk.mount) || null;
  const mount = findMount();
  /* The desk API's page key is the route's first segment (`plants`, `notices`, `event`), not the
     mount's plan-set key (/plants carries the `assets` mount). */
  const PAGE_KEY = PARTS[0] || 'home';
  /* The page's own words from its title: "Visayas price spike · Alerts · InGRID" reads
     "Visayas price spike" (the older "InGRID · Alerts" reads "Alerts"). */
  const PAGE_NAME = (() => {
    const first = String(document.title || '').split(/\s*·\s*/).filter((part) => part && part !== BRAND)[0];
    return first || BRAND;
  })();
  const MAC = /Mac|iPhone|iPad/.test(String(navigator.platform || navigator.userAgent || ''));

  const esc = (value) => String(value == null ? '' : value).replace(/[&<>"\x27]/g,
    (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\x27': '&#39;'}[c]));
  const list = (value) => (Array.isArray(value) ? value : []);
  const reduced = () => Boolean(window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const asOf = () => {
    try {
      const t = window.GNShell && typeof window.GNShell.asOf === 'function' && window.GNShell.asOf();
      if (t) return String(t).slice(0, 16);
    } catch (error) { /* no shell, no clock */ }
    return '';
  };
  const hhmm = (t) => (/T\d\d:\d\d/.test(String(t || '')) ? String(t).slice(11, 16) : '');
  const desk = () => window.DeskAsk || null;
  const safeHref = (href) => (typeof href === 'string' && SITE_HREF.test(href) ? href : '');

  /* ---------- glyphs: 16px line icons, only where they carry meaning ---------- */
  const PATHS = {
    search: '<circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/>',
    mic: '<rect x="6" y="1.75" width="4" height="8" rx="2"/><path d="M3.5 7.5a4.5 4.5 0 0 0 9 0M8 12v2.25"/>',
    send: '<path d="M8 13V3.5M4 7.5l4-4 4 4"/>',
    plant: '<path d="M9 1.5 3.5 9H8l-1 5.5L12.5 7H8z"/>',
    event: '<path d="M1.5 8.5h3l1.5-4 3 8 1.5-4h4"/>',
    region: '<path d="M2 4.25 6 2.5l4 2 4-1.75v9.5L10 14l-4-2-4 1.75z"/><path d="M6 2.5V12M10 4.5V14"/>',
    link: '<circle cx="3.25" cy="8" r="1.75"/><circle cx="12.75" cy="8" r="1.75"/><path d="M5 8h6"/>',
    notice: '<path d="M4 1.5h5l3 3v10H4z"/><path d="M9 1.5v3h3M6.25 8h3.5M6.25 11h3.5"/>',
    dataset: '<ellipse cx="8" cy="3.75" rx="5" ry="2"/><path d="M3 3.75v8.5c0 1.1 2.24 2 5 2s5-.9 5-2v-8.5M3 8c0 1.1 2.24 2 5 2s5-.9 5-2"/>',
    page: '<rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="M2 6h12"/>',
    ask: '<path d="M2.5 3h11v7.5h-6l-3 2.5v-2.5h-2z"/>',
    recorded: '<path d="M3.5 1.5h9v13l-1.5-1-1.5 1-1.5-1-1.5 1-1.5-1-1.5 1z"/><path d="M6 5.5h4M6 8.5h4"/>',
    resolve: '<circle cx="8" cy="8" r="5"/><circle cx="8" cy="8" r="1.5"/>',
    read: '<ellipse cx="8" cy="3.75" rx="5" ry="2"/><path d="M3 3.75v8.5c0 1.1 2.24 2 5 2s5-.9 5-2v-8.5"/>',
    relate: '<circle cx="3" cy="8" r="1.5"/><path d="M4.5 8h8M10 5.5 12.5 8 10 10.5"/>',
    compare: '<path d="M3 13.5v-5M8 13.5v-11M13 13.5V6"/>',
    filter: '<path d="M2 3h12l-4.5 5.5V13l-3-1.5v-3z"/>',
    rank: '<path d="M3 4h10M3 8h7M3 12h4"/>',
    trace: '<circle cx="3" cy="3.5" r="1.5"/><circle cx="13" cy="8" r="1.5"/><circle cx="3" cy="12.5" r="1.5"/><path d="M4.5 3.5h3a2 2 0 0 1 2 2V8h2M9.5 8v2.5a2 2 0 0 1-2 2h-3"/>',
    chev: '<path d="m4.5 6 3.5 3.5L11.5 6"/>',
    up: '<path d="m4.5 10 3.5-3.5 3.5 3.5"/>',
    history: '<circle cx="8" cy="8" r="6"/><path d="M8 4.75V8l2.25 1.5"/>',
    plus: '<path d="M8 3v10M3 8h10"/>',
    expand: '<path d="M9.5 2.5h4v4M13.5 2.5l-5 5M6.5 3.5h-3v9h9v-3"/>',
    out: '<path d="M6 3.5h6.5V10M12.5 3.5 4 12"/>',
    copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5v-2A1.5 1.5 0 0 0 9 2H4a1.5 1.5 0 0 0-1.5 1.5V9A1.5 1.5 0 0 0 4 10.5h1.5"/>',
    close: '<path d="m4 4 8 8M12 4l-8 8"/>',
    arrow: '<path d="M3 8h10M9 4l4 4-4 4"/>',
    dot: '<circle cx="8" cy="8" r="2"/>',
  };
  const icon = (name, cls) => '<svg class="gc-i' + (cls ? ' ' + cls : '') + '" viewBox="0 0 16 16"'
    + ' aria-hidden="true" focusable="false">' + (PATHS[name] || PATHS.dot) + '</svg>';

  const KIND_WORD = {plant: 'Plant', event: 'Event', region: 'Region', link: 'HVDC link',
                     notice: 'Notice', dataset: 'Dataset', page: 'Page'};
  const GROUP_WORD = {plant: 'Plants', event: 'Events', region: 'Regions', link: 'HVDC',
                      notice: 'Notices', dataset: 'Data', page: 'Pages'};
  const OP_WORD = {resolve: 'Resolve', read: 'Read', relate: 'Relate', compare: 'Compare',
                   filter: 'Filter', rank: 'Rank'};
  const PREVIEWABLE = ['plant', 'event', 'region', 'link', 'notice', 'dataset'];

  /* Where an entity lives when the server gave no link for it. */
  function defaultHref(kind, id) {
    const key = encodeURIComponent(String(id || ''));
    if (kind === 'plant') return '/plant/' + key;
    if (kind === 'event') return '/event/' + key;
    if (kind === 'dataset') return '/data#' + key;
    if (kind === 'notice') return '/notices';
    return '';
  }

  /* ---------- the thread, kept in this browser session ---------- */
  function storage() {
    try { return window.sessionStorage || null; } catch (error) { return null; }
  }
  function readStore() {
    const empty = {open: false, turns: []};
    const store = storage();
    if (!store) return empty;
    try {
      const saved = JSON.parse(store.getItem(STORE_KEY) || 'null');
      if (!saved || typeof saved !== 'object' || !Array.isArray(saved.turns)) return empty;
      const turns = saved.turns.filter((turn) => turn && typeof turn === 'object'
        && typeof turn.id === 'string' && typeof turn.q === 'string').slice(-MAX_TURNS);
      /* A question still in flight when the page changed never got its answer here. */
      turns.forEach((turn) => { if (turn.kind === 'pending') turn.kind = 'lost'; });
      return {open: saved.open === true && turns.length > 0, turns: turns,
              gemini: saved.gemini === true};
    } catch (error) {
      return empty;
    }
  }
  function writeStore() {
    const store = storage();
    if (!store) return;
    const turns = state.turns.map((turn) => {
      const copy = Object.assign({}, turn);
      delete copy.fresh;
      if (typeof copy.html === 'string' && copy.html.length > 60000) {
        copy.html = '';
        copy.kind = 'lost';
      }
      return copy;
    });
    try {
      store.setItem(STORE_KEY, JSON.stringify({open: state.open, turns: turns, gemini: state.gemini === true}));
    } catch (error) { /* full */ }
  }

  const state = readStore();
  state.focus = false;
  state.panel = 'thread';
  const ui = {listKind: null, options: [], active: -1, q: '', searchSeq: 0, searchTimer: 0,
              searchCtl: null, results: null, searchFailed: false};
  const prompts = {key: '', items: null, failed: false, pending: null, model: null};

  /* ---------- the model behind an answer ---------- */
  const GEMINI_MODES = ['live', 'recorded'];
  const isGemini = (model) => Boolean(model && typeof model === 'object'
    && GEMINI_MODES.indexOf(model.mode) >= 0 && /gemini/i.test(String(model.name || '')));
  const signedIn = () => {
    try { return Boolean(window.GNShell && typeof window.GNShell.user === 'function' && window.GNShell.user()); } catch (error) { return false; }
  };
  /* "gemini-3.8-flash" reads "Gemini 3.8 Flash". */
  const modelName = (name) => String(name || 'Gemini').split(/[-_\s]+/).filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const dayWords = (t) => {
    const found = /^(\d{4})-(\d\d)-(\d\d)/.exec(String(t || ''));
    return found ? Number(found[3]) + ' ' + MONTHS[Number(found[2]) - 1] : '';
  };

  /* Why the server composed an answer instead of a Gemini run (desk-api.md, `model`). */
  const FALLBACK = {
    not_configured: AGENT + ' is not set up on this site.',
    sign_in_required: 'Sign in to ask ' + AGENT + ' live.',
    budget_exhausted: 'The day\'s budget for ' + AGENT + ' is spent.',
    budget_unavailable: 'The budget meter did not answer, so ' + AGENT + ' did not run.',
    model_timeout: AGENT + ' ran out of time.',
    model_unavailable: AGENT + ' did not answer.',
    model_quota: AGENT + ' is over her quota.',
    model_auth_failed: 'The model refused the site\'s credentials, so ' + AGENT + ' did not run.',
    model_credential_missing: 'The site holds no model credentials, so ' + AGENT + ' did not run.',
    invalid_json: AGENT + ' returned an answer the desk could not read.',
    no_tool_call: AGENT + ' read no record, so the desk set her answer aside.',
    figure_not_in_citation: AGENT + ' cited a figure its source does not show, so the desk set it aside.',
    figure_in_text: AGENT + ' wrote a figure without a source, so the desk set it aside.',
    entity_unknown: AGENT + ' named a record the tools never returned, so the desk set it aside.',
    cite_unresolved: AGENT + ' cited a source that does not exist, so the desk set it aside.',
  };

  /* The badge: which model wrote this answer, how, and how long it took. */
  function modelBadge(model) {
    if (isGemini(model)) {
      const name = modelName(model.name);
      const tokens = model.tokens && typeof model.tokens === 'object'
        && typeof model.tokens.in === 'number' && typeof model.tokens.out === 'number'
        ? model.tokens.in.toLocaleString('en-US') + ' tokens in, ' + model.tokens.out.toLocaleString('en-US') + ' out' : '';
      if (model.mode === 'live') {
        const secs = typeof model.latency_ms === 'number' ? (model.latency_ms / 1000).toFixed(1) + ' s' : '';
        const words = [AGENT, secs, 'live'].filter(Boolean).join(' · ');
        const tip = [AGENT + ' ran live: ' + name + ' on ' + (model.provider || 'Vertex AI') + '.', tokens ? tokens + '.' : '',
          'The server checked every figure against its source.'].filter(Boolean).join(' ');
        return badgeHtml('gemini', words, tip, 'live');
      }
      const when = dayWords(model.recorded_at);
      const tip = ['Replays a run of ' + AGENT + ' (' + name + ')' + (when ? ' recorded on ' + when : '') + '.',
        tokens ? tokens + '.' : '', signedIn() ? '' : 'Sign in to ask ' + AGENT + ' live.'].filter(Boolean).join(' ');
      return badgeHtml('gemini', AGENT + ' · recorded run' + (when ? ' ' + when : ''), tip, 'recorded');
    }
    const key = model && typeof model === 'object' ? String(model.fallback_reason || '') : '';
    const why = FALLBACK[key] || (key ? AGENT + ' did not answer (' + key.replace(/_/g, ' ') + ').' : '');
    const reason = [why, 'No model call ran for this answer.'].filter(Boolean).join(' ');
    return badgeHtml('composed', 'Composed from records', reason, 'composed');
  }

  function badgeHtml(kind, words, tip, mode) {
    return '<p class="gc-model" data-model="' + esc(kind) + '" data-mode="' + esc(mode) + '">'
      + '<span class="gc-model-b" tabindex="0" data-tip="' + esc(tip) + '" aria-label="' + esc(words + '. ' + tip) + '">'
      + (kind === 'gemini' ? '<span class="gc-model-w">' + esc(AGENT) + '</span>' + esc(words.slice(AGENT.length))
        : icon('dataset') + esc(words))
      + '</span></p>';
  }

  async function authHeaders(base) {
    const headers = Object.assign({'Accept': 'application/json'}, base || {});
    try {
      const token = window.GNShell && typeof window.GNShell.idToken === 'function' && signedIn()
        ? await window.GNShell.idToken() : null;
      if (token) headers.Authorization = 'Bearer ' + token;
    } catch (error) { /* anonymous */ }
    return headers;
  }

  /* ---------- the network: public reads of the desk API, the one place this file fetches ---------- */
  const send = (url, init) => fetch(url, Object.assign({credentials: 'same-origin',
    headers: {'Accept': 'application/json'}}, init || {}));
  async function getJson(url, init) {
    try {
      const response = await send(url, init);
      let data = null;
      try { data = await response.json(); } catch (error) { data = null; }
      return {ok: Boolean(response && response.ok), status: response ? response.status : 0, data: data};
    } catch (error) {
      return {ok: false, status: error && error.name === 'AbortError' ? -1 : 0, data: null};
    }
  }
  const query = (params) => Object.keys(params).filter((k) => params[k] !== '' && params[k] != null)
    .map((k) => encodeURIComponent(k) + '=' + encodeURIComponent(params[k])).join('&');

  /* ---------- the frame: bar, results list, sheet and the floating card ---------- */
  const root = document.createElement('div');
  root.id = 'gn-cmd';
  root.className = 'gc';
  root.setAttribute('data-open', 'false');
  root.innerHTML = ''
    + '<section class="gc-sheet" id="gc-sheet" aria-label="' + esc('Answers from ' + AGENT) + '" hidden>'
    + '<header class="gc-head">'
    + '<p class="gc-title"><span class="gc-title-k">' + (WORKSPACE ? 'Conversation' : esc(AGENT_SHORT)) + '</span><span class="gc-title-dot" aria-hidden="true">·</span>'
    + '<span class="gc-title-page">' + esc(PAGE_NAME) + '</span></p>'
    + '<div class="gc-tools">'
    + '<button type="button" class="gc-tool" data-act="panel" aria-pressed="false" aria-label="Cases, queue and threads" data-tip="Cases, queue and threads">' + icon('history') + '</button>'
    + '<button type="button" class="gc-tool" data-act="new" aria-label="New thread" data-tip="New thread">' + icon('plus') + '</button>'
    + '<a class="gc-tool" href="/ask" aria-label="Open the conversation as a full page" data-tip="Full page">' + icon('expand') + '</a>'
    + '<button type="button" class="gc-tool" data-act="min" aria-label="Minimise the answers" data-tip="Minimise · Esc">' + icon('chev') + '</button>'
    + '</div></header>'
    + '<div class="gc-body" id="gc-body">'
    + '<div class="gc-thread" id="gc-thread" aria-live="polite" aria-relevant="additions text"></div>'
    + '<div class="gc-desk" id="gc-desk" hidden></div>'
    + '</div></section>'
    + '<div class="gc-list" id="gc-list" role="listbox" aria-label="Suggestions and search results" hidden></div>'
    + '<form class="gc-bar" role="search" aria-label="' + esc('Search or ask ' + AGENT) + '" autocomplete="off">'
    + '<span class="gc-glyph" aria-hidden="true">' + icon('search') + '</span>'
    + '<input id="gc-input" class="gc-input" type="text" role="combobox" aria-label="' + esc('Search or ask ' + AGENT) + '"'
    + ' aria-expanded="false" aria-controls="gc-list" aria-autocomplete="list" aria-haspopup="listbox"'
    + ' maxlength="500" enterkeyhint="send" spellcheck="false" autocomplete="off"'
    + ' placeholder="' + esc('Search plants, events, data, or ask ' + AGENT) + '">'
    + '<button type="button" class="gc-resume" data-act="resume" hidden></button>'
    + '<kbd class="gc-kbd" aria-hidden="true">/</kbd>'
    + '<button type="button" class="gc-mic" aria-disabled="true" aria-label="Voice input, coming soon"'
    + ' data-tip="Voice input, coming soon">' + icon('mic') + '</button>'
    + '<button type="submit" class="gc-send" aria-label="' + esc('Ask ' + AGENT) + '" data-tip="Ask · Enter">' + icon('send') + '</button>'
    + '</form>'
    + '<button type="button" class="gc-pill" data-act="expand" aria-label="' + esc('Search or ask ' + AGENT) + '">' + icon('search')
    + '<span>Ask</span><kbd class="gc-pill-k" aria-hidden="true">/</kbd></button>';

  const $ = (sel) => root.querySelector(sel);
  const sheet = $('#gc-sheet');
  const body = $('#gc-body');
  const thread = $('#gc-thread');
  const deskPanel = $('#gc-desk');
  const listBox = $('#gc-list');
  const form = $('.gc-bar');
  const input = $('#gc-input');
  const resume = $('.gc-resume');
  const panelBtn = root.querySelector('[data-act="panel"]');

  function attach() {
    if (WORKSPACE) {
      const host = document.getElementById('ask-main') || document.querySelector('main') || document.body;
      root.classList.add('gc-ws');
      host.appendChild(root);
      const frame = document.querySelector('.ask-ws');
      if (frame) frame.classList.add('is-live');
      /* The page's heading names the assistant from the shell (the static one is the fallback). */
      const heading = document.querySelector('.ask-rail h1');
      if (heading) heading.textContent = 'Ask ' + AGENT;
      document.documentElement.classList.add('gc-on');
      applyVoice();
      return;
    }
    document.body.appendChild(root);
    /* Room at the end of a scrolling page, so its last lines can scroll clear of the bar. The map
       desk on / keeps its own layout and leaves the bottom centre clear. */
    if (PARTS.length && !document.querySelector('.gn-page')) {
      const room = document.createElement('div');
      room.className = 'gc-room';
      room.setAttribute('aria-hidden', 'true');
      document.body.appendChild(room);
    }
    /* ask.js's mount: the cases, queue, threads and sign-in live in the sheet's panel. */
    adoptMount();
    document.documentElement.classList.add('gc-on');
    applyVoice();
  }

  /* The bar's own words: Ingrid is named as the one who answers only when the server reported a
     Gemini run for prompts (the model behind her is not displayed in the bar; owner, 19 October). */
  function applyVoice() {
    const narrow = Boolean(window.matchMedia && window.matchMedia('(max-width: 520px)').matches);
    let words = narrow ? 'Search or ask ' + AGENT : 'Search plants, events, data, or ask ' + AGENT;
    if (state.gemini) words = narrow ? 'Search or ask ' + AGENT : 'Search, or ask ' + AGENT + ' about the grid';
    input.setAttribute('placeholder', words);
    root.classList.toggle('gc-gemini', state.gemini === true);
  }

  function adoptMount() {
    if (WORKSPACE) return;
    const found = findMount();
    if (!found || deskPanel.contains(found)) return;
    found.classList.add('gc-held');
    deskPanel.appendChild(found);
  }

  /* ---------- states: idle, focused, open ---------- */
  /* Past the first screen of a scrolling page the bar rests as a small "Ask" pill at the lower
     right, out of the reading column. The full bar shows at the top of the page, or when called:
     "/", Ctrl or Cmd with K, or a click on the pill. The map desk on / keeps the full bar. */
  const COMPACT_AT = 160;
  /* A reading page (the paper, the explainer, the case: `.gn-page--read`) starts with the pill,
     so the bar never sits over its prose. */
  const reading = () => Boolean(document.querySelector('.gn-page--read'));
  const restsCompact = () => PARTS.length > 0 && !WORKSPACE && (reading() || window.scrollY > COMPACT_AT);
  const compact = {wanted: false};
  function sync() {
    root.classList.toggle('gc-compact', compact.wanted && !state.open && !state.focus && !ui.listKind);
    root.setAttribute('data-open', isOpen() ? 'true' : 'false');
    root.classList.toggle('gc-focus', state.focus || Boolean(ui.listKind));
    root.classList.toggle('gc-listing', Boolean(ui.listKind));
    sheet.hidden = !isOpen();
    const count = state.turns.length;
    resume.hidden = isOpen() || !count;
    if (count) {
      resume.innerHTML = icon('up') + '<span>' + count + (count === 1 ? ' answer' : ' answers') + '</span>';
      resume.setAttribute('aria-label', 'Open the thread, ' + count
        + (count === 1 ? ' answer' : ' answers'));
    }
    thread.hidden = state.panel !== 'thread';
    deskPanel.hidden = state.panel !== 'desk';
    panelBtn.setAttribute('aria-pressed', state.panel === 'desk' ? 'true' : 'false');
  }

  function openSheet(panel) {
    if (!WORKSPACE) state.open = true;
    if (panel) state.panel = panel;
    sync();
    writeStore();
    if (state.panel === 'thread' && !state.turns.length) renderEmpty();
  }
  function closeSheet() {
    if (WORKSPACE) { hideCard(true); return; }
    state.open = false;
    hideCard(true);
    sync();
    writeStore();
  }
  function scrollToEnd() {
    body.scrollTop = body.scrollHeight;
  }

  /* ---------- the list: suggestions on focus, results while typing ---------- */
  function optionHtml(option, index) {
    const id = 'gc-opt-' + index;
    const meta = option.meta ? '<span class="gc-opt-meta">' + esc(option.meta) + '</span>' : '';
    return '<div class="gc-opt" role="option" id="' + id + '" data-i="' + index + '"'
      + (option.kind ? ' data-kind="' + esc(option.kind) + '"' : '') + ' data-type="' + esc(option.type) + '"'
      + ' aria-selected="' + (index === ui.active ? 'true' : 'false') + '">'
      + '<span class="gc-opt-ico">' + icon(option.glyph || option.kind || 'dot') + '</span>'
      + '<span class="gc-opt-main"><span class="gc-opt-title">' + option.titleHtml + '</span>'
      + (option.sub ? '<span class="gc-opt-sub">' + esc(option.sub) + '</span>' : '') + '</span>'
      + meta + '<span class="gc-opt-enter" aria-hidden="true">' + icon('arrow') + '</span></div>';
  }

  function groupHtml(label, gid, items) {
    return '<div role="group" class="gc-grp" aria-labelledby="' + gid + '">'
      + '<div class="gc-grp-h" id="' + gid + '" role="presentation">' + esc(label) + '</div>'
      + items.join('') + '</div>';
  }

  const FOOT = '<div class="gc-foot" aria-hidden="true">'
    + '<span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open or ask</span>'
    + '<span><kbd>⇧</kbd><kbd>↵</kbd> preview</span><span><kbd>esc</kbd> close</span></div>';

  function recordedViews() {
    const d = desk();
    if (!d || !d.state || !d.state.present) return [];
    return list(d.state.views).map((view, index) => ({view: view, index: index}))
      .filter((row) => row.view && typeof row.view.question === 'string');
  }

  function renderList() {
    if (!ui.listKind) {
      listBox.hidden = true;
      listBox.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      sync();
      return;
    }
    const options = [];
    const groups = [];
    let note = '';
    if (ui.listKind === 'prompts') {
      const items = prompts.items || [];
      if (items.length) {
        groups.push(groupHtml((state.gemini ? 'Ask ' + AGENT + ' about the grid · ' : 'Suggested at ')
          + (asOf().slice(11, 16) || 'the replay clock'),
          'gc-g-prompts', items.map((item) => {
            options.push({type: 'prompt', glyph: 'ask', id: item.id, text: item.text,
                          titleHtml: esc(item.text), sub: item.hint || ''});
            return optionHtml(options[options.length - 1], options.length - 1);
          })));
      }
      const recorded = recordedViews();
      if (recorded.length) {
        groups.push(groupHtml('Recorded for this page', 'gc-g-recorded', recorded.map((row) => {
          options.push({type: 'recorded', glyph: 'recorded', index: row.index, text: row.view.question,
                        titleHtml: esc(row.view.question), sub: 'Recorded plan'});
          return optionHtml(options[options.length - 1], options.length - 1);
        })));
      }
      /* ask.js's panel: sign-in, cases, the queue of confirmations, and the threads. */
      if (findMount() && !WORKSPACE) {
        options.push({type: 'panel', glyph: 'history', titleHtml: 'Cases, queue and threads',
                      sub: signedIn() ? 'Your cases and what waits for your decision' : 'Sign in to ask live and keep cases'});
        groups.push(groupHtml(AGENT_SHORT, 'gc-g-desk', [optionHtml(options[options.length - 1], options.length - 1)]));
      }
      if (prompts.pending && !items.length) note = 'Reading the suggestions for this page.';
      else if (prompts.failed && !items.length) {
        note = 'Suggestions did not load. Type a name or a question.';
      } else if (!items.length && !recorded.length) note = 'Type a name or a question.';
    } else {
      const q = ui.q;
      options.push({type: 'ask', glyph: 'ask', text: q,
                    titleHtml: esc('Ask ' + AGENT + ': ')
                      + '<span class="gc-quote">“' + esc(q) + '”</span>',
                    sub: 'Composed from the records at ' + (asOf().slice(11, 16) || 'the replay clock')});
      groups.push('<div role="group" class="gc-grp gc-grp-ask" aria-label="Ask">'
        + optionHtml(options[0], 0) + '</div>');
      const result = ui.results;
      list(result && result.groups).forEach((group) => {
        const items = list(group.items);
        if (!items.length) return;
        const kind = String(group.kind || (items[0] && items[0].kind) || 'page');
        groups.push(groupHtml(group.label || GROUP_WORD[kind] || kind, 'gc-g-' + esc(kind),
          items.map((item) => {
            options.push({type: 'entity', kind: String(item.kind || kind), id: item.id,
                          href: safeHref(item.href) || defaultHref(item.kind || kind, item.id),
                          titleHtml: mark(item.title || item.id, q), sub: item.subtitle || '',
                          meta: typeof item.badge === 'string' ? item.badge : '',
                          text: item.title || item.id});
            return optionHtml(options[options.length - 1], options.length - 1);
          })));
      });
      if (ui.searchFailed) note = 'Search did not answer. Ask still works.';
      else if (result && result.q === q && options.length === 1) {
        note = 'No plant, event or dataset matches this. Ask it as a question.';
      }
    }
    ui.options = options;
    if (ui.active >= options.length) ui.active = options.length - 1;
    listBox.innerHTML = groups.join('')
      + (note ? '<p class="gc-note" role="presentation">' + esc(note) + '</p>' : '') + FOOT;
    listBox.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    setActive(ui.active, false);
    sync();
  }

  /* The matched part of a title, marked; the rest escaped. Accent- and case-insensitive. */
  function mark(title, q) {
    const text = String(title || '');
    const fold = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const needle = fold(String(q || '').trim());
    if (!needle) return esc(text);
    const at = fold(text).indexOf(needle);
    if (at < 0 || fold(text).length !== text.length) return esc(text);
    return esc(text.slice(0, at)) + '<mark>' + esc(text.slice(at, at + needle.length)) + '</mark>'
      + esc(text.slice(at + needle.length));
  }

  function setActive(index, scroll) {
    ui.active = index;
    listBox.querySelectorAll('.gc-opt').forEach((node) => {
      node.setAttribute('aria-selected', node.getAttribute('data-i') === String(index) ? 'true' : 'false');
    });
    const node = index >= 0 ? listBox.querySelector('#gc-opt-' + index) : null;
    if (node) {
      input.setAttribute('aria-activedescendant', node.id);
      if (scroll && typeof node.scrollIntoView === 'function') node.scrollIntoView({block: 'nearest'});
    } else {
      input.removeAttribute('aria-activedescendant');
    }
  }

  function showPrompts() {
    ui.listKind = 'prompts';
    ui.active = -1;
    renderList();
    loadPrompts().then(() => { if (ui.listKind === 'prompts') renderList(); });
    const d = desk();
    if (d && d.ready && typeof d.ready.then === 'function') {
      d.ready.then(() => { if (ui.listKind === 'prompts') renderList(); }, () => {});
    }
  }

  function closeList() {
    ui.listKind = null;
    ui.active = -1;
    renderList();
  }

  function loadPrompts() {
    const key = asOf() + '|' + PAGE_KEY;
    if (prompts.key === key && (prompts.items || prompts.pending)) {
      return prompts.pending || Promise.resolve();
    }
    prompts.key = key;
    prompts.items = null;
    prompts.failed = false;
    prompts.pending = authHeaders().then((headers) => getJson(API + 'prompts?'
      + query({at: asOf(), page: PAGE_KEY}), {headers: headers})).then((answer) => {
      if (prompts.key !== key) return;
      prompts.pending = null;
      const items = answer.ok && answer.data ? list(answer.data.prompts) : [];
      prompts.items = items.filter((item) => item && typeof item.text === 'string').slice(0, 5);
      prompts.failed = !answer.ok;
      prompts.model = answer.ok && answer.data && answer.data.model ? answer.data.model : null;
      const gemini = isGemini(prompts.model);
      if (answer.ok && gemini !== state.gemini) {
        state.gemini = gemini;
        writeStore();
      }
      applyVoice();
    });
    return prompts.pending;
  }

  function search(q) {
    ui.q = q;
    ui.listKind = 'search';
    ui.active = 0;
    ui.searchFailed = false;
    renderList();
    clearTimeout(ui.searchTimer);
    ui.searchTimer = setTimeout(async () => {
      const seq = ++ui.searchSeq;
      if (ui.searchCtl && typeof ui.searchCtl.abort === 'function') ui.searchCtl.abort();
      ui.searchCtl = typeof AbortController === 'function' ? new AbortController() : null;
      const answer = await getJson(API + 'search?' + query({q: q, at: asOf(), limit: 8}),
        ui.searchCtl ? {signal: ui.searchCtl.signal} : undefined);
      if (seq !== ui.searchSeq || answer.status === -1 || ui.listKind !== 'search') return;
      ui.searchFailed = !answer.ok;
      ui.results = answer.ok && answer.data ? Object.assign({}, answer.data, {q: q}) : null;
      renderList();
    }, 140);
  }

  function activate(option, preview) {
    if (!option) return;
    if (option.type === 'ask') { ask(option.text); return; }
    if (option.type === 'prompt') { ask(option.text, option.id); return; }
    if (option.type === 'recorded') { askRecorded(option.index); return; }
    if (option.type === 'panel') { closeList(); openSheet('desk'); return; }
    if (option.type === 'entity') {
      const node = listBox.querySelector('#gc-opt-' + ui.options.indexOf(option));
      if ((preview || !option.href) && PREVIEWABLE.indexOf(option.kind) >= 0 && node) {
        showPreview(node, option.kind, option.id, true, 'side');
        return;
      }
      if (option.href) go(option.href);
    }
  }

  /* Leaving for a page: the bar comes back collapsed there, the thread one click away. */
  function go(href) {
    state.open = false;
    writeStore();
    window.location.assign(href);
  }

  /* ---------- asking ---------- */
  const newId = () => 't' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

  function startTurn(question) {
    const turn = {id: newId(), q: question, at: asOf(), page: PAGE_NAME, kind: 'pending', since: Date.now(),
                  live: Boolean(prompts.model && prompts.model.mode === 'live' && isGemini(prompts.model))};
    state.turns.push(turn);
    setBusy();
    while (state.turns.length > MAX_TURNS) {
      const old = state.turns.shift();
      const node = thread.querySelector('[data-turn="' + old.id + '"]');
      if (node) node.remove();
    }
    closeList();
    input.value = '';
    ui.q = '';
    state.panel = 'thread';
    openSheet();
    const empty = thread.querySelector('.gc-empty');
    if (empty) empty.remove();
    thread.insertAdjacentHTML('beforeend', turnHtml(turn));
    scrollToEnd();
    writeStore();
    return turn;
  }

  async function ask(text, promptId) {
    const question = String(text || '').trim().slice(0, 500);
    if (!question) return;
    const turn = startTurn(question);
    const asked = JSON.stringify({question: question, prompt_id: promptId || null, at: turn.at,
                                  page: PAGE_KEY});
    /* A live run streams its steps. Without a stream, or when it fails, the plain route answers. */
    let answer = turn.live ? await askStream(turn, asked) : null;
    if (!answer) {
      /* The plain route runs again from the start, so the stream's steps give way to its answer. */
      if (list(turn.steps).length) { turn.steps = []; updateTurn(turn); }
      answer = await getJson(API + 'answer', {method: 'POST',
        headers: await authHeaders({'Content-Type': 'application/json'}), body: asked});
    }
    delete turn.steps;
    const data = answer.ok && answer.data && typeof answer.data === 'object' ? answer.data : null;
    if (data && data.status === 'answered') {
      turn.kind = 'desk';
      turn.answer = data;
      turn.fresh = true;
    } else {
      /* No composed answer: a recorded plan or the agent service may still answer it. */
      const other = await fromDeskAsk(question);
      if (other && other.html) {
        turn.kind = other.kind;
        turn.html = other.html;
        turn.basis = other.basis || '';
      } else if (data && data.status === 'no_match') {
        turn.kind = 'desk';
        turn.answer = data;
        turn.near = other && other.nearest ? other.nearest : '';
      } else {
        turn.kind = 'error';
        turn.status = answer.status;
        turn.near = other && other.nearest ? other.nearest : '';
      }
    }
    updateTurn(turn);
    writeStore();
  }

  /* The answer stream: server-sent events read with fetch and a reader. Each `step` event is a
     tool call the live loop has run, drawn with the final trace's own markup. The `answer` event
     is the body the plain route returns. Null on any failure, so the caller asks the plain route. */
  async function askStream(turn, asked) {
    if (typeof ReadableStream !== 'function' || typeof TextDecoder !== 'function') return null;
    let reader = null;
    try {
      const response = await send(API + 'answer/stream', {method: 'POST',
        headers: await authHeaders({'Content-Type': 'application/json', 'Accept': 'text/event-stream'}),
        body: asked});
      const type = response && response.headers ? String(response.headers.get('Content-Type') || '') : '';
      if (!response || !response.ok || !response.body || typeof response.body.getReader !== 'function'
        || type.indexOf('text/event-stream') !== 0) return null;
      reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const chunk = await reader.read();
        buffer += decoder.decode(chunk.value || new Uint8Array(0), {stream: !chunk.done});
        let cut = buffer.indexOf('\n\n');
        while (cut >= 0) {
          const event = streamEvent(buffer.slice(0, cut));
          buffer = buffer.slice(cut + 2);
          if (!event || event.event === 'error') throw new Error('stream');
          if (event.event === 'answer') {
            reader.cancel().catch(() => {});
            return {ok: true, status: 200, data: event.answer};
          }
          if (event.event === 'step') liveStep(turn, event.step);
          cut = buffer.indexOf('\n\n');
        }
        if (chunk.done) return null;
      }
    } catch (error) {
      if (reader) reader.cancel().catch(() => {});
      return null;
    }
  }

  /* One event's `data:` lines as JSON, or null when it does not parse. */
  function streamEvent(text) {
    const data = String(text).split('\n').filter((line) => line.indexOf('data:') === 0)
      .map((line) => line.slice(5).replace(/^ /, '')).join('\n');
    try {
      const event = JSON.parse(data);
      return event && typeof event === 'object' ? event : null;
    } catch (error) {
      return null;
    }
  }

  /* One step the server reported: kept on the turn, and added under the pending line. */
  function liveStep(turn, step) {
    if (!step || typeof step !== 'object' || turn.kind !== 'pending') return;
    turn.steps = list(turn.steps).concat([step]);
    const box = thread.querySelector('[data-turn="' + turn.id + '"] .gc-trace-live');
    if (!box) return;
    box.hidden = false;
    box.insertAdjacentHTML('beforeend', stepHtml(step));
    scrollToEnd();
  }

  async function fromDeskAsk(question) {
    const d = desk();
    if (!d || typeof d.answer !== 'function') return null;
    try {
      if (d.ready && typeof d.ready.then === 'function') await d.ready;
      return await d.answer(question);
    } catch (error) {
      return null;
    }
  }

  function askRecorded(index) {
    const d = desk();
    if (!d || typeof d.pick !== 'function') return;
    const view = d.state && d.state.views && d.state.views[index];
    if (!view) return;
    const turn = startTurn(String(view.question || ''));
    const found = d.pick(index);
    if (found && found.html) {
      turn.kind = found.kind || 'recorded';
      turn.html = found.html;
      turn.basis = found.basis || '';
    } else {
      turn.kind = 'error';
    }
    updateTurn(turn);
    writeStore();
  }

  /* The bar is busy while any turn is pending: the send button shows the ring, and one ticker
     writes the seconds elapsed into each pending line. The ticker stops with the last answer. */
  let ticker = null;
  function setBusy() {
    const busy = state.turns.some((t) => t.kind === 'pending');
    root.classList.toggle('gc-busy', busy);
    root.querySelector('.gc-send').setAttribute('aria-busy', busy ? 'true' : 'false');
    if (busy && !ticker) ticker = setInterval(tick, 1000);
    if (!busy && ticker) { clearInterval(ticker); ticker = null; }
    tick();
  }
  function tick() {
    root.querySelectorAll('.gc-elapsed').forEach((el) => {
      const since = Number(el.getAttribute('data-since')) || 0;
      const s = since ? Math.max(0, Math.round((Date.now() - since) / 1000)) : 0;
      el.textContent = s >= 2 ? s + ' s' : '';
    });
  }
  function updateTurn(turn) {
    setBusy();
    const node = thread.querySelector('[data-turn="' + turn.id + '"]');
    if (!node) return;
    node.outerHTML = turnHtml(turn);
    const fresh = thread.querySelector('[data-turn="' + turn.id + '"]');
    if (turn.fresh && fresh) reveal(fresh, turn);
    delete turn.fresh;
    scrollToEnd();
  }

  /* ---------- one turn ---------- */
  function turnHtml(turn) {
    let inner = '<div class="gc-q"><p>' + esc(turn.q) + '</p></div>';
    if (turn.kind === 'pending') {
      /* While the answer is on its way the line moves (one slow ring, stilled under reduced
         motion) and counts the seconds, so a 10 to 20 second live call never looks frozen. The
         thread is already a live region, so the line is announced once when it is added; the
         counter is visual only. No step is invented: a live step appears only when the server
         reports a tool call that has run, and the answer's trace comes from the server. */
      inner += '<p class="gc-wait">'
        + '<span class="gc-spin" aria-hidden="true"></span><span>' + (turn.live
        ? esc(AGENT) + ' is reading the records at ' + esc(hhmm(turn.at) || 'the replay clock') + '…'
        : 'Reading the records at ' + esc(hhmm(turn.at) || 'the replay clock') + '.') + '</span>'
        + '<span class="gc-elapsed" aria-hidden="true" data-since="' + esc(String(Number(turn.since) || Date.now())) + '"></span>'
        + (turn.live ? '<span class="gc-wait-note">A live answer takes about 10 to 20 seconds.</span>' : '')
        + '</p>'
        + '<ol class="gc-steps gc-trace-live" aria-label="Steps ' + esc(AGENT) + ' has run so far"'
        + (list(turn.steps).length ? '' : ' hidden') + '>' + list(turn.steps).map(stepHtml).join('') + '</ol>';
    } else if (turn.kind === 'desk' && turn.answer) {
      inner += answerHtml(turn.answer, turn);
    } else if ((turn.kind === 'recorded' || turn.kind === 'live') && turn.html) {
      inner += '<div class="gc-a gc-plan" data-kind="' + esc(turn.kind) + '">'
        + '<p class="gc-plan-k">' + icon(turn.kind === 'live' ? 'ask' : 'recorded')
        + '<span>' + (turn.kind === 'live' ? 'Agent answer' : 'Recorded plan') + '</span></p>'
        + turn.html + (turn.basis ? '<p class="gc-basis">' + esc(turn.basis) + '</p>' : '') + '</div>';
    } else if (turn.kind === 'lost') {
      inner += '<p class="gc-quiet">This answer did not survive the page change. Ask again.</p>'
        + followHtml([{text: turn.q}]);
    } else {
      inner += '<p class="gc-quiet">' + esc(AGENT_CAP) + ' did not answer'
        + (turn.status > 0 ? ' (status ' + esc(turn.status) + ')' : '') + '. '
        + 'The suggested and recorded questions still work.</p>'
        + followHtml(turn.near ? [{text: turn.near, recorded: true}] : [])
        + '<p class="gc-basis">No model call ran for this question.</p>';
    }
    return '<article class="gc-turn" data-turn="' + esc(turn.id) + '" aria-label="'
      + esc('Answer to: ' + turn.q.slice(0, 80)) + '">' + inner + '</article>';
  }

  function answerHtml(answer, turn) {
    const ctx = {id: turn.id, cites: {}, entities: list(answer.entities)};
    list(answer.citations).forEach((c) => { if (c && c.n != null) ctx.cites[c.n] = c; });
    const blocks = list(answer.blocks).map((block) => blockHtml(block, ctx)).join('');
    const follow = list(answer.followups).slice(0, 4);
    if (turn.near) follow.push({text: turn.near, recorded: true});
    const at = hhmm(answer.at || turn.at);
    return '<div class="gc-a" data-status="' + esc(answer.status) + '">'
      + (answer.status === 'answered' ? modelBadge(answer.model) : '')
      + traceHtml(answer, turn)
      + '<div class="gc-blocks">' + blocks + '</div>'
      + (answer.basis || at ? '<p class="gc-basis">' + esc(answer.basis || '')
        + (at ? ' <span class="gc-at">Replay clock <span class="mono">' + esc(at) + '</span></span>' : '')
        + '</p>' : '')
      + followHtml(follow) + '</div>';
  }

  function followHtml(items) {
    const buttons = list(items).filter((item) => item && typeof item.text === 'string').map((item) =>
      '<button type="button" class="gc-follow-b" data-text="' + esc(item.text) + '"'
      + (item.prompt_id ? ' data-prompt="' + esc(item.prompt_id) + '"' : '')
      + (item.recorded ? ' data-recorded="1"' : '') + '>'
      + icon(item.recorded ? 'recorded' : 'arrow') + '<span>' + esc(item.text) + '</span></button>');
    return buttons.length ? '<div class="gc-follow" role="group" aria-label="Follow-up questions">'
      + buttons.join('') + '</div>' : '';
  }

  /* The trace: what the desk resolved, followed and read, as ontology steps. */
  function traceSummary(answer) {
    const steps = list(answer.trace);
    const path = [];
    steps.forEach((step) => {
      let word = '';
      if (step.op === 'resolve') word = step.type || KIND_WORD[step.entity && step.entity.kind] || '';
      else if (step.op === 'relate') word = String(step.label || '').split(/\s+/)[0] || '';
      if (word && path[path.length - 1] !== word) path.push(word);
    });
    const datasets = new Set();
    steps.forEach((step) => { if (step.dataset_id) datasets.add(step.dataset_id); });
    list(answer.citations).forEach((c) => { if (c && c.dataset_id) datasets.add(c.dataset_id); });
    const count = steps.length + (steps.length === 1 ? ' step' : ' steps');
    const parts = [isGemini(answer.model) ? AGENT + ' traced ' + count : 'Traced ' + count];
    if (path.length) parts.push(path.slice(0, 4).join(' → '));
    if (datasets.size) parts.push(datasets.size + (datasets.size === 1 ? ' dataset' : ' datasets'));
    return parts.join(' · ');
  }

  function stepHtml(step) {
    const op = String(step.op || 'step');
    let label = esc(step.label || '');
    if (step.op === 'resolve' && step.entity && PREVIEWABLE.indexOf(step.entity.kind) >= 0) {
      label = entityHtml({kind: step.entity.kind, id: step.entity.id, label: step.label}, null);
    } else if (step.op === 'read' && step.dataset_id) {
      label = entityHtml({kind: 'dataset', id: step.dataset_id, label: step.label}, null);
    }
    const chip = step.type || step.relation;
    const rows = typeof step.rows === 'number'
      ? '<span class="gc-step-rows mono">' + esc(step.rows.toLocaleString('en-US'))
        + (step.rows === 1 ? ' row' : ' rows') + '</span>' : '';
    return '<li class="gc-step" data-op="' + esc(op) + '">'
      + '<span class="gc-step-ico">' + icon(PATHS[op] ? op : 'dot') + '</span>'
      + '<span class="gc-step-op">' + esc(OP_WORD[op] || op) + '</span>'
      + '<span class="gc-step-label">' + label
      + (chip ? ' <span class="gc-chip' + (step.relation ? ' mono' : '') + '">' + esc(chip) + '</span>' : '')
      + '</span>' + rows + '</li>';
  }

  function traceHtml(answer, turn) {
    const steps = list(answer.trace);
    if (!steps.length) return '';
    const id = 'gc-tr-' + turn.id;
    return '<div class="gc-trace">'
      + '<button type="button" class="gc-trace-sum" aria-expanded="false" aria-controls="' + id + '">'
      + icon('trace', 'gc-trace-ico') + '<span class="gc-trace-text">' + esc(traceSummary(answer)) + '</span>'
      + icon('chev', 'gc-chev') + '</button>'
      + '<ol class="gc-steps" id="' + id + '" hidden>' + steps.map(stepHtml).join('') + '</ol></div>';
  }

  /* A fresh answer: the steps fire one after another, then the prose lands. */
  function reveal(node, turn) {
    const steps = list(turn.answer && turn.answer.trace);
    const text = node.querySelector('.gc-trace-text');
    const items = [...node.querySelectorAll('.gc-step')];
    const blocks = node.querySelector('.gc-a');
    if (!steps.length || !text || reduced()) return;
    const final = text.textContent;
    node.classList.add('gc-firing');
    items.forEach((li) => li.classList.add('gc-step-wait'));
    let i = 0;
    const tick = () => {
      if (i < steps.length) {
        const step = steps[i];
        text.textContent = (OP_WORD[step.op] || 'Step') + ' · ' + String(step.label || '')
          + '  ' + (i + 1) + '/' + steps.length;
        if (items[i]) items[i].classList.remove('gc-step-wait');
        i += 1;
        setTimeout(tick, STEP_MS);
        return;
      }
      text.textContent = final;
      node.classList.remove('gc-firing');
      if (blocks) blocks.classList.add('gc-landed');
      scrollToEnd();
    };
    tick();
  }

  function partHtml(part, ctx) {
    if (typeof part === 'string' || typeof part === 'number') return esc(part);
    if (!part || typeof part !== 'object') return '';
    if (part.t === 'num') {
      return '<span class="gc-num">' + esc(part.v) + '</span>' + citesHtml(part.cite, part.v, ctx);
    }
    if (part.t === 'entity') return entityHtml(part, ctx);
    if (part.t === 'strong') return '<strong>' + esc(part.v) + '</strong>';
    return esc(part.v);
  }

  function citesHtml(numbers, value, ctx) {
    return list(numbers).map((n) => {
      const c = ctx && ctx.cites[n];
      return '<button type="button" class="gc-cite" data-cite="' + esc(n) + '" data-turn="'
        + esc(ctx ? ctx.id : '') + '" data-v="' + esc(value == null ? '' : value) + '"'
        + ' aria-haspopup="dialog" aria-label="Source ' + esc(n) + (c ? ', ' + esc(c.title) : '') + '">'
        + esc(n) + '</button>';
    }).join('');
  }

  function entityHtml(part, ctx) {
    const kind = String(part.kind || '');
    const known = ctx ? ctx.entities.find((e) => e && e.kind === kind && String(e.id) === String(part.id)) : null;
    const href = (known && safeHref(known.href)) || defaultHref(kind, part.id);
    const label = esc(part.label || part.id);
    if (PREVIEWABLE.indexOf(kind) < 0) {
      return href ? '<a class="gc-ent gc-ent-plain" href="' + esc(href) + '">' + label + '</a>' : label;
    }
    return '<a class="gc-ent" href="' + esc(href || '#') + '" data-kind="' + esc(kind) + '" data-id="'
      + esc(part.id) + '" data-entity="' + esc(kind + ':' + part.id) + '" aria-haspopup="dialog">' + label + '</a>';
  }

  const NUMERIC = /^[-−+]?[₱$]?\s?[\d,]+(\.\d+)?\s?(%|MW|MWh)?$/;

  function blockHtml(block, ctx) {
    if (!block || typeof block !== 'object') return '';
    if (block.type === 'p') {
      return '<p class="gc-p">' + list(block.parts).map((part) => partHtml(part, ctx)).join('') + '</p>';
    }
    if (block.type === 'table') {
      const columns = list(block.columns);
      const rows = list(block.rows);
      const numeric = columns.map((_, col) => rows.length > 0 && rows.every((row) => {
        const cell = list(row)[col];
        return cell == null || cell === '' || (typeof cell === 'object' ? cell.t === 'num'
          : NUMERIC.test(String(cell).trim()));
      }));
      const cell = (value, col, tag) => '<' + tag + (numeric[col] ? ' class="num"' : '')
        + (tag === 'th' ? ' scope="col"' : '') + '>' + partHtml(value, ctx) + '</' + tag + '>';
      return '<figure class="gc-table">'
        + (block.caption || list(block.cite).length ? '<figcaption>' + esc(block.caption || '')
          + citesHtml(block.cite, '', ctx) + '</figcaption>' : '')
        + '<div class="gc-table-scroll"><table><thead><tr>'
        + columns.map((c, col) => cell(c, col, 'th')).join('') + '</tr></thead><tbody>'
        + rows.map((row) => '<tr>' + list(row).map((c, col) => cell(c, col, 'td')).join('') + '</tr>').join('')
        + '</tbody></table></div></figure>';
    }
    if (block.type === 'list') {
      return '<ul class="gc-ul">' + list(block.items).map((item) => '<li>'
        + list(item && item.parts ? item.parts : [item]).map((part) => partHtml(part, ctx)).join('')
        + '</li>').join('') + '</ul>';
    }
    return '';
  }

  function renderThread() {
    thread.innerHTML = state.turns.map(turnHtml).join('');
    /* The suggestions load when the sheet opens or the bar takes focus, never on the first screen. */
    if (!state.turns.length && isOpen()) renderEmpty();
  }

  function renderEmpty() {
    if (state.turns.length || thread.querySelector('.gc-empty')) return;
    thread.insertAdjacentHTML('beforeend', '<div class="gc-empty"><p class="gc-empty-t">Ask about '
      + esc(WORKSPACE ? 'the grid' : PAGE_NAME) + ' at <span class="mono">' + esc(asOf().slice(11, 16) || 'the replay clock')
      + '</span></p><p class="gc-quiet">Answers come from the baked records, with every step and source shown.</p>'
      + '<div class="gc-empty-list"></div></div>');
    loadPrompts().then(() => {
      const box = thread.querySelector('.gc-empty-list');
      if (!box) return;
      const items = (prompts.items || []).map((item) => ({text: item.text, prompt_id: item.id}));
      recordedViews().slice(0, 3).forEach((row) => items.push({text: row.view.question, recorded: true}));
      box.innerHTML = followHtml(items) || '<p class="gc-quiet">Type a name or a question below.</p>';
    });
  }

  /* ---------- the floating card: a citation's rows, or an entity's preview ----------
     One card and one preview cache for the whole site: ui.js renders and places it (GNUI.card,
     GNUI.preview), so an entity in an answer shows the same card as anywhere else. */
  const UI = () => (window.GNUI && window.GNUI.card ? window.GNUI : null);
  const cardEl = () => (UI() ? UI().card.el : null);
  const cardOpen = () => Boolean(UI() && UI().card.isOpen());
  const cardState = () => (UI() ? UI().card.state : {anchor: null, pinned: false, key: ''});
  const inCard = (node) => Boolean(node && UI() && UI().card.isOpen() && UI().card.el.contains(node));

  function findTurn(id) { return state.turns.find((turn) => turn.id === id) || null; }

  const digits = (value) => String(value == null ? '' : value).replace(/[^\d.\-−]/g, '').replace('−', '-');

  function citeCardHtml(c, value) {
    const table = c.table && typeof c.table === 'object' ? c.table : {columns: [], rows: []};
    const rows = list(table.rows);
    const wanted = digits(value);
    const hit = (cell) => wanted && wanted.length > 0 && digits(cell) === wanted;
    const href = safeHref(c.href) || defaultHref('dataset', c.dataset_id);
    return '<p class="gn-pcard-k">' + icon('dataset') + '<span>Source ' + esc(c.n) + '</span></p>'
      + '<p class="gn-pcard-title" id="gn-pcard-title">' + esc(c.title || c.dataset_id) + '</p>'
      + '<p class="gn-pcard-meta">' + rows.length + (rows.length === 1 ? ' row' : ' rows')
      + (hhmm(c.at) ? ' · at <span class="mono">' + esc(hhmm(c.at)) + '</span>' : '') + '</p>'
      + (c.filter ? '<p class="gn-pcard-filter mono">' + esc(c.filter) + '</p>' : '')
      + (rows.length ? '<div class="gn-pcard-table"><table><thead><tr>'
        + list(table.columns).map((col) => '<th scope="col">' + esc(col) + '</th>').join('')
        + '</tr></thead><tbody>' + rows.slice(0, 12).map((row) => '<tr>' + list(row).map((cell) =>
          '<td' + (hit(cell) ? ' class="gn-hit"' : '') + '>' + esc(cell) + '</td>').join('') + '</tr>').join('')
        + '</tbody></table></div>' : '')
      + '<div class="gn-pcard-acts">'
      + (href ? '<a class="gn-pcard-open" href="' + esc(href) + '">Open dataset ' + icon('out') + '</a>' : '')
      + '<button type="button" class="gn-pcard-btn" data-copy="' + esc(c.n) + '">' + icon('copy')
      + '<span>Copy rows</span></button></div>';
  }

  function hideCard(force) { if (UI()) UI().card.hide(force); }

  function showCite(anchor, pinned) {
    const turn = findTurn(anchor.getAttribute('data-turn'));
    const n = anchor.getAttribute('data-cite');
    const c = turn && turn.answer ? list(turn.answer.citations).find((item) => item && String(item.n) === n) : null;
    if (!c || !UI()) return;
    const el = UI().card.open(anchor, '<div class="gn-pcard-cite">' + citeCardHtml(c, anchor.getAttribute('data-v')) + '</div>',
      {pinned: pinned, label: 'Source ' + n, key: 'cite:' + turn.id + ':' + n});
    el.setAttribute('data-turn', turn.id);
  }

  function showPreview(anchor, kind, id, pinned, prefer) {
    if (!UI()) return;
    UI().preview(anchor, kind, id, {pinned: pinned, prefer: prefer, sideOf: prefer === 'side' ? listBox : null});
  }

  function showFor(anchor, pinned) {
    if (anchor.classList.contains('gc-cite')) showCite(anchor, pinned);
    else if (anchor.classList.contains('gc-ent') && anchor.getAttribute('data-kind')) {
      showPreview(anchor, anchor.getAttribute('data-kind'), anchor.getAttribute('data-id'), pinned, null);
    } else if (anchor.classList.contains('gc-opt')) {
      const option = ui.options[Number(anchor.getAttribute('data-i'))];
      if (option && option.type === 'entity' && PREVIEWABLE.indexOf(option.kind) >= 0) {
        showPreview(anchor, option.kind, option.id, pinned, 'side');
      }
    }
  }

  /* Citations and result rows preview here; an entity link in an answer carries data-entity, so
     ui.js previews it on hover and focus as it does across the site. */
  const ANCHORS = '.gc-cite, .gc-opt[data-kind]';

  function copyRows(n) {
    const el = cardEl();
    const turn = el ? findTurn(el.getAttribute('data-turn')) : null;
    const c = turn && turn.answer ? list(turn.answer.citations).find((item) => item && String(item.n) === String(n)) : null;
    const btn = el ? el.querySelector('[data-copy]') : null;
    if (!c || !btn) return;
    const quote = (v) => {
      const s = String(v == null ? '' : v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const table = c.table || {};
    const csv = [list(table.columns)].concat(list(table.rows)).map((row) => list(row).map(quote).join(',')).join('\n');
    const done = (word) => {
      const span = btn.querySelector('span');
      if (span) span.textContent = word;
      setTimeout(() => { if (span && span.isConnected) span.textContent = 'Copy rows'; }, 1400);
    };
    try {
      navigator.clipboard.writeText(csv).then(() => done('Copied'), () => done('Copy failed'));
    } catch (error) {
      done('Copy failed');
    }
  }

  /* ---------- events ---------- */
  function typingTarget(target) {
    if (!target || target === input) return false;
    const tag = String(target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || Boolean(target.isContentEditable);
  }

  function focusBar() {
    compact.wanted = false;
    sync();
    input.focus();
    if (typeof input.select === 'function' && input.value) input.select();
  }

  document.addEventListener('keydown', (event) => {
    const key = event.key;
    if ((key === 'k' || key === 'K') && (event.metaKey || event.ctrlKey) && !event.altKey) {
      event.preventDefault();
      focusBar();
      return;
    }
    if (key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !typingTarget(event.target)
        && document.activeElement !== input) {
      event.preventDefault();
      focusBar();
      return;
    }
    if (key === 'Escape') {
      /* ui.js closes an open preview card first (its listener runs before this one). */
      if (event.defaultPrevented) return;
      if (cardOpen()) {
        const anchor = cardState().anchor;
        hideCard(true);
        if (anchor && root.contains(anchor) && typeof anchor.focus === 'function') anchor.focus();
        event.preventDefault();
        return;
      }
      /* Esc belongs to the page while the person works in the page's own controls. */
      const focused = document.activeElement;
      if (focused && focused !== document.body && !root.contains(focused)) return;
      if (ui.listKind) {
        closeList();
        if (!input.value && !state.open) input.blur();
      } else if (state.open && !WORKSPACE) {
        closeSheet();
        if (root.contains(focused)) quietFocus();
      } else {
        input.blur();
      }
      event.preventDefault();
    }
  });

  input.addEventListener('keydown', (event) => {
    const count = ui.options.length;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!ui.listKind) {
        if (!input.value) showPrompts();
        else search(input.value.trim());
      }
      if (!ui.options.length) return;
      event.preventDefault();
      const step = event.key === 'ArrowDown' ? 1 : -1;
      let next = ui.active + step;
      if (next >= ui.options.length) next = 0;
      if (next < 0) next = ui.options.length - 1;
      setActive(next, true);
      if (cardOpen() && !cardState().pinned) hideCard(true);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (ui.listKind && ui.active >= 0 && ui.active < count) {
        activate(ui.options[ui.active], event.shiftKey);
        return;
      }
      ask(input.value);
    }
  });

  input.addEventListener('input', () => {
    const q = input.value.trim();
    hideCard(true);
    if (!q) {
      ui.results = null;
      if (isOpen()) closeList();
      else showPrompts();
      return;
    }
    search(q);
  });

  /* Back to the bar after the sheet closes, without opening the suggestions over the page. */
  function quietFocus() {
    ui.quiet = true;
    input.focus();
    ui.quiet = false;
  }

  input.addEventListener('focus', () => {
    state.focus = true;
    if (ui.quiet) { sync(); return; }
    if (!input.value && !isOpen()) showPrompts();
    else if (input.value.trim()) search(input.value.trim());
    sync();
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (ui.listKind && ui.active > 0 && ui.active < ui.options.length) {
      activate(ui.options[ui.active], false);
      return;
    }
    ask(input.value);
  });

  root.addEventListener('focusout', (event) => {
    const next = event.relatedTarget;
    if (next && (root.contains(next) || inCard(next))) return;
    setTimeout(() => {
      const now = document.activeElement;
      if (now && (root.contains(now) || inCard(now))) return;
      state.focus = false;
      if (ui.listKind) closeList();
      compact.wanted = restsCompact();
      sync();
    }, 0);
  });

  document.addEventListener('pointerdown', (event) => {
    const target = event.target;
    if (!target || root.contains(target) || inCard(target)) return;
    if (ui.listKind) closeList();
  });

  listBox.addEventListener('mousedown', (event) => { event.preventDefault(); });
  listBox.addEventListener('click', (event) => {
    const node = event.target.closest && event.target.closest('.gc-opt');
    if (!node) return;
    activate(ui.options[Number(node.getAttribute('data-i'))], event.shiftKey);
  });
  listBox.addEventListener('mousemove', (event) => {
    const node = event.target.closest && event.target.closest('.gc-opt');
    if (node && node.getAttribute('data-i') !== String(ui.active)) setActive(Number(node.getAttribute('data-i')), false);
  });

  root.addEventListener('click', (event) => {
    const target = event.target;
    if (!target || typeof target.closest !== 'function') return;
    const act = target.closest('[data-act]');
    if (act) {
      const what = act.getAttribute('data-act');
      if (what === 'expand') { focusBar(); return; }
      if (what === 'min') { closeSheet(); quietFocus(); }
      else if (what === 'resume') { state.panel = 'thread'; openSheet(); scrollToEnd(); input.focus(); }
      else if (what === 'new') {
        state.turns = [];
        state.panel = 'thread';
        hideCard(true);
        renderThread();
        setBusy();
        writeStore();
        sync();
        input.focus();
      } else if (what === 'panel') {
        state.panel = state.panel === 'desk' ? 'thread' : 'desk';
        sync();
        if (state.panel === 'thread' && !state.turns.length) renderEmpty();
      }
      return;
    }
    const sum = target.closest('.gc-trace-sum');
    if (sum) {
      const open = sum.getAttribute('aria-expanded') !== 'true';
      sum.setAttribute('aria-expanded', open ? 'true' : 'false');
      const steps = sum.parentNode.querySelector('.gc-steps');
      if (steps) steps.hidden = !open;
      return;
    }
    const follow = target.closest('.gc-follow-b');
    if (follow) {
      const text = follow.getAttribute('data-text');
      if (follow.getAttribute('data-recorded')) {
        const row = recordedViews().find((r) => r.view.question === text);
        if (row) { askRecorded(row.index); return; }
      }
      ask(text, follow.getAttribute('data-prompt'));
      return;
    }
    const cite = target.closest('.gc-cite');
    if (cite) {
      if (cardState().anchor === cite && cardState().pinned) hideCard(true);
      else showCite(cite, true);
      return;
    }
    const ent = target.closest('.gc-ent[data-kind]');
    if (ent && !event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) {
      event.preventDefault();
      if (cardState().anchor === ent && cardState().pinned) hideCard(true);
      else showPreview(ent, ent.getAttribute('data-kind'), ent.getAttribute('data-id'), true, null);
      return;
    }
    /* ask.js's own buttons inside an agent turn: a confirmation answers through ask.js. */
    const confirm = target.closest('[data-confirm], [data-decline]');
    if (confirm && thread.contains(confirm)) decideFromThread(confirm);
  });

  async function decideFromThread(button) {
    const d = desk();
    if (!d || typeof d.decide !== 'function') return;
    const yes = button.getAttribute('data-confirm');
    const id = yes || button.getAttribute('data-decline');
    const node = button.closest('[data-turn]');
    const turn = node ? findTurn(node.getAttribute('data-turn')) : null;
    await d.decide(id, yes ? 'confirm' : 'decline');
    const found = typeof d.current === 'function' ? d.current() : null;
    if (turn && found && found.html) {
      turn.html = found.html;
      updateTurn(turn);
      writeStore();
    }
  }

  /* Hover and focus open the card on a citation or a result row; a click pins it. */
  const hover = {show: 0, hide: 0};
  const canHover = () => !window.matchMedia || window.matchMedia('(hover: hover)').matches;
  function onOver(event) {
    if (!canHover()) return;
    const anchor = event.target.closest && event.target.closest(ANCHORS);
    if (!anchor) return;
    clearTimeout(hover.hide);
    if (cardState().anchor === anchor || (cardState().pinned && cardOpen())) return;
    clearTimeout(hover.show);
    const delay = anchor.classList.contains('gc-opt') ? 380 : 120;
    hover.show = setTimeout(() => showFor(anchor, false), delay);
  }
  function onOut(event) {
    const anchor = event.target.closest && event.target.closest(ANCHORS);
    if (!anchor) return;
    const next = event.relatedTarget;
    if (next && (anchor.contains(next) || inCard(next))) return;
    clearTimeout(hover.show);
    if (!cardState().pinned) hover.hide = setTimeout(() => hideCard(false), 180);
  }
  root.addEventListener('mouseover', onOver);
  root.addEventListener('mouseout', onOut);
  root.addEventListener('focusin', (event) => {
    const anchor = event.target.closest && event.target.closest('.gc-cite');
    if (!anchor || (cardState().pinned && cardOpen()) || cardState().anchor === anchor) return;
    clearTimeout(hover.show);
    hover.show = setTimeout(() => showFor(anchor, false), 200);
  });
  root.addEventListener('focusout', (event) => {
    const anchor = event.target.closest && event.target.closest('.gc-cite');
    if (!anchor) return;
    clearTimeout(hover.show);
    const next = event.relatedTarget;
    if (next && inCard(next)) return;
    if (!cardState().pinned && cardState().anchor === anchor) hideCard(false);
  });
  body.addEventListener('scroll', () => { if (cardOpen() && !cardState().pinned) hideCard(true); }, {passive: true});

  /* The shared card's own buttons: Copy rows for a citation; a link leaves with the sheet closed. */
  function wireCard() {
    const el = cardEl();
    if (!el || el.dataset.gcWired) return;
    el.dataset.gcWired = '1';
    el.addEventListener('click', (event) => {
      const target = event.target;
      if (!target || typeof target.closest !== 'function') return;
      const copy = target.closest('[data-copy]');
      if (copy) { copyRows(copy.getAttribute('data-copy')); return; }
      const goLink = target.closest('a[href]');
      if (goLink && !event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) {
        const href = goLink.getAttribute('href');
        if (safeHref(href)) { event.preventDefault(); go(href); }
      }
    });
  }

  /* The mic: shown, not wired. */
  root.querySelector('.gc-mic').addEventListener('click', (event) => event.preventDefault());

  function onClock() {
    prompts.key = '';
    if (ui.listKind === 'prompts') showPrompts();
  }

  if (PARTS.length && !WORKSPACE) {
    window.addEventListener('scroll', () => {
      const want = restsCompact();
      if (want === compact.wanted) return;
      if (want && (state.open || state.focus || ui.listKind)) return;  // in use: it stays as it is
      compact.wanted = want;
      sync();
    }, {passive: true});
  }

  /* ---------- start ---------- */
  attach();
  wireCard();
  renderThread();
  sync();
  if (window.GNShell && typeof window.GNShell.onAsOf === 'function') window.GNShell.onAsOf(onClock);
  if (isOpen()) scrollToEnd();
  if (WORKSPACE && !state.turns.length) renderEmpty();
  if (restsCompact() && !state.open) { compact.wanted = true; sync(); }
  /* ask.js may load after this file (a page without its own mount): adopt its mount once it runs. */
  if (!window.DeskAsk && !WORKSPACE) {
    let tries = 0;
    const wait = setInterval(() => {
      tries += 1;
      if (window.DeskAsk || tries > 40) { clearInterval(wait); adoptMount(); }
    }, 100);
  }
  const kbd = root.querySelector('.gc-kbd');
  if (kbd) kbd.setAttribute('title', (MAC ? '⌘K' : 'Ctrl K') + ' or / to focus');

  window.GNCommand = {
    state: state,
    ui: ui,
    ask: ask,
    focus: focusBar,
    open: () => openSheet('thread'),
    close: closeSheet,
    page: PAGE_KEY,
  };
})();
