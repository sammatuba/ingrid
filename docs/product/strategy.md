# Nowcast: direction of record

<!-- grid-nowcast-definitive-2026-10-04 -->
> **2026-10-04 update:** the [definitive v1 design](definitive-blueprint-2026-10-04.md) and [execution milestones](../work/milestones.md) now govern the selected scope, architecture and launch order. This earlier record is preserved; conflicting open choices or schedules below are superseded, not evidence of implemented capability.


> **2026-10-11:** the [working paper](working-paper-2026-10-11.md) and [strategy refresh](../work/strategy-refresh-2026-10-11/strategy.md) define the probe-bundle method and revise three blueprint selections.

> **2026-10-14:** the [strategy refresh](../work/strategy-refresh-2026-10-14/strategy.md) selects the grid-first public screen; the desk is its drill-down. [START-HERE](../START-HERE.md) orients a person.

**2026-10-03 · Strategy finalized for the current phase · Owner: Sam**

**Repository scope update:** this repository is now the single software-platform home. The
user's later organization request supersedes prior instructions to locate an external code
repository. Lifecycle, skills, contracts and implementation stay here; no submodules or
multi-repository setup. See [architecture](../architecture/README.md) and
[lifecycle](../engineering/lifecycle.md). Product scope and evidence limits below still apply.

This closes the direction-setting round at Sam's request. **Grid Nowcast of Meaning is the
active project within Grid Nervous System.** It carries forward the evidence-to-outlook and
ontology work in [07](../strategy/history/07-evidence-to-outlook-research.md),
[08](../strategy/history/08-ontology-and-linked-intelligence.md) and [09](../strategy/history/09-session-handoff.md).
It supersedes earlier candidate rankings, retail-first build plans and mandatory harvester
steps. It selects a product direction, not a validated product, final competition submission,
production architecture or authorization to operate the forecasting estate.

## 1. The product and its first user

**Maintain an evidence-backed, revisable understanding of the Philippine electricity system,
and show how new evidence changes the assumptions, forecasts and scenarios analysts use.**

The first user is the energy analyst/modeler maintaining a supply-demand and market outlook.
The first decision is whether to retain, revise, investigate or defer an assumption, and which
scenario would clarify its consequences. The durable output is a **reviewed outlook revision**,
including a defensible decision to keep the current assumption.

Nowcast means the team's current understanding **as of a stated information cutoff**. It has
two connected parts: the latest available grid/market conditions, and what those conditions
and new research imply for the outlook. Five-minute data resolution does not establish
five-minute availability. Every view must show source freshness and material gaps.

The product should answer five questions:

1. What changed, and when could we have known it?
2. Which entity, region and assumption does it affect?
3. What supports or challenges our interpretation?
4. What should an analyst review or compare next?
5. What changed in the accepted outlook, and why?

Existing BI remains useful for monitoring. Nowcast adds evidence relationships, assumption
history and a reviewable path into modeling. Improved forecast skill, earlier warnings,
commercial value and analyst time savings are hypotheses to measure.

## 2. Scope and order

| Area | Current decision |
|---|---|
| Grid and market conditions | Use existing GCS WESM Parquet and SO advisories; assemble bounded, dated context for an investigation. |
| Text intelligence | Treat permitted policy, project, economic and industry material as attributed evidence with versions and passages. Begin with the first case's sources. |
| Assumption maintenance | Core: preserve the prior position, conflicting evidence, alternatives, review disposition and affected model representation. |
| Modeling | Prepare conditional scenario proposals and compare compatible outputs; retain existing PLEXOS operator gates. |
| Operational risk prediction | A subsequent evaluated capability; it is not a prerequisite for useful assumption reviews. |
| Contracts, customer load and portfolio exposure | Later commercial extension. Preserve identifiers/context that can support it; do not require private exposure data now. |
| Flexibility Atlas | Separate parked application of shared intelligence; storage/flexible-load optimization has its own validation requirements. |
| Climate-Adaptive Grid OS | Separate parked response/coordination application; posture policies and permissions require their own evidence and users. |
| Earlier retail/other ideas | Historical alternatives in [ideas/](../ideas/README.md), outside the active backlog. |

Minutes-to-hours observations supply current context. Days-to-weeks developments inform
near-term outlook review. Months-to-quarters project and economic evidence informs explicit
assumptions. Long-run policies remain conditional scenario context. These horizons share
identities and provenance, not a forced common update cadence or a single prediction score.

## 3. First validation slice

**One real supply/project-timing development → one reviewed assumption → one scenario proposal
→ one outlook revision.** Prefer a commissioning or connection milestone that challenged a
forecast assumption. An outage-duration episode is an acceptable substitute if it supplies
the clearer permitted evidence and analyst decision. Do not invent a historical case.

The analyst opens an as-of case with relevant market/SO context, reads exact passages,
checks the asset-to-model mapping, sees the prior assumption and competing interpretations,
and records retain/revise/defer. A material unresolved change can produce a baseline versus
alternative scenario proposal. A comparison uses supplied compatible outputs or a separately
authorized run. Without outputs, the case ends honestly at a reviewed proposal.

The first interface needs an evidence timeline, assumption review and outlook revision with
scenario comparison when available. A map/atlas is an optional view over the same records.
Do not make a national dashboard, broad news crawler or many-model benchmark a prerequisite.

The [first-case brief](../cases/first-case.md) is the execution entry point. No real episode,
data schema, source-to-model mapping or model result is asserted by this strategy.

## 4. Semantic and technical commitments

Use a small explicit domain model before selecting storage. Keep these states distinct:
physical conditions; rules/institutions; analyst beliefs; and model inputs/results.

The minimum linked records are entity/mapping, document version/passage, attributed claim,
event report, series reference, assumption version, model representation, scenario proposal,
review decision and outlook revision. Add model run/comparison records when outputs exist.
The definitions in [08](../strategy/history/08-ontology-and-linked-intelligence.md) and the grounding in
[research/27](../research/27-ontology-for-energy-intelligence.md) govern this profile.

Every consequential relationship needs provenance, context and time. Preserve event/valid
time, publication/effectivity where applicable, first-observed time, revision and information
cutoff. Unknown historical availability remains unknown. Source claims, accepted assumptions
and simulation outputs are separate. Plant, unit, market resource and modeled aggregate are
different types; ambiguous mappings block dependent conclusions until reviewed.

Keep numerical histories and large artifacts in existing stores. Link their versioned
references and bounded query results; do not duplicate GCS or turn every interval into a graph
node. Begin the case with inspectable typed records. A relational store, graph database,
retrieval engine, framework and deployment stack remain implementation choices after the case
establishes necessary queries. No universal ontology or standards-conformance claim is needed.

| Component | Responsibility in this direction |
|---|---|
| Deterministic services | Time/unit alignment, calculations, validation, provenance and permission checks. |
| Gemini / System Two | Evidence extraction and synthesis, alternatives and scenario proposals, all source-grounded. |
| System One | Candidate bounded relevance/contradiction/prioritization judgments; add only if it improves a matched baseline. |
| TimesFM / TabFM | Candidate numerical/structured predictors for declared targets and horizons; neither is required for the first case. TabFM is not interchangeable with TabPFN. |
| PLEXOS | Conditional structural comparisons under stated assumptions and the existing operator workflow. |
| Analyst | Review mappings and assumptions, resolve material ambiguity, accept outlook revisions and authorize consequential actions. |

This is a responsibility split, not a mandatory model shopping list. Backend/version/access
claims from older research need verification when selected. Source text and model output can
propose work but cannot grant approval. Assumption review, run approval and execution remain
separate records. No forecasting scripts, production inputs or cloud jobs are changed here.

## 5. Evidence of success and gates

The first case tests traceability and decision usefulness, not generalized forecasting skill.
Record the current manual workflow and compare it with a simple document/metadata retrieval
baseline on the same questions, evidence cutoff and review budget. Compare ontology-guided
retrieval separately. Add model layers only against the resulting baseline.

| Gate | Evidence required before moving on |
|---|---|
| Case ready | A permitted real episode, prior assumption, decision cutoff and target decision; missing inputs explicitly listed. |
| Evidence trustworthy | Every material claim reaches an exact passage/version or numerical derivation; copied sources are grouped; contradictions and unknowns remain visible. |
| Time and identity correct | Known-then retrieval excludes later evidence; mappings, quantities, regions and horizons are reviewed; unknown availability is disclosed. |
| Review useful | Analyst can accept, reject, defer or retain with reasons; record unsupported suggestions, missed material issues and time/rework against the manual baseline. |
| Scenario faithful | Proposed delta names the model representation and background assumptions; comparison is like-for-like or explains incompatibility. Approval is not inferred. |
| Ready to expand | A complete reviewed case and its failures are documented; then test additional independent cases, including no-change and contradictory-evidence cases. |

Traceability, temporal exclusion and action boundaries are required for every material output
in the bounded case. Quantitative usefulness targets and case counts must be set before a
larger evaluation, using the actual task and analyst baseline. One successful case is not a
calibration set or commercial validation. Retrospective model knowledge can leak hindsight;
label replay limitations and use prospective shadow work before predictive claims.

If text improves review but not numerical forecast scores, retain the demonstrated review
value. If ontology-guided retrieval does not improve answers or review effort, simplify the
retrieval implementation while preserving identity, provenance and time. If System One adds no
value, omit that layer. Earlier-alert and sustainability claims need their own measured basis.

## 6. Execution sequence and decisions left open

**Delivery update, 2026-10-03:** the user selected capability-based parallel workstreams under
one [grand-plan architecture](../work/building-blocks/intent.md). Structured-data modeling
with TimesFM/TabFM, regulatory parsing and project/event intelligence may develop and evaluate
independently in parallel. The sequence below remains the integrated analyst-case validation
path, not a prerequisite chain for every workstream. Model promotion still requires its own
evaluation; accepted assumptions and external execution retain their review/authorization gates.

1. Complete the real-case brief and manual baseline.
2. Specify the minimal records, mappings and as-of evidence pack for that case.
3. Build the evidence-to-assumption review flow and deterministic validations.
4. Produce a scenario proposal and, when outputs are available, a comparison/outlook revision.
5. Evaluate against simple retrieval and analyst workflow; record failures before expansion.
6. Extend to demand/economic and rule-applicability cases, then assess operational predictions
   and later commercial/application modules on demonstrated need.

Execution still needs case-specific permitted artifacts, relevant GCS references/schema,
the prior forecast assumption and model mapping. These are inputs to the first work unit,
not reasons to reopen the entire strategy. Backend, storage, deployment, competition theme,
submission deliverables and release permissions are unresolved until their point of use.

Reopen the product direction if the analyst case shows no useful assumption/decision link,
necessary evidence cannot be used, or Sam changes the primary user/problem. New tools or
interesting adjacent ideas alone do not change the active scope. Record material direction
changes here or in a dated successor, and update the entry documents in the same change.
