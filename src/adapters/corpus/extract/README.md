# Corpus extraction: proposed claims with whole-passage citations

The module the [corpus plan note](../../../../docs/work/corpus/intent.md) calls CORP-3: a model
reads the compiled permitted passages and proposes claims typed by the
[ontology profile](../../../../docs/architecture/ontology-profile-v1.md); code checks every
citation against the source version's own text layer; an analyst accepts. The task record
with commands, evidence and the recorded gaps is
[extraction.md](../../../../docs/work/corpus/extraction.md).

| Module | What it holds |
|---|---|
| [`schema.py`](schema.py) | The claim shape: subject typed reference, predicate from the profile's relation list, typed object or value, modality, exact passage citation (source id, immutable source version, offsets and quoted text), stated valid time with its precision — one object that is both the Gemini `responseFormat` schema and the validator's contract. Every claim enters as `proposed`, and the claim id carries the cited revision. |
| [`check.py`](check.py) | Refuses a claim whose citation is not the complete compiled passage the model was given — source id, immutable version, offsets and quote — or whose version's own text layer does not show the quote at exactly those offsets; refuses a citation that is not one of the compiled permitted passages; partitions a run into kept claims and recorded refusals. |
| [`run.py`](run.py) | Builds the System Two request (the compiled permitted passages as the only state, the instructions, the response schema, the decided thinking level), binds every supplied passage's layer to its immutable version before any call, calls the existing Gemini transport unchanged, replays a stored response offline, and records the receipt: request digest, model version, tokens, time. |

## The two recorded gaps

* **G-1, thinking level — blocking.** The owner's GATE-8 decision for extraction is Gemini
  3.8 Flash with thinking level high, and the request **carries that decision at the wire**
  (`thinkingConfig` `{"thinkingLevel": "HIGH"}`, the spelling the Vertex probe table
  exercised). The unchanged transport's body validator accepts only `{"thinkingBudget": 0}`
  for `vertex_ai` and no `thinkingConfig` for `gemini_developer`, so it cannot carry the
  decided level until a CORE transport change lands: every request and receipt records the
  decision (`thinking.decided`), the form carried (`thinking.carried`), what the transport
  accepts (`thinking.transport_accepts`) and `thinking.carried_by_transport` (`false`
  today), and `--live` refuses `THINKING_NOT_CARRIED_BY_TRANSPORT` before it builds a
  transport, writes a ledger or reads a credential. Nothing is silently downgraded and
  nothing is faked.
* **G-2, the case label.** `LiveConfig` fixes `permitted_case` to `synthetic-case` so the
  fictional cited task cannot be turned on real data. The extraction runs over permitted
  corpus documents rather than a review case, so `scripts/corpus/extract.py` lifts that
  one bound by subclass (`CorpusLiveConfig`) — the recorded pattern of the grid-desk live
  run — with every other bound unchanged and the label in every receipt.

## Running it

`scripts/corpus/extract.py` is the operator's path: `--prepare` reads a run spec over the
ignored local store and writes the request; `--replay` runs a stored response through the
same checks offline; `--live` is the one step that calls the transport, run by the
orchestrator with an approved configuration — blocked while G-1 stands. `--prepare`
resolves each document against the acquisition records this workflow already holds (the
`*.acquisition.json` payloads beside the bytes and the source payloads of earlier run
files), keys the run's provenance and layers by immutable version (`source_id@version`),
and refuses two contents that resolve to one version identity rather than merging them.
The command for the first live extraction, the reserve-market documents and its
preconditions are in the task record. No document byte enters the repository, and no claim
from any run writes to the review core: a claim moves an assumption or an applicability
assessment only through an analyst's recorded accept.
