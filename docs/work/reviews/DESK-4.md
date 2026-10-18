
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `b0cd4208`, 2026-10-17 14:42, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # Review: DESK-4 — **Verdict: rework**
> 
> I read `git log feat/product-refine..HEAD` (bc592daf and b0cd4208) and `git diff feat/product-refine...HEAD` (12 files, +1339/−29). I edited no files. My only scratch output went to `/tmp`.
> 
> ## Commands run
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_event` (verify) | `Ran 222 tests in 5.928s` · **OK (skipped=3)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-4 feat/product-refine` | `OK: all changed files inside DESK-4 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 2021 tests in 173.094s` · **OK (skipped=47)** |
> | Fresh real bakes into `/tmp/desk4-rv-with` (default `--impact`) and `/tmp/desk4-rv-without` (`--impact` set to a missing file), each a write then `build_all.py --check` | all four runs exit 0 with `violations []`. The impact key is present in the first bake and absent in the second. `events/pedc-u2-2026-09-21.json` is identical between the two bakes and identical to `.local/grid-snapshot/events/`. The outlook view minus `impact` is equal across the two bakes. |
> | Real record digest | `01fd5206…e95072`; threshold 1000000.0 `at_or_above`; 19468 / 82080 / 12 |
> 
> I did not run `test_grid_page` in a browser. The executor's 390/1280 browser run is their claim (packet §6), not something I verified.
> 
> ## Checklist
> 1. **Every acceptance item met by a check that was run — no.** Most items are shown: the digest is on every sentence, the key sets are exact, there are no volumes or prices in the bytes, the card is hidden when the record is absent, there is no route, `events` are byte-identical, and the fresh bakes pass both ways. One item fails: "the materiality line … in the record's own words". The comparator phrase is page text, not taken from the record (finding 1).
> 2. **Allowed paths — yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened — yes.** The only removed lines in the test diff are function signatures and argument lists that gained an `impact` parameter. No assertion was deleted.
> 4. **No new dependency, network, model or cloud call — yes.** The only new import is the in-repo `src.price.impact`.
> 5. **Mode labels truthful — yes.** The record's own synthetic label is printed in words, and the builder refuses any record that is not synthetic.
> 6. **Unknowns stayed unknown — no (one branch).** The load-node branch states a "no" that cannot be known (finding 2). The PEDC answer itself is correct: the bake's `sites.json` has `08PEDC` as `k: "G"`.
> 7. **Packet records interpreter, commands, results, unfinished items and next action — yes.** There are small inaccuracies (finding 4).
> 8. **No contradiction of the blueprint, strategy or invariants — yes, apart from finding 1.**
> 
> ## Findings
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/grid/event.js:354` | The words "a change at or above" are hard-coded. Both the builder (`build_data.py`, `impact_record_problems`) and the contract (`impact_problems`) accept `comparator: "above"`. | A record that passes the contract with `"above"` renders "a change at or above 1,000,000 PHP is material (comparator above)". That sentence contradicts itself and does not follow the record. It reads correctly on the real record only because the current policy happens to be `at_or_above`. DESK-2 was sent back for this same kind of defect (an input the code accepts but no test exercises). | Build the phrase from `m.comparator` ("at or above" / "above"), or drop the paraphrase and let the comparator and rule speak. Add a test with `"above"`. Also drop the "Materiality stated first:" prefix: it is page prose about ordering, not a record field (copy rule 3). |
> | important | `scripts/grid/build_data.py:1045` | An `NL` site gets the statement "is a load-node site; the impact record names its portfolio nodes by alias only, so this event's unit is not a portfolio node". | The aliases are de-identified load nodes, so a load-node site may be one of them. The honest answer is that it cannot be told from the record. Stating "no" invents an answer (checklist 6; the brief says "no invented link"). The PEDC case never reaches this branch, and no test covers it. | For a load-node site, say it cannot be told whether the site is one of the aliased nodes, and set `portfolio_node` to unknown (or null) rather than `False`. Add a test for the branch. |
> | minor | `tests/test_grid_data.py:1505` | The "plain" sub-run leaves out `--impact`, so a unit test reads the default `.local/price/impact.json`. | The test passes whether or not the file exists, and its result depends on the machine. That goes against the never-read-`.local/` convention in `fixture_args`. The hidden bake that follows is written but never `--check`ed. | Pass an explicit missing path and run `--check` on the hidden bake. |
> | minor | `docs/work/price-outlook/desk-4.md:202,204` | Two packet claims overstate what was run. | Row 202 `--check`s a bake that was written *with* the record, using a missing `--impact`, and calls it "the fresh bake without an impact file". Row 204 says the test runs "`--check` both ways", but its no-impact bake is never checked. My own `/tmp` bakes do cover both readings. | Restate the rows to match what ran, or rerun them as described. |
> 
> **Verdict: rework.** The impact card's first sentence ignores the record's comparator, so it is not in "the record's own words" for a record the contract accepts, and the load-node branch asserts a "no" it cannot know. Both are small fixes inside the allowed paths, and everything else (counts, digest, hiding, routes, byte-identity, suite) checks out.
> 
> The second monitor finished with the same full-suite result the review already uses (`Ran 2021 tests in 173.094s`, OK with 47 skipped). Nothing changes: the verdict is still **rework**, for the comparator wording at `src/grid/event.js:354` and the load-node "no" at `scripts/grid/build_data.py:1045`.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `92098b1f`, 2026-10-17 15:02, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # Review: DESK-4 (round 2, commit `92098b1f`), verdict **accept**
> 
> I did not author this change and I edited no files. I read `git log feat/product-refine..HEAD` (4 commits) and `git diff feat/product-refine...HEAD` (13 files, +1576/−29), including the round-1 review record. Scratch bakes went to a Python `tempfile` directory only.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_event` (verify) | `Ran 224 tests in 7.179s` · **OK (skipped=3)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-4 feat/product-refine` | `OK: all changed files inside DESK-4 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 100 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (509 Markdown files, 3426 local links, bootstrap 1399 words) |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 2023 tests in 181.786s` · **OK (skipped=47)** |
> | The DESK-4 classes by name, verbose (`RenderedImpactOnTheRealRecord`, `RenderedImpactWithTheAboveComparator`, `RealImpactRecord`, `ImpactInput`, the BuildAll with/without test) | 17 tests, all **ok**. They ran under node and were not skipped. |
> | Fresh real bakes into a temporary `--data`: one with the default `--impact`, one with an explicit missing path; each written, then `--check`ed | All four runs exit 0 with `violations []`. The first bake has the `impact` key, the second does not. The outlook view minus `impact` is identical across the two. `events/pedc-u2-2026-09-21.json` is the same bytes in both bakes and in `.local/grid-snapshot/events/`. The baked view contains no `contract_price`, `uncovered` or `method_demonstration`, and the impact block contains no `region`. |
> | Real record | sha256 `01fd5206…e95072`; threshold 1000000.0 `at_or_above`; 19468 of 82080 in 12 nodes; unit `08PEDC` generator, `portfolio_node: false` |
> 
> No browser in this environment: the browser test classes skip by design. The 390/1280 browser run is in the executor's packet (§6) only; I did not repeat it.
> 
> ## Round-1 findings, re-checked
> - **Comparator (important): fixed.** The sentence now takes its words from `m.comparator` via `COMPARATOR_WORDS` (`src/grid/event.js:772-784`), and the "Materiality stated first:" prefix is gone. `RenderedImpactWithTheAboveComparator` builds an `above` record through the real `build_impact_record`, bakes it and renders it, and it passes.
> - **Load-node "no" (important): fixed.** At `scripts/grid/build_data.py`, `unit_membership` now returns `portfolio_node: null` and "cannot be told from the record" for a load-node site, a site of unknown kind and an event with no site. The contract accepts null and refuses any other non-boolean, and a test covers each of the three cases.
> - **Machine-dependent BuildAll test (minor): fixed.** It now passes an explicit missing path, and the hidden bake is `--check`ed.
> - **Packet rows (minor): fixed.** §6 is restated to what actually ran, and §9 records the corrected runs.
> 
> ## Checklist
> 1. **Every acceptance item met by a check that was run: yes.**
>    - Every sentence cites the digest: `RenderedImpactOnTheRealRecord` checks this.
>    - Exact key sets at every level, and a scan for forbidden fields.
>    - The line comes before the counts, both in the block's key order and in the DOM order.
>    - The comparator and rule are the record's own words; the label is in words, not a badge.
>    - The card is hidden when the record is absent (fixture renders and absent-key tests).
>    - No route added, and `tests/test_cache_headers.py` is untouched.
>    - `events` files are byte-identical, and the record is read, never written (digest checked before and after).
>    - The real figures are asserted, and the fresh `build_all --check` passes with and without the record (my run).
> 2. **Allowed paths: yes.** `plan.py scope` printed OK.
> 3. **Frozen contracts, acceptance text, tests: yes, all unchanged.** The only removed lines in `tests/` are three function signatures, their argument lists and one comment, each extended for `impact`. No assertion was removed.
> 4. **No new dependency, network, model or cloud call: yes.** The only new import is the in-repo `src.price.impact` (and `src.price.scorecard` in the tests).
> 5. **Mode labels truthful: yes.** The builder refuses any record that is not `synthetic: true`. The card prints the record's own label: "method demonstration on the synthetic portfolio … never a business number".
> 6. **Unknowns stayed unknown: yes.** A load-node site or an unknown kind gives null with "cannot be told". The PEDC "no" rests on the bake's `k: G` and on `src/price/impact.py:11,226`, which says the nodes are load nodes.
> 7. **Packet complete: yes.** It records the interpreter, the commands, the results, unfinished items and the next action (§6, §8, §9).
> 8. **No contradiction of the blueprint, strategy or invariants: yes.**
> 
> ## Findings
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/price-outlook/desk-4.md:289,299` | The quoted sentences put the comparator in backticks, which the page does not render. | The rendered text is `(comparator at_or_above)` (the test at `tests/test_grid_event.py` pins it without backticks). | Quote the rendered text exactly, without the backticks. |
> | minor | `src/grid/event.js:785` | The "of 12 portfolio nodes" total is `nodes.length`, not a field of the record. | It matches the record's 12 node blocks. The packet discloses this in §7. | None required. A later task could bake an explicit node count if one is wanted. |
> | minor | `scripts/grid/build_data.py` `unit_membership`, generator branch | "the portfolio's nodes are load nodes" is page text, not a record field. | The brief and the impact module's docstring (`src/price/impact.py:11,226`) back it, so nothing is invented. | None required. |
> 
> **Verdict: accept.** Both important findings from round 1 are fixed and tested, every acceptance item was shown by checks I ran myself (verify, full suite, scope, and fresh real bakes with and without `--impact`), and the only remaining findings are minor.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
