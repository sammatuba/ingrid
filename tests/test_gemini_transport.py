"""Hermetic transport and fictional run tests. No Google requests or real credentials."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from src.adapters.gemini import GeminiProvider
from src.adapters.gemini.run import prepare_bundle, read_private_json, run_case, write_private_json
from src.adapters.gemini.transport import (AttemptLedger, DeveloperAPITransport, GeminiTransport,
    HOST, LiveConfig, VERTEX_HOST)
from src.adapters.gemini.worker import request as worker_request
from src.judgment import JudgmentUnavailable

NOW = '2026-10-06T01:00:00Z'
KEY = 'labeled-test-key-never-real'
TOKEN = 'ya29.synthetic-adc-token-never-real'
PROJECT = 'synthetic-project'


def config(**changes):
    values = dict(project=PROJECT, model='gemini-fixture', credential_env='M3_TEST_KEY',
        authorization_ref='synthetic-test-authorization', run_id='fixture-run', api_version='v1beta',
        permitted_case='synthetic-case', budget_policy='request_and_token_limits',
        location='global', max_attempts=1, timeout_seconds=3, max_request_bytes=192*1024,
        max_response_bytes=65536, max_output_tokens=2048, api='gemini_developer')
    if changes.get('api') == 'vertex_ai':
        values.update(api_version='v1', credential_env='M3_TEST_TOKEN')
    values.update(changes)
    return LiveConfig(**values)


def body():
    return {'systemInstruction': {'parts': [{'text': 'test'}]},
        'contents': [{'role': 'user', 'parts': [{'text': 'test'}]}],
        'generationConfig': {'candidateCount': 1, 'maxOutputTokens': 2048,
            'responseFormat': {'text': {'mimeType': 'APPLICATION_JSON'}}}}


def vertex_body():
    value = body()
    value['generationConfig']['thinkingConfig'] = {'thinkingBudget': 0}
    return value


def envelope(**changes):
    value = dict(api='gemini_developer', model='gemini-fixture', api_version='v1beta', project=None,
        key=KEY, body=body(), timeout_seconds=3, max_response_bytes=65536)
    value.update(changes)
    return value


def vertex_envelope(**changes):
    value = envelope(api='vertex_ai', api_version='v1', project=PROJECT, key=TOKEN, body=vertex_body())
    value.update(changes)
    return value


FIXTURE_WORKER = '''
import json, sys
e = json.load(sys.stdin)
prompt = json.loads(e['body']['contents'][0]['parts'][0]['text'])
answer = {'label':'challenges','explanation':'Testing does not confirm commercial availability.',
    'citations':[{'passage_index':0,'quote':prompt['context'][0]['quote']}],
    'alternatives':['Availability may be confirmed later.'], 'unknowns':['Commercial availability is unconfirmed.']}
response = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(answer),
    'thoughtSignature':'opaque-synthetic-signature'}]}}], 'modelVersion':'synthetic-contract.v1',
    'responseId':'synthetic-response', 'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':50,
    'thoughtsTokenCount':10,'totalTokenCount':160, 'untrusted_field':'ignored'}}
print(json.dumps({'response':response}))
'''


class FixtureTransport(DeveloperAPITransport):
    program = FIXTURE_WORKER

    def _start_worker(self):
        self.process = subprocess.Popen([sys.executable, '-c', self.program],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return self.process


# Shape-only fixture for the Vertex fields the local probe recorded (createTime,
# usageMetadata.trafficType and promptTokensDetails). Synthetic text and numbers: this is
# not a Gemini run and not provider evidence.
VERTEX_FIXTURE_WORKER = '''
import json, sys
envelope = json.load(sys.stdin)
assert envelope['api'] == 'vertex_ai' and envelope['api_version'] == 'v1'
assert envelope['project'] == 'synthetic-project'
generation = envelope['body']['generationConfig']
assert generation['thinkingConfig'] == {'thinkingBudget': 0}
assert generation['responseFormat']['text']['mimeType'] == 'APPLICATION_JSON'
prompt = json.loads(envelope['body']['contents'][0]['parts'][0]['text'])
answer = {'label':'challenges','explanation':'Testing does not confirm commercial availability.',
    'citations':[{'passage_index':0,'quote':prompt['context'][0]['quote']}],
    'alternatives':['Availability may be confirmed later.'], 'unknowns':['Commercial availability is unconfirmed.']}
response = {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(answer),
    'thoughtSignature':'opaque-synthetic-signature'}]}}], 'createTime':'2026-10-11T00:00:00Z',
    'modelVersion':'synthetic-vertex-shape.v1', 'responseId':'synthetic-vertex-response',
    'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':50,'thoughtsTokenCount':88,
    'totalTokenCount':238,'trafficType':'ON_DEMAND','promptTokensDetails':[{'modality':'TEXT','tokenCount':100}]}}
print(json.dumps({'response':response}))
'''


class VertexFixtureTransport(FixtureTransport):
    program = VERTEX_FIXTURE_WORKER


# For body-shape checks only: the parent validates before any worker runs.
ECHO_WORKER = "import json;print(json.dumps({'response':{'modelVersion':'synthetic-body-check.v1'}}))"


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'M3_TEST_KEY': KEY, 'M3_TEST_TOKEN': TOKEN})
        self.env.start()
        self.addCleanup(self.env.stop)

    def transport(self, program, **changes):
        transport = FixtureTransport(config(**changes), self.root/'attempts.sqlite3')
        transport.program = program
        return transport

    def invoke(self, transport, request=None):
        return transport('gemini-fixture', request or body(), timeout_seconds=30, max_response_bytes=65536)

    def test_explicit_config_rejects_missing_extra_and_unsafe_fields(self):
        value = config().as_dict()
        self.assertEqual(config(), LiveConfig.from_dict(value))
        for malformed in (None, dict(value, key=KEY), {k:v for k,v in value.items() if k!='authorization_ref'}):
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                LiveConfig.from_dict(malformed)
        for field, values in {'model':['../escape','gemini-fixture?key=secret',True],
            'project':['', '../project'], 'credential_env':['KEY\r\nHost:evil',''],
            'authorization_ref':[''], 'run_id':['../other'], 'api_version':['v1','unknown'],
            'permitted_case':['private-case'], 'budget_policy':['monetary_cap',''],
            'location':['us-central1','asia-southeast1'], 'max_attempts':[True,0,11],
            'timeout_seconds':[True,0,31,float('nan')], 'max_request_bytes':[True,0,192*1024+1],
            'max_response_bytes':[True,0,65537], 'max_output_tokens':[True,0,2049],
            'api':['vertex','vertex-ai','']}.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(JudgmentUnavailable):
                    config(**{field:value})

    def test_api_selects_one_fixed_destination_and_missing_api_is_rejected(self):
        developer, vertex = config(), config(api='vertex_ai')
        self.assertEqual(developer, LiveConfig.from_dict(developer.as_dict()))
        self.assertEqual(vertex, LiveConfig.from_dict(vertex.as_dict()))
        self.assertEqual('gemini_developer', developer.api)
        self.assertEqual('vertex_ai', vertex.api)
        for missing in ('api', 'api_version', 'location'):
            value = vertex.as_dict()
            del value[missing]
            with self.subTest(missing=missing), self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                LiveConfig.from_dict(value)
        for changes in ({'api':'vertex-ai'}, {'api':True}, {'api':None},
                {'api':'vertex_ai','api_version':'v1beta'},
                {'api':'vertex_ai','location':'asia-southeast1'},
                {'api':'vertex_ai','location':'us-central1'},
                {'api':'gemini_developer','api_version':'v1'},
                {'api':'gemini_developer','location':'asia-southeast1'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                config(**changes)
        self.assertIs(GeminiTransport, DeveloperAPITransport)

    def test_vertex_body_requires_thinking_budget_zero_and_application_json(self):
        transport = self.transport(ECHO_WORKER, api='vertex_ai')
        self.invoke(transport, vertex_body())
        self.assertEqual('response_received', transport.last_receipt['status'])
        self.assertEqual('vertex_ai', transport.last_receipt['api'])
        invalid = [body()]
        for thinking in ({'thinkingBudget':1}, {'thinkingBudget':0.0}, {'thinkingBudget':True},
                {'thinkingBudget':0,'extra':0}, [], None):
            value = vertex_body()
            value['generationConfig']['thinkingConfig'] = thinking
            invalid.append(value)
        mislabelled = vertex_body()
        mislabelled['generationConfig']['responseFormat']['text']['mimeType'] = 'application/json'
        invalid.append(mislabelled)
        for request in invalid:
            with self.subTest(thinking=request['generationConfig'].get('thinkingConfig', 'absent')):
                with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                    self.invoke(transport, request)

    def test_body_api_mismatch_is_rejected_for_both_apis_before_any_attempt(self):
        developer = self.transport(ECHO_WORKER)
        vertex = self.transport(ECHO_WORKER, api='vertex_ai')
        for transport, request in ((developer, vertex_body()), (vertex, body())):
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                self.invoke(transport, request)
            self.assertIsNone(transport.last_receipt)
        self.assertFalse((self.root/'attempts.sqlite3').exists())

    def test_input_and_credential_failure_do_not_consume_attempt_or_spawn(self):
        transport = DeveloperAPITransport(config(max_request_bytes=100), self.root/'allowance')
        with patch.object(transport, '_start_worker') as start:
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_INPUT_LIMIT$'):
                self.invoke(transport)
            start.assert_not_called()
        self.assertFalse((self.root/'allowance').exists())
        transport = DeveloperAPITransport(config(), self.root/'allowance')
        for key in ('', 'secret\r\nHost:evil', 'é'):
            with patch.dict(os.environ, {'M3_TEST_KEY':key}), self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CREDENTIAL_MISSING$'):
                self.invoke(transport)
        self.assertFalse((self.root/'allowance').exists())

    def test_vertex_missing_credential_is_refused_before_reservation(self):
        # Corrected intent, 2026-10-11 (review finding 1): like the Developer path, a missing
        # Vertex token refuses as MODEL_CREDENTIAL_MISSING before any attempt is reserved —
        # no worker, no ledger entry, no receipt — and leaves the allowance usable.
        transport = GeminiTransport(config(api='vertex_ai'), self.root/'vertex-allowance')
        with patch.object(transport, '_start_worker') as start:
            for key in ('', 'token\r\nHost:evil', 'é'):
                with self.subTest(key=key), patch.dict(os.environ, {'M3_TEST_TOKEN':key}):
                    with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CREDENTIAL_MISSING$'):
                        self.invoke(transport, vertex_body())
            start.assert_not_called()
        self.assertIsNone(transport.last_receipt)
        self.assertFalse((self.root/'vertex-allowance').exists())
        # Same ledger path: had the refused calls consumed anything, this would be
        # MODEL_ATTEMPT_LIMIT instead of attempt 1 of 1.
        working = FixtureTransport(config(api='vertex_ai'), self.root/'vertex-allowance')
        working.program = ECHO_WORKER
        self.invoke(working, vertex_body())
        self.assertEqual('vertex_ai', working.last_receipt['api'])
        self.assertEqual(1, working.last_receipt['attempt'])

    def test_worker_deadline_stops_hang_and_partial_output(self):
        for i, program in enumerate(("import time; time.sleep(10)", "import sys,time;sys.stdout.write('{');sys.stdout.flush();time.sleep(10)")):
            transport = FixtureTransport(config(timeout_seconds=.2), self.root/f'allowance-{i}')
            transport.program = program
            at = time.monotonic()
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_TIMEOUT$'):
                self.invoke(transport)
            self.assertLess(time.monotonic()-at, 2)
            self.assertIsNotNone(transport.process.poll())
            self.assertEqual('MODEL_TIMEOUT', transport.last_receipt['status'])
            reopened = DeveloperAPITransport(config(timeout_seconds=.2), self.root/f'allowance-{i}')
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ATTEMPT_LIMIT$'):
                self.invoke(reopened)

    def test_process_failure_discards_stderr_and_consumes_attempt(self):
        transport = self.transport(f"import sys;sys.stderr.write({KEY!r});sys.exit(1)")
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_UNAVAILABLE$'):
            self.invoke(transport)
        self.assertNotIn(KEY, json.dumps(transport.last_receipt))
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ATTEMPT_LIMIT$'):
            self.invoke(transport)

    def test_spawn_failure_is_consumed_and_has_safe_receipt(self):
        transport = DeveloperAPITransport(config(), self.root/'allowance')
        with patch.object(transport, '_start_worker', side_effect=OSError(KEY)):
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_UNAVAILABLE$'):
                self.invoke(transport)
        self.assertEqual(1, transport.last_receipt['attempt'])
        self.assertNotIn(KEY, json.dumps(transport.last_receipt))
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ATTEMPT_LIMIT$'):
            self.invoke(transport)

    def test_ledger_restart_concurrent_reservation_and_config_change(self):
        cfg = config()
        path = self.root/'concurrent.sqlite3'
        def reserve(_):
            try:
                return AttemptLedger(path, cfg).reserve()
            except JudgmentUnavailable as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(reserve, range(6)))
        self.assertEqual(1, results.count(1))
        self.assertEqual(5, results.count('MODEL_ATTEMPT_LIMIT'))
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ALLOWANCE_CONFLICT$'):
            AttemptLedger(path, replace(cfg, max_attempts=2)).reserve()
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ALLOWANCE_CONFLICT$'):
            AttemptLedger(path, replace(cfg, api='vertex_ai', api_version='v1')).reserve()
        self.assertNotIn(KEY.encode(), path.read_bytes())
        if os.name == 'posix':
            self.assertEqual(0o600, path.stat().st_mode & 0o777)

    def test_invalid_worker_output_and_safe_codes(self):
        for i, output in enumerate(('not json', '{"response":{},"response":{}}',
                '{"code":"private-code"}', '{"code":[]}', '{"response":[],"extra":"authority"}',
                '{"code":"MODEL_QUOTA"}')):
            transport = FixtureTransport(config(), self.root/f'allowance-{i}')
            transport.program = f'import sys;sys.stdout.write({output!r})'
            with self.assertRaises(JudgmentUnavailable) as caught:
                self.invoke(transport)
            self.assertIn(caught.exception.code, ('MODEL_INVALID_RESPONSE', 'MODEL_QUOTA'))

    def test_response_cap_and_untrusted_usage_metadata(self):
        transport = self.transport("import json;print(json.dumps({'response':{'text':'x'*500}}))", max_response_bytes=200)
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_RESPONSE_LIMIT$'):
            self.invoke(transport)
        path = self.root/'clean'
        transport = FixtureTransport(config(), path)
        transport.program = "import json;print(json.dumps({'response':{'modelVersion':'fixture','responseId':'fixture-id','usageMetadata':{'promptTokenCount':True,'totalTokenCount':-1,'thoughtsTokenCount':3,'private': 'ignored'}}}))"
        self.invoke(transport)
        self.assertEqual({'thoughtsTokenCount':3}, transport.last_receipt['usage'])
        self.assertEqual('fixture-id', transport.last_receipt['response_id'])

    def test_transport_rejects_model_override_tools_and_bad_limits(self):
        transport = DeveloperAPITransport(config(), self.root/'allowance')
        with self.assertRaises(JudgmentUnavailable):
            transport('gemini-other', body(), timeout_seconds=30, max_response_bytes=65536)
        with self.assertRaises(JudgmentUnavailable):
            self.invoke(transport, dict(body(), tools=[{'functionDeclarations':[]}]))
        for timeout, cap in ((True,65536),(float('inf'),65536),(31,65536),(30,True),(30,65537)):
            with self.assertRaises(JudgmentUnavailable):
                transport('gemini-fixture', body(), timeout_seconds=timeout, max_response_bytes=cap)
        for field, value in (('candidateCount',True),('maxOutputTokens',2049)):
            invalid = body(); invalid['generationConfig'][field] = value
            with self.assertRaises(JudgmentUnavailable):
                self.invoke(transport, invalid)
        self.assertFalse((self.root/'allowance').exists())


class WorkerTests(unittest.TestCase):
    def response(self, raw, *, headers=None, status=200):
        response = Mock(status=status)
        headers = headers or {'Content-Type':'application/json; charset=UTF-8'}
        response.getheader.side_effect = lambda k, default=None: headers.get(k, default)
        response.read.return_value = raw
        return response

    def call(self, response, request=None, **changes):
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('src.adapters.gemini.worker.http.client.HTTPSConnection', return_value=connection) as https:
            result = worker_request(envelope(**changes) if request is None else request)
        return result, connection, https

    def test_fixed_tls_destination_header_credential_and_bounded_read(self):
        result, connection, https = self.call(self.response(b'{"modelVersion":"fixture"}'))
        self.assertEqual({'response':{'modelVersion':'fixture'}}, result)
        self.assertEqual(HOST, https.call_args.args[0])
        self.assertEqual('generativelanguage.googleapis.com', HOST)
        self.assertIsNotNone(https.call_args.kwargs['context'])
        args, kwargs = connection.request.call_args
        self.assertEqual(('POST','/v1beta/models/gemini-fixture:generateContent'), args)
        self.assertNotIn(KEY, args[1])
        self.assertEqual(KEY, kwargs['headers']['x-goog-api-key'])
        self.assertNotIn('Authorization', kwargs['headers'])
        self.assertNotIn('x-goog-user-project', kwargs['headers'])
        connection.getresponse.return_value.read.assert_called_once_with(65537)
        connection.close.assert_called_once()

    def test_vertex_destination_is_the_global_publisher_path_with_bearer_and_project(self):
        result, connection, https = self.call(self.response(b'{"modelVersion":"fixture"}'), vertex_envelope())
        self.assertEqual({'response':{'modelVersion':'fixture'}}, result)
        self.assertEqual('aiplatform.googleapis.com', VERTEX_HOST)
        self.assertEqual(VERTEX_HOST, https.call_args.args[0])
        args, kwargs = connection.request.call_args
        self.assertEqual(('POST', '/v1/projects/synthetic-project/locations/global/publishers/google/models/gemini-fixture:generateContent'), args)
        self.assertEqual({'Content-Type':'application/json', 'Accept':'application/json',
            'Accept-Encoding':'identity', 'Authorization':'Bearer '+TOKEN,
            'x-goog-user-project':PROJECT}, kwargs['headers'])
        self.assertNotIn(TOKEN, args[1])
        connection.close.assert_called_once()

    def test_vertex_worker_rejects_version_project_and_api_injection_before_connecting(self):
        cases = [vertex_envelope(api_version='v1beta'), vertex_envelope(project='synthetic-project/evil'),
            vertex_envelope(project='Synthetic-Project'), vertex_envelope(project='a'),
            vertex_envelope(project='synthetic-project\r\nHost: evil'), vertex_envelope(project=True),
            vertex_envelope(api='vertex'),
            vertex_envelope(api='gemini_developer'), vertex_envelope(model='gemini-fixture/other'),
            envelope(project=PROJECT)]
        with patch('src.adapters.gemini.worker.http.client.HTTPSConnection') as https:
            for request in cases:
                with self.subTest(request=request['project'], api=request['api']):
                    self.assertEqual({'code':'MODEL_UNAVAILABLE'}, worker_request(request))
            https.assert_not_called()

    def test_redirect_auth_quota_and_error_payloads_never_read_or_retry(self):
        for status, code in ((301,'MODEL_UNAVAILABLE'),(307,'MODEL_UNAVAILABLE'),
                (401,'MODEL_AUTH_FAILED'),(403,'MODEL_AUTH_FAILED'),(429,'MODEL_QUOTA'),(500,'MODEL_UNAVAILABLE')):
            response = self.response(KEY.encode(), status=status)
            result, connection, _ = self.call(response)
            self.assertEqual({'code':code}, result)
            response.read.assert_not_called()
            connection.request.assert_called_once()
            connection.close.assert_called_once()

    def test_missing_misleading_length_encoding_content_type_and_json(self):
        cases = [
            (b'{}',{'Content-Type':'application/json','Content-Length':'65537'},'MODEL_RESPONSE_LIMIT'),
            (b'{}',{'Content-Type':'application/json','Content-Length':'-1'},'MODEL_INVALID_RESPONSE'),
            (b'{}',{'Content-Type':'application/json','Content-Length':'4'},'MODEL_INVALID_RESPONSE'),
            (b'x'*101,{'Content-Type':'application/json'},'MODEL_RESPONSE_LIMIT'),
            (b'{}',{'Content-Type':'application/json','Content-Encoding':'gzip'},'MODEL_INVALID_RESPONSE'),
            (b'{}',{'Content-Type':'text/html'},'MODEL_INVALID_RESPONSE'),
            (b'{"x":1,"x":2}',{'Content-Type':'application/json'},'MODEL_INVALID_RESPONSE'),
            (b'{"x":NaN}',{'Content-Type':'application/json'},'MODEL_INVALID_RESPONSE'),
            (b'[]',{'Content-Type':'application/json'},'MODEL_INVALID_RESPONSE')]
        for raw, headers, code in cases:
            with self.subTest(headers=headers, raw=raw[:20]):
                result, _, _ = self.call(self.response(raw, headers=headers), max_response_bytes=100)
                self.assertEqual({'code':code}, result)

    def test_worker_rejects_endpoint_and_header_injection_before_connection(self):
        with patch('src.adapters.gemini.worker.http.client.HTTPSConnection') as https:
            for values in ({'model':'gemini-fixture/other'}, {'key':'key\r\nHost:evil'},
                    {'api_version':'../evil'}, {'max_response_bytes':True}):
                self.assertEqual({'code':'MODEL_UNAVAILABLE'}, worker_request(envelope(**values)))
            https.assert_not_called()

    def test_real_worker_invalid_input_exits_safely_without_network(self):
        result = subprocess.run([sys.executable,'-m','src.adapters.gemini.worker'],
            input=b'{"key":"private","body":{}}', capture_output=True, timeout=3)
        self.assertEqual(0, result.returncode)
        self.assertEqual({'code':'MODEL_UNAVAILABLE'}, json.loads(result.stdout))
        self.assertEqual(b'', result.stderr)

    def test_real_vertex_worker_sends_bearer_token_and_never_echoes_it(self):
        # The stub connection reports derived facts only, so the token cannot appear in stdout.
        program = '''
import json, sys
from types import SimpleNamespace
from src.adapters.gemini import worker
seen = {}
class Connection:
    def __init__(self, host, **kwargs): seen['host'] = host
    def request(self, method, path, body=None, headers=None): seen['path'], seen['headers'] = path, headers
    def getresponse(self):
        class Response:
            status = 200
            def getheader(self, key, default=None): return {'Content-Type':'application/json'}.get(key, default)
            def read(self, size): return b'{"modelVersion":"synthetic-stub.v1"}'
        return Response()
    def close(self): pass
worker.http = SimpleNamespace(client=SimpleNamespace(HTTPSConnection=Connection,
    IncompleteRead=worker.http.client.IncompleteRead))
envelope = json.load(sys.stdin)
result = worker.request(envelope)
headers = seen['headers']
print(json.dumps({'result': result, 'host': seen['host'], 'path': seen['path'],
    'scheme': headers['Authorization'].split(' ', 1)[0],
    'credential_length': len(headers['Authorization']) - len('Bearer '),
    'credential_matches': headers['Authorization'] == 'Bearer ' + envelope['key'],
    'user_project': headers['x-goog-user-project'],
    'api_key_header_absent': 'x-goog-api-key' not in headers}))
'''
        result = subprocess.run([sys.executable, '-c', program],
            input=json.dumps(vertex_envelope()).encode('utf-8'), capture_output=True, timeout=5,
            cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b'', result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual({'response':{'modelVersion':'synthetic-stub.v1'}}, report['result'])
        self.assertEqual(VERTEX_HOST, report['host'])
        self.assertEqual('/v1/projects/synthetic-project/locations/global/publishers/google/models/gemini-fixture:generateContent', report['path'])
        self.assertEqual('Bearer', report['scheme'])
        self.assertEqual(len(TOKEN), report['credential_length'])
        self.assertTrue(report['credential_matches'])
        self.assertEqual(PROJECT, report['user_project'])
        self.assertTrue(report['api_key_header_absent'])
        self.assertNotIn(TOKEN, result.stdout.decode('utf-8'))
        self.assertNotIn(TOKEN.encode(), result.stdout)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'M3_TEST_KEY':KEY, 'M3_TEST_TOKEN':TOKEN})
        self.env.start(); self.addCleanup(self.env.stop)

    def run_fixture(self, **kwargs):
        return run_case(config(), self.root, transport_factory=FixtureTransport,
            execution_mode='synthetic_fixture', clock=lambda:NOW, **kwargs)

    def run_vertex(self, run_id='vertex-fixture-run', **kwargs):
        return run_case(config(api='vertex_ai', run_id=run_id), self.root,
            transport_factory=VertexFixtureTransport, execution_mode='synthetic_fixture',
            clock=lambda:NOW, **kwargs)

    def test_prepare_performs_no_inference_and_preserves_context(self):
        with patch('src.adapters.gemini.transport.subprocess.Popen', side_effect=AssertionError('network')):
            bundle = prepare_bundle(lambda:NOW)
        self.assertFalse(bundle['inference_performed'])
        self.assertEqual('offline_preparation',bundle['mode'])
        self.assertIn('commercial availability is unconfirmed',bundle['task']['payload']['context'][0]['quote'])

    def test_case_run_receipt_citations_and_successful_restart_without_inference(self):
        result = self.run_fixture()
        self.assertEqual('synthetic_fixture',result['execution_mode'])
        self.assertEqual('proposed',result['judgment']['payload']['review_state'])
        self.assertEqual('synthetic-response',result['transport']['response_id'])
        self.assertEqual(160,result['transport']['usage']['totalTokenCount'])
        self.assertEqual('pending_human_review',result['semantic_review']['status'])
        self.assertNotIn(KEY,json.dumps(result))
        with patch.dict(os.environ, {'M3_TEST_KEY':''}), patch.object(FixtureTransport,'_start_worker',side_effect=AssertionError('repeat')):
            self.assertEqual(result,self.run_fixture())
        if os.name == 'posix':
            self.assertEqual(0o600,(self.root/'fixture-run/result.json').stat().st_mode & 0o777)

    def test_run_failure_retains_attempt_and_safe_failure_receipt(self):
        class Failed(FixtureTransport):
            program = "import json;print(json.dumps({'code':'MODEL_QUOTA'}))"
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_QUOTA$'):
            run_case(config(),self.root,transport_factory=Failed,execution_mode='synthetic_fixture',clock=lambda:NOW)
        failure = read_private_json(self.root/'fixture-run/failure.json')
        self.assertEqual('MODEL_QUOTA',failure['status'])
        self.assertEqual(1,failure['transport']['attempt'])
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_ATTEMPT_LIMIT$'):
            self.run_fixture()
        self.assertEqual(failure,read_private_json(self.root/'fixture-run/failure.json'))
        self.assertFalse((self.root/'fixture-run/result.json').exists())

    def test_restart_rejects_changed_config_and_tampered_artifact(self):
        result = self.run_fixture()
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_ALLOWANCE_CONFLICT$'):
            run_case(replace(config(),max_output_tokens=1024),self.root,execution_mode='synthetic_fixture')
        result['judgment']['payload']['answer']['explanation']='tampered'
        write_private_json(self.root/'fixture-run/result.json',result)
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_RECEIPT_INVALID$'):
            self.run_fixture()

    def test_restart_rejects_tampered_source_bundle(self):
        result = self.run_fixture()
        result['source']['payload']['original_text'] = 'tampered evidence'
        write_private_json(self.root/'fixture-run/result.json',result)
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_RECEIPT_INVALID$'):
            self.run_fixture()

    def test_restart_rejects_tampered_transport_receipt(self):
        result = self.run_fixture()
        result['transport']['response_id'] = 'different response'
        write_private_json(self.root/'fixture-run/result.json',result)
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_RECEIPT_INVALID$'):
            self.run_fixture()

    def test_provider_rejects_authority_metadata_and_accepts_opaque_signature(self):
        response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}','thoughtSignature':'opaque'}]}}],'modelVersion':'fixture'}
        adapter=GeminiProvider('gemini-fixture',Mock(return_value=response),execution_mode='synthetic_fixture',max_output_tokens=1024)
        self.assertEqual('{}',adapter.generate('fixture')['text'])
        self.assertEqual(1024,adapter.transport.call_args.args[1]['generationConfig']['maxOutputTokens'])
        for extra in ({'approval':True},{'thought':True},{'functionCall':{}},{'thoughtSignature':True}):
            response['candidates'][0]['content']['parts']=[dict(text='{}',**extra)]
            with self.assertRaises(JudgmentUnavailable):adapter.generate('fixture')

    def test_provider_generation_config_follows_the_configured_api(self):
        response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}'}]}}],'modelVersion':'fixture'}
        developer=GeminiProvider('gemini-fixture',Mock(return_value=response),execution_mode='synthetic_fixture')
        vertex=GeminiProvider('gemini-fixture',Mock(return_value=response),execution_mode='synthetic_fixture',api='vertex_ai')
        with self.assertRaises(ValueError):
            GeminiProvider('gemini-fixture',Mock(),execution_mode='synthetic_fixture',api='vertex')
        developer.generate('fixture'); vertex.generate('fixture')
        for adapter, expected in ((developer, None), (vertex, {'thinkingBudget':0})):
            generation=adapter.transport.call_args.args[1]['generationConfig']
            self.assertEqual('APPLICATION_JSON',generation['responseFormat']['text']['mimeType'])
            self.assertEqual(expected,generation.get('thinkingConfig'))

    def test_vertex_recorded_shape_response_yields_verified_judgment_and_receipt(self):
        result = self.run_vertex()
        self.assertEqual('synthetic_fixture', result['execution_mode'])
        self.assertEqual('proposed', result['judgment']['payload']['review_state'])
        self.assertEqual('synthetic_fixture', result['judgment']['payload']['metadata']['execution_mode'])
        self.assertEqual('gemini-fixture', result['judgment']['payload']['metadata']['model'])
        self.assertEqual(result['task']['payload']['context'][0]['quote'],
            result['judgment']['payload']['answer']['citations'][0]['quote'])
        self.assertEqual('vertex_ai', result['transport']['api'])
        self.assertEqual('synthetic-vertex-response', result['transport']['response_id'])
        self.assertEqual('synthetic-vertex-shape.v1', result['transport']['model_version'])
        self.assertEqual(88, result['transport']['usage']['thoughtsTokenCount'])
        self.assertEqual(238, result['transport']['usage']['totalTokenCount'])
        self.assertEqual('pending_human_review', result['semantic_review']['status'])
        self.assertNotIn(TOKEN, json.dumps(result))
        with patch.dict(os.environ, {'M3_TEST_TOKEN':''}), patch.object(VertexFixtureTransport,'_start_worker',side_effect=AssertionError('repeat')):
            self.assertEqual(result, self.run_vertex())

    def test_synthetic_vertex_token_never_reaches_receipt_failure_file_or_stdout(self):
        class Leaky(VertexFixtureTransport):
            program = f"import sys;sys.stderr.write({TOKEN!r});sys.exit(1)"
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_UNAVAILABLE$'):
            run_case(config(api='vertex_ai', run_id='vertex-leak'), self.root, transport_factory=Leaky,
                execution_mode='synthetic_fixture', clock=lambda:NOW)
        failure = self.root/'vertex-leak/failure.json'
        self.assertEqual('MODEL_UNAVAILABLE', read_private_json(failure)['status'])
        self.assertNotIn(TOKEN.encode(), failure.read_bytes())
        # The whole runner stdout, not only a search for the token: nothing else leaks either.
        self.assertEqual('', stdout.getvalue())
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_ATTEMPT_LIMIT$'):
            self.run_vertex(run_id='vertex-leak')


if __name__ == '__main__':
    unittest.main()
