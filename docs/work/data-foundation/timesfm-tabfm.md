# TimesFM and TabFM in BigQuery: what they are, how we ran them, what we found

**2026-10-03 · Scripts:** `scripts/data/analysis/20_timesfm_backtest.sql`, `eval_timesfm.py`, `30_tabfm_predict.sql`, `31_tabfm_scores.sql`, `eval_tabfm.py`
· **Commands in order:** [RUNBOOK.md](RUNBOOK.md) steps 7 and 8 · **Models compared:** [training.md](training.md)

Both are pretrained models exposed as BigQuery SQL functions, so there is nothing to host. Facts below were observed by running them in project `grid-nowcast`, region `asia-southeast1`.

## In plain words

| | TimesFM | TabFM |
|---|---|---|
| What it does | Forecasts the next values of one number over time from its history | Predicts one column of a table from the other columns, learning from example rows you pass in the same query (no training step) |
| BigQuery function | `AI.FORECAST` (TimesFM 2.5 is GA) | `AI.PREDICT` (Preview) |
| We used it for | Forecasting the `Dr` reserve shortfall fraction, then scoring "will a deficiency start soon" from the forecast | Predicting `y_onset_1h` (a deficiency starts within the next hour) from the 17 grid-state features |

## TimesFM (`AI.FORECAST`)

**What we ran** (`20_timesfm_backtest.sql`): for each hourly forecast origin in September (Visayas and Mindanao) one series made of the previous 2,048 five-minute intervals of `dr_short_pct`
(the model sees nothing after the origin), horizon 36 (3 hours), `model => 'TimesFM 2.5'`, `context_window => 2048`, `id_cols => ['series_id']` where `series_id = region|origin`. All 1,152 series are forecast in **one call**.
The first argument can be a subquery. Origins whose 2,048-interval window contains a gap were skipped (2026-09-25 is missing from the reserve data), which left origins from 2026-09-01 to 2026-09-24.

**Observed:** 5-minute data is accepted; output columns `series_id`, `forecast_timestamp`, `forecast_value`, `prediction_interval_lower_bound`, `prediction_interval_upper_bound`, `confidence_level`, `ai_forecast_status`
(status was empty for every row); 41,472 forecast rows; 48 series took 9 seconds and all 1,152 took 2 minutes 19 seconds; **billed 20 MiB** in both cases (the two-table minimum), well inside the free tier.
Forecast values stayed between about -0.02 and 1.02.

**How it was scored** (`eval_timesfm.py`): the onset score at an origin is the maximum forecast shortfall over the next 12 steps (1 h) or 36 steps (3 h); compared by ROC AUC with the other models on the same origins,
with a day-block bootstrap for differences.

**Result:** zero-shot TimesFM is not competitive as an onset predictor. AUC for onset in the next hour: Visayas 0.688, Mindanao 0.737; for 3 hours 0.743 and 0.782. The hour-of-day baseline reaches 0.85-0.89 and the local
gradient-boosting model 0.93-0.96; blending the TimesFM score into the boosted model lowers it (AUC difference -0.03 to -0.08, intervals mostly exclude 0). Caveats: it forecasts a spiky, mostly-zero series from a 7-day window,
only one series (shortfall) was tried, no covariates (weather, outages) are used, and the origins are hourly over 24 days (33-35 onset positives per region at 1 h, 82-85 at 3 h).
Forecasts of other series (price, import share) and TimesFM 3.0 with covariates were not tried.

## TabFM (`AI.PREDICT`)

**What we ran** (`30_tabfm_predict.sql`): `AI.PREDICT(context_query, test_query, label_col => 'y')`. Context: a deterministic sample of 2,000 labeled rows from the train split (March-July) of both regions; test: the 744
hourly September origins that are not deficient now (the same origins as the TimesFM backtest). Inputs are the 17 features plus a throwaway `row_id` (0 in the context, 1..N in the test rows) so predictions can be joined back.
`31_tabfm_scores.sql` repeats the exact selection and order of the test rows to attach the interval and region.

**Observed:**
- It works in this project and region with no extra setup; subqueries are accepted; 18 input columns are fine (the reported cap of about 20 columns was not hit).
- Output keeps all input columns of the test rows and adds `predicted_y` (BOOLEAN) and `predicted_y_probs` (REPEATED RECORD of `label STRING`, `prob FLOAT`, for `"true"` and `"false"`): **class probabilities are returned**.
  Extra columns such as `row_id` pass through.
- A probe (300 context rows, 20 test rows) took 70 seconds; the 2,000 / 744 run took 54 seconds. Both **billed about 22 MB**, and the job statistics show no other charge. TabFM is in Preview and token-based pricing was reported to start
  2026-10-30 (unverified), so keep a byte cap on every call and re-check the billing console after 2026-10-30.

**Result** (`eval_tabfm.py`, same 744 origins, AUC for onset in the next hour, September):

| Region | TabFM (2,000-row context) | Local gradient boosting (36,827 training rows per region) | Hour-of-day model | TimesFM alone |
|---|---|---|---|---|
| Visayas | 0.947 | 0.943 | 0.888 | 0.688 |
| Mindanao | 0.967 | 0.961 | 0.869 | 0.737 |

TabFM minus boosted model: +0.004 [-0.022, +0.022] (Visayas), +0.006 [-0.009, +0.018] (Mindanao): statistically tied. TabFM minus hour-of-day model: +0.058 [+0.023, +0.091] and +0.098 [+0.065, +0.124]: significant.
Averaging the within-region ranks of TabFM and the boosted model gives a small gain over the boosted model alone (+0.015 [+0.002, +0.028] and +0.012 [+0.003, +0.022]).
Caveats: one run, one context sample (no repeats over different samples), only 35 and 33 onset positives per region over 24 days, the probabilities were not calibrated, and TabFM is Preview (behavior and price may change).

## Why this matters

- A model that sees only 2,000 example rows matches a boosted model trained on about 74,000, so TabFM is a credible way to build the classifier **inside BigQuery with no model to host**, which also counts as Google AI.
- Zero-shot forecasting of the shortfall series did not help; if forecasts are wanted, forecast price or import share, or use covariates, and test them as inputs to the classifier.
- Both are cheap in bytes (20-22 MB per call here); the open cost question is TabFM's Preview pricing after 2026-10-30.

## Next checks

1. Repeat TabFM with several context samples and sizes (500, 2,000, 5,000) and test whether it holds on August and on rolling folds.
2. Calibrate the probabilities (they feed any user-facing percentage).
3. Compare on the evening window with the day-block bootstrap, as for the boosted model.
4. TimesFM on price and import share, and as classifier inputs.
