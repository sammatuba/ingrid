#!/usr/bin/env python3
"""The driver card in words (ontology intent, slice O4): a composed paragraph, and a Gemini phrasing of it.

Code writes the facts; the model only rewords them. ``compose`` turns one recorded card and its likely-
drivers ranking (JSON rows exported by ``scripts/ontology/record_cards.sh`` into the ignored
``.local/ontology/cards/``) into template sentences: the price, the ranked likely drivers against their
28-day baseline, the operator messages known by the cutoff, the unconfirmed matches (named only as
unconfirmed), what was withheld, and fuel as cost context. ``verify`` checks a phrasing against the
composed text: every figure of the composed text is kept, no new figure appears, every named entity is
kept, and no causal wording appears ("likely driver" and "most unusual" are allowed; "caused",
"because", "due to", "drove", "led to", "triggered", "resulted in" are not). A phrasing that fails is
not used; the composed text is.

Fuel group and technology stay internal (owner decision 2026-10-17): the composed text says only "fuel
context available". The second case is not on the transport's real-case allowlist
(``src/adapters/gemini/transport.py``), so only the PEDC case may be sent; the other keeps its template.

Commands::

    phrase_card.py compose --case pedc-u2-2026-09-21          # print the composed paragraph
    phrase_card.py run --case pedc-u2-2026-09-21 --config .local/ontology/gemini/config.json
    phrase_card.py verify --case pedc-u2-2026-09-21 --phrased .local/ontology/gemini/<case>/result.json
    phrase_card.py explain-facts --case pedc-u2-2026-09-21    # print the per-family fact lines
    phrase_card.py explain --case pedc-u2-2026-09-21 --config .local/ontology/gemini/config.json

Per-family explanations (``explain``): for each ranked family of the assumed ranking, code writes one fact
line (its indicators, values, medians and percent of the baseline); Gemini answers one or two sentences
saying what was unusual and how such a condition can push the price up or down. Each sentence is checked
against its own fact line: no figure that is not in the line, no causal or past-tense claim (only "can"),
no advice, at most two sentences. A sentence that fails is dropped (the page then shows none for that
family). The result goes to ``.local/ontology/gemini/<case>/explain.json`` for bake_panel.py.

Exit codes: 0 clean, 1 verification failed, 2 usage or input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / '.local' / 'ontology' / 'cards'
RUNS = ROOT / '.local' / 'ontology' / 'gemini'
TRANSMITTABLE = {'pedc-u2-2026-09-21'}  # the transport's allowlist; checked again by the transport
CASES = {
    'pedc-u2-2026-09-21': {'region': 'Visayas', 'when': '13:40 on 21 September 2026', 'hour': 13},
    'cvis-2026-06-25-0910': {'region': 'Visayas', 'when': '09:10 on 25 June 2026', 'hour': 9},
}
FAMILY = {'D': 'demand', 'S': 'supply and interconnection', 'O': 'outages', 'Rules': 'rules and grid constraints',
          'F': 'fuel cost baseline'}
INDICATOR = {
    'demand_mw': ('demand', 'MW', 0), 'import_share': ('import share', '', 3),
    'reserve_shortfall_mw': ('reserve shortfall', 'MW', 0), 'hvdc_links_congested': ('congested HVDC links', '', 0),
    'scheduled_outage_mw': ('capacity scheduled out', 'MW', 0), 'linked_derated_mw': ('linked derated capacity', 'MW', 0),
    'coal_driver': ('coal price', '', 1), 'lng_driver': ('LNG price', '', 1),
    'congested_elements': ('congested transmission elements at the region\'s stations', '', 0),
    'congestion_overload_mw': ('congestion overload', 'MW', 0),
}
FLAG = {'cap_bound': 'price cap bound', 'admin_priced': 'administered price', 'secondary_cap': 'secondary cap',
        'price_mitigated': 'price mitigated', 'price_substituted': 'price substituted'}
INSTRUCTION_VERSION = 1
INSTRUCTION = (
    "Rewrite the sentences below as one paragraph of plain English for an energy trading desk. Keep every "
    "figure, unit, name and time exactly as given, character for character. Add no figure, name or time. "
    "Remove no sentence. Never state or imply a cause: do not write caused, because, due to, drove, led to, "
    "triggered or resulted in; you may say \"likely driver\" or \"most unusual\". Matches marked unconfirmed "
    "stay unconfirmed. Answer with one JSON object: {\"text\": \"<the paragraph>\"}."
)
CAUSAL = re.compile(r"\b(caus(e|ed|es|ing)|because|due to|dr(o|i)ve[ns]?|driven|led to|lead(s)? to|trigger(ed|s)?|result(ed|s)? in|owing to)\b", re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


class InputError(Exception):
    pass


def load(case: str, kind: str, mode: str = 'assumed') -> list:
    path = CARDS / f'{case}-{kind}-{mode}.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f'cannot read {path}: {exc}') from None


def load_summary(case: str, mode: str = 'assumed'):
    """The recorded card_summary row (severity, confidence, ...) if record_cards.sh exported one."""
    path = CARDS / 'recorded_summary.json'
    if not path.exists():
        return None
    rows = [r for r in json.loads(path.read_text(encoding='utf-8')) if r.get('case_id') == case and r.get('mode') == mode]
    return rows[0] if rows else None


def num(value, digits=0) -> str:
    x = float(value)
    return f'{x:,.{digits}f}'


def compose(case: str) -> dict:
    """Template sentences from the recorded card and ranking (assumed mode); returns text and entities."""
    if case not in CASES:
        raise InputError(f'unknown case {case}')
    card, drivers = load(case, 'card'), load(case, 'drivers')
    meta = CASES[case]
    facts = [r for r in card if r.get('section') == 'fact']
    unconf = [r for r in card if r.get('section') == 'unconfirmed']
    withheld = [r for r in card if r.get('section') == 'withheld']
    price = next((r for r in facts if r.get('predicate') == 'price_capped_median'), None)
    out, names = [], [meta['region']]
    if price:
        out.append(f"At {meta['when']}, the {meta['region']} capped median price was {num(price['value_num'])} PHP/MWh.")
    ranked = sorted((r for r in drivers if r.get('rank') and r.get('status') == 'scored'),
                    key=lambda r: (int(r['rank']), -float(r['indicator_score'] or 0)))
    best = {}
    for r in ranked:
        best.setdefault(r['family'], r)
    parts = []
    for fam, r in sorted(best.items(), key=lambda kv: int(kv[1]['rank'])):
        label, unit, d = INDICATOR.get(r['indicator'], (r['indicator'], '', 2))
        if fam == 'F':
            parts.append(f"{FAMILY[fam]} (fuel context available, percentile {num(float(r['indicator_score']) * 100)})")
            continue
        u = f' {unit}' if unit else ''
        parts.append(f"{FAMILY[fam]} ({label} {num(r['value_at_t'], d)}{u} against a median of "
                     f"{num(r['baseline_median'], d)}{u}, percentile {num(float(r['indicator_score']) * 100)})")
    if parts:
        out.append('Likely drivers, ranked by how unusual each was against the last 28 days at this hour '
                   '(evidence, not proof): ' + '; '.join(parts) + '.')
    nodata = sorted({r['family'] for r in drivers if r.get('family') in FAMILY and r.get('status') == 'no data'
                     and not any(x['family'] == r['family'] and x.get('status') == 'scored' for x in drivers)})
    if nodata:
        out.append('No data for ' + ', '.join(FAMILY[f] for f in nodata) + '.')
    msgs = [r for r in facts if str(r.get('predicate', '')).startswith('mention_') and r.get('match_confidence') == 'confirmed']
    if msgs:
        items = []
        for r in sorted(msgs, key=lambda r: r['known_by_utc']):
            items.append(f"{r['predicate'].replace('mention_', '')} {r['value_text']}")
            names.append(r['value_text'])
        out.append('Operator messages known by the cutoff name: ' + '; '.join(items) + '.')
    outages = sorted({r['subject_label'] for r in facts if r.get('predicate') == 'scheduled_outage'})
    if outages:
        out.append('Schedule records active: ' + ', '.join(outages) + '.')
        names.extend(outages)
    if unconf:
        texts = sorted({r['value_text'] for r in unconf if r.get('value_text')})
        out.append(f'{len(texts)} unconfirmed plant matches are listed, not counted.')
    summary = load_summary(case)
    if summary:
        out.append(f"Severity {summary['severity']}; confidence {summary['confidence']}; financial impact not "
                   f"available without portfolio data.")
    n_withheld = sum(int(r['n_withheld']) for r in withheld)
    if n_withheld:
        out.append(f'{n_withheld} facts were withheld as not yet known at the cutoff.')
    return {'case': case, 'text': ' '.join(out), 'entities': names}


def verify(composed: dict, phrased: str) -> list:
    problems = []
    # figures compared as multisets: a dropped repeat or an invented repeat fails too
    want = Counter(t.replace(',', '') for t in NUMBER.findall(composed['text']))
    got = Counter(t.replace(',', '') for t in NUMBER.findall(phrased))
    for missing in sorted((want - got).elements()):
        problems.append(f'figure {missing} missing')
    for extra in sorted((got - want).elements()):
        problems.append(f'figure {extra} not in the card')
    for name in composed['entities']:
        if name not in phrased:
            problems.append(f'name {name!r} missing')
    if CAUSAL.search(phrased):
        problems.append(f'causal wording: {CAUSAL.search(phrased).group(0)!r}')
    if 'unconfirmed' in composed['text'] and 'unconfirmed' not in phrased.lower():
        problems.append('unconfirmed matches not marked unconfirmed')
    return problems


def body_for(composed: dict, max_output_tokens: int) -> dict:
    return {
        'systemInstruction': {'parts': [{'text': INSTRUCTION}]},
        'contents': [{'role': 'user', 'parts': [{'text': composed['text']}]}],
        'generationConfig': {'candidateCount': 1, 'maxOutputTokens': max_output_tokens,
                             'responseFormat': {'text': {'mimeType': 'APPLICATION_JSON'}},
                             'thinkingConfig': {'thinkingBudget': 0}},
    }


def write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def run(case: str, config_path: Path) -> int:
    composed = compose(case)
    record = {'case': case, 'instruction_version': INSTRUCTION_VERSION, 'composed': composed['text'],
              'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    out = RUNS / case / 'result.json'
    if case not in TRANSMITTABLE:
        record.update(result='template', reason='case not on the transport real-case allowlist; composed text kept',
                      text=composed['text'])
        write_private(out, record)
        print(f'{case}: template (not transmittable)')
        return 0
    sys.path.insert(0, str(ROOT))
    from src.adapters.gemini.transport import GeminiTransport, LiveConfig
    from src.judgment import JudgmentUnavailable
    config = LiveConfig.from_dict(json.loads(config_path.read_text(encoding='utf-8')))
    transport = GeminiTransport(config, RUNS / case / 'ledger.sqlite3')
    body = body_for(composed, config.max_output_tokens)
    try:
        response = transport(config.model, body, case=case, timeout_seconds=config.timeout_seconds,
                             max_response_bytes=config.max_response_bytes)
        text = json.loads(response['candidates'][0]['content']['parts'][0]['text'])['text']
        problems = verify(composed, text)
        record.update(phrased=text, problems=problems,
                      result='phrased' if not problems else 'template',
                      text=text if not problems else composed['text'])
    except (JudgmentUnavailable, KeyError, IndexError, TypeError, ValueError) as exc:
        record.update(result='template', reason=f'model call failed: {getattr(exc, "code", type(exc).__name__)}',
                      text=composed['text'])
    record['receipt'] = transport.last_receipt
    write_private(out, record)
    print(f"{case}: {record['result']}" + (f" ({record.get('problems')})" if record.get('problems') else ''))
    return 0 if record['result'] == 'phrased' else 1


def hour_span(hour: int) -> str:
    return f'{hour:02d}:00 to {hour + 1:02d}:00'


def pct_words(score, span: str, base: str = '') -> str:
    """The percentile in words, naming what it is compared with (the page uses the same wording)."""
    p = round(float(score) * 100)
    base = base or f'the five-minute intervals from {span} on the last 28 days'
    if p >= 55:
        return f'higher than {p}% of {base}'
    if p <= 45:
        return f'lower than usual: only {p}% of {base} were lower'
    return f'about usual ({p}%, in the middle of {base})'


EXPLAIN_VERSION = 2
EXPLAIN_INSTRUCTION = (
    "You explain a likely-drivers ranking to an energy trading desk. For each family below, write one or two "
    "plain sentences saying what was unusual about it at the interval, or that it was about usual. Describe "
    "only what the facts say, using the facts' own words; say nothing about prices or any effect on them "
    "(a fixed general note is added by code). Use only figures that appear in that family's facts, written "
    "exactly as given; add no figure, name or time. Never use because, due to, led to, triggered, resulted "
    "in, can, may, might, will or would. No advice. Answer with one JSON object: "
    "{\"explanations\": [{\"family\": \"<code>\", \"text\": \"<sentences>\"}]}."
)
CLAIM = re.compile(r"\b(pushed|raised|lifted|lowered|increased|decreased|explains?|explained|made the price|"
                   r"buy|sell|hedge|should|recommend\w*|proof|proves?|certainly|definitely)\b", re.I)
# The general effect on price is never written by the model. It is a fixed note per family, in code, shown
# beside a checked explanation. The model's text is checked by an allowlist of words, not a list of bad
# words: every word must come from that family's fact line (pricing-flag names count only as whole names)
# or from PLAIN_WORDS, which hold no verb of effect, no modal and no word for price or market.
EFFECT_NOTE = {
    'D': 'In general, demand above its usual level can push prices up, and demand below it can push prices down.',
    'S': 'In general, thinner reserves or a larger share of imports over limited links can push prices up.',
    'O': 'In general, more capacity out of service than usual can push prices up.',
    'Rules': 'In general, congestion on transmission elements can push prices up in the area it separates.',
    'F': 'In general, higher fuel costs can push prices up over months rather than within a day.',
}
EFFECT_NOTE_KIND = 'general note written by the team, not a finding about this interval'
PLAIN_WORDS = frozenset('''
a an the this that these those it its they them their there here s
is are was were be been being had has have
and or but nor as so while also both either neither
of at in on to from with by for into over under within across between per
than then when where which what who
no not none only any all each every other another one two few
about around roughly nearly almost close near just exactly
more most less least much many very slightly somewhat fairly quite well far rather
higher lower high low highest lowest above below
usual unusual unusually normal typical typically notable notably middle
value values level levels reading readings recorded figure
same hour hours day days interval intervals minute minutes period
compared against median share percent zero
'''.split())
WORD = re.compile(r"[a-z]+")
FLAG_SENTENCE = re.compile(r";? ?pricing flags set at the interval: [^.;]*")
PRICE_WORD = re.compile(r"\b(?:pric\w*|lmps?|tariffs?|clearing|bids?|offers?|php|pesos?|markets?|rates?|"
                        r"spot)\b", re.I)
MODAL = re.compile(r"\b(?:can|could|may|might|will|would|must|shall|tends?)\b", re.I)
EFFECT_VERB = re.compile(r"\b(?:push|rais|lift|boost|increas|decreas|reduc|driv|affect|influenc|pressur|elevat|"
                         r"inflat|depress|contribut|spik|lead|caus|impact|determin|alter|chang|shap|set|"
                         r"weigh|worsen)\w*", re.I)


def strip_flags(text: str) -> str:
    out = text
    for name in FLAG.values():
        out = re.sub(r'\b' + re.escape(name) + r'\b', ' ', out, flags=re.I)
    return out


def effect_problem(text: str):
    """The first word for price, modal or effect verb in a model text (pricing-flag names aside), or None.
    The bake re-checks with this where the fact line is not at hand; verify_explanation also checks words."""
    rest = strip_flags(text)
    for rx in (PRICE_WORD, MODAL, EFFECT_VERB):
        m = rx.search(rest)
        if m:
            return m.group(0)
    return None


def unknown_words(facts: str, text: str) -> list:
    """Words of the text found neither in the family's fact line nor in PLAIN_WORDS."""
    flags = [n for n in FLAG.values() if n in facts]
    vocab = set(WORD.findall(FLAG_SENTENCE.sub(' ', NUMBER.sub(' ', facts)).lower())) | PLAIN_WORDS
    vocab -= set(w.lower() for w in PRICE_WORD.findall(facts))
    rest = text
    for name in flags:
        rest = re.sub(r'\b' + re.escape(name) + r'\b', ' ', rest, flags=re.I)
    rest = NUMBER.sub(' ', rest).lower()
    return sorted({w for w in WORD.findall(rest) if w not in vocab})


SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def family_facts(case: str, mode: str = 'assumed') -> list:
    """One fact line per ranked family of the recorded ranking, in rank order."""
    if case not in CASES:
        raise InputError(f'unknown case {case}')
    meta, drivers = CASES[case], load(case, 'drivers', mode)
    span = hour_span(meta['hour'])
    ranked = {}
    for r in drivers:
        if r.get('rank') is not None and r.get('family') in FAMILY:
            ranked.setdefault(r['family'], {'rank': int(r['rank']), 'score': r.get('family_score'), 'rows': []})['rows'].append(r)
    out = []
    for fam, g in sorted(ranked.items(), key=lambda kv: kv[1]['rank']):
        parts = []
        for r in g['rows']:
            if r.get('status') != 'scored' or r.get('indicator_score') is None:
                if fam != 'F':
                    parts.append(f"{INDICATOR.get(r['indicator'], (str(r['indicator']).replace('_', ' '),))[0]}: no data")
                continue
            if fam == 'F':
                parts.append(f"fuel cost level: {pct_words(r['indicator_score'], span, 'its own monthly history')} "
                             f"(a slow-moving cost level, not an intra-day move)")
                continue
            label, unit, d = INDICATOR.get(r['indicator'], (str(r['indicator']).replace('_', ' '), '', 2))
            u = f' {unit}' if unit else ''
            parts.append(f"{label} {num(r['value_at_t'], d)}{u} against a median of {num(r['baseline_median'], d)}{u}, "
                         f"{pct_words(r['indicator_score'], span)}")
        if fam == 'Rules':
            flags = [FLAG[r['indicator']] for r in drivers if r.get('family') == 'Rules' and r.get('status') == 'present'
                     and r.get('indicator') in FLAG]
            if flags:
                parts.append('pricing flags set at the interval: ' + ', '.join(flags))
        line = (f"{FAMILY[fam]} (rank {g['rank']}), {meta['region']} at {meta['when']}: " + '; '.join(parts) + '.')
        out.append({'family': fam, 'rank': g['rank'], 'facts': line})
    return out


def verify_explanation(facts: str, text: str) -> list:
    problems = []
    allowed = {t.replace(',', '') for t in NUMBER.findall(facts)}
    for figure in NUMBER.findall(text):
        if figure.replace(',', '') not in allowed:
            problems.append(f'figure {figure} not in the facts')
    if CAUSAL.search(text):
        problems.append(f'causal wording: {CAUSAL.search(text).group(0)!r}')
    if CLAIM.search(text):
        problems.append(f'claim or advice wording: {CLAIM.search(text).group(0)!r}')
    if effect_problem(text):
        problems.append(f'effect or price wording (the effect note is added by code): {effect_problem(text)!r}')
    unknown = unknown_words(facts, text)
    if unknown:
        problems.append(f'words not in the facts or the plain-word list: {", ".join(unknown[:5])}')
    if len(SENTENCE_END.findall(text.strip())) > 2:
        problems.append('more than two sentences')
    if not text.strip():
        problems.append('empty')
    return problems


def explain(case: str, config_path: Path) -> int:
    items = family_facts(case)
    record = {'case': case, 'mode': 'assumed', 'instruction_version': EXPLAIN_VERSION, 'facts': items,
              'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'explanations': {}}
    out = RUNS / case / 'explain.json'
    if case not in TRANSMITTABLE:
        record['reason'] = 'case not on the transport real-case allowlist; no explanation (none is shown)'
        write_private(out, record)
        print(f'{case}: none (not transmittable)')
        return 0
    sys.path.insert(0, str(ROOT))
    from src.adapters.gemini.transport import GeminiTransport, LiveConfig
    from src.judgment import JudgmentUnavailable
    config = LiveConfig.from_dict(json.loads(config_path.read_text(encoding='utf-8')))
    transport = GeminiTransport(config, RUNS / case / 'ledger.sqlite3')
    body = {
        'systemInstruction': {'parts': [{'text': EXPLAIN_INSTRUCTION}]},
        'contents': [{'role': 'user', 'parts': [{'text': json.dumps([{'family': i['family'], 'facts': i['facts']} for i in items])}]}],
        'generationConfig': {'candidateCount': 1, 'maxOutputTokens': config.max_output_tokens,
                             'responseFormat': {'text': {'mimeType': 'APPLICATION_JSON'}},
                             'thinkingConfig': {'thinkingBudget': 0}},
    }
    checks = {}
    try:
        response = transport(config.model, body, case=case, timeout_seconds=config.timeout_seconds,
                             max_response_bytes=config.max_response_bytes)
        answer = json.loads(response['candidates'][0]['content']['parts'][0]['text'])['explanations']
        by_family = {i['family']: i for i in items}
        for a in answer:
            fam, text = a.get('family'), str(a.get('text') or '').strip()
            if fam not in by_family or fam in checks:
                continue
            problems = verify_explanation(by_family[fam]['facts'], text)
            checks[fam] = {'text': text, 'problems': problems}
            if not problems:
                record['explanations'][fam] = text
        record['checks'] = checks
    except (JudgmentUnavailable, KeyError, IndexError, TypeError, ValueError) as exc:
        record['reason'] = f'model call failed: {getattr(exc, "code", type(exc).__name__)}; no explanation shown'
    record['receipt'] = transport.last_receipt
    write_private(out, record)
    print(f"{case}: {len(record['explanations'])} of {len(items)} families explained"
          + ''.join(f"; {f} dropped ({c['problems']})" for f, c in checks.items() if c['problems']))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('command', choices=['compose', 'run', 'verify', 'explain-facts', 'explain'])
    ap.add_argument('--case', required=True)
    ap.add_argument('--config', type=Path)
    ap.add_argument('--phrased', type=Path)
    a = ap.parse_args(argv)
    try:
        if a.command == 'compose':
            c = compose(a.case)
            print(c['text'])
            print('request digest (instruction + text):',
                  hashlib.sha256((INSTRUCTION + c['text']).encode('utf-8')).hexdigest()[:16])
            return 0
        if a.command == 'explain-facts':
            for i in family_facts(a.case):
                print(i['facts'])
            return 0
        if a.command == 'explain':
            if not a.config:
                raise InputError('explain needs --config')
            return explain(a.case, a.config)
        if a.command == 'run':
            if not a.config:
                raise InputError('run needs --config')
            return run(a.case, a.config)
        phrased = json.loads(a.phrased.read_text(encoding='utf-8'))['phrased']
        problems = verify(compose(a.case), phrased)
        print('\n'.join(problems) or 'verified')
        return 1 if problems else 0
    except InputError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
