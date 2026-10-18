# Platform boundaries

<!-- grid-nowcast-definitive-2026-10-04 -->
> **2026-10-04 update:** the [definitive v1 design](decision-system-v1.md) and [execution milestones](../work/milestones.md) now govern the selected scope, architecture and launch order. This earlier record is preserved; conflicting open choices or schedules below are superseded, not evidence of implemented capability.

> **2026-10-16:** the [meta thesis, technical framework and architecture](meta-thesis-and-framework.md) states the thesis at its most general, the seven record kinds, and the status of every box as of that day; it cites this page and the v1 design rather than replacing them. The [theoretical foundation](theoretical-foundation.md) names the four theories behind it.


**Status: logical boundaries, written before the first slice. Implemented since: Cloud Run with
Firebase Hosting in front, Firestore, Firebase anonymous identity, Vertex AI Gemini transport;
see the [hosting packet](../work/hosting/implementation.md). The boundary table below still governs.**
Detailed [platform contracts](platform-contracts.md) specify record ownership, ports, state
transitions, cutoff/access rules and integration behavior. The
[building-block grand plan](../work/building-blocks/intent.md) owns assignments;
[composition architecture](building-blocks.md) adds model and regulatory interchange contracts.
[Milestones](../work/milestones.md) own the order of work.
[Decision-system v1](decision-system-v1.md) selects the application stack; the
[H0 intent](../work/h0-review-case/intent.md) retained a stdlib-only offline core, which stands.
Earlier open technical choices below are historical where v1 decides them.

The [product strategy](../product/strategy.md) owns scope. This repository owns the application
code under `src/`; there are no sibling-repo dependencies or submodules.

## Organize around the evidence-to-outlook loop

| Boundary | Owns | Does not confer |
|---|---|---|
| Evidence | Versioned document/passages, observed series references, access context and source lineage | Factual acceptance of an extracted claim |
| Identity and time | Plant/unit/resource/model correspondences, validity and recorded times, units and cutoff queries | Equality from fuzzy name similarity |
| Research and assumptions | Attributed claims, hypotheses, competing explanations, versioned assumptions and review decisions | Permission to execute a scenario |
| Scenario and comparison | Explicit input deltas, model representations, run/output references and compatible comparisons | Real-world causation from simulation results |
| Outlook | Reviewed synthesis, prior/new position, remaining uncertainty and later outcome links | Forecast skill or commercial value without evaluation |
| Workflow and access | Actor identity, proposal/review/approval/receipt transitions and authorization checks | Approval from source text, AI suggestions or missing records |

Start as a modular application with explicit internal contracts. These are logical boundaries,
not a mandate to create six services or packages. Add code directories only with working code.
Use a domain/application/adapters separation where it clarifies a real dependency: the core
must not import an SDK, cloud path or experiment package to define its business meaning.

## Adapter boundary

Existing GCS datasets remain external data sources, accessed through bounded read adapters
selected by an intent. Retain references and data versions rather than copying all histories.
Document acquisition, numerical predictors, LLMs and scenario engines are replaceable adapters.
Source text is untrusted data. An adapter reports provenance and errors rather than granting
workflow authority. No model-specific answer format becomes the domain model by accident.

Scenario execution is initially a proposal/export contract. A future execution adapter needs
explicit authority, input/version checks, idempotency and receipts. Private operational systems
are outside this repository's scope; no multi-repository bootstrap or orchestration is needed.

## First-slice contract questions

The first implementation intent must specify:

- canonical identifiers and reviewed mappings, including one-to-many representations;
- event/valid time, publication/effectivity, first-observed time and revision semantics;
- source passage/artifact references, units, quantity type, region, horizon and price status;
- claim, assumption, proposal, review and execution state transitions and who may cause them;
- how an as-of query excludes later information and discloses unknown historical availability;
- how a scenario delta identifies a baseline and how incompatible results are refused;
- access rules for private/public evidence and the behavior on missing data or denied access;
- deterministic validations and meaningful cases that prove the boundaries.

Runtime, storage and model backends were chosen once those contracts were concrete (H0, H1,
CORE-7, HOST-2). No universal ontology or graph vendor is selected by this document. Numeric
histories, semantic records, retrieval indexes and execution controls have distinct duties.

## Verification layers

Repository checks prove navigation and handoff integrity. Product tests will prove domain
behavior, adapter contracts and end-to-end review. Research evaluations compare usefulness
against the analyst/simple-retrieval baseline with information cutoffs fixed. One kind of
check cannot stand in for the other two.
