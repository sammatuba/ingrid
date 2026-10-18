"""Where the portfolio versions, notification rules, alerts and runs live.

Hosted: Firestore, under the private namespace's root (`h1_namespaces/<namespace>`), collections
prefixed `alerts_`. Portfolio and rules versions are append-only: a save takes the next number from a
counter inside one transaction and creates the version document, which is never overwritten. Demo mode
and the tests use `MemoryAlertStore`, which keeps the same rules in process.

Company data (portfolio values, recipients) is stored here and nowhere else; nothing here logs a value.
"""
import copy
import hashlib
from threading import RLock

KINDS = ('portfolio', 'rules')


class StoreUnavailable(Exception):
    """Firestore could not be reached or refused the write; the route answers 503."""


class VersionExists(Exception):
    """A version document already existed: never overwritten."""


def delivery_id(email):
    """A recipient's delivery document id: a digest, so the address is not a document name."""
    return hashlib.sha256(email.encode('utf-8')).hexdigest()[:32]


class MemoryAlertStore:
    def __init__(self):
        self._lock = RLock()
        self._versions = {kind: {} for kind in KINDS}
        self._alerts, self._runs, self._state, self._claims = {}, {}, {}, set()

    def add_version(self, kind, doc):
        with self._lock:
            versions = self._versions[kind]
            version = max(versions, default=0) + 1
            if version in versions:
                raise VersionExists(kind)
            versions[version] = dict(copy.deepcopy(doc), version=version)
            return version

    def versions(self, kind):
        with self._lock:
            return [copy.deepcopy(v) for _, v in sorted(self._versions[kind].items())]

    def latest(self, kind):
        with self._lock:
            versions = self._versions[kind]
            return copy.deepcopy(versions[max(versions)]) if versions else None

    def version(self, kind, number):
        with self._lock:
            return copy.deepcopy(self._versions[kind].get(number))

    def claim_delivery(self, key, email):
        """True for exactly one caller per (alert, recipient): the one that may send."""
        with self._lock:
            if (key, delivery_id(email)) in self._claims:
                return False
            self._claims.add((key, delivery_id(email)))
            return True

    def release_delivery(self, key, email):
        with self._lock:
            self._claims.discard((key, delivery_id(email)))

    def add_emailed(self, key, emails, sent_at, error):
        with self._lock:
            alert = self._alerts[key]
            alert['emailed_to'] = alert.get('emailed_to', []) + [e for e in emails if e not in alert.get('emailed_to', [])]
            if emails:
                alert['sent_at'] = sent_at
            alert['email_error'] = error

    def create_alert(self, key, doc):
        """True when created, False when an alert with this key already existed (never replaced)."""
        with self._lock:
            if key in self._alerts:
                return False
            self._alerts[key] = copy.deepcopy(doc)
            return True

    def get_alert(self, key):
        with self._lock:
            return copy.deepcopy(self._alerts.get(key))

    def update_alert(self, key, fields):
        with self._lock:
            self._alerts[key].update(copy.deepcopy(fields))

    def recent_alerts(self, limit=50):
        with self._lock:
            items = sorted(self._alerts.values(), key=lambda a: (a.get('created_at', ''), a['key']), reverse=True)
            return [copy.deepcopy(a) for a in items[:limit]]

    def put_run(self, run_id, doc):
        with self._lock:
            self._runs[run_id] = copy.deepcopy(doc)

    def get_run(self, run_id):
        with self._lock:
            return copy.deepcopy(self._runs.get(run_id))

    def pending_runs(self, limit=10):
        with self._lock:
            items = [r for r in self._runs.values() if r.get('status') == 'running']
            return [copy.deepcopy(r) for r in sorted(items, key=lambda r: r.get('created_at', ''))[:limit]]

    def get_state(self, name):
        with self._lock:
            return copy.deepcopy(self._state.get(name))

    def set_state(self, name, doc):
        with self._lock:
            self._state[name] = copy.deepcopy(doc)


class FirestoreAlertStore:
    """The same interface over Firestore; imported only in hosted mode (needs google-cloud-firestore)."""

    def __init__(self, client, namespace):
        self.client = client
        self.root = client.collection('h1_namespaces').document(namespace)

    def _call(self, fn, *args):
        from google.api_core.exceptions import GoogleAPICallError, RetryError
        try:
            return fn(*args)
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StoreUnavailable() from exc

    def add_version(self, kind, doc):
        from google.cloud import firestore
        if kind not in KINDS:
            raise ValueError(kind)
        counter = self.root.collection('alerts_state').document(kind + '_counter')
        versions = self.root.collection('alerts_' + kind)

        @firestore.transactional
        def write(tx):
            snap = counter.get(transaction=tx)
            version = int((snap.to_dict() or {}).get('last', 0)) + 1 if snap.exists else 1
            ref = versions.document('%06d' % version)
            if ref.get(transaction=tx).exists:
                raise VersionExists(kind)
            tx.set(counter, {'last': version})
            tx.create(ref, dict(doc, version=version))
            return version

        return self._call(lambda: write(self.client.transaction()))

    def versions(self, kind):
        def read():
            docs = self.root.collection('alerts_' + kind).stream(timeout=10)
            return sorted((d.to_dict() for d in docs), key=lambda v: v['version'])
        return self._call(read)

    def version(self, kind, number):
        def read():
            snap = self.root.collection('alerts_' + kind).document('%06d' % number).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def claim_delivery(self, key, email):
        """Create the (alert, recipient) delivery document; only the caller that created it sends."""
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import firestore

        def write():
            try:
                (self.root.collection('alerts_log').document(key).collection('deliveries')
                 .document(delivery_id(email)).create({'claimed_at': firestore.SERVER_TIMESTAMP}))
                return True
            except AlreadyExists:
                return False
        return self._call(write)

    def release_delivery(self, key, email):
        return self._call(lambda: self.root.collection('alerts_log').document(key).collection('deliveries')
                          .document(delivery_id(email)).delete())

    def add_emailed(self, key, emails, sent_at, error):
        from google.cloud import firestore
        fields = {'email_error': error}
        if emails:
            fields.update(emailed_to=firestore.ArrayUnion(list(emails)), sent_at=sent_at)
        return self._call(lambda: self.root.collection('alerts_log').document(key).update(fields))

    def latest(self, kind):
        from google.cloud import firestore

        def read():
            docs = list(self.root.collection('alerts_' + kind)
                        .order_by('version', direction=firestore.Query.DESCENDING).limit(1).stream(timeout=10))
            return docs[0].to_dict() if docs else None
        return self._call(read)

    def create_alert(self, key, doc):
        from google.api_core.exceptions import AlreadyExists

        def write():
            try:
                self.root.collection('alerts_log').document(key).create(doc)
                return True
            except AlreadyExists:
                return False
        return self._call(write)

    def get_alert(self, key):
        def read():
            snap = self.root.collection('alerts_log').document(key).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def update_alert(self, key, fields):
        return self._call(lambda: self.root.collection('alerts_log').document(key).update(fields))

    def recent_alerts(self, limit=50):
        from google.cloud import firestore

        def read():
            docs = (self.root.collection('alerts_log')
                    .order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream(timeout=10))
            return [d.to_dict() for d in docs]
        return self._call(read)

    def put_run(self, run_id, doc):
        return self._call(lambda: self.root.collection('alerts_runs').document(run_id).set(doc))

    def get_run(self, run_id):
        def read():
            snap = self.root.collection('alerts_runs').document(run_id).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def pending_runs(self, limit=10):
        def read():
            docs = (self.root.collection('alerts_runs').where('status', '==', 'running')
                    .limit(limit).stream(timeout=10))
            return sorted((d.to_dict() for d in docs), key=lambda r: r.get('created_at', ''))
        return self._call(read)

    def get_state(self, name):
        def read():
            snap = self.root.collection('alerts_state').document(name).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def set_state(self, name, doc):
        return self._call(lambda: self.root.collection('alerts_state').document(name).set(doc))
