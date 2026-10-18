# BOOK-4 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent; commit `8853270e`, 2026-10-18)

| Field | Value |
|---|---|
| Task | BOOK-4: the book in the dock. The exposure table and the account impact card are record-backed components the planner may arrange. The two queries are actions. Everything runs on the fixture book. |
| Branch | `task/BOOK-4`, worktree `.local/wt/BOOK-4` |
| Commit under review | `8853270e` (the build `54f8940b`, and the record commits `6c3d8a25`, `75ee33c8`, `8853270e`) |
| Base | `d5f172fe` (`origin/main` at the DOCK batch, with BOOK-1 and BOOK-2 merged) |
| Reviewer | Claude Opus 5.5 in-session subagent. It is read-only and independent of the author (the executor seat). The owner allowed this reviewer while the Codex seat has no credits. |
| Verdict | **accept**. Every acceptance line is proved by a check I ran. No major finding stands. Six findings (five minor, one nit) carry recommendations. One of them is a hand-back the packet already names. |

I read AGENTS.md, the `plan.py brief BOOK-4` output and the task entry in `tasks.json`. I read the strategy record (section 1, "The book and the outlook from the dock", and section 3), the agent contract (sections 1, 2 and 6), the packet [book-4.md](../desk-agent-and-book-2026-10-18/book-4.md), the BOOK-2 hand-back to BOOK-4 (`book-2.md` "To BOOK-4") and the BOOK-2 review (notes A to C). I used the [DOCK-1 review](DOCK-1.md) for the record format and the six rules. I read the DOCK-3 call sites in `src/agent/service.py` (lines 362 to 387). I read `git diff d5f172fe..HEAD` in full: `src/judgment/view.py`, `src/judgment/actions.py`, the new `src/book/adapter.py`, the new `tests/test_book_views.py`, the two moved pins, `build.py`, the README, the six regenerated plan sets, `tasks.json` and `PROGRESS.md`. Interpreter: `/usr/bin/python3`. `node` is on the path. I made no network, model or cloud call. I edited no file except this record.

**The owner's data.** I read `.local/outlook-archive` and `.local/price` only through `sha256sum` and `OutlookArchive.verify()`. Before and after all my runs, `verify()` gives `outlooks 2, receipts 0, attributions 0, problems []`. The `sha256sum` lists of the 30 files are byte-identical (`cmp`).

### Commands and results

| Command | Result |
|---|---|
| `-m unittest discover -s tests -p "test_*.py"` (full offline suite, head `8853270e`) | `Ran 3050 tests in 241.528s`, **`OK (skipped=62)`**, exit 0. This is the packet's figure: the base's 3018 plus the 32 new tests. |
| `-m unittest tests.test_book_views tests.test_judgment_view tests.test_judgment_actions tests.test_grid_ask_page tests.test_grid_catalog` | `Ran 336 tests`, **`OK (skipped=1)`**. The one skip is `test_grid_catalog.Check.test_the_real_bake_when_it_is_there` ("no real bake at build/grid-data in this worktree"), the environment. |
| `-m unittest tests.test_book_views` | `Ran 32 tests`, **OK** |
| `scripts/plan.py scope BOOK-4 d5f172fe` | `OK: all changed files inside BOOK-4 allowed paths` |
| `scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `scripts/repo.py check` | `Checked 617 Markdown files, 3899 local links, 5 skills; bootstrap 1399 words.` **PASS** |
| `git diff --check d5f172fe..HEAD` | clean |
| `tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce` |
| Removed lines in the touched test files (`git diff d5f172fe..HEAD -- tests/`, lines starting `-`) | Seven lines, all inside the two moved pins (`test_judgment_actions.CONTRACT['query_impact']`, and `test_an_identifier_the_caller_did_not_supply_is_never_offered`). Test methods base against head: `test_judgment_view.py` 124 → 124, `test_judgment_actions.py` 18 → 18. **No assertion was removed.** |
| `git diff --stat d5f172fe..HEAD -- tests/test_grid_ask_page.py tests/test_grid_catalog.py src/grid/ask.js src/agent/` | empty. The dock's tests and the service are untouched. |
| A path diff of `home.json` base against head, per answer | The outlook and price answers differ only in `receipt.request_digest`, `labels`, `receipt.labels` and the receipt component's `receipt_digest`. Their plans, plan digests, components and text are unchanged. The exposure answer changes its components, `not_shown`, plan, stability arrangements, records, labels and text. This is the packet's account. `index.json` is unchanged. |

### Adversarial probes (my own scripts, against the head)

| # | Probe | Outcome |
|---|---|---|
| 1 | 20 hostile inputs to the adapter: windows `x/y`, reversed, half-hour, `a/b/c`, an integer, a list, a sentence with a slash, a midnight-crossing window; cutoffs `garbage` and `5`; accounts as a string, nodes `None`, an unknown node and an unknown account; vintage ids `../../../etc/passwd`, `a/b`, `''`, `7`, `..` | Each returns `{status: refused, code, reason_key, record_id: null, synthetic, label}` with a stable code (`WINDOW_INVALID`, `WINDOW_OUTSIDE_PROFILE`, `CUTOFF_INVALID`, `ARGUMENT_INVALID`, `UNKNOWN_NODE`, `UNKNOWN_ACCOUNT`, `VINTAGE_UNKNOWN`). No exception and no error text leaves the adapter. |
| 2 | The rendered request for the Visayas question, with the book's two records and the adapter's ids, searched for values | Zero hits for `MWh`, `PHP`, `demand`, `contracted`, `uncovered`, `p10`, `p50`, `p90`, `95.244`, `80477`, `8679`, `51.602`. No JSON number anywhere in the request. The only `price` and `band` hits are the component name `impact_band` and the missing kind `price_series`. The `book_impact` label carries the vintage id and two 12-digit hex prefixes, which are identifiers. |
| 3 | A hostile window id supplied by the caller (`ids={'windows': ['95.244 MWh uncovered']}`) | **Accepted into the manifest.** See finding 4. |
| 4a–4h | The Visayas plan with the raw window id as an action argument; a sentence as the window; an unoffered handle `window-b`; an unoffered `outlook-c`; a component argument `window`; a fifth action argument; a duplicate `exposure_table`; the table left out with no `not_shown` entry | `NUMERAL_IN_PLAN: plan.actions[].args.window`; `ARGUMENT_NOT_A_REFERENCE: window`; recorded `argument_not_in_manifest` (twice); `COMPONENT_ARGUMENT_NOT_IN_MANIFEST: exposure_table`; `MODEL_INVALID_RESPONSE`; `DUPLICATE_PART`; **composed** (finding 3) |
| 5 | The bake's three `home.json` answers: receipt records and labels | The outlook and price answers list `event, outlook, impact, judgment` in `receipt.records`, with no book record. Their `labels` and `receipt.labels` carry the `exposure` label. The exposure answer lists `exposure` in both. The impact card is left out under `no_record` (finding 2). |
| 6 | A `book_impact` record with `p50_php` changed on one account and on the total, its `content_digest` unchanged | `src.book.impact.verify_record` refuses it (`RECORD_DIGEST_MISMATCH`). **The composer shows the changed figures under the original record id** (finding 1). |
| 7 | The Visayas question at `repeats=3` | `forms 3`, `basis: repeats`, `measured: true`, `stable: true`, the statement "stability over repeated plans at one wording" |
| 8 | The same question with both book components left out of the plan | The text holds no book sentence, and the receipt lists no book record. A book template is written only when its component is shown. |
| 9 | DOCK-3's `AgentService` with the adapter, a plan proposing both queries | `query_exposure` is `done` with the exposure record id. `query_impact` is `done` with `record_refs [{kind: impact, id: null}]`, and its result is `refused WINDOW_REQUIRED` (finding 5) |
| 10 | Copy check of the four `BOOK_TEXT_TEMPLATES`, the four unavailable reasons and the book label, with `repo.py`'s own `sentences`, `PASSIVE` and the 61 banned words of `docs/routes.json` | No hit. Every sentence is under 20 words and active, with no semicolon or dash. |

### Against the six rules of the paper's section 10, as the record refines them

1. **The model writes no text, and the page composes from records.** The two components take no arguments (`COMPONENT_ARGS` is `{}`). Each fill copies a fixed field list, and nothing is computed (`_fill_exposure`, `_fill_account_impact`). The numeric walk in `test_every_figure_a_component_carries_is_at_a_quotable_path` finds every number at a `QUOTABLE_PATHS` path, and no unquotable key (`demand_mw`, `contracted_mw`, `price_php_mwh`, `band_php_mwh` and others) is copied. Every slot I tried for a book figure is refused: a reason key, a component argument, a component name, an action argument, a JSON number (probe 4, the tests in `QuotablePaths`). The four book sentences are code constants that quote only `BOOK_TEXT_PATHS`, and they are written only when their component is shown (probe 8).
2. **The manifest carries identifiers, never values.** The adapter's `manifest_ids` gives account ids, node ids and a window id. The vintage ids come through the outlook record. No book figure and no JSON number is in the rendered request (probe 2). One open slot is caller ids for windows (finding 4).
3. **Every view is under a receipt, the label travels and mandatory parts hold.** The materiality block is the first field of the impact card, and `_check_book_records` refuses a record whose first block is not the materiality line. The synthetic label is on every row, account block and total of both components (the walk in `test_every_block_carries_the_synthetic_label`). The receipt's `records` lists a book record only when its component is shown (probe 5, `test_an_outlook_answer_rests_on_no_book_record`). The book components are optional parts of the exposure question (finding 3).
4. **The cutoff governs.** An exposure record whose cutoff date is after the view cutoff's Manila date is not offered, and its key is `not_in_cutoff` (`test_a_book_record_computed_after_the_view_cutoff_is_not_offered`). An impact record whose vintage was issued after the view cutoff is not offered either (V2 at 03:00Z). The bake's impact card is a separate case (finding 2).
5. **Stability is recorded.** The Visayas question at three repeats gives `stable: true` over three forms (probe 7, `test_the_question_composes_the_table_with_no_model`). The recorded exposure question keeps four wordings (`test_the_exposure_question_shows_the_book_first_with_no_model`).
6. **Actions run through code, on identifiers.** Both queries through the adapter give a record id, a window id, a cutoff and, for the impact query, the vintage by id, record digest and values digest. Refusals carry BOOK-2's stable codes and no error text (probe 1, `TheTwoActionsThroughTheAdapter`). The adapter reaches a band only through `query_impact`, which calls `load_vintage` (BOOK-2 review, note C). `vintage_digest` and `vintages` read outlook records from the archive, never a values file, and the adapter calls neither `build_impact` nor `tie_band`. The adapter imports no web layer (the AST test, and I read the imports: `datetime`, `pathlib`, `src.contracts.jsonutil`, `src.outlook.records`, `src.price.impact`, and `src.book` siblings).

### The executor's design choices

- **`BOOK_COMPONENTS` beside the frozen `CATALOGUE`.** Sound. `test_grid_ask_page` pins `set(CATALOGUE)` to the titles in `ask.js`, and the brief keeps the dock's tests green. `request_catalogue` offers the book only when a book record is present, so a request without the book is the DOCK-1 request, byte for byte (`test_a_book_component_the_request_does_not_offer_is_refused`). The merge into `CATALOGUE` is handed to DOCK-6, which is the right owner.
- **The components optional on the exposure question.** The reason holds. `TheCutoffItems.compose_with_decision` validates `FIXTURE_PLANS['exposure']` over `build.plan_records()`, which now carries the book, so a mandatory table would turn a DOCK-2 test red. The cost is finding 3.
- **The account impact card absent from the bake.** Honest in substance. Both fixture vintages were issued on 18 October, after the plan cutoff that DOCK-2's tests pin, and `test_the_bake_reads_the_region_and_window_of_the_strategy_s_question` proves the adapter refuses that query with `VINTAGE_AFTER_CUTOFF`. The receipt states only part of the reason (finding 2).
- **Every plan set's bytes moving.** Explained and verified. The book is in every key's record set, so every manifest changes. Only digests and labels move in the outlook and price answers (the path diff above).
- **Window ids as `start/end` strings.** They are manifest ids, never plan arguments. A plan names them only by the handle `window-a`, and the raw string is refused `NUMERAL_IN_PLAN` (probe 4a). So DOCK-1's reference-shape rule holds on the plan side. The manifest does not check their shape (finding 4).
- **The service's two-argument call to `impact`.** Recorded as a DOCK-5 hand-back with the exact call. `test_the_adapter_runs_under_the_agent_service` runs only `query_exposure` and says so. That is honest scoping, because `src/agent/` is outside this task's paths. Probe 9 shows what happens until DOCK-5 lands (finding 5).
- **"Gain one exposure answer per page key".** The executor reads this as "each key's existing exposure answer gains the book", not as a fourth answer. Three DOCK-2 tests fix every key at three equal answers, so a fourth answer needs edits outside the brief. I accept the reading. The orchestrator should confirm it.

### Findings

| # | Severity | Location | Bears on | Failure mechanism and evidence | Correction |
|---|---|---|---|---|---|
| 1 | minor | `src/judgment/view.py:757-760` (`_check_book_records`, the `book_impact` branch); `:801` (`book_record_id`) | acceptance line 2 ("every figure from src/book by record id") | The exposure record's stated digest is recomputed (`:752-754`). The impact record's digest is checked only for its shape (`_HEX64.fullmatch`). Probe 6: a `book_impact` record with changed `p50_php` figures and its old `content_digest` composes, and the card shows `999999.99` under record id `7546e9cb4b9b…`. `src.book.impact.verify_record` refuses the same record with `RECORD_DIGEST_MISMATCH`. The base composer recomputes no stated digest for any record (`:916-937` take `content_digest` as given), so this is below the bar the task set for the exposure record, not below the base. The adapter hands in real records, so no path today produces it. | In the `else` branch, refuse a record whose `content_digest` does not recompute. Use `src.book.impact.record_digest(record) != record['content_digest']`, or `verify_record(record)` with its error turned into the `ValueError`. Add one test beside the exposure case in `test_a_malformed_book_record_is_a_caller_error`. No bake bytes move, because the bake holds no impact record. |
| 2 | minor | `src/judgment/view.py:874-878` and `:962-968` (`_unavailable_reason`, `_unavailable_reason_key`); `tests/fixtures/grid/catalog/build.py:211-215` and `:105-107` | rule 4 (an after-cutoff vintage is left out under `not_in_cutoff`) | In the bake, the impact card is left out under `no_record` with "No impact record of the synthetic book is among this view inputs." That sentence is true, but the reason is the cutoff: the adapter refuses `VINTAGE_AFTER_CUTOFF` before a record can exist. Only the packet and the README say so. Also, the bake manifest marks `query_impact` available over `outlook-fixture-2026-11-system`, the composer's fixture vintage. The book archive does not hold that id, so any impact query a planner proposes there can only be refused `VINTAGE_UNKNOWN`. | Either (a) put the book archive's vintages in the outlook record (`adapter.vintages()`, the step the packet hands to DOCK-5), so the composer's `_visible_outlooks` filter withholds them at the plan cutoff, `query_impact` becomes unavailable, and the left-out reason follows the cutoff, or (b) let the caller state that the book has vintages after the cutoff, and key the card `not_in_cutoff`. (a) is preferred, because it is DOCK-5's provider in any case. Until then, the packet's account is correct. |
| 3 | minor | `src/judgment/view.py` `mandatory_parts` (no book row); `FixtureView._with_book` (`:1728`) | acceptance line 2 for a planner other than the fixture; rule 3 | With the book present and the exposure table available, a plan for "What is exposed?" that neither shows the table nor lists it under `not_shown` validates (probe 4h). DOCK-1 lets any optional part be left out silently, so the fixture planner's `_with_book` is the only thing that puts the table first. A live planner could drop the book's answer to the exposure question with no reason shown. The executor's reason for this choice is correct (a DOCK-2 pin), and the packet hands the change to DOCK-6. | Before DOCK-4 records a live exposure answer, make `exposure_table` a mandatory part of the exposure question when the book is present (one row in `mandatory_parts`), and move `TheCutoffItems.compose_with_decision` to the book's plan with it. Or require every available book component to be shown or listed under `not_shown`. |
| 4 | minor | `src/judgment/actions.py:188-197` (`_id_list`); `src/book/adapter.py:161-164` (`manifest_ids(windows=…)`) | rule 2 (identifiers, never values) | Caller ids for `windows` are checked only for being nonblank strings. Probe 3: `ids={'windows': ['95.244 MWh uncovered']}` is accepted, and that string is sent to the planner in the manifest. `manifest_ids(windows=…)` also passes a string through without parsing it. The adapter refuses any such window at execution (`WINDOW_INVALID`, probe 1), and the plan side cannot carry it, so no figure reaches a view. The caller is trusted code. This is the same class as the DOCK-1 review's finding 1. | In `manifest_ids`, round-trip each window through `parse_window` and `window_id`. In `action_manifest`, refuse a `windows` id that does not match the `<YYYY-MM-DDTHH:00>/<YYYY-MM-DDTHH:00>` shape. Add a test with a hostile window id. |
| 5 | minor (hand-back, recorded) | `src/agent/service.py:386`; `src/agent/catalogue.py:20`; `docs/work/desk-agent-and-book-2026-10-18/agent-contract.md:38`; `tests/test_judgment_actions.py` `CONTRACT` | acceptance line 3; the contract's rule that "a change to this file is a change to all three" | `ACTIONS['query_impact']` and the moved `CONTRACT` pin now take four arguments. The contract table and the agent's fallback catalogue still list two. The service calls `book.impact(account_ids, outlook_id)`. Probe 9: through the service, `query_impact` is recorded `done` with `record_refs [{kind: impact, id: null}]`, while the adapter's result is `refused WINDOW_REQUIRED`. So a refused query reads as done. The packet names all three items as hand-backs, with the exact call, and the paths are outside this task. | The orchestrator amends `agent-contract.md` section 2 at merge, as section 6 did for the DOCK batch. DOCK-5 takes hand-back items 2, 3 and 6: pass `window` and `cutoff`, record an adapter `refused` answer as a refused receipt under its `reason_key`, and widen the fallback table. Do not wire the adapter into a served service before DOCK-5. |
| 6 | nit | `src/judgment/view.py:951-959` (`_labels`) | rule 3 (a book record in the receipt only when shown) | The outlook and price answers carry the `exposure` record's label in `labels` and `receipt.labels`, while `receipt.records` correctly leaves the book record out (probe 5). This is the base's behaviour: `_labels` lists every input record, and the price impact label is carried on the outlook answer in the same way. A reader of the bake still sees the synthetic book's label on an answer that rests on no book record. | Optional: filter the book's labels by the shown components, matching `_record_refs(shown=)`. Or state in the `_labels` docstring that labels cover every input record. |

### Verdict

**Accept.** Each acceptance line is proved by a check I ran.

1. **Line 1.** Each component renders from the fixture book with no model. `TheComponentsRenderFromTheBook` (8 tests) and `TheFixtureBake` (2) pass with the labelled `FixtureView`, `execution_mode: synthetic_fixture`. A plan that quotes a book figure is refused in every slot: the `QuotablePaths` tests (7) and my probes 4a to 4g. The numeric walk finds every figure at a quotable path.
2. **Line 2.** The Visayas question composes the table from `src.book` by record id with the synthetic label. `TheVisayasExposureQuestion` (5) rebuilds the record with `src.book.exposure.exposure` and checks the record id, all 10 rows and the three account figures (51.602, 36.838, 6.804). It checks the impact card against `query_impact` (total p50 80,477.01). The label is on the view and in the receipt, and stability over three repeats is recorded. Finding 1 is a hardening item on a path no caller takes today.
3. **Line 3.** No assertion was removed. Seven removed lines all sit in the two moved pins, and both pins still assert their claim with the four-argument action. Method counts are unchanged. The full suite passes: `Ran 3050 tests`, `OK (skipped=62)`. No live call occurs. The only planner built is the fixture.

No major finding stands. Findings 1 to 4 are minor and do not block. The orchestrator should schedule 1 and 4 as a small follow-up in the BOOK lane, or fold them into DOCK-5. Finding 3 belongs before DOCK-4 records a live exposure answer, with DOCK-6's mandatory row. Finding 5 needs the contract amendment at merge and DOCK-5's three hand-back items. The orchestrator should confirm the "gain one exposure answer" reading.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent; commit `f1264534`, 2026-10-18)

| Field | Value |
|---|---|
| Commit under review | `f1264534`, one commit over `8853270e` (the rework of round 1 findings 1 and 4) |
| Base | `d5f172fe` |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, independent of the author |
| Verdict | **accept** |

I read `git diff 8853270e..f1264534` in full: `src/judgment/view.py`, `src/judgment/actions.py`, `src/book/adapter.py`, three test files and the packet's rework section. I made no network, model or cloud call. The owner's data is unchanged: `verify()` gives `outlooks 2, receipts 0, attributions 0, problems []`, and the 30 files match the round 1 `sha256sum` list (`cmp`).

### Commands and results

| Command | Result |
|---|---|
| `-m unittest tests.test_book_views` | `Ran 35 tests`, **OK** (32 + 3 new) |
| `-m unittest tests.test_book_views tests.test_judgment_view tests.test_judgment_actions tests.test_grid_ask_page tests.test_grid_catalog` | `Ran 339 tests`, **`OK (skipped=1)`** (the same environment skip as round 1) |
| `tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce` |
| `scripts/plan.py scope BOOK-4 d5f172fe` | `OK: all changed files inside BOOK-4 allowed paths` |
| `scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `scripts/repo.py check` | `Checked 618 Markdown files, 3902 local links, 5 skills; bootstrap 1399 words.` **PASS** |
| `git diff --check d5f172fe..HEAD` | clean |
| Removed lines in tests, `8853270e..f1264534` | Three lines. Each is a window fixture value (`tomorrow-afternoon`, `SYN-WINDOW`) replaced by a real window id, because the new shape rule refuses the old value. Every assertion stays. Method counts: 124 → 124, 18 → 18, 32 → 35. |
| Round 1 probe 6 (a changed `p50_php` under the original impact record id) | Now refused: `ValueError: the book impact record does not match its content digest` |
| Round 1 probe 3 and more (window ids supplied by the caller) | Refused in the manifest: `95.244 MWh uncovered`, `sell now before noon`, a full-width digit, an empty window. The real window id is accepted. `manifest_ids` refuses an invalid window (`WINDOW_INVALID`). |

### Findings

- **Round 1 finding 1: closed.** `_check_book_records` recomputes the impact record's digest with `src.book.impact.record_digest`. `test_a_changed_impact_figure_under_the_original_record_id_is_refused` proves it. The import is lazy, inside the function. The import fence in `test_judgment_view.LiveBackend` gains `src.book.impact`, and its `assertLessEqual` stays. `src.book.impact` imports only the standard library, `src.outlook`, `src.price` and `src.book`, with no web layer and no network. This is a moved pin, not a weakened one.
- **Round 1 finding 4: closed.** `is_window_id` in `action_manifest` refuses any window id without the `<YYYY-MM-DDTHH:00>/<YYYY-MM-DDTHH:00>` shape and ascending order. `manifest_ids` round-trips each window through `parse_window` and `window_id`. `WindowIdentifiers` (2 tests, 8 hostile strings each) proves both.
- **New nit.** `is_window_id` checks the shape, not the calendar: `2026-13-45T99:00/2026-13-46T99:00` passes the manifest check. The shape allows only digits in fixed places, so no value or sentence can travel in it. The adapter refuses such a window (`WINDOW_INVALID`) both in `manifest_ids` and when the query runs. Optional: parse the two hours with `datetime.fromisoformat` in `is_window_id`.
- Round 1 findings 2, 3, 5 and 6 stand as recorded. None of them blocks.

### Verdict

**Accept** at `f1264534`. The round 1 acceptance proofs hold, and the rework closes findings 1 and 4 with tests I ran. No major finding stands.

## Round 3 (Claude Opus 5.5 in-session subagent, read-only, independent; commit `0dd68872`, 2026-10-18)

**Verdict: accept** at `0dd68872`, one commit over the merge `09326f53`. The commit touches only `tests/test_book_views.py` and the packet, with no production change (`git diff 09326f53..0dd68872 --stat`). BOOK-3 added two fixture vintages (`cluz`, `cmin`) that sort before `cvis`. The three moved pins keep their strength:
- The outlook answer's receipt list is still an exact list, now `event`, one `outlook` per vintage in the records, then `impact` and `judgment`. It adds `assertIn` for V1 and V2. A vintage the cutoff withheld would still turn it red.
- The manifest's vintage list is still an exact ordered list, now equal to `OutlookArchive(ARCHIVE).issue_ids()`.
- The Visayas plan reads V1's handle from the rendered manifest instead of the literal `outlook-a`. The unchanged assertion at line 581 still requires the resolved `outlook_id` to be V1, so the test proves more than before, not less.

The behaviour is the one I accepted in rounds 1 and 2: DOCK-1's `handle(prefix, index)` over `_visible_outlooks`. My run gives handles `outlook-a` to `outlook-d` for `cluz`, `cmin`, `cvis`, `cvis-v2` at `LATE`. At `2026-10-18T03:00:00Z` the manifest offers only the first three, because `cvis-v2` was issued at 06:00Z. So the manifest offers every vintage the cutoff admits, in record order.

One nit: the manifest pin compares against every archive vintage. That equals "every vintage the cutoff admits" only because `LATE` admits all four. Filtering `issue_ids()` by `issued_at <= LATE` would state the rule exactly.

Results:
- `-m unittest tests.test_book_views`: `Ran 35 tests`, **OK**
- `scripts/plan.py scope BOOK-4 09326f53`: OK
- `git diff --check 09326f53..0dd68872`: clean
- The owner's `.local/outlook-archive` and `.local/price` are byte-identical to the round 1 snapshot.
