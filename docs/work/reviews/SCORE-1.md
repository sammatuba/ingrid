
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `2bb60617`, 2026-10-17 20:11, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> The full suite is still running; I'll give the verdict once it finishes.
> 
> # Review of SCORE-1: verdict **accept**
> 
> I reviewed `task/SCORE-1` at `2bb60617` against `feat/product-refine`: two commits and six files (`src/outlook/scoring.py`, `scripts/outlook/score.py`, `tests/test_outlook_scoring.py`, `docs/work/outlook-archive/scoring.md`, `tasks.json`, `PROGRESS.md`). This review is independent; I did not write the change, and I edited no files.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | Archive `verify()` before the tests | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}` |
> | The brief's verify command (four outlook test modules) | `Ran 209 tests` / **OK** |
> | Archive `verify()` after the verify run and again after the full suite | unchanged: 2 outlooks, 0 receipts, 0 problems |
> | `tests.test_outlook_scoring.RealArchive` and `StdlibOnly` with `-v` | 5 tests, all **ok**. The real-archive test ran; it did not skip. |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2232 tests in 154.884s` / **OK (skipped=58)** |
> | `/usr/bin/python3 scripts/plan.py scope SCORE-1 feat/product-refine` | `OK: all changed files inside SCORE-1 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 105 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (534 Markdown files, 3532 links) |
> | Extra test: a whole day missing from the export, run through the test fixture under the temp dir | 26 skip entries, 24 hours scored (see the first finding) |
> 
> ## Checklist
> 
> 1. **Every acceptance item is met by a check that was actually run: yes.**
>    - **No receipt is added:** `verify()` reads 2/0/0 before and after both the verify run and the full suite. `RealArchive` refuses both November outlook ids with `WINDOW_NOT_SETTLED` at `scored_at` 2026-12-01. That instant is after the window closed, so the refusal comes from the export (its last hour is before 2026-11-26 00:00 local), not from the clock.
>    - **The real values files pass every check that comes before the export check:** digest, row count, shape and horizon coverage are all checked first in `score_outlook`. So the real refusal also shows that the first outlook's values files have the shape the scoring code needs.
>    - **The receipt validates and its metrics match the scorecard:** `validate_receipt` passes, and the archive's own `build_receipt` enforces the link rules. The metrics equal `metrics_from` on independently rebuilt `(realized, point, p10, p50, p90)` rows, for both a mid-only values file and one with a band.
>    - **Marked hours are skipped, never filled:** the export is checked by `verify_inputs` before it is parsed, and both digest refusals are tested. Marked hours appear in `coverage.skipped` with their reasons: 96 administered-pricing hours plus 24 irregular-day hours plus 48 scored hours make up the 168-hour window.
>    - **The command:** argparse exits with code 2 without `--final-series-version`. `StdlibOnly` checks the imports. The command was tested end to end, including `--dry-run`, the duplicate refusal and the default `scored_at` from the clock.
>    - **Full suite:** OK.
> 2. **No file outside the allowed paths changed: yes.** `plan.py scope SCORE-1 feat/product-refine` printed OK. That is the brief's base branch; the checklist text names `feat/h1-api-persistence`.
> 3. **No frozen contract or acceptance text changed, and no test was weakened: yes.** Only new files plus the task's own `tasks.json` and `PROGRESS.md` rows changed. No existing test file was edited.
> 4. **No new dependency, network call, model call or cloud effect: yes.** The module reads no clock. The command reads the clock once, only when `--scored-at` is omitted, and prints that instant.
> 5. **Mode labels are truthful: yes.** Fixture outlooks have `synthetic=True`, and `synthetic` passes from the outlook to the receipt one way, tested in both directions.
> 6. **Unknowns stayed unknown: yes.** No price values are quoted. A mid-only values file is scored with a zero-width band, which the owner's note allows and which §5.1 records.
> 7. **The packet records interpreter, commands, results, unfinished items and next action: yes.** See `scoring.md` §6 and §9. The committed tree was re-run at `a201d78`.
> 8. **Nothing contradicts the blueprint or domain invariants: yes.** The record states the regional-only scope and the decision to skip administered-pricing hours (§5.2, §5.4).
> 
> ## Findings
> 
> **1. Minor: `src/outlook/scoring.py:361`**
> - **Failure mechanism:** the comment says the `missing hour` branch is "Unreachable behind the day mark". It is reachable. `derive_marks` (`src/price/series.py:473-477`) only counts days that have at least one row, so a day missing entirely from the export is not an irregular day. Each of its hours then falls through with its own reason, `missing hour <iso>`. Nothing is filled, but one gap becomes 24 separate entries in `coverage.skipped`, and no test covers this. The fixture's `missing=` parameter is never used.
> - **Evidence:** my extra test, `Fixture(missing=<24 hours of 2026-03-25>)`, gave 26 skipped entries and 24 scored hours.
> - **Correction:** fix the comment, add a test that uses `missing=`, and consider grouping the gap under one reason per day, such as `missing day <date>`.
> 
> **2. Minor: `src/outlook/scoring.py:290` (`_skip_reason`) and `:382`**
> - **Failure mechanism:** a billing month with mixed administered pricing is skipped as a whole, including its market hours. The `ap` metrics row can therefore never be produced. The brief says "one metrics row per horizon label and slice as scorecard.py defines slices"; in practice only the `market` row is emitted.
> - **Evidence:** the code at those lines. `scoring.md` §5.2 records this reading of the brief's text about skipping administered pricing, and the 2026-11 window has no administered-pricing mark, so the first real receipt is not affected.
> - **Correction:** none needed for this task. The guardian may confirm the reading when a mixed or administered window first needs scoring.
> 
> ## Verdict
> 
> **Accept.** Every acceptance item was shown by a check I ran myself: the real archive is still at 0 receipts, both November outlooks are refused with `WINDOW_NOT_SETTLED`, the fixture receipt validates and matches `metrics_from`, scope is OK and the full suite is OK with 58 skips. Neither finding is blocking or important.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
