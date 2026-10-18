# Governed generative views

<!-- paper: 10 5.2 -->

The users ask to explore. They want to trace an event to the portfolio, ask why an alert fired, and
put a question in their own words. A fixed dashboard answers only the questions its designer
foresaw. A generative interface lets a model compose the view that fits the question. The paper
specifies a governed form of it. Nothing in this chapter has run, and its grade is "specified".

## Two hypotheses, pulling two ways

The paper names two motivations, and both are hypotheses to test. A composed view may let a person
explore faster than a fixed page. A polished view may also invite more reliance than its content
deserves, as research on automation bias predicts. The design tries to keep the first and guard
against the second.

## From the question to the receipt

<!-- widget: fig-views -->

## Six rules

1. The model arranges, and the records fill. A query fills every figure, and the plan holds none.
2. The model plans over a list of what exists: component ids, record ids, labels and states, never values.
3. Every view is an AI judgment with a receipt, saved in the person's own copy of the case.
4. Mandatory parts counter omission. A plan without them fails the check.
5. Connecting text quotes and does not compute. It holds no numeral except a record field by its id.
6. "Insufficient" is an answer. It names the missing record.

Withholding the values does not stop a model from writing an unsupported number. The validator
does: it refuses any plan whose text holds a numeral that quotes no record field, and it records
the refusal.

## Try the validator

The sample question asks why the price is what it is at 13:40 on the trip day. That is question
kind Q1 of chapter 20, with five mandatory parts.

<!-- widget: view-validator -->

## Wordings here, forms there

The view rules ask each question in four wordings and record whether the plan changes. Here the
wordings are real rephrasings. The judgment's four presentation forms in chapter 16 never rephrase.
They change order, labels, negation and passage order only.

## What would narrow the design

The paper plans a test against a fixed dashboard on the same case, with two users per arm. The
design narrows if the generated arm misses more issues or leaves out a mandatory part in any
wording. It also narrows if the plan changes in more than one of four wordings on more than a
quarter of the questions. The narrow form: the model proposes a layout, and the person picks from
the catalogue.

<!-- quiz -->
Q: A plan carries every mandatory part, and its text says "Supply leads at 0.78". What does the validator do?
- Accepts it, because every mandatory part is present
- [x] Refuses it, because 0.78 quotes no record field by its id, and records the refusal
- Rounds the number and accepts it
Why: Connecting text may hold a number only as a record field quoted by its id. Present parts do not excuse an unsupported figure.
<!-- /quiz -->

## Sources for this chapter

- The design, the six rules, the catalogue and Figure 6: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 10.
- The mandatory parts per question kind: the same paper, section 5.2 and table 8.
- The test against a fixed dashboard: the same paper, section 12 and table 13.
- The decision to adopt this direction: the [product-shape record](../work/product-shape-2026-10-17/strategy.md).
