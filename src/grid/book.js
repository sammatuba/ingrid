/* Book page (BOOK-3). Design file: the synthetic book as one surface.
   Reads two baked files and nothing else: `/grid-data/<stamp>/book/index.json` (the book record
   and its contract hour runs) and `/grid-data/<stamp>/book/exposure.json` (the materiality block,
   the vintage chosen per region, the heat steps, the exposure record and one impact record per
   region), both written by `scripts/book/bake_book.py`. The page does no arithmetic: every figure,
   sum, shade step and hour run is a field of those files, printed at the precision the record
   holds. Each table's caption names the record its rows come from and its cutoff, once (platform
   polish: no column repeats one value in every row). The synthetic label is in the title, in the
   header line under the bar, in the page head and beside every table. The page opens on the
   exposure, and three tabs hold the exposure, the impact band and the book's own records. */
(() => {
  'use strict';
  /* The build stamp the page was served under, as the other pages read it. A page served without
     a stamp reads the unversioned names. */
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
  const MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  /* A record date `2026-10-18` as `18 Oct 2026`, read from the text, never from a clock. */
  const day = (t) => {
    const text = String(t || '');
    return `${Number(text.slice(8, 10))} ${MONTHS[Number(text.slice(5, 7))]} ${text.slice(0, 4)}`;
  };
  /* A record instant `2026-10-18T06:00:00Z` as `18 Oct 2026 06:00 UTC`. */
  const utcWhen = (t) => `${day(t)} ${String(t || '').slice(11, 16)} UTC`;
  const clock = (h) => `${String(h).padStart(2, '0')}:00`;
  /* The short form of a record id, as the impact label prints it: the first 12 hex digits. */
  const short = (id) => `${String(id).slice(0, 12)}…`;
  /* A figure at the precision its record holds, thousands grouped. The record already holds the
     figure at these decimals, so this formats and never rounds. */
  const fig = (value, digits) => {
    const text = Number(value).toFixed(digits);
    const sign = text.startsWith('-') ? '-' : '';
    const [whole, part] = text.replace('-', '').split('.');
    return sign + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (part === undefined ? '' : '.' + part);
  };
  const mwh = (v) => fig(v, 3);
  const mw = (v) => fig(v, 3);
  const php = (v) => fig(v, 2);
  const KIND_WORDS = { fixed_price: 'fixed price', tou_block: 'time-of-use block' };
  const COMPARATOR_WORDS = { at_or_above: 'at or above', above: 'above' };
  /* The page's own fixed sentences. The materiality line classifies a change between two vintages,
     never a level in the band table, and the page says so right under the line (review round 1). */
  const LINE_SCOPE = 'The line applies to a change between two vintages, not to the levels in this table.';
  const EMPTY_LINE = 'The build has no book files, so the page shows no figure.';
  const noVintage = (region, when) => `No vintage prices ${region} at the cutoff of ${when}, so the page shows no band for it.`;

  /* The line beside every table: the word Synthetic first, then the record and its as-of. */
  const flagLine = (text) => `<p class="bk-cap bk-say"><b class="bk-syn">Synthetic.</b> ${esc(text)}</p>`;
  const cell = (value, cls) => `<td${cls ? ` class="${cls}"` : ''}>${esc(value)}</td>`;
  /* A region is a grid: its cell links the desk scoped to that grid, with the entity preview. */
  const regionCell = (name, code) => (code
    ? `<td><a href="/?grid=${esc(code)}" data-entity="grid:${esc(code)}">${esc(name)}</a></td>` : cell(name));
  /* A header label is a name, or [name, unit] for a figure column: the unit sits in the header,
     never in the cells, and a figure column is right-aligned and sortable. An hour column of the
     heat is [hour, ''], right-aligned and not sortable. */
  const head = (labels, sortable) => '<thead><tr>' + labels.map((label) => {
    const [name, unit] = Array.isArray(label) ? label : [label, null];
    if (unit === '') return `<th scope="col" class="num">${esc(name)}</th>`;
    const sort = (kind) => (sortable === false ? '' : ` data-sort="${kind}"`);
    return unit
      ? `<th scope="col" class="num"${sort('num')}>${esc(name)} <span class="gn-unit">${esc(unit)}</span></th>`
      : `<th scope="col"${sort('text')}>${esc(name)}</th>`;
  }).join('') + '</tr></thead>';
  /* `cols` names each column's width class (empty for a column that takes the rest). */
  const table = (key, labels, rows, sortable, cols) => `<div class="gn-table-wrap bk-wrap"><table class="gn-table gn-table--compact bk-table" data-table="${key}"${sortable === false ? '' : ' data-sortable'}>`
    + (cols ? `<colgroup>${cols.map((c) => (c ? `<col class="${c}">` : '<col>')).join('')}</colgroup>` : '')
    + head(labels, sortable) + `<tbody>${rows.join('')}</tbody></table></div>`;
  /* A figure cell carries the record's value as its sort key, as printed. */
  const num = (text) => `<td class="num" data-value="${esc(String(text).replace(/,/g, ''))}">${esc(text)}</td>`;

  /* A section: its title, its sentences, the synthetic caption line and the table. Sentences
     that explain the method rather than the figures (`more`) fold under one disclosure. */
  function sectionHtml(key, title, sayings, caption, body, more) {
    const say = (text) => `<p class="bk-text bk-say">${esc(text)}</p>`;
    return `<section class="gn-section bk-section" data-section="${key}"><h2>${esc(title)}</h2>`
      + sayings.map(say).join('')
      + (more && more.length ? `<details class="gn-disclosure bk-more"><summary>${esc(more[0])}</summary>${more.slice(1).map(say).join('')}</details>` : '')
      + flagLine(caption) + body + '</section>';
  }

  /* The book record: accounts, load nodes and contracts, each row citing the book record. */
  function bookSections(index, page) {
    const book = index.book;
    const asOf = `Book record ${short(book.content_digest)} · ${book.version} · cutoff ${day(page.cutoff)}.`;
    const accounts = book.accounts.map((a) => {
      const nodes = book.nodes.filter((n) => n.account_id === a.id).map((n) => n.id);
      const contracts = book.contracts.filter((c) => c.account_id === a.id).map((c) => c.id);
      return `<tr data-row="${esc(a.id)}">` + cell(a.id, 'mono') + cell(a.name) + regionCell(a.region, a.region_code)
        + cell(nodes.join(', '), 'mono wrap') + cell(contracts.join(', '), 'mono wrap') + '</tr>';
    });
    const nodes = book.nodes.map((n) => {
      const profile = book.profiles.find((p) => p.node_id === n.id) || {};
      return `<tr data-row="${esc(n.id)}">` + cell(n.id, 'mono') + cell(n.account_id, 'mono') + regionCell(n.region, n.region_code)
        + cell(n.region_code, 'mono') + num(mw(profile.peak_mw)) + '</tr>';
    });
    const runs = (index.contract_hours || {}).runs || {};
    const contracts = book.contracts.map((c) => {
      const hours = (runs[c.id] || []).map(([first, last]) => `${clock(first)} to ${clock(last)}`).join(', ');
      return `<tr data-row="${esc(c.id)}">` + cell(c.id, 'mono') + cell(c.account_id, 'mono') + cell(c.node_id, 'mono')
        + cell(KIND_WORDS[c.kind] || c.kind) + num(fig(c.mw, 1)) + num(fig(c.price_php_mwh, 0))
        + cell(hours, 'wrap') + cell(day(c.term_start), 'mono') + cell(day(c.term_end), 'mono') + '</tr>';
    });
    return sectionHtml('accounts', 'Accounts',
      [`At the cutoff of ${day(page.cutoff)}, ${book.version} holds ${book.counts.accounts} accounts in `
        + `${book.regions.map((r) => r.name).slice(0, -1).join(', ')} and ${book.regions.map((r) => r.name).slice(-1)}.`],
      asOf,
      table('accounts', ['Account', 'Name', 'Region', 'Load nodes', 'Contracts'], accounts, true,
        ['bk-c-id', 'w-lg', 'bk-c-region', '', '']))
      + sectionHtml('nodes', 'Load nodes',
        [`Each of the ${book.counts.nodes} load nodes belongs to one account and one region.`],
        asOf,
        table('nodes', ['Node', 'Account', 'Region', 'Code', ['Peak', 'MW']], nodes, true,
          ['bk-c-id', 'bk-c-id', 'bk-c-region', 'w-sm', '']))
      + sectionHtml('contracts', 'Contracts',
        [`The ${book.counts.contracts} contracts cover their nodes in the clock hours of each run.`],
        asOf,
        table('contracts', ['Contract', 'Account', 'Node', 'Kind', ['Volume', 'MW'], ['Price', 'PHP/MWh'],
          'Clock hours', 'Term start', 'Term end'], contracts, true,
          ['bk-c-id', 'bk-c-id', 'bk-c-id', 'w-md', 'w-sm', 'w-num', '', 'w-time', 'w-time']));
  }

  /* The exposure heat: one row per node, one column per clock hour, shaded by the baked step. */
  function heatSection(page) {
    const record = page.exposure;
    const heat = page.heat;
    const when = `${day(record.window.day)}, ${clock(record.window.start_hour)} to ${clock(record.window.end_hour)} Manila`;
    const hours = (heat.rows[0] || { hours: [] }).hours.map((t) => String(t).slice(11, 13));
    const rows = heat.rows.map((h) => {
      const cells = record.rows.filter((r) => r.node_id === h.node_id);
      return `<tr data-row="${esc(h.node_id)}">` + cell(h.node_id, 'mono') + cell(h.account_id, 'mono')
        + cells.map((r, place) => `<td class="num bk-heat bk-shade-${esc(h.shades[place])}" `
          + `data-shade="${esc(h.shades[place])}">${esc(mwh(r.uncovered_mwh))}</td>`).join('')
        + '</tr>';
    });
    const edges = heat.edges_mwh.map(mwh);
    return sectionHtml('heat', 'Exposure by hour', [
      `The table shows uncovered MWh per load node for each hour of ${day(record.window.day)}, Manila time.`,
      `Darker cells hold more. The four shade steps end at ${edges.slice(0, -1).join(', ')} and `
        + `${edges.slice(-1)} MWh.`,
    ], `Book record ${short(record.book.content_digest)} · cutoff ${day(record.cutoff)} · window ${when}.`,
    table('heat', ['Node', 'Account'].concat(hours.map((hour) => [hour, ''])), rows, false,
      ['bk-c-node', 'bk-c-acct'].concat(hours.map(() => ''))));
  }

  /* The exposure per account and the book's total, as the exposure record states them. */
  function accountExposureSection(page) {
    const record = page.exposure;
    const rows = record.accounts.map((a) => `<tr data-row="${esc(a.account_id)}">` + cell(a.account_id, 'mono')
      + regionCell(a.region, a.region_code) + num(mwh(a.demand_mwh)) + num(mwh(a.covered_mwh))
      + num(mwh(a.uncovered_mwh)) + '</tr>');
    rows.push('<tr class="bk-total" data-row="total" data-sort-fixed>' + cell('Book total') + cell('') + cell('') + cell('')
      + num(mwh(record.totals.uncovered_mwh)) + '</tr>');
    return sectionHtml('exposure', 'Exposure per account', [
      `On ${day(record.window.day)} the book leaves ${mwh(record.totals.uncovered_mwh)} MWh uncovered `
        + `over ${record.totals.rows} node hours.`,
    ], `Book record ${short(record.book.content_digest)} · cutoff ${day(record.cutoff)}.`,
    table('exposure', ['Account', 'Region', ['Demand', 'MWh'], ['Covered', 'MWh'], ['Uncovered', 'MWh']], rows, true,
      ['bk-c-id', 'bk-c-region', '', '', '']));
  }

  /* The impact band per account under each region's chosen vintage. The materiality line comes
     first, above the table, as the record states it; the page makes no verdict of its own. */
  function impactSection(page) {
    const line = page.materiality;
    const chosen = (page.selection.regions || []);
    const sayings = [
      `The materiality line for the cutoff of ${day(page.cutoff)} is ${php(line.threshold_php)} PHP, `
        + `${COMPARATOR_WORDS[line.comparator] || line.comparator}.`,
      LINE_SCOPE,
      line.rule,
    ];
    /* The vintage per region and the method fold under one disclosure, so the table follows the
       line and its rule closely. */
    const more = ['Vintages and method', line.basis, page.selection.rule];
    chosen.forEach((entry) => {
      more.push(entry.outlook_id
        ? `${entry.region} accounts use vintage ${entry.outlook_id}, record ${short(entry.outlook_digest)}, `
          + `issued ${utcWhen(entry.issued_at)}.`
        : noVintage(entry.region, day(page.cutoff)));
    });
    const method = (page.impacts[0] || {}).method || {};
    if (method.impact) more.push(method.impact);
    if (method.reference) more.push(method.reference);
    more.push(`The low, middle and high figures price the vintage's p10, middle and p90 levels on ${day(page.window.day)}.`);
    const rows = [];
    /* The vintage, its record and its issue instant are one per region: the sentences above name
       them, and the vintage cell carries the record and the impact record in its title. */
    page.impacts.forEach((record) => {
      const vintage = `<td class="mono trunc" title="${esc(`${record.vintage.outlook_id} · record ${short(record.vintage.outlook_digest)} · impact ${short(record.content_digest)} · issued ${utcWhen(record.as_of.vintage_issued_at)}`)}">${esc(record.vintage.outlook_id)}</td>`;
      record.accounts.forEach((a) => {
        rows.push(`<tr data-row="${esc(a.account_id)}">` + cell(a.account_id, 'mono') + regionCell(a.region, a.region_code)
          + num(mwh(a.uncovered_mwh)) + num(php(a.p10_php)) + num(php(a.p50_php))
          + num(php(a.p90_php)) + vintage + '</tr>');
      });
      const region = record.accounts.length ? record.accounts[0].region : record.vintage.series;
      rows.push(`<tr class="bk-total" data-row="total-${esc(record.vintage.series)}">` + cell(`${region} total`) + cell('')
        + num(mwh(record.totals.uncovered_mwh)) + num(php(record.totals.p10_php))
        + num(php(record.totals.p50_php)) + num(php(record.totals.p90_php))
        + vintage + '</tr>');
    });
    const caption = `Every peso figure is a method demonstration on the synthetic book. `
      + `Cutoff ${day(page.cutoff)} · window ${day(page.window.day)}.`;
    return sectionHtml('impact', 'Impact band', sayings, caption,
      table('impact', ['Account', 'Region', ['Uncovered', 'MWh'], ['Low', 'PHP'], ['Middle', 'PHP'], ['High', 'PHP'],
        'Vintage'], rows, false, ['bk-c-id', 'bk-c-region', '', '', '', '', 'w-lg']), more);
  }

  async function read(name) {
    try {
      const response = await fetch(DATA + name);
      return response.ok ? await response.json() : null;
    } catch (err) {
      return null;
    }
  }

  /* The anchor: what the book leaves uncovered on the window day, then each region's middle
     impact figure with its low and high, all fields of the exposure and impact records. */
  function statsHtml(page) {
    const record = page.exposure;
    const stat = (label, value, unit, meta, key) => `<div class="gn-stat${key ? ' gn-stat--key' : ''}">`
      + `<span class="gn-label">${esc(label)}</span>`
      + `<span class="gn-value gn-value--lg">${esc(value)}<span class="gn-unit">${esc(unit)}</span></span>`
      + `<span class="gn-meta">${esc(meta)}</span></div>`;
    return stat('Uncovered', mwh(record.totals.uncovered_mwh), 'MWh',
      `${record.totals.rows} node hours on ${day(record.window.day)}`, true)
      + page.impacts.map((impact) => {
        const region = impact.accounts.length ? impact.accounts[0].region : impact.vintage.series;
        return stat(`${region} impact, middle`, php(impact.totals.p50_php), 'PHP',
          `Low ${php(impact.totals.p10_php)} to high ${php(impact.totals.p90_php)}`);
      }).join('');
  }

  async function main() {
    const [index, page] = await Promise.all([read('book/index.json'), read('book/exposure.json')]);
    const empty = $('bk-empty');
    if (!index || !page || !index.book || !page.exposure || index.synthetic !== true || page.synthetic !== true) {
      empty.hidden = false;
      empty.textContent = EMPTY_LINE;
      $('bk-none').hidden = false;
      return;
    }
    const book = index.book;
    /* The header line carries the book record's own label. */
    $('bk-flag').textContent = book.label;
    $('bk-summary').textContent = `Book ${book.version}, record ${short(book.content_digest)}, holds `
      + `${book.counts.nodes} load nodes and ${book.counts.contracts} contracts at the cutoff of ${day(page.cutoff)}.`;
    $('bk-cutoff').textContent = `Cutoff ${day(page.cutoff)} · window ${day(page.window.day)}`;
    $('bk-stats').innerHTML = statsHtml(page);
    $('exposure').innerHTML = accountExposureSection(page) + heatSection(page);
    $('impact').innerHTML = impactSection(page);
    $('records').innerHTML = bookSections(index, page);
    $('bk-tabs').hidden = false;
    $('caption').append(' Every figure is a method demonstration on an invented book, never a business number.');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
})();
