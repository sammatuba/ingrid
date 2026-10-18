#!/usr/bin/env python3
"""Build the synthetic reserve-market fixture for the corpus store.

Every document below is **fictional**: the issuers, locators, dates, clause numbers, suspension
and notice in this file describe nothing real, and the fixture says so. Nothing here is copied
from a real document; the real corpus stays under the ignored `.local/corpus/` tree and no byte
of it enters the repository.

The fixture is built by the real code, not written by hand beside it:

* every document goes through :func:`src.adapters.corpus.acquire.acquire`, so the source
  versions carry the fingerprints, the five times and the state the acquisition contract fixes;
* every passage goes through :func:`src.adapters.corpus.text.TextLayer.locator`, so its offsets
  and its quote digest are the ones the adapter computes over the exact text;
* every rule version comes from :class:`src.regulatory.lineage.RuleRegister`, so the fixture's
  clause chain is the lineage module's own answer, and `tests/test_corpus_store.py` can hold the
  store's SQL against it;
* the embeddings are :func:`src.adapters.corpus.store.local.hash_embedding` — a deterministic
  bag of words, recorded under a model name that says it is a stand-in and nothing about meaning.

    /usr/bin/python3 tests/fixtures/corpus/store/build.py            # rewrite the fixture
    /usr/bin/python3 tests/fixtures/corpus/store/build.py --check    # fail if it is stale
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.adapters.corpus import acquire as acq  # noqa: E402
from src.adapters.corpus import text as tx  # noqa: E402
from src.adapters.corpus.store import local as store_local  # noqa: E402
from src.adapters.corpus.store import records  # noqa: E402
from src.regulatory.lineage import Amendment, AmendmentChange, RuleRegister  # noqa: E402
from src.regulatory.structure import DateMetadata, Source  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "reserve-market.json"
RECORDED = "2026-10-16T00:00:00Z"
EMBEDDING_MODEL = "synthetic-hash-embedding-v1: deterministic stand-in, not a semantic model"
DIMENSION = 64

#: The query the vector-search test ranks with, and the passages it must and must not reach.
QUERY_TEXT = "reserve market suspended extension"

DOCUMENTS = (
    {
        "key": "rules",
        "issuer": "Synthetic PEMC",
        "locator": "https://example.invalid/synthetic/wesm-rules",
        "published": ("2026-01-05", "date"),
        "availability": "2026-01-06T00:00:00Z",
        "basis": {"basis_kind": "archive_snapshot",
                  "basis_ref": "synthetic fixture archive 2026-01",
                  "note": "a fictional dated archive; no real archive is described"},
        "title": "WESM Rules, synthetic baseline",
        "text": (
            "WESM RULES — SYNTHETIC FIXTURE\n"
            "\n"
            "3.5 PROVISION OF RESERVE\n"
            "3.5.4.1 The Market Operator shall schedule and dispatch reserve capacity through\n"
            "the Reserve Market, co-optimised with the Energy Market.\n"
            "3.5.4.2 Reserve capacity shall be traded at the reserve trading intervals.\n"
        ),
    },
    {
        "key": "resolution",
        "issuer": "Synthetic ERC",
        "locator": "https://example.invalid/synthetic/erc/resolutions/2026-0912",
        "published": ("2026-09-24", "date"),
        "availability": "2026-09-25T00:30:00Z",
        "basis": {"basis_kind": "capture_logged_at",
                  "basis_ref": "synthetic fixture capture log",
                  "note": "the fictional instant this fixture was captured"},
        "title": "Resolution 2026-0912, synthetic",
        "text": (
            "RESOLUTION NO. 2026-0912 — SYNTHETIC FIXTURE\n"
            "\n"
            "WHEREAS, the Reserve Market has experienced sustained price separation;\n"
            "RESOLVED, that the Reserve Market is suspended for the period 1 October 2026 to\n"
            "31 December 2026, subject to review.\n"
        ),
    },
    {
        "key": "amendment",
        "issuer": "Synthetic DOE",
        "locator": "https://example.invalid/synthetic/doe/circulars/2026-03",
        "published": ("2026-10-06", "date"),
        "availability": "2026-10-07T00:00:00Z",
        "basis": {"basis_kind": "archive_snapshot",
                  "basis_ref": "synthetic fixture archive 2026-10",
                  "note": "a fictional dated archive; no real archive is described"},
        "title": "Department Circular 2026-03, synthetic",
        "text": (
            "DEPARTMENT CIRCULAR NO. 2026-03 — SYNTHETIC FIXTURE\n"
            "\n"
            "SECTION 1. Amendment to Clause 3.5.4.1. Clause 3.5.4.1 of the WESM Rules is\n"
            "amended to read: The Market Operator shall schedule and dispatch reserve\n"
            "capacity through the Reserve Market, subject to any suspension ordered by the\n"
            "Energy Regulatory Commission.\n"
            "SECTION 2. New Clause 3.5.4.3. The WESM Rules gain a clause 3.5.4.3: The Market\n"
            "Operator shall publish every suspension of the Reserve Market.\n"
            "SECTION 3. Effectivity. This Circular takes effect on 6 October 2026.\n"
        ),
    },
    {
        "key": "notice",
        "issuer": "Synthetic IEMOP",
        "locator": "https://example.invalid/synthetic/iemop/notices/2026-10-12",
        "published": ("2026-10-11", "date"),
        "availability": "2026-10-13T00:00:00Z",
        "basis": {"basis_kind": "archive_snapshot",
                  "basis_ref": "synthetic fixture archive 2026-10",
                  "note": "a fictional dated archive; no real archive is described"},
        "title": "Market Notice 2026-10-12, synthetic",
        "text": (
            "MARKET NOTICE 2026-10-12 — SYNTHETIC FIXTURE\n"
            "\n"
            "The suspension of the Reserve Market is extended to 31 March 2027.\n"
        ),
    },
    {
        "key": "copy",
        "issuer": "Synthetic Energy News",
        "locator": "https://example.invalid/synthetic/news/reserve-suspension",
        "published": ("2026-09-26", "date"),
        "availability": "2026-09-27T00:00:00Z",
        "basis": {"basis_kind": "archive_snapshot",
                  "basis_ref": "synthetic fixture archive 2026-09",
                  "note": "a fictional dated archive; no real archive is described"},
        "title": "Synthetic Energy News, reserve market report",
        "text": (
            "SYNTHETIC ENERGY NEWS\n"
            "\n"
            "The Reserve Market is suspended for the period 1 October 2026 to 31 December\n"
            "2026, the regulator said on Thursday.\n"
        ),
    },
)

#: The text layer's ``strip`` must be a no-op, or an offset computed on the layer would not be
#: an offset in the source bytes. Only the trailing newline of each literal is dropped here.
DOCUMENTS = tuple(dict(document, text=document["text"].rstrip("\n")) for document in DOCUMENTS)

#: One passage per document, quoted verbatim from its text.
PASSAGES = (
    ("rules", "3.5.4.1 The Market Operator shall schedule and dispatch reserve capacity through\n"
              "the Reserve Market, co-optimised with the Energy Market."),
    ("resolution", "RESOLVED, that the Reserve Market is suspended for the period 1 October 2026 "
                   "to\n31 December 2026, subject to review."),
    ("amendment", "The Market Operator shall schedule and dispatch reserve\n"
                  "capacity through the Reserve Market, subject to any suspension ordered by the\n"
                  "Energy Regulatory Commission."),
    ("notice", "The suspension of the Reserve Market is extended to 31 March 2027."),
    ("copy", "The Reserve Market is suspended for the period 1 October 2026 to 31 December\n"
             "2026, the regulator said on Thursday."),
)

#: The amended text the circular substitutes, quoted from the circular itself.
AMENDED_CLAUSE = ("The Market Operator shall schedule and dispatch reserve\n"
                  "capacity through the Reserve Market, subject to any suspension ordered by the\n"
                  "Energy Regulatory Commission.")
ADDED_CLAUSE = "The Market\nOperator shall publish every suspension of the Reserve Market."

CUTOFFS = {
    "before_action": {"value": "2026-09-20", "precision": "day"},
    "after_action_before_amendment": {"value": "2026-10-05", "precision": "day"},
    "after_amendment": {"value": "2026-10-20", "precision": "day"},
}


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _availability(document):
    """The acquisition's availability: an instant with the typed basis the register states.

    The acquisition contract takes evidence of an instant, never a bare date, so a fictional
    capture is an instant too; the coarse, date-precision availabilities appear on the rule
    versions and the relations, where the record is a supplied date.
    """
    basis = document["basis"]
    return acq.Availability(basis["basis_kind"], basis["basis_ref"], document["availability"],
                            basis["note"])


def _source_row(document, layer):
    availability = _availability(document)
    metadata = acq.SuppliedMetadata(
        issuer=document["issuer"], locator=document["locator"],
        publication=acq.SuppliedDate.stated(*document["published"]),
        licence_ref="synthetic fixture: no terms, no real document",
        availability=availability, first_availability_rule=availability.basis_kind,
        synthetic=True)
    content = document["text"].encode("utf-8")
    record = acq.acquire(content, metadata, recorded_at=RECORDED)
    assert record.state == "compilable", document["key"]
    assert round_trip(layer, document["text"]), document["key"]
    return records.source_version_row(record)


def round_trip(layer, text):
    """The text layer of a plain-text document is the document, so offsets are the text's."""
    return layer.text == text


def _passage_payload(document, layer, quote, source_row):
    start = layer.text.index(quote)
    locator = layer.locator(1, start, start + len(quote))
    payload = {"source_id": source_row["source_id"], "source_version": source_row["source_version"],
               "start": locator["start"], "end": locator["end"], "quote": locator["quote"],
               "quote_digest": locator["quote_digest"], "page": locator["page"],
               "page_start": locator["page_start"], "page_end": locator["page_end"]}
    return payload, records.passage_row(payload, source_row)


def _source(document):
    text = document["text"]
    return Source(source_id="synthetic:" + document["key"], source_revision="1",
                  digest=_sha256(text), original_bytes=text.encode("utf-8"))


def _clause_locator(document, quote):
    text = document["text"]
    start = text.index(quote)
    source = _source(document)
    from src.regulatory.structure import Locator
    return source, Locator(source.source_id, source.source_revision, source.digest,
                           start, start + len(quote))


def rules(documents, first_availability="2026-01-06", effective="2026-01-05"):
    """The register: a baseline from the rules document and one amendment from the circular."""
    register = RuleRegister("wesm_rules")
    baseline = _source(documents["rules"])
    register.add_baseline(baseline, DateMetadata(first_availability, "day", None),
                          effective=DateMetadata(effective, "day", None), kinds=("clause",))
    amended_source, amended_locator = _clause_locator(documents["amendment"], AMENDED_CLAUSE)
    _, added_locator = _clause_locator(documents["amendment"], ADDED_CLAUSE)
    changes = (AmendmentChange("3.5.4.1", amended_locator, AMENDED_CLAUSE,
                               replaces=register.versions("3.5.4.1")[-1].version_id),
               AmendmentChange("3.5.4.3", added_locator, ADDED_CLAUSE, adds_clause=True))
    register.apply(Amendment(amended_source, "DOE-DC-2026-03",
                             DateMetadata("2026-10-06", "day", None),
                             DateMetadata("2026-10-07", "day", None), changes))
    return register


def _rule_rows(register, sources):
    """Every registered version as a row, with the provenance of the source it was read from.

    Each version's locator names the document it was read out of, and that document's
    ``source_versions`` row is the resolved provenance: this fixture's five documents are
    synthetic, so their versions are synthetic — and a real document loaded through the same
    call would be recorded as what it is. The lookup is by the locator's own source id, so a
    version whose document is not among the acquired rows fails loudly instead of defaulting.
    """
    resolved = {"synthetic:" + key: row for key, row in sources.items()}
    rows = []
    for label in register.labels():
        for version in register.versions(label):
            rows.append(records.rule_version_row(version, "wesm_rules", RECORDED,
                                                 source_row=resolved[version.locator.source_id]))
    return rows


def _claim(subject="commodity:synthetic-reserve-market", **overrides):
    row = {"claim_id": "claim:synthetic-placeholder", "claim_revision": 1,
           "subject_ref": subject, "subject_type": "Commodity", "predicate": "reports",
           "object_value": "suspended", "modality": "actual",
           "attributed_to": "Synthetic issuer",
           "recorded_at": RECORDED, "review_state": "proposed", "synthetic": True}
    row.update(overrides)
    return row


def _relation(kind, from_ref, from_type, to_ref, to_type, availability, state="accepted",
              **overrides):
    row = {"relation_kind": kind, "from_ref": from_ref, "from_type": from_type, "to_ref": to_ref,
           "to_type": to_type, "availability_value": availability[0],
           "availability_precision": availability[1],
           "availability_basis": {"basis_kind": "attested",
                                  "basis_ref": "synthetic fixture analyst",
                                  "note": "a fictional analyst's record"},
           "recorded_at": RECORDED, "review_state": state, "synthetic": True}
    row.update(overrides)
    return row


def build():
    """``(fixture, register, layers)``: the JSON-safe fixture, the register and the text layers."""
    documents = {document["key"]: document for document in DOCUMENTS}
    layers, sources = {}, {}
    for key, document in documents.items():
        layers[key] = tx.extract(document["text"].encode("utf-8"), "text/plain")
        sources[key] = _source_row(document, layers[key])
    passages, passage_ids = [], {}
    for key, quote in PASSAGES:
        _, row = _passage_payload(documents[key], layers[key], quote, sources[key])
        passages.append(row)  # the fixture holds the rows the store loads, not the payloads
        passage_ids[key] = row["passage_id"]
    register = rules(documents)
    rule_rows = _rule_rows(register, sources)
    claims = [
        _claim(claim_id="claim:synthetic-erc-suspension", attributed_to="Synthetic ERC",
               source_id=sources["resolution"]["source_id"],
               source_version=sources["resolution"]["source_version"],
               passage_id=passage_ids["resolution"], object_value="suspension_ordered",
               locator_start=passages[1]["start_offset"], locator_end=passages[1]["end_offset"],
               quote_digest=passages[1]["quote_digest"], extraction_method="synthetic_fixture",
               extraction_version="v1", review_state="accepted",
               event_value="2026-10-01", event_precision="day",
               event_end_value="2026-12-31", event_end_precision="day",
               published_value="2026-09-24", published_precision="date",
               availability_value="2026-09-25T00:30:00Z", availability_precision="second",
               availability_basis={"basis_kind": "capture_logged_at",
                                   "basis_ref": "synthetic fixture capture log",
                                   "note": "the fictional instant this fixture was captured"}),
        _claim(claim_id="claim:synthetic-extension", attributed_to="Synthetic IEMOP",
               source_id=sources["notice"]["source_id"],
               source_version=sources["notice"]["source_version"],
               passage_id=passage_ids["notice"], object_value="suspension_extended",
               locator_start=passages[3]["start_offset"], locator_end=passages[3]["end_offset"],
               quote_digest=passages[3]["quote_digest"], extraction_method="synthetic_fixture",
               extraction_version="v1", review_state="accepted",
               event_value="2027-01-01", event_precision="day",
               event_end_value="2027-03-31", event_end_precision="day",
               published_value="2026-10-11", published_precision="date",
               availability_value="2026-10-13T00:00:00Z", availability_precision="second",
               availability_basis={"basis_kind": "archive_snapshot",
                                   "basis_ref": "synthetic fixture archive 2026-10",
                                   "note": "a fictional dated archive; no real archive is described"}),
        _claim(claim_id="claim:synthetic-news-copy", attributed_to="Synthetic Energy News",
               source_id=sources["copy"]["source_id"],
               source_version=sources["copy"]["source_version"],
               passage_id=passage_ids["copy"],
               locator_start=passages[4]["start_offset"], locator_end=passages[4]["end_offset"],
               quote_digest=passages[4]["quote_digest"], extraction_method="synthetic_fixture",
               extraction_version="v1",
               published_value="2026-09-26", published_precision="date",
               availability_value="2026-09-27T00:00:00Z", availability_precision="second",
               availability_basis={"basis_kind": "archive_snapshot",
                                   "basis_ref": "synthetic fixture archive 2026-09",
                                   "note": "a fictional dated archive; no real archive is described"}),
    ]
    relations = [
        _relation("dependsOn", "assumption:synthetic-reserve-adequacy", "AssumptionRevision",
                  "commodity:synthetic-reserve-market", "Commodity", ("2026-09-20", "day"),
                  notes="a fictional assumption that depends on the reserve market"),
        _relation("dependsOn", "scenario:synthetic-q4-outlook", "ScenarioAlternative",
                  "assumption:synthetic-reserve-adequacy", "AssumptionRevision",
                  ("2026-09-21", "day"), notes="a fictional scenario built on the assumption"),
        _relation("copiedFrom", "claim:synthetic-news-copy", "Claim",
                  "claim:synthetic-erc-suspension", "Claim", ("2026-09-27", "day"),
                  notes="the news item restates the resolution; it adds no independent source"),
        _relation("challenges", "claim:synthetic-erc-suspension", "Claim",
                  "assumption:synthetic-reserve-adequacy", "AssumptionRevision",
                  ("2026-09-25", "day"),
                  notes="the action bears on the assumption; a challenge is a reason to "
                        "reconsider, not proof it is false"),
    ]
    entities = [
        {"entity_id": "commodity:synthetic-reserve-market", "entity_type": "Commodity",
         "label": "Synthetic reserve market (fictional)", "issuer": "Synthetic PEMC",
         "recorded_at": RECORDED, "review_state": "accepted", "synthetic": True},
        {"entity_id": "assumption:synthetic-reserve-adequacy", "entity_type": "AssumptionRevision",
         "label": "Synthetic reserve adequacy assumption (fictional)",
         "recorded_at": RECORDED, "review_state": "accepted", "synthetic": True},
        {"entity_id": "scenario:synthetic-q4-outlook", "entity_type": "ScenarioAlternative",
         "label": "Synthetic fourth-quarter outlook (fictional)",
         "recorded_at": RECORDED, "review_state": "accepted", "synthetic": True},
        {"entity_id": "issuer:synthetic-erc", "entity_type": "Issuer",
         "label": "Synthetic ERC (fictional)", "issuer": "Synthetic ERC",
         "recorded_at": RECORDED, "review_state": "accepted", "synthetic": True},
    ]
    vectors = {passage_ids[key]: store_local.hash_embedding(quote, DIMENSION)
               for key, quote in PASSAGES}
    fixture = {
        "fixture": "corpus-store-reserve-market-synthetic.v1",
        "marker": "SYNTHETIC",
        "note": ("Every issuer, locator, date, clause, claim and number in this file is "
                 "fictional. It is built by tests/fixtures/corpus/store/build.py from the "
                 "real corpus, lineage and store code, and no real document byte is in it."),
        "cutoffs": CUTOFFS,
        "query": QUERY_TEXT,
        "embeddings": {"model": EMBEDDING_MODEL, "dimension": DIMENSION, "vectors": vectors},
        "tables": {"source_versions": [sources[document["key"]] for document in DOCUMENTS],
                   "passages": passages, "rule_versions": rule_rows,
                   "claims": claims, "relations": relations, "entities": entities},
        "passage_ids": passage_ids,
        "clause_labels": ["3.5.4.1", "3.5.4.3"],
        "amendment_ref": "DOE-DC-2026-03",
    }
    return fixture, register, layers


def render(fixture):
    return json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fixture, _, _ = build()
    text = render(fixture)
    if "--check" in argv:
        held = FIXTURE.read_text(encoding="utf-8") if FIXTURE.exists() else ""
        if held != text:
            print("STALE: %s differs from what build.py produces" % FIXTURE.name)
            return 1
        print("current: %s (%d bytes)" % (FIXTURE.name, len(text)))
        return 0
    FIXTURE.write_text(text, encoding="utf-8")
    print("wrote %s (%d bytes)" % (FIXTURE, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
