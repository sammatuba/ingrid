"""Journal entries: what a request may carry, and how a list is filtered and ordered.

Record (docs/work/ericka-desk-2026-10-18/intent.md, section 3):

    {id, author{uid, email}, created_at, updated_at, as_of, target{kind: event|plant, id}, text,
     snapshot{price, region, latest_notice, known_facts[]}, visibility: private|desk}

`author` comes from the verified ID token only; a body that names one is refused, like any other
field this module does not know. `as_of` is the replay clock the entry was written against
(Manila wall time, minute precision, `YYYY-MM-DDTHH:MM`, the shared shell's format); `created_at`
and `updated_at` are the real save times (Manila, `+08:00`). `text` is kept exactly as text: it is
never parsed, escaped or rendered here, and the page writes it with `textContent`.

Decision D2: `visibility` is `private` (the default) or `desk`. A private entry is returned to its
author only; `scope=desk` lists shared entries only. Only `text` and `visibility` can be changed
after a save; the target and the "known then" snapshot are fixed when the entry is written.
"""
import math
import re
from datetime import datetime

KINDS = ('event', 'plant')
VISIBILITY = ('private', 'desk')
SCOPES = ('mine', 'desk')
SORTS = ('newest', 'oldest')

MAX_TEXT = 4000
MAX_FACTS = 20
MAX_FACT = 300
MAX_NOTICE = 500
MAX_QUERY = 200
MAX_PRICE = 1_000_000  # PHP/MWh; the market cap is far below this, so a larger value is an error
LIST_LIMIT = 200

ENTRY_ID = re.compile(r'[0-9a-f]{32}\Z')
TARGET_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z')
REGION = re.compile(r'[A-Z][A-Z0-9_]{1,15}\Z')
AS_OF = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z')
# Text may hold line breaks and tabs; no other control character (NUL, escape, bidi controls).
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f‪-‮⁦-⁩]')

CREATE_FIELDS = {'as_of', 'target', 'text', 'snapshot', 'visibility'}
CREATE_REQUIRED = {'as_of', 'target', 'text'}
UPDATE_FIELDS = {'text', 'visibility'}
TARGET_FIELDS = {'kind', 'id'}
SNAPSHOT_FIELDS = {'price', 'region', 'latest_notice', 'known_facts'}


class InvalidInput(ValueError):
    """A refused entry or list request; `field` names what was wrong (the route answers 422)."""

    def __init__(self, field, reason):
        self.field, self.reason = field, reason
        super().__init__(f'{field}: {reason}')


def _require(condition, field, reason):
    if not condition:
        raise InvalidInput(field, reason)


def _object(value, field, allowed, required=()):
    _require(type(value) is dict, field, 'an object')
    prefix = '' if field == 'body' else field + '.'
    extra = sorted(set(value) - set(allowed))
    if extra:
        raise InvalidInput(prefix + str(extra[0])[:40], 'not a known field')
    missing = sorted(set(required) - set(value))
    if missing:
        raise InvalidInput(prefix + missing[0], 'required')
    return value


def _string(value, field, limit, minimum=1):
    _require(type(value) is str, field, 'a string')
    _require(minimum <= len(value) <= limit, field, f'{minimum} to {limit} characters')
    _require(not CONTROL.search(value), field, 'no control characters')
    return value


def as_of(value, field='as_of'):
    _require(type(value) is str and AS_OF.fullmatch(value), field, 'a time YYYY-MM-DDTHH:MM (Manila)')
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        raise InvalidInput(field, 'a real date and time') from None
    return value


def target(value):
    _object(value, 'target', TARGET_FIELDS, TARGET_FIELDS)
    _require(value['kind'] in KINDS, 'target.kind', 'event or plant')
    _require(type(value['id']) is str and TARGET_ID.fullmatch(value['id']), 'target.id',
             'letters, digits, dot, dash or underscore (at most 80)')
    return {'kind': value['kind'], 'id': value['id']}


def snapshot(value):
    if value is None:
        value = {}
    _object(value, 'snapshot', SNAPSHOT_FIELDS)
    price = value.get('price')
    if price is not None:
        _require(type(price) in (int, float) and math.isfinite(price) and abs(price) <= MAX_PRICE,
                 'snapshot.price', 'a number (PHP/MWh) or null')
    region = value.get('region')
    if region is not None:
        _require(type(region) is str and REGION.fullmatch(region), 'snapshot.region', 'a region code or null')
    notice = value.get('latest_notice')
    if notice is not None:
        _string(notice, 'snapshot.latest_notice', MAX_NOTICE)
    facts = value.get('known_facts', [])
    _require(type(facts) is list and len(facts) <= MAX_FACTS, 'snapshot.known_facts',
             f'a list of at most {MAX_FACTS} strings')
    for i, fact in enumerate(facts):
        _string(fact, f'snapshot.known_facts[{i}]', MAX_FACT)
    return {'price': price, 'region': region, 'latest_notice': notice, 'known_facts': list(facts)}


def text(value):
    _string(value, 'text', MAX_TEXT)
    _require(value.strip(), 'text', 'not only spaces')
    return value


def visibility(value):
    _require(value in VISIBILITY, 'visibility', 'private or desk')
    return value


def new_entry(body):
    """The validated fields of a create request (everything but id, author and the save times)."""
    _object(body, 'body', CREATE_FIELDS, CREATE_REQUIRED)
    return {'as_of': as_of(body['as_of']), 'target': target(body['target']), 'text': text(body['text']),
            'snapshot': snapshot(body.get('snapshot')),
            'visibility': visibility(body.get('visibility', 'private'))}


def changes(body):
    """The validated fields of an update request: `text` and/or `visibility`, nothing else."""
    _object(body, 'body', UPDATE_FIELDS)
    _require(body, 'body', 'text or visibility')
    out = {}
    if 'text' in body:
        out['text'] = text(body['text'])
    if 'visibility' in body:
        out['visibility'] = visibility(body['visibility'])
    return out


def query(q='', plant='', event='', region='', since='', until='', scope='mine', sort='newest'):
    """A validated list request; empty strings mean "no filter"."""
    _require(type(q) is str and len(q) <= MAX_QUERY and not CONTROL.search(q), 'q',
             f'at most {MAX_QUERY} characters')
    for name, value in (('plant', plant), ('event', event)):
        _require(value == '' or (type(value) is str and TARGET_ID.fullmatch(value)), name, 'a code')
    _require(region == '' or (type(region) is str and REGION.fullmatch(region)), 'region', 'a region code')
    for name, value in (('since', since), ('until', until)):
        if value != '':
            as_of(value, name)
    _require(not (since and until and since > until), 'since', 'at or before until')
    _require(scope in SCOPES, 'scope', 'mine or desk')
    _require(sort in SORTS, 'sort', 'newest or oldest')
    return {'q': q.strip().lower(), 'plant': plant, 'event': event, 'region': region, 'since': since,
            'until': until, 'scope': scope, 'sort': sort}


def visible_to(entry, uid):
    """D2: an author sees their own entries; anyone signed in sees the ones shared with the desk."""
    return entry['author']['uid'] == uid or entry.get('visibility') == 'desk'


def _haystack(entry):
    snap = entry.get('snapshot') or {}
    parts = [entry.get('text', ''), entry['target']['id'], snap.get('region') or '',
             snap.get('latest_notice') or '', entry['author'].get('email') or '', *snap.get('known_facts', [])]
    return '\n'.join(parts).lower()


def matches(entry, uid, filters, event_sites=None):
    """One entry against a validated query, for the caller `uid`. Never true for a private entry
    of someone else, whatever the filters say."""
    if not visible_to(entry, uid):
        return False
    if filters['scope'] == 'mine' and entry['author']['uid'] != uid:
        return False
    if filters['scope'] == 'desk' and entry.get('visibility') != 'desk':
        return False
    kind, ident = entry['target']['kind'], entry['target']['id']
    if filters['plant']:
        # An entry on an event counts for its plant when the baked events file names the site.
        site = ident if kind == 'plant' else (event_sites or {}).get(ident)
        if site != filters['plant']:
            return False
    if filters['event'] and not (kind == 'event' and ident == filters['event']):
        return False
    if filters['region'] and (entry.get('snapshot') or {}).get('region') != filters['region']:
        return False
    if filters['since'] and entry['as_of'] < filters['since']:
        return False
    if filters['until'] and entry['as_of'] > filters['until']:
        return False
    if filters['q'] and filters['q'] not in _haystack(entry):
        return False
    return True


def ordered(entries, sort):
    """Newest or oldest by the replay time the entry is about, then by when it was saved."""
    return sorted(entries, key=lambda e: (e['as_of'], e['created_at'], e['id']), reverse=(sort == 'newest'))
