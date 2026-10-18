# Behind the prototype: the data and the event map

<!-- paper: 3.2 3.3 -->

This chapter is the numerical side. It shows where the figures come from, from the market's files
to the pages, and the small experiment that turned operator messages into vectors.

## The data and the prototype

The operating company's copy of the market data holds 73 tables, about 24.9 GB, up to 29 September
2026. Final nodal prices cover 59 billing months, and the node count grows from 887 to 1,214. A
billing month runs from the 26th to the 25th. Prices come every five minutes, in pesos per MWh, and
the timestamps carry no time zone.

<!-- widget: fig-prototype -->

The warehouse holds the market's shared vocabulary: 2,178 entities and 3,543 relations. The
relations come from a closed list of six: located in, part of, represents, uses fuel, connects and
refers to. A new relation needs a new version of the data shape. The list holds no "causes"
relation.

## From files to the figures on the page

The data foundation runs inside BigQuery. Click a stage to see what each one holds.

<!-- widget: pipeline-layers -->

Two rules hold through the pipeline. Features must have been available at the origin time.
Labels must have matured before the training cutoff. A three-hour embargo between inputs and
labels keeps the future out of training. Every displayed value links to its field, with its unit
and its quantity kind. A bag of matching numbers is not numerical validation.

## The models the team tried

The question was whether a reserve shortage starts within the next one or three hours. A boosted
tree model trained locally and TabFM inside BigQuery tied. Visayas scored 0.947 against 0.943,
Mindanao 0.967 against 0.961, on area under the curve. Both beat an hour-of-day baseline over
all hours, but not inside the evening window.

TimesFM alone, zero-shot, was not competitive. TabFM ran once, on one context sample, with
probabilities that nobody calibrated. That makes the tie a dated result. Nobody reran it, and nobody shows it as a forecast.

## The semantic state

Every five minutes and for each grid, the pipeline writes one row of fixed words. The words
cover the price band, the reserve condition, the shortfall severity, the trend and the import
dependence. They also cover the alerts now and ahead. The pipeline rebuilds the alerts as of
each interval from the advisories issued by then, never from later knowledge. Code writes the
grid page's plain paragraph from such facts.

## The event map

The operator's messages are an event stream: 43,667 of them from July 2021 to September 2026.
A short experiment typed each one as grid, asset and action. Then it learned one vector per
type with Event2Vec. A day's history is the running sum of its event vectors, clipped to a
maximum length. Try the sum.

<!-- widget: vector-sum -->

Because the history is a sum, a linear score on it splits into one share per event. That
property makes a score explainable without a surrogate model. The clip changes that a little: once
the sum reaches the maximum length, the order of the events matters and the shares are
approximate.

The experiment measured two things on a time split: 2021 to 2025 for training and 2026 for testing.
On next-event prediction, the vectors beat a first-order Markov baseline by a small margin,
top-3 accuracy 0.437 against 0.417. On early warning from the state at noon, the vectors reached
AUC 0.785. The rule "an alert notice already before noon" reached 0.717 on the same split.

The site ships the vectors and draws each grid's day as a path. It ships no score. A score would
need several splits and a comparison with the onset model above. That evaluation has not run.

<!-- quiz -->
Q: The event-map score reached AUC 0.785 on the 2026 test year. What does the site show?
- The score, as an early warning
- [x] Only the path of the day. The score stays in the experiment until a proper evaluation exists
- The score, labelled experimental
Why: One split of one year is a reason to measure more, not a claim. The site draws the path and says "not a forecast, no score".
<!-- /quiz -->

## Sources for this chapter

- The data, the prototype and the shared vocabulary: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 3.2 and 3.3.
- The pipeline, the models and the tie: the [data foundation handoff](../work/data-foundation/HANDOFF.md), sections 2, 5 and 12.
- The numerical rules: [decision system v1](../architecture/decision-system-v1.md), section 8.
- The event map: the [experiment record](../work/event-map/spike-2026-10-15.md).
