# Documentation routes

People start at [START-HERE](START-HERE.md). AI agents start with [AGENTS.md](../AGENTS.md) and
[status](status.md). Load one route and its selected task record. The file `docs/routes.json` is
the machine index. Load historical research only when it bears on the task.
[Milestones](work/milestones.md) and the [task graph](work/tasks.json) own the execution order.

| Task | Route | Destination |
|---|---|---|
| Understand the project as a person | start / explain | [START-HERE](START-HERE.md), the [explainer](explainer/README.md), the [glossary](glossary.md) |
| Change something as a person | people | [How we work](engineering/how-we-work.md) |
| Explore or challenge a decision | strategy | Strategy skill and the retained product direction |
| Plan a bounded change | `intent` | Plan-note skill, architecture and the selected task record |
| Build or fix current work | implement | Build skill and the task record that the brief names |
| Review a change or a pull request | review / audit | Review skill and the selected plan note and evidence |
| Understand the full project thesis | thesis | [Working paper](product/working-paper-2026-10-11.md), then the earlier [thesis](product/project-thesis.md) |
| Start a fresh execution session | handoff | [START-HERE](START-HERE.md), then the [AI helper roles](engineering/seats.md) |
| Understand the selected product scope | product / blueprint | [V1 blueprint](product/definitive-blueprint-2026-10-04.md) |
| Understand runtime and domain boundaries | architecture | [Architecture index](architecture/README.md) |
| Orient to the project structure | map | [Repository map](repository-map.md) |
| Coordinate the remaining work | execution / milestones | [Milestones](work/milestones.md) and the [task graph](work/tasks.json) |
| Track or report progress | progress | [PROGRESS](work/PROGRESS.md), [FEEDBACK](work/FEEDBACK.md) |
| Review a task, or understand roles and rules | process | [Review and feedback process](engineering/review-and-feedback.md) |
| Start a build session on an AI helper | `seats` | [Roles and launchers](engineering/seats.md) |
| Identify missing inputs | inputs | [Input register](work/input-register.md) |
| Audit remote findings and pull requests | integration | [Inventory](work/branch-consolidation-2026-10-04/inventory.md), research decisions |
| Review modeling evidence | modeling | [Completed M0 review](work/bb1-modeling/review.md), [real input check](work/bb1-modeling/intake.md) |
| Resume regulatory work | regulatory | [Completed R0 review](work/bb2-regulatory/review.md), [parked export plan note](work/r0-f0-export/intent.md) (historical) |
| Prepare a permitted analyst case | case | [First-case intake](cases/first-case.md) |
| Read a dated finding | research | [Research index](research/README.md), then one dossier |
| Plan competition evidence | competition | [Requirements](competition/ai-builder-cup-2026/requirements.md), submission checklist |
| Build the interface or the story | demo | [Grid desk plan note](work/grid-desk/intent.md), [strategy refresh of 14 October](work/strategy-refresh-2026-10-14/strategy.md), story |
| Revisit parked ideas or old assets | ideas / decks / experiments | Scoped historical indexes. No active runtime dependency. |

Name the work folder when you have a bounded task:

```sh
/usr/bin/python3 scripts/repo.py route implement --work docs/work/performance
/usr/bin/python3 scripts/repo.py route review --work docs/work/hosting
```

The [default handoff](work/current.json) selects the performance task record. An explicit request
or `--work` overrides it. The [work index](work/README.md) explains ownership. A route prints
files. It gives no permission to run historical scripts, call cloud services or run models.

The earlier starters (F0, M0, R0, H0, H1) ended. Their records stay under `docs/work/` as dated
records.

The bootstrap budget (`AGENTS.md` plus `status.md`) rose from 1200 to 1400 words on
11 October 2026. The entry point can then carry the directory map, the authority chain and the
plan commands. The status page stays limited to what exists. The pages for people follow the
plain-language rules in `docs/routes.json`, and `scripts/repo.py check` enforces them.

The [layout migration map](engineering/migrations/platform-layout-2026-10-03.json) preserves
earlier path identities. Dated schedules and research stay in their original folders with
supersession notices. The current entry documents use the consolidated milestone plan.
