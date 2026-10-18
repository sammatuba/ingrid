# Review: EVAL-6

Reviewed commit `154cddb` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of `154cddbfb258dd8c73270efeb348fbb1c9a3918c`, using the requested diff and log against `feat/h1-api-persistence`. One commit; three changed files; working tree clean. No files edited.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **no** | Metric definitions have the defects below. The freeze digest matches PROGRESS, but pending task/closed gate states alone do not demonstrate that no session occurred. |
> | 2. Changes within allowed paths | **yes** | Requested scope command printed `OK: all changed files inside EVAL-6 allowed paths`. |
> | 3. Contracts, acceptance text and tests preserved | **yes** | Diff changes only the protocol, EVAL-6 state, and PROGRESS row/log. |
> | 4. No unauthorized dependencies or external effects | **yes** | Documentation-only change; no new executable calls or dependencies. |
> | 5. Truthful mode labels | **yes** | Protocol sections 4, 10 and 12 distinguish saved artifacts, backend mode and synthetic results; no live-run claim. |
> | 6. Unknowns remain unknown | **no** | Lines 15–16 and 265 infer “no analyst session has occurred” from planning states, without a session record or explicit facilitator/owner attestation. |
> | 7. Complete verification and handoff record | **yes** | Section 13 records interpreter, commands, reported results, unfinished inputs and next action. Author-reported suite success was not reproduced here. |
> | 8. Consistent with governing documents | **no** | M1 conflates missed and falsely asserted issues; M3 has conflicting definitions, undermining blueprint §9 measurement. |
> 
> All finding locations below refer to `docs/work/probe-bundle/baseline-protocol.md`. Disposition: unresolved.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | baseline-protocol.md:179 | M1 measures a mixture of omissions and false positives, preventing interpretation as “missed material issues.” | M1 includes categories 1 **and 2**; category 2 explicitly includes non-key items falsely asserted as material (159–160). | Count missed key issues separately; report false material assertions and wrong-direction answers as separate measures. |
> | important | baseline-protocol.md:181 | Two incompatible M3 rules allow different results from the same session. | Lines 147–149 exclude initially indefensible dispositions from time-to-defensible; line 181 instead assigns disposition time plus rework time. No analyst rework timer or final defensibility endpoint is specified. | Choose one rule, define rework start/stop and successful adjudication, and specify how unresolved/capped cases are reported consistently. |
> | important | baseline-protocol.md:265 | Acceptance is marked met using an unsupported inference about session history. | Closed GATE-7 and pending EVAL-7 establish recorded authorization/progress, not actual absence of prior sessions; the timestamp comparison in lines 13–15 is prospective. | Record an attributable pre-session confirmation and freeze reference; describe the future annex check as pending rather than already demonstrated. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 239 Markdown files, 1004 links.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-6 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 41 tasks, 7 gates.
> - `/usr/bin/python3 -B -m unittest discover -s tests -v` — **251 tests, 30 errors**; sandbox lacked a usable temporary directory. This does not establish a change-induced regression or reproduce the reported passing suite.
> 
> **Verdict: rework** — resolve the metric definitions and substantiate the pre-session freeze claim before accepting EVAL-6.
## Outcome and next action

**Verdict: rework.**
Executor separates missed key issues from false material assertions, picks one time-to-defensible rule with defined rework timing, and records the pre-session freeze as pending rather than met; then re-review.

## Review round 2026-10-11 evening (commit `1e7e48c`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `1e7e48ccfb89222d8da4c4d74409da2cad732bdc` against `feat/h1-api-persistence`: inspected the requested diff and log, covering three commits and four files. Working tree clean; no files edited.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **no** | Protocol line 291 explicitly leaves pre-session confirmation pending. Metrics now match blueprint §9: M1 excludes false positives; M3 uses one timing rule. |
> | 2. Changes within allowed paths | **yes** | Requested scope command printed `OK: all changed files inside EVAL-6 allowed paths`. |
> | 3. Frozen contracts, acceptance text and tests preserved | **yes** | Diff contains only the protocol, review record, EVAL-6 state and PROGRESS updates. |
> | 4. No unauthorized dependencies or external effects | **yes** | Documentation-only diff; no dependencies, service calls or runtime changes introduced. |
> | 5. Truthful mode labels | **yes** | Sections 4, 10 and 12 distinguish saved assistance, backend mode and synthetic results; no live-run result claimed. |
> | 6. Unknowns remain unknown | **no** | Despite pending confirmation, lines 316–320 assert all findings fixed and that v1 never governed a session. |
> | 7. Complete verification and handoff record | **yes** | Section 13 records interpreter, commands, results, unfinished inputs and next action. Author-reported suite success was not reproduced here. |
> | 8. Consistent with governing documents | **no** | Unsupported session-history assertions remain contrary to the evidence invariant. Earlier M1/M3 inconsistencies are resolved. |
> 
> All finding locations below refer to `docs/work/probe-bundle/baseline-protocol.md`. Disposition: unresolved.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | baseline-protocol.md:291 | A required acceptance item remains undemonstrated; prescribing a future check does not establish that the freeze preceded every session. | Confirmation is explicitly **pending**, deferred to EVAL-7. The matching file digest establishes content identity, not session chronology. | Obtain and record attributable confirmation tied to the frozen version, digest and timestamp before accepting EVAL-6. |
> | important | baseline-protocol.md:320 | Rework retains an unsupported assertion about session history. | “Never governed a session” contradicts the acknowledged absence of confirmation at line 291; line 316 nevertheless declares all findings fixed. The latest PROGRESS entry repeats the assertion. | Remove or qualify these assertions until supported, and describe the freeze finding as unresolved. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**: 240 Markdown files, 1007 links, 8 skills.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-6 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**: 41 tasks, 7 gates.
> - `/usr/bin/python3 -B -m unittest discover -s tests -v` — **251 tests, 30 errors** from unavailable writable temporary directories in the read-only sandbox; this does not establish a change-induced regression.
> 
> **Verdict: rework** — the metric corrections are satisfactory, but pre-session freeze acceptance remains undemonstrated and unsupported session-history claims remain.
**Verdict: rework.** Rework: the pre-session freeze confirmation stays pending until EVAL-7; remove the unsupported 'never governed a session' assertion and record the acceptance item as not yet demonstrated.

## Interim review (orchestrator seat, Fable, commit ef81abc, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated re-review is required before `done`.

Reviewed `ef81abc` (`eval-6: rework 2`) against `feat/h1-api-persistence` in worktree `.local/wt/EVAL-6`, working tree clean. Range inspected: `git diff feat/h1-api-persistence...HEAD` (4 files: `docs/work/probe-bundle/baseline-protocol.md` +422, `docs/work/reviews/EVAL-6.md` +75, `docs/work/PROGRESS.md` +7/-2, `docs/work/tasks.json` state only), `git log` of 5 commits. The reviewer did not author any of the change; the executor seat (DeepSeek V4.1 Flash) did. No file edited except this record.

### Checklist

| Checklist | Answer | Evidence |
|---|---|---|
| 1. Every acceptance item demonstrated | **no, one deferred** | Item 2 (metrics match blueprint section 9): met, see item 8. Item 1 (protocol fixed before any analyst session): the packet reports it **not yet demonstrated** (protocol line 297) and the head of the file (lines 3 to 6, 20 to 28) states the freeze is not established for session purposes until the two section 10 annex records exist. This is the honest statement the round-2 review asked for. Resolution lies with the owner or facilitator (an attributable pre-session confirmation), not with the executor seat; see deferral ruling below. |
| 2. Changes within allowed paths | **yes** | `plan.py scope EVAL-6 feat/h1-api-persistence` printed `OK: all changed files inside EVAL-6 allowed paths`. |
| 3. Frozen contracts, acceptance text and tests preserved | **yes** | Diff touches only the four allowed documentation/coordination files. Acceptance text in `tasks.json` unchanged (only `state` changed). No test file in the diff; the suite grew 251 to 261 by rebase onto `dc5ad00`, not by this branch. Working-paper section 5 definitions are referenced (protocol 3.2 names the eight working paper 5.2 questions and the h0.v1 `ReviewDecision` vocabulary) and not restated or altered. |
| 4. No unauthorized dependencies or external effects | **yes** | Documentation-only diff; protocol section 5 "Shared" row forbids model calls and external services during a pass. |
| 5. Truthful mode labels | **yes** | Protocol sections 4, 9 (execution-mode axis incl. `manual_session`), 10 and 12 (`synthetic_fixture` backend named as such); no live-run result claimed anywhere. |
| 6. Unknowns remain unknown | **yes** | `grep` over the protocol for session-history assertions returns only the rule definitions (lines 20, 240) and the two review-table rows quoting the removed assertions (337, 376). Sections 3.1 and 5 copy case facts from the case pack into the annex at session time and abort on any field that cannot be copied; no case value appears in the protocol. The round-1 "never governed a session" / "all three are fixed" sentences are gone from the file (lines 320 to 331 now say findings 1 and 2 fixed, finding 3 open, v1 superseded with no session-history claim). |
| 7. Complete verification and handoff record | **yes** | Round-2 packet section (lines 364 to 422) records interpreter (Python 3.14.4), four commands with results, the CORE-7 row-sync rationale and the failing-then-passing `test_progress_record_matches_task_states` run, unfinished items and the exact next action. Reproduced below with one minor count discrepancy. |
| 8. Consistent with governing documents | **yes** | Blueprint section 9 names exactly five measures: missed material issues, unsupported proposals, time to a defensible disposition, reviewer rework, traceability. Protocol section 9 rows M1 to M5 carry those five phrases verbatim with counting rules; M1 = rework category 1 only (line 205), M3 = the single section 7 rule (lines 157 to 170) with rework start/stop and `not_reached`; the four record axes (line 218 to 223) and "accepted is a review status, not a content kind" match the blueprint paragraph; forecast on a separate scorecard and carbon/outage/commercial behind later evidence (lines 40 to 42, 276 to 278); no-change-is-success (line 83). Nothing contradicts the blueprint, working paper or domain invariants found. |

### Verification executed (this seat, 2026-10-12, `/usr/bin/python3` = Python 3.14.4, tree at `ef81abc`)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/repo.py check` (brief verify command) | `Checked 252 Markdown files, 1105 local links, 8 skills; bootstrap 1293 words.` **PASS**, exit 0 |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates`, exit 0 |
| `/usr/bin/python3 scripts/plan.py scope EVAL-6 feat/h1-api-persistence` | `OK: all changed files inside EVAL-6 allowed paths`, exit 0 |
| `/usr/bin/python3 -m unittest discover -s tests` | **Ran 261 tests, OK** (0 failures, 0 errors, 0 skipped), 2.45 s, exit 0 |
| `sha256sum docs/work/probe-bundle/baseline-protocol.md` | `e82d0932…3d4c50`, identical to the v3 digest recorded in the PROGRESS round-2 row and to `git show ef81abc:` of the file |
| `git cat-file -t` on `154cddb`, `1e7e48c`, `a13cf7e`, `dc5ad00`, `ef2f936` | all resolve to commits; no stale reference |

### Findings

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| minor | docs/work/probe-bundle/baseline-protocol.md:394 | Reported link count differs from the reproduced count by one on the same commit; harmless, but a packet number that does not reproduce exactly weakens the "results actually run" record | packet recorded `1104 local links`; this seat reproduced `1105 local links` on a clean tree at `ef81abc`; PASS either way, cause undetermined (likely measured before the final PROGRESS row edit) | Not required for acceptance. If another round occurs, re-run the verify command last and paste the final number |
| minor | docs/work/PROGRESS.md:117, 119 | Append-only log rows from round 0 and round 1 still contain the withdrawn phrases "no session run" and "never governed a session" | Row 121 (round 2) explicitly withdraws them; the protocol file no longer asserts them | None; log history is append-only. Recorded here so the designated reviewer does not re-flag the historical rows as a live claim |

No blocking and no important finding against the work itself. Questions without evidence: none.

### Deferral ruling on acceptance item 1

The only open acceptance item is "protocol fixed before any analyst session". It is a chronology claim whose only admissible evidence under the protocol's own freeze rule is an attributable pre-session confirmation by the facilitator (countersigned by the owner when different), recorded in the section 10 annex. By design that record is created at `EVAL-7` before session 1; the executor seat can neither make nor infer it, and the round-2 rework correctly refused to manufacture one. The item can still be met **without changing the acceptance text or any frozen contract**: the owner (Sam) can record a dated one-line attestation now, which rules out `escalate`; and nothing further lies within the executor's authority, which rules out a third `rework` round on the same point. Section 11 makes any session without the confirmation `off_protocol`, so deferring the check costs nothing in rigor.

Ruling: EVAL-6 may be accepted with item 1 recorded as **deferred to owner attestation or the EVAL-7 annex**, explicitly listed as a deferred item (not an unresolved defect of the work) in the accept record. Recommended next action for the orchestrator: ask the owner for the dated attestation now, so the designated re-review sees item 1 met rather than deferred; failing that, the designated reviewer applies this same deferral.

**Interim verdict: accept.** Both metric findings are fixed to blueprint section 9, the freeze claim is stated honestly as not yet demonstrated, nothing undemonstrated is claimed, scope/check/suite pass, and acceptance item 1 is deferred to owner attestation or the EVAL-7 annex as a non-defect; designated independent re-review still required before `done`.

## Designated review (GPT Astra, independent, commit `d65ed25`, 2026-10-12)

> Independent review of `feat/h1-api-persistence...d65ed25d4c21`: inspected the diff and all six branch commits. Four files changed; working tree clean. No files edited.
> 
> | Checklist item | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | `baseline-protocol.md:297` explicitly reports pre-session freeze **not yet demonstrated**; both annex records are absent. Metrics at lines 205–223 match blueprint §9. |
> | 2. Changes within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EVAL-6 allowed paths`. |
> | 3. Frozen contracts, acceptance text and tests preserved | **Yes** | Four-file documentation diff; `tasks.json` changes only EVAL-6 state. No contracts or tests changed. |
> | 4. No unauthorized dependencies or external effects | **Yes** | Documentation-only change introduces no executable dependency or service call. Protocol line 123 prohibits calls during passes. |
> | 5. Truthful mode labels | **Yes** | Sections 4, 9 and 12 distinguish saved assistance, backend modes and fixture limitations; no live result claimed. |
> | 6. Unknowns remain unknown | **Yes** | Lines 20–28 preserve unknown session history; lines 61–67 require recorded case facts. PROGRESS’s round-2 entry withdraws earlier unsupported chronology claims. |
> | 7. Complete verification and handoff record | **Yes** | Lines 390–422 record interpreter, commands, results, outstanding confirmation and next action. Historical suite success was not reproduced in this sandbox. |
> | 8. Consistent with governing product documents and invariants | **Yes** | Sections 7–9 preserve the five blueprint metrics, separate record axes and justified no-change; section 12 excludes unsupported forecast/commercial claims. Acceptance-process conflict is identified below. |
> 
> Verification executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** — 252 Markdown files, 1106 local links, 8 skills |
> | `/usr/bin/python3 scripts/plan.py scope EVAL-6 feat/h1-api-persistence` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK** — 41 tasks, 7 gates |
> | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests` | **261 tests, 37 errors** — temporary-directory creation unavailable in read-only sandbox; not a demonstrated change regression |
> 
> | severity | path:line | failure mechanism | evidence | correction |
> |---|---|---|---|---|
> | important | `docs/work/probe-bundle/baseline-protocol.md:297` | Required chronology acceptance remains unproven. A future session guard cannot establish that the freeze preceded every session. | Acceptance row and lines 413–420 explicitly acknowledge missing freeze/confirmation records. | Obtain attributable confirmation and the version/digest/timestamp freeze record; independently check chronology before closing EVAL-6. Keep `in_progress` meanwhile. |
> | important | `docs/work/reviews/EVAL-6.md:120` | Interim ruling permits acceptance with a required item unfulfilled, bypassing the governing acceptance rule. | Lines 120–122 defer item 1 while recommending acceptance; review-and-feedback requires **all** acceptance items met. | Supersede the deferral ruling and interim acceptance; request review again after the missing evidence exists. |
> 
> **Verdict: rework** — the required pre-session freeze evidence is absent, and deferring it cannot satisfy acceptance.
**Verdict: rework.** Supersedes the interim accept above: pre-session freeze evidence is absent and deferral cannot satisfy acceptance. Owner action: one dated line attesting the protocol freeze (sha256 `e82d0932…`) before the manual-baseline session; then re-review.

## Designated review (GPT Astra, independent, commit `248d76c`, 2026-10-12)

> Independent review of `248d76c8c1eb` against `feat/h1-api-persistence`: inspected the requested diff and all eight branch commits. Four files changed; working tree clean. No files edited.
> 
> | Checklist item | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **Yes** | Owner’s dated attestation at `baseline-protocol.md:424–430` establishes the pre-session freeze. Its SHA-256 matches the complete protocol at parent commit `b5e5797`; those bytes remain unchanged. M1–M5 at lines 205–209 match blueprint §9. |
> | 2. Changes within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EVAL-6 allowed paths`. |
> | 3. Frozen contracts, acceptance text and tests preserved | **Yes** | Four-file documentation diff; `tasks.json` changes only EVAL-6’s state. No contracts or tests changed. |
> | 4. No unauthorized dependencies or external effects | **Yes** | No executable dependency, service integration or external effect introduced by the diff. |
> | 5. Truthful mode labels | **Yes** | Protocol §§4, 10 and 12 distinguish saved assistance, backend modes and synthetic limitations; no live result claimed. |
> | 6. Unknowns remain unknown | **Yes** | Case fields must come from records (§3.1); missing fields abort. Chronology now rests on an attributed owner statement rather than planning-state inference. |
> | 7. Verification and handoff recorded | **Yes** | Lines 390–422 record interpreter, commands, results and outstanding session preparation; latest PROGRESS entry requests re-review. Stale acceptance wording is noted below. |
> | 8. Consistent with governing documents and invariants | **Yes** | §§7–9 preserve the five blueprint metrics, separate record axes and justified no-change; §12 excludes unsupported forecast and commercial claims. |
> 
> Checks executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** — 252 Markdown files, 1107 local links, 8 skills |
> | `/usr/bin/python3 scripts/plan.py scope EVAL-6 feat/h1-api-persistence` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK** — 41 tasks, 7 gates |
> | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests` | **261 tests, 37 errors** from unavailable writable temporary directories; passing suite not independently reproduced |
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/probe-bundle/baseline-protocol.md:5` | Current status and handoff obscure the newly supplied freeze evidence. | Lines 5–6, 297 and 413–422 still describe confirmation as absent; lines 424–430 now contain the owner attestation. | Add an explicit superseding status note referencing the attested parent version and digest, while preserving its bytes and retaining EVAL-7’s session-annex requirements. |
> 
> The owner attestation demonstrates EVAL-6’s protocol-freeze criterion. It does not demonstrate analyst-session execution or waive the facilitator confirmation, key freeze and other pre-session checks required for EVAL-7.
> 
> **Verdict: accept** — both task acceptance items are demonstrated, with only a minor documentation consistency finding remaining.
**Verdict: accept.** Owner freeze attestation recorded.
