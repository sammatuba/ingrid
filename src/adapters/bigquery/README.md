# BigQuery what-if adapter (NUM-1)

Renders the two `AI.FORECAST` statements of the what-if contract, validates the parameters, and
parses the engine rows into a per-step difference with fixed labels. Contract and limits:
[intent](../../../docs/work/whatif/intent.md) (working paper §5.6). This module holds no
credential, client, network or subprocess call: execution is NUM-3 behind GATE-3, through the
caller-supplied transport.

```python
from src.adapters.bigquery import build_covariate_path, render_statements, run_pair
path = build_covariate_path(proposal, series_id='CVIS', series_relation='p.d.t',
    anchor='2026-10-02T23:00:00', horizon=72, context_window=64)
prior, accepted = render_statements(path)     # byte-identical except one covariate literal
pair = run_pair(path, transport, observed_rows, execution_mode='synthetic fixture')
```

## What the two statements guarantee

One reviewed `ScenarioProposal` delta becomes two statements over one identical hourly history.
The horizon is exactly the disputed window `W`: `W` must begin at `H0+1`, and a longer requested
`N` is clipped to `N_eff` (`horizon_clipped: true`; the engine only ever sees `N_eff`). Path A
(`prior`) carries `L_old` on the future rows and path B (`accepted`) `L_new`; both carry the
constructed `L_new` on the context rows, so the two model inputs differ on one line only. Target
and past-covariate columns are NULL on future rows. The model literal is exactly `'TimesFM 3.0'`;
TimesFM 3.0 is reachable only through BigQuery `AI.FORECAST`, never by weights, endpoint or
substitute model.

## Limits and typed errors

| Parameter | Rule |
|---|---|
| `horizon` | integer 1…1,024 (requested `N` and effective `N_eff` both) |
| `context_window` | multiple of 32, 64…2,048 |
| `anchor` | the last complete context hour: minute and second are zero |
| field/unit | only `assumed_available_capacity`, quantity kind `assumed_available_capacity`, unit `MW` |
| time rule | stored civil time; a date-only bound is `T00:00:00`; the seconds field is optional (an omitted one is zero); an offset or zone name is refused |
| window | `W` begins at `H0+1`, else the result is uncomputed |

Every public reader (`render_statements`, `path_digest`, `covariate_basis`, `context_rows`,
`availability_summary`, `history_digest`, `parse_forecast_rows`, `run_pair`) revalidates a
`CovariatePath` exactly as `build_covariate_path` built it: both horizons as bounded integers, the
clipping flag as the clipping result, and the window `W` re-read as the horizon itself
(`N_eff` recomputed from `W`, `window_last_step` checked against `H0 + N_eff`). A hand-built path
can therefore neither render SQL outside `W` nor carry a receipt field the builder would not have
produced.

`parse_forecast_rows` additionally verifies its statement against the supplied path: call, role,
covariate level, SQL text and path digest must equal the canonical rendering of that path for
that call, so a statement rendered from another covariate path is refused
(`WHATIF_CONFIG_INVALID` at `$.statement.*`) instead of being combined with this path's receipt
fields.

## Context history and availability

The context window is the contiguous hourly run of `K` non-NULL rows ending at `H0`; a short,
gapped, unordered, NULL-target or future-hour row is `WHATIF_HISTORY`, and no row is ever filled
from another hour. A row whose `available_at` is later than `H0` — information the estate records
as known only after the cutoff — is refused the same way, at `$.context_rows[i].available_at`,
rather than entering the model history unflagged.

`availability_summary(observed, path)` is the receipt's `availability_basis` source, computed
over the same validated rows: any row whose availability is unknown makes the summary `unknown`
(so the history is not a strict known-then input), otherwise the recorded bases are summarised as
their sorted distinct values joined by `'; '`. `run_pair` copies the value onto both call
receipts; a caller that parses rows directly defaults to `unknown`, because an unvalidated series
cannot claim a known-then input. The pair is also refused (`WHATIF_RESULT_INCOMPATIBLE` at
`$.calls[].availability_basis`) if two calls somehow carry different summaries.

The anchor and `K` are parameters of this builder, which refuses a gap. The intent's walk-back
("the builder walks the anchor back and reduces `K` to the largest multiple of 32 that fits",
[intent](../../../docs/work/whatif/intent.md), series contract) is **not implemented in NUM-1**:
it needs the observed series, which the path builder does not take. NUM-3 selects the anchor and
`K` for a gapped series, or records the uncomputed fallback; the reading of "the builder" there
is recorded as a guardian question in the NUM-1 packet.

NUM-3 must supply `observed` as exactly the rows the relation returns under the statement's own
`context_rows` predicate (`hour_start` in `(H0 − K, H0]`) — the statement matches the intent's
template byte for byte and selects by `hour_start` alone. The late-known refusal above guards the
caller-supplied rows, not what the engine reads: a relation row with `hour_start <= H0` and
`available_at > H0` would make the engine's history differ from the validated, digested one. An
availability predicate in the SQL would be an intent revision, not a NUM-1 edit; the question is
recorded for the guardian in the NUM-1 packet.

`WhatIfError` carries the fixed code, the field path and the rule, and never partial SQL or a
number: `WHATIF_CONFIG_INVALID`, `WHATIF_HORIZON_RANGE`, `WHATIF_CONTEXT_WINDOW`,
`WHATIF_DELTA_FIELD`, `WHATIF_DELTA_WINDOW`, `WHATIF_HISTORY`, `WHATIF_HISTORY_MISMATCH`,
`WHATIF_RESULT_INCOMPATIBLE`. `uncomputed(error, execution_mode=…)` returns the fallback record
with `consequences: "uncomputed"` and its reason; the proposal's own frozen
`consequences: "uncomputed"` is never overwritten.

## Results, difference and labels

`parse_forecast_rows` accepts the `bq query --format=json` rows (a list of objects or its JSON
text) and returns the per-hour steps ordered by step; each receipt carries the relation it ran
over; `compare_calls` refuses an incompatible
pair (history digest, `N_eff`, requested `N`, context, resolution, model, units, series id and its
relation; two
identical paths) and otherwise returns the per-step difference `B − A` with `n_steps`,
`mean_delta_w` and `max_abs_delta`. The relation must agree even though the two model inputs are
equal: `history_digest` is over the rows and cannot separate two tables, so a pair built from two
relations would carry the one-identical-history verdict without a receipt field that reveals it
(`WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].series_relation`). Every result and receipt carries
`feature_status: "Preview"`, `interpretation: "directional"`, `content_kind: "simulation output"`,
one explicit `execution_mode`, the attenuation caveat and `consequences`.

A pair's `execution_mode` is the calls' own, never a caller's relabel: `compare_calls` refuses
(`WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].labels.execution_mode`) two calls of different modes,
a pair label that contradicts both calls, a call whose `steps` do not cover its `N_eff`, and a
`history_digest_value` or statement that is not the rendered, digested shape. A hand-built
`CallResult` therefore cannot pass off synthetic or stored inputs as a live inference.

The two paths are compared on the number the model receives, not on its spelling: the SQL literal
is cast to FLOAT64, so `0` and `0.0` are one covariate level and so are two different decimals
that land on one FLOAT64 (`0.1` and `0.1000000000000000000000001`); such a pair is refused as
identical (nothing to compare). The reviewed spelling is kept for provenance in
`prior_mw`/`accepted_mw`, the statement text and each call's `level_mw`, and a decimal with no
FLOAT64 value at all keeps its digits, so no limit the intent does not state is added. Every
derived difference and the mean must be finite: a subtraction or an aggregation that overflows two
finite forecasts is refused with its field path rather than reported as an infinity, and the mean
is computed overflow-safe (each difference is scaled before summing).

Every number taken from an input passes one guarded reader: the conversion is bounded before
finiteness is tested, so an arbitrarily large integer (which `math.isfinite` alone would turn into
an uncaught `OverflowError`) is the typed refusal of its own path — `WHATIF_HISTORY` at
`$.context_rows[i].price_php_mwh` for a context price, `WHATIF_RESULT_INCOMPATIBLE` at
`$.rows[i].price_php_mwh.<field>` for a forecast value or bound. `history_digest` revalidates each
row the same way (the five columns, the series id, finite numbers), so a hand-built row that would
otherwise fail inside canonical serialization is refused typed before anything is digested.

Not yet verified against the engine (S1/S3 resolve it; recorded in the intent): the exact target
STRUCT column name and the keyword spelling exceptions of the `AI.FORECAST` call. The parser
requires the target struct under `price_php_mwh` with `value`,
`prediction_interval_lower_bound`, `prediction_interval_upper_bound` and an empty
`ai_forecast_status`, and refuses anything else with a reason. Further engine-shape
assumptions NUM-3 must confirm against the recorded result: `_hour` strips a trailing ` UTC` or
`Z` from `forecast_timestamp` on the assumption that BigQuery echoes the zone-less
`TIMESTAMP '<H0>'` literal as UTC text, so no conversion occurs; the model-literal check only
fires when a row actually carries a `model` key; a level whose literal shape is beyond the
FLOAT64/INT64 range — a decimal with no finite FLOAT64 value, or an integer spelling of 20+
digits with no decimal point — is admitted by `build_covariate_path`, `render_statements` and
`path_digest` and rendered as an unquoted literal whose GoogleSQL acceptance is unverified,
because the intent's limit is "finite decimal" and no numeric range is added; but such a level can
never be the FLOAT64 model input the statement casts, so a run refuses it typed (`WHATIF_CONFIG_INVALID`
at `$.accepted_mw`, from `context_rows`, `availability_summary` and `run_pair`) instead of letting
an infinity into the constructed context rows and their digest; and the level unification
assumes BigQuery's literal-to-FLOAT64 conversion rounds as Python's `float()` does (both IEEE
round-to-nearest-even).

## Verification

```sh
/usr/bin/python3 -m unittest tests.test_whatif -v
```

`fixtures/whatif_statements.json` is the golden rendering for both calls: the boundary example of
the intent (date-only 2026-10-03 to 2026-10-05, `H0` 2026-10-02T23:00:00, `N` 72 clipped to
`N_eff` 48, `K` 64) with synthetic placeholder series and levels — no registered case value and
no engine run.
