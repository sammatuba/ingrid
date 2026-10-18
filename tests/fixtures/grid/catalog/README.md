# `tests/fixtures/grid/catalog/` — the data catalog's fixture bake

Everything here is synthetic and deterministic. `bake/` is not hand-written: it is what the
**real** bake builder (`scripts/grid/build_data.py`) writes over the synthetic grid fixture
(`../snapshot`, `../geo`, `../events.json`) plus the two small inputs beside this file — the
event-map spike output the bake turns into `vectors.json`, and one recorded event view it copies
into `events/`. No real WESM row, plant, coordinate, operator message or case fact is added here;
the site codes the grid fixture uses are its own synthetic rows.

| Path | What it is |
|---|---|
| `build.py` | Runs the real builder over the synthetic inputs and writes `bake/`. `--check` rebuilds in memory and compares every byte; `tests/test_grid_catalog.py` runs it that way. |
| `inputs/spike.json` | A synthetic event-map spike output (`vocab`, `E`, `plane`), the shape `build_data.py` reads to write `vectors.json`. |
| `inputs/events/syn-bay-unit-2-trip.json` | One synthetic recorded event view, copied byte for byte into `bake/events/` (and given `ask: true`, BAKE-1, because it is also a plan set's key). Its `id` is its file name, which the builder checks. |
| `bake/views/` | BAKE-1: the recorded plan sets `build.py` writes beside the CSV snapshot, and `index.json` listing them. VIEW-1 regenerates them through the governed view composer (`src/judgment/view.py`): each set carries the three recorded questions' answers — `What does this trip do to the outlook?`, `What was the price doing around the trip?` and `What is exposed?` — composed by `answer_question()` from the fixture's own records, so every receipt carries the composer's full field set and every figure is a record field copied by code. DOCK-1 moved them to plan shape `view.v4`: each receipt's plan carries `components`, `actions` and `not_shown` with reason keys and no text, the view's sentences are the composer's templates over the records, and the receipt's `actions` block lists the actions proposed, refused and run (the price plan's web search is refused `needs_sign_in`, because the bake answers an anonymous request). `build.py` writes them with `answer_question()` and `FixtureView`; nothing is hand-edited. Six keys: the fixture event's id and the pages that carry the assistant's mount (`home`, `outlooks`, `register`, `models`, `ask`). BOOK-4: the record set also carries the synthetic book's exposure record for Visayas over 2026-10-19 13:00 to 15:00 at the plan cutoff (built by `src/book/adapter.py` from `tests/fixtures/book/`), so every set's exposure answer shows the exposure table first, and the account impact card is left out because both fixture vintages were issued after the plan cutoff. |
| `bake/` | The files the catalog builder measures: `regions.json`, `hvdc.json`, `nodes-2026-09-21.json`, `advisories.json`, `sites.json`, `events.json`, `events/syn-bay-unit-2-trip.json`, `ph.geojson`, `vectors.json`, plus the outlook and register indexes, the event's outlook view, its ontology placeholder and the `views/` plan sets. Four intervals (2026-09-21 13:35 to 13:50), three grids, five sites, six messages, one event. |
| `render.mjs` | Runs the catalog page's own script (`src/grid/catalog.js`) against a **built** payload under a small DOM shim and prints one JSON report: the tiles, a table per category, the dataset detail, the search and the caption. Offline, no browser, no library. |

The catalog payload is built, never committed: `scripts/grid/build_catalog.py` writes
`catalog.json` beside the baked files of the directory it measures, and the fixture bake is not a
place to keep it. To run the two by hand:

```sh
# the fixture bake reproduces from the real builder
/usr/bin/python3 tests/fixtures/grid/catalog/build.py --check

# build the payload from the fixture bake into a scratch directory
/usr/bin/python3 scripts/grid/build_catalog.py --bake tests/fixtures/grid/catalog/bake \
  --out /tmp/catalog-fixture/catalog.json

# run the page's own script against it (a machine with node; the orchestrator runs it)
node tests/fixtures/grid/catalog/render.mjs --root . --data /tmp/catalog-fixture \
  --stamp 0123456789abcdef
```

`render.mjs` is an approximation of a browser: it proves the script runs and fills the page from
the payload, not that the layout looks right. The real browser run at 390 and 1280 is the
orchestrator's and belongs in the task record (ATG-8's checklist), not here.

## The view.v3 plan set the dock still reads (DOCK-2)

`v3/views/ask.json` is the fixture bake's `views/ask.json` as the composer wrote it under
view.v3, before DOCK-1 regenerated the bake under view.v4: the same bytes as blob
`5b79f852ace2ae8617a348ab72ad896fa6c3b7a5` at commit `971885b0`. The live site's plan sets are
view.v3 until a release carries view.v4, so `tests/test_grid_ask_page.py` runs the dock on this
file as well (`ask-render.mjs --data tests/fixtures/grid/catalog/v3`). Never edit it by hand.
