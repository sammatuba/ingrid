"""The citation check: code refuses a claim the supplied passage and its version's layer do not confirm.

A claim's citation is four things at once — the source id, the immutable source version, the
character offsets and the quoted text — and all four have to be true of one and the same
*source version*: the version whose text layer the run compiled the passage from. The check
is therefore bound to the compiled permitted passage set: a citation is confirmed only when
it **is** one of the passages the model was given — the same source, the same version, the
same offsets and the same quote, character for character — and that version's text layer
shows the quote at exactly those offsets. A model that quotes a sentence but counts the offsets
wrong, writes a plausible sentence the source never contained, tidies a quote by one character,
or names a span the run never supplied produces a claim this module refuses before anything is
recorded.
A layer of some *other* version confirming the text changes nothing: the model was never
supplied it. ``refuse`` never searches a different source, never repairs the offsets from the
quote and never accepts a near match.

The layers are keyed by immutable version identity (:func:`version_key`), so a layer is bound
to the version whose bytes it was extracted from and two versions of one source can never
overwrite each other. Offsets count Unicode code points of the layer's decoded text, the unit
:mod:`src.adapters.corpus.text` and the review core's ``Passage`` records both use.

Refusals, each with its own code:

* ``MALFORMED_CITATION`` — the citation is not the five-field object the schema fixes, or it
  names no source version.
* ``UNKNOWN_SOURCE`` — the run compiled no passage of the cited source and holds no text
  layer for it (or holds compiled passages of it but no layer at all).
* ``LAYER_NOT_EXTRACTED`` — the layer that would confirm the quote says it carries no text.
* ``CITATION_OUT_OF_BOUNDS`` — the offsets are not a half-open span inside any text layer the
  run holds for that source.
* ``CITATION_NOT_VERBATIM`` — the quote is not the text between its own offsets. The detail
  distinguishes the two ways that happens, because they are different mistakes: a quote that
  *does* occur elsewhere in the layer (the offsets are wrong) and a quote that occurs nowhere
  (the text was not in this source at all).
* ``CITATION_NOT_A_PERMITTED_PASSAGE`` — the citation is not one of the compiled permitted
  passages the model was given: a different quote at a supplied passage's own offsets, or a
  span the run never compiled — verbatim in a layer or not.
* ``CITATION_VERSION_MISMATCH`` — the cited text and offsets *are* a supplied passage's,
  but the citation names another immutable revision of that source: the run compiled that
  text as a different version, and the cited revision was never supplied. Identical
  passages across revisions stay distinct citations this way; the cited revision is never
  silently replaced by the first version that happens to match.

A refused claim is never written as a claim: :func:`check_claims` returns the kept claims
and the refusals side by side, and a run records both. Nothing here changes a claim's
review state; every claim stays ``proposed``.
"""
from __future__ import annotations

from .schema import CITATION_KEYS, ExtractionRefused, PROPOSED

__all__ = ["check_claim", "check_claims", "check_citation", "occurrences", "version_key"]


def version_key(source_id, source_version):
    """The identity a text layer, a compiled passage and a citation meet on.

    One immutable source version: the corpus ``source_id`` and the version ordinal the
    acquisition contract assigns, joined by ``@``. A run's layers and its provenance map are
    keyed by this, so two versions of one source can never overwrite each other and a layer
    can always be matched back to the version whose bytes it came from.
    """
    return "%s@%s" % (source_id, source_version)


def _refuse(code, detail):
    raise ExtractionRefused(code, detail)


def _extracted(layer, key):
    """The layer, or the refusal that it carries no text to confirm a quote against."""
    if getattr(layer, "status", None) != "extracted":
        _refuse("LAYER_NOT_EXTRACTED",
                "the text layer of %s is not extracted (%s), so no quote can be confirmed "
                "against it" % (key, getattr(layer, "reason", "no reason recorded")))
    return layer


def _layers_for(layers, source_id):
    """The text layers this run holds for one source, by version; never another source's."""
    if type(layers) is not dict:
        return {}
    prefix = source_id + "@"
    return {key[len(prefix):]: layer for key, layer in layers.items()
            if type(key) is str and key.startswith(prefix)}


def occurrences(text, quote):
    """How many times ``quote`` occurs in ``text``, as the text's own substring count."""
    count, start = 0, 0
    while True:
        found = text.find(quote, start)
        if found < 0:
            return count
        count += 1
        start = found + len(quote)


def _confirm(layer, source_id, version, start, end, quote):
    """The layer of this one version must show the quote at exactly its own offsets."""
    if not 0 <= start < end <= len(layer.text):
        _refuse("CITATION_OUT_OF_BOUNDS",
                "the citation's span %r..%r is not inside %s version %s's text layer "
                "(%d characters)" % (start, end, source_id, version, len(layer.text)))
    if layer.text[start:end] != quote:
        found = occurrences(layer.text, quote)
        if found:
            first = layer.text.find(quote)
            _refuse("CITATION_NOT_VERBATIM",
                    "the quote is not the text between its own offsets in %s version %s; the "
                    "same text occurs %d time(s) in the layer, first at %d..%d"
                    % (source_id, version, found, first, first + len(quote)))
        _refuse("CITATION_NOT_VERBATIM",
                "the quoted text does not occur verbatim anywhere in %s version %s's text "
                "layer" % (source_id, version))
    return layer


def check_citation(citation, layers, *, passages):
    """One citation against the compiled permitted passages and the versions' text layers.

    Returns the citation unchanged when it *is* one of the supplied passages — on source id,
    version, offsets and quote at once — and that version's own text layer confirms the quote
    at those offsets; raises :class:`~.schema.ExtractionRefused` otherwise. ``passages`` is
    the compiled permitted passage set the model was given (each entry a mapping with
    ``source_id``, ``source_version``, ``start``, ``end`` and ``quote``), and ``layers`` is
    keyed by :func:`version_key`, so the layer a citation is confirmed against is always the
    layer of the version the passage names. The citation's own revision is part of the match,
    never chosen for it: a citation that names one revision while the run supplied the same
    text as another is refused ``CITATION_VERSION_MISMATCH``, so identical passages in two
    revisions are two citations and neither is confirmed by the other's passage.
    """
    if type(citation) is not dict or set(citation) != set(CITATION_KEYS):
        _refuse("MALFORMED_CITATION", "a citation must be an object with exactly %s"
                % list(CITATION_KEYS))
    source_id = citation["source_id"]
    version = citation["source_version"]
    start, end, quote = citation["start"], citation["end"], citation["quote"]
    if type(start) is not int or type(end) is not int or type(quote) is not str:
        _refuse("MALFORMED_CITATION", "a citation's offsets are integers and its quote a string")
    if type(version) is not str or not version.strip():
        _refuse("MALFORMED_CITATION", "a citation names its immutable source version")
    supplied = [passage for passage in (passages or [])
                if type(passage) is dict and passage.get("source_id") == source_id
                and all(key in passage for key in ("source_version", "start", "end", "quote"))]
    exact = [passage for passage in supplied
             if (passage["source_version"], passage["start"], passage["end"], passage["quote"])
             == (version, start, end, quote)]
    if exact:
        key = version_key(source_id, version)
        layer = layers.get(key) if type(layers) is dict else None
        if layer is None:
            _refuse("UNKNOWN_SOURCE",
                    "the citation is the compiled passage %s %d..%d of version %s, and this run "
                    "holds no text layer for that version" % (source_id, start, end, version))
        _confirm(_extracted(layer, key), source_id, version, start, end, quote)
        return citation
    # The citation is not one of the supplied passages. Refuse with the most precise cause.
    known = _layers_for(layers, source_id)
    held = {held_version: layer for held_version, layer in known.items()
            if getattr(layer, "status", None) == "extracted"}
    if not supplied and not known:
        _refuse("UNKNOWN_SOURCE",
                "the citation names source %r and this run compiled no passage of it and holds "
                "no text layer for it" % (source_id,))
    same_span = [passage for passage in supplied
                 if (passage["start"], passage["end"]) == (start, end)]
    if same_span:
        supplied_versions = sorted({passage["source_version"] for passage in same_span})
        if version in supplied_versions:
            _refuse("CITATION_NOT_A_PERMITTED_PASSAGE",
                    "the citation %s version %s %d..%d is not the compiled permitted passage "
                    "this run supplied: the run supplied a different quote at those offsets of "
                    "that version, and the cited quote is not the passage the model was given"
                    % (source_id, version, start, end))
        if any(passage["quote"] == quote for passage in same_span):
            _refuse("CITATION_VERSION_MISMATCH",
                    "the cited text at %s %d..%d is supplied as version(s) %s, and the citation "
                    "names version %s: the run did not compile that revision, and identical "
                    "text in another revision is another citation"
                    % (source_id, start, end, ", ".join(supplied_versions), version))
        _refuse("CITATION_NOT_A_PERMITTED_PASSAGE",
                "the citation %s version %s %d..%d is not the compiled permitted passage this "
                "run supplied: the run supplied version(s) %s at those offsets with a different "
                "quote, and the cited quote is not the passage the model was given"
                % (source_id, version, start, end, ", ".join(supplied_versions)))
    if not held:
        for held_version, layer in sorted(known.items()):
            _extracted(layer, version_key(source_id, held_version))  # raises with the reason
        _refuse("UNKNOWN_SOURCE",
                "the citation names source %r and this run holds no text layer for it, so its "
                "compiled passages cannot be confirmed" % (source_id,))
    if not any(0 <= start < end <= len(layer.text) for layer in held.values()):
        first = sorted(held)[0]
        _refuse("CITATION_OUT_OF_BOUNDS",
                "the citation's span %r..%r is not inside any text layer this run holds for %s "
                "(version %s carries %d characters)"
                % (start, end, source_id, first, len(held[first].text)))
    for held_version in sorted(held):
        if held[held_version].text[start:end] == quote:
            _refuse("CITATION_NOT_A_PERMITTED_PASSAGE",
                    "the cited text is verbatim in %s version %s at %d..%d, but it is not one "
                    "of the compiled permitted passages this run supplied"
                    % (source_id, held_version, start, end))
    held_version = sorted(held)[0]
    found = occurrences(held[held_version].text, quote)
    if found:
        first = held[held_version].text.find(quote)
        _refuse("CITATION_NOT_VERBATIM",
                "the quote is not the text between its own offsets in %s; the same text occurs "
                "%d time(s) in version %s's layer, first at %d..%d"
                % (source_id, found, held_version, first, first + len(quote)))
    _refuse("CITATION_NOT_VERBATIM",
            "the quoted text does not occur verbatim anywhere in the text layers this run "
            "holds for %s (version(s) %s)" % (source_id, ", ".join(sorted(held))))


def check_claim(claim, layers, *, passages):
    """One claim through :func:`check_citation`; the claim is returned or refused whole."""
    if type(claim) is not dict or "citation" not in claim:
        _refuse("INVALID_CLAIM", "a claim carries a citation")
    if claim.get("review_state") != PROPOSED:
        _refuse("NOT_PROPOSED",
                "a claim enters as %r; nothing here accepts a claim or moves a review state"
                % PROPOSED)
    check_citation(claim["citation"], layers, passages=passages)
    return claim


def check_claims(claims, layers, *, passages):
    """``(kept, refusals)``: every claim checked; a refused one is never among the kept.

    Each refusal carries the claim id when one is present, the stable code and the
    detail, so a run records what was refused and why without writing it as a claim.
    """
    kept, refusals = [], []
    for claim in claims:
        try:
            kept.append(check_claim(claim, layers, passages=passages))
        except ExtractionRefused as exc:
            refusals.append({"claim_id": claim.get("claim_id"), "code": exc.code,
                             "detail": exc.detail,
                             "citation": claim.get("citation")})
    return kept, refusals
