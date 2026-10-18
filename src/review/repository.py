"""In-memory reference adapter for H0's application and atomic-review ports.

Storage is private canonical JSON, never a caller-owned mutable object. A lock
serializes registration, dependency invalidation and review commits. ActorContext
is supplied by a trusted caller; constructing one is not authentication.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from src.contracts.jsonutil import canonical_dumps, compute_content_digest, parse_json
from .errors import ReviewError, require
from .records import (
    RecordError, covers, load_permissions, overlaps, instant, interval, json_copy, make_record,
    nonblank, provenance, quantity, reference, require_v2, same_quantity_type, valid_ref,
    validate_record, normalize_times, typed_entity,
)

#: The checkout's permission registry, read once at import: the signed files under
#: ``docs/work/permissions/``. A drafted file is not a grant, so until the owner signs
#: one this set is empty and no real record validates anywhere in this checkout. Tests
#: inject their own registry into the service they build.
DEFAULT_PERMISSIONS = load_permissions(Path(__file__).resolve().parents[2])

POLICY = {
    "id": "evidence_assumption_relation.v1",
    "labels": ["supports", "challenges", "mixed", "unrelated", "insufficient"],
    "definitions": {
        "supports": "Consistent with and directly relevant to the proposition.",
        "challenges": "Relevant reason to reconsider; does not establish falsity.",
        "mixed": "Supported elements pull in different directions.",
        "unrelated": "Does not bear on the proposition under the declared scope.",
        "insufficient": "Necessary meaning or context is missing.",
    },
    "max_passages": 32, "max_dependency_nodes": 32,
    "availability": "strict_known_then", "execution_mode": "deterministic",
}


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    tenant_id: str
    accessible_cases: frozenset[str]
    source_policy_refs: frozenset[str]
    can_review: bool

    def __post_init__(self):
        require(nonblank(self.actor_id) and nonblank(self.tenant_id), "ACCESS_DENIED")
        require(type(self.accessible_cases) is frozenset and type(self.source_policy_refs) is frozenset, "ACCESS_DENIED")
        require(all(nonblank(x) for x in self.accessible_cases | self.source_policy_refs), "ACCESS_DENIED")
        require(type(self.can_review) is bool, "ACCESS_DENIED")


def _key(tenant, case, ref):
    return tenant, case, ref["record_kind"], ref["record_id"], ref["revision_id"]


def _logical(record):
    return record["tenant_id"], record["case_id"], record["record_kind"], record["record_id"]


def _sort_ref(ref):
    return ref["record_kind"], ref["record_id"], ref["revision_id"], ref["content_digest"]


#: The three ports a prepared provisioning batch may call. A batch is one way of making the
#: existing calls, not a wider authority: it may write a case and its evidence registration,
#: and it can reach no port that compiles a task, commits a review or reads private state.
PROVISION_PORTS = ("register_case", "register", "seed_assumption")


def apply_operations(service, actor, operations):
    """Apply one prepared batch of seeding operations to one service, in order.

    ``operations`` is an ordered sequence of ``(method, args, kwargs)`` triples naming the
    ports in `PROVISION_PORTS`. Each is called against ``service`` with the batch's actor
    exactly as a caller makes it alone, so every guard inside every port runs unchanged; this
    function only sequences them and returns the results in the same order. It stores
    nothing: the caller decides whether ``service`` is in-memory state or the decoded copy a
    storage step will commit once.
    """
    results = []
    for method, args, kwargs in operations:
        require(method in PROVISION_PORTS, "ACCESS_DENIED")
        results.append(getattr(service, method)(actor, *args, **kwargs))
    return results


#: One decision's preparation in one call (`prepare_task` below). The pair route set the
#: precedent (`src/review/pairing.py`): an operation's own refusals are typed, and their
#: codes live with the operation, not in `src/review/errors.MESSAGES`, which owns the
#: stable h0.v1 set.
PREPARE_ASSUMPTION_COUNT = 'PREPARE_ASSUMPTION_COUNT'
PREPARE_MESSAGES = {
    PREPARE_ASSUMPTION_COUNT: 'the accepted state does not hold exactly one assumption for this decision',
}


class PrepareError(ReviewError):
    """A typed refusal of a prepared decision, carrying no record content.

    A ``ReviewError`` so the application's existing handler answers it as ``{'code': code}``,
    with a message from :data:`PREPARE_MESSAGES` rather than the frozen core set; no code
    here discloses record content.
    """

    def __init__(self, code):
        self.code = code
        ValueError.__init__(self, PREPARE_MESSAGES[code])


class ReviewService:
    def __init__(self, permissions=None):
        self._lock = RLock()
        self._permissions = DEFAULT_PERMISSIONS if permissions is None else frozenset(permissions)
        self._records = {}
        self._latest = {}
        self._cases = {}
        self._heads = {}
        self._outlooks = {}
        self._history = {}
        self._receipts = {}
        self._stale = {}

    def _pair(self, tenant, case):
        """The case's ``(synthetic, permission_ref)`` pair; the case fixes it for the case.

        The pair is read under the case's own envelope rules: a v1 case predates the
        pair and is synthetic by definition, a v2 case declares it explicitly.
        """
        case_record = self._lookup(tenant, case, self._cases[(tenant, case)])
        return provenance(case_record["payload"], self._permissions, case_record["schema_version"])

    def _record(self, kind, tenant, case, ident, revision, recorded_at, payload):
        """One new record through the frozen envelope, under this service's registry."""
        return make_record(kind, tenant, case, ident, revision, recorded_at, payload,
                           permissions=self._permissions)

    def _pair_fields(self, tenant, case):
        """The two provenance keys every derived write copies from its case."""
        synthetic, permission_ref = self._pair(tenant, case)
        return {"synthetic": synthetic, "permission_ref": permission_ref}

    def _check_provenance(self, record):
        """A record carries its case's pair; the case is wholly real or wholly synthetic."""
        if record["record_kind"] == "Case":
            return
        scope = (record["tenant_id"], record["case_id"])
        require(scope in self._cases, "MISSING_INPUT")
        pair = provenance(record["payload"], self._permissions, record["schema_version"])
        require_v2(pair == self._pair(*scope), "CASE_PROVENANCE_MISMATCH")

    def _lookup(self, tenant, case, ref):
        valid_ref(ref)
        text = self._records.get(_key(tenant, case, ref))
        require(text is not None, "MISSING_INPUT")
        record, _ = parse_json(text)
        require(record["content_digest"] == ref["content_digest"], "INVALID_RECORD")
        return record

    def _check_case(self, actor, case):
        require(isinstance(actor, ActorContext), "ACCESS_DENIED")
        require(nonblank(case), "ACCESS_DENIED")
        require(case in actor.accessible_cases, "ACCESS_DENIED")
        ref = self._cases.get((actor.tenant_id, case))
        require(ref is not None, "ACCESS_DENIED")
        record = self._lookup(actor.tenant_id, case, ref)
        require(actor.actor_id in record["payload"]["permitted_actors"], "ACCESS_DENIED")
        return record

    def _check_source(self, actor, source):
        require(source["payload"]["access_policy_ref"] in actor.source_policy_refs, "ACCESS_DENIED")

    def _access_record(self, actor, case, record, seen=None):
        """Transitive permission check, including old snapshots/receipts after revocation."""
        seen = set() if seen is None else seen
        records = [record]
        while records:
            current = records.pop()
            identity = _key(actor.tenant_id, case, reference(current))
            if identity in seen:
                continue
            seen.add(identity)
            if current["record_kind"] == "SourceVersion":
                self._check_source(actor, current)
            values = [current["payload"]]
            while values:
                value = values.pop()
                if type(value) is dict:
                    if set(value) == {"record_kind", "record_id", "revision_id", "content_digest"}:
                        records.append(self._lookup(actor.tenant_id, case, value))
                    else:
                        values.extend(value.values())
                elif type(value) is list:
                    values.extend(value)

    def _preflight(self, records):
        pending = {}
        for raw in records:
            record = validate_record(raw, self._permissions)
            self._check_provenance(record)
            key = _key(record["tenant_id"], record["case_id"], reference(record))
            text = canonical_dumps(record)
            existing = pending.get(key, self._records.get(key))
            require(existing is None or existing == text, "REVISION_CONFLICT")
            pending[key] = text
        return pending

    def _write(self, records):
        # All validation/conflict checks happen before the first write.
        pending = self._preflight(records)
        self._records.update(pending)
        for record in records:
            self._latest[_logical(record)] = reference(record)

    def provision(self, actor, case, operations):
        """Apply a prepared provisioning batch to this service, in order.

        The in-memory half of the provisioning port: `PersistentRepository.provision` has
        this exact signature and applies the same operations to the decoded service inside
        one storage step. A caller can therefore seed a case identically through a plain
        service (fixtures, scripts, tests) and through a store, and the only difference is
        where the resulting state lives. ``case`` repeats the scope the operations carry.
        """
        require(type(case) is str and bool(case.strip()), "ACCESS_DENIED")
        return apply_operations(self, actor, operations)

    def read(self, actor, case, ref):
        with self._lock:
            self._check_case(actor, case)
            valid_ref(ref)
            text = self._records.get(_key(actor.tenant_id, case, ref))
            require(text is not None, "ACCESS_DENIED")
            record, _ = parse_json(text)
            self._access_record(actor, case, record)
            require(record["content_digest"] == ref["content_digest"])
            return record

    def register_case(self, actor, record):
        with self._lock:
            require(isinstance(actor, ActorContext), "ACCESS_DENIED")
            require(actor.can_review, "ACCESS_DENIED")
            require(type(record) is dict and record.get("tenant_id") == actor.tenant_id and nonblank(record.get("case_id")) and record.get("case_id") in actor.accessible_cases, "ACCESS_DENIED")
            record = validate_record(record, self._permissions)
            require(record["record_kind"] == "Case")
            require(actor.actor_id in record["payload"]["permitted_actors"] and actor.can_review, "ACCESS_DENIED")
            scope = actor.tenant_id, record["case_id"]
            existing = self._cases.get(scope)
            require(existing is None or existing == reference(record), "REVISION_CONFLICT")
            self._write([record])
            self._cases[scope] = reference(record)
            self._heads.setdefault(scope, {})
            self._outlooks.setdefault(scope, None)
            self._history.setdefault(scope, [])
            return json_copy(record)

    def _bind_mapping(self, case_record, mapping):
        p, c = mapping["payload"], case_record["payload"]
        require(all(e in c["entities"] for e in p["entities"]), "UNRESOLVED_MAPPING")
        models = [m for m in c["representations"] if m["representation_id"] == p["representation_id"]]
        require(len(models) == 1 and p["input_field"] in models[0]["input_fields"], "UNRESOLVED_MAPPING")
        model = models[0]
        if p["cardinality"] == "one_to_one":
            require(len(p["entities"]) == 1 and p["entities"][0]["entity_type"] == model["target_type"], "UNRESOLVED_MAPPING")
        elif p["cardinality"] == "many_to_one":
            require(len(p["entities"]) >= 2 and model["target_type"] == "ModeledAggregate", "UNRESOLVED_MAPPING")
        else:
            # The H0 field contract has one target; fan-out needs an explicit later contract.
            raise ReviewError("UNRESOLVED_MAPPING")
        return model["input_fields"][p["input_field"]]

    def register(self, actor, record, *, source_bytes=None):
        """Register evidence/mappings only. Review/accepted state has dedicated ports."""
        with self._lock:
            case_id = record.get("case_id") if type(record) is dict else None
            case_record = self._check_case(actor, case_id)
            require(record.get("tenant_id") == actor.tenant_id, "ACCESS_DENIED")
            if record.get("record_kind") == "SourceVersion":
                policy = record.get("payload", {}).get("access_policy_ref") if type(record.get("payload")) is dict else None
                require(nonblank(policy) and policy in actor.source_policy_refs, "ACCESS_DENIED")
            record = validate_record(record, self._permissions)
            self._check_provenance(record)
            kind, p = record["record_kind"], record["payload"]
            require(kind in ("SourceVersion", "Passage", "MappingRevision"))
            if kind == "SourceVersion":
                self._check_source(actor, record)
                require(type(source_bytes) is bytes, "INVALID_SOURCE")
                try:
                    require(source_bytes.decode("utf-8", "strict") == p["original_text"], "INVALID_SOURCE")
                except UnicodeError:
                    raise ReviewError("INVALID_SOURCE") from None
                require(hashlib.sha256(source_bytes).hexdigest() == p["source_byte_digest"], "INVALID_SOURCE")
                require(p["source_id"] == record["record_id"] and p["source_version"] == record["revision_id"], "INVALID_SOURCE")
                if p.get("copied_from") is not None:
                    original = self._lookup(actor.tenant_id, case_id, p["copied_from"])
                    self._access_record(actor, case_id, original)
                    require(original["payload"]["lineage_id"] == p["lineage_id"], "INVALID_SOURCE")
                    if p["known_at"] is not None and original["payload"]["known_at"] is not None:
                        require(instant(p["known_at"]) >= instant(original["payload"]["known_at"]), "INVALID_SOURCE")
            elif kind == "Passage":
                source = self._lookup(actor.tenant_id, case_id, p["source_ref"])
                self._access_record(actor, case_id, source)
                s = source["payload"]
                require(p["end"] <= len(s["original_text"]) and s["original_text"][p["start"]:p["end"]] == p["quote"], "INVALID_SOURCE")
                require(all(p[k] == s[k] for k in ("source_id", "source_version", "source_byte_digest")), "INVALID_SOURCE")
            else:
                if p["status"] == "reviewed":
                    require(actor.can_review and p["reviewer"] == actor.actor_id, "ACCESS_DENIED")
                    require(instant(p["reviewed_at"]) <= instant(record["recorded_at"]), "MALFORMED_TIME")
                self._bind_mapping(case_record, record)
                self._access_record(actor, case_id, record)
            prior = self._latest.get(_logical(record))
            if _key(actor.tenant_id, case_id, reference(record)) in self._records:
                self._preflight([record])
                return json_copy(record)  # old identical registration cannot reset latest
            impact = None
            affected = []
            if prior is not None or kind == "MappingRevision":
                for draft in self._records_in(actor.tenant_id, case_id):
                    if draft["record_kind"] not in ("CompiledTask", "ScenarioProposal"):
                        continue
                    changed_mapping = False
                    if kind == "MappingRevision":
                        assumption_ref = draft["payload"].get("assumption_ref", draft["payload"].get("new_assumption_ref"))
                        assumption = self._lookup(actor.tenant_id, case_id, assumption_ref)["payload"]
                        changed_mapping = p["representation_id"] == assumption["representation_id"] and p["input_field"] == assumption["input_field"] and assumption["entity"] in p["entities"] and overlaps(p["valid_period"], assumption["valid_period"])
                    if (prior is not None and prior in self._draft_dependencies(draft)) or changed_mapping:
                        affected.append(reference(draft))
                if prior is not None or affected:
                    impact = self._record("DependencyImpact", actor.tenant_id, case_id,
                        "impact:" + record["content_digest"], "1", record["recorded_at"], {
                            "changed_ref": reference(record), "previous_ref": prior,
                            "affected_drafts": sorted(affected, key=_sort_ref),
                            "reason": "Dependency revision or overlapping mapping changed; draft requires refresh.",
                            **self._pair_fields(actor.tenant_id, case_id),
                        })
            self._write([record] + ([impact] if impact else []))
            for ref in affected:
                self._stale[_key(actor.tenant_id, case_id, ref)] = "STALE_DEPENDENCY"
            return json_copy(record)

    def _records_in(self, tenant, case, kind=None):
        return [parse_json(text)[0] for key, text in sorted(self._records.items())
                if key[:2] == (tenant, case) and (kind is None or key[2] == kind)]

    def _draft_dependencies(self, draft):
        p = draft["payload"]
        spans = p.get("context", p.get("evidence", []))
        return p.get("dependencies", []) + [item["passage_ref"] for item in spans]

    def _source_dependencies(self, tenant, case, ref):
        dependencies = []
        while ref is not None:
            dependencies.append(ref)
            source = self._lookup(tenant, case, ref)
            ref = source["payload"].get("copied_from")
        return dependencies

    def seed_assumption(self, actor, record_id, revision_id, recorded_at, payload, rationale):
        """Explicit initial acceptance, requiring trusted review capability.

        The seed decision's ``synthetic_initial`` label mirrors the case's provenance
        through the case's pair: it reads true only on a synthetic case, and a real
        case's seed is real like every record that case holds.
        """
        with self._lock:
            case = payload.get("case_id") if type(payload) is dict else None
            case_record = self._check_case(actor, case)
            require(actor.can_review, "ACCESS_DENIED")
            payload = json_copy(payload)
            require(type(payload) is dict and set(payload) == {"case_id", "entity", "proposition", "value", "valid_period", "representation_id", "input_field", "mapping_ref"})
            payload.pop("case_id")
            require(nonblank(rationale))
            valid_ref(payload["mapping_ref"], "MappingRevision")
            typed_entity(payload["entity"])
            quantity(payload["value"])
            interval(payload["valid_period"])
            mapping = self._lookup(actor.tenant_id, case, payload["mapping_ref"])
            self._access_record(actor, case, mapping)
            field = self._bind_mapping(case_record, mapping)
            require(mapping["payload"]["status"] == "reviewed" and covers(mapping["payload"]["valid_period"], payload["valid_period"]), "UNRESOLVED_MAPPING")
            require(instant(mapping["recorded_at"]) <= instant(recorded_at) and instant(mapping["payload"]["reviewed_at"]) <= instant(recorded_at), "MALFORMED_TIME")
            require(payload["entity"] in mapping["payload"]["entities"] and payload["representation_id"] == mapping["payload"]["representation_id"] and payload["input_field"] == mapping["payload"]["input_field"], "UNRESOLVED_MAPPING")
            quantity(payload["value"])
            require(field == {k: payload["value"][k] for k in ("unit", "quantity_kind")}, "UNRESOLVED_MAPPING")
            pair = self._pair_fields(actor.tenant_id, case)
            decision = self._record("ReviewDecision", actor.tenant_id, case, "seed:" + record_id, revision_id, recorded_at, {
                "actor_id": actor.actor_id, "request_id": "seed:" + record_id,
                "idempotency_key": "seed:" + record_id, "disposition": "seed",
                "rationale": rationale, "reviewed_at": recorded_at,
                "synthetic_initial": pair["synthetic"],
                "mapping_ref": reference(mapping), "judgment_ref": None,
                **pair,
            })
            payload.update(prior_ref=None, accepted_review_ref=reference(decision), **pair)
            assumption = self._record("AssumptionRevision", actor.tenant_id, case, record_id, revision_id, recorded_at, payload)
            scope = actor.tenant_id, case
            head = self._heads[scope].get(record_id)
            require(head is None or head == reference(assumption), "REVISION_CONFLICT")
            self._write([decision, assumption])
            self._heads[scope][record_id] = reference(assumption)
            return json_copy(assumption)

    def heads(self, actor, case):
        with self._lock:
            self._check_case(actor, case)
            result = {"assumptions": self._heads[(actor.tenant_id, case)], "outlook": self._outlooks[(actor.tenant_id, case)]}
            for ref in result["assumptions"].values():
                self._access_record(actor, case, self._lookup(actor.tenant_id, case, ref))
            if result["outlook"] is not None:
                self._access_record(actor, case, self._lookup(actor.tenant_id, case, result["outlook"]))
            return json_copy(result)

    def build_snapshot(self, actor, case, audit_cutoff, recorded_at):
        with self._lock:
            snapshot = self._snapshot_record(actor, case, audit_cutoff, recorded_at)
            self._write([snapshot])
            return snapshot

    def _snapshot_record(self, actor, case, audit_cutoff, recorded_at):
        with self._lock:
            self._check_case(actor, case)
            cutoff = instant(audit_cutoff)
            require(cutoff <= instant(recorded_at), "MALFORMED_TIME")
            heads = {}
            for assumption in self._records_in(actor.tenant_id, case, "AssumptionRevision"):
                p = assumption["payload"]
                decision = self._lookup(actor.tenant_id, case, p["accepted_review_ref"])
                if all(instant(t) <= cutoff for t in (assumption["recorded_at"], decision["recorded_at"], decision["payload"]["reviewed_at"])):
                    old = heads.get(assumption["record_id"])
                    if old is None or instant(assumption["recorded_at"]) > instant(old["recorded_at"]) or p["prior_ref"] == reference(old):
                        heads[assumption["record_id"]] = assumption
            manifest = {key: reference(value) for key, value in sorted(heads.items())}
            for assumption in heads.values():
                self._access_record(actor, case, assumption)
            payload = {"heads": manifest, "audit_cutoff": audit_cutoff,
                       **self._pair_fields(actor.tenant_id, case)}
            snap_id = "snapshot:" + compute_content_digest({"payload": payload, "recorded_at": recorded_at})
            snapshot = self._record("BeliefSnapshot", actor.tenant_id, case, snap_id, "1", recorded_at, payload)
            return snapshot

    def _mapping_status(self, actor, case_record, assumption, audit_cutoff, information_cutoff):
        p = assumption["payload"]
        candidates = []
        for mapping in self._records_in(actor.tenant_id, assumption["case_id"], "MappingRevision"):
            m = mapping["payload"]
            if self._latest.get(_logical(mapping)) != reference(mapping):
                continue
            try:
                self._access_record(actor, assumption["case_id"], mapping)
            except ReviewError as exc:
                if exc.code == "ACCESS_DENIED":
                    continue
                raise
            if m["representation_id"] == p["representation_id"] and m["input_field"] == p["input_field"] and p["entity"] in m["entities"] and overlaps(m["valid_period"], p["valid_period"]):
                candidates.append(mapping)
        if len(candidates) > 1:
            return None, "AMBIGUOUS_MAPPING"
        if not candidates:
            return None, "UNRESOLVED_MAPPING"
        mapping = candidates[0]
        m = mapping["payload"]
        if m["status"] != "reviewed" or not covers(m["valid_period"], p["valid_period"]) or instant(m["reviewed_at"]) > instant(audit_cutoff) or instant(mapping["recorded_at"]) > instant(audit_cutoff):
            return mapping, "UNRESOLVED_MAPPING"
        for ref in m["source_refs"]:
            source = self._lookup(actor.tenant_id, assumption["case_id"], ref)
            known = source["payload"]["known_at"]
            if known is None or instant(known) > instant(information_cutoff):
                return mapping, "UNRESOLVED_MAPPING"
        field = self._bind_mapping(case_record, mapping)
        if field != {k: p["value"][k] for k in ("unit", "quantity_kind")}:
            return mapping, "UNRESOLVED_MAPPING"
        return mapping, None

    def compile_task(self, actor, case, snapshot_ref, assumption_id, information_cutoff, recorded_at, *, passage_ids=None):
        with self._lock:
            case_record = self._check_case(actor, case)
            cutoff = instant(information_cutoff)
            require(cutoff <= instant(recorded_at), "MALFORMED_TIME")
            require(nonblank(assumption_id))
            if passage_ids is not None:
                require(type(passage_ids) is list and all(nonblank(x) for x in passage_ids) and len(set(passage_ids)) == len(passage_ids))
            snapshot = self._lookup(actor.tenant_id, case, snapshot_ref)
            require(snapshot["record_kind"] == "BeliefSnapshot")
            self._access_record(actor, case, snapshot)
            require(instant(snapshot["recorded_at"]) <= instant(recorded_at), "MALFORMED_TIME")
            audit = snapshot["payload"]["audit_cutoff"]
            ref = snapshot["payload"]["heads"].get(assumption_id)
            require(ref is not None, "MISSING_INPUT")
            assumption = self._lookup(actor.tenant_id, case, ref)
            mapping, mapping_error = self._mapping_status(actor, case_record, assumption, audit, information_cutoff)
            dependencies = {canonical_dumps(reference(case_record)): reference(case_record), canonical_dumps(ref): ref}
            for accepted_ref in snapshot["payload"]["heads"].values():
                dependencies[canonical_dumps(accepted_ref)] = accepted_ref
            if mapping:
                dependencies[canonical_dumps(reference(mapping))] = reference(mapping)
                for support in mapping["payload"]["source_refs"]:
                    for dep in self._source_dependencies(actor.tenant_id, case, support):
                        dependencies[canonical_dumps(dep)] = dep
            context, omissions, groups = [], [], {}
            for passage in self._records_in(actor.tenant_id, case, "Passage"):
                if self._latest.get(_logical(passage)) != reference(passage):
                    continue
                if passage_ids is not None and passage["record_id"] not in passage_ids:
                    continue
                source = self._lookup(actor.tenant_id, case, passage["payload"]["source_ref"])
                try:
                    self._access_record(actor, case, source)
                except ReviewError as exc:
                    if exc.code == "ACCESS_DENIED":
                        continue
                    raise
                s = source["payload"]
                reason = "UNKNOWN_AVAILABILITY" if s["known_at"] is None else ("LATER_AVAILABILITY" if instant(s["known_at"]) > cutoff else None)
                if reason:
                    omissions.append({"passage_ref": reference(passage), "code": reason})
                    continue
                context.append({"passage_ref": reference(passage), "source_ref": reference(source),
                    "quote": passage["payload"]["quote"], "start": passage["payload"]["start"], "end": passage["payload"]["end"],
                    "source_byte_digest": s["source_byte_digest"], "published_at": s["published_at"],
                    "known_at": s["known_at"], "publisher": s["publisher"], "lineage_id": s["lineage_id"],
                    "content_kind": "reported_claim"})
                groups.setdefault(s["lineage_id"], []).append(reference(source))
                # Passages have their own 32-item context budget; dependency nodes
                # are the source/mapping/assumption/case traversal, not duplicate spans.
                for dep in self._source_dependencies(actor.tenant_id, case, reference(source)):
                    dependencies[canonical_dumps(dep)] = dep
            reasons = [mapping_error] if mapping_error else []
            if not context:
                reasons.append("MISSING_INPUT")
            if self._heads[(actor.tenant_id, case)] != snapshot["payload"]["heads"]:
                reasons.append("STALE_HEAD")
            truncated = len(context) > POLICY["max_passages"] or len(dependencies) > POLICY["max_dependency_nodes"]
            if truncated:
                reasons.append("TRUNCATED_CONTEXT")
            dep_list = sorted(dependencies.values(), key=_sort_ref)
            if any(self._latest.get((actor.tenant_id, case, d["record_kind"], d["record_id"])) != d for d in dep_list):
                reasons.append("STALE_DEPENDENCY")
            payload = {
                "policy": POLICY["id"], "original_definitions": POLICY,
                "status": "blocked" if reasons else "compiled", "block_reasons": sorted(set(reasons)),
                "snapshot_ref": reference(snapshot), "assumption_ref": ref,
                "mapping_ref": reference(mapping) if mapping else None,
                "assumption_definition": {k: assumption["payload"][k] for k in (
                    "entity", "proposition", "value", "valid_period", "representation_id", "input_field")},
                "mapping_definition": mapping["payload"] if mapping else None,
                "model_representation": next(model for model in case_record["payload"]["representations"]
                    if model["representation_id"] == assumption["payload"]["representation_id"]),
                "information_cutoff": information_cutoff, "audit_cutoff": audit,
                "context": context[:32], "dependencies": dep_list[:32],
                "omissions": omissions, "truncated": truncated,
                "permitted_counts": {"passages": len(context), "dependency_nodes": len(dep_list)},
                "lineage_groups": [{"lineage_id": key, "source_refs": sorted({canonical_dumps(r): r for r in refs}.values(), key=_sort_ref)} for key, refs in sorted(groups.items())],
                "access_scope": {"tenant_id": actor.tenant_id, "case_id": case, "actor_id": actor.actor_id,
                    "source_policies": sorted({self._lookup(actor.tenant_id, case, item["source_ref"])["payload"]["access_policy_ref"] for item in context})},
                **self._pair_fields(actor.tenant_id, case),
                "execution_mode": "deterministic", "candidate": None,
            }
            normalized_payload = normalize_times({"payload": json_copy(payload)})["payload"]
            payload["task_digest"] = compute_content_digest(normalized_payload)
            task = self._record("CompiledTask", actor.tenant_id, case, "task:" + payload["task_digest"], compute_content_digest({"recorded_at": recorded_at}), recorded_at, payload)
            self._write([task])
            return task

    def prepare_task(self, actor, case, audit_cutoff, information_cutoff, recorded_at):
        """One decision's whole preparation: the heads, the snapshot and the compiled task.

        The three operations the event page used to make as three round trips happen here
        under one lock: the case heads, `build_snapshot` at the audit cutoff (the instant of
        the accepted state the decision audits) and `compile_task` at the information cutoff
        (the event's own recorded posting time, which never moves). Nothing is relaxed: each
        operation runs its own guards unchanged and writes the same records with the same
        identities, so the answer is the objects the three calls return. The review that
        follows still carries `expected_assumption_head`, `expected_outlook_head` and
        `snapshot_digest`, so `commit_review` re-checks the stale-head and dependency
        conditions when the decision is actually posted.

        The assumption compiled is the snapshot's own single accepted head. A state that does
        not hold exactly one is refused with `PREPARE_ASSUMPTION_COUNT` before anything is
        written: which assumption a decision is about is input the caller would otherwise be
        guessing, and `compile_task` has to be told one.
        """
        with self._lock:
            heads = self.heads(actor, case)
            snapshot = self._snapshot_record(actor, case, audit_cutoff, recorded_at)
            accepted = snapshot["payload"]["heads"]
            if len(accepted) != 1:
                raise PrepareError(PREPARE_ASSUMPTION_COUNT)
            self._write([snapshot])
            task = self.compile_task(actor, case, reference(snapshot), next(iter(accepted)),
                                     information_cutoff, recorded_at)
            return {"heads": heads, "snapshot": json_copy(snapshot), "task": json_copy(task)}

    def draft_status(self, actor, case, ref):
        with self._lock:
            record = self.read(actor, case, ref)
            require(record["record_kind"] in ("CompiledTask", "ScenarioProposal"))
            return {"status": "stale" if _key(actor.tenant_id, case, ref) in self._stale else "current"}

    def judgment_input(self, actor, case, task_ref, key):
        """Replays are readable history; new model work requires a current task."""
        with self._lock:
            task = self.read(actor, case, task_ref)
            require(task['record_kind'] == 'CompiledTask')
            require(task['payload']['access_scope']['actor_id'] == actor.actor_id, 'ACCESS_DENIED')
            require(nonblank(key) and len(key) <= 200)
            ident = 'judgment:' + compute_content_digest({'actor': actor.actor_id, 'key': key})
            prior_ref = self._latest.get((actor.tenant_id, case, 'JudgmentArtifact', ident))
            if prior_ref:
                prior = self.read(actor, case, prior_ref)
                require(prior['payload']['task_ref'] == task_ref, 'IDEMPOTENCY_CONFLICT')
                return prior, task
            p = task['payload']
            require(p['status'] == 'compiled', 'BLOCKED_TASK')
            snapshot = self._lookup(actor.tenant_id, case, p['snapshot_ref'])
            require(self._heads[(actor.tenant_id, case)] == snapshot['payload']['heads'], 'STALE_HEAD')
            require(self.draft_status(actor, case, task_ref)['status'] == 'current', 'STALE_DEPENDENCY')
            for dep in self._draft_dependencies(task):
                require(self._latest.get((actor.tenant_id, case, dep['record_kind'], dep['record_id'])) == dep, 'STALE_DEPENDENCY')
            return None, task

    def save_judgment(self, actor, case, task_ref, key, answer, metadata, recorded_at):
        from src.judgment import validate_answer
        with self._lock:
            prior, task = self.judgment_input(actor, case, task_ref, key)
            if prior is not None:
                return prior
            require(instant(recorded_at) >= instant(task['recorded_at']), 'MALFORMED_TIME')
            validate_answer(answer, task['payload']['context'])
            ident = 'judgment:' + compute_content_digest({'actor': actor.actor_id, 'key': key})
            record = self._record('JudgmentArtifact', actor.tenant_id, case, ident, '1', recorded_at, {
                'task_ref': task_ref, 'actor_id': actor.actor_id, 'idempotency_key': key,
                'answer': answer, 'metadata': metadata, 'review_state': 'proposed',
                **self._pair_fields(actor.tenant_id, case)})
            self._write([record])
            return json_copy(record)

    def bundle_input(self, actor, case, task_ref, key):
        """Replays are readable history; new probe work requires a current task.

        Identical guards to ``judgment_input``: the same task access, compilation
        status, latest revision, live heads and live dependencies, checked before any
        backend can be reached. The artifact identity is actor-scoped by the key.
        """
        with self._lock:
            task = self.read(actor, case, task_ref)
            require(task['record_kind'] == 'CompiledTask')
            require(task['payload']['access_scope']['actor_id'] == actor.actor_id, 'ACCESS_DENIED')
            require(nonblank(key) and len(key) <= 200)
            ident = 'probe:' + compute_content_digest({'actor': actor.actor_id, 'key': key})
            prior_ref = self._latest.get((actor.tenant_id, case, 'ProbeBundleArtifact', ident))
            if prior_ref:
                prior = self.read(actor, case, prior_ref)
                require(prior['payload']['task_ref'] == task_ref, 'IDEMPOTENCY_CONFLICT')
                return prior, task
            p = task['payload']
            require(p['status'] == 'compiled', 'BLOCKED_TASK')
            snapshot = self._lookup(actor.tenant_id, case, p['snapshot_ref'])
            require(self._heads[(actor.tenant_id, case)] == snapshot['payload']['heads'], 'STALE_HEAD')
            require(self.draft_status(actor, case, task_ref)['status'] == 'current', 'STALE_DEPENDENCY')
            for dep in self._draft_dependencies(task):
                require(self._latest.get((actor.tenant_id, case, dep['record_kind'], dep['record_id'])) == dep, 'STALE_DEPENDENCY')
            return None, task

    def bundle_lineage_prior(self, actor, case, task_ref):
        """The earlier bundle a repeated source gives the composition: label and artifact.

        A qualifying prior is a saved ``ProbeBundleArtifact``, readable by this actor
        transitively, on a *different* ``CompiledTask`` for the same assumption (the
        same ``assumption_ref`` record) whose context carries a source in a lineage
        group the current task's context also carries: the current passages repeat
        evidence that task already covered. "Different" is logical identity, as
        ``_logical`` records it: a recompile of the identical task is a new revision of
        the same task, not an earlier source, so it cannot supply its own label back.
        Its task's ``information_cutoff`` must be at or before this task's cutoff,
        because a bundle composed from evidence a later
        cutoff saw cannot decide an earlier task; of the qualifying priors the one at
        the greatest such cutoff wins (the most recent earlier evidence), with its
        recorded time and its record id breaking ties, so the answer is deterministic.
        Its ``composed`` label answers the composition's ``lineage_reuse`` row and the
        returned ``ref`` is what the artifact records as its inherited dependency. An
        artifact the actor cannot read is absent, not an error and never a leak.
        """
        with self._lock:
            task = self.read(actor, case, task_ref)
            require(task['record_kind'] == 'CompiledTask')
            lineages = {group['lineage_id'] for group in task['payload']['lineage_groups']}
            if not lineages:
                return None
            cutoff = instant(task['payload']['information_cutoff'])
            qualifying = []
            for record in self._records_in(actor.tenant_id, case, 'ProbeBundleArtifact'):
                if self._latest.get(_logical(record)) != reference(record):
                    continue
                try:
                    self._access_record(actor, case, record)
                except ReviewError as exc:
                    if exc.code in ('ACCESS_DENIED', 'MISSING_INPUT'):
                        continue
                    raise
                prior_task = self._lookup(actor.tenant_id, case, record['payload']['task_ref'])
                if prior_task['record_kind'] != 'CompiledTask' or _logical(prior_task) == _logical(task):
                    continue
                if prior_task['payload']['assumption_ref']['record_id'] != task['payload']['assumption_ref']['record_id']:
                    continue
                prior_cutoff = instant(prior_task['payload']['information_cutoff'])
                if prior_cutoff > cutoff:
                    continue
                if lineages & {group['lineage_id'] for group in prior_task['payload']['lineage_groups']}:
                    qualifying.append((prior_cutoff, record))
            if not qualifying:
                return None
            _, latest = max(qualifying,
                            key=lambda item: (item[0], instant(item[1]['recorded_at']), item[1]['record_id']))
            return {'label': latest['payload']['composed']['label'], 'ref': reference(latest)}

    def save_bundle(self, actor, case, task_ref, key, questions, answers, composed, stability, metadata, recorded_at):
        """Persist one validated probe bundle; the record re-validates the whole payload.

        The completed artifact's transitive access is checked with the actor this
        operation carries, before any write. The adapter supplies its membership as of
        this moment (``PersistentRepository.execute``), so a source behind an inherited
        ``composed['lineage_ref']`` revoked while the backend ran denies the save here:
        the creation response cannot disclose a label the actor may no longer read, and
        nothing is written.
        """
        with self._lock:
            prior, task = self.bundle_input(actor, case, task_ref, key)
            if prior is not None:
                return prior
            require(instant(recorded_at) >= instant(task['recorded_at']), 'MALFORMED_TIME')
            ident = 'probe:' + compute_content_digest({'actor': actor.actor_id, 'key': key})
            record = self._record('ProbeBundleArtifact', actor.tenant_id, case, ident, '1', recorded_at, {
                'task_ref': task_ref, 'actor_id': actor.actor_id, 'idempotency_key': key,
                'questions': questions, 'answers': answers, 'composed': composed, 'receipt': stability,
                'metadata': metadata, 'review_state': 'proposed',
                **self._pair_fields(actor.tenant_id, case)})
            self._access_record(actor, case, record)
            self._write([record])
            return json_copy(record)

    def workspace(self, actor, case):
        """One consistent, permitted projection; no inaccessible record counts."""
        with self._lock:
            heads = self.heads(actor, case)
            tasks, judgments, bundles = [], [], []
            for record in self._records_in(actor.tenant_id, case):
                if record['record_kind'] not in ('CompiledTask', 'JudgmentArtifact', 'ProbeBundleArtifact'):
                    continue
                owner = record['payload'].get('actor_id', record['payload'].get('access_scope', {}).get('actor_id'))
                if owner != actor.actor_id:
                    continue
                try:
                    self._access_record(actor, case, record)
                except ReviewError as exc:
                    if exc.code in ('ACCESS_DENIED', 'MISSING_INPUT'):
                        continue
                    raise
                if record['record_kind'] == 'CompiledTask':
                    p = record['payload']
                    snapshot = self._lookup(actor.tenant_id, case, p['snapshot_ref'])
                    stale = (snapshot['payload']['heads'] != heads['assumptions'] or
                             self.draft_status(actor, case, reference(record))['status'] == 'stale')
                    tasks.append({'record': record, 'stale': stale})
                elif record['record_kind'] == 'JudgmentArtifact':
                    judgments.append(record)
                else:
                    bundles.append(record)
            # `probe_bundles` is the key `src/workspace/app.js` reads for the probe panel and
            # filters by `payload.task_ref`; the name is the producer/consumer contract, so a
            # saved artifact is only visible to the review view under this exact key.
            return {'heads': heads, 'assumptions': [self.read(actor, case, r) for r in heads['assumptions'].values()],
                    'history': self.history(actor, case), 'tasks': sorted(tasks, key=lambda x: x['record']['recorded_at']),
                    'judgments': sorted(judgments, key=lambda x: x['recorded_at']),
                    'probe_bundles': sorted(bundles, key=lambda x: x['recorded_at']), 'can_review': actor.can_review,
                    **self._pair_fields(actor.tenant_id, case), 'consequences': 'uncomputed'}

    def _validate_review_request(self, request):
        request = json_copy(request)
        required = {
            "case_id", "request_id", "idempotency_key", "task_ref", "snapshot_digest",
            "expected_assumption_head", "expected_outlook_head", "disposition", "rationale",
            "reviewed_at", "recorded_at", "new_value",
        }
        # ``judgment_ref`` is optional: absent and explicit null both mean no reference.
        require(type(request) is dict and (set(request) == required or set(request) == required | {"judgment_ref"}))
        # The two spellings of "no reference" are one request: the normalized request
        # carries the key explicitly, so the idempotency digest is the same whether the
        # caller omitted the field or set it to null, and a retry under either spelling
        # replays instead of conflicting.
        request.setdefault("judgment_ref", None)
        require(all(nonblank(request[k]) for k in ("case_id", "request_id", "idempotency_key", "rationale")))
        require(type(request["disposition"]) is str and request["disposition"] in ("retain", "revise", "reject", "defer", "investigate"))
        require(instant(request["reviewed_at"]) <= instant(request["recorded_at"]), "MALFORMED_TIME")
        valid_ref(request["task_ref"], "CompiledTask")
        valid_ref(request["expected_assumption_head"], "AssumptionRevision")
        if request["expected_outlook_head"] is not None:
            valid_ref(request["expected_outlook_head"], "OutlookRevision")
        if request.get("judgment_ref") is not None:
            valid_ref(request["judgment_ref"])
        if request["disposition"] == "revise":
            quantity(request["new_value"])
        else:
            require(request["new_value"] is None)
        return request

    def _resolve_judgment_ref(self, actor, case, ref, task_ref):
        """A decision's judgment reference must name this task's saved artifact.

        The reference is recorded, never interpreted: only the artifact's kind and
        task are checked. A reference the actor cannot read is denied exactly as the
        artifact's own read is; every other non-match is ``JUDGMENT_TASK_MISMATCH``,
        including a reference that names nothing.
        """
        try:
            artifact = self._lookup(actor.tenant_id, case, ref)
        except ReviewError as exc:
            if exc.code in ("MISSING_INPUT", "INVALID_RECORD"):
                raise RecordError("JUDGMENT_TASK_MISMATCH") from None
            raise
        self._access_record(actor, case, artifact)
        require_v2(artifact["record_kind"] in ("JudgmentArtifact", "ProbeBundleArtifact"), "JUDGMENT_TASK_MISMATCH")
        require_v2(artifact["payload"]["task_ref"] == task_ref, "JUDGMENT_TASK_MISMATCH")
        return artifact

    def _review_guards(self, actor, request, task):
        case = request["case_id"]
        self._check_case(actor, case)
        require(actor.can_review, "ACCESS_DENIED")
        self._access_record(actor, case, task)
        p = task["payload"]
        require(p["access_scope"]["actor_id"] == actor.actor_id, "ACCESS_DENIED")
        snapshot = self._lookup(actor.tenant_id, case, p["snapshot_ref"])
        require(request["snapshot_digest"] == snapshot["content_digest"])
        require(request["expected_assumption_head"] == p["assumption_ref"])
        require(instant(task["recorded_at"]) <= instant(request["reviewed_at"]), "MALFORMED_TIME")
        scope = actor.tenant_id, case
        require(self._heads[scope].get(p["assumption_ref"]["record_id"]) == request["expected_assumption_head"] and self._outlooks[scope] == request["expected_outlook_head"], "STALE_HEAD")
        if p["status"] == "blocked":
            require(request["disposition"] in ("defer", "investigate"), "BLOCKED_TASK")
        if request["disposition"] in ("revise", "retain", "reject"):
            require(_key(actor.tenant_id, case, reference(task)) not in self._stale, "STALE_DEPENDENCY")
            require(self._heads[scope] == snapshot["payload"]["heads"], "STALE_HEAD")
            for dep in self._draft_dependencies(task):
                require(self._latest.get((actor.tenant_id, case, dep["record_kind"], dep["record_id"])) == dep, "STALE_DEPENDENCY")
        if request["disposition"] == "revise":
            assumption = self._lookup(actor.tenant_id, case, p["assumption_ref"])
            require(same_quantity_type(assumption["payload"]["value"], request["new_value"]))
            mapping, error = self._mapping_status(actor, self._check_case(actor, case), assumption, request["reviewed_at"], p["information_cutoff"])
            require(error is None and reference(mapping) == p["mapping_ref"], "UNRESOLVED_MAPPING")
        if request.get("judgment_ref") is not None:
            # Re-read from the store on every call, so the reference resolved during
            # preparation is resolved again under the commit lock.
            self._resolve_judgment_ref(actor, case, request["judgment_ref"], request["task_ref"])
        return snapshot

    def _prepare_review(self, actor, request, task):
        """Pure record rendering against copies; no clock, network or writes."""
        case, scope = request["case_id"], (actor.tenant_id, request["case_id"])
        p = task["payload"]
        snapshot = self._review_guards(actor, request, task)
        suffix = compute_content_digest({"actor_id": actor.actor_id, "request": request})
        decision_payload = dict(request, actor_id=actor.actor_id, snapshot_ref=reference(snapshot),
            information_cutoff=p["information_cutoff"], audit_cutoff=p["audit_cutoff"],
            retrospective=instant(request["reviewed_at"]) > instant(p["information_cutoff"]),
            **self._pair_fields(actor.tenant_id, case))
        decision = self._record("ReviewDecision", actor.tenant_id, case, "decision:" + suffix, "1", request["recorded_at"], decision_payload)
        prior_heads = json_copy(self._heads[scope])
        new_heads = json_copy(prior_heads)
        assumption = self._lookup(actor.tenant_id, case, p["assumption_ref"])
        new_assumption = None
        if request["disposition"] == "revise":
            new_payload = dict(assumption["payload"], prior_ref=reference(assumption),
                value=request["new_value"], mapping_ref=p["mapping_ref"], accepted_review_ref=reference(decision),
                **self._pair_fields(actor.tenant_id, case))
            new_assumption = self._record("AssumptionRevision", actor.tenant_id, case, assumption["record_id"], suffix, request["recorded_at"], new_payload)
            new_heads[assumption["record_id"]] = reference(new_assumption)
        accepted = request["disposition"] in ("retain", "revise")
        difference = {"kind": "revised" if new_assumption else "no_change" if accepted else "unaccepted_review",
            "entity": assumption["payload"]["entity"], "proposition": assumption["payload"]["proposition"],
            "old_value": assumption["payload"]["value"], "new_value": request["new_value"] if new_assumption else assumption["payload"]["value"],
            "valid_period": assumption["payload"]["valid_period"], "rationale": request["rationale"]}
        outlook = self._record("OutlookRevision", actor.tenant_id, case, "outlook:" + suffix, "1", request["recorded_at"], {
            "previous_outlook_ref": self._outlooks[scope], "decision_ref": reference(decision),
            "prior_heads": prior_heads, "new_heads": new_heads, "difference": difference,
            "state": "accepted" if accepted else "open", "reviewed_at": request["reviewed_at"],
            "information_cutoff": p["information_cutoff"], "audit_cutoff": p["audit_cutoff"],
            "open_issues": [] if accepted else [{"disposition": request["disposition"], "reason": request["rationale"]}],
            "consequences": "uncomputed", **self._pair_fields(actor.tenant_id, case),
        })
        return decision, new_assumption, outlook

    def commit_review(self, actor, request):
        # Access is checked before payload validation; inaccessible case existence is hidden.
        with self._lock:
            case = request.get("case_id") if type(request) is dict else None
            self._check_case(actor, case)
            require(actor.can_review, "ACCESS_DENIED")
        request = self._validate_review_request(request)
        digest = compute_content_digest(request)
        key = actor.tenant_id, case, actor.actor_id, request["idempotency_key"]
        with self._lock:
            task = self._lookup(actor.tenant_id, case, request["task_ref"])
            self._access_record(actor, case, task)
            existing = self._receipts.get(key)
            if existing:
                require(existing["request_digest"] == digest, "IDEMPOTENCY_CONFLICT")
                return self.receipt(actor, case, request["idempotency_key"])
            decision, new_assumption, outlook = self._prepare_review(actor, request, task)
        return self._commit_prepared(actor, request, task, digest, key, decision, new_assumption, outlook)

    def _commit_prepared(self, actor, request, task, digest, key, decision, new_assumption, outlook):
        # Rendering is complete. Recheck every authority/head/dependency under the write lock.
        with self._lock:
            case = request["case_id"]
            existing = self._receipts.get(key)
            if existing:
                require(existing["request_digest"] == digest, "IDEMPOTENCY_CONFLICT")
                return self.receipt(actor, case, request["idempotency_key"])
            self._review_guards(actor, request, task)
            require(outlook["payload"]["prior_heads"] == self._heads[(actor.tenant_id, case)], "STALE_HEAD")
            records = [decision, outlook] + ([new_assumption] if new_assumption else [])
            affected = []
            if new_assumption:
                prior = task["payload"]["assumption_ref"]
                affected = [reference(draft) for draft in self._records_in(actor.tenant_id, case)
                    if draft["record_kind"] in ("CompiledTask", "ScenarioProposal") and prior in self._draft_dependencies(draft)]
                records.append(self._record("DependencyImpact", actor.tenant_id, case,
                    "impact:" + new_assumption["content_digest"], "1", request["recorded_at"], {
                        "changed_ref": reference(new_assumption), "previous_ref": prior,
                        "affected_drafts": sorted(affected, key=_sort_ref),
                        "reason": "Accepted assumption changed; bound drafts require refresh.",
                        **self._pair_fields(actor.tenant_id, case),
                    }))
            self._write(records)
            scope = actor.tenant_id, case
            if new_assumption:
                self._heads[scope][new_assumption["record_id"]] = reference(new_assumption)
                for ref in affected:
                    self._stale[_key(actor.tenant_id, case, ref)] = "STALE_DEPENDENCY"
            if request["disposition"] in ("retain", "revise"):
                self._outlooks[scope] = reference(outlook)
            self._history[scope].append(reference(outlook))
            result = {"request_digest": digest, "decision_ref": reference(decision),
                "outlook_ref": reference(outlook), "assumption_ref": reference(new_assumption) if new_assumption else task["payload"]["assumption_ref"],
                "accepted_outlook_head": self._outlooks[scope], "history_sequence": len(self._history[scope])}
            self._receipts[key] = json_copy(result)
            return json_copy(result)

    def receipt(self, actor, case, idempotency_key):
        with self._lock:
            self._check_case(actor, case)
            require(actor.can_review, "ACCESS_DENIED")
            require(nonblank(idempotency_key))
            receipt = self._receipts.get((actor.tenant_id, case, actor.actor_id, idempotency_key))
            require(receipt is not None, "MISSING_INPUT")
            for name in ("decision_ref", "outlook_ref", "assumption_ref"):
                self._access_record(actor, case, self._lookup(actor.tenant_id, case, receipt[name]))
            return json_copy(receipt)

    def history(self, actor, case):
        with self._lock:
            self._check_case(actor, case)
            result = []
            for ref in self._history[(actor.tenant_id, case)]:
                record = self._lookup(actor.tenant_id, case, ref)
                self._access_record(actor, case, record)
                result.append(record)
            return result

    def prepare_scenario(self, actor, case, idempotency_key, recorded_at):
        with self._lock:
            receipt = self.receipt(actor, case, idempotency_key)
            decision = self._lookup(actor.tenant_id, case, receipt["decision_ref"])
            require(decision["payload"]["disposition"] == "revise")
            require(instant(decision["recorded_at"]) <= instant(recorded_at), "MALFORMED_TIME")
            task = self._lookup(actor.tenant_id, case, decision["payload"]["task_ref"])
            new = self._lookup(actor.tenant_id, case, receipt["assumption_ref"])
            old = self._lookup(actor.tenant_id, case, new["payload"]["prior_ref"])
            mapping = self._lookup(actor.tenant_id, case, new["payload"]["mapping_ref"])
            require(self._heads[(actor.tenant_id, case)].get(new["record_id"]) == reference(new), "STALE_HEAD")
            dependencies = [dep for dep in task["payload"]["dependencies"] if dep != reference(old)] + [reference(new)]
            for dep in dependencies + [item["passage_ref"] for item in task["payload"]["context"]]:
                require(self._latest.get((actor.tenant_id, case, dep["record_kind"], dep["record_id"])) == dep, "STALE_DEPENDENCY")
            current_mapping, error = self._mapping_status(actor, self._check_case(actor, case), new, recorded_at, task["payload"]["information_cutoff"])
            require(error is None and reference(current_mapping) == reference(mapping), "UNRESOLVED_MAPPING")
            snapshot = self._snapshot_record(actor, case, decision["recorded_at"], recorded_at)
            proposal = self._record("ScenarioProposal", actor.tenant_id, case,
                "scenario:" + decision["content_digest"], compute_content_digest({"recorded_at": recorded_at}), recorded_at, {
                    "snapshot_ref": reference(snapshot), "baseline_snapshot_ref": task["payload"]["snapshot_ref"],
                    "decision_ref": reference(decision), "mapping_ref": reference(mapping),
                    "old_assumption_ref": reference(old), "new_assumption_ref": reference(new),
                    "delta": {"representation_id": new["payload"]["representation_id"], "input_field": new["payload"]["input_field"],
                        "entity": new["payload"]["entity"], "cardinality": mapping["payload"]["cardinality"],
                        "old_value": old["payload"]["value"], "new_value": new["payload"]["value"], "valid_period": new["payload"]["valid_period"]},
                    "evidence": task["payload"]["context"], "dependencies": sorted(dependencies, key=_sort_ref),
                    "information_cutoff": task["payload"]["information_cutoff"], "audit_cutoff": task["payload"]["audit_cutoff"],
                    "execution": "proposal_only", "comparison": "pending_outputs", "consequences": "uncomputed",
                    **self._pair_fields(actor.tenant_id, case),
                })
            self._write([snapshot, proposal])
            return proposal

    def export_scenario(self, actor, case, ref):
        with self._lock:
            proposal = self.read(actor, case, ref)
            require(proposal["record_kind"] == "ScenarioProposal")
            require(_key(actor.tenant_id, case, ref) not in self._stale, "STALE_DEPENDENCY")
            for dep in self._draft_dependencies(proposal):
                require(self._latest.get((actor.tenant_id, case, dep["record_kind"], dep["record_id"])) == dep, "STALE_DEPENDENCY")
            assumption = self._lookup(actor.tenant_id, case, proposal["payload"]["new_assumption_ref"])
            mapping, error = self._mapping_status(actor, self._check_case(actor, case), assumption, proposal["recorded_at"], proposal["payload"]["information_cutoff"])
            require(error is None and reference(mapping) == proposal["payload"]["mapping_ref"], "UNRESOLVED_MAPPING")
            return proposal


class InMemoryRepository(ReviewService):
    """Reference adapter retaining the original H0 public interface."""
