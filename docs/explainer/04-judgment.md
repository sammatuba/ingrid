# The judgment and the decision

This chapter opens the box. It shows the questions the AI model gets, how its answers become one
label, and what the analyst does next.

## Eight fixed questions

The desk does not ask the model "what do you think?". It asks eight short questions, each with a
fixed list of allowed answers.

1. Which unit is this about?
2. What kind of event is it?
3. When did it happen, compared with the assumption's day?
4. Is the statement conditional or planned?
5. Does it only repeat an earlier source?
6. Does it report a fact, not a plan?
7. Is the evidence enough to decide?
8. Taken alone, does it support or challenge the assumption?

Gemini gave these answers on 14 October 2026, the same at both cutoffs, and we saved them. Tap a
question below to read it in plain words.

<!-- widget: question-set -->

## Four presentation forms, one stability record

Language models can change their answer when the question changes shape. To catch that, the desk
asks each question in four presentation forms inside one request. One form changes the order of
the options. For a yes-or-no question, that form asks the question the other way round instead.
Another form replaces the option names with numbers, and the last reverses the evidence passages.

The forms never rephrase a question. Some forms come out the same: with one passage, the reversed
order changes nothing. If the forms agree, the stability record says "stable". When more than a
quarter of a question's forms disagree with the majority, the judgment counts as unstable. Its
label then becomes "not enough evidence". On the PEDC trip, every form agreed on every question.

## Code builds the label

The model never writes the label. A short table of rules in the code does. The rules encode the
project's own meaning. A forced outage challenges an availability assumption. A test run is not
commercial operation. A later date challenges an earlier assumption.

Try it below.

<!-- widget: label-rule -->

The judgment records which rule fired. An analyst can read the rule and disagree with it. That is
a feature. Anyone can inspect the rules, and the team can change them in a new version of the table.

## The analyst decides

Now the human part. The analyst reads the notice, the assumption, the eight answers and the label.
Then the analyst chooses one of three decisions and writes a reason.

- Keep the assumption. The day total may still hold, because the unit returned at 15:07.
- Change the assumption, to a new value or a new time span.
- Open the assumption for review, when the evidence is not enough.

The desk refuses a decision without a reason. It saves the decision in the history of the
analyst's own copy of the case. Try it. Nothing you type here leaves this page.

<!-- widget: practice-decision -->

## A recorded disagreement, kept on purpose

At the return cutoff, a rule-based reading took the four notices by the latest one and composed
"supports": the unit is back. Gemini read the same set as a forced outage and composed
"challenges". The case pack records no decision at that cutoff. The demo leaves it to you.

We did not hide this. The live run record and the working paper both say it. Whether the event
question should look at the latest passage only is an open question for a later version. The
desk is for exactly this moment: the model flags, and the analyst decides against it, with a
reason.

<!-- quiz -->
Q: Two of the four forms of a question give a different answer from the other two. What happens?
- The desk takes the majority answer
- [x] The judgment counts as unstable and its label becomes "not enough evidence"
- The desk asks the model again
Why: Two differing forms out of four is a flip rate of 0.5, above the 0.25 threshold. The stability record marks the judgment unstable and the rules send it to "not enough evidence". One differing form would be exactly 0.25 and would stay stable.
<!-- /quiz -->

## Sources for this chapter

- The eight questions, the four presentation forms and the rule table: the
  [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 9.3 and appendix C.
- Gemini's recorded answers, the two calls and the disagreement: the
  [live run record](../work/grid-desk/live-run-2026-10-14.md).
- The decision form and the history on the event page: the [event page record](../work/grid-desk/event.md).
