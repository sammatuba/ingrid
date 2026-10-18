"""Likely drivers for one replay alert, computed in the app from the replay data (owner decision of
2026-10-18: "fully dynamic, computed inside the app when an alert is opened").

The method follows the warehouse ranking used on the event page, on the subset of inputs the replay
holds:

* the baseline is the same region, the same Manila hour of day, over the 28 days before t; t itself is
  excluded (every five-minute interval of that hour, as in the warehouse ranking);
* an indicator's score is its percentile against that baseline, (count below + 0.5 x ties) / n;
* with fewer than MIN_DAYS earlier days in the baseline, the indicator says "Not enough history"
  instead of a score; a value missing at t says "No data"; nothing is guessed;
* a family's score is its strongest indicator; families rank by score, highest first, ties by family
  name, and fuel ranks after every other scored family whenever any of them scores 0.8 or more;
* the price is context only, never a driver.

Indicators the replay holds (higher pushes prices up in every case):
  D  demand_mw              the region's demand
  S  reserve_shortfall_mw   the reserve shortfall
  S  import_share           imports over demand
  S  hvdc_links_congested   the region's HVDC links flagged congested
  O  trip_notices_6h        the operator's trip notices for the region in the 6 hours to the interval end
Not in the replay: congestion on transmission elements and price-rule flags (Rules), fuel series (F).
Those families say so; the event page, built from the full warehouse, has them.

No BigQuery, no model, no file other than the replay. Pure functions on `Replay.data()`.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

BASELINE_DAYS = 28
MIN_DAYS = 7
FUEL_LAST_AT = 0.8
FAMILIES = ('D', 'S', 'O', 'Rules', 'F')
NOT_IN_REPLAY = ('Rules', 'F')
NOTICE_HOURS = 6
# The HVDC links by their two ends: MIN-VIS joins Mindanao and the Visayas, VIS-LUZ the Visayas and Luzon.
# A link whose name is not here is not counted for any region (never guessed).
REGION_LINKS = {'CLUZ': ('VISLUZ1',), 'CVIS': ('MINVIS1', 'VISLUZ1'), 'CMIN': ('MINVIS1',)}
STATUS_SCORED, STATUS_HISTORY, STATUS_NO_DATA, STATUS_NOT_HELD = 'scored', 'not enough history', 'no data', 'not in replay'


def _num(v):
    return float(v) if type(v) in (int, float) and v == v else None


def percentile(value, baseline):
    """(count below + 0.5 x ties) / n, rounded to 4 places; None with no value or no baseline."""
    vals = [v for v in baseline if v is not None]
    if value is None or not vals:
        return None
    below = sum(1 for v in vals if v < value)
    ties = sum(1 for v in vals if v == value)
    return round((below + 0.5 * ties) / len(vals), 4)


def baseline_slots(times, t, days=BASELINE_DAYS):
    """Indexes of the baseline: the same Manila hour as t, from t - days up to t, t excluded."""
    start = (datetime.strptime(t, '%Y-%m-%dT%H:%M') - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M')
    hour = t[11:13]
    return [i for i, s in enumerate(times) if start <= s < t and s[11:13] == hour]


def rank_families(scores):
    """{family: score or None} -> {family: rank or None}: highest first, ties by name; fuel after every
    other scored family when any of them scores FUEL_LAST_AT or more; no score, no rank."""
    other = [s for f, s in scores.items() if f != 'F' and s is not None]
    fuel_last = bool(other) and max(other) >= FUEL_LAST_AT
    order = sorted((f for f, s in scores.items() if s is not None),
                   key=lambda f: (f == 'F' and fuel_last, -scores[f], f))
    return {f: (order.index(f) + 1 if f in order else None) for f in scores}


def _series(d, region):
    """The region's indicator series over the whole replay, built once per replay data object (the data is
    replaced, never changed, when the bake changes) and kept in it under a private key; a shallow copy."""
    cache = d.setdefault('_drivers_series', {})
    if region not in cache:
        cache[region] = _build_series(d, region)
    return dict(cache[region])


def _build_series(d, region):
    g = d['regions'][region]
    times = d['t']
    demand = g.get('demand_mw') or [None] * len(times)
    imports = g.get('import_mw') or [None] * len(times)
    share = []
    for dem, imp in zip(demand, imports):
        dem, imp = _num(dem), _num(imp)
        share.append(round(imp / dem, 4) if dem and dem > 0 and imp is not None else None)
    links = [n for n in REGION_LINKS.get(region, ()) if n in (d.get('hvdc') or {})]
    if links:
        flags = [d['hvdc'][n] for n in links]
        hvdc = [None if any(f[i] is None for f in flags) else float(sum(f[i] for f in flags)) for i in range(len(times))]
    else:
        hvdc = [None] * len(times)
    return {
        ('D', 'demand_mw', 'MW'): [_num(v) for v in demand],
        ('S', 'reserve_shortfall_mw', 'MW'): [_num(v) for v in g.get('dr_short_mw') or [None] * len(times)],
        ('S', 'import_share', 'fraction'): share,
        ('S', 'hvdc_links_congested', 'links'): hvdc,
    }


def _notice_counts(d, region, idx):
    """The region's trip notices in the NOTICE_HOURS before each interval's end, for the given indexes.
    The notices span the replay; a slot before the first replay day has no count (no data)."""
    times = d['t']
    trips = sorted(a['t'] for a in d.get('advisories') or [] if a['grid'] == region and a['kind'] == 'trip')
    first = times[0] if times else None
    out = {}
    for i in idx:
        t = times[i]
        end = (datetime.strptime(t, '%Y-%m-%dT%H:%M') + timedelta(minutes=5))
        start = end - timedelta(hours=NOTICE_HOURS)
        if first is None or start.strftime('%Y-%m-%dT%H:%M') < first:
            out[i] = None  # the window reaches before the replay: not counted
            continue
        lo, hi = start.strftime('%Y-%m-%dT%H:%M'), end.strftime('%Y-%m-%dT%H:%M')
        out[i] = float(sum(1 for x in trips if lo <= x < hi))
    return out


def likely_drivers(d, region, t):
    """Rows shaped like the warehouse ranking for one region and interval start t (Manila):
    {'rows': [...], 'context': {...}, 'baseline_days': n, 'missing': [...]} or None if t is not in the replay."""
    if not d or region not in (d.get('regions') or {}) or t not in d['t']:
        return None
    times = d['t']
    i_t = times.index(t)
    base = baseline_slots(times, t)
    series = _series(d, region)
    counts = _notice_counts(d, region, base + [i_t])
    series[('O', 'trip_notices_6h', 'notices')] = [counts.get(i) for i in range(len(times))]
    indicators = []
    for (fam, name, unit), values in series.items():
        b = [(i, values[i]) for i in base if values[i] is not None]
        days = len({times[i][:10] for i, _ in b if times[i][:10] < t[:10]})
        value = values[i_t]
        row = {'family': fam, 'indicator': name, 'unit': unit, 'value_at_t': value, 'baseline_n': len(b),
               'baseline_days': days, 'baseline_median': statistics.median([v for _, v in b]) if b else None,
               'indicator_score': None}
        if value is None:
            row['status'] = STATUS_NO_DATA
        elif days < MIN_DAYS:
            row['status'] = STATUS_HISTORY
        else:
            row['status'] = STATUS_SCORED
            row['indicator_score'] = percentile(value, [v for _, v in b])
        indicators.append(row)
    scores = {}
    for fam in FAMILIES:
        got = [r['indicator_score'] for r in indicators if r['family'] == fam and r['status'] == STATUS_SCORED]
        scores[fam] = max(got) if got else None
    ranks = rank_families(scores)
    rows = []
    for r in indicators:
        rows.append(dict(r, rank=ranks[r['family']], family_score=scores[r['family']]))
    for fam in NOT_IN_REPLAY:
        rows.append({'family': fam, 'indicator': None, 'unit': '', 'value_at_t': None, 'baseline_n': 0,
                     'baseline_days': 0, 'baseline_median': None, 'indicator_score': None,
                     'status': STATUS_NOT_HELD, 'rank': None, 'family_score': None})
    price = [_num(v) for v in d['regions'][region]['price']]
    pb = [price[i] for i in base if price[i] is not None]
    context = {'family': 'P', 'indicator': 'price_capped_median', 'unit': 'PHP/MWh', 'value_at_t': price[i_t],
               'baseline_n': len(pb), 'baseline_median': statistics.median(pb) if pb else None,
               'indicator_score': percentile(price[i_t], pb), 'status': 'context'}
    days = len({times[i][:10] for i in base if times[i][:10] < t[:10]})
    return {'rows': rows, 'context': context, 'baseline_days': days,
            'from': times[base[0]] if base else None, 'missing': list(NOT_IN_REPLAY)}
