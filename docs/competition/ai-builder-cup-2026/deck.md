# InGRID (Grid Nowcast until release 23) - competition deck (twelve slides plus appendix)

**From market signals to trustworthy, traceable decisions.**

Document control. This file is the REL-2 output: the deck text, its speaker notes and the
claim-to-evidence register for the AI Builder Cup 2026 submission. Lane REL, milestone M6,
branch `task/REL-2`, executor seat DeepSeek V4.1 Flash, written 2026-10-12 and reworked
2026-10-13 after its designated review, on the branch rebuilt on the EVAL-3 line. It is
Markdown with speaker notes; the PDF build steps are recorded in
[Appendix C](#appendix-c-pdf-build-steps).
The slide order follows the deck narrative the project's
[story and script](story-and-script.md) owns; this file supplies the evidence and the
per-claim register the story document leaves to REL-2. Slide 1 was replaced on 2026-10-17
(REL-4) to open on the theory-first framing of the
[theoretical foundation](../../architecture/theoretical-foundation.md) and the
[future-of-work case](future-of-work-case.md); slides 2 to 12 are unchanged by that edit, and
its commands and results are in the
[REL-4 record](../../work/entry-framing-2026-10-17/implementation.md). Slides 4 and 10,
slide 11's status bullets, Appendix A, Appendix B (rows 17, 44, 46, 47 rewritten, rows 54 to
57 added, rows 13, 14 and 45 annotated) and Appendix D were rewritten
on 2026-10-18 (POLISH-2, finding F-01 of the
[independent review](../../work/polish-2026-10-18/findings.md)) to the live state; the other
slides are unchanged by that edit.

**How to read this deck.** Every bullet and every sentence in the speaker notes carries one or
more evidence markers in brackets, `[H0]`, `[EVAL]` and so on. The markers are defined in
[Appendix A](#appendix-a-evidence-key). A claim that no artifact on this branch supports is
marked **NOT ESTABLISHED** and is never phrased as a result. [Appendix B](#appendix-b-claim-register)
lists every load-bearing claim with its evidence and its status, so a reviewer can check the
deck against the repository instead of against impressions. [Appendix D](#appendix-d-how-this-deck-was-checked)
records the commands this task ran. Nothing in this deck was measured by this task; every number
is read from the packet named beside it, and the packets record their own runs.

**Scope of the claims.** The deck is frozen at `main` 106bd5e9 on 2026-10-18; slides 4 and
10 and their register rows are matched to the records on that commit. The other slides were
matched to the artifacts on `task/REL-2` at 2026-10-13, after the branch was rebuilt on the
EVAL-3 line, and slide 1 to `main` on 2026-10-17 (REL-4).
The product of record for scope is the [v1 blueprint](../../product/definitive-blueprint-2026-10-04.md)
[BLUE]; this deck describes the artifacts rather than widening that scope. Where a capability
exists on another lane's branch and not here, the deck says what the repository records and
does not link the file. Task states are those in
[PROGRESS.md](../../work/PROGRESS.md) and `docs/work/tasks.json` on this branch.

**Mode labels** follow working paper section 4.2 [WP]: `live_inference`, `stored run`,
`retrospective replay`, `deterministic`, `synthetic_fixture`. A model output is a
*proposal* until an analyst records a disposition; `proposed` is not `accepted`.

---

## Cover and positioning (front matter, not one of the twelve slides)

InGRID - from market signals to trustworthy, traceable decisions [STORY]. Who answers for a
decision made with AI? Trust and traceability are properties of records, not of models [FOW]; the
instance is a change-review desk for power-system outlooks [STORY]. Category:
Future of Work & Enterprise Productivity [STORY]. The category shown by the submission portal
is unverified; the [requirements table](requirements.md) records that as open [REQ].

One-sentence pitch: InGRID connects new grid evidence to the assumptions behind an
analyst's outlook, then makes each retained or revised position traceable and reviewable
[STORY].

**Convergence with OpenGrid (positioning only).** The OpenGrid Foundation, governed at the
Linux Foundation, independently frames grid planning as comparing versioned assumptions
against a common reference: studies tagged to the data and assumptions they used, datasets
issued as immutable citable releases, assumptions publishable while network detail stays with
its owners, and a deterministic engine executing any workflow an agent composes [R30]. Grid
Nowcast converges with that framing and applies it to the near-term evidence loop OpenGrid's
draft does not address - advisories, market data and information cutoffs, reviewed while the
outlook is still live. This is positioning context: there is no dependency, no integration and
no compatibility claim, and the convergence was recorded as a revised assumption in the
[strategy refresh](../../work/strategy-refresh-2026-10-11/strategy.md), not as validation
[STRAT][R30].

**Speaker notes.** Open on the theory, as slide 1 does, then land on the analyst and the decision; never on the model stack. The positioning line above exists so that a judge who knows the Linux Foundation planning
initiative hears the relationship stated accurately: same framing of assumptions and
provenance, different time horizon and different object (a review desk for evidence arriving
now, not a multi-year planning hub whose first tools are expected in 2027) [R30]. Say plainly
that Grid Nowcast is independent of OpenGrid and cites it as convergent public positioning,
not as a partner.

---

## Slide 1 - The foundation: four questions, and the claim that follows

**Slide text**

- Four questions organize the work: what do we know, why, and when should a belief change; given
  uncertainty, what should we do and what is timely information worth; who may propose, accept
  and act; how do outcomes change beliefs, methods and goals [FOUND]. The claim this entry sets out to test, a
  hypothesis until experiment 3 runs: the productivity gain from AI in knowledge work is bounded by
  trust and traceability, and both are properties of records, not of models [FOW].
- A forecast can be mathematically sound and still rely on an assumption that has gone stale
  [STORY].
- The analyst's hard question is not only what changed in the grid, but what that change means
  for the outlook they are responsible for [STORY].
- InGRID is a change-review desk: what changed since the last accepted outlook, which
  assumption it affects, and whether the accepted position should stay or change [AGENTS].
- Observations, attributed claims, accepted assumptions and simulation results are separate
  records; nothing silently becomes truth [AGENTS].
- The AI does the evidence legwork; the analyst keeps acceptance authority; a justified
  no-change is success [STORY][AGENTS].

**Speaker notes.** Open on the theory and land it [FOUND][FOW]. AI-native knowledge work is a
governed loop: changing evidence becomes revisable beliefs, decisions rest on them, and
learning comes from what settles [FOUND]. The four questions above come from established work
and structure that loop: belief revision and the two clocks of time; decision theory's question
of what to do under uncertainty and what timely information is worth; coordination theory's
question of who may propose, accept and act; and organizational learning's question of how
outcomes change beliefs, methods and goals [FOUND]. The claim the rest of the deck sets out to test, stated as a hypothesis until experiment 3 runs: the
productivity gain from AI in knowledge work is bounded by trust and traceability, and both are
properties of records, not of models [FOW]. Then lead with the failure mode a
practitioner recognises: the emotional problem is a stale assumption, not a lack of charts
[STORY]. The number was defensible when it was accepted, the world moved, and nothing in the
desk said so. Then set the boundary that the rest of the deck respects: the tool does not
decide, it makes the change and its consequences for one accepted assumption inspectable, and
it records the analyst's decision either way [AGENTS][WP].

**Evidence.** `[FOUND]` theoretical foundation, sections 1, 2, 3 and 8 (the four questions and the loop). `[FOW]` future-of-work case, sections 1, 2 and 8 (the records claim, a hypothesis until experiment 3). `[STORY]` story and script, positioning and one-sentence pitch.
`[AGENTS]` AGENTS.md, mission and domain invariants. `[WP]` working paper sections 4.1 and 9.

---

## Slide 2 - One analyst, one decision, one reviewable outcome

**Slide text**

- One user (an energy analyst), one decision (retain or revise one accepted assumption), one
  reviewable outcome [STORY].
- Proposal, analyst review, execution approval and execution receipt are distinct records
  [AGENTS].
- A model output is a *proposal*: the saved artifact starts `review_state = 'proposed'`, and
  the accepted value changes only through the review transaction [CORE2][WP].
- Dispositions are retain, revise, reject, defer and investigate, each with a mandatory reason
  and an attributable history entry [W3][H0].
- A retain stores the rationale and preserves the accepted head and value: the no-change path
  is a first-class outcome, not a failure to decide [H0].
- The system does not operate the grid and dispatches nothing [WP].

**Speaker notes.** This is the authority slide. The distinction between a proposal and an
acceptance is a domain invariant in this repository [AGENTS], and it is enforced in data, not
in prose: the judgment artifact's review state is `proposed` until the review transaction
appends a decision, and the receipt is separate from the decision [CORE2][WP]. Mention the
no-change path explicitly - a review desk that only rewards changes is an advocacy tool.

**Evidence.** `[STORY]` positioning, "the hero is the analyst". `[AGENTS]` domain invariants.
`[WP]` working paper 5.8 (review transaction) and 9 (authority boundaries). `[H0]` H0 packet,
acceptance row "No-change / T08". `[W3]` M3 workspace packet, delivered behaviour. `[CORE2]`
probe-bundle implementation packet, S2 section.

---

## Slide 3 - The evidence-to-outlook loop

**Slide text**

- One deterministic compiler produces the context a model may see: access filter, availability
  filter, reviewed identity, context and type checks, relevant passages and series, lineage
  grouping, bounded render, canonical digest [WP].
- Two clocks: the information cutoff (what was knowable) and the review time are always
  separate, and five-minute market resolution does not imply five-minute freshness
  [WP][AGENTS].
- The compiled task is immutable and lists allowed references and explicit omissions; strict
  mode excludes unknown or later availability [WP][H0].
- The probe bundle asks eight typed atomic questions in four perturbed forms each - 32 questions
  in one frozen request. The relation label is composed in code from the modal top answer of
  each question; the table is total and `insufficient` is the fall-through
  [CORE1][REV-CORE-1][INTENT].
- A stability receipt records a flip rate and a noul polarity gap per question; an unstable
  bundle is downgraded to `insufficient` and escalated to Gemini interpretation plus manual
  review [CORE1].
- The analyst then sees the composed label, the rule that fired, the atomic answers, the
  receipt and the referenced passages before recording a disposition [REV-UI-1][WP].

**Speaker notes.** Walk the loop once: source -> compiled task -> bundle -> composed relation
-> analyst disposition -> immutable outlook difference [WP]. The two-clock rule is the part
practitioners test first, so give it a concrete sentence: a report that existed on 2026-09-20
is invisible to a task compiled at a 2026-09-15 cutoff, and the omission is listed rather than
implied [WP][H0]. The composition being in code - not in the model's own confidence - is what
makes the rule that fired inspectable [WP][CORE1].

**Evidence.** `[WP]` working paper 5.1, 4.3, 5.2, 5.3. `[AGENTS]` domain invariants on cutoffs
and identity. `[H0]` H0 packet, acceptance rows for exact evidence, time portions, identity and
determinism. `[CORE1]` probe-bundle packet, "S1 delivered behaviour". `[INTENT]` probe-bundle
intent, contracts for render, composition and receipt. `[REV-UI-1]` UI-1 review record
(designated accept, 2026-10-12).

---

## Slide 4 - Live demonstration - what runs today, and how it is labelled

**Slide text**

- The demonstration is the hosted desk at `https://ingrid-desk.web.app`: Firebase Hosting
  serves the first screen and the grid files and sends every other path to the Cloud Run app
  in `asia-southeast1` [SVC][REQ][REV-HOST-2].
- The first screen a visitor meets is the sign-in screen. The owner keeps the sign-in wall;
  password accounts are made by the team, and the judges' account is to be named in the
  submission form at REL-7 [BOARD][PROG][AUTH].
- The case on screen is the real one: the PEDC Unit 2 trip of 21 September 2026, read from
  the operator's advisories and the capacity register under the signed permission record
  [EVENT][PERM][LIVE-REAL].
- The event page carries the advisory, the retained 83.7 MW value, the desk line, the
  decision form with a reason, and the history of each decision [EVENT][PROG].
- Two recorded Gemini calls on the real case (2026-10-14, Vertex AI `gemini-3.8-flash`,
  `global`): both compiles composed `challenges`; at the return cutoff the scripted reading
  says `supports` and the analyst's recorded decision is retain. The desk kept the
  disagreement [LIVE-REAL].
- One earlier receipt on the labelled synthetic case (`core6-cited-002`): 3.45 s, 1,786 tokens
  (1,474 prompt + 312 candidate), label `challenges`, one citation identical to the immutable
  passage; the owner's semantic review agrees with the label [LIVE][VT][REV-CORE-6].
- A visit is a replay: the site answers from recorded runs and recorded plans; no model call
  runs while a visitor reads the page [PROG][EVENT].
- Not yet recorded: a stranger's walkthrough from source to a saved disposition (HOST-3,
  deferred by the owner 2026-10-17) [PROG][MILES].

**Speaker notes.** Say the label out loud at the start of the recording: this is the hosted
site, the case is real, and every model answer on it is a recorded run [LIVE-REAL][PROG][STORY].
Show the sign-in screen for two seconds and say who may enter; the judges' account is to be
named in the submission form at REL-7 [BOARD][AUTH]. Then run the one straight line: the grid page at 13:40, review
impact, the event page, the judgment card, the return-cutoff disagreement said out loud, retain
with a reason, save, history [EVENT][LIVE-REAL][STORY]. The disagreement is the honesty beat:
the scripted reading and the model differ on the same four passages, both are kept, and the
analyst's decision against the model is recorded [LIVE-REAL]. Do not narrate a live model call
during the visit; none runs on the event page [PROG]. The live release is batch release 23: one deployer, one
complete build, one stamp on Hosting, the first screen and Cloud Run; the command bar answers a
signed-in visitor live on Vertex AI since release 23, labelled live, and the presenter reads figures
off its table because the citation mark sits flush after each figure [PROG]; the submission
identifiers are those of the last release before the portal submission [PROG][BOARD].

**Evidence.** `[SVC]` the one services table. `[REQ]` requirements table, rows E5 and E6.
`[REV-HOST-2]` HOST-2 review record (designated accept, 2026-10-14; 24 of 24 Hosting checks).
`[BOARD]` coordination board, rows R11 and R12. `[PROG]` PROGRESS log, the 'Batch release' rows
(by title and date; the release 19, 20, 21 and 22 rows among them). `[AUTH]` the sign-in module's docstring. `[EVENT]` GRID-3 event
packet. `[PERM]` the signed permission record. `[LIVE-REAL]` the live run record on the real
case, 2026-10-14. `[LIVE]` CORE-6 section of the m3-live-gemini packet. `[VT]` CORE-7 packet.
`[REV-CORE-6]` CORE-6 review record. `[MILES]` milestones, M5 and M6.

---

## Slide 5 - The model division of labor, and Gemini's substantive role

**Slide text**

- Gemini does the evidence work around the judgment: cited claim extraction from advisory text,
  competing interpretations and unknowns, the review brief, and escalation when a bundle is
  `insufficient` or unstable [WP].
- Its output is validated against the immutable task context - one label, one explanation,
  exact whole-passage citations, bounded alternatives - and it never composes the relation
  label from its own confidence and cannot accept an assumption [GEM][WP].
- The live receipt demonstrates that path end to end, including citation validation against the
  immutable passage; later replays of the same receipt are labelled replays, not new inference
  [LIVE][REV-CORE-6].
- The decision-model call goes through one port that speaks the System One request and response
  shape, with a labelled fixture backend in tests and, as separate slices, a Gemini
  structured-output emulation whose response schema carries one property per rendered question,
  and an HTTP client that posts the rendered request to a configured origin, one call, no
  default URL [INTENT][CORE3].
- The numerical view is built as two BigQuery `AI.FORECAST` statements with
  `model => 'TimesFM 3.0'` over one identical history and two future-covariate paths, labelled
  *Preview, directional*, or the explicit *uncomputed* label; the statement pair and its parser
  are tested offline through an injected transport, and no BigQuery query has run
  [WHATIF][NUM1][WP].
- Semantic scores never become event probabilities, and a semantic score never becomes a
  scenario consequence [WP][AGENTS].
- The proof is the complete review journey, not the number of models in the diagram [STORY].

**Speaker notes.** Answer "where is the AI, substantively" with two artifacts: the live cited
judgment, and the escalation path that hands an unstable or insufficient bundle to Gemini for
interpretation [LIVE][WP]. Then be strict about what the other models are for. The decision
model answers typed atomic questions and its probabilities are stored raw and used only to
compose a relation label [INTENT][CORE1]. TimesFM through BigQuery is a licensed numerical view
of consequences, Preview and directional, and it starts uncomputed [WHATIF][R30]. Each
component has a declared task; the baselines that would judge them are designed but not yet run
[PROTO].

**Evidence.** `[WP]` working paper 5.7, 5.6, 6. `[LIVE]` CORE-6 packet. `[REV-CORE-6]` CORE-6
review record. `[INTENT]` probe-bundle intent, "Backends in this intent". `[CORE3]` probe-bundle
packet, S3 section; `[REV-CORE-3]` CORE-3 review record (designated re-review, findings none).
`[WHATIF]` NUM-0 intent, outcome and scope. `[NUM1]` NUM-1 packet, statement pair, parser and
acceptance table. `[CORE1]` probe-bundle packet, S1. `[AGENTS]` domain invariants. `[R30]`
research 30, sections 2.2, 4.1, 4.2. `[STORY]` deck narrative item 5. `[PROTO]` baseline
protocol.

---

## Slide 6 - Ontology-to-task compilation and dependency tracing

**Slide text**

- Records keep exact UTF-8 evidence with half-open passages, typed entity and model bindings,
  signed decimal quantities and explicit time metadata; the eleven `h0.v1` record kinds
  round-trip [H0].
- Compilation applies reviewed identity, availability at the cutoff and lineage grouping before
  a bounded render and a canonical digest; the compiled task is immutable and its digest is
  reproducible across runs [H0][FIX].
- The probe artifact is additive to that contract: exact payload and metadata keys, identity
  `probe:<digest(actor, key)>`, and an `output_digest` over the composed result; the existing
  record kinds are untouched [INTENT][CORE2].
- Replay and conflict are explicit: the same key on the same task returns the saved artifact
  with no backend call; the same key on a different task is a conflict and writes nothing
  [CORE2].
- Cutoff pairing is derived, never stored: the T0 context contains only what was knowable then,
  the T1 context adds the new passages, and the pair reports which atomic answers changed and
  which passages are new; the pair endpoint is read-only and refuses mismatched assumptions,
  snapshots and cutoff order with typed codes [WP][INTENT][CORE4].
- The dependency path runs source -> claim -> assumption -> model input -> outlook, and an
  unresolved or ambiguous mapping blocks a dependent revision instead of guessing [H0][STORY].

**Speaker notes.** This is the "what is actually new" slide; keep it concrete. The compiler is
deterministic and its output is a digest-bound artifact, so two runs over the same inputs give
the same task [H0][CORE1]. The probe bundle is a second renderer over the same compiled task,
which is why task identity and digests did not change when the bundle was added [WP][INTENT].
Dependency tracing is where a change becomes a consequence: the mapped unit, the assumption,
the input field and the outlook are linked, and an ambiguous mapping blocks rather than
guesses [H0][STORY].

**Evidence.** `[H0]` H0 packet, changes and acceptance rows. `[FIX]` EVAL-1 packet (digests
produced by running the repository code, never by hand). `[INTENT]` probe-bundle intent,
"Record" and "Cutoff pairing". `[CORE2]` S2 implementation section, acceptance table. `[CORE4]`
S4 implementation section, pair contract and acceptance table; `[REV-CORE-4]` CORE-4 review
record (designated accept). `[WP]` working paper 5.1 and 5.4. `[STORY]` deck narrative item 6.

---

## Slide 7 - What the experiments establish - and do not

**Slide text**

- Fixture set: 25 evidence-assumption pairs over the eight required edge classes, 28 compiles,
  with the annotation policy and every label frozen before any backend run; policy digest
  `0c2f32ea...5483c`, fixture digest `ce6cddf0...a979a996` [FIX].
- A1, bundle against single render: 22/28 against 22/28 overall, a tie; the bundle abstains on
  4 compiles (1 of them correctly, on the frozen `insufficient`) and reaches 21/24 selective
  accuracy against 22/28 when only answered cases count in it; at the 24 compiles all four
  conditions answer, 21/24 against 19/24 [EVAL].
- A2, the sufficiency gate: its only effect on this set is one compile, and that compile is on
  the calibration split, so the test split is identical with and without the gate [EVAL].
- A3, the stability downgrade: **NOT ESTABLISHED**. Every flip rate is 0 by construction on a
  scripted backend, the downgrade never fires, and the two conditions are byte-equal; the
  report records `identifiable: false` and the deck makes no claim about predictive value
  [EVAL].
- No unsupported revisions occur under any condition. The bundle's two missed challenges
  (`pb-er-1/t1`, `pb-er-2/t1`) are definite non-challenge answers where the frozen label is
  `challenges` - `mixed`, the v5 direction gate surfacing the disagreement with the modal Q8,
  and `supports` through the gated earlier-observation row - and the widened availability-kind
  row adds one more wrong definite answer, `pb-tc-3/t1` composing `challenges` where the frozen
  label is `mixed`; the owner's Round 9 ruling settles that row in bundle v5, and EVAL-3
  withdrew its own restriction proposal [EVAL][REV-EVAL-3].
- The bundle's four abstentions are a separate story: three are deliberate and conservative
  (lineage without a prior label; two identity cases) and one is correct on the frozen
  `insufficient`, with `pb-cl-3/t1` the abstention on a challenge [EVAL].
- Stated limits: the backend is a script replaying frozen annotations, not a model; the set is
  25 project-authored pairs; the thresholds are untuned; and none of this is analyst validation
  [EVAL].
- The real case is a skeleton: 16 chronology items, every one flagged secondary or unverified,
  no source registered and first availability null throughout [CASE].

**Speaker notes.** Give the honest shape first: on this fixture set the composed bundle ties
the single-render baseline on overall accuracy and is more selective at matched coverage, and
it is right on 7 of the 8 test-split compiles it answers [EVAL]. Then say what the run cannot
show: the backend is a script, the gate's effect is one calibration-split compile, and A3 is
not identified at all [EVAL]. A judge who hears "we measured our own rule and here is where it
fails" trusts the rest of the deck more, not less [SCORE]. The Visayas pack is a skeleton with
nothing registered [CASE].

**Evidence.** `[FIX]` EVAL-1 packet, summary and digests. `[EVAL]` EVAL-3 ablation report,
sections 2 to 5 (read from the report file at its recorded digest). `[CASE]` Visayas pack
record. `[SCORE]` scorecard, "Reasons, not numerology" and evidence rows.

---

## Slide 8 - Safety, time, identity and approval boundaries

**Slide text**

- Time: evidence later than the cutoff is excluded by construction and the omission is
  explicit in the compiled task [H0][WP].
- Identity and authority: trusted membership contexts and capability checks; client-supplied
  actor fields are rejected; source text cannot grant authority [H0][H1].
- Access: a revoked cited source denies reading the saved artifact - 404 through the API -
  including an artifact that inherited a prior label through lineage [CORE2].
- Guards run before any model call: blocked, stale and other-actor tasks never reach the
  backend, and an invalid model response writes nothing [CORE2].
- Failures are typed and reduce the claim: `MODEL_DISABLED`, `MODEL_BUSY`,
  `MODEL_INVALID_RESPONSE`, `MODEL_UNAVAILABLE`; a backend's own error text is never echoed
  [INTENT][CORE2].
- Modes are labelled truthfully in every view, and Gemini's probabilities are recorded as
  verbalized and uncalibrated [WP][INTENT].
- Private data and credentials stay out of Git, and the live receipt lives in an ignored local
  directory [AGENTS][LIVE].

**Speaker notes.** Three boundaries to name: the cutoff boundary (later evidence cannot change
an earlier decision), the authority boundary (routing and acceptance stay in code and in the
analyst's transaction, and untrusted text cannot grant access) [WP][H1], and the failure
boundary (a model that is absent, busy, malformed or unstable reduces the result to an
explicit abstention or escalation instead of a nicer story) [CORE2][SCORE]. The revocation and
idempotency behaviours are pinned by tests named in the CORE-2 packet, including the emulator
read-back after a restart [CORE2].

**Evidence.** `[H0]` H0 packet, authority and time rows. `[WP]` working paper 4.2, 5.1, 9.
`[H1]` H1 self-review, authority and receipt paragraphs. `[CORE2]` S2 acceptance table and its
supporting checks. `[INTENT]` probe-bundle intent, failure behaviour and metadata. `[AGENTS]`
domain invariants. `[LIVE]` CORE-6 packet, credential handling. `[SCORE]` scorecard, "a model
failure should reduce the relevant claim, not be hidden".

---

## Slide 9 - User value and the pilot measurement plan

**Slide text**

- The value offered is a defensible disposition: what changed, which assumption it affects, and
  why the accepted position should or should not move [STORY].
- The comparison is designed before any session runs: condition A (manual) against condition B
  (assisted), with one-factor matching, a fixed evidence budget (E0 set, at most 3 logged
  additions, 60-minute cap), randomization, sealing and washout [PROTO].
- Metrics M1 to M5 are exactly the five phrases of blueprint section 9, with counting rules: M1
  missed material issues (rework category 1 only); M2 unsupported proposals (category 3); M3
  time to a defensible disposition under one rule, with rework time inside the clock and
  reviewer time excluded, reported `not_reached` with its components when no disposition is
  ever adjudged defensible; M4 reviewer rework (distinct defects, round trips, reviewer time);
  M5 traceability (share of material assertions with an exact resolvable citation, citations
  outside the permitted set or after the cutoff, and identity defects) [PROTO].
- Rework category 2's two halves - key items asserted in the wrong direction, and non-key items
  asserted as material - are supporting counts that are never merged into M1 or M2, and
  abstention is reported as a count, not a rate [PROTO].
- Status: **NOT ESTABLISHED** - no analyst session has run. The session is EVAL-7, gated by
  GATE-7 (analyst time), closed at this commit; the protocol freeze is attested [PROG][PROTO].
- Not claimed: adoption, prevented blackouts, saved money, reduced emissions or forecast
  skill; wider resilience and commercial claims are a future validation agenda [WP][SCORE].

**Speaker notes.** Be explicit that the pilot is a protocol, not a result, and describe what
the session will and will not measure [PROTO]. The two things a judge should take away: the
comparison is matched and the rework time is inside the clock, so the measure is not flattering
by construction; and the metric that matters most - missed key issues - is counted separately
from over-assertion, because a tool that says "insufficient" too often must be visible as such
[PROTO][SCORE].

**Evidence.** `[STORY]` positioning and deck narrative item 9. `[PROTO]` EVAL-6 baseline
protocol v3, sections 4 to 8 and the acceptance table. `[PROG]` PROGRESS gates table (GATE-7
closed) and task table (EVAL-7 pending). `[WP]` working paper 6, metrics and the list of things
the project will not claim. `[SCORE]` scorecard, impact reasoning.

---

## Slide 10 - Where it runs: the services table

**Slide text**

- The table below is the project's one services table; START-HERE, the explainer and the
  export README are to carry the same rows. State words: running, ran once, built (not run live),
  set up (no run record), designed [SVC].

| Service | What it does here | State | Evidence |
|---|---|---|---|
| Firebase Hosting | Serves the first screen and the grid files. Sends every other path to Cloud Run. | running | [PROG][REV-HOST-2] |
| Cloud Run (asia-southeast1) | The app server: visitor copies, decisions, the ask service, the command bar search and answers, alerts, journal and book pages. | running | [PROG][REV-HOST-2] |
| Artifact Registry | Holds each release image. | running | [PROG] |
| Firestore | Each visitor's copy of the case and decisions; the alerts, ask and journal data. | running | [REV-HOST-2][PROG] |
| Firebase Authentication | Anonymous visitor identity; sign-in for the editors; the sign-in screen. | running | [REV-HOST-2][PROG] |
| Vertex AI Gemini | Eight fixed questions on one evidence and assumption pair; the planner; cited extraction. | question set ran once on the real case (2026-10-14, two calls at two cutoffs) and once on the synthetic case (2026-10-11); planner and extraction built, not run live | [LIVE-REAL][LIVE][PROG] |
| BigQuery | The company copy. Read when the grid files are built and by the alerts page. | ran at each build; alerts read built, no run record | [PROG][ALERTS] |
| Cloud Storage | The company copy and the anonymised portfolio draft. | data location | [PERM] |
| Secret Manager | The mail password and the search key for the alerts. | set up, no run record | [ALERTS] |
| Cloud Scheduler | The automatic alerts check when new data lands. | built, no run record | [ALERTS] |
| Cloud Build | Ran the hosting checks once (2026-10-14). Not in the deploy path. | ran once | [REV-HOST-2] |

- Latest release row: batch release 25 from `main` c140f7ec (the live trace stream and the
  desk fixes, on the release 23 bake of the platform-polish batch and the InGRID name), one
  deployer, one complete build: a one-year bake (361 days, 2025-10-18 to 2026-10-14; 3,394
  outages read from BigQuery; saved alert material baked in), the full suite with the browser
  on the batch tree (`Ran 3760`, OK, skipped 69), Cloud Run revision `grid-nowcast-00047-lnt` (platform
  digest `sha256:a7f88093`), one live build stamp `10c1942669d71a9b` read back on Hosting, the
  first screen and Cloud Run `/health`; `DESK_GEMINI=1` on Cloud Run; rollback
  `grid-nowcast-00046-vl5` recorded in the same row [PROG][BOARD].
- The submission identifiers are those of the last release before the portal submission;
  board row R12 (one deployer, one complete build) is done with release 22 and releases 23, 24
  and 25 followed the same way (board rows R14 to R16) [BOARD][PROG].
- Still open: the `roles/firebaseauth.admin` grant for the session cookie path; the ask
  service's recorded plan sets exist only for the ask page and the synthetic event, so every
  other page's recorded answer file is a 404 (live since batch release 22, 2026-10-18: the
  command bar of GitHub PR #102 replaces the floating dock panel and reads the same plan
  sets; no Gemini call has run through the bar); the stranger's walkthrough (HOST-3, deferred by the owner
  2026-10-17) [PROG][MILES].

**Speaker notes.** Say what runs and what has only run once, in the table's own state words
[SVC]. Five services carry the live site: Hosting, Cloud Run, Artifact Registry, Firestore and
Firebase Authentication [SVC][REV-HOST-2]. Gemini ran once on the real case (2026-10-14, two calls at two cutoffs) and the site
replays that run; the planner and the extraction are built and have not run live [LIVE-REAL][PROG].
The competition requires a working deployed link as a separate eligibility item; the link is
live, and the judges' sign-in is to be named in the submission form at REL-7 [REQ][AUTH]. Name
release 23 as the live release and say that the submission identifiers are those of the last
release before the portal submission [PROG][BOARD].

**Evidence.** `[SVC]` the one services table. `[PROG]` PROGRESS log, the 'Batch release' rows (by title and date).
`[REV-HOST-2]` HOST-2 review record. `[LIVE-REAL]` live run record on the real case.
`[LIVE]` CORE-6 packet. `[ALERTS]` the alerts contract. `[PERM]` the signed permission record.
`[BOARD]` coordination board, row R12. `[REQ]` requirements table, rows E5 and E6. `[MILES]`
milestones.

---

## Slide 11 - Delivery status, near-term scope and research frontier

**Slide text**

- Delivered and reviewed on this line: the H0 review core; the H1 local API and persistence;
  the connected local workspace; the bounded Vertex and Developer transport; the probe-bundle
  renderer, composer and receipt; the System One port with its additive record, repository and
  API (designated accept recorded); the Gemini structured-output emulation and HTTP client
  (designated accept recorded); the cutoff-pairing backend and route (designated accept
  recorded); the export audit and provenance log (designated accept recorded); the labelled
  fixture set; the ablation report (reworked after its designated review; re-review
  outstanding); the manual-baseline protocol; the Visayas pack skeleton; the what-if statement
  builder (designated accept recorded); and the what-if and hosting intents
  [PROG][MILES][STATUS][REV-CORE-2][REV-CORE-3][REV-CORE-4][NUM1][REV-REL-1][REV-EVAL-3].
- Since the REL-2 text (updated 2026-10-18): the pair view (UI-2), the container and the
  Cloud Run deploy (HOST-1, HOST-2, HOST-4, HOST-5) and the shot list (REL-3) are done; the
  scenario and evaluation views (UI-3, UI-4), the browser check (UI-5) and the BigQuery
  what-if execution (NUM-2, NUM-3) are cut; the stranger's walkthrough (HOST-3) is deferred by
  the owner 2026-10-17; pending: the public export (REL-5), the video (REL-6) and the portal
  submission (REL-7) [PROG][MILES].
- Known limit of the live release: the ask service's recorded plan sets (built as the dock,
  DOCK-1 to DOCK-5) exist only for the ask page and the synthetic event, so every other
  page's recorded answer file is a 404; recorded plans per page are the open gap. Live since
  batch release 22 (2026-10-18), the command bar of GitHub PR #102 replaces the floating dock
  panel on every page but the ask page; it reads the same plan sets and no Gemini call has run
  through it [PROG].
- M3 live evidence exists as one accepted cited Gemini receipt on the synthetic case and two
  recorded calls on the real case [REV-CORE-6][LIVE-REAL]; M4 is closed (the PEDC real case on
  the real readers); M5 is open with the hosted site live and the walkthrough deferred; M6 is
  open, with the export, the video and the portal receipt as the work in it [MILES][PROG].
- Frontier: an adaptation study with permission and lineage rules, and an open planning-hub
  alignment note carrying no compatibility claim [MILES].
- Open questions this deck does not answer: decision-model memory and latency on a 24 GB GPU
  under quantization; whether Cloud Run GPU hosting of a third-party open model satisfies the
  competition's Google-stack rule; the first availability and licence of the operator
  statements behind the Visayas episode; the official closing clock and time zone [R30].

**Speaker notes.** Read the status plainly and let the reviewer check each line against
PROGRESS and tasks.json [PROG]. Say the recorded-plan gap before a judge finds it: on every page but
the ask page and the synthetic event, the ask service (the command bar, live since batch release 22,
2026-10-18, GitHub PR #102; the floating dock panel before it) has no recorded plan to answer from [PROG]. The point of this slide in a competition deck is not modesty; it is that every
forward item has a named task, a named artifact and a named gate, so "near-term scope" is a
plan a judge can hold the team to on 10-17 [MILES].

**Evidence.** `[PROG]` PROGRESS task table, gates and log. `[MILES]` milestones, lane table,
M3 to M8 exit evidence and cut order. `[REV-CORE-6]` CORE-6 review record. `[REV-CORE-2]`,
`[REV-CORE-3]`, `[REV-CORE-4]`, `[NUM1]` and `[REV-REL-1]` the CORE-2, CORE-3, CORE-4, NUM-1 and
REL-1 review records; `[REV-EVAL-3]` the EVAL-3 record whose rework the ablation-report note
reflects. `[LIVE-REAL]` the live run record on the real case. `[R30]` research 30, open
questions.

---

## Slide 12 - Why this is not a dashboard or a PDF chatbot

**Slide text**

- "Why not a dashboard?" A dashboard shows conditions; this preserves the evidence-to-decision
  history and identifies which accepted assumption needs review [SCORE].
- "Why not chat with PDFs?" Chat retrieves text; this binds answers to reviewed identity,
  known-then versions, model inputs and explicit acceptance transitions [SCORE].
- "Why so many models?" They answer different questions, and each must beat or complement a
  baseline; the workflow stays usable when a model is absent, because the sufficiency gate and
  the stability receipt are computed in code and do not depend on model calibration
  [SCORE][STRAT].
- "What is actually new?" The compiler and the dependency-aware review loop. The evidence
  offered is a test suite and a measured ablation, not a first-ever claim [SCORE][EVAL].
- Nothing here is offered as scientific novelty; the claim is that a known set of methods is
  assembled into an inspectable review transaction with measured behaviour [SCORE].

**Speaker notes.** Rehearse these four answers as answers to questions, not as a manifesto
[SCORE]. The strongest evidence in the room is the ablation table on slide 7 and the refusal
paths on slide 8: both are things a dashboard or a chat interface would have to invent
[EVAL][CORE2].

**Evidence.** `[SCORE]` scorecard, "Judge objections to rehearse" and "Reasons, not
numerology". `[STRAT]` strategy refresh, why the bundle is the novelty and its reversibility.
`[EVAL]` EVAL-3 report. `[CORE2]` CORE-2 acceptance table.

---

## Appendix A: Evidence key

Relative paths are from this file. Review records are written by the reviewer role, never by
the author of the change ([review and feedback](../../engineering/review-and-feedback.md)).

| ID | Source | What it establishes here |
|---|---|---|
| AGENTS | [AGENTS.md](../../../AGENTS.md) | mission, authority chain, domain invariants, roles |
| WP | [working paper](../../product/working-paper-2026-10-11.md) | method definitions: sections 4 to 6, 8, 9 |
| BLUE | [v1 blueprint](../../product/definitive-blueprint-2026-10-04.md) | product scope of record |
| STRAT | [strategy refresh](../../work/strategy-refresh-2026-10-11/strategy.md) | selected direction, OpenGrid positioning row, cut order |
| FOUND | [theoretical foundation](../../architecture/theoretical-foundation.md) | the four questions, the governed loop and the disciplines behind each; sections 1 to 3 and 8 |
| FOW | [future of work case](future-of-work-case.md) | the general claim and its evidence grades, the seven records, the domain instance; sections 1 and 2 |
| H0 | [H0 packet](../../work/h0-review-case/implementation.md) | offline review core, acceptance rows |
| H1 | [H1 self-review](../../work/h1-api-persistence/review.md) | local API, identity, transactional persistence |
| W3 | [M3 workspace packet](../../work/m3-workspace/implementation.md) | local workspace, browser walkthrough, screenshots |
| GEM | [M3 judgment packet](../../work/m3-gemini/implementation.md) | the cited judgment boundary |
| VT | [CORE-7 packet](../../work/vertex-transport/implementation.md) | Developer and Vertex transport rules and receipts |
| LIVE | [CORE-6 packet](../../work/m3-live-gemini/implementation.md) | the live cited Gemini receipt and the owner's semantic review |
| INTENT | [probe-bundle intent](../../work/probe-bundle/intent.md) | frozen payload, metadata, port, composition, routes, failure codes |
| CORE1 | [CORE-1 packet](../../work/probe-bundle/implementation.md) | S1 render, composition, receipt and their tests |
| CORE2 | [CORE-2 packet](../../work/probe-bundle/implementation.md) | S2 port, record, repository, API and their tests |
| CORE3 | [CORE-3 packet](../../work/probe-bundle/implementation.md) | S3 Gemini emulation, HTTP client, runner and their tests |
| CORE4 | [CORE-4 packet](../../work/probe-bundle/implementation.md) | S4 cutoff-pairing backend, refusals, route and tests |
| FIX | [EVAL-1 packet](../../work/probe-bundle/fixtures.md) | fixture set, annotation policy, digests |
| EVAL | [EVAL-3 report](../../work/probe-bundle/evaluation.md) | A1 to A3 numbers and limits |
| PROTO | [EVAL-6 protocol](../../work/probe-bundle/baseline-protocol.md) | manual-baseline design and metrics M1 to M5 |
| CASE | [Visayas pack record](../../cases/visayas-2026-09/packet.md) | case skeleton status |
| WHATIF | [NUM-0 intent](../../work/whatif/intent.md) | what-if contract and labels |
| NUM1 | [NUM-1 packet](../../work/reviews/NUM-1.md) | what-if statement pair, labels, parser and designated accept |
| HOST | [HOST-0 intent](../../work/hosting/intent.md) | container, demo mode, hosted assembly |
| STATUS | [status](../../status.md) | what exists, what is missing |
| PROG | [PROGRESS](../../work/PROGRESS.md) | task states, gate states, log |
| MILES | [milestones](../../work/milestones.md) | lanes, milestones, exit evidence, cut order |
| SCORE | [scorecard](scorecard.md) | diagnostic scores, reasons, judge objections |
| STORY | [story and script](story-and-script.md) | positioning, pitch, demo script, deck narrative |
| REQ | [requirements](requirements.md) | competition requirements E1 to E11 |
| CHECK | [submission checklist](submission-checklist.md) | release gate rows and allowlist |
| R30 | [research 30](../../research/30-decision-models-and-energy-2026-10-11.md) | external evidence, OpenGrid and Ask The Grid, competition check |
| REGISTER | [input register](../../work/input-register.md) | gated owner inputs |
| REV-CORE-1 | [review record](../../work/reviews/CORE-1.md) | CORE-1 verdict and findings |
| REV-CORE-2 | [review record](../../work/reviews/CORE-2.md) | CORE-2 designated accept of rework 5 |
| REV-CORE-3 | [review record](../../work/reviews/CORE-3.md) | CORE-3 designated re-review, findings none |
| REV-CORE-4 | [review record](../../work/reviews/CORE-4.md) | CORE-4 designated accept, pair contract |
| REV-CORE-6 | [review record](../../work/reviews/CORE-6.md) | CORE-6 designated accept, M3 live gate met |
| REV-UI-1 | [review record](../../work/reviews/UI-1.md) | UI-1 designated accept, browser walkthrough |
| REV-REL-1 | [review record](../../work/reviews/REL-1.md) | REL-1 designated accept, export audit |
| REV-EVAL-3 | [review record](../../work/reviews/EVAL-3.md) | EVAL-3 designated review, rework and the withdrawn row proposal |
| REV-HOST-2 | [review record](../../work/reviews/HOST-2.md) | HOST-2 designated accept (2026-10-14): Cloud Run, Firebase Authentication, Firestore; 24 of 24 Hosting checks run from Cloud Build |
| LIVE-REAL | [live run record](../../work/grid-desk/live-run-2026-10-14.md) | the two recorded Gemini calls on the real PEDC case, 2026-10-14, and the return-cutoff disagreement |
| EVENT | [GRID-3 event packet](../../work/grid-desk/event.md) | the hosted event page: the real case, the decision form, the receipt and the history |
| SVC | [services table](../../work/polish-2026-10-18/services-table.md) | the one services table and its state words |
| BOARD | [coordination board](../../work/coordination/board.md) | rows R11 (the owner keeps the sign-in wall) and R12 (one deployer, one submission deploy) |
| AUTH | [sign-in module](../../../src/alerts/auth.py) | who is signed in; password accounts made by the team, the judges' account named in the submission form |
| PERM | [permission record](../../work/permissions/2026-10-13-wesm-company-copy.md) | the signed permission for the company copy |
| ALERTS | [alerts contract](../../work/alerts-portfolio-2026-10-17/contract.md) | Secret Manager, Cloud Scheduler and the alerts page's BigQuery read |

Review records for the other accepted tasks (CORE-7, EVAL-1, EVAL-2, EVAL-4, EVAL-6, HOST-0,
NUM-0) are under [docs/work/reviews/](../../work/reviews/) and are the authority for those
verdicts. A verdict in a review record is not a live product test and not a judge score
[SCORE].

## Appendix B: Claim register

Status values: **E** established (a packet, receipt or review record on this branch supports
it); **P** partial (supported for a labelled subset only - synthetic, local, or one split);
**N** not established (no artifact supports it; the deck says so); **F** forward-looking (an
intent or plan, never a result). A row with **N** or **F** must not be narrated in the present
tense in the video or the PDF.

| # | Claim | Slide | Evidence | Status |
|---|---|---|---|---|
| 1 | The failure mode is a stale assumption, not a lack of charts | 1 | STORY positioning | E |
| 2 | InGRID is a change-review desk for one analyst's outlook | 1 | AGENTS, STORY | E |
| 3 | Observations, claims, assumptions and simulation results are separate records | 1 | AGENTS | E |
| 4 | Model output starts as a proposal; only the review transaction changes an accepted value | 2 | CORE2, WP 5.8, AGENTS | E |
| 5 | Dispositions are retain, revise, reject, defer, investigate with a mandatory reason | 2 | W3, H0 | E |
| 6 | A retain preserves the accepted head and records an attributable no-change | 2 | H0 | E |
| 7 | The system does not operate the grid or dispatch | 2 | WP 9 | E |
| 8 | The compiler order and its filters are as stated | 3 | WP 5.1, H0 | E |
| 9 | Information cutoff and review time are separate; resolution is not freshness | 3 | WP 4.3, AGENTS | E |
| 10 | The compiled task is immutable, lists omissions, and excludes later availability | 3 | WP 5.1, H0 | E |
| 11 | Eight typed questions in four forms give 32 questions in one request; composition is in code | 3 | CORE1, INTENT | E |
| 12 | The receipt records flip rate and polarity gap and downgrades an unstable bundle | 3 | CORE1 | E |
| 13 | The workspace browser walkthrough passed at 390/768/1440 px with the named behaviours | 4 (REL-2 text; not on the slide since 2026-10-18) | W3 | E |
| 14 | The probe view renders label, rule, atomic answers, receipt, escalation and passages | 4 (REL-2 text; not on the slide since 2026-10-18) | REV-UI-1 | E |
| 15 | Live Gemini judgment: Vertex AI, `gemini-3.8-flash`, 3.45 s, 1,786 tokens, label `challenges`, citation equals the immutable passage | 4 | LIVE, REV-CORE-6 | E |
| 16 | The owner's semantic review agrees with the label on the synthetic case | 4 | LIVE, REV-CORE-6 | E |
| 17 | A hosted URL exists: `https://ingrid-desk.web.app`, Firebase Hosting serving the first screen and sending every other path to Cloud Run (rewritten 2026-10-18; the REL-2 row said none existed) | 4, 10 | PROG the 'Batch release' rows, REV-HOST-2, REQ E6 | E |
| 18 | Gemini's role and validation bounds are as stated | 5 | WP 5.7 | E |
| 19 | The System One port, its fixture backend, the Gemini emulation and the HTTP client all exist | 5 | INTENT, CORE2, CORE3 | E |
| 20 | The what-if statement pair over identical history, with Preview, directional and uncomputed labels, is built and tested offline; no query has run | 5 | WHATIF, NUM1, WP 5.6 | P |
| 21 | Semantic scores are never event probabilities | 5, 8 | WP 6, AGENTS | E |
| 22 | Eleven `h0.v1` record kinds round-trip; evidence keeps exact bytes and half-open passages | 6 | H0 | E |
| 23 | The probe artifact is additive with exact payload and metadata keys and a digest identity | 6 | INTENT, CORE2 | E |
| 24 | Replay returns the saved artifact without a backend call; a foreign task under the same key conflicts | 6 | CORE2 | E |
| 25 | Cutoff pairing is derived, not stored: the pair reports the changed answers and new passages, and T0 sees only what was knowable then | 6 | WP 5.4, INTENT, CORE4 | E |
| 26 | An ambiguous mapping blocks a dependent revision | 6 | H0, STORY | E |
| 27 | The fixture set is 25 pairs / 28 compiles with policy digest `0c2f32ea...5483c` | 7 | FIX | E |
| 28 | A1: 22/28 against 22/28, a tie; 4 abstentions (1 correct); selective 21/24 against 22/28 (answered cases only); 21/24 against 19/24 at matched coverage | 7 | EVAL | P |
| 29 | A2: the gate's only effect is one calibration-split compile | 7 | EVAL | P |
| 30 | A3 is not identified; all flip rates are 0 by construction | 7 | EVAL | N |
| 31 | No unsupported revisions under any condition; the missed challenges are definite non-challenge answers on frozen `challenges` compiles (`mixed` through the v5 direction gate, `supports` through the gated row), the widened availability-kind row adds one wrong definite answer, and the abstentions are separate | 7 | EVAL | P |
| 32 | The contestable v4 row is settled by bundle v5 and the owner's Round 9 ruling; EVAL-3's own restriction proposal is withdrawn | 7 | EVAL, REV-EVAL-3 | E |
| 33 | Fixture results are not analyst validation and the backend is a script | 7 | EVAL | E |
| 34 | The Visayas pack is a skeleton with nothing registered and first availability null | 7 | CASE | E |
| 35 | Later-than-cutoff evidence is excluded and the omission is explicit | 8 | H0, WP 5.1 | E |
| 36 | Trusted membership and capability checks hold; client actor fields are rejected | 8 | H0, H1 | E |
| 37 | A revoked cited source denies reading the saved artifact, including inherited lineage | 8 | CORE2 | E |
| 38 | Blocked, stale and other-actor tasks never reach the backend; invalid responses write nothing | 8 | CORE2 | E |
| 39 | Failure codes are typed and backend error text is never echoed | 8 | INTENT, CORE2 | E |
| 40 | Modes are labelled truthfully; Gemini probabilities are verbalized and uncalibrated | 8 | WP 4.2, INTENT | E |
| 41 | The manual-versus-assisted comparison, matching, budget and M1 to M5 rules are fixed | 9 | PROTO | E |
| 42 | No analyst session has run; EVAL-7 waits on GATE-7 | 9 | PROG, PROTO | N |
| 43 | The project does not claim adoption, blackouts prevented, savings or forecast skill | 9 | WP 6, SCORE | E |
| 44 | Each release builds one image, pushes it to Artifact Registry and deploys it to Cloud Run by platform digest with Firebase Authentication and Firestore; release 25 is `grid-nowcast-00047-lnt` (release 24 was `grid-nowcast-00046-vl5`, release 23 `grid-nowcast-00045-vg8`; rewritten 2026-10-19; the REL-2 row was the HOST-2 plan) | 10 | PROG row 'Batch release 25' (2026-10-19), REV-HOST-2 | E |
| 45 | The API, workspace and browser walkthrough run locally over emulators | 10 (REL-2 text; not on the slide since 2026-10-18) | H1, W3 | E |
| 46 | Hosted deployment evidence exists: URL, revision, platform digest and rollback command in each release row, 24 of 24 Hosting checks in the HOST-2 record; releases 23 to 25 each read back one stamp on Hosting, the first screen and Cloud Run; the stranger walkthrough is HOST-3, deferred by the owner 2026-10-17 (rewritten 2026-10-19; the REL-2 row said none existed) | 10 | PROG rows 'Batch release 23' (2026-10-18) and 'Batch release 25' (2026-10-19), REV-HOST-2, MILES | E |
| 47 | The delivery status list of delivered, cut, deferred and pending items is as PROGRESS, tasks.json and milestones record (updated 2026-10-18) | 11 | PROG, MILES | E |
| 48 | M3 live evidence exists as one accepted cited Gemini receipt | 11 | REV-CORE-6, LIVE | E |
| 49 | The research frontier and the open questions are as research 30 records | 11 | MILES, R30 | E |
| 50 | The four judge objections are answered at the object level | 12 | SCORE | E |
| 51 | OpenGrid converges with this project's assumptions framing and is cited as positioning only | Cover | STRAT, R30 | E |
| 52 | Four questions from established work organize the entry: belief revision and the two clocks, decision theory, coordination theory, organizational learning | 1 | FOUND | E |
| 53 | The productivity gain from AI in knowledge work is bounded by trust and traceability, and both are properties of records, not of models (the entry's claim, a hypothesis until experiment 3; the slide says so) | 1 | FOW | F |
| 54 | The first screen is a sign-in screen and the owner keeps the sign-in wall | 4 | BOARD R11, PROG row 'Batch release 20' (2026-10-18) | E |
| 55 | The judges' account is to be named in the submission form (the form is REL-7; no receipt yet) | 4, 10 | AUTH | F |
| 56 | The submission deploys ran as batch releases 22 to 25: one deployer, one complete build each; the submission identifiers are those of the last release before the portal submission, release 25 at this writing | 4, 10 | PROG rows 'Batch release 22' to 'Batch release 25' (2026-10-18 and 2026-10-19), BOARD R12, R14 to R16 | E |
| 57 | The ask service's recorded plan sets (built as the dock, DOCK-1 to DOCK-5) exist only for the ask page and the synthetic event; every other page's recorded answer file is a 404; live since batch release 22 (2026-10-18), the command bar of GitHub PR #102 replaces the floating dock panel and reads the same plan sets; since batch release 23 (2026-10-18) the bar answers a signed-in visitor live on Vertex AI under the day meter (`DESK_GEMINI=1` on Cloud Run), and anonymous visitors get composed answers; since batch release 25 (2026-10-19) the trace steps stream as the answer is written, or arrive together with it where Firebase Hosting buffers the response (the withdrawn "wrong figure" of the release 23 row was a citation mark glued to the figure in copied text) | 10, 11 | PROG rows 'Batch release 22' and 'Batch release 23' (2026-10-18) and 'Batch release 25' (2026-10-19) | E |

Every row above is checkable against the named file. The deck asserts no number that is not in
one of those files. Rows 13, 14 and 45 describe the REL-2 text of slides 4 and 10, rewritten on
2026-10-18; their evidence stands, and the slides no longer carry those claims.

## Appendix C: PDF build steps

The competition wants the explanation deck as a PDF (the FAQ wording is "PPT converted to
PDF"), in English, and the submission checklist tracks it as "Story: final deck PDF, English
copy, matched implemented claims" [REQ][CHECK][R30]. This Markdown file is the text of record;
the PDF must reproduce it. The steps below are recorded, not all executed: see the note at the
end of this appendix.

1. Work from the repository root of the release candidate commit, with a clean tree.
2. Primary path, if `pandoc` and a TeX engine are installed:

   ```sh
   mkdir -p .local/release
   pandoc docs/competition/ai-builder-cup-2026/deck.md \
     -o .local/release/grid-nowcast-deck.pdf \
     --pdf-engine=xelatex \
     -V geometry:a4paper -V geometry:margin=18mm -V fontsize=10pt \
     --toc --toc-depth=2 \
     --metadata title="InGRID - AI Builder Cup 2026"
   ```

   Checks after the build: the PDF opens; the cover, slides 1 to 12 and appendices A to E are
   present in order; the tables render; and the text of every slide matches this file.
3. Fallback path, if no TeX engine is available (this produces a plain, readable printout, not
   the styled deck): render the Markdown to a paged HTML file with the standard library, then
   print it to PDF from a browser.

   ```sh
   /usr/bin/python3 - <<'PY'
   import html, pathlib
   src = pathlib.Path("docs/competition/ai-builder-cup-2026/deck.md")
   out = pathlib.Path(".local/release/grid-nowcast-deck.html")
   out.parent.mkdir(parents=True, exist_ok=True)
   body = html.escape(src.read_text(encoding="utf-8"))
   body = body.replace("## ", "</pre><pre>## ", 1)  # first slide heading starts a page
   page = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
           "<title>InGRID deck</title><style>"
           "@page{size:A4;margin:18mm}pre{white-space:pre-wrap;"
           "font:10pt/1.35 ui-monospace,Menlo,Consolas,monospace}"
           "</style></head><body><pre>" + body + "</pre></body></html>")
   out.write_text(page, encoding="utf-8")
   print("wrote", out, out.stat().st_size, "bytes")
   PY
   ```

   Then open `.local/release/grid-nowcast-deck.html` in a browser and use Print -> Save as
   PDF, A4, default margins, background graphics off.
4. Record the artifact: SHA-256 of the PDF, page count, source commit, and the tool and version
   used, in the release manifest (REL-4) and, at submission, in the portal receipt (REL-7).
   The PDF is a release artifact, so it is built from the frozen commit and never rebuilt from
   an edited working tree [CHECK][MILES].
5. Update step: if any claim in this deck changes, the change is made here first, its evidence
   reference and Appendix B status are updated in the same commit, and the PDF is rebuilt. A
   stale PDF that says more than the repository does is the failure mode this appendix exists
   to prevent [CHECK].

**What was executed while writing this deck.** Appendix C step 3 was run as written and
produced `.local/release/grid-nowcast-deck.html` under the ignored `.local/` tree. Its byte
size and SHA-256 are recorded in the task packet rather than here, because editing this file
changes them. **No PDF was produced by this task.** The executor seat runs `/usr/bin/python3`,
`git` and the local H1 test script; `pandoc`, a TeX engine, `libreoffice` and a browser are not
present in it (`shutil.which` returns `None` for `pandoc`, `wkhtmltopdf`, `weasyprint`,
`libreoffice`, `soffice` and `chromium`), so step 2 and step 3's print action were not run and
are not reported as run. Building the PDF is a release-owner action and is recorded here rather
than assumed.

## Appendix D: How this deck was checked

Commands run from the worktree root of `task/REL-2` with `/usr/bin/python3` (Python 3.14.4) on
the tree this file is committed in. No model call, cloud write, credential use or network call
by any of them. The same commands and results are recorded in the task packet
`docs/work/probe-bundle/implementation.md`.

| Check | Command | Result |
|---|---|---|
| Repository verify command | `/usr/bin/python3 scripts/repo.py check` | Exit 1 with three `Broken local link` errors, all in `docs/work/reviews/REL-2.md`, whose three deck-line links are absolute paths with a `:line` suffix no file matches; no error concerns this file. The counts and exact output are in the task packet, which records this as a hand-back item because fixing the record is not this task's to do |
| Full offline suite | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 420 tests in 5.621s` - `OK` (the post-commit re-run is in the task packet) |
| Plan integrity | `/usr/bin/python3 scripts/plan.py check` | `OK: 45 tasks, 7 gates` |
| Scope | `/usr/bin/python3 scripts/plan.py scope REL-2 feat/h1-api-persistence` | Exit 1, listing `docs/work/reviews/EVAL-3.md` - the review record inherited from the stacked parent (`task/REL-2` is stacked on `task/EVAL-3`), not this task's work; `scope REL-2 task/EVAL-3` prints `OK: all changed files inside REL-2 allowed paths` |
| English only | `/usr/bin/python3 .local/rel2/check_deck.py` | `PASS: ASCII-only, ...` - the file contains no character outside ASCII, which is a necessary condition for the English-only item and not proof of it; the English itself was inspected by reading the prose, as the note below records |
| Structure and markers | `/usr/bin/python3 .local/rel2/check_deck.py` | `PASS: ASCII-only, 12 slides, every bullet referenced, every marker defined`. Exact line, character, marker and register counts are in the task packet, because editing this file changes them |
| PDF fallback render | Appendix C step 3, run as written | `wrote .local/release/grid-nowcast-deck.html ... bytes`; the size and the digest of that render are in the task packet |

`check_deck.py` is a scratch script under the ignored `.local/rel2/` directory, outside the
repository tree; it is not a test and not a runtime dependency. It fails if a bullet carries no
evidence marker or if any marker used is missing from Appendix A. The English check is a
necessary condition, not proof of good English: it rejects non-ASCII text, and the prose was
read once more by the author. Nothing in this file is a substitute for the packets it cites;
where a packet records a run, the packet holds the command and its output.

**The slide-1 replacement (REL-4, 2026-10-17).** Slide 1 was replaced to open on the four
questions of the [theoretical foundation](../../architecture/theoretical-foundation.md) and the
claim that trust and traceability are properties of records; the stale-assumption line is now
its second bullet, the speaker notes open on the same claim, `[FOUND]` and `[FOW]` were added
to Appendix A, and Appendix B gained rows 52 and 53. The replacement's commands and results,
including the byte-for-byte comparison of slides 2 to 12 against the accepted REL-2 revision
and the structural deck check, are in the
[REL-4 task record](../../work/entry-framing-2026-10-17/implementation.md). Twelve slides
remain.

**The slide-4 and slide-10 rewrite (POLISH-2, 2026-10-18).** Slides 4 and 10 were rewritten
to the live state after finding F-01 of the independent review; slide 10 is now the one
services table. Appendix A gained the markers `REV-HOST-2`, `LIVE-REAL`, `EVENT`, `SVC`,
`BOARD`, `AUTH`, `PERM` and `ALERTS`; Appendix B rows 17, 44 and 46 were rewritten and are
established, rows 54 to 57 were added, rows 13, 14 and 45 are marked as REL-2 text, and
slide 11's status bullets and row 47 were updated to tasks.json after batch release 21
(PROGRESS row 'Batch release 21' (2026-10-18)). The
scratch scripts of REL-2 and REL-4 are not in this checkout, so the structural check was
rerun as an equivalent scratch script (ignored, outside the tree): it counts the `## Slide N`
headings, flags every slide bullet and every slide table row without a bracketed marker, and
flags every marker without an Appendix A row; it also checks that the file is ASCII-only.
Its output on this revision: `deck: 12 slides, 45 markers used, 0 unmarked bullets/rows, undefined markers: none, non-ASCII bytes: 0`. `python3 scripts/repo.py check` printed
`PASS` on the same tree. No test module reads this file (`grep -rln deck.md tests` finds none).

## Appendix E: What this deck must not claim

Taken verbatim from the project's own prohibitions, so the video, the PDF and the answers to
judges stay inside them:

- No live nowcasting or production readiness; no newly trained or first-ever grid foundation
  model; no earlier warnings than the operator; no prevented blackouts, saved money or reduced
  emissions; no calibrated event probabilities from semantic scores; no graph path as proof of
  cause; no scenario difference as a measured real-world effect; no autonomous recommendation
  as approval to operate anything; and not "first energy deployment of a decision model" -
  only "no published deployment found as of 2026-10-11" [WP][R30].
- No claim that an energy narrative is an emissions measurement, and no commercial or
  resilience claims without evidence [SCORE].
- No claim of OpenGrid partnership, integration, dependency or compatibility; convergence is
  positioning only [STRAT][R30].
- Fixture results are reported separately from any real case and are never presented as
  analyst validation [FIX][EVAL].
- A polished fixture-only presentation must not be scored as real analyst validation, and a
  missing eligibility item makes the entry not ready even when the concept score is high
  [SCORE][REQ].
