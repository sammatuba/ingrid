"""Formatting, names, severity and the dataset references every desk answer shares."""
import re
import unicodedata
from urllib.parse import quote

from .bake import GRID_NAMES, LINKS

CAP = 32000  # the offer cap the desk's pages name (src/grid/overview.js CAP)
KIND_WORDS = {'G': 'generator', 'NL': 'load node', 'PS': 'pumped storage'}
NOTICE_WORDS = {'trip': 'Trip', 'online': 'Back online', 'red': 'Red alert', 'yellow': 'Yellow alert',
                'mld': 'Load dropping', 'derate': 'Derate', 'notice': 'Notice'}
# Severity, shared with the map and the strip (docs/work/ui-refinement-2026-10-18/desk-api.md).
SEVERITY = {'red': 'alert', 'trip': 'alert', 'yellow': 'warning', 'mld': 'warning', 'derate': 'warning',
            'online': 'info', 'notice': 'info'}
SEVERITY_ORDER = {'alert': 0, 'warning': 1, 'info': 2}
SEVERITY_WORDS = {'alert': 'Alert', 'warning': 'Warning', 'info': 'Information'}
LINK_NAMES = {'VISLUZ1': 'Leyte-Luzon HVDC', 'MINVIS1': 'Mindanao-Visayas HVDC'}
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# The bake's datasets (scripts/grid/catalog.json ids). A bake with its own catalog.json names
# them in its own words; these are the stable fallback when it has none.
DATASETS = {
    'bake-regions': 'Region replay: demand, generation, flows, reserves and price',
    'bake-hvdc': 'Interconnection flow and congestion',
    'bake-nodes': 'Site price and schedule series for one replay day',
    'bake-advisories': 'Operator messages in the replay window',
    'bake-sites': 'Sites in the replay: kind, capacity and position',
    'bake-events': 'Reviewable events',
    'bake-event-views': 'Recorded event views',
}
SHORT = {'bake-regions': 'Regional prices, 5-min', 'bake-hvdc': 'HVDC flow and congestion, 5-min',
         'bake-nodes': 'Location prices and dispatch, 5-min', 'bake-advisories': 'Operator notices',
         'bake-sites': 'Site register', 'bake-events': 'Reviewable events',
         'bake-event-views': 'Recorded event views'}
PAGES = (('/', 'Dashboard'), ('/alerts', 'Alerts'), ('/notices', 'Notices'), ('/plants', 'Plants'),
         ('/journal', 'Journal'), ('/data', 'Data catalog'), ('/paper', 'Research paper'),
         ('/explain', 'How it works'), ('/outlooks', 'Outlooks'), ('/models', 'Models'),
         ('/work', 'Who did the work'), ('/map', 'Project map'), ('/register', 'Assumption register'),
         ('/ask', 'Ask the desk'), ('/book', 'Book'), ('/settings', 'Settings'))
BASIS = 'Composed from the baked records at the replay clock. No model call.'


def fold(text):
    """Lower case, accents removed: the form every match is made in."""
    decomposed = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).lower()


def fmt(value):
    """A figure as the desk prints it: thousands separated, whole above 100, one decimal below."""
    if value is None:
        return None
    if abs(value) >= 100 or float(value).is_integer():
        whole = int(round(value))
        return f'{whole:,}' if whole else '0'
    return f'{value:,.1f}'


def peso(value):
    return None if value is None else f'₱{fmt(value)}/MWh'


def mw(value):
    return None if value is None else f'{fmt(value)} MW'


def hhmm(t, at=None):
    """`13:40` on the clock's own day, `20 Sep 13:40` on another."""
    if at is not None and t[:10] == at[:10]:
        return t[11:16]
    return day_words(t) + ' ' + t[11:16]


def day_words(t):
    return f'{int(t[8:10])} {MONTHS[int(t[5:7]) - 1]}'


def severity_of(kind):
    return SEVERITY.get(str(kind or '').lower(), 'info')


def site_tokens(code):
    """The page's naming rule (src/grid/grid.js siteTokens): letter groups of three or more."""
    return [t.upper() for t in re.findall(r'[A-Za-z]{3,}', str(code))]


def mentions(text, tokens):
    up = str(text).upper()
    return any(re.search(r'(^|[^A-Z])' + re.escape(t) + r'($|[^A-Z])', up) for t in tokens)


def site_title(site):
    return site['name'] or site['s']


def site_subtitle(site):
    parts = [GRID_NAMES.get(site['g']) or 'Grid not stated', KIND_WORDS.get(site['k'], site['k'] or 'site')]
    if site['cap'] is not None:
        parts.append(f"{fmt(site['cap'])} MW")
    return ' · '.join(parts)


def notice_title(a):
    return f"{NOTICE_WORDS.get(a['kind'], a['kind'].capitalize() or 'Notice')} notice {a['id']}".strip()


def href(kind, ident, at=None):
    if kind == 'plant':
        return '/plant/' + quote(ident, safe='')
    if kind == 'event':
        return '/event/' + quote(ident, safe='')
    if kind == 'region':
        return '/?grid=' + quote(ident, safe='')
    if kind == 'link':
        return '/?link=' + quote(ident, safe='')
    if kind == 'notice':
        return '/notices' + (f'?at={at}' if at else '') + '#adv-' + quote(ident, safe='')
    if kind == 'dataset':
        return '/data#' + quote(ident, safe='')
    return ident


def link_direction(link, flow):
    """`(from, to)` grid names for a signed flow (positive is the first grid to the second)."""
    a, b = LINKS[link]
    if flow is None or flow == 0:
        return None
    return (GRID_NAMES[a], GRID_NAMES[b]) if flow > 0 else (GRID_NAMES[b], GRID_NAMES[a])


def dataset_title(bake, dataset_id):
    entry = bake.catalog().get(dataset_id)
    return entry['name'] if entry else DATASETS.get(dataset_id, dataset_id)


def source(bake, dataset_id):
    return {'dataset_id': dataset_id, 'title': dataset_title(bake, dataset_id), 'href': href('dataset', dataset_id)}
