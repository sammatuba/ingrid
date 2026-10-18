"""The alerts HTTP surface, added to the hosted application (src/api/hosted.py).

Every answer here is JSON and declares no cache class, so the application's header policy makes it
`no-store` with the default content security policy. The page `/alerts` itself is served by
src/api/hosted.py with the sign-in policy (src/api SIGN_IN_POLICY).

Routes (contract: docs/work/alerts-portfolio-2026-10-17/intent.md):
  GET  /api/alerts/client-config   Firebase web config for the sign-in button (public)
  GET  /api/alerts/config          what the caller may see of the portfolio and the rules
  PUT  /api/alerts/portfolio       signed in with Google: a new portfolio version
  GET  /api/alerts/portfolio/draft signed in: the portfolio import's draft (404 IMPORT_OFF when off)
  PUT  /api/alerts/rules           signed in with Google: a new rules version
  POST /api/alerts/run             signed in with Google: check one interval; answers at once
  GET  /api/alerts/runs/{id}       signed in with Google: advance and read a run (poll until done)
  POST /api/alerts/scheduled       the Cloud Scheduler job only (Google OIDC token)
  POST /api/alerts/test-email      signed in with Google: one TEST message to the saved recipients
  GET  /api/alerts/history         the last 50 alerts (estimates and recipients hidden unless signed in)
  GET  /api/alerts/inbox           ?at=&view=all|high: alerts up to the clock, grouped, worst first
                                   (public; estimates hidden unless signed in)
  GET  /api/alerts/alert/{key}     ?at=: one replay alert with its series and notices around it (public;
                                   built from the bake on request; estimates hidden unless signed in)
  GET  /api/alerts/explain/{key}   ?at=: the alert's likely drivers, summary and paragraph, computed from
                                   the replay data (public; no model call), plus `ontology`, the full
                                   driver card: baked or saved, else computed in BigQuery for a signed-in
                                   caller on first open (capped bytes, saved in Firestore; the page asks
                                   again while it computes), and `ontology_status`, its state and note;
                                   src/alerts/ontology_live.py
"""
import json
import re

from .auth import NotAllowed, NotSignedIn
from .bigquery import QueryFailed
from .draft import DraftUnavailable
from .mail import MailUnavailable
from .model import InvalidInput
from .service import ChecksUnavailable, ImportOff, NoDraft, NoRules, UnknownAlert
from .store import StoreUnavailable, VersionExists

RUN_ID = re.compile(r'[0-9a-f]{32}\Z')


def register(app, service, users, scheduler, client_config):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    def answer(body, status=200):
        return JSONResponse(body, status_code=status)

    messages = {'SIGN_IN_REQUIRED': 'Sign in to do this.',
                'NOT_AN_EDITOR': 'This account may not edit the alerts settings.',
                'STORAGE_UNAVAILABLE': 'The settings store could not be reached; try again.',
                'UNAUTHENTICATED': 'Only the scheduled job may call this.', 'NOT_FOUND': 'Not found.',
                'SIGN_IN_UNAVAILABLE': 'Sign-in is not configured here.',
                'IMPORT_OFF': 'The portfolio import is switched off on this server.',
                'NO_DRAFT': 'No imported portfolio draft has been uploaded yet.',
                'DRAFT_UNAVAILABLE': 'The imported portfolio draft could not be read; try again.'}

    def refuse(code, status, **extra):
        # `message` is what the page shows; `reason` and `field` say what was refused.
        message = extra.get('reason') and (f"{extra['field']}: {extra['reason']}" if extra.get('field') else extra['reason'])
        return JSONResponse(dict(extra, code=code, message=message or messages.get(code, code)), status_code=status)

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
        except ImportOff:
            return refuse('IMPORT_OFF', 404)
        except NoDraft:
            return refuse('NO_DRAFT', 404)
        except DraftUnavailable:
            return refuse('DRAFT_UNAVAILABLE', 503)
        except NoRules:
            return refuse('NO_RULES', 409, reason='save the notification settings first')
        except ChecksUnavailable as exc:
            return refuse('CHECKS_UNAVAILABLE', 503, reason=exc.reason)
        except MailUnavailable:
            return refuse('EMAIL_UNAVAILABLE', 503, reason='email is not configured or the mail server refused')
        except (StoreUnavailable, VersionExists):
            return refuse('STORAGE_UNAVAILABLE', 503)
        except QueryFailed as exc:
            return refuse('CHECKS_UNAVAILABLE', 503, reason='BigQuery: ' + exc.reason)
        except UnknownAlert:
            return refuse('NOT_FOUND', 404)

    @app.get('/api/alerts/client-config')
    def alerts_client_config():
        config = client_config()
        return answer(config) if config else refuse('SIGN_IN_UNAVAILABLE', 503)

    @app.get('/api/alerts/config')
    def alerts_config(request: Request):
        return guarded(lambda: answer(service.config(users.user(request.headers.get('authorization')))))

    @app.put('/api/alerts/portfolio')
    def alerts_portfolio(request: Request):
        return guarded(lambda: answer(service.save_portfolio(users.require(request.headers.get('authorization')),
                                                             body_of(request))))

    @app.get('/api/alerts/portfolio/draft')
    def alerts_portfolio_draft(request: Request):
        return guarded(lambda: answer(service.portfolio_draft(users.require(request.headers.get('authorization')))))

    @app.put('/api/alerts/rules')
    def alerts_rules(request: Request):
        return guarded(lambda: answer(service.save_rules(users.require(request.headers.get('authorization')),
                                                         body_of(request))))

    @app.post('/api/alerts/run')
    def alerts_run(request: Request):
        def run():
            result = service.start_run(users.require(request.headers.get('authorization')), body_of(request))
            return answer(result, 200 if result['status'] == 'done' else 202)
        return guarded(run)

    @app.get('/api/alerts/runs/{run_id}')
    def alerts_run_status(run_id: str, request: Request):
        def read():
            user = users.require(request.headers.get('authorization'))
            if not RUN_ID.fullmatch(run_id):
                return refuse('NOT_FOUND', 404)
            run = service.poll_run(run_id)
            return answer(service.run_for(user, run)) if run else refuse('NOT_FOUND', 404)
        return guarded(read)

    @app.post('/api/alerts/scheduled')
    def alerts_scheduled(request: Request):
        if not scheduler.check(request.headers.get('authorization')):
            return refuse('UNAUTHENTICATED', 401)
        return guarded(lambda: answer(service.scheduled()))

    @app.post('/api/alerts/test-email')
    def alerts_test_email(request: Request):
        return guarded(lambda: answer(service.test_email(users.require(request.headers.get('authorization')))))

    @app.get('/api/alerts/history')
    def alerts_history(request: Request):
        return guarded(lambda: answer({'alerts': service.history(users.user(request.headers.get('authorization')))}))

    @app.get('/api/alerts/inbox')
    def alerts_inbox(request: Request):
        q = request.query_params
        return guarded(lambda: answer(service.inbox(users.user(request.headers.get('authorization')),
                                                    q.get('at') or None, q.get('view') or 'all')))

    @app.get('/api/alerts/alert/{key}')
    def alerts_alert(key: str, request: Request):
        return guarded(lambda: answer(service.alert(users.user(request.headers.get('authorization')),
                                                    key, request.query_params.get('at') or None)))

    @app.get('/api/alerts/explain/{key}')
    def alerts_explain(key: str, request: Request):
        return guarded(lambda: answer(service.explain(users.user(request.headers.get('authorization')),
                                                      key, request.query_params.get('at') or None)))
