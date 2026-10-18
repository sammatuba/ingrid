"""The ports `src/api/hosted.py` hands the agent service (DOCK-5), independent of HTTP.

* :class:`PlanSets`: the baked plan sets (`<data>/views/<key>.json`, BAKE-1), the recorded answers an
  anonymous ask is served from, and the cutoff each page's plans were composed at (`cutoff_for`).
* :class:`AgentRecords`: the records provider per page. A base provider supplies the composer's four
  record kinds (event, outlook, impact, judgment); the book adapter adds what BOOK-4 names: its
  vintages in the outlook record (so `_visible_outlooks` withholds the ones issued after the cutoff),
  the exposure record of the book window and, when a vintage is issued by the cutoff, the book impact
  record. `ids(owner, case_ref, page_key)` is the book's manifest identifiers.
* the book adapter itself is built by `src/api/hosted.py` (`book_adapter`): this package imports
  no other lane's internals (`tests/test_agent_fakes.py` `ImportBoundary`), so it only calls the
  adapter's methods and treats any of its refusals as the `ValueError` they are.
* :func:`review_decision_writer`: the `save_decision` port over the review repository's
  `commit_review`; the draft body is the review request's own fields (:data:`DECISION_BODY_KEYS`),
  and the request carries the confirmation's `request_id` and `idempotency_key`.

Nothing here writes outside the port it wraps, logs, or imports the web layer. Files are read
with the built-in `open` only (the package's import boundary admits no path module).
"""
import copy
import json
import re

VIEW_KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
DESK = 'desk'
#: The book question every page offers (BOOK-4, the strategy's worked example): "What is exposed in
#: Visayas tomorrow 13:00 to 15:00?" over the day the synthetic vintages price.
BOOK_REGION = 'Visayas'
BOOK_WINDOW = '2026-10-19T13:00/2026-10-19T15:00'

#: The `decision_reason` draft body: the review request of `commit_review` without the fields the
#: writer fills (`request_id`, `idempotency_key`, `reviewed_at`, `recorded_at`). `judgment_ref` is
#: optional there and here.
DECISION_BODY_KEYS = frozenset({'case_id', 'task_ref', 'snapshot_digest', 'expected_assumption_head',
                                'expected_outlook_head', 'disposition', 'rationale', 'new_value'})
DECISION_OPTIONAL_KEYS = frozenset({'judgment_ref'})


def _instant(value):
    """The UTC instant of an ISO 8601 stamp with an offset (`Z` included), else None."""
    from datetime import datetime, timezone
    if type(value) is not str or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


class PlanSets:
    """The baked plan sets of one data directory, read once per key (the bake is immutable)."""

    def __init__(self, data_dir):
        self.root = str(data_dir).rstrip('/') + '/views' if data_dir is not None else None
        self._read = {}

    def key(self, case_ref, page_key):
        """The plan set a request reads: the case's own (an event id) when baked, else the page's."""
        for candidate in ((case_ref if case_ref != DESK else None), page_key):
            if type(candidate) is str and VIEW_KEY.fullmatch(candidate) and candidate != 'index' \
                    and self.views(candidate):
                return candidate
        return None

    def views(self, key):
        if self.root is None or type(key) is not str or not VIEW_KEY.fullmatch(key) or key == 'index':
            return []
        if key not in self._read:
            from src.judgment.view import read_view_set
            try:
                with open(self.root + '/' + key + '.json', encoding='utf-8') as handle:
                    document = json.load(handle)
                self._read[key] = [view for _version, view in read_view_set(document)]
            except (OSError, ValueError):
                self._read[key] = []
        return copy.deepcopy(self._read[key])

    def answers(self, case_ref, page_key):
        """`recorded_answers(case_ref, page_key)`: the views of the plan set the request reads."""
        key = self.key(case_ref, page_key)
        return self.views(key) if key else []

    def cutoff_for(self, case_ref, page_key):
        """The cutoff the page's recorded plans were composed at, or None when none is baked."""
        for view in self.answers(case_ref, page_key):
            if type(view.get('cutoff')) is str and view['cutoff'].strip():
                return view['cutoff']
        return None


class AgentRecords:
    """`records(case_ref, page_key, cutoff)` and `ids(owner, case_ref, page_key)` for the service.

    `base(case_ref, page_key, cutoff) -> records | None` supplies the four required record kinds; a
    page without them answers None (the service then replays the recorded answers). `window` and
    `region` name the book question the page offers (BOOK-4: the strategy's Visayas window).
    """

    def __init__(self, base=None, book=None, window=None, region=None):
        self.base, self.book, self.window, self.region = base, book, window, region

    def _vintages(self):
        if self.book is None:
            return []
        try:
            return self.book.vintages()
        except Exception:  # noqa: BLE001 - an unreadable archive lists no vintage, never an error
            return []

    def __call__(self, case_ref, page_key, cutoff):
        records = self.base(case_ref, page_key, cutoff) if self.base is not None else None
        if type(records) is not dict:
            return None
        records = copy.deepcopy(records)
        if self.book is None:
            return records
        vintages = self._vintages()
        outlook = records.get('outlook')
        if type(outlook) is dict and type(outlook.get('outlooks')) is list:
            known = {v.get('outlook_id') for v in outlook['outlooks'] if type(v) is dict}
            outlook['outlooks'] = outlook['outlooks'] + [v for v in vintages if v['outlook_id'] not in known]
        if self.window is None or cutoff is None:
            return records
        try:
            exposure = self.book.exposure_record(self.window, cutoff, region=self.region)
        except ValueError:  # the adapter's refusals (BookError) are ValueErrors
            return records
        records['exposure'] = exposure
        impact = self._impact(vintages, exposure, cutoff)
        if impact is not None:
            records['book_impact'] = impact
        return records

    def _impact(self, vintages, exposure, cutoff):
        """The impact record against the newest vintage issued by the cutoff that prices the
        window's region (BOOK-2 refuses a vintage of another region, `BAND_REGION_MISMATCH`, and
        that vintage is passed over); None when no vintage answers."""
        known = []
        stated = _instant(cutoff)
        for vintage in vintages:
            issued = _instant(vintage.get('issued_at'))
            if stated is not None and issued is not None and issued <= stated:
                known.append(vintage)
        accounts = [block['account_id'] for block in exposure.get('accounts', [])]
        for vintage in sorted(known, key=lambda v: v['issued_at'], reverse=True):
            try:
                return self.book.impact_record(vintage['outlook_id'], self.window, cutoff, accounts=accounts)
            except ValueError:
                continue
        return None

    def ids(self, owner, case_ref, page_key):
        """The book's identifiers the action manifest offers (accounts, nodes, the window)."""
        if self.book is None:
            return {}
        try:
            return self.book.manifest_ids(windows=[self.window] if self.window else ())
        except ValueError:
            return {}


def decision_body_problems(body):
    """Why a `decision_reason` draft body is not the review request's shape (empty when it is)."""
    if type(body) is not dict:
        return ['the body is not a mapping']
    keys = set(body)
    problems = ['missing ' + key for key in sorted(DECISION_BODY_KEYS - keys)]
    problems += ['not a review field: ' + key for key in sorted(keys - DECISION_BODY_KEYS - DECISION_OPTIONAL_KEYS)]
    if not problems and (type(body['case_id']) is not str or not body['case_id'].strip()):
        problems.append('case_id is blank')
    return problems


def review_decision_writer(commit_review, actor_for, clock):
    """The `decision_writer(owner, request)` port over `commit_review(actor, request)`.

    `actor_for(owner, case_id) -> ActorContext | None` resolves who writes in the review repository;
    without it there is no write path (None: the service refuses `save_decision` with
    `no_write_path` before any confirmation is parked). An owner it cannot resolve raises, which
    the service records as a refused receipt (`write_failed`) under the confirmation.
    """
    if commit_review is None or actor_for is None:
        return None

    def write(owner, request):
        problems = decision_body_problems({k: v for k, v in request.items()
                                           if k not in ('request_id', 'idempotency_key')})
        if problems:
            raise ValueError('the decision draft is not a review request: ' + '; '.join(problems))
        actor = actor_for(owner, request['case_id'])
        if actor is None:
            raise LookupError('no review actor for this owner')
        at = clock()
        command = {k: request[k] for k in DECISION_BODY_KEYS | (DECISION_OPTIONAL_KEYS & set(request))}
        command.update(request_id=request['request_id'], idempotency_key=request['idempotency_key'],
                       reviewed_at=at, recorded_at=at)
        receipt = commit_review(actor, command)
        refs = []
        for name in ('decision_ref', 'outlook_ref', 'assumption_ref'):
            ref = receipt.get(name) if type(receipt) is dict else None
            if type(ref) is dict:
                refs.append(dict(ref, kind=ref.get('record_kind')))
        return refs
    return write
