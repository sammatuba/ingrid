"""Probe-bundle counterexamples: S1 render, composition and receipt; S2 port, record,
repository and service.

Offline, synthetic and stdlib-only; nothing here contacts a backend. The H0 task is
compiled through the real repository from the fictional seed in `src/demo`. Rows that
need a mapping or an assumption the seed does not carry derive a synthetic payload from
that compiled task: `bundle.py` is a pure function over a task dict, and the S2 rows
that need a repository shape the seed cannot produce (a refused render) use the local
stub declared below. Backends are the labelled fixture and scripted test doubles; no
transport, credential or network call exists in this file.
"""
import hashlib
import json
import re
import unittest
from dataclasses import replace
from pathlib import Path

from src.contracts.jsonutil import canonical_dumps, compute_content_digest
from src.demo import AT, seed
from src.judgment import JudgmentUnavailable
from src.judgment.bundle import (BUNDLE_VERSION, DEFAULT_THRESHOLDS, ESCALATION, QUESTION_SPECS, RULES, STATE_KEYS,
                                 compose, receipt, render_bundle, request_digest)
from src.judgment.systemone import (MAX_RESPONSE_BYTES, FixtureSystemOne, SystemOneService, record_questions,
                                    validate_answers, validate_response)
from src.review import InMemoryRepository, ReviewError, make_record, reference, validate_record

NOW = '2026-10-05T02:00:00Z'
MODEL = 'fixture-systemone'
#: The v5 Q2 vocabulary, mirrored here so the test states the token set independently
#: of the module under test.
EVENTS = ('planned_outage', 'forced_outage', 'return_to_service', 'derating', 'grid_alert',
          'testing', 'commercial_operation', 'other')
DIRECTIONS = ('supports', 'challenges', 'neither')
REPO_ROOT = Path(__file__).resolve().parents[1]

#: Every form answers these canonical values unless a row overrides a specific form.
#: Nouls are probabilities on the wire; composition takes the modal top option, so the
#: composed atomic values for this input are written down in ``BASE_TOPS``. ``BASE`` is
#: the demo seed's advisory (a testing state on the assumed supply-outlook field), so it
#: composes ``challenges`` through ``milestone_mismatch`` under v5.
BASE = {'q1': 'fictional-unit-a', 'q2': 'testing', 'q3': 'same', 'q4': 0.1, 'q5': 0.1, 'q6': 0.1,
        'q7': 0.9, 'q8': 'neither'}

#: The composed atomic values for BASE: q1 to q3 and q8 carry their option, q4 to q7 the
#: modal top option of the four forms (0.1 is below 0.5, 0.9 is at or above it).
BASE_TOPS = {'q1': 'fictional-unit-a', 'q2': 'testing', 'q3': 'same', 'q4': 'no', 'q5': 'no',
             'q6': 'no', 'q7': 'yes', 'q8': 'neither'}


def derived_task(task, *, field=None, candidates=None, quote=None, passages=None, input_fields=None):
    """A synthetic compiled-task dict derived from the H0 task for pure-renderer tests.

    ``field`` moves the assumption's input field and ``input_fields`` replaces the
    model representation's field table, so the availability-kind cases can build a
    field the representation defines (an availability kind) and a field it does not.
    """
    payload = json.loads(canonical_dumps(task['payload']))
    if field is not None:
        payload['assumption_definition']['input_field'] = field
    if candidates is not None:
        payload['mapping_definition'] = dict(payload['mapping_definition'], entities=candidates)
    if input_fields is not None:
        payload['model_representation'] = dict(payload['model_representation'], input_fields=input_fields)
    if quote is not None:
        payload['context'][0]['quote'] = quote
    if passages is not None:
        template = payload['context'][0]
        payload['context'] = [
            dict(template, passage_ref=dict(template['passage_ref'], record_id=f'fictional-passage-{index + 1}'),
                 quote=f'Synthetic passage {index + 1}: {template["quote"]}')
            for index in range(passages)]
    return {'record_kind': 'CompiledTask', 'payload': payload}


def candidate_entities(count):
    entities = [{'entity_id': 'fictional-unit-a', 'entity_type': 'GeneratingUnit'}]
    entities += [{'entity_id': f'synthetic-unit-{index}', 'entity_type': 'GeneratingUnit'}
                 for index in range(1, count)]
    return entities


def answers_for(bundle, atomic, flips=None):
    """Well-formed per-form answers from canonical atomic values.

    Each form answers in its own presentation: the permuted form's token, the aliased
    form's bracketed identifier, and the negated noul form's inverted probability.
    """
    questions = bundle['request']['questions']
    answers = {}
    for spec in QUESTION_SPECS:
        for form in range(bundle['forms']):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            question = questions[name]
            value = (flips or {}).get(spec['id'], {}).get(form, atomic[spec['id']])
            if question['type'] == 'choice':
                options = question['criteria']['options']
                token = next(token for token, canonical in options.items() if canonical == value)
                answers[name] = {'choice': token, 'probabilities': {token: 1.0}}
            else:
                answers[name] = {'noul': value if question['criteria']['options']['yes'] == 'yes' else 1 - value}
    return answers


class BundleTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()
        self.seed = seed(self.repo)
        self.actor = self.seed['actor']
        self.case = next(iter(self.actor.accessible_cases))
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        self.task = self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption', NOW, NOW)

    def render(self, task=None, **kwargs):
        return render_bundle(task or self.task, MODEL, **kwargs)


class BundleRenderTests(BundleTestCase):
    def test_deterministic_render_and_request_digest_for_the_h0_task(self):
        before = canonical_dumps(self.task)
        first, second = self.render(), self.render()
        self.assertEqual(canonical_dumps(first), canonical_dumps(second))
        self.assertEqual(first['request_digest'], second['request_digest'])
        self.assertEqual(first['request_digest'], request_digest(first['request']))
        self.assertEqual(first['request_digest'],
                         compute_content_digest({'bundle_version': BUNDLE_VERSION, 'input': first['request']}))
        self.assertRegex(first['request_digest'], r'^[0-9a-f]{64}$')
        self.assertEqual('rendered', first['status'])
        self.assertEqual({'model', 'state', 'questions'}, set(first['request']))
        self.assertEqual(MODEL, first['request']['model'])
        state = first['request']['state']
        self.assertEqual(set(STATE_KEYS), set(state))
        self.assertNotIn('access_scope', state)
        self.assertEqual('fictional-unit-a', state['assumption_definition']['entity']['entity_id'])
        self.assertEqual(before, canonical_dumps(self.task))  # render never mutates the task

    def test_question_budget_and_candidate_limit(self):
        questions = self.render()['request']['questions']
        expected = {f"{spec['id']}_{spec['slug']}_f{form}" for spec in QUESTION_SPECS for form in range(4)}
        self.assertEqual(32, len(questions))
        self.assertEqual(expected, set(questions))
        kinds = {name: question['type'] for name, question in questions.items()}
        self.assertEqual({'q4', 'q5', 'q6', 'q7'},
                         {name.split('_')[0] for name, kind in kinds.items() if kind == 'noul'})
        self.assertEqual({'fictional-unit-a', 'cannot_tell'},
                         set(questions['q1_identity_f0']['criteria']['options']))
        self.assertEqual(['fictional-unit-a', 'cannot_tell'],
                         questions['q1_identity_f0']['criteria']['presentation'])
        eight = self.render(derived_task(self.task, candidates=candidate_entities(8)))
        self.assertEqual('rendered', eight['status'])
        self.assertEqual(9, len(eight['request']['questions']['q1_identity_f0']['criteria']['options']))
        nine = self.render(derived_task(self.task, candidates=candidate_entities(9)))
        self.assertEqual('insufficient', nine['status'])
        self.assertEqual('TOO_MANY_CANDIDATES', nine['reason'])
        self.assertNotIn('request', nine)

    def test_four_forms_perturb_options_and_passage_order(self):
        questions = self.render()['request']['questions']
        canonical, permuted, aliased, passage_form = (questions[f'q2_event_f{form}'] for form in range(4))
        self.assertEqual({'options', 'presentation', 'passages'}, set(canonical['criteria']))
        self.assertEqual(list(EVENTS), canonical['criteria']['presentation'])
        self.assertEqual(list(EVENTS), list(aliased['criteria']['options'].values()))
        self.assertTrue(all(token.startswith('[') for token in aliased['criteria']['presentation']))
        self.assertEqual(set(canonical['criteria']['options']), set(permuted['criteria']['options']))
        self.assertEqual(set(canonical['criteria']['presentation']), set(permuted['criteria']['presentation']))
        self.assertNotEqual(canonical['criteria']['presentation'], permuted['criteria']['presentation'])
        # f3 perturbs the passage sequence only, so its wording is the f0 wording.
        self.assertEqual(canonical['instructions'], permuted['instructions'])
        self.assertEqual(canonical['instructions'], passage_form['instructions'])
        self.assertEqual({'options', 'passages'}, set(questions['q4_conditional_f0']['criteria']))
        self.assertEqual({'yes': 'yes', 'no': 'no'}, questions['q4_conditional_f0']['criteria']['options'])
        self.assertEqual({'yes': 'no', 'no': 'yes'}, questions['q4_conditional_f1']['criteria']['options'])
        self.assertEqual(questions['q4_conditional_f0']['instructions'], questions['q4_conditional_f2']['instructions'])
        self.assertEqual(set(DIRECTIONS), set(questions['q8_direction_f0']['criteria']['options']))
        self.assertEqual(set(DIRECTIONS), set(questions['q8_direction_f0']['criteria']['presentation']))

    def test_option_order_is_explicit_in_criteria_and_the_digest(self):
        bundle = self.render()
        canonical, permuted = (bundle['request']['questions'][f'q2_event_f{form}'] for form in range(2))

        def without_order(question):
            return {key: value for key, value in question['criteria'].items() if key != 'presentation'}

        # Canonical serialization sorts object keys, so nothing except the explicit
        # presentation list can carry the option order ...
        self.assertEqual(canonical_dumps(without_order(canonical)), canonical_dumps(without_order(permuted)))
        # ... which is why the presentation list is a list: it survives serialization and
        # makes the two forms distinguishable.
        self.assertNotEqual(canonical_dumps(canonical), canonical_dumps(permuted))
        # The request digest is sensitive to the presented order: swapping only the f0
        # sequence for f1's changes it.
        swapped = json.loads(canonical_dumps(bundle['request']))
        swapped['questions']['q2_event_f0']['criteria']['presentation'] = list(permuted['criteria']['presentation'])
        self.assertNotEqual(bundle['request_digest'], request_digest(swapped))
        self.assertEqual(bundle['request_digest'], request_digest(bundle['request']))

    def test_f3_reverses_the_presented_passage_order(self):
        bundle = self.render(derived_task(self.task, passages=3))
        questions = bundle['request']['questions']
        context = bundle['request']['state']['context']
        quotes = [entry['quote'] for entry in context]
        self.assertEqual(3, len({entry['passage_ref']['record_id'] for entry in context}))
        for spec in QUESTION_SPECS:
            orders = [questions[f"{spec['id']}_{spec['slug']}_f{form}"]['criteria']['passages'] for form in range(4)]
            self.assertEqual([0, 1, 2], orders[0])
            self.assertEqual(orders[0], orders[1])
            self.assertEqual(orders[0], orders[2])
            self.assertEqual([2, 1, 0], orders[3])
        presented = [quotes[index] for index in questions['q2_event_f3']['criteria']['passages']]
        self.assertEqual(list(reversed(quotes)), presented)
        # f3 differs from f0 only in the presented passage sequence, and that difference is
        # visible in canonical serialization and in the request digest.
        self.assertEqual(canonical_dumps({key: value for key, value in questions['q2_event_f0']['criteria'].items()
                                          if key != 'passages'}),
                         canonical_dumps({key: value for key, value in questions['q2_event_f3']['criteria'].items()
                                          if key != 'passages'}))
        self.assertNotEqual(canonical_dumps(questions['q2_event_f0']), canonical_dumps(questions['q2_event_f3']))
        swapped = json.loads(canonical_dumps(bundle['request']))
        swapped['questions']['q2_event_f0']['criteria']['passages'] = [2, 1, 0]
        self.assertNotEqual(bundle['request_digest'], request_digest(swapped))
        # One state serves all 32 questions, so it stays canonical: reordering it would
        # perturb every form, including f0.
        self.assertEqual(quotes, [entry['quote'] for entry in bundle['request']['state']['context']])

    def test_render_refusal_and_state_limit(self):
        refusal = self.render(derived_task(self.task, candidates=candidate_entities(9)))
        composed = compose(refusal, {})
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('TOO_MANY_CANDIDATES', composed['reason'])
        self.assertEqual('render_refused', composed['fired_rule'].split(':')[0])
        self.assertEqual(ESCALATION, composed['escalation'])
        oversized = derived_task(self.task, quote='x' * (140 * 1024))
        with self.assertRaises(JudgmentUnavailable) as caught:
            self.render(oversized)
        self.assertEqual('MODEL_INPUT_LIMIT', caught.exception.code)

    def test_caller_arguments_are_checked(self):
        self.assertRaises(ValueError, self.render, forms=0)
        self.assertRaises(ValueError, self.render, forms=5)
        self.assertRaises(ValueError, render_bundle, {'payload': {}}, MODEL)
        self.assertRaises(ValueError, render_bundle, self.task, '  ')
        broken = derived_task(self.task)
        broken['payload']['context'] = 'not a list'
        self.assertRaises(ValueError, self.render, broken)


#: ``atomic`` is the canonical answer value per question (nouls as probabilities);
#: ``atomic_out`` names only the composed atomic entries that differ from ``BASE_TOPS``,
#: so the expected composed value is written down rather than derived from the input.
#: ``field``/``input_fields`` move the assumption field and the model representation's
#: field table for the availability-kind rows; ``candidates`` widens the reviewed set.
#: The non-availability rows name ``commercial_operation`` with Q3 ``before`` and Q6
#: ``no``, which is the minimal input no availability-kind row and no later row matches.
ROW_CASES = (
    {'name': 'unstable', 'flips': {'q2': {0: 'testing', 1: 'testing', 2: 'planned_outage', 3: 'planned_outage'}},
     'atomic_out': {'q2': 'other'}, 'label': 'insufficient', 'rule': 'unstable', 'reason': 'UNSTABLE'},
    {'name': 'sufficiency gate', 'atomic': dict(BASE, q7=0.4), 'atomic_out': {'q7': 'no'},
     'label': 'insufficient', 'rule': 'sufficiency_gate', 'reason': 'LOW_SUFFICIENCY'},
    {'name': 'identity cannot_tell', 'atomic': dict(BASE, q1='cannot_tell'), 'atomic_out': {'q1': 'cannot_tell'},
     'label': 'insufficient', 'rule': 'identity_unknown', 'reason': 'IDENTITY_UNKNOWN'},
    {'name': 'unrelated entity', 'atomic': dict(BASE, q1='synthetic-unit-1'), 'candidates': 8,
     'atomic_out': {'q1': 'synthetic-unit-1'}, 'label': 'unrelated', 'rule': 'unrelated_entity', 'reason': None},
    {'name': 'other event', 'atomic': dict(BASE, q2='other'), 'atomic_out': {'q2': 'other'},
     'label': 'unrelated', 'rule': 'event_other', 'reason': None},
    {'name': 'grid alert', 'atomic': dict(BASE, q2='grid_alert'), 'atomic_out': {'q2': 'grid_alert'},
     'label': 'unrelated', 'rule': 'event_other', 'reason': None},
    {'name': 'lineage reuse', 'atomic': dict(BASE, q5=0.8), 'atomic_out': {'q5': 'yes'}, 'prior': 'challenges',
     'label': 'challenges', 'rule': 'lineage_reuse', 'reason': None, 'escalation': 'none'},
    {'name': 'lineage without prior', 'atomic': dict(BASE, q5=0.8), 'atomic_out': {'q5': 'yes'}, 'prior': None,
     'label': 'insufficient', 'rule': 'lineage_reuse', 'reason': 'LINEAGE_NO_PRIOR'},
    {'name': 'confirmed commercial operation', 'atomic': dict(BASE, q2='commercial_operation'),
     'atomic_out': {'q2': 'commercial_operation'},
     'label': 'supports', 'rule': 'availability_confirmed', 'reason': None},
    {'name': 'confirmed return to service', 'atomic': dict(BASE, q2='return_to_service'),
     'atomic_out': {'q2': 'return_to_service'},
     'label': 'supports', 'rule': 'availability_confirmed', 'reason': None},
    {'name': 'milestone mismatch', 'atomic': BASE, 'atomic_out': {},
     'label': 'challenges', 'rule': 'milestone_mismatch', 'reason': None},
    {'name': 'milestone mismatch on the availability-from field', 'atomic': BASE, 'field': 'commercial_availability_from',
     'input_fields': {'commercial_availability_from': {'quantity_kind': 'commercial_availability_from', 'unit': 'MW'}},
     'atomic_out': {}, 'label': 'challenges', 'rule': 'milestone_mismatch', 'reason': None},
    {'name': 'milestone mismatch on an available_capacity kind', 'atomic': BASE, 'field': 'available_capacity',
     'input_fields': {'available_capacity': {'quantity_kind': 'available_capacity', 'unit': 'MW'}},
     'atomic_out': {}, 'label': 'challenges', 'rule': 'milestone_mismatch', 'reason': None},
    {'name': 'milestone mismatch on a field absent from the representation', 'atomic': BASE,
     'field': 'commercial_availability_from', 'atomic_out': {},
     'label': 'insufficient', 'rule': 'fall_through', 'reason': 'FALL_THROUGH'},
    {'name': 'milestone mismatch on a non-availability field', 'atomic': BASE, 'field': 'fictional-feed-in-price',
     'input_fields': {'fictional-feed-in-price': {'quantity_kind': 'php_per_mwh', 'unit': 'PHP/MWh'}},
     'atomic_out': {}, 'label': 'insufficient', 'rule': 'fall_through', 'reason': 'FALL_THROUGH'},
    {'name': 'planned outage', 'atomic': dict(BASE, q2='planned_outage'), 'atomic_out': {'q2': 'planned_outage'},
     'label': 'challenges', 'rule': 'outage_or_later', 'reason': None},
    {'name': 'forced outage', 'atomic': dict(BASE, q2='forced_outage'), 'atomic_out': {'q2': 'forced_outage'},
     'label': 'challenges', 'rule': 'outage_or_later', 'reason': None},
    {'name': 'derating', 'atomic': dict(BASE, q2='derating'), 'atomic_out': {'q2': 'derating'},
     'label': 'challenges', 'rule': 'outage_or_later', 'reason': None},
    {'name': 'later than the assumed time', 'atomic': dict(BASE, q2='commercial_operation', q3='after'),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'after'},
     'label': 'challenges', 'rule': 'outage_or_later', 'reason': None},
    {'name': 'an outage on a non-availability field falls through', 'atomic': dict(BASE, q2='forced_outage'),
     'field': 'fictional-feed-in-price',
     'input_fields': {'fictional-feed-in-price': {'quantity_kind': 'php_per_mwh', 'unit': 'PHP/MWh'}},
     'atomic_out': {'q2': 'forced_outage'}, 'label': 'insufficient', 'rule': 'fall_through', 'reason': 'FALL_THROUGH'},
    {'name': 'earlier observation', 'atomic': dict(BASE, q2='commercial_operation', q3='before', q6=0.9),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'before', 'q6': 'yes'},
     'label': 'supports', 'rule': 'earlier_observation', 'reason': None},
    {'name': 'direction conflict', 'atomic': dict(BASE, q2='commercial_operation', q3='before', q6=0.9,
                                                 q8='challenges'),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'before', 'q6': 'yes', 'q8': 'challenges'},
     'label': 'mixed', 'rule': 'direction_conflict', 'reason': None},
    {'name': 'conditional support', 'atomic': dict(BASE, q2='commercial_operation', q4=0.9),
     'atomic_out': {'q2': 'commercial_operation', 'q4': 'yes'},
     'label': 'mixed', 'rule': 'conditional_support', 'reason': None},
    {'name': 'time not stated with direction', 'atomic': dict(BASE, q2='commercial_operation', q3='not_stated',
                                                              q8='supports'),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'not_stated', 'q8': 'supports'},
     'label': 'mixed', 'rule': 'time_not_stated', 'reason': None},
    {'name': 'time not stated and neither', 'atomic': dict(BASE, q2='commercial_operation', q3='not_stated'),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'not_stated'},
     'label': 'insufficient', 'rule': 'time_not_stated', 'reason': 'NOT_STATED_NEITHER'},
    {'name': 'fall through', 'atomic': dict(BASE, q2='commercial_operation', q3='before'),
     'atomic_out': {'q2': 'commercial_operation', 'q3': 'before'},
     'label': 'insufficient', 'rule': 'fall_through', 'reason': 'FALL_THROUGH'},
)


class CompositionTests(BundleTestCase):
    def test_every_composition_row_fires_on_its_minimal_input(self):
        seen = set()
        for case in ROW_CASES:
            with self.subTest(case=case['name']):
                candidates = candidate_entities(case['candidates']) if case.get('candidates') else None
                bundle = self.render(derived_task(self.task, field=case.get('field'), candidates=candidates,
                                                  input_fields=case.get('input_fields')))
                composed = compose(bundle, answers_for(bundle, case.get('atomic', BASE), case.get('flips')),
                                   prior_label=case.get('prior'))
                self.assertEqual(case['label'], composed['label'])
                self.assertEqual(case['rule'], composed['fired_rule'].split(':')[0])
                self.assertEqual(case['reason'], composed['reason'])
                self.assertEqual(case.get('escalation', ESCALATION if case['label'] == 'insufficient' else 'none'),
                                 composed['escalation'])
                self.assertEqual(dict(BASE_TOPS, **case.get('atomic_out', {})), composed['atomic'])
                self.assertEqual(DEFAULT_THRESHOLDS, composed['thresholds'])
                seen.add(case['rule'])
        self.assertEqual(set(RULES), seen)  # the table is total and every row is exercised

    def test_every_event_token_round_trips_through_all_four_forms(self):
        self.assertEqual(('planned_outage', 'forced_outage', 'return_to_service', 'derating', 'grid_alert',
                          'testing', 'commercial_operation', 'other'), EVENTS)
        bundle = self.render()
        self.assertEqual(list(EVENTS), bundle['request']['questions']['q2_event_f0']['criteria']['presentation'])
        # One canonical answer per token, in every form: f1 permutes, f2 aliases and f3
        # reorders the passages, so the composition's atomic Q2 is the token itself only
        # if un-aliasing round-trips.
        for token in EVENTS:
            with self.subTest(event=token):
                composed = compose(bundle, answers_for(bundle, dict(BASE, q2=token)))
                self.assertEqual(token, composed['atomic']['q2'])

    def test_availability_kind_is_read_from_the_model_representation(self):
        # Q2 = testing is the milestone row's token; the row needs the field to be an
        # availability fact, which only the representation can say. Positive cases: the
        # synthetic quantity kind, a name-prefixed field, and the available_capacity kind
        # the brief names. Negative: a field the representation defines as something else,
        # and a name that sounds like an availability field but is absent entirely.
        positives = (
            ('the assumption field as seeded', None, None),
            ('the availability-from name prefix', 'commercial_availability_from',
             {'commercial_availability_from': {'quantity_kind': 'commercial_availability_from', 'unit': 'MW'}}),
            ('an available_capacity quantity kind', 'available_capacity',
             {'available_capacity': {'quantity_kind': 'available_capacity', 'unit': 'MW'}}),
        )
        for name, field, input_fields in positives:
            with self.subTest(case=name):
                bundle = self.render(derived_task(self.task, field=field, input_fields=input_fields))
                composed = compose(bundle, answers_for(bundle, BASE))
                self.assertEqual(('challenges', 'milestone_mismatch'),
                                 (composed['label'], composed['fired_rule'].split(':')[0]))
        negatives = (
            ('a non-availability field', 'fictional-feed-in-price',
             {'fictional-feed-in-price': {'quantity_kind': 'php_per_mwh', 'unit': 'PHP/MWh'}}),
            ('a field absent from the representation', 'commercial_availability_from', None),
        )
        for name, field, input_fields in negatives:
            with self.subTest(case=name):
                bundle = self.render(derived_task(self.task, field=field, input_fields=input_fields))
                composed = compose(bundle, answers_for(bundle, BASE))
                self.assertEqual(('insufficient', 'fall_through'),
                                 (composed['label'], composed['fired_rule'].split(':')[0]))

    def test_modal_tie_on_q3_resolves_to_not_stated(self):
        bundle = self.render()
        answers = answers_for(bundle, BASE, {'q3': {0: 'before', 1: 'before', 2: 'after', 3: 'after'}})
        rec = receipt(bundle, answers)
        self.assertEqual({'f0': 'before', 'f1': 'before', 'f2': 'after', 'f3': 'after'},
                         rec['questions']['q3']['tops'])
        # No form named the tie option, so every form differs from the resolved top and
        # the receipt's first row, not `time_not_stated`, is the one that fires.
        self.assertEqual(1.0, rec['questions']['q3']['flip_rate'])
        self.assertEqual(['q3'], rec['unstable_questions'])
        composed = compose(bundle, answers)
        self.assertEqual('not_stated', composed['atomic']['q3'])
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('UNSTABLE', composed['reason'])

    def test_tie_options_are_per_question(self):
        bundle = self.render(derived_task(self.task, candidates=candidate_entities(8)))
        flips = {'q1': {0: 'fictional-unit-a', 1: 'fictional-unit-a', 2: 'synthetic-unit-1', 3: 'synthetic-unit-1'},
                 'q2': {0: 'testing', 1: 'testing', 2: 'planned_outage', 3: 'planned_outage'},
                 'q8': {0: 'supports', 1: 'supports', 2: 'challenges', 3: 'challenges'}}
        composed = compose(bundle, answers_for(bundle, BASE, flips))
        self.assertEqual({'q1': 'cannot_tell', 'q2': 'other', 'q3': 'same', 'q8': 'neither'},
                         {qid: composed['atomic'][qid] for qid in ('q1', 'q2', 'q3', 'q8')})

    def test_two_of_four_flip_on_q2_downgrades_to_unstable(self):
        bundle = self.render()
        answers = answers_for(bundle, dict(BASE, q3='after'),
                              {'q2': {0: 'forced_outage', 1: 'forced_outage', 2: 'planned_outage', 3: 'derating'}})
        rec = receipt(bundle, answers)
        self.assertEqual(['q2'], rec['unstable_questions'])
        self.assertEqual(0.5, rec['questions']['q2']['flip_rate'])  # two of four forms differ from the modal top
        composed = compose(bundle, answers)
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('UNSTABLE', composed['reason'])
        self.assertEqual(ESCALATION, composed['escalation'])
        self.assertEqual('unstable', composed['fired_rule'].split(':')[0])
        # The same answers without the downgrade compose `challenges` from Q3=after.
        stable = compose(bundle, answers, {'tau_flip': 0.6})
        self.assertEqual('challenges', stable['label'])
        self.assertEqual('outage_or_later', stable['fired_rule'].split(':')[0])

    def test_polarity_gap_of_point_four_flags_unstable(self):
        bundle = self.render()
        # Raw answers p(yes, f0) = 0.8 and p(yes, f1 negated) = 0.6; the f1 form is negated,
        # so its canonical value is 1 - 0.6 = 0.4 and the gap is |0.8 - 0.4| = 0.4.
        answers = answers_for(bundle, BASE, {'q4': {0: 0.8, 1: 0.4, 2: 0.1, 3: 0.1}})
        self.assertEqual(0.8, answers['q4_conditional_f0']['noul'])
        self.assertEqual(0.6, answers['q4_conditional_f1']['noul'])
        rec = receipt(bundle, answers)
        self.assertEqual(0.4, rec['questions']['q4']['polarity_gap'])
        self.assertEqual(0.7, rec['questions']['q4']['max_gap'])
        self.assertEqual(0.25, rec['questions']['q4']['flip_rate'])
        self.assertEqual(['q4'], rec['unstable_questions'])
        composed = compose(bundle, answers)
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('UNSTABLE', composed['reason'])
        self.assertEqual(ESCALATION, composed['escalation'])

    def test_noul_composition_uses_the_modal_form_top_not_the_mean(self):
        bundle = self.render()
        # Review counterexample: Q6 canonical probabilities [0.49, 0.49, 0.49, 1.0] have a
        # mean of 0.6175, so a mean-based composition read Q6 as yes; the modal top of the
        # per-form tops is no, and only the fourth form differs (flip_rate 0.25). The event
        # is commercial operation so the only row Q6=yes could reach is earlier_observation.
        answers = answers_for(bundle, dict(BASE, q2='commercial_operation', q3='before'),
                              {'q6': {0: 0.49, 1: 0.49, 2: 0.49, 3: 1.0}})
        rec = receipt(bundle, answers)
        self.assertEqual({'f0': 'no', 'f1': 'no', 'f2': 'no', 'f3': 'yes'}, rec['questions']['q6']['tops'])
        self.assertEqual(0.25, rec['questions']['q6']['flip_rate'])
        self.assertFalse(rec['unstable'])
        self.assertEqual([], rec['unstable_questions'])
        # Q6 is no, so the earlier-observation row cannot fire and nothing below it
        # matches this fixture: it falls through to insufficient, not `supports`.
        composed = compose(bundle, answers)
        self.assertEqual('no', composed['atomic']['q6'])
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('fall_through', composed['fired_rule'].split(':')[0])
        self.assertEqual('FALL_THROUGH', composed['reason'])
        self.assertEqual(ESCALATION, composed['escalation'])

    def test_noul_threshold_rows_read_the_modal_top_not_the_mean(self):
        bundle = self.render()
        # Tops [yes, no, no, no]: modal no, flip_rate 0.25 and polarity_gap 0.29, so the
        # bundle is stable under the recorded thresholds while the mean is 0.5625 — the
        # value a mean reading would compare to the threshold. The f0 value is 0.78 and
        # not 0.79 because 0.79 - 0.49 is 0.30000000000000004: under the unrounded
        # comparison that gap is above tau_pol 0.3 and the instability row would mask
        # the row this test is about. The un-negated f1 round trip is exact for 0.49.
        answers = answers_for(bundle, BASE, {'q7': {0: 0.78, 1: 0.49, 2: 0.49, 3: 0.49}})
        rec = receipt(bundle, answers)
        self.assertEqual({'f0': 'yes', 'f1': 'no', 'f2': 'no', 'f3': 'no'}, rec['questions']['q7']['tops'])
        self.assertEqual(0.25, rec['questions']['q7']['flip_rate'])
        self.assertEqual(0.29, rec['questions']['q7']['polarity_gap'])
        self.assertFalse(rec['unstable'])
        # tau_suff 0.5 sits below the mean 0.5625, so a mean-based gate would pass this
        # fixture; the modal top is no and the gate fires on it.
        composed = compose(bundle, answers, {'tau_suff': 0.5})
        self.assertEqual('no', composed['atomic']['q7'])
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('sufficiency_gate', composed['fired_rule'].split(':')[0])
        self.assertEqual('LOW_SUFFICIENCY', composed['reason'])
        # The same tops on Q4 under the recorded tau_cond 0.5: the mean 0.5625 is at or
        # above tau_cond, yet the modal top no leaves the statement confirmed.
        confirmed = answers_for(bundle, dict(BASE, q2='commercial_operation'),
                                {'q4': {0: 0.78, 1: 0.49, 2: 0.49, 3: 0.49}})
        composed = compose(bundle, confirmed)
        self.assertEqual('no', composed['atomic']['q4'])
        self.assertEqual('supports', composed['label'])
        self.assertEqual('availability_confirmed', composed['fired_rule'].split(':')[0])

    def test_noul_split_has_no_modal_top_and_the_receipt_cannot_see_the_reading(self):
        bundle = self.render()
        yes_first = answers_for(bundle, BASE, {'q6': {0: 0.7, 1: 0.7, 2: 0.3, 3: 0.3}})
        no_first = answers_for(bundle, BASE, {'q6': {0: 0.3, 1: 0.3, 2: 0.7, 3: 0.7}})
        first, second = receipt(bundle, yes_first), receipt(bundle, no_first)
        self.assertEqual({'f0': 'yes', 'f1': 'yes', 'f2': 'no', 'f3': 'no'}, first['questions']['q6']['tops'])
        self.assertEqual({'f0': 'no', 'f1': 'no', 'f2': 'yes', 'f3': 'yes'}, second['questions']['q6']['tops'])
        # An exact split has no modal top: either side leaves two of four forms outside
        # it, so flip_rate, instability and the outcome under the recorded defaults are
        # identical whichever side a reading picked.
        self.assertEqual(0.5, first['questions']['q6']['flip_rate'])
        self.assertEqual(0.5, second['questions']['q6']['flip_rate'])
        self.assertTrue(first['unstable'])
        self.assertTrue(second['unstable'])
        for answers in (yes_first, no_first):
            composed = compose(bundle, answers)
            self.assertEqual(('insufficient', 'UNSTABLE'), (composed['label'], composed['reason']))
        # Above the recorded tau_flip the split is stable, so the resolution is
        # observable. The intent names tie options only for choice questions; NOUL_TIE
        # reads an even split as `no`, not a majority for yes.
        self.assertEqual('no', compose(bundle, yes_first, {'tau_flip': 0.6})['atomic']['q6'])
        self.assertEqual('no', compose(bundle, no_first, {'tau_flip': 0.6})['atomic']['q6'])

    def test_prior_label_must_be_a_relation_label(self):
        bundle = self.render()
        with self.assertRaises(ValueError):
            compose(bundle, answers_for(bundle, BASE), prior_label='approved')


class RoundingBoundaryTests(BundleTestCase):
    """Boundary cases for the rounding rule: decisions read raw, presentation rounds.

    Every case below changes side if the value is rounded before it is compared, which
    is the re-review 2 finding. The receipt's presented number can therefore sit exactly
    on a threshold while the raw value decided the other way.
    """

    def test_noul_top_is_chosen_from_the_unrounded_probability(self):
        bundle = self.render()
        # Reviewer counterexample: canonical Q6 = 0.4999996 on every form. round(x, 6)
        # reaches 0.5, so a rounded-first read takes the top to yes and, with Q3=before,
        # composes `supports`; the value the answer carries is below the boundary, every
        # top is no, and the table falls through. The event is commercial operation with
        # Q3 before, the minimal shape where only Q6 stands between the row and supports.
        answers = answers_for(bundle, dict(BASE, q2='commercial_operation', q3='before'),
                              {'q6': {form: 0.4999996 for form in range(4)}})
        self.assertEqual(0.5, round(0.4999996, 6))  # the value rounding first would compare
        rec = receipt(bundle, answers)
        self.assertEqual({'f0': 'no', 'f1': 'no', 'f2': 'no', 'f3': 'no'}, rec['questions']['q6']['tops'])
        self.assertEqual(0.0, rec['questions']['q6']['flip_rate'])
        self.assertFalse(rec['unstable'])
        composed = compose(bundle, answers)
        self.assertEqual('no', composed['atomic']['q6'])
        self.assertEqual('insufficient', composed['label'])
        self.assertEqual('fall_through', composed['fired_rule'].split(':')[0])
        self.assertEqual('FALL_THROUGH', composed['reason'])
        self.assertEqual(ESCALATION, composed['escalation'])
        # The boundary itself is inclusive: an answer of exactly 0.5 takes the yes top
        # and the earlier-observation row fires.
        at_boundary = answers_for(bundle, dict(BASE, q2='commercial_operation', q3='before'),
                                  {'q6': {form: 0.5 for form in range(4)}})
        self.assertEqual('yes', receipt(bundle, at_boundary)['questions']['q6']['tops']['f0'])
        composed = compose(bundle, at_boundary)
        self.assertEqual('supports', composed['label'])
        self.assertEqual('earlier_observation', composed['fired_rule'].split(':')[0])
        self.assertEqual('none', composed['escalation'])

    def test_polarity_gap_is_compared_before_rounding(self):
        bundle = self.render()
        # Reviewer counterexample: canonical Q4 = [0.4000004, 0.1, 0.1, 0.1]. The raw gap
        # is above tau_pol 0.3 and the bundle is unstable; the presented value rounds to
        # 0.3, a number that is not itself above the threshold.
        answers = answers_for(bundle, BASE, {'q4': {0: 0.4000004, 1: 0.1, 2: 0.1, 3: 0.1}})
        canonical_f1 = 1 - answers['q4_conditional_f1']['noul']  # the intent's 1 - p(yes, f1 negated)
        self.assertGreater(abs(0.4000004 - canonical_f1), DEFAULT_THRESHOLDS['tau_pol'])
        rec = receipt(bundle, answers)
        self.assertEqual({'f0': 'no', 'f1': 'no', 'f2': 'no', 'f3': 'no'}, rec['questions']['q4']['tops'])
        self.assertEqual(0.0, rec['questions']['q4']['flip_rate'])
        self.assertEqual(0.3, rec['questions']['q4']['polarity_gap'])
        self.assertFalse(rec['questions']['q4']['polarity_gap'] > DEFAULT_THRESHOLDS['tau_pol'])
        self.assertTrue(rec['unstable'])
        self.assertEqual(['q4'], rec['unstable_questions'])
        composed = compose(bundle, answers)
        self.assertEqual(('insufficient', 'UNSTABLE'), (composed['label'], composed['reason']))
        self.assertEqual(ESCALATION, composed['escalation'])

    def test_flip_rate_is_compared_before_rounding(self):
        # With three forms a one-form difference is 1/3 = 0.3333333333..., presented as
        # 0.333333. A threshold of 0.3333333 sits between the two, so rounding first
        # reports stable and the raw value reports unstable.
        bundle = self.render(forms=3)
        answers = answers_for(bundle, BASE, {'q2': {0: 'testing', 1: 'testing', 2: 'planned_outage'}})
        rec = receipt(bundle, answers, {'tau_flip': 0.3333333})
        self.assertEqual(0.333333, rec['questions']['q2']['flip_rate'])
        self.assertFalse(rec['questions']['q2']['flip_rate'] > 0.3333333)
        self.assertTrue(rec['unstable'])
        self.assertEqual(['q2'], rec['unstable_questions'])
        composed = compose(bundle, answers, {'tau_flip': 0.3333333})
        self.assertEqual(('insufficient', 'UNSTABLE'), (composed['label'], composed['reason']))

    def test_named_threshold_boundaries_read_the_hard_yes_no_tops(self):
        # Noul tops reach the named composition thresholds as a hard yes (1.0) or no
        # (0.0), so their reachable boundaries are the ends of [0, 1]: tau_suff 1.0
        # passes a yes top and fires on a no top, tau_lineage 1.0 includes yes and
        # excludes no, tau_cond 0.5 confirms a no top while tau_cond 0.0 puts the
        # confirmed row out of reach (nothing is below it) and the mixed row fires.
        # `open` is BASE moved off the milestone token: commercial operation with Q3
        # before reaches no row at all, so a lifted threshold shows as fall_through.
        open_base = dict(BASE, q2='commercial_operation', q3='before')
        cases = (
            ('tau_suff 1.0 keeps the gate open for Q7 yes', open_base, {'tau_suff': 1.0},
             'insufficient', 'fall_through', 'FALL_THROUGH'),
            ('tau_suff 1.0 fires the gate on Q7 no', dict(BASE, q7=0.4), {'tau_suff': 1.0},
             'insufficient', 'sufficiency_gate', 'LOW_SUFFICIENCY'),
            ('tau_lineage 1.0 includes a Q5 yes top', dict(BASE, q5=0.9), {'tau_lineage': 1.0},
             'insufficient', 'lineage_reuse', 'LINEAGE_NO_PRIOR'),
            ('tau_lineage 1.0 excludes a Q5 no top', dict(open_base, q5=0.1), {'tau_lineage': 1.0},
             'insufficient', 'fall_through', 'FALL_THROUGH'),
            ('tau_cond 0.5 confirms a Q4 no top', dict(BASE, q2='commercial_operation'), {'tau_cond': 0.5},
             'supports', 'availability_confirmed', None),
            ('tau_cond 0.0 leaves the confirmed row unreachable', dict(BASE, q2='commercial_operation'),
             {'tau_cond': 0.0}, 'mixed', 'conditional_support', None),
        )
        bundle = self.render()
        for name, atomic, thresholds, label, rule, reason in cases:
            with self.subTest(case=name):
                composed = compose(bundle, answers_for(bundle, atomic), thresholds)
                self.assertEqual(label, composed['label'])
                self.assertEqual(rule, composed['fired_rule'].split(':')[0])
                self.assertEqual(reason, composed['reason'])


class ReceiptTests(BundleTestCase):
    def test_receipt_records_thresholds_and_choices_per_form(self):
        bundle = self.render()
        answers = answers_for(bundle, BASE, {'q2': {0: 'testing', 1: 'testing', 2: 'testing', 3: 'planned_outage'}})
        default = receipt(bundle, answers)
        self.assertEqual(4, default['forms'])
        self.assertEqual(DEFAULT_THRESHOLDS, default['thresholds'])
        self.assertEqual(0.25, default['questions']['q2']['flip_rate'])
        self.assertFalse(default['unstable'])  # 0.25 is not above tau_flip
        entry = default['questions']['q2']
        self.assertEqual({'slug', 'type', 'tops', 'flip_rate', 'polarity_gap', 'max_gap'}, set(entry))
        self.assertEqual({'f0': 'testing', 'f1': 'testing', 'f2': 'testing', 'f3': 'planned_outage'}, entry['tops'])
        self.assertIsNone(entry['polarity_gap'])
        strict = receipt(bundle, answers, {'tau_flip': 0.2})
        self.assertEqual(0.2, strict['thresholds']['tau_flip'])
        self.assertEqual(0.6, strict['thresholds']['tau_suff'])  # unnamed thresholds keep their defaults
        self.assertEqual(['q2'], strict['unstable_questions'])
        self.assertRaises(ValueError, receipt, bundle, answers, {'tau_unknown': 0.5})
        self.assertRaises(ValueError, receipt, bundle, answers, {'tau_flip': 2})

    def test_invalid_answers_raise_model_invalid_response(self):
        bundle = self.render()
        good = answers_for(bundle, BASE)
        missing = dict(good); missing.pop('q1_identity_f0')
        unknown = dict(good); unknown['q1_identity_f0'] = {'choice': 'who', 'probabilities': {'who': 1.0}}
        out_of_range = dict(good); out_of_range['q4_conditional_f0'] = {'noul': 1.2}
        incomplete = dict(good); incomplete['q1_identity_f0'] = {'choice': 'fictional-unit-a'}
        for answers in (missing, unknown, out_of_range, incomplete):
            for call in (receipt, compose):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    call(bundle, answers)
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)


# --------------------------------------------------------------------------------------
# S2: System One port, fixture backend, ProbeBundleArtifact, repository methods and service
# --------------------------------------------------------------------------------------

SYSTEMONE_MODEL = 'fixture-systemone'

#: A canonical input that composes a real label (`challenges`, rule `outage_or_later`), so
#: the saved artifact carries a decision rather than the fall-through of ``BASE``.
S2_BASE = dict(BASE, q2='forced_outage')

#: A later cutoff for the lineage rows: the same source is known, so the task differs
#: from the seeded one in ``information_cutoff`` alone and is still a task for the
#: same assumption.
LATER = '2026-10-06T00:00:00Z'


class ScriptedSystemOne:
    """A test backend returning exactly one fixed response, verbatim.

    Used for response shapes the dictionary-keyed fixture cannot produce (an oversized
    response, an answer keyed under an unknown question).
    """
    name = 'scripted-systemone'
    model = SYSTEMONE_MODEL
    execution_mode = 'synthetic_fixture'
    probabilities = 'fixture_supplied'

    def __init__(self, response):
        self.response = response
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        return json.loads(canonical_dumps(self.response))


class FailingSystemOne:
    """A backend that raises; the service must map it without leaking its text."""
    name, model, execution_mode = 'failing-systemone', SYSTEMONE_MODEL, 'synthetic_fixture'

    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        raise TimeoutError('private backend detail')


class DisclosingSystemOne:
    """A backend failing with a ``JudgmentUnavailable`` carrying its own code.

    ``decide`` is the port; whatever it raises is a backend failure, so the service
    must return the one safe code and never echo this text.
    """
    name, model, execution_mode = 'disclosing-systemone', SYSTEMONE_MODEL, 'synthetic_fixture'

    def __init__(self, code):
        self.code = code
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        raise JudgmentUnavailable(self.code)


class StubBundleRepository:
    """The one read the service performs, handing back a task the renderer refuses.

    ``save_bundle`` raises rather than records, so a refusal that ever reached a write
    would fail the test instead of passing quietly.
    """
    def __init__(self, task):
        self.task, self.saved = task, []

    def bundle_input(self, actor, case, task_ref, key):
        return None, self.task

    def save_bundle(self, *args, **kwargs):
        self.saved.append(args)
        raise AssertionError('a refused render must not write')


class RevokingBundleRepository:
    """One generation, two memberships: the adapter's save-time access boundary.

    ``PersistentRepository.execute`` hands each repository operation the actor its
    membership store holds at that moment, so a policy revoked while the backend runs is
    in force at ``save_bundle`` even though ``bundle_lineage_prior`` resolved the prior
    under the older membership. This stub reproduces that boundary in memory: reads use
    the caller's actor, the save uses ``save_actor``.
    """

    def __init__(self, repository, save_actor):
        self.repository, self.save_actor = repository, save_actor

    def bundle_input(self, actor, case, task_ref, key):
        return self.repository.bundle_input(actor, case, task_ref, key)

    def bundle_lineage_prior(self, actor, case, task_ref):
        return self.repository.bundle_lineage_prior(actor, case, task_ref)

    def save_bundle(self, actor, case, *args):
        return self.repository.save_bundle(self.save_actor, case, *args)


class SystemOnePortTests(BundleTestCase):
    def test_response_envelope_and_answers_are_validated(self):
        bundle = self.render()
        good = answers_for(bundle, S2_BASE)
        answers, model_version = validate_response(bundle, {'answers': good, 'model_version': 'fixture-1'})
        self.assertEqual(good, answers)
        self.assertIsNot(good, answers)  # a defensive copy, raw probabilities kept
        self.assertEqual(0.9, answers['q7_sufficiency_f0']['noul'])
        self.assertEqual('fixture-1', model_version)
        self.assertEqual(64 * 1024, MAX_RESPONSE_BYTES)

        invalid_answers = {
            'missing question': {k: v for k, v in good.items() if k != 'q1_identity_f0'},
            'unknown question': dict(good, q9_nothing_f0={'choice': 'fictional-unit-a',
                                                          'probabilities': {'fictional-unit-a': 1.0}}),
            'unknown option': dict(good, q1_identity_f0={'choice': 'who', 'probabilities': {'who': 1.0}}),
            'probability above one': dict(good, q4_conditional_f0={'noul': 1.2}),
            'probability below zero': dict(good, q6_observation_f0={'noul': -0.1}),
            'unknown probability option': dict(good, q1_identity_f0={'choice': 'fictional-unit-a',
                                                                     'probabilities': {'who': 1.0}}),
            'incomplete answer': dict(good, q1_identity_f0={'choice': 'fictional-unit-a'}),
        }
        for name, answers_case in invalid_answers.items():
            with self.subTest(case=name):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    validate_response(bundle, {'answers': answers_case, 'model_version': 'fixture-1'})
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)

        invalid_responses = (
            {'answers': good},
            {'answers': good, 'model_version': 'fixture-1', 'extra': 1},
            {'answers': good, 'model_version': ''},
            {'answers': good, 'model_version': 'x' * 201},
            {'answers': good, 'model_version': 'x' * (70 * 1024)},  # over the 64 KiB bound
            {'answers': dict(good, q1_identity_f0={'choice': 'fictional-unit-a',
                                                   'probabilities': {'fictional-unit-a': 1.0},
                                                   'note': 'x' * (70 * 1024)}), 'model_version': 'fixture-1'},
            [],
            'text',
        )
        for response in invalid_responses:
            with self.subTest(response=str(response)[:60]):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    validate_response(bundle, response)
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
        with self.assertRaises(ValueError):  # a caller error, not a model response
            validate_response({'status': 'insufficient', 'reason': 'TOO_MANY_CANDIDATES'}, {'answers': good})

    def test_record_questions_carry_names_types_criteria_form_kinds_and_no_state(self):
        bundle = self.render()
        recorded = record_questions(bundle)
        self.assertEqual(set(bundle['request']['questions']), set(recorded))
        self.assertEqual(32, len(recorded))
        for name, question in recorded.items():
            self.assertEqual({'type', 'form', 'instructions', 'criteria'}, set(question))
            self.assertEqual(bundle['request']['questions'][name]['type'], question['type'])
            self.assertEqual(bundle['request']['questions'][name]['criteria'], question['criteria'])
            self.assertEqual(bundle['request']['questions'][name]['instructions'], question['instructions'])
            self.assertEqual(name.rsplit('_f', 1)[-1], question['form'][1:])
        self.assertEqual('f0', recorded['q1_identity_f0']['form'])
        self.assertEqual('f3', recorded['q8_direction_f3']['form'])
        self.assertNotIn('state', recorded)  # the task state stays out of the record
        self.assertTrue(all('state' not in question for question in recorded.values()))
        # The record's questions carry the extra form/instructions keys and still validate answers.
        self.assertEqual(answers_for(bundle, S2_BASE), validate_answers(recorded, answers_for(bundle, S2_BASE)))
        with self.assertRaises(ValueError):
            record_questions({'status': 'insufficient', 'reason': 'TOO_MANY_CANDIDATES'})

    def test_fixture_backend_answers_only_the_questions_asked(self):
        bundle = self.render()
        good = answers_for(bundle, S2_BASE)
        fixture = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, dict(good, q9_extra_f0={'choice': 'x'}))
        response = fixture.decide(bundle['request'])
        self.assertEqual(set(good), set(response['answers']))
        self.assertEqual(good, response['answers'])
        self.assertEqual('fixture-1', response['model_version'])
        self.assertEqual([bundle['request']], fixture.requests)
        self.assertEqual({'answers': {}, 'model_version': 'fixture-1'},
                         FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, {}).decide(bundle['request']))
        # A fixture that omits an answer produces a response the port rejects.
        dropped = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL,
                                   {k: v for k, v in good.items() if k != 'q4_conditional_f0'})
        with self.assertRaises(JudgmentUnavailable) as caught:
            validate_response(bundle, dropped.decide(bundle['request']))
        self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
        self.assertRaises(ValueError, FixtureSystemOne, '  ', SYSTEMONE_MODEL, {})
        self.assertRaises(ValueError, FixtureSystemOne, 'fixture-systemone', SYSTEMONE_MODEL, [])


class ProbeBundleServiceTests(BundleTestCase):
    def setUp(self):
        super().setUp()
        self.rendered = self.render()
        self.answers = answers_for(self.rendered, S2_BASE)
        self.backend = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, self.answers)
        self.service = SystemOneService(self.backend)

    def generate(self, key='probe-a', task=None, clock=None, actor=None, service=None):
        return (service or self.service).generate(self.repo, actor or self.actor, self.case,
                                                  reference(task or self.task), key, clock or (lambda: NOW))

    def assertCode(self, code, call, *args, **kwargs):
        with self.assertRaises(ReviewError) as caught:
            call(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return str(caught.exception)

    def test_service_saves_the_probe_bundle_artifact_and_replays_without_a_call(self):
        saved = self.generate()
        self.assertEqual('ProbeBundleArtifact', saved['record_kind'])
        payload = saved['payload']
        self.assertEqual({'task_ref', 'actor_id', 'idempotency_key', 'questions', 'answers', 'composed',
                          'receipt', 'metadata', 'review_state', 'synthetic', 'permission_ref'}, set(payload))
        self.assertEqual(reference(self.task), payload['task_ref'])
        self.assertEqual(self.actor.actor_id, payload['actor_id'])
        self.assertEqual('probe-a', payload['idempotency_key'])
        self.assertEqual('proposed', payload['review_state'])
        self.assertIs(True, payload['synthetic'])
        # Every stored value is either the raw validated answers or S1 output.
        self.assertEqual(self.answers, payload['answers'])
        self.assertEqual(compose(self.rendered, self.answers), payload['composed'])
        self.assertEqual(receipt(self.rendered, self.answers), payload['receipt'])
        self.assertEqual(('challenges', 'outage_or_later', None),
                         (payload['composed']['label'], payload['composed']['fired_rule'].split(':')[0],
                          payload['composed']['reason']))
        self.assertEqual(record_questions(self.rendered), payload['questions'])
        metadata = payload['metadata']
        self.assertEqual({'provider', 'model', 'model_version', 'execution_mode', 'bundle_version',
                          'probabilities', 'request_digest', 'output_digest'}, set(metadata))
        self.assertEqual(('fixture-systemone', SYSTEMONE_MODEL, 'fixture-1', 'synthetic_fixture'),
                         (metadata['provider'], metadata['model'], metadata['model_version'],
                          metadata['execution_mode']))
        self.assertEqual(BUNDLE_VERSION, metadata['bundle_version'])
        self.assertEqual('fixture_supplied', metadata['probabilities'])
        self.assertEqual(self.rendered['request_digest'], metadata['request_digest'])
        self.assertEqual(compute_content_digest(payload['composed']), metadata['output_digest'])
        # Read back, then replay with a clock that would fail and a backend call counter.
        self.assertEqual(saved, self.repo.read(self.actor, self.case, reference(saved)))
        self.assertEqual(1, len(self.backend.requests))

        def no_clock():
            raise AssertionError('a replay must not read the clock')

        self.assertEqual(saved, self.generate(clock=no_clock))
        self.assertEqual(1, len(self.backend.requests))
        self.assertEqual([saved], self.repo.workspace(self.actor, self.case)['probe_bundles'])
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['judgments'])

    def test_invalid_responses_write_nothing(self):
        dropped = {k: v for k, v in self.answers.items() if k != 'q1_identity_f0'}
        responses = (
            ('missing question', FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, dropped)),
            ('unknown option', FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL,
                                                dict(self.answers, q1_identity_f0={'choice': 'who',
                                                                                   'probabilities': {'who': 1.0}}))),
            ('probability above one', FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL,
                                                       dict(self.answers, q4_conditional_f0={'noul': 1.2}))),
            ('oversized response', ScriptedSystemOne({'answers': self.answers,
                                                      'model_version': 'x' * (70 * 1024)})),
        )
        for index, (name, backend) in enumerate(responses):
            with self.subTest(case=name):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    self.generate(key=f'probe-{index}', service=SystemOneService(backend))
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
                self.assertEqual(1, len(backend.requests))  # the backend was asked; the answer was not kept
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['probe_bundles'])
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['judgments'])

    def test_same_key_on_a_different_task_conflicts_without_a_second_call(self):
        saved = self.generate()
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        other = self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption', AT, NOW)
        self.assertNotEqual(reference(other), reference(self.task))
        self.assertCode('IDEMPOTENCY_CONFLICT', self.generate, task=other)
        self.assertEqual(1, len(self.backend.requests))
        self.assertEqual([saved], self.repo.workspace(self.actor, self.case)['probe_bundles'])

    def test_blocked_stale_and_other_actor_tasks_never_call_the_backend(self):
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        blocked = self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption',
                                         '2026-09-01T00:00:00Z', NOW)
        self.assertCode('BLOCKED_TASK', self.generate, task=blocked)
        mapping = self.seed['mapping']
        newer = make_record('MappingRevision', self.actor.tenant_id, self.case, mapping['record_id'], '2', NOW,
                            mapping['payload'])
        self.repo.register(self.actor, newer)
        self.assertCode('STALE_DEPENDENCY', self.generate)
        self.assertCode('ACCESS_DENIED', self.generate, actor=replace(self.actor, actor_id='other'))
        self.assertEqual([], self.backend.requests)
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['probe_bundles'])

    def test_a_render_refusal_is_a_result_with_no_call_and_no_write(self):
        task = derived_task(self.task, candidates=candidate_entities(9))
        stub = StubBundleRepository(task)
        result = self.service.generate(stub, self.actor, self.case, reference(self.task), 'probe-a', lambda: NOW)
        self.assertEqual({'status': 'insufficient', 'reason': 'TOO_MANY_CANDIDATES',
                          'bundle_version': BUNDLE_VERSION}, result)
        self.assertEqual([], self.backend.requests)
        self.assertEqual([], stub.saved)

    def test_backend_failure_disabled_and_busy_have_no_writes(self):
        failing = FailingSystemOne()
        with self.assertRaises(JudgmentUnavailable) as caught:
            self.generate(service=SystemOneService(failing))
        self.assertEqual('MODEL_UNAVAILABLE', str(caught.exception))
        self.assertNotIn('private backend detail', str(caught.exception))
        self.assertEqual(1, len(failing.requests))
        with self.assertRaises(JudgmentUnavailable) as caught:
            self.generate(key='probe-b', service=SystemOneService())
        self.assertEqual('MODEL_DISABLED', str(caught.exception))
        self.service.slots.acquire()
        try:
            with self.assertRaises(JudgmentUnavailable) as caught:
                self.generate()
            self.assertEqual('MODEL_BUSY', str(caught.exception))
        finally:
            self.service.slots.release()
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['probe_bundles'])

    def test_a_backend_judgment_unavailable_is_sanitized_to_model_unavailable(self):
        for index, code in enumerate(('synthetic-private-error-detail', 'MODEL_BUSY', 'MODEL_INVALID_RESPONSE')):
            with self.subTest(code=code):
                backend = DisclosingSystemOne(code)
                with self.assertRaises(JudgmentUnavailable) as caught:
                    self.generate(key=f'probe-private-{index}', service=SystemOneService(backend))
                # One safe code, the backend's own code and text never exposed: the
                # code above is the backend's choice, not a service failure code.
                self.assertEqual('MODEL_UNAVAILABLE', caught.exception.code)
                self.assertEqual('MODEL_UNAVAILABLE', str(caught.exception))
                self.assertNotIn('private', str(caught.exception))
                self.assertEqual(1, len(backend.requests))
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['probe_bundles'])
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['judgments'])

    def test_a_revoked_cited_source_denies_read_of_the_saved_bundle(self):
        saved = self.generate()
        revoked = replace(self.actor, source_policy_refs=frozenset())
        self.assertCode('ACCESS_DENIED', self.repo.read, revoked, self.case, reference(saved))
        self.assertCode('ACCESS_DENIED', self.repo.workspace, revoked, self.case)
        self.assertEqual([saved], self.repo.workspace(self.actor, self.case)['probe_bundles'])

    def test_record_validation_rejects_foreign_payloads(self):
        payload = self.generate()['payload']
        self.assertEqual('ProbeBundleArtifact',
                         validate_record(make_record('ProbeBundleArtifact', self.actor.tenant_id, self.case,
                                                     'probe:direct', '1', NOW, payload))['record_kind'])

        def rejected(code='INVALID_RECORD', **changes):
            candidate = json.loads(canonical_dumps(payload))
            candidate.update(changes)
            with self.assertRaises(ReviewError) as caught:
                make_record('ProbeBundleArtifact', self.actor.tenant_id, self.case, 'probe:x', '1', NOW, candidate)
            self.assertEqual(code, caught.exception.code)

        rejected(metadata=dict(payload['metadata'], output_digest='0' * 64))
        rejected(metadata=dict(payload['metadata'], probabilities=''))
        without_probabilities = dict(payload['metadata'])
        without_probabilities.pop('probabilities')
        rejected(metadata=without_probabilities)
        rejected(metadata=dict(payload['metadata'], execution_mode='live'))
        rejected(answers={})
        rejected(questions={k: v for k, v in payload['questions'].items() if k != 'q1_identity_f0'})
        rejected(review_state='accepted')
        # An h0.v2 payload that declares itself real needs a signed permission_ref, and
        # a synthetic one may not cite a permission at all.
        rejected(code='PERMISSION_UNKNOWN', synthetic=False)
        rejected(code='PERMISSION_UNKNOWN', synthetic=False, permission_ref='perm:never-signed')
        rejected(synthetic=True, permission_ref='perm:never-signed')
        # The pair is declared, never defaulted: a v2 payload that omits either key is
        # refused rather than read as synthetic.
        for key in ('synthetic', 'permission_ref'):
            without = {k: v for k, v in payload.items() if k != key}
            with self.assertRaises(ReviewError) as caught:
                make_record('ProbeBundleArtifact', self.actor.tenant_id, self.case, 'probe:no-pair', '1', NOW, without)
            self.assertEqual('INVALID_RECORD', caught.exception.code)
        # The v2 fixture rule applies to the bundle exactly as to the single judgment:
        # a synthetic fixture is synthetic content, so it cannot declare itself real
        # even where the registry holds the identifier it cites — while live inference
        # may be real.
        registry = frozenset({'perm:bundle-signed'})
        real_pair = {'synthetic': False, 'permission_ref': 'perm:bundle-signed'}
        for mode, refused in (('synthetic_fixture', True), ('live_inference', False)):
            candidate = dict(payload, metadata=dict(payload['metadata'], execution_mode=mode), **real_pair)
            if refused:
                with self.assertRaises(ReviewError) as caught:
                    make_record('ProbeBundleArtifact', self.actor.tenant_id, self.case, 'probe:real-fixture',
                                '1', NOW, candidate, permissions=registry)
                self.assertEqual('INVALID_RECORD', caught.exception.code)
            else:
                self.assertEqual('ProbeBundleArtifact', validate_record(make_record(
                    'ProbeBundleArtifact', self.actor.tenant_id, self.case, 'probe:real-live', '1', NOW,
                    candidate, permissions=registry), registry)['record_kind'])
        rejected(composed=dict(payload['composed'], label='approved'))
        # The composition result is closed and its rule is a table row: an invented key
        # cannot ride into `output_digest`, and an unknown row cannot read as "not
        # reused" while claiming to be a composition result. The digest is recomputed
        # over the tampered composition, so only the closed key set and the rule check
        # stand between these payloads and acceptance.
        invented = dict(payload['composed'], invented_note='anything')
        rejected(composed=invented, metadata=dict(payload['metadata'], output_digest=compute_content_digest(invented)))
        invented_rule = dict(payload['composed'], fired_rule='invented_row: not one of the table rows')
        rejected(composed=invented_rule,
                 metadata=dict(payload['metadata'], output_digest=compute_content_digest(invented_rule)))
        rejected(task_ref=dict(payload['task_ref'], record_kind='JudgmentArtifact'))
        rejected(extra='field')
        # The inherited dependency, when recorded, is a probe-bundle reference, and only a
        # reused label carries one: a provenance-free reuse is not a valid record.
        rejected(composed=dict(payload['composed'], lineage_ref=payload['task_ref']))
        rejected(composed=dict(payload['composed'], lineage_ref={
            'record_kind': 'ProbeBundleArtifact', 'record_id': 'probe:other',
            'revision_id': '1', 'content_digest': '0' * 64}))


class LineagePriorTests(BundleTestCase):
    """S2 lineage resolution: a repeated source's earlier bundle supplies the label.

    `compose` reads the label; `ReviewService.bundle_lineage_prior` resolves it, with the
    artifact it came from, from saved artifacts on other tasks for the same assumption
    whose context shares a lineage with this task's context and whose information cutoff
    is at or before this task's. The cases the reviews named: an existing prior, an
    absent prior, a prior the actor cannot read, a prior at a later cutoff, and a mix of
    earlier priors where the most recent one at or before the cutoff must win.
    """

    MID = '2026-10-05T12:00:00Z'
    CURRENT = '2026-10-07T00:00:00Z'
    FUTURE = '2026-10-08T00:00:00Z'

    def generate(self, task, atomic, key, *, actor=None, clock=None):
        rendered = render_bundle(task, SYSTEMONE_MODEL)
        backend = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, answers_for(rendered, atomic))
        saved = SystemOneService(backend).generate(self.repo, actor or self.actor, self.case,
                                                   reference(task), key, clock or (lambda: NOW))
        return saved, backend

    def task_at(self, cutoff, **kwargs):
        """A second task for the same assumption at another information cutoff."""
        snapshot = self.repo.build_snapshot(self.actor, self.case, cutoff, cutoff)
        return self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption',
                                      cutoff, cutoff, **kwargs)

    def assertDenied(self, ref, actor=None):
        with self.assertRaises(ReviewError) as caught:
            self.repo.read(actor or self.actor, self.case, ref)
        self.assertEqual('ACCESS_DENIED', caught.exception.code)

    def test_a_lineage_hit_without_a_qualifying_prior_abstains(self):
        self.assertIsNone(self.repo.bundle_lineage_prior(self.actor, self.case, reference(self.task)))
        saved, backend = self.generate(self.task, dict(BASE, q5=0.8), 'probe-a')
        composed = saved['payload']['composed']
        self.assertEqual('yes', composed['atomic']['q5'])
        self.assertEqual(('insufficient', 'lineage_reuse', 'LINEAGE_NO_PRIOR', ESCALATION),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['reason'],
                          composed['escalation']))
        self.assertEqual(1, len(backend.requests))
        self.assertEqual([saved], self.repo.workspace(self.actor, self.case)['probe_bundles'])

    def test_a_repeated_source_reuses_the_earlier_bundle_label(self):
        # The earlier bundle composes its own label: its answers report no repetition.
        prior, _ = self.generate(self.task, dict(BASE, q2='commercial_operation'), 'probe-prior')
        self.assertEqual(('supports', 'availability_confirmed'),
                         (prior['payload']['composed']['label'],
                          prior['payload']['composed']['fired_rule'].split(':')[0]))
        self.assertNotIn('lineage_ref', prior['payload']['composed'])
        # A second task for the same assumption at a later cutoff covers the same
        # source, and its answers report the repetition (Q5 = yes).
        other = self.task_at(LATER)
        self.assertNotEqual(reference(other), reference(self.task))
        self.assertEqual({'label': 'supports', 'ref': reference(prior)},
                         self.repo.bundle_lineage_prior(self.actor, self.case, reference(other)))
        reused, backend = self.generate(other, dict(BASE, q5=0.8), 'probe-b', clock=lambda: LATER)
        composed = reused['payload']['composed']
        self.assertEqual('yes', composed['atomic']['q5'])
        self.assertEqual(('supports', 'lineage_reuse', None, 'none', reference(prior)),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['reason'],
                          composed['escalation'], composed['lineage_ref']))
        self.assertEqual(1, len(backend.requests))
        # The inherited dependency is stored, so the read check can follow it and the
        # output digest still covers exactly the composed result.
        self.assertEqual(reused, self.repo.read(self.actor, self.case, reference(reused)))
        self.assertEqual(compute_content_digest(composed), reused['payload']['metadata']['output_digest'])

    def test_a_later_cutoff_prior_cannot_supply_the_label(self):
        # The second review's reproduction: a `supports` bundle saved at a later cutoff,
        # then a bundle for an earlier-cutoff task whose answers report the repeat. Later
        # evidence cannot decide an earlier task, so the row abstains.
        later = self.task_at(LATER)
        prior, _ = self.generate(later, dict(BASE, q2='commercial_operation'), 'probe-later', clock=lambda: LATER)
        self.assertEqual('supports', prior['payload']['composed']['label'])
        self.assertIsNone(self.repo.bundle_lineage_prior(self.actor, self.case, reference(self.task)))
        saved, backend = self.generate(self.task, dict(BASE, q5=0.8), 'probe-earlier')
        composed = saved['payload']['composed']
        self.assertEqual('yes', composed['atomic']['q5'])
        self.assertEqual(('insufficient', 'lineage_reuse', 'LINEAGE_NO_PRIOR', ESCALATION, None),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['reason'],
                          composed['escalation'], composed.get('lineage_ref')))
        self.assertEqual(1, len(backend.requests))

    def test_the_latest_earlier_cutoff_wins_and_later_evidence_is_excluded(self):
        # Three bundles for the same assumption and the same repeated source, so only the
        # cutoff rule separates them: `challenges` at NOW, `supports` at MID and
        # `challenges` at FUTURE, the last one recorded last and newest by cutoff.
        current, mid, future = self.task_at(self.CURRENT), self.task_at(self.MID), self.task_at(self.FUTURE)
        early_bundle, _ = self.generate(self.task, S2_BASE, 'probe-early')
        mid_bundle, _ = self.generate(mid, dict(BASE, q2='commercial_operation'), 'probe-mid', clock=lambda: self.MID)
        future_bundle, _ = self.generate(future, S2_BASE, 'probe-future', clock=lambda: self.FUTURE)
        self.assertEqual(['challenges', 'supports', 'challenges'],
                         [bundle['payload']['composed']['label'] for bundle in (early_bundle, mid_bundle, future_bundle)])
        self.assertLess(early_bundle['recorded_at'], future_bundle['recorded_at'])
        # The most recent earlier evidence wins: the mid bundle, not the later-cutoff or
        # the most recently recorded one.
        self.assertEqual({'label': 'supports', 'ref': reference(mid_bundle)},
                         self.repo.bundle_lineage_prior(self.actor, self.case, reference(current)))
        saved, backend = self.generate(current, dict(BASE, q5=0.8), 'probe-current', clock=lambda: self.CURRENT)
        composed = saved['payload']['composed']
        self.assertEqual(('supports', 'lineage_reuse', reference(mid_bundle)),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['lineage_ref']))
        self.assertEqual(1, len(backend.requests))

    def restricted_source_tasks(self):
        """A prior whose label rests on evidence only one policy may read.

        The fixture of the review rounds: a second source under ``synthetic-restricted``
        is cited by task A alone, so the prior bundle saved on task A is readable only
        with that policy. Task B, at a later cutoff for the same assumption, repeats the
        public lineage; it is compiled by the narrow actor. Returns ``(full, prior,
        task_b)``: the actor holding both policies, task A's ``supports`` bundle and the
        later task.
        """
        full = replace(self.actor, source_policy_refs=frozenset({'synthetic-public', 'synthetic-restricted'}))
        text = ('Fictional addendum — not a real plant report.\n'
                'A second fictional bulletin repeats the unit A testing claim.\n')
        quote = 'A second fictional bulletin repeats the unit A testing claim.'
        source = make_record('SourceVersion', self.actor.tenant_id, self.case, 'fictional-bulletin', '1', NOW, {
            'synthetic': True, 'permission_ref': None,
            'source_id': 'fictional-bulletin', 'source_version': '1',
            'source_byte_digest': hashlib.sha256(text.encode()).hexdigest(), 'original_text': text,
            'lineage_id': 'fictional-lineage', 'publisher': 'Fictional system operator',
            'published_at': '2026-10-02', 'known_at': NOW, 'access_policy_ref': 'synthetic-restricted',
            'availability_basis': {'basis_kind': 'attested', 'basis_ref': 'synthetic fixture', 'note': 'Labeled local fixture'}, 'unknown_reason': None, 'copied_from': None})
        self.repo.register(full, source, source_bytes=text.encode())
        start = text.index(quote)
        passage = make_record('Passage', self.actor.tenant_id, self.case, 'passage:fictional-bulletin', '1', NOW, {
            'synthetic': True, 'permission_ref': None,
            'source_ref': reference(source), 'source_id': 'fictional-bulletin', 'source_version': '1',
            'source_byte_digest': source['payload']['source_byte_digest'], 'start': start, 'end': start + len(quote),
            'quote': quote, 'quote_digest': hashlib.sha256(quote.encode()).hexdigest()})
        self.repo.register(full, passage)

        # Task A, compiled with the restricted policy in scope, covers both sources.
        snapshot = self.repo.build_snapshot(full, self.case, NOW, NOW)
        task_a = self.repo.compile_task(full, self.case, reference(snapshot), 'capacity-assumption', NOW, NOW)
        self.assertEqual(2, len(task_a['payload']['context']))
        prior, _ = self.generate(task_a, dict(BASE, q2='commercial_operation'), 'probe-prior', actor=full)
        self.assertEqual('supports', prior['payload']['composed']['label'])

        # Task B, compiled without the restricted policy, is a different task for the
        # same assumption; the prior is the only qualifying bundle and it is unreadable.
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        task_b = self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption', LATER, LATER)
        self.assertEqual(1, len(task_b['payload']['context']))
        self.assertEqual(['fictional-lineage'], [group['lineage_id'] for group in task_b['payload']['lineage_groups']])
        return full, prior, task_b

    def test_an_inaccessible_prior_is_absent_not_an_error(self):
        full, prior, task_b = self.restricted_source_tasks()
        self.assertIsNone(self.repo.bundle_lineage_prior(self.actor, self.case, reference(task_b)))
        abstained, _ = self.generate(task_b, dict(BASE, q5=0.8), 'probe-b', clock=lambda: LATER)
        self.assertEqual(('insufficient', 'LINEAGE_NO_PRIOR'),
                         (abstained['payload']['composed']['label'], abstained['payload']['composed']['reason']))

        # The same task and answers with the restricted policy in scope reuse the
        # label: the difference is access, not the qualification rule.
        self.assertEqual({'label': 'supports', 'ref': reference(prior)},
                         self.repo.bundle_lineage_prior(full, self.case, reference(task_b)))
        reused, _ = self.generate(task_b, dict(BASE, q5=0.8), 'probe-c', actor=full, clock=lambda: LATER)
        composed = reused['payload']['composed']
        self.assertEqual(('supports', 'lineage_reuse', reference(prior)),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['lineage_ref']))
        # Revocation follows the inherited dependency: the reused label rests on the
        # prior's restricted source, so the narrow actor is denied the derived read
        # exactly as it is denied the prior, and the projection drops both.
        self.assertEqual(reused, self.repo.read(full, self.case, reference(reused)))
        self.assertDenied(reference(reused))
        self.assertDenied(reference(prior))
        # The abstaining bundle rests on the readable task alone and stays projected.
        def projected(actor):
            return {canonical_dumps(reference(record))
                    for record in self.repo.workspace(actor, self.case)['probe_bundles']}

        self.assertEqual({canonical_dumps(reference(abstained))}, projected(self.actor))
        self.assertEqual({canonical_dumps(reference(record)) for record in (prior, abstained, reused)},
                         projected(full))

    def test_a_revocation_during_generation_denies_the_inherited_save(self):
        # The third review's reproduction at the service level: the qualifying prior is
        # resolved while the restricted policy is in scope, the policy is gone by the
        # time the completed artifact reaches `save_bundle`, and the save must refuse
        # rather than return the reused label. `RevokingBundleRepository` hands the save
        # the narrowed actor, as `PersistentRepository.execute` does after a membership
        # change, so the denial is not a read-time trick: nothing is written and the
        # creation response carries the denial, never the inherited result.
        full, prior, task_b = self.restricted_source_tasks()
        rendered = render_bundle(task_b, SYSTEMONE_MODEL)
        backend = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, answers_for(rendered, dict(BASE, q5=0.8)))
        service = SystemOneService(backend)
        with self.assertRaises(ReviewError) as caught:
            service.generate(RevokingBundleRepository(self.repo, self.actor), full, self.case,
                             reference(task_b), 'probe-revoked', lambda: LATER)
        self.assertEqual('ACCESS_DENIED', caught.exception.code)
        self.assertNotIn('supports', str(caught.exception))
        self.assertEqual(1, len(backend.requests))  # the backend ran; its answer was not kept
        # No artifact was written: under the full policy the projection still holds the
        # prior alone, so the denied save left nothing behind.
        self.assertEqual([prior], self.repo.workspace(full, self.case)['probe_bundles'])

    def test_a_recompile_of_the_same_task_is_not_its_own_prior(self):
        # The interim review's minor case A3: a recompile of identical content is a new
        # revision of the same logical task, not a different task, so the task's own
        # earlier bundle cannot supply an "earlier source" label back to it.
        prior, _ = self.generate(self.task, dict(BASE, q2='commercial_operation'), 'probe-prior')
        self.assertEqual('supports', prior['payload']['composed']['label'])
        recompiled = self.repo.compile_task(self.actor, self.case, self.task['payload']['snapshot_ref'],
                                            'capacity-assumption', NOW, LATER)
        self.assertEqual(self.task['record_id'], recompiled['record_id'])
        self.assertNotEqual(reference(self.task), reference(recompiled))
        self.assertIsNone(self.repo.bundle_lineage_prior(self.actor, self.case, reference(recompiled)))
        saved, backend = self.generate(recompiled, dict(BASE, q5=0.8), 'probe-self', clock=lambda: LATER)
        composed = saved['payload']['composed']
        self.assertEqual(('insufficient', 'lineage_reuse', 'LINEAGE_NO_PRIOR', None),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['reason'],
                          composed.get('lineage_ref')))
        self.assertEqual(1, len(backend.requests))


class ProbeBundleViewContractTests(BundleTestCase):
    """A saved probe bundle must reach the view through the key the view reads.

    Designated review 2, finding 1: the repository projected saved artifacts under
    ``bundles`` while `src/workspace/app.js` reads ``state.probe_bundles``, so the panel
    showed "No probe bundle is saved." after a refresh although the record existed (the
    POST response is discarded and the projection refreshed instead). Both sides are
    read here as source — the consumer from the view script, the producer from the
    repository plus the route that adds the two availability flags — so a rename on
    either side fails here rather than silently emptying the panel again.
    """

    def view_state_keys(self):
        """The ``state.<key>`` names the view reads out of the workspace response."""
        script = (REPO_ROOT / 'src' / 'workspace' / 'app.js').read_text(encoding='utf-8')
        return set(re.findall(r'state\??\.([a-z_]+)', script))

    def save(self, key='probe-view'):
        rendered = render_bundle(self.task, SYSTEMONE_MODEL)
        backend = FixtureSystemOne('fixture-systemone', SYSTEMONE_MODEL, answers_for(rendered, S2_BASE))
        return SystemOneService(backend).generate(self.repo, self.actor, self.case,
                                                  reference(self.task), key, lambda: NOW)

    def test_every_key_the_view_reads_is_one_the_workspace_response_carries(self):
        carried = set(self.repo.workspace(self.actor, self.case))
        route = (REPO_ROOT / 'src' / 'api' / '__init__.py').read_text(encoding='utf-8')
        carried |= set(re.findall(r"result\['([a-z_]+)'\] =", route))
        consumed = self.view_state_keys()
        self.assertIn('probe_bundles', consumed)  # the view still reads the bundle key
        self.assertEqual(set(), consumed - carried,
                         f'the view reads {sorted(consumed - carried)}, which the response cannot carry')

    def test_a_saved_bundle_is_reachable_through_the_key_the_view_reads(self):
        saved = self.save()
        projection = self.repo.workspace(self.actor, self.case)
        reachable = {key for key, value in projection.items() if isinstance(value, list) and saved in value}
        self.assertEqual({'probe_bundles'}, reachable)
        self.assertLessEqual(reachable, self.view_state_keys())


if __name__ == '__main__':
    unittest.main()
