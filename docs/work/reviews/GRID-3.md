# GRID-3 review record

## Orchestrator finding (2026-10-14, not a designated review)

See `docs/work/grid-desk/event.md`, "Orchestrator image check and finding". Fix `.dockerignore` so the image carries
`docs/work/permissions/` and nothing else from `docs`, with a test; keep everything else as it is. The designated
reviewer (Sol) is out of credits tonight; your work stays in progress until it reviews.

## Designated review 1 (GPT Sol, independent, commit `2038bbf`, 2026-10-14)

> Independent review of `task/GRID-2...2038bbf`; inspected the diff and commit log. No files edited.
> 
> Verification executed:
> 
> - Required event suite: **30 tests, OK, 3 skipped**.
> - HTTP-enabled rerun: **blocked by sandbox socket permissions** (`PermissionError`); HTTP behavior was not independently verified.
> - Full offline suite: **618 tests, OK, 12 skipped**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - `plan.py scope GRID-3 task/GRID-2`: **failed**, listing 14 paths outside the allowed scope.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes**, for the brief’s three items: executed `JudgeFlow`, `SeededSession`, and `CaseRecords` tests demonstrate account-free decisions/history, session isolation, and permission references. Cited judgment display from the broader intent remains unverified: the adapter fixture has `judgment: null`. |
> | 2 | Only allowed paths changed | **No**. Requested scope check failed on EVAL-5 case/fixture files, its review record, the grid intent, and the session report. The log identifies inherited integration/EVAL-5 commits. |
> | 3 | Frozen contracts, acceptance text, tests preserved | **Yes**. No frozen review/judgment implementation changed in the range; GRID-3 acceptance text is unchanged. Added conditional HTTP skips are explicit; no existing test was weakened or removed. |
> | 4 | No unapproved dependency or external effect | **Yes**. Runtime changes read local case data and use existing repository/API ports; no new dependency or model call. |
> | 5 | Truthful mode labels | **Yes**. Harness data identifies itself as a shape fixture; recorded judgment is described as stored, not live inference on load. |
> | 6 | Unknowns remain unknown | **Yes**. Executed source-clock and dispatch tests preserve unknown availability; capacity comes from the register run. |
> | 7 | Complete verification and handoff packet | **Yes**. `event.md` records interpreters, commands/results, deviations, unfinished work, and next actions. |
> | 8 | Consistent with intent and invariants | **No**. History failures are silently swallowed despite the explicit refusal requirement; repeated decisions after revision use a stale snapshot. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | docs/work/grid-desk/intent.md:127 | Requested review range exceeds GRID-3’s allowed paths. | Scope command exits 1 with 14 disallowed paths; log includes the integration merge and EVAL-5 commits. | Have the orchestrator reconcile the branch/base or authorize the expanded review scope, then obtain a passing scope check. |
> | important | src/grid/event-api.js:103 | Every decision snapshots the original seeding instant, excluding revisions already accepted in this session. | Reproduced `revise → retain` through the existing route harness: second decision raises `STALE_HEAD`; history remains at one entry. Existing test covers only `retain → revise`. | Snapshot the current accepted state for subsequent decisions while preserving the historical information cutoff; test a decision following revision. |
> | important | src/grid/event-api.js:157 | Failed history requests become an empty history without explaining the failure. | Non-OK responses and malformed bodies return `[]`; intent item 4 requires refusal codes and sentences to be shown. | Propagate and display history errors; test authorization, storage, and malformed-response failures. |
> 
> **Verdict: rework** — scope fails against the requested base, and two evidenced adapter defects remain unresolved.
**Verdict: rework.** The blocking scope row is the orchestrator's: the review used task/GRID-2 as base, but this branch merged the integration branch at f429d24; the re-review uses f429d24, where scope passes. Yours: (1) a later decision in the same session snapshots the current accepted state (keep the event's historical information cutoff for the compile) so revise then retain both save; test the sequence both ways; (2) history failures (non-OK status, malformed body) surface as the route's code and sentence on the page, never as an empty history; tests for authorization, storage and malformed responses. Address every blocking/important row above; dispose of minors explicitly.

## Designated review 2 (GPT Sol, independent, commit `5916777`, 2026-10-14)

> Independent review of `f429d24...435b3bb`, including `git log f429d24..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every brief acceptance item demonstrated | **Yes** for the three explicit bullets: executed `JudgeFlow`, `SeededSession`, `CaseRecords`, and page-harness tests demonstrate decision/history, isolation, and permission references. The intent’s cited-judgment outcome remains unverified; see finding 2. |
> | 2 | Changes within allowed paths | **Yes** — `scripts/plan.py scope GRID-3 f429d24` printed `OK`. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened | **Yes** — diff preserves frozen modules/contracts and acceptance text. Existing image assertions were extended for the permission registry; added live tests have explicit environment guards. |
> | 4 | No unplanned dependency or external effect | **Yes** — no dependency changes or new model/cloud calls; adapter uses existing routes. |
> | 5 | Truthful mode labels | **Yes** for inspected evidence — fixture view is explicitly labelled; historical evidence retains replay times and session actions use current server times. Actual stored-judgment presentation remains unverified. |
> | 6 | Unknowns preserved; no invented facts | **Yes** — executed source-equality tests, register-derived capacity checks, and dispatch `known_at: null` omission checks pass. |
> | 7 | Packet records verification and handoff | **Yes** — `event.md` records interpreters, commands/results, limitations, deferred items, and re-review instructions. |
> | 8 | Consistent with intent and domain invariants | **No** — the new outlook read can silently fail, violating the intent’s requirement to surface route refusals; cited-judgment verification is incomplete. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/grid/event-api.js:106` | Failed `/read` leaves the audit cutoff stale. HTTP failure is silently ignored; transport failure reports failure after the decision already committed. | Injected `503 STORAGE_UNAVAILABLE` after revise: adapter reports `Saved`, then sends `02:01Z` instead of accepted `02:02Z`. Replaying that cutoff through the real repository rejects the next retain with `STALE_HEAD`. | Preserve and display the saved receipt plus refresh failure; retry adoption of that accepted outlook before another decision. Cover HTTP, transport, and malformed-response failures. |
> | important | `tests/fixtures/grid/event/build.py:108` | Tests cannot demonstrate the required cited judgment and stability receipt because the view model contains `judgment: null`. | Executed rendering tests cover the no-judgment branch. Packet acknowledges the live seed and real baked snapshot remain handoffs; no actual baked event file is present here. This is a verification gap, not proof that conversion fails. | Execute and record a page check using the actual converted stored run; verify judgment, citations, four-form receipt, and subsequent decision/history. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_event -v` — **36 tests, OK, 3 skipped**.
> - `/usr/bin/python3 scripts/plan.py scope GRID-3 f429d24` — **OK**.
> - Full offline suite — **624 tests, OK, 12 skipped**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - Live-enabled rerun attempted — **blocked by sandbox socket creation**, `PermissionError: Operation not permitted`; live HTTP tests were not executed.
> 
> **Verdict: rework** — the saved-decision refresh failure remains reproducible, and the intent’s cited-judgment outcome lacks demonstrated page evidence.
**Verdict: rework.** Yours: the refresh after a saved decision. When the follow-up /read (or history) fails after a decision committed, show the saved receipt plus the refresh failure (its code and sentence), keep the session marked stale, and re-adopt the accepted outlook before the next decision is sent; never send a stale cutoff. Tests: HTTP failure, transport failure and malformed body after a successful save, each followed by a second decision that succeeds. The judgment-evidence row is answered by the orchestrator's page evidence in docs/work/grid-desk/event.md. Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `570092a`, 2026-10-14)

> Independent review of `f429d24...570092a9089bfd2f9576288472bc42e39a6254a8`, including `git log f429d24..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every brief acceptance item demonstrated | **Yes.** Executed `JudgeFlow` and `RenderedPage` tests demonstrate account-free decision recording and visible history; `SeededSession` and isolation tests demonstrate another judge’s case remains untouched; `CaseRecords` and derived-record validation demonstrate permission references. |
> | 2 | Only allowed paths changed | **Yes.** `plan.py scope GRID-3 f429d24` printed `OK: all changed files inside GRID-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance preserved; no tests weakened | **Yes.** Diff leaves frozen contracts and acceptance text unchanged. Image assertions were extended for the permission registry; new HTTP tests have explicit environment guards. |
> | 4 | No unplanned dependency or external effect | **Yes.** Runtime changes use local source rows, existing repository ports and existing API routes. No dependency, model-call or cloud-execution code added. |
> | 5 | Mode labels truthful | **Yes**, for inspected code and executed fixtures. Historical evidence retains replay clocks; session actions use server time; page loading reads stored data without inference. Actual converted-judgment presentation is supported by the packet’s recorded orchestrator check, not independently reproduced here. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Source-equality and register-derived-capacity tests passed. Dispatch availability remains unknown and is omitted as `UNKNOWN_AVAILABILITY`; later advisories are excluded at the event cutoff. |
> | 7 | Packet records verification and handoff | **Yes.** `event.md` records interpreters, exact commands/results, limitations, rework evidence and independent re-review as the next action. |
> | 8 | Consistent with intent and domain invariants | **Yes.** Accepted-state audit time advances independently of historical information time. Executed failure tests preserve the saved receipt, display refresh/history errors and retry the accepted-outlook read before another decision. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_event -v` — **38 tests, OK, 3 skipped**.
> - `/usr/bin/python3 scripts/plan.py scope GRID-3 f429d24` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **626 tests, OK, 12 skipped**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - HTTP-enabled rerun attempted — **failed during setup because sandbox socket creation is denied**, `PermissionError: Operation not permitted`. HTTP behavior was not independently verified.
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | docs/work/grid-desk/event.md:609 | Supplemental judgment evidence references an unavailable release record, limiting auditability. | `docs/work/grid-desk/release-poc-2026-10-14.md` does not exist in this checkout; the packet itself contains the orchestrator’s page-check report. | Provide a repository-resident evidence record or identify the exact commit containing the referenced artifact. |
> 
> **Verdict: accept** — all three brief acceptance items are demonstrated by executed checks, the prior adapter defects are covered and resolved, and no blocking or important finding remains.
**Verdict: accept.** independent accept at 570092a
