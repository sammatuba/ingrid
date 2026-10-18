"""The claim store: the corpus records as typed table rows, and the cutoff rule.

:mod:`~src.adapters.corpus.store.records` holds one shape per table and derives the half-open
availability interval every cutoff query compares against; it turns the records the corpus
adapter and the regulatory lineage produce into rows, and rows into newline JSON for
``scripts/corpus/bq/load.py``.
:mod:`~src.adapters.corpus.store.local` answers the same queries offline, in memory and in
sqlite, so the cutoff rule is proved by tests without a cloud call.
:mod:`~src.adapters.corpus.store.sqlcheck` is the standard-library checker the SQL files are
held to.

Nothing here opens a socket, reads a file, consults a clock or calls a model. Retrieval is a
filter before the compiler, never an authority: a passage returned at a cutoff is a candidate
context, not an accepted fact. See ``docs/work/corpus/store.md`` for the tables, the exact
``bq`` commands and the cost note.
"""
__all__ = ["local", "records", "sqlcheck"]
