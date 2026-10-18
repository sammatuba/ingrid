#!/usr/bin/env python3
"""EVAL-5 case builder and checker: the PEDC Unit 2 real case of 2026-09-21.

Builds `case.json` for the first real case (task EVAL-5, lane EVAL, milestone M4)
and the two generated case-pack documents under `docs/cases/pedc-u2-2026-09-21/`,
by running the real repository: the DATA-1 readers build the source records, the
review core registers and seeds them, `compile_task` compiles at the four declared
cutoffs, `render_bundle` renders the frozen `probe-bundle.v5` request, the fixture
backend's scripted readings answer it, and the frozen `compose` produces the
labels. `--check` replays all of that and compares every recorded output; it writes
nothing.

Frozen rules this builder obeys and never edits:

* the case's records are **real** (`synthetic: false`, `permission_ref` the signed
  `perm:wesm-company-copy:2026-10-13`), so the repository refuses any record whose
  pair differs from the case's (`CASE_PROVENANCE_MISMATCH`);
* a `synthetic_fixture` judgment artifact cannot carry a real case's provenance
  (h0.v2, pinned by `tests.test_review_case.H0V2Case.
  test_a_synthetic_fixture_bundle_cannot_carry_a_real_case_s_provenance`), and no
  live inference is authorized or happens here, so the fixture-backend judgment is
  **not saved into the case**: it is recorded in this fixture and in the case
  packet as the run's output;
* **the records name who actually acted and when** (review 1, 2026-10-14): the
  case was assembled by the EVAL-5 case assembly on 2026-10-14, and every record
  the assembly wrote says so. Each source keeps the clock it really carries
  (`known_at`, posting instants); the desk's own acts (the reviewed mapping, the
  seed) and the replay's derived records carry the reconstructed 2026-09-21
  positions the compile replay requires, and each record that acts as the desk
  names that timeline a reconstruction rather than a day-of record;
* **no disposition is pre-written**: the compiled pairs are judged and the review
  of each cutoff is left to the demo's judge or the analyst (orchestrator
  direction, 2026-10-14, `docs/work/reviews/EVAL-5.md`). The only review decision
  here is the seed, the initial acceptance;
* composed labels are never written first: they are the output of
  `src.judgment.bundle.compose` over the fixture backend's scripted readings, and
  `--check` recomputes them and refuses any drift.

No model, transport, credential or network call is reachable from this file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adapters.wesm import advisories as wesm_advisories  # noqa: E402
from src.adapters.wesm import registry as wesm_registry  # noqa: E402
from src.contracts.jsonutil import canonical_dumps, compute_content_digest  # noqa: E402
from src.judgment.bundle import BUNDLE_VERSION, QUESTION_SPECS, compose, receipt, render_bundle  # noqa: E402
from src.review import ActorContext, InMemoryRepository, make_record, reference  # noqa: E402
from src.review.repository import DEFAULT_PERMISSIONS  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent
CASE_DOC_DIR = ROOT / "docs" / "cases" / "pedc-u2-2026-09-21"
CASE_FILE = FIXTURE_DIR / "case.json"
MANIFEST_FILE = CASE_DOC_DIR / "evidence-manifest.json"
MAPPINGS_FILE = CASE_DOC_DIR / "mappings.json"

SCHEMA = "pedc-case-fixture.v1"
TENANT = "grid-nowcast"
CASE = "pedc-u2-2026-09-21"
#: The actor that really performed every act in this fixture: the EVAL-5 case
#: assembly (orchestrator and executor seats), assembling on 2026-10-14. No analyst
#: session ran, so no record claims one.
ACTOR = "eval-5-case-assembly"
ASSEMBLY_ROLE = "EVAL-5 case assembly (orchestrator and executor seats)"
ASSEMBLED_ON = "2026-10-14"
#: The assembly instant: the real clock of the build that wrote this fixture,
#: recorded to the minute. It is the case record's own ``recorded_at`` (and the
#: dispatch records'), so the case's creation time is real while its replay
#: positions stay historical.
ASSEMBLED_AT = "2026-10-14T01:27:00+08:00"
PERMISSION = "perm:wesm-company-copy:2026-10-13"
REPRESENTATION = "pedc-availability.v1"
INPUT_FIELD = "available_capacity_mw"
ENTITY = {"entity_id": "08PEDC_U02", "entity_type": "GeneratingUnit"}
ASSUMPTION_ID = "assumption:08PEDC_U02:2026-09-21"
MODEL = "fixture-systemone"
SCRIPTED_PROBABILITY = 0.8
ADVISORY_FIXTURE = ROOT / "tests" / "fixtures" / "wesm" / "advisories-sample.jsonl"
REGISTER_FIXTURE = ROOT / "tests" / "fixtures" / "wesm" / "registry-pedc-sample.jsonl"
PROFILE = "docs/work/foundation-review-2026-10-13/sources/01-so-advisories.md"
SAMPLE_GROUP = "pedc_u2_21sep"
REGISTER_RESOURCE = "08PEDC_U02"
CASE_DAY = "2026-09-21"

#: The case record's own statement of who assembled it, when, and what the
#: 2026-09-21 timeline is: a reconstruction the compile replay needs. It rides on
#: the Case payload (the validator fixes no exact key set there), so every reader
#: of the fixture sees the assembly without consulting the packet.
CASE_ASSEMBLY = {
    "assembled_by": ACTOR,
    "assembled_role": ASSEMBLY_ROLE,
    "assembled_on": ASSEMBLED_ON,
    "timeline": "reconstruction",
    "note": ("Assembled 2026-10-14 from the company copy; this record's own recorded_at is the "
             "assembly instant. Every source keeps the clock it really carries (known_at, posting "
             "instants); the desk's own acts (the reviewed mapping, the seed) and the replay's "
             "derived records sit on the 2026-09-21 timeline at the positions the compile replay "
             "requires. No analyst session ran, and the desk's disposition at each cutoff is left "
             "to the judge or the analyst."),
}

#: The reconstructed positions of the desk's two acts on the case timeline. The
#: repository's guards require the reviewed mapping and the seeded assumption (and
#: its acceptance decision) to precede the pair cutoffs, so a real 2026-10-14 time
#: would leave every compile `UNRESOLVED_MAPPING`/`MISSING_INPUT`; the records
#: therefore carry these positions and say, in their own payloads, that they are
#: the reconstruction.
REVIEW_POSITION = "2026-09-21T00:05:00+08:00"
SEED_POSITION = "2026-09-21T00:10:00+08:00"

#: The reviewed mapping's provenance. Its envelope time must precede the cutoffs for
#: the mapping guard to resolve, so the reviewed_at position is the reconstruction
#: and the record says so; the assembly instant is the real one.
MAPPING_RECONSTRUCTION = {
    "timeline": "reconstruction",
    "assembled_by": ACTOR,
    "assembled_role": ASSEMBLY_ROLE,
    "assembled_at": ASSEMBLED_AT,
    "note": ("Review act of the EVAL-5 case assembly on 2026-10-14, placed at reviewed_at "
             "2026-09-21 00:05 (+08:00) because the compile replay requires the reviewed mapping "
             "to precede the cutoffs. No analyst session ran; the free-text-to-registry link is "
             "this case's, evidenced by the register run."),
}

#: The four information cutoffs of the two cutoff pairs, the snapshot instants and
#: the task instants, all Asia/Manila. T0 is the cutoff immediately before the new
#: source's first availability, T1 the cutoff at or after it (working paper 5.4);
#: each pair shares one snapshot whose audit cutoff is the pair's earliest
#: information cutoff (the frozen pairing contract). The cutoffs are the case's
#: historical evidence positions and are kept exactly; the snapshot/task instants
#: are the replay's own reconstruction positions and create no claim about the day.
#:
#: No disposition is planned here. Review 1 (2026-10-14) dropped the two pre-written
#: desk decisions: the fixture compiles and judges, and the disposition at each
#: cutoff is made by the demo's judge or the analyst, not authored in advance.
PAIR_PLAN = {
    "trip": {
        "new_source": "nso-advisory:2026-09-21:V133937",
        "t0": "2026-09-21T13:39:36+08:00",
        "t1": "2026-09-21T13:39:37+08:00",
        "snapshot_audit_cutoff": "2026-09-21T13:39:36+08:00",
        "snapshot_recorded_at": "2026-09-21T13:39:36+08:00",
        "t0_recorded_at": "2026-09-21T13:39:36+08:00",
        "t1_recorded_at": "2026-09-21T13:39:40+08:00",
    },
    "return": {
        "new_source": "nso-advisory:2026-09-21:V155556",
        "t0": "2026-09-21T15:55:55+08:00",
        "t1": "2026-09-21T15:55:56+08:00",
        "snapshot_audit_cutoff": "2026-09-21T15:55:55+08:00",
        "snapshot_recorded_at": "2026-09-21T15:55:55+08:00",
        "t0_recorded_at": "2026-09-21T15:55:55+08:00",
        "t1_recorded_at": "2026-09-21T15:56:30+08:00",
    },
}

#: The fixture backend's scripted reading of each judged compile, one atomic answer
#: per question, with the passage evidence each answer rests on. The labels are
#: never written here: `compose` produces them from these readings at build time and
#: `--check` recomputes them. `q2` follows the bundle v5 event vocabulary and the
#: Round 9 owner ruling that a notice stating an outage with no plan is
#: `forced_outage`; the reading of a set of passages follows the latest known
#: statement about the entity (annotation policy, `evidence_set_rule`).
READINGS = {
    ("trip", "t1"): {
        "answers": {"q1": ENTITY["entity_id"], "q2": "forced_outage", "q3": "same", "q4": "no",
                    "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"},
        "citations": {
            "q1": 'The passage names "PEDC U2"; the reviewed mapping resolves that free text to 08PEDC_U02.',
            "q2": '"Tripped at 1334H (Unplanned Outage)": an outage with no plan stated (Round 9 ruling).',
            "q3": "The 1334H trip lies on the header date, inside the assumption's day 2026-09-21.",
            "q4": "An unconditional statement of fact; nothing conditional or subject to clearance.",
            "q5": "The only passage in context; nothing earlier is repeated.",
            "q6": "It reports something that happened, not a target or plan.",
            "q7": "The trip alone decides the relation of the evidence to the assumed availability.",
            "q8": "The unit is out of service, so the assumed available capacity does not hold.",
        },
    },
    ("return", "t0"): {
        "answers": {"q1": ENTITY["entity_id"], "q2": "forced_outage", "q3": "same", "q4": "no",
                    "q5": "no", "q6": "yes", "q7": "yes", "q8": "challenges"},
        "citations": {
            "q1": 'The trip and MLD passages name "PEDC U2"; the reviewed mapping resolves it to 08PEDC_U02.',
            "q2": "The latest statement about the entity is the trip; the MLD repeats its cause, the yellow "
                  "alert names the grid, not the unit.",
            "q3": "The 1334H trip lies on the header date, inside the assumption's day 2026-09-21.",
            "q4": "The trip and the MLD are statements of fact; the alert states a condition, not a plan.",
            "q5": "No passage repeats an earlier source in context.",
            "q6": "The trip happened; the alert states a condition that holds over named hours.",
            "q7": "The context suffices: the unit is out of service at this cutoff.",
            "q8": "The assumed available capacity for the day does not hold while the unit is out.",
        },
    },
    ("return", "t1"): {
        "answers": {"q1": ENTITY["entity_id"], "q2": "return_to_service", "q3": "same", "q4": "no",
                    "q5": "no", "q6": "yes", "q7": "yes", "q8": "supports"},
        "citations": {
            "q1": 'The re-online passage names "PEDC Unit 2"; the reviewed mapping resolves it to 08PEDC_U02.',
            "q2": 'The latest statement about the entity is "re-online at 1507H" (the parenthetical names the '
                  "feed's outage category, not the event).",
            "q3": "The 1507H return lies on the header date, inside the assumption's day 2026-09-21.",
            "q4": "An unconditional statement that the unit is back online.",
            "q5": "The return is new information, not a repetition of an earlier source.",
            "q6": "It reports the return that happened, observed at posting time.",
            "q7": "The return decides the relation: the assumed availability holds again.",
            "q8": "The unit is online again, consistent with the assumed available capacity.",
        },
    },
}

#: The dispatch corroboration. The copy's RTD schedule rows are not exported to this
#: branch (the executor seat has no `bq`); the source carries the schedule readings
#: that the source profile records for this resource and day, cited in
#: ``inputs.dispatch.recorded_in``. Its first availability is unknown because the
#: copy carries no `run_time` column, so the revisions cannot be ordered
#: (real-sources intent): `known_at` is null and every compiled context omits it
#: with `UNKNOWN_AVAILABILITY`.
#:
#: The summary's publication instant is unknown too (review 1, 2026-10-14): the
#: profile records no publication time, and a schedule interval (16:00) is not one.
#: The summary body says so itself; the record's `published_at` is the profile
#: document's own date as an approximation labelled `published_at_approximate`, the
#: owner-ruled stand-in for a source the copy carries no publication instant for
#: (Round 9, as the register reader does), never a stated publication.
DISPATCH_BODY = {
    "kind": "rtd_schedule_readings",
    "table": "grid_raw.ext_rtd_prices_and_schedules",
    "resource_name": REGISTER_RESOURCE,
    "participant": "PEDC",
    "trading_day": CASE_DAY,
    "readings": [
        {"at": "13:30", "scheduled_mw": "83.7"},
        {"from": "13:45", "to": "15:15", "scheduled_mw": "0.0"},
        {"at": "15:30", "scheduled_mw": "17.5"},
        {"at": "16:00", "scheduled_mw": "30.0"},
    ],
    "published_at": None,
    "unknown_reason": "the RTD copy and the source profile record no publication instant",
    "recorded_in": PROFILE,
}
DISPATCH_SOURCE_ID = "rtd-schedule:%s:%s" % (REGISTER_RESOURCE, CASE_DAY)
#: The dispatch records were written by the assembly, so their own time is the real
#: assembly instant, not a reconstructed position on the day.
DISPATCH_RECORDED_AT = ASSEMBLED_AT
#: Who really produced these bytes: the case assembly, digesting the source profile
#: document. Not an IEMOP export.
DISPATCH_PUBLISHER = "EVAL-5 case assembly, digest of the source profile document"
DISPATCH_PUBLISHED_AT = "2026-10-13"  # the profile document's own date, date precision
DISPATCH_UNKNOWN_REASON = (
    "RUN_TIME absent from the copy, so first availability is unknown; the copy and the source "
    "profile record no publication instant, so published_at is the profile document's own date, "
    "approximate, never a stated publication")

#: The free-text forms of the entity that the case's own passages carry; the
#: reviewed mapping is written over exactly these (checked against the quotes).
FREE_TEXT_FORMS = ("PEDC U2", "PEDC Unit 2")


class FixtureProblem(Exception):
    """The replay disagrees with the recorded fixture; nothing is written."""


def _load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_records():
    """The case's records, in registration order, built by the real repository code."""
    permissions = DEFAULT_PERMISSIONS
    if PERMISSION not in permissions:
        raise FixtureProblem("the signed permission record %s is not in this checkout's registry" % PERMISSION)

    case_record = make_record("Case", TENANT, CASE, CASE, "1", ASSEMBLED_AT, {
        "permitted_actors": [ACTOR],
        "entities": [dict(ENTITY)],
        "representations": [{"representation_id": REPRESENTATION, "target_type": "GeneratingUnit",
                             "model_version": REPRESENTATION,
                             "input_fields": {INPUT_FIELD: {"quantity_kind": "available_capacity", "unit": "MW"}}}],
        "assembly": dict(CASE_ASSEMBLY),
        "synthetic": False, "permission_ref": PERMISSION}, permissions=permissions)

    advisory_rows = [row for row in _load_rows(ADVISORY_FIXTURE) if row.get("sample_group") == SAMPLE_GROUP]
    batch = wesm_advisories.parse_advisories(advisory_rows)
    if len(batch.advisories) != 4 or batch.rejected:
        raise FixtureProblem("the PEDC sample group must hold four parsable advisories")
    advisory_records = []
    for item in batch.advisories:
        one = wesm_advisories.AdvisoryBatch(advisories=(item,), rejected=())
        advisory_records.extend(wesm_advisories.records(one, TENANT, CASE, item.source["known_at"], permissions=permissions))

    register_rows = [row for row in _load_rows(REGISTER_FIXTURE) if row["resource_name"] == REGISTER_RESOURCE]
    runs, rejected = wesm_registry.build_runs(register_rows)
    if rejected:
        raise FixtureProblem("the register sample for %s must parse whole" % REGISTER_RESOURCE)
    day = date.fromisoformat(CASE_DAY)
    covering = [run for run in runs if run.first_day <= day <= run.last_day]
    if len(covering) != 1:
        raise FixtureProblem("exactly one change-only run of %s must cover %s" % (REGISTER_RESOURCE, CASE_DAY))
    run = covering[0]
    register_records = wesm_registry.records([run], TENANT, CASE, "2026-09-21T00:00:00+08:00",
                                             representation_id=REPRESENTATION, input_field=INPUT_FIELD,
                                             permissions=permissions)
    run_source = next(record for record in register_records if record["record_kind"] == "SourceVersion")
    candidate = next(record for record in register_records if record["record_kind"] == "MappingRevision")
    reviewed_payload = wesm_registry.mapping_payload(run, run_source,
                                                     representation_id=REPRESENTATION, input_field=INPUT_FIELD)
    reviewed_payload.update(status="reviewed", reviewer=ACTOR, reviewed_at=REVIEW_POSITION,
                            reconstruction=dict(MAPPING_RECONSTRUCTION))
    reviewed = make_record("MappingRevision", TENANT, CASE, run.mapping_id, "2", REVIEW_POSITION,
                           reviewed_payload, permissions=permissions)

    dispatch_text = canonical_dumps(DISPATCH_BODY)
    dispatch_bytes = dispatch_text.encode("utf-8")
    dispatch = make_record("SourceVersion", TENANT, CASE, DISPATCH_SOURCE_ID, "1", DISPATCH_RECORDED_AT, {
        "source_id": DISPATCH_SOURCE_ID, "source_version": "1", "lineage_id": DISPATCH_SOURCE_ID,
        "publisher": DISPATCH_PUBLISHER, "access_policy_ref": PERMISSION,
        "original_text": dispatch_text, "source_byte_digest": hashlib.sha256(dispatch_bytes).hexdigest(),
        "published_at": DISPATCH_PUBLISHED_AT, "published_at_approximate": True,
        "derived_from": PROFILE,
        "known_at": None, "availability_basis": None,
        "unknown_reason": DISPATCH_UNKNOWN_REASON, "copied_from": None,
        "synthetic": False, "permission_ref": PERMISSION}, permissions=permissions)
    dispatch_passage = make_record("Passage", TENANT, CASE, "passage:" + DISPATCH_SOURCE_ID, "1", DISPATCH_RECORDED_AT, {
        "source_ref": reference(dispatch), "source_id": DISPATCH_SOURCE_ID, "source_version": "1",
        "source_byte_digest": dispatch["payload"]["source_byte_digest"], "start": 0, "end": len(dispatch_text),
        "quote": dispatch_text, "quote_digest": hashlib.sha256(dispatch_text.encode("utf-8")).hexdigest(),
        "synthetic": False, "permission_ref": PERMISSION}, permissions=permissions)

    ordered = [case_record, *advisory_records, *register_records, reviewed, dispatch, dispatch_passage]
    return ordered, {"run": run, "run_source": run_source, "candidate": candidate, "reviewed": reviewed,
                     "dispatch": dispatch, "dispatch_passage": dispatch_passage, "batch": batch,
                     "advisory_rows": advisory_rows, "register_rows": register_rows}


def scripted_answers(bundle, reading):
    """Per-form answers whose top option is the reading's answer in every form.

    The fixture backend: a deterministic script, not a model. A choice question
    answers in the token the form presents (canonical, permuted or aliased); a noul
    answers in the form's own polarity, so the negated form's probability inverts.
    """
    answers = {}
    for spec in QUESTION_SPECS:
        for form in range(bundle["forms"]):
            name = f"{spec['id']}_{spec['slug']}_f{form}"
            criteria = bundle["request"]["questions"][name]["criteria"]
            if spec["type"] == "choice":
                tokens = [token for token, option in criteria["options"].items() if option == reading[spec["id"]]]
                if len(tokens) != 1:
                    raise FixtureProblem(f"{name}: the reading {reading[spec['id']]!r} is not uniquely presented")
                answers[name] = {"choice": tokens[0], "probabilities": {tokens[0]: SCRIPTED_PROBABILITY}}
            else:
                value = SCRIPTED_PROBABILITY if criteria["options"]["yes"] == "yes" else 1 - SCRIPTED_PROBABILITY
                if reading[spec["id"]] != "yes":
                    value = 1 - value
                answers[name] = {"noul": value}
    return answers


def replay():
    """Register the case, seed it, compile the four cutoffs, judge, compose, review."""
    records, ctx = build_records()
    actor = ActorContext(ACTOR, TENANT, frozenset({CASE}), frozenset({PERMISSION}), True)
    repo = InMemoryRepository()
    repo.register_case(actor, records[0])
    for record in records[1:]:
        if record["record_kind"] == "SourceVersion":
            repo.register(actor, record, source_bytes=record["payload"]["original_text"].encode("utf-8"))
        else:
            repo.register(actor, record)
    run = ctx["run"]
    seed_payload = {
        "case_id": CASE, "entity": dict(ENTITY),
        "proposition": "The registered maximum available capacity of 08PEDC_U02 holds for 2026-09-21",
        # The value is read from the register run's capacity, never typed by hand.
        "value": {"value": run.capacity_mw, "quantity_kind": "available_capacity", "unit": "MW"},
        "valid_period": {"start": "2026-09-21", "end": "2026-09-22"},
        "representation_id": REPRESENTATION, "input_field": INPUT_FIELD,
        "mapping_ref": reference(ctx["reviewed"])}
    # The seed is the assembly's initial acceptance, recorded on 2026-10-14 and placed
    # at the reconstructed day-start position the compile guards require. The payload
    # key set is fixed by the port, so the provenance lives in this rationale.
    seed_rationale = (
        "Initial acceptance recorded by the %s on %s, placed at the reconstructed position %s "
        "(the compile replay requires the accepted position to precede the cutoffs). The value is "
        "read from the register run's capacity (83.7 MW, participant PEDC), never typed; no "
        "analyst session ran." % (ACTOR, ASSEMBLED_ON, SEED_POSITION))
    assumption = repo.seed_assumption(actor, ASSUMPTION_ID, "1", SEED_POSITION,
                                      seed_payload, seed_rationale)

    pairs = []
    for pair_id, plan in PAIR_PLAN.items():
        snapshot = repo.build_snapshot(actor, CASE, plan["snapshot_audit_cutoff"], plan["snapshot_recorded_at"])
        compiles = []
        for at in ("t0", "t1"):
            task = repo.compile_task(actor, CASE, reference(snapshot), ASSUMPTION_ID,
                                     plan[at], plan[f"{at}_recorded_at"])
            payload = task["payload"]
            entry = {
                "at": at, "information_cutoff": payload["information_cutoff"], "audit_cutoff": payload["audit_cutoff"],
                "recorded_at": task["recorded_at"], "task_ref": reference(task), "task_digest": payload["task_digest"],
                "assumption_ref": payload["assumption_ref"], "mapping_ref": payload["mapping_ref"],
                "status": payload["status"], "block_reasons": payload["block_reasons"],
                "omissions": [{"passage_ref": item["passage_ref"], "code": item["code"]} for item in payload["omissions"]],
                "context_passages": [item["passage_ref"]["record_id"] for item in payload["context"]],
                "judgment": None,
            }
            reading = READINGS.get((pair_id, at))
            if reading is not None:
                bundle = render_bundle(task, MODEL)
                if bundle["status"] != "rendered":
                    raise FixtureProblem(f"{pair_id}/{at}: the frozen renderer refused: {bundle.get('reason')}")
                answers = scripted_answers(bundle, reading["answers"])
                entry["judgment"] = {
                    "backend": {"name": MODEL, "kind": "fixture", "execution_mode": "synthetic_fixture",
                                "live_calls": 0, "scripted_probability": SCRIPTED_PROBABILITY},
                    "reading": reading["answers"], "citations": reading["citations"],
                    "answers_digest": compute_content_digest(answers),
                    "render": {"status": bundle["status"], "bundle_version": bundle["bundle_version"],
                               "forms": bundle["forms"], "task_digest": bundle["task_digest"],
                               "request_digest": bundle["request_digest"], "question_count": len(bundle["request"]["questions"])},
                    # The composed result is the frozen table's output over the reading above,
                    # recorded from the run; `--check` recomputes it and refuses any drift.
                    "composed": compose(bundle, answers),
                    "receipt": receipt(bundle, answers),
                }
            else:
                entry["judgment"] = None
                entry["judgment_omitted_because"] = ("no passage is known at this cutoff, so the compile is blocked "
                                                     "and there is nothing to judge")
            compiles.append(entry)
        # No disposition is committed: the pair ends judged, and the review of each
        # cutoff belongs to the demo's judge or the analyst (orchestrator direction).
        pairs.append({"pair_id": pair_id, "new_source": plan["new_source"],
                      "snapshot": {"audit_cutoff": snapshot["payload"]["audit_cutoff"],
                                   "recorded_at": snapshot["recorded_at"], "ref": reference(snapshot)},
                      "compiles": compiles})

    heads = repo.heads(actor, CASE)
    history = repo.history(actor, CASE)
    review_state = {
        "committed": len(history),
        "dispositions": [],
        "note": ("No disposition is committed by this fixture (review 1, 2026-10-14): every pair "
                 "ends judged, and the review of each cutoff is left to the demo's judge or the "
                 "analyst. The seed below is the case's initial acceptance, not a review of "
                 "evidence."),
    }
    kind_counts = {}
    for record in repo._records_in(TENANT, CASE):
        kind_counts[record["record_kind"]] = kind_counts.get(record["record_kind"], 0) + 1
    workspace = {
        "assumption_head": heads["assumptions"][ASSUMPTION_ID], "outlook_head": heads["outlook"],
        "history": [{"decision_ref": record["payload"].get("decision_ref"), "outlook_ref": reference(record),
                     "disposition": record["payload"]["open_issues"][0]["disposition"] if record["payload"]["open_issues"] else "retain",
                     "state": record["payload"]["state"], "difference_kind": record["payload"]["difference"]["kind"],
                     "reviewed_at": record["payload"]["reviewed_at"], "rationale": record["payload"]["difference"]["rationale"]}
                    for record in history],
        "record_kinds": kind_counts, "probe_bundles": len(repo.workspace(actor, CASE)["probe_bundles"]),
        "consequences": "uncomputed",
    }
    return {"records": records, "assumption": assumption, "assumption_ref": reference(assumption),
            "seed_payload": seed_payload, "seed_rationale": seed_rationale,
            "pairs": pairs, "review_state": review_state, "workspace": workspace, "ctx": ctx}


def document(result):
    """The fixture document: inputs, records and the recorded run outputs."""
    ctx = result["ctx"]
    run = ctx["run"]
    return {
        "schema": SCHEMA,
        "fixture_label": ("Real company-copy rows for the PEDC Unit 2 case of 2026-09-21, assembled %s by the %s "
                          "(see the case record's `assembly`): the sources keep their real clocks and the case's "
                          "2026-09-21 timeline is a reconstruction. The rows are real and cited to the signed "
                          "permission record; the judgment backend below is a deterministic script "
                          "(synthetic_fixture), not a model and not an analyst, and no disposition is pre-written."
                          % (ASSEMBLED_ON, ACTOR)),
        "case_id": CASE, "tenant_id": TENANT, "actor_id": ACTOR, "permission_ref": PERMISSION,
        "assembled_on": ASSEMBLED_ON, "assembly": dict(CASE_ASSEMBLY),
        "bundle_version": BUNDLE_VERSION,
        "inputs": {
            "advisories": {"path": "tests/fixtures/wesm/advisories-sample.jsonl", "sha256": _sha256(ADVISORY_FIXTURE),
                           "sample_group": SAMPLE_GROUP, "rows": len(ctx["advisory_rows"]),
                           "adv_ids": [row["adv_id"] for row in ctx["advisory_rows"]]},
            "register": {"path": "tests/fixtures/wesm/registry-pedc-sample.jsonl", "sha256": _sha256(REGISTER_FIXTURE),
                         "resource_name": REGISTER_RESOURCE, "rows": len(ctx["register_rows"]),
                         "run": {"source_id": run.source_id, "participant": run.participant, "capacity_mw": run.capacity_mw,
                                 "region": run.region, "valid_period": run.valid_period, "trading_days": run.days,
                                 "status": run.status}},
            "dispatch": {"table": DISPATCH_BODY["table"], "recorded_in": PROFILE,
                         "publisher": DISPATCH_PUBLISHER, "published_at": None, "known_at": None,
                         "unknown_reason": DISPATCH_UNKNOWN_REASON,
                         "note": ("The copy's RTD rows are not exported to this branch; the source carries the "
                                  "schedule readings the source profile records for this resource and day, its "
                                  "publication instant unknown (the record's `published_at` is the profile "
                                  "document's own date, labelled approximate).")},
            "external_document": None,
        },
        "case_definition": {"entity": dict(ENTITY), "representation": REPRESENTATION, "input_field": INPUT_FIELD,
                            "free_text_forms": list(FREE_TEXT_FORMS)},
        "records": result["records"],
        "assumption_seed": {"record_id": ASSUMPTION_ID, "revision_id": "1", "recorded_at": SEED_POSITION,
                            "rationale": result["seed_rationale"], "payload": result["seed_payload"]},
        "assumption_ref": result["assumption_ref"],
        "cutoffs": {pair_id: {"t0": plan["t0"], "t1": plan["t1"]} for pair_id, plan in PAIR_PLAN.items()},
        "pairs": result["pairs"],
        "review_state": result["review_state"],
        "workspace": result["workspace"],
        "provenance": {
            "built_by": "tests/fixtures/pedc-u2-2026-09-21/build.py",
            "builder": "EVAL-5 executor seat, /usr/bin/python3",
            "assembly": ("every record here was written by the %s on %s; the case record's `assembly` block and "
                         "the reviewed mapping's `reconstruction` block state it, and the seed's rationale states "
                         "it too (review 1, 2026-10-14)" % (ACTOR, ASSEMBLED_ON)),
            "composed_labels": ("outputs of src.judgment.bundle.compose over the scripted readings above, recorded "
                                "from the run; no label was authored before the run and --check recomputes every one"),
            "reviews": ("none: no disposition is committed (review 1, 2026-10-14). The compiled pairs are judged "
                        "and the review of each cutoff is left to the demo's judge or the analyst; the only "
                        "ReviewDecision here is the seed, the case's initial acceptance"),
            "no_backend_run": ("no model, transport, credential or network call is reachable from the builder; the "
                               "fixture backend records live_calls 0"),
            "not_stored": ("the fixture-backend judgment is not saved into the case: the frozen validator refuses a "
                           "synthetic_fixture artifact carrying a real case's provenance "
                           "(tests/test_review_case.py, H0V2Case), and no live inference is authorized by this task"),
        },
    }


def manifest_document(result, fixture_digest):
    ctx = result["ctx"]
    sources = []
    for record in result["records"]:
        if record["record_kind"] == "SourceVersion":
            payload = record["payload"]
            entry = {"source_id": payload["source_id"], "source_version": payload["source_version"],
                     "lineage_id": payload["lineage_id"], "publisher": payload["publisher"],
                     "published_at": payload["published_at"],
                     "published_at_approximate": payload.get("published_at_approximate", False),
                     "derived_from": payload.get("derived_from"),
                     "known_at": payload["known_at"], "availability_basis": payload["availability_basis"],
                     "unknown_reason": payload["unknown_reason"], "access_policy_ref": payload["access_policy_ref"],
                     "permission_ref": payload["permission_ref"], "source_byte_digest": payload["source_byte_digest"],
                     "record": reference(record), "passage_ref": None, "advisory": None, "register_run": None}
            if payload["source_id"].startswith("nso-advisory:"):
                item = next(a for a in ctx["batch"].advisories if a.source["source_id"] == payload["source_id"])
                entry["advisory"] = {"adv_id": item.row["adv_id"], "category": item.category, "event_at": item.event_at,
                                     "event_time_flag": item.event_time_flag, "header_clock": item.header.isoformat()}
            elif payload["source_id"].startswith("regcap:"):
                run = ctx["run"]
                entry["register_run"] = {"resource_name": run.resource_name, "participant": run.participant,
                                         "capacity_mw": run.capacity_mw, "region": run.region,
                                         "first_day": run.first_day.isoformat(), "last_day": run.last_day.isoformat(),
                                         "trading_days": run.days, "status": run.status}
            else:
                entry["register_run"] = None
            sources.append(entry)
    for record in result["records"]:
        if record["record_kind"] == "Passage":
            payload = record["payload"]
            source = next(item for item in sources if item["source_id"] == payload["source_id"])
            source["passage_ref"] = {"record": reference(record), "start": payload["start"], "end": payload["end"],
                                     "quote_digest": payload["quote_digest"], "quote": payload["quote"],
                                     "category": payload.get("category"), "event_at": payload.get("event_at")}
    omissions, contexts = {}, {}
    for pair in result["pairs"]:
        for compile_entry in pair["compiles"]:
            key = f"{pair['pair_id']}/{compile_entry['at']}"
            omissions[key] = {item["passage_ref"]["record_id"]: item["code"] for item in compile_entry["omissions"]}
            contexts[key] = compile_entry["context_passages"]
    return {
        "manifest_version": "pedc-u2-2026-09-21.evidence.v1",
        "case_id": CASE, "generated_from": "tests/fixtures/pedc-u2-2026-09-21/case.json",
        "fixture_digest": fixture_digest,
        "assembly": dict(CASE_ASSEMBLY),
        "evidence_scope": {
            "advisory_only": True,
            "external_document_supplied": False,
            "statement": ("Advisory-only: the case's evidence is the four NGCP advisories of 2026-09-21 registered "
                          "above; no external document was supplied, and the dispatch corroboration is never counted "
                          "as evidence at a cutoff (RUN_TIME absent from the copy, publication instant unknown)."),
        },
        "cutoffs": {pair_id: {"t0": plan["t0"], "t1": plan["t1"]} for pair_id, plan in PAIR_PLAN.items()},
        "sources": sources,
        "lineage_groups": [{"lineage_id": item.source["lineage_id"], "source_refs": [item.source["source_id"]]}
                           for item in ctx["batch"].advisories]
                          + [{"lineage_id": ctx["run"].source_id, "source_refs": [ctx["run"].source_id]},
                             {"lineage_id": DISPATCH_SOURCE_ID, "source_refs": [DISPATCH_SOURCE_ID]}],
        "omissions_by_compile": omissions,
        "context_passages_by_compile": contexts,
    }


def mappings_document(result):
    ctx = result["ctx"]
    candidate, reviewed = ctx["candidate"]["payload"], ctx["reviewed"]["payload"]
    return {
        "mappings_version": "pedc-u2-2026-09-21.mappings.v1",
        "case_id": CASE, "generated_from": "tests/fixtures/pedc-u2-2026-09-21/case.json",
        "entities": [dict(ENTITY)],
        "representations": [{"representation_id": REPRESENTATION, "target_type": "GeneratingUnit",
                             "model_version": REPRESENTATION,
                             "input_fields": {INPUT_FIELD: {"quantity_kind": "available_capacity", "unit": "MW"}}}],
        "correspondences": [{
            "from_text": list(FREE_TEXT_FORMS),
            "to": ENTITY["entity_id"],
            "canonical_type": "GeneratingUnit",
            "status": reviewed["status"], "cardinality": reviewed["cardinality"],
            "valid_period": reviewed["valid_period"], "representation_id": reviewed["representation_id"],
            "input_field": reviewed["input_field"], "reviewer": reviewed["reviewer"], "reviewed_at": reviewed["reviewed_at"],
            "reconstruction": reviewed["reconstruction"],
            "mapping_ref": reference(ctx["reviewed"]), "source_refs": reviewed["source_refs"],
            "superseded_candidate": {"status": candidate["status"], "mapping_ref": reference(ctx["candidate"]),
                                     "note": ("the register reader's unreviewed candidate; the reviewed "
                                              "revision 2 supersedes it and cites the same register run")},
        }],
        "unresolved": [],
        "notes": [
            ("The case's advisories name the unit in free text only; nothing in the feed links 'PEDC U2' to the "
             "registry code 08PEDC_U02. The link is the case assembly's reviewed mapping, evidenced by the register "
             "run; the review act is the assembly's on 2026-10-14, placed at the reconstructed reviewed_at position "
             "above, and no analyst session ran."),
            ("One register run covers 2026-09-21 for this resource (2026-02-05 to 2026-09-29, 83.7 MW, participant "
             "PEDC); the copy's 2025 hole splits it from the 2024 run, which is not part of this case."),
        ],
    }


def compile_entry_of(doc, pair_id, at):
    pair = next(pair for pair in doc["pairs"] if pair["pair_id"] == pair_id)
    return next(entry for entry in pair["compiles"] if entry["at"] == at)


def check(doc, result):
    """Every recorded output re-derived and compared; raises on the first problem."""
    problems = []
    fresh = document(result)
    # The acceptance lines first, spelled out rather than implied by the comparison
    # below, so a drifted file is reported against the acceptance wording itself.
    trip_t0 = compile_entry_of(doc, "trip", "t0")
    omissions = {item["passage_ref"]["record_id"]: item["code"] for item in trip_t0["omissions"]}
    if omissions.get("passage:nso-advisory:2026-09-21:V133937") != "LATER_AVAILABILITY":
        problems.append("trip/t0 must omit the trip advisory with LATER_AVAILABILITY")
    if omissions.get("passage:" + DISPATCH_SOURCE_ID) != "UNKNOWN_AVAILABILITY":
        problems.append("trip/t0 must omit the dispatch with UNKNOWN_AVAILABILITY")
    for pair in doc["pairs"]:
        for compile_entry in pair["compiles"]:
            codes = {item["passage_ref"]["record_id"]: item["code"] for item in compile_entry["omissions"]}
            if codes.get("passage:" + DISPATCH_SOURCE_ID) != "UNKNOWN_AVAILABILITY":
                problems.append(f"{pair['pair_id']}/{compile_entry['at']}: the dispatch must be omitted "
                                "UNKNOWN_AVAILABILITY from every compiled context")
    return_t1 = compile_entry_of(doc, "return", "t1")["judgment"]
    if return_t1 is None or return_t1["composed"]["fired_rule"].split(":")[0] != "availability_confirmed":
        problems.append("return/t1 must compose through availability_confirmed")
    quotes = " ".join(record["payload"]["quote"] for record in doc["records"] if record["record_kind"] == "Passage")
    for form in FREE_TEXT_FORMS:
        if form not in quotes:
            problems.append(f"the reviewed mapping's free-text form {form!r} does not occur in the case's passages")
    if doc["inputs"]["external_document"] is not None:
        problems.append("this case supplies no external document; the scope statement must read advisory-only")
    # The rework's own lines (review 1, 2026-10-14), again spelled out: no disposition
    # is pre-written, every act names the real assembly, and the dispatch's publication
    # clock stays an approximate stand-in rather than a schedule interval.
    kinds = doc["workspace"]["record_kinds"]
    if kinds.get("ReviewDecision", 0) != 1 or kinds.get("OutlookRevision", 0) != 0:
        problems.append("no review disposition may be pre-written: the seed's initial acceptance is "
                        "the only ReviewDecision and no outlook revision exists, so each cutoff's "
                        "decision is left to the judge or the analyst")
    if doc["workspace"]["history"] or doc["workspace"]["outlook_head"] is not None:
        problems.append("the case must hold no outlook history; the decision is not pre-written")
    case_record = next(record for record in doc["records"] if record["record_kind"] == "Case")
    assembly = case_record["payload"].get("assembly")
    if not (type(assembly) is dict and assembly.get("timeline") == "reconstruction"
            and assembly.get("assembled_by") == ACTOR and assembly.get("assembled_on") == ASSEMBLED_ON):
        problems.append("the case record must name its assembly and mark the timeline a reconstruction")
    mapping = next(record for record in doc["records"]
                   if record["record_kind"] == "MappingRevision" and record["revision_id"] == "2")
    if (mapping["payload"].get("reconstruction") or {}).get("assembled_by") != ACTOR:
        problems.append("the reviewed mapping must name the assembly that recorded it")
    dispatch = next(record for record in doc["records"] if record["record_id"] == DISPATCH_SOURCE_ID)
    if (dispatch["payload"].get("published_at_approximate") is not True
            or dispatch["payload"].get("published_at") != DISPATCH_PUBLISHED_AT
            or dispatch["payload"].get("derived_from") != PROFILE
            or dispatch["payload"].get("publisher") != DISPATCH_PUBLISHER):
        problems.append("the dispatch publication clock must stay an approximate stand-in and name "
                        "its real publisher and provenance")
    if doc["review_state"]["committed"] != 0:
        problems.append("no review may be committed by this fixture")
    for key in ("records", "assumption_seed", "assumption_ref", "cutoffs", "review_state", "workspace"):
        if canonical_dumps(doc[key]) != canonical_dumps(fresh[key]):
            problems.append(f"{key}: differs from a fresh build")
    if canonical_dumps(doc["pairs"]) != canonical_dumps(fresh["pairs"]):
        problems.append("pairs: a compile, composition or receipt differs from a fresh replay")
    if problems:
        raise FixtureProblem("; ".join(problems))
    return fresh


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check_only = "--check" in argv
    unknown = [arg for arg in argv if arg != "--check"]
    if unknown:
        raise SystemExit("usage: build.py [--check]")
    try:
        result = replay()
        doc = document(result)
        fixture_digest = compute_content_digest(doc)
        manifest = manifest_document(result, fixture_digest)
        mappings = mappings_document(result)
        if check_only:
            recorded = json.loads(CASE_FILE.read_text(encoding="utf-8"))
            check(recorded, result)
            for path, expected in ((MANIFEST_FILE, manifest), (MAPPINGS_FILE, mappings)):
                if canonical_dumps(json.loads(path.read_text(encoding="utf-8"))) != canonical_dumps(expected):
                    raise FixtureProblem(f"{path.relative_to(ROOT)} differs from a fresh build")
    except FixtureProblem as problem:
        print(f"fixture problem: {problem}", file=sys.stderr)
        return 1
    if check_only:
        print(f"OK: {len(doc['records'])} records, 2 pairs, 4 compiles, "
              f"{doc['review_state']['committed']} committed reviews (none by design); "
              f"bundle {doc['bundle_version']}; fixture digest {fixture_digest}; "
              f"trip/t0 omissions verified; composed labels recomputed")
        return 0
    CASE_DOC_DIR.mkdir(parents=True, exist_ok=True)
    for path, payload in ((CASE_FILE, doc), (MANIFEST_FILE, manifest), (MAPPINGS_FILE, mappings)):
        path.write_text(canonical_dumps(payload) + "\n", encoding="utf-8")
    print(f"wrote {CASE_FILE.relative_to(ROOT)}, {MANIFEST_FILE.relative_to(ROOT)}, "
          f"{MAPPINGS_FILE.relative_to(ROOT)}; fixture digest {fixture_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
