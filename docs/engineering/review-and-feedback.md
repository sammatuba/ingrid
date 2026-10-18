# Review and feedback process

Adopted 2026-10-11; seats and launchers are in [seats.md](seats.md). This document sets the roles and rails for executing the
[grand execution plan](../work/milestones.md). It extends the
[lifecycle contract](lifecycle.md) and does not restate it. Nothing here is enforced by a
hook, slash command or automatic model switch; every rule is either a command a person types,
a test the suite runs, or a record a reviewer writes. The canonical stop conditions and
closing steps live in `docs/work/tasks.json` under `rails`, and `scripts/plan.py brief <ID>`
prints them verbatim into every worker hand-off.

## Roles

| Role | Default model | Does | Does not |
|---|---|---|---|
| Owner | Sam | Opens gates, decides cuts, performs human tasks, authorizes external effects | Delegate authorization to any model |
| Guardian | Claude Fable (sparingly) | Strategy decisions; final acceptance of reviews and escalations; keeps the feedback ledger; sole authority to change a frozen contract through a new intent | Implement tasks; open gates |
| Orchestrator | Claude Opus 5.5 in Claude Code | Picks critical-path tasks, generates briefs, dispatches the executor, runs scope and verification, requests review, records verdicts, keeps tasks.json and PROGRESS.md in sync | Implement tasks the executor can do; set `done` without a reviewer record; merge or push without the user |
| Reviewer and advisor | GPT Sol (`gpt-6.1-sol`) through Codex, read-only | Independent review of each task branch with the checklist; bounded advice on consequential decisions | Edit files; author what it reviews |
| Executor | DeepSeek V4.1 Flash through Claude Code on the DeepSeek endpoint | Implements one brief at a time inside allowed paths on `task/<ID>`; reports verification | Choose tasks; edit tasks.json beyond its own state; call services; push |

The guardian is strict by construction: it does not implement a task it will review, does not
mark its own work `done`, does not open gates, and does not edit a frozen contract in place.
Role names describe who normally does what. Model availability does not change the rules:
whichever model reviews must not have authored the change, and a review by the author is a
self-review and is labelled so.

## The rails

A worker receives `plan.py brief <ID>` and nothing else is assumed. The brief contains the
read-first files, the allowed paths, the acceptance list, the verify command, the frozen
contracts and the stop conditions. Going off the rails is defined as any stop condition
occurring; the correct response is to stop, write what happened in the packet, and hand back.
Working around a stop condition is the one behaviour that always fails review.

Commit authority: a task packet authorizes commits on its own branch `task/<ID>`. Push, merge,
rebase onto `feat/h1-api-persistence`, publication and any effect outside that branch need the
user. Save a generated brief under ignored `.local/briefs/<ID>.md` or pipe it to the worker;
a brief inside the repository tree fails `plan.py scope`.

Structural checks a worker and reviewer both run:

```sh
/usr/bin/python3 scripts/plan.py scope <ID>      # changed files inside allowed paths
/usr/bin/python3 scripts/plan.py check           # graph, states, review records
/usr/bin/python3 scripts/repo.py check           # links, routes, skills, bootstrap budget
/usr/bin/python3 -m unittest discover -s tests   # full offline suite
```

## Task states and who sets them

| Transition | Who | Requires |
|---|---|---|
| pending → in_progress | builder or executor | branch `task/<ID>`, PROGRESS.md row and log entry |
| in_progress → in_progress (self-review) | author | packet section labelled "self-review" with commands and results |
| in_progress → done | orchestrator, on the independent reviewer's `accept`; never the author | review record `docs/work/reviews/<ID>.md` with verdict `accept`; `plan.py check` passes |
| any → cut | owner | one-line reason in PROGRESS.md log |
| gate closed → open | owner | evidence reference in the input register and PROGRESS.md gate table |

`plan.py check` refuses `done` without `review.reviewer`, `review.verdict == accept` and an
existing `review.record`. The test suite runs the same check, so a merge with an unreviewed
`done` fails the suite.

## Review protocol

The reviewer reads, in order: the task brief, the intent it implements, the diff including
untracked files, the packet's verification section. Then the reviewer runs the verify command
and the structural checks, and inspects each acceptance item against the actual behaviour.

Checklist (each item answered yes, no, or not applicable with evidence):

1. Every acceptance item in the brief is met by an observable check that was actually run.
2. No file outside the allowed paths changed (`plan.py scope <ID> feat/h1-api-persistence` printed OK on the reviewed branch).
3. No frozen contract changed; no acceptance text changed; no test weakened or skipped.
4. No new dependency, service, credential, network call, model call or cloud effect beyond the packet.
5. Mode labels are truthful: synthetic fixture, stored run, replay, live inference.
6. Unknowns stayed unknown; no invented case facts, receipts or numbers.
7. The packet records interpreter, commands, results, unfinished items and next action.
8. Nothing in the change contradicts the blueprint, strategy refresh, working paper or domain invariants.

Findings use the lifecycle format: severity (`blocking`, `important`, `minor`), exact
location, failure mechanism, evidence, concrete correction, disposition. Questions without
evidence stay questions.

Verdicts:

- **accept**: all acceptance items met, no blocking or unresolved important findings. Task
  becomes `done`; the record names the commit reviewed.
- **rework**: at least one blocking or important finding. Task stays `in_progress`; the
  record lists the corrections; the author fixes and re-requests review on the same branch.
- **escalate**: the finding is in the intent, a frozen contract or the plan, not the work.
  Task stays `in_progress` with an escalation line in PROGRESS.md; the guardian opens an
  intent revision or a strategy question for the owner. No one edits the contract in place.

Record template: `docs/engineering/templates/review.md`, saved as `docs/work/reviews/<ID>.md`
with the reviewed commit hash and whether the review was independent.

## Feedback loop

Every `rework` or `escalate`, and every stop condition that fired, gets a dated entry in
[FEEDBACK.md](../work/FEEDBACK.md): pattern, task, impact, rule added and where. The guardian
reviews the ledger on each pass. A pattern seen twice becomes a rule: a stop
condition in `tasks.json`, a line in the relevant packet, or a sentence in `AGENTS.md`. A rule
that stops being needed is retired with a dated note, not deleted.

Feedback flows the other way too: a builder or executor who finds an intent ambiguous,
an acceptance check untestable, or an estimate wrong records that in the packet and the
ledger. That is a contribution, not a failure.

## Guardian pass

When asked, the guardian runs `plan.py ready` and `plan.py progress`, reads PROGRESS.md and
FEEDBACK.md, confirms gate states with the owner, and writes a three-line log entry: what
closed, what is blocked, what the chain needs next. Cuts are the owner's call.

**Amendment 2026-10-14 (guardian seat):** `done` is set by the orchestrator when it records an
independent reviewer's `accept` in `docs/work/reviews/<ID>.md`; the author of a change never sets
it; the owner may run `scripts/seats/accept.sh` directly. This replaces the earlier "guardian
only" wording in the transition table and matches the practice recorded since CORE-1.
