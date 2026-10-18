
## Designated review 1 (GPT Sol, independent, commit `cead6dc`, 2026-10-14)

> Reviewed independently at `cead6dc35a8090dc3766d088776da78e612e2e83`, using the requested base/head diff and both branch commits. Working tree was clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **yes** — all four named acceptance tests ran and passed: pinned-ready revision, not-ready message, index/platform equivalence, different-image refusal. |
> | 2 | Changes within allowed paths | **yes** — requested scope command printed `OK: all changed files inside HOST-4 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened | **yes** — seven-file diff touches no frozen contract or acceptance text. Changed tests strengthen release checks; seven FastAPI skips are pre-existing. |
> | 4 | No unprovided dependencies or external effects | **yes** — index inspection implements the packet’s prescribed registry resolution; tests use stubs. No deployment or cloud call performed during review. |
> | 5 | Truthful mode labels | **yes** — test digests are labelled synthetic; packet distinguishes offline checks from outstanding live proof. |
> | 6 | Unknowns preserved; no invented facts | **no** — an index without an amd64 entry is incorrectly treated as a resolved platform manifest; see finding below. |
> | 7 | Complete verification and handoff record | **yes** — packet records interpreter, commands, results, self-review, outstanding live proof and exact next actions. |
> | 8 | Consistent with direction/domain invariants | **no** — unresolved platform identity becomes an asserted platform digest and permits a deployment attempt. |
> 
> Commands executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_hosted_config -v` — **95 tests, OK (skipped=7)**; all HOST-4 tests passed.
> - `/usr/bin/python3 scripts/plan.py scope HOST-4 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 50 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **648 tests, OK (skipped=7)**.
> 
> Findings, both unresolved:
> 
> - **important | scripts/deploy/platform_digest.py:32 | Missing platform resolution falls back to the index digest and proceeds to deployment | An arm64-only index returned exit 0 with empty output; an offline stub release then attempted `run deploy`, rejecting only at the subsequent digest comparison. `deploy.sh:260` substitutes the index digest. | Distinguish a plain manifest from an index lacking a valid amd64 digest; reject the latter before deployment and add a release test asserting no deploy attempt.**
> - **minor | docs/work/PROGRESS.md:304 | Resume instructions reproduce the defective readiness selector | The entry claims exact `=` selection but prints `filter("type:Ready")`; implementation and packet explicitly identify this substring selector as incorrect. | Change the recorded expression to `filter("type=Ready")`.**
> 
> **Verdict: rework** — the required acceptance tests pass, but unresolved platform identity must fail before deployment rather than being substituted with the index digest.
**Verdict: rework.** deploy.sh and platform_digest.py: an index without an amd64 digest fails before run deploy, with a release test; PROGRESS selector text Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `1ddb59e`, 2026-10-14)

> Independent review of `feat/h1-api-persistence...HEAD` at `1ddb59e7c348`, including all five branch commits. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **yes** — executed tests at `tests/test_hosted_config.py:1361,1381,1414,1454` demonstrate pinned-ready success, not-ready message, index/platform equivalence, and different-image refusal. |
> | 2 | Changes within allowed paths | **yes** — requested scope command printed `OK: all changed files inside HOST-4 allowed paths`. |
> | 3 | Frozen contracts/acceptance unchanged; no weakened or skipped tests | **yes** — diff changes no frozen contracts or acceptance text. Tests strengthen release checks; seven FastAPI skips are pre-existing and unrelated to HOST-4 acceptance. |
> | 4 | No external additions beyond packet | **yes** — registry inspection implements the prescribed platform resolution using existing tooling; executed release tests use stubs. No cloud effects performed during review. |
> | 5 | Truthful mode labels | **yes** — fixtures use synthetic digests; packet distinguishes offline verification from outstanding live deployment proof. |
> | 6 | Unknowns preserved; no invented facts | **yes** — unresolved index identity now exits nonzero; the regression test at `tests/test_hosted_config.py:1488` proves no deployment attempt occurs. |
> | 7 | Complete verification and handoff record | **yes** — `docs/work/hosting/deploy-fix.md` records interpreter, commands, results, unfinished live verification, and exact next actions. |
> | 8 | Consistent with direction/domain invariants | **yes** — readiness targets the created revision, digest verification precedes traffic routing, and unresolved platform identity fails before deployment. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_hosted_config -v` — **98 tests, OK (skipped=7)**. All four acceptance tests ran.
> - `/usr/bin/python3 scripts/plan.py scope HOST-4 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 50 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **651 tests, OK (skipped=7)**.
> 
> Findings: **none unresolved**. Both prior findings are corrected: missing amd64 resolution refuses before deployment, and PROGRESS uses the exact `type=Ready` selector.
> 
> **Verdict: accept** — all required offline acceptance checks were demonstrated, and rework closes the prior findings; live deployment remains explicitly unverified.
**Verdict: accept.** independent accept at 1ddb59e
