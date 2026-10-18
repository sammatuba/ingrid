"""ATG-6: the map canvas — its transform, its hit testing, its layers and its fallback.

The module `src/grid/map.js` is a browser script (a canvas 2D element, pointer events, an HTML
overlay), so most of it cannot run on this interpreter. What is proven here, in the order the
task's acceptance names it:

1. **The transform and hit-testing math as pure functions.** The constants are read out of
   `src/grid/map.js` itself (a changed bound, pad, zoom factor or stop is caught here), the
   formulas are re-derived in Python exactly as the module documents them, and the properties
   the acceptance asks for are asserted on the fixture's own sites: zoom in, zoom out and fit
   each change the transform, and a click on a drawn site resolves to that site after every one
   of them, after a pan and after a wheel zoom. `Harness` then compares that re-derivation with
   the module's own `GridMap.math` output, number by number — the two implementations must
   agree, so neither the Python copy nor the JavaScript can drift alone.
2. **Every layer reads only baked data.** The source carries no fetch, no XHR, no import and no
   storage; the node harness runs the module with a `fetch` that throws, and the report shows it
   was never called. Every figure the drawing shows is derived here from the fixture files.
3. **An unlocated site is never drawn at a coordinate.** The fixture's placeholders carry null
   coordinates; the module's drawn set and its located-site hit test skip a placeholder outright,
   and nothing on the canvas stands for one (PP-B5: the matrix in open sea is gone). The
   snapshot carries each as a `pending` row with its price and colour and no position, which
   the page lists apart; the harness reports the same from the module's own numbers.
4. **The fallback.** With a canvas that has no `getContext` the module builds the text surface;
   the harness runs that path and the same figures are checked in its lines.
5. **The unknown state stays unknown** (the rework after the designated review). A congestion
   the record does not state — a null cell, a shorter or absent flag list, an interval the
   link's axis does not carry — is `null`, never a coerced `false`; the tooltip, the canvas
   label and the fallback say `congestion unknown` rather than "not congested". The two-finger
   zoom anchors on the pair's *previous* midpoint, so the world point under the fingers lands
   under the new midpoint; the reviewed rule (zoom at the new midpoint, then translate) left it
   at (337.5, 300) in the review's own case and is asserted here to be gone.
6. **The drag re-anchors when the fingers change** (the rework after the second review round).
   A second pointer makes the gesture a pinch that is never a click, and when a pinch loses a
   finger the survivor's drag starts where that finger is now, so its next move pans by its own
   travel; the reviewed defect panned by the distance back to where the pinch was last measured
   (51 px for 1 px in the review's own sequence) and is re-derived, reproduced and asserted
   gone here.

The node harness (`tests/fixtures/grid/map/harness.mjs`) executes the module under a small DOM
and a recording canvas-2D context. It is skipped, with its reason, on an interpreter without
node; the Python re-derivation above runs either way.

The fixture (`tests/fixtures/grid/map/`) is synthetic and deterministic, built by its own
`build.py` from the page fixture's formulas; `Fixture` runs that `build.py --check`, so the
committed bytes cannot drift from their definition.
"""
import json
import math
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / 'src' / 'grid'
FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'map'
DATA = FIXTURE / 'data'
NODE = shutil.which('node')

MAP_JS = (GRID / 'map.js').read_text(encoding='utf-8')
MAP_CSS = (GRID / 'map.css').read_text(encoding='utf-8')

# --------------------------------------------------------------------------- the module's own constants
# Every number below is read out of src/grid/map.js and asserted equal to the pinned value, so
# this file cannot silently test its own copy of the design: a bound, pad, zoom factor or stop
# that moves in the module and not here — or here and not in the module — fails at once.


def js(pattern, cast=float, text=MAP_JS):
    found = re.search(pattern, text)
    assert found, f'the module does not state {pattern}'
    return cast(found.group(1))


BOUNDS = {
    'w': js(r'const BOUNDS = \{ w: ([\d.]+)', float),
    'e': js(r'const BOUNDS = \{ w: [\d.]+, e: ([\d.]+)', float),
    's': js(r'e: [\d.]+, s: ([\d.]+)', float),
    'n': js(r's: [\d.]+, n: ([\d.]+)', float),
}
COSLAT = js(r'const COSLAT = Math\.cos\(\(([\d.]+) \* Math\.PI\) / 180\)')
COSLAT = math.cos(math.radians(COSLAT))
PAD = js(r'const PAD = ([\d.]+)')
KMAX_FACTOR = js(r'const KMAX_FACTOR = ([\d.]+)')
WHEEL_SCALE = js(r'const WHEEL_SCALE = ([\d.]+)')
BUTTON_FACTOR = js(r'const BUTTON_FACTOR = ([\d.]+)')
DRAG_CLICK_PX = js(r'const DRAG_CLICK_PX = ([\d.]+)')
HIT_SLOP = js(r'const HIT_SLOP = ([\d.]+)')
LINK_HIT = js(r'const LINK_HIT = ([\d.]+)')
LINK_SAMPLES = js(r'const LINK_SAMPLES = ([\d.]+)', int)
# PP-B5: Fit frames the archipelago itself (FIT, the outline's own extent); BOUNDS stays the
# plane's origin. The matrix of unlocated sites in open sea is gone with the sea it needed.
FIT = {
    'w': js(r'const FIT = \{ w: ([\d.]+)', float),
    'e': js(r'const FIT = \{ w: [\d.]+, e: ([\d.]+)', float),
    's': js(r'const FIT = \{ w: [\d.]+, e: [\d.]+, s: ([\d.]+)', float),
    'n': js(r'const FIT = \{ w: [\d.]+, e: [\d.]+, s: [\d.]+, n: ([\d.]+)', float),
}
MSG_WINDOW_MIN = js(r'const MSG_WINDOW_MIN = ([\d.]+)', int)
EVENT_WINDOW_MIN = js(r'const EVENT_WINDOW_MIN = ([\d.]+)', int)
LOAD_RADIUS = js(r'const LOAD_RADIUS = ([\d.]+)')
# UX-3: the price scale is data-adaptive. Its knots are these quantiles of the drawn prices at
# the clock, clamped to [PRICE_FLOOR, PRICE_CEIL]; its five colours are the theme's --p0 to --p4,
# with the dark theme's values as the module's own fallback.
SCALE_Q = [float(v) for v in js(r'const SCALE_Q = \[([\d., ]+)\]', str).split(',')]
PRICE_FLOOR = js(r'const PRICE_FLOOR = ([\d.]+)')
PRICE_CEIL = js(r'const PRICE_CEIL = ([\d.]+)')
MIN_SPAN = js(r'const MIN_SPAN = ([\d.]+)')
P_DARK = re.findall(r"'(#[0-9a-f]{6})'", js(r"const P_DARK = \[([^\]]+)\]", str))
CLUSTER_PX = js(r'const CLUSTER_PX = ([\d.]+)')
SHELL_CSS = (GRID / 'shell.css').read_text(encoding='utf-8')
SHELL_DARK_P = re.findall(r'--p\d: (#[0-9a-f]{6});', SHELL_CSS[SHELL_CSS.index(':root[data-theme], :root[data-theme="dark"]'):SHELL_CSS.index(':root[data-theme="light"]')])
UNKNOWN_FILL = re.search(r"const UNKNOWN_FILL = '(#[0-9a-f]{6})'", MAP_JS).group(1)
PRICES_OFF_FILL = re.search(r"const PRICES_OFF_FILL = '(#[0-9a-f]{6})'", MAP_JS).group(1)
LINK_DEFS = {
    'VISLUZ1': {'a': (124.61, 11.01), 'b': (123.18, 13.62)},
    'MINVIS1': {'a': (123.75, 7.97), 'b': (123.48, 10.05)},
}

# The pinned design values (research §3.2 and §3.5). Reading them out is not enough: the design
# is what the evidence fixed, so a change here is a change to the design and is rejected.
PINNED = {'BOUNDS': BOUNDS == {'w': 112.9, 'e': 127.2, 's': 4.4, 'n': 21.2},
          'PAD': PAD == 14, 'KMAX_FACTOR': KMAX_FACTOR == 64, 'WHEEL_SCALE': WHEEL_SCALE == 480,
          'BUTTON_FACTOR': BUTTON_FACTOR == 1.25, 'DRAG_CLICK_PX': DRAG_CLICK_PX == 3,
          'HIT_SLOP': HIT_SLOP == 4, 'LINK_HIT': LINK_HIT == 6, 'LINK_SAMPLES': LINK_SAMPLES == 32,
          'FIT': FIT == {'w': 116.9, 'e': 126.7, 's': 4.6, 'n': 21.2},
          'MSG_WINDOW_MIN': MSG_WINDOW_MIN == 60, 'EVENT_WINDOW_MIN': EVENT_WINDOW_MIN == 90,
          'SCALE_Q': SCALE_Q == [0.05, 0.25, 0.5, 0.75, 0.95], 'PRICE_FLOOR': PRICE_FLOOR == 0,
          'PRICE_CEIL': PRICE_CEIL == 32000, 'MIN_SPAN': MIN_SPAN == 200, 'CLUSTER_PX': CLUSTER_PX == 9,
          # the fallback colours are the shell's own dark tokens, so the canvas and the page agree
          'P_DARK': P_DARK == SHELL_DARK_P and len(P_DARK) == 5,
          'COSLAT': abs(COSLAT - math.cos(math.radians(12.5))) < 1e-12}

# --------------------------------------------------------------------------- the formulas, re-derived
# The same arithmetic the module documents (its header, §math), written again in Python from
# the constants above. `Harness` compares the two implementations; these functions carry the
# acceptance in the environment where node is absent.

SPAN_X = (BOUNDS['e'] - BOUNDS['w']) * COSLAT
SPAN_Y = BOUNDS['n'] - BOUNDS['s']


def plane(lon, lat):
    return ((lon - BOUNDS['w']) * COSLAT, BOUNDS['n'] - lat)


FIT_NW = ((FIT['w'] - BOUNDS['w']) * COSLAT, BOUNDS['n'] - FIT['n'])
FIT_SE = ((FIT['e'] - BOUNDS['w']) * COSLAT, BOUNDS['n'] - FIT['s'])
FIT_X, FIT_Y = FIT_SE[0] - FIT_NW[0], FIT_SE[1] - FIT_NW[1]


def fit_transform(w, h):
    """The module's §fitTransform, re-derived: the archipelago (FIT) inside the padding, its
    centre under the canvas centre."""
    k = min(max(1e-6, w - 2 * PAD) / FIT_X, max(1e-6, h - 2 * PAD) / FIT_Y)
    return {'k': k, 'fx': FIT_NW[0] + FIT_X / 2, 'fy': FIT_NW[1] + FIT_Y / 2, 'w': w, 'h': h}


def to_screen(t, p):
    return (t['w'] / 2 + t['k'] * (p[0] - t['fx']), t['h'] / 2 + t['k'] * (p[1] - t['fy']))


def world_of(t, sx, sy):
    return (t['fx'] + (sx - t['w'] / 2) / t['k'], t['fy'] + (sy - t['h'] / 2) / t['k'])


def zoom_at(t, factor, sx, sy):
    w = world_of(t, sx, sy)
    fit_k = fit_transform(t['w'], t['h'])['k']
    k = min(max(t['k'] * factor, fit_k), KMAX_FACTOR * fit_k)
    return {'k': k, 'fx': w[0] - (sx - t['w'] / 2) / k, 'fy': w[1] - (sy - t['h'] / 2) / k,
            'w': t['w'], 'h': t['h']}


def pan_by(t, dx, dy):
    return {'k': t['k'], 'fx': t['fx'] - dx / t['k'], 'fy': t['fy'] - dy / t['k'], 'w': t['w'], 'h': t['h']}


def pinch_transform(t, prev, nxt):
    """The module's §pinchTransform, re-derived: zoom about the pair's *previous* midpoint (that
    point does not move under its own zoom), then pan by the midpoint's own travel, so the world
    point that was under the fingers lands under the new midpoint."""
    factor = nxt['d'] / prev['d'] if prev['d'] > 0 else 1
    return pan_by(zoom_at(t, factor, prev['mid'][0], prev['mid'][1]),
                  nxt['mid'][0] - prev['mid'][0], nxt['mid'][1] - prev['mid'][1])


def drag_down(prev, p, count):
    """The module's §dragDown, re-derived: a pointer landing re-anchors the drag on itself. Two
    pointers are a gesture, never a click, so `moved` stands at the threshold from the moment
    the second pointer lands; a lone pointer starts at whatever the previous drag had moved."""
    moved = prev['moved'] if prev else 0
    return {'x': p[0], 'y': p[1],
            'moved': max(moved, DRAG_CLICK_PX) if count >= 2 else moved,
            'last': {'x': p[0], 'y': p[1]}}


def drag_up(prev, survivor):
    """The module's §dragUp, re-derived: with no pointer left the drag ends; with one left the
    drag re-anchors on that survivor where it is now, so its next move pans by its own travel
    rather than by the distance back to where the pinch was last measured."""
    if not prev or not survivor:
        return None
    return {'x': survivor[0], 'y': survivor[1], 'moved': max(prev['moved'], DRAG_CLICK_PX),
            'last': {'x': survivor[0], 'y': survivor[1]}}


def flow_at(link, ri):
    """The module's §flowAt, re-derived: the flow the record states, else None."""
    if link is None or ri is None or not link.get('flow') or ri >= len(link['flow']):
        return None
    return None if link['flow'][ri] is None else link['flow'][ri]


def congestion_at(link, ri):
    """The module's §congestionAt, re-derived: True/False are the record's states, None is its
    silence — a null cell, a shorter or absent flag list, an interval the axis does not name."""
    if link is None or ri is None or not link.get('congested') or ri >= len(link['congested']):
        return None
    return None if link['congested'][ri] is None else bool(link['congested'][ri])


def radius_of(site):
    if site['k'] == 'NL':
        return LOAD_RADIUS
    return min(7, 2 + (site['cap'] or 1) ** 0.5 / 6)


def _to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklab(hexs):
    """The module's §oklab, re-derived: sRGB hex to OKLab (Björn Ottosson's matrices)."""
    r, g, b = (_to_linear(int(hexs[i:i + 2], 16) / 255) for i in (1, 3, 5))
    l = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s_,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s_,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s_)


def from_oklab(lab):
    big_l, a, b = lab
    l = (big_l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (big_l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (big_l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s_,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s_,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s_)
    clamp = lambda x: max(0.0, min(1.0, x))
    return '#' + ''.join('%02x' % int(math.floor(clamp(_to_gamma(clamp(c))) * 255 + 0.5)) for c in rgb)


def mix_oklab(a, b, t):
    pa, pb = oklab(a), oklab(b)
    return from_oklab(tuple(pa[i] + (pb[i] - pa[i]) * t for i in range(3)))


def quantile(ordered, p):
    """Linear between ranks (type 7), as the module's §quantile."""
    if not ordered:
        return None
    h = (len(ordered) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (h - lo)


def price_scale(values, colours=None):
    """The module's §priceScale, re-derived: five knots at SCALE_Q of the drawn prices, clamped
    to [PRICE_FLOOR, PRICE_CEIL], a spread under MIN_SPAN widened about its median, then made
    strictly increasing and held under the ceiling."""
    v = sorted(float(x) for x in values if x is not None)
    if not v:
        return None
    cut = lambda x: max(PRICE_FLOOR, min(PRICE_CEIL, x))
    knots = [cut(quantile(v, p)) for p in SCALE_Q]
    if knots[4] - knots[0] < MIN_SPAN:
        m, step = knots[2], MIN_SPAN / 4
        knots = [cut(x) for x in (m - 2 * step, m - step, m, m + step, m + 2 * step)]
    for i in range(1, 5):
        if knots[i] <= knots[i - 1]:
            knots[i] = knots[i - 1] + 1
    if knots[4] > PRICE_CEIL:
        knots[4] = PRICE_CEIL
        for i in range(3, -1, -1):
            if knots[i] >= knots[i + 1]:
                knots[i] = knots[i + 1] - 1
    return {'knots': knots, 'colours': list(colours or P_DARK), 'median': quantile(v, 0.5), 'n': len(v),
            'atCeil': sum(1 for x in v if x >= PRICE_CEIL)}


def color_at(scale, v):
    """The colour of one price: the end colours past the end knots, OKLab between two knots."""
    if v is None or scale is None:
        return UNKNOWN_FILL
    k, c = scale['knots'], scale['colours']
    if v <= k[0]:
        return mix_oklab(c[0], c[0], 0)
    if v >= k[4]:
        return mix_oklab(c[4], c[4], 0)
    i = 0
    while i < 3 and v > k[i + 1]:
        i += 1
    return mix_oklab(c[i], c[i + 1], (v - k[i]) / (k[i + 1] - k[i]))


def ramp_gradient(scale):
    c = scale['colours'] if scale else P_DARK
    stops = []
    for j in range(17):
        pos = j / 16
        seg = min(3, math.floor(pos * 4))
        stops.append(f'{mix_oklab(c[seg], c[seg + 1], pos * 4 - seg)} {pos * 100:.2f}%')
    return 'linear-gradient(90deg, ' + ', '.join(stops) + ')'


def tick_label(value):
    """The module's §tickLabel, re-derived: a knot as a plain number, and a knot at the ceiling
    with a `+`. The node series is uncapped (research §2.4c: it reaches ₱753,290 on the real
    bake), so the label names what happens above it rather than calling it a cap."""
    return '{:,}'.format(int(math.floor(value + 0.5))) + ('+' if value >= PRICE_CEIL else '')


def colour_close(a, b, tolerance=1):
    """Two hex colours equal to within one step per channel (the pow and cube roots of two
    runtimes may round a channel differently at the half)."""
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= tolerance for i in (1, 3, 5))


def cluster_radius(members):
    if len(members) == 1:
        return radius_of(members[0])
    gen = sum((s['cap'] or 0) for s in members if s['k'] != 'NL')
    biggest = max(radius_of(s) for s in members)
    r = min(13, 2.5 + math.sqrt(gen) / 6) if gen > 0 else min(4.5, LOAD_RADIUS + 0.7 * (len(members) - 1))
    return max(r, biggest + 1)


def is_approx(site):
    return site['p'] == 'approximate' and site['lon'] is not None


def place_marks(members):
    """The module's §placeMarks: the located sites' disc and the approximate sites' dashed ring."""
    core = [m for m in members if not is_approx(m)]
    approx = [m for m in members if is_approx(m)]
    core_r = cluster_radius(core) if core else 0
    ring = 0 if not approx else max(cluster_radius(approx), core_r + 2.5) if core else max(3, cluster_radius(approx))
    return {'core': core_r, 'ring': ring, 'r': max(core_r, ring), 'approx': len(approx)}


def cluster_sites(t, sites):
    """The module's §clusterSites, re-derived: drawn sites, the located ones first, then the
    largest registered MW (then code), each joining the first place whose anchor is within
    CLUSTER_PX on screen. An approximate site only joins a place or starts its own."""
    order = sorted((s for s in sites if s['p'] != 'placeholder' and s['lon'] is not None),
                   key=lambda s: (is_approx(s), -(s['cap'] or 0), s['s']))
    places = []
    for site in order:
        x, y = to_screen(t, plane(site['lon'], site['lat']))
        hit = next((p for p in places if (p['ax'] - x) ** 2 + (p['ay'] - y) ** 2 <= CLUSTER_PX ** 2), None)
        if hit:
            hit['members'].append(site)
        else:
            places.append({'ax': x, 'ay': y, 'members': [site]})
    return [dict(place_marks(p['members']), codes=[m['s'] for m in p['members']]) for p in places]


def order_stack(hits):
    return sorted(hits, key=lambda h: (-h['r'], h['code']))


def site_at(t, sites, sx, sy):
    out = []
    for site in sites:
        if site['p'] == 'placeholder' or site['lon'] is None or site['lat'] is None:
            continue
        px, py = to_screen(t, plane(site['lon'], site['lat']))
        r = radius_of(site)
        if (px - sx) ** 2 + (py - sy) ** 2 <= (r + HIT_SLOP) ** 2:
            out.append({'code': site['s'], 'site': site, 'x': px, 'y': py, 'r': r})
    return order_stack(out)


def curve_point(p1, c, p2, t):
    a, b, cc = (1 - t) ** 2, 2 * (1 - t) * t, t * t
    return (a * p1[0] + b * c[0] + cc * p2[0], a * p1[1] + b * c[1] + cc * p2[1])


def link_curve(defn):
    p1, p2 = plane(*defn['a']), plane(*defn['b'])
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return p1, ((p1[0] + p2[0]) / 2 + dy * 0.18, (p1[1] + p2[1]) / 2 - dx * 0.18), p2


def link_at(t, sx, sy):
    best = None
    for name, defn in LINK_DEFS.items():
        p1, c, p2 = link_curve(defn)
        prev = to_screen(t, curve_point(p1, c, p2, 0))
        for i in range(1, LINK_SAMPLES + 1):
            point = to_screen(t, curve_point(p1, c, p2, i / LINK_SAMPLES))
            dx, dy = point[0] - prev[0], point[1] - prev[1]
            span = dx * dx + dy * dy
            frac = min(1, max(0, ((sx - prev[0]) * dx + (sy - prev[1]) * dy) / span)) if span else 0
            near = ((prev[0] + frac * dx), (prev[1] + frac * dy))
            distance = ((sx - near[0]) ** 2 + (sy - near[1]) ** 2) ** 0.5
            if distance <= LINK_HIT and (best is None or distance < best[0]):
                best = (distance, name, i / LINK_SAMPLES)
            prev = point
    return best


# --------------------------------------------------------------------------- the fixture

def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


SITES = load('sites.json')
NODES = load('nodes-2026-09-21.json')
HVDC = load('hvdc.json')
ADVISORIES = load('advisories.json')
EVENTS = load('events.json')
GEO = load('ph.geojson')
CLOCK = '2026-09-21 13:40:00'
LOOK = {'w': 1280, 'h': 700}
PHONE = {'w': 390, 'h': 585}
FITTED = fit_transform(**LOOK)
LOCATED = [s for s in SITES if s['p'] != 'placeholder']
PLACEHOLDERS = [s for s in SITES if s['p'] == 'placeholder']
STACKED = (123.42, 10.90)         # SYN-BAY-1, SYN-BAY-3 and SYN-STA-1 share this position


def node_index():
    return {'site': {code: i for i, code in enumerate(NODES['sites'])},
            'row': {t: i for i, t in enumerate(NODES['t'])}}


def value_of(site, stamp=CLOCK):
    idx = node_index()
    if stamp not in idx['row'] or site['s'] not in idx['site']:
        return None
    return NODES['lmp'][idx['row'][stamp]][idx['site'][site['s']]]


def drawn_value_at_clock(sites):
    return [v for v in (value_of(s) for s in sites) if v is not None]


# --------------------------------------------------------------------------- the module's source


class Source(unittest.TestCase):
    """What the module is, read off the file: self-contained, no request, the right surface."""

    def test_the_module_is_one_iife_with_mount_and_math_and_no_library(self):
        self.assertIn('GridMap.mount', MAP_JS)
        self.assertIn('const GridMap = { mount, math,', MAP_JS)
        self.assertIn('function mount(container, data, callbacks)', MAP_JS)
        for added in ('fetch(', 'XMLHttpRequest', 'import(', 'require(', 'WebSocket', 'EventSource',
                      'localStorage', 'sessionStorage', 'document.write'):
            self.assertNotIn(added, MAP_JS, added)

    def test_every_callback_is_the_one_the_detail_panel_opens_by(self):
        # grid.js's explorable layer resolves the map's clicks with `selectSite(code)` and
        # `selectLink(id)` (grid.js:952-960); ATG-8 passes those two, so the module must call
        # exactly these names and nothing of its own.
        self.assertIn('callbacks.onSite', MAP_JS)
        self.assertIn('callbacks.onLink', MAP_JS)
        harness = (FIXTURE / 'harness.mjs').read_text(encoding='utf-8')
        for needle in ('onSite:', 'onLink:'):
            self.assertIn(needle, harness, needle)
        # the module never reaches into grid.js: it calls the callbacks and nothing else
        self.assertNotIn('GridDesk', MAP_JS)
        self.assertNotIn('selectSite(', MAP_JS)
        self.assertNotIn('selectLink(', MAP_JS)

    def test_the_surface_the_record_promises_is_exposed(self):
        for needle in ('setClock, setScope, fit, zoomIn, zoomOut, panBy: panByScreen, resize: draw',
                       'transform, hitTest: hitTestAt, snapshot: () => snapshot, legend: () => legendText',
                       # ATG-8 rework: the node file's layer is handed to the mounted canvas
                       # (`setNodes`), so the page never remounts it and the reader's layers,
                       # scope, transform and open tooltip stay.
                       'function setNodes(nodes)', 'setNodes, destroy, canvas, root, fallback',
                       'destroy, canvas, root, fallback', 'unplacedSites(data.sites, state.scope)', 'rampGradient(scale)',
                       # UX-3: the page reads the scale (its state-card dots) and tells the map
                       # what its overlays cover
                       'scale: () => scale, priceColor: (v) =>', 'function setInsets(i)'):
            self.assertIn(needle, MAP_JS, needle)

    def test_the_placeholder_rule_is_in_the_code_not_only_in_the_data(self):
        # a located hit never returns a placeholder, at any transform: the guard is in siteAt
        self.assertIn("if (site.p === 'placeholder' || site.lon == null || site.lat == null) continue;", MAP_JS)
        # a placeholder has no drawn position, so nothing (a ring, a glyph) is placed at one
        self.assertIn("if (!drawnSet.has(site.s) || site.p === 'placeholder') return null;", MAP_JS)
        # a notice that names a site with no position stands at its grid
        self.assertIn('out.grid.push({ a, severity: sev, grid: g, unplaced: named.site,', MAP_JS)

    def test_one_scale_draws_the_dots_and_the_ramp(self):
        # UX-3: one scale object per draw. The ramp's stops are the same OKLab mix colorAt uses,
        # and the legend's ramp and ticks are read off that object, never a second list in CSS.
        self.assertIn('ramp.style.background = rampGradient(scale);', MAP_JS)
        self.assertIn('ramp.style.background = text.ramp;', MAP_JS)
        self.assertIn('stops.push(`${mixOklab(c[seg], c[seg + 1], pos * 4 - seg)}', MAP_JS)
        self.assertIn('return mixOklab(c[i], c[i + 1], (value - k[i]) / (k[i + 1] - k[i]));', MAP_JS)
        self.assertIn('scale = priced && values.length ? priceScale(values, C.p) : null;', MAP_JS)
        self.assertNotIn('linear-gradient(90deg, var(--p0)', MAP_CSS)
        # no fixed stops survive: the old 0 to 32,000 list drew Luzon one colour
        self.assertIsNone(re.search(r"\[\d+, '#[0-9a-f]{6}'\]", MAP_JS))

    def test_the_stylesheet_wraps_the_chips_and_fills_the_width(self):
        self.assertIn('flex-wrap: wrap', MAP_CSS)
        self.assertIn('width: 100%', MAP_CSS)
        self.assertIn('@media (max-width: 760px)', MAP_CSS)
        self.assertIn('.gmap-canvas', MAP_CSS)
        self.assertIn('touch-action: none', MAP_CSS)
        self.assertIn('.gmap-tip', MAP_CSS)
        self.assertIn('.gmap-fallback', MAP_CSS)


# --------------------------------------------------------------------------- the transform


class TransformMath(unittest.TestCase):
    """Acceptance 1, first half: zoom in, out, fit and pinch each change the transform."""

    def test_the_pinned_design_values_are_what_the_module_states(self):
        for name, ok in PINNED.items():
            self.assertTrue(ok, f'{name} moved: the design record fixes it (research §3.2, §3.5)')

    def test_fit_places_the_whole_archipelago_inside_the_padding_at_both_widths(self):
        for box in (LOOK, PHONE):
            t = fit_transform(**box)
            for lon, lat in ((FIT['w'], FIT['n']), (FIT['e'], FIT['s']),
                             (FIT['w'], FIT['s']), (FIT['e'], FIT['n'])):
                x, y = to_screen(t, plane(lon, lat))
                self.assertGreaterEqual(x, PAD - 1e-9, (box, lon, lat))
                self.assertLessEqual(x, box['w'] - PAD + 1e-9, (box, lon, lat))
                self.assertGreaterEqual(y, PAD - 1e-9, (box, lon, lat))
                self.assertLessEqual(y, box['h'] - PAD + 1e-9, (box, lon, lat))
            # the archipelago's centre stands at the canvas centre: equal sea on both sides
            cx, cy = to_screen(t, plane((FIT['w'] + FIT['e']) / 2, (FIT['n'] + FIT['s']) / 2))
            self.assertAlmostEqual(cx, box['w'] / 2, places=9)
            self.assertAlmostEqual(cy, box['h'] / 2, places=9)
            self.assertEqual(t['w'], box['w'])

    def test_the_fit_box_holds_the_real_outline_with_a_hair_of_sea(self):
        # the real outline runs 116.955 to 126.618 E and 4.656 to 21.122 N (the showcase and the
        # company bake share it); the fit box holds it with at most 0.15 degrees to spare
        for edge, real in (('w', 116.955), ('e', 126.618), ('s', 4.656), ('n', 21.122)):
            self.assertLessEqual(abs(FIT[edge] - real), 0.15, edge)
        self.assertLess(FIT['w'], 116.955)
        self.assertGreater(FIT['e'], 126.618)
        self.assertLess(FIT['s'], 4.656)
        self.assertGreater(FIT['n'], 21.122)

    def test_fit_is_the_usual_arithmetic_at_the_two_widths_the_page_uses(self):
        # PP-B5: Fit frames the archipelago (FIT), not the plane with its sea for the old matrix.
        # A 1280x700 box is height-bound: (700 - 28) / 16.6 degrees = 40.48 px per plane unit.
        # A 390x585 box is height-bound too: (585 - 28) / 16.6 = 33.55 px.
        self.assertAlmostEqual(fit_transform(1280, 700)['k'], 672 / 16.6, places=9)
        self.assertAlmostEqual(fit_transform(390, 585)["k"], 557 / 16.6, places=8)

    def test_zoom_in_changes_k_by_the_button_factor_and_zoom_out_returns(self):
        t = fit_transform(**LOOK)
        inside = zoom_at(t, BUTTON_FACTOR, LOOK['w'] / 2, LOOK['h'] / 2)
        self.assertGreater(inside['k'], t['k'])
        self.assertAlmostEqual(inside['k'] / t['k'], BUTTON_FACTOR, places=12)
        # anchored at the centre: the centre's world point does not move
        self.assertEqual(world_of(t, LOOK['w'] / 2, LOOK['h'] / 2), world_of(inside, LOOK['w'] / 2, LOOK['h'] / 2))
        back = zoom_at(inside, 1 / BUTTON_FACTOR, LOOK['w'] / 2, LOOK['h'] / 2)
        self.assertAlmostEqual(back['k'], t['k'], places=9)
        self.assertAlmostEqual(back['fx'], t['fx'], places=9)
        self.assertAlmostEqual(back['fy'], t['fy'], places=9)

    def test_fit_resets_the_transform_after_a_zoom_and_a_pan(self):
        t = fit_transform(**LOOK)
        moved = pan_by(zoom_at(zoom_at(t, 4, 300, 400), BUTTON_FACTOR, 50, 50), 120, -80)
        self.assertNotEqual((moved['k'], moved['fx'], moved['fy']), (t['k'], t['fx'], t['fy']))
        again = fit_transform(moved['w'], moved['h'])
        self.assertEqual((again['k'], again['fx'], again['fy']), (t['k'], t['fx'], t['fy']))

    def test_a_zoom_keeps_the_world_point_under_the_pointer(self):
        t = fit_transform(**LOOK)
        for factor, sx, sy in ((1.25, 100, 80), (4.0, 900, 640), (0.5, 640, 350),
                               (1 / BUTTON_FACTOR, 3, 699)):
            before = world_of(t, sx, sy)
            after = world_of(zoom_at(t, factor, sx, sy), sx, sy)
            self.assertAlmostEqual(before[0], after[0], places=9, msg=(factor, sx, sy))
            self.assertAlmostEqual(before[1], after[1], places=9, msg=(factor, sx, sy))

    def test_the_clamps_hold_and_the_anchor_survives_the_clamp(self):
        t = fit_transform(**LOOK)
        fit_k = t['k']
        big = t
        for _ in range(20):
            big = zoom_at(big, 8, 640, 350)
        self.assertAlmostEqual(big['k'], KMAX_FACTOR * fit_k, places=9)
        small = big
        for _ in range(20):
            small = zoom_at(small, 0.5, 640, 350)
        self.assertAlmostEqual(small['k'], fit_k, places=9)
        # even when the clamp bites, the world point under the pointer is the same
        clamped = zoom_at(zoom_at(t, 1e6, 200, 200), 2, 200, 200)
        self.assertAlmostEqual(clamped['k'], KMAX_FACTOR * fit_k, places=9)
        self.assertAlmostEqual(world_of(clamped, 200, 200)[0], world_of(t, 200, 200)[0], places=9)

    def test_pan_translates_by_exactly_the_drag_and_keeps_k(self):
        t = fit_transform(**LOOK)
        for dx, dy in ((30, 20), (-140, 60), (0, 0)):
            moved = pan_by(t, dx, dy)
            self.assertEqual(moved['k'], t['k'])
            point = plane(121.0, 14.6)
            x, y = to_screen(t, point)
            mx, my = to_screen(moved, point)
            self.assertAlmostEqual(mx - x, dx, places=9)
            self.assertAlmostEqual(my - y, dy, places=9)

    def test_the_wheel_factor_is_per_event_and_clamped_per_event(self):
        # k *= 2 ** (-deltaY / 480), the research's §3.2 rule; two events compose, one event
        # at the ceiling does not accumulate past it.
        t = fit_transform(**LOOK)
        one = zoom_at(t, 2 ** (240 / WHEEL_SCALE), 640, 350)
        self.assertAlmostEqual(one['k'], t['k'] * 2 ** 0.5, places=9)
        two = zoom_at(one, 2 ** (240 / WHEEL_SCALE), 640, 350)
        self.assertAlmostEqual(two['k'], t['k'] * 2, places=9)
        ceiling = fit_transform(**LOOK)
        for _ in range(30):
            ceiling = zoom_at(ceiling, 16, 10, 10)
        self.assertAlmostEqual(ceiling['k'], KMAX_FACTOR * fit_transform(**LOOK)['k'], places=9)

    def test_a_pinch_anchors_on_the_previous_midpoint(self):
        """The world point under the pair's previous midpoint lands under the new midpoint."""
        t = fit_transform(**LOOK)
        for prev, nxt in (
                ({'d': 100.0, 'mid': (350.0, 300.0)}, {'d': 200.0, 'mid': (325.0, 300.0)}),
                ({'d': 100.0, 'mid': (900.0, 120.0)}, {'d': 100.0, 'mid': (820.0, 200.0)}),
                ({'d': 10.0, 'mid': (10.0, 10.0)}, {'d': 4000.0, 'mid': (1200.0, 690.0)}),
                ({'d': 0.0, 'mid': (100.0, 100.0)}, {'d': 50.0, 'mid': (100.0, 100.0)})):
            was = world_of(t, prev['mid'][0], prev['mid'][1])
            x, y = to_screen(pinch_transform(t, prev, nxt), was)
            self.assertAlmostEqual(x, nxt['mid'][0], places=6, msg=(prev, nxt))
            self.assertAlmostEqual(y, nxt['mid'][1], places=6, msg=(prev, nxt))

    def test_the_reviewed_zoom_at_the_new_midpoint_rule_is_the_drift_this_fix_removes(self):
        # the reviewed commit zoomed at the *new* midpoint and only then translated: in the
        # review's own case ((350,300) to (325,300) at 1.5x) it left the previous midpoint's
        # world point at (337.5, 300) — 12.5 px off the fingers. The fixed rule (the zoom about
        # the previous midpoint, then the travel as a pan) puts it back under the new midpoint,
        # and the module states that rule as `pinchTransform`.
        t = fit_transform(**LOOK)
        prev, nxt = (350.0, 300.0), (325.0, 300.0)
        was = world_of(t, prev[0], prev[1])
        reviewed = pan_by(zoom_at(t, 1.5, nxt[0], nxt[1]), nxt[0] - prev[0], nxt[1] - prev[1])
        x, y = to_screen(reviewed, was)
        self.assertAlmostEqual(x, 337.5, places=6)
        self.assertAlmostEqual(y, 300.0, places=6)
        fixed = pinch_transform(t, {'d': 100.0, 'mid': prev}, {'d': 150.0, 'mid': nxt})
        x, y = to_screen(fixed, was)
        self.assertAlmostEqual(x, nxt[0], places=6)
        self.assertAlmostEqual(y, nxt[1], places=6)
        self.assertIn('function pinchTransform(T, prev, next) {', MAP_JS)
        # the gesture itself goes through the anchored rule, not a second formula in onMove
        self.assertIn('state.transform = pinchTransform(state.transform, state.pinch, pinch);', MAP_JS)

    def test_a_pinch_that_loses_a_finger_hands_the_drag_to_the_survivor(self):
        """The round-2 review's defect: the pinch never moved the drag's anchor, so the first
        move of the surviving finger panned by the distance back to where the pinch was last
        measured — 51 px of pan for 1 px of movement in the review's own sequence. The drag is
        now re-anchored on the survivor when the pair becomes one, and a two-pointer gesture is
        never a click whatever the fingers did."""
        t = fit_transform(**LOOK)
        # the review's sequence: down at (300,300), a second down at (400,300), the pair drawn
        # apart to (250,300)/(450,300), then the first finger lifts and the other moves 1 px
        drag = drag_down(drag_down(None, (300.0, 300.0), 1), (400.0, 300.0), 2)
        step = pinch_transform(t, {'d': 100.0, 'mid': (350.0, 300.0)}, {'d': 150.0, 'mid': (325.0, 300.0)})
        pinched = pinch_transform(step, {'d': 150.0, 'mid': (325.0, 300.0)}, {'d': 200.0, 'mid': (350.0, 300.0)})
        lifted = drag_up(drag, (450.0, 300.0))
        self.assertEqual({'x': 450.0, 'y': 300.0, 'moved': DRAG_CLICK_PX},
                         {'x': lifted['x'], 'y': lifted['y'], 'moved': lifted['moved']})
        # the survivor moves 1 px: the re-anchored drag pans by 1 px, the reviewed anchor by 51
        fixed = pan_by(pinched, 451.0 - lifted['last']['x'], 0)
        stale = pan_by(pinched, 451.0 - drag['last']['x'], 0)
        self.assertAlmostEqual(fixed['fx'] - pinched['fx'], -1 / pinched['k'], places=12)
        self.assertAlmostEqual(stale['fx'] - pinched['fx'], -51 / pinched['k'], places=12)
        self.assertEqual(fixed['k'], pinched['k'], 'a pan never changes k')
        # and the world point under the finger stays under the finger through the move
        before = world_of(pinched, 450.0, 300.0)
        after = world_of(fixed, 451.0, 300.0)
        self.assertAlmostEqual(before[0], after[0], places=12)
        self.assertAlmostEqual(before[1], after[1], places=12)
        # a pointer landing twice over: two pointers are a gesture, so `moved` is already at the
        # click threshold; a drag that had moved keeps its own count; a lone tap is still a click
        self.assertEqual(DRAG_CLICK_PX, drag_down(None, (10.0, 10.0), 2)['moved'])
        self.assertEqual(20.0, drag_down({'moved': 20.0, 'last': {'x': 0, 'y': 0}}, (10.0, 10.0), 2)['moved'])
        self.assertEqual(0, drag_down(None, (10.0, 10.0), 1)['moved'])
        self.assertIsNone(drag_up(drag, None), 'the last pointer lifting ends the drag')
        # the module states the rule and the handlers use it
        self.assertIn('function dragDown(prev, p, count) {', MAP_JS)
        self.assertIn('function dragUp(prev, survivor) {', MAP_JS)
        self.assertIn('state.drag = dragDown(state.drag, [p.x, p.y], state.pointers.size);', MAP_JS)
        self.assertIn('state.drag = dragUp(state.drag, restPointer());', MAP_JS)

    def test_a_resize_keeps_the_reader_and_scales_k_with_the_fit_ratio(self):
        t = zoom_at(fit_transform(**LOOK), 4, 640, 350)
        # the module's resize rule: focus stays, k follows the fit ratio
        w2, h2 = 390, 585
        ratio = fit_transform(w2, h2)['k'] / fit_transform(t['w'], t['h'])['k']
        resized = {'k': t['k'] * ratio, 'fx': t['fx'], 'fy': t['fy'], 'w': w2, 'h': h2}
        self.assertAlmostEqual(resized['k'] / fit_transform(w2, h2)['k'], 4, places=9)
        self.assertEqual(resized['fx'], t['fx'])
        # the module's resizeTransform does exactly this, then clamps
        self.assertIn('function resizeTransform(T, w, h) {', MAP_JS)
        self.assertIn('const ratio = fitTransform(w, h).k / fitK(T);', MAP_JS)


# --------------------------------------------------------------------------- hit testing


class HitTesting(unittest.TestCase):
    """Acceptance 1, second half: a click on a drawn site resolves to that site."""

    def transforms(self):
        t = fit_transform(**LOOK)
        wheeled = zoom_at(t, 2 ** (240 / WHEEL_SCALE), 640, 350)
        return {'fit': t, 'zoomIn': zoom_at(t, BUTTON_FACTOR, 640, 350),
                'zoomIn2': zoom_at(zoom_at(t, BUTTON_FACTOR, 640, 350), BUTTON_FACTOR, 640, 350),
                'zoomOut': zoom_at(zoom_at(t, BUTTON_FACTOR, 640, 350), 1 / BUTTON_FACTOR, 640, 350),
                'wheel': wheeled, 'pan': pan_by(wheeled, 30, 20),
                'pinch': pinch_transform(pinch_transform(pan_by(wheeled, 30, 20),
                                                         {'d': 100, 'mid': (350, 300)}, {'d': 150, 'mid': (325, 300)}),
                                         {'d': 150, 'mid': (325, 300)}, {'d': 200, 'mid': (350, 300)}),
                'phone': fit_transform(**PHONE),
                'ceiling': zoom_at(fit_transform(**LOOK), 1e6, 640, 350)}

    def test_a_click_on_a_drawn_site_resolves_to_it_after_every_transform(self):
        for name, t in self.transforms().items():
            for site in LOCATED:
                x, y = to_screen(t, plane(site['lon'], site['lat']))
                hits = [h['code'] for h in site_at(t, SITES, x, y)]
                self.assertIn(site['s'], hits, (name, site['s'], hits))

    def test_the_click_opens_the_largest_dot_whose_circle_covers_the_point(self):
        """The stack rule, read through the one pair the fixture makes prove it.

        SYN-PS-1 stands 0.2369 plane units from the shared position — 9.589 px at the fitted
        1280 scale and 7.949 px at 390 — so at 390 SYN-BAY-3's drawn circle (radius 4.789,
        reach 8.789 px with the slop) covers PS-1's centre and opens first there, and at 1280
        nothing but PS-1 itself reaches its own centre. Both figures are the formulas above,
        not a second rule.
        """
        distance = math.dist(plane(*STACKED), plane(123.55, 10.70))
        ps1 = [s for s in SITES if s['s'] == 'SYN-PS-1'][0]
        bay3 = [s for s in SITES if s['s'] == 'SYN-BAY-3'][0]
        look = fit_transform(**LOOK)
        phone = fit_transform(**PHONE)
        self.assertGreater(distance * look['k'], radius_of(bay3) + HIT_SLOP)   # 9.589 > 8.789
        self.assertLess(distance * phone['k'], radius_of(bay3) + HIT_SLOP)     # 7.949 < 8.789
        x, y = to_screen(look, plane(123.55, 10.70))
        hits = [h['code'] for h in site_at(look, SITES, x, y)]
        self.assertEqual(['SYN-PS-1'], hits)
        x, y = to_screen(phone, plane(123.55, 10.70))
        hits = [h['code'] for h in site_at(phone, SITES, x, y)]
        self.assertEqual(['SYN-BAY-3', 'SYN-BAY-1', 'SYN-PS-1'], hits)
        self.assertIn('SYN-PS-1', hits, 'PS-1 is still in the stack it shares at 390')
        self.assertAlmostEqual(radius_of(ps1), min(7, 2 + math.sqrt(120) / 6), places=12)
        self.assertAlmostEqual(distance * look['k'], 9.589, places=2)

    def test_the_shared_position_returns_the_whole_stack_in_the_stated_order(self):
        for name, t in self.transforms().items():
            x, y = to_screen(t, plane(*STACKED))
            hits = site_at(t, SITES, x, y)
            expected = sorted(hits, key=lambda h: (-h['r'], h['code']))
            self.assertEqual([h['code'] for h in hits], [h['code'] for h in expected], name)
            self.assertIn('SYN-BAY-1', [h['code'] for h in hits], name)
            self.assertIn('SYN-BAY-3', [h['code'] for h in hits], name)
            # radius descending, code ascending on a tie — the documented order
            radii = [h['r'] for h in hits]
            self.assertEqual(radii, sorted(radii, reverse=True), name)

    def test_the_more_zoom_the_tighter_the_click_the_slop_reaches(self):
        # a real property, measured on the fixture: in a small 300x450 box the stacked position
        # also reaches SYN-PS-1, whose dot overlaps there at that scale; at 1280 it does not.
        phone = fit_transform(300, 450)
        desktop = fit_transform(**LOOK)
        x, y = to_screen(phone, plane(*STACKED))
        self.assertIn('SYN-PS-1', [h['code'] for h in site_at(phone, SITES, x, y)])
        x, y = to_screen(desktop, plane(*STACKED))
        self.assertNotIn('SYN-PS-1', [h['code'] for h in site_at(desktop, SITES, x, y)])

    def test_a_click_far_from_every_site_hits_nothing(self):
        t = fit_transform(**LOOK)
        self.assertEqual([], site_at(t, SITES, -50, -50))
        self.assertEqual([], site_at(t, SITES, t['w'] + 50, t['h'] + 50))

    def test_the_links_are_hit_on_their_curve_and_missed_away_from_it(self):
        t = fit_transform(**LOOK)
        for name, defn in LINK_DEFS.items():
            p1, c, p2 = link_curve(defn)
            for t_frac in (0.1, 0.5, 0.9):
                x, y = to_screen(t, curve_point(p1, c, p2, t_frac))
                near = link_at(t, x, y)
                self.assertIsNotNone(near, (name, t_frac))
                self.assertEqual(near[1], name, (name, t_frac))
                self.assertLessEqual(near[0], LINK_HIT)
            x, y = to_screen(t, curve_point(p1, c, p2, 0.5))
            self.assertIsNone(link_at(t, x + 40, y + 40), name)

    def test_the_radius_is_the_pages_own_glyph_rule(self):
        for site in SITES:
            if site['k'] == 'NL':
                self.assertEqual(round(radius_of(site), 9), LOAD_RADIUS)
            else:
                self.assertAlmostEqual(radius_of(site), min(7, 2 + (site['cap'] or 1) ** 0.5 / 6), places=12)
        # the one pumped-storage site is drawn as a generator, as the page draws it today
        pumped = [s for s in SITES if s['k'] == 'PS'][0]
        self.assertGreater(radius_of(pumped), LOAD_RADIUS)

    def test_the_price_scale_adapts_to_the_drawn_prices(self):
        """UX-3: the knots are the 5th to 95th percentiles of the drawn prices, so a grid whose
        prices sit together still spreads across the colours; a price at either end takes the end
        colour; the median is the neutral centre."""
        values = [5200, 5600, 9400, 9900, 10100, 10300, 10700, 16000, 31000, 32000, 32000, 40000]
        scale = price_scale(values)
        self.assertEqual(5, len(scale['knots']))
        self.assertEqual(scale['knots'], sorted(scale['knots']))
        self.assertLessEqual(scale['knots'][4], PRICE_CEIL, 'the knots stop at the ceiling')
        self.assertAlmostEqual(scale['knots'][2], quantile(sorted(values), 0.5), places=9)
        self.assertEqual(color_at(scale, None), UNKNOWN_FILL)
        self.assertTrue(colour_close(color_at(scale, -500), P_DARK[0]), 'below the domain: the first colour')
        self.assertTrue(colour_close(color_at(scale, 999999), P_DARK[4]), 'above it: the last')
        self.assertTrue(colour_close(color_at(scale, scale['knots'][2]), P_DARK[2]), 'the median is the centre')
        # the old fixed stops drew every price between 9,400 and 10,700 one colour; here they span
        # from the first quarter to the centre and differ visibly
        self.assertNotEqual(color_at(scale, 9400), color_at(scale, 10700))
        # between two knots the mix is in OKLab, not RGB: the halfway colour differs from the
        # channel average and matches this file's own OKLab arithmetic
        mid = (scale['knots'][2] + scale['knots'][3]) / 2
        rgb_mid = '#' + ''.join('%02x' % round((int(P_DARK[2][j:j + 2], 16) + int(P_DARK[3][j:j + 2], 16)) / 2) for j in (1, 3, 5))
        self.assertNotEqual(color_at(scale, mid), rgb_mid)
        self.assertTrue(colour_close(color_at(scale, mid), mix_oklab(P_DARK[2], P_DARK[3], 0.5)))

    def test_a_flat_or_clamped_spread_still_gives_an_increasing_scale(self):
        flat = price_scale([4000, 4000, 4000])
        self.assertEqual([3900, 3950, 4000, 4050, 4100], flat['knots'], 'widened about the median')
        capped = price_scale([32000] * 4 + [50000])
        self.assertEqual(capped['knots'], sorted(capped['knots']))
        self.assertEqual(len(set(capped['knots'])), 5, 'strictly increasing')
        self.assertEqual(PRICE_CEIL, capped['knots'][4])
        self.assertTrue(colour_close(color_at(capped, 32000), P_DARK[4]), 'a cap event reads hot')
        negative = price_scale([-2000, -500, 100, 300, 900, 1500])
        self.assertGreaterEqual(negative['knots'][0], PRICE_FLOOR, 'negatives are clamped')
        self.assertTrue(colour_close(color_at(negative, -2000), P_DARK[0]))
        self.assertIsNone(price_scale([]))
        self.assertIsNone(price_scale([None, None]))

    def test_places_cluster_on_screen_and_split_as_the_map_zooms_in(self):
        """UX-3: sites closer than CLUSTER_PX on screen share one mark. The fixture's three-site
        stack is one place at every zoom; SYN-PS-1, 9.475 px from it at 1280 and 6.141 px at 390,
        joins it on a phone only, and the stack's place is sized by its generating MW."""
        look, phone = fit_transform(**LOOK), fit_transform(**PHONE)
        stack = lambda t: next(p for p in cluster_sites(t, SITES) if 'SYN-BAY-1' in p['codes'])
        self.assertEqual(['SYN-BAY-3', 'SYN-BAY-1', 'SYN-STA-1'], stack(look)['codes'])
        self.assertEqual(['SYN-BAY-3', 'SYN-BAY-1', 'SYN-PS-1', 'SYN-STA-1'], stack(phone)['codes'])
        self.assertAlmostEqual(stack(look)['r'], min(13, 2.5 + math.sqrt(260 + 280) / 6), places=9)
        self.assertEqual(len(LOCATED), sum(len(p['codes']) for p in cluster_sites(look, SITES)), 'every located site in one place')
        ceiling = zoom_at(look, 1e6, 640, 350)
        self.assertEqual(['SYN-BAY-3', 'SYN-BAY-1', 'SYN-STA-1'], stack(ceiling)['codes'],
                         'a shared position stays one place at any zoom')
        self.assertEqual(['SYN-PS-1'], next(p for p in cluster_sites(ceiling, SITES) if 'SYN-PS-1' in p['codes'])['codes'])


# --------------------------------------------------------------------------- fail-closed


class Unlocated(unittest.TestCase):
    """Acceptance 3: an unlocated site is never drawn at a coordinate."""

    def test_the_fixture_placeholders_carry_no_position(self):
        self.assertEqual(set(s['s'] for s in PLACEHOLDERS), {'SYN-BAY-2', 'SYN-VIS-LD'})
        for site in PLACEHOLDERS:
            self.assertIsNone(site['lon'])
            self.assertIsNone(site['lat'])
            self.assertNotIn('name', site)

    def test_a_located_hit_test_never_returns_a_placeholder(self):
        for box in (LOOK, PHONE):
            for scale in (1, 1.5, KMAX_FACTOR):
                t = fit_transform(**box)
                if scale != 1:
                    t = zoom_at(t, scale, box['w'] / 2, box['h'] / 2)
                for lon in (113.0, 114.0, 120.0, 123.42, 127.5):
                    for lat in (4.0, 10.9, 14.0, 21.5):
                        x, y = to_screen(t, plane(lon, lat))
                        for hit in site_at(t, SITES, x, y):
                            self.assertNotEqual(hit['site']['p'], 'placeholder')

    def test_the_drawn_set_never_holds_a_placeholder_at_any_scope_or_layer(self):
        # the module's §viewSites: a placeholder is never drawn, whatever the reader switches on
        self.assertIn("&& s.p !== 'placeholder' && s.lon != null && s.lat != null", MAP_JS)
        self.assertNotIn('matrixLayout', MAP_JS)
        self.assertNotIn('PENDING_ORIGIN', MAP_JS)
        self.assertNotIn('layers.pending', MAP_JS)

    def test_the_unplaced_rows_are_by_grid_then_largest_first(self):
        # the module's §unplacedSites: grid order, then registered MW descending, then code
        ordered = sorted(PLACEHOLDERS, key=lambda s: (s['g'], -(s['cap'] or 0), s['s']))
        self.assertEqual(['SYN-VIS-LD', 'SYN-BAY-2'], [s['s'] for s in ordered])
        self.assertIn('function unplacedSites(sites, scope) {', MAP_JS)


# --------------------------------------------------------------------------- unknown state


class CongestionUnknown(unittest.TestCase):
    """The unknown-state invariant (the review's fix): a congestion the record does not state
    stays unknown — it is never read, drawn or worded as a known "not congested"."""

    def test_the_rule_is_in_the_code_not_a_boolean_coercion(self):
        self.assertIn('function congestionAt(link, ri) {', MAP_JS)
        self.assertIn('function flowAt(link, ri) {', MAP_JS)
        self.assertIn('congested === true', MAP_JS)
        self.assertIn('congestion unknown at the clock', MAP_JS)
        self.assertIn('congestion unknown at ', MAP_JS)   # the canvas label and the fallback line
        self.assertNotIn('!!(link && ri != null', MAP_JS, 'the reviewed boolean coercion is gone')

    def test_a_null_or_missing_flag_is_unknown_never_false(self):
        # the record's own two states
        self.assertIs(congestion_at({'flow': [1], 'congested': [1]}, 0), True)
        self.assertIs(congestion_at({'flow': [1], 'congested': [0]}, 0), False)
        # the unknowns: a null cell, an interval past the flags, an empty or absent flag list,
        # no link at all, and an interval the link's own axis does not name
        self.assertIsNone(congestion_at({'flow': [1], 'congested': [None]}, 0))
        self.assertIsNone(congestion_at({'flow': [1, 1], 'congested': [1]}, 1))
        self.assertIsNone(congestion_at({'flow': [1], 'congested': []}, 0))
        self.assertIsNone(congestion_at({'flow': [1]}, 0))
        self.assertIsNone(congestion_at(None, 0))
        self.assertIsNone(congestion_at({'flow': [1], 'congested': [1]}, None))

    def test_the_flow_follows_the_same_rule_a_zero_is_a_state(self):
        self.assertEqual(0, flow_at({'flow': [0]}, 0))
        self.assertEqual(-120, flow_at({'flow': [-120]}, 0))
        self.assertIsNone(flow_at({'flow': [None]}, 0))
        self.assertIsNone(flow_at({'flow': [1]}, 1))
        self.assertIsNone(flow_at({'congested': [1]}, 0))
        self.assertIsNone(flow_at(None, 0))
        self.assertIsNone(flow_at({'flow': [1]}, None))

    def test_the_fixtures_unknowns_are_exactly_the_two_cells_the_build_leaves_unstated(self):
        unknown = sorted(f'{name}@{HVDC["t"][i]}'
                         for name in ('MINVIS1', 'VISLUZ1')
                         for i in range(len(HVDC['t'])) if congestion_at(HVDC['links'][name], i) is None)
        self.assertEqual(['MINVIS1@2026-09-21 13:45:00', 'VISLUZ1@2026-09-21 14:00:00'], unknown)
        # the clock itself is untouched: both flags stated, so the reviewed failure was the
        # module turning an unstated cell into a negative, not the fixture's flags moving
        row = HVDC['t'].index(CLOCK)
        self.assertIs(congestion_at(HVDC['links']['MINVIS1'], row), True)
        self.assertIs(congestion_at(HVDC['links']['VISLUZ1'], row), True)
        self.assertIs(congestion_at(HVDC['links']['MINVIS1'], HVDC['t'].index('2026-09-21 14:00:00')), False)
        self.assertIsNone(congestion_at(HVDC['links']['VISLUZ1'], HVDC['t'].index('2026-09-21 14:00:00')))


# --------------------------------------------------------------------------- the fixture contract


class Fixture(unittest.TestCase):
    """The synthetic bake the harness runs on: deterministic, and shaped as the page reads it."""

    def test_the_committed_bytes_are_reproducible_from_the_formulas(self):
        result = subprocess.run([sys.executable, str(FIXTURE / 'build.py'), '--check'],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_the_shapes_are_the_bakes_shapes(self):
        axis = json.loads((DATA / 'regions.json').read_text(encoding='utf-8'))['t']
        self.assertEqual(288, len(axis), 'one day of five-minute intervals')
        self.assertEqual(axis, HVDC['t'])
        self.assertEqual(axis, NODES['t'])
        for site in SITES:
            self.assertEqual({'s', 'k', 'g', 'cap', 'lon', 'lat', 'p'} | ({'name'} if site.get('name') else set()),
                             set(site))
            self.assertIn(site['g'], ('CLUZ', 'CVIS', 'CMIN'))
            self.assertIn(site['k'], ('G', 'NL', 'PS'))
        self.assertEqual(set(NODES['sites']), {s['s'] for s in SITES})
        self.assertEqual(len(NODES['lmp']), len(axis))
        self.assertEqual(len(NODES['lmp'][0]), len(SITES))

    def test_the_stack_the_messages_and_the_event_are_in_the_fixture_as_documented(self):
        # one position three sites share, as the real bake has (research §2.4a)
        at_stack = [s['s'] for s in LOCATED if (s['lon'], s['lat']) == STACKED]
        self.assertEqual(sorted(at_stack), ['SYN-BAY-1', 'SYN-BAY-3', 'SYN-STA-1'])
        self.assertEqual(8, len(LOCATED))
        # the message the map marks at a located site: only CALACA's text names one site
        self.assertIn('CALACA', [a['text'] for a in ADVISORIES if a['id'] == 'SYN-ADV-0008'][0])
        # the event names a placeholder site: it has no position, so its notice stands at its grid
        self.assertEqual('SYN-BAY-2', EVENTS[0]['site'])
        self.assertEqual('2026-09-21 13:40:00', EVENTS[0]['t'])

    def test_the_link_flags_at_the_clock_are_the_ones_the_report_expects(self):
        row = HVDC['t'].index(CLOCK)
        self.assertEqual({'MINVIS1': 1, 'VISLUZ1': 1}, {k: v['congested'][row] for k, v in HVDC['links'].items()})
        # and the two cells the build leaves unstated, so an unknown has a case in the fixture
        # (the flag the record does not state is not a "not congested": src/grid/map.js §congestionAt)
        self.assertIsNone(HVDC['links']['MINVIS1']['congested'][HVDC['t'].index('2026-09-21 13:45:00')])
        self.assertIsNone(HVDC['links']['VISLUZ1']['congested'][HVDC['t'].index('2026-09-21 14:00:00')])
        self.assertEqual(0, HVDC['links']['MINVIS1']['congested'][HVDC['t'].index('2026-09-21 14:00:00')])


# --------------------------------------------------------------------------- the node harness


def run_harness(width=1280, height=700, extra=()):
    """Run the module under the fixture harness; the report is one JSON object."""
    if NODE is None:
        raise unittest.SkipTest('node is not installed for this interpreter')
    command = [NODE, str(FIXTURE / 'harness.mjs'), '--root', str(ROOT), '--data', str(DATA),
               '--width', str(width), '--height', str(height), *extra]
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, timeout=120)
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise AssertionError(f'harness.mjs printed no report: {result.stdout[-400:]} {result.stderr[-800:]}')


def approximate_data(temp):
    """The fixture with two approximate sites (build_data's display placement): SYN-BAY-2 drawn
    at the shared Bay position, and SYN-APX-1 alone where no located site stands."""
    for path in DATA.iterdir():
        shutil.copy2(path, Path(temp) / path.name)
    sites = json.loads((DATA / 'sites.json').read_text(encoding='utf-8'))
    for site in sites:
        if site['s'] == 'SYN-BAY-2':
            site.update({'lon': STACKED[0], 'lat': STACKED[1], 'p': 'approximate',
                         'approx': {'prefix': '08', 'near': 'SYN-BAY-1', 'n': 3}})
    sites.append({'s': 'SYN-APX-1', 'k': 'G', 'g': 'CVIS', 'cap': 90, 'lon': 122.55, 'lat': 11.2,
                  'p': 'approximate', 'approx': {'prefix': '06', 'near': 'SYN-NONE', 'n': 1}})
    (Path(temp) / 'sites.json').write_text(json.dumps(sites), encoding='utf-8')
    return sites


@unittest.skipUnless(NODE, 'the module is a browser script; the harness runs on node, absent here')
class ApproximateHarness(unittest.TestCase):
    """An approximate site is drawn as a dashed ring, labelled, and never moves a located place."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.temp = tempfile.TemporaryDirectory(prefix='grid-map-approx-')
        cls.sites = approximate_data(cls.temp.name)
        run = lambda *extra: json.loads(subprocess.run(
            [NODE, str(FIXTURE / 'harness.mjs'), '--root', str(ROOT), '--data', cls.temp.name, *extra],
            capture_output=True, text=True, cwd=ROOT, timeout=120).stdout)
        cls.look = run('--width', '1280', '--height', '700')
        cls.text = run('--width', '390', '--height', '585', '--no-canvas')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_it_runs_clean(self):
        for report in (self.look, self.text):
            self.assertTrue(report['ok'], report.get('error'))
            self.assertEqual([], report['errors'])

    def test_approximate_sites_are_drawn_and_only_placeholders_are_pending(self):
        draw = self.look['draw']
        rows = {row['code']: row for row in draw['located']}
        self.assertTrue(rows['SYN-BAY-2']['approximate'])
        self.assertTrue(rows['SYN-APX-1']['approximate'])
        self.assertFalse(rows['SYN-BAY-1']['approximate'])
        self.assertEqual(['SYN-VIS-LD'], [row['code'] for row in draw['pending']])
        self.assertIn('8 sites located and 2 approximate', draw['legend']['asof'])
        self.assertIn('1 unplaced and listed apart', draw['legend']['asof'])

    def test_the_located_places_are_what_they_were_and_the_ring_joins_one(self):
        t = fit_transform(**LOOK)
        clusters = self.look['draw']['clusters']
        # this file's clustering of the same sites, with the ring sizes
        want = cluster_sites(t, self.sites)
        self.assertEqual(sorted(p['codes'] for p in want), sorted(c['codes'] for c in clusters))
        for c in clusters:
            p = next(w for w in want if w['codes'] == c['codes'])
            for key in ('core', 'ring', 'r', 'approx'):
                self.assertAlmostEqual(p[key], c[key], places=6, msg=(c['codes'], key))
        # removing the approximate sites gives the located clustering of the fixture unchanged
        located = [[code for code in c['codes'] if code not in ('SYN-BAY-2', 'SYN-APX-1')] for c in clusters]
        self.assertEqual(sorted(p['codes'] for p in cluster_sites(t, SITES)), sorted(c for c in located if c))
        ley = next(c for c in clusters if 'SYN-BAY-1' in c['codes'])
        self.assertEqual('SYN-BAY-2', ley['codes'][-1], 'the located sites first, whatever the MW')
        self.assertEqual(1, ley['approx'])
        self.assertGreaterEqual(ley['ring'], ley['core'] + 2.5)
        x, y = to_screen(t, plane(*STACKED))
        self.assertAlmostEqual(x, ley['x'], places=6)
        self.assertAlmostEqual(y, ley['y'], places=6)
        alone = next(c for c in clusters if c['codes'] == ['SYN-APX-1'])
        self.assertEqual((0, 1), (alone['core'], alone['approx']))
        self.assertGreaterEqual(alone['ring'], 3)
        # the ring is painted: an arc of the ring's radius at the place
        self.assertIn({'x': round(ley['x'], 2), 'y': round(ley['y'], 2), 'r': round(ley['ring'], 2)},
                      [{k: round(a[k], 2) for k in ('x', 'y', 'r')} for a in self.look['draw']['arcs']])

    def test_the_hover_and_the_key_say_approximate(self):
        # the list the stack's clicks pinned, and the lone site's hover, which names no ring
        listed = self.look['pin']['stack']
        self.assertIn('Approximate position, placed near other 08 sites. No surveyed location.', listed)
        self.assertEqual(1, listed.count('gn-badge gn-badge--outline gt-approx'))
        self.assertNotIn('Approximate', self.look['hover']['site'])
        kinds = self.look['draw']['legend']['kinds']
        self.assertTrue(any(k.startswith('Approximate position · dashed ring') for k in kinds), kinds)

    def test_the_text_fallback_says_approximate(self):
        lines = self.text['fallback']['lines']
        self.assertTrue(any('SYN-APX-1' in line and 'approximate position near other 06 sites' in line
                            for line in lines), lines)
        pending = [line for line in lines if 'no position on record' in line][0]
        self.assertIn('1 sites with no position on record', pending)
        self.assertNotIn('SYN-BAY-2', pending)

    def test_an_approximate_position_never_decides_a_province_grid(self):
        self.assertIn("const located = (sites || []).filter(isLocated).map(", MAP_JS)
        self.assertIn("if (isLocated(s)) { const v = valueOf(s); if (v != null) everyPrice.push(v); }", MAP_JS)


@unittest.skipUnless(NODE, 'the module is a browser script; the harness runs on node, absent here')
class Harness(unittest.TestCase):
    """The module itself, executed: its painting, its gestures and its own math."""

    @classmethod
    def setUpClass(cls):
        cls.look = run_harness()
        cls.phone = run_harness(390, 585)
        cls.text = run_harness(390, 585, ('--no-canvas',))

    def test_the_module_runs_clean_and_asks_the_network_for_nothing(self):
        for report in (self.look, self.phone, self.text):
            self.assertTrue(report['ok'], report.get('error'))
            self.assertEqual([], report['errors'])
            self.assertEqual([], report['fetches'], 'the module fetched: every layer reads baked data')

    def test_the_transforms_the_module_computed_are_this_files_arithmetic(self):
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            got = report['gestures']['transforms']
            t = fit_transform(**box)
            self.assertAlmostEqual(got['open']['k'], t['k'], places=8)
            inside = zoom_at(t, BUTTON_FACTOR, box['w'] / 2, box['h'] / 2)
            self.assertAlmostEqual(got['zoomIn']['k'], inside['k'], places=8)
            twice = zoom_at(inside, BUTTON_FACTOR, box['w'] / 2, box['h'] / 2)
            self.assertAlmostEqual(got['zoomIn2']['k'], twice['k'], places=8)
            back = zoom_at(twice, 1 / BUTTON_FACTOR, box['w'] / 2, box['h'] / 2)
            self.assertAlmostEqual(got['zoomOut']['k'], back['k'], places=8)
            self.assertAlmostEqual(got['fit']['k'], t['k'], places=8)
            self.assertAlmostEqual(got['fit']['fx'], t['fx'], places=8)
            wheeled = zoom_at(t, 2 ** (240 / WHEEL_SCALE), box['w'] / 2, box['h'] / 2)
            self.assertAlmostEqual(got['wheel']['k'], wheeled['k'], places=8)
            panned = pan_by(wheeled, 30, 20)
            self.assertAlmostEqual(got['pan']['fx'], panned['fx'], places=8)
            self.assertAlmostEqual(got['pan']['fy'], panned['fy'], places=8)
            # the pinch: 100 px apart drawn to 200 px, in two anchored steps of 150% and 4/3,
            # with the midpoint moving -25 then +25 px; each step zooms about its *previous*
            # midpoint and pans by the midpoint's travel
            step = pinch_transform(panned, {'d': 100, 'mid': (350, 300)}, {'d': 150, 'mid': (325, 300)})
            pinched = pinch_transform(step, {'d': 150, 'mid': (325, 300)}, {'d': 200, 'mid': (350, 300)})
            self.assertAlmostEqual(got['pinch']['k'], pinched['k'], places=8)
            self.assertAlmostEqual(got['pinch']['fx'], pinched['fx'], places=8)
            self.assertAlmostEqual(got['pinch']['fy'], pinched['fy'], places=8)
            # zoom in, zoom out and fit each changed k (acceptance 1, first half)
            self.assertGreater(got['zoomIn']['k'], got['open']['k'])
            self.assertLess(got['zoomOut']['k'], got['zoomIn2']['k'])
            self.assertAlmostEqual(got['fit']['k'], got['open']['k'], places=8)
            self.assertNotEqual(got['wheel']['k'], got['open']['k'])

    def test_a_click_on_a_drawn_site_resolves_to_that_site_after_each_transform(self):
        """The harness records the transform it clicked under; this file re-derives the screen
        point of the target from that same transform (the formulas above), checks the click was
        there, and checks the module opened the top of the re-derived stack."""
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            clicks = report['gestures']['clicks']
            for name, code in (('zoomIn', 'SYN-LUZ-1'), ('zoomOut', 'SYN-MIN-1'),
                               ('fit', 'SYN-LEY-1'), ('pan', 'SYN-CALACA-1')):
                clicked = clicks[name]
                t = clicked['t']
                site = [s for s in SITES if s['s'] == code][0]
                x, y = to_screen(t, plane(site['lon'], site['lat']))
                self.assertAlmostEqual(clicked['at'][0], round(x, 3), places=2, msg=(name, box))
                self.assertAlmostEqual(clicked['at'][1], round(y, 3), places=2, msg=(name, box))
                expected = [h['code'] for h in site_at(t, SITES, x, y)]
                self.assertIn(code, expected, (name, box))
                self.assertEqual(clicked['got'], expected[0], (name, box, expected))

    def test_the_shared_position_cycles_its_stack_in_the_re_derived_order(self):
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            clicks = report['gestures']['clicks']
            fit = fit_transform(**box)
            x, y = to_screen(fit, plane(*STACKED))
            expected = [h['code'] for h in site_at(fit, SITES, x, y)]
            self.assertEqual(clicks['stack'], expected[:3], (box, clicks['stack'], expected))
            self.assertEqual(len(set(clicks['stack'])), 3, 'three clicks open three different sites')

    def test_a_drag_is_not_a_click_and_a_nudge_is(self):
        for report in (self.look, self.phone):
            clicks = report['gestures']['clicks']
            self.assertEqual(0, clicks['dragLongClicks'], 'a 20 px drag fired a click')
            self.assertEqual('SYN-LEY-1', clicks['dragShort'], 'a 2 px drag did not count as a click')

    def test_the_pinch_to_drag_transition_pans_by_the_survivors_own_travel(self):
        """Round 2 of the review: a pinch never moved the drag's anchor, so the first move of
        the surviving finger panned by the distance back to where the second finger landed —
        51 px for 1 px of movement in the review's own sequence. The harness replays it (down at
        (300,300) and (400,300), drawn apart to (250,300) and (450,300), the first lifted, the
        other moved 1 px) and records the transform at the lift and after that move; this file
        re-derives both from the fitted box."""
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            lift = report['gestures']['pinchLift']
            t = fit_transform(**box)
            step = pinch_transform(t, {'d': 100.0, 'mid': (350.0, 300.0)}, {'d': 150.0, 'mid': (325.0, 300.0)})
            pinched = pinch_transform(step, {'d': 150.0, 'mid': (325.0, 300.0)},
                                      {'d': 200.0, 'mid': (350.0, 300.0)})
            self.assertAlmostEqual(lift['afterLift']['k'], pinched['k'], places=8, msg=box)
            self.assertAlmostEqual(lift['afterLift']['fx'], pinched['fx'], places=8, msg=box)
            self.assertAlmostEqual(lift['afterLift']['fy'], pinched['fy'], places=8, msg=box)
            # the survivor's own 1 px (450 -> 451) is the whole pan, and k does not move
            one = pan_by(pinched, 1.0, 0)
            self.assertAlmostEqual(lift['afterOne']['fx'], one['fx'], places=8, msg=box)
            self.assertAlmostEqual(lift['afterOne']['fy'], one['fy'], places=8, msg=box)
            self.assertAlmostEqual(lift['afterOne']['k'], pinched['k'], places=8, msg=box)
            self.assertAlmostEqual((lift['afterLift']['fx'] - lift['afterOne']['fx']) * pinched['k'], 1.0,
                                   places=6, msg=box)
            # the reviewed anchor would have panned by the 51 px back to the second finger
            stale = pan_by(pinched, 51.0, 0)
            self.assertNotAlmostEqual(lift['afterOne']['fx'], stale['fx'], places=6, msg=box)
            # a two-finger tap over a drawn site opens nothing; a lone tap there still opens it
            self.assertEqual(0, lift['clicksAfterTwoFingerTap'], box)
            self.assertEqual('SYN-LEY-1', lift['oneFingerTap'], box)
            # and the taps really were on the site: the harness's point is this file's own
            # screen position of SYN-LEY-1 at the fitted box
            leyre = [s for s in SITES if s['s'] == 'SYN-LEY-1'][0]
            x, y = to_screen(t, plane(leyre['lon'], leyre['lat']))
            self.assertAlmostEqual(lift['twoFingerTapPoint'][0], x, places=6, msg=box)
            self.assertAlmostEqual(lift['twoFingerTapPoint'][1], y, places=6, msg=box)

    def test_a_click_on_a_link_calls_the_link_callback_with_that_link(self):
        for report in (self.look, self.phone):
            self.assertEqual('VISLUZ1', report['gestures']['clicks']['link'])
            self.assertEqual('VISLUZ1', report['linkProbe']['hit'])
            self.assertEqual([], report['linkProbe']['sites'], 'no site stands at the link midpoint')

    def test_the_hover_tooltip_names_the_site_its_code_and_the_price_at_the_clock(self):
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            tip = report['hover']['site']
            self.assertIn('<b>SYN-LEY-1</b>', tip)
            self.assertIn('generator · Visayas', tip)
            self.assertIn('<span class="gt-time mono">13:40</span>', tip)
            self.assertRegex(tip, r'<span class="gt-price mono"><svg class="gt-dot"[^>]*><circle[^>]*fill="#[0-9a-f]{6}"/></svg>₱32,000</span>')
            self.assertIn('<span class="gt-cap mono">180 MW</span>', tip)
            self.assertIn('MW scheduled', tip)
            # UX-3: a name that reveals the technology is withheld (the overview's rule), the code stays
            self.assertNotIn('Geothermal', tip)
            self.assertNotIn('href=', tip, 'the hover lists; only the pinned list links')
            # the place's list names every site of the place the hover's own transform drew:
            # three at 1280, four at 390, where SYN-PS-1 joins the stack's place
            t = fit_transform(**box)
            place = next(p for p in cluster_sites(t, SITES) if 'SYN-BAY-1' in p['codes'])
            stack_tip = report['hover']['stack']
            self.assertIn(f'{len(place["codes"])} assets at this place · Visayas', stack_tip)
            self.assertEqual(place['codes'], re.findall(r'<b>([A-Z0-9-]+)</b>', stack_tip))
            self.assertEqual(4 if box is PHONE else 3, len(place['codes']), box)
            self.assertIsNone(report['hover']['blank'], 'the tooltip stayed open away from every site')

    def test_a_click_on_a_place_of_several_pins_its_list_with_links_and_escape_closes_it(self):
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            pinned = report['pin']['stack']
            t = fit_transform(**box)
            place = next(p for p in cluster_sites(t, SITES) if 'SYN-BAY-1' in p['codes'])
            self.assertEqual([f'/plant/{code}' for code in place['codes']], re.findall(r'href="([^"]+)"', pinned))
            self.assertIn('class="gt-close" aria-label="Close the list"', pinned)
            self.assertTrue(report['pin']['closedByEscape'], box)
            self.assertFalse(report['pin']['loneClickPins'], 'a lone site opens its detail, no list')

    def test_every_layer_is_painted_from_the_bake_and_nothing_else(self):
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            draw = report['draw']
            t = fit_transform(**box)
            self.assertEqual(len(GEO['features']), draw['land'], box)
            self.assertEqual(sorted(s['s'] for s in LOCATED), sorted(d['code'] for d in draw['located']))
            self.assertEqual(sorted(s['s'] for s in PLACEHOLDERS), sorted(d['code'] for d in draw['pending']))
            # the fills are the scale of the drawn prices at the clock, applied to each site's own
            values = drawn_value_at_clock(LOCATED)
            scale = price_scale(values)
            by_code = {s['s']: s for s in SITES}
            for row in draw['located']:
                self.assertTrue(colour_close(color_at(scale, value_of(by_code[row['code']])), row['fill']),
                                (row['code'], row['fill']))
            for row in draw['located']:
                site = by_code[row['code']]
                x, y = to_screen(t, plane(site['lon'], site['lat']))
                self.assertAlmostEqual(row['x'], x, places=8, msg=row['code'])
                self.assertAlmostEqual(row['y'], y, places=8, msg=row['code'])
                self.assertAlmostEqual(row['r'], radius_of(site), places=8, msg=row['code'])
                self.assertEqual(value_of(site), row['value'], row['code'])
            # the places are this file's clustering of the same sites, each painted once
            places = cluster_sites(t, SITES)
            self.assertEqual(sorted(p['codes'] for p in places), sorted(c['codes'] for c in draw['clusters']), box)
            for c in draw['clusters']:
                want = [p for p in places if p['codes'] == c['codes']][0]
                self.assertAlmostEqual(want['r'], c['r'], places=8)
                self.assertEqual(len(c['codes']), c['n'])
            # PP-B5: the pending rows carry no position at all (the page lists them apart), each
            # with the price the node file states and the scale's colour for it
            ordered = sorted(PLACEHOLDERS, key=lambda s: (s['g'], -(s['cap'] or 0), s['s']))
            self.assertEqual([s['s'] for s in ordered], [d['code'] for d in draw['pending']], box)
            for row in draw['pending']:
                self.assertNotIn('x', row, row['code'])
                self.assertNotIn('y', row, row['code'])
                self.assertEqual(value_of(by_code[row['code']]), row['value'], row['code'])
                self.assertTrue(colour_close(color_at(scale, row['value']), row['fill']), row['code'])
            # the price readings are the fixture's own cells
            self.assertEqual(min(values), draw['price']['min'])
            self.assertEqual(max(values), draw['price']['max'])
            self.assertEqual(sum(1 for v in values if v >= PRICE_CEIL), draw['price']['atCeil'])
            # the links: both congested at the clock, one mark each, the flows from hvdc.json
            row_index = HVDC['t'].index(CLOCK)
            self.assertEqual({'VISLUZ1', 'MINVIS1'}, {link['id'] for link in draw['links']})
            for link in draw['links']:
                self.assertIs(True, link['congested'])
                self.assertEqual(1, link['marks'])
                self.assertEqual(HVDC['links'][link['id']]['flow'][row_index], link['flow'])
                self.assertIn('congested at 13:40', link['label'])
            # the messages the last hour names at a drawn site; the event's site has no position
            self.assertEqual(['SYN-ADV-0008'], [m['id'] for m in draw['messages']])
            self.assertEqual([], draw['events'])
            # UX-3: drawn by severity. CALACA's notice is an information glyph at its place. The
            # trip names SYN-BAY-2, which has no position (PP-B5), so it and the event made from
            # it stand as one alert at the Visayas grid. The yellow alert of 09:10 is past its
            # four hours.
            self.assertEqual([('info', 'site', 'SYN-CALACA-1', None, 1), ('alert', 'grid', None, 'CVIS', 1)],
                             [(m['severity'], m['level'], m['code'], m['grid'], m['n']) for m in draw['markers']])
            self.assertEqual('syn-bay-unit-2-trip', draw['markers'][1]['event'])
            self.assertEqual(['SYN-ADV-0002'], [n['id'] for n in draw['notices']])
            self.assertEqual({'alert': 1, 'warning': 0, 'info': 1}, draw['severity'])
            # every arc on the canvas is a place, a count badge or the round information glyph,
            # and nothing else: nothing stands for a site with no position
            badges = sum(1 for c in draw['clusters'] if c['badge'])
            infos = sum(1 for m in draw['markers'] if m['severity'] == 'info')
            self.assertEqual(len(draw['clusters']) + badges + infos, len(draw['arcs']), box)
            # the labels: the grid names, the two links with their clock, and the link's own name
            # and the grid notice's plate only where there is room (the page hides them at 390)
            for text in ('LUZON', 'VISAYAS', 'MINDANAO'):
                self.assertIn(text, draw['texts'], box)
            self.assertFalse(any('sites' in t and '·' in t for t in draw['texts']), 'no matrix caption')
            if box['w'] >= 600:
                self.assertIn('Leyte–Luzon HVDC', draw['texts'], box)
                self.assertIn('Visayas grid notice', draw['texts'], box)
            else:
                self.assertNotIn('Leyte–Luzon HVDC', draw['texts'], box)
                self.assertNotIn('Visayas grid notice', draw['texts'], box)

    def test_a_notice_naming_a_site_with_no_position_stands_at_its_grid(self):
        # the fixture's event names SYN-BAY-2, a placeholder: nothing is drawn where it could be
        # read as a coordinate; the notice and its event stand as one mark at the Visayas grid,
        # inside the part of the map the overlays leave visible
        for report, box in ((self.look, LOOK), (self.phone, PHONE)):
            draw = report['draw']
            grid = [m for m in draw['markers'] if m['level'] == 'grid'][0]
            self.assertEqual(['SYN-ADV-0002'], grid['ids'])
            notice = draw['notices'][0]
            self.assertEqual((grid['x'], grid['y']), (notice['x'], notice['y']))
            self.assertGreater(notice['x'], 0)
            self.assertLess(notice['x'], box['w'])
            located = {(r['x'], r['y']) for r in draw['located']}
            self.assertNotIn((notice['x'], notice['y']), located)

    def test_a_congestion_the_record_does_not_state_is_unknown_not_a_known_negative(self):
        """The review's finding: a null flag was coerced to `false`, and the tooltip then said
        "not congested". The fixture states one of each at 14:00 — MINVIS1's flag is 0 (the
        record says not congested) and VISLUZ1's is null (the record says nothing) — and the
        drawing, the canvas label, the legend line and the tooltip must keep them apart."""
        for report in (self.look, self.phone):
            links = {link['id']: link for link in report['clocks']['at1400']['links']}
            self.assertIs(False, links['MINVIS1']['congested'])
            self.assertIsNone(links['VISLUZ1']['congested'])
            self.assertEqual(0, links['MINVIS1']['marks'], 'a known-negative link draws no mark')
            self.assertEqual(0, links['VISLUZ1']['marks'], 'an unknown link draws no mark')
            self.assertNotIn('congestion', links['MINVIS1']['label'], 'a known false is not marked')
            self.assertIn('congestion unknown at 14:00', links['VISLUZ1']['label'])
            self.assertIn('1 link with unknown congestion', report['clocks']['at1400']['legendAsOf'])
            self.assertNotIn('unknown', report['clocks']['at1340']['legendAsOf'],
                             'both flags are stated at the clock')
            self.assertIn('2 links congested', report['clocks']['at1340']['legendAsOf'])
            # the tooltip: one link named and said not congested, the other named and unknown
            self.assertIn('Mindanao–Visayas HVDC', report['hover']['link1400Known'])
            self.assertIn('not congested at the clock', report['hover']['link1400Known'])
            self.assertIn('Leyte–Luzon HVDC', report['hover']['link1400Unknown'])
            self.assertIn('congestion unknown at the clock', report['hover']['link1400Unknown'])
            self.assertNotIn('not congested', report['hover']['link1400Unknown'])
            self.assertIn('congested at the clock', report['hover']['link'])

    def test_the_legend_prints_the_scale_the_range_and_the_kinds(self):
        for report in (self.look, self.phone):
            legend = report['draw']['legend']
            self.assertEqual('Node price, ₱/MWh', legend['title'])
            values = drawn_value_at_clock(LOCATED)
            scale = price_scale(values)
            # UX-3: the legend states the domain: the five knots of this draw's scale, the top one
            # with a `+` where it is the ceiling (never "cap": the node series is uncapped)
            ticks = [tick_label(value) for value in scale['knots']]
            self.assertEqual(ticks, legend['ticks'])
            self.assertEqual('32,000+', legend['ticks'][-1], 'the fixture\'s 95th percentile is at the ceiling')
            self.assertNotIn('cap', ' '.join(legend['ticks']))
            self.assertEqual(legend['ticks'], report['draw']['snapshotLegend']['ticks'],
                             'the DOM tick spans and the snapshot print the same labels')
            self.assertEqual(ramp_gradient(scale).count('#'), legend['ramp'].count('#'))
            for got, want in zip(re.findall(r'#[0-9a-f]{6}', legend['ramp']), re.findall(r'#[0-9a-f]{6}', ramp_gradient(scale))):
                self.assertTrue(colour_close(got, want), (got, want))
            self.assertIn(f"At 2026-09-21 13:40 the {len(values)} drawn prices run", legend['range'])
            self.assertIn('{:,}'.format(min(values)), legend['range'])
            self.assertIn('{:,}'.format(max(values)), legend['range'])
            self.assertIn('Centre: their median.', legend['range'])
            self.assertIn(f"{sum(1 for v in values if v >= PRICE_CEIL)} of {len(values)} at ₱32,000 or above", legend['range'])
            self.assertNotIn('cap', legend['range'])
            self.assertIn(f"{len(LOCATED)} sites located", legend['asof'])
            self.assertIn(f"{len(PLACEHOLDERS)} unplaced and listed apart", legend['asof'])
            self.assertIn('2 links congested', legend['asof'])
            for kind in ('Generator · circle sized by registered MW', 'Load node · small circle',
                         'Pumped storage · drawn as a generator',
                         'Several assets at one place · one mark with their count',
                         'Congested link · red, with a mark at the clock',
                         'Alert · red alert or trip notice',
                         'Warning · yellow alert, load dropping or derating',
                         'Information · notice or back online'):
                self.assertIn(kind, legend['kinds'], legend['kinds'])
            self.assertFalse(any('pending' in k.lower() for k in legend['kinds']), 'no matrix in the key')
            # the ramp and the dots are one scale: the module's own functions draw both
            self.assertEqual(report['math']['scaleAtClock']['ramp'], legend['ramp'])
            self.assertEqual(report['math']['scaleAtClock']['ticks'], legend['ticks'])
            self.assertEqual(report['math']['colorNull'], UNKNOWN_FILL)

    def test_the_chips_toggle_their_group_and_the_scope_scopes(self):
        for report in (self.look, self.phone):
            chips = report['chips']
            on = chips['on']
            self.assertEqual(len(LOCATED), on['located'])
            self.assertEqual(len(PLACEHOLDERS), on['pending'])
            generators = [s for s in LOCATED if s['k'] != 'NL']
            loads = [s for s in LOCATED if s['k'] == 'NL']
            self.assertEqual(len(loads), chips['off_generators']['located'], 'generators off leaves the loads')
            self.assertEqual(len(generators), len(chips['off_loads']['fills']), 'loads off leaves the generators')
            self.assertNotIn('off_pending', chips, 'no pending layer: nothing on the canvas stands for one')
            self.assertEqual(0, chips['off_messages']['messages'])
            self.assertEqual(0, chips['off_events']['events'])
            self.assertEqual('false', chips['off_generators']['pressed'])
            self.assertEqual(on['located'], chips['restored']['located'], 'the chips restore')
            self.assertEqual([PRICES_OFF_FILL] * len(LOCATED), chips['off_prices']['fills'])
            # the scope: Luzon only leaves Luzon's two located sites and no unplaced row
            self.assertEqual(['SYN-CALACA-1', 'SYN-LUZ-1'], chips['scopeLuzon']['located'])
            self.assertEqual(0, chips['scopeLuzon']['pending'])
            self.assertEqual('true', chips['scopeLuzon']['pressed'])
            self.assertEqual('false', chips['scopeLuzon']['all'])
            self.assertEqual(len(LOCATED), len(chips['scopeAll']))
            self.assertEqual(len(generators) + len(loads), len(LOCATED))

    def test_an_unpriced_clock_says_so_and_draws_every_dot_unknown(self):
        for report in (self.look, self.phone):
            clocks = report['clocks']
            self.assertTrue(clocks['at1340']['priced'])
            # 14:00 is the same day, out of the price spike: priced, different fills
            self.assertTrue(clocks['at1400']['priced'])
            self.assertNotEqual(sorted(clocks['at1340']['fills']), sorted(clocks['at1400']['fills']))
            # the trip names a site with no position: it stands at its grid, not in these lists
            self.assertEqual(['SYN-ADV-0008'], clocks['at1400']['messages'])
            self.assertEqual([], clocks['at1400']['events'])
            # 22 September is not in the one baked node day: every dot unknown, the legend says so
            # and states no domain (a ramp over grey dots would claim one)
            self.assertFalse(clocks['atSep22']['priced'])
            self.assertTrue(clocks['atSep22']['allUnknown'])
            self.assertEqual(0, clocks['atSep22']['messages'])
            self.assertEqual(0, clocks['atSep22']['events'])
            self.assertIn('No price for 2026-09-22 07:30 in the node file', clocks['atSep22']['legendRange'])
            self.assertIn('2026-09-21', clocks['atSep22']['legendRange'])
            self.assertEqual([], clocks['atSep22']['legendTicks'], 'no price, no domain')
            self.assertEqual(CLOCK, clocks['back']['clock'])

    def test_the_modules_math_agrees_with_this_files_re_derivation(self):
        # the harness computes its math block against one fixed 1280x700 transform whatever the
        # run width, so `maths` below is compared with that transform in both runs
        for report in (self.look, self.phone):
            maths = report['math']
            t = fit_transform(1280, 700)
            self.assertAlmostEqual(maths['fit1280x700']['k'], t['k'], places=8)
            self.assertAlmostEqual(maths['fit390x585']['k'], fit_transform(390, 585)['k'], places=8)
            # the anchor: the world point under the pointer is unchanged by a zoom
            self.assertEqual(maths['anchor']['before'], maths['anchor']['after'])
            before = world_of(t, 420, 260)
            self.assertAlmostEqual(maths['anchor']['before'][0], round(before[0], 9), places=8)
            self.assertAlmostEqual(maths['anchor']['before'][1], round(before[1], 9), places=8)
            # the pinch anchor: the module's own pair puts the previous midpoint's world point
            # under the new midpoint, and that point is this file's world_of of the same pair
            pinch = maths['pinchAnchor']
            prev, nxt = {'d': 100.0, 'mid': (350.0, 300.0)}, {'d': 200.0, 'mid': (325.0, 300.0)}
            self.assertEqual(pinch['was'], pinch['now'])
            was = world_of(t, prev['mid'][0], prev['mid'][1])
            self.assertAlmostEqual(pinch['was'][0], round(was[0], 9), places=8)
            self.assertAlmostEqual(pinch['was'][1], round(was[1], 9), places=8)
            self.assertAlmostEqual(pinch['k'], pinch_transform(t, prev, nxt)['k'], places=8)
            # the pointer bookkeeping: the module's own dragDown/dragUp, the same inputs
            d = maths['drag']
            first = drag_down(None, (300.0, 300.0), 1)
            self.assertEqual(first, d['afterFirstDown'])
            second = drag_down(first, (400.0, 300.0), 2)
            self.assertEqual(second, d['afterSecondDown'])
            self.assertEqual(DRAG_CLICK_PX, second['moved'], 'two pointers are never a click')
            self.assertEqual(drag_up(second, (450.0, 300.0)), d['afterLift'])
            self.assertIsNone(d['liftedWithNoSurvivor'])
            self.assertEqual(drag_down({'x': 100, 'y': 100, 'moved': 20, 'last': {'x': 100, 'y': 100}},
                                       (150.0, 150.0), 2), d['dragKeptAcrossASecondPointer'])
            # the congestion and flow readers: the same inputs, the same tri-state
            c = maths['congestion']
            self.assertEqual([True, True], c['atClock'])
            self.assertEqual([False, None], c['at1400'])
            self.assertIs(True, c['knownTrue'])
            self.assertIs(False, c['knownFalse'])
            for key in ('nullFlag', 'shortFlags', 'noFlags', 'noLink', 'noInterval'):
                self.assertIsNone(c[key], key)
            unknowns = sorted(f'{name}@{HVDC["t"][i]}' for name in ('MINVIS1', 'VISLUZ1')
                              for i in range(len(HVDC['t'])) if congestion_at(HVDC['links'][name], i) is None)
            self.assertEqual(unknowns, c['fixtureUnknowns'],
                             'the module reads the fixture\'s own unstated cells as unknown')
            f = maths['flow']
            self.assertEqual(0, f['zero'])
            for key in ('nullCell', 'shortList', 'noList', 'noLink', 'noInterval'):
                self.assertIsNone(f[key], key)
            # the round trip through the transform
            world = plane(121.0, 14.6)
            screen = to_screen(t, world)
            self.assertEqual(maths['roundTrip']['world'], [round(world[0], 9), round(world[1], 9)])
            self.assertEqual(maths['roundTrip']['screen'], [round(screen[0], 9), round(screen[1], 9)])
            self.assertEqual(maths['roundTrip']['world'], maths['roundTrip']['back'])
            # hit testing re-derived, and the unlocated sites listed apart
            self.assertEqual(['SYN-LUZ-1'], maths['siteAtLuzon'])
            x, y = to_screen(t, plane(*STACKED))
            self.assertEqual([h['code'] for h in site_at(t, SITES, x, y)], maths['siteAtStack'])
            ordered = sorted(PLACEHOLDERS, key=lambda s: (s['g'], -(s['cap'] or 0), s['s']))
            self.assertEqual([s['s'] for s in ordered], maths['unplacedCodes'])
            self.assertEqual([], maths['unplacedLuzon'])
            self.assertEqual(['sites', 'link'], maths['hitKeys'])
            self.assertEqual('MINVIS1', maths['linkAtMid'])
            self.assertIsNone(maths['linkAtFar'])
            for entry in maths['radiusOf']:
                site = [s for s in SITES if s['s'] == entry['code']][0]
                self.assertAlmostEqual(radius_of(site), entry['r'], places=8, msg=entry['code'])
            # UX-3: the price scale, OKLab included, and the clustering are this file's arithmetic
            sc = maths['scaleAtClock']
            want = price_scale(drawn_value_at_clock(LOCATED))
            for got, knot in zip(sc['knots'], want['knots']):
                self.assertAlmostEqual(got, knot, places=6)
            self.assertEqual([tick_label(v) for v in want['knots']], sc['ticks'])
            self.assertEqual(want['atCeil'], sc['atCeil'])
            for value, colour in sc['colours']:
                self.assertTrue(colour_close(color_at(want, value), colour), (value, colour))
            self.assertEqual(price_scale([4000, 4000, 4000])['knots'], maths['scales']['flat'])
            self.assertEqual(price_scale([32000] * 4 + [50000])['knots'], maths['scales']['capped'])
            self.assertEqual(price_scale([-2000, -500, 100, 300, 900, 1500])['knots'], maths['scales']['negative'])
            self.assertIsNone(maths['scales']['empty'])
            mixes = [(P_DARK[2], P_DARK[3], 0.5), (P_DARK[0], P_DARK[4], 0.25), (P_DARK[1], P_DARK[2], 0.8)]
            for got, (a, b, f) in zip(maths['scales']['mix'], mixes):
                self.assertTrue(colour_close(got, mix_oklab(a, b, f)), (got, a, b, f))
            self.assertEqual([p['codes'] for p in cluster_sites(t, SITES)], [c['codes'] for c in maths['clustersFit']])
            # the region names the province layer carries: grid and short label, unknown stays None
            self.assertEqual([('CLUZ', 'Central Luzon'), ('CLUZ', 'CALABARZON'), ('CLUZ', 'MIMAROPA'), ('CVIS', 'Western Visayas'),
                              ('CMIN', 'Caraga'), ('CMIN', 'Northern Mindanao'), ('CLUZ', 'Metro Manila'), ('CLUZ', 'Cordillera'),
                              ('CMIN', 'ARMM'), None, None],
                             [None if r is None else (r['grid'], r['short']) for r in maths['regionInfo']])
            # severity by the advisory's own kind (desk-api.md); a trip that reads as a derating is a warning
            self.assertEqual({'SYN-ADV-0001': 'info', 'SYN-ADV-0005': 'warning', 'SYN-ADV-0002': 'alert', 'SYN-ADV-0003': 'warning',
                              'SYN-ADV-0004': 'info', 'SYN-ADV-0006': 'alert', 'SYN-ADV-0007': 'info', 'SYN-ADV-0008': 'info',
                              'derate': 'warning'}, dict(maths['severity']))
            # the name rule: the event record first, then exactly one token match, never a guess
            named = {entry['id']: (entry['site'], entry['candidates']) for entry in maths['namedBy']}
            self.assertEqual(('SYN-BAY-2', 1), named['SYN-ADV-0002'])
            self.assertEqual(('SYN-CALACA-1', 1), named['SYN-ADV-0008'])
            self.assertEqual((None, 3), named['SYN-ADV-0001'], 'BAY names three sites now: none is selected')
            self.assertEqual((None, 0), named['SYN-ADV-0006'])

    def test_the_text_fallback_carries_the_same_readings_without_a_canvas(self):
        report = self.text
        lines = report['fallback']['lines']
        self.assertIn('canvas is not available', lines[0])
        self.assertIn('Replay 2026-09-21 13:40', lines[0])
        for site in LOCATED:
            row = [line for line in lines if f' {site["s"]} ·' in line]
            self.assertTrue(row, site['s'])
            value = value_of(site)
            self.assertIn('₱{:,}/MWh at 13:40'.format(value), row[0], site['s'])
        for link in ('Leyte–Luzon HVDC', 'Mindanao–Visayas HVDC'):
            rows = [line for line in lines if line.startswith(link)]
            self.assertTrue(rows, link)
            self.assertIn('congested at 13:40', rows[0], link)
        pending = [line for line in lines if 'no position on record' in line][0]
        self.assertIn('2 sites with no position on record', pending)
        self.assertIn('never drawn at a coordinate', pending)
        for site in PLACEHOLDERS:
            self.assertIn(site['s'], pending)
        after = report['fallbackAfterClock']
        self.assertIn('Replay 2026-09-22 07:30', after[0])
        self.assertTrue(any('no price for this day' in line for line in after))
        # the day the link axis does not carry: the fallback says the congestion is unknown, not
        # that the links are not congested
        for link in ('Leyte–Luzon HVDC', 'Mindanao–Visayas HVDC'):
            rows = [line for line in after if line.startswith(link)]
            self.assertTrue(rows, link)
            self.assertIn('congestion unknown at 07:30', rows[0], link)
            self.assertNotIn('not congested', rows[0], link)
        # there is no canvas and no transform: a hit test answers with nothing, never throws
        self.assertEqual({'sites': [], 'link': None}, report['fallbackHit'])

    def observed(self, report, name):
        """The transform the harness recorded for one gesture, as a transform dict."""
        got = report['gestures']['transforms'][name]
        return {'k': got['k'], 'fx': got['fx'], 'fy': got['fy'], 'w': got['w'], 'h': got['h']}


if __name__ == '__main__':
    unittest.main()
