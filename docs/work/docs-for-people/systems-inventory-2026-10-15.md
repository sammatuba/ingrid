# The systems in place: inventory for the explainer (2026-10-15)

Orchestrator record, written for DOC-4 after the owner's conceptual review request ("I want to know the
frameworks and tools we're employing and how they all connect and fit in place to the conceptual
foundation"). Every row names the committed record it comes from. The explainer's systems map reads its
node data from this inventory; when a status changes, change it here first and then in the widget.

## The foundation in one paragraph

InGRID is a change-review desk for power-system analysts. An operator notice arrives. The desk
asks whether the notice supports or challenges an accepted assumption about the grid, at the moment the
notice became available. Three authorities never mix. Code owns time, identity, access and the write
transaction. Models answer typed questions only inside a compiled, permitted context. The analyst owns
acceptance. The method is a composition of known parts; the working paper refuses to claim it invented
any of them ([working paper](../../product/working-paper-2026-10-11.md), sections 1 and 6).

## Status words

| Status | Meaning |
|---|---|
| live | runs on the site today |
| built | in the code and the suite, exercised by tests or a recorded run, not on every page view |
| recorded | ran once or in one comparison; the record holds the numbers; not rerun |
| designed | in the working paper with a contract; no code path runs it |

## Inventory

| Id | Component | What it is | Role in the desk | Status | Source |
|---|---|---|---|---|---|
| ontology | Ontology profile v1 | Typed meaning: claims, sources, assumptions, mappings, five time fields per record | Defines what a task may mean before any model sees it | built | [ontology profile](../../architecture/ontology-profile-v1.md) |
| compiler | Known-then compiler | Filters by access, availability, reviewed identity, context; one fingerprint per task | Keeps the future out of every judgment; makes runs reproducible | live | [working paper](../../product/working-paper-2026-10-11.md) 5.1; [review core](../../../src/review/README.md) |
| transaction | Review transaction | Firestore append with expected heads, idempotency key, audit entry | The only path that changes an accepted assumption | live | working paper 5.8; [decision system v1](../../architecture/decision-system-v1.md) 6 and 7 |
| systemone | System One API port | One request shape: state plus typed questions; choice or probability answers | Lets any decision backend plug in | built (one backend) | working paper 5.5; `src/adapters/systemone/` |
| gemini-s1 | Decision questions on Gemini | Gemini 3.8 Flash on Vertex, structured response schema, thinking budget 0, four wordings per question | Answers the eight typed questions | recorded (one real-case run) | [live run 2026-10-14](../grid-desk/live-run-2026-10-14.md); `src/adapters/gemini/` |
| compose | Composition table | Fourteen rules in fixed order; thresholds 0.6, 0.5, 0.5 fixed before testing | Turns answers into one label; code, not the model, decides | live | working paper 5.3; `src/judgment/bundle.py` |
| receipt | Stability record | Flip rate and polarity gap across wordings; unstable vetoes to "not enough evidence" | Turns the 2026 audit findings into a mechanism | built (never fired: every flip rate was zero) | working paper 5.3; [comparison report](../probe-bundle/evaluation.md) |
| gemini-s2 | Gemini analysis roles (System Two) | Cited claim extraction, competing interpretations, review brief, escalation on insufficient or unstable | The reasoning and analysis layer; never composes the label, never accepts | designed (transport built, no live task) | working paper 5.7; [research 26](../../research/26-google-stack-fit.md) section 8 |
| bigquery | BigQuery data foundation | Five-minute WESM tables; features available at the time, labels matured; three-hour embargo | Source of every figure on the grid page | built (teammate) | [data foundation](../data-foundation/intent.md); explainer chapter 13 |
| timesfm | TimesFM through AI.FORECAST | Google time-series foundation model inside BigQuery (2.5 GA, 3.0 preview) | Reserve-shortfall forecast; the covariate what-if for scenarios | recorded (zero-shot onset AUC 0.69 to 0.78, below the hour-of-day baseline); what-if designed, not run | [TimesFM and TabFM](../data-foundation/timesfm-tabfm.md); working paper 5.6 |
| tabfm | TabFM through AI.PREDICT | Google zero-shot tabular in-context model inside BigQuery (preview) | Reserve-onset classifier from 17 grid features | recorded (AUC Visayas 0.943, Mindanao 0.961) | [TimesFM and TabFM](../data-foundation/timesfm-tabfm.md) |
| boosted | Local boosted trees | Gradient boosting trained on the same features | The baseline TabFM tied with (AUC 0.947, 0.967) | recorded | [training](../data-foundation/training.md) |
| event2vec | Event2Vec event map | One vector per typed operator event; a day is a clipped running sum; 175 types, 16 numbers | Day-as-a-path panel, nearest similar days, early-warning probe (noon AUC 0.785 against the best rule 0.717) | live (panel) and recorded (spike) | [spike record](../event-map/spike-2026-10-15.md); EXPL-2 record |
| grid-page | Replay grid page | Static desk over baked five-minute data, every element explorable | How people meet the data | live | [explore record](../explore/implementation.md) |
| event-page | Event page | The recorded judgment, the cutoff pair, the rule that fired, the decision form | How people meet the judgment | live | [grid desk record](../grid-desk/implementation.md) |
| evaluation | Evaluation harness | 28 labelled compiles, three ablations, metrics fixed before any backend ran | Evidence for the method and its refused claims | recorded (22 of 28 both ways; the set abstains 4 times) | [comparison report](../probe-bundle/evaluation.md) |
| hosting | Cloud Run and Firebase Hosting | Stamped immutable files from the CDN; one instance at most; one deploy per batch | Where it runs | live | [hosting record](../hosting/implementation.md); explainer chapter 14 |
| docs | Plain-language pages and explainer | STE-checked pages, interactive chapters at /explain | How the team and the judges understand it | live | [DOC record](implementation.md) |

## How they connect

Reading side: notice bytes with a fingerprint, admitted at the cutoff by the compiler; one task per
cutoff; Gemini answers the typed questions in four wordings; the table picks the first rule that fits;
the receipt records stability; the analyst decides; the transaction writes or refuses. Every object in
that chain is on the event page.

Numbers side: the BigQuery foundation turns raw market files into figures, features and labels under the
same availability rule. TabFM and the boosted trees score reserve onset. TimesFM forecasts a series from
its history. The join between the two sides is the reviewed mapping: an accepted assumption becomes a
future-covariate path, and two TimesFM forecasts with two paths give a directional scenario difference.
That bridge is designed and unrun.

Event map: a third representation, the day as a sequence of typed events. Today a browsing aid. Its next
role is as a signal the sufficiency question can see, never as a label.

## Gemini: two roles, two settings

| Role | Setting | Why | Status |
|---|---|---|---|
| System One, the typed questions | thinking off (budget 0), structured schema, four wordings, order and gaps only | The 2026 audits: answers flip with option order and polarity; Gemini 3.x returns no logprobs, so probabilities are verbal and uncalibrated | recorded on the real case |
| System Two, the analysis | thinking level high, cited passages, competing interpretations, review brief, escalation; grounding and a BigQuery toolset in the reference architecture | Deep reading where the desk needs analysis, kept outside the label and the transaction | designed |

The one live moment of analysis on record: on the PEDC return, Gemini read the four-notice set as a forced
outage and composed challenges; the scripted reading composed supports; the analyst recorded retain. The
desk kept the disagreement and shows it ([live run](../grid-desk/live-run-2026-10-14.md)).

Owner's emphasis for the hackathon (2026-10-15): the model thinks and flags, code composes and records,
the person decides. Recommended before submission: one live System Two task (the review brief for the
PEDC case) recorded like the probe run, shown beside its receipt.
