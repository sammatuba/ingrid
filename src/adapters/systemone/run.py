"""One isolated fictional-case probe run: offline preparation, or one authorized call.

Mirrors `src/adapters/gemini/run.py`. The private-file IO and the synthetic case are that
module's helpers, the operator configuration is the same `LiveConfig` (exact keys, one fixed
service, one attempt, no credential in the file), and the one-attempt `GeminiTransport`
supplies the credential, the allowance ledger and the deadline. This module adds the System
One step: render the S1 bundle for the compiled synthetic task, ask the configured Gemini
emulation once through `SystemOneService`, and save the proposed `ProbeBundleArtifact` under
an ignored run directory. No accepted value, head or revision changes.

Offline preparation performs no inference and names no model: it renders the request with
the self-describing label `PREPARED_MODEL` and says so, so a prepared digest is never read
as a claim about a call that happened. The authorized run re-renders with the configured
model, so its request digest is its own.

Placeholders are refused. `src/adapters/gemini/README.md` publishes an example configuration
whose values (`replace-with-approved-project`, `gemini-approved-model`,
`APPROVED_GEMINI_API_KEY`, `replace-with-recorded-service-case-and-budget-authorization`,
`approved-smoke-001`) all satisfy `LiveConfig`'s grammar, so a copied example would otherwise
pass validation and look like a configured run until the credential step. A text field whose
value carries one of those documented placeholder words as a separate token is refused as
`MODEL_CONFIG_INVALID` before a transport exists. The rule errs toward refusal: a real value
that happens to carry one of the words is refused too, and the operator rewords it.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from src.adapters.gemini.run import prepare_case, read_private_json, utc_now, write_private_json
from src.adapters.gemini.transport import GeminiTransport, LiveConfig
from src.contracts.jsonutil import canonical_bytes, compute_content_digest, with_content_digest
from src.demo import CASE
from src.judgment import JudgmentUnavailable
from src.judgment.bundle import BUNDLE_VERSION, DEFAULT_THRESHOLDS, render_bundle
from src.judgment.systemone import SystemOneService
from src.review import reference, validate_record

from . import GeminiSystemOneEmulation

#: The label an offline preparation renders under. It is not a provider model and the
#: preparation says so; the authorized run re-renders with the configured model.
PREPARED_MODEL = 'offline-preparation'

#: The placeholder vocabulary of the published example configuration, as separate tokens.
PLACEHOLDER_WORDS = frozenset({'approved', 'change', 'changeme', 'example', 'fixme', 'insert',
                               'placeholder', 'replace', 'sample', 'tbd', 'todo', 'xxx', 'your'})

#: What a reviewer checks in prepared output before authorizing a run; mirrors the
#: `semantic_checks` of the m3 runner. Every statement is about the method, not the case.
SEMANTIC_CHECKS = (
    'The bundle is a proposal; it changes no accepted value, head or revision.',
    'The label and the eight atomic answers are composed from perturbation-stable top options, never from means.',
    'A model probability is a verbalized judgement, uncalibrated, and never an event probability.',
    'An unstable or insufficient bundle is reported as insufficient with an escalation, never as a decision.',
    'The composition thresholds are initial values, untuned until the offline ablation.',
)


def _tokens(value):
    return [token for token in re.split(r'[^0-9A-Za-z]+', value) if token]


def placeholder_fields(config):
    """The text fields of one operator configuration that still carry a placeholder value."""
    return tuple(name for name, value in sorted(config.as_dict().items())
                 if type(value) is str and any(token.lower() in PLACEHOLDER_WORDS for token in _tokens(value)))


def load_config(path):
    """One trusted operator configuration: exact keys, valid values, no placeholder.

    Reading, parsing and the value grammar are `LiveConfig`'s; the placeholder refusal is
    this module's, applied to every text field before a transport can be constructed.
    """
    config = LiveConfig.from_dict(read_private_json(path, cap=8192))
    if placeholder_fields(config):
        raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
    return config


def prepare_probe(clock=utc_now):
    """The offline preparation: the rendered request and its digest, no backend or credential."""
    repository, actor, task, seeded = prepare_case(clock)
    rendered = render_bundle(task, PREPARED_MODEL)
    prepared = {'mode': 'offline_preparation', 'synthetic_case': True, 'inference_performed': False,
        'task': task, 'source': seeded['source'], 'passage': seeded['passage'], 'mapping': seeded['mapping'],
        'heads': repository.heads(actor, CASE), 'bundle_version': BUNDLE_VERSION,
        'thresholds': dict(DEFAULT_THRESHOLDS), 'model': PREPARED_MODEL,
        'semantic_checks': list(SEMANTIC_CHECKS)}
    if rendered['status'] == 'rendered':
        prepared.update({'request': rendered['request'], 'request_digest': rendered['request_digest'],
                         'question_count': len(rendered['request']['questions'])})
    else:
        # A refusal is a result: no request exists, so nothing would be called.
        prepared['refusal'] = rendered
    return prepared


def _saved_result(saved, digest, execution_mode):
    """One already-saved run, validated: a successful restart re-reads, never re-runs."""
    if saved['config_digest'] != digest or saved['execution_mode'] != execution_mode:
        raise JudgmentUnavailable('MODEL_ALLOWANCE_CONFLICT')
    if saved['status'] == 'render_refused':
        refusal = saved['refusal']
        if (type(refusal) is not dict or refusal.get('status') != 'insufficient'
                or not refusal.get('reason') or saved['transport'] is not None):
            raise ValueError()
        return saved
    if saved['status'] != 'proposed_bundle_saved':
        raise ValueError()
    artifact, task = saved['bundle'], saved['task']
    for record in (artifact, task, saved['source'], saved['passage'], saved['mapping']):
        validate_record(record)
    if (artifact['record_kind'] != 'ProbeBundleArtifact' or artifact['payload']['task_ref'] != reference(task)
            or artifact['payload']['metadata']['execution_mode'] != execution_mode
            or artifact['case_id'] != saved['source']['case_id'] or task['case_id'] != saved['source']['case_id']):
        raise ValueError()
    return saved


def run_case(config, output_root, *, transport_factory=GeminiTransport,
        execution_mode='live_inference', clock=utc_now):
    """Only an explicitly configured operator command invokes this function.

    The directory and ledger are retained for the approved run. A successful restart reads
    the immutable local result; an incomplete or failed attempt never reruns automatically.
    """
    root = Path(output_root) / config.run_id
    if config.max_attempts != 1:
        raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / 'result.json'
    digest = hashlib.sha256(canonical_bytes(config.as_dict())).hexdigest()
    if result_path.exists():
        try:
            saved = read_private_json(result_path)
            if saved['content_digest'] != compute_content_digest(saved):
                raise ValueError()
            return _saved_result(saved, digest, execution_mode)
        except JudgmentUnavailable:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise JudgmentUnavailable('MODEL_RECEIPT_INVALID') from None
    repository, actor, task, seeded = prepare_case(clock)
    heads = repository.heads(actor, CASE)
    transport = transport_factory(config, root / 'attempts.sqlite3')
    backend = GeminiSystemOneEmulation(config.model, transport, execution_mode=execution_mode,
        max_output_tokens=config.max_output_tokens, api=config.api)
    service = SystemOneService(backend)
    try:
        artifact = service.generate(repository, actor, CASE, reference(task), config.run_id, clock)
        if repository.heads(actor, CASE) != heads or repository.history(actor, CASE):
            raise JudgmentUnavailable('MODEL_STATE_CHANGED')
    except JudgmentUnavailable as exc:
        # Preserve the first actual attempt receipt when a later spent-allowance check fails.
        if transport.last_receipt is not None or not (root / 'failure.json').exists():
            write_private_json(root / 'failure.json', {'status': exc.code,
                'synthetic_case': True, 'execution_mode': execution_mode,
                'config_digest': digest, 'transport': transport.last_receipt})
        raise
    if type(artifact) is not dict or artifact.get('record_kind') != 'ProbeBundleArtifact':
        # A render refusal is a result, not an error: no request was answered, the backend
        # was never called and nothing was written. It is saved so a restart reads it back
        # rather than deriving the same refusal again.
        result = with_content_digest({'status': 'render_refused', 'synthetic_case': True,
            'execution_mode': execution_mode, 'config_digest': digest, 'refusal': artifact,
            'transport': transport.last_receipt})
        write_private_json(result_path, result)
        return result
    result = with_content_digest({'status': 'proposed_bundle_saved', 'synthetic_case': True,
        'execution_mode': execution_mode, 'config_digest': digest,
        'task': task, 'source': seeded['source'], 'passage': seeded['passage'], 'mapping': seeded['mapping'],
        'accepted_heads': heads, 'bundle': artifact, 'transport': transport.last_receipt,
        'semantic_review': {'status': 'pending_human_review', 'consequences': 'uncomputed'}})
    write_private_json(result_path, result)
    return result
