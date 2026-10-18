"""`/api/desk/search` and `/api/desk/preview`: what the command bar lists and the cards it opens.

Nothing later than the clock is returned: an event or a notice posted after `at` is neither found
nor previewed, and every fact and spark ends at the latest interval at or before `at`.
"""
from .bake import GRID_NAMES, GRIDS, LINKS, number, shift
from .words import (KIND_WORDS, LINK_NAMES, NOTICE_WORDS, PAGES, fold, fmt, hhmm, href, mentions,
                    severity_of, site_subtitle, site_title, site_tokens, source)

KINDS = ('plant', 'event', 'region', 'link', 'notice', 'dataset', 'page')
LABELS = {'plant': 'Plants', 'event': 'Events', 'region': 'Regions', 'link': 'HVDC links',
          'notice': 'Notices', 'dataset': 'Datasets', 'page': 'Pages'}
DEFAULT_LIMIT = 5
MAX_LIMIT = 12
NOTICE_SEARCH_DAYS = 31
DAY_MINUTES = 24 * 60


def _rank(query, fields):
    """0 for a prefix of a field, 1 for a word prefix, 2 for a substring; None for no match."""
    best = None
    for field in fields:
        text = fold(field)
        if not text:
            continue
        if text.startswith(query):
            return 0
        if any(word.startswith(query) for word in text.replace('-', ' ').replace('_', ' ').split()):
            best = 1 if best is None else min(best, 1)
        elif query in text:
            best = 2 if best is None else min(best, 2)
    return best


def _events_known(bake, at):
    return [e for e in bake.events() if e['t'] <= at]


def event_severity(bake, event, at):
    advisory = bake.advisory(event['advisory'], at) if event.get('advisory') else None
    if advisory:
        return severity_of(advisory['kind'])
    view = bake.event_view(event['id'])
    timeline = view.get('timeline') if isinstance(view, dict) else None
    if isinstance(timeline, list) and timeline and isinstance(timeline[0], dict):
        return severity_of(timeline[0].get('kind'))
    return 'info'


def search(bake, q, at, limit=DEFAULT_LIMIT):
    query = fold(q).strip()
    out = {'q': q, 'at': at, 'groups': []}
    if not query:
        return out
    limit = max(1, min(MAX_LIMIT, limit))
    found = {kind: [] for kind in KINDS}
    for site in bake.sites():
        rank = _rank(query, (site['s'], site['name'] or '', KIND_WORDS.get(site['k'], ''), 'plant'))
        if rank is not None:
            found['plant'].append((rank, site['s'], {
                'kind': 'plant', 'id': site['s'], 'title': site_title(site), 'subtitle': site_subtitle(site),
                'href': href('plant', site['s']), 'grid': site['g'], 'badge': None}))
    for event in _events_known(bake, at):
        rank = _rank(query, (event['id'], event['title'], event['site'] or '', 'event'))
        if rank is not None:
            grid = bake.event_grid(event)
            found['event'].append((rank, _newest(event['t']), {
                'kind': 'event', 'id': event['id'], 'title': event['title'],
                'subtitle': ' · '.join(p for p in (GRID_NAMES.get(grid), hhmm(event['t'], at)) if p),
                'href': href('event', event['id']), 'grid': grid, 'badge': event_severity(bake, event, at)}))
    for code in GRIDS:
        rank = _rank(query, (GRID_NAMES[code], code, 'grid', 'region'))
        if rank is not None:
            found['region'].append((rank, code, {
                'kind': 'region', 'id': code, 'title': GRID_NAMES[code], 'subtitle': f'Grid · {code}',
                'href': href('region', code), 'grid': code, 'badge': None}))
    for link, (a, b) in LINKS.items():
        rank = _rank(query, (link, LINK_NAMES[link], GRID_NAMES[a], GRID_NAMES[b], 'hvdc', 'link'))
        if rank is not None:
            found['link'].append((rank, link, {
                'kind': 'link', 'id': link, 'title': LINK_NAMES[link],
                'subtitle': f'HVDC link · {link} · {GRID_NAMES[a]} and {GRID_NAMES[b]}',
                'href': href('link', link), 'grid': None, 'badge': None}))
    for a in reversed(bake.advisories(shift(at, -NOTICE_SEARCH_DAYS * DAY_MINUTES), at)):
        rank = _rank(query, (a['id'], a['text'], NOTICE_WORDS.get(a['kind'], a['kind']), 'notice'))
        if rank is not None:
            found['notice'].append((rank, _newest(a['t']), _notice_item(a, at)))
    for dataset_id, entry in sorted(_datasets(bake).items()):
        rank = _rank(query, (dataset_id, entry['name'], 'dataset'))
        if rank is not None:
            found['dataset'].append((rank, dataset_id, {
                'kind': 'dataset', 'id': dataset_id, 'title': entry['name'], 'subtitle': 'Dataset · ' + dataset_id,
                'href': href('dataset', dataset_id), 'grid': None, 'badge': None}))
    for path, label in PAGES:
        rank = _rank(query, (label, path.strip('/') or 'dashboard', 'page'))
        if rank is not None:
            found['page'].append((rank, label, {
                'kind': 'page', 'id': path, 'title': label, 'subtitle': 'Page · ' + path,
                'href': path, 'grid': None, 'badge': None}))
    for kind in KINDS:
        items = [item for _, _, item in sorted(found[kind], key=lambda x: (x[0], x[1]))[:limit]]
        if items:
            out['groups'].append({'kind': kind, 'label': LABELS[kind], 'items': items})
    return out


def _newest(t):
    """A sort key that puts the newest record first among equal ranks."""
    return ''.join(chr(0x10FFFF - ord(c)) for c in t)


def _notice_item(a, at):
    text = a['text'] if len(a['text']) <= 80 else a['text'][:77].rstrip() + '...'
    return {'kind': 'notice', 'id': a['id'], 'title': text or a['id'],
            'subtitle': ' · '.join(p for p in (GRID_NAMES.get(a['grid']) or 'Grid not stated', hhmm(a['t'], at),
                                                NOTICE_WORDS.get(a['kind'], a['kind'])) if p),
            'href': href('notice', a['id'], a['t']), 'grid': a['grid'], 'badge': severity_of(a['kind'])}


def _datasets(bake):
    from .words import DATASETS
    catalog = bake.catalog()
    if catalog:
        return catalog
    return {key: {'name': name, 'definition': None} for key, name in DATASETS.items()}


# ---------------------------------------------------------------------------------- previews

def preview(bake, kind, ident, at):
    """The card for one entity at the clock, or None when it is unknown (or not yet known)."""
    builder = {'plant': _plant, 'region': _region, 'event': _event, 'notice': _notice, 'link': _link,
               'dataset': _dataset}.get(kind)
    return builder(bake, ident, at) if builder else None


def _spark(label, unit, times, values):
    return {'label': label, 'unit': unit, 't': times, 'v': values}


def _fact(label, value, unit, at):
    return {'label': label, 'value': value, 'unit': unit, 'at': at}


def _plant(bake, code, at):
    site = bake.site(code)
    if site is None:
        return None
    nodes, row = bake.node_interval(at)
    t = nodes['t'][row] if nodes else at
    price = bake.node_value(nodes, row, code) if nodes else None
    dispatch = bake.node_value(nodes, row, code, 'mw') if nodes else None
    start = shift(at, -24 * 60)
    pt, pv = bake.node_series(code, start, at)
    dt, dv = bake.node_series(code, start, at, 'mw')
    named = [a for a in bake.advisories(start, at) if mentions(a['text'], site_tokens(code))]
    via = {e['advisory'] for e in bake.events() if e['site'] == code and e['t'] <= at}
    named += [a for a in bake.advisories(start, at) if a['id'] in via and a not in named]
    named.sort(key=lambda a: a['t'])
    summary = None
    if named:
        last = named[-1]
        summary = f"Latest notice naming it, {hhmm(last['t'], at)}: {last['text']}"
    return {'kind': 'plant', 'id': code, 'title': site_title(site), 'subtitle': site_subtitle(site),
            'href': href('plant', code), 'grid': site['g'],
            'facts': [_fact('Price', price, '₱/MWh', t), _fact('Dispatch', dispatch, 'MW', t)],
            'sparks': [_spark('Price, 24 h', '₱/MWh', pt, pv), _spark('Dispatch, 24 h', 'MW', dt, dv)],
            'summary': summary,
            'sources': [source(bake, 'bake-nodes'), source(bake, 'bake-sites')]
            + ([source(bake, 'bake-advisories')] if named else [])}


def _grid_value(payload, i, grid, field):
    series = ((payload or {}).get('grids') or {}).get(grid, {}).get(field)
    return number(series[i]) if series and i is not None else None


def _region(bake, code, at):
    if code not in GRIDS:
        return None
    payload, i = bake.interval(at)
    t = payload['t'][i] if payload else at
    start = shift(at, -24 * 60)
    pt, pv = bake.series(start, at, lambda p, j: _grid_value(p, j, code, 'lmp_median'))
    dt, dv = bake.series(start, at, lambda p, j: _grid_value(p, j, code, 'demand_mw'))
    imp, exp = _grid_value(payload, i, code, 'import_mw'), _grid_value(payload, i, code, 'export_mw')
    net = imp - exp if imp is not None and exp is not None else None
    price = _grid_value(payload, i, code, 'lmp_median')
    summary = None
    if price is not None:
        summary = f'{GRID_NAMES[code]} cleared at ₱{fmt(price)}/MWh median at {hhmm(t, at)}.'
    return {'kind': 'region', 'id': code, 'title': GRID_NAMES[code], 'subtitle': f'Grid · {code}',
            'href': href('region', code), 'grid': code,
            'facts': [_fact('Median price', price, '₱/MWh', t),
                      _fact('Demand', _grid_value(payload, i, code, 'demand_mw'), 'MW', t),
                      _fact('Reserve requirement', _grid_value(payload, i, code, 'dr_req_mw'), 'MW', t),
                      _fact('Reserve shortfall', _grid_value(payload, i, code, 'dr_short_mw'), 'MW', t),
                      _fact('Net import', net, 'MW', t)],
            'sparks': [_spark('Median price, 24 h', '₱/MWh', pt, pv), _spark('Demand, 24 h', 'MW', dt, dv)],
            'summary': summary, 'sources': [source(bake, 'bake-regions')]}


def _event(bake, event_id, at):
    event = next((e for e in bake.events() if e['id'] == event_id), None)
    if event is None or event['t'] > at:
        return None
    view = bake.event_view(event_id)
    advisory = bake.advisory(event['advisory'], at) if event.get('advisory') else None
    text = advisory['text'] if advisory else None
    if text is None and isinstance(view, dict) and isinstance(view.get('advisory'), dict):
        text = str(view['advisory'].get('text') or '') or None
    grid = bake.event_grid(event)
    site = bake.site(event['site']) if event.get('site') else None
    facts = [_fact('Time', event['t'], None, event['t']),
             _fact('Severity', event_severity(bake, event, at), None, event['t'])]
    if site:
        facts.append(_fact('Plant', site_title(site), None, None))
    if event['assumption']:
        facts.append(_fact('Assumption', event['assumption'], None, None))
    return {'kind': 'event', 'id': event_id, 'title': event['title'],
            'subtitle': ' · '.join(p for p in (GRID_NAMES.get(grid), hhmm(event['t'], at)) if p),
            'href': href('event', event_id), 'grid': grid, 'facts': facts, 'sparks': [],
            'summary': text, 'sources': [source(bake, 'bake-events')]
            + ([source(bake, 'bake-advisories')] if advisory else [])}


def _notice(bake, advisory_id, at):
    a = bake.advisory(advisory_id, at)
    if a is None:
        return None
    item = _notice_item(a, at)
    return {'kind': 'notice', 'id': a['id'], 'title': item['title'], 'subtitle': item['subtitle'],
            'href': item['href'], 'grid': a['grid'],
            'facts': [_fact('Time', a['t'], None, a['t']), _fact('Severity', severity_of(a['kind']), None, a['t'])],
            'sparks': [], 'summary': a['text'] or None, 'sources': [source(bake, 'bake-advisories')]}


def _link_value(payload, i, link, field):
    series = ((payload or {}).get('links') or {}).get(link, {}).get(field)
    if not series or i is None:
        return None
    value = series[i]
    if field == 'congested':
        return value if value in (0, 1) and type(value) is not bool else None
    return number(value)


def _link(bake, link, at):
    if link not in LINKS:
        return None
    payload, i = bake.interval(at)
    t = payload['t'][i] if payload else at
    start = shift(at, -24 * 60)
    ft, fv = bake.series(start, at, lambda p, j: _link_value(p, j, link, 'flow'))
    congested = _link_value(payload, i, link, 'congested')
    a, b = LINKS[link]
    return {'kind': 'link', 'id': link, 'title': LINK_NAMES[link],
            'subtitle': f'HVDC link · {link} · {GRID_NAMES[a]} and {GRID_NAMES[b]}',
            'href': href('link', link), 'grid': None,
            'facts': [_fact('Flow', _link_value(payload, i, link, 'flow'), 'MW', t),
                      _fact('Congested', None if congested is None else bool(congested), None, t)],
            'sparks': [_spark('Flow, 24 h', 'MW', ft, fv)],
            'summary': f'Positive flow runs from {GRID_NAMES[a]} to {GRID_NAMES[b]}.',
            'sources': [source(bake, 'bake-hvdc')]}


def _dataset(bake, dataset_id, at):
    entry = _datasets(bake).get(dataset_id)
    if entry is None:
        return None
    return {'kind': 'dataset', 'id': dataset_id, 'title': entry['name'], 'subtitle': 'Dataset · ' + dataset_id,
            'href': href('dataset', dataset_id), 'grid': None, 'facts': [], 'sparks': [],
            'summary': entry.get('definition'), 'sources': [source(bake, dataset_id)]}
