"""The desk agent's action catalogue: what a plan may propose, over the manifest only.

The contract is ``docs/work/desk-agent-and-book-2026-10-18/agent-contract.md``, section 2. A plan
(view.v4, :mod:`src.judgment.view`) may carry ``actions``: each one names an action of
:data:`ACTIONS`, its arguments and a reason key. Every argument is a **manifest reference**,
never a value: :func:`action_manifest` renders, for the request, the identifiers an action may
take (the site's own routes, the record, event, outlook and assumption identifiers the records
carry, and the account, node, window, draft, thread, view, passage, case and revision
identifiers the caller supplies) each under a reference the plan names. A route is its own
reference; every other identifier is referenced by a letter handle such as ``record-a``, so a
plan never needs a numeral to name a record whose identifier carries one (the numeral rule of
:mod:`src.judgment.view` refuses any numeral anywhere in a plan, with no exemption).

:func:`check_action` reads one proposed action against the catalogue, the manifest and the
request's ``signed_in`` flag and returns ``(resolved, refusal)``: an action outside the
catalogue is refused ``not_in_catalogue``, an argument outside its schema or the manifest is
refused ``argument_not_in_manifest``, and an action whose ``writes`` is true on a request that
is not signed in is refused ``needs_sign_in``. The refusal is the reason key the receipt
records. Nothing here executes an action: the composer records the actions proposed, refused
and run (none, here); execution is the existing API's write path (DOCK-3), and an action whose
``confirm`` is true runs only after the person's recorded confirmation.

The module is pure: it imports nothing from the web layer, opens no file and calls nothing.
"""
from __future__ import annotations

#: The site's own section routes, as ``tests/test_hosting_stage.py`` ``SITE_ROUTES`` states
#: them (the test pins the two sets equal). ``open`` takes one of these and nothing else.
SITE_ROUTES = ('/', '/alerts', '/ask', '/book', '/data', '/explain', '/map', '/models', '/notices',
               '/outlooks', '/paper', '/plants', '/register', '/work')

#: The kinds of draft ``draft`` may prepare (contract section 2).
DRAFT_KINDS = ('case', 'decision_reason', 'reissue')

#: The identifier kinds the manifest renders, and the handle prefix of each. A route and a
#: draft kind are their own references; every other identifier gets a letter handle.
ID_KINDS = {
    'routes': None,
    'records': 'record',
    'events': 'event',
    'outlooks': 'outlook',
    'assumptions': 'assumption',
    'revisions': 'revision',
    'accounts': 'account',
    'nodes': 'node',
    'windows': 'window',
    'cutoffs': 'cutoff',
    'questions': 'question',
    'passages': 'passage',
    'threads': 'thread',
    'views': 'view',
    'drafts': 'draft',
    'cases': 'case',
    'draft_kinds': None,
}

#: The handle prefixes :func:`handle` writes, and the longest letter run a handle may carry.
HANDLE_PREFIXES = tuple(prefix for prefix in ID_KINDS.values() if prefix is not None)
MAX_HANDLE_LETTERS = 4

#: The identifier kinds a caller may supply; the others are read from the records.
CALLER_ID_KINDS = ('accounts', 'nodes', 'windows', 'revisions', 'passages', 'threads', 'views',
                   'drafts', 'cases', 'assumptions')


def _arg(ids, many=False):
    return {'ids': ids, 'many': many}


#: The action catalogue (contract section 2). ``args`` maps each argument to the manifest
#: identifier kind it takes (``many`` for a list); ``required`` must all be present;
#: ``one_of`` groups name arguments of which exactly one is present; ``reads`` and
#: ``writes`` name the record kinds; ``sign_in`` and ``confirm`` are the flags the dock shows.
#: ``writes`` is empty for an action that writes nothing.
ACTIONS = {
    'open': {
        'args': {'route': _arg('routes'), 'record_id': _arg('records')},
        'required': ('route',), 'one_of': (),
        'reads': (), 'writes': (), 'sign_in': False, 'confirm': False},
    'query_exposure': {
        'args': {'account_ids': _arg('accounts', True), 'node_ids': _arg('nodes', True),
                 'window': _arg('windows'), 'cutoff': _arg('cutoffs')},
        'required': ('account_ids', 'node_ids', 'window', 'cutoff'), 'one_of': (),
        'reads': ('book', 'exposure'), 'writes': (), 'sign_in': False, 'confirm': False},
    # BOOK-4: the impact query also takes the window and the cutoff (BOOK-2's hand-back: the
    # band is read through the archive by the vintage's id, resolved to its digest by the book
    # adapter, over a window inside the vintage's horizon and at the question's cutoff).
    'query_impact': {
        'args': {'account_ids': _arg('accounts', True), 'outlook_id': _arg('outlooks'),
                 'window': _arg('windows'), 'cutoff': _arg('cutoffs')},
        'required': ('account_ids', 'outlook_id', 'window', 'cutoff'), 'one_of': (),
        'reads': ('book', 'impact'), 'writes': (), 'sign_in': False, 'confirm': False},
    'search_web': {
        'args': {'question_id': _arg('questions'), 'cutoff': _arg('cutoffs')},
        'required': ('question_id', 'cutoff'), 'one_of': (),
        'reads': ('evidence_receipt',), 'writes': ('private_copy',),
        'sign_in': True, 'confirm': False},
    'pin': {
        'args': {'record_id': _arg('records'), 'passage_id': _arg('passages'),
                 'thread_id': _arg('threads')},
        'required': ('thread_id',), 'one_of': (('record_id', 'passage_id'),),
        'reads': (), 'writes': ('private_copy',), 'sign_in': True, 'confirm': False},
    'draft': {
        'args': {'kind': _arg('draft_kinds'), 'record_ids': _arg('records', True)},
        'required': ('kind', 'record_ids'), 'one_of': (),
        'reads': ('named_records',), 'writes': ('private_copy',),
        'sign_in': True, 'confirm': False},
    'mark_stale': {
        'args': {'assumption_id': _arg('assumptions'), 'revision': _arg('revisions')},
        'required': ('assumption_id', 'revision'), 'one_of': (),
        'reads': ('register', 'archive'), 'writes': ('stale_marks',),
        'sign_in': True, 'confirm': True},
    'reissue_outlook': {
        'args': {'draft_id': _arg('drafts')},
        'required': ('draft_id',), 'one_of': (),
        'reads': ('archive', 'book'), 'writes': ('vintage', 'impact'),
        'sign_in': True, 'confirm': True},
    'save_decision': {
        'args': {'draft_id': _arg('drafts'), 'event_id': _arg('events'), 'case_id': _arg('cases')},
        'required': ('draft_id',), 'one_of': (('event_id', 'case_id'),),
        'reads': (), 'writes': ('decision_record',), 'sign_in': True, 'confirm': True},
    'share': {
        'args': {'thread_id': _arg('threads'), 'view_id': _arg('views')},
        'required': (), 'one_of': (('thread_id', 'view_id'),),
        'reads': (), 'writes': ('shared_record',), 'sign_in': True, 'confirm': True},
}

ACTION_NAMES = tuple(ACTIONS)

#: The manifest identifier kind each argument name takes, across the whole catalogue (an
#: argument name means one kind wherever it appears; the live schema enumerates by it).
ARG_IDS = {}
for _spec in ACTIONS.values():
    for _arg_name, _item in _spec['args'].items():
        if ARG_IDS.setdefault(_arg_name, (_item['ids'], _item['many'])) != (_item['ids'], _item['many']):
            raise ValueError('an argument name takes two identifier kinds: ' + _arg_name)
del _spec, _arg_name, _item

#: At most this many arguments on one action, and items in one list argument.
MAX_ACTION_ARGS = max(len(spec['args']) for spec in ACTIONS.values())
MAX_ARGUMENT_ITEMS = 16

#: The refusal reason keys :func:`check_action` returns (members of the view's reason
#: catalogue, :data:`src.judgment.view.REASONS`).
REFUSALS = ('not_in_catalogue', 'argument_not_in_manifest', 'needs_sign_in')


def is_snake_key(value, words=3, length=32):
    """Whether ``value`` is a short lower-case snake-case key (at most ``words`` words)."""
    if type(value) is not str or not value or len(value) > length:
        return False
    parts = value.split('_')
    return len(parts) <= words and all(part and part.isascii() and part.isalpha()
                                       and part.islower() for part in parts)


def is_reference(value, routes):
    """Whether ``value`` is shaped like a manifest reference: a route the manifest lists, a
    draft kind, or a handle ``<prefix>-<letters>`` with a known prefix. A well-shaped reference
    the manifest does not offer is still :func:`check_action`'s recorded refusal; a value of any
    other shape (a sentence, a URL, a raw identifier) is not a reference at all."""
    if type(value) is not str:
        return False
    if value in routes or value in DRAFT_KINDS:
        return True
    prefix, _, letters = value.partition('-')
    return (prefix in HANDLE_PREFIXES and 1 <= len(letters) <= MAX_HANDLE_LETTERS
            and letters.isascii() and letters.isalpha() and letters.islower())


def writes(name):
    """Whether the catalogue action ``name`` writes anything."""
    return bool(ACTIONS[name]['writes'])


def handle(prefix, index):
    """The letter handle ``<prefix>-a``, ``-b`` … ``-z``, ``-aa`` … for the ``index``-th id."""
    if type(index) is not int or index < 0:
        raise ValueError('a handle index is a non-negative integer')
    letters = ''
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord('a') + rest) + letters
    return prefix + '-' + letters


def is_window_id(value):
    """Whether ``value`` is a window identifier: two local hours ``YYYY-MM-DDTHH:00`` joined by
    a slash, the first before the second (``src.book.adapter.window_id`` writes it)."""
    if type(value) is not str or value.count('/') != 1:
        return False
    hours = value.split('/')
    for hour in hours:
        if len(hour) != 16 or hour[4] != '-' or hour[7] != '-' or hour[10] != 'T' \
                or hour[13:] != ':00':
            return False
        digits = hour[0:4] + hour[5:7] + hour[8:10] + hour[11:13]
        if not (digits.isascii() and digits.isdigit()):
            return False
    return hours[0] < hours[1]


def _id_list(kind, values):
    if type(values) not in (list, tuple):
        raise ValueError(f'the {kind} identifiers must be a list')
    seen = []
    for value in values:
        if type(value) is not str or not value.strip():
            raise ValueError(f'every {kind} identifier must be a nonblank string')
        if value not in seen:
            seen.append(value)
    return seen


def action_manifest(record_ids, *, event_id, outlook_ids, assumption_ids, cutoff, question,
                    signed_in, ids=None):
    """The identifiers the actions may take, each under the reference a plan names.

    ``record_ids`` is the receipt's record references (``{'record', 'record_id'}``) in order;
    ``event_id``, ``outlook_ids`` and ``assumption_ids`` are read from the records by the
    composer; ``cutoff`` and ``question`` are the request's own (``question`` may be ``None``
    when no question is rendered, and then no question identifier is offered). ``ids`` is the caller's
    mapping of :data:`CALLER_ID_KINDS` to identifier lists (accounts, nodes, windows, drafts,
    threads, views, passages, cases, revisions, further assumptions); a kind no caller
    supplies is an empty list, so an action that needs it is unavailable and any argument for
    it is refused. Identifiers only: no record value, figure or text is rendered here.
    """
    if type(signed_in) is not bool:
        raise ValueError('signed_in must be a boolean')
    supplied = {} if ids is None else ids
    if type(supplied) is not dict or any(kind not in CALLER_ID_KINDS for kind in supplied):
        raise ValueError('ids must map caller identifier kinds to lists: '
                         + ', '.join(CALLER_ID_KINDS))
    values = {kind: [] for kind in ID_KINDS}
    values['routes'] = list(SITE_ROUTES)
    values['draft_kinds'] = list(DRAFT_KINDS)
    values['records'] = _id_list('record', [ref['record_id'] for ref in record_ids])
    values['events'] = _id_list('event', [event_id])
    values['outlooks'] = _id_list('outlook', list(outlook_ids))
    values['cutoffs'] = _id_list('cutoff', [cutoff])
    values['questions'] = _id_list('question', [] if question is None else [question])
    values['assumptions'] = _id_list('assumption', list(assumption_ids))
    for kind, listed in supplied.items():
        values[kind] = _id_list(kind, values[kind] + list(_id_list(kind, listed)))
    # BOOK-4 rework round 1 (review finding 4): a window is an identifier, never a sentence.
    if any(not is_window_id(value) for value in values['windows']):
        raise ValueError('every window identifier must be <YYYY-MM-DDTHH:00>/<YYYY-MM-DDTHH:00>')
    record_kind = {ref['record_id']: ref['record'] for ref in record_ids}
    rendered = {}
    for kind, prefix in ID_KINDS.items():
        entries = []
        for index, value in enumerate(values[kind]):
            entry = {'ref': value if prefix is None else handle(prefix, index), 'id': value}
            if kind == 'records':
                entry['record'] = record_kind[value]
            entries.append(entry)
        rendered[kind] = entries
    catalogue = []
    for name, spec in ACTIONS.items():
        needed = set(spec['required'])
        for group in spec['one_of']:
            needed |= set() if any(rendered[spec['args'][arg]['ids']] for arg in group) \
                else set(group)
        available = all(rendered[spec['args'][arg]['ids']] for arg in needed)
        catalogue.append({'action': name,
                          'args': {arg: dict(item) for arg, item in spec['args'].items()},
                          'required': list(spec['required']),
                          'one_of': [list(group) for group in spec['one_of']],
                          'writes': writes(name), 'sign_in': spec['sign_in'],
                          'confirm': spec['confirm'], 'available': available})
    return {'catalogue': catalogue, 'ids': rendered, 'signed_in': signed_in}


def _resolve(entries, ref):
    for entry in entries:
        if entry['ref'] == ref:
            return entry['id']
    return None


def check_action(action, manifest):
    """``(resolved, refusal)`` for one proposed action against the catalogue and manifest.

    ``action`` is ``{'action', 'args', 'reason_key'}`` as the plan carries it (its shape and
    the numeral rule are the view validator's). ``resolved`` maps each argument to the
    identifier (or list of identifiers) its reference names, and ``refusal`` is ``None`` or one
    of :data:`REFUSALS`. The checks run in order: the name, then every argument (its name, its
    one-or-many shape, each reference in the manifest, the required arguments and the
    exactly-one groups), then sign-in for an action that writes.
    """
    name, args = action['action'], action['args']
    if name not in ACTIONS:
        return None, 'not_in_catalogue'
    spec = ACTIONS[name]
    if type(args) is not dict:
        return None, 'argument_not_in_manifest'
    resolved = {}
    for arg, value in args.items():
        if arg not in spec['args']:
            return None, 'argument_not_in_manifest'
        schema = spec['args'][arg]
        entries = manifest['ids'][schema['ids']]
        refs = value if schema['many'] else [value]
        if type(refs) is not list or not refs or len(set(map(str, refs))) != len(refs):
            return None, 'argument_not_in_manifest'
        found = []
        for ref in refs:
            identifier = _resolve(entries, ref) if type(ref) is str else None
            if identifier is None:
                return None, 'argument_not_in_manifest'
            found.append(identifier)
        resolved[arg] = found if schema['many'] else found[0]
    if any(arg not in args for arg in spec['required']):
        return None, 'argument_not_in_manifest'
    for group in spec['one_of']:
        if sum(arg in args for arg in group) != 1:
            return None, 'argument_not_in_manifest'
    if writes(name) and manifest['signed_in'] is not True:
        return resolved, 'needs_sign_in'
    return resolved, None


def action_record(actions, manifest):
    """The receipt's actions block: ``{'proposed', 'refused', 'run'}``.

    ``proposed`` lists every action the plan proposed, in order, with its references, its
    resolved identifiers and the catalogue's flags (``writes``, ``sign_in``, ``confirm``;
    ``None`` for a name outside the catalogue). ``refused`` lists each refused action by its
    position with the refusal reason key. ``run`` is empty: the composer executes nothing.
    """
    proposed, refused = [], []
    for index, action in enumerate(actions):
        resolved, refusal = check_action(action, manifest)
        spec = ACTIONS.get(action['action'])
        proposed.append({'action': action['action'], 'args': dict(action['args']),
                         'reason_key': action['reason_key'],
                         'resolved': None if refusal and refusal != 'needs_sign_in' else resolved,
                         'writes': None if spec is None else writes(action['action']),
                         'sign_in': None if spec is None else spec['sign_in'],
                         'confirm': None if spec is None else spec['confirm']})
        if refusal is not None:
            refused.append({'index': index, 'action': action['action'], 'reason_key': refusal})
    return {'proposed': proposed, 'refused': refused, 'run': []}
