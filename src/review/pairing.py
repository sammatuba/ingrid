"""S4 cutoff pairing: the derived, read-only diff of two saved probe bundles.

Frozen by `docs/work/probe-bundle/intent.md` ("Cutoff pairing"): given two
``ProbeBundleArtifact`` references whose tasks share the assumption and the snapshot but
differ in ``information_cutoff``, the view is

    {'before': ref, 'after': ref, 'label_before', 'label_after',
     'changed': [question ids], 'new_passages': [passage refs present only after]}

and a pair with different assumptions, different snapshots or
``after.cutoff <= before.cutoff`` is refused. The view is derived, never stored: nothing
in this module writes a record, calls a backend or reads a clock. Both artifacts and
their tasks are read through the repository's public ``read`` port, whose transitive
access check already decides which saved artifacts this actor may pair, so a source
revoked behind a bundle denies its pair exactly as it denies the bundle itself.

Refusals are typed. :class:`PairingError` carries one code and no record content, and
the API's existing domain-error handler answers it as ``{'code': <code>}``:

* ``PAIR_ASSUMPTION_MISMATCH`` — the two tasks are not for the same assumption.
* ``PAIR_SNAPSHOT_MISMATCH`` — the two tasks were not compiled from the same snapshot.
* ``PAIR_CUTOFF_ORDER`` — ``after`` does not carry a strictly later information cutoff.
* ``PAIR_NOT_A_BUNDLE`` — a reference does not name a saved probe bundle artifact.
* ``PAIR_NO_ATOMIC_ANSWERS`` — an artifact's composition carries no atomic answers, so
  there is nothing to diff. The service never saves such an artifact (a render refusal
  is a result, not a record); the check keeps a hand-built or foreign payload typed
  instead of failing on it.

A query value that is not a record reference at all stays the existing
``INVALID_RECORD``, as a malformed reference is on every other route.
"""
from __future__ import annotations

from src.contracts.jsonutil import canonical_dumps, parse_json
from src.judgment.bundle import QUESTION_SPECS
from .errors import ReviewError, require
from .records import instant, json_copy, valid_ref

PAIR_ASSUMPTION_MISMATCH = 'PAIR_ASSUMPTION_MISMATCH'
PAIR_SNAPSHOT_MISMATCH = 'PAIR_SNAPSHOT_MISMATCH'
PAIR_CUTOFF_ORDER = 'PAIR_CUTOFF_ORDER'
PAIR_NOT_A_BUNDLE = 'PAIR_NOT_A_BUNDLE'
PAIR_NO_ATOMIC_ANSWERS = 'PAIR_NO_ATOMIC_ANSWERS'

#: One sentence per refusal. The pair codes are not in `src/review/errors.MESSAGES`,
#: which owns the stable h0.v1 set; none of these discloses record content.
PAIR_MESSAGES = {
    PAIR_ASSUMPTION_MISMATCH: 'the two tasks are not for the same assumption',
    PAIR_SNAPSHOT_MISMATCH: 'the two tasks are not compiled from the same snapshot',
    PAIR_CUTOFF_ORDER: 'the after pair must carry a strictly later information cutoff',
    PAIR_NOT_A_BUNDLE: 'a pair reference must name a saved probe bundle artifact',
    PAIR_NO_ATOMIC_ANSWERS: 'the artifact carries no atomic answers to diff',
}

#: The eight atomic question ids by question: the rendered names without their form
#: suffix, because pairing is at the question level, across all four forms.
QUESTION_IDS = {spec['id']: f"{spec['id']}_{spec['slug']}" for spec in QUESTION_SPECS}


class PairingError(ReviewError):
    """A typed refusal of a pair, carrying no record content.

    A ``ReviewError`` so the application's existing handler answers it, with a message
    from :data:`PAIR_MESSAGES` rather than ``errors.MESSAGES``, which the frozen core
    codes own.
    """

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, PAIR_MESSAGES[code])


def _require(condition, code):
    """The pair conditions, as typed refusals rather than the core ``require`` codes."""
    if not condition:
        raise PairingError(code)


def _bundle(record):
    """One reference's record as a pairable bundle, or a typed refusal."""
    _require(record.get('record_kind') == 'ProbeBundleArtifact', PAIR_NOT_A_BUNDLE)
    _require(type(record['payload']['composed'].get('atomic')) is dict, PAIR_NO_ATOMIC_ANSWERS)
    return record


def _view(before_ref, before, after_ref, after, before_task, after_task):
    """The frozen six-key view, or the frozen refusals in their frozen order.

    The assumptions are compared by ``assumption_ref['record_id']``, the assumption
    identity the compiler keys a task by (``assumption_id``); the snapshots by their
    full reference, because the frozen text says the two tasks share the snapshot. A
    question is changed when the two artifacts' stored atomic answers differ;
    ``new_passages`` keeps the after task's context order and carries the later task's
    passage references, which the reads above have already shown this actor may see.
    """
    before_composed, after_composed = before['payload']['composed'], after['payload']['composed']
    before_payload, after_payload = before_task['payload'], after_task['payload']
    _require(before_payload['assumption_ref']['record_id'] == after_payload['assumption_ref']['record_id'],
             PAIR_ASSUMPTION_MISMATCH)
    _require(before_payload['snapshot_ref'] == after_payload['snapshot_ref'], PAIR_SNAPSHOT_MISMATCH)
    _require(instant(after_payload['information_cutoff']) > instant(before_payload['information_cutoff']),
             PAIR_CUTOFF_ORDER)
    before_atomic, after_atomic = before_composed['atomic'], after_composed['atomic']
    changed = [QUESTION_IDS[spec['id']] for spec in QUESTION_SPECS
               if before_atomic.get(spec['id']) != after_atomic.get(spec['id'])]
    carried = {canonical_dumps(item['passage_ref']) for item in before_payload['context']}
    new_passages, seen = [], set()
    for item in after_payload['context']:
        key = canonical_dumps(item['passage_ref'])
        if key not in carried and key not in seen:
            seen.add(key)
            new_passages.append(json_copy(item['passage_ref']))
    return {'before': json_copy(before_ref), 'after': json_copy(after_ref),
            'label_before': before_composed['label'], 'label_after': after_composed['label'],
            'changed': changed, 'new_passages': new_passages}


def pair(repository, actor, case, before_ref, after_ref):
    """The derived cutoff-pair view of two saved bundles; reads only, writes nothing.

    The references are the caller's; the two artifacts and their tasks come from the
    repository's public ``read`` port, so access is the repository's decision and no
    pairing-specific port or allow-list entry is needed. A pair request that is not a
    readable saved bundle is refused before any derivation: ``ACCESS_DENIED`` or
    ``MISSING_INPUT`` from the reads, then the typed codes above.
    """
    before = _bundle(repository.read(actor, case, before_ref))
    after = _bundle(repository.read(actor, case, after_ref))
    return _view(before_ref, before, after_ref, after,
                 repository.read(actor, case, before['payload']['task_ref']),
                 repository.read(actor, case, after['payload']['task_ref']))


def query_ref(text):
    """A record reference from one query-string value: strict JSON of the exact shape.

    The frozen route carries the two references as their JSON encoding in the query
    string (``?before=<ref>&after=<ref>``), percent-encoded by the caller as usual. The
    shape check is the shared one; whether the reference names a probe bundle is the
    pair's own typed decision (:data:`PAIR_NOT_A_BUNDLE`), not a parse error.
    """
    value, error = parse_json(text)
    require(error is None, 'INVALID_RECORD')
    valid_ref(value)
    return value


def register_pair_route(app, prefix, repository, actor):
    """Register the additive ``GET <prefix>/probe-bundles/pair`` route on ``app``.

    ``prefix`` is the frozen tenant/case prefix and ``actor`` the application's actor
    dependency, so ``src/api`` adds one import and one call and this module owns the
    handler. ``fastapi`` is imported here rather than at module scope: the offline suite
    imports this module on a stdlib interpreter, and pairing itself depends on no HTTP
    framework. The route is read-only; a replay is not involved, so it needs no backend
    and no clock.
    """
    from fastapi import Depends

    @app.get(prefix + '/probe-bundles/pair')
    def pair_bundles(case: str, before: str, after: str, a=Depends(actor)):
        return pair(repository, a, case, query_ref(before), query_ref(after))

    return pair_bundles
