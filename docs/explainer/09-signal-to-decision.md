# From a signal to a scored decision

<!-- paper: 2.2 2.3 7.4 9.4 -->

The paper names a small set of objects and one chain that joins them. This chapter follows the
chain from left to right, then shows the loop that a settled month closes.

## The objects, in order

1. A signal is an item of evidence with a known-at time and a valid time.
2. A belief is a proposition with an owner, a source layer, a valid interval and a state.
3. The accepted snapshot at a cutoff holds every accepted belief that is valid then.
4. A position is a forecast version: a cutoff, inputs by fingerprint, beliefs by identifier, a method.
5. An impact prices a position against the portfolio's uncovered volume, hour by hour.
6. A decision records what, on which version and snapshot, by whom, when and why.
7. A scoring receipt compares a version with the settled price under a loss stated first.

A new version supersedes an old one. Nobody edits a version.

<!-- widget: fig-chain -->

The two labelled arrows of the figure, "touches" and "proposes a change to", are proposals. A
person reviews each one. The other arrows are identifiers that the target record stores.

## The materiality line

The impact of a version is the sum, over the hours, of the uncovered volume times the forecast
price minus the contract price. A change is material when it moves the impact by at least a line
that the desk states before it scores any change. The procedure refuses to classify a change
without a stated line.

The paper ran this on a synthetic portfolio of twelve nodes, with a line of 1,000,000 pesos per
change. 19,468 of 82,080 changes, 23.7%, crossed the line. By horizon: day 7,083 of 45,828, week
12,282 of 36,144, month 103 of 108. These are movements of the forecast between origins. They are
not changes to an accepted belief, and the right line is a business question.

## Two versions, waiting for a settled month

Two versions of a system price forecast for billing month November 2026 exist. The desk issued
them on 16 and 17 October 2026, with cutoffs of 25 August and 25 September. Both rest on the same
five price and rule beliefs, and none of the five changed between them. The scoring waits for the
market operator's final prices, expected in December 2026.

## Attribution: built and proposed

A miss is a scored version whose loss exceeds a threshold stated with the loss. Today a person
writes an attribution beside the scoring receipt. It names a belief, a signal or the method, with
a statement and an optional share. Nothing in the prototype computes an attribution.

The paper proposes a computed form. Re-run the forecast with one changed belief set to its later
value. The drop in loss is the part of the miss that the computed form gives to that belief. The miss is avoidable only if the later
value was knowable before the version's cutoff.

| Measure | What it needs | Status |
|---|---|---|
| Attribution coverage: the share of misses with a written attribution | the built record and one settled month | implemented, waiting for a month |
| Avoidable-miss share: avoidable misses over all misses in a month | the computed re-runs and a join to the knowable time | proposed, not built |

<!-- widget: fig-loop -->

The single loop changes a belief and issues a new version. The double loop compares the month's
review share with a threshold stated first, and it can change the method or the product. Neither
loop names a cause in the market.

<!-- quiz -->
Q: A belief changed after a forecast's cutoff, and the re-run with its later value has a lower loss. Is the miss avoidable?
- Yes, because the re-run has a lower loss
- [x] No. The belief explains the miss, but nobody could know its later value before the cutoff
- Only if a person wrote a share of 1
Why: Avoidable needs two things: a positive drop in loss, and a later value that was knowable before the cutoff. A person's share field proves neither.
<!-- /quiz -->

## Sources for this chapter

- The objects, the impact, the materiality line and attribution: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 2.2 and 2.3.
- The materiality run and the two versions: the same paper, section 7.4.
- The single and the double loop: the same paper, section 9.4, after Argyris and Schön (1978).
- The impact record behind the materiality run: the [impact record](../work/price-outlook/impact.md).
