// The /work page's one behaviour: the worker filter over the step table. Every row names the
// worker that did the step, so the segments show all rows or the rows of one worker. The filter
// lives in the address (`?worker=code`), so a filtered view can be shared, and the count beside
// it says how many steps show. The page's facts are in the markup and stay readable without
// this file; no fetch, clock or storage.
(() => {
  'use strict';
  const buttons = Array.from(document.querySelectorAll('.wk-filter button[data-worker]'));
  const rows = Array.from(document.querySelectorAll('.wk-steps tbody tr[data-worker]'));
  const count = document.getElementById('wk-count');
  if (!buttons.length || !rows.length) return;
  const known = new Set(buttons.map((button) => button.dataset.worker));
  const show = (worker, write) => {
    buttons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.worker === worker));
    });
    rows.forEach((row) => {
      row.hidden = worker !== 'all' && row.dataset.worker !== worker;
    });
    if (count) count.textContent = rows.filter((row) => !row.hidden).length + ' of ' + rows.length + ' steps';
    if (!write) return;
    try {
      const url = new URL(window.location.href);
      if (worker === 'all') url.searchParams.delete('worker'); else url.searchParams.set('worker', worker);
      history.replaceState(history.state, '', url.pathname + url.search + url.hash);
    } catch (error) { /* the filter still works without an address */ }
  };
  buttons.forEach((button) => {
    button.addEventListener('click', () => show(button.dataset.worker, true));
  });
  let start = 'all';
  try { start = new URLSearchParams(window.location.search).get('worker') || 'all'; } catch (error) { start = 'all'; }
  if (known.has(start) && start !== 'all') show(start, false);
})();
