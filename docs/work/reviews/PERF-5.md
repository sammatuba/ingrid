
## Designated review 1 (GPT Sol, independent, commit `982eb0f`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...982eb0f`, including commits `67cf4c0` and `982eb0f`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Offline staging, refusal, config, deployment ordering, warm-up failure handling and export exclusions pass focused tests. Real Hosting deployment, cold-screen timing and browser verification here remain undemonstrated. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside PERF-5 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened | **Yes.** No frozen contracts or acceptance text changed. Replaced Hosting assertions reflect the authorized static-file policy; other changes add checks. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Stager uses stdlib; `/health` is explicitly required. Diff adds no other service, credential or runtime dependency. |
> | 5 | Truthful mode labels | **Yes.** Tests use labelled synthetic fixtures; packet distinguishes offline evidence from outstanding deployment and timing. |
> | 6 | Unknowns remain unknown | **Yes.** No invented case facts or receipts found; cold performance is explicitly unclaimed. |
> | 7 | Complete execution/handoff record | **Yes.** `perf-5.md` records interpreters, commands, results, an intermittent failure, unfinished work and next actions. |
> | 8 | Consistent with governing intent/invariants | **No.** Broad immutable header rules include unversioned routes, contrary to the performance intent’s versioned-only caching rule. |
> 
> Findings:
> 
> **important | scripts/deploy/firebase.json:7 | Unversioned responses receive an immutable cache policy |** `/grid-data/**` matches `/grid-data/events/<id>.json`, which remains unstaged and is served `no-store` by the application. `/grid/**` similarly includes unversioned assets. Firebase documents that custom-header matching occurs before rewrites ([official documentation](https://firebase.google.com/docs/hosting/full-config#headers)). `tests/test_hosting_stage.py:399` omits the unversioned event route from its negative assertions; the packet acknowledges the unresolved interaction. **Correction:** restrict immutable rules to stamped paths, add negative assertions for unversioned routes, and verify resulting headers through Hosting. Live header precedence was not measured here.
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **FAILED:** 826 tests, 1 setup error, 25 skipped. Browser harness could not bind localhost: sandbox `listen EPERM`; this does not establish a code regression.
> - Focused hosting/config/cache suite — **OK:** 174 tests, 13 skipped.
> - `tests.test_grid_page.RenderedPage` — **OK:** 11 tests.
> - Requested scope command — **OK**.
> - `scripts/plan.py check` — **OK**.
> - `scripts/repo.py check` — **PASS**.
> 
> **Verdict: rework — narrow the immutable cache rules and demonstrate the outstanding acceptance checks before acceptance.**
**Verdict: rework.** Immutable header rules must match ONLY files that Hosting itself serves from build/hosting at the CURRENT build stamp: generate the Hosting config at staging time with the exact stamp (sources /grid/<stamp>/** and /grid-data/<stamp>/**, or the equivalent exact regex), so unversioned routes (/grid-data/events/<id>.json, /grid/<file>), other or unknown stamps (proxied to Cloud Run, 404 no-store) and every API/session route get no Hosting cache header. Keep / and /index.html no-cache. Add negative tests over the generated config for: /grid-data/events/<id>.json, /grid/grid.js, /grid-data/<other-stamp>/x.json, /grid/<other-stamp>/x, /health, /demo/session, /v1/..., /event/<id>. deploy.sh must deploy with the generated config, and --dry-run must name it. Live Hosting deploy, header checks via web.app and cold timing stay orchestrator steps; record them as outstanding, do not claim them. Address every blocking/important row above; dispose of minors explicitly.

## Designated review 2 (GPT Sol, independent, commit `6a6f3ae`, 2026-10-14)

> Independent review of `task/PERF-5` at `6a6f3ae`, against `feat/h1-api-persistence`; inspected the three-dot diff and all six branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Staging, stamp checks, generated cache rules, deploy ordering, warm-up and export exclusions have tests. The packet explicitly leaves the production deploy and cold timing outstanding; preview evidence does not demonstrate those required steps. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside PERF-5 allowed paths`. |
> | 3 | Contracts and acceptance unchanged; tests not weakened | **Yes.** Frozen contract files and acceptance text are unchanged. Previous Hosting expectations were replaced with assertions for the authorized static-file design, including generated-config negative checks; no skips were added. |
> | 4 | No unplanned dependency or external effect | **Yes.** Stager uses the standard library. The added `/health` request and Hosting deployment are named in the packet; no new service, SDK or credential is introduced. |
> | 5 | Truthful mode labels | **Yes.** Tests use labelled synthetic replay fixtures; the packet distinguishes preview Hosting files from the live Cloud Run service and production deployment. |
> | 6 | Unknowns remain unknown | **Yes.** No case facts, model receipts or judgment semantics changed. Production cold timing remains explicitly outstanding; preview timings are identified by their environment. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreters, commands, results, prior failure, unfinished work and exact next actions. Task and progress remain `in_progress`. |
> | 8 | Consistent with product and domain invariants | **Yes.** Change concerns delivery and caching, preserves review semantics, and tests Git/export exclusion of Hosting artifacts under the owner-authorized design. |
> 
> Commands executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **failed:** 842 tests, one setup error, 25 skips. `BrowserPage` received empty JSON because its loopback server failed with `listen EPERM … 127.0.0.1`; confirmed by running the harness directly. Browser behavior could not be independently verified in this sandbox.
> - `/usr/bin/python3 scripts/plan.py scope PERF-5 feat/h1-api-persistence` — **OK**.
> - `scripts/plan.py check` — **OK: 59 tasks, 7 gates**.
> - `scripts/repo.py check` — **PASS**.
> - Stager, hosted-config and cache modules — **190 tests passed, 13 skips**.
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | [docs/work/performance/perf-5.md:579](../../../docs/work/performance/perf-5.md) | Required production deployment and cold-screen measurement are deferred until after acceptance, leaving acceptance incomplete. | Lines 556–558 identify a preview deployment with a different stamp from the live service; lines 579–580 explicitly leave production release and Cloud Build timing outstanding. | Orchestrator completes the authorized production release through `deploy.sh`, records production headers and cold first-screen timing with revision/sample evidence, then requests review again. Under two seconds remains a goal. |
> 
> **Verdict: rework** — the cache-rule rework is supported, but required production deployment and cold-screen evidence remain undemonstrated.
**Verdict: rework.** No code finding; the production release and the cold first-screen timing were outstanding. Recorded late (2026-10-15) by the orchestrator: the output file existed but had not been copied here. The production release followed the same day (`grid-nowcast-00008-5ln`, packet section "Production release").

## Designated review 3 (GPT Sol, independent, commit `a6cb010`, 2026-10-15)

> Independent review of `feat/h1-api-persistence...a6cb010a6d657682d1beacc7f4a2b1b9c654b431`, including the branch log and clean working tree. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Staging/config tests and deployment evidence are recorded, but the timing run warmed Cloud Run with `/health` before loading the page; it does not demonstrate the required cold first screen. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside PERF-5 allowed paths`. |
> | 3 | No frozen contract or acceptance changes; no weakened/skipped tests | **Yes.** Diff leaves frozen contracts and acceptance text unchanged. Hosting assertions reflect the authorized policy; additional tests cover generated headers and refusals. |
> | 4 | No effects beyond the packet | **Yes.** Stager uses stdlib; `/health` is required by the brief. Packet identifies the production release as owner-run. |
> | 5 | Truthful mode labels | **No.** Synthetic/replay labels remain intact, but `perf-5.md:603` labels a post-warm-up measurement “with the instance cold.” |
> | 6 | Unknowns preserved; no invented facts, receipts or numbers | **Yes.** No invented case facts or receipts found. The timing issue is an unsupported interpretation of recorded measurements. |
> | 7 | Complete execution and handoff record | **Yes.** Packet records interpreters, commands, results, failures, deployment references and next actions; later sections supersede earlier outstanding-work lists. |
> | 8 | Consistent with governing direction and invariants | **No.** Hosting implementation follows the owner decision, but the cold-screen completion claim exceeds its measurement evidence. |
> 
> Finding:
> 
> **important | docs/work/performance/perf-5.md:603 | Cold-screen acceptance is claimed from a warmed-service measurement |** Lines 610–611 explicitly say `/health` wakes the instance before page loading; lines 603 and 607–608 nevertheless claim a cold first screen and achievement of the goal. Hosting delivery supports the architectural conclusion, but this sequence does not measure it under the required condition. **Correction:** label the existing result as Hosting-file timing after service warm-up; run a browser visit through production `web.app` before any preliminary service request, measure first useful render, and record the revision, sample count and observed result.
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **FAILED:** 841 tests, 188 errors, 25 skipped. Read-only filesystem prevents temporary files and test artifacts; this does not establish a code regression.
> - Requested `plan.py scope PERF-5 feat/h1-api-persistence` — **OK**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - Focused config/export/render checks — 19 tests, 3 sandbox temporary-directory errors; 16 passed, including warm-up and failure handling.
> - `deploy.sh --dry-run` — **passed**, showing staging, checking and generated-config deployment in order.
> 
> **Verdict: rework — correct the unsupported cold-screen claim and demonstrate that remaining acceptance check before acceptance.**
**Verdict: rework.** The Cloud Build `b4e996fe` run requested `/health` before the page, so its 0.85 s is Hosting-file timing after service warm-up, not the cold first screen. Orchestrator disposition: the packet's reading is relabelled (no cold claim), and a second cold run whose first request is the page itself was run as Cloud Build `6a9786f3` (packet section "Cold first screen, page-first order": grid ready 0.86 s, the first service request afterwards 6.51 s, so the instance was cold). No executor rework: the finding was about measurement, not code. Review 4 next.

## Designated review 4 (GPT Sol, independent, commit `bf15a53`, 2026-10-15)

> Independent review of `bf15a53c02e6` against `feat/h1-api-persistence`; inspected the three-dot diff and all 10 branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Staging, stamped configuration, deployment ordering, warm-up and export exclusions have tests and recorded runs. Cold **first useful screen** remains unmeasured: the latest run measures HTTP arrival, explicitly excluding browser render time (`perf-5.md:637`). |
> | 2 | Changes confined to allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-5 allowed paths`. Working tree clean. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff changes deployment, grid warm-up, tests and records; no frozen contract or acceptance changes. Existing assertions remain, with additional warm-up/config checks. |
> | 4 | No unlisted dependencies or external effects | **Yes.** Stager uses the standard library; `/health` is required by the brief. Packet attributes deployment to the owner and timing to the orchestrator. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures and deployed replay remain labelled; the final measurement explicitly identifies its stdlib HTTP method. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** No invented case facts or receipts found. The unsupported timing interpretation is addressed below. |
> | 7 | Complete execution and handoff record | **Yes.** Packet records interpreters, commands, results, failures, deployment references, limitations and next review action. |
> | 8 | Consistent with governing direction and invariants | **No.** Implementation follows the owner’s Hosting decision, but claiming achievement of the first-useful-screen goal exceeds the recorded measurement. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **failed:** 841 tests, 188 errors, 25 skipped. Read-only sandbox prevents temporary files and test artifacts; this does not establish a code regression.
> - `/usr/bin/python3 scripts/plan.py scope PERF-5 feat/h1-api-persistence` — **OK**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - Focused configuration, Git/export exclusion and warm-up checks — **16 tests passed**.
> - `deploy.sh --dry-run` — **passed**, showing stage → check → generated-config Hosting deployment.
> 
> Finding, unresolved:
> 
> **important | docs/work/performance/perf-5.md:631 | HTTP arrival is treated as first useful screen completion | Lines 631–633 claim the goal was met in 0.86 s, while lines 636–637 explicitly say browser first useful render was not measured; JS/CSS/font loading, parsing and rendering are outside this measurement | Retain 0.86 s as HTTP page-and-data timing, remove the goal-achieved claim, and record a page-first cold browser visit through production `web.app` measuring the rendered useful screen.**
> 
> **Verdict: rework — the implementation is supported, but the required cold first-screen timing is not yet demonstrated by a render measurement.**
**Verdict: rework.** HTTP arrival is not a render measurement. Orchestrator disposition: the goal-met sentence is withdrawn; a cold browser visit through production `web.app` is recorded in the packet section "Cold first useful screen in a browser" (LCP 2.86 s from Manila with the instance proven cold by the Cloud Run log; above the 2 s goal, which stays a goal). Review 5 next.

## Designated review (GPT Sol, independent, commit `0e282d7`, 2026-10-15)

> Independent review of `feat/h1-api-persistence...0e282d7`, including all 11 branch commits and the clean working tree. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Packet records passing stager/config/refusal tests, production deployment and headers, and a cold browser measurement (`perf-5.md:639–660`). LCP was **2.86 s**; under 2 s remains an unmet goal, not a required threshold. Historical runs were not independently repeated here. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside PERF-5 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes.** Frozen contracts and acceptance text unchanged. Hosting assertions follow the authorized policy change; added tests cover stamped rules, refusals and warm-up failures. |
> | 4 | No effects beyond the packet | **Yes.** Stager uses stdlib; `/health` is explicitly required. Deployment is recorded as owner-run and timing as orchestrator work. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures and replay remain labelled; corrected packet separates warmed-service HTTP timing, page-first HTTP timing and browser rendering. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** No invented case facts or receipts found. Browser timing identifies revision, location and one-sample limitation. |
> | 7 | Complete execution and handoff record | **Yes.** Packet includes interpreters, commands, results, prior failures, deployment evidence and the next independent review action. |
> | 8 | Consistent with governing direction and invariants | **Yes.** Implements the owner-approved Hosting option, preserves review semantics and export exclusions, and keeps dynamic routes on Cloud Run. |
> 
> Verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **attempted; failed:** 841 tests, 188 errors, 25 skipped. Read-only sandbox blocked temporary directories and test output files; this does not demonstrate a code regression.
> - `/usr/bin/python3 scripts/plan.py scope PERF-5 feat/h1-api-persistence` — **OK**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - Focused configuration, Git/export exclusion, stamped URL and warm-up checks — **16 passed**.
> - `deploy.sh --dry-run` — **passed**, showing stage → check → Hosting deployment with the generated config.
> 
> Findings: **None blocking, important or minor.** Earlier cold-screen evidence findings are addressed by the corrected interpretation and recorded cold browser run.
> 
> **Verdict: accept — all required acceptance items have demonstrated evidence, with no unresolved material finding; the 2 s performance goal remains unmet and is reported accurately.**
**Verdict: accept.** First screen from Hosting with no Cloud Run dependency; cold browser LCP 2.86 s reported as an unmet goal.
