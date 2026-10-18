# ASK-2 review record

## Round 1 (orchestrator-run, Claude Opus 5.5 in-session subagent, read-only, independent; commit `6985a0ff`, 2026-10-18 02:15)

Recorded verbatim:

> # ASK-2 review, round 1: accept
>
> Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the orchestrator seat).
>
> Commit under review: `6985a0ff` (made on main by the orchestrator seat). Base: `7dcbf98d` (its parent).
> All commands ran in a temporary worktree `/tmp/claude-1000/ask2-review` at `6985a0ff`, interpreter `/usr/bin/python3`. No network, model or cloud call.
>
> ## Commands and results
>
> | Command | Result |
> |---|---|
> | `python3 scripts/plan.py scope ASK-2 7dcbf98d` | `OK: all changed files inside ASK-2 allowed paths`. `tests/fixtures/grid/catalog/ask-render.mjs` is not in ASK-2's own `owned_paths`, but ancestors own it (ATG-4 owns `tests/fixtures/grid/catalog/`; GRID-1, EXPL-1, EXPL-2 and CORP-5 own `tests/fixtures/grid/`). `docs/work/PROGRESS.md` and `docs/work/tasks.json` are coordination files. |
> | `/usr/bin/python3 tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce`, exit 0 |
> | `/usr/bin/python3 -m unittest tests.test_judgment_view tests.test_grid_ask_page tests.test_grid_catalog tests.test_grid_data tests.test_hosting_stage` (the brief's verify command plus the two named modules) | `Ran 375 tests`, **OK** (skipped=1) |
> | `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 2572 tests in 167.136s`, `FAILED (errors=1, skipped=126)`. The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: `pypdf is not importable; unpack it at .local/pylib/`. The temporary worktree has no `.local/pylib`. This is an environment limit, and ASK-2 touches no corpus file. |
> | Same, after linking the main checkout's `.local/pylib` into the temp worktree: `/usr/bin/python3 -m unittest tests.test_corpus_index` | `Ran 10 tests`, **OK**. So the full suite is green apart from that environment limit. |
> | `python3 scripts/repo.py check` | `Checked 586 Markdown files, 3762 local links, 5 skills; bootstrap 1400 words. PASS` |
> | `python3 scripts/plan.py check` | `OK: 120 tasks, 8 gates` |
> | `grep -rnE "price rise\|moved the price\|price higher after\|explains the price\|why the price moved" src tests` | One hit only: `src/grid/explain.html:1382`, a quiz about a typhoon. It is unrelated, and the old question is not present. |
> | `git grep -nI "price rise after" -- . ':!docs/work'` | no hits. The old wording survives only in records under `docs/work` (ask-2.md, cold-read-release-12.md, tasks.json), and it is quoted there on purpose. |
> | `grep -rn "13:34" src tests` | No hit in any plan text, wording or reason. `tests/test_judgment_view.py:625` is the numeral-rule probe (`'Shows the notice posted at 13:34.'`, refused), unchanged. The other hits are paper/explainer/event records. |
> | Script over the six `bake/views/*.json` price entries: status, `view_version`, wordings, digits in plan text, part and not-shown reasons, `stability.stable` | All six: `composed`, `view.v3`, the four new wordings, no digits, `stable: True` |
> | Regex for digits in the `text` and `reason` fields of `view.FIXTURE_PLANS` | none in outlook, price or exposure |
> | `grep -o "view\.v[0-9]" bake/views/*.json \| sort \| uniq -c` | `view.v3` ×9 in each of the six plan sets. No `view.v2` is left in the bake. |
> | `grep -rn "view\.v2" src tests docs` | `tests/test_grid_data.py:290,306,320` (a labelled synthetic receipt helper; `build_data.py` checks only that the string is non-empty). `view-0.md` and `bake-1.md` are historical records. Neither counts as a stale pin. |
> | `cmp` of `.local/grid-snapshot/views/{ask,syn-bay-unit-2-trip}.json` (main checkout) against the fixture bake at `7dcbf98d` and at `6985a0ff` | Both are byte-identical to the **old** (`7dcbf98d`) fixture bake. `scripts/grid/build_all.py:55,82` defaults to `.local/grid-snapshot/views`. See finding 2. |
>
> ## Checklist
>
> 1. **Every acceptance item met by a check I ran.** Yes.
>    - A1: The recorded price question and all four wordings presume no cause. The panel (`src/grid/ask.js`) has no hard-coded question and reads the wording from the bake. The price plan text still says "No price-series record is among this view inputs ... adds no market explanation", so the event page's figures stay the record.
>    - A2: The six-rule tests pass. `build.py --check` proves the plan sets are the composer's own output.
>    - A3: The new wordings and the one changed reason are short, active, with no semicolons and no "stale".
>    - A4: The diffs of the touched tests are one-for-one line replacements of wording pins only. The full suite is green apart from the pypdf environment limit, which I resolved separately.
> 2. **Only allowed paths changed.** Yes (scope OK; `ask-render.mjs` is covered through ancestors).
> 3. **No frozen contract, acceptance text or test weakened.** Yes. Only the question pins moved, together with the wording and the version. There are no VIEW_VERSION pins in tests. `test_grid_data` uses its own synthetic helper.
> 4. **No new dependency, service, network or model call.** Yes.
> 5. **Mode labels truthful.** Yes. The fixture plan sets keep their synthetic labels, and the record says the live planner's recorded runs used the old wording.
> 6. **Nothing invented.** With one exception: the record's claim about a full-suite result (finding 1).
> 7. **Packet records interpreter, commands, results, limits and next action.** Partly. It records the interpreter, commands, results and limits. The full-suite pointer is wrong, and the next action does not cover the deploy input (finding 2).
> 8. **Nothing contradicts the paper, the strategy or the records.** Yes. The change follows cold read §5 (the price was at the cap at 13:30, before the 13:34 trip). VIEW_VERSION's bump is justified: `request_digest` digests `{'view_version', 'input': request}` (`view.py:658`), and the request carries the wordings. Every regenerated receipt carries `view.v3`.
>
> The new wordings keep the subject (the price, relative to the trip), and rule 5 stability is recorded as stable over them. No numeral entered any plan text or reason.
>
> ## Findings
>
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor (record) | `docs/work/product-gap-2026-10-17/ask-2.md` §3, row "full offline suite" | The record points at a result that does not exist. The packet cites a full-suite run that nobody recorded. | The row says "recorded in the PROGRESS log row of the commit". The added PROGRESS log row names only the five modules (`test_judgment_view ... test_hosting_stage` **OK**), not the full suite. | Cite a real run: interpreter, base `6985a0ff`, the run's "Ran N tests" figure and the result. This review's run is 2572 tests, green except the pypdf `.local/pylib` environment limit, which passes with the library linked (10 tests OK). If no run exists, say the full suite was not run before review. |
> | minor (handoff) | `.local/grid-snapshot/views/` (ignored, outside ASK-2's paths); ask-2.md §4 Limits | The deploy input still carries the old wording. `build_all.py` copies `<snapshot>/views` byte for byte into the site bake, so the next release's panel would replay "Why did the price rise after 13:34?" with `view.v2`. | `cmp`: `ask.json` and `syn-bay-unit-2-trip.json` in `.local/grid-snapshot/views` are identical to the `7dcbf98d` fixture bake. `build_all.py:55` `DEFAULT_SNAPSHOT = ROOT / ".local" / "grid-snapshot"`, `:82` `views_directory`. | Add to Limits and the next action: copy the regenerated `tests/fixtures/grid/catalog/bake/views/{ask,syn-bay-unit-2-trip}.json` (or the full set the release uses) into `.local/grid-snapshot/views/` before the next batch deploy. Then check the baked `views/` before deploying. |
> | nit | `src/judgment/view.py:190` | "Where was the price when the unit tripped?" asks about one moment, while the other wordings ask "around / before and after". The subject (the price, relative to the trip) is kept, and the fixture plan stays stable. A live planner could still arrange this wording differently. | `stability.stable: True` in all six fixture receipts (the fixture backend). | None required. If a future live recording shows this wording as the unstable one, consider "Where was the price around the time the unit tripped?". |
>
> ## Verdict
>
> **Accept.** Every acceptance item is met by a check I ran:
> - The verify command plus `test_grid_data` and `test_hosting_stage`: 375 tests OK.
> - `build.py --check` passes.
> - The full offline suite is green apart from one environment-only error, which passes when `pypdf` is available.
> - Scope is OK, and the plan and repo checks pass.
> - The old wording is gone from `src/`, `tests/` and the fixture bake. No numeral entered a plan text or reason. The view.v3 bump is justified and is in every regenerated receipt.
>
> Two minor record findings remain: a false full-suite pointer in ask-2.md §3, and the ignored deploy snapshot still holding the old plan sets. Neither blocks. The orchestrator should correct both when it sets `done` and before the next deploy.
