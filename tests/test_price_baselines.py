"""PRICE-2: the rolling-origin baselines and their scorecard, offline.

Every case here builds its own synthetic series; no network, model or cloud call
is made and no repository fixture is read. The three acceptance items carry named
tests: marked months are excluded as origins and never filled
(:class:`MarkedMonthsAreExcluded`, :class:`NeverFilled`), ``src/price`` imports
only the standard library (:class:`StdlibOnly`), and the scorecard is
reproducible from the exported files by digest (:class:`Reproducible` and
:class:`RealExports`, which reads the real export only when it is linked in).
Two review findings are pinned the same way: the fan's sign (:class:`FanSign`),
the ordering of one origin's three reported quantiles
(:class:`QuantileOrdering`) and the digest covering the written file's bytes
exactly (:class:`CommandLine`).
"""
import contextlib
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

from src.price.baselines import (  # noqa: E402
    BaselineError,
    Forecast,
    LastWeekSameInterval,
    Persistence,
    SeasonalAverageByBillingMonth,
    aggregate,
    candidate_origins,
    default_baselines,
    history_cutoff,
    last_ended_hour,
    window_for,
)
from src.price.scorecard import (  # noqa: E402
    AP,
    MARKET,
    QUANTILE_RULE,
    ErrorFan,
    build_scorecard,
    metrics_from,
    ordered_quantiles,
    pinball,
    quantile,
    slice_of,
)
from src.price.series import (  # noqa: E402
    REGIONAL_KEYS,
    HourRow,
    Series,
    SeriesError,
    billing_day_hours,
    billing_month_days,
    billing_month_hours,
    billing_month_of,
    billing_month_start,
    derive_marks,
    digest_file,
    load_regional,
    verify_inputs,
)

PRICE_DIR = ROOT / ".local" / "price"
REGIONAL_CSV = PRICE_DIR / "lwap_final_hourly.csv"
DIGESTS_JSON = PRICE_DIR / "digests.json"

CSV_HEADER = "byear,bmonth,region_name,hour_start,n5,lwap_mean,lwap_min,lwap_max"


def scratch_directory(prefix="price2-"):
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


def make_rows(start: date, days: int, value_of=day_value, absent_hours=(),
              short_hours=(), ap_hours=(), flagged=False) -> dict:
    """Hour rows for ``days`` billing days from ``start``, with named holes.

    ``absent_hours`` produce no row at all, ``short_hours`` a row of six
    intervals, and ``ap_hours`` a row whose twelve intervals are all administered
    pricing. Nothing is interpolated for a hole.
    """
    rows = {}
    for day_index in range(days):
        day = start + timedelta(days=day_index)
        value = day_value(day)
        for hour in billing_day_hours(day):
            if hour in absent_hours:
                continue
            intervals = 6 if hour in short_hours else 12
            rows[hour] = HourRow(
                hour_start=hour,
                intervals=intervals,
                mean=float(value_of(hour) if callable(value_of) else value),
                ap_intervals=12 if hour in ap_hours else 0,
                ap_known=flagged,
            )
    return rows


def make_series(key="CLUZ", kind="regional", start=date(2023, 6, 26), days=200, **kwargs) -> Series:
    rows = make_rows(start, days, **kwargs)
    return Series(key=key, kind=kind, label=f"{key} synthetic", source="synthetic.csv",
                  region=kwargs.get("region", ""), rows=rows)


def three_years(**kwargs) -> Series:
    """A fixture long enough for the seasonal baseline: 2023-06-26 to 2025-08-25."""
    return make_series(start=date(2023, 6, 26), days=792, **kwargs)


def pooled_seasonal_mean(series: Series, target_label: tuple[int, int], hour_of_day: int,
                         back_to: int = 4) -> float | None:
    """Re-derive the seasonal sample by hand: same hour of day, same month, earlier years."""
    year, month = target_label
    values = [
        row.mean for row in series.rows.values()
        if row.hour_start.hour == hour_of_day
        for back in range(1, back_to + 1)
        if billing_month_of(row.hour_start) == (year - back, month)
    ]
    return sum(values) / len(values) if values else None


def score_one(series, horizons=("day", "week", "month"), **kwargs):
    kwargs.setdefault("baselines", (
        Persistence(),
        LastWeekSameInterval(),
        SeasonalAverageByBillingMonth(min_samples=3, min_seasons=1),
    ))
    kwargs.setdefault("min_fan_samples", 3)
    return build_scorecard([series], horizons=horizons, **kwargs)


class ConstantBaseline:
    """A test baseline that forecasts one fixed value at every target hour."""

    name = "constant"
    version = "test"
    formula = "forecast(hour) = a fixed constant"

    def __init__(self, value: float) -> None:
        self.value = float(value)

    def forecast(self, series, window, cutoff, index=None):
        return Forecast((self.value,) * len(window.hours), {"value": self.value})


def horizon_of(scorecard, name, series_index=0):
    return next(entry for entry in scorecard.series[series_index].horizons
                if entry.horizon == name)


class BillingClock(unittest.TestCase):
    def test_one_date_maps_to_the_billing_month_that_contains_it(self):
        for moment, expected in (
            (date(2021, 6, 26), (2021, 7)),
            (date(2021, 7, 25), (2021, 7)),
            (date(2021, 7, 26), (2021, 8)),
            (date(2025, 12, 25), (2025, 12)),
            (date(2025, 12, 26), (2026, 1)),
            (date(2026, 3, 26), (2026, 4)),
            (date(2026, 4, 25), (2026, 4)),
            (date(2026, 4, 26), (2026, 5)),
        ):
            self.assertEqual(billing_month_of(moment), expected, moment)

    def test_a_billing_month_runs_twenty_sixth_to_twenty_fifth(self):
        self.assertEqual(billing_month_start(2026, 4), date(2026, 3, 26))
        self.assertEqual(billing_month_start(2026, 1), date(2025, 12, 26))
        self.assertEqual(billing_month_days(2026, 4), 31)
        self.assertEqual(billing_month_days(2022, 3), 28)   # 26 Feb to 25 Mar
        self.assertEqual(billing_month_days(2024, 3), 29)   # leap year
        hours = billing_month_hours(2026, 4)
        self.assertEqual(len(hours), 744)
        self.assertEqual(hours[0], datetime(2026, 3, 26, 0, 0))
        self.assertEqual(hours[-1], datetime(2026, 4, 25, 23, 0))

    def test_windows_begin_at_the_origin(self):
        day = window_for("day", date(2026, 8, 25))
        self.assertEqual((len(day.hours), day.start, day.end, day.days),
                         (24, datetime(2026, 8, 25), datetime(2026, 8, 26), 1))
        week = window_for("week", date(2026, 8, 19))
        self.assertEqual((len(week.hours), week.start, week.end, week.label()),
                         (168, datetime(2026, 8, 19), datetime(2026, 8, 26), "2026-08-19"))
        month = window_for("month", date(2026, 7, 26))
        self.assertEqual((len(month.hours), month.start, month.label()),
                         (744, datetime(2026, 7, 26), "2026-08"))

    def test_candidate_origins_run_over_the_whole_span_including_gaps(self):
        days = candidate_origins("day", date(2026, 1, 1), date(2026, 1, 10))
        self.assertEqual(len(days), 10)
        weeks = candidate_origins("week", date(2026, 1, 1), date(2026, 1, 10))
        self.assertEqual((len(weeks), weeks[0], weeks[-1]),
                         (4, date(2026, 1, 1), date(2026, 1, 4)))
        months = candidate_origins("month", date(2021, 6, 26), date(2026, 8, 25))
        self.assertEqual((len(months), months[0], months[-1]),
                         (62, date(2021, 6, 26), date(2026, 7, 26)))

    def test_the_cutoff_is_the_embargo_before_the_origin(self):
        self.assertEqual(history_cutoff(date(2026, 8, 25), 24), datetime(2026, 8, 24))
        self.assertEqual(last_ended_hour(datetime(2026, 8, 24)), datetime(2026, 8, 23, 23))
        self.assertEqual(last_ended_hour(datetime(2026, 8, 24, 6, 30)), datetime(2026, 8, 24, 6))


class ExportedFiles(unittest.TestCase):
    def write_csv(self, directory, hours, regions=REGIONAL_KEYS, value=100.0):
        path = Path(directory) / "lwap_final_hourly.csv"
        lines = [CSV_HEADER]
        for region in regions:
            for row in hours:
                year, month = billing_month_of(row)
                lines.append(f"{year},{month},{region},{row:%Y-%m-%d %H:%M:%S},12,{value},1.0,2.0")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_a_well_formed_export_loads_one_series_per_region(self):
        with scratch_directory() as tmp:
            path = self.write_csv(tmp, [datetime(2026, 8, 25, 0, 0), datetime(2026, 8, 25, 1, 0)])
            series = load_regional(path)
            self.assertEqual([entry.key for entry in series], list(REGIONAL_KEYS))
            self.assertEqual(len(series[0].rows), 2)
            self.assertEqual(series[0].rows[datetime(2026, 8, 25, 0, 0)].intervals, 12)
            self.assertFalse(series[0].has_ap_flags)

    def test_a_missing_header_column_is_refused(self):
        with scratch_directory() as tmp:
            path = Path(tmp) / "broken.csv"
            path.write_text("byear,bmonth,region_name,hour_start,n5\n", encoding="utf-8")
            with self.assertRaises(SeriesError) as caught:
                load_regional(path)
            self.assertEqual(caught.exception.code, "MALFORMED_EXPORT")

    def test_a_row_outside_its_billing_month_is_refused(self):
        with scratch_directory() as tmp:
            path = Path(tmp) / "clock.csv"
            lines = [CSV_HEADER]
            for region in REGIONAL_KEYS:
                lines.append(f"2026,8,{region},2026-08-25 00:00:00,12,1.0,1.0,1.0")
            lines.append("2026,8,CLUZ,2026-08-26 00:00:00,12,1.0,1.0,1.0")   # billing month 2026-09
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(SeriesError) as caught:
                load_regional(path)
            self.assertEqual(caught.exception.code, "CLOCK_MISMATCH")

    def test_the_export_is_checked_against_the_recorded_digest(self):
        with scratch_directory() as tmp:
            path = self.write_csv(tmp, [datetime(2026, 8, 25, 0, 0)])
            digests = {"lwap_final_hourly.csv": digest_file(path)}
            report = verify_inputs([path], digests)
            self.assertEqual(report[0]["sha256"], digest_file(path))
            digests["lwap_final_hourly.csv"] = "0" * 64
            with self.assertRaises(SeriesError) as caught:
                verify_inputs([path], digests)
            self.assertEqual(caught.exception.code, "DIGEST_MISMATCH")

    def test_an_unrecorded_file_is_refused_rather_than_assumed(self):
        with scratch_directory() as tmp:
            path = self.write_csv(tmp, [datetime(2026, 8, 25, 0, 0)])
            with self.assertRaises(SeriesError) as caught:
                verify_inputs([path], {"other.csv": digest_file(path)})
            self.assertEqual(caught.exception.code, "DIGEST_NOT_RECORDED")


class Marks(unittest.TestCase):
    def test_a_month_short_of_intervals_is_marked_short_with_its_days_irregular(self):
        series = make_series(start=date(2026, 1, 26), days=90)
        holes = tuple(hour for day in range(1, 8) for hour in billing_day_hours(date(2026, 3, day)))
        for hour in holes:
            series.rows.pop(hour)
        marks = derive_marks(series)
        self.assertEqual(marks.short_months, ("2026-03",))
        self.assertEqual(marks.absent_months, ())
        # a day with no row is a hole, not an irregular day: only a day that is
        # there with the wrong number of intervals is marked irregular
        self.assertEqual(marks.irregular_days, ())

    def test_a_month_with_no_row_at_all_is_absent(self):
        series = make_series(start=date(2026, 1, 26), days=90)
        for hour in billing_month_hours(2026, 3):
            series.rows.pop(hour)
        marks = derive_marks(series)
        self.assertEqual(marks.absent_months, ("2026-03",))
        self.assertEqual(marks.short_months, ())

    def test_the_regional_series_takes_its_pricing_marks_from_the_record(self):
        marks = derive_marks(make_series(start=date(2026, 3, 26), days=40))
        self.assertEqual(marks.ap_all_months, ("2026-04",))
        self.assertIn("2022-01", marks.ap_mixed_months)

    def test_a_nodal_series_reads_pricing_from_its_own_flags(self):
        ap_hours = set(billing_day_hours(date(2026, 4, 1)))
        series = make_series(kind="nodal", start=date(2026, 3, 26), days=31,
                             ap_hours=ap_hours, flagged=True)
        marks = derive_marks(series)
        self.assertEqual(marks.ap_all_months, ())
        self.assertEqual(marks.ap_mixed_months, ("2026-04",))


class PersistenceBaseline(unittest.TestCase):
    def setUp(self):
        self.series = make_series(start=date(2026, 8, 1), days=10)
        self.window = window_for("day", date(2026, 8, 9))

    def test_it_repeats_the_latest_value_the_cutoff_could_see(self):
        forecast = Persistence().forecast(self.series, self.window,
                                          history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(set(forecast.values), {day_value(date(2026, 8, 7))})
        self.assertEqual(len(forecast.values), 24)
        self.assertEqual(forecast.detail["used"], "2026-08-07T23:00:00")

    def test_the_embargo_moves_the_value_a_further_day_back(self):
        without = Persistence().forecast(self.series, self.window,
                                         history_cutoff(date(2026, 8, 9), 0))
        self.assertEqual(set(without.values), {day_value(date(2026, 8, 8))})

    def test_a_stale_value_is_refused_instead_of_forecast_across_a_gap(self):
        series = make_series(start=date(2026, 8, 1), days=3)
        window = window_for("day", date(2026, 8, 20))
        with self.assertRaises(BaselineError) as caught:
            Persistence().forecast(series, window, history_cutoff(date(2026, 8, 20), 24))
        self.assertEqual(caught.exception.code, "STALE_HISTORY")

    def test_no_history_at_all_is_refused(self):
        window = window_for("day", date(2026, 7, 1))
        with self.assertRaises(BaselineError) as caught:
            Persistence().forecast(self.series, window, history_cutoff(date(2026, 7, 1), 24))
        self.assertEqual(caught.exception.code, "NO_HISTORY")

    def test_the_aggregate_of_a_flat_profile_is_that_value(self):
        forecast = Persistence().forecast(self.series, self.window,
                                          history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(aggregate(forecast.values, (12,) * 24), day_value(date(2026, 8, 7)))


class LastWeekBaseline(unittest.TestCase):
    def setUp(self):
        self.series = make_series(start=date(2026, 8, 1), days=10)
        self.baseline = LastWeekSameInterval()

    def test_the_window_reads_the_same_clock_hour_seven_days_earlier(self):
        window = window_for("day", date(2026, 8, 9))
        forecast = self.baseline.forecast(self.series, window, history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(forecast.detail["sample_start"], "2026-08-02T00:00:00")
        self.assertEqual(forecast.detail["sample_end"], "2026-08-02T23:00:00")
        self.assertEqual(forecast.detail["weeks"], 1)
        self.assertEqual(forecast.values[0], day_value(date(2026, 8, 2)))
        self.assertEqual(forecast.values[23], day_value(date(2026, 8, 2)))

    def test_the_weekly_pattern_continues_when_a_lead_reaches_past_the_cutoff(self):
        window = window_for("week", date(2026, 8, 9))
        forecast = self.baseline.forecast(self.series, window, history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(len(forecast.values), 168)
        self.assertEqual(forecast.detail["weeks"], 2)
        # leads up to 143 read the week of 2 August; from lead 144 the hour seven
        # days back is still inside the embargo, so the pattern steps back a week
        self.assertEqual(forecast.values[0], day_value(date(2026, 8, 2)))
        self.assertEqual(forecast.values[143], day_value(date(2026, 8, 7)))
        self.assertEqual(forecast.values[144], day_value(date(2026, 8, 1)))

    def test_a_month_window_repeats_the_week_by_lead_modulo_168(self):
        series = make_series(start=date(2026, 1, 1), days=200)
        window = window_for("month", date(2026, 6, 26))
        forecast = self.baseline.forecast(series, window, history_cutoff(date(2026, 6, 26), 24))
        self.assertEqual(len(forecast.values), 720)
        self.assertEqual(forecast.values[168], forecast.values[0])
        self.assertEqual(forecast.values[719], forecast.values[719 - 168 * 4])

    def test_a_sampled_hour_that_is_absent_is_refused_and_never_padded(self):
        absent = set(billing_day_hours(date(2026, 8, 2)))
        series = make_series(start=date(2026, 8, 1), days=10, absent_hours=absent)
        window = window_for("day", date(2026, 8, 9))
        with self.assertRaises(BaselineError) as caught:
            self.baseline.forecast(series, window, history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(caught.exception.code, "INCOMPLETE_WEEK")
        self.assertIn("24 of 24 sampled hours absent", caught.exception.detail)

    def test_a_hole_the_samples_do_not_read_does_not_refuse_the_origin(self):
        absent = set(billing_day_hours(date(2026, 8, 4)))
        series = make_series(start=date(2026, 8, 1), days=10, absent_hours=absent)
        window = window_for("day", date(2026, 8, 9))
        forecast = self.baseline.forecast(series, window, history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(forecast.values[0], day_value(date(2026, 8, 2)))

    def test_a_short_sampled_hour_is_refused_too(self):
        series = make_series(start=date(2026, 8, 1), days=10,
                             short_hours={datetime(2026, 8, 2, 12, 0)})
        window = window_for("day", date(2026, 8, 9))
        with self.assertRaises(BaselineError) as caught:
            self.baseline.forecast(series, window, history_cutoff(date(2026, 8, 9), 24))
        self.assertEqual(caught.exception.code, "INCOMPLETE_WEEK")


class SeasonalBaseline(unittest.TestCase):
    def setUp(self):
        self.series = three_years()
        self.baseline = SeasonalAverageByBillingMonth(min_samples=3, min_seasons=1)

    def test_it_averages_the_same_hour_over_earlier_years_of_the_same_month(self):
        target = date(2025, 8, 5)
        window = window_for("day", target)
        forecast = self.baseline.forecast(self.series, window, history_cutoff(target, 24))
        self.assertEqual(forecast.detail["seasons"], 2)
        for hour_of_day in (0, 11, 23):
            expected = pooled_seasonal_mean(self.series, (2025, 8), hour_of_day)
            self.assertAlmostEqual(forecast.values[hour_of_day], expected)

    def test_only_present_rows_enter_the_sample(self):
        holes = set()
        for day in range(1, 8):
            holes.update(billing_day_hours(date(2024, 8, day)))
        series = three_years(absent_hours=holes)
        target = date(2025, 8, 5)
        forecast = self.baseline.forecast(series, window_for("day", target),
                                          history_cutoff(target, 24))
        self.assertAlmostEqual(forecast.values[0], pooled_seasonal_mean(series, (2025, 8), 0))
        self.assertNotEqual(forecast.values[0], day_value(date(2024, 8, 1)))

    def test_a_fully_absent_earlier_month_is_skipped_not_filled(self):
        holes = set(billing_month_hours(2024, 8))
        series = three_years(absent_hours=holes)
        self.assertIn("2024-08", derive_marks(series).absent_months)
        target = date(2025, 8, 5)
        forecast = self.baseline.forecast(series, window_for("day", target),
                                          history_cutoff(target, 24))
        self.assertAlmostEqual(forecast.values[0], pooled_seasonal_mean(series, (2025, 8), 0))
        self.assertEqual(forecast.detail["seasons"], 1)
        self.assertNotIn(day_value(date(2024, 8, 1)), set(forecast.values))

    def test_below_the_sample_floor_the_origin_is_excluded(self):
        strict = SeasonalAverageByBillingMonth(min_samples=100, min_seasons=1)
        target = date(2025, 8, 5)
        with self.assertRaises(BaselineError) as caught:
            strict.forecast(self.series, window_for("day", target), history_cutoff(target, 24))
        self.assertEqual(caught.exception.code, "INSUFFICIENT_SEASON_SAMPLES")

    def test_it_needs_an_earlier_year_at_all(self):
        first_year = SeasonalAverageByBillingMonth(min_samples=3, min_seasons=1)
        target = date(2023, 8, 5)
        with self.assertRaises(BaselineError) as caught:
            first_year.forecast(self.series, window_for("day", target), history_cutoff(target, 24))
        self.assertEqual(caught.exception.code, "INSUFFICIENT_SEASON_SAMPLES")

    def test_a_two_season_floor_excludes_the_first_scored_year(self):
        two = SeasonalAverageByBillingMonth(min_samples=3, min_seasons=2)
        target = date(2024, 8, 5)
        with self.assertRaises(BaselineError) as caught:
            two.forecast(self.series, window_for("day", target), history_cutoff(target, 24))
        self.assertEqual(caught.exception.code, "INSUFFICIENT_SEASON_SAMPLES")


class Metrics(unittest.TestCase):
    def test_bias_mae_rmse_and_pinball_are_computed_on_the_recorded_rows(self):
        # rows are (realized, point, p10, p50, p90); in the ordinary case the
        # point forecast is the middle value of the sorted triple
        scored = [(10.0, 9.0, 8.0, 9.0, 12.0), (20.0, 18.0, 15.0, 18.0, 25.0)]
        metrics = metrics_from(scored)
        self.assertEqual(metrics.count, 2)
        self.assertAlmostEqual(metrics.bias, -1.5)
        self.assertAlmostEqual(metrics.mae, 1.5)
        self.assertAlmostEqual(metrics.rmse, 2.5 ** 0.5)
        self.assertAlmostEqual(metrics.pinball_p10, 0.35)
        self.assertAlmostEqual(metrics.pinball_p50, 0.75)
        self.assertAlmostEqual(metrics.pinball_p90, 0.35)

    def test_the_point_metrics_never_read_the_reported_median(self):
        # a crossed fan: the reported p50 is the nearer arm, not the point
        # forecast, so bias / MAE / RMSE follow the point and pinball follows p50
        scored = [(30.0, 26.0, 26.0, 28.0, 40.0)]
        metrics = metrics_from(scored)
        self.assertAlmostEqual(metrics.bias, -4.0)
        self.assertAlmostEqual(metrics.mae, 4.0)
        self.assertAlmostEqual(metrics.rmse, 4.0)
        self.assertAlmostEqual(metrics.pinball_p50, 1.0)
        self.assertAlmostEqual(metrics.pinball_p50, pinball(0.50, 30.0, 28.0))
        self.assertAlmostEqual(metrics.pinball_p10, pinball(0.10, 30.0, 26.0))

    def test_pinball_at_p50_is_exactly_half_the_mae_when_the_triple_does_not_cross(self):
        scored = [(1.0, 0.7, 0.5, 0.7, 1.4), (-3.0, -2.8, -3.5, -2.8, -2.0),
                  (100.0, 105.0, 90.0, 105.0, 120.0)]
        for realized, point, p10, p50, p90 in scored:
            self.assertEqual(p50, point)
            self.assertLess(p10, p50)
            self.assertLess(p50, p90)
        metrics = metrics_from(scored)
        self.assertAlmostEqual(metrics.pinball_p50, metrics.mae / 2.0)

    def test_an_empty_slice_reports_a_zero_count_and_no_metric(self):
        metrics = metrics_from([])
        self.assertEqual(metrics.count, 0)
        self.assertIsNone(metrics.mae)
        self.assertIsNone(metrics.pinball_p10)

    def test_pinball_is_zero_only_when_the_quantile_is_exact(self):
        self.assertEqual(pinball(0.10, 5.0, 5.0), 0.0)
        self.assertAlmostEqual(pinball(0.10, 5.0, 4.0), 0.1)
        self.assertAlmostEqual(pinball(0.10, 4.0, 5.0), 0.9)
        self.assertAlmostEqual(pinball(0.90, 4.0, 5.0), 0.1)

    def test_quantile_interpolates_between_order_statistics(self):
        sample = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(quantile(sample, 0.0), 1.0)
        self.assertEqual(quantile(sample, 1.0), 4.0)
        self.assertAlmostEqual(quantile(sample, 0.5), 2.5)
        self.assertAlmostEqual(quantile(sample, 0.1), 1.3)
        self.assertEqual(quantile([7.0], 0.9), 7.0)
        with self.assertRaises(ValueError):
            quantile([], 0.5)


class ErrorFanRules(unittest.TestCase):
    def test_an_error_is_released_only_after_its_window_outlived_the_embargo(self):
        fan = ErrorFan(24)
        fan.add(datetime(2026, 1, 1), 5.0)
        fan.release(datetime(2026, 1, 1, 12))
        self.assertEqual(len(fan), 0)
        fan.release(datetime(2026, 1, 2))
        self.assertEqual(len(fan), 1)

    def test_the_arms_are_offsets_from_the_point_forecast(self):
        fan = ErrorFan(0)
        for step, error in enumerate([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]):
            fan.add(datetime(2026, 1, 1) + timedelta(hours=step), error)
        fan.release(datetime(2026, 2, 1))
        low, high = fan.arms()
        self.assertAlmostEqual(low, -2.1)
        self.assertAlmostEqual(high, 5.1)

    def test_a_fan_no_one_could_compute_is_never_scored(self):
        fan = ErrorFan(0)
        with self.assertRaises(BaselineError) as caught:
            fan.arms()
        self.assertEqual(caught.exception.code, "NO_ERROR_FAN")


class Slices(unittest.TestCase):
    def test_a_regional_window_inside_an_ap_month_is_the_ap_slice(self):
        series = make_series(start=date(2026, 3, 26), days=40)
        marks = derive_marks(series)
        self.assertEqual(slice_of(series, window_for("day", date(2026, 4, 3)), marks), AP)

    def test_a_window_that_mixes_an_ap_month_with_a_market_month_is_mixed(self):
        series = make_series(start=date(2026, 3, 20), days=20)
        marks = derive_marks(series)
        self.assertEqual(slice_of(series, window_for("week", date(2026, 3, 24)), marks), "mixed")

    def test_a_nodal_window_classifies_by_its_own_interval_counts(self):
        flagged = make_series(kind="nodal", start=date(2026, 3, 26), days=40,
                              ap_hours=set(billing_day_hours(date(2026, 4, 3))), flagged=True)
        marks = derive_marks(flagged)
        self.assertEqual(slice_of(flagged, window_for("day", date(2026, 4, 3)), marks), AP)
        self.assertEqual(slice_of(flagged, window_for("day", date(2026, 4, 2)), marks), MARKET)


class FanSign(unittest.TestCase):
    """The fan stores ``realized − forecast``, so an arm corrects the point forecast
    toward the settled values, never away from them.

    A constant residual makes the sign exact. Every settled value 100 with every
    forecast 80 gives a residual of +20 at every origin, so both raw arms land on
    100; reversing the stored residual would place them at 60 and 140 instead. The
    reported triple is the sorted one (``QuantileOrdering`` below), so a fan that
    has crossed the point forecast puts the point at one end: here the triple is
    ``(80, 100, 100)``, the two arms are the two highest values, and the pinball
    losses are 2, 0 and 0 PHP/MWh.
    """

    def score_constant(self, forecast_value):
        series = make_series(start=date(2025, 1, 26), days=90, value_of=lambda hour: 100.0)
        return build_scorecard(
            [series], horizons=("day",),
            baselines=(ConstantBaseline(forecast_value),), min_fan_samples=3,
        )

    def test_an_under_forecast_lifts_both_arms_onto_the_settled_value(self):
        metrics = horizon_of(self.score_constant(80.0), "day").baselines[0].slices[MARKET]
        self.assertGreater(metrics.count, 0)
        # bias and MAE stay on the point forecast; the pair of 100s below are the arms
        self.assertAlmostEqual(metrics.bias, -20.0)
        self.assertAlmostEqual(metrics.mae, 20.0)
        self.assertAlmostEqual(metrics.pinball_p10, pinball(0.10, 100.0, 80.0))
        self.assertGreater(metrics.pinball_p10, 0.0)
        self.assertAlmostEqual(metrics.pinball_p50, 0.0)
        self.assertAlmostEqual(metrics.pinball_p90, 0.0)

    def test_an_over_forecast_lowers_both_arms_onto_the_settled_value(self):
        metrics = horizon_of(self.score_constant(120.0), "day").baselines[0].slices[MARKET]
        self.assertGreater(metrics.count, 0)
        self.assertAlmostEqual(metrics.bias, 20.0)
        self.assertAlmostEqual(metrics.mae, 20.0)
        # the mirrored triple is (100, 100, 120): both arms at 100, the point on top
        self.assertAlmostEqual(metrics.pinball_p10, 0.0)
        self.assertAlmostEqual(metrics.pinball_p50, 0.0)
        self.assertAlmostEqual(metrics.pinball_p90, pinball(0.90, 100.0, 120.0))
        self.assertGreater(metrics.pinball_p90, 0.0)

    def test_the_scored_arms_are_the_released_residual_quantiles_in_order(self):
        start = date(2025, 1, 26)
        forecast_value = 2000.0
        scorecard = build_scorecard(
            [make_series(start=start, days=31)], horizons=("day",),
            baselines=(ConstantBaseline(forecast_value),), min_fan_samples=29,
        )
        horizon = horizon_of(scorecard, "day")
        self.assertEqual(dict(horizon.scored)[MARKET], 1, "one origin with 29 released residuals")
        metrics = horizon.baselines[0].slices[MARKET]
        realized = day_value(date(2025, 2, 25))
        residuals = sorted(day_value(start + timedelta(days=step)) - forecast_value
                           for step in range(29))
        low = forecast_value + quantile(residuals, 0.10)
        high = forecast_value + quantile(residuals, 0.90)
        self.assertLess(low, forecast_value)
        self.assertLess(forecast_value, high)
        self.assertAlmostEqual(metrics.pinball_p10, pinball(0.10, realized, low))
        self.assertAlmostEqual(metrics.pinball_p90, pinball(0.90, realized, high))
        self.assertAlmostEqual(metrics.pinball_p50, pinball(0.50, realized, forecast_value))
        self.assertAlmostEqual(metrics.bias, forecast_value - realized)


class QuantileOrdering(unittest.TestCase):
    """Review finding: one origin's three reported quantiles never cross.

    The raw triple is the fan's two arms around the point forecast, and where both
    arms sit on one side of zero that triple crosses. ``ordered_quantiles`` is the
    whole rule and is pinned directly first, then end to end through the scorecard
    for a positive fan and a negative one (in :class:`FanSign`) and for the
    ordinary straddling fan here, where nothing moves and the point forecast stays
    the middle value.
    """

    START = date(2025, 1, 26)

    def test_the_three_values_are_returned_in_ascending_order(self):
        # the review's probe, as raw arms: settled value 100, point forecast 80,
        # both residual quantiles +20 — the raw triple (100, 80, 100) crosses
        self.assertEqual(ordered_quantiles(80.0, 20.0, 20.0), (80.0, 100.0, 100.0))
        # and its mirror: point forecast 120 with both residual quantiles −20
        self.assertEqual(ordered_quantiles(120.0, -20.0, -20.0), (100.0, 100.0, 120.0))
        # the ordinary straddling fan: nothing moves
        self.assertEqual(ordered_quantiles(100.0, -20.0, 20.0), (80.0, 100.0, 120.0))
        self.assertEqual(ordered_quantiles(100.0, 30.0, 50.0), (100.0, 130.0, 150.0))
        self.assertEqual(ordered_quantiles(100.0, -50.0, -30.0), (50.0, 70.0, 100.0))
        self.assertEqual(ordered_quantiles(100.0, 0.0, 0.0), (100.0, 100.0, 100.0))

    def test_a_crossed_triple_is_never_reported_crossed(self):
        for point, low, high in ((80.0, 20.0, 20.0), (120.0, -20.0, -20.0),
                                 (100.0, 30.0, 50.0), (100.0, -50.0, -30.0)):
            raw = (point + low, point, point + high)
            self.assertFalse(raw[0] <= raw[1] <= raw[2], "the raw triple does cross")
            p10, p50, p90 = ordered_quantiles(point, low, high)
            self.assertLessEqual(p10, p50)
            self.assertLessEqual(p50, p90)
            self.assertEqual(sorted(raw), [p10, p50, p90])

    def test_a_straddling_fan_leaves_the_point_forecast_in_the_middle(self):
        series = make_series(start=self.START, days=120,
                             value_of=lambda hour: 100.0 + 40.0 * (hour.day % 5 - 2))
        scorecard = build_scorecard([series], horizons=("day",),
                                    baselines=(ConstantBaseline(100.0),), min_fan_samples=5)
        metrics = horizon_of(scorecard, "day").baselines[0].slices[MARKET]
        self.assertGreater(metrics.count, 0)
        # no arm crosses here, so p50 is the point forecast and the identity holds
        self.assertAlmostEqual(metrics.pinball_p50, metrics.mae / 2.0)
        self.assertGreater(metrics.pinball_p10, 0.0)
        self.assertGreater(metrics.pinball_p90, 0.0)


class MarkedMonthsAreExcluded(unittest.TestCase):
    """Acceptance 1: a marked month never becomes an origin and is never filled.

    The fixture is 2024-12-26 to 2026-04-25 (billing months 2025-01 to 2026-04),
    whole, except that billing month 2026-02 (26 Jan to 25 Feb 2026) has no row.
    """

    START = date(2024, 12, 26)
    DAYS = 486
    GAP_START = date(2026, 1, 26)
    GAP_END = date(2026, 2, 25)

    @classmethod
    def setUpClass(cls):
        gap = set()
        day = cls.GAP_START
        while day <= cls.GAP_END:
            gap.update(billing_day_hours(day))
            day += timedelta(days=1)
        cls.gap_hours = gap
        cls.series = make_series(start=cls.START, days=cls.DAYS, absent_hours=gap)
        cls.scorecard = score_one(cls.series)

    def test_the_gap_month_is_reported_as_absent(self):
        marks = derive_marks(self.series)
        self.assertEqual(marks.absent_months, ("2026-02",))
        self.assertEqual(marks.short_months, ())

    def test_every_origin_inside_the_gap_is_excluded_with_a_reason(self):
        day = horizon_of(self.scorecard, "day")
        codes = dict(day.excluded_rows)
        self.assertEqual(codes[self.GAP_START.isoformat()], "window_incomplete")
        self.assertEqual(codes[self.GAP_END.isoformat()], "window_incomplete")
        self.assertEqual(dict(day.excluded)["window_incomplete"], 31)
        scored = {row[0] for row in day.origin_rows}
        self.assertFalse(scored & {hour.date().isoformat() for hour in self.gap_hours})

    def test_the_candidate_origins_are_a_partition_of_scored_and_excluded(self):
        for horizon in self.scorecard.series[0].horizons:
            counts = dict(horizon.scored)
            self.assertEqual(horizon.candidates,
                             counts[MARKET] + counts[AP] + len(horizon.excluded_rows))
            self.assertEqual(len(horizon.origin_rows), counts[MARKET] + counts[AP])
            self.assertEqual(len({row[0] for row in horizon.origin_rows}),
                             len(horizon.origin_rows))

    def test_a_baseline_that_would_need_a_marked_hour_excludes_the_origin(self):
        day = horizon_of(self.scorecard, "day")
        persistence = next(entry for entry in day.baselines if entry.name == "persistence")
        self.assertGreaterEqual(dict(persistence.unavailable).get("STALE_HISTORY", 0), 1)
        self.assertNotIn("2026-02-26", [row[0] for row in day.origin_rows])

    def test_every_baseline_is_scored_on_the_same_origins(self):
        for horizon in self.scorecard.series[0].horizons:
            counts = dict(horizon.scored)
            for baseline in horizon.baselines:
                self.assertEqual(baseline.slices[MARKET].count, counts[MARKET], baseline.name)
                self.assertEqual(baseline.slices[AP].count, counts[AP], baseline.name)

    def test_the_marked_month_still_scores_something_around_it(self):
        day = horizon_of(self.scorecard, "day")
        self.assertGreater(dict(day.scored)[MARKET], 0)
        self.assertGreater(dict(day.excluded)["baseline_unavailable"], 0)


class MarkedShortMonthsAreExcluded(unittest.TestCase):
    """Acceptance 1: a month marked short from the bytes never supplies an origin.

    The fixture is the whole billing months 2025-02 to 2025-04 with one hour of
    2025-03-10 absent, so ``derive_marks`` marks 2025-03 short. Every origin whose
    own billing month is 2025-03 is excluded even where its window is complete;
    the window that contains the hole itself is excluded as incomplete, and the
    month horizon — whose window is the marked month — follows the same rule.
    """

    START = date(2025, 1, 26)
    DAYS = 90                                    # 2025-01-26 to 2025-04-25
    HOLE = datetime(2025, 3, 10, 5, 0)
    FIRST = "2025-02-26"                         # billing month 2025-03 opens
    LAST = "2025-03-25"

    @classmethod
    def setUpClass(cls):
        cls.series = make_series(start=cls.START, days=cls.DAYS, absent_hours={cls.HOLE})
        cls.scorecard = build_scorecard(
            [cls.series], horizons=("day", "week", "month"),
            baselines=(Persistence(), LastWeekSameInterval()), min_fan_samples=3,
        )

    def test_the_month_is_marked_short_from_the_bytes(self):
        marks = derive_marks(self.series)
        self.assertEqual(marks.short_months, ("2025-03",))
        self.assertEqual(marks.absent_months, ())
        self.assertEqual(marks.irregular_days, ("2025-03-10",))

    def test_no_origin_in_the_short_month_is_scored_at_any_horizon(self):
        for horizon in self.scorecard.series[0].horizons:
            inside = [row[0] for row in horizon.origin_rows
                      if self.FIRST <= row[0] <= self.LAST]
            self.assertEqual(inside, [], horizon.horizon)

    def test_day_and_week_origins_in_the_month_carry_the_month_short_reason(self):
        for name in ("day", "week"):
            codes = dict(horizon_of(self.scorecard, name).excluded_rows)
            self.assertEqual(codes[self.FIRST], "month_short", name)
            self.assertEqual(codes[self.LAST], "month_short", name)

    def test_the_window_that_contains_the_hole_is_excluded_as_incomplete(self):
        day = horizon_of(self.scorecard, "day")
        self.assertEqual(dict(day.excluded_rows)["2025-03-10"], "window_incomplete")
        month = horizon_of(self.scorecard, "month")
        self.assertEqual(dict(month.excluded_rows)["2025-02-26"], "window_incomplete")
        self.assertNotIn("2025-03", [row[1] for row in month.origin_rows])

    def test_the_partition_still_holds_with_the_short_month_exclusions(self):
        for horizon in self.scorecard.series[0].horizons:
            counts = dict(horizon.scored)
            self.assertEqual(horizon.candidates,
                             counts[MARKET] + counts[AP] + len(horizon.excluded_rows))
        self.assertGreater(dict(horizon_of(self.scorecard, "day").excluded)["month_short"], 0)
        self.assertGreater(dict(horizon_of(self.scorecard, "week").excluded)["month_short"], 0)


class NeverFilled(unittest.TestCase):
    """A missing or short hour is excluded, never interpolated or carried forward.

    The fixture starts a year before the holes it carries, so the seasonal
    baseline is available and an exclusion here is about the hole, not about a
    missing season.
    """

    START = date(2024, 12, 26)

    def test_a_day_short_of_intervals_is_excluded_as_a_window(self):
        short = set(billing_day_hours(date(2026, 1, 3))) - {datetime(2026, 1, 3, 5, 0)}
        series = make_series(start=self.START, days=400, short_hours=short)
        self.assertEqual(derive_marks(series).irregular_days, ("2026-01-03",))
        day = horizon_of(score_one(series), "day")
        self.assertEqual(dict(day.excluded_rows)["2026-01-03"], "window_short")
        self.assertNotIn("2026-01-03", [row[0] for row in day.origin_rows])

    def test_the_realized_value_of_a_partial_window_is_never_reported(self):
        series = make_series(start=self.START, days=400,
                             absent_hours={datetime(2026, 1, 3, 5, 0)})
        day = horizon_of(score_one(series, horizons=("day",)), "day")
        self.assertEqual(dict(day.excluded_rows)["2026-01-03"], "window_incomplete")
        self.assertNotIn("2026-01-03", [row[0] for row in day.origin_rows])

    def test_a_short_hour_inside_a_week_moves_the_week_window_out(self):
        series = make_series(start=self.START, days=400,
                             short_hours={datetime(2026, 1, 3, 5, 0)})
        week = horizon_of(score_one(series, horizons=("week",)), "week")
        self.assertIn("window_short", dict(week.excluded))

    def test_a_window_whose_hours_are_all_present_scores(self):
        series = make_series(start=self.START, days=400)
        day = horizon_of(score_one(series, horizons=("day",)), "day")
        self.assertGreater(dict(day.scored)[MARKET], 0)
        self.assertEqual(dict(day.excluded).get("window_incomplete", 0), 0)
        self.assertEqual(dict(day.excluded).get("window_short", 0), 0)


class ScorecardShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scorecard = score_one(make_series(start=date(2023, 6, 26), days=792))

    def test_the_record_carries_the_required_metrics_per_horizon_and_baseline(self):
        for horizon in self.scorecard.series[0].horizons:
            self.assertEqual([baseline.name for baseline in horizon.baselines],
                             [baseline.name for baseline in default_baselines()])
            for baseline in horizon.baselines:
                metrics = baseline.slices[MARKET].to_dict()
                self.assertEqual(sorted(metrics), sorted([
                    "count", "bias", "mae", "rmse",
                    "pinball_p10", "pinball_p50", "pinball_p90"]))

    def test_each_horizon_scores_its_own_window_length(self):
        lengths = {horizon.horizon: horizon.window_hours
                   for horizon in self.scorecard.series[0].horizons}
        self.assertEqual(lengths["day"], (24,))
        self.assertEqual(lengths["week"], (168,))
        self.assertTrue(lengths["month"] and all(length % 24 == 0 for length in lengths["month"]))

    def test_the_shorter_horizon_scores_more_origins(self):
        counts = {horizon.horizon: dict(horizon.scored)[MARKET]
                  for horizon in self.scorecard.series[0].horizons}
        self.assertGreater(counts["day"], counts["week"])
        self.assertGreater(counts["week"], counts["month"])

    def test_a_higher_fan_minimum_withholds_more_leading_origins(self):
        series = make_series(start=date(2024, 12, 26), days=400)
        counts = {}
        for minimum in (1, 3, 6):
            day = horizon_of(score_one(series, horizons=("day",), min_fan_samples=minimum), "day")
            counts[minimum] = dict(day.excluded).get("no_error_fan", 0)
            self.assertGreater(dict(day.scored)[MARKET], 0, minimum)
        self.assertLess(counts[1], counts[3])
        self.assertLess(counts[3], counts[6])

    def test_an_unknown_horizon_is_refused(self):
        with self.assertRaises(BaselineError) as caught:
            build_scorecard([make_series(start=date(2023, 6, 26), days=30)], horizons=("hour",))
        self.assertEqual(caught.exception.code, "UNKNOWN_HORIZON")


class Reproducible(unittest.TestCase):
    """Acceptance 3: the record is a deterministic function of the exported bytes."""

    @classmethod
    def setUpClass(cls):
        cls.series = make_series(start=date(2023, 6, 26), days=200)

    def test_the_same_inputs_give_the_same_bytes_and_digest(self):
        first = score_one(self.series)
        second = score_one(self.series)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.content_digest(), second.content_digest())
        self.assertEqual(first.content_digest(),
                         hashlib.sha256(first.to_json().encode("utf-8")).hexdigest())

    def test_the_configuration_is_part_of_the_record(self):
        first = score_one(self.series)
        second = build_scorecard(
            [self.series], horizons=("day", "week", "month"),
            baselines=(Persistence(), LastWeekSameInterval(),
                       SeasonalAverageByBillingMonth(min_samples=3, min_seasons=1)),
            min_fan_samples=4)
        self.assertEqual(second.min_fan_samples, 4)
        self.assertNotEqual(first.content_digest(), second.content_digest())

    def test_the_inputs_are_carried_by_digest_and_row_count(self):
        record = score_one(self.series, inputs=[{"file": "lwap_final_hourly.csv",
                                                 "sha256": "a" * 64, "rows": 42}])
        self.assertEqual(record.to_dict()["inputs"],
                         [{"file": "lwap_final_hourly.csv", "sha256": "a" * 64, "rows": 42}])
        self.assertIn('"inputs":[{"file":"lwap_final_hourly.csv"', record.to_json())

    def test_the_record_has_no_non_finite_number(self):
        text = score_one(self.series).to_json()
        self.assertNotIn("NaN", text)
        self.assertNotIn("Infinity", text)
        json.loads(text)

    def test_the_record_names_its_baselines_and_their_formulas(self):
        record = json.loads(score_one(self.series).to_json())
        self.assertEqual(record["kind"], "price-baseline-scorecard")
        self.assertEqual([entry["name"] for entry in record["baselines"]],
                         [baseline.name for baseline in default_baselines()])
        for entry in record["baselines"]:
            self.assertTrue(entry["formula"])
        self.assertEqual(record["embargo_hours"], 24)

    def test_the_record_states_the_quantile_rule_it_reports(self):
        record = json.loads(score_one(self.series).to_json())
        self.assertEqual(record["quantile_rule"], QUANTILE_RULE)
        self.assertIn("ascending order", record["quantile_rule"])
        self.assertIn("unadjusted point forecast", record["quantile_rule"])
        self.assertEqual(record["version"], "price-2.3")


class CommandLine(unittest.TestCase):
    """The runner: export in, scorecard JSON out, digest printed."""

    SPEC = importlib.util.spec_from_file_location(
        "price_baselines_cli", ROOT / "scripts" / "price" / "baselines.py")

    def load_cli(self):
        module = importlib.util.module_from_spec(self.SPEC)
        self.SPEC.loader.exec_module(module)
        return module

    def write_export(self, directory, days=500, start=date(2023, 6, 26)):
        """A four-region export in the PRICE-1 column order, with its digest record."""
        path = Path(directory) / "lwap_final_hourly.csv"
        lines = [CSV_HEADER]
        for day_index in range(days):
            day = start + timedelta(days=day_index)
            year, month = billing_month_of(day)
            for hour in billing_day_hours(day):
                value = day_value(day) + hour.hour
                for region in REGIONAL_KEYS:
                    lines.append(f"{year},{month},{region},{hour:%Y-%m-%d %H:%M:%S},"
                                 f"12,{value},1.0,2.0")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        digests = Path(directory) / "digests.json"
        digests.write_text(json.dumps({"lwap_final_hourly.csv": digest_file(path)},
                                      sort_keys=True), encoding="utf-8")
        return path, digests

    def test_it_writes_a_record_whose_digest_matches_its_bytes(self):
        cli = self.load_cli()
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp)
            out = Path(tmp) / "scorecard.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = cli.main(["--regional", str(path), "--digests", str(digests),
                                   "--out", str(out), "--series", "regional",
                                   "--summary-series", "none", "--min-fan-samples", "3"])
            self.assertEqual(status, 0)
            bytes_written = out.read_bytes()
            # the digest covers the file's bytes exactly: nothing is appended and
            # nothing is trimmed before hashing (review finding, round 2)
            self.assertFalse(bytes_written.endswith(b"\n"),
                             "the file is exactly the bytes the digest covers")
            digest = hashlib.sha256(bytes_written).hexdigest()
            self.assertIn(f"content_digest {digest}", stdout.getvalue())
            record = json.loads(bytes_written.decode("utf-8"))
            self.assertEqual(record["kind"], "price-baseline-scorecard")
            self.assertEqual(record["inputs"][0]["sha256"], digest_file(path))
            self.assertEqual(len(record["series"]), 4)
            self.assertEqual(bytes_written.decode("utf-8"),
                             json.dumps(record, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False, allow_nan=False))

    def test_the_summary_reports_one_row_per_baseline(self):
        cli = self.load_cli()
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp, days=500)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = cli.main(["--regional", str(path), "--digests", str(digests),
                                   "--summary-series", "regional"])
            self.assertEqual(status, 0)
            text = stdout.getvalue()
            for name in ("persistence", "last_week_same_interval",
                         "seasonal_average_billing_month"):
                self.assertIn(name, text)
            self.assertIn("candidates", text)

    def test_a_tampered_export_fails_with_a_digest_error(self):
        cli = self.load_cli()
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp, days=40)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("2026,8,CLUZ,2026-08-25 10:00:00,12,1.0,1.0,1.0\n")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = cli.main(["--regional", str(path), "--digests", str(digests),
                                   "--summary-series", "none"])
            self.assertEqual(status, 2)
            self.assertIn("DIGEST_MISMATCH", stderr.getvalue())


class RealExports(unittest.TestCase):
    """The exported files themselves: digests, the marks, and the record's digest.

    These cases are skipped when the PRICE-1 export is not linked into
    ``.local/price`` (it never enters Git); nothing else in this file reads it.
    The facts are those of the export regenerated after the 2026-10-17 refresh
    (docs/work/data-organization-2026-10-17/record.md): 63 billing months, the
    2025-09 to 2025-12 gap filled.
    """

    @classmethod
    def setUpClass(cls):
        if not (REGIONAL_CSV.exists() and DIGESTS_JSON.exists()):
            raise unittest.SkipTest("the PRICE-1 export is not present under .local/price")
        cls.digests = json.loads(DIGESTS_JSON.read_text(encoding="utf-8"))
        cls.hint = ".local/price/lwap_final_hourly.csv"
        cls.inputs = verify_inputs([REGIONAL_CSV], cls.digests)
        series = [entry for entry in load_regional(REGIONAL_CSV) if entry.key == "CLUZ"]
        cls.series = series
        cls.scorecard = build_scorecard(series, inputs=cls.inputs)

    def test_the_export_still_matches_its_recorded_digest(self):
        self.assertEqual(self.inputs[0]["sha256"], self.digests[self.hint])
        self.assertEqual(self.inputs[0]["rows"], 184036)

    def test_the_marks_are_only_the_july_2022_artifact_after_the_refresh(self):
        marks = derive_marks(self.series[0])
        self.assertEqual(marks.absent_months, ())
        self.assertEqual(marks.short_months, ())
        self.assertEqual(marks.irregular_days, ("2022-07-07", "2022-07-08"))
        self.assertEqual(marks.ap_all_months, ("2026-04",))

    def test_the_scorecard_is_reproducible_from_the_exported_bytes(self):
        again = build_scorecard(self.series, inputs=verify_inputs([REGIONAL_CSV], self.digests))
        self.assertEqual(self.scorecard.to_json(), again.to_json())
        self.assertEqual(self.scorecard.content_digest(), again.content_digest())

    def test_the_filled_gap_is_scored_and_the_two_july_days_are_not(self):
        day = horizon_of(self.scorecard, "day")
        codes = dict(day.excluded_rows)
        scored_days = {row[0] for row in day.origin_rows}
        self.assertNotIn("2025-09-01", codes)
        self.assertIn("2025-10-15", scored_days)
        self.assertEqual(codes["2022-07-07"], "window_incomplete")
        self.assertEqual(codes["2022-07-08"], "window_short")
        self.assertEqual(dict(day.excluded)["window_incomplete"], 1)

    def test_the_administered_pricing_month_is_its_own_slice(self):
        day = horizon_of(self.scorecard, "day")
        self.assertEqual(dict(day.scored)[AP], 31)
        ap_days = {row[0] for row in day.origin_rows if row[2] == AP}
        self.assertEqual(ap_days, {
            (date(2026, 3, 26) + timedelta(days=step)).isoformat() for step in range(31)})
        market_days = {row[0] for row in day.origin_rows if row[2] == MARKET}
        self.assertFalse(market_days & ap_days)

    def test_every_baseline_keeps_the_same_denominator(self):
        for horizon in self.scorecard.series[0].horizons:
            counts = dict(horizon.scored)
            for baseline in horizon.baselines:
                self.assertEqual(baseline.slices[MARKET].count, counts[MARKET])
                self.assertEqual(baseline.slices[AP].count, counts[AP])

    def test_the_required_metrics_are_present_for_every_region_key(self):
        record = json.loads(self.scorecard.to_json())
        self.assertEqual([entry["key"] for entry in record["series"]], ["CLUZ"])
        for horizon in record["series"][0]["horizons"]:
            for baseline in horizon["baselines"]:
                metrics = baseline["slices"]["market"]
                self.assertGreater(metrics["count"], 0)
                for name in ("bias", "mae", "rmse", "pinball_p10", "pinball_p50", "pinball_p90"):
                    self.assertIsNotNone(metrics[name], (horizon["horizon"], baseline["name"]))


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

    def test_the_price_modules_import_only_the_standard_library(self):
        paths = sorted((ROOT / "src/price").glob("*.py"))
        # challengers.py is PRICE-3's; it is held to the same rule, and its own
        # module names the same check among its acceptance tests
        self.assertEqual([path.name for path in paths],
                         ["__init__.py", "availability.py", "baselines.py", "challengers.py", "fuel.py",
                          "impact.py", "response.py", "scorecard.py", "series.py"])
        for path in paths:
            for root in self.imported_roots(path):
                self.assertTrue(root in sys.stdlib_module_names or root == "__future__"
                                or root.startswith("."), f"{path.name} imports {root}")
        self.assertEqual(self.imported_roots(ROOT / "src/price/__init__.py"), set())

    def test_the_runner_imports_only_the_standard_library_and_this_package(self):
        for root in self.imported_roots(ROOT / "scripts/price/baselines.py"):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                            root)

    def test_the_test_module_itself_stays_offline(self):
        for root in self.imported_roots(Path(__file__)):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"}, root)


if __name__ == "__main__":
    unittest.main()
