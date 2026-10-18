#!/usr/bin/env python3
"""The labelled synthetic fixture: the reserve-market case's shape, with evidence of access.

CORP-5's designated review found that the real case cannot demonstrate the required path:
the compendium copies carry no first-availability evidence, so the strict cutoff rule places
no clause version at either cutoff, and a refusal alone demonstrates nothing. This fixture
carries the case's own shape with *invented* records that do carry availability evidence, so
the event page and the corpus store demonstrate, end to end:

* at the earlier cutoff, a clause version the store places — in force — while the same cutoff
  refuses the version that replaced it as ``after_cutoff``, naming it and withholding its text;
* at the later cutoff, the amended version in force, the announcement that changed it placed
  and quoted, and the earlier announcement available at both cutoffs;
* the accepted dependency the store's own walk returns, which the real pack cannot show while
  its mapping stays proposed.

Every record here is invented, and the fixture says so in five places: the manifest's
``fixture`` block, its ``title``, the view's first limit line and its ``fixture_note``, and the
store rows' ``synthetic: true`` (which the store refuses to admit with a permission). Nothing
in this directory is a fact about the WESM reserve market; nothing was fetched, read from a
document, or produced by a model.

    /usr/bin/python3 tests/fixtures/grid/event/rules-in-force/build.py
    /usr/bin/python3 tests/fixtures/grid/event/rules-in-force/build.py --check

This script writes ``evidence-manifest.json`` with every digest computed here, then the event
view through ``scripts/grid/build_rules.py`` (the same builder the real case uses).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "evidence-manifest.json"
RULES_BUILD = ROOT / "scripts" / "grid" / "build_rules.py"

CASE_ID = "fixture-rules-in-force"
TITLE = ("Fixture (synthetic): a clause in force at each cutoff and the announcement that "
         "changed it")
RECORDED_AT = "2026-10-16T00:00:00Z"
#: The same two cutoffs as the real case, so the fixture demonstrates the same two days.
CUTOFFS = {
    "day_after": {
        "label": "One day after the action",
        "precision": "second",
        "value": "2026-10-16T01:00:00+08:00",
        "why": "just after the fixture's own record of reading the order, the first cutoff that "
               "permits every record this fixture cites",
    },
    "day_before": {
        "label": "One day before the action",
        "precision": "second",
        "value": "2026-10-13T23:59:00+08:00",
        "why": "the last minute of 13 October 2026 in Manila, before the stop takes effect at "
               "trading interval 0005H on 14 October",
    },
}
RULES_SHA = hashlib.sha256(b"fixture rules copy, invented for CORP-5").hexdigest()
ORDER_SHA = hashlib.sha256(b"fixture order copy, invented for CORP-5").hexdigest()
RULES_READ = "2026-01-12T09:00:00Z"
ORDER_READ = "2026-10-15T16:19:55Z"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


BASELINE_NOTE = ("(This clause is the fixture's baseline: it states the reserve trading the "
                 "fixture order later stopped.)")
AMEND_NOTE = "Amended by the fixture order No. 2026-002 dated 12 October 2026."
BASELINE_TEXT = ("4.2.1 Reserve trading. The market operator shall operate a spot market for "
                 "the trading of reserve.")
AMENDED_TEXT = ("4.2.1 Reserve trading. The market operator shall operate a spot market for "
                "the trading of reserve, except while the regulator has stopped reserve "
                "trading. " + AMEND_NOTE)
SUSPENSION_QUOTE = ("The fixture regulator has stopped reserve trading under the fixture "
                    "rules from trading interval 0005H on 14 October 2026, pending a review. "
                    "(Invented passage: this fixture's own words, not a real document's.)")
COMMENCEMENT_QUOTE = ("Reserve trading under the fixture rules commenced on 26 December 2025. "
                      "(Invented passage: this fixture's own words, not a real document's.)")

_CAPTURE = {"basis_kind": "capture_logged_at", "basis_ref": "the fixture's own fetch log (invented)"}
_AMENDMENT_UNKNOWN = ("the fixture holds no rules copy carrying this amendment; the note is "
                      "read from the order copy's own text")


def sources():
    return [
        {"source_id": "src:fixture-rules-2025-08-31", "held": True,
         "issuer": "Fixture Regulator",
         "title": "Synthetic reserve market rules, as of 31 August 2025 (fixture copy)",
         "version": "as of 2025-08-31",
         "locator": "fixture://rules-2025-08-31 (invented; nothing was fetched)",
         "content_type": "application/pdf", "bytes": 118000, "pages": 42,
         "sha256": RULES_SHA,
         "published": "2025-09-03",
         "published_basis": "the fixture copy's own stated posting date",
         "stated": {"approving_circular": "Fixture DC No. 2025-08-0011",
                    "effective": "2025-08-31"},
         "first_availability": {"state": "known", "value": RULES_READ,
                                **_CAPTURE,
                                "note": "the time the fixture says this workflow first read "
                                        "the copy; invented with the fixture"},
         "note": "invented for CORP-5's labelled demonstration; no such document exists"},
        {"source_id": "src:fixture-order-2026-10-12", "held": True,
         "issuer": "Fixture Regulator",
         "title": "Synthetic order stopping reserve trading (fixture copy)",
         "version": "2026-10-12",
         "locator": "fixture://order-2026-002 (invented; nothing was fetched)",
         "content_type": "text/html", "bytes": 9100,
         "sha256": ORDER_SHA,
         "published": "2026-10-12",
         "published_basis": "the fixture copy's own stated date",
         "first_availability": {"state": "known", "value": ORDER_READ,
                                **_CAPTURE,
                                "note": "the time the fixture says this workflow first read "
                                        "the order; invented with the fixture"},
         "note": "invented for CORP-5's labelled demonstration; no such order exists"},
    ]


def rule_versions():
    return [
        {"version_id": "rv-fixture-4.2.1-2025-08-31", "clause_label": "4.2.1",
         "family": "fixture_rules", "title": "Reserve trading",
         "why": "the clause the fixture's action stops",
         "text": BASELINE_TEXT, "text_digest": sha(BASELINE_TEXT),
         "locator": {"source_id": "src:fixture-rules-2025-08-31",
                     "source_revision": "2025-08-31", "digest": RULES_SHA, "page": 12,
                     "start": 400, "end": 400 + len(BASELINE_TEXT),
                     "into": "the fixture copy's extracted text, offsets in Unicode "
                             "characters (invented with the fixture)"},
         "effective": {"value": "2025-08-31", "precision": "day",
                       "note": "the fixture copy's own issue date"},
         "first_availability": {"state": "known", "value": RULES_READ, "basis": _CAPTURE},
         "amendments": [{"ref": "Fixture DC No. 2016-10-0014", "dated": "2016-10-14",
                         "kind": "added", "reached": "4.2.1",
                         "note": BASELINE_NOTE, "note_digest": sha(BASELINE_NOTE),
                         "locator": {"page": 12, "start": 500,
                                     "end": 500 + len(BASELINE_NOTE)},
                         "held": False,
                         "first_availability": {"state": "unknown",
                                                "reason": _AMENDMENT_UNKNOWN}}]},
        {"version_id": "rv-fixture-4.2.1-2026-10-14", "clause_label": "4.2.1",
         "family": "fixture_rules", "title": "Reserve trading",
         "replaces": "rv-fixture-4.2.1-2025-08-31",
         "why": "the clause as the fixture order leaves it: reserve trading stops",
         "text": AMENDED_TEXT, "text_digest": sha(AMENDED_TEXT),
         "locator": {"source_id": "src:fixture-order-2026-10-12",
                     "source_revision": "2026-10-12", "digest": ORDER_SHA, "page": 3,
                     "start": 200, "end": 200 + len(AMENDED_TEXT),
                     "into": "the fixture order's extracted text, offsets in Unicode "
                             "characters (invented with the fixture)"},
         "effective": {"value": "2026-10-14", "precision": "day",
                       "note": "the date the fixture order states the stop takes effect"},
         "first_availability": {"state": "known", "value": ORDER_READ, "basis": _CAPTURE},
         "amendments": [{"ref": "Fixture Order No. 2026-002", "dated": "2026-10-12",
                         "kind": "amended", "reached": "4.2.1",
                         "note": AMEND_NOTE, "note_digest": sha(AMEND_NOTE),
                         "locator": {"page": 3, "start": 250, "end": 250 + len(AMEND_NOTE)},
                         "held": True,
                         "first_availability": {"state": "known", "value": ORDER_READ,
                                                "basis": _CAPTURE}}]},
        {"version_id": "rv-fixture-4.2.2-2025-08-31", "clause_label": "4.2.2",
         "family": "fixture_rules", "title": "Reserve market reports",
         "why": "a clause with no amendment, so the block shows both shapes",
         "text": "4.2.2 Reports. The market operator shall report reserve trading weekly.",
         "text_digest": sha("4.2.2 Reports. The market operator shall report reserve trading "
                            "weekly."),
         "locator": {"source_id": "src:fixture-rules-2025-08-31",
                     "source_revision": "2025-08-31", "digest": RULES_SHA, "page": 13,
                     "start": 100, "end": 174,
                     "into": "the fixture copy's extracted text, offsets in Unicode "
                             "characters (invented with the fixture)"},
         "effective": {"value": "2025-08-31", "precision": "day",
                       "note": "the fixture copy's own issue date"},
         "first_availability": {"state": "known", "value": RULES_READ, "basis": _CAPTURE},
         "amendments": []},
    ]


def passages():
    return [
        {"passage_id": "p-fixture-suspension", "key": "suspension",
         "source_id": "src:fixture-order-2026-10-12", "start": 600,
         "end": 600 + len(SUSPENSION_QUOTE), "page": 1,
         "into": "the fixture order's extracted text",
         "quote": SUSPENSION_QUOTE, "quote_digest": sha(SUSPENSION_QUOTE)},
        {"passage_id": "p-fixture-commencement", "key": "commencement",
         "source_id": "src:fixture-rules-2025-08-31", "start": 900,
         "end": 900 + len(COMMENCEMENT_QUOTE), "page": 12,
         "into": "the fixture copy's extracted text",
         "quote": COMMENCEMENT_QUOTE, "quote_digest": sha(COMMENCEMENT_QUOTE)},
    ]


def claims():
    return [
        {"claim_id": "claim:fixture-suspension", "claim_revision": 1,
         "subject_ref": "market-product:fixture-reserve-market", "subject_type": "MarketProduct",
         "predicate": "refersTo", "object_value": "suspended", "modality": "actual",
         "attributed_to": "Fixture Regulator",
         "passage_ref": "p-fixture-suspension",
         "stated_valid_time": {"start": "2026-10-14", "precision": "day",
                               "note": "the fixture order states the stop begins at trading "
                                       "interval 0005H on 14 October 2026 and names no end"},
         "note": "invented; the announcement that changed the clause's operation"},
        {"claim_id": "claim:fixture-commencement", "claim_revision": 1,
         "subject_ref": "market-product:fixture-reserve-market", "subject_type": "MarketProduct",
         "predicate": "effectiveDuring", "object_value": "in_operation", "modality": "actual",
         "attributed_to": "Fixture Regulator",
         "passage_ref": "p-fixture-commencement",
         "stated_valid_time": {"start": "2025-12-26", "precision": "day", "note": None},
         "note": "invented; the announcement that was available before the action as well"},
    ]


def relations():
    attested = {"basis_kind": "attested",
                "basis_ref": "the fixture's own record, evidence-manifest.json",
                "note": "the fixture's mapping, invented with the fixture"}
    available = {"availability_value": RULES_READ, "availability_precision": "second",
                 "availability": attested}
    return [
        {"relation_id": "rel-fixture-suspension-bears-on-clause", "relation_kind": "refersTo",
         "from_ref": "claim:fixture-suspension", "from_type": "Claim",
         "to_ref": "clause:4.2.1", "to_type": "RuleVersion",
         "notes": "the fixture's action concerns the reserve trading clause 4.2.1 governs",
         "review_state": "proposed", **available},
        {"relation_id": "rel-fixture-commencement-bears-on-clause", "relation_kind": "refersTo",
         "from_ref": "claim:fixture-commencement", "from_type": "Claim",
         "to_ref": "clause:4.2.1", "to_type": "RuleVersion",
         "notes": "the commencement the fixture states is what clause 4.2.1 provides for",
         "review_state": "proposed", **available},
        {"relation_id": "rel-fixture-assumption-depends-on-market", "relation_kind": "dependsOn",
         "from_ref": "assumption:fixture-reserve-procurement",
         "from_type": "AssumptionRevision",
         "to_ref": "market-product:fixture-reserve-market", "to_type": "MarketProduct",
         "notes": "the fixture accepts this edge, so the store's own walk returns it; the "
                  "real case's mapping is still proposed",
         "review_state": "accepted", **available},
    ]


def entities():
    return [
        {"entity_id": "issuer:fixture-regulator", "entity_type": "Issuer",
         "label": "Fixture Regulator (invented)"},
        {"entity_id": "market-product:fixture-reserve-market", "entity_type": "MarketProduct",
         "label": "the fixture's reserve market (invented)"},
        {"entity_id": "clause:4.2.1", "entity_type": "RuleVersion",
         "label": "the fixture's reserve trading clause (invented)"},
        {"entity_id": "clause:4.2.2", "entity_type": "RuleVersion",
         "label": "the fixture's reserve reporting clause (invented)"},
        {"entity_id": "assumption:fixture-reserve-procurement",
         "entity_type": "AssumptionRevision",
         "label": "the fixture's prepared assumption about reserve procurement (invented)"},
    ]


def build():
    """The fixture's evidence manifest, digests computed from the texts above."""
    return {
        "schema": "corpus.case.evidence-manifest.v1",
        "case_id": CASE_ID,
        "title": TITLE,
        "built_by": "tests/fixtures/grid/event/rules-in-force/build.py",
        "recorded_at": RECORDED_AT,
        "manifest_path": "tests/fixtures/grid/event/rules-in-force/evidence-manifest.json",
        "fixture_note": "built by scripts/grid/build_rules.py from "
                        "tests/fixtures/grid/event/rules-in-force/evidence-manifest.json and "
                        "the corpus store; every record here is a labelled synthetic fixture "
                        "record, invented to demonstrate the path the real case cannot yet show",
        "fixture": {
            "label": "Synthetic fixture — not a fact about the real market",
            "why": "the reserve-market case's real copies carry no first-availability evidence, "
                   "so no cutoff can place a clause version there and a refusal alone "
                   "demonstrates nothing. This fixture keeps the case's shape and invents the "
                   "records that carry availability evidence, so the page shows a clause in "
                   "force, the amendment that reached it, the announcement that changed it, and "
                   "the version each cutoff refuses — with the cutoff respected.",
        },
        "cutoffs": CUTOFFS,
        "action": {"issuer": "Fixture Regulator",
                   "effective": "2026-10-14T00:05:00+08:00",
                   "effective_note": "invented: trading interval 0005H on 14 October 2026; the "
                                     "same date as the real case, so the two cutoffs are the "
                                     "same two days",
                   "through": "the fixture order No. 2026-002 dated 12 October 2026, an "
                              "invented order"},
        "governs": {
            "series": {"series_ref": "series:fixture-five-minute:dr_short_mw",
                       "definition": "the dispatchable reserve the fixture operator requires, "
                                     "and the shortfall against it, MW",
                       "definition_ref": "src/grid/grid.js",
                       "source": "the fixture's own series record (invented); no bytes",
                       "open": "nothing is open about an invented series"},
            "assumption": {"ref": "assumption:fixture-reserve-procurement",
                           "state": "prepared",
                           "proposition": "Reserve is procured through the fixture's spot "
                                          "market for reserve.",
                           "prepared_note": "the fixture prepares it and no analyst has "
                                            "accepted it"},
            "product_ref": "market-product:fixture-reserve-market",
        },
        "limits": [
            "This page is a fixture: every record behind it is invented for the test, and no "
            "line here is a fact about the WESM reserve market or the real ERC case.",
            "The fixture exists because the real case's copies carry no evidence of access, so "
            "no cutoff places a clause there. The fixture keeps that shape and invents the "
            "evidence, so the whole path is shown once, end to end.",
            "The dates, fingerprints, offsets and fetch times are invented with it; nothing was "
            "fetched, read from a document, or produced by a model.",
            "The dependency walk returns one accepted edge because the fixture accepts it; the "
            "real case's own mapping is still proposed, and the page says so there.",
        ],
        "sources": sources(),
        "rule_versions": rule_versions(),
        "passages": passages(),
        "claims": claims(),
        "relations": relations(),
        "entities": entities(),
        "gaps": [],
    }


def render(manifest):
    return json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def load_build_rules():
    spec = importlib.util.spec_from_file_location("nowcast_build_rules_fixture", RULES_BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="compare the committed manifest and view with a fresh build")
    options = parser.parse_args(argv)
    manifest_text = render(build())
    build_rules = load_build_rules()
    view_path = HERE / "view.json"
    if options.check:
        view_text = build_rules.render(build_rules.build(MANIFEST)[0])
        stale = []
        for path, text in ((MANIFEST, manifest_text), (view_path, view_text)):
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        if stale:
            print("STALE: %s differ from a fresh build" % ", ".join(stale))
            return 1
        print("current: %s and %s (%d and %d bytes)"
              % (MANIFEST.name, view_path.name, len(manifest_text), len(view_text)))
        return 0
    # The manifest is written first: build_rules.py reads it from disk, as it does for the
    # real case, so the view is built from exactly the bytes that land here.
    MANIFEST.write_text(manifest_text, encoding="utf-8")
    view_text = build_rules.render(build_rules.build(MANIFEST)[0])
    view_path.write_text(view_text, encoding="utf-8")
    print("wrote %s (%d bytes) and %s (%d bytes)"
          % (MANIFEST, len(manifest_text), view_path, len(view_text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
