# COPY-2 review record

## Round 1 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `6bfb139b`, 2026-10-18 06:55)

Recorded verbatim:

> # COPY-2 review, round 1: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat).
>
> Commit under review: 6bfb139b (made on main). Base: 27ee48f8. Commands ran in a temporary worktree at /tmp/claude-1000/copy2-review on 6bfb139b. The ignored bake view `.local/grid-snapshot/events/pedc-u2-2026-09-21.json` was copied in for read-only use. The worktree was removed with `--force` at the end. Nothing in the repository was edited, committed or moved.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `git diff 27ee48f8 6bfb139b` | 5 files: PROGRESS.md (row to in_progress plus a log row), copy-2.md (new), tasks.json (state and note), render.mjs (+14), test_grid_event.py (+13). Zero deleted lines in either test file. |
> | `python3 scripts/plan.py scope COPY-2 27ee48f8` | `OK: all changed files inside COPY-2 allowed paths`, exit 0 |
> | `python3 scripts/plan.py check` | `OK: 121 tasks, 8 gates`, exit 0 |
> | `python3 scripts/repo.py check` | `Checked 592 Markdown files, 3784 local links, 5 skills; bootstrap 1400 words.` PASS, exit 0 |
> | `node --check tests/fixtures/grid/event/render.mjs` | clean |
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` | `Ran 104 tests`, `OK (skipped=8)`, exit 0. All 8 skips come from this worktree's environment: LiveServer x3 (no FastAPI), RenderedImpactOnTheRealRecord x3 and RenderedPageWithTheRealArchive x2 (their `.local` records are not linked into the review worktree). The diff touches none of these classes. The new real-page test in `DeskLineOnTheRealRecord` ran and passed. |
> | `node render.mjs --root <wt>` (fixture) | `ok: true`. `plain` is 1675 characters and contains no `perm`, `seat`, `blob` or hex run of 10 or more characters. |
> | `node render.mjs --root <wt> --fixture <real view + flow.json>` | `ok: true`. `plain` contains "Data use Under the signed WESM company-copy record of 13 Oct 2026 (folded with the records below)" and no `perm:`. The folds are still the three "Show the records". |
> | Mutation: the same real view with the row reverted to "Permission" / `perm:wesm-company-copy:2026-10-13` (scratch copy only) | `plain` contains "Permission perm:wesm-company-copy:2026-10-13". The new test would fail on the release-16 page. |
>
> ## Checklist
>
> 1. **Diff matches the record.** Yes. copy-2.md says what changed, and the diff contains that and nothing more. The bake-input rewording is an ignored file, so Git does not show it. The copied view and the real-page "Data use" assertion confirm it.
> 2. **The walk reaches what the scripts drew.** Yes. `set innerHTML` clears `children` and runs `parseFragment`. That function appends real `Shim` children, adds them to `all` and stores the text between tags on the enclosing node. `textContent` writes to the node's own `text`. `createElement` and `createElementNS` nodes are walked once they are appended. The walk starts from every node in `all` that has no `parentNode`, which includes the static page's top-level tags, and goes down through `children`.
> 3. **The skip rules are correct.** Yes. DETAILS, SCRIPT, STYLE, TEMPLATE, HEAD, TITLE and nodes with `.hidden` set are skipped together with their whole subtree. The known gaps in the shim all make the check stricter: a static `hidden` attribute does not set `.hidden`, CSS hiding is not modelled, `innerHTML` does not reset the node's earlier own text, and an unattached created node counts as a root. Each of these can only add text to `plain`, never hide text from it.
> 4. **The permission id would be caught if it were visible.** Yes. The mutation run above shows it.
> 5. **The word list is reasonable, and the real page must say "Data use".** Yes, with two small gaps (F1). The list covers permission ids, 'orchestrator seat', 'git blob', 'System One', the three execution-mode tokens and path or extension fragments. The real-page test also asserts `'Data use' in plain`.
> 6. **No existing assertion was weakened.** Yes. Both test files only gain lines. DESK-7's three records folds and DESK-8's readings fold assertions are unchanged, and the real view still renders exactly three "Show the records" folds.
> 7. **Scope and bookkeeping are correct.** Yes. Scope is OK. The PROGRESS row for COPY-2 was edited in place (no second row). The state is `in_progress`, not `done`.
> 8. **The brief's first output is honestly unnecessary.** Yes. The brief's note (03:00) already records that the live walk of release 16 found exactly one repository word outside a fold, and that it was bake input. The release-17 bake removes it. The fixture and real `plain` texts show no permission id, digest, seat name, 'git blob' or path, so there is nothing left to fold. Adding a fold class with no content would be unwarranted. The DESK-7 pin stays intact by design. The brief's purpose (no repository word on the first screen, with a test that holds it there) is met.
>
> ## Findings
>
> | # | Severity | Finding | Action |
> |---|---|---|---|
> | F1 | low | The acceptance names "digest" and "seat name". The word list has no digest pattern (for example a hex run or `sha256`) and names only 'orchestrator seat' (not executor or reviewer seat). Neither page shows any today (checked: no hex run of 10 or more characters and no "seat" in either `plain`), so there is no live defect. The guard is narrower than the acceptance wording. | Optional: add a hex-run regex and the other seat names in a later copy task. Not blocking. |
> | F2 | info | The fixture page shows "Saved · receipt event:pedc-u2-2026-09-21:retain:1" outside a fold after the person records a decision. This is a receipt id the page issues itself, not one of the acceptance's listed classes. | Note for a later plain-language pass. Not in COPY-2's scope. |
> | F3 | info | The fix itself is in an ignored bake input, so Git cannot show it. It is pinned indirectly by the real-page test, which needs the view under `.local` and cannot run without it. | Accepted as recorded. The release-17 bake carries it. |
> | F4 | info | The 8 skips in the review run come from the environment (no `.local` impact or archive links, no FastAPI). None of them is in a changed class. | The author's full-suite run in the linked checkout covers them. |
>
> ## Verdict
>
> **Accept.** The shim's `plainOutsideFolds` reads the page as drawn by its own scripts and skips exactly the folded, hidden and non-visible elements. Its imperfections all make it stricter. A scratch mutation shows the new real-page test fails on the release-16 permission row and passes on the release-17 "Data use" row. No existing assertion was removed or weakened, and DESK-7's three-fold pin is untouched. Scope, plan and repository checks pass, and the two named test modules pass (104 tests, 8 environment skips). Not adding the brief's fold class is an honest reading: the brief's own note records that the only visible repository word was bake input, and that is now plain words. COPY-2 may be set `done` once the author quotes a green full offline suite on 6bfb139b. F1 is a non-blocking suggestion to widen the word list toward the acceptance wording.
