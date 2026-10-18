#!/usr/bin/env python3
"""Bake the "Why this price" panel data (ontology intent, slice O5) from the recorded, checked cards.

Reads the ignored export of ``scripts/ontology/record_cards.sh`` (``.local/ontology/cards/``) and the O4
result (``.local/ontology/gemini/<case>/result.json``) and writes one public file per case,
``<data>/ontology/<case>.json``, beside the rest of the baked desk data (``build/grid-data`` by default).
The page reads only that file: no BigQuery at runtime.

Public by construction: fuel rows are reduced to a count ("fuel context available"), so no fuel value,
fuel group or technology leaves the export; rows marked ``public = false`` never pass; unconfirmed
matches keep their own block with the plant text and the reason, never a candidate plant code. Every
fact keeps its known-by time and its assumption id; the three modes stay separate so the page can
toggle them. ``--check`` builds in memory, validates, and writes nothing.

    bake_panel.py                      # -> build/grid-data/ontology/<case>.json
    bake_panel.py --check
    bake_panel.py --data DIR --cards DIR --runs DIR
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = {'pedc-u2-2026-09-21': ('Visayas', '2026-09-21T13:40:00+08:00'),
         'cvis-2026-06-25-0910': ('Visayas', '2026-06-25T09:10:00+08:00')}
MODES = ('assumed', 'hindsight', 'strict')
FACT_KEYS = ('family', 'subject_label', 'predicate', 'value_num', 'value_text', 'unit', 'valid_from_utc',
             'known_by_utc', 'assumed_known_by_utc', 'availability_assumption', 'availability_at_cutoff',
             'source_table', 'review_state', 'match_confidence', 'object_label')
FUEL_TIMING_KEYS = ('valid_from_utc', 'known_by_utc', 'assumed_known_by_utc', 'availability_assumption',
                    'availability_at_cutoff')
INTERNAL = ('fuel_group', 'technology', 'fuel_role', 'coal_driver', 'lng_driver', 'candidate_id', 'candidate_label')
SUMMARY_KEYS = ('severity', 'severity_reason', 'financial_impact', 'confidence', 'confidence_reason',
                'relationship_trail', 'what_to_check')


class BakeError(Exception):
    pass


def read(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise BakeError(f'cannot read {path}: {exc}') from None


def truthy(v) -> bool:
    return v is True or str(v).lower() == 'true'


def phrase_module():
    spec = importlib.util.spec_from_file_location('phrase_card', Path(__file__).resolve().parent / 'phrase_card.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def checked_explanations(case: str, cards: Path, e: dict) -> dict:
    """The explanations that still pass phrase_card.py's check against today's fact lines: a sentence whose
    recorded fact line differs from the current one (stale), or that fails the check, is dropped."""
    pc = phrase_module()
    pc.CARDS = cards
    mode = e.get('mode') or 'assumed'
    current = {i['family']: i['facts'] for i in pc.family_facts(case, mode)}
    recorded = {i.get('family'): i.get('facts') for i in (e.get('facts') or [])}
    return {f: t for f, t in (e.get('explanations') or {}).items()
            if f in current and t and recorded.get(f) == current[f] and not pc.verify_explanation(current[f], t)}


def bake_case(case: str, cards: Path, runs: Path = ROOT / '.local' / 'ontology' / 'gemini') -> dict:
    region, t = CASES[case]
    out = {'case': case, 'region': region, 't': t, 'source': 'grid_ontology.driver_card, likely_drivers, card_summary '
           '(recorded and checked by scripts/ontology/record_cards.sh)',
           'heading': None, 'modes': {}, 'drivers': {}, 'summary': None, 'paragraph': None, 'explanations': None}
    for mode in MODES:
        rows = read(cards / f'{case}-card-{mode}.json')
        facts = [r for r in rows if r.get('section') == 'fact']
        public = [r for r in facts if r.get('family') != 'F' and truthy(r.get('public'))]
        out['modes'][mode] = {
            'cutoff_utc': rows[0]['cutoff_utc'] if rows else None,
            'facts': [{k: r.get(k) for k in FACT_KEYS} for r in public],
            'fuel_context': sum(1 for r in facts if r.get('family') == 'F'),
            # when each fuel row was known, with its assumption id (A-FUEL); never its series, value or role
            'fuel_timing': [{k: r.get(k) for k in FUEL_TIMING_KEYS} for r in facts if r.get('family') == 'F'],
            'unconfirmed': [{'label': 'Unconfirmed matches (not counted)', 'plant_text': r.get('value_text'),
                             'kind': r.get('predicate'), 'known_by_utc': r.get('known_by_utc'),
                             'reason': r.get('match_reason')} for r in rows if r.get('section') == 'unconfirmed'],
            'withheld': [{'family': r.get('family'), 'reason': r.get('withheld_reason'), 'n': int(r.get('n_withheld') or 0)}
                         for r in rows if r.get('section') == 'withheld'],
        }
        path = cards / f'{case}-drivers-{mode}.json'
        if path.exists():
            drv = read(path)
            out['heading'] = out['heading'] or next((r['heading'] for r in drv if r.get('heading')), None)
            out['drivers'][mode] = [{
                'rank': r.get('rank'), 'family': r.get('family'), 'status': r.get('status'),
                'indicator': 'fuel cost baseline' if r.get('family') == 'F' else r.get('indicator'),
                'family_score': r.get('family_score'), 'indicator_score': r.get('indicator_score'),
                'value_at_t': None if r.get('family') == 'F' else r.get('value_at_t'),
                'baseline_median': None if r.get('family') == 'F' else r.get('baseline_median'),
                'unit': None if r.get('family') == 'F' else r.get('unit'),
                'value_text': None if r.get('family') == 'F' else r.get('value_text'),
                'known_at_utc': r.get('known_at_utc'), 'availability_assumption': r.get('availability_assumption'),
                'source_table': r.get('source_table'),
                # how many past intervals the score was taken against (the "How we got this" modal)
                'baseline_n': None if r.get('family') == 'F' else r.get('baseline_n')} for r in drv]
    summ = [r for r in read(cards / 'recorded_summary.json') if r.get('case_id') == case and r.get('mode') == 'assumed']
    if summ:
        out['summary'] = {k: summ[0].get(k) for k in SUMMARY_KEYS}
    result = runs / case / 'result.json'
    r = read(result) if result.exists() else None
    if r is not None:
        out['paragraph'] = {'text': r.get('text'), 'kind': 'phrased by Gemini, verified' if r.get('result') == 'phrased'
                            else 'composed by code (template)',
                            'model': (r.get('receipt') or {}).get('model_version')}
    # per-family explanations: re-checked here against the current fact lines, not trusted from the file
    explain = runs / case / 'explain.json'
    e = read(explain) if explain.exists() else None
    if e is not None:
        items = checked_explanations(case, cards, e)
        if items:
            pc = phrase_module()
            out['explanations'] = {'mode': e.get('mode') or 'assumed', 'items': items,
                                   'kind': 'explained by Gemini, checked against the facts',
                                   'notes': {f: pc.EFFECT_NOTE[f] for f in items if f in pc.EFFECT_NOTE},
                                   'notes_kind': pc.EFFECT_NOTE_KIND,
                                   'model': (e.get('receipt') or {}).get('model_version')}
    out['provenance'] = provenance(case, cards, out, r, e)
    return out


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def provenance(case: str, cards: Path, out: dict, r, e) -> dict:
    """How the record was made, for the page's "How we got this" modal: the ranking's baseline window as
    data (read from the recorded heading, so the words follow the SQL), when the cards were exported and
    baked, and the run details of the recorded AI steps. Metadata only: no prompt, digest, project,
    request or response id, and nothing from BigQuery or a model call."""
    m = re.search(r'last (\d+) days at this hour', out.get('heading') or '')
    exported = [p.stat().st_mtime for p in cards.glob(f'{case}-*.json')]
    pv = {'baseline': {'days': int(m.group(1)), 'hour': 'same Manila hour of day', 'excludes_t': True,
                       'score': '(past values below + half of those equal) / number of past values'} if m else None,
          'recorded_at_utc': utc(max(exported)) if exported else None,
          'baked_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
          'paragraph': None, 'explanations': None}
    if r is not None:
        rc = r.get('receipt') or {}
        pv['paragraph'] = {'result': r.get('result'), 'attempt': rc.get('attempt'),
                           'max_attempts': (rc.get('limits') or {}).get('max_attempts'),
                           'run_at_utc': r.get('run_at_utc'), 'instruction_version': r.get('instruction_version'),
                           'problems_n': len(r.get('problems') or []) if 'problems' in r else None,
                           'api': rc.get('api')}
    if e is not None:
        kept = len((out.get('explanations') or {}).get('items') or {})
        pv['explanations'] = {'run_at_utc': e.get('run_at_utc'), 'kept_n': kept,
                              'dropped_n': max(0, len(e.get('explanations') or {}) - kept)}
    return pv


def validate(baked: dict) -> list:
    problems = []
    text = json.dumps(baked)
    for word in INTERNAL:
        if word in text:
            problems.append(f"{baked['case']}: internal field or value {word!r} in the bake")
    for mode, block in baked['modes'].items():
        for f in block['facts']:
            if f['family'] == 'F':
                problems.append(f"{baked['case']} {mode}: a fuel fact in the public facts")
            if f.get('availability_at_cutoff') == 'assumed' and not f.get('availability_assumption'):
                problems.append(f"{baked['case']} {mode}: an assumed fact without its assumption id")
            if mode == 'strict' and f.get('availability_at_cutoff') != 'evidenced':
                problems.append(f"{baked['case']} {mode}: a strict fact that is not evidence-known")
        for f in block.get('fuel_timing', []):
            if f.get('availability_at_cutoff') == 'assumed' and f.get('availability_assumption') != 'A-FUEL':
                problems.append(f"{baked['case']} {mode}: an assumed fuel row without its A-FUEL assumption id")
        for u in block['unconfirmed']:
            if not u['reason'] or not u['plant_text']:
                problems.append(f"{baked['case']} {mode}: an unconfirmed match without its text or reason")
    s = baked.get('summary') or {}
    if s and any(ch.isdigit() for ch in s.get('financial_impact', '')):
        problems.append(f"{baked['case']}: a figure in financial_impact")
    ex = baked.get('explanations') or {}
    for fam, t in (ex.get('items') or {}).items():
        pc = phrase_module()
        if pc.CAUSAL.search(t) or pc.CLAIM.search(t) or pc.effect_problem(t):
            problems.append(f"{baked['case']}: causal or claim wording in the {fam} explanation")
    for fam, note in (ex.get('notes') or {}).items():
        if note != phrase_module().EFFECT_NOTE.get(fam):
            problems.append(f"{baked['case']}: the {fam} general note is not the fixed note in phrase_card.py")
    pv = baked.get('provenance') or {}
    if baked.get('heading') and not (pv.get('baseline') or {}).get('days'):
        problems.append(f"{baked['case']}: the baseline window is not in the provenance")
    for word in ('grid_', '.sql', '.sh', '.py', 'digest', 'project', 'response_id', 'run_id', 'permission'):
        if word in json.dumps(pv):
            problems.append(f"{baked['case']}: internal word {word!r} in the provenance")
    if 'evidence, not proof' not in (baked.get('heading') or ''):
        problems.append(f"{baked['case']}: the likely-drivers heading is missing")
    return problems


def tracked(path: Path) -> bool:
    r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(path)], capture_output=True)
    return r.returncode != 0 and str(path.resolve()).startswith(str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--data', type=Path, default=ROOT / 'build' / 'grid-data')
    ap.add_argument('--cards', type=Path, default=ROOT / '.local' / 'ontology' / 'cards')
    ap.add_argument('--runs', type=Path, default=ROOT / '.local' / 'ontology' / 'gemini')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    try:
        baked = [bake_case(c, a.cards, a.runs) for c in CASES]
    except BakeError as exc:
        print(exc, file=sys.stderr)
        return 2
    problems = [p for b in baked for p in validate(b)]
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 1
    if a.check:
        print(f'ok: {len(baked)} panel files validate (nothing written)')
        return 0
    out = a.data / 'ontology'
    if tracked(out / 'x.json'):
        print(f'refusing to write company data into a path Git would track: {out}', file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    for b in baked:
        (out / f"{b['case']}.json").write_text(json.dumps(b, ensure_ascii=False, allow_nan=False, indent=1) + '\n',
                                               encoding='utf-8')
    print(f'wrote {len(baked)} files to {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
