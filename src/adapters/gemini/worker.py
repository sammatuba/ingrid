"""Internal networking subprocess. Only the parent transport configures and invokes it.

The parent names the configured API; this module derives the host, path and credential
headers from the fixed `API_RULES` table, never from request content.
"""
import http.client
import re
import socket
import ssl
import sys

from src.contracts.jsonutil import canonical_bytes, parse_json
from .transport import API_RULES, MAX_WIRE_BYTES

# The fixed developer host stays addressable as `worker.HOST`; local TLS fixtures assert that
# the connection is opened against it rather than against fixture input.
HOST = API_RULES['gemini_developer'].host
MODEL = re.compile(r'gemini-[A-Za-z0-9._-]+')
PROJECT = re.compile(r'[a-z][a-z0-9-]{4,62}')


def _destination(api, version, model, project, key):
    """Return (host, path, credential headers) for one configured API, or None."""
    rule = API_RULES.get(api) if type(api) is str else None
    if rule is None or version != rule.api_version or not MODEL.fullmatch(model):
        return None
    if api == 'gemini_developer':
        # The configured project label is operator configuration for the Developer API; the
        # API key determines the actual project, so nothing project-shaped is transmitted.
        if project is not None:
            return None
        return rule.host, f'/{rule.api_version}/models/{model}:generateContent', {'x-goog-api-key': key}
    if type(project) is not str or not PROJECT.fullmatch(project):
        return None
    path = (f'/{rule.api_version}/projects/{project}/locations/{rule.location}'
        f'/publishers/google/models/{model}:generateContent')
    return rule.host, path, {'Authorization': f'Bearer {key}', 'x-goog-user-project': project}


def request(envelope):
    model, key = envelope['model'], envelope['key']
    if (type(model) is not str or type(key) is not str or not key or len(key) > 4096
            or not key.isascii() or any(ord(x) < 33 or ord(x) > 126 for x in key)):
        return {'code': 'MODEL_UNAVAILABLE'}
    destination = _destination(envelope['api'], envelope['api_version'], model,
        envelope['project'], key)
    timeout, cap = envelope['timeout_seconds'], envelope['max_response_bytes']
    if (destination is None or type(timeout) not in (int, float) or not 0 < timeout <= 30
            or type(cap) is not int or not 0 < cap <= 65536):
        return {'code': 'MODEL_UNAVAILABLE'}
    host, path, credential = destination
    connection = http.client.HTTPSConnection(host, timeout=timeout, context=ssl.create_default_context())
    try:
        connection.request('POST', path, body=canonical_bytes(envelope['body']),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                'Accept-Encoding': 'identity', **credential})
        response = connection.getresponse()
        if response.status != 200:
            return {'code': {401: 'MODEL_AUTH_FAILED', 403: 'MODEL_AUTH_FAILED', 429: 'MODEL_QUOTA'}.get(response.status, 'MODEL_UNAVAILABLE')}
        if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
            return {'code': 'MODEL_INVALID_RESPONSE'}
        if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return {'code': 'MODEL_INVALID_RESPONSE'}
        length = response.getheader('Content-Length')
        if length is not None:
            if not length.isascii() or not length.isdecimal():
                return {'code': 'MODEL_INVALID_RESPONSE'}
            if int(length) > cap:
                return {'code': 'MODEL_RESPONSE_LIMIT'}
        try:
            raw = response.read(cap + 1)
        except http.client.IncompleteRead:
            return {'code': 'MODEL_INVALID_RESPONSE'}
        if len(raw) > cap:
            return {'code': 'MODEL_RESPONSE_LIMIT'}
        if length is not None and len(raw) != int(length):
            return {'code': 'MODEL_INVALID_RESPONSE'}
        value, error = parse_json(raw.decode('utf-8'))
        if error or type(value) is not dict:
            return {'code': 'MODEL_INVALID_RESPONSE'}
        return {'response': value}
    finally:
        connection.close()


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_WIRE_BYTES + 1)
        if len(raw) > MAX_WIRE_BYTES:
            raise ValueError()
        envelope, error = parse_json(raw.decode('utf-8'))
        keys = {'api', 'model', 'api_version', 'project', 'key', 'body', 'timeout_seconds', 'max_response_bytes'}
        if error or type(envelope) is not dict or set(envelope) != keys:
            raise ValueError()
        result = request(envelope)
    except (TimeoutError, socket.timeout):
        result = {'code': 'MODEL_TIMEOUT'}
    except Exception:
        # Never print exception text, request content, error bodies or credential details.
        result = {'code': 'MODEL_UNAVAILABLE'}
    sys.stdout.buffer.write(canonical_bytes(result))


if __name__ == '__main__':
    main()
