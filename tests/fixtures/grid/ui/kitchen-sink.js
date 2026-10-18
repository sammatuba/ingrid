/* The reference page's own script: the filter bar wired through GNUI.filters, filtering the
   table's rows, and badges made by GNUI.badge. Tests and dev only. */
(() => {
  'use strict';
  window.GNUI.ready.then((UI) => {
    const table = document.getElementById('ks-table');
    const rows = Array.from(table.tBodies[0].rows).filter((tr) => !tr.classList.contains('gn-row-detail'));
    const meta = new Map(rows.map((tr) => [tr, {
      grid: tr.dataset.href.includes('08PEDC') || tr.dataset.href.includes('06CEBU') ? 'CVIS' : 'CLUZ',
      kind: (tr.querySelector('.gn-badge') || {}).textContent === 'Trip' ? 'trip' : (tr.querySelector('.gn-badge') || {}).textContent === 'Derate' ? 'derate' : 'other',
      sev: (tr.querySelector('.gn-badge--alert') ? 'alert' : tr.querySelector('.gn-badge--warning') ? 'warning' : 'info'),
    }]));
    const apply = (state) => {
      let shown = 0;
      rows.forEach((tr) => {
        const m = meta.get(tr);
        const ok = (state.grid === 'all' || m.grid === state.grid) && (state.kind === 'all' || m.kind === state.kind)
          && (state.sev === 'all' || m.sev === state.sev)
          && (!state.q || tr.textContent.toLowerCase().includes(state.q.toLowerCase()));
        tr.hidden = !ok;
        if (ok) shown += 1;
      });
      ctl.count(shown, rows.length);
    };
    const ctl = UI.filters(document.getElementById('ks-filters'), {defaults: {grid: 'all', kind: 'all', sev: 'all', q: ''}, onChange: apply});
    apply(ctl.get());
    const box = document.getElementById('ks-badges-js');
    ['trip', 'red', 'yellow', 'mld', 'derate', 'online', 'notice', 'extreme', 'high', 'medium', 'low'].forEach((k) => {
      box.append(UI.badge(k), document.createTextNode(' '));
    });
    window.ksFilters = ctl;
  });
})();
