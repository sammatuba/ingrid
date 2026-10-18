"""The journal HTTP surface, added to the hosted application (src/api/hosted.py).

Every answer here is JSON and declares no cache class, so the application's header policy makes it
`no-store` with the default content security policy. The page `/journal` is served by
src/api/hosted.py like the other grid pages.

Every route needs a signed-in user (a verified Firebase ID token, src/alerts/auth.py GoogleUsers);
without one it answers 401 SIGN_IN_REQUIRED, reads included, because private entries are the
default (decision D2).

Routes:
  GET  /api/journal              list: q, plant, event, region, since, until (YYYY-MM-DDTHH:MM),
                                 scope=mine|desk, sort=newest|oldest
  POST /api/journal              create one entry; the author is the token's user
  PUT  /api/journal/{entry_id}   change your own entry's text and/or visibility
Refusals are `{code, message, field?, reason?}` like the alerts routes.
"""
import json

from src.alerts.auth import NotSignedIn

from .model import InvalidInput
from .service import NotFound, NotYours
from .store import EntryExists, StoreUnavailable


def register(app, service, users):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    messages = {'SIGN_IN_REQUIRED': 'Sign in to use the journal.',
                'NOT_FOUND': 'No such journal entry.',
                'NOT_YOURS': 'Only the author can change this entry.',
                'STORAGE_UNAVAILABLE': 'The journal store could not be reached; try again.'}

    def refuse(code, status, **extra):
        message = extra.get('reason') and (f"{extra['field']}: {extra['reason']}" if extra.get('field') else extra['reason'])
        return JSONResponse(dict(extra, code=code, message=message or messages.get(code, code)), status_code=status)

    def signed_in(request):
        user = users.user(request.headers.get('authorization'))
        if user is None or type(user.get('uid')) is not str or not user['uid']:
            raise NotSignedIn()
        return user

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
        except InvalidInput as exc:
            return refuse('INVALID_INPUT', 422, field=exc.field, reason=exc.reason)
        except NotFound:
            return refuse('NOT_FOUND', 404)
        except NotYours:
            return refuse('NOT_YOURS', 403)
        except (StoreUnavailable, EntryExists):
            return refuse('STORAGE_UNAVAILABLE', 503)

    @app.get('/api/journal')
    def journal_list(request: Request, q: str = '', plant: str = '', event: str = '', region: str = '',
                     since: str = '', until: str = '', scope: str = 'mine', sort: str = 'newest'):
        return guarded(lambda: JSONResponse(service.list(
            signed_in(request), q=q, plant=plant, event=event, region=region, since=since, until=until,
            scope=scope, sort=sort)))

    @app.post('/api/journal')
    def journal_create(request: Request):
        return guarded(lambda: JSONResponse(service.create(signed_in(request), body_of(request)), status_code=201))

    @app.put('/api/journal/{entry_id}')
    def journal_update(entry_id: str, request: Request):
        return guarded(lambda: JSONResponse(service.update(signed_in(request), entry_id, body_of(request))))
