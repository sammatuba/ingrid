"""Structured, non-throwing errors for the M0 baseline evaluation harness.

The harness validates synthetic input/config, filters as-of history, runs
in-process baseline providers and scores aligned forecasts.  Every expected
failure is reported as a :class:`ModelingError` record with three controlled
fields:

``code``
    Stable machine-readable identifier.  Codes are part of the contract and do
    not change meaning.
``message``
    A fixed, safe sentence selected from :data:`MESSAGES`.  It never contains
    caller-supplied values, so private input cannot leak into logs.
``path``
    A JSON-pointer-like location built only from literal field names and array
    indexes.  It never embeds caller-controlled keys.

Public parse/evaluation entry points return errors rather than raising for
malformed input.  Exceptions are reserved for programmer error or for an
unexpected provider failure outside the declared port.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- stable error codes ---------------------------------------------------

INVALID_TYPE = "INVALID_TYPE"
MISSING_FIELD = "MISSING_FIELD"
INVALID_VALUE = "INVALID_VALUE"
BOOLEAN_AS_NUMBER = "BOOLEAN_AS_NUMBER"
NON_FINITE_NUMBER = "NON_FINITE_NUMBER"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
NAIVE_TIMESTAMP = "NAIVE_TIMESTAMP"
DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
UNORDERED_TIMESTAMPS = "UNORDERED_TIMESTAMPS"
MIXED_UNITS = "MIXED_UNITS"
MIXED_ENTITIES = "MIXED_ENTITIES"
UNKNOWN_AVAILABILITY = "UNKNOWN_AVAILABILITY"
LATE_AVAILABILITY = "LATE_AVAILABILITY"
ORIGIN_ORDER = "ORIGIN_ORDER"
INVALID_CONFIG = "INVALID_CONFIG"
NO_ELIGIBLE_HISTORY = "NO_ELIGIBLE_HISTORY"
MISSING_SEASON_SLOT = "MISSING_SEASON_SLOT"
MISSING_TRUTH = "MISSING_TRUTH"
PROVIDER_ERROR = "PROVIDER_ERROR"
MALFORMED_PREDICTION = "MALFORMED_PREDICTION"
NON_FINITE_PREDICTION = "NON_FINITE_PREDICTION"
WRONG_HORIZON = "WRONG_HORIZON"
REAL_INPUT_UNSUPPORTED = "REAL_INPUT_UNSUPPORTED"
OVERFLOW = "OVERFLOW"
INVALID_PROVIDER = "INVALID_PROVIDER"
INTERNAL_ERROR = "INTERNAL_ERROR"

#: Fixed safe message per code.  Never parameterized with caller input.
MESSAGES = {
    INVALID_TYPE: "value has the wrong type",
    MISSING_FIELD: "required field is missing",
    INVALID_VALUE: "value is not allowed",
    BOOLEAN_AS_NUMBER: "a boolean is not accepted as a number",
    NON_FINITE_NUMBER: "non-finite numbers are not allowed",
    INVALID_TIMESTAMP: "timestamp is not a valid offset-bearing ISO 8601 value",
    NAIVE_TIMESTAMP: "timestamp is missing a UTC offset",
    DUPLICATE_TIMESTAMP: "timestamps must be unique instants",
    UNORDERED_TIMESTAMPS: "timestamps must be strictly increasing",
    MIXED_UNITS: "one unit is allowed per evaluation",
    MIXED_ENTITIES: "one entity is allowed per evaluation",
    UNKNOWN_AVAILABILITY: "observation availability is unknown",
    LATE_AVAILABILITY: "observation was not available at the forecast origin",
    ORIGIN_ORDER: "forecast origins must be strictly increasing",
    INVALID_CONFIG: "configuration is not valid",
    NO_ELIGIBLE_HISTORY: "no eligible history exists at or before the origin",
    MISSING_SEASON_SLOT: "seasonal naive requires an eligible value at every season slot",
    MISSING_TRUTH: "evaluation truth does not cover the full horizon",
    PROVIDER_ERROR: "the prediction provider reported a failure",
    MALFORMED_PREDICTION: "provider output is not a valid horizon-aligned prediction",
    NON_FINITE_PREDICTION: "provider output contains non-finite values",
    WRONG_HORIZON: "provider output does not match the configured horizon",
    REAL_INPUT_UNSUPPORTED: "only labeled synthetic input is supported",
    OVERFLOW: "metric computation overflowed the finite float range",
    INVALID_PROVIDER: "prediction provider does not implement the bounded port",
    INTERNAL_ERROR: "evaluation could not be completed",
}

#: Every code emitted by the M0 harness.
ALL_CODES = frozenset(MESSAGES)


@dataclass(frozen=True)
class ModelingError:
    """One structured, non-throwing modeling failure or exclusion."""

    code: str
    message: str
    path: str = "$"

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "path": self.path}


def issue(code: str, path: str = "$") -> ModelingError:
    """Build an error record using the code's fixed message."""
    return ModelingError(code=code, message=MESSAGES[code], path=path)


class ModelingValidationError(ValueError):
    """Raised only by direct record construction with a malformed shape.

    Public parse functions convert the same problem into a structured
    :class:`ModelingError` instead of raising.
    """

    def __init__(self, error: ModelingError) -> None:
        self.error = error
        super().__init__(error.message)


__all__ = [
    "ALL_CODES",
    "MESSAGES",
    "ModelingError",
    "ModelingValidationError",
    "issue",
    "INVALID_TYPE",
    "MISSING_FIELD",
    "INVALID_VALUE",
    "BOOLEAN_AS_NUMBER",
    "NON_FINITE_NUMBER",
    "INVALID_TIMESTAMP",
    "NAIVE_TIMESTAMP",
    "DUPLICATE_TIMESTAMP",
    "UNORDERED_TIMESTAMPS",
    "MIXED_UNITS",
    "MIXED_ENTITIES",
    "UNKNOWN_AVAILABILITY",
    "LATE_AVAILABILITY",
    "ORIGIN_ORDER",
    "INVALID_CONFIG",
    "NO_ELIGIBLE_HISTORY",
    "MISSING_SEASON_SLOT",
    "MISSING_TRUTH",
    "PROVIDER_ERROR",
    "MALFORMED_PREDICTION",
    "NON_FINITE_PREDICTION",
    "WRONG_HORIZON",
    "REAL_INPUT_UNSUPPORTED",
    "OVERFLOW",
    "INVALID_PROVIDER",
    "INTERNAL_ERROR",
]
