
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `6c527bf0`, 2026-10-17 21:00, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # VIEW-0 review: verdict **rework**
> 
> I'm an independent reviewer and did not write this change. I reviewed commit `6c527bf0` on `task/VIEW-0` against `feat/product-gap-b` at `13456a8b`. The branch has one commit touching five files, all inside the allowed paths.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_judgment_view` (the verify command) | `Ran 54 tests` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope VIEW-0 feat/product-gap-b` | **OK**: all changed files inside VIEW-0 allowed paths |
> | Full suite, python only (`PATH=/usr/bin:/bin`, empty `HOME`) | `Ran 2253 tests in 149.453s` · **OK (skipped=196)** · exit 0 |
> | Full suite with node visible | `Ran 2240 tests` · FAILED (errors=1, skipped=58). The one error is `test_grid_page.BrowserPage.setUpClass` (`JSONDecodeError … char 64847`), the same browser-harness error the packet records. It is a browser-guarded class, so it is outside this review. |
> | Probes run through the real functions (results under the findings) | see below |
> 
> I did not edit any repository file. The only things I created are ignored scratch under `.local/`: an empty HOME directory and a suite log.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: no.**
>    - Met: the six rules each have a test class; no live call is made (the transport would fail if called and its call list stays empty); the web-layer and no-file rule is pinned by an AST test; the full offline suite passes.
>    - Not met: "no figure originates in a plan". The validator accepts non-ASCII numerals (finding 1).
>    - Met only in name: "the live backend exists". `LiveView` is not a working Gemini backend (finding 5).
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** Two new files plus one-line state edits in `tasks.json` and `PROGRESS.md`.
> 4. **No new dependency, service, network or model call: yes.**
> 5. **Mode labels truthful: no.** The receipt states cutoff 13:39:37+08 but the view shows records from after it (finding 3). `LiveView` would label any injected callable's output as `gemini` / `live_inference` (finding 5). The fixture backend's `synthetic_fixture` label is correct.
> 6. **Unknowns stayed unknown, no invented facts: no.** The test's judgment record is the trip-cutoff compile, but it carries the return cutoff's disagreement as unresolved (finding 4). The impact figures, IMPACT label, digest and live-run receipt figures all check out against `impact.md`, `live-run-2026-10-14.md` and `grid-desk/event.md`.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** But its next action ("record live plans with an injected transport") cannot work with the repository's `GeminiTransport` (finding 5).
> 8. **Nothing contradicts the paper: no.** Section 10 F1 says parts are filled "under the cutoff and mode", and rule 6 says insufficient answers name the missing record (findings 3 and 6).
> 
> ## Findings
> 
> **1. important | `src/judgment/view.py:154` (used at :449)**
> - **Mechanism:** `_NUMERAL = re.compile(r'[0-9]')` only matches ASCII digits, so rule 4 can be bypassed and a figure can originate in a plan.
> - **Evidence:** through `validate_response`, these texts were all ACCEPTED: `'The price rose ５ percent.'` (fullwidth), `'…٥ percent.'` (Arabic-Indic), `'Capacity is ½ of…'` and `'It was Ⅻ MW.'`.
> - **Correction:** refuse any character whose `unicodedata.category(ch)` starts with `N` in the text left after removing quotes. That covers Nd, Nl and No; `\d` alone would still miss ½ and Ⅻ. Add a test per class. Spelled-out numbers ("seventy-five") also pass; that is a question for the packet, not a finding.
> 
> **2. important | `src/judgment/view.py:634-643` (`compose`)**
> - **Mechanism:** `compose()` re-validates the plans against the caller's request but never ties that request's manifest to the records it fills from. It only checks `event_id`. So the mandatory parts, `kind` and `cutoff` all come from caller data, and the receipt then lists the real records beside a plan that was validated against something else.
> - **Evidence:**
>   - Rendering the exposure request from records with `resolved: True`, then composing over the real records (unresolved; `mandatory_parts` returns `('impact_band','belief_card','judgment','receipt')`), produced `['impact_band','belief_card','receipt']`. The judgment was dropped.
>   - Setting `manifest.mandatory_parts.outlook = ['receipt']` composed `['event_timeline','receipt']`.
>   - The packet's self-review item 2 overstates the guarantee.
> - **Correction:** in `compose()`, re-render `render_request(request['question'], records, request['cutoff'])` and refuse unless its `request_digest` equals `request_digest(request)`. Add a test that runs at compose time.
> 
> **3. important | `src/judgment/view.py:582-585` and `:673-684`; `tests/test_judgment_view.py:37` and `:105-108`**
> - **Mechanism:** `compose()` never applies `request['cutoff']`. Every timeline row and record is filled whatever its time, while the receipt and the view state the cutoff.
> - **Evidence:**
>   - The sample view at `CUTOFF = 2026-09-21T13:39:37+08:00` fills the timeline with V135622 (13:56:22), V141257 (14:12:57) and V155556 (15:55:56, "re-online at 1507H").
>   - The fixture price text asserts "the load dropping that followed", which comes from the 13:56 notice.
>   - Paper section 10, Figure 6, F1: "Catalogue queries under the cutoff and mode".
> - **Correction:** filter timestamped rows to at or before the cutoff, or refuse a record stamped after it. Alternatively, name the field as the judgment's cutoff rather than the view's information cutoff. Add a test either way.
> 
> **4. important | `tests/test_judgment_view.py:133` and `:154-159`; packet `view-0.md` self-review item 6**
> - **Mechanism:** the judgment fixture combines records from two different cutoffs, then tests rule 3 against that combination.
>   - `CASE['pairs'][0]['compiles'][1]` is the trip compile (trip/t1, cutoff 05:39:37Z).
>   - `live-run-2026-10-14.md:23` says the live and scripted readings **agree** at the trip cutoff. The disagreement is at the **return** cutoff (`:24-26`, a different artifact, `probe:6e4f9a81…`).
>   - The fixture still attaches `disagreement.resolved: False` to the trip record.
> - **Evidence:**
>   - The case fixture's pairs are `trip: [None, 'challenges']` and `return: ['challenges', 'supports']`.
>   - So `test_the_unresolved_disagreement_makes_the_judgment_mandatory` and `test_the_sample_event_view_shows_the_disagreement_it_keeps` prove rule 3 on a fact the trip-cutoff record does not hold.
>   - The sources also conflict: `live-run-2026-10-14.md:26` says the analyst recorded **retain** at that cutoff, while the explainer says the case pack records no decision.
> - **Correction:** either build the disagreement case from the return pair at its own cutoff, or put it in a separate, clearly labelled synthetic fixture. Correct self-review item 6. VIEW-1 is likely to copy this fixture into the bake, so this matters beyond the tests.
> 
> **5. important | `src/judgment/view.py:795-822` (`LiveView`)**
> - **Mechanism:** `LiveView` is a pass-through, not a Gemini backend "as System One has them". It has no system instruction, no `generateContent` body, no response schema and no envelope decoding.
>   - It calls `transport(request)`. The repository's `GeminiTransport.__call__(self, model, body, *, case=None, timeout_seconds, max_response_bytes)` (`src/adapters/gemini/transport.py:256`) cannot be injected; any attempt maps to `MODEL_UNAVAILABLE`.
>   - Any callable returning a plans dict would be receipted as `backend: 'gemini'`, `execution_mode: 'live_inference'`, with an unchecked `model_version`.
> - **Evidence:** compare `GeminiSystemOneEmulation.body` and `decide` (`src/adapters/systemone/__init__.py:212-236`).
> - **Correction:** follow that pattern: an explicit model, a planner system instruction, a JSON response schema over `CATALOGUE`, envelope decoding, and passing model, body and bounds to the transport. Keep it never called. Or record in the packet that only the gate exists and soften the "live Gemini planner" claims.
> 
> **6. minor | `src/judgment/view.py:403-407`**
> - **Mechanism:** the unrecorded-question insufficient result has no receipt, and its `missing` field ("a recorded question; the site makes no live model call") names no record. It also carries site wording inside a pure module.
> - **Evidence:** the probe output; paper rule 6 ("with the missing record named").
> - **Correction:** name the missing record kind, and consider a minimal receipt (question, cutoff, `view_version`).
> 
> **7. minor | `src/judgment/view.py:746-747` and `:785`**
> - **Mechanism:** the fixture texts state record facts in prose instead of quoting them.
>   - "labels the belief as challenged" should quote `{{judgment.label}}`.
>   - "The event unit is not a portfolio node, as the record states" is not carried by any record passed to `compose`. `sample_impact()` has no `unit` block, so `impact_band.fields.unit` is `None`. The fact exists in DESK-4's baked view (`desk-4.md:78-80`, `portfolio_node: false`).
> - **Correction:** quote the label, and add the `unit` block to the impact fixture or drop the sentence.
> 
> **8. minor | `src/judgment/view.py:128-132`**
> - **Mechanism:** `MANDATORY` follows the brief's list, but paper Table 8 lists more parts. Q9 also requires the decision form. Q10 also requires the portfolio version and effective date (or "Not available") and the formula named.
> - **Correction:** record in the packet how the three kinds map to Table 8 and which parts are deferred.
> 
> ## Verdict
> 
> **Rework.** Four important findings (1, 2, 3, 5) are in the module itself and one (4) is in its tests. The numeral rule and the mandatory-part rule can each be bypassed, demonstrated through the real functions; the view shows records after the cutoff its receipt states; the sample disagreement belongs to a different cutoff; and the "live Gemini backend" is a pass-through that would mislabel any callable's output as live Gemini inference.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `c289a670`, 2026-10-17 21:26, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> **Verdict: rework.** One important finding is new and shown through the real functions: the view's cutoff is not a fixed instant. The same moment written with two different offsets gives two different views, and the judgment record's own stored cutoff refuses the event it judged. Six of the eight round-1 findings are fixed. Finding 3 is only partly fixed, and finding 8 was answered with a written record (no code).
> 
> I reviewed `task/VIEW-0` at `c289a670` against `feat/product-gap-b`. The branch has three commits (`dc7c923f`, `c8fc79c6`, `c289a670`) and changes six files. I did not write this change and edited no file.
> 
> ## Commands run
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_judgment_view` (verify) | `Ran 73 tests` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope VIEW-0 feat/product-gap-b` | **OK**: all changed files inside VIEW-0 allowed paths |
> | `/usr/bin/python3 -m unittest discover -s tests` (full suite, node visible) | `Ran 2349 tests in 242.272s` · **OK (skipped=62)** · exit 0 |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates`. The packet says 112; the base has moved since it was written. |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (548 Markdown files, 3597 local links) |
> | Probes through the real `render_request` / `validate_response` / `compose` | Results quoted under each finding |
> 
> ## Status of the round-1 findings
> 
> - **Fixed:**
>   - **1:** the numeral check now covers every Unicode category N character.
>   - **2:** `compose()` re-renders the request and compares digests.
>   - **4:** the trip and return judgments are separate records, each at its own cutoff.
>   - **5:** `LiveView` now builds the body the System One emulation sends, and that body passes `GeminiTransport.__call__`'s checks. I checked this at `src/adapters/gemini/transport.py:256-280`; the probed body is 7,988 bytes.
>   - **6:** an unrecorded question gets a minimal receipt.
>   - **7:** the fixture texts quote record fields, and the unit statement matches `desk-4.md:78-80` exactly.
> - **Answered in writing:** **8:** the packet now maps the three question kinds to Table 8 and lists what is deferred.
> - **Partly fixed:** **3:** the timeline, the outlook vintages and the judgment are now checked against the cutoff, but see findings A and B.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - All six rules have test classes.
>    - No figure comes from a plan, apart from the CJK gap in finding C.
>    - No live call is made; the gate test's transport list stays empty.
>    - `LiveView` sits behind `VIEW_LIVE=1`.
>    - An AST test shows the module imports nothing from the web layer and opens no file.
>    - The full suite passes.
> 2. **No file outside the allowed paths: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** Two new files, the review record, and one-line state changes in `tasks.json` and `PROGRESS.md`.
> 4. **No new dependency, service, network call or model call: yes.**
> 5. **Mode labels truthful: partly.**
>    - The fixture backend is labelled `synthetic_fixture` everywhere.
>    - Finding B: a receipt states a 21 Sep cutoff over a record built on 16–17 Oct.
>    - Finding D: `compose()` uses whatever backend label the caller passes.
> 6. **Unknowns stayed unknown, no invented facts: yes.** Checked against the source records:
>    - the live-run rows and atomic answers (`live-run-2026-10-14.md:4,17-20`);
>    - the impact unit block (`desk-4.md:78-80`);
>    - the impact digest and label (`impact.md:86-88`);
>    - the case cutoffs (`case.json`).
> 7. **The packet records interpreter, commands, results, unfinished items and next action: yes.**
> 8. **Nothing contradicts the paper: no.** Paper section 10, Figure 6, F1 says "Catalogue queries under the cutoff and mode". Findings A and B break that, and the module docstring (`view.py:42`) and the packet (`view-0.md:36-39`) both claim "the cutoff is applied to every query".
> 
> ## Findings
> 
> **A. important | `src/judgment/view.py:230-245` (`_instant`), used at `:365`, `:370`, `:425`, `:431`**
> - **Failure mechanism:**
>   - A record time without an offset is read in whatever offset the caller wrote the cutoff in.
>   - So the result depends on how the cutoff is spelled, not on the moment it names.
>   - That breaks the module's own rule that the cutoff "must name an instant" (`:214-216`).
> - **Evidence (probes on the sample records with the return judgment):**
>   - Same instant, two spellings: `2026-09-21T23:00:00+08:00` shows the timeline `['V133937','V135622','V141257','V155556']`. `2026-09-21T15:00:00Z` shows `['V133937','V135622','V141257']`.
>   - Same instant, two spellings: `21:00:00+08:00` renders. `13:00:00Z` is refused with "the event advisory is later than the view cutoff".
>   - Each judgment record's own `information_cutoff`, as the live run stores it, refuses its own event. `2026-09-21T05:39:37Z` (trip) and `2026-09-21T07:55:56Z` (return) both fail with that error.
>   - The test's sample `CUTOFF` is itself written with `Z`, so the sample advisory times are read eight hours late. This has no effect only because that cutoff is 17 Oct.
>   - VIEW-1 is likely to pass a judgment's cutoff straight through, and it will hit this.
> - **Correction:**
>   - Read a time without an offset at a fixed offset the record declares. For example, the event record carries `+08:00` from the case, or the bake normalises its times to include the offset.
>   - Or refuse record times that have no offset.
>   - Never use the cutoff's spelling.
>   - Add a test that two spellings of one instant produce the same view, and one that a judgment's own Z-spelled cutoff renders its event.
> 
> **B. important | `src/judgment/view.py:383-399` (impact checks), `:42-48` (docstring); `tests/test_judgment_view.py:741-761`, `:1046-1057`; packet `view-0.md:36-39`**
> - **Failure mechanism:**
>   - The cutoff is checked only on records that carry a time.
>   - The impact record (and an optional scorecard) needs none, so it is shown under any cutoff.
> - **Evidence:**
>   - The rework's own `test_the_return_view_shows_the_disagreement_it_keeps` shows `impact_band` under a receipt with cutoff `2026-09-21T15:55:56+08:00`.
>   - The receipt lists the records `['event','impact','judgment']`.
>   - The impact record was written on 16–17 Oct (`impact.md:3-5`, `:116-117`; its label says "owner 2026-10-16"; the test comment at `:48` says "impact record (16 Oct)").
>   - `CutoffQueries.test_the_timeline_shows_only_the_notices…` does the same at the trip cutoff.
>   - This is the same mechanism as round-1 finding 3, for a record that has no time field.
> - **Correction:** either require a recorded-at time on the impact and scorecard records and refuse one later than the cutoff, or narrow the claim. If narrowing:
>   - the receipt says per record whether it was cut (for example, the impact band is stated as of its digest and date);
>   - the docstring and the packet say the cutoff governs the event, judgment and outlook queries only.
> 
> **C. minor | `src/judgment/view.py:202-210` (`_has_numeral`)**
> - **Failure mechanism:** CJK number characters such as 五 are in Unicode category `Lo`, not `N`, so they pass the numeral check. The docstring and packet say the rule covers "any Unicode numeric character".
> - **Evidence:**
>   - `'The price rose 五 percent.'` and `'The unit lost 八十三 megawatts.'` were both ACCEPTED by `validate_response`.
>   - `unicodedata.numeric('五') == 5.0`, `category == 'Lo'`.
>   - The rework did exactly what round 1 prescribed, so this is a gap in that correction, not a reopened finding. It sits beside the spelled-out-number question ("seventy-five") the packet keeps open.
> - **Correction:** also refuse any character where `unicodedata.numeric(ch, None) is not None`. Add one test.
> 
> **D. minor | `src/judgment/view.py:766-811` (`compose`)**
> - **Failure mechanism:** the receipt takes `backend.name`, `backend.execution_mode` and `model_version` from the caller. Nothing ties them to where the plans came from.
> - **Evidence:** fixture plans composed with `LiveView()` and `'gemini-3.8-flash-001'` give the receipt `gemini / live_inference / gemini-3.8-flash-001`. This is structural, like System One's port, so it is a question about how truthful the label can be, not finding 5 left unresolved.
> - **Correction:** have `compose()` accept the backend's response and check the model version against the backend (for the fixture, `FixtureView.model_version`). Or state in the packet that the caller is trusted for the backend label.
> 
> **E. minor | `tests/test_judgment_view.py:45-50` and packet `view-0.md:80-82`**
> - **Failure mechanism:** the sample view's cutoff (17 Oct) is after the return-cutoff judgment, which carries an unresolved disagreement. The sample view still uses the trip judgment, which has none, so the default view shows no disagreement.
> - **Why it matters:** the outlook question is about the trip, so this choice can be defended. But VIEW-1 is likely to copy this setup into the bake.
> - **Correction:** record in the packet which judgment VIEW-1 should pass for a cutoff after the return judgment, and why.
> 
> ## Verdict
> 
> **Rework.** Finding A is shown through the real functions and contradicts the module's own cutoff contract: the same instant gives different views, and a judgment's own cutoff refuses its event. Finding B leaves the paper's "queries under the cutoff" rule half applied while the module and packet claim it in full. All other acceptance items are met, and round-1 findings 1, 2 and 4–7 are fixed.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Round 3 — 2026-10-17 21:55, Claude Opus 5.5 in-session reviewer (read-only, independent; run by the orchestrator after the runner's two rounds)

Range reviewed: 73a9fc44..f494cfd6 (task/VIEW-0). The reviewer's output, verbatim:

### Reviewer line

Claude Opus 5.5, an in-session subagent acting as the independent reviewer. I worked read-only and did not write this change. I edited no repository file and ran no git write command. My probe scripts are in my scratchpad only.

- Worktree: `.local/wt/VIEW-0`; branch and commit: `task/VIEW-0` at `f494cfd6`; merge base with `origin/main`: `73a9fc44`; range reviewed: `73a9fc44..f494cfd6`.

### Commands run (with results)

1. **Brief.** The brief owns three paths: `src/judgment/view.py`, `tests/test_judgment_view.py` and `docs/work/product-gap-2026-10-17/view-0.md`.
2. **Diff stat.** `git diff --stat 73a9fc44..HEAD` shows 6 files: the 3 owned paths; `docs/work/PROGRESS.md` (one state cell and 3 log rows); `docs/work/tasks.json` (`pending` → `in_progress`); `docs/work/reviews/VIEW-0.md`.
3. **Scope.** `python3 scripts/plan.py scope VIEW-0 origin/main` printed `OK: all changed files inside VIEW-0 allowed paths`.
4. **Verify command.** `/usr/bin/python3 -m unittest tests.test_judgment_view` printed `Ran 84 tests in 0.094s`, **OK**.
5. **Full offline suite.** Python-only, node hidden, empty HOME: `Ran 2360 tests in 193.023s`, **OK (skipped=201)**, exit 0. Matches the packet's count.
6. **Probe scripts** importing the test file's own record builders and calling `render_request` → `FixtureView.decide` → `validate_response` → `compose`:
   - **Finding A, two spellings of one instant.** Identical filled components (canonical bytes) and identical receipt `records` for `2026-09-21T23:00:00+08:00` / `15:00:00Z` (timeline `['V133937','V135622','V141257','V155556']`), for `21:00:00+08:00` / `13:00:00Z` (the same four rows) and for `13:39:37+08:00` / `05:39:37Z` (`['V133937']`).
   - **Finding A, each judgment at its own Z-spelled cutoff.** The trip judgment at `2026-09-21T05:39:37Z` renders its event. The return judgment at `2026-09-21T07:55:56Z` renders all four notices with `['event_timeline','impact_band','belief_card','judgment','receipt']` (the judgment is required by the unresolved disagreement; a plan without it is refused). One second earlier (`05:39:36Z`) is refused: "the event is later than the view cutoff".
   - **Finding A, stamps without an offset.** A stamp without an offset on a timeline row, the advisory, the judgment `information_cutoff`, an outlook `issued_at` or an impact `recorded_at` is refused with ValueError "… must carry an ISO 8601 time with an offset".
   - **Finding B, the impact record.** At the return cutoff the receipt refs are: event `under_cutoff` True; impact False, "no recorded_at; stated as of its content digest"; judgment True. `recorded_at` checks: impact 16 Oct refused; impact 1 Sep accepted ("recorded_at at or before the cutoff"); scorecard after the cutoff refused; impact `recorded_at: None` refused.
   - **Finding C, the numeral rule.** `validate_response` refuses with `NUMERAL_IN_TEXT`: `'The price rose 五 percent.'`, `'The unit lost 八十三 megawatts.'`, `Ⅻ`, `½`, `٣`, `〇`, `兆` in the text; `五` in a reason; `'The 五 records are missing.'` in an insufficient plan's `missing`. `'seventy-five'` is accepted (the spelled-out case the packet keeps open).
   - **Finding D, the backend tie.** `LiveView()` + `'fixture-view-1'` refused; fixture backend + `'gemini-3.8-flash-001'` refused; `LiveView()` + `'gemini-3.8-flashy'` refused; `LiveView()` + `'gemini-3.8-flash-001'` composes. The residual caller trust is documented in `_check_backend`.
   - **Outlook question at the case trip cutoff.** The manifest lists `outlook_vintages` as mandatory and unavailable together; an all-`insufficient` plan set validates and composes under a full receipt.
   - **Decision and history fields.** A labelled synthetic `event.decision` and `event.history` entry stamped `2026-10-01T09:00:00+08:00` both render in `decision_form_and_history` under the trip cutoff `2026-09-21T13:39:37+08:00`; the event ref still says `under_cutoff: True` with the basis "the advisory and timeline rows at or before the cutoff".
7. **Test history.** `git diff c289a670..HEAD -- tests/test_judgment_view.py | grep -E '^-.*(def test|assert)'` finds 2 removed lines, both retargets that follow from `sample_records()` now passing the return judgment (`LIVE_TRIP` → `LIVE_RETURN`; `mandatory_parts('exposure', sample_records())` → `trip_records()`). The three `def test` removals since `dc7c923f` are round-1 renames reviewed in round 2. No test was weakened.
8. **Imports and live calls.** Imports: `datetime`, `math`, `os`, `re`, `unicodedata`, `src.contracts.jsonutil`, `src.judgment`, `src.judgment.systemone`, `src.review.records`; none from the web layer. No `open(`, no HTTP library, no socket; `os` only for `os.environ` in `backend_from_env`. `LiveBackend.test_the_live_backend_is_behind_the_flag_and_no_transport_runs` builds the backend behind `VIEW_LIVE=1` with a transport that raises if called and asserts `calls == []`. `test_the_module_imports_nothing_from_the_web_layer_and_opens_no_file` is the AST guard.

### Findings

**Round-2 findings, re-checked.** **A (important) is fixed:** `_instant` (`src/judgment/view.py:249`) and `_at_or_before` refuse a stamp without an offset instead of reading it at the cutoff's spelling; probes reproduce round 2's exact instants; tests `CutoffQueries.test_two_spellings_of_one_instant_select_the_same_records` and `test_a_judgment_at_its_own_z_spelled_cutoff_renders_its_event`; the tests attach the case's own `+08:00`, read from `case.json`, to the advisory rows. **B (important) is fixed by narrowing the claim, with a per-record receipt status:** `_record_refs` (`:485-532`) gives each reference `under_cutoff` and `basis`; a `recorded_at` on the impact or scorecard record is checked in `_check_records` and refused when after the cutoff; the docstring (`:44-59`) and the packet (`view-0.md:36-59`) say the cutoff governs the event, the outlook and the judgment, and the impact and scorecard records are stated as of their digest; tests `test_the_receipt_says_which_records_the_cutoff_governs`, `test_an_impact_record_recorded_after_the_cutoff_is_refused`, `test_an_impact_record_that_declares_a_recorded_at_is_cut`, `test_a_scorecard_record_recorded_after_the_cutoff_is_refused`. **C (minor) is fixed:** `_has_numeral` (`:215-230`) also refuses any character where `unicodedata.numeric(ch, None) is not None`; test `test_a_cjk_numeral_outside_the_number_categories_is_refused`. **D (minor) is fixed:** `_check_backend` (`:815-838`) ties the model version to the backend; tests `ComposeTiesTheBackendToTheModelVersion` (2). **E (minor) is fixed:** `sample_records()` passes the return-cutoff judgment; the packet (`view-0.md:94-100`) tells VIEW-1 to pass the latest judgment at or before its view cutoff.

**New findings in round 3.**

**F. minor | `src/judgment/view.py:803-807` (`_fill`, `decision_form_and_history`), `:769-773` (`belief_card`'s `accepted`), `:510` (event ref basis), `:44` (docstring "The cutoff governs the event").** Mechanism: the event record's `decision`, `history` and `assumption.accepted.at` are filled with no check against the cutoff while the event ref carries `under_cutoff: True`. Evidence: a labelled synthetic decision and history entry dated 1 Oct renders under the 21 Sep trip cutoff; the ref basis is scoped honestly to "the advisory and timeline rows", so no reference makes a false claim, but the docstring reads wider than the code; the sample case's history is empty and `accepted.at` is before every case cutoff, so nothing leaks on the committed fixtures; the packet (`view-0.md:118-123`) defers the decision form to VIEW-1. Correction (VIEW-1 or a follow-up, not a reason to rework): filter `history` rows by time against the cutoff and refuse an `accepted.at` or `decision` stamped after it, or narrow the docstring to "the event's advisory and timeline" and hand VIEW-1 the rule for a baked decision.

**G. minor | `src/judgment/view.py:187-190` (`MANDATORY`); packet `view-0.md:108-126`.** Mechanism: `outlook_vintages` is mandatory for the outlook and price questions and the only vintage was issued on 16 Oct, so at any case cutoff on 21 Sep the only lawful answer to those two questions is `insufficient`. Evidence: at the trip cutoff the manifest lists `outlook_vintages` as mandatory and as unavailable in the same request; an all-`insufficient` plan set validates and composes; `PLANNER_SYSTEM` tells the model to answer "insufficient" when a needed record is not offered, consistent with rule 6; neither the packet nor a test states this consequence. Correction: one packet sentence for VIEW-1 (before an outlook vintage exists, the outlook and price views are answered "insufficient"); optionally one test pinning that answer at the trip cutoff.

**H. none | receipt fields that follow the cutoff spelling.** For two spellings of one instant, `receipt.cutoff`, `request_digest`, `plan_digest` and the receipt component's `receipt_digest` differ because the request carries the caller's cutoff string. Expected: the receipt records what was asked; the records selected and the filled components are identical. Recorded so that a later reader does not take it for finding A surviving.

**Six rules, acceptance and scope.** (1) The model arranges; the records fill: the plan shape is closed (`{status, parts, not_shown, text}` and `{component, reason}`), the manifest carries no record value, `compose()` re-renders the request and refuses a digest mismatch; tested in `RuleOneModelArrangesRecordsFill` and `ComposeTiesTheRequestToTheRecords`. (2) Every view is under a receipt: `receipt` is mandatory and last; the insufficient result for an unrecorded question carries a minimal receipt; `RuleTwoEveryViewUnderAReceipt`. (3) Mandatory parts cannot be omitted: `MANDATORY` and `mandatory_parts()`, which adds `judgment` on an unresolved or unstable reading; every record's label is carried; `RuleThreeMandatoryParts`. (4) Connecting text carries no numeral: Nd, Nl, No plus any character with a Unicode numeric value; quotes only for paths in the manifest's quotable list; `RuleFourConnectingTextHasNoNumeral`. (5) Stability across the four wordings is recorded: `stability()` with per-wording digests; `RuleFiveStabilityAcrossFourWordings`. (6) "Insufficient" is an answer: an unrecorded question and an insufficient plan, each under a receipt; `RuleSixInsufficientIsAnAnswer`. Other acceptance items: no figure originates in a plan; no live call is made and `LiveView` exists only through `backend_from_env` with `VIEW_LIVE == '1'`; the module imports nothing from the web layer and opens no file; the full suite passes. Scope: all changed files are within the owned paths plus the coordination files.

### Verdict: accept

Each round-2 finding holds under probes I ran myself through the module's own functions: A, two spellings of one instant select the same records and fill the same components, and each live-run judgment's own Z-spelled cutoff renders its event, while a stamp without an offset is refused; B, the receipt states per record whether the cutoff was applied, the docstring and packet match that narrower claim, and a declared `recorded_at` after the cutoff is refused; C, `五` and `八十三` are refused; D and E are also fixed. The six rules each have a test class and hold in code, no live call is made, scope is clean, no test was weakened, and the verify module (84) and the full offline suite (2360, OK, skipped=201) pass. The two new minor findings belong to VIEW-1, which owns the bake: F (the event's decision, history and acceptance time are not cut) and G (the outlook and price questions can only be answered "insufficient" before a vintage exists). The VIEW-1 packet should carry both. Neither breaks a claim the module makes per record, and neither changes the committed sample views.
