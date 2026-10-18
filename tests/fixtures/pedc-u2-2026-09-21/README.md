# PEDC Unit 2 real-case fixture, 2026-09-21 (EVAL-5)

The first **real** case of the review desk, built from the company WESM copy and cited to the
signed permission record
[`perm:wesm-company-copy:2026-10-13`](../../../docs/work/permissions/2026-10-13-wesm-company-copy.md).
Every record here is `synthetic: false` with that `permission_ref`; the case's advisory text is
quoted under the permission's fixtures-and-tests clause.

**Assembled 2026-10-14 by the EVAL-5 case assembly (`eval-5-case-assembly`, the orchestrator
and executor seats).** Every record says who wrote it: the case record's `assembly` block, the
reviewed mapping's `reconstruction` block and the seed's rationale all name the assembly and
the real date. Each **source** keeps the clock it really carries (`known_at`, posting instants);
the desk's own acts (the mapping review, the seed) and the replay's derived records carry the
2026-09-21 positions the compile replay requires, and the records that act as the desk name
that timeline a **reconstruction** — no analyst session ran, and the desk's disposition at each
cutoff is left to the demo's judge or the analyst (review 1, 2026-10-14).

| File | What it is |
|---|---|
| `case.json` | The case fixture: the 14 input records in registration order, the assumption seed, the four compile cutoffs, the two cutoff pairs with every compiled output, the fixture-backend judgment of three compiles, the empty review state, and the resulting workspace summary |
| `build.py` | Generator and checker; writes `case.json` and the two generated documents under `docs/cases/pedc-u2-2026-09-21/`, or with `--check` replays everything and compares (writes nothing) |
| `README.md` | This file |

The case's narrative artifacts are under
[docs/cases/pedc-u2-2026-09-21/](../../../docs/cases/pedc-u2-2026-09-21/packet.md); the task
record is that directory's `packet.md`.

```sh
/usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py           # write
/usr/bin/python3 tests/fixtures/pedc-u2-2026-09-21/build.py --check   # replay, compare, write nothing
```

## Where the facts come from

The four advisories are the `pedc_u2_21sep` rows of
[tests/fixtures/wesm/advisories-sample.jsonl](../wesm/advisories-sample.jsonl) (real rows,
exported by the orchestrator seat and committed byte-for-byte; `sha256`
`974e7980830beb85575d9a42c6513b3091124f3b9cee2edd01d8ca7b571e9f05`). The register run is the
`08PEDC_U02` run covering 2026-09-21 from
[tests/fixtures/wesm/registry-pedc-sample.jsonl](../wesm/registry-pedc-sample.jsonl)
(`sha256` `4d366a8a41fdfd962bb5437c86ca18175cc2a8c63f7aad12765acbc99738eaeb`): 2026-02-05 to
2026-09-29, 83.7 MW, participant PEDC, one `unreviewed` candidate from the reader. Each
advisory carries its real posting instant; the register run carries its first trading day.

The dispatch source is **not** an exported RTD row set: the executor seat has no `bq`, and the
copy carries no `run_time` column, so the revisions cannot be ordered. Its `original_text` is
the canonical JSON of the schedule readings that the source profile records for this resource
and day ([01-so-advisories.md](../../../docs/work/foundation-review-2026-10-13/sources/01-so-advisories.md),
"First real case"); the record names its real publisher (the case assembly's digest, not an
IEMOP export), its provenance (`derived_from` that document) and its `known_at: null` with
`unknown_reason` — so it is omitted from every compiled context as `UNKNOWN_AVAILABILITY` and
is never evidence at a cutoff. Its **publication instant is unknown** too: a schedule interval
(16:00) is not a publication time, so the summary body records `published_at: null` with an
`unknown_reason`, and the record's `published_at` is the profile document's own date as a
stand-in labelled `published_at_approximate: true` (the owner-ruled form for a source the copy
carries no publication instant for; review 1, 2026-10-14).

## How the run was produced

`build.py` calls the real code, in this order: the DATA-1 readers build the advisory and
register records; `InMemoryRepository` registers the case, the sources, the unreviewed register
candidate and the reviewed mapping revision, seeds the prior assumption from the run's capacity
(83.7 MW, not typed by hand), builds one `BeliefSnapshot` per cutoff pair and compiles both
cutoffs through `compile_task`; `render_bundle` renders the frozen `probe-bundle.v5` request; a
deterministic scripted backend answers it; and the frozen `compose` and `receipt` produce the
labels and the stability receipt. The run stops there: **no disposition is committed.**

**Composed labels are recorded as run, never written first.** No label appears anywhere in
`case.json` before the run; each `composed` block is the output of `compose` over the reading
recorded beside it, and `--check` recomputes every one and refuses any drift. The readings are
the scripted backend's own annotation, each answer cited to the passage evidence it rests on.

**No backend ran and no judgment artifact is stored.** The backend is a script
(`synthetic_fixture`, `live_calls: 0`); the frozen validator refuses a `synthetic_fixture`
artifact carrying a real case's provenance
([tests/test_review_case.py](../../../tests/test_review_case.py), `H0V2Case`), and no live
inference is authorized by this task, so the judgment is recorded here and in the case packet
instead of being saved into the case.

## Recorded outcome (from the fixture digest below)

| Pair | T0 | T1 |
|---|---|---|
| trip (new source V133937) | blocked `MISSING_INPUT`, omissions V133937/V135622/V141257/V155556 `LATER_AVAILABILITY` + dispatch `UNKNOWN_AVAILABILITY` | compiled, context V133937, composes **challenges** (`outage_or_later`) |
| return (new source V155556) | compiled, context V133937/V135622/V141257, composes **challenges** (`outage_or_later`) | compiled, context + V155556, composes **supports** (`availability_confirmed`) |

All three judged compiles are stable (`unstable: false`, `forms: 4`). Reviews: **none
committed** (`review_state.committed: 0`; the only `ReviewDecision` is the seed). The replayed
case holds 23 records: 14 inputs in the fixture plus 2 snapshots, 4 compiled tasks, 1
assumption, 1 seed decision and 1 dependency impact.

Fixture digest (`compute_content_digest` of the parsed `case.json`):
`26ba43bfa09b93c14d7981a2ccaa4715a7e3efee48bcdf3bb4660a6e10dbe72e`. The digest covers
`case.json` only; `build.py`, this README and the case packet are not part of it, and
regenerating the file must reproduce this digest byte for byte.
