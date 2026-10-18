#!/usr/bin/env python3
"""Build the map-canvas fixture: the grid page's synthetic replay day, plus what the canvas
tests need — a position three sites share, a message naming one located site, and an outline
whose land the placeholder matrix does not touch.

Everything here is synthetic and deterministic, and it is derived from the page fixture's own
formulas (`tests/fixtures/grid/page/build.py`, imported by path): the same interval axis, the
same region series, the same two links, the same messages and event. Nothing is random, no real
WESM row, plant, coordinate, operator message or case fact appears, and nothing is read from the
company copy. What this fixture adds to the page fixture:

  * `sites.json` gains three synthetic sites:
      SYN-BAY-3   a generator at SYN-BAY-1's own position (123.42, 10.90) — with SYN-BAY-1 and
                  SYN-STA-1 that is one position three sites share, the real bake's own shape
                  (492 located sites on 193 positions, research §2.4a);
      SYN-STA-1   a load node with no registered capacity (cap null, as the bake writes for a
                  load node), at the same position;
      SYN-CALACA-1 a generator on the Luzon grid, alone at its position.
  * `advisories.json` gains one synthetic notice naming CALACA at 13:35 (the page fixture's own
    messages share the word BAY between several sites, so none of them resolves to one site by
    text; this one does, which is what the canvas's message marks need to be read).
  * `ph.geojson` moves the country box's west edge to 114.5 so no land covers the placeholder
    matrix's anchor (113.2, 20.6, open sea north-west of Luzon) — the same relationship the real
    Natural Earth outline has with it, and the reason a test can prove an unlocated site is never
    drawn on land.
  * `hvdc.json` carries the page fixture's own flags with two cells left unstated (null):
    `MINVIS1` at 13:45 and `VISLUZ1` at 14:00. A real link record can be silent for an interval,
    and an unknown congestion must be readable as unknown, not as a "not congested" — the canvas
    tests read these two cells for that state. The clock itself (13:40) is untouched: both links
    are congested there, as the page's formula states.

    /usr/bin/python3 tests/fixtures/grid/map/build.py            # write data/ beside this file
    /usr/bin/python3 tests/fixtures/grid/map/build.py --check    # compare, write nothing

`--check` exits non-zero when the committed bytes differ, so the fixture the map tests read is
reproducible from this file and the page fixture's (tests/test_grid_map.py calls it that way).
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / 'page'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


page = load('grid_page_fixture_build', PAGE / 'build.py')

DAY = '2026-09-21'
NODES_NAME = 'nodes-%s.json' % DAY
CLOCK = '2026-09-21 13:40:00'          # the trip interval, the clock the tests open on

# The three sites this fixture adds. Coordinates are synthetic; SYN-BAY-3 and SYN-STA-1 repeat
# SYN-BAY-1's position by construction — that is the stack under test.
EXTRA_SITES = [
    {'s': 'SYN-BAY-3', 'k': 'G', 'g': 'CVIS', 'cap': 280, 'lon': 123.42, 'lat': 10.90,
     'p': 'plant', 'name': 'Synthetic Bay Unit 3'},
    {'s': 'SYN-STA-1', 'k': 'NL', 'g': 'CVIS', 'cap': None, 'lon': 123.42, 'lat': 10.90,
     'p': 'municipality', 'name': 'Synthetic Bay Substation'},
    {'s': 'SYN-CALACA-1', 'k': 'G', 'g': 'CLUZ', 'cap': 300, 'lon': 120.90, 'lat': 13.90,
     'p': 'plant', 'name': 'Synthetic Calaca Unit'},
]
EXTRA_ADVISORY = {'t': '2026-09-21 13:35:00', 'id': 'SYN-ADV-0008', 'grid': 'CLUZ', 'kind': 'notice',
                  'text': 'Synthetic CALACA unit output reduced to 40 MW at 1335H.'}
# The two congestion cells this fixture leaves unstated: a null flag is the record being silent,
# which the canvas must read as unknown rather than as "not congested" (src/grid/map.js
# §congestionAt; tests/test_grid_map.py CongestionUnknown and the harness's unknown clock).
UNKNOWN_CONGESTION = [('MINVIS1', '2026-09-21 13:45:00'), ('VISLUZ1', '2026-09-21 14:00:00')]


def hvdc():
    """The page fixture's own flows and flags, with the two cells above set to null."""
    made = page.hvdc()
    for name, stamp in UNKNOWN_CONGESTION:
        made['links'][name]['congested'][made['t'].index(stamp)] = None
    return made


def sites():
    return [dict(s) for s in page.SITES] + [dict(s) for s in EXTRA_SITES]


def advisories():
    return [dict(a) for a in page.ADVISORIES] + [dict(EXTRA_ADVISORY)]


def node_lmp(site, i):
    """The page fixture's per-site price rule, extended to the three added sites: the Calaca
    generator follows its grid's median, the two stacked CVIS sites follow the Visayas spike."""
    if site['s'] == 'SYN-CALACA-1':
        return page.region_field('CLUZ', 'lmp_median', i)
    if site['s'] in ('SYN-BAY-3', 'SYN-STA-1'):
        return 32000 if i in page.SPIKE else page.region_field('CVIS', 'lmp_median', i)
    return page.node_lmp(site['s'], i)


def node_mw(site, i):
    if site['s'] == 'SYN-BAY-3':
        return round(page.wave(280 * 0.75, 28, i), 1)
    if site['s'] == 'SYN-STA-1':
        return round(page.wave(220, 18, i), 1)      # a load node with no registered capacity
    if site['s'] == 'SYN-CALACA-1':
        return round(page.wave(300 * 0.75, 30, i), 1)
    return page.node_mw(site, i)


def nodes():
    axis = page.times()
    rows = sites()
    return {'t': axis, 'sites': [s['s'] for s in rows],
            'lmp': [[node_lmp(s, i) for s in rows] for i in range(page.INTERVALS)],
            'mw': [[node_mw(s, i) for s in rows] for i in range(page.INTERVALS)]}


def geojson():
    """The page fixture's boxes with the country's west edge moved east of the placeholder
    matrix's anchor (PENDING_ORIGIN = 113.2, 20.6 in src/grid/map.js). Every box sits on land
    that starts at 114.5 E, so a pending cell drawn anywhere west of it is provably off land."""
    def box(kind, west, south, east, north):
        ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
        return {'type': 'Feature', 'properties': {'kind': kind},
                'geometry': {'type': 'Polygon', 'coordinates': [ring]}}
    return {'type': 'FeatureCollection', 'features': [
        box('country', 114.5, 4.4, 127.2, 21.2),
        box('province', 119.5, 13.0, 122.5, 18.5),
        box('province', 122.6, 9.5, 125.6, 12.5),
        box('province', 123.0, 5.5, 126.5, 9.0),
    ]}


def files():
    return {'regions.json': page.regions(), 'hvdc.json': hvdc(), NODES_NAME: nodes(),
            'advisories.json': advisories(), 'sites.json': sites(),
            'events.json': [dict(e) for e in page.EVENTS],
            'ph.geojson': geojson()}


def dump(obj):
    """The page fixture's own writing style: compact JSON, no trailing newline."""
    return json.dumps(obj, separators=(',', ':'))


def build(target):
    target.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, obj in files().items():
        written[name] = dump(obj)
        (target / name).write_text(written[name], encoding='utf-8')
    return written


def check(target):
    expected = {name: dump(obj) for name, obj in files().items()}
    problems = []
    for name, text in expected.items():
        path = target / name
        if not path.is_file():
            problems.append(f'missing {name}')
        elif path.read_text(encoding='utf-8') != text:
            problems.append(f'{name} differs from the formulas')
    extra = sorted(p.name for p in target.glob('*') if p.is_file() and p.name not in expected)
    problems += [f'unexpected {name}' for name in extra]
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('target', nargs='?', type=Path, default=HERE / 'data')
    parser.add_argument('--check', action='store_true')
    options = parser.parse_args(argv)
    if options.check:
        problems = check(options.target)
        print('\n'.join(problems) if problems else f'OK: {len(files())} fixture files reproduce')
        return 1 if problems else 0
    for name, size in sorted((n, len(t)) for n, t in build(options.target).items()):
        print(f'{name} {size}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
