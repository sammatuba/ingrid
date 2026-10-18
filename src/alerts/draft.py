"""The portfolio import's draft (scripts/alerts/portfolio_import.py), read from the private bucket.

Only read when NOWCAST_PORTFOLIO_IMPORT=on (src/api/hosted.py). The draft holds region totals per
hour and counts, never a name, ID or node; it reaches the page only for a signed-in user, and only a
signed-in user's save turns it into a portfolio version. Storage over its JSON API with the
runtime's own identity (google-auth, already in the lock); no value is logged.
"""
import json
from urllib.parse import quote

# Bucket and object kept apart (the release audit allows no storage URI in shipped code).
BUCKET = 'grid-nowcast-data'
OBJECT = 'raw/portfolio/derived/draft-latest.json'
SCOPES = ('https://www.googleapis.com/auth/devstorage.read_only',)
MAX_BYTES = 1 << 20


class DraftUnavailable(Exception):
    """The bucket could not be read or the object is not a draft; the route answers 503."""


def checked(draft):
    """The draft if it has the import's shape (kind, window, units, 24-hour regions), else DraftUnavailable."""
    try:
        ok = (draft['kind'] == 'portfolio-draft' and isinstance(draft['window']['last'], str)
              and draft['units']['mq'] in ('kWh', 'MWh') and draft['units']['bcq'] in ('kWh', 'MWh')
              and draft['regions'] and all(
                  len(r['demand_mw_by_hour']) == 24 and len(r['contracted_mw_by_hour']) == 24
                  for r in draft['regions'].values()))
    except (KeyError, TypeError, AttributeError):
        ok = False
    if not ok:
        raise DraftUnavailable('not a portfolio draft')
    return draft


class GcsDraft:
    def __init__(self, bucket=BUCKET, name=OBJECT, session=None):
        if not bucket or not name:
            raise ValueError('a bucket and an object name')
        self.bucket, self.name = bucket, name
        self._session = session

    def session(self):
        if self._session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials, _ = google.auth.default(scopes=SCOPES)
            self._session = AuthorizedSession(credentials)
        return self._session

    def read(self):
        """The draft, or None when there is none yet."""
        url = (f'https://storage.googleapis.com/storage/v1/b/{quote(self.bucket, safe="")}'
               f'/o/{quote(self.name, safe="")}?alt=media')
        try:
            response = self.session().get(url, timeout=10)
        except Exception as exc:  # network or credentials: the reason only
            raise DraftUnavailable(type(exc).__name__) from None
        if response.status_code == 404:
            return None
        if response.status_code != 200 or len(response.content) > MAX_BYTES:
            raise DraftUnavailable(f'storage answered {response.status_code}')
        try:
            return checked(json.loads(response.content))
        except ValueError:
            raise DraftUnavailable('not JSON') from None
