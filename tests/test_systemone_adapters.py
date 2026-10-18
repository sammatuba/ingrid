"""S3 adapter counterexamples: the Gemini structured-output emulation, the HTTP client and
the probe runner.

Offline, synthetic and stdlib-only; no test here contacts a backend, opens a socket or reads
a credential. The H0 task is compiled through the real repository from the fictional seed in
`src/demo`. The Gemini transport of every row is a local callable returning a canned
envelope, and the HTTP transport is a local callable capturing its arguments, so the exact
URL and body are asserted without a server. The runner rows read and refuse configuration
files and, where they run a case at all, drive it through a synthetic transport factory.

A decision raised by a backend is sanitized by `SystemOneService` to `MODEL_UNAVAILABLE`
(S2's frozen rule for every backend exception), so an invalid response inside the emulation
is `MODEL_INVALID_RESPONSE` when `decide` is called directly and `MODEL_UNAVAILABLE` when it
travels through the service. Both are asserted below, and nothing is written either way.
"""
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.adapters.gemini import GeminiProvider
from src.adapters.gemini.run import prepare_case, write_private_json
from src.adapters.gemini.transport import LiveConfig
from src.adapters.systemone import (GeminiSystemOneEmulation, HttpSystemOne, decode_response, questions_of,
                                    response_schema, validate_envelope)
from src.adapters.systemone.run import (PREPARED_MODEL, load_config, placeholder_fields, prepare_probe, run_case)
from src.contracts.jsonutil import canonical_bytes, canonical_dumps, compute_content_digest, with_content_digest
from src.demo import seed
from src.judgment import JudgmentUnavailable, MAX_RESPONSE_BYTES as PROVIDER_TEXT_BYTES
from src.judgment.bundle import BUNDLE_VERSION, QUESTION_SPECS, receipt, render_bundle, request_digest
from src.judgment.systemone import MAX_RESPONSE_BYTES as PORT_RESPONSE_BYTES, SystemOneService
from src.review import InMemoryRepository, reference, validate_record
# The nine-candidate task fixture the S1 and S2 refusal rows use, so the runner's refusal
# row refuses the same synthetic task those do.
from tests.test_probe_bundle import candidate_entities, derived_task

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('probe_runner', ROOT / 'scripts/probe/run.py')
probe_runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe_runner)

NOW = '2026-10-05T02:00:00Z'
MODEL = 'gemini-fixture'
VERSION = 'synthetic-gemini.v1'

#: Every form answers these canonical values: q2 is a forced outage, so the H0
#: task composes `challenges` by the `outage_or_later` row rather than falling through.
ATOMIC = {'q1': 'fictional-unit-a', 'q2': 'forced_outage', 'q3': 'same', 'q4': 0.1, 'q5': 0.1,
          'q6': 0.1, 'q7': 0.9, 'q8': 'neither'}


def answers_for(bundle, atomic):
    """Well-formed per-form answers for a rendered bundle or a request-bearing mapping.

    Each form answers in its own presentation: the permuted form's token, the aliased form's
    bracketed identifier and the negated noul form's inverted probability, so a round trip
    that passes proves the emulation carried the form's own tokens, not canonical ones.
    """
    questions = bundle['request']['questions']
    answers = {}
    for spec in QUESTION_SPECS:
        for form in range(bundle['forms']):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            question = questions[name]
            value = atomic[spec['id']]
            if question['type'] == 'choice':
                token = next(token for token, canonical in question['criteria']['options'].items()
                             if canonical == value)
                answers[name] = {'choice': token, 'probabilities': {token: 1.0}}
            else:
                answers[name] = {'noul': value if question['criteria']['options']['yes'] == 'yes' else 1 - value}
    return answers


def envelope(text, *, finish='STOP', version=VERSION, parts=None):
    """One synthetic generateContent response carrying `text`; no provider is involved."""
    return {'candidates': [{'finishReason': finish, 'content': {'parts': parts or [{'text': text}]}}],
            'modelVersion': version}


class RecordingTransport:
    """The Gemini transport call shape, recording every call; returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, model, body, *, timeout_seconds, max_response_bytes):
        self.calls.append({'model': model, 'body': body, 'timeout_seconds': timeout_seconds,
                           'max_response_bytes': max_response_bytes})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class RecordingHttpTransport:
    """The HTTP transport call shape, recording the exact URL and body; returns a response."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, body, *, timeout_seconds, max_response_bytes):
        self.calls.append({'url': url, 'body': body, 'timeout_seconds': timeout_seconds,
                           'max_response_bytes': max_response_bytes})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class AdapterTestCase(unittest.TestCase):
    #: The model the H0 bundle is rendered with; a backend must be configured with it,
    #: because the rendered request names the model it was rendered for.
    model = MODEL

    def setUp(self):
        self.repo = InMemoryRepository()
        self.seed = seed(self.repo)
        self.actor = self.seed['actor']
        self.case = next(iter(self.actor.accessible_cases))
        snapshot = self.repo.build_snapshot(self.actor, self.case, NOW, NOW)
        self.task = self.repo.compile_task(self.actor, self.case, reference(snapshot), 'capacity-assumption', NOW, NOW)
        self.bundle = render_bundle(self.task, self.model)
        self.answers = answers_for(self.bundle, ATOMIC)

    def emulation(self, response, **kwargs):
        self.transport = RecordingTransport(response)
        return GeminiSystemOneEmulation(MODEL, self.transport, execution_mode='synthetic_fixture', **kwargs)

    def generate(self, backend, key='probe-a'):
        return SystemOneService(backend).generate(self.repo, self.actor, self.case,
                                                  reference(self.task), key, lambda: NOW)

    def assertNothingWritten(self, label=''):
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['probe_bundles'], label)


class SchemaTests(AdapterTestCase):
    def test_schema_has_one_property_per_question_with_enum_options(self):
        body = self.emulation(envelope('{}')).body(self.bundle['request'])
        schema = body['generationConfig']['responseFormat']['text']['schema']
        questions = self.bundle['request']['questions']
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(questions), set(schema['properties']))
        self.assertEqual(list(questions), schema['required'])
        for name, question in questions.items():
            with self.subTest(name):
                fragment = schema['properties'][name]
                self.assertFalse(fragment['additionalProperties'])
                if question['type'] == 'choice':
                    presentation = question['criteria']['presentation']
                    self.assertEqual(['choice', 'probabilities'], fragment['required'])
                    self.assertEqual(presentation, fragment['properties']['choice']['enum'])
                    self.assertEqual('string', fragment['properties']['choice']['type'])
                    probabilities = fragment['properties']['probabilities']
                    self.assertEqual(set(presentation), set(probabilities['properties']))
                    self.assertEqual(list(presentation), probabilities['required'])
                    self.assertTrue(all(value == {'type': 'number', 'minimum': 0, 'maximum': 1}
                                        for value in probabilities['properties'].values()))
                else:
                    self.assertEqual({'noul'}, set(fragment['properties']))
                    self.assertEqual(['noul'], fragment['required'])
                    self.assertEqual({'type': 'number', 'minimum': 0, 'maximum': 1},
                                     fragment['properties']['noul'])
        # The forms the renderer perturbed are constrained to what each form presented.
        aliased = schema['properties']['q1_identity_f2']['properties']['choice']['enum']
        self.assertTrue(all(token.startswith('[') and token.endswith(']') for token in aliased))
        permuted = schema['properties']['q2_event_f1']['properties']['choice']['enum']
        self.assertEqual(questions['q2_event_f1']['criteria']['presentation'], permuted)
        with self.assertRaises(ValueError):
            response_schema({})
        with self.assertRaises(ValueError):
            response_schema({'q1_identity_f0': {'type': 'other', 'criteria': {}}})

    def test_body_is_the_rendered_request_bounded_by_the_configured_api(self):
        request = self.bundle['request']
        body = self.emulation(envelope('{}')).body(request)
        self.assertEqual({'systemInstruction', 'contents', 'generationConfig'}, set(body))
        self.assertEqual(canonical_dumps(request), body['contents'][0]['parts'][0]['text'])
        self.assertEqual('user', body['contents'][0]['role'])
        self.assertEqual(1, len(body['contents'][0]['parts']))
        self.assertEqual(1, len(body['systemInstruction']['parts']))
        generation = body['generationConfig']
        self.assertEqual({'candidateCount', 'maxOutputTokens', 'responseFormat'}, set(generation))
        self.assertEqual((1, 2048), (generation['candidateCount'], generation['maxOutputTokens']))
        self.assertEqual('APPLICATION_JSON', generation['responseFormat']['text']['mimeType'])
        # The Vertex budget must be pinned or a bounded request returns MAX_TOKENS without JSON.
        vertex = self.emulation(envelope('{}'), api='vertex_ai').body(request)
        self.assertEqual({'thinkingBudget': 0}, vertex['generationConfig']['thinkingConfig'])
        bounded = self.emulation(envelope('{}'), max_output_tokens=1024).body(request)
        self.assertEqual(1024, bounded['generationConfig']['maxOutputTokens'])

    def test_constructor_requires_model_transport_mode_bounds_and_api(self):
        transport = RecordingTransport(envelope('{}'))
        self.assertRaises(TypeError, GeminiSystemOneEmulation, MODEL, transport,
                          execution_mode='synthetic_fixture', timeout_seconds=30)
        self.assertRaises(TypeError, GeminiSystemOneEmulation, MODEL)
        for model in ('gpt-4', '', 'gemini', 7, None):
            self.assertRaises(ValueError, GeminiSystemOneEmulation, model, transport,
                              execution_mode='synthetic_fixture')
        for value in (None, 'transport', 7):
            self.assertRaises(ValueError, GeminiSystemOneEmulation, MODEL, value,
                              execution_mode='synthetic_fixture')
        for mode in ('live', 'fixture', None, True):
            self.assertRaises(ValueError, GeminiSystemOneEmulation, MODEL, transport, execution_mode=mode)
        for tokens in (0, 2049, True, 2048.0, '2048'):
            self.assertRaises(ValueError, GeminiSystemOneEmulation, MODEL, transport,
                              execution_mode='synthetic_fixture', max_output_tokens=tokens)
        self.assertRaises(ValueError, GeminiSystemOneEmulation, MODEL, transport,
                          execution_mode='synthetic_fixture', api='openai')
        self.assertEqual(0, len(transport.calls))

    def test_renderer_arguments_are_caller_errors_not_model_errors(self):
        emulation = self.emulation(envelope('{}'))
        for request in (None, {}, {'model': MODEL, 'state': {}, 'questions': {}},
                        {'model': MODEL, 'state': {}, 'answers': {}},
                        {'model': MODEL, 'state': {}, 'questions': []},
                        dict(self.bundle['request'], extra=True)):
            with self.subTest(str(request)[:40]):
                self.assertRaises(ValueError, questions_of, request)
                self.assertRaises(ValueError, emulation.body, request)
                self.assertRaises(ValueError, emulation.decide, request)
        self.assertRaises(ValueError, emulation.decide, dict(self.bundle['request'], model='gemini-other'))
        self.assertEqual([], self.transport.calls)


class EmulationResponseTests(AdapterTestCase):
    def test_truncated_oversize_malformed_and_missing_question_write_nothing(self):
        good = canonical_dumps(self.answers)
        dropped = canonical_dumps({name: answer for name, answer in self.answers.items() if name != 'q3_time_f1'})
        rows = (
            ('truncated', envelope(good, finish='MAX_TOKENS')),
            ('oversize text', envelope('{"padding":"' + 'x' * (70 * 1024) + '"}')),
            ('oversize envelope', dict(envelope(good), padding='x' * 70000)),
            ('malformed text', envelope('not json at all')),
            ('duplicate keys', envelope('{"answers":{},"answers":{}}')),
            ('non-finite number', envelope('{"q3_time_f1":NaN}')),
            ('text is a list', envelope('[1,2,3]')),
            ('missing question', envelope(dropped)),
            ('unknown option', envelope(canonical_dumps(dict(self.answers,
                q1_identity_f0={'choice': 'who', 'probabilities': {'who': 1.0}})))),
            ('probability above one', envelope(canonical_dumps(dict(self.answers,
                q4_conditional_f0={'noul': 1.2})))),
            ('answer is not an object', envelope(canonical_dumps(dict(self.answers, q2_event_f0='testing')))),
            ('extra answer', envelope(canonical_dumps(dict(self.answers, q9_extra_f0={'noul': 0.5})))),
            ('frozen envelope instead of answers', envelope(canonical_dumps(
                {'answers': self.answers, 'model_version': VERSION}))),
            ('two candidates', dict(envelope(good), candidates=envelope(good)['candidates'] * 2)),
            ('blank model version', envelope(good, version='')),
            ('no model version', {'candidates': envelope(good)['candidates']}),
            ('two parts', envelope(good, parts=[{'text': good}, {'text': good}])),
            ('authority part', envelope(good, parts=[{'text': good, 'approval': True}])),
            ('non-text part', envelope(good, parts=[{'text': 7}])),
            ('oversize thought signature', envelope(good, parts=[{'text': good, 'thoughtSignature': 'x' * 16385}])),
        )
        for label, response in rows:
            with self.subTest(label):
                transport = RecordingTransport(response)
                backend = GeminiSystemOneEmulation(MODEL, transport, execution_mode='synthetic_fixture')
                with self.assertRaises(JudgmentUnavailable) as caught:
                    backend.decide(self.bundle['request'])
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
                self.assertEqual(1, len(transport.calls))  # one attempt, never a retry
                served = GeminiSystemOneEmulation(MODEL, transport, execution_mode='synthetic_fixture')
                with self.assertRaises(JudgmentUnavailable) as through:
                    self.generate(served)
                # Any backend failure reaches the service as one safe code, never the
                # adapter's own, and never as a partial answer.
                self.assertEqual('MODEL_UNAVAILABLE', through.exception.code)
                self.assertEqual(2, len(transport.calls))
                self.assertNothingWritten(label)

    def test_an_opaque_signature_is_provider_metadata_and_the_answers_still_parse(self):
        response = envelope(canonical_dumps(self.answers),
                            parts=[{'text': canonical_dumps(self.answers), 'thoughtSignature': 'opaque'}])
        backend = self.emulation(response)
        self.assertEqual({'answers': self.answers, 'model_version': VERSION}, backend.decide(self.bundle['request']))
        self.assertEqual(1, len(self.transport.calls))

    def test_a_backend_transport_failure_is_never_retried_and_writes_nothing(self):
        backend = self.emulation(JudgmentUnavailable('MODEL_TIMEOUT'))
        with self.assertRaises(JudgmentUnavailable) as caught:
            self.generate(backend)
        self.assertEqual('MODEL_UNAVAILABLE', caught.exception.code)
        self.assertEqual(1, len(self.transport.calls))
        self.assertNothingWritten()

    def test_decoded_envelopes_are_read_from_the_port_bound(self):
        self.assertEqual(('{}', VERSION), decode_response(envelope('{}')))
        self.assertRaises(JudgmentUnavailable, validate_envelope, {'q1_identity_f0': {}},
                          {'answers': {}, 'model_version': ''})
        self.assertRaises(JudgmentUnavailable, validate_envelope, {'q1_identity_f0': {}},
                          {'answers': {}, 'model_version': 'x' * 201})

    def test_the_decoded_text_cap_is_gemini_providers_and_not_the_port_bound(self):
        """The designated review's finding: the answer text is capped at 32 KiB.

        The whitespace-padded texts parse to the same well-formed answers and every
        envelope stays under the port's 64 KiB, so the text cap is the only thing that can
        refuse them; before the fix the reviewer's 42,036-byte envelope was accepted while
        ``GeminiProvider`` refused the identical envelope.
        """
        good = canonical_dumps(self.answers)

        def padded(size):
            """Well-formed answers with insignificant JSON spaces, exactly `size` text bytes."""
            return good[0] + ' ' * (size - len(good.encode('utf-8'))) + good[1:]

        for label, size, accepted in (('at the Gemini cap', PROVIDER_TEXT_BYTES, True),
                                      ('one byte over the cap', PROVIDER_TEXT_BYTES + 1, False),
                                      ("the reviewer's padded envelope", 41701, False)):
            with self.subTest(label):
                response = envelope(padded(size))
                self.assertLessEqual(len(canonical_bytes(response)), PORT_RESPONSE_BYTES)
                provider = GeminiProvider(MODEL, RecordingTransport(response),
                                          execution_mode='synthetic_fixture')
                backend = GeminiSystemOneEmulation(MODEL, RecordingTransport(response),
                                                   execution_mode='synthetic_fixture')
                if accepted:
                    self.assertEqual(padded(size), provider.generate('synthetic')['text'])
                    self.assertEqual({'answers': self.answers, 'model_version': VERSION},
                                     backend.decide(self.bundle['request']))
                else:
                    for call in (lambda: provider.generate('synthetic'),
                                 lambda: backend.decide(self.bundle['request'])):
                        with self.assertRaises(JudgmentUnavailable) as caught:
                            call()
                        self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
                    served = GeminiSystemOneEmulation(MODEL, RecordingTransport(response),
                                                      execution_mode='synthetic_fixture')
                    with self.assertRaises(JudgmentUnavailable) as through:
                        self.generate(served)
                    # One safe code through the service, and nothing written.
                    self.assertEqual('MODEL_UNAVAILABLE', through.exception.code)
                    self.assertNothingWritten(label)


class EmulationRoundTripTests(AdapterTestCase):
    def test_valid_synthetic_round_trip_saves_with_verbalized_probabilities(self):
        transport = RecordingTransport(envelope(canonical_dumps(self.answers)))
        backend = GeminiSystemOneEmulation(MODEL, transport, execution_mode='synthetic_fixture')
        saved = self.generate(backend)
        validate_record(saved)
        self.assertEqual('ProbeBundleArtifact', saved['record_kind'])
        payload = saved['payload']
        self.assertEqual(reference(self.task), payload['task_ref'])
        self.assertEqual(self.actor.actor_id, payload['actor_id'])
        self.assertEqual('probe-a', payload['idempotency_key'])
        self.assertEqual('proposed', payload['review_state'])
        self.assertIs(True, payload['synthetic'])
        self.assertEqual(self.answers, payload['answers'])
        # The forms' own tokens survived: the aliased choice, the negated noul, and the
        # un-negated atomic values the composition reads.
        aliased = self.answers['q1_identity_f2']['choice']
        self.assertEqual('fictional-unit-a',
                         self.bundle['request']['questions']['q1_identity_f2']['criteria']['options'][aliased])
        self.assertEqual(1 - ATOMIC['q4'], self.answers['q4_conditional_f1']['noul'])
        self.assertEqual(('fictional-unit-a', 'no'),
                         (payload['composed']['atomic']['q1'], payload['composed']['atomic']['q4']))
        self.assertEqual(('challenges', 'outage_or_later', None),
                         (payload['composed']['label'], payload['composed']['fired_rule'].split(':')[0],
                          payload['composed']['reason']))
        metadata = payload['metadata']
        self.assertEqual(('gemini', MODEL, VERSION, 'synthetic_fixture', 'verbalized_uncalibrated'),
                         (metadata['provider'], metadata['model'], metadata['model_version'],
                          metadata['execution_mode'], metadata['probabilities']))
        self.assertEqual(BUNDLE_VERSION, metadata['bundle_version'])
        self.assertEqual(self.bundle['request_digest'], metadata['request_digest'])
        self.assertEqual(compute_content_digest(payload['composed']), metadata['output_digest'])
        self.assertEqual(receipt(self.bundle, self.answers), payload['receipt'])
        # One call, the Gemini bounds, and a body whose text is exactly the rendered request.
        self.assertEqual(1, len(transport.calls))
        call = transport.calls[0]
        self.assertEqual((MODEL, 30, 65536), (call['model'], call['timeout_seconds'], call['max_response_bytes']))
        self.assertEqual(canonical_dumps(self.bundle['request']), call['body']['contents'][0]['parts'][0]['text'])
        self.assertEqual(self.bundle['request_digest'],
                         request_digest(json.loads(call['body']['contents'][0]['parts'][0]['text'])))
        self.assertEqual([saved], self.repo.workspace(self.actor, self.case)['probe_bundles'])
        self.assertEqual([], self.repo.workspace(self.actor, self.case)['judgments'])
        # A replay of the same key reads the saved artifact without another call.
        self.assertEqual(saved, self.generate(backend))
        self.assertEqual(1, len(transport.calls))


class HttpSystemOneTests(AdapterTestCase):
    model = 'clef-flash'

    def client(self, response, base_url='http://127.0.0.1:8080'):
        self.http = RecordingHttpTransport(response)
        return HttpSystemOne(base_url, self.http, model=self.model, execution_mode='synthetic_fixture')

    def test_the_client_posts_the_exact_path_with_the_rendered_request_and_never_retries(self):
        request = self.bundle['request']
        client = self.client({'answers': self.answers, 'model_version': 'clef-0.1'})
        self.assertEqual({'answers': self.answers, 'model_version': 'clef-0.1'}, client.decide(request))
        self.assertEqual(1, len(self.http.calls))
        call = self.http.calls[0]
        self.assertEqual('http://127.0.0.1:8080/v1/systemone', call['url'])
        self.assertEqual(request, call['body'])
        self.assertEqual(canonical_dumps(request), canonical_dumps(call['body']))
        self.assertEqual(self.bundle['request_digest'], request_digest(call['body']))
        self.assertEqual((30, 65536), (call['timeout_seconds'], call['max_response_bytes']))
        # The base is an origin: a trailing slash does not double the path.
        self.client({'answers': self.answers, 'model_version': 'clef-0.1'},
                    base_url='http://127.0.0.1:8080/').decide(request)
        self.assertEqual('http://127.0.0.1:8080/v1/systemone', self.http.calls[0]['url'])
        # The injected callable is the only thing that can reach a server.
        with patch('socket.socket', side_effect=AssertionError('the client must not open a socket')):
            self.client({'answers': self.answers, 'model_version': 'clef-0.1'}).decide(request)

    def test_no_default_url_or_transport_and_explicit_configuration_required(self):
        self.assertRaises(TypeError, HttpSystemOne)
        self.assertRaises(TypeError, HttpSystemOne, 'http://127.0.0.1:8080')
        transport = RecordingHttpTransport({'answers': self.answers, 'model_version': 'clef-0.1'})
        for base_url in ('', '/v1/systemone', 'ftp://server', 'http://', '127.0.0.1:8080',
                         'http://127.0.0.1:8080/v1/systemone', 'http://127.0.0.1:8080?tenant=a',
                         'http://127.0.0.1:8080/#fragment', 'http://user:secret@127.0.0.1:8080', 8080, None):
            with self.subTest(str(base_url)):
                self.assertRaises(ValueError, HttpSystemOne, base_url, transport,
                                  model='clef-flash', execution_mode='synthetic_fixture')
        for value in (None, 'transport', 7):
            self.assertRaises(ValueError, HttpSystemOne, 'http://127.0.0.1:8080', value,
                              model='clef-flash', execution_mode='synthetic_fixture')
        for model in ('', '  ', 'x' * 201, 7):
            self.assertRaises(ValueError, HttpSystemOne, 'http://127.0.0.1:8080', transport,
                              model=model, execution_mode='synthetic_fixture')
        for mode in ('live', None, True):
            self.assertRaises(ValueError, HttpSystemOne, 'http://127.0.0.1:8080', transport,
                              model='clef-flash', execution_mode=mode)
        # The class carries no URL, transport or model of its own; only the configured
        # instance does, and the callable that can reach a server is the injected one.
        self.assertEqual({'name', 'probabilities'},
                         {name for name, value in vars(HttpSystemOne).items()
                          if not name.startswith('__') and not callable(value)})
        self.assertRaises(ValueError, self.client({'answers': self.answers, 'model_version': 'x'}).decide,
                          dict(self.bundle['request'], model='clef-other'))

    def test_a_malformed_response_is_refused_and_nothing_is_read_from_an_oversized_one(self):
        rows = (
            ('missing question', {name: answer for name, answer in self.answers.items() if name != 'q5_lineage_f0'}),
            ('unknown option', dict(self.answers, q1_identity_f0={'choice': 'who', 'probabilities': {'who': 1.0}})),
            ('probability below zero', dict(self.answers, q7_sufficiency_f0={'noul': -0.1})),
            ('probability above one', dict(self.answers, q3_time_f0={'choice': 'same', 'probabilities': {'same': 1.2}})),
            ('extra answer', dict(self.answers, q9_extra_f0={'noul': 0.5})),
            ('not an object', 'answers'),
        )
        for label, answers in rows:
            with self.subTest(label):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    self.client({'answers': answers, 'model_version': 'clef-0.1'}).decide(self.bundle['request'])
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)
                self.assertEqual(1, len(self.http.calls))
        for label, response in (
                ('extra key', {'answers': self.answers, 'model_version': 'clef-0.1', 'ok': True}),
                ('no version', {'answers': self.answers}),
                ('blank version', {'answers': self.answers, 'model_version': ''}),
                ('oversize', {'answers': self.answers, 'model_version': 'clef-0.1', 'padding': 'x' * 70000}),
                ('not a mapping', [self.answers]),
        ):
            with self.subTest(label):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    self.client(response).decide(self.bundle['request'])
                self.assertEqual('MODEL_INVALID_RESPONSE', caught.exception.code)

    def test_a_round_trip_through_the_port_records_unreported_probabilities(self):
        client = self.client({'answers': self.answers, 'model_version': 'clef-0.1'})
        saved = self.generate(client)
        validate_record(saved)
        metadata = saved['payload']['metadata']
        self.assertEqual(('systemone_http', 'clef-flash', 'clef-0.1', 'synthetic_fixture', 'unreported'),
                         (metadata['provider'], metadata['model'], metadata['model_version'],
                          metadata['execution_mode'], metadata['probabilities']))
        self.assertEqual(self.answers, saved['payload']['answers'])
        self.assertEqual(self.bundle['request_digest'], metadata['request_digest'])
        self.assertEqual(1, len(self.http.calls))
        self.assertEqual('http://127.0.0.1:8080/v1/systemone', self.http.calls[0]['url'])


class ProbeFixtureTransport:
    """A synthetic one-attempt transport with the runner's call shape: no subprocess, no credential.

    It answers from the request it is given, so the answered question set is the rendered
    one; its receipt stands in for the transport receipt the real adapter records.
    """

    def __init__(self, config, ledger_path):
        self.config, self.ledger_path, self.last_receipt = config, ledger_path, None
        self.calls = []

    def __call__(self, model, body, *, timeout_seconds, max_response_bytes):
        request = json.loads(body['contents'][0]['parts'][0]['text'])
        self.calls.append({'model': model, 'timeout_seconds': timeout_seconds,
                           'max_response_bytes': max_response_bytes})
        self.last_receipt = {'attempt': 1, 'status': 'response_received', 'model': model,
                             'request_body_digest': hashlib.sha256(canonical_bytes(body)).hexdigest()}
        return envelope(canonical_dumps(answers_for({'request': request, 'forms': 4}, ATOMIC)),
                        version='synthetic-gemini.v2')


class FailingProbeTransport(ProbeFixtureTransport):
    def __call__(self, model, body, *, timeout_seconds, max_response_bytes):
        self.calls.append({'model': model})
        self.last_receipt = {'attempt': 1, 'status': 'MODEL_QUOTA'}
        raise JudgmentUnavailable('MODEL_QUOTA')


class RefusingBundleRepository:
    """Serves the runner a task the real renderer refuses, and pins the refusal's no-write.

    A nine-candidate mapping cannot be compiled through the repository (`_bind_mapping`
    requires a `one_to_one` mapping to carry exactly one entity), so the task is the same
    synthetic ``derived_task`` fixture the S1 and S2 refusal rows use; the real renderer
    refuses it inside the real service. ``bundle_input`` returns it, ``save_bundle`` and
    ``bundle_lineage_prior`` raise rather than proceed, and the runner's own reads
    (``heads``, ``history``) delegate to the real repository.
    """

    def __init__(self, repository, task):
        self.repository, self.task = repository, task

    def bundle_input(self, actor, case, task_ref, key):
        return None, self.task

    def bundle_lineage_prior(self, *args):
        raise AssertionError('a refused render must not resolve a lineage prior')

    def save_bundle(self, *args):
        raise AssertionError('a refused render must not write')

    def heads(self, actor, case):
        return self.repository.heads(actor, case)

    def history(self, actor, case):
        return self.repository.history(actor, case)


#: The example configuration of `src/adapters/gemini/README.md`, verbatim values included:
#: every value here satisfies `LiveConfig`'s grammar, which is the gap the runner's
#: placeholder refusal closes.
PLACEHOLDER_CONFIG = {'api': 'gemini_developer', 'project': 'replace-with-approved-project',
    'model': 'gemini-approved-model', 'credential_env': 'APPROVED_GEMINI_API_KEY',
    'authorization_ref': 'replace-with-recorded-service-case-and-budget-authorization',
    'run_id': 'approved-smoke-001', 'permitted_case': 'synthetic-case',
    'budget_policy': 'request_and_token_limits', 'api_version': 'v1beta', 'location': 'global',
    'max_attempts': 1, 'timeout_seconds': 30, 'max_request_bytes': 196608,
    'max_response_bytes': 65536, 'max_output_tokens': 2048}

#: A concrete-shaped configuration for the parse-check rows. The authorization reference
#: says what it is: no run is made with it and no service input is claimed by it.
CONCRETE_CONFIG = dict(PLACEHOLDER_CONFIG, project='grid-nowcast', model='gemini-3.8-flash',
    credential_env='GEMINI_API_KEY', authorization_ref='parse-check-only-not-an-authorization',
    run_id='probe-2026-10-13-01')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-probe-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def config_file(self, value, name='probe-config.json'):
        path = self.root / name
        path.write_bytes(canonical_bytes(value) + b'\n')
        return path

    def run_main(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = probe_runner.main(argv)
        return code, json.loads(out.getvalue())

    def exploding_transport(self, *args):
        """A transport factory that must never be reached: a saved result is read back,
        never re-run. A regressed read-back guard fails here instead of building the real
        transport and attempting a live call."""
        raise AssertionError('a saved result must never build a transport')

    def test_the_runner_refuses_placeholder_configuration(self):
        self.assertEqual(set(LiveConfig.__dataclass_fields__), set(PLACEHOLDER_CONFIG))
        # The published example already passes the transport's own value grammar; only the
        # placeholder refusal stops it.
        self.assertIsInstance(LiveConfig.from_dict(PLACEHOLDER_CONFIG), LiveConfig)
        self.assertEqual(('authorization_ref', 'credential_env', 'model', 'project', 'run_id'),
                         placeholder_fields(LiveConfig.from_dict(PLACEHOLDER_CONFIG)))
        path = self.config_file(PLACEHOLDER_CONFIG)
        with self.assertRaises(JudgmentUnavailable) as caught:
            load_config(path)
        self.assertEqual('MODEL_CONFIG_INVALID', caught.exception.code)
        with patch.object(probe_runner, 'ROOT', self.root), patch.object(
                probe_runner, 'run_case', side_effect=AssertionError('a refused config must not run')):
            code, printed = self.run_main(['--config', str(path)])
        self.assertEqual((1, 'MODEL_CONFIG_INVALID', False),
                         (code, printed['status'], printed['inference_verified']))
        self.assertFalse((self.root / '.local').exists())
        # The rule is per field and per documented word, not one hard-coded file.
        for field, value in (('run_id', 'TODO-1'), ('run_id', 'CHANGE_ME'), ('project', 'your-project'),
                             ('authorization_ref', 'placeholder authorization'),
                             ('model', 'gemini-EXAMPLE-model'), ('credential_env', 'SAMPLE_GEMINI_KEY')):
            with self.subTest(f'{field}={value}'):
                self.assertTrue(placeholder_fields(LiveConfig.from_dict(dict(CONCRETE_CONFIG, **{field: value}))))

    def test_the_runner_loads_a_concrete_configuration_and_refuses_other_shapes(self):
        config = load_config(self.config_file(CONCRETE_CONFIG))
        self.assertEqual((), placeholder_fields(config))
        self.assertEqual(('grid-nowcast', 'gemini-3.8-flash', 'probe-2026-10-13-01'),
                         (config.project, config.model, config.run_id))
        for label, value in (
                ('placeholder credential env', dict(CONCRETE_CONFIG, credential_env='APPROVED_GEMINI_API_KEY')),
                ('unknown key', dict(CONCRETE_CONFIG, budget_usd=5)),
                ('missing key', {k: v for k, v in CONCRETE_CONFIG.items() if k != 'location'})):
            with self.subTest(label):
                with self.assertRaises(JudgmentUnavailable) as caught:
                    load_config(self.config_file(value, name=f"{label.replace(' ', '-')}.json"))
                self.assertEqual('MODEL_CONFIG_INVALID', caught.exception.code)
        with self.assertRaises(JudgmentUnavailable) as caught:
            run_case(replace(config, max_attempts=2), self.root,
                     transport_factory=lambda *args: AssertionError('no transport'))
        self.assertEqual('MODEL_CONFIG_INVALID', caught.exception.code)
        self.assertFalse((self.root / config.run_id).exists())

    def test_offline_preparation_names_no_model_and_performs_no_inference(self):
        with patch('src.adapters.gemini.transport.subprocess.Popen', side_effect=AssertionError('network')):
            prepared = prepare_probe(lambda: NOW)
        self.assertEqual(('offline_preparation', False, PREPARED_MODEL),
                         (prepared['mode'], prepared['inference_performed'], prepared['model']))
        self.assertEqual(32, prepared['question_count'])
        self.assertEqual(request_digest(prepared['request']), prepared['request_digest'])
        self.assertEqual(canonical_dumps(render_bundle(prepared['task'], PREPARED_MODEL)['request']),
                         canonical_dumps(prepared['request']))
        self.assertEqual(BUNDLE_VERSION, prepared['bundle_version'])
        self.assertTrue(prepared['semantic_checks'])
        validate_record(prepared['task'])
        with patch.object(probe_runner, 'ROOT', self.root):
            code, printed = self.run_main([])
        self.assertEqual((0, 'offline_preparation', False),
                         (code, printed['status'], printed['inference_performed']))
        written = json.loads((self.root / '.local/probe/prepared.json').read_text(encoding='utf-8'))
        self.assertEqual((False, PREPARED_MODEL, 32),
                         (written['inference_performed'], written['model'], written['question_count']))
        self.assertEqual((self.root / '.local/probe/prepared.json').as_posix(), printed['artifact'])

    def test_the_probe_case_saves_one_bundle_and_a_restart_makes_no_call(self):
        config = load_config(self.config_file(CONCRETE_CONFIG))
        created = []

        def factory(config_value, ledger_path):
            transport = ProbeFixtureTransport(config_value, ledger_path)
            created.append(transport)
            return transport

        result = run_case(config, self.root, transport_factory=factory,
                          execution_mode='synthetic_fixture', clock=lambda: NOW)
        saved = result['bundle']
        validate_record(saved)
        self.assertEqual(('proposed_bundle_saved', 'synthetic_fixture'),
                         (result['status'], result['execution_mode']))
        metadata = saved['payload']['metadata']
        self.assertEqual((config.model, 'synthetic-gemini.v2', 'gemini', 'synthetic_fixture',
                          'verbalized_uncalibrated'),
                         (metadata['model'], metadata['model_version'], metadata['provider'],
                          metadata['execution_mode'], metadata['probabilities']))
        self.assertEqual('pending_human_review', result['semantic_review']['status'])
        self.assertEqual(1, result['transport']['attempt'])
        self.assertEqual(32, len(saved['payload']['answers']))
        self.assertEqual(1, len(created))
        self.assertEqual(1, len(created[0].calls))
        self.assertNotIn('GEMINI_API_KEY', json.dumps(result))
        self.assertEqual([saved], [result['bundle']])
        # The restart reads the immutable result: no second transport, no second call. The
        # factory raises if it is ever reached, so a regressed read-back guard fails loudly
        # instead of building a live transport.
        again = run_case(config, self.root, transport_factory=self.exploding_transport,
                         execution_mode='synthetic_fixture', clock=lambda: NOW)
        self.assertEqual(result, again)
        self.assertEqual(1, len(created))
        result_path = self.root / config.run_id / 'result.json'
        write_private_json(result_path, with_content_digest(dict(result, config_digest='0' * 64)))
        with self.assertRaises(JudgmentUnavailable) as caught:
            run_case(config, self.root, transport_factory=self.exploding_transport,
                     execution_mode='synthetic_fixture', clock=lambda: NOW)
        self.assertEqual('MODEL_ALLOWANCE_CONFLICT', caught.exception.code)
        write_private_json(result_path, dict(result, content_digest='0' * 64))
        with self.assertRaises(JudgmentUnavailable) as caught:
            run_case(config, self.root, transport_factory=self.exploding_transport,
                     execution_mode='synthetic_fixture', clock=lambda: NOW)
        self.assertEqual('MODEL_RECEIPT_INVALID', caught.exception.code)

    def test_a_render_refusal_is_saved_as_a_result_and_a_restart_makes_no_call(self):
        """The interim review's open minor: the `render_refused` branches through the runner.

        The task is the nine-candidate synthetic fixture (S1's cap is eight), so the real
        renderer refuses with `TOO_MANY_CANDIDATES`. No request exists, so the backend is
        never called, and the refusal is saved as the run's result: a restart reads it back
        without constructing a transport.
        """
        config = load_config(self.config_file(CONCRETE_CONFIG))
        created = []

        def factory(config_value, ledger_path):
            transport = ProbeFixtureTransport(config_value, ledger_path)
            created.append(transport)
            return transport

        def nine_candidates_for_preparation(clock):
            """The nine-candidate task, as ``prepare_probe`` consumes the compiled one."""
            repository, actor, task, seeded = prepare_case(clock)
            return repository, actor, derived_task(task, candidates=candidate_entities(9)), seeded

        def nine_candidates_for_the_runner(clock):
            """The same task, served through the one read the runner's service performs."""
            repository, actor, task, seeded = prepare_case(clock)
            return (RefusingBundleRepository(repository, derived_task(task, candidates=candidate_entities(9))),
                    actor, task, seeded)

        refusal = {'status': 'insufficient', 'reason': 'TOO_MANY_CANDIDATES',
                   'bundle_version': BUNDLE_VERSION}
        with patch('src.adapters.systemone.run.prepare_case', side_effect=nine_candidates_for_preparation):
            prepared = prepare_probe(lambda: NOW)
        self.assertEqual(refusal, prepared['refusal'])
        self.assertNotIn('request', prepared)
        with patch('src.adapters.systemone.run.prepare_case', side_effect=nine_candidates_for_the_runner):
            result = run_case(config, self.root, transport_factory=factory,
                              execution_mode='synthetic_fixture', clock=lambda: NOW)
        self.assertEqual(('render_refused', refusal, None),
                         (result['status'], result['refusal'], result['transport']))
        self.assertEqual(1, len(created))
        self.assertEqual([], created[0].calls)
        self.assertTrue((self.root / config.run_id / 'result.json').exists())
        self.assertFalse((self.root / config.run_id / 'failure.json').exists())
        again = run_case(config, self.root, transport_factory=self.exploding_transport,
                         execution_mode='synthetic_fixture', clock=lambda: NOW)
        self.assertEqual(result, again)

    def test_a_failed_attempt_is_preserved_and_never_answered_from_a_stale_result(self):
        config = load_config(self.config_file(CONCRETE_CONFIG))
        with self.assertRaises(JudgmentUnavailable) as caught:
            run_case(config, self.root, transport_factory=FailingProbeTransport,
                     execution_mode='synthetic_fixture', clock=lambda: NOW)
        # The service sanitizes any backend failure, the transport's own code included.
        self.assertEqual('MODEL_UNAVAILABLE', caught.exception.code)
        failure = json.loads((self.root / config.run_id / 'failure.json').read_text(encoding='utf-8'))
        self.assertEqual(('MODEL_UNAVAILABLE', {'attempt': 1, 'status': 'MODEL_QUOTA'}),
                         (failure['status'], failure['transport']))
        self.assertFalse((self.root / config.run_id / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()
