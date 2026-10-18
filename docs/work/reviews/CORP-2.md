
## Designated review (GPT Sol, independent, commit `2f21255`, 2026-10-16 01:12, overnight round 1)

> Independent review of `feat/corpus-overnight...HEAD`, commit `2f21255939d7d576c5eaaebee249a845e565de64`, including all eight branch commits. Working tree clean; no files edited.
> 
> Checklist:
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **No** | Focused acceptance tests pass and real-corpus counts reproduce, but the full offline suite fails, including a reproducible progress-state mismatch. |
> | 2 | **Yes** | `/usr/bin/python3 scripts/plan.py scope CORP-2 feat/corpus-overnight` prints `OK: all changed files inside CORP-2 allowed paths`. |
> | 3 | **Yes** | Diff changes no frozen contracts, acceptance text or existing tests; `structure.py` and its tests remain unchanged. |
> | 4 | **Yes** | Deterministic offline code; pypdf is the packet-authorized local copy. No additional service, credential or external effect introduced. |
> | 5 | **Yes** | Synthetic fixtures explicitly disclaim legal authority; ERC/DOE coverage is described as synthetic-only. Real excerpts reproduce against the compendium. |
> | 6 | **No** | Unknown effectivity can still yield a definitive “in force” result; replacement precedence is assigned from registration order. |
> | 7 | **No** | Packet contains interpreter, commands and next actions, but its claimed branch-tip green suite does not match the reviewed branch’s reproducible failure. |
> | 8 | **No** | Ignoring effectivity and deriving replacement relationships from insertion order violate the intended temporal and reviewed-precedence boundaries. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/regulatory/lineage.py:314` | `in_force()` checks availability alone, ignoring supplied effectivity. | Reproduction: amendment available `2026-02-01`, effective `2026-12-01`, is selected at cutoff `2026-03-01`. Existing tests also select amendments with unknown effectivity. | Apply both availability and supplied effectivity constraints; represent unknown/imprecise effectivity explicitly. Add future-effective and unknown-effectivity tests. |
> | important | `src/regulatory/lineage.py:297` | Registration order determines `replaces` and which version wins without supplied replacement authority. Filtering unavailable ancestors can also return a broken chain. | Applying an August amendment followed by a distinct February amendment makes February replace August and win in October. Another reproduction returns a chain whose final `replaces` points to an excluded version. | Require supplied replacement relationships; reject conflicting or unresolved lineage and preserve an auditable chain at cutoff. |
> | important | `docs/work/PROGRESS.md:111` | Added duplicate rows overwrite CORP-0/CORP-1 states when the progress table is read. | `tests.test_plan.PlanTests.test_progress_record_matches_task_states` fails independently: CORP-0 is `pending` in the table versus `in_progress` in tasks.json. | Remove duplicate rows, update the existing CORP-2 row, rerun checks and correct the packet’s verification record. |
> 
> Executed verification:
> 
> - Requested verify command: **42 tests, OK**.
> - Scope: **OK**; repo check: **PASS**; plan check: **OK**.
> - Excerpt `--check`: **OK**, eight excerpts match.
> - Excerpt `--report`: reproduced **11 chapters, 636 clauses, 77 unrecognised candidates**, including the first ten on page 3, and all three manual surveys.
> - Full offline suite: **970 tests; FAILED—1 failure, 211 errors, 29 skipped**. Temporary-directory writes were blocked by the read-only sandbox; the progress-state failure reproduced independently without writes. Full-suite acceptance is therefore not demonstrated.
> 
> **Verdict: rework** — unresolved lineage correctness defects and the reproducible progress-state failure prevent acceptance.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `a77bf43`, 2026-10-16 01:24, overnight round 2)

> Independent review of `feat/corpus-overnight...a77bf43`, including the 11 commits in `git log feat/corpus-overnight..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **No** | Targeted tests and real-corpus checks passed, but the full offline suite did not pass in this sandbox. Two additional lineage defects reproduced below. |
> | 2 | Changes inside allowed paths | **Yes** | `plan.py scope CORP-2 feat/corpus-overnight` printed `OK: all changed files inside CORP-2 allowed paths`. |
> | 3 | Frozen contracts, acceptance and existing tests preserved | **Yes** | Diff leaves frozen contracts, acceptance text, `structure.py` and its existing tests unchanged. |
> | 4 | No unauthorized dependencies or external effects | **Yes** | Runtime additions use the standard library; excerpt tooling uses the packet’s local pypdf. No added network, model or cloud calls. |
> | 5 | Truthful mode labels | **Yes** | Fixtures explicitly say synthetic; packet identifies ERC/DOE coverage as synthetic-only and distinguishes real PDF excerpts. |
> | 6 | Unknowns preserved; no invented facts | **No** | February’s month endpoint is fabricated as February 29 even in non-leap years, affecting cutoff results. |
> | 7 | Packet records interpreter, commands, results and handoff | **Yes** | `structure.md` records Python 3.14, verification, rework, limits and next action. Its reported 996-test pass was not reproduced: this checkout discovered 979 tests. |
> | 8 | Consistent with domain invariants | **No** | Amendment resubmission can silently discard supplied effectivity/availability metadata and return an unsupported cutoff result. |
> 
> Verification executed with `/usr/bin/python3` and bytecode writing disabled:
> 
> - Requested verify command: **51 tests, OK**, including unchanged structure tests.
> - Requested scope command: **OK**.
> - `scripts/plan.py check`: **OK**, 71 tasks, 8 gates.
> - `scripts/repo.py check`: **PASS**.
> - `scripts/corpus/excerpt.py --check`: **OK**, eight excerpts match local PDFs.
> - `scripts/corpus/excerpt.py --report`: reproduced **11 chapters, 636 clauses, 77 unrecognised WESM candidates**, with the first ten on page 3; three manual surveys also reproduced.
> - Full offline suite: **979 tests; 211 errors; 29 skipped**. Errors include sandbox-denied temporary-directory creation. This does not establish a change-induced regression, but it does not demonstrate acceptance’s required pass.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/regulatory/lineage.py:415` | The idempotency branch compares an identity excluding dates, then returns the stored version without checking supplied metadata. Conflicting records silently succeed. | After registering the amendment effective `2026-05-15`, resubmitting the same amendment with effective `2026-12-01` returned `2026-05-15`; July still selected the amendment. | Allow idempotency only when all supplied record fields match; reject conflicting metadata explicitly. Add tests for changed effectivity and availability. |
> | important | `src/regulatory/lineage.py:90` | February always ends on day 29, delaying admission for non-leap-year month metadata. | With effective month `2026-02` and availability `2026-02-01`, cutoff `2026-02-28` excluded the amendment as `effectivity_imprecise`. February had fully elapsed. | Calculate the actual calendar month endpoint; test leap and non-leap February for both effectivity and availability. |
> 
> **Verdict: rework** — two reproduced date-handling defects remain, and a full offline-suite pass at the reviewed head remains undemonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `21fe056`, 2026-10-16 09:32, overnight round 1)

> Independent review of **21fe056**, against `feat/corpus-overnight`. Inspected both commits (`664b8e9`, `21fe056`), the diff, task brief, review protocol and task evidence. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** Focused suite: 54 tests OK, covering amendment cutoffs, unchanged clauses and diagnostics. Real-corpus report reproduced 11 chapters, 636 clauses and 77 unrecognised candidates; first ten are recorded with page numbers. Full suite and repo check passed. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope CORP-2 feat/corpus-overnight` printed OK; all five changed files are allowed. |
> | 3 | Contracts and tests preserved | **Yes.** No frozen contract or acceptance changes. Existing structure implementation/tests unchanged; three tests added, none weakened or skipped. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Added `calendar` is standard library. No new service, credential, network, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures explicitly disclaim legal authority; real excerpts carry source citations and fingerprints. |
> | 6 | Unknowns preserved | **Yes.** Unknown-date exclusions remain explicit. February boundaries now use the actual calendar; conflicting resubmitted metadata is refused. |
> | 7 | Complete execution record | **Yes.** `docs/work/corpus/structure.md` records interpreter, commands, results, unresolved integration work and exact next actions. |
> | 8 | Consistent with product/domain invariants | **Yes.** Dates and replacement relationships remain supplied metadata; document wording confers no applicability, precedence or approval. |
> 
> Executed checks:
> 
> - Required verify command: **54 tests, OK**.
> - Full offline suite: **1,144 tests, OK (44 skipped)**, including the browser skips permitted for this review.
> - Scope: **OK**; repo check: **PASS**; plan check: **OK**.
> - Excerpt `--check`: **OK**, eight excerpts match the compendium.
> - Excerpt `--report`: reproduced WESM Rules and three-manual counts and page-attributed candidates.
> 
> Findings: **None.** Both previous date-handling findings are corrected and covered by passing regression tests.
> 
> **Verdict: accept** — all required acceptance checks were demonstrated, with no blocking or unresolved important findings.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `0b662ab`, 2026-10-16)

> Independent review of **21fe056**, against `feat/corpus-overnight`. Inspected both commits (`664b8e9`, `21fe056`), the diff, task brief, review protocol and task evidence. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **Yes.** Focused suite: 54 tests OK, covering amendment cutoffs, unchanged clauses and diagnostics. Real-corpus report reproduced 11 chapters, 636 clauses and 77 unrecognised candidates; first ten are recorded with page numbers. Full suite and repo check passed. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope CORP-2 feat/corpus-overnight` printed OK; all five changed files are allowed. |
> | 3 | Contracts and tests preserved | **Yes.** No frozen contract or acceptance changes. Existing structure implementation/tests unchanged; three tests added, none weakened or skipped. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Added `calendar` is standard library. No new service, credential, network, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures explicitly disclaim legal authority; real excerpts carry source citations and fingerprints. |
> | 6 | Unknowns preserved | **Yes.** Unknown-date exclusions remain explicit. February boundaries now use the actual calendar; conflicting resubmitted metadata is refused. |
> | 7 | Complete execution record | **Yes.** `docs/work/corpus/structure.md` records interpreter, commands, results, unresolved integration work and exact next actions. |
> | 8 | Consistent with product/domain invariants | **Yes.** Dates and replacement relationships remain supplied metadata; document wording confers no applicability, precedence or approval. |
> 
> Executed checks:
> 
> - Required verify command: **54 tests, OK**.
> - Full offline suite: **1,144 tests, OK (44 skipped)**, including the browser skips permitted for this review.
> - Scope: **OK**; repo check: **PASS**; plan check: **OK**.
> - Excerpt `--check`: **OK**, eight excerpts match the compendium.
> - Excerpt `--report`: reproduced WESM Rules and three-manual counts and page-attributed candidates.
> 
> Findings: **None.** Both previous date-handling findings are corrected and covered by passing regression tests.
> 
> **Verdict: accept** — all required acceptance checks were demonstrated, with no blocking or unresolved important findings.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
