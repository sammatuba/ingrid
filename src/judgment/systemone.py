"""System One port (S2): response validation, the fixture backend and the service.

The request is the frozen shape rendered by :func:`src.judgment.bundle.render_bundle`
(``{'model', 'state', 'questions'}``); the response is the frozen
``{'answers': {name: {'choice', 'probabilities'} | {'noul'}}, 'model_version'}``. A
backend is any object with ``name``, ``model``, ``execution_mode`` in
``('synthetic_fixture', 'live_inference')`` and ``decide(request) -> response``;
:class:`FixtureSystemOne` is the labelled test backend of this slice. Nothing in this
module opens a socket, reads a credential or invents an answer: every stored value is
either the backend's validated response or the S1 renderer's and composer's output.

Failure surface, all :class:`src.judgment.JudgmentUnavailable`:

* ``MODEL_INPUT_LIMIT`` — the rendered state exceeds 128 KiB (raised by the renderer).
* ``MODEL_DISABLED`` — no backend is configured.
* ``MODEL_BUSY`` — one request is already in flight (one-slot semaphore, as for
  judgments).
* ``MODEL_INVALID_RESPONSE`` — the response is not exactly one well-formed answer per
  rendered question, an option is unknown, a probability is outside [0, 1], or the
  response exceeds 64 KiB. Nothing is written.
* ``MODEL_UNAVAILABLE`` — the backend raised. Every exception from ``decide`` maps to
  this one code, a ``JudgmentUnavailable`` raised by the backend itself included, so
  neither the backend's text nor a code of its choosing is ever exposed.

Caller errors stay ``ValueError``. The front-door guards (task readable by this actor,
``compiled``, current heads and dependencies, replay and conflict by idempotency key)
live in :meth:`ReviewService.bundle_input` and raise the existing review codes before
any backend call. A render refusal (``TOO_MANY_CANDIDATES``, ``UNRESOLVED_MAPPING``)
is a result, not an error: no request exists, so nothing is called and nothing is
written.
"""
from __future__ import annotations

import math
from threading import BoundedSemaphore

from src.contracts.jsonutil import canonical_dumps, compute_content_digest
from src.judgment import JudgmentUnavailable
from src.judgment.bundle import BUNDLE_VERSION, compose, receipt, render_bundle
from src.review.records import json_copy

#: The frozen response bound: a response at or below this many canonical bytes is
#: measured as one unit before any field is trusted.
MAX_RESPONSE_BYTES = 64 * 1024
MAX_NAME = 200

#: Provenance of the stored probabilities, read from the backend when it declares one.
#: The Gemini emulation labels verbalized values ``verbalized_uncalibrated``; the
#: fixture backend labels its caller-supplied values ``fixture_supplied``. A backend
#: that declares nothing is recorded as ``unreported`` rather than described.
PROBABILITIES_DEFAULT = 'unreported'


def _invalid():
    raise JudgmentUnavailable('MODEL_INVALID_RESPONSE')


def _check(condition):
    if not condition:
        _invalid()


def _probability(value):
    _check((type(value) is int or type(value) is float) and math.isfinite(value) and 0 <= value <= 1)


def _rendered(bundle):
    """The rendered request's questions, or a caller error (as in ``bundle._values``)."""
    if (type(bundle) is not dict or bundle.get('status') != 'rendered'
            or type(bundle.get('request')) is not dict or type(bundle['request'].get('questions')) is not dict):
        raise ValueError('a rendered bundle is required')
    return bundle['request']['questions']


def validate_answers(questions, answers):
    """The single answers-shape check the port, the record and S1 all agree on.

    ``questions`` is the rendered request's question mapping, or the stored record's
    ``questions`` (which carries the extra ``form``/``instructions`` keys this check
    ignores). Every condition mirrors ``bundle._values``, so an answers mapping that
    passes here passes composition and receipt, and anything else raises
    ``MODEL_INVALID_RESPONSE``. A missing question, an unknown question, an option the
    form never presented, or a value outside [0, 1] all fail here.
    """
    if type(questions) is not dict or not questions or type(answers) is not dict:
        _invalid()
    if set(answers) != set(questions):
        _invalid()
    for name, question in questions.items():
        _check(type(name) is str and 0 < len(name) <= MAX_NAME)
        _check(type(question) is dict)
        qtype, criteria = question.get('type'), question.get('criteria')
        _check(qtype in ('choice', 'noul') and type(criteria) is dict)
        options = criteria.get('options')
        _check(type(options) is dict and options and all(type(token) is str for token in options))
        answer = answers[name]
        _check(type(answer) is dict)
        if qtype == 'choice':
            presentation = criteria.get('presentation')
            _check(type(presentation) is list and len(presentation) == len(options)
                   and all(type(token) is str for token in presentation))
            _check(set(answer) == {'choice', 'probabilities'} and type(answer['choice']) is str)
            _check(answer['choice'] in presentation and answer['choice'] in options)
            probabilities = answer['probabilities']
            _check(type(probabilities) is dict and set(probabilities) <= set(options))
            for value in probabilities.values():
                _probability(value)
        else:
            _check(set(options) == {'yes', 'no'} and options['yes'] != options['no'])
            _check(set(answer) == {'noul'})
            _probability(answer['noul'])
    return json_copy(answers)


def validate_response(bundle, response):
    """Validate one System One response against the rendered bundle.

    Returns ``(answers, model_version)``. The 64 KiB bound is measured on the canonical
    bytes of the whole response before any field is trusted, so an oversized response
    fails as one unit and nothing downstream sees a partial answer; probabilities are
    returned exactly as the backend sent them, raw.
    """
    questions = _rendered(bundle)
    _check(type(response) is dict and set(response) == {'answers', 'model_version'})
    try:
        size = len(canonical_dumps(response).encode('utf-8'))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _invalid()
    _check(size <= MAX_RESPONSE_BYTES)
    model_version = response['model_version']
    _check(type(model_version) is str and 0 < len(model_version) <= MAX_NAME)
    return validate_answers(questions, response['answers']), model_version


def record_questions(bundle):
    """The rendered questions as the artifact stores them.

    Names, types, criteria and form kinds; the shared state is not stored because it is
    reproducible from the task. The instructions are kept because they are part of the
    rendered question and are versioned by ``BUNDLE_VERSION`` together with the
    criteria.
    """
    questions = _rendered(bundle)
    return json_copy({name: {'type': question['type'], 'form': 'f' + name.rsplit('_f', 1)[-1],
                             'instructions': question['instructions'], 'criteria': question['criteria']}
                      for name, question in questions.items()})


class FixtureSystemOne:
    """Labelled test backend: answers from a dict keyed by question name.

    ``decide`` returns the fixture's answers for exactly the questions the request
    carries, never a question the request did not ask, so a missing entry stays a
    missing answer and the service rejects the response exactly as it would a backend's
    that omitted one. ``requests`` records every request received, so a replay can be
    shown not to call the backend. No transport, credential or network call exists in
    this object.
    """

    execution_mode = 'synthetic_fixture'
    probabilities = 'fixture_supplied'

    def __init__(self, name, model, answers, model_version='fixture-1'):
        for field, value in (('name', name), ('model', model), ('model_version', model_version)):
            if type(value) is not str or not value.strip() or len(value) > MAX_NAME:
                raise ValueError(f'{field} must be a nonblank string of at most {MAX_NAME} characters')
        if type(answers) is not dict:
            raise ValueError('answers must be a mapping keyed by question name')
        self.name, self.model, self.model_version = name, model, model_version
        self.answers = json_copy(answers)
        self.requests = []

    def decide(self, request):
        self.requests.append(json_copy(request))
        return {'answers': json_copy({name: self.answers[name] for name in request['questions']
                                      if name in self.answers}),
                'model_version': self.model_version}


def _repository_call(repository, name, actor, case, *args):
    """Call one additive repository method through whichever port the adapter exposes.

    ``PersistentRepository`` publishes repository methods through an explicit allow-list
    (``src/review/storage.py``) that predates the probe-bundle methods, so there the same
    single call runs through its ``execute`` port; ``ReviewService`` exposes the methods
    directly. Either way the call is one repository operation: the backend invocation
    stays outside ``execute``, and a retried transaction re-renders nothing because all
    rendering happens before the write call.
    """
    method = getattr(repository, name, None)
    if method is not None:
        return method(actor, case, *args)
    return repository.execute(actor, case, lambda service, fresh: getattr(service, name)(fresh, case, *args))


class SystemOneService:
    """Proposal-only bundle generation: one render, one backend call, one artifact."""

    def __init__(self, backend=None):
        self.backend = backend
        self.slots = BoundedSemaphore(1)

    def generate(self, repository, actor, case, task_ref, key, clock):
        """One render, one backend call, one artifact.

        The composition's lineage row (Q5) reuses the label of a qualifying earlier
        bundle on a task for the same assumption at or before this task's cutoff; that
        prior is resolved from the repository before the one model call, so the backend
        is never asked to decide evidence an earlier bundle on the same assumption
        already decided. When the row fires, the artifact records the prior's reference
        as ``composed['lineage_ref']``, so a later read traverses the inherited artifact
        and its sources too and a revoked source denies the derived read as it denies
        the prior's.
        """
        prior, task = _repository_call(repository, 'bundle_input', actor, case, task_ref, key)
        if prior is not None:
            return prior
        if self.backend is None:
            raise JudgmentUnavailable('MODEL_DISABLED')
        if not self.slots.acquire(blocking=False):
            raise JudgmentUnavailable('MODEL_BUSY')
        try:
            rendered = render_bundle(task, self.backend.model)
            if rendered['status'] != 'rendered':
                # The renderer refused: there is no request to answer, so no backend is
                # called and no artifact is written. The refusal is the result.
                return rendered
            lineage = _repository_call(repository, 'bundle_lineage_prior', actor, case, task_ref)
            try:
                response = self.backend.decide(rendered['request'])
            except Exception:
                # A backend failure is one safe code, never its text and never a code of
                # its own choosing: a backend-raised ``JudgmentUnavailable`` is a
                # backend failure like any other exception.
                raise JudgmentUnavailable() from None
            answers, model_version = validate_response(rendered, response)
            composed = compose(rendered, answers, prior_label=lineage['label'] if lineage else None)
            if lineage is not None and composed['fired_rule'].split(':')[0] == 'lineage_reuse':
                # The composition reused that artifact's label, so the artifact records
                # the inherited dependency. The reference is a record reference, and the
                # read check walks references: a source the prior cited can no longer be
                # dropped from the derived artifact's access.
                composed['lineage_ref'] = lineage['ref']
            receipt_record = receipt(rendered, answers)
            metadata = {
                'provider': self.backend.name, 'model': self.backend.model,
                'model_version': model_version, 'execution_mode': self.backend.execution_mode,
                'bundle_version': BUNDLE_VERSION,
                'probabilities': getattr(self.backend, 'probabilities', PROBABILITIES_DEFAULT),
                'request_digest': rendered['request_digest'],
                'output_digest': compute_content_digest(composed),
            }
            return _repository_call(repository, 'save_bundle', actor, case, task_ref, key,
                                    record_questions(rendered), answers, composed, receipt_record,
                                    metadata, clock())
        finally:
            self.slots.release()
