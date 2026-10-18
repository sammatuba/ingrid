# Packet: EVAL-5 — first real case, PEDC Unit 2 trip and return, 2026-09-21

Task `EVAL-5` (lane EVAL, milestone M4), route implement, executor agent, on `task/EVAL-5`
stacked on `task/GRID-1` (`d3fb970`), the integration line that carries DATA-1 and CORE-8.
Intent [real-sources/intent.md](../../work/real-sources/intent.md); source profile
[01-so-advisories.md](../../work/foundation-review-2026-10-13/sources/01-so-advisories.md);
permission [`perm:wesm-company-copy:2026-10-13`](../../work/permissions/2026-10-13-wesm-company-copy.md),
signed. Interpreter `/usr/bin/python3` (Python 3.14.4). Everything here is offline: no model,
transport, credential or network call is reachable from the fixture, the builder or any command
below.

**State: `in_progress`, self-review only; re-review is the next action.** The first build went
through designated review 1 (GPT Sol, independent, commit `0c14f26`), whose verdict was
**rework**; [Rework (designated review 1)](#rework-designated-review-1-2026-10-14) below
disposes of every finding and carries the current commands and results. The sections above it
are the first build's record; where the rework superseded a statement in them, the correction
is made in place and named in the rework section. Readings for the reviewer are in
[Decisions inside the stated contracts](#decisions-inside-the-stated-contracts-for-review).

## What changed

| File | Change |
|---|---|
| `tests/fixtures/pedc-u2-2026-09-21/build.py` | New: the case generator and checker. Builds the records with the real DATA-1 readers and the review core, replays the case through `InMemoryRepository`, compiles the four cutoffs, renders `probe-bundle.v5`, answers with the scripted backend and composes through the frozen table; commits no disposition (corrected by the rework — the first build committed two desk reviews here); `--check` replays all of it and compares, writing nothing |
| `tests/fixtures/pedc-u2-2026-09-21/case.json` | New (generated): 14 input records in registration order, the assumption seed, the cutoffs, the two cutoff pairs with every compiled output, the three judged compiles, the empty review state and the workspace summary. Fixture digest `26ba43bfa09b93c14d7981a2ccaa4715a7e3efee48bcdf3bb4660a6e10dbe72e` (rework; the first build's digest was `51185d10…48274a`) |
| `tests/fixtures/pedc-u2-2026-09-21/README.md` | New: provenance, files, rebuild/check commands, the recorded outcome, the digest rule |
| `docs/cases/pedc-u2-2026-09-21/evidence-manifest.json` | New (generated): per source version and passage — publisher, clocks, `availability_basis`, `unknown_reason`, digests, record and passage references; per compile the omissions and context; the advisory-only scope statement |
| `docs/cases/pedc-u2-2026-09-21/mappings.json` | New (generated): the entity and representation, the reviewed correspondence with its free-text forms, validity period, evidence and the superseded unreviewed candidate; no unresolved matches |
| `docs/cases/pedc-u2-2026-09-21/brief.md`, `review.md`, `outlook-revision.md`, `scenario-proposal.md`, `evaluation.md`, `packet.md` | New: the case pack per [first-case.md](../first-case.md), written from the run |
| `docs/work/tasks.json`, `docs/work/PROGRESS.md` | EVAL-5 state `pending` → `in_progress`, note with the first build, row and one log entry |

No frozen contract and no test was changed, weakened, skipped or deleted; no file outside the
allowed paths changed (`plan.py scope` below). `src/` and `tests/test_*.py` are untouched by
this task.

## The run

The case is built, not copied: the four advisories are the `pedc_u2_21sep` rows of the
committed WESM sample and the register run is the `08PEDC_U02` run covering 2026-09-21 from the
committed register sample, each keeping its real clock (posting instants, the run's first
trading day). The desk's own acts (the reviewed mapping 00:05, the seed 00:10) and the replay's
derived records sit on the 2026-09-21 timeline as a **reconstruction** at the positions the
compile replay requires (rework; the first build presented this as the desk's own day-of
timeline, including a 16:02 dispatch record time that is now the real 2026-10-14 assembly
instant).

- **Identity.** `08PEDC_U02` as `GeneratingUnit`; representation `pedc-availability.v1` with
  `available_capacity_mw` (`available_capacity`, MW). The register reader's `unreviewed`
  candidate is registered as revision 1 and superseded by the case assembly's `reviewed`
  revision 2 over the same run's source version (free-text forms "PEDC U2" and "PEDC Unit 2",
  both checked to occur in the case's own passages; rework: the reviewer is the assembly, and
  the payload's `reconstruction` block states it).
- **Prior assumption.** Seeded by the case assembly on 2026-10-14 at the reconstructed
  2026-09-21 00:10 position from the run's capacity — the value `83.7` is read from
  `run.capacity_mw`, never typed; valid period the case day.
- **Dispatch.** A sixth source with `known_at: null` and `unknown_reason` naming both unknowns
  (`RUN_TIME absent from the copy`, so first availability is unknown; the copy and the profile
  record no publication instant), carrying the schedule readings the source profile records for
  this resource and day, with its real publisher and `derived_from` that document. Its
  `published_at` is the profile's own date, labelled `published_at_approximate: true` (rework;
  the first build asserted `2026-09-21T16:00:00+08:00`, a schedule interval, as its publication
  time). Omitted from every compiled context as `UNKNOWN_AVAILABILITY`.
- **Cutoffs.** Two pairs (working paper 5.4), each with one shared snapshot whose audit cutoff
  is the pair's earliest information cutoff: trip 13:39:36 / 13:39:37 around V133937's posting,
  return 15:55:55 / 15:55:56 around V155556's, all `+08:00`.
- **Judgment.** `render_bundle` renders the frozen request (4 forms, 32 questions); the scripted
  backend's reading answers it; `compose` and `receipt` produce the labels. No label is stored
  before the run; `--check` recomputes every one.
- **Review.** The run stops after judging: no disposition is committed, and the decision at
  each cutoff is left to the demo's judge or the analyst (rework; the first build committed two
  pre-written desk decisions at 13:41 and 15:57 under the actor id `desk-analyst`).

Recorded outcome: trip/T0 blocked `MISSING_INPUT` (no passage known) with omissions V133937,
V135622, V141257, V155556 `LATER_AVAILABILITY` and the dispatch `UNKNOWN_AVAILABILITY`;
trip/T1 **challenges** (`outage_or_later`); return/T0 **challenges** (`outage_or_later`);
return/T1 **supports** (`availability_confirmed`). All three judged compiles stable
(`unstable: false`, 4 forms). The replayed case holds 23 records: 14 inputs in the fixture plus
2 snapshots, 4 compiled tasks, 1 assumption, 1 seed decision and 1 dependency impact; no
outlook revision exists (rework; the first build held 27 records with 3 review decisions and
2 outlook revisions).

## Acceptance

| Criterion (brief) | Exact check | Result |
|---|---|---|
| T0 omits the trip advisory `LATER_AVAILABILITY` and dispatch `UNKNOWN_AVAILABILITY` | `build.py --check`, acceptance block, and the fixture's recorded omissions | **met** — trip/T0's omissions are exactly V133937/V135622/V141257/V155556 `LATER_AVAILABILITY` + dispatch `UNKNOWN_AVAILABILITY`; the dispatch is omitted `UNKNOWN_AVAILABILITY` from all four compiles; `--check` names both lines and fails on drift (negative control 2) |
| Composed labels recorded as run, never written first | `build.py --check` recomputes each `composed` block from the recorded reading through the frozen `compose` | **met** — no label exists anywhere before the run; each label is the output of `compose` over the reading beside it, recorded from the run with the command in this packet; a hand-edited label is detected (negative control 1) |
| Advisory-only stated if no external document is supplied | `inputs.external_document` is `null`; the scope statement in `evidence-manifest.json` and the packet | **met** — the case's evidence is the four advisories; the manifest's `evidence_scope` reads advisory-only, `brief.md` and this packet repeat it, and a supplied document would be a fifth source in a new revision |

Intent acceptance table, items not in the brief:

| Criterion | Check | Result |
|---|---|---|
| Four advisories, register run, reviewed mapping, prior assumption, dispatch as record families | fixture `records` and the source table above | **met** — 6 source versions (4 advisories, the run, the dispatch), 5 passages, 2 mapping revisions, 1 seeded assumption |
| Real records validate and carry the signed pair | the replay registers and validates every record under the checkout's own registry | **met** — all 23 records carry `synthetic: false` and the permission reference; nothing was injected, the registry is the signed file (rework: 27 before, the four dropped desk records aside) |
| Suite | command below (first build) and the rework section | **met** — `Ran 550 tests … OK (skipped=7)` at the first build; the rework tip's run is in [Rework](#rework-designated-review-1-2026-10-14) |

## Commands and results (first build, 2026-10-14, before the review)

The fixture digest below is the first build's and is superseded by the rework's; the suite and
check results were re-run at the rework tip (see [Rework](#rework-designated-review-1-2026-10-14)).

```sh
$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py
wrote tests/fixtures/pedc-u2-2026-09-21/case.json, docs/cases/pedc-u2-2026-09-21/evidence-manifest.json, docs/cases/pedc-u2-2026-09-21/mappings.json; fixture digest 51185d1066e3687b5c767a99029d6201779b1d34b0a59db701bbe7563b48274a

$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
OK: 14 records, 2 pairs, 4 compiles, 2 reviews; bundle probe-bundle.v5; fixture digest 51185d1066e3687b5c767a99029d6201779b1d34b0a59db701bbe7563b48274a; trip/t0 omissions verified; composed labels recomputed

$ /usr/bin/python3 -m unittest discover -s tests -v
Ran 550 tests in 10.473s

OK (skipped=7)

$ /usr/bin/python3 scripts/plan.py check
OK: 49 tasks, 7 gates

$ /usr/bin/python3 scripts/repo.py check
Checked 309 Markdown files, 1627 local links, 8 skills; bootstrap 1399 words.
PASS

$ /usr/bin/python3 scripts/plan.py scope EVAL-5 feat/h1-api-persistence
OK: all changed files inside EVAL-5 allowed paths

$ bash scripts/h1/test.sh          # the H1 emulator integration suite (extra evidence)
Ran 71 tests in 74.303s

OK
```

Negative controls for `--check` (in-memory tampering and a stubbed registry; nothing written).
The first build's table is kept below for the record; the two controls that parted with the
rework — `reviews: differs from a fresh build` (no review exists to tamper with now) and the
`reviews` key itself — were replaced by the rework's controls, run at the rework tip:

| Control (first build) | Result |
|---|---|
| untouched fixture | `check passes` |
| composed label flipped to `challenges` | detected: `pairs: a compile, composition or receipt differs from a fresh replay` |
| trip/T0 omission code changed | detected: `pairs: …` |
| advisory V133937 `original_text` edited | detected: `records: differs from a fresh build` |
| trip T0 cutoff moved one second | detected: `cutoffs: differs from a fresh build` |
| trip review disposition changed to `retain` | detected: `reviews: differs from a fresh build` — control retired with the reviews (rework) |
| permission registry stubbed empty | refused: `the signed permission record perm:wesm-company-copy:2026-10-13 is not in this checkout's registry` |

## Decisions inside the stated contracts (for review)

1. **The scripted judgment is not stored in the case.** The frozen validator refuses a
   `synthetic_fixture` artifact carrying a real case's provenance
   ([tests/test_review_case.py](../../../tests/test_review_case.py), `H0V2Case`), and no live
   inference is authorized by this task or happened. The judgment therefore lives in the
   fixture, the case pack and [review.md](review.md#model-assisted-readings-as-run) — labelled
   as a deterministic script — and **not** as a `ProbeBundleArtifact`. Nothing reports a
   backend run that did not happen (rework: the two desk decisions that carried
   `judgment_ref: null` are dropped; with no review committed, no decision exists to carry it).
2. **The dispatch source carries the profile's recorded readings, not an export.** The executor
   seat has no `bq`, and the copy's missing `RUN_TIME` is exactly why the source can never be
   evidence at a cutoff; its bytes are the canonical JSON of the readings the source profile
   records, with the assembly named as their publisher and the profile named in `derived_from`,
   and a real export would replace it in a new revision.
3. **No disposition is authored for the desk** (rework). The fixture compiles and judges; the
   decision at each cutoff is left to the demo's judge or the analyst
   ([review.md](review.md#attribution)). The first build committed two pre-written decisions
   (`investigate` at 13:41, `retain` at 15:57) under the actor id `desk-analyst` while
   acknowledging that no analyst session ran — that is what review 1's first finding struck
   down, and the records it questioned are gone.
4. **The register's unreviewed candidate is registered and superseded** by the reviewed
   revision of the same mapping (revision 2), so the case shows the review act itself and the
   repository records the dependency impact; only the reviewed revision is a compile candidate.
5. **The case's own timeline is a reconstruction, named as one** (rework). The sources keep
   their real clocks; the desk's acts (the reviewed mapping 00:05, the seed 00:10) and the
   replay's derived records sit at the positions the compile replay requires, and the records
   that act as the desk say so (the case record's `assembly` block, the mapping's
   `reconstruction` block, the seed's rationale). The compile decisions are cutoffs, not record
   times, which is why trip/T0 still sees the 13:39:37 advisory as `LATER_AVAILABILITY` even
   though the record is registered in the same fixture. The case's own records carry the real
   assembly instant (2026-10-14 01:27 +08:00), not a fictional day-of time.

## Post-commit verification (superseded)

**The heading that stood here cited commit `1002163`, which is not on this branch's log** (the
identifier in commit `0c14f26`'s subject was mistaken for a commit id; no branch in the
repository carries it — review 1's minor). The block's results are superseded by the rework's
own verification below; the digest it names is the first build's. Kept for the record:

```sh
$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
OK: 14 records, 2 pairs, 4 compiles, 2 reviews; bundle probe-bundle.v5; fixture digest 51185d1066e3687b5c767a99029d6201779b1d34b0a59db701bbe7563b48274a; trip/t0 omissions verified; composed labels recomputed

$ /usr/bin/python3 -m unittest discover -s tests
Ran 550 tests in 10.526s

OK (skipped=7)

$ /usr/bin/python3 scripts/plan.py check
OK: 49 tasks, 7 gates

$ /usr/bin/python3 scripts/repo.py check
Checked 309 Markdown files, 1627 local links, 8 skills; bootstrap 1399 words.
PASS

$ /usr/bin/python3 scripts/plan.py scope EVAL-5 feat/h1-api-persistence
OK: all changed files inside EVAL-5 allowed paths
```

## Unfinished items and exact next action

1. **Re-review of `task/EVAL-5`** (the reviewer's record lands at
   `docs/work/reviews/EVAL-5.md`, written by the reviewer, not by this task) against this
   packet and the case pack, after the rework below; only a reviewer's `accept` record sets the
   task `done`. First questions for the reviewer: decision 1 (the judgment is not stored — is
   the recording sufficient evidence for the case's judgment step?), decision 3 and the rework
   section (are the assembly attribution and the reconstruction statement sufficient, and is
   the dispatch's labelled publication stand-in acceptable where the frozen validator admits no
   null `published_at`?) and whether the stand-in value should be the profile's date or another
   labelled form.
2. **A live judgment on this case is a later, authorized task**: the deployed demo's event page
   produces it (`grid-desk`), and it is the only way an artifact with real provenance can be
   attached (`execution_mode: live_inference`). Until then the case holds no judgment artifact.
   The orchestrator's 2026-10-14 live probe run on this case is recorded in
   [evaluation.md](evaluation.md#live-probe-run-on-this-case-recorded-elsewhere); it changes
   nothing in this fixture.
3. **The day-ahead `RUN_TIME` re-export** (DATA-1 open input) remains the only path to using
   dispatch as a dated baseline; the dispatch source here stays unknown-availability by design.

Exact next action: run the re-review of `task/EVAL-5` over the rework commit; the reviewer's
first questions are listed above.

## Self-review (executor, labelled as such; not an independent review)

Written for the first build; the rework's own self-review is at the end of the
[Rework](#rework-designated-review-1-2026-10-14) section.

- **Scope.** Only the fixture directory, the case directory, `docs/work/tasks.json` and
  `docs/work/PROGRESS.md` changed; `plan.py scope` prints OK. No frozen contract, acceptance
  text or test touched.
- **Facts.** Every advisory byte, clock, digest and category comes from the committed WESM
  samples through the DATA-1 readers; the register capacity and run come from the committed
  register sample; the profile-derived dispatch bytes are quoted and cited; nothing was typed
  from memory, and the composed labels were read off the run's output.
- **Truthful labels.** The backend is labelled a script in the fixture, the pack and here;
  `live_calls: 0`; no model, analyst or run claim is made anywhere, and no stored artifact
  pretends to come from a backend that did not run.
- **Residual risk.** The readings are the case assembly's annotation, cited per answer but not
  analyst-validated; the dispositions the first build recorded were the case assembly's and
  were struck down by review 1 (rework decision 3); and the acceptance checks live in the
  fixture's own `build.py --check`, not in the offline suite — the suite's count is unchanged
  because EVAL-5 adds no test file. Its own paths hold no test module, and the test files its
  scope inherits belong to the ancestor tasks' artifacts (EVAL-1's fixtures and EVAL-2's
  ablation test, `tests/test_wesm_sources.py`, `tests/test_probe_bundle.py`,
  `tests/test_review_case.py`) and are not edited here. A later change that broke this replay
  would be caught by `build.py --check`, not by `discover`.

## Rework (designated review 1, 2026-10-14)

Review record: [docs/work/reviews/EVAL-5.md](../../work/reviews/EVAL-5.md) (the reviewer's text,
not edited by this task) with the orchestrator's direction recorded under the verdict. Every
finding is disposed below; the composed labels, the cutoffs and the acceptance lines are
unchanged by this rework. The statements corrected in place above are named in these rows: the
"What changed" table's build.py and case.json rows, the Identity / Prior assumption / Dispatch /
Review bullets, the intent-acceptance real-records row, Decisions 1, 2, 3 and 5, and the
post-commit heading.

| Review row | Disposition |
|---|---|
| important `build.py:255` — fabricated historical review provenance enters real records | **fixed**: the records name who actually acted. The actor is `eval-5-case-assembly` (the EVAL-5 case assembly: orchestrator and executor seats, assembling 2026-10-14); the case record's `assembly` block, the reviewed mapping's `reconstruction` block and the seed's rationale each state the assembly, the real date and that the record's 2026-09-21 position is the reconstruction the compile replay requires (a real 2026-10-14 position cannot precede the cutoffs — the repository's mapping guard and snapshot-head filter would block every compile). The case and dispatch records now carry the real assembly instant (`2026-10-14T01:27:00+08:00`, the build minute) as their own `recorded_at`, replacing the day-of fictions (`2026-09-21T00:00:00`, `16:02`); every source keeps its real clock (`known_at`, posting instants), as the direction requires |
| important `build.py:265` — unsupported publication clock promoted to source metadata | **fixed, with one form change**: the summary body now carries `published_at: null` with its own `unknown_reason` (the copy and the profile record no publication instant), the record's `publisher` names the real author of the bytes (the case assembly's digest, not an IEMOP export) with `derived_from` the source profile document, and `unknown_reason` names both unknowns. The record's `published_at` cannot be null: the frozen validator requires a temporal (`src/review/records.py:395`, `temporal(p["published_at"])` refuses null with `MALFORMED_TIME`). It is therefore the owner-ruled stand-in form — the profile document's own date (`2026-10-13`, date precision) labelled `published_at_approximate: true`, exactly as the accepted DATA-1 reader does for the register (Round 9). No schedule interval is asserted as publication anywhere |
| important `build.py:112` — return notice used to confirm an unsupported quantitative assumption | **fixed**: the retain rationale and both other pre-written decisions are gone from the fixture (direction item 3), and the pack no longer reads the return notice as confirming 83.7 MW for the day. [review.md](review.md) now states that the notice reports the re-online and states no capacity, that it does not establish the seeded value or resolve the whole-day assumption, and that the trip contradicts uninterrupted day-level availability; [outlook-revision.md](outlook-revision.md) carries the same in its remaining-uncertainty section. The accepted position is the seed only; no outlook revision exists |
| row 6's second half — historical review/capture times authored without source records | **fixed** with the same three changes: the surviving desk acts (the mapping review, the seed) carry the assembly's real actor, date and instant in their own payload text, and the case record states the reconstruction; no desk act is dated to a 2026-09-21 clock without saying what that position is |
| rows 5 and 8 — generated desk history presented as real provenance | **fixed**: no disposition is pre-written at all. The fixture compiles and judges, then stops: `review_state.committed` is `0`, no `OutlookRevision` exists, and the decision at each cutoff is left to the demo's judge or the analyst. `--check` now refuses a fixture that gains a disposition or an outlook history (controls below) |
| minor — the post-commit heading cited `1002163`, absent from the branch log | **fixed in place**: the heading now reads "Post-commit verification (superseded)" and names the mistake; no branch in this repository carries `1002163` (it was the trailing token of commit `0c14f26`'s subject). The block is kept for the record and superseded by this section's results |
| direction item 4 — note the live result in evaluation.md | **done**: [evaluation.md](evaluation.md#live-probe-run-on-this-case-recorded-elsewhere) records the orchestrator's 2026-10-14 live probe run on this case (`docs/work/grid-desk/live-run-2026-10-14.md` on `feat/h1-api-persistence`, named rather than linked because the file is not on this branch): both live compiles composed `challenges`, the scripted reading composes `supports` at return/T1, the disagreement is for the owner, and this fixture's labels stay exactly as run |

What the rework does **not** change: the four cutoffs and the pair structure, every source's
`known_at`, the compiled contexts and omissions, the scripted readings, the composed labels, the
frozen contracts and the acceptance items. The fixture digest moves from `51185d10…48274a` to
`26ba43bfa09b93c14d7981a2ccaa4715a7e3efee48bcdf3bb4660a6e10dbe72e` because the records'
provenance and the dropped decisions changed, not because any output did.

### Commands and results at the rework tip

```sh
$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py
wrote tests/fixtures/pedc-u2-2026-09-21/case.json, docs/cases/pedc-u2-2026-09-21/evidence-manifest.json, docs/cases/pedc-u2-2026-09-21/mappings.json; fixture digest 26ba43bfa09b93c14d7981a2ccaa4715a7e3efee48bcdf3bb4660a6e10dbe72e

$ /usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check
OK: 14 records, 2 pairs, 4 compiles, 0 committed reviews (none by design); bundle probe-bundle.v5; fixture digest 26ba43bfa09b93c14d7981a2ccaa4715a7e3efee48bcdf3bb4660a6e10dbe72e; trip/t0 omissions verified; composed labels recomputed

$ /usr/bin/python3 -m unittest discover -s tests -v
Ran 550 tests in 9.390s

OK (skipped=7)

$ /usr/bin/python3 scripts/plan.py check
OK: 49 tasks, 7 gates

$ /usr/bin/python3 scripts/repo.py check
Checked 310 Markdown files, 1638 local links, 8 skills; bootstrap 1399 words.
PASS

$ /usr/bin/python3 scripts/plan.py scope EVAL-5 feat/h1-api-persistence
OK: all changed files inside EVAL-5 allowed paths

$ bash scripts/h1/test.sh          # the H1 emulator integration suite (extra evidence)
Ran 71 tests in 41.397s

OK
# (the script's own exit line in the first invocation: "Script exited successfully (code 0)")
```

Negative controls at the rework tip (`.local/eval/check_controls_rework.py`, ignored, in
memory, nothing written):

```sh
$ /usr/bin/python3 .local/eval/check_controls_rework.py
passes    untouched                                  check passes
detected  composed label flipped to challenges       pairs: a compile, composition or receipt differs from a fresh replay
detected  trip/t0 omission code changed              trip/t0 must omit the trip advisory with LATER_AVAILABILITY; pairs: a compile, composition or receipt differs from a fresh replay
detected  advisory V133937 original_text edited      records: differs from a fresh build
detected  trip T0 cutoff moved one second            cutoffs: differs from a fresh build
detected  a review disposition appears               no review disposition may be pre-written: the seed's initial acceptance is the only ReviewDecision and no outlook revision exists, so each cutoff's decision is left to the judge or the analyst; workspace: differs from a fresh build
detected  an outlook revision appears                the case must hold no outlook history; the decision is not pre-written; workspace: differs from a fresh build
detected  assembly block stripped from the case      the case record must name its assembly and mark the timeline a reconstruction; records: differs from a fresh build
detected  dispatch published_at back to the 16:00 interval the dispatch publication clock must stay an approximate stand-in and name its real publisher and provenance; records: differs from a fresh build
detected  dispatch publisher back to the IEMOP copy  the dispatch publication clock must stay an approximate stand-in and name its real publisher and provenance; records: differs from a fresh build
detected  review_state claims a committed review     no review may be committed by this fixture; review_state: differs from a fresh build
detected  mapping reconstruction stripped            the reviewed mapping must name the assembly that recorded it; records: differs from a fresh build
refused   permission registry stubbed empty          the signed permission record perm:wesm-company-copy:2026-10-13 is not in this checkout's registry
controls: all as expected
```

### Self-review at the rework tip (executor, labelled as such)

- **Acceptance.** All three brief items still hold, unchanged: trip/T0's omissions are exactly
  V133937/V135622/V141257/V155556 `LATER_AVAILABILITY` plus the dispatch
  `UNKNOWN_AVAILABILITY`; every composed label is still the frozen `compose` output over the
  reading beside it, recorded from the run; the manifest still reads advisory-only with
  `external_document: null`. The fixture digest changed; no label, cutoff or omission did.
- **Facts.** Nothing in this rework was inferred: the assembly date and instant are the real
  ones of this build; the profile document's date is its own `Status:` line; the actor id names
  the seats that did the work. No analyst, model or cloud run is claimed anywhere, and the live
  run noted in evaluation.md is quoted from the orchestrator's record, not this task's.
- **Residual risk.** (a) The dispatch `published_at` stand-in is the profile's date labelled
  approximate; the direction's literal "null" is not representable under the frozen h0.v2
  validator, and the reviewer may prefer another labelled form — recorded here rather than
  worked around. (b) The mapping review and the seed still carry reconstructed 2026-09-21
  positions, because the repository's compile guards require them; the records say so, but the
  envelope times themselves cannot be real without changing the replay semantics. (c) The
  review of each cutoff is now nobody's in this fixture by design; the demo's judge or the
  analyst supplies it.
- **Scope.** Only `tests/fixtures/pedc-u2-2026-09-21/` and `docs/cases/pedc-u2-2026-09-21/`
  changed, with `docs/work/tasks.json` and `docs/work/PROGRESS.md`; `plan.py scope` prints OK.
  No frozen contract, acceptance text, test, review record or feedback file was touched.
