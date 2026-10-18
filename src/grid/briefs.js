/* InGRID briefings and findings (ATG-5). A self-contained panel: `window.GridBriefs.mount(
   container, data, links)` draws the composed briefing for one grid at one replay time and the
   findings feed beside it. Nothing here is wired into the grid page yet — ATG-8 mounts it.

   Data is the bake's two files, already fetched by the caller: `data.briefs` is `briefs.json`
   (per grid: `latest` and one briefing per replay day) and `data.findings` is `findings.json`
   (`{findings: [...]}`). This module makes no request of its own and calls no model; every
   sentence it draws was composed by `scripts/grid/briefs.py` from the baked rows, and every entry
   carries the row it was read from.

   `links` (all optional) wires the panel to the page:
     { grid: 'CVIS', clock: '2026-09-21T13:40',
       figure: (ref, grid) => ...,   // a briefing or entry entity with data-figure="<code>:<series>"
       link:   (id) => ...,          // data-link="MINVIS1"
       message:(id) => ...,          // data-adv="V133937"
       site:   (code) => ...,        // data-site="08PEDC"
       event:  (id) => ... }         // a review link, /event/<id>
   The elements carry the same references the grid page already links (`data-figure`, `data-link`,
   `data-adv`, `data-site`), so the page's own EXPL-1 listeners can take them; when a callback is
   given this module also calls it on the click. The event link is an `<a href="/event/<id>">`, as
   the page's own review list writes it.

   The panel holds one click listener, delegated on its own section: it serves the chips, the
   entity references and the event link whatever the last redraw left inside it. A handler bound
   per node would stack on the chips, which persist across redraws, and a grid change, which
   redraws the paragraph alone, would leave the new paragraph's entities unwired.

   The returned controller is `{ setGrid(code), setClock(t), setKind(kind), select(), element }`;
   the clock picks the briefing of that replay day, the latest one when the clock is past the
   replay. `window.GridBriefs.filterFeed(findings, kind, clock)` is the feed's own selection —
   the rows at or before the clock, of the chosen kind, newest first, at most 60 of them — without
   a panel around it, so a harness with no DOM can read it.

   The chips are the five the task names: All, Events, Links, Prices, Messages. Findings of the
   reserve kind (the shortfall and the curtailment runs) are shown under All and are counted in the
   caption; they have no chip of their own, which the task record states. */
(() => {
  'use strict';

  const CHIPS = [['all', 'All'], ['event', 'Events'], ['link', 'Links'], ['price', 'Prices'],
                 ['message', 'Messages']];
  const KIND_LABEL = { price: 'Price', link: 'Link', reserve: 'Reserve', message: 'Message',
                       event: 'Event' };
  const ENTITY_ATTR = { grid: 'data-figure', link: 'data-link', message: 'data-adv', site: 'data-site' };
  const SHOWN = 60;                                   // entries drawn at once, newest first
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  /* FRONT-1: the feed's rows are drawn as runs. A run joins consecutive rows of the same kind,
     grid and label family in the feed's own newest-first order: the next row joins only when no
     row of the same kind and grid with another family stands between the two, and when the two
     are no more than RUN_GAP minutes apart. The brief's own example — the Visayas price rows at
     or near the cap from 13:05 to 13:35 — keeps a fifteen-minute gap (the Mindanao rows of the
     same minutes fall between them, but they are another grid), while rows hours or days apart,
     or a run interrupted by another claim about the same grid, stay apart. A row that carries a
     review link is always its own row, so the link is never behind a disclosure. The family is
     the claim the row's own rule makes, so F1 ("at the page's declared cap") and F2 ("within 3%
     of it") share the cap family, and no rule id has to be repeated in the words. A run of one
     row is drawn exactly as it was; a longer one is one expandable row naming its span and its
     count, and every member keeps its own composed headline and why. */
  const RUN_GAP = 30;                                 // minutes, the widest gap a run may cross
  const RUN_FAMILY = { F1: 'cap', F2: 'cap', F3: 'low', F4: 'p90', F5: 'p10',
                       F6: 'congestion', F7: 'reverse', F8: 'short', F9: 'curtailed',
                       F10: 'marked', F11: 'online', F12: 'event' };
  const RUN_LABEL = { cap: "At or near the page's declared cap", low: "At the replay's lowest",
                      p90: "Above the replay's own p90", p10: "Below the replay's own p10",
                      congestion: 'Congestion', reverse: 'Reversed flow',
                      short: 'Reserve short', curtailed: 'Load curtailed',
                      marked: 'Marked operator message', online: 'Back online',
                      event: 'Reviewable event' };

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  /* The bake writes its times as `YYYY-MM-DDTHH:MM[:SS]`; the page's clock reads the same way.
     Comparisons are made in one shape, so a finding at an interval and a message with seconds
     are ordered against the clock by the same rule. */
  const norm = (t) => String(t == null ? '' : t).replace('T', ' ');
  const hhmm = (t) => String(t || '').slice(11, 16);
  const dayOf = (t) => String(t || '').slice(0, 10);
  const dayWords = (t) => {
    // the replay day as words; the axis has a missing day, so a date is always written out
    const date = new Date(dayOf(t) + 'T00:00:00Z');
    const weekday = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][date.getUTCDay()];
    return `${weekday}, ${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
  };
  const stamp = (t) => `${dayOf(t).slice(8, 10)} ${MONTHS[Number(dayOf(t).slice(5, 7)) - 1]} ${hhmm(t)}`;

  /* A clause's segments are drawn as the page draws its brief: the entity as the reference the
     page links, the figure and the time in the tabular face. A time segment carries a label when
     the record belongs to an earlier replay day (`YYYY-MM-DD HH:MM`): its clock alone under the
     briefing's newer date would read as current, so the label is drawn in place of the clock. */
  function segments(list) {
    return list.map((s) => {
      if (s.segment === 'text') return esc(s.text);
      if (s.segment === 'figure') return `<b class="num">${esc(s.display)}</b>`;
      if (s.segment === 'time') return `<span class="num" data-t="${esc(s.iso)}">${esc(s.label || s.hhmm)}</span>`;
      if (s.type === 'event') return `<a class="ent b-event" href="/event/${esc(s.code)}">${esc(s.name)}</a>`;
      return `<span class="ent" ${ENTITY_ATTR[s.type] || 'data-entity'}="${esc(s.ref || s.code)}">${esc(s.name)}</span>`;
    }).join('');
  }

  function entry(f) {
    const e = f.entity || {};
    let ref = '';
    if (e.type && ENTITY_ATTR[e.type]) {
      ref = `<span class="ent b-ref" ${ENTITY_ATTR[e.type]}="${esc(e.ref || e.code)}">${esc(e.name)}</span>`;
    }
    const review = f.review ? `<a class="b-review" href="${esc(f.review)}">Review impact →</a>` : '';
    return `<li class="b-entry" data-kind="${esc(f.kind)}" data-rule="${esc(f.rule)}" data-grid="${esc(f.grid || '')}">` +
      `<div class="b-head"><span class="b-kind ${esc(f.kind)}">${esc(KIND_LABEL[f.kind] || f.kind)}</span>` +
      `<span class="b-market">${esc(f.grid_name)}</span>` +
      `<span class="b-time">${esc(stamp(f.t))}</span></div>` +
      `<div class="b-headline">${esc(f.headline)}</div>` +
      `<div class="b-why">${esc(f.why)}</div>` +
      `<div class="b-foot">${ref}${review}</div></li>`;
  }

  /* The family a row's own rule states (FRONT-1): two rules that make the same claim share it,
     so F1 and F2 are one family, and a rule not named here is its own family. */
  function familyOf(f) { return RUN_FAMILY[f.rule] || String(f.rule || ''); }
  function keyOf(f) { return `${f.kind}|${f.grid || ''}|${familyOf(f)}`; }

  /* A stamp in minutes since the epoch, or NaN when it states no readable clock. The bake and
     the page write `YYYY-MM-DDTHH:MM[:SS]` or `YYYY-MM-DD HH:MM[:SS]`; only the minutes matter
     to a run's gap. */
  function minutesOf(t) {
    const s = norm(t);
    if (s.length < 16) return NaN;
    return Date.UTC(Number(s.slice(0, 4)), Number(s.slice(5, 7)) - 1, Number(s.slice(8, 10)),
                    Number(s.slice(11, 13)), Number(s.slice(14, 16))) / 60000;
  }

  /* The runs the feed draws, in the order the feed's own newest-first rows give them: a run
     takes its place where its newest row stands, and the rows of its key that follow join it
     while they are consecutive and near enough (RUN_GAP). A row that carries a review link
     stands alone and also ends the run of its key, so the link is never hidden. */
  function runsOf(shown) {
    const out = [];
    const open = {};      // key -> the run at the end of the feed that is still taking rows
    const previous = {};  // kind|grid -> the key of its last row drawn
    for (const f of shown) {
      const key = keyOf(f), family = `${f.kind}|${f.grid || ''}`;
      const run = open[key];
      const gap = run ? minutesOf(run.rows[run.rows.length - 1].t) - minutesOf(f.t) : NaN;
      if (run && !f.review && previous[family] === key && gap >= 0 && gap <= RUN_GAP) {
        run.rows.push(f);
        continue;
      }
      const made = { key, rows: [f] };
      if (f.review) delete open[key]; else open[key] = made;
      out.push(made);
      previous[family] = key;
    }
    return out;
  }

  /* The span a run names: its newest and its oldest row's stamps, newest last, and one stamp
     when both ends are the same minute. */
  function runSpan(rows) {
    const newest = stamp(rows[0].t), oldest = stamp(rows[rows.length - 1].t);
    return newest === oldest ? newest : `${oldest} to ${newest}`;
  }

  /* One expandable row for a run of two or more: the kind, the grid, the span, the family and
     the count. Its members are the same entries a single row would draw, so opening it changes
     no finding's words. `<details>` is the native disclosure; the panel binds no handler for it.
     `data-run` is the run's key, so a redraw can open the runs the reader had open. */
  function runRow(run) {
    const rows = run.rows, first = rows[0];
    const what = RUN_LABEL[familyOf(first)] || KIND_LABEL[first.kind] || first.kind;
    return `<li class="b-group" data-run="${esc(run.key)}" data-kind="${esc(first.kind)}" data-grid="${esc(first.grid || '')}">` +
      `<details><summary><span class="b-head"><span class="b-kind ${esc(first.kind)}">` +
      `${esc(KIND_LABEL[first.kind] || first.kind)}</span>` +
      `<span class="b-market">${esc(first.grid_name)}</span>` +
      `<span class="b-time">${esc(runSpan(rows))}</span></span>` +
      `<span class="b-headline">${esc(what)} · ${rows.length} findings</span>` +
      `<span class="b-open">Show the ${rows.length} rows</span></summary>` +
      `<ol class="b-rows">${rows.map(entry).join('')}</ol></details></li>`;
  }

  function mount(container, data, links) {
    if (!container || !data) throw new Error('GridBriefs.mount(container, data, links): container and data are required');
    links = links || {};
    const briefs = data.briefs || {};
    const findings = (data.findings && data.findings.findings) || [];
    const grids = briefs.grids || {};
    const view = { grid: links.grid && grids[links.grid] ? links.grid : Object.keys(grids)[0],
                   clock: links.clock || (briefs.axis && briefs.axis.last) || '', kind: 'all' };

    const panel = document.createElement('section');
    panel.className = 'briefs';
    panel.innerHTML =
      '<article class="b-brief card"><h2 class="b-title"></h2><p class="b-text"></p><p class="b-asof"></p></article>' +
      '<article class="b-feed card"><div class="b-chips" role="group" aria-label="Finding kind"></div>' +
      '<ol class="b-entries"></ol><p class="b-count asof"></p></article>';
    container.appendChild(panel);
    const title = panel.querySelector('.b-title');
    const text = panel.querySelector('.b-text');
    const asof = panel.querySelector('.b-asof');
    const chips = panel.querySelector('.b-chips');
    const list = panel.querySelector('.b-entries');
    const count = panel.querySelector('.b-count');

    chips.innerHTML = CHIPS.map(([kind, label]) =>
      `<button type="button" data-kind="${kind}" aria-pressed="${kind === view.kind}">${label}</button>`).join('');

    function briefingFor() {
      const block = grids[view.grid];
      if (!block) return null;
      const day = dayOf(view.clock);
      if (day >= (block.latest.day || '')) return block.latest;
      const days = (block.days || []).filter((entry) => entry.day <= day);
      return days.length ? days[days.length - 1] : block.latest;
    }

    function drawBrief() {
      const briefing = briefingFor();
      if (!briefing) { title.textContent = ''; text.textContent = ''; asof.textContent = ''; return; }
      /* FRONT-1: the composed briefing is the day's closing brief (the bake composes it at the
         day's last interval), and the page's own narrative beside it is "What's happening" at
         the clock. The heading names which one this is; the as-of line keeps the grid's name. */
      title.textContent = `Closing brief, ${hhmm(briefing.t)}`;
      text.innerHTML = briefing.clauses.map((c) => esc(c.lead) + segments(c.segments)).join('');
      asof.textContent = `${briefing.name} · replay of ${dayWords(briefing.t)}, ${hhmm(briefing.t)} ` +
        `Manila time · composed by code from the replay figures`;
    }

    /* The reader's open runs survive a redraw: the feed rewrites its list on every clock tick,
       so a run the reader opened would fold again without this. The open state is kept by the
       run's key (kind, grid and family), the only identity a redrawn run shares. */
    function openRuns() {
      const keys = new Set();
      for (const box of list.querySelectorAll('details[open]')) {
        const group = box.closest('.b-group');
        if (group && group.dataset.run) keys.add(group.dataset.run);
      }
      return keys;
    }
    function reopenRuns(keys) {
      if (!keys.size) return;
      for (const group of list.querySelectorAll('.b-group')) {
        if (!keys.has(group.dataset.run)) continue;
        const box = group.querySelector('details');
        if (box) box.setAttribute('open', '');
      }
    }

    function drawFeed() {
      const { all, kept, shown } = filterFeed(findings, view.kind, view.clock);
      /* The rows are drawn as runs (FRONT-1), but the count keeps counting findings: the note is
         how many findings of the window are shown and how many there are, never how many rows
         the grouping drew. */
      const openKeys = openRuns();
      list.innerHTML = runsOf(shown).map((run) => (run.rows.length > 1 ? runRow(run)
        : entry(run.rows[0]))).join('');
      reopenRuns(openKeys);
      const note = shown.length < kept ? `${shown.length} of ${kept}` : `${kept}`;
      count.textContent = `${note} findings · ${all} at or before ${hhmm(view.clock)} ` +
        `${dayOf(view.clock)}`;
    }

    /* One listener on the panel serves every control, whatever the last redraw left inside it:
       the chips, a briefing or entry entity, and the event link. Bound once here, it cannot
       stack on the persistent chips, and it covers the paragraph `setGrid` replaces. */
    panel.addEventListener('click', (event) => {
      const node = event.target;
      if (!node || !node.closest) return;
      const chip = node.closest('button[data-kind]');
      if (chip) { setKind(chip.dataset.kind); return; }
      /* The event link is a real link, as the page's review list writes it. A caller that routes
         in the page rather than by navigation takes the click instead. */
      const anchor = node.closest('a.b-event');
      if (anchor && links.event) {
        event.preventDefault();
        links.event(anchor.getAttribute('href').split('/').pop());
        return;
      }
      const entity = node.closest('.ent');
      if (!entity) return;
      if (entity.dataset.figure && links.figure) links.figure(entity.dataset.figure);
      else if (entity.dataset.link && links.link) links.link(entity.dataset.link);
      else if (entity.dataset.adv && links.message) links.message(entity.dataset.adv);
      else if (entity.dataset.site && links.site) links.site(entity.dataset.site);
    });

    function draw() {
      drawBrief();
      drawFeed();
    }

    function setGrid(code) { if (grids[code]) { view.grid = code; drawBrief(); } }
    function setClock(t) { view.clock = t || view.clock; draw(); }
    function setKind(kind) {
      view.kind = kind;
      for (const button of chips.querySelectorAll('button')) {
        button.setAttribute('aria-pressed', String(button.dataset.kind === kind));
      }
      drawFeed();
    }

    draw();
    return { setGrid, setClock, setKind, select: () => filterFeed(findings, view.kind, view.clock),
             element: panel, view };
  }

  /* `filterFeed` is the feed's selection without a panel around it: a harness with no DOM can
     still exercise the clock cut, the kind filter and the shown-first order over a real bake. */
  function filterFeed(findings, kind, clock) {
    const at = norm(clock);
    const all = (findings || []).filter((f) => !at || norm(f.t) <= at);
    const kept = kind === 'all' ? all : all.filter((f) => f.kind === kind);
    return { all: all.length, kept: kept.length, shown: kept.slice(-SHOWN).reverse() };
  }

  if (typeof window !== 'undefined') window.GridBriefs = { mount, chips: CHIPS, filterFeed };
})();
