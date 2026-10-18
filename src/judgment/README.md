# Cited judgment boundary

`JudgmentService` takes a configured provider, repository and trusted clock. The default
provider is absent and returns `MODEL_DISABLED`; manual review remains available. This module
has no network or model SDK dependency. See the [intent](../../docs/work/m3-gemini/intent.md).

The compiled task supplies allowed passages, attribution, source lineage, prior assumption,
reviewed mapping, typed representation and both cutoffs. Membership metadata and unrelated
sources are excluded. Input JSON is capped at 128 KiB. Output is capped at 32 KiB, one label,
one explanation, 1–32 exact whole-passage citations and at most eight alternatives/unknowns.
Citation indices refer to the immutable task context. Validation proves citation membership,
not the truth or semantic quality of an interpretation. There are no calibrated scores.

A saved `JudgmentArtifact` is an additive h0.v1 record kind; existing kind/hash contracts are
unchanged. Its proposed answer binds to an exact task and trusted provider metadata. Prompt
version plus rendered task produces the request digest; the validated answer produces the
output digest. Immutable identity hashes actor/idempotency key within the tenant/case. A saved
replay returns the original artifact without a clock/model call; a different task conflicts.
Reads recursively recheck source access. New inference requires a current, unblocked task;
commit rechecks after inference. Provider work never occurs inside transaction retries.

The per-service semaphore bounds local inference to one request. Concurrent service instances
can perform duplicate inference for the same key, but the transactional store persists only
the winning artifact. The opt-in [Vertex AI transport](../adapters/gemini/README.md) (CORE-7;
the Developer API class remains as a compatibility alias) implements a process deadline and
durable local attempt allowance. Distributed rate limits, daily spend caps and hosted controls
remain unresolved; the hosted app runs without a judgment provider. A protocol timeout argument alone
does not prove that an arbitrary injected transport enforces it.

`GeminiProvider` implements the request/response shape behind an explicit injected transport.
It sends no tools, requests one candidate and at most 2,048 output tokens, requires `STOP` and
one text part (optional opaque signature metadata), and records the returned model version.
It has no default network transport, credentials,
region or model ID. Local tests use `synthetic_fixture`; no preferred model is assumed to exist.
Transport failure, truncated output and malformed/citation-invalid responses write no judgment.
Live service inputs and actual Gemini evaluation remain open in the
[input register](../../docs/work/input-register.md).
