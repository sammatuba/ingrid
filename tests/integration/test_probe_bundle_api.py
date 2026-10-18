"""S2 probe-bundle API integration on the local emulators (Auth + Firestore).

Requires the auth and Firestore emulators, so it runs through `bash scripts/h1/test.sh`,
which starts them and executes this file with the pinned H1 venv. Every recorded answer
comes from the labelled fixture backend; nothing here contacts a model, transport or
network outside the two loopback emulators, and no case fact is invented.
"""
import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_h1 as h1
import test_probe_bundle as probes
import test_review_case as h0
from src.api import create_app
from src.judgment.systemone import FixtureSystemOne, SystemOneService
from src.review import reference
from src.review.records import json_copy
from src.review.storage import encode

MODEL = 'fixture-systemone'


class RevokingSystemOne:
    """The labelled fixture's answers, with the restricted policy dropped mid-call.

    ``decide`` runs between the prior's resolution and ``save_bundle``: revoking the
    membership store here is the window the designated review 2 named, and the store
    then supplies the narrowed actor to the save transaction. No transport, credential
    or network call exists in this object.
    """

    name, model, execution_mode = 'revoking-systemone', MODEL, 'synthetic_fixture'
    probabilities = 'fixture_supplied'

    def __init__(self, answers, member):
        self.answers, self.member, self.requests = json_copy(answers), member, []

    def decide(self, request):
        self.requests.append(json_copy(request))
        self.member.update({'source_policy_refs': ['synthetic-public']})
        return {'answers': json_copy({name: self.answers[name] for name in request['questions']
                                      if name in self.answers}),
                'model_version': 'fixture-1'}


class ProbeBundleAPI(unittest.TestCase):
    def setUp(self):
        # Reuse the H1 fixture (case, membership, auth token, mock clock); not the
        # inherited H0 test collection.
        self.f = h1.H1HTTP(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.task = self.f.task()
        self.rendered = probes.render_bundle(self.task, MODEL)
        self.answers = probes.answers_for(self.rendered, probes.S2_BASE)
        self.backend = FixtureSystemOne('fixture-systemone', MODEL, self.answers)
        self.client = TestClient(create_app(self.f.repo, self.f.identity, self.f.clock,
                                            bundle=SystemOneService(self.backend)))
        self.addCleanup(self.client.close)
        self.body = {'task_ref': reference(self.task), 'idempotency_key': 'probe-a'}

    def post(self, suffix, body):
        return self.client.post(self.f.url + suffix, json=body, headers=self.f.headers)

    def saved_bundle(self, task, atomic, key):
        """Save one probe bundle for `task` through the API, from the labelled fixture."""
        rendered = probes.render_bundle(task, MODEL)
        backend = FixtureSystemOne('fixture-systemone', MODEL, probes.answers_for(rendered, atomic))
        client = TestClient(create_app(self.f.repo, self.f.identity, self.f.clock,
                                       bundle=SystemOneService(backend)))
        self.addCleanup(client.close)
        response = client.post(self.f.url + '/probe-bundles',
                               json={'task_ref': reference(task), 'idempotency_key': key}, headers=self.f.headers)
        self.assertEqual(200, response.status_code, response.text)
        return response.json(), backend

    def test_bundle_saved_replayed_read_back_after_restart_and_projected(self):
        saved = self.post('/probe-bundles', self.body)
        self.assertEqual(200, saved.status_code, saved.text)
        record = saved.json()
        self.assertEqual('ProbeBundleArtifact', record['record_kind'])
        self.assertEqual(reference(self.task), record['payload']['task_ref'])
        self.assertEqual('probe-a', record['payload']['idempotency_key'])
        self.assertEqual('proposed', record['payload']['review_state'])
        self.assertIs(True, record['payload']['synthetic'])
        self.assertEqual(self.answers, record['payload']['answers'])
        self.assertEqual('challenges', record['payload']['composed']['label'])
        self.assertEqual('outage_or_later', record['payload']['composed']['fired_rule'].split(':')[0])
        self.assertEqual(self.rendered['request_digest'], record['payload']['metadata']['request_digest'])
        self.assertEqual(1, len(self.backend.requests))

        workspace = self.client.get(self.f.url + '/workspace', headers=self.f.headers)
        self.assertEqual(200, workspace.status_code, workspace.text)
        self.assertIs(True, workspace.json()['bundle_available'])
        self.assertEqual([record], workspace.json()['probe_bundles'])

        # Restart: a new app over a new connection to the same store, with a fixture
        # backend that holds no answers, so any backend call on the replay would fail.
        fresh_backend = FixtureSystemOne('fixture-systemone', MODEL, {})
        restarted = TestClient(create_app(self.f.connection(), self.f.identity, self.f.clock,
                                          bundle=SystemOneService(fresh_backend)))
        self.addCleanup(restarted.close)
        readback = restarted.post(self.f.url + '/read', json={'ref': reference(record)}, headers=self.f.headers)
        self.assertEqual(200, readback.status_code, readback.text)
        self.assertEqual(record, readback.json())
        replay = restarted.post(self.f.url + '/probe-bundles', json=self.body, headers=self.f.headers)
        self.assertEqual(200, replay.status_code, replay.text)
        self.assertEqual(record, replay.json())
        self.assertEqual([], fresh_backend.requests)
        projection = restarted.get(self.f.url + '/workspace', headers=self.f.headers)
        self.assertEqual([record], projection.json()['probe_bundles'])

    def test_conflict_blocked_task_and_missing_backend_stay_off_the_backend(self):
        saved = self.post('/probe-bundles', self.body)
        self.assertEqual(200, saved.status_code, saved.text)
        other = self.f.task(info=h0.TODAY)
        self.assertNotEqual(reference(other), reference(self.task))
        conflict = self.post('/probe-bundles', {'task_ref': reference(other), 'idempotency_key': 'probe-a'})
        self.assertEqual((409, {'code': 'IDEMPOTENCY_CONFLICT'}), (conflict.status_code, conflict.json()))
        self.assertEqual(1, len(self.backend.requests))
        blocked = self.f.task(info='2026-09-01T00:00:00Z')
        blocked_response = self.post('/probe-bundles', {'task_ref': reference(blocked), 'idempotency_key': 'probe-b'})
        self.assertEqual((422, {'code': 'BLOCKED_TASK'}), (blocked_response.status_code, blocked_response.json()))
        self.assertEqual(1, len(self.backend.requests))

        # The app built by H1HTTP.setUp has no bundle backend and no judgment provider.
        # A new key is MODEL_DISABLED; the saved key still replays without any backend,
        # because a replay is readable history rather than new model work.
        disabled = self.f.client.post(self.f.url + '/probe-bundles',
                                      json=dict(self.body, idempotency_key='probe-c'), headers=self.f.headers)
        self.assertEqual((503, {'code': 'MODEL_DISABLED'}), (disabled.status_code, disabled.json()))
        replay_without_backend = self.f.client.post(self.f.url + '/probe-bundles', json=self.body, headers=self.f.headers)
        self.assertEqual(200, replay_without_backend.status_code, replay_without_backend.text)
        self.assertEqual(saved.json(), replay_without_backend.json())
        # The same store, so the workspace still projects the saved artifact; the flag
        # reports that *this* app has no backend, not that the record is missing.
        default_workspace = self.f.client.get(self.f.url + '/workspace', headers=self.f.headers).json()
        self.assertIs(False, default_workspace['bundle_available'])
        self.assertIs(False, default_workspace['model_available'])
        self.assertEqual([saved.json()], default_workspace['probe_bundles'])
        self.assertEqual([saved.json()], self.f.repo.workspace(self.f.actor, self.f.case)['probe_bundles'])

    def test_backend_raised_judgment_unavailable_is_sanitized(self):
        backend = probes.DisclosingSystemOne('synthetic-private-error-detail')
        client = TestClient(create_app(self.f.repo, self.f.identity, self.f.clock,
                                       bundle=SystemOneService(backend)))
        self.addCleanup(client.close)
        response = client.post(self.f.url + '/probe-bundles', json=self.body, headers=self.f.headers)
        # One safe code, whatever the backend raised: its own code is not echoed.
        self.assertEqual((503, {'code': 'MODEL_UNAVAILABLE'}), (response.status_code, response.json()))
        self.assertEqual(1, len(backend.requests))
        self.assertEqual([], self.f.repo.workspace(self.f.actor, self.f.case)['probe_bundles'])

    def test_a_repeated_source_reuses_the_saved_label_through_the_api(self):
        # The earlier task's bundle composes its own label: its answers report no repeat.
        earlier = self.f.task(info=h0.SEED)
        self.assertNotEqual(reference(earlier), reference(self.task))
        prior, _ = self.saved_bundle(earlier, dict(probes.BASE, q2='commercial_operation'), 'probe-prior')
        self.assertEqual(('supports', 'availability_confirmed'),
                         (prior['payload']['composed']['label'],
                          prior['payload']['composed']['fired_rule'].split(':')[0]))

        # The seeded task, at a later cutoff for the same assumption, covers the same
        # source and its answers report the repetition (Q5 = yes): the earlier bundle's
        # label is reused, and the artifact records what it inherited the label from.
        reused, backend = self.saved_bundle(self.task, dict(probes.BASE, q5=0.8), 'probe-derived')
        composed = reused['payload']['composed']
        self.assertEqual(('supports', 'lineage_reuse', None, reference(prior)),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['reason'],
                          composed['lineage_ref']))
        self.assertEqual(1, len(backend.requests))

    def test_inherited_source_dependency_denies_read_after_revocation(self):
        # A second source under a restricted policy is cited only by the earlier task:
        # the later task selects the public passage alone, so its own context stays
        # readable once the restricted policy is revoked.
        self.f.add_source(ident='source-private', lineage='source-private', policy='synthetic-private')
        earlier = self.f.task(info=h0.SEED)
        later = self.f.task(info=h0.TODAY, passage_ids=['passage:source-a'])
        self.assertEqual([2, 1], [len(earlier['payload']['context']), len(later['payload']['context'])])
        self.assertEqual(['source-a'], [group['lineage_id'] for group in later['payload']['lineage_groups']])

        prior, _ = self.saved_bundle(earlier, dict(probes.BASE, q2='commercial_operation'), 'probe-prior')
        derived, _ = self.saved_bundle(later, dict(probes.BASE, q5=0.8), 'probe-derived')
        composed = derived['payload']['composed']
        self.assertEqual(('supports', 'lineage_reuse', reference(prior)),
                         (composed['label'], composed['fired_rule'].split(':')[0], composed['lineage_ref']))
        readable = self.client.post(self.f.url + '/read', json={'ref': reference(derived)}, headers=self.f.headers)
        self.assertEqual(200, readable.status_code, readable.text)

        # Revoking the restricted policy denies the derived artifact through its
        # inherited dependency, while its own task and the public records stay readable.
        member = self.f.repo.store.member_ref(self.f.actor.actor_id, self.f.actor.tenant_id, self.f.case)
        member.update({'source_policy_refs': ['synthetic-public']})
        for ref in (reference(derived), reference(prior)):
            denied = self.client.post(self.f.url + '/read', json={'ref': ref}, headers=self.f.headers)
            self.assertEqual((404, {'code': 'NOT_FOUND'}), (denied.status_code, denied.json()))
        for ref in (reference(later), reference(self.f.source), reference(self.f.passage)):
            allowed = self.client.post(self.f.url + '/read', json={'ref': ref}, headers=self.f.headers)
            self.assertEqual(200, allowed.status_code, allowed.text)

    def test_revocation_during_generation_denies_the_inherited_save(self):
        # The designated review's reproduction through the API: the prior is resolved
        # while the restricted policy is in scope, the policy is revoked while the
        # backend runs, and the completed artifact reaches `save_bundle` under the
        # narrowed membership. The save is denied, nothing is written, and the creation
        # response carries the denial rather than the inherited label.
        self.f.add_source(ident='source-private', lineage='source-private', policy='synthetic-private')
        earlier = self.f.task(info=h0.SEED)
        later = self.f.task(info=h0.TODAY, passage_ids=['passage:source-a'])
        prior, _ = self.saved_bundle(earlier, dict(probes.BASE, q2='commercial_operation'), 'probe-prior')
        self.assertEqual('supports', prior['payload']['composed']['label'])

        member = self.f.repo.store.member_ref(self.f.actor.actor_id, self.f.actor.tenant_id, self.f.case)
        answers = probes.answers_for(probes.render_bundle(later, MODEL), dict(probes.BASE, q5=0.8))
        backend = RevokingSystemOne(answers, member)
        client = TestClient(create_app(self.f.repo, self.f.identity, self.f.clock,
                                       bundle=SystemOneService(backend)))
        self.addCleanup(client.close)
        response = client.post(self.f.url + '/probe-bundles',
                               json={'task_ref': reference(later), 'idempotency_key': 'probe-derived'},
                               headers=self.f.headers)
        self.assertEqual((404, {'code': 'NOT_FOUND'}), (response.status_code, response.json()))
        self.assertNotIn('supports', response.text)
        self.assertEqual(1, len(backend.requests))  # the backend ran; its answer was not kept

        # Nothing was written: with the policy restored, the projection holds the prior
        # alone, so the denied save left no derived artifact behind.
        member.update({'source_policy_refs': ['synthetic-public', 'synthetic-private']})
        workspace = self.client.get(self.f.url + '/workspace', headers=self.f.headers)
        self.assertEqual(200, workspace.status_code, workspace.text)
        self.assertEqual([prior], workspace.json()['probe_bundles'])

    def test_invalid_response_writes_nothing_through_the_api(self):
        scripted = probes.ScriptedSystemOne({'answers': self.answers, 'model_version': 'x' * (70 * 1024)})
        client = TestClient(create_app(self.f.repo, self.f.identity, self.f.clock,
                                       bundle=SystemOneService(scripted)))
        self.addCleanup(client.close)
        response = client.post(self.f.url + '/probe-bundles', json=self.body, headers=self.f.headers)
        self.assertEqual((503, {'code': 'MODEL_INVALID_RESPONSE'}), (response.status_code, response.json()))
        self.assertEqual(1, len(scripted.requests))
        self.assertEqual([], self.f.repo.workspace(self.f.actor, self.f.case)['probe_bundles'])

    def test_revoked_cited_source_denies_read_and_projection(self):
        record = self.post('/probe-bundles', self.body).json()
        allowed = self.client.post(self.f.url + '/read', json={'ref': reference(record)}, headers=self.f.headers)
        self.assertEqual(200, allowed.status_code, allowed.text)
        member = self.f.repo.store.member_ref(self.f.actor.actor_id, self.f.actor.tenant_id, self.f.case)
        member.update({'source_policy_refs': []})
        denied = self.client.post(self.f.url + '/read', json={'ref': reference(record)}, headers=self.f.headers)
        self.assertEqual((404, {'code': 'NOT_FOUND'}), (denied.status_code, denied.json()))
        self.assertEqual(404, self.client.get(self.f.url + '/workspace', headers=self.f.headers).status_code)

    def test_pair_route_returns_the_diff_lists_the_new_passage_and_writes_nothing(self):
        # Two tasks for the seeded assumption sharing one snapshot at different cutoffs;
        # the later cutoff sees a second source the earlier one cannot carry.
        source, passage = self.f.add_source(ident='source-b', lineage='source-b',
                                            known='2026-10-03T00:00:00Z', at=h0.TODAY)
        snapshot = self.f.repo.build_snapshot(self.f.actor, self.f.case, h0.CUTOFF, h0.TODAY)
        early = self.f.repo.compile_task(self.f.actor, self.f.case, reference(snapshot), 'assumption-a',
                                         h0.CUTOFF, h0.TODAY)
        late = self.f.repo.compile_task(self.f.actor, self.f.case, reference(snapshot), 'assumption-a',
                                        h0.TODAY, h0.TODAY)
        self.assertEqual([1, 2], [len(early['payload']['context']), len(late['payload']['context'])])
        early_bundle, _ = self.saved_bundle(early, dict(probes.BASE, q2='forced_outage'), 'probe-early')
        late_bundle, _ = self.saved_bundle(late, dict(probes.BASE, q2='forced_outage', q3='after', q6=0.9),
                                           'probe-late')
        before = encode(self.f.repo.state())
        response = self.client.get(self.f.url + '/probe-bundles/pair', headers=self.f.headers, params={
            'before': json.dumps(reference(early_bundle)), 'after': json.dumps(reference(late_bundle))})
        self.assertEqual(200, response.status_code, response.text)
        view = response.json()
        self.assertEqual({'before', 'after', 'label_before', 'label_after', 'changed', 'new_passages'}, set(view))
        self.assertEqual(reference(early_bundle), view['before'])
        self.assertEqual(reference(late_bundle), view['after'])
        self.assertEqual(['challenges', 'challenges'], [view['label_before'], view['label_after']])
        self.assertEqual(['q3_time', 'q6_observation'], view['changed'])
        self.assertEqual([reference(passage)], view['new_passages'])
        self.assertEqual(before, encode(self.f.repo.state()))  # the derived view writes nothing

    def test_pair_route_refuses_typed_and_malformed_queries_without_writing(self):
        bundle = self.post('/probe-bundles', self.body).json()
        url = self.f.url + '/probe-bundles/pair'
        ref = json.dumps(reference(bundle))
        before = encode(self.f.repo.state())
        # Equal cutoffs: the same saved bundle on both sides is not a later cutoff.
        same = self.client.get(url, headers=self.f.headers, params={'before': ref, 'after': ref})
        self.assertEqual((422, {'code': 'PAIR_CUTOFF_ORDER'}), (same.status_code, same.json()))
        # A task reference is readable, but it is not a saved probe bundle.
        other = json.dumps(reference(self.task))
        wrong_kind = self.client.get(url, headers=self.f.headers, params={'before': other, 'after': ref})
        self.assertEqual((422, {'code': 'PAIR_NOT_A_BUNDLE'}), (wrong_kind.status_code, wrong_kind.json()))
        # A query value that is not a record reference stays the shared INVALID_RECORD.
        malformed = self.client.get(url, headers=self.f.headers, params={'before': 'not-a-ref', 'after': ref})
        self.assertEqual((422, {'code': 'INVALID_RECORD'}), (malformed.status_code, malformed.json()))
        # A reference the actor cannot read is hidden as on every other route.
        missing = json.dumps(dict(reference(bundle), record_id='probe:absent', content_digest='0' * 64))
        absent = self.client.get(url, headers=self.f.headers, params={'before': missing, 'after': ref})
        self.assertEqual((404, {'code': 'NOT_FOUND'}), (absent.status_code, absent.json()))
        self.assertEqual(before, encode(self.f.repo.state()))


    def test_a_review_records_the_artifact_it_cites_and_refuses_another_task_s(self):
        # A review decision may name the judgment it relied on: `ReviewBody` carries the
        # optional `judgment_ref`, the decision records it, and a replay returns the same
        # receipt. A reference that does not name this task's artifact is a conflict.
        saved = self.post('/probe-bundles', self.body).json()
        body = dict(self.f.body(), disposition='retain', new_value=None, judgment_ref=reference(saved))
        review = self.post('/reviews', body)
        self.assertEqual(200, review.status_code, review.text)
        receipt = review.json()
        decision = self.f.repo.read(self.f.actor, self.f.case, receipt['decision_ref'])
        self.assertEqual(reference(saved), decision['payload']['judgment_ref'])
        self.assertEqual(200, self.post('/reviews', body).status_code)
        self.assertEqual(receipt, self.post('/reviews', body).json())
        self.assertEqual(1, len(self.f.repo.history(self.f.actor, self.f.case)))

        # Another task's saved artifact is the wrong judgment for this decision, and a
        # reference that names nothing resolves to nothing; both are typed refusals.
        earlier = self.f.task(info=h0.SEED)
        foreign, _ = self.saved_bundle(earlier, probes.BASE, 'probe-foreign')
        absent = dict(reference(saved), record_id='probe:absent', content_digest='0' * 64)
        for label, ref in (('foreign', reference(foreign)), ('absent', absent)):
            response = self.post('/reviews', dict(self.f.body(), judgment_ref=ref, idempotency_key=label, request_id=label))
            self.assertEqual((409, {'code': 'JUDGMENT_TASK_MISMATCH'}), (response.status_code, response.json()))
        malformed = self.post('/reviews', dict(self.f.body(), judgment_ref={'record_id': 'probe:x'},
                                              idempotency_key='malformed', request_id='malformed'))
        self.assertEqual((422, {'code': 'INVALID_RECORD'}), (malformed.status_code, malformed.json()))
        self.assertEqual(1, len(self.f.repo.history(self.f.actor, self.f.case)))


if __name__ == '__main__':
    unittest.main()
