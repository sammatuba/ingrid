"""One replay alert in words (ericka-desk events-ai; owner decisions of 2026-10-18: "it should be
dynamic, not hard coded", then "computed inside the app when an alert is opened").

For any replay alert, on request, with no batch step and no case list:

* ``drivers.likely_drivers`` ranks the families at the alert's peak interval from the replay data
  (src/alerts/drivers.py);
* ``ranked`` gives one row per family (D, S, O, Rules, F): the strongest indicator, its value against
  the same-hour median and its percentile, or "Not enough history", "No data" or "Not in the replay
  data"; never a guess;
* ``summarise`` gives the severity (the alert's own stated rule) and a confidence from how much could
  be ranked;
* ``compose`` writes the paragraph in code: no cause claim, the drivers are "evidence, not proof", no
  technology and no plant name, no peso impact.

AI wording is optional: a phrasing saved beside the bake (``load_saved``) is shown only when it was made
for exactly these facts (the same ``facts_hash``). This module calls no model and no BigQuery; the
full BigQuery driver card shown beside it (owner decision of 2026-10-18: computed on first open by a
signed-in user, capped bytes, cached in Firestore) is src/alerts/ontology_live.py.
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from . import drivers as drivers_mod

SAVED_DIR = ('ontology', 'alerts')
KEY = re.compile(r'[0-9a-f]{24}\Z')
NO_DATA = 'No data'
NOT_ENOUGH = 'Not enough history'
NOT_HELD = 'Not in the replay data'
HEADING = 'Likely drivers (ranked by how unusual each was against the same hour over the 28 days before; evidence, not proof)'
BASIS = ('Computed from the replay data when the alert is opened: each indicator at the peak interval against '
         'the same hour over the 28 days before. It may differ slightly from the event page, which uses the full '
         'data warehouse (price-rule flags, transmission congestion and fuel series are not in the replay).')
FAMILIES = drivers_mod.FAMILIES
FAMILY = {'D': 'demand', 'S': 'supply and interconnection', 'O': 'outages', 'Rules': 'rules and grid constraints',
          'F': 'fuel cost baseline'}
FAMILY_TITLE = {'D': 'Demand', 'S': 'Supply and interconnection', 'O': 'Outages', 'Rules': 'Rules and grid constraints',
                'F': 'Fuel cost baseline'}
INDICATOR = {
    'demand_mw': ('demand', 'MW', 0), 'import_share': ('import share of demand', '', 3),
    'reserve_shortfall_mw': ('reserve shortfall', 'MW', 0), 'hvdc_links_congested': ('congested HVDC links', '', 0),
    'trip_notices_6h': ('trip notices in the 6 hours to the interval', '', 0),
}
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')
FINANCIAL = 'Not available: needs portfolio data (positions, contracts, load nodes)'
NOTE_NO_AI = 'The AI phrasing is not available for these facts. The text is composed by code.'


def _num(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float('inf') else None


def fmt(value, digits=0):
    return f'{float(value):,.{digits}f}'


def when_words(t):
    """'13:40 on 21 September 2026' from a Manila 'YYYY-MM-DDTHH:MM'."""
    return f'{t[11:16]} on {int(t[8:10])} {MONTHS[int(t[5:7]) - 1]} {t[:4]}'


def ranked(result):
    """One row per family from `drivers.likely_drivers`: ranked families first, then the rest."""
    rows = (result or {}).get('rows') or []
    out = []
    for fam in FAMILIES:
        mine = [r for r in rows if r['family'] == fam]
        scored = [r for r in mine if r['status'] == drivers_mod.STATUS_SCORED]
        base = {'family': fam, 'name': FAMILY_TITLE[fam], 'rank': None, 'percentile': None, 'indicator': None,
                'value': None, 'median': None, 'unit': '', 'baseline_n': None, 'baseline_days': None}
        if scored:
            r = max(scored, key=lambda x: (x['indicator_score'], x['indicator']))
            label, unit, d = INDICATOR.get(r['indicator'], (str(r['indicator']).replace('_', ' '), '', 2))
            pct = round(r['indicator_score'] * 100)
            u = f' {unit}' if unit else ''
            text = (f"{label} {fmt(r['value_at_t'], d)}{u} against a median of {fmt(r['baseline_median'], d)}{u}, "
                    f'percentile {pct}')
            out.append(dict(base, rank=r['rank'], status='scored', percentile=pct, text=text, indicator=label,
                            value=r['value_at_t'], median=r['baseline_median'], unit=unit,
                            baseline_n=r['baseline_n'], baseline_days=r['baseline_days']))
        elif any(r['status'] == drivers_mod.STATUS_HISTORY for r in mine):
            days = max(r['baseline_days'] for r in mine)
            out.append(dict(base, status='not enough history', baseline_days=days,
                            text=f'{NOT_ENOUGH}: {days} earlier day{"" if days == 1 else "s"} at this hour '
                                 f'(needs {drivers_mod.MIN_DAYS})'))
        elif any(r['status'] == drivers_mod.STATUS_NOT_HELD for r in mine):
            out.append(dict(base, status='not in replay', text=NOT_HELD))
        else:
            out.append(dict(base, status='no data', text=NO_DATA))
    out.sort(key=lambda r: (r['rank'] is None, r['rank'] or 0))
    return out


def summarise(alert, result):
    """Severity: the alert's own stated rule. Confidence: how much of the board could be ranked."""
    rows = ranked(result)
    n_scored = sum(1 for r in rows if r['status'] == 'scored')
    days = (result or {}).get('baseline_days') or 0
    # never High: the replay holds three of the five families at most
    confidence = 'Medium' if n_scored >= 3 and days >= 14 else 'Low'
    creason = (f'{n_scored} of {len(FAMILIES)} families ranked; {days} earlier day{"" if days == 1 else "s"} '
               f'at this hour; the replay holds no congestion, price-rule or fuel data')
    return {'severity': alert.get('severity') or 'unrated',
            'severity_reason': alert.get('severity_reason') or 'the alert rule on the recorded price',
            'confidence': confidence, 'confidence_reason': creason, 'financial_impact': FINANCIAL,
            'families_ranked': n_scored, 'baseline_days': days}


def compose(alert, result):
    """The paragraph in code, from the alert and the in-app ranking. Returns {'text', 'entities'}."""
    region = alert.get('region_label') or alert['region']
    spike = alert.get('direction') != 'collapse'
    price, usual = _num(alert.get('price_php_mwh')), _num(alert.get('usual_php_mwh'))
    out = []
    lead = f"At {when_words(alert['interval_manila'])}, the {region} capped median price was "
    out.append(lead + (f'{fmt(price)} PHP/MWh' if price is not None else NO_DATA.lower())
               + f", the {'peak' if spike else 'lowest'} of this alert.")
    out.append(f'The usual for that hour was {fmt(usual)} PHP/MWh.' if usual is not None
               else 'There is no usual price for that hour yet.')
    rows = ranked(result)
    parts = [f"{FAMILY[r['family']]} ({r['text']})" for r in rows if r['status'] == 'scored']
    if parts:
        out.append('Likely drivers, ranked by how unusual each was against the same hour over the 28 days before '
                   '(evidence, not proof): ' + '; '.join(parts) + '.')
    short = [FAMILY[r['family']] for r in rows if r['status'] == 'not enough history']
    if short:
        days = (result or {}).get('baseline_days') or 0
        out.append(f"{NOT_ENOUGH} for {', '.join(short)}: {days} earlier day{'' if days == 1 else 's'} at this hour, "
                   f'{drivers_mod.MIN_DAYS} needed.')
    none = [FAMILY[r['family']] for r in rows if r['status'] == 'no data']
    if none:
        out.append(f"{NO_DATA} for {', '.join(none)}.")
    held = [FAMILY[r['family']] for r in rows if r['status'] == 'not in replay']
    if held:
        out.append(f"{NOT_HELD}: {', '.join(held)}.")
    out.append('Financial impact not available without portfolio data.')
    return {'text': ' '.join(out), 'entities': [region]}


def facts_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------- checking a model's wording
# A model may only reword the composed paragraph. `verify_phrasing` is the code check every saved wording
# must pass, in the batch before it is saved and again here before it is shown; anything it finds keeps the
# composed text on the page.
NUMBER = re.compile(r'(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?')  # a sign is part of the figure
CAUSAL = re.compile(r'\b(?:caus(?:e|ed|es|ing)|because|due to|dr(?:o|i)ve[ns]?|driven|driving|led to|leads? to|'
                    r'leading to(?! the interval)|trigger(?:ed|s|ing)?|result(?:ed|s|ing)? in|owing to|responsible|blame[ds]?|'
                    r'attribut\w*|explain(?:s|ed|ing)?|thanks to|as a result|therefore|hence|consequen\w*|'
                    r'pushed|push(?:es|ing)?|raised|lifted|sparked|fuell?ed|spurred|contribut\w*|factors?|reasons?|'
                    r'behind|account(?:s|ed)? for|roles?)\b', re.I)
FORECAST = re.compile(r'\b(?:will|would|could(?! not\b)|may|might|shall|should|expect\w*|forecast\w*|predict\w*|'
                      r'project(?:ed|ion|ions|s)?|outlook|anticipat\w*|tomorrow|upcoming|going forward|'
                      r'is set to|likely to|bound to|poised|recommend\w*|advis\w*|buy|sell|hedge)\b', re.I)
PESO = re.compile(r'[₱$€£]|\bpesos?\b|\bPHP\b(?!/MWh)|\bP\s?\d|\b(?:thousand|million|billion|trillion|'
                  r'mn|bn)s?\b|\b\d+(?:\.\d+)?\s?[kKmMbB]\b', re.I)
# Unit technology, fuel and plant words: never in a wording unless the composed text has the word itself
# (the family name "fuel cost baseline" is in it, so "fuel" is allowed there and only there).
TECHNOLOGY = re.compile(r'\b(?:coal|gas|lng|natural|diesel|oil|bunker|hydro\w*|geothermal|solar|wind|'
                        r'biomass|nuclear|batter(?:y|ies)|bess|storage|thermal|turbine\w*|combined|cycle|'
                        r'peaker\w*|baseload|fuel\w*|plants?|units?|generators?|gensets?|stations?|'
                        r'facilit(?:y|ies)|dam|reservoir|ccgt|ocgt|ppa|ipp\w*)\b', re.I)
WORD_TOKEN = re.compile(r"[A-Za-z][A-Za-z'/-]*")
# Words a wording may start a sentence with although the composed text does not hold them.
STARTERS = frozenset('''a an the at in on for over against by with and but also however meanwhile overall
this that these those it its there here no not none only each every both while when where of as
below above under across among during after before within then compared together
several many some all most first next finally second third lastly information details further additionally
they their them what which such other another one two three is was were has had any
'''.split())
# A sentence may also start with an ordinary word of these endings ("Assessing", "Notably"); a plant or
# unit name with no such ending, or anywhere else in a sentence, still fails.
COMMON_ENDING = re.compile(r'[a-z]{3,}(?:ing|ly|ed|tion|ment|ever)\Z')
# Phrases the composed text carries that the wording must keep (lower case, when the composed text has them).
KEEP = ('capped median price', 'evidence, not proof', 'not enough history', 'no data', 'not in the replay data', 'portfolio')


def verify_phrasing(composed, phrased, entities=()):
    """The problems of a model's wording `phrased` against the code-composed paragraph `composed` (str);
    [] when it may be shown. It fails on: any figure added, dropped or changed (figures compared as a
    multiset); a family, a kept phrase or a named entity (the region) dropped, or a kept phrase added; a word for a cause, a
    forecast, advice or a peso amount; a unit technology, fuel or plant word the composed text does not
    hold; any capitalised word, code or acronym the composed text does not hold (a plant or unit name);
    list or markdown layout; an empty or much longer text; the facts text returned unchanged (nothing to label as reworded)."""
    problems = []
    if type(phrased) is not str or not phrased.strip():
        return ['empty']
    text, src = phrased.strip(), composed
    if ' '.join(text.split()) == ' '.join(src.split()):
        return ['not reworded: the same text as the facts']
    if re.search(r'[*#`_\n\r]|^\s*[-•]', text, re.M):
        problems.append('layout or markdown: one plain paragraph only')
    if len(text) > 1.5 * len(src) + 80:
        problems.append('much longer than the facts')
    def figures(t):
        return Counter(x.replace(',', '').replace('−', '-') for x in NUMBER.findall(t))
    want, got = figures(src), figures(text)
    problems += [f'figure {x} missing' for x in sorted((want - got).elements())]
    problems += [f'figure {x} not in the facts' for x in sorted((got - want).elements())]
    low, src_low = text.lower(), src.lower()
    for name in entities:
        if name and name not in text:
            problems.append(f'name {name!r} missing')
    for phrase in KEEP + tuple(FAMILY.values()):
        if phrase in src_low and phrase not in low:
            problems.append(f'{phrase!r} missing')
    for phrase in KEEP:
        if phrase in low and phrase not in src_low:
            problems.append(f'{phrase!r} not in the facts')
    for rx, what in ((CAUSAL, 'causal wording'), (FORECAST, 'forecast or advice wording'),
                     (PESO, 'peso amount')):
        for m in rx.finditer(text):
            if not re.search(r'\b' + re.escape(m.group(0).lower()) + r'\b', src_low):
                problems.append(f'{what}: {m.group(0)!r}')
                break
    for m in TECHNOLOGY.finditer(text):
        if not re.search(r'\b' + re.escape(m.group(0).lower()) + r'\b', src_low):
            problems.append(f'technology, fuel or plant word: {m.group(0)!r}')
            break
    src_words = set(WORD_TOKEN.findall(src))
    src_lower = {w.lower() for w in src_words}
    for m in WORD_TOKEN.finditer(text):
        w = m.group(0)
        if w in src_words or not any(c.isupper() for c in w):
            continue
        before = text[:m.start()].rstrip()
        sentence_start = not before or before[-1] in '.!?:;('
        if sentence_start and w[1:] == w[1:].lower() and (w.lower() in src_lower or w.lower() in STARTERS
                                                           or COMMON_ENDING.search(w)):
            continue
        problems.append(f'name or code not in the facts: {w!r}')
        break
    if re.search(r'[A-Za-z]\d|\d[A-Za-z]', re.sub(r'\d[\d,]*(?:\.\d+)?(?:st|nd|rd|th)\b', ' ', text)):
        problems.append('a code mixing letters and figures')
    return problems


def saved_path(directory, key):
    if not (type(key) is str and KEY.fullmatch(key)):
        raise ValueError('alert key')
    return Path(directory).joinpath(*SAVED_DIR, key + '.json')


def load_saved(directory, alert):
    """An optional saved AI phrasing for this alert, or None when absent, unreadable or made for another
    alert, region or peak interval."""
    try:
        value = json.loads(saved_path(directory, alert['key']).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if (type(value) is not dict or value.get('key') != alert['key'] or value.get('region') != alert['region']
            or value.get('interval_manila') != alert['interval_manila']):
        return None
    return value


def answer(alert, result, saved=None, card=None):
    """The API answer: {drivers, context, summary, paragraph, phrased_by, cache, as_of, basis, note, ontology, ...}.
    `saved` wording is used only when its facts_hash equals these facts' hash, it was marked verified when
    saved, and it passes `verify_phrasing` again here. `card` is the saved full ontology card for this alert
    and peak (src/alerts/ontology.py `load_card`), or None."""
    composed = compose(alert, result)
    fh = facts_hash(composed['text'])
    out = {'status': 'ok', 'key': alert['key'], 'region': alert['region'], 'interval_manila': alert['interval_manila'],
           'heading': HEADING, 'basis': BASIS, 'drivers': ranked(result), 'summary': summarise(alert, result),
           'context': _context(result), 'baseline_from': (result or {}).get('from'),
           'composed': composed['text'], 'paragraph': composed['text'], 'facts_hash': fh,
           'phrased_by': None, 'cache': {'state': 'no saved phrasing'}, 'as_of': None, 'note': NOTE_NO_AI,
           'ontology': card}
    if not (saved and saved.get('phrased_by')):
        return out
    if saved.get('facts_hash') != fh:
        out['cache'] = {'state': 'saved phrasing is for other facts; not shown'}
    elif (saved.get('verified') is not True or type(saved.get('paragraph')) is not str
          or verify_phrasing(composed['text'], saved['paragraph'], composed['entities'])):
        out['cache'] = {'state': 'saved phrasing did not pass the check; not shown'}
    else:
        out.update(paragraph=saved['paragraph'], phrased_by=saved['phrased_by'], as_of=saved.get('as_of'),
                   cache={'state': 'saved phrasing for these facts'}, note=None)
    return out


def _context(result):
    c = (result or {}).get('context')
    if not c or c.get('value_at_t') is None:
        return None
    pct = None if c.get('indicator_score') is None else round(c['indicator_score'] * 100)
    return {'name': 'Price (context, never a driver)', 'value': c['value_at_t'], 'median': c.get('baseline_median'),
            'unit': 'PHP/MWh', 'percentile': pct}
