
## Designated review 1 (GPT Sol, independent, commit `9662af4`, 2026-10-15)

> Independent review of commit `9662af44a0d1b288616a89105a0f7b1f3630d3ae` against `feat/h1-api-persistence`. The log contains one commit; the diff adds a task record and one PROGRESS entry. Working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build runs through `web.app` are recorded, but required cold/warm route statistics and completed session cleanup are not demonstrated. |
> | 2 | Changes within allowed paths | **No.** Scope command exited 1, listing `docs/work/performance/perf-0.md`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** The two-file documentation diff changes none of these. |
> | 4 | No effects beyond the packet | **Yes.** The diff introduces no runtime changes; described hosted timing and test sessions fall within the packet. |
> | 5 | Truthful mode labels | **Yes.** Runs 5–6 explicitly identify Manila browser measurements; other runs identify Cloud Build. |
> | 6 | Unknowns preserved; no invented facts or numbers | **No.** Completed cleanup is asserted without a cleanup receipt; the referenced baseline says sessions were left for cleanup. Numerical provenance is recorded but was not independently retrieved. |
> | 7 | Complete commands, results and handoff | **No.** Packet lines 43–46 omit exact verification commands/results, interpreter, full-suite evidence and an exact next action. |
> | 8 | Consistent with product direction and invariants | **Yes.** The documentation-only change preserves domain contracts and distinguishes browser measurements from Cloud Build measurements. |
> 
> Verification performed, using the required `rtk` wrapper:
> 
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **failed**, exit 1; listed `docs/work/performance/perf-0.md`.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **863 tests; 187 errors, 35 skipped**. Errors include unavailable writable temporary directories in this read-only sandbox; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**. It requires an external cloud job and live session writes unavailable in this read-only, restricted-network review sandbox.
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | `docs/work/performance/perf-0.md:1` | New task record violates allowed-path stop condition. | Scope exits 1 and lists this file. | Move the record into an allowed packet location and rerun scope until it prints OK. |
> | important | `docs/work/performance/perf-0.md:30` | Claims complete cold/warm p50/p95 coverage that the baseline does not demonstrate. | Baseline lines 14–22: cold request is `/health`, subsequent grid requests are warm, and session/decision measurements lack separate cold populations. Run 2 explicitly omits cold timing; run 7 measures warm decision paths. | Record the missing route-level cold/warm measurements with sample counts and explicitly defined percentiles; correct the acceptance claim meanwhile. |
> | important | `docs/work/performance/perf-0.md:41` | Treats deferred cleanup as completed acceptance. | Baseline lines 37, 61, 84 and 104–105 leave sessions for future cleanup. Hosting intent specifies manual cleanup, not an automatic 48-hour process. | Have the authorized operator clean the test sessions and record actual commands, deletion counts and confirmation. |
> | important | `docs/work/performance/perf-0.md:45` | Verification and handoff cannot establish task closure. | Only abbreviated check names and build references appear; no exact hosted invocation, full offline-suite result or precise next action is recorded. | Add exact interpreter, commands, results, remaining work and next action, including scope and full-suite evidence from a capable environment. |
> 
> **Verdict: rework** — scope fails, required measurement coverage and cleanup remain unproven, and the verification record is incomplete.
**Verdict: rework.** Orchestrator disposition: (blocking) `perf-0.md` added to PERF-0's owned paths in `tasks.json`, scope OK; (important) the acceptance section now states exactly which populations are cold and which warm, and that session creation and the decision path have no cold population; (important) cleanup is recorded as pending until the operator runs `cleanup.py --apply` and the counts are written here; (important) exact commands, build ids, interpreter and next action added.

## Designated review 2 (GPT Sol, independent, commit `f1c30cd`, 2026-10-15)

> Independent review of `f1c30cd35be7480fb30d94bd2ceea2607b391389` against `feat/h1-api-persistence`. Inspected the requested diff and all three branch commits (`9662af4`, `0750990`, `f1c30cd`). Four documentation/coordination files changed; working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build measurements through `web.app` are recorded, but cold session/decision populations are explicitly absent, and cleanup deleted nothing. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes documentation and adds an owned path; no contracts, acceptance text or tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded timing runs and operator cleanup fall within the packet; no runtime dependency or service changes. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build runs and supporting Manila browser runs are distinguished; warm-instance measurements are identified. |
> | 6 | Unknowns preserved; no invented facts or numbers | **No.** Packet claims warm run-4 sample coverage absent from the baseline. Cloud receipts were not independently retrieved. |
> | 7 | Complete verification record and handoff | **No.** Interpreter and commands are improved, but hosted configurations/scripts are unavailable here, full-suite evidence is only an abbreviated PROGRESS result, and next action omits outstanding acceptance work. |
> | 8 | Consistent with product direction and invariants | **Yes.** No runtime or domain-contract changes; measurement limitations are largely explicit. |
> 
> Executed checks, all through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **863 tests, 187 errors, 35 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; external cloud jobs and live writes are unavailable in this read-only, restricted-network sandbox.
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/perf-0.md:35` | Required cold/warm route baseline remains incomplete. | Packet explicitly states session creation and decision paths have no cold population; cold samples elsewhere are single observations without reported p95. | Run and record missing Cloud Build cold/warm measurements, with revision, counts and p50/p95 per required route. |
> | important | `docs/work/performance/perf-0.md:78` | Cleanup invocation does not satisfy “test sessions cleaned.” | Receipt reports zero deletions and 84 younger memberships; cleanup is manual. | Have the operator remove the identified test sessions and record deletion counts and confirmation. |
> | important | `docs/work/performance/perf-0.md:34` | Packet overstates recorded warm coverage. | Claims runs 1–4 each have ten repeat grid loads and p50/p95; baseline run 4 records one grid load and no warm grid population. | Correct coverage to match recorded samples, or supply the missing run-4 results. |
> | important | `docs/work/performance/perf-0.md:68` | Verification and handoff remain insufficient for closure. | Suite result is indirect and abbreviated; referenced `.local/perf/` is absent here; next action proceeds toward acceptance without missing measurements and cleanup. | Record reproducible hosted instructions, complete suite results from a writable environment, and an exact next action addressing remaining acceptance items. |
> 
> **Verdict: rework** — required cold/warm measurement coverage and completed test-session cleanup remain undemonstrated.
**Verdict: rework.** Orchestrator disposition: cold session and decision populations taken (baseline run 9, Cloud Build `ae789869`: session as the first request to a cold instance 6.81 s, decision 2.11 s); test sessions deleted with the owner's authorisation (94 cases, 94 memberships, 47 Auth users); the warm-coverage sentence now names the runs that hold n=10 warm loads (1, 2, 3, 8) and excludes run 4; build ids for every run and the exact next action added.

## Designated review 3 (GPT Sol, independent, commit `03ed307`, 2026-10-15)

> Independent review of `03ed307cfcfb` against `feat/h1-api-persistence`, including the requested diff and all five branch commits. Four documentation/coordination files changed; working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cold per-route p50/p95 remain absent, and five run-9 sessions await cleanup (`perf-0.md:30–35,91–93`). |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes documentation and adds an owned path; no contracts, acceptance text or tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded hosted measurements and cleanup serve the task; cleanup records owner authorization (`perf-0.md:83`). No runtime dependencies added. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build HTTP measurements and Manila browser measurements are distinguished. |
> | 6 | Unknowns preserved; no unsupported numbers | **No.** The packet combines different cold request types into an “instance start” population and claims warm-load coverage not shown in run 9. No fabrication established. |
> | 7 | Complete verification record and handoff | **No.** Scripts/configurations are unavailable here; full-suite evidence is abbreviated; next action claims no remaining acceptance items despite outstanding cleanup. |
> | 8 | Consistent with direction and domain invariants | **Yes.** No runtime or domain-contract changes; the grid-first direction and no-warm-instance decision are preserved. |
> 
> Checks executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests; 187 errors, 37 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; external cloud jobs and live session writes are unavailable in this read-only, restricted-network sandbox. Cloud receipts were not independently retrieved.
> 
> All findings below remain unresolved.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/perf-0.md:30` | Required cold per-route percentile coverage remains incomplete. | Explicitly says cold figures have no p95. Run 9 measures a decision after session creation has already warmed the instance. | Record cold/warm populations and p50/p95 for the required routes, identifying precisely which request incurs startup. |
> | important | `docs/work/performance/perf-0.md:91` | Closure proceeds before test-session cleanup is complete. | Lines 92–93 acknowledge five run-9 sessions awaiting cleanup; the 03:31 cleanup predates run 9. | Clean those sessions under authorization, record actual results, and update remaining work. |
> | important | `docs/work/performance/perf-0.md:31` | Aggregation misrepresents request latency as instance-start timing. | Combines `/health`, event-page and session-request latencies across revisions; 6.81 s includes session provisioning. Line 38 also claims three warm grid loads absent from baseline run 9. | Separate startup logs from request latency; correct coverage claims to match recorded samples. |
> | important | `docs/work/performance/perf-0.md:73` | Verification cannot substantiate closure from the available record. | Full-suite result redirects to abbreviated `OK (skipped=35)` entries; referenced `.local/perf/` is absent. | Preserve inspectable scripts/configurations or equivalent build artifacts and exact complete suite results; make the next action address outstanding acceptance work. |
> 
> **Verdict: rework** — required cold percentile coverage and final test-session cleanup remain undemonstrated, with material evidence and handoff inconsistencies.
**Verdict: rework.** Orchestrator disposition: a cold population per route needs repeated idle waits, so one Cloud Build runs four idle-then-measure cycles (session as the first request, then a decision) to give n=5 with run 9; the cold observations are then reported per first-request type, not pooled; the run-9 and cycle sessions are removed by a policy cleanup afterwards and the counts recorded; the warm-load sentence drops run 9; the scripts' unavailability in the sandbox is stated as a limit (they create live sessions and stay out of Git by the lane rule).

## Designated review 4 (GPT Sol, independent, commit `4ec2ef7`, 2026-10-15 13:30 Manila)

> Independent review of `4ec2ef72f648ee719273c7448183397b915f9177` against `feat/h1-api-persistence`: inspected the requested diff and seven branch commits. Five documentation/coordination files changed; working tree clean. No files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cold/warm route coverage remains incomplete, and 12 test memberships remain (`perf-0.md:33–40,96–106`). |
> | 2 | All changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes documentation and an owned-path entry; no contracts, acceptance text or tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded hosted measurements and authorized cleanup serve the packet; no runtime dependencies or services added. |
> | 5 | Truthful mode labels | **No.** Browser/Cloud Build labels are clear, but cold state is inferred from latency, and mixed request timings are called “instance start” (`baseline.md:183–188`). |
> | 6 | Unknowns preserved; no unsupported numbers | **No.** Instance-state classifications lack corresponding startup evidence; pooled timings combine routes and revisions. No fabrication established. |
> | 7 | Complete verification record and handoff | **No.** Hosted scripts/configurations are unavailable here; current-commit suite results are absent; next action claims no remaining acceptance items despite retained sessions (`perf-0.md:81–107`). |
> | 8 | Consistent with direction and domain invariants | **Yes.** No runtime/domain-contract changes; grid-first direction and min-instances-zero policy remain intact. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests; 187 errors, 37 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**. External cloud jobs and live writes are unavailable in this read-only, restricted-network sandbox. Cloud receipts were not independently retrieved.
>
> All findings remain unresolved.
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/baseline.md:174` | Mixed warm/cold cycles do not demonstrate separate cold percentiles for every required route. | Two cycles explicitly answered warm; decisions and grid requests follow session creation, which already wakes Cloud Run. Earlier cold grid measurement remains n=1 without p95. | Record the missing cold/warm route statistics, defining cold state and identifying which request incurs startup. |
> | important | `docs/work/performance/baseline.md:183` | Latency alone cannot establish instance lifecycle or isolate startup duration. | Slow session responses are classified as starts; faster responses as warm. The pooled “instance start” values include `/health`, event-page and session responses across revisions. | Correlate samples with Cloud Run startup logs; report request latency separately from startup duration and keep populations comparable. |
> | important | `docs/work/performance/perf-0.md:96` | Cleanup acceptance remains incomplete. | Final receipt explicitly leaves 12 younger memberships; lines 104–106 nevertheless claim no remaining acceptance items. A future policy run is not completed cleanup. | Remove the remaining test sessions under authorization, record deletion counts, and correct the handoff until complete. |
> | important | `docs/work/performance/perf-0.md:81` | Verification evidence cannot establish closure on the reviewed commit. | Packet points to a current-commit PROGRESS suite result that is absent; hosted measurement scripts/configurations are unavailable for inspection. | Record complete current-commit suite results and provide reviewable hosted measurement instructions/artifacts. |
>
> **Verdict: rework** — required cold/warm evidence, completed test-session cleanup, and current-commit verification remain undemonstrated.

**Verdict: rework.** Orchestrator disposition: the cold state is now read from the Cloud Run instance and request logs
per cycle (baseline run 10, correlated section: three cold sessions, two warm because another visitor had started the
instance), instance startup is reported from the log as its own population (n=14, p50 6.2 s) separate from request
latency, first-request latency is per route and per revision, the Hosting route's independence from the instance is
stated, every test session was removed (three receipts, namespace empty at 05:34 UTC), the measurement scripts are in
`scripts/perf/`, and the suite result for the commit is in the PROGRESS log line. Review 5 requested.

## Designated review 5 (GPT Sol, independent, commit `c281d12`, 2026-10-15 13:36 Manila)

> Independent review of `c281d123c522` against `feat/h1-api-persistence`, covering the requested diff and eight branch commits. Working tree clean; no files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build/web.app runs and completed cleanup are recorded, but route-specific percentile reporting remains incomplete; see finding 1. |
> | 2 | All changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff adds measurement scripts and documentation; no frozen contracts, acceptance text or existing tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded timing runs and authorized cleanup serve the packet. No application dependency or service added. Browser tooling uses an existing local Playwright installation. |
> | 5 | Truthful mode labels | **Yes.** Browser measurements are distinguished from Cloud Build HTTP measurements; the added log correlation distinguishes cold and warm cycles (`baseline.md:195–205`). |
> | 6 | Unknowns preserved; no invented numbers | **No.** The retained pooled “instance start” statement still combines request latencies across routes and revisions (`baseline.md:183–188`), despite the corrected section below. No fabrication established. |
> | 7 | Complete verification record and handoff | **No.** Scripts and suite totals are now available, but the handoff claims no remaining acceptance items despite incomplete percentile reporting; it also incorrectly says scripts remain uncommitted (`perf-0.md`, opening and next-action sections). |
> | 8 | Consistent with direction and domain invariants | **Yes.** No application/domain-contract changes; grid-first delivery and min-instances-zero policy remain intact. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests, 187 errors, 37 skipped**. Errors include unavailable writable temporary directories in this sandbox; this is not a passing verification run.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; cloud jobs and live writes are unavailable in this read-only, restricted-network sandbox. Cloud receipts were not independently retrieved.
>
> All findings below remain open.
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/perf/baseline.py:120` | Summaries pool different data-file routes, preventing the required per-route baseline. | Samples use one `*:data` kind for all seven files; aggregation groups only by `kind`. The baseline predominantly reports aggregate grid-ready timing rather than n/p50/p95 for each required file. Same pattern exists in the variants. | Group by route and population; record revision, successful n, p50 and p95 for each required route, including separate log-confirmed cold-session/decision-workflow statistics. |
> | important | `scripts/perf/baseline.py:111` | Failed requests can contribute latency samples and a successful Cloud Build exit without demonstrating a successful judge workflow. | Session timings include non-200 responses; decision exceptions are printed and swallowed at line 115; read-back status is unchecked before recording `decide:total` at lines 91–93. Variants repeat this behavior. | Validate expected statuses and read-back results, report failures separately, and fail verification when required successful sample counts are unmet. Inspect existing run output before accepting its populations. |
> | minor | `docs/work/performance/baseline.md:183` | Contradictory retained interpretation mislabels request latency as startup duration. | Lines 186–187 pool `/health`, event and session latencies as “instance start”; lines 207–230 correctly distinguish startup from request latency. Line 188 also attributes an outlier to the after-start population although cycle 4 was warm. | Replace the superseded interpretation with the log-correlated classification and keep startup and request statistics separate. |
>
> **Verdict: rework** — required per-route reporting and successful-sample validation remain incomplete, although log correlation, script availability and recorded cleanup have improved.

**Verdict: rework.** Orchestrator disposition: the per-file populations and the status audit were recomputed from the
raw request lines of every run (kept under `.local/perf/logs/`) and written into the baseline ("Per route and per
file"); the superseded pooled reading in run 10 is replaced by a pointer to the correlated section; the handoff now
says the scripts are in `scripts/perf/` and names what remains unmeasured. No new run was needed. Review 6 requested.

## Designated review 6 (GPT Sol, independent, commit `d67762c`, 2026-10-15 14:14 Manila)

> Independent review of `d67762cd882c` against `feat/h1-api-persistence`, including the diff and nine commits. Working tree clean; no files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Hosted runs and cleanup receipts are recorded, but per-route reporting remains incomplete. Raw logs referenced by the status audit are unavailable in this worktree. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen contracts, acceptance text or existing tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded hosted timings and authorized cleanup fit the packet; no application dependency or service added. |
> | 5 | Truthful mode labels | **Yes.** Browser runs are distinguished from Cloud Build timings; log correlation distinguishes cold and warm cycles. |
> | 6 | Unknowns preserved; numbers supported | **No.** The new claim that scripts require HTTP 200 at every decision step contradicts the code. No fabrication established, but the claimed raw-log audit could not be checked. |
> | 7 | Complete verification record and handoff | **No.** Commands and suite totals are recorded, but the handoff claims no remaining acceptance items despite the findings below. |
> | 8 | Consistent with direction and domain invariants | **Yes.** No application/domain-contract changes; min-instances-zero and grid-first delivery remain intact. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests; 187 errors, 37 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; the read-only, restricted-network sandbox does not permit the cloud job and live writes. Cloud receipts were not independently retrieved.
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/perf/baseline.py:111` | Failed requests can enter timing populations while verification exits successfully. | Session timings include non-200 responses; decision exceptions are swallowed at line 115; read-back status is unchecked before `decide:total`. Variants repeat this behavior. `baseline.md:242` incorrectly claims every step requires 200. | Validate expected statuses and read-back results, exclude failures, and fail when required successful sample counts are unmet. Supply reviewable status-audit evidence for existing runs and correct the claim. |
> | important | `docs/work/performance/baseline.md:260` | Required per-route baseline remains incomplete across revisions and populations. | Only run 8 has a complete per-file percentile table. Earlier revisions and run 10 give ranges across files; the log-confirmed cold session and subsequent decision populations report medians without p95. | Record revision, successful n, p50 and p95 for each required route and population, including earlier deploy baselines; explicitly identify unavailable measurements. |
> | minor | `docs/work/performance/perf-0.md:113` | Handoff overstates completion and retains inconsistent measurement limits. | “Remaining acceptance items: none known” conflicts with incomplete reporting; lines 114 and 49 retain startup population n=6 although the correlated baseline reports n=14. Opening text also says scripts are uncommitted. | Reconcile the packet with the committed scripts, current populations and unresolved findings. |
>
> **Verdict: rework** — per-route acceptance evidence remains incomplete, and the measurement scripts still permit failed workflows to appear in successful timing runs.

**Verdict: rework.** Orchestrator disposition: the scripts now record a non-200 answer as a failure and exit non-zero
(the recorded runs had none); the baseline carries the per-file p50/p95 table for every run and revision and states
p95 for the n=3 cold populations; the handoff names the per-route coverage and the n=14 startup population. Review 7
requested.

## Designated review 7 (GPT Sol, independent, commit `9eb0179`, 2026-10-15 14:19 Manila)

> Independent review of `9eb0179388da`, using `git diff feat/h1-api-persistence...HEAD` and `git log feat/h1-api-persistence..HEAD`. Working tree clean; no files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Build IDs, cold/warm tables and cleanup results are recorded, but raw logs referenced at `.local/perf/logs/` are unavailable here. Contradictory baseline values also prevent accepting the measurement output. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence` printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Diff changes documentation, task ownership and measurement scripts; no frozen contract, acceptance text or existing test changed. |
> | 4 | No effects or dependencies beyond packet | **Yes.** Hosted timing and test-session writes match the packet. Browser measurements use an existing local Playwright installation; no application dependency added. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build HTTP measurements and Manila browser measurements are distinguished; scripts disclose live session writes. |
> | 6 | Unknowns preserved; numbers supported | **No.** Baseline line 271 contradicts both run 1’s table and its per-file timings; see finding below. |
> | 7 | Complete verification and handoff record | **No.** Interpreter, historical commands, cleanup and next action are recorded, but the latest PROGRESS entry omits the current commit’s suite result and the packet refers readers there. |
> | 8 | Consistent with product and domain invariants | **Yes.** No application semantics changed; source-derived cutoff, expected heads and retain disposition remain explicit in the probes. No model-skill claim introduced. |
>
> Findings, all unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/baseline.md:271` | Misattributes improved timings to the original baseline, corrupting the before/after comparison. | Claims run 1 warm grid-ready p50 **0.303 s**, while line 17 says **1.46 s** and run 1’s nodes alone have warm p50 **1.294 s**. Its 1.43 s first-load value also matches run 2’s narrative. | Recompute from the identified build logs and reconcile every conflicting summary. |
> | important | `scripts/perf/baseline.py:69` | Failed requests still enter successful aggregate timing populations. Same pattern exists in the other three Python timing variants. | An in-memory probe returning HTTP 500 for HTML and data produced a `warm:grid_ready` sample in all four variants. A failed final read likewise reaches `decide:total` at line 99. | Append aggregate samples only after every constituent request succeeds; test failed HTML, data and final-read responses. |
> | important | `scripts/perf/cold_session.py:116` | First-decision exceptions can leave the run successful despite missing cold-decision evidence. | Handler prints the exception without adding it to `FAILURES`; exit status depends solely on `FAILURES`. | Count this exception as a failure and verify a nonzero exit. |
> | important | `scripts/perf/cold_cycles.yaml:4` | A failed earlier cycle can be hidden by a successful final cycle. | Shell loop has no fail-fast behavior or accumulated failure status; its final command determines success. | Propagate any cycle failure to the build exit status. |
> | minor | `docs/work/performance/perf-0.md:79` | Current verification evidence is incomplete. | Suite result is delegated to PROGRESS, whose latest commit entry records no suite result. | Record the exact current-revision command and result, plus remaining verification limits. |
>
> Verification executed with `/usr/bin/python3`:
>
> - `scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **OK**
> - `scripts/plan.py check`: **OK — 59 tasks, 7 gates**
> - `scripts/repo.py check`: **PASS**
> - `-m unittest discover -s tests`: **872 tests; FAILED, 187 errors, 37 skipped**. Sandbox temporary-directory restrictions caused errors; this is not a passing suite.
> - In-memory failure probes: confirmed failed requests enter grid-ready populations; no network calls or file edits.
>
> The hosted verify step, `orchestrator: Cloud Build hosted timing run`, **was not run**: this sandbox restricts network access and filesystem writes. Historical cloud and cleanup results remain recorded evidence, not independently re-executed checks.
>
> **Verdict: rework** — contradictory baseline values and incomplete failure propagation leave important measurement-integrity findings unresolved.

**Verdict: rework.** Orchestrator disposition: the grid-ready per-run line is recomputed from the build logs (run 1
warm 1.526 s, not 0.303 s, which was run 2's) and says which figure to read where an earlier narrative differs; the
scripts record an aggregate only when every constituent answered 200, count a first-decision exception as a failure,
and the four-cycle build fails on any failed cycle; the suite result is written from the run. Review 8 requested.

## Designated review 8 (GPT Sol, independent, commit `efb071a`, 2026-10-15 14:31 Manila)

> Independent review of `efb071ad368f` against `feat/h1-api-persistence`, including the requested diff and commit log. No files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build IDs, cold/warm populations and cleanup results are recorded, but referenced raw logs are unavailable here. Two reproduced defects still allow failed measurements into successful aggregate populations. |
> | 2 | Changes within allowed paths | **Yes.** The requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No application contracts, acceptance text or existing tests changed in the diff. |
> | 4 | No dependencies or effects beyond the packet | **Yes.** Hosted timing and test-session writes fit the packet; no application dependency added. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build HTTP timings and Manila browser measurements are distinguished; scripts disclose live writes. |
> | 6 | Unknowns preserved; no unsupported numbers | **No.** Failure probes produced successful aggregate samples from failed requests; see findings. Historical measurements were not independently retrieved. |
> | 7 | Complete verification and handoff record | **Yes.** The packet records interpreter, commands, suite result, cleanup, limitations and next action. Some stale statements remain. |
> | 8 | Consistent with product and domain invariants | **Yes.** No application semantics changed; probes retain cutoffs, expected heads and explicit retain decisions. No forecast-skill claim added. |
>
> All findings below remain unresolved.
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/perf/cold_first.py:125` | The initial page-first aggregate bypasses status validation and enters the successful timing population after failed requests. | In-memory execution with HTTP 500 for HTML and all seven files recorded eight failures **and** `first:grid_ready` in `samples`. | Require all eight requests to succeed before appending the initial aggregate; verify failed HTML and data responses. |
> | important | `scripts/perf/cold_session.py:124` | Unconditionally relabeling `samples[-1]` can turn a successful individual request into a cold decision total after the decision fails. | Injecting HTTP 500 on final read produced two failures and a successful `cold:decide_total` containing the **review request’s 0.2 s**, rather than total decision time. | Return an explicit successful aggregate from `decide`; label and append it only on success. Never mutate the previous sample. |
> | minor | `docs/work/performance/perf-0.md:10` | Stale handoff statements contradict the committed artifacts and current coverage. | Opening says scripts are uncommitted; line 43 says run 4 has no warm population, while baseline lists ten warm loads; line 54 retains startup n=6 versus n=14 later. | Reconcile the packet with committed scripts and current population tables. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **OK**.
> - `/usr/bin/python3 scripts/plan.py check`: **OK — 59 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check`: **PASS**.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests`: **872 tests; 187 errors, 37 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - In-memory failure probes: reproduced both important findings without network calls or file edits.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; the sandbox restricts network access and writes. Historical cloud and cleanup results remain recorded evidence.
>
> **Verdict: rework** — failed requests can still produce successful aggregate timing samples, so measurement integrity and acceptance remain insufficiently demonstrated.

**Verdict: rework.** Orchestrator disposition: every grid-ready aggregate now stands only when the page and all seven
files answered 200, read from each request's own answer (the reviewer's injected failures would be counted as
failures); the cold relabel in `cold_session.py` applies only to a decision that produced a total, else a failure is
recorded; the three stale sentences in the record are reconciled. Review 9 requested.

## Designated review 9 (GPT Sol, independent, commit `7c0296f`, 2026-10-15 15:45 Manila)

> Independent review of `7c0296fe8972` against `feat/h1-api-persistence`, including the branch diff and 14 commits. Working tree clean; no files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Timing populations and cleanup results are recorded in `baseline.md` and `perf-0.md:95–108`, but the hosted verification was not run here and cloud receipts were not independently retrieved. Acceptance remains unconfirmed. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff adds measurement scripts and records; no frozen contracts, acceptance text or existing tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Hosted timing and session cleanup serve the packet; no application dependency or service configuration changes. |
> | 5 | Truthful mode labels | **Yes.** Packet distinguishes Cloud Build HTTP timing, Manila browser runs, cold sessions and decisions after startup. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes, within inspected evidence.** Correlated run-10 records distinguish two cold and two warm cycles and disclose small populations. No fabrication established; cloud numbers remain independently unverified. |
> | 7 | Complete verification record and handoff | **No.** Commands, results and next action exist, but the packet contains stale script-provenance statements and failure handling still permits a misleading successful build. |
> | 8 | Consistent with direction and domain invariants | **Yes.** No application semantics changed; Hosting-first delivery and min-instances-zero direction remain intact. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests, 187 errors, 37 skipped**. Errors include unavailable writable temporary directories; this is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; this read-only, restricted-network sandbox cannot perform the cloud job and live session writes.
>
> Findings, all unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/perf/perf3.yaml:4` | A failed old-path measurement can produce a successful Cloud Build. | Commands use semicolons without failure accumulation or `set -e`; Bash returns the final prepare script’s status, masking an earlier nonzero exit. | Fail immediately or accumulate both script statuses and exit nonzero if either fails. |
> | minor | `scripts/perf/baseline.py:77` | Failed aggregates emit a previous successful sample again, corrupting request-log counts. | Failure branch appends to `FAILURES`, then unconditionally prints `samples[-1]`. Same pattern exists in all four Python timing variants and their decision totals. | Print the record created by the current branch, including the failure record. |
> | minor | `docs/work/performance/perf-0.md:14` | Script provenance contradicts the reviewed tree. | Says scripts are not committed; line 79 says copied unchanged, although subsequent commits modify their failure handling. | Describe the committed scripts and distinguish historical run versions from current corrected versions. |
>
> **Verdict: rework** — the comparison build can conceal a failed measurement, and hosted acceptance remains unconfirmed in this review.

**Verdict: rework.** Orchestrator disposition: `perf3.yaml` accumulates both scripts' statuses; every failure branch
prints its own failure record and every aggregate branch the record it created; the record distinguishes the
script versions the runs used from the hardened committed ones. Review 10 requested.

## Designated review 10 (GPT Sol, independent, commit `b7f32e6`, 2026-10-15 16:05 Manila)

> Independent review of `b7f32e65df33` against `feat/h1-api-persistence`, including the requested diff and all 16 branch commits. Working tree clean; no files edited.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build runs through `web.app` and completed cleanup are recorded, but the intent’s cold/warm baseline on `00006-ttp` lacks cold route populations; run 1 wakes the instance through `/health` before measuring the required routes. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff adds measurement scripts and records; no frozen contracts, acceptance text or tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded hosted measurements and cleanup serve the packet; cleanup authorization is recorded at `perf-0.md:102`. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build HTTP timing and supporting Manila browser measurements are distinguished; warm cycles are explicitly identified. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** Small populations and interference from other traffic are disclosed. No fabrication found; cloud receipts were not independently retrieved. |
> | 7 | Complete verification record and handoff | **No.** Commands, interpreter, suite results and cleanup are recorded, but `perf-0.md:115` declares no remaining acceptance items despite missing original-revision coverage. |
> | 8 | Consistent with direction and domain invariants | **Yes.** No runtime/domain contract changes; no-warm-instance direction and data boundaries remain intact. |
>
> Checks executed through `rtk proxy`:
>
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests, 187 errors, 37 skipped**; errors include unavailable writable temporary directories. This is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; the read-only, restricted-network sandbox prevents the external job and live writes.
>
> All findings remain unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/baseline.md:254` | Later revisions’ cold measurements cannot establish the required original-revision cold baseline. | Intent requires cold/warm p50/p95 for the required routes on `00006-ttp`; run 1 measures those routes after cold `/health`. Its cold `/` evidence at line 222 is server-side request logging, not Cloud Build client timing; cold session coverage begins on later revisions. | Supply qualifying original-revision measurements, or return the unmet historical requirement to the guardian for an explicit intent disposition; update the handoff accordingly. |
> | minor | `scripts/perf/cold_first.py:116` | First-load aggregate includes an extra HTML request, making it differ from the stated page-plus-seven-files sequence. | Timer starts at line 114; `/` is fetched at both lines 115 and 116 before data requests. Warm aggregates fetch HTML once. | Extract the build stamp from the first HTML response and remove the second fetch; disclose its contribution to historical run-4 timing. |
>
> **Verdict: rework** — required original-revision cold/warm coverage remains undemonstrated, so acceptance cannot be granted.

**Verdict: rework.** Orchestrator disposition and escalation to the owner. The minor finding is fixed: `cold_first.py`
reads the build stamp from the first page answer and fetches the page once. The important finding cannot be met by
measurement: it asks for cold p50/p95 on the original revision `00006-ttp` for every route. That revision was
replaced on 2026-10-14; run 1's cold evidence on it is one first request (`/health`, 6.19 s client, instance startup
5.8 s in the Cloud Run log) and the request log's cold `GET /` answers (6.39 s, 6.72 s), and later revisions carry the
cold populations per route. Re-measuring a retired revision would mean routing live traffic back to it, which the
owner has not authorised and which the lane's intent does not require. The record states what exists for `00006-ttp`
and what does not. **The owner decides** whether the baseline is accepted with that limitation stated; the
orchestrator does not record an accept.


## Designated review (GPT Sol, independent, commit `fb4a12c`, 2026-10-15)

> Independent review of `b7f32e65df33` against `feat/h1-api-persistence`, including the requested diff and all 16 branch commits. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cloud Build runs through `web.app` and completed cleanup are recorded, but the intent’s cold/warm baseline on `00006-ttp` lacks cold route populations; run 1 wakes the instance through `/health` before measuring the required routes. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff adds measurement scripts and records; no frozen contracts, acceptance text or tests changed. |
> | 4 | No effects beyond the packet | **Yes.** Recorded hosted measurements and cleanup serve the packet; cleanup authorization is recorded at `perf-0.md:102`. |
> | 5 | Truthful mode labels | **Yes.** Cloud Build HTTP timing and supporting Manila browser measurements are distinguished; warm cycles are explicitly identified. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** Small populations and interference from other traffic are disclosed. No fabrication found; cloud receipts were not independently retrieved. |
> | 7 | Complete verification record and handoff | **No.** Commands, interpreter, suite results and cleanup are recorded, but `perf-0.md:115` declares no remaining acceptance items despite missing original-revision coverage. |
> | 8 | Consistent with direction and domain invariants | **Yes.** No runtime/domain contract changes; no-warm-instance direction and data boundaries remain intact. |
> 
> Checks executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/plan.py scope PERF-0 feat/h1-api-persistence`: **passed**.
> - `/usr/bin/python3 scripts/plan.py check`: **passed**, 59 tasks, 7 gates.
> - `/usr/bin/python3 scripts/repo.py check`: **passed**.
> - `/usr/bin/python3 -B -m unittest discover -s tests`: **872 tests, 187 errors, 37 skipped**; errors include unavailable writable temporary directories. This is not a passing suite.
> - `orchestrator: Cloud Build hosted timing run`: **not run**; the read-only, restricted-network sandbox prevents the external job and live writes.
> 
> All findings remain unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/performance/baseline.md:254` | Later revisions’ cold measurements cannot establish the required original-revision cold baseline. | Intent requires cold/warm p50/p95 for the required routes on `00006-ttp`; run 1 measures those routes after cold `/health`. Its cold `/` evidence at line 222 is server-side request logging, not Cloud Build client timing; cold session coverage begins on later revisions. | Supply qualifying original-revision measurements, or return the unmet historical requirement to the guardian for an explicit intent disposition; update the handoff accordingly. |
> | minor | `scripts/perf/cold_first.py:116` | First-load aggregate includes an extra HTML request, making it differ from the stated page-plus-seven-files sequence. | Timer starts at line 114; `/` is fetched at both lines 115 and 116 before data requests. Warm aggregates fetch HTML once. | Extract the build stamp from the first HTML response and remove the second fetch; disclose its contribution to historical run-4 timing. |
> 
> **Verdict: rework** — required original-revision cold/warm coverage remains undemonstrated, so acceptance cannot be granted.
**Verdict: accept.** accepted with the original-revision limitation stated
