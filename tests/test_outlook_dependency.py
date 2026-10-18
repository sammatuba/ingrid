"""ARCH-3: the dependency walk and stale marking, offline and stdlib-only.

Every case runs in a scratch directory over a fixture register and a fixture
archive; no network, clock, model or cloud call is made. The first acceptance
item carries named tests: changing an accepted assumption marks dependent
outlooks stale (:class:`AcceptedChange`) without erasing them
(:class:`NothingIsErased`). The second is checked against the issued first
outlook itself in :class:`FirstOutlook`, which skips unless the ignored runtime
archive and the PRICE-1 export are linked into ``.local/``. The stdlib-only
item is :class:`StdlibOnly`.
"""
import copy
import json
import re
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
from src.outlook.records import OutlookArchive, OutlookError, build_outlook

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
FIRST_ID = "outlook-2026-11-system"


def scratch_directory(prefix="arch3-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path.

    A review sandbox may mount no writable system temporary directory while the
    workspace itself stays writable; the fallback keeps these tests runnable
    there. It sits under the ignored ``.local/`` and is cleaned up the same way.
    """
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def assumption(**overrides):
    """One well-formed register record for the fixture register."""
    row = {
        "assumption_id": "rules:billing_month_clock",
        "proposition": "a billing month runs from the 26th to the 25th",
        "family": "rules",
        "layer": "official",
        "source_locator": [{"path": "docs/work/price-outlook/target-contract.md", "line": 14,
                            "quote": "billing month `bmonth` = 26th of the month before to the 25th"}],
        "valid_from": None,
        "valid_to": None,
        "state": "accepted",
        "owner": "project owner",
        "affected_code": ["src/price/series.py"],
        "falsifier": "a settlement statement whose label covers another date range",
        "last_checked_revision": None,
    }
    row.update(overrides)
    return row


def a_register(*rows):
    """A minimal valid envelope: the sources declare no counted rows."""
    return {
        "register_version": reg.REGISTER_VERSION,
        "sources": [{"family": "threshold", "path": reg.SOURCE_PATHS["threshold"], "rows": 0},
                    {"family": "composer", "path": reg.SOURCE_PATHS["composer"], "rows": 0}],
        "assumptions": list(rows) or [assumption()],
    }


def outlook_fields(**overrides):
    """The named fields of one well-formed outlook, with overrides applied."""
    fields = dict(
        outlook_id=FIRST_ID,
        issued_at="2026-10-16T00:00:00Z",
        information_cutoff="2026-08-25T16:00:00Z",
        horizon={"label": "month", "start": "2026-10-25T16:00:00Z", "end": "2026-11-25T16:00:00Z"},
        target_series_ref={"table": "grid_raw.ext_pmr_lwap_final", "column": "lwap",
                           "version": "final-bmonth-2026-11"},
        inputs=[{"name": "lwap_final_hourly.csv", "digest": DIGEST_A}],
        assumption_ids=["rules:billing_month_clock"],
        model_version="seasonal_average_billing_month price-2.1",
        values_ref={"path_hint": ".local/outlook-archive/values/outlook-2026-11-system.json",
                    "sha256": DIGEST_B, "rows": 744},
        issuer="Grid Nowcast executor seat (ARCH-3)",
        synthetic=False,
    )
    fields.update(overrides)
    return fields


def an_outlook(**overrides):
    return build_outlook(**outlook_fields(**overrides))


def a_mark(outlook, **overrides):
    fields = dict(assumption_id="rules:billing_month_clock", new_revision="016ae92",
                  outlook=outlook, assumption_state="accepted",
                  marked_at="2026-10-16T00:00:00Z", synthetic=False)
    fields.update(overrides)
    return dep.build_mark(**fields)


class Scratch:
    """A scratch archive plus the fixture register, built per test class."""

    def __init__(self, test):
        self.temp = scratch_directory()
        test.addCleanup(self.temp.cleanup)
        self.archive = OutlookArchive(self.temp.name)
        self.store = dep.StaleMarks(self.temp.name)
        self.register = a_register()

    def issue(self, **overrides):
        outlook = an_outlook(**overrides)
        self.archive.issue(outlook)
        return outlook

    def refused(self, case, build):
        with case.assertRaises(dep.DependencyError) as caught:
            build()
        return caught.exception.code


class Walk(unittest.TestCase):
    """outlook -> assumption_ids -> evidence refs."""

    def setUp(self):
        self.scratch = Scratch(self)

    def test_the_walk_resolves_each_assumption_to_its_evidence_refs(self):
        outlook = self.scratch.issue()
        walked = dep.walk(outlook, register_payload=self.scratch.register)
        self.assertEqual(walked["outlook_id"], FIRST_ID)
        self.assertEqual(walked["outlook_digest"], outlook["content_digest"])
        self.assertEqual(walked["unknown"], [])
        entry = walked["assumptions"][0]
        self.assertTrue(entry["known"])
        self.assertEqual(entry["family"], "rules")
        self.assertEqual(entry["layer"], "official")
        self.assertEqual(entry["state"], "accepted")
        self.assertEqual(entry["evidence"], [{"line": 14, "path": "docs/work/price-outlook/target-contract.md",
                                               "quote": "billing month `bmonth` = 26th of the month before to the 25th"}])
        self.assertEqual(entry["affected_code"], ["src/price/series.py"])

    def test_a_proposition_the_register_carries_travels_with_its_assumption(self):
        outlook = self.scratch.issue()
        walked = dep.walk(outlook, register_payload=self.scratch.register)
        self.assertEqual(walked["assumptions"][0]["proposition"],
                         "a billing month runs from the 26th to the 25th")

    def test_an_id_the_register_does_not_carry_is_reported_unknown(self):
        outlook = self.scratch.issue(assumption_ids=["rules:billing_month_clock", "rules:not_a_row"])
        walked = dep.walk(outlook, register_payload=self.scratch.register)
        self.assertEqual(walked["unknown"], ["rules:not_a_row"])
        self.assertEqual([item["known"] for item in walked["assumptions"]], [True, False])
        self.assertEqual(walked["assumptions"][1]["evidence"], [])

    def test_the_walk_reads_the_register_it_is_given_and_the_file_by_default(self):
        # The default path is the committed register; the payload form is the
        # one the tests drive, so the walk never depends on a mutable file here.
        walked = dep.walk(an_outlook(assumption_ids=["threshold:price_cap_php_mwh"]),
                          register_payload=reg.load_register(root=ROOT))
        self.assertEqual(walked["assumptions"][0]["family"], "threshold")
        self.assertTrue(walked["assumptions"][0]["evidence"])

    def test_assumption_of_and_evidence_refs_read_one_record(self):
        payload = reg.register(self.scratch.register)
        record = dep.assumption_of(payload, "rules:billing_month_clock")
        self.assertEqual(record["state"], "accepted")
        self.assertEqual(dep.evidence_refs(record)[0]["line"], 14)
        self.assertIsNone(dep.assumption_of(payload, "rules:absent"))

    def test_a_malformed_register_payload_is_refused_by_the_register_rules(self):
        # The register's own validator owns its refusals; the dependency layer
        # passes them through rather than inventing a code for the same gap.
        outlook = self.scratch.issue()
        payload = a_register()
        payload["assumptions"][0]["state"] = "not_a_state"
        with self.assertRaises(reg.RegisterError) as caught:
            dep.walk(outlook, register_payload=payload)
        self.assertEqual(caught.exception.code, "INVALID_RECORD")

    def test_walk_archive_walks_every_issued_outlook(self):
        self.scratch.issue()
        self.scratch.issue(outlook_id="outlook-2026-12-system", issued_at="2026-11-16T00:00:00Z",
                           information_cutoff="2026-11-15T16:00:00Z",
                           horizon={"label": "month", "start": "2026-11-25T16:00:00Z",
                                    "end": "2026-12-25T16:00:00Z"},
                           target_series_ref={"table": "grid_raw.ext_pmr_lwap_final", "column": "lwap",
                                              "version": "final-bmonth-2026-12"})
        walked = dep.walk_archive(self.scratch.archive, register_payload=self.scratch.register)
        self.assertEqual([entry["outlook_id"] for entry in walked],
                         [FIRST_ID, "outlook-2026-12-system"])

    def test_the_walk_seals_the_horizon_and_the_target_series(self):
        walked = dep.walk(self.scratch.issue(), register_payload=self.scratch.register)
        self.assertEqual(walked["horizon"], {"label": "month", "start": "2026-10-25T16:00:00Z",
                                             "end": "2026-11-25T16:00:00Z"})
        self.assertEqual(walked["target_series_ref"]["column"], "lwap")


class MarkContract(unittest.TestCase):
    """The StaleMark record: a closed key set, a sealed digest, the register vocabularies."""

    def setUp(self):
        self.scratch = Scratch(self)
        self.outlook = self.scratch.issue()

    def test_a_mark_is_sealed_over_every_field_except_the_digest(self):
        mark = a_mark(self.outlook)
        self.assertEqual(mark["content_digest"], compute_content_digest(mark))
        self.assertEqual(set(mark) - {"content_digest"},
                         {"schema_version", "kind", "assumption_id", "new_revision", "outlook_id",
                          "outlook_digest", "assumption_state", "marked_at", "synthetic"})
        self.assertEqual(mark["kind"], "StaleMark")
        self.assertEqual(mark["outlook_digest"], self.outlook["content_digest"])

    def test_the_mark_names_the_outlook_bytes_it_affects(self):
        mark = a_mark(self.outlook)
        self.assertEqual(mark["outlook_id"], self.outlook["outlook_id"])
        self.assertEqual(mark["outlook_digest"], self.outlook["content_digest"])

    def test_the_assumption_state_is_the_registers_own_vocabulary(self):
        for value in ("accepted", "deployed", "unverified", "contradicted", "test_fixture",
                      "designed_unrun"):
            self.assertEqual(a_mark(self.outlook, assumption_state=value)["assumption_state"], value)
        for value in ("", "ACCEPTED", "approved", "unknown"):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, assumption_state=value)),
                             "STALE_INVALID")

    def test_a_state_of_the_wrong_type_is_refused_as_a_mark(self):
        for value in ([], {}, 7, None, True):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, assumption_state=value)),
                             "STALE_INVALID")

    def test_the_new_revision_is_a_commit_id(self):
        for value in ("016ae92", "0" * 40):
            self.assertEqual(a_mark(self.outlook, new_revision=value)["new_revision"], value)
        for value in ("", "016ae9", "016AE92", "016ae9z", 7, None):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, new_revision=value)),
                             "STALE_INVALID")

    def test_the_ids_are_register_ids(self):
        for value in ("rules:billing_month_clock", "threshold:price_cap_php_mwh"):
            self.assertEqual(a_mark(self.outlook, assumption_id=value)["assumption_id"], value)
        for value in ("", "rules:a b", "rules:a/b", ":x", 7, None):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, assumption_id=value)),
                             "STALE_INVALID")

    def test_the_marked_at_instant_is_offset_bearing(self):
        self.assertEqual(a_mark(self.outlook, marked_at="2026-10-16T08:00:00+08:00")["marked_at"],
                         "2026-10-16T08:00:00+08:00")
        for value in ("", "2026-10-16", "2026-10-16T08:00:00", 7, None):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, marked_at=value)),
                             "STALE_INVALID")

    def test_the_synthetic_flag_is_a_boolean(self):
        for value in (True, False):
            self.assertEqual(a_mark(self.outlook, synthetic=value)["synthetic"], value)
        for value in (1, 0, "yes", None):
            self.assertEqual(self.scratch.refused(self, lambda: a_mark(self.outlook, synthetic=value)),
                             "STALE_INVALID")

    def test_a_mark_that_is_not_the_kind_is_refused(self):
        mark = a_mark(self.outlook)
        for change in ({"kind": "OutlookRecord"}, {"schema_version": "outlook.v2"},
                       {"extra": 1}, {"content_digest": "0" * 64}):
            tampered = dict(mark)
            tampered.update(change)
            self.assertEqual(self.scratch.refused(self, lambda: dep.validate_mark(tampered)),
                             "STALE_INVALID")
        # A non-mapping and an empty mapping are refusals of the contract, never
        # a TypeError or a KeyError out of it.
        for value in ([], {}, None, 7, "StaleMark"):
            self.assertEqual(self.scratch.refused(self, lambda: dep.validate_mark(value)),
                             "STALE_INVALID")

    def test_a_mark_built_against_an_invalid_outlook_is_refused(self):
        # The outlook validator owns that refusal, as it does for a receipt.
        broken = dict(self.outlook)
        broken["synthetic"] = "no"
        with self.assertRaises(OutlookError) as caught:
            dep.build_mark(assumption_id="rules:billing_month_clock", new_revision="016ae92",
                           outlook=broken, assumption_state="accepted",
                           marked_at="2026-10-16T00:00:00Z", synthetic=False)
        self.assertEqual(caught.exception.code, "OUTLOOK_INVALID")

    def test_the_message_table_is_closed_and_safe(self):
        for code, text in dep.MESSAGES.items():
            self.assertTrue(text)
            self.assertNotIn(code, text)
        self.assertEqual(dep.MESSAGES["STALE_DUPLICATE"],
                         "that change is already marked for that outlook revision")


class AcceptedChange(unittest.TestCase):
    """Acceptance 1: changing an accepted assumption marks dependent outlooks stale."""

    def setUp(self):
        self.scratch = Scratch(self)
        self.outlook = self.scratch.issue()

    def test_a_change_to_an_accepted_assumption_marks_the_outlook_stale(self):
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                                  marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(affected, (FIRST_ID,))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), (FIRST_ID,))
        marks = dep.marks_of(self.scratch.archive)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0]["assumption_state"], "accepted")
        self.assertEqual(marks[0]["new_revision"], "016ae92")
        self.assertEqual(marks[0]["outlook_digest"], self.outlook["content_digest"])
        self.assertFalse(marks[0]["synthetic"])

    def test_an_outlook_that_does_not_cite_the_assumption_is_not_marked(self):
        other = self.scratch.issue(outlook_id="outlook-other", assumption_ids=["rules:other_row"])
        affected = dep.mark_stale(self.scratch.archive, "rules:other_row", "016ae92",
                                  marked_at="2026-10-16T00:00:00Z",
                                  register_payload=a_register(assumption(assumption_id="rules:other_row")))
        self.assertEqual(affected, ("outlook-other",))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), ("outlook-other",))
        self.assertNotIn(self.outlook["content_digest"],
                         [mark["outlook_digest"] for mark in dep.marks_of(self.scratch.archive)])

    def test_a_change_no_outlook_cites_marks_nothing(self):
        payload = a_register(assumption(), assumption(assumption_id="rules:unused_row"))
        affected = dep.mark_stale(self.scratch.archive, "rules:unused_row", "016ae92",
                                  marked_at="2026-10-16T00:00:00Z", register_payload=payload)
        self.assertEqual(affected, ())
        self.assertEqual(dep.marks_of(self.scratch.archive), ())
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), ())

    def test_two_outlooks_that_cite_it_are_both_marked(self):
        self.scratch.issue(outlook_id="outlook-2026-12-system", issued_at="2026-11-16T00:00:00Z",
                           information_cutoff="2026-11-15T16:00:00Z",
                           horizon={"label": "month", "start": "2026-11-25T16:00:00Z",
                                    "end": "2026-12-25T16:00:00Z"})
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                                  marked_at="2026-12-01T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(affected, (FIRST_ID, "outlook-2026-12-system"))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), (FIRST_ID, "outlook-2026-12-system"))
        self.assertEqual(len(dep.marks_of(self.scratch.archive)), 2)

    def test_an_outlook_issued_after_the_marking_instant_is_left_alone(self):
        # An outlook issued after the change already cites the changed register:
        # it is not invalidated by the change, so the scan leaves it unmarked.
        future = self.scratch.issue(outlook_id="outlook-later", issued_at="2027-01-16T00:00:00Z",
                                    information_cutoff="2027-01-15T16:00:00Z",
                                    horizon={"label": "month", "start": "2027-01-25T16:00:00Z",
                                             "end": "2027-02-25T16:00:00Z"},
                                    assumption_ids=["rules:billing_month_clock"])
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                                  marked_at="2026-10-16T12:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(affected, (FIRST_ID,))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), (FIRST_ID,))
        self.assertNotIn(future["content_digest"],
                         [mark["outlook_digest"] for mark in dep.marks_of(self.scratch.archive)])

    def test_an_unknown_assumption_is_refused_and_nothing_is_marked(self):
        self.assertEqual(self.scratch.refused(self, lambda: dep.mark_stale(
            self.scratch.archive, "rules:not_a_row", "016ae92", marked_at="2026-10-16T00:00:00Z",
            register_payload=self.scratch.register)), "ASSUMPTION_UNKNOWN")
        self.assertEqual(dep.marks_of(self.scratch.archive), ())

    def test_the_same_change_for_the_same_outlook_is_refused_once(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(self.scratch.refused(self, lambda: dep.mark_stale(
            self.scratch.archive, "rules:billing_month_clock", "016ae92",
            marked_at="2026-10-16T08:00:00Z", register_payload=self.scratch.register)),
            "STALE_DUPLICATE")
        self.assertEqual(len(dep.marks_of(self.scratch.archive)), 1)

    def test_a_later_change_to_the_same_assumption_is_a_new_mark(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "beefbee",
                                  marked_at="2026-11-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(affected, (FIRST_ID,))
        # The store reads in file-name order, which is key order and carries no
        # meaning; the test asserts the content: both changes are stored, one
        # mark each, and the later one is a second record rather than an edit.
        marks = dep.marks_of(self.scratch.archive)
        self.assertEqual({mark["new_revision"] for mark in marks}, {"016ae92", "beefbee"})
        self.assertEqual(len(marks), 2)
        self.assertEqual({mark["outlook_digest"] for mark in marks}, {self.outlook["content_digest"]})

    def test_a_demonstration_mark_does_not_make_an_outlook_stale(self):
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                                  marked_at="2026-10-16T00:00:00Z",
                                  register_payload=self.scratch.register, synthetic=True)
        self.assertEqual(affected, (FIRST_ID,))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), ())
        self.assertEqual(dep.demonstration_outlooks(self.scratch.archive), (FIRST_ID,))
        self.assertTrue(dep.marks_of(self.scratch.archive)[0]["synthetic"])

    def test_a_real_mark_beside_a_demonstration_reads_as_stale(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z",
                       register_payload=self.scratch.register, synthetic=True)
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "beefbee",
                       marked_at="2026-11-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), (FIRST_ID,))
        self.assertEqual(dep.demonstration_outlooks(self.scratch.archive), ())
        self.assertEqual(len(dep.marks_of(self.scratch.archive)), 2)

    def test_a_real_mark_of_the_same_change_stands_beside_its_demonstration(self):
        # Provenance is part of a mark's identity: the demonstration of a change
        # must never refuse the real mark that change lands, for the identical
        # triple. Both records are stored, the outlook reads stale from the real
        # one, and the demonstration is still labelled.
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z",
                       register_payload=self.scratch.register, synthetic=True)
        affected = dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                                  marked_at="2026-10-16T00:00:00Z",
                                  register_payload=self.scratch.register)
        self.assertEqual(affected, (FIRST_ID,))
        self.assertEqual(dep.stale_outlooks(self.scratch.archive), (FIRST_ID,))
        self.assertEqual(dep.demonstration_outlooks(self.scratch.archive), ())
        marks = dep.marks_of(self.scratch.archive)
        self.assertEqual(sorted(mark["synthetic"] for mark in marks), [False, True])
        self.assertEqual({mark["new_revision"] for mark in marks}, {"016ae92"})
        self.assertEqual({mark["outlook_digest"] for mark in marks}, {self.outlook["content_digest"]})
        self.assertEqual(self.scratch.store.verify(self.scratch.archive), {"marks": 2, "problems": []})

    def test_each_provenance_of_one_change_is_still_written_once(self):
        # Separating the identities does not make the store writable twice: a
        # second mark of one change with one provenance is still refused.
        for synthetic in (True, False):
            dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                           marked_at="2026-10-16T00:00:00Z",
                           register_payload=self.scratch.register, synthetic=synthetic)
        for synthetic in (True, False):
            self.assertEqual(self.scratch.refused(self, lambda: dep.mark_stale(
                self.scratch.archive, "rules:billing_month_clock", "016ae92",
                marked_at="2026-10-16T08:00:00Z", register_payload=self.scratch.register,
                synthetic=synthetic)), "STALE_DUPLICATE")
        self.assertEqual(len(dep.marks_of(self.scratch.archive)), 2)


class NothingIsErased(unittest.TestCase):
    """Acceptance 1, second half: the marking erases nothing."""

    def setUp(self):
        self.scratch = Scratch(self)
        self.outlook = self.scratch.issue()
        self.path = self.scratch.archive.outlooks_dir / (FIRST_ID + ".json")
        self.before = self.path.read_bytes()

    def test_the_outlook_bytes_and_digest_are_unchanged_by_the_mark(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(self.path.read_bytes(), self.before)
        stored = self.scratch.archive.outlook(FIRST_ID)
        self.assertEqual(stored, self.outlook)
        self.assertEqual(stored["content_digest"], self.outlook["content_digest"])

    def test_the_marked_outlook_still_validates_and_still_carries_its_assumptions(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        stored = self.scratch.archive.outlook(FIRST_ID)
        self.assertEqual(stored["assumption_ids"], ["rules:billing_month_clock"])
        self.assertEqual(self.scratch.archive.verify(), {"outlooks": 1, "receipts": 0,
                                                         "attributions": 0, "problems": []})

    def test_the_mark_is_stored_beside_the_outlook_not_on_it(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        self.assertEqual(sorted(path.name for path in self.scratch.archive.outlooks_dir.glob("*.json")),
                         [FIRST_ID + ".json"])
        self.assertEqual(len(list(self.scratch.store.marks_dir.glob("*.json"))), 1)
        self.assertEqual(self.scratch.store.verify(self.scratch.archive), {"marks": 1, "problems": []})

    def test_a_store_with_no_write_path_reports_io_rather_than_raising(self):
        mark = a_mark(self.outlook)
        blocked = Path(self.scratch.temp.name) / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        self.assertEqual(self.scratch.refused(self, lambda: dep.StaleMarks(blocked).append(mark)),
                         "DEPENDENCY_IO")

    def test_a_tampered_mark_file_is_reported_by_the_store(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        path = next(self.scratch.store.marks_dir.glob("*.json"))
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('"016ae92"', '"beefbee"'), encoding="utf-8")
        report = self.scratch.store.verify(self.scratch.archive)
        self.assertEqual(report["marks"], 0)
        self.assertEqual(len(report["problems"]), 1)
        self.assertTrue(report["problems"][0].endswith("STALE_INVALID"))

    def test_a_mark_whose_outlook_is_gone_is_reported(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        (self.scratch.archive.outlooks_dir / (FIRST_ID + ".json")).unlink()
        report = self.scratch.store.verify(self.scratch.archive)
        self.assertEqual(report["marks"], 1)
        self.assertEqual(report["problems"], [next(self.scratch.store.marks_dir.glob("*.json")).name
                                              + ": OUTLOOK_UNKNOWN"])


class MarksReadBack(unittest.TestCase):
    def setUp(self):
        self.scratch = Scratch(self)
        self.outlook = self.scratch.issue()

    def test_marks_can_be_read_for_one_outlook(self):
        other = self.scratch.issue(outlook_id="outlook-other",
                                   assumption_ids=["rules:other_row"])
        payload = a_register(assumption(), assumption(assumption_id="rules:other_row"))
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=payload)
        dep.mark_stale(self.scratch.archive, "rules:other_row", "beefbee",
                       marked_at="2026-11-16T00:00:00Z", register_payload=payload)
        self.assertEqual(len(dep.marks_of(self.scratch.archive)), 2)
        self.assertEqual([mark["assumption_id"] for mark in dep.marks_of(self.scratch.archive, FIRST_ID)],
                         ["rules:billing_month_clock"])
        self.assertEqual([mark["assumption_id"] for mark in dep.marks_of(self.scratch.archive, "outlook-other")],
                         ["rules:other_row"])

    def test_the_walk_of_a_stale_outlook_carries_its_marks(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-16T00:00:00Z", register_payload=self.scratch.register)
        walked = dep.walk(self.scratch.archive.outlook(FIRST_ID), register_payload=self.scratch.register,
                          marks=dep.marks_of(self.scratch.archive))
        self.assertEqual(len(walked["stale"]), 1)
        self.assertEqual(walked["stale"][0]["assumption_id"], "rules:billing_month_clock")
        self.assertEqual(walked["stale"][0]["assumption_state"], "accepted")

    def test_a_mark_for_other_bytes_of_the_same_id_is_not_the_walk_s_stale_mark(self):
        mark = a_mark(self.outlook, assumption_id="rules:billing_month_clock")
        walked = dep.walk(self.scratch.archive.outlook(FIRST_ID), register_payload=self.scratch.register,
                          marks=[dict(mark, outlook_digest="0" * 64)])
        self.assertEqual(walked["stale"], [])

    def test_a_missing_mark_file_is_reported(self):
        path = self.scratch.store.marks_dir / ("f" * 64 + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"kind": "StaleMark"}), encoding="utf-8")
        report = self.scratch.store.verify(self.scratch.archive)
        self.assertEqual(report["marks"], 0)
        self.assertEqual(report["problems"], [path.name + ": STALE_INVALID"])


class DirectionShare(unittest.TestCase):
    """The ARCH-3 direction check: the share of assumptions changed between monthly outlooks."""

    def setUp(self):
        self.scratch = Scratch(self)
        self.first = self.scratch.issue()
        self.second = self.scratch.issue(
            outlook_id="outlook-2026-12-system", issued_at="2026-11-16T00:00:00Z",
            information_cutoff="2026-11-15T16:00:00Z",
            horizon={"label": "month", "start": "2026-11-25T16:00:00Z", "end": "2026-12-25T16:00:00Z"},
            target_series_ref={"table": "grid_raw.ext_pmr_lwap_final", "column": "lwap",
                               "version": "final-bmonth-2026-12"})

    def test_no_change_between_the_two_issues_is_a_zero_share(self):
        result = dep.direction_share(self.first, self.second, dep.marks_of(self.scratch.archive))
        self.assertEqual(result["union"], ["rules:billing_month_clock"])
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["share"], 0.0)

    def test_a_real_change_between_the_two_issues_is_counted(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "beefbee",
                       marked_at="2026-11-01T00:00:00Z", register_payload=self.scratch.register)
        result = dep.direction_share(self.first, self.second, dep.marks_of(self.scratch.archive))
        self.assertEqual(result["changed"], ["rules:billing_month_clock"])
        self.assertEqual(result["union_count"], 1)
        self.assertEqual(result["share"], 1.0)

    def test_a_change_before_the_first_issue_or_after_the_second_is_not_counted(self):
        first = self.scratch.issue(outlook_id="outlook-2026-10-system", issued_at="2026-10-20T00:00:00Z",
                                   information_cutoff="2026-10-19T16:00:00Z",
                                   horizon={"label": "month", "start": "2026-10-25T16:00:00Z",
                                            "end": "2026-11-25T16:00:00Z"})
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "016ae92",
                       marked_at="2026-10-19T00:00:00Z", register_payload=self.scratch.register)
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "beefbee",
                       marked_at="2026-12-01T00:00:00Z", register_payload=self.scratch.register)
        result = dep.direction_share(first, self.second, dep.marks_of(self.scratch.archive))
        self.assertEqual(result["changed"], [])

    def test_a_demonstration_change_never_moves_the_check(self):
        dep.mark_stale(self.scratch.archive, "rules:billing_month_clock", "beefbee",
                       marked_at="2026-11-01T00:00:00Z", register_payload=self.scratch.register,
                       synthetic=True)
        result = dep.direction_share(self.first, self.second, dep.marks_of(self.scratch.archive))
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["share"], 0.0)

    def test_the_union_is_every_assumption_either_outlook_cites(self):
        second = self.scratch.issue(
            outlook_id="outlook-2026-12b", issued_at="2026-11-16T00:00:00Z",
            information_cutoff="2026-11-15T16:00:00Z",
            horizon={"label": "month", "start": "2026-11-25T16:00:00Z", "end": "2026-12-25T16:00:00Z"},
            assumption_ids=["rules:billing_month_clock", "rules:other_row"])
        result = dep.direction_share(self.first, second,
                                     register_payload=self.scratch.register, marks=())
        self.assertEqual(result["union"], ["rules:billing_month_clock", "rules:other_row"])
        self.assertEqual(result["union_count"], 2)

    def test_two_non_monthly_outlooks_are_refused(self):
        day = an_outlook(outlook_id="outlook-day", horizon={"label": "day",
                                                            "start": "2026-10-25T16:00:00Z",
                                                            "end": "2026-10-26T16:00:00Z"})
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(day, self.second)),
                         "NOT_MONTHLY")

    def test_two_different_target_series_are_refused(self):
        other = an_outlook(outlook_id="outlook-other-series",
                           target_series_ref={"table": "grid_raw.ext_pmr_settlement_prices",
                                              "column": "lmp", "version": "final-bmonth-2026-12"})
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(self.first, other)),
                         "NOT_MONTHLY")

    def test_an_unordered_pair_is_refused(self):
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(self.second, self.first)),
                         "NOT_ORDERED")

    def test_an_outlook_compared_with_itself_is_refused(self):
        # One outlook twice is not a monthly pair; the check refuses it rather
        # than reporting a share no month of desk work produced.
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(self.first, self.first)),
                         "NOT_MONTHLY")

    def test_two_outlooks_issued_at_the_same_instant_are_refused(self):
        # Equal issue instants leave no interval to measure; the pair is refused
        # in both directions rather than answered with the interval's emptiness.
        twin = self.scratch.issue(outlook_id="outlook-2026-11-twin",
                                  issued_at=self.first["issued_at"],
                                  information_cutoff=self.first["information_cutoff"],
                                  horizon=self.first["horizon"],
                                  target_series_ref=self.first["target_series_ref"])
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(self.first, twin)),
                         "NOT_ORDERED")
        self.assertEqual(self.scratch.refused(self, lambda: dep.direction_share(twin, self.first)),
                         "NOT_ORDERED")


class FirstOutlook(unittest.TestCase):
    """Acceptance 2: the first outlook cites PRICE-2's inputs by digest.

    The issued record and its values live in the ignored runtime archive
    (``.local/outlook-archive/``) and the PRICE-1 export in ``.local/price/``;
    neither enters Git, so these cases skip when they are not linked. What is
    checked here is the record as issued: its five assumptions resolve against
    the committed register, its input digest is the export's own bytes, and its
    packet is the record's text.
    """

    ARCHIVE = ROOT / ".local" / "outlook-archive"
    EXPORT = ROOT / ".local" / "price" / "lwap_final_hourly.csv"
    PACKET = ROOT / "docs/work/outlook-archive/first-outlook.md"

    @classmethod
    def setUpClass(cls):
        if not (cls.ARCHIVE / "outlooks" / (FIRST_ID + ".json")).exists():
            raise unittest.SkipTest("the first outlook is not issued under .local/outlook-archive")
        cls.archive = OutlookArchive(cls.ARCHIVE)
        cls.record = cls.archive.outlook(FIRST_ID)
        cls.payload = reg.load_register(root=ROOT)

    def test_the_record_cites_the_price_2_export_by_digest(self):
        """The first vintage cites the export it was issued from, by the digest its packet records.

        After a data refresh the export under ``.local/price`` is a newer file; the issued record
        is never edited, so its digest stays the one of 2026-10-16. The newest issued vintage of the
        same series must then cite the export as it is now (a refresh issues a new vintage, it does
        not rewrite the old one).
        """
        if not self.EXPORT.exists():
            raise unittest.SkipTest("the PRICE-1 export is not present under .local/price")
        from src.price.series import digest_file
        self.assertEqual([item["name"] for item in self.record["inputs"]], ["lwap_final_hourly.csv"])
        cited = self.record["inputs"][0]["digest"]
        self.assertIn(cited[:8], self.PACKET.read_text(encoding="utf-8"))
        current = digest_file(self.EXPORT)
        newest = max((self.archive.outlook(i) for i in self.archive.issue_ids()
                      if i.startswith(FIRST_ID)), key=lambda r: r["issued_at"])
        self.assertEqual(newest["inputs"][0]["digest"], current,
                         "the newest issued vintage must cite the export as it is now")

    def test_every_assumption_the_record_cites_is_a_register_row(self):
        walked = dep.walk(self.record, register_payload=self.payload)
        self.assertEqual(walked["unknown"], [])
        self.assertEqual(len(walked["assumptions"]), 5)
        for entry in walked["assumptions"]:
            with self.subTest(entry["assumption_id"]):
                self.assertTrue(entry["known"])
                self.assertTrue(entry["evidence"])
        states = {entry["assumption_id"]: entry["state"] for entry in walked["assumptions"]}
        self.assertEqual(states["rules:billing_month_clock"], "accepted")
        self.assertEqual(states["price:final_settlement_lmp"], "accepted")

    def test_the_record_is_a_monthly_outlook_that_runs_forward_from_its_issue(self):
        self.assertEqual(self.record["horizon"]["label"], "month")
        self.assertLessEqual(self.record["issued_at"], self.record["horizon"]["start"])
        self.assertLessEqual(self.record["information_cutoff"], self.record["issued_at"])

    def test_the_packet_carries_the_record_as_stored(self):
        text = self.PACKET.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
        stored = [json.loads(block) for block in blocks
                  if json.loads(block).get("kind") == "OutlookRecord"]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0], self.record)

    def test_the_archive_and_its_marks_verify_clean(self):
        verified = self.archive.verify()
        self.assertEqual(verified["problems"], [])
        self.assertEqual(verified["receipts"], 0)
        self.assertGreaterEqual(verified["outlooks"], 1)  # later vintages are issued beside the first, never over it
        self.assertEqual(dep.StaleMarks(self.ARCHIVE).verify(self.archive)["problems"], [])

    def test_the_first_outlook_is_not_stale_and_any_mark_on_it_is_labelled(self):
        self.assertEqual(dep.stale_outlooks(self.archive), ())
        for mark in dep.marks_of(self.archive, FIRST_ID):
            self.assertTrue(mark["synthetic"], "a real change has not happened yet")


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

    def test_the_dependency_module_imports_only_the_standard_library_and_this_repository(self):
        path = ROOT / "src/outlook/dependency.py"
        roots = self.imported_roots(path)
        self.assertTrue(roots)
        for root in roots:
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}
                            or root.startswith("."), f"dependency.py imports {root}")

    def test_the_dependency_module_reaches_only_the_two_outlook_modules(self):
        text = (ROOT / "src/outlook/dependency.py").read_text(encoding="utf-8")
        reached = set(re.findall(r"^from (src\.[A-Za-z0-9_.]+) import", text, re.M))
        self.assertLessEqual(reached, {"src.contracts.jsonutil", "src.outlook", "src.outlook.records"})

    def test_the_test_module_itself_stays_offline(self):
        for root in self.imported_roots(Path(__file__)):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)


if __name__ == "__main__":
    unittest.main()
