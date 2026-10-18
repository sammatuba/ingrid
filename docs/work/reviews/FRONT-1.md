
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `dbd9c708`, 2026-10-17 20:48, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> I'm returning FRONT-1 for **rework**. The front strip, the closing-brief heading and the chart labels are sound. The problem is the feed grouping: it merges every row of the same kind, grid and family in the 60-row window, however far apart in time. The brief asked for consecutive rows. I edited no files.
> 
> ## Commands run (on `task/FRONT-1` @ `dbd9c708`, base `feat/product-gap` @ `d716d4dd`)
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_hosting_stage tests.test_grid_page tests.test_grid_briefs` | `Ran 247 tests` **OK (skipped=11)** |
> | `/usr/bin/python3 scripts/plan.py scope FRONT-1 feat/product-gap` | `OK: all changed files inside FRONT-1 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2204 tests in 235.621s` **OK (skipped=58)**, the same counts as the record's §9 |
> | `/usr/bin/python3 scripts/repo.py check` | `PASS` (542 Markdown files, 3547 links) |
> | `scripts/grid/briefs.py --data .local/grid-snapshot/data --out /tmp/f1rev-briefs`, plus read-only probes that repeat `filterFeed` + `runsOf` | Measured the gaps inside each run (finding 1) |
> 
> **Browser tests ran here.** Contrary to the prompt, this environment has a working browser. `BrowserPage.test_the_findings_feed_draws_a_run_of_rows_as_one_row_in_the_browser ... ok` passed in this run. The 11 skips are 4 compression tests (they need the h1 venv) and 7 `RealBake` tests (no bake in the worktree). No browser class was skipped.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes for all four acceptance items, no for one Output.**
>    - The strip: `FrontStrip`, plus the browser layout at both widths.
>    - Copy rules: `CopyRules` and `repo.py check`.
>    - No inline script or style, and no new data file: checked.
>    - The staged-page rule: `test_hosting_stage` passes.
>    - Member text unchanged: members are drawn by the same `entry()`.
>    - Assertions kept and the suite green: yes.
>    - The one gap: the Output "groups **consecutive** rows" is not what the code does (finding 1).
> 2. **Allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** Existing assertions are only extended: two allow-lists gained the strip's routes and one class list gained three names.
> 4. **No new dependency, service or call: yes.** `localStorage` is a browser API, and it stores only the `nowcast-front-seen` flag.
> 5. **Truthful mode labels: yes.** The strip says "A replay", "a recorded run of 14 October 2026" and "no live model call", which is the brief's text word for word.
> 6. **Unknowns stay unknown: yes.** The dates come from the brief. "Operator notice of 21 September 2026" matches the PEDC finding at `2026-09-21T13:39:37`. Chapter 6 is `01-why.md` (built explainer `id="ch-6" data-source="01-why.md"`), and `explain.js:19` reads `#ch-<n>`.
> 7. **The packet records commands and next action: yes, but §3 misstates the rule** (part of finding 1).
> 8. **No contradiction with strategy or invariants: yes, except the grouping.** The strategy's "about sixty near-identical rows" means bursts of repeats. Merging episodes hours or days apart works against that aim.
> 
> I also checked by reading:
> - The panel's click handler (`briefs.js:214-233`) never calls `preventDefault` on a `<summary>`, so the native disclosure expands. No test opens a run.
> - `renderChart` uses the full axis (`times = D.t`, `grid.js:296`), and `setTime` calls `render()`, so the chart subtitle follows the clock.
> - Hosting's catch-all rewrite to Cloud Run (`scripts/deploy/firebase.json:44`) serves `/event/pedc-u2-2026-09-21`.
> 
> ## Findings
> 
> **1. important | `src/grid/briefs.js:118` (`runsOf`), with the rule text at `briefs.js:47-54` and `docs/work/product-gap-2026-10-17/front-1.md:62-64`**
> - **Mechanism:** `runsOf` groups every row of a key across the whole 60-row window. The stated limit, "no other row of that key drawn between them", is always true for rows of one key, so nothing ever splits a run. The span text then reads as one continuous episode when it is not.
> - **Evidence:** I composed the findings from the snapshot and replayed the rule over 1,863 views (clock times and chips):
>   - 4,363 of 6,706 multi-row runs have a gap of more than 60 minutes between members.
>   - At the default 13:40 "all" view: CLUZ "below the replay's own p10" draws as "06:30 to 12:00 · 17 findings", with gaps up to 85 minutes. Link congestion draws as 3 findings over 08:30–11:30, with a 145-minute gap.
>   - Messages chip at 22 Sep 12:00: CVIS "Marked operator message" draws as "21 Sep 13:39 to 22 Sep 08:32 · 7 findings" (gap of 977 minutes). This folds the PEDC message's only "Review impact →" link behind the disclosure.
>   - Messages chip late on 29 Sep: CMIN "Back online" draws as "21 Sep 07:22 to 29 Sep 16:35 · 3 findings".
> - **Correction:** add a real break condition and state it. For example, end a run when the gap to the previous member is longer than a stated bound, or when another row of the same kind and grid falls between them. The brief's own example run (CVIS cap, 13:05–13:35) has a 15-minute gap, so the bound must allow it. Then:
>   - Restate the rule in the comment and in record §3.
>   - Re-measure the browser pin `[2, 2, 17, 17, 16]` and the record's "10 rows at 13:40". The page fixture's runs all have 5-minute gaps, so the pin will likely hold.
>   - Add a gapped fixture case to `panel-harness.mjs` so a run that crosses the bound shows as two rows.
> 
> **2. minor | `src/grid/briefs.js:139`**
> - **Mechanism:** a run can fold a row that carries a review link.
> - **Evidence:** as in finding 1, the PEDC message folds inside a run of 7.
> - **Correction:** consider drawing any finding with a `review` link as its own row.
> 
> **3. minor | `src/grid/index.html:256`**
> - **Mechanism:** the `<summary>` is the whole three-sentence `<h2>` (about 40 words). Folded, it is still several lines on a 390 px phone, not the "one line" the brief asks for.
> - **Correction:** make the summary "Grid Nowcast is a review desk." and move the other two sentences inside the `<details>`, or record the departure from the brief.
> 
> **4. minor | `src/grid/briefs.js:204`**
> - **Mechanism:** `drawFeed` rewrites `innerHTML` on every `setClock`, so a run the reader opened folds again on the next tick while the clock plays.
> - **Correction:** keep the open state by run key, or note the behaviour in the record.
> 
> **5. minor | `tests/test_grid_page.py:448`**
> - **Mechanism:** no test pins the nine-day title "21 to 29 Sept 2026", the different-month branch of `spanWords`, or the subtitle on that axis. Only record row 7, run on the ignored snapshot, shows the title.
> - **Correction:** add a node render pin over a fixture with two or more days, or accept the record row as the evidence.
> 
> ## Verdict: **rework**
> 
> Finding 1 is important: the grouping departs from the brief's "consecutive rows" Output. On the real data it merges findings up to eight days apart into one run whose span reads as a single episode, and it hides the PEDC review link behind a run in the messages view. The fix is limited to `runsOf`, its rule text and its pins, so the next round can be short.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `843ac5ea`, 2026-10-17 21:18, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> The suite is still running. I'll write the verdict once its result arrives.
> 
> # FRONT-1 independent review: rework
> 
> I reviewed `task/FRONT-1` @ `843ac5ea` against `feat/product-gap` @ `73a9fc44`, the current merge base. I edited no files.
> 
> The product work holds. The front strip, the closing-brief heading, the chart title and subtitle, and the feed grouping all meet the brief, and the first review's five findings are fixed. The branch still fails because the full offline suite is red on this tree, from a stale row in `docs/work/PROGRESS.md`.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_hosting_stage tests.test_grid_page tests.test_grid_briefs` (the brief's verify command) | `Ran 250 tests in 24.059s` **OK (skipped=11)**. The browser-guarded classes skip by design here. |
> | `/usr/bin/python3 scripts/plan.py scope FRONT-1 feat/product-gap` | `OK: all changed files inside FRONT-1 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 2291 tests in 223.871s` **FAILED (failures=1, skipped=62)**. The failure is `test_plan.PlanTests.test_progress_record_matches_task_states`: `'pending' != 'done' : DESK-6 state differs between PROGRESS.md and tasks.json` |
> | `/usr/bin/python3 -m unittest tests.test_plan` | `Ran 8 tests` **FAILED (failures=1)**, the same assertion |
> | `/usr/bin/python3 scripts/repo.py check` | `Checked 548 Markdown files, 3585 local links …` **PASS** |
> | Python comparison of PROGRESS rows with `tasks.json` states, at the base and at HEAD | base `feat/product-gap`: no mismatch. HEAD: `[('DESK-6', 'pending', 'done')]` |
> | `git blame` on `PROGRESS.md:149` | the `| DESK-6 | pending |` row comes from this branch's own commit `436c71e9` |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.**
>    - **Front strip: met.** It is the first block of `<main>` and the `front` grid area at all three widths. Its sentences match `docs/explainer/01-why.md:37-44`, and the built explainer confirms that file is chapter 6 (`id="ch-6" data-source="01-why.md"`). The status line is the brief's text word for word. `FrontStrip` pins all of this.
>    - **Copy rules: met.** `CopyRules` checks the strip: every sentence under 20 words, no semicolon, no "stale".
>    - **No inline script or style, no new data file, staged-page rule: met.** `test_hosting_stage` passes.
>    - **Grouping changes no finding's text: met.** Each member is still drawn by the same `entry()` function.
>    - **Full offline suite passes: not met.** It fails on HEAD (finding 1).
> 2. **Allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - Existing assertions are only extended: two route allow-lists and one CSS class list.
>    - The staged-page loop keeps its `assertIn` for every other reference.
> 4. **No new dependency, service or call: yes.** The fold stores one `localStorage` flag (`nowcast-front-seen`). A browser that refuses storage keeps the strip open.
> 5. **Truthful mode labels: yes.** The strip says "A replay of 21 September 2026", "a recorded run of 14 October 2026" and "no live model call". This matches `strategy.md:34,59`. The test pins that "live model" appears only in that denial.
> 6. **Unknowns stay unknown: yes.** The dates and the chapter-6 words come from the records. The `/explain#ch-6` anchor is the one `src/grid/explain.js:19` reads.
> 7. **The packet records commands, results and next action: partly.** The record is thorough, but every suite figure in it (2203, 2204, 2207, all OK) was measured on the old base `d716d4dd`. It does not record the move to `73a9fc44`, and on that base the suite is red.
> 8. **No contradiction with blueprint, strategy or invariants: yes.**
>    - The first review's finding 1 is properly fixed. `RUN_GAP = 30`, a row of another family for the same kind and grid breaks a run, and a review row stands alone.
>    - The panel harness exercises these cases with rows added in memory (far, near and interrupted runs, the review row, a reopened run).
> 
> ## Findings
> 
> **1. blocking | `docs/work/PROGRESS.md:149` (also lines 148 and 150, and the log entries at the end of the file)**
> - **Mechanism:** commit `436c71e9` added a `| DESK-6 | pending |` row below the base's `| DESK-6 | done |` row (line 147). `test_plan` keeps the last row for each task id, so the file now says DESK-6 is `pending` while `tasks.json` says `done`. The full suite fails, so acceptance item 4 is not met on the reviewed commit.
>   - The same commit added a second FRONT-1 status row (line 150, `in_progress`) instead of editing the existing `pending` row (line 148).
>   - It also added two near-identical "FRONT-1 implemented" log entries.
> - **Evidence:** the full suite reads `FAILED (failures=1, skipped=62)` with the DESK-6 assertion. The base comparison shows no mismatch, HEAD shows `('DESK-6','pending','done')`, and blame points to `436c71e9`.
> - **Correction:**
>   - Delete the `| DESK-6 | pending |` row.
>   - Edit the FRONT-1 row at line 148 to `in_progress` and remove the duplicate at line 150.
>   - Drop the duplicated first log entry.
>   - Record the base drift `d716d4dd → 73a9fc44` in `front-1.md`.
>   - Re-run the full suite on this base and quote the count measured there. The 2207 figure is out of date.
> 
> **2. minor | `src/grid/briefs.js` (`openRuns` / `reopenRuns`)**
> - **Mechanism:** the open state is kept by run key (kind, grid and family) alone. Two separate runs with the same key in one window (for example two Luzon p10 runs) both open after a redraw when the reader opened only one. A run the reader opened also stays open after the clock moves to a different episode with the same key.
> - **Evidence:** read from the code. `reopenRuns` opens every `.b-group` whose `data-run` value is in the set.
> - **Correction:** include the run's newest stamp in the identity, or note the behaviour in record §3.
> 
> **3. minor | `src/grid/index.html:69-71`**
> - **Mechanism:** all three steps link to the same `/event/pedc-u2-2026-09-21`. The brief fixes that URL only for step 1. Steps 2 and 3 name things the visitor does on that page, so this is acceptable, but the record should say so.
> - **Correction:** none required. Optionally point steps 2 and 3 at anchors on the event page in a later task. No anchors are added here, because that page is out of scope.
> 
> Two departures from the brief are recorded and acceptable, so neither is a finding. The grouping is in `briefs.js`, not `grid.js`, because `briefs.js` is where the feed rows are drawn. Chapter 6 is `01-why.md`, not `06-work.md`, because the theory-first reorder renumbered the chapters.
> 
> ## Verdict: **rework**
> 
> The branch adds a stale `DESK-6 | pending` row to `PROGRESS.md`, so `test_plan` fails and "the full offline suite passes" is not demonstrated on `843ac5ea`; the product work holds, and the fix is one file inside the allowed paths plus a re-measured suite count in the packet.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Round 3 — 2026-10-17 21:40, Claude Opus 5.5 in-session reviewer (read-only, independent; run by the orchestrator after the runner's two rounds ended with the orchestrator's own PROGRESS slip as the only open important finding)

Range reviewed: 73a9fc44..ae1978ad (fix/FRONT-1). The reviewer's output, verbatim:

### Reviewer line

Claude Opus 5.5, an independent reviewer working read-only in an in-session subagent seat. I did not write this change. I edited no files and ran no git write command. The worktree is `.local/wt/merge-main` at `ae1978adfe6a095624f35b87e454d6b409464f6e`. `git status` showed only `?? .local` before and after my runs.

### Commands run

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_plan` | `Ran 8 tests` **OK** |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates`, exit 0 |
| `grep -n DESK-6 docs/work/PROGRESS.md` | One status row only, `\| DESK-6 \| done \| ... accept`, at line 147. No `pending` row is left. |
| Brief verify: `/usr/bin/python3 -m unittest tests.test_hosting_stage tests.test_grid_page tests.test_grid_briefs` | `Ran 250 tests in 22.032s` **OK (skipped=4)**. With `-v`, all 4 skips are `test_grid_page.Compression`, which needs the container image or the h1 venv. The node and browser classes executed. |
| Full offline suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2291 tests in 221.038s` **OK (skipped=46)**, exit 0 |
| `/usr/bin/python3 scripts/repo.py check` | **PASS** (548 Markdown files, 3585 local links, 5 skills, bootstrap 1400 words) |
| `scripts/plan.py scope FRONT-1 --base 73a9fc44` | This form is not supported. The script passes `--base` to `git diff` as a revision ("invalid option: --base...HEAD"). |
| `scripts/plan.py scope FRONT-1 73a9fc44` (positional base, the script's own usage) | Exit 1. The only path listed is `.local`, an untracked directory in this merge worktree that is not part of the range. No committed file is listed. |
| `plan.py brief FRONT-1` allowed paths compared with `git diff --name-only 73a9fc44..ae1978ad` | All 15 changed files are on the allowed list. `src/grid/briefs.js`, `src/grid/briefs.css` and `tests/fixtures/grid/` come from the dependency closure. The coordination files are `tasks.json`, `PROGRESS.md` and `reviews/FRONT-1.md`. |
| `git diff 73a9fc44..ae1978ad -- tests/ \| grep '^-[^-]'` | 5 removed lines. Each one is a line that was extended in place: the harness's JSON report gained keys, the stylesheet class tuple gained `.b-group/.b-rows/.b-open`, and the `SITE_ROUTES` skip gained `or reference in FRONT_STRIP_ROUTES`. No assertion was dropped or weakened. |
| A Python scan of the strip's text in `src/grid/index.html` | Every sentence is 18 words or fewer. No `;`, no "stale", no `style=`, no `<script`. The `index.html` diff has no inline handler. |

### Findings

**1. none: the round-2 important finding is closed.** In `docs/work/PROGRESS.md:147` the stale `| DESK-6 | pending |` row that the rebase re-added is gone. Only the `done/accept` row is left, `tests.test_plan` passes, and `plan.py check` is OK. The full suite is now green on this exact tree (2291 tests, skipped=46). That count agrees with the orchestrator's "OK (skipped=46)", but I measured it myself. Correction: none.

**2. minor (still open from round 2, does not block), `src/grid/briefs.js:119` (`keyOf`) and `:237` (`reopenRuns`).** A run's identity is kind, grid and family only. If the reader opens one run, every redrawn run with the same key is reopened, including a later, separate run of that key after a gap break. Evidence: `data-run="${esc(run.key)}"`, where `run.key = keyOf(f)`, and `reopenRuns` opens every `.b-group` whose key matches. The cost is only extra open disclosures. No text changes and no finding is hidden. Correction (optional, later task): add the run's oldest stamp to `data-run`.

**3. minor, `docs/work/PROGRESS.md:603-604`.** Two nearly identical "FRONT-1 implemented on `task/FRONT-1` from `d716d4dd`" log rows were added. The second differs only in the full-suite figure and the `repo.py` counts. The log is append-only and `test_plan` reads the status table, not the log, so nothing fails. Correction: none required. The orchestrator may mark the first row as superseded in a later log row.

**4. none: the acceptance items check out against the diff.**
- **Front strip.** `index.html:56-75` puts `<section class="front card">` as the first child of `<main class="desk">`. `grid.css` makes `front` the first grid area at all three widths, so it is the first block on a phone. The heading is "Grid Nowcast is a review desk.", followed by two sentences on what it does. There are three numbered steps linking to `/event/pedc-u2-2026-09-21`, then "How the desk works" linking to `/explain#ch-6`, and "Read the paper" linking to `/paper`. The status line is word for word: "A replay of 21 September 2026. The AI reading is a recorded run of 14 October 2026. The site makes no live model call." Nothing claims more than "recorded run". The fold is `grid.js:473`, `foldFront`: it stores one `localStorage` flag in a try/catch, and the strip stays open if storage is refused.
- **Feed grouping.** `briefs.js:135`, `runsOf`, groups consecutive rows of the same kind, grid and family. A run breaks on a gap over 30 minutes, on another family's row for the same kind and grid, and around any row with a review link. A run row names the span and the count, and its members are the unchanged `entry()` output inside a native `<details>`. The count line still counts findings (`shown.length` / `kept`), not rows.
- **Closing brief and chart.** The closing brief heading is `Closing brief, ${hhmm(briefing.t)}`. The grid name moves to the as-of line. The chart title at `grid.js:388` names the axis span through `spanWords`. The subtitle names the clock's day and time.
- **Test pins.** The staged-index href pin admits and requires the event page, the explainer anchor and `/paper`. The briefs tests pin the heading, and executed node cases cover the runs, the gaps, a review row standing alone and the reopen behaviour.
- **Departures.** Two departures were recorded in round 2: the grouping is in `briefs.js`, not `grid.js`, and chapter 6 is now `01-why.md`. Both are reasonable, and both files are inside the allowed paths.

Correction: none.

**5. none (tooling note), `scripts/plan.py` `scope` takes its base as a positional argument.** The `--base` form in my instructions is not supported. With the positional form, the only path flagged is the untracked `.local` in this merge worktree, which is an environment artifact and not part of the change. Correction: none for this task.

### Verdict: accept

The one finding that blocked round 2 is closed on this tree. The stale DESK-6 pending row is gone, and I ran `tests.test_plan` (OK), `plan.py check` (OK), the brief's verify command (250 tests, OK, with the 4 skips being the venv-only compression tests) and the full offline suite (2291 tests, OK, skipped=46) myself. The product work meets the brief. The front strip is the first block of `<main>` and uses chapter 6's words, the three steps and the exact status line, within the copy rules and with no inline script or style. The feed grouping rearranges rows without changing any finding's text and keeps the count's meaning. The closing brief and the chart title now say what they show. Every changed file is inside FRONT-1's allowed paths, and no existing test assertion was removed. The two minors left (run identity on reopen, and a duplicated log row) are cosmetic and can wait for a later task.
