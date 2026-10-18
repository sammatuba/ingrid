"""The store's columns, one list per table: the single source the DDL is held against.

`scripts/corpus/bq/ddl.sql` is written out in full — BigQuery DDL has no way to share a column
block — so the two are compared instead of trusted: `tests/test_corpus_store.py` parses the
DDL, reads the columns each ``CREATE TABLE`` declares, and fails if a table here and the DDL
disagree on a name, an order or a type. The sqlite backend creates its tables from this list,
so an offline test writes exactly the rows the cloud table is typed for.

Types are BigQuery's. ``FLOAT64_ARRAY`` is ``ARRAY<FLOAT64>``: the passage embedding. Nothing
here names a partition, a cluster or an index; those live in the DDL where the physical
choices belong.
"""
from __future__ import annotations

#: The shared time block, in the column order every table uses (see ``records``).
TIME_BLOCK = (
    ("event_time_start", "TIMESTAMP"), ("event_time_end", "TIMESTAMP"),
    ("event_value", "STRING"), ("event_end_value", "STRING"),
    ("event_precision", "STRING"), ("event_end_precision", "STRING"),
    ("event_unknown_reason", "STRING"),
    ("published_on", "DATE"), ("published_at", "TIMESTAMP"), ("published_value", "STRING"),
    ("published_precision", "STRING"), ("published_unknown_reason", "STRING"),
    ("availability_from", "TIMESTAMP"), ("availability_until", "TIMESTAMP"),
    ("availability_value", "STRING"), ("availability_precision", "STRING"),
    ("availability_basis", "STRING"), ("availability_unknown_reason", "STRING"),
    ("recorded_at", "TIMESTAMP"), ("reviewed_at", "TIMESTAMP"), ("review_state", "STRING"),
)

_PROVENANCE = (("synthetic", "BOOL"), ("permission_ref", "STRING"))

COLUMNS = {
    "entities": (
        ("entity_id", "STRING"), ("entity_type", "STRING"), ("label", "STRING"),
        ("canonical_ref", "STRING"), ("issuer", "STRING"),
        ("evidence_passage_id", "STRING"), ("notes", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
    "source_versions": (
        ("source_id", "STRING"), ("source_version", "STRING"), ("lineage_id", "STRING"),
        ("issuer", "STRING"), ("locator", "STRING"), ("content_type", "STRING"),
        ("content_type_source", "STRING"), ("document_length", "INT64"),
        ("document_sha256", "STRING"), ("licence_ref", "STRING"),
        ("access_policy_ref", "STRING"), ("state", "STRING"), ("corpus_record", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
    "passages": (
        ("passage_id", "STRING"), ("source_id", "STRING"), ("source_version", "STRING"),
        ("issuer", "STRING"), ("page", "INT64"), ("page_start", "INT64"), ("page_end", "INT64"),
        ("start_offset", "INT64"), ("end_offset", "INT64"), ("quote", "STRING"),
        ("quote_digest", "STRING"), ("embedding", "FLOAT64_ARRAY"),
        ("embedding_model", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
    "claims": (
        ("claim_id", "STRING"), ("claim_revision", "INT64"), ("subject_ref", "STRING"),
        ("subject_type", "STRING"), ("predicate", "STRING"), ("object_ref", "STRING"),
        ("object_type", "STRING"), ("object_value", "STRING"), ("object_unit", "STRING"),
        ("object_quantity_kind", "STRING"), ("modality", "STRING"), ("attributed_to", "STRING"),
        ("source_id", "STRING"), ("source_version", "STRING"), ("passage_id", "STRING"),
        ("locator_start", "INT64"), ("locator_end", "INT64"), ("quote_digest", "STRING"),
        ("extraction_method", "STRING"), ("extraction_version", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
    "relations": (
        ("relation_id", "STRING"), ("relation_kind", "STRING"), ("from_ref", "STRING"),
        ("from_type", "STRING"), ("to_ref", "STRING"), ("to_type", "STRING"),
        ("claim_ref", "STRING"), ("passage_id", "STRING"), ("source_id", "STRING"),
        ("source_version", "STRING"), ("notes", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
    "rule_versions": (
        ("version_id", "STRING"), ("clause_label", "STRING"), ("family", "STRING"),
        ("text", "STRING"), ("source_id", "STRING"), ("source_revision", "STRING"),
        ("source_digest", "STRING"), ("locator_start", "INT64"), ("locator_end", "INT64"),
        ("replaces", "STRING"), ("amendment_ref", "STRING"),
    ) + TIME_BLOCK + _PROVENANCE,
}

#: The column that decides every cutoff question, and its partner for the reason.
CUTOFF_COLUMN = "availability_until"

_SQLITE_TYPES = {"STRING": "TEXT", "INT64": "INTEGER", "BOOL": "INTEGER", "DATE": "TEXT",
                 "TIMESTAMP": "TEXT", "FLOAT64_ARRAY": "TEXT"}


def names(table):
    """Every column name of one table, in order."""
    return tuple(name for name, _ in COLUMNS[table])


def sqlite_type(bigquery_type):
    """The sqlite storage class a BigQuery type lands in; an array is stored as JSON text."""
    return _SQLITE_TYPES[bigquery_type]


def sqlite_create(table):
    """The sqlite ``CREATE TABLE`` statement for one table, from this module's columns."""
    body = ", ".join("%s %s" % (name, sqlite_type(kind)) for name, kind in COLUMNS[table])
    return "CREATE TABLE IF NOT EXISTS %s (%s)" % (table, body)


def sqlite_columns(table):
    return names(table)
