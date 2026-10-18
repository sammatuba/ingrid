# Interface direction: make the change understandable

> **Superseded 2026-10-14:** the [strategy refresh](../work/strategy-refresh-2026-10-14/strategy.md)
> opens on the Philippine grid (a real map, no sign-in) and reaches this desk from one real event.
> The copy and visual rules there replace the journey below; this file is the dated record.

Selected experience: a calm, high-trust change desk, not a chatbot landing page or decorative
national map. Primary promise: 'When the evidence changes, know what must change.'

## Information architecture

One primary journey: Changes -> Case -> Evidence -> Review -> Outlook difference.
Secondary views: State, Model evidence, Assumptions and History. Keep deep research behind
progressive disclosure. Do not require a first-time judge to understand BB1-BB8.

## Five memorable interactions

1. **Rewind knowledge.** Move the information cutoff backward; later evidence leaves the model
context. Show review time separately. Never claim old evidence was known merely because its
event timestamp is old.
2. **Open the exact words.** A cited claim opens the original version and highlighted passage.
Distinguish 'testing' from 'available' in plain language without hiding the source.
3. **Trace what depends on it.** An interactive path connects source -> claim -> assumption ->
model representation -> outlook. These are dependency relations, not proven causal pathways.
4. **Compare one explicit change.** Show before/after model inputs. A capacity input diagram
is labeled input comparison; only compatible run outputs may show computed system consequences.
5. **Accept or retain, visibly.** Save a reason; show the new review record and accepted-history
diff. A blocked mapping prevents a dependent revision. A no-change case still records useful work.

## Screen specification

Header: product name, environment/mode, source freshness, information cutoff and case selector.
Main grid: left evidence timeline; central assumption/dependency and input comparison; right
review card with rationale and disposition. Bottom drawer: exact sources, model artifacts,
unknowns and audit history. One question per section, short factual sentences and defined terms.

Distinct metadata badges: content kind, review status and execution mode. No green 'trusted'
badge that mixes these. Distinguish official alert, observed condition, model prediction and
analyst assumption. Show missing data as missing, not zero.

An always-visible environment label says LIVE MODEL RUN, STORED RUN, RETROSPECTIVE REPLAY or
SYNTHETIC WALKTHROUGH. The supplied HTML is the last of these. It makes no model API calls and
has no authoritative backend. Stored fixture judgments must never display a provider latency.

## Visual system

Dark ink background, warm white type, a mint accent for accepted paths, amber for review-needed
states, and a restrained violet for model outputs. Use text/icons as well as color. Human-readable
large titles, tabular numerals, thin structural lines, generous whitespace, minimal shadows.
No particle globe, false realtime pulse, unexplained confidence donut or huge network hairball.

Animate meaningful transitions only: evidence arriving, dependencies highlighting, a review
record appended. Honor reduced motion. Never use motion to mask loading or missing functionality.

## Accessibility and interaction acceptance

Every interaction has a keyboard path, visible focus and accessible name. Tooltips also open on
focus/click and are not the sole source of meaning. Keep button targets at least 44px. Design
for 390px, 768px and 1440px widths; charts have text equivalents; no horizontal document overflow.
Use contrast-tested type and actual readable empty/error states. Escape external text.

Persist real accepted state server-side. A stale expected head returns a conflict. Reset in a
public sandbox affects only that session. No public session can discover private case counts.

The concept prototype supports a challenge, a justified no-change and an ambiguous-mapping
case; a cutoff control; evidence inspection; a source-to-outlook path; a hypothetical input
comparison; and local-only review history. It is an interaction target, not the deployed entry.

## What to instrument

Time to identify affected assumption; time to open supporting passage; errors in distinguishing
reported/predicted/accepted; successful disposition; backtracks; unsupported acceptance; and
ability to explain the decision afterward. Observe a person unfamiliar with the project. Visual
appeal matters, but comprehension and safe review completion are the first acceptance tests.

## Interface precedent (added 2026-10-11)

[Ask The Grid](https://askthegrid.com/) ([research 30, 2.6](../research/30-decision-models-and-energy-2026-10-11.md))
is the closest live interface to this vision for North American markets. Three idioms carry
over to UI-1 without changing the information architecture above:

1. **Entry cards.** Four plain questions on the home screen. Ours: "What changed since the
   accepted outlook?", "Open a case", "Find a unit or resource", "Review queue".
2. **Visible trace.** Their agent panel shows "Ran 4 tools". Our review brief shows the
   compiled chain as text: access and cutoff filter, reviewed mapping, n passages, 32 probes,
   composed rule, escalation. Each step links to its record; nothing is generated prose.
3. **Range view.** "Know the range before it settles" shows a distribution with spike risk
   and peak timing. Our scenario-difference view shows two labelled trajectories and their
   difference per step, headed "Which assumption moves the range", with the Preview and
   directional labels always visible and the uncomputed state unchanged.

Do not copy the map-first layout or data-breadth claims; this product is the review layer
above an explorer, not a competing explorer.
