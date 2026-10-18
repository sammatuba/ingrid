# Bounded Gemini transport: Developer API or Vertex AI

The default workspace keeps AI disabled. The protocol adapter accepts an explicitly supplied
transport. `transport.py` adds an opt-in, stdlib-only implementation for one of two fixed
services; it does not discover credentials, select a model or activate an application provider.

Prepare the fictional task without configuration or network activity:

```sh
/usr/bin/python3 scripts/m3/gemini-run.py
```

This writes `.local/m3-live/prepared.json`, with the exact compiled task, source, mapping and
semantic review checks. It is offline preparation, not a Gemini answer.

## Explicit service configuration

Live execution needs an operator-supplied local JSON file. Only use approved project/model,
case and budget references. The project label is operator configuration; on the Developer API
the API key determines the actual Google project and this adapter does not independently
verify that association.

The required `api` key selects one fixed service. Every other version/location pair, a missing
`api` or an unknown value is rejected as `MODEL_CONFIG_INVALID` before any network work:

| `api` | `api_version` | `location` | host | credential header |
|---|---|---|---|---|
| `gemini_developer` | `v1beta` | `global` | `generativelanguage.googleapis.com` | `x-goog-api-key` |
| `vertex_ai` | `v1` | `global` | `aiplatform.googleapis.com` | `Authorization: Bearer <token>` and `x-goog-user-project <project>` |

Vertex AI is served here from the global endpoint only, at the publisher path
`/v1/projects/{project}/locations/global/publishers/google/models/{model}:generateContent`; the
approved model answers 404 on the regional host. A Developer API key cannot satisfy a Vertex AI
requirement and a Vertex token cannot be used on the Developer host.

Both files share the keys below; placeholders are **not approved for execution**:

```json
{
  "api": "gemini_developer",
  "project": "replace-with-approved-project",
  "model": "gemini-approved-model",
  "credential_env": "APPROVED_GEMINI_API_KEY",
  "authorization_ref": "replace-with-recorded-service-case-and-budget-authorization",
  "run_id": "approved-smoke-001",
  "permitted_case": "synthetic-case",
  "budget_policy": "request_and_token_limits",
  "api_version": "v1beta",
  "location": "global",
  "max_attempts": 1,
  "timeout_seconds": 30,
  "max_request_bytes": 196608,
  "max_response_bytes": 65536,
  "max_output_tokens": 2048
}
```

The Vertex AI file differs only in the four service keys, for example:

```json
{
  "api": "vertex_ai",
  "project": "replace-with-approved-project",
  "model": "gemini-approved-model",
  "credential_env": "VERTEX_ACCESS_TOKEN",
  "api_version": "v1",
  "location": "global"
}
```

Keep the file under ignored `.local/`; keep the secret value in the specified environment
variable through the approved credential setup. Do not put a key value into this JSON or Git.
The trusted host configuration must refer to authorization for transmitting the fictional
case and for the specified service/request/token bounds. Source records and browser requests
cannot supply this configuration. It is not an authority-verification service.

## Real cases: the signed-permission allowlist

`permitted_case` is the fictional case or one real case from the transport's own allowlist
(`REAL_CASE_ALLOWLIST` in `transport.py`), which binds each real case id there to the one signed
permission record that permits transmitting that case's records. The permission is never a
configuration value: a file carrying a `permission_ref` or `permission` key is rejected as
`MODEL_CONFIG_INVALID`, and a case id outside the table is rejected the same way, so no caller,
request or source record can add a case or substitute a permission.

Before any attempt is reserved, the transport requires:

- the caller's declared case to equal the configured case (`MODEL_CASE_MISMATCH` otherwise: a
  caller that does not declare a real case never transmits one), and
- the bound record under `docs/work/permissions/` to be a live grant: only a record whose
  `Status:` line leads with `signed` counts, so an absent, unsigned, withdrawn or revoked record
  is `MODEL_PERMISSION_UNAVAILABLE`.

Both refusals happen before the worker starts, before the credential is read and before an
allowance is reserved: no request, no consumed attempt and no receipt. The repository registry
(`src/review/records.load_permissions`) reads any status but the draft marker as signed; the
transport reads affirmatively because it authorizes transmission, so every identifier the
transport permits the registry also holds. A receipt records `permission_ref` beside
`permitted_case` (null for the fictional case) and still never a credential value.

The transport does not compile a case. `src/adapters/gemini/run.py` prepares the fictional case
only and refuses a configuration naming any other case, so a real-case runner is a separate,
reviewed addition, and adding a real case is a reviewed change to the allowlist table.

## Operator token step (Vertex AI)

The credential is read only from the environment variable named by `credential_env`. For
Vertex AI the operator exports a short-lived access token for the approved project, obtained
through the already-authenticated operator tooling:

```sh
export VERTEX_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
```

The transport never reads credential files, runs `gcloud`, refreshes or discovers credentials;
it sends the exported value as `Authorization: Bearer <token>` with
`x-goog-user-project: <configured project>`. Access tokens expire in about an hour, so re-export
before the approved run. A blank or absent value is refused as `MODEL_CREDENTIAL_MISSING` before
any attempt is reserved: no request is sent, no allowance is consumed and no receipt is written.
A rejected or expired token reaches the provider and fails as `MODEL_AUTH_FAILED` with the
attempt consumed. Neither is retried automatically. Token values are never recorded, logged,
written to receipts or failure files, or printed to stdout.

## Request body

Both APIs send `generationConfig.responseFormat.text.mimeType` `APPLICATION_JSON`; the recorded
probe shows the Developer API rejecting `application/json`, and `APPLICATION_JSON` passing
validation. The `vertex_ai` body additionally carries
`generationConfig.thinkingConfig = {"thinkingBudget": 0}`: without it, hidden thought tokens
consume the bounded output and a bounded request returns `MAX_TOKENS` without JSON. The
transport accepts exactly that addition for `vertex_ai` and rejects it for `gemini_developer`,
so a body and its configured API cannot silently disagree.

`budget_policy` explicitly selects request and token limits. These are not a monetary cap;
thinking tokens, provider pricing and other account activity still matter. A requirement for
an enforced currency ceiling needs a separate, verified service budget contract before live
execution. Unknown or monetary-cap policy values are rejected. Configuration in this repository
does not supply live authorization or credentials.

Once the registered service inputs and authorization are resolved, the command takes whichever
of the two service files above is approved:

```sh
/usr/bin/python3 scripts/m3/gemini-run.py --config .local/m3-live/approved-config.json
```

The runner supports one attempt per run. It uses the fictional in-memory repository, verifies
exact citations through JudgmentService, leaves accepted heads/history unchanged and writes
an immutable proposed artifact and transport receipt to `.local/m3-live/<run-id>/result.json`.
The source case is synthetic even when `execution_mode` is `live_inference`. Semantic review
is marked pending; provider success does not establish factual correctness or analyst approval.
This command does not connect the workspace to Gemini or establish hosted persistence.

## Failure and recovery

The transport reserves an attempt in local SQLite before launching network work. Failures,
timeouts and invalid answers consume the attempt. The same ledger enforces the allowance across
restarts and concurrent instances; a changed configuration cannot silently increase the bound.
The transport permits up to ten explicitly configured attempts for other callers, but the
fictional runner requires exactly one. Retain the ledger for the approved run. Deleting it or
selecting a new run ID is an operator action, not automatic retry or recovery.

A networking subprocess enforces the deadline across DNS, TLS, upload, headers and body reading.
At expiry the parent kills and reaps it. HTTPS uses system trust verification and the one fixed
host of the configured API; the parent never names a destination. Credentials travel in a
request header, never a URL. The worker refuses redirects, compressed
responses, non-JSON responses, excess bytes and malformed JSON; provider errors are safe codes,
with no provider error body or stderr exposed. There are no model-request retries.

`failure.json` preserves the original attempt receipt after a failed run. A later spent-allowance
check does not overwrite it. If a process exits after the reservation but before a receipt,
the allowance remains consumed; investigate instead of rerunning automatically. A successful
restart validates the saved artifact and returns it without loading a key or invoking Gemini.
Artifacts and ledger are local, operator-owned files, not a distributed tamper-proof billing
system. Requests may be billable even if no judgment was saved.

Receipts whitelist response identifier, returned model version and numeric usage metadata
(including `thoughtsTokenCount` for `vertex_ai`), and record the selected API name as
`transport.api`, the configured service, limits, attempt, elapsed time and request-body digest.
Missing metadata stays null. Raw secret values and exception/provider error text are never
recorded.

## Verification

```sh
/usr/bin/python3 -m unittest discover -s tests -p test_gemini_transport.py -v
/usr/bin/python3 -m unittest discover -s tests -p test_transport_permission.py -v
/usr/bin/python3 -m unittest discover -s tests -p test_judgment.py -v
/usr/bin/python3 -m unittest discover -s tests/integration -p test_gemini_wire.py -v
```

Tests use explicitly synthetic subprocess responses and mocked HTTPS connections. They cover
both configured APIs: accepted/rejected configuration, the exact Vertex host, publisher path and
headers, the API-specific request body, a recorded-shape Vertex response, hard deadlines,
partial stdout, response bounds, redirect/error handling, safe secrets, atomic allowances,
restarts, failed-attempt preservation, proposal-only persistence and receipt validation.
`test_transport_permission.py` covers the real-case gate with a fake worker: the allowlist and
the refused non-allowlisted ids, a configuration that cannot carry a permission, the declared
case, absent/unsigned/withdrawn/revoked records refused before any attempt, and the unchanged
budgets for an authorized real case. No fixture is an actual Gemini run. The four TLS integration checks use actual loopback
sockets and ephemeral synthetic certificates, with a test-only connection substitution; they
need an interpreter with `cryptography` (the existing H1 lockfile, or the system interpreter
here) and make no external connection. The transport and offline tests remain stdlib-only.
See the [live work packet](../../../docs/work/m3-live-gemini/intent.md), the
[Vertex transport packet](../../../docs/work/vertex-transport/implementation.md) and the
[real-case permission packet](../../../docs/work/vertex-transport/real-case-permission.md).

Protocol references checked during implementation: Google's
[generateContent API](https://ai.google.dev/api/generate-content),
[API-key header guidance](https://ai.google.dev/gemini-api/docs/api-key) and
[thinking metadata](https://ai.google.dev/gemini-api/docs/thinking). Opaque thought signatures
may accompany the single answer text part; they are ignored as metadata and never become
evidence or authority. Function calls and other extra fields remain rejected. The Vertex AI
destination, header and thinking-budget evidence is the recorded probe table in the
[Vertex transport intent](../../../docs/work/vertex-transport/intent.md); this adapter is not
itself evidence that any hosted model is available.
