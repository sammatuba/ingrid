"""BOOK-2: the impact of an outlook vintage's band on the synthetic book, per account and node, offline.

Acceptance lines proved here: the impact per account rests on the vintage's band by digest and a band
that cannot be tied to its record is refused; the materiality line is stated before any figure and no
change is classified without a stated policy; every figure is labelled synthetic; src/price/impact.py is
imported, its alias pattern stays as it is and its portfolio loader and pairing check are never called
on the book; versions are append-only. The vintages are the committed synthetic fixture
``tests/fixtures/book/vintages`` (built by ``scripts/book/vintages.py``), never the owner's archive.
"""
import ast
import copy
import dataclasses
import hashlib
import re
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.book import exposure as ex  # noqa: E402
from src.book import impact as im  # noqa: E402
from src.book.records import LABEL, counts_of, seal  # noqa: E402
from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.outlook.records import build_outlook  # noqa: E402
from src.price import impact as price_impact  # noqa: E402
from src.price.impact import DEFAULT_MATERIALITY, MaterialityPolicy, NodePosition  # noqa: E402
from tests.test_book_exposure import MODULES, book, figure_dicts  # noqa: E402

ARCHIVE = ROOT / "tests" / "fixtures" / "book" / "vintages"
V1 = "book-demo-2026-10-19-cvis"
V2 = "book-demo-2026-10-19-cvis-v2"
#: The question's cutoff: 2026-10-18, a date, so it closes at 2026-10-19 00:00 Manila (2026-10-18T16:00Z).
#: Both fixture vintages were issued before that (02:00Z and 06:00Z), so both may price the question.
CUTOFF = "2026-10-18"
WINDOW = ex.Window(date(2026, 10, 19), 13, 15)


def _script():
    spec = importlib.util.spec_from_file_location("book_vintages", ROOT / "scripts" / "book" / "vintages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VINTAGES = _script()


def outlook(outlook_id):
    return json.loads((ARCHIVE / "outlooks" / f"{outlook_id}.json").read_text(encoding="utf-8"))


def values(outlook_id):
    return (ARCHIVE / "values" / f"{outlook_id}.json").read_bytes()


def vintage(outlook_id=V1):
    return im.load_vintage(ARCHIVE, outlook_id, outlook(outlook_id)["content_digest"])


def in_memory_vintage(document, **overrides):
    """A vintage built through the real archive builder from a values document, never written to disk."""
    data = (canonical_dumps(document) + "\n").encode("utf-8")
    fields = VINTAGES.outlook_fields(V1)
    fields["values_ref"] = {"path_hint": "in-memory", "sha256": hashlib.sha256(data).hexdigest(),
                            "rows": len(document["hours"])}
    fields.update(overrides)
    record = build_outlook(**fields)
    return record, data


def scratch_directory(prefix="book2-"):
    """The system temp dir, else the ignored .local/test-scratch (a review sandbox may lack /tmp)."""
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


class OneAccountOneHour(unittest.TestCase):
    def test_the_impact_of_one_visayas_account_for_one_hour_written_out(self):
        record = im.build_impact(book(), vintage(), ex.Window(date(2026, 10, 19), 13, 14), CUTOFF,
                                 DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        [account] = record["accounts"]
        [node] = account["nodes"]
        [hour] = node["hours"]
        # The arithmetic, written out:
        #   uncovered MWh (test_book_exposure)           6.635 - (2.0 + 1.5)          = 3.135
        #   reference, contract-weighted                 (2.0 x 5370 + 1.5 x 7130) / 3.5
        #                                                = 21435 / 3.5 = 6124.2857... -> 6124.29
        #   band at 13:00 (vintage V1, peak hour)        p10 6200, p50 7400, p90 10000
        #   p10: 3.135 x (6200  - 6124.29) = 3.135 x 75.71   =   237.35085 ->   237.35
        #   p50: 3.135 x (7400  - 6124.29) = 3.135 x 1275.71 =  3999.35085 ->  3999.35
        #   p90: 3.135 x (10000 - 6124.29) = 3.135 x 3875.71 = 12150.35085 -> 12150.35
        self.assertEqual(hour["uncovered_mwh"], 3.135)
        self.assertEqual(hour["reference_php_mwh"], 6124.29)
        self.assertEqual(hour["reference_php_mwh"], round((2.0 * 5370 + 1.5 * 7130) / 3.5, 2))
        self.assertEqual(hour["covering_contracts"], ["CT-VIS03-1", "CT-VIS03-2"])
        self.assertEqual(hour["band_php_mwh"], {"p10": 6200.0, "p50": 7400.0, "p90": 10000.0})
        self.assertEqual((hour["p10_php"], hour["p50_php"], hour["p90_php"]), (237.35, 3999.35, 12150.35))
        self.assertEqual(hour["p50_php"], round(3.135 * (7400 - 6124.29), 2))
        self.assertEqual((account["p10_php"], account["p50_php"], account["p90_php"]), (237.35, 3999.35, 12150.35))
        self.assertEqual(node["reference_basis"], "contract_weighted")
        self.assertTrue(node["band_basis"].startswith("regional"))

    def test_the_band_is_kept_in_order_and_the_sign_is_kept(self):
        record = im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        for account in record["accounts"]:
            self.assertLessEqual(account["p10_php"], account["p50_php"])
            self.assertLessEqual(account["p50_php"], account["p90_php"])
        # ACC-VIS02 pays 8190 on NODE-VIS05's peak block, above the 7400 mid band: a gain, kept negative.
        vis02 = next(a for a in record["accounts"] if a["account_id"] == "ACC-VIS02")
        self.assertLess(vis02["p50_php"], 0)

    def test_the_figures_add_up_from_the_stored_hour_figures(self):
        record = im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        for key in ("p10_php", "p50_php", "p90_php"):
            for account in record["accounts"]:
                for node in account["nodes"]:
                    self.assertEqual(node[key], round(sum(h[key] for h in node["hours"]), 2))
                self.assertEqual(account[key], round(sum(n[key] for n in account["nodes"]), 2))
            self.assertEqual(record["totals"][key], round(sum(a[key] for a in record["accounts"]), 2))

    def test_it_is_the_impact_1_product_per_node(self):
        # NODE-VIS01 has one fixed contract over all hours (CT-VIS01-1, 5070), so the reference price is
        # constant and IMPACT-1's NodePosition computes the same product from the same uncovered hours.
        record = im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, nodes=["NODE-VIS01"])
        node = record["accounts"][0]["nodes"][0]
        profile = ex.exposure(book(), ex.Window(date(2026, 10, 19), 0, 24), CUTOFF, nodes=["NODE-VIS01"])["rows"]
        position = NodePosition(node="NODE-VIS01", region="Visayas", contract_price_php_mwh=5070.0,
                                uncovered_mwh_by_hour=tuple(r["uncovered_mwh"] for r in profile))
        hours = [datetime(2026, 10, 19, 13), datetime(2026, 10, 19, 14)]
        for key, level in (("p10_php", 6200.0), ("p50_php", 7400.0), ("p90_php", 10000.0)):
            self.assertAlmostEqual(node[key], position.impact_php(hours, level), places=2)
        self.assertAlmostEqual(node["uncovered_mwh"], position.uncovered_mwh(hours), places=9)


class TiedByDigest(unittest.TestCase):
    def test_the_record_names_the_vintage_and_the_book_by_digest(self):
        record = im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        stored = outlook(V1)
        self.assertEqual(record["vintage"]["outlook_id"], V1)
        self.assertEqual(record["vintage"]["outlook_digest"], stored["content_digest"])
        self.assertEqual(record["vintage"]["values_sha256"], hashlib.sha256(values(V1)).hexdigest())
        self.assertEqual(record["vintage"]["values_sha256"], stored["values_ref"]["sha256"])
        self.assertEqual(record["book"]["content_digest"],
                         "bfa951be548462eff9f50f6e51cf5ede43c02fe002d4eea9c48c4eae4c9874a1")
        self.assertEqual(record["content_digest"], im.record_digest(record))

    def test_a_values_file_with_one_byte_changed_is_refused(self):
        data = bytearray(values(V1))
        index = data.index(b"7400")
        data[index] = ord("8")
        with self.assertRaises(im.BookImpactError) as caught:
            im.tie_band(outlook(V1), bytes(data), outlook(V1)["content_digest"])
        self.assertEqual(caught.exception.code, "BAND_DIGEST_MISMATCH")

    def test_another_vintages_values_file_is_refused(self):
        with self.assertRaises(im.BookImpactError) as caught:
            im.load_vintage(ARCHIVE, V1, outlook(V1)["content_digest"], values_file=ARCHIVE / "values" / f"{V2}.json")
        self.assertEqual(caught.exception.code, "BAND_DIGEST_MISMATCH")

    def test_an_edited_outlook_record_is_refused(self):
        record = outlook(V1)
        record["values_ref"]["sha256"] = hashlib.sha256(b"other bytes").hexdigest()
        with self.assertRaises(im.BookImpactError) as caught:
            im.tie_band(record, values(V1), outlook(V1)["content_digest"])
        self.assertEqual(caught.exception.code, "VINTAGE_NOT_A_RECORD")

    def test_a_record_other_than_the_one_named_is_refused(self):
        with self.assertRaises(im.BookImpactError) as caught:
            im.tie_band(outlook(V1), values(V1), outlook(V2)["content_digest"])
        self.assertEqual(caught.exception.code, "VINTAGE_DIGEST_MISMATCH")
        with self.assertRaises(im.BookImpactError) as caught:
            im.load_vintage(ARCHIVE, V1, outlook(V2)["content_digest"])
        self.assertEqual(caught.exception.code, "VINTAGE_DIGEST_MISMATCH")

    def test_a_resealed_record_citing_other_bytes_is_refused(self):
        document = VINTAGES.values_document(V1)
        record, _ = in_memory_vintage(document)
        with self.assertRaises(im.BookImpactError) as caught:
            im.tie_band(record, values(V2), record["content_digest"])
        self.assertEqual(caught.exception.code, "BAND_DIGEST_MISMATCH")

    def test_a_row_count_other_than_the_records_is_refused(self):
        document = VINTAGES.values_document(V1)
        record, data = in_memory_vintage(document)
        fields = VINTAGES.outlook_fields(V1)
        fields["values_ref"] = dict(record["values_ref"], rows=23)
        short = build_outlook(**fields)
        with self.assertRaises(im.BookImpactError) as caught:
            im.tie_band(short, data, short["content_digest"])
        self.assertEqual(caught.exception.code, "BAND_ROWS_MISMATCH")

    def test_an_unknown_vintage_is_refused(self):
        with self.assertRaises(im.BookImpactError) as caught:
            im.load_vintage(ARCHIVE, "book-fixture-none", "0" * 64)
        self.assertEqual(caught.exception.code, "VINTAGE_UNKNOWN")

    def test_a_band_not_read_through_the_tie_is_refused(self):
        loose = {"outlook_id": V1, "levels": {}}
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), loose, WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(caught.exception.code, "BAND_NOT_TIED")

    def test_a_window_outside_the_vintage_is_refused(self):
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), vintage(), ex.Window(date(2026, 10, 20), 13, 15), CUTOFF,
                            DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_VINTAGE")

    def test_the_as_of_rule_refuses_an_early_cutoff_before_the_exposure_runs(self):
        # 2025-12-31 is before the contract terms and before the vintage's issue. The as-of rule runs
        # first, so the refusal names the vintage.
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), vintage(), WINDOW, "2025-12-31", DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertEqual(caught.exception.code, "VINTAGE_AFTER_CUTOFF")

    def test_the_exposure_cutoff_refusal_reaches_through_build_impact(self):
        # A resealed book whose CT-VIS03-1 starts 2026-10-19, after the 2026-10-18 cutoff. The vintage
        # qualifies, so the exposure's own rule refuses the question.
        data = book()
        for contract in data["contracts"]:
            if contract["id"] == "CT-VIS03-1":
                contract["term_start"] = "2026-10-19"
        seal(data)
        with self.assertRaises(ex.ExposureError) as caught:
            im.build_impact(data, vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertEqual(caught.exception.code, "CUTOFF_BEFORE_TERM_START")
        self.assertIn("CT-VIS03-1", str(caught.exception))


class ForgedBands(unittest.TestCase):
    """Review finding 2: build_impact accepts only a band that tie_band sealed and nobody changed."""

    def test_a_hand_built_band_is_refused(self):
        real = vintage()
        forged = im.VintageBand(**{f.name: getattr(real, f.name) for f in dataclasses.fields(real)
                                   if f.name != "seal"})
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), forged, WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(caught.exception.code, "BAND_NOT_TIED")

    def test_a_replaced_copy_with_other_levels_is_refused(self):
        real = vintage()
        levels = {hour: (0.0, 0.0, 0.0) for hour in real.levels}
        for changed in (dataclasses.replace(real, levels=levels),
                        dataclasses.replace(real, levels=im.MappingProxyType(levels)),
                        dataclasses.replace(real, outlook_digest="0" * 64)):
            with self.subTest(), self.assertRaises(im.BookImpactError) as caught:
                im.build_impact(book(), changed, WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
            self.assertEqual(caught.exception.code, "BAND_NOT_TIED")

    def test_a_tied_band_cannot_be_changed_in_place(self):
        real = vintage()
        hour = datetime(2026, 10, 19, 13)
        with self.assertRaises(TypeError):
            real.levels[hour] = (0.0, 0.0, 0.0)
        object.__setattr__(real, "levels", im.MappingProxyType({**real.levels, hour: (0.0, 0.0, 0.0)}))
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), real, WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(caught.exception.code, "BAND_NOT_TIED")

    def test_a_deep_copy_is_refused_with_a_named_error(self):
        with self.assertRaises(im.BookImpactError) as caught:
            copy.deepcopy(vintage())
        self.assertEqual(caught.exception.code, "BAND_NOT_COPYABLE")
        self.assertFalse(hasattr(im.VintageBand, "expected_seal"))

    def test_an_untouched_tied_band_is_accepted(self):
        self.assertEqual(im.check_band(vintage()).outlook_id, V1)


class AsOf(unittest.TestCase):
    """Orchestrator decision A: a vintage may price a question only if it was issued by the cutoff."""

    def test_a_vintage_issued_after_the_cutoff_is_refused(self):
        # V1 was issued 2026-10-18T02:00Z and V2 at 06:00Z. A cutoff at 04:00Z admits V1 only.
        im.build_impact(book(), vintage(V1), WINDOW, "2026-10-18T04:00:00Z", DEFAULT_MATERIALITY,
                        accounts=["ACC-VIS03"])
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), vintage(V2), WINDOW, "2026-10-18T04:00:00Z", DEFAULT_MATERIALITY,
                            accounts=["ACC-VIS03"])
        self.assertEqual(caught.exception.code, "VINTAGE_AFTER_CUTOFF")
        # A date cutoff of 2026-10-17 closes at 2026-10-17T16:00Z, before both vintages.
        for outlook_id in (V1, V2):
            with self.subTest(outlook_id=outlook_id), self.assertRaises(im.BookImpactError) as caught:
                im.build_impact(book(), vintage(outlook_id), WINDOW, "2026-10-17", DEFAULT_MATERIALITY,
                                accounts=["ACC-VIS03"])
            self.assertEqual(caught.exception.code, "VINTAGE_AFTER_CUTOFF")

    def test_an_issue_exactly_at_an_instant_cutoff_is_accepted(self):
        record = im.build_impact(book(), vintage(V1), WINDOW, "2026-10-18T02:00:00Z", DEFAULT_MATERIALITY,
                                 accounts=["ACC-VIS03"])
        self.assertEqual(record["as_of"]["question_cutoff_closes"], "2026-10-18T02:00:00Z")

    def test_the_record_states_both_instants(self):
        record = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertEqual(record["as_of"]["question_cutoff"], "2026-10-18")
        self.assertEqual(record["as_of"]["question_cutoff_closes"], "2026-10-18T16:00:00Z")
        self.assertEqual(record["as_of"]["vintage_issued_at"], "2026-10-18T06:00:00Z")
        self.assertEqual(record["as_of"]["vintage_issued_at"], outlook(V2)["issued_at"])
        self.assertEqual(record["as_of"]["vintage_information_cutoff"], outlook(V2)["information_cutoff"])
        self.assertEqual(record["as_of"]["rule"], im.AS_OF_RULE)


class SeveralDays(unittest.TestCase):
    """Orchestrator decision B: a window of whole days inside the horizon, the profile repeated per day."""

    def week_vintage(self):
        document = VINTAGES.values_document(V1)
        day_rows = document["hours"]
        rows = []
        for n in range(7):
            for row in day_rows:
                rows.append(dict(row, hour_start=row["hour_start"].replace("2026-10-19", f"2026-10-{19 + n}")))
        document["hours"] = rows
        record, data = in_memory_vintage(document, horizon={"label": "week", "start": "2026-10-18T16:00:00Z",
                                                            "end": "2026-10-25T16:00:00Z"})
        return im.tie_band(record, data, record["content_digest"])

    def test_two_whole_days_are_the_sum_of_their_days(self):
        band = self.week_vintage()
        two = ex.Window.between("2026-10-19T00:00", "2026-10-21T00:00")
        record = im.build_impact(book(), band, two, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        days = [im.build_impact(book(), band, ex.Window(date(2026, 10, d), 0, 24), CUTOFF, DEFAULT_MATERIALITY,
                                region="Visayas") for d in (19, 20)]
        self.assertEqual(record["window"]["hours"], 48)
        for key in ("p10_php", "p50_php", "p90_php"):
            for index, account in enumerate(record["accounts"]):
                self.assertEqual(account[key], round(days[0]["accounts"][index][key] + days[1]["accounts"][index][key], 2))
            self.assertEqual(record["totals"][key], round(days[0]["totals"][key] + days[1]["totals"][key], 2))
        # The band and the profile repeat, so day two equals day one here.
        self.assertEqual(days[0]["totals"]["p50_php"], days[1]["totals"]["p50_php"])

    def test_a_window_outside_the_day_horizon_is_refused(self):
        two = ex.Window.between("2026-10-19T00:00", "2026-10-21T00:00")
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), vintage(), two, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_VINTAGE")

    def test_a_window_across_a_midnight_inside_a_day_is_still_refused(self):
        with self.assertRaises(ex.ExposureError) as caught:
            ex.Window.between("2026-10-19T13:00", "2026-10-20T15:00")
        self.assertEqual(caught.exception.code, "WINDOW_OUTSIDE_PROFILE")


class BandShapes(unittest.TestCase):
    def test_a_mid_only_vintage_is_a_zero_width_band_and_says_so(self):
        document = VINTAGES.values_document(V1)
        for row in document["hours"]:
            for key in ("p10", "p50", "p90"):
                del row[key]
        record, data = in_memory_vintage(document)
        band = im.tie_band(record, data, record["content_digest"])
        self.assertTrue(band.zero_width)
        self.assertTrue(band.reference()["band_width"].startswith("zero"))
        result = im.build_impact(book(), band, WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        account = result["accounts"][0]
        self.assertEqual(account["p10_php"], account["p50_php"])
        self.assertEqual(account["p50_php"], account["p90_php"])

    def test_a_system_band_prices_a_regional_node_and_names_the_basis(self):
        document = dict(VINTAGES.values_document(V1), series="SYSTEM")
        record, data = in_memory_vintage(document)
        band = im.tie_band(record, data, record["content_digest"])
        result = im.build_impact(book(), band, WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertTrue(result["accounts"][0]["nodes"][0]["band_basis"].startswith("system"))

    def test_another_regions_band_is_refused(self):
        document = dict(VINTAGES.values_document(V1), series="CLUZ")
        record, data = in_memory_vintage(document)
        band = im.tie_band(record, data, record["content_digest"])
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(book(), band, WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertEqual(caught.exception.code, "BAND_REGION_MISMATCH")

    def test_a_partial_band_row_and_an_hour_outside_the_horizon_are_refused(self):
        partial = VINTAGES.values_document(V1)
        del partial["hours"][3]["p90"]
        outside = VINTAGES.values_document(V1)
        outside["hours"][0]["hour_start"] = "2026-10-20T00:00:00"
        unknown = dict(VINTAGES.values_document(V1), series="NODE-VIS03")
        for document, code in ((partial, "BAND_SHAPE"), (outside, "BAND_SHAPE"), (unknown, "BAND_SERIES_UNSUPPORTED")):
            record, data = in_memory_vintage(document)
            with self.subTest(code=code), self.assertRaises(im.BookImpactError) as caught:
                im.tie_band(record, data, record["content_digest"])
            self.assertEqual(caught.exception.code, code)

    def test_an_hour_with_uncovered_volume_and_no_contract_is_refused(self):
        data = book()
        data["contracts"] = [c for c in data["contracts"] if c["node_id"] != "NODE-VIS03"]
        data["counts"] = counts_of(data)
        seal(data)
        with self.assertRaises(im.BookImpactError) as caught:
            im.build_impact(data, vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertEqual(caught.exception.code, "NO_COVERING_CONTRACT")


class MaterialityFirst(unittest.TestCase):
    def test_the_materiality_block_is_the_first_key_and_the_first_text(self):
        record = im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        self.assertEqual(next(iter(record)), "materiality")
        text = im.record_text(record)
        self.assertTrue(text.startswith('{"materiality":{'))
        block_end = text.index("}")
        self.assertLess(block_end, text.index('"p50_php"'))
        self.assertLess(block_end, text.index('"uncovered_mwh"'))
        self.assertEqual(json.loads(text), record)
        block = record["materiality"]
        self.assertEqual(block["threshold_php"], price_impact.MATERIALITY_THRESHOLD_PHP)
        self.assertEqual(block["comparator"], "at_or_above")
        self.assertEqual(block["rule"], im.BOOK_RULE)
        self.assertIn("comes before any figure", block["statement"])

    def test_no_figure_is_written_without_a_stated_policy(self):
        with self.assertRaises(TypeError):
            im.build_impact(book(), vintage(), WINDOW, CUTOFF)  # noqa: the policy has no default
        for policy in (None, 1_000_000.0, {"threshold_php": 1}):
            with self.subTest(policy=policy), self.assertRaises(im.BookImpactError) as caught:
                im.build_impact(book(), vintage(), WINDOW, CUTOFF, policy, region="Visayas")
            self.assertEqual(caught.exception.code, "POLICY_REQUIRED")

    def test_the_change_between_two_vintages_against_the_line(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        change = im.compare_impacts(before, after, DEFAULT_MATERIALITY)
        self.assertEqual(next(iter(change)), "materiality")
        # V2 raises the peak mid band from 7400 to 8900 (+1500) and hours 13 and 14 are peak hours, so each
        # account's p50 moves by its uncovered MWh x 1500:
        #   ACC-VIS01: 51.602 x 1500 = 77403.0
        #   ACC-VIS02: 36.838 x 1500 = 55257.0
        #   ACC-VIS03:  6.804 x 1500 = 10206.0
        self.assertEqual([(r["account_id"], r["change_php"]) for r in change["accounts"]],
                         [("ACC-VIS01", 77403.0), ("ACC-VIS02", 55257.0), ("ACC-VIS03", 10206.0)])
        # None reaches the stated 1,000,000 PHP line.
        self.assertEqual(change["summary"]["material"], 0)
        self.assertEqual(change["before"]["impact_digest"], before["content_digest"])
        self.assertEqual(change["after"]["outlook_digest"], outlook(V2)["content_digest"])

    def test_the_verdict_follows_the_stated_line_never_the_changes(self):
        def changes(policy):
            before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, policy, region="Visayas")
            after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, policy, region="Visayas")
            return im.compare_impacts(before, after, policy)

        self.assertEqual([r["material"] for r in changes(MaterialityPolicy(50_000.0))["accounts"]],
                         [True, True, False])
        self.assertEqual([r["material"] for r in changes(MaterialityPolicy(55_257.0))["accounts"]],
                         [True, True, False])
        self.assertEqual([r["material"] for r in changes(MaterialityPolicy(55_257.0, "above"))["accounts"]],
                         [True, False, False])

    def test_no_change_is_classified_without_a_stated_policy_or_against_another_line(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        with self.assertRaises(TypeError):
            im.compare_impacts(before, after)  # noqa: the policy has no default
        with self.assertRaises(im.BookImpactError) as caught:
            im.compare_impacts(before, after, None)
        self.assertEqual(caught.exception.code, "POLICY_REQUIRED")
        with self.assertRaises(im.BookImpactError) as caught:
            im.compare_impacts(before, after, MaterialityPolicy(50_000.0))
        self.assertEqual(caught.exception.code, "POLICY_MISMATCH")

    def test_records_that_do_not_compare_are_refused(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        other_window = im.build_impact(book(), vintage(V2), ex.Window(date(2026, 10, 19), 13, 14), CUTOFF,
                                       DEFAULT_MATERIALITY, region="Visayas")
        fewer = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        for after in (other_window, fewer):
            with self.assertRaises(im.BookImpactError) as caught:
                im.compare_impacts(before, after, DEFAULT_MATERIALITY)
            self.assertEqual(caught.exception.code, "CHANGE_NOT_COMPARABLE")
        edited = copy.deepcopy(before)
        edited["accounts"][0]["p50_php"] += 1
        with self.assertRaises(im.BookImpactError) as caught:
            im.compare_impacts(edited, before, DEFAULT_MATERIALITY)
        self.assertEqual(caught.exception.code, "RECORD_DIGEST_MISMATCH")

    def test_records_over_other_nodes_of_an_account_are_refused(self):
        # Review finding 1: one node of ACC-VIS01 against the whole account, both on the same vintage.
        # Without the node check the "change" would be NODE-VIS04's share, 45,052.68 PHP.
        node_only = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, nodes=["NODE-VIS01"])
        account = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS01"])
        self.assertEqual([a["account_id"] for a in node_only["accounts"]], ["ACC-VIS01"])
        with self.assertRaises(im.BookImpactError) as caught:
            im.compare_impacts(node_only, account, DEFAULT_MATERIALITY)
        self.assertEqual(caught.exception.code, "CHANGE_NOT_COMPARABLE")

    def test_a_stored_change_record_proves_its_own_verdicts(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        change = im.compare_impacts(before, after, DEFAULT_MATERIALITY)
        self.assertIs(im.verify_record(change, im.CHANGE_KIND), change)
        for edit in ("verdict", "change", "count"):
            forged = copy.deepcopy(change)
            if edit == "verdict":
                forged["accounts"][0]["material"] = True
            elif edit == "change":
                forged["accounts"][0]["change_php"] = 1.0
            else:
                forged["summary"]["material"] = 3
            forged["content_digest"] = im.record_digest(forged)
            with self.subTest(edit=edit), self.assertRaises(im.BookImpactError) as caught:
                im.verify_record(forged, im.CHANGE_KIND)
            self.assertEqual(caught.exception.code, "RECORD_INVALID")


class Labels(unittest.TestCase):
    def test_every_figure_carries_the_synthetic_label(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        change = im.compare_impacts(before, after, DEFAULT_MATERIALITY)
        for record in (before, change):
            self.assertTrue(record["synthetic"])
            self.assertTrue(record["label"].startswith(LABEL))
            body = {k: v for k, v in record.items() if k != "materiality"}
            found = list(figure_dicts(body))
            self.assertTrue(found)
            for node, labelled in found:
                self.assertTrue(labelled, sorted(node))
        self.assertIn(V1, before["label"])
        self.assertIn(outlook(V1)["content_digest"][:12], before["label"])
        self.assertIn("never a business number", before["label"])
        self.assertIn("method demonstration", before["units"]["impact"])

    def test_a_vintage_that_declares_real_inputs_still_gives_synthetic_figures(self):
        record, data = in_memory_vintage(VINTAGES.values_document(V1), synthetic=False)
        band = im.tie_band(record, data, record["content_digest"])
        result = im.build_impact(book(), band, WINDOW, CUTOFF, DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["vintage"]["synthetic"])
        self.assertIn("declares real inputs", result["label"])
        self.assertTrue(result["accounts"][0]["label"].startswith(LABEL))


class PlainStrings(unittest.TestCase):
    """Review finding 3: the strings inside the records follow the plain-language rules of the site."""

    def strings(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        change = im.compare_impacts(before, after, DEFAULT_MATERIALITY)
        record, data = in_memory_vintage(VINTAGES.values_document(V1), synthetic=False)
        real = im.tie_band(record, data, record["content_digest"])
        exposure = ex.exposure(book(), WINDOW, CUTOFF, region="Visayas")
        strings = {"label": before["label"], "real label": im.impact_label(real), "change label": change["label"],
                   "statement": im.BOOK_STATEMENT, "rule": im.BOOK_RULE, "basis": im.BOOK_BASIS,
                   "as of": im.AS_OF_RULE, "zero band": im.BAND_ZERO, "full band": im.BAND_FULL,
                   "clock": before["window"]["clock"]}
        # Every method string the records carry (review round 2, note D).
        for name, text in before["method"].items():
            strings["impact method " + name] = text
        for name, text in exposure["method"].items():
            strings["exposure method " + name] = text
        for name, text in {**before["units"], **exposure["units"]}.items():
            strings["unit " + name] = text
        strings["materiality " + "rule"] = before["materiality"]["rule"]
        return strings

    def test_no_banned_word_no_passive_and_short_sentences(self):
        config = json.loads((ROOT / "docs" / "routes.json").read_text(encoding="utf-8"))["plain_language"]
        banned = [re.compile(pattern, re.I) for pattern in config["banned_words"]]
        spec = importlib.util.spec_from_file_location("repo_tool", ROOT / "scripts" / "repo.py")
        repo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(repo)
        for name, text in self.strings().items():
            with self.subTest(name=name):
                self.assertNotIn(";", text)
                for pattern in banned:
                    self.assertIsNone(pattern.search(text), (pattern.pattern, text))
                for sentence in repo.sentences(text):
                    self.assertLess(len(sentence.split()), 20, sentence)
                    hit = next((m for m in repo.PASSIVE.finditer(sentence)
                                if m.group(1).lower() not in repo.NOT_PARTICIPLES), None)
                    self.assertIsNone(hit, sentence)

    def test_the_label_names_the_record_id(self):
        label = self.strings()["label"]
        self.assertIn("record id " + outlook(V1)["content_digest"][:12], label)
        self.assertNotIn("content digest", label)
        self.assertNotIn("p50", im.BAND_ZERO + im.BAND_FULL)


class TheAffectedPartAndTheQuery(unittest.TestCase):
    def test_the_affected_part_of_visayas_is_priced(self):
        record = im.affected_impact(book(), "CVIS", WINDOW, CUTOFF, vintage(), DEFAULT_MATERIALITY)
        self.assertEqual([a["account_id"] for a in record["accounts"]], ["ACC-VIS01", "ACC-VIS02", "ACC-VIS03"])
        self.assertEqual(record, im.build_impact(book(), vintage(), WINDOW, CUTOFF, DEFAULT_MATERIALITY,
                                                 region="Visayas"))

    def test_the_query_names_the_vintage_by_id_and_digest(self):
        record = im.query_impact(book(), ARCHIVE, V1, outlook(V1)["content_digest"], WINDOW, CUTOFF,
                                 DEFAULT_MATERIALITY, accounts=["ACC-VIS03"])
        # Hour 13: 3.135 x (7400 - 6124.29) = 3999.35 (OneAccountOneHour).
        # Hour 14: 7.169 - 3.5 = 3.669 MWh, and 3.669 x (7400 - 6124.29) = 3.669 x 1275.71 = 4680.58.
        # The window's p50: 3999.35 + 4680.58 = 8679.93.
        hour14 = record["accounts"][0]["nodes"][0]["hours"][1]
        self.assertEqual(hour14["uncovered_mwh"], 3.669)
        self.assertEqual(hour14["p50_php"], 4680.58)
        self.assertEqual(hour14["p50_php"], round(3.669 * (7400 - 6124.29), 2))
        self.assertEqual(record["accounts"][0]["p50_php"], 8679.93)


class AppendOnly(unittest.TestCase):
    def test_each_version_is_written_once_beside_the_others(self):
        before = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        after = im.build_impact(book(), vintage(V2), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        change = im.compare_impacts(before, after, DEFAULT_MATERIALITY)
        with scratch_directory() as scratch:
            store = im.ImpactStore(scratch)
            first = store.append(before)
            with self.assertRaises(im.BookImpactError) as caught:
                store.append(before)
            self.assertEqual(caught.exception.code, "RECORD_EXISTS")
            store.append(after)
            store.append(change)
            self.assertEqual(store.digests(), tuple(sorted([before["content_digest"], after["content_digest"]])))
            self.assertEqual(store.digests(im.CHANGE_KIND), (change["content_digest"],))
            self.assertEqual(store.read(im.KIND, before["content_digest"]), before)
            self.assertTrue(first.read_text(encoding="utf-8").startswith('{"materiality":'))

    def test_the_store_refuses_the_repository_tree_and_an_edited_record(self):
        with self.assertRaises(im.BookImpactError) as caught:
            im.ImpactStore(ROOT / "docs" / "book-impact")
        self.assertEqual(caught.exception.code, "WRITE_INTO_REPOSITORY")
        record = im.build_impact(book(), vintage(V1), WINDOW, CUTOFF, DEFAULT_MATERIALITY, region="Visayas")
        record["totals"]["p50_php"] = 0.0
        with scratch_directory() as scratch, self.assertRaises(im.BookImpactError) as caught:
            im.ImpactStore(scratch).append(record)
        self.assertEqual(caught.exception.code, "RECORD_DIGEST_MISMATCH")


class TheFixtureAndImpact1(unittest.TestCase):
    def test_the_vintage_fixture_reproduces_from_its_builder(self):
        self.assertEqual(VINTAGES.check(), [])

    def test_the_fixture_vintages_are_synthetic_and_cite_their_values_by_digest(self):
        for outlook_id in (V1, V2):
            record = outlook(outlook_id)
            self.assertTrue(record["synthetic"])
            self.assertEqual(record["values_ref"]["sha256"], hashlib.sha256(values(outlook_id)).hexdigest())
            self.assertTrue(json.loads(values(outlook_id))["synthetic"])

    def _tree(self, path):
        return ast.parse(path.read_text(encoding="utf-8"))

    def test_src_price_impact_is_imported(self):
        tree = self._tree(ROOT / "src" / "book" / "impact.py")
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imported |= {f"{node.module}.{a.name}" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                     for a in node.names}
        self.assertIn("src.price.impact", imported)
        self.assertIs(im.MaterialityPolicy, price_impact.MaterialityPolicy)

    def test_the_book_never_widens_the_alias_pattern_nor_loads_the_portfolio(self):
        self.assertEqual(price_impact.ALIAS_PATTERN.pattern, r"N\d{2}\Z")
        for path in MODULES:
            tree = self._tree(path)
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            names |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets
                      if isinstance(t, ast.Name)}
            for forbidden in ("ALIAS_PATTERN", "load_portfolio", "pair_positions"):
                with self.subTest(module=path.name, name=forbidden):
                    self.assertNotIn(forbidden, names)
            self.assertFalse(hasattr(im, "ALIAS_PATTERN"))
            self.assertFalse(hasattr(ex, "ALIAS_PATTERN"))


if __name__ == "__main__":
    unittest.main()
