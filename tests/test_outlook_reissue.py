"""OUT-1: the issue command, the re-issue preview and the confirmed re-issue, offline.

Every case builds its own archive, inputs and values files in a scratch
directory (the system temporary directory, else the ignored ``.local/tmp/``);
the values are invented numbers, labelled synthetic where a record carries a
provenance flag, and nothing is written into the owner's runtime archive
``.local/outlook-archive`` — :class:`ZRealArchiveAcceptanceNothingWritten`
reads it after the run and checks its counts and its bytes. No network, model,
cloud or clock call is made (every instant is given).

The acceptance lines have one class each, named after the line:

* :class:`AcceptanceReissueNamesTheMarkThePredecessorAndTheChangedBeliefs`
* :class:`AcceptanceDeltaFromTheTwoValuesFilesByDigest`
* :class:`AcceptanceRefusedWhenThePredecessorDigestIsTheSame`
* :class:`AcceptanceCommandRefusesWithoutCutoffAndMethodRecord`
* :class:`AcceptanceSyntheticInheritanceOneWay`
* :class:`AcceptanceExistingShapeKeptAndStdlibOnly`
* rework round 1: :class:`ReworkConfirmationRequiredAtTheRecordsLayer` and
  :class:`ReworkReissueWithoutAMark` (the mark-free ``--supersedes`` path)
* OUT-3: :class:`NotLatestVintageOnTheRealArchiveShape` (the real archive's NOT_LATEST_VINTAGE
  case on a scratch archive of its shape)
* :class:`ZRealArchiveAcceptanceNothingWritten` (sorts last, so it runs after the others)
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
from src.outlook import reissue
from src.outlook.records import (
    OUTLOOK_KEYS,
    OutlookArchive,
    OutlookError,
    build_outlook,
    check_supersedes,
    validate_outlook,
)

SCRIPT = ROOT / "scripts" / "outlook" / "issue.py"
REAL_ARCHIVE = ROOT / ".local" / "outlook-archive"

#: A register row the committed register carries (the mark store refuses an
#: unknown assumption), and a second one for the two-mark case.
BELIEF = "rules:billing_month_clock"
OTHER_BELIEF = "price:one_day_embargo"
ASSUMPTIONS = ["price:final_settlement_lmp", OTHER_BELIEF, BELIEF]

HORIZON = {"label": "month", "start": "2026-10-25T16:00:00Z", "end": "2026-10-25T20:00:00Z"}
HOURS = ["2026-10-26T00:00:00", "2026-10-26T01:00:00", "2026-10-26T02:00:00",
         "2026-10-26T03:00:00"]
PREVIOUS_VALUES = [100, 200.5, 300, 400]
NEW_VALUES = [110, 190.5, 330, 400]
SERIES = {"table": "fixture.final_series", "column": "lwap", "version": "fixture-v1"}

PREDECESSOR_ISSUED = "2026-10-16T00:00:00Z"
PREDECESSOR_CUTOFF = "2026-08-25T16:00:00Z"
MARKED_AT = "2026-10-17T00:00:00Z"
REVISION = "abcdef1"
CUTOFF = "2026-10-14T16:00:00Z"
ISSUED_AT = "2026-10-18T00:00:00Z"
NEW_ID = "fixture-2026-11-v2"
ISSUER = "OUT-1 test person"


def scratch_directory(prefix="out1-"):
    """The system temporary directory, else the ignored workspace ``.local/tmp/``."""
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "tmp"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_values(path, values, *, series="SYSTEM", note="fixture"):
    """One values file in the shape the archive's vintages cite: hours with a point value."""
    payload = {"label": "synthetic fixture values (OUT-1 tests)", "note": note, "series": series,
               "hours": [{"hour_start": hour, "value": value} for hour, value in zip(HOURS, values)]}
    Path(path).write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_of(path)


def snapshot(root):
    """Every file under a directory by relative path and SHA-256; empty when absent."""
    root = Path(root)
    if not root.exists():
        return {}
    return {str(path.relative_to(root)): sha256_of(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


#: The owner's archive as it stood when this module was imported, before any test ran.
REAL_BEFORE = snapshot(REAL_ARCHIVE) if REAL_ARCHIVE.exists() else None


class Fixture:
    """A scratch archive with one issued predecessor, its values file, one input and a method run."""

    def __init__(self, test, *, predecessor_synthetic=False, method_synthetic=False,
                 new_values=None, mark_synthetic=False, mark=True):
        self.temp = scratch_directory()
        test.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        # No test may ever write the owner's archive: every archive lives in scratch.
        assert REAL_ARCHIVE.resolve() not in (self.dir / "archive").resolve().parents
        self.archive = OutlookArchive(self.dir / "archive")
        self.input_path = self.dir / "inputs" / "export.csv"
        self.input_path.parent.mkdir(parents=True)
        self.input_path.write_text("hour_start,value\nsynthetic,1\n", encoding="utf-8")
        values_dir = self.dir / "archive" / "values"
        values_dir.mkdir(parents=True)
        self.previous_values = values_dir / "predecessor.json"
        previous_digest = write_values(self.previous_values, PREVIOUS_VALUES)
        self.predecessor = self.archive.issue(build_outlook(
            outlook_id="fixture-2026-11", issued_at=PREDECESSOR_ISSUED,
            information_cutoff=PREDECESSOR_CUTOFF, horizon=HORIZON, target_series_ref=SERIES,
            inputs=[{"name": "export.csv", "digest": sha256_of(self.input_path)}],
            assumption_ids=ASSUMPTIONS, model_version="fixture-method v1",
            values_ref={"path_hint": str(self.previous_values), "sha256": previous_digest,
                        "rows": len(HOURS)},
            issuer="OUT-1 test fixture", synthetic=predecessor_synthetic))
        self.new_values = values_dir / "successor.json"
        write_values(self.new_values, NEW_VALUES if new_values is None else new_values)
        self.method_path = self.dir / "method.json"
        self.write_method(synthetic=method_synthetic)
        self.mark_path = None
        if mark:
            self.mark_path = self.add_mark(BELIEF, synthetic=mark_synthetic)

    def method(self, **overrides):
        record = {
            "method_version": "fixture-method v2",
            "target_series_ref": dict(SERIES, version="fixture-v2"),
            "horizon": dict(HORIZON),
            "information_cutoff": CUTOFF,
            "assumption_ids": list(ASSUMPTIONS),
            "inputs": [{"name": "export.csv", "path": str(self.input_path),
                        "digest": sha256_of(self.input_path)}],
            "values": {"path": str(self.new_values), "sha256": sha256_of(self.new_values)},
            "synthetic": False,
        }
        record.update(overrides)
        return record

    def write_method(self, **overrides):
        self.method_path.write_text(json.dumps(self.method(**overrides), indent=1) + "\n",
                                    encoding="utf-8")
        return self.method_path

    def add_mark(self, assumption_id, *, synthetic=False, marked_at=MARKED_AT, revision=REVISION):
        dep.mark_stale(self.archive, assumption_id, revision, marked_at=marked_at,
                       synthetic=synthetic)
        mark = [item for item in dep.marks_of(self.archive)
                if item["assumption_id"] == assumption_id and item["new_revision"] == revision
                and item["synthetic"] is synthetic][0]
        path = self.dir / ("mark-%s.json" % mark["content_digest"][:12])
        path.write_text(json.dumps(mark), encoding="utf-8")
        return path

    def mark(self, path=None):
        return json.loads((path or self.mark_path).read_text(encoding="utf-8"))

    def preview(self, marks=None, **arguments):
        arguments.setdefault("outlook_id", NEW_ID)
        arguments.setdefault("issuer", ISSUER)
        arguments.setdefault("cutoff", CUTOFF)
        if marks is None and "supersedes" not in arguments:
            marks = [self.mark()]
        return reissue.build_preview(self.archive, marks or [], self.method_path, **arguments)

    def confirm(self, preview, ref, **overrides):
        """The confirming call: the id, issuer, method record and cutoff are its own."""
        arguments = dict(outlook_id=NEW_ID, issuer=ISSUER, method_record=self.method_path,
                         cutoff=CUTOFF)
        arguments.update(overrides)
        return reissue.issue_confirmed(self.archive, preview, issued_at=ISSUED_AT,
                                       confirmation_ref=ref, **arguments)


def refused(test, call, error=reissue.ReissueError):
    with test.assertRaises(error) as caught:
        call()
    return caught.exception.code


def run_cli(*arguments):
    return subprocess.run([sys.executable, str(SCRIPT)] + list(arguments),
                          capture_output=True, text=True, cwd=ROOT, timeout=180)


class AcceptanceReissueNamesTheMarkThePredecessorAndTheChangedBeliefs(unittest.TestCase):
    """A re-issue names the stale mark, the previous vintage by digest and the changed assumptions."""

    def test_the_preview_names_the_mark_the_predecessor_and_the_changed_beliefs(self):
        fixture = Fixture(self)
        mark = fixture.mark()
        preview = fixture.preview()
        self.assertEqual(preview["kind"], "ReissuePreview")
        self.assertEqual(preview["predecessor"]["outlook_id"], "fixture-2026-11")
        self.assertEqual(preview["predecessor"]["outlook_digest"], fixture.predecessor["content_digest"])
        self.assertEqual(preview["predecessor"]["values_digest"],
                         fixture.predecessor["values_ref"]["sha256"])
        self.assertEqual([item["content_digest"] for item in preview["stale_marks"]],
                         [mark["content_digest"]])
        self.assertEqual(preview["stale_marks"][0]["new_revision"], REVISION)
        self.assertEqual(preview["changed_assumption_ids"], [BELIEF])
        self.assertEqual(preview["information_cutoff"], CUTOFF)
        self.assertEqual(preview["method_record"]["sha256"], sha256_of(fixture.method_path))
        self.assertEqual(preview["content_digest"], compute_content_digest(preview))
        self.assertIs(reissue.validate_preview(preview), preview)

    def test_the_confirmed_issue_writes_a_vintage_that_supersedes_the_marked_one(self):
        fixture = Fixture(self)
        preview = fixture.preview()
        record = fixture.confirm(preview, "confirmation-fixture-1")
        stored = fixture.archive.outlook("fixture-2026-11-v2")
        self.assertEqual(stored, record)
        block = stored["supersedes"]
        self.assertEqual(block["outlook_id"], "fixture-2026-11")
        self.assertEqual(block["outlook_digest"], fixture.predecessor["content_digest"])
        self.assertEqual(block["stale_marks"], [{"content_digest": fixture.mark()["content_digest"],
                                                 "assumption_id": BELIEF, "synthetic": False}])
        self.assertEqual(block["changed_assumption_ids"], [BELIEF])
        self.assertEqual(block["delta"], preview["delta"])
        self.assertEqual(block["confirmation_ref"], "confirmation-fixture-1")
        self.assertEqual(stored["information_cutoff"], CUTOFF)
        self.assertEqual(stored["model_version"], "fixture-method v2")
        report = fixture.archive.verify()
        self.assertEqual((report["outlooks"], report["problems"]), (2, []))
        # The predecessor's bytes are untouched: a re-issue adds a file, it never edits one.
        self.assertEqual(fixture.archive.outlook("fixture-2026-11"), fixture.predecessor)

    def test_two_marks_of_one_vintage_carry_both_changed_beliefs(self):
        fixture = Fixture(self)
        second = fixture.add_mark(OTHER_BELIEF)
        preview = fixture.preview(marks=[fixture.mark(), fixture.mark(second)])
        self.assertEqual(preview["changed_assumption_ids"], sorted([BELIEF, OTHER_BELIEF]))
        self.assertEqual(len(preview["stale_marks"]), 2)

    def test_a_mark_that_is_not_in_the_archive_store_is_refused(self):
        fixture = Fixture(self)
        other = Fixture(self)
        self.assertEqual(refused(self, lambda: fixture.preview(marks=[other.mark()])), "MARK_UNKNOWN")
        forged = dict(fixture.mark(), new_revision="1234567")
        forged["content_digest"] = compute_content_digest(forged)
        self.assertEqual(refused(self, lambda: fixture.preview(marks=[forged])), "MARK_UNKNOWN")

    def test_a_mark_on_an_older_vintage_is_answered_from_the_newest(self):
        fixture = Fixture(self)
        fixture.confirm(fixture.preview(), "confirmation-fixture-1")
        # The first vintage's mark again: the current vintage is now the re-issue.
        self.assertEqual(refused(self, lambda: fixture.preview(outlook_id="fixture-2026-11-v3")),
                         "NOT_LATEST_VINTAGE")

    def test_no_issue_without_a_recorded_confirmation(self):
        fixture = Fixture(self)
        preview = fixture.preview()
        for blank in ("", "   ", None):
            self.assertEqual(refused(self, lambda: fixture.confirm(preview, blank)),
                "CONFIRMATION_MISSING")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_a_preview_that_no_longer_matches_the_archive_is_refused_and_nothing_written(self):
        fixture = Fixture(self)
        preview = fixture.preview()
        # The method run's values file is rewritten after the preview was confirmed.
        write_values(fixture.new_values, [111, 190.5, 330, 400])
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "c-1")),
            "VALUES_DIGEST_MISMATCH")
        # The method record itself is rewritten to match: the rebuilt preview differs.
        fixture.write_method()
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "c-1")),
            "PREVIEW_STALE")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_a_resealed_issuer_or_id_edit_is_refused_against_the_confirming_call(self):
        # Rework round 1, finding 1: a preview whose issuer or vintage id is edited and
        # resealed is a valid preview on its own, so the confirming call states the
        # id, the issuer, the method record and the cutoff, and a preview that names
        # others is refused. Nothing is written.
        fixture = Fixture(self)
        preview = fixture.preview()
        for field, value in (("issuer", "someone else"), ("outlook_id", "fixture-forged")):
            forged = dict(preview, outlook=dict(preview["outlook"], **{field: value}))
            forged["content_digest"] = compute_content_digest(forged)
            self.assertIs(reissue.validate_preview(forged), forged)
            self.assertEqual(refused(self, lambda: fixture.confirm(forged, "c-1")), "PREVIEW_MISMATCH")
        other_method = fixture.dir / "other-method.json"
        other_method.write_bytes(fixture.method_path.read_bytes())
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "c-1", method_record=other_method)),
                         "PREVIEW_MISMATCH")
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "c-1", cutoff="2026-10-15T16:00:00Z")),
                         "PREVIEW_MISMATCH")
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "c-1", issuer="someone else")),
                         "PREVIEW_MISMATCH")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))
        # The same cutoff instant written in another offset is the same cutoff.
        fixture.confirm(preview, "c-1", cutoff="2026-10-15T00:00:00+08:00")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11", NEW_ID))

    def test_an_edited_preview_is_refused(self):
        fixture = Fixture(self)
        preview = fixture.preview()
        edited = dict(preview, changed_assumption_ids=[OTHER_BELIEF])
        self.assertEqual(refused(self, lambda: reissue.validate_preview(edited)), "PREVIEW_INVALID")
        resealed = dict(edited)
        resealed["content_digest"] = compute_content_digest(resealed)
        self.assertEqual(refused(self, lambda: reissue.validate_preview(resealed)), "PREVIEW_INVALID")

    def test_the_archive_refuses_a_successor_whose_predecessor_is_missing_or_other_bytes(self):
        fixture = Fixture(self)
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        empty = OutlookArchive(fixture.dir / "empty")
        self.assertEqual(refused(self, lambda: empty.issue(record), OutlookError), "OUTLOOK_UNKNOWN")
        other = dict(fixture.predecessor, issuer="someone else")
        other["content_digest"] = compute_content_digest(other)
        self.assertEqual(refused(self, lambda: check_supersedes(record, other), OutlookError),
                         "OUTLOOK_DIGEST_MISMATCH")

    def test_verify_reports_a_predecessor_replaced_after_the_reissue(self):
        fixture = Fixture(self)
        fixture.confirm(fixture.preview(), "c-1")
        path = fixture.archive.outlooks_dir / "fixture-2026-11.json"
        replaced = dict(fixture.predecessor, issuer="replaced")
        replaced["content_digest"] = compute_content_digest(replaced)
        path.write_text(json.dumps(replaced), encoding="utf-8")
        self.assertIn("fixture-2026-11-v2.json: OUTLOOK_DIGEST_MISMATCH",
                      fixture.archive.verify()["problems"])


class AcceptanceDeltaFromTheTwoValuesFilesByDigest(unittest.TestCase):
    """The delta is computed from the two values files, each read by its digest."""

    def test_the_delta_states_both_digests_and_the_difference_per_horizon(self):
        fixture = Fixture(self)
        delta = fixture.preview()["delta"]
        self.assertEqual(delta["previous_values_digest"], sha256_of(fixture.previous_values))
        self.assertEqual(delta["new_values_digest"], sha256_of(fixture.new_values))
        # new - previous per hour: 10, -10, 30, 0.
        self.assertEqual(delta["horizons"], [{
            "label": "month", "start": HORIZON["start"], "end": HORIZON["end"], "hours": 4,
            "mean_difference": "7.500000", "mean_abs_difference": "12.500000",
            "min_difference": "-10.000000", "max_difference": "30.000000"}])

    def test_a_predecessor_values_file_that_is_not_its_digest_is_refused(self):
        fixture = Fixture(self)
        write_values(fixture.previous_values, [101, 200.5, 300, 400])
        self.assertEqual(refused(self, fixture.preview), "VALUES_DIGEST_MISMATCH")

    def test_a_new_values_file_that_is_not_the_method_digest_is_refused(self):
        fixture = Fixture(self)
        fixture.write_method(values={"path": str(fixture.new_values), "sha256": "0" * 64})
        self.assertEqual(refused(self, fixture.preview), "VALUES_DIGEST_MISMATCH")

    def test_values_files_over_other_hours_or_series_are_refused(self):
        fixture = Fixture(self)
        payload = json.loads(fixture.new_values.read_text(encoding="utf-8"))
        payload["hours"] = payload["hours"][:3]
        fixture.new_values.write_text(json.dumps(payload), encoding="utf-8")
        fixture.write_method()
        self.assertEqual(refused(self, fixture.preview), "HOURS_MISMATCH")
        write_values(fixture.new_values, NEW_VALUES, series="CVIS")
        fixture.write_method()
        self.assertEqual(refused(self, fixture.preview), "HOURS_MISMATCH")

    def test_every_input_is_checked_against_its_digest_before_anything_is_issued(self):
        fixture = Fixture(self)
        fixture.input_path.write_text("hour_start,value\nchanged,2\n", encoding="utf-8")
        self.assertEqual(refused(self, fixture.preview), "INPUT_DIGEST_MISMATCH")
        method, _digest = reissue.load_method_record(fixture.method_path)
        self.assertEqual(refused(self, lambda: reissue.build_issue(
            method, outlook_id="x-1", issued_at=ISSUED_AT, issuer="p", cutoff=CUTOFF)),
            "INPUT_DIGEST_MISMATCH")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))


class AcceptanceRefusedWhenThePredecessorDigestIsTheSame(unittest.TestCase):
    """A vintage whose values digest equals its predecessor's is refused REPEATS_PREDECESSOR."""

    def test_the_same_values_file_is_refused_by_the_preview(self):
        fixture = Fixture(self)
        fixture.write_method(values={"path": str(fixture.previous_values),
                                     "sha256": sha256_of(fixture.previous_values)})
        self.assertEqual(refused(self, fixture.preview), "REPEATS_PREDECESSOR")

    def test_the_same_hourly_values_in_other_bytes_are_refused_too(self):
        fixture = Fixture(self, new_values=PREVIOUS_VALUES)
        write_values(fixture.new_values, PREVIOUS_VALUES, note="only the header moved")
        fixture.write_method()
        self.assertNotEqual(sha256_of(fixture.new_values), sha256_of(fixture.previous_values))
        self.assertEqual(refused(self, fixture.preview), "REPEATS_PREDECESSOR")

    def test_the_archive_refuses_a_record_whose_delta_repeats_the_predecessor(self):
        fixture = Fixture(self)
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        fields = {key: value for key, value in record.items()
                  if key not in ("schema_version", "kind", "content_digest", "supersedes")}
        block = json.loads(json.dumps(record["supersedes"]))
        fields["values_ref"] = dict(fixture.predecessor["values_ref"])
        block["delta"]["new_values_digest"] = fixture.predecessor["values_ref"]["sha256"]
        self.assertEqual(refused(self, lambda: build_outlook(**fields, supersedes=block), OutlookError),
                         "REPEATS_PREDECESSOR")

    def test_a_first_issue_that_repeats_the_newest_vintage_is_refused(self):
        fixture = Fixture(self)
        method, _digest = reissue.load_method_record(fixture.write_method(
            values={"path": str(fixture.previous_values), "sha256": sha256_of(fixture.previous_values)}))
        self.assertEqual(refused(self, lambda: reissue.build_issue(
            method, outlook_id="fixture-2026-11-b", issued_at=ISSUED_AT, issuer="p", cutoff=CUTOFF,
            archive=fixture.archive)), "REPEATS_PREDECESSOR")

    def test_the_command_refuses_with_the_reason_and_writes_nothing(self):
        fixture = Fixture(self)
        fixture.write_method(values={"path": str(fixture.previous_values),
                                     "sha256": sha256_of(fixture.previous_values)})
        run = run_cli("--archive", str(fixture.archive.root), "--method-record", str(fixture.method_path),
                      "--cutoff", CUTOFF, "--outlook-id", "fixture-2026-11-v2", "--issuer", "p",
                      "--issued-at", ISSUED_AT, "--from-stale", str(fixture.mark_path),
                      "--confirm", "c-1")
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("REPEATS_PREDECESSOR", run.stderr)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))


class AcceptanceCommandRefusesWithoutCutoffAndMethodRecord(unittest.TestCase):
    """The command refuses to run without an explicit cutoff and method record."""

    def base(self, fixture):
        return ["--archive", str(fixture.archive.root), "--outlook-id", "fixture-2026-11-b",
                "--issuer", "OUT-1 test person", "--issued-at", ISSUED_AT]

    def test_without_a_cutoff_the_command_refuses(self):
        fixture = Fixture(self)
        run = run_cli(*self.base(fixture), "--method-record", str(fixture.method_path))
        self.assertEqual(run.returncode, 2)
        self.assertIn("--cutoff", run.stderr)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_without_a_method_record_the_command_refuses(self):
        fixture = Fixture(self)
        run = run_cli(*self.base(fixture), "--cutoff", CUTOFF)
        self.assertEqual(run.returncode, 2)
        self.assertIn("--method-record", run.stderr)
        run = run_cli(*self.base(fixture), "--cutoff", CUTOFF, "--from-stale", str(fixture.mark_path),
                      "--confirm", "c-1")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_a_cutoff_that_is_not_the_method_record_s_own_is_refused(self):
        fixture = Fixture(self)
        run = run_cli(*self.base(fixture), "--method-record", str(fixture.method_path),
                      "--cutoff", "2026-10-15T16:00:00Z")
        self.assertEqual(run.returncode, 1)
        self.assertIn("CUTOFF_MISMATCH", run.stderr)
        # The same instant in another offset is the same cutoff.
        method, _digest = reissue.load_method_record(fixture.method_path)
        reissue.check_cutoff(method, "2026-10-15T00:00:00+08:00")

    def test_the_command_issues_a_first_vintage_from_a_method_record(self):
        fixture = Fixture(self, mark=False)
        run = run_cli(*self.base(fixture), "--method-record", str(fixture.method_path),
                      "--cutoff", CUTOFF)
        self.assertEqual(run.returncode, 0, run.stderr)
        digest = re.search(r"^digest: ([0-9a-f]{64})$", run.stdout, re.M).group(1)
        stored = fixture.archive.outlook("fixture-2026-11-b")
        self.assertEqual(stored["content_digest"], digest)
        self.assertEqual(set(stored), OUTLOOK_KEYS)
        self.assertEqual(stored["inputs"], [{"name": "export.csv", "digest": sha256_of(fixture.input_path)}])
        self.assertEqual(stored["values_ref"], {"path_hint": str(fixture.new_values),
                                                "sha256": sha256_of(fixture.new_values), "rows": 4})
        self.assertEqual(stored["information_cutoff"], CUTOFF)
        again = run_cli(*self.base(fixture), "--method-record", str(fixture.method_path),
                        "--cutoff", CUTOFF)
        self.assertEqual(again.returncode, 1)
        self.assertIn("OUTLOOK_IMMUTABLE", again.stderr)

    def test_the_reissue_loop_through_the_command_preview_then_confirm(self):
        fixture = Fixture(self)
        preview_path = fixture.dir / "draft.json"
        arguments = ["--archive", str(fixture.archive.root), "--method-record", str(fixture.method_path),
                     "--cutoff", CUTOFF, "--issued-at", ISSUED_AT,
                     "--outlook-id", "fixture-2026-11-v2", "--issuer", "p"]
        shown = run_cli(*arguments, "--from-stale", str(fixture.mark_path),
                        "--preview-out", str(preview_path))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("not confirmed: nothing issued", shown.stdout)
        self.assertIn("changed assumptions: %s" % BELIEF, shown.stdout)
        self.assertIn("predecessor: fixture-2026-11 %s" % fixture.predecessor["content_digest"], shown.stdout)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))
        preview = json.loads(preview_path.read_text(encoding="utf-8"))
        self.assertIs(reissue.validate_preview(preview), preview)
        unconfirmed = run_cli(*arguments, "--preview", str(preview_path))
        self.assertEqual(unconfirmed.returncode, 2)
        # Rework round 1, finding 1: the draft edited to another issuer and resealed
        # is refused, because the issuer is this run's own --issuer.
        forged = dict(preview, outlook=dict(preview["outlook"], issuer="someone else"))
        forged["content_digest"] = compute_content_digest(forged)
        forged_path = fixture.dir / "forged.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        refused_run = run_cli(*arguments, "--preview", str(forged_path), "--confirm", "confirmation-7")
        self.assertEqual(refused_run.returncode, 1, refused_run.stdout)
        self.assertIn("PREVIEW_MISMATCH", refused_run.stderr)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))
        issued = run_cli(*arguments, "--preview", str(preview_path), "--confirm", "confirmation-7")
        self.assertEqual(issued.returncode, 0, issued.stderr)
        stored = fixture.archive.outlook("fixture-2026-11-v2")
        self.assertEqual(stored["supersedes"]["confirmation_ref"], "confirmation-7")
        self.assertIn("supersedes: fixture-2026-11 %s" % fixture.predecessor["content_digest"],
                      issued.stdout)

    def test_dry_run_writes_nothing(self):
        fixture = Fixture(self, mark=False)
        run = run_cli(*self.base(fixture), "--method-record", str(fixture.method_path),
                      "--cutoff", CUTOFF, "--dry-run")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("dry run: nothing issued", run.stdout)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))


class AcceptanceSyntheticInheritanceOneWay(unittest.TestCase):
    """Synthetic inheritance one way, as in the records module."""

    def test_a_real_reissue_from_a_demonstration_mark_is_refused(self):
        fixture = Fixture(self, mark_synthetic=True)
        self.assertEqual(refused(self, fixture.preview), "SYNTHETIC_ONE_WAY")

    def test_a_real_reissue_of_a_synthetic_predecessor_is_refused(self):
        fixture = Fixture(self, predecessor_synthetic=True)
        self.assertEqual(refused(self, fixture.preview), "SYNTHETIC_ONE_WAY")

    def test_a_synthetic_reissue_may_rest_on_either(self):
        for predecessor, mark in ((True, True), (False, False), (False, True), (True, False)):
            fixture = Fixture(self, predecessor_synthetic=predecessor, mark_synthetic=mark,
                              method_synthetic=True)
            record = fixture.confirm(fixture.preview(), "c-1")
            self.assertIs(record["synthetic"], True)
            self.assertEqual(fixture.archive.verify()["problems"], [])

    def test_the_records_module_refuses_the_false_claim_on_its_own(self):
        fixture = Fixture(self, method_synthetic=True, mark_synthetic=True)
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        fields = {key: value for key, value in record.items()
                  if key not in ("schema_version", "kind", "content_digest", "supersedes")}
        fields["synthetic"] = False
        self.assertEqual(refused(self, lambda: build_outlook(**fields, supersedes=record["supersedes"]),
                                 OutlookError), "OUTLOOK_INVALID")
        real = Fixture(self, predecessor_synthetic=True, method_synthetic=True)
        record = reissue._vintage(real.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        fields = {key: value for key, value in record.items()
                  if key not in ("schema_version", "kind", "content_digest", "supersedes")}
        fields["synthetic"] = False
        block = dict(record["supersedes"])
        forged = build_outlook(**fields, supersedes=block)
        self.assertEqual(refused(self, lambda: real.archive.issue(forged), OutlookError),
                         "SUPERSEDES_INVALID")


def block_fields(record):
    """The builder's keyword fields of one sealed record, without its ``supersedes`` block."""
    return {key: value for key, value in record.items()
            if key not in ("schema_version", "kind", "content_digest", "supersedes")}


class ReworkConfirmationRequiredAtTheRecordsLayer(unittest.TestCase):
    """Rework round 1, finding 3: no re-issue record exists without a confirmation reference."""

    def test_a_reissue_record_without_a_confirmation_reference_is_refused(self):
        fixture = Fixture(self)
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        for blank in (None, "", "   ", 7):
            block = dict(record["supersedes"], confirmation_ref=blank)
            self.assertEqual(refused(self, lambda: build_outlook(**block_fields(record), supersedes=block),
                                     OutlookError), "OUTLOOK_INVALID")
        # Nothing reaches the archive's own write path without one either.
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_a_first_issue_carries_no_block_and_needs_no_reference(self):
        fixture = Fixture(self, mark=False)
        self.assertNotIn("supersedes", fixture.predecessor)
        self.assertIs(validate_outlook(fixture.predecessor), fixture.predecessor)


class ReworkReissueWithoutAMark(unittest.TestCase):
    """Rework round 1, the orchestrator's decision: --supersedes <id> --reason method_changed | inputs_refreshed."""

    def test_a_method_change_reissues_without_a_mark(self):
        fixture = Fixture(self, mark=False)
        preview = fixture.preview(supersedes="fixture-2026-11", reason="method_changed")
        self.assertEqual((preview["reason"], preview["stale_marks"], preview["changed_assumption_ids"]),
                         ("method_changed", [], []))
        self.assertEqual(preview["delta"]["horizons"][0]["mean_difference"], "7.500000")
        record = fixture.confirm(preview, "c-1")
        block = record["supersedes"]
        self.assertEqual((block["reason"], block["stale_marks"], block["changed_assumption_ids"]),
                         ("method_changed", [], []))
        self.assertEqual(block["outlook_digest"], fixture.predecessor["content_digest"])
        self.assertEqual(fixture.archive.verify()["problems"], [])

    def test_a_method_change_needs_another_method_version(self):
        fixture = Fixture(self, mark=False)
        fixture.write_method(method_version="fixture-method v1")
        self.assertEqual(refused(self, lambda: fixture.preview(supersedes="fixture-2026-11",
                                                               reason="method_changed")),
                         "METHOD_UNCHANGED")
        # The records layer holds the same rule on its own.
        fixture.write_method()
        record = reissue._vintage(fixture.preview(supersedes="fixture-2026-11", reason="method_changed"),
                                  issued_at=ISSUED_AT, confirmation_ref="c-1")
        fields = dict(block_fields(record), model_version="fixture-method v1")
        same = build_outlook(**fields, supersedes=record["supersedes"])
        self.assertEqual(refused(self, lambda: fixture.archive.issue(same), OutlookError),
                         "SUPERSEDES_INVALID")

    def test_an_input_refresh_needs_another_input_digest(self):
        fixture = Fixture(self, mark=False)
        fixture.write_method(method_version="fixture-method v1")
        self.assertEqual(refused(self, lambda: fixture.preview(supersedes="fixture-2026-11",
                                                               reason="inputs_refreshed")),
                         "INPUTS_UNCHANGED")
        fixture.input_path.write_text("hour_start,value\nrefreshed,2\n", encoding="utf-8")
        fixture.write_method(method_version="fixture-method v1")
        record = fixture.confirm(fixture.preview(supersedes="fixture-2026-11", reason="inputs_refreshed"),
                                 "c-1")
        self.assertEqual(record["supersedes"]["reason"], "inputs_refreshed")

    def test_the_delta_newest_vintage_and_confirmation_rules_are_unchanged(self):
        fixture = Fixture(self, mark=False)
        fixture.write_method(values={"path": str(fixture.previous_values),
                                     "sha256": sha256_of(fixture.previous_values)})
        self.assertEqual(refused(self, lambda: fixture.preview(supersedes="fixture-2026-11",
                                                               reason="method_changed")),
                         "REPEATS_PREDECESSOR")
        fixture.write_method()
        preview = fixture.preview(supersedes="fixture-2026-11", reason="method_changed")
        self.assertEqual(refused(self, lambda: fixture.confirm(preview, "")), "CONFIRMATION_MISSING")
        fixture.confirm(preview, "c-1")
        self.assertEqual(refused(self, lambda: fixture.preview(
            supersedes="fixture-2026-11", reason="method_changed", outlook_id="fixture-2026-11-v3")),
            "NOT_LATEST_VINTAGE")
        self.assertEqual(refused(self, lambda: fixture.preview(supersedes="no-such-vintage",
                                                               reason="method_changed")),
                         "PREDECESSOR_UNKNOWN")

    def test_a_reason_needs_the_right_kind_of_predecessor_name(self):
        fixture = Fixture(self)
        self.assertEqual(refused(self, lambda: fixture.preview(supersedes="fixture-2026-11",
                                                               reason="belief_changed")),
                         "REASON_INVALID")
        self.assertEqual(refused(self, lambda: fixture.preview(reason="method_changed")), "REASON_INVALID")
        self.assertEqual(refused(self, lambda: fixture.preview(marks=[], supersedes="fixture-2026-11")),
                         "REASON_INVALID")
        # A belief change carries its marks, at the records layer too.
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        block = dict(record["supersedes"], stale_marks=[], changed_assumption_ids=[])
        self.assertEqual(refused(self, lambda: build_outlook(**block_fields(record), supersedes=block),
                                 OutlookError), "OUTLOOK_INVALID")

    def test_a_mark_free_reason_carries_no_mark_at_the_records_layer(self):
        # Rework round 2, finding R2-1: a record built directly with a mark-free reason
        # and a mark in its block is refused before the archive's write path.
        fixture = Fixture(self)
        mark = fixture.mark()
        fixture.write_method(method_version="fixture-method v2")
        record = reissue._vintage(fixture.preview(marks=[], supersedes="fixture-2026-11",
                                                  reason="method_changed"),
                                  issued_at=ISSUED_AT, confirmation_ref="c-1")
        for reason in ("method_changed", "inputs_refreshed"):
            block = dict(record["supersedes"], reason=reason,
                         stale_marks=[{"content_digest": mark["content_digest"],
                                       "assumption_id": BELIEF, "synthetic": False}],
                         changed_assumption_ids=[BELIEF])
            self.assertEqual(refused(self, lambda: build_outlook(**block_fields(record), supersedes=block),
                                     OutlookError), "OUTLOOK_INVALID")
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))

    def test_the_command_previews_then_issues_a_mark_free_reissue(self):
        fixture = Fixture(self, mark=False)
        arguments = ["--archive", str(fixture.archive.root), "--method-record", str(fixture.method_path),
                     "--cutoff", CUTOFF, "--issued-at", ISSUED_AT, "--outlook-id", NEW_ID,
                     "--issuer", ISSUER, "--supersedes", "fixture-2026-11"]
        no_reason = run_cli(*arguments)
        self.assertEqual(no_reason.returncode, 2)
        self.assertIn("--reason", no_reason.stderr)
        self.assertEqual(run_cli(*arguments, "--reason", "belief_changed").returncode, 2)
        shown = run_cli(*arguments, "--reason", "method_changed")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("reason: method_changed", shown.stdout)
        self.assertIn("changed assumptions: none", shown.stdout)
        self.assertIn("not confirmed: nothing issued", shown.stdout)
        self.assertEqual(fixture.archive.issue_ids(), ("fixture-2026-11",))
        reason_alone = run_cli(*arguments[:-2], "--reason", "method_changed")
        self.assertEqual(reason_alone.returncode, 2)
        issued = run_cli(*arguments, "--reason", "method_changed", "--confirm", "c-9")
        self.assertEqual(issued.returncode, 0, issued.stderr)
        stored = fixture.archive.outlook(NEW_ID)
        self.assertEqual((stored["supersedes"]["reason"], stored["supersedes"]["confirmation_ref"]),
                         ("method_changed", "c-9"))
        self.assertEqual(fixture.archive.verify()["problems"], [])


class AcceptanceExistingShapeKeptAndStdlibOnly(unittest.TestCase):
    """The first-issue shape is unchanged; the new modules stay offline and stdlib-only."""

    def test_a_first_issue_keeps_exactly_the_original_keys(self):
        fixture = Fixture(self, mark=False)
        self.assertEqual(set(fixture.predecessor), OUTLOOK_KEYS)
        self.assertNotIn("supersedes", OUTLOOK_KEYS)

    def test_a_supersedes_block_with_another_key_is_refused(self):
        fixture = Fixture(self)
        record = reissue._vintage(fixture.preview(), issued_at=ISSUED_AT, confirmation_ref="c-1")
        fields = {key: value for key, value in record.items()
                  if key not in ("schema_version", "kind", "content_digest", "supersedes")}
        block = dict(record["supersedes"], note="free text")
        self.assertEqual(refused(self, lambda: build_outlook(**fields, supersedes=block), OutlookError),
                         "OUTLOOK_INVALID")
        self.assertIs(validate_outlook(record), record)

    def imported_roots(self, path):
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_new_modules_import_only_the_standard_library(self):
        for path in (ROOT / "src/outlook/reissue.py", SCRIPT, Path(__file__)):
            roots = self.imported_roots(path)
            self.assertTrue(roots, path)
            for root in roots:
                self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                                f"{path.name} imports {root}")


#: The owner's two first-issue vintages, issued by hand before OUT-1.
REAL_FIRST_ISSUES = ("outlook-2026-11-system", "outlook-2026-11-system-v2")
#: The third vintage OUT-3 prepares; the orchestrator issues it into the real archive (OUT-3 decision g).
REAL_THIRD = "outlook-2026-11-system-v3"


@unittest.skipUnless(REAL_ARCHIVE.exists(),
                     ".local/outlook-archive is not linked into this checkout; the owner's real "
                     "archive cannot be read here")
class ZRealArchiveAcceptanceNothingWritten(unittest.TestCase):
    """Nothing is written into .local/outlook-archive; verify() reports no receipts and no problems.

    The class name sorts last in this module, so unittest runs it after every
    other test here; its byte check compares against the snapshot taken when the
    module was imported, before any test ran.

    OUT-3 moved the pins so they hold both before and after the orchestrator issues the
    real third vintage: 2 outlooks, or 3 with the third superseding the second
    (``method_changed``, no mark); the one demonstration mark either way (a mark-free
    re-issue writes no mark); the base's NOT_LATEST_VINTAGE refusal on the owner's archive is
    kept verbatim (it holds after the third vintage too: the newest vintage is then the third,
    still newer than the marked first), and a scratch archive of the same shape repeats it
    (:class:`NotLatestVintageOnTheRealArchiveShape`).
    """

    def test_verify_reports_two_outlooks_or_the_third_no_receipts_no_problems(self):
        report = OutlookArchive(REAL_ARCHIVE).verify()
        self.assertIn(report["outlooks"], (2, 3))
        self.assertEqual((report["receipts"], report["problems"]), (0, []))
        marks = dep.StaleMarks(REAL_ARCHIVE).verify(OutlookArchive(REAL_ARCHIVE))
        self.assertEqual(marks["problems"], [])
        ids = OutlookArchive(REAL_ARCHIVE).issue_ids()
        self.assertEqual(ids, REAL_FIRST_ISSUES if report["outlooks"] == 2 else REAL_FIRST_ISSUES + (REAL_THIRD,))
        if report["outlooks"] == 3:
            third = OutlookArchive(REAL_ARCHIVE).outlook(REAL_THIRD)
            second = OutlookArchive(REAL_ARCHIVE).outlook(REAL_FIRST_ISSUES[1])
            block = third["supersedes"]
            self.assertEqual((block["outlook_id"], block["outlook_digest"], block["reason"], block["stale_marks"]),
                             (second["outlook_id"], second["content_digest"], "method_changed", []))
            self.assertEqual(block["delta"]["previous_values_digest"], second["values_ref"]["sha256"])

    def test_no_file_of_the_real_archive_changed_during_this_module(self):
        self.assertEqual(snapshot(REAL_ARCHIVE), REAL_BEFORE)

    def test_the_real_archive_s_one_mark_cannot_start_a_reissue_today(self):
        # Read only: the one stored mark is a demonstration on the first vintage,
        # and the second vintage is newer, so the preview stops before reading any
        # method record or values file (OUT-3 needs a mark on the second vintage).
        archive = OutlookArchive(REAL_ARCHIVE)
        marks = dep.StaleMarks(REAL_ARCHIVE).marks()
        self.assertEqual([(mark["outlook_id"], mark["synthetic"]) for mark in marks],
                         [("outlook-2026-11-system", True)])
        self.assertEqual(refused(self, lambda: reissue.build_preview(
            archive, list(marks), ROOT / ".local" / "tmp" / "no-method.json",
            outlook_id="never-issued", issuer="nobody", cutoff=CUTOFF)), "NOT_LATEST_VINTAGE")

    def test_the_real_archive_s_one_mark_is_the_demonstration_on_the_first_vintage(self):
        # Read only: the one stored mark is a demonstration on the first vintage, before
        # and after the third vintage (the method_changed path writes no mark).
        marks = dep.StaleMarks(REAL_ARCHIVE).marks()
        self.assertEqual([(mark["outlook_id"], mark["synthetic"]) for mark in marks],
                         [("outlook-2026-11-system", True)])

    def test_the_real_vintages_carry_no_block_so_the_confirmation_rule_leaves_their_bytes(self):
        # Rework round 1, finding 3: the confirmation reference is required only on a
        # record that carries a supersedes block; neither first-issue vintage carries one,
        # so their stored bytes still validate and their digests still recompute. A
        # re-issued vintage (the third) carries one with a non-blank reference.
        for path in sorted((REAL_ARCHIVE / "outlooks").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["outlook_id"] in REAL_FIRST_ISSUES:
                self.assertNotIn("supersedes", record)
            else:
                self.assertTrue(record["supersedes"]["confirmation_ref"].strip())
            self.assertEqual(compute_content_digest(record), record["content_digest"])
            self.assertIs(validate_outlook(record), record)

    def test_the_real_vintages_still_read_in_the_first_issue_shape(self):
        archive = OutlookArchive(REAL_ARCHIVE)
        for outlook_id in archive.issue_ids():
            keys = set(archive.outlook(outlook_id))
            if outlook_id in REAL_FIRST_ISSUES:
                self.assertEqual(keys, OUTLOOK_KEYS)
            else:
                self.assertEqual(keys, OUTLOOK_KEYS | {"supersedes"})


class NotLatestVintageOnTheRealArchiveShape(unittest.TestCase):
    """The real archive's NOT_LATEST_VINTAGE case, moved to a scratch archive of its shape (OUT-3).

    Two first issues of one target, a demonstration mark on the first, the second
    newer: a preview from that mark stops at NOT_LATEST_VINTAGE before reading any
    method record or values file, as it did on the owner's archive.
    """

    def test_a_demonstration_mark_on_the_first_vintage_cannot_start_a_reissue(self):
        fixture = Fixture(self, mark=False)
        values = fixture.dir / "archive" / "values" / "second.json"
        write_values(values, NEW_VALUES)
        fixture.archive.issue(build_outlook(
            outlook_id="fixture-2026-11-v2", issued_at="2026-10-17T03:00:00Z",
            information_cutoff="2026-09-25T16:00:00Z", horizon=HORIZON, target_series_ref=SERIES,
            inputs=[{"name": "export.csv", "digest": sha256_of(fixture.input_path)}],
            assumption_ids=ASSUMPTIONS, model_version="fixture-method v1",
            values_ref={"path_hint": str(values), "sha256": sha256_of(values), "rows": len(HOURS)},
            issuer="OUT-3 test fixture", synthetic=False))
        mark_path = fixture.add_mark(BELIEF, synthetic=True)
        marks = dep.StaleMarks(fixture.archive.root).marks()
        self.assertEqual([(mark["outlook_id"], mark["synthetic"]) for mark in marks], [("fixture-2026-11", True)])
        self.assertEqual(refused(self, lambda: reissue.build_preview(
            fixture.archive, [fixture.mark(mark_path)], fixture.dir / "no-method.json",
            outlook_id="never-issued", issuer="nobody", cutoff=CUTOFF)), "NOT_LATEST_VINTAGE")


if __name__ == "__main__":
    unittest.main()
