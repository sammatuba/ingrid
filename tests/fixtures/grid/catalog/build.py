#!/usr/bin/env python3
"""Build the data catalog fixture: a small baked replay the catalog builder measures.

The bake under ``bake/`` is produced by the **real** builder — ``scripts/grid/build_data.py``
over the synthetic grid fixture (``tests/fixtures/grid/snapshot``, ``geo`` and ``events.json``)
plus the synthetic inputs beside this file: the event-map spike output the bake turns into
``vectors.json``, one recorded event view it copies into ``events/``, and the recorded view plan
sets BAKE-1 copies into ``views/``. VIEW-1 regenerates those plan sets through the governed
view composer (``src/judgment/view.py``): one ``answer_question()`` call per recorded question
over the fixture's own records — the event view above, the fixture archive's one vintage, the
impact policy's own constants and the event's labelled judgment block — so every receipt
carries the composer's full field set and every figure is a record field copied by code. The
sets are keyed by the fixture event's id and by the pages that carry the assistant's mount
(``home``, ``outlooks``, ``register``, ``models``, ``ask``). DOCK-1: the composer's plan shape is
``view.v4`` (components, actions and parts left out with reason keys, no text); the sets are
regenerated through the same ``answer_question()`` path with the labelled ``FixtureView``, so
each receipt carries the plan with its keys, the page's own template sentences and the actions
proposed, refused and run. BOOK-4: the record set also carries the synthetic book's exposure
record for the fixture event's region (Visayas) over the window of the strategy's question
(2026-10-19, 13:00 to 15:00) at the plan cutoff, built by the book adapter
(``src/book/adapter.py``) from the committed book fixture; the exposure answer shows the exposure
table first and leaves the account impact card out under the manifest's own key, because both
fixture vintages were issued after the plan cutoff. Nothing here is a real WESM row,
plant, coordinate, operator message or case fact, and nothing is read from the company copy:
the values are the grid fixture's own synthetic rows.

    /usr/bin/python3 tests/fixtures/grid/catalog/build.py            # write bake/ beside this file
    /usr/bin/python3 tests/fixtures/grid/catalog/build.py --check    # compare, write nothing

``--check`` rebuilds in memory and compares every byte, so the committed bake is reproducible
from the formulas and the builder alone (``tests/test_grid_catalog.py`` runs it that way).
"""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.book.adapter import BookAdapter  # noqa: E402
from src.contracts.jsonutil import compute_content_digest  # noqa: E402
from src.judgment import view  # noqa: E402
from src.outlook.records import OutlookArchive  # noqa: E402
from src.price.impact import (MATERIALITY_COMPARATOR, MATERIALITY_RULE,  # noqa: E402
                              MATERIALITY_STATEMENT, MATERIALITY_THRESHOLD_PHP,
                              SYNTHETIC_STATEMENT, MaterialityPolicy)
GRID_FIXTURE = HERE.parent
SNAPSHOT = GRID_FIXTURE / 'snapshot'
GEO = GRID_FIXTURE / 'geo'
EVENTS = GRID_FIXTURE / 'events.json'
NODES = SNAPSHOT / 'nodes_0921_5min.csv'
SPIKE = HERE / 'inputs' / 'spike.json'
VIEWS = HERE / 'inputs' / 'events'
#: DESK-1: the synthetic register and price-outlook archive the bake's outlook views are read
#: from. They live beside the grid fixture so the bake stays reproducible without `.local/`.
OUTLOOK = GRID_FIXTURE / 'outlook'
TARGET = HERE / 'bake'
#: VIEW-1: the recorded view plan sets the bake copies and lists, now produced by the
#: composer itself. Every view is one ``answer_question()`` call over the synthetic fixture's
#: own records — the event view, the fixture archive's one vintage, the impact policy's own
#: constants and the event's labelled judgment block — so each receipt carries the composer's
#: full field set and every figure is a record field the composer copied. The bakes are
#: static: they replay recorded or fixture plans and call no model.
PLAN_CUTOFF = '2026-10-17T00:00:00Z'
#: The fixture event's own clock is Manila civil time. The recorded view states its times
#: without an offset; the composer refuses a stamp that names no instant, so every stamp
#: carries the replay's own offset (the page's footer says "replay in Manila time").
FIXTURE_OFFSET = '+08:00'
#: The page keys, plus the fixture event's own id (so the bake sets ``ask: true`` on its event
#: view) and the assistant's full-screen page. The panel on each page reads its own key.
PLAN_KEYS = ('ask', 'home', 'models', 'outlooks', 'register', 'syn-bay-unit-2-trip')
#: The fixture event view the plan records are read from (BAKE-1's recorded view).
EVENT_VIEW = VIEWS / 'syn-bay-unit-2-trip.json'
#: The one synthetic vintage of the fixture archive, read through the real archive class.
VINTAGE = 'outlook-fixture-2026-11-system'
#: VIEW-1: the fixture's own statements, written without a semicolon because the panel draws
#: them as prose and the copy rules allow none (VIEW-1 review, finding 4). The impact policy's
#: ``SYNTHETIC_STATEMENT`` prefix is that module's own text and is passed through unchanged.
IMPACT_LABEL_SUFFIX = '. This fixture record scores no portfolio change'
UNIT_STATEMENT = ('Synthetic Bay Unit 2 is a generator unit. The fixture portfolio holds load '
                  'nodes, so this unit is not a portfolio node')
#: BOOK-4: the book's exposure question for the fixture event's region: "What is exposed in
#: Visayas tomorrow 13:00 to 15:00?" over the day the fixture vintages price (BOOK-2's worked
#: example), read at the plan cutoff. The policy is IMPACT-1's stated demonstration line.
BOOK_REGION = 'Visayas'
BOOK_WINDOW = '2026-10-19T13:00/2026-10-19T15:00'


def book_adapter() -> BookAdapter:
    """The book adapter over the committed book and fixture vintages, IMPACT-1's stated line."""
    return BookAdapter(MaterialityPolicy())


def plan_exposure() -> dict:
    """The exposure record of the fixture event's region over the book window, at the cutoff."""
    return book_adapter().exposure_record(BOOK_WINDOW, PLAN_CUTOFF, region=BOOK_REGION)


def plan_ids(records: dict) -> dict:
    """The identifiers the action manifest offers for the book: the exposure record's own."""
    return book_adapter().manifest_ids(records['exposure'])


def _stamped(value) -> str:
    """A fixture stamp with the replay's offset when the record states none."""
    text = str(value)
    return text if ('+' in text[10:] or text.endswith('Z')) else text + FIXTURE_OFFSET


def plan_event() -> dict:
    """The fixture event record, read from the fixture's own recorded event view.

    The title, assumption, advisory and timeline are the view's fields; the composer needs a
    record id, an ``event_at`` and an assumption block, and it refuses a stamp without an
    offset, so the view's Manila times carry the replay's own offset above.
    """
    recorded = json.loads(EVENT_VIEW.read_text(encoding='utf-8'))
    assumption = recorded['assumption']
    return {
        'record_id': recorded['id'],
        'id': recorded['id'],
        'synthetic': True,
        'label': 'synthetic fixture',
        'title': recorded['title'],
        'event_at': _stamped(recorded['event_at']),
        'advisory': {'id': recorded['advisory']['id'],
                     't': _stamped(recorded['advisory']['t'])},
        'timeline': [{'t': _stamped(row['t']), 'kind': row['kind'], 'src': row['src']}
                     for row in recorded['timeline']],
        'assumption': {'value': assumption['value'], 'unit': assumption['unit'],
                       'proposition': assumption['proposition']},
    }


def plan_outlook() -> dict:
    """The outlook record: the fixture archive's own vintage, re-verified on read."""
    vintage = OutlookArchive(OUTLOOK / 'archive').outlook(VINTAGE)
    recorded = json.loads(EVENT_VIEW.read_text(encoding='utf-8'))
    return {
        'event_id': recorded['id'],
        'assumption': {'text': recorded['assumption']['proposition']},
        'rests_on_this_assumption': False,
        'synthetic': True,
        'label': 'synthetic fixture',
        'outlooks': [vintage],
    }


def plan_impact() -> dict:
    """The impact record: the impact policy's own constants, and no scored change.

    The materiality line and its rule are the module's own stated policy, never a market
    figure. The direction counts are zero because no portfolio change is scored on this
    fixture; the record says so in its label, and the exposure view shows the line before the
    counts.
    """
    label = SYNTHETIC_STATEMENT + IMPACT_LABEL_SUFFIX
    record = {
        'record_id': 'VIEW-1-FIXTURE-IMPACT',
        'label': label,
        'synthetic': True,
        'materiality': {'threshold_php': MATERIALITY_THRESHOLD_PHP,
                        'comparator': MATERIALITY_COMPARATOR, 'rule': MATERIALITY_RULE},
        'direction_check': {'id': 'VIEW-1-FIXTURE-IMPACT',
                            'statement': MATERIALITY_STATEMENT,
                            'changes_compared': 0, 'material_changes': 0,
                            'nodes_with_a_material_change': 0, 'label': label},
        'unit': {'site': recorded_site(), 'kind': 'generator', 'portfolio_node': False,
                 'statement': UNIT_STATEMENT},
    }
    record['content_digest'] = compute_content_digest(record)
    return record


def recorded_site() -> str:
    """The fixture event's site code, when its recorded view carries one."""
    recorded = json.loads(EVENT_VIEW.read_text(encoding='utf-8'))
    return recorded.get('site') or recorded['id']


def plan_judgment() -> dict:
    """The judgment record: the fixture event view's own labelled reading block.

    The label, the rule and the run's word are the recorded block's; ``provenance`` repeats
    that word so the receipt's labels list never presents the composed reading as a label.
    The fixture states no unresolved disagreement and no instability, and no question rows
    because the block records none.
    """
    recorded = json.loads(EVENT_VIEW.read_text(encoding='utf-8'))
    block = recorded['judgment']
    return {
        'record_id': 'syn-judgment-1',
        'information_cutoff': _stamped(recorded['event_at']),
        'synthetic': True,
        'label': block['label'],
        'rule': block['rule'],
        'by': block['receipt'],
        'receipt': block['receipt'],
        'provenance': block['receipt'],
        'unstable': False,
        'questions': [],
    }


def plan_records() -> dict:
    """The one synthetic record set every page's plan set is composed from (BOOK-4: with the
    book's exposure record, so the book is in every page's manifest)."""
    return {'event': plan_event(), 'outlook': plan_outlook(), 'impact': plan_impact(),
            'judgment': plan_judgment(), 'exposure': plan_exposure()}


def plan_views() -> list:
    """The three recorded questions' answers, through the composer's whole path.

    ``answer_question()`` renders the request, the labelled fixture backend plans it, the
    validator checks the plan and ``compose()`` fills every part from the records. Every page
    key carries the same three answers because the fixture records one event; a real bake
    carries the plans the orchestrator recorded for each page's own records.
    """
    records = plan_records()
    backend = view.fixture_backend()
    ids = plan_ids(records)
    return [view.answer_question(spec['question'], records, PLAN_CUTOFF, backend, ids=ids)
            for spec in view.QUESTION_SPECS]


def plan_files() -> dict:
    """``{key: document}``: the plan sets, each naming its own file key."""
    answers = plan_views()
    return {key: {'key': key, 'views': json.loads(json.dumps(answers))}
            for key in PLAN_KEYS}


def builder():
    """``scripts/grid/build_data.py`` by file location, the way the suite loads it."""
    path = ROOT / 'scripts' / 'grid' / 'build_data.py'
    spec = importlib.util.spec_from_file_location('grid_build_data', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def files(where: Path = None) -> dict:
    """``{name: bytes}``: the bake the real builder writes over the synthetic inputs.

    ``where`` is the directory the view's parent snapshot is assembled in; the builder reads
    the CSVs, the location material, the event spec, the node file and the spike output, so the
    only things staged are the ``events/`` directory the recorded views live in and the
    ``views/`` directory the plan sets live in (BAKE-1), both beside the snapshot's CSVs.
    """
    build_data = builder()
    with tempfile.TemporaryDirectory() as scratch:
        snapshot = Path(where or scratch) / 'snapshot'
        snapshot.mkdir(parents=True, exist_ok=True)
        for path in sorted(SNAPSHOT.glob('*.csv')):
            shutil.copyfile(path, snapshot / path.name)
        (snapshot / 'events').mkdir(exist_ok=True)
        for path in sorted(VIEWS.glob('*.json')):
            shutil.copyfile(path, snapshot / 'events' / path.name)
        (snapshot / 'views').mkdir()
        for key, document in plan_files().items():
            (snapshot / 'views' / (key + '.json')).write_text(
                json.dumps(document, separators=(',', ':')), encoding='utf-8')
        payload, _ = build_data.build(snapshot, GEO, EVENTS, [snapshot / NODES.name], SPIKE,
                                      register_path=OUTLOOK / 'register.json',
                                      archive_root=OUTLOOK / 'archive')
    return payload


def check(target: Path = TARGET) -> list:
    """Every file that differs from what the real builder produces now."""
    expected = files()
    problems = []
    for name, data in sorted(expected.items()):
        path = target / name
        if not path.is_file():
            problems.append('missing %s' % name)
        elif path.read_bytes() != data:
            problems.append('%s differs from the builder' % name)
    extra = sorted(str(path.relative_to(target)) for path in target.rglob('*')
                   if path.is_file() and str(path.relative_to(target)) not in expected)
    problems += ['unexpected %s' % name for name in extra]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('target', nargs='?', type=Path, default=TARGET)
    parser.add_argument('--check', action='store_true')
    options = parser.parse_args(argv)
    if options.check:
        problems = check(options.target)
        print('\n'.join(problems) if problems
              else 'OK: %d fixture bake files reproduce' % len(files()))
        return 1 if problems else 0
    written = files()
    options.target.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(written.items()):
        (options.target / name).parent.mkdir(parents=True, exist_ok=True)
        (options.target / name).write_bytes(data)
        print('%s %d' % (name, len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
