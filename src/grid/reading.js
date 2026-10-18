/* InGRID reading pages (platform polish PP-B4): the contents rail and the reading progress
   of the long pages (the paper, the project map). Declarative: it reads data attributes only.

     <nav data-toc> … <a href="#section-id">…</a> … </nav>
         The link of the section in view gets aria-current="location"; the rail keeps it in sight.
     <div data-read-progress hidden><span></span></div>
         A hairline under the bar that fills as the reader moves through [data-read-target]
         (or the whole page). It stays hidden without this script.

   Without the script the rail is plain anchor links and no progress shows. No library, no
   network, no storage; the only writes are attributes and one CSSOM transform. */
(() => {
  'use strict';
  const rails = Array.from(document.querySelectorAll('[data-toc]'));
  const bar = document.querySelector('[data-read-progress]');
  const fill = bar ? bar.firstElementChild : null;
  const target = document.querySelector('[data-read-target]');
  if (!rails.length && !fill) return;

  /* The fixed bar's height: the shell measures it into --bar-h (or --gn-bar-h). */
  function offset() {
    const style = getComputedStyle(document.documentElement);
    const value = parseFloat(style.getPropertyValue('--bar-h')) || parseFloat(style.getPropertyValue('--gn-bar-h')) || 0;
    return value + 24;
  }

  const entries = rails.map((rail) => {
    const links = Array.from(rail.querySelectorAll('a[href^="#"]'));
    const items = links.map((link) => {
      let id = link.getAttribute('href').slice(1);
      try { id = decodeURIComponent(id); } catch (error) { /* keep it as written */ }
      return {link, section: document.getElementById(id)};
    }).filter((item) => item.section);
    return {rail, items, current: null};
  }).filter((entry) => entry.items.length);

  function mark(entry, item) {
    if (entry.current === item) return;
    if (entry.current) entry.current.link.removeAttribute('aria-current');
    entry.current = item;
    if (!item) return;
    item.link.setAttribute('aria-current', 'location');
    /* Keep the current link inside the rail's own scroll box, without moving the page. */
    const rail = entry.rail;
    if (rail.scrollHeight > rail.clientHeight) {
      const top = item.link.offsetTop - rail.offsetTop;
      if (top < rail.scrollTop + 24 || top > rail.scrollTop + rail.clientHeight - 48) {
        rail.scrollTop = Math.max(0, top - rail.clientHeight / 3);
      }
    }
  }

  let queued = false;
  function update() {
    queued = false;
    const line = offset();
    /* While the shell holds the page hidden (its sign-in gate), nothing has a box yet: wait. */
    const box = (target || document.body).getBoundingClientRect();
    if (!box.height) return;
    for (const entry of entries) {
      let found = null;
      for (const item of entry.items) {
        if (item.section.getBoundingClientRect().top - line <= 1) found = item; else break;
      }
      /* At the very end of the page the last section counts as read, even if it is short. */
      if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
        found = entry.items[entry.items.length - 1];
      }
      mark(entry, found);
    }
    if (fill) {
      const span = Math.max(1, box.height - window.innerHeight + line);
      const done = Math.min(1, Math.max(0, (line - box.top) / span));
      fill.style.transform = 'scaleX(' + done.toFixed(4) + ')';
    }
  }
  function queue() {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(update);
  }

  if (bar) bar.hidden = false;
  window.addEventListener('scroll', queue, {passive: true});
  window.addEventListener('resize', queue);
  window.addEventListener('hashchange', queue);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(queue);
  /* The page's height changes as the shell reveals it and as late parts land: measure again. */
  if (typeof ResizeObserver === 'function') new ResizeObserver(queue).observe(target || document.body);
  update();
})();
