# Methods and models

<!-- paper: 4 8 -->

The prototype uses several frameworks and models. Each one fills one role, produces one kind of
record, and answers to one theory. None of them is the record. The record is what a person can open
later. This chapter takes them one by one.

## Three roles

1. Forecasts produce positions. They must beat simple baselines under a proper loss before any claim.
2. Classifiers produce signals. Their probability is an event probability, kept apart from any judgment score.
3. The language model proposes belief changes and could arrange views. It never writes a belief, a decision or a figure.

<!-- widget: model-cards -->

## The foundation models, side by side

The paper tests two pretrained foundation models through the warehouse's own functions. Both face
the same bar as any other challenger.

| Model | Task | Result | Reading |
|---|---|---|---|
| TimesFM 2.5 | forecast five-minute reserve shortfall, zero shot, then flag an onset | AUC 0.69 to 0.78 | below the hour-of-day baseline of 0.85 to 0.89 |
| TabFM | predict onset from 2,000 labelled rows and 17 inputs | AUC 0.947 and 0.967 | tied with the local model, above hour-of-day |
| Local boosted trees | the same onset task, trained on earlier months | AUC 0.943 and 0.961 | the model the desk shows in four bands |

A foundation model is a challenger here, not an oracle. One of the two lost to a clock rule. The
other tied with a small local model and needs no training step. It ran once, with uncalibrated
probabilities.

## Does the classifier warn earlier than the operator?

No. The three-hour variant flagged the top 5% of its scores over June to September in the Visayas.
It flagged 43 of 71 alert days before the alert started, with a median lead of three hours. Only 7
of those came before the operator's own notice, which precedes an alert by a median 9.5 hours. It
also flagged 20 of 49 days without an announced alert.

## The decision model and the comparison

The language model answers the eight bounded questions of chapter 16, and fourteen fixed rules turn
the answers into a label. On 28 test tasks with labels the authors wrote, the question set and a
single direct question both scored 22 of 28. On the test split the single question scored 8 of 10,
and the question set 7 of 10.

The question set abstained four times, once correctly. On the 24 tasks that every condition
answered, it scored 21 of 24 against 19 of 24. Every answer stayed stable across the forms, so this
set cannot show what the stability record predicts.

<!-- quiz -->
Q: TabFM tied with the local boosted model on reserve-shortfall onset. What may the desk claim from that?
- TabFM is the better model
- [x] A pretrained model with no training step matched the local model on one run, with uncalibrated probabilities
- Foundation models beat simple baselines
Why: The intervals of the difference span zero, so the result is a tie. TimesFM, the other foundation model, fell below the hour-of-day baseline.
<!-- /quiz -->

## Sources for this chapter

- The models, their roles, the theories and the results: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 4 and table 6.
- The onset models, the lead-time test and the compiled-judgment comparison: the same paper, section 8.
- The foundation-model runs: the [TimesFM and TabFM record](../work/data-foundation/timesfm-tabfm.md).
- The comparison on test data: the [comparison report](../work/probe-bundle/evaluation.md).
