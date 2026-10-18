# Strategy -> intent -> implement -> audit/review

The lifecycle separates kinds of reasoning and their evidence. It does not require four
people, four models, separate chats, a GitHub issue or a framework service. Phase changes
do not expand authorization or erase user choices.

## Phase contracts

| Phase | Entry | Durable output | Exit evidence |
|---|---|---|---|
| Strategy | A direction decision, challenged premise or explicit brainstorm | Decision, examined assumptions/alternatives, trade-offs, unknowns and cheapest tests | A chosen direction or a bounded question that can be investigated |
| Intent | A chosen outcome or sufficiently clear request | Exact scope, contracts, ordered slices, acceptance checks, edge cases, dependencies and recovery | A builder can execute without inventing a material product decision |
| Implement | Ready intent or an already clear bounded fix | Code/docs, checks run, behavior evidence, deviations and unfinished items | Required acceptance criteria met, or a precise remaining blocker recorded |
| Audit/review | Actual changes and intended outcome | Evidenced findings, severity, disposition, verification and residual limits | Material findings resolved; result and limits communicated |

Strategy explores before committing; intent chooses implementation details; implementation
executes the contract; review attempts to find counterexamples. A failure of implementation
returns to implement. A deficient contract returns to intent. A failed product premise returns
to strategy. Do not quietly amend acceptance criteria merely to make a result pass.

## Models and context

The seats in use (Claude Opus 5.5 orchestrating, DeepSeek V4.1 Flash executing, GPT Sol
reviewing through Codex, Claude Fable as guardian) and their launchers are in
[seats.md](seats.md); the earlier [model workflow](model-workflow.md) is a historical record.
Use the user-selected model and effort. Consequential decisions may warrant a separate
review context, but no model change or delegation follows automatically.
These are configurable human preferences, not resolved provider model identifiers, cost
claims, enforced routing or a reason to halt when a named model is unavailable.

For a fresh session or model, pass the selected skill, relevant contract/intent, touched files,
verification and unresolved questions. Leave the full ideation transcript and historical
research out unless a live question requires them. Never describe self-review as independent.
Do not automatically launch a subagent or another CLI; delegation requires applicable user or
harness authorization. No external framework is responsible for enforcing this lifecycle.

## Work packets and readiness

For significant work, use `docs/work/<work-id>/` with `strategy.md` when a new decision was
needed, `intent.md`, `implementation.md`, `review.md`, and a small `work.json` manifest. Link
an existing strategy instead of manufacturing another strategy document. Use the
[templates](templates/README.md) only for the artifacts needed. A narrow fix may use one
record with concise intent/implementation/review sections and corresponding manifest links.

Each manifest contains `version`, `id`, `phase`, `status`, `base_commit`, `artifacts`,
`blockers` and `next_action`. Phase is `strategy`, `intent`, `implement` or `review`.
Status is `draft`, `ready`, `in_progress`, `awaiting_input` or `complete`. `artifacts` maps
phase names to existing **repository-relative** Markdown paths. `base_commit` is the starting
revision, not a freshness guarantee or an approval. `blockers` describes missing decisions,
data or prerequisites; do not infer their resolution from elapsed time.

`docs/work/current.json` contains `version`, `work_id`, `phase`, `status`, `references`,
`blockers` and `next_action`; references are repository-relative paths. It is the default
resume pointer only. Explicit task/work arguments override it. Validate files and compare the
actual working tree with the recorded baseline before resuming. Keep past work packets; do
not overwrite them with the latest task.

An intent marked ready permits work only within existing user authorization. New external
effects still need authority. Existing authorization does not need repeated confirmation.
If a required input is missing, finish independent work and record precisely what cannot yet
be completed. Do not fabricate case artifacts or turn every uncertainty into a user question.

## Review and closure

Reviewers read the intent, actual diff and relevant verification, then inspect affected paths.
Findings state severity, exact location, failure mechanism, evidence and a concrete correction.
Use `blocking` for unmet material acceptance/correctness or authority boundaries, `important`
for substantive maintainability/reliability problems, and `minor` for limited improvements.
Questions without evidence stay questions. Avoid preference-only findings.

Disposition each material finding: fixed and checked, or explicitly deferred with reason and
impact. Mark completion only when required work is complete; disclosed untested integrations
remain untested. A local review does not automatically approve/post to a PR. Record whether
the review was independent or self-review, and which changes/checks it actually covered.

Before ending or changing context, persist: current outcome, changed paths, verification,
unresolved items, next action and recommended phase. The human-facing reply can stay concise
because the work packet holds the execution evidence. Committing, pushing and publication are
separate actions governed by the user's request, not automatic lifecycle hooks.
