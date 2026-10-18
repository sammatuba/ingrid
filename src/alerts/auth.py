"""Who is calling: a user signed in through Firebase Auth (Google or email and password), or the
Cloud Scheduler job.

Owner decisions 2026-10-17: no roles, every signed-in user may view and edit. Signed in means a
Firebase token whose provider is Google (`google.com`, verified email required) or email and password
(`password`). Password accounts are created by the team with the Admin SDK (for example the judges'
account named in the submission form), so `email_verified` is not required for them. An anonymous
judge session, a custom token or any other provider only sees the read-only view.
NOWCAST_ALERT_EDITORS (emails or @domain, separated by ';' or spaces) can narrow editing later;
unset means every signed-in user.

The scheduler calls with a Google-signed OIDC token for its service account; the audience is the
Cloud Run URL of the scheduled route (NOWCAST_ALERT_SCHEDULER_AUDIENCE) and the account is
NOWCAST_ALERT_SCHEDULER_SA.
"""
import re

GOOGLE = 'google.com'
PASSWORD = 'password'
SIGNED_IN_PROVIDERS = (GOOGLE, PASSWORD)


class NotSignedIn(Exception):
    """No usable sign-in (Google or email and password) on the request (the route answers 401 SIGN_IN_REQUIRED)."""


class NotAllowed(Exception):
    """Signed in, but not an editor under NOWCAST_ALERT_EDITORS (403)."""


def _bearer(authorization):
    if not authorization or not authorization.startswith('Bearer '):
        return None
    token = authorization[7:].strip()
    return token if token and len(token) <= 16384 else None


def parse_editors(value):
    return tuple(p.lower() for p in re.split(r'[;\s,]+', value or '') if p)


class GoogleUsers:
    """`verify(token) -> claims` is firebase_admin's verify_id_token in hosted mode; None in demo mode."""

    def __init__(self, verify=None, editors=()):
        self._verify, self.editors = verify, tuple(editors)

    @classmethod
    def hosted(cls, firebase_app, editors=''):
        def verify(token):
            from firebase_admin import auth
            return auth.verify_id_token(token, app=firebase_app, check_revoked=True)
        return cls(verify, parse_editors(editors))

    def user(self, authorization):
        """The signed-in user {'uid', 'email', 'provider'}, or None when the request carries no sign-in."""
        token = _bearer(authorization)
        if token is None or self._verify is None:
            return None
        try:
            claims = self._verify(token)
        except Exception:
            # An expired, revoked or foreign token is "not signed in", never an error page.
            return None
        firebase = claims.get('firebase') or {}
        email = claims.get('email')
        provider = firebase.get('sign_in_provider')
        if provider not in SIGNED_IN_PROVIDERS or type(email) is not str or not email.strip():
            return None
        if provider == GOOGLE and not claims.get('email_verified'):
            return None
        return {'uid': claims.get('uid') or claims.get('sub'), 'email': email.lower(), 'provider': provider}

    def require(self, authorization):
        user = self.user(authorization)
        if user is None:
            raise NotSignedIn()
        if self.editors and not any(user['email'] == e or (e.startswith('@') and user['email'].endswith(e))
                                    for e in self.editors):
            raise NotAllowed()
        return user


class SchedulerAuth:
    def __init__(self, account='', audience='', verify=None):
        self.account, self.audience, self._verify = account.strip().lower(), audience.strip(), verify

    @classmethod
    def hosted(cls, account, audience):
        def verify(token, audience):
            from google.auth.transport.requests import Request
            from google.oauth2 import id_token
            return id_token.verify_oauth2_token(token, Request(), audience=audience)
        return cls(account or '', audience or '', verify)

    @property
    def configured(self):
        return bool(self.account and self.audience and self._verify)

    def check(self, authorization):
        token = _bearer(authorization)
        if not self.configured or token is None:
            return False
        try:
            claims = self._verify(token, self.audience)
        except Exception:
            return False
        return (str(claims.get('email', '')).lower() == self.account and bool(claims.get('email_verified'))
                and claims.get('aud') == self.audience)
