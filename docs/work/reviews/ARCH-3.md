
## Designated review (GPT Sol, independent, commit `a76f6d4`, 2026-10-16 18:53, overnight round 1)

> Independent review of `feat/price-outlook...a76f6d4`, including all four commits from `git log feat/price-outlook..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Dependency and preservation tests pass; all six stored-first-outlook tests pass, including PRICE-2 input-digest verification. However, demonstration marks can prevent real stale marking. The recorded 0/5 is explicitly provisional: no monthly pair exists yet. |
> | 2 | Changes inside allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside ARCH-3 allowed paths`. |
> | 3 | Contracts and acceptance unchanged; tests preserved | **Yes.** Diff leaves frozen contracts and acceptance text unchanged. Register assertions accommodate five added rows while retaining source-family coverage; no existing test was skipped or deleted. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Changed implementation uses standard library and existing repository modules; no added service, network, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** First outlook is labelled real; demonstration marks carry `synthetic: true` and are excluded from the real stale set. |
> | 6 | Unknowns preserved | **Yes.** Unknown dependency IDs remain unresolved; validity intervals and checked revisions remain null. Missing monthly comparison is disclosed. |
> | 7 | Complete verification and handoff packet | **Yes.** `first-outlook.md` records interpreter, commands, results, limitations, unfinished work and next action. |
> | 8 | Domain invariants preserved | **No.** A synthetic demonstration can prevent an actual change from marking its dependent outlook stale, as reproduced below. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1752 tests, OK (skipped=62)**. Browser guards are accepted under this review’s instructions.
> - `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 93 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest tests.test_outlook_dependency.FirstOutlook -v` — **6 tests, OK**, none skipped.
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/outlook/dependency.py:151` | Demonstration and real marks share a uniqueness key, allowing a demonstration to block a real change. | Scratch-archive probe: append synthetic mark, then real mark for identical assumption/revision/outlook → `STALE_DUPLICATE`; `stale_outlooks()` remains `()`. | Separate demonstration and real mark identities while preserving immutable history; add a regression proving both can coexist and the real mark makes the outlook stale. |
> | important | `src/outlook/dependency.py:494` | Direction calculation accepts an outlook compared with itself and produces an unsupported monthly result. | Executed `direction_share(o, o)` returns `share: 0.0`; the guard permits equal issue instants. | Require distinct, chronologically ordered monthly outlooks; add rejection tests for self-comparison and equal issue instants. |
> | minor | `docs/work/outlook-archive/first-outlook.md:245` | Acceptance table treats a provisional single-vintage count as the required monthly direction measurement. | Section 6 acknowledges that the second monthly outlook does not exist. | Distinguish the demonstrated fixture calculation from the pending real monthly measurement; leave the latter unfulfilled. |
> 
> **Verdict: rework.** The suite passes, but the reproduced stale-mark collision and invalid direction comparison leave important correctness gaps.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `6b0be8b`, 2026-10-16 19:03, overnight round 2)

> Independent review of `feat/price-outlook...6b0be8b`, including all seven branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Stale marking, preservation and first-outlook input digests pass executed tests. The monthly direction measurement remains explicitly unfulfilled in `first-outlook.md:256`. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside ARCH-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **Yes.** Neither frozen contracts nor acceptance text changed. Existing assertion changes accommodate added register rows and remove dependence on hash ordering; coverage remains. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Implementation uses standard library and existing repository modules; no new service, network, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Real outlook and synthetic demonstration marks are distinguished; executed regressions confirm demonstrations cannot block real marks. |
> | 6 | Unknowns preserved | **Yes.** Unknown IDs remain unresolved, register validity/check fields remain null, and the missing monthly comparison is disclosed. |
> | 7 | Complete verification and handoff packet | **Yes.** Packet §8–12 records interpreter, commands, results, unfinished work and next action. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** Issued records remain unchanged, evidence links persist, and no forecast skill or completed monthly measurement is claimed. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1756 tests, OK (skipped=62)**; browser skips accepted under this review’s instructions.
> - `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 93 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - Dependency module — **60 tests, OK**.
> - Stored `FirstOutlook` checks — **6 tests, OK; none skipped**.
> 
> The previous stale-mark collision and invalid self-comparison findings are resolved by implementation changes and passing regression tests.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/outlook-archive/first-outlook.md:256` | The required direction-check number remains unavailable; a single-vintage count cannot demonstrate change between monthly outlooks. | §6 explicitly says 0/5 is not a monthly measurement and only one monthly outlook exists; the governing direction check is defined in `docs/work/price-outlook/intent.md:72`. | Guardian must resolve the timing mismatch through intent clarification, or leave acceptance pending until a genuine second monthly outlook supports the measurement. Do not substitute a fixture or provisional count. |
> 
> **Verdict: escalate.** The implementation checks pass, but the required monthly measurement depends on a future outlook, leaving an intent/acceptance timing conflict that this change cannot honestly satisfy.

Verdict recorded by the overnight runner: **escalate**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `c659ea0`, 2026-10-16 21:07, overnight round 1)

> Independent review of `feat/price-outlook...c659ea0423b2f621fe29eadde8c1c10f0082f830`, including all 10 commits from `git log feat/price-outlook..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed dependency tests demonstrate accepted-change stale marking and preservation of issued bytes. All six `FirstOutlook` checks ran without skips, including input-file digest verification. Packet §6 records the open **0/5**, assigns monthly measurement to **IMPACT-1**, and names **2026-11 → 2026-12**, satisfying the restated acceptance. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside ARCH-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests preserved | **Yes.** Diff changes no frozen contract or acceptance text. Register assertions accommodate five added rows while preserving counted-family coverage; no existing test was deleted or skipped. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Implementation uses standard library and existing repository modules; no added service, credential, network, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Real outlook and synthetic demonstration marks remain distinct. Passing regressions demonstrate that demonstrations neither make outlooks genuinely stale nor block subsequent real marks. |
> | 6 | Unknowns preserved | **Yes.** Unknown assumption IDs remain unresolved; register validity and checked-revision fields remain null. The missing monthly measurement is explicitly disclosed. |
> | 7 | Complete verification and handoff packet | **Yes.** `first-outlook.md` §8–13 records `/usr/bin/python3`, commands, results, limitations, unfinished work and exact next actions. |
> | 8 | Product direction and domain invariants preserved | **Yes.** Issued outlooks remain immutable, evidence references persist, and neither forecast skill nor completed monthly impact measurement is claimed. The restated direction is recorded consistently. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1766 tests in 36.702s; OK (skipped=62)**. Browser-guarded skips accepted as instructed.
> - `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 94 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest tests.test_outlook_dependency -v` — **60 tests; OK**, including all six stored-first-outlook checks.
> 
> Findings: **None.** Previous stale-mark collision and self-comparison defects have passing regression coverage; the prior timing escalation is addressed by the authorized restated acceptance.
> 
> **Verdict: accept.** All current acceptance items are demonstrated, with no unresolved blocking or important findings.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
