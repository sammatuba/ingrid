
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `0dd71871`, 2026-10-17 23:36, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # OUTLOOK-7 independent review
> 
> **Verdict: accept.** Every acceptance item is met, and I re-ran the evidence myself on `0dd71871`, including a render of the real data at both page widths. All five findings are minor: none blocks the merge, and each can go into a follow-up task.
> 
> I reviewed `task/OUTLOOK-7` at `0dd71871` (two commits) against `feat/product-gap-g` at `dbdb0269`, which is also the merge base. I did not write this change. I edited no tracked file. The only files I wrote were an ignored log (`.local/review-outlook7-suite.log`) and screenshots under `/tmp/rev-outlook7/`.
> 
> ## Commands run (`/usr/bin/python3`, worktree root)
> 
> | Command | Result |
> |---|---|
> | `-m unittest tests.test_grid_outlooks_page` (the verify command) | `Ran 36 tests in 5.827s`, **OK**, 0 skipped. Node and Chromium were found, so the browser class ran at 390 and 1280 px instead of skipping. |
> | `-m unittest discover -s tests` (full suite) | `Ran 2452 tests in 240.266s`, **OK (skipped=62)**, exit 0, no FAIL or ERROR lines |
> | `scripts/plan.py scope OUTLOOK-7 feat/product-gap-g` | `OK: all changed files inside OUTLOOK-7 allowed paths` |
> | `scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `scripts/repo.py check` | `Checked 571 Markdown files, 3695 local links, 5 skills; bootstrap 1400 words.` **PASS** |
> | `tests/fixtures/grid/outlooks/browser.mjs`, real data (`.local/outlook7-bake/index.json`), at 390 and 1280 with `--shot` | `ok: true`, overflow 0 at both widths. In the screenshots, "Billing month 2026-11" and "…is 4,770.9 PHP/MWh." sit near y≈310–340 of the 900 px viewport, so they are on the first screen. |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **Price, month and band on the first screen:** I checked this myself with the screenshots of the real data at both widths. The browser test confirms the answer is each target's first element.
>    - **The band:** shown only on the labelled synthetic fixture. Both real values records carry no band, which I confirmed with `TheRealArchive` and by reading the files. The page says so in words.
>    - **Position versus forecast model:** the title line says it, and a test pins the wording.
>    - **Copy rules:** tested on every answer sentence. Each figure carries as-of fingerprints of both records.
>    - **Values come from the values file by fingerprint:** `test_each_real_vintage_carries_the_values_record_the_page_prices_from` re-hashes the record's bytes.
>    - **Full suite passes:** see the table above.
> 2. **No file outside allowed paths: yes.** `plan.py scope` printed OK, and `tests/fixtures/grid/` is an allowed path.
> 3. **No frozen contract, acceptance text or test weakened: yes.**
>    - In `tasks.json`, only the note and state changed.
>    - One expected value moved: `values b2b2b2b2…` became `first_values['sha256'][:8]`. It is still exact and comes from the independently written record, as DESK-6 did.
>    - The harness `line` selector now points at `.ol-records .asof`. That is a pointer change only, and no assertion reads it.
>    - Nothing was skipped or deleted.
> 4. **No new dependency, service, network, model or cloud effect: yes.** The change is JS, CSS and HTML, plus a loopback-only harness.
> 5. **Mode labels truthful: yes.** The real page's caption says "recorded method run … (synthetic false)", and the fixture stays labelled synthetic.
> 6. **Unknowns stayed unknown: yes, with finding 1 below.** The missing band is stated, the missing receipt is stated, and the mean is described in words.
> 7. **Packet complete: yes.** §6 records the interpreter, commands and results, and §8 lists unfinished items and the next action.
> 8. **No contradiction of the plan or domain: yes.** `target-contract.md` defines hourly scoring per horizon and no monthly figure, so the page's mean is display arithmetic that it labels. It does not redefine the target.
> 
> ## Findings
> 
> All five are minor.
> 
> 1. **The headline sentence is stronger than the record** (`src/grid/outlooks.js:260`)
>    - **Problem:** "The desk's current position for billing month 2026-11 is 4,770.9 PHP/MWh." states a single monthly figure. The record holds 744 hourly values, scoring is hourly, and the series is a load-weighted average, of which a simple mean is not the monthly figure. The next sentence corrects this, but the large first line reads on its own.
>    - **Fix:** phrase it as "The desk's current position for billing month 2026-11 averages 4,770.9 PHP/MWh over its 744 hours."
> 2. **The band label claims a monthly p10–p90 it does not compute** (`src/grid/outlooks.js:265`)
>    - **Problem:** "Its band runs from X to Y PHP/MWh (p10 to p90)" prints the means of the hourly p10 and p90 values. That is not the p10–p90 range of the monthly figure. Real records carry no band, so this only shows on the fixture today.
>    - **Fix:** "The mean of its hourly p10 and p90 levels runs from X to Y PHP/MWh." The same applies to the chart's `band … to …` label.
> 3. **The chart scale ignores the band** (`src/grid/outlooks.js:311`)
>    - **Problem:** `low` and `high` come from the means only, so whiskers can fall outside the 0–150 drawing area and be cut off with no warning. In the fixture the p90 whisker lands at y≈1.1. With a single vintage the span is only 2% of the value, so any realistic band runs far outside the chart. The test checks `y1 < y2` but never checks the bounds.
>    - **Fix:** include p10 and p90 in `low` and `high` when present, and assert that every whisker y is between 0 and 150.
> 4. **The first screen does not say which price this is** (`src/grid/outlooks.js:286`)
>    - **Problem:** the series line moved into the fold. The heading "Billing month 2026-11" and the answer never say what the price is ("whole-system load-weighted average") or which window the billing month covers (26 Oct to 25 Nov). Both facts are in the data the page already has (`series_label`, `window_start_hour_local`, `window_end_hour_local`). In the fixture, two targets render the same heading.
>    - **Fix:** put `series_label` and the window in the first sentence or the heading. For "what it rests on", name the series rather than the file `lwap_final_hourly.csv`.
> 5. **One answer path has no test** (`src/grid/outlooks.js:257`, `tests/test_grid_outlooks_page.py`)
>    - **Problem:** every vintage in the browser fixture now has a values record. Nothing checks the "The build links no values record for this position, so the page shows no price." sentence, or that a vintage without values draws no chart point.
>    - **Fix:** add one browser or page-source case with a vintage that has no `values` block.
> 
> ## Verdict
> 
> **Accept.** The first screen of `/outlooks` now shows the month and a price backed by a record, and the title line separates a position from a forecast model. All checks pass, and the five findings are minor wording, chart-scale and test-coverage items for a follow-up. The band appears only on the synthetic fixture because the real records have none, so the live page will say "no band" until a scoring run records one.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
