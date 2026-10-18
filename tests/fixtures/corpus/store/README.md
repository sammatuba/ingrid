# The synthetic reserve-market store fixture

`reserve-market.json` is **fictional**. Every issuer, locator, date, clause, claim and number in
it describes nothing real, and the file itself says so. It holds no byte of any real document:
the compendium, the fetched pages and the extracted text stay under the ignored `.local/corpus/`
tree and never enter the repository.

| File | What it is |
|---|---|
| [build.py](build.py) | builds `reserve-market.json` from the documents below, with the real acquisition, lineage and store code |
| `reserve-market.json` | the six tables' rows, the three cutoffs, the query text and the passage embeddings |

```sh
/usr/bin/python3 tests/fixtures/corpus/store/build.py            # rewrite the fixture
/usr/bin/python3 tests/fixtures/corpus/store/build.py --check    # fail if it is stale
```

The fixture is *built*, not written beside the code: each document goes through
`acquire.acquire` (so the source versions carry real fingerprints, the five times and the
`compilable`/`excluded` state), each passage through `TextLayer.locator` (so its offsets and
quote digest are the adapter's own), each rule version through `RuleRegister` (so the clause
chain is the lineage module's answer, which [`tests/test_corpus_store.py`](../../../test_corpus_store.py)
also holds the store's SQL against), and the embeddings through the store's documented
`hash_embedding` stand-in.

The scene: a fictional baseline rules clause, a fictional resolution suspending the reserve
market, a fictional circular amending the clause and adding one, a fictional notice extending
the suspension, and a fictional news item that copies the resolution's sentence. Three cutoffs
sit before the action, after the action but before the amendment, and after the amendment.
