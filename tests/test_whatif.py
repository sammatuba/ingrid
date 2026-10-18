"""Offline what-if contract tests: SQL text, limits, parser, difference and labels.

Hermetic: no network, client, credential or cloud call. The only executor is a local fake
transport, exactly the seam NUM-3 will wire to BigQuery behind GATE-3.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import unittest

from src.adapters.bigquery import (AVAILABILITY_UNKNOWN, COVARIATE_PAST_BASIS, MODEL,
    TIMEZONE_CONVENTION, WhatIfError, availability_summary, build_covariate_path, compare_calls,
    context_rows, covariate_basis, history_digest, labels, parse_forecast_rows, path_digest,
    render_statements, run_pair, uncomputed)

#: A recorded first-availability basis, distinct from the unknown placeholder of ``observed()``.
KNOWN_BASIS = 'estate first-availability time, recorded before the cutoff'

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'src' / 'adapters' / 'bigquery' / 'fixtures' / 'whatif_statements.json'
MODULE = ROOT / 'src' / 'adapters' / 'bigquery' / 'whatif.py'

#: The intent's boundary example: date-only 2026-10-03 to 2026-10-05, H0 2026-10-02T23:00:00,
#: requested N 72 clipped to N_eff 48 (the step 2026-10-05T00:00:00 is end-exclusive).
H0 = '2026-10-02T23:00:00'
H0_DATETIME = datetime(2026, 10, 2, 23)
PARAMS = {'series_id': 'CVIS', 'series_relation': 'synthetic-project.whatif.price_hourly_fixture',
    'anchor': H0, 'horizon': 72, 'context_window': 64}
PERIOD = {'start': '2026-10-03', 'end': '2026-10-05'}


def ref(kind):
    return {'record_kind': kind, 'record_id': kind.lower() + ':1', 'revision_id': 'r1',
        'content_digest': 'b' * 64}


def proposal(*, old='100', new='0', field='assumed_available_capacity', kind='assumed_available_capacity',
        unit='MW', period=None):
    return {'schema_version': 'h0.v1', 'tenant_id': 'tenant', 'case_id': 'case',
        'record_kind': 'ScenarioProposal', 'record_id': 'scenario:1', 'revision_id': 'r1',
        'recorded_at': '2026-10-11T00:00:00Z', 'content_digest': 'a' * 64, 'time_metadata': {},
        'payload': {'execution': 'proposal_only', 'comparison': 'pending_outputs',
            'consequences': 'uncomputed', 'synthetic': True, 'decision_ref': ref('ReviewDecision'),
            'mapping_ref': ref('MappingRevision'), 'old_assumption_ref': ref('AssumptionRevision'),
            'new_assumption_ref': ref('AssumptionRevision'),
            'delta': {'representation_id': 'rep-1', 'input_field': field,
                'entity': {'entity_id': 'unit-1', 'entity_type': 'GeneratingUnit'},
                'cardinality': 'one_to_one',
                'old_value': {'value': old, 'quantity_kind': kind, 'unit': unit},
                'new_value': {'value': new, 'quantity_kind': kind, 'unit': unit},
                'valid_period': deepcopy(period or PERIOD)}}}


def path_for(**changes):
    values = dict(PARAMS)
    values.update({key: value for key, value in changes.items() if key in values})
    return build_covariate_path(changes.get('record', proposal()), **values)


def hour_text(step):
    return (H0_DATETIME + timedelta(hours=step)).strftime('%Y-%m-%dT%H:%M:%S')


def observed(count=64, *, price=2500.0, out_hours=3):
    """The contiguous hourly context run ending at H0, ascending."""
    return [{'hour_start': hour_text(index + 1 - count), 'region_code': 'CVIS',
        'price_php_mwh': price, 'n_resources_out_hour': out_hours,
        'available_at': None, 'availability_basis': 'unknown'} for index in range(count)]


def result_rows(*, count=48, shift=0.0, status='', stamp='{hour} UTC', model=None):
    """One call's bq query --format=json rows; the target STRUCT carries value and bounds."""
    rows = []
    for step in range(1, count + 1):
        value = 3000.0 + step + shift
        row = {'series_id': 'CVIS', 'forecast_timestamp': stamp.format(hour=hour_text(step)),
            'price_php_mwh': {'value': value, 'prediction_interval_lower_bound': value - 1.0,
                'prediction_interval_upper_bound': value + 1.0, 'ai_forecast_status': status}}
        if model is not None:
            row['model'] = model
        rows.append(row)
    return rows


def transport(*, shift_a=0.0, shift_b=5.0, mutate=None):
    """A local fake transport: one statement in, its rows out; records the calls it received."""
    calls = []

    def call(statement):
        calls.append(statement)
        rows = result_rows(count=statement_rows(statement),
            shift=shift_a if statement.call == 'A' else shift_b)
        return mutate(rows) if mutate else rows
    call.calls = calls
    return call


def statement_rows(statement):
    """The rendered horizon, read back from the statement's own N_eff literal."""
    return int(statement.sql.split('horizon => ')[1].split(',')[0])


def shaped_rows(values, count=48):
    """One call's rows whose (lower, value, upper) triple is constant over the horizon."""
    lower, value, upper = values
    return [{'series_id': 'CVIS', 'forecast_timestamp': hour_text(step) + ' UTC',
        'price_php_mwh': {'value': value, 'prediction_interval_lower_bound': lower,
            'prediction_interval_upper_bound': upper, 'ai_forecast_status': ''}}
        for step in range(1, count + 1)]


def extremes(first, second):
    """A local fake transport returning one extreme (lower, value, upper) triple per call."""
    def call(statement):
        return shaped_rows(first if statement.call == 'A' else second)
    return call


def build_error(test, **changes):
    with test.assertRaises(WhatIfError) as caught:
        path_for(**changes)
    return caught.exception


#: The public readers that must revalidate a hand-built path: (name, callable taking the path).
PATH_READERS = (('render_statements', render_statements), ('covariate_basis', covariate_basis),
    ('path_digest', lambda path: path_digest(path, 'A')))


class GoldenStatementTests(unittest.TestCase):
    """Acceptance: the SQL text matches the golden fixture."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cls.path = build_covariate_path(deepcopy(cls.fixture['inputs']['proposal']),
            **{key: cls.fixture['inputs'][key] for key in PARAMS})
        cls.prior, cls.accepted = render_statements(cls.path)

    def test_golden_sql_matches_the_fixture(self):
        expected = self.fixture['expected']['statements']
        self.assertEqual(expected['A'], self.prior.sql)
        self.assertEqual(expected['B'], self.accepted.sql)

    def test_golden_path_digests_and_labels_match_the_fixture(self):
        expected = self.fixture['expected']
        self.assertEqual(expected['path'], self.path.as_dict())
        self.assertEqual({'A': self.prior.statement_digest, 'B': self.accepted.statement_digest},
            expected['statement_digest'])
        self.assertEqual({'A': self.prior.path_digest, 'B': self.accepted.path_digest},
            expected['path_digest'])
        self.assertEqual(expected['covariate_basis'], covariate_basis(self.path))
        self.assertEqual(expected['labels'], labels('synthetic fixture'))

    def test_rendered_statements_are_deterministic(self):
        again = render_statements(build_covariate_path(deepcopy(self.fixture['inputs']['proposal']),
            **{key: self.fixture['inputs'][key] for key in PARAMS}))
        self.assertEqual([self.prior.sql, self.accepted.sql], [item.sql for item in again])

    def test_statements_differ_only_on_the_future_covariate_literal(self):
        left, right = self.prior.sql.splitlines(), self.accepted.sql.splitlines()
        self.assertEqual(len(left), len(right))
        differing = [index for index, (x, y) in enumerate(zip(left, right)) if x != y]
        self.assertEqual(1, len(differing))
        line = left[differing[0]]
        self.assertIn('assumed_available_capacity_mw', line)
        self.assertIn('CAST(100 AS FLOAT64)', line)          # call A: the prior level L_old
        self.assertIn('CAST(0 AS FLOAT64)', right[differing[0]])  # call B: the accepted level L_new
        future = self.prior.sql.index('future_rows AS (')
        self.assertLess(future, self.prior.sql.index(line.strip()))

    def test_target_and_past_covariate_are_null_on_future_rows(self):
        for statement in (self.prior, self.accepted):
            future = statement.sql[statement.sql.index('future_rows AS ('):]
            self.assertIn('CAST(NULL AS FLOAT64) AS price_php_mwh', future)
            self.assertIn('CAST(NULL AS INT64) AS n_resources_out_hour', future)
            self.assertIn("model => 'TimesFM 3.0'", statement.sql)
            self.assertIn('confidence_level => 0.95', statement.sql)

    def test_context_rows_carry_the_constructed_accepted_level_in_both_calls(self):
        for statement in (self.prior, self.accepted):
            head = statement.sql[:statement.sql.index('future_rows AS (')]
            self.assertIn('CAST(0 AS FLOAT64) AS assumed_available_capacity_mw', head)

    def test_rendered_horizon_is_the_clipped_effective_horizon(self):
        self.assertTrue(self.path.horizon_clipped)
        self.assertEqual(48, self.path.horizon_effective)
        self.assertEqual('2026-10-04T23:00:00', self.path.window_last_step)
        for statement in (self.prior, self.accepted):
            self.assertIn('INTERVAL 48 HOUR', statement.sql)
            self.assertIn('horizon => 48', statement.sql)
            self.assertNotIn('INTERVAL 72 HOUR', statement.sql)
            self.assertNotIn('horizon => 72', statement.sql)


class LimitTests(unittest.TestCase):
    """Acceptance: limit violations raise typed errors."""

    def test_horizon_outside_1_to_1024_is_refused(self):
        for horizon in (0, -1, 1025, 2048, 64.0, '64', True, None):
            with self.subTest(horizon=horizon):
                error = build_error(self, horizon=horizon)
                self.assertEqual('WHATIF_HORIZON_RANGE', error.code)
                self.assertEqual('$.horizon', error.field_path)
                self.assertIn('1,024', error.rule)

    def test_horizon_bounds_are_accepted(self):
        for horizon in (1, 1024):
            with self.subTest(horizon=horizon):
                self.assertEqual(horizon, path_for(horizon=horizon).horizon_requested)

    def test_context_window_must_be_a_multiple_of_32_from_64_to_2048(self):
        for context_window in (0, 32, 63, 65, 96 + 1, 2080, 2112, '64', True, None):
            with self.subTest(context_window=context_window):
                error = build_error(self, context_window=context_window)
                self.assertEqual('WHATIF_CONTEXT_WINDOW', error.code)
                self.assertEqual('$.context_window', error.field_path)

    def test_context_window_bounds_are_accepted(self):
        for context_window in (64, 96, 2048):
            with self.subTest(context_window=context_window):
                self.assertEqual(context_window,
                    path_for(context_window=context_window).context_window)

    def test_refusal_carries_code_field_path_and_rule(self):
        error = build_error(self, horizon=4096)
        self.assertEqual({'code': 'WHATIF_HORIZON_RANGE', 'field_path': '$.horizon',
            'rule': error.rule}, error.as_dict())
        self.assertIn('WHATIF_HORIZON_RANGE at $.horizon', str(error))


class DeltaTests(unittest.TestCase):
    """The reviewed delta: field, unit, values, time rule and disputed window."""

    def test_only_the_accepted_field_unit_and_quantity_kind_are_taken(self):
        error = build_error(self, record=proposal(field='available_capacity'))
        self.assertEqual('WHATIF_DELTA_FIELD', error.code)
        self.assertEqual('$.payload.delta.input_field', error.field_path)
        for changes, field_path in (({'kind': 'capacity'}, '$.payload.delta.old_value.unit'),
                ({'unit': 'GW'}, '$.payload.delta.old_value.unit')):
            with self.subTest(**changes):
                error = build_error(self, record=proposal(**changes))
                self.assertEqual('WHATIF_DELTA_FIELD', error.code)
                self.assertEqual(field_path, error.field_path)
        record = proposal()
        record['payload']['delta']['new_value']['unit'] = 'GW'
        error = build_error(self, record=record)
        self.assertEqual('WHATIF_DELTA_FIELD', error.code)
        self.assertEqual('$.payload.delta.new_value.unit', error.field_path)

    def test_malformed_delta_values_are_configuration_errors(self):
        for value in ('NaN', 'Infinity', 'x', '', '1e3', 5, None, '--1'):
            with self.subTest(value=value):
                error = build_error(self, record=proposal(old=value))
                self.assertEqual('WHATIF_CONFIG_INVALID', error.code)
                self.assertEqual('$.payload.delta.old_value.value', error.field_path)

    def test_a_bound_anchor_or_hour_with_an_offset_or_zone_is_refused(self):
        cases = [(proposal(period={'start': '2026-10-03T00:00:00Z', 'end': '2026-10-05'}),
                '$.payload.delta.valid_period.start'),
            (proposal(period={'start': '2026-10-03T00:00:00+08:00', 'end': '2026-10-05'}),
                '$.payload.delta.valid_period.start'),
            (proposal(period={'start': '2026-10-03', 'end': '2026-10-05T00:00:00[Asia/Manila]'}),
                '$.payload.delta.valid_period.end'),
            (proposal(), '$.anchor')]
        for record, field_path in cases:
            changes = {'record': record}
            if field_path == '$.anchor':
                changes['anchor'] = H0 + 'Z'
            with self.subTest(field_path=field_path):
                error = build_error(self, **changes)
                self.assertEqual('WHATIF_CONFIG_INVALID', error.code)
                self.assertEqual(field_path, error.field_path)

    def test_window_must_begin_at_h0_plus_one(self):
        for period in ({'start': '2026-10-03T01:00:00', 'end': '2026-10-05'},
                {'start': '2026-10-02T20:00:00', 'end': '2026-10-02T23:00:00'},
                {'start': '2026-09-01', 'end': '2026-10-02'}):
            with self.subTest(period=period):
                error = build_error(self, record=proposal(period=period))
                self.assertEqual('WHATIF_DELTA_WINDOW', error.code)
                self.assertEqual('$.payload.delta.valid_period', error.field_path)

    def test_clipping_only_shortens_the_requested_horizon(self):
        path = path_for(horizon=24)
        self.assertEqual(24, path.horizon_effective)
        self.assertFalse(path.horizon_clipped)
        wide = path_for(record=proposal(period={'start': '2026-10-03', 'end': '2026-11-01'}))
        self.assertEqual(72, wide.horizon_effective)
        self.assertFalse(wide.horizon_clipped)

    def test_a_mutated_proposal_is_refused(self):
        for key, value in (('execution', 'executed'), ('comparison', 'computed'),
                ('consequences', 'computed')):
            record = proposal()
            record['payload'][key] = value
            with self.subTest(key=key):
                error = build_error(self, record=record)
                self.assertEqual('WHATIF_CONFIG_INVALID', error.code)
                self.assertEqual('$.payload.execution', error.field_path)

    def test_the_anchor_must_be_the_last_complete_context_hour(self):
        for anchor in ('2026-10-02T23:30:00', '2026-10-02T23:00:30', '2026-10-02T23:59:59'):
            with self.subTest(anchor=anchor):
                error = build_error(self, anchor=anchor)
                self.assertEqual('WHATIF_CONFIG_INVALID', error.code)
                self.assertEqual('$.anchor', error.field_path)
                self.assertIn('last complete context hour', error.rule)

    def test_a_hand_built_path_off_the_hour_is_refused_before_rendering(self):
        off_hour = replace(path_for(), h0='2026-10-02T23:30:00')
        for name, read in PATH_READERS:
            with self.subTest(call=name):
                with self.assertRaises(WhatIfError) as caught:
                    read(off_hour)
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual('$.h0', caught.exception.field_path)

    def test_a_hand_built_path_is_fully_revalidated_before_rendering(self):
        cases = [({'horizon_requested': 1025}, 'WHATIF_HORIZON_RANGE', '$.horizon_requested'),
            ({'horizon_requested': 0.5}, 'WHATIF_HORIZON_RANGE', '$.horizon_requested'),
            ({'horizon_effective': 1.5}, 'WHATIF_HORIZON_RANGE', '$.horizon_effective'),
            ({'horizon_effective': 1025}, 'WHATIF_HORIZON_RANGE', '$.horizon_effective'),
            # W gives 48 steps: an effective horizon longer than W is a forecast outside W
            ({'horizon_effective': 60, 'horizon_clipped': True}, 'WHATIF_DELTA_WINDOW',
                '$.horizon_effective'),
            ({'window_start': '2026-10-03T05:00:00'}, 'WHATIF_DELTA_WINDOW', '$.window'),
            ({'window_end': '2026-10-03T05:00:00'}, 'WHATIF_DELTA_WINDOW', '$.horizon_effective'),
            ({'window_last_step': '2026-10-09T00:00:00'}, 'WHATIF_CONFIG_INVALID',
                '$.window_last_step'),
            ({'horizon_clipped': False}, 'WHATIF_CONFIG_INVALID', '$.horizon_clipped'),
            ({'horizon_clipped': 'yes'}, 'WHATIF_CONFIG_INVALID', '$.horizon_clipped'),
            ({'series_id': None}, 'WHATIF_CONFIG_INVALID', '$.series_id'),
            ({'series_relation': 7}, 'WHATIF_CONFIG_INVALID', '$.series_relation')]
        for changes, code, field_path in cases:
            broken = replace(path_for(), **changes)
            for name, read in PATH_READERS:
                with self.subTest(changes=changes, call=name):
                    with self.assertRaises(WhatIfError) as caught:
                        read(broken)
                    self.assertEqual(code, caught.exception.code)
                    self.assertEqual(field_path, caught.exception.field_path)
                    self.assertTrue(caught.exception.rule.strip())

    def test_the_civil_seconds_field_is_optional_and_impossible_times_are_refused(self):
        path = path_for(anchor='2026-10-02T23:00')
        self.assertEqual(H0, path.h0)
        prior, _ = render_statements(path)
        self.assertIn("TIMESTAMP '2026-10-02T23:00:00'", prior.sql)
        self.assertEqual(64, len(context_rows(
            [dict(row, hour_start=row['hour_start'][:16]) for row in observed()], path)))
        for anchor in ('2026-10-02T23:00:99', '2026-10-02T24:00', '2026-10-02T23:00:00.5',
                '2026-10-02T23', '2026-10-02T23:00Z'):
            with self.subTest(anchor=anchor):
                error = build_error(self, anchor=anchor)
                self.assertEqual('WHATIF_CONFIG_INVALID', error.code)
                self.assertEqual('$.anchor', error.field_path)
                self.assertTrue(error.rule.strip())

    def test_delta_refs_record_the_reviewed_references(self):
        refs = path_for().delta_refs
        self.assertEqual('a' * 64, refs['proposal_content_digest'])
        self.assertEqual({'decision_content_digest': 'b' * 64, 'old_assumption_content_digest': 'b' * 64,
            'new_assumption_content_digest': 'b' * 64, 'mapping_content_digest': 'b' * 64},
            {key: refs[key] for key in ('decision_content_digest', 'old_assumption_content_digest',
                'new_assumption_content_digest', 'mapping_content_digest')})
        self.assertEqual({'old_value': '100', 'new_value': '0', 'unit': 'MW',
            'quantity_kind': 'assumed_available_capacity', 'input_field': 'assumed_available_capacity',
            'valid_period': {'start': '2026-10-03T00:00:00', 'end': '2026-10-05T00:00:00'}},
            {key: refs[key] for key in ('old_value', 'new_value', 'unit', 'quantity_kind',
                'input_field', 'valid_period')})


class ContextHistoryTests(unittest.TestCase):
    """The constructed context covariate and the ordered history digest."""

    def test_context_rows_construct_the_accepted_level(self):
        rows = context_rows(observed(), path_for())
        self.assertEqual(64, len(rows))
        self.assertEqual(hour_text(-63), rows[0]['hour_start'])
        self.assertEqual(H0, rows[-1]['hour_start'])
        for row in rows:
            self.assertEqual(['series_id', 'hour_start', 'price_php_mwh', 'n_resources_out_hour',
                'assumed_available_capacity_mw'], list(row))
            self.assertEqual('CVIS', row['series_id'])
            self.assertEqual(2500.0, row['price_php_mwh'])
            self.assertEqual(3, row['n_resources_out_hour'])
            self.assertEqual(0.0, row['assumed_available_capacity_mw'])

    def test_short_gapped_null_or_unknown_series_rows_are_history_errors(self):
        cases = [observed()[:63], observed()[1:], observed(count=64)[:-1] + [observed(64)[62]],
            [dict(row, price_php_mwh=None) for row in observed()],
            [dict(row, n_resources_out_hour=None) for row in observed()],
            [dict(row, region_code='CLUZ') for row in observed()],
            [dict(row, unexpected=1) for row in observed()],
            [dict(row, available_at='2026-10-02T00:00:00', availability_basis=None)
                for row in observed()],
            [dict(row, hour_start='2026-10-02 23:00:00') for row in observed()],
            # future leakage 1: every row an hour later, so the last row is H0+1
            [dict(row, hour_start=hour_text(index + 2 - 64)) for index, row in enumerate(observed())],
            # future leakage 2: the valid run plus one extra row at H0+1
            observed() + [dict(observed()[0], hour_start=hour_text(1))],
            # future leakage 3: one row replaced by an hour after H0
            observed()[:30] + [dict(observed()[30], hour_start=hour_text(5))] + observed()[31:],
            # known only after the cutoff: the estate records the row's availability past H0
            [dict(row, available_at=hour_text(3), availability_basis='published later')
                for row in observed()]]
        for index, rows in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(WhatIfError) as caught:
                    context_rows(rows, path_for())
                self.assertEqual('WHATIF_HISTORY', caught.exception.code)

    def test_a_row_known_only_after_the_cutoff_is_refused_at_its_availability_time(self):
        late = [dict(row, available_at=hour_text(3), availability_basis='published later')
            for row in observed()]
        path = path_for()
        with self.assertRaises(WhatIfError) as caught:
            context_rows(late, path)
        self.assertEqual('WHATIF_HISTORY', caught.exception.code)
        self.assertEqual('$.context_rows[0].available_at', caught.exception.field_path)
        self.assertIn('cutoff', caught.exception.rule)
        injected = transport()
        with self.assertRaises(WhatIfError) as caught:
            run_pair(path, injected, late, execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_HISTORY', caught.exception.code)
        self.assertEqual([], injected.calls)     # refused before any statement reaches the transport

    def test_availability_at_the_cutoff_is_known_then(self):
        rows = [dict(row, available_at=H0, availability_basis=KNOWN_BASIS) for row in observed()]
        self.assertEqual(64, len(context_rows(rows, path_for())))
        self.assertEqual({'availability_basis': KNOWN_BASIS, 'known_rows': 64, 'unknown_rows': 0},
            availability_summary(rows, path_for()))

    def test_availability_summary_is_unknown_unless_every_row_records_its_time(self):
        path = path_for()
        mixed_bases = [dict(row, available_at=hour_text(-1),
            availability_basis='a' if index % 2 else 'b') for index, row in enumerate(observed())]
        one_known = [dict(observed()[0], available_at=H0, availability_basis=KNOWN_BASIS)] + observed()[1:]
        cases = [(observed(), 'unknown', 0, 64), (mixed_bases, 'a; b', 64, 0),
            (one_known, 'unknown', 1, 63)]
        for rows, basis, known, unknown in cases:
            with self.subTest(basis=basis):
                self.assertEqual({'availability_basis': basis, 'known_rows': known,
                    'unknown_rows': unknown}, availability_summary(rows, path))
        self.assertEqual('unknown', AVAILABILITY_UNKNOWN)

    def test_a_late_row_is_refused_by_the_summary_too(self):
        late = [dict(row, available_at=hour_text(7), availability_basis='published later')
            for row in observed()]
        with self.assertRaises(WhatIfError) as caught:
            availability_summary(late, path_for())
        self.assertEqual('WHATIF_HISTORY', caught.exception.code)
        self.assertEqual('$.context_rows[0].available_at', caught.exception.field_path)

    def test_an_oversized_integer_in_a_context_price_is_refused_typed(self):
        """A huge integer target is the typed history refusal, never an OverflowError."""
        rows = observed()
        rows[3]['price_php_mwh'] = 10 ** 400
        with self.assertRaises(WhatIfError) as caught:
            context_rows(rows, path_for())
        self.assertEqual('WHATIF_HISTORY', caught.exception.code)
        self.assertEqual('$.context_rows[3].price_php_mwh', caught.exception.field_path)
        self.assertEqual('non-NULL finite target value', caught.exception.rule)
        injected = transport()
        with self.assertRaises(WhatIfError) as caught:
            run_pair(path_for(), injected, rows, execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_HISTORY', caught.exception.code)
        self.assertEqual([], injected.calls)     # refused before any statement reaches the transport

    def test_a_constructed_level_with_no_float64_value_is_refused_typed(self):
        """The level is a finite decimal; the model input is the FLOAT64 the statement casts."""
        beyond = '1' + '0' * 400
        path = path_for(record=proposal(old='100', new=beyond))
        self.assertEqual(path_digest(path, 'B'), render_statements(path)[1].path_digest)
        self.assertIn(f'CAST({beyond} AS FLOAT64)', render_statements(path)[1].sql)
        injected = transport()
        readers = [('context_rows', lambda: context_rows(observed(), path)),
            ('availability_summary', lambda: availability_summary(observed(), path)),
            ('run_pair', lambda: run_pair(path, injected, observed(),
                execution_mode='synthetic fixture'))]
        for name, reader in readers:
            with self.subTest(reader=name):
                with self.assertRaises(WhatIfError) as caught:
                    reader()
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual('$.accepted_mw', caught.exception.field_path)
                self.assertTrue(caught.exception.rule.strip())
        self.assertEqual([], injected.calls)
        # the boundary is representability in FLOAT64, not a numeric range: 1e308 still builds
        inside = '1' + '0' * 308
        level = context_rows(observed(), path_for(record=proposal(old='0', new=inside)))[0]
        self.assertEqual(1e308, level['assumed_available_capacity_mw'])

    def test_a_hand_built_row_with_a_non_finite_value_is_refused_by_the_digest(self):
        """The digest covers the numbers the model input carries, so a hand-built infinity is typed."""
        path = path_for()
        cases = [('price_php_mwh', float('inf')), ('price_php_mwh', float('nan')),
            ('assumed_available_capacity_mw', float('inf')),
            ('assumed_available_capacity_mw', float('nan')), ('price_php_mwh', '2500'),
            ('n_resources_out_hour', 3.0), ('hour_start', 7), ('series_id', 7)]
        for column, value in cases:
            rows = context_rows(observed(), path)
            rows[5][column] = value
            with self.subTest(column=column, value=value):
                with self.assertRaises(WhatIfError) as caught:
                    history_digest(rows, path)
                self.assertEqual('WHATIF_HISTORY', caught.exception.code)
                self.assertEqual(f'$.context_rows[5].{column}', caught.exception.field_path)
                self.assertTrue(caught.exception.rule.strip())

    def test_history_digest_is_stable_and_covers_the_constructed_covariate(self):
        path = path_for()
        rows = context_rows(observed(), path)
        self.assertEqual(history_digest(rows, path), history_digest(context_rows(observed(), path), path))
        changed = [dict(row) for row in rows]
        changed[10]['assumed_available_capacity_mw'] = 7.5
        self.assertNotEqual(history_digest(rows, path), history_digest(changed, path))
        self.assertNotEqual(history_digest(rows, path),
            history_digest(rows, path, covariate_past_basis='observed'))
        self.assertEqual(64, len(history_digest(rows, path)))
        basis = covariate_basis(path)
        self.assertEqual(COVARIATE_PAST_BASIS, basis['covariate_past_basis'])
        self.assertEqual({'prior_mw': '100', 'accepted_mw': '0'}, basis['accepted_levels'])
        self.assertEqual('0', basis['context_level_mw'])


class ParserTests(unittest.TestCase):
    """Acceptance: an incompatible result is refused with a reason."""

    def setUp(self):
        self.path = path_for()
        self.prior, self.accepted = render_statements(self.path)
        self.digest = history_digest(context_rows(observed(), self.path), self.path)

    def parse(self, rows, statement=None, digest=None, **keywords):
        return parse_forecast_rows(rows, self.path, statement or self.prior,
            history_digest_value=digest or self.digest, execution_mode='synthetic fixture', **keywords)

    def test_parsed_steps_are_ordered_by_step_and_carry_the_row_values(self):
        rows = list(reversed(result_rows()))
        call = self.parse(rows)
        self.assertEqual(48, len(call.steps))
        self.assertEqual([1, 48, 48], [call.steps[0].step, call.steps[-1].step, len(call.steps)])
        self.assertEqual(hour_text(1), call.steps[0].hour_start)
        self.assertEqual(hour_text(48), call.steps[-1].hour_start)
        self.assertEqual(3001.0, call.steps[0].value)
        self.assertEqual(3000.0, call.steps[0].lower)
        self.assertEqual(3002.0, call.steps[0].upper)

    def test_rows_may_arrive_as_bq_query_json_text(self):
        call = self.parse(json.dumps(result_rows()))
        self.assertEqual(48, len(call.steps))
        self.assertEqual(MODEL, call.model)
        self.assertEqual({'target': 'PHP/MWh', 'covariate': 'MW'}, call.units)
        self.assertEqual('hourly', call.resolution)
        self.assertEqual(self.digest, call.history_digest)
        self.assertEqual(self.prior.path_digest, call.path_digest)
        self.assertEqual(self.prior.statement_digest, call.statement_digest)

    def test_a_seconds_less_forecast_timestamp_parses_on_the_grid(self):
        for suffix in ('', ' UTC', 'Z'):
            rows = [dict(row, forecast_timestamp=row['forecast_timestamp'][:16] + suffix)
                for row in result_rows()]
            with self.subTest(suffix=suffix):
                call = self.parse(rows)
                self.assertEqual(hour_text(1), call.steps[0].hour_start)
                self.assertEqual(hour_text(48), call.steps[-1].hour_start)
        impossible = [dict(row, forecast_timestamp=hour_text(7)[:14] + ':99 UTC')
            for row in result_rows()]
        with self.assertRaises(WhatIfError) as caught:
            self.parse(impossible)
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.rows[0].forecast_timestamp', caught.exception.field_path)

    def test_a_statement_of_another_path_is_refused(self):
        """A statement rendered from another covariate path is not parsed with this path."""
        other = path_for(record=proposal(old='200', new='50'))
        shifted = path_for(anchor='2026-10-01T23:00:00',
            record=proposal(period={'start': '2026-10-02', 'end': '2026-10-05'}))
        cases = [(statement, '$.statement.level_mw') for statement in render_statements(other)]
        cases.append((render_statements(shifted)[0], '$.statement.sql'))  # same levels, moved W
        for statement, field_path in cases:
            with self.subTest(call=statement.call, field=field_path):
                with self.assertRaises(WhatIfError) as caught:
                    self.parse(result_rows(), statement=statement)
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual(field_path, caught.exception.field_path)
                self.assertTrue(caught.exception.rule.strip())

    def test_a_statement_is_verified_field_by_field_against_this_path(self):
        broken = [('call', replace(self.prior, call='C'), '$.statement.call'),
            ('call-type', replace(self.prior, call=[]), '$.statement.call'),
            ('role', replace(self.prior, role='accepted'), '$.statement.role'),
            ('role-type', replace(self.prior, role=None), '$.statement.role'),
            ('level', replace(self.prior, level_mw='7'), '$.statement.level_mw'),
            ('sql', replace(self.prior, sql=self.prior.sql + '\n'), '$.statement.sql'),
            ('digest', replace(self.prior, path_digest='0' * 64), '$.statement.path_digest')]
        for name, statement, field_path in broken:
            with self.subTest(field=name):
                with self.assertRaises(WhatIfError) as caught:
                    self.parse(result_rows(), statement=statement)
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual(field_path, caught.exception.field_path)
                self.assertTrue(caught.exception.rule.strip())
        self.assertEqual('A', self.parse(result_rows()).call)             # this path's A statement
        self.assertEqual('B', self.parse(result_rows(), statement=self.accepted).call)

    def test_the_history_digest_argument_must_be_a_digest(self):
        for value in (None, '', 'c' * 63, 'C' * 64, 7):
            with self.subTest(value=value):
                with self.assertRaises(WhatIfError) as caught:
                    parse_forecast_rows(result_rows(), self.path, self.prior,
                        history_digest_value=value, execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual('$.history_digest', caught.exception.field_path)

    def test_the_receipt_defaults_to_an_unknown_availability(self):
        self.assertEqual('unknown', self.parse(result_rows()).availability_basis)
        call = self.parse(result_rows(), availability_basis=KNOWN_BASIS)
        self.assertEqual(KNOWN_BASIS, call.as_dict()['availability_basis'])
        for value in ('', '  ', None, 1):
            with self.subTest(value=value):
                with self.assertRaises(WhatIfError) as caught:
                    self.parse(result_rows(), availability_basis=value)
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
                self.assertEqual('$.availability_basis', caught.exception.field_path)

    def test_an_oversized_integer_in_a_forecast_field_is_refused_typed(self):
        """A finite-looking integer the type check admits cannot escape as an OverflowError."""
        for name in ('value', 'prediction_interval_lower_bound', 'prediction_interval_upper_bound'):
            rows = result_rows()
            rows[0]['price_php_mwh'][name] = 10 ** 400
            with self.subTest(field=name):
                with self.assertRaises(WhatIfError) as caught:
                    self.parse(rows)
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual(f'$.rows[0].price_php_mwh.{name}', caught.exception.field_path)
                self.assertEqual('a finite numeric value', caught.exception.rule)

    def test_incompatible_results_are_refused_with_a_reason(self):
        def drop_one(rows):
            return rows[:-1]

        def nonempty_status(rows):
            rows[3]['price_php_mwh']['ai_forecast_status'] = 'TIMESFM_ERROR: bad input'
            return rows

        def off_grid(rows):
            rows[5]['forecast_timestamp'] = hour_text(6)[:14] + '30:00 UTC'
            return rows

        def shifted_grid(rows):
            return [dict(row, forecast_timestamp=hour_text(index) + ' UTC')
                for index, row in enumerate(rows, 2)]

        def unordered_bounds(rows):
            rows[7]['price_php_mwh']['prediction_interval_lower_bound'] = 9999.0
            return rows

        def missing_field(rows):
            del rows[9]['price_php_mwh']['prediction_interval_lower_bound']
            return rows

        def wrong_model(rows):
            rows[1]['model'] = 'TimesFM 2.5'
            return rows

        def wrong_series(rows):
            rows[11]['series_id'] = 'CLUZ'
            return rows

        def duplicate_hour(rows):
            rows[13]['forecast_timestamp'] = rows[12]['forecast_timestamp']
            return rows

        def null_value(rows):
            rows[14]['price_php_mwh']['value'] = None
            return rows

        def impossible_timestamp(rows):
            rows[6]['forecast_timestamp'] = hour_text(7)[:14] + ':99 UTC'
            return rows

        def missing_timestamp(rows):
            del rows[4]['forecast_timestamp']
            return rows

        def oversized_value(rows):
            rows[2]['price_php_mwh']['value'] = 10 ** 400
            return rows

        for mutate in (drop_one, nonempty_status, off_grid, shifted_grid, unordered_bounds,
                missing_field, wrong_model, wrong_series, duplicate_hour, null_value,
                impossible_timestamp, missing_timestamp, oversized_value):
            with self.subTest(mutation=mutate.__name__):
                with self.assertRaises(WhatIfError) as caught:
                    self.parse(mutate(result_rows()))
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertTrue(caught.exception.rule.strip())
                self.assertTrue(caught.exception.field_path.startswith('$.'))


class PairTests(unittest.TestCase):
    """The injected transport, the per-step difference and the labels."""

    def test_pair_difference_aggregates_and_labels(self):
        path = path_for()
        injected = transport()
        pair = run_pair(path, injected, observed(), execution_mode='synthetic fixture')
        self.assertEqual(2, len(injected.calls))
        self.assertEqual(['A', 'B'], [statement.call for statement in injected.calls])
        self.assertEqual(['prior', 'accepted'], [call.role for call in pair.calls])
        self.assertEqual(48, len(pair.steps))
        self.assertEqual([5.0, 5.0, 5.0], [pair.steps[0].delta_value, pair.steps[0].delta_lower,
            pair.steps[0].delta_upper])
        self.assertEqual({'n_steps': 48, 'mean_delta_w': 5.0, 'max_abs_delta': 5.0},
            pair.aggregates)
        self.assertEqual(pair.calls[0].history_digest, pair.calls[1].history_digest)
        self.assertEqual({'feature_status': 'Preview', 'interpretation': 'directional',
            'content_kind': 'simulation output', 'execution_mode': 'synthetic fixture',
            'consequences': 'computed'}, {key: pair.labels[key] for key in
                ('feature_status', 'interpretation', 'content_kind', 'execution_mode', 'consequences')})
        self.assertIn('attenuate', pair.labels['caveat'])
        self.assertIn('never an event probability', pair.labels['caveat'])
        self.assertTrue(pair.verdict['compatible'])
        self.assertEqual('uncomputed', pair.proposal_consequences)
        self.assertEqual(pair.calls[0].history_digest, pair.verdict['history_digest'])

    def test_difference_of_a_single_pair_admits_zero_delta(self):
        pair = run_pair(path_for(), transport(shift_a=7.0, shift_b=7.0), observed(),
            execution_mode='synthetic fixture')
        self.assertEqual({'n_steps': 48, 'mean_delta_w': 0.0, 'max_abs_delta': 0.0}, pair.aggregates)

    def test_two_identical_paths_are_refused(self):
        path = path_for(record=proposal(old='0', new='0'))
        prior, accepted = render_statements(path)
        self.assertEqual(prior.sql, accepted.sql)
        with self.assertRaises(WhatIfError) as caught:
            run_pair(path, transport(), observed(), execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.calls[].path_digest', caught.exception.field_path)

    def test_equivalent_covariate_spellings_are_one_model_input_and_refused(self):
        """The model receives the number, not the spelling: equal levels, nothing to compare."""
        for old, new in (('0', '0.0'), ('0', '00'), ('100', '100.0'), ('100', '0100'),
                ('5', '+5.000'), ('1.5', '1.50'),
                # different decimals, one FLOAT64: the CAST hands the model the same number
                ('0.1', '0.1000000000000000000000001'), ('2', '2.000000000000000000000000001')):
            with self.subTest(old=old, new=new):
                path = path_for(record=proposal(old=old, new=new))
                prior, accepted = render_statements(path)
                self.assertEqual(prior.path_digest, accepted.path_digest)
                with self.assertRaises(WhatIfError) as caught:
                    run_pair(path, transport(), observed(), execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].path_digest', caught.exception.field_path)
                self.assertIn('numerically equal', caught.exception.rule)

    def test_the_reviewed_level_spelling_is_kept_for_provenance(self):
        path = path_for(record=proposal(old='100.50', new='+0.0'))
        prior, accepted = render_statements(path)
        self.assertNotEqual(prior.path_digest, accepted.path_digest)
        self.assertEqual({'prior_mw': '100.50', 'accepted_mw': '0.0'},
            covariate_basis(path)['accepted_levels'])
        self.assertEqual(['100.50', '0.0'], [prior.level_mw, accepted.level_mw])
        self.assertIn('CAST(100.50 AS FLOAT64)', prior.sql)
        self.assertIn('CAST(0.0 AS FLOAT64)', accepted.sql)
        pair = run_pair(path, transport(), observed(), execution_mode='synthetic fixture')
        self.assertTrue(pair.verdict['compatible'])
        self.assertEqual(['100.50', '0.0'], [call.level_mw for call in pair.calls])

    def test_a_level_with_no_float64_value_keeps_a_stable_digest(self):
        """Beyond FLOAT64 range there is no float to unify on: the digest stays typed, not a crash."""
        beyond = '1' + '0' * 400
        path = path_for(record=proposal(old=beyond, new='0.00000000000000000000000001'))
        prior, accepted = render_statements(path)
        for statement in (prior, accepted):
            self.assertRegex(statement.path_digest, r'[0-9a-f]{64}')
        self.assertNotEqual(prior.path_digest, accepted.path_digest)
        self.assertEqual([path_digest(path, 'A'), path_digest(path, 'B')],
            [prior.path_digest, accepted.path_digest])                  # stable across calls
        self.assertIn(f'CAST({beyond} AS FLOAT64)', prior.sql)          # spelling kept for the SQL
        self.assertEqual(beyond, covariate_basis(path)['accepted_levels']['prior_mw'])

    def test_a_hand_built_pair_whose_levels_are_one_number_is_refused(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        # One number, other spellings, and a stale digest that would otherwise hide the equality.
        for spelling in ('100.0', '+100.000', '100.0000000000000000000000001'):
            with self.subTest(level=spelling):
                forged = replace(right, level_mw=spelling, path_digest='0' * 64)
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, forged, execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].level_mw', caught.exception.field_path)
                self.assertIn('nothing to compare', caught.exception.rule)
        for junk in ('x', '', '1e3', None):
            with self.subTest(level=junk):
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, replace(right, level_mw=junk),
                        execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].level_mw', caught.exception.field_path)

    def test_an_overflowing_difference_is_refused_and_the_mean_never_overflows(self):
        path = path_for()
        huge, top = 1e308, 1.797e308
        cases = [('$.difference[0].delta_value', (-huge, -huge, -huge), (huge, huge, huge)),
            ('$.difference[0].delta_lower', (-top, 0.0, 0.0), (top, top, top)),
            ('$.difference[0].delta_upper', (-huge, -huge, -huge), (-huge, -huge, huge))]
        for field_path, first, second in cases:
            with self.subTest(field=field_path):
                with self.assertRaises(WhatIfError) as caught:
                    run_pair(path, extremes(first, second), observed(),
                        execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual(field_path, caught.exception.field_path)
                self.assertIn('finite', caught.exception.rule)
        # 48 finite differences of 1e308: a naive sum overflows, the scaled mean does not.
        pair = run_pair(path, extremes((-huge, -huge, -huge), (0.0, 0.0, 0.0)), observed(),
            execution_mode='synthetic fixture')
        self.assertTrue(math.isfinite(pair.aggregates['mean_delta_w']))
        self.assertLess(abs(pair.aggregates['mean_delta_w'] - huge), huge * 1e-9)

    def test_a_hand_built_step_with_a_junk_value_or_no_steps_is_refused(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        for field in ('value', 'lower', 'upper'):
            with self.subTest(field=field):
                broken = replace(right,
                    steps=(replace(right.steps[0], **{field: 'junk'}),) + right.steps[1:])
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, broken, execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual(f'$.calls[].steps[0].{field}', caught.exception.field_path)
        for junk in ((), None, 7, True, 'x'):                             # not a step sequence
            with self.subTest(steps=junk):
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, replace(right, steps=junk, horizon_effective=-1),
                        execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].steps', caught.exception.field_path)
        empty = {'steps': (), 'horizon_effective': 0}                     # both calls empty
        with self.assertRaises(WhatIfError) as caught:
            compare_calls(replace(left, **empty), replace(right, **empty),
                execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.calls[].steps', caught.exception.field_path)

    def test_a_history_mismatch_is_refused(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='c' * 64,
            execution_mode='synthetic fixture')
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        with self.assertRaises(WhatIfError) as caught:
            compare_calls(left, right, execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_HISTORY_MISMATCH', caught.exception.code)
        self.assertEqual('$.calls[].history_digest', caught.exception.field_path)
        self.assertIn('one identical ordered model history', caught.exception.rule)

    def test_the_pair_receipts_carry_the_availability_summary(self):
        path = path_for()
        pair = run_pair(path, transport(), observed(), execution_mode='synthetic fixture')
        self.assertEqual(['unknown', 'unknown'], [call.availability_basis for call in pair.calls])
        self.assertEqual('unknown', pair.calls[0].as_dict()['availability_basis'])
        self.assertEqual('unknown', pair.verdict['checks']['availability_basis'])
        known = [dict(row, available_at=hour_text(-1), availability_basis=KNOWN_BASIS)
            for row in observed()]
        pair = run_pair(path, transport(), known, execution_mode='synthetic fixture')
        self.assertEqual([KNOWN_BASIS, KNOWN_BASIS], [call.availability_basis for call in pair.calls])

    def test_a_pair_label_cannot_contradict_its_calls(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        with self.assertRaises(WhatIfError) as caught:
            compare_calls(left, right, execution_mode='live inference')
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.calls[].labels.execution_mode', caught.exception.field_path)
        self.assertIn('never relabelled', caught.exception.rule)
        other = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            execution_mode='stored run')
        for mode in ('live inference', 'synthetic fixture', 'preview'):
            with self.subTest(mode=mode):
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, other, execution_mode=mode)
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].labels.execution_mode', caught.exception.field_path)
                self.assertIn('one execution', caught.exception.rule)
        pair = compare_calls(left, right, execution_mode='synthetic fixture')
        self.assertEqual('synthetic fixture', pair.labels['execution_mode'])
        self.assertEqual(['synthetic fixture', 'synthetic fixture'],
            [call.labels['execution_mode'] for call in pair.calls])

    def test_a_call_with_a_mismatched_step_count_is_refused(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        for steps in (right.steps[:-1], right.steps + right.steps[:1], ()):
            with self.subTest(steps=len(steps)):
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(left, replace(right, steps=steps),
                        execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].steps', caught.exception.field_path)

    def test_a_pair_with_two_availability_summaries_is_refused(self):
        path = path_for()
        prior, accepted = render_statements(path)
        rows = result_rows()
        left = parse_forecast_rows(rows, path, prior, history_digest_value='d' * 64,
            execution_mode='synthetic fixture')
        right = parse_forecast_rows(rows, path, accepted, history_digest_value='d' * 64,
            availability_basis=KNOWN_BASIS, execution_mode='synthetic fixture')
        with self.assertRaises(WhatIfError) as caught:
            compare_calls(left, right, execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.calls[].availability_basis', caught.exception.field_path)

    def test_the_receipts_carry_the_relation_of_their_path(self):
        path = path_for()
        pair = run_pair(path, transport(), observed(), execution_mode='synthetic fixture')
        self.assertEqual([path.series_relation, path.series_relation],
            [call.series_relation for call in pair.calls])
        self.assertEqual(path.series_relation, pair.calls[0].as_dict()['series_relation'])
        self.assertEqual(path.series_relation, pair.verdict['checks']['series_relation'])

    def test_a_pair_of_two_relations_is_refused(self):
        """One pair is one region in one relation: two tables cannot carry the one-history verdict.

        The history digest is over the ordered rows and the relation is not one of them, so honest
        digests are equal across two tables; a pair whose paths differ only in `series_relation`
        must be refused on the receipt field, not accepted on the equal history.
        """
        first = path_for()
        second = replace(first, series_relation='synthetic-project.whatif.other_hourly_fixture')
        rows = result_rows()
        prior = parse_forecast_rows(rows, first, render_statements(first)[0],
            history_digest_value='d' * 64, execution_mode='synthetic fixture')
        accepted = parse_forecast_rows(rows, second, render_statements(second)[1],
            history_digest_value='d' * 64, execution_mode='synthetic fixture')
        self.assertEqual(history_digest(context_rows(observed(), first), first),
            history_digest(context_rows(observed(), second), second))     # the relation is no row
        self.assertNotEqual(prior.path_digest, accepted.path_digest)      # but it is in the path
        with self.assertRaises(WhatIfError) as caught:
            compare_calls(prior, accepted, execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
        self.assertEqual('$.calls[].series_relation', caught.exception.field_path)
        self.assertTrue(caught.exception.rule.strip())
        # A junk relation cannot ride on a hand-built receipt either.
        for junk in (None, 7, '', 'synthetic-project.whatif',
                '`synthetic-project.whatif.price_hourly_fixture`'):
            with self.subTest(relation=junk):
                with self.assertRaises(WhatIfError) as caught:
                    compare_calls(replace(prior, series_relation=junk), accepted,
                        execution_mode='synthetic fixture')
                self.assertEqual('WHATIF_RESULT_INCOMPATIBLE', caught.exception.code)
                self.assertEqual('$.calls[].series_relation', caught.exception.field_path)
                self.assertTrue(caught.exception.rule.strip())

    def test_run_pair_rejects_a_missing_transport(self):
        with self.assertRaises(WhatIfError) as caught:
            run_pair(path_for(), None, observed(), execution_mode='synthetic fixture')
        self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)
        self.assertEqual('$.transport', caught.exception.field_path)

    def test_uncomputed_fallback_records_its_reason_and_keeps_the_labels(self):
        reason = uncomputed(build_error(self, horizon=2000), execution_mode='live inference')
        self.assertEqual('uncomputed', reason['consequences'])
        self.assertEqual('WHATIF_HORIZON_RANGE', reason['error']['code'])
        self.assertEqual('uncomputed', reason['labels']['consequences'])
        self.assertIn('WHATIF_HORIZON_RANGE at $.horizon', reason['labels']['uncomputed_reason'])
        self.assertEqual('Preview', reason['labels']['feature_status'])
        plain = uncomputed('BigQuery job failed', execution_mode='retrospective replay')
        self.assertEqual('BigQuery job failed', plain['uncomputed_reason'])
        self.assertIsNone(plain['error'])

    def test_labels_refuse_an_unlabelled_or_contradictory_result(self):
        cases = [lambda: labels('live'), lambda: labels('synthetic fixture', 'computed', 'because'),
            lambda: labels('synthetic fixture', 'uncomputed'),
            lambda: labels('synthetic fixture', 'uncomputed', '  '),
            lambda: labels('synthetic fixture', 'partial')]
        for index, call in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(WhatIfError) as caught:
                    call()
                self.assertEqual('WHATIF_CONFIG_INVALID', caught.exception.code)

    def test_contract_constants_are_the_frozen_ones(self):
        self.assertEqual('TimesFM 3.0', MODEL)
        self.assertEqual('assumed Asia/Manila, unverified (scripts/data/sql/02_intervals.sql:2-3)',
            TIMEZONE_CONVENTION)
        self.assertEqual('constructed: level held constant; not observed, not an accepted assumption',
            COVARIATE_PAST_BASIS)

    def test_no_credential_client_or_network_import_in_the_module(self):
        source = MODULE.read_text(encoding='utf-8')
        for token in ('import os', 'import socket', 'import subprocess', 'import urllib',
                'import requests', 'google.cloud', 'googleapiclient', 'os.environ', 'getenv'):
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        self.assertIn('canonical_bytes', source)


if __name__ == '__main__':
    unittest.main()
