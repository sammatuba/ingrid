# BOOK-3 review record

## Round 1: rework

- Task: BOOK-3, the book page `/book`: accounts, contracts, load nodes with regions, the exposure heat by hour, the impact band per account from the chosen vintage, every figure with its record id and the synthetic label on every screen (lane BOOK, milestone M15).
- Branch: `task/BOOK-3`. Commit under review: `6ad60fd8` (the grant commit). Build commit `28c1d0ab`, merges `07d64b26` (origin/main `d5f172fe`) and `cbc02e35` (origin/main `d14946ab`).
- Base: `d14946ab` (origin/main, BOOK-3 depends on DOCK-2 for the `DOCK_PAGES` row). The diff under review is `d14946ab..6ad60fd8`.
- Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the executor). The owner's rule of 17 October allows this seat while the Codex reviewer has no credits.
- Worktree: `.local/wt/BOOK-3`, interpreter `/usr/bin/python3`, node and the ms-playwright Chromium through the worktree's `.local` links. No network, model or cloud call. The only file written in the tree is this record. Scratch scripts and screenshots stayed in the session scratch directory.
- Verdict: **rework**. The build is clean and every figure is proved against its record, but one major finding stands: the impact section states the materiality line above a table of band levels and never says what the line is compared against. Two minor findings and three advisory notes follow. The rework is small (one sentence and its test, one sentence rewritten, three unit tests).

### Commands and results

| Command | Result |
|---|---|
| `python3 scripts/plan.py brief BOOK-3` | Brief printed with the note: the orchestrator's grant of 2026-10-18 for the fifteenth `DOCK_PAGES` row. Four acceptance lines |
| `git diff d14946ab..HEAD` (read in full) | 17 files. New: `src/grid/book.{html,js,css}`, `scripts/book/bake_book.py`, four fixture vintage files, the two baked files, `tests/fixtures/grid/book/browser.mjs`, `tests/test_grid_book_page.py`, the packet. Modified: `scripts/book/vintages.py` (two rules, `series` and `issuer` read from the rule), `tests/test_grid_ask_page.py` (one `DOCK_PAGES` row, the count 14 to 15, one comment line), `tasks.json` (one state line), `PROGRESS.md` (the BOOK-3 row edited in place, one log line) |
| Shared files: `git diff --name-only d14946ab..HEAD` against `src/grid/index.html`, `src/api/hosted.py`, `src/api/__init__.py`, `scripts/grid/build_data.py`, `scripts/grid/build_all.py`, `scripts/deploy/`, `tests/test_hosting_stage.py`, `tests/test_cache_headers.py` | none changed. The only shared test file touched is the granted `DOCK_PAGES` row |
| `/usr/bin/python3 -m unittest tests.test_grid_book_page` (and `-v`) | `Ran 44 tests`, **OK**. The browser and fixture-server classes ran, none skipped |
| `/usr/bin/python3 -m unittest tests.test_grid_ask_page` | `Ran 88 tests`, **OK** |
| `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` | `Ran 3062 tests in 252.904s`, **`OK (skipped=62)`**. Equals the packet's count on the same base |
| `python3 scripts/plan.py scope BOOK-3 d14946ab` | `OK: all changed files inside BOOK-3 allowed paths`, exit 0 |
| `python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `python3 scripts/repo.py check` | `Checked 617 Markdown files, 3895 local links, 5 skills; bootstrap 1399 words.` **PASS** (before this record) |
| `git diff --check d14946ab..HEAD` | clean, exit 0 |
| `python3 scripts/book/bake_book.py --check` | `OK: 2 book page files reproduce`, exit 0 |
| `python3 scripts/book/vintages.py --check` | `OK: 8 vintage fixture files reproduce`, exit 0 |
| `python3 scripts/book/generate.py --check` | `unchanged`, digest `bfa951be…74a1`, exit 0 |
| `bake_book.py --out <scratch>` then `cmp` against both committed files | `book/index.json 14003`, `book/exposure.json 382032`, byte-equal |
| Scratch reconstruction, outside the test module: `index.book == load_book(FIXTURE)`; `exposure == exposure(book, Window(2026-10-19, 0, 24), "2026-10-18")`; per region `build_impact(book, load_vintage(V, id, archive digest), …) == record` and `record_digest(record) == content_digest`; every heat row's hours equal the first row's | all true. Luzon `4bc8e18fd693`, Visayas `4faaa648d420`, Mindanao `6b4822d72ef7`, totals as the packet's table; 24 hours on every heat row |
| New vintages: `OutlookArchive(tests/fixtures/book/vintages)` per record; `grep` for `.local` and `outlook-archive` in the four new fixture files and the two baked files | four records, every one `synthetic: true`; the new two carry `issuer "BOOK-3 fixture"`, series `CLUZ` and `CMIN`, source `scripts/book/vintages.py band rule`; no hit |
| `browser.mjs` at 390 and 1280 with `--shot`, plus viewport screenshots at 390 (scroll 0, 1700, 3000) | `ok: true`, overflow 0, 7 and 6 screens. The label line sits at 98–144 px (390) and 48–76 px (1280) on every screen and is topmost. Every table scrolls in its wrapper. Text read below |
| `copy_problems` (the test module's own checker) on page sentences outside the browser run | see finding 2 |
| After all runs: `OutlookArchive('.local/outlook-archive').verify()` | `outlooks 2, receipts 0, attributions 0, problems 0` |
| After all runs: `sha256sum -c` of the 30 files under `.local/outlook-archive` and `.local/price` against the snapshot taken before any run | identical |
| After all runs: `git status --short` | clean (ignored `__pycache__` only) |

### Acceptance lines

1. **Every figure on the page is read by a test from the baked record that holds it. The synthetic label is visible on every screen and in the page title.** Proved. The browser tests compare every cell of the six tables, the summary and the section sentences with the record field that holds each figure, at both widths. Each test also asserts the record holds the figure at the precision printed, so `toFixed` never rounds. `book.js` has no `Math`, `reduce`, product, quotient or accumulation. Totals, shade steps and hour runs are fields of the files. The heat class is `bk-shade-<h.shades[i]>`, read from `heat.rows`, never computed in the page. The title is `Grid Nowcast · Synthetic book`. The label line is the book record's own label, in one sticky block with the bar, in view and topmost at every scroll position. A `Synthetic.` line stands right before each table.
2. **The page has no route of its own until DOCK-5 stages it. The fixture server test proves it renders. No shared file changes here.** Proved. No `/book` or `book.html` in `src/api/__init__.py`, `hosted.py` or `stage_hosting.py`. No other page links `/book`. The harness alone serves it, under the application's CSP, and the browser run reports no console error, page error, failed request or bad answer. The `DOCK_PAGES` row is the granted change, and every other assertion in that file is kept.
3. **Copy rules 1 to 7. Every figure with its record as-of. Status words never stronger than the record's.** Not proved. Finding 1 (the materiality line implies a reading the record does not make) and finding 2 (one passive sentence the tests never see). Every rendered sentence passes the checker. Every figure row ends with its record and as-of.
4. **Every existing assertion in the touched test files is kept. The full offline suite passes. No live call.** Proved. `test_grid_ask_page.py`: one row added, `14` to `15`, nothing removed. Full suite 3062, OK. The builder is stdlib only, the harness binds loopback only.

### Findings

| # | Severity | Location | Acceptance line | Finding | Recommended change |
|---|---|---|---|---|---|
| 1 | major | `src/grid/book.js:145-152` (the impact sayings), `tests/test_grid_book_page.py:691-707`, `:736` | 3 (status words never stronger than the record's) | The page prints "The materiality line … is 1,000,000.00 PHP, at or above", then the basis, then the selection rule, then a table of band levels. The record's `materiality.rule` says the line applies to a change: the middle figure under a later vintage minus the one under an earlier vintage. The page omits the rule. Nothing on the page says what the line is compared against. A stranger reads the line directly above the Visayas middle total (1,358,277.35) and every High total, all above 1,000,000. The natural reading is "these are over the line". The impact records classify nothing. So the page's layout draws a verdict the record never makes. The orchestrator asked exactly this question ("what the materiality line means"). From the page text alone, the answer is not clear | Add one sentence between the line and the table. Either the record's own rule (its first sentence is 19 words, active, and passes `copy_problems`), or a fixed sentence such as "The line applies to a change between two vintages, not to the levels in this table." (passes `copy_problems`). If the record's wording is used, its last sentence contains "material" in the defining sense, so narrow `test_no_repository_word_or_stronger_status_word_on_the_page` (`:736`) to the verdict forms (`is material`, `not material`) the source test already uses. Extend `test_the_materiality_line_is_stated_above_the_impact_table` to pin the new sentence and its place (after the basis, before the table) |
| 2 | minor | `src/grid/book.js:199`, `tests/test_grid_book_page.py:427-431` | 3 (copy rules, active voice) | The fallback sentence "The book files could not be read from this build, so the page shows no figure." fails the repository's own passive check (`be read`; `copy_problems` returns `['passive be read']`). No test sees it: the element is hidden in the browser run, the `says` list skips hidden nodes, and the static-sentence test covers only the label and the footer. The no-vintage sentence at `:157` is also never checked, though it passes | Rewrite it in active voice, for example "The build has no book files, so the page shows no figure." Add a source test that runs `copy_problems` on the page's fixed fallback strings (the empty line and the no-vintage sentence with a sample region and date) |
| 3 | minor | `scripts/book/bake_book.py:120-130` (`choose`), `src/grid/book.js:157` | 1 and 3 (the stated selection rule, as shown on the page) | The page states a two-part rule: the newest regional vintage at or before the cutoff, else the newest system vintage. Only the first part runs on the fixture. No test exercises the `SYSTEM` fallback, the `VINTAGE_TIE` refusal or the `None` return that leads to the page's "No vintage prices …" sentence. The second half of a rule the page prints is unproved | Add unit tests on `choose` with a hand-built band list: a region with no regional vintage takes the newest system one; a region with neither returns `None, []`; two regional vintages issued at the same instant raise `VINTAGE_TIE`; a vintage issued after the cutoff is not considered |

### Advisory notes (no rework required)

- **A. Precision is a page constant.** `fig` prints with fixed digit counts (MWh 3, MW 3, PHP 2, contract MW 1, price 0). The tests pin these to this fixture through `round(x, n) == x`. A future record at a finer precision would round silently. DOCK-5 or BOOK-4 should state the precision in the files, or keep the test that checks it against the real bake.
- **B. "Reference price" is undefined on the page.** The method sentence names it, and the record's `method.reference` defines it (five sentences, all pass `copy_problems`). Showing it after the method sentence would close the gap for a stranger. Its mention of centavos is the record's and needs a look before it reaches a page.
- **C. Test names.** `test_the_fourteen_pages_carry_the_mount_and_load_no_new_script` and `test_the_dock_renders_on_all_fourteen_pages` now cover fifteen pages. Renaming is DOCK-2's owner's call, as the packet says.

### The executor's decisions

1. **One vintage per region, newest at or before the cutoff, else system.** Accepted. Every account is priced against its own region's band, which is the `band_basis` regional case. BOOK-2's Visayas vintages stay on the page, and the later `-v2` is used. Each region names its vintage id, record id and issue time in a sentence and in every row, which is what BOOK-2 note C asks. The fallback half needs its tests (finding 3).
2. **Exposure figures cite the book record id plus the cutoff.** Accepted. The exposure record has no digest, and the page does not invent one. The exposure is a function of the book and the cutoff (and the window, stated in the heat caption). BOOK-4 should either keep this cite or give the exposure record a digest under a stated rule, as the packet hands back.
3. **Low, Middle and High headers with one mapping sentence.** Accepted. `p50` is on the banned list. The sentence "The low, middle and high figures price the vintage's p10, middle and p90 levels" maps the headers to the record fields and passes the checker.
4. **The sticky label block (`.bk-top`).** Accepted. The bar wraps to two rows at 390 px, so a separate sticky line would slide under it. With the bar static inside one sticky block, the label is in view and topmost on all 7 screens at 390 and all 6 at 1280, overflow 0. It costs about 146 of 844 px at 390, which is acceptable for the label the acceptance requires.

### Read as a stranger (390 and 1280)

The label line under the bar says the book is invented, and it stays there on every screen. A stranger gets "this is invented" within seconds. Each table has one sentence that says what it shows, and its `Synthetic.` line says which record and cutoff it comes from. Every row ends with its record and as-of. At 390 the record columns sit to the right of each table's own scroll, which is fine. The weak point is the impact section: seven sentences before the table, and none says what the materiality line is for (finding 1). The record ids and vintage slugs (`book-demo-2026-10-19-cvis-v2`) are plumbing-like, but the brief asks for every figure with its record id, so they stay.

### Verdict and exact rework

**rework** for `6ad60fd8`. Do these on `task/BOOK-3`, then request round 2:

1. Finding 1: add the sentence that says the line applies to a change between two vintages, between the line and the impact table. Pin it in `test_the_materiality_line_is_stated_above_the_impact_table`. If the record's `materiality.rule` wording is used, narrow the `\bmaterial\b` assertion to the verdict forms.
2. Finding 2: rewrite the fallback sentence at `book.js:199` in active voice, and add a source test that checks the page's fixed fallback strings with `copy_problems`.
3. Finding 3: add the four `choose` unit tests.
4. Re-run `bake_book.py --check` (it must still reproduce, nothing in the files changes), `tests.test_grid_book_page`, `tests.test_grid_ask_page`, the full suite, `plan.py scope BOOK-3 d14946ab`, `plan.py check`, `repo.py check` and `git diff --check`. Record the results in the packet.

The orchestrator should not set BOOK-3 to `done` on this round.

## Round 2: accept

- Commit under review: `80019dc2` (one commit over `6ad60fd8`, the rework of round 1). Base `d14946ab` as before.
- Reviewer: the same Claude Opus 5.5 in-session subagent, read-only, independent of the author. The only file written is this record, and round 1 stays above unchanged.
- Verdict: **accept**. All three round-1 findings are closed, and so is advisory note B. Every acceptance line is now proved by a check I ran. No major finding stands. One new minor finding (R2-1) comes from note B's fix. It does not bear on an acceptance line as the brief states it.

### Commands and results

| Command | Result |
|---|---|
| `git diff 6ad60fd8..80019dc2` (read in full) | 3 files: `src/grid/book.js` (+10 −2), `tests/test_grid_book_page.py` (+74 −3), the packet (a "Rework round 1" section). `scripts/`, `tests/fixtures/` and every shared file unchanged (`git diff --quiet` on both trees) |
| `/usr/bin/python3 -m unittest tests.test_grid_book_page` (and `-v`) | `Ran 49 tests`, **OK**. The browser and server classes ran, none skipped |
| `/usr/bin/python3 -m unittest tests.test_grid_ask_page` | `Ran 88 tests`, **OK** |
| `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` | `Ran 3067 tests in 239.256s`, **`OK (skipped=62)`**. That is round 1's 3062 plus the five new tests |
| `python3 scripts/plan.py scope BOOK-3 d14946ab` | `OK: all changed files inside BOOK-3 allowed paths` |
| `python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `python3 scripts/repo.py check` | `Checked 618 Markdown files, 3896 local links, 5 skills; bootstrap 1399 words.` **PASS**. The count includes this untracked record, and the packet now links it |
| `git diff --check d14946ab..HEAD` | clean |
| `python3 scripts/book/bake_book.py --check` | `OK: 2 book page files reproduce`. The baked bytes did not change |
| `browser.mjs` at 390 and 1280 | `ok: true`, overflow 0, 7 and 6 screens, the label line in view and topmost on every one. The impact section's eleven sentences were read and checked with `copy_problems` (none flagged) |
| After all runs: `OutlookArchive('.local/outlook-archive').verify()` and `sha256sum -c` of the 30 files under `.local/outlook-archive` and `.local/price` | `outlooks 2, receipts 0, attributions 0, problems 0`. All 30 files are identical to the snapshot taken before round 1 |

### Round-1 findings

1. **Closed (major, the materiality line).** Right under the line the page now says "The line applies to a change between two vintages, not to the levels in this table." Next comes the record's own `materiality.rule`, then the basis, then the selection rule. The browser test pins that order at both widths. The verdict-word test removes the one quoted rule (asserted to appear exactly once) and refuses `is material`, `not material`, `are material` and `material change` everywhere else. The source test still refuses `is material` and `not material` in the code. Read as a stranger: the line, what it applies to, and why it is not a business limit come before any figure. The Visayas middle total above 1,000,000 no longer reads as "over the line".
2. **Closed (minor, the passive fallback).** `EMPTY_LINE` is now "The build has no book files, so the page shows no figure." The new `test_the_fixed_fallback_sentences_follow_the_copy_rules` reads it, the scope sentence and the `noVintage` template (filled with a sample region and date) out of the source. All three pass `copy_problems`. The test also pins that the empty element is set from `EMPTY_LINE`.
3. **Closed (minor, the untested selection branches).** `TheSelectionRule` has four tests on a hand-built band list: the newest regional pick, with a vintage issued at the date cutoff's close (16:00Z) left out, which matches `as_of_block`'s rule; the system fallback; `VINTAGE_TIE`; and `(None, [])` for a region with nothing known. `choose` itself did not change.

Advisory B is closed: `method.reference` now follows the method sentence, pinned by position. Advisories A and C are recorded in the packet as hand-backs, as recommended.

### New finding

| # | Severity | Location | Acceptance line | Finding | Recommended change |
|---|---|---|---|---|---|
| R2-1 | minor | `src/grid/book.js:168` (shows `method.reference`), the string `METHOD_REFERENCE` at `src/book/impact.py:125-130` | none as written (3 in spirit: plain meaning) | The page now shows "The reference price is the MW-weighted price of the contracts …, in centavos." The code means the price is in PHP/MWh, *rounded to* the centavo (`_cents`, two decimals, `impact.py:31-33`). A stranger who has just read the contracts table's "Price PHP/MWh" column can take "in centavos" as the unit, a hundred times off. No figure on the page is in centavos, and the reference price itself is not shown, so no figure is wrong. Round 1's note B flagged this word ("needs a look before it reaches a page"). The packet answered that it is "plain". It is plain, but it says something other than what the code does | Do not change the record string in this task, because it is inside every impact record's digest and moves the record ids. Either the page adds one fixed sentence after it, for example "The page states every price in PHP per MWh, kept to two decimals." Or the next task that touches `src/book/impact.py` (BOOK-4 or OUT-3) rewrites it as "…, in PHP per MWh, rounded to the centavo." and re-bakes. Not a condition of this accept |

### Verdict

**accept** for `80019dc2`. Every acceptance line is proved:
- Line 1: every figure is read from its record, and the label is on every screen and in the title.
- Line 2: the page has no route, it renders on the fixture server, and only the granted shared row changed.
- Line 3: the copy rules hold and the line's scope is stated, so no status word is stronger than the record's.
- Line 4: every existing assertion is kept, the full suite passes, and no live call was made.

The orchestrator may set BOOK-3 to `done` and must commit this record with it. The packet links `../reviews/BOOK-3.md`, so the branch's `repo.py check` needs this file committed. R2-1 goes to BOOK-4 or OUT-3 as a hand-back.
