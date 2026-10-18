# Review record: PEDC Unit 2 trip and return, 2026-09-21

**Status: open — the case records no disposition.** The evidence, the competing
interpretations and the model-assisted reading are set out below; the decision at each cutoff
is made by the demo's judge or the analyst on their own copy of the case (review 1,
2026-10-14: the fixture commits no pre-written desk decision, and none is presented as one).
The model-assisted reading beside them is the deterministic scripted backend's, labelled as
such and **not** stored as a judgment artifact — the frozen validator refuses a
`synthetic_fixture` artifact on a real case, and no live inference is authorized by this task.

## Evidence the review stands on

The four advisories registered in [evidence-manifest.json](evidence-manifest.json) and the
reviewed mapping in [mappings.json](mappings.json). The dispatch corroboration is attached and
was never available as evidence at any cutoff (`RUN_TIME absent from the copy`), so no review
claim rests on it.

## Supported links

- **Trip.** V133937, posted 13:39:37 (+08:00): "PEDC U2 Tripped at 1334H (Unplanned Outage)".
  The reviewed mapping resolves "PEDC U2" to `08PEDC_U02`; the event lies inside the
  assumption's day.
- **Grid consequence.** V135622, posted 13:56:22: "Visayas Grid Implement MLD at 1338H due to
  generation deficiency cause by tripping of PEDC U2" — the same event, plus the operator's
  load-drop action on the grid.
- **Condition stated for the evening.** V141257, posted 14:12:57: yellow alert for the
  interval hours 1700H–2000H. It names the grid, not the unit's state.
- **Return.** V155556, posted 15:55:56: "PEDC Unit 2 re-online at 1507H (Unplanned Outage)" —
  the latest statement about the unit at that cutoff.

## Unsupported and unknown

- **The return notice states no capacity.** It reports that the unit re-onlined at 1507H; it
  says nothing about the outage hours' capacity and nothing about the day-level value. It
  therefore does not establish the seeded 83.7 MW for 2026-09-21, and it does not resolve the
  whole-day assumption the seed states: the recorded trip contradicts uninterrupted day-level
  availability for that day. Read together, the day's evidence shows a unit that was out from
  1334H to 1507H, with no capacity stated for that window. Any day-level position an analyst
  takes on it is the analyst's reading, not something this record settles.
- No numerical consequence is asserted: the dispatch readings cannot be ordered without
  `RUN_TIME`, and no run exists — consequences remain **uncomputed**
  ([outlook-revision.md](outlook-revision.md)).
- No causal or commercial claim is read into the yellow alert; the alert names interval hours,
  not a unit condition.

## Lineage caution

V135622 restates the trip's cause while adding the grid action, and V155556 supersedes the
outage state it names in its parenthetical. The desk reads them as the operator's successive
statements about one event, not as independent corroboration.

## Model-assisted readings (as run)

Produced by the fixture backend and the frozen `probe-bundle.v5` composition
([tests/fixtures/pedc-u2-2026-09-21/case.json](../../../tests/fixtures/pedc-u2-2026-09-21/case.json),
`--check` recomputes every label from the recorded readings):

| Compile | Context | Composed label | Fired rule | Stable |
|---|---|---|---|---|
| trip / T0 (13:39:36) | none — blocked `MISSING_INPUT` | — (no passage to judge) | — | — |
| trip / T1 (13:39:37) | V133937 | **challenges** | `outage_or_later` (Q2=forced_outage, Q3=same on an availability kind) | yes, 4 forms |
| return / T0 (15:55:55) | V133937, V135622, V141257 | **challenges** | `outage_or_later` | yes, 4 forms |
| return / T1 (15:55:56) | + V155556 | **supports** | `availability_confirmed` (Q2=return_to_service, Q3=same, Q4 below tau_cond) | yes, 4 forms |

The scripted reading of the return set takes the re-online notice as the latest statement
about the unit; that reading is the script's, not a reviewed conclusion, and it is where a
live model differed — both live compiles composed `challenges`, recorded in
[evaluation.md](evaluation.md#live-probe-run-on-this-case-recorded-elsewhere).

## Competing interpretations (for the analyst or judge to decide)

1. **Revise the day-level value.** The trip leaves the unit unavailable from 1334H; on this
   reading the accepted 83.7 MW for the day should be restated. It faces the same limit at
   both cutoffs: the evidence states no capacity for the outage hours, so no new day-level
   value can be stated from the advisories without inventing one.
2. **Open the question.** The trip challenges the position; no day-level value can be defended
   while the unit's state is unknown and the outage hours' capacity is unstated.
3. **The registered value stands (no change).** The return notice shows the unit back in
   service, and the accepted position describes the unit again. Read strictly, it supports
   availability at the return instant, not the whole day: the intraday excursion is history
   either way, but the day-level 83.7 MW stays an assumption the notice does not establish.

No interpretation was accepted here: **the case records no outcome**. No capacity, price or
commercial claim is made anywhere in this pack.

## Attribution

Every record here was written by the EVAL-5 case assembly (`eval-5-case-assembly`) on
2026-10-14 — not by an analyst, and the reviewed mapping and the seed say so in their own
payloads. The reviewed mapping's `reconstruction` block and the seed's rationale state that
their 2026-09-21 positions are the reconstruction the compile replay needs; the sources keep
their real clocks. This pack is not evidence that any analyst session occurred.
