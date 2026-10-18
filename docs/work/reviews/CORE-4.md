# Packet: CORE-4 — S4 cutoff pairing backend and API

Executor packet and self-review, 2026-10-12. Author: the executor seat; this is **not** an
independent review and sets no verdict — only a reviewer writes the review section. Task
[brief](../tasks.json) CORE-4, lane CORE, milestone M3, branch `task/CORE-4`, base `7575cbd`
(parent `task/CORE-2`, which sits on `feat/h1-api-persistence`). Interpreter
`/usr/bin/python3` (Python 3.14.4); the emulator suite runs through `.local/h1-venv/bin/python`
inside `scripts/h1/test.sh`. No model, transport, credential, service or network call is made
by any command below or by the code this task adds: the paired artifacts are saved by the
labelled `FixtureSystemOne` test double and the route only reads them back.

## Outputs

| Output (brief) | Where |
|---|---|
| `pair(before_ref, after_ref)` derived view | `src/review/pairing.py:118` — `pair(repository, actor, case, before_ref, after_ref)`; the pure derivation is `_view` at `:86` |
| `GET /probe-bundles/pair` registered from `src/api` via an additive import | `src/review/pairing.py:148` — `register_pair_route(app, prefix, repository, actor)`, which owns the route; `src/api/__init__.py:18` adds the import and `:214` the one registration call |

The whole operation is reads through the repository's public `read` port — the port
`PersistentRepository` already publishes — so the route works behind the emulator adapter
with no allow-list change in `src/review/storage.py` (outside this task's allowed paths).
`tests/test_pairing.py:159` pins that property through a facade that exposes `read` alone.

## Acceptance

| Acceptance item (brief) | Exact check | Result |
|---|---|---|
| `changed` lists differing questions; `new_passages` lists the later passage | `tests/test_pairing.py:139` `test_changed_lists_the_differing_questions_and_new_passages_the_later_passage`: two tasks share one snapshot at cutoffs `2026-10-05T02:00:00Z` and `2026-10-07T00:00:00Z`, the later task carrying a second source the earlier cannot (`context` lengths 1 and 2); the view's key set is exactly the six frozen keys, `changed == ['q3_time', 'q6_observation']`, `new_passages == [reference(later passage)]`, labels `challenges`/`challenges`, refs echoed. Emulator `test_pair_route_returns_the_diff_lists_the_new_passage_and_writes_nothing` repeats it end to end through the route | Pass |
| Different assumption, different snapshot or wrong cutoff order rejected with typed codes | `tests/test_pairing.py:198` (`PAIR_ASSUMPTION_MISMATCH`), `:205` (`PAIR_SNAPSHOT_MISMATCH`), `:191` (`PAIR_CUTOFF_ORDER`: the pair swapped, and two bundles on one task with equal cutoffs), plus `:211` (`PAIR_NOT_A_BUNDLE`) and `:214` (`PAIR_NO_ATOMIC_ANSWERS`); the emulator case asserts the 422 bodies `{'code': ...}` for equal cutoffs, a task reference, a malformed query value (shared `INVALID_RECORD`) and an absent reference (404 `NOT_FOUND`) | Pass |
| No write occurs | Every offline case compares all eight reference-store tables (`records`, `latest`, `cases`, `heads`, `outlooks`, `history`, `receipts`, `stale`) before and after the call, refusals included; the emulator cases compare `encode(state())` — all nine tables, `http_receipts` included — before and after the route call, so the GET commits nothing through the Firestore adapter and the generator does not move | Pass |

Readings inside the frozen text, the decisions they rest on and what is deliberately not
in the view are in [implementation.md](../probe-bundle/implementation.md), "S4 cutoff pairing
backend and API". The three worth the reviewer's eye: (1) the intent's S4 row names a
"repository pair method" and this is a module function over the public `read` port instead,
because a new repository method would need the `execute` bridge or a `storage.py` allow-list
entry and `storage.py` is outside the allowed paths; (2) the pair codes live in `pairing.py`
as a `ReviewError` subclass because `src/review/errors.MESSAGES` is outside the allowed
paths, and the app's existing handler answers them 422 (the intent fixes no status); (3)
assumption equality is `assumption_ref['record_id']` — the `assumption_id` the compiler keys
a task by — so two revisions of one assumption still pair.

## Executed verification

All commands run on `task/CORE-4` after the code, tests and this packet were final; none
touches the network. Rows measured with the packet present and the working tree otherwise
final.

| Command | Result |
|---|---|
| the brief's verify: `/usr/bin/python3 -m unittest tests.test_pairing -v` | `Ran 10 tests in 0.225s` — `OK` (10 passed, 0 failed) |
| the full offline suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 288 tests in 2.111s` — `OK` (278 before this task) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` — `Checked 252 Markdown files, 1113 local links, 8 skills; bootstrap 1293 words.` (re-run after this packet and the PROGRESS log entry were written; the same command before the packet existed reported `251 Markdown files, 1107 local links` and the two links into this not-yet-written file as broken) |
| `/usr/bin/python3 scripts/plan.py scope CORE-4 task/CORE-2` | `OK: all changed files inside CORE-4 allowed paths` |
| `/usr/bin/python3 scripts/plan.py scope CORE-4 feat/h1-api-persistence` | lists exactly one path, `docs/work/reviews/CORE-2.md` — the parent branch's review record, carried by the stacked branch and not part of this task (below) |
| `bash scripts/h1/test.sh` (emulator suite, the brief's S4 check) | `Ran 68 tests in 31.100s` — `OK`, `✔ Script exited successfully (code 0)` (66 before; both new cases ran and passed: `test_pair_route_returns_the_diff_lists_the_new_passage_and_writes_nothing`, `test_pair_route_refuses_typed_and_malformed_queries_without_writing`) |

The emulator suite ran twice on this tree with identical results (`Ran 68 tests in 31.822s`
before the last offline case and the documentation edits, `31.100s` after); neither run
altered a record outside the test's own random namespace.

### Post-commit re-run

The same commands were re-run on the committed tree at `31c07b9` with the working tree
clean: `/usr/bin/python3 -m unittest tests.test_pairing` → `Ran 10 tests in 0.225s` `OK`;
`/usr/bin/python3 -m unittest discover -s tests` → `Ran 288 tests in 2.077s` `OK`;
`plan.py check` → `OK: 41 tasks, 7 gates`; `repo.py check` → `Checked 252 Markdown files,
1113 local links, 8 skills; bootstrap 1293 words.` `PASS`; `plan.py scope CORE-4 task/CORE-2`
→ `OK: all changed files inside CORE-4 allowed paths`; `plan.py scope CORE-4
feat/h1-api-persistence` → the same single stacked-branch path, `docs/work/reviews/CORE-2.md`;
`bash scripts/h1/test.sh` → `Ran 68 tests in 32.524s` `OK`, `✔ Script exited successfully
(code 0)`, log `.local/core4-final.log` (ignored local file). This follow-up commit changes
this packet alone.

### Scope note (stacked branch)

`CORE-4` is stacked on `task/CORE-2`, which is stacked on `feat/h1-api-persistence`. The
allowed set is the brief's: CORE-4's own paths plus CORE-2's and CORE-1's owned paths, the
two coordination files and `docs/work/reviews/CORE-4.md`. Every path this task touches is in
that set (verified against the parent branch: `scope CORE-4 task/CORE-2` prints OK). The
three-dot diff against `feat/h1-api-persistence` also carries the parent's review record
`docs/work/reviews/CORE-2.md`, which the CORE-2 accept commit wrote on the stack; CORE-4's
allowed set contains only its own record, so `scope` against that older base reports that one
path and cannot print OK from inside this task's allowed paths. Nothing in this task writes
or edits it.

## Stop conditions

None fired. No change outside the allowed paths was needed; no acceptance text, frozen
contract, payload key, metadata key or existing test changed; the work adds no runtime
dependency, SDK, service, credential or network call (the route and the pairing module import
no HTTP framework at module scope, and `fastapi` is imported inside `register_pair_route`
only, so the stdlib suite still imports the module on `/usr/bin/python3`); no model call,
cloud write, deployment, publication, push or merge occurred; effort stayed inside the
estimate; no test was weakened, skipped or deleted — the offline suite grew 278 → 288 and the
emulator suite 66 → 68; and every value in the recorded views comes from a record: the
fixture backends' validated answers, the composed results and the compiled tasks.

## Self-review (executor seat, not a review)

- Both brief outputs exist and are wired: the derived view and the route, registered from
  `src/api` by adding one import and one call next to the existing probe-bundle route. No
  existing route, handler, signature or frozen behaviour was touched.
- All three acceptance items have a named, executed check (table above) and pass, on both the
  reference adapter and the emulator adapter. The two emulator cases run the real API through
  `PersistentRepository` over Firestore and compare the whole encoded store before and after,
  which is the strongest available offline proof that the pair view writes nothing.
- Weak spots for the reviewer: reading (1) above — the intent's "repository pair method" is a
  module function here, for the scope reason given; the choice to keep the view to the frozen
  six keys, so it carries no cutoffs and no per-form detail; the 422 status the existing
  handler gives the pair codes; `PAIR_NO_ATOMIC_ANSWERS`, which the service itself cannot
  produce (a render refusal is a result, not a record) and which is pinned through a
  read-port double with a hand-built record; and the pair of saved history being derivable
  after a later mapping revision stales the drafts (`tests/test_pairing.py:169` pins that
  reading).
- Two defects appeared while writing the first draft and were fixed before any recorded run:
  the pair conditions first went through the core `require`, whose `MESSAGES` lookup has no
  pair code and raised `KeyError` instead of the typed refusal, so they now raise
  `PairingError`; and the integration test's docstring claim about which tables it compares
  was checked against `encode()`'s `TABLES` before being written down. No product behaviour
  changed for either, and no test expectation was moved to match a defect.
- Untested by this task, recorded rather than implied: the workspace rendering of the pair
  (UI-1's half of the S4 row), any live backend (S3/S5), and the `PersistentRepository`
  allow-list cleanup in `src/review/storage.py` (outside the allowed paths).

## Limits, unfinished items and next action

- This is the executor's self-review record, labelled as such. The task state is
  `in_progress` in [tasks.json](../tasks.json) and in the [PROGRESS](../PROGRESS.md) table,
  with one log entry; only an independent reviewer may set `done` with an accept record.
- Unfinished and where it belongs: the workspace pair view and its browser check (UI-1);
  `bundle_input`, `bundle_lineage_prior`, `save_bundle` and the pairing reads joining the
  `PersistentRepository` allow-list in `src/review/storage.py` (two-line cleanup, still
  outside every task's paths so far); S3 (CORE-3) and S5 (fixtures and offline evaluation);
  `docs/work/probe-bundle/work.json` still declares phase `intent`.
- Exact next action: independent review via `bash scripts/seats/reviewer.sh CORE-4`, on
  `task/CORE-4`, re-running the brief's verify command, the full offline suite, the emulator
  suite and `plan.py scope CORE-4 task/CORE-2`; the reviewer's eyes are asked for the three
  readings above.

## Designated review (GPT Astra, independent, commit `3756cf7`, 2026-10-12)

> Independent review of `3756cf7` against `task/CORE-2`, including both commits (`5702d5c`, `3756cf7`). Working tree was clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** All 10 pairing tests passed: differing questions, later passage, assumption/snapshot mismatches, reversed/equal cutoffs, and unchanged store on successful and rejected calls. |
> | 2 | Allowed paths only | **Yes.** Requested `scope CORE-4 task/CORE-2` printed `OK`. |
> | 3 | Frozen contracts and tests preserved | **Yes.** Diff adds pairing and route registration; no frozen contract, acceptance text, or existing test was weakened or removed. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Pairing uses repository reads and existing dependencies; no backend invocation or write operation added. |
> | 5 | Truthful mode labels | **Yes.** Tests explicitly use synthetic fixtures; no live-inference claim in the implementation. |
> | 6 | Unknowns preserved | **Yes.** Results derive from saved atomic answers and task passage references; no new case facts or receipts are inferred. |
> | 7 | Complete verification and handoff record | **Yes, with a minor provenance issue below.** Packet includes interpreter, commands, results, limitations and next action. |
> | 8 | Domain and direction consistency | **Yes.** Pairing preserves transitive access checks, requires matching assumption/snapshot and increasing cutoffs, and produces a derived view without changing accepted assumptions. |
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 -m unittest tests.test_pairing -v` — **10 passed**.
> - `/usr/bin/python3 scripts/plan.py scope CORE-4 task/CORE-2` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **290 passed**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 42 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> `bash scripts/h1/test.sh` was attempted but failed before tests started: sandbox loopback binding returned `EPERM`. An additional in-process API smoke check hung and was interrupted; it supplies no verification evidence. HTTP/Firestore integration was therefore **not independently demonstrated in this review**.
> 
> Findings:
> 
> minor | `docs/work/reviews/CORE-4.md:65` | Verification provenance does not identify the current reviewed revision clearly | Packet attributes its post-commit checks to `31c07b9` and reports 288 tests/41 tasks; reviewed HEAD is `3756cf7`, with 290 tests/42 tasks | Preserve historical results as historical and append the current revision’s verification and sandbox limitation.
> 
> **Verdict: accept** — All three brief acceptance items were demonstrated by executed tests, and no blocking or important implementation finding was identified.
**Verdict: accept.** Stacked on CORE-2; merges into the integration branch only after CORE-2 is done.

## Orchestrator note (rebase onto CORE-2 rework 4, 2026-10-12)

`task/CORE-4` was rebased onto `task/CORE-2` at `41fbd2f` (`git rebase --onto task/CORE-2 16c1e8d`); the only
conflicts were PROGRESS.md and the shared packet, resolved by keeping both sides. No source or test file changed in
the rebase; full suite OK (292 tests), `plan.py scope CORE-4 task/CORE-2` OK, `plan.py check` OK, `repo.py check` PASS.
The designated accept verdict above stands; CORE-4 merges after CORE-2.

## Designated review (GPT Sol, independent, commit `6044362`, 2026-10-13)


## Designated review (GPT Sol, independent, commit `6044362`, 2026-10-13)

> Independent review of `60443623427b` against `task/CORE-2`. Inspected the three-dot diff and all four branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Executed all 10 pairing tests: differing questions, later passage, assumption/snapshot mismatches, reversed/equal cutoffs, and unchanged store on success/refusal. |
> | 2 | Allowed paths only | **Yes.** `scope CORE-4 task/CORE-2` printed OK; all eight changed files are allowed. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff adds pairing, route registration and tests; frozen files and existing test assertions remain unchanged. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Pairing uses existing imports and repository reads; no backend call or write added (`pairing.py:118–131`). |
> | 5 | Truthful mode labels | **Yes.** Tests explicitly use `FixtureSystemOne`; no live-inference result claimed. |
> | 6 | Unknowns preserved | **Yes.** Labels, atomic answers and passage references come from saved records (`pairing.py:96–115`); revoked-source access is tested. |
> | 7 | Verification and handoff recorded | **Yes, with a minor inconsistency below.** Packet records interpreter, commands, results, limitations and next action. |
> | 8 | Direction and domain invariants preserved | **Yes.** Matching assumption/snapshot and increasing cutoffs are enforced; transitive access remains intact; the view changes no accepted state. |
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 -m unittest tests.test_pairing -v` — **10 passed**.
> - `/usr/bin/python3 scripts/plan.py scope CORE-4 task/CORE-2` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **292 passed**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 42 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `bash scripts/h1/test.sh` — failed before tests started because sandbox loopback binding returned `EPERM`; HTTP/Firestore integration was **not independently verified**.
> 
> Finding:
> 
> minor | `docs/work/reviews/CORE-4.md:130` | Resume instructions describe obsolete task state | Section says state is `in_progress` and independent review is next, while tasks.json, PROGRESS and the later review section mark it done | Label this section as historical executor handoff and state the current next action.
> 
> **Verdict: accept** — All brief acceptance items were demonstrated by executed tests, with no blocking or important finding.
**Verdict: accept.** Orchestrator ran scripts/h1/test.sh at 6044362: 69 tests OK (reviewer sandbox had no loopback).
