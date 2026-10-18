# Grid snapshot fixture (synthetic)

A small, **entirely synthetic** sample of the four files `scripts/grid/export.sh` writes,
plus the location material `scripts/grid/build_data.py` reads. It exists so
`tests/test_grid_data.py` can exercise the builder offline: no real WESM row, no real
plant name, no real coordinates and no real operator message appears here — every value is
made up to trip a rule:

| Path | What it exercises |
|---|---|
| `snapshot/regions_5min.csv` | four intervals (2026-09-21 13:35 to 13:50), three grids; a Visayas interval at the offer cap |
| `snapshot/hvdc_5min.csv` | both links on the same intervals, complete rows: one congested flag; the blank-flow, unknown-flag and missing-row variants are made by the tests in a temporary copy |
| `snapshot/nodes_0921_5min.csv` | five sites (G and NL), one plant that trips to zero MW, one row per interval/site/type in the export's shape — the group's price sum with its resource count (`lmp_sum,lmp_n`), its schedule sum with the resources stating one and the group's resource count (`mw_sum,mw_n,resources`); the dual-listed variant — a site priced both as a generator and as its own load, in both row orders, a group whose generator rows are blank, and one with an unequal resource count per type — is made by the tests in a temporary copy, so the fixture itself keeps its one shape |
| `snapshot/advisories.csv` | a trip, a `de-energized` planned-outage line, a yellow alert, a bracketed `[NSO Advisory]` re-online, a message with no readable header, and one whose header clock disagrees with its posting time |
| `geo/sites.csv` | registered capacity per site and type, the shape the register aggregation has: a generator row's value must read as a number or the build stops by name, and a load node's output capacity is null by nature |
| `geo/crosswalk.csv` | one row passing both location gates, one failing the site-code/province gate, one failing the ±25% capacity gate, one explicit `placeholder` row, and one site with no row at all. The blank-capacity, malformed-capacity, tolerance-edge, no-register and unknown-province variants are made by the tests in temporary copies of this file, so the fixture itself stays the one shape |
| `geo/ph.geojson` | squares, not boundaries: a synthetic country polygon and three synthetic provinces carrying the Natural Earth region names the province gate reads |
| `events.json` | an event whose time must come from the advisory record |

Run the fixture build with:

```sh
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
```

The real snapshot is company WESM data exported by the orchestrator seat into
`.local/grid-snapshot/`; it is never committed and never appears under `tests/fixtures/`.
