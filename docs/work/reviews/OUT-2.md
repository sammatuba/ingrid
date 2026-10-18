# OUT-2 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Item | Value |
|---|---|
| Task | OUT-2, the event study and the availability response |
| Branch | `task/OUT-2` |
| Commit under review | `dca37302` |
| Base | `971885b0` (origin/main, merged into the branch at `31e749cd`) |
| Reviewer | Claude Opus 5.5 in-session subagent. It is read-only and independent of the author (the executor seat). |
| Verdict | **rework** |

Every command ran in the worktree `.local/wt/OUT-2` with `/usr/bin/python3`. There was no network,
model or BigQuery call. The real final series `.local/price/lwap_final_hourly.csv` was read for counts
and its digest only. No value from it is in this record. `.local/price/outages_forced.csv` does not
exist: the capped export has not run.

### Commands and results

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` (full offline suite) | `Ran 2671 tests in 243.508s`, `FAILED (errors=1, skipped=115)`. The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: `ModuleNotFoundError: No module named 'pypdf'`. This is the known environment limit. OUT-2 touches no corpus file. There are no failures. |
| `/usr/bin/python3 -m unittest tests.test_price_response tests.test_price_baselines` | `Ran 139 tests in 16.795s`, **OK** |
| `/usr/bin/python3 scripts/plan.py scope OUT-2 971885b0` | `OK: all changed files inside OUT-2 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 602 Markdown files, 3846 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check 971885b0..HEAD` | clean |
| `sha256sum .local/price/lwap_final_hourly.csv`, and the same key in `.local/price/digests.json` | `3b3b0b66…bc19` for both. This equals the record. |
| `event_study.py --final .local/price/lwap_final_hourly.csv --series-only` | 184,036 rows, the same SHA-256. CLUZ, CVIS, CMIN and SYSTEM each have 46,009 hours from 2021-06-26 00:00 to 2026-09-25 23:00, and 41,617 of them have a baseline. This matches `event-study.md`. The 4,392 hours without one are the six administered months (183 days × 24). It printed no price. |
| A reviewer script in the scratch directory (outside the tree). It recomputes SYN_V03 (CVIS), SYN_L04 (CLUZ, crosses Sunday into Monday) and SYN_M02 (CMIN) from the raw fixture CSV rows. It uses its own baseline, billing-month, exclusion and quantile code and imports nothing from the runner. | Per event: 7.9728893678, 1.9715260935 and 4.9841527778. These equal `event_response` exactly, with 6 hours used each. CVIS cell from my quantiles: median 7.986104, p10 7.965934, p90 8.006734. These equal the record's cell and the `event-study.md` table. |
| The same script, `baseline_days(2026-02-15, 4, weekend=False)` for SYN_L04's Monday 00:00 hour | It includes 2026-02-16 to 2026-02-20, the Monday hour's own ISO week (finding 2) |
| A scratch fixture built by the committed generator with one more invented unit, `SYN_L02B`. It is 350 MW and trips with SYN_L02 over the same hours. The invented slope stays 2.0 per MW. | Each of the two events reports **3.9993** PHP/MWh per MW lost (finding 1) |
| Grep of `event_study.sql` against `12_outage_events.sql` | It reads only `grid-nowcast.grid_curated.outage_events`. The columns it reads (`run`, `resource_name`, `region_code`, `status`, `p_max`, `start_manila`, `end_manila`, `start_utc`, `end_utc`, `first_seen_manila`, `first_seen_utc`, `lead_hours`, `duration_hours`, `n_revisions`, `revision_no`) are all in the final SELECT of `12`. It has no write statement. |
| `grep -n -i stale` on `event-study.md` and `out-2.md` | One hit only: `out-2.md:71` quotes the rule itself. The two records are `docs/work` records, and `repo.py check` passes them. |

### What I checked against the brief

- **Basis (acceptance 1): met.** `read_final_series` (`scripts/price/event_study.py:116-145`) refuses a
  real-time file by its name and by its header. The runner has no real-time option. `BasisNeverMixes`
  instruments `open` and `Path.open` and shows that a whole run opens only the two exports. The level
  comes only from `series.row(hour).mean` of the final series (`event_study.py:301`). `validate`
  refuses another basis (`src/price/response.py:97-98, 132-133, 147-148`).
- **Baseline: implemented as stated, with one edge (finding 2).** It takes the same clock hour on days
  of the same weekday class, two ISO weeks before and two after, and leaves out the event week. It
  leaves out hours that overlap any forced outage in the export for the region (`affected_hours`
  floors the start and covers every hour before the end). It leaves out all six administered months,
  "mixed" months included, which is the conservative reading. It takes a plain mean and needs at least
  3 hours. My recomputation agrees with the runner exactly.
- **Measured hours, response, pooling: correct arithmetic.** Whole clock hours inside the outage, at
  most 6. The response is the mean of (price minus baseline) over those hours, divided by the MW lost.
  The median, p10 and p90 come from `scorecard.quantile` (linear interpolation, numpy's `linear`), with
  the count per region and size class. Every left-out event is counted by reason. The method is
  correct for one outage at a time. It is wrong when outages overlap (finding 1).
- **Exploratory threshold (acceptance 2, second half): met.** A cell is `small_sample` when its count
  is below `min_events_per_cell`, which defaults to 10 and is written in the record. `validate` refuses
  a cell that hides its small sample. `apply` refuses an exploratory cell with `EXPLORATORY_CELL`
  unless `allow_exploratory=True`, and then the label travels (`response.py:216-242`).
- **Reproducibility (acceptance 2, first half): proved on the fixture only.** Two builds give the same
  digest. The written file's SHA-256 equals the printed digest. Inputs are cited by path, rows and
  SHA-256. A digest record that does not match refuses the run (`verify_inputs` matches by file
  name, so the path keys in `.local/price/digests.json` work). The generator reproduces the committed
  fixture bytes.
- **No company value in the repository: met.** Every fixture value comes from `make_synthetic.py`
  (invented bases, sine shape, hash noise, `SYN_*` units). A test checks that the generator reproduces
  the committed bytes. From the real series the records carry only counts, dates of range and the
  digest. "16 of 319" is a count from `docs/work/outage-table-2026-10-17/record.md:20-22`.
- **Model card (acceptance 3, first half): met against the assumed fields (finding 7).** The method,
  inputs, sample, spread, basis and expectation are present and equal the record.
- **Existing assertions (acceptance 4): kept.** `tests/test_price_baselines.py` changes one line: the
  expected `src/price` file list gains `response.py`, so the stdlib assertion now also covers the new
  module. No live call.

### Findings

| # | Severity | Location | Bears on | Finding | Correction |
|---|---|---|---|---|---|
| 1 | **major** | `scripts/price/event_study.py:283-316` (`event_response`), `:323-351` (`run_study`) | Outputs and decision 12, "pooled per MW lost". Acceptance 2: the figures reproduce, but the real record would hold a biased number. | Each event takes the whole regional price change and divides it by its own MW. When two forced outages of 50 MW or more overlap in one region inside the measured hours, each takes the other's effect too. Multi-unit trips and grid disturbances do this. The pooled median is then biased upward by construction. My scratch pair (two 350 MW units over the same hours, invented slope 2.0) gives 3.9993 per MW for each event. The committed fixture has no overlapping events, so none of the 51 tests reaches this path. | Do one of these two. (a) Leave out an event whose measured hours overlap another forced event of the region, and count it under a stated reason such as `overlapping_outage`. (b) Merge the overlapping events of a region into one event: the summed MW, the earliest start, and the hours where both are out. Write the rule in `parameters`. Add a labelled fixture pair, built through `make_synthetic.py`, that recovers the invented slope, and keep the generator test. Update the fixture run in `event-study.md` if its numbers move. |
| 2 | minor | `scripts/price/event_study.py:297` (`event["start"].date()` passed as the event day), `:236-247` (`baseline_days`) | Brief: "surrounding weeks". The record's stated rule: "the event week excluded" (`event_study.py:432-437`, `event-study.md` parameter table). | The excluded week is the ISO week of the start day, not of each measured hour. An outage that starts late on Sunday measures its Monday hours against a baseline that includes that Monday's own ISO week. For SYN_L04 the Monday 00:00 hour draws from 2026-02-16 to 2026-02-20. Only the hour itself is left out, as an outage hour. | Key the week to each measured hour's own date, or leave out the ISO weeks of every measured hour. Add a test on SYN_L04. |
| 3 | minor (definition: forced) | `scripts/price/event_study.sql:36-41, 67, 76` | Brief: "status forced". Decision 12: "forced outage records". | The rule is "no run carried the same unit and start before that start", and the match is on the exact `(resource_name, start_manila)`. The table has no forced status, so this reading of the outage record (`record.md:47-53`, "the forced outages behind UC-01") is reasonable and is stated as hand-back 2. But a planned outage that DAP or WAP carried in advance, and whose actual RTD start differs from the planned start by minutes, forms a new group and is classed forced. Also, `known_at` is read (`event_study.py:192`) but nothing uses it, so the reporting lag is neither bounded nor reported. | Keep the rule for the real run. In the same run, count the events classed forced that have a same-unit record in any run carried before the start and overlapping in time, and report that share and the lag distribution (`lead_hours`) in `event-study.md`. If the share is material, tighten the rule to an overlap match in a later round. |
| 4 | minor (definition: MW lost) | `scripts/price/event_study.sql:54, 73-74` | Decision 12: "per MW lost" | Using `p_max` is the only size the table has, and hand-back 3 states its direction honestly: a derated or part-loaded unit is overstated, so the response per MW is understated. Not stated: `p_max` comes from one IEMOP list (snapshot 2026-09-11) and is applied to five years of events. | Keep it. Say "per MW of rated capacity (IEMOP list of 2026-09-11)" in the record's units text, the card method and `event-study.md`. |
| 5 | minor (definition: normalization) | `scripts/price/event_study.py:313-315`, `docs/work/desk-agent-and-book-2026-10-18/out-2.md:87` (hand-back 4) | Decision 12 and the brief: "per MW lost relative to regional demand" | The response is per MW lost, not per share of regional demand. This departs from the decision's words. The card says "divided by the MW lost", so the departure is stated, and the runner switches when a `demand_mw_mean` column exists. But hand-back 4 says the demand must come from PRICE-1's file. The register already lists a regional demand source: `RTD_Regional_Summaries`, family D, "used", read by `scripts/data/sql/02_intervals.sql` (`docs/work/data-register-2026-10-17/register.md:23`). A denominator is not a price level, so the never-mix rule does not forbid it. It would be a second export, outside this task's one-export cost line and the single-table SQL. | No executor change beyond the record. Correct hand-back 4 so that it names the existing source and states the choice for the orchestrator or the owner. Either accept per MW lost as the stated unit, or add a capped demand export per region and hour that is joined only as the denominator. |
| 6 | minor (condition) | `docs/work/desk-agent-and-book-2026-10-18/event-study.md:83-111` | Acceptance 2, first clause. Acceptance 3, second clause. The Outputs line for `event-study.md`. | The real export has not run, so these are **not yet proved**: (a) "every figure in the record reproduces from the two exports by digest" holds on the fixture only, and no real record exists; (b) "the BigQuery cost of the one export is written" still reads "to fill"; (c) the measurement record "with every number, its inputs by digest, the BigQuery cost" waits on the same run. The record says all of this honestly. | The orchestrator runs the dry run and the capped export, adds the export's digest to `.local/price/digests.json`, and runs the study with `--digests` **after** finding 1's fix. It then fills the "Real run" table, including bytes processed and billed. The SQL is not affected by finding 1, so the export can run now. Only the study over it waits. |
| 7 | minor (contract assumed; board R4 open) | `src/price/response.py:276-349`, `src/grid/models.js:9`, `response.py:31, 40-43, 294-296` | Acceptance 3: "in the MODELS contract fields" | The fields copy the four cards of `models.html` (`id`, `title`, `status_word`, `status`, `lines`, `figures` with `label`, `value`, `figure`, `record`, and `as_of`), and that is fair while R4 is open. Three things R4 has to answer. `models.js:9` returns early unless exactly four `.md-card` elements exist, so a fifth card would silently turn off the summary line. `status` repeats `status_word` at its start, so a `<b>word</b> status` template would print the word twice. `basis` and `label` carry semicolons, but the copy-rule test covers only `lines`, `status` and `expectation`. None of these is an OUT-2 defect, and the page files are outside OUT-2's paths. | Put the three points on board R4 for MODELS. If a card field is ever rendered as copy, give it a semicolon-free text and add it to `test_the_card_lines_keep_the_plain_language_rules`. |
| 8 | nit | `scripts/price/event_study.py:417`, `src/price/response.py:215` | Labels | The synthetic label is chosen by file name only, and the runner never reads `synthetic-label.json`. `apply` validates a bare cell without the record's minimum, so a hand-edited cell with `small_sample: false` passes `apply`. The record-level `validate` catches it. | Optional: read the sidecar when it sits beside an input, and carry `min_events_per_cell` in each cell so that `apply` can check it. |

### Verdict

**Rework.** The basis rule, the exploratory label and its refusal, the card fields, the stdlib rule and
the suite all hold under checks I ran. On the fixture the arithmetic is exact. One major method defect
remains: overlapping outages share one price change, and each counts it whole. That would bias the real
record, and the real record is the task's whole output. It is a small fix in the runner.

Exact rework, in the allowed paths:

1. Finding 1: handle overlapping forced events in a region (leave them out with a counted reason, or
   merge them by summed MW). State the rule in the record's `parameters`. Add a labelled fixture pair
   through `make_synthetic.py` that recovers the invented slope.
2. Finding 2: key the excluded week to each measured hour. Test it on SYN_L04.
3. Findings 3, 4 and 5 in the records: add the forced-rule sensitivity count and the lag distribution
   to the "Real run" table to fill. Add "rated capacity (IEMOP list of 2026-09-11)" to the units text.
   Correct hand-back 4 so that it names `RTD_Regional_Summaries` as the existing demand source and
   puts the normalization choice to the orchestrator.
4. Re-run the fixture run and update `event-study.md` and the test pins if the numbers move. Run the
   full suite, `plan.py scope OUT-2 971885b0`, `plan.py check` and `repo.py check`, and record them.

The task cannot be `done` until finding 6's condition is met: the orchestrator's capped export, the
study run with `--digests` after the fix, and the "Real run" table filled with the BigQuery cost.
Finding 7 goes to board R4. Finding 8 is optional.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Item | Value |
|---|---|
| Task | OUT-2 |
| Branch | `task/OUT-2` |
| Commit under review | `8a9c8fe9` (rework round 1, on top of `dca37302`) |
| Base | `971885b0` |
| Reviewer | Claude Opus 5.5 in-session subagent. It is read-only and independent of the author. |
| Verdict | **accept**, with the real-run condition below |

**The branch moved during this review.** `1db5f29d` ("real run: the measurement record filled from
the orchestrator's exports") landed at 08:41:33, after `8a9c8fe9` (08:37:01). It changes only
`event-study.md` and `out-2.md`, so the code and tests under review are byte-identical at both
commits. I ran the two touched test modules again on a frozen `git archive` of `8a9c8fe9`, in the
scratch directory outside the tree. I ran the full suite on the worktree after the move, and checked
the head before and after the run. This verdict covers `8a9c8fe9`. The note after the findings
records what I checked of `1db5f29d`. It is not a full review of that commit.

### Commands and results

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_price_response tests.test_price_baselines` (worktree) | `Ran 157 tests in 18.499s`, **OK** |
| The same, on a `git archive 8a9c8fe9` export in the scratch directory (no `.local`) | `Ran 150 tests in 11.590s`, **OK (skipped=1)**. The 7 fewer tests and the 1 skip are the real-series tests of `test_price_baselines`, which need `.local/price`. |
| Full offline suite, first run (it straddled the move to `1db5f29d`) | `Ran 2689 tests in 219.314s`, `FAILED (errors=1, skipped=115)`. The one error is `test_corpus_index.IndexScriptTests` setUpClass, `No module named 'pypdf'`, the known environment limit. |
| Full offline suite, second run on the settled head (head checked before and after) | Head `1db5f29d` before and after. `Ran 2689 tests in 272.838s`, `FAILED (errors=1, skipped=115)`. The one error is the same pypdf setUpClass. There are no failures. |
| `plan.py scope OUT-2 971885b0` | `OK: all changed files inside OUT-2 allowed paths` |
| `plan.py check` | `OK: 135 tasks, 9 gates` |
| `repo.py check` | `Checked 603 Markdown files, 3850 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check 971885b0..8a9c8fe9` | clean |
| `event_study.py --final .local/price/lwap_final_hourly.csv --series-only` | 184,036 rows, SHA-256 `3b3b0b66…bc19`, equal to `digests.json`. CLUZ, CVIS, CMIN and SYSTEM each have 46,009 hours and 41,617 with a baseline. These match the round 1 counts and the record. It printed no price. |
| Round 1 probe again, on a scratch copy built with the committed generator (`SYN_L02B`, 350 MW, out with SYN_L02 over the same hours) | With the rule, both are `overlapping_outage`. Without the rule (`events=()`), each reports 3.9993, as in round 1. The CLUZ cell keeps 11 events with median 1.995334, against the invented 2.0. On both the per-MW run and the demand run, `overlapping_outage` = 4 (the probe pair plus SYN_L15 and SYN_L16). |
| Committed fixture, SYN_L15 and SYN_L16 | Both `overlapping_outage`. CLUZ cell: 12 events, median 1.996429. Excluded counts: `overlapping_outage` 2, plus one each of the other four reasons. |
| My round 1 recomputation script, changed to key the week to each measured hour (own code, no runner import) | SYN_V03 7.9728893678, SYN_L04 1.9712427035, SYN_M02 4.9841527778. These equal `event_response` exactly. SYN_L04's Monday hour now has 20 baseline hours, and none falls in 16–22 February. With the demand fixture, the responses equal per-MW × 2,000, 10,000 and 2,500. The cell medians in `event-study.md` (19964.2921, 15972.2071, 12460.3819) are the per-MW medians × the invented demand. |

### Round 1 findings, re-checked against code and tests

| # | Round 1 | Round 2 state | Evidence |
|---|---|---|---|
| 1 | major: overlapping outages each take the whole change | **Closed** | `overlaps_another` (`scripts/price/event_study.py`) checks other forced outages of the same region in any measured hour. It compares by object identity, so it covers every other record. `event_response` leaves the event out as `overlapping_outage` before any price is read. The rule is in `parameters.overlap_rule`. Class `Overlap` (4 tests) and the fixture pair SYN_L15/SYN_L16 prove it, and the generator test still reproduces the committed bytes. My scratch probe agrees. |
| 2 | minor: excluded week keyed to the start day | **Closed** | `baseline_candidates(hour, weeks)` keys the days to each measured hour's own date. `baseline_for` no longer takes an event day. `test_syn_l04_monday_hour_takes_its_baseline_outside_its_own_week` pins the case. `series_counts` uses the same function, and the real-series counts did not change. |
| 3 | minor: exact-start forced rule, `known_at` unused | **Closed as a stated limit** | `known_at_limits` writes into `limits.known_at` the events first seen within one hour of their start, their share, and the lag median, p10, p90 and max. `limits.forced_rule` names the weakness. Query 1's comment says the same. The fixture's two moved sightings make the count non-trivial (23 of 25). This is a proxy, not the overlap-match count round 1 suggested (finding R2-3). |
| 4 | minor: `p_max` from one IEMOP list | **Closed** | `MW_LOST_BASIS` is in the record (`mw_lost_basis`, `limits.mw_lost`). The units read "per MW of rated capacity lost". The card method names the IEMOP list of 11 September 2026. Query 1's comment says the same. `Limits.test_the_record_states_rated_capacity_from_the_iemop_list` pins it. |
| 5 | minor: per MW lost, not over demand | **Closed** (orchestrator decision) | Query 2 (`-- BEGIN demand`/`-- END demand`) reads only `grid-nowcast.grid_curated.intervals`. It uses only the columns `region_name`, `interval_start` and `en_requirement_mw`, all three defined in `02_intervals.sql`. It writes nothing and selects no price column (tests `test_the_demand_query_reads_only_the_intervals_demand_and_no_price`, `test_neither_query_writes`). It has its own exact header `region_name,hour_start,n5,demand_mw_mean`, and the SELECT list is pinned to that header. `read_demand` refuses any other header, region, duplicate hour or non-positive value. `--demand` divides the change by MW lost over the mean demand of the used hours, and without it the runner divides by the MW lost alone. The record's `denominator` says which, and `validate` requires the `demand` input exactly when the normalization is per share of demand. Both fixture runs are in `event-study.md` by digest, and `MeasurementRecord` pins both. Query 1 still reads only the outage table and its columns (`test_it_reads_only_the_curated_outage_table_and_only_its_columns`). The level still comes only from the final series: the demand file has no price column, and the open-file test allows only the exports and the label sidecar. |
| 6 | condition: the real run | **Still the condition for `done`** | See "Condition" below. |
| 7 | minor: card contract (R4) | **Closed in OUT-2's paths**; R4 stays open | `status` no longer repeats `status_word` ("on a synthetic fixture, not on the snapshot."). The card's `basis` and `label` are semicolon-free card texts, and the record keeps the brief's basis sentence. `test_the_card_lines_keep_the_plain_language_rules` now walks every string of the card on both runs (more than 30 strings). The four-card guard in `src/grid/models.js:9` is outside OUT-2's paths and stays a hand-back for board R4. |
| 8 | nit: label by file name, bare-cell minimum | **Closed** | `read_label` reads `synthetic-label.json` beside each input that it lists. A file named `synthetic` that no sidecar lists is refused (`UNLABELLED_SYNTHETIC`). Class `Labels` (3 tests). Each cell carries `min_events`, and `validate_cell` checks the count against it, so `apply` refuses a bare cell that hides its small sample (`test_apply_refuses_a_bare_cell_that_hides_its_small_sample`). |

The test diff `dca37302..8a9c8fe9` replaces two of OUT-2's own round 0 tests,
`test_a_demand_column_switches_the_normalization` and
`test_units_are_per_mw_lost_because_the_series_has_no_demand_column`. The in-series demand path they
tested was removed by decision. Their assertions (the switch, the units, `DEMAND_REQUIRED`, the
shift) live on in `Denominator` over the `--demand` path. Every other test keeps its name, and
several keep the same assertions over both runs. The acceptance line "every existing assertion in
the touched test files is kept" is about files that existed at the base. `test_price_baselines.py`
is unchanged since round 1, where it gained one list entry.

### Findings, round 2

| # | Severity | Location | Bears on | Finding | Recommendation |
|---|---|---|---|---|---|
| R2-1 | minor | `scripts/price/event_study.py` `input_path` and `build_record` (`inputs[].path`) | Acceptance 2: "every figure in the record reproduces from the exports by digest" | The record stores each input's path as the run was given it. So the record's digest depends on the checkout it runs from. I rebuilt the real record in memory from the worktree: the inputs, rows, SHA-256 values, counts and cells all equal the stored `.local/price/response.json`. Only `inputs[].path` differed (`.local/price/…` against the main checkout's absolute paths), and so did the digest. Run with the main checkout's absolute paths, the digest equals `64412aaa…d9ed`. The figures reproduce, but the record digest does so only from the same path. | Write a path that does not depend on the checkout. Use the `digests.json` hint (`.local/price/<file>`), or the file name for a file outside the repository. Or else state the exact command, with absolute paths, beside the record's digest in `event-study.md`. This does not block. |
| R2-2 | minor (method judgment, for OUT-3 or a later round) | `overlaps_another` together with `affected_hours` | Decision 12: "for every forced outage above a stated size" | The overlap rule is correct and consistent with the baseline rule. Hours of any forced outage are kept out of baselines, so an outage already in progress does change the delta, and leaving the event out is the honest choice. But on the real export it leaves out 388 of 490 events (from the record at `1db5f29d`). I counted on the real export, counts only: in 301 of those 388, every overlapping outage was already out an hour before the first measured hour and stayed out to the end. In 87, another outage starts or ends inside the window. In 9, the only overlapping records are of the same unit, which is one physical outage recorded twice. 223 of the 490 events last over 7 days. | Keep the rule for this record. A later round could test, as a stated sensitivity, a rule that holds the set of ongoing outages the same in the event hours and the baseline hours. That would leave out only events where another outage starts or ends in the window. It could also merge same-unit overlapping records into one event. |
| R2-3 | nit | `known_at_limits` (`NEAR_START_HOURS = 1.0`) | Round 1 finding 3 | The share of events first seen within one hour of their start is a proxy for planned outages whose start moved. Genuinely forced outages are also often first seen soon after their start. `event-study.md` says "if the share is large" but gives no threshold. The count also covers every event read, the left-out ones included. | Optional: give a threshold, or add a column to query 1 later for a same-unit record carried before the start that overlaps in time. That would give a direct count. |
| R2-4 | nit | `src/price/response.py` `model_card` (`record["label"].startswith("synthetic")`) | Labels | The card decides "synthetic" from the label text's first word. A sidecar label that does not start with "synthetic" gives a card that reads "Measured on the snapshot exports" (the `Labels` test uses "a test label"). | Optional: carry a boolean `synthetic` from `read_label` into the record and read that. |
| R2-5 | nit | query 2, `TIMESTAMP_TRUNC(i.interval_start, HOUR)` | Denominator alignment | The final series keys an hour by `TIMESTAMP_TRUNC(interval_end - 1 minute)` (`scripts/price/export.sql`). Query 2 keys by `interval_start`. These agree only if `interval_start` is the start of the interval. The query's comment cites `HANDOFF.md`, which states this for the DIPC rows (`interval_start = interval_end - 5 minutes`). `02_intervals.sql:2-3` says the stamp is "not converted, verify". At worst this is a five-minute shift in an hourly mean of demand, which does not matter for a denominator. | None required. Say "assumed, as for DIPC" in the comment. |

### Condition (the real export), stated for the orchestrator

At `8a9c8fe9` these are proved on the fixture only, and they wait on the real run:

- acceptance 2, first clause: "every figure in the record reproduces from the two exports by digest
  with the stdlib". There are now three exports, with the demand denominator.
- acceptance 3, second clause: "the BigQuery cost of the one export is written". There are now two
  exports by the orchestrator's decision, so there are two cost lines. The brief's "one export" no
  longer matches the decided design. Record that decision where the brief can see it (the `tasks.json`
  note or the board), not only in the task record and the SQL comment.
- the Outputs line for `event-study.md`: "every number, its inputs by digest, the BigQuery cost".

The other clauses are met by code and tests at `8a9c8fe9`: acceptance 1 (the bases never mix), the
second half of acceptance 2 (the exploratory label and its refusal), the first half of acceptance 3
(the card's method, inputs, sample, spread and basis in the assumed fields, with R4 open) and
acceptance 4 (assertions kept, suite green apart from pypdf, no live call).

### Note on `1db5f29d` (checked in part, not reviewed in full)

- The three export digests in `event-study.md` equal `.local/price/digests.json` and the files' own
  SHA-256 values. The record's digest `64412aaa…d9ed` reproduces in memory from the three exports
  with `--digests`, with no file written. This holds only when the main checkout's absolute paths are
  given (R2-1). I copied no value from the exports into this record. The counts quoted in R2-2 are
  counts.
- The cost rows give dry-run upper bounds (1,499,128 and 36,742,926 bytes processed). They do not give
  the bytes billed by each job. Acceptance 3 asks for the cost of the export: add the billed bytes from
  `bq show -j <job id>` or `INFORMATION_SCHEMA.JOBS_BY_USER`, or state that the dry-run bound stands
  in for them.
- Line 3 of `event-study.md` still reads "fixture run; the real export waits for the orchestrator's
  BigQuery step". It now carries a correcting sentence, and `MeasurementRecord` pins it. When the
  orchestrator closes the task, update the line and its pin together.

### Verdict

**Accept `8a9c8fe9`.** All seven round 1 findings that OUT-2 could act on are closed in code and
tests, and the round 1 major is proved closed by the fixture pair and by my own probe. The remaining
findings are one minor about reproducibility (R2-1), one minor method judgment (R2-2) and three nits.
None blocks. The task becomes `done` when the orchestrator records the real-run condition above. The
exports and the record by digest are now at `1db5f29d`, which this round did not review in full. The
orchestrator also adds the billed cost, or states that the dry-run bound stands in for it.

## Round 3 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Item | Value |
|---|---|
| Task | OUT-2 |
| Branch | `task/OUT-2` |
| Commit under review | `8cc4d2bc` (rework round 2, on top of `1db5f29d`) |
| Base | `971885b0` |
| Reviewer | Claude Opus 5.5 in-session subagent. It is read-only and independent of the author. |
| Verdict | **accept** |

I read `git diff 8a9c8fe9..8cc4d2bc`. It changes `input_path` in `scripts/price/event_study.py`
and adds one test plus one pin change in `tests/test_price_response.py`. It also changes
`event-study.md`, `out-2.md` and OUT-2's `tasks.json` note.

### Commands and results

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_price_response tests.test_price_baselines` | `Ran 158 tests in 18.369s`, **OK** |
| Full offline suite (head `8cc4d2bc` before and after) | `Ran 2690 tests in 187.546s`, `FAILED (errors=1, skipped=115)`. The one error is `test_corpus_index.IndexScriptTests` setUpClass, `No module named 'pypdf'`, the known environment limit. There are no failures. |
| `plan.py scope OUT-2 971885b0` | `OK: all changed files inside OUT-2 allowed paths` |
| `plan.py check` | `OK: 135 tasks, 9 gates` |
| `repo.py check` | `Checked 603 Markdown files, 3850 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check 971885b0..8cc4d2bc` | clean |
| The real record rebuilt in memory with `--digests` and no file written, from four path forms: worktree relative (`.local/price/…`), worktree absolute, the main checkout's absolute path, and a symlink in the scratch directory under `/tmp` that points to the exports directory | All four give `deffe125…f51f`. Each stores `.local/price/<file>` as the path. The stored `.local/price/response.json` has the same SHA-256. No value was printed. |
| A scan of both full documents (`event-study.md`, `out-2.md`) against the three real exports, run in memory with counts and matches only | No unit name and no outage start stamp from the export. No decimal equals a demand value. The seven decimals that equal some final-price value are tolerances and slopes (0.01, 0.02, 0.04, 0.25, 8.0) and two band shifts computed by `apply` (18.12, 2174.01). In a series of 184,036 hours these are chance matches, not copied rows. "50.00" is the card's minimum size. The real-run section holds counts, digests, pooled cell statistics and computed shifts, which is what the brief's "every number" asks for. |

### Round 2 items

- **R2-1: closed.** `input_path` stores the path relative to the repository root. That holds whether
  the path is typed relative or absolute, through the worktree's `.local/price` link, or through the
  link's target. A file outside every checkout is stored as `external:<name>`. The new test
  `Reproducible.test_the_stored_input_path_is_the_same_in_every_checkout` covers each form. It also
  shows that a copy outside the tree keeps the same SHA-256 values and no machine path. Such a copy
  stores `external:` paths, so its record digest differs. The figures and input digests are the
  same. That is the stated design.
- **Line 3 of `event-study.md`: closed.** It now reads "fixture run, then the real run of 18 October
  2026 on the orchestrator's exports", and `MeasurementRecord` pins the new text.
- **Cost: closed.** The rows give the dry-run upper bounds (1,499,128 and 36,742,926 bytes). A row
  states that the bounds stand in for the billed bytes, because the network dropped before the jobs'
  statistics could be read. The two-export design is recorded as an orchestrator decision in OUT-2's
  `tasks.json` note.
- R2-2 (the overlap rule leaves out most real events), R2-3, R2-4 and R2-5 stay as recorded
  recommendations for OUT-3 or a later round. None blocks.

### Condition from rounds 1 and 2: met

The real run is recorded with both exports by digest. The record digest reproduces from the exports
with the stdlib, from any checkout path. The BigQuery cost of each export is written, with the stated
reason for using dry-run bounds. All four acceptance lines now hold.

### Verdict

**Accept `8cc4d2bc`.** The orchestrator may set OUT-2 to `done`.
