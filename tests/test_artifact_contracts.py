"""Behavioral tests for the offline v1 artifact contracts.

Positive cases load the labeled synthetic fixtures in ``tests/fixtures/contracts``.
Those fixtures are valid interchange artifacts: each carries its correct
canonical ``content_digest`` and validates as written.  Negative cases mutate a
fresh deep copy and check stable error codes, safe messages and controlled field
paths; when a mutation changes content, the copy is re-stamped with
:func:`with_content_digest`.
"""
import copy
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts import (
    ALL_CODES,
    DATASET_SNAPSHOT,
    PREDICTION_ARTIFACT,
    PROVISION_CANDIDATE,
    SAFE_CANONICALIZATION_MESSAGE,
    CanonicalizationError,
    canonical_dumps,
    compute_content_digest,
    evaluate_eligibility,
    validate_artifact,
    validate_json,
    with_content_digest,
)
from src.contracts.errors import MESSAGES, issue

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contracts"

_SAFE_PATH = re.compile(r"^\$[A-Za-z0-9_.\[\]]*$")


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def read_fixture_text(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def codes(result):
    return set(result.codes())


def paths(result, code):
    return {error.path for error in result.errors if error.code == code}


DATASET = "dataset_snapshot.json"
PREDICTION = "prediction_artifact.json"
PROVISION = "provision_candidate.json"


class PositiveFixtures(unittest.TestCase):
    def test_each_fixture_validates_and_is_strictly_eligible(self):
        for name, artifact_type in (
            (DATASET, DATASET_SNAPSHOT),
            (PREDICTION, PREDICTION_ARTIFACT),
            (PROVISION, PROVISION_CANDIDATE),
        ):
            with self.subTest(fixture=name):
                artifact = load_fixture(name)
                self.assertEqual(artifact_type, artifact["artifact_type"])
                self.assertIs(True, artifact["synthetic"])
                self.assertIn("synthetic", artifact["artifact_id"])
                self.assertIn("content_digest", artifact)
                result = validate_artifact(artifact)
                self.assertTrue(result.ok, result.errors)
                eligibility = evaluate_eligibility(artifact)
                self.assertTrue(eligibility.structural_ok)
                self.assertTrue(eligibility.eligible, eligibility.errors)

    def test_each_fixture_text_validates_directly_as_interchange(self):
        # The stored digest must match, so raw fixture text passes without any
        # test-time stamping.
        for name in (DATASET, PREDICTION, PROVISION):
            with self.subTest(fixture=name):
                result = validate_json(read_fixture_text(name))
                self.assertTrue(result.ok, result.errors)

    def test_creation_time_may_follow_the_cutoff(self):
        artifact = with_content_digest(load_fixture(DATASET))
        self.assertGreater(artifact["created_at"], artifact["information_cutoff"])
        self.assertTrue(validate_artifact(artifact).ok)
        self.assertTrue(evaluate_eligibility(artifact).eligible)


class CanonicalDigest(unittest.TestCase):
    def test_digest_is_key_order_independent(self):
        raw = load_fixture(DATASET)
        reordered = dict(reversed(list(raw.items())))
        reordered["payload"] = dict(reversed(list(raw["payload"].items())))
        reordered["source_refs"] = [
            dict(reversed(list(ref.items()))) for ref in raw["source_refs"]
        ]
        self.assertNotEqual(list(raw.keys()), list(reordered.keys()))
        self.assertEqual(compute_content_digest(raw), compute_content_digest(reordered))

    def test_changed_content_changes_digest(self):
        raw = load_fixture(DATASET)
        changed = copy.deepcopy(raw)
        changed["payload"]["missingness"]["missing_count"] = 13
        self.assertNotEqual(compute_content_digest(raw), compute_content_digest(changed))

    def test_only_top_level_content_digest_is_excluded(self):
        raw = load_fixture(DATASET)
        baseline = compute_content_digest(raw)

        with_toplevel = copy.deepcopy(raw)
        with_toplevel["content_digest"] = "f" * 64
        self.assertEqual(baseline, compute_content_digest(with_toplevel))

        nested_changed = copy.deepcopy(raw)
        nested_changed["source_refs"][0]["content_digest"] = "1" * 64
        self.assertNotEqual(baseline, compute_content_digest(nested_changed))

    def test_tampered_digest_is_rejected(self):
        artifact = with_content_digest(load_fixture(PREDICTION))
        artifact["payload"]["outcome"]["value"] = 9999.0
        result = validate_artifact(artifact)
        self.assertIn("DIGEST_MISMATCH", codes(result))
        self.assertEqual({"$.content_digest"}, paths(result, "DIGEST_MISMATCH"))

    def test_missing_digest_is_rejected(self):
        artifact = load_fixture(PREDICTION)
        del artifact["content_digest"]
        result = validate_artifact(artifact)
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertEqual({"$.content_digest"}, paths(result, "MISSING_FIELD"))


class EnvelopeRejections(unittest.TestCase):
    def test_unsupported_schema_version(self):
        raw = load_fixture(DATASET)
        raw["schema_version"] = 2
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("UNSUPPORTED_SCHEMA_VERSION", codes(result))

    def test_boolean_schema_version_is_not_a_number(self):
        raw = load_fixture(DATASET)
        raw["schema_version"] = True
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("BOOLEAN_AS_NUMBER", codes(result))

    def test_unsupported_artifact_type(self):
        raw = load_fixture(DATASET)
        raw["artifact_type"] = "model_spec"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("UNSUPPORTED_ARTIFACT_TYPE", codes(result))

    def test_naive_timestamp_is_rejected(self):
        raw = load_fixture(DATASET)
        raw["created_at"] = "2026-10-03T12:00:00"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("NAIVE_TIMESTAMP", codes(result))

    def test_malformed_timestamp_is_rejected(self):
        raw = load_fixture(DATASET)
        raw["created_at"] = "yesterday"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVALID_TIMESTAMP", codes(result))

    def test_non_object_artifact_is_rejected_without_crashing(self):
        for value in (None, 1, "artifact", True, [], [1, 2], {}, {"a": 1}):
            with self.subTest(value=repr(value)):
                result = validate_artifact(value)
                self.assertFalse(result.ok)

    def test_python_object_with_non_string_keys_is_rejected_without_crashing(self):
        result = validate_artifact({1: "x"})
        self.assertFalse(result.ok)

    def test_unknown_fields_do_not_leak_into_paths_or_messages(self):
        raw = load_fixture(DATASET)
        raw["payload"]["SECRET_KEY"] = "private"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVALID_VALUE", codes(result))
        for error in result.errors:
            self.assertNotIn("SECRET", error.path)
            self.assertNotIn("SECRET", error.message)
            self.assertNotIn("private", error.message)


class DatasetPayload(unittest.TestCase):
    def test_missing_units_is_rejected(self):
        raw = load_fixture(DATASET)
        del raw["payload"]["quantity_schema"]["units"]
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertIn("$.payload.quantity_schema.units", paths(result, "MISSING_FIELD"))

    def test_missing_feature_units_is_rejected(self):
        raw = load_fixture(DATASET)
        del raw["payload"]["target_features"][1]["units"]
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertIn("$.payload.target_features[1].units", paths(result, "MISSING_FIELD"))

    def test_inverted_window_is_rejected(self):
        raw = load_fixture(DATASET)
        raw["payload"]["window"]["end"] = "2026-08-01T00:00:00+08:00"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVERTED_INTERVAL", codes(result))
        self.assertIn("$.payload.window", paths(result, "INVERTED_INTERVAL"))

    def test_missing_count_above_total_is_rejected(self):
        raw = load_fixture(DATASET)
        raw["payload"]["missingness"]["missing_count"] = 9000
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.missingness", paths(result, "INVALID_VALUE"))


class PredictionPayload(unittest.TestCase):
    def test_input_cutoff_after_forecast_origin_is_rejected(self):
        raw = load_fixture(PREDICTION)
        raw["payload"]["input_cutoff"] = "2026-10-02T07:00:00+08:00"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("TEMPORAL_ORDER", codes(result))
        self.assertIn("$.payload.input_cutoff", paths(result, "TEMPORAL_ORDER"))

    def test_input_cutoff_after_information_cutoff_is_rejected(self):
        raw = load_fixture(PREDICTION)
        raw["information_cutoff"] = "2026-10-02T05:00:00+08:00"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("TEMPORAL_ORDER", codes(result))

    def test_latest_revision_pointer_is_rejected(self):
        raw = load_fixture(PREDICTION)
        raw["payload"]["model_spec_ref"]["revision_id"] = "latest"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("LATEST_POINTER_FORBIDDEN", codes(result))
        self.assertIn(
            "$.payload.model_spec_ref.revision_id",
            paths(result, "LATEST_POINTER_FORBIDDEN"),
        )

    def test_boolean_is_not_accepted_as_a_number(self):
        raw = load_fixture(PREDICTION)
        raw["payload"]["quantiles"][0]["value"] = True
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("BOOLEAN_AS_NUMBER", codes(result))
        self.assertIn("$.payload.quantiles[0].value", paths(result, "BOOLEAN_AS_NUMBER"))

    def test_class_scores_are_supported_without_label_paths(self):
        raw = load_fixture(PREDICTION)
        raw["payload"]["outcome"] = {
            "kind": "class_scores",
            "scores": {"up": 0.6, "down": 0.2, "flat": 0.2},
        }
        artifact = with_content_digest(raw)
        self.assertTrue(validate_artifact(artifact).ok)

    def test_non_finite_class_score_is_rejected_at_container_path(self):
        raw = load_fixture(PREDICTION)
        hostile_label = "<script>alert(1)</script>"
        raw["payload"]["outcome"] = {
            "kind": "class_scores",
            "scores": {hostile_label: float("nan"), "down": 0.5},
        }
        raw["content_digest"] = "0" * 64
        result = validate_artifact(raw, require_digest=False)
        self.assertIn("NON_FINITE_NUMBER", codes(result))
        self.assertEqual({"$.payload.outcome.scores"}, paths(result, "NON_FINITE_NUMBER"))
        for error in result.errors:
            self.assertNotIn(hostile_label, error.path)
            self.assertNotIn(hostile_label, error.message)


class ProvisionPayload(unittest.TestCase):
    def test_passage_must_bind_to_envelope_source_ref(self):
        raw = load_fixture(PROVISION)
        raw["payload"]["passages"][0]["source_ref_id"] = "src-does-not-exist"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("UNRESOLVED_CITATION", codes(result))
        self.assertIn(
            "$.payload.passages[0].source_ref_id",
            paths(result, "UNRESOLVED_CITATION"),
        )

    def test_passage_requires_exact_locator(self):
        raw = load_fixture(PROVISION)
        raw["payload"]["passages"][0]["locator"] = {"kind": "query", "query": "everything"}
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.passages[0].locator.kind", paths(result, "INVALID_VALUE"))

    def test_unknown_actor_requires_explicit_reason(self):
        raw = load_fixture(PROVISION)
        raw["payload"]["actor"] = {"kind": "market_operator", "name": None, "unknown_reason": None}
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertIn("$.payload.actor.unknown_reason", paths(result, "MISSING_FIELD"))

    def test_date_precision_is_preserved(self):
        artifact = with_content_digest(load_fixture(PROVISION))
        self.assertTrue(validate_artifact(artifact).ok)
        self.assertEqual("2026-09-28", artifact["payload"]["publication_date"])
        self.assertIsInstance(artifact["payload"]["publication_date"], str)

    def test_date_with_time_is_rejected(self):
        raw = load_fixture(PROVISION)
        raw["payload"]["publication_date"] = "2026-09-28T00:00:00+08:00"
        result = validate_artifact(with_content_digest(raw))
        self.assertIn("INVALID_DATE", codes(result))


class StrictEligibility(unittest.TestCase):
    def test_unknown_availability_is_structurally_valid_but_ineligible(self):
        raw = load_fixture(DATASET)
        raw["source_refs"][0]["availability"] = {
            "known_at": None,
            "unknown_reason": "feed not confirmed for the historical window",
        }
        artifact = with_content_digest(raw)
        self.assertTrue(validate_artifact(artifact).ok)
        result = evaluate_eligibility(artifact)
        self.assertTrue(result.structural_ok)
        self.assertFalse(result.eligible)
        self.assertIn("UNKNOWN_AVAILABILITY", result.codes())

    def test_late_availability_is_ineligible(self):
        raw = load_fixture(DATASET)
        raw["source_refs"][0]["availability"]["known_at"] = "2026-10-05T00:00:00+08:00"
        artifact = with_content_digest(raw)
        self.assertTrue(validate_artifact(artifact).ok)
        result = evaluate_eligibility(artifact)
        self.assertFalse(result.eligible)
        self.assertIn("LATE_AVAILABILITY", result.codes())

    def test_late_availability_against_prediction_input_cutoff(self):
        raw = load_fixture(PREDICTION)
        # Availability is before information_cutoff but after input_cutoff.
        raw["source_refs"][0]["availability"]["known_at"] = "2026-10-02T05:45:00+08:00"
        artifact = with_content_digest(raw)
        self.assertTrue(validate_artifact(artifact).ok)
        result = evaluate_eligibility(artifact)
        self.assertFalse(result.eligible)
        self.assertIn("LATE_AVAILABILITY", result.codes())

    def test_structural_failure_is_not_eligible(self):
        result = evaluate_eligibility({"artifact_type": DATASET_SNAPSHOT})
        self.assertFalse(result.structural_ok)
        self.assertFalse(result.eligible)
        self.assertTrue(result.errors)


class StrictJsonParsing(unittest.TestCase):
    def test_malformed_json_text(self):
        result = validate_json(read_fixture_text("malformed.json"))
        self.assertEqual({"MALFORMED_JSON"}, codes(result))

    def test_non_finite_text(self):
        result = validate_json(read_fixture_text("non_finite.json"))
        self.assertEqual({"NON_FINITE_NUMBER"}, codes(result))

    def test_duplicate_keys(self):
        result = validate_json(read_fixture_text("duplicate_key.json"))
        self.assertEqual({"DUPLICATE_KEY"}, codes(result))

    def test_non_object_json_root(self):
        self.assertEqual({"INVALID_TYPE"}, codes(validate_json("[]")))
        self.assertEqual({"INVALID_TYPE"}, codes(validate_json("null")))
        self.assertEqual({"INVALID_TYPE"}, codes(validate_json("3")))

    def test_non_text_json_input_is_rejected(self):
        for value in (None, 3, b"{}", ["{}"]):
            with self.subTest(value=repr(value)):
                self.assertEqual({"MALFORMED_JSON"}, codes(validate_json(value)))

    def test_valid_json_text_round_trips_to_positive_artifact(self):
        artifact = with_content_digest(load_fixture(DATASET))
        result = validate_json(json.dumps(artifact))
        self.assertTrue(result.ok, result.errors)


class CanonicalizationFailures(unittest.TestCase):
    def test_lone_surrogate_is_reported_not_raised(self):
        artifact = load_fixture(PREDICTION)
        artifact["artifact_id"] = "pred-\ud800-bad"
        # The fixture digest is well-formed but the content cannot be encoded.
        result = validate_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertIn("INTERNAL_ERROR", codes(result))
        self.assertEqual({"$"}, paths(result, "INTERNAL_ERROR"))
        for error in result.errors:
            self.assertNotIn("\ud800", error.path)
            self.assertNotIn("\ud800", error.message)

    def test_lone_surrogate_via_json_text_is_reported(self):
        artifact = load_fixture(PREDICTION)
        artifact["artifact_id"] = "pred-\ud800-bad"
        text = json.dumps(artifact)  # ensure_ascii=True keeps the text ASCII
        result = validate_json(text)
        self.assertFalse(result.ok)
        self.assertIn("INTERNAL_ERROR", codes(result))

    def test_canonicalization_errors_use_the_fixed_safe_message(self):
        for value in ({"artifact_id": "\ud800"}, {"value": object()}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(CanonicalizationError) as cm:
                    compute_content_digest(value)
                self.assertEqual(SAFE_CANONICALIZATION_MESSAGE, str(cm.exception))

    def test_excessive_nesting_is_wrapped_not_raised(self):
        # Whether a deeply nested value hits the encoder's recursion limit is
        # interpreter-specific: CPython 3.14.7 serialized 5000 nested lists while
        # older encoders raise RecursionError.  Both outcomes are safe, so the
        # portable contract is "return canonical text or wrap a real
        # RecursionError", never propagate one.
        deep = []
        node = deep
        for _ in range(5000):
            child = []
            node.append(child)
            node = child
        try:
            text = canonical_dumps(deep)
        except CanonicalizationError as exc:
            self.assertEqual(SAFE_CANONICALIZATION_MESSAGE, str(exc))
        else:
            # Canonical form is deterministic: the outer list plus the 5000
            # appended children is 5001 lists, hence 5001 bracket pairs.
            self.assertEqual("[" * 5001 + "]" * 5001, text)

        # A real deep value must never escape as an uncaught exception, and the
        # extra envelope key is rejected structurally whether or not the value
        # happened to serialize on this interpreter.
        artifact = load_fixture(DATASET)
        artifact["deep_value"] = deep
        result = validate_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$", paths(result, "INVALID_VALUE"))

    def test_encoder_recursion_error_is_wrapped_and_reported(self):
        # Patch the encoder itself so the RecursionError conversion is exercised
        # deterministically on every interpreter, independent of the depth at
        # which CPython happens to give up.
        artifact = load_fixture(DATASET)
        artifact["deep_value"] = [1]
        with mock.patch(
            "src.contracts.jsonutil.json.dumps", side_effect=RecursionError
        ):
            with self.assertRaises(CanonicalizationError) as cm:
                canonical_dumps({"any": "value"})
            self.assertEqual(SAFE_CANONICALIZATION_MESSAGE, str(cm.exception))

            result = validate_artifact(artifact)
        self.assertFalse(result.ok)
        self.assertIn("INTERNAL_ERROR", codes(result))
        self.assertEqual({"$"}, paths(result, "INTERNAL_ERROR"))


class EffectivityShape(unittest.TestCase):
    def _provision(self, mutate):
        raw = load_fixture(PROVISION)
        mutate(raw["payload"]["effectivity"])
        return with_content_digest(raw)

    def test_equal_interval_endpoints_are_rejected(self):
        def mutate(effectivity):
            effectivity.clear()
            effectivity.update(
                {"kind": "interval", "start": "2026-10-01", "end": "2026-10-01"}
            )

        result = validate_artifact(self._provision(mutate))
        self.assertIn("INVERTED_INTERVAL", codes(result))
        self.assertIn("$.payload.effectivity", paths(result, "INVERTED_INTERVAL"))

    def test_open_ended_interval_is_allowed(self):
        def mutate(effectivity):
            effectivity.clear()
            effectivity.update({"kind": "interval", "start": "2026-10-01"})

        result = validate_artifact(self._provision(mutate))
        self.assertTrue(result.ok, result.errors)

    def test_single_date_form_rejects_range_fields(self):
        def mutate(effectivity):
            effectivity["start"] = "2026-09-01"

        result = validate_artifact(self._provision(mutate))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.effectivity.start", paths(result, "INVALID_VALUE"))

    def test_interval_form_rejects_single_date(self):
        def mutate(effectivity):
            effectivity.clear()
            effectivity.update(
                {
                    "kind": "interval",
                    "start": "2026-10-01",
                    "end": "2026-11-01",
                    "date": "2026-10-01",
                }
            )

        result = validate_artifact(self._provision(mutate))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.effectivity.date", paths(result, "INVALID_VALUE"))

    def test_unknown_form_rejects_invented_date(self):
        def mutate(effectivity):
            effectivity.clear()
            effectivity.update(
                {"kind": "unknown", "unknown_reason": "not stated", "date": "2026-10-01"}
            )

        result = validate_artifact(self._provision(mutate))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.effectivity.date", paths(result, "INVALID_VALUE"))

    def test_effectivity_kind_shapes_do_not_crash(self):
        for kind in (None, [], {}, True, 1, 1.5, "bogus"):
            def mutate(effectivity, kind=kind):
                effectivity.clear()
                effectivity.update({"kind": kind, "unknown_reason": "not stated"})

            with self.subTest(kind=repr(kind)):
                result = validate_artifact(self._provision(mutate))
                self.assertFalse(result.ok)
                self.assertIn("INVALID_VALUE", codes(result))
                self.assertIn("$.payload.effectivity.kind", paths(result, "INVALID_VALUE"))

    def test_other_discriminator_shapes_do_not_crash(self):
        for kind in (None, [], {}, True, 7, "bogus"):
            raw = load_fixture(PREDICTION)
            raw["payload"]["outcome"] = {"kind": kind}
            with self.subTest(discriminant="outcome", kind=repr(kind)):
                result = validate_artifact(with_content_digest(raw))
                self.assertFalse(result.ok)

            raw = load_fixture(PREDICTION)
            raw["source_refs"][0]["locator"] = {"kind": kind}
            with self.subTest(discriminant="locator", kind=repr(kind)):
                result = validate_artifact(with_content_digest(raw))
                self.assertFalse(result.ok)


class PredictionEvaluationStatus(unittest.TestCase):
    def _prediction(self, mutate):
        raw = load_fixture(PREDICTION)
        mutate(raw["payload"])
        return with_content_digest(raw)

    def test_experimental_unknown_is_valid(self):
        def mutate(payload):
            payload["status"] = "experimental"
            payload["evaluation_report_ref"] = None
            payload["evaluation_report_unknown_reason"] = "not yet evaluated"

        result = validate_artifact(self._prediction(mutate))
        self.assertTrue(result.ok, result.errors)

    def test_experimental_unknown_requires_reason(self):
        def mutate(payload):
            payload["status"] = "experimental"
            payload["evaluation_report_ref"] = None

        result = validate_artifact(self._prediction(mutate))
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertIn(
            "$.payload.evaluation_report_unknown_reason",
            paths(result, "MISSING_FIELD"),
        )

    def test_evaluated_requires_real_reference(self):
        def mutate(payload):
            payload["evaluation_report_ref"] = None
            payload["evaluation_report_unknown_reason"] = "not yet evaluated"

        result = validate_artifact(self._prediction(mutate))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn("$.payload.evaluation_report_ref", paths(result, "INVALID_VALUE"))

    def test_real_reference_rejects_unknown_reason(self):
        def mutate(payload):
            payload["evaluation_report_unknown_reason"] = "contradiction"

        result = validate_artifact(self._prediction(mutate))
        self.assertIn("INVALID_VALUE", codes(result))
        self.assertIn(
            "$.payload.evaluation_report_unknown_reason",
            paths(result, "INVALID_VALUE"),
        )

    def test_approved_requires_promotion_decision(self):
        def mutate(payload):
            payload["status"] = "approved-for-declared-use"

        result = validate_artifact(self._prediction(mutate))
        self.assertIn("MISSING_FIELD", codes(result))
        self.assertIn("$.payload.promotion_decision_ref", paths(result, "MISSING_FIELD"))

    def test_approved_with_promotion_decision_is_valid(self):
        def mutate(payload):
            payload["status"] = "approved-for-declared-use"
            payload["promotion_decision_ref"] = {
                "artifact_id": "promotion-synthetic-001",
                "revision_id": "promo-rev-001",
                "content_digest": "1" * 64,
            }

        result = validate_artifact(self._prediction(mutate))
        self.assertTrue(result.ok, result.errors)

    def test_promotion_decision_must_be_immutable(self):
        def mutate(payload):
            payload["status"] = "approved-for-declared-use"
            payload["promotion_decision_ref"] = {
                "artifact_id": "promotion-synthetic-001",
                "revision_id": "latest",
                "content_digest": "1" * 64,
            }

        result = validate_artifact(self._prediction(mutate))
        self.assertIn("LATEST_POINTER_FORBIDDEN", codes(result))
        self.assertIn(
            "$.payload.promotion_decision_ref.revision_id",
            paths(result, "LATEST_POINTER_FORBIDDEN"),
        )

    def test_non_approved_status_may_not_carry_promotion_decision(self):
        for status in ("experimental", "evaluated"):
            def mutate(payload, status=status):
                payload["status"] = status
                payload["promotion_decision_ref"] = {
                    "artifact_id": "promotion-synthetic-001",
                    "revision_id": "promo-rev-001",
                    "content_digest": "1" * 64,
                }
                if status == "experimental":
                    payload["evaluation_report_ref"] = None
                    payload["evaluation_report_unknown_reason"] = "not yet evaluated"

            with self.subTest(status=status):
                result = validate_artifact(self._prediction(mutate))
                self.assertIn("INVALID_VALUE", codes(result))
                self.assertIn(
                    "$.payload.promotion_decision_ref",
                    paths(result, "INVALID_VALUE"),
                )


class ErrorHygiene(unittest.TestCase):
    def test_every_code_has_a_fixed_nonempty_message(self):
        self.assertTrue(ALL_CODES)
        for code in ALL_CODES:
            with self.subTest(code=code):
                error = issue(code)
                self.assertEqual(code, error.code)
                self.assertEqual(MESSAGES[code], error.message)
                self.assertTrue(error.message.strip())

    def test_inverted_interval_message_is_explicit(self):
        self.assertEqual("start must be before end", MESSAGES["INVERTED_INTERVAL"])

    def test_reported_paths_are_controlled_tokens(self):
        raw = load_fixture(PREDICTION)
        raw["payload"]["outcome"] = {"kind": "bogus"}
        result = validate_artifact(with_content_digest(raw))
        self.assertFalse(result.ok)
        for error in result.errors:
            self.assertRegex(error.path, _SAFE_PATH)


if __name__ == "__main__":
    unittest.main()
