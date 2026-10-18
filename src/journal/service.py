"""The journal's rules over a store: who writes, who reads, what a list returns.

Every call takes the signed-in user `{'uid', 'email', ...}` the route got from the verified Firebase
ID token (src/alerts/auth.py GoogleUsers). The author of an entry is that user and nothing else: a
body field naming an author is refused by the model before this runs.
"""
import uuid
from datetime import datetime, timedelta, timezone

from . import model
from .store import EntryExists

MANILA = timezone(timedelta(hours=8))


class NotFound(Exception):
    """No such entry, or a private entry of someone else (never told apart: 404)."""


class NotYours(Exception):
    """A desk entry written by someone else: readable, never editable (403)."""


def present(entry, uid):
    """An entry as the page gets it: `mine` says whether the caller wrote it, and the author is
    the email only (the uid is the store's key for ownership, not something the page needs)."""
    out = dict(entry, mine=entry['author']['uid'] == uid)
    out['author'] = {'email': entry['author'].get('email')}
    return out


def _manila_now():
    return datetime.now(MANILA).isoformat(timespec='seconds')


class JournalService:
    def __init__(self, store, clock=_manila_now, new_id=lambda: uuid.uuid4().hex, event_sites=None):
        self.store, self.clock, self.new_id = store, clock, new_id
        # Event id -> plant code, from the baked events file; lets a plant filter find the
        # entries written on that plant's events. Empty when the file is missing.
        self.event_sites = dict(event_sites or {})

    def create(self, user, body):
        fields = model.new_entry(body)
        now = self.clock()
        entry = dict(fields, id=self.new_id(), author={'uid': user['uid'], 'email': user['email']},
                     created_at=now, updated_at=now)
        try:
            self.store.create(entry)
        except EntryExists:
            entry['id'] = self.new_id()
            self.store.create(entry)
        return present(entry, user['uid'])

    def update(self, user, entry_id, body):
        if not model.ENTRY_ID.fullmatch(entry_id or ''):
            raise NotFound()
        fields = model.changes(body)
        entry = self.store.get(entry_id)
        if entry is None or not model.visible_to(entry, user['uid']):
            raise NotFound()
        if entry['author']['uid'] != user['uid']:
            raise NotYours()
        fields['updated_at'] = self.clock()
        return present(self.store.update(entry_id, fields), user['uid'])

    def list(self, user, **params):
        filters = model.query(**params)
        uid = user['uid']
        rows = self.store.by_author(uid) if filters['scope'] == 'mine' else self.store.shared()
        found = [e for e in rows if model.matches(e, uid, filters, self.event_sites)]
        entries = [present(e, uid) for e in model.ordered(found, filters['sort'])]
        return {'entries': entries[:model.LIST_LIMIT], 'total': len(entries),
                'truncated': len(entries) > model.LIST_LIMIT, 'filters': filters}
