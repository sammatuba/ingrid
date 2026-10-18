"""Structured validation errors for the offline artifact contracts (schema v1).

Every validator returns errors as :class:`ContractError` records instead of
raising.  A record has three controlled fields:

``code``
    Stable machine-readable identifier (see the ``*`` constants below).  Codes
    are part of the contract and never change meaning for a given schema
    version.
``message``
    A fixed, safe human-readable sentence selected from :data:`MESSAGES`.  It
    never contains caller-supplied values, so it cannot leak private input or
    be used for log injection.
``path``
    A JSON-pointer-like location built only from literal schema field names and
    array indexes (``$``, ``$.payload.units``, ``$.source_refs[0]``).  It never
    embeds caller-controlled object keys or class-score labels.

Validators never raise on malformed input; they convert every failure into one
or more records.  Exceptions are reserved for programmer error in the library
itself.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- stable error codes ---------------------------------------------------

MALFORMED_JSON = "MALFORMED_JSON"
DUPLICATE_KEY = "DUPLICATE_KEY"
MISSING_FIELD = "MISSING_FIELD"
INVALID_TYPE = "INVALID_TYPE"
INVALID_VALUE = "INVALID_VALUE"
UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
UNSUPPORTED_ARTIFACT_TYPE = "UNSUPPORTED_ARTIFACT_TYPE"
BOOLEAN_AS_NUMBER = "BOOLEAN_AS_NUMBER"
NON_FINITE_NUMBER = "NON_FINITE_NUMBER"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
NAIVE_TIMESTAMP = "NAIVE_TIMESTAMP"
INVALID_DATE = "INVALID_DATE"
INVERTED_INTERVAL = "INVERTED_INTERVAL"
TEMPORAL_ORDER = "TEMPORAL_ORDER"
INVALID_DIGEST = "INVALID_DIGEST"
DIGEST_MISMATCH = "DIGEST_MISMATCH"
LATEST_POINTER_FORBIDDEN = "LATEST_POINTER_FORBIDDEN"
INVALID_REFERENCE = "INVALID_REFERENCE"
UNRESOLVED_CITATION = "UNRESOLVED_CITATION"
UNKNOWN_AVAILABILITY = "UNKNOWN_AVAILABILITY"
LATE_AVAILABILITY = "LATE_AVAILABILITY"
INTERNAL_ERROR = "INTERNAL_ERROR"

#: Fixed safe message per code.  Never parameterized with caller input.
MESSAGES = {
    MALFORMED_JSON: "input is not valid JSON",
    DUPLICATE_KEY: "JSON object contains a duplicate key",
    MISSING_FIELD: "required field is missing",
    INVALID_TYPE: "value has the wrong type",
    INVALID_VALUE: "value is not allowed",
    UNSUPPORTED_SCHEMA_VERSION: "artifact schema version is not supported",
    UNSUPPORTED_ARTIFACT_TYPE: "artifact type is not supported",
    BOOLEAN_AS_NUMBER: "a boolean is not accepted as a number",
    NON_FINITE_NUMBER: "non-finite numbers are not allowed",
    INVALID_TIMESTAMP: "timestamp is not a valid offset-bearing ISO 8601 value",
    NAIVE_TIMESTAMP: "timestamp is missing a UTC offset",
    INVALID_DATE: "date is not a valid YYYY-MM-DD value",
    INVERTED_INTERVAL: "start must be before end",
    TEMPORAL_ORDER: "temporal fields are in an invalid order",
    INVALID_DIGEST: "digest is not a lowercase 64-character SHA-256 hex value",
    DIGEST_MISMATCH: "content_digest does not match the canonical artifact content",
    LATEST_POINTER_FORBIDDEN: "revision references must be exact, not latest pointers",
    INVALID_REFERENCE: "artifact reference is not exact",
    UNRESOLVED_CITATION: "passage citation does not bind to an envelope source reference",
    UNKNOWN_AVAILABILITY: "source availability is unknown",
    LATE_AVAILABILITY: "source availability is later than the applicable cutoff",
    INTERNAL_ERROR: "artifact content could not be canonicalized",
}

#: Every code emitted by v1 validators.
ALL_CODES = frozenset(MESSAGES)


@dataclass(frozen=True)
class ContractError:
    """One structured, non-throwing contract failure."""

    code: str
    message: str
    path: str = "$"

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "path": self.path}


def issue(code: str, path: str = "$") -> ContractError:
    """Build an error record with the code's fixed message."""
    return ContractError(code=code, message=MESSAGES[code], path=path)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of structural validation; ``ok`` is true when no errors exist."""

    errors: tuple[ContractError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:  # allow ``if result:``
        return self.ok

    def codes(self) -> tuple[str, ...]:
        return tuple(error.code for error in self.errors)


@dataclass(frozen=True)
class EligibilityResult:
    """Outcome of strict eligibility.

    ``structural_ok`` states whether the artifact passed structural validation.
    ``eligible`` is true only when the artifact is structurally valid and every
    source availability is known and not later than the applicable cutoff(s).
    ``errors`` carries either the structural failures or the eligibility
    exclusions.
    """

    structural_ok: bool
    eligible: bool
    errors: tuple[ContractError, ...] = ()

    def codes(self) -> tuple[str, ...]:
        return tuple(error.code for error in self.errors)
