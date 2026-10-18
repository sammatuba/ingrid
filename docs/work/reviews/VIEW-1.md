
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `f913eb3c`, 2026-10-17 23:48, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # VIEW-1 independent review: rework
> 
> I reviewed `task/VIEW-1` against `feat/product-gap-h` (commits `7a0f83d3` and `f913eb3c`). I did not write this change, and I edited no tracked file.
> 
> ## Commands I ran
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 scripts/plan.py scope VIEW-1 feat/product-gap-h` | `OK: all changed files inside VIEW-1 allowed paths` |
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_ask_page tests.test_hosting_stage` | `Ran 104 tests in 3.102s` · OK |
> | Full suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2498 tests in 200.983s` · OK (skipped=62). One stray `cvis-…: none (not transmittable)` line comes from an existing test. |
> | `build_all.py --force`, then `--check`, on the real snapshot with no views directory | Writer exit 0; all four checks exit 0; `failed None` |
> | The same pair with `--views` pointing at a copy of the six fixture plan sets (without `index.json`) | Writer exit 0; check exit 0; build_data contract `files 20, violations []` |
> | The panel harness (`ask-render.mjs`) on an early-cutoff plan set from `answer_question(..., '2026-10-15T00:00:00Z', fixture_backend())` | Finding 1 below |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.** Four of the five items are demonstrated: the panel on the five pages and `/ask` with three questions each, the six rules each with a test class, no live call, and the suite plus both `build_all --check` runs. The copy-rule item "status words never stronger than the record's" is not met on the insufficient path (finding 1). Its test, `CopyRules.test_the_status_word_is_never_stronger_than_the_record`, only looks at composed views.
> 2. **Changed files inside the allowed paths: yes.** `plan.py scope` printed OK. `src/judgment/view.py`, `scripts/grid/build_data.py`, `tests/fixtures/explainer/` and `tests/fixtures/grid/` are all in the brief's paths.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - `test_grid_catalog` changed `["composed","insufficient"]` to three `composed`. That expectation moved because the fixture was regenerated, as the brief granted. The insufficient envelope is still tested by `TheCutoffItems.test_the_insufficient_answer_fits_the_bakes_plan_set_contract`.
>    - `plan_receipt` in `test_grid_data` now builds the full receipt.
>    - The home page's late-file count moved from 10 to 11 for the new plan-set file.
> 4. **No new dependency, service, network or model call: yes.** `ask.js` makes one `fetch` of the baked file. The test pins that it contains no `EventSource`, `XMLHttpRequest`, `WebSocket` or `VIEW_LIVE`. No `VIEW_LIVE` is set anywhere.
> 5. **Mode labels truthful: no.** On the insufficient answer the panel says "Recorded plans, replayed." when no plan was rendered (finding 1).
> 6. **Unknowns stayed unknown: yes, mostly.** The fixture records are read from the synthetic event view, the fixture archive and the impact policy constants, all labelled synthetic. The hand-written unit statement in `build.py` is fixture text, labelled synthetic.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** See `view-1.md` §6, §9 and the post-commit table. One gap: §2 says the status line is derived from `execution_mode`, which is not true on the minimal-receipt path.
> 8. **Nothing contradicts the blueprint, paper or invariants: yes.**
>    - The task record (§8) asks the reviewer to judge its reading of "composes the view in place". I accept it: the composer fills `fields` from the records at bake time, BAKE-1's accepted contract bakes composed answers, the panel renders `fields` and never the plan, and plans with a numeral are refused.
>    - The brief says the composer's receipt has 15 fields. `compose()` builds 14 (`view.py:953-968`), and the task pins those 14. The brief's count is off by one; no field was dropped.
> 
> ## Findings
> 
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | **important** | `src/grid/ask.js:297-306` with `src/judgment/view.py:1001-1002` | When an outlook or price question is answered "insufficient" before a vintage exists (item G), the answer carries only a minimal receipt: `view_version`, `question`, `cutoff`, `missing`. It has no `execution_mode`, so `provenanceWord()` falls to its default and claims a recorded plan was replayed. No plan was rendered, and the bake is fixture plans. With nothing selected the line comes from `views[0]`, so a set that opens with such an answer mislabels the whole panel. This breaks "status words never stronger than the record's" and checklist item 5. | The harness on the early-cutoff set drew `insufficient \| Recorded plans, replayed. The site makes no live model call.` for both insufficient answers. The composed answer drew `Fixture plans, labelled synthetic…`. `test_an_insufficient_view_is_shown_in_words` (`tests/test_grid_ask_page.py:723`) never checks the status line. | Choose one: (a) `answer_question()` already has `backend`, so put `backend.name` and `execution_mode` into the minimal receipt and widen `VIEW_INSUFFICIENT_RECEIPT_KEYS` in `build_data.py:266`; or (b) when the mode is absent, make `provenanceWord` say something no stronger, such as "No plan was rendered for this answer. The site makes no live model call." Pin it in the harness test for both the selected and the unselected status line. |
> | minor | `src/judgment/view.py:1010` (`'; '.join(...)` in `answer_question`) with `ask.js:311` | When more than one mandatory part is missing, the reasons are joined with `; ` and drawn as `Insufficient: <missing>.`. That puts a semicolon in prose the panel shows, and only the brief's own sentence is exempt from the no-semicolon rule. | Code reading. The fixture misses only the outlook part, so no test reaches it. | Join with `. ` or render a list. |
> | minor | `ask.js:88` | The component title "What the operator reported" has four words. Copy rule 5 allows three, and §5 of the task record says the titles are "one to three words". | Source. | Use a title of three words or fewer, such as "Operator notices". |
> | minor | `tests/fixtures/grid/catalog/build.py:127` and `:139-141` | The task's own fixture record text contains semicolons (the impact label suffix and the unit statement). The panel draws both, and the unit statement is substituted into the exposure answer's text. `CopyRules` checks only literals in `ask.js`, so this passes. | Source. `test_the_filled_text_is_the_record_value` asserts that the unit statement is in the text. | Write the fixture statements without semicolons, then regenerate the bake. |
> 
> ## Verdict: **rework**
> 
> Item G's insufficient answer shows a status line claiming a recorded plan was replayed when none was rendered. That fails the acceptance item "status words never stronger than the record's", and no test covers it. The fix is small: one receipt field or one fallback line, plus a harness test. The three minor findings can go in the same round.
> 
> **Next action:** before release 10, the orchestrator should know that the real snapshot has no `views/` directory (Glob found nothing at `.local/grid-snapshot/views`). The no-views bake carried 13 contract files. The live site will therefore show "No recorded questions for this page yet" on every page until someone produces plan sets for the real page keys. The only builder for plan sets is the test fixture builder, and it is keyed to the synthetic event. The brief expects the page to say "fixture plans, labelled", so whoever bakes the release needs plan sets keyed to the real pages.
> 
> I left scratch directories in the ignored `.local/` of this worktree: `review-view1-without`, `review-view1-with` and `review-view1-views`. I did not write `docs/work/reviews/VIEW-1.md`. Recording the verdict is the orchestrator's job.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `0b845809`, 2026-10-18 00:14, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # VIEW-1 independent review, round 2: **accept**
> 
> I reviewed commit `0b845809` on `task/VIEW-1` against `feat/product-gap-h` at `dbdb0269`. The branch has five commits: the round-1 build, the runner's rework record, and the rework. I did not write this change and I edited no tracked file. My only scratch output is in `/tmp/view1-rev2` and `/tmp/view1-review-suite.log`.
> 
> ## Commands I ran
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_ask_page tests.test_hosting_stage` | `Ran 108 tests in 3.326s` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope VIEW-1 feat/product-gap-h` | `OK: all changed files inside VIEW-1 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2502 tests in 237.336s` · **OK (skipped=62)**, exit 0. The known stray `cvis-…: none (not transmittable)` line still prints. |
> | `-v tests.test_grid_ask_page` | 57 OK. Node is present (`~/.local/bin/node`), so all 7 tests in `ThePanelInTheHarness` actually executed `ask.js` here; none skipped. |
> | `build_all.py --force`, then `--check`, with no views directory | write 0, check 0, `violations: []`, no `views/` written |
> | The same pair with `--views` pointing at the six fixture plan sets (without `index.json`) | write 0, check 0, `violations: []`, 7 files under `views/` |
> | `scripts/plan.py check` / `scripts/repo.py check` | `OK: 117 tasks, 8 gates` / `PASS` (572 Markdown files, bootstrap 1400 words) |
> 
> Not run here:
> - **Browser run:** the browser pins (`test_grid_page`'s change from 10 to 11 late files, and the four `browser.mjs` plan-set servers) depend on the browser run in the task branch's own runner log. I did not check whether those classes ran or skipped in this sandbox.
> 
> ## Round-1 findings: all four fixed and pinned
> 
> 1. **Status line over an insufficient answer.**
>    - Fix: `ask.js:301-310` now falls back to "This answer carries no plan."
>    - Pins: `test_an_insufficient_answer_claims_no_plan` (`tests/test_grid_ask_page.py:688`) and the harness test at `:782`. The harness test checks the line with nothing selected, on both insufficient answers, and on the composed answer.
> 2. **Semicolon between missing records.**
>    - Fix: the reasons are joined with `'. '` (`view.py`, `answer_question`).
>    - Pin: `test_more_than_one_missing_record_leaves_no_semicolon` (`:524`).
> 3. **Four-word component title.**
>    - Fix: the title is now `Event timeline` (`ask.js:88`).
>    - Pin: `test_the_component_titles_are_three_words_or_fewer` (`:699`).
> 4. **Semicolons in the fixture's own statements.**
>    - Fix: `IMPACT_LABEL_SUFFIX` and `UNIT_STATEMENT` (`build.py:75-77`) no longer carry a semicolon.
>    - Pin: the test at `:706`. `build.py --check` reproduces the regenerated bake.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **Panel on the five pages and `/ask`:** I watched the harness render it with three questions each. Rule 1's tests show every field equals its record field and no plan carries a numeral.
>    - **The six rules:** each has its own test class.
>    - **No live call:** none is made. `ask.js` makes one `fetch` and carries no `VIEW_LIVE`.
>    - **Copy rules:** covered by `CopyRules`, with the gaps in minor findings 1 and 3.
>    - **Suite and `build_all --check`:** the suite is green, and I re-ran the check both with and without a views directory.
> 2. **Inside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - The expectations moved only where the regenerated output requires it: the catalog file count went from 16 to 20, the home set is now three composed answers, `plan_receipt` mirrors the full receipt, and the page's late files went from 10 to 11.
>    - The insufficient answer is still tested at `:516`.
> 4. **No new dependency, service, credential, network or model call: yes.**
> 5. **Mode labels truthful: yes for the panel; one overclaim in the `/ask` intro** (minor finding 2).
> 6. **Unknowns stayed unknown: yes, with one caveat.** Some of the impact record is written by hand in the fixture builder (minor finding 4). It is labelled synthetic.
> 7. **Packet records the interpreter, commands, results, unfinished items and next action: yes.** See §6, R1–R10, P4–P6 and §9.
> 8. **Nothing contradicts the blueprint, paper or invariants: yes.**
>    - I keep the round-1 reading of "composes in place".
>    - The brief says the receipt has 15 fields; the composer builds 14. The brief's count is wrong; no field was dropped.
> 
> ## Findings
> 
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `src/judgment/view.py:559`, drawn by `src/grid/ask.js:315` | The panel draws "Insufficient: no outlook vintage is issued at or before the view cutoff." This is passive voice in panel prose. `CopyRules` checks only literals inside `ask.js`, so it never sees this sentence. | The harness test at `:806` asserts this exact text. The test's own `PASSIVE` regex matches "is issued". | Reword it in the active voice, for example "the archive holds no outlook vintage at or before the view cutoff". Run `test_judgment_view` again. |
> | minor | `src/grid/ask.html:43`, pinned at `tests/test_grid_ask_page.py:598` | The `/ask` intro says "Every answer replays a recorded plan." The bake holds fixture plans, not recorded ones. An insufficient answer carries no plan at all. On a bake with no views, the sentence sits above "No recorded questions for this page yet". The status line just below it is truthful. | The panel's own line reads "Fixture plans, labelled synthetic." The brief says the page must say "fixture plans, labelled". | Write a sentence that claims no more than the receipt, for example "It replays the plans the bake carries and makes no live model call." Update the pin. Fix this before release 10. |
> | minor | `tests/test_grid_ask_page.py:632` | `CopyRules.authored()` skips any literal that contains `<` or `>`. Every sentence `ask.js` wraps in HTML therefore escapes the copy-rule test, for example `:175`, `:193` and `:205`. | Code reading. Read by hand, these sentences comply today. | Strip the tags before splitting into sentences instead of skipping the literal. |
> | minor | `tests/fixtures/grid/catalog/build.py:125-148` | The impact record's direction counts (0/0/0) and its unit statement are written in the builder. No baked page file carries them. The panel prints "0 changes compared, …" as figures. | `git grep` finds no impact record and no "portfolio" or "generator" fact anywhere in the grid fixtures. | Either build the record with `src/price/impact.py` over the synthetic portfolio, or draw "no change scored" when `changes_compared` is 0. It is labelled synthetic, so this does not block. |
> 
> Two smaller notes, not findings:
> - When nothing is selected and `views[0]` is insufficient, the status line reads "This answer carries no plan." with no answer on screen. The wording is odd but it claims less than the record, not more.
> - `SYNTHETIC_STATEMENT` still carries its semicolon through into the panel. It is record text and the packet records it.
> 
> **For the orchestrator, carried forward and not counted against this task:**
> - **Release 10:** the real snapshot has no `views/` directory, so a release bake draws "No recorded questions for this page yet" on every page. Someone needs to produce plan sets keyed to the real pages and staged with `--views` before release 10, or the panel will show nothing anywhere.
> 
> ## Verdict: **accept**
> 
> All five acceptance items are demonstrated by checks I ran here, and all four round-1 findings are fixed and pinned. The four new findings are minor, and minor finding 2 (the `/ask` intro sentence) should be fixed before release 10.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
