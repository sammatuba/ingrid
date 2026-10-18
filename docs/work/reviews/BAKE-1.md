
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `3ebdcac5`, 2026-10-17 22:57, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # Independent review of BAKE-1: verdict accept
> 
> I reviewed `task/BAKE-1` at `3ebdcac5` against `feat/product-gap-e` at `4ce586ab`, which is also the merge base. The branch has two commits and changes 15 files. I did not write this change and I edited no files.
> 
> ## Commands I ran
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_catalog` | `Ran 249 tests` **OK (skipped=1)** |
> | Full suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2432 tests in 208.753s` **OK (skipped=62)**. One stray stdout line (`cvis-…: none (not transmittable)`) came from an existing test, not this change. |
> | `/usr/bin/python3 scripts/plan.py scope BAKE-1 feat/product-gap-e` | `OK: all changed files inside BAKE-1 allowed paths` |
> | `plan.py check` / `repo.py check` | `OK: 117 tasks, 8 gates` / **PASS** |
> | `build_all.py --check` in four combinations, with the real archive and snapshot | All four exit 0 with `violations []`, steps `build_data, build_catalog, briefs, build_assets` all 0. No views + real scorecard: views off, contract 13 files, scorecard targets 1. Views + real scorecard: views on, 15 files, targets 1. Views + no scorecard: 15 files, targets 0. No views + no scorecard: 13 files, targets 0. |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **No number without its record.** `values_block` checks the file's bytes against `values_ref.sha256` and its row count against `values_ref.rows` before it copies anything. The contract ties the block's digest to the vintage's `values_sha256`.
>    - **Real data.** Both real values files hold 744 hourly rows with no band. The real outlook record has no monthly figure, so carrying the hourly rows rather than computing a month value is the correct reading of "the month's value".
>    - **`build_all.py --check` with and without views and scorecard.** I ran all four combinations myself (table above).
>    - **Existing assertions kept, suite passes.** The only expectation that moved is the catalog file count, 13 → 16. The change is justified and the three new file names are now asserted too. The two values-file helpers write a fuller header, and no assertion was removed.
> 2. **No file outside the allowed paths: yes.** Scope against `feat/product-gap-e` prints OK. The process page still names `feat/h1-api-persistence` as the branch to check against, but the brief names `feat/product-gap-e`. `tests/test_grid_outlooks_page.py` is in the allowed paths.
> 3. **No frozen contract or acceptance text changed, no test weakened or skipped: yes.**
> 4. **No new dependency, service, credential, network call, model call or cloud effect: yes.** The bake only reads local files.
> 5. **Mode labels truthful: yes.** Every fixture answer is labelled `synthetic_fixture` and `fixture-view`, and the real values are `synthetic: false` as recorded.
> 6. **Unknowns stayed unknown, nothing invented: yes for the bake output.** The fixture receipts are partly invented; see finding 1.
> 7. **The packet records interpreter, commands, results, unfinished items and next action: yes** (sections 5–7 of the task record).
> 8. **Nothing contradicts the blueprint, strategy or invariants: yes.**
>    - The values stay out of the event view (`ValuesStayInTheIndex`).
>    - The `views/` files will be deployed and served. `stage_hosting.py` copies every baked file, and `/grid-data/{name:path}` in `src/api/__init__.py:475` is a general path route with no list of folders.
>    - The event page that gets `ask: true` is rewritten rather than copied byte for byte. The brief allows this, and the fixture `--check` reproduces it.
> 
> ## Findings
> 
> 1. **minor** | `tests/fixtures/grid/catalog/build.py:57` (`_receipt`), `tests/test_grid_data.py:282` (`plan_receipt`), `scripts/grid/build_data.py:2277-2281`
>    - **Mechanism:** the fixture plan sets are written by hand, not produced by the real composer.
>      - Each receipt has 6 of the 15 fields that `compose()` writes (`src/judgment/view.py:873-888`). The receipt component in each answer also lacks `receipt_digest`.
>      - `plan_digest` is not a digest of any plan the composer checked. In the fixture it hashes a stand-in two-key dictionary. In the tests it hashes the string `"question:status"`.
>      - The bake's receipt check only requires `receipt.view_version`, so these partial receipts pass.
>      - VIEW-1 would then be built and tested against receipts that real recorded plan sets will not look like. This goes against the project's rule that page fixtures come from the real function.
>    - **Evidence:** compare `tests/fixtures/grid/catalog/bake/views/home.json` with `view.py:873-909`.
>    - **Correction:** produce the fixture plan sets through `view.compose()` with `FixtureView`, as `tests/test_judgment_view.py` already does offline. Optionally, make the bake check that the receipt has the composer's full field set. This can be VIEW-1's first step.
> 2. **minor** | `scripts/grid/build_data.py:1521`
>    - **Mechanism:** `source = record["input"]` raises `KeyError` when a values file has no `input`. `input` is not in the list of header fields checked just before, and `main` only catches `BuildInputError`. The build therefore crashes with a traceback instead of a named error and exit 2.
>    - **Correction:** use `record.get("input")`, so the existing named refusal handles it.
> 3. **minor** | `scripts/grid/build_data.py:1486`
>    - **Mechanism:** the bake now requires 11 header text fields plus `input`. The values-file rules in `src/outlook/scoring.py:37-45` and `228-273` require only `series` and `hours`. A file DESK-6 accepted, such as `{'series', 'hours': []}`, now stops the whole bake. Two test helpers had to be widened for exactly this reason (`test_grid_outlooks_page.py:218`, `test_grid_data.py:231`).
>    - **Impact today:** none, because both real files state all the fields.
>    - **Correction:** state this stricter rule in the task record as a precondition of the bake, or leave out the `values` block (instead of stopping the build) when a header field is missing.
> 4. **minor** | `scripts/grid/build_data.py:1535` / `1565`
>    - **Mechanism:** a `values` block with an empty `hours` list passes the contract, while `scoring.py:271` treats zero rows as a malformed file. The `test_grid_outlooks_page` helper now bakes exactly that case.
>    - **Correction:** refuse an empty `hours` list in `values_block` and in `values_block_problems`, or record why zero rows are allowed.
> 
> A note for OUTLOOK-7, not a finding: with the hourly rows, the real `outlook/index.json` grows from about 6 KB to about 94 KB for two vintages, and it grows by about 44 KB for each further vintage.
> 
> ## Verdict
> 
> **Accept.** I demonstrated every acceptance item myself (verify, full suite, scope and the four `--check` combinations), and the four findings are minor and do not affect the bake's output.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
