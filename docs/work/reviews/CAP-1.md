
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `68da3e59`, 2026-10-17 21:07, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # CAP-1 review: verdict **rework**
> 
> I reviewed commit `68da3e59` (one commit on `task/CAP-1`) against base `feat/product-gap-c` (`d89c83ac`). I am independent and did not write this change. I edited no files.
> 
> ## Commands run
> - **Verify:** `/usr/bin/python3 -m unittest tests.test_integration_contract` → `Ran 31 tests in 0.007s` · **OK**
> - **Scope:** `/usr/bin/python3 scripts/plan.py scope CAP-1 feat/product-gap-c` → `OK: all changed files inside CAP-1 allowed paths`
> - **Full suite:** `/usr/bin/python3 -m unittest discover -s tests` → `Ran 2217 tests in 163.052s` · **FAILED (errors=1, skipped=58)**. The error is `setUpClass (test_grid_page.BrowserPage)`: `JSONDecodeError … (char 64847)`.
>   - The browser class ran here instead of skipping, and the harness output was cut at 64 KB. The packet records the same error.
>   - CAP-1 touches no file under `src/grid/`, `tests/test_grid_page.py` or `tests/fixtures/grid/page/`, so this error came from before the change. The suite still did not pass on this tree, so I do not count that acceptance item as met.
> 
> ## Checklist
> 1. **Every acceptance item met by a check that ran: no.** The rule "status words never stronger than the record's" fails twelve times (finding 1). The full suite does not end OK.
> 2. **No file outside the allowed paths: yes.** Scope printed OK. The diff has the 4 new outputs, the packet, and one row each in tasks.json and PROGRESS.md.
> 3. **No frozen contract, acceptance text or test weakened: yes.** In tasks.json only the `note` and `state` fields changed. No existing test was changed.
> 4. **No new dependency, service, network or model call: yes.** The diff is documents plus a test that uses only the standard library.
> 5. **Mode labels truthful: no.** "deployed" is given to paper content that only the repository holds (finding 1).
> 6. **Unknowns stayed unknown: no.** The Q12 answer claims bands that the page does not draw (finding 2). The figures I checked do trace to their records:
>    - "40 of 42" unowned rows → `docs/work/outlook-archive/register.md:258-259` (ARCH-3 addendum), not copied from the owner's map.
>    - 2026-11 → 2026-12 → `first-outlook.md:231`.
>    - The Q4 and Q6 "no row" answers are true: `register.json` has 42 rows and none for a transfer limit or a fuel price.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** See `cap-1.md` §5, §6 and §8.
> 8. **No contradiction with the blueprint or strategy: no, except finding 1.** The capability map exists to keep "in the repository" apart from "deployed", and finding 1 merges the two.
> 
> ## Findings
> 1. **Blocking** | `docs/product/integration-contract.json:27` (and the same `asked` cell at :75, :123, … :555), `docs/product/integration-contract.md:18-29,33`, `docs/work/product-gap-2026-10-17/cap-1.md:43`
>    - **Failure:** All twelve `asked` answers say "Surface: /paper. Status: deployed. Record: docs/work/PROGRESS.md". The released revision does not show the desk questions.
>    - **Evidence:**
>      - Release 7 (`PROGRESS.md:596`, "Deploy now, paper later") baked origin/main `fd750b5` as `grid-nowcast-00019-rpg`.
>      - `/paper` is built from `docs/product/paper-accountable-ai-decisions-2026-10-17.md` (`scripts/docs/build_paper.py:26`).
>      - `git show fd750b5:<that file>` has no `Q\d+` token. It has none of the phrasings "Why is the price", "happening now" or "known then".
>      - The Q1–Q12 table arrives in `17d0cd3b`, which postdates the release and is still in the batch-one deploy that waits on the owner.
>      - The test let this through. `test_deployed_rests_on_the_release_record_that_names_the_revision` (`tests/test_integration_contract.py:206`) only checks that PROGRESS.md contains some "Batch release" line and some revision string. It never checks that the release shows the claimed surface.
>    - **Correction:**
>      - Set the twelve `asked` answers to `selected design`, with record `docs/work/product-shape-2026-10-17/strategy.md` (its rows 169–180 define Q1–Q12). Rewrite md:33 and cap-1.md:43 to match.
>      - Raise them to `deployed` only after a release line names a revision baked from a commit that has the table.
>      - Make the test tie each `deployed` answer to a named release commit. Do this for the deployed answers in general, not only these twelve.
> 2. **Important** | `docs/product/integration-contract.json:575` (Q12 `forecast_and_exposure`)
>    - **Failure:** The answer "The issued versions carry their horizons and bands" is marked `/outlooks` · deployed. The page draws horizon, cutoff, digests, inputs, assumptions and receipts, but no band.
>    - **Evidence:** Neither `fd750b5:src/grid/outlooks.js` nor HEAD's `outlooks.js`/`outlooks.html` contains band, quantile, p10 or p90. The vintage renderer prints only `values_sha256`.
>    - **Correction:** State only what the page shows (horizons and the values digest). Otherwise point the bands at the record that holds them, at the rung that record supports.
> 3. **Minor** | `docs/product/capability-map.md:26` (Hosting)
>    - **Failure:** "recorded run" and "deployed" both rest on `docs/work/PROGRESS.md`, so the map does not separate these two steps for this row.
>    - **Correction:** Name a separate recorded-run record, or say in the Note that the release log serves as both.
> 
> Things I checked that hold up:
> - The deployed `event.js` carries register, impact, decision and advisory content. That backs the "deployed" ticks for the Signal, Belief, Impact and Decision rows, and Q5's `/outlooks` answer.
> - `docs/status.md` and `docs/START-HERE.md` are untouched.
> - The JSON holds no numeric value.
> 
> **Verdict: rework.** Twelve `deployed` status words rest on a paper page that the released revision does not carry, and the Q12 answer claims bands that the outlooks page does not draw. Both break the rule that a status word is never stronger than its record.
> 
> Separate from this task, the orchestrator still needs to fix the 64 KB cut in `tests/fixtures/grid/page/browser.mjs` (packet §6) before a full suite can pass.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `0cc630a7`, 2026-10-17 21:31, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # CAP-1 review, round 2: verdict **accept**
> 
> I'm an independent reviewer and did not write this change. I edited no files.
> 
> **What I reviewed:** commit `0cc630a7` on `task/CAP-1`, against base `feat/product-gap-c` = `73a9fc44`. The branch has three commits: `611746f5` (the build), `00f4d6c3` (round-1 review record) and `0cc630a7` (the rework). The packet names `d89c83ac` as its base. The branch was rebased since then; I'm recording that drift, not counting it as a defect.
> 
> ## Commands run
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_integration_contract` | `Ran 35 tests in 0.037s` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope CAP-1 feat/product-gap-c` | `OK: all changed files inside CAP-1 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | `PASS` (550 Markdown files, 3582 local links, 5 skills, bootstrap 1400 words) |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2311 tests in 222.474s` · **OK (skipped=62)**, exit 0. The browser classes skip by design here. The base `73a9fc44` already carries the harness flush fix. |
> 
> ## Checklist
> 1. **Every acceptance item met by a check that ran: yes.**
>    - **No figure copied from the owner's map:** the `NoFigures` tests pass. The JSON holds no numbers. The one figure that matches the owner's map, "40 of 42", comes from `docs/work/outlook-archive/register.md:258-259` (the ARCH-3 addendum: `records` 42, `unowned` 40, dated 2026-10-16).
>    - **Every status word has its record beside it:** checked by the `StatusBacking` tests and by the Markdown test that matches each `Status: … Record: …` pair.
>    - **`deployed` only where a release record names the revision:** the last batch-release line (`PROGRESS.md:596`) names commit `fd750b5` and revision `grid-nowcast-00019-rpg`. I checked all six `deployed` claims at `fd750b5` myself:
>      - `outlooks.js` draws `cutoff ${…}`, the `Assumptions` heading and `horizon` changes.
>      - `index.html` has a `Reserve` column header.
>    - **Copy rules:** I checked the set the brief itself names in its parenthetical (sentences under 20 words, active voice, no semicolons, no "stale"). The `CopyRules` tests pass and `repo.py check` passes.
>    - **The test passes and the full offline suite passes:** both shown above.
>    - **`docs/status.md` and `docs/START-HERE.md` untouched:** neither is in the diff stat.
> 2. **No file outside the allowed paths: yes.** Scope printed OK. The diff touches 8 files, all on the brief's allowed list.
> 3. **No frozen contract, acceptance text or test changed or weakened: yes.** In `tasks.json` only `note` and `state` changed. No existing test was changed.
> 4. **No new dependency, service, network or model call: yes.** The diff is documents plus a standard-library test. Its only subprocess is a local `git cat-file` or `git show`.
> 5. **Mode labels truthful: yes.**
>    - Round 1's twelve `asked` answers are now `selected design`, resting on `docs/work/product-shape-2026-10-17/strategy.md:169-180`, which defines Q1 to Q12.
>    - Q10 keeps "synthetic book".
>    - Generated view ticks only selected design, which matches the owner's "designed direction only".
> 6. **Unknowns stayed unknown: yes.** I traced the absence claims myself:
>    - Q12 authority: `first-outlook.md:365-367` says no analyst or owner accepted the outlook.
>    - Q9 authority: `docs/cases/pedc-u2-2026-09-21/review.md:3` says the case records no disposition.
>    - Q12 no longer claims bands. `outlooks.js` at `fd750b5` has no band or quantile.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** See `cap-1.md` §5, §8 and §9. The suite counts there are out of date for this base (finding 3).
> 8. **No contradiction with blueprint, strategy or working paper: yes.** The map keeps "in the repository" apart from "deployed", as the owner's map asks.
> 
> ## Round-1 findings
> - **Finding 1 (blocking): fixed.** The `asked` answers are now `selected design`. A new test, `DeployedReleases`, ties every `deployed` answer to the release commit. I confirmed independently that the paper at `fd750b5` has no `Q1` token.
> - **Finding 2 (important): fixed.** Q12 now claims horizons, cutoffs and digests, not bands.
> - **Finding 3 (minor): fixed.** The hosting Note now says the release log serves as both its recorded run and its deployed record.
> 
> ## Findings
> All four are **minor**.
> 
> 1. **`docs/product/capability-map.md:21` (Data catalog)**
>    - **Failure:** the Note says "The release serves the data and assets pages (release record, 2026-10-17)". No 2026-10-17 release line checks those routes.
>    - **Evidence:** releases 5, 6 and 7 (`PROGRESS.md:591`, `:592`, `:596`) do not name `/data` or `/assets`. Only release 4 (`PROGRESS.md:578`, 2026-10-16) does. The `deployed` tick itself is believable: `catalog.html` is in the `fd750b5` tree, and `/data` and `/assets` are in `SITE_ROUTES` at that commit. The date and record attribution are what's wrong.
>    - **Correction:** cite release 4 (2026-10-16) for the live check. The map's `deployed` ticks are not checked against the release commit the way the contract's are, so a follow-up could add that check.
> 2. **`docs/product/integration-contract.json:288` (Q6 forecast and exposure)**
>    - **Failure:** the finding says "…and the public page withholds the fuel series". It is marked `/outlooks`, `deployed`, record `PROGRESS.md`. Neither that page nor that record states the withholding.
>    - **Evidence:** `outlooks.js` at `fd750b5` contains no fuel, coal or LNG word. The withholding rule is owner decision 3 in `docs/work/product-shape-2026-10-17/strategy.md:105` and `:174`.
>    - **Correction:** drop the clause, or give it its own answer that rests on the product-shape record.
> 3. **`docs/work/product-gap-2026-10-17/cap-1.md` §4, §6, §8 and §9; the `tasks.json` CAP-1 `note`**
>    - **Failure:** both still say the full suite carries one browser `setUpClass` error, with "2217 OK with the class excluded". They also name the base as `d89c83ac`.
>    - **Evidence:** this tree sits on `73a9fc44`, the harness flush fix. The suite here reads `Ran 2311 … OK (skipped=62)`.
>    - **Correction:** add one line saying the old count is superseded on base `73a9fc44`, with the passing run. Don't rewrite the history.
> 4. **`tests/test_integration_contract.py:325-328`; `docs/product/integration-contract.md:7`**
>    - **Failure, test:** the `shows` check looks for the word anywhere in the route's source file. A code comment can satisfy it. At `fd750b5`, the first `assumption` hit in `outlooks.js` is a comment. The claims still hold only because I checked the rendered strings by hand.
>    - **Failure, page:** line 7 says "the ladder above", but the ladder is listed below it, at line 11.
>    - **Correction:** match the rendered strings in the test, such as the `ol-sub` labels or the `<th>` text. Change "above" to "below".
> 
> **Verdict: accept.** Every acceptance item was shown by a check I ran, round 1's blocking and important findings are fixed, and the four remaining findings are minor.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
