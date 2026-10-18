"""HOST-2 operator cleanup: stale judge sessions in the demo namespace only.

Run by the operator under application default identity — never by a judge, never from a browser
and never with a judge token. It lists the membership documents in the demo namespace whose
session is older than ``--older-than`` (default 48 h) and, only with ``--apply``, deletes each
one's case documents through the same hosted-store path the failed-provisioning rollback uses,
deletes its Firebase Auth user when that user is anonymous (no provider entries, no email and no
phone number — the shape the Admin SDK reports for a Firebase anonymous user, whose
``provider_data`` is empty) and deletes its membership document **last**: the membership is the
discovery record this command lists, so a transient Auth failure leaves the session findable and
the next run finishes it instead of stranding an anonymous user. Any other namespace is refused
before a client is built; without ``--apply`` the run is a dry run that deletes nothing. The
fixture digest is printed so the record states what the demo namespace should hold.

Deliberately narrow, per the hosting intent (docs/work/hosting/intent.md) reset policy and
anonymous judge access path: a session's age is the membership document's own creation time, and
an unreadable age stays unknown — those sessions are reported and kept, never deleted on an
assumption. A session whose Auth user cannot be read, or whose user is not anonymous, is kept
whole and reported: the demo namespace must never become a path to a private account. Private
namespaces are never touched by this or any other demo path.

The store, the namespace listing and the Auth client are injected into ``cleanup_sessions``, so
the selection and deletion rules run offline against fakes (tests/test_hosted_config.py) with
no SDK, no credential and no network call; the real clients exist only in ``main``/``connect``.
"""
import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _hosted():
    """`src.api.hosted` by file location: the package's `__init__.py` imports FastAPI, and this
    operator command must run on the bare interpreter too. `hosted.py` itself imports no SDK;
    the Google and Firebase clients arrive only inside `connect`, `cleanup_store` and the
    hosted store factory."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('nowcast_hosted_for_cleanup',
                                                  ROOT / 'src' / 'api' / 'hosted.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOSTED = _hosted()
JUDGE_TENANT = HOSTED.JUDGE_TENANT
# The one namespace the judge path writes to; the deploy and the intent pin it too.
DEMO_NAMESPACE = HOSTED.DEMO_NAMESPACE_DEFAULT
DEFAULT_OLDER_THAN = '48h'
OLDER_THAN = re.compile(r'(\d+)([smhd])')
UNITS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}


class CleanupRefused(Exception):
    """A fixed refusal: the operator command never guesses which namespace to clean."""


def parse_older_than(value):
    """``48h``, ``2d``, ``90m``; anything else is refused rather than guessed."""
    match = OLDER_THAN.fullmatch(value)
    if match is None:
        raise CleanupRefused(f'--older-than takes a whole number and s/m/h/d, not {value!r}')
    return dt.timedelta(seconds=int(match.group(1)) * UNITS[match.group(2)])


def resolve_namespace(given, environ):
    """The demo namespace only, checked before any client is built."""
    namespace = (given or DEMO_NAMESPACE).strip()
    if namespace != DEMO_NAMESPACE:
        raise CleanupRefused(
            f'refusing namespace {namespace!r}: this command cleans only the demo namespace '
            f'{DEMO_NAMESPACE!r}')
    private = (environ.get('NOWCAST_NAMESPACE') or '').strip()
    if private and private == namespace:
        raise CleanupRefused('refusing to run: NOWCAST_NAMESPACE names the demo namespace')
    return namespace


@dataclass(frozen=True)
class JudgeSession:
    uid: str
    tenant: str
    case: str
    # A timezone-aware datetime, or None when the membership's age cannot be read.
    created: object


def read_memberships(documents):
    """Split membership documents into judge sessions and everything else.

    A judge session is a membership under the judge tenant carrying a non-empty uid and case.
    Anything else is malformed for this purpose: it is reported and never touched.
    """
    sessions, malformed = [], []
    for document in documents:
        data = document.to_dict() or {}
        uid, tenant, case = data.get('uid'), data.get('tenant_id'), data.get('case_id')
        if tenant != JUDGE_TENANT or not isinstance(uid, str) or not uid \
                or not isinstance(case, str) or not case:
            malformed.append(document)
            continue
        created = getattr(document, 'create_time', None)
        if isinstance(created, dt.datetime) and created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        sessions.append(JudgeSession(uid, tenant, case,
                                     created if isinstance(created, dt.datetime) else None))
    return sessions, malformed


def stale_sessions(sessions, older_than, now):
    """The stale, the young and the unknown-age judge sessions.

    An unknown age stays unknown: a membership whose creation time cannot be read is reported
    and kept, never deleted on an assumption.
    """
    stale, young, unknown = [], [], []
    for session in sessions:
        if session.created is None:
            unknown.append(session)
        elif now - session.created >= older_than:
            stale.append(session)
        else:
            young.append(session)
    return stale, young, unknown


def identity_state(auth, uid, not_found=None):
    """``anonymous``, ``absent``, ``unexpected`` or ``unknown`` for one session's Auth user.

    Only a user with no provider entries, no email and no phone number is deletable: that is the
    shape the Admin SDK reports for a real Firebase anonymous user (``provider_data`` empty; the
    ``firebase`` provider appears as the account's primary provider, never as a provider entry).
    A user with any provider entry, an email or a phone number is ``unexpected``; a lookup
    failure that is not "user not found" is ``unknown``. The caller keeps the session whole for
    both: the demo namespace is never a path to a private account, and an identity that cannot
    be read is not deleted on an assumption.
    """
    try:
        user = auth.get_user(uid)
    except Exception as exc:  # the state of an unreadable user is unknown, not absent
        if not_found is not None and isinstance(exc, not_found):
            return 'absent'
        return 'unknown'
    providers = [getattr(provider, 'provider_id', None)
                 for provider in (getattr(user, 'provider_data', None) or [])]
    email = getattr(user, 'email', None)
    phone = getattr(user, 'phone_number', None)
    return 'anonymous' if not (providers or email or phone) else 'unexpected'


@dataclass
class Summary:
    namespace: str
    older_than: dt.timedelta
    now: dt.datetime
    apply: bool
    digest: str
    judge_sessions: int
    stale: int
    young: int
    unknown_age: int
    malformed: int
    deleted: list = field(default_factory=list)      # (session, identity state)
    kept: list = field(default_factory=list)         # (session, identity state)
    failures: list = field(default_factory=list)     # (session, message)

    def deleted_cases(self):
        return len(self.deleted) if self.apply else 0

    def deleted_memberships(self):
        return len(self.deleted) if self.apply else 0

    def deleted_users(self):
        return len([1 for _, state in self.deleted if state == 'anonymous']) if self.apply else 0


def cleanup_sessions(store, auth, sessions, older_than, now, apply, *, namespace=DEMO_NAMESPACE,
                     malformed=(), not_found=None):
    """Select and (with ``apply``) delete the stale judge sessions; return the Summary.

    One session's deletion is its case documents, then its Auth user when that user is
    anonymous, then its membership document. The membership goes last on purpose: it is the
    record ``iter_memberships`` discovers, so it survives any earlier failure and the next run
    lists the session again instead of leaving an anonymous Auth user behind with nothing that
    points at it. An Auth user that is already absent is done — there is nothing to delete, so
    the membership is removed without an Auth call. A failure is recorded against that session
    and the run moves to the next one, so one bad document cannot strand the rest of a cleanup.
    """
    stale, young, unknown = stale_sessions(sessions, older_than, now)
    summary = Summary(namespace, older_than, now, bool(apply), HOSTED.fixture_digest(),
                      judge_sessions=len(sessions), stale=len(stale), young=len(young),
                      unknown_age=len(unknown), malformed=len(list(malformed)))
    for session in stale:
        state = identity_state(auth, session.uid, not_found)
        if state in ('unexpected', 'unknown'):
            summary.kept.append((session, state))
            continue
        if apply:
            try:
                store.discard_case(session.tenant, session.case)
                if state == 'anonymous':
                    auth.delete_user(session.uid)
                store.member_ref(session.uid, session.tenant, session.case).delete(timeout=10)
            except Exception as exc:
                summary.failures.append((session, f'{type(exc).__name__}: {exc}'))
                continue
        summary.deleted.append((session, state))
    return summary


def describe(summary):
    """The operator record: what was seen, what was (or would be) deleted, and the digest."""
    mode = 'apply' if summary.apply else 'dry run'
    kept = {}
    for _, state in summary.kept:
        kept[state] = kept.get(state, 0) + 1
    absent = len([1 for _, state in summary.deleted if state == 'absent'])
    verb = 'deleted' if summary.apply else 'would delete'
    counts = (f'{summary.deleted_cases()} cases, {summary.deleted_memberships()} memberships, '
              f'{summary.deleted_users()} anonymous Auth users')
    return [
        f'cleanup namespace {summary.namespace} — {mode}, older than {summary.older_than}, '
        f'now {summary.now.isoformat()}',
        f'  judge memberships:        {summary.judge_sessions}',
        f'  stale:                    {summary.stale}',
        f'  {verb}: {counts}',
        f'  Auth user already absent: {absent}',
        f'  younger:                  {summary.young}',
        f'  unknown age (kept):       {summary.unknown_age}',
        f'  unknown identity (kept):  {kept.get("unknown", 0)}',
        f'  not anonymous (kept):     {kept.get("unexpected", 0)}',
        f'  malformed memberships:    {summary.malformed} (kept)',
        f'  failures:                 {len(summary.failures)}',
        f'  fixture digest:           {summary.digest}',
    ]


def iter_memberships(client, namespace):
    """Every membership document in the demo namespace's root."""
    return list(client.collection('h1_namespaces').document(namespace)
                .collection('members').stream(timeout=10))


def cleanup_store(project, namespace, client):
    """The hosted store: `discard_case` and `member_ref` are the paths the app itself uses."""
    return HOSTED.hosted_store(project, namespace, client)


def connect(project):
    """The real clients under ADC — no key file, no emulator, no other service."""
    try:
        import firebase_admin
        from firebase_admin import auth
        from google.cloud import firestore
    except ImportError as exc:
        raise CleanupRefused(
            f'the operator environment is missing {exc.name}; run this with the pinned '
            f'environment (requirements/h1.lock)') from exc
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(options={'projectId': project})
    return firestore.Client(project=project), auth, auth.UserNotFoundError


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='cleanup.py',
        description='remove stale judge sessions from the demo namespace only (dry run '
                    'unless --apply)')
    parser.add_argument('--project', default=os.environ.get('GCLOUD_PROJECT') or 'grid-nowcast')
    parser.add_argument('--namespace', default=None,
                        help=f'the demo namespace only (default {DEMO_NAMESPACE})')
    parser.add_argument('--older-than', default=DEFAULT_OLDER_THAN,
                        help=f'stale age as a whole number and s/m/h/d (default {DEFAULT_OLDER_THAN})')
    parser.add_argument('--apply', action='store_true',
                        help='delete; without it the run only reports')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        namespace = resolve_namespace(args.namespace, os.environ)
        older_than = parse_older_than(args.older_than)
        client, auth, not_found = connect(args.project)
    except CleanupRefused as exc:
        print(f'refused: {exc}', file=sys.stderr)
        return 2
    now = dt.datetime.now(dt.timezone.utc)
    try:
        sessions, malformed = read_memberships(iter_memberships(client, namespace))
        summary = cleanup_sessions(cleanup_store(args.project, namespace, client), auth, sessions,
                                   older_than, now, args.apply, namespace=namespace,
                                   malformed=malformed, not_found=not_found)
    finally:
        client.close()
    for line in describe(summary):
        print(line)
    return 1 if summary.failures else 0


if __name__ == '__main__':
    sys.exit(main())
