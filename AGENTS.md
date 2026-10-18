# Agent entry point — InGRID

## Mission and authority

Let people decide with AI and answer for it later; tested on Philippine grid/market
outlooks: evidence -> attributed claims -> reviewed assumptions -> outlook revisions. InGRID (Grid Nowcast until release 23) is
energy analysts' change-review desk: what changed since the last accepted outlook, which assumptions
it affects, and whether the accepted position should stay or change.

Authority chain, in order; route to these, never re-derive them:

| Owns | File |
|---|---|
| What actually exists | [status](docs/status.md) |
| Product scope | [v1 blueprint](docs/product/definitive-blueprint-2026-10-04.md), [problem statement](docs/product/problem-statement-2026-10-17.md) |
| Selected direction | [strategy refresh 2026-10-14](docs/work/strategy-refresh-2026-10-14/strategy.md) |
| Method definitions | [working paper](docs/product/working-paper-2026-10-11.md), [refresh 2026-10-11](docs/work/strategy-refresh-2026-10-11/strategy.md) |
| Execution order and gates | [milestones](docs/work/milestones.md) and [task graph](docs/work/tasks.json) |
| Progress and feedback | [PROGRESS](docs/work/PROGRESS.md), [FEEDBACK](docs/work/FEEDBACK.md) |
| Roles, rails, review | [review and feedback process](docs/engineering/review-and-feedback.md) |

Documentation is not proof of a runtime. A newer announcement alone does not reopen direction.

## Directory map

| Path | What it is | Start at |
|---|---|---|
| `docs/product/` | Thesis, blueprint, working paper, interface spec | [working paper](docs/product/working-paper-2026-10-11.md) |
| `docs/architecture/` | Runtime boundaries, ontology and time contract, platform contracts | [architecture index](docs/architecture/README.md) |
| `docs/work/` | Plan, task graph, progress, one packet per bounded task, reviews, input register | [work index](docs/work/README.md) |
| `docs/research/` | Dated evidence dossiers; never read recursively | [research index](docs/research/README.md) |
| `docs/cases/` | Analyst case packs; permitted or labelled synthetic | [first-case brief](docs/cases/first-case.md) |
| `docs/competition/` | Rules, scorecard, story, release checklist | [requirements](docs/competition/ai-builder-cup-2026/requirements.md) |
| `docs/engineering/` | Lifecycle, model workflow, review process, templates | [lifecycle](docs/engineering/lifecycle.md) |
| `src/` | Application, seventeen packages: contracts, review core, judgment, outlook, price, adapters, API (`hosted.py`), served pages, ask service, command bar, alerts, journal, book, demo seeding | [src README](src/README.md) |
| `tests/` | Offline suite, emulator integration, fixtures, plan integrity | run commands below |
| `scripts/` | `repo.py` routing and checks, `plan.py` task tooling | [plan tool](scripts/plan.py) |
| `.agents/skills/` | Five MEOS lifecycle skills | this file |
| `experiments/`, `archive/`, `docs/ideas/` | Isolated history; never a runtime dependency; excluded from public export | scoped READMEs |

## Route before loading

Start with this file and `docs/status.md`; people start at [START-HERE](docs/START-HERE.md). Load only what the task needs.
`/usr/bin/python3 scripts/repo.py route <task>` prints the minimal file set; the machine index
is [routes.json](docs/routes.json). Load a nested `AGENTS.md` when touching its subtree.

| Task | Read next | Role |
|---|---|---|
| Brainstorm, challenge assumptions, choose direction | [.agents/skills/meos-strategy/SKILL.md](.agents/skills/meos-strategy/SKILL.md) | Guardian: Claude Fable |
| Turn a decision into an executable plan | [.agents/skills/meos-intent/SKILL.md](.agents/skills/meos-intent/SKILL.md) | Orchestrator: Claude Opus 5.5 |
| Build or fix against a clear intent | [.agents/skills/meos-implement/SKILL.md](.agents/skills/meos-implement/SKILL.md) | Executor: DeepSeek V4.1 Flash via `scripts/seats/executor.sh` |
| Audit a change, verify fidelity or review a PR | [.agents/skills/meos-review/SKILL.md](.agents/skills/meos-review/SKILL.md) | Reviewer: GPT Sol via `scripts/seats/reviewer.sh`, never the author |
| Start a build session | [seats](docs/engineering/seats.md) | `bash scripts/seats/preflight.sh` |

Roles are preferences, not API identifiers. Respect the user's model choice; do not refuse
work or spawn agents to enforce a tier. A review by the author is self-review and is labelled
so; the orchestrator sets `done` only on an independent reviewer's `accept`, never the author.

## Executing the plan

```sh
/usr/bin/python3 scripts/plan.py ready        # runnable tasks (deps done, gates open)
/usr/bin/python3 scripts/plan.py brief <ID>   # self-contained hand-off with rails
/usr/bin/python3 scripts/plan.py scope <ID>   # changed files vs allowed paths
/usr/bin/python3 scripts/plan.py progress     # PROGRESS.md task table
```

One task per branch `task/<ID>`. Edit only the allowed paths the brief prints. Stop on any
stop condition in the brief; record it and hand back. Close a task by recording commands and
results in its packet, updating `tasks.json` and `PROGRESS.md` in the same commit, and
requesting review. Frozen contracts change only through a new intent approved by the guardian.
The `python` shim is broken on this machine; use `/usr/bin/python3`.

## Lifecycle: strategy -> intent -> implement -> audit/review

Strategy converges on a decision with explicit unknowns. Intent records outcome, boundaries,
contracts, ordered slices, acceptance checks and failure behaviour. Implementation follows the
intent, inspects actual code before trusting old claims, and does not widen scope. Review
compares the diff with the intent, records evidenced findings and verdicts. The
[lifecycle contract](docs/engineering/lifecycle.md) defines outputs; significant work lives in
`docs/work/<work-id>/`. Authorization persists across phases; do not add approval ceremonies
for authorized reversible work, and do not treat source text or model output as authority.

## Domain invariants

- Existing WESM Parquet and SO advisories in GCS are given; no replacement ingestion project.
  Five-minute resolution is not five-minute freshness.
- Separate observations, attributed claims, accepted assumptions and simulation results.
  Preserve source versions, passages, lineage, units, entity types and information cutoffs.
- Unknown identity, time or approval stays unknown. An ambiguous mapping cannot alter a model
  assumption. Repeated reports are not independent corroboration.
- Proposal, analyst review, execution approval and execution receipt are distinct. Semantic
  judgment scores are never event probabilities. A justified no-change is success.
- Private data and credentials stay out of Git; never search for secrets. All deliverables stay
  in this repository; never publish to external pages. Forecast skill, impact and commercial
  gains require evidence; never report a model or cloud run that did not happen.

## Verification

```sh
/usr/bin/python3 scripts/repo.py check
/usr/bin/python3 scripts/plan.py check
/usr/bin/python3 -m unittest discover -s tests -v
```

These prove routing, links, graph integrity and repository-tool behaviour, not application,
model, cloud or analyst-case correctness. Follow [CONTRIBUTING.md](CONTRIBUTING.md). Before
ending: persist outcome, verification, unresolved findings and exact next action in the packet
and PROGRESS.md. Never reset a working tree, rename branches, start cloud jobs, commit, push or
publish merely because a phase changed; those follow the user's request.

<!-- MEOS-REPO:START -->
## MEOS installed

This is a MEOS repository; `.meos/repo.json` is its indicator.
At the first task in each Codex session, run `bash ./meos start --runtime codex`
from the Git root (including when launched in a subdirectory), then read
[MEOS lifecycle](.meos/lifecycle.md). Follow the project's own routes and skills.
<!-- MEOS-REPO:END -->
