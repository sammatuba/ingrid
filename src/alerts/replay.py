"""Alerts on the baked replay (ericka-desk E21, E22, E24): the saved levels run over `regions.json`.

The live checks (service.py) need BigQuery; the replay of 21 to 29 Sep 2026 that every page shows is
baked to `build/grid-data/`. This module reads that bake (read-only) and finds, for each region, the
runs of five-minute intervals whose price crosses the region's spike or collapse level, each run one
alert, up to the "as of" clock and never past it.

Rules carried here:
* usual is the same-hour median of the region's price over the EARLIER replay days only, never the
  interval's own day or a later one; the first day has no usual, so a multiple-of-usual level cannot
  fire there and the alert says "no usual price yet";
* an alert's cause is a recorded event (`events.json` and `events/<id>.json`) in the same region whose
  window, from the event to its last timeline entry, overlaps the alert and whose first notice was
  known by the clock. Nothing else is called a cause: with no such event the alert says none is on
  record (owner rule: no uncertain match), and its link is its own page (`/alert/<key>`, src/grid/spike.*),
  built from this bake on request with the notices around it shown as not claimed as the cause;
* every alert also carries `notices_around` (src/alerts/notices.py): the region's outage, trip and
  grid notices from six hours before it to its last interval, posted by the clock, each with how sure
  its plant match is; none is a cause, and `cause` stays a recorded event or None;
* severity is a stated rule on the recorded price, not a forecast; no peso figure is made here.
"""
import bisect
import json
import re
from pathlib import Path
from threading import Lock

from . import model
from . import notices as notices_mod

EVENT_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
AT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z')
GAP_MINUTES = 15  # crossings at most 15 minutes apart (two quiet intervals) are one alert
EVENT_TAIL_MINUTES = 180  # an event with no later timeline entry covers three hours
MAX_ALERTS = 300
WINDOW_MINUTES = 120  # an alert's own page shows two hours either side of it, never past the clock


def _minutes(t):
    """Minutes since 2000-01-01 for 'YYYY-MM-DDTHH:MM' (enough to compare gaps)."""
    y, mo, d, h, mi = int(t[0:4]), int(t[5:7]), int(t[8:10]), int(t[11:13]), int(t[14:16])
    from datetime import datetime
    return int((datetime(y, mo, d, h, mi) - datetime(2000, 1, 1)).total_seconds() // 60)


def _plus(t, minutes):
    from datetime import datetime, timedelta
    return (datetime.fromisoformat(t) + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


def usual_table(times, prices):
    """{index: (usual, days)}: the same-hour median of the prices on earlier days, per interval.

    Built day by day: an interval's usual is taken before its own day is added, so neither its own
    day nor any later day can reach it. The earlier prices are kept sorted per hour (replay-year: a
    year of days), so each day's median is read off the middle instead of re-sorting the year; the
    value is statistics.median's (the middle one, or the mean of the middle two).
    """
    by_day = {}
    for i, t in enumerate(times):
        by_day.setdefault(t[:10], []).append(i)
    earlier = {}  # hour -> the sorted prices of the days already passed
    days_seen = {}  # hour -> number of earlier days with a price in that hour
    out = {}
    for day in sorted(by_day):
        medians = {}
        for i in by_day[day]:
            hour = times[i][11:13]
            if hour not in medians:
                values = earlier.get(hour)
                if values:
                    n = len(values)
                    medians[hour] = (values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2, days_seen[hour])
                else:
                    medians[hour] = (None, 0)
            out[i] = medians[hour]
        for hour in {times[i][11:13] for i in by_day[day]}:
            vals = [prices[i] for i in by_day[day] if times[i][11:13] == hour and prices[i] is not None]
            if vals:
                row = earlier.setdefault(hour, [])
                for v in vals:
                    bisect.insort(row, v)
                days_seen[hour] = days_seen.get(hour, 0) + 1
    return out


class Replay:
    """The baked replay under `directory`; reloaded when `regions.json`, `events.json`,
    `advisories.json`, `hvdc.json` or `sites.json` changes."""

    def __init__(self, directory):
        # A path, or a function giving one (resolved at the first read).
        self._where = directory
        self._lock = Lock()
        self._key, self._data = None, None
        # replay-year: the episodes of the whole bake per region and levels, kept with the data they
        # were found in; a call at an earlier clock cuts them (grouping only looks back).
        self._episodes = {}

    @property
    def directory(self):
        if callable(self._where):
            self._where = self._where()
        return Path(self._where)

    def _stamp(self):
        out = []
        for name in ('regions.json', 'events.json', 'advisories.json', 'hvdc.json', 'sites.json'):
            try:
                st = (self.directory / name).stat()
                out.append((name, st.st_mtime_ns, st.st_size))
            except OSError:
                out.append((name, None, None))
        return tuple(out)

    def data(self):
        """{'t', 'regions': {code: {price, usual, facts...}}, 'events': [...]}, or None with no bake."""
        stamp = self._stamp()
        with self._lock:
            if stamp != self._key:
                self._key, self._data = stamp, self._read()
                self._episodes = {}
            return self._data

    def _json(self, name):
        try:
            return json.loads((self.directory / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None

    def _read(self):
        regions = self._json('regions.json')
        if not isinstance(regions, dict) or not isinstance(regions.get('t'), list):
            return None
        times = [str(t)[:16] for t in regions['t']]
        out = {'t': times, 'regions': {}, 'events': self._events(), 'advisories': self._advisories(),
               'hvdc': self._hvdc(times)}
        out['advisory_t'] = [a['t'] for a in out['advisories']]
        # The notices around each alert (src/alerts/notices.py), matched to plants once per bake.
        index = self._json('events.json')
        out['notice_index'] = notices_mod.NoticeIndex(out['advisories'], self._json('sites.json'),
                                                      index if isinstance(index, list) else [])
        for code in model.REGIONS:
            g = (regions.get('grids') or {}).get(code) or {}
            prices = list(g.get('lmp_median') or [None] * len(times))
            if len(prices) != len(times):
                continue
            prices = [p if type(p) in (int, float) else None for p in prices]

            def series(name):
                s = g.get(name)
                return s if isinstance(s, list) and len(s) == len(times) else [None] * len(times)
            out['regions'][code] = {'price': prices, 'usual': usual_table(times, prices),
                                    'demand_mw': series('demand_mw'), 'dr_short_mw': series('dr_short_mw'),
                                    'curtailed_mw': series('curtailed_mw'), 'import_mw': series('import_mw')}
        return out

    def _hvdc(self, times):
        """{link name: [congested 0/1 or None per interval]} for the links whose times match the
        regions' times; {} with no file or another clock."""
        h = self._json('hvdc.json')
        if not isinstance(h, dict) or [str(t)[:16] for t in h.get('t') or []] != times:
            return {}
        out = {}
        for name, link in (h.get('links') or {}).items():
            flags = (link or {}).get('congested') if isinstance(link, dict) else None
            if isinstance(flags, list) and len(flags) == len(times):
                out[str(name)] = [v if v in (0, 1) and type(v) is not bool else None for v in flags]
        return out

    def _events(self):
        index = self._json('events.json')
        out = []
        for entry in index if isinstance(index, list) else []:
            eid = str((entry or {}).get('id') or '')
            if not EVENT_ID.fullmatch(eid):
                continue
            detail = self._json(f'events/{eid}.json') or {}
            grid = detail.get('grid')
            start = str(detail.get('event_at') or entry.get('t') or '')[:16]
            if grid not in model.REGIONS or not AT.fullmatch(start):
                continue
            times = [str(x.get('t'))[:16] for x in detail.get('timeline') or [] if isinstance(x, dict) and x.get('t')]
            end = max([start] + [t for t in times if AT.fullmatch(t)])
            if end == start:
                end = _plus(start, EVENT_TAIL_MINUTES)
            advisory = detail.get('advisory') or {}
            known = str(advisory.get('t') or entry.get('t') or start)[:16]
            out.append({'id': eid, 'region': grid, 'start': start, 'end': end, 'known_at': known,
                        'title': str(detail.get('title') or entry.get('title') or eid),
                        'advisory': str(advisory.get('id') or entry.get('advisory') or ''),
                        'advisory_text': str(advisory.get('text') or '')})
        return out

    def _advisories(self):
        """The operator notices as baked: [{t (minute), id, grid, kind, text}], oldest first."""
        rows = self._json('advisories.json')
        out = []
        for a in rows if isinstance(rows, list) else []:
            if not isinstance(a, dict):
                continue
            t = str(a.get('t') or '')[:16]
            if not AT.fullmatch(t) or a.get('grid') not in model.REGIONS:
                continue
            out.append({'t': t, 'id': str(a.get('id') or ''), 'grid': a['grid'],
                        'kind': str(a.get('kind') or 'notice'), 'text': str(a.get('text') or '')})
        out.sort(key=lambda a: a['t'])
        return out

    def around(self, rules, alert, at=None):
        """An alert's surroundings for its own page: the region's five-minute series from
        WINDOW_MINUTES before its first interval to WINDOW_MINUTES after its last, and the region's
        operator notices in that window; nothing after `at` (the replay clock). Only what the bake
        holds: a value it does not carry is None, never estimated."""
        d = self.data()
        code, direction = alert['region'], alert['direction']
        series = (d or {}).get('regions', {}).get(code)
        times = d['t'] if d else []
        clock = at or (times[-1] if times else alert['last'])
        start = _plus(alert['first'], -WINDOW_MINUTES)
        end = min(_plus(alert['last'], WINDOW_MINUTES), clock)
        level = model.levels_for(rules, code).get(direction)
        out = {'from': start, 'to': end, 'clock': clock, 'minutes_either_side': WINDOW_MINUTES,
               'level_mode': level['mode'] if level else None,
               't': [], 'price': [], 'usual': [], 'level': [], 'reserve_short_mw': [], 'curtailed_mw': [],
               'demand_mw': [], 'notices': []}
        if series is None:
            return out

        def number(v):
            return v if type(v) in (int, float) else None
        for i in range(bisect.bisect_left(times, start), len(times)):
            t = times[i]
            if t > end:
                break
            usual, days = series['usual'].get(i, (None, 0))
            bound = None
            if level and level['mode'] == 'absolute':
                bound = level['value']
            elif level and days >= 1 and usual is not None and usual > 0:
                bound = level['value'] * usual
            out['t'].append(t)
            out['price'].append(series['price'][i])
            out['usual'].append(usual)
            out['level'].append(bound)
            out['reserve_short_mw'].append(number(series['dr_short_mw'][i]))
            out['curtailed_mw'].append(number(series['curtailed_mw'][i]))
            out['demand_mw'].append(number(series['demand_mw'][i]))
        notices = d['advisories']
        lo = bisect.bisect_left(d['advisory_t'], start)
        hi = bisect.bisect_right(d['advisory_t'], end)
        out['notices'] = [{'t': a['t'], 'id': a['id'], 'kind': a['kind'], 'text': a['text']}
                          for a in notices[lo:hi] if a['grid'] == code]
        return out

    def notices_around(self, alert, at=None):
        """The region's notices around one alert (src/alerts/notices.py), none claimed as its cause;
        nothing posted after `at`. None with no bake."""
        d = self.data()
        if not d or alert.get('region') not in d['regions']:
            return None
        clock = at or d['t'][-1]
        return d['notice_index'].around(alert, clock, d['regions'][alert['region']], d['t'])

    @property
    def span(self):
        d = self.data()
        return (d['t'][0], d['t'][-1]) if d and d['t'] else None

    def alerts(self, rules, at=None):
        """The replay's alerts up to `at` (inclusive), newest first; [] with no bake.

        `rules` is a stored rules version (or DEFAULT_RULES): its regions and its per-region levels.
        """
        d = self.data()
        if not d:
            return []
        times = d['t']
        at = at or times[-1]
        last = bisect.bisect_right(times, at) - 1  # the axis is in time order
        out = self._cut(d, rules, last)
        # Only the alerts shown are built: ordered on (last, key), which an episode carries already.
        out.sort(key=lambda e: (e['last'], e['key']), reverse=True)
        return [self._alert(e, rules, d, at) for e in out[:MAX_ALERTS]]

    def _all_episodes(self, d, rules, code):
        """Every episode of `code` over the whole bake, for its levels: cached per levels."""
        levels = model.levels_for(rules, code)
        cache_key = (code, json.dumps(levels, sort_keys=True, default=str), str(rules.get('version')))
        with self._lock:
            if self._data is d and cache_key in self._episodes:
                return self._episodes[cache_key]
        times, series = d['t'], d['regions'][code]
        prices, usual_of = series['price'], series['usual']
        found = []
        current = None
        for i, price in enumerate(prices):
            usual, days = usual_of.get(i, (None, 0))
            direction = model.crossing(levels, price, usual, days >= 1)
            if direction is None:
                continue
            t = times[i]
            if current and current['direction'] == direction and _minutes(t) - _minutes(current['last']) <= GAP_MINUTES:
                current['points'].append((i, t, price, usual))
                current['last'] = t
                continue
            current = {'region': code, 'direction': direction, 'first': t, 'last': t, 'points': [(i, t, price, usual)],
                       'key': model.alert_key(code, t, 'replay-' + direction)}
            found.append(current)
        starts = [e['points'][0][0] for e in found]
        with self._lock:
            if self._data is d:
                if len(self._episodes) > 64:
                    self._episodes.clear()
                self._episodes[cache_key] = (found, starts)
        return found, starts

    def _cut(self, d, rules, last):
        """The episodes up to interval `last`, as a scan stopping there finds them: the ones that
        start by then, the one running across it cut at it (grouping only ever looks back)."""
        out = []
        for code in sorted(rules.get('regions') or model.REGIONS):
            if d['regions'].get(code) is None:
                continue
            found, starts = self._all_episodes(d, rules, code)
            n = bisect.bisect_right(starts, last)
            for e in found[:n]:
                if e['points'][-1][0] <= last:
                    out.append(e)
                    continue
                points = [p for p in e['points'] if p[0] <= last]
                out.append(dict(e, points=points, last=points[-1][1]))
        return out

    def keys(self, rules):
        """Every replay alert key the rules raise over the whole bake (not only the newest shown)."""
        d = self.data()
        if not d:
            return set()
        return {e['key'] for e in self._cut(d, rules, len(d['t']) - 1)}

    def all_alerts(self, rules):
        """Every replay alert the rules raise over the whole bake (as at the last interval), oldest first;
        not capped at MAX_ALERTS like `alerts` (for offline batches over the year)."""
        d = self.data()
        if not d:
            return []
        out = self._cut(d, rules, len(d['t']) - 1)
        out.sort(key=lambda e: (e['first'], e['key']))
        return [self._alert(e, rules, d, d['t'][-1]) for e in out]

    def find(self, rules, key):
        """The replay alert `key` over the whole bake (as at its last interval), or None."""
        d = self.data()
        if not d:
            return None
        found = next((e for e in self._cut(d, rules, len(d['t']) - 1) if e['key'] == key), None)
        return self._alert(found, rules, d, d['t'][-1]) if found else None

    def _alert(self, episode, rules, d, at):
        code, direction, points = episode['region'], episode['direction'], episode['points']
        spike = direction == 'spike'
        peak = (max if spike else min)(points, key=lambda p: p[2])
        i, t, price, usual = peak
        level = model.levels_for(rules, code)[direction]
        series = d['regions'][code]
        severity, reason = severity_of(direction, price, usual, len(points))
        cause = next((e for e in d['events'] if e['region'] == code and e['known_at'] <= at
                      and e['start'] <= episode['last'] and episode['first'] <= e['end']), None)
        facts = []
        short = series['dr_short_mw'][i]
        if type(short) in (int, float) and short > 0:
            facts.append(f'Reserve short {short:,.0f} MW at {t[11:16]} (WESM RTD)')
        curtailed = series['curtailed_mw'][i]
        if type(curtailed) in (int, float) and curtailed > 0:
            facts.append(f'Curtailed {curtailed:,.0f} MW at {t[11:16]} (WESM RTD)')
        demand = series['demand_mw'][i]
        if type(demand) in (int, float):
            facts.append(f'Demand {demand:,.0f} MW at {t[11:16]} (WESM RTD)')
        # The region's notices around it, never claimed as the cause (owner rule: no uncertain match).
        around = d['notice_index'].around(dict(episode, region=code, direction=direction), at, series, d['t'])
        main = (f"{cause['title']} (notice {cause['advisory']} at {cause['known_at'][11:16]})" if cause
                else notices_mod.driver_text(around))
        key = episode.get('key') or model.alert_key(code, episode['first'], 'replay-' + direction)
        return {
            'key': key, 'source': 'replay',
            'region': code, 'region_label': model.REGIONS[code], 'direction': direction,
            'first': episode['first'], 'last': episode['last'], 'intervals': len(points),
            'interval_manila': t, 'price_php_mwh': price, 'usual_php_mwh': usual,
            'threshold_text': model.level_text(direction, level, usual if level['mode'] != 'absolute' else None,
                                               'usual (same-hour median of earlier replay days)'),
            'severity': severity, 'severity_reason': reason, 'main_driver': main,
            'cause': ({'kind': 'event', 'id': cause['id'], 'title': cause['title'], 'advisory': cause['advisory'],
                       'known_at': cause['known_at'], 'href': '/event/' + cause['id']} if cause else None),
            'facts': facts, 'points': [(p[1], p[2]) for p in points],
            'notices_around': around,
            # With no recorded event the alert has its own page, built from this bake on request
            # (src/grid/spike.*): the series and notices around it, no cause claimed.
            'href': ('/event/' + cause['id']) if cause else ('/alert/' + key),
        }


def severity_of(direction, price, usual, intervals):
    """(severity, reason): the stated rule on the recorded price."""
    if direction == 'spike':
        if price >= model.PRICE_CAP:
            return 'extreme', f'at the offer cap ({model.PRICE_CAP:,} PHP/MWh)'
        if usual is not None and usual > 0 and price >= 2 * usual:
            return 'high', f'{price / usual:.1f} x usual'
        if intervals >= 6:
            return 'high', f'{intervals} intervals above the level (30 minutes or more)'
        return 'medium', 'above the level' + (f', {price / usual:.1f} x usual' if usual and usual > 0 else ', no usual price yet')
    if price <= model.PRICE_FLOOR:
        return 'high', f'at the offer floor ({model.PRICE_FLOOR:,} PHP/MWh)'
    if price <= 0:
        return 'medium', 'at or below zero'
    return 'low', 'below the level'


# With no rules saved, the replay still shows what the desk's usual levels would raise: the page's
# own default spike level and a collapse at zero, every region. Stated as such on the page.
DEFAULT_RULES = {'version': None, 'enabled': False, 'threshold': {'mode': 'absolute', 'value': 15000},
                 'regions': sorted(model.REGIONS), 'min_severity': 'high', 'recipients': [],
                 'levels': {code: {'spike': None, 'collapse': {'mode': 'absolute', 'value': 0}} for code in model.REGIONS}}
