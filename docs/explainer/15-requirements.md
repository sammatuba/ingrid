# From user stories to desk questions

<!-- paper: 5.1 5.2 6 B -->

One of the operating company's market staff wrote twelve user stories for traders, portfolio managers and
risk staff. The stories rarely mention AI. Their shared demand is decisions that the users can trace
and defend. This chapter follows each story to the records and the desk question that serve it.

## Three verdicts

Each story gets one verdict. Adopt means the design serves it as stated. Reframe means the design
serves a narrower form. Defer means it stays outside the current design, with the reason. The
stories are candidate requirements, not the result of a user study.

<!-- widget: story-map -->

Two reframings matter most. Stories 2 and 10 ask for a "driving factor" and "root causes". The
design answers with two records. One ranks what was unusual at the time, as evidence and not proof.
The other attributes a miss to the organization's own beliefs. A claim about what moved the market
would need a causal model of the market, and that stays outside the design.

## Twelve desk questions

The desk's unit of work is the question a person asks. Each kind of question has parts that every
answer must show, so that no answer can leave out the uncomfortable part. Three examples:

| Kind | Question | Parts every answer must show |
|---|---|---|
| Q1 | Why is the price what it is at this time and place? | the cutoff and mode, one block per family or "no data", unconfirmed matches listed, withheld counts, the ranking under its fixed heading |
| Q9 | Which belief does this event touch, and what does the model say under the cutoff? | the advisory with its time, the belief, the judgment with its stability receipt, any unresolved disagreement, the decision form |
| Q12 | How did this forecast version do, and which of our beliefs moved it? | the versions and cutoffs, the loss, each attribution and its author, the coverage, and the avoidable-miss share marked "not computed" |

A question outside the records, such as a free question across market and portfolio, gets the
answer "insufficient", with the missing record named.

## The role flows

1. A trader's morning: Q8 what is happening now, then Q1 on anything unusual, then Q2 to Q4.
2. An alert: Q11 why it fired, then Q1, then Q10 the exposure.
3. A portfolio manager's event: Q9, then Q10, then a decision.
4. A risk manager's trace: Q7, the known-then view, on any answer, plus its receipt.
5. A risk analyst's month end: Q12.

## The watch list

The same staff member listed 44 factors in ten groups. On this desk a factor is never a cause. It
enters as a signal with the time it became known, or as a belief that a forecast rests on. One rule
governs the list: a factor that is not a record cannot appear in an answer. The answer says "no
record".

| Family | What is a record today | Grade |
|---|---|---|
| Supply | outage events, advisories, registered capacity, unit schedules | outages a record, available capacity and mix derivable |
| Demand | the regional requirement per interval | actual demand a record, weather and holidays not pulled |
| Fuel | the Japan LNG import average, Australian coal, crude oil | a record, with LNG as a proxy |
| Reserves | shortfall and labels from March 2026, reserve prices | shortage a record, reserve schedules in store and unread |
| Transmission | link flows and congestion flags | flows a record, the 2026 transfer limit absent |
| Rules and policy | administered, price-mitigation and secondary-cap flags per interval | flags a record with inferred meanings, no clause placed at a cutoff |
| Market structure | offers and bids, in store | excluded on purpose: bids would reopen a causal reading of the market |
| Weather | none | public source, not pulled |
| External | reference exchange rates, as background | rates a record, other events only as a dated note with no figure |

Where the list is thin, an answer says so. The ranking's 28-day reference treats a holiday like any
other day, because no holiday record exists.

<!-- quiz -->
Q: A trader asks how a typhoon moved the price. What does the desk answer?
- A paragraph on typhoons and prices
- [x] "No record" for weather, because no weather series exists on the desk
- The driver card's top family, named as the cause
Why: A factor that is not a record cannot appear in an answer. Weather is a public source that the team has not pulled, so the answer names the gap.
<!-- /quiz -->

## Sources for this chapter

- The twelve stories, the verdicts and the twelve desk questions: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 5 and tables 7 and 8.
- The watch list and its grades: the same paper, section 6, table 9 and appendix B.
- The stories as the company supplied them: the [user stories](../product/user-stories-2026-10-17.md).
- The factor list, cleaned: the [market factors](../product/market-factors-2026-10-17.md).
