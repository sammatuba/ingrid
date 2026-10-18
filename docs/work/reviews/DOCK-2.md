# DOCK-2 review record

## Round 1

| Field | Value |
|---|---|
| Task | DOCK-2: the dock on every page (M16, lane DOCK) |
| Branch | `task/DOCK-2` in `.local/wt/DOCK-2` |
| Commit under review | `433c2537` |
| Base | `a422de03` (`task/DOCK-1` rework round 1, which carries origin/main `8d20c523`). The diff judged is `git diff a422de03..433c2537`. DOCK-1's own changes are reviewed in its own record. |
| Reviewer | Claude Opus 5.5 in-session subagent. Read-only and independent: I am not the author. Offline: no network, model or cloud call. Interpreter `/usr/bin/python3`. |
| Date | 2026-10-18 |
| Verdict | **rework**. One major finding (1). The dock shows a write as done when its confirmation is still pending. |

### What I verified by running

All commands ran from `.local/wt/DOCK-2` at `433c2537`. The worktree was clean before this file was written.

| # | Command | Result |
|---|---|---|
| 1 | `/usr/bin/python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| 2 | `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` (full offline suite) | `Ran 2734 tests in 195.517s` · `FAILED (failures=2, skipped=115)`. The two failures are exactly the expected DOCK-5 reds: `test_grid_ask_page.TheFixtureBake.test_the_bake_passes_its_own_contract` and `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag`. Both fail on `build_data.contract(tree)`: "views/ask.json: views[0] receipt keys are ['actions', …]". That is `VIEW_RECEIPT_KEYS` without `actions`. Nothing else fails. `pypdf` imported through the linked `.local/pylib`. |
| 3 | `/usr/bin/python3 -m unittest tests.test_grid_ask_page` | `Ran 77 tests` · `FAILED (failures=1)`: the expected `TheFixtureBake` red only |
| 4 | The browser classes with the machine's Chromium (`GRID_BROWSER_CHROMIUM=~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome`, `GRID_BROWSER_PLAYWRIGHT=<main checkout>/.local/deckcheck/node_modules/playwright-core/index.mjs`): `tests.test_grid_page tests.test_grid_outlooks_page tests.test_grid_register_page tests.test_explainer tests.test_grid_alerts` | `Ran 231 tests in 33.095s` · **OK (skipped=12)**. The real browser launched. 4 tests skip for the server's compression library. 8 skip because puppeteer-core is absent: these are the alerts page's browser tests, the one page where sign-in lives. The real browser ran the anonymous dock on home, outlooks, register and explain. |
| 5 | Node harness by hand, fixture bake: `node tests/fixtures/grid/catalog/ask-render.mjs --root . --page src/grid/<page> --path <path>` for `event.html /event/syn-bay-unit-2-trip`, `index.html /`, `ask.html /ask`, `paper.html /paper`, `alerts.html /alerts` | All `ok`. Event: key `syn-bay-unit-2-trip`, one request (`/grid-data/views/syn-bay-unit-2-trip.json`), 3 answers, each "Stable across 4 wordings", and the case listed. Home and ask: one request each, 3 answers. Paper and alerts: the absent line, one request. All five show "Sign in to ask live" and the no-budget line. Each unmatched question gets the insufficient sentence and an offer. |
| 6 | The same harness with the labelled agent fixture the tests build (`agent_fixture()`, dumped to JSON), `--agent` on `/ask` | `api present`. The requests were `threads, queue, ask` before any click and one `confirm/conf-fixture-1` after it. The cards: open, query_exposure and draft show `done` with their receipt lines. save_decision shows `needs_confirmation` and waits. |
| 7 | **Attack: hostile strings.** Agent fixture with `<img src=x onerror=…>"'><script>…</script>` in the question, the text, every string record field, the cutoff, a receipt record id, the account ids, the record refs, the confirmation preview, the case id, the label and `event_id`, the budget day, the queue ids and the identity email. A confirmation id carries `" data-confirm="evil`. | No raw `<script>`, `<img` or `onerror=` attribute appears in the first screen, the answered screen or the after-click screen. The quote in the id is escaped (`&quot;`). The case link encodes (`/event/%22%3E%3Cscript…`). **One escape:** the route `//evil/x` renders as `<a href="//evil/x">Go there</a>` (finding 2). |
| 8 | **Attack: write reported done.** The fixture plus a `save_decision` `outcome: done` with `confirmation_id: conf-fixture-1`, where that confirmation is still `pending`. Also an unknown `delete_case` with `done`, and a `mark_stale` with `needs_confirmation` and no id. | `save_decision done` renders as **"Saved the decision in draft draft-fixture-1 on syn-bay-unit-2-trip."** On the same screen, the conf-fixture-1 card is still `pending` with both buttons (finding 1). `delete_case` renders as "Ran action delete_case." (finding 3). `mark_stale` renders as unconfirmed, never as done. |
| 9 | **Attack: budget.refused.** The fixture turn is `{budget: {refused: true}}` | The budget line says "The dock reached the day's live budget. It answers from recorded plans until the next day." The status shows VIEW-1's insufficient sentence and the nearest-answer offer. The service stays `present`. No write happens. Nit 11 covers the status sentence. |
| 10 | **Attack: confirmation POST fails.** A scratch copy of the harness (outside the repository) answers `confirm/` with 500 | The card says "The agent service did not record your answer. Try again." It never shows as confirmed anywhere. It offers no button to try again (finding 4). |
| 11 | Harness on `/ask` with `--search '?event=%E0%A4'` | `{"ok":false,"error":"… ask.js:71 … URIError: URI malformed"}`. The dock does not render (finding 5). |
| 12 | Harness with a stored session `{"threads":{"desk":{"turns":"x"}}}` | `TypeError: active.turns.map is not a function` at `ask.js:842`. The dock does not render (finding 5). |
| 13 | Copy rules on the literals `CopyRules.authored()` skips (every literal that holds `<` or `>`): a scratch script with the test's own `PASSIVE` and `NOT_PARTICIPLES`. Then the rendered text of rows 5 to 9, split into sentences, with words counted. | No semicolon, no 'stale' and no passive in any dock literal. No dock sentence reaches 20 words. Every sentence of 20 words or more is the composer's template text, a record field, the receipt fold or a record-as-of line (nit 12). |
| 14 | `git diff --stat 8d20c523..433c2537 -- 'src/grid/*.html' 'src/grid/*.js' 'src/grid/*.css'` and `git diff a422de03..433c2537 -- src/grid/ask.html` | Only `ask.html` (+6 −4: the intro sentence and two comments), `ask.js` and `ask.css` change. The page's `<script>` and `<link>` lines are unchanged. `ask.css` brings no new colour, gradient or font. |
| 15 | `/usr/bin/python3 scripts/plan.py scope DOCK-2 task/DOCK-1` and `… scope DOCK-2 a422de03` | Both `OK: all changed files inside DOCK-2 allowed paths`. Note: `task/DOCK-1` is now at `c34b2c57`, which adds DOCK-1's review record. `a422de03` is its ancestor. |
| 16 | `git diff --check a422de03..433c2537` and `git diff --check` | clean, clean |
| 17 | `/usr/bin/python3 scripts/repo.py check` | Exit 1. Exactly one finding: `Broken local link: docs/work/desk-agent-and-book-2026-10-18/dock-1.md: ../reviews/DOCK-1.md`. `c34b2c57` adds that file, so the link resolves when DOCK-1's tip is merged. Nothing else fails. |
| 18 | `git hash-object tests/fixtures/grid/catalog/v3/views/ask.json` and `git rev-parse 971885b0:tests/fixtures/grid/catalog/bake/views/ask.json` | Both `5b79f852ace2ae8617a348ab72ad896fa6c3b7a5`. The view.v3 set is the composer's own bytes. |
| 19 | Every `-` line of `git diff a422de03..433c2537 -- tests/test_grid_ask_page.py`, mapped to its replacement | No test method dropped. 12 shape moves and 2 brief-driven pin moves. Each removed line has a replacement that is as strict or stricter, except one (finding 6). |

### Findings

1. **major** · `src/grid/ask.js:657` (`actionCardHtml`), `:664-666`; `tests/test_grid_ask_page.py:1358`. Acceptance line 2: "a write never happens without a confirmation card". The brief's attack: "a turn with a write action reported done without a confirmation must never show as done". The guard is `WRITES.indexOf(run.action) >= 0 && !run.confirmation_id`. That tests whether an id string is present. It does not test whether the confirmation happened. A catalogue write the service reports as `outcome: done` with any `confirmation_id` renders in the past tense, "Saved the decision in draft draft-fixture-1 on syn-bay-unit-2-trip.". This happens even when that confirmation is `pending` in the same turn's `confirmations` and its card, with Confirm and Decline, sits on the same screen (row 8). The stranger sees a write reported as done that they never clicked. The test at `:1358` covers only the no-id case. **Rework:** show a write card in the past tense only when the dock knows its confirmation is `confirmed`: `state.decided[id].state === 'confirmed'`, or the matching entry in `turn.confirmations` or `state.queue` with `state: 'confirmed'`. In every other case, render the unconfirmed card ("The service reports a write without your confirmation …"). Add a harness test on `agent_fixture()`: a `done` write whose id is still pending must render as unconfirmed, with no "Saved". Also test that the same write renders as done after the click confirms it.

2. **minor** · `src/grid/ask.js:672-674`. Acceptance line 2, and the hostile-string attack. The "Go there" guard `/^\/[a-z0-9/_-]*$/i` admits a protocol-relative route. `//evil/x` renders `<a href="//evil/x">`, which leaves the site (row 7). The composer's manifest restricts routes server-side, but the dock's own guard is meant to keep the link on site. **Fix:** refuse a second leading slash (`/^\/(?!\/)[a-z0-9/_-]*$/i`), or link only routes the page's own route table lists. Add the case to the stranger tests.

3. **minor** · `src/grid/ask.js:630-631` (`actionWords` default), `:664-666`, `:693` (`proposedHtml`), `:477-482` (`receiptLines`). Acceptance lines 2 and 3. An action outside the catalogue (`delete_case`, `done`) renders as "Ran action delete_case.", in the past tense like a read (row 8). The dock cannot tell whether an unknown action wrote something. Also, DOCK-1's review R2-1 (recorded at `c34b2c57`, after this branch's merge base, so the executor could not see it) asks DOCK-2 to render a refused action by its catalogue name and reason sentence only. Raw `args` and an unknown name should appear only inside the receipt fold. `proposedHtml` prints `actionName(item.action, item.resolved || item.args)` in the visible list for refused actions too. **Fix:** treat an unknown action as unverified ("The service reports an action outside the catalogue."), with its name only in the receipt line. For a refused proposal, show the catalogue reason sentence, not its raw arguments.

4. **minor** · `src/grid/ask.js:713-728` (`confirmationCardHtml`), `:1005` (`decide`). Acceptance line 2: "one click each way". After a failed `POST /api/agent/confirm/{id}` the card says "Try again." But the buttons render only for `pending`, so nothing can be clicked. `decide()` would accept a retry on `failed` (row 10). Nothing shows as confirmed, which is correct. **Fix:** render both buttons on `failed` as well. Add a harness option that fails the confirm route, and a test that a second click sends a second request.

5. **minor** · `src/grid/ask.js:71`, `:121-125`, `:842`. Acceptance line 1: "the dock renders on all fourteen pages". A malformed `?event=` value (`%E0%A4`) throws an uncaught `URIError` while the module starts, and the dock does not render on `/ask` (row 11). A stored thread whose `turns` is not an array throws in `threadsHtml` (row 12). After that, `load()`'s `.catch(() => absent())` throws again. The path decode at `:62` predates DOCK-2 (`a422de03:45`), so only `:71` is new here. **Fix:** wrap the search-parameter decode in try/catch and treat a failure as no case. In `readSession`, reset any thread whose `turns` is not an array.

6. **minor** · `tests/test_grid_ask_page.py:276-279`. Acceptance line 5: "every existing assertion in the touched test files is kept". `assertEqual(RECEIPT_KEYS, set(build_data.VIEW_RECEIPT_KEYS))` became `RECEIPT_KEYS == set(composer.RECEIPT_KEYS)` plus `RECEIPT_KEYS - {'actions'} == set(VIEW_RECEIPT_KEYS) - {'actions'}`. The new composer pin is stronger. The bake pin is weaker: it no longer requires the bake's key set to hold `actions`, so it passes before and after DOCK-5. I grade this minor, not a removed assertion, for three reasons. The statement still compares the two sets. The bake's acceptance of the v4 receipt is still pinned by the kept and red `TheFixtureBake.test_the_bake_passes_its_own_contract`. And DOCK-1's accepted review allowed the same tolerant form in `test_grid_catalog`. **Fix:** when DOCK-5 widens `VIEW_RECEIPT_KEYS`, the orchestrator or DOCK-5 should restore the exact `assertEqual(RECEIPT_KEYS, set(build_data.VIEW_RECEIPT_KEYS))` in the same batch.

7. **minor** · `src/grid/ask.js:380-387` (`SENTENCES`). Acceptance lines 3 and 4: "status words never stronger than the record's". The fallback template (used only when a view carries no `text`) says "The belief's accepted value is …" without reading `fields.accepted`. The composer cuts the accepted block against the cutoff (VIEW-0 item F), so a belief with no acceptance at the cutoff would still be called "accepted". The outlook template prints "It rests on this belief: no" when `rests_on_this_assumption` is absent, against the packet's "a missing field drops its sentence". The dock's templates also differ in wording from the composer's `TEXT_TEMPLATES`, so two sentence sets now describe the same record. **Fix:** say "The belief's value is …", or condition "accepted" on `fields.accepted`. Drop the rests-on clause when the field is absent. Better still, ask DOCK-1 to ship the per-component template sentences in the view, so that the dock holds no second copy.

8. **minor** · `src/grid/ask.js:549-563` (`nearest`). Acceptance line 3: "offer the nearest recorded answer". When no recorded question shares a word with the question, the dock still offers the first composed answer as "The nearest recorded answer". "When will the synthetic sun rise?" is offered "What does this trip do to the outlook?" (row 5). That claims a nearness that does not exist. **Fix:** with zero shared words, say "A recorded answer on this page:", or offer the page's suggested questions instead.

9. **minor (record)** · `dock-2.md` §3, row 4. The packet says `CopyRules` (unchanged) "now reads every new literal sentence in ask.js". It does not. `authored()` skips every literal that holds `<` or `>` (`tests/test_grid_ask_page.py:670`), and most dock sentences are in such literals. I checked those by hand (row 13), and they pass. **Fix:** correct the sentence. Better still, make `authored()` strip tags instead of skipping the literal, so the test reads the dock's own sentences.

10. **minor (hand-back findings, with recommendations)**. Acceptance line 2: "who is signed in".
    - *Sign-in only on /alerts.* `watchSignIn` reads only `window.firebase`, which only `alerts.html` loads. On the other thirteen pages a signed-in person shows as "Sign in to ask live". A server-read session alone would not change that without a dock change either. The alerts page's own browser tests did not run here (puppeteer-core absent), so no real browser has run the signed-in dock. **Recommendation:** DOCK-5 serves a same-origin session the dock can read (for example `GET /api/agent/whoami` against a session cookie set at sign-in on /alerts). A DOCK-6 item then makes the dock probe it. That adds a request on anonymous pages, which `test_the_dock_renders_on_all_fourteen_pages` pins at exactly one, so the orchestrator decides which pin moves. The other way is the SDK on every page, which is a page HTML change for a layout slice. Also, the 15 × 400 ms poll gives up after 6 seconds if the alerts config call is slow. Have alerts.js signal readiness instead.
    - *Side placement not built.* The dock renders where each page put `#ask`, usually at the foot of the page. Strategy decisions 2 and 11 call for the dock "open at the side", and the stranger's minute depends on it. The harness proves the first screen as DOM order, not pixels. **Recommendation:** a DOCK-6 layout slice. Per page, place the dock at the side at 1280 and below the header at 390. Add a real-browser check of the signed-in stranger screen at both widths.
    - *API shape assumptions* (packet §6, five readings). The dock sends `thread: 'desk'` or `'event:<id>'`, its own session ids, where contract §4 expects a thread id. It sends no `cutoff`, which §4 lists. It expects `view`/`answer` and `confirmations` objects in the turn, `cases` in the threads answer, and `budget.refused`. **Recommendation:** DOCK-3 settles these in `agent-contract.md` itself, whose rule makes a change there a change to all three tasks. The dock then pins the settled shape in one test.

11. **nit** · `src/grid/ask.html:44`, `src/grid/ask.js:945`. Acceptance line 4: "status words". The full-screen intro says "Every answer replays a recorded plan", which is not true for a signed-in person with the service present. After a budget refusal, a signed-in person gets "… the site makes no live model call", the VIEW-1 sentence, right after a live call was refused. **Fix:** "Anonymous answers replay a recorded plan." On a refusal, use a budget-specific status sentence.

12. **nit (DOCK-1)**. Two of the composer's template sentences have 20 or more words: "The outlook record lists the vintages issued by the cutoff, …" (23) and "No price-series record is among this view inputs, …" (21). The dock prints them word for word, which is correct. Copy rule 1 is the composer's to meet, so this goes back to DOCK-1.

### Acceptance, line by line

| Acceptance line | Held? | Evidence |
|---|---|---|
| No page HTML other than ask.html changes; the dock renders on all fourteen pages from the #ask mount with no new script tag (a test lists the pages and checks) | **Yes**, with minor 5 | Row 14. `TheDockPages.test_the_fourteen_pages_carry_the_mount_and_load_no_new_script` and `TheDockInTheHarness.test_the_dock_renders_on_all_fourteen_pages` pass. Rows 5 and 4: harness and real browser. |
| A stranger sees within the first screen of the dock: who is signed in, the open cases, the queue, a question answered, and for each action a line naming what the agent did and its receipt; a write never happens without a confirmation card (tests executed in the harness) | **No** | The dock itself never writes without a click (rows 6 and 10; `test_no_write_runs_without_a_click…`, `test_decline_writes_nothing`). But it shows a write as done when the confirmation is still pending (finding 1, major). Minors 2, 3, 4 and 10 also bear on this line. |
| Every figure shown is read from the composed answer's record fields; the dock does no arithmetic and invents no sentence; insufficient answers name the missing record and offer the nearest recorded answer | **Yes**, with minors 7 and 8 | I read `ask.js` in full. It has no `Math`, no arithmetic on any field, and no numeral literal in output. Numbers reach the page only through `esc(field)`. Sentences come from fixed labels, the composer's `text`, `REASONS` (pinned word for word and per slot) and the `SENTENCES` templates. `test_an_insufficient_answer_names_the_missing_record_and_offers_the_nearest` passes. The view.v3 set renders (`test_a_view_v3_plan_set_still_renders`, row 18). |
| Copy rules 1 to 7; every figure with its record as-of; status words never stronger than the record's | **Yes**, with minors 7 and 9 and nit 11 | Row 13. Action cards carry their start and end times. Component as-of lines are VIEW-1's. |
| Every existing assertion in the touched test files is kept; the full offline suite passes; no live call | **Yes, conditionally**, with minor 6 | Row 19: no method dropped, and every shape move is as strict or stricter. Row 2: exactly the two named DOCK-5 reds. No live call: the agent routes are a labelled fixture inside the harness. |

The brief's other checks: sessionStorage is read and written only inside try/catch (`ask.js:106-135`). It holds the session's threads, signed-in or not, and no thread leaves the browser except the session thread id sent in a signed-in `ask` (finding 10). No Firebase app is started anywhere: no `initializeApp`, script injection or dynamic import (`test_the_dock_ships_from_the_panels_own_files`). The transport is only `fetch(DATA + …)` and `fetch(AGENT + path, …)`, with no EventSource, XHR or WebSocket. The three reason slots match the composer word for word (`test_the_docks_reason_slots_are_the_composers_word_for_word`). The one passive key, `proposes_a_change`, is shown as its key.

### Verdict

**rework.** Finding 1 is major: the brief names this exact attack, and the dock fails it. Exact rework for round 2:

1. Fix finding 1 as stated, with the two harness tests. This is required.
2. Fix findings 2, 4 and 5. Each is a one-line guard with one test. These are expected in the same round.
3. Fix findings 3, 7, 8, 9 and nit 11 where they fit in the same round. Otherwise record each as a named hand-back in `dock-2.md` §6.
4. Record finding 6's restore step and finding 10's three recommendations in `dock-2.md` §6. Assign them to DOCK-5, DOCK-3 and a DOCK-6 layout slice. Pass nit 12 to DOCK-1.
5. Before review, merge `task/DOCK-1` at its tip `c34b2c57`, which clears the `repo.py check` link. Then rerun the verify command, the full suite (still exactly the two DOCK-5 reds), `plan.py scope DOCK-2 task/DOCK-1`, `repo.py check` and `git diff --check`, and paste the results.

## Round 2

| Field | Value |
|---|---|
| Task | DOCK-2: the dock on every page |
| Branch | `task/DOCK-2` in `.local/wt/DOCK-2` |
| Commit under review | `c1ae95d8` (rework `9bec9808`, record `c1ae95d8`) |
| Base | `433c2537` (round 1). The branch also merged `task/DOCK-1` at `c34b2c57` and `task/DOCK-3` at `4ac679cd`, both accepted and both ancestors of HEAD. Only DOCK-2's own files are judged: `git diff 433c2537..c1ae95d8 -- src/grid/ask.js src/grid/ask.css src/grid/ask.html tests/test_grid_ask_page.py tests/fixtures/grid/catalog/ask-render.mjs docs/work/desk-agent-and-book-2026-10-18/dock-2.md` |
| Reviewer | Claude Opus 5.5 in-session subagent. Read-only and independent. Offline. Interpreter `/usr/bin/python3`. |
| Date | 2026-10-18 |
| Verdict | **rework**. Every round-1 finding is closed. One new major finding (R2-1) comes from DOCK-3's confirm answer, which reached this branch only in the directed merge. |

### What I verified by running

All runs were at `c1ae95d8`. The attack fixtures are built from the test file's own `agent_fixture()`. Changed harness copies live in the scratchpad only.

| # | Command | Result |
|---|---|---|
| 1 | `/usr/bin/python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| 2 | Full offline suite, `-m unittest discover -s tests -p "test_*.py"` | `Ran 2817 tests in 247.798s` · `FAILED (failures=2, skipped=115)`. The only failures are the two expected `VIEW_RECEIPT_KEYS` reds: `test_grid_ask_page.TheFixtureBake.test_the_bake_passes_its_own_contract` and `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag`. |
| 3 | `-m unittest tests.test_grid_ask_page` | `Ran 85 tests` (77 before, 8 new) · `FAILED (failures=1)`: the expected `TheFixtureBake` red only |
| 4 | The browser classes with ms-playwright Chromium 1234 (same five modules as round 1) | `Ran 231 tests in 49.109s` · **OK (skipped=12)** (4 compression, 8 puppeteer-core) |
| 5 | Harness by hand on `event.html /event/syn-bay-unit-2-trip`, `index.html /` and `ask.html /ask` | All `ok`. One request each (the plan set). 3 answers each, "Stable across 4 wordings". The no-shared-word question gets `offer: -1`. |
| 6 | Hostile strings (the round-1 fixture) | No raw `<script>`, `<img` or `onerror=` attribute on any screen, and no `href="//`. The only link is the encoded case link. Finding 2 is closed. |
| 7 | Write reported `done` with id `conf-fixture-1` still pending | Before the click it shows "The service reports this write as done, but your confirmation is not recorded: …" (`unconfirmed`), beside the pending card. After Confirm it shows "Saved the decision …" (`done`). Finding 1 is closed. |
| 8 | The same, then Decline | Unconfirmed before and after. It never shows as done. See nit R2-5. |
| 9 | Pending write with no click, the stock fixture | "… It waits for your confirmation." After Decline: "… You declined it." |
| 10 | The service's turn says the confirmation is `confirmed`, with no click in this dock | Shows as done. This follows the coordinator's round-2 rule ("from the click answer, the turn's confirmations or the queue"): the service's confirmation record is the person's recorded decision, possibly made in another tab. It is a recorded trust boundary, not a finding. |
| 11 | Unknown action `delete_case` done, and `mark_stale` needing confirmation with no id | "The service reports an action outside the catalogue. The dock cannot say what it did." and the unconfirmed write sentence. Finding 3 is closed for runs. |
| 12 | A refused proposal with an unknown name and a sentence-like argument, added to the bake's `ask.json` (scratch copy) | The argument does not appear outside the receipt fold. Finding 3 / R2-1 of DOCK-1 is closed. The line reads "The composer refused Proposed an action the catalogue does not know." (nit R2-4). |
| 13 | `budget.refused` turn | Status: "The dock reached the day's live budget. No recorded plan answers this question." Status line: "Fixture plans, labelled synthetic. The dock reached the day's live budget and answers from recorded plans." The budget line states the refusal. Nit 11 is closed. |
| 14 | Confirm POST answers 500 (`confirm_fails`) | "The agent service did not record your answer. Try again." with both buttons. Never confirmed. Finding 4 is closed. |
| 15 | `?event=%E0%A4` on /ask; a stored session `{"active":"nowhere","threads":{"desk":{"turns":"x"},"event:a":5}}` | Both `ok`, the dock heading is present, 3 questions. Finding 5 is closed. `/event/%E0%A4` on the event page still throws at `ask.js:62`. That path decode is VIEW-1's and predates DOCK-2, so it is not charged here (see R2-6). |
| 16 | **New probe:** a scratch harness copy that answers Confirm with DOCK-3's real shape when the write fails: `{state: 'confirmed', receipt: {outcome: 'refused', reason_key: 'write_failed', …}}` (`src/agent/service.py:535-580`) | The card says "You confirmed this at 2026-10-18T09:01:00Z. The record cites confirmation conf-fixture-1." The action card says "Save the decision … You confirmed it." Its receipt line is still the old `needs_confirmation` one. Neither shows `write_failed` or the refused receipt (finding R2-1). |
| 17 | `CopyRules().authored()` | 72 sentences read with the tags stripped. All rules pass. Finding 9 is closed. |
| 18 | `answer_question(<outlook question>, records, '2026-10-15T00:00:00Z', fixture_backend())['missing']` at `c1ae95d8`, and `src/judgment/view.py:692` at `433c2537` and at HEAD | `'no outlook vintage is issued at or before the view cutoff'` in both. The wording did not move (minor R2-2). |
| 19 | `plan.py scope DOCK-2 task/DOCK-3` (`4ac679cd`) | `OK: all changed files inside DOCK-2 allowed paths` |
| 20 | `git diff --check 433c2537..c1ae95d8`; `git diff --check` | clean; clean |
| 21 | `repo.py check` | `Checked 608 Markdown files, 3857 local links, 5 skills; bootstrap 1399 words.` **PASS**. Caveat: `dock-2.md` now links `../reviews/DOCK-2.md`, which exists only as this untracked file. Commit the review record in the merge batch, or the link goes red for every later branch, as happened with DOCK-1. |
| 22 | `ask.js` and `src/agent/service.py:132-140` | The ask body's `thread` is now the case reference (`desk` or the event id), which matches DOCK-3's `_ask_body`. |

### Round-1 findings, re-checked

| Round 1 | State | Evidence |
|---|---|---|
| 1 major, write shown done with a pending id | **closed** | Rows 7 to 10; `test_a_write_reported_done_while_its_confirmation_is_pending_is_not_shown_as_done`, `test_a_pending_write_stays_waiting_and_a_declined_one_is_never_done` |
| 2 `//evil/x` link | **closed** | `SITE_PATH` refuses a second slash or a backslash. Row 6; `test_go_there_links_only_to_a_page_of_this_site` |
| 3 unknown and refused actions | **closed** (nit R2-4 on wording) | Rows 11 and 12; `test_an_unknown_or_refused_action_is_named_by_the_catalogue_only` |
| 4 failed confirm without buttons | **closed** | Row 14; `test_a_failed_confirm_keeps_both_buttons` |
| 5 crash guards | **closed** (R2-6, pre-existing) | Row 15; `test_a_malformed_case_link_or_a_bad_stored_thread_never_stops_the_dock` |
| 6 tolerant receipt-key pin | **recorded**. The restore step is in `dock-2.md` hand-backs for DOCK-5 and the orchestrator. | — |
| 7 dock `SENTENCES` | **closed**. The templates are dropped. A view without text shows no sentence. | `test_the_dock_composes_view_v4_sentences_from_record_fields` |
| 8 nearest with no shared word | **closed** | Row 5; `test_no_shared_word_offers_no_nearest_answer` |
| 9 CopyRules skipped tags | **closed** | Row 17 |
| 10 hand-backs | **recorded** for DOCK-5, DOCK-6, DOCK-3 (settled) and DOCK-1 | `dock-2.md`, "Hand-backs and recommendations (rework round 1)" |
| 11 intro and budget status | **closed** | Row 13; `ask.html` "Anonymous visitors see recorded answers. Signed-in users ask live." (the pin moved with it, as the review asked) |
| 12 composer sentences of 20 words or more | **passed to DOCK-1** | — |

### Findings, round 2

R2-1. **major** · `src/grid/ask.js` `confirmationCardHtml` (confirmed arm: "You confirmed this at … The record cites confirmation …") and `actionCardHtml` (the `standing === 'confirmed'` arm that is not done: "… You confirmed it." with `actionReceiptLine(run)`). This bears on acceptance line 4 ("status words never stronger than the record's") and line 2 ("for each action a line naming what the agent did and its receipt"). DOCK-3's confirm answer is `{confirmation_id, state, decided_at, receipt}`. When the write fails after the click, `state` is `confirmed` and `receipt.outcome` is `refused` with `write_failed` or `draft_not_open` (`src/agent/service.py:535-580`). The dock stores that receipt in `state.decided[id].receipt` and then uses it only when it is `done`. So when the write did not happen, the dock still says "The record cites confirmation conf-fixture-1". It shows the old `needs_confirmation` receipt line instead of the refused receipt (row 16). This is the same class as round-1 finding 1: the dock reports a write as written when the service's own receipt says it was not. It is new this round only because DOCK-3's settled shape arrived in the directed merge. **Rework:**
- In `confirmationCardHtml`'s confirmed arm, say "The record cites confirmation …" only when `decided.receipt` (or the confirmation's own receipt) has `outcome === 'done'`. Otherwise say, for example, "You confirmed this at X. The service could not write it." followed by the refusal's reason.
- In `actionCardHtml`, when the standing is `confirmed` and the outcome is not `done`, render a refused card: the catalogue name, `reasonText(written, 'refusal')` and `actionReceiptLine(written)`.
- Add a harness fixture flag that answers Confirm with a refused receipt. Pin that neither "record cites" nor "Saved" appears, and that the refused receipt line does.

R2-2. **minor** · `tests/test_grid_ask_page.py` `test_an_insufficient_answer_names_the_missing_record_and_offers_the_nearest`. `assertIn('Insufficient: no outlook vintage is issued', …)` became two substrings, `'Insufficient: '` and `'no outlook vintage'`. The composer's wording did not change (row 18), so the loosening has no reason. It was DOCK-2's own round-1 assertion, so the brief's "every existing assertion" line is not breached. **Fix:** restore the exact substring, or pin `composer`'s own sentence: `'Insufficient: ' + answer['missing']`.

R2-3. **minor** · same file, `test_the_dock_composes_view_v4_sentences_from_record_fields`. `assertNotIn(composer.REASONS['opens_the_page'], report['answers'][1]['html'])` was dropped. It is the slot rule's negative guard (a key in the wrong slot never renders as a sentence). It still holds at HEAD, which I checked by running the shaped set. It is again DOCK-2's own round-1 assertion. **Fix:** restore it.

R2-4. **nit** · `ask.js` `proposedHtml`. The refused unknown proposal reads "The composer refused Proposed an action the catalogue does not know." **Fix:** "The composer refused an action outside the catalogue."

R2-5. **nit** · `ask.js` `actionCardHtml`. A write the service reported `done`, which the person then declined, keeps "your confirmation is not recorded". That is true, but weaker than what the dock knows. **Fix:** "The service reports this write as done, but you declined it." Also, DOCK-3's refusal keys (`write_failed`, `draft_not_open`) are not in `SLOTS.refusal`, so they show as bare keys. That is correct under the dock's rule. DOCK-3 or the orchestrator should decide whether the slot widens with sentences in the composer's catalogue.

R2-6. **nit, pre-existing (VIEW-1)** · `ask.js:62`. The pathname decode throws on `/event/%E0%A4`, and the dock does not render on that event page. **Recommendation:** the same try/catch as `:71`, in this task or the next one that touches `ask.js`.

### Verdict

**rework.** R2-1 is major. The exact rework for round 3:
1. Fix R2-1 as stated, with the harness flag and the test.
2. Restore the two assertions of R2-2 and R2-3.
3. Optionally fix R2-4, R2-5 and R2-6.
4. Rerun the full suite (exactly the two `VIEW_RECEIPT_KEYS` reds), `tests.test_grid_ask_page`, `plan.py check`, `plan.py scope DOCK-2 task/DOCK-3`, `repo.py check` and `git diff --check`, and paste the results in `dock-2.md`.

Everything else in round 2 holds.

## Round 3

| Field | Value |
|---|---|
| Task | DOCK-2: the dock on every page |
| Branch | `task/DOCK-2` in `.local/wt/DOCK-2` |
| Commit under review | `b98c9198` (fixes `5e8dd442`, record `b98c9198`) |
| Base | `c1ae95d8` (round 2). The diff judged is `git diff c1ae95d8..b98c9198`: `ask.js`, `ask-render.mjs`, `test_grid_ask_page.py`, `dock-2.md`. |
| Reviewer | Claude Opus 5.5 in-session subagent. Read-only and independent. Offline. Interpreter `/usr/bin/python3`. |
| Date | 2026-10-18 |
| Verdict | **accept**. "The full offline suite passes" holds on one condition: the two named DOCK-5 reds clear when `VIEW_RECEIPT_KEYS` gains `actions`. |

### What I verified by running

| # | Command | Result |
|---|---|---|
| 1 | `/usr/bin/python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| 2 | Full offline suite | `Ran 2820 tests in 221.416s` · `FAILED (failures=2, skipped=115)`. The two failures are exactly the expected `VIEW_RECEIPT_KEYS` reds: `test_grid_ask_page.TheFixtureBake.test_the_bake_passes_its_own_contract` and `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag`. Nothing else fails. |
| 3 | `-m unittest tests.test_grid_ask_page` | `Ran 88 tests` (3 new) · `FAILED (failures=1)`: the expected `TheFixtureBake` red only |
| 4 | Browser classes with ms-playwright Chromium 1234 (the same five modules) | `Ran 231 tests in 40.759s` · **OK (skipped=12)** (4 compression, 8 puppeteer-core) |
| 5 | Harness by hand on `event.html /event/syn-bay-unit-2-trip`, `index.html /` and `ask.html /ask` | All `ok`. One request each (the plan set). 3 answers each. The dock heading is present. |
| 6 | Harness on `event.html /event/%E0%A4` | `ok`, key `event`, the dock heading is present. R2-6 is closed. |
| 7 | **The round-2 probe**, rerun unchanged: a scratch harness copy that answers Confirm with DOCK-3's failed-write shape (`state: confirmed`, `receipt.outcome: refused`, `write_failed`) | Card: "You confirmed this at 2026-10-18T09:01:00Z. The service could not write it. The service could not write the record." Action card: "You confirmed save_decision. The service did not write it. …", with the refused receipt line (`Receipt: save_decision · refused · started … · ended … · confirmation conf-fixture-1`). No "The record cites" and no "Saved". R2-1 is closed. |
| 8 | The new harness flag `confirm_receipt`, with fixtures built from `agent_fixture()`: a done receipt; refused `write_failed`; refused `draft_not_open` on a write the service had reported done; refused with an unknown key; no receipt at all | **Done:** "Saved the decision …" and "The record cites confirmation conf-fixture-1." **Refused:** the refusal sentence on both cards, never "Saved" or "record cites". **Unknown key:** "Reason key some_new_key." **No receipt:** "You confirmed this at … The dock holds no receipt of the write yet." The action card says "… You confirmed it.", never "Saved". |
| 9 | Decline paths: the stock fixture, and a write the service had reported done | "Save the decision … You declined it." / "The service reports this write as done, but you declined it." The card in both: "You declined this. The dock wrote nothing." Never done. R2-5 is closed. |
| 10 | A write reported done with a pending id, before the click | Unconfirmed ("… your confirmation is not recorded …"). It is done only after Confirm with a done receipt. Round-1 finding 1 still holds. |
| 11 | Hostile-string fixture again | No raw `<script>`, `<img`, `onerror=` attribute or `href="//"` on any screen |
| 12 | `plan.py scope DOCK-2 task/DOCK-3` (`4ac679cd`) | `OK: all changed files inside DOCK-2 allowed paths` |
| 13 | `git diff --check c1ae95d8..b98c9198`; `git diff --check` | clean; clean |
| 14 | `repo.py check` | `Checked 608 Markdown files, 3857 local links, 5 skills; bootstrap 1399 words.` **PASS**. The round-2 caveat stands: `dock-2.md` links this record, so commit it in the merge batch. |
| 15 | `-` lines of `git diff c1ae95d8..b98c9198 -- tests/test_grid_ask_page.py` | Two. The loosened insufficient pin is restored to `'Insufficient: no outlook vintage is issued'` (R2-2 closed). The dropped `assertNotIn(REASONS['opens_the_page'], …)` is back (R2-3 closed). No assertion was removed. |

### Round-2 findings, re-checked

| Round 2 | State |
|---|---|
| R2-1 major, a confirmed write the service refused was said to be written | **closed** (rows 7 and 8; `test_a_confirmed_write_the_service_refused_is_never_said_to_be_written`) |
| R2-2 loosened insufficient pin | **closed** (row 15) |
| R2-3 dropped slot guard | **closed** (row 15) |
| R2-4 "The composer refused Proposed …" | **closed**: "The composer refused an action outside the catalogue." |
| R2-5 done then declined | **closed** (row 9). DOCK-3's refusal keys now have sentences in `SERVICE_REASONS`. `test_every_refusal_key_of_the_agent_service_has_a_sentence` reads the keys from `src/agent/service.py` and `budget.py`. |
| R2-6 path decode | **closed** (row 6) |

### Findings, round 3

R3-1. **nit** · `ask.js` `confirmationCardHtml`, refused arm, with `SERVICE_REASONS['write_failed']`. The card repeats itself: "The service could not write it. The service could not write the record." **Fix:** drop the fixed sentence when the key is `write_failed`, or give that key "The write failed on the service side."

R3-2. **nit (hand-back to DOCK-3 and the orchestrator)** · `ask.js` `SERVICE_REASONS`. The sentences for DOCK-3's refusal keys are the dock's own, a fixed label per key. They are short and active and say only what the key names, so I accept them under "invents no sentence". The pin finds the keys by regex over the service source, so a key spelled differently (for example a new constant) would escape it. **Recommendation:** DOCK-3 exports one refusal catalogue (key → sentence), as the composer does with `REASONS`. The dock then copies it word for word under the same pin as `REASONS`.

Carried hand-backs, unchanged: restore the exact `RECEIPT_KEYS == set(build_data.VIEW_RECEIPT_KEYS)` pin when DOCK-5 widens the constant (round-1 finding 6); sign-in beyond /alerts and the side placement for DOCK-5 and DOCK-6 (round-1 finding 10); the composer's two long sentences and the passive `proposes_a_change` for DOCK-1 (round-1 nit 12).

### Acceptance, line by line

| Acceptance line | Held? |
|---|---|
| No page HTML other than ask.html; the dock renders on all fourteen pages from #ask with no new script tag | **Yes** (round 1 rows 14 and 5, still passing; rows 5 and 6 here) |
| A stranger sees who is signed in, the open cases, the queue, a question answered, and each action with its line and receipt; no write without a confirmation card | **Yes**, in the harness (rows 7 to 10). A write is past tense only on a confirmed confirmation with a done receipt. |
| Every figure from record fields, no arithmetic, no invented sentence; insufficient answers name the missing record and offer the nearest | **Yes** (round 2 closures; R3-2 noted) |
| Copy rules 1 to 7; figures with their as-of; status words never stronger than the record's | **Yes** (`CopyRules` reads the tagged literals, including the new ones; R3-1 is a nit) |
| Every existing assertion kept; the full suite passes; no live call | **Yes, on condition of** the two named DOCK-5 reds (row 2). No assertion was removed (row 15). |

### Verdict

**accept** at `b98c9198`, on condition of the two `VIEW_RECEIPT_KEYS` reds that DOCK-5 clears. No major finding stands. R3-1 and R3-2 are nits for a later slice. The orchestrator should do three things in the merge batch:
1. Commit this record with the merge.
2. Widen `VIEW_RECEIPT_KEYS` by `actions`.
3. Restore the exact receipt-key pin.
