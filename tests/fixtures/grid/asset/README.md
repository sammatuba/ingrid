# `tests/fixtures/grid/asset/` — the asset profiles' fixture

Everything here is synthetic and deterministic, and nothing is hand-written: `payload/` is what
the **real** builder (`scripts/grid/build_assets.py`) writes over the bake fixture
`../catalog/bake` — itself the real `scripts/grid/build_data.py` over the synthetic grid inputs —
plus this directory's own location material. No real WESM row, plant, coordinate, operator
message or case fact is added here.

| Path | What it is |
|---|---|
| `build.py` | Runs the real builder and writes `payload/`. `--check` rebuilds in memory and compares every byte; `tests/test_grid_asset.py` runs it that way. |
| `geo/sites.csv` | The register aggregation for the five fixture sites, the shape `.local/geo/sites.csv` has: a generator row's `cap_mw` sums to the site's capacity, and a load node's row is its own station load. |
| `geo/crosswalk.csv` | The location file for two of them: `08PEDC` placed at plant precision with its source link and retrieval date, and `08PLACE` a `placeholder` row. The other three have no row — both reasons a location is not known. |
| `payload/assets/index.json` | The collection payload: five sites, one located and two approximate (`08SAMPLE` and `08PLACE`, drawn near `08PEDC` by the area-prefix rule); counts G 4 (1 located), NL 1, CLUZ 1, CVIS 4. |
| `payload/assets/<code>.json` | Five profiles. `08PEDC` carries the event and its one event-mapped message; `08SAMPLE` carries four messages by its code; `08PLACE` is a load node whose row states no position, so it is drawn at an approximate position near `08PEDC`; `03LUZ` and `04GEN` have no message, no event and no row. |
| `render.mjs` | Runs the pages' own script (`src/grid/asset.js`) against a built payload under a small DOM shim and prints one JSON report: the counts, the tiles, the lists, the search, the figures, both charts, the register, the location, the messages, the events, the catalog block, the not-known lines and every URL the page asked for. Offline, no browser, no library. |

The payload names its records by ATG-4's catalog dataset ids, so it is built with the real
register (`scripts/grid/catalog.json`); a rename there is a reason to run this file again, which
is what `--check` says by name. To run the two by hand:

```sh
/usr/bin/python3 tests/fixtures/grid/asset/build.py --check     # compare every byte, write nothing
/usr/bin/python3 tests/fixtures/grid/asset/build.py             # write payload/

node tests/fixtures/grid/asset/render.mjs --root . --page asset --code 08PEDC
node tests/fixtures/grid/asset/render.mjs --root . --page assets --query pedc
```

`render.mjs` is an approximation of a browser: it proves the script runs and fills the pages from
the payload, not that the layout looks right. The real browser run at 390 and 1280 is the
orchestrator's and belongs in the task record (ATG-8's checklist).
