# COPY-1 review record

The runner's own branch `task/COPY-1` carries a review record of an executor turn that never ran (provider balance); it is not a finding about this work. The rounds below are on the orchestrator seat's build on main.

## Round 1 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commits `87fbb379` and `bba9411b`, 2026-10-18 05:30)

Recorded verbatim:

> # COPY-1 review, round 1: rework
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat).
>
> Commits under review: `87fbb379` (models slice) and `bba9411b` (register and outlooks slices; task record). Base `a52f8482`. Diff read: `git diff a52f8482 bba9411b`. Commands run in a scratch worktree at `bba9411b` (`/tmp/claude-1000/copy1-review-b`, removed afterwards). It has no `.local`, so it has no browser and no outlook archive.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `python3 scripts/plan.py scope COPY-1 a52f8482` | OK: all changed files inside COPY-1 allowed paths |
> | `python3 scripts/plan.py check` | OK: 121 tasks, 8 gates |
> | `python3 scripts/repo.py check` | PASS (590 Markdown files, 3775 local links; bootstrap 1400 words) |
> | `node --check src/grid/models.js`, `register.js`, `outlooks.js` | clean (exit 0 each) |
> | `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_grid_register_page tests.test_grid_outlooks_page tests.test_hosting_stage` | Ran 134, OK (skipped=21). 19 skips are `no browser found` and 2 are `.local/outlook-archive` absent. **Every pin that moved in this change is in a skipped browser class.** I checked them by reading the code against the test strings (see item 1). They did not run here. |
>
> ## Checklist
>
> 1. **Moved pins at least as exact, no assertion removed.** Pass by reading the code. The diff touches 14 lines in `tests/test_grid_register_page.py` and 1 line in `tests/test_grid_outlooks_page.py`. Every change is a one-for-one string swap: `revision`→`version` and `(git blob id)`→`(its file id)`. The `assertEqual` and `assertIn` shape stays the same, and no assertion is added or removed. Each new string matches what `register.js` and `outlooks.js` build: summary, gaps, family line, shown line, caption, and `never checked (no version recorded)`. The source-text pin `'register version'` stays an `assertIn` on the JS, and `'revision_basis'` is still pinned. These pins ran only in the skipped browser classes here. The author's record says they ran OK.
> 2. **"It is a test stand-in, not a model run." against the fixture backend.** Pass. `FixtureSystemOne` in `src/judgment/systemone.py` is described as a "Labelled test backend" with "No transport, credential or network call". So it is a test stand-in, and it does no model inference. The sentence claims no more than the record.
> 3. **"its file id" against `revision_basis` `git blob id`.** Pass, with a note. `REVISION_BASIS = "git blob id"` (`scripts/grid/build_data.py:327`). A blob id is a content id of the file's bytes, so "its file id" is vaguer than the record but not stronger. The bake field is unchanged. The page maps only the exact string `git blob id`, and any other basis passes through verbatim. That fails safe. The mapping is duplicated: `basisWords` in `register.js` and an inline ternary in `outlooks.js`. That is acceptable for two call sites.
> 4. **Folded execution-mode rows keep `data-figure` and `data-record`, and the figure sweep covers them.** Pass. Both `<li>` rows keep their attributes unchanged inside `details.md-records`, which sits inside the same `<article class="md-card">`. `FIGURE` (`tests/test_grid_models_page.py:58`) runs over the whole body and over each card's `<article>` slice, so the folded rows stay in the value check and in the card's as-of check.
> 5. **"Kept on purpose" items defensible under the figure rule.** Partly. The as-of record paths are defensible under the figure rule, and the orchestrator's 03:00 note in the brief allows them as small print. But the brief's `outputs` and `acceptance` say the opposite: "'As of src/judgment/systemone.py' and every module path move into a records fold", and the word list includes `src/`, `docs/`, `.py` and `.js`. The register's `docs/…:line` locators match the same list. So the word-list test the brief asks for would fail on the kept items. The record does not resolve this conflict, and the brief text was not amended. See F3.
> 6. **Copy rules on the new sentences.** Pass. Each new sentence is under 20 words, in active voice, has no semicolon and does not use "stale". No status word changed: models status words are pinned by `test_the_status_words_are_the_strategy_record_s_own_and_never_stronger`. No route, nav or stage changed: `test_hosting_stage` is green.
> 7. **First screen free of the brief's listed words (the change's purpose).** Fail. Two visible items in the brief's list are left, and the record neither changes them nor lists them as "kept on purpose". See F1 and F2.
> 8. **Record honest about the missing word-list tests; slice or block.** The record is honest. §3 and §5 say the word-list test is not written. The task stays `in_progress` in `tasks.json` and PROGRESS.md and is not flipped to done. A slice without that test could be accepted on its own. But F1 and F2 are exactly what that test would catch, and the record's method claims a full walk. So the test should come with the next round, not after it.
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | F1 major | `src/grid/models.html:165` (the page caption) | The execution-mode token `synthetic_fixture` is still visible outside any fold, in the footer caption. The brief's word list names execution-mode tokens, and the change folded the same token out of the card. The record's §2 table and "kept on purpose" list do not mention the caption. | `<footer class="caption" id="caption">… The fixture backend carries the label <span class="mono">synthetic_fixture</span>.</footer>`. It is pinned by `tests/test_grid_models_page.py:330` (`'The fixture backend carries the label synthetic_fixture.'`). | Reword the caption in plain words, for example "The fixture backend is labelled as a test stand-in." Move the pin at `:330` with the copy, as the brief allows. Keep `:327-329`: the token stays in the body inside the fold, so `assertIn('synthetic_fixture', self.body)` still holds. |
> | F2 major | `src/grid/register.js:91` (`row.owner`) on `/register` | The register row facts line shows the owner verbatim. The committed register has `"owner": "orchestrator seat"`, so the page shows a seat name. The brief's `outputs` say: "'orchestrator seat' becomes 'the project seat until a person is named'". The cold-read finding names 'orchestrator seat'. The change neither does this nor records why not. | `docs/work/outlook-archive/register.json:1205` `"owner": "orchestrator seat"`. `register.js:91` builds `${row.layer} · ${row.state} · ${row.owner}`. | Map the owner word on the page, the way `basisWords` does (the bake stays the register's own word), or list it under "kept on purpose" with a reason the brief accepts. Pin the mapped words. |
> | F3 minor | `docs/work/product-gap-2026-10-17/copy-1.md` §2 "Kept on purpose", against `tasks.json` COPY-1 `outputs[0]` and `acceptance[0]` | The record keeps the as-of paths and register locators visible. The brief's own outputs and acceptance require them folded and list `src/`, `docs/`, `.py` and `.js` in the word list to test. Only a free-text note allows small print. When the word-list test is written, it must either fail or carry exemptions the acceptance text does not grant. | Brief `outputs[0]`: "'As of src/judgment/systemone.py' and every module path move into a records fold". Brief `acceptance[0]`: "no repository word of the listed set is visible outside a fold". | Before the word-list test lands, amend the brief: name the as-of line (`.md-asof`, the register evidence locators) as an allowed carrier, and scope the word list to exclude them. Alternatively, fold those lines. Record the choice in copy-1.md. |
> | F4 minor | `src/grid/register.js:48` and `:58` | The page now says "version" in every register line but still says "last checked at revision …" and "at revision …" in the mark line. A reader sees two words for one idea. These lines are not in the word list. | `` `last checked at revision ${row.last_checked_revision}` `` | Use "version" here too, or record why "revision" stays. Move any pin with it. |
> | F5 note | test run | The moved pins were not run in review: no browser exists in a worktree without `.local`. The pins are verified by reading the code, and the author's record says they ran OK. | 19 `no browser found` skips. | On rework, quote the browser-class run from the seat that has the browser. Name the run's base commit. |
>
> ## Verdict
>
> **Rework.** What changed is sound. The moved pins are exact one-for-one swaps with no assertion removed. "It is a test stand-in, not a model run." and "its file id" claim no more than `FixtureSystemOne` and `REVISION_BASIS`. The folded rows keep `data-figure` and `data-record` inside the card, where the figure sweep and the as-of check still reach them. The record is honest that the word-list test is missing, and the task stays `in_progress`. But the slice leaves two items from the brief's own list visible on the first screen, without a record of why. One is `synthetic_fixture` in the `/models` caption (F1). The other is the `orchestrator seat` owner word on `/register` (F2), which the brief rewrites in so many words. These are exactly what the missing word-list test exists to catch. The brief's acceptance also conflicts with the record's "kept on purpose" as-of paths (F3), and the word-list test cannot be written until that is settled. For the next round: fix F1 and F2, amend the brief or the record for F3, and add the word-list test in the same round. F4 is optional.

## Round 2 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `cfa0f74d`, 2026-10-18 06:00)

Recorded verbatim:

> # COPY-1 review, round 2: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat).
>
> Commit under review: `cfa0f74d` (rework after round 1). Base `a52f8482`. Round 1 reviewed `87fbb379` and `bba9411b`; its findings are in `docs/work/reviews/COPY-1.md`. Diff read: `git show cfa0f74d` (7 files, +80/-7). Commands were run in a scratch worktree at `cfa0f74d` (`/tmp/claude-1000/copy1-review-r2`, removed afterwards). That worktree has no `.local`, so it has no browser and no outlook archive.
>
> The verdict accepts the round-2 rework as a slice. It does **not** let the task be set done. See the Verdict paragraph.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `git show cfa0f74d --stat` and the diff | 7 files: `models.html` (caption), `register.js` (owner words, 2 × 'version'), `test_grid_models_page.py` (moved pin, new class), and the record, review, PROGRESS and tasks.json |
> | `python3 scripts/plan.py scope COPY-1 a52f8482` | OK: all changed files inside COPY-1 allowed paths |
> | `python3 scripts/plan.py check` | OK: 121 tasks, 8 gates |
> | `python3 scripts/repo.py check` | PASS (591 Markdown files, 3777 local links, 5 skills; bootstrap 1400 words) |
> | `node --check src/grid/register.js` | clean (exit 0) |
> | `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_grid_register_page tests.test_grid_outlooks_page tests.test_hosting_stage` | Ran 135, OK (skipped=21). 19 skips are `no browser found`, and 2 are because `.local/outlook-archive` is absent. The browser classes did not run. I read their pins against the JS instead. |
> | Mutation check (scratch script): the new test's filter, with `docs/` and `src/` added to the list, run over `models.html` at `a52f8482`, `bba9411b` and `cfa0f74d` | base: `System One`, `synthetic_fixture`, `fixture_supplied` found; round 1 (`bba9411b`): `synthetic_fixture` found (this is F1); `cfa0f74d`: none. `docs/` and `src/` occur only inside the as-of lines. |
>
> ## Checklist
>
> 1. **F1 (models caption token) closed.** Pass. At `models.html:165` the caption now ends "The fixture backend carries its own label, folded on its card." The pin at `test_grid_models_page.py:330` moved with the copy. `assertIn('synthetic_fixture', self.body)` and `'fixture backend'` are kept. No assertion was removed.
> 2. **The caption's new sentence says no more than the record.** Pass. The token `synthetic_fixture` sits on the decision card inside `details.md-records` ("Show the records", `:128-133`), with `data-record="src/judgment/systemone.py"`. So "its own label, folded on its card" is literally true, and the sentence claims nothing new. It is under 20 words, in active voice, with no semicolon.
> 3. **F2 (seat owner) closed.** Pass, with a gap. `ownerWords` maps only the exact `'orchestrator seat'` to the brief's own words, 'the project seat until a person is named'. Any other value passes through verbatim, which fails safe. The bake has one such row; the other owners are `project owner` (2) and `unassigned` (40). Gap: no test pins the mapped words. Round 1 asked for that (F-a below).
> 4. **F3 (as-of paths, register locators) decided and recorded.** Pass, with a note. The amendment is in the COPY-1 `note` in `tasks.json` (05:40) and in copy-1.md §2–§3. Its reason holds: the figure rule needs each figure's record as-of, and a register is a record of records. The `outputs[0]` and `acceptance[0]` texts themselves are unchanged, so a reader of the acceptance alone still sees the old rule. That is acceptable because the note is the brief's amendment channel. The note says the word list "keeps every other word", but the new test leaves out `docs/` and `src/` altogether (F-b below).
> 5. **F4 ('version' everywhere) closed.** Pass. `register.js:50` and `:60` now say "at version". The `revision` that is left in `register.js:6` and `outlooks.js:420` is in code comments only. The field names (`last_checked_revision`, `new_revision`, `revision_basis`) are not shown. These two lines are not pinned (no test asserts `last checked at`).
> 6. **F5 (browser-class run with its commit) handed on honestly.** Partly. copy-1.md §4 and PROGRESS row 666 quote `Ran 2604 tests … OK (skipped=46)` on `bba9411b`, with the commit named. The rework commit `cfa0f74d` changed `register.js`, but the record names no browser-class or full-suite run on `cfa0f74d`. PROGRESS row 667 cites only the four modules, with no commit or skip count (F-c below).
> 7. **The new word-list test is meaningful.** Pass. `PlainWordsOutsideTheFolds` strips only `<details>…</details>`, `<p class="md-asof">…</p>` and HTML comments, then strips tags and checks the text. The page has exactly 5 `md-asof` paragraphs and one `details`, and no nesting. The `.js` in the `<script src>` attribute is removed with the tags, so it cannot hide or fake a hit. The mutation check shows the test fails on the round-1 page (`synthetic_fixture` in the caption). So it would have caught F1. `models.js` writes only `#md-summary` from the page's own status words, so the static check sees every visible word. Weaknesses: it runs on the committed HTML, not the rendered DOM. That is adequate for a static page. Its list leaves out `docs/` and `src/` (F-b).
> 8. **Done as a slice, or in progress.** The task must stay `in_progress`. `acceptance[0]` reads "on the models, register and outlooks pages … a test checks each rendered page". Only the models page has a test. The register and outlooks checks are named as the next step in copy-1.md §3/§5. `acceptance[3]` ("the full offline suite passes") was last shown on `bba9411b`, not on `cfa0f74d`. tasks.json keeps the task `in_progress`, which is correct. The round-2 rework itself can be accepted.
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | F-a minor | `src/grid/register.js:33,93`; `tests/test_grid_register_page.py` | The owner mapping (F2) and the two 'at version' lines (F4) are unpinned. A later edit could bring back 'orchestrator seat' or 'revision' on `/register` with every test green. Round 1's F2 correction asked to "pin the mapped words". | `grep 'project seat\|orchestrator seat\|last checked'` over the register tests: no hit. | In the register word-list step, assert that a row with owner `orchestrator seat` renders 'the project seat until a person is named', and that 'orchestrator seat' and 'revision' are absent from the rendered rows. |
> | F-b minor | `tests/test_grid_models_page.py` `PlainWordsOutsideTheFolds.WORDS` | The brief's list (`outputs[2]`) and the amended note keep `src/` and `docs/` outside as-of lines and register locators. The test leaves them out entirely, so a module path in a sentence outside an as-of line would pass. | `WORDS` has `tests/`, `.py`, `.js`, `perm:` but no `docs/` or `src/`. Adding both passes today (mutation check: none found outside the as-of lines at `cfa0f74d`). | Add `'docs/'` and `'src/'` to `WORDS`, in this task's next round. |
> | F-c note | copy-1.md §4; PROGRESS row 667 | The full-suite and browser-class evidence is on `bba9411b`. The rework changed `register.js` after that, and its four-module run is quoted with no commit or skip count. `acceptance[3]` needs a full suite on the final tree. | §4: "full offline suite on `bba9411b`". Row 667: "… `tests.test_hosting_stage` OK. Round 2 next." | Before done, run the full offline suite on the final commit in the seat that has the browser, and quote it with the commit and skip count. |
> | F-d note | copy-1.md §3 | Cosmetic. The new paragraph is followed by a double blank line, and the older paragraph after it repeats that the word-list test "is not added here". That now reads as partly stale, since the models test was added. | Lines ~36-43. | Merge the two paragraphs when the record is next touched. |
>
> ## Verdict
>
> **Accept (the round-2 rework, as a slice); the task stays `in_progress`.** All three code findings from round 1 are closed:
>
> - The `/models` caption no longer prints `synthetic_fixture`. Its new sentence says only what the folded card shows.
> - `/register` prints the brief's own words for the seat owner, and the mapping fails safe.
> - 'version' is now used in every line the register page shows.
>
> F3 is decided with a sound reason, the figure rule and a register being a record of records, and it is recorded in the task note and in copy-1.md. F5 is answered with a named-commit suite run, but on the round-1 commit.
>
> The new `PlainWordsOutsideTheFolds` test is meaningful. It excludes only `details` and the five as-of paragraphs, sees every visible word on that static page, and fails on the round-1 page. So it would have caught F1.
>
> The task cannot be set done. `acceptance[0]` requires a test on each rendered page, and only `/models` has one. `acceptance[3]` has no full-suite run on the final tree. The next round should:
>
> - add the register and outlooks word-list checks in their browser classes, with the owner and 'version' pins (F-a);
> - add `docs/` and `src/` to the models list (F-b);
> - quote a full browser-seat suite run on the final commit (F-c).
>
> That round needs only a short confirming review.

## Round 3 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `83c5ac88`, 2026-10-18 06:05)

Recorded verbatim:

> # COPY-1 review, round 3: rework
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author.
>
> Commit under review: `83c5ac88` (rework after review round 2). Base: `a52f8482`. Round 2 accepted `cfa0f74d` as a slice and named items (a) to (d) as owed. Commands ran in a throwaway worktree at `/tmp/claude-1000/copy1-review-r3` (detached at `83c5ac88`, removed afterwards). This seat has no browser, so the browser classes skip. I read their new assertions against the harnesses and the page JS.
>
> ## Commands
>
> | Command | Result |
> |---|---|
> | `git show 83c5ac88 --stat` and the diff | 8 files, +60/-2. Tests, the two harnesses and the task docs only. No change to `src/`. |
> | `python3 scripts/plan.py scope COPY-1 a52f8482` | exit 1. One file is outside scope: `docs/work/current.json`, from orchestrator commit `36432145` ("live pointer at session close"). This is the known case where an orchestrator commit falls outside the task's paths. |
> | `python3 scripts/plan.py scope COPY-1 36432145` | exit 0. `OK: all changed files inside COPY-1 allowed paths` |
> | `python3 scripts/plan.py check` | exit 0. `OK: 121 tasks, 8 gates` |
> | `python3 scripts/repo.py check` | exit 0. `PASS` (591 Markdown files, 3779 local links, bootstrap 1400 words) |
> | `node --check tests/fixtures/grid/register/browser.mjs` | exit 0 |
> | `node --check tests/fixtures/grid/outlooks/browser.mjs` | exit 0 |
> | `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_grid_register_page tests.test_grid_outlooks_page tests.test_hosting_stage` | **exit 1**. `Ran 153 tests ... FAILED (errors=3, skipped=36)`. All 3 errors are in `TheOneRowRegisterInTheBrowser` (`KeyError: 'seen'` / `'thrown'`). See F1. |
>
> ## Checklist
>
> 1. **Diff is in scope and matches the record.** Mostly yes. The change touches tests, harnesses and task docs only. Scope is green against the orchestrator commit `36432145`, and the `current.json` line comes from the orchestrator commit, not from the author. One part of record section 7 does not match the code (F2).
> 2. **Both harnesses' `plain` field removes details, hidden elements, scripts and styles before it reads the text.** Yes. Each harness clones `document.body`, removes `details, [hidden], script, style, template` from the clone, then reads `textContent` with whitespace collapsed. The result is stricter than what is on screen, because it also keeps text that CSS hides. That errs on the safe side.
> 3. **The two new browser tests would catch the round-1 findings.** Yes, when a browser is present. Both lists hold `orchestrator seat` and `git blob`, and `plain` contains only text outside a fold. If `ownerWords` in `src/grid/register.js:33` regressed, or a `git blob` basis leaked outside a fold, the test would fail. Both tests also assert `register version` and the absence of `revision`.
> 4. **The register list allows row source locators, says so, and the reason holds; the outlooks list keeps the path words.** The register docstring says so, and the reason holds ("a register is a record of records"). `tests/`, `.py` and `.js` are left out of the register list for that reason. The outlooks list keeps `tests/`, `.py` and `.js`, but it does **not** contain `docs/` or `src/`, although the record says it does (F2).
> 5. **`ThePageSource` pins the owner mapping and the `at version` lines.** Yes. The test pins the exact `ownerWords` ternary, `'last checked at version '`, `'</span> at version '` and `assertNotIn('at revision')`. All of these match `src/grid/register.js` lines 33, 50 and 60.
> 6. **`docs/` and `src/` are in the models list.** Yes (`tests/test_grid_models_page.py` `PlainWordsOutsideTheFolds.WORDS`).
> 7. **Checks are green.** `plan.py check`, `repo.py check` and `node --check` are green. Scope is green against the orchestrator commit. The four-module run is **red** in a seat without a browser (F1).
> 8. **Full suite on the final tree, with commit and skip count.** Pending in the author's seat, as briefed. This review does not count it as missing. On this commit, though, that run comes back red in any seat without a browser, because of F1.
>
> ## Findings
>
> | # | Severity | Finding | Evidence | Fix |
> |---|---|---|---|---|
> | F1 | Blocking | The new register class `PlainWordsOutsideTheFolds` was inserted **between** the existing `@unittest.skipUnless(all(BROWSER) and NODE, ...)` decorator and `class TheOneRowRegisterInTheBrowser`. The decorator now applies to the new class, which inherits the skip from `ThePageInTheBrowser` anyway. `TheOneRowRegisterInTheBrowser` lost its skip guard. In any seat without a browser (this seat, the reviewer sandbox, a bare worktree), its `setUpClass` runs the harness with no browser path, and its three tests error. The author's run did not show this because that seat has a real Chromium, where the class runs and passes. | `tests/test_grid_register_page.py:634-656`. Compare `git show 83c5ac88^:tests/test_grid_register_page.py`, where the decorator sits directly above `TheOneRowRegisterInTheBrowser`. The run gives `FAILED (errors=3, skipped=36)`. | Move the `@unittest.skipUnless(...)` block back above `class TheOneRowRegisterInTheBrowser`. Keep the new class as it is (it inherits the skip), or give it its own decorator, but do not take the existing one. Re-run the four modules with no browser and expect zero errors. |
> | F2 | Minor | Record section 7 says "the outlooks list keeps `tests/`, `.py`, `.js`, `docs/` and `src/`". The outlooks `WORDS` tuple has no `docs/` or `src/`. The outlooks docstring hints at a reason (the track record names the scorecard's inputs by file), but nobody says this is an allowance. | `tests/test_grid_outlooks_page.py:1165` and `docs/work/product-gap-2026-10-17/copy-1.md` section 7 | Add `docs/` and `src/` to the outlooks list if the rendered page passes with them (the author can check this in the browser seat). If not, correct the record and state the allowance in the docstring, as the register class does. |
> | F3 | Note | Both new classes subclass `ThePageInTheBrowser`, so each one runs the whole parent setUpClass (one browser launch per width) again and re-runs every inherited test. The result is right, but the browser time for these two modules about doubles. The register test also asserts `assertNotIn('git blob', plain)` twice (once in the loop and once after it). | Both new classes | Optional: move the method into the parent class, or set the inherited tests aside. Do not block on this. |
>
> ## Verdict
>
> **Rework.** The substance of round 2's items (a), (b) and (c) is in place and correct. Both harnesses build `plain` the right way. The new tests would catch a seat name or `git blob` outside a fold. The owner mapping and the two `at version` lines are pinned exactly against `src/grid/register.js`. The models list has `docs/` and `src/`. However, the commit moved a skip decorator off `TheOneRowRegisterInTheBrowser` (F1), so the four named modules, and therefore the full suite, are red (3 errors) in every seat without a browser. That would turn the next reviewer's and any bare worktree's run red. The task may **not** be set done on the author's full-suite quote for `83c5ac88`. The fix is to move the decorator back, which is one line. Also settle F2, either by adding `docs/` and `src/` to the outlooks list or by correcting the record. Then quote a full suite on that new commit, with its skip count, and run once with no browser to show the browser classes skip cleanly. With that done, a confirming look is all that is needed. No further design work is owed.

## Round 4 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `b39cc042`, 2026-10-18 06:25)

Recorded verbatim:

> # COPY-1 review, round 4: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author.
>
> - Commit under review: `b39cc042` (rework after round 3), recorded at `550aecd3` (no-browser run row)
> - Base: `83c5ac88` (round 3's commit)
> - Diff read: `git diff 83c5ac88 b39cc042` and `git diff 83c5ac88 550aecd3` (5 files: two tests, task record, review record, PROGRESS)
>
> ## Commands
>
> | Command (bare worktree at `b39cc042`, no browser, no ignored inputs) | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_grid_register_page tests.test_grid_outlooks_page tests.test_hosting_stage` | `Ran 153 tests` **OK (skipped=39)**, no errors |
> | `python3 scripts/plan.py check` | `OK: 121 tasks, 8 gates`, exit 0 |
> | `python3 scripts/repo.py check` | `Checked 591 Markdown files, 3781 local links, 5 skills; bootstrap 1400 words. PASS`, exit 0 |
>
> ## Checklist
>
> 1. The skip decorator is back on `TheOneRowRegisterInTheBrowser` (tests/test_grid_register_page.py line 652 over class at 655). Yes.
> 2. Register `PlainWordsOutsideTheFolds(ThePageInTheBrowser)` has no own decorator and inherits the skip from `ThePageInTheBrowser` (decorated at line 489). Yes.
> 3. Outlooks `PlainWordsOutsideTheFolds` subclasses the decorated outlooks `ThePageInTheBrowser` (lines 817/820/1160), and its `WORDS` now holds `docs/` and `src/`. Yes.
> 4. The duplicate `assertNotIn('git blob', ...)` was dropped; `'git blob'` stays in `WORDS`, so no coverage is lost. Yes.
> 5. Task record copy-1.md section 8 describes the fix truthfully and quotes the full suite on `83c5ac88`: `Ran 2623 tests` **OK (skipped=46)**. Yes.
> 6. PROGRESS row (round 3) quotes the same 83c5ac88 full-suite figure. Yes.
> 7. PROGRESS row at `550aecd3` quotes the no-browser run on `b39cc042` as **OK (skipped=39)**; my independent run reproduces exactly that. Yes.
> 8. A seat without a browser no longer errors (round 3 blocker closed); plan and repo checks pass. Yes.
>
> ## Findings
>
> | # | Severity | Finding |
> |---|---|---|
> | - | - | None. Round 3's blocking finding (displaced skip decorator) and minor finding (outlooks word list) are both resolved. |
>
> Note (not a finding): the rendered-page check of the new `docs/` and `src/` words on /outlooks needs a browser; it skipped here by design. The author states the rendered page passes; the full suite on `b39cc042` with real Chromium will show it.
>
> ## Verdict
>
> Accept. The rework is limited to the two round-3 findings and does them correctly; the browser-less run reproduces OK (skipped=39) with no errors, and plan and repo checks pass. The task may be set done once the author records the full suite on `b39cc042` (real Chromium) as OK with no failures or errors, which also covers the outlooks browser class that holds the new words.
