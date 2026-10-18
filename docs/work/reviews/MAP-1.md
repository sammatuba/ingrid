
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `1b67f397`, 2026-10-18 00:22, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> ## MAP-1 review: verdict **rework**
> 
> I reviewed `task/MAP-1` at `1b67f397` (commits `a7796689` and `1b67f397`) against `feat/product-gap-e`. This review was independent and read-only, and I edited no files.
> 
> **What I ran:**
> - **Verify command** (`/usr/bin/python3 -m unittest tests.test_grid_map_page tests.test_hosting_stage`): `Ran 73 tests in 4.067s`, **OK**.
> - **Full offline suite** (`/usr/bin/python3 -m unittest discover -s tests`): `Ran 2511 tests in 270.823s`, **OK (skipped=62)**, exit 0. The browser classes skipped by design. The trailing `cvis-…` stdout line is the known one and does not affect the result.
> - **`/usr/bin/python3 scripts/plan.py scope MAP-1 feat/product-gap-e`**: `OK: all changed files inside MAP-1 allowed paths`.
> - **`plan.py check`**: `OK: 117 tasks, 8 gates`. **`repo.py check`**: **PASS** (573 Markdown files, 3676 links).
> 
> ### Checklist
> 1. **Every acceptance item met by a check that was run: no.**
>    - **Snapshot line: met.** The page says "Snapshot of main at 8d0bd5ec." in the top line, where the owner's map says it, and the full commit is in the page details. The only newer claims are batch release 8 (`PROGRESS.md:603` names `grid-nowcast-00024-cnz`) and the contract cells, and each names its record.
>    - **No inline script or style: met.** The page has no `<style>`, no `style=` and no `on*=` handler. Its one script is `ask.js`. The full suite is green.
>    - **Figures: met.** Every figure has its record and date. I traced the records myself: register 82/4,154/40,108,160,699; the data-organization record's 63 months and 184,036 rows; the constraint record's 31 of 31; register.md's 42/40 at 2026-10-16.
>    - **Status words: met.** They are never stronger than the record's. All 72 cells equal the JSON, and the one prose status word matches `capability-map.md:19`.
>    - **Copy rules 1 to 7: not met.** See finding 1.
> 2. **No file outside allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - The diff touches only the page, the builder, the CSS, the new test and the coordination files.
>    - Removing the `map.js` script tag breaks no pin; the full suite is green.
>    - That reading is sound: `routes-1.md:23` says ATG-6's canvas owns `map.js`, and `/map` mounts no canvas.
> 4. **No new dependency, service, network or model call: yes.** The builder is standard-library Python and runs offline.
> 5. **Mode labels truthful: yes.** Q10 keeps the synthetic label, and the page says it reads no data when it opens, which is true of a baked page.
> 6. **Unknowns stayed unknown: yes.** No figure lacks a record string.
> 7. **Packet records commands, results and next action: yes, with commit-id drift** (finding 4).
> 8. **No contradiction with strategy, paper or invariants: yes.**
> 
> ### Findings
> 1. **important** | `tests/test_grid_map_page.py:427-472`, `src/grid/map.html:151-152`, `src/grid/map.html:52-54`, `docs/work/product-gap-2026-10-17/map-1.md:122`
>    - **Failure mechanism:** the project reads "copy rules 1 to 7" as the strategy refresh's seven rules (`strategy-refresh-2026-10-14/strategy.md:48-55`). The MODELS-1 review set that reading and gave rework for this same pattern (`reviews/MODELS-1.md:27`). `TheCopyRules` tests only the brief's four examples in brackets, yet the packet marks the item "Met".
>    - **Evidence, rule 5 (labels of at most three words):** two metric labels break it. "Market factors in the domain watch list" has 7 words and "Desk questions, Q1 to Q12" has 5.
>    - **Evidence, rule 3 (no slogans, no hero headline, no all-caps eyebrow taglines):**
>      - `<h1>From market signals to accountable decisions.</h1>` is a slogan in a hero block.
>      - The eyebrow tagline `<p class="mp-eyebrow">Current project map / integrated review</p>` is set in capitals by CSS (`map.css`, `.mp-eyebrow { text-transform: uppercase }`).
>      - The sibling pages in the site's style carry plain titles: `register.html:42` "Assumption register" and `work.html:41` "The future of work case".
>      - Small uppercase labels do exist in `register.css:25,51`, so the section-number and card labels are closer to the site's style. The hero headline and the tagline are not.
>    - **Correction:**
>      - Cut the two labels to three words or fewer and move the qualifier into the card text, for example "Market factors" with "in the domain watch list" beside it, and "Desk questions" with "Q1 to Q12".
>      - Make the h1 a plain title (for example "Project map") and keep the owner's line as body text, or drop the uppercase tagline.
>      - Add a label-length test and a rule 3 test to `TheCopyRules`.
>      - Mark the item in §6 against all seven rules. On rule 1, use the DESK-5 reading: the record's as-of date supplies the time.
> 2. **minor** | `src/grid/map.css:35` together with `scripts/grid/build_map_page.py:67-71`
>    - **Failure mechanism:** the hero rule `.mp-meta { display: flex; flex-wrap: wrap; gap: 4px 22px }` also applies to the contract cells' `<p class="mp-meta">`, and `.mp-contract .mp-meta` does not override `display`.
>    - **Evidence:** each "Surface: / Record: / Status:" line becomes a flex row. Its text, the `<span class="mono">` and the closing "." are split into separate items with 22 px gaps and can wrap apart in a 172 px cell. I have this from reading the stylesheet; I did not view it in a browser.
>    - **Correction:** rename the cell class (for example `mp-cellmeta`) in the builder and the CSS, or set `display: block` on `.mp-contract .mp-meta`.
> 3. **minor (advisory)** | `src/grid/map.html:266`, `src/grid/map.html:268`
>    - **Failure mechanism:** the page's own prose uses two words on the project's banned list (`docs/routes.json`): "rendered" (use "draw") and "revision" (use "version").
>    - **Evidence:** `/map` is not on that list, so the check does not run on it, and MODELS-1 treated this as advisory. The other hits ("digest", "disposition", "ontology") come from the contract JSON or from record paths, not from this task.
>    - **Correction:** reword those two sentences.
> 4. **minor** | `docs/work/product-gap-2026-10-17/map-1.md:3,173-188` and the MAP-1 log row at `docs/work/PROGRESS.md:621`
>    - **Failure mechanism:** the packet cites commit `faa06d5` and base `4ce586ab`. The branch is `a7796689` and `1b67f397` on `5a43d567`, with WORK-1 merged beneath it.
>    - **Evidence:** the packet's suite count of 2438 was measured on the old base. This review measured 2511 on the current one.
>    - **Correction:** cite the branch's own commits and base, and quote the suite count against `5a43d567`.
> 5. **minor** | `src/grid/map.html:171`, `src/grid/map.html:223`
>    - **Failure mechanism:** two of the owner's sentences changed meaning.
>    - **Evidence:** "an essential mechanism" became "the central mechanism", which is stronger than the owner's map. "Disposition and impact record structure" became "Decision and impact record structures".
>    - **Correction:** restore "an essential mechanism". The second change follows the banned-word list, so record that reason in §2.
> 
> **Verdict: rework.** One acceptance item, copy rules 1 to 7, is marked "Met" but was not demonstrated: two labels break rule 5 and the hero headline breaks rule 3. Every fix is inside the allowed paths and none needs a contract or intent change.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `af50bfdf`, 2026-10-18 00:40, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # MAP-1 review, round 2: verdict **accept**
> 
> I reviewed `task/MAP-1` at `af50bfdf` against `feat/product-gap-e` at `5a43d567`. The branch has five commits: `a7796689`, `1b67f397`, `839dd884` (the runner's review record), `9a23839d` (the rework) and `af50bfdf` (evidence only). The review was independent and read-only, and I edited no files.
> 
> ## What I ran
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_map_page tests.test_hosting_stage` | `Ran 79 tests in 2.026s` **OK** |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2517 tests in 206.712s` **OK (skipped=62)**, exit 0. The browser classes skipped by design. The trailing `cvis-…` line is the known stdout line. |
> | `/usr/bin/python3 scripts/plan.py scope MAP-1 feat/product-gap-e` | `OK: all changed files inside MAP-1 allowed paths` |
> | `/usr/bin/python3 scripts/grid/build_map_page.py --check` | `the map page carries a fresh render of the integration contract` |
> | `plan.py check` / `repo.py check` | `OK: 117 tasks, 8 gates` / **PASS** (574 Markdown files, 3682 links) |
> 
> I could not run the browser probe (packet R8) because this environment has no browser. That evidence is the author's own.
> 
> ## Checklist
> 
> 1. **Every acceptance item is met by a check that ran: yes.**
>    - **Snapshot line:** the mast at `map.html:49` reads "Snapshot of main at 8d0bd5ec.", where the owner's map puts it. The full commit stands at `:59`.
>    - **Nothing newer than the snapshot:** a test parses every ISO and written date on the page and finds none after 2026-10-17. The one later claim, batch release 8 / `grid-nowcast-00024-cnz`, names its record, `PROGRESS.md`.
>    - **Figures:** a test checks all 16 figure spans against each record's own words. I spot-traced 251,623 (`grid-constraints/record.md:48`), 31 of 31 (`:111`), 184,036 (`data-organization…/record.md:56`), "2021-07 to 2026-09" (`:29`), "twelve user stories" (paper `:444`), "2 outlooks" (refresh record `:70`) and the issue on 2026-10-16 (`:55,63`). All match.
>    - **Status words:** all 72 contract cells equal the JSON. The only prose ladder word is "selected design", and a test ties it to the capability map's Generated-view row.
>    - **Copy rules 1 to 7:** read as the strategy refresh's seven rules (`strategy-refresh-2026-10-14/strategy.md:48-55`). Tests cover rules 2 to 7 and the four word rules. Rule 1 has no test. It follows the established DESK-5 reading, where the record's as-of date supplies the time (`reviews/MODELS-1.md:94`, `price-outlook/desk-5.md:126`). Round 1 directed that reading.
>    - **No inline script or style:** tests find no `<style>`, no `style=`, no `on*=` handler and no Print button. The page loads one external script, `ask.js`.
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK, and `scripts/grid/` is in the allowed paths for the builder.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - The change set is three modified files (PROGRESS, tasks.json, map.css/html) and new files only: the builder, the new test and the packet.
>    - No existing test file changed.
>    - `reviews/MAP-1.md` was touched only by the runner's `839dd884`.
> 4. **No new dependency, service, network, model or cloud call: yes.** The builder uses only the standard library and runs offline.
> 5. **Mode labels are truthful: yes.** The caption line says "The PEDC case is real data." and labels the portfolio exposure synthetic. Q10 keeps "with synthetic labels".
> 6. **Unknowns stayed unknown: yes.** Every figure carries a record and a date. The contract's "missing" cells keep their reasons.
> 7. **The packet records interpreter, commands, results, unfinished items and next action: yes.** One count is out of date (finding 1).
> 8. **No contradiction with strategy, paper or invariants: yes.** On `map.js`: the Outputs line names it, but `routes-1.md:23` records `map.js` as ATG-6's canvas. `/map` mounts no canvas, so leaving the file alone and dropping its `<script>` tag is sound (n.a. for this page).
> 
> ## Round-1 findings
> 
> All five are fixed:
> 1. **Title, tagline and labels:** the title is now `Project map`, the eyebrow and its CSS rule are gone, and the labels are three words or fewer. Two new tests hold this.
> 2. **Cell layout:** the builder writes a separate `mp-cellmeta` class with `display: block`, and a test pins it.
> 3. **Banned words:** "rendered" became "drawn" and "revision" became "version".
> 4. **Commit ids:** the packet now cites the branch's real commits and base.
> 5. **Wording:** "an essential mechanism" is back at `map.html:170`, and §2 records the "Disposition" change with its reason.
> 
> ## Findings
> 
> 1. **minor** | `docs/work/product-gap-2026-10-17/map-1.md:23`
>    - **Failure mechanism:** the packet still says "22 tests" after the rework.
>    - **Evidence:** the module now holds 28 tests (12 + 8 + 8), and §10 R2 itself says 28.
>    - **Correction:** change the count to 28.
> 2. **minor** | `src/grid/map.html:331-343` (section 07) and `map-1.md:124`
>    - **Failure mechanism:** the packet says "Section 07 lists every record", but the source trail leaves one out.
>    - **Evidence:** the paper record behind the "twelve" stories figure (`docs/product/paper-accountable-ai-decisions-2026-10-17.md`) is missing from the list. So is the theoretical-foundation record that the owner's trail listed for Workstream B. The figure span itself still names the paper.
>    - **Correction:** add both records to the list, or soften the packet's sentence.
> 3. **minor (advisory)** | `src/grid/map.html:54`
>    - **Failure mechanism:** the owner's slogan "From market signals to accountable decisions." survives as the lead's first sentence. Rule 3 bans slogans wherever they stand, and the fragment carries no entity or time for rule 1.
>    - **Evidence:** round 1's correction explicitly allowed keeping the line as body text, so this is not grounds for rework.
>    - **Correction:** optional. Drop it, or join it to the next sentence.
> 
> **Verdict: accept.** All three acceptance items are shown by checks I ran: verify 79 OK, the full suite 2517 OK (skipped=62), scope OK and the builder check clean. Every round-1 correction is inside the allowed paths, and what remains is minor.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
