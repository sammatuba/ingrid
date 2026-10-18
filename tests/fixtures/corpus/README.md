# Corpus fixtures: synthetic bytes, no real document

Everything here is **fictional**. No issuer, resolution, date, market action or company datum
in this directory is real, and no real document byte or fetched page is committed anywhere in
this repository. The acquisition tests read these bytes; the records they produce are labelled
synthetic.

| File | What it is | Used by |
|---|---|---|
| `synthetic-listing.html` | a fictional listing page with a title, a list, a script element and two paragraphs | [tests/test_corpus_acquire.py](../../test_corpus_acquire.py) |

The fixtures are small on purpose: the tests build the PDF fixture in the test itself (a routine
writes a two-page PDF into a temporary directory), because a binary document would be an opaque
blob in review and would tempt a reader into treating a name as evidence. The text of
`synthetic-listing.html` is written so a page boundary, a markup boundary and a script element
can each be checked against the text layer the adapter produces.

Document bytes fetched from a real issuer are never committed. The fetch tool writes them under
`.local/corpus/fetched/`, which Git ignores, and the orchestrator uploads them to the company
bucket with `scripts/corpus/upload.sh`.
