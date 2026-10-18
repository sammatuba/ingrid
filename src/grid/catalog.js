/* InGRID data catalog (`/data`). Reads the built catalog payload under the page's
   build-stamped prefix and draws the page: the anchor figures, the category rail, one dense
   table of every dataset and one dataset's detail in a panel beside the table (its schema, its
   lineage, the pages and code that read it, the baked file, a sample row and its licence).

   Every figure on the page comes from the payload, which `scripts/grid/build_catalog.py` joins
   from the hand-maintained register (`scripts/grid/catalog.json`) and the baked files it
   measures: a count with its record, or a count measured from a named file. No library, no
   network beyond same origin, and no figure the payload does not carry.

   Address: `?family=<id>&q=<text>` keeps the filter, so a filtered view can be shared, and
   `#<dataset id>` opens that dataset (the command bar's citations link there). The table's
   sorting is the shared layer's (`ui.js`, `th[data-sort]` reading `td[data-value]`); after a
   re-render the page asks it to re-apply the active sort. */
(() => {
  'use strict';
  /* The build stamp the page was served under, as `grid.js` reads it: the application writes it
     into the asset URLs and into `meta#nowcast-build`, so the catalog file is read from the same
     build as this script. A page served without a stamp (a fixture harness serving the source
     HTML) reads the unversioned name, which is never cached. */
  const STAMP = (() => {
    const meta = typeof document !== 'undefined' && document.getElementById
      ? document.getElementById('nowcast-build') : null;
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP + 'catalog.json';

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => (n == null ? '' : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','));
  const esc = (text) => String(text == null ? '' : text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  /* The pages of this site that a reader path names, so "Read by" links to the page and not only
     to the file. A path not listed here is code that is not a page: it is shown as its path. */
  const PAGES = {
    'src/grid/grid.js': ['The desk', '/'],
    'src/grid/map.js': ['The desk', '/'],
    'src/grid/overview.js': ['The desk', '/'],
    'src/grid/event.js': ['Event pages', '/alerts', 'Every event page reads it. Events open from alerts.'],
    'src/grid/asset.js': ['Plants', '/plants'],
    'src/grid/alerts.js': ['Alerts', '/alerts'],
    'src/grid/notices.js': ['Notices', '/notices'],
    'src/grid/outlooks.js': ['Outlooks', '/outlooks'],
    'src/grid/register.js': ['Assumption register', '/register'],
    'src/grid/book.js': ['Book', '/book'],
    'src/grid/journal.js': ['Journal', '/journal'],
    'src/grid/catalog.js': ['Data catalog', '/data'],
  };

  const state = { q: '', family: null, open: null };
  let D = null;          // the built payload
  let bounds = null;     // the coverage axis: [min, max] over every dated dataset
  let onRender = [];     // the harness's own listeners
  let lastFocus = null;  // the link that opened the panel, so closing it returns focus there

  // ------------------------------------------------------------------------------ reading

  /* A coverage bound as a number, or null when the bound is not a date. The builder's bounds are
     either stamps ("2021-06", "2026-09-29 23:55", "2026-09-21T00:00") or a stated unknown. */
  function parts(text) {
    const match = String(text || '').match(/^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?(?:[T ](\d{2}):(\d{2}))?/);
    if (!match) return null;
    return {year: Number(match[1]), month: match[2] ? Number(match[2]) : null,
            day: match[3] ? Number(match[3]) : null,
            hour: match[4] ? Number(match[4]) : 0, minute: match[5] ? Number(match[5]) : 0};
  }

  function stampValue(text) {
    const p = parts(text);
    if (!p) return null;
    return Date.UTC(p.year, (p.month || 1) - 1, p.day || 1, p.hour, p.minute);
  }

  /* Two bounds as one short range: "21 to 29 Sep 2026" inside one month, else "Jun 2021 to Oct 2026". */
  function rangeWords(first, last) {
    const a = parts(first), b = parts(last);
    if (!a || !b) return [first, last].filter(Boolean).join(' to ');
    if (a.day && b.day && a.year === b.year && a.month === b.month) {
      return (a.day === b.day ? '' : a.day + ' to ') + b.day + ' ' + MONTHS[b.month - 1] + ' ' + b.year;
    }
    const short = (p) => (p.month ? MONTHS[p.month - 1] + ' ' : '') + p.year;
    return short(a) === short(b) ? short(a) : short(a) + ' to ' + short(b);
  }

  function coverageOf(set) {
    const coverage = set.coverage || {};
    if (coverage.measured && set.measured) return {first: set.measured.first, last: set.measured.last, measured: true};
    if (coverage.first || coverage.last) return {first: coverage.first, last: coverage.last, record: coverage.record};
    return {first: null, last: null, why: coverage.why || null};
  }

  function rowsOf(set) {
    if ((set.rows || {}).measured && set.measured) return {count: set.measured.rows, where: 'measured'};
    if (typeof (set.rows || {}).count === 'number') return {count: set.rows.count, where: 'record', record: set.rows.record};
    return {count: null, where: 'not counted', why: (set.rows || {}).why || null};
  }

  function rowsNote(rows) {
    if (rows.where === 'measured') return 'Measured from the baked file';
    if (rows.where === 'record') return 'Stated by ' + rows.record;
    return 'Not counted' + (rows.why ? ': ' + rows.why : '');
  }

  /* The coverage bar: every dated dataset is drawn on one axis, so a bar can be compared with
     any other. A dataset with no dates keeps its bounds as words instead. */
  function computeBounds() {
    const values = [];
    for (const set of D.datasets) {
      const {first, last} = coverageOf(set);
      for (const value of [stampValue(first), stampValue(last)]) if (value != null) values.push(value);
    }
    bounds = values.length ? [Math.min(...values), Math.max(...values)] : null;
  }

  function bar(set) {
    const cover = coverageOf(set);
    const a = stampValue(cover.first), b = stampValue(cover.last);
    if (bounds == null || a == null || b == null) {
      return '<span class="cat-unknown" title="' + esc(cover.why || 'Not timed') + '">Not timed</span>';
    }
    const span = Math.max(1, bounds[1] - bounds[0]);
    const left = Math.max(0, ((Math.min(a, b) - bounds[0]) / span) * 100);
    const width = Math.max(1.5, (Math.abs(b - a) / span) * 100);
    return '<span class="span" aria-hidden="true"><span class="fill" data-left="' + left.toFixed(2) + '" data-width="'
      + Math.min(100 - left, width).toFixed(2) + '"></span></span>'
      + '<span class="span-label">' + esc(rangeWords(cover.first, cover.last)) + '</span>';
  }

  /* DATA-1: the site's policy is `style-src 'self'`, and a browser refuses a `style` attribute
     written in markup under it. A value set through the CSSOM after the markup is in the page is
     allowed, so the markup carries each bar's place as data (`data-left`, `data-width`) and this
     sets it on the nodes: the bars keep their exact place, and no markup the page writes carries
     a style attribute. The lineage is a nested list (PP-B4), so its indent is the stylesheet's
     and needs no value here. */
  function place(host) {
    if (!host || !host.querySelectorAll) return;
    for (const node of host.querySelectorAll('.fill')) {
      if (!node.style || node.getAttribute('data-left') == null) continue;
      node.style.setProperty('left', node.getAttribute('data-left') + '%');
      node.style.setProperty('width', node.getAttribute('data-width') + '%');
    }
  }

  function familyOf(id) {
    return D.families.find((f) => f.id === id) || null;
  }

  function familyName(id) {
    return (familyOf(id) || {}).name || id;
  }

  function matches(set) {
    if (state.family && set.family !== state.family) return false;
    const q = state.q.trim().toLowerCase();
    if (!q) return true;
    return [set.id, set.name, set.publisher, set.definition, set.cadence, familyName(set.family)]
      .some((field) => String(field || '').toLowerCase().includes(q));
  }

  function dataset(id) {
    return D.datasets.find((set) => set.id === id) || null;
  }

  /* The lineage chain: the dataset's upstream ids, walked up until the sources, each with how
     deep it sits, so the detail can draw the chain the register states. */
  function chain(id) {
    const out = [], seen = new Set([id]);
    const walk = (from, depth) => {
      for (const up of (dataset(from) || {}).upstream || []) {
        if (seen.has(up)) continue;
        seen.add(up);
        out.push({id: up, depth, name: (dataset(up) || {}).name || up});
        walk(up, depth + 1);
      }
    };
    walk(id, 0);
    return out;
  }

  /* The datasets built directly from this one: the other half of its lineage. */
  function feeds(id) {
    return D.datasets.filter((set) => (set.upstream || []).includes(id));
  }

  // ------------------------------------------------------------------------------ address

  function readAddress() {
    if (typeof location === 'undefined') return;
    try {
      const params = new URLSearchParams(location.search || '');
      const family = params.get('family');
      state.family = family && familyOf(family) ? family : null;
      state.q = params.get('q') || '';
    } catch (error) { /* an address the page cannot read keeps the defaults */ }
    const hash = String(location.hash || '').replace(/^#/, '');
    state.open = hash && dataset(decodeURIComponent(hash)) ? decodeURIComponent(hash) : null;
  }

  function writeAddress() {
    if (typeof history === 'undefined' || !history.replaceState || typeof location === 'undefined') return;
    try {
      const params = new URLSearchParams(location.search || '');
      if (state.family) params.set('family', state.family); else params.delete('family');
      if (state.q.trim()) params.set('q', state.q.trim()); else params.delete('q');
      const query = params.toString();
      history.replaceState(history.state, '', location.pathname + (query ? '?' + query : '')
        + (state.open ? '#' + encodeURIComponent(state.open) : ''));
    } catch (error) { /* the view still filters without an address */ }
  }

  // ------------------------------------------------------------------------------ rendering

  function renderStats() {
    const host = $('stats');
    if (!host) return;
    const totals = D.totals || {};
    const inBake = D.datasets.filter((set) => set.measured).length;
    const replay = D.replay || {};
    const first = replay.measured_first || replay.first, last = replay.measured_last || replay.last;
    const stat = (label, value, meta, key) => '<div class="gn-stat' + (key ? ' gn-stat--key' : '') + '">'
      + '<span class="gn-label">' + label + '</span>'
      + '<span class="gn-value gn-value--lg">' + value + '</span>'
      + (meta ? '<span class="gn-meta">' + meta + '</span>' : '') + '</div>';
    const mb = typeof totals.bytes === 'number' ? (totals.bytes / 1e6).toFixed(1) + ' MB' : '';
    host.innerHTML = ''
      + stat('Datasets', fmt(totals.datasets), 'in ' + fmt(totals.families) + ' categories', true)
      + stat('In the bake', fmt(inBake), 'datasets the site serves')
      + stat('Baked files measured', fmt(totals.measured_files),
             [mb, typeof totals.measured_rows === 'number' ? fmt(totals.measured_rows) + ' rows' : '']
               .filter(Boolean).join(' · '))
      + (first && last ? stat('Replay window', replayValue(first, last), 'Manila civil time') : '');
  }

  /* The replay window as a figure: the days as the value, the month and year as its unit. */
  function replayValue(first, last) {
    const a = parts(first), b = parts(last);
    if (!a || !b || !a.day || !b.day || a.year !== b.year || a.month !== b.month) return esc(rangeWords(first, last));
    return (a.day === b.day ? a.day : a.day + '\u2013' + b.day)
      + '<span class="gn-unit">' + MONTHS[b.month - 1] + ' ' + b.year + '</span>';
  }

  function renderTiles() {
    const host = $('tiles');
    if (!host) return;
    host.innerHTML = '';
    const make = (id, name, count, title) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'cat-cat';
      button.setAttribute('data-family', id || '');
      button.setAttribute('aria-pressed', String((state.family || null) === (id || null)));
      if (title) button.setAttribute('title', title);
      button.innerHTML = '<span class="cat-cat-name">' + esc(name) + '</span>'
        + '<span class="cat-cat-n">' + fmt(count) + '</span>';
      button.addEventListener('click', () => setFamily(id && state.family !== id ? id : null));
      host.appendChild(button);
    };
    make(null, 'All datasets', D.totals.datasets, D.totals.families + ' categories, '
      + fmt(D.totals.measured_files) + ' baked files measured');
    for (const family of D.families) make(family.id, family.name, family.count, family.definition);
  }

  function rowMarkup(set) {
    const rows = rowsOf(set);
    const cover = coverageOf(set);
    const sortTime = stampValue(cover.first);
    const rowCell = rows.count == null
      ? '<td class="num" data-value="-1"><span class="cat-unknown" title="' + esc(rowsNote(rows)) + '">not counted</span></td>'
      : '<td class="num" data-value="' + rows.count + '" title="' + esc(rowsNote(rows)) + '">' + fmt(rows.count) + '</td>';
    return ''
      + '<td class="trunc" title="' + esc(set.name + '. ' + set.definition) + '">'
      + '<a class="cat-name" href="#' + esc(set.id) + '">' + esc(set.name) + '</a></td>'
      + '<td class="trunc cat-pub" title="' + esc(set.publisher) + '">' + esc(set.publisher) + '</td>'
      + '<td class="trunc cat-cad" title="' + esc(set.cadence) + '">' + esc(set.cadence) + '</td>'
      + '<td class="cat-cov" data-value="' + (sortTime == null ? '' : sortTime) + '">' + bar(set) + '</td>'
      + rowCell;
  }

  function renderList() {
    const host = $('list');
    if (!host) return;
    const shown = D.datasets.filter(matches);
    host.innerHTML = shown.map((set) => '<tr data-set="' + esc(set.id) + '" data-href="#' + esc(set.id) + '"'
      + (state.open === set.id ? ' aria-selected="true" class="is-selected"' : '')
      + '>' + rowMarkup(set) + '</tr>').join('');
    for (const tr of host.querySelectorAll ? host.querySelectorAll('tr') : []) {
      const id = tr.getAttribute && tr.getAttribute('data-set');
      if (!id) continue;
      /* The name is a real link for the keyboard and a new tab; a click anywhere else on the row
         opens the same dataset. */
      tr.addEventListener('click', (event) => {
        const target = event && event.target;
        if (target && target.closest && target.closest('a')) return;
        go(id);
      });
    }
    place(host);
    const table = $('sets');
    if (table && typeof window !== 'undefined' && window.GNUI && typeof window.GNUI.resort === 'function') {
      window.GNUI.resort(table);
    }

    const empty = $('empty');
    if (empty) {
      empty.hidden = shown.length > 0;
      empty.innerHTML = shown.length ? '' : '<div class="gn-empty" role="status">'
        + '<p class="gn-empty-title">No dataset matches</p>'
        + '<p class="gn-empty-body">' + (state.q.trim()
          ? 'Nothing' + (state.family ? ' in ' + esc(familyName(state.family)) : '') + ' matches "' + esc(state.q.trim()) + '".'
          : 'This category holds no dataset.') + '</p>'
        + '<div class="gn-empty-actions"><button type="button" class="gn-btn" data-clear>Clear filters</button></div></div>';
      for (const button of empty.querySelectorAll ? empty.querySelectorAll('button') : []) {
        button.addEventListener('click', clear);
      }
    }
    const count = $('count');
    if (count) count.textContent = shown.length + ' of ' + D.totals.datasets + ' datasets';
    const clearButton = $('clear');
    if (clearButton) clearButton.hidden = !state.q.trim() && !state.family;
    const note = $('family-note');
    if (note) {
      const family = state.family ? familyOf(state.family) : null;
      note.hidden = !family;
      note.textContent = family ? family.definition : '';
    }
    const axis = $('axis');
    if (axis && bounds) {
      const from = new Date(bounds[0]).getUTCFullYear(), to = new Date(bounds[1]).getUTCFullYear();
      const years = from === to ? String(from) : from + ' to ' + to;
      axis.setAttribute('title', 'Every bar is drawn on one axis, ' + years);
      axis.setAttribute('aria-label', 'Coverage, drawn on one axis from ' + years);
    }
  }

  function kv(rows) {
    return '<table class="cat-kv"><tbody>' + rows.filter(Boolean).map(([label, value, title]) =>
      '<tr><th scope="row">' + label + '</th><td' + (title ? ' title="' + esc(title) + '"' : '') + '>'
      + value + '</td></tr>').join('') + '</tbody></table>';
  }

  /* The upstream chain as a small tree: each source the dataset is built from, and what that
     source is built from in turn, nested under it. */
  function treeMarkup(id, seen) {
    const ups = ((dataset(id) || {}).upstream || []).filter((up) => !seen.has(up));
    if (!ups.length) return '';
    ups.forEach((up) => seen.add(up));
    return '<ul>' + ups.map((up) => {
      const set = dataset(up);
      return '<li><a href="#' + esc(up) + '" data-set-link="' + esc(up) + '" data-entity="dataset:' + esc(up) + '">'
        + esc(set ? set.name : up) + '</a>'
        + treeMarkup(up, seen) + '</li>';
    }).join('') + '</ul>';
  }

  function readersMarkup(set) {
    const pages = [], code = [], named = new Set();
    for (const path of set.read_by || []) {
      const page = PAGES[path];
      if (page && !named.has(page[1] + page[0])) {
        named.add(page[1] + page[0]);
        pages.push('<li><a class="gn-link" href="' + esc(page[1]) + '"' + (page[2] ? ' title="' + esc(page[2]) + '"' : '')
          + '>' + esc(page[0]) + '</a></li>');
      }
      code.push('<li><code>' + esc(path) + '</code></li>');
    }
    if (!code.length) return '<p class="cat-none">No code reads it today.</p>';
    return (pages.length ? '<ul class="cat-pages">' + pages.join('') + '</ul>'
                         : '<p class="cat-none">No page of the site reads it directly.</p>')
      + '<details class="gn-disclosure cat-code"><summary>Code that reads it (' + code.length + ')</summary>'
      + '<ul class="cat-paths">' + code.join('') + '</ul></details>';
  }

  function renderDetail() {
    const host = $('detail-body');
    const panel = $('detail');
    const title = $('detail-title');
    const set = state.open ? dataset(state.open) : null;
    const layout = $('layout');
    if (layout && layout.classList) layout.classList[set ? 'add' : 'remove']('is-open');
    if (!host || !panel) return;
    if (!set) { panel.hidden = true; if (title) title.textContent = 'Dataset'; return; }
    panel.hidden = false;
    if (title) title.textContent = set.name;
    const crumbs = $('detail-crumbs');
    if (crumbs) {
      crumbs.innerHTML = '<a href="/data" data-crumb="">Data catalog</a>'
        + '<a href="/data?family=' + esc(set.family) + '" data-crumb="' + esc(set.family) + '">' + esc(familyName(set.family)) + '</a>';
      for (const link of crumbs.querySelectorAll ? crumbs.querySelectorAll('a') : []) {
        link.addEventListener('click', (event) => {
          if (event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
          event.preventDefault();
          setFamily(link.getAttribute('data-crumb') || null);
        });
      }
    }
    const publisher = $('detail-publisher');
    if (publisher) publisher.textContent = set.publisher;

    const rows = rowsOf(set);
    const cover = coverageOf(set);
    const measured = set.measured || null;
    const licenceId = set.licence && set.licence.id || set.licence;
    const licence = D.licences.find((item) => item.id === licenceId) || {};
    const schema = set.schema || {};
    const fields = (schema.fields || []).map((field) => '<tr><td class="mono">'
      + '<span class="cat-s-field">' + esc(field.field) + '</span>'
      + '<span class="cat-s-meaning">' + esc(field.meaning) + '</span></td>'
      + '<td class="cat-s-unit">' + esc(field.unit) + '</td></tr>').join('');
    const tree = treeMarkup(set.id, new Set([set.id]));
    const below = feeds(set.id);
    const files = measured ? measured.files.map((file) => '<tr><td class="mono trunc" title="' + esc(file.name) + '">'
      + esc(file.name) + '</td><td class="num">' + fmt(file.rows) + '</td><td class="num">' + fmt(file.bytes)
      + '</td><td class="mono" title="' + esc(file.sha256 || '') + '">' + esc((file.sha256 || '').slice(0, 12))
      + '</td></tr>').join('') : '';
    const sample = set.sample || null;
    const coverWords = cover.first || cover.last ? rangeWords(cover.first, cover.last) : 'Not timed';
    const coverTitle = cover.measured ? 'Measured from the baked file'
      : cover.record ? 'Stated by ' + cover.record : (cover.why || '');

    host.innerHTML = ''
      + '<p class="cat-d-def">' + esc(set.definition) + '</p>'
      + kv([
        ['Cadence', esc(set.cadence)],
        ['Coverage', esc(coverWords)
          + (coverTitle ? '<span class="cat-d-sub">' + esc(coverTitle) + '</span>' : ''), ''],
        ['Rows', rows.count == null ? '<span class="cat-unknown">not counted</span>'
          + (rows.why ? '<span class="cat-d-sub">' + esc(rows.why) + '</span>' : '')
          : '<span class="gn-num">' + fmt(rows.count) + '</span><span class="cat-d-sub">' + esc(rowsNote(rows)) + '</span>'],
        ['In the bake', measured ? 'Yes, ' + measured.files.length + (measured.files.length === 1 ? ' file' : ' files') : 'No'],
        ['Licence', '<code>' + esc(licenceId) + '</code>'],
      ])
      + '<section class="cat-d-sec"><h3 class="gn-label">Schema</h3>'
      + (schema.state === 'not stated'
        ? '<p class="cat-none">Schema not stated: ' + esc(schema.why) + '</p>'
        : '<table class="cat-schema"><colgroup><col><col class="cat-s-unit-col"></colgroup>'
          + '<thead><tr><th scope="col">Field and meaning</th><th scope="col">Unit</th></tr></thead><tbody>'
          + fields + '</tbody></table>')
      + '</section>'
      + '<section class="cat-d-sec"><h3 class="gn-label">Lineage</h3>'
      + '<div class="cat-tree"><p class="cat-tree-root">' + esc(set.name) + '</p>'
      + (tree ? '<p class="cat-tree-cap">Built from</p>' + tree : '<p class="cat-none">A source dataset: nothing upstream.</p>')
      + (below.length ? '<p class="cat-tree-cap">Feeds</p><ul class="cat-feeds">' + below.map((down) =>
        '<li><a href="#' + esc(down.id) + '" data-set-link="' + esc(down.id) + '" data-entity="dataset:' + esc(down.id) + '">'
        + esc(down.name) + '</a></li>').join('') + '</ul>' : '')
      + '</div></section>'
      + '<section class="cat-d-sec"><h3 class="gn-label">Read by</h3>' + readersMarkup(set) + '</section>'
      + (measured ? '<section class="cat-d-sec"><h3 class="gn-label">Baked file</h3><div class="gn-table-wrap">'
        + '<table class="gn-table gn-table--compact gn-on-panel cat-files"><colgroup><col><col class="cat-f-num"><col class="cat-f-num"><col class="cat-f-sha"></colgroup>'
        + '<thead><tr><th scope="col">File</th><th scope="col" class="num">Rows</th>'
        + '<th scope="col" class="num">Bytes</th><th scope="col">sha256</th></tr></thead><tbody>' + files + '</tbody></table></div></section>' : '')
      + '<section class="cat-d-sec"><h3 class="gn-label">Sample row</h3>'
      + (sample
        ? '<p class="src">' + esc(sample.file) + (sample.at ? ' at ' + esc(sample.at)
          + (sample.exact === false ? ' (nearest baked interval)' : '') : '')
          + (sample.index != null ? ' row ' + sample.index : '') + '</p>'
          + '<pre class="cat-sample">' + esc(JSON.stringify(sample.row, null, 1)) + '</pre>'
        : '<p class="cat-none">This dataset is not in the bake, so the page shows no row of it.</p>')
      + '</section>'
      + '<section class="cat-d-sec"><h3 class="gn-label">Licence</h3>'
      + '<p class="cat-d-text"><code>' + esc(licenceId) + '</code></p>'
      + (licence.use ? '<p class="cat-d-text">' + esc(licence.use) + '</p>' : '')
      + (set.licence && set.licence.note ? '<p class="cat-d-text">' + esc(set.licence.note) + '</p>' : '')
      + (licence.record ? '<p class="cat-d-meta">Record <code>' + esc(licence.record) + '</code></p>' : '')
      + '</section>'
      + (set.note ? '<section class="cat-d-sec"><h3 class="gn-label">Note</h3><p class="cat-d-text">' + esc(set.note) + '</p></section>' : '');
  }

  /* DATA-1: the replay window the page states is the bake's own, measured by the builder
     (`replay.json`'s first and last, else the baked interval axis), never the register's
     declared nine days. The register's bounds show only when nothing was measured, and then
     say they are declared and by which record. The words are the builder's `window_text`, so
     a payload built before DATA-1 (measured bounds beside the declared ones) reads the same. */
  function replayWindow() {
    const replay = D.replay || {};
    const at = (stamp) => String(stamp).replace('T', ' ').slice(0, 16);
    if (replay.measured_first && replay.measured_last) {
      return 'replay ' + at(replay.measured_first) + ' to ' + at(replay.measured_last)
        + ', Manila civil time, measured from ' + (replay.measured_from || 'the baked files');
    }
    const declared = replay.declared || replay;
    const words = (D.caption || {}).window
      || (declared.first && declared.last ? 'replay ' + at(declared.first) + ' to ' + at(declared.last) : '');
    return words ? words.replace(/ \(declared by [^)]*\)$/, '') + ' (declared by '
      + (declared.record || 'the register') + '; no baked interval was measured)' : '';
  }

  /* The one sources block, from the payload: the source, the permission, the replay window and
     how every other figure is read. The page carries the same words, without a window, before
     the data lands, so the line is there to read either way. */
  function renderCaption() {
    const node = $('caption');
    if (!node || !D.caption) return;
    const caption = D.caption;
    node.textContent = 'Source: ' + [caption.source, caption.permission, replayWindow(),
                                     caption.method].filter(Boolean).join(' · ');
    const list = $('licences');
    if (list && Array.isArray(D.licences)) {
      list.innerHTML = D.licences.map((item) => '<li><code>' + esc(item.id) + '</code> ' + esc(item.use || '') + '</li>').join('');
    }
  }

  function render() {
    if (!D) return;
    renderStats();
    renderTiles();
    renderList();
    renderDetail();
    renderCaption();
    for (const listener of onRender) listener(state);
  }

  // ------------------------------------------------------------------------------ actions

  function setFamily(id) {
    state.family = id && familyOf(id) ? id : null;
    writeAddress();
    render();
  }

  function focusTitle() {
    const title = $('detail-title');
    if (title && typeof title.focus === 'function') {
      try { title.focus({preventScroll: true}); } catch (error) { title.focus(); }
    }
  }

  function revealRow(id) {
    if (typeof document.querySelector !== 'function') return;
    const row = document.querySelector('#list tr[data-set="' + String(id).replace(/["\\]/g, '') + '"]');
    if (row && typeof row.scrollIntoView === 'function') row.scrollIntoView({block: 'nearest'});
  }

  /* Open one dataset in the panel. A dataset outside the current filter clears the filter first,
     so a link from anywhere always lands on its row. */
  function open(id, focus) {
    if (id && !dataset(id)) id = null;
    if (id && !matches(dataset(id))) {
      state.family = null;
      state.q = '';
      const input = $('search');
      if (input) input.value = '';
    }
    state.open = id;
    writeAddress();
    render();
    if (id && focus) { focusTitle(); revealRow(id); }
  }

  function go(id) {
    if (typeof document !== 'undefined' && document.activeElement) lastFocus = document.activeElement;
    open(id, true);
  }

  function close() {
    const was = state.open;
    state.open = null;
    writeAddress();
    render();
    const back = was && typeof document.querySelector === 'function'
      ? document.querySelector('#list tr[data-set="' + String(was).replace(/["\\]/g, '') + '"] a') : null;
    const target = back || lastFocus;
    if (target && typeof target.focus === 'function') target.focus();
  }

  function search(q) {
    state.q = String(q);
    const input = $('search');
    if (input && input.value !== state.q) input.value = state.q;
    writeAddress();
    render();
  }

  function clear() {
    state.q = '';
    state.family = null;
    const input = $('search');
    if (input) input.value = '';
    writeAddress();
    render();
  }

  function wire() {
    const input = $('search');
    if (input) {
      input.value = state.q;
      input.addEventListener('input', (event) => search(event.target.value));
      input.addEventListener('search', (event) => search(event.target.value));
    }
    const clearButton = $('clear');
    if (clearButton) clearButton.addEventListener('click', clear);
    const closeButton = $('detail-close');
    if (closeButton) closeButton.addEventListener('click', close);
    if (typeof window !== 'undefined' && window.addEventListener) {
      window.addEventListener('hashchange', () => {
        const id = decodeURIComponent(String(location.hash || '').replace(/^#/, ''));
        if (id === (state.open || '')) return;
        if (!id) { state.open = null; render(); return; }
        if (dataset(id)) go(id);
      });
    }
    if (typeof document !== 'undefined' && document.addEventListener) {
      document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape' || !state.open || event.defaultPrevented) return;
        const target = event.target;
        if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName || '')) return;
        close();
      });
    }
  }

  function failed(error) {
    const host = $('list');
    if (host) {
      host.innerHTML = '<tr><td colspan="5"><p class="gn-error">The catalog could not be loaded: '
        + esc(error && error.message ? error.message : error) + '. '
        + '<button type="button" class="gn-btn gn-btn--sm" data-retry>Retry</button></p></td></tr>';
      for (const button of host.querySelectorAll ? host.querySelectorAll('button') : []) {
        button.addEventListener('click', load);
      }
    }
    if (typeof console !== 'undefined' && console.warn) console.warn('catalog:', error);
  }

  /* The surface the harness and the page tests read: the payload, the click handlers and the
     renderer. A page served without a stamp still fetches the unversioned name, which the
     application answers uncached. */
  window.DataCatalog = {
    get D() { return D; },
    state, DATA, render, open, close, search, setFamily, clear,
    familyName, chain, feeds, rangeWords, onRender: (fn) => { onRender.push(fn); },
  };

  let wired = false;
  function load() {
    return fetch(DATA).then((response) => {
      if (!response.ok) throw new Error(DATA + ' answered ' + response.status);
      return response.json();
    }).then((payload) => {
      D = payload;
      computeBounds();
      readAddress();
      if (!wired) { wire(); wired = true; }
      render();
      if (state.open) revealRow(state.open);
      if (typeof Event === 'function' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new Event('data-catalog-ready'));
      }
    }).catch(failed);
  }
  load();
})();
