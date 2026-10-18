# Packet: CORE-9 — h0.v2 records: real records with a permission reference, typed availability basis, judgment reference

Task `CORE-9` (lane CORE, milestone M4), route implement, executor agent, on `task/CORE-9`
stacked on `task/CORE-4` (which carries CORE-2 and CORE-3), base of this branch's own work
`d9bb808` on top of `6044362`. Intent [h0-v2/intent.md](../h0-v2/intent.md); the intent names
`docs/work/h0-v2/` as the packet directory, and this record follows the CORE-2/CORE-4
convention of a per-task record under `docs/work/reviews/`, with the summary section appended
to [probe-bundle/implementation.md](../probe-bundle/implementation.md).

Interpreter `/usr/bin/python3` (Python 3.14.4). Every command below is offline: no model,
transport, credential, service or network call is made by the code under test or by any
command in this packet. The emulator suite runs the two loopback Firebase emulators only.

**State: `in_progress`, blocked on one owner decision.** The implementation is complete and
every acceptance item that this task's allowed paths can reach is met and run; one acceptance
item — the offline suite green — is **not** met, because the h0.v2 typed basis refuses a
single legacy line in `src/demo/__init__.py`, a file **outside the allowed paths printed by
`plan.py brief`**. Per the brief's stop conditions this was recorded and handed back rather
than worked around; the exact one-line change and the decision needed are in
[Stop conditions](#stop-conditions) below.

## What changed

| File | Change |
|---|---|
| `src/review/records.py` | h0.v2 envelope: `make_record` writes `h0.v2`, `validate_record(raw, permissions=None)` accepts `h0.v1` and `h0.v2` and validates a v1 record by the unchanged v1 rules. Adds `provenance(payload, permissions)`, `typed_basis(value)`, `load_permissions(root)`, the three v2 codes (`PERMISSION_UNKNOWN`, `CASE_PROVENANCE_MISMATCH`, `JUDGMENT_TASK_MISMATCH`) with their own message table, `SCHEMA_VERSION`/`SCHEMA_VERSIONS`/`BASIS_KINDS`, and the v2 branches: the pair on every kind, the typed basis on `SourceVersion`, the optional `judgment_ref` on `ReviewDecision` |
| `src/review/repository.py` | `ReviewService.__init__(permissions=None)` holds the registry (`DEFAULT_PERMISSIONS` read once from the checkout at import); `_record`, `_pair`, `_pair_fields` and `_check_provenance` wrap every write; `_preflight` validates under the registry and refuses a record whose pair differs from its case's; every derived write (snapshot, compiled task, judgment, bundle, decision, assumption, outlook, proposal, dependency impact) copies the case's pair instead of the literal `True`; `_validate_review_request` accepts the optional `judgment_ref`; `_review_guards` resolves it (`_resolve_judgment_ref`) on every call, so the reference is re-read under the commit lock; the workspace view reports the case's pair |
| `src/api/__init__.py` | `ReviewBody.judgment_ref: dict | None = None`; the domain-error handler maps the three new codes (409 for `JUDGMENT_TASK_MISMATCH`, 422 otherwise) |
| `src/review/README.md` | The h0.v2 envelope and the three rules, one paragraph each |
| `tests/test_review_case.py` | The source helper's basis becomes the typed object; a new `H0V2Case` class of 11 cases: the real case end to end, replay/conflict, the judgment reference, the signed-permission refusals, the registry loader, mixed cases both ways, the undeclared pair, the basis forms, the synthetic-fixture mode, the frozen corpus |
| `tests/test_probe_bundle.py` | Two assertions that encoded the v1 payload shape for a saved bundle: the artifact's key set gains `permission_ref` (still an exact set), and `rejected(synthetic=False)` now expects the h0.v2 code `PERMISSION_UNKNOWN` rather than `INVALID_RECORD` — the same refusal, the more precise code — with two further pair refusals added beside it. Nothing else in that file is touched; CORE-8 re-freezes it |
| `tests/integration/test_probe_bundle_api.py` | One emulator case: a review that cites a saved `ProbeBundleArtifact` through `ReviewBody`, the recorded reference and the replay, and the typed refusals for another task's artifact, an absent reference and a malformed one |

No fixture, bundle, workspace, adapter, storage or `src/review/errors.py` file is touched, and
no frozen contract changes: the two closed payload key sets stay closed, the API's existing
routes and handlers are untouched, and `src/review/storage.py`'s tables and codec are
untouched.

## Implementation decisions inside the stated contracts (for review)

1. **The pair is read as declared; an undeclared pair is the synthetic default.** `provenance`
   reads `synthetic = payload.get("synthetic", True)` and `permission_ref =
   payload.get("permission_ref")`, so a payload that declares nothing is synthetic with a null
   reference — exactly the pair every h0.v1 write hard-coded — while a payload that declares
   `synthetic: false` must cite a non-blank identifier the registry holds
   (`PERMISSION_UNKNOWN` for null, unknown, blank and unsigned), and a synthetic payload
   carrying a reference is the mixed case and is `INVALID_RECORD`. Requiring the keys to be
   *present* was rejected for one reason: `make_record` now writes the v2 envelope for every
   caller, and the only callers that omit the pair are `src/demo/__init__.py` (consumed by
   `tests/test_judgment.py`, `tests/test_probe_bundle.py`, `tests/test_pairing.py`,
   `tests/test_gemini_transport.py`, `tests/integration/test_gemini_wire.py`,
   `scripts/m3/seed.py`, `src/adapters/gemini/run.py`) and those files are outside this task's
   allowed paths. Nothing is weakened by the reading: the repository writes the pair
   explicitly on every record it creates, and `_check_provenance` refuses any record whose
   effective pair differs from its case's (`CASE_PROVENANCE_MISMATCH`), so a real case cannot
   ingest an undeclared record. Pinned by
   `test_an_undeclared_pair_reads_as_the_synthetic_default` and
   `test_no_mixed_case_is_stored_in_either_direction`.
2. **The three v2 codes carry their own messages (`RecordError`, `V2_MESSAGES`).**
   `src/review/errors.py` owns the frozen h0.v1 `MESSAGES` set and is outside the allowed
   paths, so the codes live in `records.py` and are raised through `require_v2`; the
   application's existing handler answers them as `{'code': …}` exactly like every other
   `ReviewError`. This follows CORE-4's `PairingError` precedent.
   **Consequence, recorded as an unfinished item:** the intent's sentence "the error code
   `INVALID_RECORD` text becomes *record does not satisfy h0.v1 or h0.v2*" needs
   `src/review/errors.py`, which is not in this task's allowed paths, so the text is
   unchanged. No acceptance item depends on it.
3. **`JUDGMENT_TASK_MISMATCH` answers 409, the permission codes 422.** The intent fixes no
   status. A decision naming another task's artifact conflicts with recorded state, like a
   stale head (`STALE_HEAD`, 409); a record whose provenance its case refuses, or that cites
   no signed permission, is not an acceptable record (422). Pinned by the emulator case.
4. **The judgment reference is validated in two places, deliberately.** The validator fixes the
   shape of `judgment_ref` (a typed reference, `INVALID_RECORD` otherwise) and does not read
   the store, so a saved record never needs a registry or a second record; the repository
   resolves it inside the review transaction — `_review_guards` runs in `_prepare_review` and
   again in `_commit_prepared`, and each call re-reads the artifact — so a reference revoked
   or replaced between preparation and commit is denied at commit, and the reference is part
   of `compute_content_digest(request)`, which is the idempotency digest, so the same key with
   a different reference is `IDEMPOTENCY_CONFLICT`. Kind and task are the only things checked;
   the reference changes no disposition ("recorded, never interpreted").
5. **`_check_provenance` sits in `_preflight`, the single write gate.** `_write` preflights its
   whole batch before the first write, so a mismatch stores nothing; `register` also checks the
   caller's record immediately after validating it, so the code does not depend on which deeper
   binding check runs first. The Case itself is exempt — it defines the pair for the case.
6. **The registry is read once per process and injected, never re-read per call.**
   `DEFAULT_PERMISSIONS = load_permissions(<checkout root>)` at import; `ReviewService(
   permissions=…)` lets a test inject one, and `make_record`/`validate_record` take the registry
   as an argument. `load_permissions` parses the `Status:` line's leading word (Markdown
   emphasis stripped, so `**draft, unsigned**` reads as `draft`) and the backticked value on
   the `Permission identifier` line, and ignores a signed file whose identifier does not parse
   — citing it stays refused. Today the checkout's registry is **empty**: the one file under
   `docs/work/permissions/` is the owner's unsigned draft, so no real record validates anywhere
   in this checkout, which is what the intent asks for until the owner signs it.
7. **No new storage state.** The case's pair is derived from the registered Case record on
   demand (`_pair`), so `src/review/storage.py`'s nine `TABLES` and the decode/encode codec are
   untouched and a `PersistentRepository` transaction behaves exactly as before. The
   consequence to know: a decoded store uses the checkout's registry, because the registry is a
   property of the checkout rather than of case state — which is also the fail-closed direction
   for the deployed adapters.
8. **The `execution_mode == 'synthetic_fixture'` rule is applied to `JudgmentArtifact` only,
   as the intent states it.** `live_inference` is accepted for synthetic and real cases alike.
   Pinned by `test_a_synthetic_fixture_execution_mode_is_refused_on_a_real_case`.
9. **A v2 record with `known_at: null` must not carry a basis.** The object exists "when
   `known_at` is set", so a non-null basis without availability is a contradiction rather than
   a note; `INVALID_RECORD`. The v1 branch is untouched: the string form is still what a v1
   envelope requires, and a v1 envelope still refuses an object basis and a real pair.
10. **The two closed key sets stay closed.** `JudgmentArtifact` and `ProbeBundleArtifact` accept
    exactly their frozen v1 key set, or that set plus `permission_ref` under h0.v2; any other
    key is still `INVALID_RECORD`, so the frozen payload and metadata contracts hold.
11. **The API test cites a saved `ProbeBundleArtifact`.** A review may name either artifact kind
    (CORE-2 is an ancestor of this branch); citing the bundle keeps the emulator case free of any
    provider, and the offline case cites a `JudgmentArtifact` through `save_judgment`, so both
    kinds are covered without a model or backend call.

## Acceptance

| Acceptance item (brief) | Exact check | Result |
|---|---|---|
| Real records refused without a signed permission and accepted with an injected registry | `H0V2Case.test_real_records_are_refused_without_a_signed_permission` (null, `perm:never-signed`, blank ⇒ `PERMISSION_UNKNOWN`; a synthetic payload carrying a reference ⇒ `INVALID_RECORD`), `test_a_real_case_needs_a_registry_the_repository_holds` (a repository without the grant refuses the case and stores nothing), `test_the_checkout_registry_grants_only_signed_files` (temp directory: a signed file grants its identifier, a drafted file grants nothing), and the whole `H0V2Case` fixture — a real case registered, seeded, compiled, judged, reviewed, revised and proposed under `frozenset({'perm:local-signed:2026-10-13'})` | Pass |
| 25 pairs, 135 h0.v1 records still validate | `H0V2Case.test_the_frozen_probe_bundle_corpus_still_validates`: every record of every `tests/fixtures/probe-bundle/pb-*.json` validates, 25 files, `manifest['pairs'] == 25`, 135 records, every one an `h0.v1` envelope. A hand-built v1 envelope with the string basis also validates (`test_typed_basis_forms_and_the_v1_string`) | Pass |
| `judgment_ref` must match the decision's task | `H0V2Case.test_the_judgment_reference_must_name_this_task_s_artifact` (another task's artifact, the task itself, an absent record id and a wrong digest ⇒ `JUDGMENT_TASK_MISMATCH`; a malformed reference ⇒ `INVALID_RECORD`; the recorded reference read back from the decision and the history) and `test_a_real_case_replays_read_only_and_refuses_a_changed_request_under_one_key` (same key, different reference ⇒ `IDEMPOTENCY_CONFLICT`), plus `test_a_review_records_the_artifact_it_cites_and_refuses_another_task_s` through the app factory, where the refusal answers `(409, {'code': 'JUDGMENT_TASK_MISMATCH'})` | Pass |
| Full offline suite green except the expected fixture digest drift, listed verbatim | **Not met.** `Ran 303 tests … FAILED (errors=69)`; every failure is the same one, rooted at `src/demo/__init__.py:26` under the typed-basis rule (verbatim evidence and the exact one-line change in [Stop conditions](#stop-conditions)). With that one line upgraded in memory — no repository file changed — the same 303 tests run `FAILED (failures=1)`, the single failure being `test_typed_basis_forms_and_the_v1_string`, whose purpose is to require the string basis to be refused and which that in-memory patch rewrites. The expected fixture drift is also larger than "digest drift": `build.py --check` now raises before it can report a digest, because the builder's own sources carry the v1 string basis (verbatim below); that file is CORE-8's, whose intent re-freezes the fixtures under h0.v2 | Fail — stop condition, handed back |

## Executed verification

All commands run in this worktree on the working tree that this commit contains, with the
packet present; none touches the network.

| Command | Result |
|---|---|
| the brief's verify: `/usr/bin/python3 -m unittest tests.test_review_case -v` | `Ran 54 tests in 0.685s` — `OK` (43 before this task; 11 new) |
| the full offline suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 303 tests in 1.581s` — `FAILED (errors=69)`; `grep -c 'src/demo/__init__.py'` over the same output counts 138 traceback lines, i.e. 69 × 2, one root cause for all of them |
| `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` | raises `src.review.errors.ReviewError: record does not satisfy h0.v1` from `src/review/records.py` `typed_basis` while rebuilding the fixtures (CORE-8's file, its own re-freeze); the frozen files on disk are untouched by `--check` |
| the frozen corpus count | every record of `tests/fixtures/probe-bundle/pb-*.json` validates through `validate_record`: **25 pairs, 135 h0.v1 records** |
| the checkout's registry | `sorted(load_permissions('.'))` → `[]` — the drafted permission record grants nothing, so no real record validates in this checkout today |
| `plan.py check` | `OK: 45 tasks, 7 gates` |
| `plan.py scope CORE-9 task/CORE-4` | lists six paths, all written by the branch's prep commit `d9bb808` before this task ran, none by this task (below) |
| `plan.py scope CORE-9 feat/h1-api-persistence` | the same six paths plus `docs/work/reviews/CORE-2.md` and `docs/work/reviews/CORE-4.md`, also carried by the stack (below) |
| `bash scripts/h1/test.sh` (emulator suite) | `Ran 70 tests in 40.038s` — `FAILED (errors=4)`; all four are `test_gemini_wire.WireTests`, each rooted at `src/adapters/gemini/run.py:23 prepare_case` → `src/demo/__init__.py:26`, the same one line as the offline failures. The other 66 cases pass, this task's new case among them; log `.local/scratch/h1-run3.log` (ignored local file) |
| a local measurement of that one line (no repository file changed) | A scratch runner (`.local/scratch/shim.py`, ignored, not part of the tree) that upgrades the demo's string basis to the typed object in memory only, then runs the same offline suite: `Ran 303 tests in 2.539s` — `FAILED (failures=1)`, and the one failure is this task's own `H0V2Case.test_typed_basis_forms_and_the_v1_string`, which requires a v2 string basis to be refused and which the shim by construction rewrites. So the 69 errors are one legacy line in one unowned file: with it applied, the offline suite is green apart from CORE-8's fixture re-freeze |

### Post-commit re-run

The same chain was re-run on the committed tree at `8504399` with the working tree clean:
`/usr/bin/python3 -m unittest tests.test_review_case` → `Ran 54 tests in 0.673s` `OK`;
`/usr/bin/python3 -m unittest discover -s tests` → `Ran 303 tests in 1.586s` `FAILED
(errors=69)`; `plan.py check` → `OK: 45 tasks, 7 gates`; `repo.py check` → `Checked 269
Markdown files, 1245 local links, 8 skills; bootstrap 1293 words.` `PASS`; `bash
scripts/h1/test.sh` → `Ran 70 tests in 40.223s` `FAILED (errors=4)`, the same four
`test_gemini_wire` cases with the same one root cause (log `.local/scratch/h1-postcommit.log`,
an ignored local file). No code or test file changed between the two runs.

## Stop conditions

**Fired: "a change is needed outside the allowed paths printed by `plan.py brief`."** One
change outside the allowed set is needed for the fourth acceptance item, and it was **not
made**.

The typed basis that the intent mandates — "the v1 string form is accepted only inside a
`h0.v1` envelope" — is refused in every h0.v2 record, and `src/demo/__init__.py:26` writes
exactly that legacy form for its fictional advisory source:

```python
        'availability_basis':'Labeled local fixture','unknown_reason':None,'copied_from':None})
```

`src/demo/__init__.py` is in no task's `owned_paths` (checked against
`docs/work/tasks.json`), is not a coordination file, and is not in this brief's allowed set.
It is consumed by `tests/test_judgment.py`, `tests/test_probe_bundle.py`,
`tests/test_pairing.py`, `tests/test_gemini_transport.py` (offline) and
`tests/integration/test_gemini_wire.py` through `src/adapters/gemini/run.py`, and at runtime
by `scripts/m3/seed.py` and `src/adapters/gemini/run.py`. The one line that fixes all of it,
ready for an owner or an amended brief to apply (the two in-scope assertion updates in
`tests/test_probe_bundle.py` are already made and are not part of this diff):

```diff
-        'availability_basis':'Labeled local fixture','unknown_reason':None,'copied_from':None})
+        'availability_basis':{'basis_kind':'attested','basis_ref':'Labeled local fixture, 2026-10-01','note':''},'unknown_reason':None,'copied_from':None})
```

`'attested'` is the right kind on the demo's own terms: the fictional seed is asserted by the
walkthrough's operator, not by a feed, a capture log or an archive. Decision needed, either
way one commit: **(a)** amend `CORE-9`'s `owned_paths` (or authorize the edit in this task) so
the executor applies the line, re-runs the suite and requests review, or **(b)** apply it from
the orchestrator/owner seat and let the review compare this packet's evidence. Nothing else in
this task depends on the outcome; the four h0.v2 rules behave identically either way.

Two smaller out-of-scope items, recorded rather than worked around:

1. `src/review/errors.py` is outside the allowed paths, so the `INVALID_RECORD` message text
   stays `record does not satisfy h0.v1` (see decision 2). One line in that file closes it;
   no acceptance item depends on it.
2. `tests/fixtures/probe-bundle/build.py` (CORE-8's) cannot rebuild under h0.v2 until its own
   source payloads use the typed basis — that is precisely CORE-8's "fixtures re-frozen once
   under h0.v2" row, and this task's record is the branch it starts from.

No other stop condition fired: no acceptance text or frozen contract was changed; no runtime
dependency, SDK, service, credential or network call was added; no model call, cloud write,
deployment, publication, push, merge or rebase occurred; effort stayed inside the estimate;
no test was weakened, skipped or deleted — the offline suite grew 292 → 303 and the emulator
suite 67 → 70; and every value in this packet comes from a record or from a command that was
actually run.

### Scope note (stacked branch)

`CORE-9` is stacked on `task/CORE-4` (CORE-2, CORE-3, CORE-1 below it). The allowed set is the
brief's: CORE-9's six owned paths plus its ancestors' owned paths (`src/judgment/bundle.py`,
`src/judgment/systemone.py`, `tests/test_probe_bundle.py`,
`tests/integration/test_probe_bundle_api.py`, `src/review/pairing.py`, `tests/test_pairing.py`,
`docs/work/probe-bundle/implementation.md`), the two coordination files and
`docs/work/reviews/CORE-9.md`. Every path this task changed is in that set: the six modified
files listed under "What changed", this record, and the two coordination rows. `plan.py scope`
cannot print OK from inside this task, because the branch already carried the prep commit
`d9bb808` ("core-9: packet, permission draft, intents and plan rows") when this task started;
its six documentation paths and the two parent review records are what `scope` reports, and
nothing in this task writes or edits them.

## Self-review (executor seat, not a review)

Read against the intent's own words, line by line:

- **Envelope** — `make_record` writes `h0.v2`; `validate_record` accepts `h0.v1` and `h0.v2`
  and runs the v1 rules unchanged for v1 (pinned by the 135 frozen records and by hand-built
  v1 envelopes in `test_typed_basis_forms_and_the_v1_string`); mixed-version references are
  untouched; the `INVALID_RECORD` text is the one line this task cannot reach.
- **Real or synthetic** — the pair is on every kind; `synthetic: true` requires a null
  reference, `synthetic: false` requires a signed identifier; the case fixes the pair and the
  repository refuses a mismatch in either direction; every derived write copies the pair, which
  `test_a_real_case_runs_end_to_end_and_every_record_carries_the_case_pair` checks over *every*
  record the case holds, not a selected list; `synthetic_fixture` is refused on a real case.
- **Typed basis** — the object with its three keys and four kinds, non-blank `basis_ref`, string
  `note`; each kind accepted, the string refused, an unknown kind refused, the v1 form still
  valid in a v1 envelope; a basis never touches `known_at`.
- **Judgment reference** — optional, shape-checked by the validator, resolved and task-matched
  in the transaction, re-read under the lock, in the idempotency digest, exported with the
  decision, on both the record and the API body.
- **Unchanged and asserted by tests** — STALE_HEAD on replay, reviewer equals compiling actor,
  retain writes `no_change`, two cutoffs, omission codes, `consequences: uncomputed`: all
  covered by the 43 pre-existing cases, which pass untouched apart from the source helper's
  basis line. Two assertions in `tests/test_probe_bundle.py` were updated for the v2 payload
  shape (the exact key set gains `permission_ref`; `synthetic=False` with no signed reference
  is `PERMISSION_UNKNOWN` rather than the generic `INVALID_RECORD`) — the same refusals, coded
  as the intent names them; no expectation was weakened, and the offline suite grew 292 → 303
  while the emulator suite grew 67 → 70.

What I would flag to a reviewer as the two judgement calls to attack first: decision 1 (the
undeclared pair reads as the synthetic default) and decision 12-in-effect, the still-red suite,
which is a scope outcome rather than a code outcome.

## Limits, unfinished items and next action

- **Blocked, one line, outside the allowed paths:** the `src/demo/__init__.py` basis (above).
  Until it is applied, the offline suite keeps 69 errors and the emulator suite 4, all with
  that single root cause, and the fourth acceptance item is unmet.
- **Open owner input:** the signature on
  [permissions/2026-10-13-wesm-company-copy.md](../permissions/2026-10-13-wesm-company-copy.md).
  The real path is proven with an injected registry only; no real case, source or decision
  exists in this checkout, and the packet does not claim one.
- **Left to other tasks, deliberately:** the fixture re-freeze and the builder's typed basis
  (CORE-8, whose row already says "fixtures re-frozen once under h0.v2"); the advisory and
  register reader that will consume the v2 shapes (DATA-1); the `INVALID_RECORD` message text
  and the demo line, both needing an allowed path they do not have.
- **Exact next action:** the owner (or the orchestrator) decides between (a) and (b) in
  [Stop conditions](#stop-conditions), applies the one-line basis, and then the executor
  re-runs `/usr/bin/python3 -m unittest discover -s tests` (expect green), `bash
  scripts/h1/test.sh` (expect green), and requests the independent review of this branch; the
  review record belongs in this file, appended under this packet.

## Orchestrator completion of the stop condition (2026-10-13, orchestrator seat)

The executor stopped on files outside its allowed set. The orchestrator widened CORE-9's
`owned_paths` in `docs/work/tasks.json` by `src/demo/__init__.py` and `src/review/errors.py`
(the packet's omission, not the executor's) and applied the four legacy string-basis sites to
the typed basis (`basis_kind: attested`): `src/demo/__init__.py` (the fictional seed),
`tests/test_pairing.py` `add_source`, `tests/test_probe_bundle.py` `restricted_source_tasks`;
and the `INVALID_RECORD` text in `src/review/errors.py` now reads "record does not satisfy
h0.v1 or h0.v2". No validator or repository line changed.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 303 tests in 2.224s` `OK` |
| `bash scripts/h1/test.sh` (emulator suite, tooling linked from the main checkout) | `Ran 70 tests in 33.134s` `OK` |
| `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` | fails with `record does not satisfy h0.v1 or h0.v2` as the intent predicts: the rebuilt envelopes are `h0.v2`; the re-freeze is CORE-8's |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 45 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` |

State stays `in_progress`; the designated review (Sol 6.1) is next. Not pushed.

## Designated review 1 (GPT Sol, independent, commit `59b4b80`, 2026-10-13)

> Independent review of `59b4b8040603` against `task/CORE-4`; inspected the five commits and branch diff. Working tree clean. No files edited.
> 
> Executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_review_case -v` | 54 tests, **OK** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 303 tests, **OK** |
> | `/usr/bin/python3 scripts/plan.py scope CORE-9 task/CORE-4` | **Failed**, seven paths outside scope |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 45 tasks, 7 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` | Failed before digest comparison: `src.review.errors.ReviewError: record does not satisfy h0.v1 or h0.v2` |
> 
> The emulator suite was not rerun; its reported results remain author evidence.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed tests demonstrate permission refusal/injected acceptance, 25 pairs and 135 v1 records, and judgment/task matching; all 303 offline tests pass. The packet lists the fixture-builder exception verbatim, although this is a validation failure rather than demonstrated digest drift. |
> | 2 | All changes within allowed paths | **No.** Scope exits 1, listing bundle-v5 intent, three foundation source profiles, foundation strategy, permission record, and real-sources intent. |
> | 3 | Contracts unchanged; tests not weakened | **No.** Missing provenance fields are accepted in v2, contrary to the intent’s explicit pair requirement. Existing test changes otherwise preserve refusals; no skips/deletions found. |
> | 4 | No unplanned dependency or external effect | **Yes.** Runtime changes use stdlib/local files; no new service, SDK, credential or network path. Imported research documents describe earlier reads, which this review did not execute or verify. |
> | 5 | Truthful mode labels | **Yes.** New test data is explicitly fictional; `synthetic_fixture` judgments are refused for real cases. No new runtime result is presented as live inference evidence. |
> | 6 | Unknowns preserved; no invented facts | **No.** Omitted provenance becomes `(True, None)` rather than remaining undeclared or being refused. |
> | 7 | Complete verification and handoff packet | **No.** Commands, interpreter and results exist, but current status/next-action sections still describe resolved blockers and an unsigned permission. |
> | 8 | Consistent with direction and invariants | **No.** Implicit synthetic classification conflicts with explicit provenance required by the h0.v2 intent; no other evidenced runtime contradiction found. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | `docs/work/bundle-v5/intent.md:1` and six other scope-listed paths | The reviewed range contains changes outside CORE-9’s allowed set, preventing scope closure. | Requested scope command exits 1; the seven paths match the branch diff. | Owner/orchestrator must reconcile the preparation changes with an authorized task boundary, then obtain scope **OK** for the reviewed range. |
> | important | `src/review/records.py:109` | V2 silently accepts absent provenance keys, so exported records can lack the required explicit pair. | `test_an_undeclared_pair_reads_as_the_synthetic_default` passes with both keys removed; judgment/bundle validators also permit omission of `permission_ref`. | Require explicit `synthetic` and `permission_ref` in v2, preserve v1 compatibility, and update callers; any alternate default needs an approved intent revision. |
> | important | `docs/work/tasks.json:1609` | Resume metadata directs work toward an already-resolved blocker and misstates current acceptance evidence. | Note still reports 69 offline errors; packet lines 252–265 request the demo fix and signature, while its appended completion reports green tests and the permission file is signed. | Update current summaries and exact next action to the reviewed tip, retaining earlier failures as dated history. |
> | minor | `docs/work/reviews/CORE-9.md:283` | Fixture failure is attributed to changed envelopes, obscuring its actual cause. | Builder stops at `build.py:620` because a legacy string basis fails `typed_basis`; digest comparison never runs. | Describe the typed-basis validation failure explicitly and distinguish it from later expected digest drift. |
> 
> **Verdict: rework** — scope fails, v2 provenance validation departs from the intent, and current handoff metadata remains inconsistent despite passing offline tests.
**Verdict: rework.** Require explicit synthetic and permission_ref in v2 records (v1 unchanged) and bring the packet and tasks.json note to the current tip. The scope failure is the orchestrator's (intent files from integration); leave it. Address every blocking/important row above; dispose of minors explicitly.

## Rework (executor agent, commit after `0348638`, 2026-10-13)

Rework pass under the verdict above, on `task/CORE-9`, inside the allowed paths. No frozen
contract, acceptance text or review record was edited; the review's sections above stand as
written, and everything the rework supersedes in this packet is stated here, with the earlier
text kept as dated history. `/usr/bin/python3` is 3.14.4; every command below is offline, as
before.

### Disposition of the findings

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | blocking | `plan.py scope` exits 1 on seven paths outside CORE-9's set | **Left, per the review's own direction** ("the scope failure is the orchestrator's (intent files from integration); leave it"). Nothing at this seat can close it: the seven paths are carried by the branch's prep commit `d9bb808`, and removing them would need a rebase of the task branch — a stop condition. Re-run verbatim below; my own changes are all within the allowed paths (`git status` shows only the six owned files). |
| 2 | important | `src/review/records.py:109` — v2 silently accepts absent provenance keys | **Fixed.** An `h0.v2` payload must now *declare* both `synthetic` and `permission_ref`; an omitted key is `INVALID_RECORD` before any kind rule runs. The two exact-key-set validators the finding names ("judgment/bundle") now require `required \| {'permission_ref'}` under v2 — `permission_ref` is required, not optional — while the v1 set stays exactly `required`. The `synthetic_fixture` check reads the now-guaranteed key. Callers updated: `src/demo/__init__.py` (Case, SourceVersion, Passage, MappingRevision), `tests/test_review_case.py`, `tests/test_pairing.py`, `tests/test_probe_bundle.py`. v1 compatibility is preserved and pinned: a v1 envelope validates without the keys, and the repository reads a v1 case's pair as the v1 default `(True, None)` — a v1 record can never be real or cite a permission. |
| 3 | important | `docs/work/tasks.json` note directs work to a resolved blocker and misstates evidence | **Fixed.** The CORE-9 note now describes the rework tip: the pair rule, the green suites, the signed permission and the open scope finding. Earlier packet text that the note repeated is superseded by this section; it stays above as dated history. |
| 4 | minor | fixture failure attributed to changed envelopes | **Disposed.** The builder's failure is a *validation* failure in the rebuild, never digest drift — digest comparison does not run. At the review it stopped at the legacy string basis (`build.py:620`, `typed_basis`); at the rework tip the same rebuild stops one step earlier, at the builder's own Case payload missing `permission_ref` (`build.py:614`). Both are CORE-8's re-freeze input; verbatim trace below. |

### What changed in this pass

| File | Change |
|---|---|
| `src/review/records.py` | `provenance(payload, permissions=None, version=SCHEMA_VERSION)`: the v2 branch first requires `"synthetic" in payload and "permission_ref" in payload` (`INVALID_RECORD` otherwise) and only then applies the declared-pair rules; a v1 payload reads as `(True, None)` — the v1 rules already fix every v1 record as synthetic. `JudgmentArtifact` and `ProbeBundleArtifact`: under v2 the key set is exactly `required \| {'permission_ref'}`. The `synthetic_fixture` check uses `p['synthetic']` directly. This supersedes decision 1 above ("the pair is read as declared; an undeclared pair is the synthetic default"): the pair is declared, never defaulted. |
| `src/review/repository.py` | `_pair` and `_check_provenance` read the pair under the record's own envelope version, so a stored v1 case keeps working and reads `(True, None)`. No write path changed; every derived write already copied the pair. |
| `src/demo/__init__.py` | The four payloads declare the pair (`'synthetic':True,'permission_ref':None`); the ambiguous mapping revision inherits the mapping payload's pair. |
| `tests/test_review_case.py` | `H0Case`'s Case, source, passage and mapping payloads and the two inline `BeliefSnapshot` payloads declare the pair. `test_an_undeclared_pair_reads_as_the_synthetic_default` is replaced by `test_a_v2_pair_is_declared_never_defaulted_and_a_v1_record_cannot_be_real` (either key omitted ⇒ `INVALID_RECORD`, from `make_record` and from `provenance`; a v1 envelope validates without the pair and reads `(True, None)`), and a new `test_a_v1_case_still_registers_and_its_pair_reads_as_the_v1_default` registers a v1 case, stores a v2 synthetic record in it and refuses the real one. `test_the_checkout_registry_grants_only_signed_files` now also asserts the checkout registry holds the owner's signed identifier. |
| `tests/test_pairing.py`, `tests/test_probe_bundle.py` | The hand-built source and passage payloads declare the pair. `test_record_validation_rejects_foreign_payloads` adds the two no-pair refusals for the bundle artifact. |
| `src/review/README.md` | The pair paragraph now states the declaration rule and the v1 reading. |

### Commands and results (rework tip, working tree that was committed)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_review_case -v` (brief's verify) | `Ran 55 tests in 0.809s` — `OK` (54 before; the pair-default test replaced by two) |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 304 tests in 4.209s` — `OK` |
| `bash scripts/h1/test.sh` (emulator suite) | `Ran 70 tests in 40.202s` — `OK` (log `.local/scratch/h1-rework.log`, an ignored local file) |
| frozen corpus count | 25 pair files, `manifest['pairs'] == 25`, 135 records, every one `h0.v1`, through `validate_record` |
| `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` | raises `src.review.errors.ReviewError: record does not satisfy h0.v1 or h0.v2` at `build.py:614` (`provenance`, missing `permission_ref` on the builder's own Case payload) — verbatim trace below |
| the checkout's registry | `sorted(load_permissions('.'))` → `['perm:wesm-company-copy:2026-10-13']` — the owner signed the WESM record on 2026-10-13, so the checkout registry is no longer empty (decision 6 above and the earlier stop-condition text are superseded on this point) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 45 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope CORE-9 task/CORE-4` | exit 1: `docs/work/bundle-v5/intent.md`, the three `foundation-review-2026-10-13/sources/*` profiles, `strategy.md`, `permissions/2026-10-13-wesm-company-copy.md`, `real-sources/intent.md` — the prep commit's seven paths, none written by this task |
| `/usr/bin/python3 scripts/plan.py scope CORE-9 feat/h1-api-persistence` | exit 1: the same seven plus `docs/work/reviews/CORE-2.md` and `docs/work/reviews/CORE-4.md`, the two parent packets carried by the stack |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 270 Markdown files, 1248 local links, 8 skills; bootstrap 1293 words.` — `PASS` |

Verbatim, the builder's rebuild failure (tail; the full trace starts at
`build.py:952` → `main` → `build_all:814` → `build_pair:614`):

```
  File ".../tests/fixtures/probe-bundle/build.py", line 614, in build_pair
    case = record("Case", CASE, {
  File ".../src/review/records.py", line 117, in provenance
    require("synthetic" in payload and "permission_ref" in payload)
src.review.errors.ReviewError: record does not satisfy h0.v1 or h0.v2
```

This is a validation failure in the rebuild, not digest drift: the comparison never runs.
`build.py` is outside this task's allowed paths and its re-freeze is CORE-8's row; its
payloads need the declared pair and the typed basis before `--check` can report anything
about digests.

### Acceptance at the rework tip

| Acceptance item (brief) | Exact check | Result |
|---|---|---|
| Real records refused without a signed permission and accepted with an injected registry | unchanged from the table above, plus the rework's `test_the_checkout_registry_grants_only_signed_files` assertion that the owner's signed identifier is now in the checkout registry | Pass |
| 25 pairs, 135 h0.v1 records still validate | unchanged; re-run above | Pass |
| `judgment_ref` must match the decision's task | unchanged from the table above; 55 verify tests green | Pass |
| Full offline suite green except the expected fixture digest drift, listed verbatim | The offline suite is now **fully green**: `Ran 304 tests in 4.209s` — `OK`, no exception needed. The fixture `--check` (not part of the suite; CORE-8's re-freeze) fails verbatim above, and its failure is a validation failure before any digest comparison, not drift — stated explicitly per finding 4 | Pass (suite green; fixture exception reported verbatim as a validation failure) |

### Post-commit re-run

The battery was re-run on the committed tree `21664f7` with the working tree clean:
`/usr/bin/python3 -m unittest tests.test_review_case` → `Ran 55 tests in 0.905s` `OK`;
`/usr/bin/python3 -m unittest discover -s tests` → `Ran 304 tests in 3.117s` `OK`;
`/usr/bin/python3 scripts/plan.py check` → `OK: 45 tasks, 7 gates`;
`/usr/bin/python3 scripts/plan.py scope CORE-9 feat/h1-api-persistence` → exit 1, first
line `docs/work/bundle-v5/intent.md` (the unchanged prep-commit set). No code or test file
differs between the emulator run above and this commit; the emulator log is
`.local/scratch/h1-rework.log`, an ignored local file.

### Left open, and the exact next action

- **The scope finding is open and left with the orchestrator**, as the review directs.
- **The fixture re-freeze is CORE-8's**: `build.py`'s payloads need the declared pair (and its
  three string bases the typed basis), then the re-frozen files.
- **No real case, source or decision exists in this checkout.** The real path is proven with
  an injected registry and with the loader over the signed file's identifier; no record cites
  WESM data or asserts anything about it.
- **Exact next action:** independent re-review of the rework tip (Sol 6.1); the review record
  belongs in this file, appended below this section.

## Orchestrator re-measure after rebase onto the integration branch (2026-10-13)

Rebased onto `feat/h1-api-persistence` (which now carries the accepted CORE-2 and CORE-4); earlier commit citations in this packet name pre-rebase commits. At `e32ab89`: full offline suite `Ran 332 tests in 5.067s` OK; task tests `Ran 55 tests in 0.581s` OK; `bash scripts/h1/test.sh` `Ran 70 tests` OK; `plan.py scope CORE-9 feat/h1-api-persistence` OK: all changed files inside CORE-9 allowed paths; `plan.py check` OK; `repo.py check` PASS. Run by the orchestrator seat; ready for the designated re-review.

## Designated review 2 (GPT Sol, independent, commit `de5e3be`, 2026-10-13)

> Independent review of `de5e3be`, using `git diff feat/h1-api-persistence...HEAD` and `git log feat/h1-api-persistence..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Verify passed 55 tests, including permission refusal/injected acceptance, mixed-case refusal, typed basis, judgment/task matching, and validation of 25 pairs containing 135 h0.v1 records. Full offline suite passed 332 tests. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORE-9 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** The v1 validation branches remain intact; acceptance text is unchanged. Existing test changes adapt payloads to v2 without removing checks. |
> | 4 | No additional dependencies or external effects | **Yes.** Runtime changes use local files and stdlib facilities; the diff adds no dependency, service, credential, network or model call. |
> | 5 | Truthful mode labels | **No.** Real seed decisions retain `synthetic_initial:true`; fixture-generated bundles can be stored as `synthetic:false`. See findings below. |
> | 6 | Unknowns preserved; no invented factual evidence | **Yes.** Test inputs are explicitly fictional. No real source, case, model run or measured gain is introduced or claimed. Unknown availability remains blocked. |
> | 7 | Complete, accurate handoff evidence | **No.** The packet records commands, results and next action, but the CORE-9 task note still claims scope fails and no rebase occurred, contradicting the latest packet and executed scope check. |
> | 8 | Domain invariants preserved | **No.** The conflicting provenance labels and fixture-bundle path undermine the separation of real and synthetic records. Identity, cutoff and review guards otherwise remain exercised by passing tests. |
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/review/records.py:367` | The bundle validator allows fixture-generated judgments to inherit real-case provenance, unlike the single-judgment validator. | Executed probe through `SystemOneService.generate`: saved `ProbeBundleArtifact` with `synthetic:false`, `execution_mode:synthetic_fixture`; a real retain decision successfully cited it. | Add the equivalent v2 fixture/provenance guard for bundles and test refusal without writes. |
> | important | `src/review/repository.py:330` | Real seed decisions receive contradictory provenance labels. | Executed real-case setup produced `synthetic:false`, a permission reference, and `synthetic_initial:true`. The README describes this port as “Explicit synthetic initial acceptance.” | Make v2 seed semantics and labels consistent with the case’s provenance; preserve v1 behavior and verify both cases. |
> | minor | `src/review/repository.py:697` | Omitted and explicit-null judgment references have different idempotency digests despite being described as equivalent. | Executed retry of an otherwise identical request, adding `judgment_ref:null`, returned `IDEMPOTENCY_CONFLICT`. | Normalize omission to null before hashing, and test equivalent retries. |
> | important | `docs/work/tasks.json:1611` | The resume note reports a resolved blocker and obsolete branch history. | Note says scope exits 1 and “no rebase was run”; packet line 421 records the rebase and successful scope, independently confirmed here. | Update the task note and matching progress handoff to the reviewed tip’s evidence. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_review_case -v` — **55 tests, OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **332 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope CORE-9 feat/h1-api-persistence` — **OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> 
> The standalone fixture builder was also run. It fails before digest comparison at `build.py:614`, where its Case omits `permission_ref`:
> 
> ```text
> src.review.errors.ReviewError: record does not satisfy h0.v1 or h0.v2
> ```
> 
> Digest drift was **not demonstrated**; the documented builder/re-freeze work remains with CORE-8. Emulator tests were not rerun.
> 
> **Verdict: rework.** Resolve the real/synthetic provenance inconsistencies and stale handoff note before acceptance.
**Verdict: rework.** Add the v2 fixture/provenance guard to the bundle validator (a synthetic_fixture bundle can never carry synthetic:false) with a no-write refusal test; make real-case seed decisions' labels consistent with the case provenance (no synthetic_initial:true on a real case), v1 unchanged; bring the tasks.json note and PROGRESS handoff to the rebased tip (rebase done by the orchestrator, scope OK). Address every blocking/important row above; dispose of minors explicitly.

## Orchestrator re-measure after the rework-2 rebase (2026-10-13)

Rebased onto `feat/h1-api-persistence`, which now carries the accepted EVAL-2 (frozen probe-bundle fixtures and their evaluation test). At `e184387`: `tests.test_review_case` `Ran 59 tests` OK; `bash scripts/h1/test.sh` `Ran 71 tests` OK; scope, plan and repository checks OK. Full offline suite `Ran 420 tests` **FAILED (errors=1)**: `tests.test_eval_probe_bundle` raises `FixtureProblem` (`pb-cc-1`: assumption ref, pair snapshot, compiled task and request digest differ from the frozen expectation). This is the planned coupling recorded in the foundation review: h0.v2 changes every compiled record, and CORE-8 (stacked on this branch) re-freezes the fixtures under h0.v2. CORE-9 cannot be merged alone; it merges together with CORE-8, whose branch must show the full suite green. The reviewer should judge CORE-9 on its own acceptance items with this failure attributed, not waived.

## Designated review (GPT Sol, independent, commit `c03cdb9`, 2026-10-13)

> Independent review of `c03cdb9bcdcc`, using both requested Git ranges against `feat/h1-api-persistence`. No files edited; working tree remains clean.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes, with the expressly allowed fixture-drift exception.** Verify passed 59 tests, including permission refusal/injected-registry acceptance, mixed-case refusal, typed basis, matching judgment references, and validation of 25 pairs/135 h0.v1 records. Full suite ran 420 tests with one frozen-expectation drift error, reproduced below. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORE-9 feat/h1-api-persistence` printed `OK: all changed files inside CORE-9 allowed paths`. |
> | 3 | Frozen contracts preserved; tests not weakened | **Yes.** Diff retains v1 validation branches and confines v2 changes to provenance, availability basis and judgment references. Updated assertions enforce the new contract; no tests were skipped or deleted. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Changes use local permission files and existing services; no added dependency, credential, network operation or cloud/model execution. |
> | 5 | Truthful mode labels | **Yes.** Both artifact validators refuse real provenance for `synthetic_fixture`. Passing tests demonstrate bundle refusal without writes and seed labels matching case provenance. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Unknown availability remains explicit; tests use injected permissions and fixture backends. No real case or live-run evidence is claimed. |
> | 7 | Packet records verification and handoff | **Yes, with a minor synchronization issue below.** Implementation packet records interpreter, commands, dispositions and next action; the latest review appendix records the rebased suite failure and CORE-8 handoff. |
> | 8 | Domain invariants preserved | **Yes.** Provenance is checked before writes; judgment resolution is access-checked and repeated under the commit lock. Existing cutoff, lineage, head, replay and uncomputed-consequence checks pass. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_review_case -v` — **59 tests, OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **420 tests, FAILED (errors=1)**, solely:
>   ```text
>   eval_probe_bundle.FixtureProblem: pb-cc-1: assumption ref differs from the frozen expectation; pair snapshot differs from the frozen expectation; t1: compiled task differs from the frozen expectation; t1: request digest differs
>   ```
> - Scope — **OK**; `plan.py check` — **45 tasks, 7 gates, OK**; `repo.py check` — **PASS**.
> - `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` — failed before digest comparison because the builder’s Case payload lacks `permission_ref`:
>   ```text
>   src.review.errors.ReviewError: record does not satisfy h0.v1 or h0.v2
>   ```
>   This command did **not** demonstrate digest drift. Emulator verification was not rerun.
> 
> Findings:
> 
> minor | `docs/work/tasks.json:1616` | The task’s resume note still presents the earlier 336-test green result without the current integration failure | Current execution and `docs/work/reviews/CORE-9.md:466` establish 420 tests with one fixture-drift error | Append current results and the requirement to verify the combined CORE-9/CORE-8 branch; synchronize PROGRESS and the implementation handoff.
> 
> **Verdict: accept.** Required behavior is demonstrated, the offline failure falls within the explicitly permitted and recorded fixture-drift exception, and no blocking or important finding remains; combined-branch green verification remains required before merging with CORE-8.
**Verdict: accept.** Emulator 71 OK at e184387. Merges only together with CORE-8 (planned h0.v2 fixture coupling).
