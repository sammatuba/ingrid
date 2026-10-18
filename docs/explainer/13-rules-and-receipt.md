# From answers to a label

<!-- paper: 9.3 C -->

Chapter 9 showed the eight questions and one rule. This chapter opens the whole rule table, the
thresholds, and the stability record that can veto all of it.

## Typed questions

Each question has a closed list of options. A choice question returns one option from a named
list. A yes/no question returns a probability for yes, and its top answer is yes at 0.5 or more.

The desk uses choices for identity, event, time and direction. It uses yes/no for conditional,
repeat, observation and sufficiency. Question 8, the direction, decides only inside rules 10, 11
and 13. The other rules never read it.

## The table, in order

The label is the first row of the table that fits. The code checks fourteen rows in a fixed order. Set the
answers and watch which row fires. The widget follows appendix C of the paper row by row.

<!-- widget: rule-table -->

Three rows apply only when the belief is an availability quantity, such as a unit's available
capacity. The table names three thresholds: sufficiency at 0.6,
conditional at 0.5 and repeat at 0.5. Each one tests the modal answer, read as 1.0 for yes and 0.0
for no, never a probability. The table is total: every combination of answers reaches a row, and
"not enough evidence" is the last one.

## The contestable row

Row 10 says that an observed earlier event supports the belief, unless the direction answer says
challenges. That is right for a supply belief and wrong for a return-date belief as stated. The
earlier working paper marked the row contestable on purpose and sent it to the comparison with
both belief kinds.

The comparison records what happened. Fourteen of the 28 compiles carry the row's pattern. The branch decided
four of them. For the two supply compiles it composed supports, and both were right.

For the two return-date compiles it was wrong both times. One composed supports where the expected label was
challenges. The other went to the direction-conflict row and composed mixed. The other ten compiles never
reached the row. The row stays, with those four outcomes recorded beside it.

## The stability record

Each question comes in four presentation forms inside one request. Form 0 is the base text. Form 1
changes the option order, or negates a yes/no question. Form 2 numbers the options of a choice
question. Form 3 reverses the passages.

The record keeps, per question, the top answer under each form and the flip rate. For yes/no
questions it also keeps the polarity gap. Change the answers of question 2 below and watch.

<!-- widget: receipt-sim -->

The whole judgment counts as unstable when any flip rate exceeds 0.25 or any polarity gap
exceeds 0.3. Unstable sends the label to "not enough evidence", whatever the answers said. The
record describes this one task. It is not a calibration claim about any model.

## What the model never sees

The compiled task holds the permitted passages and nothing else. No membership, access or
routing information enters it. Authority and routing stay in code. Text in a source that tries
to give instructions is data. The desk reads the model's probabilities only for their top option
and for the polarity gap, never as calibrated values.

<!-- quiz -->
Q: Two of the four forms of question 2 answered "testing" and two answered "forced outage". Every other answer is as on the PEDC trip. What is the label?
- challenges, because the forced-outage reading fires row 9
- [x] not enough evidence, because a flip rate of 0.5 is above 0.25 and the first row checks stability before anything else
- mixed
Why: Two differing forms out of four is a flip rate of 0.5, strictly above the 0.25 threshold. The first row of the table checks stability before anything else. One differing form would be exactly 0.25 and would stay stable.
<!-- /quiz -->

## Sources for this chapter

- The question types, the forms, the table and the thresholds: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 9.3 and appendix C.
- Why row 10 is contestable: the [earlier working paper](../product/working-paper-2026-10-11.md), section 5.2.
- The contestable row on the test data: the [comparison report](../work/probe-bundle/evaluation.md), section 4.
