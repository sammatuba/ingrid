# Showcase: the recorded judgment

<!-- paper: 3.6 7.5 9.3 C -->

On 14 October 2026 a hosted Gemini model read the PEDC trip twice, once after the trip notice and
once after the return notice. That is one experiment with two inference runs. This chapter replays
it step by step, with the paper's own values.

## The four notices

| Notice | Event time | Header clock | Known-at | Text |
|---|---|---|---|---|
| V133937 | 13:34 | 13:40 | 13:39:37 | "PEDC U2 Tripped at 1334H (Unplanned Outage)" |
| V135622 | 13:38 | 13:57 | 13:56:22 | manual load dropping, "due to generation deficiency cause by tripping of PEDC U2" |
| V141257 | not stated | 14:13 | 14:12:57 | "Visayas Grid is on YELLOW Alert for the interval hours 1700H-2000H." |
| V155556 | 15:07 | 15:56 | 15:55:56 | "PEDC Unit 2 re-online at 1507H (Unplanned Outage)" |

The two cutoffs are the known-at times of the first and the fourth notice. The trip run reads one
passage. The return run reads all four.

## The run, step by step

<!-- widget: judgment-walk -->

## Count the presentation forms

Each question comes in four presentation forms inside one request. Form 1 changes the option order
of a choice question and negates a yes/no question. Form 2 numbers the options of a choice question, and form 3 reverses
the passages. No form rephrases a question. Some forms coincide, so the count of distinct forms depends on the run.

<!-- widget: forms-count -->

The answer to a question is its modal top option across the forms. The flip rate is the share of
forms whose top answer differs from the mode. The polarity gap compares the yes probabilities of
the base and the negated form. A flip rate above 0.25 or a gap above 0.3 makes the whole set
"not enough evidence" before any rule reads it.

## The disagreement, and why the record keeps it

At the return cutoff, both readings use the same fourteen rules. The model reads the set of four
passages as a forced outage, so rule 9 gives challenges. The rules reading takes the latest
statement, the return at 15:07, so rule 7 gives supports.

The two readings differ on one point: which passage governs the event question for a set. The
latest one, or the set as a whole? Nobody has decided yet. Without the cutoff, the passages and the
forms, nobody could even state the disagreement. The paper uses this as its first reason to build
the records before any user study.

## The worker, never the record

The model proposes which belief a signal touches, the change and the reason, with citations. It
never decides. Its answer reaches the belief set only through a person's recorded decision. Code
enforces every state change, and a model's text cannot grant a role or approve a change.

<!-- quiz -->
Q: The trip run read one passage. How many distinct presentations did its yes/no questions have?
- Four
- Three
- [x] Two
Why: Form 2 equals form 0 for a yes/no question, and form 3 equals form 0 with one passage. Only the base and the negated form differ.
<!-- /quiz -->

## Sources for this chapter

- The run, the answers and the disagreement: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 3.6 and 7.5.
- The forms, the modal answer and the thresholds: the same paper, section 9.3.
- The notices, the question texts, the rules and the request fingerprints: the same paper, appendix C.
- The run as recorded: the [live run record](../work/grid-desk/live-run-2026-10-14.md).
