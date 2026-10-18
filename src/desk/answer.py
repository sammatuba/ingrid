"""`/api/desk/answer` and `/api/desk/prompts`: deterministic answers composed from the baked records.

Every answer is built from the bake at the replay clock and nothing else: no model is called, no
figure is invented, and a value the records do not hold is said to be not on record. Each figure in
the prose is a `num` part that cites a numbered citation whose `table` shows the same formatted
figure. The trace names the ontology steps (docs/architecture/ontology-profile-v1.md): the entity
resolved and its type, the relation followed (`locatedIn`, `connects`, `refersTo`), the dataset
read and the rows it gave. Records near a price are shown as records; no cause is claimed (the
profile has no `causes` relation).
"""
import re
import statistics

from .bake import GRID_NAMES, GRIDS, LINKS, number, shift
from .search import _link_value, event_severity
from .words import (BASIS, CAP, KIND_WORDS, LINK_NAMES, SEVERITY_ORDER, SEVERITY_WORDS, SHORT,
                    dataset_title, fold, fmt, hhmm, href, link_direction, mentions, mw, notice_title, peso,
                    severity_of, site_title, site_tokens)

NEAR_MINUTES = 120  # "in the two hours to" the clock
RECENT_MINUTES = 6 * 60
PLANT_MINUTES = 24 * 60
STATE_LOOKBACK_MINUTES = 3 * 24 * 60
TOP_LOCATIONS = 5
UNUSUAL_LOCATIONS = 8
MAX_QUESTION = 500
GRID_WORDS = {'luzon': 'CLUZ', 'cluz': 'CLUZ', 'visayas': 'CVIS', 'visaya': 'CVIS', 'cvis': 'CVIS',
              'mindanao': 'CMIN', 'cmin': 'CMIN'}
PROMPT_GRID = {'luzon': 'CLUZ', 'visayas': 'CVIS', 'mindanao': 'CMIN'}
# Generic words a plant name carries that name no particular plant.
NAME_STOPWORDS = frozenset({'synthetic', 'power', 'plant', 'station', 'energy', 'unit', 'units', 'grid',
                            'corporation', 'corp', 'inc', 'the', 'and', 'of', 'solar', 'wind', 'hydro', 'coal',
                            'geothermal', 'diesel', 'thermal', 'gas', 'oil', 'biomass', 'battery', 'combined',
                            'cycle', 'pumped', 'storage', 'node', 'load', 'sample', 'project', 'farm', 'city'})


class NotAnswerable(Exception):
    pass


class Composer:
    """One answer under construction: blocks, citations, entities and the trace."""

    def __init__(self, bake, at, question, intent):
        self.bake, self.at, self.question, self.intent = bake, at, question, intent
        self.trace, self.blocks, self.citations, self.followups = [], [], [], []
        self._entities = {}
        self.rows = {}  # citation n -> its rows with the entity parts kept (a table block rebuilt from it)
        self.substantive = False

    # parts
    def text(self, value):
        return {'t': 'text', 'v': value}

    def num(self, value, display, cite):
        return {'t': 'num', 'v': display, 'n': value, 'cite': list(cite)}

    def entity(self, kind, ident, label, at=None):
        key = (kind, ident)
        if key not in self._entities:
            self._entities[key] = {'kind': kind, 'id': ident, 'label': label, 'href': href(kind, ident, at)}
        return {'t': 'entity', 'kind': kind, 'id': ident, 'label': label}

    def p(self, *parts):
        merged = []
        for part in parts:
            if isinstance(part, str):
                part = self.text(part)
            if part['t'] == 'text' and merged and merged[-1]['t'] == 'text':
                merged[-1] = self.text(merged[-1]['v'] + part['v'])
            else:
                merged.append(part)
        self.blocks.append({'type': 'p', 'parts': merged})

    def table(self, caption, columns, rows, cite):
        self.blocks.append({'type': 'table', 'caption': caption, 'columns': columns, 'rows': rows,
                            'cite': list(cite)})

    def cite(self, dataset_id, filter_words, columns, rows, at=None):
        n = len(self.citations) + 1
        plain = [[cell['label'] if isinstance(cell, dict) else cell for cell in row] for row in rows]
        self.rows[n] = rows
        self.citations.append({'n': n, 'dataset_id': dataset_id, 'title': dataset_title(self.bake, dataset_id),
                               'at': at or self.at, 'filter': filter_words, 'href': href('dataset', dataset_id),
                               'table': {'columns': columns, 'rows': plain}})
        return n

    def step(self, op, label, **fields):
        entry = {'op': op, 'label': label}
        entry.update({k: v for k, v in fields.items() if v is not None})
        self.trace.append(entry)

    def read(self, dataset_id, rows):
        self.step('read', SHORT.get(dataset_id, dataset_title(self.bake, dataset_id)), dataset_id=dataset_id, rows=rows)

    def result(self):
        return {'status': 'answered', 'question': self.question, 'at': self.at, 'intent': self.intent,
                'trace': self.trace, 'blocks': self.blocks, 'citations': self.citations,
                'entities': list(self._entities.values()), 'followups': self.followups, 'basis': BASIS}


# ------------------------------------------------------------------------------- shared reads

def _grid(payload, i, grid, field):
    series = ((payload or {}).get('grids') or {}).get(grid, {}).get(field)
    return number(series[i]) if series and i is not None and i < len(series) else None


def _usual(payload, i, grid):
    """`(usual, earlier days)` for the interval's clock hour, `(None, 0)` when none is on record."""
    if not payload or i is None:
        return None, 0
    pair = ((payload.get('usual') or {}).get(grid) or {}).get(payload['t'][i][11:13])
    if isinstance(pair, list) and len(pair) == 2 and number(pair[0]) is not None and type(pair[1]) is int:
        return pair[0], pair[1]
    return None, 0


def _notice_row(c, a, at):
    return [a['t'][11:16] if a['t'][:10] == at[:10] else hhmm(a['t'], at),
            c.entity('notice', a['id'], notice_title(a), a['t']),
            SEVERITY_WORDS[severity_of(a['kind'])], a['text']]


def _event_row(c, e, at):
    advisory = c.bake.advisory(e['advisory'], at) if e.get('advisory') else None
    return [hhmm(e['t'], at), c.entity('event', e['id'], e['title']),
            SEVERITY_WORDS[event_severity(c.bake, e, at)],
            advisory['text'] if advisory else (e['assumption'] or '')]


def _apart(notices, events):
    """The notices that are not an event's own advisory (the event's row stands for it)."""
    carried = {e['advisory'] for e in events if e.get('advisory')}
    return [a for a in notices if a['id'] not in carried]


def _events_between(bake, start, end, grid=None, site=None):
    out = []
    for e in bake.events():
        if not (start < e['t'] <= end):
            continue
        if grid is not None and bake.event_grid(e) != grid:
            continue
        if site is not None and e['site'] != site:
            continue
        out.append(e)
    return out


def _records_table(c, notices, events, caption):
    """The notices and events as one table, newest first, with its citation."""
    at = c.at
    rows = sorted([(e['t'], _event_row(c, e, at)) for e in events] + [(a['t'], _notice_row(c, a, at)) for a in notices],
                  key=lambda x: x[0], reverse=True)
    rows = [row for _, row in rows]
    columns = ['Time', 'Record', 'Severity', 'Text']
    dataset = 'bake-advisories' if notices or not events else 'bake-events'
    n = c.cite(dataset, caption, columns, rows)
    c.table(caption, columns, rows, [n])
    return n


def _where(c, payload, i):
    """The interval the answer reads, as words."""
    return hhmm(payload['t'][i], c.at)


def _top_followups(c, exclude):
    for prompt in prompts(c.bake, c.at, limit=5):
        if prompt['id'] != exclude and len(c.followups) < 3:
            c.followups.append({'text': prompt['text'], 'prompt_id': prompt['id']})


# ------------------------------------------------------------------------------- the intents

def region_price_why(c, grid):
    bake, at, name = c.bake, c.at, GRID_NAMES[grid]
    c.step('resolve', name, entity={'kind': 'region', 'id': grid}, type='Region')
    region = c.entity('region', grid, name)
    payload, i = bake.interval(at)
    price = _grid(payload, i, grid, 'lmp_median')
    if price is None:
        c.read('bake-regions', 0)
        c.p(f'No price is on record for {name} at {hhmm(at, at)}.')
        return
    c.substantive = True
    t = payload['t'][i]
    when = _where(c, payload, i)
    c.read('bake-regions', i + 1)
    top = _grid(payload, i, grid, 'lmp_max')
    usual, days = _usual(payload, i, grid)
    hour = t[11:13] + ':00'
    row = [when, fmt(price), fmt(top) if top is not None else 'Not on record',
           fmt(usual) if usual is not None else 'Not on record', str(days)]
    n1 = c.cite('bake-regions', f'grid = {name}, interval = {when}',
                ['Interval', 'Median ₱/MWh', 'Max ₱/MWh', f'Usual for {hour} ₱/MWh', 'Earlier days'], [row], at=t)
    first = [region, ' cleared at a median of ', c.num(price, peso(price), [n1]), f' at {when}.']
    if price >= CAP:
        first.append(' That is the offer cap.')
    c.p(*first)
    if usual is not None:
        c.step('compare', f'Against the usual for {hour} over {days} earlier days')
        word = 'above' if price > usual * 1.1 else 'below' if price < usual * 0.9 else 'close to'
        c.p(f'The usual for {hour} is ', c.num(usual, peso(usual), [n1]), ' over ',
            c.num(days, str(days), [n1]), f' earlier days. The price is {word} its usual.')
    else:
        c.step('compare', f'No usual for {hour} yet: no earlier day on record')
        c.p(f'No usual price is on record for {hour} yet. The replay holds no earlier day.')
    # the links that connect this grid
    links = [link for link, pair in LINKS.items() if grid in pair]
    c.step('relate', f'HVDC links connecting {name}', relation='connects', rows=len(links), type='NetworkElement')
    c.read('bake-hvdc', len(links))
    rows, sentences = [], []
    for link in links:
        flow = _link_value(payload, i, link, 'flow')
        flag = _link_value(payload, i, link, 'congested')
        way = link_direction(link, flow)
        rows.append([link, when, fmt(abs(flow)) if flow is not None else 'Not on record',
                     f'{way[0]} to {way[1]}' if way else ('No flow' if flow == 0 else 'Not on record'),
                     'Yes' if flag == 1 else 'No' if flag == 0 else 'Not on record'])
        sentences.append((link, flow, flag, way))
    n2 = c.cite('bake-hvdc', f'links connecting {name}, interval = {when}',
                ['Link', 'Interval', 'Flow MW', 'Direction', 'Congested'], rows, at=t)
    for link, flow, flag, way in sentences:
        _link_sentence(c, link, flow, flag, way, when, n2)
    # notices and events that refer to this grid
    start = shift(at, -NEAR_MINUTES)
    notices = [a for a in bake.advisories(start, at) if a['grid'] == grid]
    events = _events_between(bake, start, at, grid=grid)
    notices = _apart(notices, events)
    c.step('relate', f'Notices and events referring to {name}, last 2 h', relation='refersTo',
           rows=len(notices) + len(events), type='Evidence')
    if notices or events:
        c.read('bake-advisories', len(notices))
        lead = _lead_record(c, notices, events)
        if lead:
            c.p(*lead)
        c.p(f'These notices and events refer to {name} in the two hours to {hhmm(at, at)}.')
        _records_table(c, notices, events, f'Notices and events for {name}, two hours to {hhmm(at, at)}')
        c.p('They are on record near the price. The desk does not claim a cause.')
    else:
        c.p(f'No notice or event for {name} is on record in the two hours to {hhmm(at, at)}.')
    # the plants located in this grid and their prices
    located = [s for s in bake.sites() if s['g'] == grid]
    c.step('relate', f'Plants located in {name}', relation='locatedIn', rows=len(located), type='Plant')
    nodes, r = bake.node_interval(at)
    priced = []
    if nodes:
        for s in located:
            value = bake.node_value(nodes, r, s['s'])
            if value is not None:
                priced.append((value, s, bake.node_value(nodes, r, s['s'], 'mw')))
    if not priced:
        c.p(f'No location prices for {name} are on record at {hhmm(at, at)}.')
        return
    c.read('bake-nodes', len(priced))
    priced.sort(key=lambda x: (-x[0], x[1]['s']))
    node_when = hhmm(nodes['t'][r], at)
    rows = [[c.entity('plant', s['s'], site_title(s)), fmt(v), fmt(d) if d is not None else 'Not on record']
            for v, s, d in priced[:TOP_LOCATIONS]]
    caption = f'Highest-priced {name} locations at {node_when}'
    n4 = c.cite('bake-nodes', f'grid = {name}, interval = {node_when}, highest price first',
                ['Location', 'Price ₱/MWh', 'Dispatch MW'], rows, at=nodes['t'][r])
    best_value, best, _ = priced[0]
    c.p('The highest-priced location was ', c.entity('plant', best['s'], site_title(best)), ' at ',
        c.num(best_value, peso(best_value), [n4]), f' at {node_when}.')
    c.table(caption, ['Location', 'Price ₱/MWh', 'Dispatch MW'], rows, [n4])


def _lead_record(c, notices, events):
    """The parts of one sentence naming the newest, most severe record: an event before a notice."""
    at = c.at
    ranked = sorted([(SEVERITY_ORDER[event_severity(c.bake, e, at)], 0, _desc(e['t']), 'event', e) for e in events]
                    + [(SEVERITY_ORDER[severity_of(a['kind'])], 1, _desc(a['t']), 'notice', a) for a in notices],
                    key=lambda x: x[:3])
    if not ranked:
        return None
    severity, _, _, kind, record = ranked[0]
    word = SEVERITY_WORDS[[k for k, v in SEVERITY_ORDER.items() if v == severity][0]].lower()
    if kind == 'event':
        part = c.entity('event', record['id'], record['title'])
    else:
        part = c.entity('notice', record['id'], notice_title(record), record['t'])
    article = 'an' if word[0] in 'aeiou' else 'a'
    return [part, f" is on record at {hhmm(record['t'], at)}, {article} {word}."]


def _link_sentence(c, link, flow, flag, way, when, n):
    label = c.entity('link', link, LINK_NAMES[link])
    if flow is None:
        c.p('No flow is on record for ', label, f' at {when}.')
    elif way is None:
        c.p(label, f' carried no flow at {when}.')
    else:
        c.p(label, ' carried ', c.num(abs(flow), mw(abs(flow)), [n]), f' from {way[0]} to {way[1]} at {when}.')
    if flag is None:
        c.p(f'No congestion flag is on record for {link} at {when}.')
    else:
        c.p(f'It was {"congested" if flag == 1 else "not congested"} at {when}.')


def unusual_nodes(c):
    bake, at = c.bake, c.at
    c.step('resolve', 'Every priced location', type='MarketResource')
    nodes, r = bake.node_interval(at)
    payload, i = bake.interval(at)
    if not nodes or not payload:
        c.p(f'No location prices are on record at {hhmm(at, at)}.')
        return
    node_t = nodes['t'][r]
    if payload['t'][i] != node_t:
        c.p(f'No grid median is on record for {hhmm(node_t, at)}.')
        return
    when = hhmm(node_t, at)
    medians = {g: _grid(payload, i, g, 'lmp_median') for g in GRIDS}
    gaps = []
    for code in nodes['sites']:
        site = bake.site(code)
        if not site or site['g'] is None or medians.get(site['g']) is None:
            continue
        value = bake.node_value(nodes, r, code)
        if value is None:
            continue
        gaps.append((value - medians[site['g']], value, site, bake.node_value(nodes, r, code, 'mw')))
    c.step('relate', 'Locations by grid', relation='locatedIn', rows=len(gaps), type='Region')
    c.read('bake-nodes', len(gaps))
    c.read('bake-regions', 3)
    gaps = [g for g in gaps if g[0] != 0]
    if not gaps:
        c.p(f'Every priced location matched its grid median at {when}.')
        return
    c.substantive = True
    gaps.sort(key=lambda g: (-abs(g[0]), g[2]['s']))
    shown = gaps[:UNUSUAL_LOCATIONS]
    c.step('compare', f'Each location against its grid median at {when}')
    med_rows = [[GRID_NAMES[g], when, fmt(medians[g]) if medians[g] is not None else 'Not on record'] for g in GRIDS]
    n2 = c.cite('bake-regions', f'interval = {when}, the three grid medians', ['Grid', 'Interval', 'Median ₱/MWh'],
                med_rows, at=node_t)
    columns = ['Location', 'Grid', 'Price ₱/MWh', 'Gap to grid median ₱/MWh', 'Dispatch MW']
    rows = [[c.entity('plant', s['s'], site_title(s)), GRID_NAMES[s['g']], fmt(v),
             ('+' if gap > 0 else '') + fmt(gap), fmt(d) if d is not None else 'Not on record']
            for gap, v, s, d in shown]
    n1 = c.cite('bake-nodes', f'interval = {when}, the locations furthest from their grid median', columns, rows,
                at=node_t)
    gap, value, site, _ = shown[0]
    grid = site['g']
    c.p(c.entity('plant', site['s'], site_title(site)), f' was furthest from its grid median at {when}.')
    c.p('It cleared at ', c.num(value, peso(value), [n1]), f' against a {GRID_NAMES[grid]} median of ',
        c.num(medians[grid], peso(medians[grid]), [n2]), '.')
    c.table(f'Locations furthest from their grid median at {when}', columns, rows, [n1, n2])
    # what the records say near them
    start = shift(at, -NEAR_MINUTES)
    codes = {s['s'] for _, _, s, _ in shown}
    via = {e['advisory'] for e in bake.events() if e['site'] in codes and e['t'] <= at}
    named = [a for a in bake.advisories(start, at)
             if a['id'] in via or any(mentions(a['text'], site_tokens(code)) for code in codes)]
    events = [e for e in _events_between(bake, start, at) if e['site'] in codes]
    named = _apart(named, events)
    c.step('relate', 'Notices and events naming those locations, last 2 h', relation='refersTo',
           rows=len(named) + len(events), type='Evidence')
    if named or events:
        c.read('bake-advisories', len(named))
        c.p(f'These notices and events name those locations in the two hours to {hhmm(at, at)}.')
        _records_table(c, named, events, f'Records naming those locations, two hours to {hhmm(at, at)}')
        c.p('They are on record nearby. The desk does not claim a cause.')
    else:
        c.p(f'No notice or event names these locations in the two hours to {hhmm(at, at)}.')


def hvdc_congestion(c):
    bake, at = c.bake, c.at
    for link, (a, b) in LINKS.items():
        c.step('resolve', LINK_NAMES[link], entity={'kind': 'link', 'id': link}, type='NetworkElement')
        c.step('relate', f'{link} connects {GRID_NAMES[a]} and {GRID_NAMES[b]}', relation='connects', rows=2,
               type='Region')
    payload, i = bake.interval(at)
    if not payload:
        c.read('bake-hvdc', 0)
        c.p(f'No HVDC flow is on record at {hhmm(at, at)}.')
        return
    t = payload['t'][i]
    when = hhmm(t, at)
    times, _ = bake.series(shift(t, -STATE_LOOKBACK_MINUTES), t, lambda p, j: None)
    c.read('bake-hvdc', len(times))
    rows, said = [], []
    for link in LINKS:
        flow = _link_value(payload, i, link, 'flow')
        flag = _link_value(payload, i, link, 'congested')
        way = link_direction(link, flow)
        since, bounded = _state_since(bake, link, t, flag)
        if flow is not None or flag is not None:
            c.substantive = True
        rows.append([link, when, fmt(abs(flow)) if flow is not None else 'Not on record',
                     f'{way[0]} to {way[1]}' if way else ('No flow' if flow == 0 else 'Not on record'),
                     'Yes' if flag == 1 else 'No' if flag == 0 else 'Not on record',
                     (hhmm(since, at) if bounded else 'before ' + hhmm(since, at)) if since else 'Not on record'])
        said.append((link, flow, flag, way, since, bounded))
    n = c.cite('bake-hvdc', f'both links, interval = {when}',
               ['Link', 'Interval', 'Flow MW', 'Direction', 'Congested', 'State since'], rows, at=t)
    c.step('compare', 'Each link\'s congested state, traced back to where it last changed')
    for link, flow, flag, way, since, bounded in said:
        _link_sentence(c, link, flow, flag, way, when, n)
        if flag is not None and since:
            state = 'congested' if flag == 1 else 'uncongested'
            if bounded:
                c.p(f'It has been {state} since {hhmm(since, at)}.')
            else:
                c.p(f'It has been {state} since before {hhmm(since, at)}, the earliest interval read.')
    c.table(f'HVDC links at {when}', ['Link', 'Interval', 'Flow MW', 'Direction', 'Congested', 'State since'],
            rows, [n])


def _state_since(bake, link, t, flag):
    """`(since, bounded)`: when the link's current congested state began, looking back three days.
    `bounded` is False when the state already held at the earliest interval read."""
    if flag is None:
        return None, False
    times, flags = bake.series(shift(t, -STATE_LOOKBACK_MINUTES), t, lambda p, j: _link_value(p, j, link, 'congested'))
    if not times:
        return None, False
    since = times[-1]
    for k in range(len(times) - 1, -1, -1):
        if flags[k] != flag:
            return since, True
        since = times[k]
    return since, False


def plant_status(c, code):
    bake, at = c.bake, c.at
    site = bake.site(code)
    title = site_title(site)
    c.step('resolve', title, entity={'kind': 'plant', 'id': code}, type='Plant')
    plant = c.entity('plant', code, title)
    c.read('bake-sites', 1)
    grid = site['g']
    if grid:
        c.step('relate', f'{title} is located in {GRID_NAMES[grid]}', relation='locatedIn', rows=1, type='Region')
        c.entity('region', grid, GRID_NAMES[grid])
    kind = KIND_WORDS.get(site['k'], 'site')
    reg = [code, kind, GRID_NAMES.get(grid) or 'Not stated', fmt(site['cap']) if site['cap'] is not None else 'Not on record']
    n0 = c.cite('bake-sites', f'site = {code}', ['Code', 'Kind', 'Grid', 'Registered MW'], [reg])
    where = f' in {GRID_NAMES[grid]}' if grid else ''
    if site['cap'] is not None:
        c.p(plant, f' is a {kind}{where} with ', c.num(site['cap'], mw(site['cap']), [n0]), ' registered.')
    else:
        c.p(plant, f' is a {kind}{where}. No registered capacity is on record.')
    nodes, r = bake.node_interval(at)
    price = bake.node_value(nodes, r, code) if nodes else None
    dispatch = bake.node_value(nodes, r, code, 'mw') if nodes else None
    if nodes and code in nodes['col']:
        when = hhmm(nodes['t'][r], at)
        c.read('bake-nodes', 1)
        n1 = c.cite('bake-nodes', f'site = {code}, interval = {when}', ['Location', 'Interval', 'Price ₱/MWh', 'Dispatch MW'],
                    [[title, when, fmt(price) if price is not None else 'Not on record',
                      fmt(dispatch) if dispatch is not None else 'Not on record']], at=nodes['t'][r])
        if price is not None:
            c.substantive = True
            c.p('It cleared at ', c.num(price, peso(price), [n1]), f' at {when}.')
        else:
            c.p(f'No price is on record for it at {when}.')
        if dispatch is not None:
            c.p('Its dispatch was ', c.num(dispatch, mw(dispatch), [n1]), f' at {when}.')
        else:
            c.p(f'No dispatch is on record for it at {when}.')
    else:
        c.read('bake-nodes', 0)
        c.p(f'No price or dispatch is on record for it at {hhmm(at, at)}.')
    start = shift(at, -PLANT_MINUTES)
    via = {e['advisory'] for e in bake.events() if e['site'] == code and e['t'] <= at}
    named = [a for a in bake.advisories(start, at) if a['id'] in via or mentions(a['text'], site_tokens(code))]
    events = _events_between(bake, start, at, site=code)
    named = _apart(named, events)
    c.step('relate', f'Notices and events referring to {title}, last 24 h', relation='refersTo',
           rows=len(named) + len(events), type='Evidence')
    if named or events:
        c.substantive = True
        c.read('bake-advisories', len(named))
        c.p(f'These notices and events name it in the day to {hhmm(at, at)}.')
        _records_table(c, named, events, f'Records naming {title}, the day to {hhmm(at, at)}')
    else:
        c.p(f'No notice or event names it in the day to {hhmm(at, at)}.')


def recent_events(c, grid=None):
    bake, at = c.bake, c.at
    scope = GRID_NAMES[grid] if grid else 'every grid'
    if grid:
        c.step('resolve', GRID_NAMES[grid], entity={'kind': 'region', 'id': grid}, type='Region')
    start = shift(at, -RECENT_MINUTES)
    notices = [a for a in bake.advisories(start, at) if grid is None or a['grid'] == grid]
    events = _events_between(bake, start, at, grid=grid)
    notices = _apart(notices, events)
    c.read('bake-advisories', len(notices))
    c.read('bake-events', len(events))
    c.step('relate', f'Notices and events referring to {scope}, last 6 h', relation='refersTo',
           rows=len(notices) + len(events), type='Evidence')
    if not notices and not events:
        c.p(f'No notice or event for {scope} is on record in the six hours to {hhmm(at, at)}.')
        return
    c.substantive = True
    counts = {'alert': 0, 'warning': 0, 'info': 0}
    for a in notices:
        counts[severity_of(a['kind'])] += 1
    for e in events:
        counts[event_severity(bake, e, at)] += 1
    n1 = c.cite('bake-advisories', f'{scope}, six hours to {hhmm(at, at)}, by severity', ['Severity', 'Records'],
                [[SEVERITY_WORDS[s], str(counts[s])] for s in ('alert', 'warning', 'info')])
    parts = [f'In the six hours to {hhmm(at, at)}, the records hold ']
    for k, s in enumerate(('alert', 'warning', 'info')):
        word = {'alert': ('alert', 'alerts'), 'warning': ('warning', 'warnings'),
                'info': ('information record', 'information records')}[s][counts[s] != 1]
        parts += [c.num(counts[s], str(counts[s]), [n1]), f' {word}']
        parts.append(', ' if k == 0 else ' and ' if k == 1 else '.')
    c.p(*parts)
    rows = sorted([(SEVERITY_ORDER[event_severity(bake, e, at)], e['t'], _event_row(c, e, at)) for e in events]
                  + [(SEVERITY_ORDER[severity_of(a['kind'])], a['t'], _notice_row(c, a, at)) for a in notices],
                  key=lambda x: (x[0], _desc(x[1])))
    rows = [row for _, _, row in rows]
    columns = ['Time', 'Record', 'Severity', 'Text']
    caption = f'Notices and events for {scope}, six hours to {hhmm(at, at)}, worst first'
    n2 = c.cite('bake-advisories' if notices else 'bake-events', caption, columns, rows)
    c.table(caption, columns, rows, [n2])


def _desc(t):
    return ''.join(chr(0x10FFFF - ord(ch)) for ch in t)


def grid_overview(c):
    bake, at = c.bake, c.at
    for g in GRIDS:
        c.step('resolve', GRID_NAMES[g], entity={'kind': 'region', 'id': g}, type='Region')
    payload, i = bake.interval(at)
    prices = {g: _grid(payload, i, g, 'lmp_median') for g in GRIDS}
    if not payload or all(v is None for v in prices.values()):
        c.read('bake-regions', 0)
        c.p(f'No grid price is on record at {hhmm(at, at)}.')
        return
    c.substantive = True
    t = payload['t'][i]
    when = hhmm(t, at)
    c.read('bake-regions', i + 1)
    columns = ['Grid', 'Interval', 'Median ₱/MWh', 'Usual ₱/MWh', 'Demand MW', 'Reserve shortfall MW', 'Net import MW']
    rows, short = [], []

    def cell(v):
        return fmt(v) if v is not None else 'Not on record'
    for g in GRIDS:
        usual, _ = _usual(payload, i, g)
        imp, exp = _grid(payload, i, g, 'import_mw'), _grid(payload, i, g, 'export_mw')
        net = imp - exp if imp is not None and exp is not None else None
        gap = _grid(payload, i, g, 'dr_short_mw')
        if gap:
            short.append((g, gap))
        rows.append([c.entity('region', g, GRID_NAMES[g]), when, cell(prices[g]), cell(usual),
                     cell(_grid(payload, i, g, 'demand_mw')), cell(gap), cell(net)])
    n = c.cite('bake-regions', f'the three grids, interval = {when}', columns, rows, at=t)
    known = sorted((v, g) for g, v in prices.items() if v is not None)
    hi_v, hi = known[-1]
    c.p(c.entity('region', hi, GRID_NAMES[hi]), ' was the highest-priced grid at ', c.num(hi_v, peso(hi_v), [n]),
        f' at {when}.')
    if len(known) > 1:
        lo_v, lo = known[0]
        c.p(c.entity('region', lo, GRID_NAMES[lo]), ' was the cheapest at ', c.num(lo_v, peso(lo_v), [n]), '.')
    if short:
        for g, gap in short:
            c.p(c.entity('region', g, GRID_NAMES[g]), ' was short of reserve by ', c.num(gap, mw(gap), [n]),
                f' at {when}.')
    elif all(_grid(payload, i, g, 'dr_short_mw') is not None for g in GRIDS):
        c.p(f'No grid was short of reserve at {when}.')
    c.table(f'The three grids at {when}', columns, rows, [n])


INTENTS = {'region_price_why', 'unusual_nodes', 'hvdc_congestion', 'plant_status', 'recent_events', 'grid_overview'}


def compose(bake, at, question, intent, entity=None, with_followups=True):
    c = Composer(bake, at, question, intent)
    if intent == 'region_price_why':
        region_price_why(c, entity)
    elif intent == 'unusual_nodes':
        unusual_nodes(c)
    elif intent == 'hvdc_congestion':
        hvdc_congestion(c)
    elif intent == 'plant_status':
        plant_status(c, entity)
    elif intent == 'recent_events':
        recent_events(c, entity)
    elif intent == 'grid_overview':
        grid_overview(c)
    else:
        raise NotAnswerable(intent)
    if with_followups:
        _top_followups(c, exclude=_prompt_id(intent, entity, bake))
    return c


# ------------------------------------------------------------------------------- matching

def _words(text):
    return re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', fold(text))


def match_plant(bake, text):
    """The one plant the question names, or None (several equally named plants are not guessed)."""
    folded = fold(text)
    words = set(_words(text))
    scores = []
    for site in bake.sites():
        score = 0
        code = site['s'].lower()
        if code in words or re.search(r'(^|[^a-z0-9])' + re.escape(code) + r'($|[^a-z0-9])', folded):
            score = 10
        else:
            name = fold(site['name'] or '')
            if name and len(name) > 5 and name in folded:
                score = 6
            tokens = [t.lower() for t in site_tokens(site['s']) if t.lower() not in NAME_STOPWORDS]
            score += sum(2 for t in tokens if t in words and len(t) >= 4)
            name_words = [w for w in _words(name) if w not in NAME_STOPWORDS and len(w) >= 4]
            score += sum(1 for w in name_words if w in words)
        if score:
            scores.append((score, site['s']))
    if not scores:
        return None
    scores.sort(reverse=True)
    if len(scores) > 1 and scores[1][0] == scores[0][0]:
        return None
    return scores[0][1] if scores[0][0] >= 2 else None


def match_grid(text):
    for word in _words(text):
        if word in GRID_WORDS:
            return GRID_WORDS[word]
    return None


def _has(text, *stems):
    folded = fold(text)
    return any(re.search(r'(^|[^a-z])' + re.escape(stem), folded) for stem in stems)


def match(bake, question):
    """`(intent, entity)` for free text, or `(None, None)`."""
    q = question or ''
    grid = match_grid(q)
    if _has(q, 'unusual', 'outlier', 'odd ', 'abnormal', 'strange', 'furthest', 'spread', 'anomal'):
        return 'unusual_nodes', None
    if _has(q, 'hvdc', 'congest', 'interconnect', 'cable', 'minvis', 'visluz', 'link'):
        return 'hvdc_congestion', None
    plant = match_plant(bake, q)
    if plant:
        return 'plant_status', plant
    if (_has(q, 'cheapest', 'highest', 'lowest', 'most expensive') and
            _has(q, 'node', 'location', 'plant', 'site', 'generator')):
        return 'unusual_nodes', None
    pricey = _has(q, 'price', 'why', 'expensive', 'cheap', 'cost', 'lmp', 'high', 'low', 'spike', 'cap', 'reserve')
    eventy = _has(q, 'event', 'notice', 'trip', 'outage', 'alert', 'happen', 'recent', 'advisor', 'derate',
                  'load dropping', 'news', 'latest')
    if eventy and not (grid and pricey):
        return 'recent_events', grid
    if grid:
        return 'region_price_why', grid
    if pricey or _has(q, 'overview', 'grids', 'compare', 'summary', 'status', 'now', 'cheapest', 'highest'):
        return 'grid_overview', None
    return None, None


# ------------------------------------------------------------------------------- prompts

PROMPT_HINTS = {'region_price_why': 'Region · price · notices', 'unusual_nodes': 'Locations · price · notices',
                'hvdc_congestion': 'HVDC links · flow · congestion', 'recent_events': 'Notices · events · severity',
                'grid_overview': 'Grids · price · reserves', 'plant_status': 'Plant · price · notices'}


def _prompt_id(intent, entity, bake=None):
    if intent == 'region_price_why':
        return f'why-{GRID_NAMES[entity].lower()}-price'
    if intent == 'plant_status':
        return f'plant-{entity}'
    if intent == 'recent_events' and entity:
        return f'recent-events-{GRID_NAMES[entity].lower()}'
    return intent.replace('_', '-') if intent else None


def resolve_prompt(bake, prompt_id):
    """`(intent, entity)` for a prompt id, or `(None, None)` when the id names nothing."""
    pid = str(prompt_id or '')
    m = re.fullmatch(r'why-(luzon|visayas|mindanao)-price', pid)
    if m:
        return 'region_price_why', PROMPT_GRID[m.group(1)]
    m = re.fullmatch(r'recent-events-(luzon|visayas|mindanao)', pid)
    if m:
        return 'recent_events', PROMPT_GRID[m.group(1)]
    m = re.fullmatch(r'plant-(.+)', pid)
    if m and bake.site(m.group(1)):
        return 'plant_status', m.group(1)
    intent = pid.replace('-', '_')
    if intent in ('unusual_nodes', 'hvdc_congestion', 'recent_events', 'grid_overview'):
        return intent, None
    return None, None


def prompts(bake, at, page=None, limit=5):
    """3 to 5 prompts, each with a substantive composed answer at `at`, the most telling first."""
    candidates = []
    payload, i = bake.interval(at)
    # the grid whose price stands out most
    best = None
    for g in GRIDS:
        price = _grid(payload, i, g, 'lmp_median')
        if price is None:
            continue
        usual, _ = _usual(payload, i, g)
        others = [v for v in (_grid(payload, i, o, 'lmp_median') for o in GRIDS if o != g) if v is not None]
        if price >= CAP:
            score = 5.0
        elif usual:
            score = max(price / usual, usual / price if price > 0 else 1.0)
        elif others and statistics.median(others) > 0:
            score = price / statistics.median(others)
        else:
            score = 1.0
        if best is None or score > best[0]:
            best = (score, g, price, usual)
    if best:
        score, g, price, usual = best
        name = GRID_NAMES[g]
        high = price >= CAP or (usual and price > usual * 1.2) or (not usual and score > 1.5)
        low = usual and price < usual * 0.8
        text = (f'Why is {name} so expensive at {hhmm(at, at)}?' if high else
                f'Why is {name} cheap at {hhmm(at, at)}?' if low else f'What sets the {name} price at {hhmm(at, at)}?')
        candidates.append((min(score, 6.0) + 1.0, 'region_price_why', g, text))
    start = shift(at, -NEAR_MINUTES)
    near = bake.advisories(start, at)
    alerts = sum(1 for a in near if severity_of(a['kind']) == 'alert')
    recent = bake.advisories(shift(at, -RECENT_MINUTES), at)
    if recent or _events_between(bake, shift(at, -RECENT_MINUTES), at):
        candidates.append((2.0 + 0.5 * alerts if alerts else 1.1, 'recent_events', None,
                           'What happened on the grid in the last six hours?'))
    congested = any(_link_value(payload, i, link, 'congested') == 1 for link in LINKS)
    candidates.append((2.5 if congested else 0.8, 'hvdc_congestion', None,
                       'Is anything congested on the HVDC links?' if not congested else
                       'Which HVDC link is congested, and since when?'))
    candidates.append((1.5, 'unusual_nodes', None, 'Which locations are furthest from their grid price, and what is near them?'))
    candidates.append((1.0, 'grid_overview', None, 'How do the three grids compare right now?'))
    if page == 'notices':
        candidates = [(s + 3 if intent == 'recent_events' else s, intent, e, t) for s, intent, e, t in candidates]
    elif page in ('plants', 'plant'):
        candidates = [(s + 3 if intent == 'unusual_nodes' else s, intent, e, t) for s, intent, e, t in candidates]
    candidates.sort(key=lambda x: -x[0])
    out = []
    for _, intent, entity, text in candidates:
        try:
            c = compose(bake, at, text, intent, entity, with_followups=False)
        except Exception:  # a prompt whose answer cannot be composed is not offered
            continue
        if c.substantive:
            out.append({'id': _prompt_id(intent, entity), 'text': text, 'hint': PROMPT_HINTS[intent]})
        if len(out) >= limit:
            break
    return out


# ------------------------------------------------------------------------------- the route's work

def answer(bake, at, question, prompt_id=None, page=None):
    question = str(question or '')[:MAX_QUESTION]
    intent, entity = (None, None)
    if prompt_id:
        intent, entity = resolve_prompt(bake, prompt_id)
        if intent and not question:
            question = next((p['text'] for p in prompts(bake, at, page) if p['id'] == prompt_id), question)
    if intent is None:
        intent, entity = match(bake, question)
    if intent is None:
        return no_match(bake, at, question, page)
    return compose(bake, at, question, intent, entity).result()


def no_match(bake, at, question, page=None):
    return {'status': 'no_match', 'question': question, 'at': at, 'intent': None, 'trace': [],
            'blocks': [{'type': 'p', 'parts': [{'t': 'text', 'v': (
                'The desk answers from the baked records about grid prices, locations, HVDC links, plants and notices.')}]}],
            'citations': [], 'entities': [],
            'followups': [{'text': p['text'], 'prompt_id': p['id']} for p in prompts(bake, at, page)],
            'basis': BASIS}


__all__ = ['answer', 'prompts', 'match', 'compose', 'INTENTS']
