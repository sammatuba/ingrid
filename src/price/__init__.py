"""The price outlook baselines: exported series, baselines by rolling origin, scorecard.

Modules are imported explicitly, so the package marker carries no re-exports and
adding one cannot disturb another module:

* :mod:`src.price.series` — the PRICE-1 export (hourly rows, the billing-month
  clock, the marks: absent and short months, irregular days, administered
  pricing) and the digest check that ties a run to the exported bytes.
* :mod:`src.price.baselines` — the rolling-origin windows and the three
  baselines: persistence, last week same interval, seasonal average by billing
  month (PRICE-2, plan note: ``docs/work/price-outlook/intent.md``).
* :mod:`src.price.scorecard` — the day/week/month scorecard: bias, MAE, RMSE and
  pinball at p10/p50/p90 per series and horizon, with every excluded origin
  counted under a reason.
* :mod:`src.price.challengers` — PRICE-3: the ridge and boosted-tree
  challengers, their blocked walk-forward with the embargo, and the gate that
  only lets a challenger claim skill on an out-of-sample gain with stable
  calibration.
* :mod:`src.price.impact` — the synthetic portfolio priced against a node's
  outlook band and contract price, per horizon, with the materiality line stated
  before any change is scored (IMPACT-1).

Standard library only, as the PRICE-2 and PRICE-3 briefs require. No price value, node name
of the retailer's portfolio or portfolio volume lives in this repository: the
series are read from the exported files under the ignored ``.local/price/``.
"""
