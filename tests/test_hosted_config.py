"""HOST-1: hosted configuration, the safe demo sandbox and the local image contract.

Offline and SDK-free. `src/api/__init__.py` imports FastAPI, so this module is loaded by file
location the way tests/test_plan.py loads scripts/plan.py: the configuration, in-process store,
session, reset and image-structure checks then run with the bare interpreter. The HTTP wiring
checks need FastAPI's TestClient and are skipped where it is not installed — run them in the
container image or with `.local/h1-venv/bin/python -m unittest tests.test_hosted_config -v`.
No network call, model call or cloud write is made anywhere in this file.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.identity import AuthenticationFailed, FirebaseIdentity, local_configuration
from src.review import ActorContext, ReviewError, reference
from src.review.storage import PersistentRepository, RetryPreparation, StorageUnavailable

SPEC = importlib.util.spec_from_file_location('nowcast_hosted', ROOT / 'src' / 'api' / 'hosted.py')
hosted = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hosted)

try:
    from fastapi.testclient import TestClient
    FASTAPI = True
except ImportError:  # the bare interpreter has no FastAPI; the wiring checks say so.
    FASTAPI = False

AUDIT = '2026-10-01T10:00:00+08:00'
TODAY = '2026-10-05T10:00:00+08:00'
# A labelled synthetic cloud project: the release audit (REL-1) accepts `synthetic-*`
# identifiers and the hosted tests only need a value the stubbed SDKs can echo back.
PROJECT = 'synthetic-nowcast-h1'
HOSTED_ENV = dict(NOWCAST_ENV='hosted', GCLOUD_PROJECT=PROJECT,
                  FIREBASE_WEB_API_KEY='public-web-key', NOWCAST_NAMESPACE='private-cases')
FIREBASE_UID = 'firebase-anonymous-uid'
ANONYMOUS_CLAIM = dict(uid=FIREBASE_UID, firebase=dict(sign_in_provider='anonymous'))


def demo_runtime():
    return hosted.demo_runtime(dict())


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baked_copy(source, target, missing=()):
    """DATA-2: a copy of the replay tree `source` at `target` with the manifest build_all.py
    would write for it — its stamp, its data digest and its own digest from build_all.py's and
    the stager's own functions — so a release's manifest gate passes on a labelled synthetic
    fixture. `missing` records inputs left out (a partial bake)."""
    build_all = _load('data2_build_all', ROOT / 'scripts' / 'grid' / 'build_all.py')
    stager = _load('data2_stage_hosting', ROOT / 'scripts' / 'deploy' / 'stage_hosting.py')
    shutil.copytree(source, target)
    digest, files = build_all.data_digest(Path(target))
    manifest = {'schema': build_all.MANIFEST_SCHEMA,
                'stamp': stager.build_stamp(target, ROOT / 'src' / 'grid'),
                'data_digest': digest, 'files': files, 'missing': list(missing),
                'allowed_missing': list(missing), 'inputs': [], 'replay': None,
                'outages': None, 'counts': {}, 'git': {}, 'options': {}}
    manifest['digest'] = build_all.manifest_digest(manifest)
    manifest['written_at'] = '2026-10-18T00:00:00+00:00'
    build_all.write_manifest(Path(target), manifest)
    return Path(target)


def actor(session):
    return ActorContext(session.uid, session.tenant, frozenset([session.case]),
                        frozenset([hosted.SOURCE_POLICY]), True)


class DemoCase(unittest.TestCase):
    """Shared demo fixture: one runtime over the labelled corpus, plus the two session helpers."""

    def setUp(self):
        self.runtime = demo_runtime()

    def capped(self, maximum):
        """The same demo runtime with a reachable sandbox cap; nothing else is swapped."""
        runtime = self.runtime
        fixture = hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE)
        return hosted.Runtime(runtime.settings, runtime.store,
                              hosted.SandboxIdentity(fixture, maximum=maximum),
                              runtime.repository, runtime.digest)

    def open_session(self, runtime=None):
        runtime = runtime or self.runtime
        return hosted.create_judge_session(hosted.DEMO_MODE, runtime.store,
                                           runtime.identity, runtime.repository)

    def review(self, session, key='review-a'):
        snapshot = self.runtime.repository.build_snapshot(actor(session), session.case, AUDIT, TODAY)
        task = self.runtime.repository.compile_task(actor(session), session.case, reference(snapshot),
                                                    'capacity-assumption', AUDIT, TODAY)
        heads = self.runtime.repository.heads(actor(session), session.case)
        return dict(case_id=session.case, request_id=key, idempotency_key=key, task_ref=reference(task),
                    snapshot_digest=task['payload']['snapshot_ref']['content_digest'],
                    expected_assumption_head=task['payload']['assumption_ref'],
                    expected_outlook_head=heads['outlook'],
                    disposition='retain', rationale='Fictional analyst retained the accepted input',
                    new_value=None, reviewed_at=TODAY, recorded_at=TODAY)


class ConfigurationTests(unittest.TestCase):
    def refusal(self, environ, call=hosted.hosted_settings):
        with self.assertRaises(hosted.HostedConfigurationError) as caught:
            call(environ)
        return caught.exception

    def test_unset_mode_is_demo_and_needs_no_environment(self):
        self.assertEqual('demo', hosted.select_mode(dict()))
        self.assertEqual('demo', hosted.select_mode(dict(NOWCAST_ENV='')))
        self.assertEqual(hosted.Settings('demo'), hosted.demo_settings(dict()))
        self.assertEqual('demo', hosted.settings(dict()).mode)

    def test_demo_and_hosted_are_accepted_and_local_is_refused_here(self):
        self.assertEqual('demo', hosted.select_mode(dict(NOWCAST_ENV='demo')))
        self.assertEqual('hosted', hosted.select_mode(HOSTED_ENV))
        self.assertEqual('hosted', hosted.settings(HOSTED_ENV).mode)
        self.assertEqual('LOCAL_MODE_REFUSED', self.refusal(dict(NOWCAST_ENV='local'), hosted.settings).code)

    def test_unknown_mode_is_refused(self):
        for value in ('production', 'DEMO', 'local ', 'demo ', ' demo'):
            self.assertEqual('UNKNOWN_MODE', self.refusal(dict(NOWCAST_ENV=value), hosted.select_mode).code)

    def test_emulator_variables_are_refused_outside_local_mode(self):
        for name in hosted.EMULATOR_VARIABLES:
            for call, base in ((hosted.demo_settings, dict()), (hosted.hosted_settings, HOSTED_ENV)):
                environ = dict(base, **{name: '127.0.0.1:18080'})
                self.assertEqual('EMULATOR_CONFIGURATION', self.refusal(environ, call).code)

    def test_every_named_hosted_setting_is_required(self):
        for missing in ('GCLOUD_PROJECT', 'FIREBASE_WEB_API_KEY', 'NOWCAST_NAMESPACE'):
            environ = dict(HOSTED_ENV)
            environ.pop(missing)
            self.assertEqual('MISSING_CONFIGURATION', self.refusal(environ).code)
            self.assertEqual('MISSING_CONFIGURATION', self.refusal(dict(environ, **{missing: '   '})).code)

    def test_the_local_project_pattern_is_refused_in_hosted_mode(self):
        for project in ('demo-nowcast-h1', 'demo-x'):
            self.assertEqual('CONFLICTING_CONFIGURATION',
                             self.refusal(dict(HOSTED_ENV, GCLOUD_PROJECT=project)).code)

    def test_demo_and_private_namespaces_must_differ_and_be_portable(self):
        for change in (dict(NOWCAST_NAMESPACE='demo-judge'), dict(NOWCAST_DEMO_NAMESPACE='private-cases'),
                       dict(NOWCAST_NAMESPACE='Private Cases'), dict(NOWCAST_DEMO_NAMESPACE='demo_judge'),
                       dict(NOWCAST_NAMESPACE='demo-'), dict(NOWCAST_DEMO_NAMESPACE='-demo')):
            self.assertEqual('CONFLICTING_CONFIGURATION', self.refusal(dict(HOSTED_ENV, **change)).code)

    def test_the_demo_namespace_defaults_and_the_port_is_bounded(self):
        settings = hosted.hosted_settings(HOSTED_ENV)
        self.assertEqual('demo-judge', settings.demo_namespace)
        self.assertEqual(8080, settings.port)
        self.assertEqual(9000, hosted.hosted_settings(dict(HOSTED_ENV, PORT='9000')).port)
        for port in ('0', '70000', 'abc', '-1', '8080 ', '8080.0', '', '   '):
            self.assertEqual('CONFLICTING_CONFIGURATION', self.refusal(dict(HOSTED_ENV, PORT=port)).code)

    def test_an_absent_port_defaults_and_an_explicitly_blank_port_is_a_conflict(self):
        # Designated review 1, minor finding: `PORT=''` used to fall through to 8080, so an
        # explicitly blank value must be refused like every other blank named setting.
        self.assertEqual(8080, hosted.hosted_settings(HOSTED_ENV).port)
        self.assertEqual(8080, hosted.hosted_settings(dict(HOSTED_ENV, PORT=None)).port)
        for blank in ('', '   '):
            self.assertEqual('CONFLICTING_CONFIGURATION', self.refusal(dict(HOSTED_ENV, PORT=blank)).code)

    def test_a_refusal_never_echoes_a_supplied_value(self):
        # Labelled synthetic, and deliberately not named like a credential: the release audit
        # flags credential-shaped assignments in the shipped tree by name, not by value.
        supplied = 'synthetic-web-key-value'
        error = self.refusal(dict(HOSTED_ENV, FIREBASE_WEB_API_KEY=supplied, NOWCAST_NAMESPACE='demo-judge'))
        self.assertNotIn(supplied, str(error))
        self.assertNotIn(supplied, error.code)

    def test_local_configuration_still_refuses_hosted_indicators(self):
        loopback = dict(NOWCAST_ENV='local', FIRESTORE_EMULATOR_HOST='127.0.0.1:18080',
                        FIREBASE_AUTH_EMULATOR_HOST='127.0.0.1:19099')
        with patch.dict(os.environ, loopback, clear=True):
            self.assertIsNone(local_configuration('demo-nowcast-h1'))
        for changes in (dict(loopback, NOWCAST_ENV='hosted'), dict(loopback, K_SERVICE='deployed'),
                        dict(loopback, GAE_ENV='standard'), dict(loopback, FIRESTORE_EMULATOR_HOST='remote:8080'),
                        dict(loopback, FIREBASE_AUTH_EMULATOR_HOST='127.0.0.1'),
                        dict(loopback, FIRESTORE_EMULATOR_HOST='127.0.0.1:0')):
            with patch.dict(os.environ, changes, clear=True), self.assertRaises(ValueError):
                local_configuration('demo-nowcast-h1')
        with patch.dict(os.environ, loopback, clear=True), self.assertRaises(ValueError):
            local_configuration('real-project')


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = hosted.MemoryStore()
        self.session = hosted.Session('demo-a', hosted.JUDGE_TENANT, 'demo-case-a')
        self.store.member_ref(self.session.uid, self.session.tenant, self.session.case).set(
            hosted.membership_document(self.session.uid, self.session.tenant, self.session.case))

    def load(self, session=None):
        return self.store.load(actor(session or self.session), (session or self.session).case)

    def commit(self, before, entries, session=None):
        after = dict(before.entries)
        after.update(entries)
        self.store.commit(actor(session or self.session), (session or self.session).case, before, after)

    def test_membership_has_exactly_the_six_keys_current_actor_validates(self):
        membership = self.store.membership(self.session.uid, self.session.tenant, self.session.case)
        self.assertEqual({'uid', 'tenant_id', 'case_id', 'active', 'can_review', 'source_policy_refs'},
                         set(membership))
        membership['active'] = False
        self.assertTrue(self.store.membership(self.session.uid, self.session.tenant, self.session.case)['active'])
        self.assertIsNone(self.store.membership(self.session.uid, self.session.tenant, 'other-case'))

    def test_load_refuses_without_a_membership_for_this_uid_tenant_and_case(self):
        for uid, tenant, case in (('demo-b', self.session.tenant, self.session.case),
                                  (self.session.uid, 'demo-tenant-other', self.session.case),
                                  (self.session.uid, self.session.tenant, 'other-case')):
            candidate = ActorContext(uid, tenant, frozenset([case]), frozenset([hosted.SOURCE_POLICY]), True)
            with self.assertRaises(ReviewError) as caught:
                self.store.load(candidate, case)
            self.assertEqual('ACCESS_DENIED', caught.exception.code)

    def test_a_revoked_widened_or_malformed_membership_is_refused(self):
        ref = self.store.member_ref(self.session.uid, self.session.tenant, self.session.case)
        document = hosted.membership_document(self.session.uid, self.session.tenant, self.session.case)
        for change in (dict(active=False), dict(can_review='yes'), dict(source_policy_refs='synthetic-public'),
                       dict(extra=True), dict(active=False, extra=True)):
            ref.set(dict(document, **change))
            with self.assertRaises(ReviewError) as caught:
                self.load()
            self.assertEqual('ACCESS_DENIED', caught.exception.code)
        ref.set(document)
        self.assertEqual({}, self.load().entries)

    def test_commit_rechecks_the_generation_and_the_stored_membership(self):
        before = self.load()
        self.commit(before, {'["latest", ["demo-judge-a"]]': '1'})
        self.assertEqual(1, self.load().generation)
        with self.assertRaises(RetryPreparation):
            self.commit(before, {'["latest", ["demo-judge-b"]]': '1'})
        current = self.load()
        self.store.member_ref(self.session.uid, self.session.tenant, self.session.case).set(
            dict(hosted.membership_document(self.session.uid, self.session.tenant, self.session.case),
                 can_review=False))
        with self.assertRaises(RetryPreparation):
            self.commit(current, {'["latest", ["demo-judge-c"]]': '1'})
        self.assertEqual(1, self.load().generation)

    def test_an_immutable_record_key_cannot_be_rewritten(self):
        key = '["records", ["demo-judge", "demo-case-a", "SourceVersion", "fictional-advisory", "1"]]'
        self.commit(self.load(), {key: '"first"'})
        with self.assertRaises(ReviewError) as caught:
            self.commit(self.load(), {key: '"second"'})
        self.assertEqual('REVISION_CONFLICT', caught.exception.code)

    def test_entries_are_returned_as_copies_and_commit_is_bounded(self):
        self.commit(self.load(), {'["latest", ["demo-judge-a"]]': '1'})
        snapshot = self.load()
        snapshot.entries.clear()
        self.assertEqual(1, len(self.load().entries))
        with self.assertRaises(ReviewError):
            self.commit(self.load(), {f'["latest", ["demo-{index}"]]': '1' for index in range(451)})

    def test_discard_case_drops_only_that_case_and_not_its_membership(self):
        other = hosted.Session('demo-b', hosted.JUDGE_TENANT, 'demo-case-b')
        self.store.member_ref(other.uid, other.tenant, other.case).set(
            hosted.membership_document(other.uid, other.tenant, other.case))
        self.commit(self.load(), {'["latest", ["demo-judge-a"]]': '1'})
        self.commit(self.load(other), {'["latest", ["demo-judge-b"]]': '1'}, session=other)
        self.store.discard_case(self.session.tenant, self.session.case)
        self.assertEqual({}, self.load().entries)
        self.assertEqual(0, self.load().generation)
        self.assertEqual(1, len(self.load(other).entries))
        self.assertIsNotNone(self.store.membership(self.session.uid, self.session.tenant, self.session.case))


class DemoSessionTests(DemoCase):
    def test_the_fixture_corpus_is_labelled_and_provisioned_at_startup(self):
        self.assertEqual('synthetic-tenant', hosted.TENANT)
        self.assertEqual('synthetic-case', hosted.CASE)
        fixture = actor(hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE))
        workspace = self.runtime.repository.workspace(fixture, hosted.CASE)
        self.assertEqual(1, len(workspace['assumptions']))
        self.assertEqual('capacity-assumption', workspace['assumptions'][0]['record_id'])
        self.assertEqual(64, len(self.runtime.digest))
        source = self.runtime.repository.read(fixture, hosted.CASE, workspace['assumptions'][0]['payload']['mapping_ref'])
        self.assertEqual('MappingRevision', source['record_kind'])

    def test_two_sessions_get_distinct_server_derived_uids_cases_and_memberships(self):
        first, first_token = self.open_session()
        second, second_token = self.open_session()
        self.assertNotEqual(first.uid, second.uid)
        self.assertNotEqual(first.case, second.case)
        self.assertNotEqual(first_token, second_token)
        for session in (first, second):
            self.assertEqual(hosted.JUDGE_TENANT, session.tenant)
            self.assertEqual(hosted.session_case(session.uid), session.case)
            self.assertRegex(session.uid, r'demo-[0-9a-f]{32}')
            self.assertRegex(session.case, r'demo-[0-9a-f]{16}')
            document = self.runtime.store.membership(session.uid, session.tenant, session.case)
            self.assertEqual({'uid', 'tenant_id', 'case_id', 'active', 'can_review', 'source_policy_refs'},
                             set(document))
            self.assertEqual([hosted.SOURCE_POLICY], document['source_policy_refs'])

    def test_each_session_reads_and_reviews_only_its_own_case(self):
        first, _ = self.open_session()
        second, _ = self.open_session()
        for session in (first, second):
            projection = self.runtime.repository.workspace(actor(session), session.case)
            self.assertEqual(1, len(projection['assumptions']))
            self.assertEqual(session.case, projection['assumptions'][0]['case_id'])
        self.runtime.repository.commit_review(actor(first), self.review(first))
        self.assertEqual(1, len(self.runtime.repository.history(actor(first), first.case)))
        self.assertEqual(0, len(self.runtime.repository.history(actor(second), second.case)))
        for session, other in ((first, second), (second, first)):
            for call in ('workspace', 'heads', 'history'):
                with self.assertRaises(ReviewError) as caught:
                    getattr(self.runtime.repository, call)(actor(session), other.case)
                self.assertEqual('ACCESS_DENIED', caught.exception.code)

    def test_a_private_or_unknown_shape_reaches_nothing(self):
        session, _ = self.open_session()
        for tenant, case in ((hosted.JUDGE_TENANT, hosted.CASE), ('private-tenant', hosted.CASE),
                             (hosted.TENANT, hosted.CASE), (hosted.JUDGE_TENANT, 'demo-0000000000000000')):
            candidate = ActorContext(session.uid, tenant, frozenset([case]), frozenset([hosted.SOURCE_POLICY]), True)
            with self.assertRaises(ReviewError) as caught:
                self.runtime.repository.workspace(candidate, case)
            self.assertEqual('ACCESS_DENIED', caught.exception.code)

    def test_a_client_supplied_uid_tenant_or_case_selects_nothing(self):
        session, _ = self.open_session()
        self.assertEqual(hosted.JUDGE_TENANT, session.tenant)
        self.assertEqual(hosted.session_case(session.uid), session.case)
        self.assertIsNone(self.runtime.store.membership('client-supplied-uid', hosted.JUDGE_TENANT, session.case))
        self.assertIsNone(self.runtime.store.membership(session.uid, hosted.JUDGE_TENANT, 'client-supplied-case'))
        self.assertIsNone(self.runtime.store.membership(session.uid, 'private-tenant', session.case))

    def test_the_documented_fictional_account_signs_in_without_network_or_emulator(self):
        with patch('socket.socket', side_effect=AssertionError('network use during sign-in')):
            runtime = demo_runtime()
            result = runtime.identity.sign_in(hosted.EMAIL, hosted.PASSWORD)
        uid = runtime.identity.verify('Bearer ' + result['id_token'])
        self.assertEqual(hosted.UID, uid)
        fixture = actor(hosted.Session(uid, hosted.TENANT, hosted.CASE))
        self.assertEqual(1, len(runtime.repository.workspace(fixture, hosted.CASE)['assumptions']))
        for email, password in (('other@example.test', hosted.PASSWORD), (hosted.EMAIL, 'wrong'),
                                (hosted.EMAIL, ''), ('', ''), (None, None), (hosted.EMAIL, None)):
            with self.assertRaises(AuthenticationFailed):
                runtime.identity.sign_in(email, password)

    def test_tokens_are_opaque_and_bounded(self):
        session, token = self.open_session()
        self.assertEqual(session.uid, self.runtime.identity.verify('Bearer ' + token))
        for header in (None, '', 'token', 'Bearer', 'Bearer ', 'Basic ' + token,
                       'Bearer ' + 'x' * (hosted.MAX_TOKEN + 1)):
            with self.assertRaises(AuthenticationFailed):
                self.runtime.identity.verify(header)


class SandboxCapacityTests(DemoCase):
    """The sandbox cap refuses new sessions; it never evicts a live one (review finding 2)."""

    def test_a_full_sandbox_refuses_new_sessions_without_writing_or_evicting_anything(self):
        runtime = self.capped(2)
        first, first_token = self.open_session(runtime)
        second, second_token = self.open_session(runtime)
        cases, members = len(runtime.store._cases), len(runtime.store._members)
        with self.assertRaises(hosted.SessionUnavailable):
            self.open_session(runtime)
        self.assertEqual((cases, members),
                         (len(runtime.store._cases), len(runtime.store._members)))
        for session, token in ((first, first_token), (second, second_token)):
            self.assertEqual(session.uid, runtime.identity.verify('Bearer ' + token))
            self.assertEqual(1, len(runtime.repository.workspace(actor(session), session.case)['assumptions']))

    def test_the_cap_bounds_outstanding_tokens_too(self):
        runtime = self.capped(1)
        session, token = self.open_session(runtime)
        tokens, cases = len(runtime.identity._tokens), len(runtime.store._cases)
        # The fictional account is shared, so repeated sign-ins are a second growth path.
        with self.assertRaises(hosted.SessionUnavailable):
            runtime.identity.sign_in(hosted.EMAIL, hosted.PASSWORD)
        self.assertEqual((tokens, cases), (len(runtime.identity._tokens), len(runtime.store._cases)))
        self.assertEqual(session.uid, runtime.identity.verify('Bearer ' + token))
        self.assertEqual(1, len(runtime.repository.workspace(actor(session), session.case)['assumptions']))

    def test_below_the_cap_sessions_open_and_rotate_as_before(self):
        runtime = self.capped(2)
        first, token = self.open_session(runtime)
        second, second_token = self.open_session(runtime)
        fresh = runtime.identity.rotate(first.uid)
        with self.assertRaises(AuthenticationFailed):
            runtime.identity.verify('Bearer ' + token)
        self.assertEqual(first.uid, runtime.identity.verify('Bearer ' + fresh))
        self.assertEqual(second.uid, runtime.identity.verify('Bearer ' + second_token))


class ProvisioningFailureTests(DemoCase):
    """A failed provisioning answers 503 and cleans up; cleanup never masks the 503."""

    def test_a_failed_hosted_provisioning_discards_the_case_and_answers_503(self):
        store = FailingStore()
        identity = AnonymousIdentity()
        repository = PersistentRepository(store)
        with self.assertRaises(hosted.SessionUnavailable):
            hosted.create_judge_session(hosted.HOSTED_MODE, store, identity, repository)
        case = hosted.session_case(identity.uid)
        self.assertEqual([(hosted.JUDGE_TENANT, case)], store.discarded)
        # The membership written just before the failed seed is rolled back with the case; the
        # anonymous Auth user is not (no request may delete one) and stays for HOST-2.
        self.assertEqual([(identity.uid, hosted.JUDGE_TENANT, case)], store.deleted)

    def test_a_failed_demo_provisioning_unregisters_the_session_and_answers_503(self):
        store = FailingStore()
        with self.assertRaises(hosted.SessionUnavailable):
            hosted.create_judge_session(hosted.DEMO_MODE, store, self.runtime.identity,
                                        self.runtime.repository)
        self.assertEqual(1, len(store.discarded))
        self.assertEqual({}, self.runtime.identity._sessions)
        self.assertEqual({}, self.runtime.identity._tokens)
        uid, tenant, case = store.deleted[0]
        self.assertEqual((tenant, case), store.discarded[0])
        self.assertEqual(hosted.session_case(uid), case)

    def test_a_cleanup_failure_never_replaces_the_503(self):
        for store in (FailingStore(discard_fails=True), FailingStore(delete_fails=True),
                      FailingStore(discard_fails=True, delete_fails=True)):
            with self.assertRaises(hosted.SessionUnavailable):
                hosted.create_judge_session(hosted.HOSTED_MODE, store, AnonymousIdentity(),
                                            PersistentRepository(store))


class DemoResetTests(DemoCase):
    def test_reset_restores_the_callers_fixture_state_and_rotates_only_its_tokens(self):
        first, token = self.open_session()
        second, second_token = self.open_session()
        fixture = self.runtime.store.load(actor(first), first.case).entries
        self.runtime.repository.commit_review(actor(first), self.review(first))
        self.assertNotEqual(fixture, self.runtime.store.load(actor(first), first.case).entries)
        membership = self.runtime.store.membership(first.uid, first.tenant, first.case)
        session, fresh = hosted.reset_session(self.runtime.store, self.runtime.identity,
                                              self.runtime.repository, first.uid)
        self.assertEqual(first, session)
        self.assertNotEqual(token, fresh)
        with self.assertRaises(AuthenticationFailed):
            self.runtime.identity.verify('Bearer ' + token)
        self.assertEqual(first.uid, self.runtime.identity.verify('Bearer ' + fresh))
        self.assertEqual(0, len(self.runtime.repository.history(actor(first), first.case)))
        self.assertEqual(1, len(self.runtime.repository.workspace(actor(first), first.case)['assumptions']))
        self.assertEqual(fixture, self.runtime.store.load(actor(first), first.case).entries)
        self.assertEqual(membership, self.runtime.store.membership(first.uid, first.tenant, first.case))
        self.assertEqual(second.uid, self.runtime.identity.verify('Bearer ' + second_token))

    def test_reset_is_repeatable_and_leaves_another_session_untouched(self):
        first, _ = self.open_session()
        second, second_token = self.open_session()
        receipt = self.runtime.repository.commit_review(actor(second), self.review(second, key='review-b'))
        hosted.reset_session(self.runtime.store, self.runtime.identity, self.runtime.repository, first.uid)
        first_entries = self.runtime.store.load(actor(first), first.case).entries
        self.assertEqual(second.uid, self.runtime.identity.verify('Bearer ' + second_token))
        self.assertEqual(1, len(self.runtime.repository.history(actor(second), second.case)))
        self.assertEqual(receipt, self.runtime.repository.receipt(actor(second), second.case, 'review-b'))
        self.assertEqual(1, len(self.runtime.repository.workspace(actor(second), second.case)['assumptions']))
        self.runtime.repository.commit_review(actor(second), self.review(second, key='review-b2'))
        self.assertEqual(2, len(self.runtime.repository.history(actor(second), second.case)))
        second_entries = self.runtime.store.load(actor(second), second.case).entries
        hosted.reset_session(self.runtime.store, self.runtime.identity, self.runtime.repository, first.uid)
        self.assertEqual(first_entries, self.runtime.store.load(actor(first), first.case).entries)
        self.assertEqual(second_entries, self.runtime.store.load(actor(second), second.case).entries)
        self.assertEqual(2, len(self.runtime.repository.history(actor(second), second.case)))
        self.assertEqual(second.uid, self.runtime.identity.verify('Bearer ' + second_token))

    def test_reset_needs_the_callers_own_session_token(self):
        first, _ = self.open_session()
        for uid in ('demo-' + '0' * 32, hosted.UID, 'client-supplied-uid'):
            with self.assertRaises(AuthenticationFailed):
                hosted.reset_session(self.runtime.store, self.runtime.identity, self.runtime.repository, uid)
        self.assertEqual(1, len(self.runtime.repository.workspace(actor(first), first.case)['assumptions']))

    def test_the_fixture_account_has_its_own_resettable_session(self):
        token = self.runtime.identity.sign_in(hosted.EMAIL, hosted.PASSWORD)['id_token']
        self.assertEqual(hosted.UID, self.runtime.identity.verify('Bearer ' + token))
        fixture = hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE)
        self.runtime.repository.commit_review(actor(fixture), self.review_fixture(fixture))
        self.assertEqual(1, len(self.runtime.repository.history(actor(fixture), hosted.CASE)))
        session, fresh = hosted.reset_session(self.runtime.store, self.runtime.identity,
                                              self.runtime.repository, hosted.UID)
        self.assertEqual(fixture, session)
        with self.assertRaises(AuthenticationFailed):
            self.runtime.identity.verify('Bearer ' + token)
        self.assertEqual(hosted.UID, self.runtime.identity.verify('Bearer ' + fresh))
        self.assertEqual(0, len(self.runtime.repository.history(actor(fixture), hosted.CASE)))

    def review_fixture(self, session):
        snapshot = self.runtime.repository.build_snapshot(actor(session), session.case, AUDIT, TODAY)
        task = self.runtime.repository.compile_task(actor(session), session.case, reference(snapshot),
                                                    'capacity-assumption', AUDIT, TODAY)
        return self.review(session, key='review-fixture')

    def test_the_fixture_digest_is_one_constant_across_sessions_and_resets(self):
        first, _ = self.open_session()
        second, _ = self.open_session()
        self.assertEqual(self.runtime.digest, hosted.fixture_digest())
        hosted.reset_session(self.runtime.store, self.runtime.identity, self.runtime.repository, first.uid)
        hosted.reset_session(self.runtime.store, self.runtime.identity, self.runtime.repository, second.uid)
        self.assertEqual(self.runtime.digest, hosted.fixture_digest())
        self.assertEqual(self.runtime.digest, demo_runtime().digest)


class ResetGenerationTests(DemoCase):
    """Designated review 1, important finding 1: reset must not permit stale writes.

    The reviewer loaded a snapshot, reset the session and committed the old snapshot: the case
    was dropped and re-seeded, so its generation restarted and the pre-reset write matched
    `5 == 5`. `MemoryStore.reset_case` now carries the generation forward across the reset and
    holds the store for the whole discard-and-reseed; these tests are the regression.
    """

    def marker(self):
        return '["latest", ["stale-writer"]]'

    def test_a_snapshot_prepared_before_a_reset_cannot_commit_after_it(self):
        session, _ = self.open_session()
        store = self.runtime.store
        self.runtime.repository.commit_review(actor(session), self.review(session))
        stale = store.load(actor(session), session.case)
        self.assertGreater(stale.generation, 0)
        after = dict(stale.entries, **{self.marker(): '1'})
        hosted.reset_session(store, self.runtime.identity, self.runtime.repository, session.uid)
        current = store.load(actor(session), session.case)
        self.assertGreater(current.generation, stale.generation)
        with self.assertRaises(RetryPreparation):
            store.commit(actor(session), session.case, stale, after)
        self.assertEqual(current.entries, store.load(actor(session), session.case).entries)
        self.assertNotIn(self.marker(), store.load(actor(session), session.case).entries)

    def test_the_generation_keeps_moving_across_repeated_resets(self):
        session, _ = self.open_session()
        store = self.runtime.store
        generations = [store.load(actor(session), session.case).generation]
        for _ in range(3):
            hosted.reset_session(store, self.runtime.identity, self.runtime.repository, session.uid)
            generations.append(store.load(actor(session), session.case).generation)
        self.assertEqual(sorted(set(generations)), generations)
        self.assertGreater(len(set(generations)), 1)

    def test_a_write_and_a_read_during_a_reset_wait_for_it_and_see_the_reset_state(self):
        session, token = self.open_session()
        store, identity, repository = self.runtime.store, self.runtime.identity, self.runtime.repository
        pristine = store.load(actor(session), session.case).entries
        self.runtime.repository.commit_review(actor(session), self.review(session))
        stale = store.load(actor(session), session.case)
        after = dict(stale.entries, **{self.marker(): '1'})
        holding, read_done = threading.Event(), threading.Event()
        attempted = {'writer': threading.Event(), 'reader': threading.Event()}
        outcome, observed = [], {}
        real_commit = store.commit
        reset_thread = threading.current_thread()

        def pausing_commit(actor_ctx, case, before, entries):
            # The reset holds the store here, inside its first step. Both helpers attempt their
            # store call inside this window, and neither can reach the store until the reset
            # ends: that is the serialization this test observes, plus the reset generation the
            # stale write then runs into.
            if threading.current_thread() is reset_thread and not holding.is_set():
                holding.set()
                for name, event in attempted.items():
                    self.assertTrue(event.wait(10), f'the {name} never attempted its store call')
                self.assertFalse(read_done.wait(0.2), 'a read completed while the reset held the store')
            return real_commit(actor_ctx, case, before, entries)

        def writer():
            self.assertTrue(holding.wait(10), 'the reset never reached the store')
            attempted['writer'].set()
            try:
                store.commit(actor(session), session.case, stale, after)
                outcome.append('committed')
            except RetryPreparation:
                outcome.append('retry')

        def reader():
            self.assertTrue(holding.wait(10), 'the reset never reached the store')
            attempted['reader'].set()
            observed['snapshot'] = store.load(actor(session), session.case)
            read_done.set()

        store.commit = pausing_commit
        threads = [threading.Thread(target=writer, daemon=True),
                   threading.Thread(target=reader, daemon=True)]
        for thread in threads:
            thread.start()
        try:
            hosted.reset_session(store, identity, repository, session.uid)
        finally:
            store.commit = real_commit
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(['retry'], outcome)
        # The reader saw the complete reset state, never the half-reset case it would have
        # caught between the discard and the seed.
        self.assertEqual(pristine, observed['snapshot'].entries)
        self.assertNotIn(self.marker(), observed['snapshot'].entries)
        self.assertEqual(pristine, store.load(actor(session), session.case).entries)
        with self.assertRaises(AuthenticationFailed):
            identity.verify('Bearer ' + token)  # the completed reset rotated this session's token

    def test_a_failed_reset_puts_the_case_back_on_a_further_generation(self):
        session, token = self.open_session()
        store, repository = self.runtime.store, self.runtime.repository
        self.runtime.repository.commit_review(actor(session), self.review(session))
        before = store.load(actor(session), session.case)
        calls = []

        def fail():
            calls.append(1)
            raise StorageUnavailable()  # the re-seed's own commit: the case must be restored whole

        repository.before_commit = fail
        try:
            with self.assertRaises(hosted.SessionUnavailable):
                hosted.reset_session(store, self.runtime.identity, repository, session.uid)
        finally:
            repository.before_commit = None
        # PERF-2: the re-seed is one prepared batch, so the whole case is written in one
        # commit and this injection is that commit; the reset used to write it in three.
        self.assertEqual(1, len(calls))
        after = store.load(actor(session), session.case)
        self.assertEqual(before.entries, after.entries)
        self.assertGreater(after.generation, before.generation)
        with self.assertRaises(RetryPreparation):
            store.commit(actor(session), session.case, before, dict(before.entries))
        self.assertEqual(session.uid, self.runtime.identity.verify('Bearer ' + token))


class FakeDocument:
    def __init__(self, path):
        self.path = path


class FakeClient:
    def __init__(self):
        self.closed = 0

    def collection(self, name):
        return types.SimpleNamespace(document=lambda item: FakeDocument(f'{name}/{item}'))

    def close(self):
        self.closed += 1


def google_stub():
    """The two SDK names `hosted_store` reads at factory time, without the SDK."""
    api_core = types.ModuleType('google.api_core')
    api_core.__path__ = []
    exceptions = types.ModuleType('google.api_core.exceptions')

    class GoogleAPICallError(Exception):
        pass

    class RetryError(Exception):
        pass

    exceptions.GoogleAPICallError = GoogleAPICallError
    exceptions.RetryError = RetryError
    api_core.exceptions = exceptions
    google = types.ModuleType('google')
    google.__path__ = []
    google.api_core = api_core
    return {'google': google, 'google.api_core': api_core, 'google.api_core.exceptions': exceptions}


def firestore_stub():
    module = types.ModuleType('src.adapters.firestore')

    class FirestoreStore:
        def __init__(self, *args, **kwargs):
            raise AssertionError('the emulator constructor must not run in hosted mode')

        def case_ref(self, tenant, case):
            return ('case', tenant, case)

        def member_ref(self, uid, tenant, case):
            return ('member', uid, tenant, case)

        def membership(self, uid, tenant, case):
            return ('membership', uid, tenant, case)

        def load(self, actor, case):
            return ('load', actor.tenant_id, case)

        def commit(self, actor, case, before, after):
            return ('commit', actor.tenant_id, case)

        def close(self):
            return 'closed'

    module.FirestoreStore = FirestoreStore
    return module


class FailingStore:
    """A store whose provisioning write fails; the failure path must clean up and answer 503."""

    def __init__(self, discard_fails=False, delete_fails=False):
        self.discarded = []
        self.deleted = []
        self.discard_fails = discard_fails
        self.delete_fails = delete_fails

    def member_ref(self, uid, tenant, case):
        def set(mapping):
            raise ValueError('the store refused the provisioning write')

        def delete():
            self.deleted.append((uid, tenant, case))
            if self.delete_fails:
                raise RuntimeError('the membership rollback is unavailable')

        return types.SimpleNamespace(set=set, delete=delete)

    def discard_case(self, tenant, case):
        self.discarded.append((tenant, case))
        if self.discard_fails:
            raise RuntimeError('the cleanup itself is unavailable')


class AnonymousIdentity:
    """The hosted path's identity, stubbed: one anonymous uid and its token, no SDK."""

    def __init__(self, uid=FIREBASE_UID, token='anonymous-token'):
        self.uid, self.token = uid, token

    def anonymous_session(self):
        return self.token, self.uid


def discard_stub(entries=0):
    """A Firestore-shaped stub whose case ref holds `entries` documents and records deletes."""
    events = []

    class Reference:
        def __init__(self, path, children=()):
            self.path = path
            self.children = list(children)

        def collection(self, name):
            return types.SimpleNamespace(
                stream=lambda timeout=None: iter(types.SimpleNamespace(reference=child)
                                                 for child in self.children))

        def delete(self, timeout=None):
            events.append(('delete', self.path))

    class Batch:
        def delete(self, reference):
            events.append(('batch', reference.path))

        def commit(self):
            events.append(('commit',))

    class Client:
        def collection(self, name):
            return types.SimpleNamespace(document=lambda item: Reference(f'{name}/{item}'))

        def batch(self):
            return Batch()

    class FirestoreStore:
        def __init__(self, *args, **kwargs):
            raise AssertionError('the emulator constructor must not run in hosted mode')

        def case_ref(self, tenant, case):
            path = f'case/{tenant}/{case}'
            return Reference(path, [Reference(f'{path}/entries/{index}') for index in range(entries)])

    module = types.ModuleType('src.adapters.firestore')
    module.FirestoreStore = FirestoreStore
    return module, Client(), events


def firebase_stub(calls=None, claims=None):
    """The three module names the hosted identity imports, without the SDK."""
    root = types.ModuleType('firebase_admin')
    root.__path__ = []
    auth = types.ModuleType('firebase_admin.auth')
    exceptions = types.ModuleType('firebase_admin.exceptions')

    class FirebaseError(Exception):
        pass

    def verify_id_token(token, app=None, check_revoked=False):
        return dict(claims if claims is not None else ANONYMOUS_CLAIM)

    def initialize_app(options=None, **kwargs):
        if calls is not None:
            calls.append((options, kwargs))
        return types.SimpleNamespace(name='hosted-app')

    auth.verify_id_token = verify_id_token
    exceptions.FirebaseError = FirebaseError
    root.auth = auth
    root.exceptions = exceptions
    root.initialize_app = initialize_app
    return {'firebase_admin': root, 'firebase_admin.auth': auth, 'firebase_admin.exceptions': exceptions}


def httpx_stub(calls, status=200, data=None, fail=False):
    module = types.ModuleType('httpx')

    class HTTPError(Exception):
        pass

    class Response:
        status_code = status

        def json(self):
            return data or {}

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, json=None):
            calls.append((url, json, self.kwargs))
            if fail:
                raise HTTPError('unreachable')
            return Response()

    module.HTTPError = HTTPError
    module.Client = Client
    return module


class HostedAdapterTests(unittest.TestCase):
    def test_the_hosted_store_replaces_only_the_emulator_initialization(self):
        client = FakeClient()
        stub = firestore_stub()
        with patch.dict(sys.modules, dict(google_stub(), **{'src.adapters.firestore': stub})):
            store = hosted.hosted_store(PROJECT, 'demo-judge', client)
        self.assertEqual('h1_namespaces/demo-judge', store.root.path)
        self.assertIs(client, store.client)
        for name in ('load', 'commit', 'membership', 'case_ref', 'member_ref', 'close'):
            self.assertIs(getattr(stub.FirestoreStore, name), getattr(type(store), name), name)
        # The emulator store has no reset path, so the hosted store defines its own discard.
        self.assertIn('discard_case', type(store).__dict__)
        self.assertFalse(hasattr(stub.FirestoreStore, 'discard_case'))

    def test_the_hosted_store_discards_only_the_cases_own_documents(self):
        for entries, batches in ((0, 0), (3, 1), (hosted.DELETE_BATCH + 1, 2)):
            module, client, events = discard_stub(entries)
            with patch.dict(sys.modules, dict(google_stub(), **{'src.adapters.firestore': module})):
                store = hosted.hosted_store(PROJECT, 'demo-judge', client)
            store.discard_case(hosted.JUDGE_TENANT, 'demo-case-a')
            case = f'case/{hosted.JUDGE_TENANT}/demo-case-a'
            paths = [event[1] for event in events if event[0] in ('batch', 'delete')]
            self.assertEqual([f'{case}/entries/{index}' for index in range(entries)] + [case], paths, entries)
            self.assertEqual(batches, len([event for event in events if event[0] == 'commit']), entries)
            self.assertTrue(all(path.startswith(case) for path in paths))
            self.assertFalse(any('member' in path for path in paths))

    def test_the_namespace_store_discards_through_the_routed_namespace(self):
        calls = []
        private = types.SimpleNamespace(discard_case=lambda tenant, case: calls.append(('private', tenant, case)))
        judge = types.SimpleNamespace(discard_case=lambda tenant, case: calls.append(('judge', tenant, case)))
        store = hosted.NamespaceStore(private, judge)
        store.discard_case(hosted.JUDGE_TENANT, 'demo-case-a')
        store.discard_case('acme', 'private-case')
        self.assertEqual([('judge', hosted.JUDGE_TENANT, 'demo-case-a'), ('private', 'acme', 'private-case')],
                         calls)

    def test_the_hosted_identity_initializes_under_application_default_identity(self):
        calls = []
        with patch.dict(sys.modules, firebase_stub(calls=calls)):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
        self.assertEqual([(dict(projectId=PROJECT), {})], calls)
        self.assertIs(FirebaseIdentity.verify, type(identity).verify)
        self.assertIsNot(FirebaseIdentity.sign_in, type(identity).sign_in)
        source = (ROOT / 'src' / 'api' / 'hosted.py').read_text(encoding='utf-8')
        self.assertNotIn('AnonymousCredentials', source)
        self.assertNotIn('local_configuration(', source)

    def test_the_hosted_sign_in_posts_to_identity_toolkit_over_tls(self):
        # What the caller typed at runtime, in a variable: the release audit flags a
        # credential-shaped literal sitting next to a credential-like name.
        supplied = 'supplied-at-runtime'
        calls = []
        with patch.dict(sys.modules, dict(firebase_stub(), httpx=httpx_stub(calls, data={'idToken': 'issued-token'}))):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
            self.assertEqual(dict(id_token='issued-token'), identity.sign_in('analyst@example.test', supplied))
        url, body, kwargs = calls[0]
        self.assertEqual('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=public-web-key', url)
        self.assertTrue(url.startswith('https://'))
        self.assertEqual(dict(email='analyst@example.test', password=supplied, returnSecureToken=True), body)
        self.assertEqual(10, kwargs['timeout'])
        self.assertFalse(kwargs['trust_env'])
        self.assertNotIn(supplied, json.dumps(vars(identity), default=str))

    def test_hosted_sign_in_and_anonymous_sign_in_map_failures_without_downgrading(self):
        calls = []
        with patch.dict(sys.modules, dict(firebase_stub(), httpx=httpx_stub(calls, fail=True))):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
            with self.assertRaises(AuthenticationFailed):
                identity.sign_in('analyst@example.test', 'x' * 300)
            with self.assertRaises(StorageUnavailable):
                identity.sign_in('analyst@example.test', 'password')
            with self.assertRaises(hosted.SessionUnavailable):
                identity.anonymous_session()
        with patch.dict(sys.modules, dict(firebase_stub(), httpx=httpx_stub([], status=400))):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
            with self.assertRaises(AuthenticationFailed):
                identity.sign_in('analyst@example.test', 'password')
            with self.assertRaises(hosted.SessionUnavailable):
                identity.anonymous_session()
        with patch.dict(sys.modules, dict(firebase_stub(), httpx=httpx_stub([], data={'error': 'x'}))):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
            with self.assertRaises(hosted.SessionUnavailable):
                identity.anonymous_session()

    def test_an_anonymous_session_is_checked_against_the_verified_claim(self):
        calls = []
        issued = httpx_stub(calls, data={'idToken': 'anonymous-token', 'localId': FIREBASE_UID})
        with patch.dict(sys.modules, dict(firebase_stub(), httpx=issued)):
            identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
            self.assertEqual(('anonymous-token', FIREBASE_UID), identity.anonymous_session())
        self.assertTrue(calls[0][0].endswith('/accounts:signUp?key=public-web-key'))
        self.assertEqual(dict(returnSecureToken=True), calls[0][1])
        for claims in (dict(uid=FIREBASE_UID, firebase=dict(sign_in_provider='password')),
                       dict(uid='someone-else', firebase=dict(sign_in_provider='anonymous')),
                       dict(uid=FIREBASE_UID)):
            with patch.dict(sys.modules, dict(firebase_stub(claims=claims), httpx=issued)):
                identity = hosted.HostedFirebaseIdentity(PROJECT, 'public-web-key')
                with self.assertRaises(hosted.SessionUnavailable):
                    identity.anonymous_session()

    def test_the_namespace_store_routes_the_judge_tenant_to_the_demo_namespace(self):
        private, judge = types.SimpleNamespace(name='private'), types.SimpleNamespace(name='judge')
        store = hosted.NamespaceStore(private, judge)
        self.assertIs(judge, store._route(hosted.JUDGE_TENANT))
        self.assertIs(private, store._route('acme'))
        self.assertIs(private, store._route('demo-judge '))


_IGNORE_PATTERNS = {}


def dockerignore_keeps(entries, path):
    """True if Docker would put `path` in the build context under these `.dockerignore` lines.

    Docker matches every line against the path and against each of its parent directories, a `*`
    stops at a `/`, a leading `!` re-includes, and the last matching line wins
    (docs.docker.com/build/concepts/context). Reproduced here so the context contract can be
    checked over the real tree without a docker daemon. `[` is read literally: no path this
    check names depends on a character class.
    """
    keeps = True
    for entry in entries:
        pattern = entry[1:] if entry.startswith('!') else entry
        if pattern not in _IGNORE_PATTERNS:
            _IGNORE_PATTERNS[pattern] = _dockerignore_regex(pattern)
        if _IGNORE_PATTERNS[pattern].match(path):
            keeps = entry.startswith('!')
    return keeps


def _dockerignore_regex(pattern):
    expression, index = [], 0
    while index < len(pattern):
        if pattern.startswith('**/', index):
            expression.append('(?:.*/)?')
            index += 3
        elif pattern.startswith('**', index):
            expression.append('.*')
            index += 2
        elif pattern[index] == '*':
            expression.append('[^/]*')
            index += 1
        elif pattern[index] == '?':
            expression.append('[^/]')
            index += 1
        else:
            expression.append(re.escape(pattern[index]))
            index += 1
    # A pattern covers the path itself and everything under it.
    return re.compile('^' + ''.join(expression) + r'(?:/.*)?$')


class AgentWiringTests(unittest.TestCase):
    """DOCK-5: the desk agent's parts per mode and the service the assembly builds from them.

    Offline: no Firestore, no Firebase. A labelled fake client stands in for Firestore, and the
    service is read for the ports it was handed, never run against a service.
    """

    PLAN_BAKE = ROOT / 'tests' / 'fixtures' / 'grid' / 'catalog' / 'bake'

    class Collections:
        """Labelled fake of the Firestore client surface the agent store's constructor reads."""

        def __init__(self):
            self.paths = []

        def collection(self, name):
            self.paths.append(name)
            return self

        def document(self, name):
            self.paths.append(name)
            return self

    def test_demo_mode_keeps_the_agent_in_process_with_no_session_cookie(self):
        from src.agent.store import MemoryAgentStore
        runtime = hosted.demo_runtime({})
        self.assertIsInstance(runtime.agent.store, MemoryAgentStore)
        self.assertFalse(runtime.agent.sessions.available)
        self.assertTrue(runtime.agent.demonstration)
        self.assertIs(runtime.alerts.users, runtime.agent.sessions.users)

    def test_hosted_mode_uses_the_private_namespace_and_the_firebase_session(self):
        from src.agent.store import FirestoreAgentStore
        settings = hosted.Settings(hosted.HOSTED_MODE, project='p', web_api_key='k', namespace='nowcast-private')
        client = self.Collections()
        alerts = hosted.AlertsWiring(None, types.SimpleNamespace(editors=()), None)
        agent = hosted.hosted_agent(settings, client, types.SimpleNamespace(app=object()), alerts,
                                    {'NOWCAST_PUBLIC_URL': 'https://example.test/'})
        self.assertIsInstance(agent.store, FirestoreAgentStore)
        self.assertEqual(['h1_namespaces', 'nowcast-private'], client.paths)
        self.assertTrue(agent.sessions.available)
        self.assertEqual('https://example.test', agent.sessions.origins[0])
        self.assertIn('https://grid-nowcast.web.app', agent.sessions.origins)
        self.assertFalse(agent.demonstration)
        self.assertIsNone(agent.archive)

    def test_the_service_is_built_from_the_bake_s_plan_sets_the_book_and_the_site_routes(self):
        from src.book.adapter import BookAdapter
        from src.judgment.actions import SITE_ROUTES
        service = hosted.agent_service(hosted.demo_runtime({}), self.PLAN_BAKE)
        self.assertEqual(tuple(SITE_ROUTES), service.site_routes)
        self.assertIn('/book', service.site_routes)
        self.assertIsInstance(service.book, BookAdapter)
        self.assertIsNone(service.live_backend, 'no live planner: the day meter is never charged here')
        self.assertIsNone(service.decision_writer, 'no review actor is mapped for an agent owner')
        self.assertEqual('What is exposed?', service.recorded_answers('desk', 'home')[2]['question'])
        self.assertEqual(service.recorded_answers('desk', 'home')[0]['cutoff'], service.cutoff_for('desk', 'home'))
        self.assertIn('ACC-VIS01', service.caller_ids(None, 'desk', 'home')['accounts'])
        answer = service.ask(None, {'question': 'What is exposed?', 'page_key': 'home'})
        self.assertEqual('composed', answer['view']['status'])
        self.assertFalse(answer['signed_in'])

    def test_the_book_is_read_from_the_bake_when_it_carries_one(self):
        book_adapter = hosted.book_adapter
        with tempfile.TemporaryDirectory(prefix='dock5-book-') as temp:
            (Path(temp) / 'book').mkdir()
            index = json.loads((ROOT / 'tests' / 'fixtures' / 'grid' / 'book' / 'bake' / 'book' / 'index.json')
                               .read_text(encoding='utf-8'))
            (Path(temp) / 'book' / 'index.json').write_text(json.dumps(index), encoding='utf-8')
            adapter = book_adapter(temp, archive_root=Path(temp) / 'no-archive')
            self.assertEqual(index['book']['content_digest'], adapter.book['content_digest'])
            self.assertEqual([], adapter.vintages() if (Path(temp) / 'no-archive').is_dir() else [])
            refused = adapter.impact(['ACC-VIS01'], 'book-demo-2026-10-19-cvis', '2026-10-19T13:00/2026-10-19T15:00',
                                     '2026-10-18T15:00:00Z')
            self.assertEqual('refused', refused['status'], 'no vintage archive in the image: refused, never raised')

    def test_the_session_cookie_is_firebase_s_own_session_cookie_read_with_revocation(self):
        from src.agent.session import AgentSessions
        calls = []
        auth = types.SimpleNamespace(
            create_session_cookie=lambda token, expires_in, app: calls.append(('mint', token, expires_in, app)) or 'c.j.w',
            verify_session_cookie=lambda cookie, check_revoked, app: calls.append(('read', cookie, check_revoked, app))
            or {'uid': 'u', 'email': 'sam@example.com', 'email_verified': True,
                'firebase': {'sign_in_provider': 'google.com'}})
        app = object()
        module = types.ModuleType('firebase_admin')
        module.auth = auth
        users = types.SimpleNamespace(editors=(), user=lambda authorization: {'uid': 'u', 'email': 'sam@example.com',
                                                                             'provider': 'google.com'})
        with patch.dict(sys.modules, {'firebase_admin': module}):
            sessions = hosted.firebase_sessions(AgentSessions, users, app, ('https://grid-nowcast.web.app',))
            cookie, user = sessions.mint('an-id-token')
            seen = sessions.user(types.SimpleNamespace(headers={'cookie': '__session=c.j.w'}))
        self.assertEqual('c.j.w', cookie)
        self.assertEqual(('mint', 'an-id-token', timedelta(seconds=432000), app), calls[0])
        self.assertEqual(('read', 'c.j.w', True, app), calls[1])
        self.assertEqual('sam@example.com', seen['email'])

    def test_the_outlook_write_inputs_come_only_from_the_two_named_settings(self):
        self.assertEqual((None, None), hosted._agent_outlook_inputs({}))
        with tempfile.TemporaryDirectory(prefix='dock5-archive-') as temp:
            register = Path(temp) / 'register.json'
            register.write_text('{"assumptions": []}', encoding='utf-8')
            archive, payload = hosted._agent_outlook_inputs({'NOWCAST_AGENT_OUTLOOK_ARCHIVE': temp,
                                                             'NOWCAST_AGENT_REGISTER': str(register)})
            self.assertEqual(temp, str(archive.root))
            self.assertEqual({'assumptions': []}, payload)


class ImageContractTests(unittest.TestCase):
    def setUp(self):
        self.dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
        self.ignored = (ROOT / '.dockerignore').read_text(encoding='utf-8')

    def test_the_base_is_the_interpreter_the_lock_was_verified_on(self):
        from_lines = [line for line in self.dockerfile.splitlines() if line.startswith('FROM ')]
        self.assertEqual(1, len(from_lines))
        self.assertIn('python:3.14.4', from_lines[0])

    def test_the_image_copies_only_the_lock_the_application_the_grid_snapshot_and_the_permissions(self):
        # GRID-1 added `build/grid-data` (the baked grid replay, company WESM data under
        # permission record version 2: it ships inside the image only, is never committed and
        # is excluded from the public export). `docs/work/permissions` joined with GRID-3: a judge
        # session seeds a copy of the real PEDC event case, and every real record must cite a
        # permission the registry holds. The reviewed set stays closed: a new COPY source fails
        # here until it is reviewed.
        sources = [line.split()[1] for line in self.dockerfile.splitlines() if line.startswith('COPY ')]
        self.assertEqual({'requirements/h1.lock', 'src', 'build/grid-data', 'docs/work/permissions'}, set(sources))
        self.assertEqual([], [line for line in self.dockerfile.splitlines()
                              if line.startswith('ADD ')], 'the image copies nothing by URL or archive')

    def test_the_image_carries_the_signed_permission_registry(self):
        self.assertIn('COPY docs/work/permissions ./docs/work/permissions', self.dockerfile)
        from src.review.repository import DEFAULT_PERMISSIONS
        self.assertIn('perm:wesm-company-copy:2026-10-13', DEFAULT_PERMISSIONS)

    def test_the_entry_point_is_the_hosted_factory_without_an_access_log(self):
        self.assertIn('src.api.hosted:app --factory --host 0.0.0.0 --port ${PORT:-8080} --no-access-log',
                      self.dockerfile)
        self.assertIn('USER nowcast', self.dockerfile)
        self.assertNotIn('USER root', self.dockerfile)

    def test_no_mode_or_secret_is_baked_into_the_image(self):
        instructions = [line for line in self.dockerfile.splitlines() if re.match(r'\s*(ENV|ARG)\s', line)]
        self.assertFalse([line for line in instructions if 'NOWCAST_ENV' in line])
        self.assertIsNone(re.search(r'(?i)\b(secret|password|token|api_key|apikey|credential)\s*=\s*\S',
                                    self.dockerfile))

    def test_the_container_walkthrough_runner_keeps_the_container_contract(self):
        runner = (ROOT / 'scripts' / 'deploy' / 'walkthrough.sh').read_text(encoding='utf-8')
        program = (ROOT / 'scripts' / 'deploy' / 'walkthrough.py').read_text(encoding='utf-8')
        compile(program, 'walkthrough.py', 'exec')  # the program the runner drives must parse
        for needle in ('docker build', '--read-only', '--tmpfs /tmp', 'walkthrough.py'):
            self.assertIn(needle, runner)
        self.assertIn('/usr/bin/python3', runner)
        self.assertIn('/health', program)

    def test_the_build_context_excludes_local_state_and_material(self):
        entries = {line.strip() for line in self.ignored.splitlines() if line.strip() and not line.startswith('#')}
        for needle in ('.git', '.local', '.env', '.env.*', 'node_modules', '**/__pycache__', '*.pem', '*.key',
                       '*.tar.gz', 'venv'):
            self.assertIn(needle, entries)

    def test_the_build_context_re_includes_exactly_the_permission_records_the_image_copies(self):
        # `docs` is excluded and the image copies docs/work/permissions, so the context must
        # re-include that one path: without the line the build failed with
        # `"/docs/work/permissions": not found` (orchestrator finding, 2026-10-14). Every other
        # docs path stays out, and the exclusion of local state and secret-shaped names survives.
        entries = [line.strip() for line in self.ignored.splitlines()
                   if line.strip() and not line.startswith('#')]
        copied = [line.split()[1] for line in self.dockerfile.splitlines() if line.startswith('COPY docs/')]
        self.assertEqual(['docs/work/permissions'], copied)
        negations = [entry for entry in entries if entry.startswith('!')]
        self.assertEqual(['!' + source for source in copied], negations)
        self.assertLess(entries.index('docs'), entries.index(negations[0]))
        for source in copied:
            self.assertTrue(dockerignore_keeps(entries, source), source)

        registry = ROOT / 'docs' / 'work' / 'permissions'
        held = sorted(path.relative_to(ROOT).as_posix() for path in registry.rglob('*'))
        self.assertTrue(held, 'the registry must hold the signed record the image copies')
        self.assertEqual(held, [path for path in held if dockerignore_keeps(entries, path)])
        elsewhere = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / 'docs').rglob('*')
                           if path.is_file() and registry not in path.parents)
        self.assertGreater(len(elsewhere), 200)
        self.assertEqual([], [path for path in elsewhere if dockerignore_keeps(entries, path)])

        for path in ('requirements/h1.lock', 'src/api/hosted.py'):
            self.assertTrue(dockerignore_keeps(entries, path), path)
        for path in ('.git/config', '.local/h1-venv/bin/python', 'venv/lib/site-packages/x.py',
                     'node_modules/left-pad/index.js', 'archive/scan.pdf', 'experiments/notes.md',
                     '.env', '.env.production', 'service-account.json.key', 'private.pem',
                     'run.log', 'bundle.tar.gz', '.DS_Store'):
            self.assertFalse(dockerignore_keeps(entries, path), path)


class HealthBodyTests(unittest.TestCase):
    """DATA-2: the hosted `/health` names the bake the image serves, SDK-free.

    The route itself is exercised under FastAPI in HTTPContractTests; the body is a pure function
    of the mode, the stamp the application derives and the baked manifest, read once.
    """

    def test_the_host_1_keys_stay_and_the_stamp_and_replay_span_are_added(self):
        manifest = {'schema': 'bake-manifest/1', 'stamp': 'ffffffffffffffff',
                    'replay': {'first': '2026-09-21T00:00', 'last': '2026-09-29T23:55', 'days': 8,
                               'missing': ['2026-09-25'], 'node_days': ['2026-09-21']}}
        self.assertEqual({'status': 'ok', 'mode': 'hosted', 'storage_checked': False,
                          'stamp': '0123456789abcdef',
                          'replay': {'first': '2026-09-21T00:00', 'last': '2026-09-29T23:55',
                                     'days': 8}},
                         hosted.health_body('hosted', '0123456789abcdef', manifest))

    def test_an_absent_or_broken_manifest_gives_null_replay_fields_never_an_error(self):
        nulls = {'first': None, 'last': None, 'days': None}
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(hosted.read_bake_manifest(directory))
            self.assertIsNone(hosted.read_bake_manifest(Path(directory) / 'nowhere'))
            (Path(directory) / 'manifest.json').write_text('not json', encoding='utf-8')
            self.assertIsNone(hosted.read_bake_manifest(directory))
            (Path(directory) / 'manifest.json').write_text('[1, 2]', encoding='utf-8')
            self.assertIsNone(hosted.read_bake_manifest(directory))
            body = {'replay': {'first': 'a', 'last': 'b', 'days': 3}}
            (Path(directory) / 'manifest.json').write_text(json.dumps(body), encoding='utf-8')
            self.assertEqual(body, hosted.read_bake_manifest(directory))
        for manifest in (None, {}, {'replay': None}, {'replay': 'x'}):
            self.assertEqual(nulls, hosted.health_body('demo', 'abc', manifest)['replay'])
        self.assertEqual({'status': 'ok', 'mode': 'demo', 'storage_checked': False,
                          'stamp': None, 'replay': nulls}, hosted.health_body('demo'))

    def test_the_assembly_reads_the_manifest_from_the_served_data_directory(self):
        source = (ROOT / 'src' / 'api' / 'hosted.py').read_text(encoding='utf-8')
        self.assertIn("_replace_health(application, runtime.settings.mode, build_stamp(grid_data_directory()),\n"
                      "                    read_bake_manifest(grid_data_directory()))", source)


@unittest.skipUnless(FASTAPI, 'FastAPI is not installed for this interpreter; run in the container '
                              'image or with .local/h1-venv/bin/python')
class HTTPContractTests(DemoCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(self.runtime.application())
        self.addCleanup(self.client.close)

    def open_over_http(self):
        response = self.client.post('/demo/session')
        self.assertEqual(200, response.status_code, response.text)
        payload = response.json()
        uid = self.runtime.identity.verify('Bearer ' + payload['id_token'])
        return (hosted.Session(uid, payload['tenant'], payload['case']), payload,
                {'authorization': 'Bearer ' + payload['id_token']})

    def url(self, session):
        return f'/v1/tenants/{session.tenant}/cases/{session.case}'

    def body(self, session, key='review-a'):
        request = self.review(session, key)
        return {k: v for k, v in request.items() if k not in ('case_id', 'recorded_at', 'reviewed_at')}

    def test_the_demo_app_builds_with_an_empty_environment_and_reports_its_mode(self):
        with patch.dict(os.environ, dict(), clear=True):
            application = hosted.demo_application()
        client = TestClient(application)
        self.addCleanup(client.close)
        health = client.get('/health').json()
        # DATA-2: the HOST-1 keys are unchanged and the bake this image serves is added — the
        # stamp every page names (asserted against the page's own meta below) and the baked
        # manifest's replay span (null fields when the data directory holds no manifest).
        from src.api import grid_data_directory
        manifest = hosted.read_bake_manifest(grid_data_directory())
        replay = (manifest or {}).get('replay') or {}
        self.assertEqual({'status': 'ok', 'mode': 'demo', 'storage_checked': False,
                          'stamp': health['stamp'],
                          'replay': {key: replay.get(key) for key in ('first', 'last', 'days')}},
                         health)
        # GRID-2: `/` is the public grid desk and the change desk it replaced is at `/desk`. The
        # baked replay files are not asserted here — they live in the image (GRID-1 bakes them
        # and the Dockerfile copies them in), and scripts/deploy/walkthrough.py checks them on
        # the container port.
        page = client.get('/')
        self.assertEqual(200, page.status_code)
        self.assertIn('InGRID · Philippine grid', page.text)
        desk = client.get('/desk')
        self.assertEqual(200, desk.status_code)
        self.assertIn('SYNTHETIC WALKTHROUGH', desk.text)
        self.assertEqual(200, client.get('/grid/grid.js').status_code)
        self.assertEqual('text/javascript', client.get('/grid/grid.js').headers['content-type'].split(';')[0])
        self.assertEqual(404, client.get('/grid/server.py').status_code)
        self.assertEqual(200, client.get('/favicon.ico').status_code)  # InGRID brand: the real icon
        self.assertEqual(200, client.get('/assets/app.js').status_code)
        # PERF-1: the page revalidates and names its own build; the versioned files under that
        # stamp are immutable, the unversioned names are never cached, and an unknown stamp is
        # a 404 rather than a fallback to whatever the process currently serves.
        self.assertEqual('no-cache', client.get('/').headers['cache-control'])
        stamp = re.search(r'id="nowcast-build"[^>]*content="([0-9a-f]{16})"', page.text).group(1)
        self.assertEqual(stamp, health['stamp'], 'DATA-2: /health names the stamp the page carries')
        versioned = client.get(f'/grid/{stamp}/grid.js')
        self.assertEqual(200, versioned.status_code)
        self.assertEqual('public, max-age=31536000, immutable',
                         versioned.headers['cache-control'])
        self.assertEqual('no-store', client.get('/grid/grid.js').headers['cache-control'])
        self.assertEqual('no-store', client.get('/health').headers['cache-control'])
        self.assertEqual(404, client.get(f'/grid-data/{"0" * 16}/regions.json').status_code)

    def test_the_local_health_response_is_unchanged(self):
        from src.api import create_app
        from src.review.storage import PersistentRepository
        local = TestClient(create_app(PersistentRepository(hosted.MemoryStore()), object()))
        self.addCleanup(local.close)
        self.assertEqual({'status': 'ok', 'mode': 'local', 'storage_checked': False}, local.get('/health').json())

    def test_two_sessions_reach_their_own_case_and_nothing_else(self):
        first, first_payload, first_headers = self.open_over_http()
        second, second_payload, second_headers = self.open_over_http()
        self.assertEqual('demo', first_payload['mode'])
        self.assertEqual(hosted.JUDGE_TENANT, first_payload['tenant'])
        self.assertEqual(self.runtime.digest, first_payload['fixture_digest'])
        self.assertEqual(first_payload['fixture_digest'], second_payload['fixture_digest'])
        self.assertNotEqual(first.case, second.case)
        # GRID-3: every judge session also carries its own copy of the real PEDC event case,
        # named by the session answer, and reaches it with the same token.
        for payload, session in ((first_payload, first), (second_payload, second)):
            self.assertEqual(hosted.event_case(session.uid), payload['event_case'])
            self.assertNotEqual(payload['case'], payload['event_case'])
            self.assertTrue(payload['event_seeded_at'])
        self.assertEqual(200, self.client.get(
            f'/v1/tenants/{first.tenant}/cases/{first_payload["event_case"]}', headers=first_headers).status_code)
        self.assertEqual(404, self.client.get(
            f'/v1/tenants/{second.tenant}/cases/{first_payload["event_case"]}', headers=second_headers).status_code)
        for session, headers in ((first, first_headers), (second, second_headers)):
            self.assertEqual(200, self.client.get(self.url(session), headers=headers).status_code)
            self.assertEqual(200, self.client.get(self.url(session) + '/workspace', headers=headers).status_code)
        for headers, other in ((first_headers, second), (second_headers, first)):
            denied = self.client.get(self.url(other), headers=headers)
            self.assertEqual((404, {'code': 'NOT_FOUND'}), (denied.status_code, denied.json()))
        private = self.client.get(f'/v1/tenants/{hosted.TENANT}/cases/{hosted.CASE}', headers=first_headers)
        self.assertEqual((404, {'code': 'NOT_FOUND'}), (private.status_code, private.json()))
        self.assertEqual(401, self.client.get(self.url(first)).status_code)
        self.assertEqual(401, self.client.get(self.url(first), headers={'authorization': 'Bearer unknown'}).status_code)

    def test_a_review_saves_on_the_callers_case_only(self):
        first, _, first_headers = self.open_over_http()
        second, _, second_headers = self.open_over_http()
        body = self.body(first)
        saved = self.client.post(self.url(first) + '/reviews', json=body, headers=first_headers)
        self.assertEqual(200, saved.status_code, saved.text)
        self.assertEqual(1, len(self.client.get(self.url(first) + '/history', headers=first_headers).json()))
        self.assertEqual([], self.client.get(self.url(second) + '/history', headers=second_headers).json())
        elsewhere = self.client.post(self.url(second) + '/reviews', json=body, headers=second_headers)
        self.assertEqual(404, elsewhere.status_code)

    def test_a_full_sandbox_refuses_a_new_session_with_503_and_keeps_the_live_one(self):
        runtime = self.capped(1)
        client = TestClient(runtime.application())
        self.addCleanup(client.close)
        opened = client.post('/demo/session')
        self.assertEqual(200, opened.status_code, opened.text)
        payload = opened.json()
        refused = client.post('/demo/session')
        self.assertEqual((503, {'code': 'SESSION_UNAVAILABLE'}), (refused.status_code, refused.json()))
        headers = {'authorization': 'Bearer ' + payload['id_token']}
        live = client.get(f'/v1/tenants/{payload["tenant"]}/cases/{payload["case"]}', headers=headers)
        self.assertEqual(200, live.status_code, live.text)

    def test_a_client_supplied_tenant_case_or_uid_changes_nothing(self):
        injected = dict(tenant='demo-judge', case='demo-0000000000000000', uid='client-supplied-uid')
        payload = self.client.post('/demo/session', json=injected).json()
        self.assertEqual(hosted.JUDGE_TENANT, payload['tenant'])
        self.assertNotEqual(injected['case'], payload['case'])
        self.assertNotEqual(injected['uid'], self.runtime.identity.verify('Bearer ' + payload['id_token']))
        self.assertIsNone(self.runtime.store.membership(injected['uid'], hosted.JUDGE_TENANT, payload['case']))

    def test_reset_requires_the_callers_own_token_and_is_session_local(self):
        first, first_payload, first_headers = self.open_over_http()
        second, _, second_headers = self.open_over_http()
        first_saved = self.client.post(self.url(first) + '/reviews', json=self.body(first), headers=first_headers)
        self.assertEqual(200, first_saved.status_code, first_saved.text)
        second_saved = self.client.post(self.url(second) + '/reviews',
                                        json=self.body(second, key='review-b'), headers=second_headers)
        self.assertEqual(200, second_saved.status_code, second_saved.text)
        self.assertEqual(401, self.client.post('/demo/reset').status_code)
        self.assertEqual(401, self.client.post('/demo/reset', headers={'authorization': 'Bearer unknown'}).status_code)
        reset = self.client.post('/demo/reset', headers=first_headers)
        self.assertEqual(200, reset.status_code, reset.text)
        self.assertEqual(dict(reset=True, id_token=reset.json()['id_token'], mode='demo',
                              tenant=first_payload['tenant'], case=first_payload['case'],
                              fixture_digest=first_payload['fixture_digest']), reset.json())
        self.assertEqual(401, self.client.get(self.url(first), headers=first_headers).status_code)
        self.assertEqual(401, self.client.post(self.url(first) + '/reviews', json=self.body(first),
                                               headers=first_headers).status_code)
        fresh = {'authorization': 'Bearer ' + reset.json()['id_token']}
        self.assertEqual(200, self.client.get(self.url(first), headers=fresh).status_code)
        self.assertEqual([], self.client.get(self.url(first) + '/history', headers=fresh).json())
        self.assertEqual(200, self.client.get(self.url(second), headers=second_headers).status_code)
        self.assertEqual(second_saved.json(),
                         self.client.get(self.url(second) + '/receipts/review-b', headers=second_headers).json())


CLEANUP_SPEC = importlib.util.spec_from_file_location('nowcast_cleanup',
                                                      ROOT / 'scripts' / 'deploy' / 'cleanup.py')
cleanup = importlib.util.module_from_spec(CLEANUP_SPEC)
CLEANUP_SPEC.loader.exec_module(cleanup)


def index_manifest(platform, single=False, entries=None):
    """The manifest a push resolves to, as `docker buildx imagetools inspect --raw` prints it.

    An OCI image *index* carries the linux/amd64 manifest a Cloud Run revision runs and, first
    in the list, the provenance attestation manifest — the shape the POC release's push had, and
    the reason a resolver that took the first entry would compare the wrong digest. A
    single-platform push is a plain manifest instead. `entries` replaces the list for the
    degenerate indexes a push should never resolve to.
    """
    if single:
        return {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                'config': {'mediaType': 'application/vnd.oci.image.config.v1+json',
                           'digest': 'sha256:synthetic-config-digest', 'size': 100},
                'layers': []}
    return {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json',
            'manifests': [
                {'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                 'digest': 'sha256:synthetic-attestation-digest', 'size': 583,
                 'platform': {'architecture': 'unknown', 'os': 'unknown'}},
                {'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                 'digest': platform, 'size': 1024,
                 'platform': {'architecture': 'amd64', 'os': 'linux'}},
            ] if entries is None else entries}


PLATFORM_SPEC = importlib.util.spec_from_file_location(
    'nowcast_platform_digest', ROOT / 'scripts' / 'deploy' / 'platform_digest.py')
platform_digest = importlib.util.module_from_spec(PLATFORM_SPEC)
PLATFORM_SPEC.loader.exec_module(platform_digest)


class PlatformDigestTests(unittest.TestCase):
    """HOST-4: the digest a revision is compared against is the linux/amd64 manifest.

    Artifact Registry reports the image *index* digest for a pushed tag while Cloud Run records
    the platform manifest it runs — two digests for the same push (orchestrator evidence,
    2026-10-14) — so `deploy.sh` pipes `docker buildx imagetools inspect --raw` through
    [scripts/deploy/platform_digest.py](../../scripts/deploy/platform_digest.py) before comparing.
    An index with no readable linux/amd64 manifest is refused there, so an empty answer always
    means a plain manifest — never an unresolved platform identity.
    """

    def resolve(self, manifest=None, text=None):
        out, err = io.StringIO(), io.StringIO()
        code = platform_digest.main(io.StringIO(json.dumps(manifest) if text is None else text),
                                    out, err)
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_the_linux_amd64_manifest_is_selected_by_platform_and_not_by_position(self):
        code, out, err = self.resolve(index_manifest('sha256:synthetic-platform-digest'))
        self.assertEqual((0, 'sha256:synthetic-platform-digest', ''), (code, out, err))

    def test_a_plain_manifest_resolves_to_nothing_and_the_registry_digest_stands(self):
        self.assertEqual((0, '', ''), self.resolve(index_manifest(None, single=True)))

    def test_an_index_without_a_linux_amd64_manifest_is_refused(self):
        """An index that lists no linux/amd64 manifest cannot say what Cloud Run would run, so
        the resolver exits non-zero with what it read. An empty answer is a plain manifest, not
        this: letting the two share it substituted the index digest for a platform identity the
        release never established (review finding, 2026-10-14)."""
        manifest = {'manifests': [{'digest': 'sha256:arm', 'platform': {'os': 'linux',
                                                                       'architecture': 'arm64'}}]}
        code, out, err = self.resolve(manifest)
        self.assertEqual((1, ''), (code, out))
        self.assertIn('no linux/amd64 manifest digest in the image index', err)
        self.assertIn('manifests: linux/arm64', err)

    def test_an_amd64_entry_without_a_usable_digest_is_refused(self):
        """The linux/amd64 entry has to carry a digest to be one; a blank, absent or malformed
        one leaves the platform identity unresolved exactly as an absent entry does."""
        for digest in ('', None, 'sha256:', 'not-a-digest'):
            manifest = {'manifests': [{'digest': digest,
                                       'platform': {'os': 'linux', 'architecture': 'amd64'}}]}
            code, out, err = self.resolve(manifest)
            self.assertEqual(1, code, digest)
            self.assertEqual('', out, digest)
            self.assertIn('linux/amd64 without a digest', err, digest)

    def test_an_index_that_states_no_manifest_list_is_refused(self):
        """An index media type with nothing usable behind it is still an index: it must not pass
        for a plain manifest and let the registry's index digest compare as the platform one."""
        for manifest in (index_manifest('sha256:synthetic-platform-digest', entries=[]),
                         {'mediaType': 'application/vnd.oci.image.index.v1+json'},
                         {'manifests': 'not a list'}):
            code, out, err = self.resolve(manifest)
            self.assertEqual(1, code, manifest)
            self.assertEqual('', out, manifest)
            self.assertIn('no linux/amd64 manifest digest in the image index', err, manifest)

    def test_anything_that_is_not_a_manifest_object_is_refused(self):
        for text in ('', '   ', 'not a manifest', '[]', '"sha256:digest"', 'null'):
            code, out, err = self.resolve(text=text)
            self.assertEqual(1, code, text)
            self.assertEqual('', out, text)
            self.assertIn('not a manifest', err, text)


class ReadStampTests(unittest.TestCase):
    """DATA-2: scripts/deploy/read_stamp.py reads the stamp each half of the site names, and fails
    closed — exit 1 with the reason — on anything that names none."""

    TOOL = ROOT / 'scripts' / 'deploy' / 'read_stamp.py'

    def read(self, *args, stdin=''):
        return subprocess.run([sys.executable, str(self.TOOL), *args], input=stdin,
                              capture_output=True, text=True)

    def test_the_three_sources(self):
        stamp = '0123456789abcdef'
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'firebase.json'
            config.write_text(json.dumps({'hosting': {'headers': [
                {'source': f'/grid-data/{stamp}/**', 'headers': []},
                {'source': f'/grid/{stamp}/**', 'headers': []},
                {'source': '/', 'headers': []}]}}), encoding='utf-8')
            result = self.read('config', str(config))
            self.assertEqual((0, stamp + '\n'), (result.returncode, result.stdout), result.stderr)
            config.write_text(json.dumps({'hosting': {'headers': [
                {'source': f'/grid-data/{stamp}/**'},
                {'source': '/grid/fedcba9876543210/**'}]}}), encoding='utf-8')
            self.assertEqual(1, self.read('config', str(config)).returncode, 'two stamps')
        result = self.read('health', stdin=json.dumps({'status': 'ok', 'stamp': stamp}))
        self.assertEqual((0, stamp + '\n'), (result.returncode, result.stdout))
        page = f'<head><meta id="nowcast-build" name="nowcast-build" content="{stamp}"></head>'
        result = self.read('page', stdin=page)
        self.assertEqual((0, stamp + '\n'), (result.returncode, result.stdout))

    def test_anything_without_a_stamp_fails_closed(self):
        for args, stdin in ((('health',), '{}'), (('health',), '{"stamp": null}'),
                            (('health',), 'not json'), (('health',), '{"stamp": "__NOWCAST_STAMP__"}'),
                            (('page',), '<meta id="nowcast-build" content="__NOWCAST_STAMP__">'),
                            (('page',), '<html></html>'), (('config', '/nonexistent/x.json'), '')):
            with self.subTest(args=args, stdin=stdin):
                result = self.read(*args, stdin=stdin)
                self.assertEqual(1, result.returncode)
                self.assertEqual('', result.stdout)
                self.assertTrue(result.stderr.startswith('read_stamp.py: '), result.stderr)
        self.assertEqual(2, self.read('stamp').returncode)


DEPLOY_SCRIPT = ROOT / 'scripts' / 'deploy' / 'deploy.sh'


@unittest.skipUnless(DEPLOY_SCRIPT.exists(), 'scripts/deploy/deploy.sh is withheld from the public export')
class DeployScriptTests(unittest.TestCase):
    """H2a: the deploy script prints every command in a dry run, and runs none of them.

    The dry run is the offline check the intent requires; the real push, deploy and Hosting
    release are the orchestrator's steps, recorded in docs/work/hosting/implementation.md.
    """

    SCRIPT = ROOT / 'scripts' / 'deploy' / 'deploy.sh'

    # deploy.sh's default REMOTE_IMAGE (region asia-southeast1, project grid-nowcast,
    # repository grid-nowcast, service grid-nowcast): the repository a release pushes
    # to, and therefore the only image name a full `status.imageDigest` reference may
    # carry. The stubbed release answers that reference — the pushed repository with
    # the platform digest — rather than a duplicated literal, and the refusal tests
    # present other names so the comparison is exercised (review finding, 2026-10-14).
    REGISTRY = 'asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast'
    REMOTE_IMAGE = REGISTRY + '/grid-nowcast'

    @classmethod
    def setUpClass(cls):
        # DATA-2: a release refuses a bake without build_all.py's manifest, so the dry runs read
        # a baked copy of the synthetic replay fixture (manifest included) through GRID_DATA
        # instead of the work tree's build/grid-data, which a checkout need not hold.
        cls.BAKE_ROOT = Path(tempfile.mkdtemp(prefix='data2-deploy-'))
        cls.addClassCleanup(shutil.rmtree, cls.BAKE_ROOT, ignore_errors=True)
        cls.BAKED = baked_copy(cls.STAGE_FIXTURE, cls.BAKE_ROOT / 'grid-data')

    def run_script(self, *args, path=None, extra=None, env=None):
        # DATA-2: GRID_DATA names the baked fixture copy unless a test's own env says otherwise.
        environ = env if env is not None else dict(os.environ, GRID_DATA=str(self.BAKED))
        if path is not None or extra is not None:
            environ = dict(environ, **(extra or {}))
            if path is not None:
                environ['PATH'] = path
        return subprocess.run(['bash', str(self.SCRIPT), *args], cwd=ROOT,
                              capture_output=True, text=True, env=environ)

    def stub_tools(self, directory):
        """docker/gcloud/firebase/curl stubs: any execution of one is recorded and exits 99."""
        marker = Path(directory) / 'executed.txt'
        for name in ('docker', 'gcloud', 'firebase', 'curl'):
            binary = Path(directory) / name
            binary.write_text(f'#!/bin/sh\necho "$0 $*" >> "{marker}"\nexit 99\n', encoding='utf-8')
            binary.chmod(0o755)
        return marker

    def stub_release(self, directory, deployed, served, percent=100,
                     index='sha256:synthetic-index-digest',
                     platform='sha256:synthetic-platform-digest', revision_digest=None,
                     ready='True', ready_message='', conditions=True, single_manifest=False,
                     raw_manifest=None, pinned='grid-nowcast-00001-old'):
        """A release's tools, stubbed.

        gcloud answers the registry with the digest the tag resolves to (`index`, an image index
        as Artifact Registry reports one), the deploy with the revision it created (`deployed`),
        that revision's own Ready condition with `ready` and its message with `ready_message`
        (no condition at all when `conditions` is false), the revision's image digest with
        `revision_digest` (default: the pushed repository's full reference,
        `REMOTE_IMAGE@platform`, the linux/amd64 manifest behind the index), the
        service's traffic with `served` at `percent`, and the service's ready-revision field
        with `pinned` — the revision a rollback left the traffic on. A release that still read
        that field rather than the revision's own condition follows the pinned revision, and the
        recorded calls show it. docker answers the index resolution with `raw_manifest` (default:
        `platform`'s manifest, a plain manifest when `single_manifest`). Every call is recorded.
        """
        marker = Path(directory) / 'executed.txt'
        revision_digest = (f'{self.REMOTE_IMAGE}@{platform}'
                           if revision_digest is None else revision_digest)
        state = ready if conditions else ''
        manifest = raw_manifest if raw_manifest is not None else json.dumps(
            index_manifest(platform, single=single_manifest))
        bodies = {
            'docker': f'''case "$*" in
  *"imagetools inspect"*) printf '%s\\n' '{manifest}' ;;
esac
exit 0
''',
            'firebase': 'exit 0',
            # DATA-2: the service and the site answer with the stamp the stager wrote into the
            # generated config (read with grep, not with the release's own reader), unless a test
            # sets STUB_SERVICE_STAMP, STUB_SITE_HEALTH_STAMP or STUB_SITE_PAGE_STAMP.
            'curl': ('''stamp="$(grep -o '/grid/[0-9a-f]\\{16\\}/' '@CONFIG@' 2>/dev/null | head -n 1 | cut -d/ -f3)"
case "$*" in
  *"run.app/health"*) printf '{"status":"ok","stamp":"%s"}' "${STUB_SERVICE_STAMP:-$stamp}" ;;
  *"web.app/health"*) printf '{"status":"ok","stamp":"%s"}' "${STUB_SITE_HEALTH_STAMP:-$stamp}" ;;
  *"web.app/"*) printf '<meta id="nowcast-build" name="nowcast-build" content="%s">' "${STUB_SITE_PAGE_STAMP:-$stamp}" ;;
  *) printf '{}' ;;
esac
exit 0''').replace('@CONFIG@', str(Path(directory) / 'build' / 'firebase.json')),
            'gcloud': f'''case "$*" in
  *"artifacts docker images describe"*) printf '%s\\n' '{index}' ;;
  *"firstof(status)"*) printf '%s\\n' '{state}' ;;
  *"firstof(message)"*) printf '%s\\n' '{ready_message}' ;;
  *"value(status.imageDigest)"*) printf '%s\\n' '{revision_digest}' ;;
  *"run deploy"*) printf '%s\\n' '{deployed}' ;;
  *"services update-traffic"*) exit 0 ;;
  *"latestReadyRevisionName"*) printf '%s\\n' '{pinned}' ;;
  *"traffic[0]"*) printf '%s\\t{percent}\\n' '{served}' ;;
  *"status.url"*) printf '%s\\n' https://grid-nowcast-stub.a.run.app ;;
esac
exit 0
''',
        }
        for name, body in bodies.items():
            binary = Path(directory) / name
            binary.write_text(f'#!/bin/sh\necho "$0 $*" >> "{marker}"\n{body}\n', encoding='utf-8')
            binary.chmod(0o755)
        return marker

    #: The synthetic replay fixture the stubbed releases stage (PERF-5). It is the labelled
    #: synthetic grid fixture, so a test release never writes company data anywhere; the
    #: Hosting config template below points the stage at the test's own temporary directory.
    STAGE_FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'page' / 'data'
    #: The build-stamp token the stager writes the build stamp into (`src.api.STAMP_TOKEN`;
    #: tests/test_hosting_stage.py pins the stager's own constant to it). The synthetic template
    #: carries it exactly where the real template does.
    STAMP_TOKEN = '__NOWCAST_STAMP__'

    def stub_release_env(self, directory, key, **extra):
        """The environment a stubbed release runs with: the stubs first on PATH, the synthetic
        web key, a readiness wait that cannot stall a test (the polls answer at once), and the
        PERF-5 staging inputs — the synthetic replay fixture, a Hosting config template whose
        `hosting.public` is a directory of this test, and the generated config the release
        deploys with. Both config paths are inside `directory`, so the release stages, generates
        and reads back there and never writes into the work tree. `extra` overrides any of those.
        """
        (Path(directory) / 'deploy').mkdir()
        config = Path(directory) / 'deploy' / 'firebase.json'
        config.write_text(json.dumps(
            {'hosting': {'site': 'grid-nowcast', 'public': '../build/hosting',
                         'headers': [
                             {'source': '/grid-data/%s/**' % self.STAMP_TOKEN,
                              'headers': [{'key': 'Cache-Control',
                                           'value': 'public, max-age=31536000, immutable'}]},
                             {'source': '/grid/%s/**' % self.STAMP_TOKEN,
                              'headers': [{'key': 'Cache-Control',
                                           'value': 'public, max-age=31536000, immutable'}]}],
                         'rewrites': [{'source': '**',
                                       'run': {'serviceId': 'grid-nowcast',
                                               'region': 'asia-southeast1'}}]}}), encoding='utf-8')
        # DATA-2: GRID_DATA is a baked copy of the fixture with its manifest (`baked_copy`).
        environ = dict(os.environ, WEB_API_KEY_FILE=str(key), REVISION_TIMEOUT='10',
                       REVISION_POLL='0',
                       GRID_DATA=str(baked_copy(self.STAGE_FIXTURE, Path(directory) / 'grid-data')),
                       FIREBASE_CONFIG=str(config),
                       FIREBASE_HOSTING_CONFIG=str(Path(directory) / 'build' / 'firebase.json'),
                       PATH=f'{directory}{os.pathsep}{os.environ["PATH"]}')
        environ.update(extra)
        return environ

    def release_key(self, directory):
        """A synthetic web-key file, so the stubbed release has one to read."""
        key = Path(directory) / 'web-key'
        key.write_text('synthetic-web-key', encoding='utf-8')
        return key

    def test_the_dry_run_prints_the_pinned_release_and_runs_none_of_its_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_tools(directory)
            result = self.run_script('--dry-run',
                                     path=f'{directory}{os.pathsep}{os.environ["PATH"]}')
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(marker.exists(),
                             marker.read_text(encoding='utf-8') if marker.exists() else '')
        for needle in (
            'gcloud run deploy grid-nowcast --project grid-nowcast --region asia-southeast1',
            '--service-account',
            '--allow-unauthenticated --max-instances 1 --concurrency 40 --timeout 60 '
            '--min-instances 0 --memory 512Mi --no-cpu-boost',
            '--image asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/grid-nowcast@sha256:',
            '--set-env-vars NOWCAST_ENV=hosted,GCLOUD_PROJECT=grid-nowcast,'
            'NOWCAST_DEMO_NAMESPACE=demo-judge,NOWCAST_NAMESPACE=nowcast-private',
            'FIREBASE_WEB_API_KEY=<from .local/hosting/firebase-web-api-key>',
            'firebase deploy --only hosting --project grid-nowcast '
            '--config build/firebase.json',
            'https://grid-nowcast.web.app',
            # PERF-5: the first screen is staged from the same inputs the image was built from —
            # and the config this build deploys is generated from the template with this build's
            # stamp written into its header rules — before the site is released with it.
            # DATA-2: the data path is the baked fixture copy (GRID_DATA); the default,
            # build/grid-data, is pinned in the script text below.
            '/usr/bin/python3 scripts/deploy/stage_hosting.py --config '
            f'scripts/deploy/firebase.json --config-out build/firebase.json --data {self.BAKED}',
            '/usr/bin/python3 scripts/deploy/stage_hosting.py --check --config '
            f'scripts/deploy/firebase.json --config-out build/firebase.json --data {self.BAKED}',
        ):
            self.assertIn(needle, result.stdout, needle)
        staging = result.stdout.index('stage_hosting.py --config')
        checking = result.stdout.index('stage_hosting.py --check')
        releasing = result.stdout.index('firebase deploy --only hosting')
        self.assertLess(staging, checking)
        self.assertLess(checking, releasing, 'the stage is read back before the site is released')
        self.assertIn('Hosting files:', result.stdout, 'the closing evidence names the stage')
        self.assertIn('--config build/firebase.json', result.stdout,
                      'the release deploys the generated config, never the template')
        self.assertIn('GRID_DATA="${GRID_DATA:-build/grid-data}"',
                      self.SCRIPT.read_text(encoding='utf-8'))

    def test_the_deploy_line_carries_the_configured_runtime_service_account(self):
        # A labelled synthetic account: the release audit scans this shipped tree, and the real
        # runtime identity belongs in the deploy script's default, not in a test literal.
        account = 'synthetic-runtime@example.invalid'
        result = self.run_script('--dry-run', extra={'RUNTIME_SERVICE_ACCOUNT': account})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(f'--service-account {account}', result.stdout)

    def test_a_release_selects_waits_for_and_verifies_the_revision_its_deploy_created(self):
        """Cloud Run keeps the traffic where a rollback pinned it, and the service's ready field
        still names the previous revision after a deploy, so a release must take the revision its
        own deploy created (`status.latestCreatedRevisionName`), resolve the pushed image's
        linux/amd64 manifest, wait for that revision's own Ready condition — selected by its
        type, never by position, and never read through the service's ready field — check the
        image digest it runs, and only then route the traffic — and read the traffic back and
        fail when the service serves another revision."""
        result = self.run_script('--dry-run')
        self.assertEqual(0, result.returncode, result.stderr)
        deploy_line = next(line for line in result.stdout.splitlines()
                           if line.startswith('  + gcloud run deploy'))
        self.assertIn("--format 'value(status.latestCreatedRevisionName)'", deploy_line)
        self.assertNotIn('latestReadyRevisionName', result.stdout)
        steps = [
            "docker buildx imagetools inspect --raw asia-southeast1-docker.pkg.dev/grid-nowcast/"
            "grid-nowcast/grid-nowcast@sha256:<pushed-image-digest> | "
            "/usr/bin/python3 scripts/deploy/platform_digest.py",
            "gcloud run revisions describe <revision> --project grid-nowcast --region "
            "asia-southeast1 --format 'value(status.conditions.filter(\"type=Ready\")"
            ".slice(0).firstof(status))'",
            "gcloud run revisions describe <revision> --project grid-nowcast --region "
            "asia-southeast1 --format 'value(status.imageDigest)'",
            'gcloud run services update-traffic grid-nowcast --project grid-nowcast '
            '--region asia-southeast1 --to-revisions <revision>=100',
            "gcloud run services describe grid-nowcast --project grid-nowcast --region "
            "asia-southeast1 --format 'value(status.traffic[0].revisionName,status.traffic[0].percent)'",
        ]
        for needle in steps:
            self.assertIn(needle, result.stdout, needle)
        positions = [result.stdout.index(needle) for needle in steps]
        self.assertEqual(sorted(positions), positions)  # resolve, wait, verify, route, read back

    def test_a_ready_revision_under_pinned_traffic_proceeds(self):
        """The first POC follow-up: traffic pinned by a rollback left the service's ready field
        naming the previous revision, and the old release waited on that field — 300 s of it —
        and refused a revision that was Ready. The revision's own Ready condition is what
        decides now, and the service's ready field is never read: the stub answers it with the
        pinned revision, so reading it would show up in the recorded calls."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00004-8rm',
                                       served='grid-nowcast-00004-8rm',
                                       pinned='grid-nowcast-00003-7m9')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('ready: grid-nowcast-00004-8rm', result.stdout)
            self.assertIn('traffic: 100% of requests to grid-nowcast-00004-8rm', result.stdout)
            calls = marker.read_text(encoding='utf-8')
            self.assertNotIn('latestReadyRevisionName', calls)  # the service field is not a proxy
            self.assertLess(calls.index('run deploy'), calls.index('revisions describe'))
            self.assertIn('--to-revisions grid-nowcast-00004-8rm=100', calls)

    def test_a_not_ready_revision_fails_with_its_message(self):
        """Ready=False on the created revision is a failed release that names the reason: the
        revision's own condition message is printed, and nothing is routed or released."""
        with tempfile.TemporaryDirectory() as directory:
            message = 'Container failed to start and listen on the port defined by PORT=8080'
            marker = self.stub_release(directory, deployed='grid-nowcast-00004-8rm',
                                       served='grid-nowcast-00004-8rm',
                                       ready='False', ready_message=message)
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn(f'refusing: grid-nowcast-00004-8rm reports Ready=False: {message}; '
                          'nothing is released', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertNotIn('services update-traffic', calls)  # nothing is routed
            self.assertNotIn('deploy --only hosting', calls)  # and nothing is released as served

    def test_a_revision_without_a_ready_condition_fails_after_the_timeout(self):
        """A revision that never reports Ready=True is refused after REVISION_TIMEOUT, not
        waited on forever."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00004-8rm',
                                       served='grid-nowcast-00004-8rm', conditions=False)
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key,
                                                               REVISION_TIMEOUT='0'))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: grid-nowcast-00004-8rm reported no Ready=True within 0s '
                          '(Ready: absent); nothing is released', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertNotIn('services update-traffic', calls)
            self.assertNotIn('deploy --only hosting', calls)

    def test_the_index_and_the_platform_digest_of_the_same_push_proceed(self):
        """The second POC follow-up: Artifact Registry reported the pushed image's index digest
        (`sha256:2b054bde…`) while Cloud Run recorded the linux/amd64 manifest it runs
        (`sha256:572c87ba…`) for the same push, and the release refused. Resolving the index to
        its platform manifest makes the same push compare equal; the deploy still pins the
        digest the registry reported, and the release prints both."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00005-kxh',
                                       served='grid-nowcast-00005-kxh',
                                       index='sha256:synthetic-index-digest',
                                       platform='sha256:synthetic-platform-digest')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('digest: sha256:synthetic-index-digest', result.stdout)
            self.assertIn('platform digest: sha256:synthetic-platform-digest', result.stdout)
            self.assertIn('image digest of grid-nowcast-00005-kxh: '
                          'asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/'
                          'grid-nowcast@sha256:synthetic-platform-digest', result.stdout)
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('imagetools inspect --raw', calls)
            self.assertIn('--image asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/'
                          'grid-nowcast@sha256:synthetic-index-digest', calls)
            self.assertIn('--to-revisions grid-nowcast-00005-kxh=100', calls)

    def test_a_push_that_is_a_plain_manifest_compares_the_registry_digest(self):
        """A single-platform push has no index to resolve: the registry's digest is already the
        platform manifest Cloud Run records, and the release proceeds on it."""
        with tempfile.TemporaryDirectory() as directory:
            digest = 'sha256:synthetic-single-manifest-digest'
            marker = self.stub_release(directory, deployed='grid-nowcast-00005-kxh',
                                       served='grid-nowcast-00005-kxh', index=digest,
                                       revision_digest=digest, single_manifest=True)
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(f'platform digest: {digest}', result.stdout)
            self.assertIn(f'image digest of grid-nowcast-00005-kxh: {digest}', result.stdout)
            self.assertIn('--to-revisions grid-nowcast-00005-kxh=100',
                          marker.read_text(encoding='utf-8'))

    def test_the_full_cloud_run_reference_is_verified_by_its_platform_digest(self):
        """Regression: the live API returns an image@sha256 reference, not a bare digest,
        and that reference names the repository this release pushed
        (`asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/grid-nowcast@…`,
        release record 2026-10-14): the release proceeds on it and routes the traffic."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                       served='grid-nowcast-00006-ttp')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(f'image digest of grid-nowcast-00006-ttp: '
                          f'{self.REMOTE_IMAGE}@sha256:synthetic-platform-digest', result.stdout)
            self.assertIn('--to-revisions grid-nowcast-00006-ttp=100',
                          marker.read_text(encoding='utf-8'))

    def test_a_reference_naming_another_repository_is_refused_before_traffic(self):
        """The name before the @ is the repository whose image the revision runs, and a
        release only accepts what it pushed: `/@sha256:…` and `example.invalid//image@…`
        are malformed paths, and another repository presenting the same platform digest is
        not this release's image. Each is refused before the traffic update and the Hosting
        release — the digest after the @ matches the pushed manifest, so a release that
        only compared the suffix would have proceeded (review finding, 2026-10-14)."""
        for reference in ('/@sha256:synthetic-platform-digest',
                          'example.invalid//image@sha256:synthetic-platform-digest',
                          'example.invalid/image@sha256:synthetic-platform-digest',
                          f'{self.REGISTRY}/other-image@sha256:synthetic-platform-digest'):
            with self.subTest(reference=reference), tempfile.TemporaryDirectory() as directory:
                marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                           served='grid-nowcast-00006-ttp',
                                           revision_digest=reference)
                key = self.release_key(directory)
                result = self.run_script(env=self.stub_release_env(directory, key))
                self.assertEqual(1, result.returncode)
                self.assertIn(f'runs {reference}, not the linux/amd64 manifest', result.stderr)
                self.assertIn('nothing is released', result.stderr)
                calls = marker.read_text(encoding='utf-8')
                self.assertNotIn('services update-traffic', calls)
                self.assertNotIn('deploy --only hosting', calls)

    def test_a_full_reference_with_another_digest_is_refused_before_traffic(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                       served='grid-nowcast-00006-ttp',
                                       revision_digest='example.invalid/image@sha256:synthetic-other-digest')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('nothing is released', result.stderr)
            self.assertNotIn('services update-traffic', marker.read_text(encoding='utf-8'))

    def test_an_invalid_qualified_reference_is_refused_before_traffic(self):
        for invalid in ('@sha256:synthetic-platform-digest',
                        'example.invalid/image@other@sha256:synthetic-platform-digest',
                        'example.invalid/bad image@sha256:synthetic-platform-digest'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                           served='grid-nowcast-00006-ttp',
                                           revision_digest=invalid)
                key = self.release_key(directory)
                result = self.run_script(env=self.stub_release_env(directory, key))
                self.assertEqual(1, result.returncode)
                calls = marker.read_text(encoding='utf-8')
                self.assertNotIn('services update-traffic', calls)
                self.assertNotIn('deploy --only hosting', calls)

    def test_a_whitespace_or_control_character_in_the_image_name_is_refused_before_traffic(self):
        """A reference whose image name carries a tab, a newline or another control character
        is malformed exactly as one with a space is — and, whatever its shape, it is not the
        repository this release pushed, so no comparison may accept it: the release refuses
        rather than authorize a traffic update, and the refusal names the reference it read
        (review finding, 2026-10-14). The digest after the @ matches the pushed platform
        manifest here, so a release that only compared the suffix would have proceeded."""
        for control in ('\t', '\n', '\v'):
            with self.subTest(control=repr(control)), tempfile.TemporaryDirectory() as directory:
                reference = ('example.invalid/bad' + control + 'image@'
                             'sha256:synthetic-platform-digest')
                marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                           served='grid-nowcast-00006-ttp',
                                           revision_digest=reference)
                key = self.release_key(directory)
                result = self.run_script(env=self.stub_release_env(directory, key))
                self.assertEqual(1, result.returncode)
                self.assertIn(f'runs {reference}, not the linux/amd64 manifest', result.stderr)
                self.assertIn('nothing is released', result.stderr)
                calls = marker.read_text(encoding='utf-8')
                self.assertNotIn('services update-traffic', calls)
                self.assertNotIn('deploy --only hosting', calls)

    def test_a_missing_image_digest_is_refused_before_traffic(self):
        """A revision whose image-digest read comes back empty is refused like any other value
        that is not the pushed platform manifest: the release proceeds on evidence, never on
        nothing (acceptance: malformed or missing values are refused)."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                       served='grid-nowcast-00006-ttp', revision_digest='')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('runs no image, not the linux/amd64 manifest', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertNotIn('services update-traffic', calls)
            self.assertNotIn('deploy --only hosting', calls)

    def test_a_different_image_is_refused(self):
        """A ready revision that runs another image is not this release: the digest read turns a
        wrong selection — or another image pushed under the same tag — into a loud failure
        instead of a release serving old code."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00003-new',
                                       served='grid-nowcast-00003-new',
                                       revision_digest='sha256:synthetic-other-digest')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: grid-nowcast-00003-new runs sha256:synthetic-other-digest, '
                          'not the linux/amd64 manifest sha256:synthetic-platform-digest of the '
                          'pushed sha256:synthetic-index-digest; nothing is released', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertNotIn('services update-traffic', calls)
            self.assertNotIn('deploy --only hosting', calls)

    def test_an_unresolvable_manifest_refuses_before_anything_is_deployed(self):
        """The resolution fails closed: a manifest that is not JSON — a broken docker, a wrong
        reference — refuses the release before the deploy, instead of comparing against the
        wrong digest."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00003-new',
                                       served='grid-nowcast-00003-new',
                                       raw_manifest='not a manifest')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: could not resolve the linux/amd64 manifest of '
                          'asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/grid-nowcast@'
                          'sha256:synthetic-index-digest; nothing is deployed', result.stderr)
            self.assertNotIn('run deploy', marker.read_text(encoding='utf-8'))

    def test_an_index_without_a_linux_amd64_manifest_refuses_before_anything_is_deployed(self):
        """A push whose index lists no linux/amd64 manifest has no established platform identity:
        the release must refuse in step 3, before the deploy, rather than substituting the index
        digest and deploying an image it could not identify (review finding, 2026-10-14). The
        stub answers the revision's image digest with the index digest, so a release that slipped
        through would have compared equal and reported success."""
        with tempfile.TemporaryDirectory() as directory:
            arm64 = index_manifest('sha256:synthetic-arm64-digest', entries=[
                {'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                 'digest': 'sha256:synthetic-arm64-digest', 'size': 1024,
                 'platform': {'architecture': 'arm64', 'os': 'linux'}}])
            marker = self.stub_release(directory, deployed='grid-nowcast-00005-kxh',
                                       served='grid-nowcast-00005-kxh',
                                       revision_digest='sha256:synthetic-index-digest',
                                       raw_manifest=json.dumps(arm64))
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: could not resolve the linux/amd64 manifest of '
                          'asia-southeast1-docker.pkg.dev/grid-nowcast/grid-nowcast/grid-nowcast@'
                          'sha256:synthetic-index-digest; nothing is deployed', result.stderr)
            self.assertIn('no linux/amd64 manifest digest in the image index '
                          '(manifests: linux/arm64)', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('imagetools inspect --raw', calls)  # the resolution was attempted
            self.assertNotIn('run deploy', calls)  # the finding: nothing is deployed
            self.assertNotIn('revisions describe', calls)
            self.assertNotIn('services update-traffic', calls)
            self.assertNotIn('deploy --only hosting', calls)

    def test_a_release_whose_service_serves_another_revision_fails(self):
        """After a rollback the traffic stays pinned: the release must refuse, not report."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00003-new',
                                       served='grid-nowcast-00001-old')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: grid-nowcast serves 100% to grid-nowcast-00001-old, '
                          'not 100% to grid-nowcast-00003-new', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('services update-traffic', calls)
            self.assertNotIn('deploy --only hosting', calls)  # nothing is released as served

    def test_the_release_ships_the_firestore_rules_that_deny_every_client_write(self):
        """DOCK-5: the rules file denies every client read and write (the agent's `agent_*`
        collections among them) and the release deploys it, after the stage is read back and
        before the site is released; a rollback deploys no rules."""
        rules = (ROOT / 'scripts' / 'deploy' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertTrue(rules.startswith("rules_version = '2';"))
        allows = re.findall(r'allow ([a-z, ]+): if ([^;]+);', rules)
        self.assertTrue(allows)
        self.assertEqual({('read, write', 'false')}, set(allows), 'every rule is a denial')
        self.assertIn('match /{document=**}', rules, 'the catch-all denies everything else')
        self.assertIn('match /h1_namespaces/{namespace}/{collection}/{document=**}', rules)
        self.assertIn('agent_*', rules)
        self.assertNotIn('request.auth', rules)
        config = json.loads((ROOT / 'scripts' / 'deploy' / 'firestore.json').read_text(encoding='utf-8'))
        self.assertEqual({'firestore': {'rules': 'firestore.rules'}}, config,
                         'the path is read beside the config file, as firebase-tools resolves it')
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_tools(directory)
            result = self.run_script('--dry-run', path=f'{directory}{os.pathsep}{os.environ["PATH"]}')
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(marker.exists())
        line = ('firebase deploy --only firestore:rules --project grid-nowcast '
                '--config scripts/deploy/firestore.json')
        self.assertIn(line, result.stdout)
        self.assertLess(result.stdout.index('stage_hosting.py --check'), result.stdout.index(line))
        self.assertLess(result.stdout.index(line), result.stdout.index('firebase deploy --only hosting'))
        rollback = self.run_script('--dry-run', '--rollback', 'grid-nowcast-00002-xyz')
        self.assertEqual(0, rollback.returncode, rollback.stderr)
        self.assertNotIn('firestore:rules', rollback.stdout)

    def test_the_rollback_shifts_traffic_back_and_checks_health(self):
        result = self.run_script('--dry-run', '--rollback', 'grid-nowcast-00002-xyz')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('gcloud run services update-traffic grid-nowcast --project grid-nowcast '
                      '--region asia-southeast1 --to-revisions grid-nowcast-00002-xyz=100',
                      result.stdout)
        # The rollback also reads the traffic back and fails unless the target serves it all.
        self.assertIn("--format 'value(status.traffic[0].revisionName,status.traffic[0].percent)'",
                      result.stdout)
        self.assertIn('curl --fail --silent --show-error <service-url>/health', result.stdout)
        self.assertNotIn('docker build', result.stdout)

    def test_a_dry_run_takes_an_existing_image_without_building(self):
        result = self.run_script('--dry-run', '--image', 'grid-nowcast:release-candidate')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('taking the existing image grid-nowcast:release-candidate', result.stdout)
        # The image is taken, not built; `docker buildx imagetools inspect` below is the registry
        # read that resolves the pushed index, not a build of the image.
        self.assertNotIn('docker build -t', result.stdout)
        self.assertIn('docker buildx imagetools inspect --raw', result.stdout)

    def test_a_release_stages_the_first_screen_before_it_releases_hosting(self):
        """PERF-5: the site is released with the staged files already in its public directory and
        with the config the stager generated for this build.

        The release stages the grid page, its design files and the replay data at the template's
        own `hosting.public` (a directory of this test), writes the generated config with this
        build's stamp written into its header rules, reads both back against the inputs
        (`--check`) and only then runs `firebase deploy --only hosting` with the generated config.
        """
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                       served='grid-nowcast-00006-ttp')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            stage = Path(directory) / 'build' / 'hosting'
            staged = sorted(path.relative_to(stage).as_posix()
                            for path in stage.rglob('*') if path.is_file())
            self.assertIn('index.html', staged, 'the page the site serves at / is staged')
            stamp = re.search(r'for build ([0-9a-f]{16})', result.stdout)
            self.assertIsNotNone(stamp, result.stdout)
            for name in ('regions.json', 'nodes-2026-09-21.json', 'ph.geojson'):
                self.assertIn(f'grid-data/{stamp.group(1)}/{name}', staged, name)
            self.assertIn(f'grid/{stamp.group(1)}/grid.js', staged)
            page = (stage / 'index.html').read_text(encoding='utf-8')
            self.assertIn(f'/grid/{stamp.group(1)}/grid.js', page)
            self.assertIn(f'content="{stamp.group(1)}"', page,
                          'the meta element the script reads carries the same stamp')
            # The generated config: this build's stamp in the header rules, naming this stage,
            # and it is what the release hands to firebase.
            config = Path(directory) / 'build' / 'firebase.json'
            generated = json.loads(config.read_text(encoding='utf-8'))['hosting']
            self.assertEqual({'/grid-data/%s/**' % stamp.group(1), '/grid/%s/**' % stamp.group(1)},
                             {rule['source'] for rule in generated['headers']})
            self.assertNotIn(self.STAMP_TOKEN, config.read_text(encoding='utf-8'),
                             'the token is replaced before the config is deployed')
            self.assertEqual(stage.resolve(), (config.parent / generated['public']).resolve())
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('deploy --only hosting', calls, 'the site was released after staging')
            self.assertIn(f'--config {config}', calls,
                          'the release deploys the generated config, never the template')
            self.assertLess(result.stdout.index('staged '), result.stdout.index('firebase deploy'))

    def test_a_release_without_replay_data_refuses_before_hosting(self):
        """The acceptance's refusal: no stage is possible without `build/grid-data`, so the
        release stops — naming the missing input — before `firebase deploy --only hosting`,
        and writes neither a stage nor a generated config."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00006-ttp',
                                       served='grid-nowcast-00006-ttp')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(
                directory, key, GRID_DATA=str(Path(directory) / 'nowhere')))
            # DATA-2: the manifest gate meets the missing tree first, before anything is built:
            # the refusal names the missing manifest and no tool runs at all (stronger than the
            # stager's own refusal, which came after the deploy).
            self.assertEqual(1, result.returncode)
            self.assertIn('nowhere/manifest.json is missing', result.stderr)
            calls = marker.read_text(encoding='utf-8') if marker.exists() else ''
            self.assertNotIn('deploy --only hosting', calls)
            self.assertNotIn('run deploy', calls)
            self.assertFalse((Path(directory) / 'build' / 'hosting').exists())
            self.assertFalse((Path(directory) / 'build' / 'firebase.json').exists())

    def test_a_bake_without_a_manifest_is_refused_before_anything_is_built(self):
        """DATA-2: a tree build_all.py did not make has no manifest; even the dry run refuses it,
        prints how to bake, and runs no tool."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_tools(directory)
            bare = Path(directory) / 'grid-data'
            shutil.copytree(self.STAGE_FIXTURE, bare)
            result = self.run_script('--dry-run', path=f'{directory}{os.pathsep}{os.environ["PATH"]}',
                                     extra={'GRID_DATA': str(bare)})
            self.assertEqual(1, result.returncode)
            self.assertIn(f'refusing: {bare}/manifest.json is missing, so {bare} was not baked by '
                          'scripts/grid/build_all.py; nothing is built or released', result.stderr)
            self.assertIn(f'/usr/bin/python3 scripts/grid/build_all.py --data {bare}', result.stderr)
            self.assertNotIn('docker build', result.stdout)
            self.assertFalse(marker.exists())

    def test_the_dry_run_prints_the_bake_and_stamp_checks_in_order(self):
        """DATA-2: the manifest is verified before the image is built; the stage's stamp and the
        routed service's /health stamp are read after the stage is read back and before the
        Firestore rules and the Hosting release; the site's /health and first screen are read
        after the Hosting release."""
        result = self.run_script('--dry-run')
        self.assertEqual(0, result.returncode, result.stderr)
        steps = [
            f'/usr/bin/python3 scripts/grid/build_all.py --verify-manifest {self.BAKED}',
            'docker build -t grid-nowcast .',
            'services update-traffic grid-nowcast',
            'stage_hosting.py --check',
            '/usr/bin/python3 scripts/deploy/read_stamp.py config build/firebase.json',
            'curl --fail --silent --show-error <service-url>/health | '
            '/usr/bin/python3 scripts/deploy/read_stamp.py health',
            'firebase deploy --only firestore:rules',
            'firebase deploy --only hosting',
            'curl --fail --silent --show-error https://grid-nowcast.web.app/health | '
            '/usr/bin/python3 scripts/deploy/read_stamp.py health',
            'curl --fail --silent --show-error https://grid-nowcast.web.app/ | '
            '/usr/bin/python3 scripts/deploy/read_stamp.py page',
        ]
        positions = [result.stdout.index(needle) for needle in steps]
        self.assertEqual(sorted(positions), positions)
        partial = self.run_script('--dry-run', extra={'ALLOW_PARTIAL_BAKE': '1'})
        self.assertIn(f'--verify-manifest {self.BAKED} --allow-partial', partial.stdout)

    def test_a_release_reads_one_stamp_on_both_halves_of_the_site(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                       served='grid-nowcast-00007-abc')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(directory, key))
            self.assertEqual(0, result.returncode, result.stderr)
            stamp = re.search(r'for build ([0-9a-f]{16})', result.stdout).group(1)
            self.assertIn(f'stamps: Hosting stage {stamp}, Cloud Run {stamp}', result.stdout)
            self.assertIn(f'site stamps: https://grid-nowcast.web.app/health {stamp}, '
                          f'https://grid-nowcast.web.app/ {stamp}', result.stdout)
            self.assertIn(f'build stamp:   {stamp}', result.stdout)
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('https://grid-nowcast-stub.a.run.app/health', calls)
            self.assertIn('https://grid-nowcast.web.app/health', calls)
            self.assertLess(calls.index('https://grid-nowcast-stub.a.run.app/health'),
                            calls.index('deploy --only hosting'))
            self.assertLess(calls.index('deploy --only hosting'),
                            calls.index('https://grid-nowcast.web.app/health'))

    def test_a_service_on_another_bake_is_refused_before_hosting(self):
        """DATA-2's root cause: Cloud Run serving one bake while the stage holds another."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                       served='grid-nowcast-00007-abc')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(
                directory, key, STUB_SERVICE_STAMP='0123456789abcdef'))
            self.assertEqual(1, result.returncode)
            self.assertIn('refusing: Cloud Run grid-nowcast-00007-abc serves build '
                          '0123456789abcdef but the Hosting stage is build ', result.stderr)
            self.assertIn('Hosting is not released', result.stderr)
            calls = marker.read_text(encoding='utf-8')
            self.assertIn('services update-traffic', calls)
            self.assertNotIn('firestore:rules', calls)
            self.assertNotIn('deploy --only hosting', calls)

    def test_a_service_answering_no_stamp_is_refused_before_hosting(self):
        """An image from before DATA-2 names no stamp on /health: that is no evidence either."""
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                       served='grid-nowcast-00007-abc')
            key = self.release_key(directory)
            result = self.run_script(env=self.stub_release_env(
                directory, key, STUB_SERVICE_STAMP='none'))
            self.assertEqual(1, result.returncode)
            self.assertIn('names no build stamp', result.stderr)
            self.assertNotIn('deploy --only hosting', marker.read_text(encoding='utf-8'))

    def test_a_split_site_after_the_release_fails_loudly(self):
        for variable in ('STUB_SITE_HEALTH_STAMP', 'STUB_SITE_PAGE_STAMP'):
            with self.subTest(variable=variable), tempfile.TemporaryDirectory() as directory:
                marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                           served='grid-nowcast-00007-abc')
                key = self.release_key(directory)
                result = self.run_script(env=self.stub_release_env(
                    directory, key, **{variable: 'fedcba9876543210'}))
                self.assertEqual(1, result.returncode)
                self.assertIn('FAILED: the released site is split: ', result.stderr)
                self.assertIn('fedcba9876543210', result.stderr)
                self.assertNotIn('release complete', result.stdout)
                self.assertIn('deploy --only hosting', marker.read_text(encoding='utf-8'))

    def test_a_changed_or_partial_bake_is_refused_before_anything_is_built(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                       served='grid-nowcast-00007-abc')
            key = self.release_key(directory)
            environ = self.stub_release_env(directory, key)
            regions = Path(environ['GRID_DATA']) / 'regions.json'
            regions.write_bytes(regions.read_bytes() + b' ')
            result = self.run_script(env=environ)
            self.assertEqual(1, result.returncode)
            self.assertIn("do not match the manifest's data_digest", result.stderr)
            self.assertNotIn('build', marker.read_text(encoding='utf-8')
                             if marker.exists() else '')
        with tempfile.TemporaryDirectory() as directory:
            marker = self.stub_release(directory, deployed='grid-nowcast-00007-abc',
                                       served='grid-nowcast-00007-abc')
            key = self.release_key(directory)
            partial = baked_copy(self.STAGE_FIXTURE, Path(directory) / 'partial',
                                 missing=('views',))
            environ = self.stub_release_env(directory, key, GRID_DATA=str(partial))
            result = self.run_script(env=environ)
            self.assertEqual(1, result.returncode)
            self.assertIn('a partial bake, made without views', result.stderr)
            self.assertFalse(marker.exists() and 'docker build' in marker.read_text(encoding='utf-8'))
            shipped = self.run_script(env=dict(environ, ALLOW_PARTIAL_BAKE='1'))
            self.assertEqual(0, shipped.returncode, shipped.stderr)
            self.assertIn('deploy --only hosting', marker.read_text(encoding='utf-8'))

    def test_an_unknown_argument_is_a_usage_error(self):
        result = self.run_script('--release')
        self.assertEqual(2, result.returncode)
        self.assertIn('unknown argument: --release', result.stderr)


@unittest.skipUnless(DEPLOY_SCRIPT.exists(), 'scripts/deploy/deploy.sh is withheld from the public export')
class DeployHostingConfigTests(unittest.TestCase):
    """H2b, revised by PERF-5: the site publishes the staged first screen and rewrites the rest.

    Until PERF-5 the config was one rewrite and no `public` directory. The owner's decision of
    2026-10-14 (performance/intent.md) moved the grid page and its replay data to Hosting files,
    so `scripts/deploy/firebase.json` now names the staged directory and carries the header-rule
    classes with the build-stamp token where the stamp goes — it is the template. The release
    deploys the *generated* config (`stage_hosting.py --config-out`), which writes this build's
    stamp into those rules, and the "**" rewrite stays for every path the stage does not hold.
    `tests/test_hosting_stage.py::HostingConfig` and `::GeneratedHostingConfig` audit the
    template and the generated config — the classes, the security headers against the
    application's own, and the paths that must not be matched by a rule — so this class keeps
    only the template's shape and the release's use of it.
    """

    def setUp(self):
        self.hosting = json.loads((ROOT / 'scripts' / 'deploy' / 'firebase.json')
                                  .read_text(encoding='utf-8'))['hosting']
        self.script = (ROOT / 'scripts' / 'deploy' / 'deploy.sh').read_text(encoding='utf-8')

    def test_the_site_rewrites_every_path_to_the_cloud_run_service(self):
        self.assertEqual({'site', 'public', 'headers', 'rewrites'}, set(self.hosting))
        self.assertEqual('grid-nowcast', self.hosting['site'])
        self.assertEqual([{'source': '**',
                           'run': {'serviceId': 'grid-nowcast', 'region': 'asia-southeast1'}}],
                         self.hosting['rewrites'])

    def test_the_public_directory_is_the_staged_one_and_no_redirects_were_added(self):
        self.assertEqual('../../build/hosting', self.hosting['public'])
        for key in ('source', 'cleanUrls', 'redirects'):
            self.assertNotIn(key, self.hosting, key)

    def test_the_rewrite_service_and_region_match_the_deploy_script(self):
        self.assertIn("SERVICE='grid-nowcast'", self.script)
        self.assertIn("REGION='asia-southeast1'", self.script)
        # The script defaults FIREBASE_CONFIG to this template, generates the effective config
        # from it at staging time and passes *that* to the stager, the read-back and the release
        # (the dry-run test in DeployScriptTests pins the printed lines).
        self.assertIn('scripts/deploy/firebase.json', self.script)
        rewrite = self.hosting['rewrites'][0]['run']
        self.assertIn(f"SERVICE='{rewrite['serviceId']}'", self.script)
        self.assertIn(f"REGION='{rewrite['region']}'", self.script)

    def test_the_release_deploys_the_generated_config_and_never_the_template(self):
        self.assertIn('HOSTING_CONFIG="${FIREBASE_HOSTING_CONFIG:-build/firebase.json}"',
                      self.script)
        self.assertIn('deploy --only hosting --project "$PROJECT" --config "$HOSTING_CONFIG"',
                      self.script)
        self.assertNotIn('deploy --only hosting --project "$PROJECT" --config "$CONFIG"',
                         self.script)
        # The generated config lands where `build/` is git-ignored: it is a deploy artifact.
        result = subprocess.run(['git', 'check-ignore', '-q', 'build/firebase.json'], cwd=ROOT,
                                capture_output=True)
        self.assertEqual(0, result.returncode, 'build/firebase.json must be ignored by Git')


class CleanupStore:
    """The deletion path, fake: models the membership documents the store still holds.

    ``held`` is the state a later listing would discover: the memberships the store has, which
    ``member_ref(...).delete()`` removes. ``held`` starts empty unless a test seeds it (a store
    that never had the document still records the delete request), ``members`` records every
    delete request, and ``log`` is shared with the fake Auth client so a test can assert the
    deletion order: the membership must go last, after the case and the Auth user.
    """

    def __init__(self, held=(), log=None):
        self.cases, self.members = [], []
        self.held = set(held)
        self.log = [] if log is None else log

    def discard_case(self, tenant, case):
        self.cases.append((tenant, case))
        self.log.append(('case', case))

    def member_ref(self, uid, tenant, case):
        def delete(timeout=None):
            self.members.append((uid, tenant, case))
            self.held.discard((uid, tenant, case))
            self.log.append(('membership', uid))
        return types.SimpleNamespace(delete=delete)


class CleanupAuth:
    """The Auth client, fake: users by uid with the Admin SDK's real shape, and deletions.

    A real Firebase anonymous user has an **empty** ``provider_data`` (the ``firebase`` provider
    the Admin SDK reports is the account's primary provider, not an entry in ``provider_data``),
    no email and no phone number; a private account carries its provider entries and its email.
    The fake models that, so the selection rule is tested against the shape the deployed
    project actually answers with (orchestrator evidence, HOST-2 packet, cleanup finding).
    ``delete_failures`` injects a transient fault: ``{uid: n}`` fails the next ``n`` deletions of
    that uid before one succeeds, which is what the failure-and-retry test drives.
    """

    class UserNotFound(Exception):
        pass

    def __init__(self, providers, lookup_failures=(), emails=None, phones=None, log=None,
                 delete_failures=None):
        self.providers, self.lookup_failures = dict(providers), set(lookup_failures)
        self.emails, self.phones = dict(emails or {}), dict(phones or {})
        self.deleted = []
        self.log = [] if log is None else log
        self.delete_failures = dict(delete_failures or {})

    def get_user(self, uid):
        if uid in self.lookup_failures:
            raise RuntimeError('the Auth backend is unreachable')
        if uid not in self.providers:
            raise self.UserNotFound(uid)
        return types.SimpleNamespace(
            provider_data=[types.SimpleNamespace(provider_id=name)
                           for name in self.providers[uid]],
            email=self.emails.get(uid),
            phone_number=self.phones.get(uid))

    def delete_user(self, uid):
        if self.delete_failures.get(uid):
            self.delete_failures[uid] -= 1
            self.log.append(('auth-failed', uid))
            raise RuntimeError('the Auth backend is unreachable')
        self.deleted.append(uid)
        self.log.append(('auth-deleted', uid))


def membership_view(uid, tenant, case, created):
    """One membership document as the listing returns it: a mapping and a create time."""
    return types.SimpleNamespace(
        to_dict=lambda: {'uid': uid, 'tenant_id': tenant, 'case_id': case, 'active': True,
                         'can_review': True, 'source_policy_refs': [hosted.SOURCE_POLICY]},
        create_time=created)


class CleanupListing:
    """A Firestore-shaped client stub: records the collection path and streams documents."""

    def __init__(self, documents):
        self.path, self.documents = [], list(documents)

    def collection(self, name):
        self.path.append(name)
        return types.SimpleNamespace(document=self._namespace)

    def _namespace(self, item):
        self.path.append(item)
        return types.SimpleNamespace(collection=self._members)

    def _members(self, name):
        self.path.append(name)
        return types.SimpleNamespace(stream=lambda timeout=None: iter(self.documents))


class CleanupTests(unittest.TestCase):
    """H2c: the operator cleanup deletes stale judge sessions, and only those, only there."""

    NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    OLD = NOW - timedelta(hours=72)
    RECENT = NOW - timedelta(hours=1)
    OLDER_THAN = timedelta(hours=48)

    def session(self, uid, created=OLD, case=None):
        return cleanup.JudgeSession(uid, cleanup.JUDGE_TENANT, case or f'demo-{uid[-8:]}', created)

    def test_only_the_demo_namespace_may_be_cleaned(self):
        self.assertEqual('demo-judge', cleanup.resolve_namespace(None, {}))
        self.assertEqual('demo-judge', cleanup.resolve_namespace('demo-judge', {}))
        self.assertEqual('demo-judge', cleanup.resolve_namespace(' demo-judge ', {}))
        for given, environ in (('private-cases', {}), ('demo', {}), ('demo-judge-x', {}),
                               (None, {'NOWCAST_NAMESPACE': 'demo-judge'})):
            with self.assertRaises(cleanup.CleanupRefused, msg=(given, environ)):
                cleanup.resolve_namespace(given, environ)

    def test_the_cli_refuses_another_namespace_before_any_client_exists(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'deploy' / 'cleanup.py'),
                                 '--namespace', 'private-cases'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertIn('refusing namespace', result.stderr)
        self.assertEqual('', result.stdout)  # refused before any listing or client

    def test_older_than_takes_a_number_and_a_unit_only(self):
        self.assertEqual(timedelta(hours=48), cleanup.parse_older_than('48h'))
        self.assertEqual(timedelta(days=2), cleanup.parse_older_than('2d'))
        self.assertEqual(timedelta(seconds=90), cleanup.parse_older_than('90s'))
        self.assertEqual(timedelta(minutes=30), cleanup.parse_older_than('30m'))
        for value in ('soon', '48', '', 'h48', '-1h', '48 hours', '1.5h'):
            with self.assertRaises(cleanup.CleanupRefused, msg=value):
                cleanup.parse_older_than(value)

    def test_the_listing_reads_the_members_of_the_demo_namespace(self):
        documents = [membership_view('demo-abc', cleanup.JUDGE_TENANT, 'demo-abc', self.OLD)]
        client = CleanupListing(documents)
        self.assertEqual(documents, cleanup.iter_memberships(client, cleanup.DEMO_NAMESPACE))
        self.assertEqual(['h1_namespaces', 'demo-judge', 'members'], client.path)

    def test_a_membership_outside_the_judge_tenant_or_without_ids_is_malformed(self):
        good = membership_view('demo-abc', cleanup.JUDGE_TENANT, 'demo-abc', self.OLD)
        private = membership_view('analyst-uid', 'private-tenant', 'case-a', self.OLD)
        nameless = membership_view('', cleanup.JUDGE_TENANT, 'demo-abc', self.OLD)
        sessions, malformed = cleanup.read_memberships([good, private, nameless])
        self.assertEqual([cleanup.JudgeSession('demo-abc', cleanup.JUDGE_TENANT, 'demo-abc', self.OLD)],
                         sessions)
        self.assertEqual([private, nameless], malformed)

    def ages(self):
        """One session per age and identity state the selection rules distinguish."""
        return [self.session('demo-' + 'a' * 32),
                self.session('demo-' + 'b' * 32, created=self.RECENT),
                self.session('demo-' + 'c' * 32, created=None),
                self.session('demo-' + 'd' * 32),
                self.session('demo-' + 'e' * 32)]

    def providers(self):
        # Anonymous users are the real shape: empty provider_data, no email, no phone number.
        return {'demo-' + 'a' * 32: [],
                'demo-' + 'b' * 32: [],
                'demo-' + 'd' * 32: ['password'],
                'demo-' + 'e' * 32: []}

    def test_a_dry_run_deletes_nothing_and_reports_what_it_would_delete(self):
        store = CleanupStore()
        auth = CleanupAuth(self.providers(), lookup_failures={'demo-' + 'e' * 32})
        summary = cleanup.cleanup_sessions(store, auth, self.ages(), self.OLDER_THAN, self.NOW,
                                           False, not_found=CleanupAuth.UserNotFound)
        self.assertEqual([], store.cases)
        self.assertEqual([], store.members)
        self.assertEqual([], auth.deleted)
        self.assertEqual((0, 0, 0), (summary.deleted_cases(), summary.deleted_memberships(),
                                     summary.deleted_users()))
        self.assertEqual(5, summary.judge_sessions)
        self.assertEqual(3, summary.stale)  # a, d and e are old; identity decides who is removed
        self.assertEqual(1, summary.young)
        self.assertEqual(1, summary.unknown_age)
        text = '\n'.join(cleanup.describe(summary))
        self.assertIn('dry run', text)
        self.assertIn(hosted.fixture_digest(), text)
        self.assertIn('fixture digest', text)

    def test_apply_deletes_exactly_the_stale_anonymous_sessions(self):
        store = CleanupStore()
        auth = CleanupAuth(self.providers(), lookup_failures={'demo-' + 'e' * 32})
        summary = cleanup.cleanup_sessions(store, auth, self.ages(), self.OLDER_THAN, self.NOW,
                                           True, not_found=CleanupAuth.UserNotFound)
        stale = ('demo-' + 'a' * 32,)
        self.assertEqual([(cleanup.JUDGE_TENANT, self.session(uid).case) for uid in stale],
                         store.cases)
        self.assertEqual([(uid, cleanup.JUDGE_TENANT, self.session(uid).case) for uid in stale],
                         store.members)
        self.assertEqual(['demo-' + 'a' * 32], auth.deleted)  # 'd' has a non-anonymous provider
        self.assertEqual(1, len(summary.deleted))
        self.assertEqual(1, summary.deleted_cases())
        self.assertEqual(1, summary.deleted_memberships())
        self.assertEqual(1, summary.deleted_users())
        kept = {(session.uid, state) for session, state in summary.kept}
        self.assertEqual({('demo-' + 'd' * 32, 'unexpected'), ('demo-' + 'e' * 32, 'unknown')}, kept)
        young = self.session('demo-' + 'b' * 32, created=self.RECENT)
        self.assertNotIn(young.uid, [uid for uid, _, _ in store.members])

    def test_a_user_with_a_provider_an_email_or_a_phone_number_is_kept(self):
        """A real anonymous user has none of the three; any one of them is a private account.

        This is the shape the deployed project answered with: `provider_id='firebase'`,
        `provider_data=[]`, no email — while a password judge or an analyst with an email or a
        phone number must never be deleted by this command.
        """
        anonymous = 'demo-' + 'a' * 32
        password = 'demo-' + 'd' * 32
        email = 'demo-' + 'h' * 32
        phone = 'demo-' + 'i' * 32
        # A labelled synthetic phone value: the release audit scans this shipped tree and flags
        # a realistic private-data shape (ph-mobile-number), so the test carries the label, not
        # a dialable-looking number; the rule under test reads only that the field is present.
        auth = CleanupAuth({anonymous: [], password: ['password'], email: [], phone: []},
                           emails={email: 'analyst@example.test'},
                           phones={phone: 'synthetic-phone-number'})
        sessions = [self.session(uid) for uid in (anonymous, password, email, phone)]
        store = CleanupStore()
        summary = cleanup.cleanup_sessions(store, auth, sessions, self.OLDER_THAN, self.NOW, True,
                                           not_found=CleanupAuth.UserNotFound)
        self.assertEqual([(cleanup.JUDGE_TENANT, self.session(anonymous).case)], store.cases)
        self.assertEqual([anonymous], auth.deleted)
        self.assertEqual(1, summary.deleted_cases())
        kept = {(session.uid, state) for session, state in summary.kept}
        self.assertEqual({(password, 'unexpected'), (email, 'unexpected'), (phone, 'unexpected')},
                         kept)

    def test_a_session_whose_auth_user_is_absent_is_deleted_without_a_user_delete(self):
        uid = 'demo-' + 'f' * 32
        store, auth = CleanupStore(), CleanupAuth({})
        summary = cleanup.cleanup_sessions(store, auth, [self.session(uid)], self.OLDER_THAN,
                                           self.NOW, True, not_found=CleanupAuth.UserNotFound)
        self.assertEqual([(cleanup.JUDGE_TENANT, self.session(uid).case)], store.cases)
        self.assertEqual([], auth.deleted)
        # An already-absent user is done, not a failure: its membership is still removed, so a
        # retry finishes the session instead of listing it forever.
        self.assertEqual([(uid, cleanup.JUDGE_TENANT, self.session(uid).case)], store.members)
        self.assertEqual(1, summary.deleted_cases())
        self.assertEqual(0, summary.deleted_users())

    def test_the_membership_is_deleted_only_after_the_case_and_the_auth_user(self):
        """The membership is the discovery record the listing reads, so it goes last."""
        uid = 'demo-' + 'j' * 32
        log = []
        store = CleanupStore([(uid, cleanup.JUDGE_TENANT, self.session(uid).case)], log)
        auth = CleanupAuth({uid: []}, log=log)
        summary = cleanup.cleanup_sessions(store, auth, [self.session(uid)], self.OLDER_THAN,
                                           self.NOW, True, not_found=CleanupAuth.UserNotFound)
        self.assertEqual([], summary.failures)
        self.assertEqual([('case', self.session(uid).case), ('auth-deleted', uid),
                          ('membership', uid)], log)
        self.assertEqual([uid], auth.deleted)
        self.assertEqual([(uid, cleanup.JUDGE_TENANT, self.session(uid).case)], store.members)
        self.assertEqual(set(), store.held)

    def test_a_failed_auth_delete_keeps_the_membership_and_the_next_run_finishes_the_job(self):
        """A transient Auth failure must not strand a user with no record pointing at it.

        The first run fails at the Auth delete; because the membership is removed last it is
        still held, so the next run's listing returns the session again and that run deletes the
        user and then the membership.
        """
        uid = 'demo-' + 'k' * 32
        membership = (uid, cleanup.JUDGE_TENANT, self.session(uid).case)
        log = []
        store = CleanupStore([membership], log)
        auth = CleanupAuth({uid: []}, log=log, delete_failures={uid: 1})
        first = cleanup.cleanup_sessions(store, auth, [self.session(uid)], self.OLDER_THAN,
                                         self.NOW, True, not_found=CleanupAuth.UserNotFound)
        self.assertEqual(1, len(first.failures))
        self.assertEqual(uid, first.failures[0][0].uid)
        self.assertEqual([('case', self.session(uid).case), ('auth-failed', uid)], log)
        self.assertEqual([], auth.deleted)          # the Auth user survived...
        self.assertEqual({membership}, store.held)  # ... and the record that finds it survived too
        # The next run lists what is still held, exactly as iter_memberships would return it.
        documents = [membership_view(entry_uid, tenant, case, self.OLD)
                     for entry_uid, tenant, case in sorted(store.held)]
        sessions, malformed = cleanup.read_memberships(
            cleanup.iter_memberships(CleanupListing(documents), cleanup.DEMO_NAMESPACE))
        self.assertEqual([], malformed)
        second = cleanup.cleanup_sessions(store, auth, sessions, self.OLDER_THAN, self.NOW, True,
                                          not_found=CleanupAuth.UserNotFound)
        self.assertEqual([], second.failures)
        self.assertEqual([uid], auth.deleted)
        self.assertEqual(set(), store.held)
        self.assertEqual(1, second.deleted_users())
        self.assertEqual([('case', self.session(uid).case), ('auth-failed', uid),
                          ('case', self.session(uid).case), ('auth-deleted', uid),
                          ('membership', uid)], log)

    def test_a_session_whose_age_cannot_be_read_is_kept(self):
        uid = 'demo-' + 'c' * 32
        store, auth = CleanupStore(), CleanupAuth({uid: []})
        summary = cleanup.cleanup_sessions(store, auth, [self.session(uid, created=None)],
                                           self.OLDER_THAN, self.NOW, True,
                                           not_found=CleanupAuth.UserNotFound)
        self.assertEqual([], store.cases)
        self.assertEqual([], auth.deleted)
        self.assertEqual(1, summary.unknown_age)

    def test_a_failure_on_one_session_is_recorded_and_the_run_continues(self):
        class HalfBroken(CleanupStore):
            def discard_case(self, tenant, case):
                if case.endswith('a' * 8):
                    raise RuntimeError('the case delete is unavailable')
                super().discard_case(tenant, case)

        first, second = self.session('demo-' + 'a' * 32), self.session('demo-' + 'g' * 32)
        store = HalfBroken()
        auth = CleanupAuth(dict(self.providers(), **{'demo-' + 'g' * 32: []}))
        summary = cleanup.cleanup_sessions(store, auth, [first, second], self.OLDER_THAN, self.NOW,
                                           True, not_found=CleanupAuth.UserNotFound)
        self.assertEqual([(cleanup.JUDGE_TENANT, second.case)], store.cases)
        self.assertEqual(1, len(summary.failures))
        self.assertEqual(first.uid, summary.failures[0][0].uid)
        self.assertEqual(1, summary.deleted_cases())
        self.assertEqual([second.uid], auth.deleted)
        self.assertTrue(any('failures:' in line and line.rstrip().endswith('1')
                            for line in cleanup.describe(summary)))


if __name__ == '__main__':
    unittest.main()
