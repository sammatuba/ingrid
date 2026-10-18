"""Opt-in gemini_developer or vertex_ai transport, with persistent attempt and deadline bounds.

The configured API selects one fixed destination. No credential discovery, model default, retry,
SDK or application activation. These are request/token bounds, not a monetary or distributed
billing control.

The configuration also names the case it serves: the fictional case, or one real case from the
explicit allowlist below, bound there to a signed permission record. A real case is refused
before any attempt is reserved unless the caller declares that same case and the record is a
live grant under the checkout's permission directory.
"""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from typing import NamedTuple

from src.contracts.jsonutil import canonical_bytes, parse_json
from src.judgment import JudgmentUnavailable
from src.review.records import PERMISSION_DIR, PERMISSION_IDENTIFIER

HOST = 'generativelanguage.googleapis.com'
VERTEX_HOST = 'aiplatform.googleapis.com'
MAX_REQUEST_BYTES = 192 * 1024
MAX_WIRE_BYTES = MAX_REQUEST_BYTES + 8192
SAFE_CODES = frozenset({'MODEL_UNAVAILABLE', 'MODEL_TIMEOUT', 'MODEL_AUTH_FAILED',
    'MODEL_QUOTA', 'MODEL_INVALID_RESPONSE', 'MODEL_RESPONSE_LIMIT'})

#: The status word a permission record must lead with to be a live grant. The repository
#: registry (`src.review.records.load_permissions`) treats any status but the draft marker as
#: signed; the transport reads the same files strictly, because it authorizes transmission
#: off this machine, so a draft, a withdrawal and a revocation are all no grant. Every
#: identifier this reading returns is one the registry also holds.
GRANT_STATUS = 'signed'

#: The explicit allowlist of real cases: each entry names the one case id an operator
#: configuration may set as `permitted_case`, bound to the one signed permission record that
#: permits transmitting that case's records. The table is code, so it changes only through a
#: reviewed change; a permission is never read from the configuration, the caller, a request
#: or a source record, and no case id outside this table is accepted.
REAL_CASE_ALLOWLIST = {'pedc-u2-2026-09-21': 'perm:wesm-company-copy:2026-10-13'}

#: Replay alerts (approved by the project lead, 2026-10-18): a case id `alert-<24 hex>`, the
#: alert key the replay computes, is bound to the same company-copy permission as the PEDC
#: case. Only the id shape is checked here; the batch (`scripts/grid/explain_alerts.py`) takes
#: its keys from the baked replay alerts. Every other refusal (case mismatch, unsigned or
#: withdrawn permission, budget and attempt limits) still applies.
REAL_CASE_PATTERNS = ((re.compile(r'alert-[0-9a-f]{24}'), 'perm:wesm-company-copy:2026-10-13'),)


def _real_case_permission(value):
    """The permission bound to a real case id, or None when the id is not allowed."""
    if type(value) is not str:
        return None
    if value in REAL_CASE_ALLOWLIST:
        return REAL_CASE_ALLOWLIST[value]
    for pattern, permission in REAL_CASE_PATTERNS:
        if pattern.fullmatch(value):
            return permission
    return None


class ApiRule(NamedTuple):
    """Fixed api version, location and host for one configured API name."""
    api_version: str
    location: str
    host: str


#: The only supported API names. `vertex_ai` is served from the global endpoint only; the
#: regional host answers 404 for the approved model.
API_RULES = {'gemini_developer': ApiRule('v1beta', 'global', HOST),
    'vertex_ai': ApiRule('v1', 'global', VERTEX_HOST)}


def _text(value, limit=200):
    return type(value) is str and 0 < len(value) <= limit and value.strip() == value


def _permitted_case(value):
    """The fictional case id, or one real case id from the explicit allowlist."""
    return value == 'synthetic-case' or _real_case_permission(value) is not None


def _status_token(line):
    """The Status line's leading word, with Markdown emphasis dropped."""
    value = line[len('Status:'):].strip().lstrip('*_` ').strip()
    token = re.match(r'[A-Za-z]+', value)
    return token.group(0).lower() if token else ''


def signed_permissions(root):
    """The identifiers of the permission records that are live grants under the checkout.

    A record grants only when its ``Status:`` line leads with ``signed``: a draft, a
    revocation, any other status word and a file whose identifier does not parse are all no
    grant, so a real case citing one is refused. Reads local files only: no network,
    credential or clock.
    """
    identifiers = set()
    for path in sorted(Path(root).joinpath(*PERMISSION_DIR).glob('*.md')):
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        status, identifier = None, None
        for line in text.splitlines():
            if line.startswith('Status:'):
                status = _status_token(line)
            match = PERMISSION_IDENTIFIER.match(line.strip())
            if match:
                value = match.group(1).strip()
                ticked = re.fullmatch(r'`([^`]+)`', value)
                identifier = ticked.group(1) if ticked else value.strip('*_. ')
        if identifier and status == GRANT_STATUS:
            identifiers.add(identifier)
    return frozenset(identifiers)


@dataclass(frozen=True)
class LiveConfig:
    """Trusted operator configuration; never obtained from a source or browser request.

    `api` is a required key of operator configuration files: `from_dict` accepts exactly the
    declared fields, so a file without it is rejected. The default keeps in-process Developer
    API callers that predate the key working; no operator path can omit it.

    `permitted_case` is the fictional case or one id in `REAL_CASE_ALLOWLIST`. The permission
    record behind an allowlisted case is not a configuration value: the operator cannot supply
    one, and the transport reads the binding from the table.
    """
    project: str
    model: str
    credential_env: str
    authorization_ref: str
    run_id: str
    permitted_case: str
    budget_policy: str
    api_version: str
    location: str
    max_attempts: int
    timeout_seconds: float
    max_request_bytes: int
    max_response_bytes: int
    max_output_tokens: int
    api: str = 'gemini_developer'

    def __post_init__(self):
        rule = API_RULES.get(self.api) if type(self.api) is str else None
        good = (rule is not None and self.api_version == rule.api_version
            and self.location == rule.location
            and _text(self.project) and re.fullmatch(r'[a-z][a-z0-9-]{4,62}', self.project)
            and _text(self.model) and re.fullmatch(r'gemini-[A-Za-z0-9._-]+', self.model)
            and _text(self.credential_env) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,99}', self.credential_env)
            and _text(self.authorization_ref, 500)
            and _text(self.run_id, 80) and re.fullmatch(r'[A-Za-z0-9_-]+', self.run_id)
            and _permitted_case(self.permitted_case)
            and self.budget_policy == 'request_and_token_limits'
            and type(self.max_attempts) is int and 1 <= self.max_attempts <= 10
            and type(self.timeout_seconds) in (int, float) and math.isfinite(self.timeout_seconds)
            and 0 < self.timeout_seconds <= 30
            and type(self.max_request_bytes) is int and 1 <= self.max_request_bytes <= MAX_REQUEST_BYTES
            and type(self.max_response_bytes) is int and 1 <= self.max_response_bytes <= 65536
            and type(self.max_output_tokens) is int and 1 <= self.max_output_tokens <= 2048)
        if not good:
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != set(cls.__dataclass_fields__):
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID') from None

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


class AttemptLedger:
    """Atomic local run allowance. Failed attempts are consumed, including process startup.

    The operator must retain this file for a run. Deleting it or selecting a new run is
    not an automatic recovery path; no protection against the file's administrator is claimed.
    """
    def __init__(self, path, config):
        self.path = Path(path)
        self.config = config
        self.digest = hashlib.sha256(canonical_bytes(config.as_dict())).hexdigest()

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # This file contains configuration digests and counts, never prompts or credentials.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        return sqlite3.connect(self.path, timeout=1)

    def reserve(self):
        try:
            with closing(self._connect()) as db, db:
                db.execute('CREATE TABLE IF NOT EXISTS allowance (id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT NOT NULL, used INTEGER NOT NULL)')
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT digest, used FROM allowance WHERE id=1').fetchone()
                if row is None:
                    db.execute('INSERT INTO allowance VALUES (1, ?, 0)', (self.digest,))
                    used = 0
                else:
                    if row[0] != self.digest:
                        raise JudgmentUnavailable('MODEL_ALLOWANCE_CONFLICT')
                    used = row[1]
                if type(used) is not int or not 0 <= used < self.config.max_attempts:
                    raise JudgmentUnavailable('MODEL_ATTEMPT_LIMIT')
                db.execute('UPDATE allowance SET used=? WHERE id=1', (used + 1,))
                return used + 1
        except (OSError, sqlite3.Error):
            raise JudgmentUnavailable('MODEL_ALLOWANCE_UNAVAILABLE') from None


class GeminiTransport:
    """One-attempt transport for the configured API: the Developer API or Vertex AI.

    The worker subprocess receives the API name and derives host, path and credential headers
    from the fixed table in `worker.py`; nothing about the destination is caller-selectable.

    A configuration naming a real case is refused before any attempt is reserved unless the
    caller declares that same case and the allowlist's permission record is a live grant under
    `permission_root`, which defaults to this checkout.
    """
    def __init__(self, config, ledger_path, *, permission_root=None):
        if not isinstance(config, LiveConfig):
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
        self.config = config
        self.permission_root = (Path(__file__).resolve().parents[3] if permission_root is None
            else Path(permission_root))
        self.ledger = AttemptLedger(ledger_path, config)
        self.last_receipt = None

    def _permission_for(self, case):
        """The permission this call may cite, or a refusal; called before any attempt exists.

        The declared case must be the configured case: a caller that does not declare a real
        case, or declares another, is refused, so content compiled for one case is never
        transmitted under another's permission. A real case then needs its bound record to be
        a live signed grant; an absent, unsigned, withdrawn or revoked record is refused here,
        before the worker starts, a credential is read or an attempt is reserved.
        """
        configured = self.config.permitted_case
        if case is not None and case != configured:
            raise JudgmentUnavailable('MODEL_CASE_MISMATCH')
        if configured == 'synthetic-case':
            return None
        if case != configured:
            raise JudgmentUnavailable('MODEL_CASE_MISMATCH')
        permission = _real_case_permission(configured)
        if permission is None:
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
        if permission not in signed_permissions(self.permission_root):
            raise JudgmentUnavailable('MODEL_PERMISSION_UNAVAILABLE')
        return permission

    def _start_worker(self):
        # Secrets go through stdin, never argv, environment overrides or temporary files.
        return subprocess.Popen([sys.executable, '-m', 'src.adapters.gemini.worker'],
            cwd=Path(__file__).resolve().parents[3], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def __call__(self, model, body, *, case=None, timeout_seconds, max_response_bytes):
        self.last_receipt = None
        c = self.config
        if model != c.model or type(body) is not dict:
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
        permission = self._permission_for(case)
        try:
            generation = body['generationConfig']
            fields = {'candidateCount', 'maxOutputTokens', 'responseFormat'}
            if c.api == 'vertex_ai':
                # Vertex spends hidden thinking tokens unless the budget is pinned to zero.
                fields.add('thinkingConfig')
            if (set(generation) != fields
                    or type(generation['candidateCount']) is not int or generation['candidateCount'] != 1
                    or type(generation['maxOutputTokens']) is not int or generation['maxOutputTokens'] != c.max_output_tokens):
                raise ValueError()
            if c.api == 'vertex_ai':
                thinking = generation['thinkingConfig']
                if (type(thinking) is not dict or set(thinking) != {'thinkingBudget'}
                        or type(thinking['thinkingBudget']) is not int or thinking['thinkingBudget'] != 0):
                    raise ValueError()
            if generation['responseFormat']['text']['mimeType'] != 'APPLICATION_JSON':
                raise ValueError()
            if set(body) != {'systemInstruction', 'contents', 'generationConfig'}:
                raise ValueError()
            request = canonical_bytes(body)
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID') from None
        if len(request) > c.max_request_bytes:
            raise JudgmentUnavailable('MODEL_INPUT_LIMIT')
        # Only tighter limits are accepted from the provider; malformed/relaxed values fail.
        if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 30 or type(max_response_bytes) is not int
                or not 0 < max_response_bytes <= 65536):
            raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
        timeout = min(timeout_seconds, c.timeout_seconds)
        cap = min(max_response_bytes, c.max_response_bytes)
        key = os.environ.get(c.credential_env, '')
        if not key or len(key) > 4096 or not key.isascii() or any(ord(x) < 33 or ord(x) > 126 for x in key):
            raise JudgmentUnavailable('MODEL_CREDENTIAL_MISSING')
        envelope = canonical_bytes({'api': c.api, 'model': model, 'api_version': c.api_version,
            'project': c.project if c.api == 'vertex_ai' else None, 'key': key, 'body': body,
            'timeout_seconds': timeout, 'max_response_bytes': cap})
        if len(envelope) > MAX_WIRE_BYTES:
            raise JudgmentUnavailable('MODEL_INPUT_LIMIT')
        attempt = self.ledger.reserve()
        started = time.monotonic()
        receipt = {'api': c.api, 'api_version': c.api_version, 'configured_project': c.project,
            'location': c.location, 'model': model, 'authorization_ref': c.authorization_ref,
            'permitted_case': c.permitted_case, 'permission_ref': permission,
            'budget_policy': c.budget_policy,
            'run_id': c.run_id, 'attempt': attempt, 'request_bytes': len(request),
            'request_body_digest': hashlib.sha256(request).hexdigest(),
            'limits': {'timeout_seconds': timeout, 'max_response_bytes': cap,
                'max_output_tokens': c.max_output_tokens, 'max_attempts': c.max_attempts},
            'response_id': None, 'usage': None, 'model_version': None, 'status': 'MODEL_UNAVAILABLE'}
        process = None
        try:
            process = self._start_worker()
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise subprocess.TimeoutExpired('gemini-worker', timeout)
            wire, _ = process.communicate(envelope, timeout=remaining)
            if time.monotonic() - started > timeout:
                raise subprocess.TimeoutExpired('gemini-worker', timeout)
            # Worker bounds stdout; allow only its JSON envelope overhead beyond the response.
            if process.returncode != 0 or len(wire) > cap + 1024:
                raise JudgmentUnavailable('MODEL_UNAVAILABLE')
            result, error = parse_json(wire.decode('utf-8'))
            if error or type(result) is not dict:
                raise JudgmentUnavailable('MODEL_INVALID_RESPONSE')
            if set(result) == {'code'} and type(result['code']) is str and result['code'] in SAFE_CODES:
                raise JudgmentUnavailable(result['code'])
            if set(result) != {'response'} or type(result['response']) is not dict:
                raise JudgmentUnavailable('MODEL_INVALID_RESPONSE')
            response = result['response']
            if len(canonical_bytes(response)) > cap:
                raise JudgmentUnavailable('MODEL_RESPONSE_LIMIT')
            receipt['response_id'] = response.get('responseId') if _text(response.get('responseId')) else None
            receipt['model_version'] = response.get('modelVersion') if _text(response.get('modelVersion')) else None
            usage = response.get('usageMetadata')
            if type(usage) is dict:
                names = ('promptTokenCount', 'candidatesTokenCount', 'thoughtsTokenCount', 'totalTokenCount', 'cachedContentTokenCount')
                receipt['usage'] = {k: usage[k] for k in names if type(usage.get(k)) is int and 0 <= usage[k] <= 10**9}
            receipt['status'] = 'response_received'
            return response
        except subprocess.TimeoutExpired:
            receipt['status'] = 'MODEL_TIMEOUT'
            raise JudgmentUnavailable('MODEL_TIMEOUT') from None
        except JudgmentUnavailable as exc:
            receipt['status'] = exc.code
            raise
        except (OSError, UnicodeError, ValueError):
            raise JudgmentUnavailable('MODEL_UNAVAILABLE') from None
        finally:
            if process is not None:
                if process.poll() is None:
                    # Kill the entire networking worker, including DNS/TLS or trickling headers.
                    process.kill()
                process.communicate()
            receipt['elapsed_seconds'] = round(time.monotonic() - started, 6)
            self.last_receipt = receipt


# The class accepted only Developer API configuration before the API key existed; callers
# outside this package still import the old name for a `gemini_developer` config.
DeveloperAPITransport = GeminiTransport
