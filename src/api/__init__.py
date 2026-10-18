"""H1 local HTTP application factory; no default cloud connection."""
import base64
import binascii
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel, ConfigDict

from src.adapters.identity import AuthenticationFailed, MembershipIdentity
from src.review import ReviewError
from src.review.errors import require
from src.review.pairing import register_pair_route
from src.review.storage import StorageUnavailable
from src.judgment import JudgmentService, JudgmentUnavailable
from src.judgment.systemone import SystemOneService

LOG = logging.getLogger('nowcast.http')

# --- the public grid desk (GRID-2) ------------------------------------------------------------
# The grid pages under `src/grid` are served with the build stamp written in; the replay data
# they read is baked by scripts/grid/build_data.py and ships beside the code in the image,
# never in Git. `/` is the grid desk, the change desk it replaced stays reachable at `/desk`
# with its assets at their unchanged paths, and every route added here is additive.
GRID_DIR = Path(__file__).resolve().parents[1] / 'grid'
DESK_DIR = Path(__file__).resolve().parents[1] / 'workspace'
GRID_FILES = frozenset({'index.html', 'event.html', 'event.css', 'event.js', 'event-api.js',
                        'grid.css', 'grid.js', 'explain.html', 'explain.css', 'explain.js',
                        # DESK-3: the outlooks page at `/outlooks`, the archive's own surface.
                        'outlooks.html', 'outlooks.css', 'outlooks.js',
                        # DESK-5: the register page at `/register`, the register's own surface.
                        'register.html', 'register.css', 'register.js',
                        # ROUTES-1: the four pages the page briefs build (/models, /work, /map,
                        # /ask), shipped as shells so the routes, the staging list and the
                        # section navigation are in place before the briefs land.
                        'models.html', 'models.css', 'models.js',
                        'work.html', 'work.css', 'work.js',
                        'map.html',
                        'ask.html', 'ask.css', 'ask.js',
                        # UX-1: the command bar every page but /ask loads through shell.js.
                        'command.js', 'command.css',
                        # Platform polish: the shared component layer every page links before
                        # shell.css, and its small behaviour helpers the shell loads.
                        'ui.css', 'ui.js',
                        # PP-B4: the project map's own frame and the reading pages' rail.
                        'projectmap.css', 'reading.js',
                        'assets.html', 'asset.html', 'asset.css', 'asset.js',
                        # ATG-4's catalog page (`/data`), ATG-5's briefing and findings panel and
                        # ATG-6's map canvas, which the grid page loads and mounts (ATG-8;
                        # `src/api/hosted.py` serves /data).
                        'catalog.html', 'catalog.css', 'catalog.js', 'briefs.css', 'briefs.js',
                        'map.css', 'map.js',
                        # The alerts and portfolio page (`/alerts`, `src/api/hosted.py`) and the
                        # Firebase JS SDK it signs in with, vendored byte for byte (10.12.2 compat).
                        'alerts.html', 'alerts.css', 'alerts.js',
                        'firebase-app-compat.js', 'firebase-auth-compat.js',
                        # The working paper (`/paper`), built by scripts/docs/build_paper.py.
                        'paper.html', 'paper.css',
                        # ericka-desk: the shared shell (top bar, theme, replay clock, ticker)
                        # Added by slice 1 of docs/work/ericka-desk-2026-10-18/intent.md.
                        'shell.css', 'shell.js',
                        # ericka-desk E9, E10: the outage and derating tracker
                        'outages.css', 'outages.js',
                        # ericka-desk slice 8: the Trader's Journal page (`/journal`,
                        # `src/api/hosted.py`) and its reusable "Add to journal" box.
                        'journal.html', 'journal.css', 'journal.js', 'journal-box.js',
                        # ericka-desk slice 3: the dashboard's region cards, link monitor and trip rings.
                        'overview.js', 'overview.css', 'event-desk.js', 'event-desk.css',
                        'dash-alerts.js', 'dash-map.js', 'dashboard.css',
                        # ericka-desk: the operator notices page (`/notices`)
                        'notices.html', 'notices.js', 'notices.css',
                        # ericka-desk: the alert settings page (`/settings`); alerts.js drives it
                        'settings.html', 'settings.css',
                        # ericka-desk: an alert's own page (`/alert/<alert key>`), built on request
                        # from the baked replay when no recorded event explains the alert.
                        'spike.html', 'spike.js', 'spike.css',
                        # BOOK-3's book page (`/book`, DOCK-5): the synthetic book's exposure.
                        'book.html', 'book.css', 'book.js',
                        # "How we got this": the data-flow dialog behind the "?" on card headers.
                        'flow.js', 'flow.css',
                        # InGRID brand (docs/brand/README.md): the mark, the logo, and the icons
                        # and manifest also answered at the site root (BRAND_ROOT_FILES).
                        'ingrid-mark.svg', 'ingrid-logo.svg',
                        'favicon.ico', 'favicon.svg', 'apple-touch-icon.png', 'icon-192.png',
                        'icon-512.png', 'icon-maskable-512.png', 'site.webmanifest'})
# The files a browser asks for at the site root by convention or through the pages' head links:
# each has its own root route, serves the design file of the same name, and revalidates.
BRAND_ROOT_FILES = ('favicon.ico', 'favicon.svg', 'apple-touch-icon.png', 'icon-192.png',
                    'icon-512.png', 'icon-maskable-512.png', 'site.webmanifest')
FONT_NAME = re.compile(r'[a-z0-9][a-z0-9._-]*\.woff2\Z')
# One baked replay file: a name in the data directory, `events/<id>.json` or
# `assets/<code>.json` (ATG-7's profiles), or one of the page files —
# `outlook/index.json` (DESK-3), `register/index.json` (DESK-5) and the book page's two files
# `book/index.json` and `book/exposure.json` (BOOK-3, DOCK-5). A name cannot start with a
# dot and holds no other separator, so `..`, an absolute name and a nested escape cannot match
# at all; the resolve() below is the second check, for symlinks.
# ericka-desk slice 7: ontology/ (the event's drivers file, which hosting already ships) joins the four;
# DOCK-5: book/ (the book page's two files).
# replay-year: days/<YYYY-MM-DD>.json and advisories/<YYYY-MM>.json (the year replay, by day and month).
# DATA-1 (and UX-B, the same fix on both branches): views/<key>.json and views/index.json
# (BAKE-1's recorded plan sets, read by ask.js's dock, now the command bar). Without it Cloud Run
# answered 404 for every dock answer. The directories here are every
# directory the bake writes (build_data.py, build_catalog.py, briefs.py, build_assets.py,
# build_outages.py); tests/test_cache_headers.py walks the fixture bakes (and build/grid-data when
# it is there) and requires every baked file to be served, so a new directory cannot 404 silently.
GRID_DATA_NAME = re.compile(r'(?:events/|assets/|outlook/|register/|ontology/|days/|advisories/|views/|book/)?'
                            r'[A-Za-z0-9][A-Za-z0-9._-]*\.(?:json|geojson)\Z')
MEDIA_TYPES = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
               '.json': 'application/json', '.geojson': 'application/geo+json',
               '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png',
               '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json'}
CONTENT_SECURITY_POLICY = ("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                           "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                           "form-action 'self'")
# The one other policy an answer may carry: the alerts page's, for "Sign in with Google" through
# Firebase Auth. The SDK is served from this origin; the sign-in itself loads Google's API loader
# (apis.google.com), frames the project's Firebase auth handler (*.firebaseapp.com) and calls the
# Identity Toolkit and Secure Token APIs. A route earns it only by declaring it on its answer
# (`declaring_policy`); since ericka-desk D1 every grid page does (`page_response`), so the shared
# shell can sign in anywhere. Every other answer carries CONTENT_SECURITY_POLICY, unchanged.
SIGN_IN_POLICY = ("default-src 'self'; script-src 'self' https://apis.google.com; style-src 'self'; "
                  "connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com "
                  "https://apis.google.com; frame-src https://*.firebaseapp.com https://apis.google.com "
                  "https://accounts.google.com; img-src 'self'; object-src 'none'; base-uri 'none'; "
                  "frame-ancestors 'none'; form-action 'self'")
# The live release measured one baked day of node data at 1.8 MB and the grid page draws
# nothing until it arrives, so an answer at or above a kibibyte travels gzip-compressed when
# the client accepts it. The floor is the library's minimum size, not a second guess: the
# small JSON replies stay byte-identical on the wire.
GZIP_MINIMUM_SIZE = 1024

# --- the three cache classes (PERF-1) ---------------------------------------------------------
# One build stamp names one version of everything public this application serves: the baked
# replay files and the grid design files (pages, code, styles, fonts). It is derived from their
# content when the application is built, written into the served pages, and carried as the
# first path segment of every versioned URL, so a URL that carries it can be cached for a
# year: the same URL always answers the same bytes, and changed content is a new URL. An
# unknown stamp is a 404 at the route, never a fallback to the current files.
#
# A route earns a class by declaring it on the answer it returns (`declaring`, read back by
# `declared_class`), and only after it has validated what it is serving: an existing file under
# *this* build's stamp, or a page this process renders. `cache_control` is the one place the
# class string is decided, and it answers `no-store` for an answer no route declared and for
# every answer that is not 200. No URL earns a class by its shape: a route added under
# `/event/` or `/grid/` is private until its own code says otherwise.
IMMUTABLE_CACHE = 'public, max-age=31536000, immutable'
REVALIDATE_CACHE = 'no-cache'
NO_STORE = 'no-store'
CACHE_CLASSES = frozenset({IMMUTABLE_CACHE, REVALIDATE_CACHE, NO_STORE})
# 16 hex digits (64 bits) of the digest: short enough for a URL path, wide enough that two
# builds cannot collide. The token is what the source pages carry where the stamp goes; it is
# not stamp-shaped, so a page served without substitution (a fixture harness, or a static file
# served as it lies) can never be mistaken for a versioned one.
STAMP_SIZE = 16
STAMP_TOKEN = '__NOWCAST_STAMP__'
STAMP_SHAPE = re.compile(r'[0-9a-f]{%d}\Z' % STAMP_SIZE)


def grid_asset(name: str) -> Path | None:
    """The design file `name` names, or None: one of the pages, its code, or a vendored font."""
    allowed = name in GRID_FILES or (name.startswith('fonts/') and FONT_NAME.fullmatch(name[6:]))
    candidate = GRID_DIR / name
    return candidate if allowed and candidate.is_file() else None


# An alert key (src/alerts/model.py alert_key): 24 lowercase hex digits.
ALERT_PAGE_ID = re.compile(r'[0-9a-f]{24}\Z')


# The replay time an alert page may be opened at (`?at=2026-09-21T13:40`), kept across the redirect.
REPLAY_AT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z')


def event_page_file(event_id: str, data_dir: Path) -> Path:
    """The page `/event/<id>` stands for: the alert's own page (spike.html) for an alert key that no
    baked event carries, else the event review page, for a baked event and any other id as before.
    The route itself redirects the alert case to `/alert/<key>` (alert_page_path)."""
    if ALERT_PAGE_ID.fullmatch(event_id) and not (Path(data_dir) / 'events' / f'{event_id}.json').is_file():
        return GRID_DIR / 'spike.html'
    return GRID_DIR / 'event.html'


def alert_page_path(key: str, at=None) -> str:
    """`/alert/<key>`, the address of an alert no recorded event explains, with a well-formed
    replay time kept (anything else in `at` is dropped)."""
    return f'/alert/{key}' + (f'?at={at}' if isinstance(at, str) and REPLAY_AT.fullmatch(at) else '')


def grid_data_directory(environ=None) -> Path:
    """Where the baked replay files are, in the order the repository states them.

    `GRID_DATA_DIR` names the directory outright. Otherwise the builder's own output
    (`build/grid-data`, scripts/grid/build_data.py) and the image's copy beside the code
    (`src/grid/grid-data`, the Dockerfile line after `COPY src ./src`) are tried in turn. A
    directory that is not there is not an error here: every file below it is a 404.
    """
    env = os.environ if environ is None else environ
    given = (env.get('GRID_DATA_DIR') or '').strip()
    if given:
        return Path(given)
    root = Path(__file__).resolve().parents[2]
    for candidate in (root / 'build' / 'grid-data', root / 'src' / 'grid' / 'grid-data'):
        if candidate.is_dir():
            return candidate
    return root / 'build' / 'grid-data'


def grid_data_file(name: str, directory: Path) -> Path | None:
    """The baked file `name` names inside `directory`, or None when it is missing or escapes."""
    if not GRID_DATA_NAME.fullmatch(name):
        return None
    try:
        base = Path(directory).resolve(strict=True)
        resolved = (base / name).resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_file() and base in resolved.parents else None


def media_type_for(path: Path) -> str:
    """The content type of one served file; anything unreviewed is an opaque binary."""
    return MEDIA_TYPES.get(path.suffix, 'application/octet-stream')


def build_stamp(data_dir=None, grid_dir=GRID_DIR) -> str:
    """The content-derived build stamp: a digest over the baked replay files and the design files.

    Every file under the data directory and under `src/grid` contributes its relative name and
    the digest of its bytes, in a fixed order, so the stamp changes when any byte of the replay
    data or of the page's own code, styles or fonts changes, and never otherwise. The image
    keeps the baked data inside `src/grid` (`COPY build/grid-data ./src/grid/grid-data`), where
    the data files would be walked twice; they are counted once, so an image build and the
    `build/grid-data` tree it was built from derive the same stamp. A data directory that is
    not there contributes nothing — every file below it is a 404 — and is not an error here.
    DATA-2: the bake manifest (`manifest.json` at the data root, scripts/grid/build_all.py)
    is the one file left out: it records this stamp, so it cannot be part of it.
    """
    digest = hashlib.sha256()
    seen = set()
    for label, root in (('data', grid_data_directory() if data_dir is None else data_dir),
                        ('grid', grid_dir)):
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(entry for entry in root.rglob('*') if entry.is_file()):
            resolved = path.resolve()
            # DATA-2: the bake manifest at the data root names this stamp, so it cannot be part
            # of it; it is marked seen, so the image's copy inside src/grid is not counted either.
            if label == 'data' and path.relative_to(root).as_posix() == 'manifest.json':
                seen.add(resolved)
                continue
            if resolved in seen:  # the image holds the data inside src/grid: count it once
                continue
            seen.add(resolved)
            digest.update(label.encode('ascii'))
            digest.update(b'\0')
            digest.update(path.relative_to(root).as_posix().encode('utf-8'))
            digest.update(b'\0')
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()[:STAMP_SIZE]


def requested_stamp(name: str) -> tuple:
    """`(stamp, name_without_it)`: the build stamp a served path carries, if it carries one.

    A served file's first path segment is its build stamp when it is stamp-shaped; the rest of
    the name goes to the same allow-list the unversioned route uses. A path that carries no
    stamp-shaped segment is the unversioned form, whose answers are never cached.
    """
    head, slash, rest = name.partition('/')
    if slash and STAMP_SHAPE.match(head):
        return head, rest
    return '', name


def stamped_page(source: Path, stamp: str) -> str:
    """The page's own bytes with the build stamp written into the asset and data URLs.

    The source pages carry `__NOWCAST_STAMP__` where the stamp goes: the script and stylesheet
    URLs, and the `nowcast-build` meta element the page's own scripts read to build the replay
    data URLs (and, through the stylesheet's relative font URLs, the font prefix). The change
    desk at `/desk` carries no token: its own assets are not versioned, so the answer's
    `no-cache` is what keeps that page fresh.
    """
    return source.read_text(encoding='utf-8').replace(STAMP_TOKEN, stamp)


def declared_class(answer):
    """The cache class the route declared on this answer, or None when it declared none.

    An answer with no headers at all — a route returning a plain value, which the server
    library renders into a response of its own — has declared nothing and so is `no-store`.
    """
    return getattr(answer, 'headers', {}).get('Cache-Control')


def declaring(answer, cache_class):
    """Name one answer's cache class: the one way a route earns more than `no-store`.

    A route calls this on the answer it is about to return, and only after it has validated
    what it is serving — an existing file under this build's stamp, or a page this process
    renders. The declaration is the answer's own `Cache-Control`, because a response's headers
    are what cross the server library's own middleware wrapping (a private attribute on the
    answer does not survive `BaseHTTPMiddleware`'s re-wrap, and would leave every answer
    `no-store` on the wire while the offline tests still read it). `cache_control` reads the
    declaration back and a route that declares nothing stays private however its URL looks.
    """
    answer.headers['Cache-Control'] = cache_class
    return answer


def cache_control(declared, status: int = 200) -> str:
    """The cache class of one answer: the one place the three classes are decided.

    (1) An answer whose route declared `IMMUTABLE_CACHE` — a versioned public file: the baked
    replay data or a design file, under the stamp that names its bytes — is immutable for a
    year, so a cached answer can never go stale. (2) An answer whose route declared
    `REVALIDATE_CACHE` — one of the HTML pages — revalidates, so a deploy is picked up on the
    next visit while the response stays a normal, cacheable control flow. (3) Everything else
    is `no-store`: an answer no route declared (every session, case, judge and API answer), a
    declaration that is not one of the three, and every answer that is not 200, refusals
    included.
    """
    if status != 200:
        return NO_STORE
    return declared if declared in CACHE_CLASSES else NO_STORE


def declaring_policy(answer, policy):
    """Name one answer's content security policy: only SIGN_IN_POLICY can be named.

    The declaration is the answer's own header, read back by `response_headers`; any other value
    is ignored there, so a route cannot widen the policy by accident.
    """
    answer.headers['Content-Security-Policy'] = policy
    return answer


def declared_policy(answer):
    """The policy an answer carries: SIGN_IN_POLICY when its route declared it, else the default."""
    declared = getattr(answer, 'headers', {}).get('Content-Security-Policy')
    return SIGN_IN_POLICY if declared == SIGN_IN_POLICY else CONTENT_SECURITY_POLICY


def response_headers(answer) -> dict:
    """The headers every answer carries, read off the answer the route produced.

    The cache class is `cache_control`'s decision, from the class the route declared on this
    answer and this answer's own status — so an undeclared answer, a declaration that is not
    one of the three, and a non-200 answer all come out `no-store`, whatever the URL looks
    like. An answer that carries no status is a 200 by construction. The content security
    policy and `X-Content-Type-Options` are unchanged by this lane; the CSP still admits no
    origin other than this one.
    """
    return {'Cache-Control': cache_control(declared_class(answer),
                                           getattr(answer, 'status_code', 200)),
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy': declared_policy(answer)}


def page_response(source: Path, stamp: str):
    """One HTML page answer, and the file it was rendered from.

    The body is the page with this build's stamp written into the URLs it references, and the
    answer's `path` is the source page — the same relationship a `FileResponse`'s `path` has to
    the file it streams, so a caller that reads which file answered still can. The change desk
    stays a plain `FileResponse`: it carries no token, so there is nothing to write into it.

    Every grid page carries SIGN_IN_POLICY (ericka-desk decision D1): the shared shell shows the
    account chip on every page and loads the vendored Firebase SDK when sign-in is configured.
    Data files, design files and API answers keep CONTENT_SECURITY_POLICY.
    """
    response = Response(content=stamped_page(Path(source), stamp),
                        media_type=MEDIA_TYPES['.html'])
    response.path = Path(source)
    return declaring_policy(response, SIGN_IN_POLICY)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class RefBody(StrictModel):
    ref: dict


class EvidenceBody(StrictModel):
    record: dict
    source_base64: str | None = None


class SnapshotBody(StrictModel):
    audit_cutoff: str


class CompileBody(StrictModel):
    snapshot_ref: dict
    assumption_id: str
    information_cutoff: str
    passage_ids: list[str] | None = None


class PrepareBody(StrictModel):
    audit_cutoff: str
    information_cutoff: str


class ReviewBody(StrictModel):
    request_id: str
    idempotency_key: str
    task_ref: dict
    snapshot_digest: str
    expected_assumption_head: dict
    expected_outlook_head: dict | None
    disposition: str
    rationale: str
    new_value: dict | None
    judgment_ref: dict | None = None


class ProposalBody(StrictModel):
    idempotency_key: str


class JudgmentBody(StrictModel):
    task_ref: dict
    idempotency_key: str


class BundleBody(StrictModel):
    task_ref: dict
    idempotency_key: str


class SignInBody(StrictModel):
    email: str
    password: str


def error(code, status):
    return JSONResponse({'code': code}, status_code=status)


class BodyLimit:
    """Bound chunked and Content-Length requests before JSON/text parsing."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            data = message.get('body', b'')
            size += len(data)
            if size > 1024 * 1024:
                return await error('INVALID_RECORD', 422)(scope, receive, send)
            chunks.append(data)
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        scope['h1.raw_body'] = body
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()
        correlation = uuid4().hex
        async def safe_send(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((b'x-request-id', correlation.encode()))
                LOG.info('request=%s status=%s', correlation, message['status'])
            await send(message)
        await self.app(scope, bounded_receive, safe_send)


def create_app(repository, identity, clock=None, judgment=None, bundle=None, data_dir=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    # Registered before the header middleware below, so what it compresses is the routes'
    # answer and the header middleware then writes the policy onto the finished (possibly
    # gzipped) response. The compression decision — the floor, `Vary` — stays the library's.
    #
    # The import is inside the factory, not at module scope: the offline loaders stub the HTTP
    # stack by replacing `fastapi` in `sys.modules`, and a module-level Starlette import failed
    # every stub that supplies no Starlette name (release merge after GRID-3, reviews/GRID-2.md
    # finding 2). FastAPI carries Starlette, so a real application — and every loader built on
    # the real libraries — registers the middleware here; only a stub without Starlette skips
    # it, and a stub is not an application.
    try:
        from starlette.middleware.gzip import GZipMiddleware
    except ImportError:
        GZipMiddleware = None
    if GZipMiddleware is not None:
        app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)
    clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
    memberships = MembershipIdentity(repository.store)
    judgment = judgment or JudgmentService()
    bundle = bundle or SystemOneService()
    data_dir = grid_data_directory() if data_dir is None else Path(data_dir)
    # The build stamp is derived once, when the application is built, and every answer of this
    # process is served under it: a request can never see the stamp move under it.
    stamp = build_stamp(data_dir)

    @app.middleware('http')
    async def security_headers(request, call_next):
        # The policy is read off the answer the route produced — and the route declares its
        # class on that answer — so no part of it is decided from the request path.
        response = await call_next(request)
        response.headers.update(response_headers(response))
        return response

    @app.exception_handler(JudgmentUnavailable)
    async def model_unavailable(request, exc):
        return error(exc.code, 503)

    # `/` is the public grid desk (GRID-2) and `/desk` the change desk it replaced: the old
    # page's own code and assets keep their paths, so only the page URL moved. The grid page
    # is served with this build's stamp written into its asset and data URLs; both page routes
    # declare `REVALIDATE_CACHE`, so the next visit picks a new build up.
    @app.get('/')
    def grid_page():
        return declaring(page_response(GRID_DIR / 'index.html', stamp), REVALIDATE_CACHE)

    @app.get('/desk')
    def change_desk_page():
        return declaring(FileResponse(DESK_DIR / 'index.html', media_type='text/html'),
                         REVALIDATE_CACHE)

    # Both grid routes serve the same allow-listed files, under their unversioned names and
    # under a leading build stamp. A stamp this build does not know is a 404 — a file is never
    # served under a version it does not belong to — and only a name that carries this build's
    # stamp is declared immutable. The unversioned name is still answered (a recorded flow),
    # but it declares nothing and so is never cached.
    @app.get('/grid/{name:path}')
    def grid_file(name: str):
        version, bare = requested_stamp(name)
        if version and version != stamp:
            return error('NOT_FOUND', 404)
        path = grid_asset(bare)
        if path is None:
            return error('NOT_FOUND', 404)
        answer = FileResponse(path, media_type=media_type_for(path))
        return declaring(answer, IMMUTABLE_CACHE) if version == stamp else answer

    @app.get('/grid-data/{name:path}')
    def grid_data(name: str):
        version, bare = requested_stamp(name)
        if version and version != stamp:
            return error('NOT_FOUND', 404)
        path = grid_data_file(bare, data_dir)
        if path is None:
            return error('NOT_FOUND', 404)
        answer = FileResponse(path, media_type=media_type_for(path))
        return declaring(answer, IMMUTABLE_CACHE) if version == stamp else answer

    # GRID-3's event review page is served by its own URL; its data comes from the same baked
    # replay directory (`/grid-data/<stamp>/events/<id>.json`, or the unversioned name), so it
    # needs no route of its own. `/event/` is for recorded events only: an alert key no baked
    # event carries (an older link to an alert's own page) is sent on to `/alert/<key>`.
    @app.get('/event/{event_id}')
    def event_page(event_id: str, at: str = None):
        source = event_page_file(event_id, data_dir)
        if source.name == 'spike.html':
            return Response(status_code=307, headers={'Location': alert_page_path(event_id, at)})
        return declaring(page_response(source, stamp), REVALIDATE_CACHE)

    # ericka-desk: an alert no recorded event explains has its own page (src/grid/spike.*), built
    # on request from the baked replay by /api/alerts/alert/<key>; served like the event page.
    @app.get('/alert/{key}')
    def alert_page(key: str):
        if not ALERT_PAGE_ID.fullmatch(key):
            return error('NOT_FOUND', 404)
        return declaring(page_response(GRID_DIR / 'spike.html', stamp), REVALIDATE_CACHE)

    # DOC-3: the explainer, the guided walk through the project for people, served as a page so
    # the team reaches it from the site. Built by scripts/docs/build_explainer.py from the
    # chapters under docs/explainer/; its stylesheet and script are design files under the stamp.
    @app.get('/explain')
    def explain_page():
        return declaring(page_response(GRID_DIR / 'explain.html', stamp), REVALIDATE_CACHE)

    # The working paper, served as a page so it can be read on the site. Built by
    # scripts/docs/build_paper.py from docs/product/; its stylesheet is a design file under the stamp.
    @app.get('/paper')
    def paper_page():
        return declaring(page_response(GRID_DIR / 'paper.html', stamp), REVALIDATE_CACHE)
    # DESK-3: the outlooks page, the price-outlook archive's own surface. It reads one baked
    # file (`/grid-data/<stamp>/outlook/index.json`) through the same route every replay file
    # travels, so it needs no second data route; served like `/explain`, it revalidates.
    @app.get('/outlooks')
    def outlooks_page():
        return declaring(page_response(GRID_DIR / 'outlooks.html', stamp), REVALIDATE_CACHE)

    # DESK-5: the register page, the committed assumption register's own surface. It reads one
    # baked file (`/grid-data/<stamp>/register/index.json`) through the same route every replay
    # file travels; served like `/explain`, it revalidates.
    @app.get('/register')
    def register_page():
        return declaring(page_response(GRID_DIR / 'register.html', stamp), REVALIDATE_CACHE)

    # BOOK-3's book page, served by DOCK-5 exactly like `/outlooks`. It reads two baked files
    # (`/grid-data/<stamp>/book/index.json` and `book/exposure.json`, built from the synthetic book
    # by scripts/book/bake_book.py) through the same route every replay file travels.
    @app.get('/book')
    def book_page():
        return declaring(page_response(GRID_DIR / 'book.html', stamp), REVALIDATE_CACHE)

    # ROUTES-1: the four pages the page briefs build, each served exactly like `/outlooks` so a
    # brief owns only its own files. `/ask` is the desk assistant's full-screen panel; the same
    # component is mounted on every page through the `<section id="ask">` mount point.
    @app.get('/models')
    def models_page():
        return declaring(page_response(GRID_DIR / 'models.html', stamp), REVALIDATE_CACHE)

    @app.get('/work')
    def work_page():
        return declaring(page_response(GRID_DIR / 'work.html', stamp), REVALIDATE_CACHE)

    @app.get('/map')
    def map_page():
        return declaring(page_response(GRID_DIR / 'map.html', stamp), REVALIDATE_CACHE)

    @app.get('/ask')
    def ask_page():
        return declaring(page_response(GRID_DIR / 'ask.html', stamp), REVALIDATE_CACHE)

    # InGRID brand: the icons and the manifest every page's head links, at the root where a
    # browser also asks for `/favicon.ico` unprompted. Each serves the design file of the same
    # name (scripts/brand/build_icons.py draws the rasters) and revalidates like the pages, so a
    # new mark is picked up on the next visit without a stamped URL.
    def brand_file(name):
        def answer():
            path = GRID_DIR / name
            return declaring(FileResponse(path, media_type=media_type_for(path)), REVALIDATE_CACHE)
        answer.__name__ = 'brand_' + re.sub(r'\W', '_', name)
        return answer

    for icon in BRAND_ROOT_FILES:
        app.get('/' + icon)(brand_file(icon))

    @app.get('/assets/{name}')
    def workspace_asset(name: str):
        if name not in ('app.js', 'style.css'):
            return error('NOT_FOUND', 404)
        return FileResponse(DESK_DIR / name)

    @app.post('/session')
    def sign_in(body: SignInBody):
        if not hasattr(identity, 'sign_in'):
            raise AuthenticationFailed()
        return identity.sign_in(body.email, body.password)

    @app.exception_handler(ReviewError)
    async def domain_error(request, exc):
        if exc.code in {'ACCESS_DENIED', 'MISSING_INPUT'}:
            return error('NOT_FOUND', 404)
        # A decision naming an artifact of another task conflicts with recorded state,
        # like a stale head; a record whose provenance its case refuses or that cites no
        # signed permission is not an acceptable record at all.
        conflict = {'STALE_HEAD', 'STALE_DEPENDENCY', 'IDEMPOTENCY_CONFLICT', 'REVISION_CONFLICT', 'JUDGMENT_TASK_MISMATCH'}
        status = 409 if exc.code in conflict else 422
        return error(exc.code, status)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return error('INVALID_RECORD', 422)

    @app.exception_handler(AuthenticationFailed)
    async def unauthenticated(request, exc):
        return error('UNAUTHENTICATED', 401)

    @app.exception_handler(StorageUnavailable)
    async def unavailable(request, exc):
        return error('STORAGE_UNAVAILABLE', 503)

    def actor(request: Request, tenant: str, case: str):
        uid = identity.verify(request.headers.get('authorization'))
        return memberships.actor(uid, tenant, case)

    prefix = '/v1/tenants/{tenant}/cases/{case}'

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'local', 'storage_checked': False}

    @app.get(prefix)
    def case_read(case: str, a=Depends(actor)):
        return repository.heads(a, case)

    @app.get(prefix + '/history')
    def history(case: str, a=Depends(actor)):
        return repository.history(a, case)

    @app.get(prefix + '/workspace')
    def workspace(case: str, a=Depends(actor)):
        result = repository.workspace(a, case)
        result['model_available'] = judgment.provider is not None
        result['bundle_available'] = bundle.backend is not None
        return result

    @app.post(prefix + '/judgments')
    def generate_judgment(case: str, body: JudgmentBody, a=Depends(actor)):
        return judgment.generate(repository, a, case, body.task_ref, body.idempotency_key, clock)

    @app.post(prefix + '/probe-bundles')
    def generate_probe_bundle(case: str, body: BundleBody, a=Depends(actor)):
        return bundle.generate(repository, a, case, body.task_ref, body.idempotency_key, clock)

    # The cutoff pair view is additive and read-only; the route itself lives in
    # src/review/pairing.py, so this file only imports and registers it.
    register_pair_route(app, prefix, repository, actor)

    @app.get(prefix + '/receipts/{key}')
    def receipt(case: str, key: str, a=Depends(actor)):
        return repository.receipt(a, case, key)

    @app.post(prefix + '/read')
    def read(case: str, body: RefBody, a=Depends(actor)):
        return repository.read(a, case, body.ref)

    @app.post(prefix + '/evidence')
    def evidence(case: str, body: EvidenceBody, a=Depends(actor)):
        require(body.record.get('case_id') == case and body.record.get('tenant_id') == a.tenant_id, 'ACCESS_DENIED')
        data = None
        if body.source_base64 is not None:
            require(len(body.source_base64) <= 4 * ((256 * 1024 + 2) // 3), 'INVALID_SOURCE')
            try:
                data = base64.b64decode(body.source_base64, validate=True)
            except (ValueError, binascii.Error):
                raise ReviewError('INVALID_SOURCE') from None
            require(len(data) <= 256 * 1024, 'INVALID_SOURCE')
        return repository.register(a, body.record, source_bytes=data)

    @app.post(prefix + '/snapshots')
    def snapshot(case: str, body: SnapshotBody, a=Depends(actor)):
        return repository.build_snapshot(a, case, body.audit_cutoff, clock())

    # The event page's decision preparation in one round trip (PERF-3): the case heads, the
    # snapshot of the accepted state and the task compiled at the information cutoff come
    # back together, guarded by the same access check as every other route. It writes exactly
    # what the two routes above write — the snapshot and the compiled task — and the decision
    # that follows still carries its own expected heads, so the stale-head and dependency
    # checks stay on the review, where they were.
    @app.post(prefix + '/prepare')
    def prepare(case: str, body: PrepareBody, a=Depends(actor)):
        return repository.prepare_task(a, case, body.audit_cutoff, body.information_cutoff, clock())

    @app.post(prefix + '/compile')
    def compile_task(case: str, body: CompileBody, a=Depends(actor)):
        return repository.compile_task(a, case, body.snapshot_ref, body.assumption_id,
                                       body.information_cutoff, clock(), passage_ids=body.passage_ids)

    @app.post(prefix + '/reviews')
    def review(case: str, body: ReviewBody, request: Request, a=Depends(actor)):
        digest = hashlib.sha256(request.scope['h1.raw_body']).hexdigest()
        key = a.tenant_id, case, a.actor_id, body.idempotency_key
        def replay(s, fresh):
            s._check_case(fresh, case)
            require(fresh.can_review, 'ACCESS_DENIED')
            prior = s._http_receipts.get(key)
            if prior is None:
                return None
            # Recheck transitive source access before exposing even conflict status.
            result = s.receipt(fresh, case, body.idempotency_key)
            require(prior['body_digest'] == digest, 'IDEMPOTENCY_CONFLICT')
            return result
        prior = repository.execute(a, case, replay)
        if prior is not None:
            return prior
        at = clock()
        command = dict(body.model_dump(), case_id=case, reviewed_at=at, recorded_at=at)
        def commit(s, fresh):
            prior = replay(s, fresh)
            if prior is not None:
                return prior
            result = s.commit_review(fresh, command)
            s._http_receipts[key] = {'body_digest': digest, 'request': command}
            return result
        return repository.execute(a, case, commit)

    @app.post(prefix + '/proposals')
    def proposal(case: str, body: ProposalBody, a=Depends(actor)):
        return repository.prepare_scenario(a, case, body.idempotency_key, clock())

    @app.post(prefix + '/export')
    def export(case: str, body: RefBody, a=Depends(actor)):
        return repository.export_scenario(a, case, body.ref)

    return app
