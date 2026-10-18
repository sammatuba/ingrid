"""ARCH-1: the outlook archive records, offline and stdlib-only.

Every case runs in a scratch directory; no network, clock, model or cloud call
is made and no fixture outside this file is read. The two acceptance items carry
named tests: an outlook cannot be edited after issue (:class:`IssueOnce`,
:class:`TamperEvidence`) and a scoring receipt names the final series version it
was scored against (:class:`ReceiptContract`, :class:`Receipts`); the
stdlib-only item is :class:`StdlibOnly`.
"""
import copy
import json
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import compute_content_digest
from src.outlook.records import (
    KINDS,
    MESSAGES,
    OutlookArchive,
    OutlookError,
    build_outlook,
    build_receipt,
    outlook_reference,
    receipt_stem,
    validate_outlook,
    validate_receipt,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def scratch_directory(prefix="arch1-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path.

    A review sandbox may mount no writable system temporary directory while the
    workspace itself stays writable; the fallback keeps the archive tests
    runnable there. It sits under the ignored ``.local/`` and is removed by
    :class:`tempfile.TemporaryDirectory` cleanup exactly like the primary path.
    """
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def outlook_fields(**overrides):
    """The named fields of one well-formed outlook, with overrides applied."""
    fields = dict(
        outlook_id="outlook-2026-10-16-01",
        issued_at="2026-10-16T09:00:00Z",
        information_cutoff="2026-10-16T08:00:00Z",
        horizon={"label": "day", "start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z"},
        target_series_ref={"table": "grid_raw.ext_pmr_settlement_prices", "column": "lmp",
                           "version": "final-bmonth-2026-09"},
        inputs=[{"name": "region-lwap-final-bmonth-2026-08", "digest": DIGEST_A}],
        assumption_ids=["UC-01-001", "UC-03-004"],
        model_version="baseline-last-week-same-interval.v1",
        values_ref={"path_hint": ".local/price/outlook-01.csv", "sha256": DIGEST_B, "rows": 288},
        issuer="orchestrator-seat",
        synthetic=True,
    )
    fields.update(overrides)
    return fields


def an_outlook(**overrides):
    return build_outlook(**outlook_fields(**overrides))


def receipt_fields(**overrides):
    """The keyword fields of one well-formed receipt, minus the outlook link."""
    fields = dict(
        scored_at="2026-10-19T00:30:00Z",
        final_series_version="final-bmonth-2026-09",
        final_series_digest=DIGEST_A,
        window={"start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z"},
        metrics=[{"horizon": "day", "slice": "market", "intervals": 288,
                  "bias": "-3.5", "mae": "120.25", "rmse": "201.5",
                  "pinball_p10": "60.5", "pinball_p50": "80", "pinball_p90": "70.25"}],
        coverage={"scored": 288, "skipped": [{"count": 12, "reason": "administered pricing"}]},
        synthetic=True,
    )
    fields.update(overrides)
    return fields


def a_receipt(outlook=None, **overrides):
    return build_receipt(outlook if outlook is not None else an_outlook(), **receipt_fields(**overrides))


def raw_receipt(**overrides):
    """A sealed receipt built without an outlook, to test the shape rules alone."""
    record = {"schema_version": "outlook.v1", "kind": "ScoringReceipt",
              "outlook_id": "outlook-2026-10-16-01", "outlook_digest": DIGEST_A}
    record.update(receipt_fields(**overrides))
    record["content_digest"] = compute_content_digest(record)
    return record


def refused(case, build):
    """The code of the OutlookError a build raises; fails if it raises nothing else."""
    with case.assertRaises(OutlookError) as caught:
        build()
    return caught.exception.code


class Sealing(unittest.TestCase):
    def test_valid_outlook_seals_a_digest_over_every_field(self):
        outlook = an_outlook()
        self.assertEqual(outlook["content_digest"], compute_content_digest(outlook))
        self.assertEqual(set(outlook) - {"content_digest", "schema_version", "kind"}, set(outlook_fields()))
        for field, value in (("outlook_id", "outlook-2026-10-16-99"),
                             ("model_version", "a-different-model.v2"),
                             ("values_ref", {"path_hint": ".local/price/other.csv", "sha256": DIGEST_B,
                                             "rows": 288})):
            self.assertNotEqual(an_outlook(**{field: value})["content_digest"], outlook["content_digest"])

    def test_digest_ignores_key_order_and_the_digest_key_itself(self):
        outlook = an_outlook()
        shuffled = {key: outlook[key] for key in reversed(list(outlook))}
        self.assertEqual(compute_content_digest(shuffled), outlook["content_digest"])
        self.assertEqual(compute_content_digest(dict(outlook, content_digest="0" * 64)),
                         outlook["content_digest"])

    def test_timestamps_are_written_in_utc_so_equal_instants_share_a_digest(self):
        manila = an_outlook(issued_at="2026-10-16T17:00:00+08:00",
                            information_cutoff="2026-10-16T16:00:00+08:00",
                            horizon={"label": "day", "start": "2026-10-17T08:00:00+08:00",
                                     "end": "2026-10-18T08:00:00+08:00"})
        self.assertEqual(manila["issued_at"], "2026-10-16T09:00:00Z")
        self.assertEqual(manila["horizon"]["start"], "2026-10-17T00:00:00Z")
        self.assertEqual(manila["content_digest"], an_outlook()["content_digest"])
        self.assertEqual(an_outlook(issued_at="2026-10-16T09:00:00.000000Z")["issued_at"],
                         "2026-10-16T09:00:00Z")

    def test_builder_does_not_mutate_the_callers_structures(self):
        horizon = {"label": "day", "start": "2026-10-17T08:00:00+08:00", "end": "2026-10-18T08:00:00+08:00"}
        inputs = [{"name": "one", "digest": DIGEST_A}]
        mind = dict(receipt_fields()["window"])
        an_outlook(horizon=horizon, inputs=inputs)
        a_receipt(window=mind, scored_at="2026-10-19T00:30:00+08:00")
        self.assertEqual(horizon["start"], "2026-10-17T08:00:00+08:00")
        self.assertEqual(inputs, [{"name": "one", "digest": DIGEST_A}])
        self.assertEqual(mind["start"], "2026-10-17T00:00:00Z")

    def test_reference_names_the_issued_bytes(self):
        outlook = an_outlook()
        self.assertEqual(outlook_reference(outlook),
                         {"outlook_id": outlook["outlook_id"], "outlook_digest": outlook["content_digest"]})

    def test_the_archive_holds_two_record_kinds(self):
        self.assertEqual(KINDS, ("OutlookRecord", "ScoringReceipt"))
        self.assertEqual({an_outlook()["kind"], a_receipt()["kind"]}, set(KINDS))

    def test_every_error_code_has_fixed_text(self):
        for code in ("OUTLOOK_INVALID", "RECEIPT_INVALID", "OUTLOOK_IMMUTABLE", "OUTLOOK_UNKNOWN",
                     "OUTLOOK_DIGEST_MISMATCH", "RECEIPT_DUPLICATE", "ARCHIVE_TAMPERED", "ARCHIVE_IO"):
            self.assertTrue(MESSAGES[code])
            self.assertNotIn(code, MESSAGES[code])
        self.assertEqual(str(OutlookError("OUTLOOK_IMMUTABLE")), MESSAGES["OUTLOOK_IMMUTABLE"])


class OutlookContract(unittest.TestCase):
    def test_blank_identifier_is_refused(self):
        for value in ("", "   ", 7, None):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(outlook_id=value))),
                             "OUTLOOK_INVALID")

    def test_identifier_cannot_escape_the_archive_directory(self):
        for value in ("../etc/passwd", "a/b", ".hidden", "x" * 129):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(outlook_id=value))),
                             "OUTLOOK_INVALID")

    def test_cutoff_after_issue_is_refused(self):
        self.assertEqual(
            refused(self, lambda: build_outlook(**outlook_fields(information_cutoff="2026-10-16T10:00:00Z"))),
            "OUTLOOK_INVALID")
        an_outlook(information_cutoff="2026-10-16T09:00:00Z")  # the boundary is accepted

    def test_horizon_must_start_at_or_after_issue_and_before_it_ends(self):
        early = {"label": "day", "start": "2026-10-16T08:59:59Z", "end": "2026-10-18T00:00:00Z"}
        self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(horizon=early))),
                         "OUTLOOK_INVALID")
        empty = {"label": "day", "start": "2026-10-18T00:00:00Z", "end": "2026-10-18T00:00:00Z"}
        self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(horizon=empty))),
                         "OUTLOOK_INVALID")
        an_outlook(horizon={"label": "day", "start": "2026-10-16T09:00:00Z",
                            "end": "2026-10-18T00:00:00Z"})  # equal to the issue is accepted

    def test_horizon_label_is_one_of_the_contract_labels(self):
        for label in ("day", "week", "month"):
            an_outlook(horizon={"label": label, "start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z"})
        bad = {"label": "year", "start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z"}
        self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(horizon=bad))),
                         "OUTLOOK_INVALID")

    def test_malformed_timestamp_is_refused(self):
        for field in ("issued_at", "information_cutoff"):
            for value in ("2026-10-16 09:00:00Z", "2026-10-16T09:00:00", "2026-13-40T09:00:00Z", 7):
                self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(**{field: value}))),
                                 "OUTLOOK_INVALID")

    def test_target_series_ref_is_closed_and_required(self):
        for value in ({"table": "t", "column": "lmp"},
                      {"table": "t", "column": "lmp", "version": "v", "extra": "x"},
                      {"table": "", "column": "lmp", "version": "v"}, "table"):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(target_series_ref=value))),
                             "OUTLOOK_INVALID")

    def test_inputs_are_named_once_with_a_digest_each(self):
        for value in ([], "x", [{"name": "a"}], [{"name": "", "digest": DIGEST_A}],
                      [{"name": "a", "digest": "A" * 64}], [{"name": "a", "digest": DIGEST_A, "extra": 1}],
                      [{"name": "a", "digest": DIGEST_A}, {"name": "a", "digest": DIGEST_B}]):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(inputs=value))),
                             "OUTLOOK_INVALID")

    def test_assumption_ids_are_present_and_unique(self):
        for value in ([], ["ok", "ok"], ["../up"], [None]):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(assumption_ids=value))),
                             "OUTLOOK_INVALID")

    def test_an_assumption_id_takes_the_register_id_form(self):
        # ARCH-2's register ids are `<family>:<slug>`; the one separator the
        # register uses is allowed in this field only, because an assumption id
        # never names a file in the archive directory.
        ids = ["threshold:price_cap_php_mwh", "rules:billing_month_clock"]
        self.assertEqual(an_outlook(assumption_ids=ids)["assumption_ids"], ids)
        for value in ([":x"], ["rules:a/b"], ["rules:a b"], ["rules:a\\b"]):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(assumption_ids=value))),
                             "OUTLOOK_INVALID")

    def test_values_ref_carries_the_hint_digest_and_row_count(self):
        for value in ({"path_hint": ".local/x", "sha256": DIGEST_B},
                      {"path_hint": "", "sha256": DIGEST_B, "rows": 1},
                      {"path_hint": ".local/x", "sha256": DIGEST_B, "rows": -1},
                      {"path_hint": ".local/x", "sha256": DIGEST_B, "rows": True},
                      {"path_hint": ".local/x", "sha256": DIGEST_B, "rows": 1, "extra": 0}):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(values_ref=value))),
                             "OUTLOOK_INVALID")

    def test_text_fields_must_be_non_blank_strings(self):
        for field in ("model_version", "issuer"):
            for value in ("", "  ", 4, None):
                self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(**{field: value}))),
                                 "OUTLOOK_INVALID")

    def test_synthetic_must_be_declared_as_a_boolean(self):
        for value in (1, 0, "true", None):
            self.assertEqual(refused(self, lambda: build_outlook(**outlook_fields(synthetic=value))),
                             "OUTLOOK_INVALID")

    def test_validator_refuses_unknown_keys_and_unknown_schema(self):
        outlook = an_outlook()
        with self.assertRaises(OutlookError):
            validate_outlook(dict(outlook, extra="x"))
        with self.assertRaises(OutlookError):
            validate_outlook(dict(outlook, schema_version="outlook.v2"))
        with self.assertRaises(OutlookError):
            validate_outlook(dict(outlook, kind="Outlook"))
        missing = {key: outlook[key] for key in outlook if key != "issuer"}
        with self.assertRaises(OutlookError):
            validate_outlook(missing)

    def test_tampered_digest_is_refused_on_validation(self):
        outlook = an_outlook()
        outlook["issuer"] = "somebody-else"
        self.assertEqual(refused(self, lambda: validate_outlook(outlook)), "OUTLOOK_INVALID")

    def test_validator_does_not_rewrite_stored_content(self):
        outlook = an_outlook()
        stored = copy.deepcopy(outlook)
        validate_outlook(outlook)
        self.assertEqual(outlook, stored)


class ReceiptContract(unittest.TestCase):
    def test_receipt_names_the_final_series_version_it_was_scored_against(self):
        receipt = a_receipt()
        self.assertEqual(receipt["final_series_version"], "final-bmonth-2026-09")
        self.assertEqual(receipt["final_series_digest"], DIGEST_A)

    def test_missing_or_blank_final_series_version_is_refused(self):
        for value in ("", "  ", None, 9):
            self.assertEqual(refused(self, lambda: a_receipt(final_series_version=value)), "RECEIPT_INVALID")
        receipt = a_receipt()
        del receipt["final_series_version"]
        self.assertEqual(refused(self, lambda: validate_receipt(receipt)), "RECEIPT_INVALID")

    def test_final_series_version_must_be_named_wherever_the_record_is_read(self):
        receipt = a_receipt()
        receipt["final_series_version"] = " "
        self.assertEqual(refused(self, lambda: validate_receipt(receipt)), "RECEIPT_INVALID")

    def test_series_and_outlook_digests_are_well_formed(self):
        self.assertEqual(refused(self, lambda: a_receipt(final_series_digest="z" * 64)), "RECEIPT_INVALID")
        self.assertEqual(refused(self, lambda: a_receipt(final_series_digest=DIGEST_A.upper())),
                         "RECEIPT_INVALID")
        receipt = a_receipt()
        receipt["outlook_digest"] = "z" * 64
        self.assertEqual(refused(self, lambda: validate_receipt(receipt)), "RECEIPT_INVALID")

    def test_a_receipt_that_cites_other_bytes_than_its_outlook_is_refused(self):
        outlook = an_outlook()
        receipt = raw_receipt(outlook_digest=DIGEST_B)
        self.assertTrue(validate_receipt(receipt))  # the shape alone names some well-formed digest
        with tempfile.TemporaryDirectory() as tmp:
            archive = OutlookArchive(Path(tmp) / "archive")
            archive.issue(outlook)
            self.assertEqual(refused(self, lambda: archive.append_receipt(receipt)),
                             "OUTLOOK_DIGEST_MISMATCH")

    def test_receipt_is_written_after_its_window_settles(self):
        self.assertEqual(refused(self, lambda: a_receipt(scored_at="2026-10-17T23:59:59Z")),
                         "RECEIPT_INVALID")
        settled = a_receipt(scored_at="2026-10-18T00:00:00Z")  # the window end is the boundary
        self.assertEqual(settled["scored_at"], "2026-10-18T00:00:00Z")

    def test_window_is_an_interval(self):
        for value in ({"start": "2026-10-18T00:00:00Z", "end": "2026-10-17T00:00:00Z"}, {"start": "x"},
                      {"start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z", "mid": 0}):
            self.assertEqual(refused(self, lambda: a_receipt(window=value)), "RECEIPT_INVALID")

    def test_window_must_lie_inside_the_horizon_the_outlook_predicted(self):
        # The default outlook predicts the half-open day 2026-10-17T00:00Z to
        # 2026-10-18T00:00Z; every window below reaches outside it, so each
        # contains intervals the outlook never predicted.
        outside = (
            {"start": "2026-10-16T00:00:00Z", "end": "2026-10-16T12:00:00Z"},  # wholly before
            {"start": "2027-01-01T00:00:00Z", "end": "2027-01-02T00:00:00Z"},  # wholly after
            {"start": "2026-10-16T23:00:00Z", "end": "2026-10-17T01:00:00Z"},  # opens before the horizon
            {"start": "2026-10-17T23:00:00Z", "end": "2026-10-18T00:00:01Z"},  # runs past its end
        )
        for window in outside:
            fields = dict(window=window, scored_at="2027-01-03T00:00:00Z")
            self.assertTrue(validate_receipt(raw_receipt(**fields)))  # the record alone is well formed
            self.assertEqual(refused(self, lambda: build_receipt(an_outlook(), **receipt_fields(**fields))),
                             "RECEIPT_INVALID")

    def test_the_horizon_edges_and_the_whole_horizon_are_scorable(self):
        outlook = an_outlook()
        whole = {"start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:00Z"}
        front = {"start": "2026-10-17T00:00:00Z", "end": "2026-10-17T06:00:00Z"}
        back = {"start": "2026-10-17T18:00:00Z", "end": "2026-10-18T00:00:00Z"}
        for window in (whole, front, back):
            receipt = a_receipt(outlook, window=window)
            self.assertEqual(receipt["window"], window)
            self.assertEqual(receipt["outlook_digest"], outlook["content_digest"])

    def test_receipt_cites_the_outlook_it_was_built_from(self):
        outlook = an_outlook()
        receipt = a_receipt(outlook)
        self.assertEqual(receipt["outlook_id"], outlook["outlook_id"])
        self.assertEqual(receipt["outlook_digest"], outlook["content_digest"])

    def test_a_real_receipt_cannot_score_a_synthetic_outlook(self):
        self.assertEqual(refused(self, lambda: a_receipt(an_outlook(synthetic=True), synthetic=False)),
                         "RECEIPT_INVALID")

    def test_provenance_is_inherited_one_way(self):
        real, synthetic = an_outlook(synthetic=False), an_outlook(synthetic=True)
        # A real outlook may carry a real receipt or one that declares itself a
        # fixture; a synthetic outlook may carry only a synthetic receipt.
        self.assertFalse(a_receipt(real, synthetic=False)["synthetic"])
        self.assertTrue(a_receipt(real, synthetic=True)["synthetic"])
        self.assertTrue(a_receipt(synthetic, synthetic=True)["synthetic"])

    def test_a_scored_window_can_be_an_inner_slice_of_the_horizon(self):
        inner = dict(window={"start": "2026-10-17T12:00:00Z", "end": "2026-10-17T13:00:00Z"},
                     scored_at="2026-10-18T00:30:00Z")
        receipt = a_receipt(**inner)
        self.assertEqual(receipt["window"]["start"], "2026-10-17T12:00:00Z")
        self.assertEqual(receipt["metrics"][0]["intervals"], 288)

    def test_metric_rows_are_closed_per_horizon_and_slice(self):
        good = [{"horizon": h, "slice": s, "intervals": 1, "bias": "0", "mae": "0", "rmse": "0",
                 "pinball_p10": "0", "pinball_p50": "0", "pinball_p90": "0"}
                for h in ("day", "week", "month") for s in ("market", "ap")]
        self.assertEqual(len(a_receipt(metrics=good)["metrics"]), 6)
        for value in ([], [dict(good[0], horizon="year")], [dict(good[0], slice="all")],
                      [good[0], good[0]], [dict(good[0], extra="x")],
                      [dict(good[0], intervals=0)], [dict(good[0], intervals=True)]):
            self.assertEqual(refused(self, lambda: a_receipt(metrics=value)), "RECEIPT_INVALID")

    def test_metric_values_are_decimal_strings_with_defined_signs(self):
        row = {"horizon": "day", "slice": "market", "intervals": 1, "bias": "0", "mae": "0", "rmse": "0",
               "pinball_p10": "0", "pinball_p50": "0", "pinball_p90": "0"}
        self.assertEqual(a_receipt(metrics=[dict(row, bias="-12.5")])["metrics"][0]["bias"], "-12.5")
        for key, value in (("mae", "-0.1"), ("rmse", "-1"), ("pinball_p10", "-0.0001"),
                           ("bias", "1e3"), ("mae", 1.5), ("rmse", "NaN"), ("pinball_p90", "nan")):
            self.assertEqual(refused(self, lambda: a_receipt(metrics=[dict(row, **{key: value})])),
                             "RECEIPT_INVALID")

    def test_coverage_keeps_scored_and_skipped_with_reasons(self):
        self.assertEqual(a_receipt(coverage={"scored": 0, "skipped": []})["coverage"]["scored"], 0)
        for value in ({"scored": -1, "skipped": []}, {"scored": 1}, {"scored": 1, "skipped": [{}]},
                      {"scored": 1, "skipped": [{"count": 0, "reason": "gap"}]},
                      {"scored": 1, "skipped": [{"count": 1, "reason": " "}]},
                      {"scored": 1, "skipped": [{"count": 1, "reason": "gap", "extra": 0}]}):
            self.assertEqual(refused(self, lambda: a_receipt(coverage=value)), "RECEIPT_INVALID")

    def test_receipt_validator_refuses_unknown_keys(self):
        receipt = a_receipt()
        with self.assertRaises(OutlookError):
            validate_receipt(dict(receipt, confidence="0.9"))
        with self.assertRaises(OutlookError):
            validate_receipt(dict(receipt, scored_at="2026-10-19T00:30:00"))  # no offset


class IssueOnce(unittest.TestCase):
    def setUp(self):
        self._tmp = scratch_directory()
        self.addCleanup(self._tmp.cleanup)
        self.archive = OutlookArchive(Path(self._tmp.name) / "outlook-archive")

    def test_issue_writes_one_document_and_reads_it_back(self):
        outlook = self.archive.issue(an_outlook())
        path = self.archive.outlooks_dir / f"{outlook['outlook_id']}.json"
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), outlook)
        self.assertEqual(self.archive.outlook(outlook["outlook_id"]), outlook)
        self.assertEqual(self.archive.issue_ids(), (outlook["outlook_id"],))

    def test_second_issue_of_the_same_id_is_refused_and_changes_nothing(self):
        outlook = self.archive.issue(an_outlook())
        path = self.archive.outlooks_dir / f"{outlook['outlook_id']}.json"
        before = path.read_bytes()
        self.assertEqual(refused(self, lambda: self.archive.issue(outlook)), "OUTLOOK_IMMUTABLE")
        self.assertEqual(refused(self, lambda: self.archive.issue(
            an_outlook(model_version="a-different-model.v2"))), "OUTLOOK_IMMUTABLE")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.archive.outlook(outlook["outlook_id"]), outlook)

    def test_the_archive_offers_no_mutation_entry_point(self):
        names = {name for name in dir(self.archive) if not name.startswith("_")}
        for forbidden in ("update", "edit", "replace", "delete", "remove", "amend"):
            self.assertFalse(any(forbidden in name for name in names), forbidden)
        self.assertTrue({"issue", "outlook", "append_receipt", "verify"} <= names)

    def test_unknown_outlook_id_is_refused(self):
        self.assertEqual(refused(self, lambda: self.archive.outlook("no-such-outlook")), "OUTLOOK_UNKNOWN")
        self.assertEqual(refused(self, lambda: self.archive.outlook("../etc")), "OUTLOOK_UNKNOWN")

    def test_issue_validates_before_touching_the_directory(self):
        self.assertEqual(refused(self, lambda: self.archive.issue(an_outlook(outlook_id=""))),
                         "OUTLOOK_INVALID")
        self.assertFalse(self.archive.outlooks_dir.exists())

    def test_an_unusable_archive_root_is_an_io_refusal(self):
        blocked = Path(self._tmp.name) / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        self.assertEqual(refused(self, lambda: OutlookArchive(blocked).issue(an_outlook())),
                         "ARCHIVE_IO")

    def test_an_unreadable_stored_path_is_an_io_refusal(self):
        (self.archive.outlooks_dir / "some-id.json").mkdir(parents=True)
        self.assertEqual(refused(self, lambda: self.archive.outlook("some-id")), "ARCHIVE_IO")


class Receipts(unittest.TestCase):
    def setUp(self):
        self._tmp = scratch_directory()
        self.addCleanup(self._tmp.cleanup)
        self.archive = OutlookArchive(Path(self._tmp.name) / "outlook-archive")
        self.outlook = self.archive.issue(an_outlook())

    def test_receipt_is_appended_once_and_read_by_outlook(self):
        receipt = self.archive.append_receipt(a_receipt(self.outlook))
        path = self.archive.receipts_dir / f"{receipt_stem(receipt)}.json"
        self.assertTrue(path.is_file())
        self.assertEqual(self.archive.receipts(self.outlook["outlook_id"]), (receipt,))
        self.assertEqual(self.archive.receipts(), (receipt,))
        self.assertEqual(self.archive.verify(), {"outlooks": 1, "receipts": 1,
                                                 "attributions": 0, "problems": []})

    def test_the_same_final_series_version_is_scored_once(self):
        self.archive.append_receipt(a_receipt(self.outlook))
        again = a_receipt(self.outlook, metrics=[{"horizon": "week", "slice": "ap", "intervals": 1,
                                                  "bias": "1", "mae": "1", "rmse": "1",
                                                  "pinball_p10": "1", "pinball_p50": "1", "pinball_p90": "1"}])
        self.assertEqual(refused(self, lambda: self.archive.append_receipt(again)), "RECEIPT_DUPLICATE")
        self.assertEqual(len(self.archive.receipts()), 1)

    def test_a_later_settled_series_version_is_a_new_receipt(self):
        first = self.archive.append_receipt(a_receipt(self.outlook))
        second = self.archive.append_receipt(a_receipt(
            self.outlook, final_series_version="corrected-final-bmonth-2026-09",
            scored_at="2026-10-20T00:30:00Z"))
        self.assertEqual(len(self.archive.receipts(self.outlook["outlook_id"])), 2)
        self.assertNotEqual(first["content_digest"], second["content_digest"])

    def test_two_outlooks_may_be_scored_against_the_same_series_version(self):
        other = self.archive.issue(an_outlook(outlook_id="outlook-2026-10-16-02"))
        self.archive.append_receipt(a_receipt(self.outlook))
        second = self.archive.append_receipt(a_receipt(other, scored_at="2026-10-19T01:00:00Z"))
        self.assertEqual(len(self.archive.receipts()), 2)
        self.assertEqual(len(self.archive.receipts(other["outlook_id"])), 1)
        self.assertEqual(second["final_series_version"], "final-bmonth-2026-09")

    def test_a_real_receipt_cannot_be_appended_to_a_synthetic_outlook(self):
        # The receipt is well formed on its own and cites the stored bytes; the
        # archive refuses it on provenance alone, and stores nothing.
        forged = raw_receipt(outlook_id=self.outlook["outlook_id"],
                            outlook_digest=self.outlook["content_digest"], synthetic=False)
        self.assertTrue(validate_receipt(forged))
        self.assertEqual(refused(self, lambda: self.archive.append_receipt(forged)), "RECEIPT_INVALID")
        self.assertEqual(self.archive.receipts(), ())
        self.assertFalse(self.archive.receipts_dir.exists())

    def test_a_receipt_whose_window_left_the_horizon_is_refused_by_the_archive(self):
        forged = raw_receipt(outlook_id=self.outlook["outlook_id"],
                            outlook_digest=self.outlook["content_digest"],
                            window={"start": "2026-10-17T00:00:00Z", "end": "2026-10-18T00:00:01Z"},
                            scored_at="2026-10-18T00:30:00Z")
        self.assertTrue(validate_receipt(forged))
        self.assertEqual(refused(self, lambda: self.archive.append_receipt(forged)), "RECEIPT_INVALID")
        self.assertEqual(self.archive.receipts(), ())
        self.assertFalse(self.archive.receipts_dir.exists())

    def test_a_receipt_for_an_unissued_outlook_is_refused(self):
        other = an_outlook(outlook_id="outlook-2026-10-16-02")
        self.assertEqual(refused(self, lambda: self.archive.append_receipt(a_receipt(other))),
                         "OUTLOOK_UNKNOWN")
        self.assertFalse(self.archive.receipts_dir.exists())

    def test_receipt_link_rules_survive_a_round_trip_through_the_archive(self):
        receipt = self.archive.append_receipt(a_receipt(self.outlook))
        stored = self.archive.receipts(self.outlook["outlook_id"])[0]
        self.assertEqual(stored, receipt)
        self.assertEqual(compute_content_digest(stored), stored["content_digest"])


def metric_row(bias="0"):
    """One well-formed market metric row with a distinguishing ``bias``."""
    return {"horizon": "day", "slice": "market", "intervals": 288, "bias": bias, "mae": "1",
            "rmse": "1", "pinball_p10": "1", "pinball_p50": "1", "pinball_p90": "1"}


class ReceiptStorageKey(unittest.TestCase):
    """Rework round 2: a receipt's storage key is its (outlook_id, series version) pair."""

    def setUp(self):
        self._tmp = scratch_directory()
        self.addCleanup(self._tmp.cleanup)
        self.archive = OutlookArchive(Path(self._tmp.name) / "outlook-archive")
        self.outlook = self.archive.issue(an_outlook())

    def test_the_stem_names_the_pair_and_not_the_content(self):
        first = a_receipt(self.outlook, metrics=[metric_row(bias="1")])
        second = a_receipt(self.outlook, scored_at="2026-10-19T01:00:00Z", metrics=[metric_row(bias="2")])
        self.assertNotEqual(first["content_digest"], second["content_digest"])
        self.assertEqual(receipt_stem(first), receipt_stem(second))  # one pair, one file
        self.assertTrue(receipt_stem(first).startswith(self.outlook["outlook_id"] + "."))
        later = a_receipt(self.outlook, final_series_version="corrected-final-bmonth-2026-09")
        self.assertNotEqual(receipt_stem(first), receipt_stem(later))  # another version, another file

    def test_a_version_text_stays_one_safe_path_segment(self):
        # The version is arbitrary text; the name hashes it, so no text can
        # point the write outside the receipts directory.
        for version in ("../../final-bmonth-2026-09", "a/b", "final-µm-2026-09", ".."):
            receipt = self.archive.append_receipt(a_receipt(self.outlook, final_series_version=version))
            path = self.archive.receipts_dir / f"{receipt_stem(receipt)}.json"
            self.assertEqual(path.parent, self.archive.receipts_dir)
            self.assertTrue(path.is_file())
            self.assertNotIn("/", receipt_stem(receipt))
        self.assertEqual(len(self.archive.receipts()), 4)

    def test_a_second_receipt_for_a_pair_is_refused_whatever_its_bytes(self):
        self.archive.append_receipt(a_receipt(self.outlook, metrics=[metric_row(bias="1")]))
        again = a_receipt(self.outlook, scored_at="2026-10-19T01:00:00Z", final_series_digest=DIGEST_B,
                          coverage={"scored": 144, "skipped": [{"count": 144, "reason": "gaps"}]},
                          metrics=[metric_row(bias="2")])
        self.assertTrue(validate_receipt(again))  # well formed on its own, but a second write
        self.assertEqual(refused(self, lambda: self.archive.append_receipt(again)), "RECEIPT_DUPLICATE")
        self.assertEqual(len(self.archive.receipts()), 1)

    def test_concurrent_appends_for_one_pair_leave_exactly_one_receipt(self):
        # Every writer builds different bytes for one pair, so content-addressed
        # names would have let them all through; the pair's one path admits one.
        workers = 8
        start = threading.Barrier(workers)
        receipts = [a_receipt(self.outlook, metrics=[metric_row(bias=str(index))])
                    for index in range(workers)]
        outcomes, lock = [], threading.Lock()

        def attempt(index):
            try:
                start.wait(timeout=30)
                self.archive.append_receipt(receipts[index])
                outcome = "stored"
            except OutlookError as error:
                outcome = error.code
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=attempt, args=(index,)) for index in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), ["RECEIPT_DUPLICATE"] * (workers - 1) + ["stored"])
        self.assertEqual(len(self.archive.receipts(self.outlook["outlook_id"])), 1)
        self.assertEqual(self.archive.verify()["problems"], [])


class TamperEvidence(unittest.TestCase):
    def setUp(self):
        self._tmp = scratch_directory()
        self.addCleanup(self._tmp.cleanup)
        self.archive = OutlookArchive(Path(self._tmp.name) / "outlook-archive")
        self.outlook = self.archive.issue(an_outlook())
        self.receipt = self.archive.append_receipt(a_receipt(self.outlook))
        self.path = self.archive.outlooks_dir / f"{self.outlook['outlook_id']}.json"
        self.receipt_name = f"{receipt_stem(self.receipt)}.json"

    def rewrite(self, mutate):
        edited = json.loads(self.path.read_text(encoding="utf-8"))
        mutate(edited)
        self.path.write_text(json.dumps(edited, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    def test_an_edit_after_issue_is_reported_on_read_and_by_verify(self):
        self.rewrite(lambda record: record.update(model_version="a-different-model.v2"))
        self.assertEqual(refused(self, lambda: self.archive.outlook(self.outlook["outlook_id"])),
                         "ARCHIVE_TAMPERED")
        report = self.archive.verify()
        self.assertEqual(report["outlooks"], 0)
        self.assertEqual(report["receipts"], 1)
        self.assertEqual(sorted(report["problems"]),
                         sorted([f"{self.path.name}: ARCHIVE_TAMPERED",
                                 f"{self.receipt_name}: OUTLOOK_UNKNOWN"]))

    def test_an_edit_that_recomputes_the_digest_still_breaks_the_receipt(self):
        def mutate(record):
            record["model_version"] = "a-different-model.v2"
            record["content_digest"] = compute_content_digest(record)
        self.rewrite(mutate)
        self.assertTrue(self.archive.outlook(self.outlook["outlook_id"]))  # self-consistent bytes
        report = self.archive.verify()
        self.assertEqual(report["outlooks"], 1)
        self.assertEqual(report["problems"], [f"{self.receipt_name}: OUTLOOK_DIGEST_MISMATCH"])

    def test_a_receipt_edited_after_it_was_written_is_reported(self):
        path = self.archive.receipts_dir / self.receipt_name
        edited = json.loads(path.read_text(encoding="utf-8"))
        edited["coverage"]["scored"] = 1
        path.write_text(json.dumps(edited, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        report = self.archive.verify()
        self.assertEqual(report["problems"], [f"{path.name}: ARCHIVE_TAMPERED"])

    def test_verify_reports_a_stored_receipt_that_contradicts_its_outlook(self):
        # Sealed by hand and stored under its own pair's name, so only the link
        # rules can object: a real receipt on a synthetic outlook is reported on
        # read, for a series version of its own that no other receipt holds.
        forged = raw_receipt(outlook_id=self.outlook["outlook_id"],
                            outlook_digest=self.outlook["content_digest"],
                            final_series_version="corrected-final-bmonth-2026-09",
                            synthetic=False)
        self.assertTrue(validate_receipt(forged))
        path = self.archive.receipts_dir / f"{receipt_stem(forged)}.json"
        path.write_text(json.dumps(forged, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        report = self.archive.verify()
        self.assertEqual((report["outlooks"], report["receipts"]), (1, 2))
        self.assertEqual(report["problems"], [f"{path.name}: RECEIPT_INVALID"])

    def test_a_receipt_stored_under_another_name_is_reported(self):
        # The name is the storage key: a receipt copied to a name that is not
        # its (outlook_id, final_series_version) pair is tamper evidence.
        moved = self.archive.receipts_dir / "moved-receipt.json"
        moved.write_text((self.archive.receipts_dir / self.receipt_name).read_text(encoding="utf-8"),
                         encoding="utf-8")
        report = self.archive.verify()
        self.assertEqual((report["outlooks"], report["receipts"]), (1, 1))
        self.assertEqual(report["problems"], [f"{moved.name}: ARCHIVE_TAMPERED"])

    def test_a_renamed_or_unparseable_file_is_reported(self):
        (self.archive.outlooks_dir / "moved.json").write_text(self.path.read_text(encoding="utf-8"),
                                                              encoding="utf-8")
        (self.archive.receipts_dir / "broken.json").write_text("{not json", encoding="utf-8")
        self.path.unlink()
        report = self.archive.verify()
        self.assertEqual(sorted(report["problems"]),
                         sorted(["broken.json: ARCHIVE_TAMPERED", "moved.json: ARCHIVE_TAMPERED",
                                 f"{self.receipt_name}: OUTLOOK_UNKNOWN"]))
        self.assertEqual((report["outlooks"], report["receipts"]), (0, 1))  # the orphaned receipt reads

    def test_an_empty_archive_verifies_clean(self):
        empty = OutlookArchive(Path(self._tmp.name) / "empty")
        self.assertEqual(empty.verify(), {"outlooks": 0, "receipts": 0,
                                          "attributions": 0, "problems": []})
        self.assertEqual(empty.issue_ids(), ())
        self.assertEqual(empty.receipts(), ())


class StdlibOnly(unittest.TestCase):
    def imported_roots(self, path):
        """Top-level import names; a relative import is reported with its dots."""
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_archive_modules_import_only_the_standard_library(self):
        paths = (ROOT / "src/outlook/records.py", ROOT / "src/contracts/jsonutil.py")
        for path in paths:
            roots = self.imported_roots(path)
            self.assertTrue(roots, path)
            for root in roots:
                self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}
                                or root.startswith("."), f"{path.name} imports {root}")
        self.assertEqual(self.imported_roots(ROOT / "src/outlook/__init__.py"), set())

    def test_the_test_module_itself_stays_offline(self):
        for root in self.imported_roots(Path(__file__)):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)


if __name__ == "__main__":
    unittest.main()
