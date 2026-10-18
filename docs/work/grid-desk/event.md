# GRID-3: the event review of the PEDC Unit 2 trip

Task packet. Lane GRID, milestone M5, executor agent, branch `task/GRID-3` from
`feat/h1-api-persistence` (merged into this branch at `f429d24`). Read first:
[AGENTS.md](../../../AGENTS.md), [milestones](../milestones.md), the
[grid-desk intent](intent.md), the [real-sources intent](../real-sources/intent.md). State
`in_progress`, self-review only — a reviewer sets `done`. The commands and results below were
run in the task worktree on 2026-10-14 with `/usr/bin/python3` 3.14.4, node 22.23.1 and
`.local/h1-venv/bin/python` (FastAPI 0.115.12, uvicorn); this branch is not pushed.

## What was built

| Path | What it is |
|---|---|
| [`src/demo/pedc.py`](../../../src/demo/pedc.py) | The runtime module: it builds the EVAL-5 case's records for a given tenant, case and actor from the rows committed beside it, and seeds them through the review core. |
| [`src/demo/pedc-case.json`](../../../src/demo/pedc-case.json) | The source rows the runtime needs — the four `pedc_u2_21sep` advisory rows and the 237 register rows of the one `08PEDC_U02` run covering 2026-09-21 — plus the case definition and the dispatch body. Copied from `tests/fixtures/`, never imported from it. 36 KB. |
| [`src/api/hosted.py`](../../../src/api/hosted.py) | `POST /demo/session` now provisions a second case per judge session: the session's own copy of the real PEDC case. The session answer gains `event_case` and `event_seeded_at`; the reset answer is unchanged. |
| [`src/grid/event-api.js`](../../../src/grid/event-api.js) | The real adapter, replacing the orchestrator's preview: `load` reads the baked view model, `decide` runs the judge's path (session, snapshot, compile, review), `history` maps the case history. |
| [`tests/test_grid_event.py`](../../../tests/test_grid_event.py) | 30 tests: the records against the EVAL-5 fixture, the session's two cases and their isolation, the judge's decision through the frozen routes, the recorded-flow harness, and the live demo application over loopback. |
| [`tests/fixtures/grid/event/`](../../../tests/fixtures/grid/event/) | `build.py` (writes `view.json` and `flow.json`, `--check` refuses drift), `flow.json` (the recorded flow of two decisions, built by the real repository), `view.json` (the shape fixture the adapter harness reads), `run.mjs` (the node harness), `README.md`. |
| [`Dockerfile`](../../../Dockerfile) | One added line: `COPY docs/work/permissions ./docs/work/permissions`. See "The image needed the permission record" below. |
| [`scripts/deploy/walkthrough.py`](../../../scripts/deploy/walkthrough.py) | Four checks added: the event page and its adapter are served, the judge session carries its own event case and reads it, and the second judge's token cannot. |
| [`tests/test_hosted_config.py`](../../../tests/test_hosted_config.py) | The demo-session HTTP test asserts the event case and its isolation; the image contract pins the new `COPY`. |

## Why the judge's case is a second case

The intent allowed either seeding the real PEDC records into the session's case or giving the
session a second case, and HOST-2's store keys a case by `(tenant, case)` with one membership
per case. The first is impossible: a case record fixes the case's `(synthetic, permission_ref)`
pair for every record it holds (h0.v2, `CASE_PROVENANCE_MISMATCH`), and the session's case is
the labelled synthetic corpus. So a judge session gets **two cases in tenant `demo-judge`**:

* `demo-<16 hex of sha256(uid)>` — the synthetic corpus, membership policy `synthetic-public`;
* `pedc-<16 hex>` — its own copy of the real case, membership policy
  `perm:wesm-company-copy:2026-10-13`, and nothing else.

That is also what makes the acceptance's isolation provable: two sessions hold two copies, and
the event case is reachable only through its own membership. The fictional analyst's fixture
session keeps one case and no event case.

## The judge's path, as the adapter runs it

1. `load(id)` → `GET /grid-data/events/<id>.json`, the baked view model with the recorded
   judgment (written by the orchestrator's converter, `reference/event_judgment.py`). No model
   call on a page load.
2. `decide({decision, value, reason})` →
   `POST /demo/session` (empty body, no credentials, once per page load) → `GET` the case heads
   → `POST /snapshots` with `audit_cutoff` **= `event_seeded_at`** → `POST /compile` with
   `information_cutoff` **= the advisory's own posting time** read from the view model
   (`2026-09-21T13:39:37+08:00`) → `POST /reviews` with the disposition, the reason, and the
   quantity read from the compiled task's assumption definition. The message names the saved
   receipt; a refusal is shown as its code and a sentence.
3. `history()` → `GET .../history`, newest first, mapped to `{t, what, reason, who}`.

Why the seeded instant is the audit cutoff: the intent fixes that the desk's own acts (the
reviewed mapping and the seed acceptance) carry the session actor and the session's real time,
so the case's belief state is "now" while the evidence is read at the event's cutoff — the
`retrospective` flag on the decision says exactly that. The instant is the server's own, so no
client clock decides it.

## Acceptance

| Acceptance item | How it is met | Where it is proven |
|---|---|---|
| a judge with no account records a decision on the PEDC event and sees it in history | `POST /demo/session` takes an empty body and no credentials; the flow above runs on the session's own event case; the decision, its `OutlookRevision` and the compiled task are real records carrying the permission; `history` returns them. | `tests/test_grid_event.py::JudgeFlow::test_a_judge_with_no_account_records_a_decision_and_sees_it_in_history`, `::test_a_revise_decision_changes_the_accepted_value_and_the_history_shows_both`, `::RecordedFlow::test_the_decisions_are_saved_and_read_back_as_history`, `::LiveServer::test_the_adapter_runs_the_judge_path_over_http` (the same adapter, over HTTP, on the real application) |
| another judge's case is untouched | Each session's event case is its own; a decision lands on one, the other stays empty, and neither token reaches the other's case (`ACCESS_DENIED` → 404). | `::SeededSession::test_two_sessions_copies_are_independent`, `::JudgeFlow::test_another_judge_s_case_is_untouched`, `::LiveServer::test_the_session_and_the_pages_over_http`, `::test_a_decision_lands_only_on_the_judges_own_case`, `tests/test_hosted_config.py::HTTPContractTests::test_two_sessions_reach_their_own_case_and_nothing_else` |
| real records carry the permission reference | Every record of the seeded case and everything derived from it is `synthetic: false` with `perm:wesm-company-copy:2026-10-13`, validated against the signed registry; an empty registry refuses the build `PERMISSION_UNKNOWN`. | `::CaseRecords::test_every_record_is_real_and_cites_the_signed_permission`, `::SeededSession::test_every_seeded_event_record_is_real_and_carries_the_permission`, `::JudgeFlow` |

Outputs: **`/event/<id>` page** — served with its adapter, reached from the grid page's feed and
review list (`::JudgeFlow::test_the_pages_and_the_adapter_are_served`, the walkthrough);
**hosted session seeds a copy of the real PEDC case** — `event_case` / `event_seeded_at` on the
session answer, the case built by `src/demo/pedc.py` (`::SeededSession`, the walkthrough).

## The same records the EVAL-5 fixture builds

`tests/fixtures/pedc-u2-2026-09-21/case.json` is the record; the built copy holds the same
records with the same payloads (proved record by record in
`::CaseRecords::test_the_records_are_the_eval_5_case_s_records`), and the only differences are
the ones the intent names:

| Record | Differences from the fixture's |
|---|---|
| the four advisories, their passages, the register run and its unreviewed candidate | the passage/mapping `source_ref(s)` digest, because the envelope names this session's case |
| the reviewed `MappingRevision` | that digest too, and its own act: `reviewer` the session's actor, `reviewed_at` the session's instant, and no `reconstruction` block (this act is real, not a reconstruction of one) |
| the seed acceptance | the `mapping_ref` it cites, and the case it names |
| the dispatch source and passage | nothing: byte-identical (its envelope keeps the assembly instant the fixture recorded) |

The four advisories' `known_at` are their posting instants and the register run's is
2026-02-05T00:00+08:00, exactly as the fixture has them. The committed `pedc-case.json` rows are
compared with the `tests/fixtures/wesm` rows they were copied from
(`::CaseRecords::test_the_committed_rows_are_the_fixture_rows`).

## The image needed the permission record

`DEFAULT_PERMISSIONS` is read from `docs/work/permissions/` at the repository root, and the
image copies only `requirements/h1.lock` and `src`. Without a change, every `POST /demo/session`
in the container would have failed 503 once the event case was seeded, because no real record
can cite an identifier the registry does not hold. The Dockerfile therefore copies that one
directory, and the image contract test pins both the line and the identifier
(`tests/test_hosted_config.py::ImageContractTests`). It copies a permission record, not a
credential, and `.dockerignore` still excludes `.git`, `.local` and every key-shaped name. The
build context's own exclusions had to be told about the copy — the line alone was not enough —
see **Rework** below.

## Commands and results

Run in the task worktree on 2026-10-14, before the commit on `task/GRID-3`:

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 30 tests in 0.686s

OK (skipped=3)          # the three live-application tests, below

$ GRID_EVENT_PYTHON=<venv>/bin/python /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 30 tests in 1.661s

OK                      # the real demo application on loopback, no test skipped

$ /usr/bin/python3 -m unittest discover -s tests
Ran 617 tests in 12.615s

OK (skipped=12)         # 9 pre-existing (7 FastAPI-guarded, 2 browser), 3 live-application

$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event
Ran 92 tests in 3.345s

OK                      # the same two files under the real FastAPI and pydantic

$ /usr/bin/python3 -m unittest tests.test_hosted_config
Ran 62 tests in 1.815s

OK (skipped=7)          # under the bare interpreter

$ /usr/bin/python3 scripts/repo.py check
Checked 314 Markdown files, 1664 local links, 8 skills; bootstrap 1399 words.
PASS

$ /usr/bin/python3 scripts/plan.py check
OK: 49 tasks, 7 gates

$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
OK: all changed files inside GRID-3 allowed paths

$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check
OK: view.json and flow.json reproduce; 2 decisions, 2 history entries,
information cutoff 2026-09-21T13:39:37+08:00

$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
OK: 14 records, 2 pairs, 4 compiles, 0 committed reviews (none by design); bundle probe-bundle.v5;
fixture digest 26ba43bf…; trip/t0 omissions verified; composed labels recomputed

$ node tests/fixtures/grid/event/run.mjs --root .
{"ok": true, "transport": "recorded", "event": "pedc-u2-2026-09-21", "problems": [],
 "flow": {"decisions": [{"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:retain:1"},
                        {"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:revise:2"}],
          "history": [[{"t": "14 Oct 2026, 10:01 Manila", "what": "Retained 83.7 MW",
                        "reason": "Fixture decision: the trip puts the assumed availability in question.",
                        "who": "You (this session)"}],
                      [{"t": "14 Oct 2026, 10:02 Manila", "what": "Revised to 95.5 MW", …},
                       {"t": "14 Oct 2026, 10:01 Manila", "what": "Retained 83.7 MW", …}]]},
 "local": {"decision": {"ok": false, "message": "Decisions are recorded on the hosted demo."}},
 "refusal": {"decision": {"ok": false, "message": "STALE_HEAD: the case moved since this page
                          loaded; reload and decide again"}}}

$ node tests/fixtures/grid/event/run.mjs --root . --base http://127.0.0.1:<port>
{"ok": true, "transport": "live", "problems": [], "flow": {… the same two decisions, saved by
 the real application and read back from its history …}}
```

The live server above is the container's own entry point, started and stopped by the test:

```sh
$ NOWCAST_ENV=demo <venv>/bin/python -m uvicorn src.api.hosted:app --factory \
      --host 127.0.0.1 --port <free port> --no-access-log          # GRID_DATA_DIR set
$ /usr/bin/python3 scripts/deploy/walkthrough.py --port <same port>
36/36 checks passed on the container port
```

The walkthrough ran against that loopback server with `GRID_DATA_DIR` pointed at
`tests/fixtures/grid/page/data`, so its six baked-replay checks resolve as they do in the image
(`build/grid-data`); in the container the same checks read the real snapshot. The four added
checks passed: `/event/<id>` serves the page, `/grid/event-api.js` is served, the judge session
seeds its own copy of the real PEDC case and reads it (`assumption:08PEDC_U02:2026-09-21`), and
the second judge's token is 404 on it. The walkthrough's reset section still passes: the reset
restores the session's *synthetic* case and leaves the event case alone (see below).

Session provisioning, measured on this worktree (five runs): 23–27 ms, 10.2 KiB of entries for
the synthetic case and 32.7 KiB for the event case, 43 KiB per session. One earlier mistake was
caught by this measurement and is fixed: the register sample's 237 rows are inputs to the
*builder*, and the case holds one change-only `SourceVersion` for the run, not 237 records.

## Post-commit verification (2026-10-14, commit `4f29b1a`)

Every command above was re-run on the committed tree, with the same results:

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event        → Ran 30 tests … OK (skipped=3)
$ GRID_EVENT_PYTHON=<venv>/bin/python /usr/bin/python3 -m unittest tests.test_grid_event
                                                            → Ran 30 tests … OK
$ /usr/bin/python3 -m unittest discover -s tests            → Ran 617 tests … OK (skipped=12)
$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event        → Ran 92 tests … OK
$ /usr/bin/python3 scripts/repo.py check                    → PASS
$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check       → OK: … 2 decisions, 2 history entries
$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
                                                            → OK: 14 records, 2 pairs, 4 compiles … (digest 26ba43bf…)
$ node tests/fixtures/grid/event/run.mjs --root .           → {"ok": true, "problems": []}
```

## Decisions, deviations and flags a reviewer should see

1. **The judge's copy is a second case**, not records added to the session's corpus case, for
   the provenance reason above. The intent allowed it ("or as the session's second case, if the
   store keys one case per session; choose the smaller change and say which"): the store keys
   one case per session, and a second case is the only one that validates.
2. **`event_case` and `event_seeded_at` are additive keys on `POST /demo/session`'s answer.**
   The route is HOST-1's and not frozen; the reset answer keeps its exact key set (pinned by
   `tests/test_hosted_config.py::HTTPContractTests::test_reset_requires_the_callers_own_token_and_is_session_local`).
   The alternative — the client's own clock as the audit cutoff — would let a skewed browser
   break the demo.
3. **`POST /demo/reset` does not re-seed the event case.** It restores the session's synthetic
   case as before; a judge's decisions on its own copy of the real case are that judge's record
   and survive it. If the orchestrator wants a reset to wipe the event case too, that is a
   small follow-up in `reset_session` (nest a second `reset_case`); it was left alone because
   HOST-1's reset tests pin the current behaviour and the walkthrough's reset section exercises
   it.
4. **The live probe bundle is not seeded.** The intent's note said the seed would carry the
   orchestrator's saved live probe bundle; the brief's seeding point (the operative text) names
   the case records only, and the live artifact's `task_ref` names a task of the *fixture* case
   — seeding it faithfully would mean replicating the fixture's whole compile chain in the
   runtime, and re-enveloping the artifact would break its digests. The live judgment the judge
   *sees* is the baked view model's, which is where the brief puts it. Unfinished item for the
   orchestrator (see below).
5. **The refusal sentences are the adapter's own copy**, keyed by the refusal codes the routes
   answer with; the code is always shown verbatim and an unknown code or a non-JSON answer is
   shown as `HTTP <status>`. The routes' error bodies carry the code only.
6. **`pedc-case.json` carries real company rows** (the advisories' text and the register rows),
   as the permission record allows and as `tests/fixtures/wesm/` already does. It is a runtime
   copy, so a runtime image never reads `tests/`.
7. **The dispatch record keeps the fixture's assembly envelope** (`recorded_at`
   2026-10-13T17:27:00Z, `publisher` "EVAL-5 case assembly, digest of the source profile
   document"): the desk did not produce those bytes, and the fixture did.

## Unfinished items and the exact next action

Nothing in this task's acceptance is unfinished. The next action is **independent review of
`task/GRID-3`** (reviewer: not the author) — the reviewer should re-run the verify command, the
suite and the recorded-flow harness rather than trusting this record. Handed back to the
orchestrator: (a) the live probe bundle seed (deviation 4) if the owner wants the judge's case
to hold the artifact itself; (b) GRID-1's real snapshot merge, which is what makes the page's
baked view model the real one — the fixture here is a shape fixture, labelled as one, and the
harness reads it only; (c) the reset question (deviation 3).

## Self-review note

- Every acceptance item is executed, not inspected: the decision path runs through the real
  route functions over the real repository (bare interpreter), through the real application over
  loopback HTTP (venv), and through the adapter itself in node against the recorded flow.
- The recorded flow is *the repository's own output*: `build.py` builds the session with the
  function `POST /demo/session` calls and replays the same calls the routes make, and the
  harness refuses any request body that differs from the recorded one, so the adapter cannot
  pass on a transport that answers anything.
- The copies' payloads are compared record by record against the EVAL-5 fixture, and the rows
  against the `tests/fixtures/wesm` files they were copied from; nothing was typed twice.
- The one thing this seat cannot run is the container build (`docker`), so the Dockerfile line
  and its contract test are recorded, not executed; the walkthrough's new checks were executed
  against the same application on loopback, which is what the container runs.
- Two tests around the live server are skipped without `GRID_EVENT_PYTHON`; that is stated in
  the skip reason, and both were executed in this seat with the venv interpreter.
- Rework 2 (both review findings) keeps that standard and states its own limits: the page
  harness is a DOM shim, not a browser — it proves the design file executes, records the
  decision through the page's form and fills the history card from what the adapter returned,
  and the real browser check stays the orchestrator's walkthrough and image run (36/36 here on
  loopback); the refusal row is the channel the read-only renderer offers, since the adapter may
  not add elements to a design file's page, and `who: 'History unavailable'` marks it as a state
  rather than an entry; the read-back instant comes from the case, never from this seat's clock;
  and the fixture's `judgment: null` stands until the orchestrator's baked view model carries
  the live receipt.

## Orchestrator image check and finding (2026-10-14, orchestrator seat, not a designated review)

The orchestrator merged this branch with `task/GRID-1` and `task/GRID-2` in a scratch worktree (not pushed), resolving the
two expected conflicts (`Dockerfile`: both `COPY build/grid-data` and `COPY docs/work/permissions`; the hosted-config test:
one COPY-set test with all four sources), baked the real data and built the image.

**Finding (important, `.dockerignore`):** the build failed with `"/docs/work/permissions": not found` because
`.dockerignore` excludes `docs`; the image built from this branch cannot contain the permission registry the seeded real
case needs. Correction, tested in the scratch build: keep `docs` excluded and add `!docs/work/permissions` on the next
line; the image then holds `docs/work/permissions/` only. Add a test that `.dockerignore` re-includes exactly that path.

**Result after the correction, image in demo mode (`--read-only`, no environment), Chrome 1280 px:** the event page loaded
the baked view, then a judge with no account chose Retain with a reason and pressed Record decision. Network:
`GET /grid-data/events/pedc-u2-2026-09-21.json` 200, `POST /demo/session` 200, `GET .../cases/pedc-b3d06538f575aeaa` 200,
`POST .../snapshots` 200, `POST .../compile` 200, `POST .../reviews` 200, `GET .../history` 200. Status "Saved · receipt
event:pedc-u2-2026-09-21:retain:1"; all four rail steps done; history "You (this session) · Retained 83.7 MW" with the
reason; no console message.

## Rework (2026-10-14, executor seat): the `.dockerignore` finding

The finding ([review record](../reviews/GRID-3.md)): the orchestrator merged this branch with
GRID-1 and GRID-2 in a scratch worktree and built the image; the build failed with
`"/docs/work/permissions": not found`, because `.dockerignore` excludes `docs` and the `COPY`
source was therefore not in the build context. The image built from this branch could not hold
the registry the seeded real case cites. The correction asked for: keep `docs` excluded,
re-include exactly that one path so the image carries `docs/work/permissions/` and nothing else
from `docs`, with a test, and keep everything else as it is.

| Path | Change |
|---|---|
| [`.dockerignore`](../../../.dockerignore) | One line, `!docs/work/permissions`, directly after the `docs` exclusion (plus the header comment, which now names the registry among the image's sources). Docker applies the lines in order and the last match wins, so `docs` stays out and the registry — the directory and everything under it — comes back in. |
| [`tests/test_hosted_config.py`](../../../tests/test_hosted_config.py) | `ImageContractTests::test_the_build_context_re_includes_exactly_the_permission_records_the_image_copies`: the file's only negation is exactly the `COPY docs/` source (`docs/work/permissions`), it comes after `docs`; Docker's own matching rules applied to the real tree then prove the `COPY` source and every file under `docs/work/permissions` are in the context while all 374 other files under `docs/` stay out, and that `.git`, `.local`, `venv`, `node_modules`, `.env`, `*.key`, `*.pem`, archives and logs stay out. |
| [`scripts/deploy/README.md`](../../../scripts/deploy/README.md) | Adjacent correction, flagged for the reviewer, not part of the finding: the "Secrets" paragraph said the image copies "only the lock file and `src/`" — false since this task added the registry copy — and now names all three sources and the re-include. One sentence. |

The matching rules (last matching line wins; a line covers the path itself and everything under
it; `*` stops at `/`) are reproduced in the test module because this seat cannot run `docker`.
The negative controls (`.local/eval/check_dockerignore_controls.py`, ignored, not committed) show
the checker is not vacuous: it drops the registry file when the negation is removed (the build
failure the orchestrator observed), keeps `docs/competition/…` when an extra negation is added,
and drops the registry file again when the negation is placed before `docs` (the last-match
rule). Five controls, all as expected.

Commands and results (this worktree, 2026-10-14, reworked tip):

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 30 tests in 0.557s

OK (skipped=3)          # the three live-application tests, as before

$ /usr/bin/python3 -m unittest discover -s tests
Ran 618 tests in 10.443s

OK (skipped=12)         # 617 before this rework; the added context test is the 618th

$ /usr/bin/python3 -m unittest tests.test_hosted_config
Ran 63 tests in 0.950s

OK (skipped=7)          # under the bare interpreter; 62 before this rework

$ GRID_EVENT_PYTHON=<venv>/bin/python /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 30 tests in 1.415s

OK                      # the real demo application on loopback, no test skipped

$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event
Ran 93 tests in 2.938s

OK                      # 92 before this rework, under the real FastAPI and pydantic

$ /usr/bin/python3 .local/eval/check_dockerignore_controls.py
ok    the real file keeps the registry record: keeps(docs/work/permissions/2026-10-13-wesm-company-copy.md) = True
ok    the real file keeps other docs paths out: keeps(docs/competition/ai-builder-cup-2026/provenance-log.md) = False
ok    without the negation the record is outside the context (the observed build failure): … = False
ok    an extra negation would carry another docs path in (the test would fail): … = True
ok    the negation before the `docs` exclusion does not survive the last-match rule: … = False
5 controls as expected

$ /usr/bin/python3 scripts/plan.py check
OK: 49 tasks, 7 gates

$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
OK: all changed files inside GRID-3 allowed paths

$ /usr/bin/python3 scripts/repo.py check
Checked 317 Markdown files, 1691 local links, 8 skills; bootstrap 1399 words.
PASS
```

Nothing else changed: the Dockerfile, the application, the routes, the seeds, the fixtures and
the recorded flow are as the review record found them, and no test was weakened, skipped or
deleted. [tasks.json](../tasks.json) keeps this task's state `in_progress` (it has been
`in_progress` since the first build; no other task or field was touched, and no acceptance text
was edited). [PROGRESS.md](../PROGRESS.md) carries one further log row for this rework.

Unfinished and the exact next action: (a) the orchestrator re-runs the scratch build — `docker
build` and the demo-mode run on the reworked tip — to confirm the context holds
`docs/work/permissions/` and nothing else from `docs`; this seat cannot run `docker`, so the
correction's real effect is observed there and pinned here by the emulated contract test; (b)
independent review of `task/GRID-3` by a reviewer who is not the author, re-running the verify
command, the suite and the recorded-flow harness rather than trusting this record. The standing
hand-backs are unchanged: the live probe bundle seed, `/demo/reset` not touching the event case,
and GRID-1's real snapshot. Nothing in this task's acceptance is unfinished.

### Post-commit verification (commit `3cdfd88`)

The verify command, the suite and the structural checks re-run on the committed tree, with the
same results:

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event        → Ran 30 tests … OK (skipped=3)
$ /usr/bin/python3 -m unittest discover -s tests            → Ran 618 tests … OK (skipped=12)
$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/repo.py check                    → PASS (317 Markdown files, 1691 local links)
```

## Rework 2 (2026-10-14, executor seat): designated review 1's two important findings

The rework instruction: fix every blocking and important finding in the
[review record](../reviews/GRID-3.md), inside the allowed paths. The blocking row is the
orchestrator's own — the review range — and it is answered by the re-review's base: the review
used `task/GRID-2` as base while this branch merged the integration branch at `f429d24`, and
`plan.py scope GRID-3 f429d24` prints OK (below, with the brief's own base). The two important
rows are this task's, and both are fixed and tested here. No minor rows were listed.

| Path | Change |
|---|---|
| [`src/grid/event-api.js`](../../../src/grid/event-api.js) | Both findings: `decide` now moves the audit cutoff with the accepted state (`state_at`, adopted through `POST .../read` after every save) while the compile keeps the event's historical information cutoff; `history` no longer returns `[]` on a failure — it answers one `History unavailable` row carrying the route's code and sentence. |
| [`tests/fixtures/grid/event/build.py`](../../../tests/fixtures/grid/event/build.py) | The recorded flow is three decisions (retain, revise, retain) with this session's own audit cutoff per step and the read-back of each accepted outlook; the rule is replayed through `build_snapshot`/`commit_review`/`read`, not restated. |
| [`tests/fixtures/grid/event/flow.json`](../../../tests/fixtures/grid/event/flow.json) | Regenerated by the builder (`--check` reproduces it); now 3 decisions and 3 history entries, 50,839 bytes. |
| [`tests/fixtures/grid/event/run.mjs`](../../../tests/fixtures/grid/event/run.mjs) | Answers and checks the `/read` request body, checks each snapshot body against that decision's recorded state instant, and adds the three history-failure scenarios (401, 503, 200-not-a-list). |
| [`tests/fixtures/grid/event/render.mjs`](../../../tests/fixtures/grid/event/render.mjs) (new) | The page harness: a DOM shim built from `src/grid/event.html`, the page's own scripts, a decision submitted through the page's form, and the history card as rendered — with `--history-failure` for each refusal. |
| [`tests/fixtures/grid/event/README.md`](../../../tests/fixtures/grid/event/README.md) | The fixture documentation for the three decisions, the read-back and the second harness. |
| [`tests/test_grid_event.py`](../../../tests/test_grid_event.py) | 30 → 36 tests: the both-orders decision sequences, the cutoff rule read off the recorded flow, the three history failures at the adapter and at the page, and the live assertions moved to three decisions. |

### Finding 1 (important): a later decision snapshots the current accepted state

The defect: every decision sent `audit_cutoff: event_seeded_at`, so after a **revise** the head
the case had accepted was outside the snapshot, and the next decision was refused `STALE_HEAD`
(the reviewer reproduced `revise → retain`). The fix keeps the event's historical information
cutoff for the compile and moves only the audit: the adapter starts at the seeding instant, and
after each saved decision it reads the accepted outlook back (`POST
/v1/tenants/<t>/cases/<c>/read` with the receipt's `outlook_ref`) and takes that record's own
`recorded_at` — the server's clock; the browser's clock decides nothing — as the next snapshot's
cutoff. A read that fails leaves the previous instant and the next decision refuses with a code
and a sentence rather than snapshotting stale state.

The rule is proven three ways: the recorded flow (retain, revise, **retain**) saves its third
decision through the real repository and the committed fixture re-derives it record by record
(`RecordedFlow::test_the_recorded_flow_is_the_flow_the_routes_accept`); the fixture's own
cutoffs are asserted equal to the seeding instant and the two accepted instants
(`::test_each_decision_audits_the_state_the_previous_one_accepted`); the same three decisions
run over HTTP against the real application in `LiveServer::test_the_adapter_runs_the_judge_path_over_http`.
The old failure is kept as a control, so the rule is not vacuous:
`JudgeFlow::test_the_seeding_instant_cannot_see_a_revision_the_session_has_accepted` snapshots a
second decision at the seeding instant and gets `STALE_HEAD` — and
`JudgeFlow::test_a_retain_after_a_revise_saves_and_the_history_shows_both` runs the same
sequence the adapter's way and saves, with the retained value the revision's (95.5 MW).

### Finding 2 (important): a failed history read is shown, never an empty history

The defect: `history()` answered `[]` for a non-OK status and for a body that was not a list,
so a refusal was indistinguishable from "nothing recorded". The design file is read-only for
this seat (stop condition), and its renderer draws every row it is given — `who`, `t`, `what`,
`reason` — so the fix lives entirely in the adapter: a failed read is **one row** in the list,
`{t: '', who: 'History unavailable', what: '<code>: <sentence>', reason: ''}`, with the same
code and sentence `decide` shows and no invented timestamp or entry. An open session that has
recorded nothing is still an empty list (correct, and the load path before the first action);
the refusal row appears when a read of an opened session fails.

At the adapter: `RecordedFlow::test_a_history_failure_is_the_code_and_a_sentence_in_the_history`
covers authorization (`401 UNAUTHENTICATED`), storage (`503 STORAGE_UNAVAILABLE`) and a
malformed body (`200` that is not a list); `::test_a_refusal_is_the_code_and_a_sentence` keeps
the unknown-code path (`HTTP 500`). On the page: the new harness runs the page's own scripts,
submits the decision through the page's form and shows the refusal in the history card —
`RenderedPage::test_a_failed_history_read_is_shown_in_the_history_card` for the three kinds and
`::test_the_page_records_the_decision_and_shows_it_in_history` for the plain flow (rail through
decision, `Saved · receipt event:pedc-u2-2026-09-21:retain:1`, the entry with
`You (this session)` and its reason, no console message). The route's own `UNAUTHENTICATED`
code is anchored live in `LiveServer::test_the_session_and_the_pages_over_http`.

### Not changed

- The design file `src/grid/event.js` and the rest of `src/grid/`'s design files are untouched.
- No frozen contract, acceptance text, route, route shape, `src/api/__init__.py`, `src/demo/*`,
  `src/api/hosted.py`, `Dockerfile`, `.dockerignore` or `scripts/deploy/walkthrough.py` changed;
  `tasks.json` is untouched (this task's state is already `in_progress`, and no other field or
  task may change). No test was weakened, skipped or deleted: the three live tests keep their
  `GRID_EVENT_PYTHON` skip and were run with it below.
- The reviewer's note on the shape fixture (checklist 1, not a finding row) stands unchanged:
  `view.json` still carries `judgment: null`, because the judgment block the page renders is
  converted by the orchestrator from a live `result.json` that lives in the ignored run
  directory; retyping it here would invent a receipt. The real baked view model is GRID-1's, and
  the adapter passes `judgment` through unchanged.
- `docker build` is still not run in this seat (as in rework 1).

### Commands and results (this worktree, 2026-10-14, reworked tip)

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 36 tests in 1.331s

OK (skipped=3)          # the three live-application tests, run below

$ GRID_EVENT_PYTHON=.local/h1-venv/bin/python /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 36 tests in 2.336s

OK                      # the real demo application on loopback, three decisions over HTTP

$ /usr/bin/python3 -m unittest discover -s tests
Ran 624 tests in 15.487s

OK (skipped=12)         # 618 before this rework; the six added tests are the difference

$ GRID_EVENT_PYTHON=.local/h1-venv/bin/python .local/h1-venv/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event
Ran 99 tests in 5.411s

OK                      # 93 before this rework

$ /usr/bin/python3 -m unittest tests.test_hosted_config
Ran 63 tests in 1.289s

OK (skipped=7)          # unchanged

$ node tests/fixtures/grid/event/run.mjs --root .
{"ok": true, "transport": "recorded", "problems": [],
 "flow": {"decisions": [{"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:retain:1"},
                        {"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:revise:2"},
                        {"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:retain:3"}],
          "history": [[{"t": "14 Oct 2026, 10:01 Manila", "what": "Retained 83.7 MW", …}],
                      [{"what": "Revised to 95.5 MW", …}, {"what": "Retained 83.7 MW", …}],
                      [{"what": "Retained 95.5 MW", …}, {"what": "Revised to 95.5 MW", …},
                       {"what": "Retained 83.7 MW", …}]]},
 "history_failures": {"unauthorized": {"history": [{"who": "History unavailable",
        "what": "UNAUTHENTICATED: the judge session is no longer valid; reload the page"}]},
   "storage": {"history": [{… "what": "STORAGE_UNAVAILABLE: the demo store is unavailable; try again"}]},
   "malformed": {"history": [{… "what": "HTTP 200: the history answer is not a list of entries"}]}},
 "local": {"decision": {"ok": false, "message": "Decisions are recorded on the hosted demo."}, "history": []},
 "refusal": {"decision": {… "STALE_HEAD: the case moved since this page loaded; reload and decide again"},
             "history": [{"who": "History unavailable", "what": "HTTP 500", …}]}}

$ node tests/fixtures/grid/event/render.mjs --root .
{"ok": true, "errors": [],
 "afterLoad": {"history": {"hidden": true}, …},                         # nothing before the first action
 "decision": {"status": "Saved · receipt event:pedc-u2-2026-09-21:retain:1",
              "rail": ["done", "done", "done", "done"]},
 "history": {"hidden": false, "html": "<li class=\"new\"><div class=\"h-head\"><span>You (this session)</span>
              <span>14 Oct 2026, 10:01 Manila</span></div><div class=\"h-what\">Retained 83.7 MW</div>
              <div>Fixture decision: the trip puts the assumed availability in question.</div></li>"},
 "calls": ["GET /grid-data/events/pedc-u2-2026-09-21.json", "POST /demo/session", "GET …/pedc-…",
           "POST …/snapshots", "POST …/compile", "POST …/reviews", "POST …/read", "GET …/history"]}

$ node tests/fixtures/grid/event/render.mjs --root . --history-failure storage
history html: <li class="new"><div class="h-head"><span>History unavailable</span><span></span></div>
              <div class="h-what">STORAGE_UNAVAILABLE: the demo store is unavailable; try again</div><div></div></li>
              # the 401 and 200-not-a-list modes likewise, each shown where the history belongs

$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check
OK: view.json and flow.json reproduce; 3 decisions, 3 history entries,
information cutoff 2026-09-21T13:39:37+08:00

$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
OK: 14 records, 2 pairs, 4 compiles, 0 committed reviews (none by design); bundle probe-bundle.v5;
fixture digest 26ba43bf…; trip/t0 omissions verified; composed labels recomputed

$ NOWCAST_ENV=demo <venv>/bin/python -m uvicorn src.api.hosted:app --factory \
      --host 127.0.0.1 --port <free port> --no-access-log          # GRID_DATA_DIR set
$ /usr/bin/python3 scripts/deploy/walkthrough.py --port <same port>
36/36 checks passed on the container port

$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/plan.py scope GRID-3 f429d24     → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/repo.py check                    → PASS (317 Markdown files, 1704 local links)
```

### Post-commit verification (commit `35d649b`)

The verify command, the suite, the harnesses and the structural checks re-run on the committed
tree, with the same results:

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event        → Ran 36 tests … OK (skipped=3)
$ GRID_EVENT_PYTHON=<venv>/bin/python /usr/bin/python3 -m unittest tests.test_grid_event
                                                            → Ran 36 tests … OK
$ /usr/bin/python3 -m unittest discover -s tests            → Ran 624 tests in 13.481s … OK (skipped=12)
$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event        → Ran 99 tests … OK
$ node tests/fixtures/grid/event/run.mjs --root .           → {"ok": true, "problems": []}
$ node tests/fixtures/grid/event/render.mjs --root .        → ok true, "Saved · receipt
      event:pedc-u2-2026-09-21:retain:1", no console message
$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check       → OK: 3 decisions, 3 history entries
$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/repo.py check                    → PASS (317 Markdown files, 1704 local links)
```

### Unfinished items and the exact next action

Nothing in this task's acceptance is unfinished, and no stop condition was hit. The next action
is **re-review of `task/GRID-3`** by the reviewer who is not the author, against `f429d24` (the
base the review record names for the re-review), re-running the verify command, the suite and
both harnesses rather than trusting this record. The standing hand-backs from rework 1 are
unchanged: the orchestrator's scratch build on this tip (this seat cannot run `docker`), the
live probe bundle seed, `/demo/reset` not touching the event case, and GRID-1's real snapshot
that makes the page's baked view model the real one.

## Orchestrator page evidence with the real converted judgment (2026-10-14 03:2x)

Answers designated review 2's verification gap. The orchestrator's converter
(`docs/work/grid-desk/reference/event_judgment.py`) turned the saved live run `pedc-live-001-trip` into the baked
`events/pedc-u2-2026-09-21.json`, which the live service serves (`release/poc-2026-10-14`, revision `grid-nowcast-00005-kxh`).
Chrome on `https://grid-nowcast-adcri4pd6q-as.a.run.app/event/pedc-u2-2026-09-21`: label `challenges`, rule
`outage_or_later: Q2=forced_outage, Q3=same on an availability kind`, by `gemini-3.8-flash · Vertex AI · live`; 8 question
rows, 4 phrasings each, all agreeing; answers 08PEDC_U02 (shown "08PEDC U02", a converter display bug the orchestrator
fixes), forced outage, same, no, no, yes, yes, challenges; receipt "4 phrasings × 8 questions · max flip rate 0 · 9,743
tokens in, 1,784 out · 11.1 s · request 512a7faa6554… · probe:e575d3c9e91a6e…"; advisory quote shown. Decisions recorded
on the same page in hosted mode earlier tonight (Retain twice, live; Investigate and Revise 0 MW in the image) each saved
with a receipt and appeared in the history (release record, `docs/work/grid-desk/release-poc-2026-10-14.md`).

## Rework 3 (2026-10-14, executor seat): designated review 2's important finding

The rework instruction: fix every blocking and important finding in the
[review record](../reviews/GRID-3.md), inside the allowed paths. Designated review 2 lists no
blocking row for this seat — its scope check passes at `f429d24`, the base it names for the
re-review — one important row on the refresh that follows a saved decision, and one important
row about cited-judgment evidence. The first is fixed and tested here; the second is disposed
of below, because the review's own closing paragraph answers it with the orchestrator's page
evidence. No minor rows were listed.

| Path | Change |
|---|---|
| [`src/grid/event-api.js`](../../../src/grid/event-api.js) | The read-back after a save is no longer swallowed: `adopt` returns its outcome, a failure leaves the accepted outlook `pending` on the session, the save's answer keeps its receipt and names the failure beside it, and the next decision re-reads the accepted outlook before it sends anything. |
| [`tests/fixtures/grid/event/run.mjs`](../../../tests/fixtures/grid/event/run.mjs) | Four read-back failure scenarios — an HTTP refusal, a transport error, a body that is not JSON and a body that carries no accepted instant — each followed by a second decision that re-reads, then saves; the recorded transport grows the `readFailure` hook that injects exactly one failure. |
| [`tests/fixtures/grid/event/render.mjs`](../../../tests/fixtures/grid/event/render.mjs) | `--refresh-failure <mode>` for the same four: what the page's own handler leaves in the status line, the rail and the history card. |
| [`tests/fixtures/grid/event/README.md`](../../../tests/fixtures/grid/event/README.md) | The new scenario family, documented; the regenerate block gains one command. |
| [`tests/test_grid_event.py`](../../../tests/test_grid_event.py) | 36 → 38 tests: the adapter's four failures with the retry's exact call sequence and the accepted snapshot instant, and the page's four, each with the saved receipt and the failure in the status line. |

### The finding (important): a failed refresh after a saved decision

The defect the reviewer reproduced: the read that follows a save — `POST .../read` of the
receipt's accepted outlook, which is how the adapter learns the instant the next snapshot must
audit — was ignored when it failed. An HTTP refusal (the reviewer's `503 STORAGE_UNAVAILABLE`
after a revise) left the previous audit cutoff in place, so the next decision snapshotted the
seeding instant where the case had accepted a later one; the reviewer replayed that cutoff
through the real repository and the next retain is refused `STALE_HEAD`. A transport error was
worse than silent: `adopt` threw, `decide`'s outer handler turned it into `{ok: false}`, and the
page reported a failure for a decision that had already committed.

The fix, in the adapter only (the design file is read-only for this seat, and its renderer shows
exactly one status line and the history list):

- `adopt` returns `{ok, message}` and every way the read can fail is named: the route's code and
  sentence for a refusal, `The demo could not be reached: <reason>` for a transport error, and
  `HTTP <status>: the read answer names no accepted instant` for a body that carries none. All
  of them leave the accepted outlook `pending` on the session: the session is behind the case's
  accepted state and no decision may be sent on the old cutoff.
- The save's answer keeps `ok: true` — the decision *is* recorded — and its message carries the
  receipt **and** the failure: `Saved · receipt <key> · the accepted state could not be re-read:
  <code>: <sentence>`. The page shows that line as it shows every other refusal, and its rail
  completes.
- The next decision re-reads the accepted outlook first, before any other request; if the
  re-read still fails, the decision is refused (`The accepted state could not be re-read, so the
  decision was not sent: <code>: <sentence>`) and nothing is sent. When it succeeds, the
  snapshot carries the instant that read named — never a stale cutoff.
- A receipt that names no accepted outlook (defensive: the frozen receipt always carries
  `outlook_ref`) leaves the session behind rather than guessing, so a cutoff that cannot be
  placed in time is never sent.

Evidence, adapter level (`run.mjs`, recorded transport; the second decision is the review's
"each followed by a second decision that succeeds"):

| Scenario | First decision's answer | Second decision's answer |
|---|---|---|
| `storage` — `503 STORAGE_UNAVAILABLE` | `Saved · receipt event:pedc-u2-2026-09-21:retain:1 · the accepted state could not be re-read: STORAGE_UNAVAILABLE: the demo store is unavailable; try again` | `Saved · receipt event:pedc-u2-2026-09-21:revise:2` |
| `transport` — the connection drops | `… · the accepted state could not be re-read: The demo could not be reached: the connection was dropped` | `Saved · receipt event:pedc-u2-2026-09-21:revise:2` |
| `malformed` — `200`, not JSON | `… · the accepted state could not be re-read: HTTP 200: the read answer names no accepted instant` | `Saved · receipt event:pedc-u2-2026-09-21:revise:2` |
| `no_instant` — `200`, `{}` | `… · the accepted state could not be re-read: HTTP 200: the read answer names no accepted instant` | `Saved · receipt event:pedc-u2-2026-09-21:revise:2` |

The recorded transport still refuses any body that is not the recorded one, so the retry's read
body is the accepted outlook and the second snapshot's body is the recorded accepted instant
(`2026-10-14T02:01:00+00:00`, not the seeding instant). The route sequence of each scenario is
asserted in `RecordedFlow::test_a_failed_refresh_keeps_the_saved_receipt_and_the_next_decision_re_reads`
— `<case>`, `/snapshots`, `/compile`, `/reviews`, `/read` (the failure), `/read` (the retry),
`<case>`, `/snapshots`, `/compile`, `/reviews`, `/read`, `/history`.

Evidence, page level (`render.mjs`, the design file's own handler): for all four modes the
status line shows the receipt and the failure, the rail completes
(`["done", "done", "done", "done"]` — the decision did save), and the history card holds the
entry the page then read, with no console message
(`RenderedPage::test_a_failed_refresh_is_shown_with_the_saved_receipt`).

**The control**, so neither check is vacuous: the adapter as review 2 found it (`435b3bb`, the
commit it reviewed) makes `run.mjs` exit 1 with `the snapshot body is not the recorded state
instant: {"audit_cutoff":"2026-10-14T02:00:00+00:00"}` — the seeding instant the reviewer's
evidence names — and its first answer is the bare `Saved · receipt …` with no failure; the page
harness against the same copy shows that same bare status line. The script lives in the ignored
`.local/grid3-rework3-control/check.py` (not committed), so the control is reproducible after
this commit pins the fixed adapter in `HEAD`.

### Disposition: the cited-judgment evidence row

`tests/fixtures/grid/event/build.py:108` (`judgment: null`) is not a defect in this task's
deliverable, and the review's closing paragraph settles it: "The judgment-evidence row is
answered by the orchestrator's page evidence in docs/work/grid-desk/event.md" — the section
directly above this one, where the converted live run is served by the release and Chrome shows
the label, the rule, the eight question rows with four phrasings each and the four-form receipt.
Nothing in this seat changes for it, and the shape fixture is deliberately left as it is: the
judgment block is the orchestrator's converted receipt from a run directory this worktree does
not hold, and typing one here would invent a model receipt (a stop condition). The page's
judgment rendering is unchanged by this rework.

### Not changed

- The design files (`src/grid/event.js`, `event.html`, `event.css`) are untouched, as the intent
  requires; the adapter is the only runtime file this rework changes.
- No frozen contract, acceptance text, route, route shape, `src/api/__init__.py`, `src/demo/*`,
  `Dockerfile`, `.dockerignore`, `scripts/deploy/walkthrough.py`, fixture (`build.py`,
  `view.json`, `flow.json`) or `tasks.json` field changed. No test was weakened, skipped or
  deleted: the three live tests keep their `GRID_EVENT_PYTHON` guard and were run with it below.

### Commands and results (this worktree, 2026-10-14, reworked tip)

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event -v
Ran 38 tests in 1.264s

OK (skipped=3)          # 36 before this rework; the three live tests run below

$ GRID_EVENT_PYTHON=.local/h1-venv/bin/python .local/h1-venv/bin/python -m unittest \
      tests.test_grid_event -v
Ran 38 tests in 1.893s

OK                      # the real demo application on loopback, three decisions over HTTP

$ /usr/bin/python3 -m unittest discover -s tests
Ran 626 tests in 11.213s

OK (skipped=12)         # 624 before this rework

$ GRID_EVENT_PYTHON=.local/h1-venv/bin/python .local/h1-venv/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event
Ran 101 tests in 3.642s

OK                      # 99 before this rework

$ node tests/fixtures/grid/event/run.mjs --root .
{"ok": true, "transport": "recorded", "problems": [],
 "flow": {"decisions": [{"ok": true, "message": "Saved · receipt event:pedc-u2-2026-09-21:retain:1"}, …]},
 "refresh_failures": {"storage": {"decisions": [{"ok": true, "message": "Saved · receipt
   event:pedc-u2-2026-09-21:retain:1 · the accepted state could not be re-read: STORAGE_UNAVAILABLE:
   the demo store is unavailable; try again"}, {"ok": true, "message": "Saved · receipt
   event:pedc-u2-2026-09-21:revise:2"}], …}, "transport": {…}, "malformed": {…}, "no_instant": {…}}}

$ node tests/fixtures/grid/event/render.mjs --root . --refresh-failure transport
status: Saved · receipt event:pedc-u2-2026-09-21:retain:1 · the accepted state could not be
        re-read: The demo could not be reached: the connection was dropped
rail: ["done", "done", "done", "done"]; history holds the entry; errors []
                        # the storage, malformed and no_instant modes likewise

$ /usr/bin/python3 .local/grid3-rework3-control/check.py        # ignored, not committed
the pre-fix adapter fails run.mjs (exit 1, ok=False):
    the snapshot body is not the recorded state instant: {"audit_cutoff":"2026-10-14T02:00:00+00:00"}
    first answer: Saved · receipt event:pedc-u2-2026-09-21:retain:1
    second answer: Saved · receipt event:pedc-u2-2026-09-21:revise:2 (saved anyway, at the stale cutoff)
the page shows the bare receipt, no failure: Saved · receipt event:pedc-u2-2026-09-21:retain:1
36/36 checks passed on the container port

$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check
OK: view.json and flow.json reproduce; 3 decisions, 3 history entries,
information cutoff 2026-09-21T13:39:37+08:00

$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/plan.py scope GRID-3 f429d24     → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/repo.py check                    → PASS (317 Markdown files, 1705 local links)
```

The last three lines of the control script start the container's own entry point on a free
loopback port (`NOWCAST_ENV=demo`, `GRID_DATA_DIR` pointed at `tests/fixtures/grid/page/data`)
and run `scripts/deploy/walkthrough.py` against it: **36/36 checks passed**, as before.

### Post-commit verification (commit `dcbf7b2`)

The verify command, the suite, both harnesses and the structural checks re-run on the committed
tree, with the same results:

```sh
$ /usr/bin/python3 -m unittest tests.test_grid_event        → Ran 38 tests in 1.124s … OK (skipped=3)
$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest tests.test_grid_event
                                                            → Ran 38 tests in 2.026s … OK
$ /usr/bin/python3 -m unittest discover -s tests            → Ran 626 tests in 12.228s … OK (skipped=12)
$ GRID_EVENT_PYTHON=<venv>/bin/python <venv>/bin/python -m unittest \
      tests.test_hosted_config tests.test_grid_event        → Ran 101 tests in 3.681s … OK
$ node tests/fixtures/grid/event/run.mjs --root .           → exit 0, {"ok": true, "problems": []}
$ node tests/fixtures/grid/event/render.mjs --root .        → exit 0, ok true, no console message
$ /usr/bin/python3 tests/fixtures/grid/event/build.py --check
                                                            → OK: 3 decisions, 3 history entries
$ /usr/bin/python3 scripts/plan.py check                    → OK: 49 tasks, 7 gates
$ /usr/bin/python3 scripts/plan.py scope GRID-3 feat/h1-api-persistence
                                                            → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/plan.py scope GRID-3 f429d24     → OK: all changed files inside GRID-3 allowed paths
$ /usr/bin/python3 scripts/repo.py check                    → PASS
```

### Self-review note and the exact next action

The new tests execute the adapter itself (node, recorded transport), the page's own scripts
(the DOM shim) and the three-decision flow over HTTP against the real application; the failure
modes themselves are injected at the transport boundary, because a real server cannot be asked
to fail on demand — the control above shows they are the failures the reviewer reproduced and
that the checks catch the old behaviour. Everything in this task's acceptance is unchanged and
still executed; nothing was reported that was not run. No stop condition was hit: every edit is
inside the allowed paths, no frozen contract, route, design file or acceptance text changed, no
new dependency, credential or network call was added, and the only server touched is the
loopback one this seat starts and stops.

The next action is **independent re-review of `task/GRID-3`** by a reviewer who is not the
author, against `f429d24`, re-running the verify command, the suite and both harnesses rather
than trusting this record. The standing hand-backs are unchanged: the orchestrator's scratch
build on this tip (this seat cannot run `docker`), the live probe bundle seed, `/demo/reset` not
touching the event case, and GRID-1's real snapshot that makes the page's baked view model the
real one.
