# Problem statement and thesis, tightened

Written 2026-10-16 by the guardian seat from the owner's whiteboard of the same day and the records
already in this folder ([strategy](strategy.md), [price basis](price-basis.md),
[coverage](coverage.md)). This page supersedes section C of the strategy record and its scope lines
(G5) where they differ. It is the statement the M11 build is held to. The chain on the board (demand,
supply, price, portfolio, fuel and bids, rules) is the belief-family table and the graded watch list of
the [companion paper](../../product/paper-accountable-ai-decisions-2026-10-17.md) (revised 2026-10-17),
which also carries the checked sources behind the thesis.

## The board, transcribed

> Problem statement. Evidence-backed quick decision. Organize but cluttered information. Both lead
> to: connection of market information to portfolio impact leading to board decision. Material
> market changes affecting portfolio and outlook: D̃ – Ŝ – Price – P – F(Bid), Rules. Establishing
> causality of WESM factors to result. Regulatory rules, policy-driven incentive, goals influencing
> price results. Review of past decision for future action recommendation.

Read as one chain: demand and supply set the price; the price meets the portfolio and becomes an
impact; the impact, when material, reaches the board; the board's decision is kept and reviewed
against what settled. Bids and rules shape the price on the way.

## Problem statement

A retailer in the Philippine wholesale market must make quick, evidence-backed decisions about its
portfolio: what to contract, what to leave exposed, when to act. The market information it needs
exists but arrives cluttered: operator advisories, outage schedules, registrations, project lists,
rule changes, administered pricing notices, and the price series itself. Nothing connects a change
in that information to the portfolio in pesos, so the board sees either everything or nothing.

Two things fail as a result. First, material changes in demand, supply or rules reach the outlook
late or not at all. Where the operator's own outage schedule reflects a trip, it does so a median 8.5
hours after the advisory (27 matched rows of 148 late ones), 12 of 27 more than a day late, and most
trip advisories have no schedule row at all (corrected 2026-10-17 to the typed pass; the first pass gave
20.7 hours and half more than a day late) ([VAL-1](../validation/outage-lag.md)).
A unit listed by the Department of Energy in July as still testing had been dispatching since May
([PROJ-1](../projects/sources.md)). Second, when a decision turns out wrong, nobody can say which
factor moved the result, or what was known when the decision was taken. The review that should
shape the next recommendation has no record to read.

The premise, stated so it can fail: outlook errors that cost money come from assumptions nobody
owns a time-stamped record of, more than from the model.

## Thesis

One price outlook, kept honest, connected to the portfolio, and reviewed.

- **Outlook.** Every outlook version is stored with its date, inputs by digest, assumptions by id,
  model version and horizon, and scored later against final settlement prices. The baselines exist
  (PRICE-2, `docs/work/price-outlook/baselines.md` on `feat/price-outlook`, merged 2026-10-16); challengers must beat them or the outlook ships with
  the baseline and no skill claim.
- **Assumptions.** The outlook's inputs are owned records in a register: demand, supply, rules.
  Each has a source, a valid interval, a state and an owner. A change to an accepted assumption
  marks the outlooks that used it stale without erasing them.
- **Portfolio impact.** The outlook meets the portfolio: uncovered volume by node and hour against
  the outlook's price band and the contract price. That number, in pesos, is what "material" means.
  A change is material when it moves the impact past a stated threshold. Only material changes
  reach the board.
- **Decision.** The board's decision is a record: what was decided, on which outlook version, by
  whom, when. It is kept with the outlook.
- **Review.** When prices settle, the scoring receipt says how far the outlook missed and which
  accepted assumption had changed between the version used and the version that would have been
  right. That is the honest answer to "causality": attribution to an assumption change, by re-running
  the outlook with one assumption reverted. It is not a causal engine over the market.

The AI judgment is an accelerator inside this loop, for reading cluttered evidence and proposing
which assumption it touches. It is not the product. The reader of the decision history is the
board first; a regulator or counterparty second.

Read with the [meta framing record](../meta-framing-2026-10-17/strategy.md) (2026-10-17): the
problem is trusting and answering for decisions made with AI; the product is the record structure
that makes that possible; the model is the worker inside it, never the record of it. This page is
that problem's domain application, and the sentence above is consistent with it.

## The chain as assumption families

| Board symbol | Family | Series or record in hand | Not in hand |
|---|---|---|---|
| D̃ demand | demand | hourly load at the twelve exported load nodes (`mw_mean`), regional load-weighted prices | demand forecasts of the operator |
| Ŝ supply | availability and entry | advisories, outage schedule (VAL-1), registrations and first dispatch (PROJ-1), DOE project lists | generator bids |
| Price | the target | final nodal and regional prices 2021-07 to 2026-08, gaps and administered months marked | 2025-09 to 2025-12 |
| P portfolio | the company's position | synthetic portfolio: uncovered MWh by hour and contract price per node (owner: synthetic is acceptable) | the real portfolio, kept out of Git regardless |
| F(Bid) | bidding behaviour | none | bid data; out of scope until a family above shows a measured gain |
| Rules | rules and policy actions that move price | pricing flags per interval; billing month 2026-04 at 100% administered pricing; mixed months listed in [coverage](coverage.md) | ERC orders (fetch refused), live rule extraction |

Reconciliation 2026-10-17: the owner confirmed to the teammate that the fourth board symbol is `O`
for outage, not `P` for portfolio, and that `F(Bid)` reads fuel (bid)
([problem statement 2026-10-17](../../product/problem-statement-2026-10-17.md)). The table above
keeps the 2026-10-16 reading as filed; in use, outages belong to the Ŝ supply family (VAL-1), the
portfolio stays the input of the impact record (IMPACT-1), and fuel enters through the teammate's
daily fuel and exchange-rate pull.

## Use cases, collapsed into the chain

The four use cases of the strategy record are one chain with the price outlook as its hub.

| Use case | Role in the chain | First real datum |
|---|---|---|
| UC-02 price outlook | the hub: target, outlook, impact, decision, review | PRICE-2 scorecard, Luzon day-horizon MAE 1,796 PHP/MWh for the best baseline |
| UC-01 physical events | supply assumptions: availability | VAL-1, median schedule lag 8.5 h (typed pass; 20.7 h first pass) |
| UC-04 infrastructure milestones, generation and transmission | supply assumptions: entry dates | Masinloc Unit 4: listed as testing in July, dispatching since May |
| UC-03 rules | rules assumptions: actions that move price results | billing month 2026-04, every interval administered |

UC-03 is reframed from "which rules governed at a cutoff, for one role" to "rules and policy actions
that move price results". The cross-stakeholder framing of #81 and the one-role precursor are out of
scope until the chain shows a measured gain.

## Scope

In scope for M11: the target contract, the exported series, baselines and challengers, the outlook
archive and assumption register, portfolio impact with a materiality threshold, the decision record,
scoring receipts with attribution, and the four case sheets as repository documents. Models are
optional and must beat the baselines.

Deferred with a reason, not cut: VAL-2 (blind re-labelling of the probe-bundle fixtures) and LIVE-3
(live rule extraction on the 30 documents) serve the demoted judgment mechanism, not the chain. They
resume when a family above shows a measured gain and the judgment layer is asked to read evidence
for it.

Out of scope: a causal engine over the market, bid modelling, cross-stakeholder overlays, a graph
engine, new ontology types, further Ask the Grid parity, any second data pipeline. Cut stays cut.

This supersedes the strategy record's G5 lines that placed price forecasting and portfolio exposure
arithmetic out of scope. The owner's decision of 2026-10-16, "the price case, and WESM price outlook
defines the core strategy", and the whiteboard above move both into the core.

## Direction checks, restated in pesos

- **PRICE-3:** no challenger beats the baselines out of sample, the outlook ships with the baseline
  and no skill claim. Recorded 2026-10-17: 28 of 192 groups claim skill, 27 on the day horizon and one
  on the week horizon, none on the month horizon or the administered slice; pre-fold origins withheld
  (`docs/work/price-outlook/challengers.md`, pre-backfill exports).
- **IMPACT-1:** the materiality threshold is stated before any change is scored; every peso figure
  from the synthetic portfolio is labelled a method demonstration, never a business number. Recorded
  2026-10-17: the line is stated first in the module, the record and the print order; 12 of 12 nodes
  carry a material change at a one-million-peso line (`docs/work/price-outlook/impact.md`).
- **ARCH-3, restated:** the desk earns its place if an accepted assumption change moves the portfolio
  impact past the threshold at least once in the scored months. The earlier "one assumption in ten
  changes" count stays recorded but no longer decides.
- **Review:** on the scored months, the share of outlook misses that a reverted assumption would have
  reduced, stated as a number. If it is near zero, the premise fails and the product narrows to the
  archive and the scorecard.

## Added and moved in the plan

- Added **IMPACT-1** (stream PRICE, after PRICE-2): portfolio impact from the synthetic portfolio
  against the outlook's price band and contract price, per node and horizon, with a stated materiality
  threshold; the direction check above.
- VAL-2 and LIVE-3: deferred with the reason above, left registered.
- The reader of the decision history and the meaning of "causality" in section C of the strategy
  record are replaced by this page.
