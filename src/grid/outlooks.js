/* Outlooks page. Design file: the whole price-outlook archive as one surface (DESK-3).
   Reads one baked file and nothing else: `/grid-data/<stamp>/outlook/index.json`, the index
   `scripts/grid/build_data.py` writes in the same bake as the replay data. Every sentence is
   composed from the file's own fields — no clock, no value file, nothing derived; every time
   is the record's own instant with its date, in UTC; every figure cites the record it came
   from. One block per target: the plain answer and the chart, then its vintages newest first
   as a table with the chosen vintage's record beside it (the current one named in words), the
   baseline track record, and every record id and digest folded under "Show the records".
   The links to event pages are the index's own `events` entries: a vintage links an event
   only where that event's dependency walk claimed the vintage rests on its assumption. */
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
  const day = (t) => new Date(String(t).slice(0, 10) + 'T00:00:00Z')
    .toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  /* Every time is the record's own instant, with its date, in UTC — never a build instant. */
  const utcWhen = (t) => `${day(t)} ${hhmm(t)} UTC`;
  const shortHex = (value) => `${String(value).slice(0, 16)}…`;
  const shortDigest = (value) => `${String(value).slice(0, 8)}…`;
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  /* DESK-2's diff sentence, composed from the baked `changes` and the entry's own id, issue
     instant and `supersedes` and nothing else: every time is a record's own instant, every
     digest a record's own input or values digest, and the two facts the diff states by
     absence (the model version and the assumption set) are said in words. */
  function changesSentence(o) {
    const changes = o.changes || [];
    const parts = [];
    const cutoff = changes.find((c) => c.field === 'information_cutoff');
    if (cutoff) {
      parts.push(cutoff.from === cutoff.to
        ? `information cutoff unchanged at ${utcWhen(cutoff.from)}`
        : `information cutoff ${utcWhen(cutoff.from)} to ${utcWhen(cutoff.to)}`);
    }
    for (const c of changes.filter((x) => x.field === 'input')) {
      if (c.from && c.to) parts.push(`input ${c.name} ${shortDigest(c.from)} to ${shortDigest(c.to)}`);
      else if (c.to) parts.push(`input ${c.name} added ${shortDigest(c.to)}`);
      else parts.push(`input ${c.name} removed ${shortDigest(c.from)}`);
    }
    const values = changes.find((x) => x.field === 'values');
    if (values && values.from && values.to) {
      parts.push(`values ${shortDigest(values.from)} to ${shortDigest(values.to)}`);
    }
    const model = changes.find((c) => c.field === 'model_version');
    parts.push(model ? `model ${model.from} to ${model.to}` : 'same model');
    const assumptions = changes.find((c) => c.field === 'assumption_ids') || { added: [], removed: [] };
    const added = assumptions.added || [], removed = assumptions.removed || [];
    if (added.length || removed.length) {
      const said = [];
      if (added.length) said.push(`added ${added.join(', ')}`);
      if (removed.length) said.push(`removed ${removed.join(', ')}`);
      parts.push(`assumptions ${said.join(', ')}`);
    } else parts.push('same assumptions');
    for (const c of changes.filter((x) => x.field === 'horizon')) {
      parts.push(`horizon ${c.edge} ${utcWhen(c.from)} to ${utcWhen(c.to)}`);
    }
    return `${o.outlook_id} (issued ${utcWhen(o.issued_at)}) supersedes ${o.supersedes}: ${parts.join('; ')}.`;
  }

  /* ARCH-4's attribution, one sentence from the record's own fields: the statement in the
     author's words, the cause and its reference, the share when the record states one, the
     author, the attributed instant, the record's own provenance when it is synthetic, and the
     attribution record's own digest — the share is that record's figure, not the receipt's. */
  function attributionReference(a) {
    if (a.cause === 'belief') return `belief, assumption ${a.assumption_id}`;
    if (a.cause === 'signal') {
      return `signal, ${a.signal_ref.source} available ${utcWhen(a.signal_ref.available_at)}, `
        + `effective ${utcWhen(a.signal_ref.effective_at)}`;
    }
    return `method, ${a.method_ref}`;
  }
  function attributionSentence(a) {
    const share = a.share == null ? '' : `, share ${a.share} of the miss`;
    return `${a.statement} — ${attributionReference(a)}${share}; attributed by ${a.attributed_by} `
      + `at ${utcWhen(a.attributed_at)}${a.synthetic ? ' (synthetic)' : ''} · record `
      + `${shortHex(a.content_digest)}.`;
  }
  /* The receipt is named by its own fields, then its attributions grouped by cause: what the
     desk believed, what it missed, and which method was wrong are three readings, kept apart.
     A receipt whose shares sum above one carries the archive's own verify finding beside it. */
  function receiptHtml(r) {
    const groups = r.attributions || {};
    const causes = ['belief', 'signal', 'method'];
    return `<div class="ol-receipt">`
      + `<div class="ol-line">Receipt for final series <span class="mono">${esc(r.final_series_version)}</span>, `
      + `scored ${esc(utcWhen(r.scored_at))} · record <span class="mono">${esc(shortHex(r.receipt_digest))}</span></div>`
      + causes.filter((cause) => (groups[cause] || []).length).map((cause) => {
        const entries = groups[cause] || [];
        return `<div class="ol-cause"><b>${esc(cause)}</b> · ${esc(plural(entries.length, 'attribution'))}</div>`
          + entries.map((a) => `<div class="ol-attribution">${esc(attributionSentence(a))}</div>`).join('');
      }).join('')
      + (r.share_problem
        ? '<div class="ol-share-problem">The shares attributed to this receipt sum above one; '
          + 'the archive\'s verify reports SHARE_OVER_ONE.</div>'
        : '')
      + '</div>';
  }

  /* Copy rule 7: any synthetic record says so in the caption line, read from the shown
     records' own `synthetic` flags — never a standing the page asserts for them. */
  const CAPTION_REAL = 'The price-outlook archive is a recorded method run on pre-backfill exports (synthetic false); it makes no skill claim.';
  const CAPTION_SYNTHETIC = 'Every price outlook shown is a synthetic record (synthetic true), not a run on pre-backfill exports; no skill claim is made.';
  function provenanceSentence(shown) {
    const synthetic = shown.filter((o) => o.synthetic === true).length;
    if (!synthetic) return CAPTION_REAL;
    if (synthetic === shown.length) return CAPTION_SYNTHETIC;
    return `${synthetic} of ${shown.length} price outlooks shown are synthetic records (synthetic true); `
      + "the rest are the archive's recorded method run on pre-backfill exports (synthetic false). "
      + 'No skill claim is made.';
  }

  /* DESK-5: a register row's id links to its own row on the register page. An id the register
     does not carry is not a row there, so it stays plain text — no link to a row that does not
     exist. */
  /* COPY-1: a seat is not a person; the page says what the register means by it. */
  const ownerWords = (o) => (o === 'orchestrator seat' ? 'the project seat' : String(o || ''));
  function assumptionRow(item) {
    const facts = item.known
      ? `${item.family} · ${item.layer} · ${item.state} · ${ownerWords(item.owner)}`
      : 'not a register row';
    const id = item.known
      ? `<a class="mono" href="/register#${esc(item.assumption_id)}">${esc(item.assumption_id)}</a>`
      : `<span class="mono">${esc(item.assumption_id)}</span>`;
    return `<li>${id} <span class="unit">${esc(facts)}</span></li>`;
  }
  function inputRow(item) {
    return `<li><span class="mono">${esc(item.name)}</span> `
      + `<span class="unit mono" title="${esc(item.digest)}">${esc(shortHex(item.digest))}</span></li>`;
  }
  /* One vintage, as the record states it: the id and its issue instant and cutoff in the head
     line (the current vintage named in words, never a badge), the horizon and record digests,
     the diff against the previous vintage, the inputs and the register rows it rests on, its
     receipts with their attributions by cause, and the event pages the dependency walk claims
     it rests on. Every sentence carries the record's own time. */
  function vintageHtml(o, place, chosen) {
    const current = o.current === true ? 'current · ' : '';
    const sentence = o.supersedes && Array.isArray(o.changes)
      ? `<div class="ol-change">${esc(changesSentence(o))}</div>` : '';
    const assumptions = (o.assumptions || []).map(assumptionRow).join('');
    const receipts = (o.receipts || []).map(receiptHtml).join('');
    const events = (o.events || []).map((e) =>
      `<li><a href="/event/${encodeURIComponent(e.event_id)}">Event ${esc(e.event_id)}</a> rests on `
      + `<span class="mono">${esc(e.assumption_id)}</span>, as recorded at ${esc(utcWhen(o.issued_at))}.</li>`).join('');
    return `<li class="ol-vintage${o.current === true ? ' current' : ''}" data-v="${place}"${place === chosen ? '' : ' hidden'}>`
      + `<div class="ol-headline"><b>${esc(o.outlook_id)}</b> <span class="unit">${current}`
      + `issued ${esc(utcWhen(o.issued_at))} · cutoff ${esc(utcWhen(o.information_cutoff))}</span></div>`
      + '<div class="ol-line">'
      + `${esc(o.horizon.label)} horizon ${esc(utcWhen(o.horizon.start))} to ${esc(utcWhen(o.horizon.end))}`
      + ` · model <span class="mono">${esc(o.model_version)}</span></div>`
      + sentence
      + `<div class="ol-sub">Assumptions</div><ul class="ol-rows">${assumptions}</ul>`
      + (receipts ? `<div class="ol-sub">Receipts</div>${receipts}` : '')
      + (events ? `<div class="ol-sub">Events</div><ul class="ol-links">${events}</ul>` : '')
      + '</li>';
  }

  /* DESK-6: the target's baseline track record, one row per baseline per horizon from the
     baked `scorecard` block. Every figure is the block's own — copied from the scorecard as
     recorded, never recomputed and never ranked — and every row cites the scorecard's content
     digest as its as-of. The slice is named in words: the figures are market hours, and the
     administered-pricing hours are counted apart. An unavailable count is said in words with
     the record's own code. A target without the key draws no block (copy rule 4). */
  const scoreMetric = (value) => (value == null ? '—' : String(value));
  const whenDigest = (value) => `record ${shortHex(value)}`;
  function unavailableText(items) {
    if (!items || !items.length) return 'no origin unavailable';
    return items.map((item) => `${item.count} unavailable (${item.code})`).join(' · ');
  }
  function scoreRow(horizon, baseline) {
    const figures = [baseline.bias, baseline.mae, baseline.rmse,
      baseline.pinball_p10, baseline.pinball_p50, baseline.pinball_p90]
      .map((value) => `<td class="num">${esc(scoreMetric(value))}</td>`).join('');
    return `<tr><td class="trunc mono" title="${esc(baseline.name)}">${esc(baseline.name)}</td><td>${esc(horizon)}</td>`
      + `<td class="num">${esc(baseline.count)}</td>${figures}`
      + `<td class="wrap gn-meta">${esc(unavailableText(baseline.unavailable))}</td></tr>`;
  }
  function scorecardHtml(scorecard) {
    const digest = scorecard.content_digest;
    const inputs = (scorecard.inputs || []).map((item) =>
      `${esc(item.name)} <span class="mono">${esc(shortHex(item.digest))}</span>`).join(', ');
    return '<section class="gn-section ol-score"><h3>How the baselines have done</h3>'
      + (scorecard.horizons || []).map((horizon) => '<div class="ol-score-horizon">'
        + `<div class="ol-score-slice">${esc(horizon.horizon)} horizon · market hours; `
        + `administered-pricing hours counted apart: `
        + `${esc(plural(horizon.administered_count, 'origin'))} scored · `
        + `${esc(whenDigest(digest))}</div>`
        + '<div class="gn-table-wrap ol-score-wrap"><table class="gn-table gn-table--compact ol-score-table">'
        + '<colgroup><col class="ol-s-name"><col class="w-sm"><col class="w-sm"><col><col><col><col><col><col><col class="ol-s-unavail"></colgroup><thead><tr>'
        + '<th scope="col">Baseline</th><th scope="col">Horizon</th><th scope="col" class="num">Origins</th>'
        + '<th scope="col" class="num">Bias <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col" class="num">MAE <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col" class="num">RMSE <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col" class="num">Pinball p10 <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col" class="num">Pinball p50 <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col" class="num">Pinball p90 <span class="gn-unit">PHP/MWh</span></th>'
        + '<th scope="col">Unavailable</th></tr></thead><tbody>'
        + (horizon.baselines || []).map((baseline) =>
          scoreRow(horizon.horizon, baseline)).join('')
        + '</tbody></table></div></div>').join('')
      + `<div class="ol-score-inputs">scorecard inputs: ${inputs}</div></section>`;
  }

  /* OUTLOOK-7: the number in words. The values record BAKE-1 bakes states one point per hour
     and no month scalar, so the month's value is the mean of the hours the record holds — an
     arithmetic the page states in words beside the figure, never a claim the record makes. The
     band is the same mean of the three recorded levels, shown only when every hour carries one;
     a record with no band says so instead. Nothing here reads a clock, a value file or a price
     series: the hours are the baked record's own, and the values digest below the answer is its
     as-of. */
  const meanOf = (items, key) => items.reduce((sum, item) => sum + item[key], 0) / items.length;
  /* One decimal, half up, thousands grouped, so the page prints one figure one way in every
     browser: 4100 -> "4,100.0". */
  function phpText(value) {
    const rounded = Math.round(value * 10) / 10;
    const text = String(Math.abs(rounded));
    const point = text.indexOf('.');
    const whole = point < 0 ? text : text.slice(0, point);
    const fraction = point < 0 ? '0' : text.slice(point + 1);
    return `${rounded < 0 ? '-' : ''}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
      + `.${(fraction + '0').slice(0, 1)}`;
  }
  function monthlySummary(values) {
    const hours = values && Array.isArray(values.hours) ? values.hours : [];
    if (!hours.length) return null;
    const banded = hours.every((row) => row.p10 != null && row.p50 != null && row.p90 != null);
    return {
      month: values.billing_month,
      count: hours.length,
      value: meanOf(hours, 'value'),
      p10: banded ? meanOf(hours, 'p10') : null,
      p90: banded ? meanOf(hours, 'p90') : null,
    };
  }
  /* The plain answer, sentence by sentence, from the current vintage's own fields and its
     values record. Each sentence stays under twenty words and in the active voice; every figure
     is the record's own or the stated mean of it, and the as-of line below names the two record
     digests. Status words are never stronger than the record: `current` is the record's own
     flag, and a vintage with no receipt says it has not been scored. */
  function answerSentences(o, summary) {
    const out = [];
    if (!summary) {
      out.push(o.values
        ? 'The values record states no hour for this position, so the page shows no price.'
        : 'The build links no values record for this position, so the page shows no price.');
      return out;
    }
    /* The headline says what the figure is: the mean of the record's hourly values over the
       billing month, never a monthly figure the record does not hold (review round 1). */
    out.push(`The desk's current position for billing month ${summary.month} averages `
      + `${phpText(summary.value)} PHP/MWh over its ${plural(summary.count, 'hour')}.`);
    out.push(`The series is ${o.values.series_label}, from ${day(o.values.window_start_hour_local)} `
      + `to ${day(o.values.window_end_hour_local)} local time.`);
    out.push(summary.p10 == null
      ? 'The record carries no band for this vintage.'
      : `The mean of its hourly p10 and p90 levels runs from ${phpText(summary.p10)} to `
        + `${phpText(summary.p90)} PHP/MWh.`);
    out.push('It rests on the assumptions the record cites and on the inputs it names below.');
    out.push(`The desk issued it on ${utcWhen(o.issued_at)}.`);
    out.push(`Its information cutoff is ${utcWhen(o.information_cutoff)}.`);
    const receipts = o.receipts || [];
    if (!receipts.length) {
      out.push('The archive holds no receipt, so no month has scored it.');
    } else {
      const latest = receipts.map((r) => String(r.scored_at)).sort().slice(-1)[0];
      out.push(receipts.length === 1
        ? `The archive holds one receipt, scored ${utcWhen(latest)}.`
        : `The archive holds ${receipts.length} receipts. The latest is scored ${utcWhen(latest)}.`);
    }
    return out;
  }
  function answerHtml(target, newest, chart) {
    const summary = newest.values ? monthlySummary(newest.values) : null;
    const heading = summary ? `Billing month ${summary.month}`
      : `${target.horizon_label} horizon`;
    const asof = summary
      ? `Values record <span class="mono" title="${esc(newest.values.sha256)}">${esc(shortHex(newest.values.sha256))}</span>`
        + ` · outlook record <span class="mono" title="${esc(newest.content_digest)}">${esc(shortHex(newest.content_digest))}</span>.`
      : `Outlook record <span class="mono" title="${esc(newest.content_digest)}">${esc(shortHex(newest.content_digest))}</span>.`;
    /* The first sentence is the page's anchor (the month's figure); the chart sits beside the
       sentences on a wide screen. */
    return '<section class="ol-answer"><div class="ol-answer-words">'
      + `<h2 class="ol-answer-month">${esc(heading)}</h2>`
      + answerSentences(newest, summary).map((sentence) =>
        `<p class="ol-answer-text">${esc(sentence)}</p>`).join('')
      + `<p class="asof ol-answer-asof">${asof}</p>`
      + '</div>' + (chart || '') + '</section>';
  }
  /* OUTLOOK-7: one small chart of the vintages' values, drawn from the baked hours and nothing
     else. One point per vintage that carries a values record, in issued order, labelled
     directly with its mean, its issued date and its values record digest — the chart has no
     zero baseline and no unlabelled scale. A band, where the record holds one, is a whisker
     between the means of p10 and p90. The source line says what the points are. */
  function chartHtml(issuedOrder) {
    const plotted = issuedOrder.map((o) => {
      const summary = o.values ? monthlySummary(o.values) : null;
      return summary ? {o, summary} : null;
    }).filter(Boolean);
    if (!plotted.length) return '';
    /* The scale takes the band levels in, so a whisker never leaves the drawing area. */
    const values = plotted.map((point) => point.summary.value);
    plotted.forEach((point) => {
      if (point.summary.p10 != null) values.push(point.summary.p10, point.summary.p90);
    });
    const low = Math.min.apply(null, values);
    const high = Math.max.apply(null, values);
    const span = high > low ? high - low : Math.max(1, Math.abs(high) * 0.02);
    const floor = low - span * 0.3;
    const ceiling = high + span * 0.3;
    const top = 30, bottom = 96, left = 64, right = 416;
    const xOf = (place) => (plotted.length === 1 ? (left + right) / 2
      : left + (place * (right - left)) / (plotted.length - 1));
    const yOf = (value) => bottom - ((value - floor) / (ceiling - floor)) * (bottom - top);
    const month = plotted[0].summary.month;
    const described = plotted.map((point) =>
      `${phpText(point.summary.value)} PHP/MWh issued ${day(point.o.issued_at)}`).join(', ');
    const points = plotted.map((point, place) => {
      const x = xOf(place).toFixed(1);
      const y = yOf(point.summary.value);
      /* The first and last labels anchor inward, so a chart label is never clipped at an edge;
         the middle labels stay centred on their point. */
      const anchor = plotted.length === 1 || (place > 0 && place < plotted.length - 1)
        ? 'middle' : (place === 0 ? 'start' : 'end');
      const band = point.summary.p10 == null ? ''
        : `<line class="ol-chart-band" x1="${x}" x2="${x}" `
          + `y1="${yOf(point.summary.p90).toFixed(1)}" y2="${yOf(point.summary.p10).toFixed(1)}"></line>`;
      /* A recorded band is labelled directly beside its whisker, so the chart says the band in
         words as well as drawing it. */
      const bandLabel = point.summary.p10 == null ? ''
        : `<text class="ol-chart-bandtext" text-anchor="${anchor}" x="${x}" y="108">`
          + `${esc(`mean p10 ${phpText(point.summary.p10)} to mean p90 ${phpText(point.summary.p90)}`)}</text>`;
      return '<g class="ol-chart-point">' + band
        + `<circle cx="${x}" cy="${y.toFixed(1)}" r="3.5"></circle>`
        + `<text class="ol-chart-value" text-anchor="${anchor}" x="${x}" y="${(y - 9).toFixed(1)}">`
        + `${esc(phpText(point.summary.value))}</text>`
        + bandLabel
        + `<text class="ol-chart-date" text-anchor="${anchor}" x="${x}" y="122">`
        + `${esc(day(point.o.issued_at))}</text>`
        + `<text class="ol-chart-record" text-anchor="${anchor}" x="${x}" y="136">`
        + `${esc('record ' + shortHex(point.o.values.sha256))}</text>`
        + '</g>';
    }).join('');
    return '<figure class="ol-chart">'
      + `<svg viewBox="0 0 480 150" role="img" aria-label="${esc(`Vintage values for billing month ${month}: ${described}.`)}">`
      + `<title>${esc(`Vintage values, billing month ${month}`)}</title>`
      + '<text class="ol-chart-unit" x="8" y="14">PHP/MWh</text>'
      + points
      + '</svg>'
      + '<figcaption class="ol-chart-source">Chart values are the mean of the hours each values record holds.</figcaption>'
      + '</figure>';
  }

  /* The vintages of one target as a dense table, newest first: id, issue instant, cutoff, the
     mean of the hours its values record holds (the page's own stated mean, as in the chart), the
     band of p10 and p90 means where every hour carries one, its receipts and its standing in the
     record's own words (the record's `current` flag, or the later vintage that supersedes it).
     A row picks the vintage the detail beside the table shows. */
  function vintagesTable(vintages, chosen) {
    const supersededBy = (o) => vintages.find((v) => v.supersedes === o.outlook_id);
    const rows = vintages.map((o, place) => {
      const summary = o.values ? monthlySummary(o.values) : null;
      const later = supersededBy(o);
      const standing = o.current === true ? '<td><span class="ol-standing">current</span></td>'
        : later ? `<td class="trunc gn-meta" title="superseded by ${esc(later.outlook_id)}">superseded</td>` : '<td><span class="gn-meta">–</span></td>';
      const band = summary && summary.p10 != null ? `, band ${phpText(summary.p10)} to ${phpText(summary.p90)}` : ', no band';
      const clock = (t) => `${day(t)} ${hhmm(t)}`;
      return `<tr data-v="${place}"${place === chosen ? ' class="is-selected" aria-selected="true"' : ' aria-selected="false"'}>`
        + `<td><button type="button" class="ol-pick mono" data-v="${place}" aria-pressed="${place === chosen}" aria-label="Show vintage ${esc(o.outlook_id)}">${esc(o.outlook_id)}</button></td>`
        + `<td class="mono" data-value="${esc(o.issued_at)}" title="${esc(utcWhen(o.issued_at))}">${esc(clock(o.issued_at))}</td>`
        + `<td class="mono" data-value="${esc(o.information_cutoff)}" title="${esc(utcWhen(o.information_cutoff))}">${esc(clock(o.information_cutoff))}</td>`
        + (summary ? `<td class="num" title="${esc(`Mean ${phpText(summary.value)}${band}`)}">${esc(phpText(summary.value))}</td>` : '<td class="num"><span class="gn-meta">–</span></td>')
        + `<td class="num">${(o.receipts || []).length}</td>`
        + `${standing}</tr>`;
    }).join('');
    return '<div class="gn-table-wrap"><table class="gn-table gn-table--compact ol-vtable" data-sortable>'
      + '<colgroup><col class="ol-c-id"><col class="ol-c-time"><col class="ol-c-time"><col class="ol-c-mean"><col class="ol-c-n"><col class="ol-c-standing"></colgroup>'
      + '<thead><tr><th scope="col" data-sort="text">Vintage</th><th scope="col" data-sort="time">Issued <span class="gn-unit">UTC</span></th><th scope="col" data-sort="time">Cutoff <span class="gn-unit">UTC</span></th>'
      + '<th scope="col" class="num" data-sort="num" title="The mean of the hours its values record holds, PHP/MWh">Mean <span class="gn-unit">PHP/MWh</span></th>'
      + '<th scope="col" class="num" data-sort="num">Receipts</th><th scope="col">Standing</th></tr></thead>'
      + `<tbody>${rows}</tbody></table></div>`;
  }

  /* The record fold: the target's series, then one line per vintage with its record digest, its
     values digest, its model and its inputs by name and digest. */
  function recordsHtml(target, vintages) {
    const newest = vintages[0] || {};
    const series = target.target_series_ref || {};
    return '<details class="gn-disclosure ol-records"><summary>Show the records</summary>'
      + `<p class="ol-series"><span class="mono">${esc(series.table)} · ${esc(series.column)} · ${esc(series.version)}</span></p>`
      + `<p class="asof">${esc(target.horizon_label)} horizon · ${esc(plural(vintages.length, 'vintage'))}`
      + ` · newest issued ${esc(utcWhen(newest.issued_at))}`
      + ` · record <span class="mono">${esc(shortHex(newest.content_digest))}</span></p>`
      + '<ul class="ol-record-list">' + vintages.map((o) => `<li><b class="mono">${esc(o.outlook_id)}</b>`
        + ` · record <span class="mono" title="${esc(o.content_digest)}">${esc(shortHex(o.content_digest))}</span>`
        + ` · values <span class="mono" title="${esc(o.values_sha256)}">${esc(shortHex(o.values_sha256))}</span>`
        + ` · model <span class="mono">${esc(o.model_version)}</span>`
        + `<ul class="ol-rows">${(o.inputs || []).map(inputRow).join('')}</ul></li>`).join('') + '</ul>'
      + '</details>';
  }

  /* One block per target. OUTLOOK-7: it opens with the plain answer, the chart of the
     vintages' values; the vintages follow as a table, newest first, with the chosen vintage's
     record beside it; DESK-6's baseline track record comes next; the target's series and every
     record id and digest fold under "Show the records". */
  function targetHtml(target, index) {
    const vintages = (target.vintages || []).slice().reverse();
    const newest = vintages[0] || {};
    const chosen = Math.max(0, vintages.findIndex((o) => o.current === true));
    return `<section class="gn-section ol-target" data-target="${index}">`
      + answerHtml(target, newest, chartHtml(vintages.slice().reverse()))
      + '<div class="gn-grid gn-grid--main-side ol-vintage-grid">'
      + `<section class="ol-vintage-list"><header class="gn-section-head"><h3>Vintages</h3><span class="gn-section-meta">${esc(plural(vintages.length, 'vintage'))}, newest first</span></header>`
      + vintagesTable(vintages, chosen) + '</section>'
      + `<aside class="gn-card ol-detail" aria-label="The chosen vintage" aria-live="polite"><ol class="ol-vintages">${vintages.map((o, place) => vintageHtml(o, place, chosen)).join('')}</ol></aside>`
      + '</div>'
      + (target.scorecard ? scorecardHtml(target.scorecard) : '')
      + recordsHtml(target, vintages)
      + '</section>';
  }

  /* A row of the vintages table shows that vintage's record in the panel beside it. */
  function pick(block, place) {
    block.querySelectorAll('.ol-vtable tbody tr').forEach((row) => {
      const on = row.dataset.v === place;
      row.classList.toggle('is-selected', on);
      row.setAttribute('aria-selected', String(on));
      row.querySelector('.ol-pick').setAttribute('aria-pressed', String(on));
    });
    block.querySelectorAll('.ol-vintage').forEach((item) => { item.hidden = item.dataset.v !== place; });
  }

  function showEmpty(line) {
    const empty = $('ol-empty');
    empty.hidden = false;
    empty.textContent = line;
    $('ol-none').hidden = false;
  }

  async function main() {
    const summary = $('ol-summary');
    let data = null;
    try {
      const response = await fetch(DATA + 'outlook/index.json');
      if (response.ok) data = await response.json();
    } catch (err) {
      data = null;
    }
    if (!data) {
      showEmpty('This build could not read its outlook index, so the page shows no issued outlook.');
      return;
    }
    const register = data.register || {};
    const archive = data.archive || {};
    const targets = Array.isArray(data.targets) ? data.targets : [];
    /* Copy rule 4: a feature that is not connected is not shown. A bake with no archive (or an
       archive with no issued outlook) draws the one honest empty state and no block. */
    if (data.available !== true || !targets.length) {
      showEmpty('This build carries no outlook archive, so there is no issued outlook to show.');
      return;
    }
    const shown = targets.flatMap((target) => target.vintages || []);
    if (!shown.length) {
      showEmpty('The archive in this build holds no issued outlook yet.');
      return;
    }
    const newest = shown.reduce((best, o) => (String(o.issued_at) > String(best.issued_at) ? o : best));
    const counts = archive.verify || {};
    const counted = counts.outlooks != null;
    const total = counted ? counts.outlooks : shown.length;
    /* The count is the archive's own verify() answer, and the sentence says so, so the
       register revision beside it is not read as the count's source. A file that lost the
       counts says instead that the index lists the records it carries. */
    summary.textContent = (counted
      ? `The archive's verify counts ${plural(total, 'issued outlook')} in `
      : `The archive lists ${plural(total, 'issued outlook')} in `)
      + `${plural(targets.length, 'target')}, newest issued ${utcWhen(newest.issued_at)} · register `
      + `version ${shortHex(register.revision)} (${register.revision_basis === 'git blob id' ? 'its file id' : register.revision_basis}).`;
    $('targets').innerHTML = targets.map(targetHtml).join('');
    $('targets').addEventListener('click', (event) => {
      const row = event.target.closest('.ol-vtable tbody tr');
      if (!row || event.target.closest('a')) return;
      pick(row.closest('.ol-target'), row.dataset.v);
    });
    /* The caption line holds every disclaimer; the provenance is the shown records' own. */
    $('caption').textContent += ' · ' + provenanceSentence(shown);
    /* DESK-6: the baseline track record's own reading, in the same caption line (copy rule 2):
       the figures are the scorecard's, copied as recorded, and they make no skill claim. */
    const scored = targets.filter((target) => target.scorecard);
    if (scored.length) {
      $('caption').textContent += ' · The baseline figures are the scorecard record '
        + `${shortHex(scored[0].scorecard.content_digest)}'s own, copied as recorded; `
        + 'they rank no baseline and make no skill claim.';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
})();
