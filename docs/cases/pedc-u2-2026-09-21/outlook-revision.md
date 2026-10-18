# Outlook revision: PEDC Unit 2, 2026-09-21

**No revision was committed.** The case's only accepted position is the seeded assumption — the
registered maximum 83.7 MW, read from the register run and accepted by the case assembly on
2026-10-14 at the reconstructed day-start position — and the case records no review decision
that changes it or confirms it. The accepted outlook head is empty
(`workspace.outlook_head: null` in the fixture); the decision is left to the demo's judge or
the analyst. No run comparison exists: **consequences remain uncomputed**.

## Before and after

| Field | Accepted position |
|---|---|
| Entity / field | `08PEDC_U02`, `pedc-availability.v1` / `available_capacity_mw` (MW) |
| Assumed position (seed, reconstructed 2026-09-21 00:10 +08:00) | 83.7 MW for 2026-09-21, evidenced by the register run’s source version |
| After the two cutoff pairs | **unchanged — no decision was recorded**; the assumption head is the seed, the outlook head is empty, and the pair’s judged readings stand beside it in [review.md](review.md#model-assisted-readings-as-run) |

The seed states the desk's assumption, not a measured fact: it is the registered maximum
carried into the day as the accepted available capacity. The evidence registered for the day
does not establish that value **for the whole day** — the unit was out of service from 1334H to
1507H on the operator's own notices, and the return notice states no capacity for the outage
hours. Whether the day-level assumption should stand, be revised or be opened is exactly the
decision this case leaves open.

Record references and digests are in
[tests/fixtures/pedc-u2-2026-09-21/case.json](../../../tests/fixtures/pedc-u2-2026-09-21/case.json)
(`workspace`).

## Recorded decisions

**None.** `review_state.committed` is `0` in the fixture: no `ReviewDecision` beyond the seed
and no `OutlookRevision` exists, so there is no committed rationale to quote here. The seed's
own rationale is reproduced from the record:

> "Initial acceptance recorded by the eval-5-case-assembly on 2026-10-14, placed at the
> reconstructed position 2026-09-21T00:10:00+08:00 (the compile replay requires the accepted
> position to precede the cutoffs). The value is read from the register run's capacity
> (83.7 MW, participant PEDC), never typed; no analyst session ran."

## Sources of the position

- The reviewed mapping `mapping:regcap:08PEDC_U02:PEDC:83.7:2026-02-05` revision 2, reviewed by
  the case assembly and evidenced by the run's source version ([mappings.json](mappings.json)).
- The four advisories of the day, whose composed readings at each cutoff are in
  [review.md](review.md#model-assisted-readings-as-run).

## Remaining uncertainty

- The unit's return capacity and the outage hours' capacity are unstated by the evidence; the
  dispatch readings cannot be ordered without `RUN_TIME`, and its publication instant is
  unknown.
- The seeded 83.7 MW is a day-level assumption the day's evidence does not confirm: the trip
  contradicts uninterrupted availability, and no registered source states a capacity for the
  outage window.
- The yellow alert's interval hours passed after the last advisory of the case; no later
  advisory of the day is registered here.
- No numerical, price or commercial consequence of the excursion is computed, and no
  disposition is recorded.
