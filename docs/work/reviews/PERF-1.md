
## Designated review 1 (GPT Sol, independent, commit `dbdc4c3`, 2026-10-14)

> Independent review of `dbdc4c3`, using the requested diff and five-commit log against `feat/h1-api-persistence`. No files edited; working tree remains clean.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Stamp derivation, changed-content detection, unknown-stamp refusals, stamped fetches and current-route enumeration passed targeted checks. However, new routes do not universally default to `no-store` (finding below). The packet records the orchestrator image/browser check; I could not repeat browser verification here. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PERF-1 allowed paths`. |
> | 3 | No frozen contract, acceptance or test weakening | **No, literally:** `tasks.json` changes acceptance to exempt `/desk`. This matches the ruling explicitly supplied in the review brief, so it is not an unresolved finding. No frozen contract changes or weakened/skipped tests found; old header assertions were replaced for the authorized policy. |
> | 4 | No unapproved dependencies or effects | **Yes.** Diff adds no runtime dependency, service, credential or external call. Container/browser execution is attributed to the orchestrator in the packet. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures, replay data and demo-image evidence remain distinguished; no live-inference claim added. |
> | 6 | Unknowns remain unknown | **Yes.** No case facts, receipts or data files added; unavailable checks are identified explicitly. |
> | 7 | Complete execution packet | **Yes.** `perf-1.md` records interpreters, commands, results, limitations, unfinished work and next action, including the later image/browser check. |
> | 8 | Consistent with product/domain invariants | **Yes for existing behavior inspected.** Evidence, identity, cutoff, authorization and judgment contracts are unchanged; no company data added to Git. The future-route caching gap requires correction. |
> 
> Finding:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/api/__init__.py:186` | Broad path-prefix classification grants caching to newly registered routes without explicit classification, violating the required default of `no-store`. | Registered `/event/x/private` in a temporary application: classifier returned `no-cache`. `/grid/0123456789abcdef/private` returned `public, max-age=31536000, immutable`. The new-route test exercises only `/v1/…`. | Classify using explicitly recognized route identities and validated static-file responses; default other endpoints to `no-store`. Add regression checks for new routes beneath both prefixes. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests`: **785 tests; FAILED (errors=1, skipped=24)**. Browser setup parsed an empty report; direct diagnosis showed sandbox `listen EPERM` on `127.0.0.1`.
> - `/usr/bin/python3 scripts/plan.py scope PERF-1 feat/h1-api-persistence`: **OK**.
> - `scripts/plan.py check`: **OK**; `scripts/repo.py check`: **PASS**.
> - Installed FastAPI interpreter, five non-wire cache test classes: **25 tests passed**.
> - Additional wire/combined runs stalled and were interrupted; they are **not passing verification evidence**.
> 
> **Verdict: rework** — the classifier fails the explicit requirement that a new route defaults to `no-store`.
**Verdict: rework.** classify by explicit route identity, not prefix: only the registered grid-page, event-page and desk HTML routes get no-cache, and only the stamped static-file/data routes answering an existing file get immutable; any other route, including new ones under /event/ or /grid/, is no-store; regression tests registering /event/x/private and /grid/<stamp>/private on a temporary app Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `35ae518`, 2026-10-14)

> Independent review of `2afb9f27946e` against `feat/h1-api-persistence`; inspected the requested diff and eight-commit log. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Cache tests pass, but the post-rework demo-image browser check remains explicitly unfinished (`perf-1.md:427–429`). |
> | 2 | Changes within allowed paths | **Yes.** Scope command printed `OK: all changed files inside PERF-1 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **No, literally.** `tasks.json:2122` changes acceptance to exempt `/desk`; this matches the explicit ruling supplied in the current brief. No frozen-contract change or weakened/skipped existing test identified. |
> | 4 | No unapproved dependency or external effect | **Yes.** Implementation adds no dependency, service or external call; recorded image checks are local orchestrator verification. |
> | 5 | Truthful mode labels | **Yes.** Tests use labelled synthetic fixtures; packet distinguishes fixture/browser checks from demo-image and deployed measurements. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Changes concern headers and URLs; no new data files, case facts or receipts introduced. Unknown stamps return 404. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreters, commands, results, unfinished image checks and the next review action. |
> | 8 | Consistent with product/domain invariants | **Yes.** Private answers remain `no-store`; evidence, permissions, cutoffs and judgment contracts are unchanged. |
> 
> Commands executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests`: **FAILED**, 789 tests, 1 error, 25 skips. Browser setup failed parsing empty stdout; direct diagnosis showed sandbox denial: `listen EPERM … 127.0.0.1`.
> - `/usr/bin/python3 scripts/plan.py scope PERF-1 feat/h1-api-persistence`: **OK**.
> - `scripts/plan.py check`: **OK**; `scripts/repo.py check`: **PASS**.
> - `/usr/bin/python3 -m unittest tests.test_cache_headers`: **OK**, 33 tests, 6 wire tests skipped.
> - Additional real-library test runs stalled and were interrupted; no passing result claimed.
> 
> Finding:
> 
> **important | docs/work/performance/perf-1.md:427 | Required demo-image behavior lacks evidence for the reviewed rework | Packet explicitly says the browser check covered the pre-rework image and should be repeated; this review’s browser execution was sandbox-blocked | Run the walkthrough and both pages in a demo-mode image built from the reviewed revision, record results, and rerun verification in an environment permitting loopback.**
> 
> **Verdict: rework** — the earlier classification defect appears addressed, but required post-rework demo-image acceptance evidence is still missing.
**Verdict: accept.** review 2: classification defect addressed; the one open item (post-rework demo-image evidence, orchestrator-owned) recorded at 35ae518: walkthrough 43/43, headers, grid and event pages in Chrome
