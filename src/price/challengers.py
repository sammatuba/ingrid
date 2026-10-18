"""PRICE-3: the challengers — a regularized regression and a boosted model.

The comparison
==============
PRICE-2 scored three naive baselines over a blocked rolling origin with a one-day
embargo (:mod:`src.price.baselines`, :mod:`src.price.scorecard`). This module adds
two *trained* challengers against the same target: the interval-weighted mean
price of the window that begins at the origin, at the day, week and month
horizons.

* **ridge regression** — a linear model over fourteen features (calendar
  encodings, the as-of weekly sample, the recent level, and the recent shape of
  the same clock hour), fitted on standardized features with an L2 penalty.
* **boosted trees** — a small gradient-boosted regression-tree ensemble
  (histogram splits, squared loss, subsampled rows) over the same features.

Nothing a model reads comes from after the origin
=================================================
Every feature is a function of exported rows that *ended* at or before the
origin's history cutoff (``origin - embargo``), exactly as in PRICE-2: the level
features average the hours that ended before the cutoff, the weekly feature
samples the same clock hour the smallest whole number of weeks earlier that ended
before the cutoff (PRICE-2's own rule), and the calendar features are properties
of the target hour itself. A feature that cannot be computed is *absent*: the
training row is dropped, and an origin whose window needs it is recorded as
unserved and never filled or imputed.

The walk-forward
================
The scored origins of one series are cut into chronological folds — equal counts
of the day-horizon origins the PRICE-2 record scored, so the fold edges are the
same for the day, week and month walks. A fold's models are fitted once, on
**training rows**: one row per hour of a settled billing day — a day whose 24
hours are all present and carry every interval, whose window is a market window,
and whose window *ended*, plus the embargo, before the fold's own history cutoff.
The models fitted for a fold then forecast every candidate origin of that fold,
and no others: an origin that precedes the fold that covers it — on this design,
every candidate before the first fold — is *withheld* (recorded unserved as
``BEFORE_FIRST_FOLD``) because the only model that could forecast it was fitted
on settled days that lie ahead of it. A withheld origin contributes no residual,
so every fan is seeded only by forecasts that were out of sample. The comparison
is read on the origins the PRICE-2 scorecard scored, so both sides share one
denominator. There is no random split and no shuffled origin: a forecast of 2022
is never made by a model that has seen 2023.

What "accepted" means here
==========================
:func:`assess_claim` is the gate the acceptance names — a challenger carries a
skill claim on a (series, horizon, market) group only when it beats the *best*
of the three PRICE-2 baselines on the same origins out of sample (lower MAE and
lower RMSE, with the week-block bootstrap interval of the MAE gain excluding
zero), when that gain holds in at least two thirds of the folds, and when its own
p10-p90 interval is calibrated (it covers between 60 % and 99 % of the scored
origins overall, and at least 55 % in two thirds of the group's folds — a fold
that holds fewer than 60 judged origins measures nothing and counts as a fold
that fails, so a group with no measurable fold carries no claim). Both sides are
scored on the origins the challenger serves, using the record's own per-origin
baseline points, so the comparison keeps one denominator; the group may still
claim only while that common set keeps at least 95 % of the origins the record
scored. Where the baseline wins there is no claim, and the administered-pricing
slice is never market skill. The bands are fixed constants here, stated before
the run, never fitted to it.
"""
from __future__ import annotations

import math
import random
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Mapping, Sequence

from .baselines import (
    BaselineError,
    aggregate,
    candidate_origins,
    history_cutoff,
    last_ended_hour,
    window_for,
)
from .scorecard import (
    MARKET,
    MIXED,
    ErrorFan,
    Metrics,
    metrics_from,
    ordered_quantiles,
    quantile,
    slice_of,
)
from .series import (
    HOUR,
    INTERVALS_PER_HOUR,
    WEEK_HOURS,
    Marks,
    Series,
    billing_month_of,
    derive_marks,
)

VERSION = "price-3.1"
KIND = "price-challenger-comparison"

#: The feature vector, in the order :meth:`OriginContext.features` returns it.
FEATURES: tuple[str, ...] = (
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "billing_month_sin",
    "billing_month_cos", "weekend", "last_week_same_hour", "weeks_back",
    "mean_last_24h", "mean_last_168h", "trend", "same_hour_7d", "same_hour_28d",
)

#: Presence floors below which an as-of average is refused rather than computed
#: from too few hours. They are validity conditions on a feature, not prices:
#: nothing is filled in for the hours that are not there.
MEAN24_MIN_HOURS = 12
MEAN168_MIN_HOURS = 84
SAME_HOUR_7D_MIN = 4
SAME_HOUR_28D_MIN = 14

#: The gate (pre-stated; see the module docstring). The bootstrap is the
#: week-block bootstrap of the training record's stability check, applied to the
#: MAE gain of one origin block at a time.
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 0
BOOTSTRAP_LEVEL = 0.95
COVERAGE_FLOOR = 0.60
COVERAGE_CEILING = 0.99
FOLD_COVERAGE_FLOOR = 0.55
FOLD_COVERAGE_MIN_ORIGINS = 60
FOLD_GAIN_SHARE = 2.0 / 3.0

#: The share of the PRICE-2 scored origins a group has to keep before it may
#: carry a claim: a challenger that cannot serve the origins right after the
#: four-month gap (2025-09 to 2025-12) loses those from both sides of the
#: comparison, and that is allowed only while it costs a few per cent.
MIN_COMMON_SHARE = 0.95

TrainingRow = tuple[date, tuple[float, ...], float]


# --- the as-of index -------------------------------------------------------


class HistoryIndex:
    """One series' exported rows indexed for as-of queries (nothing later, ever).

    The index is built once and is read-only: every query takes a closed range of
    ``hour_start`` values that the caller has already limited to the cutoff, and
    a range with no row answers with a count of zero instead of a value, so a
    missing hour can never be averaged in.
    """

    def __init__(self, series: Series) -> None:
        self.series = series
        hours = series.hours
        self.hours = hours
        weight_prefix = [0]
        value_prefix = [0.0]
        by_hour: list[list[datetime]] = [[] for _ in range(24)]
        for hour in hours:
            row = series.rows[hour]
            weight_prefix.append(weight_prefix[-1] + row.intervals)
            value_prefix.append(value_prefix[-1] + row.mean * row.intervals)
            by_hour[hour.hour].append(hour)
        self._weights = tuple(weight_prefix)
        self._values = tuple(value_prefix)
        self._by_hour = tuple(tuple(entry) for entry in by_hour)

    def weight_between(self, first: datetime, last: datetime) -> tuple[int, float | None]:
        """Rows whose ``hour_start`` lies in ``[first, last]``: count and weighted mean."""
        left = bisect_left(self.hours, first)
        right = bisect_right(self.hours, last)
        if right <= left:
            return 0, None
        weight = self._weights[right] - self._weights[left]
        return right - left, (self._values[right] - self._values[left]) / weight

    def same_hour_between(self, clock: int, first: datetime,
                          last: datetime) -> tuple[int, float | None]:
        """Rows at one clock hour inside ``[first, last]``: count and weighted mean."""
        sequence = self._by_hour[clock]
        left = bisect_left(sequence, first)
        right = bisect_right(sequence, last)
        if right <= left:
            return 0, None
        total, weight = 0.0, 0
        for hour in sequence[left:right]:
            row = self.series.rows[hour]
            total += row.mean * row.intervals
            weight += row.intervals
        return right - left, total / weight


def weekly_sample(index: HistoryIndex, hour: datetime,
                  last_ended: datetime) -> tuple[float, int]:
    """The weekly sample of one target hour: the same clock hour, whole weeks back.

    The rule is PRICE-2's ``last week same interval`` sample, used here as a
    feature: the smallest whole number of weeks earlier whose hour ended at or
    before the cutoff, and the sampled hour must be a complete exported hour.
    """
    sample = hour - HOUR * WEEK_HOURS
    weeks = 1
    while sample > last_ended:
        sample -= HOUR * WEEK_HOURS
        weeks += 1
    row = index.series.rows.get(sample)
    if row is None or row.intervals != INTERVALS_PER_HOUR:
        raise BaselineError("INCOMPLETE_WEEK", sample.isoformat())
    return row.mean, weeks


class OriginContext:
    """Everything a forecast at one origin may read, taken as of its cutoff.

    The constructor refuses an origin whose recent history is too thin to make
    its level features mean anything (:data:`MEAN24_MIN_HOURS`,
    :data:`MEAN168_MIN_HOURS`); :meth:`features` answers ``None`` for a target
    hour whose weekly sample, 7-day or 28-day shape is not there. Neither
    refusal is ever replaced by a neighbouring hour, a carried-forward value or
    an interpolated one.
    """

    def __init__(self, index: HistoryIndex, origin: date, embargo_hours: int = 24,
                 extra: Callable[[datetime], tuple[float, ...] | None] | None = None) -> None:
        self.index = index
        self.origin = origin
        self.embargo_hours = embargo_hours
        self.cutoff = history_cutoff(origin, embargo_hours)
        self.last_ended = last_ended_hour(self.cutoff)
        series = index.series
        if self.last_ended not in series.rows:
            raise BaselineError("NO_HISTORY", f"no hour ended at or before {self.cutoff}")
        self.last_row_hour = self.last_ended
        count, mean = index.weight_between(self.last_ended - HOUR * 23, self.last_ended)
        if count < MEAN24_MIN_HOURS or mean is None:
            raise BaselineError("SHORT_RECENT_HISTORY", f"{count} of 24 hours before the cutoff")
        self.mean_24h = mean
        count, mean = index.weight_between(self.last_ended - HOUR * 167, self.last_ended)
        if count < MEAN168_MIN_HOURS or mean is None:
            raise BaselineError("SHORT_WEEK_HISTORY", f"{count} of 168 hours before the cutoff")
        self.mean_168h = mean
        self.trend = (self.mean_24h - self.mean_168h) / (abs(self.mean_168h) + 1.0)
        # Optional extra features (for example fuel prices), read once as of the same
        # cutoff. ``None`` means one is not yet published or too stale: the vector is
        # then absent, exactly like a missing price feature.
        self.extra: tuple[float, ...] | None = () if extra is None else extra(self.cutoff)
        self._shape: dict[int, tuple[float | None, float | None]] = {}

    def shape_of_day(self, clock: int) -> tuple[float | None, float | None]:
        """The 7-day and 28-day means of one clock hour, as of the cutoff.

        Each mean is judged by its own window's presence count: a seven-day mean
        taken from fewer than :data:`SAME_HOUR_7D_MIN` hours is refused as absent
        however rich the 28-day window is, and the 28-day mean likewise.
        """
        if clock not in self._shape:
            seven_count, seven = self.index.same_hour_between(
                clock, self.last_ended - HOUR * 167, self.last_ended)
            twenty_eight_count, twenty_eight = self.index.same_hour_between(
                clock, self.last_ended - HOUR * 671, self.last_ended)
            self._shape[clock] = (
                seven if seven_count >= SAME_HOUR_7D_MIN else None,
                twenty_eight if twenty_eight_count >= SAME_HOUR_28D_MIN else None,
            )
        return self._shape[clock]

    def features(self, hour: datetime) -> tuple[float, ...] | None:
        """The feature vector of one target hour, or ``None`` when one is absent."""
        seven, twenty_eight = self.shape_of_day(hour.hour)
        if seven is None or twenty_eight is None or self.extra is None:
            return None
        try:
            last_week, weeks_back = weekly_sample(self.index, hour, self.last_ended)
        except BaselineError:
            return None
        _, month = billing_month_of(hour)
        hour_angle = 2.0 * math.pi * hour.hour / 24.0
        day_angle = 2.0 * math.pi * hour.weekday() / 7.0
        month_angle = 2.0 * math.pi * ((month - 1) % 12) / 12.0
        return (
            math.sin(hour_angle), math.cos(hour_angle),
            math.sin(day_angle), math.cos(day_angle),
            math.sin(month_angle), math.cos(month_angle),
            1.0 if hour.weekday() >= 5 else 0.0,
            last_week, float(weeks_back),
            self.mean_24h, self.mean_168h, self.trend,
            seven, twenty_eight,
        ) + self.extra


# --- the challengers -------------------------------------------------------


def _cholesky_solve(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    """Solve a symmetric positive-definite system by Cholesky factorisation."""
    size = len(vector)
    lower = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1):
            total = matrix[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if total <= 0.0:
                    raise BaselineError("RIDGE_NOT_POSITIVE_DEFINITE", str(total))
                lower[i][j] = math.sqrt(total)
            else:
                lower[i][j] = total / lower[j][j]
    forward = [0.0] * size
    for i in range(size):
        total = vector[i] - sum(lower[i][k] * forward[k] for k in range(i))
        forward[i] = total / lower[i][i]
    solution = [0.0] * size
    for i in range(size - 1, -1, -1):
        total = forward[i] - sum(lower[k][i] * solution[k] for k in range(i + 1, size))
        solution[i] = total / lower[i][i]
    return solution


class Ridge:
    """Ridge regression on standardized features (closed form, no tuning on test).

    ``alpha`` is fixed in the constructor and never chosen on a scored origin:
    the penalty is applied to the standardized coefficients, and the intercept is
    the training mean of the target.
    """

    name = "ridge_regression"
    version = VERSION

    def __init__(self, alpha: float = 100.0) -> None:
        self.alpha = float(alpha)
        self.hyperparameters: Mapping[str, object] = {"alpha": self.alpha,
                                                      "standardized": True}
        self.formula = (
            "point(hour) = mean_target + sum_j w_j * (x_j - mean_j) / sd_j, with w the "
            "solution of (X'X + alpha I) w = X'y over the standardized training rows"
        )
        self.means: tuple[float, ...] = ()
        self.deviations: tuple[float, ...] = ()
        self.weights: tuple[float, ...] = ()
        self.intercept = 0.0

    def fit(self, rows: Sequence[TrainingRow]) -> "Ridge":
        if not rows:
            raise BaselineError("NO_TRAINING_ROWS")
        count = len(rows)
        width = len(rows[0][1])
        means = [sum(row[1][j] for row in rows) / count for j in range(width)]
        deviations = []
        for j in range(width):
            variance = sum((row[1][j] - means[j]) ** 2 for row in rows) / count
            deviations.append(math.sqrt(variance) or 1.0)
        target_mean = sum(row[2] for row in rows) / count
        gram = [[0.0] * width for _ in range(width)]
        right = [0.0] * width
        for _, vector, target in rows:
            scaled = [(vector[j] - means[j]) / deviations[j] for j in range(width)]
            centred = target - target_mean
            for a in range(width):
                value = scaled[a]
                row_a = gram[a]
                for b in range(a + 1):
                    row_a[b] += value * scaled[b]
                right[a] += value * centred
        for a in range(width):
            gram[a][a] += self.alpha
            for b in range(a):
                gram[b][a] = gram[a][b]
        self.means = tuple(means)
        self.deviations = tuple(deviations)
        self.weights = tuple(_cholesky_solve(gram, right))
        self.intercept = target_mean
        return self

    def predict(self, features: Sequence[float]) -> float:
        if not self.weights:
            raise BaselineError("NOT_FITTED", self.name)
        return self.intercept + sum(
            weight * (value - mean) / deviation
            for weight, value, mean, deviation in zip(
                self.weights, features, self.means, self.deviations)
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "formula": self.formula,
                "hyperparameters": dict(self.hyperparameters)}


class BoostedTrees:
    """Gradient-boosted regression trees over histogram splits (squared loss).

    The ensemble is small and fully deterministic: the feature bins come from the
    training rows, the row subsample of each tree comes from a seeded generator,
    and the leaf value is the shrunk mean residual with an L2 denominator. No
    early stopping, no validation split and no tuning on a scored origin.
    """

    name = "boosted_trees"
    version = VERSION

    def __init__(self, trees: int = 40, depth: int = 3, learning_rate: float = 0.08,
                 subsample: float = 0.25, bins: int = 16, min_leaf: int = 40,
                 l2: float = 1.0, seed: int = 0) -> None:
        self.trees = int(trees)
        self.depth = int(depth)
        self.learning_rate = float(learning_rate)
        self.subsample = float(subsample)
        self.bins = int(bins)
        self.min_leaf = int(min_leaf)
        self.l2 = float(l2)
        self.seed = int(seed)
        self.hyperparameters: Mapping[str, object] = {
            "trees": self.trees, "depth": self.depth, "learning_rate": self.learning_rate,
            "subsample": self.subsample, "bins": self.bins, "min_leaf": self.min_leaf,
            "l2": self.l2, "seed": self.seed,
        }
        self.formula = (
            "point(hour) = base + learning_rate * the sum of the leaves of `trees` "
            "regression trees fitted to the residuals of the previous ones; splits are "
            "histogram cuts of `bins` quantile bins per feature on a seeded subsample of "
            "`subsample` of the training rows"
        )
        self.width = 0
        self.base = 0.0
        self.cuts: tuple[tuple[float, ...], ...] = ()
        self.nodes: list[list[float]] = []
        self.roots: list[int] = []

    def _cut_points(self, values: Sequence[float]) -> tuple[float, ...]:
        ordered = sorted(values)
        if len(ordered) <= self.bins:
            return tuple(dict.fromkeys(ordered))[:-1] if len(ordered) > 1 else ()
        return tuple(
            ordered[min(len(ordered) - 1, max(0, int(round(step * len(ordered) / self.bins))))]
            for step in range(1, self.bins)
        )

    def fit(self, rows: Sequence[TrainingRow]) -> "BoostedTrees":
        if not rows:
            raise BaselineError("NO_TRAINING_ROWS")
        width = len(rows[0][1])
        self.width = width
        targets = [row[2] for row in rows]
        self.base = sum(targets) / len(targets)
        self.cuts = tuple(self._cut_points([row[1][j] for row in rows]) for j in range(width))
        binned = [tuple(bisect_right(self.cuts[j], row[1][j]) for j in range(width))
                  for row in rows]
        predictions = [self.base] * len(rows)
        generator = random.Random(self.seed)
        for _ in range(self.trees):
            residuals = [target - prediction for target, prediction in zip(targets, predictions)]
            index = self._subsample(len(rows), generator)
            root = self._grow(binned, residuals, index, self.depth)
            self.roots.append(root)
            for position, row in enumerate(binned):
                predictions[position] += self._value(root, row)
        return self

    def _subsample(self, count: int, generator: random.Random) -> list[int]:
        size = max(1, int(count * self.subsample))
        if size >= count:
            return list(range(count))
        return sorted(generator.sample(range(count), size))

    def _grow(self, binned: Sequence[Sequence[int]], residuals: Sequence[float],
              index: Sequence[int], depth: int) -> int:
        node = len(self.nodes)
        self.nodes.append([-1.0, 0.0, 0.0, 0.0, 0.0])
        total = sum(residuals[i] for i in index)
        if depth <= 0 or len(index) < 2 * self.min_leaf:
            self.nodes[node][4] = self.learning_rate * total / (len(index) + self.l2)
            return node
        best = None
        for feature in range(self.width):
            counts = [0] * (len(self.cuts[feature]) + 1)
            sums = [0.0] * (len(self.cuts[feature]) + 1)
            for i in index:
                position = binned[i][feature]
                counts[position] += 1
                sums[position] += residuals[i]
            left_count, left_sum = 0, 0.0
            for cut in range(len(counts) - 1):
                left_count += counts[cut]
                left_sum += sums[cut]
                right_count = len(index) - left_count
                if left_count < self.min_leaf or right_count < self.min_leaf:
                    continue
                right_sum = total - left_sum
                gain = (left_sum * left_sum / (left_count + self.l2)
                        + right_sum * right_sum / (right_count + self.l2))
                if best is None or gain > best[0]:
                    best = (gain, feature, cut)
        if best is None:
            self.nodes[node][4] = self.learning_rate * total / (len(index) + self.l2)
            return node
        _, feature, cut = best
        left = [i for i in index if binned[i][feature] <= cut]
        right = [i for i in index if binned[i][feature] > cut]
        self.nodes[node][0] = float(feature)
        self.nodes[node][1] = float(cut)
        self.nodes[node][2] = float(self._grow(binned, residuals, left, depth - 1))
        self.nodes[node][3] = float(self._grow(binned, residuals, right, depth - 1))
        return node

    def _value(self, node: int, row: Sequence[int]) -> float:
        """The leaf a binned row reaches: the left child holds ``bin <= cut``."""
        while True:
            entry = self.nodes[node]
            if entry[0] < 0.0:
                return entry[4]
            node = int(entry[3]) if row[int(entry[0])] > entry[1] else int(entry[2])

    def predict(self, features: Sequence[float]) -> float:
        if not self.roots:
            raise BaselineError("NOT_FITTED", self.name)
        row = tuple(bisect_right(self.cuts[j], features[j]) for j in range(self.width))
        return self.base + sum(self._value(root, row) for root in self.roots)

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "formula": self.formula,
                "hyperparameters": dict(self.hyperparameters)}


def default_challengers() -> tuple[Ridge, BoostedTrees]:
    """One fresh instance of each challenger, in a fixed order."""
    return (Ridge(), BoostedTrees())


def default_challenger_factories() -> tuple[Callable[[], object], ...]:
    """Factories that build one fresh instance of each challenger, in the same order."""
    return (Ridge, BoostedTrees)


# --- the blocked walk-forward ---------------------------------------------


def window_end_of(origin: date) -> datetime:
    """The exclusive end of the billing day that begins at ``origin``."""
    return datetime(origin.year, origin.month, origin.day) + HOUR * 24


def train_deadline(first_origin: date, embargo_hours: int = 24) -> datetime:
    """The last settled window end a model fitted for ``first_origin`` may have seen.

    A training window has to have ended, and its settled value has to have had the
    embargo to arrive, before the fold's own history cutoff: the deadline is
    ``history_cutoff(first_origin) - embargo``.
    """
    return history_cutoff(first_origin, embargo_hours) - timedelta(hours=embargo_hours)


@dataclass(frozen=True)
class Fold:
    """One chronological block of scored origins: where it starts, and how far it runs."""

    index: int
    first: date
    last: date

    def to_dict(self) -> dict:
        return {"fold": self.index, "first_origin": self.first.isoformat(),
                "last_origin": self.last.isoformat()}


def fold_definitions(scored_origins: Sequence[date], folds: int = 6) -> tuple[Fold, ...]:
    """Chronological folds of equal origin count over the scored day origins.

    Cutting the *scored* origins keeps the folds comparable across the three
    horizons: every horizon's walk uses the same fold edges, so a fold means the
    same stretch of calendar whichever window is being forecast.
    """
    ordered = sorted(set(scored_origins))
    if folds < 1:
        raise BaselineError("BAD_FOLD_COUNT", str(folds))
    if len(ordered) < folds:
        raise BaselineError("NOT_ENOUGH_ORIGINS", f"{len(ordered)} origins for {folds} folds")
    size = math.ceil(len(ordered) / folds)
    definitions = []
    for index in range(folds):
        block = ordered[index * size:(index + 1) * size]
        if not block:
            break
        definitions.append(Fold(index=index, first=block[0], last=block[-1]))
    return tuple(definitions)


def fold_index_of(folds: Sequence[Fold], origin: date) -> int:
    """The fold a date falls in; an origin before the first fold answers fold 0.

    The clamp keeps the answer in range for classification only. :func:`walk`
    withholds such an origin instead of serving it with fold 0's models: those
    models were fitted on settled days that lie after it, so a forecast there
    would not be out of sample.
    """
    starts = [fold.first for fold in folds]
    position = bisect_right(starts, origin) - 1
    return max(0, min(position, len(folds) - 1))


def build_training_pool(index: HistoryIndex, series: Series, marks: Marks,
                        embargo_hours: int = 24,
                        extra: Callable[[datetime], tuple[float, ...] | None] | None = None,
                        ) -> tuple[TrainingRow, ...]:
    """One row per hour of every settled market billing day, in chronological order.

    A day qualifies when its 24 hours are all present and carry every interval,
    its window is a market window, and every feature of the hour is computable
    as of that day's own cutoff. A day that fails any of these contributes
    nothing — no hour of it is used, filled or carried over.
    """
    rows: list[TrainingRow] = []
    for origin in candidate_origins("day", series.first_day, series.last_day):
        window = window_for("day", origin)
        if not series.is_complete(window.hours):
            continue
        if slice_of(series, window, marks) != MARKET:
            continue
        try:
            context = OriginContext(index, origin, embargo_hours, extra)
        except BaselineError:
            continue
        for hour in window.hours:
            features = context.features(hour)
            if features is None:
                continue
            rows.append((origin, features, series.rows[hour].mean))
    return tuple(rows)


@dataclass(frozen=True)
class FittedFold:
    """The models of one fold, and exactly which rows they were fitted on."""

    index: int
    first: date
    deadline: datetime
    names: tuple[str, ...]
    train_rows: int
    train_origins: int
    train_first: date | None
    train_last: date | None
    models: Mapping[str, object] | None
    reason: str

    def to_dict(self) -> dict:
        return {
            "fold": self.index,
            "first_origin": self.first.isoformat(),
            "train_deadline": self.deadline.isoformat(),
            "models": list(self.names),
            "train_rows": self.train_rows,
            "train_origins": self.train_origins,
            "train_first_origin": None if self.train_first is None else self.train_first.isoformat(),
            "train_last_origin": None if self.train_last is None else self.train_last.isoformat(),
            "fitted": self.models is not None,
            "reason": self.reason,
        }


def fit_folds(index: HistoryIndex, series: Series, folds: Sequence[Fold],
              factories: Sequence[Callable[[], object]], *, pool: Sequence[TrainingRow] | None = None,
              embargo_hours: int = 24,
              min_train_rows: int = 500) -> tuple[FittedFold, ...]:
    """Fit one model set per fold, on the settled days that precede it.

    A fold with fewer than ``min_train_rows`` training rows fits nothing and says
    so: it serves no origin, and the comparison refuses a claim in its groups
    rather than scoring a model fitted on nothing.
    """
    if pool is None:
        pool = build_training_pool(index, series, derive_marks(series), embargo_hours)
    names = tuple(factory().name for factory in factories)
    fitted = []
    for fold in folds:
        deadline = train_deadline(fold.first, embargo_hours)
        usable = [row for row in pool if window_end_of(row[0]) <= deadline]
        train_origins = sorted({row[0] for row in usable})
        models = None
        reason = ""
        if len(usable) < min_train_rows:
            reason = "NO_TRAINING_DATA"
        else:
            built = [factory() for factory in factories]
            models = {model.name: model.fit(usable) for model in built}
        fitted.append(FittedFold(
            index=fold.index, first=fold.first, deadline=deadline, names=names,
            train_rows=len(usable), train_origins=len(train_origins),
            train_first=train_origins[0] if train_origins else None,
            train_last=train_origins[-1] if train_origins else None,
            models=models, reason=reason,
        ))
    return tuple(fitted)


@dataclass(frozen=True)
class CandidateResult:
    """One candidate origin of one walk: what was scored, and by which fold's models."""

    origin: date
    slice: str
    fold: int
    realized: float
    served: bool
    reason: str
    points: Mapping[str, float]
    quantiles: Mapping[str, tuple[float, float, float]]


@dataclass(frozen=True)
class WalkResult:
    """One (series, horizon) walk: every candidate origin, in chronological order."""

    series_key: str
    horizon: str
    folds: tuple[FittedFold, ...]
    candidates: tuple[CandidateResult, ...]

    def served_by(self, name: str) -> int:
        return sum(1 for entry in self.candidates if entry.served and name in entry.points)


def walk(index: HistoryIndex, series: Series, horizon: str, fitted: Sequence[FittedFold],
         folds: Sequence[Fold], *, embargo_hours: int = 24,
         min_fan_samples: int = 12,
         extra: Callable[[datetime], tuple[float, ...] | None] | None = None) -> WalkResult:
    """Forecast every candidate origin of one horizon with the fold's own models.

    The walk visits the candidates in chronological order and runs the same as-of
    fan the baselines use: a settled window's signed residual joins the fan only
    once its window ended at least one embargo before the origin being forecast,
    and a fan that is not yet wide enough withholds that origin's quantiles.

    A forecast also needs a model that was as-of for *its* origin: the fold that
    would serve the origin must have finished training — deadline, embargo
    included — by the origin's own training deadline (:func:`train_deadline`).
    Candidates before the first fold fail that test: they are inside fold 0 only
    by the clamp of :func:`fold_index_of`, and fold 0's models were fitted on
    settled days that lie ahead of them, so they are recorded unserved as
    ``BEFORE_FIRST_FOLD`` and contribute no residual to any fan. Nothing is
    warmed up with a model fitted after the origin it forecasts.
    """
    marks = derive_marks(series)
    names = tuple(fitted[0].names) if fitted else ()
    fans = {name: ErrorFan(embargo_hours) for name in names}
    results: list[CandidateResult] = []
    for origin in candidate_origins(horizon, series.first_day, series.last_day):
        window = window_for(horizon, origin)
        if not series.is_complete(window.hours):
            continue
        slice_name = slice_of(series, window, marks)
        if slice_name == MIXED:
            continue
        realized = series.window_mean(window.hours)
        fold = fitted[fold_index_of(folds, origin)]
        points: dict[str, float] = {}
        reason = ""
        if fold.models is None:
            reason = fold.reason
        elif fold.deadline > train_deadline(origin, embargo_hours):
            # The fold's training had not finished by this origin's own training
            # deadline: the models saw settled days from after the origin, so a
            # forecast here would not be out of sample. Withheld — no forecast,
            # no residual, no warm-up with a model fitted after the origin.
            reason = "BEFORE_FIRST_FOLD"
        else:
            try:
                context = OriginContext(index, origin, embargo_hours, extra)
            except BaselineError as error:
                reason = error.code
            else:
                vectors = []
                for hour in window.hours:
                    features = context.features(hour)
                    if features is None:
                        reason = "FEATURE_UNAVAILABLE"
                        break
                    vectors.append(features)
                if not reason:
                    weights = (INTERVALS_PER_HOUR,) * len(vectors)
                    for name, model in fold.models.items():
                        points[name] = aggregate([model.predict(vector) for vector in vectors],
                                                 weights)
        for fan in fans.values():
            fan.release(window.start)
        if not reason:
            for name, point in points.items():
                fans[name].add(window.end, realized - point)
        quantiles = {}
        for name, point in points.items():
            if len(fans[name]) >= min_fan_samples:
                quantiles[name] = ordered_quantiles(point, *fans[name].arms())
        results.append(CandidateResult(
            origin=origin, slice=slice_name, fold=fold.index, realized=realized,
            served=not reason, reason=reason, points=points, quantiles=quantiles,
        ))
    return WalkResult(series_key=series.key, horizon=horizon, folds=tuple(fitted),
                      candidates=tuple(results))


# --- the gate --------------------------------------------------------------


def calibration_of(rows: Sequence[tuple[float, float, float, float, float]]) -> dict:
    """Interval coverage and quantile shares of one group's reported triples."""
    if not rows:
        return {"count": 0, "coverage": None, "below_p10": None,
                "below_p50": None, "below_p90": None}
    count = len(rows)
    covered = sum(1 for realized, _, low, _, high in rows if low <= realized <= high)
    return {
        "count": count,
        "coverage": covered / count,
        "below_p10": sum(1 for realized, _, low, _, _ in rows if realized < low) / count,
        "below_p50": sum(1 for realized, _, _, middle, _ in rows if realized < middle) / count,
        "below_p90": sum(1 for realized, _, _, _, high in rows if realized < high) / count,
    }


def week_of(origin: date) -> tuple[int, int]:
    """The ISO week of an origin: the block a resample draws as one unit."""
    iso = origin.isocalendar()
    return iso[0], iso[1]


def week_block_bootstrap(blocks: Mapping[tuple[int, int], tuple[int, float, float]],
                         *, resamples: int = BOOTSTRAP_RESAMPLES,
                         seed: int = BOOTSTRAP_SEED,
                         level: float = BOOTSTRAP_LEVEL) -> dict:
    """The interval of the MAE gain over a resample of whole origin weeks.

    ``blocks`` maps one ISO week to ``(origins, baseline absolute error sum,
    challenger absolute error sum)``. Each draw resamples the weeks with
    replacement and pools their sums, so windows that overlap inside a week move
    together; the returned interval is the ``level`` two-sided interval of
    ``baseline MAE - challenger MAE``, positive when the challenger wins.
    """
    keys = sorted(blocks)
    if not keys:
        return {"resamples": 0, "seed": seed, "level": level, "low": None, "high": None}
    generator = random.Random(seed)
    gains = []
    for _ in range(resamples):
        count = 0
        baseline_total = 0.0
        challenger_total = 0.0
        for _ in range(len(keys)):
            key = keys[generator.randrange(len(keys))]
            size, baseline_sum, challenger_sum = blocks[key]
            count += size
            baseline_total += baseline_sum
            challenger_total += challenger_sum
        gains.append((baseline_total - challenger_total) / count)
    gains.sort()
    return {
        "resamples": resamples,
        "seed": seed,
        "level": level,
        "low": quantile(gains, (1.0 - level) / 2.0),
        "high": quantile(gains, 1.0 - (1.0 - level) / 2.0),
    }


@dataclass(frozen=True)
class GroupRow:
    """One scored origin of one group: what it realized, and what each side said."""

    origin: date
    fold: int
    realized: float
    baseline: Mapping[str, float]
    point: float
    quantiles: tuple[float, float, float] | None


def point_metrics(pairs: Sequence[tuple[float, float]]) -> Metrics:
    """Bias, MAE and RMSE of ``(realized, point)`` rows; the point side of a group."""
    return metrics_from([(realized, point, point, point, point) for realized, point in pairs])


def assess_claim(rows: Sequence[GroupRow], *, slice_name: str, scored_in_record: int,
                 name: str, min_common_share: float = MIN_COMMON_SHARE) -> dict:
    """Decide whether one challenger may claim skill on one group, and say why.

    The gate is the acceptance in machine-readable form. Both sides are scored on
    the origins the challenger serves — the record's own per-origin points give
    the baselines the same denominator — and the basis is the best of the three
    PRICE-2 baselines by MAE on those origins. A claim needs a lower MAE and RMSE
    than that basis, a week-block bootstrap interval of the MAE gain that excludes
    zero, a positive gain in at least two thirds of the folds, and a calibrated
    interval; and it needs the comparison to keep at least ``min_common_share``
    of the origins the record scored, so a model cannot claim skill on the
    handful of origins it happens to serve. Fold calibration stability is judged
    over every fold of the group, not only the measurable ones: a fold holding
    fewer than :data:`FOLD_COVERAGE_MIN_ORIGINS` judged origins fails the floor
    rather than shrinking the denominator, so a group whose folds cannot be
    measured at all is refused instead of accepted on no evidence at all. Every
    refusal carries its reason.

    Baseline *pinball* is not recomputed here: the PRICE-2 record carries the
    baselines' arms and they are quoted from it as they stand.
    """
    report: dict = {
        "challenger": name,
        "scored_in_record": scored_in_record,
        "served": len(rows),
        "common_share": (len(rows) / scored_in_record) if scored_in_record else None,
    }
    group = [(row.realized, row.point) + (row.quantiles or (row.point, row.point, row.point))
             for row in rows]
    report["metrics"] = metrics_from(group).to_dict()
    report["calibration"] = calibration_of(group)
    names = sorted({name for row in rows for name in row.baseline})
    report["baselines"] = {
        entry: point_metrics([(row.realized, row.baseline[entry]) for row in rows]).to_dict()
        for entry in names
    }
    if not rows or not names:
        report["claim"] = False
        report["verdict"] = "no claim: no origins served"
        return report
    best_name = min(names, key=lambda key: report["baselines"][key]["mae"])
    best = report["baselines"][best_name]
    report["basis"] = best_name
    report["gain_mae"] = best["mae"] - report["metrics"]["mae"]
    report["gain_rmse"] = best["rmse"] - report["metrics"]["rmse"]

    blocks: dict[tuple[int, int], tuple[int, float, float]] = {}
    for row in rows:
        entry = blocks.setdefault(week_of(row.origin), (0, 0.0, 0.0))
        baseline_error = abs(row.baseline[best_name] - row.realized)
        blocks[week_of(row.origin)] = (entry[0] + 1, entry[1] + baseline_error,
                                       entry[2] + abs(row.point - row.realized))
    bootstrap = week_block_bootstrap(blocks)
    report["bootstrap"] = bootstrap

    fold_rows: dict[int, list[GroupRow]] = {}
    for row in rows:
        fold_rows.setdefault(row.fold, []).append(row)
    fold_gains = []
    fold_coverage = []
    for index in sorted(fold_rows):
        entries = fold_rows[index]
        gain = sum(abs(row.baseline[best_name] - row.realized) - abs(row.point - row.realized)
                   for row in entries) / len(entries)
        fold_gains.append({"fold": index, "count": len(entries), "gain_mae": gain})
        calibrated = [entry for entry in entries if entry.quantiles]
        if len(calibrated) >= FOLD_COVERAGE_MIN_ORIGINS:
            share = sum(1 for entry in calibrated
                        if entry.quantiles[0] <= entry.realized <= entry.quantiles[2])
            fold_coverage.append({"fold": index, "count": len(calibrated),
                                  "coverage": share / len(calibrated)})
    report["folds"] = fold_gains
    report["fold_coverage"] = fold_coverage

    reasons = []
    if slice_name != MARKET:
        reasons.append("administered_pricing_slice")
    if report["common_share"] is None or report["common_share"] < min_common_share:
        reasons.append("denominators_differ")
    if report["gain_mae"] <= 0.0:
        reasons.append("baseline_wins")
    if report["gain_rmse"] <= 0.0:
        reasons.append("gain_not_out_of_sample")
    if bootstrap["low"] is None or bootstrap["low"] <= 0.0:
        reasons.append("gain_not_significant")
    needed = math.ceil(FOLD_GAIN_SHARE * len(fold_gains))
    positive = sum(1 for entry in fold_gains if entry["gain_mae"] > 0.0)
    report["folds_positive"] = positive
    report["folds_needed"] = needed
    if positive < needed:
        reasons.append("gain_not_stable")
    coverage = report["calibration"]["coverage"]
    if coverage is None or not COVERAGE_FLOOR <= coverage <= COVERAGE_CEILING:
        reasons.append("interval_miscalibrated")
    # A fold counts towards stability only while it holds enough judged origins to
    # measure, and the two thirds are of every fold of the group: a fold without
    # calibration evidence is not evidence, so a group with no measurable fold —
    # or with too few of them — carries no claim.
    stable = sum(1 for entry in fold_coverage if entry["coverage"] >= FOLD_COVERAGE_FLOOR)
    report["fold_coverage_assessed"] = len(fold_coverage)
    report["fold_coverage_folds"] = len(fold_gains)
    report["fold_coverage_stable"] = stable
    report["fold_coverage_needed"] = math.ceil(FOLD_GAIN_SHARE * len(fold_gains))
    if stable < report["fold_coverage_needed"]:
        reasons.append("calibration_not_stable")
    report["reasons"] = reasons
    report["claim"] = not reasons
    report["verdict"] = (f"claim: {name} beats {best_name} out of sample with stable calibration"
                         if not reasons else "no claim: " + ", ".join(reasons))
    return report


__all__ = [
    "BOOTSTRAP_LEVEL",
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "BoostedTrees",
    "COVERAGE_CEILING",
    "COVERAGE_FLOOR",
    "CandidateResult",
    "FEATURES",
    "FOLD_COVERAGE_FLOOR",
    "FOLD_GAIN_SHARE",
    "FittedFold",
    "Fold",
    "GroupRow",
    "HistoryIndex",
    "KIND",
    "MARKET",
    "MIN_COMMON_SHARE",
    "OriginContext",
    "Ridge",
    "VERSION",
    "WalkResult",
    "assess_claim",
    "build_training_pool",
    "calibration_of",
    "default_challenger_factories",
    "default_challengers",
    "fit_folds",
    "fold_definitions",
    "fold_index_of",
    "point_metrics",
    "train_deadline",
    "walk",
    "week_block_bootstrap",
    "week_of",
    "weekly_sample",
    "window_end_of",
]
