#!/usr/bin/env python3
"""Build the outlook fixture inputs: a synthetic register and a synthetic price-outlook archive.

DESK-1 puts the committed assumption register (ARCH-2) and the runtime price-outlook archive
(ARCH-1/ARCH-3) on the event page. The page's own fixtures must not depend on `.local/` — that
directory is a runtime place, absent from most worktrees and from every review sandbox — so
this builder writes the two inputs the other fixture builds read: ``register.json``, a
synthetic three-row register in the ARCH-2 shape, and ``archive/``, one issued price outlook
and one labelled demonstration mark in the ARCH-1/ARCH-3 shape. Both are written by the real
modules (`src.outlook.register`'s validator, `src.outlook.records.OutlookArchive`,
`src.outlook.dependency.build_mark`), never typed by hand, and ``--check`` proves the committed
bytes reproduce.

Every value here is synthetic: no real price, node, resource, portfolio or case fact, and
nothing is read from the company copy. The register's citations point at this file's own
declaration lines, so each one is a real line of a real file (the register's own citation
check finds nothing dangling); the counted families are declared as the synthetic rows they
are, so this register is audited against this file and not against the company sources.

    /usr/bin/python3 tests/fixtures/grid/outlook/build.py            # write beside this file
    /usr/bin/python3 tests/fixtures/grid/outlook/build.py --check    # compare, write nothing
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.outlook import dependency as outlook_dependency  # noqa: E402
from src.outlook import register as outlook_register  # noqa: E402
from src.outlook.records import OutlookArchive, build_outlook  # noqa: E402

REGISTER_FILE = 'register.json'
ARCHIVE_DIR = 'archive'
SELF = 'tests/fixtures/grid/outlook/build.py'

#: The event assumption the register's availability row states, word for word: the page
#: fixture's synthetic event records exactly this text ('Synthetic Bay Unit 2 available
#: capacity'), so its lookup resolves the row below.
PROP_SYN_BAY = 'Synthetic Bay Unit 2 available capacity is 180 MW on the synthetic day.'

#: The three propositions, each on one line of its own: the register row's citation quote is
#: the proposition's own text, so the locator points at the line that really holds it (an
#: audit of the fixture finds no dangling locator, and no other line carries the words).
PROP_CUT = "The fixture's price cut is 3,000 PHP/MWh on the synthetic day."
PROP_COMPOSER = 'The fixture composer refuses a row it cannot read.'

#: The synthetic outlook. It cites the availability row above and one threshold row, declares
#: itself synthetic (`synthetic: true`) and makes no skill claim anywhere.
OUTLOOK = {
    'outlook_id': 'outlook-fixture-2026-11-system',
    'issued_at': '2026-10-16T00:00:00Z',
    'information_cutoff': '2026-08-25T16:00:00Z',
    'horizon': {'label': 'month', 'start': '2026-10-25T16:00:00Z', 'end': '2026-11-25T16:00:00Z'},
    'target_series_ref': {'table': 'fixture_grid.synthetic_lwap', 'column': 'lwap',
                          'version': 'fixture-bmonth-2026-11'},
    'inputs': [{'name': 'fixture_hourly.csv', 'digest': 'a1' * 32}],
    'assumption_ids': ['availability:syn-bay-unit-2', 'threshold:fixture_cut'],
    'model_version': 'fixture seasonal average',
    'values_ref': {'path_hint': 'tests/fixtures/grid/outlook/values.json',
                   'sha256': 'b2' * 32, 'rows': 4},
    'issuer': 'DESK-1 fixture',
    'synthetic': True,
}

#: One labelled demonstration mark on the issued outlook: `synthetic: true` declares it a
#: demonstration of the marking path, never evidence that something changed.
MARK = {
    'assumption_id': 'threshold:fixture_cut',
    'new_revision': 'abc1234',
    'assumption_state': 'deployed',
    'marked_at': '2026-10-17T00:00:00Z',
    'synthetic': True,
}

#: The synthetic register's rows, in file order. Each carries a quote this builder locates in
#: its own text (the proposition's own line above), so the citation is a real one.
ROWS = (
    {'assumption_id': 'threshold:fixture_cut', 'family': 'threshold', 'layer': 'analytical',
     'state': 'deployed', 'owner': 'unassigned',
     'proposition': PROP_CUT,
     'quote': PROP_CUT,
     'falsifier': 'A fixture day whose synthetic median crosses the cut.',
     'affected_code': ['scripts/grid/build_data.py']},
    {'assumption_id': 'composer:fixture_row', 'family': 'composer', 'layer': 'exploratory',
     'state': 'test_fixture', 'owner': 'unassigned',
     'proposition': PROP_COMPOSER,
     'quote': PROP_COMPOSER,
     'falsifier': 'A synthetic row the fixture composer reads although it cannot.',
     'affected_code': ['src/grid/event.js']},
    {'assumption_id': 'availability:syn-bay-unit-2', 'family': 'availability',
     'layer': 'analytical', 'state': 'accepted', 'owner': 'unassigned',
     'proposition': PROP_SYN_BAY,
     'quote': PROP_SYN_BAY,
     'falsifier': 'A fixture day on which the synthetic unit is stated unavailable.',
     'affected_code': ['src/grid/event.js', 'scripts/grid/build_data.py']},
)


def line_of(quote: str) -> int:
    """The one-based line of this builder's own text that carries ``quote``."""
    lines = [n for n, text in enumerate(Path(__file__).read_text(encoding='utf-8').splitlines(), 1)
             if quote in text]
    if len(lines) != 1:
        raise SystemExit('the fixture quote is not exactly one line of this file: %r' % quote)
    return lines[0]


def register_document() -> dict:
    """The synthetic register envelope, in the ARCH-2 contract."""
    assumptions = []
    for row in ROWS:
        assumptions.append({
            'assumption_id': row['assumption_id'],
            'proposition': row['proposition'],
            'family': row['family'],
            'layer': row['layer'],
            'source_locator': [{'path': SELF, 'line': line_of(row['quote']), 'quote': row['quote']}],
            'valid_from': None,
            'valid_to': None,
            'state': row['state'],
            'owner': row['owner'],
            'affected_code': list(row['affected_code']),
            'falsifier': row['falsifier'],
            'last_checked_revision': None,
        })
    return {'register_version': outlook_register.REGISTER_VERSION,
            'sources': [{'family': 'threshold',
                         'path': outlook_register.SOURCE_PATHS['threshold'], 'rows': 1},
                        {'family': 'composer',
                         'path': outlook_register.SOURCE_PATHS['composer'], 'rows': 1}],
            'assumptions': assumptions}


def archive_files(where: Path) -> dict:
    """``{relative name: bytes}`` of the synthetic archive, written by the real classes."""
    archive = OutlookArchive(where)
    record = build_outlook(**OUTLOOK)
    archive.issue(record)
    mark = outlook_dependency.build_mark(
        assumption_id=MARK['assumption_id'], new_revision=MARK['new_revision'], outlook=record,
        assumption_state=MARK['assumption_state'], marked_at=MARK['marked_at'],
        synthetic=MARK['synthetic'])
    outlook_dependency.StaleMarks(where).append(mark)
    return {str(path.relative_to(where)): path.read_bytes()
            for path in sorted(where.rglob('*.json'))}


def files() -> dict:
    """``{relative name: bytes}``: the register and every archive file this fixture holds."""
    written = {REGISTER_FILE: (canonical_dumps(register_document()) + '\n').encode('utf-8')}
    with tempfile.TemporaryDirectory(prefix='outlook-fixture-') as scratch:
        archive = archive_files(Path(scratch))
    written.update({ARCHIVE_DIR + '/' + name: data for name, data in archive.items()})
    return written


def check() -> list:
    """Every committed fixture file that differs from what the real classes produce now."""
    expected = files()
    problems = []
    for name, data in sorted(expected.items()):
        path = HERE / name
        if not path.is_file():
            problems.append('missing %s' % name)
        elif path.read_bytes() != data:
            problems.append('%s differs from the builder' % name)
    extra = sorted(str(path.relative_to(HERE)) for path in HERE.rglob('*')
                   if path.is_file() and str(path.relative_to(HERE)) not in expected
                   and path.suffix == '.json')
    problems += ['unexpected %s' % name for name in extra]
    return problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--check']:
        problems = check()
        print('\n'.join(problems) if problems
              else 'OK: the register and %d archive files reproduce' % (len(files()) - 1))
        return 1 if problems else 0
    if argv:
        raise SystemExit('usage: build.py [--check]')
    written = files()
    shutil.rmtree(HERE / ARCHIVE_DIR, ignore_errors=True)
    for name, data in sorted(written.items()):
        path = HERE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print('%s %d' % (name, len(data)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
