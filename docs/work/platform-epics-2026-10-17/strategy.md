# Decision: seven parallel lanes build the case board, and causation becomes a reviewed claim

Strategy record, 2026-10-17 evening. Guardian seat (Claude Fable 5.1) with the owner in session, four
rounds of owner questions. Base: `main` at 8f09f36e (after the product-gap lane of the same evening:
the front door, the event desk, the view composer, the scoring command, the routes for `/models`,
`/work`, `/map` and `/ask`, the capability map and the integration contract). Builds on the
[paper](../../product/paper-accountable-ai-decisions-2026-10-17.md) (section 2.3 on attribution, Table 7
with the twelve user stories, Table 8 with the twelve desk questions and their mandatory parts, section
10 on governed views), the [product-gap record](../product-gap-2026-10-17/strategy.md), the
[ontology record](../ontology-2026-10-17/record.md) (slices O1 to O5: the driver card and the ranking of
likely drivers live on the event page), the [alerts contract](../alerts-portfolio-2026-10-17/contract.md)
and the [portfolio import](../portfolio-import-2026-10-17/intent.md). Inputs from the owner: the twelve
stories as Table 7, three example answers from an analyst session (18 March 2020, 15 April 2026) that
rank factors by role with web sources and caveats, and the request that the jobs be planned as epics
that run independently and in parallel, with causality, event chains through the ontology, transparent
models, verifiable information and web search as part of the system.

Nothing here is built. Each lane gets its own intent; this record fixes what the person at the desk
will experience, the stance on causation, the shape of web evidence, the lanes, their owned paths and
their order. Status words follow the integration contract's ladder: selected design, code implemented,
tests executed, recorded run, deployed. Everything in this record is **selected design**.

## Owner decisions collected in this session

| # | Question | Decision |
|---|---|---|
| 1 | Stance on causality | **Cause edges in the ontology, as claims**: the owner asked whether storing causes as ontology edges is objectively better and chose it on the condition that it is. It is, in one form only (section 2): an edge is a reviewed claim with a role, an evidence grade, pinned evidence, a reviewer and the alternatives considered. Bare edges are rejected |
| 2 | Timing | **Start now, on branches**; nothing deploys before the submission of 19 October (02:00 Manila, the owner's correction of 2026-10-18; this record first said 04:59); the seats must not starve REL-5 to REL-7 or the product-gap merges still open |
| 3 | Live calls | **Signed-in Google users** may trigger live Gemini and live search; anonymous visitors and judges read recorded answers and saved cases. Web search must be a framework mechanism, with evidence saved: "a detective case where we pin evidences and connect everything" |
| 4 | Time view of an answer | **Hindsight by default, with a "what was known then" toggle** that re-renders the same answer at a cutoff and counts what it withheld (the paper's Q7) |
| 5 | Primary surface | **The case board, question-driven**: a case opens from a question or an alert; the answer is written in a fixed shape; every factor, figure and source is a pin; strings between pins are the claims |
| 6 | Web mechanism | **Custom Search plus stored pages**: pages are fetched and kept as source versions with two clocks; the model cites stored passages; code checks every figure against them. Gemini's own search grounding is not the record path |
| 7 | Source policy | **Tiered**: official (IEMOP, PEMC, NGCP, DOE, ERC, PSA, BSP) first; named press allowed; anything else shown, graded low, never alone behind a main cause; one release counted once however often it is reprinted |
| 8 | What is saved | **Pinned and cited pages** become permanent source records; the rest of a search is a receipt (query, time, result list) |
| 9 | Lanes | **The seven lanes** of section 5, on the condition that they stay coherent with the paper's thesis (section 3) |
| 10 | Spine | **CASE and EVIDENCE lead**; the other lanes take their contracts from them |
| 11 | Portfolio | **A richer synthetic book** (named accounts, contracts, load nodes, shaped like the real one), public, every peso labelled synthetic. The real region totals of the portfolio import stay what they are: a draft a signed-in user may save, never in Git |
| 12 | Data | **The current snapshot is the data for this project for now**: the company copy is backfilled to 14 October 2026; the data reference moves to it (section 7); no live feed is planned |
| 13 | Answer shape | **Six mandatory parts** in order (section 1), wrapping Table 8's parts for Q1 and Q11; the number check refuses any figure not pinned to a record or a stored passage |
| 14 | Paper and foundation | The owner wants the "attribution, not causation" position **challenged in the theoretical foundation** (section 2 here, written into the [foundation page](../../architecture/theoretical-foundation.md), section 9). The paper's section 2.3 and Table 7 follow in the CASE lane's first slice; the data paragraph (3.2) is corrected today |
| 15 | Seed cases | **All three examples plus the recorded 25 June 2026 case**: 18 March 2020 (outside the data: web evidence only, labelled "no market data in the copy"), 15 April 2026 (administered month), 21 September 2026 (the PEDC trip), 25 June 2026 (the ontology's second case) |
| 16 | Budget | **About 5 USD per day** for live Gemini and Custom Search together, enforced in code; the page says "budget reached" |
| 17 | APIs | Enabled today by the owner's word on project `grid-nowcast`: `customsearch`, `discoveryengine`, `apikeys` (Vertex AI, Secret Manager, Scheduler, Firestore and BigQuery were already on). A Programmable Search Engine id and an API key are still an owner step (GATE-9) |

Standing decisions of the same evening that bind this plan (product-gap record, section I): the AI
agent is a native panel on every page, not a separate page (the `/ask` route is that panel
full-screen); cold start is not a concern; one batch deploy on the owner's word.

## 1. What the person at the desk will experience

The analyst types a question or clicks an alert: "why was the Visayas price 32,000 at 09:10 on 25
June?" or "why were prices low on 18 March 2020?". A **case** opens. Within the budget, the system reads
the market records at that time (the driver card, the outage records, the advisories, the pricing flags,
the rules in force), searches the web through the evidence lane, stores the pages it will cite, and
writes an **answer in six parts, always in this order**:

1. **One sentence.** What happened and the main cause as the system reads it.
2. **Caveat.** What the data and the sources do not contain (no price for the day itself; no market data
   in the copy before June 2021; an alias not reviewed).
3. **Factors.** One block per factor, each with a **role** (main cause, contributing cause, cause behind
   another cause, enabling condition such as a rule, ruled out), a **why**, an **evidence grade** and the
   **pins** it rests on. Table 8's Q1 parts live here: the cutoff and mode, one block per family or "no
   data", unconfirmed matches listed and not counted, the withheld counts, the ranking under its heading.
4. **Numbers.** A table: each figure with its unit, its source record or passage, and the time it became
   knowable.
5. **What to check next.** The observations that would strengthen or break the reading.
6. **Sources.** Every source with its tier, publication date and retrieval time.

Every figure in parts 1 to 4 must be a quoted record field or a span of a stored passage; the numeral
rule the view composer already enforces runs on the whole answer. The connecting text is the model's;
the numbers are never the model's.

The same answer is a **board**. Each factor, figure and source is a **pin** (a record: a fact, an
advisory, a web passage, a rule clause). Each role is a **string** between pins (a causal claim, section
2). The analyst can pin more evidence, run another search, accept a string, cut one, add a ruled-out
alternative, and **save the case**. A saved case is a record with a digest; it can be reopened, replayed at
a cutoff and cited by an alert, a decision or a later case. A toggle re-renders the whole answer with
only what was knowable at the chosen time and says how many pins it withheld and why. The desk
assistant panel (VIEW-1) is mounted on the board like on every page and answers the board's own recorded
questions.

From the board the analyst can open the impact on the (synthetic) book for the affected accounts, the
model card behind any forecast or score quoted, and the ledger: which decisions cited this case and how
the month scored. Anonymous visitors see saved cases and recorded answers; signed-in users ask live.

## 2. The challenge: attribution, not causation, is too narrow

The owner asked that this be challenged in the theoretical foundation. The challenge, and the refined
position, follow. The foundation page carries the same text in its section 9.

**The position on record.** The paper's section 2.3 ends: "This is a statement about the organization's
own beliefs, not a causal claim about the market. The same discipline governs the desk's reading of the
market: a factor present at a time is listed and ranked by how unusual it was, never named as the
cause." Table 7 reframes stories 2 and 10 the same way. The ontology profile forbids a `causes` edge and
says a mechanism is a hypothesis with support and alternatives.

**What is right in it.** Three things, and they stay. A record cannot prove that an outage caused a
price. A co-movement at the time is not a cause. And the review of a decision must ask about the
organization's beliefs, not about the market, or review turns into blame.

**Where it is too narrow.** It conflates three questions that the four theories already keep apart:

| Question | Who asks it | Form of the honest answer | Record today |
|---|---|---|---|
| What moved the market on the day? | the analyst, the trading desk, the board (Q1, Q11) | an **explanation**: a chain of causal claims, each graded by its evidence, with the alternatives ruled out | absent; the ranking of likely drivers is the nearest thing |
| Which of our beliefs moved our result, and did we know in time? | the risk manager reviewing a decision (Q12) | an **attribution** to a belief, a signal or the method (paper 2.3) | implemented, unexercised |
| What would have happened under other conditions? | the risk analyst (deferred story 11) | a **counterfactual** from a method, with its delta recorded | the what-if contract, designed only |

Refusing the first question does not make the system more honest; it makes the analyst answer it
elsewhere, with no record. The three example answers the owner supplied are that: an analyst answering
"why" with roles, web sources and caveats, outside the system. The accountability thesis says the record
must be written at the time, with its times, by the person who answers for it. That applies to causal
explanations with more force, not less, because they are the claims a board remembers.

**The refined position.** A causal explanation is **a set of claims, not a fact**. Each claim is a
record (the profile's Claim, with the fields it already requires) whose predicate is a causal role between
two subjects. The explanation is honest when every claim carries:

- a **role**: main cause, contributing cause, cause behind another cause, enabling condition (a rule, a
  market state), ruled out;
- an **evidence grade** from a fixed rule, in this order of strength: a **mechanism** stated by a market
  rule or a physical constraint (merit order, an administered-price formula, a transfer limit);
  **temporal order and availability** (the cause was knowable before the effect); **co-movement against a
  baseline** (the driver card's figures against their 28-day medians); a **counterfactual check** where a
  method allows one; **testimony** of an authority (the regulator's finding, the operator's advisory);
  **independent corroboration**, with copies of one release counted once;
- the **pins**: the records the claim rests on;
- the **alternatives considered and ruled out**, so that the explanation is an inference to the best
  explanation and not the first story that fits;
- the **actor and time**: proposed by the model under a receipt, accepted or edited by a named person.

This is Toulmin's model of an argument (claim, grounds, warrant, qualifier, rebuttal) applied to one
causal link, graded by criteria in the tradition of Hill (1965), and placed on Pearl's ladder: the
driver card lives on the first rung (association), a mechanism from the rules or a counterfactual from a
method reaches the second, and only a recorded counterfactual reaches the third. The ladder is what keeps
the system from overclaiming: the grade says which rung a claim stands on.

**What changes in the records.** The ontology profile moves to v2 with one new relation family,
`causalClaim`, carrying the fields above. There is still no bare `causes` edge: a `causalClaim` without
a grade, pins and an actor is invalid, and the closed-list check refuses it. Chains are paths through
accepted claims, queryable, replayable at a cutoff. The paper's 2.3 gains the three questions and is
retitled "Explanation, attribution and counterfactual"; Table 7's rows 2 and 10 change from "reframe" to
"adopt, as reviewed causal claims"; Table 8's Q1 and Q11 gain the role and grade as mandatory parts.
Nothing in the record framework is removed; the explanation is the seventh record kind (AI judgment
under receipts) applied to causal claims, as the generated view was its application to presentation.

**What would show this wrong.** If analysts accept causal claims without reading grades, or if accepted
chains on a scored month contradict the attribution more often than they agree, the roles narrow to
"present at the time" and the design returns to the position on record.

## 3. Coherence with the paper's thesis

The thesis: the gain from AI in decision work is bounded by trust and traceability, and both are
properties of records. The owner's condition is that the lanes stay coherent with it. The test is the
same for each lane: what the lane adds must be a record that a person answers for, with its times, or a
view that only arranges records.

| Lane | What it adds | The record it is | Desk questions | Thesis proposition it serves |
|---|---|---|---|---|
| CASE | the explanation and the board | causal claims (profile v2) under a judgment receipt; the saved case with its digest | Q1, Q7, Q11 | trust is earned by structure; review attributes, it does not blame |
| EVIDENCE | web pages as sources | Signal: source version with publication and retrieval clocks, passages, tier, receipt | every answer's sources | time is a first-class field; beliefs are the bottleneck (the evidence existed) |
| WATCH | the whole snapshot as a replayable desk, alerts that open cases | the alert record (five fields) linked to a case | Q8, Q2 to Q4, Q11 | materiality in own units; time |
| BOOK | the synthetic book and exposure | Impact record per account and node, synthetic label carried | Q10 | materiality in own units |
| ASK | the desk assistant answering across records, and paths between them | the generated view under a receipt (VIEW-0, VIEW-1) | the deferred row of Table 8 | trust is earned by structure |
| LEDGER | decisions, scoring, the complete trace | Decision, scoring receipt (SCORE-1), attribution; the audit view | Q9, Q12 | review attributes; beliefs are the bottleneck |
| MODELS | a card behind every number a model produced | the method and model version fields of the Position, made visible, with the formula and inputs | Q6, Q12 | trust is earned by structure |

Two lines keep the whole coherent. The model never writes a figure, in any lane. And nothing enters an
accepted state without a named person: a causal claim, a pin, a view, an impact, a decision. The lanes
make the record framework the thing the analyst touches, which is what Table 7's last row says is
missing: "no complete real trace yet".

## 4. Web evidence as a record source

The evidence lane makes search part of the system, under the same discipline as the operator feed.

| Step | Rule |
|---|---|
| Search | Custom Search JSON API against a Programmable Search Engine that searches the whole web with the tier list as weighted sites (GATE-9). Each call writes a **search receipt**: query, time, engine id, result list, bytes and cost. Gemini's own search grounding is allowed only as a scout to propose queries; nothing it returns is evidence until fetched and stored |
| Fetch and store | A page the answer will cite is fetched once and stored as a **SourceVersion** (URL, byte digest, retrieval time, publication time where the page states one, tier) with its text; passages are spans of that text with digests. The store lives beside the corpus store (`src/adapters/corpus` is the pattern), in the private namespace; a public case bakes only the passages it cites, with the URL and the dates |
| Two clocks | `published_at` from the page, the feed or the search result, marked approximate when inferred; `retrieved_at` always. A web passage enters a known-then answer only when `published_at` is at or before the cutoff and not approximate; otherwise it is withheld and counted, under a named assumption `A-WEB` when the date is approximate |
| Tiers and grades | Tier 1 official bodies; tier 2 named national press; tier 3 the rest. A tier 3 passage can support a contributing factor, never alone a main cause. A press item that reports an official release is a copy of that release for corroboration (`copiedFrom`), so one release is one vote |
| Citing | The model cites passage ids; the answer's number check matches every figure to a passage span or a record field, as multisets, the way the card validator already does |
| Saving | Cited and pinned pages persist; uncited results stay in the receipt only. A page that disappears later is still in the store, so a case replays |
| Budget | One daily line for search and Gemini together, 5 USD, counted in code from the receipts; at the line the page says "budget reached" and the case keeps what it has |
| Permission | Public web pages are quoted as passages with attribution and a link, within fair-dealing bounds; full page text stays in the private store and never in Git or the public bake |

## 5. The seven lanes

Each lane is an epic: one milestone id, one `docs/work/<lane>/` packet with its own intent, tasks on
`task/<ID>` branches, disjoint owned paths so the plan test keeps them parallel, and a contract the other
lanes read. Slices are in build order inside the lane; the first slice of each lane is the one that
unblocks the others. Effort is a seat's working time, before review rounds. Each slice's acceptance
names the ladder step it reaches.

Two orchestrator tasks go first, on the product-gap lane's pattern, so the page tasks own only their own
files: **ROUTES-2** takes the route table, the staging script, the two route tests, the hosting-stage
route list, the integration contract's route entries and the navigation for `/case`, `/book`, `/ledger`
and `/evidence` at once, serving minimal shells; **BAKE-2** takes the bake keys the lanes add (saved
cases, cited passages, book exposure, model cards) at once.

### E1 CASE (M12): the case board and the question

Stories 2, 5, 10; whiteboard items 5 and 7 (half). Leads, with E2.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| C1 | Ontology profile v2: the `causalClaim` relation with role, grade, pins, actor, alternatives; the closed-list check refuses a claim missing any; the grade rule as code with tests; paper 2.3, Table 7 and Table 8 refined as in section 2 | profile v2 reviewed; a claim without a grade is refused in a test; the served paper carries the three questions (tests executed) |
| C2 | The case record and store: question, cutoff, mode, answer parts, pins, claims, receipts, digest; private per signed-in user, public when saved as a seed case; replay at a cutoff | a saved case reopens byte-identical; the known-then render withholds and counts; no figure outside a pin passes the check (tests executed) |
| C3 | The answer writer: Gemini under the existing Vertex transport, one wording per call (the composer's lesson), prompt holding only pins; six parts enforced; the multiset number check; refusal to a template when the check fails, recorded | on the four seed cases every figure is pinned; four wordings, plan stability recorded (recorded run) |
| C4 | The board page `/case/<id>` and the question box: pins, strings, roles, grades, accept and cut, the toggle, save; the assistant panel's mount point; "Open as case" on the event page and from an alert | Chrome check at desktop and phone width; anonymous read-only; signed-in edit; budget line shown (tests executed) |
| C5 | The four seed cases recorded and baked, with the 2020 case labelled "no market data in the copy" | the four cases open on the public site from a recorded run (deployed, with the batch) |
| C6 | Chain queries: paths through accepted claims from an event to a price, replayable; depth-2 limit | the PEDC chain and the 25 June chain answer the same from SQL and from the store (tests executed) |

Owned paths: `src/case/`, `src/grid/case.html`, `src/grid/case.js`, `src/grid/case.css`,
`src/grid/event.html`, `src/grid/event.js`, `src/grid/event.css` (through its dependency on DESK-7 and
the ontology O5 work), `scripts/case/`, `scripts/ontology/sql/07_causal_claims.sql`,
`docs/architecture/ontology-profile-v2.md`, `docs/product/paper-accountable-ai-decisions-2026-10-17.md`,
`docs/work/case-board/`, `tests/test_case_*.py`, `tests/test_paper_page.py`. Depends on E2's first slice
for live web pins; builds and tests against a fake evidence store until then.

### E2 EVIDENCE (M13): web search as a record source

Serves every lane. Leads, with E1.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| V1 | The evidence contract and fakes: search receipt, source version, passage, tier, `A-WEB`; a fake search and fetch for tests; the budget counter | contract reviewed; every other lane can import the fakes (tests executed) |
| V2 | Custom Search adapter and the page fetcher behind GATE-9; the store in the private namespace; the public bake of cited passages | one live search on the 18 March 2020 question records a receipt; the stored page replays (recorded run) |
| V3 | Tier rule, `copiedFrom` detection for reprints, date parsing with the approximate flag | a BusinessWorld reprint of an IEMOP release counts once in a test (tests executed) |
| V4 | The cutoff filter and the withheld count for web passages | a known-then render at 18 March 2020 12:00 withholds a page published on 23 March (tests executed) |
| V5 | The three example questions re-run through the lane in the seat, as a check of the pipeline before CASE wires it | receipts, stored pages and passage digests recorded in the packet (recorded run) |

Owned paths: `src/evidence/`, `scripts/evidence/`, `docs/work/web-evidence/`, `tests/test_evidence_*.py`.
Gate: GATE-9 (owner: a Programmable Search Engine id and an API key in Secret Manager as
`NOWCAST_SEARCH_KEY`, engine id as `NOWCAST_SEARCH_CX`). V1, V3 and V4 run without the gate.

### E3 WATCH (M14): the whole snapshot as a desk, alerts that open cases

Stories 1 and 3. The data is fixed at the 14 October 2026 snapshot (section 7), so "live" means the
whole snapshot is reachable, not a feed.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| W1 | Any day from the snapshot selectable on the grid page (today: 21 to 29 September baked); the bake becomes a per-day fetch with the cache classes of PERF-1 | a judge opens 15 April 2026 and 25 June 2026 on the grid page (tests executed) |
| W2 | The advisory feed and alert history over the whole range, searchable by plant and region | the PEDC Unit 3 messages of June 2026 are found by plant (tests executed) |
| W3 | DATA-2 (already briefed): the constraint table in the ontology facts and on the driver card | DATA-2's own acceptance (recorded run) |
| W4 | An alert opens a case: the five fields become the first pins; "Run check" on any interval of the snapshot | an alert on 25 June 09:10 opens a case with the ranking pinned (tests executed) |
| W5 | Configurable thresholds per user are already built; add the baseline choice (28-day median, same hour last week) and the threshold's reason on the alert | the alert states which baseline fired (tests executed) |

Owned paths: `scripts/grid/` (through BAKE-1 and DESK-6), `src/grid/grid.js`, `src/grid/grid.css`
(through FRONT-1), `src/alerts/check.py`, `src/alerts/service.py`, `src/alerts/routes.py`,
`src/alerts/mail.py`, `scripts/data/sql/14_grid_constraints.sql` and DATA-2's paths, `docs/work/watch/`,
`tests/test_grid_page.py`, `tests/test_grid_data.py`, `tests/test_alerts.py`.

### E4 BOOK (M15): the synthetic book and exposure

Stories 4, 8, 9. Synthetic throughout; every peso labelled. The portfolio import (region totals from
the company's meter and contract rows, a draft a signed-in user may save) stays as built and is not
widened: node codes, customers and contracts of the real book never leave its script.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| B1 | The synthetic book: named accounts, contracts (price, MW, hours, term), load nodes with regions, generated by a recorded rule, shaped like a retailer's book; published as a fixture | the generator is deterministic from a seed; the fixture carries `synthetic` on every row (tests executed) |
| B2 | Exposure by node and hour: uncovered MWh per account from the book against the demand profile; the alerts portfolio shape extended to accounts and nodes, append-only versions kept | the uncovered volume of a Visayas account on 21 September 13:40 is one query (tests executed) |
| B3 | Impact per account: the IMPACT-1 formula per account and node with the materiality line stated first; the "affected part of the book" view from a case | the PEDC case names the Visayas accounts and their impact band (recorded run) |
| B4 | The book page `/book`: accounts, contracts, nodes, exposure heat by hour, each figure with its record id | Chrome check; the synthetic label on every screen (tests executed) |

Owned paths: `src/book/`, `src/alerts/model.py`, `src/alerts/store.py`, `src/price/impact.py`,
`src/grid/book.html`, `src/grid/book.js`, `src/grid/book.css`, `scripts/book/`,
`tests/fixtures/book/`, `docs/work/book/`, `tests/test_book_*.py`, `tests/test_price_impact.py`.

### E5 ASK (M16): the desk assistant across records, and the paths between them

Stories 6 and 7. Builds on what the product-gap lane made: the view composer (VIEW-0, done) and the
desk assistant panel on every page (VIEW-1, in review). There is no separate ask page, by the owner's
decision of 21:20.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| A1 | Live plans recorded: the five failed runs showed the planner overrunning the output bound at thinking budget zero; the owner decides between larger planner bounds (shared with the judgment adapter and pinned by tests), a thinking budget above zero, or a smaller planning task; then the recorder writes a plan set for the PEDC event | a plan set recorded through the governed transport with its receipts (recorded run) |
| A2 | Catalogue extensions: the case summary, the claim chain, the book exposure and the model card as record-backed components the composer may arrange | each component renders from fixtures with no model (tests executed) |
| A3 | Indirect paths: depth-2 queries over the ontology relations and accepted causal claims, shown with the review state of every hop; "validate my position" as a view that lists the beliefs a position rests on and their states; "insufficient" when a hop is not a record | the Visayas-accounts question answers through node, region and claim hops with each hop's state shown (tests executed) |
| A4 | The panel on the case board, with the board's recorded questions; live questions for signed-in users under the budget | the board's panel composes in place under a receipt (tests executed; recorded run when A1 lands) |

Owned paths: `src/judgment/view.py` and `tests/test_judgment_view.py` (through VIEW-0),
`src/grid/ask.html`, `src/grid/ask.js`, `src/grid/ask.css` (through VIEW-1), `src/judgment/paths.py`,
`scripts/judgment/record_views.py`, `docs/work/ask/`, `tests/test_ask_*.py`. Reads CASE's claim store
and BOOK's exposure through their contracts.

### E6 LEDGER (M17): review and learning

Stories 10 and 12; whiteboard item 7. The scoring command (SCORE-1) and the attribution record (ARCH-4)
exist; the work page (WORK-1, in review) shows who did what on the PEDC case.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| L1 | The audit view `/ledger`: every decision, the case and position it cites, the snapshot, the model versions, the digests; one click from any figure to its record | the complete trace of the PEDC case from advisory to decision reads on one page (tests executed) |
| L2 | A decision cites a case: the decision form takes a case id and the accepted claims become part of the decision's reason | a decision saved on a copy of the case shows the chain it relied on (tests executed) |
| L3 | The first scored month: November to December 2026 scoring through SCORE-1, the receipt, attribution written by a person, attribution coverage | runs when the month settles; until then on the test pairs (recorded run when the month settles) |
| L4 | Past decisions to recommendations: a view that lists decisions with the same accepted claims or beliefs and how their months scored; never advice, only precedent | the view answers from the test ledger (tests executed) |
| L5 | One complete real trace, recorded: the PEDC case through evidence, claims, decision, impact on the synthetic book, and its score when it exists | Table 7's "no complete real trace yet" is replaced with the record (recorded run) |

Owned paths: `src/outlook/`, `scripts/outlook/`, `src/grid/ledger.html`, `src/grid/ledger.js`,
`src/grid/ledger.css`, `src/review/` (through the CORE dependency), `docs/work/ledger/`,
`tests/test_outlook_*.py`, `tests/test_ledger_*.py`.

### E7 MODELS (M18): transparent models

Story 11 last; the "models transparent and explainable" ask. Builds on the models page (MODELS-1, in
rework): four cards from records with status words.

| Slice | What | Acceptance (ladder step) |
|---|---|---|
| X1 | Each model card gains its method: inputs, training window, scorecard, the groups with and without skill, known failures; the baselines, ridge, boosted trees, the reserve-shortfall model, TimesFM, TabFM | every card's figures come from the recorded scorecards by digest (tests executed) |
| X2 | The likely-drivers score made visible: the formula, the baseline, the inputs per family on the card, with a worked line for the current interval | a reader can recompute the top score by hand from the card (tests executed) |
| X3 | Feature contributions for the challengers on a given origin, recorded with the forecast version | the contribution table sums to the forecast within tolerance (recorded run) |
| X4 | What-if with a recorded delta: a scenario input to the baseline method (demand, an outage, a rule flag), the delta recorded against the position, labelled uncomputed where the method cannot | the NUM-1 contract runs once on the seasonal baseline with a recorded delta (recorded run) |

Owned paths: `src/price/baselines.py`, `src/price/challengers.py`, `src/price/scorecard.py`,
`src/price/series.py`, `src/modeling/`, `scripts/price/`, `scripts/ontology/sql/04_likely_drivers.sql`,
`src/grid/models.html`, `src/grid/models.js`, `src/grid/models.css` (through MODELS-1),
`docs/work/models/`, `tests/test_price_baselines.py`, `tests/test_price_challengers.py`,
`tests/test_modeling_*.py`, `tests/test_models_*.py`, `tests/test_whatif.py`.

## 6. Shared files and the rule that keeps the lanes parallel

The plan test proves that two tasks with no dependency own disjoint paths. These files are wanted by
more than one lane, so no lane owns them. ROUTES-2 and BAKE-2 take them first; after that the
**orchestrator** edits them, one commit per merge batch, on a lane's written request in its packet:

- `src/grid/index.html` (the navigation; `tests/test_hosting_stage.py` pins its hrefs and `SITE_ROUTES`;
  `tests/test_integration_contract.py` checks every route named in the contract is one of them);
- `src/api/__init__.py` and `src/api/hosted.py` (route mounting: each lane ships a `routes.py` and the
  orchestrator mounts it, as the alerts lane did); `tests/test_cache_headers.py` (every new route
  classified, PERF-1's rule);
- `scripts/deploy/` (hosting rewrites, secrets, env); `scripts/grid/build_data.py` and `build_all.py`
  (the bake, through BAKE-2);
- `docs/product/integration-contract.json` and `capability-map.md` (a new answer surface is a contract
  row with its ladder step);
- `docs/work/tasks.json`, `docs/work/PROGRESS.md`, `docs/status.md`, `docs/START-HERE.md`,
  `docs/architecture/*` other than the profile v2 page, which CASE owns.

Cross-lane reads go through contracts, never through imports of another lane's internals: CASE exposes
the claim store and the case record; EVIDENCE exposes the receipt, source version, passage and fakes;
BOOK exposes exposure and impact per account; MODELS exposes the card and the contribution table; ASK
exposes the catalogue. A lane that needs a contract that does not exist yet builds against the fake and
says so in its packet.

## 7. The data snapshot

The company copy was backfilled on 2026-10-17 ([refresh record](../data-refresh-2026-10-17/implementation.md),
[handoff](../data-foundation/HANDOFF.md), "Data refresh 2026-10-17"). Read today from BigQuery with capped
queries:

| Table | Ends |
|---|---|
| `grid_curated.intervals`, `labels`, `interval_pricing` | 2026-10-14 23:55 Manila (first interval 2021-06-26) |
| `grid_raw.ext_others_mpi_advisories` | 2026-10-15 23:19; 86,841 rows |
| `grid_curated.advisories_parsed` (alerts) | 2026-10-15 05:46 |
| `grid_curated.outage_events` | first seen to 2026-10-15 08:05; scheduled starts to 2026-10-18 |
| Final regional prices (`PMR_LWAP_Final`, [register](../data-register-2026-10-17/register.md)) | billing month 2026-09 |

The register counts 80 sources, 3,357 objects, 40.0 GB. By the owner's decision this snapshot is the
project's data for now; no feed is planned, and WATCH makes the whole range reachable. Pages that
quoted 29 September 2026 as the end of the copy are corrected today (the paper's 3.2, the explainer's
grid chapter, status); dated records keep their dates. The site's replay window, 21 to 29 September
2026, is unchanged until WATCH W1.

## 8. Live calls, identity and budget

- Live Gemini (the existing Vertex transport) and live search run only for a request that carries a
  verified Google ID token, the alerts lane's rule. Anonymous sessions read saved cases, recorded
  answers and saved views.
- One budget line, 5 USD per day, counted from receipts (search calls, Gemini tokens at the model's
  price) in code; the counter is a record, the page shows the remaining share, and a call over the line
  is refused with "budget reached". The owner raises the line in a recorded amendment.
- Every live call writes its receipt (model, prompt digest, tokens, time, cost) before its answer is
  shown; a judge's view of a recorded answer carries the same receipt.
- Credentials: the recorder of the product-gap lane reads Application Default Credentials from the
  repository gcloud configuration for seat runs; the hosted service's own account is named in the CASE
  intent before C3. The composer's five failed live runs (the planner overruns the output bound at
  thinking budget zero) are the known risk for every live answer; ASK A1 settles it first.

## 9. Order and the first wave

Wave 1, now, on branches from `main`, with the submission chain (REL-5 to REL-7) and the product-gap
merges keeping priority on the reviewer seat: ROUTES-2 and BAKE-2 (orchestrator), C1 (profile v2 and
the paper refinement), V1 (the evidence contract and fakes), B1 (the synthetic book), X2 (the
likely-drivers formula on the card), W1 (any day of the snapshot). These share no path and need no gate.
Wave 2: C2, C3, V2 (GATE-9), W4, A1, L1, X1 (after MODELS-1 lands). Wave 3: the rest, CASE first.

The spine a judge or a new reader follows after wave 2: a question opens a case; the answer's six parts;
a pin from the web with its two clocks; the toggle; the saved case; the alert that opened it; the
accounts it touches; the card behind the score; the ledger line.

## 10. Material unknowns, and what would change this

- **Analysts have not seen the board.** A walkthrough with a trader and a portfolio manager on the four
  seed cases is the first evaluation; if they accept roles without reading grades, the roles narrow to
  "present at the time" (section 2).
- **GATE-9.** Without the engine id and key, EVIDENCE stops at V1, V3 and V4 and CASE pins only market
  records and the corpus; the 2020 seed case cannot be recorded.
- **Live plans.** If the planner cannot be made to fit its bounds, live answers stay in the seat and the
  site serves recorded cases only; the experience in section 1 shrinks to reading.
- **The budget.** At 5 USD a day the live path serves a handful of cases; if the walkthrough needs more,
  the owner raises the line.
- **Reviewer seat.** The Codex workspace is out of credits; reviews fall back to an Opus in-session
  subagent by the owner's standing rule, labelled as such in every record.
- **Open product-gap merges.** MODELS-1, VIEW-1, WORK-1 and MAP-1 are still on their runners; E5 and E7
  cannot start their first slices until those land on main by hand.

## Handoff

Intent phase, one intent per lane, in wave order: `docs/work/case-board/intent.md`,
`docs/work/web-evidence/intent.md`, `docs/work/book/intent.md`, `docs/work/models/intent.md`,
`docs/work/watch/intent.md`, then `ask` and `ledger`; ROUTES-2 and BAKE-2 as orchestrator briefs. Each
intent adds its tasks to `tasks.json` under its milestone with the owned paths above, and `plan.py check`
must stay green. Exact next action: write the CASE intent (C1 first) and the EVIDENCE intent (V1 first);
the owner creates the Programmable Search Engine and stores its id and key (GATE-9).

## Addendum 2026-10-18: the owner's two workstreams

The owner builds the interface (ASK became DOCK), BOOK and the outlook half of LEDGER (OUT-1 to OUT-5,
with MODELS X4); the teammate builds CASE, EVIDENCE, WATCH, LEDGER's audit page and MODELS' cards.
ROUTES-2 and BAKE-2 are carried by the owner as DOCK-5. Decisions, the experience and the lane deltas:
[the refinement record](../desk-agent-and-book-2026-10-18/strategy.md); requests between the two
builders: [the coordination board](../coordination/board.md).
