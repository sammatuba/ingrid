"""The same-origin session the agent routes read (DOCK-5): sign in once on /alerts, signed in everywhere.

The alerts page signs in with Firebase Auth and holds an ID token in the browser. No other page loads
the Firebase SDK, so no other page can send that token. After sign-in, `src/grid/alerts.js` posts the
ID token once to `POST /api/agent/session`; the server checks it exactly as the alerts routes do
(`src/alerts/auth.py` `GoogleUsers`: a Google account with a verified email, or a team email and
password account) and answers with a Firebase session cookie. Every page then reads
`GET /api/agent/whoami`, and the agent routes accept that cookie or the bearer token.

The cookie:

* is named `__session`, the one cookie Firebase Hosting forwards to Cloud Run through its rewrite;
* is `HttpOnly` (no page script reads it), `Secure`, `SameSite=Lax` and `Path=/`;
* holds a Firebase session cookie (`firebase_admin.auth.create_session_cookie`), read back with
  `verify_session_cookie(..., check_revoked=True)` on every request, so a revoked account is signed
  out at its next request and the claims pass the same checks as an ID token;
* lives `MAX_AGE` seconds; `POST /api/agent/session/end` (sign-out on /alerts) clears it.

Cross-site requests (CSRF). `SameSite=Lax` keeps the cookie off every cross-site `POST` and every
cross-site `fetch`. As a second line, a request that changes anything (a `POST`) may use the cookie only
when the browser says it is same-origin: `Sec-Fetch-Site: same-origin`, or, from a browser that sends
no fetch metadata, an `Origin` header that is one of the site's own origins. Otherwise the cookie is
ignored: the ask is answered as an anonymous ask, and a confirm answers 401. The bearer token is
unchanged by this: no browser attaches it to a cross-site request by itself. Setting and clearing the
session require the same same-origin check (no login CSRF). A `GET` may use the cookie: no `GET`
route writes.

No FastAPI import at module level, so the module loads with the bare interpreter (the tests).
"""
import re

from src.alerts.auth import GoogleUsers, NotAllowed, NotSignedIn

COOKIE = '__session'
#: Five days. Firebase allows five minutes to two weeks; revocation is checked on every read.
MAX_AGE = 5 * 24 * 3600
ATTRIBUTES = 'Path=/; HttpOnly; Secure; SameSite=Lax'
#: The site's own origins, as a browser names them in `Origin` (deploy: NOWCAST_PUBLIC_URL).
DEFAULT_ORIGINS = ('https://ingrid-desk.web.app', 'https://ingrid-desk.firebaseapp.com',
                   'https://grid-nowcast.web.app', 'https://grid-nowcast.firebaseapp.com')
MAX_COOKIE = 16384
#: A session cookie is a signed JWT: base64url segments joined by dots.
COOKIE_VALUE = re.compile(r'[A-Za-z0-9_.-]+')


def _bearer(authorization):
    """The token of a `Bearer` header, as `src/alerts/auth.py` reads it; None otherwise."""
    if type(authorization) is not str or not authorization.startswith('Bearer '):
        return None
    token = authorization[7:].strip()
    return token if token and len(token) <= MAX_COOKIE else None


def _header(request, name):
    headers = getattr(request, 'headers', None) or {}
    value = headers.get(name)
    if value is None:
        value = headers.get(name.title())
    return value if type(value) is str else None


def cookie_value(request):
    """The `__session` value the request carries, or None (a malformed header is no cookie)."""
    raw = _header(request, 'cookie')
    if not raw:
        return None
    for part in raw.split(';'):
        name, separator, value = part.strip().partition('=')
        if separator and name == COOKIE:
            value = value.strip().strip('"')
            return value if value and len(value) <= MAX_COOKIE and COOKIE_VALUE.fullmatch(value) else None
    return None


def same_origin(request, origins):
    """True when the browser says the request comes from this site (see the module docstring)."""
    site = _header(request, 'sec-fetch-site')
    if site is not None:
        return site == 'same-origin'
    origin = _header(request, 'origin')
    return origin is not None and origin.rstrip('/') in origins


def set_cookie(value, max_age=MAX_AGE):
    return f'{COOKIE}={value}; Max-Age={int(max_age)}; {ATTRIBUTES}'


def clear_cookie():
    return f'{COOKIE}=; Max-Age=0; {ATTRIBUTES}'


class AgentSessions:
    """Who is calling an agent route: the bearer token, else the session cookie.

    `users` is the alerts' `GoogleUsers` (ID tokens). `read_cookie(cookie) -> claims` and
    `mint(id_token, max_age) -> cookie` are firebase_admin's session-cookie calls in hosted mode
    (`src/api/hosted.py` `firebase_sessions`, which keeps the SDK out of this package); without
    them (demo mode) the session is unavailable and only the bearer token counts.
    """

    def __init__(self, users, read_cookie=None, mint=None, origins=DEFAULT_ORIGINS, max_age=MAX_AGE):
        self.users, self._mint, self.max_age = users, mint, int(max_age)
        self.origins = tuple(o.rstrip('/') for o in origins if o)
        self._cookie_users = (GoogleUsers(read_cookie, getattr(users, 'editors', ()))
                              if read_cookie is not None else None)

    @property
    def available(self):
        return self._mint is not None and self._cookie_users is not None

    def _source(self, request, unsafe):
        """`(users, authorization, via)`: the bearer token wins; the cookie only as stated above."""
        authorization = _header(request, 'authorization')
        if _bearer(authorization) is not None:
            return self.users, authorization, 'bearer'
        cookie = cookie_value(request)
        if cookie and self._cookie_users is not None and (not unsafe or same_origin(request, self.origins)):
            return self._cookie_users, 'Bearer ' + cookie, 'cookie'
        return self.users, None, None

    def user(self, request, unsafe=False):
        users, authorization, _via = self._source(request, unsafe)
        return users.user(authorization) if authorization else None

    def require(self, request, unsafe=False):
        users, authorization, _via = self._source(request, unsafe)
        if authorization is None:
            raise NotSignedIn()
        return users.require(authorization)

    def whoami(self, request):
        """`GET /api/agent/whoami`: the signed-in state, for the dock on every page."""
        users, authorization, via = self._source(request, unsafe=False)
        user = users.user(authorization) if authorization else None
        if user is None:
            return {'signed_in': False, 'session_available': self.available}
        try:
            users.require(authorization)
            editor = True
        except (NotSignedIn, NotAllowed):
            editor = False
        return {'signed_in': True, 'email': user['email'], 'provider': user['provider'], 'via': via,
                'editor': editor, 'session_available': self.available}

    def mint(self, id_token):
        """The session cookie for a verified ID token, or None when the token is not a sign-in."""
        if not self.available or type(id_token) is not str or _bearer('Bearer ' + id_token) is None:
            return None, None
        user = self.users.user('Bearer ' + id_token)
        if user is None:
            return None, None
        try:
            cookie = self._mint(id_token, self.max_age)
        except Exception:  # noqa: BLE001 - an unusable token is "not signed in", never an error page
            return None, None
        if isinstance(cookie, bytes):
            cookie = cookie.decode('ascii', 'replace')
        if type(cookie) is not str or not cookie or len(cookie) > MAX_COOKIE:
            return None, None
        return cookie, user


def register(app, sessions):
    """`POST /api/agent/session`, `POST /api/agent/session/end` and `GET /api/agent/whoami`; JSON, no cache class."""
    import json

    from fastapi import Request
    from fastapi.responses import JSONResponse

    messages = {'SIGN_IN_REQUIRED': 'Sign in to do this.',
                'SIGN_IN_UNAVAILABLE': 'Sign-in is not configured here.',
                'CROSS_SITE': 'This request did not come from this site.',
                'INVALID_INPUT': 'body: a JSON object with an id_token'}

    def refuse(code, status, headers=None):
        return JSONResponse({'code': code, 'message': messages[code]}, status_code=status,
                            headers=headers or {})

    def token_of(request):
        raw = request.scope.get('h1.raw_body', b'')
        try:
            value = json.loads(raw or b'{}')
        except (ValueError, UnicodeDecodeError):
            return None
        if type(value) is not dict or set(value) != {'id_token'} or type(value['id_token']) is not str:
            return None
        return value['id_token']

    @app.post('/api/agent/session')
    def agent_session_start(request: Request):
        if not sessions.available:
            return refuse('SIGN_IN_UNAVAILABLE', 503)
        if not same_origin(request, sessions.origins):
            return refuse('CROSS_SITE', 403)
        token = token_of(request)
        if token is None:
            return refuse('INVALID_INPUT', 422)
        cookie, user = sessions.mint(token)
        if cookie is None:
            return refuse('SIGN_IN_REQUIRED', 401, {'Set-Cookie': clear_cookie()})
        return JSONResponse({'signed_in': True, 'email': user['email'], 'provider': user['provider'],
                             'max_age': sessions.max_age},
                            status_code=200, headers={'Set-Cookie': set_cookie(cookie, sessions.max_age)})

    @app.post('/api/agent/session/end')
    def agent_session_end(request: Request):
        if not same_origin(request, sessions.origins):
            return refuse('CROSS_SITE', 403)
        return JSONResponse({'signed_in': False}, status_code=200, headers={'Set-Cookie': clear_cookie()})

    @app.get('/api/agent/whoami')
    def agent_whoami(request: Request):
        return JSONResponse(sessions.whoami(request), status_code=200)
