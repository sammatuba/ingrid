"""The agent service: ask, confirm and decline, the queue, independent of HTTP.

`ask` plans through the composer (`src/judgment/view.py`'s `answer_question`, which renders the
request from the records, validates the plan and records the actions block), then executes the
actions the plan proposes:

* the identifiers come from the composer's actions block (`receipt.actions.proposed[i].resolved`),
  never from the plan's own arguments, which are manifest handles such as `record-a`; an action
  the composer refused (`receipt.actions.refused`) is recorded as a refused receipt under the
  composer's reason key and never runs. Only an answer without an actions block (view.v3, or a
  composer handed in that has none) falls back to the plan's arguments;
* the free actions (`open`, `query_exposure`, `query_impact`, `search_web` through the search
  adapter, `pin`, `draft`) run at once, and each leaves an action receipt;
* the writing actions (`mark_stale`, `reissue_outlook`, `save_decision`, `share`) never run here:
  each becomes a confirmation in state `pending` with a preview of what would be written, where,
  and under which receipt; a write that could not run is refused before any confirmation is parked;
* a request without an owner runs only `open`, `query_exposure` and `query_impact`, whatever the
  catalogue table says, plans from the recorded plan sets only and never touches the day meter.
  With a `recorded_answers` provider (DOCK-5: the baked plan sets), an anonymous ask is answered
  with the recorded view whose question or one of its four wordings it matches, and nothing else;
  a signed-in ask whose page has no record set is answered the same way.

`confirm` decides a pending confirmation once. Only a confirmation the store returned in state
`confirmed` reaches `_execute_write`, the one function that calls a writing API, and it refuses
anything else (`NotConfirmed`). Each write goes through the existing API of the record it writes:

* `mark_stale` -> `src.outlook.dependency.mark_stale` on the archive handed in (exclusive create of
  each `StaleMark`); the mark's key set is closed, so the action receipt cites the confirmation id
  and each mark's content digest;
* `reissue_outlook` -> `OutlookArchive.issue` (exclusive create of the `OutlookRecord`) from a
  `reissue` draft whose body is the outlook's own fields, validated by `build_outlook` when drafted;
  the issued record's `issuer` cites the confirmation id;
* `save_decision` -> the decision writer handed in (the review repository's `commit_review` port);
  the request's `request_id` and `idempotency_key` are the confirmation id;
* `share` -> the share writer handed in. Absent writers refuse with `no_write_path`: this package
  creates no write path of its own for another lane's record.

A write that fails after the click is a refused receipt (`write_failed`, or the API's own refusal
code), never an exception; the confirmation stays `confirmed`, the person's recorded decision.
Nothing here logs, prints or imports the web layer.
"""
import copy
import hashlib
import re
import uuid
from datetime import datetime, timezone

from src.judgment import JudgmentUnavailable

from . import catalogue
from .budget import ALLOWED, DayMeter
from .fakes import FakeSearch, open_cases
from .store import AlreadyDecided, RecordExists, UnknownRecord, owner_id, thread_id

IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
ROUTE = re.compile(r'/[A-Za-z0-9/_.-]{0,200}\Z')
#: A register revision: a commit id, short or full (`src/outlook/dependency.py` REVISION).
REVISION = re.compile(r'[0-9a-f]{7,40}\Z')
MAX_QUESTION = 500
DRAFT_KINDS = ('case', 'decision_reason', 'reissue')
DESK = 'desk'
#: The only actions a request without an owner may run: reads that write nothing anywhere.
PUBLIC_READS = ('open', 'query_exposure', 'query_impact')
#: The caller identifier kinds the composer's action manifest takes (src/judgment/actions.py).
CALLER_ID_KINDS = ('accounts', 'nodes', 'windows', 'revisions', 'passages', 'threads', 'views',
                   'drafts', 'cases', 'assumptions')

DONE, REFUSED, NEEDS_CONFIRMATION = 'done', 'refused', 'needs_confirmation'
ARG_REFUSED = 'argument_not_in_manifest'  # DOCK-1's spelling (src/judgment/actions.py REFUSALS)
WRITE_FAILED = 'write_failed'


class InvalidInput(Exception):
    """A request body the route answers 422 for; `field` and `reason` say what was refused."""

    def __init__(self, field, reason):
        self.field, self.reason = field, reason
        super().__init__(f'{field}: {reason}')


class NotConfirmed(Exception):
    """A write was asked for a confirmation that is not in state confirmed: no write path exists."""


class _Refused(Exception):
    def __init__(self, reason_key):
        self.reason_key = reason_key
        super().__init__(reason_key)


class _BudgetRefused(Exception):
    """The live planner's calls would pass the day's line; the recorded plan sets answer instead."""


class _Metered:
    """The live planner behind the day meter: each `decide` charges its forms before the call.

    A question the composer answers without calling the planner (insufficient before planning)
    charges nothing, because no live call runs. The attributes the composer checks are the
    planner's own.
    """

    def __init__(self, backend, meter):
        self._backend, self._meter, self.outcome = backend, meter, None

    def __getattr__(self, name):
        return getattr(self._backend, name)

    def decide(self, request):
        forms = request.get('forms') or request.get('wordings') or [None]
        self.outcome = self._meter.charge(len(forms))
        if self.outcome['outcome'] != ALLOWED:
            raise _BudgetRefused()
        return self._backend.decide(request)


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _new_id():
    return uuid.uuid4().hex


def _normal(text):
    return ' '.join(text.split()).casefold()


def _identifier(value):
    return type(value) is str and IDENTIFIER.fullmatch(value) is not None


def _ids(value):
    return type(value) is list and bool(value) and all(_identifier(v) for v in value)


def _ask_body(body):
    if type(body) is not dict:
        raise InvalidInput('body', 'a JSON object')
    unknown = set(body) - {'question', 'thread', 'page_key', 'cutoff'}
    if unknown:
        raise InvalidInput(sorted(unknown)[0], 'not a field of an ask')
    question = body.get('question')
    if type(question) is not str or not question.strip() or len(question) > MAX_QUESTION:
        raise InvalidInput('question', f'a question of 1 to {MAX_QUESTION} characters')
    thread = body.get('thread', DESK)
    if not _identifier(thread):
        raise InvalidInput('thread', 'desk, or the id of an event, alert or case')
    page_key = body.get('page_key')
    if page_key is not None and not _identifier(page_key):
        raise InvalidInput('page_key', 'a page key')
    cutoff = body.get('cutoff')
    if cutoff is not None and (type(cutoff) is not str or not cutoff.strip()):
        raise InvalidInput('cutoff', 'an instant with an offset')
    return question.strip(), thread, page_key, cutoff


def proposed_actions(answer):
    """`[(action, args, refusal_key)]` to execute or record, from a composed answer.

    With the composer's actions block (view.v4: `receipt.actions`), each proposed entry carries
    its resolved identifiers and each refused entry its reason key, matched by index. Without a
    block, the answer's own `actions` (or the plan's) are read with their arguments as given.
    """
    if type(answer) is not dict:
        return []
    receipt = answer.get('receipt') if type(answer.get('receipt')) is dict else {}
    block = receipt.get('actions')
    if type(block) is dict and type(block.get('proposed')) is list:
        refused = {item.get('index'): item.get('reason_key') for item in block.get('refused') or []
                   if type(item) is dict}
        out = []
        for index, entry in enumerate(block['proposed']):
            if type(entry) is not dict:
                out.append((None, {}, 'not_in_catalogue'))
                continue
            resolved = entry.get('resolved') if type(entry.get('resolved')) is dict else {}
            refusal = refused.get(index) or (None if type(entry.get('resolved')) is dict else ARG_REFUSED)
            out.append((entry.get('action'), resolved, refusal))
        return out
    actions = answer.get('actions')
    if type(actions) is not list:
        plan = receipt.get('plan')
        actions = plan.get('actions') if type(plan) is dict else None
    if type(actions) is not list:
        return []
    return [(a.get('action'), a.get('args', {}), None) if type(a) is dict else (None, {}, None)
            for a in actions]


def validate_reissue_body(body):
    """A `reissue` draft's body is the `OutlookRecord`'s own fields; `build_outlook` validates it."""
    from src.outlook.records import OutlookError, build_outlook
    if type(body) is not dict:
        raise _Refused('draft_invalid')
    try:
        return build_outlook(**body)
    except (OutlookError, TypeError):
        raise _Refused('draft_invalid') from None


def _confirmation_view(doc):
    return {k: doc.get(k) for k in ('confirmation_id', 'action', 'args', 'preview', 'state', 'decided_at')}


class AgentService:
    """The agent's work over its store and the adapters it is handed.

    `records(case_ref, page_key, cutoff) -> records | None` supplies the composer's records and
    `cutoff_for(case_ref, page_key) -> cutoff | None` the cutoff when an ask names none;
    `ids(owner, case_ref, page_key) -> {kind: [ids]}` the caller identifiers the action manifest
    offers (accounts, nodes, windows, revisions, ...; the owner's open drafts and the thread are
    added here). `recorded_backend` is the recorded plan sets' planner (the only one an anonymous
    ask uses); `live_backend` is the live planner for signed-in users under the day meter;
    `composer` is `view.answer_question` unless a test hands in another with its signature. `book`,
    `search`, `archive`, `register_payload`, `decision_writer`, `share_writer` and `drafters` are
    the adapters the actions call; an absent one makes its action refuse with a recorded reason.
    """

    def __init__(self, store, records=None, recorded_backend=None, live_backend=None, meter=None,
                 composer=None, book=None, search=None, archive=None, register_payload=None,
                 decision_writer=None, share_writer=None, drafters=None, site_routes=None,
                 demonstration=False, clock=_utc_now, ids=None, cutoff_for=None, new_id=_new_id,
                 live_repeats=3, recorded_answers=None):
        self.store, self.records = store, records
        if recorded_backend is None:
            from src.judgment.view import fixture_backend
            recorded_backend = fixture_backend()
        self.recorded_backend, self.live_backend = recorded_backend, live_backend
        self.meter = meter if meter is not None else DayMeter(store, clock=clock)
        if composer is None:
            from src.judgment.view import answer_question
            composer = answer_question
        self.composer = composer
        self.book, self.search = book, search if search is not None else FakeSearch()
        self.archive, self.register_payload = archive, register_payload
        self.decision_writer, self.share_writer = decision_writer, share_writer
        self.drafters = dict(drafters or {})
        self.site_routes = tuple(site_routes) if site_routes is not None else None
        self.demonstration = bool(demonstration)
        self.clock, self.caller_ids, self.cutoff_for = clock, ids, cutoff_for
        self.new_id, self.live_repeats = new_id, live_repeats
        self.recorded_answers = recorded_answers
        self.actions, self.actions_source = catalogue.load()

    # ------------------------------------------------------------------------------ asking
    def _manifest_ids(self, owner, case_ref, page_key, tid):
        supplied = dict(self.caller_ids(owner, case_ref, page_key) or {}) if self.caller_ids else {}
        ids = {kind: list(supplied.get(kind) or []) for kind in CALLER_ID_KINDS if kind in supplied}
        if owner:
            drafts = [d['draft_id'] for d in self.store.drafts(owner, state='draft')]
            ids['drafts'] = ids.get('drafts', []) + [d for d in drafts if d not in ids.get('drafts', [])]
            ids['threads'] = ids.get('threads', []) + ([tid] if tid not in ids.get('threads', []) else [])
        return {k: v for k, v in ids.items() if v}

    def _compose(self, question, records, cutoff, backend, signed_in, free_text, ids):
        if records is None or cutoff is None:
            return {'status': 'insufficient', 'reason_key': 'no_record', 'question': question,
                    'cutoff': cutoff, 'components': [], 'receipt': None}
        try:
            return self.composer(question, records, cutoff, backend, signed_in=signed_in,
                                 free_text=free_text, repeats=self.live_repeats, ids=ids)
        except _BudgetRefused:
            raise
        except JudgmentUnavailable as exc:
            return {'status': 'refused', 'reason_key': str(getattr(exc, 'code', 'plan_refused')).lower(),
                    'question': question, 'cutoff': cutoff, 'components': [], 'receipt': None}
        except ValueError:
            return {'status': 'refused', 'reason_key': 'request_refused', 'question': question,
                    'cutoff': cutoff, 'components': [], 'receipt': None}

    def _plan(self, owner, question, records, cutoff, ids):
        """`(answer, budget)`: the live planner under the meter for an owner, else the recorded sets."""
        signed_in = owner is not None
        if signed_in and self.live_backend is not None and records is not None and cutoff is not None:
            metered = _Metered(self.live_backend, self.meter)
            try:
                answer = self._compose(question, records, cutoff, metered, True, True, ids)
                return answer, metered.outcome
            except _BudgetRefused:
                answer = self._compose(question, records, cutoff, self.recorded_backend, True, False, ids)
                return answer, metered.outcome
        return self._compose(question, records, cutoff, self.recorded_backend, signed_in, False, ids), None

    def _recorded(self, question, case_ref, page_key):
        """The recorded view whose question or one of its wordings matches, from the plan sets.

        `recorded_answers(case_ref, page_key) -> [view]` is the baked plan set's views (DOCK-5).
        The match is exact after case folding and collapsing white space; no nearest answer is
        guessed here (the dock offers one itself). No match is the composer's insufficient shape
        under `no_record`.
        """
        wanted = _normal(question)
        for view in self.recorded_answers(case_ref, page_key) or []:
            if type(view) is not dict:
                continue
            receipt = view.get('receipt') if type(view.get('receipt')) is dict else {}
            forms = [view.get('question')] + list(receipt.get('wordings') or [])
            if any(type(form) is str and _normal(form) == wanted for form in forms):
                return copy.deepcopy(view)
        return {'status': 'insufficient', 'reason_key': 'no_record', 'question': question,
                'cutoff': None, 'components': [], 'receipt': None}

    def ask(self, user, body):
        """`POST /api/agent/ask`: the turn, with the composed answer as `view`.

        Returns the turn's fields (`turn_id`, `thread_id`, `at`, `question`, `receipt`,
        `actions_run`, `confirmations_pending`) plus `view` (the composed answer), `confirmations`
        (the pending confirmation objects), `budget` (the meter's outcome for this ask, or today's
        line for a signed-in caller, with `refused`), `signed_in`, `case_ref`, `results` (each free
        action's result by receipt id) and `actions_source`. A signed-in ask is stored: the thread
        for its case (opened when absent), the turn, each receipt and each pending confirmation.
        An anonymous ask is stored nowhere (the dock keeps its thread in the browser).
        """
        question, case_ref, page_key, cutoff = _ask_body(body)
        owner = owner_id(user['uid']) if user else None
        at = self.clock()
        if cutoff is None and self.cutoff_for is not None:
            cutoff = self.cutoff_for(case_ref, page_key)
        replay = self.recorded_answers is not None and owner is None
        records = self.records(case_ref, page_key, cutoff) if self.records and not replay else None
        replay = replay or (self.recorded_answers is not None and records is None)
        thread = self.store.open_thread(owner, case_ref, at) if owner else None
        tid = thread['thread_id'] if thread else None
        if replay:
            answer, budget = self._recorded(question, case_ref, page_key), None
        else:
            answer, budget = self._plan(owner, question, records, cutoff,
                                        self._manifest_ids(owner, case_ref, page_key, tid))
        receipts, results, confirmations = [], {}, []
        for name, args, refusal in proposed_actions(answer):
            receipt, result, confirmation = self._act(owner, tid, name, args, refusal)
            receipts.append(receipt)
            if result is not None:
                results[receipt['receipt_id']] = result
            if confirmation is not None:
                confirmations.append(_confirmation_view(confirmation))
        turn = {'turn_id': self.new_id(), 'thread_id': tid, 'at': at, 'question': question,
                'receipt': answer.get('receipt'), 'actions_run': receipts,
                'confirmations_pending': [c['confirmation_id'] for c in confirmations],
                'budget': budget}
        if owner:
            self.store.append_turn(turn)
        shown_budget = budget if budget is not None else (self.meter.today() if owner else None)
        return dict(turn, view=answer, confirmations=confirmations, budget=shown_budget,
                    signed_in=owner is not None, case_ref=case_ref, results=results,
                    actions_source=self.actions_source)

    # ----------------------------------------------------------------------------- actions
    def _receipt(self, owner, tid, name, args, started, outcome, refs=(), confirmation_id=None,
                 reason_key=None, receipt_id=None):
        return {'receipt_id': receipt_id or self.new_id(), 'owner': owner, 'thread_id': tid, 'action': name,
                'args': args, 'started_at': started, 'ended_at': self.clock(), 'outcome': outcome,
                'record_refs': list(refs), 'confirmation_id': confirmation_id, 'reason_key': reason_key}

    def _keep(self, owner, receipt):
        if owner:
            self.store.add_receipt(receipt)
        return receipt

    def _act(self, owner, tid, name, args, refusal=None):
        """One proposed action: `(receipt, result, confirmation)`; refused, run, or parked."""
        started = self.clock()
        name = name if type(name) is str else None
        args = args if type(args) is dict else {}

        def refused(key, shown_args=None):
            receipt = self._receipt(owner, tid, name, args if shown_args is None else shown_args, started,
                                    REFUSED, reason_key=key)
            return self._keep(owner, receipt), None, None

        if refusal is not None:
            return refused(refusal)  # the composer refused it: recorded, never run
        entry = self.actions.get(name) if name else None
        if entry is None:
            return refused('not_in_catalogue', {})
        if set(args) - set(entry['args']):
            return refused(ARG_REFUSED, {})
        if owner is None and (name not in PUBLIC_READS or entry['writes'] or entry['sign_in'] or entry['confirm']):
            return refused('needs_sign_in')
        try:
            if entry['confirm']:
                receipt_id = self.new_id()
                preview = dict(self._preview(owner, name, args), receipt=receipt_id)
                confirmation = self.store.create_confirmation({
                    'confirmation_id': self.new_id(), 'owner': owner, 'action': name, 'args': args,
                    'preview': preview, 'state': 'pending', 'decided_at': None})
                receipt = self._receipt(owner, tid, name, args, started, NEEDS_CONFIRMATION,
                                        confirmation_id=confirmation['confirmation_id'])
                return self._keep(owner, receipt), None, confirmation
            refs, result = self._run_free(owner, tid, name, args)
        except _Refused as exc:
            return refused(exc.reason_key)
        return self._keep(owner, self._receipt(owner, tid, name, args, started, DONE, refs)), result, None

    def _run_free(self, owner, tid, name, args):
        if name == 'open':
            route = args.get('route')
            if type(route) is not str or ROUTE.fullmatch(route) is None or (
                    self.site_routes is not None and route not in self.site_routes):
                raise _Refused('unknown_route')
            refs = [{'kind': 'route', 'id': route}]
            if args.get('record_id') is not None:
                if not _identifier(args['record_id']):
                    raise _Refused(ARG_REFUSED)
                refs.append({'kind': 'record', 'id': args['record_id']})
            return refs, {'route': route, 'record_id': args.get('record_id')}
        if name in ('query_exposure', 'query_impact'):
            if self.book is None:
                raise _Refused('no_record')
            if not _ids(args.get('account_ids')):
                raise _Refused(ARG_REFUSED)
            if name == 'query_exposure':
                if not _ids(args.get('node_ids')) or type(args.get('cutoff')) is not str:
                    raise _Refused(ARG_REFUSED)
                result = self.book.exposure(args['account_ids'], args['node_ids'], args.get('window'), args['cutoff'])
            else:
                if not _identifier(args.get('outlook_id')):
                    raise _Refused(ARG_REFUSED)
                # BOOK-4: the four-argument call; the adapter refuses a missing window or cutoff.
                result = self.book.impact(args['account_ids'], args['outlook_id'], args.get('window'),
                                          args.get('cutoff'))
            if type(result) is not dict:
                raise _Refused('no_record')
            if result.get('status') == 'refused':
                # The adapter's own stable code, lower case (BOOK-2's codes); no error text.
                key = result.get('reason_key')
                raise _Refused(key if type(key) is str and re.fullmatch(r'[a-z_]{1,64}', key) else 'no_record')
            return [{'kind': name[6:], 'id': result.get('record_id'), 'synthetic': result.get('synthetic')}], result
        if owner is None:
            raise _Refused('needs_sign_in')  # every other action writes into a private copy
        if name == 'search_web':
            if type(args.get('question_id')) is not str or type(args.get('cutoff')) is not str:
                raise _Refused(ARG_REFUSED)
            receipt = self.search.search(args['question_id'], args['cutoff'])
            key = hashlib.sha256((owner + '|' + receipt['receipt_id']).encode('utf-8')).hexdigest()[:32]
            try:
                self.store.save_evidence(key, {'receipt_id': receipt['receipt_id'], 'owner': owner, 'receipt': receipt})
            except RecordExists:
                pass  # the same receipt is already in this owner's private copy
            return [{'kind': 'search_receipt', 'id': receipt['receipt_id'], 'synthetic': receipt.get('synthetic')}], receipt
        if name == 'pin':
            target = [args[k] for k in ('record_id', 'passage_id') if args.get(k) is not None]
            if len(target) != 1 or not _identifier(target[0]):
                raise _Refused(ARG_REFUSED)
            pin_thread = args.get('thread_id', tid)
            thread = self.store.get_thread(pin_thread) if _identifier(pin_thread) else None
            if thread is None or thread['owner'] != owner:
                raise _Refused('not_found')
            return [{'kind': 'pin', 'id': target[0], 'thread_id': pin_thread}], None
        if name == 'draft':
            return self._draft(owner, args)
        raise _Refused('not_in_catalogue')

    def _draft(self, owner, args):
        kind = args.get('kind')
        if kind not in DRAFT_KINDS or not _ids(args.get('record_ids')):
            raise _Refused(ARG_REFUSED)
        drafter = self.drafters.get(kind)
        if drafter is None:
            raise _Refused('no_drafter')
        try:
            made = drafter(owner, args)
        except ValueError:
            raise _Refused('draft_invalid') from None
        if type(made) is not dict or set(made) != {'body', 'rests_on'} or type(made['rests_on']) is not list:
            raise _Refused('draft_invalid')
        if kind == 'reissue':
            validate_reissue_body(made['body'])
        draft = self.store.create_draft({'draft_id': self.new_id(), 'owner': owner, 'kind': kind, 'body': made['body'],
                                         'rests_on': made['rests_on'], 'created_at': self.clock(), 'state': 'draft'})
        return [{'kind': 'draft', 'id': draft['draft_id']}], {'draft_id': draft['draft_id'], 'kind': kind}

    def _open_draft(self, owner, draft_id, kind):
        draft = self.store.get_draft(draft_id) if _identifier(draft_id) else None
        if draft is None or draft['owner'] != owner or draft['kind'] != kind:
            raise _Refused('not_found')
        if draft['state'] != 'draft':
            raise _Refused('draft_not_open')
        return draft

    def _preview(self, owner, name, args):
        """What a writing action would write and where; refused when the write could not happen."""
        if name == 'mark_stale':
            if not _identifier(args.get('assumption_id')) or type(args.get('revision')) is not str \
                    or REVISION.fullmatch(args['revision']) is None:
                raise _Refused(ARG_REFUSED)
            if self.archive is None:
                raise _Refused('no_write_path')
            from src.outlook.records import OutlookError
            try:
                affected = [oid for oid in self.archive.issue_ids()
                            if args['assumption_id'] in self.archive.outlook(oid)['assumption_ids']]
            except OutlookError as exc:
                raise _Refused(exc.code.lower()) from None
            if not affected:
                raise _Refused('no_record')  # no outlook rests on it: the click would write nothing
            return {'what': 'a mark beside each of ' + ', '.join(affected),
                    'where': 'the outlook archive', 'outlooks': affected}
        if name == 'reissue_outlook':
            draft = self._open_draft(owner, args.get('draft_id'), 'reissue')
            if self.archive is None:
                raise _Refused('no_write_path')
            return {'what': 'the outlook vintage ' + str(draft['body'].get('outlook_id')),
                    'where': 'the outlook archive', 'draft_id': draft['draft_id']}
        if name == 'save_decision':
            draft = self._open_draft(owner, args.get('draft_id'), 'decision_reason')
            targets = [args[k] for k in ('event_id', 'case_id') if args.get(k) is not None]
            if len(targets) != 1 or not _identifier(targets[0]):
                raise _Refused(ARG_REFUSED)
            if self.decision_writer is None:
                raise _Refused('no_write_path')
            return {'what': 'a decision record', 'where': 'the decision history of ' + targets[0],
                    'draft_id': draft['draft_id']}
        if name == 'share':
            targets = [args[k] for k in ('thread_id', 'view_id') if args.get(k) is not None]
            if len(targets) != 1 or not _identifier(targets[0]):
                raise _Refused(ARG_REFUSED)
            if self.share_writer is None:
                raise _Refused('no_write_path')
            return {'what': 'a shared copy of ' + targets[0], 'where': 'the shared space'}
        raise _Refused('not_in_catalogue')

    # -------------------------------------------------------------------------- confirming
    def _execute_write(self, confirmation):
        """The only caller of a writing API; refuses any confirmation not in state confirmed.

        Returns the record refs written. Every ref names the record by its own id and digest; the
        action receipt that carries them cites the confirmation id, and so do the issued outlook's
        `issuer` and the decision request's `request_id` and `idempotency_key`.
        """
        if type(confirmation) is not dict or confirmation.get('state') != 'confirmed':
            raise NotConfirmed()
        cid, name, args, owner = (confirmation['confirmation_id'], confirmation['action'],
                                  confirmation['args'], confirmation['owner'])
        if name == 'mark_stale':
            from src.outlook.dependency import DependencyError, mark_stale, marks_of
            if self.archive is None:
                raise _Refused('no_write_path')
            try:
                affected = mark_stale(self.archive, args['assumption_id'], args['revision'], marked_at=self.clock(),
                                      register_payload=self.register_payload, synthetic=self.demonstration)
                marks = [m for m in marks_of(self.archive)
                         if m['assumption_id'] == args['assumption_id'] and m['new_revision'] == args['revision']
                         and m['synthetic'] is self.demonstration and m['outlook_id'] in affected]
            except DependencyError as exc:
                raise _Refused(exc.code.lower()) from None
            return [{'kind': 'StaleMark', 'outlook_id': m['outlook_id'], 'content_digest': m['content_digest']}
                    for m in marks]
        if name == 'reissue_outlook':
            from src.outlook.records import OutlookError, build_outlook
            draft = self._open_draft(owner, args.get('draft_id'), 'reissue')
            if self.archive is None:
                raise _Refused('no_write_path')
            fields = dict(draft['body'], issuer=f"{draft['body'].get('issuer')}, agent confirmation {cid}")
            try:
                issued = self.archive.issue(build_outlook(**fields))
            except OutlookError as exc:
                raise _Refused(exc.code.lower()) from None
            self.store.settle_draft(draft['draft_id'], 'signed')
            return [{'kind': 'OutlookRecord', 'id': issued['outlook_id'], 'content_digest': issued['content_digest']}]
        if name == 'save_decision':
            draft = self._open_draft(owner, args.get('draft_id'), 'decision_reason')
            if self.decision_writer is None:
                raise _Refused('no_write_path')
            request = dict(draft['body'], request_id='agent-confirmation-' + cid,
                           idempotency_key='agent-confirmation-' + cid)
            written = self.decision_writer(owner, request)
            self.store.settle_draft(draft['draft_id'], 'signed')
            return [dict(ref, confirmation_id=cid) for ref in written]
        if name == 'share':
            if self.share_writer is None:
                raise _Refused('no_write_path')
            return [dict(ref, confirmation_id=cid) for ref in self.share_writer(owner, args, cid)]
        raise _Refused('not_in_catalogue')

    def confirm(self, user, confirmation_id, body):
        """`POST /api/agent/confirm/{id}` with `{"decision": "confirm" | "decline"}`.

        Returns `{confirmation_id, state, decided_at, receipt}`. The decision is the person's and is
        made once (`AlreadyDecided` on a second). A confirmed action is executed by `_execute_write`
        and its receipt (under the id the preview named) cites the confirmation; any failure of the
        write is a refused receipt with a fixed reason key and no exception text, never an exception.
        """
        owner = owner_id(user['uid'])
        if type(body) is not dict or set(body) != {'decision'} or body['decision'] not in ('confirm', 'decline'):
            raise InvalidInput('decision', 'confirm or decline')
        current = self.store.get_confirmation(confirmation_id) if _identifier(confirmation_id) else None
        if current is None or current['owner'] != owner:
            raise UnknownRecord('confirmation')
        decided = self.store.decide_confirmation(
            confirmation_id, 'confirmed' if body['decision'] == 'confirm' else 'declined', self.clock())
        out = {'confirmation_id': confirmation_id, 'state': decided['state'], 'decided_at': decided['decided_at'],
               'receipt': None}
        if decided['state'] != 'confirmed':
            return out
        started = self.clock()
        receipt_id = (decided.get('preview') or {}).get('receipt')
        try:
            refs = self._execute_write(decided)
            receipt = self._receipt(owner, None, decided['action'], decided['args'], started, DONE, refs,
                                    confirmation_id=confirmation_id, receipt_id=receipt_id)
        except _Refused as refusal:
            receipt = self._receipt(owner, None, decided['action'], decided['args'], started, REFUSED,
                                    confirmation_id=confirmation_id, reason_key=refusal.reason_key,
                                    receipt_id=receipt_id)
        except AlreadyDecided:
            receipt = self._receipt(owner, None, decided['action'], decided['args'], started, REFUSED,
                                    confirmation_id=confirmation_id, reason_key='draft_not_open',
                                    receipt_id=receipt_id)
        except Exception:  # noqa: BLE001 - any failure of the write is a recorded refusal, never text
            receipt = self._receipt(owner, None, decided['action'], decided['args'], started, REFUSED,
                                    confirmation_id=confirmation_id, reason_key=WRITE_FAILED,
                                    receipt_id=receipt_id)
        try:
            self.store.add_receipt(receipt)
        except RecordExists:
            receipt = dict(receipt, receipt_id=self.new_id())
            self.store.add_receipt(receipt)
        out['receipt'] = receipt
        return out

    # ----------------------------------------------------------------------------- reading
    def threads(self, user):
        """`GET /api/agent/threads`: `{threads, cases, budget}`."""
        return {'threads': self.store.threads(owner_id(user['uid'])), 'cases': self.cases(user)['cases'],
                'budget': self.meter.today()}

    def cases(self, user):
        """`GET /api/agent/cases`: the open cases (the labelled fakes until the case lane lands)."""
        owner = owner_id(user['uid'])
        out = []
        for case in open_cases(owner):
            refs = [case['case_id']] + ([case['event_id'], 'event:' + case['event_id']] if case['event_id'] else [])
            found = [thread_id(owner, ref) for ref in refs if self.store.get_thread(thread_id(owner, ref))]
            out.append(dict(case, thread_id=found[0] if found else None))
        return {'cases': out}

    def thread(self, user, key):
        thread = self.store.get_thread(key) if _identifier(key) else None
        if thread is None or thread['owner'] != owner_id(user['uid']):
            raise UnknownRecord('thread')
        return {'thread': thread, 'turns': self.store.turns(key)}

    def drafts(self, user):
        return {'drafts': self.store.drafts(owner_id(user['uid']))}

    def queue(self, user):
        """`GET /api/agent/queue`: `{items, budget}`; pending confirmations, open drafts, stale vintages.

        A confirmation item is the confirmation object; a draft item `{draft_id, kind, created_at}`;
        a stale vintage `{outlook_id, assumption_id, synthetic}` from the archive's marks (a
        demonstration mark is labelled as one). An archive that cannot be read is one item
        `{unreadable: 'outlook_archive', reason_key}`, never an exception.
        """
        owner = owner_id(user['uid'])
        items = [_confirmation_view(c) for c in self.store.confirmations(owner, state='pending')]
        items += [{'draft_id': d['draft_id'], 'kind': d['kind'], 'created_at': d['created_at']}
                  for d in self.store.drafts(owner, state='draft')]
        if self.archive is not None:
            from src.outlook.dependency import DependencyError, marks_of, stale_outlooks
            try:
                real = set(stale_outlooks(self.archive))
                seen = set()
                for mark in marks_of(self.archive):
                    key = (mark['outlook_id'], mark['assumption_id'], mark['synthetic'])
                    if key in seen or (mark['synthetic'] and mark['outlook_id'] in real):
                        continue
                    seen.add(key)
                    item = {'outlook_id': mark['outlook_id'], 'assumption_id': mark['assumption_id'],
                            'synthetic': mark['synthetic']}
                    if mark['synthetic']:
                        item['label'] = 'Demonstration mark only. Nothing real changed.'
                    items.append(item)
            except DependencyError as exc:
                items.append({'unreadable': 'outlook_archive', 'reason_key': exc.code.lower()})
        return {'items': items, 'budget': self.meter.today()}
