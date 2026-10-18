
## Designated review (GPT Sol, independent, commit `860f166`, 2026-10-16 23:36, overnight round 1)

> Independent review of `860f166a9863e8029b92d66ea61f313e6bd22e70` against `feat/price-outlook`. Inspected the diff, clean working tree, task brief, review process, implementation, tests and stored comparison.
> 
> Commits reviewed:
> 
> - `526464e` — implement ridge and boosted challengers.
> - `860f166` — record post-commit verification.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Feature cutoff tests and baseline-loss suppression pass, but stable calibration is not demonstrated for every accepted group: two month groups claim with no fold calibration measurements. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope PRICE-3 feat/price-outlook` printed `OK: all changed files inside PRICE-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** No frozen contract or acceptance text changed. The existing baseline test adds the challenger module to its stdlib check. Browser skips are unchanged and permitted by this review’s instructions. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Added implementation uses standard-library code and local files; no added service, credential, network or cloud call. |
> | 5 | Truthful mode labels | **Yes.** Tests identify synthetic inputs; packet and stored comparison label results as **pre-backfill exports (digests in docs/work/price-outlook/export.md)**. |
> | 6 | Unknowns preserved; numbers supported | **Yes.** Historical first availability remains explicitly unknown. Stored comparison matches the packet’s SHA-256 `631bc47a…2309`; stored scorecard matches `41ea6521…a305`. |
> | 7 | Complete, usable verification and handoff record | **No.** Interpreter, results and next action are recorded, but the reproduction command cannot regenerate the documented sixteen-series comparison. |
> | 8 | Consistent with governing direction and invariants | **No.** Claims without demonstrated calibration stability violate the brief’s acceptance requirement. Baseline-winning and administered-pricing groups correctly carry no claim. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/price/challengers.py:932` | Missing calibration evidence passes the gate: empty `fold_coverage` bypasses rejection and sets the required fold count to zero. | Stored pre-backfill comparison accepts N01 and N03 boosted month groups, each with five origins across two folds and `fold_coverage=[]`. A synthetic probe also returned `claim=True`, `fold_coverage_needed=0`, `reasons=[]`. | Refuse claims when fold calibration stability cannot be assessed; require sufficient evidence across the evaluated folds. Add regression coverage and regenerate the comparison and packet. |
> | important | `src/price/challengers.py:242` | The 28-day query overwrites the seven-day count, so the seven-day presence floor is checked against the wrong window. | A probe returning one seven-day observation and 22 observations over 28 days retained the seven-day feature, despite its declared four-observation minimum. | Keep separate counts, test sparse seven-day history with adequate 28-day history, and regenerate affected results. |
> | important | `docs/work/price-outlook/challengers.md:288` | The documented reproduction command silently excludes nodal series. | It omits `--series both`; the challenger parser defaults to `regional`, even when `--nodal` is supplied. The stored artifact contains sixteen series. | Add `--series both` and verify that the exact documented command reproduces the full artifact and digest. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,800 tests, 84.198s, OK (skipped=63)**. Browser skips are permitted here.
> - Scope command above — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 94 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> No files were edited.
> 
> **Verdict: rework** — unresolved important findings permit unsupported calibration claims, violate a declared feature floor, and prevent reproduction of the documented comparison.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `fbff1f7`, 2026-10-17 00:07, overnight round 2)

> Independent review of `fbff1f7334f887972e62d683a7d63cf261a6d8f4` against `feat/price-outlook`, including the five commits from `526464e` through `fbff1f7`. Working tree was clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Feature cutoff and baseline-winning suppression are tested, but calibration uses residuals from forecasts made with future-trained models, as demonstrated below. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PRICE-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff changes neither frozen contracts nor acceptance text. Existing baseline test extends its stdlib check; browser skips are unchanged and permitted. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Added implementation uses standard-library computation and local files; no added network, service or cloud call. |
> | 5 | Truthful mode labels | **Yes.** Tests label synthetic inputs; packet and comparison identify pre-backfill exports and their digests. |
> | 6 | Unknowns preserved; numbers supported | **Yes.** Historical availability remains explicitly unknown. Stored comparison is 458,493 bytes with SHA-256 `31403312…a605a9`, matching the packet, and contains 28 claims. Their validity remains subject to the finding below. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreter, commands, results, reproduction instructions, limitations and re-review as the next action. |
> | 8 | Consistent with direction and domain invariants | **No.** Future-trained forecasts enter the supposedly as-of calibration evidence. |
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/price/challengers.py:725` | Origins preceding the first fold are assigned fold 0’s model. Their forecasts therefore use later training labels, and their residuals enter the calibration fan at lines 750–752. Waiting for settlement does not make these forecasts out of sample. | A read-only probe using existing `WalkForward` fixtures produced 234 served pre-fold forecasts beginning 2023-07-11 from a model trained through 2024-02-27. On the real pre-backfill CLUZ export, a ridge-only probe produced **301** pre-fold forecasts, 2021-07-11 through 2022-07-10, using training through 2022-07-06; the first scored origin, 2022-07-11, already had fan quantiles. | Withhold pre-fold forecasts and residuals, or generate warm-up residuals using models fitted strictly before each forecast’s permitted cutoff. Add a regression covering model training dates for every fan contribution; regenerate the comparison and packet. **Unresolved.** |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,803 tests in 89.784s; OK (skipped=63)**. Permitted browser skips are not failures.
> - `/usr/bin/python3 scripts/plan.py scope PRICE-3 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 94 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> **Verdict: rework** — calibration evidence includes residuals from future-trained forecasts, so the required out-of-sample acceptance has not been demonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `9098d30`, 2026-10-17 01:22, overnight round 1)

> Independent review of `9098d30f2b4bc011b500c20912d9a54e8bebe1a5` against `feat/price-outlook`, covering commits `93b0a0d`, `1ea5699`, and `9098d30`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed suite covers feature cutoffs, training deadlines, out-of-sample fan seeding, calibration gates, and baseline-winning suppression. Stored comparison has 28 claims; all satisfy the recorded gain and calibration requirements. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside PRICE-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff changes no frozen contract or acceptance text and adds four regression tests without weakening existing tests. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Changes use existing standard-library computation and local inputs; no added dependency, network call, service, credential, or cloud effect. |
> | 5 | Truthful mode labels | **Yes.** Synthetic tests and stored historical comparison are distinguished; comparison explicitly labels pre-backfill exports. |
> | 6 | Unknowns preserved; numbers supported | **Yes.** Historical first availability remains unknown. Comparison is 459,787 bytes, SHA-256 `a536d050…2b52`, matching the packet and byte-identical to the recorded second run. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreter, commands, results, reproduction instructions, limitations, unfinished work, and re-review as the next action. |
> | 8 | Consistent with governing direction and invariants | **Yes.** Pre-fold forecasts now contribute neither predictions nor residuals; baseline-winning outcomes refuse claims, and administered-pricing outcomes remain excluded from skill claims. |
> 
> Findings: none. The previous important finding is resolved by the guard in `src/price/challengers.py:750` and the added regression coverage.
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,870 tests in 171.039s; OK (skipped=63)**. Browser skips are permitted by the review instructions.
> - `/usr/bin/python3 scripts/plan.py scope PRICE-3 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 94 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `git diff --check feat/price-outlook...HEAD` — **passed**.
> 
> **Verdict: accept** — the rework removes future-trained forecasts from calibration evidence, demonstrates the required acceptance behavior, and passes verification with no unresolved important findings.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
