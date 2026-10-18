"""The baked replay as the desk API reads it: one directory, parsed lazily, cached in memory.

The directory is the one the `/grid-data` route serves (`src/api.grid_data_directory`). Its files
are immutable for one build, so a parsed file is kept for the life of the process; the per-day
files (node days, day slices, event views, advisory months) sit in a small LRU so a year bake
never holds every day at once. Nothing here writes, and a missing or unreadable file is `None`
(the caller answers an empty section), never an error.

Two bake shapes are read:

* the year bake: `replay.json`, `days/<day>.json` (the day's regions and links plus `usual`),
  `advisories/<YYYY-MM>.json`, `nodes-<day>.json` for the node days;
* the single-file bake (the page fixture): `regions.json`, `hvdc.json`, `advisories.json`,
  `nodes-<day>.json`. Its `usual` is derived here by the same rule (`src/alerts/replay.py`).

Timestamps arrive as `2026-09-21 00:00:00` (the page fixture) or `2026-09-21T13:40[:SS]` (the
bake); every time leaves this module as `YYYY-MM-DDTHH:MM`.
"""
import json
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, RLock

GRIDS = ('CLUZ', 'CVIS', 'CMIN')
GRID_NAMES = {'CLUZ': 'Luzon', 'CVIS': 'Visayas', 'CMIN': 'Mindanao'}
LINKS = {'VISLUZ1': ('CVIS', 'CLUZ'), 'MINVIS1': ('CMIN', 'CVIS')}
AT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z')
DAY = re.compile(r'\d{4}-\d{2}-\d{2}\Z')
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
LRU_SIZE = 24


def norm_t(value):
    """`YYYY-MM-DDTHH:MM` from either stored shape, or None when it is not a time."""
    text = str(value or '')[:16].replace(' ', 'T')
    return text if AT.fullmatch(text) else None


def parse_t(at):
    return datetime.strptime(at, '%Y-%m-%dT%H:%M')


def shift(at, minutes):
    return (parse_t(at) + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


def minutes_between(a, b):
    """Minutes from `a` to `b` (both `YYYY-MM-DDTHH:MM`)."""
    return int((parse_t(b) - parse_t(a)).total_seconds() // 60)


def number(value):
    """A finite int or float as stored, else None (a bool is not a number here)."""
    if type(value) in (int, float) and value == value and value not in (float('inf'), float('-inf')):
        return value
    return None


class _Lru:
    def __init__(self, size):
        self.size, self.items = size, OrderedDict()

    def get(self, key, load):
        if key in self.items:
            self.items.move_to_end(key)
            return self.items[key]
        value = load()
        self.items[key] = value
        if len(self.items) > self.size:
            self.items.popitem(last=False)
        return value


class Bake:
    """One baked replay directory, read on demand."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self._lock = RLock()
        self._once = {}
        self._lru = _Lru(LRU_SIZE)

    # ---------------------------------------------------------------- raw files

    def _read(self, name):
        try:
            return json.loads((self.directory / name).read_text(encoding='utf-8'))
        except (OSError, ValueError, UnicodeDecodeError):
            return None

    def _cached(self, key, load):
        with self._lock:
            if key not in self._once:
                self._once[key] = load()
            return self._once[key]

    def _recent(self, key, load):
        with self._lock:
            return self._lru.get(key, load)

    # ---------------------------------------------------------------- the span

    def index(self):
        """{'first', 'last', 'days', 'node_days', 'months', 'by_day'}: what the bake holds."""
        return self._cached('index', self._index)

    def _index(self):
        replay = self._read('replay.json')
        if isinstance(replay, dict) and isinstance(replay.get('days'), list):
            days = sorted(d for d in replay['days'] if isinstance(d, str) and DAY.fullmatch(d))
            node_days = [d for d in replay.get('node_days') or [] if isinstance(d, str) and DAY.fullmatch(d)]
            months = [m for m in replay.get('months') or [] if isinstance(m, str)]
            return {'first': norm_t(replay.get('first')), 'last': norm_t(replay.get('last')),
                    'days': days, 'node_days': sorted(set(node_days)), 'months': months, 'by_day': True}
        regions = self._regions_whole()
        times = regions['t'] if regions else []
        node_days = sorted(p.name[6:16] for p in self._listing('.') if re.fullmatch(r'nodes-\d{4}-\d{2}-\d{2}\.json', p.name))
        return {'first': times[0] if times else None, 'last': times[-1] if times else None,
                'days': sorted({t[:10] for t in times}), 'node_days': node_days, 'months': [], 'by_day': False}

    def _listing(self, sub):
        try:
            return sorted((self.directory / sub).iterdir())
        except OSError:
            return []

    def last(self):
        return self.index()['last']

    # ---------------------------------------------------------------- regions and links per day

    def _regions_whole(self):
        """The single-file bake's regions and links, normalised, with `usual` per day (or None)."""
        return self._cached('regions', self._load_regions_whole)

    def _load_regions_whole(self):
        regions = self._read('regions.json')
        if not isinstance(regions, dict) or not isinstance(regions.get('t'), list):
            return None
        times = [norm_t(t) for t in regions['t']]
        if any(t is None for t in times):
            return None
        grids = {}
        for code in GRIDS:
            g = (regions.get('grids') or {}).get(code)
            if isinstance(g, dict):
                grids[code] = {k: v for k, v in g.items() if isinstance(v, list) and len(v) == len(times)}
        hvdc = self._read('hvdc.json')
        links = {}
        if isinstance(hvdc, dict) and [norm_t(t) for t in hvdc.get('t') or []] == times:
            for name, link in (hvdc.get('links') or {}).items():
                if isinstance(link, dict):
                    links[str(name)] = {k: v for k, v in link.items() if isinstance(v, list) and len(v) == len(times)}
        usual = {code: _usual_by_day(times, grids.get(code, {}).get('lmp_median')) for code in GRIDS}
        return {'t': times, 'grids': grids, 'links': links, 'usual': usual}

    def day(self, day):
        """{'t', 'grids', 'links', 'usual'} for one civil day, or None when the bake has none."""
        if not isinstance(day, str) or not DAY.fullmatch(day):
            return None
        if self.index()['by_day']:
            return self._recent(('day', day), lambda: self._load_day_file(day))
        whole = self._regions_whole()
        if not whole:
            return None
        return self._cached(('day', day), lambda: _slice_day(whole, day))

    def _load_day_file(self, day):
        payload = self._read(f'days/{day}.json')
        if not isinstance(payload, dict) or not isinstance(payload.get('t'), list):
            return None
        times = [norm_t(t) for t in payload['t']]
        if any(t is None for t in times):
            return None
        out = {'t': times, 'grids': {}, 'links': {}, 'usual': {}}
        for code in GRIDS:
            g = (payload.get('grids') or {}).get(code)
            if isinstance(g, dict):
                out['grids'][code] = {k: v for k, v in g.items() if isinstance(v, list) and len(v) == len(times)}
            table = (payload.get('usual') or {}).get(code)
            out['usual'][code] = table if isinstance(table, dict) else {}
        for name, link in (payload.get('links') or {}).items():
            if isinstance(link, dict):
                out['links'][str(name)] = {k: v for k, v in link.items() if isinstance(v, list) and len(v) == len(times)}
        return out

    def series(self, start, end, pick):
        """`(times, values)` over the intervals in (start, end], read day by day.

        `pick(day_payload, i)` gives one value. Days the bake does not hold are skipped.
        """
        times, values = [], []
        day = start[:10]
        while day <= end[:10]:
            payload = self.day(day)
            if payload:
                for i, t in enumerate(payload['t']):
                    if start < t <= end:
                        times.append(t)
                        values.append(pick(payload, i))
            day = (datetime.strptime(day, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        return times, values

    def interval(self, at, stale_minutes=30):
        """`(day_payload, index)` of the latest interval at or before `at`, within `stale_minutes`;
        `(None, None)` when no interval is on record that close to the clock."""
        for day in (at[:10], shift(at, -24 * 60)[:10]):
            payload = self.day(day)
            if not payload:
                continue
            best = None
            for i, t in enumerate(payload['t']):
                if t <= at:
                    best = i
                else:
                    break
            if best is not None:
                if minutes_between(payload['t'][best], at) > stale_minutes:
                    return None, None
                return payload, best
        return None, None

    # ---------------------------------------------------------------- nodes

    def nodes(self, day):
        """{'t', 'sites', 'lmp', 'mw', 'col'} for one node day, or None."""
        if not isinstance(day, str) or not DAY.fullmatch(day):
            return None
        return self._recent(('nodes', day), lambda: self._load_nodes(day))

    def _load_nodes(self, day):
        payload = self._read(f'nodes-{day}.json')
        if not isinstance(payload, dict):
            return None
        times = [norm_t(t) for t in payload.get('t') or []]
        sites = payload.get('sites')
        lmp, mw = payload.get('lmp'), payload.get('mw')
        if not times or any(t is None for t in times) or not isinstance(sites, list):
            return None
        if not isinstance(lmp, list) or len(lmp) != len(times):
            return None
        if not isinstance(mw, list) or len(mw) != len(times):
            mw = [[None] * len(sites)] * len(times)
        return {'t': times, 'sites': [str(s) for s in sites], 'lmp': lmp, 'mw': mw,
                'col': {str(s): j for j, s in enumerate(sites)}}

    def node_interval(self, at, stale_minutes=30):
        """`(nodes_payload, row)` of the latest node interval at or before `at`, or `(None, None)`."""
        payload = self.nodes(at[:10])
        if not payload:
            return None, None
        best = None
        for i, t in enumerate(payload['t']):
            if t <= at:
                best = i
            else:
                break
        if best is None or minutes_between(payload['t'][best], at) > stale_minutes:
            return None, None
        return payload, best

    def node_value(self, payload, row, code, field='lmp'):
        j = payload['col'].get(code)
        if j is None:
            return None
        cells = payload[field][row]
        return number(cells[j]) if isinstance(cells, list) and j < len(cells) else None

    def node_series(self, code, start, end, field='lmp'):
        times, values = [], []
        day = start[:10]
        while day <= end[:10]:
            payload = self.nodes(day)
            if payload and code in payload['col']:
                for i, t in enumerate(payload['t']):
                    if start < t <= end:
                        times.append(t)
                        values.append(self.node_value(payload, i, code, field))
            day = (datetime.strptime(day, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        return times, values

    # ---------------------------------------------------------------- sites, events, notices

    def sites(self):
        """[{s, k, g, cap, name, located}], the bake's sites; [] without the file."""
        return self._cached('sites', self._load_sites)

    def _load_sites(self):
        rows = self._read('sites.json')
        names = {}
        index = self._read('assets/index.json')
        for entry in (index.get('sites') if isinstance(index, dict) else None) or []:
            if isinstance(entry, dict) and entry.get('s') and entry.get('name'):
                names[str(entry['s'])] = str(entry['name'])
        out = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not isinstance(row.get('s'), str) or not SAFE_ID.fullmatch(row['s']):
                continue
            name = row.get('name') or names.get(row['s'])
            out.append({'s': row['s'], 'k': str(row.get('k') or ''), 'g': row.get('g') if row.get('g') in GRIDS else None,
                        'cap': number(row.get('cap')), 'name': str(name) if name else None,
                        'located': row.get('p') in ('plant', 'municipality')})
        return out

    def site(self, code):
        return self._cached('site_map', lambda: {s['s']: s for s in self.sites()}).get(code)

    def events(self):
        """[{id, t, site, title, assumption, advisory, grid}] from `events.json`, oldest first."""
        return self._cached('events', self._load_events)

    def _load_events(self):
        rows = self._read('events.json')
        out = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            eid, t = str(row.get('id') or ''), norm_t(row.get('t'))
            if not SAFE_ID.fullmatch(eid) or t is None:
                continue
            site = row.get('site') if isinstance(row.get('site'), str) else None
            out.append({'id': eid, 't': t, 'site': site, 'title': str(row.get('title') or eid),
                        'assumption': str(row['assumption']) if row.get('assumption') else None,
                        'advisory': str(row.get('advisory') or '') or None})
        out.sort(key=lambda e: (e['t'], e['id']))
        return out

    def event_view(self, event_id):
        if not SAFE_ID.fullmatch(str(event_id)):
            return None
        return self._recent(('event', event_id), lambda: self._read(f'events/{event_id}.json'))

    def event_grid(self, event):
        """The event's grid: its view's own `grid`, else its site's grid, else its advisory's."""
        view = self.event_view(event['id'])
        if isinstance(view, dict) and view.get('grid') in GRIDS:
            return view['grid']
        site = self.site(event['site']) if event.get('site') else None
        if site and site['g']:
            return site['g']
        return None

    def advisories(self, start, end):
        """Notices with `start < t <= end`, oldest first: [{t, id, grid, kind, text}]."""
        out = []
        if self.index()['by_day']:
            months = sorted({start[:7], end[:7]} | {m for m in self.index()['months'] if start[:7] <= m <= end[:7]})
            for month in months:
                out.extend(self._recent(('month', month), lambda m=month: _notices(self._read(f'advisories/{m}.json'))))
            if not out and not any((self.directory / f'advisories/{m}.json').is_file() for m in months):
                out = self._cached('advisories', lambda: _notices(self._read('advisories.json')))
        else:
            out = self._cached('advisories', lambda: _notices(self._read('advisories.json')))
        return [a for a in out if start < a['t'] <= end]

    def all_advisories(self):
        """Every notice of the bake (the whole-span file, or the months), oldest first."""
        whole = self._cached('advisories', lambda: _notices(self._read('advisories.json')))
        if whole or not self.index()['months']:
            return whole
        out = []
        for month in self.index()['months']:
            out.extend(self._recent(('month', month), lambda m=month: _notices(self._read(f'advisories/{m}.json'))))
        return out

    def advisory(self, advisory_id, at):
        """One notice by id, known by `at`, or None."""
        for a in reversed(self.all_advisories()):
            if a['id'] == advisory_id:
                return a if a['t'] <= at else None
        return None

    # ---------------------------------------------------------------- the catalog

    def catalog(self):
        """{dataset id: {'name', 'definition'}} from the bake's `catalog.json`; {} without it."""
        return self._cached('catalog', self._load_catalog)

    def _load_catalog(self):
        payload = self._read('catalog.json')
        out = {}
        for entry in (payload.get('datasets') if isinstance(payload, dict) else None) or []:
            if isinstance(entry, dict) and isinstance(entry.get('id'), str):
                out[entry['id']] = {'name': str(entry.get('name') or entry['id']),
                                    'definition': str(entry.get('definition') or '') or None,
                                    'file': entry.get('file')}
        return out


def _notices(rows):
    out = []
    for a in rows if isinstance(rows, list) else []:
        if not isinstance(a, dict):
            continue
        t = norm_t(a.get('t'))
        if t is None:
            continue
        out.append({'t': t, 'id': str(a.get('id') or ''), 'grid': a.get('grid') if a.get('grid') in GRIDS else None,
                    'kind': str(a.get('kind') or 'notice'), 'text': str(a.get('text') or '')})
    out.sort(key=lambda a: (a['t'], a['id']))
    return out


def _slice_day(whole, day):
    rows = [i for i, t in enumerate(whole['t']) if t[:10] == day]
    if not rows:
        return None
    lo, hi = rows[0], rows[-1] + 1
    return {'t': whole['t'][lo:hi],
            'grids': {code: {k: v[lo:hi] for k, v in fields.items()} for code, fields in whole['grids'].items()},
            'links': {name: {k: v[lo:hi] for k, v in fields.items()} for name, fields in whole['links'].items()},
            'usual': {code: (whole['usual'].get(code) or {}).get(day, {}) for code in GRIDS}}


def _usual_by_day(times, prices):
    """{day: {'HH': [median, days]}}: the same-hour median over the EARLIER days only.

    The rule of `scripts/grid/build_data.py` `usual_by_day` and `src/alerts/replay.py`: nothing
    from the interval's own day or a later day reaches its usual; the first day has none.
    """
    import bisect
    if not isinstance(prices, list) or len(prices) != len(times):
        return {}
    by_day = {}
    for i, t in enumerate(times):
        by_day.setdefault(t[:10], []).append(i)
    earlier, seen, out = {}, {}, {}
    for day in sorted(by_day):
        hours = sorted({times[i][11:13] for i in by_day[day]})
        table = {}
        for hour in hours:
            values = earlier.get(hour)
            if values:
                n = len(values)
                middle = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
                table[hour] = [middle, seen[hour]]
            else:
                table[hour] = [None, 0]
        out[day] = table
        for hour in hours:
            vals = [number(prices[i]) for i in by_day[day] if times[i][11:13] == hour]
            vals = [v for v in vals if v is not None]
            for v in vals:
                bisect.insort(earlier.setdefault(hour, []), v)
            if vals:
                seen[hour] = seen.get(hour, 0) + 1
    return out


_BAKES = {}
_BAKES_LOCK = Lock()


def bake_for(directory):
    """The one `Bake` per resolved directory (the files are immutable for one build)."""
    try:
        key = str(Path(directory).resolve())
    except OSError:
        key = str(directory)
    with _BAKES_LOCK:
        if key not in _BAKES:
            _BAKES[key] = Bake(directory)
        return _BAKES[key]
