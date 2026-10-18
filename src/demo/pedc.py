"""The PEDC Unit 2 event case, built into a judge's own case at session creation.

The first real case (`tests/fixtures/pedc-u2-2026-09-21/build.py`, task EVAL-5) is the
PEDC Unit 2 trip of 2026-09-21. The event review (GRID-3) lets a judge decide on that
case, so a hosted sandbox session seeds a copy of it: this module builds the same
records the EVAL-5 fixture builds — the four `pedc_u2_21sep` advisories and the
`08PEDC_U02` register run through the DATA-1 readers, the reviewed free-text mapping,
the dispatch corroboration, and the seed acceptance at 83.7 MW — for a given tenant,
case and actor, from the source rows committed beside this file in `pedc-case.json`.

Two rules fix who the records say acted and when (`docs/work/grid-desk/intent.md`,
GRID-3):

* the sources keep the clocks they really carry — `known_at`, posting instants — and
  their envelopes keep the positions the EVAL-5 fixture recorded;
* the desk's own acts (the reviewed mapping and the seed acceptance) carry the session
  actor and the session's real time, because that is when this desk acted.

Every record is real: `synthetic: false` with the signed permission record
``perm:wesm-company-copy:2026-10-13`` (`docs/work/permissions/2026-10-13-wesm-company-copy.md`).
Runtime code never imports from ``tests/``: the rows it needs were copied into
`pedc-case.json`, and `tests/test_grid_event.py` proves the copy is the fixture's own
rows and that the built payloads are the EVAL-5 case's.

No model, transport, credential or network call is reachable from this module: it reads
one local JSON file and calls the review core.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from src.adapters.wesm import advisories as wesm_advisories
from src.adapters.wesm import registry as wesm_registry
from src.contracts.jsonutil import canonical_dumps
from src.review import make_record, reference
from src.review.repository import DEFAULT_PERMISSIONS

#: The event id `/event/<id>` and the baked view model use (`scripts/grid/events.json`,
#: GRID-1); the case copy's own pointer to the case it copies.
EVENT_ID = 'pedc-u2-2026-09-21'
#: The prefix of the per-session case id; `src.api.hosted.event_case` builds the rest.
CASE_PREFIX = 'pedc-'
#: The signed permission every record of this case cites.
PERMISSION_REF = wesm_registry.PERMISSION_REF
#: The source rows and the case definition, copied from the EVAL-5 fixture's inputs.
CASE_FILE = Path(__file__).with_name('pedc-case.json')
#: The envelope the register records carry, as the fixture recorded it: the register run
#: starts at 2026-09-21 00:00 +08:00 in the replay's positions.
REGISTER_RECORDED_AT = '2026-09-21T00:00:00+08:00'
#: The one register run the case uses, and the day it must cover.
REGISTER_DAY = '2026-09-21'


class PedcCaseError(ValueError):
    """The committed case data cannot produce the case; the session is refused, never patched."""


@lru_cache(maxsize=1)
def case_data():
    """The committed case file, parsed once; a bad copy is a refusal, not a demo with holes."""
    try:
        document = json.loads(CASE_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise PedcCaseError('pedc-case.json is unreadable: %s' % (exc,)) from None
    for key in ('case', 'rows', 'dispatch'):
        if type(document) is not dict or type(document.get(key)) is not dict:
            raise PedcCaseError('pedc-case.json carries no %r block' % key)
    if not document['rows'].get('advisories') or not document['rows'].get('register'):
        raise PedcCaseError('pedc-case.json carries no source rows')
    return document


def _advisory_records(tenant_id, case_id, permissions):
    """The four advisories of the trip day: one SourceVersion and one Passage each."""
    rows = case_data()['rows']['advisories']
    batch = wesm_advisories.parse_advisories(rows)
    if len(batch.advisories) != 4 or batch.rejected:
        raise PedcCaseError('the committed advisory rows must be four parsable messages, '
                            '%d parsed and %d refused' % (len(batch.advisories), len(batch.rejected)))
    records = []
    for item in batch.advisories:
        one = wesm_advisories.AdvisoryBatch(advisories=(item,), rejected=())
        # The recorder is the feed's own position: the envelope keeps the clock the source
        # really carries, exactly as the EVAL-5 fixture records it.
        records.extend(wesm_advisories.records(one, tenant_id, case_id, item.source['known_at'],
                                               permissions=permissions))
    return batch, records


def register_run():
    """The one change-only run of ``08PEDC_U02`` that covers the case day."""
    document = case_data()
    runs, rejected = wesm_registry.build_runs(document['rows']['register'])
    if rejected:
        raise PedcCaseError('the committed register rows must parse whole')
    day = date.fromisoformat(document['case']['register_day'])
    covering = [run for run in runs if run.first_day <= day <= run.last_day]
    if len(covering) != 1:
        raise PedcCaseError('exactly one register run must cover %s' % document['case']['register_day'])
    return covering[0]


def _dispatch_records(tenant_id, case_id, permissions):
    """The dispatch corroboration: one SourceVersion and one Passage, cited to the profile.

    Its first availability is unknown (`known_at` null, the copy carries no `RUN_TIME`), so
    every compiled context omits it with `UNKNOWN_AVAILABILITY`; the body, the publisher and
    the unknown reason are the recorded ones from the case file.
    """
    dispatch = case_data()['dispatch']
    text = canonical_dumps(dispatch['body'])
    data = text.encode('utf-8')
    source = make_record('SourceVersion', tenant_id, case_id, dispatch['source_id'], '1',
                         dispatch['recorded_at'], {
                             'source_id': dispatch['source_id'], 'source_version': '1',
                             'lineage_id': dispatch['source_id'], 'publisher': dispatch['publisher'],
                             'access_policy_ref': PERMISSION_REF, 'original_text': text,
                             'source_byte_digest': hashlib.sha256(data).hexdigest(),
                             'published_at': dispatch['published_at'], 'published_at_approximate': True,
                             'derived_from': dispatch['derived_from'], 'known_at': None,
                             'availability_basis': None, 'unknown_reason': dispatch['unknown_reason'],
                             'copied_from': None, 'synthetic': False, 'permission_ref': PERMISSION_REF,
                         }, permissions=permissions)
    passage = make_record('Passage', tenant_id, case_id, 'passage:' + dispatch['source_id'], '1',
                          dispatch['recorded_at'], {
                              'source_ref': reference(source), 'source_id': dispatch['source_id'],
                              'source_version': '1', 'source_byte_digest': hashlib.sha256(data).hexdigest(),
                              'start': 0, 'end': len(text), 'quote': text,
                              'quote_digest': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                              'synthetic': False, 'permission_ref': PERMISSION_REF,
                          }, permissions=permissions)
    return source, passage


def build_records(tenant_id, case_id, actor_id, at, permissions=None):
    """The case's records, in registration order, for one session's own copy.

    ``at`` is the session's real instant: the reviewed mapping and the seed acceptance
    carry it, and the caller passes the same instant back as the session's
    ``event_seeded_at`` so the judge's snapshot can name the belief state it reads.
    Returns the records plus the parts a caller or a test reads back (the run, the
    advisory batch, the seed payload and the rationale).
    """
    document = case_data()
    definition = document['case']
    permissions = DEFAULT_PERMISSIONS if permissions is None else permissions
    if definition['permission_ref'] != PERMISSION_REF:
        raise PedcCaseError('pedc-case.json states the permission %r, not %r'
                            % (definition['permission_ref'], PERMISSION_REF))
    # A registry without the signed record refuses every record below (PERMISSION_UNKNOWN):
    # real records need a signed permission, and this module never falls back to synthetic ones.

    case_record = make_record('Case', tenant_id, case_id, case_id, '1', at, {
        'permitted_actors': [actor_id],
        'entities': [dict(definition['entity'])],
        'representations': [dict(definition['representation'])],
        'copy': {
            'of': EVENT_ID,
            'assembled_by': 'the EVAL-5 case assembly, %s' % document['case']['copied_from']['case_records'],
            'rows_from': 'src/demo/pedc-case.json',
            'copied_by': actor_id, 'copied_at': at,
            'note': ('Per-session copy of the first real case for the judge’s own decision. The sources '
                     'keep the clocks they really carry; the reviewed mapping and the seed acceptance are '
                     'this session’s acts and carry its actor and its real time.'),
        },
        'synthetic': False, 'permission_ref': PERMISSION_REF,
    }, permissions=permissions)

    batch, advisory_records = _advisory_records(tenant_id, case_id, permissions)
    run = register_run()
    register_records = wesm_registry.records([run], tenant_id, case_id, REGISTER_RECORDED_AT,
                                             representation_id=definition['representation']['representation_id'],
                                             input_field=definition['input_field'], permissions=permissions)
    run_source = next(record for record in register_records if record['record_kind'] == 'SourceVersion')
    candidate = next(record for record in register_records if record['record_kind'] == 'MappingRevision')
    # The free-text link "PEDC U2" -> 08PEDC_U02 is the desk's review act: this session's
    # actor, this session's real time, evidenced by the register run the reader selected.
    reviewed_payload = wesm_registry.mapping_payload(
        run, run_source, representation_id=definition['representation']['representation_id'],
        input_field=definition['input_field'])
    reviewed_payload.update(status='reviewed', reviewer=actor_id, reviewed_at=at)
    reviewed = make_record('MappingRevision', tenant_id, case_id, run.mapping_id, '2', at,
                           reviewed_payload, permissions=permissions)

    dispatch_source, dispatch_passage = _dispatch_records(tenant_id, case_id, permissions)

    field = definition['representation']['input_fields'][definition['input_field']]
    seed = definition['assumption']
    assumption = {
        'case_id': case_id, 'entity': dict(definition['entity']),
        'proposition': seed['proposition'],
        # The value is read from the register run's capacity, never typed by hand.
        'value': {'value': run.capacity_mw, 'quantity_kind': field['quantity_kind'], 'unit': field['unit']},
        'valid_period': dict(seed['valid_period']),
        'representation_id': definition['representation']['representation_id'],
        'input_field': definition['input_field'], 'mapping_ref': reference(reviewed),
    }
    rationale = (
        'Initial acceptance recorded by the judge session %s at %s for its own copy of the %s case; '
        'the value is read from the register run’s capacity (%s MW, participant %s), never typed.'
        % (actor_id, at, EVENT_ID, run.capacity_mw, run.participant))
    records = [case_record, *advisory_records, *register_records, reviewed,
               dispatch_source, dispatch_passage]
    return {'case': case_record, 'records': records, 'run': run, 'batch': batch,
            'candidate': candidate, 'reviewed': reviewed, 'dispatch': dispatch_source,
            'dispatch_passage': dispatch_passage, 'assumption': assumption,
            'assumption_id': seed['record_id'], 'assumption_revision': seed['revision_id'],
            'rationale': rationale}


def batch(built, at):
    """The prepared operations that write ``built``, in the order the per-record seed used.

    One ``(method, args, kwargs)`` triple per record — the case first, then the advisories,
    the register run, the reviewed mapping and the dispatch corroboration — followed by the
    seed acceptance. They name the same three provisioning ports with the same arguments, so
    a batch is the same calls made once, never a second way to write.
    """
    operations = [('register_case', (built['case'],), {})]
    for record in built['records'][1:]:
        kwargs = ({'source_bytes': record['payload']['original_text'].encode('utf-8')}
                  if record['record_kind'] == 'SourceVersion' else {})
        operations.append(('register', (record,), kwargs))
    operations.append(('seed_assumption',
                       (built['assumption_id'], built['assumption_revision'], at,
                        built['assumption'], built['rationale']), {}))
    return operations


def seed(repository, actor, case, at, permissions=None):
    """Register the case's records under ``actor`` and seed its initial acceptance.

    The whole case is one prepared batch (`repository.provision`): the case is loaded once,
    every record is applied to the decoded service in memory, and the complete state is
    committed once, so no partial case is ever visible. Every write goes through the review
    core's own ports, so the h0.v2 rules, the case provenance pair and the mapping guards
    apply exactly as they do to any other case.
    """
    built = build_records(actor.tenant_id, case, actor.actor_id, at, permissions=permissions)
    built['assumption_record'] = repository.provision(actor, case, batch(built, at))[-1]
    return built
