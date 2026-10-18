"""BOOK-2: the uncovered volume of the synthetic book per account, node and hour, offline.

Acceptance lines proved here: the uncovered volume of one Visayas account for one hour is one call and
one test with the arithmetic written out; a window reaching outside the profile's day is refused; a
cutoff before a contract's term start is refused; the covering contracts are named; the volume is never
negative; every figure carries the synthetic label; the modules import nothing from the web layer.
"""
import ast
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.book import exposure as ex  # noqa: E402
from src.book.records import LABEL, BookError, seal  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "book" / "book-v1.json"
MODULES = (ROOT / "src" / "book" / "exposure.py", ROOT / "src" / "book" / "impact.py")
#: The web layer and the network: nothing under src/book may import them.
FORBIDDEN = ("src.api", "src.grid", "src.workspace", "src.judgment", "src.alerts", "src.demo", "src.hosted",
             "urllib", "http", "socket", "requests", "ssl", "ftplib", "smtplib")
FIGURE_SUFFIXES = ("_mw", "_mwh", "_php")


def book():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def figure_dicts(node, inherited=False):
    """Every dict that holds a numeric figure, with whether it or its parent row carries the label."""
    if isinstance(node, dict):
        own = node.get("synthetic") is True and node.get("label", "").startswith(LABEL)
        if any(k.endswith(FIGURE_SUFFIXES) and type(v) in (int, float) for k, v in node.items()):
            yield node, own or inherited
        for key, value in node.items():
            # A covering contract and a band row are inputs quoted inside a labelled row.
            yield from figure_dicts(value, own if key in ("covering_contracts", "band_php_mwh") else False)
    elif isinstance(node, list):
        for item in node:
            yield from figure_dicts(item, inherited)


class OneAccountOneHour(unittest.TestCase):
    """ACC-VIS03 (Tangub Seafood Cooperative, Visayas) has one node, NODE-VIS03."""

    def test_the_uncovered_volume_of_one_visayas_account_for_one_hour_is_one_call(self):
        answer = ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2026-10-14")
        # The arithmetic, written out from the fixture:
        #   demand of NODE-VIS03 at clock hour 13 (profile mw_by_hour[13])      6.635 MW
        #   CT-VIS03-1, fixed price, all 24 hours, term 2026-01-01..2027-12-31   2.0 MW
        #   CT-VIS03-2, time-of-use block, hours 8..21, same term                1.5 MW
        #   contracted = 2.0 + 1.5                                               3.5 MW
        #   uncovered  = max(0, 6.635 - 3.5) x 1 hour                            3.135 MWh
        self.assertEqual(answer["account_id"], "ACC-VIS03")
        self.assertEqual(answer["region"], "Visayas")
        self.assertEqual(answer["nodes"], ["NODE-VIS03"])
        self.assertEqual(answer["demand_mwh"], 6.635)
        self.assertEqual(answer["covered_mwh"], 3.5)
        self.assertEqual(answer["uncovered_mwh"], 3.135)
        self.assertEqual(answer["uncovered_mwh"], round(6.635 - (2.0 + 1.5), 3))
        [row] = answer["rows"]
        self.assertEqual(row["hour_start"], "2026-10-19T13:00:00")
        self.assertEqual(row["demand_mw"], 6.635)
        self.assertEqual(row["contracted_mw"], 3.5)
        self.assertEqual(row["uncovered_mwh"], 3.135)
        self.assertEqual([c["id"] for c in row["covering_contracts"]], ["CT-VIS03-1", "CT-VIS03-2"])
        self.assertTrue(answer["synthetic"] and row["synthetic"])
        self.assertEqual(answer["label"], LABEL)
        self.assertEqual(row["label"], LABEL)

    def test_an_off_peak_hour_drops_the_peak_block(self):
        # Hour 3 is outside CT-VIS03-2's hours 8..21: 6.009 - 2.0 = 4.009 MWh, covered by CT-VIS03-1 only.
        answer = ex.account_hour(book(), "ACC-VIS03", "2026-10-19T03:00", "2026-10-14")
        [row] = answer["rows"]
        self.assertEqual(row["demand_mw"], 6.009)
        self.assertEqual([c["id"] for c in row["covering_contracts"]], ["CT-VIS03-1"])
        self.assertEqual(answer["uncovered_mwh"], 4.009)

    def test_an_account_with_two_nodes_sums_its_rows(self):
        # ACC-VIS01 holds NODE-VIS01 and NODE-VIS04, each with one fixed contract over all hours.
        #   NODE-VIS01: 19.274 - 9.5  = 9.774
        #   NODE-VIS04: 29.278 - 13.0 = 16.278
        #   account:    9.774 + 16.278 = 26.052 MWh
        answer = ex.account_hour(book(), "ACC-VIS01", "2026-10-19T13:00", "2026-10-14")
        self.assertEqual([r["uncovered_mwh"] for r in answer["rows"]], [9.774, 16.278])
        self.assertEqual(answer["uncovered_mwh"], 26.052)

    def test_an_offset_instant_names_the_same_local_hour(self):
        local = ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2026-10-14")
        utc = ex.account_hour(book(), "ACC-VIS03", "2026-10-19T05:00:00Z", "2026-10-14")
        self.assertEqual(local["rows"], utc["rows"])


class Windows(unittest.TestCase):
    def test_a_window_reaching_into_the_next_day_is_refused(self):
        with self.assertRaises(ex.ExposureError) as caught:
            ex.Window.between("2026-10-19T23:00", "2026-10-20T01:00")
        self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_PROFILE")

    def test_a_window_past_hour_24_is_refused(self):
        for start, end in ((22, 25), (-1, 3), (24, 25)):
            with self.subTest(start=start, end=end), self.assertRaises(ex.ExposureError) as caught:
                ex.Window(date(2026, 10, 19), start, end)
            self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_PROFILE")

    def test_a_window_that_crosses_a_midnight_inside_a_day_is_refused(self):
        # The orchestrator's decision at review: several whole days are allowed, part-days across a
        # midnight are not.
        for start, end in (("2026-10-19T13:00", "2026-10-20T15:00"), ("2026-10-19T00:00", "2026-10-20T15:00"),
                           ("2026-10-19T13:00", "2026-10-21T00:00")):
            with self.subTest(start=start, end=end), self.assertRaises(ex.ExposureError) as caught:
                ex.Window.between(start, end)
            self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_PROFILE")
        with self.assertRaises(ex.ExposureError) as caught:
            ex.Window(date(2026, 10, 19), 13, 15, days=2)
        self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_PROFILE")
        for days in (0, -1, True):
            with self.subTest(days=days), self.assertRaises(ex.ExposureError) as caught:
                ex.Window(date(2026, 10, 19), 0, 24, days=days)
            self.assertEqual(caught.exception.code, "WINDOW_INVALID")

    def test_a_window_of_whole_days_repeats_the_profile_per_day(self):
        window = ex.Window.between("2026-10-19T00:00", "2026-10-21T00:00")
        self.assertEqual((window.day, window.start_hour, window.end_hour, window.days),
                         (date(2026, 10, 19), 0, 24, 2))
        self.assertEqual(len(window.hours), 48)
        self.assertEqual(window.hours[24].isoformat(), "2026-10-20T00:00:00")
        two = ex.exposure(book(), window, "2026-10-14", accounts=["ACC-VIS03"])
        one = ex.exposure(book(), ex.Window(date(2026, 10, 19), 0, 24), "2026-10-14", accounts=["ACC-VIS03"])
        self.assertEqual(len(two["rows"]), 48)
        self.assertEqual([r["uncovered_mwh"] for r in two["rows"][24:]], [r["uncovered_mwh"] for r in one["rows"]])
        # Both days are inside every term, so the two-day total is twice the one-day total.
        self.assertEqual(two["accounts"][0]["uncovered_mwh"], round(2 * one["accounts"][0]["uncovered_mwh"], 3))
        self.assertEqual(two["window"]["days"], 2)
        self.assertEqual(two["window"]["last_day"], "2026-10-20")

    def test_each_day_of_a_window_checks_the_terms_on_its_own_date(self):
        data = book()
        for contract in data["contracts"]:
            if contract["id"] == "CT-VIS03-2":
                contract["term_end"] = "2026-10-19"
        seal(data)
        record = ex.exposure(data, ex.Window(date(2026, 10, 19), 0, 24, days=2), "2026-10-14",
                             accounts=["ACC-VIS03"])
        day1 = next(r for r in record["rows"] if r["hour_start"] == "2026-10-19T13:00:00")
        day2 = next(r for r in record["rows"] if r["hour_start"] == "2026-10-20T13:00:00")
        self.assertEqual([c["id"] for c in day1["covering_contracts"]], ["CT-VIS03-1", "CT-VIS03-2"])
        self.assertEqual([c["id"] for c in day2["covering_contracts"]], ["CT-VIS03-1"])
        self.assertEqual((day1["uncovered_mwh"], day2["uncovered_mwh"]), (3.135, round(6.635 - 2.0, 3)))

    def test_the_next_midnight_closes_the_day(self):
        window = ex.Window.between("2026-10-19T20:00", "2026-10-20T00:00")
        self.assertEqual((window.day, window.start_hour, window.end_hour), (date(2026, 10, 19), 20, 24))
        self.assertEqual(window.clock_hours, (20, 21, 22, 23))

    def test_empty_backwards_and_unaligned_windows_are_refused(self):
        for start, end in (("2026-10-19T13:00", "2026-10-19T13:00"), ("2026-10-19T15:00", "2026-10-19T13:00"),
                           ("2026-10-19T13:30", "2026-10-19T15:00"), ("not an hour", "2026-10-19T15:00")):
            with self.subTest(start=start, end=end), self.assertRaises(ex.ExposureError) as caught:
                ex.Window.between(start, end)
            self.assertEqual(caught.exception.code, "WINDOW_INVALID")

    def test_the_error_is_a_book_error(self):
        self.assertTrue(issubclass(ex.ExposureError, BookError))


class Cutoffs(unittest.TestCase):
    def test_a_cutoff_before_a_contracts_term_start_is_refused(self):
        # CT-VIS03-1 and CT-VIS03-2 start 2026-01-01.
        with self.assertRaises(ex.ExposureError) as caught:
            ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2025-12-31")
        self.assertEqual(caught.exception.code, "CUTOFF_BEFORE_TERM_START")
        self.assertIn("CT-VIS03-1", str(caught.exception))

    def test_the_term_start_day_itself_is_accepted(self):
        answer = ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2026-01-01")
        self.assertEqual(answer["uncovered_mwh"], 3.135)

    def test_an_instant_cutoff_is_read_as_the_local_date(self):
        # 2025-12-31T16:00Z is 2026-01-01 00:00 in Manila, the term start: accepted.
        self.assertEqual(ex.cutoff_date("2025-12-31T16:00:00Z"), date(2026, 1, 1))
        with self.assertRaises(ex.ExposureError) as caught:
            ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2025-12-31T15:59:00Z")
        self.assertEqual(caught.exception.code, "CUTOFF_BEFORE_TERM_START")

    def test_a_malformed_cutoff_is_refused(self):
        for cutoff in ("yesterday", 20261014, None):
            with self.subTest(cutoff=cutoff), self.assertRaises(ex.ExposureError) as caught:
                ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", cutoff)
            self.assertEqual(caught.exception.code, "CUTOFF_INVALID")

    def test_only_contracts_in_scope_are_checked(self):
        # CT-VIS04-1 starts 2026-07-01; a cutoff of 2026-06-30 refuses ACC-VIS01 but not ACC-VIS03.
        ex.account_hour(book(), "ACC-VIS03", "2026-10-19T13:00", "2026-06-30")
        with self.assertRaises(ex.ExposureError) as caught:
            ex.account_hour(book(), "ACC-VIS01", "2026-10-19T13:00", "2026-06-30")
        self.assertIn("CT-VIS04-1", str(caught.exception))


class Coverage(unittest.TestCase):
    def test_a_window_day_outside_a_term_drops_that_contract(self):
        data = book()
        for contract in data["contracts"]:
            if contract["id"] == "CT-VIS03-2":
                contract["term_end"] = "2026-10-18"
        seal(data)
        answer = ex.account_hour(data, "ACC-VIS03", "2026-10-19T13:00", "2026-10-14")
        self.assertEqual([c["id"] for c in answer["rows"][0]["covering_contracts"]], ["CT-VIS03-1"])
        self.assertEqual(answer["uncovered_mwh"], round(6.635 - 2.0, 3))

    def test_the_volume_is_never_negative(self):
        data = book()
        for contract in data["contracts"]:
            if contract["id"] == "CT-VIS03-1":
                contract["mw"] = 9.0
        seal(data)
        [row] = ex.account_hour(data, "ACC-VIS03", "2026-10-19T13:00", "2026-10-14")["rows"]
        self.assertEqual(row["uncovered_mwh"], 0.0)
        # 9.0 + 1.5 - 6.635 = 3.865 MW above demand, reported and not netted.
        self.assertEqual(row["over_contracted_mw"], 3.865)

    def test_no_row_of_the_whole_book_is_negative_and_every_row_names_its_contracts(self):
        record = ex.exposure(book(), ex.Window(date(2026, 10, 19), 0, 24), "2026-10-14")
        self.assertEqual(len(record["rows"]), 14 * 24)
        for row in record["rows"]:
            self.assertGreaterEqual(row["uncovered_mwh"], 0.0)
            self.assertTrue(row["covering_contracts"], row["node_id"])
            expected = round(max(0.0, row["demand_mw"] - sum(c["mw"] for c in row["covering_contracts"])), 3)
            self.assertEqual(row["uncovered_mwh"], expected)

    def test_a_tampered_book_is_refused_before_any_row(self):
        data = book()
        data["profiles"][0]["mw_by_hour"][13] = 99.0
        with self.assertRaises(BookError) as caught:
            ex.exposure(data, ex.Window(date(2026, 10, 19), 13, 14), "2026-10-14")
        self.assertEqual(caught.exception.code, "BOOK_INVALID")

    def test_unknown_ids_and_regions_are_refused(self):
        window = ex.Window(date(2026, 10, 19), 13, 14)
        for kwargs, code in (({"accounts": ["ACC-NOPE"]}, "UNKNOWN_ACCOUNT"), ({"nodes": ["NODE-NOPE"]}, "UNKNOWN_NODE"),
                             ({"region": "Palawan"}, "UNKNOWN_REGION"),
                             ({"accounts": ["ACC-VIS03"], "region": "Luzon"}, "EMPTY_SCOPE")):
            with self.subTest(kwargs=kwargs), self.assertRaises(ex.ExposureError) as caught:
                ex.exposure(book(), window, "2026-10-14", **kwargs)
            self.assertEqual(caught.exception.code, code)


class AffectedPart(unittest.TestCase):
    def test_the_affected_part_of_visayas_for_a_window(self):
        window = ex.Window.between("2026-10-19T13:00", "2026-10-19T15:00")
        part = ex.affected_part(book(), "CVIS", window, "2026-10-14")
        self.assertEqual(part["region"], "Visayas")
        self.assertEqual(part["accounts"], ["ACC-VIS01", "ACC-VIS02", "ACC-VIS03"])
        self.assertEqual(part["nodes"], ["NODE-VIS01", "NODE-VIS02", "NODE-VIS03", "NODE-VIS04", "NODE-VIS05"])
        # The off-peak blocks CT-VIS02-2 and CT-VIS05-2 do not cover 13:00 to 15:00.
        self.assertEqual(part["contracts"], ["CT-VIS01-1", "CT-VIS02-1", "CT-VIS03-1", "CT-VIS03-2", "CT-VIS04-1",
                                             "CT-VIS05-1"])
        record = part["exposure"]
        self.assertEqual({r["region"] for r in record["rows"]}, {"Visayas"})
        self.assertEqual(len(record["rows"]), 5 * 2)
        # ACC-VIS03 over hours 13 and 14: (6.635 - 3.5) + (7.169 - 3.5) = 3.135 + 3.669 = 6.804 MWh.
        vis03 = next(a for a in record["accounts"] if a["account_id"] == "ACC-VIS03")
        self.assertEqual(vis03["uncovered_mwh"], 6.804)
        self.assertEqual(record["totals"]["uncovered_mwh"],
                         round(sum(a["uncovered_mwh"] for a in record["accounts"]), 3))
        self.assertEqual(ex.affected_part(book(), "Visayas", window, "2026-10-14"), part)


class Labels(unittest.TestCase):
    def test_every_figure_carries_the_synthetic_label(self):
        window = ex.Window(date(2026, 10, 19), 0, 24)
        record = ex.exposure(book(), window, "2026-10-14")
        self.assertTrue(record["synthetic"])
        self.assertEqual(record["label"], LABEL)
        found = list(figure_dicts(record))
        self.assertGreater(len(found), 14 * 24)
        for node, labelled in found:
            self.assertTrue(labelled, sorted(node))
        self.assertIn("method demonstration", record["units"]["uncovered_mwh"])

    def test_the_record_names_the_book_by_digest(self):
        record = ex.exposure(book(), ex.Window(date(2026, 10, 19), 13, 14), "2026-10-14")
        self.assertEqual(record["book"]["content_digest"],
                         "bfa951be548462eff9f50f6e51cf5ede43c02fe002d4eea9c48c4eae4c9874a1")

    def test_the_input_book_is_not_changed(self):
        data = book()
        before = copy.deepcopy(data)
        ex.exposure(data, ex.Window(date(2026, 10, 19), 0, 24), "2026-10-14")
        self.assertEqual(data, before)


class Imports(unittest.TestCase):
    def imported(self, path):
        names = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = "src.book" + ("." + base if base else "")
                names.add(base)
        return names

    def test_no_import_from_the_web_layer_or_the_network(self):
        for path in MODULES:
            for name in self.imported(path):
                with self.subTest(module=path.name, name=name):
                    self.assertFalse(any(name == f or name.startswith(f + ".") for f in FORBIDDEN), name)

    def test_only_the_standard_library_and_the_repository_are_imported(self):
        allowed_src = ("src.book", "src.price", "src.outlook", "src.contracts")
        stdlib = getattr(sys, "stdlib_module_names", None)
        for path in MODULES:
            for name in self.imported(path):
                with self.subTest(module=path.name, name=name):
                    if name.startswith("src."):
                        self.assertTrue(name.startswith(allowed_src), name)
                    elif stdlib is not None:
                        self.assertIn(name.split(".")[0], stdlib)


if __name__ == "__main__":
    unittest.main()
