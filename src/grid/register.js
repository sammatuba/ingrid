/* Register page. Design file: the committed assumption register as one dense table (DESK-5,
   platform polish 2026-10-18).
   Reads one baked file and nothing else: `/grid-data/<stamp>/register/index.json`, the index
   `scripts/grid/build_data.py` writes in the same bake as the replay data. Every sentence is
   composed from the file's own fields — no clock, nothing derived; every row's words are the
   register's own, its layer, state and owner the register's own vocabulary. The register file
   carries no instant, so the register's digest and git blob revision are the as-of every
   figure on the page cites. One row per assumption, opening onto its statement, its evidence,
   the marks on it and the issued outlooks that rest on it; one filter bar over the register's
   own family, layer and state words and its two known gaps, kept in the address. The markup
   follows the design system contract (docs/work/platform-polish-2026-10-18/design-system.md):
   ui.js sorts the table and opens a row's detail. */
(() => {
  'use strict';
  /* The build stamp the page was served under, as grid.js reads it: the index is asked for
     under the same build as this script. A page served without a stamp (a fixture harness
     serving the source HTML) reads the unversioned name, which is never cached. */
  const STAMP = (() => {
    const meta = typeof document !== 'undefined' && document.getElementById
      ? document.getElementById('nowcast-build') : null;
    const value = (meta && meta.getAttribute('content')) || '';
    return /^[0-9a-f]{16}$/.test(value) ? value + '/' : '';
  })();
  const DATA = '/grid-data/' + STAMP;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const hhmm = (t) => String(t || '').slice(11, 16);
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  /* A record date as "16 Oct 2026", read from the text, never from a clock. */
  const day = (t) => `${Number(String(t).slice(8, 10))} ${MONTHS[Number(String(t).slice(5, 7)) - 1] || ''} ${String(t).slice(0, 4)}`;
  /* Every instant is the record's own, with its date, in UTC — never a build instant. */
  const utcWhen = (t) => `${day(t)} ${hhmm(t)} UTC`;
  const shortHex = (value) => `${String(value).slice(0, 16)}…`;
  /* COPY-1: the bake names the version's basis in repository words; the page says it plainly. */
  const basisWords = (b) => (b === 'git blob id' ? 'its file id' : String(b || ''));
  /* COPY-1: a seat is not a person; the page says what the register means by it. */
  const ownerWords = (o) => (o === 'orchestrator seat' ? 'the project seat until a person is named' : String(o || ''));
  const plural = (n, word, many) => `${n} ${n === 1 ? word : (many || word + 's')}`;
  const GNUI = () => (typeof window !== 'undefined' && window.GNUI ? window.GNUI : null);

  let REGISTER = {};
  const version = () => `register version ${shortHex(REGISTER.revision)} (${basisWords(REGISTER.revision_basis)})`;

  /* The valid interval in the register's own dates: the record states them as calendar dates,
     so they are printed as stated, never converted to a clock time. A row that states neither
     end says so — the register's known gap, named, never hidden. */
  function intervalText(row) {
    const from = row.valid_from, to = row.valid_to;
    if (from && to) return `valid from ${from} to ${to}`;
    if (from) return `valid from ${from}, no end recorded`;
    if (to) return `valid to ${to}, no start recorded`;
    return 'no valid interval recorded';
  }
  /* The table's short form of the same interval: the dates as stated, or a quiet "None". */
  function intervalCell(row) {
    const from = row.valid_from, to = row.valid_to;
    if (!from && !to) return `<td class="gn-meta" data-value="" title="${esc(intervalText(row))}">None</td>`;
    const shown = from && from === to ? from : `${from || '…'} to ${to || '…'}`;
    return `<td class="mono trunc" data-value="${esc(from || to)}" title="${esc(intervalText(row))}">${esc(shown)}</td>`;
  }
  function checkedText(row) {
    return row.last_checked_revision
      ? `last checked at version ${row.last_checked_revision}`
      : 'never checked (no version recorded)';
  }
  /* One mark, in the record's own words: the change it records, the outlook whose exact bytes
     it affects, the marking instant, its own provenance and its record digest. A demonstration
     is named as a demonstration. */
  function markHtml(mark) {
    const kind = mark.synthetic ? 'A labelled demonstration mark names this row'
      : 'A change mark names this row';
    return `<li class="rg-mark">${esc(kind)} (${mark.synthetic ? 'synthetic' : 'synthetic false'}): `
      + `outlook <span class="mono">${esc(mark.outlook_id)}</span> at version `
      + `<span class="mono">${esc(mark.new_revision)}</span>, marked ${esc(utcWhen(mark.marked_at))} · `
      + `record <span class="mono">${esc(shortHex(mark.content_digest))}</span></li>`;
  }
  /* Copy rule 7: any synthetic record says so in the caption line, read from the shown marks'
     own `synthetic` flags — never a standing the page asserts for them. A page whose shown
     marks are all real change marks, or that shows no mark, has no synthetic record to name. */
  function provenanceSentence(marks) {
    const synthetic = marks.filter((mark) => mark.synthetic === true).length;
    if (!synthetic) return '';
    if (synthetic === marks.length) {
      return 'Every mark shown is a synthetic record (synthetic true): a labelled demonstration, '
        + 'not a recorded change.';
    }
    const rest = marks.length - synthetic;
    return `${synthetic} of ${marks.length} marks shown `
      + `${synthetic === 1 ? 'is a synthetic record' : 'are synthetic records'} (synthetic true): `
      + `${synthetic === 1 ? 'a labelled demonstration, not a recorded change'
        : 'labelled demonstrations, not recorded changes'}. `
      + (rest === 1 ? 'The other is a real change mark (synthetic false).'
        : 'The rest are real change marks (synthetic false).');
  }
  /* An evidence ref is a repository locator: path and line in quiet mono, the register's own
     quote beside it. No page serves repository files, so the locator is text to copy, not a link. */
  function evidenceRow(ref) {
    return `<li><code class="rg-ref">${esc(ref.path)}:${esc(ref.line)}</code> `
      + `<span class="rg-quote">${esc(ref.quote)}</span></li>`;
  }
  /* Each resting outlook is the index's own dependency-walk answer, and links to the page
     that lists the issued outlooks. */
  function outlookRow(outlook) {
    return `<li><a href="/outlooks">${esc(outlook.outlook_id)}</a> `
      + `<span class="gn-meta">issued ${esc(utcWhen(outlook.issued_at))}</span></li>`;
  }
  const unowned = (row) => !row.owner || row.owner === 'unassigned';
  const noInterval = (row) => !row.valid_from && !row.valid_to;

  /* One assumption: a row of the register's own fields, and the detail row under it that the
     row's button opens. The row's id is the assumption id, so `/register#<id>` opens it. */
  function rowHtml(row, place) {
    const detail = `rg-d-${place}`;
    const evidence = (row.evidence || []).map(evidenceRow).join('');
    const marks = (row.marks || []).map(markHtml).join('');
    const outlooks = (row.outlooks || []).map(outlookRow).join('');
    const owner = unowned(row)
      ? `<td class="gn-meta" title="${esc(ownerWords(row.owner) || 'no owner recorded')}">${esc(row.owner || 'none')}</td>`
      : `<td class="trunc" title="${esc(ownerWords(row.owner))}">${esc(ownerWords(row.owner))}</td>`;
    const checked = row.last_checked_revision
      ? `<td class="mono trunc" title="${esc(checkedText(row))}">${esc(String(row.last_checked_revision).slice(0, 10))}</td>`
      : `<td class="gn-meta" data-value="" title="${esc(checkedText(row))}">Never</td>`;
    return `<tr class="rg-row" id="${esc(row.assumption_id)}" data-family="${esc(row.family)}" `
      + `data-layer="${esc(row.layer)}" data-state="${esc(row.state)}">`
      + `<td class="rg-id"><div class="rg-id-cell"><button type="button" class="gn-row-toggle rg-toggle" aria-expanded="false" aria-controls="${detail}" `
      + `aria-label="Statement and evidence for ${esc(row.assumption_id)}"></button>`
      + `<span class="mono" title="${esc(row.assumption_id)}">${esc(row.assumption_id)}</span></div></td>`
      + `<td>${esc(row.family)}</td><td>${esc(row.layer)}</td>`
      + `<td><span class="gn-badge">${esc(row.state)}</span></td>`
      + owner + intervalCell(row) + checked
      + `<td class="num">${(row.evidence || []).length}</td>`
      + `<td class="num">${(row.outlooks || []).length || '<span class="gn-meta">–</span>'}</td></tr>`
      + `<tr class="gn-row-detail rg-detail" id="${detail}" hidden><td colspan="9"><div class="rg-detail-body">`
      + `<p class="rg-statement">${esc(row.proposition)}</p>`
      + `<p class="rg-line gn-meta">${esc(intervalText(row))} · ${esc(checkedText(row))} · owner ${esc(ownerWords(row.owner))}</p>`
      + `<div class="rg-cols"><div><h3 class="gn-label">Evidence</h3><ul class="rg-list rg-evidence">${evidence || '<li class="gn-meta">No evidence ref recorded.</li>'}</ul></div>`
      + `<div><h3 class="gn-label">Outlooks resting on it</h3><ul class="rg-list rg-outlooks">${outlooks || '<li class="gn-meta">No issued outlook rests on it.</li>'}</ul>`
      + (marks ? `<h3 class="gn-label">Marks</h3><ul class="rg-list rg-marks">${marks}</ul>` : '')
      + '</div></div></div></td></tr>';
  }

  /* The filter's options are the register's own words, as the index carries them, with an
     "all" reading in front; no option is computed or prettified. Each group is one segmented
     control in the filter bar. */
  function fill(group, all, values) {
    group.innerHTML = `<button type="button" data-value="all" aria-pressed="true">${esc(all)}</button>`
      + values.map((value) => `<button type="button" data-value="${esc(value)}" aria-pressed="false">${esc(value)}</button>`).join('');
  }
  function distinct(rows, field) {
    const values = [];
    for (const row of rows) if (!values.includes(row[field])) values.push(row[field]);
    return values;
  }

  /* The filter state. ui.js's filter controller (`GNUI.filters`) owns the bar and keeps it in
     the address, so a filtered view can be shared and comes back on load. */
  const DEFAULTS = { family: 'all', layer: 'all', state: 'all', gap: 'all', q: '' };
  const on = (v) => v && v !== 'all';

  function applyFilter(rows, state, ctl) {
    const q = String(state.q || '').trim().toLowerCase();
    let shown = 0;
    rows.forEach((row, place) => {
      const keep = (!on(state.family) || row.family === state.family)
        && (!on(state.layer) || row.layer === state.layer)
        && (!on(state.state) || row.state === state.state)
        && (state.gap !== 'owner' || unowned(row))
        && (state.gap !== 'interval' || noInterval(row))
        && (!q || `${row.assumption_id} ${row.proposition} ${row.owner}`.toLowerCase().includes(q));
      const tr = document.getElementById(row.assumption_id);
      const detail = document.getElementById(`rg-d-${place}`);
      if (tr) tr.hidden = !keep;
      if (detail) detail.hidden = !keep || tr.querySelector('[aria-expanded]').getAttribute('aria-expanded') !== 'true';
      if (keep) shown += 1;
    });
    $('rg-shown').textContent = shown === rows.length ? `${plural(shown, 'row')} shown`
      : `${shown} of ${plural(rows.length, 'row')} shown`;
    document.querySelectorAll('#rg-gap-actions [data-gap]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.gap === state.gap)));
    $('rg-table').querySelector('.gn-empty').hidden = shown > 0;
    $('rg-table').querySelector('.gn-table-wrap').hidden = shown === 0;
    if (!ctl) $('rg-clear').hidden = !Object.keys(DEFAULTS).some((key) => (state[key] || '') !== DEFAULTS[key]);
  }

  /* `/register#<assumption id>` (the outlooks and event pages link rows this way) opens that
     row and brings it into view. */
  function openTarget() {
    let id = '';
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (err) { id = ''; }
    const tr = id ? document.getElementById(id) : null;
    if (!tr || !tr.classList.contains('rg-row') || tr.hidden) return;
    const button = tr.querySelector('[aria-expanded]');
    button.setAttribute('aria-expanded', 'true');
    document.getElementById(button.getAttribute('aria-controls')).hidden = false;
    tr.classList.add('is-selected');
    tr.scrollIntoView({ block: 'center' });
  }

  async function main() {
    const empty = $('rg-empty');
    let data = null;
    try {
      const response = await fetch(DATA + 'register/index.json');
      if (response.ok) data = await response.json();
    } catch (err) {
      data = null;
    }
    if (!data || !data.register) {
      empty.hidden = false;
      empty.textContent = 'The register index could not be read from this build, so no assumption is shown.';
      $('rg-none').hidden = false;
      return;
    }
    REGISTER = data.register;
    const counts = data.counts || {};
    const families = Array.isArray(data.families) ? data.families : [];
    const rows = families.flatMap((block) => block.rows || []);
    const marks = rows.flatMap((row) => row.marks || []);
    /* Copy rule 4: a feature that is not connected is not shown. A register with no row draws
       the one honest absence state and no table. */
    if (!rows.length) {
      empty.hidden = false;
      empty.textContent = 'No assumption is recorded in this build\'s register.';
      $('rg-none').hidden = false;
      return;
    }
    $('rg-summary').textContent = `The register lists ${plural(counts.records, 'assumption')} `
      + `in ${plural(families.length, 'family', 'families')} · ${version()}.`;
    /* The register's known gaps, counted from the audit's own answers, in one line with a
       filter shortcut each — never hidden; each count carries its own word, singular or plural. */
    $('rg-gaps').textContent = `${plural(counts.unowned, 'row')} `
      + `${counts.unowned === 1 ? 'has' : 'have'} no owner · `
      + `${plural(counts.unknown_interval, 'row')} `
      + `${counts.unknown_interval === 1 ? 'has' : 'have'} no valid interval. `
      + `These are the register's known gaps.`;
    $('rg-gap-actions').innerHTML = (counts.unowned ? '<button type="button" class="gn-btn gn-btn--sm" data-gap="owner" aria-pressed="false">Show unowned</button>' : '')
      + (counts.unknown_interval ? '<button type="button" class="gn-btn gn-btn--sm" data-gap="interval" aria-pressed="false">Show no interval</button>' : '');
    $('rg-gaps-box').hidden = !(counts.unowned || counts.unknown_interval);

    $('rg-table').innerHTML = '<div class="gn-table-wrap"><table class="gn-table gn-table--compact rg-table" data-sortable>'
      + '<colgroup><col class="rg-c-id"><col class="rg-c-family"><col class="rg-c-layer"><col class="rg-c-state"><col class="rg-c-owner">'
      + '<col class="rg-c-valid"><col class="rg-c-checked"><col class="rg-c-n"><col class="rg-c-n"></colgroup>'
      + '<thead><tr><th scope="col" data-sort="text">Assumption</th><th scope="col" data-sort="text">Family</th>'
      + '<th scope="col" data-sort="text">Layer</th><th scope="col" data-sort="text">State</th><th scope="col" data-sort="text">Owner</th>'
      + '<th scope="col" data-sort="text">Valid</th><th scope="col" data-sort="text" title="Last checked at version">Checked</th>'
      + '<th scope="col" class="num" data-sort="num" title="Evidence refs">Evidence</th><th scope="col" class="num" data-sort="num" title="Issued outlooks that rest on it">Outlooks</th></tr></thead>'
      + `<tbody>${rows.map(rowHtml).join('')}</tbody></table></div>`
      + '<div class="gn-empty" role="status" hidden><p class="gn-empty-title">No assumption matches these filters</p>'
      + '<p class="gn-empty-body">The register holds rows, but none has every value you picked.</p>'
      + '<div class="gn-empty-actions"><button type="button" class="gn-btn" data-clear>Clear filters</button></div></div>';
    fill($('rg-family'), 'All families', distinct(rows, 'family'));
    fill($('rg-layer'), 'All layers', distinct(rows, 'layer'));
    fill($('rg-state'), 'All states', distinct(rows, 'state'));
    $('rg-gap').innerHTML = '<button type="button" data-value="all" aria-pressed="true">Any</button>'
      + '<button type="button" data-value="owner" aria-pressed="false">No owner</button>'
      + '<button type="button" data-value="interval" aria-pressed="false">No interval</button>';
    $('rg-filters').hidden = false;
    /* Without ui.js the page still draws every row, unfiltered, with the plain count. */
    let ctl = null;
    let state = Object.assign({}, DEFAULTS);
    const ui = GNUI();
    if (ui && ui.ready) await Promise.race([ui.ready, new Promise((resolve) => { setTimeout(resolve, 4000); })]);
    const G = GNUI();
    if (G && typeof G.filters === 'function') {
      ctl = G.filters($('rg-filters'), { defaults: DEFAULTS, onChange: (next) => { state = next; applyFilter(rows, state, ctl); } });
      state = ctl.get();
    }
    const set = (partial) => { if (ctl) ctl.set(partial); else { Object.assign(state, partial); applyFilter(rows, state, ctl); } };
    $('rg-gap-actions').addEventListener('click', (event) => {
      const button = event.target.closest('[data-gap]');
      if (!button) return;
      set({ gap: state.gap === button.dataset.gap ? 'all' : button.dataset.gap });
    });
    $('rg-table').addEventListener('click', (event) => {
      if (!event.target.closest('[data-clear]')) return;
      if (ctl) ctl.clear(); else set(Object.assign({}, DEFAULTS));
    });
    applyFilter(rows, state, ctl);
    openTarget();
    window.addEventListener('hashchange', openTarget);
    if (G && typeof G.resort === 'function') G.resort($('rg-table').querySelector('table'));
    $('rg-method').textContent = `Every row is the register's own record: its words, its layer, state and owner, its valid interval and its evidence refs. The index counts the gaps from the register's own audit. ${version()}, file ${REGISTER.path_hint || 'not named'}.`;
    /* Copy rule 7 lands in the one caption line: when a shown mark is a demonstration, the
       caption says a synthetic record is shown, from the marks' own flags. */
    const provenance = provenanceSentence(marks);
    $('caption').textContent += ' · register version ' + shortHex(REGISTER.revision)
      + ' (' + basisWords(REGISTER.revision_basis) + ') is the as-of of every figure'
      + (provenance ? '. ' + provenance : '.');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
})();
