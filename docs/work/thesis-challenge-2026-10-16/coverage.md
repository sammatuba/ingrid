# Coverage of the final settlement price series

Measured 2026-10-16 with partition-bounded BigQuery reads (one per year, each under 6 GB; the
load-weighted table under 2 GB), repo gcloud config. Aggregates only; no price values leave the
bucket. Companion to [price-basis.md](price-basis.md). A billing month `YYYY-MM` runs from the 26th of
the month before to the 25th (interval ends 00:05 on the 26th to 00:00 on the 26th of `MM`).

## `PMR_Settlement_Prices` (nodal final prices; 59 billing months)

| Range | 2021-07 to 2026-08 |
|---|---|
| Missing billing months | **2025-09, 2025-10, 2025-12** |
| Short month | 2025-11: 8,844 interval ends instead of 8,928 (84 missing, about 7 hours) |
| Nodes | 887 (2021-07) rising to 1,214 (2026-08); 647 load (NL), 563 generators (G), 4 pumped storage (PS) in 2026-08, typed through the real-time table's `resource_type` |
| Null prices | 7 rows in 2022-04; none elsewhere |
| Latest final month | 2026-08; 2026-09 (26 Aug to 25 Sep) not yet final; real-time copy runs to 2026-09-29 |

Administered pricing (`pricing_flag = AP`) share of rows, months above 5 per cent:

| Billing month | AP share |
|---|---|
| **2026-04** (26 Mar to 25 Apr 2026) | **100.0 %, every row** |
| 2026-05 | 19.2 % |
| 2022-01 | 18.4 % |
| 2024-06 | 9.0 % |
| 2021-12 | 7.8 % |
| 2024-05 | 4.3 % |

All of billing month 2026-04 settled at administered prices. Any price outlook, baseline or skill
score must treat that month as a rule intervention, not a market outcome (UC-02 hypothesis M4). Flag
meanings are still unconfirmed from IEMOP documentation (register A04).

## `PMR_LWAP_Final` (regional load-weighted average; 58 billing months)

Regions `CLUZ`, `CVIS`, `CMIN`, `SYSTEM`; one row per five-minute interval; every present month
complete. Missing: **2025-09, 2025-10, 2025-11, 2025-12**. `PMR_GWAP_Final` has the same shape
(generation-weighted); not scanned.

## Consequences for the price outlook

1. The gap of 2025-09 to 2025-12 (nodal) and 2025-09 to 2025-12 (regional) sits inside the most
   recent year; a rolling-origin evaluation must skip or mark those origins, never fill them.
2. The nodal series is the retailer target; the regional load-weighted series is the public reference
   and the first baseline target. Both have the same billing-month clock.
3. Real-time (`RTD_*`) prices exist for 2026-09 where final prices do not; the two must never be mixed
   in one scored series. Final is the target; real-time is a known-then observation.
4. Open: whether `lmp` in these files is the owner's `fedp` (final energy dispatch price). Assumed yes
   until the owner confirms; every figure above is a row count and unaffected.

## After the refresh of 2026-10-17

Measured from the bucket's object listing and the regional parquet, no BigQuery read
([record](../data-organization-2026-10-17/record.md)). `PMR_Settlement_Prices` and `PMR_LWAP_Final` now
both run 2021-07 to 2026-09, 63 billing months, none missing: the 2025-09 to 2025-12 gap is filled and
2026-09 is final. `PMR_LWAP_Final` has the full interval count in every month except 2022-07 (the two
irregular days, unchanged). Consequence 1 above no longer applies to the regional series; the nodal row
counts per month are not re-checked (no BigQuery access on the machine that ran this).
