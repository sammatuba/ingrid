# First case: evidence to a supply outlook revision

<!-- grid-nowcast-definitive-2026-10-04 -->
> **2026-10-04 update:** the [definitive v1 design](../product/definitive-blueprint-2026-10-04.md) and [execution milestones](../work/milestones.md) now govern the selected scope, architecture and launch order. This earlier record is preserved; conflicting open choices or schedules below are superseded, not evidence of implemented capability.


**Status: execution brief; awaiting a real episode. No example results or plant facts are supplied.**

Direction: [Nowcast strategy](../product/strategy.md).
Preferred case: a commissioning/connection milestone challenges a supply-entry assumption.
Use an outage-duration revision instead if that provides the clearer permitted analyst case.

## Inputs to establish at the start

| Input | Current status | Why needed |
|---|---|---|
| Episode, analyst and target decision | Not yet selected | Defines whose decision and what question the work must improve. |
| Original assumption and forecast cycle | Not yet provided | Establishes the before-state without reconstructing it from later outcomes. |
| Information cutoff and chronology | Not yet provided | Separates known-then evidence from subsequent developments. |
| Permitted documents and exact versions/passages | Case-specific inputs needed | Supports claims, contradictions and source-lineage grouping. |
| Relevant GCS series/advisory references | Availability confirmed; case schema/coverage uninspected | Supplies dated market context, units, price status and availability limits. |
| Plant/unit/resource/model mapping | Not yet reviewed | Prevents an announcement about one object changing an unrelated model input. |
| Baseline manual research process | To reconstruct with the analyst | Enables a meaningful comparison of correctness, effort and rework. |
| Scenario input representation and comparable outputs | Not yet supplied | Enables a faithful proposal; output comparison is conditional on availability. |

Request only these case inputs at execution time. Do not request credentials in documents,
restart market ingestion or copy the private Forecasting estate into this repository.

## Case pack

Create `docs/cases/<case-id>/` from the repository root with:

- `brief.md`: question, user, cutoff, horizon, prior assumption, baseline workflow and disposition.
- `evidence-manifest.json`: immutable source/version references, exact passage or numerical
  lineage, publication/first-observed times, access context and source-lineage groups.
- `mappings.json`: canonical entity types and reviewed source-to-model correspondences,
  validity periods, cardinality and unresolved matches.
- `review.md`: competing interpretations, supported and unsupported links, proposed delta,
  reviewer, retain/revise/reject/defer outcome and reasons.
- `scenario-proposal.md`: baseline and alternative assumptions, affected representation,
  common background inputs, horizon, units, expected output contract and required approval.
- `evaluation.md`: frozen questions, baseline answers/effort, assisted answers/effort, failures
  and what can reasonably be concluded from this case.
- `outlook-revision.md`: accepted before/after position, sources, remaining uncertainty and
  any compatible run comparison. If no run exists, state that consequences remain uncomputed.

These are planned case artifacts, not files that already exist. Keep private evidence in its
approved location and store only permitted references/content. Define the record fields while
assembling the case; a universal schema is unnecessary.

## Walkthrough to validate

1. Freeze the question and information cutoff. Separate later outcomes for subsequent evaluation.
2. Retrieve the available numerical/advisory context and the source passages actually known
   then. Mark unknown first availability; show numerical data freshness and raw/final status.
3. Resolve the asset identity and model correspondence with review. Stop dependent proposals
   at an ambiguous mapping rather than guessing.
4. Extract attributed claims. Keep reported targets, factual observations, assumptions and
   model outputs distinct. Group repeated publications by original source.
5. Compare the new evidence with the prior assumption. Preserve a competing explanation,
   contradiction or unknown where one exists. Do not fabricate one to populate a checklist.
6. Record the analyst's disposition and its reasoning. A justified no-change decision passes.
7. Where warranted, prepare baseline/alternative scenarios with one explicit change and common
   background inputs. Do not edit PLEXOS or run it from an extracted claim or an AI suggestion.
8. Compare supplied compatible results, or request the existing operator process when a run
   becomes necessary. Preserve input snapshot, model version, horizon, units and run receipt.
9. Write the outlook revision and assess it against the manual/simple-retrieval baseline.

## Acceptance and failure cases

All material assertions must be traceable. A later document must be excluded by an earlier
cutoff; an uncertain mapping must remain uncertain; a missing approval must prevent execution;
conflicting claims must survive synthesis. Use explicitly synthetic fixtures to check these
behaviors when the real episode lacks a particular edge case; report fixture and real-case
results separately.

The analyst must be able to inspect the prior position, alternatives, proposed change and
reason for the final disposition. Record missed issues, unsupported suggestions, review time
and rework with and without assistance. Do not invent a speedup target or generalize from one
episode. Freeze broader evaluation thresholds before evaluating additional cases.

This work unit is complete when the real case has a reviewed outlook revision and an evaluation
record. If outputs are absent, scenario fidelity is assessable but quantitative consequences
are not. Record that limit before deciding whether to authorize a separate comparison run.
