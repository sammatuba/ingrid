# The theories behind the design

<!-- paper: 11 13.5 -->

The design borrows from several research traditions. Each one answers a different question. This
chapter names them in the paper's order, with the works the paper cites, and says what the design
takes from each.

## What the studies of AI at work measure

Studies report that large language models touch a large share of job tasks, and that AI help raises
output in writing and customer support. A field study of consultants found a "jagged frontier": AI
helps inside the model's competence and hurts just outside it. These studies measure the output and
quality of tasks. None of them asks whether an organization can later rebuild and review a decision
made with AI.

## Four traditions, four questions

| Tradition | The question it answers | What the design takes |
|---|---|---|
| Knowledge: belief change and time | What do we know, and when should it change? | belief change as a reviewed step, and valid time apart from recorded time |
| Judgment: decisions and forecasts | What should we do, and what is timely information worth? | a materiality line, proper scoring, and strong simple baselines |
| Work: coordination and authority | Who may propose, accept and act? | the AI proposes, a person decides, and structure counters automation bias |
| Learning: single and double loops | How do outcomes change beliefs and methods? | the scoring receipt, attribution and the review share of chapter 14 |

The paper argues that answering for a decision needs all four at once, joined by one time contract.
Most systems for AI at work use one of them. The join is a record design.

Accountability research frames the need. An actor must explain and justify conduct to a forum that
can question it. Audit frameworks ask for records made during the work, and the EU AI Act asks for
automatic record keeping and human oversight. These sources say that records are necessary. The
paper proposes which records, with which time fields.

## Known risks of model judgment

The design treats each known weakness of model judgment as a rule in code, not as a caveat. Pick a
risk to see the mechanism that answers it.

<!-- widget: finding-mechanism -->

## How far it travels

The problem statement, the record kinds and the view rules name no electricity quantity except in
their examples. A budget, a capacity plan, a credit book or a care pathway also has beliefs and
versions. Each has an impact in its own units, decisions and a later truth. What travels is the time
contract, the seven kinds and the invariants. A domain with no settled truth keeps four of the five
propositions testable and loses the scored month.

<!-- quiz -->
Q: The studies of AI at work report output gains. What do they not measure, according to the paper?
- Whether workers like the tools
- [x] Whether an organization can later rebuild and review a decision taken with AI
- Whether the models are large
Why: The studies measure the output and quality of tasks. The paper's question is accountability: who decided what, on which evidence, and when.
<!-- /quiz -->

## Sources for this chapter

- The traditions and the works: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 11 and its reference list.
- AI at work: Eloundou and others (2024), Noy and Zhang (2023), Brynjolfsson and others (2025), Dell'Acqua and others (2026).
- Reliance and trust: Parasuraman, Sheridan and Wickens (2000), Lee and See (2004), Parasuraman and Manzey (2010), Bansal and others (2021).
- Accountability: Bovens (2007), Nissenbaum (1996), Raji and others (2020), the EU AI Act (2024), articles 12 and 14, and NIST (2023).
- Belief and time: Doyle (1979), Alchourrón, Gärdenfors and Makinson (1985), Jensen and Snodgrass (1999), the W3C PROV data model (2013).
- Decisions and forecasts: Howard (1966), Murphy (1993), Gneiting and Raftery (2007), Weron (2014), Lago and others (2021).
- Organizational learning: Argyris and Schön (1978).
- How far it travels: the same paper, section 13.5.
