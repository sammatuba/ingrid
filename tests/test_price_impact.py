"""IMPACT-1: the synthetic portfolio against the outlook band, offline.

Every case here builds its own synthetic series, portfolio and exports; no
network, model or cloud call is made and no repository fixture is read. The four
acceptance items carry named tests: the impact is the uncovered MWh by hour times
the band price minus the contract price and comes from the synthetic file and the
PRICE-2 scorecard bands with the standard library only
(:class:`ImpactArithmetic`, :class:`BandsAreTheScorecards`, :class:`StdlibOnly`),
the materiality threshold is stated before any change is scored
(:class:`MaterialityStatedFirst`), every peso figure is labelled a method
demonstration from a synthetic portfolio (:class:`DemonstrationLabel`) and no
portfolio volume, contract price or node name enters Git beyond the synthetic
file's aliases (:class:`NoPortfolioByteInGit`). :class:`RealExports` reads the
real exports and the real synthetic portfolio only when they are linked under
``.local/price/``.
"""
import contextlib
import dataclasses
import hashlib
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.price.baselines import HORIZONS, window_for  # noqa: E402
from src.price.impact import (  # noqa: E402
    ALIAS_PATTERN,
    DEFAULT_MATERIALITY,
    KIND,
    MATERIALITY_THRESHOLD_PHP,
    SYNTHETIC_STATEMENT,
    VERSION,
    ImpactError,
    ImpactRow,
    MaterialityPolicy,
    NodePosition,
    bands_of,
    build_impact_record,
    classify_changes,
    demonstration_label,
    impact_rows,
    load_portfolio,
    pair_positions,
    record_digest,
    record_text,
    verify_bands_against_record,
)
from src.price.scorecard import (  # noqa: E402
    AP,
    MARKET,
    build_scorecard,
    metrics_from,
)
from src.price.series import (  # noqa: E402
    REGIONAL_KEYS,
    HourRow,
    Series,
    billing_day_hours,
    billing_month_of,
    digest_file,
    load_nodal,
    load_regional,
)

PRICE_DIR = ROOT / ".local" / "price"
REGIONAL_CSV = PRICE_DIR / "lwap_final_hourly.csv"
NODAL_CSV = PRICE_DIR / "portfolio_nodal_hourly_deid.csv"
PORTFOLIO_JSON = PRICE_DIR / "portfolio-synthetic.json"
DIGESTS_JSON = PRICE_DIR / "digests.json"
SCORECARD_JSON = PRICE_DIR / "scorecard.json"

CSV_HEADER = "byear,bmonth,region_name,hour_start,n5,lwap_mean,lwap_min,lwap_max"
NODAL_HEADER = ("byear,bmonth,resource_name,region,hour_start,n5,lmp_mean,lmp_min,lmp_max,"
                "mw_mean,ap5,sec5,psm5")


def scratch_directory(prefix="impact1-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path.

    A review sandbox may mount no writable system temporary directory while the
    workspace itself stays writable; the fallback keeps these tests runnable
    there. It sits under the ignored ``.local/`` and is removed by
    :class:`tempfile.TemporaryDirectory` cleanup exactly like the primary path.
    """
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def day_value(day: date) -> float:
    """The synthetic value of one billing day: constant inside the day, unique."""
    return day.day * 100.0 + day.month * 10.0


def make_rows(start: date, days: int, value_of=day_value, absent_hours=(), ap_hours=(),
              flagged=False) -> dict:
    rows = {}
    for day_index in range(days):
        day = start + timedelta(days=day_index)
        value = day_value(day)
        for hour in billing_day_hours(day):
            if hour in absent_hours:
                continue
            rows[hour] = HourRow(
                hour_start=hour,
                intervals=12,
                mean=float(value_of(hour) if callable(value_of) else value),
                ap_intervals=12 if hour in ap_hours else 0,
                ap_known=flagged,
            )
    return rows


def make_series(key="N01", kind="nodal", start=date(2023, 6, 26), days=430, **kwargs) -> Series:
    rows = make_rows(start, days, **kwargs)
    return Series(key=key, kind=kind, label=f"{key} synthetic", source="synthetic.csv",
                  region=kwargs.get("region", "LUZON"), rows=rows)


def position(node="N01", region="LUZON", contract=5000.0, profile=None) -> NodePosition:
    if profile is None:
        profile = tuple(100.0 for _ in range(24))
    return NodePosition(node=node, region=region, contract_price_php_mwh=float(contract),
                        uncovered_mwh_by_hour=tuple(float(value) for value in profile))


def bands_for(series, horizons=("day", "week", "month"), baselines=None, min_fan_samples=3):
    """Score one series and keep the band sink beside the record."""
    bands = []
    scorecard = build_scorecard(
        [series], horizons=horizons, baselines=baselines, min_fan_samples=min_fan_samples,
        band_sink=bands,
    )
    return scorecard, bands


def write_portfolio(path, entries=None):
    entries = entries if entries is not None else [
        {"node": "N01", "region": "LUZON", "contract_price_php_mwh": 5000.0,
         "uncovered_mwh_by_hour": [float(hour + 1) for hour in range(24)], "synthetic": True},
        {"node": "N02", "region": "VISAYAS", "contract_price_php_mwh": 6000.0,
         "uncovered_mwh_by_hour": [10.0 for _ in range(24)], "synthetic": True},
    ]
    payload = {"synthetic": True, "note": "invented for the test", "portfolio": entries}
    path = Path(path)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def write_exports(directory, days=800, start=date(2023, 6, 26),
                  nodes=(("N01", "LUZON"), ("N02", "VISAYAS"))):
    """A regional and a nodal export in the PRICE-1 column order, with digests."""
    directory = Path(directory)
    regional = directory / "lwap_final_hourly.csv"
    nodal = directory / "portfolio_nodal_hourly_deid.csv"
    regional_lines = [CSV_HEADER]
    nodal_lines = [NODAL_HEADER]
    for day_index in range(days):
        day = start + timedelta(days=day_index)
        year, month = billing_month_of(day)
        for hour in billing_day_hours(day):
            value = day_value(day) + hour.hour
            for region in REGIONAL_KEYS:
                regional_lines.append(f"{year},{month},{region},{hour:%Y-%m-%d %H:%M:%S},"
                                      f"12,{value},1.0,2.0")
            for node, region in nodes:
                nodal_lines.append(f"{year},{month},{node},{region},{hour:%Y-%m-%d %H:%M:%S},"
                                   f"12,{value + 5.0},1.0,2.0,1.0,0,0,0")
    regional.write_text("\n".join(regional_lines) + "\n", encoding="utf-8")
    nodal.write_text("\n".join(nodal_lines) + "\n", encoding="utf-8")
    digests = directory / "digests.json"
    digests.write_text(json.dumps({
        "lwap_final_hourly.csv": digest_file(regional),
        "portfolio_nodal_hourly_deid.csv": digest_file(nodal),
    }, sort_keys=True), encoding="utf-8")
    return regional, nodal, digests


def load_cli(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "price" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConstantBaseline:
    """A test baseline that forecasts one fixed value at every target hour."""

    name = "constant"
    version = "test"
    formula = "forecast(hour) = a fixed constant"

    def __init__(self, value: float) -> None:
        self.value = float(value)

    def forecast(self, series, window, cutoff, index=None):
        from src.price.baselines import Forecast

        return Forecast((self.value,) * len(window.hours), {"value": self.value})


class MaterialityStatedFirst(unittest.TestCase):
    """Acceptance 2: the line exists before any change is scored."""

    def test_the_line_is_a_module_constant_readable_before_any_input(self):
        self.assertGreater(MATERIALITY_THRESHOLD_PHP, 0)
        self.assertEqual(DEFAULT_MATERIALITY.threshold_php, MATERIALITY_THRESHOLD_PHP)
        self.assertTrue(DEFAULT_MATERIALITY.to_dict()["rule"])

    def test_the_scoring_call_requires_a_declared_line(self):
        with self.assertRaises(TypeError):
            build_impact_record([], [], inputs=[])
        with self.assertRaises(ImpactError) as caught:
            build_impact_record([], [], "not a policy", [])
        self.assertEqual(caught.exception.code, "POLICY_REQUIRED")

    def test_a_change_exactly_at_the_line_is_material_and_just_below_is_not(self):
        policy = MaterialityPolicy(threshold_php=1000.0)
        self.assertTrue(policy.is_material(1000.0))
        self.assertTrue(policy.is_material(-1000.0))
        self.assertFalse(policy.is_material(999.99))
        self.assertFalse(policy.is_material(-999.99))

    def test_a_strict_comparator_can_be_stated_and_behaves_as_stated(self):
        strict = MaterialityPolicy(threshold_php=1000.0, comparator="above")
        self.assertFalse(strict.is_material(1000.0))
        self.assertTrue(strict.is_material(1000.01))
        with self.assertRaises(ImpactError) as caught:
            MaterialityPolicy(comparator="unless")
        self.assertEqual(caught.exception.code, "UNKNOWN_COMPARATOR")

    def test_a_line_that_is_not_a_positive_number_is_refused(self):
        for bad in (0.0, -1.0, "many", True, None):
            with self.assertRaises(ImpactError) as caught:
                MaterialityPolicy(threshold_php=bad)
            self.assertIn(caught.exception.code, ("THRESHOLD_NOT_POSITIVE", "THRESHOLD_NOT_A_NUMBER"))

    def test_the_line_is_an_input_and_never_a_statistic_of_the_scored_changes(self):
        # every change is exactly 1,000 PHP: at a line of 1,000 each one is
        # material, at 1,100 none is, and the rows never move the line
        rows = [ImpactRow(origin=f"2026-01-{day:02d}", window_hours=24, uncovered_mwh=100.0,
                          p10_php=0.0, p50_php=day * 1000.0, p90_php=0.0, settled_php=0.0)
                for day in range(1, 6)]
        low = classify_changes(rows, MaterialityPolicy(threshold_php=1000.0))
        high = classify_changes(rows, MaterialityPolicy(threshold_php=1100.0))
        self.assertEqual(low["compared"], high["compared"])
        self.assertEqual(low["material"], 4)
        self.assertEqual(high["material"], 0)
        # the record carries the line it was given, not a number read off the rows
        record = build_impact_record([position()], [], MaterialityPolicy(threshold_php=1500.0),
                                     inputs=[])
        self.assertEqual(record["materiality"]["threshold_php"], 1500.0)

    def test_the_record_states_the_line_ahead_of_every_impact_value(self):
        series = make_series(start=date(2023, 6, 26), days=430)
        _, bands = bands_for(series, horizons=("day",))
        self.assertTrue(bands)
        record = build_impact_record([position()], bands, DEFAULT_MATERIALITY, inputs=[])
        keys = list(record)
        self.assertEqual(keys[:5], ["kind", "version", "synthetic", "label", "materiality"])
        text = record_text(record)
        self.assertLess(text.index('"materiality"'), text.index('"nodes"'))
        self.assertLess(text.index('"materiality"'), text.index('"p50_php"'))

    def test_the_runner_prints_the_line_before_it_reads_an_input(self):
        cli = load_cli("impact")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(["--portfolio", ".local/nothing-here.json",
                               "--scorecard", ".local/nothing-here.json",
                               "--regional", "nowhere.csv", "--nodal", "nowhere.csv"])
        self.assertEqual(status, 2)
        self.assertIn("MISSING_PORTFOLIO", stderr.getvalue())
        text = stdout.getvalue()
        self.assertLess(text.index("materiality:"), text.index("label:"))
        self.assertIn("stated before any change is scored", text)
        self.assertIn(f"{MATERIALITY_THRESHOLD_PHP:,.2f}", text)


class DemonstrationLabel(unittest.TestCase):
    """Acceptance 3: every peso figure is labelled a method demonstration."""

    @classmethod
    def record(cls):
        if getattr(cls, "_record", None) is None:
            series = make_series(start=date(2023, 6, 26), days=430)
            scorecard, bands = bands_for(series, horizons=("day",))
            assert bands, "the fixture must carry priced figures"
            cls._record = build_impact_record([position()], bands, DEFAULT_MATERIALITY, inputs=[])
        return cls._record

    def test_the_record_carries_the_label_at_the_top_and_on_every_node(self):
        record = self.record()
        self.assertTrue(record["synthetic"])
        self.assertIn("never a business number", record["label"])
        self.assertIn("synthetic", record["label"])
        self.assertTrue(record["label"].startswith(SYNTHETIC_STATEMENT))
        # this record was built with no verified input: the label says so rather
        # than naming a dataset it did not read
        self.assertIn("no exported input verified in this run", record["label"])
        self.assertNotIn("pre-backfill", record["label"])
        for node in record["nodes"]:
            self.assertTrue(node["synthetic"])
            self.assertTrue(node["method_demonstration"])
        self.assertTrue(record["direction_check"]["label"])

    def test_the_label_names_every_verified_input_with_its_digest_prefix_and_row_count(self):
        inputs = [
            {"file": "lwap_final_hourly.csv", "sha256": "3b3b0b66" + "0" * 56, "rows": 184036},
            {"file": "portfolio_nodal_hourly_deid.csv", "sha256": "30ebab15" + "1" * 56,
             "rows": 517164},
        ]
        label = demonstration_label(inputs)
        self.assertTrue(label.startswith(SYNTHETIC_STATEMENT))
        expected = (SYNTHETIC_STATEMENT + "; read from the inputs this run verified: "
                    + ", ".join(f"{entry['file']} {entry['rows']} rows sha256 "
                                f"{entry['sha256'][:8]}" for entry in inputs))
        self.assertEqual(label, expected)
        for entry in inputs:
            self.assertIn(entry["file"], label)
            self.assertIn(f"{entry['rows']} rows", label)
            self.assertIn(entry["sha256"][:8], label)
        # the whole digest is not written: the label carries its first eight
        # hex digits, as the record's input block carries the whole one
        self.assertNotIn(inputs[0]["sha256"], label)

    def test_two_different_digest_sets_give_two_different_labels(self):
        first = [
            {"file": "lwap_final_hourly.csv", "sha256": "a" * 64, "rows": 184036},
            {"file": "portfolio_nodal_hourly_deid.csv", "sha256": "b" * 64, "rows": 517164},
        ]
        other_digest = [dict(first[0], sha256="c" * 64), dict(first[1])]
        other_rows = [dict(first[0]), dict(first[1], rows=517165)]
        self.assertNotEqual(demonstration_label(first), demonstration_label(other_digest))
        self.assertNotEqual(demonstration_label(first), demonstration_label(other_rows))
        # the same inputs compose the same label; nothing is read from a clock
        self.assertEqual(demonstration_label(first),
                         demonstration_label([dict(entry) for entry in first]))

    def test_the_record_label_is_the_label_of_the_inputs_it_was_built_with(self):
        inputs = [
            {"file": "regional.csv", "sha256": "0123456789abcdef" + "0" * 48, "rows": 7},
            {"file": "nodal.csv", "sha256": "fedcba9876543210" + "0" * 48, "rows": 11},
            # the scorecard and the portfolio carry no row count and are not
            # described as exports
            {"file": "scorecard.json", "sha256": "9" * 64,
             "content_digest": "9" * 64, "version": "price-2.3"},
            {"file": "portfolio-synthetic.json", "sha256": "8" * 64,
             "synthetic": True, "nodes": 12},
        ]
        record = build_impact_record([], [], DEFAULT_MATERIALITY, inputs)
        self.assertEqual(record["label"], demonstration_label(inputs))
        self.assertEqual(record["direction_check"]["label"], record["label"])
        self.assertIn("regional.csv 7 rows sha256 01234567", record["label"])
        self.assertIn("nodal.csv 11 rows sha256 fedcba98", record["label"])
        self.assertNotIn("scorecard.json", record["label"])
        self.assertNotIn("portfolio-synthetic.json", record["label"])

    @staticmethod
    def unlabelled_figures(record):
        """Every peso or volume key that no enclosing block labels."""
        offenders = []

        def walk(node, labelled):
            if isinstance(node, dict):
                here = (labelled or bool(node.get("label"))
                        or bool(node.get("method_demonstration")))
                materiality_line = "rule" in node and "threshold_php" in node
                for key, value in node.items():
                    if isinstance(key, str) and (key.endswith("_php") or key.endswith("_mwh")):
                        if not (here or materiality_line):
                            offenders.append(key)
                    walk(value, here or materiality_line)
            elif isinstance(node, list):
                for item in node:
                    walk(item, labelled)

        walk(record, False)
        return offenders

    def test_every_peso_or_volume_figure_sits_under_the_label(self):
        self.assertEqual(self.unlabelled_figures(self.record()), [])
        stripped = json.loads(json.dumps(self.record()))
        stripped.pop("label")
        stripped["synthetic"] = False
        for node in stripped["nodes"]:
            node.pop("method_demonstration")
            node["synthetic"] = False
        # without the labels the same walk flags the same figures: the check is
        # not vacuous
        self.assertTrue(self.unlabelled_figures(stripped))

    def test_the_record_is_deterministic_and_its_digest_is_its_bytes(self):
        first, second = self.record(), self.record()
        self.assertEqual(record_text(first), record_text(second))
        digest = record_digest(first)
        self.assertEqual(digest, hashlib.sha256(record_text(first).encode("utf-8")).hexdigest())
        self.assertFalse(record_text(first).endswith("\n"))
        json.loads(record_text(first))


class SyntheticPortfolio(unittest.TestCase):
    """The synthetic file is the only holder of volumes and contract prices."""

    def write(self, tmp, payload):
        path = Path(tmp) / "portfolio.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base(self, **overrides):
        entry = {"node": "N01", "region": "LUZON", "contract_price_php_mwh": 5000.0,
                 "uncovered_mwh_by_hour": [1.0] * 24, "synthetic": True}
        entry.update(overrides)
        return {"synthetic": True, "portfolio": [entry]}

    def test_a_labelled_file_loads_its_nodes_and_profile(self):
        with scratch_directory() as tmp:
            path = write_portfolio(Path(tmp) / "portfolio.json")
            positions = load_portfolio(path)
            self.assertEqual([entry.node for entry in positions], ["N01", "N02"])
            self.assertEqual(len(positions[0].uncovered_mwh_by_hour), 24)
            self.assertEqual(positions[1].contract_price_php_mwh, 6000.0)

    def test_a_file_not_labelled_synthetic_is_refused(self):
        with scratch_directory() as tmp:
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, {"portfolio": []}))
            self.assertEqual(caught.exception.code, "NOT_SYNTHETIC")
            payload = self.base()
            payload["synthetic"] = False
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, payload))
            self.assertEqual(caught.exception.code, "NOT_SYNTHETIC")

    def test_a_node_not_labelled_synthetic_is_refused(self):
        with scratch_directory() as tmp:
            payload = self.base()
            payload["portfolio"][0]["synthetic"] = False
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, payload))
            self.assertEqual(caught.exception.code, "NOT_SYNTHETIC")

    def test_a_node_key_that_is_not_an_alias_is_refused(self):
        with scratch_directory() as tmp:
            for bad in ("LUZON_LOAD_1", "N1", "N001", "node-1", ""):
                payload = self.base(node=bad)
                with self.assertRaises(ImpactError) as caught:
                    load_portfolio(self.write(tmp, payload))
                self.assertEqual(caught.exception.code, "NODE_NOT_AN_ALIAS", bad)
        self.assertTrue(ALIAS_PATTERN.match("N01"))
        self.assertTrue(ALIAS_PATTERN.match("N12"))
        self.assertFalse(ALIAS_PATTERN.match("N013"))

    def test_a_duplicate_node_is_refused(self):
        with scratch_directory() as tmp:
            payload = self.base()
            payload["portfolio"].append(dict(payload["portfolio"][0]))
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, payload))
            self.assertEqual(caught.exception.code, "DUPLICATE_NODE")

    def test_a_profile_that_is_not_twenty_four_hours_is_refused(self):
        with scratch_directory() as tmp:
            for profile in ([1.0] * 23, [1.0] * 25, [], "profile"):
                with self.assertRaises(ImpactError) as caught:
                    load_portfolio(self.write(tmp, self.base(uncovered_mwh_by_hour=profile)))
                self.assertEqual(caught.exception.code, "PROFILE_LENGTH", profile)

    def test_a_negative_volume_or_a_bad_contract_price_is_refused(self):
        with scratch_directory() as tmp:
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, self.base(uncovered_mwh_by_hour=[-1.0] + [1.0] * 23)))
            self.assertEqual(caught.exception.code, "NEGATIVE_VOLUME")
            for bad in (0.0, -5.0):
                with self.assertRaises(ImpactError) as caught:
                    load_portfolio(self.write(tmp, self.base(contract_price_php_mwh=bad)))
                self.assertEqual(caught.exception.code, "CONTRACT_PRICE")

    def test_a_missing_region_or_file_is_refused(self):
        with scratch_directory() as tmp:
            payload = self.base()
            payload["portfolio"][0].pop("region")
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(self.write(tmp, payload))
            self.assertEqual(caught.exception.code, "MALFORMED_PORTFOLIO")
            with self.assertRaises(ImpactError) as caught:
                load_portfolio(Path(tmp) / "absent.json")
            self.assertEqual(caught.exception.code, "MISSING_PORTFOLIO")

    def test_a_node_the_scorecard_never_scored_is_refused(self):
        with self.assertRaises(ImpactError) as caught:
            pair_positions([position(node="N99")], [])
        self.assertEqual(caught.exception.code, "NODE_WITHOUT_SERIES")

    def test_the_profile_is_read_at_each_hours_clock_hour(self):
        profile = [float(hour) for hour in range(24)]
        entry = position(profile=profile)
        hours = [datetime(2026, 1, 1, hour) for hour in (0, 5, 23, 5)]
        self.assertEqual(entry.uncovered_mwh(hours), 0.0 + 5.0 + 23.0 + 5.0)


class ImpactArithmetic(unittest.TestCase):
    """Acceptance 1: impact = uncovered MWh by hour times (band − contract price)."""

    def test_one_hour_is_the_volume_times_the_margin(self):
        entry = position(contract=5000.0, profile=[10.0] * 24)
        hours = [datetime(2026, 1, 1, 3)]
        self.assertEqual(entry.impact_php(hours, 5200.0), 2000.0)

    def test_a_day_window_prices_the_whole_profile(self):
        profile = [float(hour + 1) for hour in range(24)]
        entry = position(contract=1000.0, profile=profile)
        rows = impact_rows(entry, [self.band("2026-01-05", "day", p10=900.0, p50=1000.0, p90=1300.0)])
        self.assertEqual(rows[0].window_hours, 24)
        self.assertEqual(rows[0].uncovered_mwh, float(sum(range(1, 25))))
        self.assertEqual(rows[0].p50_php, 0.0)
        self.assertEqual(rows[0].p10_php, -100.0 * sum(range(1, 25)))
        self.assertEqual(rows[0].p90_php, 300.0 * sum(range(1, 25)))

    def test_a_week_window_repeats_the_profile_seven_times(self):
        entry = position(contract=0.0, profile=[1.0] * 24)
        row = impact_rows(entry, [self.band("2026-01-05", "week", p10=1.0, p50=2.0, p90=3.0)])[0]
        self.assertEqual(row.window_hours, 168)
        self.assertEqual(row.uncovered_mwh, 168.0)
        self.assertEqual(row.p50_php, 336.0)

    def test_a_month_window_follows_the_billing_month_length(self):
        entry = position(contract=0.0, profile=[1.0] * 24)
        # billing month 2026-04 is 26 March to 25 April: 31 days; billing month
        # 2025-03 is 26 February to 25 March: 28 days
        long_month = impact_rows(entry, [self.band("2026-03-26", "month", 1.0, 1.0, 1.0)])[0]
        short_month = impact_rows(entry, [self.band("2025-02-26", "month", 1.0, 1.0, 1.0)])[0]
        self.assertEqual(long_month.window_hours, 744)
        self.assertEqual(short_month.window_hours, 672)
        self.assertEqual(long_month.uncovered_mwh, 744.0)
        self.assertEqual(short_month.uncovered_mwh, 672.0)

    def test_a_band_below_the_contract_price_is_a_gain_and_keeps_its_sign(self):
        entry = position(contract=5000.0, profile=[1.0] * 24)
        row = impact_rows(entry, [self.band("2026-01-05", "day", 4000.0, 4500.0, 4900.0)])[0]
        self.assertLess(row.p50_php, 0.0)
        self.assertLess(row.p90_php, 0.0)
        self.assertEqual(row.p50_php, -12000.0)

    def test_the_three_impacts_keep_the_order_of_the_band(self):
        entry = position(contract=5000.0, profile=[3.0] * 24)
        row = impact_rows(entry, [self.band("2026-01-05", "day", 4900.0, 5050.0, 5300.0)])[0]
        self.assertLessEqual(row.p10_php, row.p50_php)
        self.assertLessEqual(row.p50_php, row.p90_php)

    def test_the_settled_value_prices_the_realized_window(self):
        entry = position(contract=5000.0, profile=[2.0] * 24)
        row = impact_rows(entry, [self.band("2026-01-05", "day", 5000.0, 5000.0, 5000.0,
                                            realized=5500.0)])[0]
        self.assertEqual(row.settled_php, 48.0 * 500.0)

    @staticmethod
    def band(origin, horizon, p10, p50, p90, realized=None, baseline="constant", series="N01"):
        from src.price.scorecard import ScoredBand

        return ScoredBand(series=series, kind="nodal", horizon=horizon, origin=origin,
                          label=origin, slice=MARKET, baseline=baseline,
                          realized=p50 if realized is None else realized,
                          point=p50, p10=p10, p50=p50, p90=p90)

    def test_the_rows_are_in_origin_order_and_counted(self):
        entry = position(contract=0.0, profile=[1.0] * 24)
        bands = [self.band(origin, "day", 1.0, 1.0, 1.0)
                 for origin in ("2026-01-01", "2026-01-02", "2026-01-03")]
        rows = impact_rows(entry, bands)
        self.assertEqual([row.origin for row in rows],
                         ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(len(bands_of(bands, "N01", "day", "constant")), 3)
        self.assertEqual(bands_of(bands, "N01", "week", "constant"), ())


class MaterialChanges(unittest.TestCase):
    """The change rule: consecutive scored origins, one stated line."""

    def rows(self, mids, volumes=100.0):
        return [ImpactRow(origin=f"2026-01-{index + 1:02d}", window_hours=24,
                          uncovered_mwh=volumes, p10_php=0.0, p50_php=float(mid),
                          p90_php=0.0, settled_php=0.0)
                for index, mid in enumerate(mids)]

    def test_the_first_origin_is_not_a_change(self):
        summary = classify_changes(self.rows([0.0, 2_000_000.0]), DEFAULT_MATERIALITY)
        self.assertEqual(summary["compared"], 1)
        self.assertEqual(summary["material"], 1)
        self.assertEqual(summary["material_changes"], [["2026-01-02", 2_000_000.0]])

    def test_a_single_origin_has_nothing_to_compare(self):
        summary = classify_changes(self.rows([5.0]), DEFAULT_MATERIALITY)
        self.assertEqual(summary["compared"], 0)
        self.assertEqual(summary["material_changes"], [])
        self.assertIsNone(summary["largest_abs_change_php"])
        self.assertIsNone(summary["largest_change_origin"])

    def test_changes_below_the_line_are_not_material_and_the_sign_is_kept(self):
        summary = classify_changes(self.rows([0.0, 500.0, 200.0, -400.0]), DEFAULT_MATERIALITY)
        self.assertEqual(summary["compared"], 3)
        self.assertEqual(summary["material"], 0)
        self.assertEqual(summary["largest_abs_change_php"], 600.0)
        self.assertEqual(summary["largest_change_origin"], "2026-01-04")

    def test_the_largest_change_and_its_origin_are_recorded(self):
        summary = classify_changes(self.rows([0.0, 3_000_000.0, 3_100_000.0]), DEFAULT_MATERIALITY)
        self.assertEqual(summary["largest_abs_change_php"], 3_000_000.0)
        self.assertEqual(summary["largest_change_origin"], "2026-01-02")
        self.assertEqual(summary["material"], 1)

    def test_the_verdict_is_reached_from_the_stored_numbers(self):
        # the rows are rounded to two decimals, so a change that is a hair below
        # the line stays below it and one at the line is material
        below = self.rows([0.0, MATERIALITY_THRESHOLD_PHP - 0.01])
        at = self.rows([0.0, MATERIALITY_THRESHOLD_PHP])
        self.assertEqual(classify_changes(below, DEFAULT_MATERIALITY)["material"], 0)
        self.assertEqual(classify_changes(at, DEFAULT_MATERIALITY)["material"], 1)

    def test_a_record_classifies_one_change_series_per_baseline_and_pools_them(self):
        series = make_series(start=date(2023, 6, 26), days=430)
        _, bands = bands_for(series, horizons=("day",))
        record = build_impact_record([position(contract=0.0)], bands, DEFAULT_MATERIALITY, inputs=[])
        block = record["nodes"][0]["horizons"][0]
        names = [entry["baseline"] for entry in block["baselines"]]
        self.assertEqual(len(names), 3)
        self.assertEqual(len(set(names)), len(names), "one block per baseline, none merged")
        for entry in block["baselines"]:
            self.assertEqual(entry["origins"], block["origins"])
            self.assertEqual(entry["changes"]["compared"], block["origins"] - 1)
        pooled = sum(entry["changes"]["compared"] for entry in block["baselines"])
        self.assertEqual(record["direction_check"]["changes_compared"], pooled)
        self.assertEqual(block["ap_origins_excluded"], 0)


class BandsAreTheScorecards(unittest.TestCase):
    """Acceptance 1: the bands are the PRICE-2 scorecard's own band levels."""

    def test_the_sink_reports_exactly_the_recorded_origin_rows(self):
        series = make_series(start=date(2023, 6, 26), days=430)
        scorecard, bands = bands_for(series, horizons=("day",))
        self.assertTrue(bands, "the fixture must score at least one origin")
        horizon = scorecard.series[0].horizons[0]
        columns = {name: index for index, name in enumerate(horizon.origin_columns)}
        for band in bands:
            row = next(entry for entry in horizon.origin_rows if entry[0] == band.origin)
            # the record rounds its origin rows to four decimals; the sink carries
            # the value the record rounded
            self.assertEqual(round(band.realized, 4), row[columns["realized"]])
            self.assertEqual(round(band.point, 4), row[columns[band.baseline]])
        self.assertEqual(len(bands), len(horizon.origin_rows) * len(horizon.baselines))

    def test_the_band_levels_reproduce_the_recorded_pinball_losses(self):
        series = make_series(start=date(2023, 6, 26), days=430)
        scorecard, bands = bands_for(series)
        self.assertTrue(bands)
        record = json.loads(scorecard.to_json())
        cells = verify_bands_against_record(bands, record)
        self.assertEqual(cells, 1 * 3 * 3 * 2 * 7)
        # and the identity is a real check: a shifted band no longer matches
        shifted = [dataclasses.replace(band, p90=band.p90 + 1.0) for band in bands]
        with self.assertRaises(ImpactError) as caught:
            verify_bands_against_record(shifted, record)
        self.assertEqual(caught.exception.code, "BANDS_DO_NOT_MATCH")

    def test_the_sink_changes_no_record_byte(self):
        series = make_series(start=date(2023, 6, 26), days=430)
        plain = build_scorecard([series], horizons=("day", "week", "month"), min_fan_samples=3)
        sink = []
        with_sink = build_scorecard([series], horizons=("day", "week", "month"),
                                    min_fan_samples=3, band_sink=sink)
        self.assertEqual(plain.to_json(), with_sink.to_json())
        self.assertEqual(plain.content_digest(), with_sink.content_digest())

    def test_a_crossed_fan_is_released_as_the_sorted_triple(self):
        series = make_series(start=date(2025, 1, 26), days=90,
                             value_of=lambda hour: 100.0)
        scorecard, bands = bands_for(series, horizons=("day",),
                                     baselines=(ConstantBaseline(80.0),))
        self.assertTrue(bands)
        for band in bands:
            self.assertEqual((band.p10, band.p50, band.p90), (80.0, 100.0, 100.0))
        metrics = scorecard.series[0].horizons[0].baselines[0].slices[MARKET]
        recomputed = metrics_from([(band.realized, band.point, band.p10, band.p50, band.p90)
                                   for band in bands])
        self.assertEqual(recomputed.to_dict(), metrics.to_dict())

    def test_the_market_slice_is_the_one_priced_and_ap_is_counted_apart(self):
        # the series starts two years before the administered day, so the
        # seasonal baseline can serve that origin and the day really scores
        ap_hours = set(billing_day_hours(date(2024, 4, 1)))
        series = make_series(start=date(2022, 6, 26), days=700, ap_hours=ap_hours, flagged=True)
        scorecard, bands = bands_for(series, horizons=("day",))
        market = bands_of(bands, "N01", "day", "persistence", MARKET)
        ap = bands_of(bands, "N01", "day", "persistence", AP)
        self.assertTrue(ap, "the fixture carries an administered-pricing day")
        record = build_impact_record([position()], bands, DEFAULT_MATERIALITY, inputs=[])
        block = record["nodes"][0]["horizons"][0]
        self.assertEqual(block["origins"], len(market))
        self.assertEqual(block["ap_origins_excluded"], len(ap))
        self.assertNotIn("2024-04-01", [band.origin for band in market])
        self.assertIn("2024-04-01", [band.origin for band in ap])
        self.assertFalse({band.origin for band in ap} & {band.origin for band in market})


class NoPortfolioByteInGit(unittest.TestCase):
    """Acceptance 4: no volume, contract price or node name enters the tree."""

    def test_only_aliases_are_written_into_the_record(self):
        record = DemonstrationLabel().record()
        for node in record["nodes"]:
            self.assertTrue(ALIAS_PATTERN.match(node["node"]), node["node"])

    def test_the_runner_refuses_to_write_inside_the_repository_tree(self):
        cli = load_cli("impact")
        # the guard runs before any input is read, so the refusal costs nothing
        for path in ("docs/work/price-outlook/impact-record.json",
                     "src/price/impact-record.json", "impact-record.json"):
            stdout, stderr = io.StringIO(), io.StringIO()
            # the materiality line prints before the guard; keep it off the console
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = cli.main(["--portfolio", ".local/portfolio-synthetic.json",
                                   "--scorecard", ".local/price/scorecard.json",
                                   "--regional", ".local/price/lwap_final_hourly.csv",
                                   "--nodal", ".local/price/portfolio_nodal_hourly_deid.csv",
                                   "--out", path])
            self.assertEqual(status, 2, path)
            self.assertIn("WRITE_INTO_REPOSITORY", stderr.getvalue())
            self.assertFalse((ROOT / path).exists(), path)

    def test_a_scratch_path_outside_the_tree_is_allowed(self):
        with scratch_directory() as tmp:
            cli = load_cli("impact")
            resolved = cli.refuse_output_inside_the_tree(Path(tmp) / "impact.json")
            self.assertEqual(resolved, (Path(tmp) / "impact.json").resolve())

    def test_the_label_is_derived_from_the_inputs_and_names_no_dataset_literal(self):
        self.assertIn("method demonstration", SYNTHETIC_STATEMENT)
        self.assertNotIn("pre-backfill", SYNTHETIC_STATEMENT)
        inputs = [{"file": "lwap_final_hourly.csv", "sha256": "3b3b0b66" + "0" * 56,
                   "rows": 184036}]
        label = demonstration_label(inputs)
        self.assertIn("method demonstration", label)
        self.assertIn("lwap_final_hourly.csv 184036 rows sha256 3b3b0b66", label)
        self.assertNotIn("pre-backfill", label)
        # with no verified input there is nothing to describe: the fixed
        # sentence is the whole label
        self.assertEqual(demonstration_label([]),
                         f"{SYNTHETIC_STATEMENT}; no exported input verified in this run")


class CommandLine(unittest.TestCase):
    """The runner end to end on a small fixture: exports in, impact record out."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = scratch_directory("impact1-cli-")
        cls.addClassCleanup(cls.tmp.cleanup)
        directory = cls.tmp.name
        cls.regional, cls.nodal, cls.digests = write_exports(directory)
        cls.portfolio = write_portfolio(Path(directory) / "portfolio-synthetic.json")
        cls.scorecard_path = Path(directory) / "scorecard.json"
        baselines = load_cli("baselines")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = baselines.main([
                "--regional", str(cls.regional), "--nodal", str(cls.nodal),
                "--digests", str(cls.digests), "--out", str(cls.scorecard_path),
                "--summary-series", "none", "--min-fan-samples", "3",
            ])
        assert status == 0, "the fixture scorecard must build"
        # one run serves every test that only needs a successful record; the
        # tests that need a second run (two stated lines, the refusals) pay for
        # their own
        cls.out = Path(directory) / "impact.json"
        cls.status, cls.text, cls.err = cls.run_impact(cls.out)

    @classmethod
    def run_impact(cls, out=None, extra=()):
        cli = load_cli("impact")
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = ["--portfolio", str(cls.portfolio), "--scorecard", str(cls.scorecard_path),
                "--regional", str(cls.regional), "--nodal", str(cls.nodal),
                "--digests", str(cls.digests), *extra]
        if out is not None:
            argv += ["--out", str(out)]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(argv)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_it_writes_a_record_whose_digest_matches_its_bytes(self):
        out, text, err = self.out, self.text, self.err
        self.assertEqual(self.status, 0, err)
        payload = out.read_bytes()
        self.assertFalse(payload.endswith(b"\n"))
        digest = hashlib.sha256(payload).hexdigest()
        self.assertIn(f"content_digest {digest}", text)
        record = json.loads(payload.decode("utf-8"))
        self.assertEqual(record["kind"], KIND)
        self.assertEqual(record["version"], VERSION)
        self.assertEqual(record["materiality"]["threshold_php"], MATERIALITY_THRESHOLD_PHP)
        self.assertEqual([node["node"] for node in record["nodes"]], ["N01", "N02"])
        self.assertIn("reproduced from the exported bytes", text)
        self.assertIn("metric cells recomputed", text)

    def test_the_printed_composed_label_names_the_verified_exports(self):
        self.assertEqual(self.status, 0, self.err)
        record = json.loads(self.out.read_text(encoding="utf-8"))
        label = record["label"]
        # the runner prints the record's own label, composed from this run's
        # verified exports
        self.assertIn(f"label: {label}", self.text)
        exports = [entry for entry in record["inputs"] if "rows" in entry]
        self.assertEqual([entry["file"] for entry in exports],
                         ["lwap_final_hourly.csv", "portfolio_nodal_hourly_deid.csv"])
        for entry in exports:
            self.assertIn(entry["file"], label)
            self.assertIn(f"{entry['rows']} rows", label)
            self.assertIn(entry["sha256"][:8], label)
        self.assertNotIn("pre-backfill", self.text)

    def test_the_record_prices_every_horizon_of_every_node(self):
        self.assertEqual(self.status, 0, self.err)
        record = json.loads(self.out.read_text(encoding="utf-8"))
        for node in record["nodes"]:
            self.assertEqual([horizon["horizon"] for horizon in node["horizons"]], list(HORIZONS))
            for horizon in node["horizons"]:
                self.assertGreater(horizon["origins"], 0, (node["node"], horizon["horizon"]))
                for block in horizon["baselines"]:
                    self.assertEqual(block["origins"], horizon["origins"])
                    self.assertEqual(block["changes"]["compared"], horizon["origins"] - 1)
                    self.assertGreater(block["latest"]["uncovered_mwh"], 0)

    def test_a_change_is_classified_against_the_line_it_was_given(self):
        # the same impact rows, two stated lines: nothing reaches a line above
        # every movement, and a great deal reaches a line of one peso
        none_out = Path(self.tmp.name) / "impact3-none.json"
        all_out = Path(self.tmp.name) / "impact3-all.json"
        for out, threshold in ((none_out, 1e12), (all_out, 1.0)):
            status, _, err = self.run_impact(out, extra=["--threshold", repr(threshold)])
            self.assertEqual(status, 0, err)
        unreachable = json.loads(none_out.read_text(encoding="utf-8"))["direction_check"]
        reachable = json.loads(all_out.read_text(encoding="utf-8"))["direction_check"]
        self.assertEqual(unreachable["material_changes"], 0)
        self.assertEqual(unreachable["nodes_with_a_material_change"], 0)
        self.assertGreater(reachable["material_changes"], 0)
        self.assertEqual(unreachable["changes_compared"], reachable["changes_compared"])

    def test_a_tampered_scorecard_is_refused(self):
        tampered = Path(self.tmp.name) / "tampered.json"
        tampered.write_text(self.scorecard_path.read_text(encoding="utf-8").rstrip() + " ",
                            encoding="utf-8")
        cli = load_cli("impact")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(["--portfolio", str(self.portfolio), "--scorecard", str(tampered),
                               "--regional", str(self.regional), "--nodal", str(self.nodal),
                               "--digests", str(self.digests)])
        self.assertEqual(status, 2)
        self.assertIn("SCORECARD_NOT_REPRODUCED", stderr.getvalue())

    def test_a_file_that_is_not_a_scorecard_is_refused(self):
        for payload, code in ((b"[]", "NOT_A_SCORECARD"),
                              (b'{"kind": "price-baseline-scorecard"}', "MALFORMED_SCORECARD"),
                              (b"{not json", "MALFORMED_SCORECARD")):
            broken = Path(self.tmp.name) / "broken.json"
            broken.write_bytes(payload)
            cli = load_cli("impact")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = cli.main(["--portfolio", str(self.portfolio),
                                   "--scorecard", str(broken),
                                   "--regional", str(self.regional), "--nodal", str(self.nodal),
                                   "--digests", str(self.digests)])
            self.assertEqual(status, 2, payload)
            self.assertIn(code, stderr.getvalue(), payload)

    def test_a_scorecard_from_other_bytes_is_refused_by_digest(self):
        other = Path(self.tmp.name) / "other.csv"
        other.write_text("a,b\n", encoding="utf-8")
        cli = load_cli("impact")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(["--portfolio", str(self.portfolio),
                               "--scorecard", str(self.scorecard_path),
                               "--regional", str(other), "--nodal", str(self.nodal),
                               "--digests", str(self.digests)])
        self.assertEqual(status, 2)
        self.assertIn("DIGEST_NOT_RECORDED", stderr.getvalue())

    def test_a_missing_portfolio_is_refused_before_any_scoring(self):
        status, text, err = self.run_impact(extra=["--portfolio", str(Path(self.tmp.name) / "no.json")])
        self.assertEqual(status, 2)
        self.assertIn("MISSING_PORTFOLIO", err)

    def test_the_summary_prints_one_line_per_node_and_horizon(self):
        text = self.text
        self.assertEqual(self.status, 0, self.err)
        for node in ("N01", "N02"):
            self.assertIn(node, text)
        for horizon in HORIZONS:
            self.assertIn(horizon, text)
        self.assertIn("direction check IMPACT-1:", text)


class RealExports(unittest.TestCase):
    """The real exports and the real synthetic portfolio.

    These cases are skipped when the PRICE-1 export or the synthetic portfolio is
    not linked into ``.local/price`` (neither ever enters Git); nothing else in
    this file reads them.
    """

    @classmethod
    def setUpClass(cls):
        missing = [path for path in (REGIONAL_CSV, NODAL_CSV, DIGESTS_JSON, PORTFOLIO_JSON,
                                     SCORECARD_JSON) if not path.exists()]
        if missing:
            raise unittest.SkipTest(f"not linked under .local/price: {[path.name for path in missing]}")
        cls.digests = json.loads(DIGESTS_JSON.read_text(encoding="utf-8"))
        from src.price.series import verify_inputs

        cls.inputs = verify_inputs([REGIONAL_CSV, NODAL_CSV], cls.digests)
        cls.record_file = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
        cls.portfolio = load_portfolio(PORTFOLIO_JSON)
        series = list(load_regional(REGIONAL_CSV)) + list(load_nodal(NODAL_CSV))
        bands = []
        cls.scorecard = build_scorecard(
            series, horizons=tuple(entry["horizon"] for entry in cls.record_file["series"][0]["horizons"]),
            inputs=cls.inputs, embargo_hours=cls.record_file["embargo_hours"],
            min_fan_samples=cls.record_file["min_fan_samples"], band_sink=bands,
        )
        cls.bands = bands
        cls.impact = build_impact_record(
            cls.portfolio, bands, DEFAULT_MATERIALITY, cls.inputs,
            baselines=tuple(entry["name"] for entry in cls.record_file["baselines"]),
        )

    def test_the_replay_reproduces_the_record_bytes(self):
        self.assertEqual(self.scorecard.content_digest(), digest_file(SCORECARD_JSON))
        self.assertEqual(self.record_file["version"], self.scorecard.version)

    def test_the_band_levels_reproduce_the_recorded_metrics(self):
        cells = verify_bands_against_record(self.bands, self.record_file)
        self.assertEqual(cells, len(self.record_file["series"]) * 3 * 3 * 2 * 7)

    def test_the_real_portfolio_pairs_one_node_to_one_series(self):
        self.assertEqual([entry.node for entry in self.portfolio],
                         [f"N{n:02d}" for n in range(1, 13)])
        pair_positions(self.portfolio, self.bands)
        self.assertEqual([node["node"] for node in self.impact["nodes"]],
                         [entry.node for entry in self.portfolio])

    def test_every_node_carries_the_price_band_and_the_change_count(self):
        for node in self.impact["nodes"]:
            self.assertTrue(node["method_demonstration"])
            self.assertGreater(node["contract_price_php_mwh"], 0)
            for horizon in node["horizons"]:
                if horizon["horizon"] in ("day", "week"):
                    self.assertGreater(horizon["origins"], 0, (node["node"], horizon["horizon"]))
                for block in horizon["baselines"]:
                    self.assertEqual(block["origins"], horizon["origins"])
                    if horizon["origins"] == 0:
                        self.assertEqual(block["changes"]["compared"], 0)
                        self.assertIsNone(block["latest"])
                        continue
                    self.assertEqual(block["changes"]["compared"], block["origins"] - 1)
                    latest = block["latest"]
                    self.assertLessEqual(latest["p10_php"], latest["p50_php"])
                    self.assertLessEqual(latest["p50_php"], latest["p90_php"])

    def test_the_record_is_reproducible_and_its_digest_is_its_bytes(self):
        again = build_impact_record(
            self.portfolio, self.bands, DEFAULT_MATERIALITY, self.inputs,
            baselines=tuple(entry["name"] for entry in self.record_file["baselines"]),
        )
        self.assertEqual(record_text(again), record_text(self.impact))
        self.assertEqual(record_digest(again), record_digest(self.impact))

    def test_the_latest_impact_recomputes_by_hand_from_the_band_and_the_profile(self):
        """An independent walk of the arithmetic: window hours, profile, margin."""
        node = self.impact["nodes"][0]
        horizon = node["horizons"][0]
        block = horizon["baselines"][0]
        latest = block["latest"]
        position = self.portfolio[0]
        band = next(band for band in self.bands
                    if band.series == node["node"] and band.horizon == horizon["horizon"]
                    and band.baseline == block["baseline"] and band.slice == MARKET
                    and band.origin == latest["origin"])
        window = window_for(band.horizon, date.fromisoformat(band.origin))
        volume = 0.0
        margin = band.p50 - position.contract_price_php_mwh
        manual = 0.0
        for hour in window.hours:
            uncovered = position.uncovered_mwh_by_hour[hour.hour]
            volume += uncovered
            manual += uncovered * margin
        self.assertAlmostEqual(latest["uncovered_mwh"], volume, places=6)
        self.assertAlmostEqual(latest["p50_php"], round(manual, 2), places=2)
        self.assertAlmostEqual(latest["settled_php"],
                               round(volume * (band.realized - position.contract_price_php_mwh), 2),
                               places=2)

    def test_the_settled_value_matches_the_records_own_realized_number(self):
        record_series = {entry["key"]: entry for entry in self.record_file["series"]}
        checked = 0
        for node in self.impact["nodes"][:3]:
            for horizon in node["horizons"][:1]:
                for block in horizon["baselines"][:1]:
                    latest = block["latest"]
                    if latest is None:
                        continue
                    rows = record_series[node["node"]]["horizons"][0]["origin_rows"]
                    columns = {name: index for index, name in enumerate(rows["columns"])}
                    row = next(entry for entry in rows["rows"] if entry[0] == latest["origin"])
                    realized = row[columns["realized"]]
                    position = next(entry for entry in self.portfolio if entry.node == node["node"])
                    expected = round(latest["uncovered_mwh"]
                                     * (realized - position.contract_price_php_mwh), 2)
                    # the record rounds its origin values to four decimals while
                    # the impact uses the value the record rounded, so the check
                    # is exact to the rounding of the realized price
                    tolerance = latest["uncovered_mwh"] * 5e-5 + 0.01
                    self.assertAlmostEqual(latest["settled_php"], expected, delta=tolerance)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_the_label_is_composed_from_the_verified_inputs(self):
        label = self.impact["label"]
        self.assertEqual(label, demonstration_label(self.inputs))
        self.assertNotIn("pre-backfill", label)
        for entry in self.inputs:
            self.assertIn(entry["file"], label)
            self.assertIn(f"{entry['rows']} rows", label)
            self.assertIn(entry["sha256"][:8], label)

    def test_the_direction_check_is_recorded_as_counts(self):
        check = self.impact["direction_check"]
        self.assertEqual(check["id"], "IMPACT-1")
        self.assertGreater(check["changes_compared"], 0)
        self.assertLessEqual(check["material_changes"], check["changes_compared"])
        self.assertLessEqual(check["nodes_with_a_material_change"], len(self.portfolio))


class StdlibOnly(unittest.TestCase):
    def imported_roots(self, path):
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_impact_module_imports_only_the_standard_library_and_its_siblings(self):
        for root in self.imported_roots(ROOT / "src/price/impact.py"):
            self.assertTrue(root in sys.stdlib_module_names or root == "__future__"
                            or root.startswith("."), root)

    def test_the_runner_imports_only_the_standard_library_and_this_package(self):
        for root in self.imported_roots(ROOT / "scripts/price/impact.py"):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)

    def test_the_test_module_itself_stays_offline(self):
        for root in self.imported_roots(Path(__file__)):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)


if __name__ == "__main__":
    unittest.main()
