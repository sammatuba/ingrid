"""The action catalogue as the agent service reads it.

The catalogue is DOCK-1's (`src/judgment/actions.py`, contract section 2). This module imports it
lazily by name and, while that file is absent, falls back to a local copy of the contract's table.
Only the flags the executor needs are read: whether an action writes, needs sign-in, needs a
confirmation. Argument schemas over the manifest are DOCK-1's validator's; the executor checks the
argument names it uses and nothing else.
"""
import importlib

FREE = ('open', 'query_exposure', 'query_impact', 'search_web', 'pin', 'draft')
WRITING = ('mark_stale', 'reissue_outlook', 'save_decision', 'share')

#: Contract section 2, copied: name -> (argument names, writes, sign-in, confirm). `writes` here is
#: the contract's column: the private copy counts as a write that needs sign-in but no confirmation.
FALLBACK = {
    'open': {'args': ('route', 'record_id'), 'writes': False, 'sign_in': False, 'confirm': False},
    'query_exposure': {'args': ('account_ids', 'node_ids', 'window', 'cutoff'), 'writes': False,
                       'sign_in': False, 'confirm': False},
    # BOOK-4: the impact query names its window and cutoff too (the adapter refuses without them).
    'query_impact': {'args': ('account_ids', 'outlook_id', 'window', 'cutoff'), 'writes': False,
                     'sign_in': False, 'confirm': False},
    'search_web': {'args': ('question_id', 'cutoff'), 'writes': True, 'sign_in': True, 'confirm': False},
    'pin': {'args': ('record_id', 'passage_id', 'thread_id'), 'writes': True, 'sign_in': True, 'confirm': False},
    'draft': {'args': ('kind', 'record_ids'), 'writes': True, 'sign_in': True, 'confirm': False},
    'mark_stale': {'args': ('assumption_id', 'revision'), 'writes': True, 'sign_in': True, 'confirm': True},
    'reissue_outlook': {'args': ('draft_id',), 'writes': True, 'sign_in': True, 'confirm': True},
    'save_decision': {'args': ('draft_id', 'event_id', 'case_id'), 'writes': True, 'sign_in': True, 'confirm': True},
    'share': {'args': ('thread_id', 'view_id'), 'writes': True, 'sign_in': True, 'confirm': True},
}

MODULE = 'src.judgment.actions'
#: Names the DOCK-1 module may export its table under, read in this order.
TABLE_NAMES = ('ACTIONS', 'CATALOGUE', 'ACTION_CATALOGUE')


def _flags(entry):
    """One entry of DOCK-1's table as the executor's flags, or None when it cannot be read.

    `writes` is a bool or, as DOCK-1 gives it, a list or tuple of the record kinds written (an
    empty one writes nothing); `sign_in` and `confirm` are bools; `args` is a dict of argument
    schemas or a list of names.
    """
    if not isinstance(entry, dict):
        return None
    flags = {}
    for key, names in (('writes', ('writes',)), ('sign_in', ('sign_in', 'needs_sign_in')),
                       ('confirm', ('confirm', 'needs_confirmation', 'confirmation'))):
        found = [entry[n] for n in names if n in entry]
        if not found:
            return None
        value = found[0]
        if key == 'writes' and type(value) in (list, tuple):
            if not all(type(kind) is str for kind in value):
                return None
            value = bool(value)
        if type(value) is not bool:
            return None
        flags[key] = value
    args = entry.get('args')
    if isinstance(args, dict):
        flags['args'] = tuple(args)
    elif isinstance(args, (list, tuple)):
        flags['args'] = tuple(a if isinstance(a, str) else a.get('name') for a in args)
    else:
        return None
    return flags


def load():
    """`(table, source)`: DOCK-1's catalogue when it is present and readable, else the local copy.

    `source` is `'src.judgment.actions'` or `'fallback'`. A present module whose table cannot be read
    entry by entry falls back whole, so the executor never mixes the two tables.
    """
    try:
        module = importlib.import_module(MODULE)
    except ImportError:
        return {k: dict(v) for k, v in FALLBACK.items()}, 'fallback'
    for name in TABLE_NAMES:
        table = getattr(module, name, None)
        if isinstance(table, dict) and table:
            read = {action: _flags(entry) for action, entry in table.items()}
            if all(v is not None for v in read.values()):
                return read, MODULE
    return {k: dict(v) for k, v in FALLBACK.items()}, 'fallback'
