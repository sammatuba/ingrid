"""The real-case permission gate: the allowlist, the signed record and the declared case.

No Gemini, Vertex AI or other network request is made. Every call below goes through a fake
worker program that prints a synthetic envelope, so the transport's own bounds, ledger and
receipt are exercised without a socket; the permission records are synthetic scratch files,
except where the checkout's own signed record is read to show it is the accepted one.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.adapters.gemini import GeminiProvider
from src.adapters.gemini.run import run_case
from src.adapters.gemini.transport import (DeveloperAPITransport, LiveConfig, REAL_CASE_ALLOWLIST,
    signed_permissions)
from src.contracts.jsonutil import canonical_bytes
from src.judgment import JudgmentUnavailable
from src.review.records import load_permissions

ROOT = Path(__file__).resolve().parents[1]
CASE = 'pedc-u2-2026-09-21'
PERMISSION = 'perm:wesm-company-copy:2026-10-13'
KEY = 'labeled-permission-test-key-never-real'

#: A fake worker: it consumes the envelope, never opens a socket, and prints a synthetic
#: provider-shaped envelope. The answer text is a well-formed judgment for the provider.
FIXTURE_WORKER = '''
import json, sys
json.load(sys.stdin)
answer = {'label': 'insufficient', 'explanation': 'Synthetic permission fixture.',
    'citations': [{'passage_index': 0, 'quote': 'synthetic'}], 'alternatives': [], 'unknowns': []}
response = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(answer)}]}}],
    'modelVersion': 'synthetic-permission-fixture.v1', 'responseId': 'synthetic-permission-response',
    'usageMetadata': {'promptTokenCount': 7, 'totalTokenCount': 9}}
print(json.dumps({'response': response}))
'''


class FakeTransport(DeveloperAPITransport):
    """The real transport and the real ledger, with the worker replaced by the fake above."""
    program = FIXTURE_WORKER

    def _start_worker(self):
        self.process = subprocess.Popen([sys.executable, '-c', self.program],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return self.process


def config(**changes):
    values = dict(project='synthetic-project', model='gemini-fixture',
        credential_env='PERMISSION_TEST_KEY', authorization_ref='synthetic-permission-test',
        run_id='permission-run', api_version='v1beta', permitted_case='synthetic-case',
        budget_policy='request_and_token_limits', location='global', max_attempts=1,
        timeout_seconds=3, max_request_bytes=192*1024, max_response_bytes=65536,
        max_output_tokens=2048, api='gemini_developer')
    values.update(changes)
    return LiveConfig(**values)


def body():
    return {'systemInstruction': {'parts': [{'text': 'synthetic instruction'}]},
        'contents': [{'role': 'user', 'parts': [{'text': 'synthetic prompt'}]}],
        'generationConfig': {'candidateCount': 1, 'maxOutputTokens': 2048,
            'responseFormat': {'text': {'mimeType': 'APPLICATION_JSON'}}}}


def record_text(identifier=PERMISSION, status='signed'):
    """One scratch permission record in the shape the repository and transport parse."""
    lines = ['# Permission record: synthetic scratch, never a grant', '']
    if status is not None:
        lines += [f'Status: **{status}**, 2026-10-13. Synthetic scratch record for tests.', '']
    lines += [f'Permission identifier (the `permission_ref` value records cite): `{identifier}`', '']
    return '\n'.join(lines)


class PermissionGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-permission-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'PERMISSION_TEST_KEY': KEY})
        self.env.start()
        self.addCleanup(self.env.stop)

    def permission_root(self, *, status='signed', identifier=PERMISSION, present=True, name='record.md'):
        """A scratch checkout root holding one permission record, or none at all."""
        root = self.root / ('root-%s-%s-%s' % (status, identifier.replace(':', '-').replace(' ', '-'),
            'present' if present else 'absent'))
        if present:
            directory = root.joinpath('docs', 'work', 'permissions')
            directory.mkdir(parents=True, exist_ok=True)
            (directory / name).write_text(record_text(identifier, status), encoding='utf-8')
        return root

    def invoke(self, transport, *, case='synthetic-case', request=None):
        return transport('gemini-fixture', request or body(), case=case,
            timeout_seconds=30, max_response_bytes=65536)

    # -- the fictional case: unchanged, and it never reads a permission record -----------------

    def test_the_fictional_case_is_unchanged_and_cites_no_permission(self):
        transport = FakeTransport(config(), self.root / 'fictional-allowance',
            permission_root=self.root / 'no-permission-directory')
        self.invoke(transport)
        receipt = transport.last_receipt
        self.assertEqual('response_received', receipt['status'])
        self.assertEqual('synthetic-case', receipt['permitted_case'])
        self.assertIsNone(receipt['permission_ref'])
        self.assertEqual(1, receipt['attempt'])
        self.assertEqual(len(canonical_bytes(body())), receipt['request_bytes'])
        self.assertNotIn(KEY, json.dumps(receipt))
        # No permission directory was read or needed: the configured path does not exist.
        self.assertFalse((self.root / 'no-permission-directory').exists())
        # A caller that declares nothing is served exactly as before.
        silent = FakeTransport(config(), self.root / 'fictional-silent')
        self.invoke(silent, case=None)
        self.assertEqual('response_received', silent.last_receipt['status'])
        # The transport reads the checkout's records by default.
        self.assertEqual(ROOT, FakeTransport(config(), self.root / 'default-root').permission_root)

    # -- the allowlisted real case ------------------------------------------------------------

    def test_the_allowlisted_real_case_runs_with_its_live_signed_record_and_declared_case(self):
        checkout = FakeTransport(config(permitted_case=CASE), self.root / 'checkout-allowance')
        self.invoke(checkout, case=CASE)
        receipt = checkout.last_receipt
        self.assertEqual('response_received', receipt['status'])
        self.assertEqual(CASE, receipt['permitted_case'])
        self.assertEqual(PERMISSION, receipt['permission_ref'])
        self.assertEqual(1, receipt['attempt'])
        self.assertEqual('gemini-fixture', receipt['model'])
        self.assertEqual({'timeout_seconds': 3, 'max_response_bytes': 65536,
            'max_output_tokens': 2048, 'max_attempts': 1}, receipt['limits'])
        self.assertNotIn(KEY, json.dumps(receipt))
        # The same call against a scratch root whose record is signed is served too, so the
        # refusal cases below differ in the record's state and nothing else.
        scratch = FakeTransport(config(permitted_case=CASE), self.root / 'scratch-allowance',
            permission_root=self.permission_root())
        self.invoke(scratch, case=CASE)
        self.assertEqual(PERMISSION, scratch.last_receipt['permission_ref'])

    # -- what a configuration may name ---------------------------------------------------------

    def test_no_configuration_can_name_a_case_outside_the_allowlist(self):
        for value in ('private-case', '', 'synthetic-case ', 'PEDC-U2-2026-09-21',
                'pedc-u2-2026-09-21-ish', None, True, ['pedc-u2-2026-09-21']):
            with self.subTest(permitted_case=value):
                with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                    config(permitted_case=value)
        self.assertEqual(CASE, config(permitted_case=CASE).permitted_case)
        # The operator path accepts exactly the allowlisted id, through the same grammar.
        value = config(permitted_case=CASE).as_dict()
        self.assertEqual(config(permitted_case=CASE), LiveConfig.from_dict(value))
        refused = dict(value, permitted_case='private-case')
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
            LiveConfig.from_dict(refused)

    def test_the_permission_is_never_a_configuration_value(self):
        # The operator file cannot supply or override a permission: the declared fields are
        # the grammar, and neither a permission_ref key nor a permission key is one of them.
        value = config(permitted_case=CASE).as_dict()
        self.assertNotIn('permission_ref', LiveConfig.__dataclass_fields__)
        for extra in (dict(value, permission_ref=PERMISSION),
                dict(value, permission='perm:forged:2026-01-01')):
            with self.subTest(extra=sorted(set(extra) - set(value))):
                with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                    LiveConfig.from_dict(extra)
        # The table is the only source, and it is exactly the recorded binding.
        self.assertEqual({CASE: PERMISSION}, dict(REAL_CASE_ALLOWLIST))

    def test_a_real_case_needs_its_caller_to_declare_it_before_any_attempt(self):
        transport = FakeTransport(config(permitted_case=CASE), self.root / 'declared-allowance',
            permission_root=self.permission_root())
        with patch.object(transport, '_start_worker') as start:
            for declared in (None, 'synthetic-case', 'another-case', CASE + '-2'):
                with self.subTest(declared=declared):
                    with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CASE_MISMATCH$'):
                        self.invoke(transport, case=declared)
            start.assert_not_called()
        self.assertIsNone(transport.last_receipt)
        self.assertFalse((self.root / 'declared-allowance').exists())
        # Nothing was reserved by the refusals: the declared call still spends attempt 1 of 1.
        self.invoke(transport, case=CASE)
        self.assertEqual(1, transport.last_receipt['attempt'])
        # The reverse holds: a fictional configuration refuses a declared other case.
        fictional = FakeTransport(config(), self.root / 'mislabelled-allowance')
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CASE_MISMATCH$'):
            self.invoke(fictional, case=CASE)
        self.assertIsNone(fictional.last_receipt)
        self.assertFalse((self.root / 'mislabelled-allowance').exists())

    # -- replay alert cases (approved 2026-10-18): `alert-<24 hex>` only ------------------------

    def test_an_alert_case_is_accepted_and_bound_to_the_company_copy_permission(self):
        alert = 'alert-' + '0123456789abcdef01234567'
        self.assertEqual(alert, config(permitted_case=alert).permitted_case)
        self.assertEqual(config(permitted_case=alert), LiveConfig.from_dict(config(permitted_case=alert).as_dict()))
        transport = FakeTransport(config(permitted_case=alert), self.root / 'alert-allowance',
            permission_root=self.permission_root())
        self.invoke(transport, case=alert)
        self.assertEqual((alert, PERMISSION), (transport.last_receipt['permitted_case'],
            transport.last_receipt['permission_ref']))
        self.assertNotIn(KEY, json.dumps(transport.last_receipt))

    def test_malformed_alert_ids_and_other_ids_are_refused(self):
        for value in ('alert-', 'alert-' + 'a' * 23, 'alert-' + 'a' * 25, 'alert-' + 'A' * 24,
                'alert-' + 'g' * 24, 'Alert-' + 'a' * 24, 'alerts-' + 'a' * 24, 'x-alert-' + 'a' * 24,
                'alert-' + 'a' * 24 + '\n', ' alert-' + 'a' * 24, 'alert_' + 'a' * 24,
                'alert-' + 'a' * 12 + '/' + 'a' * 11, 'event-' + 'a' * 24, 'a' * 24):
            with self.subTest(permitted_case=value):
                with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
                    config(permitted_case=value)

    def test_an_alert_case_still_refuses_a_case_mismatch_and_an_unsigned_record(self):
        alert, other = 'alert-' + 'a' * 24, 'alert-' + 'b' * 24
        transport = FakeTransport(config(permitted_case=alert), self.root / 'alert-mismatch',
            permission_root=self.permission_root())
        with patch.object(transport, '_start_worker') as start:
            for declared in (None, 'synthetic-case', CASE, other):
                with self.subTest(declared=declared):
                    with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CASE_MISMATCH$'):
                        self.invoke(transport, case=declared)
            start.assert_not_called()
        self.assertIsNone(transport.last_receipt)
        unsigned = FakeTransport(config(permitted_case=alert), self.root / 'alert-unsigned',
            permission_root=self.permission_root(status='draft'))
        with patch.object(unsigned, '_start_worker') as start:
            with self.assertRaises(JudgmentUnavailable):
                self.invoke(unsigned, case=alert)
            start.assert_not_called()

    # -- absent, unsigned and revoked records --------------------------------------------------

    def test_absent_unsigned_and_revoked_records_refuse_before_outbound_inference(self):
        records = ((self.permission_root(present=False), 'no-record-at-all'),
                   (self.permission_root(status='draft'), 'draft'),
                   (self.permission_root(status='revoked'), 'revoked'),
                   (self.permission_root(status='withdrawn'), 'withdrawn'),
                   (self.permission_root(status=None), 'no-status-line'),
                   (self.permission_root(identifier='perm:another:2026-10-13'), 'another-identifier'))
        for root, label in records:
            with self.subTest(record=label):
                ledger = 'allowance-%s' % label
                transport = FakeTransport(config(permitted_case=CASE), self.root / ledger,
                    permission_root=root)
                with patch.object(transport, '_start_worker') as start:
                    with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_PERMISSION_UNAVAILABLE$'):
                        self.invoke(transport, case=CASE)
                    start.assert_not_called()
                self.assertIsNone(transport.last_receipt)
                self.assertFalse((self.root / ledger).exists())
        # Signed, the same scratch root serves the call: the record's state is the difference.
        signed = self.permission_root()
        transport = FakeTransport(config(permitted_case=CASE), self.root / 'allowance-signed',
            permission_root=signed)
        self.invoke(transport, case=CASE)
        self.assertEqual(PERMISSION, transport.last_receipt['permission_ref'])

    # -- the bounds the gate must not displace ------------------------------------------------

    def test_the_budgets_and_refusals_are_unchanged_for_an_authorized_real_case(self):
        transport = FakeTransport(config(permitted_case=CASE), self.root / 'budget-allowance',
            permission_root=self.permission_root())
        self.invoke(transport, case=CASE)
        self.assertEqual(1, transport.last_receipt['attempt'])
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_ATTEMPT_LIMIT$'):
            self.invoke(transport, case=CASE)
        ledger = self.root / 'budget-allowance'
        self.assertTrue(ledger.exists())
        self.assertNotIn(KEY.encode(), ledger.read_bytes())
        # The request-byte bound and the credential bound still refuse before any attempt.
        oversized = FakeTransport(config(permitted_case=CASE, max_request_bytes=100),
            self.root / 'oversized-allowance', permission_root=self.permission_root())
        with patch.object(oversized, '_start_worker') as start:
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_INPUT_LIMIT$'):
                self.invoke(oversized, case=CASE)
            start.assert_not_called()
        self.assertFalse((self.root / 'oversized-allowance').exists())
        # The credential bound still refuses before any attempt, as it does for the fictional case.
        credentialless = FakeTransport(config(permitted_case=CASE),
            self.root / 'credential-allowance', permission_root=self.permission_root())
        for missing in ('', 'secret\r\nHost:evil'):
            with self.subTest(credential=missing), patch.dict(os.environ, {'PERMISSION_TEST_KEY': missing}):
                with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CREDENTIAL_MISSING$'):
                    self.invoke(credentialless, case=CASE)
        self.assertIsNone(credentialless.last_receipt)
        self.assertFalse((self.root / 'credential-allowance').exists())

    # -- the callers that compile a case ------------------------------------------------------

    def test_the_provider_declares_the_case_and_a_silent_caller_is_refused(self):
        declaring = FakeTransport(config(permitted_case=CASE), self.root / 'provider-allowance',
            permission_root=self.permission_root())
        provider = GeminiProvider('gemini-fixture', declaring, execution_mode='synthetic_fixture', case=CASE)
        self.assertEqual('synthetic-permission-fixture.v1', provider.generate('synthetic prompt')['model_version'])
        self.assertEqual(PERMISSION, declaring.last_receipt['permission_ref'])
        silent = FakeTransport(config(permitted_case=CASE), self.root / 'silent-provider',
            permission_root=self.permission_root())
        with patch.object(silent, '_start_worker') as start:
            with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CASE_MISMATCH$'):
                GeminiProvider('gemini-fixture', silent, execution_mode='synthetic_fixture').generate('prompt')
            start.assert_not_called()
        for invalid in ('', 7, True, 'x' * 81):
            with self.subTest(case=invalid):
                with self.assertRaises(ValueError):
                    GeminiProvider('gemini-fixture', declaring, execution_mode='synthetic_fixture', case=invalid)

    def test_the_fictional_runner_refuses_a_real_case_configuration(self):
        runs = self.root / 'runs'
        with self.assertRaisesRegex(JudgmentUnavailable, '^MODEL_CONFIG_INVALID$'):
            run_case(config(permitted_case=CASE), runs)
        self.assertFalse(runs.exists())


class PermissionRecordTests(unittest.TestCase):
    """The transport's reading of the records, against the repository registry it must not widen."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-permission-records-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        directory = self.root.joinpath('docs', 'work', 'permissions')
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(text, encoding='utf-8')

    def test_the_transport_reading_is_a_strict_subset_of_the_repository_registry(self):
        # The checkout's own record is a live grant in both readings.
        self.assertIn(PERMISSION, signed_permissions(ROOT))
        self.assertTrue(signed_permissions(ROOT) <= load_permissions(ROOT))
        # A revocation is a grant to the registry (any status but the draft marker) and no
        # grant to the transport, which authorizes transmission and reads affirmatively.
        self.write('revoked.md', record_text(status='revoked'))
        self.assertIn(PERMISSION, load_permissions(self.root))
        self.assertNotIn(PERMISSION, signed_permissions(self.root))
        # A draft is no grant in either reading.
        self.write('revoked.md', record_text(status='draft'))
        self.assertEqual(frozenset(), signed_permissions(self.root))

    def test_the_allowlist_entry_is_the_cases_own_binding(self):
        # The allowlisted case is the real case, and its permission is the record the case's
        # own fixture cites: the table cannot drift from the fixture without failing here.
        fixture = json.loads((ROOT / 'tests/fixtures/pedc-u2-2026-09-21/case.json').read_text(encoding='utf-8'))
        self.assertEqual({fixture['case_id']: fixture['permission_ref']}, dict(REAL_CASE_ALLOWLIST))
        record = (ROOT / 'docs/work/permissions/2026-10-13-wesm-company-copy.md').read_text(encoding='utf-8')
        self.assertIn(fixture['permission_ref'], record)


if __name__ == '__main__':
    unittest.main()
