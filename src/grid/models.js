/* Models page (MODELS-1). The four models are static: every sentence and figure is copied from
   a committed record, so the page fetches nothing and runs no model. This script composes the
   one-line status summary from the models' own status words, so the summary cannot drift from a
   model, and it leaves the page untouched when the models are absent.

   Platform polish (PP-B4): each model's detail is a tab (`.gn-tabs`, `#tab=model:<id>`). The
   shared layer (`ui.js`) drives tabs by delegation on the document; the small fallback below
   does the same job only while that layer is absent, so the comparison table's links always
   open the right model. */
(() => {
  'use strict';
  const cards = Array.from(document.querySelectorAll('.md-card'));
  const summary = document.getElementById('md-summary');
  if (!summary || cards.length !== 4) return;
  const parts = cards.map((card) => {
    const name = card.querySelector('h2');
    const word = card.querySelector('.md-status-word');
    if (!name || !word) return null;
    return `${name.textContent.trim()} ${word.textContent.trim().toLowerCase()}`;
  });
  if (parts.some((part) => part === null)) return;
  summary.textContent = `${parts.join(' · ')}.`;
  document.documentElement.setAttribute('data-models-ready', 'true');

  if (typeof window === 'undefined' || !document.addEventListener) return;
  const shared = () => Boolean(window.GNUI);
  const tabs = Array.from(document.querySelectorAll('.md-detail [role="tab"]'));
  if (!tabs.length) return;

  function select(id, focus) {
    const tab = tabs.find((item) => item.getAttribute('aria-controls') === id);
    if (!tab) return false;
    tabs.forEach((item) => {
      const on = item === tab;
      item.setAttribute('aria-selected', String(on));
      item.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(item.getAttribute('aria-controls'));
      if (panel) panel.hidden = !on;
    });
    if (focus) tab.focus();
    return true;
  }

  function fromHash(reveal) {
    const found = /(?:^#|&)tab=model:([a-z]+)/.exec(window.location.hash || '');
    if (!found || !select(found[1])) return;
    if (reveal) {
      const section = document.querySelector('.md-detail');
      if (section && section.scrollIntoView) section.scrollIntoView({block: 'start'});
    }
  }

  tabs.forEach((tab) => tab.addEventListener('click', () => {
    if (shared()) return;
    const id = tab.getAttribute('aria-controls');
    select(id);
    try { history.replaceState(history.state, '', '#tab=model:' + id); } catch (error) { /* no address */ }
  }));
  tabs[0].parentNode.addEventListener('keydown', (event) => {
    if (shared()) return;
    const at = tabs.indexOf(document.activeElement);
    if (at < 0) return;
    const to = {ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1}[event.key];
    if (to === undefined) return;
    event.preventDefault();
    select(tabs[(to + tabs.length) % tabs.length].getAttribute('aria-controls'), true);
  });
  /* A row of the comparison table opens its model: the row's link carries the tab address. The
     shared layer follows only site paths in `data-href`, so this page opens its own rows. */
  document.querySelectorAll('.md-compare tr[data-model]').forEach((row) => {
    row.addEventListener('click', (event) => {
      if (event.target.closest && event.target.closest('a')) return;
      window.location.hash = 'tab=model:' + row.getAttribute('data-model');
    });
  });
  window.addEventListener('hashchange', () => fromHash(true));
  fromHash(false);
})();
