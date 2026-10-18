"""M3 persistence/API tests using real local Auth and Firestore emulators."""
import json
import unittest
from unittest.mock import Mock
from fastapi.testclient import TestClient
import test_h1 as h1
# PERF-2 owns tests/test_demo_session_batch.py. A module that another module imports is not
# collected by itself, so its emulator class is bound into this file — the only integration
# file the task's paths reach (scripts/h1/test.sh discovers tests/integration) — and runs
# here against the Firestore emulator. It skips itself when no emulator is configured.
import test_demo_session_batch as perf2
SessionProvisioningOnEmulators = perf2.SessionProvisioningOnEmulators
# PERF-3 owns tests/test_event_prepare.py, for the same reason: its emulator class runs the
# additive `POST .../prepare` endpoint through the hosted store and the real application, and
# this is the only integration file the task's paths reach.
import test_event_prepare as perf3
DecisionPreparationOnEmulators = perf3.DecisionPreparationOnEmulators
import test_judgment as j
from src.api import create_app
from src.judgment import JudgmentService
from src.review import reference


class M3Integration(unittest.TestCase):
    def setUp(self):
        self.f=h1.H1HTTP(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.task=self.f.task()
        self.provider=j.provider(self.task)
        self.service=JudgmentService(self.provider)
        self.client=TestClient(create_app(self.f.repo,self.f.identity,self.f.clock,judgment=self.service))
        self.addCleanup(self.client.close)
        self.body={'task_ref':reference(self.task),'idempotency_key':'judgment-a'}

    def post(self,path,body):
        return self.client.post(self.f.url+path,json=body,headers=self.f.headers)

    def test_judgment_restart_replay_and_workspace_projection(self):
        before=self.f.repo.heads(self.f.actor,self.f.case)
        saved=self.post('/judgments',self.body)
        self.assertEqual(200,saved.status_code,saved.text)
        restarted=TestClient(create_app(self.f.connection(),self.f.identity,self.f.clock))
        self.addCleanup(restarted.close)
        replay=restarted.post(self.f.url+'/judgments',json=self.body,headers=self.f.headers)
        self.assertEqual(saved.json(),replay.json())
        self.provider.generate.assert_called_once()
        projection=restarted.get(self.f.url+'/workspace',headers=self.f.headers)
        self.assertEqual(200,projection.status_code)
        self.assertEqual([saved.json()],projection.json()['judgments'])
        self.assertFalse(projection.json()['model_available'])
        self.assertEqual(before,projection.json()['heads'])
        self.assertEqual('no-store',projection.headers['cache-control'])
        self.assertIn("frame-ancestors 'none'",projection.headers['content-security-policy'])

    def test_revocation_during_inference_has_no_persisted_result(self):
        def revoke(prompt):
            self.f.repo.store.member_ref(self.f.actor.actor_id,self.f.actor.tenant_id,self.f.case).update({'source_policy_refs':[]})
            return {'text':json.dumps(j.answer(self.task)),'model_version':'synthetic-v1'}
        self.provider.generate.side_effect=revoke
        result=self.post('/judgments',self.body)
        self.assertEqual((404,{'code':'NOT_FOUND'}),(result.status_code,result.json()))
        self.f.repo.store.member_ref(self.f.actor.actor_id,self.f.actor.tenant_id,self.f.case).update({'source_policy_refs':['synthetic-public','synthetic-private']})
        self.assertEqual([],self.f.repo.workspace(self.f.actor,self.f.case)['judgments'])

    def test_storage_retry_does_not_repeat_provider(self):
        from src.review.storage import RetryPreparation
        original=self.f.repo.store.commit
        calls=[]
        def retry(actor,case,before,after):
            if any('JudgmentArtifact' in key for key in after) and not calls:
                calls.append(1);raise RetryPreparation()
            return original(actor,case,before,after)
        self.f.repo.store.commit=retry
        result=self.post('/judgments',self.body)
        self.assertEqual(200,result.status_code,result.text)
        self.provider.generate.assert_called_once()
        self.assertEqual(1,len(self.f.repo.workspace(self.f.actor,self.f.case)['judgments']))

    def test_invalid_ai_then_manual_review_and_authority_fields(self):
        self.provider.generate.return_value={'text':'{"approved":true}','model_version':'fixture'}
        invalid=self.post('/judgments',self.body)
        self.assertEqual((503,{'code':'MODEL_INVALID_RESPONSE'}),(invalid.status_code,invalid.json()))
        self.assertEqual(422,self.post('/judgments',dict(self.body,actor_id='admin')).status_code)
        self.assertEqual(200,self.post('/reviews',self.f.body()).status_code)
        self.assertEqual(1,len(self.f.repo.history(self.f.actor,self.f.case)))

    def test_assets_session_denial_and_private_projection(self):
        page=self.client.get('/')
        self.assertEqual(200,page.status_code)
        self.assertIn('InGRID · Philippine grid',page.text)
        self.assertNotIn('SYNTHETIC WALKTHROUGH',page.text)
        desk=self.client.get('/desk')
        self.assertEqual(200,desk.status_code)
        self.assertIn('SYNTHETIC WALKTHROUGH',desk.text)
        self.assertEqual(200,self.client.get('/assets/app.js').status_code)
        self.assertEqual(404,self.client.get('/assets/private.json').status_code)
        self.assertEqual(401,self.client.get(self.f.url+'/workspace').status_code)
        failed=self.client.post('/session',json={'email':'missing@example.test','password':'wrong'})
        self.assertEqual((401,{'code':'UNAUTHENTICATED'}),(failed.status_code,failed.json()))
        self.f.repo.store.member_ref(self.f.actor.actor_id,self.f.actor.tenant_id,self.f.case).update({'active':False})
        self.assertEqual(404,self.client.get(self.f.url+'/workspace',headers=self.f.headers).status_code)
