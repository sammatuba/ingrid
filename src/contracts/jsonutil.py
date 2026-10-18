"""Canonical JSON and content digests for the offline artifact contracts.

Canonical form (schema v1)
==========================

``content_digest`` is the lowercase SHA-256 hex digest of the UTF-8 encoding of
the canonical JSON of the artifact with **only the top-level** ``content_digest``
key removed.  Nested digests (for example inside ``source_refs``) are ordinary
content and remain part of the hashed bytes.

Canonical JSON serialization is fixed as:

* object keys sorted lexicographically (*not* insertion order);
* compact separators ``","`` and ``":"`` with no insignificant whitespace;
* UTF-8 output;
* ``ensure_ascii=False``: Unicode text is embedded as literal UTF-8 rather than
  ``\\uXXXX`` escapes, so canonically equal strings hash identically regardless
  of their input escaping;
* ``allow_nan=False``: ``NaN``/``Infinity`` are rejected, never serialized.

JSON parsing
============

The standard library's :func:`json.loads` accepts ``NaN``/``Infinity`` and
silently keeps the last of duplicate object keys.  Both behaviours would let
non-finite or ambiguous content satisfy a digest check, so
:func:`parse_json` rejects them and reports a structured result instead of
raising.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

from .errors import (
    ContractError,
    DUPLICATE_KEY,
    INVALID_TYPE,
    MALFORMED_JSON,
    NON_FINITE_NUMBER,
    issue,
)


#: Fixed, caller-independent message for every canonicalization failure.  Callers
#: surface this instead of the underlying exception text so raw input and
#: interpreter details never reach messages.
SAFE_CANONICALIZATION_MESSAGE = "artifact content could not be canonicalized"


class CanonicalizationError(ValueError):
    """Raised when a value cannot be serialized to canonical JSON.

    Every expected serialization failure -- a non-JSON Python type, a
    non-finite float, a circular reference, text that is not valid UTF-8 (for
    example a lone surrogate), or excessive nesting -- is wrapped with the same
    fixed :data:`SAFE_CANONICALIZATION_MESSAGE`.  Programming errors that are
    not serialization failures are left to propagate.
    """


class _DuplicateKey(ValueError):
    """Internal marker raised by the object-pairs hook."""


class _NonFinite(ValueError):
    """Internal marker raised by the constant parser."""


def _reject_constant(_name: str) -> object:
    raise _NonFinite()


def _reject_duplicates(pairs):
    seen = set()
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey()
        seen.add(key)
    return dict(pairs)


def canonical_dumps(value) -> str:
    """Serialize ``value`` to canonical JSON or raise :class:`CanonicalizationError`."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except RecursionError as exc:  # excessively nested value
        raise CanonicalizationError(SAFE_CANONICALIZATION_MESSAGE) from exc
    except (TypeError, ValueError) as exc:  # non-finite floats, non-string keys, cycles, ...
        raise CanonicalizationError(SAFE_CANONICALIZATION_MESSAGE) from exc


def canonical_bytes(value) -> bytes:
    """Return the UTF-8 bytes of the canonical JSON form of ``value``."""
    text = canonical_dumps(value)
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:  # e.g. a lone surrogate in a string
        raise CanonicalizationError(SAFE_CANONICALIZATION_MESSAGE) from exc


def compute_content_digest(artifact) -> str:
    """Return the canonical ``content_digest`` for a mapping artifact."""
    if not isinstance(artifact, Mapping):
        raise CanonicalizationError(SAFE_CANONICALIZATION_MESSAGE)
    clone = {key: value for key, value in artifact.items() if key != "content_digest"}
    return hashlib.sha256(canonical_bytes(clone)).hexdigest()


def with_content_digest(artifact: Mapping) -> dict:
    """Return a shallow copy of ``artifact`` stamped with its canonical digest.

    Every value is shallow-copied by reference; this does not deep-copy nested
    structures.
    """
    if not isinstance(artifact, Mapping):
        raise CanonicalizationError(SAFE_CANONICALIZATION_MESSAGE)
    stamped = dict(artifact)
    stamped["content_digest"] = compute_content_digest(artifact)
    return stamped


def parse_json(text) -> tuple[object | None, ContractError | None]:
    """Parse strict JSON text.

    Returns ``(value, None)`` on success or ``(None, error)`` on failure.  The
    returned error is a structured :class:`ContractError` with a safe message.
    """
    if not isinstance(text, str):
        return None, issue(MALFORMED_JSON, "$")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey:
        return None, issue(DUPLICATE_KEY, "$")
    except _NonFinite:
        return None, issue(NON_FINITE_NUMBER, "$")
    except (ValueError, RecursionError):
        return None, issue(MALFORMED_JSON, "$")
    return value, None
