# `tests/fixtures/grid/map/` — the map canvas fixture and its harness

Everything here is synthetic and deterministic, derived from the grid page fixture's own
formulas (`tests/fixtures/grid/page/build.py`, imported by path). No real WESM row, plant,
coordinate, operator message or case fact appears, and nothing is read from the company copy.
The shapes are the ones `scripts/grid/build_data.py` (GRID-1) writes and `src/grid/map.js`
reads.

| Path | What it is |
|---|---|
| `build.py` | The formulas and the writer. `--check` rebuilds in memory and compares with the committed bytes; `tests/test_grid_map.py` runs it that way, so the fixture cannot drift. |
| `data/` | Seven files: `regions.json`, `hvdc.json`, `nodes-2026-09-21.json`, `advisories.json`, `sites.json`, `events.json`, `ph.geojson`. 10 sites: 8 located and 2 `p: "placeholder"` with null coordinates. Three located sites share one position (`SYN-BAY-1`, `SYN-BAY-3`, `SYN-STA-1` at 123.42, 10.90) — the real bake's own shape (492 located sites on 193 positions). The outline's land starts at 114.5 E so it never covers the placeholder matrix's anchor. `hvdc.json` leaves two congestion cells unstated (null): `MINVIS1` at 13:45 and `VISLUZ1` at 14:00 — an unknown congestion the canvas must not read as "not congested". |
| `harness.mjs` | Runs `src/grid/map.js` under a small DOM and a recording canvas-2D context — both throw on a member the module does not need, so a gap is a failure — and prints one JSON report of what was painted, what each gesture did to the transform and which callback a click called. Offline: no browser, no network, no library. `--width`/`--height` set the canvas box; `--no-canvas` gives the canvas no `getContext`, which is the text fallback's path. |

```sh
# from the repository root, any seat with node
node tests/fixtures/grid/map/harness.mjs --root . --data tests/fixtures/grid/map/data \
  --width 1280 --height 700
node tests/fixtures/grid/map/harness.mjs --root . --data tests/fixtures/grid/map/data \
  --width 390 --height 585 --no-canvas

# the committed bytes against the formulas
/usr/bin/python3 tests/fixtures/grid/map/build.py --check
```

`tests/test_grid_map.py` re-derives the module's transform and hit-testing formulas in Python
from the constants read out of `src/grid/map.js`, asserts the acceptance properties on those
formulas, and — when node is present — compares them, number by number, with the same module's
own `GridMap.math` output in this harness's report. The harness is skipped, with its reason, on
an interpreter without node; the Python re-derivation runs either way.

The real WESM snapshot is not here and never will be: GRID-1 bakes it from the company copy
into `build/grid-data/` (git-ignored), the image copies it inside `src/grid/grid-data`, and the
page reads it at `/grid-data/`. This fixture exists so the canvas's arithmetic, its layers, its
fail-closed placeholder rule and its fallback are testable offline, before ATG-8 wires the
module into the page.
