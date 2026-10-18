"""SDK-free transaction port and canonical state codec for the shared H0 service."""
from dataclasses import dataclass
from typing import Protocol

from src.contracts.jsonutil import canonical_dumps, parse_json
from .errors import ReviewError, require
from .repository import ReviewService, apply_operations

TABLES = ('records', 'latest', 'cases', 'heads', 'outlooks', 'history', 'receipts', 'stale', 'http_receipts')

#: Firestore refuses more than 500 documents in one transaction, and a `commit` writes one
#: document per changed entry plus the case root. `PersistentRepository.provision` commits a
#: whole case in one transaction, so a case's entry count is its write count; the stores'
#: existing 450-change and 2000-entry bounds keep every commit legal. The count of a real
#: case is asserted against this number in tests/test_demo_session_batch.py.
TRANSACTION_WRITE_LIMIT = 500


class StorageUnavailable(Exception):
    """Safe adapter availability failure; underlying details are never public."""


class RetryPreparation(Exception):
    """The case changed; render again outside the storage transaction."""


@dataclass
class Snapshot:
    generation: int
    entries: dict
    membership: dict


class TransactionStore(Protocol):
    def load(self, actor, case: str) -> Snapshot: ...
    def commit(self, actor, case: str, before: Snapshot, after: dict) -> None: ...


def encode(service):
    result = {}
    for table in TABLES:
        for key, value in getattr(service, '_' + table, {}).items():
            result[canonical_dumps([table, list(key)])] = canonical_dumps(value)
    return result


def decode(entries):
    service = ReviewService()
    service._http_receipts = {}
    for key, value in entries.items():
        table, parts = parse_json(key)[0]
        require(table in TABLES)
        getattr(service, '_' + table)[tuple(parts)] = parse_json(value)[0]
    return service


def current_actor(actor, case, membership):
    """A caller can narrow its authority, never expand current server authority."""
    from .repository import ActorContext
    m = membership
    require(type(m) is dict and set(m) == {'uid', 'tenant_id', 'case_id', 'active', 'can_review', 'source_policy_refs'}, 'ACCESS_DENIED')
    require(m['uid'] == actor.actor_id and m['tenant_id'] == actor.tenant_id and m['case_id'] == case, 'ACCESS_DENIED')
    require(m['active'] is True and type(m['can_review']) is bool, 'ACCESS_DENIED')
    policies = m['source_policy_refs']
    require(type(policies) is list and all(type(x) is str and x.strip() for x in policies), 'ACCESS_DENIED')
    require(len(set(policies)) == len(policies) and case in actor.accessible_cases, 'ACCESS_DENIED')
    return ActorContext(actor.actor_id, actor.tenant_id, frozenset({case}),
                        actor.source_policy_refs & frozenset(policies), actor.can_review and m['can_review'])


class PersistentRepository:
    """Prepare pure H0 operations outside transactions, CAS their complete state diff."""
    def __init__(self, store):
        self.store = store
        self.before_commit = None  # injected failure/race probe, outside transaction callbacks

    def provision(self, actor, case, operations):
        """One prepared batch per case: load once, apply, commit the complete state once.

        ``operations`` is the ordered ``(method, args, kwargs)`` sequence
        `src.review.repository.apply_operations` applies to the decoded service, naming the
        same seeding ports a caller would otherwise call one at a time. The difference is the
        storage shape: the case is read once, every operation runs against that one decoded
        copy, and the whole resulting state is committed in a single CAS commit — so a reader
        sees the case before the batch or complete after it, never a part of it. A failure in
        any operation, or at the commit, writes nothing. Retries keep the existing meaning:
        the batch is re-applied to a freshly loaded case, and prepared writes are pure.
        """
        require(type(case) is str and bool(case.strip()), 'ACCESS_DENIED')
        return self.execute(actor, case,
                            lambda service, fresh: apply_operations(service, fresh, operations))

    def execute(self, actor, case, operation):
        for _ in range(5):
            before = self.store.load(actor, case)
            fresh = current_actor(actor, case, before.membership)
            service = decode(before.entries)
            result = operation(service, fresh)
            after = encode(service)
            if self.before_commit:
                self.before_commit()
            try:
                # Even reads recheck generation/membership before returning old private data.
                self.store.commit(actor, case, before, after)
                return result
            except RetryPreparation:
                continue
        raise StorageUnavailable()

    def __getattr__(self, name):
        if name not in {'register_case', 'register', 'seed_assumption', 'build_snapshot', 'compile_task',
                        'prepare_task', 'commit_review', 'read', 'heads', 'history', 'receipt',
                        'draft_status', 'prepare_scenario', 'export_scenario', 'judgment_input',
                        'save_judgment', 'workspace'}:
            raise AttributeError(name)
        def invoke(actor, *args, **kwargs):
            if name in ('register_case', 'register', 'commit_review'):
                case = args[0].get('case_id') if type(args[0]) is dict else None
            elif name == 'seed_assumption':
                case = args[3].get('case_id')
            else:
                case = args[0]
            require(type(case) is str and bool(case.strip()), 'ACCESS_DENIED')
            return self.execute(actor, case, lambda s, a: getattr(s, name)(a, *args, **kwargs))
        return invoke
