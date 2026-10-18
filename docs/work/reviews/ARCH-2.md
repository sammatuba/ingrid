
## Designated review (GPT Sol, independent, commit `275a495`, 2026-10-16 16:31, overnight round 1)

> Independent review of `feat/price-outlook...HEAD`, commit `275a49565eb7df4aa80c29280ac66947e64a0caf` (one commit). Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Executed checks confirm 23 thresholds, 14 composer rows, permitted labels, and detection of missing/duplicate IDs. The packet answers all five #79 items, explicitly identifying unfinished issue-wide work rather than claiming completion. |
> | 2 | Allowed paths only | **Yes.** `/usr/bin/python3 scripts/plan.py scope ARCH-2 feat/price-outlook` printed `OK`. |
> | 3 | Contracts, acceptance and existing tests preserved | **Yes.** The six-file diff changes none of the frozen contracts, acceptance text or existing tests. |
> | 4 | No unapproved dependencies or effects | **Yes.** Implementation uses existing repository helpers and stdlib. The packet reports read-only GitHub access to answer the explicitly referenced issue; no runtime network call or external write was added. |
> | 5 | Truthful mode labels | **Yes.** Thresholds are labelled `deployed`; composer rows `test_fixture`, with supporting records and limitations explained in the packet. |
> | 6 | Unknowns preserved; no invented facts | **No.** Unknown owners, intervals and revisions remain explicit, but three price-band propositions contradict the actual SQL classification. |
> | 7 | Reproducible packet and handoff | **No.** Interpreter, commands, unfinished work and next action are recorded, but the claimed passing suite does not describe the reviewed tree: its progress-state test reproducibly fails. |
> | 8 | Consistent with product and domain invariants | **No.** Incorrect price-band propositions undermine the register’s evidence-to-assumption fidelity. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/PROGRESS.md:129` | Duplicate task rows overwrite the correct ARCH-1 state when parsed. | Added ARCH-1 `pending` follows existing `in_progress`; `test_progress_record_matches_task_states` fails independently of sandbox restrictions. ARCH-2 is also duplicated. | Preserve the original ARCH-1 row; update the existing ARCH-2 row instead of adding rows. Rerun verification and refresh the packet. |
> | important | `docs/work/outlook-archive/register.json:68` | Three propositions assign thresholds to the wrong price bands. | Lines 68, 95 and 122 say `<3000 → very_low`, `<8000 → low`, `<20000 → normal`. `05_labels_price.sql` assigns those successive ranges `low`, `normal`, `high`; `very_low` requires `<0`. Citation and ID checks pass despite these errors. | Correct all three propositions and the packet’s matching table; include lower bounds and verify representative values against the SQL. |
> | important | `src/outlook/register.py:131` | Date validation accepts impossible valid intervals. | Executed probe: `record()` accepts `valid_from="2026-99-99"`. Validation checks only the string pattern. | Validate calendar dates using `datetime.date.fromisoformat`; add invalid-month/day coverage. |
> | minor | `src/outlook/register.py:150` | Malformed enum values escape the documented error contract. | Executed probe with `family=[]` raises `TypeError`, rather than `RegisterError('INVALID_RECORD')`; layer/state membership has the same pattern. | Check string types before set membership and cover malformed JSON types. |
> 
> Verification executed:
> 
> - Full requested suite: **1581 tests; FAILED (2 failures, 310 errors, 62 skips)**. Temporary-directory restrictions caused extensive errors and the fixture-builder failure; the ARCH-1 progress-state failure is a confirmed branch defect. Browser skips are accepted as instructed.
> - Forty register checks that require no temporary writes: **OK**, including committed data, validators, missing/duplicate detection and dangling citations.
> - `plan.py scope ARCH-2 feat/price-outlook`: **OK**.
> - `plan.py check`: **OK: 93 tasks, 8 gates**.
> - `repo.py check`: **PASS**.
> 
> **Verdict: rework** — incorrect registered propositions, invalid-date acceptance and the reproducible progress-state failure require correction before acceptance.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `77dd399`, 2026-10-16 16:49, overnight round 2)

> Independent review of `77dd3997a9ca`, covering `git diff feat/price-outlook...HEAD` and all three commits in `git log feat/price-outlook..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **Yes.** Executed register checks confirm 23 thresholds, 14 composer rows, permitted labels, and detection of missing/duplicate IDs. The packet answers #79 item by item, explicitly identifying unfinished issue-wide work. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside ARCH-2 allowed paths`. |
> | 3 | Frozen contracts, acceptance text and existing tests preserved | **Yes.** The seven-file diff changes none of these; register tests are additive. |
> | 4 | No unapproved dependencies or effects | **Yes.** Runtime uses stdlib and existing repository helpers; no new service or external call. Packet documents read-only issue retrieval. |
> | 5 | Mode labels truthful | **Yes.** Thresholds carry `deployed`; composer rows carry `test_fixture`. The packet cites supporting records and limits. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** All 37 owners remain `unassigned`; intervals and checked revisions remain null. Corrected price propositions agree with the SQL ladder. |
> | 7 | Reproducible packet and handoff | **Yes.** Packet records interpreter, commands, results, unresolved issue work and exact next action. Its recorded passing suite was not reproduced in this restricted environment. |
> | 8 | Consistent with product and domain invariants | **Yes.** Provenance, state and acceptance remain distinct; semantic confidence is not presented as event probability. No material contradiction found. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests`: **1591 tests; FAILED (1 failure, 310 errors, 62 skips)**. Temporary-directory restrictions caused the errors and fixture-builder failure. Expected browser skips are accepted; this was **not** a passing full-suite run.
> - Register checks requiring no temporary writes: **52 tests, OK**; four temporary-write tests excluded from this supplemental run.
> - Direct audit: **37 records; 23 thresholds; 14 composer rows; missing, duplicate, unknown, dangling and unlabelled lists empty**.
> - `/usr/bin/python3 scripts/plan.py scope ARCH-2 feat/price-outlook`: **OK**.
> - `plan.py check`: **OK: 93 tasks, 8 gates**.
> - `repo.py check`: **PASS**.
> 
> Findings: **No unresolved blocking or important findings.** The prior four findings are corrected in the reviewed revision.
> 
> **Verdict: accept** — all bounded task acceptance items were demonstrated, with full-suite reproduction limited by the sandbox’s temporary-write restriction.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
