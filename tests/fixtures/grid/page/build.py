#!/usr/bin/env python3
"""Build the grid-page fixture: one synthetic replay day in the baked-data contract.

Every value here is computed from the interval index by the formulas below — there is no
randomness, no real WESM row, no real plant, coordinate or operator message, and nothing is
read from the company copy. The shapes are the ones `src/grid/grid.js` reads and
`scripts/grid/build_data.py` writes (GRID-1): `regions.json`, `hvdc.json`,
`nodes-2026-09-21.json`, `advisories.json`, `sites.json`, `events.json`, `ph.geojson`.

Two more files (ATG-8) are composed from those seven by the real composer,
`scripts/grid/briefs.py` (ATG-5), exactly as the bake composes them: `briefs.json` and
`findings.json`. They are what the page's briefing and findings panel mounts, so the fixture
the page tests read carries the panel's own payloads; nothing here is re-implemented for the
fixture.

Three more files (DESK-1) are the event page's register-and-price-outlook views,
`outlook/<event-id>.json`, written by the real builder (`scripts/grid/build_data.py`) from the
synthetic register and price-outlook archive beside the grid fixture
(`tests/fixtures/grid/outlook/`): one per event the browser harness serves, so the event page's
new section reads a file wherever it is loaded. The synthetic event's assumption resolves that
fixture register's availability row — the page then shows the linked chain — while the two
rules events' governed assumptions match no row and are shown as not registered.

    /usr/bin/python3 tests/fixtures/grid/page/build.py            # write data/ beside this file
    /usr/bin/python3 tests/fixtures/grid/page/build.py --check    # compare, write nothing

`--check` exits non-zero when the committed bytes differ, so the fixture the page test reads
is reproducible from this file alone (tests/test_grid_page.py calls it that way).
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DAY = '2026-09-21'
INTERVALS = 288                     # one five-minute interval per entry, 00:00 to 23:55
TRIP = 164                          # 13:40, the interval the event advisory is posted in
SPIKE = range(TRIP, TRIP + 4)       # 13:40 to 13:55: the price cap and load dropping
FIELDS = ('demand_mw', 'gen_mw', 'import_mw', 'export_mw', 'curtailed_mw', 'dr_req_mw',
          'dr_short_mw', 'lmp_median', 'lmp_max')
GRIDS = ('CLUZ', 'CVIS', 'CMIN')
SHAPE = {'SYN-BAY-1': (123.42, 10.90), 'SYN-BAY-2': (None, None), 'SYN-LEY-1': (124.62, 11.02),
         'SYN-LUZ-1': (121.10, 14.30), 'SYN-MIN-1': (124.70, 7.60), 'SYN-VIS-LD': (None, None),
         'SYN-PS-1': (123.55, 10.70)}
SITES = [
    {'s': 'SYN-BAY-1', 'k': 'G', 'g': 'CVIS', 'cap': 260, 'lon': 123.42, 'lat': 10.90,
     'p': 'municipality', 'name': 'Synthetic Bay Power'},
    # Position pending: no coordinates and no name, so the page draws it in its own column.
    {'s': 'SYN-BAY-2', 'k': 'G', 'g': 'CVIS', 'cap': 320, 'lon': None, 'lat': None,
     'p': 'placeholder'},
    {'s': 'SYN-LEY-1', 'k': 'G', 'g': 'CVIS', 'cap': 180, 'lon': 124.62, 'lat': 11.02,
     'p': 'plant', 'name': 'Synthetic Leyte Geothermal'},
    {'s': 'SYN-LUZ-1', 'k': 'G', 'g': 'CLUZ', 'cap': 600, 'lon': 121.10, 'lat': 14.30,
     'p': 'plant', 'name': 'Synthetic Luzon Combined Cycle'},
    {'s': 'SYN-MIN-1', 'k': 'G', 'g': 'CMIN', 'cap': 210, 'lon': 124.70, 'lat': 7.60,
     'p': 'municipality'},
    {'s': 'SYN-VIS-LD', 'k': 'NL', 'g': 'CVIS', 'cap': 900, 'lon': None, 'lat': None,
     'p': 'placeholder'},
    {'s': 'SYN-PS-1', 'k': 'PS', 'g': 'CVIS', 'cap': 120, 'lon': 123.55, 'lat': 10.70,
     'p': 'plant', 'name': 'Synthetic Pumped Storage'},
]
ADVISORIES = [
    {'t': '2026-09-21 06:00:00', 'id': 'SYN-ADV-0001', 'grid': 'CVIS', 'kind': 'notice',
     'text': 'Synthetic Bay Unit 2 is on planned outage until 1800H.'},
    {'t': '2026-09-21 09:10:00', 'id': 'SYN-ADV-0005', 'grid': 'CLUZ', 'kind': 'yellow',
     'text': 'Yellow alert raised over the Luzon Grid from 0910H to 1200H.'},
    {'t': '2026-09-21 13:40:00', 'id': 'SYN-ADV-0002', 'grid': 'CVIS', 'kind': 'trip',
     'text': 'Unit 2 of SYNTHETIC BAY POWER tripped. Load dropping may follow.'},
    {'t': '2026-09-21 13:45:00', 'id': 'SYN-ADV-0003', 'grid': 'CVIS', 'kind': 'mld',
     'text': 'Manual load dropping of 60 MW started in the Visayas Grid.'},
    {'t': '2026-09-21 14:20:00', 'id': 'SYN-ADV-0004', 'grid': 'CVIS', 'kind': 'online',
     'text': 'Synthetic Bay Unit 2 is back online at 180 MW. Load dropping ended.'},
    {'t': '2026-09-21 16:05:00', 'id': 'SYN-ADV-0006', 'grid': 'CMIN', 'kind': 'trip',
     'text': 'Synthetic Mindanao Unit 1 tripped at 1601H. (Unplanned Outage)'},
    {'t': '2026-09-22 07:30:00', 'id': 'SYN-ADV-0007', 'grid': 'CVIS', 'kind': 'notice',
     'text': 'Synthetic Bay Unit 2 is on planned outage until 1200H.'},
]
EVENTS = [
    {'id': 'syn-bay-unit-2-trip', 't': '2026-09-21 13:40:00', 'advisory': 'SYN-ADV-0002',
     'site': 'SYN-BAY-2', 'title': 'Synthetic Bay Unit 2 trip',
     'assumption': 'Synthetic Bay Unit 2 available capacity'},
]
#: DESK-1: the assumption texts the browser-served events carry. The fixture's own event uses
#: the text above; the two rules views' events carry the proposition of the assumption their
#: case governs, read from the view files the harness serves, so the page's new section never
#: shows a text the event's own record does not carry.
RULES_VIEWS = {
    'reserve-market-2026-10-14': ROOT / 'tests/fixtures/grid/event/reserve-market/view.json',
    'fixture-rules-in-force': ROOT / 'tests/fixtures/grid/event/rules-in-force/view.json',
}
#: DESK-1: the synthetic register and price-outlook archive the outlook views are built from.
OUTLOOK = ROOT / 'tests/fixtures/grid/outlook'


def times():
    """The shared interval axis: Manila civil time as the company copy stores it."""
    return ['%s %02d:%02d:00' % (DAY, (i * 5) // 60, (i * 5) % 60) for i in range(INTERVALS)]


def wave(base, amplitude, i):
    """One deterministic daily curve: peak mid-afternoon, trough before dawn."""
    return base + amplitude * math.sin(2 * math.pi * (i - 108) / INTERVALS)


def region_field(grid, field, i):
    """One region figure at interval `i`; CVIS carries the event."""
    visayas = grid == 'CVIS'
    if field == 'demand_mw':
        if visayas and i in SPIKE:
            return 1560
        return round(wave({'CLUZ': 9000, 'CVIS': 1500, 'CMIN': 1800}[grid],
                          {'CLUZ': 1400, 'CVIS': 220, 'CMIN': 260}[grid], i))
    if field == 'gen_mw':
        return round(region_field(grid, 'demand_mw', i) - region_field(grid, 'import_mw', i)
                     + region_field(grid, 'export_mw', i))
    if field == 'import_mw':
        return {'CLUZ': 0, 'CVIS': 250 + (60 if visayas and i in SPIKE else 0), 'CMIN': 0}[grid]
    if field == 'export_mw':
        return {'CLUZ': 400, 'CVIS': 0, 'CMIN': 120}[grid]
    if field == 'curtailed_mw':
        return 240 if visayas and i in SPIKE else 0
    if field == 'dr_req_mw':
        return {'CLUZ': 1100, 'CVIS': 320, 'CMIN': 260}[grid]
    if field == 'dr_short_mw':
        return 140 if visayas and i in SPIKE else 0
    if field == 'lmp_median':
        if visayas and i in SPIKE:
            return 32000
        return {'CLUZ': round(wave(2900, 260, i)), 'CVIS': round(wave(3200, 320, i)),
                'CMIN': round(wave(3400, 300, i))}[grid]
    if field == 'lmp_max':
        return 32000 if visayas and i in SPIKE else round(region_field(grid, 'lmp_median', i) * 1.1)
    raise AssertionError(field)


def regions():
    axis = times()
    return {'t': axis, 'grids': {g: {f: [region_field(g, f, i) for i in range(INTERVALS)]
                                     for f in FIELDS} for g in GRIDS}}


def hvdc():
    axis = times()
    links = {}
    # Positive flow: the first grid in the name sends to the second (MINVIS1: Mindanao->Visayas,
    # VISLUZ1: Visayas->Luzon). At the trip the Visayas draws from Luzon, so VISLUZ1 reverses.
    for name, base in (('MINVIS1', 250), ('VISLUZ1', 120)):
        flow, congested = [], []
        for i in range(INTERVALS):
            if name == 'MINVIS1':
                flow.append(base + (60 if i in SPIKE else 0))
            else:
                flow.append(-base - (260 if i in SPIKE else 0))
            congested.append(1 if i in SPIKE and i == TRIP else 0)
        links[name] = {'flow': flow, 'congested': congested}
    return {'t': axis, 'links': links}


def nodes():
    axis = times()
    sites = [s['s'] for s in SITES]
    lmp, mw = [], []
    for i in range(INTERVALS):
        lmp.append([node_lmp(s['s'], i) for s in SITES])
        mw.append([node_mw(s, i) for s in SITES])
    return {'t': axis, 'sites': sites, 'lmp': lmp, 'mw': mw}


def node_lmp(site, i):
    if site in ('SYN-BAY-1', 'SYN-BAY-2', 'SYN-LEY-1', 'SYN-PS-1'):
        return 32000 if i in SPIKE else region_field('CVIS', 'lmp_median', i)
    if site == 'SYN-VIS-LD':
        return region_field('CVIS', 'lmp_median', i) if i not in SPIKE else 32000
    if site == 'SYN-LUZ-1':
        return region_field('CLUZ', 'lmp_median', i)
    return region_field('CMIN', 'lmp_median', i)


def node_mw(site, i):
    cap = site['cap']
    if site['k'] == 'NL':
        return round(wave(cap, cap * 0.08, i), 1)
    if site['s'] == 'SYN-BAY-2':
        return 0.0 if i in SPIKE else 260.0
    if site['k'] == 'PS':
        return round(cap * 0.5, 1)
    return round(wave(cap * 0.75, cap * 0.1, i), 1)


def geojson():
    """A box for the country and one per grid: enough geometry for the page's projector."""
    def box(kind, west, south, east, north):
        ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
        return {'type': 'Feature', 'properties': {'kind': kind},
                'geometry': {'type': 'Polygon', 'coordinates': [ring]}}
    return {'type': 'FeatureCollection', 'features': [
        box('country', 112.9, 4.4, 127.2, 21.2),
        box('province', 119.5, 13.0, 122.5, 18.5),
        box('province', 122.6, 9.5, 125.6, 12.5),
        box('province', 123.0, 5.5, 126.5, 9.0),
    ]}


ALLOWED = {"q1": ["the mapped unit", "another unit", "cannot tell"], "q2": ["planned outage", "forced outage", "return to service", "derating", "grid alert", "testing", "commercial operation", "other"], "q3": ["before", "same", "after", "not stated"], "q4": ["yes", "no"], "q5": ["yes", "no"], "q6": ["yes", "no"], "q7": ["yes", "no"], "q8": ["supports", "challenges", "neither"]}


def event_view():
    """The event page's view model for the synthetic event (EXPL-1): the same shape the recorded
    PEDC view carries, with synthetic text, a synthetic judgment and two synthetic cutoffs."""
    questions = [('q1', 'Which unit', 'SYN-BAY-2', 'Which unit does the notice talk about?'),
                 ('q2', 'What happened', 'forced outage', 'What kind of event is it?'),
                 ('q3', 'Time against the assumption', 'same', "When did it happen, compared with the assumption's day?"),
                 ('q4', 'Conditional or planned', 'no', 'Is the statement conditional or planned?'),
                 ('q5', 'Repeats an earlier source', 'no', 'Does the notice only repeat an earlier source?'),
                 ('q6', 'An observation, not a plan', 'yes', 'Does it report something that happened, not a plan?'),
                 ('q7', 'Enough to decide', 'yes', 'Is the evidence enough to decide?'),
                 ('q8', 'Direction for the assumption', 'challenges', 'Taken alone, does the notice support or challenge the assumption?')]
    judgment = {'label': 'challenges', 'rule': 'synthetic rule: Q2=forced_outage, Q3=same',
                'by': 'synthetic fixture', 'unstable': False,
                'receipt': '4 phrasings × 8 questions · synthetic fixture, no model run',
                'questions': [{'id': i, 'label': l, 'answers': [m] * 4, 'modal': m, 'agree': [True] * 4,
                               'key': i in ('q2', 'q8'), 'plain': plain, 'allowed': ALLOWED[i]} for i, l, m, plain in questions]}
    t = lambda i: '%sT%02d:%02d' % (DAY, i // 12, (i % 12) * 5)
    series = list(range(TRIP - 24, TRIP + 37))
    return {'id': EVENTS[0]['id'], 'title': EVENTS[0]['title'], 'grid': 'CVIS', 'grid_name': 'Visayas',
            'event_at': t(TRIP),
            'advisory': {'id': 'SYN-ADV-0002', 't': t(TRIP) + ':00', 'text': ADVISORIES[2]['text']},
            'timeline': [{'t': t(TRIP) + ':00', 'kind': 'trip', 'text': ADVISORIES[2]['text'], 'src': 'SYN-ADV-0002'},
                         {'t': t(TRIP + 1) + ':00', 'kind': 'mld', 'text': ADVISORIES[3]['text'], 'src': 'SYN-ADV-0003'},
                         {'t': t(TRIP + 8) + ':00', 'kind': 'online', 'text': ADVISORIES[4]['text'], 'src': 'SYN-ADV-0004'}],
            'market': {'t': [t(i) for i in series],
                       'lmp': [node_lmp('SYN-BAY-1', i) for i in series],
                       'short': [region_field('CVIS', 'dr_short_mw', i) for i in series],
                       'imp': [region_field('CVIS', 'import_mw', i) for i in series],
                       'marks': [{'t': t(TRIP), 'kind': 'trip'}, {'t': t(TRIP + 8), 'kind': 'online'}]},
            'figures': [{'k': 'Price at 14:30', 'v': '32,000', 'unit': '/MWh', 'd': 'synthetic', 'up': False},
                        {'k': 'Reserve short', 'v': '60', 'unit': 'MW', 'd': 'synthetic', 'up': True}],
            'assumption': {'value': 180.0, 'unit': 'MW',
                           'proposition': 'Synthetic Bay Unit 2 is available at its registered capacity.',
                           'kv': [['Unit', 'SYN-BAY-2'], ['Registered', '180 MW, synthetic register']],
                           'accepted': {'at': '%sT00:10 +08:00' % DAY, 'by': 'synthetic fixture',
                                        'source': 'synthetic register'}},
            'judgment': judgment,
            'cutoffs': [{'advisory': 'SYN-ADV-0002', 't': t(TRIP) + ':00', 'pair': 'trip',
                         'before': t(TRIP) + ':00', 'after': t(TRIP) + ':01',
                         'judgments': [{'source': 'synthetic model reading', 'at': 'after', 'label': 'challenges',
                                        'rule': judgment['rule'], 'stable': True, 'receipt': judgment['receipt']},
                                       {'source': 'synthetic case reading', 'at': 'before', 'label': None,
                                        'rule': 'no passage known before this notice', 'stable': None,
                                        'receipt': 'blocked compile'}]},
                        {'advisory': 'SYN-ADV-0003', 't': t(TRIP + 1) + ':00', 'pair': None, 'judgments': []},
                        {'advisory': 'SYN-ADV-0004', 't': t(TRIP + 8) + ':00', 'pair': 'return',
                         'before': t(TRIP + 8) + ':00', 'after': t(TRIP + 8) + ':01',
                         'judgments': [{'source': 'synthetic model reading', 'at': 'after', 'label': 'challenges',
                                        'rule': judgment['rule'], 'stable': True, 'receipt': judgment['receipt']},
                                       {'source': 'synthetic case reading', 'at': 'after', 'label': 'supports',
                                        'rule': 'synthetic rule: Q2=return_to_service', 'stable': True,
                                        'receipt': 'synthetic fixture'}]}],
            'limits': ['Synthetic replay day; nothing here is real.',
                       'The judgment is a synthetic fixture; no model ran.']}


def briefs_module():
    """The real composer, `scripts/grid/briefs.py`, loaded by location (ATG-5).

    The two composed fixture files are that module's own output over the seven files this
    builder writes, so the fixture carries the panel's contract and not a second copy of it.
    """
    spec = importlib.util.spec_from_file_location('grid_briefs_page_fixture',
                                                  ROOT / 'scripts' / 'grid' / 'briefs.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def brief_files():
    """`briefs.json` and `findings.json`, composed by `scripts/grid/briefs.py` over `files()`."""
    briefs = briefs_module()
    source = files()
    bake = {'regions': source['regions.json'], 'hvdc': source['hvdc.json'],
            'advisories': source['advisories.json'], 'events': source['events.json'],
            'dir': str(HERE / 'data')}
    rules = briefs.load_rules(ROOT / 'scripts' / 'grid' / 'findings_rules.json')
    composed, findings, composed_briefs = briefs.composed(
        bake, rules, briefs.data_name(HERE / 'data'), 'findings_rules.json')
    problems = briefs.validate(bake, rules, findings, composed_briefs)
    if problems:
        raise SystemExit('the composed fixture is not valid: ' + '; '.join(problems))
    return {name: json.loads(payload.decode('utf-8')) for name, payload in composed.items()}


def files():
    """The seven files the formulas write."""
    return {'regions.json': regions(), 'hvdc.json': hvdc(), 'nodes-%s.json' % DAY: nodes(),
            'advisories.json': ADVISORIES, 'sites.json': SITES, 'events.json': EVENTS,
            'ph.geojson': geojson()}


def outlook_builder():
    """`scripts/grid/build_data.py` by location, the one the bake runs (DESK-1)."""
    path = ROOT / 'scripts' / 'grid' / 'build_data.py'
    spec = importlib.util.spec_from_file_location('grid_build_data_page_fixture', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def outlook_events():
    """`(event id, assumption text, recorded time)` for every event the browser harness serves.

    The recorded time is each event's own — the fixture event's spec row, and the two rules
    events' `event_at` read from the very views the harness serves. The outlook view names it
    (copy rule 1) and never a clock, so the fixture carries the records' own times.
    """
    events = [(EVENTS[0]['id'], EVENTS[0]['assumption'], EVENTS[0]['t'])]
    for event_id, view_path in sorted(RULES_VIEWS.items()):
        view = json.loads(view_path.read_text(encoding='utf-8'))
        events.append((event_id, view['rules']['governs']['assumption']['proposition'],
                       view['event_at']))
    return events


def outlook_files():
    """`outlook/<id>.json` per browser-served event, written by the real builder (DESK-1)."""
    built, _ = outlook_builder().price_outlook_files(
        [{'id': event_id, 'assumption': text, 't': at}
         for event_id, text, at in outlook_events()],
        OUTLOOK / 'register.json', OUTLOOK / 'archive')
    return {name: json.loads(payload.decode('utf-8')) for name, payload in built.items()}


def all_files():
    """Everything under `data/`: the seven above, the two the real composer writes and the
    event page's register-and-price-outlook views (DESK-1)."""
    fixture = files()
    fixture.update(brief_files())
    fixture.update(outlook_files())
    return fixture


def views():
    """The event views, served under `/grid-data/events/` beside the seven files above. They
    live in `views/` next to `data/` so a suite that copies `data/` and adds its own `events/`
    (the hosting stage tests) keeps working; `browser.mjs --views` serves them."""
    return {'events/%s.json' % EVENTS[0]['id']: event_view(), 'vectors.json': vectors()}


def vectors():
    """EXPL-2: a synthetic vector table of the shape `scripts/grid/build_data.py` writes from the
    event-map spike: a small vocabulary, deterministic vectors, a plane, and the type index of
    every fixture message (`null` for a message the vocabulary does not cover)."""
    vocab = ['V:unit:out:planned', 'L:system:yellow', 'V:unit:trip:unplanned', 'V:system:loaddrop', 'V:unit:return:unplanned',
             'M:unit:trip:unplanned']
    dim = 4
    table = [[round(math.sin(1.7 * i + 0.9 * j) * 0.8, 4) for j in range(dim)] for i in range(len(vocab))]
    plane = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.0, 0.0]]
    types = {a['id']: i if i < len(vocab) else None for i, a in enumerate(ADVISORIES)}
    return {'vocab': vocab, 'E': table, 'plane': plane, 'max_norm': 4.0,
            'corpus': {'messages': 5, 'span': 'synthetic', 'source': 'synthetic fixture'}, 'types': types}


def dump(name, obj):
    """The builder's own writing style: compact JSON, no trailing newline."""
    return json.dumps(obj, separators=(',', ':'))


def build(target, views_target=None):
    target.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, obj in all_files().items():
        written[name] = dump(name, obj)
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(written[name], encoding='utf-8')
    views_target = views_target or target.parent / 'views'
    for name, obj in views().items():
        written['views/' + name] = dump(name, obj)
        (views_target / name).parent.mkdir(parents=True, exist_ok=True)
        (views_target / name).write_text(written['views/' + name], encoding='utf-8')
    return written


def check(target, views_target=None):
    """Compare the committed bytes with the formulas; report every file that differs."""
    views_target = views_target or target.parent / 'views'
    expected = {name: dump(name, obj) for name, obj in all_files().items()}
    problems = []
    for name, text in expected.items():
        path = target / name
        if not path.is_file():
            problems.append(f'missing {name}')
        elif path.read_text(encoding='utf-8') != text:
            problems.append(f'{name} differs from the formulas')
    extra = sorted(p.name for p in target.glob('*') if p.is_file() and p.name not in expected)
    problems += [f'unexpected {name}' for name in extra]
    for name, obj in views().items():
        path = views_target / name
        if not path.is_file():
            problems.append(f'missing views/{name}')
        elif path.read_text(encoding='utf-8') != dump(name, obj):
            problems.append(f'views/{name} differs from the formulas')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('target', nargs='?', type=Path, default=HERE / 'data')
    parser.add_argument('--check', action='store_true')
    options = parser.parse_args(argv)
    if options.check:
        problems = check(options.target)
        print('\n'.join(problems) if problems else f'OK: {len(all_files())} fixture files and {len(views())} event views reproduce')
        return 1 if problems else 0
    for name, size in sorted((n, len(t)) for n, t in build(options.target).items()):
        print(f'{name} {size}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
