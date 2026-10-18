"""The document corpus: immutable acquisitions and the text layers read from them.

:mod:`~src.adapters.corpus.acquire` turns exact bytes plus supplied metadata into one
SourceVersion record with its fingerprint, its times and its licence, and projects a
compilable version into the review core's ``h0.v2`` records.
:mod:`~src.adapters.corpus.text` extracts a text layer with per-page offsets a locator can
cite, through the standard library and through ``pypdf`` when a caller has put it on
``sys.path``.

Both modules are additive and read-only: no network call, credential, model or clock. The
fetch tool that does use the network is ``scripts/corpus/fetch.py``, which runs by hand in
this seat and never in the test suite. See the [package README](README.md) for the record
shapes and how a document reaches a compiled context.
"""
__all__ = ["acquire", "text"]
