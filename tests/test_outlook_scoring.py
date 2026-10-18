"""SCORE-1: score an issued outlook against the settled final series, offline.

What is proven here, all of it on labelled synthetic fixtures under a scratch root
(with the workspace fallback a review sandbox needs), never against the real
runtime archive:

* a settled window scores; the receipt validates against the archive's own
  ``validate_receipt`` and its link rules, appends once and a second append for
  the same ``(outlook_id, final_series_version)`` pair is refused by the store;
* a window that has not settled is refused ``WINDOW_NOT_SETTLED`` — either
  because ``scored_at`` precedes the horizon end or because the final export's
  last hour stops before it;
* a values file whose digest, row count or shape does not match the outlook's
  record is refused, and one that does not cover the horizon exactly is refused
  rather than partly scored;
* marked intervals — administered-pricing months and irregular days, the marks
  the PRICE-2 scorecard uses — land in ``coverage.skipped`` with their reasons
  and are never filled;
* the metrics equal ``src.price.scorecard.metrics_from`` on the same
  ``(realized, point, p10, p50, p90)`` rows, for a zero-width band (the first
  vintage's mid-only values) and for an explicit per-hour band;
* the command runs end to end, including ``--dry-run``, refuses to run without
  ``--final-series-version``, and never issues an outlook or writes an
  attribution.

On the real archive, both November 2026 vintages are refused today with
``WINDOW_NOT_SETTLED`` and the archive's ``verify()`` still reads 2 outlooks, 0
receipts, 0 attributions and no problems: this task appends nothing to
``.local/outlook-archive``.

Offline and stdlib-only: no model, network, credential or clock in the module;
the only clock reading is the command's printed default when ``--scored-at`` is
omitted.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.outlook.records import (  # noqa: E402
    OutlookArchive,
    OutlookError,
    build_outlook,
    receipt_stem,
    validate_receipt,
)
from src.outlook.scoring import (  # noqa: E402
    LOCAL_UTC_OFFSET,
    MESSAGES,
    ScoringError,
    score_outlook,
)
from src.price.scorecard import METRIC_DECIMALS, metrics_from  # noqa: E402
from src.price.series import (  # noqa: E402
    HOUR,
    REGIONAL_KEYS,
    billing_month_label,
    billing_month_of,
    digest_file,
    load_digests,
    load_regional,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
SCRIPT = ROOT / "scripts" / "outlook" / "score.py"
REAL_ARCHIVE = ROOT / ".local" / "outlook-archive"
REAL_EXPORT = ROOT / ".local" / "price" / "lwap_final_hourly.csv"
REAL_DIGESTS = ROOT / ".local" / "price" / "digests.json"
INTERPRETER = Path("/usr/bin/python3") if Path("/usr/bin/python3").exists() else Path(sys.executable)

#: The fixture's week: local 2026-03-23 00:00 to 2026-03-30 00:00. Its first
#: three days lie in the market billing month 2026-03; its last four lie in
#: 2026-04, the recorded all-administered month. One market day is marked
#: irregular by giving one of its hours six five-minute intervals instead of
#: twelve, so the fixture exercises both skip reasons at once.
HORIZON_START = "2026-03-22T16:00:00Z"   # local 2026-03-23T00:00
HORIZON_END = "2026-03-29T16:00:00Z"     # local 2026-03-30T00:00
ISSUED_AT = "2026-03-20T00:00:00Z"
CUTOFF = "2026-03-01T00:00:00Z"
FINAL_VERSION = "fixture-final-bmonth-2026-03"
SCORED_AT = "2026-04-01T00:00:00Z"
EXPORT_FIRST = datetime(2026, 2, 26, 0)
EXPORT_LAST = datetime(2026, 4, 25, 23)
IRREGULAR_DAY = "2026-03-24"
IRREGULAR_HOUR = datetime(2026, 3, 24, 12)
AP_MONTH = "2026-04"
METRIC_NAMES = ("bias", "mae", "rmse", "pinball_p10", "pinball_p50", "pinball_p90")


def scratch_directory(prefix="score1-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path.

    A review sandbox may mount no writable system temporary directory while the
    workspace itself stays writable; the fallback keeps these tests runnable
    there. It sits under the ignored ``.local/`` and is cleaned up the same way
    as the primary path.
    """
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def local_hours(start_utc, end_utc):
    """The whole naive local hours of one UTC half-open horizon."""
    start = datetime.fromisoformat(start_utc.replace("Z", "+00:00")) + LOCAL_UTC_OFFSET
    end = datetime.fromisoformat(end_utc.replace("Z", "+00:00")) + LOCAL_UTC_OFFSET
    start, end = start.replace(tzinfo=None), end.replace(tzinfo=None)
    count = int((end - start).total_seconds() // 3600)
    return tuple(start + HOUR * step for step in range(count))


def mean_for(region, hour):
    """One deterministic synthetic price: a region base plus a clock pattern."""
    base = {"SYSTEM": 1000.0, "CLUZ": 900.0, "CVIS": 950.0, "CMIN": 980.0}
    return base[region] + hour.hour * 0.5 + hour.day * 0.25


def write_export(path, *, last=EXPORT_LAST, merged=(IRREGULAR_HOUR,), missing=()):
    """Write a synthetic regional export covering complete billing months.

    Four regions are written because the reader requires all of them. An hour in
    ``merged`` carries six intervals instead of twelve, which makes its whole day
    irregular under the scorecard's marks; an hour in ``missing`` has no row at
    all.
    """
    lines = ["byear,bmonth,region_name,hour_start,n5,lwap_mean"]
    hour = EXPORT_FIRST
    while hour <= last:
        if hour not in missing:
            year, month = billing_month_of(hour)
            for region in REGIONAL_KEYS:
                intervals = 6 if hour in merged else 12
                lines.append("%d,%d,%s,%s,%d,%.6f" % (
                    year, month, region, hour.isoformat(), intervals, mean_for(region, hour)))
        hour += HOUR
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def values_document(hours, *, band=False, series="SYSTEM"):
    """The outlook's values file: one mid value per hour, optionally a p10/p50/p90 band."""
    rows = []
    for index, hour in enumerate(hours):
        value = 1010.25 + index * 0.75
        row = {"hour_start": hour.isoformat(), "value": value}
        if band:
            row["p10"] = value - 4.0
            row["p50"] = value + 0.5
            row["p90"] = value + 9.0
        rows.append(row)
    return {
        "billing_month": billing_month_label(*billing_month_of(hours[0])) if hours else "",
        "horizon": "week",
        "series": series,
        "source": "fixture_regional.csv",
        "hours": rows,
    }


def outlook_fields(values_ref):
    """The named fields of the fixture outlook, with its values reference applied."""
    return dict(
        outlook_id="outlook-fixture-week-system",
        issued_at=ISSUED_AT,
        information_cutoff=CUTOFF,
        horizon={"label": "week", "start": HORIZON_START, "end": HORIZON_END},
        target_series_ref={"table": "grid_raw.ext_pmr_lwap_final", "column": "lwap",
                           "version": FINAL_VERSION},
        inputs=[{"name": "fixture_regional.csv", "digest": DIGEST_A}],
        assumption_ids=["availability:syn-bay-unit-2", "threshold:fixture_cut"],
        model_version="fixture seasonal average",
        values_ref=values_ref,
        issuer="SCORE-1 fixture",
        synthetic=True,
    )


class Fixture:
    """A scratch archive, a synthetic outlook, its values file and a synthetic export."""

    def __init__(self, test, *, band=False, document=None, export_last=EXPORT_LAST,
                 merged=(IRREGULAR_HOUR,), missing=(), hours=None, rows=None,
                 values_digest=None, values_series="SYSTEM", outlook_overrides=None):
        self.temp = scratch_directory()
        test.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = OutlookArchive(self.root / "outlook-archive")
        self.horizon_hours = (tuple(hours) if hours is not None
                              else local_hours(HORIZON_START, HORIZON_END))
        if document is None:
            document = values_document(self.horizon_hours, band=band, series=values_series)
        self.values_path = self.root / "values.json"
        self.values_path.write_text(json.dumps(document), encoding="utf-8")
        digest = digest_file(self.values_path) if values_digest is None else values_digest
        values_ref = {
            "path_hint": str(self.values_path),
            "sha256": digest,
            "rows": len(document["hours"]) if rows is None else rows,
        }
        fields = outlook_fields(values_ref)
        if outlook_overrides:
            fields.update(outlook_overrides)
        self.outlook = self.archive.issue(build_outlook(**fields))
        self.export_path = self.root / "fixture_regional.csv"
        write_export(self.export_path, last=export_last, merged=merged, missing=missing)
        self.digests = {str(self.export_path): digest_file(self.export_path)}
        self.digests_path = self.root / "digests.json"
        self.digests_path.write_text(json.dumps(self.digests), encoding="utf-8")

    def score(self, **overrides):
        arguments = dict(scored_at=SCORED_AT, final_series_version=FINAL_VERSION)
        arguments.update(overrides)
        return score_outlook(self.outlook, self.values_path, self.export_path,
                             self.digests, **arguments)


def refused(case, build):
    """The code of the ScoringError a build raises; fails if it raises nothing else."""
    with case.assertRaises(ScoringError) as caught:
        build()
    return caught.exception.code


def refused_outlook(case, build):
    """The code of the OutlookError a build raises."""
    with case.assertRaises(OutlookError) as caught:
        build()
    return caught.exception.code


def fixture_skipped(hour):
    """The fixture's two marks, computed independently of the module under test."""
    return (hour.date().isoformat() == IRREGULAR_DAY
            or billing_month_label(*billing_month_of(hour)) == AP_MONTH)


def expected_pairs(fixture, *, band=False):
    """The ``(realized, point, p10, p50, p90)`` rows the fixture's scored hours give."""
    document = json.loads(fixture.values_path.read_text(encoding="utf-8"))
    points = {datetime.fromisoformat(row["hour_start"]): row for row in document["hours"]}
    series = next(entry for entry in load_regional(fixture.export_path)
                  if entry.key == document["series"])
    pairs = []
    for hour in fixture.horizon_hours:
        if fixture_skipped(hour):
            continue
        row = points[hour]
        point = float(row["value"])
        if band:
            p10, p50, p90 = sorted(float(row[key]) for key in ("p10", "p50", "p90"))
        else:
            p10 = p50 = p90 = point
        pairs.append((series.rows[hour].mean, point, p10, p50, p90))
    return pairs


def assert_metrics_equal(case, row, metrics):
    """The receipt row's six numbers equal one scorecard ``Metrics`` to its stored decimals."""
    case.assertEqual(row["intervals"], metrics.count)
    for name in METRIC_NAMES:
        case.assertEqual(row[name], format(getattr(metrics, name) + 0.0,
                                           ".%df" % METRIC_DECIMALS))


class SettledWindow(unittest.TestCase):
    """One settled window: the receipt, its links, the store's once-only rule."""

    def setUp(self):
        self.fixture = Fixture(self)

    def test_a_settled_window_scores_and_appends_once(self):
        receipt = self.fixture.score()
        validate_receipt(receipt)
        self.assertEqual(receipt["outlook_id"], self.fixture.outlook["outlook_id"])
        self.assertEqual(receipt["outlook_digest"], self.fixture.outlook["content_digest"])
        self.assertEqual(receipt["scored_at"], SCORED_AT)
        self.assertEqual(receipt["window"], {"start": HORIZON_START, "end": HORIZON_END})
        self.assertEqual(receipt["final_series_version"], FINAL_VERSION)
        self.assertEqual(receipt["final_series_digest"],
                         digest_file(self.fixture.export_path))
        self.assertIs(True, receipt["synthetic"])
        stored = self.fixture.archive.append_receipt(receipt)
        self.assertEqual(stored, receipt)
        self.assertEqual(self.fixture.archive.receipts(), (receipt,))
        report = self.fixture.archive.verify()
        self.assertEqual((report["outlooks"], report["receipts"], report["attributions"]),
                         (1, 1, 0))
        self.assertEqual(report["problems"], [])
        self.assertEqual(refused_outlook(
            self, lambda: self.fixture.archive.append_receipt(receipt)), "RECEIPT_DUPLICATE")
        self.assertEqual(len(self.fixture.archive.receipts()), 1)

    def test_the_receipt_s_window_is_the_whole_horizon_and_lies_inside_it(self):
        receipt = self.fixture.score()
        start = datetime.fromisoformat(receipt["window"]["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(receipt["window"]["end"].replace("Z", "+00:00"))
        scored = datetime.fromisoformat(receipt["scored_at"].replace("Z", "+00:00"))
        self.assertLess(start, end)
        self.assertGreaterEqual(scored, end)
        self.assertEqual(receipt["window"]["start"], self.fixture.outlook["horizon"]["start"])
        self.assertEqual(receipt["window"]["end"], self.fixture.outlook["horizon"]["end"])

    def test_the_receipt_stores_one_market_row_for_the_horizon_label(self):
        receipt = self.fixture.score()
        self.assertEqual(len(receipt["metrics"]), 1)
        row = receipt["metrics"][0]
        self.assertEqual(row["horizon"], "week")
        self.assertEqual(row["slice"], "market")
        self.assertEqual(row["intervals"], 48)


class Settlement(unittest.TestCase):
    """The window is scored only once it has settled."""

    def setUp(self):
        self.fixture = Fixture(self)

    def test_scored_at_before_the_window_end_is_refused(self):
        self.assertEqual(refused(self, lambda: self.fixture.score(
            scored_at="2026-03-29T15:00:00Z")), "WINDOW_NOT_SETTLED")
        self.assertEqual(self.fixture.archive.receipts(), ())

    def test_scored_at_at_the_window_end_is_accepted(self):
        receipt = self.fixture.score(scored_at=HORIZON_END)
        self.assertEqual(receipt["scored_at"], HORIZON_END)

    def test_an_export_that_stops_before_the_window_end_is_refused(self):
        fixture = Fixture(self, export_last=datetime(2026, 3, 28, 23))
        self.assertEqual(refused(self, fixture.score), "WINDOW_NOT_SETTLED")
        self.assertEqual(fixture.archive.receipts(), ())

    def test_an_unreadable_export_is_refused(self):
        self.assertEqual(refused(self, lambda: score_outlook(
            self.fixture.outlook, self.fixture.values_path,
            self.fixture.root / "no-such-export.csv", self.fixture.digests,
            scored_at=SCORED_AT, final_series_version=FINAL_VERSION)),
            "EXPORT_UNREADABLE")

    def test_an_export_without_a_recorded_digest_is_refused(self):
        self.assertEqual(refused(self, lambda: score_outlook(
            self.fixture.outlook, self.fixture.values_path, self.fixture.export_path, {},
            scored_at=SCORED_AT, final_series_version=FINAL_VERSION)),
            "EXPORT_DIGEST_NOT_RECORDED")

    def test_an_export_that_does_not_match_its_digest_is_refused(self):
        with self.fixture.export_path.open("a", encoding="utf-8") as handle:
            handle.write("2026,03,SYSTEM,2026-03-30T00:00:00,12,1.0\n")
        self.assertEqual(refused(self, self.fixture.score), "EXPORT_DIGEST_MISMATCH")


class Values(unittest.TestCase):
    """The values file is checked against the outlook's record before it is read."""

    def setUp(self):
        self.fixture = Fixture(self)

    def test_a_values_file_whose_digest_does_not_match_is_refused(self):
        fixture = Fixture(self, values_digest=DIGEST_B)
        self.assertEqual(refused(self, fixture.score), "VALUES_DIGEST_MISMATCH")

    def test_the_row_count_must_match_the_record(self):
        fixture = Fixture(self, rows=len(local_hours(HORIZON_START, HORIZON_END)) + 1)
        self.assertEqual(refused(self, fixture.score), "VALUES_ROWS_MISMATCH")

    def test_the_values_must_cover_the_horizon_exactly(self):
        hours = local_hours(HORIZON_START, HORIZON_END)[:-1]
        fixture = Fixture(self, hours=hours)
        self.assertEqual(refused(self, fixture.score), "VALUES_INCOMPLETE")

    def test_an_unsupported_series_is_refused(self):
        fixture = Fixture(self, values_series="N01")
        self.assertEqual(refused(self, fixture.score), "SERIES_UNSUPPORTED")

    def test_an_outlook_on_another_target_series_is_refused(self):
        fixture = Fixture(self, outlook_overrides={
            "target_series_ref": {"table": "grid_raw.ext_pmr_settlement_prices",
                                  "column": "lmp", "version": "fixture"}})
        self.assertEqual(refused(self, fixture.score), "SERIES_UNSUPPORTED")

    def test_a_row_without_its_required_keys_is_refused(self):
        document = values_document(local_hours(HORIZON_START, HORIZON_END))
        del document["hours"][0]["value"]
        fixture = Fixture(self, document=document)
        self.assertEqual(refused(self, fixture.score), "VALUES_SHAPE")

    def test_a_row_with_a_partial_band_is_refused(self):
        document = values_document(local_hours(HORIZON_START, HORIZON_END))
        document["hours"][0]["p10"] = 1.0
        document["hours"][0]["p50"] = 2.0
        fixture = Fixture(self, document=document)
        self.assertEqual(refused(self, fixture.score), "VALUES_SHAPE")

    def test_a_duplicate_hour_is_refused(self):
        document = values_document(local_hours(HORIZON_START, HORIZON_END))
        document["hours"][1]["hour_start"] = document["hours"][0]["hour_start"]
        fixture = Fixture(self, document=document)
        self.assertEqual(refused(self, fixture.score), "VALUES_SHAPE")

    def test_a_non_finite_value_is_refused(self):
        document = values_document(local_hours(HORIZON_START, HORIZON_END))
        document["hours"][0]["value"] = float("nan")
        fixture = Fixture(self, document=document)
        self.assertEqual(refused(self, fixture.score), "VALUES_SHAPE")

    def test_an_unreadable_values_file_is_refused(self):
        self.fixture.values_path.unlink()
        self.assertEqual(refused(self, self.fixture.score), "VALUES_UNREADABLE")

    def test_an_horizon_that_is_not_whole_local_hours_is_refused(self):
        fixture = Fixture(self, outlook_overrides={
            "horizon": {"label": "week", "start": "2026-03-22T16:30:00Z",
                        "end": HORIZON_END}})
        self.assertEqual(refused(self, fixture.score), "WINDOW_UNALIGNED")


class Band(unittest.TestCase):
    """The band: an explicit per-hour p10/p50/p90 when the values carry one."""

    def test_an_explicit_band_is_read_and_scored(self):
        fixture = Fixture(self, band=True)
        receipt = fixture.score()
        metrics = metrics_from(expected_pairs(fixture, band=True))
        assert_metrics_equal(self, receipt["metrics"][0], metrics)
        # The pinball terms are the band's, not the zero-width point's: scoring the
        # same hours with the mid value at all three quantiles gives other numbers.
        zero = metrics_from(expected_pairs(fixture))
        for name in ("pinball_p10", "pinball_p50", "pinball_p90"):
            self.assertNotEqual(format(getattr(metrics, name), ".%df" % METRIC_DECIMALS),
                                format(getattr(zero, name), ".%df" % METRIC_DECIMALS))

    def test_a_crossed_band_is_reported_in_ascending_order(self):
        hours = local_hours(HORIZON_START, HORIZON_END)
        document = values_document(hours, band=True)
        for row in document["hours"]:
            row["p10"], row["p90"] = row["p90"], row["p10"]  # the raw triple crosses
        fixture = Fixture(self, document=document)
        receipt = fixture.score()
        metrics = metrics_from(expected_pairs(fixture, band=True))
        assert_metrics_equal(self, receipt["metrics"][0], metrics)


class Marks(unittest.TestCase):
    """Marked intervals are skipped with their reasons and never filled."""

    def setUp(self):
        self.fixture = Fixture(self)

    def test_marked_intervals_land_in_coverage_with_their_reasons(self):
        receipt = self.fixture.score()
        self.assertEqual(receipt["coverage"]["scored"], 48)
        self.assertEqual(receipt["coverage"]["skipped"], [
            {"count": 96, "reason": "administered pricing 2026-04"},
            {"count": 24, "reason": "irregular day 2026-03-24"},
        ])
        self.assertEqual(receipt["coverage"]["scored"]
                         + sum(item["count"] for item in receipt["coverage"]["skipped"]),
                         len(self.fixture.horizon_hours))

    def test_the_irregular_day_is_excluded_from_the_metrics(self):
        receipt = self.fixture.score()
        metrics = metrics_from(expected_pairs(self.fixture))
        self.assertEqual(metrics.count, 48)
        self.assertEqual(receipt["metrics"][0]["intervals"], 48)
        assert_metrics_equal(self, receipt["metrics"][0], metrics)

    def test_a_window_entirely_in_an_administered_month_has_nothing_to_score(self):
        hours = local_hours("2026-03-31T16:00:00Z", "2026-04-01T16:00:00Z")
        fixture = Fixture(self, hours=hours, outlook_overrides={
            "horizon": {"label": "day", "start": "2026-03-31T16:00:00Z",
                        "end": "2026-04-01T16:00:00Z"}})
        self.assertEqual(refused(self, lambda: fixture.score(
            scored_at="2026-04-02T00:00:00Z")), "WINDOW_EMPTY")
        self.assertEqual(fixture.archive.receipts(), ())


class MetricsAgreement(unittest.TestCase):
    """The receipt's numbers are the scorecard's, on the same rows."""

    def test_the_metrics_equal_the_scorecard_on_the_same_pairs(self):
        fixture = Fixture(self)
        receipt = fixture.score()
        row = receipt["metrics"][0]
        metrics = metrics_from(expected_pairs(fixture))
        assert_metrics_equal(self, row, metrics)
        self.assertEqual(receipt["coverage"]["scored"], metrics.count)

    def test_the_zero_width_band_makes_pinball_p50_half_the_mae(self):
        fixture = Fixture(self)
        row = fixture.score()["metrics"][0]
        self.assertAlmostEqual(float(row["pinball_p50"]) * 2.0, float(row["mae"]), places=9)


class Provenance(unittest.TestCase):
    """The receipt's synthetic flag is inherited from the outlook, one way."""

    def test_a_synthetic_outlook_s_receipt_is_synthetic(self):
        receipt = Fixture(self).score()
        self.assertIs(True, receipt["synthetic"])

    def test_a_real_outlook_s_receipt_is_real(self):
        # A rule test only: this fixture outlook declares itself real to prove the
        # receipt inherits that declaration, exactly as ARCH-1's provenance tests do.
        receipt = Fixture(self, outlook_overrides={"synthetic": False}).score()
        self.assertIs(False, receipt["synthetic"])


class CommandLine(unittest.TestCase):
    """``scripts/outlook/score.py``: the command, end to end."""

    def setUp(self):
        self.fixture = Fixture(self)

    def run_cli(self, *arguments):
        return subprocess.run([str(INTERPRETER), str(SCRIPT)] + list(arguments),
                              capture_output=True, text=True, cwd=ROOT, timeout=180)

    def base_arguments(self):
        return ["--archive", str(self.fixture.archive.root),
                "--outlook-id", self.fixture.outlook["outlook_id"],
                "--regional", str(self.fixture.export_path),
                "--digests", str(self.fixture.digests_path),
                "--final-series-version", FINAL_VERSION]

    def test_the_command_scores_and_prints_the_key_and_digest(self):
        run = self.run_cli(*self.base_arguments(), "--scored-at", SCORED_AT)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIn("scored_at: %s" % SCORED_AT, run.stdout)
        self.assertIn("coverage: 48 scored, 120 skipped", run.stdout)
        key = re.search(r"^key: ([A-Za-z0-9._-]+)$", run.stdout, re.M)
        digest = re.search(r"^digest: ([0-9a-f]{64})$", run.stdout, re.M)
        self.assertTrue(key, run.stdout)
        self.assertTrue(digest, run.stdout)
        stored = self.fixture.archive.receipts()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["content_digest"], digest.group(1))
        self.assertEqual(receipt_stem(stored[0]), key.group(1))
        self.assertEqual(stored[0]["scored_at"], SCORED_AT)

    def test_a_second_run_is_refused_as_a_duplicate(self):
        first = self.run_cli(*self.base_arguments(), "--scored-at", SCORED_AT)
        self.assertEqual(0, first.returncode, first.stderr)
        second = self.run_cli(*self.base_arguments(), "--scored-at", SCORED_AT)
        self.assertEqual(1, second.returncode)
        self.assertIn("RECEIPT_DUPLICATE", second.stderr)
        self.assertEqual(len(self.fixture.archive.receipts()), 1)

    def test_dry_run_prints_the_receipt_and_appends_nothing(self):
        run = self.run_cli(*self.base_arguments(), "--scored-at", SCORED_AT, "--dry-run")
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIn("receipt: {", run.stdout)
        self.assertIn("dry run: nothing appended", run.stdout)
        self.assertIn("key: ", run.stdout)
        self.assertIn("digest: ", run.stdout)
        self.assertEqual(self.fixture.archive.receipts(), ())
        self.assertFalse(self.fixture.archive.receipts_dir.exists())

    def test_the_command_refuses_to_run_without_the_final_series_version(self):
        arguments = self.base_arguments()
        arguments = arguments[:arguments.index("--final-series-version")]
        run = self.run_cli(*arguments, "--scored-at", SCORED_AT)
        self.assertEqual(2, run.returncode)
        self.assertIn("--final-series-version", run.stderr)
        self.assertEqual(self.fixture.archive.receipts(), ())

    def test_the_command_defaults_scored_at_to_the_clock_and_prints_it(self):
        run = self.run_cli(*self.base_arguments())
        self.assertEqual(0, run.returncode, run.stderr)
        match = re.search(r"^scored_at: (\S+)$", run.stdout, re.M)
        self.assertTrue(match, run.stdout)
        self.assertRegex(match.group(1), r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        stored = self.fixture.archive.receipts()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["scored_at"], match.group(1))

    def test_the_command_never_issues_an_outlook_or_writes_an_attribution(self):
        outlooks = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(self.fixture.archive.outlooks_dir.glob("*.json"))}
        run = self.run_cli(*self.base_arguments(), "--scored-at", SCORED_AT)
        self.assertEqual(0, run.returncode, run.stderr)
        after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(self.fixture.archive.outlooks_dir.glob("*.json"))}
        self.assertEqual(outlooks, after)
        self.assertFalse(self.fixture.archive.attributions_dir.exists())

    def test_the_command_reports_a_values_digest_mismatch(self):
        fixture = Fixture(self, values_digest=DIGEST_B)
        run = self.run_cli("--archive", str(fixture.archive.root),
                           "--outlook-id", fixture.outlook["outlook_id"],
                           "--regional", str(fixture.export_path),
                           "--digests", str(fixture.digests_path),
                           "--final-series-version", FINAL_VERSION,
                           "--scored-at", SCORED_AT)
        self.assertEqual(1, run.returncode)
        self.assertIn("VALUES_DIGEST_MISMATCH", run.stderr)
        self.assertEqual(fixture.archive.receipts(), ())


@unittest.skipUnless(REAL_ARCHIVE.is_dir() and REAL_EXPORT.is_file() and REAL_DIGESTS.is_file(),
                     "the runtime outlook archive and the PRICE-2 export are linked into this "
                     "worktree under .local/; absent elsewhere")
class RealArchive(unittest.TestCase):
    """Today the real archive has no settled November window, and nothing is appended."""

    def test_both_november_vintages_are_refused_until_the_month_settles(self):
        archive = OutlookArchive(REAL_ARCHIVE)
        digests = load_digests(REAL_DIGESTS)
        before = archive.verify()
        # OUT-3: two vintages, or three once the third is issued; every one is refused
        third = "outlook-2026-11-system-v3"
        ids = ("outlook-2026-11-system", "outlook-2026-11-system-v2") + (
            (third,) if third in archive.issue_ids() else ())
        self.assertEqual((before["outlooks"], before["receipts"]), (len(ids), 0))
        self.assertEqual(before["problems"], [])
        # The refusal is the export's, not the clock's: the two vintages are scored
        # at an instant after their window closed, and the current export still
        # stops in billing month 2026-09.
        series = next(entry for entry in load_regional(REAL_EXPORT) if entry.key == "SYSTEM")
        self.assertLess(max(series.hours) + HOUR, datetime(2026, 11, 26, 0))
        for outlook_id in ids:
            outlook = archive.outlook(outlook_id)
            values = ROOT / outlook["values_ref"]["path_hint"]
            self.assertEqual(refused(self, lambda outlook=outlook, values=values: score_outlook(
                outlook, values, REAL_EXPORT, digests,
                scored_at="2026-12-01T00:00:00Z",
                final_series_version="final-bmonth-2026-11")), "WINDOW_NOT_SETTLED")
        after = archive.verify()
        self.assertEqual((after["outlooks"], after["receipts"], after["attributions"]),
                         (len(ids), 0, 0))
        self.assertEqual(after["problems"], [])


class StdlibOnly(unittest.TestCase):
    """The module and the command import only the standard library and this repository."""

    def imported_roots(self, path):
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_module_and_the_command_are_stdlib_only(self):
        for path in (ROOT / "src" / "outlook" / "scoring.py", SCRIPT):
            roots = self.imported_roots(path)
            self.assertTrue(roots)
            for root in roots:
                self.assertTrue(root in sys.stdlib_module_names
                                or root in {"src", "__future__"}, root)

    def test_the_module_reaches_only_the_price_and_archive_modules(self):
        text = (ROOT / "src" / "outlook" / "scoring.py").read_text(encoding="utf-8")
        reached = set(re.findall(r"^from (src\.[A-Za-z0-9_.]+) import", text, re.M))
        self.assertEqual(reached, {"src.outlook.records", "src.price.scorecard",
                                   "src.price.series"})

    def test_the_command_reaches_only_the_archive_scoring_and_export_modules(self):
        text = SCRIPT.read_text(encoding="utf-8")
        reached = set(re.findall(r"^from (src\.[A-Za-z0-9_.]+) import", text, re.M))
        self.assertEqual(reached, {"src.contracts.jsonutil", "src.outlook.records",
                                   "src.outlook.scoring", "src.price.series"})

    def test_the_test_module_stays_offline(self):
        text = Path(__file__).read_text(encoding="utf-8")
        roots = set(re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M))
        roots |= {name.split(".")[0] for name in re.findall(
            r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M) if not name.startswith(".")}
        for root in roots:
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                            root)


class RefusalText(unittest.TestCase):
    """Every refusal code has fixed, non-disclosing text."""

    def test_every_code_has_text_that_does_not_echo_the_code(self):
        for code, message in MESSAGES.items():
            self.assertTrue(message)
            self.assertNotIn(code, message)


if __name__ == "__main__":
    unittest.main()
