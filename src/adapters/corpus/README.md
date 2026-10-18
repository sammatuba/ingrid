# Corpus acquisition and text layers

Two standard-library modules that turn a document into an immutable, citable version. They
open no socket, read no file, consult no clock and call no model: the caller brings the
bytes and every time. The plan note is [the corpus intent](../../../docs/work/corpus/intent.md);
the task record with commands and results is
[acquisition.md](../../../docs/work/corpus/acquisition.md). The extraction built on both
is [the `extract` package](extract/__init__.py), recorded in
[extraction.md](../../../docs/work/corpus/extraction.md).

| Module | Input | Output |
|---|---|---|
| [`acquire.py`](acquire.py) | exact bytes plus supplied metadata | one `SourceVersion` record: identity, SHA-256 fingerprint, content type, length, the five times, the licence, and the state that says whether it can be cited |
| [`text.py`](text.py) | exact bytes plus a content type | a text layer record: the extracted text, one entry per page with half-open offsets, and the method and version that produced it |
| [`extract/`](extract/__init__.py) | the compiled permitted passages of compilable versions | proposed, cited claims: the ontology's claim shape, the citation check against the text layers, the System Two request through the Gemini transport, and the run receipt |

`scripts/corpus/fetch.py` drives the acquisition over a register of URLs and writes the
bytes under `.local/corpus/fetched/`; `scripts/corpus/upload.sh` is the documented `gcloud
storage` command the orchestrator runs to move them to the company bucket. Neither runs in
the test suite's network path: the suite exercises the fetch tool's row-to-metadata mapping
against a stub response and the upload command's argument handling against a mocked
`gcloud`, and opens no socket and no bucket.

## One version, one fingerprint

`source_id` is derived from the normalized locator alone, so one resource has one source.
`source_version` is the ordinal of the bytes first seen there:

```python
from src.adapters.corpus import acquire as acq

metadata = acq.SuppliedMetadata(          # placeholder values, as in the fixtures
    issuer="example issuer",
    locator="https://example.invalid/resolutions/2026-0001",
    publication=acq.SuppliedDate.stated("2026-10-14", "date"),
    licence_ref="example: no terms stated",
    capture_time="2026-10-15T05:00:00+08:00")
record = acq.acquire(content, metadata, recorded_at="2026-10-16T11:00:00+08:00")
```

The same bytes at the same locator give the same version, and — given the records the
caller already holds, passed as `prior` — the same record in any order of calls. Changed
bytes give a new version. A later capture of known bytes is evidence for the fetch log,
not a change to the record. A supplied fact that contradicts the record is refused
(`VERSION_CONFLICT`) rather than overwritten; the one repair path is a fact the record
declared unknown, such as a publication the register states later.

## The five times, and the two that stay empty

| Field | Meaning here |
|---|---|
| event time | **absent**: a document version has no single event time; a claim carries it |
| publication time | the value the issuer states, with its precision (`date`, `second`, `fraction`), or unknown with a reason |
| first availability | `known_at` with the typed `availability_basis` the register's rule names, or unknown with a reason |
| recorded time | `recorded_at`: when this acquisition record was written |
| review time | **absent**: acquisition precedes any review decision |

Publication is not availability, and a basis records where first availability was observed,
never when. A date stays a date: nothing turns `2026-04-01` into midnight. Nothing reads a
date out of the content — the fetch tool takes publication only from the register row, and
records an unknown when the row states none. A response's `Last-Modified` stamp is the
delivering server's statement about the resource and is kept beside the version as
`server_last_modified`; it is never publication and never availability. The same holds for
first availability: the fetch tool supplies this workflow's own capture instant, or the
evidence object the register states, and nothing else.

Who the bytes are is stated, never defaulted: every fetch row says whether its bytes are a
real document or a synthetic example and a real row names the permission record it is held
under (`PROVENANCE_NOT_STATED`, `MISSING_PERMISSION_REF`). A real document that would have
been recorded as synthetic, or recorded without its permission, is refused before the
request instead.

## What is excluded, and why

A version is `compilable` only when it carries both a stated publication instant and
supplied first-availability evidence. Otherwise it is recorded `excluded`, with a reason
that names the missing fact, and `source_record` refuses to project it into the review
core. No passage can name it and no compiled context can hold it. This is the conservative
reading the ontology profile asks for: a capture time proves the bytes were reachable then,
not which revision of a rule was knowable at the cutoff, and an undated version cannot be
placed in an amendment chain.

An excluded version keeps everything that makes it findable later: fingerprint, length,
content type, licence, locator and its text layer. When the missing fact arrives, the same
bytes give the same version with the record repaired, because an excluded version was
never projected and nothing downstream can depend on it.

## The text layer

`TextLayer.text` is the extracted text of the exact bytes; `sha256` is the fingerprint of
those bytes, so a layer always points back at its version. Each `Page` carries half-open
offsets into that text, empty pages included, so page numbers never shift:

```python
from src.adapters.corpus import text as tx

layer = tx.extract(content, "text/html")
quote = "The synthetic reserve market is suspended for the declared period."
start = layer.text.index(quote)                         # the fixture's own sentence
locator = layer.locator(1, start, start + len(quote))   # page-relative in, layer-wide out
passage = acq.passage_record(source_record, layer, locator, "passage:1", recorded_at)
```

Offsets count Unicode code points of the decoded text, the unit the review core's
`Passage` offsets use. A locator carries both the page-relative offsets and the layer-wide
ones the core wants, plus the quote and its digest; `validate_locator` refuses a locator
whose forms disagree, so a `Passage` is never built from offsets that select other text.
PDF text comes through `pypdf` when it is importable — this package
never installs it, so a caller that wants PDF text puts the unpacked library on
`sys.path` first. When it is absent, or the document is encrypted, or no page yields text
(a scanned PDF needs OCR, which this adapter does not do), the layer is recorded with
status `not_extracted` and that reason. The bytes keep their record either way.

## What reaches the review core

`source_record(record, layer, tenant_id, case_id, recorded_at)` builds the `h0.v2`
`SourceVersion` the compiler reads: `original_text` is the layer text, `source_byte_digest`
fingerprints that text, `published_at` and `known_at` carry the times, and the document's
own fingerprint, length, type, locator, licence and the rule travel in the additive keys
`document_sha256`, `document_length`, `content_type`, `locator`, `licence_ref` and
`first_availability_rule`. The h0 validator does not know those keys and the compiler never
reads them; they exist so a record can always be traced back to the bytes it came from.
`passage_record` turns one page locator into a `Passage`, re-checking both offset forms, the
quote and its digest against the layer and binding the layer to the source's own bytes and
text, so a citation is refused rather than recorded when any part of it does not match.

## Where a version and a passage are stored

[`store/`](store/) is the claim store: it turns these records and the regulatory lineage's
`RuleVersion`s into typed, append-only table rows — with the five times, one derived
availability interval and one cutoff comparison — and answers the ontology profile's
competency questions offline in memory and in sqlite, so the cutoff rule is proved without a
cloud call. What arrives from outside is checked rather than trusted: a passage carries the
source version's own issuer, availability and publication, a claim and its citation name one
document version and the claim is never first available before its evidence — at either end of
the interval, because the end is the column the cutoff compares, so a claim finer than its
evidence cannot answer a cutoff the evidence is excluded from — a rule version's
provenance is resolved from the source version it names or stated, and every read and write
hands out a copy of the row so no caller holds a handle on the store. The BigQuery tables, the
SQL and the load tool are in
[`scripts/corpus/bq/`](../../../scripts/corpus/bq/), and the task record with the exact `bq`
commands and the cost note is [docs/work/corpus/store.md](../../../docs/work/corpus/store.md).
