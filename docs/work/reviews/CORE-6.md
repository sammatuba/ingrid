# Review: CORE-6 M3 original cited Gemini task through the existing runner

Range `feat/h1-api-persistence..3dc5773` on `task/CORE-6`; reviewed 2026-10-12; interim review by
the orchestrator seat (see below), not the designated independent reviewer; scope inspected: the
three changed files (`docs/work/m3-live-gemini/implementation.md`, `docs/work/PROGRESS.md`,
`docs/work/tasks.json`), the ignored receipts under `.local/m3-live/core6-cited-001/` and
`core6-cited-002/`, the runner stdout `.local/m3-live/core6-002.stdout`, the brief, the
milestone text and the M3 gate row.

## Interim review (orchestrator seat, Fable, commit 3dc5773, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated
re-review is required before `done`. The live calls were made by the orchestrator, so this
interim review is not fully independent of the operator; it is independent of the code author.

The verify command (`gemini-run.py --config .local/m3-live/approved-config.json`) was **not
rerun** by this reviewer: it is a live paid call, the single permitted attempt for
`core6-cited-002` is consumed (`attempts.sqlite3` `allowance` has 1 row, `max_attempts` 1), and
the reviewer seat has no call authority. Substitute evidence: the receipt `result.json`, the
one-line runner stdout (`proposed_judgment_saved`, `synthetic_case: true`, artifact path) and the
sqlite allowance table, all read with `python3 -I`.

### Checklist

1. Acceptance items met by checks actually run: **yes**. (a) Citation validated against the
   immutable context: one citation, `passage_index` 0 valid for a one-entry context; its quote
   equals `passage.payload.quote` and `task.payload.context[0].quote`; `quote_digest` and
   `source_byte_digest` recomputed and match. (b) Receipt preserved under `.local` and
   summarised in the packet: yes, numbers below. (c) M3 live gate recorded: yes, as "met for the
   transport and cited-judgment path".
2. No file outside allowed paths: **yes**. `plan.py scope CORE-6 feat/h1-api-persistence` ->
   `OK`; `git diff --stat` shows only the three docs/work files; no `src/` or `tests/` change
   remains after the rebase onto CORE-7.
3. No frozen contract, acceptance text or test changed: **yes** (no `tasks.json` change beyond
   `state`, two diff lines; no test file in the range; 261/261 OK).
4. No new dependency, service, credential, network call or cloud effect beyond the packet: **yes**.
   The two live calls are named in the packet with run ids, configs and digests; the Vertex path
   is CORE-7's merged transport, authorized by GATE-2 (PROGRESS.md:29).
5. Mode labels truthful: **yes**. `execution_mode` `live_inference` at top level and in
   `judgment.payload.metadata`; `transport.api` `vertex_ai`, `transport.status`
   `response_received`, `usage` present; attempt 1 labelled "no inference" and its receipt shows
   `usage` null, `MODEL_UNAVAILABLE`.
6. Unknowns stayed unknown, no invented numbers: **yes** for every number checked (table below);
   `semantic_review.status` `pending_human_review`, consequences `uncomputed`, `review_state`
   `proposed`; two unknowns and two alternatives present in the answer. One derived phrase, see
   finding 3.
7. Packet records interpreter, commands, results, unfinished items, next action: **partial**.
   Attempt 1 is complete; attempt 2 gives the interpreter without version, does not paste the
   post-rebase suite and scope results, and the next action ("Independent review next") sits
   only in the PROGRESS log. Finding 4.
8. Nothing contradicts the blueprint, strategy refresh, working paper or domain invariants:
   **yes**. Synthetic flags true throughout (`synthetic_case`, `judgment.payload.synthetic`,
   `task.payload.synthetic`, case `synthetic-case`); judgment stays `proposed`.

### Receipt checks (`.local/m3-live/core6-cited-002/result.json`)

| Packet claim | Receipt | Result |
|---|---|---|
| 3.45 s | `transport.elapsed_seconds` 3.445841 | match |
| 1474 / 312 / 1786 tokens | `usage` prompt 1474, candidates 312, total 1786 | match |
| request 4657 bytes | `transport.request_bytes` 4657 | match |
| response id `foTLatzyHY6ovr0P-4UV` | `transport.response_id` | match |
| config digest `5a8fb0ea…d5d58`, file sha256 prefix `78b9bc63ebefb48b` | `config_digest`, `sha256sum approved-config.json` | match |
| `gemini-3.8-flash`, `global`, `grid-nowcast`, run `core6-cited-002`, attempt 1 | `transport.*` | match |
| label `challenges`, one citation, `passage_index` 0 | `judgment.payload.answer` | match |
| attempt 1: 0.70 s, 4619 bytes, digest `232c4d56…fd457`, usage null, `v1beta` developer API | `core6-cited-001/failure.json` | match |
| "`grep ya29` finds no token" | `grep -rl ya29\|Bearer\|AIza` over `.local/m3-live/` (both run dirs, both stdout files, config) | absent |

### Findings

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| minor | docs/work/m3-live-gemini/implementation.md:148 | "bytes 46–113" misnames the offset unit; `Passage.start/end` are character offsets | `original_text[46:113] == quote` is True; the byte slice is off by one (em dash in the preamble is 3 bytes); `records.py:209-210` checks range and `quote_digest`, not the unit | write "characters 46–113" |
| minor | docs/work/m3-live-gemini/implementation.md:120 (attempt 1 stop condition) | A stop condition fired (fix outside allowed paths) and the orchestrator applied the one-line fix anyway, flagged "reviewer to judge" | Ruling: recorded, not hidden; superseded by CORE-7's merged `APPLICATION_JSON`; zero residual diff (scope OK). Not a work-around that fails review. The fired stop condition has no `FEEDBACK.md` entry (`grep CORE-6 FEEDBACK.md` empty) | guardian adds a dated ledger entry; FEEDBACK.md is outside this task's paths, no change on this branch |
| minor | docs/work/m3-live-gemini/implementation.md:145 | "well under one US cent" is derived, not read from a record | no cost field in the receipt | cite the price basis or drop the parenthesis |
| minor | docs/work/m3-live-gemini/implementation.md:127-159 | attempt-2 section omits interpreter version, post-rebase suite/scope results and the explicit next action (checklist 7) | compare with attempt 1 at :89-125 | add `3.14.4`, "261 OK", "scope OK", "next: designated independent review" |
| minor | docs/work/PROGRESS.md:17 | milestone table still says "none yet; live Gemini receipt outstanding" while the log at :118 records the receipt | the M3 exit criterion (milestones.md:76) asks for one cited receipt with digests and token counts, which now exists; CORE-2/3/4 items remain open so M3 itself stays open | update exit evidence to name `core6-cited-002` and keep state `open`; also, two log rows dated 10-11 sit after a 10-12 row |

Question, not a finding (out of CORE-6 scope): `src/review/records.py:209-210` validates the
passage range and quote digest but never checks that `original_text[start:end]` equals the
quote; a CORE-7/records follow-up could add that.

Honesty of the M3 live gate claim: the milestone text (milestones.md:76) requires "one actual
cited Gemini receipt with digests and token counts". The packet claims exactly that and
explicitly does not claim semantic review, which the brief lists as an Output but not as an
acceptance item. The split claim is honest and matches the receipt; the undelivered Output is
stated, not hidden. The gate row itself is the owner's to flip.

### Verification run by the reviewer

`/usr/bin/python3 -m unittest discover -s tests` -> Ran 261 tests, OK.
`/usr/bin/python3 scripts/plan.py scope CORE-6 feat/h1-api-persistence` -> OK.
`/usr/bin/python3 scripts/plan.py check` -> OK: 41 tasks, 7 gates.
Receipt checks via `python3 -I` script as tabulated above.

**Interim verdict: accept.** All three acceptance items are met by checks run against the
receipt, the branch carries only truthful packet records, and the findings are wording and
ledger items; `done` still waits for the designated independent accept.

## Outcome and next action

Task stays `in_progress` until the designated re-review. Suggested before that: the four
wording corrections above on this branch and the guardian's FEEDBACK.md entry. This verdict does
not imply external approval, publication or deployment.

## Designated review (GPT Astra, independent, commit `b7d766f`, 2026-10-12)

> Independent review of `feat/h1-api-persistence...b7d766fa127157fd813ab5fca5996bdf19b69ccf`, including all four commits and the preserved local receipt/ledger. Working tree clean; no files edited.
> 
> Verification executed with Python 3.14.4:
> 
> - Requested verify command: **exit 0**, `proposed_judgment_saved`. This validated the existing immutable receipt through the restart path; no new inference occurred.
> - `/usr/bin/python3 scripts/plan.py scope CORE-6 feat/h1-api-persistence`: **OK**.
> - `plan.py check`, `repo.py check`, and diff whitespace check: **passed**.
> - Full offline suite: **261 tests, 37 errors** because the read-only sandbox provides no writable temporary directory. The suite did **not** pass in this review.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every brief acceptance item demonstrated | **Yes**, for the three explicit acceptance bullets: replay validated citations/source correspondence and record digests; local receipt and ledger exist; packet records the live gate as met. The separate semantic-review output remains missing. |
> | 2 | Changes within allowed paths | **Yes**. Scope printed OK; four documentation/coordination files changed. |
> | 3 | Frozen contracts, acceptance text and tests preserved | **Yes**. No runtime/test changes; `tasks.json` changes only CORE-6’s state. |
> | 4 | No effects beyond the packet | **Yes**, against recorded authorization: GATE-2 names the Vertex service/model/project; packet describes both attempts and diagnostic calls. No new dependency or service appears in the diff. |
> | 5 | Truthful mode labels | **Yes**. Saved receipt identifies live inference on a synthetic case; judgment remains proposed. This review’s execution was receipt replay. |
> | 6 | Unknowns preserved; no invented numbers | **No**. Usage numbers match the receipt, but “well under one US cent” has no recorded cost or pricing calculation. Semantic review and consequences correctly remain pending/uncomputed. |
> | 7 | Complete execution and handoff record | **No**. Attempt 2 omits post-rebase suite/scope results and an explicit packet next action; those are scattered across the interim review and progress log. |
> | 8 | Consistent with product direction and invariants | **Yes** for demonstrated behavior: evidence remains attributed, mapping reviewed, judgment proposed, and consequences uncomputed; no accepted assumption change or forecasting claim is demonstrated. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/m3-live-gemini/implementation.md:158` | Required semantic-review output is deferred, so the task is incomplete despite citation validation. | Receipt says `pending_human_review`; brief requires semantic review; intent requires evaluating interpretation against source, assumption, mapping and cutoff. | Record that assessment and disposition. Explicitly distinguish 80 MW testing from commercial availability and assess the speculative alternatives without treating them as facts. |
> | minor | `docs/work/m3-live-gemini/implementation.md:145` | Unsupported monetary claim exceeds recorded evidence. | Receipt contains token usage, no cost; packet provides no pricing basis. | Remove the cost phrase or supply an auditable calculation. |
> | minor | `docs/work/m3-live-gemini/implementation.md:127` | Incomplete closing record makes verification and resumption ambiguous. | Attempt-2 section lacks required suite/scope command results and exact next action. | Consolidate actual verification evidence, limitations and next action in the packet; do not report this sandbox’s suite as passing. |
> 
> **Verdict: rework.** The cited receipt is demonstrated, but the required semantic review remains undelivered.
**Verdict: rework.** Supersedes the interim accept above: the required semantic review of the live answer remains undelivered. This is a human step: the owner (or an analyst) reads the saved judgment (label `challenges`, one citation, two alternatives, two unknowns) and records an attributable semantic review; no code change is implied.

## Designated review (GPT Astra, independent, commit `1513dbc`, 2026-10-12)

> Independent review of `feat/h1-api-persistence...1513dbcf35b1`, including all six commits and preserved local artifacts. No files edited.
> 
> Verification with Python 3.14.4:
> 
> - Requested verify command: **exit 0**, `proposed_judgment_saved`. It validated the existing receipt through replay; no new inference occurred.
> - `/usr/bin/python3 scripts/plan.py scope CORE-6 feat/h1-api-persistence`: **OK**.
> - `plan.py check` and `repo.py check`: **passed**.
> - `/usr/bin/python3 -m unittest discover -s tests`: **261 tests, 37 errors**; the read-only sandbox prevented temporary-directory creation. This review does **not** establish a passing full suite.
> - `git diff --check feat/h1-api-persistence...HEAD`: trailing whitespace in the review record.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Replay validated record digests, citations and source correspondence. Receipt and SQLite ledger exist under `.local/m3-live/core6-cited-002/`; the packet summarizes them and records the live gate as met. |
> | 2 | Changes within allowed paths | **Yes.** Scope printed OK; four documentation/coordination files changed. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No runtime or test changes; `tasks.json` changes only CORE-6’s state. |
> | 4 | No effects beyond the packet | **Yes**, against recorded authorization. GATE-2 and the packet identify the service, model, credential reference, attempts and diagnostic calls. |
> | 5 | Truthful mode labels | **Yes.** Preserved receipt records live inference on a synthetic case; this review performed replay. Judgment remains proposed. |
> | 6 | Unknowns preserved; no invented numbers | **No.** Token counts match the receipt, but “well under one US cent” lacks recorded cost evidence. Availability and consequences remain unknown/uncomputed. |
> | 7 | Complete execution and handoff record | **No.** Attempt 2 lacks consolidated suite/scope results and an explicit current next action; these remain scattered across review and progress records. |
> | 8 | Consistent with direction and invariants | **Yes.** Evidence remains attributed, mapping reviewed, information and audit cutoffs distinct, and accepted assumptions unchanged. |
> 
> The owner’s review at `implementation.md:161–172` resolves the previously missing semantic-review output. I agree with `challenges`: testing at 80 MW with unconfirmed commercial availability warrants reconsideration of the 100 MW assumption without establishing falsity. The reviewed mapping identifies the same unit, and the source predates the information cutoff. Both generated alternatives remain hypothetical; neither establishes commercial capacity.
> 
> All findings below remain unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/m3-live-gemini/implementation.md:145` | Unsupported monetary claim exceeds receipt evidence. | Receipt contains usage, no cost or pricing calculation. | Remove the cost phrase or supply an auditable calculation. |
> | minor | `docs/work/m3-live-gemini/implementation.md:127` | Incomplete closing record obscures verification and resumption. | Attempt-2 suite/scope results and current next action are elsewhere. | Consolidate actual commands, results, sandbox limitations and next action in the packet. |
> | minor | `docs/work/PROGRESS.md:17` | Milestone summary contradicts preserved evidence. | Says the live receipt is outstanding; `core6-cited-002` exists. | Name the receipt while keeping the overall M3 milestone open. |
> | minor | `docs/work/reviews/CORE-6.md:109` | Added whitespace fails the whitespace check. | Six quoted blank lines reported by `git diff --check`. | Remove trailing spaces. |
> 
> **Verdict: accept.** The three acceptance items are demonstrated and the required semantic review is now recorded, with only minor documentation findings remaining.
**Verdict: accept.** First live cited Gemini judgment on Vertex AI; owner semantic review recorded. M3 live gate met.
