# `tests/fixtures/grid/page/` — the grid page's synthetic replay day

Everything here is synthetic and deterministic: one day of five-minute intervals for three
regions, seven sites, two HVDC links, four operator messages and one event, all computed from
the formulas in [build.py](build.py). No real WESM row, plant, coordinate, operator message or
case fact appears here, and nothing is read from the company copy. The shapes are the ones
`src/grid/grid.js` reads and `scripts/grid/build_data.py` (GRID-1) writes.

| Path | What it is |
|---|---|
| `build.py` | The formulas and the writer. `--check` rebuilds in memory and compares with the committed bytes; `tests/test_grid_page.py` runs it that way, so the fixture cannot drift from its own definition. The last two files of `data/` are composed by the real composer, `scripts/grid/briefs.py` (ATG-5), over the seven the formulas write. |
| `data/` | Nine files: `regions.json`, `hvdc.json`, `nodes-2026-09-21.json`, `advisories.json`, `sites.json`, `events.json`, `ph.geojson`, and ATG-5's `briefs.json` and `findings.json` composed from those seven. 5 of 7 sites are located; 2 are `p: "placeholder"` with null coordinates. The Visayas price holds ₱32,000/MWh for four intervals from 13:40. |
| `render.mjs` | Runs the page's own script (`src/grid/grid.js`) against a data directory under a small DOM shim and prints one JSON report of what it rendered and which replay URLs it asked for. Offline, no browser, no library; the shim throws on any DOM method it does not implement, so a gap is a failure rather than a silent pass. It is an approximation of a browser: it proves the script runs and fills the page at a viewport width, not that the layout looks right. With `--stamp <16 hex>` the shim's page carries that build stamp in `meta#nowcast-build`, so the report shows the versioned replay URLs the application's page produces. With `--hold-node` (PERF-4) the node file's answer is kept in flight until the harness has read the page, and the report carries `initial` (before any data), `stage1` (what the six small files drew, tooltip included) and the finished page; `--node-fail` refuses the node file outright, `--stage-interact` presses the Luzon button and steps the replay forward inside stage 1, and `--no-briefs` (ATG-8) refuses the two composed files. The panel module, `src/grid/briefs.js`, needs a richer DOM than this shim gives, so the shim stands in for it: `window.GridBriefs.mount` is a recorder and the report's `briefs` block carries the container, the payload sizes, the callbacks the page passed and every `setGrid`/`setClock` its render made. The panel's own drawing is checked by `tests/fixtures/grid/briefs/panel-harness.mjs`. |
| `browser.mjs` | The real check: serves `src/grid` and a data directory over loopback under the application's own header policy (content security policy included), loads `/` in headless Chromium, and reports console errors, page errors, failed requests, what the page rendered, where it reaches past the viewport, the policy it was served with and every URL the browser asked for. A page that scrolls sideways fails it. Exit 3 means no browser was given. With `--stamp` (the value `src/api.build_stamp` derives for the data directory) it serves the page with the stamp written in and answers the versioned asset and data URLs, exactly as the image does; with `--hold-node` (PERF-4) it holds the node file's answer until the browser has rendered the page the six small files draw, and reports that state as `stage1` beside `rendered`. PERF-6: `--play <ticks>` plays the dashboard clock and reports the alert-inbox requests made while it played and after it stopped (`play`); `--cross-days <d1>,<d2>` moves the clock to the other day and back twice and reports the node and day files asked for (`cross`); `--probe` asks the shell's own readers (`GNShell.inbox`, `GNShell.dayFile`) with a refused inbox time and a day file that fails once (`probe`). `--show-briefs` serves `dashboard.css` without the selector that folds the briefing panel away, so the page reads `briefs.json` and `findings.json` and draws the panel (the dashboard as it ships reads neither). Every report carries `inbox` (each inbox request with its query) and `requested` (every request the page made, including the ones the browser's cache answered). The two-day replay bake those runs use is built by `two_day_bake` in `tests/test_grid_page.py`. |

```sh
# the offline shim (any seat with node), with and without a build stamp
node tests/fixtures/grid/page/render.mjs --root . --data tests/fixtures/grid/page/data --width 390
node tests/fixtures/grid/page/render.mjs --root . --data tests/fixtures/grid/page/data \
  --width 390 --stamp 0123456789abcdef

# the staged draw (PERF-4): the node file held, so `stage1` is the page the small files drew
node tests/fixtures/grid/page/render.mjs --root . --data tests/fixtures/grid/page/data \
  --width 390 --hold-node

# ATG-8: the two composed files refused, the way a bake without them answers — the page draws
# and the panel's mount point stays hidden
node tests/fixtures/grid/page/render.mjs --root . --data tests/fixtures/grid/page/data \
  --width 390 --no-briefs

# the real browser check (a machine with a Chromium and playwright-core)
node tests/fixtures/grid/page/browser.mjs --root . --data tests/fixtures/grid/page/data \
  --width 390 --stamp 0123456789abcdef \
  --playwright <playwright-core/index.mjs> --chromium <chrome executable>
```

PERF-1: `src/grid/index.html` carries `__NOWCAST_STAMP__` where the application writes its
build stamp — the script and stylesheet URLs, and the `nowcast-build` meta element `grid.js`
reads to build its replay URLs (the stylesheet's own font URLs are relative, so they resolve
under the same prefix). A harness that serves the source page without substituting the token
gets a page whose script reads the **unversioned** `/grid-data/...` names: that is the
`render.mjs` default, and those names are served with `no-store`. `tests/test_cache_headers.py`
runs both halves of both scripts, and `tests/test_grid_page.py::BrowserPage` runs the real
browser against the stamped page and checks that every asset and replay request the browser
made carries the stamp.

`tests/test_grid_page.py` runs the first itself and runs the second when it finds a browser:
`GRID_BROWSER_CHROMIUM` and `GRID_BROWSER_PLAYWRIGHT` win when set, and without them the
machine-local pair is tried — the newest Chromium under `~/.cache/ms-playwright` and
`playwright-core` linked at `.local/deckcheck/node_modules/playwright-core/index.mjs`:

```sh
GRID_BROWSER_CHROMIUM=<chrome> GRID_BROWSER_PLAYWRIGHT=<playwright-core/index.mjs> \
  /usr/bin/python3 -m unittest tests.test_grid_page -v
```

The browser section asserts no console error, no page error, no failed request, no sideways
overflow and a scrub control inside the viewport at 390 and 1280. Its console evidence is
only as good as the headers it serves, so the harness restates the three cache classes and
the test compares the report's policy, path by path, with the answer the application's own
route produces for each reported path — a policy drift on either side fails there. On a
machine with neither browser location the whole section skips and says so.

The real WESM snapshot is not here and never will be: GRID-1 bakes it from the company copy
into `build/grid-data/` (git-ignored), the Dockerfile copies it into the image, and the page
reads it at `/grid-data/`. This fixture exists so the routing, the page and the copy rules are
testable offline.

The browser harness serves the InGRID icons and manifest at the root (`/favicon.ico`,
`/favicon.svg`, `/site.webmanifest` and the PNG icons) from `src/grid`, as `src/api`'s own routes
do (`BRAND_ROOT_FILES`, revalidating). Every page links them in its head, so a 404 there would be
a console error on an otherwise clean page.

PERF-5: `grid.js` ends its first render with one fire-and-forget `GET /health` — scheduled after
the first paint (`requestAnimationFrame` then a timer), never awaited, its rejection caught — so
a cold Cloud Run instance starts warming while the judge reads the drawn page. Both harnesses
model that call: `render.mjs` records it on its own `health` list (the `fetched` list stays
exactly the seven replay files), supplies `setTimeout` and `requestAnimationFrame` to the shim,
and takes `--health-fail` to run the page the way a refused check leaves it (still drawn, still
no error); `browser.mjs` answers `/health` with the application's own `no-store` policy and
waits for the request before it closes the browser, so the console, failure and response lists
are read after the warm-up settled. `tests/test_grid_page.py::RenderedPage` and `::BrowserPage`
check one call at both widths, and `tests/test_cache_headers.py::Scripts` checks it in the
stamped and the unversioned runs alike.

PERF-4: the page draws in two stages, and `--hold-node` in either harness is how that is read
rather than assumed. The six small files draw the brief, the figures table, the feed, the review
list, the chart and the map outline — its land, its sites and its links — and the node file,
asked for at the same moment, adds the one thing only it carries: the site layer, the prices the
dots are coloured by. While it is in flight the map carries `pricing` (the CSS in `grid.css`
gives it a "Site prices loading…" chip) and every dot is drawn at the unknown value; the tooltip
says `—` for the price and the MW, never a figure, and the page re-writes an open tooltip when
the values land. `tests/test_grid_page.py::StagedDraw` compares stage 1 with a **separate**
finished run (so the interim screen is shown equal to the final one, not to itself), pins the
site layer as the only thing the node file changes, and covers a node file that cannot be read
(the outline stays drawn and the caption names the missing prices) and a user who switches grid
and steps the replay inside stage 1. `::BrowserPage` runs the same held capture in Chromium at
390 and 1280 and asserts no console, page or request error while the node file is still arriving.

SHELL-1 (merge follow-up, 2026-10-18): the merged desk (ericka-desk) changed what `browser.mjs`
serves and reads, and the harness follows the application:

- The grid pages (`/`, `/event/<id>`) carry the sign-in policy (`SIGN_IN_POLICY`, decision D1);
  `/desk`, the data, the design files and the API answers keep the default policy. The event page's
  policy is reported and compared with the application's answer too.
- The shared shell's reads and the dashboard's new ones are answered empty where this fixture bakes
  no file of that name, as the book and explainer harnesses do: `replay.json` with no span (the shell
  keeps its own 21–29 Sep window), `outages.json` well formed with no record,
  `/api/alerts/client-config` with `{}` (sign-in not configured) and `/api/alerts/inbox` with no alert.
- `rendered.clipped` lists the containers that clip or scroll sideways and hold content past the
  viewport (the bar's ticker; on a phone its section list and the map's pill toolbar), which `wide`
  leaves out; `overflow`, the document's own sideways scroll, stays the hard check. `rendered.shown`
  says which blocks the reader sees (the dashboard folds the brief, the grids table and the chart
  with its day path), `scrub.shown` whether the slider is drawn (UX-3: the replay sits inside the
  map on its own row, so it is drawn at every width), `steps` the boxes of the step and play buttons
  and the clock, and `step` is one real press of "forward five minutes".
- The map's popover (`tip`) is the list of the assets at the place under the pointer, each with its
  price at the clock in a `gt-price` cell; a click on a place of several assets pins a copy of it
  (`.gmap-pin`) whose rows link to each plant page.
- In `--interact`, a step on a folded element is the element's own click dispatched in the page;
  `interactions.dispatched` lists exactly those steps.
- `--legacy-cards` appends `tests/fixtures/grid/event/legacy-cards.html` to the event page before
  `</main>` (the browser twin of `render.mjs --legacy-cards`), so the EXPL-1 and CORP-5 walks keep
  exercising `event.js`'s drawing of the cards the redesign removed; `liveIds` says which walked ids
  the live page itself carries.
