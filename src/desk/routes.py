"""The desk API's five routes (docs/work/ui-refinement-2026-10-18/desk-api.md).

  GET  /api/desk/search?q=&at=&limit=     grouped search results for the command bar
  GET  /api/desk/preview/{kind}/{id}?at=  one entity's card (404 {"error": "NOT_FOUND"} when unknown)
  GET  /api/desk/prompts?at=&page=        3 to 5 prompts with an answer at the clock, and `model`:
                                          whether this caller's answer would be a live Gemini run
  POST /api/desk/answer                   {"question", "prompt_id", "at", "page"}: a composed answer
  POST /api/desk/answer/stream            the same body and answer as `text/event-stream`: one
                                          `{"event": "step", "step": ...}` per live tool step as it
                                          runs, then `{"event": "answer", "answer": ...}`

Public reads: every answer declares no cache class, so the application's header policy makes it
`no-store` with the default content security policy. `at` is `YYYY-MM-DDTHH:MM` (Manila wall
time); absent, it is the bake's last interval; malformed, 422.

Only `answer` may call a model, and only when the live path is configured (`DESK_GEMINI=1`) and the
caller is signed in through the agent's session, under the agent's day meter. Otherwise it serves
the recorded Gemini run for that prompt and clock when the bake holds one, else the composed answer.
`model` says which, and why (`fallback_reason`).

The stream route validates exactly as `answer` does (a refusal is the same JSON 422) and runs the
same `respond`. A step is sent only after its tool call has run in the live loop, and the final
`answer` event carries the very body `answer` would have returned. A live run that is set aside
(an invalid answer, a timeout) has sent its steps, and its answer event is the recorded or composed
answer with `fallback_reason` saying why. The recorded and composed paths send no steps: their
trace is in the answer.
"""
import json
import queue
import threading
from dataclasses import dataclass

from . import answer as answers
from . import live as living
from . import search as searching
from .bake import AT, bake_for
from .gemini import DEFAULT_MODEL, VertexClient, config_from_env


@dataclass
class DeskLive:
    """Who may get a live Gemini answer and how: off (`config` None), or signed in under the meter.

    `sessions` is the agent's `AgentSessions` (bearer token, or the same-origin session cookie);
    `meter` is the agent's `DayMeter`, so the desk and the dock share one daily line.
    """
    config: object = None
    client: object = None
    sessions: object = None
    meter: object = None

    @property
    def model_name(self):
        return self.config.model if self.config is not None else DEFAULT_MODEL

    def user(self, request):
        if self.sessions is None:
            return None
        try:
            return self.sessions.user(request, unsafe=True)
        except Exception:  # noqa: BLE001 - an unreadable sign-in is anonymous, never an error page
            return None


def wiring(sessions=None, store=None, environ=None):
    """The live wiring from the environment (`src/desk/gemini.py`); off when DESK_GEMINI is not 1."""
    config = config_from_env(environ)
    if config is None:
        return DeskLive(sessions=sessions)
    from src.agent.budget import DayMeter
    return DeskLive(config, VertexClient(config), sessions, DayMeter(store) if store is not None else None)


def refusal(live, request):
    """Why this caller's answer would not be a live run (`None`: it would be)."""
    if live.config is None or live.client is None:
        return 'not_configured'
    if live.user(request) is None:
        return 'sign_in_required'
    if live.meter is None:
        return 'budget_unavailable'
    return None


def model_for(live, request):
    """The `model` the prompts route reports: live when this caller would get a live run."""
    live = live or DeskLive()
    reason = refusal(live, request)
    return living.badge(live.model_name, 'live' if reason is None else 'composed', fallback_reason=reason)


def respond(bake, at, body, request, live, on_step=None):
    """The answer the route returns: live for a signed-in user when configured, else the recorded
    run for this prompt and clock, else the composed answer; each labelled in `model`.
    `on_step` receives each live tool step as it runs (`live.run`); it changes nothing returned."""
    question, prompt_id = body.get('question') or '', body.get('prompt_id')
    page = body.get('page') if isinstance(body.get('page'), str) else None
    composed = answers.answer(bake, at, question, prompt_id, page)
    live = live or DeskLive()
    reason = refusal(live, request)
    if reason is None:
        result, reason = living.run(bake, at, composed['question'], page, live.client, live.config, live.meter,
                                    on_step=on_step)
        if result is not None:
            result.pop('receipt', None)
            return result
    recorded = living.load_recorded(bake, prompt_id, at) if prompt_id else None
    if recorded is not None:
        recorded['model']['fallback_reason'] = reason
        return recorded
    composed['model'] = living.badge(live.model_name, 'composed', fallback_reason=reason)
    return composed


def sse(event):
    """One server-sent event: a single `data:` line of JSON."""
    return ('data: ' + json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n\n').encode('utf-8')


def stream(bake, at, body, request, live):
    """The streaming answer: `respond` runs on its own thread and each live step is sent as it
    happens, then the answer. Nothing runs until the first event is asked for."""
    events, done = queue.Queue(), object()

    def work():
        try:
            events.put({'event': 'answer',
                        'answer': respond(bake, at, body, request, live,
                                          on_step=lambda step: events.put({'event': 'step', 'step': step}))})
        except Exception:  # noqa: BLE001 - the client falls back to the plain route on a stream with no answer
            events.put({'event': 'error'})
        finally:
            events.put(done)

    threading.Thread(target=work, name='desk-answer-stream', daemon=True).start()
    while True:
        event = events.get()
        if event is done:
            return
        yield sse(event)


def _at(raw, bake):
    if raw is None or raw == '':
        return bake.last() or '1970-01-01T00:00'
    return raw if isinstance(raw, str) and AT.fullmatch(raw) else None


def register(app, data_dir, live=None):
    """Add the five routes to `app`; `data_dir` is a path or a function giving one (read lazily).
    `live` is the `DeskLive` wiring; absent, every answer is recorded or composed."""
    from fastapi import Request
    import fastapi.responses as responses
    from fastapi.responses import JSONResponse

    def bake():
        return bake_for(data_dir() if callable(data_dir) else data_dir)

    def invalid(field):
        return JSONResponse({'error': 'INVALID_INPUT', 'field': field}, status_code=422)

    def query(request, name):
        params = getattr(request, 'query_params', None) or {}
        return params.get(name)

    @app.get('/api/desk/search')
    def desk_search(request: Request):
        b = bake()
        at = _at(query(request, 'at'), b)
        if at is None:
            return invalid('at')
        try:
            limit = int(query(request, 'limit') or searching.DEFAULT_LIMIT)
        except ValueError:
            return invalid('limit')
        q = str(query(request, 'q') or '')[:200]
        return JSONResponse(searching.search(b, q, at, limit))

    @app.get('/api/desk/preview/{kind}/{ident}')
    def desk_preview(kind: str, ident: str, request: Request):
        b = bake()
        at = _at(query(request, 'at'), b)
        if at is None:
            return invalid('at')
        card = searching.preview(b, kind, ident, at)
        if card is None:
            return JSONResponse({'error': 'NOT_FOUND'}, status_code=404)
        return JSONResponse(card)

    @app.get('/api/desk/prompts')
    def desk_prompts(request: Request):
        b = bake()
        at = _at(query(request, 'at'), b)
        if at is None:
            return invalid('at')
        return JSONResponse({'prompts': answers.prompts(b, at, query(request, 'page')),
                             'model': model_for(live, request)})

    def asked(request):
        """`(bake, at, body)` for a well-formed question, or the 422 both answer routes refuse with."""
        raw = request.scope.get('h1.raw_body', b'')
        try:
            body = json.loads(raw or b'{}')
        except (ValueError, UnicodeDecodeError):
            return invalid('body')
        if type(body) is not dict:
            return invalid('body')
        question, prompt_id = body.get('question'), body.get('prompt_id')
        if question is not None and not isinstance(question, str):
            return invalid('question')
        if prompt_id is not None and not isinstance(prompt_id, str):
            return invalid('prompt_id')
        if len(question or '') > answers.MAX_QUESTION:
            return invalid('question')
        b = bake()
        at = _at(body.get('at'), b)
        if at is None:
            return invalid('at')
        return b, at, body

    @app.post('/api/desk/answer')
    def desk_answer(request: Request):
        question = asked(request)
        if not isinstance(question, tuple):
            return question
        b, at, body = question
        return JSONResponse(respond(b, at, body, request, live))

    @app.post('/api/desk/answer/stream')
    def desk_answer_stream(request: Request):
        question = asked(request)
        if not isinstance(question, tuple):
            return question
        b, at, body = question
        # `X-Accel-Buffering: no` asks a buffering proxy to pass each event on as it is written.
        # Read off the module at call time, so a test stub without it still registers the rest.
        return responses.StreamingResponse(stream(b, at, body, request, live), media_type='text/event-stream',
                                           headers={'X-Accel-Buffering': 'no'})

    return app
