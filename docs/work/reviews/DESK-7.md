
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `fac85d72`, 2026-10-17 21:32, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-7 independent review: verdict **rework**
> 
> I reviewed commits `8ee7086d` and `fac85d72` on `task/DESK-7`, branched from `d716d4dd`. I compared them with `feat/product-gap` (now `73a9fc44`) against the brief as printed. This is an independent review: I did not write the change, and I edited no tracked file.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` | `Ran 95 tests in 2.765s`, **OK (skipped=3)**. The 3 skips are the `LiveServer` tests, which need FastAPI. All 9 new DESK-7 tests ran and passed. |
> | `/usr/bin/python3 scripts/plan.py scope DESK-7 feat/product-gap` | `OK: all changed files inside DESK-7 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2201 tests in 197.440s`, **OK (skipped=58)**. Matches the task record. |
> | `git merge-tree feat/product-gap HEAD` | Conflicts in `docs/work/PROGRESS.md`, `docs/work/tasks.json` and `tests/fixtures/grid/page/browser.mjs`. `event.js`, `event.html`, `event.css` and `test_grid_event_drivers.py` merge cleanly. |
> 
> Not run: `plan.py check`, `repo.py check` and the browser classes (this environment has no browser).
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.**
>    - Met: the desk line sits before the tabs in the page's element order. The no-judgment, synthetic-judgment and real PEDC views are all pinned. The three "Show the records" folds are pinned, the save wait and the refusal text are pinned, and the suite passes.
>    - Not met: the outlook sentence does not name the outlook's month. The Import and Demand tiles name no interval, so "every figure with its record as-of" is not met. The wording "up to 30 seconds" comes from no record. All three are findings below.
>    - Not checked here: "the first screen" relies on the executor's screenshots under the ignored `.local/`, which I could not view.
> 2. **Every changed file inside the allowed paths: yes.** `plan.py scope` printed OK. `tests/fixtures/grid/` is an allowed path.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** The diffs of the two test files only add lines. The harness changes are parser fixes: comments are skipped, text between tags is kept, and the title-wait condition was adjusted.
> 4. **No new dependency, service, network call or model call: yes.** The page reads only the baked view and the existing adapter.
> 5. **Mode labels truthful: no.** The impact card's new opening sentence always says "synthetic portfolio", whatever the record says. Finding 3 below.
> 6. **No invented facts or numbers: no.** "Up to 30 seconds" is not in any record. Everything else is read from the view: the flip rate from the `agree` values, the reserve figure of 150 from `market.short` at the timeline's 14:45 market row.
> 7. **Task record has commands, results and the next action: yes, with one inaccuracy.** Its acceptance table says "the tile lines carry their intervals", but its own §4 admits Import and Demand carry none.
> 8. **No contradiction with strategy or invariants: no.** The base revised the wait wording at `13456a8b` and measured the cold start at 3.6 s at `74a78489`. The branch ships the superseded wording.
> 
> ## Findings
> 
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/grid/event.js:557-559` | The outlook's opening sentence uses the horizon's *label* ("month"), not the month itself. The output asks for "the outlook's month". | The pinned text is "The price outlook for the month horizon has information cutoff 25 Aug 2026 16:00 UTC". The fixture `outlook-fixture-2026-11-system` has `horizon.start` 2026-10-25T16:00Z and `horizon.end` 2026-11-25T16:00Z, and `outlookHtml` (line 476) already prints that window. | Name the window from `horizon.start`/`end`, or the month the record names. Update the pin at `tests/test_grid_event.py:981-983`. |
> | important | `src/grid/event.js:276-292` | Only the Price and Reserve tiles name an interval. Import (369) and Demand (2,449) show none, and the row now mixes 14:30 and 14:45 figures with two of them unlabelled. | In the recorded view, `imp` at 14:30 is 369. The reserve tile moved to 14:45 (150), while its neighbours stay at the unstated 14:30. Task record §4 says "the record states no interval for them". | Inferring the interval from a value match would invent a fact, so don't. Either the bake input states each figure's time (e.g. "Import at 14:30"; `ownTime` already reads a key like that), or hand this back as a stop condition. Either way, correct the task record's acceptance row. |
> | important | `src/grid/event.js:517-518` | The impact card's opening sentence always says "a method demonstration on a synthetic portfolio, never a business number". It ignores `i.synthetic` and `i.label`, even though line 521 already handles `synthetic` being false. No test pins `im-plain`. | No `impact` `plain` assertion exists in `tests/`. The render harness reports the field but nothing checks it. | Build the sentence from the record's own label, with a different branch when `synthetic` is not true. Pin it on the recorded impact view. |
> | important (disposition: orchestrator) | `src/grid/event.js:939`; pins at `tests/test_grid_event.py:658-659, 709-710` | The executor followed the printed brief. But the base changed the wording to "Saving… the service may need time to wake" (`13456a8b`) and measured the cold start at 3.6 s (`74a78489`). "Up to 30 seconds" is a number from no record. | `git show feat/product-gap:docs/work/tasks.json` against `d716d4dd` | In the rework, adopt the base's wording and change both pins. This records brief drift; it is not a fault of the executor. |
> | minor | `src/grid/event.js:282` (brief wording) | "Price, peak after the trip, 14:30" sits above the tile's own line "₱32,000 at 13:30". The price sat at 32,000 before the trip as well, so "after the trip" reads stronger than the record. | `lmp` is 32,000 at 13:30, 13:45, and 14:15–14:35 | Leave it to the brief owner. The executor implemented the brief's own words. |
> | minor | `src/grid/event.js:970-972` | The retry sentence repeats or contradicts some adapter messages. Examples: "…the decision was not recorded. The decision was not recorded. Try again." (event-api.js:109, :177), and "Try again" after the local-preview "Decisions are recorded on the hosted demo." The pinned STALE_HEAD line shows "STALE" and a semicolon on the page. | `src/grid/event-api.js:44, 57, 109, 177` | Skip the added sentence when the message already says so, and skip "Try again" for the local preview. Optionally reword the STALE_* messages, since `event-api.js` is an allowed path. |
> | minor | `src/grid/event.js:82` | The brief does not name the `unrelated` → "no change to this assumption" mapping. | Task record §10 asks for a ruling. | Reviewer ruling: acceptable. It matches the label's meaning and is pinned. |
> | minor (record) | `tests/fixtures/grid/page/browser.mjs` | Both sides fixed the same pipe-flush bug differently, so they conflict. `PROGRESS.md` and `tasks.json` also conflict. | Output of `git merge-tree` | At merge, take the base's `browser.mjs` (it adds `exitCode` and a trailing newline). Do not rebase the task branch. |
> 
> Not a finding: the limits line "…nothing is live" is the view's own sentence and the project's standard phrasing (START-HERE.md:39). It is not a status claim.
> 
> ## Verdict: rework
> 
> Two acceptance items were not demonstrated: the outlook's month is not named, and Import/Demand have no as-of interval. The impact card's opening sentence asserts "synthetic" whatever the record says. The rest (desk line, folds, save wait, ask link, tests, scope, full suite) is sound and should be kept as it is.
> 
> One scratch file, `.local/desk7-review.diff`, was written to the ignored `.local/` folder during this review; it can be deleted.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `f2f9c553`, 2026-10-17 21:54, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-7 independent review, round 2: verdict **rework**
> 
> I reviewed `task/DESK-7` at `f2f9c553`, which branches from `d716d4dd`. I compared it with `feat/product-gap` (now `73a9fc44`) using the three-dot diff, the brief and `docs/engineering/review-and-feedback.md`. I did not write this change and I edited no files.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` (verify) | `Ran 97 tests in 2.855s`, **OK (skipped=3)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-7 feat/product-gap` | `OK: all changed files inside DESK-7 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2203 tests in 210.506s`, **OK (skipped=58)** |
> | `git merge-tree --write-tree feat/product-gap HEAD` | Conflicts only in `docs/work/PROGRESS.md` and `docs/work/tasks.json`. `event.js`, `event.html`, `event.css` and `test_grid_event_drivers.py` merge cleanly. `browser.mjs` is now byte-identical to the base. |
> 
> I did not run `plan.py check`, `repo.py check` or a browser. I looked at the executor's screenshots in `.local/desk7-real-{1280,390}.png`. They date from 20:24, before the rework commit, so they show only the layout and the folds. The reworked copy is shown by the harness pins, not by the screenshots.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.**
>    - **Met:**
>      - The desk line sits under the title and before the tabs. At 390 px the AI card and the person card both fit in the first ~660 px, and neither card shows a digest.
>      - The three "Show the records" folds keep the outlook id, the register links and the digests on the page (`test_grid_event.py:965-988`).
>      - The `by` field is shown as recorded and the page adds no "live" (`:1394-1397`).
>      - The flip rate of 0 matches the receipt ("max flip rate 0").
>      - The save wait, the refusal text and the "Your copy" heading are all pinned.
>      - The suite passes and no existing assertion was removed.
>    - **Not met:** "every figure with its record as-of" fails for the Import and Demand tiles. The record states no time for either figure, so the executor handed the item back.
> 2. **Every changed file inside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.**
>    - The branch changes only `state` and `self_review` in the task's `tasks.json` entry.
>    - The diffs of both test files have zero removed lines.
>    - The harness changes are parser fixes. The title-wait condition now also skips the em-dash placeholder, because text between tags is now parsed.
>    - The STALE_HEAD pins at `:666-667` still hold.
> 4. **No new dependency, service, network call or model call: yes.**
> 5. **Mode labels truthful: yes.** The impact card's opening sentence now follows `synthetic` and `label`. Both branches are pinned (`:1323-1339`).
> 6. **No invented facts or numbers: yes.**
>    - "Up to 30 seconds" was replaced with the base's wording.
>    - The hand-back for Import and Demand is correct:
>      - No script in the repository writes `figures`; they come straight from the orchestrator's `.local` snapshot.
>      - Import 369 occurs at both 14:30 and 16:05 in the series, so matching on the value would be ambiguous as well as invented.
>      - Demand has no series at all.
> 7. **Task record has interpreter, commands, results and the next action: yes.**
> 8. **No contradiction with strategy or invariants: yes.** The wait wording and the "nothing is live" ruling both match the base at `13456a8b`.
> 
> ## Findings
> 
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `tests/test_grid_event.py:1441-1442` | The pin requires the bare keys `<div class="k">Import</div>` and `Demand`. The task record's own next step is for the orchestrator to change the bake key to `Import at 14:30`. The tile would then render `Import at 14:30`, this assertion would fail, and the verify command would go red. The pin meant to stop a value-match shortcut also blocks the approved fix. | `renderFigures` uses `key = f.k` for any figure that is not the price peak (`event.js`, `renderFigures`). `ownTime` reads `HH:MM` from `k`. | Derive the pin from the view. For each figure whose `k` has no time and is not the reserve tile, assert the rendered key equals `f['k']` and its sub-line has no "interval". For a key that carries a time, assert it renders as written. |
> | important (disposition: orchestrator) | bake input `.local/grid-snapshot/events/pedc-u2-2026-09-21.json` `figures[2..3]` | The Import and Demand tiles name no interval. The tile row now mixes Price at 14:30 and Reserve at 14:45 with two unlabelled figures. The acceptance item is not demonstrated. | `figures` = `Import` 369 and `Demand` 2,449 with no time. Import 369 appears at both 14:30 and 16:05. The view has no demand series. | The orchestrator states each figure's time in the bake key, using the source the figures were assembled from. Until then the item stays open in the task record. This is not the executor's fault. |
> | minor | `src/grid/event.js` `renderPerson` (read-only branch) | The read-only person-card branch, which shows `V.decision.note`, has no pin. The brief asked for pins on both desk cards. | Grep finds only `test_the_view_carries_the_decisions_as_read_only` (`:1669`), which checks the view and not the card. | Render the CORP-5 read-only view and pin `dp-line` to the view's own note. |
> | minor | `src/grid/event.js` `renderDesk` (`forms`) | "in N wordings each" uses the largest answer count across questions. A question with fewer wordings would make "each" overstate it. | `forms = questions.reduce(max(answers.length))` | Say "each" only when every question has the same count. Otherwise say "up to N". |
> | minor (record, merge) | `docs/work/tasks.json` DESK-7 entry | The branch's entry still carries the old `note` and `outputs`: no "nothing is live" ruling, and the "up to 30 seconds" wording. If the branch's side wins at merge, the brief goes back to the wording this rework dropped. | My field-by-field comparison of `feat/product-gap` and HEAD | At merge, take the base's `note` and `outputs` and keep the branch's `state` and `self_review`. Resolve `PROGRESS.md` the same way. Do not rebase. |
> | minor (carried from round 1) | `src/grid/event.js:282` | "peak after the trip, 14:30": the price was 32,000 at 13:30 too (before the trip), and first reached 32,000 after the trip at 13:45. | the `lmp` series | Leave this to the brief owner. The wording is the brief's own. |
> 
> Not a finding: `STALE_HEAD` still shows as a code. It quotes the route, and GRID-3 pins it at `:666`.
> 
> ## Verdict: rework
> 
> One acceptance item ("every figure with its record as-of" for Import and Demand) is still not demonstrated. The executor can fix one important defect themselves: the Import/Demand pin would turn the orchestrator's own fix into a failing verify. Everything else holds and should be kept as it is: the desk line, the folds, the impact card's standing, the save wait, the refusal text, the ask link, scope and the full suite. The bake-input change stays open with the orchestrator.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.


Orchestrator note for round 3 (2026-10-17 22:00): the bake input now labels the tiles "Reserve short at 14:30", "Import at 14:30" and "Demand at 14:30" (verified against regions_5min.csv at 2026-09-21T14:30: CVIS demand 2449.12, import 369.44, reserve short 133.17, price 32000). Make the tile pin accept a key of the form "<name> at HH:MM" (never a bare key) and keep every other pin. Fix the two minors (pin the read-only person card to the view note; say "each" only when every question has the same wording count, else "up to N"). Do not touch docs/work/tasks.json note or outputs.

## Round 3 — 2026-10-17 22:15, Claude Opus 5.5 in-session reviewer (read-only, independent; run by the orchestrator after the runner's two rounds)

Range reviewed: d716d4dd..af593a9f (task/DESK-7), against the ruling brief on origin/main. The reviewer's output, verbatim:

### Reviewer line

Reviewer: Claude Opus 5.5 (claude-opus-5-5), in-session subagent, read-only and independent of the author. I am the fallback while the Codex reviewer is unavailable. I reviewed `task/DESK-7` at `af593a9f`, from merge base `d716d4dd` with `origin/main`, against the ruling brief on `origin/main` (`git show origin/main:docs/work/tasks.json`). I edited no tracked file and ran no git write command. My only scratch output is under the session scratchpad.

### Commands run

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_grid_event_drivers` (verify) | `Ran 99 tests in 3.118s`, **OK (skipped=3)**. The 3 skips are the FastAPI `LiveServer` tests. |
| `/usr/bin/python3 scripts/plan.py scope DESK-7 origin/main` | `OK: all changed files inside DESK-7 allowed paths`, exit 0. This covers `src/grid/event-api.js`, `tests/fixtures/grid/event/render.mjs` and `tests/fixtures/grid/page/browser.mjs`, which are in the diff but outside the brief's list of six. `plan.py` allows them, as rounds 1 and 2 also found. |
| `git diff d716d4dd..HEAD -- tests/test_grid_event.py tests/test_grid_event_drivers.py \| grep -c '^-[^-]'` | `0`: no line was removed from either test file against the base, so every existing assertion is kept, GRID-3's pins included. |
| Field-by-field comparison of `tasks.json`, `d716d4dd` against HEAD | Only `DESK-7` differs, and only in `['state', 'self_review']`. |
| `grep` for inline `<script>`/`<style>`/`style=` in `src/grid/event.html` | None. The only scripts are the two external `event-api.js` and `event.js` tags. |
| `node tests/fixtures/grid/event/render.mjs` on a scratch copy of the real bake input | `ok: true`, `errors: []`. |
| Semicolon and "stale" scan of the rendered desk text and saving line | `[]`: none found. |
| `grep` of `docs/work/product-gap-2026-10-17/desk-7.md` §13 | The hand-back is closed in words (lines 329, 335). The quoted `Ran 99`, `Ran 2205` and tile values match what I observed. |

Not run by me: the full offline suite (a suite may be running in parallel in this worktree, and fixed loopback ports collide between runs). Round 2 measured `Ran 2203 … OK (skipped=58)`; the executor records `Ran 2205 … OK (skipped=58)` for round 3; the orchestrator's own run on this tree: `Ran 2205 tests`, `OK (skipped=58)`. I also did not run `plan.py check`, `repo.py check` or a browser.

### Findings

| Severity | Location | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| none (round-2 important, fixed) | `tests/test_grid_event.py:1427-1488` | The tile pin now comes from the view. Each `figure['k']` must match `^.+ at [0-2]\d:[0-5]\d$`, so a bare key fails. Each rendered key must equal the view's key, except the price peak form. Each shown value must equal the five-minute series (`lmp`/`short`/`imp`) at the named interval. Demand is pinned to its baked value, and the test checks that the view has no `dem` series. | Rendered tiles: `Price, peak after the trip, 14:30` ₱32,000, `Reserve short at 14:30` 133 MW, `Import at 14:30` 369 MW, `Demand at 14:30` 2,449 MW. In the bake input, `short`@14:30 = 133, `imp`@14:30 = 369 and `lmp`@14:30 = 32000. This matches the orchestrator's note (regions_5min.csv: 133.17, 369.44, 2449.12, 32000). | None. |
| none (round-2 minor, fixed) | `tests/test_grid_event.py:1977-1987` | The read-only person-card branch is pinned. `dp-line` must equal `RULES_VIEW['decision']['note']` word for word. | New test `test_the_person_card_carries_the_views_own_read_only_note`, which passes. | None. |
| none (round-2 minor, fixed) | `src/grid/event.js:114-120`, `tests/test_grid_event.py:1124-1133` | The card says "N wordings each" only when every question has that count, and "up to N wordings" otherwise. Both branches are pinned. | The real view renders "It answered 8 questions in 4 wordings each. The highest flip rate was 0." | None. |
| none (acceptance check) | `event.html`, `event.js` | Every brief output I could check by running is present (listed below). | Real-view harness output and pins. | None. |
| none (brief owner, recorded explicitly) | rendered reserve figures | The tile reads "Reserve short at 14:30" with 133 MW, while the timeline row and chart label read "150 MW short" and "Reserve shortfall 150 MW at 14:45". Each figure is the record's value at the interval it names. | Tile 133 at 14:30 (`short` series 133); chart and timeline 150 at 14:45 (`short` series 150). Task record §13 line 329 states this supersession. | No code change. Flag it to the owner at merge: two reserve numbers stay on the page, now each with its interval. |
| minor | `src/grid/event.js:274-296` (`reserveFigure` and the interval note in `renderFigures`) | That branch runs only for a reserve key with no time in it; every key in the real view now carries a time, so no pinned tile assertion reaches it. | No tile pin on a bare reserve key. | Not a defect. Either pin it on the synthetic view or drop the fallback later. |
| minor (record) | `tests/test_grid_event.py:1370-1376` | The real-record class reads the ignored bake input and skips when it is absent, so the tile and AI-card pins on the real view run only where `.local/grid-snapshot` is linked. | `@unittest.skipUnless(REAL_EVENT_VIEW.is_file(), …)` | None. The synthetic-view pins still run everywhere. |
| minor (copy, no action required) | `src/grid/event.js:128` | The AI card prints the rule exactly as recorded ("The rule that fired: outage_or_later: Q2=forced_outage, Q3=same on an availability kind"), code-like text in a card meant for strangers; defensible because the page must not reword records. | Rendered `desk.ai.rule`. | Leave it, or give the rule a plain gloss in a later task. |
| minor (carried, brief owner) | `src/grid/event.js` `renderFigures` (peak form) | "Price, peak after the trip, 14:30": the price was already ₱32,000 at 13:30, before the trip; the tile's own sub-line shows this. | `lmp` series | The brief owner decides. |
| minor (merge, carried) | `docs/work/tasks.json`, `docs/work/PROGRESS.md` | Both files will conflict at merge; the branch's `DESK-7` entry carries the older `note` and `outputs`. | Field comparison above. | At merge, take main's `note`/`outputs` and keep the branch's `state`/`self_review`. Do not rebase. |

Acceptance outputs confirmed: the desk line sits under the title and before the tabs; the AI reader card shows the `by` field verbatim ("gemini-3.8-flash · Vertex AI · recorded 14 Oct 2026"), the model, "8 questions in 4 wordings each", flip rate 0, the label, the rule, and "challenges proposes opening the assumption for review", ending with "You decide below." and a link to `#decision`; the person card reads "No analyst decision is recorded on the real case. What you record goes to your own copy." and after a save shows the decision in words with its receipt; three `<details>` "Show the records" folds (outlook, impact, judgment receipt), each card opening with a plain sentence, the impact sentence branching on the record's `synthetic` flag and `label`; "Saving… the service may need time to wake · 0 s" with a seconds counter and a retry sentence on refusal; the history heading reads "Your copy" after a save; "Ask the desk" renders only when the view has `ask: true`; none of the page's own strings contains "live" (the view's own limits sentence "…nothing is live." is the ruled negation).

### Verdict: accept

All three round-2 items the executor owned are fixed and pinned: the tile pin now comes from the view and fails any key that names no interval; the read-only person card is pinned to the view's own note; the wording count says "each" only when it is true. The orchestrator's bake input labels all four tiles at 14:30, and each rendered figure equals the record's series value at that interval, which closes the last open acceptance item. Scope is OK against `origin/main`, the verify command is green at 99 tests, no assertion in either test file was removed, `tasks.json` changes only DESK-7's `state` and `self_review`, and the page has no inline script or style. What remains is minor and needs no executor rework: an untested bare-key reserve fallback; copy choices for the brief owner (the 14:30-versus-14:45 reserve pair and "peak after the trip"); the carried merge instruction.
