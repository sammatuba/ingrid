"""An isolated fictional-case run. Does not activate the workspace or hosted storage."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

from src.contracts.jsonutil import canonical_bytes, compute_content_digest, parse_json, with_content_digest
from src.demo import CASE, seed
from src.judgment import JudgmentService, JudgmentUnavailable, validate_answer
from src.review import InMemoryRepository, reference, validate_record
from . import GeminiProvider
from .transport import DeveloperAPITransport

CUTOFF = '2026-10-05T02:00:00Z'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def prepare_case(clock=utc_now):
    repository = InMemoryRepository()
    seeded = seed(repository)
    actor = seeded['actor']
    at = clock()
    snapshot = repository.build_snapshot(actor, CASE, at, at)
    task = repository.compile_task(actor, CASE, reference(snapshot), 'capacity-assumption', CUTOFF, at)
    return repository, actor, task, seeded


def write_private_json(path, value):
    """Atomic local output; all runner artifacts belong under the ignored run directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.pending')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical_bytes(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_private_json(path, cap=512 * 1024):
    with Path(path).open('rb') as stream:
        raw = stream.read(cap + 1)
    if len(raw) > cap:
        raise JudgmentUnavailable('MODEL_RECEIPT_INVALID')
    value, error = parse_json(raw.decode('utf-8'))
    if error or type(value) is not dict:
        raise JudgmentUnavailable('MODEL_RECEIPT_INVALID')
    return value


def prepare_bundle(clock=utc_now):
    repository, actor, task, seeded = prepare_case(clock)
    return {'mode': 'offline_preparation', 'synthetic_case': True, 'inference_performed': False,
        'task': task, 'source': seeded['source'], 'passage': seeded['passage'],
        'mapping': seeded['mapping'], 'heads': repository.heads(actor, CASE),
        'semantic_checks': [
            'The source reports testing at 80 MW; commercial availability remains unconfirmed.',
            'Testing output is not the accepted 100 MW available-capacity assumption.',
            'A different numerical availability value requires human review and supporting evidence.',
            'A cited answer must acknowledge uncertainty and keep consequences uncomputed.',
        ]}


def run_case(config, output_root, *, transport_factory=DeveloperAPITransport,
        execution_mode='live_inference', clock=utc_now):
    """Only an explicitly configured operator command invokes this function.

    This runner prepares the fictional `CASE` only, so a configuration naming any other case —
    including a real case the transport's allowlist permits for a caller that compiles it — is
    refused here, before the run directory exists, rather than transmitting this case's content
    under a label this runner cannot vouch for. The directory and ledger are retained for the
    approved run. Successful restart reads the immutable local bundle; incomplete/failed
    attempts never automatically rerun.
    """
    root = Path(output_root) / config.run_id
    if config.max_attempts != 1 or config.permitted_case != CASE:
        raise JudgmentUnavailable('MODEL_CONFIG_INVALID')
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / 'result.json'
    digest = hashlib.sha256(canonical_bytes(config.as_dict())).hexdigest()
    if result_path.exists():
        try:
            saved = read_private_json(result_path)
            if saved['content_digest'] != compute_content_digest(saved):
                raise ValueError()
            if saved['config_digest'] != digest or saved['execution_mode'] != execution_mode:
                raise JudgmentUnavailable('MODEL_ALLOWANCE_CONFLICT')
            artifact, task = saved['judgment'], saved['task']
            for record in (artifact, task, saved['source'], saved['passage'], saved['mapping']):
                validate_record(record)
            if (artifact['record_kind'] != 'JudgmentArtifact' or artifact['payload']['task_ref'] != reference(task)
                    or artifact['payload']['metadata']['execution_mode'] != execution_mode
                    or artifact['payload']['metadata']['model'] != config.model
                    or artifact['case_id'] != config.permitted_case or task['case_id'] != config.permitted_case):
                raise ValueError()
            validate_answer(artifact['payload']['answer'], task['payload']['context'])
            passage = saved['passage']['payload']
            source = saved['source']['payload']
            context = task['payload']['context']
            if (passage['source_ref'] != reference(saved['source'])
                    or source['original_text'][passage['start']:passage['end']] != passage['quote']
                    or passage['source_byte_digest'] != source['source_byte_digest']
                    or len(context) != 1 or context[0]['quote'] != passage['quote']
                    or saved['mapping']['payload']['source_refs'] != [reference(saved['source'])]):
                raise ValueError()
            return saved
        except JudgmentUnavailable:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError):
            raise JudgmentUnavailable('MODEL_RECEIPT_INVALID') from None
    repository, actor, task, seeded = prepare_case(clock)
    heads = repository.heads(actor, CASE)
    transport = transport_factory(config, root / 'attempts.sqlite3')
    provider = GeminiProvider(config.model, transport, execution_mode=execution_mode,
        max_output_tokens=config.max_output_tokens, api=config.api, case=CASE)
    service = JudgmentService(provider)
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
    result = with_content_digest({'status': 'proposed_judgment_saved', 'synthetic_case': True,
        'execution_mode': execution_mode, 'config_digest': digest,
        'task': task, 'source': seeded['source'], 'passage': seeded['passage'],
        'mapping': seeded['mapping'], 'accepted_heads': heads,
        'judgment': artifact, 'transport': transport.last_receipt,
        'semantic_review': {'status': 'pending_human_review', 'consequences': 'uncomputed'}})
    write_private_json(result_path, result)
    return result
