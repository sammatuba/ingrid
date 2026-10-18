# Evidence ledger, main @ 6a30dfd (2026-10-16)

Companion to [strategy.md](strategy.md). Grades: **measured** = scored against labels or outcomes;
**recorded-once** = one real run with a receipt, unscored; **built-unexercised** = code and tests, fixture
or replay data only, or the live path blocked; **designed-only** = contract or intent without a run;
**absent** = no record. Every figure is quoted from the file named. Nothing was run this session.

## A. Semantic judgment (probe bundle v5)

| Claim | Grade | Figure or quote | File |
|---|---|---|---|
| Bundle versus single question | measured (scripted replay) | `single_render` 22/28, 14/18 calibration, 8/10 test; `bundle` 22/28, 15/18, 7/10, 4 abstentions (1 correct); "a tie" | [evaluation](../probe-bundle/evaluation.md) §2–3 |
| What the 28 are | measured | 25 pairs, 28 compiles; 16 calibration pairs (18 compiles), 9 test pairs (10 compiles) | §1 |
| Backend | no model | `execution_mode: synthetic_fixture`, `live_calls: 0` | §1 |
| Labels | self-authored | "executor-authored annotation, not analyst validation"; bundle "cannot disagree with `expected_composition` (28/28)" | §2, §5 |
| Sufficiency gate | one compile | affects only `pb-ng-2/t1`; absent from the test split | §3, §5 |
| Stability receipt | unidentified | every flip rate 0; `identifiable: false` | §3 |
| Thresholds | untuned | all 8 candidates tie; `tuned: false` | §1, §5 |
| Contested `earlier_observation` row | measured on 4 | right 2 of 2 for supply-outlook, wrong 0 of 2 for return-date | §4 |
| Manual analyst baseline | designed-only | protocol v3; "No analyst session has run" | [baseline protocol](../probe-bundle/baseline-protocol.md) §13 |
| Composer | built | 14 named rules plus `render_refused`; 8 questions, 4 forms; labels supports, challenges, mixed, unrelated, insufficient | `src/judgment/bundle.py` |

## B. The real case, PEDC U2 2026-09-21

| Claim | Grade | Figure or quote | File |
|---|---|---|---|
| Evaluation | absent | "No baseline and no assisted session were run on this case" | [evaluation](../../cases/pedc-u2-2026-09-21/evaluation.md) |
| Analyst | absent | every record by `eval-5-case-assembly`; "not evidence that any analyst session occurred" | [review](../../cases/pedc-u2-2026-09-21/review.md) |
| Timeline | reconstructed | desk acts placed at 00:05 and 00:10 on 09-21; assembled 2026-10-14 | [brief](../../cases/pedc-u2-2026-09-21/brief.md) |
| 83.7 MW | caveated | register value; "does not establish the seeded 83.7 MW for 2026-09-21" | brief, review |
| Disposition | absent | "the case records no disposition" | review |
| Scripted labels | fixture | trip/T1 challenges; return/T0 challenges; return/T1 supports (`availability_confirmed`) | review |
| Consequences | absent | uncomputed; dispatch unordered, `RUN_TIME` absent | [scenario proposal](../../cases/pedc-u2-2026-09-21/scenario-proposal.md) |

## C. The one live Gemini run

| Claim | Grade | Figure or quote | File |
|---|---|---|---|
| Live judgment on real data | recorded-once | two calls, Vertex `gemini-3.8-flash`; trip/t1 challenges (9,743 in, 1,784 out, 11.1 s); return/t1 challenges (11,609 in, 1,776 out, 11.9 s); both stable | [live run](../grid-desk/live-run-2026-10-14.md) |
| Disagreement | unadjudicated | script composes supports at the return cutoff; Gemini answered Q2 `forced_outage` and composed challenges; issue #73, task EVAL-8 | same |
| Guard bypass | recorded | `LiveConfig` check lifted by subclass | same |
| "Retain" decision | contradiction | live run says the analyst's decision is retain; the case review records no disposition; only smoke-test judge flows clicked Retain | live run; review; [release record](../grid-desk/release-poc-2026-10-14.md) |

## D. Numerical models (reserve-deficiency onset, never price)

| Claim | Grade | Figure or quote | File |
|---|---|---|---|
| Label | inferred | shortfall > 1% for two consecutive intervals; "rule from the strategy docs" | `scripts/data/sql/08_labels_reserve.sql`, `03_ref_regions_thresholds.sql` |
| Thresholds | 23 rows, v1 | price cuts "chosen from the 2026-09 distribution"; "flag meaning unconfirmed" | `03_ref_regions_thresholds.sql` |
| Price series | built | capped median of generator-node LMP, band −10,000 to 32,000 | `04_interval_pricing.sql` |
| Boosted model, 1 h onset | measured | test AUC Visayas 0.914, Mindanao 0.950; climatology 0.89 and 0.88; one split, one seed | [training](../data-foundation/training.md) |
| Rolling folds | measured | positive in 4 of 5 | training |
| TabFM versus boosted | measured once | 0.947 vs 0.943, 0.967 vs 0.961; "statistically tied"; 35 and 33 positives | [timesfm-tabfm](../data-foundation/timesfm-tabfm.md) |
| TimesFM zero-shot | measured, negative | AUC 0.69 to 0.78; "not competitive"; price "not tried" | same |
| Earlier than NGCP | refuted | "The model does not warn earlier than NGCP"; 7 of 71 alert days earlier; ~40% of non-alert days flagged | [alert lead time](../data-foundation/alert-leadtime.md) |
| Alert-today signal | null | AUC differences not distinguishable from zero | same |
| Price forecasting | absent | no price model evaluated | — |

## E. Data coverage

| Item | Figure | File |
|---|---|---|
| Archive | 73 tables, 74 folders, about 24.9 GB, 1,389 files; ends 2026-09-29 (some tables 10-02) | [HANDOFF](../data-foundation/HANDOFF.md) |
| Regional summaries | missing 2024-11 to 2026-03 | HANDOFF |
| Reserve labels | 2026-03-26 to 2026-09-29 | HANDOFF |
| Registration | nothing 2024-10-26 to 2026-02-04 | foundation review source 02 |
| Timestamps | naive, Asia/Manila unverified | HANDOFF |
| Assets | no fuel, plant or location data in any folder; coordinates came separately 2026-10-15 | HANDOFF, ATG plan note |
| Feed | no live feed | HANDOFF |

## F. Rules corpus (CORP-0 to 5, all accepted 2026-10-16)

| Capability | Grade | Model call | Figure or quote | File |
|---|---|---|---|---|
| CORP-0 hand walk | recorded-once (fetches) | no | eight requests, seven 200, one 403 (ERC); "the October 2026 order itself is not in hand" | [spike](../corpus/spike-reserve-market.md) |
| CORP-3 extraction | built-unexercised | **no** | live refused `THINKING_NOT_CARRIED_BY_TRANSPORT` (G-1); prepare refused `PERMISSION_UNKNOWN` (G-3); only a replay of a stored synthetic response | [extraction](../corpus/extraction.md) |
| CORP-4 store | built-unexercised | no | "No BigQuery statement was executed or dry-run"; hash embeddings; five fictional documents | [store](../corpus/store.md) |
| CORP-5 case page | built, synthetic rows | no | seven clauses `not_placed` at both cutoffs; four announcements flip to placed; `synthetic: true`; dependents "none accepted" | [case](../corpus/case.md) |
| Reserve-market case | synthetic | no | action effective 0005H 14 October 2026; market data ends 2026-09-29; the dependent series is "referenced, not baked" | [outlook revision](../../cases/reserve-market/outlook-revision.md) |
| Corpus permission | absent | — | the signed record names WESM tables only; corpus families are not named | [permission](../permissions/2026-10-13-wesm-company-copy.md) |

## G. Other

| Claim | Grade | Figure or quote | File |
|---|---|---|---|
| What-if | designed-only | `consequences: uncomputed`; "Preview, directional" when run; never run | [what-if intent](../whatif/intent.md) |
| ATG pages | built, replay | 42 datasets, 618 asset profiles, 630-file bake; no model call; Gemini phrasing documented, not run | [ATG implementation](../atg/implementation.md) |
| Hosted performance | measured | cold start 6.2 to 6.7 s; first screen 0.86 s from Hosting; LCP 2.86 s ("under 2 s" not met) | [baseline](../performance/baseline.md) |
| Data rights | signed | `perm:wesm-company-copy:2026-10-13` v2: advisories, register, dispatch and prices, outage schedules, public replay display | permission record |
| Attribution of a miss (belief, signal, method) | built, unexercised (2026-10-17) | a record of its own beside the scoring receipt, content-keyed, with the CLI write path; real archive 0 attributions (no receipt exists), fixture demonstration 3 | [ARCH-4 intent](../outlook-archive/attribution-intent.md), [ARCH-4 record](../outlook-archive/attribution.md) |

## Numbers the thesis depends on that do not exist

1. Incidence of stale-assumption failures versus model error (none).
2. Any analyst-effect measure: time, missed issues, rework, traceability (none; EVAL-7 cut).
3. Live-model accuracy on any labelled set (two compiles, one disagreement, unadjudicated).
4. Bundle advantage over a single question (tie; test split favours the baseline).
5. Predictive value of the stability receipt (unidentified).
6. One real case traced evidence → assumption → decision → consequence (none complete).
7. One rule clause placed at a cutoff on real records (zero).
8. One computed consequence of a revised assumption (zero).
9. Any price skill (none evaluated).
10. Official status of the 23 thresholds and the reserve label (inferred).
11. Multi-regime generalisation (one test month, two regions).
