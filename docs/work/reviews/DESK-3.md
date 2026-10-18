
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `bbc00457`, 2026-10-17 15:39, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-3 review: rework
> 
> I didn't write this change and edited no files. I reviewed both commits on `task/DESK-3` (`5c435353`, `bbc00457`) against `feat/product-refine`, using the brief and `docs/engineering/review-and-feedback.md`.
> 
> **Verdict: rework.** One acceptance item fails: an attribution's share figure is shown without the digest of the record it comes from, and the task record says it is shown.
> 
> ## What I ran
> 
> | Command | Result |
> |---|---|
> | Verify command (`tests.test_grid_outlooks_page tests.test_grid_outlook tests.test_cache_headers tests.test_hosting_stage`) | `Ran 185 tests in 3.975s` · **OK (skipped=8)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-3 feat/product-refine` | `OK: all changed files inside DESK-3 allowed paths` |
> | Full suite (`/usr/bin/python3 -m unittest discover -s tests`) | `Ran 2047 tests in 163.773s` · **OK (skipped=47)** |
> | `-v tests.test_grid_outlooks_page.ThePageInTheBrowser …TheRealArchive` | 7 ok. A browser was available, so the browser class actually ran here instead of skipping. |
> | `.local/desk3-buildall.py` (the executor's script: `build_all.py` write, then `--check`, on a fresh temporary `--data` directory) | write exit 0, check exit 0, all four steps 0, `violations []` |
> 
> ## Checklist
> 
> 1. **Every acceptance item demonstrated by a check that was run: no.** Item 1 ("every figure on the page cites the record digest it comes from") is not met for the attribution share (finding 1). The other items are demonstrated:
>    - **Route:** `/outlooks` is served with `REVALIDATE_CACHE`, like `/explain` (`src/api/__init__.py:460`), and is listed in `LOCAL_ROUTES` and the class table.
>    - **Hosting stage:** it carries the three design files, with a new assertion added and no existing one removed.
>    - **Home page:** `src/grid/index.html` is unchanged.
>    - **Browser:** at 390 and 1280 under the CSP, the console is clean and `/outlooks` and the index both answer 200.
>    - **Current vintage:** named in words, every time shown in UTC with its date, no badge.
>    - **Real archive:** `TheRealArchive` asserts the two vintages and 0 receipts.
>    - **Read, never written:** a test checks that a rebuild leaves the register and archive unchanged.
> 2. **No file outside the allowed paths changed: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** The moved pins (8→9 files, 10→11 fixture files) are still exact. `outlook_problems` in `tests/test_grid_outlook.py` now ignores one line, `outlook/index.json: missing`. That narrows what the view tests see but weakens nothing: those tests build event views only and never produce the index. The index's own rules are tested by eight refusal tests in the new module and by the full-bake `--check` (9 contract files).
> 4. **No new dependency, service, network, model or cloud call: yes.** The page reads one same-origin file, and there is no new import.
> 5. **Mode labels truthful: yes.** The caption's wording comes from each shown vintage's own `synthetic` flag, and the fixture run says "synthetic true".
> 6. **Unknowns stayed unknown: yes.** The real index has no event links because the PEDC assumption matches no register row.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: partly.** Everything is there, but §6 row 1 states something that isn't true (finding 1).
> 8. **Nothing contradicts the strategy or invariants: yes.** The uppercase sub-labels follow the convention that `event.css` and `grid.css` already use.
> 
> ## Findings
> 
> 1. **important** | `src/grid/outlooks.js:316-319`, and `docs/work/price-outlook/desk-3.md:177`
>    - **Failure:** The attribution sentence prints `share 0.2 of the miss` with no digest. The share comes from the attribution, which ARCH-4 made a separate record, not from the receipt named in the line above it. So a figure on the page has no record digest, which is what acceptance item 1 forbids.
>    - **Packet:** §6 row 1 says the page reads `a.content_digest`. It does not.
>    - **Evidence:** `attributionSentence` uses only `statement`, the reference, `share`, `attributed_by`, `attributed_at` and `synthetic`. The baked index does carry the digest (`tests/test_grid_outlooks_page.py:307` asserts it), so the page drops a field it already has. The browser test pins the sentence with no digest at line 621.
>    - **Correction:** add ` · record ${shortHex(a.content_digest)}` to the sentence, following the stale-mark line's convention. Re-pin the exact string at `tests/test_grid_outlooks_page.py:620-623`, and correct §6.
>    - `event.js:257` has the same gap, but that card is ARCH-4's accepted surface, so I note it without scoring it here.
> 2. **minor** | `src/grid/outlooks.js:445-447`
>    - **Failure:** The summary's counts ("holds 3 issued outlooks in 2 targets") come from `archive.verify`, but the sentence's only citation is the register revision, which is a different record.
>    - **Correction:** say where the count comes from ("by the archive's verify") so the register revision isn't read as its source.
> 3. **minor** | `scripts/grid/build_data.py` (`outlook_index_problems`, the `change_problems(name, place, …)` call)
>    - **Failure:** `place` is the target's index from the outer loop, not the vintage's, so a diff problem names the wrong position. Only the message is wrong; the check still works.
>    - **Correction:** pass `index`, or label the message `targets[place].vintages[index]`.
> 4. **minor** | `scripts/grid/build_data.py` (`OUTLOOK_INDEX = "outlook/index.json"`)
>    - **Failure:** An event whose id is `index` would share a path with the archive index. Its view would be skipped by the per-event loop and reported as missing.
>    - **Evidence:** No such event exists today.
>    - **Correction:** refuse an event id of `index`, or document that it is reserved.
> 
> **Reason:** the attribution share is shown without its record's digest, so acceptance item 1 is not met. The packet says it is, and the fix is small.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `94f42000`, 2026-10-17 15:54, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> The full suite is still running in the background. I'll write the review when it finishes.
> 
> # DESK-3 review (round 2): accept
> 
> I reviewed `task/DESK-3` at `94f42000`, against `feat/product-refine` (merge base `f26debf2`). That covers five commits, including the rework `7e305df0`. I didn't write this change and edited no files. One correction to the brief's expectation: a browser was found in this environment, so `ThePageInTheBrowser` actually ran here and passed. It did not skip.
> 
> ## What I ran
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_outlooks_page tests.test_grid_outlook tests.test_cache_headers tests.test_hosting_stage` | `Ran 186 tests in 4.307s` · **OK (skipped=8)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-3 feat/product-refine` | `OK: all changed files inside DESK-3 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 2048 tests in 194.384s` · **OK (skipped=47)** |
> | `-v …ThePageInTheBrowser …TheRealArchive` | 7 tests, all ok (the browser ran at 390 and 1280 under the header policy) |
> | `.local/desk3-buildall.py`: `build_all.py` writes a fresh temporary `--data` directory, then `--check` runs on it | write exit 0, all four steps 0, check exit 0, `violations []`, the index holds one target and one vintage, verify `1/0/0` |
> | `git status` after every run | clean. `src/grid/index.html`, `register.json` and `src/outlook/` have no diff against the base |
> 
> ## Round-1 findings: all four fixed
> 1. **Attribution digest:** `outlooks.js:86-87` now ends the sentence with ` · record <attribution content_digest>`. The browser test re-pins the exact string, reading the digest from the baked index.
> 2. **Count source:** the summary now says "The archive's verify counts …", so the count isn't read as coming from the register revision. There is a separate wording for an index that lost its counts.
> 3. **Diff row label:** `change_problems` takes a `label`. The index passes `targets[place].vintages[index].changes`, and a test pins the prefix.
> 4. **Reserved id:** `price_outlook_files` refuses an event id of `index` with a `BuildInputError`, and a new test proves the refusal.
> 
> ## Checklist
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **Digest per figure:** the vintage line, the diff, the inputs, the receipt and the attribution each cite a record digest.
>    - **Route:** `/outlooks` returns `REVALIDATE_CACHE` (`src/api/__init__.py:460`). It is classified in `LOCAL_ROUTES` and in the class table.
>    - **Hosting stage:** it carries the three design files. The new test adds assertions and removes none.
>    - **Home page:** `index.html` is untouched.
>    - **Copy:** the current vintage is named in words, times are shown in UTC with their date, and there is no badge (all pinned in the browser test).
>    - **Read, never written:** a test confirms it.
>    - **Fresh bake:** `--check` passes.
>    - **200 answers:** both `/outlooks` and the index answer 200 in the local serve, asserted at both widths, and that test ran here.
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract, acceptance text or test weakened: yes.**
>    - The file counts moved 8→9 and 10→11 and are still exact.
>    - The `outlook_problems` helper now excludes only the line `outlook/index.json: missing`. Those tests do partial view-only builds, and the index has its own contract tests.
> 4. **No new dependency, service, network, model or cloud call: yes.** The page fetches one same-origin file, and there are no new imports.
> 5. **Mode labels truthful: yes.** The caption is derived from each shown record's own `synthetic` flag.
> 6. **Unknowns stayed unknown: yes.** The real archive shows two vintages and 0 receipts. No event links appear where the dependency walk doesn't claim one.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** See desk-3.md §6–§10 and the Rework section. The figures there match what I re-ran (186 / 2048, the build output).
> 8. **No contradiction with strategy or invariants: yes.**
> 
> ## Findings
> - **minor** | `src/grid/outlooks.js:210` | The summary's "newest issued" picks the newest vintage by comparing `issued_at` as strings. The bake orders vintages by parsed instant, so two different UTC offset spellings could name a different vintage than the bake's order. | The `String(o.issued_at) > String(best.issued_at)` reduce. | Take the last vintage of the bake's issued order, or compare `Date.parse` values.
> - **minor** | `src/grid/outlooks.js:87` | The sentence ends `…` followed by `.`, so it renders as "record abcd…." with two marks. This is cosmetic. | It is pinned at `tests/test_grid_outlooks_page.py` (the attributions assertion). | Drop the final period when the sentence ends with the shortened digest, and re-pin the test.
> 
> **Verdict: accept.** Every acceptance item is shown by a check I ran here, including the browser run and the fresh `build_all --check`, and all four round-1 findings are fixed without weakening any test. Only two cosmetic minor findings remain.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
