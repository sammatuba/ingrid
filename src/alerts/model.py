"""Portfolio and notification rules: validation, the impact estimate, alert keys and the email text.

Pure functions, no SDK and no network. The shapes are the alerts contract's
(docs/work/alerts-portfolio-2026-10-17/intent.md). Portfolio values and recipients are company data:
they live in the private Firestore namespace only, never in Git, the public bake or a log line.

Owner rules carried here:
* the financial impact is computed only from a portfolio a signed-in user entered, and always says
  which version and effective date it used; with no portfolio it says so, never a number;
* likely drivers are evidence, not proof; the email lists what to check, never trading advice.
"""
import hashlib
import re
from datetime import date, datetime

REGIONS = {'CLUZ': 'Luzon', 'CVIS': 'Visayas', 'CMIN': 'Mindanao'}
# The driver card's severity levels (grid_ontology.card_summary), lowest first, plus `extreme`: a
# High card whose interval's price band (grid_curated.labels) is `extreme`. `unrated` never passes a
# minimum: an unrated card has no price band known at the cutoff.
SEVERITIES = ('low', 'medium', 'high', 'extreme')
THRESHOLD_MODES = ('absolute', 'ratio_to_baseline')
# ericka-desk E22: each region may set its own spike level (price at or above) and collapse level
# (price at or below), each in PHP/MWh (`absolute`) or as a multiple of usual (`ratio_to_baseline`).
# A region without its own spike level uses the rule set's `threshold`, so a stored version without
# `levels` reads exactly as before; a region without a collapse level has none.
DIRECTIONS = ('spike', 'collapse')
PRICE_CAP = 32000  # the WESM offer cap the replay's prices reach (PHP/MWh)
PRICE_FLOOR = -10000  # the WESM offer floor
INTERVAL_HOURS = 5 / 60
EMAIL = re.compile(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'
                   r'(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+\Z')
INTERVAL = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z')
NO_PORTFOLIO = 'Not available: no portfolio entered'
DISCLAIMER = 'Likely drivers are evidence, not proof. Nothing here is trading advice.'
MAX_CONTRACTS = 200
MAX_NODES = 500
MAX_RECIPIENTS = 50
MAX_TEXT = 200


class InvalidInput(ValueError):
    """A refused portfolio, rule set or run request; `field` names what was wrong."""

    def __init__(self, field, reason):
        self.field, self.reason = field, reason
        super().__init__(f'{field}: {reason}')


def _require(condition, field, reason):
    if not condition:
        raise InvalidInput(field, reason)


def _number(value, field, minimum=None):
    _require(type(value) in (int, float) and value == value and abs(value) < 1e9, field, 'a number')
    if minimum is not None:
        _require(value >= minimum, field, f'at least {minimum}')
    return float(value) if type(value) is float else value


def _text(value, field, required=False):
    if value is None and not required:
        return ''
    _require(type(value) is str and len(value) <= MAX_TEXT, field, f'text of at most {MAX_TEXT} characters')
    _require(not required or value.strip(), field, 'required')
    return value.strip()


def _iso_date(value, field):
    _require(type(value) is str, field, 'a date YYYY-MM-DD')
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise InvalidInput(field, 'a date YYYY-MM-DD') from None


def _keys(body, allowed, field):
    _require(type(body) is dict, field, 'an object')
    extra = sorted(set(body) - set(allowed))
    _require(not extra, field, 'unknown fields ' + ', '.join(extra))


def validate_portfolio(body):
    """The portfolio as stored, or InvalidInput. Version and saved_* are the store's, never the body's."""
    _keys(body, {'effective_from', 'note', 'benchmark_php_mwh', 'regions', 'contracts', 'nodes', 'source'}, 'portfolio')
    out = {'effective_from': _iso_date(body.get('effective_from'), 'effective_from'),
           'note': _text(body.get('note'), 'note'),
           'benchmark_php_mwh': _number(body.get('benchmark_php_mwh'), 'benchmark_php_mwh', 0)}
    regions = body.get('regions') or {}
    _require(type(regions) is dict, 'regions', 'an object keyed by region code')
    out['regions'] = {}
    for code, entry in regions.items():
        _require(code in REGIONS, 'regions', f'unknown region {code!r}')
        _keys(entry, {'demand_mw_by_hour', 'contracted_mw_by_hour'}, f'regions.{code}')
        out['regions'][code] = {'demand_mw_by_hour': _hours(entry.get('demand_mw_by_hour'), f'regions.{code}.demand_mw_by_hour')}
        if entry.get('contracted_mw_by_hour') is not None:
            out['regions'][code]['contracted_mw_by_hour'] = _hours(
                entry['contracted_mw_by_hour'], f'regions.{code}.contracted_mw_by_hour')
    contracts = body.get('contracts') or []
    _require(type(contracts) is list and len(contracts) <= MAX_CONTRACTS, 'contracts', f'a list of at most {MAX_CONTRACTS}')
    out['contracts'] = []
    for i, c in enumerate(contracts):
        f = f'contracts[{i}]'
        _keys(c, {'name', 'region', 'mw', 'price_php_mwh', 'hours', 'start', 'end'}, f)
        _require(c.get('region') in REGIONS, f + '.region', 'one of ' + ', '.join(REGIONS))
        hours = c.get('hours')
        _require(type(hours) is list and hours and all(type(h) is int and 0 <= h <= 23 for h in hours),
                 f + '.hours', 'a non-empty list of hours 0 to 23')
        start, end = _iso_date(c.get('start'), f + '.start'), _iso_date(c.get('end'), f + '.end')
        _require(start <= end, f + '.end', 'on or after start')
        out['contracts'].append({'name': _text(c.get('name'), f + '.name', required=True), 'region': c['region'],
                                 'mw': _number(c.get('mw'), f + '.mw', 0),
                                 'price_php_mwh': _number(c.get('price_php_mwh'), f + '.price_php_mwh', 0),
                                 'hours': sorted(set(hours)), 'start': start, 'end': end})
    nodes = body.get('nodes') or []
    _require(type(nodes) is list and len(nodes) <= MAX_NODES, 'nodes', f'a list of at most {MAX_NODES}')
    out['nodes'] = []
    for i, n in enumerate(nodes):
        f = f'nodes[{i}]'
        _keys(n, {'code', 'region', 'label'}, f)
        _require(n.get('region') in REGIONS, f + '.region', 'one of ' + ', '.join(REGIONS))
        out['nodes'].append({'code': _text(n.get('code'), f + '.code', required=True), 'region': n['region'],
                             'label': _text(n.get('label'), f + '.label')})
    _require(out['regions'] or out['contracts'], 'regions', 'enter demand for at least one region or at least one contract')
    if body.get('source') is not None:
        out['source'] = _source(body['source'])
    return out


def _hours(values, field):
    _require(type(values) is list and len(values) == 24, field, '24 numbers, hour 0 to 23')
    return [_number(v, f'{field}[{h}]', 0) for h, v in enumerate(values)]


UNITS = ('kWh', 'MWh')


def _source(body):
    """Where the numbers came from: only the import's tag (scripts/alerts/portfolio_import.py) is known."""
    _keys(body, {'kind', 'built_at', 'window', 'units'}, 'source')
    _require(body.get('kind') == 'import', 'source.kind', "'import'")
    window, units = body.get('window'), body.get('units')
    _keys(window, {'first', 'last', 'days'}, 'source.window')
    _keys(units, {'mq', 'bcq', 'stated_by'}, 'source.units')
    days = window.get('days')
    _require(type(days) is int and 1 <= days <= 366, 'source.window.days', 'whole days, 1 to 366')
    _require(units.get('mq') in UNITS and units.get('bcq') in UNITS, 'source.units', 'kWh or MWh')
    return {'kind': 'import', 'built_at': _text(body.get('built_at'), 'source.built_at', required=True),
            'window': {'first': _iso_date(window.get('first'), 'source.window.first'),
                       'last': _iso_date(window.get('last'), 'source.window.last'), 'days': days},
            'units': {'mq': units['mq'], 'bcq': units['bcq'],
                      'stated_by': _text(units.get('stated_by'), 'source.units.stated_by') or None}}


def _level(value, field, direction):
    """One spike or collapse level {mode, value}, or None (no level of that kind)."""
    if value is None:
        return None
    _keys(value, {'mode', 'value'}, field)
    _require(value.get('mode') in THRESHOLD_MODES, field + '.mode', ' or '.join(THRESHOLD_MODES))
    number = _number(value.get('value'), field + '.value')
    if value['mode'] == 'ratio_to_baseline':
        if direction == 'spike':
            _require(1 < number <= 100, field + '.value', 'a multiple of usual above 1 and at most 100')
        else:
            _require(0 < number < 1, field + '.value', 'a multiple of usual above 0 and below 1')
    elif direction == 'spike':
        _require(0 < number <= 1_000_000, field + '.value', 'a price above 0 PHP/MWh')
    else:
        _require(-1_000_000 <= number <= 1_000_000, field + '.value', 'a price in PHP/MWh')
    return {'mode': value['mode'], 'value': number}


def validate_levels(levels, threshold):
    """The per-region levels as stored: {region: {spike, collapse}}, each a level or None."""
    _require(type(levels) is dict, 'levels', 'an object keyed by region code')
    out = {}
    for code, entry in levels.items():
        _require(code in REGIONS, 'levels', f'unknown region {code!r}')
        f = f'levels.{code}'
        _keys(entry, set(DIRECTIONS), f)
        spike = _level(entry.get('spike'), f + '.spike', 'spike')
        collapse = _level(entry.get('collapse'), f + '.collapse', 'collapse')
        effective = spike or threshold
        if collapse and effective and collapse['mode'] == effective['mode']:
            _require(collapse['value'] < effective['value'], f + '.collapse.value', 'below the spike level')
        out[code] = {'spike': spike, 'collapse': collapse}
    return out


def levels_for(rules, region):
    """The region's effective {spike, collapse}: its own levels, the spike falling back to `threshold`."""
    own = ((rules or {}).get('levels') or {}).get(region) or {}
    spike = own.get('spike') or (rules or {}).get('threshold')
    return {'spike': spike, 'collapse': own.get('collapse')}


def crossing(levels, price, usual, usual_ok=True):
    """'spike', 'collapse' or None for one price against a region's levels.

    A multiple-of-usual level needs a usual price (`usual` above 0 and `usual_ok`); without one it
    never fires, so day 1 of a replay, with no earlier day, raises no ratio alert.
    """
    if price is None:
        return None

    def bound(level):
        if level is None:
            return None
        if level['mode'] == 'absolute':
            return level['value']
        return level['value'] * usual if usual_ok and usual is not None and usual > 0 else None

    high, low = bound(levels.get('spike')), bound(levels.get('collapse'))
    if high is not None and price >= high:
        return 'spike'
    if low is not None and price <= low:
        return 'collapse'
    return None


def level_text(direction, level, usual=None, usual_words='usual', tail=True):
    """The rule in words: 'price at or above 15,000 PHP/MWh', 'price at or below 0.3 x usual (...)'."""
    if level is None:
        return ''
    side = 'at or above' if direction == 'spike' else 'at or below'
    if level['mode'] == 'absolute':
        return f"price {side} {level['value']:,.0f} PHP/MWh"
    words = f"price {side} {level['value']:g} x {usual_words}"
    if not tail:
        return words
    return words + (f' ({usual_words} {usual:,.0f} PHP/MWh)' if usual is not None else ' (no usual price yet)')


def validate_rules(body):
    """The notification rules as stored, or InvalidInput."""
    _keys(body, {'enabled', 'threshold', 'regions', 'min_severity', 'recipients', 'levels'}, 'rules')
    _require(type(body.get('enabled')) is bool, 'enabled', 'true or false')
    threshold = body.get('threshold')
    _keys(threshold, {'mode', 'value'}, 'threshold')
    _require(threshold.get('mode') in THRESHOLD_MODES, 'threshold.mode', ' or '.join(THRESHOLD_MODES))
    value = _number(threshold.get('value'), 'threshold.value', 0)
    _require(value > 0, 'threshold.value', 'above 0')
    if threshold['mode'] == 'ratio_to_baseline':
        _require(value <= 100, 'threshold.value', 'a ratio of at most 100')
    regions = body.get('regions')
    _require(type(regions) is list and regions and all(r in REGIONS for r in regions), 'regions',
             'a non-empty list of ' + ', '.join(REGIONS))
    _require(body.get('min_severity') in SEVERITIES, 'min_severity', ' or '.join(SEVERITIES))
    recipients = body.get('recipients') or []
    _require(type(recipients) is list and len(recipients) <= MAX_RECIPIENTS, 'recipients',
             f'a list of at most {MAX_RECIPIENTS}')
    out_recipients, seen = [], set()
    for i, r in enumerate(recipients):
        f = f'recipients[{i}]'
        _keys(r, {'email', 'regions', 'min_severity'}, f)
        email = r.get('email')
        _require(type(email) is str and len(email) <= 254 and EMAIL.match(email.strip()), f + '.email', 'an email address')
        email = email.strip().lower()
        _require(email not in seen, f + '.email', 'listed twice')
        seen.add(email)
        rr = r.get('regions') or list(regions)
        _require(type(rr) is list and rr and all(x in REGIONS for x in rr), f + '.regions', 'region codes')
        ms = r.get('min_severity') or body['min_severity']
        _require(ms in SEVERITIES, f + '.min_severity', ' or '.join(SEVERITIES))
        out_recipients.append({'email': email, 'regions': sorted(set(rr)), 'min_severity': ms})
    out = {'enabled': body['enabled'], 'threshold': {'mode': threshold['mode'], 'value': value},
           'regions': sorted(set(regions)), 'min_severity': body['min_severity'], 'recipients': out_recipients}
    if body.get('levels') is not None:
        out['levels'] = validate_levels(body['levels'], out['threshold'])
    return out


def parse_interval(value):
    """'YYYY-MM-DDTHH:MM' Manila civil time on a five-minute boundary, as a naive datetime."""
    _require(type(value) is str and INTERVAL.match(value), 'interval_manila', 'YYYY-MM-DDTHH:MM (Manila time)')
    try:
        at = datetime.fromisoformat(value)
    except ValueError:
        raise InvalidInput('interval_manila', 'YYYY-MM-DDTHH:MM (Manila time)') from None
    _require(at.minute % 5 == 0, 'interval_manila', 'a five-minute interval start')
    return at


def alert_severity(card_severity, price_band):
    """The alert's level: the card's, lower-cased, raised to `extreme` for a High card in an extreme band."""
    level = (card_severity or 'unrated').strip().lower()
    return 'extreme' if level == 'high' and price_band == 'extreme' else level


def severity_rank(severity):
    """Index in SEVERITIES for 'low'/'medium'/'high'/'extreme' (any case); -1 for unrated or unknown."""
    value = (severity or '').strip().lower()
    return SEVERITIES.index(value) if value in SEVERITIES else -1


def passes(severity, minimum):
    return severity_rank(severity) >= SEVERITIES.index(minimum)


def latest_portfolio(versions, interval_date):
    """The highest version whose effective_from is on or before the interval's Manila date, or None."""
    day = interval_date.isoformat() if isinstance(interval_date, date) else str(interval_date)
    usable = [v for v in versions if v.get('effective_from', '9999') <= day]
    return max(usable, key=lambda v: v['version']) if usable else None


def contracted_mw(portfolio, region, at):
    """The listed contracts active at that hour, plus the region's contracted-by-hour profile if any."""
    day, hour = at.date().isoformat(), at.hour
    listed = sum(c['mw'] for c in portfolio.get('contracts', [])
                 if c['region'] == region and c['start'] <= day <= c['end'] and hour in c['hours'])
    profile = (portfolio.get('regions', {}).get(region) or {}).get('contracted_mw_by_hour')
    return listed + profile[hour] if profile else listed


def basis_of(portfolio):
    source = portfolio.get('source') or {}
    imported = (f" (imported, BCQ/MQ to {source['window']['last']})"
                if source.get('kind') == 'import' else '')
    return f"Estimate from portfolio v{portfolio['version']}{imported}, effective {portfolio['effective_from']}"


def impact(portfolio, region, at, price):
    """The interval's estimate from the entered portfolio, signed; or the 'not available' status.

    unhedged = demand at that hour minus the MW of the active contracts covering that hour in that
    region; php = unhedged x (price - benchmark) x 5/60 h, the contract's formula. Positive is a cost
    against the benchmark, negative a gain (price below the benchmark). An over-contracted interval
    (negative unhedged) is sold at the market price, so the same formula and sign give its effect.
    """
    if portfolio is None:
        return {'status': NO_PORTFOLIO}
    demand = portfolio.get('regions', {}).get(region)
    basis = basis_of(portfolio)
    if demand is None:
        return {'status': f'Not available: portfolio v{portfolio["version"]} has no demand for {REGIONS[region]}',
                'basis': basis}
    demand_mw = demand['demand_mw_by_hour'][at.hour]
    contracted = contracted_mw(portfolio, region, at)
    unhedged = demand_mw - contracted
    benchmark = portfolio['benchmark_php_mwh']
    php = unhedged * (price - benchmark) * INTERVAL_HOURS
    out = {'php': round(php, 2), 'unhedged_mw': round(unhedged, 3), 'demand_mw': demand_mw,
           'contracted_mw': contracted, 'benchmark_php_mwh': benchmark, 'interval_hours': round(INTERVAL_HOURS, 6),
           'basis': basis}
    if unhedged < 0:
        out['note'] = f'over-contracted by {round(-unhedged, 3)} MW, sold at the market price'
    return out


def alert_key(region, interval_manila, rules_version):
    raw = f'{region}|{interval_manila}|{rules_version}'.encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:24]


def recipients_for(rules, region, severity):
    return [r['email'] for r in rules.get('recipients', [])
            if region in r['regions'] and passes(severity, r['min_severity'])]


def _peso(value):
    sign = '-' if value < 0 else ''
    return f'{sign}PHP {abs(value):,.0f}'


def _when(interval_manila):
    at = datetime.fromisoformat(interval_manila)
    return f"{at.day} {at.strftime('%b')} {at.year} {at.strftime('%H:%M')} Manila"


def impact_line(fi):
    if 'php' not in fi:
        return fi.get('status', NO_PORTFOLIO)
    effect = 'cost' if fi['php'] >= 0 else 'gain'
    line = (f"{_peso(abs(fi['php']))} {effect} in this interval ({fi['unhedged_mw']:g} MW unhedged "
            f"against a benchmark of PHP {fi['benchmark_php_mwh']:,.0f}/MWh). {fi['basis']}.")
    return line + (f" Note: {fi['note']}." if fi.get('note') else '')


def main_driver(alert):
    """The alert's main driver, from its records only: the top-ranked likely driver, or the recorded
    event that caused it; otherwise it says none is on record, never a guess."""
    if alert.get('main_driver'):
        return alert['main_driver']
    drivers = alert.get('likely_drivers') or []
    if drivers:
        d = drivers[0]
        return f"{d.get('family_label') or d.get('family')} ({d.get('why') or 'ranked first'})"
    return 'None on record: no driver was ranked for this interval'


def email_message(alert, test=False):
    """(subject, text, html) for one alert. The HTML escapes every value it carries."""
    from html import escape
    region = REGIONS.get(alert['region'], alert['region'])
    severity = (alert.get('severity') or 'unrated').upper()
    subject = (f"[InGRID]{' TEST' if test else ''} {severity} · {region} "
               f"{alert['price_php_mwh']:,.0f} PHP/MWh · {_when(alert['interval_manila'])}")
    drivers = [f"{d['family_label']} {d['score']:.2f} ({d['why']})" for d in alert.get('likely_drivers', [])]
    lines = [
        ('Main driver', main_driver(alert)),
        ('Severity', f"{severity}: {alert.get('severity_reason', '')}"),
        ('Financial impact', impact_line(alert['financial_impact'])),
        ('Confidence', f"{alert.get('confidence', '')}: {alert.get('confidence_reason', '')}"),
        ('Likely drivers', '; '.join(drivers) or 'none ranked'),
        ('Relationship trail', alert.get('relationship_trail', '')),
        ('What to check', '; '.join(alert.get('what_to_check', [])) or 'nothing listed'),
        ('Threshold', alert.get('threshold_text', '')),
    ]
    head = 'TEST MESSAGE: no alert was raised. ' if test else ''
    text = '\n'.join([head + f"{region} price {alert['price_php_mwh']:,.0f} PHP/MWh at {_when(alert['interval_manila'])}.", '']
                     + [f'{k}: {v}' for k, v in lines]
                     + ['', DISCLAIMER, f"Event page: {alert.get('event_url', '')}", ''])
    rows = ''.join(f'<tr><th align="left" valign="top" style="padding:4px 12px 4px 0">{escape(k)}</th>'
                   f'<td style="padding:4px 0">{escape(v)}</td></tr>' for k, v in lines)
    html = (f'<div style="font-family:Arial,sans-serif;font-size:14px;color:#1b1b1b">'
            f'<p>{escape(head)}<strong>{escape(region)}</strong> price <strong>{alert["price_php_mwh"]:,.0f} PHP/MWh</strong>'
            f' at {escape(_when(alert["interval_manila"]))}.</p><table>{rows}</table>'
            f'<p style="color:#555">{escape(DISCLAIMER)}</p>'
            f'<p><a href="{escape(alert.get("event_url", ""), quote=True)}">Open the event page</a></p></div>')
    return subject, text, html
