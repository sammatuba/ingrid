"""ARCH-4: attribution of a miss as a record of its own beside the scoring receipt, offline.

What is proven here. An ``Attribution`` names the exact receipt bytes it explains and the
receipt's outlook; its cause is one of the three the foundation page fixes, and the cause
carries its own reference — a belief the outlook rested on, a signal dated after the outlook's
information cutoff and effective before the scored window ended, or the outlook's own model
version. Every invariant is refused on a fixture through the real builder and the real archive:
the content-derived key (a renamed or copied file is ``ARCHIVE_TAMPERED``), a wrong receipt
digest, a closed cause, a belief the outlook did not rest on, a signal before the cutoff or
after the statement or effective after the window, a method that is not the model version, a
share outside [0, 1], a real attribution on a synthetic receipt, and a duplicate key. The
shares of one receipt are not refused at write time; the archive's ``verify()`` reports a sum
above one, which the desk shows beside the receipt.

The labelled synthetic demonstration — a synthetic outlook, a synthetic receipt and one
attribution per cause — lives in a scratch archive under a temporary root (with the workspace
fallback a review sandbox needs), never in the real runtime archive at ``.local/outlook-archive``.
The person-driven command ``scripts/outlook/attribute.py`` is exercised end to end: it refuses
to run without ``--attributed-by``, refuses an unknown receipt, builds through the real archive
module and prints the key and the digest; it never issues or scores an outlook and calls no
model.

Direction check ARCH-4: the real archive is expected to hold 0 attributions (it holds no
receipt), and the fixture demonstration holds 3, one per cause. The first non-zero real count
can come no earlier than the first scored month.

Offline and stdlib-only: no model, network, credential or clock. Nothing here issues an outlook
into the real archive, writes a receipt into it, or attaches an attribution to it.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import compute_content_digest
from src.outlook import dependency as dep
from src.outlook import register as reg
from src.outlook.records import (
    ATTRIBUTION_KIND,
    CAUSES,
    MESSAGES,
    OutlookArchive,
    OutlookError,
    attribution_key,
    build_attribution,
    build_outlook,
    build_receipt,
    validate_attribution,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
SCRIPT = ROOT / "scripts" / "outlook" / "attribute.py"
REAL_ARCHIVE = ROOT / ".local" / "outlook-archive"
INTERPRETER = Path("/usr/bin/python3") if Path("/usr/bin/python3").exists() else Path(sys.executable)


def scratch_directory(prefix="arch4-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path.

    A review sandbox may mount no writable system temporary directory while the workspace
    itself stays writable; the fallback keeps these tests runnable there. It sits under the
    ignored ``.local/`` and is cleaned up the same way as the primary path.
    """
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def outlook_fields(**overrides):
    """The named fields of one synthetic outlook, with overrides applied."""
    fields = dict(
        outlook_id="outlook-fixture-2026-11-system",
        issued_at="2026-10-16T00:00:00Z",
        information_cutoff="2026-08-25T16:00:00Z",
        horizon={"label": "month", "start": "2026-10-25T16:00:00Z",
                 "end": "2026-11-25T16:00:00Z"},
        target_series_ref={"table": "fixture_grid.synthetic_lwap", "column": "lwap",
                           "version": "fixture-bmonth-2026-11"},
        inputs=[{"name": "fixture_hourly.csv", "digest": DIGEST_A}],
        assumption_ids=["availability:syn-bay-unit-2", "threshold:fixture_cut"],
        model_version="fixture seasonal average",
        values_ref={"path_hint": "tests/fixtures/grid/outlook/values.json",
                    "sha256": DIGEST_B, "rows": 4},
        issuer="ARCH-4 fixture",
        synthetic=True,
    )
    fields.update(overrides)
    return fields


def an_outlook(**overrides):
    return build_outlook(**outlook_fields(**overrides))


def receipt_fields(**overrides):
    """The keyword fields of one synthetic receipt, minus the outlook link."""
    fields = dict(
        scored_at="2026-11-26T00:00:00Z",
        final_series_version="fixture-final-bmonth-2026-11",
        final_series_digest=DIGEST_A,
        window={"start": "2026-10-25T16:00:00Z", "end": "2026-11-25T16:00:00Z"},
        metrics=[{"horizon": "month", "slice": "market", "intervals": 744, "bias": "0",
                  "mae": "1", "rmse": "1", "pinball_p10": "1", "pinball_p50": "1",
                  "pinball_p90": "1"}],
        coverage={"scored": 744, "skipped": []},
        synthetic=True,
    )
    fields.update(overrides)
    return fields


def a_receipt(outlook, **overrides):
    return build_receipt(outlook, **receipt_fields(**overrides))


def attribution_fields(receipt, outlook, **overrides):
    """The keyword fields of one well-formed belief attribution, with overrides applied."""
    fields = dict(
        receipt=receipt, outlook=outlook, cause="belief",
        assumption_id="availability:syn-bay-unit-2",
        statement="The synthetic unit was assumed available for the whole month.",
        attributed_by="ARCH-4 fixture analyst",
        attributed_at="2026-11-27T00:00:00Z",
        synthetic=True,
    )
    fields.update(overrides)
    return fields


def a_belief(receipt, outlook, **overrides):
    return build_attribution(**attribution_fields(receipt, outlook, **overrides))


SIGNAL = {"source": "fixture late advisory", "available_at": "2026-10-30T00:00:00Z",
          "effective_at": "2026-11-01T00:00:00Z"}


def a_signal(receipt, outlook, **overrides):
    fields = dict(attribution_fields(receipt, outlook), cause="signal", assumption_id=None,
                  signal_ref=dict(SIGNAL),
                  statement="A later advisory carried the outage the outlook could not read.")
    fields.update(overrides)
    return build_attribution(**fields)


def a_method(receipt, outlook, **overrides):
    fields = dict(attribution_fields(receipt, outlook), cause="method", assumption_id=None,
                  method_ref=outlook["model_version"],
                  statement="The seasonal average was the wrong method for this month.")
    fields.update(overrides)
    return build_attribution(**fields)


def resealed(record, **changes):
    """One record with the named fields changed and its content digest rebuilt."""
    edited = dict(record)
    edited.update(changes)
    edited.pop("content_digest", None)
    edited["content_digest"] = compute_content_digest(edited)
    return edited


def refused(case, build):
    """The code of the OutlookError a build raises; fails if it raises nothing else."""
    with case.assertRaises(OutlookError) as caught:
        build()
    return caught.exception.code


class Fixture:
    """A scratch archive holding a synthetic outlook and its synthetic receipt."""

    def __init__(self, test):
        self.temp = scratch_directory()
        test.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "outlook-archive"
        self.archive = OutlookArchive(self.root)
        self.outlook = self.archive.issue(an_outlook())
        self.receipt = self.archive.append_receipt(a_receipt(self.outlook))

    def append(self, record):
        return self.archive.append_attribution(record)


class RecordContract(unittest.TestCase):
    """The Attribution record: a closed key set, a sealed digest, the three causes."""

    def setUp(self):
        self.fixture = Fixture(self)
        self.outlook, self.receipt = self.fixture.outlook, self.fixture.receipt

    def test_an_attribution_is_sealed_over_every_field_except_the_digest(self):
        attribution = a_belief(self.receipt, self.outlook)
        self.assertEqual(attribution["kind"], ATTRIBUTION_KIND)
        self.assertEqual(attribution["content_digest"], compute_content_digest(attribution))
        self.assertEqual(set(attribution) - {"content_digest"},
                         {"schema_version", "kind", "outlook_id", "outlook_digest",
                          "receipt_digest", "cause", "assumption_id", "signal_ref", "method_ref",
                          "share", "statement", "attributed_by", "attributed_at", "synthetic"})
        # The links are read from the receipt, never typed: the exact bytes and their outlook.
        self.assertEqual(attribution["outlook_id"], self.outlook["outlook_id"])
        self.assertEqual(attribution["outlook_digest"], self.outlook["content_digest"])
        self.assertEqual(attribution["receipt_digest"], self.receipt["content_digest"])

    def test_the_key_is_the_record_s_own_content(self):
        first = a_belief(self.receipt, self.outlook)
        same = a_belief(self.receipt, self.outlook)
        self.assertEqual(attribution_key(first), attribution_key(same))
        self.assertRegex(attribution_key(first), r"^[0-9a-f]{64}$")
        changed = a_belief(self.receipt, self.outlook,
                           statement="The synthetic unit was assumed available for one day.")
        self.assertNotEqual(attribution_key(first), attribution_key(changed))
        # The signal's key is the source and available_at; the belief's is the assumption id.
        signal = a_signal(self.receipt, self.outlook)
        self.assertNotEqual(attribution_key(first), attribution_key(signal))

    def test_the_three_causes_are_closed(self):
        self.assertEqual(CAUSES, ("belief", "signal", "method"))
        for cause in CAUSES:
            builder = {"belief": a_belief, "signal": a_signal, "method": a_method}[cause]
            self.assertEqual(builder(self.receipt, self.outlook)["cause"], cause)
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        cause="data")),
                         "ATTRIBUTION_INVALID")

    def test_a_cause_carries_its_own_reference_and_no_other(self):
        for builder, other in ((a_belief, {"signal_ref": dict(SIGNAL)}),
                               (a_belief, {"method_ref": self.outlook["model_version"]}),
                               (a_signal, {"assumption_id": "availability:syn-bay-unit-2"}),
                               (a_method, {"signal_ref": dict(SIGNAL)})):
            self.assertEqual(refused(self, lambda: builder(self.receipt, self.outlook, **other)),
                             "ATTRIBUTION_INVALID")

    def test_a_belief_must_be_among_the_outlook_s_assumptions(self):
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        assumption_id="rules:not_a_row")),
                         "ATTRIBUTION_INVALID")
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        assumption_id="")),
                         "ATTRIBUTION_INVALID")

    def test_a_signal_is_dated_after_the_cutoff_before_the_statement_and_before_the_window_end(self):
        late = dict(SIGNAL, available_at="2026-08-25T16:00:00Z")  # not after the cutoff
        self.assertEqual(refused(self, lambda: a_signal(self.receipt, self.outlook,
                                                        signal_ref=late)), "ATTRIBUTION_INVALID")
        after = dict(SIGNAL, available_at="2026-11-28T00:00:00Z")  # after attributed_at
        self.assertEqual(refused(self, lambda: a_signal(self.receipt, self.outlook,
                                                        signal_ref=after)), "ATTRIBUTION_INVALID")
        late_effect = dict(SIGNAL, effective_at="2026-11-25T16:00:00Z")  # at the window end
        self.assertEqual(refused(self, lambda: a_signal(self.receipt, self.outlook,
                                                        signal_ref=late_effect)),
                         "ATTRIBUTION_INVALID")
        in_window = dict(SIGNAL, effective_at="2026-11-24T00:00:00Z")  # before the window end
        self.assertEqual(a_signal(self.receipt, self.outlook, signal_ref=in_window)["signal_ref"],
                         in_window)

    def test_a_method_names_the_outlook_s_model_version(self):
        self.assertEqual(refused(self, lambda: a_method(self.receipt, self.outlook,
                                                        method_ref="another model")),
                         "ATTRIBUTION_INVALID")
        self.assertEqual(a_method(self.receipt, self.outlook)["method_ref"],
                         self.outlook["model_version"])

    def test_a_share_is_a_decimal_string_in_the_unit_interval(self):
        self.assertEqual(a_belief(self.receipt, self.outlook, share="0")["share"], "0")
        self.assertEqual(a_belief(self.receipt, self.outlook, share="1")["share"], "1")
        for value in ("-0.1", "1.01", "2", "1e-3", 0.5, "NaN", " 0.5"):
            self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                            share=value)),
                             "ATTRIBUTION_INVALID")

    def test_the_statement_and_the_author_are_non_blank_text(self):
        for field in ("statement", "attributed_by"):
            for value in ("", "  ", 7, None):
                self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                                **{field: value})),
                                 "ATTRIBUTION_INVALID")

    def test_the_attribution_is_written_after_the_receipt_was_scored(self):
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        attributed_at="2026-11-25T23:59:59Z")),
                         "ATTRIBUTION_INVALID")
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        attributed_at="2026-11-27T00:00:00")),
                         "ATTRIBUTION_INVALID")
        boundary = a_belief(self.receipt, self.outlook, attributed_at=self.receipt["scored_at"])
        self.assertEqual(boundary["attributed_at"], self.receipt["scored_at"])

    def test_provenance_is_inherited_one_way(self):
        real_outlook = an_outlook(outlook_id="outlook-fixture-real", synthetic=False)
        real = a_receipt(real_outlook, final_series_version="fixture-real", synthetic=False)
        synthetic = a_receipt(real_outlook, final_series_version="fixture-synthetic",
                              synthetic=True)
        # A real attribution cannot sit on a synthetic receipt.
        self.assertEqual(refused(self, lambda: a_belief(self.receipt, self.outlook,
                                                        synthetic=False)),
                         "ATTRIBUTION_INVALID")
        # A synthetic attribution is honest about itself and may sit on either receipt.
        self.assertTrue(a_belief(self.receipt, self.outlook, synthetic=True)["synthetic"])
        self.assertTrue(a_belief(synthetic, real_outlook, synthetic=True)["synthetic"])
        self.assertFalse(a_belief(real, real_outlook, synthetic=False)["synthetic"])

    def test_the_validator_refuses_unknown_keys_and_unknown_kinds(self):
        attribution = a_belief(self.receipt, self.outlook)
        for change in ({"extra": 1}, {"kind": "ScoringReceipt"},
                       {"schema_version": "outlook.v2"}, {"content_digest": "0" * 64}):
            self.assertEqual(refused(self, lambda: validate_attribution(
                dict(attribution, **change))), "ATTRIBUTION_INVALID")
        for value in ([], {}, None, 7, "Attribution"):
            self.assertEqual(refused(self, lambda: validate_attribution(value)),
                             "ATTRIBUTION_INVALID")

    def test_every_error_code_has_fixed_text(self):
        for code in ("ATTRIBUTION_INVALID", "ATTRIBUTION_DUPLICATE", "RECEIPT_UNKNOWN",
                     "SHARE_OVER_ONE"):
            self.assertTrue(MESSAGES[code])
            self.assertNotIn(code, MESSAGES[code])


class ArchiveWrites(unittest.TestCase):
    """The store: exclusive create of the content key, no scan and no sequence number."""

    def setUp(self):
        self.fixture = Fixture(self)
        self.outlook, self.receipt = self.fixture.outlook, self.fixture.receipt

    def test_an_attribution_is_appended_once_and_read_back(self):
        attribution = self.fixture.append(a_belief(self.receipt, self.outlook))
        path = self.fixture.archive.attributions_dir / (attribution_key(attribution) + ".json")
        self.assertTrue(path.is_file())
        self.assertEqual(path.stem, attribution_key(attribution))
        self.assertEqual(self.fixture.archive.attributions(), (attribution,))
        self.assertEqual(self.fixture.archive.attributions(self.outlook["outlook_id"]),
                         (attribution,))
        self.assertEqual(self.fixture.archive.attributions("another-outlook"), ())
        report = self.fixture.archive.verify()
        self.assertEqual((report["outlooks"], report["receipts"], report["attributions"]),
                         (1, 1, 1))
        self.assertEqual(report["problems"], [])

    def test_a_duplicate_key_is_refused_and_one_record_is_stored(self):
        attribution = self.fixture.append(a_belief(self.receipt, self.outlook))
        before = (self.fixture.archive.attributions_dir /
                  (attribution_key(attribution) + ".json")).read_bytes()
        self.assertEqual(refused(self, lambda: self.fixture.append(a_belief(self.receipt,
                                                                            self.outlook))),
                         "ATTRIBUTION_DUPLICATE")
        self.assertEqual(len(self.fixture.archive.attributions()), 1)
        self.assertEqual((self.fixture.archive.attributions_dir /
                          (attribution_key(attribution) + ".json")).read_bytes(), before)

    def test_two_statements_that_differ_in_one_word_are_two_records(self):
        first = self.fixture.append(a_belief(self.receipt, self.outlook))
        second = self.fixture.append(a_belief(
            self.receipt, self.outlook,
            statement="The synthetic unit was assumed available for most of the month."))
        self.assertNotEqual(first["content_digest"], second["content_digest"])
        self.assertEqual(len(self.fixture.archive.attributions()), 2)

    def test_a_wrong_receipt_digest_is_refused(self):
        attribution = a_belief(self.receipt, self.outlook)
        forged = resealed(attribution, receipt_digest="0" * 64)
        self.assertTrue(validate_attribution(forged))
        self.assertEqual(refused(self, lambda: self.fixture.append(forged)), "RECEIPT_UNKNOWN")
        self.assertEqual(self.fixture.archive.attributions(), ())

    def test_an_attribution_that_names_other_outlook_bytes_is_refused(self):
        attribution = a_belief(self.receipt, self.outlook)
        forged = resealed(attribution, outlook_digest="0" * 64)
        self.assertTrue(validate_attribution(forged))
        self.assertEqual(refused(self, lambda: self.fixture.append(forged)),
                         "ATTRIBUTION_INVALID")
        self.assertEqual(self.fixture.archive.attributions(), ())

    def test_a_renamed_or_copied_file_is_archive_tampered(self):
        attribution = self.fixture.append(a_belief(self.receipt, self.outlook))
        directory = self.fixture.archive.attributions_dir
        original = directory / (attribution_key(attribution) + ".json")
        moved = directory / "moved-attribution.json"
        moved.write_bytes(original.read_bytes())
        self.assertEqual(refused(self, lambda: list(self.fixture.archive.attributions())),
                         "ARCHIVE_TAMPERED")
        report = self.fixture.archive.verify()
        self.assertEqual(report["attributions"], 1)  # the original still reads
        self.assertEqual(report["problems"], ["moved-attribution.json: ARCHIVE_TAMPERED"])
        moved.unlink()
        original.unlink()
        renamed = directory / "renamed.json"
        renamed.write_text(json.dumps(attribution), encoding="utf-8")
        report = self.fixture.archive.verify()
        self.assertEqual((report["attributions"], report["problems"]),
                         (0, ["renamed.json: ARCHIVE_TAMPERED"]))

    def test_a_share_sum_above_one_is_verify_s_problem_not_a_write_refusal(self):
        # One exclusive create cannot see its siblings, so the write path stores both; the
        # archive's whole-view check reports the sum on the receipt's own file.
        self.fixture.append(a_belief(self.receipt, self.outlook, share="0.7"))
        self.fixture.append(a_belief(self.receipt, self.outlook, share="0.4",
                                     statement="A second belief explains another part."))
        report = self.fixture.archive.verify()
        self.assertEqual(report["attributions"], 2)
        receipt_file = "%s.json" % next(
            path.stem for path in self.fixture.archive.receipts_dir.glob("*.json"))
        self.assertEqual(report["problems"], [receipt_file + ": SHARE_OVER_ONE"])
        self.assertEqual(self.fixture.archive.attributions(), self.fixture.archive.attributions())

    def test_a_share_sum_at_or_below_one_is_clean(self):
        self.fixture.append(a_belief(self.receipt, self.outlook, share="0.5"))
        self.fixture.append(a_belief(self.receipt, self.outlook, share="0.5",
                                     statement="A second belief explains the rest."))
        self.assertEqual(self.fixture.archive.verify()["problems"], [])

    def test_an_attribution_whose_receipt_is_gone_is_reported(self):
        attribution = a_belief(self.receipt, self.outlook)
        self.fixture.append(attribution)
        next(self.fixture.archive.receipts_dir.glob("*.json")).unlink()
        report = self.fixture.archive.verify()
        self.assertEqual(report["attributions"], 1)
        self.assertEqual(report["problems"],
                         ["%s.json: RECEIPT_UNKNOWN" % attribution_key(attribution)])
        self.assertEqual(refused(self, lambda: self.fixture.archive.append_attribution(
            a_belief(self.receipt, self.outlook, statement="Another statement."))),
            "RECEIPT_UNKNOWN")


class Demonstration(unittest.TestCase):
    """The labelled synthetic demonstration: synthetic outlook, synthetic receipt, three causes."""

    @classmethod
    def setUpClass(cls):
        cls.temp = scratch_directory("arch4-demo-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name) / "outlook-archive"
        cls.archive = OutlookArchive(cls.root)
        cls.outlook = cls.archive.issue(an_outlook())
        cls.receipt = cls.archive.append_receipt(a_receipt(cls.outlook))
        cls.belief = cls.archive.append_attribution(a_belief(cls.receipt, cls.outlook, share="0.2"))
        cls.signal = cls.archive.append_attribution(a_signal(cls.receipt, cls.outlook, share="0.3"))
        cls.method = cls.archive.append_attribution(a_method(cls.receipt, cls.outlook, share="0.1"))

    def test_one_attribution_per_cause_is_stored(self):
        stored = self.archive.attributions()
        self.assertEqual(3, len(stored))
        self.assertEqual(["belief", "method", "signal"], sorted(record["cause"] for record in stored))
        for record in stored:
            self.assertTrue(record["synthetic"])

    def test_each_stored_key_is_rebuilt_from_the_record(self):
        for path in sorted(self.archive.attributions_dir.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.stem, attribution_key(record))

    def test_the_demonstration_verifies_clean(self):
        report = self.archive.verify()
        self.assertEqual((report["outlooks"], report["receipts"], report["attributions"]),
                         (1, 1, 3))
        self.assertEqual(report["problems"], [])

    def test_the_walk_reports_the_receipts_and_their_attributions_by_cause(self):
        payload = reg.load_register(root=ROOT)
        walked = dep.walk(self.outlook, register_payload=payload,
                          receipts=self.archive.receipts(),
                          attributions=self.archive.attributions())
        # Every existing field is still there, and the receipts list is the only addition.
        for field in ("outlook_id", "outlook_digest", "issued_at", "information_cutoff",
                      "horizon", "target_series_ref", "assumptions", "unknown", "stale"):
            self.assertIn(field, walked)
        self.assertEqual(len(walked["receipts"]), 1)
        entry = walked["receipts"][0]
        self.assertEqual(entry["receipt"]["content_digest"], self.receipt["content_digest"])
        self.assertEqual(set(entry["attributions"]), set(CAUSES))
        self.assertEqual([record["cause"] for record in entry["attributions"]["belief"]],
                         ["belief"])
        self.assertEqual([record["cause"] for record in entry["attributions"]["signal"]],
                         ["signal"])
        self.assertEqual([record["cause"] for record in entry["attributions"]["method"]],
                         ["method"])
        self.assertEqual(entry["attributions"]["belief"][0]["content_digest"],
                         self.belief["content_digest"])

    def test_walk_archive_reads_the_receipts_and_attributions(self):
        walked = dep.walk_archive(self.archive, register_payload=reg.load_register(root=ROOT))
        self.assertEqual(len(walked), 1)
        self.assertEqual(len(walked[0]["receipts"]), 1)
        self.assertEqual(sum(len(records) for records in
                             walked[0]["receipts"][0]["attributions"].values()), 3)

    def test_an_outlook_with_no_receipt_carries_an_empty_receipts_list(self):
        with scratch_directory("arch4-noreceipt-") as temp:
            archive = OutlookArchive(Path(temp) / "archive")
            outlook = archive.issue(an_outlook(outlook_id="outlook-no-receipt"))
            walked = dep.walk(outlook, register_payload=reg.load_register(root=ROOT))
            self.assertEqual(walked["receipts"], [])


class CommandLine(unittest.TestCase):
    """``scripts/outlook/attribute.py``: the person-driven write path, end to end."""

    def setUp(self):
        self.fixture = Fixture(self)
        self.outlook, self.receipt = self.fixture.outlook, self.fixture.receipt

    def run_cli(self, *arguments):
        return subprocess.run([str(INTERPRETER), str(SCRIPT)] + list(arguments),
                              capture_output=True, text=True, cwd=ROOT, timeout=120)

    def base_arguments(self):
        return ["--archive", str(self.fixture.root),
                "--outlook-id", self.outlook["outlook_id"],
                "--final-series-version", self.receipt["final_series_version"]]

    def test_the_command_attaches_the_record_and_prints_its_key_and_digest(self):
        run = self.run_cli(*self.base_arguments(), "--cause", "belief",
                           "--assumption-id", "availability:syn-bay-unit-2",
                           "--statement", "The synthetic unit was assumed available.",
                           "--attributed-by", "ARCH-4 fixture analyst",
                           "--attributed-at", "2026-11-27T00:00:00Z",
                           "--synthetic", "--share", "0.4")
        self.assertEqual(0, run.returncode, run.stderr)
        key = re.search(r"^key: ([0-9a-f]{64})$", run.stdout, re.M)
        digest = re.search(r"^digest: ([0-9a-f]{64})$", run.stdout, re.M)
        self.assertTrue(key, run.stdout)
        self.assertTrue(digest, run.stdout)
        stored = self.fixture.archive.attributions()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["content_digest"], digest.group(1))
        self.assertEqual(attribution_key(stored[0]), key.group(1))
        self.assertEqual(stored[0]["share"], "0.4")
        self.assertIs(True, stored[0]["synthetic"])

    def test_the_command_refuses_to_run_without_the_author(self):
        run = self.run_cli(*self.base_arguments(), "--cause", "belief",
                           "--assumption-id", "availability:syn-bay-unit-2",
                           "--statement", "A statement with no author.",
                           "--attributed-at", "2026-11-27T00:00:00Z")
        self.assertEqual(2, run.returncode)
        self.assertIn("--attributed-by", run.stderr)
        self.assertFalse(self.fixture.archive.attributions_dir.exists())

    def test_the_command_refuses_an_unknown_receipt(self):
        run = self.run_cli("--archive", str(self.fixture.root),
                           "--outlook-id", self.outlook["outlook_id"],
                           "--final-series-version", "no-such-final-series",
                           "--cause", "belief",
                           "--assumption-id", "availability:syn-bay-unit-2",
                           "--statement", "Nothing to explain.",
                           "--attributed-by", "ARCH-4 fixture analyst",
                           "--attributed-at", "2026-11-27T00:00:00Z", "--synthetic")
        self.assertEqual(1, run.returncode)
        self.assertIn("no stored receipt", run.stderr)
        self.assertFalse(self.fixture.archive.attributions_dir.exists())

    def test_the_command_reads_a_signal_reference_from_its_three_flags(self):
        run = self.run_cli(*self.base_arguments(), "--cause", "signal",
                           "--signal-source", SIGNAL["source"],
                           "--available-at", SIGNAL["available_at"],
                           "--effective-at", SIGNAL["effective_at"],
                           "--statement", "A later advisory carried the outage.",
                           "--attributed-by", "ARCH-4 fixture analyst",
                           "--attributed-at", "2026-11-27T00:00:00Z", "--synthetic")
        self.assertEqual(0, run.returncode, run.stderr)
        stored = self.fixture.archive.attributions()[0]
        self.assertEqual(stored["signal_ref"], SIGNAL)

    def test_the_command_never_issues_or_scores_anything(self):
        before = {path.relative_to(self.fixture.root): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(self.fixture.root.rglob("*")) if path.is_file()}
        run = self.run_cli(*self.base_arguments(), "--cause", "method",
                           "--method-ref", self.outlook["model_version"],
                           "--statement", "The method was wrong for this month.",
                           "--attributed-by", "ARCH-4 fixture analyst",
                           "--attributed-at", "2026-11-27T00:00:00Z", "--synthetic")
        self.assertEqual(0, run.returncode, run.stderr)
        after = {path.relative_to(self.fixture.root): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(self.fixture.root.rglob("*"))
                 if path.is_file() and "attributions" not in path.parts}
        self.assertEqual(before, after)  # no outlook and no receipt was written or changed

    def test_the_same_statement_twice_is_refused(self):
        arguments = self.base_arguments() + ["--cause", "belief",
                                            "--assumption-id", "availability:syn-bay-unit-2",
                                            "--statement", "The same statement twice.",
                                            "--attributed-by", "ARCH-4 fixture analyst",
                                            "--attributed-at", "2026-11-27T00:00:00Z",
                                            "--synthetic"]
        self.assertEqual(0, self.run_cli(*arguments).returncode)
        run = self.run_cli(*arguments)
        self.assertEqual(1, run.returncode)
        self.assertIn("ATTRIBUTION_DUPLICATE", run.stderr)
        self.assertEqual(len(self.fixture.archive.attributions()), 1)


class DirectionCheck(unittest.TestCase):
    """ARCH-4's direction check: 0 attributions in the real archive, 3 in the fixture."""

    def test_the_fixture_demonstration_holds_one_attribution_per_cause(self):
        with scratch_directory("arch4-direction-") as temp:
            archive = OutlookArchive(Path(temp) / "outlook-archive")
            outlook = archive.issue(an_outlook())
            receipt = archive.append_receipt(a_receipt(outlook))
            archive.append_attribution(a_belief(receipt, outlook))
            archive.append_attribution(a_signal(receipt, outlook))
            archive.append_attribution(a_method(receipt, outlook))
            self.assertEqual(3, len(archive.attributions()))
            self.assertEqual({"belief", "signal", "method"},
                             {record["cause"] for record in archive.attributions()})

    @unittest.skipUnless(REAL_ARCHIVE.is_dir(),
                         "the runtime outlook archive is linked into this worktree under "
                         ".local/; absent elsewhere")
    def test_the_real_archive_holds_no_attribution(self):
        archive = OutlookArchive(REAL_ARCHIVE)
        self.assertEqual((), archive.attributions())
        report = archive.verify()
        # OUT-3: two vintages, or three once the third November vintage is issued
        outlooks = 3 if "outlook-2026-11-system-v3" in archive.issue_ids() else 2
        self.assertEqual((report["outlooks"], report["receipts"], report["attributions"]),
                         (outlooks, 0, 0))
        self.assertEqual(report["problems"], [])

    def test_the_test_module_stays_offline(self):
        text = Path(__file__).read_text(encoding="utf-8")
        roots = set(re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M))
        roots |= {name.split(".")[0] for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import",
                                                            text, re.M) if not name.startswith(".")}
        for root in roots:
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)


class StdlibOnly(unittest.TestCase):
    def imported_roots(self, path):
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_write_path_imports_only_the_standard_library_and_this_repository(self):
        roots = self.imported_roots(SCRIPT)
        self.assertTrue(roots)
        for root in roots:
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                            root)

    def test_the_write_path_reaches_only_the_archive_module(self):
        text = SCRIPT.read_text(encoding="utf-8")
        reached = set(re.findall(r"^from (src\.[A-Za-z0-9_.]+) import", text, re.M))
        self.assertEqual(reached, {"src.outlook.records"})


if __name__ == "__main__":
    unittest.main()
