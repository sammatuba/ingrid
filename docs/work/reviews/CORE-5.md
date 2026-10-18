# Review: CORE-5 live Gemini emulation bundle run with receipt

## Interim review (orchestrator seat, Fable, commit 89f0b15, 2026-10-12)

Interim, not the designated review. The designated reviewer (codex) had no credits; the owner decided building
continues on interim reviews. This record does not set the task `done`, is superseded by the designated independent
review when it is written, and does not replace the human semantic disposition that the pre-registered protocol in
[live-run.md](../probe-bundle/live-run.md) reserves for the owner or analyst. The reviewer did not author anything on
`task/CORE-5`. Scope inspected: the four commits `8a79891..89f0b15` (all `docs/work`, no code), the ignored run
directories under `.local/probe/` read with Python (keys, digests, numbers, `transport` block without any body; no
prompt text printed), `scripts/probe/run.py`, `src/adapters/systemone/run.py`, `src/adapters/gemini/run.py`,
`src/judgment/bundle.py`, `src/review/repository.py`, `src/review/storage.py`,
`tests/integration/test_probe_bundle_api.py`, `docs/work/probe-bundle/fixtures.md`. No network, model or gcloud call
was made by this review; no file outside this record was edited.

### Commands run and results

| Command | Result |
|---|---|
| `git rev-parse --short HEAD` | `89f0b15` |
| `git status --porcelain -uall` | empty (before and after the replay check below) |
| `grep -rIl -E 'ya29|Bearer|AIza' .local/probe/` | no match (exit 1) |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 300 tests in 3.218s` — `OK` |
| `/usr/bin/python3 scripts/plan.py scope CORE-5 task/CORE-3` | `OK: all changed files inside CORE-5 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 262 Markdown files, 1221 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `git diff --check` | clean |
| `/usr/bin/python3 scripts/plan.py show CORE-5` | state `in_progress`, owned path `docs/work/probe-bundle/live-run.md`, verify command `scripts/probe/run.py --config .local/probe/approved-config.json` |
| Offline replay of run 003 through `run_case(config, '.local/probe', transport_factory=<raises>)` with `VERTEX_ACCESS_TOKEN` unset | returned `proposed_bundle_saved`; the returned dict equals `result.json` byte for byte; the guard factory was never invoked; the run directory still holds exactly `attempts.sqlite3` and `result.json` |
| `render_bundle(saved task, 'gemini-3.8-flash')` offline on the saved `task` record | `request_digest` `f65d5595…ca6e`, equal to `bundle.payload.metadata.request_digest`; the rendered question ids equal the saved `questions` keys |
| Digest recomputation | top-level `content_digest` `e39a0135…b517` and bundle `content_digest` `f8fbc0bc…4b2d` both recompute; `sha256(canonical(composed))` equals `metadata.output_digest` `2d0dc7aa…c17f`, which is the intent's `output_digest = digest(composed)` |

The brief's verify command itself was not re-run through the CLI: with `result.json` present it would take the same
replay branch exercised above, and had the file been absent it would have attempted a model call, which this review
is not authorized to make. The guarded in-process call is the same code path minus that risk.

### Artifact-versus-record check (`.local/probe/core5-probe-003/result.json` against live-run.md lines 236–269)

| Receipt field in the record | In `result.json` | Match |
|---|---|---|
| `api` `vertex_ai` v1, model `gemini-3.8-flash`, `model_version` `gemini-3.8-flash`, location `global`, project `grid-nowcast` | `transport.api`/`api_version`/`model`/`model_version`/`location`/`configured_project` identical | yes |
| attempt 1 of 1, `response_received`, `elapsed_seconds` 11.93 | `attempt` 1, `limits.max_attempts` 1, `status` `response_received`, `elapsed_seconds` 11.929672 | yes |
| request 25,108 bytes, `request_body_digest` `8d118ff9…11d7` | `request_bytes` 25108, digest identical in full | yes |
| `response_id` `vWLMaoPAAebms8IPyd2J-Ao`; usage 8,880 / 1,609 / 10,489; no `thoughtsTokenCount` | identical; `usage` has exactly the three keys | yes |
| limits 1 / 2,048 / 65,536 / 30 s | `limits` identical | yes |
| bundle `content_digest` `f8fbc0bc…4b2d`, saved on `synthetic-case`, `semantic_review` `pending_human_review`, consequences `uncomputed` | identical; `review_state` `proposed`, `synthetic` true, `idempotency_key` `core5-probe-003`, `actor_id` `synthetic-analyst` | yes |
| `config_digest` `938b2852…` | **`db022caeb0a80999f289cae85b3c08d8287cc87d46387b54f14521640d20a51d`** (also the `allowance.digest` row in `attempts.sqlite3`, `used` 1). `938b2852…` is run 001's digest (its `failure.json`); the config file was re-id'd to `core5-probe-003`, current sha256 `38a2d273…b67d` | **no** |
| atomic answers q1–q8, flip_rate 0.0 everywhere, polarity_gap 0.0 on q4–q7, `unstable` not set | identical; `receipt.unstable` false, `unstable_questions` [] , `forms` 4 | yes |
| composed `supports`, `earlier_observation: Q3=before and Q6=yes`, escalation `none` | identical; `reason` null; thresholds tau_flip 0.25, tau_pol 0.3, tau_suff 0.6, tau_lineage 0.5, tau_cond 0.5 | yes |
| "The `metadata` block … carries no `request_digest` / `output_digest` keys" | **both keys are present**: `request_digest` `f65d5595…ca6e` (reproduced offline), `output_digest` `2d0dc7aa…c17f` (= digest of `composed`); metadata keys are exactly the intent's eight | **no** |
| "persisted on the emulator-backed store of this run" | `prepare_case` (`src/adapters/gemini/run.py:21`) builds `InMemoryRepository()`; nothing survives in any store. The durable artifact is `result.json` (mode 0600, under ignored `.local/`) | **no** |
| "replay not yet exercised" | exercised by this review (table above): the restart re-reads the immutable file, validates digests, makes no call | superseded |

Failed runs: `core5-probe-001/`, `core5-probe-002/` and `core5-inseat-001/` each hold only `failure.json`
(187 bytes) with `status` `MODEL_UNAVAILABLE`, `transport` null, `execution_mode` `live_inference`,
`synthetic_case` true, and no `attempts.sqlite3`, as the record says. Run 003 holds `attempts.sqlite3` (one table
`allowance`, one row, `used` 1) and `result.json` only. One directory the record does not mention exists:
`.local/probe/core5-gate-check/` (empty, 12:21). Unknown what created it; it holds nothing.

### Replayability (acceptance item 2)

**Met in the runner's sense, with the record's wording to be corrected.** The persisted artifact is the run
directory's `result.json`, written atomically by `write_private_json`, carrying its own `content_digest`. Replay is
`run_case`'s restart branch (`src/adapters/systemone/run.py:134-145` and `_saved_result`): when `result.json`
exists it is re-read, its content digest recomputed, its `config_digest` and `execution_mode` matched against the
configuration, every embedded record validated, and the saved result returned before any transport is constructed.
This review exercised that branch with a transport factory that raises, and got the saved result unchanged. This is
CORE-3's tested restart-replay behaviour, confirmed on the live artifact.

Not met, and not claimed by this review, is persistence in a repository store: the probe runner saves the
`ProbeBundleArtifact` through an in-memory repository that is discarded when the process exits, and the API replay
path of CORE-2 (`POST /probe-bundles` with the same key; `tests/integration/test_probe_bundle_api.py:80`) is a
different mechanism `scripts/probe/run.py` does not use. CORE-3's open note still stands: `bundle_input`,
`bundle_lineage_prior` and `save_bundle` are not in the `PersistentRepository` allow-list. The record's phrase
"emulator-backed store" is therefore wrong and should read "immutable run-directory result; the in-process
repository is in-memory".

### Reviewer's draft of the pre-registered protocol, items 1–7 (facts for the owner; no disposition)

All values below are read from `result.json`. `semantic_review.status` stays `pending_human_review`.

1. **Identity.** Q1 top is `fictional-unit-a` in f0, f1, f3 and `[1]` in f2 (un-aliased to the same option) at
   0.98 each; `cannot_tell` 0.02. `mapping.payload`: `entities` `[fictional-unit-a, GeneratingUnit]`,
   `cardinality` `one_to_one`, `status` `reviewed`, revision 1, reviewed by `synthetic-analyst`; `assumption_ref`
   `capacity-assumption` revision 1, digest `75b8…0859`, matching `accepted_heads.assumptions`. Identity is
   consistent with the reviewed mapping.
2. **Event and time.** The cited passage `quote` is "Unit A is testing at 80 MW; commercial availability is
   unconfirmed." (`start` 46, `end` 113; the slice of the source's `original_text` reproduces it). Source
   `published_at` `2026-10-01`, `known_at` `2026-10-01T01:00:00Z`, both before `task.payload.information_cutoff`
   `2026-10-05T02:00:00Z`; no later document is cited, so no post-cutoff claim exists. Q2 `testing` matches the
   quote. Q3 `before` (0.90; `not_stated` 0.07) rests on the publication date against the assumption's
   `valid_period` 2026-10-06..07: the quote itself carries no date for the testing. Reading `before` from the
   publication date is a judgement the owner confirms or not.
3. **Lineage and observation.** One lineage `fictional-lineage`, one source `fictional-advisory`,
   `copied_from` null, `content_kind` `reported_claim`. Q5 `no` (0.05; negated form 0.95) is consistent: nothing
   is repeated, and no corroboration question arises. Q6 `yes` (0.70; negated 0.30): "is testing at 80 MW" is a
   reported observation; the second clause ("unconfirmed") is not an observation. Note the observation is of
   80 MW testing, not of 100 MW available capacity.
4. **Direction and conditionality.** `assumption_definition`: `assumed_available_capacity` 100.00 MW for
   2026-10-06..07, proposition "Assumed available capacity for the next operating day". Q4 `yes` (0.85; negated
   0.15) tracks the "commercial availability is unconfirmed" clause. Q8 `challenges` 0.85 (`neither` 0.10,
   `supports` 0.05) in all four forms. Under `original_definitions`, `challenges` is "relevant reason to
   reconsider; does not establish falsity" and `supports` is "consistent with and directly relevant to the
   proposition". The composition fired `earlier_observation` (`src/judgment/bundle.py:434-435`, RULES position 10),
   which reads Q3 and Q6 only; the `conditional_support` row (Q4 ≥ tau_cond and Q3 in same/before → `mixed`) is
   position 11 and never got a chance, and Q8 enters only the `time_not_stated` row. So the frozen table composed
   `supports` without consulting the direction answer or the conditional answer, by construction.
5. **Stability.** Per-question tops identical across f0–f3 for all eight questions; `flip_rate` 0.0 everywhere;
   `polarity_gap` and `max_gap` 0.0 on q4–q7 (the negated f1 values mirror exactly: 0.15/0.95/0.30/0.25);
   `unstable` false; no escalation. The probability vectors are also identical across forms
   (0.98 / 0.95 / 0.90 / 0.85 …), a tidy verbalized pattern to note, not evidence of calibration.
6. **Status wording.** `bundle.payload.review_state` `proposed`; `metadata.probabilities`
   `verbalized_uncalibrated`; `semantic_review` `{pending_human_review, uncomputed}`; `accepted_heads` unchanged
   (`outlook` null, `capacity-assumption` revision 1); the run returned `MODEL_STATE_CHANGED` nowhere. No
   probability in this record is restated as an event probability.
7. **Unsupported claims and unknowns.**
   - The label `supports` is not supported by the quote on magnitude: 80 MW testing against 100 MW assumed, with
     availability unconfirmed. The table reads only "an earlier observation exists"; the model's own direction
     answer says `challenges`. Which is right is the owner's disposition.
   - Every probability (0.98, 0.95, 0.90, 0.85, 0.70, 0.75 and their complements) is model-supplied; no record
     confirms any of them.
   - Q7 `yes` at 0.75: whether a single passage from a single source suffices is for the owner.
   - `model_version` equals the alias `gemini-3.8-flash`; the receipt carries no dated version pin.
   - The response byte count is bounded by `max_response_bytes` 65,536 but not recorded; `response_received` is
     the only evidence it was within bound.
   - "Token held only in the runner process" is recorded as stated; not verifiable from the artifact.
   - `.local/probe/core5-gate-check/` exists empty and unexplained.
   - `audit_cutoff` `2026-10-12T04:31:56.969734Z` is the run's wall clock and enters `task_digest`, so a re-seeded
     run would render a different `request_digest`; the saved task's digest reproduces, a fresh task's would not.

### Findings

| Severity | Location | What | Why |
|---|---|---|---|
| important | `docs/work/probe-bundle/live-run.md:255` | Receipt table gives `config_digest` `938b2852…`; the artifact and the allowance ledger say `db022cae…b0a8…a51d`. `938b…` is run 001's digest | A receipt whose recorded digest does not match the artifact is a mislabelled receipt (checklist 6). Correction: replace the digest; note the config file is now run id 003, sha256 `38a2d273…b67d`, so lines 32 and 65 describe an earlier state of the same file |
| important | `docs/work/probe-bundle/live-run.md:263-266` | States the `metadata` block carries no `request_digest`/`output_digest` and defers output 1 to a reviewer's call or a later slice; both keys are present and both reproduce | Inverts the status of output 1, which is fully met by the saved artifact. Correction: delete the sentence; record the two metadata digests in the receipt table |
| important | `docs/work/probe-bundle/live-run.md:268-269` | "persisted on the emulator-backed store of this run" | Untruthful persistence label (checklist 5): the runner's repository is `InMemoryRepository`; the durable artifact is `result.json`. Correction: reword as above; replace "replay not yet exercised" with the replay evidence (this record, or the orchestrator's own re-run of the verify command, which now takes the replay branch) |
| important | `docs/work/probe-bundle/live-run.md:259-262` | Calls the live case "the same contestable row EVAL-2 and EVAL-3 flag (frozen `challenges` vs table `supports` for the return-date assumption kind)" | The live assumption is `assumed_available_capacity`, the supply-outlook half (`pb-er-3`/`pb-er-4`) on which fixtures.md records table and annotation agreeing on `supports`; EVAL-2/EVAL-3 are `pending` with no review record on this branch; the flag lives in `fixtures.md` ("The contestable rule, both assumption kinds"), `FEEDBACK.md` 2026-10-11 and the EVAL-1 record. Correction: name the half and the actual sources; state that the live model disagreed with both the table and the frozen annotation for that half |
| minor | `.local/probe/core5-gate-check/` (ignored) | Empty run-id directory not mentioned in the record | Unknown origin; either name it in the record or remove it so the artifact tree matches the account |
| minor | `docs/work/probe-bundle/live-run.md:239-240` | "`start.sh` now links the main checkout's directory" | The committed `scripts/seats/start.sh` on this branch has no `gcloud` or `CLOUDSDK` line (`grep` empty; `git log -- scripts/seats/start.sh` ends at `1789540`), so the change is uncommitted or lives elsewhere; the claim should point at where it lives or be dropped |

None of the findings touches code, a frozen contract, an acceptance text or a test. All corrections are edits to
the orchestrator's section of the owned packet.

### Acceptance verdicts

| Acceptance item | Verdict | Evidence |
|---|---|---|
| One bounded request within configured token and byte limits | met | `request_bytes` 25,108 < 196,608; `candidatesTokenCount` 1,609 < `max_output_tokens` 2,048; `attempt` 1 with `max_attempts` 1 and ledger `used` 1; `status` `response_received` within 30 s (11.93 s) |
| Artifact persisted and replayable | met in the runner's sense (file artifact plus restart replay, exercised above); the record's persistence wording is wrong and must be corrected; no repository-store persistence exists or is claimed | section above |
| No credential or prompt in Git | met | `git status --porcelain -uall` empty; `.local/` ignored; byte scan clean; the four commits are `docs/work` files only |

Outputs: receipt (request and output digests, model version, token counts) present in `transport` and
`metadata`; composed label and receipt persisted on `synthetic-case` in `result.json`; interpretation review
drafted here as items 1–7 and still owed to the packet by the owner or analyst with a disposition.

### Outcome and next action

The live run happened once, bounded, with a clean credential trail, and the artifact is sound and replayable.
What is not sound is the written receipt record in live-run.md, which misstates one digest, inverts the metadata
status, mislabels the persistence and misnames the contestable half. Next action for the orchestrator: fix the four
important lines in the "executed" section, decide the two minors, append the owner's or analyst's disposition of
items 1–7 (which this draft does not supply), then re-request review. The designated review supersedes this one; the
semantic disposition remains the owner's.

**Verdict: rework.** Documentation-only: the receipt record must match the artifact before an accept can name the
commit it reviewed.
