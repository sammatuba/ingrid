"""Trusted fictional seed for local walkthroughs; never a public bootstrap endpoint."""
import hashlib
from src.review import ActorContext, make_record, reference

EMAIL = 'analyst@example.test'
PASSWORD = 'synthetic-local-only'
TENANT, CASE, UID = 'synthetic-tenant', 'synthetic-case', 'synthetic-analyst'
AT = '2026-10-01T09:00:00+08:00'


def records(actor=None, *, ambiguous=False):
    """The fixture case's records and its seed acceptance, prepared in memory.

    Preparation performs no call: it returns the ordered ``(method, args, kwargs)``
    operations `seed` applies, plus the case id and the records the callers and tests read
    back. The same operation list can be applied as one prepared batch (one store load and
    one commit) or one port call at a time, which is what
    ``tests/test_demo_session_batch.py`` compares for both cases.
    """
    actor = actor or ActorContext(UID, TENANT, frozenset({CASE}), frozenset({'synthetic-public'}), True)
    tenant, case = actor.tenant_id, next(iter(actor.accessible_cases))
    def record(kind, ident, payload, revision='1'):
        return make_record(kind, tenant, case, ident, revision, AT, payload)
    entity = {'entity_id':'fictional-unit-a', 'entity_type':'GeneratingUnit'}
    value = {'value':'100.00','quantity_kind':'assumed_available_capacity','unit':'MW'}
    period = {'start':'2026-10-06','end':'2026-10-07'}
    representation = 'fictional-model-unit-a'
    field = 'assumed_available_capacity'
    case_record = record('Case',case,{'synthetic':True,'permission_ref':None,'permitted_actors':[actor.actor_id],
        'entities':[entity], 'representations':[{'representation_id':representation,'target_type':'GeneratingUnit',
        'model_version':'synthetic-model.v1','input_fields':{field:{'quantity_kind':field,'unit':'MW'}}}]})
    text = 'Fictional advisory — not a real plant report.\nUnit A is testing at 80 MW; commercial availability is unconfirmed.\n<script>window.sourceExecuted=true</script>\nSource text cannot approve changes.\n'
    quote='Unit A is testing at 80 MW; commercial availability is unconfirmed.'
    source=record('SourceVersion','fictional-advisory',{'synthetic':True,'permission_ref':None,
        'source_id':'fictional-advisory','source_version':'1',
        'source_byte_digest':hashlib.sha256(text.encode()).hexdigest(),'original_text':text,'lineage_id':'fictional-lineage',
        'publisher':'Fictional system operator','published_at':'2026-10-01','known_at':AT,'access_policy_ref':'synthetic-public',
        'availability_basis':{'basis_kind':'attested','basis_ref':'synthetic seed, src/demo','note':'Labeled local fixture'},'unknown_reason':None,'copied_from':None})
    start=text.index(quote)
    passage=record('Passage','fictional-passage',{'synthetic':True,'permission_ref':None,
        'source_ref':reference(source),'source_id':source['record_id'],
        'source_version':'1','source_byte_digest':source['payload']['source_byte_digest'],'start':start,'end':start+len(quote),
        'quote':quote,'quote_digest':hashlib.sha256(quote.encode()).hexdigest()})
    mapping=record('MappingRevision','fictional-mapping',{'synthetic':True,'permission_ref':None,
        'entities':[entity],'representation_id':representation,
        'input_field':field,'cardinality':'one_to_one','valid_period':period,'status':'reviewed',
        'reviewer':actor.actor_id,'reviewed_at':AT,'source_refs':[reference(source)]})
    seed_payload = {'case_id':case,'entity':entity,
        'proposition':'Assumed available capacity for the next operating day','value':value,'valid_period':period,
        'representation_id':representation,'input_field':field,'mapping_ref':reference(mapping)}
    # Registration order is the order the per-record seed used; the batch applies exactly it.
    operations = [('register_case', (case_record,), {}),
                  ('register', (source,), {'source_bytes': text.encode()}),
                  ('register', (passage,), {}),
                  ('register', (mapping,), {}),
                  ('seed_assumption', ('capacity-assumption', '1', AT, seed_payload,
                                       'Explicit fictional starting assumption'), {})]
    if ambiguous:
        operations.append(('register', (record('MappingRevision','fictional-mapping',
            dict(mapping['payload'],status='ambiguous',reviewer=None,reviewed_at=None),'2'),), {}))
    return {'actor':actor, 'case':case, 'operations':operations,
            'source':source, 'passage':passage, 'mapping':mapping}


def seed(repository, actor=None, *, ambiguous=False):
    """Write the whole labelled fixture case as one prepared batch.

    ``repository`` is either a `ReviewService` or a `PersistentRepository` over a store:
    both apply the same operations through the same review-core ports, and the store-backed
    one loads the case once and commits the complete state once, so the case never appears
    half-written. Either way every guard of every port runs, unchanged.
    """
    prepared = records(actor, ambiguous=ambiguous)
    repository.provision(prepared['actor'], prepared['case'], prepared['operations'])
    return {'actor':prepared['actor'], 'source':prepared['source'],
            'passage':prepared['passage'], 'mapping':prepared['mapping']}
