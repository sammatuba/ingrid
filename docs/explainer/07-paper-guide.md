# How to read the paper with this companion

<!-- paper: Abstract 1.2 1.3 2.4 7.1 -->

This part of the explainer follows the working paper section by section. Each chapter names the
sections it covers at the top. Then it walks the method step by step on the real cases, and it ends
with a self-check. Read a chapter here, then the section in the paper, or the other way round.

## The question and the hypothesis

The paper asks one question: who answers for a decision made with AI? A model can read operator
notices and price data at a scale no desk can match. When it does the reading, the scarce thing
becomes a record of what the organization believed, on which evidence, and who accepted it.

The paper works from one hypothesis. Two properties bound the value of AI in decision work:
traceability and trust. Traceability lives in records that the desk writes at the time, with their
times, and never changes later. Trust lives in how people rely on the system. Structure can earn it,
but only measurement can confirm it.

The paper demonstrates the record half on a prototype. It does not measure the trust half. It says
how a later study would measure it, and the last chapters of this part show that plan.

## Three levels of the problem

| Level | The problem | What the paper has |
|---|---|---|
| People | AI moves the job from finding information to judging it and answering for it. | a framing, with no measure of the effect on analysts yet |
| Organization | Without trust, people hold AI back. Without traceability, they use it blind. | a hypothesis, and the timing measurements of chapter 21 |
| Sector | In a regulated sector, a board and a regulator must see who decided what, and when. | the readers that the operating company names, not yet observed |

## One grade on every figure

Every figure in the paper carries one of five grades. The grade says how strong the evidence is.

1. Measured: scored against labels or outcomes.
2. Demonstrated: run on real data with a receipt, and not scored.
3. Implemented: code and tests, with test data only.
4. Specified: a design with no run.
5. Absent: no record exists.

<!-- widget: grade-sort -->

## Words in this part

The paper says belief for a proposition that a forecast rests on. The earlier chapters say
assumption, and the prototype's files use the same word. Both words name the same record.

A position is a forecast version. A signal is an item of evidence with its times. Every peso figure
for a portfolio comes from a synthetic portfolio. The price and error figures are real.

## Five propositions

The paper states five claims that a test could refute. Chapter 25 lists the experiment and the
threshold for each.

- Beliefs are the bottleneck.
- Time is a field of its own.
- Structure earns trust.
- Materiality uses the organization's own units.
- Review attributes a miss, and does not blame.

<!-- quiz -->
Q: The model gave the same answers in every presentation form on one real case. Which grade does that result carry?
- Measured
- [x] Demonstrated
- Specified
Why: The run used real data and kept a receipt, but no label scored it. Two runs on one case cannot estimate accuracy.
<!-- /quiz -->

## Sources for this chapter

- The question, the hypothesis, the three levels and the grades: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 1, 2.4 and 7.1.
- The same paper on the site: the [paper page](https://ingrid-desk.web.app/paper).
