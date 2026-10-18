"""Local TLS wire checks; ephemeral synthetic certificates, no Google requests.

Uses cryptography from the existing H1 lockfile. Production destination cannot be changed
through configuration; only this subprocess fixture substitutes a local TLS connection.
"""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.adapters.gemini.run import run_case
from src.adapters.gemini.transport import DeveloperAPITransport, LiveConfig
from src.judgment import JudgmentUnavailable


class WireTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-gemini-tls-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'synthetic-local-fixture')])
        at = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(at-timedelta(minutes=5)).not_valid_after(at+timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
            .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256()))
        pem = self.root/'synthetic-cert.pem'
        pem.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path = self.root/'synthetic-key.pem'
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        key_path.chmod(0o600)
        self.mode = 'success'
        self.seen = []
        self.stop = Event()
        owner = self
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self,*args):
                pass
            def do_POST(self):
                self.close_connection = True
                try:
                    raw=self.rfile.read(int(self.headers['Content-Length']))
                    owner.seen.append((self.path,dict(self.headers),json.loads(raw)))
                    if owner.mode=='slow_headers':
                        self.wfile.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n')
                        self.wfile.flush();owner.stop.wait(3);return
                    if owner.mode=='redirect':
                        self.send_response(307);self.send_header('Location','https://untrusted.invalid/')
                        self.send_header('Content-Length','0');self.end_headers();return
                    if owner.mode=='oversize':
                        self.send_response(200);self.send_header('Content-Type','application/json')
                        self.send_header('Connection','close');self.end_headers()
                        self.wfile.write(b'x'*200);return
                    prompt=json.loads(json.loads(raw)['contents'][0]['parts'][0]['text'])
                    answer={'label':'challenges','explanation':'Commercial availability remains unconfirmed.',
                        'citations':[{'passage_index':0,'quote':prompt['context'][0]['quote']}],
                        'alternatives':['Testing may conclude later.'],'unknowns':['Commercial availability is unknown.']}
                    response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(answer)}]}}],
                        'modelVersion':'synthetic-tls.v1','responseId':'synthetic-tls-response'}
                    data=json.dumps(response).encode()
                    self.send_response(200);self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(data)));self.end_headers()
                    if owner.mode=='slow_body':
                        self.wfile.write(data[:1]);self.wfile.flush();owner.stop.wait(3)
                    self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError,ssl.SSLError):
                    pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(pem,key_path)
        self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.port=self.server.server_address[1]
        self.pem=pem

    def close_server(self):
        self.stop.set();self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

    def config(self,run_id='wire',timeout=3,cap=65536):
        return LiveConfig(project='synthetic-project',model='gemini-fixture',credential_env='M3_WIRE_TEST_KEY',
            authorization_ref='synthetic-wire-test-only',run_id=run_id,permitted_case='synthetic-case',
            budget_policy='request_and_token_limits',api_version='v1beta',location='global',max_attempts=1,
            timeout_seconds=timeout,max_request_bytes=196608,max_response_bytes=cap,max_output_tokens=2048)

    def factory(self,*,trust=True):
        owner=self
        class LocalTLS(DeveloperAPITransport):
            def _start_worker(self):
                program=f'''
import json,sys
from types import SimpleNamespace
from src.adapters.gemini import worker
original=worker.http.client.HTTPSConnection
def local(host,**kwargs):
    assert host==worker.HOST
    if {trust!r}: kwargs['context'].load_verify_locations(cafile={str(owner.pem)!r})
    return original('127.0.0.1',port={owner.port},**kwargs)
worker.http=SimpleNamespace(client=SimpleNamespace(HTTPSConnection=local,IncompleteRead=worker.http.client.IncompleteRead))
try:
    result=worker.request(json.load(sys.stdin))
except Exception:
    result={{'code':'MODEL_UNAVAILABLE'}}
sys.stdout.write(json.dumps(result))
'''
                return subprocess.Popen([sys.executable,'-c',program],stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        return LocalTLS

    def run_case(self,**kwargs):
        with patch.dict('os.environ',{'M3_WIRE_TEST_KEY':'synthetic-wire-key-never-real'}):
            return run_case(kwargs.pop('config',self.config()),self.root/'runs',
                transport_factory=kwargs.pop('factory',self.factory()),execution_mode='synthetic_fixture',
                clock=lambda:'2026-10-06T01:00:00Z',**kwargs)

    def test_actual_local_tls_request_and_validated_cited_result(self):
        result=self.run_case()
        self.assertEqual('synthetic-tls-response',result['transport']['response_id'])
        self.assertEqual(1,len(self.seen))
        path,headers,body=self.seen[0]
        self.assertEqual('/v1beta/models/gemini-fixture:generateContent',path)
        self.assertNotIn('key=',path)
        self.assertEqual('synthetic-wire-key-never-real',headers['x-goog-api-key'])
        self.assertEqual(1,body['generationConfig']['candidateCount'])
        self.assertEqual('proposed',result['judgment']['payload']['review_state'])

    def test_deadline_includes_slow_headers_and_body_and_consumes_attempt(self):
        for mode in ('slow_headers','slow_body'):
            self.mode=mode
            config=self.config(run_id=mode,timeout=.4)
            at=time.monotonic()
            with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_TIMEOUT$'):
                self.run_case(config=config)
            self.assertLess(time.monotonic()-at,2)
            with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_ATTEMPT_LIMIT$'):
                self.run_case(config=config)
        self.assertEqual(2,len(self.seen))

    def test_real_wire_missing_length_response_cap_and_redirect(self):
        self.mode='oversize'
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_RESPONSE_LIMIT$'):
            self.run_case(config=self.config('oversize',cap=100))
        self.mode='redirect'
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_UNAVAILABLE$'):
            self.run_case(config=self.config('redirect'))
        self.assertEqual(2,len(self.seen))

    def test_untrusted_tls_certificate_is_rejected_before_http_request(self):
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_UNAVAILABLE$'):
            self.run_case(factory=self.factory(trust=False))
        self.assertEqual([],self.seen)


if __name__=='__main__':
    unittest.main()
