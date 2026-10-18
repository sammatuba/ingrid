# CORE-3 review record

## Interim review (orchestrator seat, Fable, commit 027ed6d, 2026-10-12)

Interim, independent review of `task/CORE-3` at `027ed6d` (stacked on `task/CORE-2`), written because the
designated reviewer (GPT Astra through Codex) is unavailable. It is the review-first list for the owner and
does **not** set the task `done`; the designated review supersedes this section when it lands. The reviewer
did not author any of the reviewed change. Read in order: `plan.py show CORE-3`, the probe-bundle intent,
the S3 section and the orchestrator note of `docs/work/probe-bundle/implementation.md`, the diff
`task/CORE-2...HEAD` (code read in full: `src/adapters/systemone/__init__.py`, `src/adapters/systemone/run.py`,
`scripts/probe/run.py`, `tests/test_systemone_adapters.py`), and for the CLEF-1 cross-check
`docs/work/clef/notes.md` and `docs/work/clef/smoke/response.json` on `task/CLEF-1` (read with `git show`).

### Commands run (interpreter `/usr/bin/python3`, inside the CORE-3 worktree)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_systemone_adapters -v` (the brief's verify command) | `Ran 18 tests in 0.186s` — `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 300 tests in 2.387s` — `OK` |
| `/usr/bin/python3 scripts/plan.py scope CORE-3 task/CORE-2` | `OK: all changed files inside CORE-3 allowed paths` (exit 0) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `git diff task/CORE-2...HEAD --stat` | 7 files: the four new code/test files plus `implementation.md`, `tasks.json` (state only), `PROGRESS.md` (row and log entry) |
| `git status --short` | clean; `.local/probe` does not exist after the suite ran (no run artifact left by any test) |
| `env \| grep -c GEMINI_API_KEY` | `0` — no credential present in the review environment |
| `git cat-file -t 56d9028; git branch --contains 56d9028` | commit object exists, on no branch (pre-rebase head cited by the packet) |

### Findings

| Severity | Location | What | Why |
|---|---|---|---|
| important (disposition: escalate, not a CORE-3 defect; does not block) | `src/adapters/systemone/__init__.py:134` (`validate_envelope`), `:267-269` (`HttpSystemOne.decide`); `src/judgment/systemone.py:102,110` (`validate_answers`) | No mapping exists between the shape the only real `/v1/systemone` server returns and the frozen port shape. CLEF-1's llama.cpp smoke response is `{"model", "answers", "usage"}` with `type` on every answer and `confidence` on choice answers (`docs/work/clef/smoke/response.json` on `task/CLEF-1`); `HttpSystemOne.decide` hands the transport's return straight to `validate_envelope`, which requires exactly `{'answers','model_version'}`, so that response is `MODEL_INVALID_RESPONSE` (through the service, `MODEL_UNAVAILABLE`), nothing written. | The intent is not contradicted by CORE-3: the HTTP acceptance item is request-side only (URL, body, no retry) and the intent says the Clef server comes "later". But even a CORE-3-local fix (`model` to `model_version`, drop `usage`) would still be refused by S2's frozen `validate_answers`, whose per-answer key sets are exact and reject `type`/`confidence`; that layer is outside CORE-3's allowed paths. The mismatch is therefore between the CLEF-1 server contract and the frozen port, exactly the "guardian's call" `docs/work/clef/notes.md` item 1 names: either a new intent revises the port/server shape, or a follow-up brief adds a documented, tested mapping in `HttpSystemOne` plus a server-side projection in the CLEF lane. The CORE-3 packet does not mention the known discrepancy; the designated reviewer or guardian may prefer `escalate` as the formal verdict for this item. |
| minor | `docs/work/probe-bundle/implementation.md` "Post-commit re-run" (S3 section) | The packet names commit `56d9028` and the figures `Ran 296 tests`, `OK: 41 tasks`; that commit is on no branch after the rebase and the figures predate CORE-2 rework 4. Measured at `027ed6d`: 300 tests, 42 tasks. The orchestrator note says the suite is OK but gives no numbers. | A record should cite the commit that exists at review time with figures re-measured there (the same gotcha CORE-2 rework 4 logged). Correction: one line in the packet with the head commit and the re-measured numbers. |
| minor | `tests/test_systemone_adapters.py:601,605` | Two `run_case` calls use the default `transport_factory=GeminiTransport` with `CONCRETE_CONFIG` (`credential_env='GEMINI_API_KEY'`, `model='gemini-3.8-flash'`). They pass only because the tampered `result.json` is refused before a transport is built. | Under a regression of the read-back guard, a runner of the suite with `GEMINI_API_KEY` exported would reserve a ledger attempt and spawn the network worker from a unit test. Correction: pass an exploding factory (`lambda *a: AssertionError(...)`), as the `max_attempts=2` row at `:540` already does. No live call is possible today (no credential in the environment, and the guard is tested), so this is hygiene, not a defect. |
| minor | `src/adapters/systemone/run.py:105-110, 163-171` (`render_refused` branch, read-back and save) and `prepare_probe` refusal branch `:95-97` | No test exercises a render refusal through the runner; the H0 synthetic case always renders 32 questions. | Defensive code consistent with S2's "a refusal is a result", but the save shape and the restart read-back of a `render_refused` result are unverified. Correction: one row with a task whose mapping has nine candidates (`TOO_MANY_CANDIDATES`) through `run_case`, asserting the saved status, `transport is None` and a no-call restart. |
| minor (noted, not a defect) | `src/adapters/systemone/__init__.py:45-48, 168`; packet decision 3 | The inner text bound is the port's 64 KiB (`MAX_RESPONSE_BYTES`), not `GeminiProvider`'s 32 KiB; the transport-level bounds (`timeout_seconds=30`, `max_response_bytes=65536`, 1 to 2048 output tokens) match `GeminiProvider` exactly (asserted at `tests:334`). | Since the whole envelope is already bounded at 65536 bytes (`:156`), the text bound can never be the binding one; the reading "same bounds as `GeminiProvider`" is defensible and the acceptance text does not pin the figure. Recorded so the designated reviewer need not re-derive it. |
| minor (noted) | `src/adapters/systemone/run.py:47-48, 61-68` (`PLACEHOLDER_WORDS`) | A real `authorization_ref` carrying the token `approved` (for example "approved by owner 2026-10-12") is refused as `MODEL_CONFIG_INVALID`. | The packet documents the rule as erring toward refusal and the operator rewords; acceptable for a file that authorizes a live call. Record in the runner's README when one is written. |

Checks that found nothing to report, with evidence:

- **Live-call paths.** The only path that can reach a provider is `scripts/probe/run.py --config <file>` through `run_case` with the unchanged `GeminiTransport`: it needs an explicit config file, a `LiveConfig` with no placeholder token, `max_attempts == 1`, the named credential in the environment (`MODEL_CREDENTIAL_MISSING` otherwise) and a free ledger slot. No default URL, model, transport or key exists in either class (`tests:392-394` asserts `HttpSystemOne` carries only `name` and `probabilities`). The suite patches `subprocess.Popen` (`tests:546`), `socket.socket` (`tests:368`) and redirects `ROOT` to a temp directory (`tests:513,557`). Same gate pattern as the accepted `scripts/m3/gemini-run.py`; live execution of this runner stays orchestrator-only (CORE-5, GATE-2).
- **Credentials.** `HttpSystemOne` refuses a base with userinfo, query, fragment or path (`:250-252`, tested at `tests:375-380`); neither adapter reads the environment; the Gemini credential travels only through `GeminiTransport`'s worker stdin (unchanged). The saved result carries `transport.last_receipt`, which holds no key.
- **Retry.** One `self.transport(...)` call per `decide` in both classes; every invalid row asserts exactly one call (`tests:265`, `:412`), and a transport exception is sanitized to `MODEL_UNAVAILABLE` with one call and nothing written (`tests:282-288`).
- **Malformed response writes nothing.** 20 emulation rows and 11 HTTP rows raise `MODEL_INVALID_RESPONSE` from `decide` and `MODEL_UNAVAILABLE` through `SystemOneService`, with `probe_bundles` empty after each (`tests:230-273`, `:398-423`). `parse_json` rejects duplicate keys and non-finite numbers (`src/contracts/jsonutil.py:139-147`).
- **Frozen contracts.** No change under `src/judgment`, `src/review`, `src/api`, `docs/work/probe-bundle/intent.md`; `tasks.json` diff is the CORE-3 state field only; no test weakened or skipped (the orchestrator's rebase fix renamed a key in two assertions to the one the workspace emits).
- **Mode labels.** Every test backend is `synthetic_fixture`; the offline preparation renders under `offline-preparation` with `inference_performed: false`; the emulation labels probabilities `verbalized_uncalibrated`, the HTTP client `unreported` (S2's default), both asserted in the saved metadata.

### Acceptance item verdicts

| Acceptance item | Verdict | Evidence |
|---|---|---|
| schema has one property per question with enum options | met | `test_schema_has_one_property_per_question_with_enum_options`: `properties` equals the question set, `required` lists every question, `additionalProperties` false at every level, each choice enum equals that form's `presentation` (aliased `f2` and permuted `f1` checked), each `noul` bounded to [0, 1]. Code: `__init__.py:85-123`. |
| valid synthetic round trip saves; truncated, oversize, malformed and missing-question responses write nothing | met | `test_valid_synthetic_round_trip_saves_with_verbalized_probabilities` (record validates, metadata, digests, receipt, one call, replay without a second call) and `test_truncated_oversize_malformed_and_missing_question_write_nothing` (20 rows, both layers, store empty); HTTP rows in `test_a_malformed_response_is_refused_and_nothing_is_read_from_an_oversized_one`. |
| HTTP client posts exactly `<base>/v1/systemone` with the rendered request, no retry | met | `test_the_client_posts_the_exact_path_with_the_rendered_request_and_never_retries`: URL `http://127.0.0.1:8080/v1/systemone` (trailing slash on the base does not double it), body equals the rendered request and re-digests to `request_digest`, one call, `socket.socket` patched to raise. The response-side shape gap with the CLEF-1 server is the important finding above and is outside this item's wording. |
| runner refuses placeholder configuration | met | `test_the_runner_refuses_placeholder_configuration`: the README example passes `LiveConfig` and is refused by `load_config` as `MODEL_CONFIG_INVALID`, the CLI prints that status and exits 1 with `run_case` patched to fail if reached, nothing written under `.local`; per-field rows for each documented word. |

Checklist: 1 yes (tests above, run here); 2 yes against the stacked base `task/CORE-2` (against `feat/h1-api-persistence` the diff lists only CORE-2's own review record, the stacked-branch listing the packet explains); 3 yes; 4 yes (no new dependency, service, credential, network or model call; the runner's live path is the pre-existing gated one); 5 yes; 6 yes; 7 yes, except the stale commit and figures in the minor finding; 8 yes for CORE-3's own work, with the port-versus-server shape question escalated.

**Verdict: accept.** All four acceptance items are met by tests run at `027ed6d` with the full suite green, and the one important item (no mapping between the CLEF-1 server's `{"model","answers","usage"}` plus per-answer `type`/`confidence` and the frozen port shape) is a contradiction between the CLEF-1 server contract and the frozen port, to be escalated to the guardian rather than reworked inside CORE-3's paths; the designated review supersedes this interim record.

## Designated review 1 (GPT Sol, independent, commit `5adabf4`, 2026-10-13)

> Independent review of `task/CORE-2...5adabf4`, including all four commits in `git log task/CORE-2..HEAD`. No files edited.
> 
> Executed with Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_systemone_adapters -v` | 18 tests, OK |
> | `/usr/bin/python3 scripts/plan.py scope CORE-3 task/CORE-2` | OK |
> | `/usr/bin/python3 -m unittest discover -s tests` | 300 tests, OK |
> | `/usr/bin/python3 scripts/plan.py check` | OK: 42 tasks, 7 gates |
> | `/usr/bin/python3 scripts/repo.py check` | PASS |
> | `/usr/bin/python3 scripts/plan.py scope CORE-3 feat/h1-api-persistence` | Exit 1: inherited `docs/work/reviews/CORE-2.md` |
> 
> The emulator suite was not rerun.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every brief acceptance item demonstrated | **Yes.** Executed tests check per-question enums, synthetic saves, 20 invalid-response cases writing nothing, exact HTTP URL/body with one call, and placeholder refusal. The byte-bound fidelity issue below remains. |
> | 2 | Changes stay within allowed paths | **Yes against the requested stacked base.** Scope prints OK. The process’s literal integration-base check fails only on CORE-2’s inherited review record. |
> | 3 | Frozen contracts and acceptance unchanged; no weakened tests | **Yes.** No frozen implementation or intent files changed; existing assertions only adopt CORE-2’s `probe_bundles` key. |
> | 4 | No effects or dependencies beyond the packet | **Yes.** New adapters use injected transports; the runner reuses the named Gemini transport. Review commands made no model or cloud calls. |
> | 5 | Truthful mode labels | **Yes.** Saved synthetic metadata, `verbalized_uncalibrated`, HTTP `unreported`, and offline `inference_performed: false` are asserted. |
> | 6 | Unknowns remain unknown | **Yes.** Tests use labelled fictional seeds and synthetic responses; consequences remain `uncomputed`. |
> | 7 | Complete implementation packet | **Yes, with a minor accuracy issue.** Interpreter, commands, results, unfinished work and next action exist; current post-rebase figures are incomplete. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** Outputs remain proposals; semantic probabilities confer no acceptance or execution authority. Intent fidelity has the separate defect below. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/systemone/__init__.py:168` | Gemini answer-text limit is relaxed to 64 KiB despite intent requiring the same byte bounds as `GeminiProvider`, whose text limit is 32 KiB. | Executed reproduction: valid answers padded with whitespace produce **41,701 text bytes**, **42,036 envelope bytes**; the new adapter accepts all 32 answers, while `GeminiProvider` rejects the identical envelope with `MODEL_INVALID_RESPONSE`. The envelope cap therefore does not make the text-limit difference irrelevant. | Enforce Gemini’s 32 KiB decoded-text cap while retaining the port’s 64 KiB response cap; add a boundary case asserting rejection and no write. |
> | minor | `tests/test_systemone_adapters.py:601` | Two tampered-result tests fall back to the real transport if read-back guards regress. | Calls at lines 601 and 605 omit `transport_factory`; `run_case` defaults to `GeminiTransport`. | Inject a factory that raises immediately if constructed. |
> | minor | `docs/work/probe-bundle/implementation.md:1631` | Post-commit evidence cites the pre-rebase commit and counts without exact replacement figures. | Packet cites `56d9028`, 296 tests and 41 tasks; current executed results are 300 tests and 42 tasks. | Append the reviewed commit and exact post-rebase commands/results. |
> 
> **Verdict: rework.** The acceptance tests pass, but the demonstrated relaxation of the intent’s Gemini text-byte bound is an unresolved important finding.
**Verdict: rework.** Enforce the Gemini 32 KiB decoded-text cap in the new adapter, with a test using the reviewer's padded envelope. Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `d61ef8c`, 2026-10-13)

> Independent review of `d61ef8c1284628abae0e6edc0005d6246a9b3ae9` against `feat/h1-api-persistence`, including the diff and all nine branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed tests verify per-question enum schemas, a saved synthetic round trip, truncated/oversize/malformed/missing-question responses writing nothing, exact HTTP URL and rendered body without retry, and placeholder configuration refusal. |
> | 2 | Only allowed paths changed | **Yes.** Requested integration-base scope command printed `OK: all changed files inside CORE-3 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Diff adds adapters, runner and tests without changing frozen contracts or acceptance text. Boundary and refusal coverage was added. |
> | 4 | No dependencies or effects beyond the packet | **Yes.** Adapters require injected transports; runner reuses the named Gemini transport and configuration. No new runtime dependency. |
> | 5 | Truthful mode labels | **Yes.** Tests assert `synthetic_fixture`, `verbalized_uncalibrated`, HTTP `unreported`, and offline `inference_performed: false`. |
> | 6 | Unknowns stayed unknown | **Yes.** Fixtures and responses are explicitly synthetic; saved results retain `pending_human_review` and consequences `uncomputed`. |
> | 7 | Packet records verification and handoff | **Yes.** Implementation packet records interpreter, exact commands/results, historical rework, post-rebase measurements, unfinished work and designated re-review as the next action. |
> | 8 | Consistent with product direction and invariants | **Yes.** Results remain proposals; semantic scores confer no acceptance or execution authority. Runner checks accepted heads and outlook history remain unchanged. |
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 -m unittest tests.test_systemone_adapters -v` — **20 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope CORE-3 feat/h1-api-persistence` — **OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **340 tests, OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 45 tasks, 7 gates**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> 
> Findings: **None.** The previous important finding is resolved: executed boundary tests demonstrate acceptance at 32,768 decoded text bytes and rejection above that limit, with no artifact written.
> 
> Emulator integration and live backend execution were not run; this review establishes the brief’s synthetic-transport acceptance criteria.
> 
> **Verdict: accept.** All required acceptance items were demonstrated by executed checks, scope passes, and no blocking or important findings remain.
**Verdict: accept.** Orchestrator ran scripts/h1/test.sh after the rebase: 69 tests OK.
