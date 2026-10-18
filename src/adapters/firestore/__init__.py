"""Emulator-only transactional store, with immutable canonical record entries."""
import hashlib
import re

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore

from src.adapters.identity import local_configuration
from src.contracts.jsonutil import canonical_dumps
from src.review.errors import require, ReviewError
from src.review.storage import Snapshot, RetryPreparation, StorageUnavailable, current_actor


def digest(parts):
    return hashlib.sha256(canonical_dumps(parts).encode('utf-8')).hexdigest()


class FirestoreStore:
    def __init__(self, project, namespace, *, client=None):
        local_configuration(project)
        if not re.fullmatch(r'synthetic-[a-zA-Z0-9-]{1,100}', namespace):
            raise ValueError('H1 requires an explicit synthetic namespace')
        self.client = client or firestore.Client(project=project, credentials=AnonymousCredentials())
        self.root = self.client.collection('h1_namespaces').document(namespace)

    def case_ref(self, tenant, case):
        return self.root.collection('tenants').document(digest([tenant])).collection('cases').document(digest([case]))

    def member_ref(self, uid, tenant, case):
        return self.root.collection('members').document(digest([uid, tenant, case]))

    def membership(self, uid, tenant, case):
        try:
            return self.member_ref(uid, tenant, case).get(timeout=10).to_dict()
        except ReviewError:
            raise
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StorageUnavailable() from exc

    def load(self, actor, case):
        ref = self.case_ref(actor.tenant_id, case)
        member = self.member_ref(actor.actor_id, actor.tenant_id, case)
        @firestore.transactional
        def read(tx):
            membership = member.get(transaction=tx, timeout=10).to_dict()
            current_actor(actor, case, membership)
            root = ref.get(transaction=tx, timeout=10).to_dict()
            if root:
                require(root.get('codec') == 'h1.state.v1')
            entries = {}
            for doc in ref.collection('entries').stream(transaction=tx, timeout=10):
                data = doc.to_dict()
                require(doc.id == digest([data['key']]))
                entries[data['key']] = data['value']
            return Snapshot(root['generation'] if root else 0, entries, membership)
        try:
            return read(self.client.transaction(max_attempts=5))
        except ReviewError:
            raise
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StorageUnavailable() from exc

    def commit(self, actor, case, before, after):
        changed = {k: v for k, v in after.items() if before.entries.get(k) != v}
        require(set(before.entries) <= set(after))
        require(len(after) <= 2000 and len(changed) <= 450)
        require(sum(len(k.encode()) + len(v.encode()) for k, v in after.items()) <= 8 * 1024 * 1024)
        require(all(len(k.encode()) + len(v.encode()) < 900 * 1024 for k, v in after.items()))
        for key in changed:
            if key.startswith('["records",'):
                require(key not in before.entries, 'REVISION_CONFLICT')
        ref = self.case_ref(actor.tenant_id, case)
        member = self.member_ref(actor.actor_id, actor.tenant_id, case)
        @firestore.transactional
        def write(tx):
            membership = member.get(transaction=tx, timeout=10).to_dict()
            current_actor(actor, case, membership)
            # Any policy change invalidates preparation, even if scope remains partly usable.
            if membership != before.membership:
                raise RetryPreparation()
            root = ref.get(transaction=tx, timeout=10).to_dict()
            if (root['generation'] if root else 0) != before.generation:
                raise RetryPreparation()
            if changed:
                for key, value in changed.items():
                    tx.set(ref.collection('entries').document(digest([key])), {'key': key, 'value': value})
                tx.set(ref, {'codec': 'h1.state.v1', 'generation': before.generation + 1,
                             'tenant_id': actor.tenant_id, 'case_id': case})
        try:
            write(self.client.transaction(max_attempts=5))
        except ReviewError:
            raise
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StorageUnavailable() from exc

    def close(self):
        self.client.close()
