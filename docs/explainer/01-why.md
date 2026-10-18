# Why a review desk exists

This chapter explains the problem that InGRID solves. It uses no technical words. If you
read only one chapter, read this one.

## The analyst's job

An energy analyst writes an outlook. An outlook is a forecast: how much power the grid will have,
how much people will use, and what it will cost. Companies, planners and traders act on it.

Every outlook rests on assumptions. An assumption is one fact that the forecast takes as given.
Three examples:

- Demand peaks near the usual evening value.
- PEDC Unit 2 in Visayas supplies 83.7 MW all day.
- Both undersea links run as scheduled.

Each assumption can become wrong at any moment. A plant trips. A cable goes down for repair. A
heat wave pushes demand up. The forecast still looks fine on paper, but one of its legs is gone.

<!-- widget: assumption-chain -->

## What goes wrong today

The analyst reads the operator's notices, the market data and the news. Then the analyst tries to
remember which forecast depends on which fact. That is hard for three reasons.

1. The notices arrive all day, and most of them touch nothing the analyst cares about.
2. The link from a notice to an assumption lives in the analyst's head, not in a system.
3. When the analyst does nothing, nobody can tell a careful "no change" from a missed change.

The third reason matters most. A forecast that nobody reviewed and a forecast that someone
reviewed and kept look the same. The desk makes them look different.

## What InGRID does

InGRID is a review desk. It does four things, in order.

1. It reads new evidence, such as an operator notice, and records when the evidence became known.
2. It finds the assumption that the evidence touches.
3. It asks an AI model a fixed set of questions about the evidence and the assumption. The model
   answers with citations. Code turns the answers into one label: supports, challenges, mixed,
   unrelated or not enough evidence.
4. It lets the analyst decide: keep the assumption, change it, or open it for review. The decision
   and its reason go into the history.

The AI never decides. It does the reading and the comparing. The analyst keeps the authority. A
kept assumption with a good reason counts as a success. That last sentence is the heart of the
project, and the site says it on the screen.

## What InGRID is not

- It is not a forecast model. It does not predict prices or demand. The price outlook it keeps is
  a position, not a prediction. It states an expectation for a month, from a seasonal baseline. The desk
  issues it once, never edits it, and scores it later against what settled.
- It is not a chatbot over PDF files. The questions never change, and the answers have fixed options.
- It does not run the grid or send anything to the operator.
- It does not claim that it prevents blackouts. We have no evidence for such a claim, so we do
  not make it.

<!-- quiz -->
Q: Who decides whether an assumption stays or changes?
- The AI model
- [x] The analyst
- The system operator
Why: The AI reads and compares. The analyst decides and gives a reason. A kept assumption with a reason is a success.
<!-- /quiz -->

## Sources for this chapter

- The method: the [working paper](../product/working-paper-2026-10-11.md), sections 1 to 4.
- The one-sentence pitch: the [story and script](../competition/ai-builder-cup-2026/story-and-script.md).
