# InGRID: definitive product blueprint v1

Decision date: 2026-10-04. Owner: Sam. Status: selected design and execution baseline;
implementation and performance remain separately evidenced. Supersedes earlier open-ended
architecture choices and competition planning where this document explicitly decides them.

<!-- strategy-refresh-2026-10-14 -->
> **2026-10-14 note:** the [strategy refresh](../work/strategy-refresh-2026-10-14/strategy.md)
> puts the Philippine grid on the first screen with no sign-in and makes the change desk the
> drill-down from one real event (PEDC Unit 2, 2026-09-21). Clef hosting (CLEF-2, 3), the
> computed what-if (NUM-2, 3) and the analyst-internal views (UI-3 to UI-6) are cut.

<!-- strategy-refresh-2026-10-11 -->
> **2026-10-11 note:** the [strategy refresh](../work/strategy-refresh-2026-10-11/strategy.md)
> revises the judgment unit (compiled probe bundle, computed abstention), the Clef-flash hosting
> path (System One API port, Google-hosted or Gemini emulation) and the scenario-consequence rule
> (BigQuery `AI.FORECAST` what-if, labelled directional). Other selections stand.

## 1. The product

**InGRID is a change-review desk for power-system outlooks. It shows what changed,
which assumptions are affected, and why the accepted outlook should stay or change.**

A forecast can be mathematically sound and still rely on an assumption that has become stale.
We connect evidence, numerical signals and reviewed assumptions without letting any model
silently overwrite the organization's accepted position.

First user: an energy analyst/modeler. First decision: retain, revise, defer, reject or investigate
an assumption. Durable output: an attributable outlook revision, including a justified no-change.
Primary competition theme: **Future of Work & Enterprise Productivity**. Resilience is the
long-term domain benefit, not a substitute for measured workflow value.

## 2. Two clocks and three loops

The fast loop estimates conditions over minutes to hours. The evidence loop tracks developments
from hours to months. The human review loop changes accepted assumptions. Their shared language
is identity, time, quantities, provenance and model representation - not one forced cadence.

Always distinguish information cutoff from review time. Reviewing historical evidence today
must never look like a decision made at that historical time. Keep observation time and first
availability separate. Data interval frequency is not arrival frequency.

## 3. One integrated promise

Sense: preserve measurements and reported developments.
Remember: connect evidence to the correct objects and versions.
Interpret: make bounded judgments and investigate ambiguity.
Review: accept a disposition and record a defensible before/after outlook.

The home screen asks, 'What changed since the last accepted outlook?' Grid monitoring is
supporting context, not a competing national dashboard product.

## 4. Selected model responsibilities

| Component | Owns | Must not do |
|---|---|---|
| Deterministic code | Units, intervals, numeric calculations, permissions and workflow validation | Delegate explicit formulas or authority to an LLM |
| TimesFM | Forecast trajectories of declared numerical quantities | Pretend a sparse-series onset experiment validates all forecasting tasks |
| TabFM and boosted baseline | Predict declared outcomes from available structured examples | Treat semantic scores as physical event probabilities |
| Clef-flash / S1 adapter | Judge an evidence-assumption relationship with abstention | Explain its internal reasoning, determine legal truth or authorize acceptance |
| Gemini | Cited extraction, alternatives, bounded investigation and intelligible review brief | Invent sources, run unsandboxed tools, approve its own work |
| Ontology/task compiler | Choose valid entities, definitions, context and allowed questions | Become a universal graph or a causal oracle |
| Analyst | Review assumptions and accept outlooks | Conflate assumption acceptance with permission to execute a model |

Gemini must perform substantive case work in the submission. Friendly wording on a conventional
forecast dashboard is insufficient for the intended technical/GenAI story.

## 5. What is innovative

The proposed contribution is an **ontology-guided prediction and belief-revision workflow**:
1. Compile a bounded, reproducible model task from a domain question and evidence snapshot.
2. Trace the dependencies from changed evidence to assumptions, model inputs and outlooks.
3. Combine numerical consequence signals with semantic relevance without merging probability meanings.
4. Use uncertainty to direct a useful investigation, not to manufacture a revision.
5. Render the review as an inspectable, time-aware difference between accepted positions.

These are testable differentiators, not a claim to have invented graph retrieval, decision models,
forecasting, human approval or temporal databases. Research novelty requires matched ablations.

## 6. Competition slice

One permitted outage-duration / return-to-service case is preferred because it can connect
short-horizon forecasts with a material supply assumption. A project commissioning case remains
valid, but it must not pretend a three-hour predictor validates next year's entry date.

The path is: exact source -> typed claim -> reviewed identity -> prior assumption -> bounded
judgment -> competing interpretation -> human disposition -> scenario proposal -> outlook diff.
Compatible supplied outputs may extend the case. Without outputs, numerical consequences stay
explicitly uncomputed. A synthetic case supports failure demonstrations but never substitutes
for real-case validation in performance claims.

## 7. Finish before widening

Must deliver: source viewer, cutoff filtering, one reviewed mapping, one assumption history,
Gemini-grounded alternatives, a working review transaction, dependency inspection, clear model
provenance, one model/evidence evaluation view, a deployment and a safe judge sandbox.

Do not require before submission: a live national feed, a complete asset map, broad regulatory
corpus, a graph database, multi-agent autonomy, PLEXOS execution, model fine-tuning, world-model
training, realtime audio, or generated video scenes. No new ingestion estate is required.

TimesFM/TabFM and S1 work remain active, but their adoption depends on measured usefulness.
A weaker challenger may be honestly shown as experimental; it must not drag the core workflow
below a proven baseline. A missing model does not disable manual evidence review.

## 8. Foundation-model ambition

Stage A: apply existing foundation models to declared domain tasks.
Stage B: adapt permitted weights using adjudicated grid examples and lineage-preserving data.
Stage C: demonstrate transfer across tasks, entities and later regimes with limited adaptation.

The competition entry is primarily Stage A plus a data/ontology foundation for B/C. A reusable
learned grid representation is a later empirical claim. Ten years of accessible data would be
valuable, but access, compatible semantics, coverage and usable labels must be demonstrated.

## 9. Product success and boundaries

Measure missed material issues, unsupported proposals, time to a defensible disposition,
reviewer rework, and traceability. Forecast metrics are a separate scorecard. Carbon, outage and
commercial effects need later causal/operational evidence. No-change is success when justified.

All records carry content kind, review status, availability state and execution mode as separate
axes. 'Accepted' is not a content kind and does not turn a prediction into an observation.
The belief state is a projection of accepted assumption versions, not a second mutable truth store.

## 10. Authority and companion specifications

- [System architecture](../architecture/decision-system-v1.md)
- [Ontology and task contracts](../architecture/ontology-profile-v1.md)
- [Interface and demo](interface-and-demo-v1.md)
- [Research grounding](../research/28-research-grounding-2026-10-04.md)
- [Competition requirements](../competition/ai-builder-cup-2026/requirements.md)
- [Execution launch board](../work/hackathon-2026-10-04/execution.md)

These define v1. Reopen a selected decision only for a failed acceptance gate, material source
change, an unavailable dependency, or a changed user goal. A new model announcement alone is
not a reason to restart the product strategy.
