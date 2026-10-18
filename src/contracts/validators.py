"""Offline, dependency-free validators for the v1 artifact contracts.

Scope (schema version 1)
========================

This module implements exactly three artifact types:

* ``dataset_snapshot`` (:class:`DatasetSnapshot`)
* ``prediction_artifact`` (:class:`PredictionArtifact`)
* ``provision_candidate`` (:class:`ProvisionCandidate`)

Anything else, and any ``schema_version`` other than ``1``, is reported as
``UNSUPPORTED_SCHEMA_VERSION`` / ``UNSUPPORTED_ARTIFACT_TYPE``.  The validators
check structure and provenance; they do **not** assess model skill, legal
applicability, approval or access.  A policy reference never grants access and
a declared prediction status never promotes a model.

Field shapes
============

Common envelope (required on every artifact)::

    {
      "schema_version": 1,
      "artifact_id": str,                     # opaque stable identity
      "artifact_type": "dataset_snapshot" | "prediction_artifact" | "provision_candidate",
      "revision_id": str,                     # immutable revision
      "producer": {"name": str, "version": str},
      "created_at": offset-bearing ISO-8601 str,   # may follow information_cutoff
      "information_cutoff": offset-bearing ISO-8601 str,
      "access_policy_ref": str,               # reference only, grants nothing
      "scope": {"kind": "case" | "dataset" | "task", "id": str},
      "source_refs": [SourceRef, ...],        # non-empty
      "payload": {...},                       # shape by artifact_type, below
      "synthetic": bool,
      "content_digest": lowercase sha-256 hex # canonical digest of the rest
    }

Timestamps must carry a UTC offset (``Z`` or ``+hh:mm``); naive values fail.
Intervals are start-inclusive / end-exclusive, so ``start`` must be strictly
before ``end``; equal endpoints fail as ``INVERTED_INTERVAL``.  ``content_digest``
is the SHA-256 of canonical JSON with only the top-level ``content_digest``
removed (see :mod:`src.contracts.jsonutil`).

SourceRef::

    {
      "source_id": str,
      "source_version": str,                  # immutable version, not "latest"
      "content_digest": lowercase sha-256 hex,
      "locator": {"kind": "exact", "path": str, "start": int?, "end": int?}
                 | {"kind": "query", "query": str,
                    "start": offset timestamp, "end": offset timestamp},
      "availability": {"known_at": offset timestamp | null,
                       "basis": str?,          # required when known_at is known
                       "unknown_reason": str?} # required when known_at is null
    }

DatasetSnapshot payload::

    {
      "window": {"start": timestamp, "end": timestamp},
      "query_digest": sha-256 hex,
      "entity_schema": {"entity_type": str, "id_field": str?},
      "quantity_schema": {"quantity_kind": str, "units": str, "currency": str?},
      "status": "raw" | "final",
      "missingness": {"missing_count": int, "total_count": int, "basis": str},
      "first_availability_basis": str,
      "target_features": [{"name": str, "role": "target" | "feature",
                           "units": str, "quantity_kind": str?}, ...]
    }

PredictionArtifact payload::

    {
      "model_spec_ref": ArtifactRef,
      "forecast_origin": timestamp,
      "input_cutoff": timestamp,              # <= forecast_origin and <= information_cutoff
      "entity": {"entity_type": str, "entity_id": str, "region": str},
      "valid_interval": {"start": timestamp, "end": timestamp},
      "horizon": {"value": positive number, "unit": str},
      "units": str,
      "quantity_kind": str,
      "outcome": {"kind": "point", "value": finite number}
                 | {"kind": "class_scores", "scores": {label: finite number}},
      "quantiles": [{"level": 0<number<1, "value": finite number}, ...]?,  # optional
      "input_snapshot_ref": ArtifactRef,
      "evaluation_report_ref": ArtifactRef | null,
                               # exact ref, or null only for a not-yet-evaluated
                               # experimental prediction; never inferred
      "evaluation_report_unknown_reason": str?,  # required when ref is null
      "promotion_decision_ref": ArtifactRef?,    # required for approved-for-declared-use
      "status": "experimental" | "evaluated" | "approved-for-declared-use"
    }

``evaluation_report_ref`` is always required as a key.  An experimental
prediction may carry ``null`` plus a non-empty
``evaluation_report_unknown_reason`` to state that evaluation has not happened;
``evaluated`` and ``approved-for-declared-use`` require an exact reference and
must not carry an unknown reason.  ``approved-for-declared-use`` additionally
requires an exact ``promotion_decision_ref``; that reference is recorded, never
enforced, and other statuses do not imply promotion.

ProvisionCandidate payload::

    {
      "passages": [{"source_ref_id": str, "locator": exact locator,
                    "content_digest": sha-256 hex}, ...],   # must bind envelope source_refs
      "issuer": str,
      "jurisdiction": {"code": str, "name": str},
      "actor": {"kind": str, "name": str|null, "unknown_reason": str|null},
      "action": str,
      "object": {"kind": str, "identifier": str|null, "unknown_reason": str|null},
      "conditions": [str, ...],
      "exceptions": [str, ...],
      "publication_date": "YYYY-MM-DD" | null,
      "publication_date_unknown_reason": str?,   # required when date is null
      "effectivity": {"kind": "on_date"|"from_date", "date": "YYYY-MM-DD"}
                     | {"kind": "interval", "start": date, "end": date?}
                     | {"kind": "unknown", "unknown_reason": str},
                     # the three forms are mutually exclusive: an interval may
                     # be open-ended (``end`` omitted/null), an unknown form
                     # never invents a date, and a dated form carries no range
      "deadlines": [{"label": str, "date": date|null, "unknown_reason": str|null}, ...],
      "amendment_refs": [ArtifactRef, ...],
      "supersession_refs": [ArtifactRef, ...],
      "unresolved_fields": [{"field": str, "reason": str}, ...]
    }

ArtifactRef is always exact::

    {"artifact_id": str?, "revision_id": str, "content_digest": sha-256 hex}

Mutable pointers (``latest``/``head``/``current``/``tip``/``now``) are rejected
as ``revision_id`` values.  Unknown semantic values use ``null`` plus an
explicit non-empty reason.  Date-only values stay ``YYYY-MM-DD`` and are never
expanded to an instant.

Strict eligibility
==================

:func:`evaluate_eligibility` first requires structural validity, then excludes
any source whose availability is unknown or later than ``information_cutoff``
(and, for predictions, later than ``input_cutoff``).  Explicitly unknown
availability stays structurally valid.  Creation time may follow the cutoff.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
import math
import re

from .errors import (
    BOOLEAN_AS_NUMBER,
    DIGEST_MISMATCH,
    EligibilityResult,
    INTERNAL_ERROR,
    INVALID_DATE,
    INVALID_DIGEST,
    INVALID_TIMESTAMP,
    INVALID_TYPE,
    INVALID_VALUE,
    INVERTED_INTERVAL,
    LATEST_POINTER_FORBIDDEN,
    LATE_AVAILABILITY,
    MISSING_FIELD,
    NAIVE_TIMESTAMP,
    NON_FINITE_NUMBER,
    TEMPORAL_ORDER,
    UNKNOWN_AVAILABILITY,
    UNSUPPORTED_ARTIFACT_TYPE,
    UNSUPPORTED_SCHEMA_VERSION,
    UNRESOLVED_CITATION,
    ContractError,
    ValidationResult,
    issue,
)
from .jsonutil import CanonicalizationError, compute_content_digest, parse_json


SCHEMA_VERSION = 1

DATASET_SNAPSHOT = "dataset_snapshot"
PREDICTION_ARTIFACT = "prediction_artifact"
PROVISION_CANDIDATE = "provision_candidate"

SUPPORTED_ARTIFACT_TYPES = frozenset(
    {DATASET_SNAPSHOT, PREDICTION_ARTIFACT, PROVISION_CANDIDATE}
)

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MUTABLE_POINTERS = frozenset({"latest", "head", "current", "tip", "now"})

_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "artifact_type",
        "revision_id",
        "producer",
        "created_at",
        "information_cutoff",
        "access_policy_ref",
        "scope",
        "source_refs",
        "payload",
        "synthetic",
        "content_digest",
    }
)

_SOURCE_REF_FIELDS = frozenset(
    {"source_id", "source_version", "content_digest", "locator", "availability"}
)
_EXACT_LOCATOR_FIELDS = frozenset({"kind", "path", "start", "end"})
_QUERY_LOCATOR_FIELDS = frozenset({"kind", "query", "start", "end"})
_AVAILABILITY_FIELDS = frozenset({"known_at", "basis", "unknown_reason"})
_ARTIFACT_REF_FIELDS = frozenset({"artifact_id", "revision_id", "content_digest"})

_DATASET_FIELDS = frozenset(
    {
        "window",
        "query_digest",
        "entity_schema",
        "quantity_schema",
        "status",
        "missingness",
        "first_availability_basis",
        "target_features",
    }
)
_PREDICTION_FIELDS = frozenset(
    {
        "model_spec_ref",
        "forecast_origin",
        "input_cutoff",
        "entity",
        "valid_interval",
        "horizon",
        "units",
        "quantity_kind",
        "outcome",
        "quantiles",
        "input_snapshot_ref",
        "evaluation_report_ref",
        "evaluation_report_unknown_reason",
        "promotion_decision_ref",
        "status",
    }
)
_PROVISION_FIELDS = frozenset(
    {
        "passages",
        "issuer",
        "jurisdiction",
        "actor",
        "action",
        "object",
        "conditions",
        "exceptions",
        "publication_date",
        "publication_date_unknown_reason",
        "effectivity",
        "deadlines",
        "amendment_refs",
        "supersession_refs",
        "unresolved_fields",
    }
)


# --- primitive helpers ----------------------------------------------------


def _is_object(value) -> bool:
    return isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray))


def _object_ok(value, path, errors):
    if not _is_object(value):
        errors.append(issue(INVALID_TYPE, path))
        return None
    for key in value.keys():
        if not isinstance(key, str):
            errors.append(issue(INVALID_TYPE, path))
            return None
    return value


def _reject_unknown(obj, allowed, path, errors) -> None:
    for key in obj:
        if key not in allowed:
            errors.append(issue(INVALID_VALUE, path))
            return


def _check_string(value, path, errors, *, nonempty: bool = True):
    if not isinstance(value, str):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if nonempty and not value:
        errors.append(issue(INVALID_VALUE, path))
        return None
    return value


def _get_string(obj, key, path, errors, *, nonempty: bool = True):
    field_path = f"{path}.{key}"
    if key not in obj:
        errors.append(issue(MISSING_FIELD, field_path))
        return None
    return _check_string(obj[key], field_path, errors, nonempty=nonempty)


def _get_bool(obj, key, path, errors):
    field_path = f"{path}.{key}"
    if key not in obj:
        errors.append(issue(MISSING_FIELD, field_path))
        return None
    value = obj[key]
    if not isinstance(value, bool):
        errors.append(issue(INVALID_TYPE, field_path))
        return None
    return value


def _check_integer(value, path, errors, *, minimum=None):
    if isinstance(value, bool):
        errors.append(issue(BOOLEAN_AS_NUMBER, path))
        return None
    if not isinstance(value, int):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if minimum is not None and value < minimum:
        errors.append(issue(INVALID_VALUE, path))
        return None
    return value


def _check_number(value, path, errors, *, minimum=None, exclusive_min=None, exclusive_max=None):
    if isinstance(value, bool):
        errors.append(issue(BOOLEAN_AS_NUMBER, path))
        return None
    if not isinstance(value, (int, float)):
        errors.append(issue(INVALID_TYPE, path))
        return None
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(issue(NON_FINITE_NUMBER, path))
        return None
    if minimum is not None and value < minimum:
        errors.append(issue(INVALID_VALUE, path))
        return None
    if exclusive_min is not None and not value > exclusive_min:
        errors.append(issue(INVALID_VALUE, path))
        return None
    if exclusive_max is not None and not value < exclusive_max:
        errors.append(issue(INVALID_VALUE, path))
        return None
    return value


def _check_digest(value, path, errors):
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        errors.append(issue(INVALID_DIGEST, path))
        return None
    return value


def _get_digest(obj, key, path, errors):
    field_path = f"{path}.{key}"
    if key not in obj:
        errors.append(issue(MISSING_FIELD, field_path))
        return None
    return _check_digest(obj[key], field_path, errors)


def _parse_timestamp(value, path, errors):
    if not isinstance(value, str):
        errors.append(issue(INVALID_TIMESTAMP, path))
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(issue(INVALID_TIMESTAMP, path))
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(issue(NAIVE_TIMESTAMP, path))
        return None
    return parsed


def _get_timestamp(obj, key, path, errors):
    field_path = f"{path}.{key}"
    if key not in obj:
        errors.append(issue(MISSING_FIELD, field_path))
        return None
    return _parse_timestamp(obj[key], field_path, errors)


def _read_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _parse_date(value, path, errors):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        errors.append(issue(INVALID_DATE, path))
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(issue(INVALID_DATE, path))
        return None
    return value


def _check_known_or_unknown(obj, path, errors, *, value_key, reason_key, parse_value):
    value_path = f"{path}.{value_key}"
    reason_path = f"{path}.{reason_key}"
    if value_key not in obj:
        errors.append(issue(MISSING_FIELD, value_path))
        return
    value = obj[value_key]
    reason = obj.get(reason_key)
    if value is None:
        if not isinstance(reason, str) or not reason:
            errors.append(issue(MISSING_FIELD, reason_path))
    else:
        parse_value(value, value_path, errors)
        if reason is not None:
            errors.append(issue(INVALID_VALUE, reason_path))


def _check_string_list(value, path, errors):
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        errors.append(issue(INVALID_TYPE, path))
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(issue(INVALID_TYPE, f"{path}[{index}]"))
            return


def _parse_interval(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return None
    _reject_unknown(obj, {"start", "end"}, path, errors)
    start = _get_timestamp(obj, "start", path, errors)
    end = _get_timestamp(obj, "end", path, errors)
    if start is not None and end is not None and not start < end:
        errors.append(issue(INVERTED_INTERVAL, path))
    return (start, end)


def _check_artifact_ref(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return None
    _reject_unknown(obj, _ARTIFACT_REF_FIELDS, path, errors)
    revision = _get_string(obj, "revision_id", path, errors)
    _get_digest(obj, "content_digest", path, errors)
    if "artifact_id" in obj:
        _check_string(obj["artifact_id"], f"{path}.artifact_id", errors)
    if revision is not None and revision.strip().lower() in _MUTABLE_POINTERS:
        errors.append(issue(LATEST_POINTER_FORBIDDEN, f"{path}.revision_id"))
    return obj


def _check_exact_locator(value, path, errors, *, require_exact: bool = False):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return None
    kind = obj.get("kind")
    if require_exact:
        _reject_unknown(obj, _EXACT_LOCATOR_FIELDS, path, errors)
        if kind != "exact":
            errors.append(issue(INVALID_VALUE, f"{path}.kind"))
        _get_string(obj, "path", path, errors)
        _check_optional_offset_range(obj, path, errors)
        return obj
    if kind == "exact":
        _reject_unknown(obj, _EXACT_LOCATOR_FIELDS, path, errors)
        _get_string(obj, "path", path, errors)
        _check_optional_offset_range(obj, path, errors)
    elif kind == "query":
        _reject_unknown(obj, _QUERY_LOCATOR_FIELDS, path, errors)
        _get_string(obj, "query", path, errors)
        start = _get_timestamp(obj, "start", path, errors)
        end = _get_timestamp(obj, "end", path, errors)
        if start is not None and end is not None and not start < end:
            errors.append(issue(INVERTED_INTERVAL, path))
    else:
        errors.append(issue(INVALID_VALUE, f"{path}.kind"))
    return obj


def _check_optional_offset_range(obj, path, errors):
    values = {}
    for key in ("start", "end"):
        if key in obj:
            parsed = _check_integer(obj[key], f"{path}.{key}", errors, minimum=0)
            if parsed is not None:
                values[key] = parsed
    if len(values) == 2 and values["start"] >= values["end"]:
        errors.append(issue(INVERTED_INTERVAL, path))


def _check_availability(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return
    _reject_unknown(obj, _AVAILABILITY_FIELDS, path, errors)
    if "known_at" not in obj:
        errors.append(issue(MISSING_FIELD, f"{path}.known_at"))
        return
    known = obj["known_at"]
    if known is None:
        reason = obj.get("unknown_reason")
        if not isinstance(reason, str) or not reason:
            errors.append(issue(MISSING_FIELD, f"{path}.unknown_reason"))
        if obj.get("basis") is not None:
            errors.append(issue(INVALID_VALUE, f"{path}.basis"))
    else:
        _parse_timestamp(known, f"{path}.known_at", errors)
        basis = obj.get("basis")
        if not isinstance(basis, str) or not basis:
            errors.append(issue(MISSING_FIELD, f"{path}.basis"))
        if obj.get("unknown_reason") is not None:
            errors.append(issue(INVALID_VALUE, f"{path}.unknown_reason"))


def _validate_source_ref(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return None
    _reject_unknown(obj, _SOURCE_REF_FIELDS, path, errors)
    source_id = _get_string(obj, "source_id", path, errors)
    _get_string(obj, "source_version", path, errors)
    _get_digest(obj, "content_digest", path, errors)
    if "locator" not in obj:
        errors.append(issue(MISSING_FIELD, f"{path}.locator"))
    else:
        _check_exact_locator(obj["locator"], f"{path}.locator", errors)
    if "availability" not in obj:
        errors.append(issue(MISSING_FIELD, f"{path}.availability"))
    else:
        _check_availability(obj["availability"], f"{path}.availability", errors)
    return source_id


def _validate_source_refs(artifact, path, errors):
    refs_path = f"{path}.source_refs"
    if "source_refs" not in artifact:
        errors.append(issue(MISSING_FIELD, refs_path))
        return set()
    refs = artifact["source_refs"]
    if not isinstance(refs, (list, tuple)) or isinstance(refs, (str, bytes)):
        errors.append(issue(INVALID_TYPE, refs_path))
        return set()
    if not refs:
        errors.append(issue(INVALID_VALUE, refs_path))
        return set()
    source_ids = set()
    for index, ref in enumerate(refs):
        ref_path = f"{refs_path}[{index}]"
        source_id = _validate_source_ref(ref, ref_path, errors)
        if source_id is None:
            continue
        if source_id in source_ids:
            errors.append(issue(INVALID_VALUE, f"{ref_path}.source_id"))
        source_ids.add(source_id)
    return source_ids


# --- envelope -------------------------------------------------------------


def _validate_producer(artifact, path, errors):
    producer_path = f"{path}.producer"
    if "producer" not in artifact:
        errors.append(issue(MISSING_FIELD, producer_path))
        return
    obj = _object_ok(artifact["producer"], producer_path, errors)
    if obj is None:
        return
    _reject_unknown(obj, {"name", "version"}, producer_path, errors)
    _get_string(obj, "name", producer_path, errors)
    _get_string(obj, "version", producer_path, errors)


def _validate_scope(artifact, path, errors):
    scope_path = f"{path}.scope"
    if "scope" not in artifact:
        errors.append(issue(MISSING_FIELD, scope_path))
        return
    obj = _object_ok(artifact["scope"], scope_path, errors)
    if obj is None:
        return
    _reject_unknown(obj, {"kind", "id"}, scope_path, errors)
    kind = _get_string(obj, "kind", scope_path, errors)
    if kind is not None and kind not in {"case", "dataset", "task"}:
        errors.append(issue(INVALID_VALUE, f"{scope_path}.kind"))
    _get_string(obj, "id", scope_path, errors)


# --- dataset snapshot -----------------------------------------------------


def _validate_dataset_payload(payload, path, errors, context):
    _reject_unknown(payload, _DATASET_FIELDS, path, errors)

    if "window" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.window"))
    else:
        _parse_interval(payload["window"], f"{path}.window", errors)

    _get_digest(payload, "query_digest", path, errors)

    entity_path = f"{path}.entity_schema"
    if "entity_schema" not in payload:
        errors.append(issue(MISSING_FIELD, entity_path))
    else:
        entity = _object_ok(payload["entity_schema"], entity_path, errors)
        if entity is not None:
            _reject_unknown(entity, {"entity_type", "id_field"}, entity_path, errors)
            _get_string(entity, "entity_type", entity_path, errors)
            if "id_field" in entity:
                _check_string(entity["id_field"], f"{entity_path}.id_field", errors)

    quantity_path = f"{path}.quantity_schema"
    if "quantity_schema" not in payload:
        errors.append(issue(MISSING_FIELD, quantity_path))
    else:
        quantity = _object_ok(payload["quantity_schema"], quantity_path, errors)
        if quantity is not None:
            _reject_unknown(quantity, {"quantity_kind", "units", "currency"}, quantity_path, errors)
            _get_string(quantity, "quantity_kind", quantity_path, errors)
            _get_string(quantity, "units", quantity_path, errors)
            if "currency" in quantity:
                _check_string(quantity["currency"], f"{quantity_path}.currency", errors)

    status = _get_string(payload, "status", path, errors)
    if status is not None and status not in {"raw", "final"}:
        errors.append(issue(INVALID_VALUE, f"{path}.status"))

    missing_path = f"{path}.missingness"
    if "missingness" not in payload:
        errors.append(issue(MISSING_FIELD, missing_path))
    else:
        missingness = _object_ok(payload["missingness"], missing_path, errors)
        if missingness is not None:
            _reject_unknown(
                missingness, {"missing_count", "total_count", "basis"}, missing_path, errors
            )
            missing_count = None
            total_count = None
            if "missing_count" in missingness:
                missing_count = _check_integer(
                    missingness["missing_count"], f"{missing_path}.missing_count", errors, minimum=0
                )
            else:
                errors.append(issue(MISSING_FIELD, f"{missing_path}.missing_count"))
            if "total_count" in missingness:
                total_count = _check_integer(
                    missingness["total_count"], f"{missing_path}.total_count", errors, minimum=0
                )
            else:
                errors.append(issue(MISSING_FIELD, f"{missing_path}.total_count"))
            _get_string(missingness, "basis", missing_path, errors)
            if missing_count is not None and total_count is not None and missing_count > total_count:
                errors.append(issue(INVALID_VALUE, missing_path))

    _get_string(payload, "first_availability_basis", path, errors)

    target_path = f"{path}.target_features"
    if "target_features" not in payload:
        errors.append(issue(MISSING_FIELD, target_path))
        return
    features = payload["target_features"]
    if not isinstance(features, (list, tuple)) or isinstance(features, (str, bytes)):
        errors.append(issue(INVALID_TYPE, target_path))
        return
    if not features:
        errors.append(issue(INVALID_VALUE, target_path))
        return
    for index, feature in enumerate(features):
        feature_path = f"{target_path}[{index}]"
        obj = _object_ok(feature, feature_path, errors)
        if obj is None:
            continue
        _reject_unknown(obj, {"name", "role", "units", "quantity_kind"}, feature_path, errors)
        _get_string(obj, "name", feature_path, errors)
        role = _get_string(obj, "role", feature_path, errors)
        if role is not None and role not in {"target", "feature"}:
            errors.append(issue(INVALID_VALUE, f"{feature_path}.role"))
        _get_string(obj, "units", feature_path, errors)
        if "quantity_kind" in obj:
            _check_string(obj["quantity_kind"], f"{feature_path}.quantity_kind", errors)


# --- prediction artifact --------------------------------------------------


def _validate_outcome(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return
    kind = obj.get("kind")
    if kind == "point":
        _reject_unknown(obj, {"kind", "value"}, path, errors)
        if "value" not in obj:
            errors.append(issue(MISSING_FIELD, f"{path}.value"))
        else:
            _check_number(obj["value"], f"{path}.value", errors)
    elif kind == "class_scores":
        _reject_unknown(obj, {"kind", "scores"}, path, errors)
        scores_path = f"{path}.scores"
        if "scores" not in obj:
            errors.append(issue(MISSING_FIELD, scores_path))
            return
        scores = _object_ok(obj["scores"], scores_path, errors)
        if scores is None:
            return
        if not scores:
            errors.append(issue(INVALID_VALUE, scores_path))
            return
        # Do not build a path from label keys; report at the container.
        for label in scores:
            score = scores[label]
            if isinstance(score, bool):
                errors.append(issue(BOOLEAN_AS_NUMBER, scores_path))
                return
            if not isinstance(score, (int, float)):
                errors.append(issue(INVALID_TYPE, scores_path))
                return
            if isinstance(score, float) and not math.isfinite(score):
                errors.append(issue(NON_FINITE_NUMBER, scores_path))
                return
    else:
        errors.append(issue(INVALID_VALUE, f"{path}.kind"))


def _validate_quantiles(value, path, errors):
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        errors.append(issue(INVALID_TYPE, path))
        return
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        obj = _object_ok(item, item_path, errors)
        if obj is None:
            continue
        _reject_unknown(obj, {"level", "value"}, item_path, errors)
        if "level" not in obj:
            errors.append(issue(MISSING_FIELD, f"{item_path}.level"))
        else:
            _check_number(
                obj["level"], f"{item_path}.level", errors, exclusive_min=0, exclusive_max=1
            )
        if "value" not in obj:
            errors.append(issue(MISSING_FIELD, f"{item_path}.value"))
        else:
            _check_number(obj["value"], f"{item_path}.value", errors)


def _validate_prediction_payload(payload, path, errors, context):
    _reject_unknown(payload, _PREDICTION_FIELDS, path, errors)

    model_ref_path = f"{path}.model_spec_ref"
    if "model_spec_ref" not in payload:
        errors.append(issue(MISSING_FIELD, model_ref_path))
    else:
        _check_artifact_ref(payload["model_spec_ref"], model_ref_path, errors)

    forecast_origin = _get_timestamp(payload, "forecast_origin", path, errors)
    input_cutoff = _get_timestamp(payload, "input_cutoff", path, errors)

    entity_path = f"{path}.entity"
    if "entity" not in payload:
        errors.append(issue(MISSING_FIELD, entity_path))
    else:
        entity = _object_ok(payload["entity"], entity_path, errors)
        if entity is not None:
            _reject_unknown(entity, {"entity_type", "entity_id", "region"}, entity_path, errors)
            _get_string(entity, "entity_type", entity_path, errors)
            _get_string(entity, "entity_id", entity_path, errors)
            _get_string(entity, "region", entity_path, errors)

    if "valid_interval" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.valid_interval"))
    else:
        _parse_interval(payload["valid_interval"], f"{path}.valid_interval", errors)

    horizon_path = f"{path}.horizon"
    if "horizon" not in payload:
        errors.append(issue(MISSING_FIELD, horizon_path))
    else:
        horizon = _object_ok(payload["horizon"], horizon_path, errors)
        if horizon is not None:
            _reject_unknown(horizon, {"value", "unit"}, horizon_path, errors)
            if "value" not in horizon:
                errors.append(issue(MISSING_FIELD, f"{horizon_path}.value"))
            else:
                _check_number(horizon["value"], f"{horizon_path}.value", errors, exclusive_min=0)
            _get_string(horizon, "unit", horizon_path, errors)

    _get_string(payload, "units", path, errors)
    _get_string(payload, "quantity_kind", path, errors)

    if "outcome" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.outcome"))
    else:
        _validate_outcome(payload["outcome"], f"{path}.outcome", errors)

    if "quantiles" in payload:
        _validate_quantiles(payload["quantiles"], f"{path}.quantiles", errors)

    snapshot_ref_path = f"{path}.input_snapshot_ref"
    if "input_snapshot_ref" not in payload:
        errors.append(issue(MISSING_FIELD, snapshot_ref_path))
    else:
        _check_artifact_ref(payload["input_snapshot_ref"], snapshot_ref_path, errors)

    status = _get_string(payload, "status", path, errors)
    if status is not None and status not in {
        "experimental",
        "evaluated",
        "approved-for-declared-use",
    }:
        errors.append(issue(INVALID_VALUE, f"{path}.status"))

    # ``evaluation_report_ref`` is always a required key.  It is either an exact
    # reference to a completed evaluation, or ``null`` for an experimental
    # prediction that has not been evaluated yet -- in which case a non-empty
    # ``evaluation_report_unknown_reason`` must say so explicitly.
    evaluation_ref_path = f"{path}.evaluation_report_ref"
    unknown_reason_path = f"{path}.evaluation_report_unknown_reason"
    requires_real_report = status in {"evaluated", "approved-for-declared-use"}
    if "evaluation_report_ref" not in payload:
        errors.append(issue(MISSING_FIELD, evaluation_ref_path))
    else:
        evaluation_ref = payload["evaluation_report_ref"]
        unknown_reason = payload.get("evaluation_report_unknown_reason")
        if evaluation_ref is None:
            if requires_real_report:
                errors.append(issue(INVALID_VALUE, evaluation_ref_path))
            elif not isinstance(unknown_reason, str) or not unknown_reason:
                errors.append(issue(MISSING_FIELD, unknown_reason_path))
        else:
            _check_artifact_ref(evaluation_ref, evaluation_ref_path, errors)
            if unknown_reason is not None:
                errors.append(issue(INVALID_VALUE, unknown_reason_path))

    # ``promotion_decision_ref`` records the promotion decision behind an
    # ``approved-for-declared-use`` status.  It is structure only: it does not
    # grant access or authority, and no other status may imply promotion.
    promotion_path = f"{path}.promotion_decision_ref"
    promotion_ref = payload.get("promotion_decision_ref")
    if status == "approved-for-declared-use":
        if promotion_ref is None:
            errors.append(issue(MISSING_FIELD, promotion_path))
        else:
            _check_artifact_ref(promotion_ref, promotion_path, errors)
    elif promotion_ref is not None:
        errors.append(issue(INVALID_VALUE, promotion_path))

    # input_cutoff cannot follow the forecast origin or the envelope cutoff.
    if input_cutoff is not None and forecast_origin is not None and not input_cutoff <= forecast_origin:
        errors.append(issue(TEMPORAL_ORDER, f"{path}.input_cutoff"))
    information_cutoff = context.get("information_cutoff")
    if input_cutoff is not None and information_cutoff is not None and not input_cutoff <= information_cutoff:
        errors.append(issue(TEMPORAL_ORDER, f"{path}.input_cutoff"))


# --- provision candidate --------------------------------------------------


def _validate_passage(value, path, errors, source_ids):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return
    _reject_unknown(obj, {"source_ref_id", "locator", "content_digest"}, path, errors)
    source_ref_id = _get_string(obj, "source_ref_id", path, errors)
    _get_digest(obj, "content_digest", path, errors)
    if "locator" not in obj:
        errors.append(issue(MISSING_FIELD, f"{path}.locator"))
    else:
        _check_exact_locator(obj["locator"], f"{path}.locator", errors, require_exact=True)
    if (
        source_ids is not None
        and source_ref_id is not None
        and source_ref_id not in source_ids
    ):
        errors.append(issue(UNRESOLVED_CITATION, f"{path}.source_ref_id"))


def _validate_effectivity(value, path, errors):
    obj = _object_ok(value, path, errors)
    if obj is None:
        return
    _reject_unknown(obj, {"kind", "date", "start", "end", "unknown_reason"}, path, errors)
    kind = obj.get("kind")
    # ``kind`` is arbitrary JSON; type-check before any set membership so a
    # list/object value cannot raise ``TypeError: unhashable``.
    if not isinstance(kind, str):
        errors.append(issue(INVALID_VALUE, f"{path}.kind"))
        return
    if kind == "unknown":
        reason = obj.get("unknown_reason")
        if not isinstance(reason, str) or not reason:
            errors.append(issue(MISSING_FIELD, f"{path}.unknown_reason"))
        # An unknown form must not smuggle in an invented date or range.
        for absent in ("date", "start", "end"):
            if obj.get(absent) is not None:
                errors.append(issue(INVALID_VALUE, f"{path}.{absent}"))
    elif kind in {"on_date", "from_date"}:
        if "date" not in obj:
            errors.append(issue(MISSING_FIELD, f"{path}.date"))
        else:
            _parse_date(obj["date"], f"{path}.date", errors)
        # A single-date form does not carry an open range or a reason.
        for absent in ("start", "end", "unknown_reason"):
            if obj.get(absent) is not None:
                errors.append(issue(INVALID_VALUE, f"{path}.{absent}"))
    elif kind == "interval":
        start = None
        end = None
        if "start" not in obj:
            errors.append(issue(MISSING_FIELD, f"{path}.start"))
        else:
            start = _parse_date(obj["start"], f"{path}.start", errors)
        # ``end`` may be omitted or null: an explicitly open-ended interval.
        if "end" in obj and obj["end"] is not None:
            end = _parse_date(obj["end"], f"{path}.end", errors)
        if start is not None and end is not None and start >= end:
            errors.append(issue(INVERTED_INTERVAL, path))
        # An interval form must not also carry a single date or a reason.
        for absent in ("date", "unknown_reason"):
            if obj.get(absent) is not None:
                errors.append(issue(INVALID_VALUE, f"{path}.{absent}"))
    else:
        errors.append(issue(INVALID_VALUE, f"{path}.kind"))


def _validate_provision_payload(payload, path, errors, context):
    _reject_unknown(payload, _PROVISION_FIELDS, path, errors)
    source_ids = context.get("source_ids")

    passages_path = f"{path}.passages"
    if "passages" not in payload:
        errors.append(issue(MISSING_FIELD, passages_path))
    else:
        passages = payload["passages"]
        if not isinstance(passages, (list, tuple)) or isinstance(passages, (str, bytes)):
            errors.append(issue(INVALID_TYPE, passages_path))
        elif not passages:
            errors.append(issue(INVALID_VALUE, passages_path))
        else:
            for index, passage in enumerate(passages):
                _validate_passage(passage, f"{passages_path}[{index}]", errors, source_ids)

    _get_string(payload, "issuer", path, errors)

    jurisdiction_path = f"{path}.jurisdiction"
    if "jurisdiction" not in payload:
        errors.append(issue(MISSING_FIELD, jurisdiction_path))
    else:
        jurisdiction = _object_ok(payload["jurisdiction"], jurisdiction_path, errors)
        if jurisdiction is not None:
            _reject_unknown(jurisdiction, {"code", "name"}, jurisdiction_path, errors)
            _get_string(jurisdiction, "code", jurisdiction_path, errors)
            _get_string(jurisdiction, "name", jurisdiction_path, errors)

    actor_path = f"{path}.actor"
    if "actor" not in payload:
        errors.append(issue(MISSING_FIELD, actor_path))
    else:
        actor = _object_ok(payload["actor"], actor_path, errors)
        if actor is not None:
            _reject_unknown(actor, {"kind", "name", "unknown_reason"}, actor_path, errors)
            _get_string(actor, "kind", actor_path, errors)
            _check_known_or_unknown(
                actor,
                actor_path,
                errors,
                value_key="name",
                reason_key="unknown_reason",
                parse_value=lambda value, value_path, errs: _check_string(value, value_path, errs),
            )

    _get_string(payload, "action", path, errors)

    object_path = f"{path}.object"
    if "object" not in payload:
        errors.append(issue(MISSING_FIELD, object_path))
    else:
        semantic = _object_ok(payload["object"], object_path, errors)
        if semantic is not None:
            _reject_unknown(semantic, {"kind", "identifier", "unknown_reason"}, object_path, errors)
            _get_string(semantic, "kind", object_path, errors)
            _check_known_or_unknown(
                semantic,
                object_path,
                errors,
                value_key="identifier",
                reason_key="unknown_reason",
                parse_value=lambda value, value_path, errs: _check_string(value, value_path, errs),
            )

    if "conditions" in payload:
        _check_string_list(payload["conditions"], f"{path}.conditions", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.conditions"))
    if "exceptions" in payload:
        _check_string_list(payload["exceptions"], f"{path}.exceptions", errors)
    else:
        errors.append(issue(MISSING_FIELD, f"{path}.exceptions"))

    if "publication_date" not in payload and "publication_date_unknown_reason" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.publication_date"))
    else:
        _check_known_or_unknown(
            payload,
            path,
            errors,
            value_key="publication_date",
            reason_key="publication_date_unknown_reason",
            parse_value=_parse_date,
        )

    if "effectivity" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.effectivity"))
    else:
        _validate_effectivity(payload["effectivity"], f"{path}.effectivity", errors)

    if "deadlines" not in payload:
        errors.append(issue(MISSING_FIELD, f"{path}.deadlines"))
    else:
        deadlines_path = f"{path}.deadlines"
        deadlines = payload["deadlines"]
        if not isinstance(deadlines, (list, tuple)) or isinstance(deadlines, (str, bytes)):
            errors.append(issue(INVALID_TYPE, deadlines_path))
        else:
            for index, deadline in enumerate(deadlines):
                item_path = f"{deadlines_path}[{index}]"
                obj = _object_ok(deadline, item_path, errors)
                if obj is None:
                    continue
                _reject_unknown(obj, {"label", "date", "unknown_reason"}, item_path, errors)
                _get_string(obj, "label", item_path, errors)
                _check_known_or_unknown(
                    obj,
                    item_path,
                    errors,
                    value_key="date",
                    reason_key="unknown_reason",
                    parse_value=_parse_date,
                )

    for key in ("amendment_refs", "supersession_refs"):
        key_path = f"{path}.{key}"
        if key not in payload:
            errors.append(issue(MISSING_FIELD, key_path))
            continue
        refs = payload[key]
        if not isinstance(refs, (list, tuple)) or isinstance(refs, (str, bytes)):
            errors.append(issue(INVALID_TYPE, key_path))
            continue
        for index, ref in enumerate(refs):
            _check_artifact_ref(ref, f"{key_path}[{index}]", errors)

    unresolved_path = f"{path}.unresolved_fields"
    if "unresolved_fields" not in payload:
        errors.append(issue(MISSING_FIELD, unresolved_path))
    else:
        unresolved = payload["unresolved_fields"]
        if not isinstance(unresolved, (list, tuple)) or isinstance(unresolved, (str, bytes)):
            errors.append(issue(INVALID_TYPE, unresolved_path))
        else:
            for index, item in enumerate(unresolved):
                item_path = f"{unresolved_path}[{index}]"
                obj = _object_ok(item, item_path, errors)
                if obj is None:
                    continue
                _reject_unknown(obj, {"field", "reason"}, item_path, errors)
                _get_string(obj, "field", item_path, errors)
                _get_string(obj, "reason", item_path, errors)


# --- public API -----------------------------------------------------------


def validate_artifact(artifact, *, require_digest: bool = True) -> ValidationResult:
    """Validate one artifact against its declared schema version 1 type.

    Returns a :class:`ValidationResult`; it never raises for malformed input.
    When ``require_digest`` is true the top-level ``content_digest`` must be
    present, well-formed and equal to the canonical content digest.
    """
    errors: list[ContractError] = []
    if not _is_object(artifact):
        return ValidationResult((issue(INVALID_TYPE, "$"),))

    _reject_unknown(artifact, _ENVELOPE_FIELDS, "$", errors)

    if "schema_version" not in artifact:
        errors.append(issue(MISSING_FIELD, "$.schema_version"))
    else:
        version = artifact["schema_version"]
        if isinstance(version, bool):
            errors.append(issue(BOOLEAN_AS_NUMBER, "$.schema_version"))
        elif not isinstance(version, int):
            errors.append(issue(INVALID_TYPE, "$.schema_version"))
        elif version != SCHEMA_VERSION:
            errors.append(issue(UNSUPPORTED_SCHEMA_VERSION, "$.schema_version"))

    artifact_type = _get_string(artifact, "artifact_type", "$", errors)
    if artifact_type is not None and artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        errors.append(issue(UNSUPPORTED_ARTIFACT_TYPE, "$.artifact_type"))
        artifact_type = None

    for key in ("artifact_id", "revision_id", "access_policy_ref"):
        _get_string(artifact, key, "$", errors)

    _validate_producer(artifact, "$", errors)

    information_cutoff = _get_timestamp(artifact, "information_cutoff", "$", errors)
    _get_timestamp(artifact, "created_at", "$", errors)
    _get_bool(artifact, "synthetic", "$", errors)
    _validate_scope(artifact, "$", errors)
    source_ids = _validate_source_refs(artifact, "$", errors)

    if "payload" not in artifact:
        errors.append(issue(MISSING_FIELD, "$.payload"))
    else:
        payload = artifact["payload"]
        payload_path = "$.payload"
        if not _is_object(payload):
            errors.append(issue(INVALID_TYPE, payload_path))
        elif artifact_type == DATASET_SNAPSHOT:
            _validate_dataset_payload(payload, payload_path, errors, {})
        elif artifact_type == PREDICTION_ARTIFACT:
            _validate_prediction_payload(
                payload, payload_path, errors, {"information_cutoff": information_cutoff}
            )
        elif artifact_type == PROVISION_CANDIDATE:
            _validate_provision_payload(
                payload, payload_path, errors, {"source_ids": source_ids}
            )

    if require_digest:
        stored = artifact.get("content_digest")
        if "content_digest" not in artifact:
            errors.append(issue(MISSING_FIELD, "$.content_digest"))
        elif not isinstance(stored, str) or not DIGEST_RE.fullmatch(stored):
            errors.append(issue(INVALID_DIGEST, "$.content_digest"))
        else:
            try:
                expected = compute_content_digest(artifact)
            except CanonicalizationError:
                # Unserializable content (lone surrogate, excessive nesting,
                # non-finite/non-JSON values) is reported as a safe contract
                # error; the raw exception never escapes.
                errors.append(issue(INTERNAL_ERROR, "$"))
            else:
                if expected != stored:
                    errors.append(issue(DIGEST_MISMATCH, "$.content_digest"))

    return ValidationResult(tuple(errors))


def validate_json(text) -> ValidationResult:
    """Parse strict JSON text and validate the resulting artifact.

    Non-parsing failures return ``MALFORMED_JSON`` / ``DUPLICATE_KEY`` /
    ``NON_FINITE_NUMBER``; non-object roots return ``INVALID_TYPE``; content that
    parses but cannot be canonicalized returns ``INTERNAL_ERROR``.  It never
    raises for malformed input.
    """
    value, error = parse_json(text)
    if error is not None:
        return ValidationResult((error,))
    return validate_artifact(value)


def evaluate_eligibility(artifact) -> EligibilityResult:
    """Decide strict eligibility for an artifact.

    Structural validity is required first.  Then every source availability must
    be known and at or before ``information_cutoff`` (and ``input_cutoff`` for
    predictions).  Unknown availability is structurally valid but never
    strictly eligible.
    """
    result = validate_artifact(artifact)
    if not result.ok:
        return EligibilityResult(structural_ok=False, eligible=False, errors=result.errors)

    information_cutoff = _read_timestamp(artifact["information_cutoff"])
    input_cutoff = None
    if artifact.get("artifact_type") == PREDICTION_ARTIFACT:
        payload = artifact.get("payload")
        if isinstance(payload, Mapping):
            input_cutoff = _read_timestamp(payload.get("input_cutoff"))

    errors: list[ContractError] = []
    for index, ref in enumerate(artifact["source_refs"]):
        availability = ref.get("availability") if isinstance(ref, Mapping) else None
        known_at = availability.get("known_at") if isinstance(availability, Mapping) else None
        path = f"$.source_refs[{index}].availability.known_at"
        if known_at is None:
            errors.append(issue(UNKNOWN_AVAILABILITY, path))
            continue
        timestamp = _read_timestamp(known_at)
        if timestamp is None:
            errors.append(issue(INVALID_TIMESTAMP, path))
            continue
        if information_cutoff is not None and timestamp > information_cutoff:
            errors.append(issue(LATE_AVAILABILITY, path))
            continue
        if input_cutoff is not None and timestamp > input_cutoff:
            errors.append(issue(LATE_AVAILABILITY, path))

    return EligibilityResult(structural_ok=True, eligible=not errors, errors=tuple(errors))


__all__ = [
    "SCHEMA_VERSION",
    "DATASET_SNAPSHOT",
    "PREDICTION_ARTIFACT",
    "PROVISION_CANDIDATE",
    "SUPPORTED_ARTIFACT_TYPES",
    "validate_artifact",
    "validate_json",
    "evaluate_eligibility",
]
