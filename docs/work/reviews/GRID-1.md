# GRID-1: grid data snapshot

Task packet. Lane GRID, milestone M5, executor agent. Branch `task/GRID-1` from
`feat/h1-api-persistence` (at `d3fb970`). Read first: [AGENTS.md](../../../AGENTS.md),
[milestones](../milestones.md), the [grid-desk intent](../grid-desk/intent.md) and the
[real-sources intent](../real-sources/intent.md). This record is the task's packet; the
commands below were run in the task worktree on 2026-10-14 with `/usr/bin/python3` 3.14.4
**before** the commit on `task/GRID-1`. State `in_progress`, self-review only — a reviewer
sets `done`.

## What was built

| Path | What it is |
|---|---|
| [`scripts/grid/export.sh`](../../../scripts/grid/export.sh) | The four read-only `bq` queries (regional summaries, node prices and schedules, HVDC schedules, operator advisories) over the replay window, with a row count and sha256 per file. Orchestrator seat only; SELECT-only under `--maximum_bytes_billed`. |
| [`scripts/grid/build_data.py`](../../../scripts/grid/build_data.py) | The builder: the four CSVs plus the location material in, the seven contract files out as compact JSON; `--check` builds in memory, validates every file against the contract and writes nothing; refuses to write into a path Git would track. |
| [`scripts/grid/events.json`](../../../scripts/grid/events.json) | The event spec. Its row is the orchestrator's own event record from the template build (`id`, `t`, `advisory`, `site`, `title`, `assumption`) — no case fact was invented here; the builder takes the event's time from the advisory row and refuses a spec that disagrees. |
| [`scripts/grid/README.md`](../../../scripts/grid/README.md) | The lane: what runs in which seat, the inputs, the swap point, the exclusion rules. |
| [`tests/test_grid_data.py`](../../../tests/test_grid_data.py) | 31 tests: the fixture build and its counts, the placeholder and gate rules, the advisory parse, 20 contract-violation mutations, and the four repository rules (Git, release export, Dockerfile/context, writer guard). |
| [`tests/fixtures/grid/`](../../../tests/fixtures/grid/README.md) | The synthetic sample (four CSVs, `sites.csv`, `crosswalk.csv`, a square-geometry `ph.geojson`, an event spec) and its README. No real WESM row, plant, coordinate or message. |
| [`Dockerfile`](../../../Dockerfile), [`.dockerignore`](../../../.dockerignore) | `COPY build/grid-data ./src/grid/grid-data` after `COPY src ./src`; the context file keeps `build/` **off** its exclusion list on purpose, with the reason written beside it. |
| [`scripts/release/allowlist.json`](../../../scripts/release/allowlist.json) | Three reviewed exclusions: `build` (`grid-snapshot-data`), `scripts/grid` (`grid-lane-scripts`) and `tests/test_grid_data.py` (`grid-data-tests`). |
| [`tests/test_release_audit.py`](../../../tests/test_release_audit.py), [`tests/test_hosted_config.py`](../../../tests/test_hosted_config.py) | One new test asserting the exclusion, and the image-contract test updated from two COPY sources to the reviewed three. |

## The contract the builder enforces

The shapes are the ones `src/grid/grid.js` (design file, on `task/GRID-2`) reads and
the intent fixes; the builder's `contract()` checks every one of them and reports a
deviation, never repairing it: the interval axis is shared by `regions.json` and `hvdc.json`
and is strictly increasing; each grid carries exactly the nine region fields at the axis
length; `hvdc.json` carries `MINVIS1` and `VISLUZ1` with integer flows and 0/1 congestion;
each `nodes-YYYY-MM-DD.json` is one day whose matrices are `intervals x sites` and whose
sites all exist in `sites.json`; `advisories.json` entries carry exactly
`t, id, grid, kind, text` with `kind` in the desk's six tokens and a grid in the three
codes or null; `sites.json` entries carry `s, k, g, cap, lon, lat, p` (and `name` only when
located), a placeholder never has a position or a name, and a located site lies inside the
design's view box; `events.json` entries carry exactly `id, t, advisory, site, title,
assumption`, name an advisory in the snapshot, take its time from that advisory and name a
site with a node series; `ph.geojson` is a non-empty FeatureCollection of country/province
features whose coordinates are `[lon, lat]` pairs rounded to 0.001°.

Two rules were read from the intent rather than carried over mechanically from the
orchestrator's scratch builder [preview_mkdata.py](../grid-desk/reference/preview_mkdata.py):

- **Advisory `grid` and `text` come from the DATA-1 reader**
  ([`src/adapters/wesm/advisories.py`](../../../src/adapters/wesm/advisories.py)): its message
  grammar names the grid and its passage is the stored text. On the real snapshot that is
  byte-identical to the reference builder's own cleaning — all 350 texts match. A row the
  reader refuses (here: none; the fixture has a grammar miss and a `CLOCK_DISAGREEMENT` row)
  keeps its own text with `grid: null` and is counted in the report.
- **`kind` stays the desk's display vocabulary** (`trip, online, red, yellow, mld, notice`)
  with the reference builder's keyword rule. The reader's bundle v5 category was measured as
  the alternative and rejected on evidence: over the 350 real advisories it differs on 200,
  including 175 planned-outage lines it calls `return_to_service` because its `energized`
  keyword matches inside `de-energized` — the feed would print "Back online" on a
  de-energized line — and its token set has no red/yellow/mld split the design switches on.
  The rule kept reproduces the template's baked kinds 350/350.

**Locations.** A crosswalk row is used only when both gates pass: the site-code prefix's grid
agrees with the found province's grid, and the public capacity is within ±25% of the
registered capacity. The province's grid is read from the prepared outline's Natural Earth
region name (17 region names map to the three grids); an unknown province fails closed. Every
failing or absent row is a placeholder — `p: "placeholder"` with `lon`/`lat` null and no
name, drawn by the page in its own labelled column (the rule changed in the template after
the reference build; the intent's orchestrator note records it).

## Acceptance evidence

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | On the fixture: `contract.files 7, violations []`; on the real snapshot: `7` files, `0` violations (report below). 20 tests mutate a built file per rule and assert the exact violation, plus one for a missing file and one for a non-JSON payload. |
| placeholder count reported | The report carries `sites: {total, located, placeholder}` and a note. Fixture: `1 of 5 sites located; 4 drawn at pending positions`. Real snapshot (no crosswalk yet): `0 of 617 sites located; 617 drawn at pending positions (locations pending)`. |
| no data file tracked by Git | `tests.test_grid_data.RepositoryRules.test_no_data_file_is_tracked_by_git`: no tracked path under `build/`, and the snapshot CSV names exist only under `tests/fixtures/grid/` (tracked or untracked). Plus the writer guard: in a throwaway Git tree the builder exits 2 and writes nothing until the output is ignored. |
| release export excludes `build/grid-data/` | `scripts/release/allowlist.json` rule `grid-snapshot-data` (`path: build`); asserted in `test_the_baked_grid_snapshot_is_a_reviewed_exclusion` and in `tests/test_grid_data.py`, including that the decision is not the `unmatched` fall-through. |

## Verification (commands and results)

All run in the task worktree, unpublished, on 2026-10-14 with `/usr/bin/python3` 3.14.4:

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 31 tests in 0.467s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 582 tests in 13.637s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (305 Markdown files, 1604 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
```

The fixture `--check` from the repository root (the command the fixture README documents):

```sh
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
# exit 0; contract {files: 7, violations: []}
# advisories {rows 6, parsed 5, refused 1 (V174000 CLOCK_DISAGREEMENT)}
# sites {total 5, located 1, placeholder 4}; gates {prefix 1, capacity 1, coordinates 0, precision 0, no_grid_for_province 0}
# notes: "1 of 5 sites located; 4 drawn at pending positions (locations pending)"
```

### Fidelity against the orchestrator's baked snapshot

The builder was run over the real export copied read-only from the main checkout's
`.local/grid-snapshot/` (ignored, never committed) and its bytes compared with the data the
design template was built against (`.local/grid-snapshot/data/`). Six of the seven files are
byte-identical; `sites.json` differs only by the documented placeholder rule — same order,
same keys, same capacity and grid, and 1,234 position fields (617 sites x lon/lat) set to
null because no crosswalk exists yet:

```
advisories.json          54781 bytes  sha256 4344eb42…418b  identical
events.json                180 bytes  sha256 2561130c…05f3  differs (spec-generated: · escape, no trailing newline; parsed value identical)
hvdc.json                73704 bytes  sha256 7cf908fa…00be  identical
nodes-2026-09-21.json  1850860 bytes  sha256 9e0aa919…9ea2  identical
ph.geojson              337837 bytes  sha256 57c0d0cf…76e5  identical
regions.json            286258 bytes  sha256 20108873…5d5c  identical
sites.json               51815 bytes  sha256 de04b7e5…c25f  differs by the placeholder rule only
```

`/usr/bin/python3 scripts/grid/build_data.py --check` on that snapshot: exit 0,
`contract {files: 7, violations: []}`, `intervals 2304`, `advisories {rows 350, parsed 350,
refused 0}`, `sites {total 617, located 0, placeholder 617}`.

## Self-review note (author-run, not independent)

Every number above comes from a run in this worktree; nothing was written first and measured
later. No frozen contract was touched: `src/judgment`, `src/review`, `src/api` and
`docs/work/probe-bundle/` are unchanged, and the DATA-1 reader was read, not modified. Two
existing tests changed and each is disclosed here rather than weakened: the HOST-1 image
contract test now names the reviewed three COPY sources instead of two (the closed set of
sources is still asserted, and `ADD` is refused), and `tests/test_release_audit.py` gained one
new test — no assertion was deleted. `tests/fixtures/grid/` is synthetic and labelled so in
its README; the real snapshot stays in `.local/` (ignored) and was never staged.

Not verified in this seat, and stated as such: the container leg (`docker build` with the new
COPY) and the `bq` export itself — this seat has no docker and no `bq`/credential. The
`--check` run above is the offline evidence that the COPY source is the directory the builder
writes and that the context file does not exclude it (both asserted by tests).

## Open items and hand-back

1. **`.gitignore` needs one line, and it is outside this task's owned paths.** `build/` is
   not ignored today, so `git add -A` in the main checkout would commit the baked company
   data, and `plan.py scope` for GRID-2/GRID-3 would list it as an outside-path change. The
   builder fails closed with that instruction rather than writing silently (`--force`
   overrides), and the release export and the tests already exclude the data. Exact next
   action for the orchestrator: add `build/` (reason: generated grid replay data, never
   committed — the same shape as the `src/dashboard/data/` line) to `.gitignore`, in the
   orchestrator's own commit.
2. **The `bq` queries are a reconstruction from recorded names.** `export.sh` was written
   from the copy's naming rule (`grid_raw.ext_<folder>`, RUNBOOK §1), the columns
   `scripts/data/sql/01`/`02` read, and the four CSVs the orchestrator exported on
   2026-10-14 — it could not be executed here (no `bq`, no credential). Before overwriting
   the snapshot, run it with `OUT=.local/grid-snapshot-rerun` and diff against the files
   already in the tree: a column or table name that is wrong fails immediately, and a
   semantic difference (for example `demand_mw`) shows as a value difference. The alias
   contract between the script and the builder is the header comment of each.
3. **The crosswalk has not been supplied.** With no `.local/geo/crosswalk.csv` every site is
   a placeholder and the map shows none; that is the documented state until the owner drops
   the file in, which needs no code change.
4. GRID-2's page must serve `/grid-data/` from the directory the image now carries
   (`src/grid/grid-data/`); the design file's `DATA = '/grid-data/'` is unchanged.

Exact next action: the independent review of this packet and the branch; then GRID-2, which
depends on it. Nothing else in GRID-1 is unfinished.

## Post-commit re-run (2026-10-14)

Committed as `2516496` on `task/GRID-1` (22 files, +1798/-7), the packet and the state edits
in the same commit. Re-run on the committed tree:

```sh
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                        # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 -m unittest tests.test_grid_data
                                        # Ran 31 tests in 0.382s  OK
/usr/bin/python3 -m unittest discover -s tests
                                        # Ran 582 tests in 11.103s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check  # PASS (305 Markdown files, 1604 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check  # OK: 49 tasks, 7 gates
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Orchestrator findings from the real export (2026-10-14, orchestrator seat, not a designated review)

`bash scripts/grid/export.sh` run against BigQuery (read-only): regions 6,048 rows, nodes 178,272, hvdc 4,608,
advisories 300. The orchestrator's reference export of the same tables gives 6,912, 204,191, 2,879 and 350 rows. Address
every row; keep all tests green.

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/grid/export.sh` (`END` default) | The default window ends at `2026-09-29 00:00:00` exclusive, so 29 Sep is missing; the intent's replay is 21–29 Sep | last exported interval `2026-09-28T23:55` | Default `END` = `2026-09-30 00:00:00` (exclusive) |
| important | `regions_sql` | Built from raw `rtd_regional_summaries` and uncapped node prices: intervals are missing (2,016 per region instead of 2,304 over the same days) and the "median generator price" differs from the curated definition the page's wording uses | counts above; the reference uses `grid_curated.intervals` and `grid_curated.interval_pricing` | Read `grid_curated.intervals` (demand, generation, import, export, load curtailed, dispatchable-reserve requirement and shortfall) LEFT JOIN `grid_curated.interval_pricing` (`gen_lmp_capped_median`, `gen_lmp_capped_max`) on interval and region code, exactly as `docs/work/grid-desk/reference/preview_mkdata.py`'s inputs were exported |
| important | `nodes_sql` | No `mkt_type = 'RTD'` filter (the table carries more than one market type) and the site is cut at the last underscore, while `sites.csv` and the crosswalk cut at the first | 178,272 rows against the reference 204,191 for 21 Sep | Filter `mkt_type = 'RTD'`; site = `SUBSTR(resource_name, 1, STRPOS(resource_name, '_') - 1)`; one row per (t, site, type) |
| minor | `export.sh` | An output override was not honoured; the run wrote into `.local/grid-snapshot/` | orchestrator passed `OUT_DIR` | Document the supported variable (`OUT`) in the usage line, or accept `OUT_DIR` |

The executor seat cannot run `bq`; change the queries and their tests, and the orchestrator re-runs the export and compares
the counts.

## Rework (2026-10-14, executor seat, after the findings above)

Read first, as the rework asked: this record. **It carries no separate designated-review section and no "Outcome and next
action" paragraph** — the only findings in it are the orchestrator's table above, committed as `65ff016` (the branch tip).
Checked rather than assumed: `docs/work/reviews/GRID-1.md` is the only file in the worktree naming GRID-1 outside the plan
files, the grid-desk intent and the reference builder, and nothing under the ignored `.local/` holds a review record. The
rework therefore disposes of that table row by row and of nothing else. All four rows are inside this task's allowed
paths, no frozen contract or acceptance text is touched, every change is in `scripts/grid/` or
`tests/test_grid_data.py`, and every number below comes from a run in this worktree on this branch.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | `END` defaulted to `2026-09-29 00:00:00`, so 29 Sep was outside the window | [`export.sh:77`](../../../scripts/grid/export.sh) defaults to `2026-09-30 00:00:00` (exclusive), stated in the header and the usage line as the 21-29 Sep replay |
| important | `regions_sql` read raw `rtd_regional_summaries` with uncapped prices | [`export.sh:105`](../../../scripts/grid/export.sh) rewritten: `grid_curated.intervals` LEFT JOIN `grid_curated.interval_pricing` on `p.interval_start = i.interval_start AND p.region_code = i.region_name`, taking `en_requirement_mw, en_generation_mw, en_import_mw, en_export_mw, en_load_curtailed_mw, dr_requirement_mw, dr_shortfall_mw` and the capped `gen_lmp_capped_median` / `gen_lmp_capped_max`, aliased to the CSV columns the builder reads (the join spelling is the one `scripts/data/sql/09_features.sql` uses; the two tables' definitions are `sql/02` and `sql/04`) |
| important | `nodes_sql` had no market-type filter and cut the site at the last underscore | [`export.sh:130`](../../../scripts/grid/export.sh) filters `mkt_type = 'RTD'`, makes the site `SUBSTR(resource_name, 1, STRPOS(resource_name, '_') - 1)` (first underscore, the cut `sites.csv` and the crosswalk use), selects `resource_type AS typ` and groups `BY t, site, typ` — one row per interval, site and type |
| minor | an `OUT_DIR` override was not honoured | [`export.sh:56`](../../../scripts/grid/export.sh): `OUT="${OUT:-${OUT_DIR:-$ROOT/.local/grid-snapshot}}"`, so `OUT_DIR` is accepted and `OUT` wins when both are set; both named in the header and the usage line |

No `bq` command was run in this seat (no `bq`, no credential); the corrected statements are executed by the orchestrator,
who re-runs the export and compares the counts as the findings note says.

### The queries are now pinned by tests

`tests/test_grid_data.py` gains `ExportQueryTests` (10 checks; the file goes 31 -> 41, the suite 582 -> 592). To make the
queries reviewable and testable in a seat with no `bq`, `export.sh` gained `--print-sql`: it prints the window, the output
directory and the four statements, built by the same functions the run path calls, and calls nothing and creates nothing
(documented in the script header and the lane README). The checks run that path with a stubbed `bq` first on `PATH` that
records any call, and assert: the review path prints the four statements and leaves no `bq` call and no directory; the
default window ends at `2026-09-30 00:00:00`, after the replay's last interval `2026-09-29 23:55:00`; the regions query
reads the curated tables, joins on interval and grid code, aliases all seven curated columns and both capped price
columns and no longer reads the raw summaries or computes a quantile itself; the nodes query filters `mkt_type = 'RTD'`,
cuts at the first underscore, groups by `t, site, typ` and carries neither `REGEXP_REPLACE` nor `ANY_VALUE`; the node query
spans exactly 21 Sep; an explicit START/END reaches the interval queries; `OUT_DIR` is honoured and `OUT` wins; every
statement is a read-only `SELECT`; an unusable argument is still a usage error.

Negative control, run here (`.local/grid-rework/check_red.py`, ignored evidence, not a repository test) — the same checks
against the pre-rework script from `HEAD` and against copies with one correction reverted each:

```
pre-rework script from HEAD: 9/10 red (the green one is the usage-error check, which the old
    script satisfied too): test_an_explicit_window_reaches_the_interval_queries,
    test_every_statement_is_a_read_only_select, test_out_wins_when_both_output_variables_are_set,
    test_the_default_window_covers_the_replay_through_29_september,
    test_the_nodes_query_covers_exactly_its_day, test_the_nodes_query_filters_the_real_time_market,
    test_the_output_directory_honours_out_dir_as_well_as_out,
    test_the_regions_query_reads_the_curated_tables,
    test_the_review_path_prints_the_window_and_the_four_statements
regions_sql reverted to the raw summaries      red: test_the_regions_query_reads_the_curated_tables (as expected)
nodes_sql loses the market-type filter         red: test_the_nodes_query_filters_the_real_time_market (as expected)
nodes_sql cuts the site at the last underscore red: test_the_nodes_query_filters_the_real_time_market (as expected)
default END back to 2026-09-29                 red: test_the_default_window_covers_the_replay_through_29_september (as expected)
OUT_DIR no longer accepted                     red: test_the_output_directory_honours_out_dir_as_well_as_out (as expected)
```

### Commands and results (all in this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 41 tests in 0.463s  OK  (31 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 592 tests in 9.623s  OK (skipped=7)  (582 before)
/usr/bin/python3 scripts/repo.py check                   # PASS (306 Markdown files, 1604 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # exit 1, one path: .gitignore (see below)
/usr/bin/python3 scripts/plan.py scope GRID-1 cd1fa92     # OK: all changed files inside GRID-1 allowed paths
bash -n scripts/grid/export.sh                           # exit 0
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
                                                         # exit 0; contract {files 7, violations []}
                                                         # sites {total 5, located 1, placeholder 4}; gates {prefix 1, capacity 1, ...}
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
                                                         # exit 0; contract {files 7, violations []}; intervals 2016
                                                         # advisories {rows 300, parsed 300, refused 0}
                                                         # sites {total 619, located 0, placeholder 619}; crosswalk absent
```

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` exits 1 listing exactly one path, `.gitignore`, and it is not
this rework's: `cd1fa92` ("gitignore: build/ (baked grid data, image only)") is the orchestrator's own commit on this
branch, adding the `build/` line the earlier packet asked for. That file is outside GRID-1's owned paths, so this seat
neither edits nor reverts it, and the default scope run cannot print OK until `.gitignore` is either a coordination file
in `docs/work/tasks.json` or accepted by the reviewer as the orchestrator's own change. Against that commit the scope is
clean, as printed above, and the working tree holds only the three files of this rework
(`scripts/grid/export.sh`, `scripts/grid/README.md`, `tests/test_grid_data.py`).

Re-run after this section's own links and the plan edits landed: `repo.py check` `PASS` (306 Markdown files, 1,611 local
links, 8 skills), `plan.py check` `OK: 49 tasks, 7 gates`, full suite `Ran 592 tests in 9.132s` `OK (skipped=7)`.

### Acceptance (unchanged text, re-checked after the rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | the two `--check` runs above (`files 7, violations []` on the fixture and on the real snapshot) and the 22 contract checks in `tests/test_grid_data.py`, all green |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` (no tracked `build/`, no snapshot CSV outside the fixture) and the writer guard |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` plus the release-audit test, both green |

### What was not changed, and why

- **`build_data.py` is untouched.** Its CSV column contract is unchanged (same headers, same aliases), so no builder
  change was needed for the corrected queries. One consequence is recorded here rather than decided quietly: the node
  CSV is now one row per `(t, site, type)`, and if a site ever carries two types the builder keeps the last row in
  `(t, site, typ)` order and the other is not represented — the same rule the reference builder
  [`preview_mkdata.py`](../grid-desk/reference/preview_mkdata.py) applies over the reference CSV it was built from, so
  the baked file still reproduces; a site that actually needs both rows would be an intent decision, not a silent choice
  here.
- No acceptance text, frozen contract, fixture, `Dockerfile`, `.dockerignore` or release allowlist changed; no test was
  weakened, skipped or deleted. The 31 earlier checks are untouched and green.
- `docs/work/tasks.json`: this task's `state` is unchanged (`in_progress`); only this task's own `note` is refreshed to
  describe the rework. No task was added and no acceptance text was touched.

### Self-review note (author-run, not independent)

The four findings are answered in the queries and pinned by executed checks that fail on the pre-rework script and on each
reverted correction; the acceptance items keep their text and their evidence. The rework did not run `bq`, did not run
`docker`, and made no model, cloud, credential or network call. Remaining limits: the corrected counts can only be
compared by the orchestrator's re-run (regions 6,912 / nodes 204,191 / advisories 350 were the reference's counts; `hvdc`
at 2,879 was not raised as a finding and its window behaviour is the orchestrator's to check), and the node-type
consequence above is recorded, not decided.

### Open items and exact next action

1. The orchestrator re-runs `bash scripts/grid/export.sh` (now defaulting to the 21-29 Sep window, `--print-sql` shows
   the four statements first) and compares the counts with the reference; then
   `/usr/bin/python3 scripts/grid/build_data.py --check`, then the bake and `docker build`.
2. `.gitignore` in the default scope run, as above: either add it to `coordination_files` in `docs/work/tasks.json` or
   accept it as the orchestrator's own commit; nothing in this rework depends on that edit.
3. The node CSV's `(t, site, type)` rows per interval, if the corrected export shows a site with two types: an intent
   question for the builder, not a change made here.

Exact next action: the independent re-review of this rework; then GRID-2, which depends on GRID-1.

## Orchestrator finding 2 (2026-10-14, after the rework re-export; not a designated review)

The re-export now matches the reference exactly (regions 6,912, nodes 204,192, hvdc 5,184 with 29 Sep, advisories 350).
One gate reads the intent more strictly than meant:

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/grid/build_data.py:307` | The capacity gate fails a row whose `public_capacity_mw` is blank. The intent's gate exists to catch a wrong match (a public capacity that contradicts the registered one); a blank value contradicts nothing, and the row still carries its source and passes the region gate | with the orchestrator's 38-row gated crosswalk: 6 located, 31 rejected by `capacity`, all of them blank | Apply the ±25% test only when `public_capacity_mw` is present; a blank value passes the capacity gate. Count blank-capacity rows separately in the report (`capacity_unstated`). Add tests for blank, within and outside the tolerance |
| minor | report | One row fails `no_grid_for_province` | report `gates.no_grid_for_province: 1` | Print the site code and the province string in the report so the orchestrator can fix the crosswalk row |

The intent's wording is clarified on the integration branch to match.

## Rework 2 (2026-10-14, executor seat, after Orchestrator finding 2)

Read first, as the rework asked: this record. It again carries **no designated-review section and
no "Outcome and next action" paragraph** — the rework prompt is `scripts/seats/rework.sh`'s
standard text, which points every task at `docs/work/reviews/<ID>.md`, and the newest findings
here are the orchestrator's own table, **Orchestrator finding 2**, committed as `c3e7ef8` (the
tip this rework starts from). This file is the task packet as well as the review record — the
brief lists it, `tasks.json`'s note and the PROGRESS row both point here — so this section is
**appended**: nothing above is edited, no verdict is written, and no reviewer record is touched
or invented. Both rows are inside the allowed paths, and neither needs a frozen contract or
acceptance text changed.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | The capacity gate failed a crosswalk row whose `public_capacity_mw` is blank, though a blank contradicts nothing and the row still passes the region gate | [`build_data.py:321`](../../../scripts/grid/build_data.py) now applies the ±25% test only when the source states a value: `public is None` passes, `keep` locates the row with its position, name and precision, and the row is counted apart as `gates.capacity_unstated` ([`build_data.py:293`](../../../scripts/grid/build_data.py)). The rule is written the same in the module docstring, the [lane README](../../../scripts/grid/README.md) and the [fixture README](../../../tests/fixtures/grid/README.md), and it matches the intent's clarified wording ("public capacity, when the source states one, within ±25% of registered capacity") |
| minor | One row fails `no_grid_for_province` and the report showed only the count | [`build_data.py:336`](../../../scripts/grid/build_data.py) adds `report["gates_detail"]["no_grid_for_province"]`, one `{"site", "province"}` object per row the outline cannot place. On the orchestrator's crosswalk it carries the one row, so the crosswalk line can be fixed by hand; the values stay in the report and are not copied into this record |

**Measured on the orchestrator's own inputs** (`.local/grid-snapshot/` and `.local/geo/`, both
ignored, read-only; nothing written): before this rework `--check` reported `gates {capacity 31,
no_grid_for_province 1}` and `sites {6 located, 611 placeholder}`; after it reports `gates
{capacity 16, capacity_unstated 15, no_grid_for_province 1}` and `sites {21 located, 596
placeholder}`, with `contract {7 files, 0 violations}`. One correction to the finding's wording,
taken from the measurement rather than from the table: of the 31 rows the capacity gate was
rejecting, **15 are blank and 16 state a capacity genuinely outside ±25%** (the finding reads
"all of them blank"). The 16 stated mismatches stay placeholders — that is the gate working —
and the 15 blanks are the rows that move to located.

### Tests (41 -> 45 in the file, 592 -> 596 in the suite)

`tests/test_grid_data.py` gains four checks, and the existing gates check grows two assertions
(no assertion was deleted or weakened):

- `test_a_blank_public_capacity_passes_the_capacity_gate` — 04GEN with a blank capacity locates
  at its crosswalk position and name, `capacity` stays 0 and `capacity_unstated` is 1; the build
  is re-validated against the contract.
- `test_a_stated_capacity_within_the_tolerance_is_located` — 08PEDC's stated 300 MW against 317
  MW registered, plus the ±25% edges themselves (237.75 and 396.25), which the gate includes.
- `test_a_stated_capacity_outside_the_tolerance_stays_a_placeholder` — 04GEN's 100 against 400,
  plus one step past each edge (237.749, 396.251).
- `test_a_province_the_outline_cannot_place_is_reported_with_its_row` — the row is a placeholder
  and `gates_detail.no_grid_for_province` names the site code and the province string.

The variants are made in a temporary copy of the fixture's crosswalk (helper `with_capacities`),
so the fixture itself keeps its one shape and its existing counts.

Negative control (`.local/grid-rework/red_check.py`, ignored evidence, not a repository test):
the pre-fix builder from `c3e7ef8` is swapped in, the checks run, and the working copy is
restored byte for byte afterwards (`working copy restored byte for byte: True`).

```
test_a_blank_public_capacity_passes_the_capacity_gate           RED   AssertionError: 'municipality' != 'placeholder'
test_a_province_the_outline_cannot_place_is_reported_with_its_row RED  KeyError: 'gates_detail'
test_the_crosswalk_gates_turn_failing_rows_into_placeholders     RED   gates dict without 'capacity_unstated'
test_a_stated_capacity_within_the_tolerance_is_located           RED   KeyError: 'capacity_unstated'
test_a_stated_capacity_outside_the_tolerance_stays_a_placeholder RED   KeyError: 'capacity_unstated'
whole file on the pre-fix builder: FAILED (failures=2, errors=5)
```

Said plainly rather than claimed as five independent proofs: the **blank** check is the one that
fails on the pre-fix builder for the finding's own reason (the row came back a placeholder); the
province and gates checks fail there because the report keys they read did not exist yet; and the
two tolerance checks pin behaviour this fix did not change (the old builder applied the same
±25% test to stated values), so they go red on the old script only on the new report key.

### Commands and results (this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 45 tests in 0.559s  OK   (41 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 596 tests in 10.156s  OK (skipped=7)  (592 before)
/usr/bin/python3 scripts/repo.py check                   # PASS (306 Markdown files, 1,611 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # exit 1, one path: .gitignore (see below)
/usr/bin/python3 scripts/plan.py scope GRID-1 cd1fa92    # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 .local/grid-rework/red_check.py         # the negative control printed above
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; intervals 2304
    # gates {capacity 16, capacity_unstated 15, coordinates 0, no_grid_for_province 1, precision 0, prefix 0}
    # sites {total 617, located 21, placeholder 596}; advisories {rows 350, parsed 350, refused 0}
    # gates_detail.no_grid_for_province: 1 entry, keys ['province', 'site'], both populated
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
    # exit 0; contract {files 7, violations []}; gates {prefix 1, capacity 1, capacity_unstated 0, ...}
    # sites {total 5, located 1, placeholder 4}
```

`scripts/grid/export.sh` is **unchanged** in this rework, so `bash -n` was not needed again; the
suite's own `test_the_export_script_is_a_reviewable_shell_script` runs `bash -n` over it and is
green. No `bq`, `docker`, model, credential, cloud or network call was made; the two `--check`
runs read local files and wrote nothing.

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` exits 1 listing exactly one path,
`.gitignore`, unchanged from the previous rework: it is the orchestrator's own commit `cd1fa92`
("gitignore: build/ (baked grid data, image only)"), outside GRID-1's owned paths, so this seat
neither edits nor reverts it. Against that commit the scope is clean as printed above, and the
working tree holds this rework's seven files.

### Acceptance (unchanged text, re-checked after this rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | both `--check` runs above (`files 7, violations []` on the fixture and on the real inputs) and the contract checks in `tests/test_grid_data.py`, all green |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the fixture check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` and the writer guard, untouched and green |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` and the release-audit test, untouched and green |

### What was not changed, and why

- No fixture, contract, `Dockerfile`, `.dockerignore` or release file changed; no test weakened,
  skipped or deleted; `export.sh` and the builder's CSV input contract are untouched, so the
  corrections from the previous rework are unaffected.
- The `gates` report block gains a key. That is a report shape, not the data contract: nothing in
  `contract()` or in the seven output files depends on it, and the page reads only the files.
- `docs/work/tasks.json`: this task's state is unchanged (`in_progress`); only this task's own
  `note` is refreshed to describe this rework. No task was added and no acceptance text touched.
- `docs/work/PROGRESS.md`: one log row added; the task-table row already reads `in_progress`.

### Self-review note (author-run, not independent)

Both findings are answered in code and pinned by executed checks, with the one discriminating
negative control named as such rather than every red counted as proof. Every number above comes
from a run in this worktree on this branch; nothing was written first and measured later. No
frozen contract, acceptance text or reviewer record was touched, and the appends to this file
added a section only. Remaining limits, stated: the orchestrator's crosswalk is the only real
input this seat can check (`.local/` is ignored and read-only here), the 16 stated capacity
mismatches are left as placeholders by design and worth a glance when the crosswalk is revised,
and the container leg (`docker build`) is still not run in this seat.

### Open items and exact next action

1. The orchestrator may now re-run the bake: the blank-capacity rows locate (21 of 617 sites
   with this crosswalk), and the one `no_grid_for_province` row is named in the report so its
   crosswalk line can be corrected; then `docker build`.
2. `.gitignore` in the default scope run, as in the previous rework: either add it to
   `coordination_files` in `docs/work/tasks.json` or accept it as the orchestrator's own commit.
3. The 16 stated-but-outside rows: placeholders today, by the intent's gate. If the source
   values are right and the register is wrong for those sites, that is an intent question, not a
   change to make here.

Exact next action: the independent review of this rework; then GRID-2, which depends on GRID-1.

### Post-commit re-run (2026-10-14)

Committed as `dfb38d1` on `task/GRID-1` (7 files, +276/-24), the packet and the state edits in
the same commit. Re-run on the committed tree, unchanged:

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 45 tests in 0.559s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 596 tests in 10.243s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (306 Markdown files, 1,618 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 cd1fa92    # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # exit 1, listing only .gitignore (as before)
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Orchestrator finding 3 (2026-10-14; not a designated review)

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/grid/build_data.py` (site type and capacity) | `sites.json` has one entry per site code, but many codes appear in the price data both as a generator (`G` or `PS`) and as a load node (`NL`, the plant's own station load). The builder takes the `NL` type for such a site, looks up `(site, NL)` capacity (0 MW) and fails the capacity gate, so located generators are drawn at pending positions | with the 38-row crosswalk: 21 located, only 10 of them generators; 28 crosswalk generators not located, including `08PEDC` (the event site), `01SUAL`, `03ILIJAN`, `01GNPD` | A site that appears with `G` or `PS` in the snapshot is that kind (prefer `PS`, then `G`, over `NL`); its capacity is the sum over its generator resources from `sites.csv`. Add a test with a dual-listed site. Report the counts by kind |

## Rework 3 (2026-10-14, executor seat, after Orchestrator finding 3)

Read first, as the rework asked: this record. It again carries **no designated-review section and
no "Outcome and next action" paragraph** — the rework prompt is `scripts/seats/rework.sh`'s
standard text pointing every task at `docs/work/reviews/<ID>.md`, and the newest findings here are
the orchestrator's own table, **Orchestrator finding 3**, committed as `3bb03c7` (the tip this
rework starts from). This file is the task packet as well as the review record — the brief lists
it, `tasks.json`'s note and the PROGRESS row both point here — so this section is **appended**:
nothing above is edited, no verdict is written, and no reviewer record is touched or invented. The
row is inside the allowed paths, and neither it nor the test it asks for needs a frozen contract or
acceptance text changed.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | A site the snapshot prices both as a generator (`G`/`PS`) and as its own station load (`NL`) took the `NL` kind; the builder then looked up `(site, NL)`, found 0 MW and failed the capacity gate | [`build_data.py:201`](../../../scripts/grid/build_data.py) collects every `typ` a site is priced under instead of the last row's; [`site_kind`](../../../scripts/grid/build_data.py) (`build_data.py:288`) returns `PS` when present, else `G`, else the remaining kind, so `NL` is a site's kind only when no generator resource is listed; [`build_data.py:424`](../../../scripts/grid/build_data.py) sums the register's generator rows per site, and [`build_data.py:327`](../../../scripts/grid/build_data.py) gives a generator-kind site that sum (with the generator rows' region) instead of the load row's 0 MW |
| important | Report the counts by kind | [`build_data.py:465`](../../../scripts/grid/build_data.py) adds `report["site_kinds"]`: a `{"total", "located"}` block per kind, all three of `G`, `NL`, `PS` always present, so the located-generator count the finding had to derive is printed |
| — | Add a test with a dual-listed site | three checks in [`tests/test_grid_data.py:253`](../../../tests/test_grid_data.py); the register (`sites.csv`) and the node CSV are varied in a temporary copy (`build_with_local_files`, `with_dual_listing`), so the fixture keeps its one shape and its existing counts. The 45 earlier checks are untouched |

### What the fix does, in code

`build_nodes` returned `{site: typ}` with the last row winning; on the real export the site rows are
ordered `t, site, typ`, so for the 91 codes that are both a plant and a load node the `NL` row is
last and the site became a load. It now returns `{site: [every typ in the file]}`; `build()`
merges the kinds across node files and applies `site_kind`, which prefers `PS` over `G` over
everything else. The register is read twice over: `capacities[(site, type)]` as before, and
`generators[site]`, the sum of `cap_mw` over the site's `G`/`PS` rows with the first non-empty
region.
`build_sites` takes the summed capacity and region for a generator-kind site, and the register row
for its own kind otherwise; the crosswalk gates and the `sites.json` shape are unchanged. The
`NL` rows still supply `lmp`/`mw` for such a site's node column — see "What was not changed".

### Measured on the orchestrator's real inputs

Both builders were run over the same `.local/grid-snapshot/` and `.local/geo/` this worktree holds
(ignored, read-only; the crosswalk's own mtime is 2026-10-14T01:38), in-process through
`.local/scratch/dual_control.py` (ignored evidence, not a repository test):

| | old builder (`3bb03c7`) | new builder |
|---|---|---|
| `sites` | total 617, located 21, placeholder 596 | total 617, located **37**, placeholder 580 |
| `gates` | capacity 16, capacity_unstated 15, no_grid_for_province 1 | **capacity 0**, capacity_unstated 15, no_grid_for_province 1 |
| `site_kinds` | absent | G 330 total / **36 located**, NL 286 / 0, PS 1 / 1 |
| located sites whose `k` is a generator kind | 10 | 37 |
| `contract` | 7 files, 0 violations | 7 files, 0 violations |

`08PEDC` (the event site) reads `k=G, cap=317, p=plant` instead of `k=NL, cap=0`; `01SUAL`
(1200), `03ILIJAN` (1200) and `01GNPD` (1336) likewise carry their register capacity and are
located. The two builders' `sites.json` entries differ for exactly the 91 dual-listed generator
codes and in exactly the fields `cap, k, lat, lon, name, p`; every differing code is a
dual-listed generator (`old k=NL`, `new k=G|PS`), and **no other output file differs** — the
contract, the other six files and the 11 crosswalk rows that do not change (ten single-kind
sites and `03KAL`) are untouched.

One correction to the finding's counts, taken from that measurement rather than from the table:
of the 38 crosswalk rows, 27 are dual-listed with the load row last (16 placeholders, now located;
11 already placed by the blank-capacity path but drawn as `NL` with 0 MW — `08PEDC` and `01GNPD`
are in that second group, so "not located" is true of their generator reading, not of their row).
The 28th dual-listed row, `03KAL` (`NL`+`PS`), has the `PS` row last, so the old builder already
read it as `PS`/729 MW; nothing changes for it. The finding's "21 located, only 10 of them
generators" reproduces exactly.

### Negative control

`.local/scratch/dual_control.py` loads the pre-fix builder from `git show
3bb03c7:scripts/grid/build_data.py` and runs the offline checks against it in-process:

```
the whole file on the pre-fix builder: ran 48, failures=2 errors=1
BuildTests on the pre-fix builder: ran 23, failures=2 errors=1
  RED test_a_dual_listed_site_takes_the_generator_kind_and_capacity
  RED test_a_site_listed_with_its_own_load_keeps_the_generator_kind
  RED test_the_report_counts_sites_by_kind
  test_a_dual_listed_site_takes_the_generator_kind_and_capacity ->  : the generator kind wins over the site's own load
  test_a_site_listed_with_its_own_load_keeps_the_generator_kind -> + NL
  test_the_report_counts_sites_by_kind -> KeyError: 'site_kinds'
```

The old builder's first failure message is that kind assertion (`'PS' != 'G'` truncated to the
message), the second its `k` assertion (`expected 'G'`, received `+ NL`), the third the absent
report key.

Exactly the three new checks are red on the pre-fix builder; the other 45 checks, the earlier 45
of them included, pass there — so none of them was weakened to accommodate the fix.

### Tests (45 -> 48 in the file, 596 -> 599 in the suite)

- `test_a_dual_listed_site_takes_the_generator_kind_and_capacity` — `08PEDC` priced as `PS`, `G`
  and `NL` (the load row last, as the export orders it) with register rows 302 + 15 + 0: the site
  reads `PS` (the preference over `G` *and* `NL`), `cap` 317 (the sum, not the preferred row's 302
  and not the 0 MW load row), locates at the crosswalk position, and `site_kinds` reports PS 1/1.
- `test_a_site_listed_with_its_own_load_keeps_the_generator_kind` — `04GEN` priced as `G` and
  `NL`: `k` is `G`, `cap` the register's 400 MW, and the row still stays a placeholder on its own
  100 MW public capacity — the gate is not loosened, only the capacity it compares.
- `test_the_report_counts_sites_by_kind` — the fixture's own report carries all three kinds with
  their located counts.
- No assertion was deleted, skipped or weakened anywhere in the file.

### Commands and results (this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 48 tests in 0.519s  OK   (45 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 599 tests in 10.021s  OK (skipped=7)
                                                          #   (596 before)
/usr/bin/python3 scripts/repo.py check                   # PASS (306 Markdown files, 1,618 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # exit 1, one path: .gitignore (see below)
/usr/bin/python3 scripts/plan.py scope GRID-1 cd1fa92    # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 .local/scratch/dual_control.py          # the negative control and the diff above
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
    # exit 0; contract {files 7, violations []}; sites {total 5, located 1, placeholder 4}
    # site_kinds {G {4, 1}, NL {1, 0}, PS {0, 0}}; gates {prefix 1, capacity 1, ...}
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; intervals 2304
    # advisories {rows 350, parsed 350, refused 0}
    # sites {total 617, located 37, placeholder 580}
    # site_kinds {G {330, 36}, NL {286, 0}, PS {1, 1}}
    # gates {capacity 0, capacity_unstated 15, no_grid_for_province 1, prefix 0, ...}
    # gates_detail.no_grid_for_province: [{"site": "13SMC", "province": "Davao Occidental"}]
```

No `bq`, `docker`, model, credential, cloud or network call was made; both `--check` runs read
local files and wrote nothing.

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` exits 1 listing exactly one path,
`.gitignore`, as in the two earlier reworks: it is the orchestrator's own commit `cd1fa92`, outside
GRID-1's owned paths, so this seat neither edits nor reverts it. Against that commit the scope is
clean, as printed above, and the working tree holds this rework's four files
(`scripts/grid/build_data.py`, `scripts/grid/README.md`, `tests/test_grid_data.py`,
`tests/fixtures/grid/README.md`).

### Acceptance (unchanged text, re-checked after this rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | both `--check` runs above (`files 7, violations []` on the fixture and on the real inputs) and the contract checks in `tests/test_grid_data.py`, all green |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` and the writer guard, untouched and green |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` and the release-audit test, untouched and green |

### What was not changed, and why

- **The node column's `lmp`/`mw` still come from the last row in `(t, site, typ)` order**, so for a
  dual-listed site those values are the load row's, as they were before this rework and as the
  reference builder [`preview_mkdata.py`](../grid-desk/reference/preview_mkdata.py) reads them.
  The finding corrects the kind and the capacity, not the series, and the same behaviour is already
  recorded as an open intent question in Rework 2. It is now visible in one more place: a located
  generator such as `08PEDC` draws its MW from its station-load rows. Changing it is an intent
  decision (which series a dual-listed site should show, or whether its two rows should be
  summed), not a silent choice here.
- No fixture file, contract, `Dockerfile`, `.dockerignore`, release file or export query changed;
  the register, node and crosswalk CSV shapes are untouched, so the corrections from Reworks 1 and
  2 are unaffected. The three kinds and the seven output files are the same shapes as before.
- `docs/work/tasks.json`: this task's state is unchanged (`in_progress`); only this task's own
  `note` is refreshed to describe this rework. No task was added and no acceptance text touched.
- `docs/work/PROGRESS.md`: one log row added; the task-table row already reads `in_progress`.

### Self-review note (author-run, not independent)

The finding's two halves are answered in code — the kind preference and the summed generator
capacity — and pinned by checks that fail on the pre-fix builder while the 45 earlier checks stay
green there. Every number above comes from a run in this worktree on this branch; nothing was
written first and measured later. The measurement also corrects two of the finding's counts
(27 rows read as `NL`, not 28; `08PEDC`/`01GNPD` placed-but-as-0 MW, not absent) rather than
restating them. No frozen contract, acceptance text or reviewer record was touched, and the appends
to this file added a section only. Remaining limits, stated: the mw/lmp tie-break above is left as
the open intent question; the orchestrator's crosswalk is the only real input this seat can check
(`.local/` is ignored and read-only here); and the container leg (`docker build`) is still not run
in this seat.

### Open items and exact next action

1. The orchestrator can re-run the bake: with this crosswalk 37 of 617 sites locate and all 37 are
   generators; the one `no_grid_for_province` row is still `13SMC` (Davao Occidental), unchanged by
   this rework; then `docker build`.
2. `.gitignore` in the default scope run, as in the previous reworks: either add it to
   `coordination_files` in `docs/work/tasks.json` or accept it as the orchestrator's own commit.
3. The `(t, site, typ)` series question above, if the page should show a dual-listed site's
   generation rather than its station load: an intent decision, not a change made here.

Exact next action: the independent review of this rework; then GRID-2, which depends on GRID-1.

### Post-commit re-run (2026-10-14)

Committed as `5461e53` on `task/GRID-1` (7 files, +348/-17), the packet and the state edits in the
same commit. Re-run on the committed tree, unchanged:

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 48 tests in 0.472s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 599 tests in 9.468s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (306 Markdown files, 1,628 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 cd1fa92    # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # exit 1, listing only .gitignore (as before)
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Orchestrator re-measure after rework 3 (2026-10-14, at `29e4838`)

Re-export against BigQuery matches the reference row for row (regions 6,912; nodes 204,192; hvdc 5,184; advisories 350). With the orchestrator's 38-row gated crosswalk: 37 sites located, 580 at pending positions; gates: capacity 0, capacity unstated 15 (passed by the clarified rule), one province-name miss in the crosswalk (the orchestrator's row, not the builder). Rebased onto the integration branch, which now carries the `build/` ignore line. Suite OK, `tests.test_grid_data` 48 OK, scope OK.

## Designated review 1 (GPT Sol, independent, commit `ab5e459`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...ab5e4599c18a`, including the 11 commits in `feat/h1-api-persistence..HEAD`. No files edited; working tree remains clean.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **no** | Fixture `--check` validated seven files and reported four placeholders; Git tracking and release-exclusion tests passed. However, the validator accepts an infinite node price with zero violations, so complete contract validation is not demonstrated. |
> | 2 | Changes within allowed paths | **yes** | Requested scope command printed `OK: all changed files inside GRID-1 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **yes** | Diff changes no frozen contracts or acceptance text. Existing image test adds the authorized snapshot source and retains a closed COPY allowlist; no skips added. |
> | 4 | No unapproved dependencies or external effects | **yes** | Builder uses existing Python modules; export’s read-only BigQuery calls are named in the packet. No new service or dependency introduced. |
> | 5 | Truthful mode labels | **yes** | Test fixtures are explicitly synthetic; snapshot tooling describes stored replay data. Packet distinguishes offline checks from orchestrator export measurements and leaves Docker verification unfinished. |
> | 6 | Unknowns remained unknown | **no** | Direct reproduction converts missing HVDC flow and congestion into `0` and `0`. |
> | 7 | Complete verification and handoff packet | **yes** | `docs/work/reviews/GRID-1.md` records interpreter, commands, results, unresolved node-series behavior, unfinished bake/container work and next action. Latest addendum corrects historical scope status. |
> | 8 | Consistent with direction and domain invariants | **no** | Station-load values are attributed to generator sites, and missing HVDC observations become asserted zero values. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/grid/build_data.py:205` | Rows sharing `(time, site)` overwrite each other across resource types, attaching station-load price/MW to a generator. | Direct reproduction with G=`32000 PHP/MWh, 317 MW` followed by NL=`1000 PHP/MWh, 5 MW` outputs `1000, 5`. Packet explicitly acknowledges this behavior for `08PEDC`. | Resolve the documented series-selection question with the intent owner; implement deterministic selection consistent with the site's kind and test both row orders. |
> | important | `scripts/grid/build_data.py:181` | Missing or malformed flow becomes measured zero; missing congestion becomes uncongested. | Direct reproduction with blank flow and flag outputs `flow: [0], congested: [0]`. | Preserve missing flow as null; reject unknown congestion inputs or obtain an approved representation for unknown status. Add missing-input checks. |
> | important | `scripts/grid/build_data.py:677` | Numeric type checking accepts non-finite values, allowing invalid JSON numbers through validation. | Injecting `float('inf')` into fixture node LMP produces `contract(files) == []`; serialization emits `Infinity`. | Reject non-finite numeric inputs and values; serialize with `allow_nan=False` and add a regression check. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_data -v` — **48 passed**.
> - `/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 49 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **599 tests, OK (skipped=7)**.
> - Fixture builder `--check` — **seven files, zero violations; one located, four placeholders**.
> 
> Docker build and a fresh cloud export were not run.
> 
> **Verdict: rework** — unresolved important defects misattribute node observations, invent zero values from missing inputs, and allow non-finite prices through contract validation.
**Verdict: rework.** Intent owner's decision on series selection: a site's series comes from rows of the site's kind (finding 3 rule: PS, then G, over NL); for a generator site, LMP is the mean over its generator resources and MW the sum of their schedules; its NL rows are ignored for that site. Test both row orders. Missing flow stays null (the page treats null as unknown); an unknown congestion flag stays null too (record it as null and count it in the report), never 0. Reject non-finite numbers in inputs and outputs and serialize with allow_nan=False. Address every blocking/important row above; dispose of minors explicitly.

## Rework 4 (2026-10-14, executor seat, after Designated review 1)

Read first, as the rework asked: this record. For the first time it carries a **real independent review** — *Designated
review 1 (GPT Sol, independent, commit `ab5e459`)*, verdict **rework** — whose findings are the three `important` rows
below, plus the intent owner's decision paragraph that ends it. (The three reworks before this one had to dispose of
orchestrator tables; this one does not, and nothing is inferred from them again.) This file is the task packet as well
as the review record — the brief lists it, `tasks.json`'s note and the PROGRESS row both point here — so this section is
**appended**: nothing above is edited, no verdict is written, and the reviewer's own text is not touched. All three
findings are inside the allowed paths (`scripts/grid/build_data.py`, `tests/test_grid_data.py`, the two READMEs that
describe the rules), and none needs an acceptance text or a frozen contract changed: the series rule, the null
representation and the finiteness rule are the intent owner's decisions, and `src/review`, `src/judgment`, `src/api` and
`docs/work/probe-bundle/` are untouched.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | Rows sharing `(time, site)` overwrite each other across resource types, attaching the station-load price/MW to a generator (`build_data.py:205`) | [`build_nodes`](../../../scripts/grid/build_data.py) now collects each `(t, site)` cell's rows by type and reads the cell through [`series_value`](../../../scripts/grid/build_data.py): a generator-kind site's LMP is the **mean** over its generator rows present at that interval and its MW the **sum** of their schedules, its `NL` rows ignored; a load site keeps its `NL` row. A cell the site's own kinds do not price is null, never the load row's value, and the site's kind is now read once for the whole snapshot (across day files), not per file. The old rule (the last row in `(t, site, typ)` order) is gone |
| important | Missing or malformed flow becomes measured zero; missing congestion becomes uncongested (`build_data.py:181`) | [`build_hvdc`](../../../scripts/grid/build_data.py) leaves a blank or malformed `flow_from` **null** (it was `num(...) or 0`) and a `congestion_flag` that is neither `Y` nor `N` — a blank included — **null** as well, never 0; both are counted per link in the new report block `hvdc` (`rows`, `flow_null`, `congestion_null`, `congestion_unknown`). The contract now accepts `null` in `congested[]` (0/1/null) and the module docstring, the lane README and the fixture README state the rule |
| important | Numeric type checking accepts non-finite values, allowing invalid JSON numbers through validation (`build_data.py:677`) | [`num`](../../../scripts/grid/build_data.py) reads `NaN`/`±inf`/`1e400` as missing (no non-finite number can enter a payload); [`dump`](../../../scripts/grid/build_data.py) serializes with `allow_nan=False`; the contract rejects any non-finite value it parses — the node matrices and located coordinates through the new `finite` helper, the outline coordinates through the same check (which also stops a `round(inf)` crash there from reaching the caller). A regression check injects `Infinity`/`-Infinity`/`NaN` into a file's bytes and requires the violation |

No minor row exists in the review's findings table. The three checklist answers of "no" (item 1: the infinite price
passing the validator; item 6: unknowns converted to zeros; item 8: station-load values on generator sites) are the same
three findings, so every finding in the review is disposed of above and there is no separate minor to name. The
review's own limits — `docker build` and a fresh cloud export not run — were already this packet's open items and stay
so, below.

### Measured on the orchestrator's real inputs

Both builders (the pre-fix one from `ab5e459` and the working tree's) were run over the same
`.local/grid-snapshot/` and `.local/geo/` this worktree holds (ignored, read-only; nothing written) through
`.local/scratch/review1_control.py` (ignored evidence, not a repository test and so not linked here):

| | pre-fix builder (`ab5e459`) | new builder |
|---|---|---|
| `contract` | 7 files, 0 violations | 7 files, **0 violations** |
| `sites` | total 617, located 37, placeholder 580 | total 617, located 37, placeholder 580 (unchanged) |
| `gates` | capacity 0, capacity_unstated 15, no_grid_for_province 1 | unchanged |
| `hvdc` report | absent | MINVIS1 and VISLUZ1 each 2,304 rows, `flow_null` 0, `congestion_null` 0, `congestion_unknown` 0 |
| output files that differ | — | **only `nodes-2026-09-21.json`** (1,856,261 bytes): 10,640 LMP cells and 18,299 MW cells over **86 site codes**, every one of them a generator-kind site, no other code touched |
| example, first interval | `08PEDC` `lmp 10405`, `mw -54.8` (its station-load row) | `08PEDC` `lmp 10297`, `mw 147.4` (its generator row) |

The 92 dual-listed codes explain the 86: five carry a generator row and a load row whose price and schedule agree at
every one of the 288 intervals (`01MASIWA`, `01PASBUSOL`, `03TGPP`, `05CARMEN`, `06BBGPP`), so their series is unchanged,
and `03KAL` (`NL`+`PS`) was already read from its `PS` row because that row is last in the export's order. On this data
— the orchestrator's re-export, complete rows, flags all `Y`/`N` — the new HVDC rule and the finiteness rule change no
byte; they are the guard for the blank and malformed cases, which the fixture variants exercise.

### Negative control

The whole test file, run against the pre-fix builder loaded from `git show ab5e459:scripts/grid/build_data.py`:

```
the whole file on the pre-fix builder: ran 56, failures=15 errors=2
  the 8 red checks are exactly this rework's new ones:
  test_a_generator_site_means_its_prices_and_sums_its_schedules -> + [1000] : (300 + 200) / 2
  test_a_missing_hvdc_value_stays_null_and_is_counted
  test_a_non_finite_input_reads_as_missing -> OverflowError: cannot convert float infinity to integer
  test_a_site_series_comes_from_its_kinds_rows_whichever_order -> + [32000, 1000, 1000]
  test_hvdc_congestion_is_0_1_or_null -> + ['hvdc.json: links.MINVIS1.congested[0] is None']
  test_non_finite_numbers_are_refused -> AssertionError: ValueError not raised
  test_num_reads_non_finite_values_as_missing -> AssertionError: inf is not None
  test_the_hvdc_report_is_empty_when_every_row_states_its_values -> KeyError: 'hvdc'
```

The series failure prints `[32000, 1000, 1000]`: on the pre-fix builder the interval whose generator row comes first
reads `32000` (that row is last) and the two intervals whose load row comes last read `1000` — the finding's own
mechanism, in both row orders. The other 48 checks pass on the pre-fix builder, so none of them was weakened or
retargeted to accommodate the fix.

### Tests (48 -> 56 in the file, 599 -> 607 in the suite)

- `test_a_site_series_comes_from_its_kinds_rows_whichever_order` — `04GEN` priced as `G` and `NL` with the load row
  first at one interval and last at the next: both read `32000`/`317.0`; the third interval prices nothing on the
  site's kind and is `null` even though the load row carries `1000`/`5`. Both row orders are built in one file.
- `test_a_generator_site_means_its_prices_and_sums_its_schedules` — `PS 300/100` and `G 200/50` and an `NL` row at one
  interval: the cell is `250` (the mean) and `150.0` (the sum), not the load row and not a last-row reading.
- `test_a_missing_hvdc_value_stays_null_and_is_counted` — a blank flow, a blank flag, a flag the copy does not use and
  an absent row: each unknown is `null` (never 0) and the `hvdc` report block counts them per link (rows 3/4,
  `flow_null` 2/0, `congestion_null` 2/1, `congestion_unknown` 1/1); the contract is clean.
- `test_the_hvdc_report_is_empty_when_every_row_states_its_values` — the fixture's complete rows: no nulls, no unknowns.
- `test_a_non_finite_input_reads_as_missing` and `test_num_reads_non_finite_values_as_missing` — `inf`, `-inf`,
  `Infinity`, `nan`, `1e400` in a CSV or handed to `num` read as missing; the serialized bytes carry no
  `Infinity`/`NaN`.
- `test_non_finite_numbers_are_refused` (contract) — `dump` raises on a non-finite value and a file whose bytes carry
  `Infinity`/`-Infinity`/`NaN` in a node cell is a violation naming the cell.
- `test_hvdc_congestion_is_0_1_or_null` (contract) — a null passes, a string does not.

The four existing tests that exercised the dual-listing variant and the hvdc shape are untouched and still green; no
assertion was deleted, skipped or weakened anywhere in the file.

### Commands and results (this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 56 tests in 0.688s  OK   (48 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 607 tests in 10.940s  OK (skipped=7)  (599 before)
/usr/bin/python3 scripts/repo.py check                   # PASS (315 Markdown files, 1,695 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 .local/scratch/review1_control.py       # the negative control and the diff above
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
    # exit 0; contract {files 7, violations []}; sites {total 5, located 1, placeholder 4}
    # hvdc {MINVIS1 {rows 4, flow_null 0, congestion_null 0, congestion_unknown 0}, VISLUZ1 ...}
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; intervals 2304
    # advisories {rows 350, parsed 350, refused 0}; sites {total 617, located 37, placeholder 580}
    # gates {capacity 0, capacity_unstated 15, no_grid_for_province 1, coordinates 0, precision 0, prefix 0}
    # hvdc {MINVIS1 and VISLUZ1: rows 2304, flow_null 0, congestion_null 0, congestion_unknown 0}
```

`scripts/grid/export.sh` and the fixture CSVs are unchanged in this rework, so no `bash -n` and no re-export was needed;
the suite's own export-check tests run the script's `--print-sql` path with a stubbed `bq` and stay green. No `bq`,
`docker`, model, credential, cloud or network call was made; both `--check` runs read local files and wrote nothing.

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` now prints **OK** — the `.gitignore` item the two earlier
reworks recorded is closed: the orchestrator's re-measure note says the branch was rebased onto the integration branch,
which carries the `build/` ignore line, so no path outside GRID-1's allowed set is in the range any more. (Against the
old `cd1fa92` base the command is not meaningful after the rebase — it lists the whole integration history.) The
working tree holds this rework's seven files: `scripts/grid/build_data.py`, `scripts/grid/README.md`,
`tests/test_grid_data.py`, `tests/fixtures/grid/README.md`, this record, `docs/work/PROGRESS.md` and
`docs/work/tasks.json`.

### Acceptance (unchanged text, re-checked after this rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | both `--check` runs above (`files 7, violations []` on the fixture and on the real inputs) and the contract checks in `tests/test_grid_data.py`, all green — including the new one that a non-finite value is a violation |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` and the writer guard, untouched and green |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` and the release-audit test, untouched and green |

### What was not changed, and why

- **`scripts/grid/export.sh` and the fixture CSVs are untouched.** The queries, the CSV contract and the crosswalk
  gates are the previous reworks' corrections and are unaffected by this one; no re-export or fixture change was
  needed to answer the review.
- **The seven output files keep their shapes**, with the two widenings the owner's decision fixes: `congested[]` may
  now be null where the flag is unknown, and a node cell now carries the site's own-kind reading (null where that kind
  states none). `regions.json`, `sites.json`, `advisories.json`, `events.json` and `ph.geojson` are byte-identical to
  the pre-fix builder's on the real inputs.
- **The baked nodes file deliberately deviates from the design template's copied snapshot** for the 86 dual-listed
  codes: the template's copy carries whichever row the scratch builder's last-row rule read. That file is the
  orchestrator's bake, not this task's output; the orchestrator's re-bake after this rework produces the owner's rule,
  and GRID-2 reads whatever is baked.
- No fixture, `Dockerfile`, `.dockerignore`, release file or frozen contract changed; no test weakened, skipped or
  deleted.
- `docs/work/tasks.json`: this task's state is unchanged (`in_progress`); only this task's own `note` is refreshed to
  describe this rework. No task was added and no acceptance text was touched. `docs/work/PROGRESS.md`: one log row
  added; the task-table row already reads `in_progress`.

### Self-review note (author-run, not independent)

All three important findings are answered in code and pinned by executed checks that fail on the reviewed commit
`ab5e459` for the finding's own reason (the series check in both row orders, the blank flow/flag staying null with the
report counts, the non-finite input/contract/serializer trio); the 48 earlier checks pass on that same pre-fix builder,
so none of them was weakened to accommodate the fix. Every number above comes from a run in this worktree on this
branch; nothing was written first and measured later. The intent owner's decision paragraph is implemented as written,
including "test both row orders" and "never 0" for unknown HVDC values. No frozen contract, acceptance text or
reviewer text was touched, and the append to this file added a section only. Remaining limits, stated: the container
leg (`docker build`), the fresh cloud export comparison and the owner's crosswalk are the orchestrator's, as before;
the 15 blank-capacity rows, the one `no_grid_for_province` row (`13SMC`, Davao Occidental) and the 16 stated-but-
outside rows are unchanged by this rework; and the real-input HVDC data states every value, so the new null rule is
proved on the fixture variants only.

### Open items and exact next action

1. The orchestrator re-runs the bake (the nodes file changes for 86 dual-listed codes, by the owner's rule) and then
   `docker build`, and can compare the HVDC counts: both links 2,304 in-window rows, no nulls and no unknown flags on
   the current export.
2. The 15 blank-capacity rows and the one `no_grid_for_province` row (`13SMC`, Davao Occidental) are as Rework 2 left
   them; the 16 stated-but-outside rows stay placeholders by the gate's intent.
3. GRID-2's page must serve `/grid-data/` from the directory the image carries (`src/grid/grid-data/`); its design file's
   `DATA = '/grid-data/'` is unchanged. The design now receives nulls where an HVDC value is unknown and the
   generator-kind series in the node matrices, both by the owner's decision.

Exact next action: the independent review of this rework; then GRID-2, which depends on GRID-1.

### Post-commit re-run (2026-10-14)

Committed as `54abc64` on `task/GRID-1` (7 files, +457/-50), the packet and the state edits in the same commit. Re-run
on the committed tree, unchanged (the `repo.py` link count grew as this section's own links and the PROGRESS row
landed):

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 56 tests in 0.654s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 607 tests in 16.238s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (315 Markdown files, 1,702 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; sites {total 617, located 37, placeholder 580}
    # hvdc {MINVIS1 and VISLUZ1: rows 2304, flow_null 0, congestion_null 0, congestion_unknown 0}
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Designated review 2 (GPT Sol, independent, commit `2af6d37`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...2af6d3771906`, including the commit log and task packet. No files edited; working tree remains clean.
> 
> | # | Checklist item | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **no** | Both fixture and real-input `--check` validate seven files; placeholder reports, Git-tracking checks and release-exclusion checks pass. However, the reproductions below produce contract-valid output despite unsupported capacity or a failed location gate. |
> | 2 | Changes within allowed paths | **yes** | Requested scope command prints `OK: all changed files inside GRID-1 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **yes** | Diff changes no frozen contract or acceptance text. The image test adds the authorized COPY source while retaining a closed allowlist. |
> | 4 | No unapproved dependencies or external effects | **yes** | Builder uses stdlib and the existing DATA-1 reader. BigQuery export calls are explicitly named in the packet. |
> | 5 | Truthful mode labels | **yes** | Fixtures are labelled synthetic; snapshot tooling describes replay. Packet identifies Docker verification as unfinished. |
> | 6 | Unknowns remained unknown | **no** | A missing register entry becomes `cap: 0`; malformed stated public capacity becomes “unstated” and permits location. |
> | 7 | Complete verification and handoff packet | **yes** | Packet records interpreter, commands, results, rework dispositions, unfinished bake/container work and exact next actions. |
> | 8 | Consistent with direction and domain invariants | **no** | The capacity fallbacks contradict “unknown stays unknown” and allow an unvalidated crosswalk match. |
> 
> Findings are unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/grid/build_data.py:416` | Every failed numeric parse receives the blank-capacity exemption, bypassing the ±25% location gate. | In-memory fixture reproduction changes `04GEN`’s public capacity from `400` to `"400 MW"` against registered `100 MW`. The site becomes located, `capacity_unstated` increments, and `contract()` returns `[]`. | Distinguish blank from nonblank invalid input. Reject or retain a placeholder for malformed stated capacity; add a regression check. |
> | important | `scripts/grid/build_data.py:394` | Missing registered capacity becomes an asserted zero. Line 487 also converts blank or malformed register capacity to zero. | In-memory reproduction removes `08PEDC`’s register mapping: output contains `cap: 0`, and the otherwise unchanged fixture passes `contract()` with `[]`. | Refuse missing or invalid register capacity with a named input error rather than substituting zero; test missing, blank and malformed values. |
> 
> Executed successfully:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_data -v` — **56 tests, OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **633 tests, OK (skipped=7)**
> - `/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence` — **OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> - Fixture and default real-input `build_data.py --check` — **seven files, zero reported violations**; respectively **4** and **580** placeholders.
> 
> Neither finding occurs in the current real inputs. Docker build and cloud export were not run.
> 
> **Verdict: rework — two unresolved important findings allow unsupported capacity values or unvalidated locations into contract-valid output.**
**Verdict: rework.** Blank public capacity passes (rule unchanged); a nonblank value that does not parse as a number keeps the row a placeholder and is counted as capacity_malformed. Registered capacity: a generator or pumped-storage site (G, PS) with a missing, blank or malformed register value is a named input error (the build stops); a load-node site (NL) has no registered capacity by nature and carries cap: null, never 0. Tests for each case. Address every blocking/important row above; dispose of minors explicitly.

## Rework 5 (2026-10-14, executor seat, after Designated review 2)

Read first, as the rework asked: this record. It carries a **real independent review** —
*Designated review 2 (GPT Sol, independent, commit `2af6d37`)*, verdict **rework** — whose
findings are the two `important` rows disposed below, plus the intent owner's decision
paragraph that ends it. The review's findings table has **no minor rows** (its three "no"
checklist answers — items 1, 6 and 8 — are the same two findings), so every row of the
review is disposed of here and there is no separate minor to name. All three earlier
reworks had to dispose of orchestrator tables; this one does not, and nothing is inferred
from them again. This file is the task packet as well as the review record — the brief
lists it, `tasks.json`'s note and the PROGRESS row both point here — so this section is
**appended**: nothing above is edited, no verdict is written, and the reviewer's text is
not touched. Both rows are inside the allowed paths (`scripts/grid/build_data.py`,
`tests/test_grid_data.py`, the two READMEs that state the rules), and neither needs an
acceptance text or a frozen contract changed: `src/review`, `src/judgment`, `src/api` and
`docs/work/probe-bundle/` are untouched.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | Every failed numeric parse of the crosswalk's public capacity received the blank-capacity exemption, bypassing the ±25% location gate (`build_data.py:416`) | [`build_sites`](../../../scripts/grid/build_data.py) reads the cell as text first: a blank keeps the unchanged rule — located, counted `capacity_unstated` — but a **nonblank value that does not read as a number** keeps the row a placeholder and is counted apart as `gates.capacity_malformed`; the blank exemption is never inherited by an unreadable value |
| important | Missing registered capacity became an asserted zero (`build_data.py:394`), and `build_data.py:487` read a blank or malformed register value as 0 as well | The register no longer defaults: a `G`/`PS` row whose `cap_mw` is blank or malformed stops the build by name as it is read (exit 2), and a site the snapshot prices as `G`/`PS` with **no generator row at all** stops it in [`build_sites`](../../../scripts/grid/build_data.py) — both named `BuildInputError`s, never a 0. A non-generator (load-node) site never reads the register for capacity and carries `cap: null`; the contract now pins that both ways (a `G`/`PS` site with null, or another kind with a number, is a violation) |

Two decisions beyond the finding's letter, taken from the owner's decision and stated here
rather than made quietly:

- **A stated public capacity with no registered capacity to check it against fails closed.**
  The owner fixes the NL output (`cap: null`) but not this gate branch; with no register
  value the ±25% test has nothing to compare, and the established rule for an unanswerable
  gate is fail closed (the unknown-province precedent), so the row stays a placeholder,
  counted as `gates.capacity_unregistered`. A blank public capacity on the same row still
  locates (`capacity_unstated`), as the unchanged blank rule says.
- **Register strictness is per row, not per snapshot member.** Every `G`/`PS` row in
  `sites.csv` must state a finite `cap_mw` — the check runs as the register is read, so a
  bad row stops the build whether or not the site is priced in this snapshot. The register
  is the same data the event review's assumption value reads, so a blank generator capacity
  is refused anywhere in the file. Measured on the orchestrator's register: 709 rows, none
  bad.

One wording note on the finding: it reproduces with "public capacity from `400` to `"400 MW"`
against registered `100 MW`" — the fixture's 04GEN has register 400 and public 100, so the
two numbers are transposed; the mechanism is unchanged, and the new check states `400 MW`,
so the refused value is one that *would have passed* the tolerance had it parsed.

### Tests (56 -> 60 in the file, 633 -> 637 in the suite)

- `test_a_malformed_public_capacity_stays_a_placeholder` — 04GEN `"400 MW"` (the finding's
  own reproduction): placeholder, `capacity_malformed` 1, `capacity_unstated` 0, contract
  clean; then 08PEDC with `N/A`, `300 MW` and `1e400` (non-finite, hence unreadable) —
  placeholder each time, while 04GEN's genuinely stated `400` still locates inside the gate.
- `test_a_site_without_a_registered_capacity_cannot_pass_the_gate` — 08PLACE (kind `NL`): a
  stated `5` keeps the placeholder and is counted `capacity_unregistered` (cap null); the
  same row blank locates with its name and `cap: null`, counted `capacity_unstated`.
- `test_a_load_node_site_carries_no_registered_capacity` — the fixture's 08PLACE reads
  `cap: null` (was 0), the contract accepts it, and a blank NL register value is not an
  error and still reads null (only generator rows must parse).
- `test_a_missing_or_invalid_generator_register_value_stops_the_build` — five variants of
  08PEDC's register: no rows at all (the finding's own reproduction), only its NL row,
  blank `cap_mw`, malformed `cap_mw`, non-finite `1e400`; each raises `BuildInputError`
  naming the site.
- `test_site_rules_are_checked` grows two assertions (no assertion removed): a `G` site
  with `cap: null` is a violation, and an `NL` site carrying a capacity is a violation
  ("only a generator site has a register") — the contract pins "null, never 0" both ways.
- `test_the_crosswalk_gates_turn_failing_rows_into_placeholders` expected dict gains the
  two new zero buckets, and the helper `build_with_local_files` is split into `local_files`
  (returning the paths) plus the same build helper, so a test that expects refusal can call
  the builder itself; the four tests that used it are untouched and green.

### Negative control

`.local/scratch/review2_control.py` (ignored evidence, not a repository test and so not
linked here) loads the pre-fix builder from `git show 2af6d37:scripts/grid/build_data.py`
and runs the whole updated file against it:

```
the whole file on the pre-fix builder: ran 60, failures=10 errors=0
  RED test_a_load_node_site_carries_no_registered_capacity -> AssertionError: 0 is not None : a load node never reads an asserted 0
  RED test_a_malformed_public_capacity_stays_a_placeholder -> + municipality
  RED test_a_missing_or_invalid_generator_register_value_stops_the_build (register='no rows at all') -> AssertionError: BuildInputError not raised
  RED test_a_missing_or_invalid_generator_register_value_stops_the_build (register='only the load row') -> AssertionError: BuildInputError not raised
  RED test_a_missing_or_invalid_generator_register_value_stops_the_build (register='blank') -> AssertionError: BuildInputError not raised
  RED test_a_missing_or_invalid_generator_register_value_stops_the_build (register='malformed') -> AssertionError: BuildInputError not raised
  RED test_a_missing_or_invalid_generator_register_value_stops_the_build (register='non-finite') -> AssertionError: BuildInputError not raised
  RED test_a_site_without_a_registered_capacity_cannot_pass_the_gate -> AssertionError: 0 is not None
  RED test_the_crosswalk_gates_turn_failing_rows_into_placeholders ->    'prefix': 1}
  RED test_site_rules_are_checked -> AssertionError: False is not true
```

Said plainly rather than counted as proof: **eight failures are the four new checks failing
for the findings' own mechanisms** — the `"400 MW"` row located (the assertion reads
`+ municipality`, the fixture's real precision), the missing/blank/malformed/non-finite
register values silently zeroed (no `BuildInputError` raised), the load node reading
`cap 0`, and the stated-capacity NL row carrying `cap 0` — and the **other two are the
updated expectations**, which cannot pass on a builder without the two new report buckets
and the new contract message. The remaining **50 checks pass on the pre-fix builder**, so
none of the earlier 56 was weakened to accommodate the fix.

### Measured on the orchestrator's real inputs

Both builders were run over the same `.local/grid-snapshot/` and `.local/geo/` this
worktree holds (ignored, read-only; nothing written):

| | pre-fix builder (`2af6d37`) | new builder |
|---|---|---|
| `contract` | 7 files, 0 violations | 7 files, 0 violations |
| `sites` / `site_kinds` | 37 located / 580 placeholder; G 330/36, NL 286/0, PS 1/1 | unchanged |
| `gates` | capacity 0, capacity_unstated 15, no_grid_for_province 1 | unchanged, plus `capacity_malformed` 0 and `capacity_unregistered` 0 |
| output files that differ | — | **only `sites.json`**: 286 site codes — every one a non-generator kind (all `NL`) — change `cap` 0 -> null; no other field of any entry, no kind, no located count differs |
| new input errors on this register | — | none: 0 blank/malformed `G`/`PS` rows of 709, and 0 of the 331 generator-kind sites without a generator register row |

The 16 blank public-capacity rows (15 locate as `capacity_unstated`; the 16th is `13SMC`,
which fails the province gate first) and the 22 stated rows are unchanged by this rework.

### Commands and results (this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 60 tests in 0.625s  OK   (56 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 637 tests in 10.844s  OK (skipped=7)
                                                          #   (633 at the reviewed commit — the review's
                                                          #   own count; the four new checks account for the rest)
/usr/bin/python3 scripts/repo.py check                   # PASS (317 Markdown files, 1740 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 .local/scratch/review2_control.py       # the negative control and the real-input diff above
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
    # exit 0; contract {files 7, violations []}; sites {total 5, located 1, placeholder 4}
    # gates {prefix 1, capacity 1, capacity_unstated 0, capacity_malformed 0,
    #        capacity_unregistered 0, coordinates 0, precision 0, no_grid_for_province 0}
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; intervals 2304
    # advisories {rows 350, parsed 350, refused 0}; sites {total 617, located 37, placeholder 580}
    # site_kinds {G {330, 36}, NL {286, 0}, PS {1, 1}}
    # gates {capacity 0, capacity_unstated 15, capacity_malformed 0, capacity_unregistered 0,
    #        coordinates 0, no_grid_for_province 1, precision 0, prefix 0}
    # gates_detail.no_grid_for_province: [{"site": "13SMC", "province": "Davao Occidental"}]
```

`scripts/grid/export.sh` and the fixture CSVs are unchanged in this rework, so no `bash -n`
and no re-export was needed; the suite's own export checks stay green. No `bq`, `docker`,
model, credential, cloud or network call was made; both `--check` runs read local files and
wrote nothing.

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` prints **OK** — the working tree
holds this rework's seven files: `scripts/grid/build_data.py`, `scripts/grid/README.md`,
`tests/test_grid_data.py`, `tests/fixtures/grid/README.md`, this record,
`docs/work/PROGRESS.md` and `docs/work/tasks.json`. (The `.gitignore` item of the earlier
reworks stays closed: the branch carries the integration branch's `build/` line.)

### Acceptance (unchanged text, re-checked after this rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | both `--check` runs above (`files 7, violations []` on the fixture and on the real inputs) and the contract checks in `tests/test_grid_data.py`, all green — including the two that pin the register rule in `sites.json` |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` and the writer guard, untouched and green |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` and the release-audit test, untouched and green |

### What was not changed, and why

- **`scripts/grid/export.sh`, the fixture CSVs, `Dockerfile`, `.dockerignore`, the release
  allowlist and the frozen contracts are untouched.** The queries and the CSV contract are
  the earlier reworks' corrections and are unaffected by this one.
- **The seven output files keep their shapes.** `sites.json` widens only the `cap` of
  non-generator kinds (0 -> null, the owner's decision); the report gains two gate
  counters and no new block; `contract()` remains the same shape, tightened inside the
  `cap` rule.
- The 16 blank public-capacity rows, the 22 stated rows, the 37 located sites and the one
  `no_grid_for_province` row (`13SMC`, Davao Occidental) are unchanged by this rework.
- **GRID-2's page must treat `cap: null` for a load-node site** — the design receives the
  owner's rule, and the page should show no capacity figure (or its own unstated form)
  rather than a 0 MW. Recorded as an open item, not changed here.
- `docs/work/tasks.json`: this task's state is unchanged (`in_progress`); only this task's
  own `note` is refreshed to describe this rework. No task was added and no acceptance
  text was touched. `docs/work/PROGRESS.md`: one log row added; the task-table row already
  reads `in_progress`.

### Self-review note (author-run, not independent)

Both findings are answered in code and pinned by executed checks that fail on the reviewed
commit `2af6d37` for the finding's own reasons — eight failures across the four new checks
— while the other 50 checks pass there, so none of the earlier 56 was weakened; the two
remaining reds are disclosed as updated expectations, not counted as proof. Every number
above comes from a run in this worktree on this branch; nothing was written first and
measured later. The owner's decision paragraph is implemented as written, including "never
0" and "tests for each case"; the two decisions beyond its letter (fail closed with
`capacity_unregistered`, per-row register strictness) are flagged above rather than buried.
No frozen contract, acceptance text or reviewer text was touched, and the append to this
file added a section only. Remaining limits, stated: the container leg (`docker build`),
the re-bake and the cloud export are the orchestrator's, as before; the real register
contains none of the bad-value cases, so the new input errors are exercised on the fixture
variants only; and the fail-closed rule cannot be exercised by the current real crosswalk
(all 38 rows are generator-kind codes).

### Open items and exact next action

1. The orchestrator re-runs the bake (only `sites.json` changes: 286 load-node sites read
   `cap: null`) and then `docker build`.
2. GRID-2 renders `sites.json`: a load-node site now carries `cap: null` and the page must
   show no capacity for it rather than a 0 MW figure.
3. The 16 blank-capacity rows and the one `no_grid_for_province` row (`13SMC`, Davao
   Occidental) are as Rework 2 left them; if the source values are right and the register
   wrong for those sites, that is an intent question, not a change to make here.

Exact next action: the independent re-review of this rework; then GRID-2, which depends on
GRID-1.

### Post-commit re-run (2026-10-14)

Committed as `09e6e9c` on `task/GRID-1` (7 files, +424/-37), the packet and the state edits
in the same commit. Re-run on the committed tree, unchanged:

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 60 tests in 0.560s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 637 tests in 9.738s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (317 Markdown files, 1740 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; sites {total 617, located 37, placeholder 580}
    # gates {capacity 0, capacity_unstated 15, capacity_malformed 0, capacity_unregistered 0, ...}
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Designated review 3 (GPT Sol, independent, commit `7f69a6b`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...7f69a6b4e7bb`, including the branch log, task brief, intent, review packet and clean working tree. No files edited.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | yes | Fixture `build_data.py --check` validated 7 files with 0 violations and reported 4 placeholders. Executed repository tests checked Git tracking and release exclusion. These demonstrate the listed checks, with semantic defects below. |
> | 2. Changes confined to allowed paths | yes | `plan.py scope GRID-1 feat/h1-api-persistence` printed `OK`. |
> | 3. Frozen contracts, acceptance and tests preserved | yes | Diff changes no frozen contract or acceptance text. Existing test expectations change for the authorized image contents and null load-node capacity; no tests deleted or newly skipped. |
> | 4. No unauthorized dependency or external effect | yes | Builder uses existing modules and stdlib. BigQuery export is named in the packet; this review executed no cloud or model calls. |
> | 5. Mode labels truthful | yes | Fixture README labels synthetic inputs; scripts describe stored replay. Packet explicitly leaves Docker execution unverified. |
> | 6. Unknowns remain unknown | no | Missing generator schedules can become a numeric partial total; finding 2. |
> | 7. Packet contains verification and handoff | yes | Packet records interpreter, commands, results, re-bake and Docker limitations, and the next review action. |
> | 8. Consistent with intent and invariants | no | Resource-price averaging and image destination diverge from the recorded requirements; findings 1 and 3. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/grid/build_data.py:251` | Averages resource-type means with equal weight, producing an incorrect mean across generator resources. | Export uses `AVG(lmp)` grouped by type at `export.sh:135–141`. Executed reproduction: two G resources priced 0 and one PS resource priced 300 should average **100**, but builder returns **150**. Owner decision in `PROGRESS.md:294` requires the mean over generator resources. | Preserve resource counts or price sums through export and calculate the resource-weighted mean. Test unequal resource counts across G and PS. |
> | important | `scripts/grid/build_data.py:247` | Drops unknown schedules before summing, presenting a partial measurement as the site's scheduled MW. | Executed reproduction with G MW blank and PS MW 5 returns **5.0**. No completeness flag distinguishes it from a measured total. | Keep the total null, or refuse the input, when a contributing generator row has an unknown schedule. Test partially missing aggregates. |
> | important | `Dockerfile:39` | Copies data to a different directory from the specified serving default. | COPY targets `/app/src/grid/grid-data`; `docs/work/grid-desk/intent.md:107` specifies `/app/build/grid-data`. No configuration override aligns them. | Copy to the specified directory and verify the serving path against the image contents. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_data -v`: **60 tests, OK**.
> - `/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence`: **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests`: **637 tests, OK, 7 skipped**.
> - Repository check: **PASS**; plan check: **OK**.
> - Fixture `build_data.py --check`: **7 files, 0 violations**.
> 
> Real-data re-bake, BigQuery export and Docker build were not run.
> 
> **Verdict: rework** — unresolved important findings allow incorrect or unsupported numeric results and leave the image path inconsistent with the intent.
**Verdict: rework.** Yours: (1) resource-weighted generator mean: export the per-(t, site, type) price sum and resource count (or the per-resource rows) and divide once over the site's generator resources; test unequal counts across G and PS; (2) if any contributing generator row has an unknown schedule, the site's MW for that interval is null; test partial gaps. The Dockerfile path finding is resolved on the integration branch by the intent owner: the intent now names /app/src/grid/grid-data, as built; merge feat/h1-api-persistence to pick up that wording. The orchestrator re-runs the export. Address every blocking/important row above; dispose of minors explicitly.

## Rework 6 (2026-10-14, executor seat, after Designated review 3)

Read first, as the rework asked: this record. It carries a **real independent review** —
*Designated review 3 (GPT Sol, independent, commit `7f69a6b`)*, verdict **rework** — whose
findings are the three `important` rows below, plus the intent owner's decision paragraph that
ends it. The review's findings table has **no minor rows** (its three "no" checklist answers —
items 1, 6 and 8 — are the same three findings), so every row of the review is disposed of here
and there is no separate minor to name. This file is the task packet as well as the review
record — the brief lists it, `tasks.json`'s note and the PROGRESS row both point here — so this
section is **appended**: nothing above is edited, no verdict is written, and the reviewer's text
is not touched. All three rows sit inside the allowed paths (`scripts/grid/export.sh`,
`scripts/grid/build_data.py`, `tests/test_grid_data.py`, `tests/fixtures/grid/` and the two
READMEs that state the rules), and none needs an acceptance text or a frozen contract changed:
`src/review`, `src/judgment`, `src/api` and `docs/work/probe-bundle/` are untouched.

### Row-by-row disposition

| Severity | Finding | Fix |
|---|---|---|
| important | The builder averaged the per-type means with equal weight, so two `G` resources priced 0 and one `PS` resource priced 300 read **150** where the owner's rule requires the mean over the resources, **100** (`build_data.py:251`) | The export now carries each `(t, site, typ)` group's **price sum with its resource count** ([`export.sh`](../../../scripts/grid/export.sh): `SUM(lmp) AS lmp_sum`, `COUNT(lmp) AS lmp_n`), and [`series_value`](../../../scripts/grid/build_data.py) adds the sums over the site's generator rows and divides **once** over the resources stating a price — a type with two resources weighs twice a type with one. The `GROUP BY` is unchanged, so the export still writes one row per `(t, site, typ)` |
| important | An unknown schedule was dropped before summing, so a `G` group stating no schedule beside a `PS` group stating 5 read **5.0** — a partial total presented as the site's MW (`build_data.py:247`) | The export carries the schedule sum with its **stated and total resource counts** (`SUM(sched_mw) AS mw_sum`, `COUNT(sched_mw) AS mw_n`, `COUNT(*) AS resources`), and [`series_value`](../../../scripts/grid/build_data.py) returns **null** for the site's MW cell whenever any contributing group has `mw_n` short of `resources` (or states no sum at all) — never the stated rows' partial sum. The LMP cell stays measured where the prices are stated |
| important | `Dockerfile:39` copies to `/app/src/grid/grid-data` while the intent at the reviewed commit said `/app/build/grid-data` | No change: the owner's decision resolves the finding — the integration branch's intent now names `/app/src/grid/grid-data`, as built. This worktree's copy of the intent ([`intent.md:108`](../grid-desk/intent.md)) still carries the old wording, `docs/work/grid-desk/` is outside GRID-1's allowed paths and a merge is a stop condition for this seat, so the wording arrives with the orchestrator's merge of `feat/h1-api-persistence`. The existing check [`test_the_dockerfile_copies_the_baked_data_into_the_image`](../../../tests/test_grid_data.py) already pins the built destination (`./src/...`), and the image contract stays a closed set of COPY sources |

### Decisions beyond the finding's letter, stated rather than made quietly

- **The LMP denominator is the resources that state a price** (`lmp_n`), not the group's whole
  resource count: a resource whose price the copy does not state is not a zero price, and the
  pre-review `AVG(lmp)` ignored nulls the same way. The sum and its count travel together; a
  row that states one without the other (impossible from the query's own emission) reads as an
  unknown cell, never a partial mean.
- **The unknown-schedule rule reads a load-node group the same way.** The owner's sentence
  names a generator row; the same check runs on a load site's own `NL` row (a group whose
  `mw_n` is short of its `resources` reads null), which only makes explicit the pre-review
  behaviour that a blank schedule never became a number.
- **The CSV column contract between the export and the builder changed** (`t,site,typ,lmp,mw`
  → `t,site,typ,lmp_sum,lmp_n,mw_sum,mw_n,resources`), because "divide once" needs the sums,
  not the per-type means. The seven output files and their contract are unchanged in shape.
  Consequence, recorded rather than worked around: the **stored** real export in
  `.local/grid-snapshot/` predates the new columns and the builder now refuses it by name
  (`nodes_0921_5min.csv is missing column(s) lmp_sum, lmp_n, mw_sum, mw_n, resources`), so the
  orchestrator's re-export is required before the bake — the owner's decision says it will be
  re-run. `export.sh`'s header, the lane README and the fixture README state the new header.

### Tests (60 -> 63 in the file, 637 -> 640 in the suite)

- `test_the_generator_mean_is_weighted_by_resource_count` — the review's own reproduction:
  a `G` group of two resources summing 0 beside a `PS` group of one summing 300 reads `100`
  (not the equal-weight `150`); a second interval of one resource per type reads the plain
  mean `250`, where both rules agree.
- `test_a_contributing_unknown_schedule_nulls_the_site_mw` — the review's own reproduction:
  a `G` group with no stated schedule beside a `PS` group stating 5 reads **null**, never
  `5.0`; a two-resource group with one stated schedule is null too; the fully stated interval
  sums (`25.0`). The LMP stays measured throughout (one priced resource per group, so this
  check pins the schedule rule alone).
- `test_the_nodes_query_carries_the_price_sums_and_resource_counts` (ExportQueryTests) — the
  statement carries `SUM(lmp) AS lmp_sum`, `COUNT(lmp) AS lmp_n`, `SUM(sched_mw) AS mw_sum`,
  `COUNT(sched_mw) AS mw_n`, `COUNT(*) AS resources`, keeps `GROUP BY t, site, typ` and the
  `mkt_type = 'RTD'` filter, and no longer carries `AVG(lmp)` — the equal-weight artifact.
- The fixture's node CSV and the four checks that write their own node rows
  (`with_dual_listing`, the series-order check, the mean/sum check, the non-finite check) are
  re-expressed in the new row contract; their expectations are unchanged, and the fixture's
  groups are one resource each, so every earlier expected value stands. No assertion was
  deleted, skipped or weakened anywhere in the file.

### Negative control

`.local/scratch/review3_control.py` (ignored evidence, not a repository test). Function level,
on the review's own two inputs — the pre-fix builder from `HEAD` against the corrected one:

```
pre-fix builder  (HEAD): lmp 150  mw 5.0
corrected builder      : lmp 100  mw None
```

Reverting **one correction at a time** in the working builder and running the whole updated
test file against each reverted copy — exactly one check turns red per reverted rule, its own:

```
weighting reverted (mean of per-type means): ran 63, failures=1 errors=0
  RED test_the_generator_mean_is_weighted_by_resource_count
partial-schedule rule reverted (unknowns dropped): ran 63, failures=1 errors=0
  RED test_a_contributing_unknown_schedule_nulls_the_site_mw -> + [5.0, 25.0, 25.0]
```

The other 62 checks pass under both reverted copies, so none of the earlier 60 was weakened to
accommodate the fix. Two byte-identity checks close the loop:

```
the fixture, old builder + old CSV vs new builder + new CSV: files that differ: none
the real inputs, old builder vs new builder (converted node CSV): files that differ: none
```

The second line carries a stated limit: the stored export's columns hold no resource counts,
so the conversion reads each `(t, site, typ)` group as one resource — the only reading the
old columns support — and therefore reproduces the old per-type mean. It proves the new
contract runs on the real data shape and changes nothing else (37 located / 580 placeholders,
every gate and the 0 contract violations unchanged); the resource weighting itself becomes
measurable on the re-export, which carries the true sums and counts. On the stored export
26,496 cells (of 177,696) hold two types; no row has a blank `lmp` or `mw`, so the new
unknown-schedule rule changes no byte there — it is the guard for the blank and partial cases,
which the fixture variants exercise.

### Commands and results (this worktree, 2026-10-14, `/usr/bin/python3` 3.14.4, before the closing commit)

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 63 tests in 0.646s  OK   (60 before)
/usr/bin/python3 -m unittest discover -s tests           # Ran 640 tests in 10.599s  OK (skipped=7)
                                                          #   (637 before)
/usr/bin/python3 scripts/repo.py check                   # PASS (317 Markdown files, 1741 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
bash -n scripts/grid/export.sh                           # exit 0
/usr/bin/python3 .local/scratch/review3_control.py       # the negative control and the diffs above
/usr/bin/python3 scripts/grid/build_data.py --check \
  --snapshot tests/fixtures/grid/snapshot --geo tests/fixtures/grid/geo \
  --events tests/fixtures/grid/events.json \
  --nodes tests/fixtures/grid/snapshot/nodes_0921_5min.csv
    # exit 0; contract {files 7, violations []}; sites {total 5, located 1, placeholder 4}
    # site_kinds {G {4, 1}, NL {1, 0}, PS {0, 0}}; gates {prefix 1, capacity 1, ... 0}
/usr/bin/python3 scripts/grid/build_data.py --check --geo .local/geo --events scripts/grid/events.json
    # exit 2: .local/grid-snapshot/nodes_0921_5min.csv is missing column(s)
    #   lmp_sum, lmp_n, mw_sum, mw_n, resources — the stored export predates review 3;
    #   the orchestrator's re-export supplies them (the bake follows it)
/usr/bin/python3 scripts/grid/build_data.py --check --snapshot .local/nc-old3/real-converted \
  --geo .local/geo --events scripts/grid/events.json
    # exit 0; contract {files 7, violations []}; intervals 2304
    # advisories {rows 350, parsed 350, refused 0}; sites {total 617, located 37, placeholder 580}
    # site_kinds {G {330, 36}, NL {286, 0}, PS {1, 1}}
    # gates {capacity 0, capacity_unstated 15, capacity_malformed 0, capacity_unregistered 0,
    #        coordinates 0, no_grid_for_province 1, precision 0, prefix 0}
    # gates_detail.no_grid_for_province: [{"site": "13SMC", "province": "Davao Occidental"}]
```

No `bq`, `docker`, model, credential, cloud or network call was made; the two `--check` runs
read local files and wrote nothing.

**Scope.** `plan.py scope GRID-1 feat/h1-api-persistence` prints **OK** — the working tree
holds this rework's nine files: `scripts/grid/export.sh`, `scripts/grid/build_data.py`,
`scripts/grid/README.md`, `tests/fixtures/grid/README.md`,
`tests/fixtures/grid/snapshot/nodes_0921_5min.csv`, `tests/test_grid_data.py`, this record,
`docs/work/PROGRESS.md` and `docs/work/tasks.json`.

### Acceptance (unchanged text, re-checked after this rework)

| Acceptance item | Evidence |
|---|---|
| `build_data.py --check` validates every file against the contract | the fixture and converted-real `--check` runs above (`files 7, violations []` both) and the contract checks in `tests/test_grid_data.py`, all green |
| placeholder count reported | both runs print `sites {total, located, placeholder}` and the note; the check is a test |
| no data file tracked by Git | `RepositoryRules.test_no_data_file_is_tracked_by_git` and the writer guard, untouched and green |
| release export excludes `build/grid-data/` | `test_the_release_export_excludes_the_baked_data` and the release-audit test, untouched and green |

### What was not changed, and why

- **The Dockerfile is untouched** — the owner's decision resolves the path finding on the
  integration branch, as recorded above; nothing on this branch contradicts the built path.
- **`regions.json`, `hvdc.json`, `advisories.json`, `events.json`, `ph.geojson` and every
  non-node rule are untouched.** Only the node CSV contract and the two rules the review
  names changed; the fixture's JSON outputs are byte-identical to the pre-review builder's
  (the control's first diff line), and the real inputs' outputs likewise under the
  conversion.
- No frozen contract, acceptance text or reviewer text was touched; no test weakened, skipped
  or deleted.
- `docs/work/tasks.json`: this task's state is unchanged (`in_progress`); only this task's own
  `note` is refreshed to describe this rework. No task was added and no acceptance text was
  touched. `docs/work/PROGRESS.md`: one log row added; the task-table row already reads
  `in_progress`.

### Self-review note (author-run, not independent)

Both numeric findings are answered in the export contract and the builder and pinned by checks
that reproduce the review's own numbers and turn red — one each — when their rule is reverted,
while the other 61 checks stay green; the third finding is disposed of by the owner's decision
(no code change, the intent wording arrives with the orchestrator's merge). Every number above
comes from a run in this worktree on this branch; nothing was written first and measured later.
The two decisions beyond the finding's letter (the priced-resource denominator; the changed
CSV header and the re-export it forces) are flagged above rather than buried. Remaining limits,
stated: the resource weighting is measurable on real data only after the re-export; the stored
export's groups carry no counts; the container leg (`docker build`), the re-bake and the cloud
export are the orchestrator's; the 15 blank-capacity rows, the one `no_grid_for_province` row
(`13SMC`, Davao Occidental) and the 16 stated-but-outside rows are unchanged by this rework.

### Open items and exact next action

1. The orchestrator re-runs `bash scripts/grid/export.sh` (its `--print-sql` now shows
   `lmp_sum/lmp_n/mw_sum/mw_n/resources`), then the bake (`sites.json` from rework 5 and the
   nodes file from rework 4 and this one change for the 26,496 two-type cells if their types
   differ in resource count) and then `docker build`.
2. GRID-2 renders `sites.json` (`cap: null` for a load-node site) and the node matrices
   (`null` MW where a contributing schedule is unknown); `src/grid/` stays read-only here.
3. The 16 blank-capacity rows and the one `no_grid_for_province` row (`13SMC`, Davao
   Occidental) are as Rework 2 left them.

Exact next action: the independent re-review of this rework; then GRID-2, which depends on
GRID-1.

### Post-commit re-run (2026-10-14)

Committed as `62e1396` on `task/GRID-1` (9 files, +407/-69), the packet and the state edits in
the same commit. Re-run on the committed tree, unchanged (the `repo.py` link count grew from
1,741 to 1,749 as this section's own links and the PROGRESS row landed):

```sh
/usr/bin/python3 -m unittest tests.test_grid_data -v      # Ran 63 tests in 0.752s  OK
/usr/bin/python3 -m unittest discover -s tests           # Ran 640 tests in 14.174s  OK (skipped=7)
/usr/bin/python3 scripts/repo.py check                   # PASS (317 Markdown files, 1749 local links, 8 skills)
/usr/bin/python3 scripts/plan.py check                   # OK: 49 tasks, 7 gates
/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence
                                                         # OK: all changed files inside GRID-1 allowed paths
/usr/bin/python3 scripts/grid/build_data.py --check --snapshot .local/nc-old3/real-converted \
  --geo .local/geo --events scripts/grid/events.json     # exit 0; contract {files 7, violations []}
                                                         # sites {total 617, located 37, placeholder 580}
```

This addendum is the only change after that commit; nothing else in the tree was touched.

## Orchestrator re-measure after rework 6 (2026-10-14, at `8fecf61`)

Re-export against BigQuery: regions 6,912, nodes 204,192 (now with per-resource sums and counts), hvdc 5,184, advisories 350. `build_data.py --check` with the gated crosswalk: 37 of 617 located, contract violations none. Suite OK, `tests.test_grid_data` 63 OK, scope OK. The Dockerfile-path finding is resolved by the intent owner on the integration branch (the intent names `/app/src/grid/grid-data`, as built).

## Designated review (GPT Sol, independent, commit `398e5ab`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...398e5ab8c179`, including the commit log. No files edited; working tree remains clean.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Fixture and real-input `--check` each validated seven files with zero violations. Real report: 37 located, 580 placeholders. Executed repository tests verify no baked/export data tracked by Git and release exclusion of `build/grid-data/`. |
> | 2 | Changes stay within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope GRID-1 feat/h1-api-persistence` printed `OK: all changed files inside GRID-1 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff leaves the listed frozen contracts and acceptance text unchanged. The image-copy expectation changes to cover the authorized snapshot copy; numeric regression checks were added. |
> | 4 | No effects or dependencies beyond the packet | **Yes.** Builder reads local files; export contains the named, bounded read-only BigQuery queries. No new runtime dependency or service added. |
> | 5 | Mode labels truthful | **Yes.** Fixture README explicitly labels invented test data synthetic; scripts and packet identify the real snapshot as historical replay. No live inference claimed. |
> | 6 | Unknowns remain unknown | **Yes.** Passing tests demonstrate null unknown schedules/HVDC values, refusal of missing generator capacity, malformed-capacity placeholders, and rejection of non-finite output. |
> | 7 | Packet records verification and handoff | **Yes.** `docs/work/reviews/GRID-1.md` records interpreter, commands, results, rework dispositions, remaining bake/container work, and next action. |
> | 8 | Consistent with product and domain invariants | **Yes.** Existing WESM sources are reused, timestamps retain the specified civil-time semantics, and the change adds replay data without changing assumptions or execution authorization. |
> 
> Executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_data -v` — **63 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **640 tests, OK (7 skipped)**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**.
> - Requested scope command — **OK**.
> - Fixture and default real-input `build_data.py --check` — **exit 0**, seven files, zero violations each.
> 
> Findings: **None.** Docker build and deployed serving behavior were not demonstrated; neither is a listed GRID-1 acceptance check.
> 
> **Verdict: accept** — all four required acceptance items were demonstrated, and no blocking or important finding remains.
**Verdict: accept.** Real export re-run by the orchestrator at 398e5ab: 37 of 617 located, contract clean.
