#!/usr/bin/env python3
"""Build the GRID-3 event fixture: `view.json` and `flow.json`, from the real code only.

`view.json` is the shape the event page's adapter reads (the page's own baked file is written
by the orchestrator's converter, `docs/work/grid-desk/reference/event_judgment.py`); its
advisory text, posting time and assumption are read from `src/demo/pedc-case.json`, the rows
the runtime module builds the judge's case from.

`flow.json` is the recorded flow of three judge decisions on a deterministic session: the
session answer, and per decision the prepare request the adapter sends, the case heads, the
snapshot, the compiled task (the three the one `POST .../prepare` call answers with, PERF-3),
the review request, the receipt, the accepted outlook the adapter reads back, and the history
after it — every record the object the real code returned (the HTTP routes in `src/api/hosted.py`
return these objects unchanged). The session is provisioned by `src.api.hosted._provision`, the
function `POST /demo/session` calls, with a pinned uid and a pinned instant, so the fixture is
reproducible; its `id_token` is a short fixture label, because the real one is minted per
session by the sandbox identity and names nothing.

The audit cutoff each snapshot carries is the adapter's own rule, replayed here instead of
restated: the seeding instant for the first decision, and for every later one the `recorded_at`
of the outlook the previous decision was accepted as — the record the adapter reads back
(`POST .../read`). The three decisions therefore cover both orders the review named: retain
then revise, and revise then retain.

Nothing here is typed by hand and no model, credential, network or cloud call is reachable.

`outlook.json` (DESK-1) is the event page's register-and-price-outlook view for this event,
written by the real builder (`scripts/grid/build_data.py`) from the synthetic register and
price-outlook archive beside the grid fixture (`tests/fixtures/grid/outlook/`) and from the
event's own assumption text in `scripts/grid/events.json` — the text the bake records. The
fixture register carries no row for that text, so the shim renders the honest reading: the
assumption is not registered and no issued price outlook rests on it.

    /usr/bin/python3 tests/fixtures/grid/event/build.py            # write the three files
    /usr/bin/python3 tests/fixtures/grid/event/build.py --check    # compare, write nothing
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adapters.wesm import advisories as wesm_advisories  # noqa: E402
from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.demo import pedc  # noqa: E402
from src.review import reference  # noqa: E402
from src.review.storage import PersistentRepository  # noqa: E402

# `src/api/__init__.py` imports FastAPI at module scope, so the hosted assembly is loaded by
# file location the way tests/test_hosted_config.py loads it: everything this fixture uses
# (the session, the provisioning and the store) needs no HTTP library.
SPEC = importlib.util.spec_from_file_location('nowcast_hosted', ROOT / 'src' / 'api' / 'hosted.py')
hosted = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hosted)

HERE = Path(__file__).resolve().parent
VIEW_FILE = HERE / 'view.json'
FLOW_FILE = HERE / 'flow.json'
OUTLOOK_FILE = HERE / 'outlook.json'
#: DESK-1: the synthetic register and archive the outlook view is built from, and the event
#: spec the bake records the event's assumption text in.
OUTLOOK_FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'outlook'
EVENTS_SPEC = ROOT / 'scripts' / 'grid' / 'events.json'

#: A pinned sandbox session: the uid `create_judge_session` would mint, replaced by a fixed
#: one so the case ids are reproducible.
UID = 'demo-' + '7f' * 16
#: A label, not a credential: nothing here talks to a server, and the real token is minted
#: per session by the sandbox identity.
TOKEN = 'fixture'
#: The instant the session was provisioned. It is also the audit cutoff the adapter sends with
#: its first snapshot (`event_seeded_at`), the same way the browser does.
SEEDED_AT = '2026-10-14T02:00:00+00:00'
#: The three decisions the harness makes, with the instant the routes would stamp on each. The
#: second follows the first (retain then revise) and the third follows the second (revise then
#: retain): the order the review found failing is covered by the third.
DECISIONS = (
    {'choice': {'decision': 'retain', 'value': None,
                'reason': 'Fixture decision: the trip puts the assumed availability in question.'},
     'key': 'event:%s:retain:1' % pedc.EVENT_ID, 'at': '2026-10-14T02:01:00+00:00'},
    {'choice': {'decision': 'revise', 'value': '95.5',
                'reason': 'Fixture decision: the unit is back, and the register value stands.'},
     'key': 'event:%s:revise:2' % pedc.EVENT_ID, 'at': '2026-10-14T02:02:00+00:00'},
    {'choice': {'decision': 'retain', 'value': None,
                'reason': 'Fixture decision: the revised value is the one the register supports.'},
     'key': 'event:%s:retain:3' % pedc.EVENT_ID, 'at': '2026-10-14T02:03:00+00:00'},
)


def trip_advisory():
    """The trip advisory of 2026-09-21, read from the committed rows by the DATA-1 reader."""
    batch = wesm_advisories.parse_advisories(pedc.case_data()['rows']['advisories'])
    return next(item for item in batch.advisories if item.row['adv_id'] == 'V133937')


def case_definition():
    return pedc.case_data()['case']


def view_document():
    """The adapter harness's view model: the fields the adapter reads, from the real rows."""
    trip = trip_advisory()
    definition = case_definition()
    field = definition['representation']['input_fields'][definition['input_field']]
    run = pedc.register_run()
    return {
        'id': pedc.EVENT_ID,
        'title': 'PEDC Unit 2 trip · Visayas',
        'grid': 'CVIS',
        'grid_name': 'Visayas',
        'event_at': trip.event_at,
        'advisory': {'id': trip.row['adv_id'], 't': trip.source['known_at'].replace('T', ' ').replace('+08:00', ''),
                     'text': trip.passage['quote']},
        'timeline': [], 'market': {'t': [], 'lmp': [], 'short': [], 'imp': [], 'marks': []},
        'figures': [],
        'assumption': {'value': float(run.capacity_mw), 'unit': field['unit'],
                       'proposition': definition['assumption']['proposition'], 'kv': []},
        'judgment': None,
        'fixture_note': ('Adapter-harness shape fixture. The event page’s own baked view model is '
                         'written by the orchestrator’s converter (docs/work/grid-desk/reference/'
                         'event_judgment.py); this file carries the fields the adapter reads, taken from '
                         'the rows in src/demo/pedc-case.json.'),
    }


def decision_documents(repository, session, information_cutoff):
    """The recorded answers of the three decisions: prepare, review and read-back.

    One `prepare_task` call per decision does what `POST .../prepare` does: it answers the case
    heads, the snapshot at the audit cutoff and the task compiled at the information cutoff, and
    it writes the snapshot and the task — the same records the separate calls wrote before
    PERF-3. `state_at` is the adapter's rule, not a restatement: the first snapshot audits the
    seeding instant, and each later one audits the `recorded_at` of the outlook the previous
    decision was accepted as — the record the adapter re-reads through `POST .../read`
    (`repository.read`, the function that route calls).
    """
    actor = hosted._event_actor(session)
    decisions, history = [], []
    state_at = session.event_seeded_at
    for step in DECISIONS:
        at, audit_cutoff = step['at'], state_at
        prepare = {'audit_cutoff': audit_cutoff, 'information_cutoff': information_cutoff}
        prepared = repository.prepare_task(actor, session.event_case, audit_cutoff,
                                           information_cutoff, at)
        heads, snapshot, task = prepared['heads'], prepared['snapshot'], prepared['task']
        value = task['payload']['assumption_definition']['value']
        review = {
            'case_id': session.event_case, 'request_id': step['key'], 'idempotency_key': step['key'],
            'task_ref': reference(task),
            'snapshot_digest': task['payload']['snapshot_ref']['content_digest'],
            'expected_assumption_head': task['payload']['assumption_ref'],
            'expected_outlook_head': heads['outlook'],
            'disposition': step['choice']['decision'], 'rationale': step['choice']['reason'],
            'new_value': ({'value': step['choice']['value'], 'quantity_kind': value['quantity_kind'],
                           'unit': value['unit']} if step['choice']['decision'] == 'revise' else None),
            'judgment_ref': None, 'reviewed_at': at, 'recorded_at': at,
        }
        receipt = repository.commit_review(actor, review)
        acceptance = repository.read(actor, session.event_case, receipt['outlook_ref'])
        state_at = acceptance['recorded_at']
        history = repository.history(actor, session.event_case)
        decisions.append({'choice': step['choice'], 'key': step['key'], 'at': at,
                          'audit_cutoff': audit_cutoff, 'prepare': prepare, 'heads': heads,
                          'snapshot': snapshot, 'compile': task, 'review': review, 'receipt': receipt,
                          'acceptance': acceptance})
    return decisions, history


def flow_document():
    """The recorded flow of one deterministic session, provisioned and decided for real."""
    session = hosted.Session(UID, hosted.JUDGE_TENANT, hosted.session_case(UID),
                             hosted.event_case(UID), SEEDED_AT)
    store = hosted.MemoryStore()
    repository = PersistentRepository(store)
    hosted._provision(store, repository, session, SEEDED_AT)
    information_cutoff = trip_advisory().source['known_at']
    assumption_id = case_definition()['assumption']['record_id']
    decisions, history = decision_documents(repository, session, information_cutoff)
    return {
        'fixture_version': 'grid-event-flow.v2',
        'note': ('Recorded by tests/fixtures/grid/event/build.py from the real repository over a pinned '
                 'session; the adapter harness (run.mjs) replays it, and --check refuses drift. v2: '
                 'each decision records the one prepare request that answers heads, snapshot and task.'),
        'information_cutoff': information_cutoff,
        'session': {'id_token': TOKEN, 'mode': 'demo', 'tenant': session.tenant, 'case': session.case,
                    'event_case': session.event_case, 'event_seeded_at': session.event_seeded_at,
                    'fixture_digest': hosted.fixture_digest()},
        'assumption_id': assumption_id,
        'decisions': decisions,
        'history': history,
    }


def outlook_document():
    """The register-and-price-outlook view for this fixture's event (DESK-1), by the real builder.

    The event's assumption text is read from the bake's own event spec, so the fixture shows
    the text the page would show; the register and the archive are the synthetic fixtures
    beside the grid fixture, so the document is reproducible without `.local/`.
    """
    spec = importlib.util.spec_from_file_location('grid_build_data_event_fixture',
                                                  ROOT / 'scripts' / 'grid' / 'build_data.py')
    build_data = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = build_data
    spec.loader.exec_module(build_data)
    events = json.loads(EVENTS_SPEC.read_text(encoding='utf-8'))
    event = next(item for item in events if item['id'] == pedc.EVENT_ID)
    built, _ = build_data.price_outlook_files([event], OUTLOOK_FIXTURE / 'register.json',
                                              OUTLOOK_FIXTURE / 'archive')
    return json.loads(built['outlook/%s.json' % pedc.EVENT_ID].decode('utf-8'))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check_only = '--check' in argv
    unknown = [arg for arg in argv if arg != '--check']
    if unknown:
        raise SystemExit('usage: build.py [--check]')
    view, flow, outlook = view_document(), flow_document(), outlook_document()
    if check_only:
        problems = []
        for path, expected in ((VIEW_FILE, view), (FLOW_FILE, flow), (OUTLOOK_FILE, outlook)):
            if not path.exists():
                problems.append('%s is missing' % path.name)
            elif canonical_dumps(json.loads(path.read_text(encoding='utf-8'))) != canonical_dumps(expected):
                problems.append('%s differs from a fresh build' % path.name)
        if problems:
            raise SystemExit('fixture problem: ' + '; '.join(problems))
        print('OK: view.json, flow.json and outlook.json reproduce; %d decisions, %d history '
              'entries, information cutoff %s' % (len(flow['decisions']), len(flow['history']),
                                                  flow['information_cutoff']))
        return 0
    for path, document in ((VIEW_FILE, view), (FLOW_FILE, flow), (OUTLOOK_FILE, outlook)):
        path.write_text(canonical_dumps(document) + '\n', encoding='utf-8')
        print('wrote', path.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
