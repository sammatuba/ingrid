# WESM source fixtures: real sample rows, cited

These two JSON-lines files are **real rows** from the company WESM copy, exported by the
orchestrator seat on 2026-10-13 with the repo-local `gcloud` configuration (`bq`, project
`grid-nowcast`) and cited to the signed permission record
[`perm:wesm-company-copy:2026-10-13`](../../../docs/work/permissions/2026-10-13-wesm-company-copy.md),
which permits quoting message text in records, fixtures, tests, the workspace and the working
paper. The executor seat cannot run the export (no `bq`, no credential); the rows below were
read from the orchestrator's export in `.local/sources/wesm/` and copied byte-for-byte. The
export query that reproduces them is `scripts/data/wesm/export.sh`.

Digests of the committed bytes (see the packet for how they were taken):

| File | Rows | SHA-256 |
|---|---|---|
| `advisories-sample.jsonl` | 11 | `974e7980830beb85575d9a42c6513b3091124f3b9cee2edd01d8ca7b571e9f05` |
| `registry-pedc-sample.jsonl` | 1,560 | `4d366a8a41fdfd962bb5437c86ca18175cc2a8c63f7aad12765acbc99738eaeb` |

## `advisories-sample.jsonl`

Rows of `grid_raw.ext_others_mpi_advisories`, columns `interval_start, adv_id, adv_sdate,
adv_tran_type, adv_text_message`. Naive timestamps are Asia/Manila. `sample_group` marks why
each row is present:

| Group | Rows | What it exercises |
|---|---|---|
| `pedc_u2_21sep` | 4 (V133937, V135622, V141257, V155556) | the PEDC Unit 2 case advisories of 2026-09-21 |
| `random` | 4 (M191225, L094738, V031315, V031940) | ordinary messages across grids; two identical texts five days apart that are *not* one lineage |
| `repost` | 2 (V133459, V133518) | one body text posted twice, 19 seconds apart: one lineage, second cites `copied_from` |
| `midnight_wrap` | 1 (M000253) | 00:02 posting with an `2358H` event clock: the event is dated the previous day |

There is **no grammar-miss row in September 2026** — every message carries the grid prefix, the
header clock and the `[WEBSMS]` tag (recorded in the orchestrator's
`.local/sources/wesm/README.md` and the source profile). The parser's grammar-miss,
clock-disagreement and six-hour-gap paths are therefore exercised by constructed rows inside
`tests/test_wesm_sources.py`, each labelled there as a counterexample and never stored in these
files.

## `registry-pedc-sample.jsonl`

Rows of `grid_raw.ext_others_regcap_generation`: 1,560 rows, every register row for
`08PEDC_U01`, `08PEDC_U02`, `08PEDC_U03` and `03KAL_G01` (the two-participant example).
Actual columns: `trading_day_id, tp_name` (the trading participant), `resource_name,
maximum_capacity, byear, bmonth`; the source profile's labels (`trading_day`, `participant`,
`capacity_mw`, `resource_type`, `region`) are read onto them, and the region is derived from
the two-digit resource prefix (01-03 Luzon, 04-08 Visayas, 09-14 Mindanao). There is no
`resource_type` or `region` column.

Facts the run builder reads from these bytes (checked by `tests/test_wesm_sources.py`):

- 389 distinct trading days, 2024-05-27 to 2026-09-29, with the copy's 2025 hole
  (2024-10-26 to 2026-02-04); each resource has 390 rows because the billing-month boundary
  repeats 2024-06-26 (`bmonth` 6 and 7, identical values).
- `08PEDC_U02` (registered maximum 83.7 MW, participant PEDC) forms two runs, split by the
  hole, both `unreviewed` candidates; nothing is interpolated across the hole.
- `03KAL_G01` carries two participants on *different* days (PSALM to 2026-02-08 with 183.0 MW
  then 181.1 MW from 2026-02-05, C9PI from 2026-02-09), so it yields three change-only runs.
  The sample contains **no day on which one resource carries two participants**, so the
  `ambiguous` rule is exercised by a constructed counterexample in the tests; the packet
  records this gap against the intent's acceptance line.

## Note on the older folder rule

`scripts/data/README.md` (the data-foundation packet, 2026-10-11) says private sample rows go
to `.local/` and are never committed. The signed permission record of 2026-10-13 explicitly
permits quoting message text in fixtures and tests, and the DATA-1 intent directs these sample
rows to be committed and cited; the newer signed record is the authority. The older README is
outside this task's allowed paths and is left unchanged; the packet records the conflict.
