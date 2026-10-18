"""Behavioral tests for the M0 synthetic baseline evaluation harness.

Fixtures in ``tests/fixtures/modeling`` are labeled synthetic inputs with
hand-calculated expectations.  Inline cases exercise validation, as-of
filtering, the bounded provider port, shared comparison denominators,
immutability and the deterministic report digest.
"""
import copy
import dataclasses
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling import (
    PersistenceProvider,
    Prediction,
    ProviderError,
    ProviderLookupError,
    build_config,
    build_input,
    build_partition,
    builtin_providers_by_name,
    default_providers,
    run_evaluation,
)
from src.modeling.errors import (
    BOOLEAN_AS_NUMBER,
    DUPLICATE_TIMESTAMP,
    INVALID_PROVIDER,
    INVALID_TIMESTAMP,
    INVALID_TYPE,
    INVALID_VALUE,
    MALFORMED_PREDICTION,
    MISSING_SEASON_SLOT,
    MISSING_TRUTH,
    MIXED_ENTITIES,
    MIXED_UNITS,
    NAIVE_TIMESTAMP,
    NO_ELIGIBLE_HISTORY,
    NON_FINITE_NUMBER,
    NON_FINITE_PREDICTION,
    ORIGIN_ORDER,
    OVERFLOW,
    REAL_INPUT_UNSUPPORTED,
    UNORDERED_TIMESTAMPS,
    WRONG_HORIZON,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "modeling"

T0 = "2026-01-01T00:00:00+00:00"
T1 = "2026-01-01T01:00:00+00:00"
T1_30 = "2026-01-01T01:30:00+00:00"
T2 = "2026-01-01T02:00:00+00:00"
T3 = "2026-01-01T03:00:00+00:00"
T4 = "2026-01-01T04:00:00+00:00"
T5 = "2026-01-01T05:00:00+00:00"
T6 = "2026-01-01T06:00:00+00:00"


def h(timestamp, value, revision="rev-1"):
    """Available exactly at its own timestamp."""
    return {
        "timestamp": timestamp,
        "value": value,
        "source_revision": revision,
        "availability": timestamp,
    }


def unknown(timestamp, value, reason, revision="rev-1"):
    return {
        "timestamp": timestamp,
        "value": value,
        "source_revision": revision,
        "availability": None,
        "unknown_reason": reason,
    }


def late(timestamp, value, availability, revision="rev-1"):
    return {
        "timestamp": timestamp,
        "value": value,
        "source_revision": revision,
        "availability": availability,
    }


def cfg(origins, horizon=2, lag=2, step=3600, entity="SYN-A", unit="MW"):
    return {
        "entity_type": "region",
        "entity_id": entity,
        "unit": unit,
        "origins": origins,
        "horizon": horizon,
        "step_seconds": step,
        "seasonal_lag": lag,
    }


def part(observations, entity="SYN-A", unit="MW"):
    return {
        "entity_type": "region",
        "entity_id": entity,
        "unit": unit,
        "observations": observations,
    }


def make_input(history, truth, config, synthetic=True):
    return {
        "synthetic": synthetic,
        "config": config,
        "history": part(history, config["entity_id"], config["unit"]),
        "truth": part(truth, config["entity_id"], config["unit"]),
    }


def standard_input():
    config = cfg([T2], horizon=2, lag=2)
    history = [h(T0, 10.0), h(T1, 20.0), h(T2, 30.0)]
    truth = [h(T3, 40.0), h(T4, 50.0)]
    return make_input(history, truth, config)


def build_codes(data):
    result = build_input(data)
    return {error.code for error in result.errors}


def outcome_codes(outcome):
    return {error.code for error in outcome.errors}


def error_paths(errors, code):
    """Return the sorted paths of every error carrying ``code``."""
    return sorted(error.path for error in errors if error.code == code)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fixture_source(data):
    """The evaluable subset of a labeled fixture (no ``models``/``expected``)."""
    return {key: data[key] for key in ("synthetic", "config", "history", "truth")}


class _WrongLength:
    name = "wrong_length"
    version = "test-0"
    formula = "returns fewer values than the horizon"

    def predict(self, context):
        return Prediction((1.0,), (context.origin,))


class _NonFinite:
    name = "non_finite"
    version = "test-0"
    formula = "returns a NaN value"

    def predict(self, context):
        return Prediction((float("nan"), 1.0), (context.origin,))


class _NonNumeric:
    name = "non_numeric"
    version = "test-0"
    formula = "returns a non-numeric value"

    def predict(self, context):
        return Prediction(("not-a-number", 1.0), (context.origin,))


class _Failing:
    name = "failing"
    version = "test-0"
    formula = "raises a declared provider error"

    def predict(self, context):
        raise ProviderError(NO_ELIGIBLE_HISTORY)


class _Boom:
    name = "boom"
    version = "test-0"
    formula = "raises an unexpected exception"

    def predict(self, context):
        raise RuntimeError("unexpected provider bug")


class _HugeValue:
    name = "huge_value"
    version = "test-0"
    formula = "returns an integer too large for a finite float"

    def predict(self, context):
        return Prediction((10**400, 1.0), (context.origin,))


class _BadMetadata:
    name = "\ud800"
    version = "test-0"
    formula = "carries a lone surrogate in provider metadata"

    def predict(self, context):
        return Prediction((1.0, 1.0), (context.origin,))


class _AlienProvenance:
    name = "alien_provenance"
    version = "test-0"
    formula = "declares a provenance timestamp absent from the eligible context"

    def predict(self, context):
        return Prediction((1.0, 1.0), (context.origin + timedelta(hours=99),))


class _DuplicateProvenance:
    name = "duplicate_provenance"
    version = "test-0"
    formula = "declares the same provenance timestamp twice"

    def predict(self, context):
        return Prediction((1.0, 1.0), (context.origin, context.origin))


class _ScalarValue:
    name = "scalar_value"
    version = "test-0"
    formula = "returns a bare float instead of a horizon-aligned tuple"

    def predict(self, context):
        return Prediction(3.0, (context.origin,))


class _NoneValue:
    name = "none_value"
    version = "test-0"
    formula = "returns None instead of a horizon-aligned tuple"

    def predict(self, context):
        return Prediction(None, (context.origin,))


class _Healthy:
    name = "healthy"
    version = "test-0"
    formula = "returns a valid horizon-aligned prediction"

    def predict(self, context):
        return Prediction(tuple(1.0 for _ in range(context.horizon)), (context.origin,))


class _TogglingBad:
    """Valid at one origin, malformed at another.

    Keyed off ``context.origin`` rather than call order so the shape is
    deterministic.  At the ``malformed_origin`` it returns the configured
    non-iterable ``malformed_value`` (a bare float or ``None``), so both
    non-iterable shapes are exercised while the earlier origin stays
    successfully scored.
    """

    name = "toggling_bad"
    version = "test-0"
    formula = "returns a valid tuple at one origin and a scalar/None at another"

    def __init__(self, malformed_origin, malformed_value):
        self.malformed_origin = malformed_origin
        self.malformed_value = malformed_value

    def predict(self, context):
        if context.origin != self.malformed_origin:
            return Prediction(
                tuple(1.0 for _ in range(context.horizon)), (context.origin,)
            )
        return Prediction(self.malformed_value, (context.origin,))


class FixtureBaselines(unittest.TestCase):
    def load(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def source(self, data):
        return {key: data[key] for key in ("synthetic", "config", "history", "truth")}

    def test_two_origin_hand_calculated_metrics(self):
        data = self.load("synthetic_two_origin.json")
        outcome = run_evaluation(self.source(data), builtin_providers_by_name(data["models"]))
        self.assertTrue(outcome.ok, outcome.errors)
        report = outcome.report
        self.assertEqual(2, report.common_origin_count)
        self.assertEqual(2, report.total_origin_count)
        self.assertAlmostEqual(1.0, report.coverage)

        by_model = {summary.model: summary for summary in report.summaries}
        persistence = by_model["persistence"]
        self.assertEqual(2, persistence.scored_origins)
        self.assertEqual(4, persistence.scored_pairs)
        self.assertAlmostEqual(15.0, persistence.mae)
        self.assertAlmostEqual(math.sqrt(250.0), persistence.rmse)
        self.assertEqual(
            [(1, 10.0, 10.0), (2, 20.0, 20.0)],
            [(metric.lead, metric.mae, metric.rmse) for metric in persistence.per_lead],
        )

        seasonal = by_model["seasonal_naive"]
        self.assertAlmostEqual(20.0, seasonal.mae)
        self.assertAlmostEqual(20.0, seasonal.rmse)

    def test_multi_season_modulo_indexing(self):
        data = self.load("synthetic_multi_season.json")
        outcome = run_evaluation(self.source(data), builtin_providers_by_name(data["models"]))
        self.assertTrue(outcome.ok, outcome.errors)
        report = outcome.report
        self.assertEqual(1, report.common_origin_count)
        forecasts = {forecast.model: forecast for forecast in report.origins[0].forecasts}
        self.assertEqual((5.0, 5.0, 5.0, 5.0, 5.0), forecasts["persistence"].values)
        self.assertEqual((4.0, 5.0, 4.0, 5.0, 4.0), forecasts["seasonal_naive"].values)
        by_model = {summary.model: summary for summary in report.summaries}
        self.assertAlmostEqual(2.6, by_model["seasonal_naive"].mae)
        self.assertAlmostEqual(3.0, by_model["seasonal_naive"].rmse)

    def test_report_carries_visible_synthetic_label(self):
        data = self.load("synthetic_two_origin.json")
        outcome = run_evaluation(self.source(data), builtin_providers_by_name(data["models"]))
        report = outcome.report
        self.assertTrue(report.synthetic)
        self.assertTrue(report.to_dict()["synthetic"])
        self.assertIn('"synthetic":true', report.to_json())


class AvailabilityAndContext(unittest.TestCase):
    def test_equality_availability_at_origin_is_eligible(self):
        config = cfg([T2], horizon=1, lag=1)
        history = [h(T0, 10.0), h(T2, 30.0)]
        truth = [h(T3, 40.0)]
        outcome = run_evaluation(make_input(history, truth, config), providers=[PersistenceProvider()])
        self.assertTrue(outcome.ok, outcome.errors)
        origin = outcome.report.origins[0]
        self.assertEqual(2, origin.counts.eligible)
        self.assertEqual(0, origin.counts.excluded_late)
        self.assertEqual((30.0,), origin.forecasts[0].values)
        self.assertEqual(0, origin.forecasts[0].used[0].age_steps)

    def test_unknown_and_late_availability_counted_and_excluded(self):
        config = cfg([T2], horizon=1, lag=1)
        history = [
            h(T0, 10.0),
            unknown(T1, 20.0, "feed not confirmed"),
            late(T1_30, 25.0, T4),
            h(T2, 30.0),
        ]
        truth = [h(T3, 40.0)]
        outcome = run_evaluation(make_input(history, truth, config), providers=[PersistenceProvider()])
        self.assertTrue(outcome.ok, outcome.errors)
        origin = outcome.report.origins[0]
        self.assertEqual(4, origin.counts.total)
        self.assertEqual(2, origin.counts.eligible)
        self.assertEqual(1, origin.counts.excluded_unknown)
        self.assertEqual(1, origin.counts.excluded_late)
        self.assertEqual((30.0,), origin.forecasts[0].values)

    def test_future_history_is_not_shown(self):
        config = cfg([T2], horizon=1, lag=1)
        history = [h(T0, 10.0), h(T3, 99.0)]
        truth = [h(T3, 40.0)]
        outcome = run_evaluation(make_input(history, truth, config), providers=[PersistenceProvider()])
        origin = outcome.report.origins[0]
        self.assertEqual(1, origin.counts.excluded_future)
        self.assertEqual((10.0,), origin.forecasts[0].values)

    def test_truth_partition_never_enters_context(self):
        config = cfg([T2], horizon=1, lag=1)
        history = [h(T0, 10.0)]
        truth = [h(T2, 999.0), h(T3, 40.0)]
        outcome = run_evaluation(make_input(history, truth, config), providers=[PersistenceProvider()])
        origin = outcome.report.origins[0]
        context_times = [row.timestamp.isoformat() for row in origin.context]
        self.assertNotIn(T2, context_times)
        self.assertEqual((10.0,), origin.forecasts[0].values)

        changed_truth = [h(T2, 111.0), h(T3, 222.0)]
        changed = run_evaluation(
            make_input(history, changed_truth, config), providers=[PersistenceProvider()]
        )
        self.assertEqual(
            origin.forecasts[0].values, changed.report.origins[0].forecasts[0].values
        )


class SharedDenominator(unittest.TestCase):
    def test_missing_season_excludes_origin_for_every_model(self):
        config = cfg([T2, T3], horizon=1, lag=2)
        history = [h(T0, 10.0), h(T1, 20.0), h(T3, 40.0)]  # T2 season slot missing
        truth = [h(T3, 40.0), h(T4, 50.0)]
        outcome = run_evaluation(make_input(history, truth, config))
        self.assertTrue(outcome.ok, outcome.errors)
        report = outcome.report
        self.assertEqual(0, report.common_origin_count)
        by_model = {summary.model: summary for summary in report.summaries}
        persistence = by_model["persistence"]
        self.assertEqual(2, persistence.successful_origins)
        self.assertEqual(0, persistence.scored_origins)
        self.assertEqual(0, persistence.scored_pairs)
        self.assertIsNone(persistence.mae)
        self.assertIsNone(persistence.rmse)
        seasonal = by_model["seasonal_naive"]
        self.assertEqual(0, seasonal.successful_origins)
        self.assertEqual(
            [(MISSING_SEASON_SLOT, 2)],
            [(item.code, item.count) for item in seasonal.exclusions],
        )

    def test_no_common_origin_gives_null_metrics(self):
        config = cfg([T2], horizon=2, lag=1)
        history = [h(T0, 10.0), h(T1, 20.0)]
        truth = []
        outcome = run_evaluation(make_input(history, truth, config))
        self.assertTrue(outcome.ok, outcome.errors)
        report = outcome.report
        self.assertEqual(0, report.common_origin_count)
        for summary in report.summaries:
            self.assertEqual(0, summary.scored_pairs)
            self.assertEqual(0, summary.scored_origins)
            self.assertIsNone(summary.mae)
            self.assertIsNone(summary.rmse)
        self.assertNotIn("NaN", report.to_json())

    def test_incomplete_truth_excludes_origin(self):
        config = cfg([T2], horizon=2, lag=1)
        history = [h(T0, 10.0), h(T1, 20.0)]
        truth = [h(T3, 40.0)]  # T4 missing
        outcome = run_evaluation(make_input(history, truth, config))
        self.assertTrue(outcome.ok, outcome.errors)
        origin = outcome.report.origins[0]
        self.assertFalse(origin.truth_ok)
        self.assertEqual(MISSING_TRUTH, origin.truth_code)
        self.assertFalse(origin.in_common)
        self.assertEqual(0, outcome.report.common_origin_count)


class ProviderPort(unittest.TestCase):
    def test_wrong_horizon_is_explicit_exclusion(self):
        outcome = run_evaluation(standard_input(), providers=[_WrongLength()])
        self.assertTrue(outcome.ok, outcome.errors)
        forecast = outcome.report.origins[0].forecasts[0]
        self.assertFalse(forecast.ok)
        self.assertEqual(WRONG_HORIZON, forecast.exclusion_code)

    def test_non_finite_output_is_explicit_exclusion(self):
        outcome = run_evaluation(standard_input(), providers=[_NonFinite()])
        self.assertTrue(outcome.ok, outcome.errors)
        forecast = outcome.report.origins[0].forecasts[0]
        self.assertEqual(NON_FINITE_PREDICTION, forecast.exclusion_code)

    def test_non_numeric_output_is_explicit_exclusion(self):
        outcome = run_evaluation(standard_input(), providers=[_NonNumeric()])
        self.assertTrue(outcome.ok, outcome.errors)
        forecast = outcome.report.origins[0].forecasts[0]
        self.assertEqual(MALFORMED_PREDICTION, forecast.exclusion_code)

    def test_provider_error_is_preserved_as_exclusion(self):
        outcome = run_evaluation(standard_input(), providers=[_Failing()])
        self.assertTrue(outcome.ok, outcome.errors)
        forecast = outcome.report.origins[0].forecasts[0]
        self.assertEqual(NO_ELIGIBLE_HISTORY, forecast.exclusion_code)

    def test_unexpected_provider_exception_propagates(self):
        with self.assertRaises(RuntimeError):
            run_evaluation(standard_input(), providers=[_Boom()])

    def test_invalid_provider_is_rejected_without_crashing(self):
        for providers in ([object()], ["not-a-provider"]):
            with self.subTest(providers=providers):
                outcome = run_evaluation(standard_input(), providers=providers)
                self.assertFalse(outcome.ok)
                self.assertIn(INVALID_PROVIDER, outcome_codes(outcome))

    def test_default_providers_are_the_two_builtins(self):
        names = [provider.name for provider in default_providers()]
        self.assertEqual(["persistence", "seasonal_naive"], names)


class InputValidation(unittest.TestCase):
    def test_duplicate_and_timezone_equivalent_timestamps_rejected(self):
        config = cfg([T2], horizon=1, lag=1)
        duplicate = build_codes(make_input([h(T0, 1.0), h(T0, 2.0)], [h(T3, 1.0)], config))
        self.assertIn(DUPLICATE_TIMESTAMP, duplicate)

        equivalent = [
            h("2026-01-01T02:00:00+00:00", 1.0),
            h("2026-01-01T03:00:00+01:00", 2.0),
        ]
        codes = build_codes(make_input(equivalent, [h(T3, 1.0)], config))
        self.assertIn(DUPLICATE_TIMESTAMP, codes)

    def test_unordered_timestamps_rejected(self):
        config = cfg([T2], horizon=1, lag=1)
        codes = build_codes(make_input([h(T1, 1.0), h(T0, 2.0)], [h(T3, 1.0)], config))
        self.assertIn(UNORDERED_TIMESTAMPS, codes)

    def test_naive_timestamp_rejected(self):
        config = cfg([T2], horizon=1, lag=1)
        row = {
            "timestamp": "2026-01-01T02:00:00",
            "value": 1.0,
            "source_revision": "rev-1",
            "availability": T0,
        }
        codes = build_codes(make_input([row], [h(T3, 1.0)], config))
        self.assertIn(NAIVE_TIMESTAMP, codes)

    def test_units_and_entities_mismatch_rejected(self):
        config = cfg([T2], horizon=1, lag=1)
        history = part([h(T0, 1.0)], entity="SYN-A", unit="MW")
        truth_mwh = part([h(T3, 1.0)], entity="SYN-A", unit="MWh")
        data = {"synthetic": True, "config": config, "history": history, "truth": truth_mwh}
        self.assertIn(MIXED_UNITS, build_codes(data))

        truth_other = part([h(T3, 1.0)], entity="SYN-B", unit="MW")
        data = {"synthetic": True, "config": config, "history": history, "truth": truth_other}
        self.assertIn(MIXED_ENTITIES, build_codes(data))

    def test_non_finite_and_boolean_values_rejected(self):
        config = cfg([T2], horizon=1, lag=1)
        nan_row = {
            "timestamp": T0,
            "value": float("nan"),
            "source_revision": "rev-1",
            "availability": T0,
        }
        self.assertIn(
            NON_FINITE_NUMBER, build_codes(make_input([nan_row], [h(T3, 1.0)], config))
        )
        bool_row = {
            "timestamp": T0,
            "value": True,
            "source_revision": "rev-1",
            "availability": T0,
        }
        self.assertIn(
            BOOLEAN_AS_NUMBER, build_codes(make_input([bool_row], [h(T3, 1.0)], config))
        )

    def test_invalid_configuration_rejected(self):
        cases = [
            (cfg([T2], horizon=0, lag=1), INVALID_VALUE),
            (cfg([T2], horizon=True, lag=1), BOOLEAN_AS_NUMBER),
            (cfg([T2], horizon=1, lag=0), INVALID_VALUE),
            (cfg([T2], horizon=1, lag=1, step=0), INVALID_VALUE),
            (cfg([T3, T2], horizon=1, lag=1), ORIGIN_ORDER),
            (cfg([], horizon=1, lag=1), INVALID_VALUE),
        ]
        for config, expected in cases:
            with self.subTest(expected=expected, config=config):
                codes = build_codes(
                    make_input([h(T0, 1.0)], [h(T3, 1.0)], config)
                )
                self.assertIn(expected, codes)

    def test_malformed_shapes_do_not_raise(self):
        for source in (
            None,
            [],
            5,
            "x",
            {"synthetic": True},
            {"synthetic": True, "config": 5, "history": "x", "truth": {}},
        ):
            with self.subTest(source=repr(source)):
                outcome = run_evaluation(source)
                self.assertFalse(outcome.ok)
                self.assertTrue(outcome.errors)
        for value in (None, [], 3, "x"):
            with self.subTest(value=repr(value)):
                self.assertFalse(build_input(value).ok)
                self.assertFalse(build_config(value).ok)
                self.assertFalse(build_partition(value).ok)

    def test_real_input_unsupported(self):
        data = standard_input()
        data["synthetic"] = False
        self.assertIn(REAL_INPUT_UNSUPPORTED, build_codes(data))
        outcome = run_evaluation(data)
        self.assertFalse(outcome.ok)
        self.assertIn(REAL_INPUT_UNSUPPORTED, outcome_codes(outcome))


class ImmutabilityAndDigest(unittest.TestCase):
    def test_records_are_frozen_and_tuple_backed(self):
        data = standard_input()
        built = build_input(data)
        self.assertTrue(built.ok, built.errors)
        input_ = built.value
        self.assertIsInstance(input_.config.origins, tuple)
        self.assertIsInstance(input_.history.observations, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            input_.config.horizon = 99

        outcome = run_evaluation(input_)
        report = outcome.report
        self.assertIsInstance(report.origins, tuple)
        self.assertIsInstance(report.origins[0].forecasts, tuple)
        self.assertIsInstance(report.origins[0].context, tuple)

        source_rows = data["history"]["observations"]
        before = input_.history.observations
        source_rows.append(h(T5, 123.0))
        self.assertEqual(before, input_.history.observations)

    def test_repeat_runs_are_byte_identical(self):
        data = standard_input()
        first = run_evaluation(data).report
        second = run_evaluation(data).report
        self.assertEqual(first.input_digest, second.input_digest)
        self.assertEqual(first.to_json(), second.to_json())

    def test_digest_changes_with_value_config_and_provenance(self):
        data = standard_input()
        baseline = run_evaluation(data).report.input_digest

        value_changed = copy.deepcopy(data)
        value_changed["history"]["observations"][0]["value"] = 11.0
        self.assertNotEqual(baseline, run_evaluation(value_changed).report.input_digest)

        provenance_changed = copy.deepcopy(data)
        provenance_changed["history"]["observations"][0]["source_revision"] = "rev-other"
        self.assertNotEqual(baseline, run_evaluation(provenance_changed).report.input_digest)

        config_changed = copy.deepcopy(data)
        config_changed["config"]["seasonal_lag"] = 1
        self.assertNotEqual(baseline, run_evaluation(config_changed).report.input_digest)

    def test_report_json_is_pure_and_parseable(self):
        report = run_evaluation(standard_input()).report
        text = report.to_json()
        parsed = json.loads(text)
        self.assertTrue(parsed["synthetic"])
        self.assertNotIn("NaN", text)
        self.assertNotIn("Infinity", text)
        self.assertEqual(report.to_dict()["input_digest"], parsed["input_digest"])

    def test_report_includes_required_metadata(self):
        report = run_evaluation(standard_input()).report
        payload = report.to_dict()
        for key in ("config", "models", "origins", "summaries", "input_digest", "metric_formulas"):
            self.assertIn(key, payload)
        origin = payload["origins"][0]
        for key in ("origin", "targets", "leads", "in_common", "history_counts", "context", "forecasts", "truth"):
            self.assertIn(key, origin)
        model = payload["models"][0]
        self.assertIn("formula", model)
        self.assertIn("per_lead", payload["summaries"][0])


class FutureAppend(unittest.TestCase):
    def test_future_history_does_not_change_earlier_predictions(self):
        config = cfg([T2], horizon=2, lag=2)
        base_history = [h(T0, 10.0), h(T1, 20.0), h(T2, 30.0)]
        truth = [h(T3, 40.0), h(T4, 50.0)]
        base = run_evaluation(make_input(base_history, truth, config))
        extended = run_evaluation(
            make_input(base_history + [h(T3, 999.0), h(T4, 888.0)], truth, config)
        )
        self.assertTrue(base.ok and extended.ok)
        base_values = [(f.model, f.values) for f in base.report.origins[0].forecasts]
        extended_values = [(f.model, f.values) for f in extended.report.origins[0].forecasts]
        self.assertEqual(base_values, extended_values)
        self.assertEqual(2, extended.report.origins[0].counts.excluded_future)


class BuildResultContracts(unittest.TestCase):
    def test_later_origins_use_history_supplied_for_that_origin(self):
        config = cfg([T2, T3], horizon=1, lag=1)
        history = [h(T0, 10.0), h(T1, 20.0), h(T2, 30.0), h(T3, 40.0)]
        truth = [h(T3, 40.0), h(T4, 50.0)]
        outcome = run_evaluation(make_input(history, truth, config), providers=[PersistenceProvider()])
        self.assertTrue(outcome.ok, outcome.errors)
        values = [origin.forecasts[0].values for origin in outcome.report.origins]
        self.assertEqual([(30.0,), (40.0,)], values)

    def test_build_config_and_partition_return_values(self):
        config_result = build_config(cfg([T2], horizon=1, lag=1))
        self.assertTrue(config_result.ok, config_result.errors)
        self.assertEqual(1, config_result.value.horizon)
        partition_result = build_partition(part([h(T0, 1.0)]))
        self.assertTrue(partition_result.ok, partition_result.errors)
        self.assertIsInstance(partition_result.value.observations, tuple)


class ReviewCorrections(unittest.TestCase):
    """Regression tests for the evidenced M0 review corrections."""

    def test_unrepresentable_history_value_is_structured(self):
        config = cfg([T2], horizon=1, lag=1)
        data = make_input([h(T0, 10**400)], [h(T3, 1.0)], config)
        built = build_input(data)
        self.assertFalse(built.ok)
        self.assertIn(NON_FINITE_NUMBER, {error.code for error in built.errors})

        outcome = run_evaluation(data, providers=[PersistenceProvider()])
        self.assertFalse(outcome.ok)
        self.assertIn(NON_FINITE_NUMBER, outcome_codes(outcome))

    def test_metric_overflow_is_structured(self):
        config = cfg([T2], horizon=1, lag=1)
        data = make_input([h(T0, 1e308)], [h(T3, -1e308)], config)
        outcome = run_evaluation(data, providers=[PersistenceProvider()])
        self.assertFalse(outcome.ok)
        self.assertIn(OVERFLOW, outcome_codes(outcome))

    def test_huge_provider_value_is_explicit_exclusion(self):
        outcome = run_evaluation(standard_input(), providers=[_HugeValue()])
        self.assertTrue(outcome.ok, outcome.errors)
        forecast = outcome.report.origins[0].forecasts[0]
        self.assertFalse(forecast.ok)
        self.assertEqual(NON_FINITE_PREDICTION, forecast.exclusion_code)

    def test_sub_microsecond_step_is_rejected(self):
        config = cfg([T2], horizon=1, lag=1, step=1e-10)
        codes = build_codes(make_input([h(T0, 1.0)], [h(T3, 1.0)], config))
        self.assertIn(INVALID_VALUE, codes)

    def test_huge_origin_spans_are_rejected(self):
        huge_step = 86400 * 365 * 9000
        config = cfg([T2], horizon=1, lag=2, step=huge_step)
        codes = build_codes(make_input([h(T0, 1.0)], [h(T3, 1.0)], config))
        self.assertIn(INVALID_VALUE, codes)

    def test_huge_horizon_and_lag_are_rejected(self):
        cases = [
            cfg([T2], horizon=10**100, lag=1),
            cfg([T2], horizon=1, lag=10**100),
        ]
        for config in cases:
            with self.subTest(config=config):
                codes = build_codes(make_input([h(T0, 1.0)], [h(T3, 1.0)], config))
                self.assertIn(INVALID_VALUE, codes)

    def test_datetime_boundaries_are_rejected(self):
        upper = cfg(["9999-12-31T23:00:00+00:00"], horizon=2, lag=1, step=3600)
        lower = cfg(["0001-01-01T00:30:00+00:00"], horizon=1, lag=2, step=3600)
        for config in (upper, lower):
            with self.subTest(config=config):
                codes = build_codes(make_input([h(T0, 1.0)], [h(T0, 1.0)], config))
                self.assertIn(INVALID_VALUE, codes)

    def test_lone_surrogate_strings_are_rejected(self):
        surrogate = "\ud800"
        config = cfg([T2], horizon=1, lag=1)

        revision = build_codes(make_input([h(T0, 1.0, revision=surrogate)], [h(T3, 1.0)], config))
        self.assertIn(INVALID_VALUE, revision)

        reason = build_codes(make_input([unknown(T1, 2.0, surrogate)], [h(T3, 1.0)], config))
        self.assertIn(INVALID_VALUE, reason)

        data = standard_input()
        data["config"]["entity_id"] = surrogate
        self.assertIn(INVALID_VALUE, build_codes(data))

    def test_lone_surrogate_provider_metadata_is_rejected(self):
        outcome = run_evaluation(standard_input(), providers=[_BadMetadata()])
        self.assertFalse(outcome.ok)
        self.assertIn(INVALID_PROVIDER, outcome_codes(outcome))

    def test_valid_input_still_serializes_after_corrections(self):
        report = run_evaluation(standard_input()).report
        parsed = json.loads(report.to_json())
        self.assertEqual(report.input_digest, parsed["input_digest"])

    def test_empty_provider_collection_is_rejected(self):
        outcome = run_evaluation(standard_input(), providers=[])
        self.assertFalse(outcome.ok)
        self.assertIn(INVALID_VALUE, outcome_codes(outcome))
        self.assertIsNone(outcome.report)

    def test_invalid_provenance_is_explicit_exclusion(self):
        for provider in (_AlienProvenance(), _DuplicateProvenance()):
            with self.subTest(provider=provider.name):
                outcome = run_evaluation(standard_input(), providers=[provider])
                self.assertTrue(outcome.ok, outcome.errors)
                forecast = outcome.report.origins[0].forecasts[0]
                self.assertFalse(forecast.ok)
                self.assertEqual(MALFORMED_PREDICTION, forecast.exclusion_code)
                self.assertEqual((), forecast.used)

    def test_direct_input_is_revalidated(self):
        built = build_input(standard_input())
        self.assertTrue(built.ok, built.errors)
        valid = built.value
        self.assertTrue(run_evaluation(valid).ok)

        real = dataclasses.replace(valid, synthetic=False)
        outcome = run_evaluation(real)
        self.assertFalse(outcome.ok)
        self.assertIn(REAL_INPUT_UNSUPPORTED, outcome_codes(outcome))

        mismatched_truth = dataclasses.replace(valid.truth, unit="MWh")
        outcome = run_evaluation(dataclasses.replace(valid, truth=mismatched_truth))
        self.assertFalse(outcome.ok)
        self.assertIn(MIXED_UNITS, outcome_codes(outcome))

    def test_direct_input_malformed_nested_records_are_structured(self):
        valid = build_input(standard_input()).value

        bad_time = dataclasses.replace(valid.history.observations[0], timestamp="not-a-timestamp")
        bad_history = dataclasses.replace(valid.history, observations=(bad_time,))
        outcome = run_evaluation(dataclasses.replace(valid, history=bad_history))
        self.assertFalse(outcome.ok)
        self.assertIn(INVALID_TIMESTAMP, outcome_codes(outcome))

        bad_value = dataclasses.replace(valid.history.observations[0], value=object())
        bad_history = dataclasses.replace(valid.history, observations=(bad_value,))
        outcome = run_evaluation(dataclasses.replace(valid, history=bad_history))
        self.assertFalse(outcome.ok)
        self.assertIn(INVALID_TYPE, outcome_codes(outcome))

    def test_direct_input_zero_effective_step_is_rejected(self):
        valid = build_input(standard_input()).value
        zero_step = dataclasses.replace(valid.config, step=timedelta(0))
        outcome = run_evaluation(dataclasses.replace(valid, config=zero_step))
        self.assertFalse(outcome.ok)
        self.assertIn(INVALID_VALUE, outcome_codes(outcome))

    def test_accepted_direct_input_is_rebuilt_immutable(self):
        valid = build_input(standard_input()).value
        outcome = run_evaluation(valid)
        self.assertTrue(outcome.ok, outcome.errors)
        report = outcome.report
        self.assertIsInstance(report.origins, tuple)
        self.assertIsInstance(report.origins[0].forecasts, tuple)
        self.assertIsInstance(report.origins[0].context, tuple)


class ReviewFixRegressions(unittest.TestCase):
    """Regression tests for the four M0 review findings fixed in this pass."""

    # --- finding 1: an unknown model name must not fall back to the defaults.

    def test_unknown_model_name_raises_instead_of_returning_none(self):
        for name in ("typo", "Persistence", "", None):
            with self.subTest(name=repr(name)):
                with self.assertRaises(ProviderLookupError) as caught:
                    builtin_providers_by_name([name])
                self.assertEqual(name, caught.exception.name)
                self.assertEqual(INVALID_PROVIDER, caught.exception.error.code)

    def test_unknown_model_name_does_not_yield_a_default_report(self):
        for name in ("typo", "Persistence", "", None):
            with self.subTest(name=repr(name)):
                with self.assertRaises(ProviderLookupError):
                    # The lookup fails before the value can reach the
                    # ``providers`` slot, so no default report can be produced.
                    run_evaluation(standard_input(), builtin_providers_by_name([name]))

    def test_unknown_name_in_position_is_not_scored_as_a_default_run(self):
        outcome = run_evaluation(standard_input(), providers=[PersistenceProvider()])
        self.assertTrue(outcome.ok, outcome.errors)
        self.assertEqual(["persistence"], [model.name for model in outcome.report.models])
        self.assertEqual([], error_paths(outcome.errors, INVALID_PROVIDER))

    def test_every_fixture_model_name_is_actually_scored(self):
        for name in ("synthetic_two_origin.json", "synthetic_multi_season.json"):
            with self.subTest(fixture=name):
                data = load_fixture(name)
                outcome = run_evaluation(
                    fixture_source(data), builtin_providers_by_name(data["models"])
                )
                self.assertTrue(outcome.ok, outcome.errors)
                self.assertEqual(
                    data["models"], [model.name for model in outcome.report.models]
                )

    def test_explicit_none_providers_is_rejected(self):
        outcome = run_evaluation(standard_input(), providers=None)
        self.assertFalse(outcome.ok)
        self.assertIsNone(outcome.report)
        self.assertIn(INVALID_PROVIDER, outcome_codes(outcome))

    def test_omitted_providers_still_select_the_default_pair(self):
        outcome = run_evaluation(standard_input())
        self.assertTrue(outcome.ok, outcome.errors)
        self.assertEqual(
            ["persistence", "seasonal_naive"],
            [model.name for model in outcome.report.models],
        )

    # --- finding 2: a malformed output excludes one origin, it does not abort.

    def _mixed_comparison(self, bad_provider):
        """Origins T2 and T3, each with full history and complete truth."""
        config = cfg([T2, T3], horizon=2, lag=1)
        history = [h(T0, 10.0), h(T1, 20.0), h(T2, 30.0), h(T3, 40.0)]
        truth = [h(T3, 40.0), h(T4, 50.0), h(T5, 60.0), h(T6, 70.0)]
        source = make_input(history, truth, config)
        return source, run_evaluation(source, providers=[bad_provider, _Healthy()])

    def test_scalar_and_none_values_exclude_that_origin_only(self):
        # Two origins, full history and truth for both.  The provider returns a
        # malformed value at the second origin only; the first is valid.  Both
        # non-iterable shapes (a bare float and None) are exercised.
        for malformed_value in (3.0, None):
            with self.subTest(malformed_value=repr(malformed_value)):
                bad = _TogglingBad(
                    malformed_origin=datetime.fromisoformat(T3),
                    malformed_value=malformed_value,
                )
                _, outcome = self._mixed_comparison(bad)
                self.assertTrue(outcome.ok, outcome.errors)
                report = outcome.report
                self.assertEqual(2, report.total_origin_count)

                model_names = [model.name for model in report.models]
                self.assertEqual([bad.name, "healthy"], model_names)
                by_model = {summary.model: summary for summary in report.summaries}

                # The malformed origin is the only excluded one; the other origin
                # still ran and was still scored.
                bad_summary = by_model[bad.name]
                self.assertEqual(2, bad_summary.called_origins)
                self.assertEqual(1, bad_summary.successful_origins)
                self.assertEqual(1, bad_summary.scored_origins)
                self.assertEqual(2, bad_summary.scored_pairs)
                self.assertEqual(
                    [(MALFORMED_PREDICTION, 1)],
                    [(item.code, item.count) for item in bad_summary.exclusions],
                )

                # Both origins remain in the report: the failure excluded one
                # origin, it did not abort the comparison, and the run produced a
                # report.
                first, second = report.origins
                self.assertTrue(first.in_common)
                self.assertFalse(second.in_common)
                self.assertEqual(1, report.common_origin_count)

                first_forecasts = {forecast.model: forecast for forecast in first.forecasts}
                self.assertTrue(first_forecasts[bad.name].ok)
                self.assertEqual((1.0, 1.0), first_forecasts[bad.name].values)
                self.assertEqual((1.0, 1.0), first_forecasts["healthy"].values)

                second_forecasts = {forecast.model: forecast for forecast in second.forecasts}
                self.assertFalse(second_forecasts[bad.name].ok)
                self.assertEqual(
                    MALFORMED_PREDICTION, second_forecasts[bad.name].exclusion_code
                )
                self.assertEqual((), second_forecasts[bad.name].used)
                self.assertIsNone(second_forecasts[bad.name].values)
                self.assertTrue(second_forecasts["healthy"].ok)

                # The shared denominator stays shared: the healthy model is scored
                # on the one common origin, not on its own two successful origins.
                healthy = by_model["healthy"]
                self.assertEqual(2, healthy.successful_origins)
                self.assertEqual(1, healthy.scored_origins)
                self.assertEqual(2, healthy.scored_pairs)
                # Origin T2: predictions (1.0, 1.0) vs truth (40.0, 50.0): MAE 44.0.
                self.assertEqual(44.0, healthy.mae)
                self.assertEqual(44.0, bad_summary.mae)  # same shared pairs

    def test_scalar_prediction_alone_still_reports_null_metrics(self):
        config = cfg([T2], horizon=1, lag=1)
        for bad in (_ScalarValue(), _NoneValue()):
            with self.subTest(provider=bad.name):
                outcome = run_evaluation(
                    make_input([h(T0, 10.0)], [h(T3, 40.0)], config),
                    providers=[bad],
                )
                self.assertTrue(outcome.ok, outcome.errors)
                summary = outcome.report.summaries[0]
                self.assertEqual(MALFORMED_PREDICTION, summary.exclusions[0].code)
                self.assertIsNone(summary.mae)
                self.assertIsNone(summary.rmse)

    # --- finding 3: the fixture expectation block is asserted, not decorative.

    def test_fixture_expected_blocks_match_computed_metrics(self):
        for name in ("synthetic_two_origin.json", "synthetic_multi_season.json"):
            with self.subTest(fixture=name):
                data = load_fixture(name)
                expected = data["expected"]
                outcome = run_evaluation(
                    fixture_source(data), builtin_providers_by_name(data["models"])
                )
                self.assertTrue(outcome.ok, outcome.errors)
                report = outcome.report
                self.assertEqual(expected["common_origins"], report.common_origin_count)
                by_model = {summary.model: summary for summary in report.summaries}
                for model, block in expected.items():
                    if model == "common_origins":
                        continue
                    with self.subTest(fixture=name, model=model):
                        summary = by_model[model]
                        self.assertEqual(block["mae"], summary.mae)
                        self.assertEqual(block["rmse"], summary.rmse)
                        if "per_lead" in block:
                            self.assertEqual(
                                [
                                    (item["lead"], item["mae"], item["rmse"])
                                    for item in block["per_lead"]
                                ],
                                [
                                    (metric.lead, metric.mae, metric.rmse)
                                    for metric in summary.per_lead
                                ],
                            )
                        if "values" in block:
                            for origin in report.origins:
                                if not origin.in_common:
                                    continue
                                forecast = next(
                                    item for item in origin.forecasts if item.model == model
                                )
                                self.assertEqual(tuple(block["values"]), forecast.values)

    def test_multi_season_persistence_metrics_are_hand_calculated(self):
        data = load_fixture("synthetic_multi_season.json")
        outcome = run_evaluation(fixture_source(data), builtin_providers_by_name(data["models"]))
        self.assertTrue(outcome.ok, outcome.errors)
        persistence = {s.model: s for s in outcome.report.summaries}["persistence"]
        # values (5,5,5,5,5) against truth (5,6,7,8,9): MAE 10/5, RMSE sqrt(30/5).
        self.assertEqual(2.0, persistence.mae)
        self.assertEqual(math.sqrt(6.0), persistence.rmse)
        self.assertEqual(2.0, data["expected"]["persistence"]["mae"])
        self.assertEqual(math.sqrt(6.0), data["expected"]["persistence"]["rmse"])

    # --- finding 4: mismatch diagnostics point at the field that mismatched.

    def test_identity_mismatch_paths_name_the_offending_field(self):
        config = cfg([T2], horizon=1, lag=1)
        good_history = part([h(T0, 1.0)], entity="SYN-A", unit="MW")
        good_truth = part([h(T3, 1.0)], entity="SYN-A", unit="MW")

        unit_mismatch = part([h(T3, 1.0)], entity="SYN-A", unit="MWh")
        result = build_input(
            {"synthetic": True, "config": config, "history": good_history, "truth": unit_mismatch}
        )
        self.assertEqual(["$.truth.unit"], error_paths(result.errors, MIXED_UNITS))
        self.assertEqual([], error_paths(result.errors, MIXED_ENTITIES))

        entity_mismatch = part([h(T3, 1.0)], entity="SYN-B", unit="MW")
        result = build_input(
            {"synthetic": True, "config": config, "history": good_history, "truth": entity_mismatch}
        )
        self.assertEqual(["$.truth.entity_id"], error_paths(result.errors, MIXED_ENTITIES))
        self.assertEqual([], error_paths(result.errors, MIXED_UNITS))

        type_mismatch = {"entity_type": "grid", "entity_id": "SYN-A", "unit": "MW",
                         "observations": [h(T0, 1.0)]}
        result = build_input(
            {"synthetic": True, "config": config, "history": type_mismatch, "truth": good_truth}
        )
        self.assertEqual(["$.history.entity_type"], error_paths(result.errors, MIXED_ENTITIES))

        # Both mismatches at once are reported separately, at their own paths.
        both = part([h(T3, 1.0)], entity="SYN-B", unit="MWh")
        result = build_input(
            {"synthetic": True, "config": config, "history": good_history, "truth": both}
        )
        self.assertEqual(["$.truth.entity_id"], error_paths(result.errors, MIXED_ENTITIES))
        self.assertEqual(["$.truth.unit"], error_paths(result.errors, MIXED_UNITS))

    def test_direct_input_unit_mismatch_reports_the_unit_path(self):
        valid = build_input(standard_input()).value
        mismatched_truth = dataclasses.replace(valid.truth, unit="MWh")
        outcome = run_evaluation(dataclasses.replace(valid, truth=mismatched_truth))
        self.assertFalse(outcome.ok)
        self.assertEqual(["$.truth.unit"], error_paths(outcome.errors, MIXED_UNITS))


if __name__ == "__main__":
    unittest.main()
