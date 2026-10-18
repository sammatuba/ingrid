"""The desk's Vertex AI client: configuration from the environment, an access token, one bounded call.

Off unless `DESK_GEMINI=1`: demo mode, the tests and any environment without it never touch the
network. The destination is the one the repository's transport fixes (`src/adapters/gemini`): the
Vertex AI global endpoint `/v1/projects/{project}/locations/global/publishers/google/models/
{model}:generateContent`. Each call runs in that package's networking worker (`worker.py`), a
subprocess that derives the host, path and headers from its fixed table and is killed at the
deadline, so a stalled DNS lookup or a trickling response cannot hold a request thread.

Environment:

| Variable | Meaning |
|---|---|
| `DESK_GEMINI` | `1` turns the live path on; anything else (or unset) is off |
| `DESK_GEMINI_PROJECT` | the Google Cloud project; default `GCLOUD_PROJECT`, then `GOOGLE_CLOUD_PROJECT` |
| `DESK_GEMINI_MODEL` | default `gemini-3.8-flash` (the recorded live run's model) |
| `DESK_GEMINI_TOKEN_ENV` | local runs only: the NAME of a variable that holds an access token |

Credentials: on Cloud Run the access token comes from the metadata server and is cached until
shortly before it expires. Locally a token is read only from the variable `DESK_GEMINI_TOKEN_ENV`
names. A token is never logged, never put in a receipt and never returned.
"""
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

PROVIDER = 'Vertex AI'
DEFAULT_MODEL = 'gemini-3.8-flash'
MODEL = re.compile(r'gemini-[A-Za-z0-9._-]{1,60}\Z')
PROJECT = re.compile(r'[a-z][a-z0-9-]{4,62}\Z')
ENV_NAME = re.compile(r'[A-Z][A-Z0-9_]{0,99}\Z')
MAX_RESPONSE_BYTES = 65536
MAX_REQUEST_BYTES = 192 * 1024
METADATA_HOST = 'metadata.google.internal'
METADATA_PATH = '/computeMetadata/v1/instance/service-accounts/default/token'
ROOT = Path(__file__).resolve().parents[2]


class ModelError(Exception):
    """A live call that did not give a usable response; `code` is a fixed word, never a message."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DeskGeminiConfig:
    project: str
    model: str = DEFAULT_MODEL
    token_env: str | None = None

    @property
    def name(self):
        return self.model


def config_from_env(environ=None):
    """The live configuration, or None when the live path is off (or its settings do not parse)."""
    env = os.environ if environ is None else environ
    if (env.get('DESK_GEMINI') or '').strip() != '1':
        return None
    project = ((env.get('DESK_GEMINI_PROJECT') or '').strip() or (env.get('GCLOUD_PROJECT') or '').strip()
               or (env.get('GOOGLE_CLOUD_PROJECT') or '').strip())
    model = (env.get('DESK_GEMINI_MODEL') or '').strip() or DEFAULT_MODEL
    token_env = (env.get('DESK_GEMINI_TOKEN_ENV') or '').strip() or None
    if not PROJECT.fullmatch(project) or not MODEL.fullmatch(model):
        return None
    if token_env is not None and not ENV_NAME.fullmatch(token_env):
        return None
    return DeskGeminiConfig(project, model, token_env)


def _clean_token(value):
    if type(value) is not str or not value or len(value) > 4096 or not value.isascii():
        return None
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        return None
    return value


class EnvToken:
    """A token from the one variable the configuration names (local runs)."""

    def __init__(self, name, environ=None):
        self.name, self.environ = name, environ

    def __call__(self):
        env = os.environ if self.environ is None else self.environ
        token = _clean_token(env.get(self.name, ''))
        if token is None:
            raise ModelError('MODEL_CREDENTIAL_MISSING')
        return token


class MetadataToken:
    """The Cloud Run service account's access token from the metadata server, cached to expiry."""

    def __init__(self, clock=time.monotonic, timeout=2.0):
        self.clock, self.timeout = clock, timeout
        self._lock = threading.Lock()
        self._token, self._until = None, 0.0

    def _fetch(self):
        connection = http.client.HTTPConnection(METADATA_HOST, timeout=self.timeout)
        try:
            connection.request('GET', METADATA_PATH, headers={'Metadata-Flavor': 'Google'})
            response = connection.getresponse()
            raw = response.read(16384)
            if response.status != 200:
                raise ModelError('MODEL_CREDENTIAL_MISSING')
        except (OSError, http.client.HTTPException):
            raise ModelError('MODEL_CREDENTIAL_MISSING') from None
        finally:
            connection.close()
        try:
            payload = json.loads(raw)
            token, expires = _clean_token(payload.get('access_token')), int(payload.get('expires_in', 0))
        except (ValueError, TypeError, AttributeError):
            raise ModelError('MODEL_CREDENTIAL_MISSING') from None
        if token is None or expires <= 0:
            raise ModelError('MODEL_CREDENTIAL_MISSING')
        return token, expires

    def __call__(self):
        with self._lock:
            now = self.clock()
            if self._token is None or now >= self._until:
                token, expires = self._fetch()
                # refreshed a minute early, so a call never starts with a token about to lapse
                self._token, self._until = token, now + max(0, expires - 60)
            return self._token


def token_source(config):
    return EnvToken(config.token_env) if config.token_env else MetadataToken()


def request_digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                          .encode('utf-8')).hexdigest()


class VertexClient:
    """One generateContent call per `__call__`, through the repository's networking worker.

    `__call__(body, timeout)` returns the response dict or raises `ModelError`. One attempt: a
    failed call is not retried here (the caller falls back to the composed answer).
    """

    def __init__(self, config, tokens=None):
        self.config = config
        self.tokens = tokens or token_source(config)

    def __call__(self, body, timeout):
        if not 0 < timeout <= 30:
            raise ModelError('MODEL_TIMEOUT')
        encoded = json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        if len(encoded) > MAX_REQUEST_BYTES:
            raise ModelError('MODEL_INPUT_LIMIT')
        key = self.tokens()
        envelope = json.dumps({'api': 'vertex_ai', 'model': self.config.model, 'api_version': 'v1',
                               'project': self.config.project, 'key': key, 'body': body,
                               'timeout_seconds': timeout, 'max_response_bytes': MAX_RESPONSE_BYTES},
                              separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        started = time.monotonic()
        process = subprocess.Popen([sys.executable, '-m', 'src.adapters.gemini.worker'], cwd=ROOT,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            wire, _ = process.communicate(envelope, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ModelError('MODEL_TIMEOUT') from None
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        if time.monotonic() - started > timeout:
            raise ModelError('MODEL_TIMEOUT')
        if process.returncode != 0 or len(wire) > MAX_RESPONSE_BYTES + 1024:
            raise ModelError('MODEL_UNAVAILABLE')
        try:
            result = json.loads(wire.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise ModelError('MODEL_INVALID_RESPONSE') from None
        if type(result) is dict and set(result) == {'code'} and type(result['code']) is str:
            raise ModelError(result['code'] if re.fullmatch(r'MODEL_[A-Z_]{1,40}', result['code'])
                             else 'MODEL_UNAVAILABLE')
        if type(result) is not dict or set(result) != {'response'} or type(result['response']) is not dict:
            raise ModelError('MODEL_INVALID_RESPONSE')
        return result['response']
