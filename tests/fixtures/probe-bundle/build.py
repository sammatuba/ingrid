#!/usr/bin/env python3
"""Build and verify the labelled synthetic probe-bundle fixtures (EVAL-1).

This is a fixture generator and validator, not a test and not a runtime dependency:
nothing under ``src/`` imports it. It writes one self-contained JSON file per
evidence-assumption pair, the frozen annotation policy, and a manifest with the
frozen digests. ``--check`` rebuilds everything in memory and re-loads every
written file through the real repository, so a reviewer can prove that the
fixtures still validate and that no digest has drifted.

Every record, digest and expectation in the fixtures is produced by the
repository and judgment code in this checkout: records through
``src.review.records.make_record`` and the ``InMemoryRepository`` write path,
the compiled task through ``compile_task``, the request through
``render_bundle``, the composed label through ``compose`` and the stability
reading through ``receipt``. No number is copied by hand. No backend, model,
transport, credential or network call is made by any code path here: the
expected atomic answers are annotations, and the per-form answers that feed
``compose`` are derived from them in memory.

Usage, from the repository root::

    /usr/bin/python3 tests/fixtures/probe-bundle/build.py           # write
    /usr/bin/python3 tests/fixtures/probe-bundle/build.py --check   # verify
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import compute_content_digest  # noqa: E402
from src.judgment.bundle import BUNDLE_VERSION, QUESTION_SPECS, compose, receipt, render_bundle  # noqa: E402
from src.review import ActorContext, InMemoryRepository, make_record, reference  # noqa: E402
from src.review.records import validate_record  # noqa: E402

TENANT = "synthetic-tenant"
CASE = "synthetic-case"
ACTOR = "synthetic-analyst"
POLICY_REFS = ["synthetic-public"]
AT = "2026-10-01T09:00:00+08:00"
CUT = "2026-10-01T10:00:00+08:00"
LATE = "2026-10-01T11:30:00+08:00"
PERIOD = {"start": "2026-10-06", "end": "2026-10-07"}
MODEL_ID = "fixture-systemone"
FIXTURE_LABEL = "Fictional synthetic probe-bundle fixture; no real unit, operator, document or event"
#: The h0.v2 typed availability basis for every fixture source version: first availability
#: is asserted by the fixture author, not observed from a feed or a capture log, and the
#: basis records where availability comes from, never when.
BASIS = {"basis_kind": "attested", "basis_ref": "synthetic fixture author, task/CORE-8",
         "note": "Fictional synthetic source; first availability asserted by the fixture"}
#: Registered for every pair as the mapping's supporting source, deliberately without a
#: Passage record: it is a dependency of the compiled task, never part of its context.
MAPPING_NOTE_ID = "fictional-case-note"
MAPPING_NOTE = ("Fictional synthetic case note: Fictional Unit A is a GeneratingUnit of the fictional plant and the "
                "reviewed mapping to fictional-model-unit-a is one-to-one for the declared period.")

ENTITY_A = {"entity_id": "fictional-unit-a", "entity_type": "GeneratingUnit"}
ENTITY_A2 = {"entity_id": "fictional-unit-a2", "entity_type": "GeneratingUnit"}
MODEL = {
    "representation_id": "fictional-model-unit-a",
    "target_type": "GeneratingUnit",
    "model_version": "synthetic-model.v1",
    "input_fields": {
        "assumed_available_capacity": {"quantity_kind": "assumed_available_capacity", "unit": "MW"},
        "commercial_availability_from": {"quantity_kind": "commercial_availability_from", "unit": "MW"},
    },
}
ASSUMPTIONS = {
    "capacity": {
        "record_id": "assumption-capacity",
        "field": "assumed_available_capacity",
        "mapping_id": "mapping-capacity",
        "proposition": "Fictional Unit A is assumed available at 120 MW for the declared day",
        "value": {"value": "120.00", "quantity_kind": "assumed_available_capacity", "unit": "MW"},
    },
    "return": {
        "record_id": "assumption-return",
        "field": "commercial_availability_from",
        "mapping_id": "mapping-return",
        "proposition": "Fictional Unit A is assumed commercially available from 2026-10-06 at 120 MW",
        "value": {"value": "120.00", "quantity_kind": "commercial_availability_from", "unit": "MW"},
    },
}
EDGE_CLASSES = (
    "testing_vs_commercial",
    "planned_vs_confirmed_outage",
    "near_name_asset",
    "copied_lineage",
    "conditional_clause",
    "later_than_cutoff_document",
    "negation",
    "earlier_observed_return",
)
#: Where the frozen annotation deliberately disagrees with the composition table under
#: ``probe-bundle.v5``: the contestable earlier-observation row for both assumption kinds
#: (`pb-er-1`, whose direction now composes `mixed` through `direction_conflict`, and
#: `pb-er-2`), the near-name entity that a single-candidate mapping cannot express
#: (`pb-na-1`, `pb-na-3`), the lineage abstention with no prior label (`pb-cl-3`), and the
#: planned test on a capacity assumption (`pb-tc-3`, which the widened milestone row now
#: composes as `challenges` while the annotation stays `mixed` under the conditional rule).
#: Exact equality is asserted so a silent label change cannot pass.
DOCUMENTED_DISAGREEMENTS = ("pb-cl-3/t1", "pb-er-1/t1", "pb-er-2/t1", "pb-na-1/t1", "pb-na-3/t1", "pb-tc-3/t1")
QUESTIONS = {spec["id"]: spec["slug"] for spec in QUESTION_SPECS}


def policy() -> dict:
    """The frozen annotation policy; its digest is recorded before any backend run."""
    return {
        "policy_id": "probe-bundle-annotation.v2",
        "frozen_at": "2026-10-13",
        "scope": "Evidence-assumption pairs compiled from the H0 synthetic case (fictional units and sources). "
                 "The label is the relation of the supplied evidence to the assumption as stated, judged from the "
                 "passage text and the reviewed mapping alone, at the declared cutoffs.",
        "labels": {
            "supports": "Consistent with and directly relevant to the proposition.",
            "challenges": "Relevant reason to reconsider; does not establish falsity.",
            "mixed": "Supported elements pull in different directions.",
            "unrelated": "Does not bear on the proposition under the declared scope.",
            "insufficient": "Necessary meaning or context is missing.",
        },
        "assumption_kinds": {
            "assumed_available_capacity": "Supply outlook: the assumed value is available capacity (MW) over the "
                                          "assumption's validity period, and the assumed time is that period. An "
                                          "availability kind: the v5 availability-kind predicate reads the field's "
                                          "quantity kind from the model representation, so testing, outage and "
                                          "return events about the unit compose against the assumption.",
            "commercial_availability_from": "Return-date assumption: the proposition states the assumed commercial "
                                            "availability date and the value is the assumed capacity from that date; "
                                            "the assumed time is the stated date. An availability kind, and its "
                                            "evidence maps to the commercial_operation token: an entered commercial "
                                            "operation, or a return to service, is that event and not a "
                                            "commissioning milestone.",
        },
        "question_conventions": {
            "q1_identity": "The subject entity of the statement, chosen from the reviewed candidates of the pair's "
                           "mapping; cannot_tell when the passage names no reviewed candidate, including a clearly "
                           "different, non-candidate entity.",
            "q2_event": "The single event the passages describe for that entity: planned_outage, forced_outage, "
                        "return_to_service, derating, grid_alert, testing, commercial_operation, or other when none "
                        "of those is described. The vocabulary is the operator-advisory feed's own verbs: an outage "
                        "the passage states as planned, scheduled or extended is planned_outage; an outage or "
                        "shutdown the passage states with no plan is forced_outage (the feed's unplanned outage); a "
                        "return or restore, including a completed synchronisation back to service, is "
                        "return_to_service; a reduced capability is derating; a grid-level alert is grid_alert; "
                        "testing covers a test or commissioning state; commercial_operation covers reaching "
                        "commercial operation or the assumed commercial availability. synchronisation is not a "
                        "token: in the corpus it names a failed return (forced_outage) or a completed one "
                        "(return_to_service).",
            "q3_time": "The time the passage attributes to its reported event or condition: an explicit date or "
                       "instant, or, where none is stated, the passage's publication instant as the latest time the "
                       "condition is asserted. same means the stated time falls inside the assumed time; before and "
                       "after are strictly earlier and later; not_stated means the time reference cannot be located "
                       "against the assumed time.",
            "q4_conditional": "yes when the statement is conditional, planned, expected or subject to clearance "
                              "rather than confirmed; no when it is an unconditional statement of fact.",
            "q5_lineage": "yes when the passage repeats the content of an earlier source already present in the "
                          "supplied context, rather than adding new information.",
            "q6_observation": "yes when the passage reports something that happened or currently holds; no when it "
                              "reports a target, plan, expectation or schedule.",
            "q7_sufficiency": "yes when the supplied passages alone suffice to decide whether the assumption is "
                              "supported or challenged; no when they do not.",
            "q8_direction": "The direction a reader would take from the supplied passages alone, without the "
                            "decomposition; it is the single-render baseline of ablation A1 and does not follow the "
                            "composite label.",
        },
        "label_rules": [
            {"id": "scope", "rule": "Evidence about a clearly different entity (near-name or sister unit) does not "
                                    "bear on the assumption: unrelated."},
            {"id": "identity", "rule": "Evidence whose subject entity cannot be determined from the passage and the "
                                       "reviewed mapping is insufficient; an ambiguous mapping cannot change an "
                                       "assumption."},
            {"id": "lineage", "rule": "A passage that repeats an in-context earlier source takes the label of the "
                                      "repeated statement; repetition is never independent corroboration."},
            {"id": "milestone", "rule": "A testing or outage state is not an observation that the assumed "
                                        "availability holds at the assumed time."},
            {"id": "outage", "rule": "An outage, an extension of an outage, or a stated time later than the assumed "
                                     "time challenges the assumption as stated."},
            {"id": "conditional", "rule": "A conditional, planned or subject-to-clearance statement names a "
                                          "possibility, not the assumed fact: mixed (conditional support), unless the "
                                          "statement also asserts an outage or a later time, which is challenges."},
            {"id": "earlier_return", "rule": "An observed return earlier than the assumed time supports a supply "
                                             "outlook (assumed_available_capacity) and challenges a return-date "
                                             "assumption (commercial_availability_from) as stated, because the "
                                             "observed return contradicts the assumed date."},
            {"id": "insufficient", "rule": "Evidence whose meaning cannot be determined, or that is silent on the "
                                           "assumed time with no direction, is insufficient."},
        ],
        "evidence_set_rule": "When a compile's context holds several passages, each atomic answer describes the set; "
                             "where the passages disagree, the annotation follows the latest known statement about "
                             "the entity, and q5 records repetition.",
        "contestable_rule": "The composition row 'q3 = before and q6 = yes -> supports' (working paper 5.2) is "
                            "deliberately contestable. The pair set contains both assumption kinds for it so ablation "
                            "A1 can decide whether the row is kept. The frozen labels are the annotation and do not "
                            "follow the table.",
        "no_backend_rule": "Labels and the frozen digests are recorded before any backend run; they are annotations "
                           "of synthetic fixtures and are not analyst validation or model output.",
    }


def src(ident, statement, *, known, published="2026-09-30", lineage=None, copied=None,
        prefix="Fictional synthetic bulletin. ", publisher="Fictional newsletter"):
    return {"id": ident, "statement": statement, "prefix": prefix, "known_at": known, "published_at": published,
            "lineage_id": lineage or ident, "copied_from": copied, "publisher": publisher}


def compile_spec(at, atomic, label, rationale):
    """One compile of a pair. The audit cutoff is not per compile: the frozen pairing contract
    gives a pair a single shared snapshot, so only the information cutoff varies."""
    return {"at": at, "atomic": atomic, "label": label, "rationale": rationale}


def pair_specs() -> list[dict]:
    """The annotated pairs: passage text, declared cutoffs, expected atomic answers, labels."""
    early = "2026-09-30T14:00:00+08:00"
    specs = []

    # ---- testing vs commercial -------------------------------------------------
    specs.append({
        "pair_id": "pb-tc-1", "edge_class": "testing_vs_commercial", "kind": "return",
        "sources": [src("fictional-early-wire", "Fictional Unit A is testing at 40 MW; commercial availability is not "
                       "confirmed.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes",
                                         "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                                  "The statement says the unit is testing and that commercial availability is not "
                                  "confirmed. Under the milestone rule a testing state is not an observation of "
                                  "commercial availability, so the evidence challenges the return-date assumption as "
                                  "stated; the unconfirmed clause raises conditionality (q4) but does not change the "
                                  "challenge.")],
    })
    specs.append({
        "pair_id": "pb-tc-2", "edge_class": "testing_vs_commercial", "kind": "return",
        "sources": [src("fictional-operator-notice", "Fictional Unit A entered commercial operation at 00:30 on "
                       "2026-10-06 and is delivering 120 MW.", known="2026-10-06T08:00:00+08:00",
                       published="2026-10-06", prefix="Fictional synthetic operator notice. ")],
        "t0": "2026-10-06T09:00:00+08:00", "t1": "2026-10-06T09:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
                                  "supports",
                                  "A confirmed observation that the unit entered commercial operation on the assumed "
                                  "date at the assumed capacity. The assumed event at the assumed time, "
                                  "unconditionally (q4 = no), supports the assumption as stated.")],
    })
    specs.append({
        "pair_id": "pb-tc-3", "edge_class": "testing_vs_commercial", "kind": "capacity",
        "sources": [src("fictional-planning-note", "Fictional Unit A is scheduled to begin testing on 2026-10-06, "
                       "subject to clearance from the fictional system operator.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "testing", "q3": "same", "q4": "yes",
                                         "q5": "no", "q6": "no", "q7": "yes", "q8": "challenges"}, "mixed",
                                  "A planned test on the assumed day, subject to clearance and at an unstated "
                                  "capacity. Under the conditional rule this is conditional support (mixed): it names "
                                  "the assumed day and progress, but asserts no availability. The single-passage "
                                  "direction (q8) reads it as a challenge, which is what ablation A1 compares "
                                  "against the composite.")],
    })

    # ---- planned vs confirmed outage -------------------------------------------
    specs.append({
        "pair_id": "pb-po-1", "edge_class": "planned_vs_confirmed_outage", "kind": "capacity",
        "sources": [src("fictional-planned-outage", "Fictional Unit A will be taken out of service on 2026-10-06 "
                       "for a fictional planned repair, subject to final clearance.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "planned_outage", "q3": "same",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "A planned outage on the assumed day, subject to clearance. Under the outage rule "
                                  "an outage of the assumed unit during the assumed period challenges the "
                                  "availability assumption; the plan-versus-confirmed distinction is carried by q4 = "
                                  "yes and does not change the label.")],
    })
    specs.append({
        "pair_id": "pb-po-2", "edge_class": "planned_vs_confirmed_outage", "kind": "capacity",
        "sources": [src("fictional-operator-bulletin", "Fictional Unit A is out of service and remains unavailable "
                       "at 00:00 on 2026-10-06.", known="2026-10-06T00:30:00+08:00", published="2026-10-06",
                       prefix="Fictional synthetic operator bulletin. ")],
        "t0": "2026-10-06T09:00:00+08:00", "t1": "2026-10-06T09:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "forced_outage", "q3": "same",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "A confirmed observation that the unit is out of service at the start of the assumed "
                                  "day. The passage states no plan, schedule or clearance, so the event is a forced "
                                  "outage, not a planned one; the outage rule gives challenges with q4 = no, and "
                                  "PB-PO-1 is the same rule with a planned outage, so the pair separates plan from "
                                  "confirmation in the atomic answers while both labels agree.")],
    })
    specs.append({
        "pair_id": "pb-po-3", "edge_class": "planned_vs_confirmed_outage", "kind": "capacity",
        "sources": [src("fictional-extension-notice", "Fictional Unit A's fictional return has been extended; the "
                       "unit will not be available before 2026-10-08.", known="2026-10-01T14:00:00+08:00",
                       published="2026-10-01", prefix="Fictional synthetic extension notice. ")],
        "t0": "2026-10-01T15:00:00+08:00", "t1": "2026-10-01T15:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "planned_outage", "q3": "after",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "An extension of the outage with a stated date later than the assumed period. The "
                                  "extension of a return schedule is a planned outage whose q3 is after, per the v5 "
                                  "vocabulary; the outage rule and the later-time rule both give challenges. q3 = "
                                  "after is recorded from the stated 2026-10-08, and q4 = yes because the extension "
                                  "is an announced plan, not an observation of the extension itself.")],
    })

    # ---- near-name asset --------------------------------------------------------
    specs.append({
        "pair_id": "pb-na-1", "edge_class": "near_name_asset", "kind": "return",
        "sources": [src("fictional-sister-wire", "Fictional Unit A2, a sister unit at the same fictional plant, "
                       "returned to service on 2026-10-02.", known="2026-10-02T09:00:00+08:00",
                       published="2026-10-02")],
        "t0": "2026-10-02T10:00:00+08:00", "t1": "2026-10-02T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "cannot_tell", "q2": "commercial_operation", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "neither"},
                                  "unrelated",
                                  "The passage is about the near-name sister unit, which is not a reviewed candidate. "
                                  "Under the scope rule the annotator can see the subject is a different entity, so "
                                  "the evidence does not bear on the assumption: unrelated. The reviewed mapping has "
                                  "one candidate, so the only honest q1 is cannot_tell and the composition can only "
                                  "abstain with IDENTITY_UNKNOWN; the disagreement is deliberate and is what A1's "
                                  "abstention column measures.")],
    })
    specs.append({
        "pair_id": "pb-na-2", "edge_class": "near_name_asset", "kind": "return",
        "sources": [src("fictional-plant-roundup", "Fictional Unit A remains out of service; its sister unit "
                       "Fictional Unit A2 is testing at 40 MW.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "forced_outage", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "The passage is about the mapped unit, which is on outage, and mentions the "
                                  "near-name sister unit only incidentally. The identity question must not follow the "
                                  "near-name mention; the outage challenges the return-date assumption under the "
                                  "outage rule.")],
    })
    specs.append({
        "pair_id": "pb-na-3", "edge_class": "near_name_asset", "kind": "return",
        "sources": [src("fictional-clearance-notice", "Fictional Unit A2, not Fictional Unit A, was cleared for "
                       "commercial operation on 2026-10-06.", known="2026-10-06T09:00:00+08:00",
                       published="2026-10-06")],
        "t0": "2026-10-06T10:00:00+08:00", "t1": "2026-10-06T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "cannot_tell", "q2": "commercial_operation", "q3": "same",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "neither"},
                                  "unrelated",
                                  "The passage clears the near-name unit and explicitly excludes the mapped unit. "
                                  "The subject is a different entity, so the evidence is unrelated under the scope "
                                  "rule; the explicit mention of the mapped unit's name is the distractor this pair "
                                  "targets, and as in PB-NA-1 the single-candidate mapping leaves the composition an "
                                  "abstention, recorded as an abstention, not as a claim about the assumption.")],
    })

    # ---- copied lineage ---------------------------------------------------------
    specs.append({
        "pair_id": "pb-cl-1", "edge_class": "copied_lineage", "kind": "return",
        "sources": [src("fictional-wire-original", "Fictional Unit A is testing at 40 MW; commercial availability "
                       "is not confirmed.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes",
                                         "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                                  "The original wire statement: a testing state is not commercial availability, so "
                                  "the evidence challenges the return-date assumption under the milestone rule. This "
                                  "pair also supplies the lineage prior label that PB-CL-2 reuses.")],
    })
    specs.append({
        "pair_id": "pb-cl-2", "edge_class": "copied_lineage", "kind": "return",
        "sources": [src("fictional-wire-original", "Fictional Unit A is testing at 40 MW; commercial availability "
                       "is not confirmed.", known=early),
                    src("fictional-wire-relay", "Unit A is testing at 40 MW; commercial availability is not "
                       "confirmed.", known="2026-09-30T15:00:00+08:00", lineage="fictional-wire-original",
                       copied="fictional-wire-original", prefix="A fictional relay reprints the wire item. ")],
        "lineage": {"repeated_source_id": "fictional-wire-relay", "earlier_source_id": "fictional-wire-original",
                    "prior_pair_id": "pb-cl-1", "prior_label": "challenges"},
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes",
                                         "q5": "yes", "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                                  "The relay repeats the earlier wire statement already in the context. Under the "
                                  "lineage rule a repeat adds no independent information and takes the label of the "
                                  "repeated statement, so the frozen label equals PB-CL-1's challenges, and the "
                                  "composition's lineage_reuse row fires with the declared prior label.")],
    })
    specs.append({
        "pair_id": "pb-cl-3", "edge_class": "copied_lineage", "kind": "capacity",
        "sources": [src("fictional-outage-wire", "Fictional Unit A remains out of service for a fictional repair; "
                       "no return date is given.", known=early),
                    src("fictional-outage-relay", "Fictional Unit A remains out of service for a fictional repair; "
                       "no return date is given.", known="2026-09-30T15:00:00+08:00", lineage="fictional-outage-wire",
                       copied="fictional-outage-wire", prefix="A fictional relay reprints the outage item. ")],
        "lineage": {"repeated_source_id": "fictional-outage-relay", "earlier_source_id": "fictional-outage-wire",
                    "prior_pair_id": None, "prior_label": None},
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "forced_outage", "q3": "before",
                                         "q4": "no", "q5": "yes", "q6": "yes", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "A relay of an outage statement about a supply-outlook assumption, with no earlier "
                                  "bundle label declared for the repeated source. Under the lineage rule the repeat "
                                  "still takes the repeated statement's relation (challenges), while the composition "
                                  "must abstain with LINEAGE_NO_PRIOR because no prior label exists in the corpus. "
                                  "The abstention is deliberate and is counted by A1 and A2.")],
    })

    # ---- conditional clause -----------------------------------------------------
    specs.append({
        "pair_id": "pb-cc-1", "edge_class": "conditional_clause", "kind": "return",
        "sources": [src("fictional-may-return", "Fictional Unit A may return to commercial operation on "
                       "2026-10-06, subject to clearance by the fictional system operator.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "supports"},
                                  "mixed",
                                  "The assumed date is named, but the statement is subject to clearance. Under the "
                                  "conditional rule the statement is conditional support (mixed): it neither "
                                  "confirms the assumption nor rules it out.")],
    })
    specs.append({
        "pair_id": "pb-cc-2", "edge_class": "conditional_clause", "kind": "return",
        "sources": [src("fictional-conditional-date", "Fictional Unit A will be commercially available from "
                       "2026-10-06; the date holds only if the fictional interconnection works complete on time.",
                       known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "supports"},
                                  "mixed",
                                  "The assumed date is named with an explicit condition. The conditional rule again "
                                  "gives mixed; the single-passage direction reads the statement as support, which is "
                                  "the baseline A1 compares against.")],
    })
    specs.append({
        "pair_id": "pb-cc-3", "edge_class": "conditional_clause", "kind": "capacity",
        "sources": [src("fictional-no-date", "Fictional Unit A's return remains subject to the fictional "
                       "operator's clearance; no date has been set.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "not_stated",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "supports"},
                                  "mixed",
                                  "The statement is conditional and states no date, so q3 is not_stated by the time "
                                  "convention. The conditional rule and the no-stated-time row both give mixed for a "
                                  "direction that is not neither.")],
    })

    # ---- later-than-cutoff document --------------------------------------------
    specs.append({
        "pair_id": "pb-lc-1", "edge_class": "later_than_cutoff_document", "kind": "return",
        "t0": CUT, "t1": LATE,
        "sources": [src("fictional-early-wire", "Fictional Unit A is testing at 40 MW; commercial availability is "
                       "not confirmed.", known=early),
                    src("fictional-final-schedule", "Fictional commercial operation for Fictional Unit A begins on "
                       "2026-10-06 at 120 MW; the fictional operator states the schedule is final and not subject to "
                       "clearance.", known="2026-10-01T11:00:00+08:00", published="2026-10-01",
                       prefix="Fictional synthetic operator bulletin. ")],
        "compiles": [
            compile_spec("t0", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes", "q5": "no",
                                "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                         "At T0 only the testing statement is known; the final schedule is not yet available and is "
                         "omitted as LATER_AVAILABILITY. The testing state challenges the return-date assumption "
                         "under the milestone rule."),
            compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same", "q4": "no",
                                "q5": "no", "q6": "no", "q7": "yes", "q8": "supports"}, "supports",
                         "At T1 the confirmed final schedule for the assumed date joins the evidence set. Under the "
                         "evidence-set rule the set now names commercial operation at the assumed time, "
                         "unconditionally (q4 = no), so the assumption as stated is supported. The pair changes the "
                         "label from challenges to supports."),
        ],
    })
    specs.append({
        "pair_id": "pb-lc-2", "edge_class": "later_than_cutoff_document", "kind": "capacity",
        # The notice first becomes available at 2026-10-06T08:00 and reports a return that happened at 06:00
        # the same day, so both cutoffs (07:00 before the notice is available, 09:00 after) sit after the
        # reported event: the T1 annotation is an observation of a past return, never a future event read as
        # somehow confirmed.
        "t0": "2026-10-06T07:00:00+08:00", "t1": "2026-10-06T09:00:00+08:00",
        "sources": [src("fictional-outage-notice", "Fictional Unit A remains out of service for a fictional repair.",
                       known=early),
                    src("fictional-return-notice", "Fictional Unit A returned to service at 120 MW at 06:00 on "
                       "2026-10-06.", known="2026-10-06T08:00:00+08:00", published="2026-10-06",
                       prefix="Fictional synthetic operator bulletin. ")],
        "compiles": [
            compile_spec("t0", {"q1": "fictional-unit-a", "q2": "forced_outage", "q3": "before", "q4": "no",
                                "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                         "At T0 the return notice is not yet available and is omitted as LATER_AVAILABILITY; the "
                         "known passage reports the unit on outage before the assumed day, so the evidence "
                         "challenges the availability assumption under the outage rule."),
            compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same", "q4": "no",
                                "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"}, "supports",
                         "At T1 the return notice, which first becomes available at 08:00 after the 06:00 return "
                         "it reports, joins the set: the unit returned to service at the assumed capacity on the "
                         "assumed day. Under the evidence-set rule the set now reports the assumed event at the "
                         "assumed time, so the assumption is supported; the pair changes the label from challenges "
                         "to supports."),
        ],
    })
    specs.append({
        "pair_id": "pb-lc-3", "edge_class": "later_than_cutoff_document", "kind": "return",
        "t0": CUT, "t1": LATE,
        "sources": [src("fictional-testing-wire", "Fictional Unit A is testing at 40 MW; commercial availability "
                       "is not confirmed.", known=early),
                    src("fictional-testing-update", "Fictional Unit A continues testing at 40 MW; no commercial "
                       "availability date is set.", known="2026-10-01T11:00:00+08:00", published="2026-10-01",
                       prefix="Fictional synthetic operator notice. ")],
        "compiles": [
            compile_spec("t0", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes", "q5": "no",
                                "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                         "At T0 only the testing statement is known and it challenges the return-date assumption "
                         "under the milestone rule; the update is omitted as LATER_AVAILABILITY."),
            compile_spec("t1", {"q1": "fictional-unit-a", "q2": "testing", "q3": "before", "q4": "yes", "q5": "no",
                                "q6": "yes", "q7": "yes", "q8": "challenges"}, "challenges",
                         "At T1 the later notice confirms the same testing state and adds no date. The evidence set "
                         "is unchanged in meaning, so the label stays challenges and the pair's changed set is empty: "
                         "the null-diff case for cutoff pairing, which creates no review obligation."),
        ],
    })

    # ---- negation ---------------------------------------------------------------
    specs.append({
        "pair_id": "pb-ng-1", "edge_class": "negation", "kind": "return",
        "sources": [src("fictional-negated-date", "Fictional Unit A is not expected to reach commercial operation "
                       "before 2026-10-09.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "after",
                                         "q4": "yes", "q5": "no", "q6": "no", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "A negated expectation with a stated date later than the assumed time. q3 = after "
                                  "is read from 2026-10-09, after the assumed 2026-10-06, so the later-time rule "
                                  "challenges the assumption; reading 'not ... before' as support is the polarity "
                                  "failure this pair targets.")],
    })
    specs.append({
        "pair_id": "pb-ng-2", "edge_class": "negation", "kind": "return",
        "sources": [src("fictional-double-negative", "The fictional bulletin did not deny that Fictional Unit A "
                       "could return in October; no date is given.", known=early)],
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "other", "q3": "not_stated", "q4": "yes",
                                         "q5": "no", "q6": "no", "q7": "no", "q8": "neither"}, "insufficient",
                                  "The passage denies a denial and asserts nothing determinate. Under the insufficient "
                                  "rule the meaning cannot be determined, so q7 is no and the sufficiency gate "
                                  "abstains before any other row reads the answers; the annotation and the composition "
                                  "agree on insufficient.")],
    })
    specs.append({
        "pair_id": "pb-ng-3", "edge_class": "negation", "kind": "return",
        "sources": [src("fictional-return-correction", "Fictional Unit A is not out of service; the unit returned "
                       "to commercial operation on 2026-10-06.", known="2026-10-06T09:00:00+08:00",
                       published="2026-10-06", prefix="Fictional synthetic market note. ")],
        "t0": "2026-10-06T10:00:00+08:00", "t1": "2026-10-06T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "same",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
                                  "supports",
                                  "The passage negates an outage and reports the return at the assumed time. Reading "
                                  "the word 'out' as an outage would be the polarity error; the event is commercial "
                                  "operation at the assumed time, so the evidence supports the return-date "
                                  "assumption as stated.")],
    })

    # ---- earlier observed return, both assumption kinds -------------------------
    specs.append({
        "pair_id": "pb-er-1", "edge_class": "earlier_observed_return", "kind": "return",
        "sources": [src("fictional-early-return", "Fictional Unit A entered commercial operation at 08:00 on "
                       "2026-10-03 at 120 MW.", known="2026-10-03T09:00:00+08:00", published="2026-10-03")],
        "t0": "2026-10-03T10:00:00+08:00", "t1": "2026-10-03T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"},
                                  "challenges",
                                  "An observed return two days before the assumed date. Under the earlier-return rule "
                                  "this challenges a return-date assumption as stated: the observed return "
                                  "contradicts the assumed date. The composition's earlier_observation row is gated "
                                  "on direction, so this bundle composes `mixed` through direction_conflict "
                                  "(q8 = challenges); the table and the annotation deliberately disagree here, and "
                                  "A1 decides whether the row is kept.")],
    })
    specs.append({
        "pair_id": "pb-er-2", "edge_class": "earlier_observed_return", "kind": "return",
        "sources": [src("fictional-market-report", "Fictional Unit A was recorded delivering 120 MW from "
                       "2026-10-03.", known="2026-10-03T09:00:00+08:00", published="2026-10-03",
                       prefix="Fictional synthetic market report. ")],
        "t0": "2026-10-03T10:00:00+08:00", "t1": "2026-10-03T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
                                  "challenges",
                                  "A second observed earlier return for the same assumption kind. The single-passage "
                                  "direction reads early availability as good news (supports), while the frozen label "
                                  "follows the earlier-return rule and challenges the assumed date as stated. "
                                  "Together with PB-ER-1 this gives A1 two kind-B instances of the contestable row.")],
    })
    specs.append({
        "pair_id": "pb-er-3", "edge_class": "earlier_observed_return", "kind": "capacity",
        "sources": [src("fictional-capacity-report", "Fictional Unit A entered commercial operation at 08:00 on "
                       "2026-10-05 at 120 MW.", known="2026-10-05T09:00:00+08:00", published="2026-10-05")],
        "t0": "2026-10-05T10:00:00+08:00", "t1": "2026-10-05T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "commercial_operation", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
                                  "supports",
                                  "An observed return before the assumed period for a supply-outlook assumption. "
                                  "Under the earlier-return rule an earlier observation supports a supply outlook, "
                                  "and the composition's earlier_observation row agrees: this is the kind-A half of "
                                  "the contestable row, where the table and the annotation agree.")],
    })
    specs.append({
        "pair_id": "pb-er-4", "edge_class": "earlier_observed_return", "kind": "capacity",
        "sources": [src("fictional-synchronisation-report", "Fictional Unit A was synchronised and delivering "
                       "120 MW from 2026-10-05.", known="2026-10-05T09:00:00+08:00", published="2026-10-05")],
        "t0": "2026-10-05T10:00:00+08:00", "t1": "2026-10-05T10:00:00+08:00",
        "compiles": [compile_spec("t1", {"q1": "fictional-unit-a", "q2": "return_to_service", "q3": "before",
                                         "q4": "no", "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
                                  "supports",
                                  "The passage reports a completed synchronisation back to service — in the "
                                  "operator feed that is a return/restore event, not a commissioning milestone — "
                                  "before the assumed period for a supply-outlook assumption. The observed "
                                  "condition before the assumed period supports the outlook under the earlier-return "
                                  "rule, and the composition's earlier_observation row agrees (q8 = supports, not "
                                  "challenges).")],
    })
    return specs


def canonical_answers(bundle: dict, atomic: dict, probability: float = 0.8) -> dict:
    """Per-form answers whose top option is the expected canonical answer in every form."""
    answers = {}
    for spec in QUESTION_SPECS:
        for form in range(bundle["forms"]):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            criteria = bundle["request"]["questions"][name]["criteria"]
            if spec["type"] == "choice":
                tokens = [token for token, option in criteria["options"].items() if option == atomic[spec["id"]]]
                if len(tokens) != 1:
                    raise SystemExit(f"{name}: expected option {atomic[spec['id']]!r} is not uniquely presented")
                answers[name] = {"choice": tokens[0], "probabilities": {tokens[0]: probability}}
            else:
                value = probability if criteria["options"]["yes"] == "yes" else 1 - probability
                if atomic[spec["id"]] != "yes":
                    value = 1 - value
                answers[name] = {"noul": value}
    return answers


def plus_minutes(value: str, minutes: int) -> str:
    return (datetime.fromisoformat(value) + timedelta(minutes=minutes)).isoformat()


def build_pair(spec: dict, policy_digest: str) -> dict:
    """Compile the pair through the repository and collect every derived expectation."""
    assumption = ASSUMPTIONS[spec["kind"]]
    actor = ActorContext(ACTOR, TENANT, frozenset({CASE}), frozenset(POLICY_REFS), True)
    repo = InMemoryRepository()
    t0 = spec.get("t0", CUT)
    t1 = spec.get("t1", t0)

    def record(kind, ident, payload, revision="1"):
        # Every h0.v2 payload declares the case's (synthetic, permission_ref) pair; an
        # omitted key is refused. These fixtures are wholly synthetic, so the pair is
        # (True, None), and the repository's derived writes copy it from this Case.
        return make_record(kind, TENANT, CASE, ident, revision, AT,
                           {"synthetic": True, "permission_ref": None, **payload})

    case = record("Case", CASE, {
        "permitted_actors": [ACTOR, "synthetic-other"], "synthetic": True,
        "entities": [ENTITY_A, ENTITY_A2], "representations": [MODEL]})
    repo.register_case(actor, case)
    records = [case]
    note_bytes = MAPPING_NOTE.encode("utf-8")
    note = record("SourceVersion", MAPPING_NOTE_ID, {
        "source_id": MAPPING_NOTE_ID, "source_version": "1",
        "source_byte_digest": hashlib.sha256(note_bytes).hexdigest(), "original_text": MAPPING_NOTE,
        "lineage_id": MAPPING_NOTE_ID, "publisher": "Fictional case registry", "published_at": "2026-10-01",
        "known_at": AT, "access_policy_ref": POLICY_REFS[0], "availability_basis": dict(BASIS),
        "unknown_reason": None, "copied_from": None})
    repo.register(actor, note, source_bytes=note_bytes)
    records.append(note)
    sources = {}
    for item in spec["sources"]:
        text = item["prefix"] + item["statement"]
        quote = item["statement"]
        start = len(item["prefix"])
        source = record("SourceVersion", item["id"], {
            "source_id": item["id"], "source_version": "1",
            "source_byte_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "original_text": text, "lineage_id": item["lineage_id"], "publisher": item["publisher"],
            "published_at": item["published_at"], "known_at": item["known_at"],
            "access_policy_ref": POLICY_REFS[0], "availability_basis": dict(BASIS), "unknown_reason": None,
            "copied_from": reference(sources[item["copied_from"]]) if item["copied_from"] else None})
        repo.register(actor, source, source_bytes=text.encode("utf-8"))
        sources[item["id"]] = source
        passage = record("Passage", "passage:" + item["id"], {
            "source_ref": reference(source), "source_id": item["id"], "source_version": "1",
            "source_byte_digest": source["payload"]["source_byte_digest"],
            "start": start, "end": start + len(quote), "quote": quote,
            "quote_digest": hashlib.sha256(quote.encode("utf-8")).hexdigest()})
        repo.register(actor, passage)
        records += [source, passage]
    mapping = record("MappingRevision", assumption["mapping_id"], {
        "entities": [ENTITY_A], "representation_id": MODEL["representation_id"], "input_field": assumption["field"],
        "cardinality": "one_to_one", "valid_period": PERIOD, "status": "reviewed", "reviewer": ACTOR,
        "reviewed_at": AT, "source_refs": [reference(note)]})
    repo.register(actor, mapping)
    records.append(mapping)
    seed = {"record_id": assumption["record_id"], "revision_id": "1", "recorded_at": AT,
            "rationale": "Explicit fictional synthetic initial state for " + spec["pair_id"],
            "payload": {"case_id": CASE, "entity": ENTITY_A, "proposition": assumption["proposition"],
                        "value": assumption["value"], "valid_period": PERIOD,
                        "representation_id": MODEL["representation_id"], "input_field": assumption["field"],
                        "mapping_ref": reference(mapping)}}
    seeded = repo.seed_assumption(actor, seed["record_id"], seed["revision_id"], seed["recorded_at"],
                                  seed["payload"], seed["rationale"])

    # One shared BeliefSnapshot per pair. The frozen pairing contract (intent, "Cutoff pairing")
    # derives a pair only from two tasks that share assumption_id and snapshot and differ in
    # information_cutoff, so every compile of the pair is bound to this single snapshot. Its audit
    # cutoff is the earliest information cutoff: that is the latest audit instant that still keeps
    # every task's recorded_at >= the snapshot's recorded_at, which ``compile_task`` requires.
    plan = []
    for item in spec["compiles"]:
        information_cutoff = t0 if item["at"] == "t0" else t1
        plan.append({"item": item, "information_cutoff": information_cutoff,
                     "recorded_at": plus_minutes(information_cutoff, 5)})
    cutoffs = [datetime.fromisoformat(step["information_cutoff"]) for step in plan]
    if len(set(cutoffs)) != len(cutoffs) or cutoffs != sorted(cutoffs):
        raise SystemExit(f"{spec['pair_id']}: pairing compiles need strictly increasing information cutoffs")
    snapshot_audit = min(step["information_cutoff"] for step in plan)
    snapshot = repo.build_snapshot(actor, CASE, snapshot_audit, snapshot_audit)
    compiles = []
    for step in plan:
        item = step["item"]
        information_cutoff = step["information_cutoff"]
        recorded_at = step["recorded_at"]
        task = repo.compile_task(actor, CASE, reference(snapshot), seed["record_id"], information_cutoff, recorded_at)
        bundle = render_bundle(task, MODEL_ID)
        answers = canonical_answers(bundle, item["atomic"])
        prior_label = (spec.get("lineage") or {}).get("prior_label")
        composed = compose(bundle, answers, prior_label=prior_label)
        receipt_result = receipt(bundle, answers)
        compiles.append({
            "at": item["at"],
            "information_cutoff": information_cutoff,
            "audit_cutoff": snapshot_audit,
            "recorded_at": recorded_at,
            "expected_snapshot_ref": reference(snapshot),
            "expected_status": task["payload"]["status"],
            "expected_block_reasons": task["payload"]["block_reasons"],
            "expected_omissions": [omission["code"] for omission in task["payload"]["omissions"]],
            "expected_context_passages": [entry["passage_ref"]["record_id"] for entry in task["payload"]["context"]],
            "expected_task_ref": reference(task),
            "expected_task_digest": task["payload"]["task_digest"],
            "expected_render": {"status": bundle["status"], "bundle_version": bundle["bundle_version"],
                                "questions": len(bundle["request"]["questions"]),
                                "request_digest": bundle["request_digest"]},
            "expected_atomic_answers": item["atomic"],
            "frozen_label": item["label"],
            "rationale": item["rationale"],
            "expected_composition": {"bundle_version": BUNDLE_VERSION, "fired_rule": composed["fired_rule"],
                                     "label": composed["label"], "reason": composed["reason"],
                                     "unstable": receipt_result["unstable"],
                                     "unstable_questions": receipt_result["unstable_questions"],
                                     "agrees_with_frozen_label": composed["label"] == item["label"]},
        })
        if task["payload"]["status"] != "compiled":
            raise SystemExit(f"{spec['pair_id']}: task is not compiled: {task['payload']['block_reasons']}")
    if any(entry["expected_snapshot_ref"] != reference(snapshot) for entry in compiles):
        raise SystemExit(f"{spec['pair_id']}: every compile of a pair must bind the pair's shared snapshot")
    document = {
        "schema": "probe-bundle-fixture.v1",
        "pair_id": spec["pair_id"],
        "edge_class": spec["edge_class"],
        "fixture_label": FIXTURE_LABEL,
        "assumption_kind": assumption["field"],
        "annotation_policy": {"policy_id": policy()["policy_id"], "digest": policy_digest},
        "bundle_version_at_freeze": BUNDLE_VERSION,
        "model_id": MODEL_ID,
        "tenant_id": TENANT, "case_id": CASE, "actor_id": ACTOR, "access_policy_refs": POLICY_REFS,
        "records": records,
        "assumption_seed": seed,
        "expected_assumption_ref": reference(seeded),
        "cutoffs": {"t0": t0, "t1": t1},
        "snapshot": {"audit_cutoff": snapshot_audit, "recorded_at": snapshot_audit, "ref": reference(snapshot)},
        "compiles": compiles,
    }
    if spec.get("lineage"):
        document["lineage"] = spec["lineage"]
    if len(compiles) == 2:
        before, after = compiles[0]["expected_atomic_answers"], compiles[1]["expected_atomic_answers"]
        document["pairing"] = {
            "before": compiles[0]["at"], "after": compiles[1]["at"],
            "label_before": compiles[0]["frozen_label"], "label_after": compiles[1]["frozen_label"],
            "expected_changed": [qid for qid in QUESTIONS if before[qid] != after[qid]],
            "expected_new_passages": [record_id for record_id in compiles[1]["expected_context_passages"]
                                      if record_id not in compiles[0]["expected_context_passages"]],
        }
    return document


def check_file(document: dict) -> list[str]:
    """Re-load one written pair file through the repository and compare to its expectations."""
    problems = []
    actor = ActorContext(document["actor_id"], document["tenant_id"], frozenset({document["case_id"]}),
                         frozenset(document["access_policy_refs"]), True)
    repo = InMemoryRepository()
    for record in document["records"]:
        validate_record(record)
        if record["record_kind"] == "Case":
            repo.register_case(actor, record)
        elif record["record_kind"] == "SourceVersion":
            repo.register(actor, record, source_bytes=record["payload"]["original_text"].encode("utf-8"))
        else:
            repo.register(actor, record)
    seed = document["assumption_seed"]
    assumption = repo.seed_assumption(actor, seed["record_id"], seed["revision_id"], seed["recorded_at"],
                                      seed["payload"], seed["rationale"])
    if reference(assumption) != document["expected_assumption_ref"]:
        problems.append(f"{document['pair_id']}: assumption ref differs from the frozen expectation")
    frozen_snapshot = document["snapshot"]
    snapshot = repo.build_snapshot(actor, document["case_id"], frozen_snapshot["audit_cutoff"],
                                   frozen_snapshot["recorded_at"])
    if reference(snapshot) != frozen_snapshot["ref"]:
        problems.append(f"{document['pair_id']}: pair snapshot differs from the frozen expectation")
    # The frozen pairing contract: every compile of a pair binds the one pair snapshot and the
    # information cutoffs strictly increase, so the later-than-cutoff diff is the only difference.
    if any(item["expected_snapshot_ref"] != frozen_snapshot["ref"] for item in document["compiles"]):
        problems.append(f"{document['pair_id']}: compiles of a pair must share the pair's snapshot")
    pair_cutoffs = [datetime.fromisoformat(item["information_cutoff"]) for item in document["compiles"]]
    if len(pair_cutoffs) > 1 and (len(set(pair_cutoffs)) != len(pair_cutoffs) or pair_cutoffs != sorted(pair_cutoffs)):
        problems.append(f"{document['pair_id']}: pairing information cutoffs must strictly increase")
    for item in document["compiles"]:
        task = repo.compile_task(actor, document["case_id"], reference(snapshot), seed["record_id"],
                                 item["information_cutoff"], item["recorded_at"])
        if reference(task) != item["expected_task_ref"] or task["payload"]["task_digest"] != item["expected_task_digest"]:
            problems.append(f"{document['pair_id']}/{item['at']}: compiled task differs")
        if task["payload"]["status"] != item["expected_status"]:
            problems.append(f"{document['pair_id']}/{item['at']}: status differs")
        if task["payload"]["block_reasons"] != item["expected_block_reasons"]:
            problems.append(f"{document['pair_id']}/{item['at']}: block reasons differ")
        if datetime.fromisoformat(task["payload"]["audit_cutoff"]) != datetime.fromisoformat(item["audit_cutoff"]):
            problems.append(f"{document['pair_id']}/{item['at']}: task audit cutoff differs")
        if [o["code"] for o in task["payload"]["omissions"]] != item["expected_omissions"]:
            problems.append(f"{document['pair_id']}/{item['at']}: omissions differ")
        if [c["passage_ref"]["record_id"] for c in task["payload"]["context"]] != item["expected_context_passages"]:
            problems.append(f"{document['pair_id']}/{item['at']}: context differs")
        bundle = render_bundle(task, document["model_id"])
        if bundle["status"] != item["expected_render"]["status"]:
            problems.append(f"{document['pair_id']}/{item['at']}: render status differs")
        if bundle["request_digest"] != item["expected_render"]["request_digest"]:
            problems.append(f"{document['pair_id']}/{item['at']}: request digest differs")
        answers = canonical_answers(bundle, item["expected_atomic_answers"])
        composed = compose(bundle, answers, prior_label=(document.get("lineage") or {}).get("prior_label"))
        if composed["label"] != item["expected_composition"]["label"] or \
                composed["fired_rule"] != item["expected_composition"]["fired_rule"]:
            problems.append(f"{document['pair_id']}/{item['at']}: composition differs")
    return problems


def build_all() -> dict[str, dict]:
    policy_object = policy()
    policy_digest = compute_content_digest(policy_object)
    files = {"annotation-policy.json": policy_object}
    classes: dict[str, list[str]] = {}
    for spec in pair_specs():
        document = build_pair(spec, policy_digest)
        files[spec["pair_id"] + ".json"] = document
        classes.setdefault(spec["edge_class"], []).append(spec["pair_id"])
    ordered = {name: files[name] for name in sorted(files) if name != "annotation-policy.json"}
    manifests = {"annotation-policy.json": files["annotation-policy.json"], **ordered}
    digests = {name: compute_content_digest(value) for name, value in manifests.items()}
    labels = []
    contestable = {kind: [] for kind in ("assumed_available_capacity", "commercial_availability_from")}
    disagreements = []
    for name, value in ordered.items():
        for item in value["compiles"]:
            entry = {"pair_id": value["pair_id"], "at": item["at"], "assumption_kind": value["assumption_kind"],
                     "frozen_label": item["frozen_label"], "table_label": item["expected_composition"]["label"],
                     "agrees_with_frozen_label": item["expected_composition"]["agrees_with_frozen_label"]}
            labels.append(entry)
            if not entry["agrees_with_frozen_label"]:
                disagreements.append(f"{entry['pair_id']}/{entry['at']}")
            atomic = item["expected_atomic_answers"]
            if atomic["q3"] == "before" and atomic["q6"] == "yes":
                contestable[value["assumption_kind"]].append(value["pair_id"])
    manifest = {
        "schema": "probe-bundle-fixture-set.v1",
        "fixture_label": FIXTURE_LABEL,
        "frozen_at": "2026-10-13",
        "frozen_by": "executor agent (CORE-8) on task/CORE-8; second and only re-freeze; labels stay "
                     "annotations, not model output",
        "bundle_version_at_freeze": BUNDLE_VERSION,
        "refreeze_causes": [
            "probe-bundle.v5 (CORE-8): the Q2 event vocabulary from the operator-advisory corpus, the "
            "availability-kind predicate read from the model representation, and the direction_conflict row; "
            "annotation policy v2 re-annotates every q2 by rule",
            "h0.v2 record envelope (CORE-9): every fixture record is now written with schema_version h0.v2, the "
            "typed availability_basis object, and the declared (synthetic, permission_ref) pair — (True, None) for "
            "every payload here; the frozen labels are unchanged by both causes",
        ],
        "annotation_policy": {"policy_id": policy_object["policy_id"], "path": "annotation-policy.json",
                              "digest": policy_digest},
        "question_legend": QUESTIONS,
        "pairs": len(ordered),
        "compiles": len(labels),
        "classes": [{"edge_class": name, "pairs": classes[name]} for name in EDGE_CLASSES],
        "files": [{"path": name, "pair_id": value.get("pair_id"), "edge_class": value.get("edge_class"),
                   "digest": digests[name]} for name, value in ordered.items()],
        "frozen_labels": labels,
        "contestable_rule": {
            "rule": "q3 = before and q6 = yes -> supports",
            "meaning": "Pairs whose expected atomic answers carry the row's pattern, grouped by assumption kind; the "
                       "earlier_observed_return class is the decisive subset for ablation A1, and both kinds are "
                       "present there.",
            "pairs_by_assumption_kind": {kind: sorted(set(names)) for kind, names in contestable.items()},
        },
        "frozen_label_disagreements": sorted(disagreements),
        "fixture_digest": compute_content_digest(digests),
        "digest_rule": "Each file digest is compute_content_digest of the parsed JSON; fixture_digest is "
                       "compute_content_digest of the path-to-digest mapping over the pair files and "
                       "annotation-policy.json. The frozen set is those files; manifest.json and build.py are not "
                       "part of it.",
        "load_rule": "Records load in list order through the repository (Case via register_case, SourceVersion via "
                     "register with source_bytes = utf-8 of payload.original_text, Passage and MappingRevision via "
                     "register), then assumption_seed through seed_assumption, passing every declared string "
                     "verbatim. The pair's single BeliefSnapshot is rebuilt once from the 'snapshot' block "
                     "(audit_cutoff, recorded_at); every compile entry compiles against that snapshot with its own "
                     "information_cutoff and recorded_at, then renders with model_id.",
        "pairing_rule": "One snapshot per pair, per the frozen pairing contract: every compile of a pair binds the "
                        "document's single 'snapshot' block, and a multi-compile pair differs only in "
                        "information_cutoff, with strictly increasing cutoffs so the pair endpoint's ordering "
                        "requirement holds. '--check' asserts snapshot-reference equality and the cutoff ordering "
                        "for every pair file.",
        "no_backend_run": "No System One backend, model, transport, credential or network call was made before or "
                          "during the freeze; slice S2 of the probe-bundle intent is not built.",
        "recheck": ["/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check"],
    }
    output = dict(manifests)
    output["manifest.json"] = manifest
    return output


def write(files: dict[str, dict]) -> None:
    for name, value in files.items():
        text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        (HERE / name).write_text(text, encoding="utf-8")
        print(f"wrote {name}")


def read_written() -> dict[str, dict]:
    return {path.name: json.loads(path.read_text(encoding="utf-8")) for path in sorted(HERE.glob("*.json"))}


def main(argv: list[str]) -> int:
    files = build_all()
    if "--check" not in argv:
        write(files)
        return 0
    on_disk = read_written()
    problems = []
    for name, value in sorted(files.items()):
        if name not in on_disk:
            problems.append(f"missing file: {name}")
        elif on_disk[name] != value:
            problems.append(f"file differs from a fresh build: {name}")
    for name in sorted(on_disk):
        if name not in files:
            problems.append(f"unexpected file in the fixture directory: {name}")
    for name, value in sorted(on_disk.items()):
        if name.startswith("pb-"):
            problems.extend(check_file(value))
    manifest = on_disk.get("manifest.json", {})
    digest = manifest.get("fixture_digest")
    recomputed = compute_content_digest({item["path"]: item["digest"] for item in manifest.get("files", [])} | {
        "annotation-policy.json": manifest.get("annotation_policy", {}).get("digest")})
    if digest != recomputed:
        problems.append("manifest fixture_digest does not match the listed file digests")
    problems.extend(invariants(manifest))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(on_disk) - 2} pairs, {len(set(EDGE_CLASSES))} edge classes, "
          f"{manifest.get('compiles')} frozen labels, policy digest {manifest['annotation_policy']['digest']}, "
          f"fixture digest {digest}")
    return 0


def invariants(manifest: dict) -> list[str]:
    """The EVAL-1 acceptance properties that the frozen set itself must satisfy."""
    problems = []
    classes = {item["edge_class"]: item["pairs"] for item in manifest.get("classes", [])}
    if set(classes) != set(EDGE_CLASSES):
        problems.append(f"edge classes differ from the required eight: {sorted(classes)}")
    for name, names in classes.items():
        if len(names) < 3:
            problems.append(f"edge class {name} has fewer than three pairs: {names}")
    if manifest.get("pairs", 0) < 24:
        problems.append("fewer than 24 evidence-assumption pairs")
    labels = {entry["frozen_label"] for entry in manifest.get("frozen_labels", [])}
    if labels != {"supports", "challenges", "mixed", "unrelated", "insufficient"}:
        problems.append(f"the five-label vocabulary is not fully exercised: {sorted(labels)}")
    kinds = manifest.get("contestable_rule", {}).get("pairs_by_assumption_kind", {})
    for kind in ("assumed_available_capacity", "commercial_availability_from"):
        if not kinds.get(kind):
            problems.append(f"no pair carries the contestable rule for assumption kind {kind}")
    if sorted(manifest.get("frozen_label_disagreements", [])) != sorted(DOCUMENTED_DISAGREEMENTS):
        problems.append("the deliberate table-versus-annotation disagreements differ from the documented set: "
                        + str(manifest.get("frozen_label_disagreements")))
    return problems


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
