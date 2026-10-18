#!/usr/bin/env python3
"""Offline probe-bundle ablations A1 to A3 over the frozen synthetic fixtures (EVAL-2).

Reads every `pb-*.json` pair under `tests/fixtures/probe-bundle/`, replays its `h0.v1`
records and assumption seed through `InMemoryRepository`, compiles each declared compile
at its own information cutoff against the pair's single snapshot, renders the frozen
`probe-bundle.v4` bundle, answers it with the fixture backend and scores four conditions
against the frozen labels. Writes one JSON report under the ignored `.local/eval/`.

Conditions (working paper section 6, intent slice S5):

* ``single_render``      the single-render baseline: the model's own one-shot direction
                         answer (Q8 of the canonical ``f0`` form, read alone), mapped to a
                         relation label; no decomposition, no sufficiency gate, no receipt.
* ``bundle``             the full bundle: composition over the modal atomic answers with
                         the Q7 sufficiency gate and the stability downgrade.
* ``bundle_no_gate``     A2: the same bundle with the sufficiency gate off
                         (``tau_suff`` 0.0, so the gate row cannot fire).
* ``bundle_no_receipt``  A3: the same bundle with the stability downgrade off
                         (``tau_flip`` and ``tau_pol`` 1.0, so no flip rate or polarity
                         gap can ever be above them).

**The fixture backend is a script, not a model.** Slice S2 of
`docs/work/probe-bundle/intent.md` (the System One port and `FixtureSystemOne`) is not
built on this branch, no model, transport, credential or network call is reachable from
this file, and no live backend may be called by it. The answers it feeds to `compose` are
the pair file's frozen annotated atomic answers, one scripted answer per form at the
frozen probability, which is the same convention EVAL-1 used to record
``expected_composition``; the report therefore measures the *composition table and the
ablation wiring* on annotated synthetic evidence. It is labelled ``synthetic_fixture``
for that reason and is not analyst validation, not model accuracy and not evidence about
any backend.

**Truth and scoring.** The frozen per-compile label is the annotated truth. A condition
abstains when it labels a compile ``insufficient``. ``neither`` (the Q8 answer
"leave unchanged") is not one of the five frozen labels and the single-render baseline is
not given an abstain primitive (working paper section 1, citing D30: decision models
"have no abstain primitive"), so it scores as ``unrelated`` — evidence that does not bear
on the proposition. The report's sensitivity block records the alternative reading
(``neither`` as an abstention) so no reader has to guess what the choice cost.

**Splits and thresholds.** The compiles are split by pair, so both compiles of a
later-than-cutoff pair stay on one side: pair-id suffix 1 or 2 is calibration, 3 or 4 is
test. The composition thresholds are fixed on the calibration split only — a declared
candidate grid is scored there and one candidate is chosen under a declared tie-break;
the test split is not read before that choice is made. On a perfectly stable scripted
backend the candidates tie (noul tops are hard yes/no, so ``tau_suff``, ``tau_cond`` and
``tau_lineage`` cannot separate them, and every flip rate is 0), and the tie-break selects
the working paper's initial values, so no tuning occurs and the report says so rather than
claiming a tuned result.

**Determinism.** The report carries no clock reading, no interpreter version, no path
outside the repository and no environment value, so the same fixtures and the same code
produce the same bytes. Fixture integrity is re-verified against `manifest.json` and the
script exits non-zero on a mismatch instead of scoring a set that is not the frozen one.

Usage, from the repository root::

    /usr/bin/python3 scripts/eval/probe_bundle.py \
        --fixtures tests/fixtures/probe-bundle --out .local/eval/report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import canonical_dumps, compute_content_digest  # noqa: E402
from src.judgment.bundle import (BUNDLE_VERSION, DEFAULT_THRESHOLDS, ESCALATION,  # noqa: E402
                                 QUESTION_SPECS, compose, receipt, render_bundle)
from src.review import ActorContext, InMemoryRepository, reference  # noqa: E402
from src.review.records import validate_record  # noqa: E402

REPORT_SCHEMA = 'probe-bundle-ablation.v1'
#: Every number in the report is a measurement on a deterministic scripted backend over
#: fictional synthetic pairs; the label travels with the report so no reader can mistake
#: it for a live-backend or analyst measurement.
REPORT_LABEL = 'synthetic_fixture'
CONDITIONS = ('single_render', 'bundle', 'bundle_no_gate', 'bundle_no_receipt')
FIXTURE_SCHEMA = 'probe-bundle-fixture.v1'
#: The probability the scripted per-form answers carry. The frozen fixture packet records
#: the same convention; only top options feed composition, so the value is not material to
#: any label.
SCRIPTED_PROBABILITY = 0.8
NEITHER_LABEL = 'unrelated'
NEITHER_ALTERNATIVE = 'insufficient'
#: Threshold toggles that switch one mechanism off without changing the frozen code: the
#: gate row reads `_yes(q7) < tau_suff`, and `_yes` yields 0.0 or 1.0, so 0.0 disables it;
#: flip rate and polarity gap are at most 1.0 and the comparisons are strict, so 1.0
#: disables the downgrade.
GATE_OFF = {'tau_suff': 0.0}
RECEIPT_OFF = {'tau_flip': 1.0, 'tau_pol': 1.0}
#: The model's own single render is the canonical form's direction question: form 0 is
#: the un-permuted, un-aliased, un-negated presentation, so its answer is the one the
#: model gives without a presentation perturbation. The rest of the composition keeps
#: reading the modal top across every form, as the frozen table specifies.
CANONICAL_Q8 = 'q8_direction_f0'

CONDITION_DEFINITIONS = {
    'single_render': "the model's own single direction answer (Q8 of the canonical form f0, read alone) mapped to a "
                     'relation label; the A1 baseline',
    'bundle': 'composition over the modal atomic answers, with the Q7 sufficiency gate and the stability downgrade',
    'bundle_no_gate': 'the bundle with the sufficiency gate off (tau_suff 0.0); ablation A2',
    'bundle_no_receipt': 'the bundle with the stability downgrade off (tau_flip 1.0, tau_pol 1.0); ablation A3',
}

METRIC_DEFINITIONS = {
    'accuracy': 'share of evaluated compiles whose condition label equals the frozen label',
    'abstention_rate': 'share of compiles the condition labels `insufficient`',
    'abstentions_correct_when_frozen_insufficient': 'abstentions whose frozen label is `insufficient`',
    'abstentions_incorrect_when_frozen_definite': 'abstentions whose frozen label is a definite relation',
    'coverage': '1 - abstention_rate: the share of compiles the condition answers',
    'selective_accuracy': 'accuracy among the compiles the condition answers: only answered cases enter the numerator '
                          'and the denominator, so a correct abstention counts in `accuracy` but not here',
    'selective_accuracy_at_matched_coverage': 'accuracy on the compiles every condition answers, so all four '
                                              'conditions are read at one coverage and not at their own',
    'missed_challenges': 'frozen `challenges` where the condition gives a definite non-challenge label '
                         '(`supports`, `mixed` or `unrelated`): the change signal is silently lost',
    'challenge_abstentions': 'frozen `challenges` where the condition abstains: escalated rather than answered',
    'unsupported_revisions': 'the condition proposes action (`challenges` or `mixed`) where the frozen label is '
                             '`supports`, `unrelated` or `insufficient`',
    'identity_mismatches': "compiles whose modal Q1 is not the assumption's mapped entity, `cannot_tell` included; "
                           'the same reading for every condition, because the atomic answers are shared',
    'flip_rate_distribution': 'per-compile maximum and per-question flip rate over the forms, as the receipt '
                              'presents them',
}

#: The candidate grid the calibration split scores. `tau_cond` and `tau_lineage` are not
#: searched: no documented reading of the frozen table gives a second defensible value for
#: them, so the intent's initial value is the only candidate and the grid says so.
CALIBRATION_GRID = {
    'tau_suff': (0.5, 0.6),
    'tau_cond': (0.5,),
    'tau_lineage': (0.5,),
    'tau_flip': (0.25, 0.5),
    'tau_pol': (0.3, 0.5),
}

#: The declared tie-break, applied in order: higher calibration accuracy, then fewer
#: incorrect abstentions, then the smaller total distance from the intent's initial
#: threshold values, then lexicographic order of the candidate values so the choice is
#: total and reproducible.
TIE_BREAK = ('higher calibration accuracy', 'fewer incorrect abstentions',
             'smaller L1 distance from the intent initial thresholds', 'lexicographic order of the candidate values')

#: Pair-id suffix to split. Both compiles of a later-than-cutoff pair share a suffix and so
#: stay on one side; the rule is fixed here and never reads a label or a condition result.
SPLIT_RULE = 'pair-id suffix in (1, 2) is calibration; suffix in (3, 4) is test'
CALIBRATION_SUFFIXES = ('1', '2')
TEST_SUFFIXES = ('3', '4')


class FixtureProblem(Exception):
    """The fixture set or its replay does not match the frozen one; nothing is scored."""


def _rate(count: int, total: int):
    return None if not total else round(count / total, 6)


def split_of(pair_id: str) -> str:
    """The declared split for a pair id, or a `FixtureProblem` for an unknown suffix."""
    suffix = pair_id.rsplit('-', 1)[-1]
    if suffix in CALIBRATION_SUFFIXES:
        return 'calibration'
    if suffix in TEST_SUFFIXES:
        return 'test'
    raise FixtureProblem(f'{pair_id}: no declared split for suffix {suffix!r}')


def verify_fixture_digests(root: Path) -> dict:
    """Re-verify the frozen digests of the set before any of it is scored.

    Mirrors EVAL-1's digest rule: each file digest is the canonical digest of the parsed
    JSON, and the fixture digest is the canonical digest of the path-to-digest mapping
    over `annotation-policy.json` and the pair files (the manifest and `build.py` are not
    part of the frozen set). A mismatch stops the run instead of scoring a set that is
    not the frozen one.
    """
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    problems = []
    digests = {}
    for entry in manifest['files']:
        digests[entry['path']] = compute_content_digest(json.loads((root / entry['path']).read_text(encoding='utf-8')))
        if digests[entry['path']] != entry['digest']:
            problems.append(f"{entry['path']}: digest differs from the manifest")
    policy_path = manifest['annotation_policy']['path']
    policy_digest = compute_content_digest(json.loads((root / policy_path).read_text(encoding='utf-8')))
    if policy_digest != manifest['annotation_policy']['digest']:
        problems.append(f'{policy_path}: digest differs from the manifest')
    fixture_digest = compute_content_digest({policy_path: policy_digest,
                                             **{name: digests[name] for name in sorted(digests)}})
    if fixture_digest != manifest['fixture_digest']:
        problems.append('fixture digest differs from the manifest')
    if problems:
        raise FixtureProblem('; '.join(problems))
    return {
        'schema': manifest['schema'], 'frozen_at': manifest['frozen_at'], 'pairs': manifest['pairs'],
        'compiles': manifest['compiles'], 'policy_id': manifest['annotation_policy']['policy_id'],
        'policy_digest': policy_digest, 'fixture_digest': fixture_digest,
        'bundle_version_at_freeze': manifest['bundle_version_at_freeze'], 'digest_rule': manifest['digest_rule'],
        'root': str(root.relative_to(ROOT)) if root.is_relative_to(ROOT) else str(root),
        'integrity': {'verified': True, 'problems': [], 'manifest': 'manifest.json',
                      'no_backend_run_at_freeze': manifest['no_backend_run']},
    }


def scripted_answers(bundle: dict, atomic: dict, probability: float = SCRIPTED_PROBABILITY) -> dict:
    """Per-form answers whose top option is the frozen atomic answer in every form.

    The fixture backend's answers. A choice question answers in the token the form
    presents (canonical, permuted or aliased); a noul answers in the form's own polarity,
    so the negated form's probability is inverted.
    """
    answers = {}
    for spec in QUESTION_SPECS:
        for form in range(bundle['forms']):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            criteria = bundle['request']['questions'][name]['criteria']
            if spec['type'] == 'choice':
                tokens = [token for token, option in criteria['options'].items() if option == atomic[spec['id']]]
                if len(tokens) != 1:
                    raise FixtureProblem(f'{name}: the frozen answer {atomic[spec["id"]]!r} is not uniquely presented')
                answers[name] = {'choice': tokens[0], 'probabilities': {tokens[0]: probability}}
            else:
                value = probability if criteria['options']['yes'] == 'yes' else 1 - probability
                if atomic[spec['id']] != 'yes':
                    value = 1 - value
                answers[name] = {'noul': value}
    return answers


def compile_pair(document: dict) -> list:
    """Replay one pair file through the repository and render every declared compile.

    The declared `records`, `assumption_seed`, `snapshot`, `cutoffs` and per-compile
    cutoffs are inputs; the file's `expected_*` fields are assertions, and a mismatch
    raises instead of scoring a compile that is not the frozen one.
    """
    problems = []
    actor = ActorContext(document['actor_id'], document['tenant_id'], frozenset({document['case_id']}),
                         frozenset(document['access_policy_refs']), True)
    repo = InMemoryRepository()
    for record in document['records']:
        validate_record(record)
        if record['record_kind'] == 'Case':
            repo.register_case(actor, record)
        elif record['record_kind'] == 'SourceVersion':
            repo.register(actor, record, source_bytes=record['payload']['original_text'].encode('utf-8'))
        else:
            repo.register(actor, record)
    seed = document['assumption_seed']
    assumption = repo.seed_assumption(actor, seed['record_id'], seed['revision_id'], seed['recorded_at'],
                                      seed['payload'], seed['rationale'])
    if reference(assumption) != document['expected_assumption_ref']:
        problems.append('assumption ref differs from the frozen expectation')
    frozen_snapshot = document['snapshot']
    snapshot = repo.build_snapshot(actor, document['case_id'], frozen_snapshot['audit_cutoff'],
                                   frozen_snapshot['recorded_at'])
    if reference(snapshot) != frozen_snapshot['ref']:
        problems.append('pair snapshot differs from the frozen expectation')
    if any(item['expected_snapshot_ref'] != frozen_snapshot['ref'] for item in document['compiles']):
        problems.append("compiles of a pair must share the pair's snapshot")
    cases = []
    for item in document['compiles']:
        task = repo.compile_task(actor, document['case_id'], reference(snapshot), seed['record_id'],
                                 item['information_cutoff'], item['recorded_at'])
        if reference(task) != item['expected_task_ref'] or task['payload']['task_digest'] != item['expected_task_digest']:
            problems.append(f"{item['at']}: compiled task differs from the frozen expectation")
        if task['payload']['status'] != item['expected_status']:
            problems.append(f"{item['at']}: status differs")
        if [omission['code'] for omission in task['payload']['omissions']] != item['expected_omissions']:
            problems.append(f"{item['at']}: omissions differ")
        if [entry['passage_ref']['record_id'] for entry in task['payload']['context']] != item['expected_context_passages']:
            problems.append(f"{item['at']}: context differs")
        bundle = render_bundle(task, document['model_id'])
        if bundle.get('bundle_version') != item['expected_render']['bundle_version']:
            problems.append(f"{item['at']}: bundle version differs")
        if bundle['status'] != item['expected_render']['status']:
            problems.append(f"{item['at']}: render status differs")
        if bundle.get('request_digest') != item['expected_render']['request_digest']:
            problems.append(f"{item['at']}: request digest differs")
        if bundle['status'] != 'rendered':
            raise FixtureProblem(f"{document['pair_id']}/{item['at']}: the frozen set does not render")
        cases.append({
            'key': f"{document['pair_id']}/{item['at']}",
            'pair_id': document['pair_id'],
            'at': item['at'],
            'edge_class': document['edge_class'],
            'assumption_kind': document['assumption_kind'],
            'model_id': document['model_id'],
            'information_cutoff': item['information_cutoff'],
            'split': split_of(document['pair_id']),
            'prior_label': (document.get('lineage') or {}).get('prior_label'),
            'frozen_label': item['frozen_label'],
            'frozen_expectation': dict(item['expected_composition']),
            'bundle': bundle,
            'answers': scripted_answers(bundle, item['expected_atomic_answers']),
        })
    if problems:
        raise FixtureProblem(f"{document['pair_id']}: " + '; '.join(problems))
    return cases


def single_render_answer(bundle: dict, answers: dict) -> str:
    """The baseline's own answer: the canonical (``f0``) Q8 top, read alone.

    `compose` reads the modal top option across all four forms of every question. That is
    the composition's convention, but it is not one render: a backend that flips under
    option order, aliasing or yes/no polarity would turn the model's own single answer
    into a majority vote over four perturbed renders and understate what decomposition
    adds. The baseline therefore reads the canonical question `q8_direction_f0` directly
    and un-aliases its token through that form's criteria.
    """
    question = (bundle.get('request') or {}).get('questions', {}).get(CANONICAL_Q8)
    options = question.get('criteria', {}).get('options') if type(question) is dict else None
    answer = answers.get(CANONICAL_Q8) if type(answers) is dict else None
    if (type(options) is not dict or type(answer) is not dict
            or type(answer.get('choice')) is not str or answer['choice'] not in options):
        raise FixtureProblem(f'{CANONICAL_Q8}: the frozen set carries no readable canonical direction answer')
    return options[answer['choice']]


def condition_labels(bundle: dict, answers: dict, prior_label, thresholds: dict) -> dict:
    """Every condition's reading of one compile, plus the receipt readings.

    `single_render` reads the model's own canonical-form Q8 answer and applies no gate
    and no receipt; `bundle` calls the frozen `compose` with the chosen thresholds;
    `bundle_no_gate` and `bundle_no_receipt` call it with the chosen thresholds and one
    mechanism switched off. The atomic reading is a call with both mechanisms off, so it
    is threshold-independent.
    """
    atomic = compose(bundle, answers, dict(thresholds, **RECEIPT_OFF), prior_label=prior_label)['atomic']
    q8 = single_render_answer(bundle, answers)
    composed = {
        'bundle': compose(bundle, answers, thresholds, prior_label=prior_label),
        'bundle_no_gate': compose(bundle, answers, dict(thresholds, **GATE_OFF), prior_label=prior_label),
        'bundle_no_receipt': compose(bundle, answers, dict(thresholds, **RECEIPT_OFF), prior_label=prior_label),
    }
    reading = {'single_render': {'label': NEITHER_LABEL if q8 == 'neither' else q8,
                                 'fired_rule': 'single_render: Q8=' + q8, 'reason': None, 'escalation': 'none'}}
    reading.update({name: {'label': value['label'], 'fired_rule': value['fired_rule'], 'reason': value['reason'],
                           'escalation': value['escalation']} for name, value in composed.items()})
    alternative = NEITHER_ALTERNATIVE if q8 == 'neither' else q8
    reading['single_render_neither_as_abstention'] = {
        'label': alternative, 'fired_rule': 'sensitivity: Q8=' + q8, 'reason': None,
        'escalation': ESCALATION if alternative == 'insufficient' else 'none'}
    unstable = {
        'bundle': receipt(bundle, answers, thresholds)['unstable'],
        'bundle_no_gate': receipt(bundle, answers, dict(thresholds, **GATE_OFF))['unstable'],
        'bundle_no_receipt': receipt(bundle, answers, dict(thresholds, **RECEIPT_OFF))['unstable'],
    }
    questions = receipt(bundle, answers)['questions']
    flips = {spec['id']: questions[spec['id']]['flip_rate'] for spec in QUESTION_SPECS}
    return {'atomic': atomic, 'conditions': reading, 'unstable': unstable,
            'flip_rate': flips, 'flip_rate_max': max(flips.values())}


def predictions_of(cases: list, name: str) -> dict:
    return {case['key']: case['reading']['conditions'][name]['label'] for case in cases}


def measure(cases: list, predictions: dict) -> dict:
    """The metric block for one condition over one set of compiles.

    ``predictions`` maps a compile key to the condition's label; ``cases`` supply the
    frozen labels and the compile keys. Every list is sorted, so the block is stable.
    """
    keys = sorted(case['key'] for case in cases)
    frozen = {case['key']: case['frozen_label'] for case in cases}
    labels = {key: predictions[key] for key in keys}
    n = len(keys)
    correct = [key for key in keys if labels[key] == frozen[key]]
    abstained = [key for key in keys if labels[key] == 'insufficient']
    answered = [key for key in keys if labels[key] != 'insufficient']
    # Selective accuracy is over the answered compiles only: a correct abstention is
    # credited by `accuracy` (its label equals the frozen label) but is not an answered
    # case, so it must not enter this numerator while being excluded from the denominator.
    answered_correct = [key for key in answered if labels[key] == frozen[key]]
    return {
        'n': n,
        'accuracy': {'correct': len(correct), 'n': n, 'rate': _rate(len(correct), n)},
        'abstentions': {
            'count': len(abstained), 'rate': _rate(len(abstained), n), 'compiles': abstained,
            'correct_when_frozen_insufficient': [key for key in abstained if frozen[key] == 'insufficient'],
            'incorrect_when_frozen_definite': [key for key in abstained if frozen[key] != 'insufficient'],
        },
        'coverage': {'answered': len(answered), 'n': n, 'rate': _rate(len(answered), n)},
        'selective_accuracy': {'correct': len(answered_correct), 'answered': len(answered),
                               'rate': _rate(len(answered_correct), len(answered))},
        'missed_challenges': [key for key in keys
                              if frozen[key] == 'challenges' and labels[key] in ('supports', 'mixed', 'unrelated')],
        'challenge_abstentions': [key for key in keys
                                  if frozen[key] == 'challenges' and labels[key] == 'insufficient'],
        'unsupported_revisions': [key for key in keys if labels[key] in ('challenges', 'mixed')
                                  and frozen[key] in ('supports', 'unrelated', 'insufficient')],
        'wrong_definite': [key for key in keys if labels[key] != frozen[key] and labels[key] != 'insufficient'],
    }


def identity_mismatches(cases: list) -> list:
    """Compiles whose modal Q1 is not the assumption's mapped entity, `cannot_tell` included."""
    return sorted(case['key'] for case in cases
                  if case['reading']['atomic']['q1'] != case['bundle']['request']['state']
                  ['assumption_definition']['entity']['entity_id'])


def flip_rate_distribution(cases: list) -> dict:
    """The flip-rate distribution the receipt reports over the evaluated compiles.

    Keys are the presented flip rates as strings. On this scripted backend every form
    answers the same top option, so the distribution is a single zero bucket: the receipt
    has nothing to measure, which is why A3 is not identified here.
    """
    histogram = {}
    per_question = {spec['id']: {} for spec in QUESTION_SPECS}
    for case in cases:
        key = str(case['reading']['flip_rate_max'])
        histogram[key] = histogram.get(key, 0) + 1
        for qid, value in case['reading']['flip_rate'].items():
            per_question[qid][str(value)] = per_question[qid].get(str(value), 0) + 1
    return {'per_compile_max': dict(sorted(histogram.items())),
            'per_question': {qid: dict(sorted(counts.items())) for qid, counts in per_question.items()},
            'presented_decimals': 6}


def metrics_block(cases: list) -> dict:
    """Metrics for every condition, plus the matched-coverage comparison and the receipts."""
    answered = {name: {case['key'] for case in cases if case['reading']['conditions'][name]['label'] != 'insufficient'}
                for name in CONDITIONS}
    matched = sorted(set.intersection(*answered.values())) if cases else []
    frozen = {case['key']: case['frozen_label'] for case in cases}
    block = {'n': len(cases), 'conditions': {}, 'identity_mismatches': identity_mismatches(cases),
             'flip_rate_distribution': flip_rate_distribution(cases)}
    for name in CONDITIONS:
        predictions = predictions_of(cases, name)
        block['conditions'][name] = measure(cases, predictions)
        correct = sum(1 for key in matched if frozen[key] == predictions[key])
        block.setdefault('selective_accuracy_at_matched_coverage', {})[name] = {
            'correct': correct, 'n': len(matched), 'rate': _rate(correct, len(matched))}
    block['matched_coverage'] = {'compiles': matched, 'n': len(matched), 'n_total': len(cases),
                                 'rate': _rate(len(matched), len(cases))}
    return block


def candidate_thresholds(grid: dict = CALIBRATION_GRID) -> list:
    """Every candidate threshold tuple of the declared grid, in a fixed order."""
    candidates = []
    for tau_suff in grid['tau_suff']:
        for tau_cond in grid['tau_cond']:
            for tau_lineage in grid['tau_lineage']:
                for tau_flip in grid['tau_flip']:
                    for tau_pol in grid['tau_pol']:
                        candidates.append({'tau_suff': tau_suff, 'tau_cond': tau_cond, 'tau_lineage': tau_lineage,
                                           'tau_flip': tau_flip, 'tau_pol': tau_pol})
    return candidates


def candidate_scores(calibration: list, grid: dict = CALIBRATION_GRID) -> list:
    """Score every candidate threshold tuple on the calibration split only.

    The objective is the A1/A2 one: label accuracy of the full bundle condition on the
    calibration compiles, then the incorrect-abstention count, then the L1 distance from
    the intent's initial values. The test split is not read anywhere in this function.
    """
    scored = []
    for thresholds in candidate_thresholds(grid):
        predictions, incorrect = {}, 0
        for case in calibration:
            reading = condition_labels(case['bundle'], case['answers'], case['prior_label'], thresholds)['conditions']
            predictions[case['key']] = reading['bundle']['label']
            if reading['bundle']['label'] == 'insufficient' and case['frozen_label'] != 'insufficient':
                incorrect += 1
        scored.append({'thresholds': thresholds,
                       'calibration_accuracy': measure(calibration, predictions)['accuracy'],
                       'calibration_incorrect_abstentions': incorrect,
                       'distance_from_initial': round(sum(abs(thresholds[name] - DEFAULT_THRESHOLDS[name])
                                                          for name in thresholds), 6)})
    return scored


def choose_thresholds(candidates: list) -> dict:
    """Apply the declared tie-break to the calibration scores and return the winner."""
    return sorted(candidates, key=lambda entry: (
        -entry['calibration_accuracy']['correct'],
        entry['calibration_incorrect_abstentions'],
        entry['distance_from_initial'],
        tuple(sorted(entry['thresholds'].items())),
    ))[0]


def contestable_block(cases: list) -> dict:
    """The compiles whose atomic reading carries the contestable row's pattern.

    Working paper 5.2 marks `Q3 = before and Q6 = yes -> supports` deliberately
    contestable and requires A1 to test it with both assumption kinds; this block is that
    comparison, computed from the annotated atomic answers rather than from a list.
    """
    matched = sorted((case for case in cases
                      if case['reading']['atomic']['q3'] == 'before' and case['reading']['atomic']['q6'] == 'yes'),
                     key=lambda case: case['key'])
    detail = [{'key': case['key'], 'edge_class': case['edge_class'], 'assumption_kind': case['assumption_kind'],
               'frozen_label': case['frozen_label'],
               **{name: case['reading']['conditions'][name]['label'] for name in CONDITIONS}}
              for case in matched]
    by_kind = {}
    for entry in detail:
        by_kind.setdefault(entry['assumption_kind'], []).append(entry['key'])
    return {
        'pattern': 'Q3 = before and Q6 = yes',
        'compiles_by_assumption_kind': {kind: sorted(keys) for kind, keys in sorted(by_kind.items())},
        'agreement_with_frozen_label': {name: {'correct': sum(1 for entry in detail if entry[name] == entry['frozen_label']),
                                               'n': len(detail)} for name in CONDITIONS},
        'detail': detail,
    }


def compare(cases: list, left: str, right: str) -> dict:
    """The compiles where two conditions disagree, with both labels."""
    left_labels, right_labels = predictions_of(cases, left), predictions_of(cases, right)
    changed = sorted(key for key in left_labels if left_labels[key] != right_labels[key])
    return {'differing_compiles': changed,
            'labels': {key: {left: left_labels[key], right: right_labels[key]} for key in changed}}


def build_report(fixtures: Path) -> dict:
    """Load the frozen set, fix the thresholds on calibration, score every condition."""
    fixtures = fixtures.resolve()
    integrity = verify_fixture_digests(fixtures)
    documents = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(fixtures.glob('pb-*.json'))]
    if len(documents) != integrity['pairs']:
        raise FixtureProblem(f'{len(documents)} pair files on disk, {integrity["pairs"]} in the manifest')
    if any(document.get('schema') != FIXTURE_SCHEMA for document in documents):
        raise FixtureProblem('a pair file does not carry the frozen fixture schema')
    cases = [case for document in documents for case in compile_pair(document)]
    if len(cases) != integrity['compiles']:
        raise FixtureProblem(f'{len(cases)} compiles replayed, {integrity["compiles"]} in the manifest')
    calibration = [case for case in cases if case['split'] == 'calibration']
    test = [case for case in cases if case['split'] == 'test']
    if not calibration or not test:
        raise FixtureProblem('both splits must hold compiles')

    # Thresholds first: the candidate grid is scored on the calibration compiles only, and
    # one candidate is fixed before the test compiles are read or scored.
    candidates = candidate_scores(calibration)
    chosen = choose_thresholds(candidates)
    thresholds = chosen['thresholds']
    for case in cases:
        case['reading'] = condition_labels(case['bundle'], case['answers'], case['prior_label'], thresholds)
        case['reading']['matches_frozen_expectation'] = (
            case['reading']['conditions']['bundle']['label'] == case['frozen_expectation']['label']
            and case['reading']['conditions']['bundle']['fired_rule'] == case['frozen_expectation']['fired_rule'])
    mismatches = sorted(case['key'] for case in cases if not case['reading']['matches_frozen_expectation'])
    model_ids = sorted({case['model_id'] for case in cases})

    return {
        'schema': REPORT_SCHEMA,
        'report_label': REPORT_LABEL,
        'task': 'EVAL-2',
        'script': 'scripts/eval/probe_bundle.py',
        'backend': {
            'name': model_ids[0],
            'model': model_ids[0],
            'model_ids': model_ids,
            'kind': 'fixture',
            'execution_mode': 'synthetic_fixture',
            'model_version': None,
            'answers': "the pair file's frozen annotated atomic answers, one scripted answer per question form",
            'probability': SCRIPTED_PROBABILITY,
            'live_calls': 0,
            'note': 'The fixture backend is a deterministic script; intent slice S2 (the System One port) is not '
                    'built and no model, transport, credential or network call is reachable from this script.',
        },
        'fixtures': integrity,
        'conditions': {'order': list(CONDITIONS), 'definitions': CONDITION_DEFINITIONS},
        'metric_definitions': METRIC_DEFINITIONS,
        'bundle_version': BUNDLE_VERSION,
        'splits': {
            'rule': SPLIT_RULE,
            'calibration': {'pairs': sorted({case['pair_id'] for case in calibration}),
                            'compiles': sorted(case['key'] for case in calibration)},
            'test': {'pairs': sorted({case['pair_id'] for case in test}),
                     'compiles': sorted(case['key'] for case in test)},
        },
        'thresholds': {
            'fixed_on': 'calibration',
            'initial': dict(DEFAULT_THRESHOLDS),
            'grid': {name: list(values) for name, values in CALIBRATION_GRID.items()},
            'candidates': sorted(candidates, key=lambda entry: tuple(sorted(entry['thresholds'].items()))),
            'chosen': dict(thresholds),
            'chosen_by': {'calibration_accuracy': chosen['calibration_accuracy'],
                          'calibration_incorrect_abstentions': chosen['calibration_incorrect_abstentions'],
                          'distance_from_initial': chosen['distance_from_initial']},
            'tie_break': list(TIE_BREAK),
            'tuned': any(thresholds[name] != DEFAULT_THRESHOLDS[name] for name in thresholds),
            'note': 'The candidate grid is scored on the calibration compiles only; the test split is not read '
                    'before a candidate is fixed, and ties are resolved by the declared tie-break.',
        },
        'metrics': {
            'all': metrics_block(cases),
            'calibration': metrics_block(calibration),
            'test': metrics_block(test),
        },
        'sensitivity': {
            'question': 'what the single_render reading of `neither` costs',
            'scored_as': NEITHER_LABEL,
            'alternative': NEITHER_ALTERNATIVE,
            'rule': '`neither` is not one of the five frozen labels and the baseline is not given an abstain '
                    'primitive, so it scores as `unrelated`; the alternative scores it as an abstention.',
            'metrics_all': measure(cases, {case['key']: case['reading']['conditions']
                                           ['single_render_neither_as_abstention']['label'] for case in cases}),
        },
        'comparisons': {
            'A1': {
                'compared': ['single_render', 'bundle'],
                'primary_question': 'does decomposition plus composition improve label accuracy and abstention '
                                    'quality?',
                'all': compare(cases, 'single_render', 'bundle'),
                'test': compare(test, 'single_render', 'bundle'),
                'contestable_rule': contestable_block(cases),
            },
            'A2': {
                'compared': ['bundle', 'bundle_no_gate'],
                'primary_question': 'does the sufficiency gate reduce unsupported revisions and missed challenges?',
                'all': compare(cases, 'bundle', 'bundle_no_gate'),
                'test': compare(test, 'bundle', 'bundle_no_gate'),
            },
            'A3': {
                'compared': ['bundle', 'bundle_no_receipt'],
                'primary_question': 'does measured instability predict errors?',
                'all': compare(cases, 'bundle', 'bundle_no_receipt'),
                'test': compare(test, 'bundle', 'bundle_no_receipt'),
                'stable_compiles': sorted(case['key'] for case in cases if not case['reading']['unstable']['bundle']),
                'identifiable': any(case['reading']['unstable']['bundle'] for case in cases),
                'note': 'A stable scripted backend reports flip rate 0 on every compile, so the downgrade never '
                        'fires, `bundle_no_receipt` equals `bundle`, and A3 is not identified on this set: measured '
                        'instability cannot predict errors when no instability is measured. The frozen label '
                        'disagreements are stable-and-wrong rows of the composition table, not receipt cases.',
            },
        },
        'compiles': [{
            'key': case['key'], 'pair_id': case['pair_id'], 'at': case['at'], 'edge_class': case['edge_class'],
            'assumption_kind': case['assumption_kind'], 'split': case['split'],
            'information_cutoff': case['information_cutoff'], 'frozen_label': case['frozen_label'],
            'frozen_expectation': {'label': case['frozen_expectation']['label'],
                                   'fired_rule': case['frozen_expectation']['fired_rule'],
                                   'agrees_with_frozen_label': case['frozen_expectation']['agrees_with_frozen_label']},
            'matches_frozen_expectation': case['reading']['matches_frozen_expectation'],
            'atomic': case['reading']['atomic'],
            'flip_rate': case['reading']['flip_rate'],
            'unstable': case['reading']['unstable'],
            'conditions': {name: case['reading']['conditions'][name] for name in CONDITIONS},
        } for case in sorted(cases, key=lambda case: case['key'])],
        'composition_matches_frozen_expectation': {'matched': len(cases) - len(mismatches), 'n': len(cases),
                                                   'mismatches': mismatches},
        'notes': [
            'Synthetic fixture result only: the answers are the frozen annotations of fictional pairs, and fixture '
            'results stay separate from any real-case result.',
            'The fixture backend is a deterministic script, not a model; this report is not analyst validation and '
            'not measured model accuracy.',
            'Every compile replayed from its declared records matched the frozen task ref, digest, cutoffs, context '
            'and request digest before it was scored; a mismatch stops the run.',
            'No clock, interpreter version or environment value is recorded, so the same fixtures and code give the '
            'same report bytes.',
        ],
    }


def summarise(report: dict) -> str:
    """One deterministic line for the terminal: the label, the set and the headline numbers."""
    bundle = report['metrics']['all']['conditions']['bundle']
    single = report['metrics']['all']['conditions']['single_render']
    return (f"{report['report_label']}: {len(report['splits']['calibration']['pairs'])} calibration pairs, "
            f"{len(report['splits']['test']['pairs'])} test pairs, {report['metrics']['all']['n']} compiles; "
            f"bundle {bundle['accuracy']['correct']}/{bundle['accuracy']['n']} correct "
            f"({bundle['abstentions']['count']} abstentions), single_render "
            f"{single['accuracy']['correct']}/{single['accuracy']['n']} correct "
            f"({single['abstentions']['count']} abstentions)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--fixtures', default='tests/fixtures/probe-bundle',
                        help='directory holding the frozen probe-bundle fixture set')
    parser.add_argument('--out', default=None,
                        help='write the JSON report here (.local/eval/report.json by convention, an ignored path); '
                             'without it the report is printed')
    args = parser.parse_args(argv)
    try:
        report = build_report(Path(args.fixtures))
    except FixtureProblem as problem:
        print(f'fixture problem: {problem}', file=sys.stderr)
        return 1
    text = canonical_dumps(report) + '\n'
    if args.out is None:
        print(text, end='')
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='utf-8')
    print(f'{summarise(report)} -> {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
