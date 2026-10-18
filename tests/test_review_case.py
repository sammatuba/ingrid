"""H0 behavior and counterexamples; all actors/evidence are labeled synthetic."""
import copy
import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from src.contracts.jsonutil import compute_content_digest, canonical_dumps
from src.judgment import PROMPT_VERSION
from src.judgment.bundle import render_bundle
from src.judgment.systemone import FixtureSystemOne, SystemOneService
from src.review import ActorContext, InMemoryRepository, ReviewError, make_record, reference, validate_record
from src.review.records import BASIS_KINDS, load_permissions, provenance

FIXTURE = json.loads((Path(__file__).parent / "fixtures/review/case.json").read_text(encoding="utf-8"))
SEED = "2026-10-01T09:00:00+08:00"
CUTOFF = "2026-10-01T10:00:00+08:00"
TODAY = "2026-10-05T10:00:00+08:00"
LATER = "2026-10-05T11:00:00+08:00"


class H0Case(unittest.TestCase):
    def make_repository(self):
        return InMemoryRepository()

    def setUp(self):
        self.f = copy.deepcopy(FIXTURE)
        self.repo = self.make_repository()
        self.actor = ActorContext(self.f["actor_id"], self.f["tenant_id"], frozenset({self.f["case_id"]}), frozenset({"synthetic-public", "synthetic-private"}), True)
        self.case = self.f["case_id"]
        model = {"representation_id": self.f["representation_id"], "target_type": "GeneratingUnit", "model_version": "synthetic-model.v1", "input_fields": {self.f["input_field"]: {"quantity_kind": self.f["value"]["quantity_kind"], "unit": "MW"}}}
        self.case_record = self.record("Case", self.case, "1", {"permitted_actors": [self.actor.actor_id, "synthetic-other"], "synthetic": True, "permission_ref": None, "entities": [self.f["entity"]], "representations": [model]})
        self.repo.register_case(self.actor, self.case_record)
        self.source, self.passage = self.add_source()
        self.mapping = self.add_mapping()
        self.assumption = self.repo.seed_assumption(self.actor, "assumption-a", "1", SEED, {
            "case_id": self.case, "entity": self.f["entity"], "proposition": "Assumed available capacity during the declared day",
            "value": self.f["value"], "valid_period": self.f["valid_period"], "representation_id": self.f["representation_id"],
            "input_field": self.f["input_field"], "mapping_ref": reference(self.mapping)}, "Explicit synthetic initial state")

    def record(self, kind, ident, revision, payload, at=SEED):
        return make_record(kind, self.actor.tenant_id, self.case, ident, revision, at, payload)

    def assertCode(self, code, call, *args, **kwargs):
        with self.assertRaises(ReviewError) as caught:
            call(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return str(caught.exception)

    def add_source(self, ident="source-a", revision="1", known=SEED, policy="synthetic-public", lineage=None, copied_from=None, text=None, at=SEED, passage=True):
        text = self.f["source_text"] if text is None else text
        data = text.encode("utf-8")
        payload = {"synthetic": True, "permission_ref": None,
            "source_id": ident, "source_version": revision, "source_byte_digest": hashlib.sha256(data).hexdigest(),
            "original_text": text, "lineage_id": lineage or ident, "publisher": "fictional issuer", "published_at": "2026-09-30",
            "known_at": known, "access_policy_ref": policy,
            "availability_basis": {"basis_kind": "capture_logged_at", "basis_ref": "synthetic capture log", "note": ""} if known else None,
            "unknown_reason": "synthetic unknown availability" if known is None else None, "copied_from": copied_from}
        source = self.record("SourceVersion", ident, revision, payload, at)
        self.repo.register(self.actor, source, source_bytes=data)
        if not passage:
            return source, None
        quote = self.f["quote"] if self.f["quote"] in text else text
        start = text.index(quote)
        span = self.record("Passage", "passage:" + ident, revision, {
            "synthetic": True, "permission_ref": None,
            "source_ref": reference(source), "source_id": ident, "source_version": revision,
            "source_byte_digest": source["payload"]["source_byte_digest"], "start": start, "end": start + len(quote),
            "quote": quote, "quote_digest": hashlib.sha256(quote.encode("utf-8")).hexdigest()}, at)
        self.repo.register(self.actor, span)
        return source, span

    def add_mapping(self, ident="mapping-a", revision="1", status="reviewed", at=SEED, mutate=None):
        payload = {"synthetic": True, "permission_ref": None,
            "entities": [self.f["entity"]], "representation_id": self.f["representation_id"], "input_field": self.f["input_field"],
            "cardinality": "one_to_one", "valid_period": self.f["valid_period"], "status": status,
            "reviewer": self.actor.actor_id if status == "reviewed" else None, "reviewed_at": at if status == "reviewed" else None,
            "source_refs": [reference(self.source)]}
        if mutate:
            mutate(payload)
        mapping = self.record("MappingRevision", ident, revision, payload, at)
        self.repo.register(self.actor, mapping)
        return mapping

    def task(self, *, audit=CUTOFF, info=CUTOFF, at=TODAY, passage_ids=None):
        snapshot = self.repo.build_snapshot(self.actor, self.case, audit, at)
        return self.repo.compile_task(self.actor, self.case, reference(snapshot), "assumption-a", info, at, passage_ids=passage_ids)

    def request(self, task=None, disposition="revise", key="review-a", at=TODAY):
        task = task or self.task()
        return {"case_id": self.case, "request_id": key, "idempotency_key": key, "task_ref": reference(task),
            "snapshot_digest": task["payload"]["snapshot_ref"]["content_digest"], "expected_assumption_head": task["payload"]["assumption_ref"],
            "expected_outlook_head": self.repo.heads(self.actor, self.case)["outlook"], "disposition": disposition,
            "rationale": "Synthetic analyst reviewed the exact advisory", "reviewed_at": at, "recorded_at": at,
            "new_value": dict(self.f["value"], value="+8.25") if disposition == "revise" else None}

    def test_exact_bytes_unicode_crlf_bom_and_json_round_trip(self):
        source = json.loads(canonical_dumps(self.source))
        self.assertEqual(source["payload"]["original_text"].encode("utf-8"), self.f["source_text"].encode("utf-8"))
        self.assertTrue(source["payload"]["original_text"].startswith("\ufeff"))
        self.assertEqual(self.passage["payload"]["quote"], self.f["quote"])
        self.assertEqual(source, self.repo.register(self.actor, source, source_bytes=self.f["source_text"].encode("utf-8")))
        self.assertEqual("date", source["time_metadata"]["/payload/published_at"]["precision"])
        self.assertEqual("+08:00", source["time_metadata"]["/recorded_at"]["offset"])
        self.assertEqual("2026-10-01T01:00:00Z", source["recorded_at"])

    def test_tampered_bytes_hash_quote_offsets_and_binding_fail(self):
        self.assertCode("INVALID_SOURCE", self.repo.register, self.actor, self.source, source_bytes=b"different")
        self.assertCode("INVALID_SOURCE", self.repo.register, self.actor, self.source, source_bytes=b"\xff")
        for key, value in (("source_byte_digest", "0" * 64), ("original_text", "altered")):
            raw = copy.deepcopy(self.source)
            raw["payload"][key] = value
            raw["content_digest"] = compute_content_digest(raw)
            self.assertCode("INVALID_SOURCE", self.repo.register, self.actor, raw, source_bytes=b"altered")
        for key, value in (("start", 0), ("end", 100000), ("quote_digest", "0" * 64), ("source_version", "private-version")):
            raw = copy.deepcopy(self.passage)
            raw["revision_id"] = "invalid-" + key
            raw["payload"][key] = value
            raw["content_digest"] = compute_content_digest(raw)
            self.assertCode("INVALID_SOURCE", self.repo.register, self.actor, raw)
        raw = copy.deepcopy(self.passage)
        raw["payload"]["quote"] = "forged quote"
        raw["payload"]["quote_digest"] = hashlib.sha256(b"forged quote").hexdigest()
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("INVALID_SOURCE", self.repo.register, self.actor, raw)

    def test_revision_idempotency_conflict_and_defensive_copies(self):
        raw = copy.deepcopy(self.source)
        self.repo.register(self.actor, raw, source_bytes=self.f["source_text"].encode("utf-8"))
        raw["payload"]["publisher"] = "changed caller"
        saved = self.repo.read(self.actor, self.case, reference(self.source))
        self.assertEqual("fictional issuer", saved["payload"]["publisher"])
        saved["payload"]["publisher"] = "changed read"
        self.assertEqual("fictional issuer", self.repo.read(self.actor, self.case, reference(self.source))["payload"]["publisher"])
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("REVISION_CONFLICT", self.repo.register, self.actor, raw, source_bytes=self.f["source_text"].encode("utf-8"))
        self.assertEqual("fictional issuer", self.repo.read(self.actor, self.case, reference(self.source))["payload"]["publisher"])

    def test_bad_python_objects_nonfinite_shapes_and_times_fail_safely(self):
        for bad in (object(), (1, 2), {1: "x"}, float("nan"), float("inf"), "\ud800"):
            raw = copy.deepcopy(self.source)
            raw["payload"]["unknown_extra"] = bad
            self.assertCode("INVALID_RECORD", validate_record, raw)
        circular = []
        circular.append(circular)
        raw = copy.deepcopy(self.source)
        raw["payload"]["unknown_extra"] = circular
        self.assertCode("INVALID_RECORD", validate_record, raw)
        for bad in ("2026-10-01T12:00:00", "2026-99-01T12:00:00Z", "2026-10-01", None, [], {}):
            self.assertCode("MALFORMED_TIME", self.record, "BeliefSnapshot", "bad", "1", {"synthetic": True, "permission_ref": None, "heads": {}, "audit_cutoff": bad})
        for start, end in (("2026-10-07", "2026-10-06"), ("2026-10-07", "2026-10-07"), ("2026-10-06", "2026-10-07T00:00:00Z")):
            self.assertCode("MALFORMED_TIME", self.add_mapping, revision="bad", mutate=lambda p: p.update(valid_period={"start": start, "end": end}))
        self.assertCode("INVALID_RECORD", self.repo.commit_review, self.actor, dict(self.request(), actor_id="admin"))

    def test_strict_cutoff_at_boundary_unknown_later_and_publication_not_availability(self):
        exact, _ = self.add_source("exact", known=CUTOFF)
        unknown, _ = self.add_source("unknown", known=None)
        later, _ = self.add_source("later", known="2026-10-01T10:00:01+08:00")
        task = self.task()
        self.assertEqual("compiled", task["payload"]["status"])
        refs = [c["source_ref"] for c in task["payload"]["context"]]
        self.assertIn(reference(exact), refs)
        self.assertNotIn(reference(unknown), refs)
        self.assertNotIn(reference(later), refs)
        self.assertEqual({"UNKNOWN_AVAILABILITY", "LATER_AVAILABILITY"}, {o["code"] for o in task["payload"]["omissions"]})

    def test_retrospective_review_and_historical_snapshot_excludes_later_decision(self):
        old = self.repo.build_snapshot(self.actor, self.case, CUTOFF, TODAY)
        receipt = self.repo.commit_review(self.actor, self.request())
        decision = self.repo.read(self.actor, self.case, receipt["decision_ref"])
        self.assertTrue(decision["payload"]["retrospective"])
        self.assertEqual("2026-10-05T02:00:00Z", decision["payload"]["reviewed_at"])
        historical = self.repo.build_snapshot(self.actor, self.case, CUTOFF, LATER)
        self.assertEqual(old["payload"]["heads"], historical["payload"]["heads"])
        current = self.repo.build_snapshot(self.actor, self.case, TODAY, LATER)
        self.assertEqual(receipt["assumption_ref"], current["payload"]["heads"]["assumption-a"])
        request = self.request(at=LATER, key="backdated")
        request["reviewed_at"] = CUTOFF
        self.assertCode("MALFORMED_TIME", self.repo.commit_review, self.actor, request)

    def test_unreviewed_ambiguous_and_overlapping_mappings_block_revision(self):
        for status in ("unreviewed", "ambiguous"):
            with self.subTest(status=status):
                self.add_mapping(revision=status, status=status, at=CUTOFF)
                task = self.task()
                self.assertIn("UNRESOLVED_MAPPING", task["payload"]["block_reasons"])
                self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task))
        self.add_mapping(revision="reviewed-2", at=CUTOFF)
        self.add_mapping(ident="mapping-conflict", at=CUTOFF)
        task = self.task()
        self.assertIn("AMBIGUOUS_MAPPING", task["payload"]["block_reasons"])
        self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task))

    def test_identity_types_cardinality_and_units_cannot_be_inferred(self):
        self.assertCode("UNRESOLVED_MAPPING", self.add_mapping, ident="plant", mutate=lambda p: p.update(entities=[dict(self.f["entity"], entity_type="Plant")]))
        self.assertCode("UNRESOLVED_MAPPING", self.add_mapping, ident="many", mutate=lambda p: p.update(cardinality="many_to_one"))
        for value in ({"value": "8", "quantity_kind": "assumed_available_capacity", "unit": "MWh"}, {"value": "8", "quantity_kind": "installed_capacity", "unit": "MW"}):
            request = self.request()
            request["new_value"] = value
            self.assertCode("INVALID_RECORD", self.repo.commit_review, self.actor, request)
        for value in (8.25, "NaN", "Infinity", "8e3", "8 MW", {}, True):
            request = self.request()
            request["new_value"]["value"] = value
            self.assertCode("INVALID_RECORD", self.repo.commit_review, self.actor, request)
        self.assertEqual([], self.repo.history(self.actor, self.case))

    def test_copied_reports_share_lineage(self):
        self.add_source("copy", lineage="source-a", copied_from=reference(self.source))
        task = self.task()
        self.assertEqual(1, len(task["payload"]["lineage_groups"]))
        self.assertEqual(2, len(task["payload"]["lineage_groups"][0]["source_refs"]))
        self.assertCode("INVALID_SOURCE", self.add_source, "false-independent", lineage="independent", copied_from=reference(self.source))

    def test_retain_no_change_and_input_request_mutation(self):
        before = self.repo.heads(self.actor, self.case)
        request = self.request(disposition="retain")
        original = copy.deepcopy(request)
        receipt = self.repo.commit_review(self.actor, request)
        self.assertEqual(original, request)
        request["rationale"] = "caller mutation"
        after = self.repo.heads(self.actor, self.case)
        self.assertEqual(before["assumptions"], after["assumptions"])
        self.assertEqual(receipt["outlook_ref"], after["outlook"])
        outlook = self.repo.read(self.actor, self.case, receipt["outlook_ref"])
        self.assertEqual("no_change", outlook["payload"]["difference"]["kind"])
        self.assertEqual(original["rationale"], outlook["payload"]["difference"]["rationale"])
        self.assertEqual(self.f["value"], outlook["payload"]["difference"]["new_value"])

    def test_reject_defer_investigate_only_append_open_history(self):
        before = self.repo.heads(self.actor, self.case)
        task = self.task()
        for i, disposition in enumerate(("reject", "defer", "investigate"), 1):
            receipt = self.repo.commit_review(self.actor, self.request(task, disposition, key=disposition))
            self.assertEqual(before, self.repo.heads(self.actor, self.case))
            self.assertEqual(i, receipt["history_sequence"])
            outlook = self.repo.read(self.actor, self.case, receipt["outlook_ref"])
            self.assertEqual("open", outlook["payload"]["state"])
            self.assertEqual(disposition, outlook["payload"]["open_issues"][0]["disposition"])

    def test_blocked_task_permits_only_open_work(self):
        self.add_mapping(revision="unreviewed", status="unreviewed", at=CUTOFF)
        task = self.task()
        for disposition in ("retain", "reject", "revise"):
            self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task, disposition, key=disposition))
        for disposition in ("defer", "investigate"):
            self.repo.commit_review(self.actor, self.request(task, disposition, key=disposition))
        self.assertEqual(reference(self.assumption), self.repo.heads(self.actor, self.case)["assumptions"]["assumption-a"])
        self.assertEqual(2, len(self.repo.history(self.actor, self.case)))

    def test_idempotency_after_heads_advance_and_changed_payload_conflict(self):
        request = self.request()
        first = self.repo.commit_review(self.actor, request)
        next_task = self.task(audit=TODAY, at=LATER)
        self.repo.commit_review(self.actor, self.request(next_task, "retain", "review-b", LATER))
        self.assertEqual(first, self.repo.commit_review(self.actor, request))
        changed = dict(request, rationale="different rationale")
        self.assertCode("IDEMPOTENCY_CONFLICT", self.repo.commit_review, self.actor, changed)
        self.assertEqual(2, len(self.repo.history(self.actor, self.case)))
        first["decision_ref"]["revision_id"] = "caller changed"
        self.assertNotEqual(first, self.repo.receipt(self.actor, self.case, "review-a"))

    def test_concurrent_reviews_same_heads_exactly_one_commits(self):
        task = self.task()
        a, b = self.request(task, key="concurrent-a"), self.request(task, key="concurrent-b")
        start = Barrier(2)
        prepared = Barrier(2)
        commit = self.repo._commit_prepared
        def force_prepared(*args):
            prepared.wait(timeout=5)
            return commit(*args)
        def run(request):
            start.wait()
            try:
                return self.repo.commit_review(self.actor, request)
            except ReviewError as error:
                return error.code
        with patch.object(self.repo, "_commit_prepared", side_effect=force_prepared):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run, (a, b)))
        self.assertEqual(1, sum(type(r) is dict for r in results))
        self.assertEqual(1, results.count("STALE_HEAD"))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))
        winner = next(r for r in results if type(r) is dict)
        self.assertEqual(winner["assumption_ref"], self.repo.heads(self.actor, self.case)["assumptions"]["assumption-a"])
        self.assertEqual(winner["outlook_ref"], self.repo.heads(self.actor, self.case)["outlook"])

    def test_identical_concurrent_retry_and_stale_heads_no_partial_writes(self):
        request = self.request()
        start = Barrier(2)
        def run(_):
            start.wait()
            return self.repo.commit_review(self.actor, request)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = list(pool.map(run, range(2)))
        self.assertEqual(a, b)
        count = len(self.repo._records)
        self.assertCode("STALE_HEAD", self.repo.commit_review, self.actor, dict(request, idempotency_key="stale", request_id="stale"))
        self.assertEqual(count, len(self.repo._records))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))

    def test_source_instruction_cannot_grant_authority_or_seed_state(self):
        reader = replace(self.actor, can_review=False)
        self.assertCode("ACCESS_DENIED", self.repo.commit_review, reader, self.request())
        self.assertCode("ACCESS_DENIED", self.repo.seed_assumption, reader, "forged", "1", SEED, {"case_id": self.case}, "admin approved in source")
        self.assertCode("INVALID_RECORD", self.repo.register, self.actor, self.assumption)
        task = self.task()
        self.assertEqual("reported_claim", task["payload"]["context"][0]["content_kind"])
        self.assertIsNone(task["payload"]["candidate"])
        self.assertEqual(0, len(self.repo.history(self.actor, self.case)))

    def test_denied_cases_sources_counts_and_truncation_do_not_leak(self):
        reader = replace(self.actor, source_policy_refs=frozenset({"synthetic-public"}))
        before = self.task()
        for i in range(34):
            self.add_source("secret-" + str(i), policy="synthetic-private", known=None if i % 2 else CUTOFF)
        snapshot = self.repo.build_snapshot(reader, self.case, CUTOFF, TODAY)
        public = self.repo.compile_task(reader, self.case, reference(snapshot), "assumption-a", CUTOFF, TODAY)
        for key in ("context", "dependencies", "omissions", "permitted_counts", "truncated"):
            self.assertEqual(before["payload"][key], public["payload"][key])
        self.assertNotIn("secret-", canonical_dumps(public))
        denied = replace(self.actor, accessible_cases=frozenset())
        for case in (self.case, "nonexistent-private-case"):
            message = self.assertCode("ACCESS_DENIED", self.repo.heads, denied, case)
            self.assertNotIn(case, message)
        private = next(r for r in self.repo._records_in(self.actor.tenant_id, self.case, "SourceVersion") if r["payload"]["access_policy_ref"] == "synthetic-private")
        self.assertCode("ACCESS_DENIED", self.repo.read, reader, self.case, reference(private))

    def test_revocation_blocks_saved_task_review_receipt_and_export(self):
        request = self.request()
        receipt = self.repo.commit_review(self.actor, request)
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        revoked = replace(self.actor, source_policy_refs=frozenset())
        self.assertCode("ACCESS_DENIED", self.repo.commit_review, revoked, request)
        self.assertCode("ACCESS_DENIED", self.repo.receipt, revoked, self.case, "review-a")
        self.assertCode("ACCESS_DENIED", self.repo.export_scenario, revoked, self.case, reference(scenario))
        self.assertCode("ACCESS_DENIED", self.repo.read, revoked, self.case, request["task_ref"])
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))

    def test_proposal_exact_signed_delta_and_uncomputed_output(self):
        receipt = self.repo.commit_review(self.actor, self.request())
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        delta = scenario["payload"]["delta"]
        self.assertEqual(self.f["value"], delta["old_value"])
        self.assertEqual("+8.25", delta["new_value"]["value"])
        self.assertEqual("MW", delta["new_value"]["unit"])
        self.assertEqual(self.f["valid_period"], delta["valid_period"])
        self.assertEqual(self.f["input_field"], delta["input_field"])
        self.assertEqual(reference(self.mapping), scenario["payload"]["mapping_ref"])
        self.assertEqual(receipt["assumption_ref"], scenario["payload"]["new_assumption_ref"])
        self.assertEqual("proposal_only", scenario["payload"]["execution"])
        self.assertEqual("pending_outputs", scenario["payload"]["comparison"])
        self.assertEqual("uncomputed", scenario["payload"]["consequences"])
        self.assertEqual(scenario, self.repo.export_scenario(self.actor, self.case, reference(scenario)))
        self.assertFalse(hasattr(self.repo, "execute"))

    def test_dependency_changes_stale_task_and_proposal_preserve_history(self):
        task = self.task()
        receipt = self.repo.commit_review(self.actor, self.request(task))
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        accepted = self.repo.heads(self.actor, self.case)
        history = self.repo.history(self.actor, self.case)
        self.add_source(revision="2", text=self.f["source_text"] + "changed\r\n", at=LATER)
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(task)))
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(scenario)))
        self.assertCode("STALE_DEPENDENCY", self.repo.export_scenario, self.actor, self.case, reference(scenario))
        self.assertEqual(accepted, self.repo.heads(self.actor, self.case))
        self.assertEqual(history, self.repo.history(self.actor, self.case))
        impacts = self.repo._records_in(self.actor.tenant_id, self.case, "DependencyImpact")
        self.assertTrue(any(reference(scenario) in r["payload"]["affected_drafts"] for r in impacts))
        self.assertEqual(receipt, self.repo.receipt(self.actor, self.case, "review-a"))

    def test_mapping_change_between_preparation_and_commit_blocks_without_writes(self):
        task = self.task()
        request = self.request(task)
        original = self.repo._prepare_review
        def changed(*args):
            records = original(*args)
            self.add_mapping(revision="2", at=TODAY)
            return records
        with patch.object(self.repo, "_prepare_review", side_effect=changed):
            self.assertCode("STALE_DEPENDENCY", self.repo.commit_review, self.actor, request)
        self.assertEqual([], self.repo.history(self.actor, self.case))
        self.assertEqual(reference(self.assumption), self.repo.heads(self.actor, self.case)["assumptions"]["assumption-a"])

    def test_context_32_passages_allowed_33_blocks_until_narrowed(self):
        p = self.passage["payload"]
        for i in range(31):
            self.repo.register(self.actor, self.record("Passage", "span-" + str(i), "1", p))
        task = self.task()
        self.assertEqual(32, task["payload"]["permitted_counts"]["passages"])
        self.assertEqual("compiled", task["payload"]["status"])
        self.repo.register(self.actor, self.record("Passage", "span-32", "1", p))
        task = self.task()
        self.assertTrue(task["payload"]["truncated"])
        self.assertIn("TRUNCATED_CONTEXT", task["payload"]["block_reasons"])
        self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task))
        narrow = self.task(passage_ids=[self.passage["record_id"]])
        self.assertEqual("compiled", narrow["payload"]["status"])
        self.repo.commit_review(self.actor, self.request(narrow))

    def test_dependency_nodes_32_allowed_33_blocks(self):
        # Case + assumption + mapping + 29 sources = 32 dependency nodes.
        for i in range(28):
            self.add_source("node-" + str(i))
        task = self.task()
        self.assertEqual(32, task["payload"]["permitted_counts"]["dependency_nodes"])
        self.assertEqual("compiled", task["payload"]["status"])
        self.add_source("node-29")
        task = self.task()
        self.assertEqual(33, task["payload"]["permitted_counts"]["dependency_nodes"])
        self.assertIn("TRUNCATED_CONTEXT", task["payload"]["block_reasons"])
        self.assertEqual(32, len(task["payload"]["dependencies"]))

    def test_determinism_modes_and_no_model_required(self):
        a, b = self.task(), self.task()
        self.assertEqual(a, b)
        self.assertEqual(a["payload"]["task_digest"], b["payload"]["task_digest"])
        self.assertEqual(a["payload"]["snapshot_ref"], b["payload"]["snapshot_ref"])
        self.assertTrue(a["payload"]["synthetic"])
        self.assertEqual("deterministic", a["payload"]["execution_mode"])
        self.assertIsNone(a["payload"]["candidate"])
        self.repo.commit_review(self.actor, self.request(a, "retain"))

    def test_task_digest_is_reproducible_from_serialized_payload(self):
        task = self.task()
        raw = json.loads(canonical_dumps(task))
        manifest = {k: v for k, v in raw["payload"].items() if k != "task_digest"}
        self.assertEqual(raw["payload"]["task_digest"], compute_content_digest(manifest))
        self.assertEqual(self.f["value"], raw["payload"]["assumption_definition"]["value"])
        self.assertEqual(self.f["entity"], raw["payload"]["assumption_definition"]["entity"])
        self.assertEqual("reviewed", raw["payload"]["mapping_definition"]["status"])
        self.assertEqual(task, validate_record(raw))
        raw["payload"]["task_digest"] = "0" * 64
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("INVALID_RECORD", validate_record, raw)

    def test_forged_time_metadata_and_invalid_offset_are_rejected(self):
        raw = copy.deepcopy(self.source)
        raw["time_metadata"]["/recorded_at"]["supplied"] = LATER
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("MALFORMED_TIME", validate_record, raw)
        raw = copy.deepcopy(self.source)
        raw["time_metadata"]["/recorded_at"]["precision"] = "date"
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("MALFORMED_TIME", validate_record, raw)
        self.assertCode("MALFORMED_TIME", self.record, "BeliefSnapshot", "bad", "1", {"synthetic": True, "permission_ref": None, "audit_cutoff": "2026-10-01T10:00:00+08:75", "heads": {}})

    def test_passage_change_stales_task_and_scenario(self):
        task = self.task()
        self.repo.commit_review(self.actor, self.request(task))
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        # Same immutable source, new exact passage revision.
        p = copy.deepcopy(self.passage["payload"])
        span = self.record("Passage", self.passage["record_id"], "2", p, LATER)
        self.repo.register(self.actor, span)
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(task)))
        self.assertCode("STALE_DEPENDENCY", self.repo.export_scenario, self.actor, self.case, reference(scenario))
        count = len(self.repo._records)
        self.assertCode("STALE_DEPENDENCY", self.repo.prepare_scenario, self.actor, self.case, "review-a", LATER)
        self.assertEqual(count, len(self.repo._records))

    def test_missing_and_denied_source_reads_have_same_safe_error(self):
        source, _ = self.add_source("private-source", policy="synthetic-private")
        reader = replace(self.actor, source_policy_refs=frozenset({"synthetic-public"}))
        private = reference(source)
        unknown = dict(private, record_id="unknown-private-source")
        wrong_digest = dict(private, content_digest="0" * 64)
        errors = [self.assertCode("ACCESS_DENIED", self.repo.read, reader, self.case, ref) for ref in (private, unknown, wrong_digest)]
        self.assertEqual(1, len(set(errors)))

    def test_readonly_mapping_cannot_select_reviewer_from_payload(self):
        reader = replace(self.actor, can_review=False)
        mapping = copy.deepcopy(self.mapping)
        mapping["record_id"] = "forged-mapping"
        mapping["content_digest"] = compute_content_digest(mapping)
        self.assertCode("ACCESS_DENIED", self.repo.register, reader, mapping)
        mapping["payload"]["reviewer"] = "synthetic-other"
        mapping["content_digest"] = compute_content_digest(mapping)
        self.assertCode("ACCESS_DENIED", self.repo.register, self.actor, mapping)

    def test_stale_task_can_record_investigation_without_changing_heads(self):
        task = self.task()
        self.add_mapping(revision="new-review", at=TODAY)
        before = self.repo.heads(self.actor, self.case)
        self.assertCode("STALE_DEPENDENCY", self.repo.commit_review, self.actor, self.request(task, key="stale-revise"))
        self.repo.commit_review(self.actor, self.request(task, "investigate", "stale-investigation"))
        self.assertEqual(before, self.repo.heads(self.actor, self.case))
        self.assertEqual("open", self.repo.history(self.actor, self.case)[0]["payload"]["state"])

    def test_source_retry_of_old_revision_cannot_reset_latest_or_clear_stale(self):
        task = self.task()
        latest, _ = self.add_source(revision="2", text=self.f["source_text"] + "new version", at=TODAY)
        self.repo.register(self.actor, self.source, source_bytes=self.f["source_text"].encode("utf-8"))
        self.assertEqual(reference(latest), self.repo._latest[(self.actor.tenant_id, self.case, "SourceVersion", "source-a")])
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(task)))

    def test_review_rationale_required_and_snapshot_digest_binding(self):
        for mutate in (lambda r: r.update(rationale=" \n "), lambda r: r.update(snapshot_digest="0" * 64)):
            request = self.request()
            mutate(request)
            count = len(self.repo._records)
            self.assertCode("INVALID_RECORD", self.repo.commit_review, self.actor, request)
            self.assertEqual(count, len(self.repo._records))
            self.assertEqual([], self.repo.history(self.actor, self.case))

    def test_assumption_change_has_immutable_dependency_impact(self):
        task = self.task()
        receipt = self.repo.commit_review(self.actor, self.request(task))
        impacts = self.repo._records_in(self.actor.tenant_id, self.case, "DependencyImpact")
        impact = next(i for i in impacts if i["payload"]["changed_ref"] == receipt["assumption_ref"])
        self.assertEqual(reference(self.assumption), impact["payload"]["previous_ref"])
        self.assertIn(reference(task), impact["payload"]["affected_drafts"])
        self.assertEqual(self.f["value"], self.repo.read(self.actor, self.case, reference(self.assumption))["payload"]["value"])

    def test_repeated_scenario_preparation_and_json_round_trip(self):
        self.repo.commit_review(self.actor, self.request())
        a = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        self.assertEqual(a, self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY))
        b = self.repo.prepare_scenario(self.actor, self.case, "review-a", LATER)
        self.assertNotEqual(reference(a), reference(b))
        self.assertEqual(a["payload"]["delta"], b["payload"]["delta"])
        self.assertEqual(b, validate_record(json.loads(canonical_dumps(b))))

    def test_actor_scoped_idempotency_and_cross_tenant_access(self):
        task = self.task()
        first = self.repo.commit_review(self.actor, self.request(task, "retain"))
        other = replace(self.actor, actor_id="synthetic-other")
        snapshot = self.repo.build_snapshot(other, self.case, CUTOFF, TODAY)
        task2 = self.repo.compile_task(other, self.case, reference(snapshot), "assumption-a", CUTOFF, TODAY)
        request2 = self.request(task2, "retain")
        second = self.repo.commit_review(other, request2)
        self.assertNotEqual(first["decision_ref"], second["decision_ref"])
        self.assertEqual(first, self.repo.receipt(self.actor, self.case, "review-a"))
        self.assertEqual(second, self.repo.receipt(other, self.case, "review-a"))
        foreign = replace(self.actor, tenant_id="foreign-tenant")
        self.assertCode("ACCESS_DENIED", self.repo.read, foreign, self.case, reference(self.source))
        self.assertCode("ACCESS_DENIED", self.repo.commit_review, foreign, self.request(task, "retain"))

    def test_context_with_only_unknown_availability_remains_blocked(self):
        _, passage = self.add_source("unknown-only", known=None)
        task = self.task(passage_ids=[passage["record_id"]])
        self.assertEqual([], task["payload"]["context"])
        self.assertIn("MISSING_INPUT", task["payload"]["block_reasons"])
        self.assertEqual("UNKNOWN_AVAILABILITY", task["payload"]["omissions"][0]["code"])
        self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task))

    def test_invalid_seed_and_direct_discriminator_shapes_fail_safely(self):
        self.assertCode("INVALID_RECORD", self.repo.seed_assumption, self.actor, "invalid", "1", SEED, {"case_id": self.case}, "synthetic invalid seed")
        for field in ("status", "cardinality", "entities", "source_refs", "representation_id"):
            for bad in ([], {}, None, True):
                raw = copy.deepcopy(self.mapping)
                raw["payload"][field] = bad
                raw["content_digest"] = compute_content_digest(raw)
                with self.subTest(field=field, bad=bad):
                    self.assertCode("INVALID_RECORD", validate_record, raw)

    def test_all_stored_record_kinds_validate_after_json_round_trip(self):
        task = self.task()
        self.repo.commit_review(self.actor, self.request(task))
        self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        self.add_source(revision="2", text=self.f["source_text"] + "revision", at=LATER)
        kinds = set()
        for record in self.repo._records_in(self.actor.tenant_id, self.case):
            kinds.add(record["record_kind"])
            self.assertEqual(record, validate_record(json.loads(canonical_dumps(record))))
        self.assertEqual({"Case", "SourceVersion", "Passage", "MappingRevision", "AssumptionRevision", "BeliefSnapshot", "CompiledTask", "ReviewDecision", "ScenarioProposal", "OutlookRevision", "DependencyImpact"}, kinds)

    def test_historical_snapshot_excludes_decision_recorded_after_audit(self):
        request = self.request()
        request["recorded_at"] = LATER
        receipt = self.repo.commit_review(self.actor, request)
        at_review = self.repo.build_snapshot(self.actor, self.case, TODAY, LATER)
        at_record = self.repo.build_snapshot(self.actor, self.case, LATER, LATER)
        self.assertEqual(reference(self.assumption), at_review["payload"]["heads"]["assumption-a"])
        self.assertEqual(receipt["assumption_ref"], at_record["payload"]["heads"]["assumption-a"])

    def test_out_of_period_mapping_and_fanout_remain_unresolved(self):
        self.add_mapping(revision="out-of-period", at=CUTOFF, mutate=lambda p: p.update(valid_period={"start": "2026-10-07", "end": "2026-10-08"}))
        task = self.task()
        self.assertIn("UNRESOLVED_MAPPING", task["payload"]["block_reasons"])
        self.assertCode("BLOCKED_TASK", self.repo.commit_review, self.actor, self.request(task))
        self.assertCode("UNRESOLVED_MAPPING", self.add_mapping, ident="fanout", mutate=lambda p: p.update(cardinality="one_to_many"))

    def test_many_to_one_is_explicit_aggregate_representation(self):
        self.repo = self.make_repository()
        second_entity = {"entity_id": "fictional-unit-b", "entity_type": "GeneratingUnit"}
        payload = copy.deepcopy(self.case_record["payload"])
        payload["entities"].append(second_entity)
        payload["representations"][0]["target_type"] = "ModeledAggregate"
        self.repo.register_case(self.actor, self.record("Case", self.case, "1", payload))
        self.source, self.passage = self.add_source()
        self.mapping = self.add_mapping(mutate=lambda p: p.update(entities=[self.f["entity"], second_entity], cardinality="many_to_one"))
        self.assumption = self.repo.seed_assumption(self.actor, "assumption-a", "1", SEED, {
            "case_id": self.case, "entity": self.f["entity"], "proposition": "Explicit synthetic aggregate input",
            "value": self.f["value"], "valid_period": self.f["valid_period"], "representation_id": self.f["representation_id"],
            "input_field": self.f["input_field"], "mapping_ref": reference(self.mapping)}, "Synthetic aggregate initial state")
        task = self.task()
        self.assertEqual("compiled", task["payload"]["status"])
        self.assertEqual("ModeledAggregate", task["payload"]["model_representation"]["target_type"])
        self.assertEqual("GeneratingUnit", task["payload"]["assumption_definition"]["entity"]["entity_type"])
        self.repo.commit_review(self.actor, self.request(task))
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        self.assertEqual("many_to_one", scenario["payload"]["delta"]["cardinality"])

    def test_background_assumption_change_invalidates_existing_proposal(self):
        payload = {"case_id": self.case, "entity": self.f["entity"], "proposition": "Separate synthetic background position",
            "value": self.f["value"], "valid_period": self.f["valid_period"], "representation_id": self.f["representation_id"],
            "input_field": self.f["input_field"], "mapping_ref": reference(self.mapping)}
        self.repo.seed_assumption(self.actor, "background", "1", SEED, payload, "Synthetic second initial position")
        self.repo.commit_review(self.actor, self.request())
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        snapshot = self.repo.build_snapshot(self.actor, self.case, TODAY, LATER)
        task = self.repo.compile_task(self.actor, self.case, reference(snapshot), "background", CUTOFF, LATER)
        request = self.request(task, key="background-review", at=LATER)
        self.repo.commit_review(self.actor, request)
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(scenario)))
        self.assertCode("STALE_DEPENDENCY", self.repo.export_scenario, self.actor, self.case, reference(scenario))

    def test_new_mapping_identity_partial_overlap_invalidates_existing_proposal(self):
        # A new ID does not supersede the old mapping, but changes identity resolution.
        self.f["valid_period"] = {"start": "2026-10-06T00:00:00Z", "end": "2026-10-07T00:00:00Z"}
        self.mapping = self.add_mapping(revision="instant-period", at=CUTOFF, mutate=lambda p: p.update(valid_period=self.f["valid_period"]))
        # Seed a separate assumption whose affected period uses those instants.
        self.repo.seed_assumption(self.actor, "instant-assumption", "1", CUTOFF, {
            "case_id": self.case, "entity": self.f["entity"], "proposition": "Synthetic instant period input",
            "value": self.f["value"], "valid_period": self.f["valid_period"], "representation_id": self.f["representation_id"],
            "input_field": self.f["input_field"], "mapping_ref": reference(self.mapping)}, "Synthetic instant seed")
        snapshot = self.repo.build_snapshot(self.actor, self.case, CUTOFF, TODAY)
        task = self.repo.compile_task(self.actor, self.case, reference(snapshot), "instant-assumption", CUTOFF, TODAY)
        self.repo.commit_review(self.actor, self.request(task))
        scenario = self.repo.prepare_scenario(self.actor, self.case, "review-a", TODAY)
        heads = self.repo.heads(self.actor, self.case)
        mapping = self.add_mapping(ident="new-overlapping-id", at=LATER, mutate=lambda p: p.update(valid_period={"start": "2026-10-06T12:00:00Z", "end": "2026-10-07T00:00:00Z"}))
        self.assertEqual({"status": "stale"}, self.repo.draft_status(self.actor, self.case, reference(scenario)))
        self.assertCode("STALE_DEPENDENCY", self.repo.export_scenario, self.actor, self.case, reference(scenario))
        self.assertCode("UNRESOLVED_MAPPING", self.repo.prepare_scenario, self.actor, self.case, "review-a", LATER)
        fresh_snapshot = self.repo.build_snapshot(self.actor, self.case, LATER, LATER)
        fresh = self.repo.compile_task(self.actor, self.case, reference(fresh_snapshot), "instant-assumption", CUTOFF, LATER)
        self.assertIn("AMBIGUOUS_MAPPING", fresh["payload"]["block_reasons"])
        self.assertEqual(heads, self.repo.heads(self.actor, self.case))
        impacts = self.repo._records_in(self.actor.tenant_id, self.case, "DependencyImpact")
        self.assertTrue(any(i["payload"]["changed_ref"] == reference(mapping) and i["payload"]["previous_ref"] is None for i in impacts))

    def test_a_synthetic_seed_decision_stays_synthetic_initial(self):
        assumption = self.repo.read(self.actor, self.case, reference(self.assumption))
        seed = self.repo.read(self.actor, self.case, assumption["payload"]["accepted_review_ref"])
        self.assertEqual("seed", seed["payload"]["disposition"])
        self.assertIs(True, seed["payload"]["synthetic_initial"])
        self.assertEqual((True, None), provenance(seed["payload"]))


PERMISSION = "perm:local-signed:2026-10-13"
REGISTRY = frozenset({PERMISSION})


class H0V2Case(unittest.TestCase):
    """h0.v2: a real case under an injected registry, the typed basis, judgment_ref.

    Every record here is fictional; the permission identifier is a local test grant
    standing in for the drafted file under docs/work/permissions/, which is unsigned
    and therefore grants nothing. No backend, model or network is contacted.
    """

    def setUp(self):
        self.f = copy.deepcopy(FIXTURE)
        self.repo = InMemoryRepository(permissions=REGISTRY)
        self.actor = ActorContext(self.f["actor_id"], self.f["tenant_id"], frozenset({self.f["case_id"]}), frozenset({"synthetic-public", "synthetic-private"}), True)
        self.case = self.f["case_id"]
        model = {"representation_id": self.f["representation_id"], "target_type": "GeneratingUnit", "model_version": "synthetic-model.v1", "input_fields": {self.f["input_field"]: {"quantity_kind": self.f["value"]["quantity_kind"], "unit": "MW"}}}
        self.case_record = self.record("Case", self.case, "1", {"permitted_actors": [self.actor.actor_id], "synthetic": False, "permission_ref": PERMISSION, "entities": [self.f["entity"]], "representations": [model]})
        self.repo.register_case(self.actor, self.case_record)
        self.source, self.passage = self.add_source()
        self.mapping = self.add_mapping()
        self.assumption = self.repo.seed_assumption(self.actor, "assumption-a", "1", SEED, {
            "case_id": self.case, "entity": self.f["entity"], "proposition": "Assumed available capacity under the signed copy",
            "value": self.f["value"], "valid_period": self.f["valid_period"], "representation_id": self.f["representation_id"],
            "input_field": self.f["input_field"], "mapping_ref": reference(self.mapping)}, "Real signed-case initial state")

    def real(self, payload):
        """The pair every real record carries; the case fixes it for the whole case."""
        return dict(payload, synthetic=False, permission_ref=PERMISSION)

    def record(self, kind, ident, revision, payload, at=SEED):
        return make_record(kind, self.actor.tenant_id, self.case, ident, revision, at, payload, permissions=REGISTRY)

    def assertCode(self, code, call, *args, **kwargs):
        with self.assertRaises(ReviewError) as caught:
            call(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return str(caught.exception)

    def add_source(self, ident="source-a", revision="1", known=SEED, basis=None, at=SEED):
        text = self.f["source_text"]
        data = text.encode("utf-8")
        payload = self.real({"source_id": ident, "source_version": revision, "source_byte_digest": hashlib.sha256(data).hexdigest(),
            "original_text": text, "lineage_id": ident, "publisher": "fictional issuer under the signed copy", "published_at": "2026-09-30",
            "known_at": known, "access_policy_ref": "synthetic-public",
            "availability_basis": {"basis_kind": "feed_logged_at", "basis_ref": "advisory posting 2026-09-30T17:00:00Z", "note": ""} if (basis is None and known) else basis,
            "unknown_reason": "synthetic unknown availability" if known is None else None, "copied_from": None})
        source = self.record("SourceVersion", ident, revision, payload, at)
        self.repo.register(self.actor, source, source_bytes=data)
        quote = self.f["quote"] if self.f["quote"] in text else text
        start = text.index(quote)
        span = self.record("Passage", "passage:" + ident, revision, self.real({
            "source_ref": reference(source), "source_id": ident, "source_version": revision,
            "source_byte_digest": source["payload"]["source_byte_digest"], "start": start, "end": start + len(quote),
            "quote": quote, "quote_digest": hashlib.sha256(quote.encode("utf-8")).hexdigest()}), at)
        self.repo.register(self.actor, span)
        return source, span

    def add_mapping(self, ident="mapping-a", revision="1", at=SEED):
        mapping = self.record("MappingRevision", ident, revision, self.real({
            "entities": [self.f["entity"]], "representation_id": self.f["representation_id"], "input_field": self.f["input_field"],
            "cardinality": "one_to_one", "valid_period": self.f["valid_period"], "status": "reviewed",
            "reviewer": self.actor.actor_id, "reviewed_at": at, "source_refs": [reference(self.source)]}), at)
        self.repo.register(self.actor, mapping)
        return mapping

    def task(self, *, audit=CUTOFF, info=CUTOFF, at=TODAY):
        snapshot = self.repo.build_snapshot(self.actor, self.case, audit, at)
        return self.repo.compile_task(self.actor, self.case, reference(snapshot), "assumption-a", info, at)

    def request(self, task, disposition="retain", key="real-review", at=TODAY, judgment_ref=None):
        request = {"case_id": self.case, "request_id": key, "idempotency_key": key, "task_ref": reference(task),
            "snapshot_digest": task["payload"]["snapshot_ref"]["content_digest"], "expected_assumption_head": task["payload"]["assumption_ref"],
            "expected_outlook_head": self.repo.heads(self.actor, self.case)["outlook"], "disposition": disposition,
            "rationale": "Analysis under the signed copy", "reviewed_at": at, "recorded_at": at,
            "new_value": dict(self.f["value"], value="+8.25") if disposition == "revise" else None}
        if judgment_ref is not None:
            request["judgment_ref"] = judgment_ref
        return request

    def judgment(self, task, key="judgment-a", execution_mode="live_inference"):
        """One saved judgment artifact for the task, through the repository's own port."""
        answer = {"label": "challenges", "explanation": "The quoted claim does not establish availability.",
            "citations": [{"passage_index": 0, "quote": task["payload"]["context"][0]["quote"]}],
            "alternatives": ["Availability may be confirmed later."], "unknowns": ["Benchmarking status is unstated."]}
        metadata = {"provider": "local-fixture", "model": "synthetic-model", "model_version": "synthetic-contract.v1",
            "execution_mode": execution_mode, "prompt_version": PROMPT_VERSION,
            "request_digest": compute_content_digest({"prompt_version": PROMPT_VERSION, "input": key}),
            "output_digest": compute_content_digest(answer)}
        return self.repo.save_judgment(self.actor, self.case, reference(task), key, answer, metadata, TODAY)

    def v1(self, record):
        """The same payload in a v1 envelope; the v1 rules are the frozen ones."""
        raw = {k: v for k, v in record.items() if k != "content_digest"}
        raw["schema_version"] = "h0.v1"
        raw["content_digest"] = compute_content_digest(raw)
        return raw

    def test_a_real_case_runs_end_to_end_and_every_record_carries_the_case_pair(self):
        task = self.task()
        artifact = self.judgment(task)
        receipt = self.repo.commit_review(self.actor, self.request(task, "retain", judgment_ref=reference(artifact)))
        decision = self.repo.read(self.actor, self.case, receipt["decision_ref"])
        self.assertEqual(reference(artifact), decision["payload"]["judgment_ref"])
        self.assertEqual("no_change", self.repo.read(self.actor, self.case, receipt["outlook_ref"])["payload"]["difference"]["kind"])
        self.repo.commit_review(self.actor, self.request(task, "revise", key="real-revise", at=LATER, judgment_ref=reference(artifact)))
        proposal = self.repo.prepare_scenario(self.actor, self.case, "real-revise", LATER)
        self.assertEqual("proposal_only", proposal["payload"]["execution"])
        records = self.repo._records_in(self.actor.tenant_id, self.case)
        self.assertEqual({"Case", "SourceVersion", "Passage", "MappingRevision", "AssumptionRevision", "BeliefSnapshot",
                          "CompiledTask", "JudgmentArtifact", "ReviewDecision", "OutlookRevision", "DependencyImpact",
                          "ScenarioProposal"}, {r["record_kind"] for r in records})
        for record in records:
            with self.subTest(kind=record["record_kind"], record=record["record_id"]):
                self.assertEqual((False, PERMISSION), provenance(record["payload"], REGISTRY))
                self.assertEqual(PERMISSION, record["payload"].get("permission_ref"))
        self.assertEqual({"h0.v2"}, {r["schema_version"] for r in records})
        workspace = self.repo.workspace(self.actor, self.case)
        self.assertEqual((False, PERMISSION), (workspace["synthetic"], workspace["permission_ref"]))

    def test_a_real_seed_decision_is_not_labelled_synthetic_initial(self):
        # The seed's initial-acceptance label mirrors the case's provenance, so a real
        # case's seed decision reads false and can never contradict its own pair.
        assumption = self.repo.read(self.actor, self.case, reference(self.assumption))
        seed = self.repo.read(self.actor, self.case, assumption["payload"]["accepted_review_ref"])
        self.assertEqual("seed", seed["payload"]["disposition"])
        self.assertIs(False, seed["payload"]["synthetic_initial"])
        self.assertEqual((False, PERMISSION), provenance(seed["payload"], REGISTRY))
        # A v2 seed decision whose label contradicts its pair is refused in either direction.
        self.assertCode("INVALID_RECORD", self.record, "ReviewDecision", "seed:forged-real", "1",
                        dict(seed["payload"], synthetic_initial=True))
        self.assertCode("INVALID_RECORD", self.record, "ReviewDecision", "seed:forged-synthetic", "1",
                        dict(seed["payload"], synthetic=True, permission_ref=None, synthetic_initial=False))
        # The v1 rules are unchanged: a v1 envelope still requires `synthetic_initial: true`.
        raw = {k: v for k, v in seed.items() if k != "content_digest"}
        raw["schema_version"] = "h0.v1"
        raw["payload"] = {k: v for k, v in raw["payload"].items() if k not in ("synthetic", "permission_ref")}
        raw["payload"]["synthetic_initial"] = True
        raw["content_digest"] = compute_content_digest(raw)
        self.assertEqual("h0.v1", validate_record(raw)["schema_version"])
        raw["payload"] = dict(raw["payload"], synthetic_initial=False)
        raw["content_digest"] = compute_content_digest(raw)
        self.assertCode("INVALID_RECORD", validate_record, raw)

    def test_a_real_case_replays_read_only_and_refuses_a_changed_request_under_one_key(self):
        task = self.task()
        artifact = self.judgment(task)
        request = self.request(task, "investigate", judgment_ref=reference(artifact))
        first = self.repo.commit_review(self.actor, request)
        self.assertEqual(first, self.repo.commit_review(self.actor, request))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))
        self.assertCode("IDEMPOTENCY_CONFLICT", self.repo.commit_review, self.actor, dict(request, judgment_ref=None))
        self.assertCode("IDEMPOTENCY_CONFLICT", self.repo.commit_review, self.actor, dict(request, rationale="a different reading"))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))

    def test_an_omitted_and_an_explicit_null_judgment_reference_are_one_request(self):
        # Absent and explicit null both mean "no reference" and normalize to one
        # idempotency digest, so a retry under the other spelling replays instead of
        # conflicting — in either order.
        task = self.task()
        for key, first in (("omit-first", {}), ("null-first", {"judgment_ref": None})):
            with self.subTest(first=first):
                base = self.request(task, "investigate", key=key)
                request = dict(base, **first)
                other = base if first else dict(base, judgment_ref=None)
                receipt = self.repo.commit_review(self.actor, request)
                self.assertEqual(receipt, self.repo.commit_review(self.actor, other))
        self.assertEqual(2, len(self.repo.history(self.actor, self.case)))

    def test_the_judgment_reference_must_name_this_task_s_artifact(self):
        task, other_task = self.task(), self.task(info=TODAY)
        artifact, foreign = self.judgment(task), self.judgment(other_task, key="judgment-other")
        recorded = self.repo.commit_review(self.actor, self.request(task, "investigate", key="cited", judgment_ref=reference(artifact)))
        decision = self.repo.read(self.actor, self.case, recorded["decision_ref"])
        self.assertEqual(reference(artifact), decision["payload"]["judgment_ref"])
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))
        for bad in (reference(foreign), reference(other_task), reference(task),
                    dict(reference(artifact), record_id="absent"),
                    dict(reference(artifact), content_digest="0" * 64)):
            with self.subTest(ref=bad):
                self.assertCode("JUDGMENT_TASK_MISMATCH", self.repo.commit_review, self.actor,
                                self.request(task, "investigate", key="wrong-" + bad["record_id"][:20], judgment_ref=bad))
        for bad in ("ref", {"record_id": artifact["record_id"]}, {"record_kind": "JudgmentArtifact"}, 7):
            with self.subTest(ref=bad):
                self.assertCode("INVALID_RECORD", self.repo.commit_review, self.actor,
                                self.request(task, "investigate", key="shape", judgment_ref=bad))
        self.assertEqual(1, len(self.repo.history(self.actor, self.case)))

    def test_a_synthetic_fixture_execution_mode_is_refused_on_a_real_case(self):
        task = self.task()
        self.assertCode("INVALID_RECORD", self.judgment, task, execution_mode="synthetic_fixture")
        self.assertEqual([], self.repo.workspace(self.actor, self.case)["judgments"])
        self.assertEqual((False, PERMISSION), provenance(self.judgment(self.task(), key="live")["payload"], REGISTRY))

    def fixture_answers(self, task):
        """Well-formed answers for every rendered question, as the fixture backend needs."""
        rendered = render_bundle(task, "synthetic-model")
        answers = {}
        for name, question in rendered["request"]["questions"].items():
            if question["type"] == "choice":
                token = question["criteria"]["presentation"][0]
                answers[name] = {"choice": token, "probabilities": {token: 1.0}}
            else:
                answers[name] = {"noul": 0.5}
        return answers

    def test_a_synthetic_fixture_bundle_cannot_carry_a_real_case_s_provenance(self):
        # The bundle validator carries the same v2 fixture rule as the single judgment:
        # a synthetic fixture is synthetic content, so the save on a real case is
        # refused after the backend ran and before anything is written.
        task = self.task()
        backend = FixtureSystemOne("synthetic-fixture", "synthetic-model", self.fixture_answers(task))
        before = len(self.repo._records)
        self.assertCode("INVALID_RECORD", SystemOneService(backend).generate, self.repo, self.actor,
                        self.case, reference(task), "probe-real", lambda: TODAY)
        self.assertEqual(1, len(backend.requests))  # the backend ran; the answer was not kept
        self.assertEqual(before, len(self.repo._records))
        self.assertEqual([], self.repo.workspace(self.actor, self.case)["probe_bundles"])
        # Nothing was stored, so no decision can cite a fixture-generated real artifact.
        self.assertEqual([], [r for r in self.repo._records_in(self.actor.tenant_id, self.case)
                              if r["record_kind"] == "ProbeBundleArtifact"])

    def test_real_records_are_refused_without_a_signed_permission(self):
        for ref in (None, "perm:never-signed", "   "):
            with self.subTest(permission_ref=ref):
                payload = dict(self.case_record["payload"], permission_ref=ref)
                self.assertCode("PERMISSION_UNKNOWN", make_record, "Case", self.actor.tenant_id, self.case,
                                "case-x", "1", SEED, payload, permissions=REGISTRY)
        mixed = dict(self.case_record["payload"], synthetic=True)
        self.assertCode("INVALID_RECORD", make_record, "Case", self.actor.tenant_id, self.case,
                        "case-y", "1", SEED, mixed, permissions=REGISTRY)

    def test_the_checkout_registry_grants_only_signed_files(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue(sorted((root / "docs" / "work" / "permissions").glob("*.md")))
        registry = load_permissions(root)
        self.assertNotIn(PERMISSION, registry)
        # The owner signed the WESM company-copy record on 2026-10-13, so the
        # checkout's own registry now grants that identifier (and nothing drafted).
        self.assertIn("perm:wesm-company-copy:2026-10-13", registry)
        # A local directory proves the rule without depending on the owner's signature:
        # a signed file grants its identifier, a drafted one grants nothing.
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "docs" / "work" / "permissions"
            target.mkdir(parents=True)
            (target / "signed.md").write_text(
                "Permission record\n\nStatus: signed by the owner, 2026-10-14\n\n"
                "Permission identifier (the `permission_ref` value records cite): `perm:temp-signed:2026-10-14`\n", encoding="utf-8")
            (target / "draft.md").write_text(
                "Permission record\n\nStatus: **draft, unsigned**. Drafted today.\n\n"
                "Permission identifier (the `permission_ref` value records cite): `perm:temp-draft`\n", encoding="utf-8")
            self.assertEqual(frozenset({"perm:temp-signed:2026-10-14"}), load_permissions(scratch))

    def test_a_real_case_needs_a_registry_the_repository_holds(self):
        # The record itself validates under the injected registry; a repository holding
        # no grant for it refuses to store the case at all.
        unsigned = InMemoryRepository()
        self.assertCode("PERMISSION_UNKNOWN", unsigned.register_case, self.actor, self.case_record)
        self.assertEqual(0, len(unsigned._records))

    def test_no_mixed_case_is_stored_in_either_direction(self):
        synthetic_source = self.record("SourceVersion", "mixed", "1", dict(self.source["payload"], synthetic=True, permission_ref=None))
        self.assertCode("CASE_PROVENANCE_MISMATCH", self.repo.register, self.actor, synthetic_source,
                        source_bytes=self.source["payload"]["original_text"].encode("utf-8"))
        # The reverse: a synthetic case refuses a real record even where the registry
        # holds the identifier the record cites.
        synthetic = InMemoryRepository(permissions=REGISTRY)
        synthetic_case = make_record("Case", self.actor.tenant_id, self.case, self.case, "1", SEED,
                                     dict(self.case_record["payload"], synthetic=True, permission_ref=None))
        synthetic.register_case(self.actor, synthetic_case)
        self.assertCode("CASE_PROVENANCE_MISMATCH", synthetic.register, self.actor, self.source,
                        source_bytes=self.source["payload"]["original_text"].encode("utf-8"))
        self.assertCode("CASE_PROVENANCE_MISMATCH", synthetic.register, self.actor, self.mapping)
        self.assertCode("CASE_PROVENANCE_MISMATCH", synthetic.register, self.actor, self.passage)
        self.assertEqual([], synthetic._records_in(self.actor.tenant_id, self.case, "SourceVersion"))
        self.assertEqual(1, len(self.repo._records_in(self.actor.tenant_id, self.case, "SourceVersion")))

    def test_a_v2_pair_is_declared_never_defaulted_and_a_v1_record_cannot_be_real(self):
        # The pair is part of the v2 contract, not a default: a payload that omits
        # either key is refused, so an exported record can never lack the pair.
        for missing in ("synthetic", "permission_ref"):
            with self.subTest(missing=missing):
                payload = {k: v for k, v in self.source["payload"].items() if k != missing}
                self.assertCode("INVALID_RECORD", self.record, "SourceVersion", "undeclared", "1", payload)
                self.assertCode("INVALID_RECORD", provenance, payload, REGISTRY)
                self.assertCode("INVALID_RECORD", provenance, payload)
        # h0.v1 predates the pair, and the v1 rules already fix every v1 record as
        # synthetic, so its pair reads (True, None): a v1 record cannot be real.
        raw = {k: v for k, v in self.source.items() if k != "content_digest"}
        raw["schema_version"] = "h0.v1"
        raw["payload"] = {k: v for k, v in raw["payload"].items() if k not in ("synthetic", "permission_ref")}
        raw["payload"]["availability_basis"] = "synthetic receipt"
        raw["content_digest"] = compute_content_digest(raw)
        validated = validate_record(raw)
        self.assertEqual("h0.v1", validated["schema_version"])
        self.assertEqual((True, None), provenance(validated["payload"], REGISTRY, "h0.v1"))

    def test_a_v1_case_still_registers_and_its_pair_reads_as_the_v1_default(self):
        raw = {k: v for k, v in self.case_record.items() if k != "content_digest"}
        raw["schema_version"] = "h0.v1"
        raw["payload"] = {k: v for k, v in raw["payload"].items() if k != "permission_ref"}
        raw["payload"]["synthetic"] = True
        raw["content_digest"] = compute_content_digest(raw)
        repo = InMemoryRepository(permissions=REGISTRY)
        repo.register_case(self.actor, raw)
        # A v2 synthetic record fits the v1 case's pair; the real record does not.
        source = self.record("SourceVersion", "source-a", "1",
                             dict(self.source["payload"], synthetic=True, permission_ref=None))
        repo.register(self.actor, source, source_bytes=source["payload"]["original_text"].encode("utf-8"))
        self.assertCode("CASE_PROVENANCE_MISMATCH", repo.register, self.actor, self.source,
                        source_bytes=self.source["payload"]["original_text"].encode("utf-8"))
        self.assertEqual(1, len(repo._records_in(self.actor.tenant_id, self.case, "SourceVersion")))

    def test_typed_basis_forms_and_the_v1_string(self):
        self.assertEqual({"basis_kind", "basis_ref", "note"}, set(self.source["payload"]["availability_basis"]))
        for kind in sorted(BASIS_KINDS):
            with self.subTest(basis_kind=kind):
                record = self.record("SourceVersion", "basis-" + kind, "1", dict(self.source["payload"],
                    availability_basis={"basis_kind": kind, "basis_ref": "named in the capture log", "note": ""}))
                self.assertEqual(kind, record["payload"]["availability_basis"]["basis_kind"])
        self.assertCode("INVALID_RECORD", self.record, "SourceVersion", "basis-string", "1",
                        dict(self.source["payload"], availability_basis="synthetic receipt"))
        for bad in ({"basis_kind": "guessed", "basis_ref": "x", "note": ""},
                    {"basis_kind": "attested", "basis_ref": "  ", "note": ""},
                    {"basis_kind": "attested", "basis_ref": "x"},
                    {"basis_kind": "attested", "basis_ref": "x", "note": 1, "extra": ""},
                    []):
            with self.subTest(basis=bad):
                self.assertCode("INVALID_RECORD", self.record, "SourceVersion", "basis-bad", "1",
                                dict(self.source["payload"], availability_basis=bad))
        self.assertCode("INVALID_RECORD", self.record, "SourceVersion", "basis-unknown", "1",
                        dict(self.source["payload"], known_at=None, unknown_reason="no capture log",
                             availability_basis={"basis_kind": "capture_logged_at", "basis_ref": "x", "note": ""}))
        # The v1 rules are the frozen ones: the string form is theirs, an object is not.
        raw = {k: v for k, v in self.source.items() if k != "content_digest"}
        raw["schema_version"] = "h0.v1"
        raw["payload"] = dict(raw["payload"], availability_basis="synthetic receipt")
        raw["content_digest"] = compute_content_digest(raw)
        self.assertEqual("h0.v1", validate_record(raw)["schema_version"])
        self.assertCode("INVALID_RECORD", validate_record, self.v1(self.source))
        self.assertCode("INVALID_RECORD", validate_record, self.v1(self.case_record))

    def test_the_frozen_probe_bundle_corpus_still_validates(self):
        directory = Path(__file__).parent / "fixtures" / "probe-bundle"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        pairs, records, versions = sorted(directory.glob("pb-*.json")), 0, set()
        for path in pairs:
            for record in json.loads(path.read_text(encoding="utf-8"))["records"]:
                versions.add(validate_record(record)["schema_version"])
                records += 1
        self.assertEqual((25, 25, 135), (len(pairs), manifest["pairs"], records))
        # CORE-8 re-froze the set exactly once, under h0.v2 and policy v2, so the whole
        # corpus is now v2; the v1 branch keeps validating records the way v1 wrote them
        # (the basis cases above build one and read it back).
        self.assertEqual({"h0.v2"}, versions)


if __name__ == "__main__":
    unittest.main()
