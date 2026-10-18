"""Synthetic judgment boundary counterexamples; no provider or network execution."""
import copy
import json
import unittest
from unittest.mock import Mock
from dataclasses import replace

from src.adapters.gemini import GeminiProvider
from src.demo import seed, AT
from src.review import InMemoryRepository, reference, ReviewError
from src.judgment import JudgmentService, JudgmentUnavailable

NOW='2026-10-05T02:00:00Z'


def answer(task):
    return {'label':'challenges','explanation':'Testing is not confirmed commercial availability.',
        'citations':[{'passage_index':0,'quote':task['payload']['context'][0]['quote']}],
        'alternatives':['Testing may finish before the operating day.'],'unknowns':['Commercial availability remains unconfirmed.']}


def provider(task):
    p=Mock(name='synthetic provider')
    p.name='gemini';p.model='gemini-fixture';p.execution_mode='synthetic_fixture'
    p.generate.return_value={'text':json.dumps(answer(task)),'model_version':'synthetic-contract.v1'}
    return p


class JudgmentTests(unittest.TestCase):
    def setUp(self):
        self.repo=InMemoryRepository();self.seed=seed(self.repo);self.actor=self.seed['actor'];self.case=next(iter(self.actor.accessible_cases))
        snapshot=self.repo.build_snapshot(self.actor,self.case,NOW,NOW)
        self.task=self.repo.compile_task(self.actor,self.case,reference(snapshot),'capacity-assumption',NOW,NOW)
        self.provider=provider(self.task);self.service=JudgmentService(self.provider)

    def generate(self,key='a',task=None):
        return self.service.generate(self.repo,self.actor,self.case,reference(task or self.task),key,lambda:NOW)

    def test_cited_proposal_replay_keeps_accepted_state_and_clock(self):
        heads=self.repo.heads(self.actor,self.case)
        result=self.generate()
        clock=Mock(side_effect=AssertionError('replay clock'))
        self.assertEqual(result,self.service.generate(self.repo,self.actor,self.case,reference(self.task),'a',clock))
        self.provider.generate.assert_called_once()
        self.assertEqual(heads,self.repo.heads(self.actor,self.case))
        self.assertEqual([],self.repo.history(self.actor,self.case))
        self.assertEqual('proposed',result['payload']['review_state'])
        prompt=json.loads(self.provider.generate.call_args.args[0])
        self.assertNotIn('access_scope',prompt)
        self.assertIn('lineage_groups',prompt)
        self.assertEqual(result,self.repo.read(self.actor,self.case,reference(result)))

    def test_invalid_responses_write_nothing_and_manual_review_remains(self):
        good=answer(self.task)
        forged=copy.deepcopy(good);forged['citations'][0]['quote']='invented source'
        authority=dict(good,approved=True)
        wrong=copy.deepcopy(good);wrong['citations'][0]['passage_index']=True
        for text in (json.dumps(forged),json.dumps(authority),json.dumps(wrong),'{"label":"supports","label":"mixed"}', 'x'*32769, 'not json'):
            self.provider.generate.return_value={'text':text,'model_version':'fixture'}
            with self.assertRaises(JudgmentUnavailable) as caught:self.generate()
            self.assertEqual('MODEL_INVALID_RESPONSE',caught.exception.code)
            self.assertEqual([],self.repo.workspace(self.actor,self.case)['judgments'])
        p=self.task['payload']
        self.repo.commit_review(self.actor,dict(case_id=self.case,request_id='manual',idempotency_key='manual',
            task_ref=reference(self.task),snapshot_digest=p['snapshot_ref']['content_digest'],expected_assumption_head=p['assumption_ref'],
            expected_outlook_head=None,disposition='retain',rationale='Manual review without AI',reviewed_at=NOW,recorded_at=NOW,new_value=None))
        self.assertEqual(1,len(self.repo.history(self.actor,self.case)))

    def test_blocked_and_stale_tasks_never_invoke_provider(self):
        snapshot=self.repo.build_snapshot(self.actor,self.case,NOW,NOW)
        blocked=self.repo.compile_task(self.actor,self.case,reference(snapshot),'capacity-assumption','2026-09-01T00:00:00Z',NOW)
        with self.assertRaises(ReviewError):self.generate(task=blocked)
        mapping=copy.deepcopy(self.seed['mapping'])
        from src.review import make_record
        newer=make_record('MappingRevision',self.actor.tenant_id,self.case,mapping['record_id'],'2',NOW,mapping['payload'])
        self.repo.register(self.actor,newer)
        with self.assertRaises(ReviewError):self.generate()
        self.provider.generate.assert_not_called()

    def test_dependency_change_during_provider_call_rejects_commit(self):
        from src.review import make_record
        def change(prompt):
            m=self.seed['mapping'];self.repo.register(self.actor,make_record('MappingRevision',self.actor.tenant_id,self.case,m['record_id'],'2',NOW,m['payload']))
            return {'text':json.dumps(answer(self.task)),'model_version':'fixture'}
        self.provider.generate.side_effect=change
        with self.assertRaises(ReviewError) as caught:self.generate()
        self.assertEqual('STALE_DEPENDENCY',caught.exception.code)
        self.assertEqual([],self.repo.workspace(self.actor,self.case)['judgments'])

    def test_saved_judgment_source_revocation_and_other_actor_denied(self):
        result=self.generate()
        revoked=replace(self.actor,source_policy_refs=frozenset())
        with self.assertRaises(ReviewError):self.repo.read(revoked,self.case,reference(result))
        with self.assertRaises(ReviewError):self.service.generate(self.repo,revoked,self.case,reference(self.task),'a',lambda:NOW)
        with self.assertRaises(ReviewError):self.service.generate(self.repo,replace(self.actor,actor_id='other'),self.case,reference(self.task),'b',lambda:NOW)
        self.provider.generate.assert_called_once()

    def test_provider_failure_disabled_and_busy_have_no_writes(self):
        self.provider.generate.side_effect=TimeoutError('private details')
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_UNAVAILABLE$'):self.generate()
        with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_DISABLED$'):
            JudgmentService().generate(self.repo,self.actor,self.case,reference(self.task),'b',lambda:NOW)
        self.service.slots.acquire()
        try:
            with self.assertRaisesRegex(JudgmentUnavailable,'^MODEL_BUSY$'):self.generate()
        finally:self.service.slots.release()
        self.assertEqual([],self.repo.workspace(self.actor,self.case)['judgments'])

    def test_changed_task_under_same_key_conflicts(self):
        self.generate()
        snapshot=self.repo.build_snapshot(self.actor,self.case,NOW,NOW)
        other=self.repo.compile_task(self.actor,self.case,reference(snapshot),'capacity-assumption',AT,NOW)
        with self.assertRaises(ReviewError) as caught:self.generate(task=other)
        self.assertEqual('IDEMPOTENCY_CONFLICT',caught.exception.code)
        self.provider.generate.assert_called_once()

    def test_gemini_transport_contract_and_truncation(self):
        response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(answer(self.task))}]}}], 'modelVersion':'fixture-version'}
        transport=Mock(return_value=response)
        adapter=GeminiProvider('gemini-fixture',transport,execution_mode='synthetic_fixture')
        result=adapter.generate('bounded task')
        self.assertEqual('fixture-version',result['model_version'])
        model,body=transport.call_args.args
        self.assertEqual('gemini-fixture',model)
        self.assertNotIn('tools',body)
        self.assertEqual(2048,body['generationConfig']['maxOutputTokens'])
        self.assertEqual(30,transport.call_args.kwargs['timeout_seconds'])
        for parts,finish in (([{'functionCall':{}}],'STOP'),([{'text':'partial'}],'MAX_TOKENS'),([], 'STOP')):
            transport.return_value={'candidates':[{'finishReason':finish,'content':{'parts':parts}}],'modelVersion':'fixture'}
            with self.assertRaises(JudgmentUnavailable):adapter.generate('bounded task')

if __name__=='__main__':unittest.main()
