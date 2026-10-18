# First-screen changes after the second cold read: review record

Orchestrator commits on main (no task packet): the desk assistant's empty line links to the ask page; the event desk's rule code folds. Review by Claude Opus 5.5 in-session subagent, read-only, independent; commit `62d0f3db`, 2026-10-18 07:35. Recorded verbatim:

> # First-screen changes review: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author.
>
> Commit: 62d0f3db (62d0f3dbf40700595f0b2ca92ea6d27e034a6224). Base: 5880fa82.
> Scope: `git diff 5880fa82 62d0f3db` touches 5 files (8 insertions, 3 deletions): `src/grid/ask.js`, `src/grid/event.html`, `src/grid/event.css`, `tests/test_grid_ask_page.py`, `docs/work/PROGRESS.md`. These are orchestrator commits outside any task's allowed paths, so `plan.py scope` does not apply and was not run.
>
> Checks ran in a separate temporary worktree, `/tmp/claude-1000/r18-review` at 62d0f3db. The ignored `.local/grid-snapshot/events/pedc-u2-2026-09-21.json` was copied in so the real-record event class could run. The worktree was removed afterwards.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_ask_page tests.test_grid_event tests.test_grid_event_drivers tests.test_hosting_stage` | OK. Ran 212, skipped 8. The skips: 3 `LiveServer` tests need FastAPI/uvicorn. 5 tests need the runtime impact record or the outlook archive under `.local/`, which this review did not copy (the brief asked only for the PEDC event). None of the 8 is the PEDC event class. |
> | `python3 scripts/plan.py check` | exit 0, `OK: 121 tasks, 8 gates` |
> | `python3 scripts/repo.py check` | exit 0, `Checked 594 Markdown files, 3789 local links, 5 skills; bootstrap 1400 words. PASS` |
> | `node --check src/grid/ask.js` | exit 0 |
> | `plan.py scope` | Not applicable: these are orchestrator commits outside any task's paths. |
>
> ## Findings
>
> | # | Area | Finding | Severity |
> |---|---|---|---|
> | 1 | Assertions | The diff removes one assertion line: the old empty-panel `assertEqual` in `tests/test_grid_ask_page.py:779`. It comes back as an exact-equality pin on the new HTML (the same strength, a moved pin). No other test line changed. DESK-7's pins are unchanged: `tests/test_grid_event.py:978-982` and `:1438` (the folds dict and exactly 3 `<summary>Show the records</summary>`), and `tests/test_grid_event_drivers.py:254`. All pass. | none |
> | 2 | Plain language | The added sentence "The desk assistant's recorded questions are on the ask page." has 9 words, is active/declarative and has no semicolon. The lead fragment "No recorded questions for this page yet." was already there, with a full stop added. | none |
> | 3 | Link target | `/ask` is a served route. It is in the route set at `tests/test_hosting_stage.py:69` and is classified in `tests/test_cache_headers.py:400,550,961,971` (REVALIDATE_CACHE). `ask.html` is staged (`test_hosting_stage.py:238`). The rule that the home page has no `/ask` nav href (`:243`) checks the staged `index.html` only, and the runtime-injected link in `ask.js` does not affect it. The test passes. | none |
> | 4 | Fold summary collision | The new summary text is "Show the rule that fired", so it does not match `<summary>Show the records</summary>`. `src/grid/event.html` still has exactly 3 of those. The harness folds report still gives the three DESK-7 keys. `event.js:160` still sets `#dl-rule` text by id, so moving it into the `details` element changes no lookup. | none |
> | 5 | Empty state | When the view has no judgment (`event.js:133-141`, `!j`), `#dl-rule` is cleared, but the new `details.rule-records` fold is still shown. The reader gets a "Show the rule that fired" summary that opens to nothing. The sibling `#dl-readings-fold` avoids this with `hidden`. Suggested follow-up: give the fold an id and set `hidden` in the `!j` branch. This is cosmetic, and no-judgment events show "No judgment is recorded for this event." just above it. | minor, non-blocking |
> | 6 | CSS | The three `.rule-records` rules are scoped to the new class and do not touch existing selectors. | none |
> | 7 | Record | The PROGRESS.md row is a new orchestrator row, not a second row for a task id, so the last-row-wins rule does not apply. `plan.py check` passes. | none |
>
> ## Verdict
>
> Accept. Both changes do what the second cold read asked. The empty ask panel now points to `/ask`, which is a real served route, with a plain sentence. The event desk's rule code folds under a summary that does not collide with DESK-7's three "Show the records" folds. No assertion was weakened: the one moved pin is still exact equality, and every DESK-7 pin is unchanged. The named suites, `plan.py check`, `repo.py check` and `node --check` all pass. Finding 5 (an empty rule fold on events with no judgment) is a small cosmetic follow-up and does not block release 18.

The one minor finding (the rule fold showing on a view with no judgment) is fixed in the commit that follows: the fold carries an id and hides in that branch, pinned on the fixture and the real record.
