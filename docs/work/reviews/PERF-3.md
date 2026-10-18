# PERF-3 review record

## Designated review 1 (GPT Sol, independent, commit `23e68f9`, 2026-10-15)

> Independent review of `23e68f9`, against `feat/h1-api-persistence`; inspected the diff and all four branch commits. Working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Equivalence, cutoffs, access control, stale heads, double submission, refusal propagation, and revise → retain passed focused tests. Required browser preparation p50/p95 before/after remains explicitly unfinished in `perf-3.md:197`. |
> | 2 | All changes within allowed paths | **No.** Requested scope command exited 1, listing `tests/test_cache_headers.py`. The orchestrator’s documented intervention does not make scope print OK. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **Yes.** Existing contracts remain unchanged; route addition is required by intent. Updated flow assertions retain behavioral coverage and add refusal coverage. Existing fixture objects are identical after removing the added `prepare` keys and version/note changes. |
> | 4 | No unapproved runtime additions or effects | **Yes.** No new dependencies, services, credentials, model calls, or external service calls introduced. Preparation uses existing repository operations and persistence. |
> | 5 | Truthful mode labels | **Yes.** Fixtures identify recorded replay; preparation remains deterministic; local timing is explicitly distinguished from hosted measurement. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Fixture reproduction passed; existing case records, receipts, and history match the base. Hosted timing remains unclaimed. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreters, commands, results, stop condition, orchestrator intervention, unfinished measurement, and next actions. Earlier handoff sections remain stale, but the final addendum records subsequent verification. |
> | 8 | Domain and product invariants preserved | **Yes.** Existing compile/review guards remain; historical information cutoff and accepted-state audit cutoff are tested separately; access checks and `no-store` classification remain intact. |
> 
> Verification executed:
> 
> - `bash scripts/h1/test.sh`: attempted, exited **2** before tests; sandbox denied emulator loopback listeners with `EPERM`. Its reported 80-test pass was not independently reproduced.
> - `/usr/bin/python3 scripts/plan.py scope PERF-3 feat/h1-api-persistence`: **failed**, listing `tests/test_cache_headers.py`.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Full offline suite: **809 tests, 147 errors, 34 skips**; sandbox filesystem restrictions prevented temporary-file operations. This run does not demonstrate a passing suite.
> - `tests.test_event_prepare`: **11 passed, four emulator tests skipped**.
> - Recorded-flow and route-table tests: **18 passed**.
> - Fixture `build.py --check`: **passed**, reproducing all three decisions.
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/perf-3.md:197` | Required performance acceptance remains undemonstrated. | Packet explicitly leaves hosted browser p50/p95 before/after open; loopback HTTP timing does not satisfy it. | Record the authorized orchestrator measurement on the same case, with revisions, sample counts, and p50/p95, before acceptance. |
> | important | `tests/test_cache_headers.py:413` | Branch cannot satisfy the mandatory scope check. | Commit `466f164` adds classification entries outside PERF-3’s allowed paths; requested scope command exits 1. | Resolve ownership through the plan’s authorized scope process or a separately scoped change, then rerun scope until OK. |
> 
> **Verdict: rework.** Functional evidence is strong, but the required browser measurement is unfinished and the mandatory scope check fails.
**Verdict: rework.** Two findings. (1) Scope: resolved by the orchestrator through the plan: PERF-3 now depends on PERF-1 (done), so PERF-1's `tests/test_cache_headers.py` is an ancestor path and `plan.py scope` prints OK; the route-table entries stay. (2) Hosted browser preparation p50/p95 before/after on the PEDC case: an orchestrator measurement that needs a deploy carrying PERF-5 and PERF-3 together, so it follows the PERF-5 merge; the "before" sample is taken on `00008-5ln` first. Re-review after the measurement is recorded.

## Designated review 2 (GPT Sol, independent, commit `af485a3`, 2026-10-15)

> Independent review of `af485a3` against `feat/h1-api-persistence`, including all seven branch commits. Working tree clean; no files edited.
> 
> | # | Checklist item | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Focused tests demonstrate equivalence, authorization, cutoffs, stale-head refusal, idempotency, refusal propagation and revise → retain. Hosted measurements exist, but use Manila rather than the intent’s required Cloud Build origin. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope PERF-3 feat/h1-api-persistence` printed **OK**. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **Yes.** Endpoint is additive; existing compile/review contracts remain intact. Updated flow tests preserve refusal and history coverage. |
> | 4 | No runtime additions or effects beyond packet | **Yes.** Implementation composes existing repository operations; no new dependency or external runtime call. Hosted deployment and measurement are recorded as owner/orchestrator actions. |
> | 5 | Truthful mode labels | **Yes.** Deterministic preparation, recorded replay, loopback timing and hosted browser timing are distinguished. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Fixture reproduction passed; case facts and receipts derive from existing records. Numerical interpretation has the correction below. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreter, commands, results, stop condition, subsequent dispositions and next actions. |
> | 8 | Product and domain invariants preserved | **Yes.** Authorization and existing review guards remain; tests separately verify historical information cutoff and accepted-state audit cutoff. |
> 
> Verification executed:
> 
> - `bash scripts/h1/test.sh`: attempted; exited **2 before tests**, because sandbox denied emulator listeners (`EPERM`). The recorded 80-test pass was not independently reproduced.
> - Requested scope check: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Full offline suite: **863 tests, 187 errors, 35 skips**; sandbox restrictions prevented temporary-directory operations. This does not demonstrate a passing suite.
> - `tests.test_event_prepare`: **11 passed, 4 emulator tests skipped**.
> - `tests.test_grid_event.RecordedFlow`: **10 passed**.
> - Fixture `build.py --check`: **passed**.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/perf-3.md:231` | Performance evidence does not follow the mandated measurement procedure. | Intent requires measurements through `web.app` **from Cloud Build**; both recorded browser runs originate from Manila (`:231–232`, `:255`). | Record comparable before/after Cloud Build measurements with revisions, sample counts and p50/p95. |
> | minor | `docs/work/performance/perf-3.md:273` | Summary overstates the measured preparation p50 improvement. | Reported medians are 3.39 s and 2.50 s: improvement **0.89 s**, rather than 1.2 s. | State 0.89 s overall; distinguish any estimate for case calls alone. |
> 
> **Verdict: rework.** Functional checks pass where executable, but required performance evidence still uses a measurement origin contrary to the intent.
**Verdict: rework.** Orchestrator disposition: (important) a Cloud Build measurement of both decision paths on the same revision `00009-g9c` (old three-call path and the prepare path, same script shape as the PERF-0 baseline) is run and recorded in the packet; (minor) the 1.2 s sentence is corrected to 0.89 s overall with the case-calls-only figure stated separately. Review 3 next.

## Designated review (GPT Sol, independent, commit `9c6c784`, 2026-10-15)

> Independent review of `470c47c33805` against `feat/h1-api-persistence`: inspected the three-dot diff and all nine branch commits. Working tree clean; no files edited.
> 
> | # | Checklist item | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Focused tests passed for equivalence, access checks, historical information cutoff, accepted-state audit cutoff, stale-head refusal, double submission, refusal propagation and revise → retain. The adapter harness proves one preparation call. The packet records browser before/after p50/p95 and the subsequent Cloud Build comparison on `00009-g9c`, five sessions per path. Hosted measurements were not independently rerun. |
> | 2 | All changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope PERF-3 feat/h1-api-persistence` printed `OK: all changed files inside PERF-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **Yes.** The endpoint is additive; existing compile/review contracts and guards remain. Updated adapter tests preserve failure coverage. Fixture reproduction passed. |
> | 4 | No additions or effects beyond the packet | **Yes.** Preparation composes existing repository operations and persistence; no new runtime dependency or external call. Deployment and hosted timing are recorded as owner/orchestrator actions. |
> | 5 | Truthful mode labels | **Yes.** Deterministic preparation, recorded fixtures, browser measurements and Cloud Build measurements are distinguished. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Case records and receipts reproduce from the repository. Consequences remain uncomputed; no forecast-performance claim is introduced. |
> | 7 | Verification and handoff recorded | **Yes.** Packet records interpreters, commands, results, stop conditions, subsequent resolutions and review as the next action. One machine-readable note remains stale, below. |
> | 8 | Product and domain invariants preserved | **Yes.** Authorization, historical cutoff, permission references, decision-time stale/dependency guards and `no-store` classification remain intact. |
> 
> Verification executed:
> 
> - `bash scripts/h1/test.sh`: attempted; exited **2 before tests** because the sandbox denied emulator listeners (`EPERM`). Recorded 80-test success was not independently reproduced.
> - Requested scope check: **OK**.
> - `scripts/plan.py check`: **OK**; `scripts/repo.py check`: **PASS**.
> - Focused preparation and recorded-flow tests: **21 passed, 4 emulator tests skipped**.
> - Fixture `build.py --check`: **passed**, reproducing three decisions.
> - Full offline suite: **863 tests, 187 errors, 35 skips**. Filesystem restrictions prevented temporary-directory operations; this run does not demonstrate a passing suite.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/tasks.json:2196` | Stale task note can misdirect the next handoff. | It still reports unresolved route-table failures and pending hosted measurement; scope now passes and the packet records both resolutions. | Update the note to the current review-ready state when recording this review. |
> 
> **Verdict: accept.** Acceptance behavior is demonstrated by executed focused checks and recorded integration/performance evidence, with no blocking or unresolved important findings.
**Verdict: accept.** Decision path after the session p50 3.19 to 1.68 s on 00009-g9c; one preparation call instead of three.
