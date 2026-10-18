# Decision: the thesis challenged, the estate organized, the scope tiered

Status: strategy record, 2026-10-16, guardian seat (Claude Fable), owner Sam. Read-only session:
nothing committed, pushed, filed, deployed or run against a paid model or cloud service. Problem: before
any new build, challenge the thesis ("stale assumptions, not only model error, make outlooks unreliable;
a grounded, temporally correct, ontology-driven desk traces evidence changes to assumptions and
decisions"), rank the filed use cases, and organize an estate of 79 tasks, 41 work folders (42 with this one), 26 research
dossiers and 14 new issues into one scoped order. Prior decisions: [strategy refresh 10-11](../strategy-refresh-2026-10-11/strategy.md),
[strategy refresh 10-14](../strategy-refresh-2026-10-14/strategy.md), [foundation review 10-13](../foundation-review-2026-10-13/strategy.md),
[corpus plan note](../corpus/intent.md), [ATG plan note](../atg/intent.md).

**Inspected:** `main` at `6a30dfd`, equal to `origin/main`, clean tree. Issues #78 to #90 cite `0701de2c`
and #91 cites `be80e5a`; both are ancestors of `main`, all from 2026-10-16. The 259 commits after
`0701de2c` hold the whole round-3 rework, merge and accept of the fourteen CORP and ATG tasks, so #78 to
#90 describe those tasks as planned or in rework where they are now done and live. The 4 commits after
`be80e5a` are the ATG-8 accept, the batch-4 release record and the session report; nothing in #91 is
contradicted by them. Companion files: [estate inventory](estate-inventory.md) and
[evidence ledger](evidence-ledger.md), both built this session from the repository, not from memory.

Evidence grades used throughout: **measured** (scored against labels or outcomes), **recorded-once**
(one real run with a receipt, unscored), **built-unexercised** (code and tests on fixtures or replay only),
**designed-only**, **absent**. Deployed behaviour (the site replays one recorded Gemini run) is kept
separate from proposed live capability in every section below.

## A. Diagnosis

**The mechanism was designed for one case type and demonstrated on another.** That is the structural
finding none of the issues state. The probe bundle's event question (Q2: testing, synchronisation,
commercial availability, outage or extension) and the whole 25-pair fixture set encode *milestone*
semantics: a project's testing date is not its commercial date, a later target challenges an earlier
assumption. The one real case, PEDC Unit 2 on 2026-09-21, is a forced trip that the operator's own feed
resolved in 93 minutes (trip 1334H, re-online 1507H). The foundation review's own corpus profile says
testing-versus-availability is "right but rare here" (29 testing messages in 2026, mostly SMS tests,
against 1,333 trips and 1,844 returns). So the demonstrated case is the one where the thesis matters
least, and the case the method fits (a commissioning or return target slipping, the PEDC-3 episode of the
10-11 refresh) has no real data in the bucket, which ends 2026-09-29.

Five further findings, each graded ([ledger](evidence-ledger.md)):

1. **The premise has never been measured.** No count exists of how often an outlook was wrong because of a
   stale assumption rather than model error. Grade: absent. The working paper asserts it in the
   introduction without a citation. It can be measured with no model call (section F).
2. **The claimed novelty shows no gain on its own test.** Bundle and single-question baseline tie at 22/28;
   on the held-out split the baseline wins 8/10 to 7/10; the stability receipt is unidentifiable because
   every flip rate is 0 under a scripted backend; the labels are executor-authored and the bundle cannot
   disagree with them (28/28 is a cross-check between two project files). Grade: measured, against the claim.
3. **The real case has no decision and a contradictory record.** The PEDC review records no disposition;
   the live-run record says the analyst's decision at the return cutoff is "retain". The only live run (two
   compiles, Vertex `gemini-3.8-flash`) disagrees with the scripted composition at the return cutoff and
   has not been adjudicated (#73, EVAL-8). Consequences are uncomputed by contract. Grade: recorded-once.
4. **Grounding is mechanics, not semantics, and the corpus is one issuer.** All 30 acquired documents are
   PEMC PDFs from one 2026-04-01 zip with unknown first availability and no permission record for their
   bytes. The rules-in-force page places zero clauses at either cutoff. The live extraction never ran
   (transport refuses the thinking budget, gap G-1; no corpus permission, gap G-3). The ERC order behind the
   reserve-market case was never fetched (HTTP 403); the case knows the action only through IEMOP's report;
   and the action's effective time, 14 October, is after the end of the market data, so "a day before and
   after" has no dispatch or reserve series behind it. Grade: built-unexercised.
5. **The temporal machinery pays off in evaluation and audit, not in the daily decision.** For a working
   analyst the cutoff is always now. Five clocks, lineage groups and belief snapshots earn their cost in
   leak-free replay and in defending a past decision. That points at a different buyer than "analyst
   productivity": the market participant who must show a regulator or a counterparty what was known when a
   procurement or outlook decision was taken. This is a hypothesis, not a finding.

Deployed today: a replay of 21 to 29 September 2026 with one recorded Gemini judgment, five ATG pages
and an event page with a rules panel whose rows are synthetic. No live model, feed, extraction or forecast.

## B. Challenge register

Issue #78's families A01 to A12 are reused with their IDs; the session adds C01 to C08. Dispositions
follow the strategy skill: upheld, revised, rejected, unresolved.

| ID | Assumption | Evidence and limit (grade) | Disposition | Cheapest resolving input or experiment |
|---|---|---|---|---|
| A01 | Archive coverage representative | 24.9 GB; regional summaries missing 2024-11 to 2026-03; reserve labels 2026-03-26 to 09-29; registration gap all of 2025 (measured) | upheld as a gap | Per-table coverage matrix, already half-written in [HANDOFF](../data-foundation/HANDOFF.md) |
| A02 | Regimes comparable | No change-point work; one test month (absent) | unresolved | Blocked on A01; not on the critical path |
| A03 | Clocks truthful | Interval timestamps naive, Asia/Manila unverified; advisories asserted Manila at import (inferred) | unresolved | One IEMOP document check; the compendium may hold it |
| A04 | Market codes interpreted correctly | `pricing_flag` meanings "NOT confirmed" (inferred) | upheld as a gap | Same check as A03 |
| A05 | Thresholds mean what labels say | 23 rows, v1, cut from the September distribution; reserve 1% "from the strategy docs" (inferred) | upheld as a gap | Label each threshold analytical or official in the register (#79) |
| A06 | Unit, resource, plant, capacity linked correctly | Register maps PEDC to U01/U02 83.7 MW, U03 150 MW; 83.7 is a register value, not pre-trip output (measured, caveated) | upheld | One reviewed crosswalk row per case unit |
| A07 | Operator statements accurate enough | SO feed versus press relay already shown to differ on 28 Sept (recorded) | upheld | Keep the feed as the source of record |
| A08 | Reposts not counted as corroboration | Implemented and tested on fixtures (built) | upheld | Corpus-wide check waits on a corpus |
| A09 | Rules resolved at cutoff | Zero clauses placed; one issuer; first availability unknown (built-unexercised) | **rejected as claimed** | Section F, experiment 5 |
| A10 | Probes yield valid labels | Tie with baseline; self-authored labels; receipt unidentified (measured) | **revised**: the bundle is a backend, not the novelty | Section F, experiment 3 |
| A11 | Performance generalizes | Reserve onset only, two regions, one month (measured, narrow) | upheld as a gap | Not on the critical path |
| A12 | Human-assisted review helps | EVAL-7 cut; no analyst session ever ran (absent) | unresolved | Section F, experiment 3 |
| C01 | Stale assumptions, not model error, are the costly failure | No incidence count (absent) | **unresolved, decisive** | Section F, experiments 1 and 2 |
| C02 | The review desk beats a feed plus checklist | H0 in every use-case sheet; never compared (absent) | unresolved | Experiment 3 includes the manual arm |
| C03 | The demonstrated case exercises the mechanism | Forced trip, resolved by the feed in 93 min; bundle built for milestones (measured) | **rejected** | Add UC-04; keep UC-01 as the premise test |
| C04 | "Justified no-change is success" is a usable metric | Unfalsifiable alone: a desk that always says insufficient is always justified | revised: pair it with missed-material-issue recall against adjudicated gold | Experiment 3 |
| C05 | Ontology extensions per use case are safe | UC-02 and UC-03 each propose new types before a second case is validated; research note 27's first trap | revised: no type added until a case needs it in a reviewed intent | None |
| C06 | Provenance and citations are the wedge | Ask the Grid ships provenance, vintages, Projects (#90, product claims) | rejected; the defensible asset is WESM participant data plus rules authority, which is a market niche, not a mechanism | Decide whether a one-market niche is the business |
| C07 | The hosted site shows the thesis | It shows a replay with one recorded judgment and no decision history by a real analyst | revised: it shows the workflow, not the value | HOST-3 walkthrough, already queued |
| C08 | Three authority files agree | milestones, current.json and status disagree with tasks.json (see section G) | rejected | One housekeeping commit |

## C. Refined thesis and wedge

Superseded 2026-10-16, same day, by [problem-and-thesis.md](problem-and-thesis.md) after the owner's
whiteboard: the board is the first reader of the decision history, causality means attribution to an
assumption change, and the portfolio impact in pesos is the materiality test. The text below is kept as filed.

Thesis as filed: evidence changes must be traced to the assumptions and decisions they touch. Refined,
with the parts that are testable made explicit:

> For a WESM market participant, the outlook errors that cost money come from assumptions that nobody
> owns a time-stamped record of. The product is the owned register of accepted assumptions bound to the
> company's own outlook inputs, with evidence changes routed to the assumption's owner and the decision
> kept. The AI judgment is an accelerator inside that loop, not the product.

What this changes. The first-class object becomes the assumption register (#79), populated from the
company's real outlook inputs (the PLEXOS phase-one scope: unit availability and return dates), not a
planning ledger kept for the audit. The probe bundle stays behind its frozen contract as one judgment
backend. The wedge, stated honestly: verified WESM semantics (rules in force, settlement basis, codes),
participant-grade data under a signed permission, and a decision history a regulator or counterparty can
read. None of these is a mechanism a competitor cannot copy; together they are a market the competitor
does not serve. This disagrees with the #81 extension of the same day, which makes the platform
cross-stakeholder and the retailer one application: no role has been validated yet, and the only
assumptions reachable for experiments 1 and 2 are the owner's company's own, so the record starts
participant-centric and lets a measured result widen it. Whether a one-market niche is the business is the owner's call, not a research result.

Falsifiers: if experiments 1 and 2 show that the company's outlook inputs were already current when the
evidence arrived, the premise fails for operator-visible outages and the product narrows to rules and
project milestones. If experiment 3 shows the manual arm matches the desk on missed issues and time, the
AI layer is a convenience and the register alone is the product.

## D. Use-case ranking

Two taxonomies were filed the same day and are not reconciled here; the mapping is proposed, the
decision is the owner's.

| Filed | #91 name | Mechanism fit | Data in hand | Decision owner reachable | Blocker | Rank |
|---|---|---|---|---|---|---|
| UC-01 #82, #84 | UC1 physical events | medium (trip and return are one Q2 option) | yes: advisories, register, outage schedules | yes: the company's own outlook | no prior forecast vintage (G1) | **1**, as the premise test |
| UC-04 (new) | UC3 infrastructure milestones | **high**: the bundle's Q2 vocabulary is this case | no: DOE and company announcements not acquired | yes | no primary milestone record | **2**, sheet only (G0) |
| UC-03 #89 | UC2 rules at cutoff, narrowed to one role | medium: known-then placement is the time contract's natural fit; probes unvalidated for rules | partial: 30 PEMC documents, no ERC or DOE bytes | yes, one role | zero clauses placed; no corpus permission; ERC 403 | **3**, one role before three |
| UC-02 #83, #85 to #88 | not in #91 | low: a diagnosis and forecasting problem; the desk is secondary | partial: prices yes, settlement basis unverified, forecast vintage unknown | yes: the owner's company is a retailer | G1 settlement semantics | **4** as a desk case; **1** by commercial stake |

Discriminators that moved the ranking: #91's UC1 is #82 (same case, say so). #91's UC2 is a single
analyst asking which rules governed at a cutoff; #89's UC-03 is three stakeholders on shared evidence.
The first is the precursor of the second; cross-stakeholder reuse stays unvalidated until one role is.
#91's UC3 has no issue; it becomes UC-04, and it is where the bundle fits. UC-02 is absent from #91 and
is the only case where the owner's own company is the user; the #81 extension says a retailer "is an
application, not the platform definition". The owner decides whether it is in the roadmap; this record
does not resolve it.

## E. Architecture decision

Keyed to [decision-system v1](../../architecture/decision-system-v1.md) and the
[ontology profile](../../architecture/ontology-profile-v1.md). Upheld: BigQuery before any graph
engine; no default `causes` edge; consequences uncomputed without compatible outputs; code owns time,
identity, permissions and the write; Gemini proposes, the analyst accepts. Revised, two items:

1. **The probe bundle is demoted from "the novelty" to "a backend behind the frozen contract".** The
   contract (artifact keys, request shape, composition table, receipt) stays frozen; the claim in the
   working paper's abstract that the bundle is the new contribution is withdrawn until experiment 3
   shows a gain. The single-render judgment remains the comparator in every evaluation.
2. **The assumption register becomes a product object.** It is populated from the company's outlook
   inputs under the PLEXOS boundary (representation version, field names, units), not from the audit.
   Every A01 to A12 and C01 to C08 entry above has a row; every threshold in
   [`03_ref_regions_thresholds.sql`](../../../scripts/data/sql/03_ref_regions_thresholds.sql) and every
   composer row in [`bundle.py`](../../../src/judgment/bundle.py) is labelled official, analytical or
   exploratory. This is #79 with a different owner: the product, not the audit.

Not changed: no new ontology type until a reviewed intent needs one (C05); CORE-10 (signed-permission
allowlist) precedes any live run against real records; the thinking-level transport gap is a CORE task.

## F. Minimum decisive experiments

Ordered by what they need: nothing, then an owner input, then one live call. Each names the number it
produces and the stop condition.

| # | Experiment | Needs | Number produced | Stop condition |
|---|---|---|---|---|
| 1 | Outage-schedule revision lag. For every 2026 resource with a trip or return advisory, measure the time from advisory posting to the first `ext_rtd_outage_schedules` snapshot that changed. The schedule is the operator's own assumed return time. Known risk: the table is sparse (PEDC rows only in January and June to July 2026; U03 at 0 MW for weeks with no row), so "never changed" and "never existed" must be kept apart; only the first bears on the thesis. | One guarded BigQuery read (orchestrator seat; the owner's word, it is billed). No model. | Distribution of lag in minutes; share of events where a row existed and never changed; share of events with no row at any time | If the median lag is under an hour and coverage is complete, operator-visible outages do not produce stale assumptions; the premise narrows to rules and milestones. If most events have no row, the experiment decides nothing and experiment 2 carries the gate alone |
| 2 | Incidence in the company's outlook. For one PLEXOS run before 2026-09-21 (and, if possible, the last five runs), compare its unit-availability inputs with the advisory feed at run time. | Owner input: the input table of a past run. No model. | Count of inputs stale at run time; the PEDC U2 row's value | If zero inputs were stale across five runs, C01 fails; the product is the register, not the desk |
| 3 | Blind re-labelling. One analyst labels the 25 fixture pairs and the 3 PEDC compiles without seeing the frozen labels; a second person adjudicates disagreements. Then the manual arm of [baseline-protocol v3](../probe-bundle/baseline-protocol.md) on the PEDC case. | Owner input: analyst time (GATE-7 is closed). No model. | Agreement with executor labels; bundle versus single-render against the new gold; missed-material-issue recall and time | If the analyst agrees with the executor on fewer than 20 of 28, the 22/28 figure is void; if manual matches the desk, the AI layer is a convenience |
| 4 | Settlement basis, offline. The compendium holds the Billing and Settlement Manual, Issue 16.0 (register row 10). Read it against [`04_interval_pricing.sql`](../../../scripts/data/sql/04_interval_pricing.sql): is a retailer's exposure the capped median of generator-node LMP, or a load-node price? | Nothing. One document, one SQL file. | A yes, a no, or the clause that says which | A no blocks every UC-02 figure until the right series exists; a yes opens #85 |
| 5 | One live extraction. After CORE-10 and a corpus permission record, run CORP-3 once on the 30 PEMC documents with the decided thinking level, and score citation fidelity against the CORP-0 hand walk. | CORE-10 (transport), a permission record for the corpus bytes, one authorized Vertex call | Share of proposed claims whose quoted passage is verbatim and placed; count of clauses placed at the reserve-market cutoff | If fewer than nine in ten citations are verbatim, extraction is not ready for a rules case; if the clause count stays zero, the register needs first-availability evidence before any case |

The real alternative, per the strategy skill: do nothing new until experiments 1 and 2 return a number.
Both are cheap, neither touches a model, and together they decide whether the desk or the register is the
product. Everything in tier 3 below waits on them.

## G. Estate organization and scoping

### G1. Authority drift (fix in one housekeeping commit, owner's word)

| File | Says | Actual |
|---|---|---|
| [milestones](../milestones.md) | 63 tasks; CORP and ATG pending; GATE-8 open; PERF-0, PERF-5, EXPL-1, EXPL-2, REL-3 open | 79 tasks; all 14 CORP and ATG done and accepted; GATE-8 closed; those five done |
| [current.json](../current.json) | work `performance`, next action starts at PERF-0 | PERF-0 done; the head of the chain is HOST-3 |
| [status](../../status.md) | PERF-0 in review; DOC-1 and DOC-2 pending; "the next deploy raises that to 492" | PERF-0 done; DOC-1 to DOC-4 in progress with reviewer accepts and no owner accept; revision 00014 is live with the corpus and ATG pages |
| [tasks.json](../tasks.json) | POST-4 depends on NUM-3 | NUM-3 is cut, so POST-4 can never become ready |
| [live run record](../grid-desk/live-run-2026-10-14.md) | the analyst's decision at the return cutoff is retain | the [case review](../../cases/pedc-u2-2026-09-21/review.md) records no disposition; the only retain clicks are smoke-test judge flows |

### G2. Orphaned branches (salvage or archive, owner's word)

`task/CORE-5` (+9, holds the recorded live bundle run of a cut task), `task/UI-3` (+21, cut), `task/UI-4`
(+45, cut), `release/poc-2026-10-14` (+21), `origin/docs/current-state-75` (+6, remote only). Thirty local
branches each checked out as a worktree. The CORE-5 run record is evidence worth keeping on `main`.

### G3. Three tiers

**Tier 1, ship.** The submission chain as it stands, nothing added: HOST-3 (ready now) → REL-4 → the owner
opens GATE-5 → REL-5 → REL-6 and REL-7 (owner). One batch deploy before REL-7 carrying the 492-site bake.
Plus the G1 housekeeping. Submission is 2026-10-18; nothing in tiers 2 and 3 enters this chain.

**Tier 2, validate.** Experiments 1 to 4 in order; EVAL-8 (ready; the #73 disagreement); CORE-10 (ready;
replaces the script subclass that #74 flags); the assumption register as a product object (section E).
Output: four numbers and one decision on whether the desk or the register is the product.

**Tier 3, expand, gated on tier 2.** Experiment 5 and the corpus live path; UC-03 as one role; UC-04
sheet and one documented milestone slip; UC-02 only if experiment 4 says yes; ATG parity work stops
until a decision value is measured (the four built ATG capabilities are live; the remaining four reference
areas, Radar, live views, alerts, ask box, are not started and stay that way).

### G4. Issue reconciliation

| Issue | Proposed action (owner files it; nothing edited here) |
|---|---|
| #80 | byte-duplicate of #81; close with a pointer |
| #81 | the case-sheet standard; keep; add UC-04 to its index |
| #82, #84 | UC-01; experiment 2 is #84's first step |
| #83, #85 to #88 | UC-02; experiment 4 is #85's first step; owner decides roadmap membership |
| #89 | UC-03; narrow to one role first; note the ERC 403 and the data-end date |
| #90 | keep as the benchmark; C06 above is its disposition |
| #91 | map UC1 to UC-01, UC2 to UC-03 narrowed, UC3 to UC-04; record that UC-02 is absent |
| #78, #79 | the register, re-owned by the product (section E) |
| #73 | EVAL-8 exists and is ready; link it |
| #74 | CORE-10 exists and is ready; link it |
| #37 to #47 | REL-4's job; do not redo it here |
| #21 to #35 | M3 and M4 epics superseded by tasks.json; close or relabel at REL-4 |
| #48 to #51 | the later-research epic (S1 baseline, adaptation, transfer); #78 cites #49 and #51 as live; they map to POST-3, not to superseded work |
| #41 | CI still does not start; unchanged |

### G5. Scope lines

Superseded 2026-10-16 by [problem-and-thesis.md](problem-and-thesis.md): price forecasting and portfolio
exposure arithmetic are the core (owner: the price outlook defines the core strategy); VAL-2 and LIVE-3 deferred.

In scope for the next build after tier 2: the register, UC-01 on a real forecast vintage, one rules case
for one role. Out of scope until a tier-2 number justifies it: a graph engine, cross-stakeholder overlays,
new ontology types, price forecasting, portfolio exposure arithmetic, the Clef hosting path, the what-if
preview, further Ask the Grid parity, any second data pipeline. Cut stays cut: CORE-5, EVAL-7, UI-3 to
UI-6, NUM-2, NUM-3, CLEF-2, CLEF-3.

## H. Recommendation

Ship tier 1 unchanged. Then run experiments 1 and 2 before any other work; they cost one guarded query and
one owner file, and they decide the product. Demote the bundle, promote the register. Add UC-04 as a sheet,
keep UC-01 as the premise test, take UC-03 one role at a time, and let the owner decide whether the
retailer case is the business. Fix the authority drift in one commit. Say "unverified" on every live
capability until experiment 5 runs.

## Owner decisions (collected)

1. Authorize the one guarded BigQuery read for experiment 1 (billed under the per-query guard).
2. Provide one past PLEXOS run's unit-availability input table for experiment 2 (stays out of Git).
3. Give one analyst half a day for experiment 3, or accept that the 22/28 figure stays self-authored.
4. Decide whether UC-02, the retailer case, is in the platform roadmap or a separate application.
5. Decide UC-04's focus: generation projects, transmission projects, or both (#91's open question).
6. Decide salvage or archive for the five orphaned branches, in particular the CORE-5 run record.
7. Authorize the housekeeping commit for the authority drift in G1.
8. Open GATE-5 when the rights review is done; it is the only closed gate on the submission chain.

## Owner answers (2026-10-16, in session)

| Decision | Answer | Consequence |
|---|---|---|
| 1 BigQuery read for the outage-schedule lag | yes | experiment 1 is authorized; one guarded query, orchestrator seat |
| 2 A past PLEXOS input table | none exists | experiment 2 cannot run backward; the outlook archive is built from now on and scores forward; experiment 1 carries the backward look alone |
| 3 The retailer price case | yes; the WESM price outlook defines the core strategy | UC-02 moves to the center; UC-01, UC-03 and UC-04 become the assumption families of one price outlook; section C's participant-centric reading stands |
| 4 UC-04 focus | both generation and transmission | DOE project lists for both enter the corpus register as sources |
| 5 Orphaned branches | review all | reviewed below; the CORE-5 run record is carried to main; the rest untouched pending the owner's word on deletion |
| 6 Housekeeping commit | yes | done in this session's commit |
| 7 Rights and publication approval | everything | GATE-5 recorded open in tasks.json |

Analyst time is not available; the blind re-labelling in experiment 3 is done by the independent
reviewer model and recorded as a model check, not a human one. No analyst-baseline claim follows.

Branch review (read-only): `task/CORE-5`, 9 ahead and 800 behind, holds the only recorded live run of
the question set (`gemini-3.8-flash`, label `supports` by `earlier_observation` while Q8 said
`challenges`) in `probe-bundle/live-run.md` and `reviews/CORE-5.md`; both carried to main, the code
superseded by CORE-3. `task/UI-3` (+21) and `task/UI-4` (+45): the scenario-difference and evaluation
views, cut on 2026-10-14; archive, no merge. `release/poc-2026-10-14` (+21): merges of GRID-1 to 3 already
on main; a release record, leave. `origin/docs/current-state-75` (+6, remote only): a docs alignment
for closed issue #75, superseded twice; recommend deleting the remote branch on the owner's word.
`task/HOST-3` (+2): active, the next task.

## Handoff

Intent must settle, after decisions 1 to 3: the register's record shape under the PLEXOS boundary, the
query for experiment 1, the blind-labelling protocol as a baseline-protocol v4 amendment, and the CORE-10
packet. Known constraints: no record of a corpus permission; the market data ends 2026-09-29; the ERC site
refuses automated fetches. Exact next action: HOST-3, which is ready, then phase 2 step 1, the settlement basis from the Billing and Settlement Manual.
