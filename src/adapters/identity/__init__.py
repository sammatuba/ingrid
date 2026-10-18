"""Local Firebase verification; identity never comes from request bodies."""
import os
import re
from uuid import uuid4

from src.review import ActorContext
from src.review.storage import current_actor, StorageUnavailable


class AuthenticationFailed(Exception):
    pass


def local_configuration(project):
    if os.environ.get('NOWCAST_ENV') != 'local' or not re.fullmatch(r'demo-[a-z0-9-]+', project):
        raise ValueError('H1 requires explicit local demo configuration')
    if os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV'):
        raise ValueError('H1 emulator mode refuses hosted configuration')
    for name in ('FIRESTORE_EMULATOR_HOST', 'FIREBASE_AUTH_EMULATOR_HOST'):
        host = os.environ.get(name, '')
        if not re.fullmatch(r'127\.0\.0\.1:[0-9]{1,5}', host) or not 0 < int(host.split(':')[1]) < 65536:
            raise ValueError('H1 requires explicit loopback emulator addresses')


class FirebaseIdentity:
    def __init__(self, project):
        local_configuration(project)
        self.project = project
        import firebase_admin
        self.app = firebase_admin.initialize_app(options={'projectId': project}, name='h1-' + uuid4().hex)

    def sign_in(self, email, password):
        """Local emulator only. Never proxy credentials to a user-selected origin."""
        local_configuration(self.project)
        import httpx
        if not 0 < len(email) <= 254 or not 0 < len(password) <= 256:
            raise AuthenticationFailed()
        try:
            with httpx.Client(timeout=10, trust_env=False) as client:
                response = client.post('http://' + os.environ['FIREBASE_AUTH_EMULATOR_HOST'] +
                    '/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=synthetic-local',
                    json={'email': email, 'password': password, 'returnSecureToken': True})
            if response.status_code != 200:
                raise AuthenticationFailed()
            data = response.json()
            return {'id_token': data['idToken']}
        except httpx.HTTPError:
            raise StorageUnavailable() from None

    def verify(self, authorization):
        from firebase_admin import auth
        from firebase_admin.exceptions import FirebaseError
        if not authorization or not authorization.startswith('Bearer '):
            raise AuthenticationFailed()
        token = authorization[7:]
        if not token or len(token) > 16384:
            raise AuthenticationFailed()
        try:
            claims = auth.verify_id_token(token, app=self.app, check_revoked=True)
            uid = claims.get('uid')
            if type(uid) is not str or not uid.strip():
                raise AuthenticationFailed()
            return uid
        except (auth.InvalidIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError, auth.UserNotFoundError, ValueError) as exc:
            raise AuthenticationFailed() from exc
        except FirebaseError as exc:
            raise StorageUnavailable() from exc

    def close(self):
        import firebase_admin
        firebase_admin.delete_app(self.app)


class MembershipIdentity:
    def __init__(self, store):
        self.store = store

    def actor(self, uid, tenant, case):
        membership = self.store.membership(uid, tenant, case)
        # Only persisted membership supplies capabilities. Validate before constructing scope.
        policies = membership.get('source_policy_refs', []) if type(membership) is dict else []
        if type(policies) is not list or not all(type(p) is str for p in policies):
            policies = []
        candidate = ActorContext(uid, tenant, frozenset({case}), frozenset(policies), True)
        return current_actor(candidate, case, membership)
