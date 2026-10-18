
## Designated review 1 (GPT Sol, independent, commit `7f191e8`, 2026-10-13)

> Independent review of `task/CORE-9...HEAD`, commit `4acc4497a938`. Inspected all four commits, the diff, task brief, intent, review process and implementation packet. Working tree was clean; no files edited.
> 
> Executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_wesm_sources -v` — **34 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope DATA-1 task/CORE-9` — **OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **337 tests, OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **yes** | All four brief acceptance checks ran: byte/quote digest recomputation, clock disagreement rejection, repost lineage, and h0.v2 validation with an injected permission registry. The additional intent requirement for ambiguity from the real sample remains undemonstrated. |
> | 2 | **yes** | Scope check against the requested base printed OK. |
> | 3 | **yes** | Diff changes no frozen contracts or acceptance text; existing tests were not weakened or skipped. |
> | 4 | **yes** | Readers use stdlib and local files. BigQuery export is explicitly named in the packet; no added runtime dependency or unnamed service. |
> | 5 | **yes** | Fixtures identify real exported rows; tests explicitly label constructed counterexamples. No live inference claim. |
> | 6 | **no** | Missing publication time is replaced with posting/trading time in advisory and register source payloads. |
> | 7 | **yes** | Packet records Python 3.14.4, commands/results, self-review, unfinished ambiguity evidence and next action. Later export evidence is appended. |
> | 8 | **no** | Publication-time fallbacks contradict the invariant that unknown time stays unknown. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/wesm/advisories.py:225` | A syntactically matching but invalid header date raises uncaught `ValueError`, aborting the entire batch instead of reporting the refused row. | Executed counterexample with month `99`: `parse_advisories()` raised `ValueError: month must be in 1..12`. Its handler catches only `WesmSourceError`. | Convert invalid header-calendar values to a reported `MALFORMED_ROW`; test that valid neighboring rows still parse. |
> | important | `src/adapters/wesm/advisories.py:261` | A grammar miss asserts posting time as publication time despite having no parsed publication header. | Executed grammar-miss input produced `header=None` and a populated `published_at`. | Resolve the missing-publication representation through intent if the frozen contract cannot preserve unknown time; do not substitute availability time. |
> | important | `src/adapters/wesm/registry.py:196` | Register source asserts midnight publication despite no publication instant in the copy. | Lines 194–197 explicitly acknowledge the missing publication instant, then assign the trading-day stamp. | Obtain an authorized publication-time rule or revise the intent/contract to represent the unknown. |
> | important | `docs/work/real-sources/implementation.md:19` | The real-sample ambiguity acceptance requirement remains unmet. | Packet acknowledges that the sample has no same-day dual participant; only a constructed counterexample demonstrates ambiguity. | Supply a permitted real sample demonstrating the requirement, or have the guardian resolve the acceptance wording. |
> | minor | `scripts/data/wesm/export.sh:28` | Documented `export.sh START END` invocation treats START as the mode and exits with usage. | `MODE=$1`, while START/END read `$2/$3`; only `window` and `samples` are accepted. | Support the documented invocation or document `export.sh window START END` consistently. |
> 
> **Verdict: rework** — Passing checks demonstrate the brief’s four acceptance items, but uncaught malformed headers, unsupported publication timestamps and unresolved intent acceptance evidence prevent acceptance.
**Verdict: rework.** Owner rulings Round 9: (1) invalid header calendar values become a reported MALFORMED_ROW with valid neighbours still parsed (code fix). (2) Sources with no publication instant keep the stand-in (trading-day midnight, posting time) but label it in the record as an approximation, never as a published time. (3) Ambiguity: the orchestrator searched the whole register (192,159 rows, 554 resources): zero same-day multi-participant rows; 444 exact duplicate rows on 2024-06-26 (same participant and capacity). Keep the constructed refusal example, add a test that an exact duplicate collapses without refusal, and reword the acceptance evidence to cite the search (strategy.md Round 9 follow-up). Rebuilt by the orchestrator on the accepted CORE-9; the one remaining suite error (tests.test_eval_probe_bundle import) is the planned h0.v2 fixture coupling resolved by CORE-8, so record it rather than fix it. Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `caa02c0`, 2026-10-13)

> Independent review of **caa02c0acd0d9d84ca32cf52c723d3bce5deaf88**, using `git diff task/CORE-9...HEAD` and all seven commits from `git log task/CORE-9..HEAD`. Working tree was clean; no repository files edited.
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1. Acceptance demonstrated | **yes** | The executed 41-test verify command recomputes byte and quote digests, rejects clock disagreement, verifies repost lineage, and validates every sample-produced record as h0.v2 with an injected signed permission registry. Midnight wrap and register runs also pass. Real ambiguity was not demonstrated; the documented Round 9 disposition uses a labelled constructed example and real duplicate-collapse evidence. |
> | 2. Allowed paths | **yes** | `scope DATA-1 task/CORE-9` printed OK; all 14 changed files are allowed. The process’s integration-base scope check exits 1 solely for the parent’s `docs/work/reviews/CORE-9.md`, not a DATA-1 change. |
> | 3. Frozen contracts, acceptance and tests preserved | **yes** | No frozen contract or acceptance text changed in the diff. The test file is additive; existing tests were not weakened, deleted or skipped. |
> | 4. Dependencies and external effects bounded | **yes** | Readers use local files and stdlib. BigQuery export is explicitly authorized by the packet. Reviewer tests run export.sh with stubbed `bq`; no cloud call was made during this review. |
> | 5. Truthful mode labels | **yes** | Committed samples identify permitted real exports; constructed counterexamples are labelled in tests. No live inference or model receipt is claimed. |
> | 6. Unknowns preserved | **yes** | Missing publication instants carry `published_at_approximate: true`, following the Round 9 owner ruling. Invalid headers are reported as refusals; mapping candidates remain unreviewed or ambiguous. |
> | 7. Complete packet evidence | **yes** | Implementation packet records interpreter, exact commands/results, previous finding dispositions, inherited fixture failure, unfinished downstream case work and independent re-review as the next action. |
> | 8. Domain and direction consistency | **yes** | Byte evidence and references are preserved; reposts share lineage; register gaps are not interpolated; parser categories remain selection metadata; mappings receive no automatic analyst approval. |
> 
> Executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_wesm_sources -v` — **41 tests, OK**.
> - `/usr/bin/python3 scripts/plan.py scope DATA-1 task/CORE-9` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 45 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **461 tests, FAILED (errors=1)**: `tests.test_eval_probe_bundle` fixture import drift. I reproduced the identical error on an isolated archive of `task/CORE-9`, confirming it is inherited.
> 
> Findings: **none unresolved in the DATA-1 diff**. The prior malformed-header, publication-label, ambiguity-evidence and export-invocation findings are addressed.
> 
> **Verdict: accept** — All four brief acceptance items were demonstrated, the prior findings are resolved under the recorded owner rulings, and the remaining suite error reproduces on the parent branch.
**Verdict: accept.** Samples re-exported from BigQuery byte-identical at caa02c0. Merges with CORE-9 and CORE-8.
