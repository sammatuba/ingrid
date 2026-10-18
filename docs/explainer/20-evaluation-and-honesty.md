# Null results, the evaluation plan and the limits

<!-- paper: 8 12 13.2 14 -->

The paper reports what failed or tied as plainly as what worked. It also lists the experiments that
could refute it, each with a threshold stated in advance. This chapter shows both, then the limits
the paper names against itself.

## What tied or failed

| Result | What the paper reports |
|---|---|
| Question set against a single question | a tie at 22 of 28. On the test split the single question scored 8 of 10 and the set 7 of 10. |
| Abstention | the set abstained four times, once correctly. At matched coverage it scored 21 of 24 against 19 of 24. |
| Stability record | every answer stayed stable, so its predictive value cannot show on this set |
| Early warning | the three-hour classifier flagged only 7 of 71 alert days before the operator's notice |
| TimesFM, zero shot | below the hour-of-day baseline |
| Month-horizon price skill | no claim possible under the six rules |

The authors wrote the 28 test labels themselves, and a scripted replay of fixed answers produced
the results. The paper treats them as test-data results, not as evidence about any live model.

## The numbers that do not exist yet

The hypothesis depends on several numbers that nobody has measured. Nobody knows how often
out-of-date beliefs cause the costly misses, or whether analysts work faster or miss less. No real
case runs complete from evidence to belief to decision to consequence. No month has a score yet.
The first, November 2026, gets its score in December 2026.

## Experiments that could refute the design

Six of the paper's nine experiments, with the threshold that would narrow or refute the design:

| Experiment | The design narrows or fails if |
|---|---|
| Out-of-date inputs in five of the company's past forecast runs | zero in five: proposition 1 fails for this company |
| An analyst relabels the 25 test pairs and the two real compiles blind, and a second person settles disputes | fewer than 20 of 28 agreements: the tie no longer holds |
| One live extraction of rule changes from 30 market documents | under 90% of citations exact and correctly placed |
| A generated view against a fixed dashboard | more missed issues, a mandatory part left out in any wording, or an unstable plan |
| The first scored month, with written attributions | coverage with an upper bound below 0.2: attribution is not happening |
| Reliance against correctness, with and without the stability badge | no difference with the badge: the stability hypothesis fails |

Until the relabelling, the scored month and the reliance study run, every sentence about value or
trust in the paper is a hypothesis.

## Claims the paper refuses

Test yourself. Some claims follow from the records, and some go past them.

<!-- widget: claim-checker -->

## Limits the paper names

- The authors wrote the test labels. The relabelling experiment exists to replace them.
- Two model calls on one case cannot estimate accuracy.
- Every portfolio figure demonstrates a method on a synthetic portfolio.
- The timestamps carry no time zone, the pricing flags have inferred meanings, and three nodal months are missing.
- Nobody knows yet whether the price series is a retailer's true exposure.
- The same team built and evaluated the prototype. A different reviewer checked each change, but no evaluator was blind to the hypothesis.
- The authors chose case 1 because it showed in the data, and case 2 by a stated rule. Neither is a sample.

<!-- quiz -->
Q: The question set and the single question both scored 22 of 28. What does the paper conclude?
- The question set is better, because it abstains
- [x] A tie. The test split favours the single question, and the authors wrote the labels
- The single question is better in every case
Why: The paper lists an advantage of the question set as a number that does not exist yet. The two tie, and the test split scores 8 of 10 against 7 of 10.
<!-- /quiz -->

## Sources for this chapter

- The null results and the missing numbers: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 8 and table 12.
- The experiments and their thresholds: the same paper, section 12 and table 13.
- What the evidence does not support, and the limits: the same paper, sections 13.2 and 14.
- The comparison on test data: the [comparison report](../work/probe-bundle/evaluation.md).
- The real-case readings: the [case review](../cases/pedc-u2-2026-09-21/review.md).
