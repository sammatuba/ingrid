# DOCK-3 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent of the author; 2026-10-18)

| Field | Value |
|---|---|
| Task | DOCK-3: the agent service (threads, turns, drafts, confirmations, action receipts, the day meter, routes, labelled fakes) |
| Branch | `task/DOCK-3` |
| Commit | `414a37ee` |
| Base | `971885b0` (origin/main merged in at `2f7b28ac`; origin/main has since moved to `8d20c523`, BOOK-1) |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author |
| Verdict | **rework** (one major finding: the executor does not read the plan shape DOCK-1's composer emits) |

The record follows the brief (`scripts/plan.py brief DOCK-3`), strategy decisions 3, 10, 13 and 14 and
sections 1 to 3, and agent contract sections 3 to 5. Orchestrator ruling applied: the six additions in
the packet's "Deviations" table are judged on soundness, not on the contract's "a field not listed here
does not exist" sentence.

### Commands run and results

All from the worktree `.local/wt/DOCK-3` with `/usr/bin/python3`. No network, model or cloud call.

| Command | Result |
|---|---|
| `git diff 971885b0..HEAD` | read in full: `src/agent/` (7 files), the three test files, the packet, `tasks.json` (state `in_progress`), `PROGRESS.md` (row edited in place, one log row) |
| `python3 -m unittest tests.test_agent_fakes tests.test_agent_service tests.test_agent_store` | `Ran 61 tests in 0.085s`, **OK** |
| `python3 scripts/plan.py check && python3 -m unittest discover -s tests -p "test_*.py"` (the brief's verify) | `OK: 135 tasks, 9 gates`; `Ran 2685 tests in 207.216s`, **OK (skipped=115)**. No pypdf error: the worktree's `.local/pylib` link is in place |
| `python3 scripts/plan.py scope DOCK-3 origin/main` | `OK: all changed files inside DOCK-3 allowed paths` |
| `python3 scripts/repo.py check` | `Checked 601 Markdown files, 3839 local links, 5 skills; bootstrap 1399 words. PASS` (before this record was written) |
| `git diff --check 971885b0..HEAD` | clean |
| `OutlookArchive('.local/outlook-archive').verify()` before and after the suite | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}` both times; `sha256` of all 5 files (2 outlooks, 2 values, 1 stale mark) identical before and after |
| `git status --short` after all runs | clean (only this record is new) |
| Probe scripts (scratchpad, outside the tree) driving `AgentService` on `MemoryAgentStore` with scratch archives, and `catalogue.load()` against `git show task/DOCK-1:src/judgment/actions.py` | results under the findings and the attack table below |

### Attack checks

| Check | Result |
|---|---|
| (a) A write without a confirmation in state `confirmed` | Not found. `_execute_write` is the only caller of `mark_stale`, `issue`, `decision_writer`, `share_writer` (the syntax-tree test, and my reading). It receives only the document `decide_confirmation` returned. Forged document stored already `confirmed`: `confirm` raises `AlreadyDecided`, 0 marks. `create_confirmation` in state `confirmed`: `ValueError`. Another uid: `UnknownRecord`, state stays `pending`. Arguments edited on a returned copy: the store keeps the originals (deep copies), and the confirm body accepts only `{decision}` (extra `args` key: `InvalidInput`). Replay: `AlreadyDecided`, still 1 mark. The store is the trust boundary: a `pending` document written straight into the store is executed on confirm (expected; see observation 1) |
| (b) An unsigned request reaching a write or the live planner | Not found with the fallback table. `_backend` returns the recorded planner for `user is None`; writing and sign-in actions are refused `needs_sign_in`; nothing is stored. The guard depends on the catalogue's flags only (finding 3) |
| (c) Budget fails closed; Manila day | `StoreUnavailable` is a `budget_unavailable` refusal and the recorded planner answers. Another store error (probe: `RuntimeError`) propagates as an exception, but the live planner is never called, so it still fails closed (finding 6). Day rollover at 16:00Z is tested and correct (UTC+8) |
| (d) Privacy | No `logging`, `warnings` or `print` in `src/agent`; `assertNoLogs` test passes. Owner is `sha256("agent-owner\|" + uid)[:32]`. Document ids are uuid4, digests or the day. Exception texts carry codes and field names only, never a value or the question. Receipts carry `args` (manifest ids) and codes. The question is stored in the turn, as contract section 3 says, in the private namespace |
| (e) Imports | Only the composer (`src.judgment`, `src.judgment.view`), DOCK-1's module by name, `src.outlook.records`, `src.outlook.dependency`, `src.alerts.auth` (exception classes), and lazy `google.*` and `fastapi`. No `src.api`, `src.grid`, `src.book`, `src.evidence`, `src.case`. Allowlist test passes |
| (f) Fakes | Every case, claim, chain, card, search receipt, adapter and adapter result carries `synthetic: True` and a `label`; numeric fields are `None`. Tested and read |
| (g) Routes | Built as `src/alerts/routes.py` is (lazy `fastapi`, the same `refuse`, `body_of`, `guarded`); `grep` finds no import of `src.agent` outside `src/agent`: not mounted |
| (h) Catalogue fallback and read path | Fallback works. The read path refuses DOCK-1's real table (finding 1) |
| (i) Copy | See finding 7 |

### Findings

1. **major. The executor does not read the plan shape DOCK-1's composer emits.** Bears on the brief's
   output line "`src/agent/service.py`: ask (plan through the composer, run the free actions, park the
   writes)" and on acceptance line 2 once DOCK-1 lands.
   - `src/agent/service.py:109` `proposed_actions` reads `answer['actions']`, else
     `answer['receipt']['plan']['actions']`, and `_act` executes their `args` as identifiers. On
     `task/DOCK-1` (`902079fe`), a composed answer has no top-level `actions`. The plan's `args` are
     manifest references (letter handles such as `assumption-a`, `record-a`). The resolved identifiers
     and the composer's refusals are in `answer['receipt']['actions']` (`proposed[i].resolved`,
     `refused[i].reason_key`; `src/judgment/actions.py` `action_record`). Handles match `IDENTIFIER`,
     so they pass every executor check. Probe: `mark_stale` with `{assumption_id: 'assumption-a',
     revision: 'revision-a'}` is parked `needs_confirmation`, and after the click it is refused
     `assumption_unknown`. A `draft` would store handles in `rests_on`, and the book would be queried
     with handle strings. The executor also runs an action the composer refused (for example an `open`
     route outside `SITE_ROUTES` when `site_routes` is not handed in).
   - `src/agent/catalogue.py:43` `_flags` requires `writes` to be a `bool`. DOCK-1's `ACTIONS` gives
     `writes` as a tuple of record kinds (`()`, `('private_copy',)`). Probe: `catalogue.load()` with
     DOCK-1's module returns `'fallback'`, and `_flags(ACTIONS['open'])` is `None`. So
     `actions_source` would say `fallback` permanently. This is safe, because the fallback equals the
     contract's flags, but the read path never works against the real file.
   - The contract's "manifest ids only" (section 1) is ambiguous, and DOCK-3 could not see DOCK-1's file
     when it was built. But the orchestrator put the DOCK-1 branch in this review's scope, and the
     fix lies inside DOCK-3's paths.
2. **minor. Confirmations are parked that cannot run.** `src/agent/service.py:346`. The packet says
   "no confirmation is parked that could not run". That holds only for an absent write path. Probes:
   (a) `revision: 'not a commit'` is parked, and after the click it is refused `stale_invalid` (the preview
   checks only `type is str`, while `dependency.py` needs `[0-9a-f]{7,40}`); (b) an assumption no outlook
   cites is parked with `preview.outlooks: []`, and after the click it records `done` with
   `record_refs: []` and 0 marks: a recorded decision that wrote nothing. Acceptance line 1 still holds.
   The person is asked to confirm a write that will not happen.
3. **minor. The unsigned guard trusts the catalogue's flags, not the executor's own invariant.**
   `src/agent/service.py:250` and `:293` to `:313`. Probe with a table that marks `draft` and
   `search_web` as no sign-in: an anonymous `draft` stores a draft with `owner: None`, and an anonymous
   `search_web` raises `TypeError` at `:297` (`owner + '|'`). The real tables both mark them sign-in,
   so this is defence in depth for acceptance line 2 ("an unsigned request can run no writing action").
4. **minor. A writer that raises outside the caught types leaves a confirmed decision with no
   execution receipt and an exception to the page.** `src/agent/service.py:436` (the `share_writer`
   result is not guarded), `:428` (only `ValueError`), `:461` to `:467`. Probe: a `share_writer`
   raising `ValueError` leaves the confirmation `confirmed`, with only the `needs_confirmation` receipt
   under it, and the `ValueError` reaches the route (500). An `OSError` from the archive behaves the same.
   The packet says "a write that its API refuses is a refused receipt under the same confirmation, never
   an exception".
5. **minor (latent test).** `tests/test_agent_service.py:435` asserts
   `actions_run == proposed_actions(answer)`. This is true only while plans carry no actions (receipts
   are not proposals). It fails under view.v4. DOCK-1 keeps `sample_records` and `CUTOFF` in
   `tests/test_judgment_view.py` (checked on `task/DOCK-1`: lines 61 and 314), so the import holds.
6. **minor. The meter's scope and an unexpected store error.** `src/agent/budget.py:61` to `:64`.
   (a) Only `StoreUnavailable` is caught. Any other error from `charge_budget` is an exception to the
   page, although no live call runs (fail-closed holds). `FirestoreAgentStore._call` maps the same
   errors as `src/alerts/store.py:128` (pattern kept), so a credential error is not mapped either.
   (b) The platform line (platform-epics strategy section 8: "5 USD per day ... search calls, Gemini
   tokens") counts search as well. This meter charges planner calls only, and `search_web` is
   uncounted. That is acceptable while search is the fake; hand it to EVIDENCE V2 and DOCK-5.
   (c) A signed-in free question charges 3 calls even when the composer answers `insufficient` without
   calling the backend. This overcharges, which is the safe direction.
7. **minor (copy, hand to DOCK-2 or fix here).** `src/agent/fakes.py:18`. Every fake's label, which the
   packet tells DOCK-2 to show beside the fake, names internal lane codes ("replaced when CASE (C1,
   C2) lands its record", "EVIDENCE (V1)", "BOOK (BOOK-2)") and joins two clauses with a semicolon.
   `MODEL_CARD.status_line` says "the card contract". On a public screen these break the plain-language
   rules (internal words, copy rule 2's one caption line). `repo.py check` scans Markdown only, so it
   passes. The semicolon in `routes.py:30` copies `src/alerts/routes.py`, so it is not a finding.

### Judgements asked of the reviewer

- **The six record additions: sound.** `turn.budget` is needed for acceptance line 3 without
  touching the composer's receipt digest. `receipt.reason_key` is the only way a refusal says why.
  The receipt envelope is right, because turns are append-only and a confirm-time receipt follows its
  turn. `agent_evidence` is the strategy's "search receipt in the private copy". `results` is not stored.
  The queue shape fills a gap in section 4. Each is documented with its reason. One note: the
  `reason_key` vocabulary splits from DOCK-1's (`args_outside_manifest` here, `argument_not_in_manifest`
  there). Pick one in the rework of finding 1.
- **`share` refusing `no_write_path`: correct.** No shared record kind exists, and the contract forbids
  a new write path.
- **The mark_stale citation in the action receipt, not the mark: correct.** It is forced by the closed
  `MARK_KEYS` and the commit-id pattern of `new_revision` in `dependency.py`, outside this task's
  paths. The consequence: the archive alone cannot trace a stale mark to the person's decision.
  Only the agent store can do that, through the receipt's `content_digest`. The ARCH-3 hand-back
  (`cause_ref`) is the right follow-up.
- **0.02 USD per call: acceptable as a stated estimate.** It is labelled not measured. DOCK-4 records
  the measured cost, and it is above a flash-model call of a few thousand tokens, so it errs safe. See
  finding 6 for the scope.
- **`save_decision` through a port with a recording double: sound.** `src/review/repository.py:785`
  requires `request_id` and `idempotency_key` in a review request, and `src/review/records.py:479`
  requires them in the DecisionRecord payload. So the citation carries through once DOCK-5 wires
  `commit_review` and owns the body shape. Today only the double proves it.

### Observations (no finding)

1. The store is the trust boundary: a `pending` confirmation written directly into the store runs on
   confirm. DOCK-5 must deny client writes to `agent_*` in the Firestore rules (hand-back).
2. `POST /api/agent/ask` uses `users.user` and not `users.require`. A signed-in account outside
   `NOWCAST_ALERT_EDITORS` can therefore ask live and write drafts, pins and search receipts, but it
   cannot read its threads or confirm (403). This matches decision 13 ("signed-in users only") while
   the editors list is unset. DOCK-5 should state which rule applies.
3. `thread` accepts any identifier as `case_ref`, so the number of threads per owner is not bounded.
4. The packet says `src/book` does not exist. That was true on the base. origin/main now carries
   BOOK-1, and the book adapter remains a handed-in port.

### Verdict and exact rework

**rework.** Acceptance lines 1 to 5 are each proved by tests I ran and by the probes. Finding 1 is
major because the executor would run the real planner's actions on handles.

1. `src/agent/service.py` `proposed_actions`: when `answer['receipt']['actions']` is a dict, read
   `proposed`. For each entry refused there (match `refused[].index`), write a `refused` receipt with
   the composer's `reason_key` and do not execute it. Otherwise execute with `resolved` as the args.
   Fall back to the plan's `actions` only when no `actions` block exists.
2. `src/agent/catalogue.py` `_flags`: accept `writes` as a bool or a list or tuple (non-empty means it
   writes). Add a test that loads a module with DOCK-1's entry shape (tuple `writes`, `args` as a dict
   of schemas, `required`, `one_of`) and gets `source == 'src.judgment.actions'`.
3. One service test with a DOCK-1-shaped answer (handles in `plan.actions`, identifiers in
   `receipt.actions.proposed[].resolved`, one entry in `refused`). It must prove that the archive
   receives the identifier, that the draft's `rests_on` holds identifiers, and that the refused entry
   is not run.
4. Findings 2 to 4 (small, same files): refuse `mark_stale` at planning when `revision` does not match
   the commit-id pattern or no outlook cites the assumption (`no_record`). In `_run_free`, refuse
   `needs_sign_in` when `owner is None` for any action other than `open`, `query_exposure` and
   `query_impact`, whatever the table says. In `confirm`, catch any exception from `_execute_write`
   after the decision, record a `refused` receipt with a fixed `reason_key` (`write_failed`, no
   exception text), then return it.
5. Change `tests/test_agent_service.py:435` so it compares the receipts' action names with the
   proposal (finding 5).
6. Finding 7: remove the lane codes and the semicolon from the labels (keep the lane in a separate
   field, for example `replaced_by`), or record a hand-back to DOCK-2 in the packet.
7. Record the observations' hand-backs (Firestore rules, the editors rule) in the packet's table for
   DOCK-5. Rerun the verify, the full suite, scope and checks, and paste the results.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent of the author; 2026-10-18)

| Field | Value |
|---|---|
| Task | DOCK-3, rework round 1 |
| Branch | `task/DOCK-3` |
| Commit | `6234850b` |
| Base | `414a37ee` (round 1 head) for the rework diff; the branch now carries `task/DOCK-1` at `c34b2c57` and origin/main `8d20c523` |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author |
| Verdict | **accept** |

I read `git diff 414a37ee..6234850b -- src/agent tests/test_agent_store.py tests/test_agent_service.py
tests/test_agent_fakes.py docs/work/desk-agent-and-book-2026-10-18/dock-3.md` in full. DOCK-1's own
files are reviewed elsewhere.

### Commands run and results (round 2)

| Command | Result |
|---|---|
| `python3 -m unittest tests.test_agent_fakes tests.test_agent_service tests.test_agent_store` | `Ran 75 tests in 0.092s`, **OK** |
| `python3 scripts/plan.py check && python3 -m unittest discover -s tests -p "test_*.py"` | `OK: 135 tasks, 9 gates`; `Ran 2789 tests in 169.384s`, `FAILED (failures=4, errors=10, skipped=115)`. The 14 are exactly the expected reds: 13 in `test_grid_ask_page` (the view.v3 pins) and `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag`. Both are inherited from `task/DOCK-1` and close with DOCK-2 and the VIEW_RECEIPT_KEYS commit at merge. No other module fails, and no agent test fails |
| `python3 scripts/plan.py scope DOCK-3 task/DOCK-1` | `OK: all changed files inside DOCK-3 allowed paths` |
| `python3 scripts/repo.py check` | `Checked 606 Markdown files, 3852 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check 414a37ee..6234850b` (and the task's files from `971885b0`) | clean |
| Real archive `verify()` and file `sha256` before and after the suite and probes | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`; all 5 files unchanged |
| Probe scripts (scratchpad, scratch archives) | results below |

### Round 1 findings, re-checked

| Round 1 finding | Status | Evidence |
|---|---|---|
| 1 (major), executor ran handles | **closed** | `proposed_actions` (`src/agent/service.py:150`) reads `receipt.actions.proposed[i].resolved`, records `refused[{index, reason_key}]` as refused receipts that never run, and reads the plan's args only without a block. `DockOneShape` runs through the real `view.answer_question` with handles in the plan: the archive gets `(rules:billing_month_clock, 016ae92)`, `rests_on` holds the record id, and no handle appears in any receipt. The composer-refused `open` is `refused argument_not_in_manifest` with no result. The anonymous ask on the same plan stores nothing. Probes: a refused entry that still carries `resolved` (`needs_sign_in`) is not run and parks no confirmation, and `resolved: None` with no refusal is refused |
| 1, `_flags` and DOCK-1's tuple `writes` | **closed** | `catalogue.load()` with the real `src/judgment/actions.py` returns `src.judgment.actions`. The flags equal the module's: `writes` is false only for `open`, `query_exposure`, `query_impact`. Tested (`test_reads_dock1s_real_module_without_falling_back`) and probed |
| 2, confirmations parked that cannot run | **closed** | `_preview` refuses a revision outside `[0-9a-f]{7,40}` (`argument_not_in_manifest`) and an assumption no issued outlook cites (`no_record`) before any confirmation exists (`RefusedBeforeTheClick`) |
| 3, no-owner guard | **closed** | `:345` allows only `PUBLIC_READS` without an owner, whatever the table says, and `:388` refuses every private write without an owner (`NoOwnerNoPrivateWrite`, nothing stored) |
| 4, write errors | **closed** | `confirm` catches any exception after the decision and records `refused`, `write_failed`, under the receipt id the preview named. The test checks that no exception text reaches the store (`ValueError`, `OSError`, `RuntimeError`) |
| 5, latent test | **closed** | the test now compares action names |
| 6, meter | **closed** | `charge` and `today` turn any store error into `budget_unavailable` (tested with `RuntimeError`; no exception text in the outcome) |
| 7, labels | **closed** | no lane codes, no semicolons, no "stale" in any fake label or the card line (new test) |
| reason-key spelling | **closed** | `argument_not_in_manifest` everywhere (`ARG_REFUSED`) |

### Attack checks on the new head

| Check | Result |
|---|---|
| (a) No write without `confirmed` | Holds. A forged document stored already `confirmed` is refused `AlreadyDecided` with 0 marks. Another uid gets `UnknownRecord`. A confirm body with `args` gets `InvalidInput`, and an edited copy leaves the stored args unchanged. A replay gets `AlreadyDecided` and leaves 1 mark. `_execute_write` is still the only caller of a writing API (syntax-tree test) |
| (b) Unsigned requests | Holds. An anonymous ask uses the recorded planner even with a live planner configured (probe: `synthetic_fixture`, `budget: None`). The composer gets `signed_in=False` and refuses writes itself, and the executor's own guard refuses them again |
| (c) Budget | Holds. With the real composer and a metered planner: a recorded question charges 4 calls (0.08 USD). The ask past the line is `refused`, `budget_exhausted`; the recorded plans answer and the day stays at 4 calls. At 16:00Z a new Manila day (2026-10-19) starts. `_BudgetRefused` passes through `answer_question` to the fallback (probed through the real composer) |
| (d) Privacy | No `logging`, `warnings`, `print` or exception text in `src/agent`. The new `except Exception` handlers record fixed keys only. Owners are still digests |
| (e) Imports | New imports are only `open_cases` and `thread_id` from the package itself. The allowlist test passes |
| (f) Fakes | `synthetic: True` and a label on every fake (test) |
| (g) Routes | Seven routes, including `GET /api/agent/cases` (signed in), built as before. No `src.agent` import outside the package, so not mounted |
| (h) Catalogue | See finding 1 above: the real module is read, and the fallback test still passes |

**API shapes the dock assumes: all present** (`ApiShapes` tests and my reading).
- `POST ask` returns the turn's fields plus `view`, `confirmations` and `budget` (with `refused`). Each confirmation is `{confirmation_id, action, args, preview{what, where, receipt}, state, decided_at}`.
- `GET threads` returns `{threads, cases, budget}`.
- `GET queue` returns `{items, budget}`.
- `POST confirm/{id}` returns `{confirmation_id, state, decided_at, receipt}`.
- `GET /api/agent/cases` returns `{cases}`.

**Budget judgement (no finding).** The executor charges zero for a question the composer answers
`insufficient` before planning. I accept this: the meter bounds live spend, and no live call runs in
that case. A question that does reach the planner is charged its forms before the call: 4 for a
recorded question, 3 repeats for a free one.

### Findings (round 2)

1. **minor (copy, hand to DOCK-2).** `src/agent/service.py:456`. The `mark_stale` preview's `what` reads "a
   stale mark beside each of …". The dock shows it on the confirmation card. The panel's copy rule
   (`tests/test_grid_ask_page.py:650`) bans "stale" in the panel's sentences. Either DOCK-2 renders its
   own sentence from `outlooks`, or this string changes (for example "a mark beside each of … that its
   belief changed"). This does not block.
2. **nit.** `src/agent/service.py:575`. If the preview-named receipt id already exists, the execution
   receipt is written under a new id, and `preview.receipt` then names the wrong receipt. This cannot
   happen with uuid4 ids.

Observations:
- Queue items have no `kind` field, and the dock tells them apart by their keys (documented in the
  packet).
- The packet links to `../reviews/DOCK-3.md`, which is uncommitted in the worktree. Commit this
  record with the merge, or `repo.py check` fails on the committed tree.

### Verdict

**accept** for `6234850b`. Every acceptance line is proved by a test I ran:
- line 1: `ConfirmedActionIsTheDecision`, `NoWritePathWithoutConfirmation`, `RefusedBeforeTheClick`;
- line 2: `FreeAndWritingActions`, `DockOneShape`, `NoOwnerNoPrivateWrite`;
- line 3: `BudgetOutcome`, `NothingLogged`;
- line 4: `test_agent_fakes`;
- line 5: the suite is green apart from the 14 expected reds inherited from DOCK-1, with no live call.

The round 1 major finding is closed through the real composer, and no major finding stands. The two
remaining items are a copy hand-back to DOCK-2 and a nit.
