"""S4 cutoff pairing: the derived view, its typed refusals and its read-only property.

Offline, synthetic and stdlib-only. The tasks are compiled through the real repository
from the fictional seed in `src/demo`, the paired artifacts are saved through the real
`SystemOneService` and the labelled `FixtureSystemOne` test double, and every assertion
reads either the derived view or the reference store's own tables. Nothing here calls a
model, transport, credential or network, and the no-write cases compare every store
table before and after the call.
"""
import hashlib
import json
import re
import unittest
from dataclasses import replace
from pathlib import Path

from src.contracts.jsonutil import canonical_dumps, compute_content_digest
from src.demo import AT, seed
from src.judgment.systemone import FixtureSystemOne, SystemOneService
from src.review import InMemoryRepository, ReviewError, make_record, reference
from src.review.pairing import (PAIR_ASSUMPTION_MISMATCH, PAIR_CUTOFF_ORDER, PAIR_MESSAGES,
                                PAIR_NOT_A_BUNDLE, PAIR_NO_ATOMIC_ANSWERS, PAIR_SNAPSHOT_MISMATCH,
                                QUESTION_IDS, pair)
from tests.test_probe_bundle import BASE, MODEL, answers_for, render_bundle

#: The view script the cutoff pair panel lives in; the contract checks read it as source.
VIEW_SCRIPT = Path(__file__).resolve().parents[1] / 'src' / 'workspace' / 'app.js'
#: The module that owns the route, the lexicon and the view the panel renders.
PAIRING_MODULE = Path(__file__).resolve().parents[1] / 'src' / 'review' / 'pairing.py'

#: The S1/S2 offline suite's cutoff; the pair rows move around it.
NOW = '2026-10-05T02:00:00Z'
#: A second source known between the two task cutoffs and a task after it.
KNOWN_LATER = '2026-10-06T00:00:00Z'
LATER = '2026-10-07T00:00:00Z'
#: The reference store's tables; a pair that wrote anything would move one of them.
TABLES = ('records', 'latest', 'cases', 'heads', 'outlooks', 'history', 'receipts', 'stale')

#: A canonical input that composes a real label (`challenges`, rule `outage_or_later`).
CHALLENGES = dict(BASE, q2='forced_outage')
#: The same label, with two atomic answers moved: the pairing is about the answers.
CHALLENGES_MOVED = dict(CHALLENGES, q3='after', q6=0.9)

SECOND_SOURCE = ('Fictional addendum — not a real plant report.\n'
                 'Unit A returns from its fictional outage on 5 October.\n')


class ReadPort:
    """A facade exposing only the public ``read`` port, over prepared records.

    `PersistentRepository` publishes repository methods through an explicit allow-list
    that does not name pairing, so the derived view must reach its inputs through
    ``read`` alone; any other attribute this facade does not have. A prepared record
    stands in for one a hand-built or foreign payload could leave in a store, which the
    service itself never writes.
    """

    def __init__(self, service):
        self.service = service
        self.prepared = {}

    def prepare(self, record):
        self.prepared[(record['record_kind'], record['record_id'])] = record

    def read(self, actor, case, ref):
        key = (ref['record_kind'], ref['record_id'])
        return self.prepared.get(key) or self.service.read(actor, case, ref)


class PairingTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository()
        self.seed = seed(self.repo)
        self.actor = self.seed['actor']
        self.case = next(iter(self.actor.accessible_cases))
        self.snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        self.task = self.compiled(NOW, NOW)

    def compiled(self, info, at, *, assumption='capacity-assumption', snapshot=None):
        return self.repo.compile_task(self.actor, self.case, reference(snapshot or self.snapshot),
                                      assumption, info, at)

    def saved(self, task, atomic, key):
        """One probe bundle for `task`, saved through the service and the fixture backend."""
        rendered = render_bundle(task, MODEL)
        backend = FixtureSystemOne(MODEL, MODEL, answers_for(rendered, atomic))
        return SystemOneService(backend).generate(self.repo, self.actor, self.case, reference(task),
                                                  key, lambda: task['recorded_at'])

    def add_source(self, ident, text, known, at=NOW):
        """A second fictional source and its passage, as `H0Case.add_source` writes them."""
        data = text.encode('utf-8')
        source = make_record('SourceVersion', self.actor.tenant_id, self.case, ident, '1', at, {
            'synthetic': True, 'permission_ref': None,
            'source_id': ident, 'source_version': '1', 'source_byte_digest': hashlib.sha256(data).hexdigest(),
            'original_text': text, 'lineage_id': ident, 'publisher': 'fictional issuer',
            'published_at': '2026-10-01', 'known_at': known, 'access_policy_ref': 'synthetic-public',
            'availability_basis': {'basis_kind': 'attested', 'basis_ref': 'synthetic receipt', 'note': ''}, 'unknown_reason': None, 'copied_from': None})
        self.repo.register(self.actor, source, source_bytes=data)
        quote = text.splitlines()[1]
        start = text.index(quote)
        passage = make_record('Passage', self.actor.tenant_id, self.case, 'passage:' + ident, '1', at, {
            'synthetic': True, 'permission_ref': None,
            'source_ref': reference(source), 'source_id': ident, 'source_version': '1',
            'source_byte_digest': source['payload']['source_byte_digest'], 'start': start, 'end': start + len(quote),
            'quote': quote, 'quote_digest': hashlib.sha256(quote.encode()).hexdigest()})
        self.repo.register(self.actor, passage)
        return source, passage

    def seed_second_assumption(self):
        """A second assumption over the same mapping, so a pair can differ by assumption."""
        mapping = self.seed['mapping']['payload']
        return self.repo.seed_assumption(self.actor, 'other-assumption', '1', AT, {
            'case_id': self.case, 'entity': mapping['entities'][0], 'proposition': 'Second fictional position',
            'value': {'value': '50.00', 'quantity_kind': 'assumed_available_capacity', 'unit': 'MW'},
            'valid_period': mapping['valid_period'], 'representation_id': mapping['representation_id'],
            'input_field': mapping['input_field'], 'mapping_ref': reference(self.seed['mapping'])},
            'Synthetic second initial position')

    def state(self):
        """Every reference-store table, canonicalised: the no-write proof."""
        def freeze(table):
            return sorted(json.dumps([list(key), value], sort_keys=True) for key, value in table.items())
        return {name: freeze(getattr(self.repo, '_' + name)) for name in TABLES}

    def pair(self, before_ref, after_ref, *, repository=None, actor=None):
        return pair(repository or self.repo, actor or self.actor, self.case, before_ref, after_ref)

    def assertRefused(self, code, before_ref, after_ref, **kwargs):
        before = self.state()
        with self.assertRaises(ReviewError) as caught:
            self.pair(before_ref, after_ref, **kwargs)
        self.assertEqual(code, caught.exception.code)
        self.assertEqual(before, self.state())  # a refusal writes nothing
        return caught.exception


class PairViewTests(PairingTestCase):
    def setUp(self):
        super().setUp()
        # The later source is known after the first task's cutoff and before the second
        # task's, so only the later task carries its passage.
        self.source, self.passage = self.add_source('fictional-return', SECOND_SOURCE, KNOWN_LATER)
        self.late = self.compiled(LATER, LATER)
        self.assertEqual([1, 2], [len(self.task['payload']['context']), len(self.late['payload']['context'])])
        self.before_bundle = self.saved(self.task, CHALLENGES, 'probe-before')
        self.after_bundle = self.saved(self.late, CHALLENGES_MOVED, 'probe-after')

    def test_changed_lists_the_differing_questions_and_new_passages_the_later_passage(self):
        before = self.state()
        view = self.pair(reference(self.before_bundle), reference(self.after_bundle))
        self.assertEqual({'before', 'after', 'label_before', 'label_after', 'changed', 'new_passages'}, set(view))
        self.assertEqual(reference(self.before_bundle), view['before'])
        self.assertEqual(reference(self.after_bundle), view['after'])
        self.assertEqual(['challenges', 'challenges'], [view['label_before'], view['label_after']])
        self.assertEqual('outage_or_later',
                         self.before_bundle['payload']['composed']['fired_rule'].split(':')[0])
        self.assertEqual(['q3_time', 'q6_observation'], view['changed'])
        self.assertEqual([reference(self.passage)], view['new_passages'])
        self.assertEqual(before, self.state())  # the derived view writes nothing

    def test_equal_atomic_answers_list_no_changed_question_but_the_new_passage(self):
        twin = self.saved(self.late, CHALLENGES, 'probe-twin')
        view = self.pair(reference(self.before_bundle), reference(twin))
        self.assertEqual([], view['changed'])
        self.assertEqual([reference(self.passage)], view['new_passages'])
        self.assertEqual(['challenges', 'challenges'], [view['label_before'], view['label_after']])

    def test_the_view_reads_only_through_the_public_read_port(self):
        port = ReadPort(self.repo)
        view = self.pair(reference(self.before_bundle), reference(self.after_bundle), repository=port)
        self.assertEqual(['q3_time', 'q6_observation'], view['changed'])
        self.assertEqual([reference(self.passage)], view['new_passages'])

    def test_a_revoked_source_denies_the_pair_and_writes_nothing(self):
        narrow = replace(self.actor, source_policy_refs=frozenset())
        self.assertRefused('ACCESS_DENIED', reference(self.before_bundle), reference(self.after_bundle), actor=narrow)

    def test_saved_history_pairs_even_when_a_later_mapping_makes_the_tasks_stale(self):
        # The pair is derived from the saved artifacts, not from the live head state: a
        # mapping revision after both cutoffs stales the drafts and leaves the pair.
        newer = make_record('MappingRevision', self.actor.tenant_id, self.case, self.seed['mapping']['record_id'],
                            '2', LATER, self.seed['mapping']['payload'])
        self.repo.register(self.actor, newer)
        for task in (self.task, self.late):
            self.assertEqual('stale', self.repo.draft_status(self.actor, self.case, reference(task))['status'])
        before = self.state()
        view = self.pair(reference(self.before_bundle), reference(self.after_bundle))
        self.assertEqual(['q3_time', 'q6_observation'], view['changed'])
        self.assertEqual([reference(self.passage)], view['new_passages'])
        self.assertEqual(before, self.state())


class PairRefusalTests(PairingTestCase):
    def setUp(self):
        super().setUp()
        self.before_bundle = self.saved(self.task, CHALLENGES, 'probe-before')
        self.late = self.compiled(LATER, LATER)
        self.after_bundle = self.saved(self.late, CHALLENGES_MOVED, 'probe-after')

    def test_wrong_cutoff_order_is_refused_with_a_typed_code(self):
        # Swapped: the later task as `before` makes the later cutoff the earlier one.
        self.assertRefused(PAIR_CUTOFF_ORDER, reference(self.after_bundle), reference(self.before_bundle))
        # Equal cutoffs: a second bundle on the same task is not a later cutoff either.
        twin = self.saved(self.task, CHALLENGES, 'probe-twin')
        self.assertRefused(PAIR_CUTOFF_ORDER, reference(self.before_bundle), reference(twin))

    def test_a_different_assumption_is_refused_with_a_typed_code(self):
        self.seed_second_assumption()
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        other = self.compiled(NOW, NOW, assumption='other-assumption', snapshot=snapshot)
        other_bundle = self.saved(other, CHALLENGES, 'probe-other')
        self.assertRefused(PAIR_ASSUMPTION_MISMATCH, reference(self.before_bundle), reference(other_bundle))

    def test_a_different_snapshot_is_refused_with_a_typed_code(self):
        snapshot = self.repo.build_snapshot(self.actor, self.case, '2026-10-05T03:00:00Z', LATER)
        other = self.compiled(LATER, LATER, snapshot=snapshot)
        other_bundle = self.saved(other, CHALLENGES_MOVED, 'probe-other-snapshot')
        self.assertRefused(PAIR_SNAPSHOT_MISMATCH, reference(self.before_bundle), reference(other_bundle))

    def test_a_reference_that_is_not_a_bundle_is_refused_with_a_typed_code(self):
        self.assertRefused(PAIR_NOT_A_BUNDLE, reference(self.task), reference(self.before_bundle))

    def test_a_bundle_without_atomic_answers_is_refused_with_a_typed_code(self):
        payload = json.loads(json.dumps(self.before_bundle['payload']))
        payload['composed'] = dict(payload['composed'], atomic=None)
        payload['metadata'] = dict(payload['metadata'], output_digest=compute_content_digest(payload['composed']))
        broken = make_record('ProbeBundleArtifact', self.actor.tenant_id, self.case, 'probe:hand-built', '1',
                             NOW, payload)
        port = ReadPort(self.repo)
        port.prepare(broken)
        self.assertRefused(PAIR_NO_ATOMIC_ANSWERS, reference(broken), reference(self.before_bundle),
                           repository=port)


class PairViewContractTests(PairingTestCase):
    """The cutoff pair panel in `src/workspace/app.js` against the module it renders.

    The UI-1 round-1 review found the probe panel reading a key the workspace response
    never carried, so the pair panel's own inputs are read here as source on both sides:
    the keys the view reads out of the response are the keys ``pair()`` returns, the
    refusal lexicon is :data:`PAIR_MESSAGES` itself, the request names the route
    `src/review/pairing.py` registers, and the embedded UI contract fixtures carry the
    frozen view with question ids and passage references the records themselves hold. The
    panel layout, the one-task state and the rendered refusal text are the browser
    check's (UI-5); these are the offline half. The setUp is the view tests' own case, so
    `moved.view` must equal the view derived here — the fixture is that output, embedded.
    """

    def setUp(self):
        super().setUp()
        # The same synthetic case the view tests pair: the second source is known between
        # the two cutoffs, so only the later task carries its passage.
        self.source, self.passage = self.add_source('fictional-return', SECOND_SOURCE, KNOWN_LATER)
        self.late = self.compiled(LATER, LATER)
        self.before_bundle = self.saved(self.task, CHALLENGES, 'probe-before')
        self.after_bundle = self.saved(self.late, CHALLENGES_MOVED, 'probe-after')
        self.view = self.pair(reference(self.before_bundle), reference(self.after_bundle))

    def script(self):
        return VIEW_SCRIPT.read_text(encoding='utf-8')

    def fixtures(self):
        literal = re.search(r'const PAIR_FIXTURE_JSON = String\.raw`([^`]*)`;', self.script())
        self.assertIsNotNone(literal, 'the pair fixtures are no longer a raw template literal')
        return json.loads(literal.group(1))['fixtures']

    def test_the_panel_reads_exactly_the_frozen_view_keys(self):
        self.assertEqual(set(self.view), set(re.findall(r'\bview\.([a-z_]+)', self.script())))

    def test_the_refusal_lexicon_is_the_pairing_modules_own(self):
        block = re.search(r'const PAIR_MESSAGES = \{(.*?)\};', self.script(), re.S).group(1)
        self.assertEqual(PAIR_MESSAGES, dict(re.findall(r"([A-Z_]+): '([^']*)'", block)))

    def test_the_request_is_the_route_the_pairing_module_registers(self):
        module = PAIRING_MODULE.read_text(encoding='utf-8')
        self.assertIn("prefix + '/probe-bundles/pair'", module)
        signature = re.search(r'def pair_bundles\(([^)]*)\)', module).group(1)
        names = [part.split('=')[0].split(':')[0].strip() for part in signature.split(',')]
        self.assertEqual(['case', 'before', 'after', 'a'], names)
        query = re.search(r'`(/probe-bundles/pair\?[^`]*)`', self.script()).group(1)
        self.assertIn('before=${', query)
        self.assertIn('after=${', query)

    def test_the_embedded_fixtures_carry_the_frozen_view_and_the_records_own_values(self):
        fixtures = self.fixtures()
        self.assertEqual(['moved', 'refused', 'single'], sorted(fixtures))
        moved = fixtures['moved']
        self.assertEqual(self.view, moved['view'])  # the same setUp, derived here and offline
        self.assertEqual(set(self.view), set(moved['view']))
        self.assertLessEqual(set(moved['view']['changed']), set(QUESTION_IDS.values()))
        tasks = {entry['record']['record_id']: entry['record'] for entry in moved['tasks']}
        bundles = {item['record_id']: item for item in moved['probe_bundles']}
        context = {side: {canonical_dumps(item['passage_ref'])
                          for item in tasks[bundles[moved['view'][side]['record_id']]['payload']
                                            ['task_ref']['record_id']]['payload']['context']}
                   for side in ('before', 'after')}
        for item in moved['view']['new_passages']:
            self.assertIn(canonical_dumps(item), context['after'])
            self.assertNotIn(canonical_dumps(item), context['before'])
        self.assertIn(fixtures['refused']['error']['code'], PAIR_MESSAGES)
        self.assertEqual(1, len(fixtures['single']['tasks']))
        self.assertEqual(1, len(fixtures['single']['probe_bundles']))
        # One task can never offer two candidates, so the compare control stays disabled.
        self.assertIn('pairOptions.length < 2', self.script())

    def test_each_choice_rechecks_the_compare_control(self):
        # Designated review 1's defect: neither bundle select had a change handler, so
        # after Compare disabled itself on two equal choices a corrected choice left it
        # disabled until another workspace action. Both selects must recheck at once.
        script = self.script()
        for side in ('pair-before', 'pair-after'):
            self.assertIn(f"$('{side}').onchange=controls", script)

    def test_the_compare_handler_clears_the_panel_only_once_it_has_an_answer(self):
        handler = re.search(r"\$\('pair-compare'\)\.onclick=\(\)=>run\(async\(\)=>\{(.*?)\n\}\);",
                            self.script(), re.S)
        self.assertIsNotNone(handler, 'the compare handler is no longer one wired function')
        body = handler.group(1)
        self.assertLess(body.index('await api(query)'), body.index('box.replaceChildren()'))

    def test_every_refusal_hint_fits_its_own_code(self):
        script = self.script()
        block = re.search(r'const PAIR_HINTS = \{(.*?)\};', script, re.S)
        self.assertIsNotNone(block, 'the refusal hints are no longer a literal map')
        hints = dict(re.findall(r"([A-Z_]+): '([^']*)'", block.group(1)))
        self.assertLessEqual(set(hints), set(PAIR_MESSAGES))
        # The two codes the panel can reach with its own choices keep fitting advice: the
        # cutoff-order hint says later, the snapshot hint says snapshot, not later.
        self.assertIn('later', hints['PAIR_CUTOFF_ORDER'])
        self.assertIn('snapshot', hints['PAIR_SNAPSHOT_MISMATCH'])

    def test_the_status_words_follow_the_candidates_not_the_probe_backend(self):
        # The pair route needs no backend, so a disconnected probe backend must not claim
        # a pair is impossible while Compare is enabled; it only gates requesting one.
        script = self.script()
        self.assertNotIn('no cutoff pair can be derived', script)
        self.assertIn('cannot be requested right now', script)
        self.assertIn('if (pairOptions.length > 1) {', script)

    def test_the_pair_banner_uses_the_pair_alert_class(self):
        self.assertIn("if (banner) node('p', banner, box).className = 'pair-alert'", self.script())

    def test_the_panel_reaches_no_markup_api(self):
        for name in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write'):
            self.assertNotIn(name, self.script())


if __name__ == '__main__':
    unittest.main()
