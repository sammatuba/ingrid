
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `3f60edcb`, 2026-10-17 20:22, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-6 review: rework
> 
> I reviewed `task/DESK-6` at `3f60edcb`, which is commit `22746f92` plus a packet-only commit. The base is `feat/product-refine`, merge base `ac7d0972`. I did not write this change and I edited no files.
> 
> ## What I ran in this worktree
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_outlooks_page` (the verify command) | `Ran 189 tests in 20.111s` / **OK**, no skips. Chromium was found here, so `ThePageInTheBrowser` actually ran. |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2245 tests in 209.068s` / **OK (skipped=58)**. The packet says 2203; the extra tests come from SCORE-1 landing on the base. |
> | `/usr/bin/python3 scripts/plan.py scope DESK-6 feat/product-refine` | `OK: all changed files inside DESK-6 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 105 tasks, 8 gates` |
> | SHA-256 of `.local/price/scorecard.json` | `70ca1c39…bf740a`. The SYSTEM entry's counts are 1414/1378/33 market origins and 31/25/1 administered-pricing origins, and its unavailable counts match the packet's §3. |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **No number without its record:** the bake copies the figures field by field, and `scorecard_block_problems` refuses anything else in the block. `TheRealArchive` compares every figure with the real record, and the browser test compares every cell with the baked index. Both ran.
>    - **Units:** "PHP/MWh" is not in the baked index, but `target-contract.md:13` (the series is in PHP/MWh) and `baselines.md:138` (the scorecard is in PHP/MWh) state the unit.
>    - **Absent when there is no scorecard:** `ScorecardInput`, `IndexBake` and `BuildAllTests.test_a_fresh_bake_takes_the_scorecard_with_and_without_it` cover it. That test writes into a temporary `--data` directory and runs `--check` with and without `--scorecard`; it passed.
>    - **Real-scorecard counts:** `refresh-regeneration-2026-10-17.md` states only the digest, not the counts. The test's counts come from the record that digest names, and I confirmed both, so the chain holds.
>    - **Copy rules:** one item fails on labelling (finding 1).
> 2. **No file outside allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract changed, no test weakened or skipped: yes.**
>    - No assertion was removed from `test_grid_data.py`.
>    - Two exact browser pins were moved because the fixture changed. Both are still exact; one now takes its expected value from the bake it checks (finding 2).
> 4. **No new dependency, service, network or model call: yes.** The scorecard and the values file are only read.
> 5. **Mode labels truthful: no, partly.** The synthetic fixture is built through the real `src.price` code and labelled as such. But the page names the pinball losses with the record's quantile names (finding 1).
> 6. **Unknowns stayed unknown: yes.**
>    - The task reads the series key from the values-file header. `first-outlook.md:132-134` records why: `target_series_ref` carries no region and the values file names it (`"series": "SYSTEM"`).
>    - The bake checks that file's digest before using it, and a missing file adds no block rather than a guessed match.
>    - The executor asked whether this read is acceptable. I find it acceptable: it is not a workaround of a stop condition.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes**, with one stale commit id (finding 3).
> 8. **No contradiction with blueprint, strategy or invariants: yes.** There is no rank, no badge and no skill claim, and the caption says so.
> 
> ## Findings
> 
> - **important** | `src/grid/outlooks.js:206-208` (pinned at `tests/test_grid_outlooks_page.py`, the `headers` assertion in `test_the_baseline_track_record_is_drawn_from_the_baked_block`)
>   - **Failure:** the column headers read `p10`, `p50` and `p90` (PHP/MWh), but the cells hold `pinball_p10/p50/p90`, which are pinball losses. The record's own `quantile_rule` uses "p10, p50 and p90" for the fan's forecast values. So a reader sees "p10 = 500.58 PHP/MWh" and "p90 = 439.03 PHP/MWh" for SYSTEM day persistence and takes them for price quantiles.
>   - **Evidence:** the `quantile_rule` field in the scorecard; the brief's Outputs say "pinball p10/p50/p90"; `baselines.md:140` labels the column "pinball p10".
>   - **Correction:** label the columns as pinball (for example `Pinball p10`, two words, inside copy rule 5), update the header pin and the packet's §3 table, and re-run the verify command.
> - **minor** | `tests/test_grid_outlooks_page.py`, the moved values-diff pin in `ThePageInTheBrowser`
>   - **Failure:** the expected digest `values_to` is read from the bake under test, so a wrong `values_sha256` there would still pass.
>   - **Evidence:** `values_to = self.index['targets'][0]['vintages'][1]['values_sha256']`.
>   - **Correction:** take it from `cls.values['sha256'][:8]`, the independently written record.
> - **minor** | `docs/work/price-outlook/desk-6.md:3,162`
>   - **Failure:** the packet's committed-tree runs name `2df38dd`, the commit before the runner's rebase; no branch contains it now. The packet also names base `87560739`, but the merge base is `ac7d0972`.
>   - **Evidence:** `git branch --contains 2df38dd` prints nothing.
>   - **Correction:** name the reviewed commits (`22746f92`/`3f60edcb`) and the merge base, and note that the suite count moved with the base.
> 
> ## Verdict: rework
> 
> One important finding stands. The page labels the pinball losses with the record's quantile names, so its figures read as price quantiles they are not. The fix is one label, one test pin and a verify re-run; everything else (scope, contract, hidden path, digest as-of, real counts and the full suite) checks out.
> 
> The full-suite monitor has now reported its own result: `Ran 2245 tests in 209.068s` / OK (skipped=58), the same run quoted in the review. The verdict is still **rework**, because of the pinball column labels at `src/grid/outlooks.js:206-208`.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `2881f652`, 2026-10-17 20:37, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-6 re-review: **accept**
> 
> I reviewed `task/DESK-6` at `2881f652` against `feat/product-refine` at `ac7d0972`, which is also the merge base. The branch has four commits over the base: `22746f92` (the change), `3f60edcb` (the packet's runs), `e86db9f6` (the first review's record) and `2881f652` (the rework). This review is independent: I did not write the change, and I edited no files.
> 
> ## What I ran in this worktree
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_outlooks_page` (the verify command) | `Ran 189 tests in 21.183s` / **OK**, no skips, exit 0. Chromium was found here, so the browser test class actually ran at 390 and 1280, and so did the real-scorecard test. |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2245 tests in 205.400s` / **OK (skipped=58)**, exit 0. This is the same count the packet and the first review measured on this base. |
> | `/usr/bin/python3 scripts/plan.py scope DESK-6 feat/product-refine` | `OK: all changed files inside DESK-6 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 105 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | `Checked 537 Markdown files, 3547 local links, 5 skills; bootstrap 1400 words.` **PASS** |
> | SHA-256 of `.local/price/scorecard.json`, plus its SYSTEM entry read directly | `70ca1c39…bf740a`. Market origins are 1414 (day), 1378 (week) and 33 (month); administered-pricing origins are 31, 25 and 1. The figures and the unavailable counts match the packet's §3 table cell for cell (for example, persistence day pinball p10 is 500.577468, and seasonal day is `INSUFFICIENT_SEASON_SAMPLES` 365). |
> 
> ## How the first review's findings were closed
> 
> - **important, pinball column labels: fixed.** `src/grid/outlooks.js:206-208` now reads `Pinball p10/p50/p90`. The browser test pins the full header list, and it ran here at both widths.
> - **minor, the values pin compared the bake with itself: fixed.** `values_to = self.values['sha256']` now comes from `values_record()`, which hashes the file it just wrote, so it no longer depends on the bake under test. The pin ran here.
> - **minor, stale commit ids: fixed.** `desk-6.md:3-8` names `22746f92`, `3f60edcb` and the merge base `ac7d0972`.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **No number without its record.**
>      - `scorecard_view` copies the market-slice fields one by one. `scorecard_block_problems` refuses any other key.
>      - `ScorecardInput` compares every figure with the record's own `to_dict()`, on a scorecard built by the real `src.price` code.
>      - `TheRealArchive` compares every figure with `70ca1c39…`'s SYSTEM entry.
>      - The browser test compares every drawn cell with the baked index.
>      - Every row and every slice line ends with `record <digest>…`.
>      - The unit "PHP/MWh" is not in the index. I read it as a column label taken from the series' recorded unit (`target-contract.md:13`, `baselines.md:138`), not as a figure. The first review read it the same way.
>    - **Hidden when the file is absent; `--check` passes with and without `--scorecard` into a temporary `--data` directory.** Three tests cover this, and all ran:
>      - `test_an_absent_scorecard_leaves_no_key` (with `None` and with an explicit absent path)
>      - `IndexBake.test_a_bake_without_a_scorecard_carries_no_baseline_block`
>      - `BuildAllTests.test_a_fresh_bake_takes_the_scorecard_with_and_without_it`
>    - **Copy rules 1 to 7.**
>      - The slice is named in words: "market hours; administered-pricing hours counted apart".
>      - The unavailable counts are in words, for example "365 unavailable (INSUFFICIENT_SEASON_SAMPLES)".
>      - Labels are three words or fewer; units are muted; the digest is the as-of.
>      - There is no badge (the page source, HTML and CSS are all checked), no rank, and the one caption sentence says no skill claim is made.
>    - **Real-scorecard test.** It asserts the digest and SYSTEM's three baselines with the 1414/1378/33 and 31/25/1 counts. The regeneration record itself states only the digest (line 42). The counts come from the record that digest names, and I checked them myself.
> 2. **Nothing outside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** I listed every removed test line in the diff. Only the browser-fixture call sites, the report-dict equality (it gained a `scorecard` key and is still exact) and the values-diff pin (now tighter) moved. No `skip` was added.
> 4. **No new dependency, service, network or model call: yes.** The scorecard and the values file are only read, and a test asserts that neither is written.
> 5. **Mode labels truthful: yes.** The synthetic scorecard is built through the real `build_scorecard`, and the columns now say "Pinball". Last round this item was "no, partly"; it is now a plain yes.
> 6. **Unknowns stayed unknown: yes.**
>    - The series key is read from the newest vintage's values-file header, and the file's digest is checked against the one the outlook cites.
>    - An absent values file or a series the scorecard lacks gives no block, never a guess.
>    - `first-outlook.md` records why: `target_series_ref` carries no region.
> 7. **The packet records interpreter, commands, results, unfinished items and next action: yes.** See §6, §8 and the Rework section.
>    - The first PROGRESS.md log row still says the headers were "p10, p50, p90" and the base was `87560739`.
>    - Log rows are dated and only ever added to, and the rework row corrects both points, so nothing needs to change.
> 8. **No contradiction with the blueprint, strategy or invariants: yes.** There is no rank, badge or skill claim, and the challengers' (PRICE-3) results are not shown.
> 
> ## Findings
> 
> - **minor** | `scripts/grid/build_data.py:1239` (the docstring of `scorecard_record_problems`, and packet §1)
>   - **Failure:** the docstring and the packet say the record is checked for "every horizon of the price target contract". The code only refuses unknown or repeated horizon labels. A record that drops the month horizon would still bake, and the page would show fewer tables with no error.
>   - **Evidence:** lines 1238-1243 check `label not in SCORECARD_HORIZONS` and repeated labels. Nothing compares `labels` with `set(SCORECARD_HORIZONS)`.
>   - **Correction:** add `if labels != set(SCORECARD_HORIZONS): fail(...)` after the horizon loop, with a refusal test. Or reword the docstring and packet to "only horizons of the target contract".
>   - **Disposition:** does not block. The real record carries all three horizons.
> - **minor** | `tests/test_grid_data.py:1900-1901`
>   - **Failure:** the diff removed the blank lines between the end of `BuildAllTests` and the module-level `def excluded_by_context`. This is a PEP 8 E305 style problem only.
>   - **Evidence:** the removed `-` blank line in the diff at the end of `BuildAllTests`.
>   - **Correction:** restore two blank lines.
>   - **Disposition:** does not block.
> 
> ## Verdict: **accept**
> 
> Every acceptance item was demonstrated by checks that ran here: the verify command (including the browser class), the full suite at 2245 OK, scope, the digest and the real counts. The first review's important finding and both minor findings are fixed. The two remaining findings are minor and do not affect what the page shows from the real record.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
