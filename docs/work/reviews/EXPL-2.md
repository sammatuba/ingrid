# EXPL-2 review record

Task: the day as a path. Plan note: [intent](../explore/intent.md). Task record: [implementation](../explore/implementation.md#expl-2-the-day-as-a-path).

## Designated review 1 (GPT Sol, independent, commit `cffb01c` on `task/EXPL-1`, 2026-10-15 14:34 Manila)

> Independent review of `cffb01ccd579`, against `task/EXPL-1`. Inspected the requested diff and log, plus the clean working tree. No files edited.
>
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **No** | Bake reproduced in memory; shape checks pass. Browser evidence covers Visayas at 13:40, without demonstrating path changes across clock times and all three grids. Current-point clicks also have the defect below. |
> | 2 | Changes inside allowed paths | **Yes** | `scope EXPL-2 task/EXPL-1` printed `OK: all changed files inside EXPL-2 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes** | Diff changes no frozen contracts or acceptance text. Request-count updates accommodate the deferred vectors request; first-screen ordering remains asserted. No added skips or deleted tests. |
> | 4 | No unauthorized dependency or external effect | **Yes** | Standard-library bake code; the additional request reads the specified baked data file. No added model, service, credential or cloud operation. |
> | 5 | Truthful mode labels | **Yes** | Fixture identifies itself as synthetic; production caption says exploratory and “Not a forecast; no score.” The browser adds stored vectors. |
> | 6 | Unknowns preserved; no invented facts | **Yes** | Out-of-vocabulary types remain `null`; shipped vectors reproduce the local spike-derived bake. Corpus facts match the spike record. |
> | 7 | Complete packet and resume information | **No** | Commands and results are recorded, but the EXPL-2 section lacks an explicit unfinished-work list and exact next action. The preceding next-action list still says EXPL-2 follows. |
> | 8 | Consistent with direction and invariants | **Yes** | Implementation ships exploratory data without forecast scores, probabilities or assumption changes. Point colours encode recorded message kinds rather than computed risk. |
>
> Findings—all unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/grid/grid.js:546` | Clicking the centre of the latest point does not open its message. | `.p-now` is appended over the latest `.p-step`, has a painted radius of 2, and lacks `data-adv`. The handler at line 933 reads only the clicked target’s attribute. | Give the overlay `pointer-events: none`, or attach the advisory identity; verify an actual pointer click at the latest point’s centre. |
> | important | `tests/test_grid_page.py:1277` | Required clock movement and per-grid behaviour remain undemonstrated. | Assertions inspect a fixed Visayas snapshot. The harness clicks the first point with `dispatchEvent`, bypassing pointer hit testing; it never asserts path changes across clock times for all three grids. | Run browser checks for each grid before and after typed messages, asserting path changes and actual point-click navigation at both widths. Record results. |
> | minor | `docs/work/explore/implementation.md:138` | Handoff does not identify the remaining work and exact next action. | EXPL-2 ends with its command table; screenshot review is mentioned as pending elsewhere without a concrete resume instruction. | Add unresolved items and the exact next action, including the required owner screenshot review’s status. |
>
> Verification executed:
>
> - Requested unittest command: **120 tests, 48 errors, 4 skipped**. Temporary-directory creation was blocked by the read-only sandbox; the browser harness also returned empty output. This does not establish an application regression or a passing verify.
> - Requested scope command: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - `ExplorableMarkup`: **5 tests passed**; fixture reproduction check: **OK**.
> - In-memory real bake: **175×16 vectors, 16×2 plane, 342/350 typed**, byte-identical to existing `vectors.json`.
> - Full offline suite was not rerun.
>
> **Verdict: rework** — correct the current-point click defect and demonstrate path updates with the clock for every grid before acceptance.

**Verdict: rework.** Orchestrator disposition: the current-point overlay now passes pointer events through, and the
run clicks the latest point with a real pointer click (not a dispatched event) and reads its message; the run moves
the clock from 00:00 to 23:55 for each of the three grids and the test asserts the point counts per grid (0 at the
start, 4 Visayas, 1 Luzon, 0 Mindanao typed at the end on the fixture); the handoff names the remaining work.
Review 2 requested.

## Designated review 2 (GPT Sol, independent, commit `3bf67ff`, 2026-10-15 15:41 Manila)

> Independent review of `task/EXPL-1...3bf67ff87595`, including both commits in `git log task/EXPL-1..HEAD`. Working tree clean; no files edited.
>
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **No** | Bake and caption evidence are recorded, and the overlay fix is present. Mindanao has no typed fixture messages, so its path drawing and clock movement remain undemonstrated. |
> | 2 | Changes within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EXPL-2 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes** | No frozen-contract or acceptance edits, added skips, or deleted tests. Request-count changes accommodate the deferred vector file while preserving ordering assertions. |
> | 4 | No unauthorized dependency or external effect | **Yes** | Standard-library bake code and the authorized static-data request; no added model or cloud operation. |
> | 5 | Truthful mode labels | **Yes** | Synthetic table identifies its corpus as synthetic; production caption says exploratory and “Not a forecast; no score.” |
> | 6 | Unknowns preserved; no invented facts | **Yes** | Unknown vocabulary mappings remain `null`; production corpus numbers match the spike record. |
> | 7 | Complete packet and resume information | **No** | Interpreter, commands, results and next actions are recorded, but the revised browser checks lack recorded execution results, and the packet overstates the Mindanao assertion. |
> | 8 | Consistent with direction and invariants | **Yes** | Stored vectors support exploration without scores, probabilities or assumption changes; point colours encode message kinds. |
>
> Findings, unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `tests/test_grid_page.py:1272` | Required path behaviour for Mindanao remains unproven. | Fixture vocabulary contains only Luzon and Visayas types. Switching Mindanao between clock endpoints exercises an empty panel; end counts are asserted only for the other grids. | Add a typed Mindanao fixture message and demonstrate its path changing with the clock at both widths; record passing execution results. |
> | minor | `docs/work/explore/implementation.md:152` | Packet claims verification the test does not perform. | It says end counts of 4, 1 **and 0** are asserted; no Mindanao end-count assertion exists. The revision section describes harness changes without reporting their executed output. | Correct the assertion description and attach results from the revised browser run. |
>
> Verification actually executed:
>
> - `/usr/bin/python3 -m unittest tests.test_grid_page tests.test_grid_data`: **120 tests, 48 errors, 4 skipped**.
> - `/usr/bin/python3 -m unittest discover -s tests`: **885 tests, 198 errors, 29 skipped**.
> - Both suites encountered sandbox restrictions, including unavailable writable temporary directories; these results do not establish application regressions or passing verification.
> - Requested scope check: **OK**. `plan.py check`: **OK**. `repo.py check`: **PASS**.
> - `ExplorableMarkup`: **5 passed**. Fixture reproduction: **OK**.
>
> **Verdict: rework** — demonstrate the required Mindanao path behaviour and record execution evidence for the revised browser checks before acceptance.

**Verdict: rework.** Orchestrator disposition: the fixture now carries a typed Mindanao message, the test asserts the
Mindanao end count, and the recorded run output at both widths is in the task record. Review 3 requested.


## Designated review (GPT Sol, independent, commit `2f6c36f`, 2026-10-15)

> Independent review of `task/EXPL-1...2f6c36fca8dc`, including all three commits in `git log task/EXPL-1..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes** | Real bake reproduced byte-identical `vectors.json`: 175×16 vectors, 16×2 plane, 342/350 messages typed. Recorded browser runs at 1280 and 390 demonstrate all three grids changing with the clock and a pointer click opening the latest message. Caption includes exploratory label and corpus size; no score or probability displayed. |
> | 2 | Changes within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EXPL-2 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes** | Diff changes no frozen contract or acceptance text. Request-count adjustments preserve first-screen ordering assertions; no added skips or removed tests. |
> | 4 | No unauthorized dependency or external effect | **Yes** | Standard-library bake code; additional request reads the specified static vector file. No new model, service or cloud operation. |
> | 5 | Truthful mode labels | **Yes** | Fixture identifies synthetic data; production caption identifies exploratory learned vectors and says “Not a forecast; no score.” |
> | 6 | Unknowns preserved; no invented facts | **Yes** | Unmapped types remain `null`; corpus figures match the spike record. Production vectors reproduce the existing bake. |
> | 7 | Complete packet and resume information | **No** | Commands, results, interpreter and revised browser outputs are recorded, but the remaining-work section contains stale review and screenshot status. |
> | 8 | Consistent with direction and invariants | **Yes** | Stored vectors support exploration without forecast scores or assumption changes. Point colours identify message kinds rather than computed risk. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/explore/implementation.md:178` | Stale handoff can send the next session back through completed steps. | Screenshot review says “Pending” despite the earlier owner acceptance; the next item still requests EXPL-2 review 2. | Reconcile the remaining-work list with the recorded owner response and current review. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_page tests.test_grid_data`: **120 tests, 48 errors, 4 skipped**. Temporary directories were unavailable under the read-only sandbox; browser setup returned empty output. This does not establish passing verification or an application regression.
> - `/usr/bin/python3 scripts/plan.py scope EXPL-2 task/EXPL-1`: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - `ExplorableMarkup`: **5 passed**; fixture reproduction: **OK**.
> - Full offline suite: **885 tests, 198 errors, 29 skipped**, encountering sandbox restrictions.
> - In-memory real bake: **byte-identical vectors.json; zero contract violations**.
> 
> Browser acceptance relies on the committed execution records at both widths; I could not independently rerun Chromium here.
> 
> **Verdict: accept** — the required behaviour is demonstrated by the recorded browser runs and reproduced bake, with only a minor handoff correction remaining.
**Verdict: accept.** the day as a path
