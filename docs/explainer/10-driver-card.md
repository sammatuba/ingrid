# Showcase: the driver card and the alert

<!-- paper: 3.4 3.5 -->

A trader sees a price spike and asks what was going on. The driver card answers with the conditions
present at that time and place, each with the time it became knowable. It never names a cause. This
chapter runs the card on the paper's two worked cases.

## What the card lists

For a region and a time, the card lists facts in six families: demand, supply, price, outages, fuel
and rules. Each fact shows its value, unit, source and known-at time, in one of the three modes of
chapter 13. A warehouse query fills the card. No model takes part.

Operator messages name plants in free text. A message links to a plant only through an accepted
alias. A person can accept an alias, or a fixed rule batch can accept it. The rules admit a plant's
own code, a word or word pair of its registered name, or initials of three or more letters.

The rules refuse a word that is only part of the company name. They refuse a name that is not on
the registration list, or that points to another plant in the region. They also refuse a match in a message that states more than 1.1 times the
plant's registered capacity. Of 1,608 aliases, 1,332 passed, and they cover 40,129 mentions. The
other 276 stay uncertain. The card lists an uncertain match as unconfirmed and never counts it.

## The ranking, step by step

<!-- widget: rank-walk -->

## The two worked cases

Case 1 is the PEDC unit 2 trip. Case 2 is the highest-priced Visayas interval since March 2026
whose schedule rows arrived after the interval. Switch the case and the mode, and watch the answer
change with what was knowable.

<!-- widget: driver-card -->

Case 2 shows what the time contract buys. In hindsight the 150 MW outage leads. At 09:10 its
schedule rows did not exist yet, so the assumed card ranks outages first on a smaller derating
signal. A desk that reads only the hindsight card would overstate what anyone could know.

Case 1 in strict mode says "no data" in every family. Almost nothing about that interval carried a
stamp of first availability. That result measures the data, not the market.

## The alert record

When the price in a region crosses a threshold that a signed-in user set, the desk writes one alert
with five fields. Case 1 gives each field.

1. The price and the user's threshold.
2. The severity line: high, price band very high, reserves healthy, no alert, top score 0.78.
3. The likely drivers, ranked under the fixed heading.
4. The trail: the trip message, its plant and region, the import over the congested link, demand, price.
5. What to check next: the unit's return time, the link's congestion, and demand against its median.

A user with a portfolio also sees the interval's impact on the uncovered volume, with the portfolio
version. Without one, the alert says "Not available: no portfolio entered". The desk ran and
recorded the alert for case 1. It has sent no live alert to a user.

<!-- quiz -->
Q: In case 2, why does the assumed card rank outages first on a derating signal and not on the 150 MW outage?
- The query skipped the outage by mistake
- [x] At 09:10 the schedule rows that record the outage did not exist yet
- Fuel always ranks last
Why: The desk first saw those rows at 09:40 and 10:00. The assumed mode admits a fact only after its known-at time, so the 150 MW outage appears only in hindsight.
<!-- /quiz -->

## Sources for this chapter

- The card, the alias rules, the ranking and the two cases: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 3.4 and table 4.
- The alert record: the same paper, section 3.5.
- Why the card stops short of a cause: the same paper, section 2.3.
