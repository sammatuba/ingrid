"""Hosted assembly: the container's demo and hosted modes over the unchanged H1 application.

FastAPI, the Google clients and firebase_admin are imported inside the factories and the
adapter constructors, so importing this module performs no network call, builds no client and
needs no SDK: the configuration surface and the in-process demo store are testable with the
bare interpreter. `create_app`, `src/api/local.py` and `src/demo` are reused unchanged; the
demo session, the session-local reset and the mode value on `/health` are additive here.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from src.adapters.identity import AuthenticationFailed, FirebaseIdentity
from src.contracts.jsonutil import canonical_dumps
from src.demo import CASE, EMAIL, PASSWORD, TENANT, UID, pedc, seed
from src.review import ActorContext
from src.review.errors import ReviewError, require
from src.review.storage import (
    PersistentRepository, RetryPreparation, Snapshot, StorageUnavailable, current_actor,
)

LOCAL_MODE, DEMO_MODE, HOSTED_MODE = 'local', 'demo', 'hosted'
MODES = (LOCAL_MODE, DEMO_MODE, HOSTED_MODE)
JUDGE_TENANT = 'demo-judge'
DEMO_NAMESPACE_DEFAULT = 'demo-judge'
SOURCE_POLICY = 'synthetic-public'
MAX_TOKEN = 16384
# The demo sandbox's in-process growth is two case copies, two memberships and a token per
# session: the synthetic corpus (10.2 KiB of entries) and the judge's copy of the real PEDC
# event case (32.7 KiB, GRID-3), which together take about 24 ms to provision and hold 43 KiB
# in process, measured on the GRID-3 worktree. At 512 sessions that is about 22 MiB. At the cap
# a *new* session is refused with 503 `SESSION_UNAVAILABLE`: no live session, token or case is
# ever evicted, so one client cannot end another judge's walkthrough, and the operator restart
# stays the only reset. (The HOST-1 interim review measured the corpus alone: 16.6 KiB and 12 ms.)
MAX_SANDBOX_SESSIONS = 512
# Firestore allows 500 writes per batch; `discard_case` deletes in chunks below that limit.
DELETE_BATCH = 400
EMULATOR_VARIABLES = ('FIRESTORE_EMULATOR_HOST', 'FIREBASE_AUTH_EMULATOR_HOST')
LOCAL_PROJECT = re.compile(r'demo-[a-z0-9-]+')
NAMESPACE = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?')
IDENTITY_TOOLKIT = 'https://identitytoolkit.googleapis.com/v1/accounts:'

MESSAGES = {
    'UNKNOWN_MODE': 'NOWCAST_ENV is not a known runtime mode',
    'LOCAL_MODE_REFUSED': 'local mode is served by src.api.local, not the hosted assembly',
    'EMULATOR_CONFIGURATION': 'emulator host variables are refused outside local mode',
    'MISSING_CONFIGURATION': 'hosted mode requires every named setting',
    'CONFLICTING_CONFIGURATION': 'hosted settings conflict with the local project pattern or the demo namespace',
}


class HostedConfigurationError(ValueError):
    """Fixed, safe startup refusal: the process exits instead of serving."""

    def __init__(self, code='MISSING_CONFIGURATION'):
        self.code = code
        super().__init__(MESSAGES[code])


class SessionUnavailable(Exception):
    """A sandbox session could not be provisioned; never a downgrade into another identity."""


@dataclass(frozen=True)
class Settings:
    mode: str
    project: str = ''
    web_api_key: str = ''
    namespace: str = ''
    demo_namespace: str = DEMO_NAMESPACE_DEFAULT
    port: int = 8080


@dataclass(frozen=True)
class Session:
    """One sandbox session: its synthetic case, and the judge's copy of the event case.

    `event_case` is empty for the fixture session (`src/demo`'s fictional analyst, whose
    walkthrough has no event review): a judge session provisions its second case, and
    `event_seeded_at` is the instant that case was built, which the event adapter passes
    back as the audit cutoff of the snapshot it reads before deciding.
    """

    uid: str
    tenant: str
    case: str
    event_case: str = ''
    event_seeded_at: str = ''


@dataclass
class Runtime:
    """One assembled mode: settings, store, identity, repository and the fixture constant."""

    settings: Settings
    store: object
    identity: object
    repository: PersistentRepository
    digest: str
    alerts: object = None  # AlertsWiring: portfolio settings and email alerts (src/alerts)
    journal: object = None  # JournalWiring: the Trader's Journal (src/journal)
    agent: object = None  # AgentWiring: the desk agent's store and session (src/agent, DOCK-5)

    def application(self):
        """The ASGI application over this runtime; needs FastAPI, which the assembly imports."""
        return _assemble(self)


def _environ(environ=None):
    return os.environ if environ is None else environ


def _refuse_emulators(env):
    for name in EMULATOR_VARIABLES:
        if env.get(name):
            raise HostedConfigurationError('EMULATOR_CONFIGURATION')


def select_mode(environ=None):
    """Unset means demo: a container started with no environment is safe and credential-free."""
    value = _environ(environ).get('NOWCAST_ENV') or DEMO_MODE
    if value not in MODES:
        raise HostedConfigurationError('UNKNOWN_MODE')
    return value


def demo_settings(environ=None):
    env = _environ(environ)
    _refuse_emulators(env)
    return Settings(DEMO_MODE)


def hosted_settings(environ=None):
    """Every named value is required; any missing or conflicting value refuses to start."""
    env = _environ(environ)
    _refuse_emulators(env)
    project = (env.get('GCLOUD_PROJECT') or '').strip()
    if not project:
        raise HostedConfigurationError('MISSING_CONFIGURATION')
    if LOCAL_PROJECT.fullmatch(project):
        raise HostedConfigurationError('CONFLICTING_CONFIGURATION')
    web_api_key = (env.get('FIREBASE_WEB_API_KEY') or '').strip()
    namespace = (env.get('NOWCAST_NAMESPACE') or '').strip()
    if not web_api_key or not namespace:
        raise HostedConfigurationError('MISSING_CONFIGURATION')
    demo_namespace = (env.get('NOWCAST_DEMO_NAMESPACE') or DEMO_NAMESPACE_DEFAULT).strip()
    if namespace == demo_namespace or not NAMESPACE.fullmatch(namespace) or not NAMESPACE.fullmatch(demo_namespace):
        raise HostedConfigurationError('CONFLICTING_CONFIGURATION')
    # Only an absent PORT takes the 8080 default: an explicitly blank value is a conflict, like
    # every other blank named setting, and never silently becomes the default.
    port = '8080' if env.get('PORT') is None else str(env.get('PORT'))
    if not port.isdigit() or not 0 < int(port) < 65536:
        raise HostedConfigurationError('CONFLICTING_CONFIGURATION')
    return Settings(HOSTED_MODE, project=project, web_api_key=web_api_key,
                    namespace=namespace, demo_namespace=demo_namespace, port=int(port))


def settings(environ=None):
    """Validate the whole environment for the selected mode before any client is built."""
    mode = select_mode(environ)
    if mode == LOCAL_MODE:
        raise HostedConfigurationError('LOCAL_MODE_REFUSED')
    return hosted_settings(environ) if mode == HOSTED_MODE else demo_settings(environ)


def session_case(uid):
    """One isolated case per session: `demo-` plus 16 hex digits of the session id's SHA-256."""
    return 'demo-' + hashlib.sha256(uid.encode('utf-8')).hexdigest()[:16]


def event_case(uid):
    """The session's own copy of the real PEDC event case: `pedc-` plus the same 16 digits.

    A case of its own, never the session's synthetic case: the case record fixes a case's
    provenance for every record it holds, and a real record cannot live in the synthetic
    corpus's case (h0.v2, `CASE_PROVENANCE_MISMATCH`). Two judges therefore hold two
    independent copies of the case, and one judge's decision is not the other's history.
    """
    return pedc.CASE_PREFIX + hashlib.sha256(uid.encode('utf-8')).hexdigest()[:16]


def membership_document(uid, tenant, case, source_policies=(SOURCE_POLICY,)):
    """The six keys `current_actor` validates; the same shape scripts/m3/seed.py writes.

    The event case's membership grants the signed permission's source policy and nothing
    else, so a judge session reads the real records of its own copy of that case and the
    synthetic corpus of its own case, and no other.
    """
    return {'uid': uid, 'tenant_id': tenant, 'case_id': case, 'active': True,
            'can_review': True, 'source_policy_refs': list(source_policies)}


class _MemberRef:
    """The store's membership write: no route reaches this, only startup and session creation.

    `delete` is the failure-path rollback `_discard` runs; the reset path never touches a
    membership, and no route reaches either operation.
    """

    def __init__(self, store, key):
        self._store, self._key = store, key

    def set(self, mapping):
        with self._store._lock:
            self._store._members[self._key] = dict(mapping)

    def delete(self):
        with self._store._lock:
            self._store._members.pop(self._key, None)


class MemoryStore:
    """In-process TransactionStore for demo mode: the port's checks are re-run, never relaxed.

    `load` and `commit` re-run `current_actor` against the stored membership and re-check the
    generation exactly as the Firestore store does, including its entry and change limits;
    nothing is written to disk or to any service.
    """

    def __init__(self):
        self._lock = RLock()
        self._cases = {}
        self._members = {}

    def member_ref(self, uid, tenant, case):
        return _MemberRef(self, (uid, tenant, case))

    def membership(self, uid, tenant, case):
        # Read under the same lock every writer holds, for symmetry with the Firestore store.
        with self._lock:
            stored = self._members.get((uid, tenant, case))
            return dict(stored) if stored is not None else None

    def load(self, actor, case):
        with self._lock:
            membership = self.membership(actor.actor_id, actor.tenant_id, case)
            current_actor(actor, case, membership)
            stored = self._cases.get((actor.tenant_id, case))
            if stored is not None:
                require(stored['codec'] == 'h1.state.v1')
                return Snapshot(stored['generation'], dict(stored['entries']), membership)
            return Snapshot(0, {}, membership)

    def commit(self, actor, case, before, after):
        changed = {k: v for k, v in after.items() if before.entries.get(k) != v}
        require(set(before.entries) <= set(after))
        require(len(after) <= 2000 and len(changed) <= 450)
        require(sum(len(k.encode()) + len(v.encode()) for k, v in after.items()) <= 8 * 1024 * 1024)
        require(all(len(k.encode()) + len(v.encode()) < 900 * 1024 for k, v in after.items()))
        for key in changed:
            if key.startswith('["records",'):
                require(key not in before.entries, 'REVISION_CONFLICT')
        with self._lock:
            membership = self.membership(actor.actor_id, actor.tenant_id, case)
            current_actor(actor, case, membership)
            # Any policy change invalidates preparation, even if scope remains partly usable.
            if membership != before.membership:
                raise RetryPreparation()
            stored = self._cases.get((actor.tenant_id, case))
            if (stored['generation'] if stored else 0) != before.generation:
                raise RetryPreparation()
            if changed:
                stored = self._cases.setdefault((actor.tenant_id, case),
                                                {'codec': 'h1.state.v1', 'generation': 0, 'entries': {}})
                stored['entries'].update(changed)
                stored['generation'] += 1

    def discard_case(self, tenant, case):
        """Failure-path rollback: drop every entry under one case id; no fixture record is edited.

        Only `_discard` calls this, for a session whose provisioning never completed and whose
        token was never issued, so no client can hold a snapshot of the case it drops. The
        session-local reset uses `reset_case` instead, which must keep the generation moving.
        """
        with self._lock:
            self._cases.pop((tenant, case), None)

    @contextmanager
    def reset_case(self, tenant, case):
        """The reset seam: discard and re-seed one case as a single store step.

        The generation is carried across the reset and advanced rather than reused, so a
        snapshot prepared before the reset can never match again: the pre-reset prepared write
        fails with `RetryPreparation` instead of committing pre-reset state over the reset. The
        store lock is held for the whole discard-and-reseed, so a concurrent write waits and
        then sees the reset generation, never a half-reset case. If re-seeding fails, the case
        is put back as it was on a further generation: a failed reset leaves no half-seeded
        case, and the pre-reset snapshots stay stale either way.
        """
        with self._lock:
            stored = self._cases.get((tenant, case))
            previous = dict(stored['entries']) if stored else {}
            generation = (stored['generation'] if stored else 0) + 1
            self._cases[(tenant, case)] = {'codec': 'h1.state.v1', 'generation': generation,
                                           'entries': {}}
            try:
                yield
            except BaseException:
                current = self._cases.get((tenant, case)) or {'generation': generation}
                self._cases[(tenant, case)] = {'codec': 'h1.state.v1',
                                               'generation': current['generation'] + 1,
                                               'entries': previous}
                raise

    def close(self):
        return None


def _constant_equal(given, expected):
    if type(given) is not str:
        return False
    return hmac.compare_digest(given.encode('utf-8'), expected.encode('utf-8'))


class SandboxIdentity:
    """Demo-mode identity: opaque in-process tokens for sandbox sessions, no network at all."""

    def __init__(self, fixture, maximum=MAX_SANDBOX_SESSIONS):
        self.fixture = fixture
        self.maximum = maximum
        self._lock = RLock()
        self._sessions = {}
        self._tokens = {}

    def _mint(self):
        # 256 bits: the token is the only thing that names a session to the server.
        return secrets.token_urlsafe(32)

    def open_session(self, session):
        """Register the session and mint its token; a full sandbox refuses, it never evicts.

        The cap covers live sessions and outstanding tokens alike, so an unauthenticated caller
        cannot grow the process without bound: the refusal is the intent's 503
        `SESSION_UNAVAILABLE`, and every session already open keeps its case and its token.
        """
        with self._lock:
            if session.uid not in self._sessions and len(self._sessions) >= self.maximum:
                raise SessionUnavailable()
            if len(self._tokens) >= self.maximum:
                raise SessionUnavailable()
            token = self._mint()
            self._sessions[session.uid] = session
            self._tokens[token] = session.uid
        return token

    def discard_session(self, uid):
        """Drop a session whose case could not be provisioned: its token names nothing now."""
        with self._lock:
            self._sessions.pop(uid, None)
            self._tokens = {token: holder for token, holder in self._tokens.items() if holder != uid}

    def session(self, uid):
        with self._lock:
            session = self._sessions.get(uid)
        if session is None:
            raise AuthenticationFailed()
        return session

    def rotate(self, uid):
        """Invalidate every token the session held and mint its replacement."""
        with self._lock:
            self.session(uid)
            self._tokens = {token: holder for token, holder in self._tokens.items() if holder != uid}
            token = self._mint()
            self._tokens[token] = uid
        return token

    def sign_in(self, email, password):
        """The documented fictional account only: constant-time compare, no emulator, no call."""
        if type(email) is not str or type(password) is not str:
            raise AuthenticationFailed()
        if not 0 < len(email) <= 254 or not 0 < len(password) <= 256:
            raise AuthenticationFailed()
        if not _constant_equal(email, EMAIL) or not _constant_equal(password, PASSWORD):
            raise AuthenticationFailed()
        return {'id_token': self.open_session(self.fixture)}

    def verify(self, authorization):
        if not authorization or not authorization.startswith('Bearer '):
            raise AuthenticationFailed()
        token = authorization[7:]
        if not token or len(token) > MAX_TOKEN:
            raise AuthenticationFailed()
        with self._lock:
            uid = self._tokens.get(token)
        if uid is None:
            raise AuthenticationFailed()
        return uid

    def close(self):
        return None


class HostedFirebaseIdentity(FirebaseIdentity):
    """Firebase Auth under application default identity: emulator initialization replaced.

    `verify` is inherited verbatim, so a hosted token is checked by the same code path as any
    identity; the emulator host constant is never read here and no key file is used.
    """

    def __init__(self, project, web_api_key):
        import firebase_admin
        self.project = project
        self.web_api_key = web_api_key
        self.app = firebase_admin.initialize_app(options={'projectId': project})

    def sign_in(self, email, password):
        """Private analyst accounts over TLS; the password is never logged or retained."""
        import httpx
        if not 0 < len(email) <= 254 or not 0 < len(password) <= 256:
            raise AuthenticationFailed()
        try:
            with httpx.Client(timeout=10, trust_env=False) as client:
                response = client.post(IDENTITY_TOOLKIT + 'signInWithPassword?key=' + self.web_api_key,
                                       json={'email': email, 'password': password, 'returnSecureToken': True})
            if response.status_code != 200:
                raise AuthenticationFailed()
            return {'id_token': response.json()['idToken']}
        except httpx.HTTPError:
            raise StorageUnavailable() from None

    def anonymous_session(self):
        """Firebase anonymous sign-in for the judge path; the uid is the one Firebase issued."""
        import httpx
        try:
            with httpx.Client(timeout=10, trust_env=False) as client:
                response = client.post(IDENTITY_TOOLKIT + 'signUp?key=' + self.web_api_key,
                                       json={'returnSecureToken': True})
            if response.status_code != 200:
                raise SessionUnavailable()
            data = response.json()
        except httpx.HTTPError:
            raise SessionUnavailable() from None
        token, uid = data.get('idToken'), data.get('localId')
        if type(token) is not str or type(uid) is not str or not uid.strip():
            raise SessionUnavailable()
        # The claim the verification path reads, not the response body, decides the provider.
        return token, self._anonymous_uid(token, uid)

    def _anonymous_uid(self, token, uid):
        from firebase_admin import auth
        from firebase_admin.exceptions import FirebaseError
        try:
            claims = auth.verify_id_token(token, app=self.app, check_revoked=True)
        except FirebaseError as exc:
            raise SessionUnavailable() from exc
        except ValueError as exc:
            raise SessionUnavailable() from exc
        if claims.get('uid') != uid or (claims.get('firebase') or {}).get('sign_in_provider') != 'anonymous':
            raise SessionUnavailable()
        return uid


def hosted_store(project, namespace, client):
    """A FirestoreStore with hosted initialization; transaction logic is inherited verbatim.

    Defined inside this factory because the emulator adapter imports the Google SDKs at import
    time, while demo mode must stay SDK-free. `load`, `commit`, `membership`, `case_ref`,
    `member_ref` and `close` are the base class's own methods: only the emulator-only
    `local_configuration` call and the `synthetic-*` namespace check are replaced, plus
    `discard_case`, which only the hosted provisioning-failure path needs.
    """
    from google.api_core.exceptions import GoogleAPICallError, RetryError
    from src.adapters.firestore import FirestoreStore

    class HostedFirestoreStore(FirestoreStore):
        def __init__(self, project, namespace, client):
            self.client = client
            self.root = client.collection('h1_namespaces').document(namespace)

        def discard_case(self, tenant, case):
            """Delete one case's own documents: the rollback of a failed provisioning.

            `create_judge_session` calls this when provisioning failed, so a refused session
            leaves no half-written case behind. The case root document and its `entries`
            subcollection are deleted in batches below Firestore's 500-write limit. Deleting
            the root drops the case's generation too, which is safe here because this is the
            only hosted caller: the uid is one Firebase minted for this call and no token was
            ever issued, so no client holds a snapshot of the case. Hosted mode has no HTTP
            reset — demo mode's session-local reset runs through `MemoryStore.reset_case`,
            which keeps the generation moving instead. The membership document is deleted by
            `_discard` beside this call; the anonymous Auth user is not deleted (no request may
            safely delete an Auth user) and belongs to the HOST-2 operator reset.
            """
            ref = self.case_ref(tenant, case)
            try:
                pending = []
                for document in ref.collection('entries').stream(timeout=10):
                    pending.append(document.reference)
                    if len(pending) >= DELETE_BATCH:
                        self._delete_documents(pending)
                        pending = []
                if pending:
                    self._delete_documents(pending)
                ref.delete(timeout=10)
            except (GoogleAPICallError, RetryError, ValueError) as exc:
                raise StorageUnavailable() from exc

        def _delete_documents(self, references):
            batch = self.client.batch()
            for reference in references:
                batch.delete(reference)
            batch.commit()

    return HostedFirestoreStore(project, namespace, client)


class NamespaceStore:
    """One client, two namespaces: judge sessions in the demo namespace, private cases elsewhere.

    The tenant segment selects the namespace; the judge tenant is a fixed constant, never a
    client field, and a membership exists only where it was provisioned.
    """

    def __init__(self, private, judge):
        self.private, self.judge = private, judge

    def _route(self, tenant):
        return self.judge if tenant == JUDGE_TENANT else self.private

    def member_ref(self, uid, tenant, case):
        return self._route(tenant).member_ref(uid, tenant, case)

    def membership(self, uid, tenant, case):
        return self._route(tenant).membership(uid, tenant, case)

    def load(self, actor, case):
        return self._route(actor.tenant_id).load(actor, case)

    def commit(self, actor, case, before, after):
        return self._route(actor.tenant_id).commit(actor, case, before, after)

    def discard_case(self, tenant, case):
        return self._route(tenant).discard_case(tenant, case)

    def close(self):
        return self.private.close()


def fixture_digest():
    """The constant every mode, session and reset reports: the labelled corpus, hashed canonically.

    The corpus is rendered for the placeholder identity (`src/demo`'s own constants), so a
    session's case is that corpus with the identity substituted and the digest never varies.
    """
    store = MemoryStore()
    store.member_ref(UID, TENANT, CASE).set(membership_document(UID, TENANT, CASE))
    repository = PersistentRepository(store)
    seed(repository)
    actor = ActorContext(UID, TENANT, frozenset({CASE}), frozenset({SOURCE_POLICY}), True)
    entries = store.load(actor, CASE).entries
    return hashlib.sha256(canonical_dumps(sorted(entries.items())).encode('utf-8')).hexdigest()


def _actor(session):
    return ActorContext(session.uid, session.tenant, frozenset({session.case}),
                        frozenset({SOURCE_POLICY}), True)


def _event_actor(session):
    """The actor for the session's own copy of the event case: its membership's policy only."""
    return ActorContext(session.uid, session.tenant, frozenset({session.event_case}),
                        frozenset({pedc.PERMISSION_REF}), True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _provision(store, repository, session, at=None):
    """Session creation writes the memberships, then seeds the session's two cases.

    The first case is the labelled synthetic corpus. The second, for a judge session, is the
    copy of the real PEDC event case `src.demo.pedc` builds — the same records the EVAL-5
    fixture builds, all real, with this session's own reviewed mapping and seed acceptance,
    recorded at the instant the session was provisioned. Each case is written by one
    prepared batch (`repository.provision`): the case is loaded once and committed once, so
    a reader sees it before the batch or complete after it, never a part of it. The event
    case's membership is written inside the same guard as its seed: anything that fails from
    that membership write on rolls the event case and its membership back here, so `_discard`
    only ever touches the writes it owns.
    """
    at = at or _now()
    store.member_ref(session.uid, session.tenant, session.case).set(
        membership_document(session.uid, session.tenant, session.case))
    seed(repository, _actor(session))
    if not session.event_case:
        return
    event_member = store.member_ref(session.uid, session.tenant, session.event_case)
    try:
        event_member.set(membership_document(session.uid, session.tenant, session.event_case,
                                             (pedc.PERMISSION_REF,)))
        pedc.seed(repository, _event_actor(session), session.event_case, at)
    except (ReviewError, StorageUnavailable, ValueError):
        try:
            store.discard_case(session.tenant, session.event_case)
        except Exception:
            pass
        try:
            event_member.delete()
        except Exception:
            pass
        raise


def _discard(store, identity, session, mode):
    """Best-effort rollback of a session the store could not provision.

    A cleanup failure is swallowed on purpose: the caller's answer is the intent's 503
    `SESSION_UNAVAILABLE`, never a 500 raised by the cleanup itself. The case and the
    membership written just before the failed seed are both dropped, so a refused session
    leaves nothing behind; a hosted anonymous Auth user is not deleted here (no request may
    safely delete an Auth user) and stays for the HOST-2 operator reset. Both rollbacks are
    independent, so one failing store call does not skip the other.
    """
    try:
        store.discard_case(session.tenant, session.case)
    except Exception:
        pass
    try:
        store.member_ref(session.uid, session.tenant, session.case).delete()
    except Exception:
        pass
    if mode == DEMO_MODE:
        try:
            identity.discard_session(session.uid)
        except Exception:
            pass


def create_judge_session(mode, store, identity, repository, clock=None):
    """`POST /demo/session`: an empty body, no credentials, one isolated case per session.

    The sandbox identity admits the session before the store writes anything, so a full
    instance refuses with 503 instead of allocating a case it cannot keep. The session's
    second case is its own copy of the real PEDC event case (GRID-3); the instant it was
    provisioned is the session's `event_seeded_at`, and a test can pin it with `clock`.
    """
    at = (clock or _now)()
    if mode == DEMO_MODE:
        uid = 'demo-' + secrets.token_hex(16)
        session = Session(uid, JUDGE_TENANT, session_case(uid), event_case(uid), at)
        token = identity.open_session(session)
    else:
        token, uid = identity.anonymous_session()
        session = Session(uid, JUDGE_TENANT, session_case(uid), event_case(uid), at)
    try:
        _provision(store, repository, session, at)
    except (ReviewError, StorageUnavailable, ValueError):
        _discard(store, identity, session, mode)
        raise SessionUnavailable() from None
    return session, token


def reset_session(store, identity, repository, uid):
    """`POST /demo/reset`: the caller's own session only; no request field selects a session.

    Discard and re-seed run inside one store step (`reset_case`): the case's generation keeps
    moving forward, so a write prepared before the reset fails instead of landing pre-reset
    state on the reset, and no concurrent write interleaves between the discard and the seed.
    """
    session = identity.session(uid)
    with store.reset_case(session.tenant, session.case):
        try:
            # The membership document is not rewritten: the stored authority must still hold.
            seed(repository, _actor(session))
        except (ReviewError, StorageUnavailable, ValueError):
            raise SessionUnavailable() from None
    return session, identity.rotate(uid)


@dataclass(frozen=True)
class AlertsWiring:
    """The alerts service and who may call it, built per mode (src/alerts)."""

    service: object
    users: object
    scheduler: object
    client_config: dict | None = None


def demo_alerts():
    """Demo mode: in-process store, no BigQuery, no email, no Google sign-in (read-only view)."""
    from src.alerts.auth import GoogleUsers, SchedulerAuth
    from src.alerts.service import AlertService
    from src.alerts.store import MemoryAlertStore
    return AlertsWiring(AlertService(MemoryAlertStore(), replay=_alerts_replay()), GoogleUsers(), SchedulerAuth())


def _alerts_replay():
    """The baked replay's alerts (ericka-desk E24): read from the same grid data the pages serve."""
    from src.alerts.replay import Replay

    def directory():
        # Asked at the first read. src.api needs FastAPI; without it (a runtime or test built without
        # it) the same order is tried here: GRID_DATA_DIR, build/grid-data, src/grid/grid-data.
        try:
            from src.api import grid_data_directory
        except ImportError:
            given = (os.environ.get('GRID_DATA_DIR') or '').strip()
            if given:
                return Path(given)
            root = Path(__file__).resolve().parents[2]
            return next((c for c in (root / 'build' / 'grid-data', root / 'src' / 'grid' / 'grid-data') if c.is_dir()),
                        root / 'build' / 'grid-data')
        return grid_data_directory()
    return Replay(directory)


def hosted_alerts(settings, client, identity, environ=None):
    """Hosted mode: Firestore under the private namespace, BigQuery and Gmail SMTP when configured.

    Every alerts setting is optional: without NOWCAST_SMTP_USER and NOWCAST_SMTP_PASSWORD email is
    off, and without the scheduler account and audience the scheduled route refuses every call.
    The portfolio import (docs/work/portfolio-import-2026-10-17) is read only when
    NOWCAST_PORTFOLIO_IMPORT is exactly `on`; absent or anything else, it stays off.
    """
    import time
    from src.alerts.auth import GoogleUsers, SchedulerAuth
    from src.alerts.bigquery import BigQueryRest
    from src.alerts.draft import GcsDraft
    from src.alerts.mail import mailer_from
    from src.alerts.ontology_live import FirestoreCardCache, LiveCards
    from src.alerts.service import AlertService
    from src.alerts.store import FirestoreAlertStore
    env = _environ(environ)
    bigquery = BigQueryRest(settings.project, (env.get('NOWCAST_BQ_LOCATION') or 'asia-southeast1').strip())
    # the full driver card on first open (signed in), saved in Firestore; NOWCAST_ONTOLOGY_MAX_BYTES caps
    # the bytes billed (default 5,000,000,000), NOWCAST_ONTOLOGY_TIMEOUT_S the wait (default 180)
    cards = LiveCards.from_env(env, FirestoreCardCache(client, settings.namespace), bigquery)
    service = AlertService(FirestoreAlertStore(client, settings.namespace), bigquery,
                           mailer_from(env),
                           public_url=(env.get('NOWCAST_PUBLIC_URL') or 'https://grid-nowcast.web.app').strip(),
                           sleep=time.sleep,
                           draft=GcsDraft() if (env.get('NOWCAST_PORTFOLIO_IMPORT') or '').strip() == 'on' else None,
                           replay=_alerts_replay(), cards=cards)
    return AlertsWiring(service, GoogleUsers.hosted(identity.app, env.get('NOWCAST_ALERT_EDITORS', '')),
                        SchedulerAuth.hosted(env.get('NOWCAST_ALERT_SCHEDULER_SA', ''),
                                             env.get('NOWCAST_ALERT_SCHEDULER_AUDIENCE', '')),
                        {'apiKey': settings.web_api_key, 'authDomain': settings.project + '.firebaseapp.com',
                         'projectId': settings.project})


@dataclass(frozen=True)
class JournalWiring:
    """The journal service and who may call it, built per mode (src/journal)."""

    service: object
    users: object


def demo_journal():
    """Demo mode: in-process store; no Google sign-in, so every journal call answers 401."""
    from src.alerts.auth import GoogleUsers
    from src.journal.service import JournalService
    from src.journal.store import MemoryJournalStore
    return JournalWiring(JournalService(MemoryJournalStore()), GoogleUsers())


def hosted_journal(settings, client, identity):
    """Hosted mode: Firestore under the private namespace (`journal_entries`); any signed-in user
    may write (the alerts editors list narrows alerts settings, not the journal)."""
    from src.alerts.auth import GoogleUsers
    from src.journal.service import JournalService
    from src.journal.store import FirestoreJournalStore
    return JournalWiring(JournalService(FirestoreJournalStore(client, settings.namespace)),
                         GoogleUsers.hosted(identity.app))


@dataclass
class AgentWiring:
    """The desk agent's parts per mode (src/agent, DOCK-5); the service is built at assembly.

    `store` holds the agent's records (`agent_*` collections under the private namespace in hosted
    mode, in process in demo mode); `sessions` reads the bearer token or the same-origin session
    cookie (`src/agent/session.py`); `archive` and `register_payload` are the outlook archive and the
    assumption register the two outlook writes use, when the environment names them
    (NOWCAST_AGENT_OUTLOOK_ARCHIVE, NOWCAST_AGENT_REGISTER); absent, those writes refuse with
    `no_write_path` before any confirmation is parked. `demonstration` labels every stale mark the
    agent writes as a demonstration (demo mode).
    """

    store: object
    sessions: object
    archive: object = None
    register_payload: dict | None = None
    demonstration: bool = False


def _agent_outlook_inputs(env):
    """`(archive, register_payload)` from the two optional settings; anything unreadable is None."""
    archive, payload = None, None
    root = (env.get('NOWCAST_AGENT_OUTLOOK_ARCHIVE') or '').strip()
    if root and os.path.isdir(root):
        from src.outlook.records import OutlookArchive
        archive = OutlookArchive(root)
    path = (env.get('NOWCAST_AGENT_REGISTER') or '').strip()
    if path and os.path.isfile(path):
        import json
        try:
            with open(path, encoding='utf-8') as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            payload = None
    return archive, payload if isinstance(payload, dict) else None


def demo_agent(alerts, environ=None):
    """Demo mode: the in-process agent store; no Google sign-in, so no session cookie."""
    from src.agent.session import AgentSessions
    from src.agent.store import MemoryAgentStore
    archive, payload = _agent_outlook_inputs(_environ(environ))
    return AgentWiring(MemoryAgentStore(), AgentSessions(alerts.users), archive, payload, demonstration=True)


def hosted_agent(settings, client, identity, alerts, environ=None):
    """Hosted mode: `FirestoreAgentStore(client, namespace)` and the Firebase session cookie."""
    from src.agent.session import DEFAULT_ORIGINS, AgentSessions
    from src.agent.store import FirestoreAgentStore
    env = _environ(environ)
    public = (env.get('NOWCAST_PUBLIC_URL') or '').strip().rstrip('/')
    origins = tuple(dict.fromkeys(((public,) if public else ()) + DEFAULT_ORIGINS))
    archive, payload = _agent_outlook_inputs(env)
    return AgentWiring(FirestoreAgentStore(client, settings.namespace),
                       firebase_sessions(AgentSessions, alerts.users, identity.app, origins), archive, payload)


def firebase_sessions(sessions_class, users, firebase_app, origins):
    """The agent's session over Firebase session cookies: `create_session_cookie` from a verified
    ID token, `verify_session_cookie(..., check_revoked=True)` on every read. firebase_admin is
    imported only when a cookie is minted or read (hosted mode)."""
    def read_cookie(cookie):
        from firebase_admin import auth
        return auth.verify_session_cookie(cookie, check_revoked=True, app=firebase_app)

    def mint(id_token, max_age):
        from datetime import timedelta

        from firebase_admin import auth
        return auth.create_session_cookie(id_token, expires_in=timedelta(seconds=max_age), app=firebase_app)
    return sessions_class(users, read_cookie, mint, origins)


def demo_runtime(environ=None):
    """Demo mode with an otherwise empty environment: in-process identity, store and fixtures."""
    settings = demo_settings(environ)
    fixture = Session(UID, TENANT, CASE)
    store = MemoryStore()
    repository = PersistentRepository(store)
    _provision(store, repository, fixture)
    alerts = demo_alerts()
    return Runtime(settings, store, SandboxIdentity(fixture), repository, fixture_digest(), alerts,
                   journal=demo_journal(), agent=demo_agent(alerts, environ))


def hosted_runtime(environ=None):
    """Hosted mode: ADC clients and Firebase Auth, validated before anything is constructed."""
    settings = hosted_settings(environ)
    from google.cloud import firestore
    client = firestore.Client(project=settings.project)
    store = NamespaceStore(hosted_store(settings.project, settings.namespace, client),
                           hosted_store(settings.project, settings.demo_namespace, client))
    identity = HostedFirebaseIdentity(settings.project, settings.web_api_key)
    alerts = hosted_alerts(settings, client, identity, environ)
    return Runtime(settings, store, identity, PersistentRepository(store), fixture_digest(), alerts,
                   journal=hosted_journal(settings, client, identity),
                   agent=hosted_agent(settings, client, identity, alerts, environ))


#: DATA-2: the bake manifest scripts/grid/build_all.py writes at the root of the baked data.
BAKE_MANIFEST = 'manifest.json'
#: The replay span `/health` carries from the manifest: its first and last interval and its
#: number of replay days.
HEALTH_REPLAY_KEYS = ('first', 'last', 'days')


def read_bake_manifest(data_dir):
    """The baked `manifest.json` as a dict, or None when it is absent or unreadable.

    Read once, when the application is assembled; an image baked before DATA-2, or a local run
    with no bake, has none, and `/health` then reports null replay fields — never an error.
    """
    try:
        manifest = json.loads((Path(data_dir) / BAKE_MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None
    return manifest if isinstance(manifest, dict) else None


def health_body(mode, stamp=None, manifest=None):
    """The hosted `/health` answer: the HOST-1 keys, unchanged, plus which bake this image serves.

    DATA-2: `stamp` is the build stamp this process serves every page and data file under (the
    one the staged first screen on Hosting must carry too — scripts/deploy/deploy.sh compares
    them), and `replay` is the span the baked manifest measured from `replay.json`. A missing
    manifest leaves the three replay fields null.
    """
    replay = manifest.get('replay') if isinstance(manifest, dict) else None
    replay = replay if isinstance(replay, dict) else {}
    return {'status': 'ok', 'mode': mode, 'storage_checked': False, 'stamp': stamp,
            'replay': {key: replay.get(key) for key in HEALTH_REPLAY_KEYS}}


def _replace_health(application, mode, stamp=None, manifest=None):
    """`create_app` is reused unchanged and reports the local mode; this assembly owns the
    application it builds, so the one route it replaces is `/health`, additively. DATA-2: the
    answer also names the bake (`health_body`), computed once here, never per request."""
    application.router.routes = [route for route in application.router.routes
                                 if getattr(route, 'path', None) != '/health']
    body = health_body(mode, stamp, manifest)

    @application.get('/health')
    def health():
        return dict(body, replay=dict(body['replay']))


def _session_response(session, token, mode, digest, **extra):
    return dict(extra, id_token=token, mode=mode, tenant=session.tenant, case=session.case,
                fixture_digest=digest)


def _assemble(runtime):
    # Absolute imports: FastAPI arrives with the application package, and this module is also
    # loadable by file location so the configuration surface stays testable without it.
    from src.api import (GRID_DIR, REVALIDATE_CACHE, SIGN_IN_POLICY, build_stamp, create_app,
                         declaring, declaring_policy, error, grid_data_directory, page_response)
    from fastapi import Request
    from fastapi.responses import Response
    from urllib.parse import quote

    application = create_app(runtime.repository, runtime.identity)
    application.add_exception_handler(
        SessionUnavailable, lambda request, exc: error('SESSION_UNAVAILABLE', 503))
    # DATA-2: `/health` names the bake this image serves — its build stamp, derived from the
    # same data directory `create_app` derives its own from, and the manifest's replay span.
    _replace_health(application, runtime.settings.mode, build_stamp(grid_data_directory()),
                    read_bake_manifest(grid_data_directory()))

    # ATG-7: the asset pages, served exactly like `/event/<id>` — the page file with this
    # build's stamp written into its asset and data URLs, declaring `REVALIDATE_CACHE`, so the
    # next visit picks a new build up while the stamped files it reads stay immutable. The
    # site code is the page's own URL segment (the profile page reads it the way the event page
    # reads its id); the stamp is derived from the same data directory `create_app` derives its
    # own from (`GRID_DATA_DIR`, else the bake tree), so the two pages never name two builds.
    stamp = build_stamp(grid_data_directory())

    @application.get('/data')
    def data_page():
        # ATG-8: the data catalog (ATG-4), served like the pages above. Its one baked file,
        # `catalog.json`, travels under the same stamp every other baked file does.
        return declaring(page_response(GRID_DIR / 'catalog.html', stamp), REVALIDATE_CACHE)

    @application.get('/alerts')
    def alerts_page():
        # The alerts and portfolio page: served like the pages above, with the one other content
        # security policy (src/api SIGN_IN_POLICY) so "Sign in with Google" can run on it.
        return declaring_policy(declaring(page_response(GRID_DIR / 'alerts.html', stamp), REVALIDATE_CACHE),
                                SIGN_IN_POLICY)

    @application.get('/settings')
    def settings_page():
        # ericka-desk: the alert settings (the one-off check, the email rules and levels, the alert
        # history), on their own page; served exactly like `/alerts`, with the sign-in policy, since
        # the same script (alerts.js) signs in to edit them.
        return declaring_policy(declaring(page_response(GRID_DIR / 'settings.html', stamp), REVALIDATE_CACHE),
                                SIGN_IN_POLICY)

    @application.get('/journal')
    def journal_page():
        # ericka-desk slice 8: the Trader's Journal, served like the pages above (the sign-in
        # policy comes with every page, D1); its entries come from `/api/journal`.
        return declaring(page_response(GRID_DIR / 'journal.html', stamp), REVALIDATE_CACHE)

    @application.get('/notices')
    def notices_page():
        # ericka-desk: every operator notice up to the shared as-of clock (src/grid/notices.js),
        # read from the replay's advisories.json; served like the pages above.
        return declaring(page_response(GRID_DIR / 'notices.html', stamp), REVALIDATE_CACHE)

    # ericka-desk: the plant list is `/plants` and each profile `/plant/<code>` (the files keep
    # their asset names). The old `/assets` and `/asset/<code>` addresses answer a permanent
    # redirect to the new ones with the query string kept (the browser keeps any #fragment), so
    # older links still land; a redirect is not 200, so it is never stored.
    @application.get('/plants')
    def plants_page():
        return declaring(page_response(GRID_DIR / 'assets.html', stamp), REVALIDATE_CACHE)

    @application.get('/plant/{code}')
    def plant_page(code: str):
        return declaring(page_response(GRID_DIR / 'asset.html', stamp), REVALIDATE_CACHE)

    def moved(request, path):
        query = (request.scope.get('query_string') or b'').decode('latin-1')
        return Response(status_code=308, headers={'Location': path + ('?' + query if query else '')})

    @application.get('/assets')
    def assets_moved(request: Request):
        return moved(request, '/plants')

    @application.get('/asset/{code}')
    def asset_moved(code: str, request: Request):
        return moved(request, '/plant/' + quote(code, safe=''))

    @application.post('/demo/session')
    def demo_session():
        session, token = create_judge_session(runtime.settings.mode, runtime.store,
                                              runtime.identity, runtime.repository)
        # The judge's event page addresses its own copy of the PEDC case by name and reads
        # its belief state at the instant it was seeded (`src/grid/event-api.js`). Both are
        # additive keys on the session answer; the reset answer stays what it was.
        return _session_response(session, token, runtime.settings.mode, runtime.digest,
                                 event_case=session.event_case,
                                 event_seeded_at=session.event_seeded_at)

    if runtime.settings.mode == DEMO_MODE:
        @application.post('/demo/reset')
        def demo_reset(request: Request):
            # Reset is never reachable without the caller's own verified session token.
            uid = runtime.identity.verify(request.headers.get('authorization'))
            session, token = reset_session(runtime.store, runtime.identity, runtime.repository, uid)
            return _session_response(session, token, DEMO_MODE, runtime.digest, reset=True)

    if runtime.alerts is not None:
        _register_alerts(application, runtime.alerts)
    if runtime.journal is not None:
        _register_journal(application, runtime.journal, grid_data_directory())
    if runtime.alerts is not None and runtime.agent is not None:
        _register_agent(application, runtime, grid_data_directory())
    # UX-B: the command bar's desk API (src/desk), public reads over the same baked replay the
    # `/grid-data` route serves. Nothing is read at startup: the directory is parsed lazily on the
    # first request and kept per build. Every answer declares no class, so it is `no-store`.
    # The live Gemini path is on only with DESK_GEMINI=1 (src/desk/gemini.py), for signed-in users
    # (the agent's session) under the agent's day meter; otherwise recorded or composed answers.
    from src.desk import register as register_desk
    from src.desk.routes import wiring as desk_wiring
    agent = runtime.agent
    register_desk(application, grid_data_directory(),
                  desk_wiring(agent.sessions if agent is not None else None,
                              agent.store if agent is not None else None))

    @asynccontextmanager
    async def lifespan(app):
        yield
        runtime.identity.close()
        runtime.store.close()

    application.router.lifespan_context = lifespan
    return application


def _register_alerts(application, alerts):
    """The alerts JSON routes (src/alerts/routes.py); the `/alerts` page is served in `_assemble`."""
    from src.alerts import routes
    routes.register(application, alerts.service, alerts.users, alerts.scheduler, lambda: alerts.client_config)


def event_sites(data_dir):
    """Event id -> plant code from the baked `events.json`; empty when it is missing or unreadable."""
    import json
    from pathlib import Path
    try:
        events = json.loads((Path(data_dir) / 'events.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return {}
    if type(events) is not list:
        return {}
    return {e['id']: e['site'] for e in events
            if type(e) is dict and type(e.get('id')) is str and type(e.get('site')) is str}


def _register_journal(application, journal, data_dir):
    """The journal JSON routes (src/journal/routes.py); the `/journal` page is served in `_assemble`."""
    from src.journal import routes
    if not journal.service.event_sites:
        journal.service.event_sites = event_sites(data_dir)
    routes.register(application, journal.service, journal.users)


def book_adapter(data_dir=None, archive_root=None):
    """`BookAdapter(MaterialityPolicy(), ...)` over the baked book (`<data>/book/index.json`), else
    the committed fixture book.

    The vintages are read from `archive_root` (default: the committed fixture vintages). Where that
    archive is absent (the image carries `src/` and the bake only), an impact query is refused by
    the adapter with its own code and the records provider lists no book vintage. None when no book
    can be read at all.
    """
    import json
    from src.book.adapter import FIXTURE_ARCHIVE, BookAdapter
    from src.price.impact import MaterialityPolicy
    book = None
    if data_dir is not None:
        try:
            with open(os.path.join(str(data_dir), 'book', 'index.json'), encoding='utf-8') as handle:
                index = json.load(handle)
            book = index.get('book') if isinstance(index, dict) else None
        except (OSError, ValueError):
            book = None
    try:
        return BookAdapter(MaterialityPolicy(), book,
                           archive_root if archive_root is not None else FIXTURE_ARCHIVE)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def agent_service(runtime, data_dir):
    """The agent service over this runtime (DOCK-3's `AgentService`, DOCK-5's ports).

    * the records provider per page: the book's records (`src/agent/wiring.py` `AgentRecords`) over
      a base provider; no base record set is baked yet, so every page answers None and the service
      replays the page's recorded answers (DOCK-4 records the live plan sets and their records);
    * the recorded answers and `cutoff_for` from the baked plan sets (`views/<key>.json`);
    * `site_routes` is `src/judgment/actions.py` SITE_ROUTES (pinned equal to the staging test's);
    * `book` is `BookAdapter(MaterialityPolicy(), ...)` over the baked book (`book/index.json`);
    * `ids` is the book's manifest identifiers;
    * the archive and the register when the environment names them, else none;
    * `decision_writer` over the review repository's `commit_review` needs a review actor for the
      agent's owner; none is mapped yet (the owner is a digest of the Google account, not an H1
      membership), so `save_decision` refuses `no_write_path` before any confirmation;
    * no live planner: the recorded planner only, so the day meter is never charged here.
    """
    from src.agent.service import AgentService
    from src.agent.wiring import BOOK_REGION, BOOK_WINDOW, AgentRecords, PlanSets, review_decision_writer
    from src.judgment.actions import SITE_ROUTES
    agent = runtime.agent
    plans = PlanSets(data_dir)
    book = book_adapter(data_dir)
    records = AgentRecords(base=None, book=book, window=BOOK_WINDOW, region=BOOK_REGION)

    def commit_review(actor, command):
        return runtime.repository.execute(actor, command['case_id'],
                                          lambda repository, fresh: repository.commit_review(fresh, command))
    return AgentService(agent.store, records=records, book=book, archive=agent.archive,
                        register_payload=agent.register_payload,
                        decision_writer=review_decision_writer(commit_review, None, _now),
                        site_routes=SITE_ROUTES, demonstration=agent.demonstration, ids=records.ids,
                        cutoff_for=plans.cutoff_for, recorded_answers=plans.answers)


def _register_agent(application, runtime, data_dir):
    """The agent JSON routes (src/agent/routes.py) and the session routes (src/agent/session.py),
    behind the alerts' sign-in (`GoogleUsers`) or the same-origin session cookie."""
    # `from <module> import <name>` resolves each module through sys.modules, so the routes and the
    # service always come from one import of the package (a package attribute could be stale).
    from src.agent.routes import register as register_routes
    from src.agent.session import register as register_session
    service = agent_service(runtime, data_dir)
    register_routes(application, service, runtime.alerts.users, runtime.agent.sessions)
    register_session(application, runtime.agent.sessions)


def demo_application(environ=None):
    return demo_runtime(environ).application()


def hosted_application(environ=None):
    return hosted_runtime(environ).application()


def app():
    """Uvicorn factory: read the environment, validate it, then build identity, store, repo."""
    mode = select_mode()
    if mode == DEMO_MODE:
        return demo_application()
    if mode == HOSTED_MODE:
        return hosted_application()
    raise HostedConfigurationError('LOCAL_MODE_REFUSED')
