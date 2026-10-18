"""The ontology's claim shape: the response schema and the code that validates it.

This module is the contract between the System Two extraction and the ontology of
[ontology profile v1](../../../../docs/architecture/ontology-profile-v1.md). A model is
asked for claims in this shape and its answer is checked against it before anything is
recorded; the very same dictionaries are the ``responseFormat.text.schema`` the Gemini
request carries, so the vocabulary the model is offered and the vocabulary code enforces
are one object, never two that can drift.

The shape, field by field, from the profile and the corpus records:

* **subject** — a typed reference: ``type`` from the profile's core types, a stable
  ``id`` and the source's own ``label``. A model may name a kind the profile lacks in
  ``proposed_type``; it can never extend the type list, because a type outside this
  vocabulary is not a reference the store can hold.
* **predicate** — exactly one name from the profile's relation list. The profile forbids
  a generic ``relatedTo`` and a default ``causes`` edge, so neither is offered here, and
  a predicate outside the list is refused rather than recorded.
* **object** — a typed reference, or a value: free text when the claim states a phrase,
  or a quantity (``value``, ``unit``, ``quantity_kind``) when it states a number. A
  quantity must carry its kind and unit, the profile's own rule for capacities, prices
  and intervals.
* **modality** — the words of the ontology note (actual report, target, proposal,
  conditional intention, forecast, denial) plus ``directive``, added by the reserve-market
  walk for an order the issuer states as taking effect
  ([the spike](../../../../docs/work/corpus/spike-reserve-market.md)).
* **citation** — the source id, the immutable source version, the character offsets into
  that version's text layer and the quoted text, exactly as the profile's "exact source
  revision/locator" requires. :mod:`check` refuses any citation the text layer does not
  confirm, and confirms it only against the revision it names, so identical passages in
  two revisions stay two citations.
* **valid time** — the time the source itself states for the condition it describes,
  with its precision: a year, a month, a date (which stays a date), or an offset-bearing
  instant. Publication time is the source version's own field, never this one.
* **attributed_actor**, **rationale** — who the source attributes the statement to, and
  one sentence of why the passage states it.

Two properties the code holds, not the model:

* **Every claim enters as proposed.** There is no review-state field in the response
  schema at all: the model cannot return "accepted", and ``proposed_claims`` stamps each
  validated claim ``review_state: "proposed"`` with the extraction method and version.
  Nothing in this package moves an accepted assumption or an applicability assessment;
  only an analyst's recorded decision does that, elsewhere.
* **The claim id is derived from the proposition** (subject, predicate, object, modality,
  attributed actor, valid time and citation — the citation's source, immutable revision,
  offsets and quote included), so the same statement cited to the same passage of the same
  source version has one identity in any run, and a statement differing anywhere is a
  different claim.

No network, credential, clock or model is consulted here: the module validates values.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime

from src.contracts.jsonutil import canonical_bytes

__all__ = [
    "CITATION_KEYS", "ExtractionRefused", "MAX_CLAIMS", "MAX_UNKNOWNS", "METHOD",
    "METHOD_VERSION", "MODALITIES", "OBJECT_KEYS", "PREDICATES", "PROPOSED",
    "REFERENCE_KEYS", "REFERENCE_TYPES", "RESPONSE_SCHEMA", "TIME_PRECISIONS",
    "VALID_TIME_KEYS", "claim_identity", "proposed_claims", "validate_claim",
    "validate_claim_set",
]

#: The profile's core types, in its own order (Physical, Institutional, Evidence,
#: Research, Modeling, Judgment). A reference names one of these and nothing else.
REFERENCE_TYPES = (
    "Region", "Plant", "GeneratingUnit", "MarketResource", "NetworkElement",
    "Issuer", "RuleVersion", "ApplicabilityAssessment", "MarketInterval", "Commodity",
    "SourceVersion", "Passage", "SeriesReference", "Claim", "EventReport",
    "SourceLineageGroup",
    "Hypothesis", "AssumptionRevision", "ReviewDecision", "BeliefSnapshot",
    "FeatureSpec", "ModelSpec", "PredictionArtifact", "ModelRepresentation",
    "ScenarioProposal", "RunArtifact", "Comparison", "OutlookRevision",
    "DecisionTaskSpec", "CompiledTask", "JudgmentArtifact", "DependencyImpact",
)

#: The profile's relation list, verbatim and complete. It is the whole enum: the profile
#: forbids a generic ``relatedTo`` edge and a default ``causes`` edge, and a model cannot
#: extend production semantics by proposing one.
PREDICATES = (
    "refersTo", "attributedTo", "reports", "derivedFrom", "supports", "challenges",
    "qualifiedBy", "copiedFrom", "represents", "usesAssumption", "effectiveDuring",
    "comparedWith", "reviewedBy", "dependsOn",
)

#: The modality vocabulary: the ontology note's list (actual report, target, proposal,
#: conditional intention, forecast, denial) plus ``directive``, which the reserve-market
#: walk added for an order its issuer states as taking effect.
MODALITIES = ("actual_report", "target", "proposal", "conditional_intention",
              "forecast", "denial", "directive")

#: A stated valid time's precision. ``date`` is a date and never becomes midnight.
TIME_PRECISIONS = ("year", "month", "day", "second", "fraction")

#: The claim record's own stamp. Every claim this package writes carries it.
PROPOSED = "proposed"

#: The extraction method and version recorded on every proposed claim. The schema moves to
#: v2 because the citation carries the immutable source version, so claim identity separates
#: identical passages in different revisions.
METHOD = "corpus-extraction.v1"
METHOD_VERSION = "corpus-extract-schema-v2"

#: The same per-request budget the review core's compiler sets for passages.
MAX_CLAIMS = 32
MAX_UNKNOWNS = 8

CLAIM_KEYS = ("subject", "predicate", "object", "modality", "attributed_actor",
              "valid_time", "citation", "rationale", "proposed_type")
REFERENCE_KEYS = ("type", "id", "label")
OBJECT_KEYS = ("reference", "value", "unit", "quantity_kind")
VALID_TIME_KEYS = ("value", "precision", "unknown_reason")
CITATION_KEYS = ("source_id", "source_version", "start", "end", "quote")

#: The proposition fields claim identity is derived from. Rationale and proposed_type
#: are commentary about the claim, so they never change its identity.
_IDENTITY_KEYS = ("subject", "predicate", "object", "modality", "attributed_actor",
                  "valid_time", "citation")

#: A quantity: the signed decimal string the review core's quantity contract uses.
_DECIMAL = r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"


class ExtractionRefused(ValueError):
    """A refused claim set, claim, reference or citation. The code is stable."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))

    def as_dict(self):
        return {"code": self.code, "detail": self.detail}


def _refuse(code, detail):
    raise ExtractionRefused(code, detail)


def _bounded_text(value, name, limit=300, code="INVALID_CLAIM"):
    if type(value) is not str or not value.strip():
        _refuse(code, "%s must be a non-blank string" % name)
    if len(value) > limit:
        _refuse(code, "%s is longer than %d characters" % (name, limit))
    return value


def _nullable_text(value, name, limit=300, code="INVALID_CLAIM"):
    if value is None:
        return None
    return _bounded_text(value, name, limit, code)


def _is_choice(value, allowed, name, code="INVALID_CLAIM"):
    if type(value) is not str or value not in allowed:
        _refuse(code, "%s must be one of %s" % (name, list(allowed)))
    return value


def validate_reference(value, name, *, nullable=False):
    """A typed reference: ``type`` from the profile, a stable id and the source's label."""
    if value is None and nullable:
        return None
    if type(value) is not dict or set(value) != set(REFERENCE_KEYS):
        _refuse("INVALID_CLAIM", "%s must be an object with exactly %s" % (name, list(REFERENCE_KEYS)))
    _is_choice(value["type"], REFERENCE_TYPES, "%s.type" % name)
    _bounded_text(value["id"], "%s.id" % name, 200)
    _bounded_text(value["label"], "%s.label" % name, 300)
    return value


def validate_valid_time(value, name="valid_time"):
    """A stated valid time with its precision, or an explicit unknown with a reason.

    A date stays a date: the precision must match the value's shape, and nothing here
    turns a date into midnight. ``second`` is an offset-bearing instant without a
    fraction, ``fraction`` one with.
    """
    if type(value) is not dict or set(value) != set(VALID_TIME_KEYS):
        _refuse("INVALID_CLAIM", "%s must be an object with exactly %s"
                % (name, list(VALID_TIME_KEYS)))
    stated, precision = value["value"], value["precision"]
    if stated is None:
        if precision is not None:
            _refuse("INVALID_CLAIM", "%s: an unknown time cannot carry a precision" % name)
        _bounded_text(value["unknown_reason"], "%s.unknown_reason" % name, 300)
        return value
    _bounded_text(stated, "%s.value" % name, 60)
    _is_choice(precision, TIME_PRECISIONS, "%s.precision" % name)
    if value["unknown_reason"] is not None:
        _refuse("INVALID_CLAIM", "%s: a stated time cannot also carry an unknown reason" % name)
    _check_stated_time(stated, precision, name)
    return value


def _check_stated_time(stated, precision, name):
    """The value must be what its precision claims; nothing is repaired into a shape."""
    parts = stated.split("-")
    try:
        if precision == "year":
            if len(parts) != 1 or len(parts[0]) != 4 or not parts[0].isdigit():
                _refuse("MALFORMED_STATED_TIME", "%s value %r is not a year" % (name, stated))
            date(int(parts[0]), 1, 1)
        elif precision == "month":
            if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
                _refuse("MALFORMED_STATED_TIME", "%s value %r is not a month" % (name, stated))
            date(int(parts[0]), int(parts[1]), 1)
        elif precision == "day":
            if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
                _refuse("MALFORMED_STATED_TIME", "%s value %r is not a date" % (name, stated))
            date(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            _check_instant(stated, precision, name)
    except ValueError:
        _refuse("MALFORMED_STATED_TIME", "%s value %r is not a calendar %s" % (name, stated, precision))


def _check_instant(stated, precision, name):
    if "T" not in stated or not (stated.endswith("Z") or stated[-6:-5] in ("+", "-")):
        _refuse("MALFORMED_STATED_TIME",
                "%s value %r is not an offset-bearing instant" % (name, stated))
    try:
        parsed = datetime.fromisoformat(stated.replace("Z", "+00:00"))
    except ValueError:
        _refuse("MALFORMED_STATED_TIME", "%s value %r is not a calendar instant" % (name, stated))
    if parsed.tzinfo is None:
        _refuse("MALFORMED_STATED_TIME", "%s value %r carries no offset" % (name, stated))
    fraction = "." in stated.split("T", 1)[-1]
    if fraction != (precision == "fraction"):
        _refuse("MALFORMED_STATED_TIME",
                "%s precision %r does not match the value %r" % (name, precision, stated))


def validate_citation(value, name="citation"):
    """The exact passage citation: source id, immutable source version, offsets, quoted text.

    This validates the *shape* only. Whether the quote is the text between those offsets in
    that source version's text layer, and whether the passage was one of the compiled
    permitted passages, is :mod:`check`'s refusal, made against the layers themselves.
    """
    if type(value) is not dict or set(value) != set(CITATION_KEYS):
        _refuse("INVALID_CLAIM", "%s must be an object with exactly %s"
                % (name, list(CITATION_KEYS)))
    _bounded_text(value["source_id"], "%s.source_id" % name, 300)
    _bounded_text(value["source_version"], "%s.source_version" % name, 40)
    start, end = value["start"], value["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        _refuse("MALFORMED_CITATION",
                "%s offsets must be integers with 0 <= start < end; got %r..%r" % (name, start, end))
    quote = _bounded_text(value["quote"], "%s.quote" % name, 12000)
    if len(quote) != end - start:
        _refuse("MALFORMED_CITATION",
                "%s quote is %d characters but the offsets span %d"
                % (name, len(quote), end - start))
    return value


def validate_object(value, name="object"):
    """A typed reference, or a value: free text, or a quantity with unit and kind."""
    if type(value) is not dict or set(value) != set(OBJECT_KEYS):
        _refuse("INVALID_CLAIM", "%s must be an object with exactly %s" % (name, list(OBJECT_KEYS)))
    reference = validate_reference(value["reference"], "%s.reference" % name, nullable=True)
    text = _nullable_text(value["value"], "%s.value" % name, 600)
    unit = _nullable_text(value["unit"], "%s.unit" % name, 60)
    kind = _nullable_text(value["quantity_kind"], "%s.quantity_kind" % name, 100)
    if reference is not None and (text is not None or unit is not None or kind is not None):
        _refuse("INVALID_CLAIM",
                "%s states a reference and a value together; a claim's object is one or the other" % name)
    if reference is None and text is None:
        _refuse("INVALID_CLAIM", "%s states neither a reference nor a value" % name)
    if reference is None and (unit is None) != (kind is None):
        _refuse("INVALID_CLAIM",
                "%s: a quantity carries its unit and quantity_kind together, or neither" % name)
    if kind is not None and not _is_decimal(text):
        _refuse("INVALID_CLAIM",
                "%s.value %r is not a signed decimal string while a quantity_kind is stated"
                % (name, text))
    return value


def _is_decimal(value):
    return bool(re.fullmatch(_DECIMAL, value or ""))


def validate_claim(claim):
    """One claim of the response, refused unless it is exactly the ontology's shape."""
    if type(claim) is not dict or set(claim) != set(CLAIM_KEYS):
        _refuse("INVALID_CLAIM", "a claim must be an object with exactly %s" % list(CLAIM_KEYS))
    validate_reference(claim["subject"], "subject")
    _is_choice(claim["predicate"], PREDICATES, "predicate")
    validate_object(claim["object"])
    _is_choice(claim["modality"], MODALITIES, "modality")
    _bounded_text(claim["attributed_actor"], "attributed_actor", 200)
    validate_valid_time(claim["valid_time"])
    validate_citation(claim["citation"])
    _bounded_text(claim["rationale"], "rationale", 1000)
    proposed = claim["proposed_type"]
    if proposed is not None:
        _bounded_text(proposed, "proposed_type", 100)
        if proposed in REFERENCE_TYPES:
            _refuse("INVALID_CLAIM",
                    "proposed_type %r is already one of the profile's types; name the type "
                    "in subject.type and leave proposed_type empty" % proposed)
    return claim


def validate_claim_set(data):
    """A whole response: the claims and the unknowns, exactly this shape and nothing else.

    A response with any other key, an unknown modality or predicate, a malformed
    citation or a claim count beyond the budget is refused; nothing is repaired and
    nothing is dropped silently.
    """
    if type(data) is not dict or set(data) != {"claims", "unknowns"}:
        _refuse("INVALID_RESPONSE", "a response must be an object with exactly claims and unknowns")
    claims, unknowns = data["claims"], data["unknowns"]
    if type(claims) is not list or len(claims) > MAX_CLAIMS:
        _refuse("INVALID_RESPONSE", "claims must be a list of at most %d items" % MAX_CLAIMS)
    for claim in claims:
        validate_claim(claim)
    if type(unknowns) is not list or len(unknowns) > MAX_UNKNOWNS:
        _refuse("INVALID_RESPONSE", "unknowns must be a list of at most %d items" % MAX_UNKNOWNS)
    for item in unknowns:
        _bounded_text(item, "an unknown", 800, code="INVALID_RESPONSE")
    return {"claims": [dict(claim) for claim in claims], "unknowns": list(unknowns)}


def claim_identity(claim):
    """The claim id: derived from the proposition's own content, never from a count."""
    proposition = {key: claim[key] for key in _IDENTITY_KEYS}
    return "claim:" + hashlib.sha256(canonical_bytes(proposition)).hexdigest()[:16]


def proposed_claims(claims, *, run_id):
    """Every claim as it enters: proposed, with the method and version that extracted it.

    There is no accept path here and no review-state the model can set: this function
    stamps ``review_state: "proposed"``, and the analyst's decision over the claim is a
    separate record made elsewhere.
    """
    _bounded_text(run_id, "run_id", 80, code="INVALID_RUN")
    stamped = []
    for claim in claims:
        record = dict(claim)
        record["claim_id"] = claim_identity(claim)
        record["review_state"] = PROPOSED
        record["extraction_method"] = METHOD
        record["extraction_version"] = METHOD_VERSION
        record["run_id"] = run_id
        stamped.append(record)
    return stamped


def response_schema():
    """The Gemini ``responseFormat`` schema: the same shape this module validates.

    Written once here so the model's contract and the code's contract cannot drift:
    every property, enum and required list below is the one :func:`validate_claim_set`
    enforces. Nullable fields carry ``nullable: true``, which is the response-schema
    spelling for the "or absent" choices the shape allows.
    """

    def reference(nullable=False):
        return {"type": "object", "additionalProperties": False, "nullable": nullable,
                "properties": {
                    "type": {"type": "string", "enum": list(REFERENCE_TYPES)},
                    "id": {"type": "string"},
                    "label": {"type": "string"}},
                "required": list(REFERENCE_KEYS)}

    def text_field(nullable=False):
        return {"type": "string", "nullable": nullable}

    claim = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "subject": reference(),
            "predicate": {"type": "string", "enum": list(PREDICATES)},
            "object": {"type": "object", "additionalProperties": False,
                       "properties": {
                           "reference": reference(nullable=True),
                           "value": text_field(nullable=True),
                           "unit": text_field(nullable=True),
                           "quantity_kind": text_field(nullable=True)},
                       "required": list(OBJECT_KEYS)},
            "modality": {"type": "string", "enum": list(MODALITIES)},
            "attributed_actor": {"type": "string"},
            "valid_time": {"type": "object", "additionalProperties": False,
                           "properties": {
                               "value": text_field(nullable=True),
                               "precision": {"type": "string", "nullable": True,
                                             "enum": list(TIME_PRECISIONS)},
                               "unknown_reason": text_field(nullable=True)},
                           "required": list(VALID_TIME_KEYS)},
            "citation": {"type": "object", "additionalProperties": False,
                         "properties": {
                             "source_id": {"type": "string"},
                             "source_version": {"type": "string"},
                             "start": {"type": "integer"},
                             "end": {"type": "integer"},
                             "quote": {"type": "string"}},
                         "required": list(CITATION_KEYS)},
            "rationale": {"type": "string"},
            "proposed_type": text_field(nullable=True),
        },
        "required": list(CLAIM_KEYS),
    }
    return {"type": "object", "additionalProperties": False,
            "properties": {
                "claims": {"type": "array", "items": claim},
                "unknowns": {"type": "array", "items": {"type": "string"}}},
            "required": ["claims", "unknowns"]}


#: The schema object the request's ``generationConfig`` carries.
RESPONSE_SCHEMA = response_schema()
