# H0 offline review core

Python 3.11+ stdlib application ports for the [H0 intent](../../docs/work/h0-review-case/intent.md).
The core imports no authentication/cloud/model SDK and has no execution port.
[H1](../../scripts/h1/README.md) supplies the local HTTP/persistence adapters;
[M3](../workspace/README.md) supplies the connected local workspace and proposed judgments.
The [synthetic tests](../../tests/test_review_case.py) demonstrate a complete case setup,
retain/revise/open-work reviews, receipt reads and proposal export.

## Public operations

Import `ActorContext`, `InMemoryRepository`, `ReviewError`, `make_record`, `reference`
and `validate_record` from `src.review`. `make_record` copies JSON input, normalizes
offset-bearing instants, retains supplied timezone/precision metadata and computes the
F0 canonical JSON digest under the separate `h0.v2` envelope. No clock is consulted.

| Port | Contract |
|---|---|
| `register_case(actor, record)` | Explicit synthetic namespace, typed entities/model fields and permitted actors; trusted reviewer required |
| `register(actor, record, source_bytes=...)` | SourceVersion, Passage or MappingRevision only; source bytes mandatory for source registration, including retries |
| `seed_assumption(actor, id, revision, recorded_at, payload, rationale)` | Explicit initial acceptance; the seed decision's `synthetic_initial` mirrors the case's provenance (true only on a synthetic case); payload contains case ID and reviewed mapping, no client-supplied acceptance decision |
| `build_snapshot(actor, case, audit_cutoff, recorded_at)` | Accepted head manifest excluding later recorded/reviewed decisions |
| `compile_task(actor, case, snapshot_ref, assumption_id, information_cutoff, recorded_at, passage_ids=None)` | Exact permitted context; optional passage-ID narrowing; structured compiled/blocked status |
| `prepare_task(actor, case, audit_cutoff, information_cutoff, recorded_at)` | One decision's preparation in one call (the additive `POST .../prepare` route, PERF-3): the heads, the snapshot and the task compiled for the state's single accepted assumption; the same records the two calls above write, and `PREPARE_ASSUMPTION_COUNT` (nothing written) when the state does not hold exactly one |
| `commit_review(actor, request)` | Atomic decision/outlook/accepted heads/history/impact/receipt; expected heads and exact request binding |
| `read`, `heads`, `history`, `receipt`, `draft_status` | Defensive projections with current access checks |
| `prepare_scenario(actor, case, idempotency_key, recorded_at)` | Exact old/new input delta after revise; immutable proposal revisions |
| `export_scenario(actor, case, proposal_ref)` | Current permitted proposal; pending outputs and uncomputed consequences |

`ActorContext` is a trusted server-side input, not authentication. Each call must receive
the actor's current case membership, source policies and review capability. Policy names
in evidence do not grant access. A future API must derive this context independently of
the request; tests use explicitly synthetic contexts. Revoked access denies old tasks,
receipts and proposals as well as current records. Read errors for denied/missing records
share the same safe code. Errors expose fixed `code` and `message` through `as_dict()`.

Review requests contain exactly `case_id`, `request_id`, `idempotency_key`, `task_ref`,
`snapshot_digest`, `expected_assumption_head`, `expected_outlook_head`, `disposition`,
`rationale`, `reviewed_at`, `recorded_at` and `new_value`. `new_value` is null except for
revise. Quantities are `{value: signed-decimal-string, quantity_kind: string, unit: string}`.
No actor/role field is accepted. Every disposition appends history; only revise/retain
advance the accepted outlook. Only revise advances the accepted assumption.

## The h0.v2 envelope

New writes use `schema_version: h0.v2`; `validate_record` accepts `h0.v1` as well and
validates a v1 record by the unchanged v1 rules, so stored records and the frozen
fixtures keep validating. Mixed-version references are allowed: a v2 record may name a
v1 dependency. The envelope's keys, identity and digests are the ones v1 fixed; only the
payload's own rules differ, in the three ways below.

**Real or synthetic.** Every record kind carries `synthetic` and `permission_ref`, and a
`h0.v2` payload must declare both: a payload that omits either is `INVALID_RECORD`, so an
exported record can never lack the pair. `synthetic: true` requires
`permission_ref: null`; `synthetic: false` requires a non-blank identifier present in the
permission registry, otherwise `PERMISSION_UNKNOWN`. A `h0.v1` record predates the pair,
and the v1 rules already fix every v1 record as synthetic, so its pair reads
`(True, None)`: a v1 record can never be real or cite a permission. The registry is the
set of `Permission identifier` values parsed by
`load_permissions(root)` from the files under `docs/work/permissions/` whose `Status:` line
is not the draft marker, so a drafted record is not a grant; the repository reads the
checkout's registry once and the validator takes it as an argument, so tests inject one.
The Case fixes the pair for the whole case and the repository refuses any record whose pair
differs from its case's (`CASE_PROVENANCE_MISMATCH`), while derived writes — snapshot,
compiled task, judgment, bundle, outlook, proposal, dependency impact and the seed decision —
copy the pair instead of the literal `True`; the seed decision's `synthetic_initial` label
mirrors that pair, so only a synthetic case's initial acceptance reads as synthetic. A
`JudgmentArtifact` or a `ProbeBundleArtifact` whose `execution_mode` is `synthetic_fixture` is
refused on a real case; `live_inference` is allowed for both.

**Typed availability basis.** A `SourceVersion` with a `known_at` carries
`availability_basis` as an object — `{"basis_kind", "basis_ref", "note"}` — where
`basis_kind` is one of `feed_logged_at` (a timestamp the delivering feed wrote),
`capture_logged_at` (our capture log), `archive_snapshot` (a dated archive) or `attested`
(a person attests first availability, named with the date in `basis_ref`), `basis_ref` is
non-blank and `note` is a possibly empty string. The v1 free-text string is accepted only
inside a `h0.v1` envelope; a v2 record carrying one is `INVALID_RECORD`. A basis records
where first availability was observed, never when: it does not change `known_at`, and
publication is still not availability.

**Judgment reference.** A `ReviewDecision` may name the judgment it relied on through the
optional typed `judgment_ref` (the API `ReviewBody` carries the same optional field; omitting
it and sending an explicit null are the same request, because the two spellings normalize to
one idempotency digest). The validator fixes the reference's shape; the repository resolves it
inside the review transaction — read during preparation and re-read under the commit lock —
and refuses a reference that does not resolve in the same tenant and case to a
`JudgmentArtifact` or a `ProbeBundleArtifact` of the decision's own task
(`JUDGMENT_TASK_MISMATCH`). The reference is recorded, never interpreted: it changes no
disposition, is part of the idempotency digest, and is exported and replayed with the
decision.

The additive `JudgmentArtifact` record and `judgment_input`, `save_judgment`, `workspace`
ports are documented in the [judgment boundary](../judgment/README.md). They do not alter
accepted assumptions. The workspace projection is actor-scoped and source-access checked.

## Immutable storage and bounded compilation

Records are stored as private canonical JSON strings. Identity is tenant/case/kind/id/revision.
Identical registration is idempotent; changed content conflicts. Caller mutations never
alter stored history. Revision registration order defines the latest dependency projection;
retrying an earlier revision cannot reset it. Snapshots contain authoritative revision refs.

Passage offsets count Unicode code points in the exact UTF-8-decoded text, including BOM,
CRLF and combining characters. Source-byte and canonical-record digests are separate.
Availability, publication, record and review times have separate meanings. Periods are
half-open; mixed date/instant or inverted periods fail. Source publication may be date-only.

The policy has two budgets: 32 passages and 32 dependency nodes. Passage refs are bound
and rechecked separately; traversal nodes comprise the case, snapshot assumption heads,
mapping and source lineage ancestors. Multiple spans in one source consume multiple passage
slots and one source node. Exactly 32 is allowed; exceeding either budget visibly truncates
and blocks acceptance until narrowed. Access filtering happens before public counts.
Task digests hash the normalized payload excluding `task_digest`; record digests hash the
envelope excluding `content_digest`. Original relationship definitions, accepted proposition,
typed value, model representation and reviewed mapping are included in the task context.

One-to-one mappings must preserve type; many-to-one mappings name an explicit modeled
aggregate and its members. Fan-out to multiple model fields is unresolved in this single-field
H0 contract. Copies declaring `copied_from` must retain the original lineage. This verifies
declared lineage; it does not detect undeclared copying or establish source independence.

Prepared review records are checked again under a single lock before all writes. Dependency
updates append impact records and mark affected drafts stale without editing accepted history.
Snapshots and proposals also preflight their entire write set. There is no disk durability,
multi-process transaction or production authentication guarantee in the reference adapter.
