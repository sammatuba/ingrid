"""Probe bundle S1: deterministic render, composition and stability receipt.

Pure stdlib functions over a compiled-task dict and a System One answers dict: no
backend, transport, clock, storage or network is reached from here. The port, the
additive record kind, the repository methods, the API routes, the workspace and the
offline evaluation are slices S2 to S5 of `docs/work/probe-bundle/intent.md`; this
module implements S1 only.

Question wording, option sets and criteria are versioned by `BUNDLE_VERSION`; changing
any of them changes the version, because the rendered request is digested and stored.
`probe-bundle.v2` carries the presented option and passage sequence explicitly inside
each question's `criteria`, so canonical serialization and the request digest
distinguish forms that differ only in the order they present. `probe-bundle.v3` marked
the modal-top composition; `probe-bundle.v4` marks the rounding boundary, so no stored
artifact can carry a label or digest computed under an earlier reading. `probe-bundle.v5`
re-derives the Q2 event vocabulary from the operator-advisory corpus (planned outage,
forced outage, return to service, derating, grid alert, testing, commercial operation,
other), reads availability kind from the state's model representation rather than from a
field-name prefix, and gates the earlier-observation row on direction through the
`direction_conflict` row; see `docs/work/bundle-v5/intent.md`. Thresholds carry the
intent's initial values, not tuned values.

Composition takes the *modal top option* of every question across its forms, as the
working paper section 5.2 and the frozen intent state: for a noul that is the majority
of its per-form ``yes``/``no`` tops, never a mean probability, and the table's numeric
thresholds read it as a hard yes (1.0) or no (0.0). A noul whose tops split evenly has
no modal top; see ``NOUL_TIE``.

Rounding is presentation only. Top selection, `flip_rate`, `polarity_gap`, `max_gap` and
every threshold comparison read the raw values the answers carry; a computed number is
rounded to ``PRESENTED_DECIMALS`` only where it is written into the receipt. Rounding
first would move values onto boundaries: p = 0.4999996 rounds to 0.5 and would take a
`yes` top, and a gap of 0.3000004 rounds to 0.3 and would look stable against `tau_pol`
0.3. A presented 0.3 can therefore accompany an unstable bundle, and the receipt shows
the decision's inputs to the last displayed digit and no further.

Failure surface:

* ``ValueError`` for caller arguments: forms, thresholds, model, non-task input.
* ``JudgmentUnavailable('MODEL_INPUT_LIMIT')`` when the rendered state exceeds 128 KiB.
* ``JudgmentUnavailable('MODEL_INVALID_RESPONSE')`` for a malformed answers mapping.
* a render result with ``status == 'insufficient'`` and a reason when the task cannot
  produce a bundle: ``TOO_MANY_CANDIDATES`` above eight reviewed candidates, or
  ``UNRESOLVED_MAPPING`` when the reviewed mapping has no usable candidates.
"""
from __future__ import annotations

import hashlib
import math

from src.contracts.jsonutil import canonical_dumps, compute_content_digest
from src.judgment import JudgmentUnavailable, LABELS
from src.review.records import json_copy

BUNDLE_VERSION = 'probe-bundle.v5'
MODEL_INPUT_LIMIT = 128 * 1024
MAX_FORMS = 4
MAX_CANDIDATES = 8
ESCALATION = 'gemini_interpretation_and_manual_review'

#: Initial composition thresholds, untuned; the ablation fixes them on a calibration
#: split. They are recorded in every composed result and receipt.
DEFAULT_THRESHOLDS = {'tau_suff': 0.6, 'tau_cond': 0.5, 'tau_lineage': 0.5, 'tau_flip': 0.25, 'tau_pol': 0.3}

#: Decimals for a computed number on its way into the receipt. Comparisons read the
#: unrounded value; only presented numbers are rounded, so `round(x, 6) > tau` is never
#: the test — `x > tau` is.
PRESENTED_DECIMALS = 6

#: The rendered state is the same task-payload subset ``render_task`` uses today.
STATE_KEYS = ('policy', 'original_definitions', 'task_digest', 'assumption_definition', 'mapping_definition',
              'model_representation', 'information_cutoff', 'audit_cutoff', 'context', 'lineage_groups')

#: The Q2 event vocabulary, re-derived from the operator-advisory corpus
#: (`docs/work/bundle-v5/intent.md`): the feed's own verbs are a planned outage, a forced
#: or unplanned outage, a return or restore, a derating, a grid alert, testing and, rarely,
#: an explicit commercial-operation declaration. ``synchronisation`` is not a token: in the
#: corpus it names a failed return (a forced outage) or a completed one (return to
#: service), never a milestone of its own. ``commercial_operation`` absorbs the old
#: ``commercial_availability`` token.
EVENTS = ('planned_outage', 'forced_outage', 'return_to_service', 'derating', 'grid_alert',
          'testing', 'commercial_operation', 'other')
TIMES = ('before', 'same', 'after', 'not_stated')
DIRECTIONS = ('supports', 'challenges', 'neither')

_ALIAS_NOTE = ' Answer with one bracketed option identifier.'

#: The eight atomic questions of working paper section 5.2, in order. ``tie`` is the
#: option a form vote tie resolves to; the question names are ``<id>_<slug>_f<form>``.
QUESTION_SPECS = (
    {'id': 'q1', 'slug': 'identity', 'type': 'choice', 'tie': 'cannot_tell', 'options': None,
     'text': 'Which reviewed candidate entity do the supplied passages refer to?', 'text_negated': None},
    {'id': 'q2', 'slug': 'event', 'type': 'choice', 'tie': 'other', 'options': EVENTS,
     'text': 'Which event do the supplied passages describe for that entity?', 'text_negated': None},
    {'id': 'q3', 'slug': 'time', 'type': 'choice', 'tie': 'not_stated', 'options': TIMES,
     'text': 'How does the time stated in the supplied passages relate to the assumed time?', 'text_negated': None},
    {'id': 'q4', 'slug': 'conditional', 'type': 'noul', 'tie': None, 'options': None,
     'text': 'Are the supplied statements conditional, planned or subject to clearance rather than confirmed?',
     'text_negated': 'Are the supplied statements unconditional and confirmed?'},
    {'id': 'q5', 'slug': 'lineage', 'type': 'noul', 'tie': None, 'options': None,
     'text': 'Do the supplied passages repeat an earlier source already present in the context rather than add '
             'new information?',
     'text_negated': 'Do the supplied passages add new information rather than repeat an earlier source already '
                     'present in the context?'},
    {'id': 'q6', 'slug': 'observation', 'type': 'noul', 'tie': None, 'options': None,
     'text': 'Do the supplied passages report an observation (something that happened) rather than a target or plan?',
     'text_negated': 'Do the supplied passages report a target or plan rather than an observation?'},
    {'id': 'q7', 'slug': 'sufficiency', 'type': 'noul', 'tie': None, 'options': None,
     'text': 'Do the supplied passages suffice to decide whether the assumption is supported or challenged?',
     'text_negated': 'Are the supplied passages insufficient to decide whether the assumption is supported or '
                     'challenged?'},
    {'id': 'q8', 'slug': 'direction', 'type': 'choice', 'tie': 'neither', 'options': DIRECTIONS,
     'text': 'Taken alone, do the supplied passages support, challenge or leave unchanged the assumed value?',
     'text_negated': None},
)

#: The composition table of working paper section 5.2, in evaluation order. The first
#: matching rule fires; ``fall_through`` is the total fallback and yields ``insufficient``.
#: Row 10 ``earlier_observation`` is gated on direction (owner decision, 2026-10-13): when
#: Q3 is ``before`` and Q6 ``yes`` but Q8 is ``challenges``, ``direction_conflict`` fires
#: instead and yields ``mixed``.
RULES = ('unstable', 'sufficiency_gate', 'identity_unknown', 'unrelated_entity', 'event_other', 'lineage_reuse',
         'availability_confirmed', 'milestone_mismatch', 'outage_or_later', 'earlier_observation',
         'direction_conflict', 'conditional_support', 'time_not_stated', 'fall_through')

#: Quantity kinds in the state's model representation that mark an input field as an
#: availability fact. ``available_capacity`` and ``commercial_operation_date`` are the
#: intent's kinds for a real representation; ``assumed_available_capacity`` is the kind
#: the synthetic representations (the demo seed and the EVAL-1 fixtures) give the
#: supply-outlook field, and the intent requires that field to compose through
#: ``milestone_mismatch``.
AVAILABILITY_QUANTITY_KINDS = ('available_capacity', 'commercial_operation_date', 'assumed_available_capacity')

#: Field-name prefixes that mark an input field as an availability fact, for
#: representations whose quantity kind is named differently.
AVAILABILITY_FIELD_PREFIXES = ('commercial_availability', 'available_capacity', 'availability_from')


def _invalid():
    raise JudgmentUnavailable('MODEL_INVALID_RESPONSE')


def _check(condition):
    if not condition:
        _invalid()


def _probability(value):
    _check((type(value) is int or type(value) is float) and math.isfinite(value) and 0 <= value <= 1)


def _refuse(reason):
    return {'status': 'insufficient', 'reason': reason, 'bundle_version': BUNDLE_VERSION}


def _thresholds(thresholds):
    if thresholds is None:
        return dict(DEFAULT_THRESHOLDS)
    if type(thresholds) is not dict or not set(thresholds) <= set(DEFAULT_THRESHOLDS):
        raise ValueError('thresholds must be a subset of the documented names')
    limits = dict(DEFAULT_THRESHOLDS)
    for name, value in thresholds.items():
        if type(value) not in (int, float) or type(value) is bool or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('thresholds must be finite numbers in [0, 1]')
        limits[name] = float(value)
    return limits


def _permutation(seed, count):
    """Deterministic, interpreter-independent option order for one question seed.

    Sorting by digest keeps the perturbation reproducible from the task digest alone,
    and a rotation avoids the identity order so the form always perturbs something.
    """
    order = sorted(range(count), key=lambda index: hashlib.sha256(f'{seed}:{index}'.encode('utf-8')).hexdigest())
    if count > 1 and order == list(range(count)):
        order = order[1:] + order[:1]
    return order


def _options(spec, candidates):
    return list(candidates) + [spec['tie']] if spec['id'] == 'q1' else list(spec['options'])


def _question(spec, form, options, seed, passages):
    """One question in one form.

    ``criteria`` carries the presentation explicitly, because canonical JSON sorts
    object keys and would otherwise erase it:

    * ``options`` maps every presented token to its canonical option, so un-aliasing
      and un-negating are one lookup;
    * ``presentation`` (choice questions) lists those tokens in the order the form
      presents them: ``f0`` canonical, ``f1`` permuted, ``f2`` aliased;
    * ``passages`` lists the context passages in the order this form presents them,
      as indices into ``state['context']``: canonical except for the ``f3`` form,
      whose sequence is reversed.
    """
    if spec['type'] == 'noul':
        # The negated wording is un-negated through the criteria map and the answer
        # probability; nothing downstream needs to know which form was negated.
        negation = {'yes': 'no', 'no': 'yes'} if form == 1 else {'yes': 'yes', 'no': 'no'}
        instructions = spec['text_negated'] if form == 1 else spec['text']
        return {'type': 'noul', 'instructions': instructions,
                'criteria': {'options': negation, 'passages': list(passages)}}
    if form == 1:
        presentation = [options[index] for index in _permutation(seed, len(options))]
        mapping = {token: token for token in presentation}
        instructions = spec['text']
    elif form == 2:
        presentation = [f'[{index + 1}]' for index in range(len(options))]
        mapping = dict(zip(presentation, options))
        instructions = spec['text'] + _ALIAS_NOTE
    else:
        presentation = list(options)
        mapping = {token: token for token in presentation}
        instructions = spec['text']
    return {'type': 'choice', 'instructions': instructions,
            'criteria': {'options': mapping, 'presentation': presentation, 'passages': list(passages)}}


def request_digest(request):
    """The stored request digest: ``digest({'bundle_version', 'input': request})``."""
    return compute_content_digest({'bundle_version': BUNDLE_VERSION, 'input': request})


def render_bundle(task, model, forms=4):
    """Render the S1 bundle for a compiled task, or a refusal result.

    Returns ``{'status': 'rendered', 'bundle_version', 'forms', 'task_digest',
    'request', 'request_digest'}`` where ``request`` is the frozen System One request
    ``{'model', 'state', 'questions'}``, or ``{'status': 'insufficient', 'reason', ...}``
    when the task cannot produce a bundle. The task dict is never mutated.
    """
    if type(forms) is not int or not 1 <= forms <= MAX_FORMS:
        raise ValueError('forms must be an integer between 1 and 4')
    if type(model) is not str or not model.strip() or len(model) > 200:
        raise ValueError('model must be a nonblank string of at most 200 characters')
    payload = task.get('payload') if type(task) is dict else None
    if type(payload) is not dict or any(key not in payload for key in STATE_KEYS):
        raise ValueError('a compiled task payload is required')
    if task.get('record_kind') not in (None, 'CompiledTask'):
        raise ValueError('a compiled task record is required')
    state = json_copy({key: payload[key] for key in STATE_KEYS})
    if type(state['context']) is not list:
        raise ValueError('a compiled task payload is required')
    if len(canonical_dumps(state).encode('utf-8')) > MODEL_INPUT_LIMIT:
        raise JudgmentUnavailable('MODEL_INPUT_LIMIT')
    mapping = state['mapping_definition']
    entities = mapping.get('entities') if type(mapping) is dict else None
    if type(entities) is not list or not entities or not all(type(entity) is dict for entity in entities):
        return _refuse('UNRESOLVED_MAPPING')
    candidates = [entity.get('entity_id') for entity in entities]
    if (any(type(candidate) is not str or not candidate.strip() for candidate in candidates)
            or len(set(candidates)) != len(candidates)):
        return _refuse('UNRESOLVED_MAPPING')
    if state['assumption_definition']['entity']['entity_id'] not in candidates:
        return _refuse('UNRESOLVED_MAPPING')
    if len(candidates) > MAX_CANDIDATES:
        return _refuse('TOO_MANY_CANDIDATES')
    seed = state['task_digest']
    # One state is shared by every question in the request, so the f3 passage-order
    # perturbation is carried per question in ``criteria`` rather than by reordering
    # the shared state, which would perturb every form including f0.
    order = list(range(len(state['context'])))
    questions = {}
    for spec in QUESTION_SPECS:
        options = _options(spec, candidates) if spec['type'] == 'choice' else None
        for form in range(forms):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            questions[name] = _question(spec, form, options, f"{seed}:{spec['id']}",
                                        order[::-1] if form == 3 else order)
    request = {'model': model, 'state': state, 'questions': questions}
    return {'status': 'rendered', 'bundle_version': BUNDLE_VERSION, 'forms': forms, 'task_digest': seed,
            'request': request, 'request_digest': request_digest(request)}


#: An exact split of a question's form votes has no modal top. A choice question
#: resolves to its ``tie`` option; the intent names tie options only for choices
#: ("``cannot_tell``, ``not_stated``, ``other`` or ``neither`` as applicable") and none
#: of them is a yes/no option, so a split noul resolves to ``no``: an even split is not
#: a majority for yes. The receipt cannot observe that reading (either way a split puts
#: ``min(yes, no)`` forms outside the top, so ``flip_rate`` is 0.5), and the recorded
#: default ``tau_flip`` of 0.25 makes any split unstable before a composition row reads
#: it; only a caller raising ``tau_flip`` to 0.5 or more reaches the resolution.
NOUL_TIE = 'no'


def _modal(tops, tie):
    counts = {}
    for option in tops.values():
        counts[option] = counts.get(option, 0) + 1
    leaders = [option for option, count in counts.items() if count == max(counts.values())]
    return leaders[0] if len(leaders) == 1 else tie


def _yes(value):
    """A noul's modal top option read against the table's numeric thresholds.

    The frozen composition takes the modal top option of each question, so a noul
    contributes ``yes`` or ``no``, not a probability: ``yes`` is a hard 1.0 and ``no``
    a hard 0.0, which keeps the named thresholds in the comparison with their ordering
    intact for every value in [0, 1]. A graded aggregate would be a different reading
    of the same frozen text and returns to intent rather than being settled here.
    """
    return 1.0 if value == 'yes' else 0.0


def _values(bundle, answers):
    """The one validated answers pass: canonical per-question values across forms.

    Choice questions contribute the modal option after un-aliasing; noul questions
    contribute the modal top option of their per-form tops (``yes``/``no``, or
    ``NOUL_TIE`` on an exact split), because the frozen composition takes the modal top
    option of every question and never a mean probability. A tied *choice* vote — which
    no form named — resolves to the question's tie option and reports a flip rate of
    1.0, so it is unstable. Every top is chosen from the raw value the answer carries,
    and every aggregate (``flip_rate``, ``polarity_gap``, ``max_gap``) is returned raw:
    the un-negated yes probabilities are kept only for the receipt and the stability
    comparison, and rounding happens where the receipt writes a number out.
    """
    if type(bundle) is not dict or bundle.get('status') != 'rendered':
        raise ValueError('a rendered bundle is required')
    questions = bundle['request']['questions']
    if type(answers) is not dict:
        _invalid()
    values = {}
    for spec in QUESTION_SPECS:
        tops, probabilities = {}, {}
        for form in range(bundle['forms']):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            question = questions.get(name)
            _check(type(question) is dict and question.get('type') == spec['type'])
            criteria = question.get('criteria')
            _check(type(criteria) is dict and type(criteria.get('options')) is dict)
            options, answer, key = criteria['options'], answers.get(name), f'f{form}'
            _check(type(answer) is dict)
            if spec['type'] == 'choice':
                presentation = criteria.get('presentation')
                _check(type(presentation) is list and len(presentation) == len(options)
                       and all(type(token) is str for token in presentation))
                _check(set(answer) == {'choice', 'probabilities'} and type(answer['choice']) is str)
                _check(answer['choice'] in presentation and answer['choice'] in options)
                _check(type(answer['probabilities']) is dict and set(answer['probabilities']) <= set(options))
                for value in answer['probabilities'].values():
                    _probability(value)
                tops[key] = options[answer['choice']]
            else:
                _check(set(answer) == {'noul'})
                _check(set(options) == {'yes', 'no'} and options['yes'] != options['no'])
                _probability(answer['noul'])
                canonical = answer['noul'] if options['yes'] == 'yes' else 1 - answer['noul']
                probabilities[key] = canonical
                # The top is chosen from the unrounded value: rounding first would move
                # 0.4999996 onto the 0.5 boundary and report a `yes` top the answer does
                # not carry.
                tops[key] = 'yes' if canonical >= 0.5 else 'no'
        if spec['type'] == 'choice':
            value = _modal(tops, spec['tie'])
            differences, polarity_gap, max_gap = sum(1 for top in tops.values() if top != value), None, None
        else:
            value = _modal(tops, NOUL_TIE)
            yes = sum(1 for top in tops.values() if top == 'yes')
            # Forms outside the strict majority = forms differing from the modal top,
            # whether or not a unique top exists (either way a split leaves min(yes, no)).
            # The gaps stay raw here: the strict `> tau_flip` / `> tau_pol` comparisons in
            # ``_unstable`` read these values, and the receipt rounds them on presentation.
            differences = min(yes, len(tops) - yes)
            polarity_gap = abs(probabilities['f0'] - probabilities['f1']) if 'f1' in probabilities else None
            max_gap = max(probabilities.values()) - min(probabilities.values()) if len(probabilities) > 1 else None
        values[spec['id']] = {'slug': spec['slug'], 'type': spec['type'], 'value': value, 'tops': tops,
                              'probabilities': probabilities or None,
                              'flip_rate': differences / len(tops),
                              'polarity_gap': polarity_gap, 'max_gap': max_gap}
    return values


def _unstable(values, limits):
    return [qid for qid, item in values.items()
            if item['flip_rate'] > limits['tau_flip']
            or (item['polarity_gap'] is not None and item['polarity_gap'] > limits['tau_pol'])]


def _presented(value):
    """A computed number as the receipt shows it: rounded only on the way out."""
    return None if value is None else round(value, PRESENTED_DECIMALS)


def receipt(bundle, answers, thresholds=None):
    """The perturbation-stability receipt: per-question tops, flip rate, polarity gap."""
    limits = _thresholds(thresholds)
    values = _values(bundle, answers)
    unstable = _unstable(values, limits)
    questions = {qid: {'slug': item['slug'], 'type': item['type'], 'tops': item['tops'],
                       'flip_rate': _presented(item['flip_rate']),
                       'polarity_gap': _presented(item['polarity_gap']),
                       'max_gap': _presented(item['max_gap'])}
                 for qid, item in values.items()}
    return {'forms': bundle['forms'], 'questions': questions, 'unstable': bool(unstable),
            'unstable_questions': unstable, 'thresholds': limits}


def _result(label, fired_rule, reason, thresholds, atomic):
    return {'label': label, 'fired_rule': fired_rule, 'reason': reason, 'atomic': atomic,
            'escalation': ESCALATION if label == 'insufficient' else 'none', 'thresholds': thresholds}


def _availability_kind(field, model_representation):
    """Whether the assumption's input field is an availability fact, from the representation.

    A pure function of ``(input_field, model_representation)``: the field's
    ``quantity_kind`` in the representation is one of :data:`AVAILABILITY_QUANTITY_KINDS`,
    or the field name starts with one of :data:`AVAILABILITY_FIELD_PREFIXES`. A field the
    representation does not define has no quantity kind to read and is not availability
    kind, so a name that merely sounds like one cannot widen the table's reach.
    """
    fields = model_representation.get('input_fields') if type(model_representation) is dict else None
    definition = fields.get(field) if type(fields) is dict and type(field) is str else None
    if type(definition) is not dict:
        return False
    if definition.get('quantity_kind') in AVAILABILITY_QUANTITY_KINDS:
        return True
    return field.startswith(AVAILABILITY_FIELD_PREFIXES)


def compose(bundle, answers, thresholds=None, prior_label=None):
    """Compose the relation label from the rendered bundle and its answers.

    The intent writes the composition as ``compose(answers, thresholds)``; un-aliasing,
    the mapped-entity and availability-kind rows and the lineage row need the
    rendered bundle's criteria and state facts, so the bundle is the first argument.
    ``prior_label`` is the saved bundle label for a repeated earlier source on a task
    for the same assumption (row ``lineage_reuse``); without it that row abstains.

    Every predicate reads the modal top option across the question's forms, as the
    frozen table specifies: ``atomic`` carries an option token for choices and
    ``yes``/``no`` for nouls, and the numeric thresholds are compared through ``_yes``.
    """
    limits = _thresholds(thresholds)
    if prior_label is not None and prior_label not in LABELS:
        raise ValueError('prior_label is not a relation label')
    if type(bundle) is dict and bundle.get('status') == 'insufficient':
        return _result('insufficient', 'render_refused: ' + str(bundle.get('reason')), bundle.get('reason'), limits, None)
    values = _values(bundle, answers)
    atomic = {qid: item['value'] for qid, item in values.items()}
    unstable = _unstable(values, limits)
    if unstable:
        return _result('insufficient', 'unstable: ' + ','.join(unstable) + ' above tau_flip or tau_pol',
                       'UNSTABLE', limits, atomic)
    if _yes(atomic['q7']) < limits['tau_suff']:
        return _result('insufficient', 'sufficiency_gate: Q7=' + atomic['q7'] + ' below tau_suff',
                       'LOW_SUFFICIENCY', limits, atomic)
    if atomic['q1'] == 'cannot_tell':
        return _result('insufficient', 'identity_unknown: Q1=cannot_tell', 'IDENTITY_UNKNOWN', limits, atomic)
    assumption = bundle['request']['state']['assumption_definition']
    if atomic['q1'] != assumption['entity']['entity_id']:
        return _result('unrelated', 'unrelated_entity: Q1=' + atomic['q1'] + ' is not the mapped entity',
                       None, limits, atomic)
    if atomic['q2'] in ('other', 'grid_alert'):
        # A grid alert names no unit assumption, so it composes as unrelated until a
        # row for it exists; the deferral is recorded in the intent.
        return _result('unrelated', 'event_other: Q2=' + atomic['q2'], None, limits, atomic)
    if _yes(atomic['q5']) >= limits['tau_lineage']:
        if prior_label is None:
            return _result('insufficient', 'lineage_reuse: Q5 above tau_lineage and no earlier bundle label',
                           'LINEAGE_NO_PRIOR', limits, atomic)
        return _result(prior_label, 'lineage_reuse: Q5 above tau_lineage; earlier source label reused',
                       None, limits, atomic)
    availability = _availability_kind(assumption['input_field'],
                                      bundle['request']['state']['model_representation'])
    if (availability and atomic['q2'] in ('commercial_operation', 'return_to_service')
            and atomic['q3'] == 'same' and _yes(atomic['q4']) < limits['tau_cond']):
        return _result('supports', 'availability_confirmed: Q2=' + atomic['q2'] + ', Q3=same, Q4 below tau_cond',
                       None, limits, atomic)
    if availability and atomic['q2'] == 'testing':
        return _result('challenges', 'milestone_mismatch: Q2=testing while the input field is availability kind',
                       None, limits, atomic)
    if availability and (atomic['q2'] in ('planned_outage', 'forced_outage', 'derating') or atomic['q3'] == 'after'):
        return _result('challenges', 'outage_or_later: Q2=' + atomic['q2'] + ', Q3=' + atomic['q3']
                                     + ' on an availability kind', None, limits, atomic)
    if atomic['q3'] == 'before' and atomic['q6'] == 'yes':
        if atomic['q8'] != 'challenges':
            return _result('supports', 'earlier_observation: Q3=before and Q6=yes', None, limits, atomic)
        return _result('mixed', 'direction_conflict: Q3=before and Q6=yes but Q8=challenges', None, limits, atomic)
    if _yes(atomic['q4']) >= limits['tau_cond'] and atomic['q3'] in ('same', 'before'):
        return _result('mixed', 'conditional_support: Q4 above tau_cond and Q3 in (same, before)',
                       None, limits, atomic)
    if atomic['q3'] == 'not_stated':
        if atomic['q8'] != 'neither':
            return _result('mixed', 'time_not_stated: Q3=not_stated and Q8=' + atomic['q8'], None, limits, atomic)
        return _result('insufficient', 'time_not_stated: Q3=not_stated and Q8=neither', 'NOT_STATED_NEITHER',
                       limits, atomic)
    return _result('insufficient', 'fall_through: no row matched', 'FALL_THROUGH', limits, atomic)
