# The case for Future of Work and Enterprise Productivity

Written 2026-10-16 by the guardian seat at the owner's request: extract the general pattern from the
grid work, state it first, and land it on the Philippine wholesale electricity market as the proving
ground. The category is already selected ([requirements](requirements.md) E4, the
[story and script](story-and-script.md), the [organizer letter](organizer-questions.md)). The decision
record of 4 October placed Future of Work as the fallback behind Sustainability. The switch is right:
the product changes how an analyst, a desk and a board do their daily work; it does not change the
grid. Every claim below carries an evidence grade from the
[evidence ledger](../../work/thesis-challenge-2026-10-16/evidence-ledger.md): measured, recorded
once, built but unexercised, designed only, or absent. The long form of this case, with the applied
results first, six figures and a checked reference list, is the
[companion paper](../../product/paper-accountable-ai-decisions-2026-10-17.md) (revised 2026-10-17).

## 1. The general claim: who answers for a decision made with AI?

AI can now read every signal and draft every change. People still decide, and people still answer
for the result. An organization that cannot show which AI judgment it trusted, and why, has two bad
choices: hold AI back and lose the work it could do, or use it blind and take decisions nobody can
explain or learn from. That is the Future of Work problem, at three levels
([meta framing record](../../work/meta-framing-2026-10-17/strategy.md)):

- **People.** The job moves from finding and reading information to judging it and answering for it
  (framing; no analyst-effect measure exists until experiment 3 runs).
- **Organization.** Without trust, AI is held back; without traceability, it is used blind. Both cost
  money, in lost work or in decisions nobody can review, and the review becomes a blame game (a belief
  with first numbers, VAL-1 and PROJ-1; incidence is absent).
- **Sector.** In an essential, regulated sector, a board and a regulator must see who decided what, on
  which evidence, and when (the readers the owner names; never observed).

The mechanism underneath is belief maintenance. Strip the word "forecast" away and what remains is this. Every organization holds a set of working
beliefs about the world it operates in: what capacity exists, what a counterparty will do, which rule is
in force, what a price will be. Knowledge work is the maintenance of that set: reading signals, deciding
which belief each signal touches, revising or retaining it, and acting on the current set. Decisions are
taken on beliefs; outcomes are explained by beliefs that were wrong or late.

Today that maintenance is done in heads, chats and spreadsheets. Beliefs are unowned and undated,
revisions are implicit, and decisions are reactive and intuition-driven because the chain from signal to
belief to position to action is never written down. When an outcome goes wrong the organization cannot
say what it believed on the day, so the review turns into a blame game and teaches nothing.

The future of work changes the worker, not the job. AI can read every signal, propose every revision and
draft every brief at a scale no desk can match. That moves the bottleneck. The scarce thing is no longer
reading or drafting; it is knowing which AI judgment to trust, and being able to show afterwards who
believed what, on what evidence, when. An organization that cannot answer those two questions cannot put
AI at the core of its decisions, whatever the model can do.

So the general claim, a design hypothesis the paper states and does not yet test: the enterprise
productivity gain from AI in knowledge work is bounded by trust and traceability; traceability is a
property of records written at the time, and trust is earned by structure and confirmed only by
measurement. The product is the operating structure
that gives an AI-core desk those two properties, so that decisions move from reactive and intuition-driven
to objective, position-aware and defensible. The owner's line for it: from market signals to trustworthy,
traceable decisions.

## 2. The structure, without the domain

The four theories behind the structure (belief revision, decision theory, coordination theory,
organizational learning) are on the [theoretical foundation](../../architecture/theoretical-foundation.md) page.

The [architecture page](../../architecture/meta-thesis-and-framework.md) gives the seven records their
fields, code locations, status and the diagram.

Seven records. The ontology gives them a shared vocabulary; time gives them an order; the review closes
the loop. The product thesis calls the same mechanism explicit belief revision; the working paper's
section 4 formalizes the first three parts and the seventh.

1. **Signals with two clocks.** Every signal carries the time it became available and the time it takes
   effect. Nothing is read before it existed, by a person or by a model.
2. **Owned beliefs.** Every working belief is a proposition with an owner, a layer (official, analytical,
   inferred, exploratory, hypothesis), a source, a valid interval and a state (accepted, unverified,
   contradicted). The set of accepted beliefs at any instant is a snapshot, computable for any past day.
3. **Versioned positions.** Whatever the organization derives from its beliefs, an outlook, a plan, a
   budget, a case, is stored as a version: inputs by digest, beliefs by id, method and model version,
   cutoff. Versions are superseded, never edited.
4. **Impact in the organization's own units.** A position meets the thing it serves, a portfolio, a
   budget, a capacity plan, and becomes a number the board understands. A signal is material when that
   number crosses a stated line. Only material changes reach the decision-maker, which is what turns
   reactive triage into objective, position-aware action.
5. **A decision bound to a version.** What was decided, on which version, on which belief snapshot, by
   whom, when.
6. **Review with attribution, not blame.** When the truth settles, the position is scored and the miss
   is attributed: to a belief that changed, to a signal that arrived late, or to the method. The review
   reads what the organization believed on the day, not who to blame, and the next recommendation starts
   from that reading.
7. **AI as the core worker, under receipts.** A model reads the signals under the cutoff and proposes,
   for each one, which belief it touches, what the revision would be and why, with citations. People keep
   acceptance. The model never decides and its answer never becomes the record without a person's
   disposition.

## 3. The challenge on the board: how can a user know when to trust the AI?

Not by a claim about the model. Trust is earned per judgment, by structure, and each layer below is a
thing a user can open and check. Evidence grades are from the ledger.

| Layer | What the user sees | Why it earns trust | Evidence grade |
|---|---|---|---|
| bounded questions | the model answers a fixed set of eight questions, each with a closed answer set, not a free essay | an answer can be wrong in one named place, and compared across runs | built; frozen contract |
| citations to records | every answer points at the signal and the belief by id and passage | the user checks the source, not the model's word | built; recorded once on the real case |
| cutoff discipline | the model saw nothing after the cutoff; the records prove it | no leakage from the future, so a past judgment can be replayed | built; tested |
| stability receipt | the same questions in four presentation forms (option order, labels and passage order varied); the receipt shows where answers flip | a judgment that changes with the wording is flagged, not hidden | built; recorded once; all flip rates 0 under the scripted backend, so unidentified live |
| disagreement shown | when the model and the case reading differ, the page says so | the system does not pretend to one truth | recorded once (the return-cutoff disagreement, open) |
| scoring against what settled | positions are scored when the truth arrives; misses attributed | the model's track record is a table, not a reputation | scoring built, no real month scored yet (first pair November to December 2026); attribution of a miss designed only |
| the person decides | retain, change, or open for review, with a reason, kept | the human holds the authority and the accountability | built and hosted; exercised in smoke tests on copies of the PEDC Unit 2 case; the real case records no analyst disposition |
| immutable records | nothing is edited; everything is superseded with a time | a review can rebuild any past day | built; tested |

Where this is honest about its limits: the AI's calibration is unmeasured, the live run happened once,
and on its own test the eight-question bundle tied a single question (22 of 28 each) while on the
held-out split the single question won, 8 of 10 to 7 of 10. The structure holds even if
the model is mediocre; that is the point of it. A better model raises the hit rate; the receipts are what
let anyone see that it did.

The structure also guards against the opposite failure, over-trust. Automation bias is real; the design
answers it with the disposition step (a kept belief with a reason counts as a success), the disagreement
display, and a scorecard that will show a bad model as bad.

## 4. What changes for the organization

| From | To | The record that does it |
|---|---|---|
| reactive triage of every signal | only material changes reach the board, with the impact in pesos | impact and materiality (part 4) |
| intuition-driven calls | a position with its beliefs, sources and method on one page | versioned positions (part 3) |
| blame after a miss | attribution to a belief, a late signal or the method | review with attribution (part 6) |
| "what did we know?" unanswerable | the belief snapshot for any day | owned beliefs with time (parts 1, 2) |
| AI as a chat window beside the work | AI as the first reader of every signal, under receipts | the receipt stack (section 3) |
| productivity as output per hour | productivity as reviewed belief revisions per day and misses attributed | the scorecard |

That last row is the productivity definition this entry proposes. For an AI-core desk the unit of work is
the reviewed belief revision: a signal read, bound to a belief, proposed, disposed with a reason, and
later scored. Throughput is revisions per analyst-day; quality is the share of misses the review can
attribute and the share of decisions defensible from the record alone. Both are countable from the
records without a survey.

## 5. The instance: a retailer in the Philippine wholesale electricity market

The position here is a price outlook; the beliefs are the assumptions behind it.

| Structure part | In this domain | Evidence grade |
|---|---|---|
| signals with two clocks | operator advisories, outage schedules, registrations, project lists, rule notices, with posting time and effective time | measured (advisory and schedule times reproduced from the company's market copy) |
| owned beliefs | three families: demand, supply (availability and entry dates), rules and policy actions | built (register with 42 rows on main); ownership by a person: designed only |
| versioned positions | the price outlook per load node and region, day, week and month, on the billing-month clock, scored against final settlement prices | built (archive on main); scorecard measured (three baselines, rolling origins 2021 to 2026) |
| impact in own units | uncovered volume by hour times the outlook's price band less the contract price, in pesos; materiality line stated first | built and recorded once (IMPACT-1, synthetic portfolio against the pre-backfill exports; a method demonstration, never a business number) |
| decision bound to a version | the retained or revised position on the event page, saved with history | built and hosted; exercised in smoke tests on copies of the PEDC Unit 2 case; the real case records no analyst disposition (corrected 2026-10-17 after the foundation page review) |
| review with attribution | scoring receipts once prices settle; one assumption reverted | scoring built and unexercised (first real monthly pair November to December 2026); attribution designed only (corrected 2026-10-17) |
| AI as core worker | eight questions in four presentation forms on Vertex Gemini, citations, stability receipt | recorded once (one live run on the real case); live calls deferred |

Why this domain is a strong proving ground, and not only a convenient one: the stakes are high (prices
range to the tens of thousands of pesos per megawatt-hour), the evidence is public and time-stamped,
the semantics are regulated and verifiable (billing month, settlement basis, node codes), and the
truth settles every month. Most productivity demonstrations cannot be scored. This one can.

## 6. The category's words, mapped

| The brief asks for | What the product does | Evidence today |
|---|---|---|
| access knowledge | turns cluttered market information into owned assumptions with provenance and time; rules in force at a cutoff; plain-language pages for people | the status quo failure is measured: the operator's own schedule records a trip a median 8.5 hours after the advisory, 12 of 27 matched cases more than a day late (typed matching; an earlier, looser pass gave 20.7 hours) ([VAL-1](../../work/validation/outage-lag.md)); a unit listed by the Department of Energy in July as still testing had been dispatching since May ([PROJ-1](../../work/projects/sources.md)) |
| collaborate | evidence routed to the owner of the assumption it touches; decisions and reasons kept where the next person can read them | designed only within one company (roles: analyst, desk, board); cross-company reuse out of scope |
| make decisions | a materiality line in pesos decides what reaches the board; every decision bound to an outlook version | decision form built and hosted; exercised in smoke tests on copies of the PEDC Unit 2 case; the real case records no analyst disposition; impact arithmetic built and recorded once on a synthetic portfolio |
| complete everyday work | the analyst's daily routine, triage, update, brief, with the model doing the evidence legwork under cutoffs | the reading and judgment steps are built and ran once on a real case; the decision step is built and hosted; exercised in smoke tests on copies of the PEDC Unit 2 case; the real case records no analyst disposition; time saved is not measured (section 8) |

## 7. What generalizes

The structure applies wherever three conditions hold: the organization's decisions rest on positions
derived from working beliefs; the evidence that changes those assumptions is time-stamped; and a ground truth
settles later so the outlook can be scored. Fuel and commodity procurement, supply-chain capacity
planning, credit and collections forecasting, and hospital bed planning meet all three. These are
hypotheses; nothing outside the grid has been tried.

## 8. The honest gap, and the measurement that closes it

No number exists for time saved or for material changes caught that a desk without the product would
have missed. The strategy record names the measurement as experiment 3
([strategy](../../work/thesis-challenge-2026-10-16/strategy.md), section F): a manual arm and a desk
arm on the same recorded weeks, scored on missed material items, time to a defensible brief, and time
to answer "what did we know on that day". The owner's company runs it on its own analysts; no model
call is needed for the manual arm. Until it runs, every productivity sentence in the submission is a
hypothesis and is written as one.

## 9. We work the way the product works

The build itself is a demonstration of AI-driven workflow execution on the same pattern, labelled as
method evidence, never as the product. Every task has a brief, owned paths, an acceptance list and a
verify command in one task graph. An executor model builds in its own worktree; an independent reviewer
model reviews against the brief and writes a record; a runner verifies, merges on green, and logs each
round; the orchestrator decides escalations in writing. Numbers from the repository on 2026-10-16:

| Measure | Value |
|---|---|
| tasks registered | 94 |
| tasks done, each with an accepted independent review record | 54 |
| review records in the repository | 58 |
| runner rounds on 16 October (five runs) | 13 tasks merged, 30 review rounds, about 7 hours of wall clock |
| test suite on main after the merge | 1,760 tests |

The same rules apply to the build as to the product: nothing becomes true without a record, a
dependency's bytes travel by digest, and a reviewer's finding is answered in writing or the task does
not move.

## 10. Changes to the submission materials

- The [story and script](story-and-script.md) positioning and 30-second pitch now open with the general
  claim and land on the grid (edited 2026-10-16). The demonstration table is unchanged; it is pinned
  to the deployed screens.
- [START-HERE](../../START-HERE.md) opens with the general claim in plain words, then the analyst
  (edited 2026-10-17; until then it opened on the assumption line alone).
- The [deck](deck.md) was accepted at REL-2 with the earlier positioning on its first slide. That slide
  aligns to this page at REL-4; two positionings in one submission folder would be a contradiction.
- The product thesis and the working paper are unchanged; this page cites them.
