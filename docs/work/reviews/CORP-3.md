
## Designated review (GPT Sol, independent, commit `62d8537`, 2026-10-16 01:47, overnight round 1)

> Independent review of five commits against `feat/corpus-overnight`, through `62d8537476262e97cb3da1f2e132b26c5cb07ec2`. Working tree clean; no files edited.
> 
> Checklist:
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1. All acceptance demonstrated | **No** | Citation-refusal, proposed-state and serialized-request tests passed, but the focused command and full suite did not pass in this sandbox. Required thinking high is also absent from the wire request. |
> | 2. Changes within allowed paths | **Yes** | `plan.py scope CORP-3 feat/corpus-overnight` printed `OK: all changed files inside CORP-3 allowed paths`. |
> | 3. Frozen contracts/acceptance preserved; tests not weakened | **Yes** | Diff adds extraction code and tests; existing contracts, acceptance text and tests are unchanged. |
> | 4. No unlisted dependency or external effect | **Yes** | Uses standard library and existing Gemini transport. Live execution is documented; no model or cloud call was performed during review. |
> | 5. Truthful mode labels | **Yes** | Fixture, replay and live paths have explicit labels; fixture documentation identifies the response as synthetic. |
> | 6. Unknowns preserved; no invented facts/receipts/numbers | **No** | Source revision identity is unreliable: changed bytes at one URL can both receive version `1` (finding below). Synthetic receipt numbers are explicitly labelled. |
> | 7. Complete execution/handoff record | **Yes** | `extraction.md` records Python 3.14, commands, reported results, gaps G-1–G-3 and exact next actions. Recorded green results were not independently reproduced. |
> | 8. Consistent with direction/domain invariants | **No** | Version conflation and incomplete permitted-passage matching undermine exact source-version lineage. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | **important** | `src/adapters/corpus/extract/run.py:82` | Vertex requests disable thinking despite the explicit requirement for thinking high. Recording the discrepancy does not satisfy the required behavior. | `THINKING_CARRIED` sends `{"thinkingBudget": 0}`; request tests assert that downgrade. Packet G-1 acknowledges it. | Hand back the transport constraint for the required CORE change; block noncompliant live extraction and verify high thinking on the serialized request afterward. |
> | **important** | `scripts/corpus/extract.py:187` | Acquisition omits existing version history, so changed bytes at the same locator receive the same source ID and version `1`. Maps keyed only by source ID then overwrite provenance/layers (`:259`, `:281`). | In-memory reproduction produced equal `(source_id, source_version)` for different document digests. | Resolve immutable corpus versions using acquisition history; bind provenance and layers to version identity, and refuse conflicting duplicates. Add changed-source and multiple-version coverage. |
> | **important** | `src/adapters/corpus/extract/check.py:98` | Permitted-passage matching compares only source ID and offsets, omitting quote and source version. A different layer can validate text the model was never supplied. | In-memory reproduction changed one character in the response and layer while retaining the original request passage: all five claims were kept, zero refused. `run.py` also strips quote/version from the permission-check input. | Match the complete supplied passage, including exact quote and immutable version; validate layer binding before inference. Add a mismatched-layer regression test. |
> 
> Checks executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_extract`: **41 tests; 32 passed, nine errors** because temporary directories were unavailable in the read-only sandbox.
> - Full offline suite: **1,020 tests; 220 errors, 29 skipped**. Temporary-directory failures prevent a green-suite conclusion.
> - Scope, `plan.py check`, `repo.py check`, and `git diff --check`: **passed**.
> 
> **Verdict: rework** — source-version and citation-boundary defects remain, and the required thinking-high request is not implemented.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `2599093`, 2026-10-16 02:03, overnight round 2)

> Independent review of `feat/corpus-overnight...2599093`, including all eight commits and the clean working tree. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Citation refusal, proposed-only claims, unchanged assumptions, and serialized-request isolation passed. The full offline suite did not pass in this sandbox; live transport compatibility remains blocked. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORP-3 feat/corpus-overnight` printed `OK`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff adds extraction code/tests; frozen files and acceptance text are unchanged. |
> | 4 | No effects beyond the packet | **Yes.** Existing transport reused unchanged; no new dependency or executed model/cloud call demonstrated. |
> | 5 | Truthful mode labels | **Yes.** Replay receipts identify synthetic fixtures; live execution is explicitly documented as blocked and unexecuted. |
> | 6 | Unknowns preserved; no invented evidence | **Yes.** Unknown-time reasons are validated; synthetic fixtures and missing permission/transport evidence are explicitly labelled. |
> | 7 | Complete execution record | **Yes.** `docs/work/corpus/extraction.md` records interpreter, commands, reported results, gaps, and next actions. Reported green-suite results were not reproduced here. |
> | 8 | Consistent with domain invariants | **No.** Recorded claims omit immutable source-version identity, undermining exact source-revision lineage. |
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/corpus/extract/schema.py:122` | Citation and claim identity omit `source_version`; identical passages from different revisions produce indistinguishable claims. `check.py` selects the first matching passage rather than preserving the cited revision. | In-memory reproduction extracted the fixture against version 1 and version 2: both kept five claims, and the complete claim lists were identical. The ontology requires an exact source revision/locator. | Include immutable version identity in the recorded citation and claim identity; require version-specific matching and add a regression covering unchanged passages across revisions. |
> | blocking | `scripts/corpus/extract.py:399` | Every supported live request is refused because HIGH thinking is incompatible with the unchanged transport. | `require_carried_thinking` compares hard-coded accepted configurations against HIGH; `transport.py:179–181` accepts only `thinkingBudget: 0`. The packet records gap G-1. | Resolve the recorded CORE transport dependency through the authorized task/intent route, then demonstrate compatibility offline without executing a model call. |
> 
> Executed checks:
> 
> - Verify command: **51 tests; 38 passed, 13 errors** from unavailable writable temporary directories.
> - Full offline suite: **1,030 tests; 224 errors, 29 skipped**; sandbox temporary-directory failures prevent a green-suite conclusion.
> - Scope, `plan.py check`, and `repo.py check`: **passed**.
> 
> **Verdict: rework** — immutable source-version lineage remains defective, and the required transport path remains blocked.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Orchestrator note (owner decision 2026-10-16, before round 3)

The owner keeps the thinking level at medium or high as the product intent (a thinking model, Gemini first, is a hackathon
use-case to show later). The live extraction call is deferred and is not required for this batch. The round 2 blocking row on
`scripts/corpus/extract.py` (gap G-1, the transport accepts only a zero thinking budget) is therefore a recorded dependency on a
CORE transport task, not a defect to fix here: keep the request carrying the decided level, keep the refusal explicit, and
demonstrate the offline path. The other round 2 rows (source_version in claim identity, the first-matching-passage pick in
check.py) stand. Recorded in docs/work/corpus/intent.md decision 3 and the input register (GATE-8).

## Designated review (GPT Sol, independent, commit `2b32bc1`, 2026-10-16 09:46, overnight round 1)

> Independent review of `feat/corpus-overnight...2b32bc1e35a6`, including all four commits from `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** All 54 extraction tests passed, covering non-verbatim citation refusal, proposed-only claims, acceptance refusal and serialized-request isolation. Full offline suite passed. Live execution remains documented and deferred. |
> | 2 | Changes within allowed paths | **No.** Scope reported `docs/work/corpus/intent.md` and exited 1. Commit `77f7ff0` introduced that change. |
> | 3 | Frozen contracts/acceptance preserved; tests not weakened | **Yes.** Frozen contracts and brief acceptance text are unchanged. Version-specific coverage was added; existing missing-layer coverage remains. |
> | 4 | No effects beyond the packet | **Yes.** Existing transport remains unchanged; no new dependency or executed model/cloud call. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures and replay receipts are labelled; blocked live execution is explicitly recorded. |
> | 6 | Unknowns preserved; no invented evidence | **Yes.** Unknown-time reasons remain validated. Citations now require the immutable revision, and tests demonstrate different claim identities across revisions. |
> | 7 | Complete execution/handoff record | **Yes.** `extraction.md` records interpreter, commands, results, unresolved CORE dependency, scope failure and next action. |
> | 8 | Consistent with direction/domain invariants | **Yes.** Exact source-version citation matching and proposed-only output preserve lineage and analyst authority. The recorded owner decision explicitly defers live transport compatibility. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_extract` — **54 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,147 tests, OK (skipped=44)**; browser classes skip as permitted.
> - `/usr/bin/python3 scripts/plan.py scope CORP-3 feat/corpus-overnight` — **failed**, listing `docs/work/corpus/intent.md`.
> - `plan.py check`, `repo.py check`, and `git diff --check feat/corpus-overnight...HEAD` — **passed**.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/corpus/intent.md:78` | The reviewed range changes a file outside the brief’s allowed paths, preventing the required scope gate from passing. | Scope exits 1; the packet attributes this to orchestrator commit `77f7ff0`. Scoping against that commit excludes part of the requested review range. | Have the guardian/orchestrator reconcile the authorized intent amendment with the task’s allowed scope, then rerun scope against the requested base. Preserve the recorded owner decision. |
> 
> **Verdict: escalate** — implementation acceptance checks pass, but the orchestrator’s intent amendment requires a scope authorization correction before this range can be accepted.

Verdict recorded by the overnight runner: **escalate**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `9b2daae`, 2026-10-16 09:55, overnight round 2)

> Independent review of `feat/corpus-overnight...9b2daaeedc00`, including all seven commits in `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** All 54 extraction tests pass, covering citation refusal, proposed-only output, unchanged accepted assumptions, and serialized-request isolation. Full offline suite passes. Live execution is documented and deferred. |
> | 2 | Changes within allowed paths | **No.** Scope exits 1, listing `docs/work/corpus/intent.md`. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** Frozen contracts and brief acceptance text are unchanged. Revision-specific regression coverage was added. |
> | 4 | No effects beyond the packet | **Yes.** Existing Gemini transport remains unchanged; no new dependency or executed model/cloud call appears in the change. |
> | 5 | Truthful mode labels | **Yes.** Fixtures and replay receipts identify synthetic execution; the live transport refusal and deferred call are explicit. |
> | 6 | Unknowns preserved; no invented evidence | **Yes.** Unknown-time reasons remain validated; citations and claim identities now distinguish immutable source revisions. Synthetic numbers are labelled. |
> | 7 | Complete execution/handoff record | **Yes.** `extraction.md` records interpreter, commands, results, unresolved scope and CORE dependencies, and the exact next action. |
> | 8 | Consistent with direction and domain invariants | **Yes.** Complete passage matching preserves source lineage; proposed claims cannot alter accepted assumptions or applicability. The recorded owner decision defers live compatibility. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_extract` — **54 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,147 tests, OK (skipped=44)**, including the permitted browser skips.
> - `/usr/bin/python3 scripts/plan.py scope CORP-3 feat/corpus-overnight` — **failed**, listing the intent file.
> - `plan.py check` and `repo.py check` — **passed**.
> - `git diff --check feat/corpus-overnight...HEAD` — reports trailing whitespace in the review record.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/corpus/intent.md:78` | An out-of-scope intent amendment prevents the required scope gate from passing. | Scope exits 1; commit `77f7ff0` introduced the amendment. The subsequent handoff documents reconciliation but does not implement it. | Guardian/orchestrator must reconcile authorization with the task’s allowed scope, preserve the owner decision, and rerun scope against `feat/corpus-overnight`. |
> 
> **Verdict: escalate** — implementation acceptance passes, but the unresolved scope authorization belongs to the plan and prevents acceptance of this branch range.

Verdict recorded by the overnight runner: **escalate**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `130c1ae`, 2026-10-16 12:12, overnight round 1)

> Independent review of `feat/corpus-overnight...130c1ae8ad30`, including all eight commits in `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** All 54 extraction tests passed, demonstrating non-verbatim refusal, proposed-only claims, unchanged accepted assumptions, and serialized-request isolation. Full offline suite passed. Live execution is documented and deferred. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORP-3 allowed paths`. The earlier intent-file finding no longer applies to this range. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** No frozen-contract or acceptance changes in the diff. Revision-specific tests were added; existing coverage remains. |
> | 4 | No effects beyond the packet | **Yes.** Existing Gemini transport remains unchanged; no new dependency or executed model/cloud call appears in the change. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures and replay receipts are labelled; deferred live execution and transport refusal are explicit. |
> | 6 | Unknowns preserved; no invented evidence | **Yes.** Unknown-time reasons remain validated. Citations and claim identities now preserve source revisions; synthetic receipt values are labelled. |
> | 7 | Complete execution/handoff record | **Yes, with minor finding below.** Packet records interpreter, commands, results, dependencies and next actions, but its latest scope handoff is stale. |
> | 8 | Consistent with direction and domain invariants | **Yes.** Complete citation matching preserves source lineage; extraction cannot accept claims or alter assumptions/applicability. The recorded owner decision defers live transport compatibility. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_extract` — **54 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,164 tests, OK (skipped=44)**, including permitted browser skips.
> - `/usr/bin/python3 scripts/plan.py scope CORP-3 feat/corpus-overnight` — **OK**.
> - `plan.py check` and `repo.py check` — **passed**.
> - `git diff --check feat/corpus-overnight...HEAD` — trailing whitespace in the review record.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/corpus/extraction.md:870` | Latest handoff directs unnecessary scope reconciliation. | Calls that hand-back the remaining open item; current requested scope check passes. | Append the current scope result and update the next action, preserving historical evidence. |
> | minor | `docs/work/reviews/CORP-3.md:81` | Trailing spaces fail whitespace validation. | `git diff --check` reports ten quoted blank lines. | Remove trailing spaces. |
> 
> **Verdict: accept** — all required acceptance checks pass, with no blocking or important findings; live transport compatibility remains an explicitly deferred CORE dependency.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `e2d6ec4`, 2026-10-16)

> Independent review of `feat/corpus-overnight...130c1ae8ad30`, including all eight commits in `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** All 54 extraction tests passed, demonstrating non-verbatim refusal, proposed-only claims, unchanged accepted assumptions, and serialized-request isolation. Full offline suite passed. Live execution is documented and deferred. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORP-3 allowed paths`. The earlier intent-file finding no longer applies to this range. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** No frozen-contract or acceptance changes in the diff. Revision-specific tests were added; existing coverage remains. |
> | 4 | No effects beyond the packet | **Yes.** Existing Gemini transport remains unchanged; no new dependency or executed model/cloud call appears in the change. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures and replay receipts are labelled; deferred live execution and transport refusal are explicit. |
> | 6 | Unknowns preserved; no invented evidence | **Yes.** Unknown-time reasons remain validated. Citations and claim identities now preserve source revisions; synthetic receipt values are labelled. |
> | 7 | Complete execution/handoff record | **Yes, with minor finding below.** Packet records interpreter, commands, results, dependencies and next actions, but its latest scope handoff is stale. |
> | 8 | Consistent with direction and domain invariants | **Yes.** Complete citation matching preserves source lineage; extraction cannot accept claims or alter assumptions/applicability. The recorded owner decision defers live transport compatibility. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_corpus_extract` — **54 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,164 tests, OK (skipped=44)**, including permitted browser skips.
> - `/usr/bin/python3 scripts/plan.py scope CORP-3 feat/corpus-overnight` — **OK**.
> - `plan.py check` and `repo.py check` — **passed**.
> - `git diff --check feat/corpus-overnight...HEAD` — trailing whitespace in the review record.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/corpus/extraction.md:870` | Latest handoff directs unnecessary scope reconciliation. | Calls that hand-back the remaining open item; current requested scope check passes. | Append the current scope result and update the next action, preserving historical evidence. |
> | minor | `docs/work/reviews/CORP-3.md:81` | Trailing spaces fail whitespace validation. | `git diff --check` reports ten quoted blank lines. | Remove trailing spaces. |
> 
> **Verdict: accept** — all required acceptance checks pass, with no blocking or important findings; live transport compatibility remains an explicitly deferred CORE dependency.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
