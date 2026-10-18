"""The agent store (DOCK-3): the records of the agent contract, section 3, on the memory store.

Threads are one per (owner, case); turns are created once and have no update path; drafts and
confirmations are decided once; the day's budget is charged all or nothing and never past the line;
owners are digests of the uid, never an email. The Firestore store is checked for its shape only
(the same method set, collections under the private namespace prefixed `agent_`, the lazy imports),
since the offline suite has no Firestore client.
"""
import ast
import inspect
import unittest
from pathlib import Path

from src.agent import store as store_module
from src.agent.budget import BUDGET_EXHAUSTED, BUDGET_UNAVAILABLE, DayMeter, manila_day
from src.agent.store import (AlreadyDecided, FirestoreAgentStore, MemoryAgentStore, RecordExists,
                             StoreUnavailable, UnknownRecord, owner_id, thread_id)

ROOT = Path(__file__).resolve().parents[1]
EMAIL = 'someone@example.com'


def confirmation(cid='c1', owner='o1'):
    return {'confirmation_id': cid, 'owner': owner, 'action': 'mark_stale',
            'args': {'assumption_id': 'avail:x', 'revision': 'abcdef1'}, 'preview': {'writes': 'StaleMark'},
            'state': 'pending', 'decided_at': None}


class OwnerAndThreadTests(unittest.TestCase):
    def test_owner_is_a_digest_of_the_uid_never_the_email(self):
        owner = owner_id('uid-123')
        self.assertRegex(owner, r'^[0-9a-f]{32}$')
        self.assertNotIn('uid-123', owner)
        self.assertEqual(owner, owner_id('uid-123'))
        self.assertNotEqual(owner, owner_id('uid-124'))
        with self.assertRaises(ValueError):
            owner_id('')

    def test_one_desk_thread_per_owner_and_one_per_case(self):
        store = MemoryAgentStore()
        desk = store.open_thread('o1', 'desk', '2026-10-18T01:00:00+00:00')
        again = store.open_thread('o1', 'desk', '2026-10-18T02:00:00+00:00')
        case = store.open_thread('o1', 'case-syn-unit-trip', '2026-10-18T01:00:00+00:00')
        other = store.open_thread('o2', 'desk', '2026-10-18T01:00:00+00:00')
        self.assertEqual(desk['thread_id'], again['thread_id'])
        self.assertEqual(again['created_at'], '2026-10-18T01:00:00+00:00')
        self.assertEqual(desk['thread_id'], thread_id('o1', 'desk'))
        self.assertEqual(len({desk['thread_id'], case['thread_id'], other['thread_id']}), 3)
        self.assertEqual(sorted(t['case_ref'] for t in store.threads('o1')), ['case-syn-unit-trip', 'desk'])
        self.assertEqual(set(desk), {'thread_id', 'owner', 'case_ref', 'created_at', 'turns'})


class TurnTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryAgentStore()
        self.thread = self.store.open_thread('o1', 'desk', '2026-10-18T01:00:00+00:00')

    def turn(self, key='t1'):
        return {'turn_id': key, 'thread_id': self.thread['thread_id'], 'at': '2026-10-18T01:00:00+00:00',
                'question': 'What is exposed?', 'receipt': None, 'actions_run': [],
                'confirmations_pending': [], 'budget': None}

    def test_turns_are_append_only(self):
        self.store.append_turn(self.turn('t1'))
        with self.assertRaises(RecordExists):
            self.store.append_turn(dict(self.turn('t1'), question='changed'))
        self.assertEqual(self.store.get_turn('t1')['question'], 'What is exposed?')
        self.store.append_turn(self.turn('t2'))
        self.assertEqual(self.store.get_thread(self.thread['thread_id'])['turns'], ['t1', 't2'])
        for name in dir(MemoryAgentStore):
            self.assertFalse(name.startswith(('update_turn', 'delete_turn', 'set_turn', 'replace_turn')), name)
        for name in dir(FirestoreAgentStore):
            self.assertFalse(name.startswith(('update_turn', 'delete_turn', 'set_turn', 'replace_turn')), name)

    def test_a_turn_needs_its_thread(self):
        with self.assertRaises(UnknownRecord):
            self.store.append_turn(dict(self.turn(), thread_id='missing'))

    def test_a_returned_turn_is_a_copy(self):
        self.store.append_turn(self.turn('t1'))
        read = self.store.get_turn('t1')
        read['question'] = 'mutated'
        self.assertEqual(self.store.get_turn('t1')['question'], 'What is exposed?')


class DraftAndConfirmationTests(unittest.TestCase):
    def test_confirmation_is_created_exclusively_and_pending(self):
        store = MemoryAgentStore()
        store.create_confirmation(confirmation())
        with self.assertRaises(RecordExists):
            store.create_confirmation(confirmation())
        with self.assertRaises(ValueError):
            store.create_confirmation(dict(confirmation('c2'), state='confirmed'))
        with self.assertRaises(ValueError):
            store.create_confirmation(dict(confirmation('c3'), decided_at='2026-10-18T01:00:00+00:00'))
        self.assertIsNone(store.get_confirmation('c2'))

    def test_confirmation_is_decided_once(self):
        store = MemoryAgentStore()
        store.create_confirmation(confirmation())
        decided = store.decide_confirmation('c1', 'confirmed', '2026-10-18T01:00:00+00:00')
        self.assertEqual((decided['state'], decided['decided_at']), ('confirmed', '2026-10-18T01:00:00+00:00'))
        with self.assertRaises(AlreadyDecided):
            store.decide_confirmation('c1', 'declined', '2026-10-18T02:00:00+00:00')
        with self.assertRaises(ValueError):
            store.decide_confirmation('c1', 'pending', '2026-10-18T02:00:00+00:00')
        with self.assertRaises(UnknownRecord):
            store.decide_confirmation('nope', 'confirmed', '2026-10-18T02:00:00+00:00')
        self.assertEqual(set(decided), {'confirmation_id', 'owner', 'action', 'args', 'preview', 'state', 'decided_at'})

    def test_draft_settles_once(self):
        store = MemoryAgentStore()
        store.create_draft({'draft_id': 'd1', 'owner': 'o1', 'kind': 'case', 'body': {}, 'rests_on': [],
                            'created_at': '2026-10-18T01:00:00+00:00', 'state': 'draft'})
        self.assertEqual(store.settle_draft('d1', 'signed')['state'], 'signed')
        with self.assertRaises(AlreadyDecided):
            store.settle_draft('d1', 'discarded')
        with self.assertRaises(ValueError):
            store.settle_draft('d1', 'draft')
        self.assertEqual([d['draft_id'] for d in store.drafts('o1', state='signed')], ['d1'])
        self.assertEqual(store.drafts('o1', state='draft'), [])


class BudgetTests(unittest.TestCase):
    def test_manila_day_is_utc_plus_eight(self):
        self.assertEqual(manila_day('2026-10-18T15:59:59Z'), '2026-10-18')
        self.assertEqual(manila_day('2026-10-18T16:00:00Z'), '2026-10-19')
        self.assertEqual(manila_day('2026-10-19T00:30:00+08:00'), '2026-10-19')
        with self.assertRaises(ValueError):
            manila_day('2026-10-18T16:00:00')

    def test_the_meter_refuses_past_the_line_as_an_outcome(self):
        store = MemoryAgentStore()
        meter = DayMeter(store, line_usd=0.1, per_call_usd=0.02, clock=lambda: '2026-10-18T01:00:00Z')
        first = meter.charge(4)
        self.assertEqual((first['outcome'], first['calls'], first['usd_estimate']), ('allowed', 4, 0.08))
        refused = meter.charge(4)
        self.assertEqual((refused['outcome'], refused['reason_key']), ('refused', BUDGET_EXHAUSTED))
        self.assertEqual((refused['calls'], refused['usd_estimate']), (4, 0.08))
        one = meter.charge(1)
        self.assertEqual((one['outcome'], one['calls'], one['usd_estimate']), ('allowed', 5, 0.1))
        self.assertEqual(meter.charge(1)['outcome'], 'refused')
        self.assertEqual(store.get_budget('2026-10-18'), {'day': '2026-10-18', 'calls': 5, 'usd_estimate': 0.1})
        self.assertEqual(meter.today()['reason_key'], BUDGET_EXHAUSTED)

    def test_a_new_manila_day_starts_a_new_line(self):
        store = MemoryAgentStore()
        now = ['2026-10-18T15:00:00Z']
        meter = DayMeter(store, line_usd=0.02, per_call_usd=0.02, clock=lambda: now[0])
        self.assertEqual(meter.charge(1)['outcome'], 'allowed')
        self.assertEqual(meter.charge(1)['outcome'], 'refused')
        now[0] = '2026-10-18T16:00:00Z'
        self.assertEqual(meter.charge(1)['day'], '2026-10-19')
        self.assertEqual(store.get_budget('2026-10-19')['calls'], 1)

    def test_the_default_line_is_about_five_dollars(self):
        meter = DayMeter(MemoryAgentStore())
        self.assertEqual(meter.line_usd, 5.0)

    def test_an_unreachable_store_is_a_refusal_never_an_exception(self):
        class Down(MemoryAgentStore):
            def charge_budget(self, *args):
                raise StoreUnavailable()

            def get_budget(self, day):
                raise StoreUnavailable()
        meter = DayMeter(Down(), clock=lambda: '2026-10-18T01:00:00Z')
        self.assertEqual(meter.charge(3)['reason_key'], BUDGET_UNAVAILABLE)
        self.assertEqual(meter.today()['reason_key'], BUDGET_UNAVAILABLE)


class FirestoreShapeTests(unittest.TestCase):
    def test_both_stores_have_the_same_interface(self):
        def public(cls):
            return {n for n, _ in inspect.getmembers(cls, inspect.isfunction) if not n.startswith('_')}
        self.assertEqual(public(MemoryAgentStore), public(FirestoreAgentStore))

    def test_collections_sit_under_the_private_namespace_prefixed_agent(self):
        class Ref:
            def __init__(self, path):
                self.path = path

            def collection(self, name):
                return Ref(self.path + ['c:' + name])

            def document(self, name):
                return Ref(self.path + ['d:' + name])
        store = FirestoreAgentStore(Ref([]), 'ns-1')
        self.assertEqual(store._col('threads').path, ['c:h1_namespaces', 'd:ns-1', 'c:agent_threads'])
        self.assertTrue(all(c.isidentifier() for c in store_module.COLLECTIONS))

    def test_google_modules_are_imported_lazily(self):
        tree = ast.parse((ROOT / 'src/agent/store.py').read_text(encoding='utf-8'))
        top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = [a.name for n in top for a in n.names] + [n.module or '' for n in top if isinstance(n, ast.ImportFrom)]
        self.assertFalse([n for n in names if n.startswith('google')])

    def test_no_email_reaches_a_stored_document(self):
        store = MemoryAgentStore()
        owner = owner_id('uid-1')
        store.open_thread(owner, 'desk', '2026-10-18T01:00:00+00:00')
        self.assertNotIn(EMAIL, repr(store._docs))
        self.assertNotIn('uid-1', repr(store._docs))


if __name__ == '__main__':
    unittest.main()
