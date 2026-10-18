# Corpus extraction fixtures

Fictional documents for the corpus tests. Every issuer, unit, date and URL here is made
up, each file says what it is, and nothing in this directory is a document byte from the
company copy, the PEMC compendium or any fetched page — those stay under the ignored
`.local/corpus/` tree and never enter Git. See
[the acquisition record](../../../../docs/work/corpus/acquisition.md) and
[the extraction record](../../../../docs/work/corpus/extraction.md).

| File | What it is |
|---|---|
| [`synthetic-notice.txt`](synthetic-notice.txt) | A fictional market notice in six paragraphs: a suspension, a fallback arrangement, a review target, a registered capacity and a new product family. |
| [`synthetic-response.json`](synthetic-response.json) | A stored provider-shaped response — synthetic, not a recorded run — whose five claims cite the notice's own sentences at their exact character offsets of version 1, the immutable revision they name. Generated once for this fixture locator through the real text layer; `tests/test_corpus_extract.py` pins every citation against the notice, so the fixture cannot drift silently. |

The sibling [corpus fixtures](../README.md) hold `synthetic-listing.html`, the fictional
listing page the acquisition tests read.
