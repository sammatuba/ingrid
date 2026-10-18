"""The full driver card when an alert is opened (owner decision of 2026-10-18: compute on first open,
cache in Firestore, signed-in users only, a bytes cap).

`LiveCards.block(user, alert, data_dir)` gives the explanation's two fields: `ontology`, the card
(src/alerts/ontology.py schema, the same JSON the batch bakes) or None, and `ontology_status`, what the
page says about it:

1. a baked card (`<data>/ontology/cards/<key>.json`, ontology.py `load_card` for this region and peak
   interval): shown at once;
2. else a card saved by an earlier open (Firestore `ontology_cards/<key>`, for this region and peak
   interval, passing ontology.py `problems`): shown at once, to anyone;
3. else, for a signed-in user only, three read-only BigQuery scripts (ontology.py `card_query`, one per
   mode) are started in parallel, each with maximum_bytes_billed a third of NOWCAST_ONTOLOGY_MAX_BYTES
   (default 5,000,000,000 in all). Measured on the PEDC interval: about 0.42 GB billed and 35-45 s per
   mode, against 1.35 GB and 110-210 s for the three-mode script run serially. That is still longer
   than one request may wait, so the page asks again every few seconds: each ask reads the jobs' state
   and, once all are done, merges their rows (`merge`), shapes the card (ontology.py `shape`), checks it
   (`problems`), saves it and shows it;
4. an anonymous caller starts nothing: the status says the card is not computed yet and to sign in;
5. a failed, refused or timed-out job (NOWCAST_ONTOLOGY_TIMEOUT_S, default 180 s from the start), or a
   card that fails `problems`, leaves the code-only explanation with the note "Full driver card not
   available right now"; nothing is made up. A signed-in open may try again after RETRY_SECONDS.

No duplicate queries: one in-process lock per alert key, and the cache is read again under it; the jobs
are claimed in Firestore with a create (only one instance starts them), and their ids are saved so any
instance can finish the card.
"""
import json
import time
from datetime import datetime, timezone
from threading import Lock

from . import ontology
from .bigquery import QueryFailed
from .store import StoreUnavailable

MAX_BYTES = 5_000_000_000
TIMEOUT_SECONDS = 180
RETRY_SECONDS = 300
POLL_SECONDS = 3
COLLECTION = 'ontology_cards'
LABELS = {'alerts': 'ontology_card'}

NOTE_COMPUTING = 'Computing the full driver card… This takes about a minute, once; it is then saved for everyone.'
NOTE_SIGN_IN = ('The full driver card has not been computed for this alert yet. Sign in to compute it '
                '(about a minute, once; it is then saved for everyone). The likely drivers above are computed '
                'from the replay data.')
NOTE_UNAVAILABLE = 'Full driver card not available right now. The likely drivers above are computed from the replay data.'
NOTE_OFF = 'Full driver card not available here. The likely drivers above are computed from the replay data.'


def _iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds')


def _utc(seconds):
    """UTC 'YYYY-MM-DD HH:MM:SS', as the card's made_at_utc."""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def merge(results):
    """One decoded `alert_json` ({cards, drivers, summary}) from the per-mode jobs' result rows; each row
    carries its mode, so ontology.shape sorts them out exactly as from the three-mode script."""
    out = {'cards': [], 'drivers': [], 'summary': []}
    for rows in results:
        part = json.loads(rows[0]['alert_json'])
        for k in out:
            out[k] += part.get(k) or []
    return out


class MemoryCardCache:
    """The cache in process (demo mode and the tests)."""

    def __init__(self):
        self._docs, self._lock = {}, Lock()

    def get(self, key):
        with self._lock:
            doc = self._docs.get(key)
            return json.loads(json.dumps(doc)) if doc is not None else None

    def claim(self, key, doc, replace=None):
        """True when this caller now owns the computation: the document did not exist, or it still equals
        `replace` (a failed or stale document seen by the caller)."""
        with self._lock:
            current = self._docs.get(key)
            if current is not None and current != replace:
                return False
            self._docs[key] = json.loads(json.dumps(doc))
            return True

    def put(self, key, doc):
        with self._lock:
            self._docs[key] = json.loads(json.dumps(doc))


class FirestoreCardCache:
    """`h1_namespaces/<namespace>/ontology_cards/<alert key>`: {state, jobs, started_at, card_json,
    computed_at, bytes, seconds, reason, region, interval_manila}. The card is kept as JSON text (one
    field, well under the 1 MiB limit)."""

    def __init__(self, client, namespace):
        self.client = client
        self.col = client.collection('h1_namespaces').document(namespace).collection(COLLECTION)

    def _call(self, fn):
        from google.api_core.exceptions import GoogleAPICallError, RetryError
        try:
            return fn()
        except (GoogleAPICallError, RetryError, ValueError) as exc:
            raise StoreUnavailable() from exc

    def get(self, key):
        def read():
            snap = self.col.document(key).get(timeout=10)
            return snap.to_dict() if snap.exists else None
        return self._call(read)

    def claim(self, key, doc, replace=None):
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import firestore
        ref = self.col.document(key)
        if replace is None:
            def create():
                try:
                    ref.create(doc)
                    return True
                except AlreadyExists:
                    return False
            return self._call(create)

        @firestore.transactional
        def swap(tx):
            snap = ref.get(transaction=tx)
            if not snap.exists or snap.to_dict() != replace:
                return False
            tx.set(ref, doc)
            return True
        return self._call(lambda: swap(self.client.transaction()))

    def put(self, key, doc):
        return self._call(lambda: self.col.document(key).set(doc))


class LiveCards:
    def __init__(self, cache=None, bigquery=None, max_bytes=MAX_BYTES, timeout_seconds=TIMEOUT_SECONDS,
                 retry_seconds=RETRY_SECONDS, clock=time.time):
        self.cache, self.bigquery = cache, bigquery
        self.max_bytes, self.timeout, self.retry = int(max_bytes), timeout_seconds, retry_seconds
        self.clock = clock
        self._locks, self._locks_lock = {}, Lock()

    @classmethod
    def from_env(cls, env, cache, bigquery):
        def number(name, default):
            try:
                value = int(str(env.get(name) or '').strip() or default)
            except ValueError:
                return default
            return value if value > 0 else default
        return cls(cache, bigquery, number('NOWCAST_ONTOLOGY_MAX_BYTES', MAX_BYTES),
                   number('NOWCAST_ONTOLOGY_TIMEOUT_S', TIMEOUT_SECONDS))

    def _lock(self, key):
        with self._locks_lock:
            return self._locks.setdefault(key, Lock())

    # ------------------------------------------------------------------------- answers
    @staticmethod
    def _ready(card, origin, computed_at=None, billed=None):
        return {'ontology': card, 'ontology_status': {'state': 'ready', 'origin': origin, 'computed_at': computed_at,
                                                      'bytes_billed': billed, 'note': None}}

    @staticmethod
    def _state(state, note, **extra):
        return {'ontology': None, 'ontology_status': dict({'state': state, 'note': note}, **extra)}

    def _from_doc(self, doc, alert):
        """The saved card when it is ready, fit, and for this alert's region and peak interval; else None."""
        if not doc or doc.get('state') != 'ready':
            return None
        try:
            card = json.loads(doc['card_json'])
        except (KeyError, TypeError, ValueError):
            return None
        if (not isinstance(card, dict) or card.get('key') != alert['key'] or ontology.problems(card)
                or card.get('region') != alert.get('region') or card.get('interval_manila') != alert.get('interval_manila')):
            return None
        return self._ready(card, 'saved', doc.get('computed_at'), doc.get('bytes'))

    # ------------------------------------------------------------------------- the flow
    def block(self, user, alert, data_dir):
        """{'ontology': card or None, 'ontology_status': {...}} for one alert (see the module docstring);
        never raises for BigQuery or the cache: a failure is the 'unavailable' state."""
        key = alert['key']
        baked = ontology.load_card(data_dir, key, alert) if data_dir is not None else None
        if baked is not None:
            return self._ready(baked, 'baked', baked.get('made_at_utc'))
        if self.cache is None:
            return self._state('unavailable', NOTE_OFF)
        try:
            doc = self.cache.get(key)
            shown = self._from_doc(doc, alert)
            if shown is not None:
                return shown
            if doc and doc.get('state') == 'running':
                return self._advance(key, alert, doc)
            if user is None:
                if doc and doc.get('state') == 'failed':
                    return self._state('unavailable', NOTE_UNAVAILABLE)
                return self._state('sign_in', NOTE_SIGN_IN)
            if self.bigquery is None:
                return self._state('unavailable', NOTE_OFF)
            return self._start(key, alert)
        except StoreUnavailable:
            return self._state('unavailable', NOTE_UNAVAILABLE)

    def _start(self, key, alert):
        with self._lock(key):
            doc = self.cache.get(key)  # again, under the lock: another request may have started or finished it
            shown = self._from_doc(doc, alert)
            if shown is not None:
                return shown
            if doc and doc.get('state') == 'running':
                return self._advance(key, alert, doc, locked=True)
            now = self.clock()
            if doc and doc.get('state') == 'failed' and now - float(doc.get('failed_at_s') or 0) < self.retry:
                return self._state('unavailable', NOTE_UNAVAILABLE)
            claim = {'state': 'running', 'jobs': None, 'started_at': _iso(now), 'started_at_s': now,
                     'region': alert['region'], 'interval_manila': alert['interval_manila']}
            if not self.cache.claim(key, claim, replace=doc):
                return self._state('computing', NOTE_COMPUTING, retry_after_s=POLL_SECONDS)
            jobs = {}
            try:
                for mode in ontology.MODES:
                    text, params = ontology.card_query(alert['region'], ontology.t_utc_of(alert['interval_manila']), mode)
                    jobs[mode] = self.bigquery.start(text, params, max_bytes=self.max_bytes // len(ontology.MODES),
                                                     labels=LABELS)
            except QueryFailed as exc:
                return self._fail(key, exc.reason)
            except ValueError:
                return self._fail(key, 'refused')
            claim = dict(claim, jobs=jobs)
            self.cache.put(key, claim)
            return self._advance(key, alert, claim, locked=True)

    def _advance(self, key, alert, doc, locked=False):
        if not locked:
            with self._lock(key):
                fresh = self.cache.get(key)
                shown = self._from_doc(fresh, alert)
                if shown is not None:
                    return shown
                if not fresh or fresh.get('state') != 'running':
                    return self._state('unavailable', NOTE_UNAVAILABLE)
                return self._advance(key, alert, fresh, locked=True)
        elapsed = self.clock() - float(doc.get('started_at_s') or 0)
        computing = self._state('computing', NOTE_COMPUTING, retry_after_s=POLL_SECONDS, started_at=doc.get('started_at'))
        jobs = doc.get('jobs')
        if not jobs:  # another instance claimed it and is starting the jobs
            return self._fail(key, 'timeout') if elapsed > self.timeout else computing
        try:
            states = {mode: self.bigquery.status(job) for mode, job in jobs.items()}
            failed = next((s['error'] for s in states.values() if s['state'] == 'DONE' and s.get('error')), None)
            if failed:
                return self._fail(key, failed)
            if not all(s['state'] == 'DONE' for s in states.values()):
                return self._fail(key, 'timeout') if elapsed > self.timeout else computing
            results = [self.bigquery.rows(job) for job in jobs.values()]
        except QueryFailed as exc:
            return self._fail(key, exc.reason)
        now = self.clock()
        try:
            card = ontology.shape(merge(results), alert, made_at_utc=_utc(now))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            return self._fail(key, 'unreadable result')
        if ontology.problems(card):
            return self._fail(key, 'card refused')
        billed = sum(int(s.get('bytes_billed') or 0) for s in states.values())
        self.cache.put(key, {'state': 'ready', 'card_json': json.dumps(card, ensure_ascii=False, allow_nan=False),
                             'computed_at': _iso(now), 'bytes': billed,
                             'seconds': round(now - float(doc.get('started_at_s') or now), 1),
                             'region': alert['region'], 'interval_manila': alert['interval_manila']})
        return self._ready(card, 'computed', _iso(now), billed)

    def _fail(self, key, reason):
        now = self.clock()
        try:
            self.cache.put(key, {'state': 'failed', 'reason': str(reason)[:80], 'failed_at': _iso(now), 'failed_at_s': now})
        except StoreUnavailable:
            pass
        return self._state('unavailable', NOTE_UNAVAILABLE)
