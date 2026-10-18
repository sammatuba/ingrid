"""Ontology-constrained corpus extraction: proposed claims with whole-passage citations.

Three modules, in dependency order:

* :mod:`~.schema` — the ontology's claim shape: the response schema the Gemini request
  carries and the code that enforces the very same shape (types, relations, modalities,
  the exact citation, the stated valid time with its precision). Every claim enters as
  ``proposed``; the model has no field in which to say otherwise.
* :mod:`~.check` — the citation check. A claim whose quoted passage is not found
  verbatim, at its own offsets, in the source version's text layer is refused by code,
  and a citation that is not one of the compiled permitted passages is refused too.
* :mod:`~.run` — the System Two request (the compiled permitted passages as the only
  state, the instructions, the response schema), the call through the existing Gemini
  transport unchanged, the replay backend for stored responses, and the receipt.

Everything a run records is a proposal for an analyst to review: nothing in this package
changes an accepted assumption, an applicability assessment or any review-core record.
The task record with commands, evidence and the recorded gaps is
[docs/work/corpus/extraction.md](../../../../docs/work/corpus/extraction.md).
"""
__all__ = ["check", "run", "schema"]
