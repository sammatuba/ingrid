# One time contract

<!-- paper: 2.1 9.2 C -->

A review of a decision can only use what people could know at the time. So every record in the
design carries the same time fields, with the same names in every section of the paper. This
chapter takes them one at a time, on the PEDC trip notice.

## Six fields, step by step

| Field | Meaning | On the trip notice V133937 |
|---|---|---|
| Valid time | When the condition holds in the world. | the outage, from 13:34 to the return at 15:07 |
| Made-at | When the source produced the item. | the advisory's posting time (the message also carries a header clock, 13:40) |
| Known-at, with its basis | The earliest time this workflow could read it. | 13:39:37, the time the market feed logged it |
| Recorded-at | When the prototype's tables stored it. | the time of the import run |
| Review time | When a person accepted a mapping, a belief or a decision. | none yet on the real case |
| Cutoff | The time a forecast, judgment or replay reads "as of". | 13:39:37 for the first run |

The header clock and the known-at time differ here. The header says 13:40, and the feed logged
the notice at 13:39:37. The desk uses the known-at time, because that is when a reader
could act.

## Evidence or assumption

Known-at carries its basis. An evidenced known-at is a time the source itself stamps. Examples are
the posting time of an operator message and the time of the team's own pull of a public series. Where no such
stamp exists, known-at is an assumed bound, and the record names the assumption.

1. A-RT: a real-time market value counts as available at the end of its five-minute interval.
2. A-RUN: a projected schedule row counts as available at the first daily snapshot that holds it.
3. A-FUEL: a fuel or exchange-rate value counts as available after a fixed lag per publisher.

A-RUN can only be late, never early: the schedule files carry no run time. A-FUEL uses two days for
the daily oil series, one day for exchange rates, and the fifteenth of the next month for coal and
LNG.

## Three modes

A replay at a cutoff reads under one of three modes. Strict reads only evidenced known-at times.
Assumed also reads facts whose known-at rests on a named assumption. Hindsight reads everything. The
driver card in chapter 15 shows how far the three answers can differ on one interval.

## Move the cutoff

The desk admits a passage only when its known-at time is at or before the cutoff. A passage with no
known availability time stays out, and the desk never fills one in. Move the slider across the
afternoon of the trip.

<!-- widget: cutoff-slider -->

## Where the fields come from

The design borrows two of its clocks from bitemporal databases. Valid time is their valid time.
Recorded-at is their transaction time. Known-at is the paper's own field. The sources rarely say
when they became available, so the field carries its basis.

<!-- quiz -->
Q: A projected schedule row first appears in the daily snapshot of 10:00. When does the desk treat it as known?
- At the outage start that the row describes
- [x] At 10:00, under assumption A-RUN, and the true time is earlier or the same
- At the time the analyst reads it
Why: The schedule files carry no run time, so the first snapshot that holds the row bounds its availability. The bound can be late, never early.
<!-- /quiz -->

## Sources for this chapter

- The six fields, the three assumptions and the three modes: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 2.1.
- The two clocks of each notice and the two cutoffs: the same paper, appendix C.
- The bitemporal roots: the same paper, section 9.2, which cites Jensen and Snodgrass (1999) and Snodgrass (2000).
- The notices and their times: the [case brief](../cases/pedc-u2-2026-09-21/brief.md).
