# Four layers and seven record kinds

<!-- paper: 9.1 9.2 9.5 -->

The paper's framework has two views. Four layers of responsibility say who answers for what. Seven
record kinds say what the desk stores so that a person can answer later. This chapter takes the
layers first, then the records, then the limits that hold across both.

## Four layers of responsibility

Read the figure from the bottom. Evidence becomes attributed claims and reviewed beliefs. Beliefs
feed forecasts and decisions. Decisions become work with receipts. Outcomes feed three kinds of
learning back into beliefs, methods and processes.

<!-- widget: fig-layers -->

The four layers are a map of ideas, not four services. Each rests on one tradition: belief change
for knowledge, decision theory for judgment, coordination for work, and organizational learning for
the last layer. The ideas part at the start of the explainer takes one layer per chapter.

## Seven record kinds

Every record carries the same envelope fields. A solid arrow points from the record that stores a
reference to the record it names. An arrow marked "flow" is not a stored field.

<!-- widget: fig-records -->

Notice the AI judgment. It stores only the identifier of the compiled task it answered. The task
stores the passages and the belief, so the judgment reaches them only through the task. The
judgment proposes and arranges. It never writes into a belief, a decision or a figure.

## The layers in the prototype

The prototype splits the work into layers that each own some things and never grant others. Code
owns time, identity and transactions. Models answer inside a compiled task. The analyst owns
acceptance. Click a layer.

<!-- widget: layer-stack -->

## Four labels on every record

Four labels on every record are independent. The first says the kind of content. The second says
its review state. The third says whether it was available at the cutoff. The fourth says whether it is
live or replayed.

<!-- widget: record-axes -->

## Invariants

- Observations, attributed claims, accepted beliefs and simulation results are separate records.
- No person and no model reads a fact before its known-at time.
- An unknown identity, time or approval stays unknown, and an ambiguous mapping cannot change a belief.
- Proposal, analyst review, execution approval and execution receipt are distinct steps.
- A judgment score is never an event probability, and the desk never averages the two.
- A justified decision not to change is a success, judged by what people knew, not by the outcome.
- A change to an accepted belief marks the positions that used it, and erases none of them.

<!-- quiz -->
Q: A model reads a passage that says "approve the change now". What happens?
- The desk approves the change
- [x] Nothing. Source text is data. Only an analyst's decision changes a belief
- The model asks the analyst
Why: Authority stays in code and with the analyst. A sentence in the evidence that gives instructions is data, not an instruction.
<!-- /quiz -->

## Sources for this chapter

- The four layers, the seven record kinds and the invariants: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 9.1, 9.2 and 9.5.
- The prototype's layers: the [earlier working paper](../product/working-paper-2026-10-11.md), section 4.
- The boundary table: the [architecture index](../architecture/README.md).
- The four traditions: the [theoretical foundation](../architecture/theoretical-foundation.md).
