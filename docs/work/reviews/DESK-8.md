# DESK-8 review record

The runner's own branch `task/DESK-8` carries two review records of an executor turn that never ran (provider balance); they are not findings about this work. The rounds below are on the orchestrator seat's build on main.

## Round 1 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `2c1e7bd7`, 2026-10-18 02:45)

Recorded verbatim:

> # DESK-8 review, round 1: rework
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat). No edit, commit, network, model or cloud call was made.
>
> - Commit under review: `2c1e7bd7` (made directly on main).
> - Base named in the brief: `3276f9a2`. The commit's real parent is `f7ff14f3` (orchestrator live pointer, touches only `docs/work/current.json`). Scope was therefore taken against `f7ff14f3` too.
> - Where checks ran: a temporary worktree `/tmp/claude-1000/desk8-review` at `2c1e7bd7`, with the ignored baked view `.local/grid-snapshot/events/pedc-u2-2026-09-21.json` copied in (read-only). Interpreter `/usr/bin/python3` (3.14), node from PATH.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `python3 scripts/plan.py scope DESK-8 3276f9a2` | exit 1, lists `docs/work/current.json` only. That file comes from the orchestrator commit `f7ff14f3`, not from DESK-8 |
> | `python3 scripts/plan.py scope DESK-8 f7ff14f3` | `OK: all changed files inside DESK-8 allowed paths` |
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` (the brief's verify) | `Ran 103 tests` **OK (skipped=8)**. The 8 skips: 3 LiveServer (no FastAPI interpreter), 3 impact-record and 2 outlook-archive tests (those ignored inputs are not in this worktree). The two new DESK-8 tests ran and passed |
> | `/usr/bin/python3 -m unittest -v tests.test_grid_event.DeskLineOnTheRealRecord` | `Ran 4 tests` OK, including `test_the_card_states_the_two_readings_at_the_return_cutoff` and `test_the_card_says_when_the_two_readings_agree` |
> | `node --check src/grid/event.js` | clean (exit 0) |
> | `python3 scripts/plan.py check` | `OK: 120 tasks, 8 gates` |
> | `python3 scripts/repo.py check` | `PASS` (588 Markdown files, 3768 local links, bootstrap 1400 words) |
> | `node tests/fixtures/grid/event/render.mjs --root . --fixture <scratch dir with the real view + fixture flow.json>` | desk card `readings`: "At the return cutoff (15:55) the AI reader said challenges. The scripted case reading said supports. The two readings differ at the return cutoff. The difference is unadjudicated." |
> | Hand read of the view's `cutoffs` entry with `pair: "return"` | advisory V155556, `t` 2026-09-21T15:55:56. After-cutoff rows: `Gemini, recorded run 14 Oct 2026 (...)` label `challenges`. `case reading, scripted (probe-bundle.v5 composition)` label `supports`. The rendered sentence matches word for word |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite, temporary worktree) | `Ran 2574 tests` FAILED (errors=1, skipped=124). The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: "pypdf is not importable; unpack it at .local/pylib/". That ignored library is not in a fresh worktree, and DESK-8 touches no corpus file. Read as green for DESK-8 |
> | `/usr/bin/python3 -m unittest tests.test_grid_page` | `Ran 92 tests` OK (skipped=18); 14 skips say "no browser found" (no browser is linked in this worktree). The browser checks were skipped, which the brief allows |
>
> Cross-checks against the records: `docs/work/grid-desk/live-run-2026-10-14.md` row `return/t1` (07:55:56Z, that is 15:55:56 Manila) gives **challenges**. The evidence ledger line 40 grades the disagreement `unadjudicated` (script composes supports, Gemini composed challenges). The cold read section 5 is the stated motivation. The line takes no side.
>
> ## Checklist
>
> | # | Item | Result |
> |---|---|---|
> | 1 | Every acceptance item met by a check I ran | **Partly.** Acceptance 1 (the disagreement stated in the AI reader card, read from the baked cutoffs): the statement is met and checked; "with the receipts folded" is not met and the record does not mention it (F2). Acceptance 2 (repository words folded on the first screen): out of scope per the record; the deferral has no owning task (F1). Acceptance 3 (copy rules): met for the new line. Acceptance 4: kept assertions met (diff adds only); full suite green apart from one environment error; no bake input changed |
> | 2 | Only allowed paths changed | Met against the real parent `f7ff14f3`. `render.mjs` passes `plan.py scope` |
> | 3 | No frozen contract, acceptance text or test weakened | Met. The diff adds assertions only; the acceptance text in `tasks.json` is unchanged (only `note` and `state` changed) |
> | 4 | No new dependency, service, network or model call | Met |
> | 5 | Mode labels truthful | Met. "the AI reader" is the recorded Gemini run the card header already names (recorded 14 Oct 2026); "the scripted case reading" matches the source `case reading, scripted` |
> | 6 | Unknowns stay unknown, nothing invented | Met. The labels and the time come from the view; the fixed words are the brief's own; the test bans "resolved / wrong / right / correct"; a view without both sources shows nothing rather than a guess |
> | 7 | Copy rules | Met for the new line: four sentences of 9, 6, 9 and 4 words, no semicolon, no "stale". "The difference is unadjudicated" is a state, not a passive. The time has no zone, like every other `hhmm` on the page |
> | 8 | Packet records interpreter, commands, results, limits, next action | Partly. Interpreter, commands, limits and a scope note are present. The full-suite row says the result is "in the PROGRESS log row that follows", but that row cites only the verify's `Ran 103 tests` (F3). The next action names a task that does not exist (F1) |
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/product-gap-2026-10-17/desk-8.md` scope note; `tasks.json` DESK-8 `note` | The second output and acceptance 2 (event-page repository words folded) go to "COPY-1's successor", but no such task exists. COPY-1 covers only the models, register and outlooks pages. Once DESK-8 is set done, acceptance 2 has no owner and silently drops. The reason given is sound: DESK-7 pins three `details.records` folds, and the executor's attempt broke a kept assertion. But the record itself names a workable path (a new fold class, or a move into the three folds), so this is a deferral, not an impossibility | `tasks.json`: no task other than DESK-8 names the event page fold work or DESK-8. COPY-1's acceptance lists "models, register and outlooks pages" only | Register the successor task in `tasks.json` with the rule stated (event page, DESK-7 fold pins kept, the word-list test). Or record an orchestrator/owner decision that splits acceptance 2 out of DESK-8. Name it in the task record and the note before `done` |
> | important | `src/grid/event.js` `readingsAtReturn()`; acceptance 1 "with the receipts folded"; output 1 "records folded under 'Show the records'" | The line carries no receipts and no fold. The two readings' receipts (request id, probe digest, `case.json`) appear only in the timeline's cutoff box, after a click on the return notice. The card does not point there. The scope note covers output 2 only and says nothing about this clause, so it is unmet and unrecorded | Rendered desk report: `readings` is plain text, and the AI reader card has no `details` element. The receipts render only in `renderCutoff()` (event.js line 255) | Add the fold beside the line. A JS-rendered fold with its own class would leave the three static `details.records` pins in `event.html` and the `folds` dict alone; check this against `test_grid_event.py` lines 970 to 977. Or point the line to the timeline's return entry. Or record the clause as deferred with F1's successor. A test should pin what is chosen |
> | minor | `desk-8.md` section 3, row "full offline suite"; PROGRESS log row | The packet says the full-suite result is in the PROGRESS row that follows, but that row reports only the verify (`Ran 103 tests`). Acceptance 4 has no author evidence | `git show 2c1e7bd7 -- docs/work/PROGRESS.md` | Record a full-suite run (count, base commit, environment errors with their reason). My run: 2574 tests, 1 environment error (pypdf absent in a fresh worktree), 124 skipped |
> | minor | `desk-8.md` header / review base | The brief names base `3276f9a2`, but the parent is `f7ff14f3`. `plan.py scope` against `3276f9a2` exits 1 on the orchestrator's `current.json` | scope outputs above | Name the parent `f7ff14f3` as the scope base in the record |
> | note | `desk-8.md` section 3 | Packet reports `skipped=3`. A worktree without the ignored impact record and outlook archive shows `skipped=8` | verify run above | None needed: an environment difference, not a regression |
>
> ## Verdict
>
> **Rework.** The built line is right. It reads the view's own return cutoff and says challenges against supports. It calls the difference unadjudicated and takes no side. It falls back to agreement or to nothing as the brief says. Tests pin it on the real record and on a matched copy. Scope, plan, repo and node checks pass, and the full suite is green apart from one environment error. Two important gaps remain, and both are in the scope handling. Acceptance 2 is handed to a task that does not exist, so it would drop when DESK-8 closes. The deferral itself is reasonable on the DESK-7 pins. Acceptance 1's "receipts folded" clause is neither built nor recorded as deferred. The fix is small: register or decide the successor, then either add and pin the fold or record its deferral. Also record the full-suite run and the real parent. A rework that does this needs no change to the readings line.

## Round 2 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `12f09442`, 2026-10-18 02:55)

Recorded verbatim:

> # DESK-8 review, round 2: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat). No edit, commit, network, model or cloud call was made.
>
> - Commit under review: `12f09442` (the rework). Round 1 reviewed `2c1e7bd7`.
> - History note: `2c1e7bd7` was rebased onto `310a9067` (orchestrator product feature list) as `5445620d`. `git range-diff f7ff14f3..2c1e7bd7 310a9067..d68b1d8d` shows `2c1e7bd7 = 5445620d` (patch identical). The DESK-8 chain on this base is `5445620d`, `d68b1d8d`, `12f09442`.
> - Base: the record names `f7ff14f3`. The real parent of the DESK-8 chain is now `310a9067`. Scope was taken against both.
> - Where checks ran: temporary worktree `/tmp/claude-1000/desk8-review-r2` at `12f09442`, with the ignored baked view `.local/grid-snapshot/events/pedc-u2-2026-09-21.json` copied in (read-only). Interpreter `/usr/bin/python3`, node from PATH. The worktree was removed afterwards.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `git show 12f09442 --stat` | 8 files: PROGRESS.md, desk-8.md, reviews/DESK-8.md, tasks.json, event.html (+1), event.js (+17 -6), render.mjs (+3), test_grid_event.py (+13 -1) |
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` (the brief's verify) | `Ran 103 tests` **OK (skipped=8)** (same 8 environment skips as round 1) |
> | `/usr/bin/python3 -m unittest -v tests.test_grid_event.DeskLineOnTheRealRecord` | `Ran 4 tests` OK (the real view was present, so the new fold assertions ran) |
> | `python3 scripts/plan.py check` | `OK: 121 tasks, 8 gates` |
> | `python3 scripts/plan.py scope DESK-8 f7ff14f3` | exit 1, lists `docs/product/features-2026-10-18.html` only. That file comes from orchestrator commit `310a9067`, not from DESK-8 |
> | `python3 scripts/plan.py scope DESK-8 310a9067` | `OK: all changed files inside DESK-8 allowed paths` |
> | `python3 scripts/repo.py check` | `PASS` (589 Markdown files, 3770 local links, 5 skills, bootstrap 1400 words) |
> | `node --check src/grid/event.js` | clean (exit 0) |
> | `node tests/fixtures/grid/event/render.mjs --root . --fixture <real view.json + fixture flow.json>` | `readings`: "At the return cutoff (15:55) the AI reader said challenges. The scripted case reading said supports. The two readings differ at the return cutoff. The difference is unadjudicated." `readings_fold`: "Show the two readings' records". `readings_hidden`: false. `readings_records`: two `<li>`, the Gemini row (label challenges, rule, phrasings, tokens, `request 1ff0b7856a2b…`, `probe:6e4f9a819e8a1149…`) and the scripted row (label supports, rule, `tests/fixtures/pedc-u2-2026-09-21/case.json`). `folds`: the three DESK-7 folds still answer "Show the records" |
> | same harness on the fixture `view.json` | `readings` empty, `readings_hidden` true, `readings_records` empty |
> | `grep -c '<summary>Show the records</summary>' src/grid/event.html` | `3` (DESK-7's pin kept); line 978's `<details class="records">` count pin also unchanged |
> | `grep` of `src/grid/event.css` and `src/grid/grid.css` for the new class or a generic `details`/`summary` rule | none (only `.records …` and `.front summary`) |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite, temporary worktree) | `Ran 2574 tests` FAILED (errors=1, skipped=124). The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: "pypdf is not importable; unpack it at .local/pylib/". That is the same environment error as round 1 (ignored library absent in a fresh worktree). Read as green for DESK-8 |
>
> ## Checklist
>
> | # | Item | Result |
> |---|---|---|
> | 1 | Every acceptance item met by a check I ran, or handed on in the record | **Met.** Acceptance 1 (disagreement in the AI reader card, from the baked cutoffs, receipts folded): met, rendered and pinned; the fold holds both receipts. Output 1 literally says "folded under 'Show the records'"; the built summary is "Show the two readings' records" on purpose, to keep DESK-7's three-summary pin, and the record says so. Acceptance 2 and the word-list clause of output 3: handed to COPY-2 in the record's scope note, the tasks.json note and COPY-2's own outputs 1 and 2. Acceptance 3: met (item 7). Acceptance 4: assertions only added; full suite green bar one environment error; no bake input changed |
> | 2 | Only allowed paths changed | Met against the real parent `310a9067`. Against the recorded base `f7ff14f3` only the orchestrator file `docs/product/features-2026-10-18.html` appears (F1) |
> | 3 | No frozen contract, acceptance text or test weakened | Met. The one changed test line is a comment; the rest adds assertions. DESK-8's acceptance text in tasks.json is unchanged (only `note`) |
> | 4 | No new dependency, service, network or model call | Met |
> | 5 | Mode labels truthful | Met. The fold rows are the view's own `source` strings ("Gemini, recorded run 14 Oct 2026 …", "case reading, scripted …") |
> | 6 | Unknowns stay unknown, nothing invented | Met. Every fold field is read from the view's cutoffs judgments; a view without both readings shows no line and a hidden fold |
> | 7 | Copy rules | Met. Summary "Show the two readings' records": 5 words, imperative like DESK-7's summaries, no semicolon. Line unchanged from round 1: sentences of 9, 6, 9 and 4 words, no semicolon, no "stale". The repository words in the fold (request id, probe digest, file path) sit inside a fold, which the acceptance allows |
> | 8 | Packet records interpreter, commands, results, limits, next action | Mostly met. The suite run on the first commit (`Ran 2604 tests` OK, skipped=46) and the scope base are now recorded, and section 5 states the round-1 fixes. The record says the post-rework full-suite run is "in the row that follows"; at `12f09442` that row cites only the targeted tests (F2). The base and commit ids are pre-rebase (F1) |
>
> COPY-2 brief coherence: owned paths are DESK-7/DESK-8's event-page files plus its own packet, which the ownership rule allows through its dependencies. Dependencies DESK-7, ROUTES-1 and REG-2 are done; DESK-8 is in progress; `plan.py check` finds no cycle. The rule "a fold class of its own, never `details.records`" is stated in outputs and note. Acceptance keeps DESK-7's three folds and DESK-8's readings fold. Verify matches DESK-8's. "Finding 3" matches item 3 of the cold read's section 3. `copy-2.md` does not exist yet, as with COPY-1; it is an output.
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `src/grid/event.css`; `event.html` `details.readings-records` | The new fold gets no style. The three DESK-7 folds have a muted 11.5px summary, a pointer and a top margin from `.records`. The new class matches no rule, so its summary renders in browser defaults beside them. The harness cannot see this | `grep` of event.css and grid.css: only `.records`, `.records summary`, `.records[open] summary` and `.front summary` | Add `.readings-records` to the three `.records` selectors in `event.css` (an owned path). Can ride with COPY-2, which owns the same file and adds folds of its own class |
> | minor | `docs/work/product-gap-2026-10-17/desk-8.md` section 3 row "full offline suite"; PROGRESS line 661 | The record says the full-suite re-run after the review fix "is in the row that follows". At `12f09442` that row cites only `tests.test_grid_event tests.test_grid_event_drivers tests.test_plan`. The record makes a claim the tree does not yet back | `git show 12f09442 -- docs/work/PROGRESS.md` | Add the post-rework full-suite row before `done`. My run on `12f09442`: 2574 tests, 1 environment error (pypdf absent in a fresh worktree), 124 skipped |
> | note | `desk-8.md` header and section 3 | The record names base `f7ff14f3` and commit `2c1e7bd7`. The chain was rebased onto `310a9067`, so `2c1e7bd7` is off this history (now `5445620d`). Scope against `f7ff14f3` exits 1 on the orchestrator's `docs/product/features-2026-10-18.html` | scope and range-diff outputs above | Name `310a9067` as scope base and `5445620d` for the first commit, or add one line on the rebase |
> | note | `tests/test_grid_event.py` `DeskLineOnTheRealRecord` | The new `<summary>Show the records</summary>` count pin and the fold-receipt assertions sit in a class that skips without the ignored real view. The always-on DESK-7 pin (line 978, `<details class="records">` count) and the fixture's `readings_hidden` assertion still run everywhere | test code | None needed |
>
> ## Verdict
>
> **Accept.** The rework closes all four round-1 findings. The folding of the event page's repository words now has an owner, COPY-2, with a coherent brief. Its rule is a fold class of its own, with DESK-7's three folds kept. The two readings' receipts now fold beside the line under `details.readings-records`, "Show the two readings' records". I rendered both receipts inside the fold on the real view and saw the fold hidden on the fixture. `event.html` still holds exactly three "Show the records" summaries. The readings line is unchanged and still correct. The verify, plan, repo and node checks pass. Scope is clean against the real parent `310a9067`. The full suite is green apart from the known pypdf environment error. Two minor items remain, and neither blocks the verdict. The new fold has no CSS. The record's post-rework full-suite row is promised but not yet in the tree, and it should land before `done`. The base and commit ids in the record predate the rebase.
