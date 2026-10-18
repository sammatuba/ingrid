"""The agent HTTP surface, built the way src/alerts/routes.py is; mounted by src/api/hosted.py (DOCK-5).

Every answer is JSON and declares no cache class, so the application's header policy makes it
`no-store` (DOCK-5 classifies the routes private in tests/test_cache_headers.py). Sign-in is the
alerts' (`src/alerts/auth.py`: Google with a verified email, or the team's email and password
accounts); `users` is that module's `GoogleUsers`.

Routes (contract: docs/work/desk-agent-and-book-2026-10-18/agent-contract.md, section 4):
  GET  /api/agent/threads          signed in: {threads, cases, budget}
  GET  /api/agent/threads/{id}     signed in: {thread, turns}
  GET  /api/agent/cases            signed in: {cases} (the labelled fakes until the case lane lands)
  POST /api/agent/ask              anyone: {question, thread?, page_key?, cutoff?} -> the turn with
                                   `view`, `confirmations` and `budget`; an anonymous ask answers
                                   from the recorded plan sets only and runs no action that writes
  POST /api/agent/confirm/{id}     signed in: {decision: confirm | decline} ->
                                   {confirmation_id, state, decided_at, receipt}
  GET  /api/agent/drafts           signed in: {drafts}
  GET  /api/agent/queue            signed in: {items, budget}

DOCK-5: with `sessions` (`src/agent/session.py` `AgentSessions`), every route accepts the bearer
token or the same-origin session cookie, and the two `POST` routes take the cookie only from a
same-origin request. The sign-in rule for `ask` is the alerts' editor rule: an account outside
`NOWCAST_ALERT_EDITORS` (when that list is set) asks as an anonymous caller, so it writes nothing
it could not read back. Without `sessions` the routes read the bearer token as before.
"""
import json
import re

from src.alerts.auth import NotAllowed, NotSignedIn

from .service import InvalidInput
from .store import AlreadyDecided, RecordExists, StoreUnavailable, UnknownRecord

RECORD_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')

MESSAGES = {'SIGN_IN_REQUIRED': 'Sign in to do this.',
            'NOT_AN_EDITOR': 'This account may not use the agent here.',
            'STORAGE_UNAVAILABLE': 'The agent store could not be reached; try again.',
            'NOT_FOUND': 'Not found.',
            'ALREADY_DECIDED': 'This was already decided.'}


def register(app, service, users, sessions=None):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    def answer(body, status=200):
        return JSONResponse(body, status_code=status)

    def refuse(code, status, **extra):
        message = extra.get('reason') and (f"{extra['field']}: {extra['reason']}" if extra.get('field') else extra['reason'])
        return JSONResponse(dict(extra, code=code, message=message or MESSAGES.get(code, code)), status_code=status)

    def body_of(request):
        raw = request.scope.get('h1.raw_body', b'')
        try:
            value = json.loads(raw or b'{}')
        except (ValueError, UnicodeDecodeError):
            raise InvalidInput('body', 'JSON') from None
        if type(value) is not dict:
            raise InvalidInput('body', 'a JSON object')
        return value

    def guarded(fn):
        try:
            return fn()
        except NotSignedIn:
            return refuse('SIGN_IN_REQUIRED', 401)
        except NotAllowed:
            return refuse('NOT_AN_EDITOR', 403)
        except InvalidInput as exc:
            return refuse('INVALID_INPUT', 422, field=exc.field, reason=exc.reason)
        except UnknownRecord:
            return refuse('NOT_FOUND', 404)
        except AlreadyDecided:
            return refuse('ALREADY_DECIDED', 409)
        except (StoreUnavailable, RecordExists):
            return refuse('STORAGE_UNAVAILABLE', 503)

    def signed(request, unsafe=False):
        if sessions is not None:
            return sessions.require(request, unsafe=unsafe)
        return users.require(request.headers.get('authorization'))

    def asker(request):
        """The caller of `ask`: a signed-in editor, else None (an anonymous ask)."""
        if sessions is None:
            return users.user(request.headers.get('authorization'))
        try:
            return sessions.require(request, unsafe=True)
        except (NotSignedIn, NotAllowed):
            return None

    @app.get('/api/agent/threads')
    def agent_threads(request: Request):
        return guarded(lambda: answer(service.threads(signed(request))))

    @app.get('/api/agent/threads/{thread_id}')
    def agent_thread(thread_id: str, request: Request):
        def read():
            user = signed(request)
            if not RECORD_ID.fullmatch(thread_id):
                return refuse('NOT_FOUND', 404)
            return answer(service.thread(user, thread_id))
        return guarded(read)

    @app.post('/api/agent/ask')
    def agent_ask(request: Request):
        # `user` is None for an anonymous caller: the service answers from the recorded plan sets.
        return guarded(lambda: answer(service.ask(asker(request), body_of(request))))

    @app.post('/api/agent/confirm/{confirmation_id}')
    def agent_confirm(confirmation_id: str, request: Request):
        def decide():
            user = signed(request, unsafe=True)
            if not RECORD_ID.fullmatch(confirmation_id):
                return refuse('NOT_FOUND', 404)
            return answer(service.confirm(user, confirmation_id, body_of(request)))
        return guarded(decide)

    @app.get('/api/agent/cases')
    def agent_cases(request: Request):
        return guarded(lambda: answer(service.cases(signed(request))))

    @app.get('/api/agent/drafts')
    def agent_drafts(request: Request):
        return guarded(lambda: answer(service.drafts(signed(request))))

    @app.get('/api/agent/queue')
    def agent_queue(request: Request):
        return guarded(lambda: answer(service.queue(signed(request))))
