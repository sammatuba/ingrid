# VAL-1: how long the operator's outage schedule lags the advisory

State: in_progress, first pass 2026-10-16 by the orchestrator seat. Owner approved the billed read
(decision 1 of the [thesis-challenge record](../thesis-challenge-2026-10-16/strategy.md)). Direction check
VAL-1: if the operator's schedule catches up within an hour on complete coverage, outages leave the
assumption families.

## Step 1: when does the schedule first carry an outage?

[`scripts/validation/outage_lag.sql`](../../../scripts/validation/outage_lag.sql) over `ext_rtd_outage_schedules`,
`byear = 2026` (billing months 2026-01 to 2026-10, snapshots from 2025-12-26): 475 distinct outage rows,
174 resources, all `STATUS = OUT`. Extract under `.local/validation/outage_rows_2026.csv` (aggregates).

| Measure | Value |
|---|---|
| Rows first seen at or before their start (planned, or registered on time) | 328 |
| Rows first seen more than 5 minutes after their start | **147** |
| Late rows: lag from outage start to first snapshot | median 2,884 min (48 h); p90 36,479 min (25 days); mean 19,372 min |
| Late rows within 1 h / within 6 h / over 24 h | 22 / 44 / 84 |
| Rows by first-seen month | 2025-12: 14; 01: 58; 02: 61; 03: 90; 04: 30; 05: 25; 06: 46; 07: 78; 08: 36; 09: 32; 10: 5 |

PEDC rows: four for `08PEDC_U03` (Dec 2025 to Jan 2026, three in June 2026); none for `08PEDC_U02`
around 2026-09-21. The foundation review's sparsity warning holds: a forced trip resolved in 93 minutes
never reaches the schedule at all. "Never existed" is a third outcome, counted separately above by its
absence (the trip of 2026-09-21 has no row).

## Step 2: advisory first, or schedule first? (first pass, heuristic matching)

For the 147 late rows, the nearest trip, shutdown or outage advisory within six hours of the outage
start whose text carries the plant token of the resource code (first five letters of the plant part)
and, where present, the unit number. Advisories from the typed export `.local/e2v/advisories_all.csv`
(5,754 candidates since 2025-12). Matching is a token heuristic; the registered task replaces it with
the DATA-1 reader's typed events.

| Measure | Value |
|---|---|
| Late rows matched to an advisory within 6 h | **39 of 147** (108 unmatched: no advisory within 6 h, or the token did not match) |
| Advisory posted after the outage start | median 7 min; p90 231 min |
| Schedule first seen after the advisory | **median 1,242 min (20.7 h); p90 17,449 min (12 days)**; earliest −129 min |
| Schedule before the advisory / within 1 h after / over 24 h after | 5 / 6 / 19 |
| Largest | `11STEAG_U01` 2026-07-01: advisory +2 min, schedule +1,344 h; `11STEAG_U02` 2026-08-07: advisory +18 min, schedule +1,324 h |

Detail per row: `.local/validation/late_rows_matched.json`.

## Step 3: typed matching (second pass, 2026-10-16 evening)

`scripts/validation/outage_lag_typed.py` replaces the token heuristic: every 2026 advisory is classified
with the DATA-1 reader's category rules, transmission messages (a kV line) are dropped, the plant is
resolved through an alias table built from the resource code, and the unit by its number. Window six
hours. Output `.local/validation/typed_matching.json` (never in Git).

| Measure | Value |
|---|---|
| Schedule rows 2026 | 475; late (first seen after start) 148 |
| Late rows matched to an outage advisory, typed | **27 of 148** (the heuristic's 39 included unit mismatches) |
| Schedule first seen after the advisory | **median 508 min (8.5 h); p90 29,678 min (20.6 days)**; 12 of 27 over 24 h; none before the advisory |
| Generator outage advisories 2026 (trip, shutdown, unplanned, planned) | 1,275 |
| ... with no schedule row for that plant within 6 h | **1,232 (96.6 %)** |
| Unmatched late rows | 121: all `STATUS = OUT`; 43 belong to plants with no outage advisory at all in 2026 (hydro and small diesel: Magat, Ambuklao, San Roque, Binga, Angat, BDPP, PDPP3); for the other 78 the nearest same-plant outage advisory is a median 339 h away and 76 of 78 are marked planned |
| Return to service | 43 rows with an end time match a return advisory; the schedule's last snapshot sits a median 2 min before that advisory (p90 85 min after) |

Reading. The two feeds describe different things. The operator's outage schedule is a plan: entries are
created for planned work, often weeks ahead, and the advisory for a planned shutdown arrives when the
unit actually goes down, a median two weeks from the scheduled start. Trips almost never enter the
schedule: 97 in 100 generator outage advisories have no schedule row near them. Where both exist for a
trip, the schedule follows the advisory by a median 8.5 hours and in 12 of 27 cases by more than a day.
On return, the schedule tracks the advisory closely.

For the premise this is sharper than the first pass. An availability belief kept from the operator's
schedule is current for planned work and blind to trips; an availability belief kept from advisories is
current for trips and must be reconciled with the plan for planned work. Neither feed alone is the
belief; the register must hold both, with the advisory as the evidence of record for an event and the
schedule as the evidence of record for a plan. The direction check does not fire: outages stay an
assumption family, and the family needs two sources.

Caveats. The reader's category rules classify "shutdown (Planned Outage)" as forced and "de-energized"
as a return; the plant alias table is hand-built for the 2026 schedule plants and may miss a spelling;
the six-hour window is the same as the first pass. The script reproduces every number above from the two
local extracts.

## Reading, so far

The advisory is the evidence and arrives within minutes. The operator's schedule, the nearest thing to
an assumed availability that the market publishes, follows about a day later for the outages it records
at all, and never records the short ones. On this first pass the direction check does not fire: outages
stay an assumption family. Open before the task closes: typed matching for the 108 unmatched rows, the
share of 2026 trip advisories with no schedule row ever, and the same measure for return-to-service.

2026-10-18 (POLISH-2): VAL-1 is in progress in tasks.json; the figures above are quoted on the architecture pages and START-HERE with that label; no review record yet.

2026-10-18 (POLISH-2 rework round 1, review finding 3): correction to the line above: the figures are quoted on the architecture pages with that label (START-HERE quotes none of them).
