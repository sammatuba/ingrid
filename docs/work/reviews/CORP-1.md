
## Designated review (GPT Sol, independent, commit `a65ef37`, 2026-10-16 00:57, overnight round 1)

> Independent review of `a65ef3794662` against `feat/corpus-overnight`, including the six commits and branch diff. No files edited.
> 
> Verification actually run:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_corpus_acquire` | PASS: 24 tests |
> | `/usr/bin/python3 scripts/plan.py scope CORP-1 feat/corpus-overnight` | OK |
> | `/usr/bin/python3 scripts/repo.py check` | PASS |
> | `/usr/bin/python3 scripts/plan.py check` | OK |
> | `/usr/bin/python3 -m unittest discover -s tests` | FAIL: 925 tests, 1 failure, 202 errors, 29 skipped |
> 
> The suite encountered read-only sandbox errors involving temporary directories. Separately, `test_progress_record_matches_task_states` demonstrated a state mismatch introduced by this diff. A passing full suite is therefore not demonstrated.
> 
> Eight checklist answers:
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **No** | Focused tests demonstrate acquisition identity and unknown-publication exclusion, but the full suite fails and the fetch path introduces unsupported dates. |
> | 2 | **Yes** | Scope command against the requested base printed OK. |
> | 3 | **Yes** | Diff changes no frozen-contract files, acceptance text, or existing tests. |
> | 4 | **Yes** | Observed imports and recorded urllib request fit the packet; no model or cloud execution demonstrated. |
> | 5 | **No** | Fetch metadata defaults to `synthetic=True` for real fetched documents. |
> | 6 | **No** | HTTP modification time becomes publication and historical availability without supporting evidence. |
> | 7 | **Yes** | `acquisition.md` records interpreter, commands, results, unfinished work and next actions; its green-suite claim was not reproduced here. |
> | 8 | **No** | Provenance and availability handling contradict the real/synthetic distinction and time contract. |
> 
> Findings, all unresolved:
> 
> - **important | scripts/corpus/fetch.py:214 | Real documents are labelled synthetic |** The metadata constructor omits `synthetic` and `permission_ref`; an executed probe confirmed defaults `(True, None)`, which flow into acquisition and projected records. **Correction:** explicitly carry real provenance and its permission reference; refuse missing required permission metadata.
> 
> - **important | scripts/corpus/fetch.py:142 | Modification time is asserted as publication |** With no supplied publication and only `Last-Modified`, an executed probe returned a stated publication timestamp. Server modification metadata does not establish when the issuer published the document. **Correction:** retain the header separately and keep publication unknown unless supported by explicit publication evidence.
> 
> - **important | scripts/corpus/fetch.py:160 | Historical availability is backdated without delivery evidence |** An executed probe fetching in October 2026 produced `feed_logged_at` availability in October 2025 solely from `Last-Modified`. This can admit evidence into earlier cutoff contexts. **Correction:** require actual feed-delivery evidence; otherwise preserve unknown availability or use explicitly authorized capture evidence.
> 
> - **important | scripts/corpus/upload.sh:35 | Documented dry run invokes upload commands |** A mocked invocation with `--dry-run` called both `gcloud storage rsync` commands without a dry-run flag. The script never reads its arguments. **Correction:** implement and propagate dry-run handling, reject unknown arguments, and verify with mocked commands before cloud use.
> 
> - **important | docs/work/PROGRESS.md:110 | Duplicate rows overwrite current task states |** The diff adds `CORP-0 pending` and another CORP-1 row instead of updating the existing row. The executed suite fails because CORP-0 resolves to `pending` while `tasks.json` says `in_progress`. **Correction:** remove the added CORP-0 row, update the existing CORP-1 row, and rerun the state-consistency test and full suite.
> 
> **Verdict: rework.** Unresolved important defects affect provenance, cutoff correctness, upload behavior and task-state consistency, and full-suite acceptance remains unproven.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `55537aa`, 2026-10-16 01:10, overnight round 2)

> Independent review of `55537aa618ab` against `feat/corpus-overnight`, including the branch diff and 11 commits. No files edited.
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **No** | Identity and unknown-publication exclusion tests passed, but a passing full offline suite was not reproduced. |
> | 2 | **Yes** | `plan.py scope CORP-1 feat/corpus-overnight` printed OK; working tree clean. |
> | 3 | **Yes** | No frozen-contract files, acceptance text, or existing tests changed. |
> | 4 | **Yes** | Optional pypdf and urllib acquisition fit the packet; no model call or cloud write was performed during review. |
> | 5 | **Yes** | Fetch rows must explicitly declare provenance; real rows require a permission reference. Synthetic fixtures are labelled. |
> | 6 | **Yes** | Missing publication stays unknown; `Last-Modified` is retained separately and does not establish publication or availability. |
> | 7 | **Yes** | `acquisition.md` records interpreter, commands, results, unfinished register integration, and next actions. Its passing-suite claim was not independently reproduced. |
> | 8 | **No** | Locator validation permits inconsistent citation offsets, violating the exact-passage invariant. |
> 
> Verification actually run:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_corpus_acquire` | 36 tests; **9 errors**, caused by unavailable writable temporary directories |
> | `/usr/bin/python3 scripts/plan.py scope CORP-1 feat/corpus-overnight` | **OK** |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 937 tests; **211 errors**, 29 skipped; sandbox prevents passing verification |
> | Acquisition, text-layer, and compiled-context classes with `.local/pylib` on `sys.path` | **21 tests passed** |
> 
> Findings:
> 
> **important | src/adapters/corpus/text.py:194; src/adapters/corpus/acquire.py:647 | Inconsistent locator offsets produce an invalid Passage record |** An executed probe retained page-relative offsets `0..12` and quote `'Synthetic is'`, changed global offsets to `20..32`, and `passage_record` accepted it despite those offsets selecting `'ting page (f'`. Repository registration subsequently rejects such a passage, so the adapter emits unusable citation records. **Correction:** validate global offsets against page-relative offsets, bind the layer to the supplied source, and add rejection tests. **Disposition:** unresolved.
> 
> **Verdict: rework.** The citation-validation defect remains important, and passing full-suite acceptance has not been independently demonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `145fd2c`, 2026-10-16 09:30, overnight round 1)

> Independent review of `feat/corpus-overnight...145fd2cda76f2601e85b4435f81a49991dadcc8d`, including all three commits in `git log feat/corpus-overnight..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **Yes.** Executed acquisition tests demonstrate same-byte deduplication, changed-byte versioning, and unknown-publication exclusion through projection refusal and real compiled-context checks. Full suite and repo check pass. |
> | 2 | Changes stay within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORP-1 feat/corpus-overnight` printed `OK: all changed files inside CORP-1 allowed paths`. |
> | 3 | Frozen contracts and acceptance preserved; no tests weakened | **Yes.** Six-file diff changes adapter validation, documentation and tests; three tests added, none removed or weakened. Frozen files and acceptance text unchanged. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Added code uses existing stdlib hashing and validation; no dependency, network, model or cloud operation added. |
> | 5 | Mode labels truthful | **Yes.** Added fixtures explicitly identify synthetic text. Packet distinguishes local probes and offline tests from deferred upload operations. |
> | 6 | Unknowns remain unknown | **Yes.** Executed tests preserve publication/availability unknowns and exclude those versions; added validation refuses inconsistent locators and mismatched source layers. |
> | 7 | Packet contains required handoff evidence | **Yes.** `acquisition.md` records Python 3.14, exact commands/results, before/after reproduction, unfinished lane items and re-review as the next action. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** Changes strengthen exact passage attribution and immutable-source binding without altering time semantics, assumptions or approval boundaries. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_acquire` — **39 tests, OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **1141 tests, OK (skipped=44)**; browser coverage was not executed here.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 71 tasks, 8 gates**
> - Requested scope command — **OK**
> 
> Findings: none.
> 
> **Verdict: accept** — All required acceptance checks passed, and the reviewed diff fixes citation consistency and source-layer binding without an unresolved blocking or important finding.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `950241e`, 2026-10-16)

> Independent review of `feat/corpus-overnight...145fd2cda76f2601e85b4435f81a49991dadcc8d`, including all three commits in `git log feat/corpus-overnight..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **Yes.** Executed acquisition tests demonstrate same-byte deduplication, changed-byte versioning, and unknown-publication exclusion through projection refusal and real compiled-context checks. Full suite and repo check pass. |
> | 2 | Changes stay within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORP-1 feat/corpus-overnight` printed `OK: all changed files inside CORP-1 allowed paths`. |
> | 3 | Frozen contracts and acceptance preserved; no tests weakened | **Yes.** Six-file diff changes adapter validation, documentation and tests; three tests added, none removed or weakened. Frozen files and acceptance text unchanged. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Added code uses existing stdlib hashing and validation; no dependency, network, model or cloud operation added. |
> | 5 | Mode labels truthful | **Yes.** Added fixtures explicitly identify synthetic text. Packet distinguishes local probes and offline tests from deferred upload operations. |
> | 6 | Unknowns remain unknown | **Yes.** Executed tests preserve publication/availability unknowns and exclude those versions; added validation refuses inconsistent locators and mismatched source layers. |
> | 7 | Packet contains required handoff evidence | **Yes.** `acquisition.md` records Python 3.14, exact commands/results, before/after reproduction, unfinished lane items and re-review as the next action. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** Changes strengthen exact passage attribution and immutable-source binding without altering time semantics, assumptions or approval boundaries. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_acquire` — **39 tests, OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **1141 tests, OK (skipped=44)**; browser coverage was not executed here.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 71 tasks, 8 gates**
> - Requested scope command — **OK**
> 
> Findings: none.
> 
> **Verdict: accept** — All required acceptance checks passed, and the reviewed diff fixes citation consistency and source-layer binding without an unresolved blocking or important finding.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
