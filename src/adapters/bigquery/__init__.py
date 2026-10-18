"""BigQuery adapter: ``AI.FORECAST`` what-if SQL text and result parsing.

No credential, client, network or subprocess call lives here. Execution is NUM-3 behind GATE-3,
through the caller-supplied transport in :func:`src.adapters.bigquery.whatif.run_pair`. Contract
and limits: ``docs/work/whatif/intent.md``.
"""
from .whatif import (ACCEPTED_FIELD, ACCEPTED_UNIT, AVAILABILITY_UNKNOWN, CAVEAT, CALLS, CODES,
    CONFIDENCE_LEVEL, CONTEXT_COLUMNS, CONTEXT_MAX, CONTEXT_MIN, CONTEXT_STEP, COVARIATE_COLUMN,
    COVARIATE_PAST_BASIS, COVARIATE_UNIT, CallResult, CovariatePath, EXECUTION_MODES, HORIZON_MAX,
    HORIZON_MIN, MODEL, PAST_COVARIATE_COLUMN, PairResult, RESOLUTION, SERIES_COLUMNS, STRUCT_FIELDS,
    Statement, StepDifference, StepForecast, TARGET_COLUMN, TARGET_UNIT, TIMEZONE_CONVENTION,
    WhatIfError, availability_summary, build_covariate_path, compare_calls, context_rows,
    covariate_basis, history_digest, labels, parse_forecast_rows, path_digest, render_statements,
    run_pair, uncomputed)

__all__ = ['ACCEPTED_FIELD', 'ACCEPTED_UNIT', 'AVAILABILITY_UNKNOWN', 'CAVEAT', 'CALLS', 'CODES',
    'CONFIDENCE_LEVEL',
    'CONTEXT_COLUMNS', 'CONTEXT_MAX', 'CONTEXT_MIN', 'CONTEXT_STEP', 'COVARIATE_COLUMN',
    'COVARIATE_PAST_BASIS', 'COVARIATE_UNIT', 'CallResult', 'CovariatePath', 'EXECUTION_MODES',
    'HORIZON_MAX', 'HORIZON_MIN', 'MODEL', 'PAST_COVARIATE_COLUMN', 'PairResult', 'RESOLUTION',
    'SERIES_COLUMNS', 'STRUCT_FIELDS', 'Statement', 'StepDifference', 'StepForecast',
    'TARGET_COLUMN', 'TARGET_UNIT', 'TIMEZONE_CONVENTION', 'WhatIfError', 'availability_summary',
    'build_covariate_path', 'compare_calls', 'context_rows', 'covariate_basis', 'history_digest',
    'labels', 'parse_forecast_rows', 'path_digest', 'render_statements', 'run_pair', 'uncomputed']
