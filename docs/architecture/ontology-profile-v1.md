# Ontology profile v1 and decision-task semantics

Status: implementable domain profile, not full CIM/CGMES or RDF conformance. Retains the existing
repository ontology research while constraining the first case. An ontology defines meaning;
a graph stores instances; a retrieval index finds context; a simulator computes consequences.

## Core types and distinctions

Physical: Region, Plant, GeneratingUnit, MarketResource, NetworkElement.
Institutional: Issuer, RuleVersion, ApplicabilityAssessment, MarketInterval, Commodity.
Evidence: SourceVersion, Passage, SeriesReference, Claim, EventReport, SourceLineageGroup.
Research: Hypothesis, AssumptionRevision, ReviewDecision, BeliefSnapshot.
Modeling: FeatureSpec, ModelSpec, PredictionArtifact, ModelRepresentation, ScenarioProposal,
RunArtifact, Comparison, OutlookRevision.
Judgment: DecisionTaskSpec, CompiledTask, JudgmentArtifact, DependencyImpact.

A unit is not its plant. A resource code is not an ownership name. A modeled aggregate is a
representation with cardinality, not an identity equivalence. Every mapping has evidence,
validity period and review status. Fuzzy similarity proposes a match; it does not accept one.

Capacity kind must name installed/dependable/available/scheduled/assumed. A target date is not
an observed milestone. Synchronization, testing, commissioning and commercial availability are
separate predicates whose precise operational definitions are case-reviewed.

## Relations

Use refersTo, attributedTo, reports, derivedFrom, supports, challenges, qualifiedBy, copiedFrom,
represents, usesAssumption, effectiveDuring, comparedWith, reviewedBy and dependsOn.
Avoid generic relatedTo as the integration contract. No default causes relation.
A proposed causal mechanism is a Hypothesis with support and alternatives, not a graph edge
that proves causality. Source lineage prevents copied news from becoming independent votes.

## A Claim is not a fact table row

Required: claim_id/revision, subject typed references, predicate, typed object/value, modality,
exact source revision/locator, attributed actor, stated valid time, publication time, first
availability, recorded time, extraction method/version and review state.

Keep extraction correctness, entity-match certainty, source authority, analyst acceptance,
probability of realization and forecast uncertainty separate. Unknowns carry a reason.
No outage record does not prove full availability. No repeal record does not establish that
a rule applies. Open-world evidence can coexist with closed, explicit action prerequisites.

## Time contract

1. Event/valid time: when the described condition applies.
2. Publication time: when the source says it was published.
3. First availability: evidence of when this workflow could access this version.
4. Recorded time: when the system stored the record.
5. Review/audit time: when a decision was actually taken.

Use offset-bearing timestamps normalized to UTC, preserving original time zone and precision.
Date-only data remains a date; do not fabricate midnight. Intervals are [start,end). Unknown
historical availability is excluded from strict known-then context, not backfilled from memory.

## Competency questions

- What changed since the last accepted outlook, using only permitted known-then sources?
- Which source-assumption pairs warrant review, and which remain supported?
- Which exact unit/model representation does this report concern?
- Are the apparent confirmations independent, copied, or derived from the same measurement?
- Which scenarios and accepted outlooks depend on a challenged input?
- What remains unknown, and what investigation could resolve a consequential uncertainty?
- Can we reproduce the earlier belief snapshot without later evidence or later review decisions?

## Task specification: evidence-assumption relationship

Task ID: evidence_assumption_relation.v1. Input: one accepted assumption revision, a reviewed
mapping, exact permitted passage(s), source attribution, modality and the necessary definitions.
Output labels: supports, challenges, mixed, unrelated, insufficient. Label policy:

supports: evidence is consistent with the assumption and directly bears on its proposition.
challenges: evidence gives a relevant reason to reconsider the proposition; not proof it is false.
mixed: distinct supported elements pull in different directions.
unrelated: the evidence does not bear on this proposition under the declared scope.
insufficient: necessary meaning/context is missing or cannot be determined.

Scores describe the judgment task, not a physical shortage probability. Missing reviewed
mapping is a deterministic block, not another probabilistic label. Only task-specific held-out
calibration may set routing thresholds. Before that, judgments are experimental review aids.

## Storage and evolution

Begin with versioned JSON payloads and explicitly typed relations in the semantic store.
Firestore adjacency records support bounded paths in the small case. Enforce a depth/node budget
and return truncation; never present a capped traversal as complete. Add a graph database only
when measured query needs justify it. Optional RDF exports may map to PROV/SOSA/QUDT patterns;
SHACL validation applies to RDF exports, not to arbitrary JSON by name alone.

Schema changes have an owner, version, migration and affected task/evaluation list. Models may
propose new types; they cannot extend production semantics automatically. Content hashes prove
byte identity, not truth, source independence or historic accessibility.

## Version 1.1 (2026-10-17): structural relations and the family tag

Owner: the data-foundation owner, approved 2026-10-17 in answer to question 4 of the
[ontology strategy](../work/ontology-2026-10-17/strategy.md). Appended; the text above is v1 unchanged.
Migration: none (additive). Affected: `scripts/ontology/` (the `grid_ontology` views) and the
[ontology intent](../work/ontology-2026-10-17/intent.md) checks.

Added relations (the closed list of `grid_ontology.relations` is these plus `represents` and
`refersTo` from v1):

| Relation | From, to | Review state |
|---|---|---|
| `partOf` | GeneratingUnit to Plant (node prefix) | proposed: many-to-one, unreviewed |
| `locatedIn` | GeneratingUnit, MarketResource, Plant to Region | accepted where the source states the region with high confidence |
| `connects` | NetworkElement (HVDC link) to each of its two Regions | proposed: read from the link name |
| `usesFuel` | GeneratingUnit to Commodity | from the registration list; internal, never public |

Family tag: a fact carries `family` in {D, S, P, O, F, Rules} (demand, supply, price, outage, fuel,
rules), the board's drivers. It is a tag on facts, not a type. Still no `causes` and no generic
`relatedTo`; a ranking of likely drivers is an evidence-weighted hypothesis, not a causal edge.
