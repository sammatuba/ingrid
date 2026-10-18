# Estate inventory, main @ 6a30dfd (2026-10-16)

Companion to [strategy.md](strategy.md). Built this session by reading the repository; nothing was changed.
`git status --porcelain` was empty before and after. Counts come from `docs/work/tasks.json` parsed with
`/usr/bin/python3`, `plan.py ready` and `plan.py progress`.

## 1. Task graph

79 tasks, four states. Header says `updated 2026-10-15`, branch `feat/h1-api-persistence`.

| Lane | done | in_progress | pending | cut | total |
|---|---|---|---|---|---|
| CORE | 8 | – | 1 (CORE-10) | 1 (CORE-5) | 10 |
| EVAL | 6 | – | 1 (EVAL-8) | 1 (EVAL-7) | 8 |
| UI | 2 | – | – | 4 (UI-3 to 6) | 6 |
| NUM | 2 | – | – | 2 (NUM-2, 3) | 4 |
| HOST | 5 | – | 1 (HOST-3) | – | 6 |
| CLEF | 1 | – | – | 2 | 3 |
| REL | 3 | – | 4 (REL-4 to 7) | – | 7 |
| POST | – | – | 4 | – | 4 |
| DATA, SYNC | 2 | – | – | – | 2 |
| GRID | 3 | – | – | – | 3 |
| PERF | 6 | – | – | – | 6 |
| DOC | – | 4 (DOC-1 to 4) | – | – | 4 |
| EXPL | 2 | – | – | – | 2 |
| CORP | 6 | – | – | – | 6 |
| ATG | 8 | – | – | – | 8 |
| **Total** | **54** | **4** | **11** | **10** | **79** |

All 54 done tasks carry an `accept` from GPT Astra or GPT Sol with a record under `docs/work/reviews/`.
No human analyst reviewed any task.

Gates: GATE-1, 2, 3 open; GATE-4, 6, 7, 8 closed (nothing waits on them); **GATE-5 closed**, blocking
REL-5 and so REL-7.

Ready now (`plan.py ready`): HOST-3, POST-3, EVAL-8, CORE-10. Open frontier of 15: HOST-3 → REL-4 →
REL-5 (GATE-5) → REL-7; REL-6; POST-1 to 4 (POST-4 depends on cut NUM-3, so it can never be ready);
EVAL-8; CORE-10; DOC-1 to 4 chained, reviewer-accepted, no owner accept.

## 2. Authority files versus the graph

| File | Disagreement |
|---|---|
| `docs/work/milestones.md` ("Updated 2026-10-14") | says 63 tasks; CORP and ATG pending; GATE-8 open; PERF-0, PERF-5, EXPL-1, EXPL-2, REL-3 open. M9 and M10 absent from its table |
| `docs/work/current.json` | work `performance`, next action from PERF-0 (done) |
| `docs/status.md` ("Updated 2026-10-15") | PERF-0 in review; DOC pending; "next deploy raises that to 492" while 00014-pzz is live |
| packet `work.json` files | several phases out of date (performance `implement/in_progress`, probe-bundle `intent/ready`, hosting `intent/ready`) |

## 3. Source tree (`src/`, 100 files)

| Module | Purpose |
|---|---|
| `src/review/` | h0.v1/v2 records, repository, cutoff pairing, storage; stdlib |
| `src/judgment/` | probe bundle: render, 14-row composer plus `render_refused`, receipt; System One port with fixture backend |
| `src/api/` | local app factory; `hosted.py` with demo and hosted modes, anonymous judges, Firestore |
| `src/adapters/gemini/` | generateContent contract; opt-in Developer/Vertex transport; the only socket in `src/` is `worker.py` |
| `src/adapters/systemone/` | Gemini structured-output emulation, HTTP client, isolated run |
| `src/adapters/corpus/` | acquisition, text layers, ontology-constrained extraction with citation check, claim store (memory, sqlite; BigQuery DDL under `scripts/corpus/bq`) |
| `src/adapters/bigquery/whatif.py` | AI.FORECAST SQL builder, no client |
| `src/adapters/firestore/`, `identity/` | emulator store; Firebase token verification |
| `src/adapters/wesm/` | bounded readers over exported advisories and register |
| `src/contracts/`, `modeling/`, `regulatory/` | F0 contracts; M0 harness; R0 segmentation, grammars, amendment lineage |
| `src/demo/`, `src/grid/`, `src/workspace/` | PEDC seed per judge; public pages (grid, event, explain, catalog, assets, map, briefs); `/desk` |

Transport refusals: `LiveConfig` accepts only `permitted_case == 'synthetic-case'`
(`src/adapters/gemini/transport.py`); a non-zero Vertex thinking budget is refused; `scripts/corpus/extract.py`
lifts the permitted-case check by subclass (what CORE-10 replaces). The deployed app makes no model call.

## 4. Tests and scripts

38 test files, 1,473 `def test_` methods (not run this session). Skips without environment: node (nine
grid and explainer files), a browser binary, the Firestore emulator, FastAPI, the real data build.

`scripts/`: `repo.py` (routing, links, plain-language check), `plan.py` (task graph), `seats/` (roles,
overnight runner), `deploy/`, `data/` (BigQuery pipeline and SQL), `h1/`, `release/` (export audit),
`grid/` (data build, Gemini phrasing command), `corpus/` (fetch, extract, upload, BigQuery), `perf/`, `clef/`,
`m3/`, `probe/`, `eval/`, `docs/`, `research/`.

## 5. Documentation estate

41 folders under `docs/work/` before this one: 29 marked complete in their `work.json` or by their tasks; open or stale
ones are `docs-for-people` (DOC-1 to 4), `hosting` (HOST-3), `vertex-transport` (CORE-10), `whatif`
(NUM-2, 3 cut), `data-foundation` (no tasks), `r0-f0-export` (no task), `foundation-review-2026-10-13`
("in progress"). Product: blueprint v1, working paper, project thesis, strategy, interface spec.
Architecture: decision system v1, ontology profile v1, building blocks, platform contracts. Research: 26
dated dossiers (01 to 16, 21 to 30). Cases: `pedc-u2-2026-09-21` (full), `reserve-market` (ERC action of 14
October 2026, synthetic rows), `visayas-2026-09` (skeleton). Ideas: two parked concepts and the ten-idea
historical portfolio. `experiments/` and `archive/` are history, not runtime.

## 6. Corpus register

34 entries: 4 families, 30 documents, all PEMC PDFs from the owner's `compendium-2026-04-01.zip`
(19,787,429 bytes) under the ignored `.local/corpus/`. Every document has a text layer; first availability
unknown for all, upper bound 2026-04-01. No ERC, DOE or IEMOP bytes, no amendment circulars. Web fetches
2026-10-15: four HTTP 200 (PEMC library, IEMOP advisory shell, DOE issuances, PEMC mirror of ERC issuances),
one 403 (ERC, Cloudflare challenge). The Billing and Settlement Manual, Issue 16.0, is row 10.

## 7. Git

971 commits on `main` (first 2026-10-03, last 2026-10-16); `main` equals `origin/main`; no stashes. 30
local branches, each a worktree; 24 on `origin`. Same commit as main: the two overnight branches,
`feat/h1-api-persistence`, every ATG, CORP, DOC, EXPL and PERF-0 task branch. Ahead of main: `task/HOST-3`
(+2), `task/CORE-5` (+9, holds the recorded live gemini-3.8-flash bundle run; task cut),
`release/poc-2026-10-14` (+21), `task/UI-3` (+21, cut), `task/UI-4` (+45, cut), `origin/docs/current-state-75`
(+6, remote only).

## 8. GitHub issues

91 issues. #7 to #51: the M1 to M6 epics of 2026-10-04, M1 and M2 closed, M3 to M6 largely superseded by
`tasks.json`. #67 to #75: the 10-13 performance and correctness set, three closed. #78 to #91: the
2026-10-16 grounding epic (#78, #79), the use-case standard (#80 and #81, byte-duplicates; #81 carries
the cross-stakeholder extension), UC-01 (#82, #84), UC-02 (#83, #85 to #88), UC-03 (#89), the Ask the Grid
benchmark (#90) and the conceptual roadmap (#91). All fourteen open, no comments, no labels.
