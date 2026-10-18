
## Designated review (GPT Sol, independent, commit `5ff844f`, 2026-10-16 02:06, overnight round 1)

> Reviewed independently at `5ff844f`, using `git diff feat/corpus-overnight...HEAD` and all four commits from `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> Verification run with `/usr/bin/python3 -B`:
> 
> - Targeted suite: **50 tests, 9 errors** from unavailable writable temporary directories; remaining 41 passed.
> - Full offline suite: **1080 tests, 1 failure, 233 errors, 29 skipped**. The progress-state failure is reproducible independently of sandbox restrictions.
> - Scope against `feat/corpus-overnight`: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Cutoff and reserve-market tests passed, as did the SQL checker tests, but the full offline suite is not green. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORP-4 allowed paths`. |
> | 3 | Frozen contracts/acceptance unchanged; tests not weakened | **Yes.** Diff adds store code and tests; frozen contracts and acceptance text are unchanged. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Implementation uses stdlib; cloud commands are documented, with no cloud/model execution introduced. |
> | 5 | Truthful mode labels | **Yes.** Fixtures and hash embeddings are explicitly synthetic; BigQuery execution and real embeddings are explicitly unrun. |
> | 6 | Unknowns preserved; no invented facts | **No.** Direct store writes can supply passage availability without any source record; see finding 2. |
> | 7 | Complete verification and handoff record | **Yes.** `store.md:130` records interpreter, commands and reported results; unfinished work and next actions are recorded. Those historical results do not establish a passing current suite. |
> | 8 | Consistent with product/domain invariants | **No.** Unvalidated passage provenance permits unsupported historical retrieval. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/corpus/bq/load.py:34` | Incorrect repository root prevents standalone loader execution. | `/usr/bin/python3 -B scripts/corpus/bq/load.py --help` fails with `ModuleNotFoundError: No module named 'src'`; `parents[2]` resolves to `scripts/`. | Use the actual repository root and test the documented CLI in a subprocess. |
> | important | `src/adapters/corpus/store/local.py:268` | Passage insertion validates embeddings but never resolves its source or verifies availability/issuer against it. Caller-supplied availability can admit unsupported historical context. | On both backends, inserting a fixture passage with availability changed to `2020-01-01` into an empty store yields **sources=0, retrieved=1** at `2020-01-02`. | Require a compilable source version and derive or validate passage availability and issuer against it; test missing, excluded and mismatched sources. |
> | important | `docs/work/PROGRESS.md:113` | Duplicate task rows introduce a contradictory CORP-3 state and break the required suite. | Lines 111/113 list CORP-3 as both `in_progress` and `pending`; `test_progress_record_matches_task_states` fails. CORP-4 is also duplicated. | Keep one row per task, matching `tasks.json`, and rerun the suite. |
> 
> **Verdict: rework** — the loader is unusable through its documented command, passage provenance is unenforced, and the required full-suite acceptance has not been demonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `74bf6c8`, 2026-10-16 02:15, overnight round 2)

> Independent review of `74bf6c8` against `feat/corpus-overnight`, covering nine commits and the branch diff. No files edited.
> 
> Verification used `/usr/bin/python3` 3.14 with bytecode writes disabled:
> 
> | Check | Observed result |
> |---|---|
> | `-m unittest tests.test_corpus_store` | 55 tests; 10 errors from unavailable writable temporary directories |
> | `-m unittest discover -s tests` | 1085 tests; 234 errors, 29 skipped; no passing full-suite result |
> | Cutoff, reserve-market and SQL test classes | All 17 tests passed |
> | `scripts/plan.py scope CORP-4 feat/corpus-overnight` | **OK** |
> | `scripts/plan.py check` | **OK** |
> | `scripts/repo.py check` | **PASS** |
> | Standalone loader `--help` | Passed |
> 
> The sandbox errors prevent verification of affected tests; they are not established implementation defects.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** The fixture cutoff, two-cutoff action and SQL checker tests passed, but the full suite did not pass here. The mutation reproduction below also bypasses cutoff protection. |
> | 2 | All changes within allowed paths | **Yes.** Requested scope command printed OK. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Branch diff preserves frozen files and acceptance text; tests are additive. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Store and loader use stdlib; cloud operations remain documented commands. |
> | 5 | Truthful mode labels | **No.** `rule_version_row` unconditionally labels incoming rule versions synthetic. |
> | 6 | Unknowns preserved; no invented facts or numbers | **No.** Claim availability can contradict its cited source without rejection. |
> | 7 | Complete verification and handoff record | **Yes.** `store.md` records interpreter, commands, reported results, limitations and next actions. Historical results do not prove this reviewed run passed. |
> | 8 | Consistent with product and domain invariants | **No.** Unsupported historical claim retrieval and mutable stored records violate provenance and append-only requirements. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/corpus/store/local.py:381` | Claim validation resolves source existence but does not constrain availability against the cited source/passage or bind both citation identities together. | Moving fixture claim `claim:synthetic-news-copy@1` availability from `2026-09-27` to `2020-01-01` was accepted by both backends; `what_changed` returned it in the 2019–2020 window. | Validate citation identity and provenance; reject availability that precedes the cited evidence. Add regressions on both backends. |
> | important | `src/adapters/corpus/store/local.py:401` | Read methods expose stored mutable dictionaries, permitting changes outside validation and causing backend disagreement. | Changing `rows('passages')[-1]['availability_until']` to 2000 made MemoryStore retrieve that passage at a 2000 cutoff; SQLite did not. | Return defensive copies from reads and writes, including nested values; test that mutations cannot alter stored records. |
> | important | `src/adapters/corpus/store/records.py:648` | The lineage converter fabricates synthetic provenance for every incoming rule version. | `rule_version_row` has no provenance input and always emits `synthetic=True, permission_ref=None`, including for a version derived from a real document. | Require supplied provenance or derive it from the resolved source version; test real and synthetic conversions. |
> 
> **Verdict: rework** — unresolved important defects permit unsupported historical retrieval, bypass append-only validation, and mislabel real rule provenance.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `15813fd`, 2026-10-16 09:58, overnight round 1)

> Independent review of `15813fddec03` against `feat/corpus-overnight`; reviewed commits `79d34fb` and `15813fd`. Working tree clean; no files edited.
> 
> Checks executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_store` — **68 tests, OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **1157 tests, OK (skipped=44)**; browser skips accepted as instructed.
> - `/usr/bin/python3 scripts/plan.py scope CORP-4 feat/corpus-overnight` — **OK**
> - `plan.py check` — **OK: 71 tasks, 8 gates**
> - `repo.py check` — **PASS**
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** Executed tests cover later amendment/announcement exclusion, clauses and action claims across cutoffs, SQL checking, and the full offline suite. |
> | 2 | Changes within allowed paths | **Yes.** Scope command printed OK; seven changed files. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** Diff adds regression tests and changes store implementation/documentation; no frozen-contract or acceptance changes. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** Changes use stdlib `copy`; no added service, credential, network, model, or cloud call. |
> | 5 | Truthful mode labels | **Yes.** Fixture remains explicitly synthetic; rule conversion now requires stated or supplied provenance. Cloud execution remains explicitly unverified. |
> | 6 | Unknowns preserved; no invented facts | **No.** Mixed precision permits a claim to appear while its evidence remains unavailable at that cutoff; reproduction below. |
> | 7 | Complete packet evidence and handoff | **Yes.** `store.md` records Python 3.14, exact commands/results, outstanding cloud/embedding work, and next action. |
> | 8 | Consistent with domain invariants | **No.** The remaining claim/evidence timing defect violates the known-at-cutoff boundary. |
> 
> Findings:
> 
> **important | [src/adapters/corpus/store/local.py:454](../../../src/adapters/corpus/store/local.py) | Comparing only availability interval starts permits a finer-precision claim before its evidence is admissible | Executed probe on both backends: set the news source/passage availability to `2026-09` (month), and its claim to `2026-09-01` (day). At cutoff `2026-09-02`, passage retrieval excludes the evidence, but `what_changed` returns `claim:synthetic-news-copy@1`. Both interval starts match, so validation accepts it | Enforce that the claim cannot become cutoff-admissible before its evidence, including interval-end comparison; add mixed-precision regression tests for both backends.**
> 
> **Verdict: rework** — The required checks pass, but an unresolved important timing defect allows a claim to surface before its cited evidence.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `ef46bfb`, 2026-10-16 10:07, overnight round 2)

> Independent review of `ef46bfb3b578d67423cffb2d28cc62146af1da94`, covering the four commits and diff against `feat/corpus-overnight`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed store tests cover later amendment/announcement exclusion, two-cutoff clause changes, action-claim availability, and SQL checking. Full offline suite passes. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-4 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; no weakened/skipped tests | **Yes.** Diff changes store implementation, fixtures, documentation and adds regression tests; frozen files and acceptance text are unchanged. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** Changes use stdlib; loader validates locally. Cloud and embedding operations remain documented orchestrator steps. |
> | 5 | Truthful mode labels | **Yes.** Fixtures and hash embeddings are explicitly synthetic; real provenance must be supplied or resolved rather than defaulted. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Unknown availability remains excluded. Regression tests demonstrate refusal of claims preceding their evidence and preservation of provenance. |
> | 7 | Complete packet and handoff | **Yes.** `docs/work/corpus/store.md` records interpreter, commands, results, unresolved cloud/embedding work and the next review action; PROGRESS records both reworks. |
> | 8 | Consistent with product and domain invariants | **Yes.** Citation identity is checked, availability compares both interval endpoints, defensive copies protect stored evidence, and retrieval confers no acceptance. |
> 
> Executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_corpus_store` | 71 tests, **OK** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 1160 tests, **OK (skipped=44)** |
> | `/usr/bin/python3 scripts/plan.py scope CORP-4 feat/corpus-overnight` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK** |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | `/usr/bin/python3 tests/fixtures/corpus/store/build.py --check` | Fixture current |
> 
> The full suite includes the browser-class skips permitted for this review environment. BigQuery execution was not performed or claimed.
> 
> Findings: none requiring correction.
> 
> **Verdict: accept** — all required acceptance checks passed, and the reviewed changes resolve the prior claim-cutoff, mutable-row and provenance findings.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `f61e715`, 2026-10-16)

> Independent review of `ef46bfb3b578d67423cffb2d28cc62146af1da94`, covering the four commits and diff against `feat/corpus-overnight`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed store tests cover later amendment/announcement exclusion, two-cutoff clause changes, action-claim availability, and SQL checking. Full offline suite passes. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-4 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; no weakened/skipped tests | **Yes.** Diff changes store implementation, fixtures, documentation and adds regression tests; frozen files and acceptance text are unchanged. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** Changes use stdlib; loader validates locally. Cloud and embedding operations remain documented orchestrator steps. |
> | 5 | Truthful mode labels | **Yes.** Fixtures and hash embeddings are explicitly synthetic; real provenance must be supplied or resolved rather than defaulted. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Unknown availability remains excluded. Regression tests demonstrate refusal of claims preceding their evidence and preservation of provenance. |
> | 7 | Complete packet and handoff | **Yes.** `docs/work/corpus/store.md` records interpreter, commands, results, unresolved cloud/embedding work and the next review action; PROGRESS records both reworks. |
> | 8 | Consistent with product and domain invariants | **Yes.** Citation identity is checked, availability compares both interval endpoints, defensive copies protect stored evidence, and retrieval confers no acceptance. |
> 
> Executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_corpus_store` | 71 tests, **OK** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 1160 tests, **OK (skipped=44)** |
> | `/usr/bin/python3 scripts/plan.py scope CORP-4 feat/corpus-overnight` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK** |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | `/usr/bin/python3 tests/fixtures/corpus/store/build.py --check` | Fixture current |
> 
> The full suite includes the browser-class skips permitted for this review environment. BigQuery execution was not performed or claimed.
> 
> Findings: none requiring correction.
> 
> **Verdict: accept** — all required acceptance checks passed, and the reviewed changes resolve the prior claim-cutoff, mutable-row and provenance findings.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
