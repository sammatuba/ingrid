# Phase 2, step 1: the price a retailer settles at

Read 2026-10-16 from the text layer of the Billing and Settlement Manual, Issue 16.0, effective
2025-08-31 (corpus register row 10, PEMC compendium of 2026-04-01; first availability unknown). Offline;
no model, no cloud. Companion to [strategy.md](strategy.md). Clause numbers are the manual's own; the
WESM Rules clauses it cites are not in hand as text and stay references.

## What the manual says

- A Trading Participant's energy trading amount is the sum over **each market trading node for which it is
  responsible**, per WESM Rules 3.13.7; "typically positive for a Generation Company and negative for a
  Customer" (manual 4.1.1 b.i, page 11). Settlement quantities follow WESM Rules 3.13.5 and 3.13.6.
- Settlement data issued with the preliminary and final statements includes the **final nodal energy
  dispatch prices**, the energy settlement quantity, line rental amounts and bilateral contract quantities
  (manual 4.1, page 13).
- A bilateral contract declaration names the market trading node "whose final nodal energy dispatch price
  will be used as reference during settlements" (manual 9.1.2 c, page 38); the buyer may name its withdrawal
  node (9.1.3); undeclared quantities are pro-rated to the buyer's nodes by metered quantity (9.3.2 b).
- For prudential projections, a member's price is the final energy dispatch price of the **geographically
  nearest market trading node** to its connection point (manual 7.4.1 f, page 27).

## What this means for our series

The query in [`04_interval_pricing.sql`](../../../scripts/data/sql/04_interval_pricing.sql) computes a capped
median of **generator-node** LMP per region. A retailer's exposure is the **final nodal energy dispatch
price at its own load nodes**, interval by interval, times its uncovered metered quantity there, with
bilateral quantities settled at the declared node's final price. The two are different quantities. The
regional generator median remains a fair descriptive index of the grid; it is not a retailer's settlement
price and must not be scored as one.

Disposition for #85 (UC-02 G1, price basis): **answered, no**. Downstream figures wait on the right series.

## Next checks, in order

1. Which bucket folders hold **final** nodal prices (the data handoff lists `PMR_*` as "prices and
   settlement" and `RTD_*` as real-time dispatch; the real-time LMP is not the final price). One schema
   read; the owner approved billed reads.
2. The retailer's own load nodes and metered quantities: a permissioned or clearly synthetic fixture, never
   in Git (#88's domain contract).
3. The settlement region rule (manual 9.2, page 39: Luzon and Visayas are one settlement region for
   bilateral purposes) when a contract's source node sits in another grid.
4. Then the price target contract for #85: series, node set, interval, units, revisions, first availability.

## Owner facts and the data check (2026-10-16, later the same day)

Owner: a billing month runs from the 26th to the 25th; the final settlement prices are the `fedp`
columns. The data handoff already records `bmonth` as a billing month (26th to 25th).

Checked against the bucket (one `gsutil ls`, three free schema reads, three partition-bounded queries
under a 3 GB cap, repo gcloud config):

| Item | Finding |
|---|---|
| Final price folders | `PMR_Settlement_Prices` (59 files, 4.17 GiB, 2021 to billing month 2026-08) and `PMR_DIPC_Final`; both external tables carry `interval_end, region_name, resource_name, pricing_flag, lmp, sched_mw, lmp_smp, lmp_loss, lmp_congestion`. Also `PMR_LWAP_Final` and `PMR_GWAP_Final` (regional load- and generation-weighted averages, `mkt_type`). |
| Column named `fedp` | none in any `grid_raw` external table (column catalog query and schema reads). In this copy the final nodal energy price column is `lmp`, with the three components beside it. **Unconfirmed** that `lmp` here is the owner's `fedp`; asked. |
| Billing month 2026-08 | `interval_end` from 2026-07-26 00:05 to 2026-08-26 00:00; 10,791,225 rows; 1,214 distinct nodes |
| Latest final month | 2026-08. Billing month 2026-09 (26 Aug to 25 Sep) has no final file yet; the real-time copy runs to 2026-09-29 |
| Load nodes present | yes: by site prefix, rows with negative `sched_mw` (withdrawal) sit beside positive ones; prefix 01 alone has 370 nodes. Identification by sign is a heuristic until the registration list maps load nodes |
| Flags in 2026-08 | OK 9,904,501 rows (avg lmp 11,990); SEC 369,712 (5,957); AP 286,812 over 323 nodes (26,283); PSM 230,200 (5,590). Flag meanings still unconfirmed from IEMOP documentation (A04) |

Consequence: the retailer price target is `PMR_Settlement_Prices.lmp` at the retailer's own load nodes
(or the declared contract nodes), per interval, under the final statement; `PMR_LWAP_Final` is the regional
load-weighted reference. The generator-median series stays a grid index. The target contract for #85 can
now be written once the `fedp` naming and the load-node mapping are confirmed.

## Verification of the price column (2026-10-16, owner: "verify")

Two checks on billing month 2026-08, partition-bounded, under 8 GB each:

1. **Reproduction of the published series.** The load-weighted average of `PMR_Settlement_Prices.lmp`
   over `NL` nodes (weights `ABS(sched_mw)`) against `PMR_LWAP_Final.lwap`, after mapping the settlement
   labels LUZON, VISAYAS, MINDANAO to CLUZ, CVIS, CMIN: 8,928 intervals matched per region; mean absolute
   difference 0.40 (Luzon), 0.02 (Mindanao), 1.01 (Visayas) PHP/MWh; maximum 15.32, 8.91, 110.21; within
   one peso on 7,614, 8,904 and 7,428 intervals. Monthly averages agree to one decimal (4,804.6 vs 4,804.3;
   19,558.6 vs 19,558.6; 18,593.4 vs 18,594.0).
2. **Relation to the real-time price.** Joined to `RTD_Prices_and_Schedules.lmp` by interval and node:
   OK rows equal in 8,203,302 of 9,904,501 cases; AP rows never equal (settlement mean 26,283 vs real-time
   311,783); settlement maxima 46,321 (OK), 37,085 (AP), 29,451 (PSM), 7,634 (SEC) against real-time
   maxima near 800,000.

**Conclusion: `lmp` in `PMR_Settlement_Prices` is the final settlement price (the owner's `fedp`).**
It is the price after the market's caps and substitutions; the real-time price is the uncapped dispatch
result. Region labels differ between the two families and must be mapped. The price target contract
(PRICE-0) can be written.

## Owner answers, later on 2026-10-16

- Permission is never an issue for this project; no further permission concern is to be raised or
  allowed to block work. The corpus permission record becomes a one-line note, not a gate.
- Synthetic load nodes and volumes are acceptable for the retailer case; labelled synthetic, never in Git.
- The walkthrough by someone new is deferred until the idea is reinforced; HOST-3 leaves the head of
  the chain.
