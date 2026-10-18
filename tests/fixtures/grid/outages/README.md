# `tests/fixtures/grid/outages/` — SYNTHETIC outage bake inputs

Everything here is SYNTHETIC, written for `tests/test_grid_outages.py`. No real plant, operator
message, schedule row or company figure appears here, and nothing was read from BigQuery.

| Path | What it is |
|---|---|
| `export.json` | The two reads `scripts/grid/build_outages.py` makes from BigQuery (`outage_mentions`, `outage_events`), in the same row shape: a trip the RTD schedule carries 40 minutes later, a trip the schedule carried first, an ambiguous name, a return, a trip with only a DAP row (never read), two derated lists, a revision row, a `_BAT` resource and a row from before the span. |
| `bake/` | A one-day replay bake (`regions.json`, `sites.json`, `advisories.json`, `events.json`) the builder reads the span, the sites and the fallback messages from. |
