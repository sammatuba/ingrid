"""The assumption register: what every outlook proposition rests on, and where it comes from.

An :class:`AssumptionRecord` is one proposition the price outlook rests on: its family, the
layer its value comes from, the source it is read at, the interval it is valid for, where it
stands, who owns it, the code it affects, what would falsify it and the revision it was last
checked at. The records live in ``docs/work/outlook-archive/register.json``; this module
validates them, loads them and audits them against the two sources they are read from.

Two fields are deliberately readable in both directions:

* ``layer`` is where the value comes from — ``official`` (an authoritative document fixes it:
  the frozen product definition, working paper section 5.2, or an official document or market
  rule), ``analytical`` (measured or derived from the data), ``inferred`` (it rests on an
  unconfirmed meaning or an internal document) or ``exploratory`` (a provisional design choice
  of the method). ``hypothesis`` is a fifth, valid layer for propositions that are not yet any
  of those; the ARCH-2 acceptance labels the 23 threshold and 14 composer rows with the other
  four, and :func:`audit` reports any of those 37 that carries another label.
* ``state`` is where the proposition stands — ``accepted`` (an owner accepted it with a
  record), ``deployed`` (a record shows it in force in a built artefact), ``unverified`` (in
  use, with no source or check confirming it), ``contradicted`` (a record disagrees),
  ``test_fixture`` (exercised on fixtures, scripted backends or recorded replays only) or
  ``designed_unrun`` (designed, never exercised). ``deployed`` says the value is in force, not
  that it is verified; the layer and the falsifier carry that.

The register leaves what is unknown unknown. ``valid_from``, ``valid_to`` and
``last_checked_revision`` are ``null`` where no record states them, and the audit counts those
rows instead of inferring a date from the value or a revision from a commit.

Failure surface (all ``RegisterError``, with the messages :data:`MESSAGES` owns):

* ``INVALID_RECORD`` for a record that is not a JSON-safe object of exactly the documented
  keys with the documented shapes, or whose id does not name its own family;
* ``INVALID_REGISTER`` for an envelope that is not the register, whose declared source row
  counts do not match its own records, or whose assumptions are not records;
* ``INVALID_JSON`` for a file that does not parse, carries duplicate object keys or a
  non-finite number;
* ``INVALID_SOURCE`` when a statement one of the readers parses cannot be found in, or
  cannot be read from, its SQL text.

Nothing here calls a model, a network, a clock or a database: the module is stdlib plus the
repository's own canonical-JSON and review-record helpers.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from src.contracts.jsonutil import parse_json
from src.review.records import json_copy

#: The register's own version, carried in the file's envelope.
REGISTER_VERSION = 'outlook-register.v1'

#: The families a proposition can belong to.
FAMILIES = frozenset({'availability', 'rules', 'projects', 'price', 'threshold', 'composer'})

#: Every layer the schema accepts; :data:`ACCEPTANCE_LAYERS` is the four the ARCH-2
#: acceptance names for the threshold and composer rows.
LAYERS = frozenset({'official', 'analytical', 'inferred', 'exploratory', 'hypothesis'})
ACCEPTANCE_LAYERS = frozenset({'official', 'analytical', 'inferred', 'exploratory'})

#: Every state the schema accepts.
STATES = frozenset({'accepted', 'unverified', 'contradicted', 'test_fixture', 'designed_unrun', 'deployed'})

#: The two families whose rows the register must carry one for one from their sources.
COUNTED_FAMILIES = ('threshold', 'composer')

#: The record keys, exactly; a record with another key is refused rather than read.
FIELDS = frozenset({'assumption_id', 'proposition', 'family', 'layer', 'source_locator', 'valid_from',
                    'valid_to', 'state', 'owner', 'affected_code', 'falsifier', 'last_checked_revision'})

#: The sources the counted families are read from.
THRESHOLD_SOURCE = 'scripts/data/sql/03_ref_regions_thresholds.sql'
COMPOSER_SOURCE = 'src/judgment/bundle.py'

#: The statement the price bands are read from: the ``price_band`` ladder that turns a capped
#: median into a band name, and the thresholds that ladder cuts on.
PRICE_LABEL_SOURCE = 'scripts/data/sql/05_labels_price.sql'

#: The source each counted family is read from. The envelope declares them, and a declaration
#: naming another path is refused rather than left as a claim nothing checks.
SOURCE_PATHS = {'threshold': THRESHOLD_SOURCE, 'composer': COMPOSER_SOURCE}

#: The register file, relative to the repository root.
REGISTER_PATH = Path('docs/work/outlook-archive/register.json')

#: The repository root, from this file's own place.
ROOT = Path(__file__).resolve().parents[2]

MESSAGES = {
    'INVALID_RECORD': 'a register record needs its documented keys with the documented shapes',
    'INVALID_REGISTER': 'the register envelope does not match the documented shape',
    'INVALID_JSON': 'the register file is not readable canonical JSON',
    'INVALID_SOURCE': 'the threshold statement was not found in the source SQL',
}

#: One date, as the register writes it.
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
#: A commit id, shortened or full.
REVISION = re.compile(r'^[0-9a-f]{7,40}$')
#: The ``grid_ref.thresholds`` statement: every row of it is one threshold.
THRESHOLD_TABLE = re.compile(r'CREATE\s+OR\s+REPLACE\s+TABLE\s+`[^`]*\.grid_ref\.thresholds`\s+AS\s+'
                             r'SELECT\s+\*\s+FROM\s+UNNEST\(\[(.*?)\]\);', re.S)
#: One ``STRUCT('<name>' AS name, <value> AS value, '<version>' AS version, <source>)`` row,
#: with the later rows' shortened form ``STRUCT('<name>', <value>, '<version>', <source>)``.
THRESHOLD_ROW = re.compile(r"STRUCT\(\s*'([^']+)'\s*(?:AS\s+name)?\s*,\s*(-?\d+(?:\.\d+)?)", re.S)
#: The price-label statement's ``price_band`` CASE, from its ``CASE`` to the ``END AS`` that
#: closes it, so a ladder elsewhere in the file cannot be read as this one.
PRICE_BAND_CASE = re.compile(r'CASE\s+(.*?)\s+END\s+AS\s+price_band', re.S)
#: One arm of that ladder: the median, the bound it is tested below, and the band it names.
#: The bound is a decimal literal or ``t.<alias>``, the two forms the statement uses.
PRICE_BAND_ARM = re.compile(r"WHEN\s+p\.gen_lmp_capped_median\s*<\s*(\d+(?:\.\d+)?|t\.\w+)\s+THEN\s+'([^']+)'")
#: The ladder's fall-through: ``ELSE '<band>'``.
PRICE_BAND_ELSE = re.compile(r"ELSE\s+'([^']+)'")
#: The statement's threshold aliases: ``MAX(IF(name = '<threshold>', value, NULL)) AS <alias>``.
PRICE_BAND_ALIAS = re.compile(r"IF\(\s*name\s*=\s*'([^']+)'\s*,\s*value\s*,\s*NULL\s*\)\s*\)?\s*AS\s+(\w+)")


class RegisterError(ValueError):
    """A refusal whose code is stable and whose text :data:`MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, MESSAGES[code])


def _require(condition, code):
    if not condition:
        raise RegisterError(code)


def _nonblank(value):
    return type(value) is str and bool(value.strip())


def _one_of(value, allowed, code='INVALID_RECORD'):
    """A member of a closed vocabulary of strings, refused as a name before it is looked up.

    Membership is tested on the text alone: a list, a dict or a number is not a name the
    vocabulary does not carry, it is a value of the wrong type, and asking whether an
    unhashable object is a member raises ``TypeError`` instead of the documented refusal.
    """
    _require(type(value) is str and value in allowed, code)


def _locator(value):
    """One citation: a repository path, a one-based line and the text read on that line."""
    _require(type(value) is dict and set(value) == {'path', 'line', 'quote'}, 'INVALID_RECORD')
    _require(_nonblank(value['path']) and '\\' not in value['path'], 'INVALID_RECORD')
    _require(type(value['line']) is int and value['line'] >= 1, 'INVALID_RECORD')
    _require(_nonblank(value['quote']), 'INVALID_RECORD')


def _date(value):
    """A valid-interval end: a real calendar date in ISO form, or ``None`` where none is stated.

    The pattern alone would accept ``2026-99-99`` or ``2026-02-30``; the calendar is what
    decides, so a date that cannot exist is refused rather than read as an interval end.
    """
    _require(value is None or (type(value) is str and DATE.match(value) is not None), 'INVALID_RECORD')
    if value is not None:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise RegisterError('INVALID_RECORD') from None
    return value


def record(payload):
    """Validate one assumption record and return its canonical copy.

    The twelve documented keys, exactly; the id must name the record's own family
    (``threshold:<name>``, ``composer:<row>``, …); at least one source locator is required,
    because a proposition with no place it was read is not a register row. An interval with
    only one end is valid; both ends must be ordered.
    """
    try:
        value = json_copy(payload)
    except ValueError:
        raise RegisterError('INVALID_RECORD') from None
    _require(type(value) is dict and set(value) == FIELDS, 'INVALID_RECORD')
    _require(_nonblank(value['assumption_id']), 'INVALID_RECORD')
    _require(_nonblank(value['proposition']), 'INVALID_RECORD')
    _one_of(value['family'], FAMILIES)
    _one_of(value['layer'], LAYERS)
    _one_of(value['state'], STATES)
    _require(_nonblank(value['owner']), 'INVALID_RECORD')
    _require(_nonblank(value['falsifier']), 'INVALID_RECORD')
    prefix = value['family'] + ':'
    _require(value['assumption_id'].startswith(prefix), 'INVALID_RECORD')
    slug = value['assumption_id'][len(prefix):]
    _require(_nonblank(slug) and slug.split() == [slug], 'INVALID_RECORD')
    locators = value['source_locator']
    _require(type(locators) is list and bool(locators), 'INVALID_RECORD')
    for locator in locators:
        _locator(locator)
    start, end = _date(value['valid_from']), _date(value['valid_to'])
    _require(start is None or end is None or start <= end, 'INVALID_RECORD')
    code = value['affected_code']
    _require(type(code) is list and all(_nonblank(item) for item in code), 'INVALID_RECORD')
    revision = value['last_checked_revision']
    _require(revision is None or (type(revision) is str and REVISION.match(revision) is not None),
            'INVALID_RECORD')
    return value


def register(payload):
    """Validate the register envelope and every record in it, and return the canonical copy.

    The envelope declares the sources it was read from and how many rows each of them has;
    a declaration that disagrees with the records actually present is refused, so the count
    can never drift from the rows it describes. The audit, not this validator, compares the
    declaration with the sources themselves.
    """
    _require(type(payload) is dict and set(payload) == {'register_version', 'sources', 'assumptions'},
            'INVALID_REGISTER')
    _require(payload['register_version'] == REGISTER_VERSION, 'INVALID_REGISTER')
    sources = payload['sources']
    _require(type(sources) is list, 'INVALID_REGISTER')
    declared = {}
    for source in sources:
        _require(type(source) is dict and set(source) == {'family', 'path', 'rows'}, 'INVALID_REGISTER')
        _one_of(source['family'], COUNTED_FAMILIES, 'INVALID_REGISTER')
        _require(_nonblank(source['path']), 'INVALID_REGISTER')
        _require(source['path'] == SOURCE_PATHS[source['family']], 'INVALID_REGISTER')
        _require(type(source['rows']) is int and source['rows'] >= 0, 'INVALID_REGISTER')
        declared[source['family']] = source['rows']
    _require(set(declared) == set(COUNTED_FAMILIES), 'INVALID_REGISTER')
    assumptions = payload['assumptions']
    _require(type(assumptions) is list and bool(assumptions), 'INVALID_REGISTER')
    records = [record(item) for item in assumptions]
    for family in COUNTED_FAMILIES:
        _require(sum(1 for item in records if item['family'] == family) == declared[family],
                'INVALID_REGISTER')
    return json_copy({'register_version': REGISTER_VERSION, 'sources': json_copy(sources),
                      'assumptions': records})


def load_register(path=REGISTER_PATH, root=ROOT):
    """Read and validate the register file.

    The file is parsed by the repository's own parser, so a duplicate object key, a NaN or a
    malformed body is refused rather than silently accepted with the last value.
    """
    text = (Path(root) / path).read_text(encoding='utf-8')
    data, error = parse_json(text)
    _require(error is None, 'INVALID_JSON')
    return register(data)


def _threshold_rows(text):
    """The thresholds statement's rows as ``(name, value)`` pairs, in file order.

    The rows are read as text because the SQL is data, not importable code; the
    ``ref_regions`` statement above it has the same ``STRUCT`` shape and is excluded by
    matching the thresholds table itself. A statement that cannot be found, or that yields no
    rows, is refused: a reader that silently expects nothing would report no gap at all.
    """
    statement = THRESHOLD_TABLE.search(text)
    _require(statement is not None, 'INVALID_SOURCE')
    rows = THRESHOLD_ROW.findall(statement.group(1))
    _require(bool(rows), 'INVALID_SOURCE')
    return rows


def threshold_names(text):
    """The threshold names of one ``grid_ref.thresholds`` statement, in file order."""
    return [name for name, _ in _threshold_rows(text)]


def threshold_values(text):
    """The same statement's thresholds as ``name -> float``, so a value can be looked up.

    A reader that needs the number a threshold carries — to compare a proposition with the
    statement, or to evaluate the statement's own CASE ladder — reads it here rather than
    restating it. Two rows sharing a name are refused: the map could hold only one of them,
    and which one it held would be a silent choice.
    """
    rows = _threshold_rows(text)
    values = {name: float(value) for name, value in rows}
    _require(len(values) == len(rows), 'INVALID_SOURCE')
    return values


def price_bands(text):
    """The ``price_band`` CASE ladder of the price-label statement, in the order it tests.

    Each entry is ``(band, bound)``: ``bound`` is the name of the ``grid_ref.thresholds`` row
    the arm reads, the literal number the arm compares against, or ``None`` for the final
    ``ELSE`` arm. The ladder is sequential — the first arm a value falls below wins — so a
    value's band is the band of the first entry it is below. The statement, its ladder, its
    fall-through and every alias a bound reads are all required: text that cannot be read as
    the ladder is refused rather than read as empty or as fewer bands than it has.
    """
    case = PRICE_BAND_CASE.search(text)
    _require(case is not None, 'INVALID_SOURCE')
    _require(re.search(r'\bCASE\b', case.group(1), re.I) is None, 'INVALID_SOURCE')
    aliases = {alias: name for name, alias in PRICE_BAND_ALIAS.findall(text)}
    bands = []
    for operand, band in PRICE_BAND_ARM.findall(case.group(1)):
        if operand.startswith('t.'):
            alias = operand[len('t.'):]
            _require(alias in aliases, 'INVALID_SOURCE')
            bands.append((band, aliases[alias]))
        else:
            bands.append((band, float(operand)))
    _require(bool(bands), 'INVALID_SOURCE')
    fallback = PRICE_BAND_ELSE.search(case.group(1))
    _require(fallback is not None, 'INVALID_SOURCE')
    bands.append((fallback.group(1), None))
    return bands


def source_ids(root=ROOT):
    """The ids the two sources declare, in source order: the SQL rows and the frozen table.

    The composer rows are read from :data:`RULES` itself, so the register cannot drift from
    the composition table that is frozen: a row added there is a missing register row, and a
    row renamed there leaves the register's row unknown.
    """
    text = (Path(root) / SOURCE_PATHS['threshold']).read_text(encoding='utf-8')
    from src.judgment.bundle import RULES
    return {'threshold': ['threshold:' + name for name in threshold_names(text)],
            'composer': ['composer:' + row for row in RULES]}


def audit(payload, root=ROOT):
    """Compare the register with its sources and report every gap as a list of names.

    ``missing`` names a threshold or composer row the source declares and the register does
    not carry; ``unknown`` names a register row of those two families the source no longer
    declares; ``duplicates`` names an id carried more than once; ``dangling`` describes a
    citation that points at nothing — a path that does not exist, a line past the end of the
    file, or a quote that is not the text on the line it names — or an ``affected_code`` path
    that does not exist; ``unlabelled`` names a row of the two counted families whose layer is
    outside the four labels the acceptance names. ``counts`` carries the numbers the register
    states about itself: the rows per family, the layers, the rows with no owner recorded, the
    rows whose valid interval is unknown and the rows whose last check is unknown.

    The audit reads the sources themselves, never the register's own declaration of them.
    """
    expected = source_ids(root)
    seen = {}
    for item in payload['assumptions']:
        seen.setdefault(item['assumption_id'], []).append(item)
    present = set(seen)
    counts = {'records': len(payload['assumptions'])}
    missing, unknown, duplicates, dangling, unlabelled = [], [], [], [], []
    for family in COUNTED_FAMILIES:
        ids = expected[family]
        present_ids = [item['assumption_id'] for item in payload['assumptions'] if item['family'] == family]
        counts[family] = len(present_ids)
        missing.extend([item for item in ids if item not in present])
        declared = set(ids)
        unknown.extend(sorted({item for item in present_ids if item not in declared}))
    duplicates.extend(sorted(item for item, records in seen.items() if len(records) > 1))
    for layer in sorted(LAYERS):
        counts[layer] = sum(1 for item in payload['assumptions'] if item['layer'] == layer)
    counts['unowned'] = sum(1 for item in payload['assumptions'] if item['owner'] == 'unassigned')
    counts['unknown_interval'] = sum(1 for item in payload['assumptions']
                                     if item['valid_from'] is None and item['valid_to'] is None)
    counts['unchecked'] = sum(1 for item in payload['assumptions'] if item['last_checked_revision'] is None)
    for item in payload['assumptions']:
        if (item['family'] in COUNTED_FAMILIES and item['layer'] not in ACCEPTANCE_LAYERS):
            unlabelled.append(item['assumption_id'])
        for locator in item['source_locator']:
            dangling.extend(_dangling(locator, root))
        for path in item['affected_code']:
            if not (Path(root) / path).is_file():
                dangling.append(path + ' (missing file, affected_code)')
    return {'missing': missing, 'unknown': unknown, 'duplicates': duplicates,
            'dangling': sorted(dangling), 'unlabelled': sorted(unlabelled), 'counts': counts}


def _dangling(locator, root):
    """Every way one citation can point at nothing, as readable lines."""
    path, line, quote = locator['path'], locator['line'], locator['quote']
    target = Path(root) / path
    if not target.is_file():
        return [path + ' (missing file)']
    lines = target.read_text(encoding='utf-8').splitlines()
    if line > len(lines):
        return ['{}:{} (line past the end of {} lines)'.format(path, line, len(lines))]
    if quote not in lines[line - 1]:
        return ['{}:{} (quote is not on that line)'.format(path, line)]
    return []
