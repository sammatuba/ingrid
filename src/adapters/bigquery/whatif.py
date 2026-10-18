"""BigQuery ``AI.FORECAST`` what-if contract: covariate path, SQL text, parser and labels.

Contract: ``docs/work/whatif/intent.md`` (SQL contract, limits, result parser, labels). One
reviewed h0.v1 ``ScenarioProposal`` delta becomes two statements over one identical hourly
history. They differ exactly on the disputed window ``W``: call ``A`` (``prior``) carries
``L_old`` on the future rows, call ``B`` (``accepted``) carries ``L_new``; the context rows carry
the constructed ``L_new`` in both, so the two model inputs differ only on ``W``.

Trust boundary
==============
This module renders SQL text from validated literals and parses result rows. It holds no
credential, opens no connection and performs no network, subprocess or file call. The only
execution seam is the caller-supplied ``transport`` in :func:`run_pair`; wiring it to BigQuery is
NUM-3 behind GATE-3. TimesFM 3.0 is reachable only through BigQuery ``AI.FORECAST``: no weights,
Vertex endpoint or substitute model is imported or permitted here.

Every refusal raises :class:`WhatIfError` carrying the fixed code, the field path and the rule.
A refusal never returns partial SQL or a number.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import math
import re

from src.contracts.jsonutil import canonical_bytes, parse_json

#: The only permitted model, and only through BigQuery AI.FORECAST.
MODEL = 'TimesFM 3.0'
CONFIDENCE_LEVEL = 0.95
HORIZON_MIN, HORIZON_MAX = 1, 1024
CONTEXT_MIN, CONTEXT_MAX, CONTEXT_STEP = 64, 2048, 32

#: Recorded, never promoted to a fact: the estate SQL only suggests the zone.
TIMEZONE_CONVENTION = 'assumed Asia/Manila, unverified (scripts/data/sql/02_intervals.sql:2-3)'
#: The context covariate is constructed, not observed and not an accepted assumption.
COVARIATE_PAST_BASIS = 'constructed: level held constant; not observed, not an accepted assumption'

ACCEPTED_FIELD = 'assumed_available_capacity'
ACCEPTED_UNIT = 'MW'
TARGET_COLUMN = 'price_php_mwh'
PAST_COVARIATE_COLUMN = 'n_resources_out_hour'
COVARIATE_COLUMN = 'assumed_available_capacity_mw'
TARGET_UNIT = 'PHP/MWh'
COVARIATE_UNIT = 'MW'
RESOLUTION = 'hourly'
#: The availability summary the receipt carries when any context row's basis is unknown.
AVAILABILITY_UNKNOWN = 'unknown'

CALLS = (('A', 'prior'), ('B', 'accepted'))
CALL_ROLES = dict(CALLS)
EXECUTION_MODES = ('live inference', 'stored run', 'retrospective replay', 'synthetic fixture')
CAVEAT = ('preview feature; default covariate interfaces can attenuate or ignore covariate '
    'effects; not a measured real-world effect; never an event probability')

SERIES_ID = re.compile(r'^[A-Z][A-Z0-9_]{0,15}$')
RELATION = re.compile(r'^[a-z][a-z0-9-]{4,62}(?:\.[A-Za-z_][A-Za-z0-9_]*){2}$')
CIVIL = re.compile(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$')
DATE_ONLY = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')
DECIMAL = re.compile(r'^[+-]?\d+(?:\.\d+)?$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')

CODES = frozenset({'WHATIF_CONFIG_INVALID', 'WHATIF_HORIZON_RANGE', 'WHATIF_CONTEXT_WINDOW',
    'WHATIF_DELTA_FIELD', 'WHATIF_DELTA_WINDOW', 'WHATIF_HISTORY', 'WHATIF_HISTORY_MISMATCH',
    'WHATIF_RESULT_INCOMPATIBLE'})

#: Columns the model input carries, in the order the statement renders them.
CONTEXT_COLUMNS = ('series_id', 'hour_start', TARGET_COLUMN, PAST_COVARIATE_COLUMN, COVARIATE_COLUMN)
#: Series columns accepted from the relation; the availability pair is carried, never filled.
SERIES_COLUMNS = frozenset({'hour_start', 'region_code', TARGET_COLUMN, PAST_COVARIATE_COLUMN,
    'available_at', 'availability_basis'})
#: Fields the engine's target STRUCT must carry for a usable step.
STRUCT_FIELDS = ('value', 'prediction_interval_lower_bound', 'prediction_interval_upper_bound',
    'ai_forecast_status')


class WhatIfError(Exception):
    """Expected, typed refusal: fixed code, field path and rule; never partial SQL."""

    def __init__(self, code, field_path, rule):
        if code not in CODES:
            raise ValueError('unknown what-if code')
        self.code = code
        self.field_path = field_path
        self.rule = rule
        super().__init__(f'{code} at {field_path}: {rule}')

    def as_dict(self):
        return {'code': self.code, 'field_path': self.field_path, 'rule': self.rule}


def _fail(code, field_path, rule):
    raise WhatIfError(code, field_path, rule)


def _whole_hour(parsed, field_path, rule):
    """The anchor is the last *complete* context hour; a :30/:59 anchor is refused."""
    if (parsed.minute, parsed.second) != (0, 0):
        _fail('WHATIF_CONFIG_INVALID', field_path, rule)


def _civil(value, field_path, code='WHATIF_CONFIG_INVALID',
        rule='civil timestamp text without an offset or zone name'):
    """Normalize one timestamp into the stored civil space; offsets and zones are refused."""
    if type(value) is not str:
        _fail(code, field_path, rule)
    text = value + 'T00:00:00' if DATE_ONLY.fullmatch(value) else value
    match = CIVIL.fullmatch(text)
    if match is None:
        _fail(code, field_path, rule)
    # The seconds field is optional in the civil form; an omitted one is zero.
    parts = [int(part or 0) for part in match.groups()]
    try:
        parsed = datetime(*parts)
    except ValueError:
        _fail(code, field_path, rule)
    return parsed, parsed.strftime('%Y-%m-%dT%H:%M:%S')


def _hour(value, field_path):
    """Normalize one engine timestamp to the requested civil hour; a shifting offset is refused."""
    rule = 'forecast_timestamp repeats the requested civil hourly grid'
    if type(value) is not str:
        _fail('WHATIF_RESULT_INCOMPATIBLE', field_path, rule)
    text = value.strip()
    text = text[:-4] if text.endswith(' UTC') else (text[:-1] if text.endswith('Z') else text)
    try:
        return _civil(text.strip().replace(' ', 'T'), field_path,
            'WHATIF_RESULT_INCOMPATIBLE', rule)[1]
    except WhatIfError:
        raise WhatIfError('WHATIF_RESULT_INCOMPATIBLE', field_path, rule) from None


def _decimal(value, field_path, code='WHATIF_CONFIG_INVALID'):
    """Validate a finite decimal literal and return it as (number, render text)."""
    rule = 'finite decimal value'
    if type(value) is not str or DECIMAL.fullmatch(value) is None:
        _fail(code, field_path, rule)
    try:
        number = Decimal(value)
    except InvalidOperation:
        _fail(code, field_path, rule)
    if not number.is_finite():
        _fail(code, field_path, rule)
    return number, (value[1:] if value.startswith('+') else value)


def _canonical_level(text):
    """One covariate level as one canonical numeric text: the FLOAT64 value, not its spelling.

    The model receives the number the statement's literal casts to FLOAT64, so ``100``, ``100.0``
    and ``+100`` are one model input and one path — and so are two different decimals that land on
    one FLOAT64 (``0.1`` and ``0.1000000000000000000000001``), because the cast hands the model
    the same number. The reviewed spelling stays for provenance in ``prior_mw``/``accepted_mw``,
    the statement text and the call receipt. A decimal with no finite FLOAT64 value (beyond the
    type's range) keeps its normalized digits: there is no float to unify on there, and no limit
    the intent does not state is invented for it.
    """
    number = Decimal(text).normalize()
    if number == 0:
        return '0'                       # '0', '0.0', '00' and '-0' are one level
    try:
        as_float = float(number)
    except (OverflowError, ValueError):
        return format(number, 'f')
    if not math.isfinite(as_float):
        return format(number, 'f')
    return format(as_float, '.17g')      # 17 significant digits name one FLOAT64 exactly


def _count(value, field_path, code, rule):
    if type(value) is not int:
        _fail(code, field_path, rule)
    return value


def _finite_number(value, field_path, code='WHATIF_RESULT_INCOMPATIBLE', rule='a finite numeric value'):
    """A finite float from a parsed value; a huge integer is refused, not converted blindly.

    ``math.isfinite`` converts its argument to float, so an arbitrarily large ``int`` — which the
    type check alone admits — would raise an uncaught ``OverflowError`` before the check. The
    conversion is guarded here, so every numeric escape is the caller's typed refusal (code, field
    path and rule) rather than an interpreter exception.
    """
    if type(value) not in (int, float):
        _fail(code, field_path, rule)
    try:
        number = float(value)
    except OverflowError:
        _fail(code, field_path, rule)
    if not math.isfinite(number):
        _fail(code, field_path, rule)
    return number


def _constructed_level(path):
    """The constructed covariate as the FLOAT64 model input the statement casts.

    The delta level is a finite decimal (the intent's limit) and keeps its spelling in
    ``prior_mw``/``accepted_mw``, the SQL literal and the call receipt; but the input row the model
    receives is ``CAST(<L_new> AS FLOAT64)``. A level with no finite FLOAT64 value therefore cannot
    be a model input and is refused here — typed, at the level itself — rather than becoming an
    infinity in the context rows, whose digest covers the numbers the model actually receives.
    """
    rule = 'the constructed covariate the model input carries: a level with a finite FLOAT64 value'
    try:
        level = float(Decimal(path.accepted_mw))
    except (ArithmeticError, OverflowError, ValueError):
        _fail('WHATIF_CONFIG_INVALID', '$.accepted_mw', rule)
    if not math.isfinite(level):
        _fail('WHATIF_CONFIG_INVALID', '$.accepted_mw', rule)
    return level


def _ref_digest(payload, name, field_path):
    ref = payload.get(name)
    if type(ref) is not dict or type(ref.get('content_digest')) is not str \
            or DIGEST.fullmatch(ref['content_digest']) is None:
        _fail('WHATIF_CONFIG_INVALID', field_path, f'{name} reference with a SHA-256 content_digest')
    return ref['content_digest']


def _digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class CovariatePath:
    """The reviewed delta as a covariate path: levels, disputed window ``W`` and clipping."""

    series_id: str
    series_relation: str
    h0: str
    context_window: int
    horizon_requested: int
    horizon_effective: int
    horizon_clipped: bool
    window_start: str
    window_end: str
    window_last_step: str
    prior_mw: str
    accepted_mw: str
    delta_refs: dict

    def level_for(self, call):
        return self.prior_mw if call == 'A' else self.accepted_mw

    def as_dict(self):
        return {'series_id': self.series_id, 'series_relation': self.series_relation, 'h0': self.h0,
            'context_window': self.context_window, 'horizon_requested': self.horizon_requested,
            'horizon_effective': self.horizon_effective, 'horizon_clipped': self.horizon_clipped,
            'window': {'start': self.window_start, 'end': self.window_end},
            'window_last_step': self.window_last_step, 'prior_mw': self.prior_mw,
            'accepted_mw': self.accepted_mw, 'timezone_convention': TIMEZONE_CONVENTION,
            'covariate_past_basis': COVARIATE_PAST_BASIS, 'model': MODEL,
            'delta_refs': self.delta_refs}


def _step_text(h0_datetime, step):
    return (h0_datetime + timedelta(hours=step)).strftime('%Y-%m-%dT%H:%M:%S')


def build_covariate_path(proposal, *, series_id, series_relation, anchor, horizon, context_window):
    """Turn a reviewed ``ScenarioProposal`` record into a validated covariate path.

    The forecast horizon is exactly ``W``: ``W`` must begin at ``H0+1``, a longer requested
    horizon is clipped to ``N_eff`` with ``horizon_clipped: true``, and any other shape is
    ``WHATIF_DELTA_WINDOW``. No covariate level is extrapolated past ``W``'s end or into the
    context.
    """
    record_rule = 'h0.v1 ScenarioProposal record'
    if type(proposal) is not dict or proposal.get('record_kind') != 'ScenarioProposal':
        _fail('WHATIF_CONFIG_INVALID', '$.record_kind', record_rule)
    payload = proposal.get('payload')
    if type(payload) is not dict:
        _fail('WHATIF_CONFIG_INVALID', '$.payload', record_rule)
    proposal_digest = proposal.get('content_digest')
    if type(proposal_digest) is not str or DIGEST.fullmatch(proposal_digest) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.content_digest', 'lowercase SHA-256 content digest')
    if (payload.get('execution'), payload.get('comparison'),
            payload.get('consequences')) != ('proposal_only', 'pending_outputs', 'uncomputed'):
        _fail('WHATIF_CONFIG_INVALID', '$.payload.execution',
            'the what-if reads an unmutated proposal_only / pending_outputs / uncomputed proposal')
    delta = payload.get('delta')
    if type(delta) is not dict:
        _fail('WHATIF_CONFIG_INVALID', '$.payload.delta', 'reviewed ScenarioProposal delta')

    # The only accepted numerical field, quantity kind and unit in v1; nothing is converted.
    if delta.get('input_field') != ACCEPTED_FIELD:
        _fail('WHATIF_DELTA_FIELD', '$.payload.delta.input_field',
            f"the only accepted input_field is '{ACCEPTED_FIELD}'")
    quantities = {}
    for name in ('old_value', 'new_value'):
        quantity = delta.get(name)
        if type(quantity) is not dict:
            _fail('WHATIF_CONFIG_INVALID', f'$.payload.delta.{name}', 'quantity with value, quantity_kind, unit')
        if quantity.get('quantity_kind') != ACCEPTED_FIELD or quantity.get('unit') != ACCEPTED_UNIT:
            _fail('WHATIF_DELTA_FIELD', f'$.payload.delta.{name}.unit',
                f"the only accepted quantity kind and unit are '{ACCEPTED_FIELD}' / '{ACCEPTED_UNIT}' MW")
        quantities[name] = quantity
    # The numeric value is validated; the statement renders the validated decimal text.
    _, prior_mw = _decimal(quantities['old_value'].get('value'), '$.payload.delta.old_value.value')
    _, accepted_mw = _decimal(quantities['new_value'].get('value'), '$.payload.delta.new_value.value')

    if type(series_id) is not str or SERIES_ID.fullmatch(series_id) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.series_id', "series id matching ^[A-Z][A-Z0-9_]{0,15}$")
    if type(series_relation) is not str or RELATION.fullmatch(series_relation) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.series_relation', 'project.dataset.table relation')
    h0_datetime, h0 = _civil(anchor, '$.anchor')
    _whole_hour(h0_datetime, '$.anchor',
        'the last complete context hour: minute and second are zero')
    if type(horizon) is not int or not HORIZON_MIN <= horizon <= HORIZON_MAX:
        _fail('WHATIF_HORIZON_RANGE', '$.horizon', 'integer horizon from 1 to 1,024 (AI.FORECAST reference)')
    if type(context_window) is not int or not CONTEXT_MIN <= context_window <= CONTEXT_MAX \
            or context_window % CONTEXT_STEP:
        _fail('WHATIF_CONTEXT_WINDOW', '$.context_window',
            'context window is a multiple of 32 from 64 to 2,048')

    period = delta.get('valid_period')
    if type(period) is not dict or set(period) != {'start', 'end'}:
        _fail('WHATIF_CONFIG_INVALID', '$.payload.delta.valid_period', 'valid_period with start and end')
    start_datetime, start = _civil(period['start'], '$.payload.delta.valid_period.start')
    end_datetime, end = _civil(period['end'], '$.payload.delta.valid_period.end')
    if not start_datetime < end_datetime:
        _fail('WHATIF_CONFIG_INVALID', '$.payload.delta.valid_period', 'start before end')
    first_step = h0_datetime + timedelta(hours=1)
    if not start_datetime <= first_step < end_datetime:
        _fail('WHATIF_DELTA_WINDOW', '$.payload.delta.valid_period',
            'W begins at H0+1; a window that does not shape this horizon is uncomputed')
    steps = 0
    for step in range(1, horizon + 1):
        if h0_datetime + timedelta(hours=step) >= end_datetime:
            break
        steps += 1
    horizon_clipped = steps < horizon
    delta_refs = {'proposal_content_digest': proposal_digest,
        'decision_content_digest': _ref_digest(payload, 'decision_ref', '$.payload.decision_ref'),
        'old_assumption_content_digest': _ref_digest(payload, 'old_assumption_ref',
            '$.payload.old_assumption_ref'),
        'new_assumption_content_digest': _ref_digest(payload, 'new_assumption_ref',
            '$.payload.new_assumption_ref'),
        'mapping_content_digest': _ref_digest(payload, 'mapping_ref', '$.payload.mapping_ref'),
        'input_field': ACCEPTED_FIELD, 'quantity_kind': ACCEPTED_FIELD, 'unit': ACCEPTED_UNIT,
        'old_value': prior_mw, 'new_value': accepted_mw,
        'valid_period': {'start': start, 'end': end}}
    return CovariatePath(series_id=series_id, series_relation=series_relation, h0=h0,
        context_window=context_window, horizon_requested=horizon, horizon_effective=steps,
        horizon_clipped=horizon_clipped, window_start=start, window_end=end,
        window_last_step=_step_text(h0_datetime, steps), prior_mw=prior_mw, accepted_mw=accepted_mw,
        delta_refs=delta_refs)


@dataclass(frozen=True)
class Statement:
    """One rendered ``AI.FORECAST`` statement and the path it descends from."""

    call: str
    role: str
    level_mw: str
    sql: str
    path_digest: str

    @property
    def statement_digest(self):
        return hashlib.sha256(self.sql.encode('utf-8')).hexdigest()


def _check_path(path):
    """Re-validate every literal before it reaches SQL text, exactly as the builder built it.

    Both horizons are bounded integers, the clipping flag is the clipping result, and the
    window ``W`` is re-read as the horizon itself: a hand-built path can neither render SQL
    outside ``W`` nor carry a receipt field the builder would not have produced.
    """
    if type(path) is not CovariatePath:
        _fail('WHATIF_CONFIG_INVALID', '$.path', 'CovariatePath from build_covariate_path')
    if type(path.series_id) is not str or SERIES_ID.fullmatch(path.series_id) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.series_id', 'validated series id')
    if type(path.series_relation) is not str or RELATION.fullmatch(path.series_relation) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.series_relation', 'validated project.dataset.table relation')
    h0_datetime, _ = _civil(path.h0, '$.h0')
    _whole_hour(h0_datetime, '$.h0',
        'the last complete context hour: minute and second are zero')
    start_datetime, _ = _civil(path.window_start, '$.window.start')
    end_datetime, _ = _civil(path.window_end, '$.window.end')
    _civil(path.window_last_step, '$.window_last_step')
    _decimal(path.prior_mw, '$.prior_mw')
    _decimal(path.accepted_mw, '$.accepted_mw')
    _count(path.context_window, '$.context_window', 'WHATIF_CONTEXT_WINDOW',
        'context window is a multiple of 32 from 64 to 2,048')
    if not CONTEXT_MIN <= path.context_window <= CONTEXT_MAX or path.context_window % CONTEXT_STEP:
        _fail('WHATIF_CONTEXT_WINDOW', '$.context_window',
            'context window is a multiple of 32 from 64 to 2,048')
    _count(path.horizon_requested, '$.horizon_requested', 'WHATIF_HORIZON_RANGE',
        'integer horizon from 1 to 1,024 (AI.FORECAST reference)')
    if not HORIZON_MIN <= path.horizon_requested <= HORIZON_MAX:
        _fail('WHATIF_HORIZON_RANGE', '$.horizon_requested',
            'integer horizon from 1 to 1,024 (AI.FORECAST reference)')
    _count(path.horizon_effective, '$.horizon_effective', 'WHATIF_HORIZON_RANGE',
        'integer effective horizon from 1 to the requested horizon')
    if not HORIZON_MIN <= path.horizon_effective <= path.horizon_requested:
        _fail('WHATIF_HORIZON_RANGE', '$.horizon_effective',
            'integer effective horizon from 1 to the requested horizon')
    if type(path.horizon_clipped) is not bool \
            or path.horizon_clipped != (path.horizon_effective < path.horizon_requested):
        _fail('WHATIF_CONFIG_INVALID', '$.horizon_clipped',
            'clipping is true exactly when the effective horizon is shorter than the requested one')
    # The horizon is exactly W: recompute the steps W shapes and check the rendered last step.
    if not start_datetime <= h0_datetime + timedelta(hours=1) < end_datetime:
        _fail('WHATIF_DELTA_WINDOW', '$.window',
            'W begins at H0+1; a window that does not shape this horizon is uncomputed')
    steps = sum(1 for step in range(1, path.horizon_requested + 1)
        if h0_datetime + timedelta(hours=step) < end_datetime)
    if steps != path.horizon_effective:
        _fail('WHATIF_DELTA_WINDOW', '$.horizon_effective',
            f'the horizon is exactly W: {steps} of the requested steps lie inside the window')
    if path.window_last_step != _step_text(h0_datetime, path.horizon_effective):
        _fail('WHATIF_CONFIG_INVALID', '$.window_last_step',
            'the last step inside W: H0 plus N_eff hours')


def _statement_sql(path, level_mw):
    return (
        "WITH context_rows AS (\n"
        f"  SELECT '{path.series_id}' AS series_id, hour_start, {TARGET_COLUMN},\n"
        f"         {PAST_COVARIATE_COLUMN}, CAST({path.accepted_mw} AS FLOAT64) AS {COVARIATE_COLUMN}\n"
        f"  FROM `{path.series_relation}`\n"
        f"  WHERE hour_start > TIMESTAMP_SUB(TIMESTAMP '{path.h0}', INTERVAL {path.context_window} HOUR)\n"
        f"    AND hour_start <= TIMESTAMP '{path.h0}'\n"
        "), future_rows AS (\n"
        f"  SELECT '{path.series_id}' AS series_id, hour_start, CAST(NULL AS FLOAT64) AS {TARGET_COLUMN},\n"
        f"         CAST(NULL AS INT64) AS {PAST_COVARIATE_COLUMN},\n"
        f"         CAST({level_mw} AS FLOAT64) AS {COVARIATE_COLUMN}\n"
        f"  FROM UNNEST(GENERATE_TIMESTAMP_ARRAY(TIMESTAMP_ADD(TIMESTAMP '{path.h0}', INTERVAL 1 HOUR),\n"
        f"        TIMESTAMP_ADD(TIMESTAMP '{path.h0}', INTERVAL {path.horizon_effective} HOUR), INTERVAL 1 HOUR)) AS hour_start\n"
        "), model_input AS (\n"
        "  SELECT * FROM context_rows UNION ALL SELECT * FROM future_rows\n"
        ")\n"
        "SELECT *\n"
        "FROM AI.FORECAST((SELECT * FROM model_input),\n"
        f"  target_cols => ['{TARGET_COLUMN}'], timestamp_col => 'hour_start', id_cols => ['series_id'],\n"
        f"  model => '{MODEL}', horizon => {path.horizon_effective}, context_window => {path.context_window}, confidence_level => {CONFIDENCE_LEVEL},\n"
        f"  past_covariate_cols => ['{PAST_COVARIATE_COLUMN}'],\n"
        f"  future_covariate_cols => ['{COVARIATE_COLUMN}']);\n")


def path_digest(path, call):
    """SHA-256 over the per-call path: window, N, N_eff, clipping and the call's level.

    The two calls share every entry but their covariate level, so equal digests mean the two
    paths are the same path and there is nothing to compare. The level is digested numerically
    (``_canonical_level``), because the model receives the value, not its spelling: ``0`` and
    ``0.0`` are one input, and two call receipts must not claim different paths for one model
    history. The path is revalidated first, so an inconsistent path is refused instead of being
    digested.
    """
    _check_path(path)
    if call not in CALL_ROLES:
        _fail('WHATIF_CONFIG_INVALID', '$.path.call', "call is 'A' (prior) or 'B' (accepted)")
    return _digest({'series_id': path.series_id, 'series_relation': path.series_relation,
        'h0': path.h0, 'context_window': path.context_window,
        'horizon_requested': path.horizon_requested, 'horizon_effective': path.horizon_effective,
        'horizon_clipped': path.horizon_clipped, 'window_start': path.window_start,
        'window_end': path.window_end, 'level_mw': _canonical_level(path.level_for(call))})


def render_statements(path):
    """Render the two statements; only the future-covariate literal differs between them."""
    _check_path(path)
    out = []
    for call, role in CALLS:
        out.append(Statement(call=call, role=role, level_mw=path.level_for(call),
            sql=_statement_sql(path, path.level_for(call)), path_digest=path_digest(path, call)))
    return tuple(out)


def covariate_basis(path):
    """The receipt's constructed/accepted split; the constructed level is never an assumption."""
    _check_path(path)
    return {'accepted_levels': {'prior_mw': path.prior_mw, 'accepted_mw': path.accepted_mw},
        'context_level_mw': path.accepted_mw, 'covariate_past_basis': COVARIATE_PAST_BASIS}


def _series_rows(observed, path):
    """Validate the observed series rows once; return (model rows, availability labels).

    A row is known-then only when it records an ``available_at`` at or before ``H0``; a row
    whose information the estate records as known only after the cutoff is refused rather than
    silently dropped, so late-known data can never enter the model history unflagged. The
    availability pair is never filled: an unrecorded availability stays ``unknown``.
    """
    _check_path(path)
    if type(observed) not in (list, tuple):
        _fail('WHATIF_HISTORY', '$.context_rows', 'the observed series rows as a list')
    if len(observed) != path.context_window:
        _fail('WHATIF_HISTORY', '$.context_rows',
            f'the context window is the latest run of {path.context_window} consecutive non-NULL hours ending at H0')
    h0_datetime, _ = _civil(path.h0, '$.h0')
    level = _constructed_level(path)
    rows, labels = [], []
    for index, raw in enumerate(observed):
        where = f'$.context_rows[{index}]'
        if type(raw) is not dict:
            _fail('WHATIF_HISTORY', where, 'one observed series row object')
        unknown = sorted(set(raw) - SERIES_COLUMNS)
        if unknown:
            _fail('WHATIF_HISTORY', where, f'unexpected column {unknown[0]}')
        for name in ('hour_start', TARGET_COLUMN, PAST_COVARIATE_COLUMN):
            if name not in raw:
                _fail('WHATIF_HISTORY', f'{where}.{name}', 'required series column')
        expected = _step_text(h0_datetime, index + 1 - path.context_window)
        _, hour = _civil(raw['hour_start'], f'{where}.hour_start', 'WHATIF_HISTORY',
            'civil timestamp text without an offset or zone name')
        if hour != expected:
            _fail('WHATIF_HISTORY', f'{where}.hour_start',
                f'contiguous hourly context ending at H0; expected {expected}')
        if raw.get('region_code') is not None and raw['region_code'] != path.series_id:
            _fail('WHATIF_HISTORY', f'{where}.region_code', f'the series is one region ({path.series_id})')
        price = _finite_number(raw[TARGET_COLUMN], f'{where}.{TARGET_COLUMN}', 'WHATIF_HISTORY',
            'non-NULL finite target value')
        out_hours = raw[PAST_COVARIATE_COLUMN]
        if type(out_hours) is not int:
            _fail('WHATIF_HISTORY', f'{where}.{PAST_COVARIATE_COLUMN}', 'non-NULL integer count')
        label = AVAILABILITY_UNKNOWN
        if raw.get('available_at') is not None:
            available_at, _ = _civil(raw['available_at'], f'{where}.available_at', 'WHATIF_HISTORY',
                'civil timestamp text without an offset or zone name')
            if type(raw.get('availability_basis')) is not str or not raw['availability_basis'].strip():
                _fail('WHATIF_HISTORY', f'{where}.availability_basis',
                    'a known availability time records its basis; unknown stays unknown')
            if available_at > h0_datetime:
                _fail('WHATIF_HISTORY', f'{where}.available_at',
                    'known at or before the cutoff H0; a row known only later cannot inform the '
                    'model history')
            label = raw['availability_basis'].strip()
        rows.append({'series_id': path.series_id, 'hour_start': hour, TARGET_COLUMN: price,
            PAST_COVARIATE_COLUMN: out_hours, COVARIATE_COLUMN: level})
        labels.append(label)
    return rows, labels


def context_rows(observed, path):
    """Build the ordered model-input context rows from the series relation's observed rows.

    The context window is the contiguous hourly run of ``K`` rows ending at ``H0``; shorter,
    gapped, unordered, NULL-target rows or a row known only after ``H0`` are ``WHATIF_HISTORY``.
    The constructed ``assumed_available_capacity_mw`` is ``L_new`` here: it is not observed and
    not an accepted assumption, and it is identical for both calls.
    """
    return _series_rows(observed, path)[0]


def _availability_summary(labels):
    """Summarise per-row availability labels into the receipt's ``availability_basis`` record.

    Any row whose availability is unknown makes the summary ``unknown`` — the history is then
    not a strict known-then input. Otherwise the recorded bases are summarised as their sorted
    distinct values, joined by ``'; '``: a summary of recorded labels, never a fabricated single
    basis. The counts travel with the value for the receipt and its evidence.
    """
    known = [label for label in labels if label != AVAILABILITY_UNKNOWN]
    bases = sorted(set(known))
    return {'availability_basis': AVAILABILITY_UNKNOWN if len(known) != len(labels) or not bases
        else '; '.join(bases), 'known_rows': len(known), 'unknown_rows': len(labels) - len(known)}


def availability_summary(observed, path):
    """The receipt's ``availability_basis`` source, over the same validated context rows.

    ``available_at``/``availability_basis`` are validated and never filled: see
    :func:`_availability_summary` for the summary rule. ``run_pair`` copies the value onto every
    call receipt.
    """
    return _availability_summary(_series_rows(observed, path)[1])


def history_digest(rows, path, *, covariate_past_basis=COVARIATE_PAST_BASIS):
    """SHA-256 over the complete ordered context rows plus the declared parameters.

    The digest covers the covariate history the model actually receives, not merely the observed
    series: a changed constructed value or basis label changes it and the pair is refused
    (``WHATIF_HISTORY_MISMATCH``). Equal digests are evidence of one identical model history. Every
    row is revalidated first — the five model-input columns, the series id and finite numbers —
    so a hand-built row carrying a non-number or a non-finite value is refused typed instead of
    failing inside canonical serialization.
    """
    _check_path(path)
    if type(rows) not in (list, tuple):
        _fail('WHATIF_HISTORY', '$.context_rows', 'the ordered context rows as a list')
    if len(rows) != path.context_window:
        _fail('WHATIF_HISTORY', '$.context_rows',
            f'the complete context window of {path.context_window} ordered rows')
    for index, row in enumerate(rows):
        where = f'$.context_rows[{index}]'
        if type(row) is not dict or set(row) != set(CONTEXT_COLUMNS):
            _fail('WHATIF_HISTORY', where, 'model-input row with exactly ' + ', '.join(CONTEXT_COLUMNS))
        if type(row['series_id']) is not str or row['series_id'] != path.series_id:
            _fail('WHATIF_HISTORY', f'{where}.series_id', 'the series id of this path')
        if type(row['hour_start']) is not str:
            _fail('WHATIF_HISTORY', f'{where}.hour_start',
                'civil timestamp text without an offset or zone name')
        # The digest covers the numbers the model input carries, so a hand-built row cannot smuggle
        # a non-number or a non-finite value into the canonical bytes (the digest would otherwise
        # fail untyped, outside this module's error boundary).
        _finite_number(row[TARGET_COLUMN], f'{where}.{TARGET_COLUMN}', 'WHATIF_HISTORY',
            'non-NULL finite target value')
        if type(row[PAST_COVARIATE_COLUMN]) is not int:
            _fail('WHATIF_HISTORY', f'{where}.{PAST_COVARIATE_COLUMN}', 'non-NULL integer count')
        _finite_number(row[COVARIATE_COLUMN], f'{where}.{COVARIATE_COLUMN}', 'WHATIF_HISTORY',
            'the constructed covariate the model input carries: a finite numeric value')
    return _digest({'context_rows': list(rows), 'covariate_past_basis': covariate_past_basis,
        'series_id': path.series_id, 'h0': path.h0, 'context_window': path.context_window,
        'horizon_requested': path.horizon_requested, 'horizon_effective': path.horizon_effective,
        'timezone_convention': TIMEZONE_CONVENTION, 'confidence_level': CONFIDENCE_LEVEL,
        'model': MODEL})


def labels(execution_mode, consequences='computed', uncomputed_reason=None):
    """The fixed result labels; every result and receipt carries them."""
    if execution_mode not in EXECUTION_MODES:
        _fail('WHATIF_CONFIG_INVALID', '$.labels.execution_mode',
            'one of ' + ', '.join(EXECUTION_MODES))
    if consequences not in ('computed', 'uncomputed'):
        _fail('WHATIF_CONFIG_INVALID', '$.labels.consequences', "consequences is 'computed' or 'uncomputed'")
    if consequences == 'uncomputed' and (type(uncomputed_reason) is not str
            or not uncomputed_reason.strip()):
        _fail('WHATIF_CONFIG_INVALID', '$.labels.uncomputed_reason',
            'an uncomputed result records its reason')
    if consequences == 'computed' and uncomputed_reason is not None:
        _fail('WHATIF_CONFIG_INVALID', '$.labels.uncomputed_reason',
            'a computed result carries no uncomputed reason')
    out = {'feature_status': 'Preview', 'interpretation': 'directional',
        'content_kind': 'simulation output', 'execution_mode': execution_mode, 'caveat': CAVEAT,
        'consequences': consequences}
    if consequences == 'uncomputed':
        out['uncomputed_reason'] = uncomputed_reason
    return out


def uncomputed(error, *, execution_mode):
    """The fallback record: no number, the typed reason, and the labels still visible."""
    if isinstance(error, WhatIfError):
        reason, details = f'{error.code} at {error.field_path}: {error.rule}', error.as_dict()
    elif type(error) is str and error.strip():
        reason, details = error, None
    else:
        _fail('WHATIF_CONFIG_INVALID', '$.uncomputed_reason', 'a typed refusal or a nonempty reason')
    return {'consequences': 'uncomputed', 'uncomputed_reason': reason, 'error': details,
        'labels': labels(execution_mode, 'uncomputed', reason)}


@dataclass(frozen=True)
class StepForecast:
    """One horizon step of one call, ordered by step."""

    step: int
    hour_start: str
    value: float
    lower: float
    upper: float

    def as_dict(self):
        return {'step': self.step, 'hour_start': self.hour_start, 'value': self.value,
            'lower': self.lower, 'upper': self.upper}


@dataclass(frozen=True)
class CallResult:
    """One parsed call: its path, its digests and its per-step forecast."""

    call: str
    role: str
    series_id: str
    series_relation: str
    level_mw: str
    model: str
    units: dict
    resolution: str
    horizon_requested: int
    horizon_effective: int
    horizon_clipped: bool
    context_window: int
    window_start: str
    window_end: str
    statement_digest: str
    path_digest: str
    history_digest: str
    availability_basis: str
    steps: tuple
    labels: dict

    def as_dict(self):
        return {'call': self.call, 'role': self.role, 'series_id': self.series_id,
            'series_relation': self.series_relation, 'level_mw': self.level_mw,
            'model': self.model, 'units': self.units,
            'resolution': self.resolution, 'horizon_requested': self.horizon_requested,
            'horizon_effective': self.horizon_effective, 'horizon_clipped': self.horizon_clipped,
            'context_window': self.context_window,
            'window': {'start': self.window_start, 'end': self.window_end},
            'statement_digest': self.statement_digest, 'path_digest': self.path_digest,
            'history_digest': self.history_digest, 'availability_basis': self.availability_basis,
            'steps': [step.as_dict() for step in self.steps], 'labels': dict(self.labels)}


def _rows(value):
    """Accept parsed rows or the ``bq query --format=json`` text of one statement."""
    rule = 'the engine rows as a JSON array of objects'
    if type(value) in (str, bytes):
        if type(value) is bytes:
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                _fail('WHATIF_RESULT_INCOMPATIBLE', '$.rows', rule)
        value, error = parse_json(value)
        if error is not None or type(value) is not list:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.rows', rule)
    if type(value) is not list:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.rows', rule)
    return value


def parse_forecast_rows(rows, path, statement, *, history_digest_value, execution_mode,
        availability_basis=AVAILABILITY_UNKNOWN):
    """Parse one statement's rows into the per-hour steps, ordered by step.

    The statement must belong to the supplied path: its call, role, covariate level, SQL text and
    path digest are verified against the canonical rendering of that path, so a statement of
    another covariate path — whose rows would be compared against the wrong receipt fields — is
    refused rather than combined with this path. A result of the wrong shape is refused with
    reason: missing struct fields, a nonempty
    ``ai_forecast_status``, a row whose model is not the literal, timestamps off the requested
    grid, unordered bounds, or fewer rows than the horizon. ``availability_basis`` is the
    context's availability summary (see :func:`availability_summary`); it defaults to
    ``unknown`` — a caller that runs no validated series cannot claim a known-then input.
    ``history_digest_value`` is the digest of that same history; a value that is not a digest is
    refused, so a receipt can never carry an unvalidated history.
    """
    _check_path(path)
    if type(statement) is not Statement or type(statement.sql) is not str \
            or statement.sql.strip() == '':
        _fail('WHATIF_CONFIG_INVALID', '$.statement', 'a rendered Statement')
    # The statement must be *this* path's statement for *this* call: its call, role, level, SQL
    # text and path digest are checked against the canonical rendering of the supplied path, so
    # a statement rendered from another covariate path can never be combined with this path's
    # receipt fields.
    if type(statement.call) is not str or statement.call not in CALL_ROLES:
        _fail('WHATIF_CONFIG_INVALID', '$.statement.call', "call is 'A' (prior) or 'B' (accepted)")
    role = CALL_ROLES[statement.call]
    if statement.role != role:
        _fail('WHATIF_CONFIG_INVALID', '$.statement.role',
            f"the role of call {statement.call} is '{role}'")
    level_mw = path.level_for(statement.call)
    if statement.level_mw != level_mw:
        _fail('WHATIF_CONFIG_INVALID', '$.statement.level_mw',
            f'the covariate level of call {statement.call} in this path')
    if statement.sql != _statement_sql(path, level_mw):
        _fail('WHATIF_CONFIG_INVALID', '$.statement.sql',
            'the SQL text rendered from this path and call; a statement of another path is refused')
    expected_path_digest = path_digest(path, statement.call)
    if statement.path_digest != expected_path_digest:
        _fail('WHATIF_CONFIG_INVALID', '$.statement.path_digest',
            'the path digest of this path and call')
    if type(history_digest_value) is not str or DIGEST.fullmatch(history_digest_value) is None:
        _fail('WHATIF_CONFIG_INVALID', '$.history_digest',
            'the lowercase SHA-256 digest of the ordered context rows supplied to the model')
    if type(availability_basis) is not str or not availability_basis.strip():
        _fail('WHATIF_CONFIG_INVALID', '$.availability_basis',
            'the context availability summary; unknown stays unknown')
    data = _rows(rows)
    expected = [_step_text(_civil(path.h0, '$.h0')[0], step)
        for step in range(1, path.horizon_effective + 1)]
    if len(data) != len(expected):
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.rows',
            f'{len(expected)} rows for the requested horizon, got {len(data)}')
    found = {}
    for index, row in enumerate(data):
        where = f'$.rows[{index}]'
        if type(row) is not dict:
            _fail('WHATIF_RESULT_INCOMPATIBLE', where, 'one result row object')
        if 'model' in row and row['model'] not in (None, MODEL):
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.model', f"the model literal is '{MODEL}'")
        if row.get('series_id') != path.series_id:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.series_id', 'the series id that was requested')
        hour = _hour(row.get('forecast_timestamp'), f'{where}.forecast_timestamp')
        if hour in found:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.forecast_timestamp',
                'one row per requested hour')
        target = row.get(TARGET_COLUMN)
        if type(target) is not dict:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.{TARGET_COLUMN}', 'the target STRUCT')
        missing = [name for name in STRUCT_FIELDS if name not in target]
        if missing:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.{TARGET_COLUMN}.{missing[0]}',
                'every target STRUCT field is present')
        if target['ai_forecast_status'] != '':
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.{TARGET_COLUMN}.ai_forecast_status',
                f"an empty forecast status; got {target['ai_forecast_status']!r}")
        bounds = []
        for name in STRUCT_FIELDS[:3]:
            bounds.append(_finite_number(target[name], f'{where}.{TARGET_COLUMN}.{name}'))
        if not bounds[1] <= bounds[0] <= bounds[2]:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'{where}.{TARGET_COLUMN}',
                'ordered bounds: lower <= value <= upper')
        found[hour] = (bounds[0], bounds[1], bounds[2])
    steps = []
    for step, hour in enumerate(expected, 1):
        if hour not in found:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.rows', f'the requested grid step {hour} is missing')
        value, lower, upper = found[hour]
        steps.append(StepForecast(step=step, hour_start=hour, value=value, lower=lower, upper=upper))
    return CallResult(call=statement.call, role=statement.role, series_id=path.series_id,
        series_relation=path.series_relation, level_mw=statement.level_mw, model=MODEL,
        units={'target': TARGET_UNIT, 'covariate': COVARIATE_UNIT}, resolution=RESOLUTION,
        horizon_requested=path.horizon_requested, horizon_effective=path.horizon_effective,
        horizon_clipped=path.horizon_clipped, context_window=path.context_window,
        window_start=path.window_start, window_end=path.window_end,
        statement_digest=statement.statement_digest, path_digest=expected_path_digest,
        history_digest=history_digest_value, availability_basis=availability_basis,
        steps=tuple(steps), labels=labels(execution_mode, 'computed'))


@dataclass(frozen=True)
class StepDifference:
    """One horizon step of the pair difference (B - A)."""

    step: int
    hour_start: str
    delta_value: float
    delta_lower: float
    delta_upper: float

    def as_dict(self):
        return {'step': self.step, 'hour_start': self.hour_start, 'delta_value': self.delta_value,
            'delta_lower': self.delta_lower, 'delta_upper': self.delta_upper}


@dataclass(frozen=True)
class PairResult:
    """The compatible pair: both calls, the per-step difference, aggregates and labels."""

    calls: tuple
    steps: tuple
    aggregates: dict
    verdict: dict
    labels: dict
    proposal_consequences: str = 'uncomputed'

    def as_dict(self):
        return {'calls': [call.as_dict() for call in self.calls],
            'difference': [step.as_dict() for step in self.steps], 'aggregates': self.aggregates,
            'verdict': self.verdict, 'labels': dict(self.labels),
            'proposal_consequences': self.proposal_consequences}


def compare_calls(call_a, call_b, *, execution_mode):
    """Refuse an incompatible pair, else return the per-step difference B - A.

    The compatibility verdict requires one identical history digest, equal ``N_eff`` and
    requested ``N``, context, resolution, model, units, the series id and its relation; two calls
    with the same path are refused because there is nothing to compare, and the paths are compared
    on the numerical covariate levels the model receives, so ``0`` and ``0.0`` do not pass as two
    inputs. The relation must agree because the history digest is over the rows and cannot
    separate two tables: a pair built from two relations would otherwise carry the one-identical-
    history verdict without a receipt field that reveals it. Every derived difference and the mean
    must be finite: a subtraction or aggregation
    that overflows two finite forecasts is refused with its field path, never reported as an
    infinity. The pair label is the calls' own execution mode: two calls of different modes, or a
    pair label contradicting both calls, are refused rather than relabelled.
    """
    for call, expected in ((call_a, 'A'), (call_b, 'B')):
        if type(call) is not CallResult or call.call != expected:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls', "the pair is call A (prior) then call B (accepted)")
        if type(call.steps) not in (list, tuple) or len(call.steps) != call.horizon_effective:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].steps',
                'one step per effective-horizon hour')
        if type(call.series_relation) is not str or RELATION.fullmatch(call.series_relation) is None:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].series_relation',
                'each call carries the validated project.dataset.table relation it ran over')
    modes = [call.labels.get('execution_mode') if type(call.labels) is dict else None
        for call in (call_a, call_b)]
    for mode in modes:
        if mode not in EXECUTION_MODES:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].labels.execution_mode',
                'each call carries one of ' + ', '.join(EXECUTION_MODES))
    if modes[0] != modes[1]:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].labels.execution_mode',
            f'the two calls must be one execution; got {modes[0]!r} and {modes[1]!r}')
    if execution_mode != modes[0]:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].labels.execution_mode',
            f"the pair label is the calls' execution mode {modes[0]!r}, never relabelled")
    if call_a.history_digest != call_b.history_digest:
        _fail('WHATIF_HISTORY_MISMATCH', '$.calls[].history_digest',
            'the two calls must supply one identical ordered model history')
    if call_a.path_digest == call_b.path_digest:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].path_digest',
            'the two paths are identical: the covariate levels are numerically equal, so there is '
            'no difference to compare')
    # Second line of defence for a hand-built call carrying stale digests: the model receives the
    # covariate number, not its spelling, so two levels that are one FLOAT64 are one model input.
    levels = [_canonical_level(_decimal(call.level_mw, '$.calls[].level_mw',
        'WHATIF_RESULT_INCOMPATIBLE')[1]) for call in (call_a, call_b)]
    if levels[0] == levels[1]:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].level_mw',
            'the two covariate levels are one number; there is nothing to compare')
    equal = (('series_id', call_a.series_id, call_b.series_id),
        ('series_relation', call_a.series_relation, call_b.series_relation),
        ('availability_basis', call_a.availability_basis, call_b.availability_basis),
        ('horizon_requested', call_a.horizon_requested, call_b.horizon_requested),
        ('horizon_effective', call_a.horizon_effective, call_b.horizon_effective),
        ('context_window', call_a.context_window, call_b.context_window),
        ('window_start', call_a.window_start, call_b.window_start),
        ('window_end', call_a.window_end, call_b.window_end),
        ('resolution', call_a.resolution, call_b.resolution),
        ('model', call_a.model, call_b.model),
        ('units', call_a.units, call_b.units))
    for name, left, right in equal:
        if left != right:
            _fail('WHATIF_RESULT_INCOMPATIBLE', f'$.calls[].{name}', 'the two calls must agree')
    steps = []
    for index, (left, right) in enumerate(zip(call_a.steps, call_b.steps)):
        if left.hour_start != right.hour_start or left.step != right.step:
            _fail('WHATIF_RESULT_INCOMPATIBLE', '$.difference',
                'the two calls must return the same ordered hourly grid')
        deltas = []
        for name, first, second in (('value', left.value, right.value),
                ('lower', left.lower, right.lower), ('upper', left.upper, right.upper)):
            where = f'$.calls[].steps[{index}].{name}'
            delta = _finite_number(second, where) - _finite_number(first, where)
            if not math.isfinite(delta):
                _fail('WHATIF_RESULT_INCOMPATIBLE', f'$.difference[{index}].delta_{name}',
                    'a finite difference: two finite forecasts must not overflow when subtracted')
            deltas.append(delta)
        steps.append(StepDifference(step=left.step, hour_start=left.hour_start,
            delta_value=deltas[0], delta_lower=deltas[1], delta_upper=deltas[2]))
    if not steps:
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.calls[].steps', 'at least one horizon step per call')
    deltas = [step.delta_value for step in steps]
    # Overflow-safe averaging: each difference is scaled before summing, so a set of large finite
    # differences cannot overflow the aggregation the way a naive sum does.
    mean_delta_w = sum(delta / len(deltas) for delta in deltas)
    if not math.isfinite(mean_delta_w):
        _fail('WHATIF_RESULT_INCOMPATIBLE', '$.aggregates.mean_delta_w', 'a finite mean difference')
    aggregates = {'n_steps': len(steps), 'mean_delta_w': mean_delta_w,
        'max_abs_delta': max(abs(delta) for delta in deltas)}
    verdict = {'compatible': True, 'history_digest': call_a.history_digest,
        'path_digests': [call_a.path_digest, call_b.path_digest],
        'checks': {name: left for name, left, _ in equal}}
    return PairResult(calls=(call_a, call_b), steps=tuple(steps), aggregates=aggregates,
        verdict=verdict, labels=labels(execution_mode, 'computed'))


def run_pair(path, transport, observed, *, execution_mode):
    """Run both statements through an injected transport and return the pair difference.

    ``transport(statement)`` returns one statement's ``bq query --format=json`` rows: a list of
    objects or the JSON text. This module never builds a client, reads a credential or touches
    the network; a transport failure propagates to the caller, which records the uncomputed
    fallback with :func:`uncomputed`. The context rows are built and digested once, so both calls
    carry one identical history digest, and the availability summary is computed from the same
    validated rows, so both receipts carry the same ``availability_basis``. A refused history —
    including a row known only after ``H0`` — stops before the transport is called.
    """
    _check_path(path)
    if not callable(transport):
        _fail('WHATIF_CONFIG_INVALID', '$.transport', 'an injected callable returning result rows')
    rows, labels = _series_rows(observed, path)
    digest = history_digest(rows, path)
    summary = _availability_summary(labels)
    statements = render_statements(path)
    calls = [parse_forecast_rows(transport(statement), path, statement,
        history_digest_value=digest, availability_basis=summary['availability_basis'],
        execution_mode=execution_mode) for statement in statements]
    return compare_calls(calls[0], calls[1], execution_mode=execution_mode)


__all__ = ['ACCEPTED_FIELD', 'ACCEPTED_UNIT', 'AVAILABILITY_UNKNOWN', 'CAVEAT', 'CALLS', 'CODES',
    'CONFIDENCE_LEVEL',
    'CONTEXT_COLUMNS', 'CONTEXT_MAX', 'CONTEXT_MIN', 'CONTEXT_STEP', 'COVARIATE_COLUMN',
    'COVARIATE_PAST_BASIS', 'COVARIATE_UNIT', 'CallResult', 'CovariatePath', 'EXECUTION_MODES',
    'HORIZON_MAX', 'HORIZON_MIN', 'MODEL', 'PAST_COVARIATE_COLUMN', 'PairResult', 'RESOLUTION',
    'SERIES_COLUMNS', 'STRUCT_FIELDS', 'Statement', 'StepDifference', 'StepForecast',
    'TARGET_COLUMN', 'TARGET_UNIT', 'TIMEZONE_CONVENTION', 'WhatIfError', 'availability_summary',
    'build_covariate_path', 'compare_calls', 'context_rows', 'covariate_basis', 'history_digest',
    'labels', 'parse_forecast_rows', 'path_digest', 'render_statements', 'run_pair', 'uncomputed']
