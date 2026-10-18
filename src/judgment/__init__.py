"""Bounded, proposal-only model work; no network or cloud SDK dependency."""
from threading import BoundedSemaphore

from src.contracts.jsonutil import canonical_dumps, compute_content_digest, parse_json
from src.review.records import json_copy, reference
from src.review.errors import require

LABELS = ('supports', 'challenges', 'mixed', 'unrelated', 'insufficient')
MAX_RESPONSE_BYTES = 32768
PROMPT_VERSION = 'cited-relation.v1'


class JudgmentUnavailable(Exception):
    """Safe failure code; provider details and source content are never exposed."""
    def __init__(self, code='MODEL_UNAVAILABLE'):
        self.code = code
        super().__init__(code)


def validate_answer(answer, context=None):
    require(type(answer) is dict and set(answer) == {'label', 'explanation', 'citations', 'alternatives', 'unknowns'})
    require(type(answer['label']) is str and answer['label'] in LABELS)
    require(type(answer['explanation']) is str and 0 < len(answer['explanation'].strip()) <= 4000)
    for name in ('alternatives', 'unknowns'):
        require(type(answer[name]) is list and len(answer[name]) <= 8)
        require(all(type(x) is str and 0 < len(x.strip()) <= 1000 for x in answer[name]))
    citations = answer['citations']
    require(type(citations) is list and 1 <= len(citations) <= 32)
    seen = set()
    for c in citations:
        require(type(c) is dict and set(c) == {'passage_index', 'quote'})
        require(type(c['passage_index']) is int and 0 <= c['passage_index'] < 32)
        require(c['passage_index'] not in seen)
        seen.add(c['passage_index'])
        require(type(c['quote']) is str and 0 < len(c['quote']) <= 12000)
        if context is not None:
            require(c['passage_index'] < len(context))
            require(c['quote'] == context[c['passage_index']]['quote'], 'INVALID_SOURCE')
    return json_copy(answer)


def render_task(task):
    p = task['payload']
    # Deliberately exclude access_scope and unrelated case state.
    value = {k: p[k] for k in ('policy', 'original_definitions', 'task_digest',
        'assumption_definition', 'mapping_definition', 'model_representation',
        'information_cutoff', 'audit_cutoff', 'context', 'lineage_groups')}
    text = canonical_dumps(value)
    if len(text.encode('utf-8')) > 128 * 1024:
        raise JudgmentUnavailable('MODEL_INPUT_LIMIT')
    return text


class JudgmentService:
    def __init__(self, provider=None):
        self.provider = provider
        self.slots = BoundedSemaphore(1)

    def generate(self, repository, actor, case, task_ref, key, clock):
        prior, task = repository.judgment_input(actor, case, task_ref, key)
        if prior is not None:
            return prior
        if self.provider is None:
            raise JudgmentUnavailable('MODEL_DISABLED')
        if not self.slots.acquire(blocking=False):
            raise JudgmentUnavailable('MODEL_BUSY')
        try:
            prompt = render_task(task)
            # Provider invocation is outside repository.execute and all transaction retries.
            try:
                result = self.provider.generate(prompt)
            except JudgmentUnavailable:
                raise
            except Exception:
                raise JudgmentUnavailable() from None
            try:
                require(type(result) is dict and set(result) == {'text', 'model_version'})
                require(type(result['text']) is str and len(result['text'].encode('utf-8')) <= MAX_RESPONSE_BYTES)
                require(type(result['model_version']) is str and 0 < len(result['model_version']) <= 200)
                answer, error = parse_json(result['text'])
                require(error is None)
                answer = validate_answer(answer, task['payload']['context'])
            except (ValueError, UnicodeError, RecursionError):
                raise JudgmentUnavailable('MODEL_INVALID_RESPONSE') from None
            metadata = {
                'provider': self.provider.name, 'model': self.provider.model,
                'model_version': result['model_version'], 'execution_mode': self.provider.execution_mode,
                'prompt_version': PROMPT_VERSION,
                'request_digest': compute_content_digest({'prompt_version': PROMPT_VERSION, 'input': prompt}),
                'output_digest': compute_content_digest(answer),
            }
            return repository.save_judgment(actor, case, task_ref, key, answer, metadata, clock())
        finally:
            self.slots.release()
