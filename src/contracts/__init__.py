"""Offline artifact contracts (schema v1) for Grid Nowcast.

Public interface::

    from src.contracts import (
        compute_content_digest,   # canonical SHA-256 over canonical JSON
        with_content_digest,      # stamp an artifact with its digest
        validate_artifact,        # structural validation -> ValidationResult
        validate_json,            # strict JSON text -> ValidationResult
        evaluate_eligibility,     # strict cutoff eligibility -> EligibilityResult
        ContractError, ValidationResult, EligibilityResult,
    )

Only :data:`DatasetSnapshot`, :data:`PredictionArtifact` and
:data:`ProvisionCandidate` schema version 1 are supported.  Validators check
structure and provenance only; they do not infer legal applicability, grant
access or promote models.  See :mod:`src.contracts.validators` for the exact
JSON field shapes and :mod:`src.contracts.jsonutil` for the canonical digest
rules.
"""
from .errors import (
    ALL_CODES,
    ContractError,
    EligibilityResult,
    ValidationResult,
)
from .jsonutil import (
    CanonicalizationError,
    SAFE_CANONICALIZATION_MESSAGE,
    canonical_bytes,
    canonical_dumps,
    compute_content_digest,
    parse_json,
    with_content_digest,
)
from .validators import (
    DATASET_SNAPSHOT,
    PREDICTION_ARTIFACT,
    PROVISION_CANDIDATE,
    SCHEMA_VERSION,
    SUPPORTED_ARTIFACT_TYPES,
    evaluate_eligibility,
    validate_artifact,
    validate_json,
)

__all__ = [
    "ALL_CODES",
    "CanonicalizationError",
    "ContractError",
    "DATASET_SNAPSHOT",
    "EligibilityResult",
    "PREDICTION_ARTIFACT",
    "PROVISION_CANDIDATE",
    "SCHEMA_VERSION",
    "SAFE_CANONICALIZATION_MESSAGE",
    "SUPPORTED_ARTIFACT_TYPES",
    "ValidationResult",
    "canonical_bytes",
    "canonical_dumps",
    "compute_content_digest",
    "evaluate_eligibility",
    "parse_json",
    "validate_artifact",
    "validate_json",
    "with_content_digest",
]
