# How we work

This page is for the owner, the teammate and anyone with a clone who wants to change something.
[Start here](../START-HERE.md) explains the project. This page explains the path that a change
takes, from idea to done. Every special word is in the [glossary](../glossary.md). Where this page
and a dated record disagree, the record and the task file win. Tell the coordinator AI, and this
page gets a fix.

## One shared line

The branches `main` and `feat/h1-api-persistence` point to the same commit. GitHub and pull
requests use `main`. The helper scripts and `plan.py` use the other name until after the
submission. The coordinator AI pushes both after every merge.

## Where the truth lives

| Question | Read |
|---|---|
| What exists today | [status](../status.md) |
| Which tasks count as done, open or cut | `/usr/bin/python3 scripts/plan.py progress`, or the task table in [PROGRESS](../work/PROGRESS.md) |
| Which task you can take now | `/usr/bin/python3 scripts/plan.py ready` |
| Why a task counts as done | its review record, `docs/work/reviews/<ID>.md` |
| The commands and results behind a task | its task record under `docs/work/`. The brief names the file. |
| The order of the remaining work | [milestones](../work/milestones.md) |
| The decisions behind the product | [strategy refresh of 14 October](../work/strategy-refresh-2026-10-14/strategy.md), [foundation review](../work/foundation-review-2026-10-13/strategy.md), [blueprint](../product/definitive-blueprint-2026-10-04.md) |
| Lessons that earlier sessions learned the hard way | the gotchas list on the [AI helper roles page](seats.md) |

Two files hold a task's state: `docs/work/tasks.json` for the machine and `PROGRESS.md` for
people. The tests fail when they disagree.

## Set up your computer

```sh
git clone https://github.com/sammatuba/ingrid
cd ingrid
/usr/bin/python3 scripts/repo.py check                 # links, routes, word budgets, plain language
/usr/bin/python3 scripts/plan.py check                 # task graph, states, review records
/usr/bin/python3 -m unittest discover -s tests         # the offline tests
```

Use Python 3.11 or newer. We verified 3.14.4. Type the full path `/usr/bin/python3`. The short
name `python` does not work on the owner's computer.

The offline tests need no extra package.
More than a hundred tests skip when a browser, a local service copy or the company data is absent.
That is normal.

The second test suite talks to local copies of Firestore and the sign-in service. Run it with
`bash scripts/h1/test.sh` after the one-time setup in [scripts/h1](../../scripts/h1/README.md).
Everything that you generate goes under the ignored folder `.local/`.

## A change, from idea to done

1. Write the idea as a GitHub issue, or say it in a session.
2. The coordinator AI registers a task in `docs/work/tasks.json`.
3. The task gets an ID, the files it may change, acceptance checks and a verify command.
4. Make a branch and a work copy for the task. The commands are below.
5. Change only the files that the brief allows.
6. Run the verify command and the three checks above.
7. Write the commands and the results into the task record.
8. Commit on the task branch.
9. Edit `tasks.json`, the PROGRESS row and one log line in the same commit when the state changes.
10. Ask for a review. Do not merge your own work.

```sh
/usr/bin/python3 scripts/plan.py ready                 # pick one task
/usr/bin/python3 scripts/plan.py brief <ID>            # files to read, allowed files, checks, stop conditions
git worktree add -b task/<ID> .local/wt/<ID> feat/h1-api-persistence
```

The brief lists stop conditions. When one happens, stop. Write what happened in the task record
and hand the task back. A workaround for a stop condition always fails review.

## Reviews

Nothing merges on the author's word. The reviewer AI, GPT Sol, reads a task through
`bash scripts/seats/reviewer.sh <ID>`. It needs Codex credits, and the owner tops them up. A
person who did not write the change can review instead. A review by the author is a self-review,
and the record says so.

The coordinator AI copies the verdict into `docs/work/reviews/<ID>.md`. The task becomes done
only on an accept. The owner records the accept with `bash scripts/seats/accept.sh`, from the
shared work copy `.local/wt/integration`.

## Owner only

- Deploys. Type `bash scripts/deploy/deploy.sh` in a plain terminal. A line that starts with `!`
  fails there. Deploys are rare: one per batch of finished work, not one per task.
- Owner approvals, such as `GATE-5` for the public export.
- Cutting a task, pushing or merging the shared line.
- Anything that spends money or calls a live AI model outside a task's allowance.

## Issues and tasks

| Issue | Task | State |
|---|---|---|
| #67 fingerprint compare in the deploy script | HOST-5 | done |
| #68 cache classes for public replay data | PERF-1 | done |
| #69 one-step visitor case setup | PERF-2 | done |
| #70 event page in at most two requests | PERF-3 | done |
| #71 grid page draws in stages | PERF-4 | done |
| #72 hosted baseline and cold start | PERF-0, HOST-3 | in progress, pending |
| #73 PEDC return-cutoff disagreement | EVAL-8 | after submission |
| #74 signed permission in the transport | CORE-10 | after submission |
| #75 refresh README, status, pointer | the 14 October refresh | done |
| #37 to #47 milestone backlog | REL-4 reconciles them | pending |
| #41 GitHub Actions do not start | open. "No checks" on a pull request means the checks did not run. | open |

## Who does what

| Role | Who | Does |
|---|---|---|
| Owner | Sam | Approvals, cuts, deploys, permissions, the submission |
| Teammate | Ericka | The data foundation. Any task through the path above. |
| Strategy reviewer | Claude Fable, used rarely | Big decisions, escalations, the fixed rules |
| Coordinator AI | Claude Opus 5.5 in Claude Code | Picks tasks, writes briefs, runs checks, records verdicts, merges on the owner's word |
| Builder AI | DeepSeek V4.1 Flash through Claude Code | Builds one brief at a time on `task/<ID>` |
| Reviewer AI | GPT Sol through Codex, read-only | Independent review. Never the author. |

Launch commands, one-time setup and the gotchas list are on the
[AI helper roles page](seats.md).

**For Ericka.** Your BigQuery pipeline, labels, models and analysis are in the
[data foundation handoff](../work/data-foundation/HANDOFF.md). They still feed the numbers. Your
replay dashboard moved to [archive/dashboard](../../archive/dashboard/README.md) on
14 October, with its npm launcher. Nothing in it changed except the path. The hosted grid page in
`src/grid/` reused its structure: one state per region, a replay clock, plain explanations.

## What is left, in order

`plan.py ready` is the live list. This is the chain. Bold marks the owner's items.

1. PERF-0: record the cold start numbers from the four-cycle measurement and pass review.
2. DOC-1 and DOC-2: these pages, the glossary, the plain-language check and the explainer.
3. HOST-3: a walkthrough by someone new, with cold start and rollback evidence.
4. REL-4: the release file list and the submission checklist. Closes issues #37 to #47.
5. REL-5: the public export. **Owner:** open `GATE-5` first. It stays closed with nothing recorded.
6. REL-6: **the owner** records the video.
7. REL-7: **the owner** submits on the portal.
8. One deploy carries the plant map with 492 of 617 sites located.
9. After the submission: EVAL-8, CORE-10, the cleanup gap from PERF-2, and the move of the
   helper scripts from `feat/h1-api-persistence` to `main`.

Standing owner item: Codex credits before any review batch.

## Things that trip people up

- The short name `python` does not work on the owner's computer. Every command here says
  `/usr/bin/python3`.
- GitHub shows no checks on any commit. The checks did not run (#41). The evidence is the local
  test runs and the Cloud Build records in the task records.
- Some networks block `web.app`. Use the Cloud Run address or mobile data.
- In a plain terminal, a command must not start with `!`. That prefix belongs to the Claude Code
  prompt only.
- A task's state lives in two files, `tasks.json` and `PROGRESS.md`. Change both in one commit,
  or the tests fail on the next rebase.
- Current work sits in the work copy `.local/wt/integration` on `feat/h1-api-persistence`. Run
  `plan.py` from there.

## Known facts, not yet acted on

Each line is a future task. Do not fix one in passing.

- The deployed app never calls a model. The file `src/api/hosted.py` builds the app server
  without a judgment provider. The event page shows the recorded run. A live judgment on the site
  is a new plan note with a budget.
- The container image copies all of `src/`, including modules that the server never loads. A
  smaller image needs an image build to verify, so it waits for a deploy.
- The file `.codex/config.toml` pins `gpt-6-astra`. The reviewer launcher overrides it to
  `gpt-6.1-sol`.
- The CI workflow exists but never starts (#41). It also lacks `plan.py check`.
- The file `src/adapters/gemini/transport.py` keeps a `DeveloperAPITransport` alias for CORE-10.
- The branches `release/poc-2026-10-14`, `task/CORE-5`, `task/UI-3` and `task/UI-4` hold cut or
  replaced work. `task/UI-3` has three unpushed commits. Remove them when the owner says so.

## Never

- Publish anything outside this repository. No external pages, docs or decks.
- Commit private data, credentials, `build/`, or anything under `.local/`.
- Invent a number, a time, a result or a model run. Unknown stays unknown.
- Edit a fixed rule, an accepted review record, or `tests/test_grid_event.py`.
- Report a command that was not run or a result that was not observed.
