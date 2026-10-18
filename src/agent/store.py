"""Where the agent's records live: threads, turns, drafts, confirmations, budget days, receipts.

Hosted: Firestore under the private namespace's root (`h1_namespaces/<namespace>`), collections
prefixed `agent_`, exactly as the alerts store keeps its own under `alerts_`. Demo mode and the tests
use `MemoryAgentStore`, which keeps the same rules in process.

The records are contract section 3 (docs/work/desk-agent-and-book-2026-10-18/agent-contract.md):

* thread `{thread_id, owner, case_ref, created_at, turns}`: the id is a digest of (owner, case_ref),
  so one desk thread per owner and one thread per case the owner opened is an exclusive create;
* turn `{turn_id, thread_id, at, question, receipt, actions_run, confirmations_pending, budget}`:
  created once, never updated; there is no update or delete method for a turn;
* draft `{draft_id, owner, kind, body, rests_on, created_at, state}`: state moves once, from
  `draft` to `signed` or `discarded`;
* confirmation `{confirmation_id, owner, action, args, preview, state, decided_at}`: created
  exclusively in state `pending`; decided once, to `confirmed` or `declined`, in one transaction;
* budget `{day, calls, usd_estimate}` per Manila day: charged in one transaction, never past the line;
* action receipt `{receipt_id, owner, thread_id, action, args, started_at, ended_at, outcome,
  record_refs, confirmation_id}`: append-only (the three envelope fields name where it belongs);
* evidence `{receipt_id, owner, receipt}`: a search receipt saved into the private copy.

Owners are digests of the sign-in uid (`owner_id`), never an email. Nothing here logs.
"""
import copy
import hashlib
from threading import RLock

COLLECTIONS = ('threads', 'turns', 'drafts', 'confirmations', 'budget', 'receipts', 'evidence')
PREFIX = 'agent_'
DRAFT_STATES = ('draft', 'signed', 'discarded')
CONFIRMATION_STATES = ('pending', 'confirmed', 'declined')


class StoreUnavailable(Exception):
    """Firestore could not be reached or refused the write; the route answers 503."""


class RecordExists(Exception):
    """A record that is created once already existed: never overwritten."""


class AlreadyDecided(Exception):
    """A confirmation or a draft was already decided: a decision is made once."""


class UnknownRecord(Exception):
    """No record with that id (or not the caller's)."""


def owner_id(uid):
    """The owner key of a signed-in user: a digest of the uid, so no email or uid names a document."""
    if type(uid) is not str or not uid.strip():
        raise ValueError('a sign-in uid is required')
    return hashlib.sha256(('agent-owner|' + uid).encode('utf-8')).hexdigest()[:32]


def thread_id(owner, case_ref):
    """One thread per (owner, case): its id is the digest of the pair."""
    return hashlib.sha256((owner + '|' + case_ref).encode('utf-8')).hexdigest()[:32]


def _budget_after(doc, day, calls, usd, line):
    """`(allowed, new_doc)` for one charge of `calls` costing `usd` against a day's line (all or nothing)."""
    doc = doc or {'day': day, 'calls': 0, 'usd_estimate': 0.0}
    total = round(doc['usd_estimate'] + usd, 6)
    if total > line + 1e-9:
        return False, doc
    return True, {'day': day, 'calls': doc['calls'] + calls, 'usd_estimate': total}


class MemoryAgentStore:
    def __init__(self):
        self._lock = RLock()
        self._docs = {name: {} for name in COLLECTIONS}

    def _get(self, kind, key):
        with self._lock:
            return copy.deepcopy(self._docs[kind].get(key))

    def _create(self, kind, key, doc):
        with self._lock:
            if key in self._docs[kind]:
                raise RecordExists(kind)
            self._docs[kind][key] = copy.deepcopy(doc)
            return copy.deepcopy(doc)

    def _where(self, kind, **match):
        with self._lock:
            return [copy.deepcopy(d) for d in self._docs[kind].values()
                    if all(d.get(k) == v for k, v in match.items())]

    # threads and turns
    def open_thread(self, owner, case_ref, created_at):
        """The owner's thread for a case, created when absent (exclusive by its id)."""
        key = thread_id(owner, case_ref)
        with self._lock:
            if key not in self._docs['threads']:
                self._docs['threads'][key] = {'thread_id': key, 'owner': owner, 'case_ref': case_ref,
                                              'created_at': created_at, 'turns': []}
            return copy.deepcopy(self._docs['threads'][key])

    def get_thread(self, key):
        return self._get('threads', key)

    def threads(self, owner):
        return sorted(self._where('threads', owner=owner), key=lambda t: (t['created_at'], t['thread_id']))

    def append_turn(self, turn):
        """Create the turn once and add its id to its thread; a second turn with the id is refused."""
        with self._lock:
            thread = self._docs['threads'].get(turn['thread_id'])
            if thread is None:
                raise UnknownRecord('thread')
            self._create('turns', turn['turn_id'], turn)
            thread['turns'].append(turn['turn_id'])
            return copy.deepcopy(turn)

    def get_turn(self, key):
        return self._get('turns', key)

    def turns(self, key):
        """A thread's turns in the order they were appended."""
        order = {tid: i for i, tid in enumerate((self.get_thread(key) or {}).get('turns', []))}
        return sorted(self._where('turns', thread_id=key), key=lambda t: (order.get(t['turn_id'], len(order)), t['at']))

    # drafts
    def create_draft(self, draft):
        return self._create('drafts', draft['draft_id'], draft)

    def get_draft(self, key):
        return self._get('drafts', key)

    def drafts(self, owner, state=None):
        found = self._where('drafts', owner=owner) if state is None else self._where('drafts', owner=owner, state=state)
        return sorted(found, key=lambda d: (d['created_at'], d['draft_id']))

    def settle_draft(self, key, state):
        """`draft` -> `signed` | `discarded`, once."""
        if state not in DRAFT_STATES[1:]:
            raise ValueError(state)
        with self._lock:
            draft = self._docs['drafts'].get(key)
            if draft is None:
                raise UnknownRecord('draft')
            if draft['state'] != 'draft':
                raise AlreadyDecided('draft')
            draft['state'] = state
            return copy.deepcopy(draft)

    # confirmations
    def create_confirmation(self, doc):
        """Exclusive create in state `pending`; an existing id is refused (RecordExists)."""
        if doc.get('state') != 'pending' or doc.get('decided_at') is not None:
            raise ValueError('a confirmation is created pending')
        return self._create('confirmations', doc['confirmation_id'], doc)

    def get_confirmation(self, key):
        return self._get('confirmations', key)

    def confirmations(self, owner, state=None):
        found = (self._where('confirmations', owner=owner) if state is None
                 else self._where('confirmations', owner=owner, state=state))
        return sorted(found, key=lambda c: c['confirmation_id'])

    def decide_confirmation(self, key, state, decided_at):
        """`pending` -> `confirmed` | `declined`, once; the decided document is returned."""
        if state not in CONFIRMATION_STATES[1:]:
            raise ValueError(state)
        with self._lock:
            doc = self._docs['confirmations'].get(key)
            if doc is None:
                raise UnknownRecord('confirmation')
            if doc['state'] != 'pending':
                raise AlreadyDecided('confirmation')
            doc.update(state=state, decided_at=decided_at)
            return copy.deepcopy(doc)

    # budget
    def charge_budget(self, day, calls, usd, line):
        """`(allowed, day_doc)`: `calls` costing `usd` charged to the day unless they pass the line."""
        with self._lock:
            allowed, doc = _budget_after(self._docs['budget'].get(day), day, calls, usd, line)
            if allowed:
                self._docs['budget'][day] = doc
            return allowed, copy.deepcopy(doc)

    def get_budget(self, day):
        return self._get('budget', day)

    # receipts and evidence
    def add_receipt(self, receipt):
        return self._create('receipts', receipt['receipt_id'], receipt)

    def receipts(self, owner, confirmation_id=None):
        found = (self._where('receipts', owner=owner) if confirmation_id is None
                 else self._where('receipts', owner=owner, confirmation_id=confirmation_id))
        return sorted(found, key=lambda r: (r['started_at'], r['receipt_id']))

    def save_evidence(self, key, doc):
        return self._create('evidence', key, doc)

    def get_evidence(self, key):
        return self._get('evidence', key)


class FirestoreAgentStore:
    """The same interface over Firestore; imported only in hosted mode (needs google-cloud-firestore)."""

    def __init__(self, client, namespace):
        self.client = client
        self.root = client.collection('h1_namespaces').document(namespace)

    def _col(self, kind):
        return self.root.collection(PREFIX + kind)

    def _call(self, fn, *args):
        from google.api_core.exceptions import GoogleAPICallError, RetryError
        try:
            return fn(*args)
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StoreUnavailable() from exc

    def _create(self, kind, key, doc):
        from google.api_core.exceptions import AlreadyExists

        def write():
            try:
                self._col(kind).document(key).create(doc)
            except AlreadyExists:
                raise RecordExists(kind) from None
            return dict(doc)
        return self._call(write)

    def _get(self, kind, key):
        def read():
            snap = self._col(kind).document(key).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def _where(self, kind, **match):
        def read():
            query = self._col(kind)
            for field, value in match.items():
                query = query.where(field, '==', value)
            return [d.to_dict() for d in query.stream(timeout=10)]
        return self._call(read)

    def open_thread(self, owner, case_ref, created_at):
        from google.api_core.exceptions import AlreadyExists
        key = thread_id(owner, case_ref)
        doc = {'thread_id': key, 'owner': owner, 'case_ref': case_ref, 'created_at': created_at, 'turns': []}

        def write():
            try:
                self._col('threads').document(key).create(doc)
                return dict(doc)
            except AlreadyExists:
                return self._col('threads').document(key).get(timeout=10).to_dict()
        return self._call(write)

    def get_thread(self, key):
        return self._get('threads', key)

    def threads(self, owner):
        return sorted(self._where('threads', owner=owner), key=lambda t: (t['created_at'], t['thread_id']))

    def append_turn(self, turn):
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import firestore
        thread_ref = self._col('threads').document(turn['thread_id'])
        turn_ref = self._col('turns').document(turn['turn_id'])

        @firestore.transactional
        def write(tx):
            if not thread_ref.get(transaction=tx).exists:
                raise UnknownRecord('thread')
            if turn_ref.get(transaction=tx).exists:
                raise RecordExists('turns')
            tx.create(turn_ref, turn)
            tx.update(thread_ref, {'turns': firestore.ArrayUnion([turn['turn_id']])})
            return dict(turn)

        def run():
            try:
                return write(self.client.transaction())
            except AlreadyExists:
                raise RecordExists('turns') from None
        return self._call(run)

    def get_turn(self, key):
        return self._get('turns', key)

    def turns(self, key):
        order = {tid: i for i, tid in enumerate((self.get_thread(key) or {}).get('turns', []))}
        return sorted(self._where('turns', thread_id=key), key=lambda t: (order.get(t['turn_id'], len(order)), t['at']))

    def create_draft(self, draft):
        return self._create('drafts', draft['draft_id'], draft)

    def get_draft(self, key):
        return self._get('drafts', key)

    def drafts(self, owner, state=None):
        found = self._where('drafts', owner=owner) if state is None else self._where('drafts', owner=owner, state=state)
        return sorted(found, key=lambda d: (d['created_at'], d['draft_id']))

    def _settle(self, kind, key, field_state, from_state, fields):
        from google.cloud import firestore
        ref = self._col(kind).document(key)

        @firestore.transactional
        def write(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists:
                raise UnknownRecord(kind)
            doc = snap.to_dict()
            if doc.get(field_state) != from_state:
                raise AlreadyDecided(kind)
            tx.update(ref, fields)
            doc.update(fields)
            return doc
        return self._call(lambda: write(self.client.transaction()))

    def settle_draft(self, key, state):
        if state not in DRAFT_STATES[1:]:
            raise ValueError(state)
        return self._settle('drafts', key, 'state', 'draft', {'state': state})

    def create_confirmation(self, doc):
        if doc.get('state') != 'pending' or doc.get('decided_at') is not None:
            raise ValueError('a confirmation is created pending')
        return self._create('confirmations', doc['confirmation_id'], doc)

    def get_confirmation(self, key):
        return self._get('confirmations', key)

    def confirmations(self, owner, state=None):
        found = (self._where('confirmations', owner=owner) if state is None
                 else self._where('confirmations', owner=owner, state=state))
        return sorted(found, key=lambda c: c['confirmation_id'])

    def decide_confirmation(self, key, state, decided_at):
        if state not in CONFIRMATION_STATES[1:]:
            raise ValueError(state)
        return self._settle('confirmations', key, 'state', 'pending', {'state': state, 'decided_at': decided_at})

    def charge_budget(self, day, calls, usd, line):
        from google.cloud import firestore
        ref = self._col('budget').document(day)

        @firestore.transactional
        def write(tx):
            snap = ref.get(transaction=tx)
            allowed, doc = _budget_after(snap.to_dict() if snap.exists else None, day, calls, usd, line)
            if allowed:
                tx.set(ref, doc)
            return allowed, doc
        return self._call(lambda: write(self.client.transaction()))

    def get_budget(self, day):
        return self._get('budget', day)

    def add_receipt(self, receipt):
        return self._create('receipts', receipt['receipt_id'], receipt)

    def receipts(self, owner, confirmation_id=None):
        found = (self._where('receipts', owner=owner) if confirmation_id is None
                 else self._where('receipts', owner=owner, confirmation_id=confirmation_id))
        return sorted(found, key=lambda r: (r['started_at'], r['receipt_id']))

    def save_evidence(self, key, doc):
        return self._create('evidence', key, doc)

    def get_evidence(self, key):
        return self._get('evidence', key)
