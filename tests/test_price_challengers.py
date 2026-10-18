"""PRICE-3: the challengers against the PRICE-2 baselines, offline.

Every case here builds its own synthetic series or its own group rows; no
network, model or cloud call is made and no repository fixture is read. The three
acceptance items carry named tests: a group is accepted only on an out-of-sample
gain with stable calibration (:class:`Gate`), no feature comes from after the
origin (:class:`FeatureContract`), and no skill is claimed where the baseline wins
(:class:`Gate` again, plus the walk's fold rules in :class:`WalkForward`).

The end-to-end case in :class:`CommandLine` writes a synthetic export, lets the
real PRICE-2 runner write the scorecard record it compares against, and runs the
challenger runner over both.
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
    LastWeekSameInterval,
    history_cutoff,
    last_ended_hour,
    window_for,
)
from src.price.challengers import (  # noqa: E402
    FEATURES,
    FOLD_COVERAGE_MIN_ORIGINS,
    SAME_HOUR_28D_MIN,
    SAME_HOUR_7D_MIN,
    BoostedTrees,
    GroupRow,
    HistoryIndex,
    OriginContext,
    Ridge,
    assess_claim,
    build_training_pool,
    default_challenger_factories,
    fit_folds,
    fold_definitions,
    fold_index_of,
    train_deadline,
    walk,
    week_block_bootstrap,
    window_end_of,
    weekly_sample,
)
from src.price.scorecard import AP, MARKET, slice_of  # noqa: E402
from src.price.series import (  # noqa: E402
    HOUR,
    REGIONAL_KEYS,
    HourRow,
    Series,
    billing_day_hours,
    billing_month_of,
    derive_marks,
    digest_file,
)

CSV_HEADER = "byear,bmonth,region_name,hour_start,n5,lwap_mean,lwap_min,lwap_max"


def scratch_directory(prefix="price3-"):
    """One test's scratch directory: the system temp dir, else an ignored repo path."""
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


def day_value(day: date) -> float:
    """The synthetic value of one billing day: constant inside the day, unique."""
    return day.day * 100.0 + day.month * 10.0


def make_rows(start: date, days: int, value_of=day_value, absent_hours=()) -> dict:
    rows = {}
    for day_index in range(days):
        day = start + timedelta(days=day_index)
        for hour in billing_day_hours(day):
            if hour in absent_hours:
                continue
            value = value_of(hour) if callable(value_of) else day_value(day)
            rows[hour] = HourRow(hour_start=hour, intervals=12, mean=float(value),
                                 ap_intervals=0, ap_known=False)
    return rows


def make_series(key="SYN", start=date(2023, 6, 26), days=400, **kwargs) -> Series:
    rows = make_rows(start, days, **kwargs)
    return Series(key=key, kind="regional", label=f"{key} synthetic", region="",
                  source="synthetic.csv", rows=rows)


def day_window_vectors(index, origin):
    context = OriginContext(index, origin)
    return context, [context.features(hour) for hour in window_for("day", origin).hours]


class FeatureContract(unittest.TestCase):
    """Acceptance: no feature comes from after the origin."""

    def test_the_vector_has_one_value_per_declared_feature(self):
        series = make_series()
        context, vectors = day_window_vectors(HistoryIndex(series), date(2023, 8, 3))
        self.assertEqual(len(FEATURES), len(context.features(billing_day_hours(
            date(2023, 8, 4))[0])))
        for vector in vectors:
            self.assertEqual(len(vector), len(FEATURES))

    def test_every_feature_is_the_same_when_every_later_row_is_deleted_or_altered(self):
        series = make_series(days=120)
        origin = date(2023, 9, 10)
        _, reference = day_window_vectors(HistoryIndex(series), origin)
        cutoff = last_ended_hour(history_cutoff(origin, 24))
        kept = {hour: row for hour, row in series.rows.items() if hour <= cutoff}
        stripped = Series(key="SYN", kind="regional", label="stripped", region="",
                          source="synthetic.csv", rows=kept)
        wild = dict(kept)
        for hour, row in series.rows.items():
            if hour > cutoff:
                wild[hour] = HourRow(hour_start=hour, intervals=12, mean=-999999.0,
                                     ap_intervals=0, ap_known=False)
        altered = Series(key="SYN", kind="regional", label="altered", region="",
                         source="synthetic.csv", rows=wild)
        for other in (stripped, altered):
            _, vectors = day_window_vectors(HistoryIndex(other), origin)
            self.assertEqual(vectors, reference)

    def test_the_cutoff_is_the_origin_minus_the_embargo(self):
        series = make_series()
        context = OriginContext(HistoryIndex(series), date(2023, 8, 3), 24)
        self.assertEqual(context.cutoff, datetime(2023, 8, 2))
        self.assertEqual(context.last_ended, datetime(2023, 8, 1, 23))
        self.assertLessEqual(context.last_ended + timedelta(hours=1), context.cutoff)

    def test_the_weekly_feature_is_the_baseline_weekly_sample(self):
        series = make_series(value_of=lambda hour: 100.0 + hour.day + hour.hour * 0.25)
        for origin in (date(2023, 8, 3), date(2023, 8, 4)):
            window = window_for("day", origin)
            forecast = LastWeekSameInterval().forecast(
                series, window, history_cutoff(origin, 24))
            context = OriginContext(HistoryIndex(series), origin, 24)
            for hour, sampled in zip(window.hours, forecast.values):
                vector = context.features(hour)
                self.assertEqual(vector[FEATURES.index("last_week_same_hour")], sampled)
                self.assertEqual(vector[FEATURES.index("weeks_back")], 1.0)

    def test_the_weekly_sample_steps_back_whole_weeks_for_a_long_window(self):
        series = make_series(value_of=lambda hour: 100.0 + hour.day + hour.hour * 0.25)
        origin = date(2023, 8, 3)
        window = window_for("week", origin)
        forecast = LastWeekSameInterval().forecast(series, window, history_cutoff(origin, 24))
        context = OriginContext(HistoryIndex(series), origin, 24)
        weeks = set()
        for hour in window.hours:
            vector = context.features(hour)
            weeks.add(int(vector[FEATURES.index("weeks_back")]))
            index = HistoryIndex(series)
            value, steps = weekly_sample(index, hour, context.last_ended)
            self.assertEqual(vector[FEATURES.index("last_week_same_hour")], value)
            self.assertEqual(vector[FEATURES.index("weeks_back")], float(steps))
        self.assertGreater(max(weeks), 1)
        self.assertIn(forecast.detail["weeks"], weeks)

    def test_a_thin_recent_history_is_refused_and_never_filled(self):
        series = make_series(days=90)
        last = max(series.rows)
        # every hour of the day before the cutoff is gone except the last one:
        # the level features have one hour to average and are therefore refused
        holes = {last - timedelta(hours=step) for step in range(2, 24)}
        thin = {hour: row for hour, row in series.rows.items() if hour not in holes}
        index = HistoryIndex(Series(key="SYN", kind="regional", label="thin", region="",
                                    source="synthetic.csv", rows=thin))
        origin = last.date() + timedelta(days=2)
        self.assertEqual(last_ended_hour(history_cutoff(origin, 24)), last)
        with self.assertRaises(BaselineError) as caught:
            OriginContext(index, origin, 24)
        self.assertEqual(caught.exception.code, "SHORT_RECENT_HISTORY")

    def test_an_origin_without_any_earlier_hour_is_refused(self):
        series = make_series(days=40)
        with self.assertRaises(BaselineError) as caught:
            OriginContext(HistoryIndex(series), date(2023, 6, 26), 24)
        self.assertEqual(caught.exception.code, "NO_HISTORY")

    def test_a_hour_whose_weekly_sample_is_missing_is_absent_from_the_vector(self):
        series = make_series(days=40)
        origin = date(2023, 8, 3)
        sample = window_for("day", origin).hours[5] - timedelta(days=7)
        holed = {hour: row for hour, row in series.rows.items() if hour != sample}
        index = HistoryIndex(Series(key="SYN", kind="regional", label="holed", region="",
                                    source="synthetic.csv", rows=holed))
        context = OriginContext(index, origin, 24)
        self.assertIsNone(context.features(window_for("day", origin).hours[5]))
        self.assertIsNotNone(context.features(window_for("day", origin).hours[6]))

    def test_the_seven_day_shape_floor_is_judged_on_the_seven_day_window(self):
        # one clock hour is present once in the last seven days but 22 times over
        # the last 28: the seven-day mean is refused as too thin, and the 28-day
        # mean beside it in the same pair is computed as usual
        series = make_series(days=90)
        last = max(series.rows)
        removed = {last - HOUR * (24 * step) for step in range(1, 7)}
        thin = {hour: row for hour, row in series.rows.items() if hour not in removed}
        index = HistoryIndex(Series(key="SYN", kind="regional", label="thin shape", region="",
                                    source="synthetic.csv", rows=thin))
        origin = last.date() + timedelta(days=2)
        self.assertEqual(last_ended_hour(history_cutoff(origin, 24)), last)
        context = OriginContext(index, origin, 24)
        seven_count, seven = index.same_hour_between(last.hour, last - HOUR * 167, last)
        twenty_eight_count, _ = index.same_hour_between(last.hour, last - HOUR * 671, last)
        self.assertLess(seven_count, SAME_HOUR_7D_MIN)
        self.assertGreaterEqual(twenty_eight_count, SAME_HOUR_28D_MIN)
        self.assertIsNotNone(seven)  # the mean is there; the count is what refuses it
        self.assertIsNone(context.shape_of_day(last.hour)[0])
        self.assertIsNotNone(context.shape_of_day(last.hour)[1])


class Models(unittest.TestCase):
    def test_ridge_recovers_a_linear_relation(self):
        rows = [(date(2024, 1, 1), (float(step), 2.0 * step), 50.0 + 3.0 * step)
                for step in range(200)]
        model = Ridge(alpha=1e-6).fit(rows)
        for step in (0, 40, 199):
            self.assertAlmostEqual(model.predict((float(step), 2.0 * step)), 50.0 + 3.0 * step,
                                   places=4)

    def test_ridge_shrinks_towards_the_training_mean_when_the_penalty_is_huge(self):
        rows = [(date(2024, 1, 1), (float(step),), 100.0 + step) for step in range(100)]
        shrunk = Ridge(alpha=1e12).fit(rows)
        self.assertAlmostEqual(shrunk.predict((200.0,)), 149.5, places=3)

    def test_boosted_trees_beat_a_constant_on_a_nonlinear_target(self):
        rows = []
        for day in range(20):
            for hour in range(24):
                feature = (float(hour), float(day % 7))
                target = 100.0 + 60.0 * (hour >= 18) + 4.0 * float(day % 7)
                rows.append((date(2024, 1, 1), feature, target))
        model = BoostedTrees().fit(rows)
        errors = [abs(model.predict(row[1]) - row[2]) for row in rows]
        constant = sum(abs(row[2] - 138.0) for row in rows) / len(rows)
        self.assertLess(sum(errors) / len(errors), constant * 0.7)

    def test_both_models_are_deterministic(self):
        rows = [(date(2024, 1, 1), (float(step % 24), float(step % 5)), 100.0 + (step % 13))
                for step in range(300)]
        for factory in default_challenger_factories():
            first = factory().fit(rows)
            second = factory().fit(rows)
            for step in range(0, 300, 37):
                self.assertEqual(first.predict(rows[step][1]), second.predict(rows[step][1]))

    def test_a_model_refuses_an_empty_training_set(self):
        for factory in default_challenger_factories():
            with self.assertRaises(BaselineError):
                factory().fit([])

    def test_a_model_refuses_to_predict_before_it_is_fitted(self):
        for factory in default_challenger_factories():
            with self.assertRaises(BaselineError) as caught:
                factory().predict((1.0,) * len(FEATURES))
            self.assertEqual(caught.exception.code, "NOT_FITTED")


class WalkForward(unittest.TestCase):
    def setUp(self):
        self.series = make_series(days=500)
        self.index = HistoryIndex(self.series)
        self.scored = [date(2024, 3, 1) + timedelta(days=step) for step in range(90)]
        self.folds = fold_definitions(self.scored, folds=3)
        self.pool = build_training_pool(self.index, self.series, derive_marks(self.series))

    def fitted(self, **kwargs):
        kwargs.setdefault("pool", self.pool)
        kwargs.setdefault("min_train_rows", 100)
        return fit_folds(self.index, self.series, self.folds,
                         default_challenger_factories(), **kwargs)

    def test_the_folds_are_equal_chronological_blocks_of_the_scored_origins(self):
        self.assertEqual([fold.first for fold in self.folds],
                         [date(2024, 3, 1), date(2024, 3, 31), date(2024, 4, 30)])
        self.assertEqual(fold_index_of(self.folds, date(2024, 2, 1)), 0)
        self.assertEqual(fold_index_of(self.folds, date(2024, 3, 1)), 0)
        self.assertEqual(fold_index_of(self.folds, date(2024, 4, 30)), 2)
        self.assertEqual(fold_index_of(self.folds, date(2030, 1, 1)), 2)

    def test_every_training_window_ended_before_the_fold_deadline(self):
        fitted = self.fitted()
        for entry in fitted:
            self.assertEqual(entry.deadline, train_deadline(entry.first, 24))
            if entry.train_last is None:
                continue
            self.assertLessEqual(window_end_of(entry.train_last), entry.deadline)
            self.assertLessEqual(entry.train_last, entry.first - timedelta(days=2))
        self.assertLess(fitted[0].train_rows, fitted[-1].train_rows)

    def test_the_training_pool_holds_only_settled_market_billing_days(self):
        marks = derive_marks(self.series)
        irregular = {date.fromisoformat(day) for day in marks.irregular_days}
        self.assertTrue(self.pool)
        for origin, _, _ in self.pool:
            window = window_for("day", origin)
            self.assertTrue(self.series.is_complete(window.hours))
            self.assertNotIn(origin, irregular)
            self.assertEqual(slice_of(self.series, window, marks), MARKET)
        self.assertLessEqual(max(origin for origin, _, _ in self.pool), self.series.last_day)

    def test_a_fold_with_too_few_rows_serves_nothing_and_says_so(self):
        fitted = self.fitted(min_train_rows=10 ** 6)
        self.assertTrue(all(entry.models is None for entry in fitted))
        self.assertTrue(all(entry.reason == "NO_TRAINING_DATA" for entry in fitted))
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=1)
        self.assertTrue(result.candidates)
        self.assertFalse(any(entry.served for entry in result.candidates))
        self.assertTrue(all(entry.reason == "NO_TRAINING_DATA" for entry in result.candidates))
        self.assertTrue(all(not entry.points for entry in result.candidates))

    def test_the_walk_serves_every_candidate_with_the_fold_that_covers_it(self):
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=3)
        self.assertTrue(result.candidates)
        for entry in result.candidates:
            if not entry.served:
                continue
            self.assertEqual(entry.fold, fold_index_of(self.folds, entry.origin))
            self.assertEqual(sorted(entry.points), ["boosted_trees", "ridge_regression"])
            self.assertAlmostEqual(entry.realized,
                                   self.series.window_mean(window_for("day", entry.origin).hours),
                                   places=6)
            for point in entry.points.values():
                self.assertEqual(point, point)  # finite, not a NaN
                self.assertLess(abs(point), 1e6)

    def test_an_origin_before_the_first_fold_is_withheld_with_no_forecast(self):
        # fold 0's models were fitted on settled days that lie after every origin
        # before the first fold, so those origins are served by nobody: no point,
        # no quantiles, and reason BEFORE_FIRST_FOLD
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=1)
        before = [entry for entry in result.candidates if entry.origin < self.folds[0].first]
        self.assertTrue(before)
        self.assertTrue(all(not entry.served for entry in before))
        self.assertTrue(all(entry.reason == "BEFORE_FIRST_FOLD" for entry in before))
        self.assertTrue(all(not entry.points and not entry.quantiles for entry in before))

    def test_every_forecast_comes_from_a_fold_fitted_before_the_origin(self):
        # the regression the review asked for: for every forecast the walk makes —
        # every origin whose residual can join a fan — the fold that made it had
        # finished training by the origin's own training deadline, so each settled
        # label the model read was readable as of the origin's cutoff
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=1)
        served = [entry for entry in result.candidates if entry.served]
        self.assertGreater(len(served), 20)
        for entry in served:
            fold = result.folds[entry.fold]
            self.assertGreaterEqual(entry.origin, self.folds[0].first)
            self.assertLessEqual(fold.deadline, train_deadline(entry.origin))
            self.assertLessEqual(fold.deadline,
                                 history_cutoff(entry.origin, 24) - timedelta(hours=24))
            if fold.train_last is not None:
                self.assertLessEqual(window_end_of(fold.train_last), fold.deadline)

    def test_the_fan_is_seeded_only_by_forecasts_that_were_as_of(self):
        # with the fan floor at one residual, the first fold's first origin has no
        # fan behind it at all — the reviewed code seeded it with pre-fold
        # forecasts whose models had seen later labels — and the fan fills from
        # served origins: a day window plus the embargo spans two days, so the
        # third served origin is the first that may read the first one's residual
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=1)
        served = [entry for entry in result.candidates if entry.served]
        self.assertGreaterEqual(len(served), 3)
        self.assertEqual(served[0].origin, self.folds[0].first)
        self.assertTrue(served[0].points)
        self.assertEqual(served[0].quantiles, {})
        self.assertEqual(served[1].quantiles, {})
        self.assertEqual(sorted(served[2].quantiles),
                         ["boosted_trees", "ridge_regression"])

    def test_the_fan_withholds_quantiles_until_it_has_enough_settled_errors(self):
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=12)
        served = [entry for entry in result.candidates if entry.served]
        self.assertGreater(len(served), 20)
        early = served[0]
        self.assertFalse(early.quantiles)
        later = served[-1]
        for name, triple in later.quantiles.items():
            self.assertEqual(list(triple), sorted(triple), name)

    def test_every_challenger_keeps_the_same_denominator(self):
        fitted = self.fitted()
        result = walk(self.index, self.series, "day", fitted, self.folds, min_fan_samples=3)
        served = [entry for entry in result.candidates if entry.served]
        for name in ("ridge_regression", "boosted_trees"):
            self.assertEqual(result.served_by(name), len(served))

    def test_an_origin_the_context_refuses_is_recorded_unserved(self):
        fitted = self.fitted()
        # the hours before the origin's cutoff are gone except the last one, so the
        # origin's own window is complete but its level features are not available
        holes = {datetime(2024, 3, 30, hour) for hour in range(23)}
        thin = {hour: row for hour, row in self.series.rows.items() if hour not in holes}
        series = Series(key="SYN", kind="regional", label="thin", region="",
                        source="synthetic.csv", rows=thin)
        result = walk(HistoryIndex(series), series, "day", fitted, self.folds, min_fan_samples=3)
        entry = next(item for item in result.candidates if item.origin == date(2024, 4, 1))
        self.assertFalse(entry.served)
        self.assertEqual(entry.reason, "SHORT_RECENT_HISTORY")
        self.assertFalse(entry.points)
        self.assertIn(date(2024, 4, 1), {item.origin for item in result.candidates})

    def test_a_window_that_settles_after_the_origin_never_joins_that_origin_fan(self):
        fitted = self.fitted()
        result = walk(self.index, self.series, "week", fitted, self.folds, min_fan_samples=1)
        served = [entry for entry in result.candidates if entry.served]
        self.assertGreater(len(served), 10)
        self.assertFalse(served[0].quantiles)
        first_with_quantiles = next(entry.origin for entry in served if entry.quantiles)
        # a week window ends seven days after its origin and needs the embargo on
        # top of that before its residual may be used, so the earliest fan entry
        # for a later origin is eight days behind
        self.assertGreaterEqual(first_with_quantiles - served[0].origin, timedelta(days=8))


class Gate(unittest.TestCase):
    """Acceptance: a claim needs an out-of-sample gain with stable calibration."""

    def rows(self, challenger_offset, baseline_offset, folds=(0, 1), coverage_breaks=0,
             challenger_by_fold=None, per_fold=30, start=date(2024, 1, 1)):
        rows = []
        for step in range(per_fold * len(folds)):
            realized = 100.0
            offset = challenger_offset
            if challenger_by_fold is not None:
                offset = challenger_by_fold[folds[step % len(folds)]]
            point = realized + offset
            quantiles = (point - 5.0, point, point + 5.0)
            if step < coverage_breaks:
                quantiles = (point + 50.0, point + 50.0, point + 60.0)
            rows.append(GroupRow(origin=start + timedelta(days=step),
                                 fold=folds[step % len(folds)], realized=realized,
                                 baseline={"persistence": realized + baseline_offset},
                                 point=point, quantiles=quantiles))
        return rows

    def test_a_challenger_that_beats_the_baseline_with_a_calibrated_interval_claims(self):
        # six folds of seventy judged origins each: every fold is measurable, every
        # fold above the coverage floor, and the claim is the evidence for it
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0,
                         folds=(0, 1, 2, 3, 4, 5), per_fold=70, coverage_breaks=6)
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=len(rows),
                              name="ridge_regression")
        self.assertTrue(report["claim"], report["reasons"])
        self.assertEqual(report["basis"], "persistence")
        self.assertGreater(report["gain_mae"], 0.0)
        self.assertGreater(report["bootstrap"]["low"], 0.0)
        self.assertEqual(report["fold_coverage_assessed"], 6)
        self.assertEqual(report["fold_coverage_stable"], 6)
        self.assertEqual(report["fold_coverage_needed"], 4)

    def test_fold_calibration_that_cannot_be_assessed_leaves_no_claim(self):
        # the gain is large and significant and the interval covers 96% of the
        # origins, but a third of the fold minimum of judged origins in every fold
        # measures no fold coverage at all: there is no calibration evidence, and
        # the claim is refused rather than accepted on an empty check
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0,
                         folds=(0, 1, 2, 3, 4), per_fold=FOLD_COVERAGE_MIN_ORIGINS // 3,
                         coverage_breaks=4)
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=len(rows),
                              name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("calibration_not_stable", report["reasons"])
        self.assertNotIn("interval_miscalibrated", report["reasons"])
        self.assertEqual(report["fold_coverage"], [])
        self.assertEqual(report["fold_coverage_assessed"], 0)
        self.assertEqual(report["fold_coverage_folds"], 5)
        self.assertEqual(report["fold_coverage_needed"], 4)
        self.assertGreater(report["gain_mae"], 0.0)
        self.assertGreater(report["bootstrap"]["low"], 0.0)

    def test_a_fold_that_cannot_be_measured_counts_against_fold_stability(self):
        # three folds carry seventy judged origins each and are stable; three more
        # carry ten each and cannot be measured: the two thirds are of the group's
        # six folds, so three stable folds of six are not enough
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0,
                         folds=(0, 1, 2), per_fold=FOLD_COVERAGE_MIN_ORIGINS + 10,
                         coverage_breaks=4)
        rows += self.rows(challenger_offset=1.0, baseline_offset=20.0,
                          folds=(3, 4, 5), per_fold=10, start=date(2024, 6, 1))
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=len(rows),
                              name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("calibration_not_stable", report["reasons"])
        self.assertEqual(report["fold_coverage_assessed"], 3)
        self.assertEqual(report["fold_coverage_stable"], 3)
        self.assertEqual(report["fold_coverage_folds"], 6)
        self.assertEqual(report["fold_coverage_needed"], 4)

    def test_the_baseline_wins_leaves_no_claim(self):
        rows = self.rows(challenger_offset=30.0, baseline_offset=1.0)
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=60, name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("baseline_wins", report["reasons"])
        self.assertLess(report["gain_mae"], 0.0)

    def test_a_gain_that_does_not_hold_across_folds_leaves_no_claim(self):
        # three folds win by 19 and three lose by 1: the overall gain is positive and
        # significant, but it does not hold in four of the six folds
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0,
                         folds=(0, 1, 2, 3, 4, 5), coverage_breaks=6,
                         challenger_by_fold={0: 1.0, 1: 1.0, 2: 1.0,
                                             3: 21.0, 4: 21.0, 5: 21.0})
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=60, name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("gain_not_stable", report["reasons"])
        self.assertEqual(report["folds_positive"], 3)
        self.assertEqual(report["folds_needed"], 4)
        self.assertGreater(report["gain_mae"], 0.0)
        self.assertGreater(report["bootstrap"]["low"], 0.0)

    def test_an_interval_that_covers_almost_nothing_is_miscalibrated(self):
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0, coverage_breaks=40)
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=60, name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("interval_miscalibrated", report["reasons"])
        self.assertLessEqual(report["calibration"]["coverage"], 0.6)

    def test_a_vacuous_interval_is_miscalibrated(self):
        rows = []
        for step in range(60):
            rows.append(GroupRow(origin=date(2024, 1, 1) + timedelta(days=step), fold=0,
                                 realized=100.0, baseline={"persistence": 120.0}, point=101.0,
                                 quantiles=(-1e6, 101.0, 1e6)))
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=60, name="ridge_regression")
        self.assertFalse(report["claim"])
        self.assertIn("interval_miscalibrated", report["reasons"])
        self.assertEqual(report["calibration"]["coverage"], 1.0)

    def test_the_administered_pricing_slice_never_claims(self):
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0,
                         folds=(0, 1, 2, 3, 4, 5), per_fold=70, coverage_breaks=6)
        report = assess_claim(rows, slice_name=AP, scored_in_record=len(rows), name="ridged")
        self.assertFalse(report["claim"])
        self.assertEqual(report["reasons"], ["administered_pricing_slice"])
        market = assess_claim(rows, slice_name=MARKET, scored_in_record=len(rows), name="ridged")
        self.assertTrue(market["claim"])

    def test_a_comparison_that_loses_too_many_origins_leaves_no_claim(self):
        rows = self.rows(challenger_offset=1.0, baseline_offset=20.0, coverage_breaks=6)
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=200, name="ridged")
        self.assertFalse(report["claim"])
        self.assertIn("denominators_differ", report["reasons"])
        self.assertAlmostEqual(report["common_share"], 0.3)

    def test_the_second_baseline_is_the_basis_when_it_is_the_better_one(self):
        rows = []
        for step in range(60):
            point = 101.0
            rows.append(GroupRow(
                origin=date(2024, 1, 1) + timedelta(days=step), fold=step % 2, realized=100.0,
                baseline={"persistence": 140.0, "last_week_same_interval": 110.0},
                point=point, quantiles=(point - 5.0, point, point + 5.0)))
        report = assess_claim(rows, slice_name=MARKET, scored_in_record=60, name="ridged")
        self.assertEqual(report["basis"], "last_week_same_interval")
        self.assertGreater(report["bootstrap"]["low"], 0.0)

    def test_the_bootstrap_interval_is_deterministic_and_excludes_zero_on_a_clear_gain(self):
        blocks = {(2024, 1): (10, 200.0, 10.0), (2024, 2): (10, 180.0, 12.0),
                  (2024, 3): (10, 220.0, 9.0)}
        first = week_block_bootstrap(blocks, resamples=200, seed=7)
        second = week_block_bootstrap(blocks, resamples=200, seed=7)
        self.assertEqual(first, second)
        self.assertGreater(first["low"], 0.0)
        reversed_blocks = {(year, week): (count, challenger, baseline)
                           for (year, week), (count, baseline, challenger) in blocks.items()}
        self.assertLess(week_block_bootstrap(reversed_blocks, resamples=200, seed=7)["high"],
                        0.0)

    def test_no_origins_served_is_reported_not_claimed(self):
        report = assess_claim([], slice_name=MARKET, scored_in_record=10, name="ridged")
        self.assertFalse(report["claim"])
        self.assertEqual(report["metrics"]["count"], 0)


class CommandLine(unittest.TestCase):
    """The runner: exports and the scorecard in, the comparison record out."""

    SPEC = importlib.util.spec_from_file_location(
        "price_challengers_cli", ROOT / "scripts" / "price" / "challengers.py")
    BASELINE_SPEC = importlib.util.spec_from_file_location(
        "price_baselines_cli", ROOT / "scripts" / "price" / "baselines.py")

    def load(self, spec):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write_export(self, directory, days=460, start=date(2023, 6, 26)):
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

    def scorecard(self, path, digests, directory):
        cli = self.load(self.BASELINE_SPEC)
        out = Path(directory) / "scorecard.json"
        with contextlib.redirect_stdout(io.StringIO()):
            status = cli.main(["--regional", str(path), "--digests", str(digests),
                               "--out", str(out), "--series", "regional",
                               "--summary-series", "none", "--min-fan-samples", "3"])
        self.assertEqual(status, 0)
        return out

    def run_cli(self, argv):
        cli = self.load(self.SPEC)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = cli.main(argv)
        return status, stdout.getvalue()

    def test_it_writes_a_record_whose_digest_matches_its_bytes(self):
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp)
            scorecard = self.scorecard(path, digests, tmp)
            out = Path(tmp) / "challengers.json"
            status, stdout = self.run_cli([
                "--regional", str(path), "--digests", str(digests),
                "--scorecard", str(scorecard), "--out", str(out),
                "--series", "regional", "--summary-series", "none",
                "--folds", "3", "--min-train-rows", "100", "--min-fan-samples", "3"])
            self.assertEqual(status, 0)
            written = out.read_bytes()
            self.assertFalse(written.endswith(b"\n"))
            digest = hashlib.sha256(written).hexdigest()
            self.assertIn(f"content_digest {digest}", stdout)
            record = json.loads(written.decode("utf-8"))
            self.assertEqual(record["kind"], "price-challenger-comparison")
            self.assertEqual(record["inputs"]["scorecard"]["sha256"], digest_file(scorecard))
            self.assertEqual(record["inputs"]["exports"][0]["sha256"], digest_file(path))
            self.assertEqual([entry["key"] for entry in record["series"]], list(REGIONAL_KEYS))
            self.assertEqual(written.decode("utf-8"),
                             json.dumps(record, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False, allow_nan=False))

    def test_the_record_carries_every_horizon_group_with_both_sides(self):
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp)
            scorecard = self.scorecard(path, digests, tmp)
            out = Path(tmp) / "challengers.json"
            status, _ = self.run_cli([
                "--regional", str(path), "--digests", str(digests),
                "--scorecard", str(scorecard), "--out", str(out),
                "--series", "regional", "--summary-series", "none",
                "--folds", "3", "--min-train-rows", "100", "--min-fan-samples", "3"])
            self.assertEqual(status, 0)
            record = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(record["data_label"].split(" (")[0], "pre-backfill exports")
            self.assertEqual(record["config"]["features"], list(FEATURES))
            for series in record["series"]:
                self.assertEqual([entry["horizon"] for entry in series["horizons"]],
                                 ["day", "week", "month"])
                self.assertEqual(len(series["folds"]), 3)
                self.assertGreater(series["horizons"][0]["slices"][MARKET]["scored_in_record"], 0)
                for horizon in series["horizons"]:
                    for slice_name in (MARKET, AP):
                        group = horizon["slices"][slice_name]
                        self.assertEqual(group["realized_mismatches"], 0)
                        self.assertEqual(group["served"] + len(group["origins_not_served"]),
                                         group["scored_in_record"])
                        for report in group["challengers"].values():
                            self.assertIn("claim", report)
                            self.assertIn("calibration", report)
                            self.assertEqual(report["metrics"]["count"], group["served"])
                            if slice_name == AP:
                                self.assertFalse(report["claim"])

    def test_the_record_withholds_the_origins_before_the_first_fold(self):
        # a span with no administered-pricing months, so every day before the first
        # scored origin is a complete market candidate and the withheld count is
        # exactly the gap: candidates before the first fold are the withheld set
        start = date(2023, 1, 1)
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp, start=start)
            scorecard = self.scorecard(path, digests, tmp)
            out = Path(tmp) / "challengers.json"
            status, _ = self.run_cli([
                "--regional", str(path), "--digests", str(digests),
                "--scorecard", str(scorecard), "--out", str(out),
                "--series", "regional", "--summary-series", "none",
                "--folds", "3", "--min-train-rows", "100", "--min-fan-samples", "3"])
            self.assertEqual(status, 0)
            record = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("model fitted before its own origin", record["config"]["quantile_rule"])
            for series in record["series"]:
                first_fold = date.fromisoformat(series["folds"][0]["first_origin"])
                expected = (first_fold - start).days
                self.assertGreater(expected, 0)
                for horizon in series["horizons"]:
                    self.assertEqual(horizon["served"] + sum(horizon["unserved"].values()),
                                     horizon["candidates"])
                    if horizon["horizon"] in ("day", "week"):
                        self.assertEqual(
                            horizon["unserved"].get("BEFORE_FIRST_FOLD", 0), expected,
                            horizon["horizon"])

    def test_the_summary_reports_both_sides_and_the_verdict(self):
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp)
            scorecard = self.scorecard(path, digests, tmp)
            status, stdout = self.run_cli([
                "--regional", str(path), "--digests", str(digests),
                "--scorecard", str(scorecard), "--series", "regional",
                "--summary-series", "regional", "--folds", "3",
                "--min-train-rows", "100", "--min-fan-samples", "3"])
            self.assertEqual(status, 0)
            for token in ("ridge_regression", "boosted_trees", "persistence",
                          "last_week_same_interval", "claim", "pre-backfill exports"):
                self.assertIn(token, stdout)

    def test_a_tampered_export_fails_with_a_digest_error(self):
        with scratch_directory() as tmp:
            path, digests = self.write_export(tmp, days=40)
            scorecard = self.scorecard(path, digests, tmp)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("2026,8,CLUZ,2026-08-25 10:00:00,12,1.0,1.0,1.0\n")
            cli = self.load(self.SPEC)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = cli.main(["--regional", str(path), "--digests", str(digests),
                                   "--scorecard", str(scorecard), "--summary-series", "none"])
            self.assertEqual(status, 2)
            self.assertIn("DIGEST_MISMATCH", stderr.getvalue())


class StdlibOnly(unittest.TestCase):
    def imported_roots(self, path):
        text = path.read_text(encoding="utf-8")
        roots = set()
        for name in re.findall(r"^import ([A-Za-z0-9_.]+)", text, re.M):
            roots.add(name.split(".")[0])
        for name in re.findall(r"^from (\.?[A-Za-z0-9_.]+) import", text, re.M):
            roots.add(name if name.startswith(".") else name.split(".")[0])
        return roots

    def test_the_challenger_module_imports_only_the_standard_library(self):
        path = ROOT / "src" / "price" / "challengers.py"
        for root in self.imported_roots(path):
            self.assertTrue(root in sys.stdlib_module_names or root == "__future__"
                            or root.startswith("."), root)

    def test_the_runner_imports_only_the_standard_library_and_this_package(self):
        for root in self.imported_roots(ROOT / "scripts" / "price" / "challengers.py"):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                            root)

    def test_the_test_module_itself_stays_offline(self):
        for root in self.imported_roots(Path(__file__)):
            self.assertTrue(root in sys.stdlib_module_names or root in {"src", "__future__"},
                            root)


if __name__ == "__main__":
    unittest.main()
