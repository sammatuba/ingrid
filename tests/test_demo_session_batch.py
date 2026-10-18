"""PERF-2: one prepared batch per judge case instead of one transaction per record.

Before this task every `register_case`, `register` and `seed_assumption` call was its own
`PersistentRepository.execute` — a whole-case load plus a CAS commit, 20 of them for one
judge session (5 for the synthetic case, 15 for the PEDC event case; `POST /demo/session`
p50 3.22 s through the deployed front door, docs/work/performance/baseline.md). Each case
is now seeded by one prepared batch: the case is loaded once, every operation is applied to
the decoded service in memory, and the complete state is committed once.

This module holds the offline half of the evidence, on the bare interpreter and with no SDK:

* one load and one commit per case, and each commit carried that case's whole state;
* the batched seed's committed state is byte-identical to the per-record seed's, for the
  labelled synthetic case (with and without the ambiguous mapping) and for the real PEDC
  event case;
* a failure injected at every provisioning phase leaves no case document, no membership and
  no sandbox session behind, and answers the intent's 503;
* the whole-case commit stays inside the Firestore transaction write bound;
* the batch can reach only the three provisioning ports, and the generation CAS still
  refuses a writer that prepared before another commit.

`SessionProvisioningOnEmulators` runs the same properties against the real Firestore
emulator through the hosted store. `tests/integration/test_m3.py` imports this module so
that class is collected by `bash scripts/h1/test.sh`, this task's verify command; with no
emulator configured the class skips itself, so the offline suite stays green on its own.
Nothing here contacts anything but the loopback emulator, and no case fact is invented.
"""
import contextlib
import importlib.util
import os
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.demo import pedc, records as demo_records, seed as demo_seed
from src.review import ActorContext, ReviewError, reference
from src.review.repository import PROVISION_PORTS, ReviewService
from src.review.storage import (
    PersistentRepository, RetryPreparation, StorageUnavailable, TRANSACTION_WRITE_LIMIT, decode,
)

# The hosted assembly is loaded by file location exactly as tests/test_hosted_config.py does:
# it stays testable with the bare interpreter, so no FastAPI and no Google SDK is imported at
# module scope here.
SPEC = importlib.util.spec_from_file_location('nowcast_hosted', ROOT / 'src' / 'api' / 'hosted.py')
hosted = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hosted)

EMULATOR = os.environ.get('FIRESTORE_EMULATOR_HOST')
PROJECT = 'demo-nowcast-h1'
#: The two cases' entry counts, measured on this tree. `provision` commits a whole case in one
#: transaction, so a case's entry count is also the write count of its commit.
SYNTHETIC_ENTRIES = 16
PEDC_ENTRIES = 37
#: The stores' own bound on one commit (src/api/hosted.py, src/adapters/firestore/__init__.py);
#: TRANSACTION_WRITE_LIMIT counts the case root document on top of the changed entries.
COMMIT_CHANGE_LIMIT = 450
PEDC_AT = '2026-10-14T09:00:00+08:00'
MARKER_KEY = '["stale", ["a concurrent writer"]]'
MARKER_VALUE = '"a concurrent writer"'
#: The five phases a session creation passes through, each with one failure injected.
PHASES = ('before load', 'during apply', 'at commit, one case already committed',
          'after the first case, at the event case commit', 'at the second membership')


def synthetic_actor(uid='demo-batch-fixture'):
    """The actor a sandbox session gets for its own copy of the labelled fixture case."""
    case = hosted.session_case(uid)
    return ActorContext(uid, hosted.JUDGE_TENANT, frozenset({case}), frozenset({hosted.SOURCE_POLICY}), True)


def pedc_actor(uid='demo-batch-pedc'):
    """The actor a sandbox session gets for its own copy of the real PEDC event case."""
    case = hosted.event_case(uid)
    return ActorContext(uid, hosted.JUDGE_TENANT, frozenset({case}), frozenset({pedc.PERMISSION_REF}), True)


class CountingStore(hosted.MemoryStore):
    """The demo store with every transaction call recorded; nothing else changes."""

    def __init__(self):
        super().__init__()
        self.loads, self.commits, self.writes = [], [], []

    def load(self, actor, case):
        self.loads.append(case)
        return super().load(actor, case)

    def commit(self, actor, case, before, after):
        changed = {key: value for key, value in after.items() if before.entries.get(key) != value}
        self.commits.append(case)
        self.writes.append((case, len(changed), len(after)))
        return super().commit(actor, case, before, after)


def stored(store, case, tenant=hosted.JUDGE_TENANT):
    """The in-process store's own document for one case; None means nothing was written.

    The emulator class reads the same thing back from Firestore as documents instead.
    """
    return store._cases.get((tenant, case))


def per_record(repository, actor, case, operations):
    """Apply prepared operations one port call at a time: the pre-PERF-2 write shape.

    Each call is its own `PersistentRepository.execute`, exactly as the seeding code did
    before this task, so this is the reference the batched seed is compared against.
    """
    return [getattr(repository, name)(actor, *args, **kwargs) for name, args, kwargs in operations]


def admit(store, actor, case):
    """Write the membership document provisioning writes, so the store will load the case.

    The document is the same six keys `current_actor` validates; the source policies come
    from the actor, which is what `_provision` passes for each of a session's two cases.
    """
    store.member_ref(actor.actor_id, actor.tenant_id, case).set(
        hosted.membership_document(actor.actor_id, actor.tenant_id, case,
                                   sorted(actor.source_policy_refs)))


class _FailingRef:
    """A membership reference whose write fails; every other operation delegates."""

    def __init__(self, ref, fail):
        self._ref, self._fail = ref, fail

    def set(self, mapping):
        if self._fail:
            raise StorageUnavailable()
        return self._ref.set(mapping)

    def __getattr__(self, name):
        return getattr(self._ref, name)


class PhaseStore:
    """A store with one failure injected at a named phase of a session's provisioning.

    The phases are the ones a session creation passes through: the first case's load, the
    in-memory apply (a service failure, injected by the caller), the first case's commit, the
    event case's commit — by then the first case is committed — and the event case's
    membership write. The second case is recognised by the case-id prefix `hosted.event_case`
    gives it, so a failure can name the phase without knowing the session's uid.
    """

    def __init__(self, store, phase):
        self.store, self.phase = store, phase

    def is_event_case(self, case):
        return case.startswith(pedc.CASE_PREFIX)

    def member_ref(self, uid, tenant, case):
        return _FailingRef(self.store.member_ref(uid, tenant, case),
                           self.phase == 'at the second membership' and self.is_event_case(case))

    def membership(self, uid, tenant, case):
        return self.store.membership(uid, tenant, case)

    def load(self, actor, case):
        if self.phase == 'before load':
            raise StorageUnavailable()
        return self.store.load(actor, case)

    def commit(self, actor, case, before, after):
        if self.phase == 'at commit, one case already committed' and not self.is_event_case(case):
            raise StorageUnavailable()
        if self.phase == 'after the first case, at the event case commit' and self.is_event_case(case):
            raise StorageUnavailable()
        return self.store.commit(actor, case, before, after)

    def discard_case(self, tenant, case):
        return self.store.discard_case(tenant, case)


class RecordingIdentity(hosted.SandboxIdentity):
    """The sandbox identity that keeps the session it admitted, so a failure can name it."""

    def __init__(self, fixture, **kwargs):
        super().__init__(fixture, **kwargs)
        self.opened = []

    def open_session(self, session):
        self.opened.append(session)
        return super().open_session(session)


class AnonymousIdentity:
    """The hosted path's identity, stubbed: one uid and token, no Auth call, no deletion."""

    def __init__(self, uid='firebase-batch-uid'):
        self.uid, self.calls = uid, 0

    def anonymous_session(self):
        self.calls += 1
        return 'anonymous-token', self.uid


def provision_failure(phase, store, mode=hosted.DEMO_MODE):
    """Create one judge session whose provisioning fails at ``phase``, and require the 503.

    Returns ``(session, identity)``: the session the identity admitted — so the caller can
    name the two case ids and the membership documents — and the identity the cleanup had to
    unregister. Any answer other than 503 `SESSION_UNAVAILABLE` fails the test, and any other
    exception propagates as itself.
    """
    fixture = hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE)
    identity = RecordingIdentity(fixture) if mode == hosted.DEMO_MODE else AnonymousIdentity()
    repository = PersistentRepository(store)
    service_failure = (patch.object(ReviewService, 'seed_assumption',
                                    side_effect=ReviewError('MISSING_INPUT'))
                       if phase == 'during apply' else contextlib.nullcontext())
    with service_failure:
        try:
            hosted.create_judge_session(mode, store, identity, repository)
        except hosted.SessionUnavailable:
            pass
        else:
            raise AssertionError('a failure at %r must answer SESSION_UNAVAILABLE' % (phase,))
    if mode == hosted.DEMO_MODE:
        return identity.opened[0], identity
    return (hosted.Session(identity.uid, hosted.JUDGE_TENANT, hosted.session_case(identity.uid),
                           hosted.event_case(identity.uid), ''), identity)


class ProvisioningShapeTests(unittest.TestCase):
    """One prepared batch per case: what a session creation reads, writes and may call."""

    def session(self):
        store = CountingStore()
        repository = PersistentRepository(store)
        identity = hosted.SandboxIdentity(hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE))
        session, token = hosted.create_judge_session(hosted.DEMO_MODE, store, identity, repository)
        return store, session, token

    def test_a_session_seeds_each_case_in_one_load_and_one_commit(self):
        store, session, token = self.session()
        self.assertEqual([session.case, session.event_case], sorted(store.commits))
        for case in (session.case, session.event_case):
            self.assertEqual(1, store.loads.count(case), case)
            self.assertEqual(1, store.commits.count(case), case)
        # Each commit carried that case's whole state, so the case was never half-written.
        writes = {case: (changed, total) for case, changed, total in store.writes}
        self.assertEqual((SYNTHETIC_ENTRIES, SYNTHETIC_ENTRIES), writes[session.case])
        self.assertEqual((PEDC_ENTRIES, PEDC_ENTRIES), writes[session.event_case])
        self.assertTrue(token)
        self.assertEqual(session.uid, hosted._event_actor(session).actor_id)

    def test_a_reset_reseeds_the_case_in_one_prepared_batch(self):
        store = CountingStore()
        repository = PersistentRepository(store)
        identity = hosted.SandboxIdentity(hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE))
        session, _ = hosted.create_judge_session(hosted.DEMO_MODE, store, identity, repository)
        store.loads.clear(), store.commits.clear(), store.writes.clear()
        hosted.reset_session(store, identity, repository, session.uid)
        self.assertEqual([session.case], store.loads)
        self.assertEqual([session.case], store.commits)
        self.assertEqual(SYNTHETIC_ENTRIES, store.writes[0][1])
        self.assertEqual(len(stored(store, session.case)['entries']), store.writes[0][2])

    def test_the_batch_can_reach_only_the_provisioning_ports(self):
        actor = pedc_actor()
        case = next(iter(actor.accessible_cases))
        store = CountingStore()
        repository = PersistentRepository(store)
        self.assertEqual(('register_case', 'register', 'seed_assumption'), PROVISION_PORTS)
        for name in ('commit_review', 'build_snapshot', 'compile_task', 'read', 'workspace',
                     'save_bundle', 'prepare_scenario', 'export_scenario'):
            for target in (repository, ReviewService()):
                with self.assertRaises(ReviewError) as caught:
                    target.provision(actor, case, [(name, (), {})])
                self.assertEqual('ACCESS_DENIED', caught.exception.code, name)
        self.assertEqual([], store.commits)  # a refused batch writes nothing at all

    def test_the_generation_cas_still_refuses_a_writer_that_prepared_earlier(self):
        store, session, _ = self.session()
        actor = hosted._actor(session)
        stale = store.load(actor, session.case)
        current = store.load(actor, session.case)
        self.assertEqual(stale.generation, current.generation)
        store.commit(actor, session.case, current, dict(current.entries, **{MARKER_KEY: MARKER_VALUE}))
        self.assertGreater(store.load(actor, session.case).generation, stale.generation)
        with self.assertRaises(RetryPreparation):
            store.commit(actor, session.case, stale, dict(stale.entries, **{MARKER_KEY: '"mine"'}))
        self.assertEqual(MARKER_VALUE, store.load(actor, session.case).entries[MARKER_KEY])


class IdenticalStateTests(unittest.TestCase):
    """The batched seed's committed state is the per-record seed's, byte for byte.

    ``Snapshot.entries`` is the case state the ``h1.state.v1`` codec holds — canonical JSON
    text per key, records, heads, history and receipts included — so equality there is
    equality of the encoded case, not a summary of it.
    """

    def seed(self, actor, case, operations, batched):
        """Seed one case over a fresh counting store, as one batch or one port call at a time."""
        store = CountingStore()
        repository = PersistentRepository(store)
        admit(store, actor, case)
        applied = operations()
        results = (repository.provision(actor, case, applied) if batched
                   else per_record(repository, actor, case, applied))
        return store, results

    def assert_identical(self, actor, case, operations):
        batch_store, batch_results = self.seed(actor, case, operations, batched=True)
        plain_store, plain_results = self.seed(actor, case, operations, batched=False)
        self.assertEqual(plain_store.load(actor, case).entries, batch_store.load(actor, case).entries)
        self.assertEqual(stored(plain_store, case)['entries'], stored(batch_store, case)['entries'])
        # Every record the two paths returned is the same record, in the same order.
        self.assertEqual([reference(record) for record in plain_results],
                         [reference(record) for record in batch_results])
        # They differ only in how many commits it took to store that one state: the batch
        # advances the case's generation once, the per-record path once per call.
        self.assertEqual(1, len(batch_store.commits))
        self.assertEqual(1, stored(batch_store, case)['generation'])
        self.assertEqual(len(plain_results), len(plain_store.commits))
        self.assertEqual(len(plain_results), stored(plain_store, case)['generation'])
        self.assertGreater(len(plain_store.commits), 1)
        return batch_store, plain_store

    def test_the_synthetic_case_is_byte_identical_to_the_per_record_seed(self):
        actor = synthetic_actor()
        case = next(iter(actor.accessible_cases))
        batch_store, plain_store = self.assert_identical(
            actor, case, lambda: demo_records(actor)['operations'])
        self.assertEqual(SYNTHETIC_ENTRIES, batch_store.writes[0][1])
        self.assertEqual(5, len(plain_store.commits))

    def test_the_ambiguous_fixture_case_is_byte_identical_too(self):
        # scripts/m3/seed.py seeds a second case with `ambiguous=True`; it batches the same way.
        actor = synthetic_actor('demo-batch-ambiguous')
        case = next(iter(actor.accessible_cases))
        batch_store, _ = self.assert_identical(
            actor, case, lambda: demo_records(actor, ambiguous=True)['operations'])
        service = decode(batch_store.load(actor, case).entries)
        self.assertEqual({'1', '2'}, {key[4] for key in service._records if key[2] == 'MappingRevision'})

    def test_the_pedc_event_case_is_byte_identical_to_the_per_record_seed(self):
        actor = pedc_actor()
        case = next(iter(actor.accessible_cases))
        # The operations the production seed applies, prepared once and replayed per record.
        built = pedc.build_records(actor.tenant_id, case, actor.actor_id, PEDC_AT)
        plain_store = CountingStore()
        admit(plain_store, actor, case)
        plain_results = per_record(PersistentRepository(plain_store), actor, case,
                                   pedc.batch(built, PEDC_AT))
        # The production batch itself, over a fresh store.
        batch_store = CountingStore()
        admit(batch_store, actor, case)
        batch_built = pedc.seed(PersistentRepository(batch_store), actor, case, PEDC_AT)
        self.assertEqual(plain_store.load(actor, case).entries, batch_store.load(actor, case).entries)
        self.assertEqual(stored(plain_store, case)['entries'], stored(batch_store, case)['entries'])
        self.assertEqual(15, stored(plain_store, case)['generation'])  # one commit per port call
        self.assertEqual(1, stored(batch_store, case)['generation'])   # one commit for the case
        # The seed acceptance the judge decides on is the same record, and every record the
        # per-record path returned is the one the batch wrote.
        self.assertEqual(reference(plain_results[-1]), reference(batch_built['assumption_record']))
        self.assertEqual(built['assumption'], batch_built['assumption'])
        self.assertEqual(PEDC_ENTRIES, batch_store.writes[0][1])
        self.assertEqual(1, len(batch_store.commits))
        self.assertEqual(len(plain_results), len(plain_store.commits))
        self.assertEqual(15, len(plain_store.commits))


class TransactionBoundTests(unittest.TestCase):
    """A whole case is one transaction, so the case has to fit in one transaction.

    One commit writes one document per changed entry plus the case root, so the case's entry
    count is the write count a whole-case commit has to keep inside Firestore's per-transaction
    write limit. The bound is asserted here for both cases, and re-counted on the emulator.
    """

    def counted(self, actor, case, seed):
        """Seed one case on a fresh store and return its single commit's (changed, total)."""
        store = CountingStore()
        admit(store, actor, case)
        seed(store)
        self.assertEqual([case], store.commits)
        return store.writes[0][1:]

    def test_both_cases_commit_their_whole_state_in_one_commit_inside_the_bound(self):
        actor = synthetic_actor()
        synthetic = self.counted(actor, next(iter(actor.accessible_cases)),
                                 lambda store: demo_seed(PersistentRepository(store), actor))
        actor = pedc_actor()
        event = self.counted(actor, next(iter(actor.accessible_cases)),
                             lambda store: pedc.seed(PersistentRepository(store), actor,
                                                     next(iter(actor.accessible_cases)), PEDC_AT))
        self.assertEqual((SYNTHETIC_ENTRIES, SYNTHETIC_ENTRIES), synthetic)
        self.assertEqual((PEDC_ENTRIES, PEDC_ENTRIES), event)
        for changed, total in (synthetic, event):
            self.assertEqual(changed, total)                     # the whole case, one commit
            self.assertLessEqual(changed, COMMIT_CHANGE_LIMIT)   # the store's own change bound
            self.assertLessEqual(changed + 1, TRANSACTION_WRITE_LIMIT)  # + the case root


class ProvisioningFailureTests(unittest.TestCase):
    """A refused session leaves no case, no membership and no sandbox session behind."""

    def test_a_failure_at_every_phase_leaves_no_case_no_membership_and_no_token(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                inner = hosted.MemoryStore()
                session, identity = provision_failure(phase, PhaseStore(inner, phase))
                self.assertEqual(1, len(identity.opened))  # the session was admitted ...
                for case in (session.case, session.event_case):
                    self.assertIsNone(stored(inner, case), case)
                    self.assertIsNone(inner.membership(session.uid, session.tenant, case), case)
                self.assertEqual({}, identity._sessions)   # ... and then unregistered:
                self.assertEqual({}, identity._tokens)     # its token names nothing now.

    def test_a_hosted_failure_keeps_the_anonymous_identity_and_drops_both_cases(self):
        # The hosted path deletes no Auth user (no request may); the HOST-2 operator reset owns
        # that. What must be gone is every write this provisioning made.
        inner = hosted.MemoryStore()
        store = PhaseStore(inner, 'at the second membership')
        session, identity = provision_failure('at the second membership', store, mode=hosted.HOSTED_MODE)
        self.assertEqual(1, identity.calls)
        self.assertFalse(hasattr(identity, 'discard_session'))
        for case in (session.case, session.event_case):
            self.assertIsNone(stored(inner, case), case)
            self.assertIsNone(inner.membership(session.uid, session.tenant, case), case)


class CountingTransactions:
    """The emulator store with its transaction calls recorded; nothing else changes.

    Everything else delegates to the store under test, so the code exercised is the
    production `HostedFirestoreStore`; only the count of loads and commits is this wrapper's.
    """

    def __init__(self, store):
        self.store, self.loads, self.commits = store, [], []

    def member_ref(self, uid, tenant, case):
        return self.store.member_ref(uid, tenant, case)

    def membership(self, uid, tenant, case):
        return self.store.membership(uid, tenant, case)

    def load(self, actor, case):
        self.loads.append(case)
        return self.store.load(actor, case)

    def commit(self, actor, case, before, after):
        changed = {key: value for key, value in after.items() if before.entries.get(key) != value}
        self.commits.append((case, len(changed), len(after)))
        return self.store.commit(actor, case, before, after)

    def discard_case(self, tenant, case):
        return self.store.discard_case(tenant, case)


@unittest.skipUnless(EMULATOR, 'the Firestore emulator is not configured for this run; '
                               'run bash scripts/h1/test.sh')
class SessionProvisioningOnEmulators(unittest.TestCase):
    """PERF-2's evidence on the real Firestore emulator, through the hosted store.

    `tests/integration/test_m3.py` imports this module, so `bash scripts/h1/test.sh` -- this
    task's verify command -- collects this class. Every judge case here is written in one
    commit and read back through Firestore, so the one-load/one-commit shape, the whole-case
    write count, the failure phases and the generation CAS are checked against the service
    the deployed demo writes to, not against the in-process stand-in.
    """

    @classmethod
    def setUpClass(cls):
        from google.auth.credentials import AnonymousCredentials
        from google.cloud import firestore
        cls.client = firestore.Client(project=PROJECT, credentials=AnonymousCredentials())

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def namespace(self):
        """One test's own namespace, deleted again whatever the test does."""
        name = 'perf2-' + uuid.uuid4().hex[:12]
        self.addCleanup(self.remove_namespace, name)
        return name

    def remove_namespace(self, name):
        def remove(ref):
            for collection in ref.collections():
                for child in collection.list_documents():
                    remove(child)
            ref.delete()
        remove(self.client.collection('h1_namespaces').document(name))

    def host_store(self, name):
        """The hosted store on the emulator: the deployed class over the Firestore client."""
        return hosted.hosted_store(PROJECT, name, self.client)

    def judge_store(self, store):
        """The judge routing the assembly uses; every tenant here is the judge tenant."""
        return hosted.NamespaceStore(store, store)

    def documents(self, store, case, tenant=hosted.JUDGE_TENANT):
        """The case's entry documents as the emulator holds them: one commit's write set."""
        return list(store.case_ref(tenant, case).collection('entries').stream(timeout=10))

    def open_session(self, store):
        identity = hosted.SandboxIdentity(hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE))
        return hosted.create_judge_session(hosted.DEMO_MODE, store, identity, PersistentRepository(store))

    def source_policy(self, repository, session, case):
        """The access policy of the source the case's seeded assumption is mapped through."""
        actor = hosted._actor(session) if case == session.case else hosted._event_actor(session)
        workspace = repository.workspace(actor, case)
        mapping = repository.read(actor, case, workspace['assumptions'][0]['payload']['mapping_ref'])
        source = repository.read(actor, case, mapping['payload']['source_refs'][0])
        return source['payload']['access_policy_ref']

    def test_one_load_and_one_commit_per_case_and_the_whole_case_lands_at_once(self):
        inner = self.host_store(self.namespace())
        store = CountingTransactions(self.judge_store(inner))
        session, token = self.open_session(store)
        self.assertEqual([session.case, session.event_case], [case for case, _, _ in store.commits])
        for case in (session.case, session.event_case):
            self.assertEqual(1, store.loads.count(case), case)
        writes = {case: (changed, total) for case, changed, total in store.commits}
        self.assertEqual((SYNTHETIC_ENTRIES, SYNTHETIC_ENTRIES), writes[session.case])
        self.assertEqual((PEDC_ENTRIES, PEDC_ENTRIES), writes[session.event_case])
        # Every one of those entries is really in Firestore and there is no other document
        # under either case: the case appeared complete because one transaction wrote it.
        for case, expected in ((session.case, SYNTHETIC_ENTRIES),
                               (session.event_case, PEDC_ENTRIES)):
            self.assertEqual(expected, len(self.documents(inner, case)), case)
        self.assertTrue(token)

    def test_the_pedc_case_stays_inside_the_transaction_write_bound_on_firestore(self):
        inner = self.host_store(self.namespace())
        session, _ = self.open_session(self.judge_store(inner))
        written = len(self.documents(inner, session.event_case))
        self.assertEqual(PEDC_ENTRIES, written)
        self.assertLessEqual(written, COMMIT_CHANGE_LIMIT)
        self.assertLessEqual(written + 1, TRANSACTION_WRITE_LIMIT)  # + the case root document

    def test_a_failure_at_every_phase_leaves_no_document_no_membership_and_no_token(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                inner = self.host_store(self.namespace())
                session, identity = provision_failure(phase, PhaseStore(self.judge_store(inner), phase))
                for case in (session.case, session.event_case):
                    self.assertEqual([], self.documents(inner, case), case)
                    self.assertIsNone(inner.membership(session.uid, session.tenant, case), case)
                self.assertEqual({}, identity._sessions)
                self.assertEqual({}, identity._tokens)

    def test_two_concurrent_sessions_are_isolated_and_each_reads_only_its_own_cases(self):
        inner = self.host_store(self.namespace())
        store = self.judge_store(inner)
        identity = hosted.SandboxIdentity(hosted.Session(hosted.UID, hosted.TENANT, hosted.CASE))
        repository = PersistentRepository(store)
        barrier = Barrier(2)

        def open_one(_):
            barrier.wait(timeout=60)  # both provisionings really overlap
            return hosted.create_judge_session(hosted.DEMO_MODE, store, identity, repository)

        with ThreadPoolExecutor(2) as pool:
            (first, first_token), (second, second_token) = pool.map(open_one, range(2))
        self.assertNotEqual(first.uid, second.uid)
        self.assertNotEqual(first.case, second.case)
        for session, token in ((first, first_token), (second, second_token)):
            self.assertEqual(session.uid, identity.verify('Bearer ' + token))
            self.assertEqual(SYNTHETIC_ENTRIES, len(self.documents(inner, session.case)))
            self.assertEqual(PEDC_ENTRIES, len(self.documents(inner, session.event_case)))
            # Each case holds its own records: the labelled fixture's synthetic policy on the
            # session's own case, the signed permission on its own copy of the real case.
            self.assertEqual(hosted.SOURCE_POLICY, self.source_policy(repository, session, session.case))
            self.assertEqual(pedc.PERMISSION_REF, self.source_policy(repository, session, session.event_case))
        for actor, other in ((hosted._actor(first), second), (hosted._actor(second), first)):
            with self.assertRaises(ReviewError) as caught:
                repository.workspace(actor, other.case)
            self.assertEqual('ACCESS_DENIED', caught.exception.code)
            self.assertIsNone(store.membership(actor.actor_id, actor.tenant_id, other.case))

    def test_the_generation_cas_refuses_a_writer_that_prepared_earlier_on_firestore(self):
        store = self.judge_store(self.host_store(self.namespace()))
        session, _ = self.open_session(store)
        actor = hosted._actor(session)
        stale, current = store.load(actor, session.case), store.load(actor, session.case)
        self.assertEqual(stale.generation, current.generation)
        store.commit(actor, session.case, current,
                     dict(current.entries, **{MARKER_KEY: MARKER_VALUE}))
        self.assertGreater(store.load(actor, session.case).generation, stale.generation)
        with self.assertRaises(RetryPreparation):
            store.commit(actor, session.case, stale,
                         dict(stale.entries, **{MARKER_KEY: '"mine"'}))
        self.assertEqual(MARKER_VALUE, store.load(actor, session.case).entries[MARKER_KEY])
