"""JSON-safe h0 records; exact bytes and canonical JSON have separate hashes.

New writes are the ``h0.v2`` envelope. ``h0.v1`` records stay valid under the v1
rules unchanged, so the frozen fixtures and every stored record keep validating.
h0.v2 adds three things and nothing else: the ``(synthetic, permission_ref)`` pair
that separates real records from synthetic ones, a typed ``availability_basis``
object, and the optional ``judgment_ref`` on a review decision.
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone, date
from pathlib import Path

from src.contracts.jsonutil import canonical_dumps, compute_content_digest, parse_json
from .errors import ReviewError, require

SCHEMA_VERSION = "h0.v2"
LEGACY_SCHEMA_VERSION = "h0.v1"
SCHEMA_VERSIONS = (LEGACY_SCHEMA_VERSION, SCHEMA_VERSION)
BASIS_KINDS = frozenset({"feed_logged_at", "capture_logged_at", "archive_snapshot", "attested"})
PERMISSION_DIR = ("docs", "work", "permissions")
PERMISSION_IDENTIFIER = re.compile(r"^Permission identifier[^:]*:\s*(.+)$")

#: The three h0.v2 refusals. ``errors.MESSAGES`` owns the stable h0.v1 code set and
#: is not editable from here, so these codes carry their own fixed, non-disclosing
#: text; the application's domain-error handler answers them like every other code.
V2_MESSAGES = {
    "PERMISSION_UNKNOWN": "a real record needs the non-blank identifier of a signed permission",
    "CASE_PROVENANCE_MISMATCH": "record provenance differs from its case's",
    "JUDGMENT_TASK_MISMATCH": "judgment reference does not name an artifact of the decision's task",
}

KINDS = frozenset({
    "Case", "SourceVersion", "Passage", "MappingRevision", "AssumptionRevision",
    "BeliefSnapshot", "CompiledTask", "ReviewDecision", "ScenarioProposal",
    "OutlookRevision", "DependencyImpact", "JudgmentArtifact", "ProbeBundleArtifact",
})
ENTITY_TYPES = frozenset({"Plant", "GeneratingUnit", "MarketResource", "Region", "NetworkElement"})
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
DECIMAL = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
TIME_KEYS = frozenset({"recorded_at", "reviewed_at", "created_at", "known_at", "published_at", "information_cutoff", "audit_cutoff", "start", "end"})


def json_copy(value):
    """Reject Python coercions (tuple, integer keys, subclasses, cycles), then copy."""
    def check(item):
        if type(item) in (str, int, bool, type(None)):
            return
        if type(item) is float:
            require(math.isfinite(item))
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict:
            for key, child in item.items():
                require(type(key) is str)
                check(child)
            return
        raise ReviewError("INVALID_RECORD")
    try:
        check(value)
        text = canonical_dumps(value)
        text.encode("utf-8", "strict")
        result, error = parse_json(text)
        require(error is None)
        return result
    except (ValueError, RecursionError, UnicodeError) as exc:
        if isinstance(exc, ReviewError):
            raise
        raise ReviewError("INVALID_RECORD") from None


def nonblank(value):
    return type(value) is str and bool(value.strip())


class RecordError(ReviewError):
    """An h0.v2 refusal whose text :data:`V2_MESSAGES` owns."""

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, V2_MESSAGES[code])


def require_v2(condition, code):
    """The h0.v2 conditions, as typed refusals rather than the core ``require`` codes."""
    if not condition:
        raise RecordError(code)


def provenance(payload, permissions=None, version=SCHEMA_VERSION):
    """One payload's ``(synthetic, permission_ref)`` pair, validated; the case fixes it.

    An ``h0.v2`` payload must *declare* both keys: ``synthetic`` chooses the record's
    nature and ``permission_ref`` is the evidence a real record cites, so a payload
    that omits either is refused (``INVALID_RECORD``) rather than read as a default
    it did not state. A record that declares ``synthetic: false`` must carry a
    non-blank ``permission_ref`` that the registry holds: ``null``, an unknown
    identifier and an unsigned file's identifier are all ``PERMISSION_UNKNOWN``. A
    synthetic record carrying a reference is the mixed case and is refused.
    ``permissions`` is the set the caller injected; the empty set is the honest
    default for an unsigned checkout.

    An ``h0.v1`` record predates the pair, and the v1 rules already fix every v1
    record as synthetic, so its pair reads ``(True, None)``: a v1 record can never
    be real or cite a permission.
    """
    if version == LEGACY_SCHEMA_VERSION:
        require(payload.get("synthetic", True) is True)
        return True, None
    require("synthetic" in payload and "permission_ref" in payload)
    synthetic, permission_ref = payload["synthetic"], payload["permission_ref"]
    require(type(synthetic) is bool)
    if synthetic:
        require(permission_ref is None)
    else:
        require_v2(nonblank(permission_ref), "PERMISSION_UNKNOWN")
        require_v2(permission_ref in (permissions or frozenset()), "PERMISSION_UNKNOWN")
    return synthetic, permission_ref


def typed_basis(value):
    """The h0.v2 ``availability_basis`` object; the v1 free-text string is not accepted.

    A basis records where first availability was observed, never when: it does not
    change ``known_at``, and publication is still not availability.
    """
    require(type(value) is dict and set(value) == {"basis_kind", "basis_ref", "note"})
    require(type(value["basis_kind"]) is str and value["basis_kind"] in BASIS_KINDS)
    require(nonblank(value["basis_ref"]))
    require(type(value["note"]) is str)


def _status_token(line):
    """The Status line's leading word, with Markdown emphasis dropped."""
    value = line[len("Status:"):].strip().lstrip("*_` ").strip()
    token = re.match(r"[A-Za-z]+", value)
    return token.group(0).lower() if token else ""


def load_permissions(root):
    """The identifiers of the signed permission files under ``docs/work/permissions/``.

    A file is signed when its ``Status:`` line does not read as the draft marker, so
    the drafted record is not a grant and nothing in the repository may cite it. The
    identifier is the backticked value on the file's ``Permission identifier`` line,
    with emphasis and backticks stripped; a signed file whose identifier does not
    parse contributes nothing, and citing it stays refused. The loader reads local
    files only: no network, credential or clock.
    """
    identifiers = set()
    for path in sorted(Path(root).joinpath(*PERMISSION_DIR).glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        status, identifier = None, None
        for line in text.splitlines():
            if line.startswith("Status:"):
                status = _status_token(line)
            match = PERMISSION_IDENTIFIER.match(line.strip())
            if match:
                value = match.group(1).strip()
                ticked = re.fullmatch(r"`([^`]+)`", value)
                identifier = ticked.group(1) if ticked else value.strip("*_. ")
        if identifier and status is not None and status != "draft":
            identifiers.add(identifier)
    return frozenset(identifiers)


def instant(value):
    require(type(value) is str and INSTANT.fullmatch(value), "MALFORMED_TIME")
    if not value.endswith("Z"):
        require(int(value[-5:-3]) <= 23 and int(value[-2:]) <= 59, "MALFORMED_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ReviewError("MALFORMED_TIME") from None


def temporal(value):
    if type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ReviewError("MALFORMED_TIME") from None
    return instant(value)


def interval(value):
    require(type(value) is dict and set(value) == {"start", "end"})
    start, end = temporal(value["start"]), temporal(value["end"])
    require(type(start) is type(end) and start < end, "MALFORMED_TIME")
    return start, end


def covers(outer, inner):
    a, b = interval(outer)
    c, d = interval(inner)
    return type(a) is type(c) and a <= c and d <= b


def overlaps(first, second):
    a, b = interval(first)
    c, d = interval(second)
    return type(a) is type(c) and a < d and c < b


def normalize_times(record):
    metadata = record.setdefault("time_metadata", {})
    def walk(value, path=""):
        if type(value) is dict:
            for key, child in list(value.items()):
                if key == "time_metadata":
                    continue
                loc = path + "/" + key
                if key in TIME_KEYS and child is not None and not (key in {"start", "end"} and type(child) is int):
                    parsed = temporal(child) if key in {"start", "end", "published_at"} else instant(child)
                    if type(parsed) is date:
                        normalized, precision, offset = child, "date", None
                    else:
                        normalized = parsed.isoformat().replace("+00:00", "Z")
                        precision = "fraction" if "." in child else "second"
                        offset = "Z" if child.endswith("Z") else child[-6:]
                    if loc not in metadata:
                        metadata[loc] = {"supplied": child, "precision": precision, "offset": offset}
                    value[key] = normalized
                else:
                    walk(child, loc)
        elif type(value) is list:
            for i, child in enumerate(value):
                walk(child, path + "/" + str(i))
    walk(record)
    return record


def make_record(kind, tenant_id, case_id, record_id, revision_id, recorded_at, payload, *, permissions=None):
    raw = normalize_times(json_copy({
        "schema_version": SCHEMA_VERSION, "tenant_id": tenant_id, "case_id": case_id,
        "record_kind": kind, "record_id": record_id, "revision_id": revision_id,
        "recorded_at": recorded_at, "payload": payload,
    }))
    raw["content_digest"] = compute_content_digest(raw)
    return validate_record(raw, permissions)


def reference(record):
    return {key: record[key] for key in ("record_kind", "record_id", "revision_id", "content_digest")}


def valid_ref(value, kind=None):
    require(type(value) is dict and set(value) == {"record_kind", "record_id", "revision_id", "content_digest"})
    require(type(value["record_kind"]) is str and value["record_kind"] in KINDS)
    require(kind is None or value["record_kind"] == kind)
    require(nonblank(value["record_id"]) and nonblank(value["revision_id"]))
    require(type(value["content_digest"]) is str and DIGEST.fullmatch(value["content_digest"]))


def typed_entity(value):
    require(type(value) is dict and set(value) == {"entity_id", "entity_type"})
    require(nonblank(value["entity_id"]) and type(value["entity_type"]) is str and value["entity_type"] in ENTITY_TYPES)


def quantity(value):
    require(type(value) is dict and set(value) == {"value", "quantity_kind", "unit"})
    require(type(value["value"]) is str and DECIMAL.fullmatch(value["value"]))
    require(nonblank(value["quantity_kind"]) and nonblank(value["unit"]))


def same_quantity_type(a, b):
    quantity(a)
    quantity(b)
    return a["quantity_kind"] == b["quantity_kind"] and a["unit"] == b["unit"]


def _validate_payload(kind, p, version=LEGACY_SCHEMA_VERSION, permissions=None):
    if version != LEGACY_SCHEMA_VERSION:
        # Every h0.v2 kind declares its case's pair; a payload that omits either key
        # is refused here, before any kind rule below. The v1 rules are unchanged.
        provenance(p, permissions)
    if kind == "JudgmentArtifact":
        from src.judgment import validate_answer, PROMPT_VERSION
        required = {'task_ref', 'actor_id', 'idempotency_key', 'answer', 'metadata', 'review_state', 'synthetic'}
        if version == LEGACY_SCHEMA_VERSION:
            require(set(p) == required)
        else:
            # The v2 payload declares the pair too: `permission_ref` is required, not optional.
            require(set(p) == required | {'permission_ref'})
        valid_ref(p['task_ref'], 'CompiledTask')
        require(nonblank(p['actor_id']) and nonblank(p['idempotency_key']))
        require(p['review_state'] == 'proposed')
        if version == LEGACY_SCHEMA_VERSION:
            require(p['synthetic'] is True)
        validate_answer(p['answer'])
        m = p['metadata']
        require(type(m) is dict and set(m) == {'provider', 'model', 'model_version', 'execution_mode', 'prompt_version', 'request_digest', 'output_digest'})
        require(all(nonblank(m[k]) and len(m[k]) <= 200 for k in ('provider', 'model', 'model_version')))
        require(m['execution_mode'] in ('synthetic_fixture', 'live_inference'))
        # A synthetic fixture is synthetic content; live inference is allowed for both.
        # The pair is declared on every v2 payload, so `synthetic` is present here.
        if version != LEGACY_SCHEMA_VERSION and m['execution_mode'] == 'synthetic_fixture':
            require(p['synthetic'] is True)
        require(m['prompt_version'] == PROMPT_VERSION)
        require(type(m['request_digest']) is str and DIGEST.fullmatch(m['request_digest']))
        require(m['output_digest'] == compute_content_digest(p['answer']))
    elif kind == "ProbeBundleArtifact":
        from src.judgment import LABELS, JudgmentUnavailable
        from src.judgment.bundle import RULES
        from src.judgment.systemone import validate_answers
        required = {'task_ref', 'actor_id', 'idempotency_key', 'questions', 'answers',
                    'composed', 'receipt', 'metadata', 'review_state', 'synthetic'}
        if version == LEGACY_SCHEMA_VERSION:
            require(set(p) == required)
        else:
            # The v2 payload declares the pair too: `permission_ref` is required, not optional.
            require(set(p) == required | {'permission_ref'})
        valid_ref(p['task_ref'], 'CompiledTask')
        require(nonblank(p['actor_id']) and nonblank(p['idempotency_key']) and len(p['idempotency_key']) <= 200)
        require(p['review_state'] == 'proposed')
        if version == LEGACY_SCHEMA_VERSION:
            require(p['synthetic'] is True)
        require(type(p['questions']) is dict and p['questions'])
        for name, question in p['questions'].items():
            require(nonblank(name) and len(name) <= 200)
            require(type(question) is dict and set(question) == {'type', 'form', 'instructions', 'criteria'})
            require(type(question['form']) is str and re.fullmatch(r'f[0-3]', question['form']))
            require(nonblank(question['instructions']))
        try:
            validate_answers(p['questions'], p['answers'])
        except JudgmentUnavailable:
            raise ReviewError('INVALID_RECORD') from None
        composed, stability = p['composed'], p['receipt']
        # The composition result is closed: exactly the keys ``compose`` can write, so an
        # invented key cannot ride into ``output_digest`` and an unknown rule cannot
        # silently read as "not reused" here.
        require(type(composed) is dict and set(composed) <= {
            'label', 'fired_rule', 'reason', 'atomic', 'escalation', 'thresholds', 'lineage_ref'})
        require(composed.get('label') in LABELS)
        require(type(composed.get('atomic')) is dict or composed.get('atomic') is None)
        # A label reused from an earlier bundle records that artifact, so reads enforce
        # the inherited evidence; a reuse without the reference would be provenance-free
        # and is rejected here, where the payload key set itself is frozen. The same row
        # consulted without a prior (`LINEAGE_NO_PRIOR`, a reason) reuses nothing.
        rule = composed.get('fired_rule')
        rule = rule.split(':')[0] if type(rule) is str else None
        require(rule in RULES, 'INVALID_RECORD')
        reused = rule == 'lineage_reuse' and composed.get('reason') is None
        lineage_ref = composed.get('lineage_ref')
        require(reused == (lineage_ref is not None), 'INVALID_RECORD')
        if lineage_ref is not None:
            valid_ref(lineage_ref, 'ProbeBundleArtifact')
        require(type(stability) is dict and type(stability.get('unstable')) is bool)
        require(type(stability.get('forms')) is int
                and stability['forms'] == len({question['form'] for question in p['questions'].values()}))
        m = p['metadata']
        require(type(m) is dict and set(m) == {'provider', 'model', 'model_version', 'execution_mode',
                                               'bundle_version', 'probabilities', 'request_digest', 'output_digest'})
        require(all(nonblank(m[k]) and len(m[k]) <= 200
                    for k in ('provider', 'model', 'model_version', 'bundle_version', 'probabilities')))
        require(m['execution_mode'] in ('synthetic_fixture', 'live_inference'))
        # A synthetic fixture is synthetic content, exactly as on the single judgment
        # artifact; live inference is allowed for both. The pair is declared on every
        # v2 payload, so `synthetic` is present here.
        if version != LEGACY_SCHEMA_VERSION and m['execution_mode'] == 'synthetic_fixture':
            require(p['synthetic'] is True)
        require(type(m['request_digest']) is str and DIGEST.fullmatch(m['request_digest']))
        require(m['output_digest'] == compute_content_digest(composed))
    elif kind == "Case":
        if version == LEGACY_SCHEMA_VERSION:
            require(p["synthetic"] is True)
        require(type(p["permitted_actors"]) is list and p["permitted_actors"] and all(nonblank(x) for x in p["permitted_actors"]))
        require(type(p["entities"]) is list and p["entities"])
        for entity in p["entities"]:
            typed_entity(entity)
        require(len({e["entity_id"] for e in p["entities"]}) == len(p["entities"]))
        require(type(p["representations"]) is list and p["representations"])
        for model in p["representations"]:
            require(nonblank(model["representation_id"]) and nonblank(model["model_version"]))
            require(model["target_type"] in ("GeneratingUnit", "ModeledAggregate", "MarketResource"))
            require(type(model["input_fields"]) is dict and model["input_fields"])
            for definition in model["input_fields"].values():
                require(nonblank(definition["unit"]) and nonblank(definition["quantity_kind"]))
        require(len({m["representation_id"] for m in p["representations"]}) == len(p["representations"]))
    elif kind == "SourceVersion":
        require(all(nonblank(p[k]) for k in ("source_id", "source_version", "lineage_id", "publisher", "access_policy_ref")))
        require(type(p["original_text"]) is str, "INVALID_SOURCE")
        require(hashlib.sha256(p["original_text"].encode("utf-8")).hexdigest() == p["source_byte_digest"], "INVALID_SOURCE")
        temporal(p["published_at"])
        if p["known_at"] is None:
            require(nonblank(p["unknown_reason"]))
            if version != LEGACY_SCHEMA_VERSION:
                require(p.get("availability_basis") is None)
        else:
            instant(p["known_at"])
            if version == LEGACY_SCHEMA_VERSION:
                require(nonblank(p["availability_basis"]) and p.get("unknown_reason") is None)
            else:
                typed_basis(p["availability_basis"])
                require(p.get("unknown_reason") is None)
        if p.get("copied_from") is not None:
            valid_ref(p["copied_from"], "SourceVersion")
    elif kind == "Passage":
        valid_ref(p["source_ref"], "SourceVersion")
        require(type(p["start"]) is int and type(p["end"]) is int and 0 <= p["start"] < p["end"], "INVALID_SOURCE")
        require(nonblank(p["quote"]) and hashlib.sha256(p["quote"].encode("utf-8")).hexdigest() == p["quote_digest"], "INVALID_SOURCE")
        require(nonblank(p["source_id"]) and nonblank(p["source_version"]))
        require(type(p["source_byte_digest"]) is str and DIGEST.fullmatch(p["source_byte_digest"]), "INVALID_SOURCE")
    elif kind == "MappingRevision":
        require(type(p["entities"]) is list and p["entities"])
        for entity in p["entities"]:
            typed_entity(entity)
        require(len({e["entity_id"] for e in p["entities"]}) == len(p["entities"]))
        require(nonblank(p["representation_id"]) and nonblank(p["input_field"]))
        require(p["cardinality"] in ("one_to_one", "many_to_one", "one_to_many"))
        require(p["status"] in ("reviewed", "unreviewed", "ambiguous"))
        interval(p["valid_period"])
        if p["status"] == "reviewed":
            require(nonblank(p["reviewer"]))
            instant(p["reviewed_at"])
        else:
            require(p.get("reviewer") is None and p.get("reviewed_at") is None)
        require(type(p["source_refs"]) is list and p["source_refs"])
        for ref in p["source_refs"]:
            valid_ref(ref, "SourceVersion")
    elif kind == "AssumptionRevision":
        typed_entity(p["entity"])
        quantity(p["value"])
        interval(p["valid_period"])
        require(all(nonblank(p[k]) for k in ("proposition", "representation_id", "input_field")))
        valid_ref(p["mapping_ref"], "MappingRevision")
        if p["prior_ref"] is not None:
            valid_ref(p["prior_ref"], "AssumptionRevision")
        valid_ref(p["accepted_review_ref"], "ReviewDecision")
    elif kind == "BeliefSnapshot":
        instant(p["audit_cutoff"])
        require(type(p["heads"]) is dict)
        for key, ref in p["heads"].items():
            valid_ref(ref, "AssumptionRevision")
            require(ref["record_id"] == key)
    elif kind == "CompiledTask":
        require(p["policy"] == "evidence_assumption_relation.v1")
        require(p["status"] in ("compiled", "blocked"))
        valid_ref(p["snapshot_ref"], "BeliefSnapshot")
        valid_ref(p["assumption_ref"], "AssumptionRevision")
        instant(p["information_cutoff"])
        instant(p["audit_cutoff"])
        require(type(p["dependencies"]) is list and type(p["context"]) is list)
        for ref in p["dependencies"]:
            valid_ref(ref)
        require(len(p["context"]) <= 32 and len(p["dependencies"]) <= 32)
        definition = p["assumption_definition"]
        typed_entity(definition["entity"])
        quantity(definition["value"])
        interval(definition["valid_period"])
        require(all(nonblank(definition[k]) for k in ("proposition", "representation_id", "input_field")))
        require(type(p["block_reasons"]) is list and type(p["omissions"]) is list and type(p["truncated"]) is bool)
        require((p["status"] == "blocked") == bool(p["block_reasons"]))
        require(not p["truncated"] or "TRUNCATED_CONTEXT" in p["block_reasons"])
        for item in p["context"]:
            valid_ref(item["passage_ref"], "Passage")
            valid_ref(item["source_ref"], "SourceVersion")
            require(type(item["start"]) is int and type(item["end"]) is int and 0 <= item["start"] < item["end"])
            require(nonblank(item["quote"]) and nonblank(item["lineage_id"]) and item["content_kind"] == "reported_claim")
            instant(item["known_at"])
            require(instant(item["known_at"]) <= instant(p["information_cutoff"]))
        if p["mapping_ref"] is not None:
            valid_ref(p["mapping_ref"], "MappingRevision")
        require(p["execution_mode"] == "deterministic")
        if version == LEGACY_SCHEMA_VERSION:
            require(p["synthetic"] is True)
    elif kind == "ReviewDecision":
        require(nonblank(p["actor_id"]) and nonblank(p["request_id"]) and nonblank(p["idempotency_key"]) and nonblank(p["rationale"]))
        require(p["disposition"] in ("seed", "retain", "revise", "reject", "defer", "investigate"))
        instant(p["reviewed_at"])
        if version != LEGACY_SCHEMA_VERSION and p.get("judgment_ref") is not None:
            # The validator fixes the shape; resolution and the task match are the
            # repository's, inside the review transaction.
            valid_ref(p["judgment_ref"])
        if p["disposition"] != "seed":
            valid_ref(p["task_ref"], "CompiledTask")
            valid_ref(p["snapshot_ref"], "BeliefSnapshot")
            valid_ref(p["expected_assumption_head"], "AssumptionRevision")
            if p["expected_outlook_head"] is not None:
                valid_ref(p["expected_outlook_head"], "OutlookRevision")
            require(type(p["retrospective"]) is bool)
            require((p["disposition"] == "revise") == (p["new_value"] is not None))
        else:
            if version == LEGACY_SCHEMA_VERSION:
                require(p["synthetic_initial"] is True)
            else:
                # The seed's initial-acceptance label mirrors the case's provenance:
                # only a synthetic case's initial acceptance is synthetic, and a real
                # case's seed decision is real. The pair is declared on every v2
                # payload, so `synthetic` is present here.
                require(type(p["synthetic_initial"]) is bool and p["synthetic_initial"] == p["synthetic"])
            valid_ref(p["mapping_ref"], "MappingRevision")
        if p.get("new_value") is not None:
            quantity(p["new_value"])
    elif kind == "ScenarioProposal":
        require(p["execution"] == "proposal_only" and p["comparison"] == "pending_outputs" and p["consequences"] == "uncomputed")
        valid_ref(p["snapshot_ref"], "BeliefSnapshot")
        valid_ref(p["mapping_ref"], "MappingRevision")
        valid_ref(p["decision_ref"], "ReviewDecision")
        quantity(p["delta"]["old_value"])
        quantity(p["delta"]["new_value"])
        require(same_quantity_type(p["delta"]["old_value"], p["delta"]["new_value"]))
        interval(p["delta"]["valid_period"])
        typed_entity(p["delta"]["entity"])
        require(nonblank(p["delta"]["representation_id"]) and nonblank(p["delta"]["input_field"]))
        valid_ref(p["baseline_snapshot_ref"], "BeliefSnapshot")
        valid_ref(p["old_assumption_ref"], "AssumptionRevision")
        valid_ref(p["new_assumption_ref"], "AssumptionRevision")
        require(type(p["dependencies"]) is list and len(p["dependencies"]) <= 32 and type(p["evidence"]) is list and len(p["evidence"]) <= 32)
        for ref in p["dependencies"]:
            valid_ref(ref)
        instant(p["information_cutoff"])
        instant(p["audit_cutoff"])
        if version == LEGACY_SCHEMA_VERSION:
            require(p["synthetic"] is True)
    elif kind == "OutlookRevision":
        valid_ref(p["decision_ref"], "ReviewDecision")
        require(p["state"] in ("accepted", "open"))
        require(type(p["prior_heads"]) is dict and type(p["new_heads"]) is dict)
        for heads in (p["prior_heads"], p["new_heads"]):
            for key, ref in heads.items():
                valid_ref(ref, "AssumptionRevision")
                require(key == ref["record_id"])
        if p["previous_outlook_ref"] is not None:
            valid_ref(p["previous_outlook_ref"], "OutlookRevision")
        instant(p["reviewed_at"])
        difference = p["difference"]
        require(difference["kind"] in ("revised", "no_change", "unaccepted_review"))
        typed_entity(difference["entity"])
        quantity(difference["old_value"])
        quantity(difference["new_value"])
        interval(difference["valid_period"])
        require(nonblank(difference["rationale"]) and nonblank(difference["proposition"]))
        require(type(p["open_issues"]) is list and p["consequences"] == "uncomputed")
        if version == LEGACY_SCHEMA_VERSION:
            require(p["synthetic"] is True)
    elif kind == "DependencyImpact":
        valid_ref(p["changed_ref"])
        if p["previous_ref"] is not None:
            valid_ref(p["previous_ref"])
        require(type(p["affected_drafts"]) is list and nonblank(p["reason"]))
        for ref in p["affected_drafts"]:
            valid_ref(ref)


def validate_record(raw, permissions=None):
    """Validate one envelope of either version; ``permissions`` is the injected registry."""
    record = json_copy(raw)
    try:
        require(type(record) is dict)
        require(set(record) == {"schema_version", "tenant_id", "case_id", "record_kind", "record_id", "revision_id", "recorded_at", "payload", "content_digest", "time_metadata"})
        require(record["schema_version"] in SCHEMA_VERSIONS)
        require(all(nonblank(record[k]) for k in ("tenant_id", "case_id", "record_id", "revision_id")))
        require(type(record["record_kind"]) is str and record["record_kind"] in KINDS)
        instant(record["recorded_at"])
        require(type(record["payload"]) is dict and type(record["time_metadata"]) is dict)
        require(compute_content_digest(record) == record["content_digest"])
        # Validate metadata against the normalized time, including supplied precision.
        normalized = normalize_times(json_copy({k: v for k, v in record.items() if k != "time_metadata"}))
        require(normalized["recorded_at"] == record["recorded_at"], "MALFORMED_TIME")
        require(normalized["payload"] == record["payload"], "MALFORMED_TIME")
        require(set(normalized["time_metadata"]) == set(record["time_metadata"]), "MALFORMED_TIME")
        for path, expected in normalized["time_metadata"].items():
            supplied = record["time_metadata"][path]
            require(type(supplied) is dict and set(supplied) == {"supplied", "precision", "offset"}, "MALFORMED_TIME")
            field = "published_at" if expected["precision"] == "date" else "recorded_at"
            probe = normalize_times({field: supplied["supplied"]})
            require(supplied == next(iter(probe["time_metadata"].values())), "MALFORMED_TIME")
            require(temporal(supplied["supplied"]) == temporal(expected["supplied"]), "MALFORMED_TIME")
        _validate_payload(record["record_kind"], record["payload"], record["schema_version"], permissions)
        if record["payload"].get("reviewed_at") is not None:
            require(instant(record["payload"]["reviewed_at"]) <= instant(record["recorded_at"]), "MALFORMED_TIME")
        if record["record_kind"] == "CompiledTask":
            p = record["payload"]
            require(p["task_digest"] == compute_content_digest({k: v for k, v in p.items() if k != "task_digest"}))
    except (KeyError, TypeError, UnicodeError):
        raise ReviewError("INVALID_RECORD") from None
    return record
