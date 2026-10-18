"""Required emulator integration suite: intentionally fails when emulators are absent."""
import base64
import copy
import hashlib
import json
import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import Mock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_review_case as h0
from src.adapters.firestore import FirestoreStore
from src.adapters.identity import FirebaseIdentity, MembershipIdentity, local_configuration
from src.api import create_app
from src.review import ReviewError, reference
from src.review.storage import PersistentRepository, StorageUnavailable, decode
from fastapi.testclient import TestClient
import httpx

PROJECT = 'demo-nowcast-h1'


class InspectableRepository(PersistentRepository):
    """Test-only inspection of committed state; never exposed through the API."""
    def state(self):
        from src.review import ActorContext
        a = h0.FIXTURE
        actor = ActorContext(a['actor_id'], a['tenant_id'], frozenset({a['case_id']}),
                             frozenset({'synthetic-public', 'synthetic-private'}), True)
        return decode(self.store.load(actor, a['case_id']).entries)

    @property
    def _latest(self):
        return self.state()._latest

    @property
    def _records(self):
        return self.state()._records

    def _records_in(self, *args):
        return self.state()._records_in(*args)


class H1Parity(h0.H0Case):
    def make_repository(self):
        store = FirestoreStore(PROJECT, 'synthetic-' + uuid4().hex)
        self.addCleanup(self.cleanup_store, store)
        for uid in (self.f['actor_id'], 'synthetic-other'):
            store.member_ref(uid, self.f['tenant_id'], self.f['case_id']).set({
                'uid': uid, 'tenant_id': self.f['tenant_id'], 'case_id': self.f['case_id'],
                'active': True, 'can_review': True,
                'source_policy_refs': ['synthetic-public', 'synthetic-private']})
        return InspectableRepository(store)

    @staticmethod
    def cleanup_store(store):
        # Delete only this random test namespace, never emulator-wide or production data.
        def remove(ref):
            for collection in ref.collections():
                for child in collection.list_documents():
                    remove(child)
            ref.delete()
        remove(store.root)
        store.close()

    def connection(self):
        store = FirestoreStore(PROJECT, self.repo.store.root.id)
        self.addCleanup(store.close)
        return PersistentRepository(store)

    def test_concurrent_reviews_same_heads_exactly_one_commits(self):
        task = self.task()
        requests = [self.request(task, key=k) for k in ('a', 'b')]
        repos = [self.connection(), self.connection()]
        barrier = Barrier(2)
        for repo in repos:
            def once(repo=repo):
                repo.before_commit = None
                barrier.wait(timeout=15)
            repo.before_commit = once
        def run(pair):
            repo, request = pair
            try:
                return repo.commit_review(self.actor, request)
            except ReviewError as exc:
                return exc.code
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(run, zip(repos, requests)))
        self.assertEqual(1, sum(type(r) is dict for r in results))
        self.assertEqual(1, results.count('STALE_HEAD'))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))

    def test_mapping_change_between_preparation_and_commit_blocks_without_writes(self):
        request = self.request()
        def change():
            self.repo.before_commit = None
            self.add_mapping(revision='2', at=h0.TODAY)
        self.repo.before_commit = change
        self.assertCode('STALE_DEPENDENCY', self.repo.commit_review, self.actor, request)
        self.assertEqual([], self.repo.history(self.actor, self.case))

    def test_proposal_exact_signed_delta_and_uncomputed_output(self):
        self.repo.commit_review(self.actor, self.request())
        proposal = self.repo.prepare_scenario(self.actor, self.case, 'review-a', h0.TODAY)
        self.assertEqual('uncomputed', self.repo.export_scenario(self.actor, self.case, reference(proposal))['payload']['consequences'])

    def test_restart_and_concurrent_identical_receipts(self):
        request = self.request()
        repos = [self.connection(), self.connection()]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda r: r.commit_review(self.actor, request), repos))
        self.assertEqual(results[0], results[1])
        restarted = self.connection()
        self.assertEqual(results[0], restarted.commit_review(self.actor, request))
        self.assertEqual(self.source, restarted.read(self.actor, self.case, reference(self.source)))
        self.assertEqual(1, len(restarted.history(self.actor, self.case)))

    def test_revocation_between_prepare_commit_and_old_receipts(self):
        request = self.request()
        member = self.repo.store.member_ref(self.actor.actor_id, self.actor.tenant_id, self.case)
        def revoke():
            self.repo.before_commit = None
            member.update({'can_review': False})
        self.repo.before_commit = revoke
        self.assertCode('ACCESS_DENIED', self.repo.commit_review, self.actor, request)
        self.assertEqual([], self.repo.history(self.actor, self.case))
        member.update({'can_review': True})
        self.repo.commit_review(self.actor, request)
        proposal = self.repo.prepare_scenario(self.actor, self.case, 'review-a', h0.TODAY)
        member.update({'source_policy_refs': []})
        self.assertCode('ACCESS_DENIED', self.repo.receipt, self.actor, self.case, 'review-a')
        self.assertCode('ACCESS_DENIED', self.repo.export_scenario, self.actor, self.case, reference(proposal))

    def test_abort_has_no_partial_writes_and_transaction_retry_uses_prepared_json(self):
        from google.api_core.exceptions import Aborted, ServiceUnavailable
        request = self.request()
        before = self.repo.store.load(self.actor, self.case).entries
        with patch('google.cloud.firestore_v1.transaction.Transaction._commit', side_effect=ServiceUnavailable('injected')):
            with self.assertRaises((StorageUnavailable, ValueError)):
                self.repo.commit_review(self.actor, request)
        self.assertEqual(before, self.repo.store.load(self.actor, self.case).entries)
        from google.cloud.firestore_v1.transaction import Transaction
        original = Transaction._commit
        writes = []
        def retry(tx):
            # read-only load also commits: abort only the prepared write transaction.
            if tx._write_pbs:
                writes.append(list(tx._write_pbs))
                if len(writes) == 1:
                    tx._rollback()
                    raise Aborted('injected retry')
            return original(tx)
        with patch.object(Transaction, '_commit', retry):
            self.repo.commit_review(self.actor, request)
        self.assertEqual(2, len(writes))
        self.assertEqual(writes[0], writes[1])
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))


class H1HTTP(H1Parity):
    # Reuse fixture, not the complete inherited parity test collection.
    def setUp(self):
        super().setUp()
        self.identity = FirebaseIdentity(PROJECT)
        self.addCleanup(self.identity.close)
        host = os.environ['FIREBASE_AUTH_EMULATOR_HOST']
        from firebase_admin import auth
        email = 'h1-' + uuid4().hex + '@example.test'
        password = 'local-only-' + uuid4().hex
        user = auth.create_user(uid=self.actor.actor_id, email=email, password=password, app=self.identity.app)
        self.addCleanup(auth.delete_user, user.uid, app=self.identity.app)
        response = httpx.post('http://' + host + '/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=synthetic',
                              json={'email': email, 'password': password, 'returnSecureToken': True})
        response.raise_for_status()
        self.headers = {'authorization': 'Bearer ' + response.json()['idToken']}
        self.clock = Mock(return_value=h0.TODAY)
        self.client = TestClient(create_app(self.repo, self.identity, self.clock))
        self.addCleanup(self.client.close)
        self.url = f'/v1/tenants/{self.actor.tenant_id}/cases/{self.case}'

    def post(self, suffix, body):
        return self.client.post(self.url + suffix, json=body, headers=self.headers)

    def body(self):
        request = self.request()
        return {k: v for k, v in request.items() if k not in ('case_id', 'recorded_at', 'reviewed_at')}

    def test_http_review_replay_restart_exact_body_and_server_clock(self):
        body = self.body()
        first = self.post('/reviews', body)
        self.assertEqual(200, first.status_code, first.text)
        self.clock.assert_called_once()
        self.clock.reset_mock()
        restarted = TestClient(create_app(self.connection(), self.identity, self.clock))
        self.addCleanup(restarted.close)
        again = restarted.post(self.url + '/reviews', json=body, headers=self.headers)
        self.assertEqual(first.json(), again.json())
        self.clock.assert_not_called()
        different_bytes = json.dumps(body, indent=2)
        conflict = restarted.post(self.url + '/reviews', content=different_bytes, headers=dict(self.headers, **{'content-type': 'application/json'}))
        self.assertEqual(409, conflict.status_code)
        self.clock.assert_not_called()
        receipt = first.json()
        decision = self.repo.read(self.actor, self.case, receipt['decision_ref'])
        self.assertEqual('2026-10-05T02:00:00Z', decision['recorded_at'])

    def test_http_auth_authority_sizes_and_discovery(self):
        self.assertEqual(401, self.client.get(self.url).status_code)
        self.assertEqual(401, self.client.get(self.url, headers={'authorization': 'Bearer malformed'}).status_code)
        denied = self.client.get(self.url.replace(self.case, 'unknown'), headers=self.headers)
        self.assertEqual((404, {'code': 'NOT_FOUND'}), (denied.status_code, denied.json()))
        self.assertEqual(422, self.post('/reviews', dict(self.body(), actor_id='admin')).status_code)
        self.assertEqual(422, self.post('/reviews', dict(self.body(), reviewed_at=h0.TODAY)).status_code)
        self.assertEqual(422, self.post('/evidence', {'record': self.source, 'source_base64': '%%%'}).status_code)
        huge = base64.b64encode(b'a' * (256 * 1024 + 1)).decode()
        self.assertEqual(422, self.post('/evidence', {'record': self.source, 'source_base64': huge}).status_code)
        response = self.client.post(self.url + '/reviews', content=b'x' * (1024 * 1024 + 1), headers=self.headers)
        self.assertEqual(422, response.status_code)
        bad = self.body(); bad['new_value']['unit'] = 'invented'
        self.assertEqual(422, self.post('/reviews', bad).status_code)
        with self.assertLogs('nowcast.http', level='INFO') as logs:
            response = self.post('/read', {'ref': dict(reference(self.source), record_id='private-secret')})
        self.assertEqual({'code': 'NOT_FOUND'}, response.json())
        self.assertNotIn('private-secret', str(logs.output))
        self.assertNotIn(self.headers['authorization'], str(logs.output))

    def test_http_end_to_end_without_model(self):
        evidence = self.post('/evidence', {'record': self.source, 'source_base64': base64.b64encode(self.f['source_text'].encode()).decode()})
        self.assertEqual(200, evidence.status_code)
        snapshot = self.post('/snapshots', {'audit_cutoff': h0.CUTOFF})
        self.assertEqual(200, snapshot.status_code, snapshot.text)
        task = self.post('/compile', {'snapshot_ref': reference(snapshot.json()), 'assumption_id': 'assumption-a', 'information_cutoff': h0.CUTOFF})
        self.assertEqual(200, task.status_code, task.text)
        req = self.request(task.json())
        body = {k: v for k, v in req.items() if k not in ('case_id', 'recorded_at', 'reviewed_at')}
        review = self.post('/reviews', body)
        self.assertEqual(200, review.status_code, review.text)
        proposal = self.post('/proposals', {'idempotency_key': 'review-a'})
        self.assertEqual(200, proposal.status_code, proposal.text)
        exported = self.post('/export', {'ref': reference(proposal.json())})
        self.assertEqual(200, exported.status_code, exported.text)
        self.repo.store.member_ref(self.actor.actor_id, self.actor.tenant_id, self.case).update({'active': False})
        self.assertEqual(404, self.post('/export', {'ref': reference(proposal.json())}).status_code)
        self.assertEqual(404, self.client.get(self.url + '/receipts/review-a', headers=self.headers).status_code)

    def test_storage_unavailable_safe_and_configuration_fail_closed(self):
        with patch.object(self.repo.store, 'load', side_effect=StorageUnavailable):
            response = self.client.get(self.url, headers=self.headers)
        self.assertEqual((503, {'code': 'STORAGE_UNAVAILABLE'}), (response.status_code, response.json()))
        for changes in ({'NOWCAST_ENV': 'production'}, {'K_SERVICE': 'deployed'}, {'FIRESTORE_EMULATOR_HOST': 'remote:8080'}):
            with patch.dict(os.environ, changes), self.assertRaises(ValueError):
                local_configuration(PROJECT)
        with self.assertRaises(ValueError):
            local_configuration('real-project')


# HTTP tests share only fixture methods; avoid counting H0 cases twice.
for name in dir(H1Parity):
    if name.startswith('test_') and name not in H1HTTP.__dict__:
        setattr(H1HTTP, name, None)
