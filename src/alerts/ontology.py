"""The full ontology driver card for one replay alert (ericka-desk): the card the PEDC event page shows,
for any alert, at its peak interval and region.

Three pieces, shared by the batch (scripts/ontology/alert_cards.py) and any on-open path, so both give the
identical JSON:

* ``card_query(region, t_utc, mode)`` -> ``(sql, params)``: one read-only BigQuery script. It runs
  ``grid_ontology.driver_card`` and ``likely_drivers`` for the mode (or the three modes) into temporary
  tables, then ``card_summary``'s own SQL over them (src/alerts/sql/06_card_summary.sql, as
  src/alerts/sql.py's live card does: the recorded function reads only the checked demo cases). Nothing
  is created or replaced in the dataset. Its one result row holds ``alert_json``.
* ``shape(rows, alert)`` -> the card dict (schema below), public by construction as
  scripts/ontology/bake_panel.py is: fuel rows are a count, never a value, series or role; rows marked
  not public never pass; unconfirmed plant matches are listed with the text and the reason and never
  counted; no table, file or script name; the financial impact is the SQL's own "Not available" sentence.
* ``load_card(data_dir, key, alert=None)`` -> the saved card at ``<data>/ontology/cards/<key>.json``, or
  None when absent, unreadable, failing ``problems``, or made for another region or peak interval.

Card schema (``SCHEMA``)::

    {schema, key, region, region_label, direction, interval_manila, t_utc, heading, basis, made_at_utc,
     modes: {assumed|hindsight|strict: {cutoff_utc, facts: [{family, subject_label, predicate, value_num,
             value_text, unit, known_by_utc, assumed_known_by_utc, availability_assumption,
             availability_at_cutoff, match_confidence}], fuel_context, withheld: [{family, reason, n}],
             unconfirmed: [{plant_text, kind, known_by_utc, reason}]}},
     drivers: {mode: [{rank, family, status, indicator, family_score, indicator_score, value_at_t,
               baseline_median, unit, baseline_n}]},
     summary: {severity, severity_reason, confidence, confidence_reason, financial_impact,
               relationship_trail, what_to_check} | null,       # the assumed mode's
     summaries: {mode: <same shape>}}

Times are UTC 'YYYY-MM-DD HH:MM:SS' as the ontology records them; ``interval_manila`` is Manila civil time.
The drivers are evidence, not proof: no row states a cause.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import sql as alert_sql
from .bigquery import parameter

SCHEMA = 'alert-ontology-card/1'
CARD_DIR = ('ontology', 'cards')
MODES = ('assumed', 'hindsight', 'strict')
REGIONS = ('CLUZ', 'CVIS', 'CMIN')
KEY = re.compile(r'[0-9a-f]{24}\Z')
BASIS = ('Ontology record: every fact with the time it was known, ranked against the same hour over the 28 days '
         'before, computed for this alert and checked by code before it was saved. Evidence, not proof.')
FACT_KEYS = ('family', 'subject_label', 'predicate', 'value_num', 'value_text', 'unit', 'known_by_utc',
             'assumed_known_by_utc', 'availability_assumption', 'availability_at_cutoff', 'match_confidence')
DRIVER_KEYS = ('rank', 'family', 'status', 'indicator', 'family_score', 'indicator_score', 'value_at_t',
               'baseline_median', 'unit', 'baseline_n')
SUMMARY_KEYS = ('severity', 'severity_reason', 'confidence', 'confidence_reason', 'financial_impact',
                'relationship_trail', 'what_to_check')
NUMERIC = ('value_num', 'rank', 'family_score', 'indicator_score', 'value_at_t', 'baseline_median', 'baseline_n')
#: fields and values that must never leave the rows (bake_panel.INTERNAL plus table and script names)
INTERNAL = ('fuel_group', 'technology', 'fuel_role', 'coal_driver', 'lng_driver', 'candidate_id', 'candidate_label',
            'grid_ontology', 'grid_curated', 'grid_raw', '.sql', '.py', '.sh', 'source_table')
UTC_TS = re.compile(r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]00(?::?00)?| UTC)?\Z')


def t_utc_of(interval_manila):
    """'2026-10-05T13:35' (Manila) -> '2026-10-05 05:35:00' (UTC), the instant the table functions take."""
    t = datetime.strptime(interval_manila, '%Y-%m-%dT%H:%M') - timedelta(hours=8)
    return t.strftime('%Y-%m-%d %H:%M:%S')


def _utc_param(t_utc):
    m = UTC_TS.fullmatch(str(t_utc or '').strip())
    if not m:
        raise ValueError('t_utc: a UTC instant YYYY-MM-DD HH:MM:SS')
    return f'{m.group(1)} {m.group(2)}+00:00'


def _summary_parts():
    source = alert_sql.CARD_SUMMARY_SQL.read_text(encoding='utf-8')
    body = source[source.index('\nAS\nWITH\n') + len('\nAS\n'):]
    cut = body.index(alert_sql.FINAL_SELECT)
    ctes, final = body[:cut], body[cut + 1:].rstrip().rstrip(';')
    if ctes.count(alert_sql.RECORDED_CARDS) != 1 or ctes.count(alert_sql.RECORDED_DRIVERS) != 1:
        raise ValueError('card_summary no longer reads the recorded tables once each; re-derive the card query')
    ctes = ctes.replace(alert_sql.RECORDED_CARDS, 'alert_card').replace(alert_sql.RECORDED_DRIVERS, 'alert_drv')
    return ctes.rstrip(), final


def card_query(region, t_utc, mode=None):
    """(sql, params): the read-only script for one region and interval start `t_utc` (UTC), in `mode` or,
    with mode None, the three modes. Params @region STRING and @t TIMESTAMP (bigquery.parameter dicts)."""
    if region not in REGIONS:
        raise ValueError('region: CLUZ, CVIS or CMIN')
    modes = MODES if mode is None else (mode,)
    if any(m not in MODES for m in modes):
        raise ValueError('mode: assumed, hindsight or strict')
    ctes, final = _summary_parts()
    lines = ['DECLARE card_region STRING DEFAULT @region;', 'DECLARE t TIMESTAMP DEFAULT @t;',
             f"DECLARE card_mode STRING DEFAULT '{modes[0]}';"]
    for fn, table in (('driver_card', 'alert_card'), ('likely_drivers', 'alert_drv')):
        for i, m in enumerate(modes):
            select = (f"SELECT card_region AS region, 'live' AS case_id, * "
                      f"FROM `grid-nowcast.grid_ontology.{fn}`(card_region, t, '{m}')")
            lines.append(f'CREATE TEMP TABLE {table} AS {select};' if i == 0 else f'INSERT INTO {table} {select};')
    summary = f'{ctes},\nsummary AS (\n{final}\n)\nSELECT * FROM summary;'
    for i, m in enumerate(modes):
        if i:
            lines.append(f"SET card_mode = '{m}';")
        lines.append(('CREATE TEMP TABLE alert_sum AS\n' if i == 0 else 'INSERT INTO alert_sum\n') + summary)
    lines.append('SELECT TO_JSON_STRING(STRUCT(ARRAY(SELECT AS STRUCT * FROM alert_card) AS cards, '
                 'ARRAY(SELECT AS STRUCT * FROM alert_drv) AS drivers, '
                 'ARRAY(SELECT AS STRUCT * FROM alert_sum) AS summary)) AS alert_json;')
    params = [parameter('region', region), parameter('t', _utc_param(t_utc), 'TIMESTAMP')]
    return '\n'.join(lines) + '\n', params


def _ts(value):
    if isinstance(value, str):
        m = UTC_TS.fullmatch(value.strip())
        if m:
            return f'{m.group(1)} {m.group(2)}'
    return value


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if x != x or abs(x) == float('inf'):
        return None
    return int(x) if x.is_integer() and not isinstance(value, float) else x


def _truthy(v):
    return v is True or str(v).lower() == 'true'


def _clean(row, keys):
    out = {}
    for k in keys:
        v = row.get(k)
        out[k] = _number(v) if k in NUMERIC else _ts(v)
    return out


def _summary(row):
    if not row:
        return None
    out = {k: row.get(k) for k in SUMMARY_KEYS}
    w = out.get('what_to_check')
    out['what_to_check'] = [str(x) for x in w] if isinstance(w, list) else ([] if w is None else [str(w)])
    return out


def shape(rows, alert, made_at_utc=None):
    """The card dict from the query's decoded `alert_json` ({cards, drivers, summary}) and the alert it is
    for ({key, region, region_label, direction, interval_manila})."""
    rows = rows or {}
    cards = [r for r in rows.get('cards') or [] if isinstance(r, dict)]
    drivers = [r for r in rows.get('drivers') or [] if isinstance(r, dict)]
    sums = [r for r in rows.get('summary') or [] if isinstance(r, dict)]
    out = {'schema': SCHEMA, 'key': alert['key'], 'region': alert['region'],
           'region_label': alert.get('region_label') or alert['region'], 'direction': alert.get('direction'),
           'interval_manila': alert['interval_manila'], 't_utc': t_utc_of(alert['interval_manila']),
           'heading': next((r['heading'] for r in drivers if r.get('heading')), None), 'basis': BASIS,
           'made_at_utc': made_at_utc or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
           'modes': {}, 'drivers': {}, 'summary': None, 'summaries': {}}
    for mode in MODES:
        mine = [r for r in cards if r.get('mode') == mode]
        if not mine and not any(r.get('mode') == mode for r in drivers):
            continue
        facts = [r for r in mine if r.get('section') == 'fact']
        out['modes'][mode] = {
            'cutoff_utc': _ts(next((r.get('cutoff_utc') for r in mine if r.get('cutoff_utc')), None)),
            'facts': [_clean(r, FACT_KEYS) for r in facts if r.get('family') != 'F' and _truthy(r.get('public'))],
            'fuel_context': sum(1 for r in facts if r.get('family') == 'F'),
            'withheld': [{'family': r.get('family'), 'reason': r.get('withheld_reason'), 'n': int(_number(r.get('n_withheld')) or 0)}
                         for r in mine if r.get('section') == 'withheld'],
            'unconfirmed': [{'plant_text': r.get('value_text'), 'kind': r.get('predicate'),
                             'known_by_utc': _ts(r.get('known_by_utc')), 'reason': r.get('match_reason')}
                            for r in mine if r.get('section') == 'unconfirmed'],
        }
        drv = [r for r in drivers if r.get('mode') == mode]
        if drv:
            items = []
            for r in drv:
                d = _clean(r, DRIVER_KEYS)
                if r.get('family') == 'F':  # fuel: its score only, never its series, value or unit
                    d.update(indicator='fuel cost baseline', value_at_t=None, baseline_median=None, unit=None, baseline_n=None)
                items.append(d)
            items.sort(key=lambda d: (d['rank'] is None, d['rank'] or 0, -(d['indicator_score'] or 0), str(d['indicator'])))
            out['drivers'][mode] = items
        s = next((r for r in sums if r.get('mode') == mode), None)
        if s:
            out['summaries'][mode] = _summary(s)
    out['summary'] = out['summaries'].get('assumed')
    return out


def problems(card):
    """What makes a card unfit to show: internal names, fuel values, a figure in the financial impact,
    a strict fact without evidence, a missing heading. [] when fit."""
    out = []
    if not isinstance(card, dict) or card.get('schema') != SCHEMA:
        return ['not an alert ontology card']
    text = json.dumps(card, ensure_ascii=False)
    out += [f'internal name {w!r}' for w in INTERNAL if w in text]
    for mode, block in (card.get('modes') or {}).items():
        for f in block.get('facts') or []:
            if f.get('family') == 'F':
                out.append(f'{mode}: a fuel fact in the facts')
            if mode == 'strict' and f.get('availability_at_cutoff') != 'evidenced':
                out.append(f'{mode}: a strict fact that is not evidence-known')
            if f.get('availability_at_cutoff') == 'assumed' and not f.get('availability_assumption'):
                out.append(f'{mode}: an assumed fact without its assumption id')
        for u in block.get('unconfirmed') or []:
            if not u.get('plant_text') or not u.get('reason'):
                out.append(f'{mode}: an unconfirmed match without its text or reason')
    for mode, rows in (card.get('drivers') or {}).items():
        for r in rows:
            if r.get('family') == 'F' and (r.get('value_at_t') is not None or r.get('baseline_median') is not None):
                out.append(f'{mode}: a fuel value in the ranking')
    for s in [card.get('summary')] + list((card.get('summaries') or {}).values()):
        if s and any(ch.isdigit() for ch in str(s.get('financial_impact') or '')):
            out.append('a figure in the financial impact')
    if card.get('drivers') and 'evidence, not proof' not in str(card.get('heading') or ''):
        out.append('the likely-drivers heading is missing')
    return out


def card_path(data_dir, key):
    if not (type(key) is str and KEY.fullmatch(key)):
        raise ValueError('alert key')
    return Path(data_dir).joinpath(*CARD_DIR, key + '.json')


def load_card(data_dir, key, alert=None):
    """The saved card for alert `key`, or None. With `alert`, also None when the card was made for
    another region or peak interval (an alert cut by an earlier clock has another peak)."""
    try:
        card = json.loads(card_path(data_dir, key).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(card, dict) or card.get('key') != key or problems(card):
        return None
    if alert is not None and (card.get('region') != alert.get('region')
                              or card.get('interval_manila') != alert.get('interval_manila')):
        return None
    return card
