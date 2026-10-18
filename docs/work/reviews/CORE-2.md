# Review: CORE-2

Reviewed commit `8b9d8c3` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of `8b9d8c34fb15`, against `feat/h1-api-persistence`, covering commits `f25ce3c` and `8b9d8c3`. Working tree clean; no files edited.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | Focused tests demonstrate invalid-response rejection, replay/conflict, pre-call guards and revoked-source denial. Emulator restart/read-back was **not run during this review**; the packet’s reported pass remains independently unverified. |
> | 2. Changes confined to allowed paths | **Yes** | Requested `plan.py scope CORE-2 feat/h1-api-persistence` printed `OK`. |
> | 3. Frozen contracts and acceptance unchanged; tests not weakened/skipped | **Yes** | Diff adds the artifact kind without changing existing kinds; frozen intent matches `7bf1c3d`; existing tests retain their assertions. Implementation fidelity issues appear below. |
> | 4. No unauthorized dependencies or external effects | **Yes** | New service uses existing modules and injected backends; integration tests target existing loopback emulators. |
> | 5. Truthful mode labels | **Yes** | Fixture declares `synthetic_fixture` and `fixture_supplied`; replay returns the saved artifact without claiming another inference. Focused test passed. |
> | 6. No invented facts, receipts or numbers | **Yes** | Tests use labelled synthetic fixtures; generated artifacts retain validated backend answers and computed composition/receipt values. |
> | 7. Packet records interpreter, verification, unfinished work and next action | **Yes** | `implementation.md:738–806` records these, including deferred lineage resolution and independent review next. |
> | 8. Consistent with governing intent and domain invariants | **No** | Required lineage reuse is unreachable through the service; backend exceptions can expose arbitrary details. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/judgment/systemone.py:217` | Backend-raised `JudgmentUnavailable` bypasses sanitization; its unrestricted code reaches the API response. | Executed a synthetic backend raising `JudgmentUnavailable('synthetic-private-error-detail')`; that exact code propagated. API handler at `src/api/__init__.py:139` returns `exc.code`. Frozen intent requires backend exceptions to map to `MODEL_UNAVAILABLE` without leaking content. | Sanitize exceptions raised by `decide`, including `JudgmentUnavailable`; test arbitrary exception content and no writes. |
> | important | `src/judgment/systemone.py:222` | Composition never receives a saved lineage label, so qualifying repeated evidence always produces `LINEAGE_NO_PRIOR`, even when a suitable prior bundle exists. | Call omits `prior_label`; `bundle.py:419–424` consequently always takes the missing-prior branch. Packet explicitly acknowledges the deferral. Frozen intent requires reuse of an earlier source’s saved label for the same assumption. | Resolve an authorized, qualifying prior bundle and pass its label; test existing-prior, absent-prior and inaccessible-prior cases. |
> 
> Verification on Python 3.14.4:
> 
> - Requested verify command attempted: **262 tests, 30 errors** caused by unavailable writable temporary directories. Because of `&&`, `bash scripts/h1/test.sh` **was not run**.
> - Focused probe suite: **33 tests passed**.
> - Scope: **OK**. Plan check: **OK, 41 tasks / 7 gates**. Repository check: **PASS**.
> - Emulator restart acceptance remains unverified here; sandbox failures are not attributed to the change.
> 
> **Verdict: rework** — fix the exception disclosure and missing lineage reuse, then demonstrate the complete verification command and emulator restart acceptance.
## Outcome and next action

**Verdict: rework.**
Executor fixes both important findings (sanitize backend `JudgmentUnavailable` to `MODEL_UNAVAILABLE`; pass the saved prior lineage label into composition) and reruns the verify command including the emulator suite; then re-review.

## Review round 2026-10-11 evening (commit `e732d2b`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `e732d2b3f359` against `feat/h1-api-persistence`, including all five branch commits and the clean working tree. No files edited.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | Focused tests demonstrate invalid-response rejection, replay/conflict, pre-call guards and direct-source revocation. Emulator restart/read-back could not run here. Inherited-source revocation fails the reproduction below. |
> | 2. All changes within allowed paths | **Yes** | `/usr/bin/python3 scripts/plan.py scope CORE-2 feat/h1-api-persistence` printed `OK`. |
> | 3. Frozen contracts/acceptance unchanged; no tests weakened or skipped | **Yes** | Frozen intent matches `7bf1c3d`; existing record kinds and judgment contract remain unchanged; existing test assertions are preserved. Implementation fidelity findings follow. |
> | 4. No unauthorized dependencies or external effects | **Yes** | Uses existing modules, injected backends and existing local emulator infrastructure; no new runtime dependency or live backend invocation. |
> | 5. Truthful mode labels | **Yes** | Fixture declares `synthetic_fixture` and `fixture_supplied`; passing replay test confirms no additional backend call. |
> | 6. Unknowns preserved; no invented facts, receipts or numbers | **Yes** | Fixtures are explicitly synthetic; answers are validated and composition/receipt values computed. |
> | 7. Packet records interpreter, commands, results, unfinished work and next action | **Yes** | `implementation.md` records Python 3.14.4, verification results, limitations and independent re-review as the next action. Reported emulator passes remain independently unverified here. |
> | 8. Consistent with governing contracts and domain invariants | **No** | Lineage reuse does not preserve information cutoffs or transitive source authorization, as demonstrated below. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/review/repository.py:564` | Any shared lineage qualifies; selecting the newest artifact permits a later-cutoff judgment to influence an earlier-cutoff task. | Executed an in-memory reproduction using existing fixtures: saved a `supports` bundle at cutoff `2026-10-06T00:00:00Z`, then generated for cutoff `2026-10-05T02:00:00Z` with Q5=yes. Result was `supports`, rule `lineage_reuse`, falsely describing an “earlier source label.” | Require a demonstrably qualifying earlier source and cutoff-compatible prior evidence. Add a reverse-cutoff regression proving later evidence cannot supply the label. |
> | important | `src/review/repository.py:569` | Returning only the inherited label drops the prior artifact’s source dependencies. Subsequent reads traverse the current task but cannot enforce authorization for evidence supporting the inherited label. | Executed the existing restricted-source lineage fixture, then read with restricted access removed: `probe-prior` returned `ACCESS_DENIED`, while derived `probe-c` remained readable with `supports`. | Preserve and enforce the inherited artifact/source dependency during commit and subsequent reads. Add revocation coverage for inherited evidence; return to intent if the frozen payload contract prevents the required provenance. |
> 
> Verification on Python 3.14.4:
> 
> - Requested verify chain attempted: **266 tests, 30 errors** from unavailable writable temporary directories; `&&` prevented its emulator step.
> - Separately attempted `bash scripts/h1/test.sh`: emulator startup failed with sandbox `listen EPERM`; **integration tests were not run**.
> - `/usr/bin/python3 -m unittest tests.test_probe_bundle -v`: **37 passed**.
> - Scope: **OK**. Plan check: **OK, 41 tasks / 7 gates**. Repository check: **PASS**.
> - Both additional in-memory reproductions above executed successfully. Sandbox failures are not attributed to this change.
> 
> **Verdict: rework** — correct lineage cutoff selection and inherited-source authorization, then demonstrate the complete verification command including emulator restart/read-back.
**Verdict: rework.** Executor rework next session: restrict lineage reuse to prior bundles at or before the current cutoff, and carry the prior artifact's source dependencies so authorization still applies.

## Interim review (orchestrator seat, Fable, commit 7575cbd, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated
re-review is required before `done`. Reviewer did not author the change (executor seat, DeepSeek).
Reviewed `git diff feat/h1-api-persistence...7575cbd` (10 files, 8 commits) and the packet
sections "S2 rework 2" and "S2 rework 2 completion". Earlier judgments in this record were
treated as prior findings to re-test, not as evidence; every result below was run here, in the
`.local/wt/CORE-2` worktree, interpreter `/usr/bin/python3` (Python 3.14.4). No file edited
other than this section.

| Checklist | Answer | Evidence |
|---|---|---|
| 1. Every acceptance item met by a check actually run | **Yes** | Offline: `test_invalid_responses_write_nothing`, replay/conflict, guards-before-call, revoked-source tests all in the 278 that passed. Emulator: all seven `ProbeBundleAPI` cases ran `ok`, including `test_bundle_saved_replayed_read_back_after_restart_and_projected` (restart read-back, the fifth acceptance item) and `test_inherited_source_dependency_denies_read_after_revocation`. "Review bundle includes probe artifacts": `workspace()` is the only review-bundle projection (judgments live there too) and now carries `bundles`. |
| 2. No file outside allowed paths | **Yes** | `plan.py scope CORE-2 feat/h1-api-persistence` → `OK: all changed files inside CORE-2 allowed paths`. Task commit `23abac2` also set the CORE-7 PROGRESS row to `done` (inside allowed paths, recorded in the packet); integration commit `c5caaa2` carries the same value, so the reviewed diff has no CORE-7 hunk and nothing collides at merge. |
| 3. No frozen contract, acceptance text or test weakened | **Yes** | `ProbeBundleArtifact` payload key set and metadata key set in `records.py:183-184,216-217` equal the intent's sets exactly; existing kinds, `JudgmentArtifact`, `PROMPT_VERSION` untouched (diff). `git diff b20b0f3..HEAD -- tests/` removes no line; `a6ab307..HEAD` removes only rework-1's `bundle_lineage_label` cases and the old-direction integration case, each replaced by a stricter assertion (adds `reference(prior)` / `lineage_ref`). |
| 4. No new dependency, service, credential, network or model call | **Yes** | `systemone.py` imports stdlib + repo modules; `FixtureSystemOne` holds a dict; API injects `SystemOneService()` with `backend=None` → `MODEL_DISABLED`. |
| 5. Mode labels truthful | **Yes** | `execution_mode='synthetic_fixture'`, `probabilities='fixture_supplied'` on the fixture; an undeclared backend is recorded `unreported`, not described; record requires `synthetic is True`, `review_state='proposed'`. |
| 6. Unknowns stay unknown | **Yes** | Composition reuses CORE-1 `compose` (modal top option per question, `_modal`, ties → `cannot_tell`/`not_stated`/`NOUL_TIE`); no mean anywhere in the path. Absent prior → `LINEAGE_NO_PRIOR` + escalation; refused render returned as a result, nothing written. |
| 7. Packet records interpreter, commands, results, unfinished, next action | **Yes** | `implementation.md:971-1203`: Python 3.14.4, chain results, storage allow-list gap, `work.json` phase, UI-1, next action. |
| 8. Nothing contradicts blueprint/paper/invariants | **Yes, with minors** | Cutoff rule now enforces "no later evidence decides an earlier task"; inherited dependency is walked by `_access_record` (generic reference walk, `repository.py:95-118`). Minors below. |

### Verification run here

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 278 tests in 2.010s` — `OK` |
| `bash scripts/h1/test.sh` (emulators via `.local/h1-*` links) | `Ran 66 tests in 31.313s` — `OK`, `Script exited successfully (code 0)`; 7/7 `test_probe_bundle_api` cases `ok` |
| `plan.py scope CORE-2 feat/h1-api-persistence` | `OK` |
| `plan.py check` | `OK: 41 tasks, 7 gates` |
| `repo.py check` | `Checked 251 Markdown files, 1105 local links, 8 skills; bootstrap 1293 words.` `PASS` |

### Adversarial re-tests of the two prior findings (own script, in-memory, read-only)

- **Finding 1 (later-cutoff prior).** A1: `supports` bundle on a `2026-10-06` task, then the `2026-10-05T02:00:00Z` task with Q5=0.8 → `bundle_lineage_prior` returns `None`; composed `('insufficient', 'lineage_reuse', 'LINEAGE_NO_PRIOR', lineage_ref=None)`. **Fixed by construction** (`prior_cutoff > cutoff: continue`, `repository.py:570-571`).
- A2 (prior on an *earlier*-cutoff task but **recorded after** the current cutoff, clock `2026-10-09`) qualifies. Ruling: by design — the frozen intent bounds visibility by `information_cutoff` through `compile_task`; `recorded_at` is generation wall-clock and carries no evidence. Not a finding.
- A3 (same compiled task recompiled: same `record_id`, new `revision_id`) → its own earlier bundle qualifies as the prior (`{'label': 'supports', ...}`). The "different task" exclusion compares `reference()`, not logical identity. Minor finding below.
- A4 (equal cutoff, genuinely different task) could not be built from the one-passage seed; inconclusive, not asserted.
- **Finding 2 (inherited source policy).** B1: prior rests on a `synthetic-restricted` source; derived bundle (full actor) records `lineage_ref == reference(prior)`; narrow actor: read prior `ACCESS_DENIED`, read derived `ACCESS_DENIED`, workspace `bundles == []`, and a third later task sees `None` (chain through the derived artifact also skipped); full actor sees the derived bundle as prior. **Fixed by construction.**
- C: hand-built records — reuse without `lineage_ref` → `INVALID_RECORD`; `lineage_ref` of kind `CompiledTask` → `INVALID_RECORD`; `lineage_ref` on an abstention → `INVALID_RECORD`; arbitrary extra key in `composed` → **accepted** (minor below). `register` refuses non-evidence kinds, so no hand-built bundle enters a store anyway.

### Rulings on the two flagged readings

1. **`lineage_ref` inside `composed`.** Accepted. The payload and metadata key sets are frozen and matched exactly; `composed` is the composition's own result and not enumerated by the intent; `output_digest = digest(composed)` is computed after the key is added, so the digest covers the provenance; `_access_record` walks it. A payload-level key would be an intent revision, not a code change; the designated reviewer may still prefer that route.
2. **Greatest-at-or-before-cutoff, equal cutoffs included, ties by `recorded_at` then `record_id`.** Accepted. A1 and `test_the_latest_earlier_cutoff_wins_and_later_evidence_is_excluded` (four cutoffs, most-recently-recorded later bundle excluded) confirm it; the rule is deterministic. The one gap is A3 (self-reuse via a revision), rated minor.

### Findings

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| minor | `src/review/repository.py:565` | "Different task" is tested by full `reference()`, so a recompile of identical content (same `record_id`, new revision) qualifies as its own prior and the lineage row reuses the task's own earlier label: circular, no earlier *source*. Same cutoff and sources, so no leak or authorization drop. | A3 above: `t1.record_id == t2.record_id`, `bundle_lineage_prior(t2)` returned the `t1` bundle. | Compare `prior_task['record_id'] != task['record_id']` (logical identity, as `_logical` does); add a recompile regression. |
| minor | `src/review/records.py:198-211` | `composed` has no closed key set and `fired_rule` is not checked against `RULES`; an unknown or non-string rule silently reads as "not reused", and arbitrary keys validate and enter `output_digest`. | C: `composed['invented_note']='anything'` → record accepted. | Require `set(composed) <= {'label','fired_rule','reason','atomic','escalation','thresholds','lineage_ref'}` and `fired_rule.split(':')[0] in RULES`; inside allowed paths. |
| minor | `src/judgment/systemone.py:228-243` | `bundle_lineage_prior` and `save_bundle` run in separate `execute` transactions; commit rechecks task access and heads but not that the chosen `lineage_ref` is still readable by the actor. Read-time enforcement denies the derived read, so no disclosure. | Code reading; not reproduced. Question for the designated reviewer, not a defect claim. | Optionally re-resolve or re-check the prior's access inside `save_bundle`. |

No blocking or important findings. Unfinished items the packet names (storage allow-list,
`work.json` phase, UI-1) are outside this task's paths and correctly left to their owners.

**Interim verdict: accept.** Both prior findings are fixed by construction and re-demonstrated adversarially here, all five acceptance items ran green including the emulator restart read-back, and the three minors need no rework before the designated re-review that must precede `done`.

## Designated review 2 (GPT Astra, independent, commit `ac0c43f`, 2026-10-12)

> Reviewed independently: `feat/h1-api-persistence...ac0c43f`, including all nine commits in the requested log. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** All 39 probe-bundle tests passed, demonstrating invalid-response rejection, replay/conflict, pre-call guards, and revoked-source reads. Emulator restart read-back was **not independently run**; previous packet results are reported evidence only. |
> | 2 | Changes stay within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORE-2 feat/h1-api-persistence` printed `OK: all changed files inside CORE-2 allowed paths`. |
> | 3 | Frozen contracts, acceptance text, and tests preserved | **Yes.** Diff preserves existing record contracts and acceptance text; the new artifact matches the frozen payload/metadata keys. Existing tests were not weakened or skipped. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Implementation uses existing modules and standard-library facilities; the fixture backend has no transport, and the API defaults to a disabled backend. |
> | 5 | Truthful mode labels | **Yes.** Fixture declares `synthetic_fixture` and `fixture_supplied`; records remain `proposed` and synthetic. |
> | 6 | Unknowns remain unknown | **Yes.** Missing/inaccessible lineage priors produce `LINEAGE_NO_PRIOR`; missing probability provenance remains `unreported`. |
> | 7 | Complete implementation packet | **Yes.** Packet records interpreter, commands, results, unfinished integration work, and the next review action. Historical results are distinct from this review’s execution. |
> | 8 | Domain invariants preserved | **No.** Revocation during generation can disclose an inherited result through the creation response, as reproduced below. |
> 
> Verification:
> 
> - Requested verify chain attempted: **278 tests, 37 errors**, including inability to create temporary directories in the read-only sandbox. Because the first command failed, `bash scripts/h1/test.sh` **was not run**.
> - `/usr/bin/python3 -m unittest tests.test_probe_bundle -q`: **39 passed**.
> - `plan.py scope`, `plan.py check`, and `repo.py check`: **passed**.
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/review/repository.py:592` | `save_bundle` rechecks the current task’s access but not the inherited `lineage_ref`. If its restricted source becomes inaccessible during the backend call, the artifact is still written and returned directly to the caller. Subsequent read checks cannot prevent disclosure through that creation response. | Read-only, in-memory reproduction using `LineagePriorTests`’ restricted-source fixture supplied the narrowed actor at save time: **`SAVE RETURNED: supports`**, followed by **`READ WITH SAME COMMIT ACTOR: ACCESS_DENIED`**. `PersistentRepository.execute` supplies refreshed membership at this same boundary. | Check the completed artifact’s transitive access with the fresh actor before `_write`, inside the commit operation. Add a regression revoking an inherited-only source during generation and assert denial, no artifact write, and no inherited result returned. |
> 
> **Verdict: rework.** The reproduced authorization gap is an unresolved important finding, and emulator restart acceptance still needs verification in a permitted environment.
**Verdict: rework.** Supersedes the interim accept above. Rework scope: (1) `save_bundle` must re-check access to the inherited `lineage_ref` with the actor's membership at save time and refuse (no artifact written, no disclosure in the creation response) when the restricted source is no longer accessible — add the reviewer's reproduction as a test; (2) record the emulator restart read-back run (`bash scripts/h1/test.sh`, 66 OK on this commit per the interim review) in the packet. Other findings per the table.

## Designated review 2 (GPT Astra, independent, commit `16c1e8d`, 2026-10-12)

> Independent review of `16c1e8d35043` against `feat/h1-api-persistence`, including the requested diff and commit log. No files edited.
> 
> Verification: Python 3.14.4; **280 offline tests passed**. The verify chain’s emulator runner failed at startup with sandbox `listen EPERM`; integration tests did not run in this review. The retained `.local/core2-rework3-postcommit.log` demonstrates **67 passing emulator tests**, including restart read-back and save-time revocation. Its recorded commit, `acb0cf2`, has identical relevant backend and integration-test files to HEAD.
> 
> Scope printed **OK**; `plan.py check` and `repo.py check` passed.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes**, combining this run and inspected prior execution evidence. `tests/test_probe_bundle.py:775–908` covers invalid responses/no writes, replay/conflict, guards and revoked-source reads. The retained emulator log explicitly passes `test_bundle_saved_replayed_read_back_after_restart_and_projected`. |
> | 2 | Changes within allowed paths | **Yes** — requested base-relative scope command printed `OK: all changed files inside CORE-2 allowed paths`. |
> | 3 | Frozen contracts preserved; no weakened/skipped tests | **Yes** — additive record/API changes; frozen intent and existing judgment contract unchanged. Existing tests retained. |
> | 4 | No unauthorized dependency or external effect | **Yes** — injected backend and fixture only; no added runtime dependency, credential, transport or live call. |
> | 5 | Truthful mode labels | **Yes** — fixture uses `synthetic_fixture` and `fixture_supplied`; replay returns the saved artifact without another backend call. |
> | 6 | Unknowns remain unknown | **Yes** — inaccessible/missing lineage priors abstain; unspecified probability provenance is `unreported`; synthetic answers are explicitly labelled. |
> | 7 | Complete execution packet | **Yes** — packet records interpreters, commands, results, prior findings, fixes and the next review action. Historical emulator evidence was inspected, not merely assumed. |
> | 8 | Consistent with product direction and domain invariants | **No** — the required analyst review view cannot consume the new workspace projection, as detailed below. |
> 
> Findings:
> 
> **important | `src/review/repository.py:637` | Saved probe artifacts disappear from the analyst review view after refresh |** The repository returns `bundles`, while `src/workspace/app.js:190` reads `state.probe_bundles`. The request handler at line 266 discards the POST response and refreshes that projection. An executed in-memory reproduction saved one artifact and returned `bundles_count: 1`, but `ui_probe_bundles_count: 0`; the view therefore displays “No probe bundle is saved.” **Correction:** expose the key consumed by the existing view from the allowed repository path and add a meaningful producer/consumer compatibility check. **Disposition:** unresolved.
> 
> **Verdict: rework.** The backend acceptance checks have evidence, but the workspace response mismatch prevents saved probe artifacts from appearing in the required review view.
**Verdict: rework.** the workspace response shape does not match what the review view expects, so saved probe artifacts do not appear in the required view. Address every blocking/important row above; dispose of minors explicitly.

## Designated review 3 (GPT Astra, independent, commit `41fbd2f`, 2026-10-12)

> Reviewed independently at `41fbd2fd129e`, using the requested diff and commit log against `feat/h1-api-persistence`. No files edited.
> 
> Verification: Python 3.14.4 ran **282 offline tests successfully**. The verify chain then exited 1: sandbox `EPERM` prevented emulator port binding, so **integration tests did not run**. Scope printed **OK**; `plan.py check` and `repo.py check` passed.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Offline tests demonstrate invalid-response/no-write cases, replay/conflict, blocked/stale/other-actor guards, and revoked-source denial. Emulator restart read-back remains unverified in this review. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORE-2 allowed paths`. |
> | 3 | Frozen contracts and tests preserved | **Yes.** Existing record kinds remain unchanged; additions preserve frozen payload/metadata keys. Acceptance text is unchanged; existing tests were not weakened or skipped. |
> | 4 | No unauthorized dependency or external effect | **Yes.** New backend is an injected fixture; no runtime dependency, credential, live transport or cloud operation was added. |
> | 5 | Truthful mode labels | **Yes.** Saved fixture artifacts assert `synthetic_fixture`, `fixture_supplied`, and `synthetic=True`; replay returns the saved artifact without another call. |
> | 6 | Unknowns preserved | **Yes.** Missing/inaccessible/future lineage priors abstain; backend failures are sanitized. Tests use explicitly fictional fixtures. |
> | 7 | Complete implementation packet | **Yes.** Packet records interpreter, commands, results, remaining review and next action. Its cited `1680a69` has identical `src/` and `tests/` content to HEAD, though it is not the reviewed commit. |
> | 8 | Consistent with domain invariants | **Yes.** Proposals remain proposed; task guards precede backend execution, commit rechecks access, and inherited source references enforce transitive revocation. |
> 
> Finding:
> 
> **important | tests/integration/test_probe_bundle_api.py:80 | Required persistence/restart acceptance remains unverified | The restart test exists, but emulator startup failed with sandbox `EPERM`; the packet reports an earlier passing run, which this review could not independently reproduce | Run the full verify chain in an environment permitting loopback emulator ports and attach results tied to the reviewed commit.** Disposition: unresolved verification gap, not a demonstrated code defect.
> 
> **Verdict: rework — acceptance requires demonstrated emulator read-back after restart, and that verification remains outstanding.**
**Verdict: rework.** Demonstrate the emulator read-back after a restart (the verify command's bash scripts/h1/test.sh) and record the numbers in the packet. Address every blocking/important row above; dispose of minors explicitly.

## Interim re-review of rework 5 (orchestrator seat, Fable, commit e8e8fb6, 2026-10-12)

Interim re-review, not the designated independent reviewer (GPT Astra, no credits); the
designated review supersedes this one and this section does not set the task `done`. The
reviewer did not author the change (executor seat, DeepSeek). Everything below was run here, in
the `.local/wt/CORE-2` worktree on a clean tree at `e8e8fb6`, interpreter `/usr/bin/python3`
(Python 3.14.4); the emulator half ran `.local/h1-venv/bin/python` inside `scripts/h1/test.sh`
against the two loopback emulators only. Packet sections read: "S2 rework 4", "S2 rework 5",
"S2 rework 5 completion" and "Duplicate-launch verification". No file edited other than this
section.

### Commands run

| Command | Result |
|---|---|
| `git diff 41fbd2f HEAD --stat` | 3 files, all docs (`PROGRESS.md`, `probe-bundle/implementation.md`, `reviews/CORE-2.md`); `git diff --quiet 41fbd2f HEAD -- src tests` exits 0, so the code and tests here are byte-identical to the commit review 3 examined |
| `git diff feat/h1-api-persistence...HEAD --stat` | 10 files; code: `src/api/__init__.py`, `src/judgment/systemone.py` (new), `src/review/records.py`, `src/review/repository.py`, `tests/test_probe_bundle.py`, `tests/integration/test_probe_bundle_api.py` |
| `/usr/bin/python3 -m unittest discover -s tests -v && bash scripts/h1/test.sh` (one chain, exit 0) | step 1: `Ran 282 tests in 4.123s` — `OK`; step 2: `Ran 67 tests in 49.866s` — `OK`, `Script exited successfully (code 0)` |
| `ProbeBundleAPI` cases in the emulator half | 8 of 8 `ok`, including `test_bundle_saved_replayed_read_back_after_restart_and_projected`, `test_revocation_during_generation_denies_the_inherited_save`, `test_inherited_source_dependency_denies_read_after_revocation` |
| `tests.test_probe_bundle` cases within the 282 | 43 `ok` |
| `/usr/bin/python3 scripts/plan.py scope CORE-2 feat/h1-api-persistence` | `OK: all changed files inside CORE-2 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 260 Markdown files, 1223 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `git diff feat/h1-api-persistence...HEAD -- tests/ \| grep '^-[^-]'` | 5 removed lines, all docstring text and two replaced imports in `tests/test_probe_bundle.py`; no assertion removed, no test skipped |

### The emulator evidence review 3 asked for

Exact command: `bash scripts/h1/test.sh`, run as the second half of the verify chain above.
The script exports `FIRESTORE_EMULATOR_HOST=127.0.0.1:18080` and
`FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:19099` and runs `firebase emulators:exec --only auth,firestore`;
this run's `.local/h1-run/firestore-debug.log` opens `Oct 12, 2026 11:23:14 AM`, records
`Started WebSocket server on ws://127.0.0.1:9150` and `API endpoint: http://127.0.0.1:18080`, so
the ports the reviewer's sandbox refused (`listen EPERM`) bound here. That log also holds six
`WARNING: Operation failed: Transaction lock timeout.` lines, recorded and not attributed to a
cause; no test failed and the suite reports 67 passed.

Is a saved bundle read back after the service restarts? Yes. The proving test is
`tests/integration/test_probe_bundle_api.py:80`
`ProbeBundleAPI.test_bundle_saved_replayed_read_back_after_restart_and_projected`, `ok` in this
run. It saves a bundle through `POST /probe-bundles` on one app, then builds a second app
(`create_app(self.f.connection(), ...)`, a new connection to the same Firestore emulator store)
with a fixture backend holding no answers; on that restarted app `POST /read` returns the
identical record (`200`), the replay `POST /probe-bundles` with the same key returns the identical
record with `fresh_backend.requests == []`, and `GET /workspace` projects it under
`probe_bundles`. What restarts is the API service and its repository connection; the emulator
process itself is not restarted, which is the construction all three designated reviews read and
accepted as the restart case.

### Checklist

| # | Item | Answer | Evidence |
|---|---|---|---|
| 1 | Every acceptance item met by a check actually run | **Yes** | Items 1-4: offline `ProbeBundleServiceTests` (`test_invalid_responses_write_nothing` with the four invalid shapes, `..._replays_without_a_call`, `..._conflicts_without_a_second_call`, `test_blocked_stale_and_other_actor_tasks_never_call_the_backend`, `test_a_revoked_cited_source_denies_read_of_the_saved_bundle`) plus their emulator twins, all `ok`. Item 5: the restart case above, `ok` in this run. |
| 2 | No file outside allowed paths | **Yes** | scope `OK` |
| 3 | No frozen contract, acceptance text or test weakened | **Yes** | `ProbeBundleArtifact` payload and metadata key sets match the intent; existing kinds and `JudgmentArtifact` untouched; the only removed test lines are docstring and imports |
| 4 | No new dependency, service, credential, network or model call | **Yes** | `systemone.py` imports stdlib and repo modules; API default `SystemOneService()` has `backend=None` → `MODEL_DISABLED` |
| 5 | Mode labels truthful | **Yes** | `synthetic_fixture` / `fixture_supplied` on the fixture, `unreported` when a backend declares nothing, record requires `synthetic is True` and `review_state == 'proposed'` |
| 6 | Unknowns stay unknown | **Yes** | absent, inaccessible, later-cutoff and self-revision priors all give `LINEAGE_NO_PRIOR`; refusals are results or errors, never writes |
| 7 | Packet complete | **Yes** | rework 5 and the two duplicate-launch sections record interpreter, commands, numbers, logs, warnings, minors disposed, next action |
| 8 | Nothing contradicts blueprint or invariants | **Yes** | see dispositions below |

### Disposition of every prior review item

| Raised in | Item | Disposition | Evidence (all `ok` in this run) |
|---|---|---|---|
| Review 1 (`8b9d8c3`) | backend-raised `JudgmentUnavailable` leaks its code | **Closed** | `systemone.py` wraps `decide` in `except Exception: raise JudgmentUnavailable() from None`; `test_a_backend_judgment_unavailable_is_sanitized_to_model_unavailable` (three codes), emulator `test_backend_raised_judgment_unavailable_is_sanitized` (`503 MODEL_UNAVAILABLE`) |
| Review 1 | lineage prior never passed to `compose` | **Closed** | `bundle_lineage_prior` → `compose(..., prior_label=...)`; `test_a_repeated_source_reuses_the_earlier_bundle_label`, emulator `test_a_repeated_source_reuses_the_saved_label_through_the_api` |
| Review 2 round 1 (`e732d2b`) | later-cutoff prior decides an earlier task | **Closed** | `repository.py` `if prior_cutoff > cutoff: continue`; `test_a_later_cutoff_prior_cannot_supply_the_label`, `test_the_latest_earlier_cutoff_wins_and_later_evidence_is_excluded` |
| Review 2 round 1 | inherited source dependency dropped | **Closed** | `composed['lineage_ref']` recorded on reuse, walked by `_access_record`; record validation requires the ref iff reused; `test_an_inaccessible_prior_is_absent_not_an_error`, emulator `test_inherited_source_dependency_denies_read_after_revocation` (prior and derived both `404`, task and public records `200`) |
| Designated review 2 (`ac0c43f`) | save-time access recheck of `lineage_ref` (revoked between resolve and save) | **Closed** | `save_bundle` re-runs `bundle_input` and `_access_record(actor, case, record)` before `_write`, under the fresh actor `PersistentRepository.execute` supplies; `test_a_revocation_during_generation_denies_the_inherited_save` (`ACCESS_DENIED`, no `supports` in the message, prior alone projected), emulator `test_revocation_during_generation_denies_the_inherited_save` (`404 NOT_FOUND`, backend ran once, nothing written) |
| Designated review 2 (`16c1e8d`) | workspace key `bundles` vs `state.probe_bundles` | **Closed** | `workspace()` returns `probe_bundles`; `ProbeBundleViewContractTests.test_every_key_the_view_reads_is_one_the_workspace_response_carries` reads `src/workspace/app.js` as source and asserts consumed ⊆ carried, `test_a_saved_bundle_is_reachable_through_the_key_the_view_reads` asserts the saved record sits under exactly that key; both emulator projection assertions use `probe_bundles` |
| Designated review 3 (`41fbd2f`) | emulator read-back after restart unverified | **Closed** | this run, section above |
| Interim review minors (`7575cbd`) | recompile is its own prior; `composed` open key set and unchecked `fired_rule`; save-time prior access | **Closed** | `_logical` comparison + `test_a_recompile_of_the_same_task_is_not_its_own_prior`; closed key set and `rule in RULES` at `records.py` + invented-key and invented-rule rejections in `test_record_validation_rejects_foreign_payloads`; the revocation-during-generation pair |

### New look: time leakage, writes outside the namespace, refusal paths, weakened tests

- Time: `bundle_lineage_prior` filters by `information_cutoff` and selects the greatest
  at-or-before cutoff; `recorded_at` is wall-clock, ruled by design in the interim review. No
  path reads the clock on a replay (`no_clock` test). `save_bundle` requires
  `recorded_at >= task.recorded_at`.
- Writes: the only write is `save_bundle` → `_write([record])` with the ident
  `probe:<digest(actor,key)>` in the actor's tenant and case; every refusal path (invalid
  response, backend failure, disabled, busy, render refusal, blocked/stale/other-actor,
  conflict, save-time denial) is asserted to leave `probe_bundles == []` or the prior alone.
- Refusals: the three repository methods are not on `PersistentRepository.__getattr__`'s
  allow-list (`src/review/storage.py`, outside allowed paths), so `_repository_call` falls
  through to `execute`; each call is one transaction and the backend call stays outside it.
  Correct, and recorded in the packet as a gap for the storage owner.
- Tests: no assertion removed vs base; rework 5 changed no code or test.

### Findings

| severity | path:line | what | why |
|---|---|---|---|
| minor (question) | `src/review/repository.py:570` | A qualifying prior is matched on `assumption_ref['record_id']` only, so a bundle composed against an earlier revision of the same assumption can supply the label to a task on a later revision. | The intent (`intent.md:77`, `:98`) says "same assumption" / "share `assumption_id`", so this matches the contract and the cutoff rule still holds; left for the designated reviewer to confirm the reading, not a defect claim. |

No blocking or important findings.

**Verdict: accept.** Every item from designated reviews 1 to 3 and the interim minors is closed by code and by a test that ran green here, and the emulator half of the verify command ran in this seat on code byte-identical to the reviewed commit, with the restart read-back test passing; the designated re-review remains required before `done`.

## Designated review (GPT Sol, independent, commit `786ab47`, 2026-10-13)


## Designated review (GPT Sol, independent, commit `786ab47`, 2026-10-13)

> Independent review of `786ab470a68f6028094f2b38ac3adc860e4f4dd3`, using the requested three-dot diff and commit log. No files edited.
> 
> Verification:
> - Requested verify chain attempted: **282 offline tests passed** in 2.019s; emulator startup failed with loopback `EPERM`, so integration tests did **not run in this attempt**.
> - Scope: **OK**, all changes inside CORE-2 allowed paths.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Inspected recorded emulator log (`.local/core2-verify64/chain2-h1.log:67`, ignored, in the CORE-2 worktree): all eight ProbeBundleAPI cases passed, including restart read-back; **67 tests passed**, exit 0. `git diff --exit-code 9868e5f HEAD -- src tests` returned 0, confirming that run exercised unchanged application and test code.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed offline tests cover all four invalid responses with no writes, replay, key conflict, blocked/stale/other-actor guards and revoked-source reads. Recorded emulator execution demonstrates restart read-back, replay and projection. |
> | 2 | Changes stay within allowed paths | **Yes.** Requested scope command printed OK. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** Three-dot diff leaves intent, bundle composition, judgment contract and working paper unchanged. Existing record validators remain unchanged; tests add coverage without removing assertions or adding skips. |
> | 4 | No unauthorized dependencies or effects | **Yes.** New service uses the fixture backend and existing repository/API infrastructure; no added runtime dependency, credential, live transport or cloud operation. |
> | 5 | Truthful mode labels | **Yes.** Fixture metadata records `synthetic_fixture` and `fixture_supplied`; replay returns the saved artifact without invoking the backend. |
> | 6 | Unknowns remain unknown | **Yes.** Missing/inaccessible lineage priors yield insufficient evidence; later-cutoff and same-logical-task priors are excluded. No invented live receipts or case facts found. |
> | 7 | Complete verification and handoff packet | **Yes.** Implementation packet records Python 3.14.4, exact commands/results, failed attempts, remaining review step and next action. CORE-2 remains `in_progress`. |
> | 8 | Consistent with product direction and invariants | **Yes.** Artifacts remain proposed; accepted assumptions are untouched. Generation occurs outside storage transactions, save rechecks access/currentness, and inherited source permissions remain enforced. |
> 
> Findings: **None.**
> 
> **Verdict: accept** — all acceptance items have executed evidence, including inspected emulator logs for unchanged code, and no blocking or important findings remain.
**Verdict: accept.** Orchestrator ran scripts/h1/test.sh at 786ab47: 67 tests OK (reviewer sandbox had no loopback).
