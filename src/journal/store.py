"""Where journal entries live.

Hosted: Firestore, under the private namespace's root (`h1_namespaces/<namespace>`), one collection
`journal_entries` whose document id is the entry id (the alerts store's namespace pattern,
src/alerts/store.py). Demo mode and the tests use `MemoryJournalStore`, which keeps the same rules in
process.

The store answers only two reads, both narrowed before any filter runs: the caller's own entries
(`author.uid == uid`) and the entries shared with the desk (`visibility == 'desk'`). A private entry
of someone else is never read for a list. Both are single-field equality queries, so Firestore needs
no composite index; ordering and the other filters run in the service. Nothing here logs a value.
"""
import copy
from threading import RLock

COLLECTION = 'journal_entries'
READ_LIMIT = 1000


class StoreUnavailable(Exception):
    """Firestore could not be reached or refused the write; the route answers 503."""


class EntryExists(Exception):
    """An entry with this id already existed: never overwritten."""


class MemoryJournalStore:
    def __init__(self):
        self._lock = RLock()
        self._entries = {}

    def create(self, entry):
        with self._lock:
            if entry['id'] in self._entries:
                raise EntryExists(entry['id'])
            self._entries[entry['id']] = copy.deepcopy(entry)

    def get(self, entry_id):
        with self._lock:
            return copy.deepcopy(self._entries.get(entry_id))

    def update(self, entry_id, fields):
        with self._lock:
            self._entries[entry_id].update(copy.deepcopy(fields))
            return copy.deepcopy(self._entries[entry_id])

    def by_author(self, uid, limit=READ_LIMIT):
        with self._lock:
            return [copy.deepcopy(e) for e in self._entries.values() if e['author']['uid'] == uid][:limit]

    def shared(self, limit=READ_LIMIT):
        with self._lock:
            return [copy.deepcopy(e) for e in self._entries.values() if e.get('visibility') == 'desk'][:limit]


class FirestoreJournalStore:
    """The same interface over Firestore; imported only in hosted mode (needs google-cloud-firestore)."""

    def __init__(self, client, namespace):
        self.client = client
        self.root = client.collection('h1_namespaces').document(namespace)

    def _entries(self):
        return self.root.collection(COLLECTION)

    def _call(self, fn):
        from google.api_core.exceptions import GoogleAPICallError, RetryError
        try:
            return fn()
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StoreUnavailable() from exc

    def create(self, entry):
        from google.api_core.exceptions import AlreadyExists

        def write():
            try:
                self._entries().document(entry['id']).create(entry)
            except AlreadyExists:
                raise EntryExists(entry['id']) from None
        return self._call(write)

    def get(self, entry_id):
        def read():
            snap = self._entries().document(entry_id).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def update(self, entry_id, fields):
        def write():
            ref = self._entries().document(entry_id)
            ref.update(fields)
            return ref.get(timeout=10).to_dict()
        return self._call(write)

    def _where(self, field, value, limit):
        from google.cloud.firestore_v1.base_query import FieldFilter

        def read():
            docs = self._entries().where(filter=FieldFilter(field, '==', value)).limit(limit).stream(timeout=10)
            return [d.to_dict() for d in docs]
        return self._call(read)

    def by_author(self, uid, limit=READ_LIMIT):
        return self._where('author.uid', uid, limit)

    def shared(self, limit=READ_LIMIT):
        return self._where('visibility', 'desk', limit)
