
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `82ef1b65`, 2026-10-17 23:11, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> The review is almost done. The last thing running is the full offline suite. I'll give the verdict when it finishes.
> 
> # MODELS-1 independent review
> 
> I reviewed `82ef1b65` on `task/MODELS-1` against `feat/product-gap-e` (`7f3ad083`, which is also the merge base). The branch has four commits and changes seven files. I edited nothing.
> 
> **Verdict: rework.** Two acceptance items were not met: 14 figure labels break copy rule 5, and the decision card says "No Clef call exists" next to an unqualified Clef-Flash answer claim. Both fixes are small and inside the allowed paths.
> 
> ## Commands run
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_hosting_stage` | `Ran 68 tests` **OK** |
> | `/usr/bin/python3 scripts/plan.py scope MODELS-1 feat/product-gap-e` | `OK: all changed files inside MODELS-1 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (569 Markdown files, 3661 links) |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2449 tests in 250.297s` **OK (skipped=62)**, exit 0. The packet's 2433 was measured before BAKE-1 joined the base. |
> | Record-edit probe (in memory, on `TheServedPage`) | TimesFM AUC 0.688→0.700: 2 failures. Paper 28→29 of 192: 2 failures. TimesFM record date `2026-10-03`→`04`: **0 failures**. |
> 
> ## Checklist
> 1. **Every acceptance item met by a check that was run: no.**
>    - **No number without its record: partly met.** Every `data-figure` value is parsed from its record and compared, and the number sweep runs. But the "3 Oct 2026" as-of date is not bound to its record (finding 3).
>    - **Copy rules 1 to 7: not met.** `TheCopyRules` tests only the brief's examples in brackets: 20 words, passive voice, semicolons, "stale". Rule 5 ("labels of at most three words") fails (finding 1). The project reads rules 1 to 7 as the strategy refresh's copy rules (`docs/work/strategy-refresh-2026-10-14/strategy.md:48-55`), as the DESK-5 record and review did. Every sentence passes the word count; the longest has 16 words.
>    - **No inline script or style; route classified; staged files listed; suite passes: met.** `ThePageSource` passes. ROUTES-1's classification and stage pins are present (`tests/test_cache_headers.py:397`, `tests/test_hosting_stage.py:235`).
>    - **Status words never stronger than the record's: no** (finding 2).
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract, acceptance text or test weakened: yes.** The only test file is the branch's new module. In the HTML, two comments were edited, and there is no route, nav or stage change.
> 4. **No new dependency, service, network or model call: yes.** The page is static and `models.js` makes no fetch.
> 5. **Mode labels truthful: no** (finding 2). The `synthetic_fixture` label is correct and appears in the caption.
> 6. **Unknowns stayed unknown, nothing invented: yes, with one exception.** I checked every prose claim against its record (timesfm-tabfm.md, the paper §7.5 and Table 6, extraction.md G-1, corpus intent, status.md, baselines). The exception is the qualifier dropped in finding 2.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes, with stale commit ids** (finding 4).
> 8. **No contradiction with the strategy, the paper or the invariants: no.** The decision card contradicts itself on Clef (finding 2).
> 
> ## Findings
> 1. **important** | `src/grid/models.html:124-185` (the `md-fig-label` spans)
>    - **Failure:** copy rule 5 (`strategy-refresh-2026-10-14/strategy.md:52`) allows labels of at most three words. 14 of the 37 figure labels are longer, for example "Hour-of-day baseline it fell below, low" (6), "Training rows per region, boosted model" (6), "Recorded runs on the real case" (6) and the "AUC, next hour, Visayas" group (4).
>    - **Evidence:** a count of the labels gives 14 over three words. The sibling pages keep labels to 1–3 words (`catalog.js:229-238`, `asset.js:163-166`, `outlooks.js:202-209`). No test checks label length, but the packet's §5 marks this item "Met".
>    - **Correction:** shorten each label to three words or fewer and move the qualifier into the card text or a column header (for example "Baseline, low" with "the hour-of-day baseline it fell below" in a card line). Add a label-length assertion to `TheCopyRules`.
> 2. **important** | `src/grid/models.html:165,173,183-185`
>    - **Failure:** the status line says "No Clef call exists." Then the card says "Clef-Flash gave three byte-identical answers to one request" and shows the three Clef-Flash figures without the record's limit. A reader concludes that a Clef call ran in the product. The text is stronger than the record, and the card contradicts its own status word.
>    - **Evidence:** the paper's Table 6 row (`paper-accountable-ai-decisions-2026-10-17.md:430`) says "smoke-tested on one structured request … never served to the desk; demonstrated on a smoke test only". `docs/work/clef/notes.md` records three live `/v1/systemone` smoke runs of the Clef-flash container.
>    - **Correction:** remove the Clef-Flash lines and figures, which the brief does not ask for. Or keep them with the record's own limit, for example "in one smoke test, never on the desk or a case". If the strategy's "no Clef call" is itself wrong given CLEF-1, that goes to the orchestrator as a question, not into this page.
> 3. **minor** | `tests/test_grid_models_page.py:288` and `src/grid/models.html:136,159`
>    - **Failure:** the "3 Oct 2026" as-of is not read from its record. `'2026'` is hard-coded as allowed, and the "3" passes the sweep only because it matches the 3-hour horizon figure.
>    - **Evidence:** the probe changed the record's `2026-10-03` and the page tests still passed.
>    - **Correction:** parse `\*\*(\d{4}-\d{2}-\d{2}) ·` from the record, assert the printed date against it, and remove the hard-coded `'2026'`.
> 4. **minor** | `docs/work/product-gap-2026-10-17/models-1.md` (post-commit section) and the PROGRESS log row
>    - **Failure:** the packet cites the build commits `e8417cb4` and `0ec7d9d6`. The branch has `d93b0116 → 9970950b → d8e5ff4d → 82ef1b65` (the runner rebased it). The log row says the branch started from `4ce586ab`, but the merge base is `7f3ad083`.
>    - **Correction:** cite the commits that are on the branch now and record the base drift.
> 5. **minor** | `src/grid/models.js`
>    - **Failure:** no test runs the status-summary script. The tests only match strings in the source, and the packet records only `node --check`. Without the script, the `md-summary` line stays empty.
>    - **Correction:** add a small node or browser check of the composed line, or record the runner's browser evidence.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `f5e14f25`, 2026-10-17 23:32, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # MODELS-1 independent review, round 2
> 
> **Verdict: rework.** Two sentences on the decision card state more than the records do: "No Clef call exists" and "the same request … in two recorded runs". Each fix is one phrase inside `src/grid/models.html`.
> 
> I reviewed `f5e14f25` on `task/MODELS-1` against `feat/product-gap-e` (`7f3ad083`, which is also the merge base). The branch has seven commits. I edited no file in the repository; the only thing I wrote was the suite log, to the ignored `.local/models1-review-suite.log`, and `git status` is clean.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_hosting_stage` | `Ran 71 tests in 3.083s` **OK**, exit 0 |
> | `/usr/bin/python3 scripts/plan.py scope MODELS-1 feat/product-gap-e` | `OK: all changed files inside MODELS-1 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (570 Markdown files, 3663 links) |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2452 tests in 269.254s` **OK (skipped=62)**, exit 0. This matches the packet's R5: round 1's 2449 plus the three new tests. |
> | `TheSummaryInNode` | Node is present here (`~/.local/bin/node`), so the test ran and passed. |
> | My record-edit probes (in memory, records untouched) | `30 documents`→`31`: 2 failures. `thinking level high`→`low`: 1 failure. `36,827`→`36,828`: 2 failures. `two runs`→`three runs`: 1 error in `setUpClass`, because the grab fails. That error is still a red run. |
> 
> All five round-1 findings are closed:
> - Every label is now three words or fewer, and a test holds that.
> - The Clef-Flash lines are gone.
> - The as-of date is parsed from its record, and the hard-coded `2026` is gone.
> - The packet records the base drift.
> - Node now runs `models.js`.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.**
>    - Figures bound to records: **met**. Every `data-figure` value is parsed from its record, the number sweep runs, and my probes turn red.
>    - Copy rules: **met**. Sentences have 20 words or fewer, the voice is active, there are no semicolons, no "stale", and labels have three words or fewer. For rule 1, I follow the DESK-5 reading: the card's as-of record supplies the time.
>    - "Nothing claimed beyond the status words": **not met** (finding 1).
>    - No inline code, route classified, files staged, suite green: **met**.
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK. `tests/fixtures/grid/models/summary.mjs` falls under the allowed `tests/fixtures/grid/`.
> 3. **No frozen contract, acceptance text or test weakened: yes.** The only test change is the new module. There is no route, stage, classification or nav change.
> 4. **No new dependency, service, network or model call: yes.** The page is static, and `models.js` makes no fetch.
> 5. **Mode labels truthful: yes.** `synthetic_fixture` and `fixture_supplied` are read from `src/judgment/systemone.py:161`, and the caption carries the label.
> 6. **Unknowns stayed unknown, nothing invented: no** (findings 1 and 2). I checked every other prose line against `timesfm-tabfm.md`, the paper §7.5 and Table 6, the working paper at line 53, `extraction.md` G-1, the corpus intent at line 78, and `status.md:21`. They hold.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes**, with some lines left over from round 1 (finding 3).
> 8. **No contradiction with the strategy, the paper or the invariants: no.** The decision card's Clef line contradicts paper Table 6.
> 
> ## Findings
> 
> 1. **important** | `src/grid/models.html:112`
>    - **Failure:** "Built. No Clef call exists." is an absolute claim. The strategy cell (`strategy.md:74`) and the brief say only "no Clef call", and "exists" goes further. Round 1 asked whether that wording holds, given CLEF-1, and handed the question to the orchestrator. The rework removed the Clef-Flash lines but left this sentence, so the card now contradicts the paper served at `/paper` on the same site.
>    - **Evidence:** the paper's Table 6 (`paper-accountable-ai-decisions-2026-10-17.md:430`) says Clef-Flash was "smoke-tested on one structured request … three byte-identical answers … never served to the desk". `docs/work/clef/notes.md:15,27,36` records three live `POST /v1/systemone` runs with execution mode `live_inference`.
>    - **Correction:** use the record's own limit, for example "Built. No Clef call serves the desk." The test's `'no clef call' in statuses[2]` still passes with that wording. Update packet §2 and §7 to match.
> 2. **important** | `src/grid/models.html:117`
>    - **Failure:** "Gemini answered the same request on the real case in two recorded runs." reads as one request answered twice. The two runs were different requests at two information cutoffs. The strategy cell's "same frozen request" refers to the port's request contract, not to the two runs.
>    - **Evidence:** paper §7.5 (`:696-701`) describes one run at the trip cutoff (one passage, 9,743 tokens in) and one after the return advisory (four passages, 11,609 tokens in), with separate request digests in Appendix C. The abstract (`:5`) says "under two information cutoffs".
>    - **Correction:** for example, "Gemini answered the same question set on the real case at two cutoffs." Keep the date sentence. The figure test is unaffected.
> 3. **minor** | `docs/work/product-gap-2026-10-17/models-1.md:16-18`, `:284-287`; `docs/work/tasks.json` (MODELS-1 note)
>    - **Failure:** the state paragraph still quotes verify 68 and suite 2433. §7 still says "The Clef-Flash facts come from the paper's Table 6", which contradicts §3 and §9 (they were removed). The `tasks.json` note still carries round 1's self-review (68 and 2433) and was not updated in the rework.
>    - **Correction:** update the three places to the current numbers (71 and 2452) and to the removal.
> 4. **minor** | `src/grid/models.html:115`
>    - **Failure:** "a probability for each option" is stronger than the validator. `systemone.py:105` accepts `set(probabilities) <= set(options)`, so an answer can carry probabilities for only some options.
>    - **Correction:** "A choice question carries a choice and its option probabilities."
> 5. **minor** | `src/grid/models.html:79,156`
>    - **Failure:** "the BigQuery gate" and "The gate admits no month group" use "gate" two ways, and both are internal words for a reader. The project's plain-language banned list (`docs/routes.json`, `\bgates?\b` → "owner approval") would flag them. The page is not on that list, so this is advisory only.
>    - **Correction:** optional. For example, "The price target waits on the owner's BigQuery approval." and "The skill test admits no month group."
> 
> **Verdict: rework.** Findings 1 and 2 are factual statements on a public card that two committed records contradict, which fails "nothing claimed beyond the status words" and checklist item 6. Both are one-phrase fixes inside the allowed paths.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Round 4 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `d57f37b2`, 2026-10-18 00:45)

Round 3 (`docs/work/product-gap-2026-10-17/models-1-review-round-3.md` on main) found review round 2 never reworked; the orchestrator seat reworked on the branch and this round reviewed it. Recorded verbatim:

> # MODELS-1 review, round 4: accept
>
> Reviewer: Claude Opus 5.5 (claude-opus-5-5) in-session subagent, read-only, independent of the author (the fixes in `d57f37b2` were made by the orchestrator seat; this reviewer wrote none of the branch).
>
> - Commit reviewed: `d57f37b2` (tip of `task/MODELS-1`, "MODELS-1: rework rounds 2 and 3 by the orchestrator seat ...").
> - Base: `7f3ad083` (pre-merge base). Task diff `git diff 7f3ad083...task/MODELS-1`: 9 files, +1198/-9. Round-4 delta `git show d57f37b2`: 4 files, +35/-11 (`models.html`, `test_grid_models_page.py`, the task record, the `tasks.json` note).
>
> ## Commands run
>
> All in a temporary detached worktree `/tmp/claude-1000/models1-review-r4` at `d57f37b2`, with `/usr/bin/python3` and node from PATH. Removed afterwards.
>
> | # | Command | Result |
> |---|---|---|
> | 1 | `git diff --stat 7f3ad083...task/MODELS-1`; `git show d57f37b2` | 9 files; the round-4 commit touches 4 files, all inside the task's paths plus the `tasks.json` note |
> | 2 | `/usr/bin/python3 -m unittest tests.test_grid_models_page tests.test_hosting_stage` (the brief's verify) | `Ran 71 tests in 2.554s` **OK**, exit 0 |
> | 3 | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates`, exit 0 |
> | 4 | `/usr/bin/python3 scripts/plan.py scope MODELS-1 7f3ad083` | `OK: all changed files inside MODELS-1 allowed paths`, exit 0 |
> | 5 | `/usr/bin/python3 scripts/repo.py check` | `Checked 570 Markdown files, 3663 local links, 5 skills; bootstrap 1400 words.` **PASS**, exit 0 |
> | 6 | `node --check src/grid/models.js` | exit 0 |
> | 7 | `/usr/bin/python3 -m unittest discover -s tests`, bare worktree (no ignored `.local/` inputs) | `Ran 2423 tests in 154.259s` FAILED (errors=1, skipped=119). The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: `pypdf is not importable; unpack it at .local/pylib/`. Environment only: the branch touches no corpus file. |
> | 8 | Same suite after linking the same ignored `.local/` inputs the runner worktree `.local/wt/MODELS-1/.local` links (pylib, corpus, h1-*, grid-snapshot, price, ...) | `Ran 2452 tests in 314.606s` **OK (skipped=62)**, exit 0. This matches round 2's count on the same code plus the copy change. |
> | 9 | `git diff 7f3ad083...HEAD -- docs/work/tasks.json` | only `state` (pending → in_progress) and `note` change; acceptance, outputs, verify and owned paths unchanged |
> | 10 | `grep` for `<script`/`<style`/`style=` in `models.html`; `fetch`/`http`/`import` in the `models.js`/`models.css` diff | two external `<script src>` tags only (the staged `models.js` and `ask.js`); no inline script or style; no fetch or network call |
> | 11 | A sentence check over every `<p>` and the footer of `models.html` (split on `.!?`, flag 20+ words, `;`, `stale`, `gate`) | no flag |
> | 12 | Record reads, quoted below: paper Table 6 (`:423`, `:428`, `:429`), §7.5 (`:694-701`), paper `:618`, `docs/work/clef/notes.md:27,36`, `src/judgment/systemone.py:104-105`, strategy rows `strategy.md:72-75`, `docs/work/data-foundation/timesfm-tabfm.md:18-54`, `docs/work/corpus/extraction.md:133-147`, `docs/status.md:21`, `docs/work/corpus/intent.md:78` | quoted below |
>
> ## The five round-2/3 findings, checked against the records
>
> 1. **Important, `models.html:112`: fixed.** Now "Built. No Clef call serves the desk." Paper Table 6 (`:429`), Clef-Flash row: "smoke-tested on one structured request … three byte-identical answers to one request across the three runs; **never served to the desk**; demonstrated on a smoke test only". `docs/work/clef/notes.md:27`: "`POST /v1/systemone` HTTP 200 in **15.8978 s**". The page sentence no longer denies the recorded smoke calls. It says only what Table 6 says. The strategy row (`strategy.md:74`) status cell "built; fixture and recorded Gemini run; no Clef call" is still respected: the status word stays "Built".
> 2. **Important, `models.html:117`: fixed.** Now "Gemini answered the same question set on the real case at two cutoffs, in two recorded runs." Paper §7.5 (`:696-701`): "the compiled question set … ran … once at the cutoff after the trip advisory (13:39:37; one passage …) and once after the return advisory (15:55:56; four passages …)". The paper abstract (`:5`) says the same: "under two information cutoffs". The sentence has 16 words.
> 3. **Minor, task record and `tasks.json` note: mostly fixed.** The state paragraph names its counts by build. §7 says the Clef-Flash figures were removed. §10 answers rounds 2 and 3 with a was/now/record table. The `tasks.json` note appends a dated correction after the round-1 self-review text. Small residue is in finding R4-1 and R4-2 below.
> 4. **Minor, `models.html:115`: fixed.** Now "a choice and probabilities over its options". `src/judgment/systemone.py:105`: `_check(type(probabilities) is dict and set(probabilities) <= set(options))`. "Over its options" claims no key for every option, so it is not stronger than the validator.
> 5. **Minor, `models.html:79,156`: fixed.** Now "The price target waits on the BigQuery decision." and "No month group passes the skill check." Paper `:618`: "no month group can pass the gate whatever its forecasting quality"; `:646-648`: "none at the month horizon, where the gate cannot be passed". The strategy row (`strategy.md:72`) "the price target (PRICE-4) is pending on the BigQuery gate" stays pinned from the record by the test (`timesfm[2]` contains `BigQuery gate`), so the page's plainer word cannot drift from the record without a test change. No `gate` is left in the page's visible text.
>
> ### Test pins that moved
>
> `tests/test_grid_models_page.py`, `d57f37b2`:
>
> - `'no clef call'` → `'no clef call serves the desk'` (narrower: it contains the old pin).
> - Two pins added: `'at two cutoffs'` and `'probabilities over its options'`.
> - `'BigQuery gate'` (page body) → `'waits on the BigQuery decision'` (a longer exact phrase). The strategy-record side still asserts `'BigQuery gate'` in the record.
> - `'The gate admits no month group.'` → `'No month group passes the skill check.'` (a whole sentence, as exact as before). The record-side pin `'none at the month horizon'` in the paper is kept.
>
> No assertion was removed. Each moved pin is at least as exact as the one it replaces.
>
> ## Prose and figure spot-check against the records
>
> - **TimesFM** (`timesfm-tabfm.md:18-29`): `model => 'TimesFM 2.5'`. "the previous 2,048 five-minute intervals". "horizon 36 (3 hours)". "All 1,152 series are forecast in one call". "next hour: Visayas 0.688, Mindanao 0.737; for 3 hours 0.743 and 0.782". "The hour-of-day baseline reaches 0.85-0.89". The page matches. "Measured once on reserve-shortfall onset, not on price" matches the strategy status cell (`:72`). The as-of date 3 Oct 2026 is parsed from the record by the test.
> - **TabFM** (`:43-54`): "2,000 labeled rows", "the 17 features", "the 744 hourly September origins". The table gives 0.947/0.967 against boosted 0.943/0.961 with "36,827 training rows per region". The record says "+0.004 … +0.006 …: statistically tied". "AI.PREDICT … TabFM is in Preview". The page matches. "Measured once on onset" matches `strategy.md:73`.
> - **Decision model**: "eight" compiled questions and "four presentation forms" (Table 6 `:428`). "two runs on one case, both cited and stable" (`:428`) supports "the answers held". `gemini-3.8-flash` and "thinking budget pinned to zero" (`:428`, `:697`). "14 October 2026" (`:696`). `synthetic_fixture` and `fixture_supplied` are read from `systemone.py` by the test. The Jev/Clef/Decisions API class sentence comes from the working paper, as rounds 2 and 3 checked. That line is unchanged.
> - **Thinking model**: 30 documents (`docs/status.md:21`). Gemini 3.8 Flash at level high, decided 2026-10-16 (`extraction.md:133-134`). "The transport refuses that level today" (`extraction.md:137-138`: the validator accepts only `{"thinkingBudget": 0}`). The owner decision is "medium or high" (`intent.md:78`). The status word is "Decided", against strategy `:75` "designed and decided; no run". The page claims no more than that.
> - **Closing line**: Table 6 `:423` gives "28 of 192 groups claim skill". The three baselines and two challengers are pinned by the test against `baselines.md` and the paper.
>
> ## Checklist
>
> 1. **Every acceptance item met by a check that was run: yes.** Every figure is read by a test from its record. No run is made. The status lines claim no more than the strategy table (verify 71 OK, rows 2 and 11-12). The copy rules hold (test plus row 11). There is no inline script or style, and the route stays classified and staged (`test_hosting_stage` in the verify). The full suite passes with every existing assertion kept (row 8).**
> 2. **Only allowed paths changed: yes.** `plan.py scope MODELS-1 7f3ad083` OK. Outside the owned paths, the only changes are `PROGRESS.md`, `reviews/MODELS-1.md` and the `tasks.json` state and note, which the scope tool admits.
> 3. **No frozen contract, acceptance text or test weakened: yes.** `tasks.json` acceptance is unchanged. The four moved pins are each at least as exact as before. No other test file changed.
> 4. **No new dependency, service, network, model or cloud effect: yes.** The page is static. `models.js` only composes the summary line and fetches nothing.
> 5. **Mode labels truthful: yes.** `synthetic_fixture` and `fixture_supplied` are shown and parsed from `systemone.py`. The footer says "No model ran for this page."
> 6. **Unknowns stay unknown, nothing invented: yes.** The Clef and two-runs sentences now say what Table 6 and §7.5 say. No figure appears without a record (the numeric sweep test passes).
> 7. **Packet records interpreter, commands, results, unfinished items, next action: partly.** Sections 0-9 carry these fields. §10 lists the fixes but no commands or results. It points to "the commit's own table", and the commit message has no table (finding R4-1).
> 8. **No contradiction with the strategy, the paper or the records: yes.** Every status word is at or below its strategy row. The two contradicted sentences are gone.
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/product-gap-2026-10-17/models-1.md` §10, last paragraph | The record says "Commands and results follow in the commit's own table". No such table exists. The rework round 2/3 is recorded with no command and no result. | `git log -1 --format=%B d57f37b2` prints only the subject line, with no body. | Add the round-4 commands and results to §10: verify 71 OK, plan check, scope, repo check, and the suite count on this tree. Or point to this review's table. |
> | minor | `models-1.md:16-18` (state paragraph) | The edit broke the inline code. "(`Ran 2433 tests … OK` at the first build, `Ran 2452 tests` after rework round 1; see §10 for the current tree\n(skipped=62)`)" leaves an unpaired backtick and an orphaned "(skipped=62)". "See §10 for the current tree" points to a section with no count. | `sed -n 16,18p` of the branch record | Rewrite the parenthesis with paired backticks and the current-tree count. |
> | minor | `models-1.md:284-286` | A fragment is left over. "…limits them to a smoke test)\n(methods section); the class sentence comes from…" keeps "(methods section)" from the old sentence. | `sed -n 284,287p` | Drop "(methods section)". |
> | minor (advisory) | `docs/work/tasks.json` MODELS-1 note; `docs/work/PROGRESS.md` | The note keeps round 1's text ("pending on the BigQuery gate", "built with no Clef call", "Ran 68", "2433") before the appended correction. PROGRESS has no log row for rounds 2/3. These are internal records, not the page. The appended sentence corrects them. | `tasks.json` note; `git diff 7f3ad083...HEAD -- docs/work/PROGRESS.md` | Optional, at merge time: the orchestrator adds a PROGRESS row for rounds 2-4 and the review outcome. |
>
> No blocking or important finding.
>
> ## Verdict
>
> **Accept.** `d57f37b2` fixes both important findings from rounds 2 and 3, in the record's own terms. "No Clef call serves the desk" is paper Table 6's "never served to the desk". "The same question set … at two cutoffs" is paper §7.5's trip and return cutoffs. The three minor page findings are also fixed: "probabilities over its options" fits `systemone.py:105`, and `gate` is gone from the page. Every moved test pin is at least as exact as before, and no assertion was removed. The brief's verify (71 OK), `plan.py check`, `plan.py scope MODELS-1 7f3ad083`, `repo.py check` and `node --check` all pass. The full offline suite passes (2452 OK, skipped=62) with the runner's ignored inputs linked. Without them, one environment-only error appears (pypdf missing). Every acceptance item is met by a check I ran. What remains are four minor record-keeping issues in the task record and the notes, not on the page. The worst is §10 pointing to a commands table that does not exist. The orchestrator can fix them at merge time, and they do not block. Only the reviewer sets `done`. The merge into main is the orchestrator's call, from `task/MODELS-1`, not from the integration branch's earlier unreviewed merge.
