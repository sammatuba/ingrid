
## Review round 2026-10-11 evening (commit `3dee303`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `3dee303d38e5` against `feat/h1-api-persistence`, including commits `7160a22` and `3dee303`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes, within the local evidence boundary.** Executed validation confirms 25 pairs, 135 valid `h0.v1` records, eight classes, 28 frozen labels and both contestable-rule assumption kinds. Committed policy/fixture digests reproduce. Pre-backend freezing is recorded in the packet; the generator invokes no backend. |
> | 2 | Changes stay inside allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside EVAL-1 allowed paths`. |
> | 3 | Frozen contracts/acceptance unchanged; tests not weakened | **Yes.** Diff adds fixtures/documentation and changes only EVAL-1’s coordination state; no existing contract or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Generator uses existing repository functions and stdlib; no added service, credential access, transport or model call. |
> | 5 | Truthful mode labels | **Yes.** Fixtures explicitly identify fictional synthetic content; computed composition expectations are distinguished from model results and analyst validation. |
> | 6 | Unknowns preserved; no unsupported facts/results | **No.** `pb-lc-2` treats a future event as an already confirmed observation; see finding 2. |
> | 7 | Packet records interpreter, commands, results and handoff | **Yes.** `fixtures.md` records Python 3.14.4, verification, limitations, self-review and EVAL-2’s next action. Its reported full-suite success could not be reproduced in this sandbox. |
> | 8 | Consistent with direction and domain invariants | **No.** Cutoff pairs violate the same-snapshot contract, and one observation has inconsistent chronology. |
> 
> Executed with `/usr/bin/python3` (Python 3.14.4):
> 
> | Command | Result |
> |---|---|
> | `-m unittest tests.test_review_case -v` | **PASS:** 43 tests |
> | `scripts/plan.py scope EVAL-1 feat/h1-api-persistence` | **OK** |
> | `tests/fixtures/probe-bundle/build.py --check` | **PASS:** 25 pairs, eight classes, 28 labels; both digests match |
> | Explicit `validate_record` over every pair’s records | **PASS:** 135 records |
> | `scripts/plan.py check` | **OK:** 41 tasks, seven gates |
> | `scripts/repo.py check` | **PASS** |
> | `-m unittest discover -s tests` | **Not green:** 251 tests, 30 errors caused by unavailable writable temporary directories |
> 
> Findings, both unresolved:
> 
> 1. **important | tests/fixtures/probe-bundle/build.py:675 | Cutoff fixtures cannot satisfy the frozen pairing contract |** Every `pb-lc-*` pair has different `expected_snapshot_ref` values at T0 and T1. The generator changes the audit cutoff and builds a separate snapshot for each compile. `docs/work/probe-bundle/intent.md:97–102` explicitly requires the same snapshot and rejects different snapshots, yet these fixtures promise successful pairing differences. **Correction:** compile both information cutoffs against one shared snapshot, regenerate expectations/digests, and assert snapshot-reference equality for all pairing fixtures.
> 
> 2. **important | tests/fixtures/probe-bundle/build.py:437 | Future-event knowledge is labelled as a confirmed observation |** `pb-lc-2` says the unit “returned … on 2026-10-06,” but the source is published/known October 1 and T1 is October 1 at 11:30. Its frozen answers set `q6=yes`, sufficiency `yes`, and label `supports`; the rationale calls this a “confirmed observation.” Passing schema validation does not establish that chronology. **Correction:** place the observed-return document and cutoffs after the event while preserving the intended cutoff transition, or explicitly make this an inconsistent-source case with appropriate expectations; regenerate and verify the frozen artifacts.
> 
> **Verdict: rework — the fixtures validate structurally, but the pairing-contract mismatch and future-observation annotation make them unreliable evaluation inputs.**
**Verdict: rework.** Executor rework next session: cutoff pairs must share one snapshot per the frozen pairing contract, and pb-lc-2 must not label a future event as a confirmed observation.

## Interim review (orchestrator seat, Fable, commit `00e3eee`, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated re-review is required before `done`. Reviewed `00e3eee` against `feat/h1-api-persistence` (rework commit `4b470ff`; `3d35127` and `00e3eee` are record-only). Working tree clean; no file edited except this record. Run from the EVAL-1 worktree with `/usr/bin/python3` (Python 3.14.4).

| # | Checklist | Answer and evidence |
|---|---|---|
| 1 | Every acceptance item demonstrated | **Yes.** Own run: `validate_record` over every `pb-*.json` passes for 25 pairs / 135 h0.v1 records; `build.py --check` prints `OK: 25 pairs, 8 edge classes, 28 frozen labels, policy digest b455c4a7…047cfa, fixture digest 2455c0a6…0eec89`, matching the digests recorded in `fixtures.md`; manifest `contestable_rule.pairs_by_assumption_kind` lists both kinds, with `pb-er-1..4` covering the earlier-observed-return row for each. No backend, model or network call exists in the generator or fixtures (S2 unbuilt). |
| 2 | Inside allowed paths | **Yes.** `plan.py scope EVAL-1 feat/h1-api-persistence` → `OK: all changed files inside EVAL-1 allowed paths`. |
| 3 | No frozen contract / acceptance / test change | **Yes.** `git diff feat/h1-api-persistence...HEAD` touches no file under `src/`, `tests/*.py`, `docs/work/probe-bundle/intent.md` or `docs/product/`; only fixtures, `fixtures.md`, this record, `tasks.json` state and `PROGRESS.md`. |
| 4 | No new dependency or external effect | **Yes.** `build.py` imports stdlib and repository modules only; check rebuilds in memory. |
| 5 | Truthful mode labels | **Yes.** Every SourceVersion carries `availability_basis: "synthetic fixture"` and fictional text; packet and README state synthetic/fictional throughout and separate table output from frozen annotation. |
| 6 | Unknowns kept unknown, no future knowledge | **Yes (prior finding 2 fixed and generalised).** `pb-lc-2` return notice `known_at` 2026-10-06T00:00Z (08:00+08) reports a 06:00+08 return; cutoffs 07:00/09:00 both follow the event; T0 omits the notice as `LATER_AVAILABILITY`. Sweep over all 25 files: 10 dated statements in `q6 = yes` context passages, 0 with event instant after `known_at`. `pb-lc-1`/`pb-lc-3` future schedules are labelled `q6 = no`. |
| 7 | Packet records interpreter, commands, results, next action | **Yes.** `fixtures.md` "Rework after independent review" lists interpreter, nine commands with results, two negative controls, acceptance re-check and the EVAL-2 hand-off. |
| 8 | Consistent with intent and invariants (prior finding 1) | **Yes.** Own sweep: all 28 compiles across 25 pairs bind their pair's single `snapshot.ref`, `snapshot.audit_cutoff == t0`, information cutoffs strictly increase, satisfying intent "Cutoff pairing" (shared assumption and snapshot, `after.cutoff > before.cutoff`). Negative controls re-run by me: tampered `pb-lc-1/t1` snapshot ref → `["pb-lc-1: compiles of a pair must share the pair's snapshot"]`; swapped `pb-lc-2` cutoffs → `SystemExit: … strictly increasing information cutoffs`. |

Verification (own run):

| Command | Result |
|---|---|
| `-m unittest tests.test_review_case` | `Ran 43 tests` OK |
| `-m unittest discover -s tests` | `Ran 261 tests` OK |
| `scripts/plan.py scope EVAL-1 feat/h1-api-persistence` | OK |
| `scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `scripts/repo.py check` | `253 Markdown files, 1102 local links, 8 skills` PASS |
| `tests/fixtures/probe-bundle/build.py --check` | OK, 25 pairs / 8 classes / 28 labels, both digests match packet |
| ad-hoc `validate_record` sweep | 25 pairs, 135 records validate |

Findings:

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| minor | `tests/fixtures/probe-bundle/manifest.json:469-477` | `contestable_rule.pairs_by_assumption_kind` matches on the q3/q6 pattern alone, so `pb-lc-2` (T0 is an outage, `q2 = outage_or_extension`, label challenges) and `pb-cl-3` appear under a rule named for observed returns; a reader of A1 could over-count the decisive subset | manifest entry vs `pb-lc-2` compiles (`q2` at T0 is not a return) | Either restrict the list to compiles where the rule fires (q8 vs label) or state in `meaning` that the list is pattern-matched, not rule-fired; `pb-er-1..4` alone satisfy the acceptance item |
| minor | `docs/work/PROGRESS.md:117-119` | Three `2026-10-11` log rows appended after the `2026-10-12` row; log is no longer in date order | `grep -n "^| 2026-10-1[12] |"` lines 116-119 | Move the three EVAL-1 rows above the 2026-10-12 row at the next coordination commit; no test depends on order |

**Interim verdict: accept.** Both rework findings are fixed at the generator level and demonstrated by my own re-runs (shared snapshot asserted for all 28 compiles, no event dated after its source's `known_at`), every acceptance item is observable, nothing frozen changed, and the two minors do not affect labels or digests; `done` still waits for the designated independent re-review.

## Designated review (GPT Astra, independent, commit `a1a36b6`, 2026-10-12)

> Independent review of `a1a36b615694` against `feat/h1-api-persistence`, covering the seven branch commits and diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed fixture check and explicit record validation: 25 pairs, eight classes, 28 annotations, 135 valid `h0.v1` records. Policy and fixture digests reproduce. `pb-er-1..4` cover both assumption kinds. Committed freeze records precede any reported backend run; generator invokes none. |
> | 2 | Changes inside allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside EVAL-1 allowed paths`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Diff changes only fixtures, packet, review record and coordination files; no frozen contract, acceptance text or existing test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Generator uses stdlib and existing repository modules; no added network, credential, model or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Fixtures identify fictional synthetic content; annotations and computed composition expectations are distinguished from backend results. |
> | 6 | Unknowns preserved; no invented factual evidence | **Yes**, with the minor rationale error below. Synthetic facts are explicitly labelled. Corrected `pb-lc-2` notice becomes known at 08:00 after its reported 06:00 return; T0 excludes it. |
> | 7 | Packet records verification and handoff | **Yes.** `fixtures.md` records interpreter, commands, results, limitations and EVAL-2’s next action. Its historical full-suite success was not reproducible under this sandbox’s restrictions. |
> | 8 | Consistent with direction and invariants | **Yes.** All 28 compiles bind their pair’s shared snapshot; paired cutoffs increase strictly. Negative controls reject mismatched snapshots and reversed cutoffs. No accepted assumption or execution authority is changed. |
> 
> Executed with `/usr/bin/python3`, Python 3.14.4:
> 
> | Command/check | Result |
> |---|---|
> | `-m unittest tests.test_review_case -v` | **43 tests passed** |
> | `scripts/plan.py scope EVAL-1 feat/h1-api-persistence` | **OK** |
> | `tests/fixtures/probe-bundle/build.py --check` | **PASS**, both recorded digests match |
> | Explicit `validate_record` sweep | **135 records passed** |
> | `scripts/plan.py check` | **OK**, 41 tasks, seven gates |
> | `scripts/repo.py check` | **PASS** |
> | `-m unittest discover -s tests` | **261 tests attempted; 37 errors** from unavailable writable temporary directories |
> 
> Finding, unresolved:
> 
> **minor | `tests/fixtures/probe-bundle/build.py:529` | Incorrect elapsed-time rationale propagates into frozen documentation |** `pb-er-1` reports October 3 against an assumed October 6 date but says “two days before”; repeated in `pb-er-1.json:337` and `fixtures.md:365`. **Correction:** use “before the assumed date” and regenerate affected digests through the documented freeze process. Atomic answers and relation labels remain unaffected.
> 
> **Verdict: accept — all task acceptance items are demonstrated, both previous important findings are resolved, and the remaining rationale error is minor.**
**Verdict: accept.** Both previous important findings resolved; one minor rationale error remains.
