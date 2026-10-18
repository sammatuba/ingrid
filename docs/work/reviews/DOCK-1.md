# DOCK-1 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent; commit `902079fe`, 2026-10-18)

| Field | Value |
|---|---|
| Task | DOCK-1: the planner plans arrangement and actions, never text (plan shape view.v4) |
| Branch | `task/DOCK-1`, worktree `.local/wt/DOCK-1` |
| Commit under review | `902079fe` |
| Base | `971885b0` (the merge of `origin/main` into the branch at `e24146ce`). Since then `origin/main` has moved to `8d20c523` (BOOK-1). Those 11 files share no path with DOCK-1 apart from the coordination files `docs/work/tasks.json` and `docs/work/PROGRESS.md`. |
| Reviewer | Claude Opus 5.5 in-session subagent. It is read-only and independent of the author (the executor seat). The owner allowed this reviewer on 2026-10-17 while the Codex seat has no credits. |
| Verdict | **accept**. Acceptance line 5's "the full offline suite passes" is accepted on the condition that the two named hand-backs land: DOCK-5 widens `VIEW_RECEIPT_KEYS`, and DOCK-2 moves the 13 ask-page pins. |

I read AGENTS.md, the `plan.py brief DOCK-1` output, the strategy record (decisions 1, 10 and 13; section 2 and its three named challenges; sections 3 and 4), the agent contract sections 1 and 2, the packet `dock-1.md`, `view-0.md`, `live-plans.md` and the ASK-2 record. I read `git diff 971885b0..HEAD` in full. That covers `src/judgment/view.py`, the new `src/judgment/actions.py`, both test files, `test_grid_catalog.py`, the build docstring, the README, the six regenerated plan sets, `tasks.json` and `PROGRESS.md`. Interpreter: `/usr/bin/python3`. I made no network, model or cloud call.

### Commands and results

| Command | Result |
|---|---|
| `-m unittest tests.test_judgment_view tests.test_judgment_actions` | `Ran 134 tests`, **OK** (119 + 15, the counts the packet gives) |
| `tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce`, exit 0 |
| `-m unittest discover -s tests -p "test_*.py"` (full offline suite) | `Ran 2666 tests in 177.191s`, `FAILED (failures=4, errors=11, skipped=115)`. This is the packet's figure exactly. The 15 reds are listed by name below. |
| `scripts/plan.py scope DOCK-1 origin/main` and `scope DOCK-1 971885b0` | both `OK: all changed files inside DOCK-1 allowed paths` |
| `scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `scripts/repo.py check` | `Checked 601 Markdown files, 3840 local links, 5 skills; bootstrap 1399 words.` **PASS** |
| `git diff --check 971885b0..HEAD` | clean |
| `build_data.contract()` over the fixture bake, in memory | 18 problems, all `views[n] receipt keys are [...]` (3 views × 6 sets) |
| The same, with `build_data.VIEW_RECEIPT_KEYS` widened by `actions` in memory only (no file edited) | `[]`. Hand-back 1 is therefore sufficient as well as necessary. |
| `git diff --quiet 971885b0..HEAD -- .../bake/views/index.json` | unchanged. The keys are `ask, home, models, outlooks, register, syn-bay-unit-2-trip`. The page key set is unchanged. |
| Test-name diff, base against head, for `test_judgment_view.py` and `test_grid_catalog.py` | 0 test methods removed, 31 added (8 + 11 + 8 + 2 + 2, the packet's count). I read each of the 79 deleted lines in its hunk. Every one is replaced by the same assertion over the v4 shape or the version. Section 5 of the packet lists each of these. **No assertion was removed.** |

**The 15 reds, and why each is expected:**

- `setUpClass (test_corpus_index.IndexScriptTests)`: `No module named 'pypdf'`. This is the environment limit.
- 13 tests in `test_grid_ask_page`, all on the DOCK-2 hand-back:
  - `RuleFour…`: `test_a_literal_digit_in_the_text_is_refused`, `test_a_quoted_field_is_filled_from_the_record`, `test_a_reason_with_a_numeral_is_refused` and `test_the_baked_plans_text_and_reasons_carry_no_numeral`
  - `RuleOne…`: `test_no_figure_appears_in_a_plan` and `test_the_plan_carries_only_components_and_reasons`
  - `RuleTwo…`: `test_every_baked_view_carries_the_composers_full_receipt`
  - `RuleThree…`: `test_a_plan_that_drops_a_mandatory_part_is_refused` and `test_every_baked_plan_shows_its_mandatory_parts`
  - `RuleSix…`: `test_an_insufficient_plan_is_an_answer_under_the_receipt`
  - `TheCutoffItems…`: `test_a_decision_history_and_accepted_block_after_the_cutoff_are_cut`
  - `ThePanelInTheHarness…`: `test_every_component_is_drawn_in_the_plans_order_from_its_fields`
  - `TheFixtureBake.test_the_bake_passes_its_own_contract`. This one is also on the DOCK-5 hand-back.
- `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag`: its last assertion (`build_data.contract(tree) == []`, line 347) fails. This is the DOCK-5 hand-back.

Nothing else is red.

### Adversarial probes (my own script, run against the head's validator and composer)

| # | Probe | Outcome |
|---|---|---|
| 1a–1d | A numeral in an action argument: ASCII `record-1`, a full-width `２` in a route, a Roman `Ⅳ` in a list argument, a JSON number | each `PlanRefused NUMERAL_IN_PLAN: plan.actions[].args.<name>` |
| 2a–2d | A component name in another case or form: `Event_Timeline`, `RECEIPT`, a left-out `Impact_band`, a trailing zero-width space | each `COMPONENT_NOT_IN_CATALOGUE` |
| 2e | The action name `Open` | The plan composes. The receipt records `refused: not_in_catalogue` and `run: []`. |
| 3a–3b | An extra argument (`url`), or an argument key in another case (`Route`) | The plan composes and the receipt records `argument_not_in_manifest`. |
| 3c | A component argument (`window`) | `COMPONENT_ARGUMENT_NOT_IN_MANIFEST` |
| 3d | An extra key on the action | `MODEL_INVALID_RESPONSE` |
| 4a–4d | A manifest identifier with a digit: the raw event id, an Arabic-Indic digit, a superscript `²`, a CJK `五` | each `NUMERAL_IN_PLAN` |
| 4e–4f | A handle beyond the manifest (`record-z`), a route traversal (`/outlooks/../admin`) | The receipt records `argument_not_in_manifest`. Nothing runs. |
| 5a–5d | A left-out part with a free-text reason: the catalogue sentence as the key, a `reason` field, `Not_asked`, `not_asked ` | `REASON_NOT_IN_CATALOGUE` (5b: `MODEL_INVALID_RESPONSE`) |
| 5e | A left-out part with an action reason key (`opens_the_page`) | **accepted**. See finding 3. |
| 6a–6b | A sentence without digits as an action argument or as an action name | **validates and composes**. The action is refused and never runs. The sentence is kept verbatim in `receipt.plan` and `receipt.actions.proposed`. See finding 1. |
| 6c–6d | A 500-item list argument; a 40-item list of one handle | `MODEL_INVALID_RESPONSE` (the 64 KiB bound); `argument_not_in_manifest` |
| 7a–7d | `search_web` on an unsigned request; on a signed request; a request rendered as signed in, composed by an unsigned caller; `mark_stale` with no revision supplied | `needs_sign_in`, `run: []`; not refused, `run: []`; `ValueError` (the digest of the re-render differs); `argument_not_in_manifest` |
| 8 | Free-text repeats that propose `open /register` and `open /models` | `stable: true`, with 2 distinct plan digests. See finding 2. |
| 9 | `read_view_set` over the base's real view.v3 `home.json` (`git show 971885b0:…`) | `['view.v3', 'view.v3', 'view.v3']`: replay works |
| 10, 11a–11c | Seven actions; `missing: "Book"`; an insufficient plan with `text`; a view.v3 `planned` plan | `MODEL_INVALID_RESPONSE`; `MISSING_NOT_IN_CATALOGUE: Book`; `MODEL_INVALID_RESPONSE`; `MODEL_INVALID_RESPONSE` |

### Against the six rules of the paper's section 10, as the record refines them

1. **No text in a plan, and no numeral anywhere in it.** The plan has no `text` field and no free reason. Reason keys and missing kinds are catalogue keys. The numeral walk covers every key and string and refuses JSON numbers, with no exemption (probes 1, 4). The view's sentences come from `compose_text()` templates over record fields, and `test_every_sentence_shown_is_a_template_over_the_records` pins this. The one open slot for a string is the action name and the action argument value (finding 1).
2. **Actions are a catalogue, with arguments from the manifest only.** `ACTIONS` matches the contract's table of ten actions, and `TheCatalogueIsTheContractTable` pins its flags. `SITE_ROUTES` is pinned equal to `test_hosting_stage`. The manifest renders identifiers under letter handles, never values.
3. **A write action on an unsigned request is refused and never runs.** `needs_sign_in` is recorded and `run` is always `[]` (probe 7a).
4. **The receipt carries proposed, refused and run.** `RECEIPT_KEYS` gains `actions`, and the fixture bake shows `search_web` refused `needs_sign_in`. Strategy section 2 also names "the confirmations". These are DOCK-3's. Each proposed entry carries its `confirm` flag.
5. **Free text uses one wording with repeats.** `forms` are `f0` to `f2` at one wording, bounded from 1 to 3. One plan gives `measured: false`, `stable: null` and the exact `SINGLE_PLAN` = "single plan, stability not measured" (asserted by `test_one_plan_says_stability_is_not_measured`). The recorded questions keep four wordings (`test_the_recorded_questions_keep_four_wordings`).
6. **The live planner.** It sends one body per form with `wording` and `form` named. `thinkingBudget: 0` stays on Vertex only, unchanged. The schema has no `text` or `reason` property, and its enums are the catalogues.

Two more checks:

- **Sign-in the caller did not state.** `compose` re-renders with the caller's `signed_in`, so a request edited to `signed_in: true` is refused (probe 7c, `test_compose_refuses_a_request_whose_sign_in_state_was_edited`).
- **v3 replay.** `read_view_set` reads the real v3 bake (probe 9). The replay that actually serves pages is still `ask.js` (DOCK-2) and `build_data.contract` (DOCK-5). Nothing at runtime calls `read_view_set` yet.

**Copy.** I checked the new page sentences (`REASONS`, `MISSING`, `TEXT_TEMPLATES`): no semicolon, no "stale", active and short. "Among this view inputs" is the wording carried over from VIEW-0 and ASK-2, not new. The exposure template drops the v3 sentence "Its label says the portfolio is a method demonstration on synthetic volumes". The label still travels in `labels` and `impact_band.fields.label`, and `git grep` finds no pin on the sentence.

### Findings

| # | Severity | Location | Bears on | Failure mechanism and evidence | Correction |
|---|---|---|---|---|---|
| 1 | minor | `src/judgment/view.py:962` (`_plan_action`), `:37-42` (the rule 5 docstring), `src/judgment/actions.py:273`; `dock-1.md:54` | acceptance line 1 ("no plan carries text … by construction") | A validated plan can carry a free sentence without digits: up to 200 characters (`MAX_NAME`) in an action argument value, or 64 (`MAX_KEY`) as an action name. Probes 6a and 6b: `{'route': 'The price will rise sharply after the trip so hedge now'}` and the action `'sell the whole position before noon'` both compose. Each action is refused (`argument_not_in_manifest`, `not_in_catalogue`) and never runs. The composed `text` and `not_shown` stay clean. But the sentence is stored verbatim in `receipt.plan.actions[].args` and `receipt.actions.proposed[]`. The live schema leaves argument values as `{"type": "string"}`, so a live model can reach this slot. The docstring says "the plan shape has no field a sentence or a figure could travel in", and the packet says "every string is an enum or a manifest reference of at most 64 characters". Both are true for figures and overstated for sentences. The acceptance line as its parenthetical defines it (no text field, no numeral, sentences composed from records) is met, so this does not block. | Before DOCK-4's live run, do one of these. (a) In `_plan_action`, refuse at plan level any action name not matching `^[a-z]+(_[a-z]+)*$` and any argument string that is not reference-shaped: a member of `SITE_ROUTES` or `DRAFT_KINDS`, or a handle `^[a-z]+(_[a-z]+)*-[a-z]+$`. Bound list arguments, for example to the manifest's id count. Add a test that a sentence in an argument refuses the plan. Well-shaped wrong references stay recorded refusals. (b) Correct the two claims and add a DOCK-2 hand-back line: render a refused action by its catalogue reason sentence only, never by its raw name or arguments. (a) is preferred. |
| 2 | minor | `src/judgment/view.py:1057` (`_arrangement`) | acceptance line 3 (stability over repeats) | Stability compares action names only. Two free-text repeats that propose `open /register` and `open /models` are recorded `stable: true`, while their plan digests differ (probe 8). For the free-text case, where the agent opens a page for the person, this reads generously. | Put each action's `args` (its references) into `_arrangement`. No fixture bytes change, because every fixture form is identical. Or state in the docstring and the receipt statement that action arguments are outside the stability comparison. |
| 3 | minor | `src/judgment/view.py:217` (`REASONS`), `:945` (`_plan_left_out`) | acceptance line 1 (every sentence shown comes from the records and the catalogue) | One reason catalogue serves both left-out parts and actions. So `opens_the_page` is accepted on a `not_shown` part, and the page then says "Opens the page that holds the records this answer reads." as the reason `impact_band` was left out (probe 5e). The reverse also holds: an action may carry `no_record`. | Split the keys into left-out reasons and action reasons, refuse a key used in the wrong slot, and give each slot its own enum in `_plan_schema()`. |
| 4 | nit (record) | `dock-1.md:68`, `:86`; `tests/test_grid_catalog.py:336` | acceptance line 5 | The packet calls `scripts/grid/build_data.py` and `tests/test_grid_ask_page.py` "files this task may not edit". `plan.py brief DOCK-1` prints both as allowed (ancestor paths). The real reason they were not edited is that DOCK-5 and DOCK-2 own them in this wave, which is a sound reason. Also, the new pin `set(VIEW_RECEIPT_KEYS) \| {"actions"} == set(RECEIPT_KEYS)` assumes DOCK-5 keeps one frozenset. If DOCK-5 widens to "both receipt sets" as two constants (the packet's wording), this pin breaks. | The orchestrator should tell DOCK-5 to widen through the existing constant, or to update this pin with it. Optionally reword the packet to say "owned by DOCK-2 / DOCK-5". |

### Verdict

**Accept.** Each acceptance line is proved by a check I ran.

1. **Line 1.** No plan carries a text field or a numeral. The fixture plans, every validated plan and every receipt plan were walked (`test_no_plan_carries_a_text_field_or_a_numeral_anywhere`), and probes 1 and 4 confirm it. The view's sentences are templates over record fields. All six rule classes stand.
2. **Line 2.** An action outside the catalogue, an argument outside the manifest, and a write on an unsigned request are each refused with a recorded reason key. The receipt carries `proposed`, `refused` and `run` (probes 2e, 3, 4e, 7).
3. **Line 3.** A free question uses one wording with up to three repeats. The receipt gives stability over repeats, or the exact sentence "single plan, stability not measured". The recorded questions keep four wordings.
4. **Line 4.** `build.py --check` passes on 20 files, and the six keys and `index.json` are unchanged.
5. **Line 5.** No assertion was removed: 0 test methods dropped, and every deleted line is a moved pin listed in section 5. No live call occurs. **The full suite passes on condition of the two named hand-backs.** DOCK-5 widens `VIEW_RECEIPT_KEYS` by `actions`, which I proved sufficient in memory. DOCK-2 moves the 13 `test_grid_ask_page` pins. Every red in the run is one of these two or the `pypdf` environment limit.

No major finding stands. Findings 1 to 3 are minor and do not block. The orchestrator should schedule finding 1, option (a), before DOCK-4 records a live plan set, because that run is the first time a model can fill the open string slot. Findings 2 and 3 can go with it. Finding 4 goes into the DOCK-5 brief. The merge forward to `origin/main` `8d20c523` touches no DOCK-1 path except `tasks.json` and `PROGRESS.md`.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent; commit `a422de03`, 2026-10-18)

| Field | Value |
|---|---|
| Commit under review | `a422de03`. It holds the rework `22b9ac77`, the merge `d370e0e8` of `origin/main` `8d20c523` (BOOK-1), and the record commit `a422de03`. |
| Base | `8d20c523` (`origin/main`, which is also the merge base) |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, independent of the author |
| Verdict | **accept**. Acceptance line 5's "the full offline suite passes" is still conditional on the two hand-backs: DOCK-5 widens `VIEW_RECEIPT_KEYS` by `actions`, and DOCK-2 moves the 13 ask-page pins. |

I read `git diff 902079fe..a422de03` in full:

- the DOCK-1 changes: `src/judgment/view.py`, `src/judgment/actions.py`, both test files, the six regenerated plan sets and the packet's rework section
- the BOOK-1 files the merge brought in: `src/book/`, `scripts/book/`, `tests/test_book_*`, `tests/fixtures/book/`, the BOOK-1 records and the coordination rows. None of these is a DOCK-1 path.

### Commands and results

| Command | Result |
|---|---|
| `-m unittest tests.test_judgment_view` | `Ran 124 tests`, **OK** |
| `-m unittest tests.test_judgment_actions` | `Ran 18 tests`, **OK** |
| `tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce`, exit 0 |
| `-m unittest discover -s tests -p "test_*.py"` (full offline suite, written to a log with a unique name) | `Ran 2710 tests in 269.388s`, `FAILED (failures=4, errors=11, skipped=115)`. These are the same 15 reds as round 1, name for name, and nothing else (see the note below). |
| `scripts/plan.py scope DOCK-1 origin/main` | `OK: all changed files inside DOCK-1 allowed paths` |
| `scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `scripts/repo.py check` | `Checked 604 Markdown files, 3845 local links, 5 skills; bootstrap 1399 words.` **PASS** |
| `git diff --check origin/main..HEAD` and `git diff --check 902079fe..HEAD` | both clean |
| `build_data.contract()` over the regenerated bake | 18 problems, every one a receipt key set. With `VIEW_RECEIPT_KEYS` widened by `actions` in memory only, the result is `[]`. Hand-back 1 is still sufficient. |
| `bake/views/index.json` | unchanged. The six keys are unchanged. |
| Test-name diff against `971885b0` and against `902079fe` | 0 test methods removed. 5 were added to `test_judgment_view.py` and 3 to `test_judgment_actions.py`. |

The 15 reds are:

- the `pypdf` setUpClass error in `test_corpus_index` (the environment limit)
- the 13 `test_grid_ask_page` tests that round 1 lists (DOCK-2), including `TheFixtureBake.test_the_bake_passes_its_own_contract`
- `test_grid_catalog.FixtureBake.test_the_fixture_bake_carries_the_plan_sets_and_the_event_s_flag` (DOCK-5)

**Note on the suite log.** My first round-2 suite log was overwritten partway by another session's run in the `.local/wt/OUT-2` worktree. The log showed `Ran 2689 tests … (errors=1)` with OUT-2 paths. I threw it away and reran into a uniquely named file, which contains no OUT-2 path. Every figure above comes from that clean run.

**Removed or moved assertions.** In round 1's own test `test_an_argument_outside_the_manifest_is_refused_with_its_reason`, the subtest `{'route': '/nowhere'}` became `{'route': 'record-a'}`. `/nowhere` is now refused at plan level and is asserted in `test_a_value_that_is_not_reference_shaped_refuses_the_plan`. The schema enum pin moved from `REASONS` to `LEFT_OUT_REASONS`, and a new pin covers `ACTION_REASONS`. Neither was an assertion of the base, and nothing was dropped.

### Round 1 findings, checked again against code, tests and probes

| Round 1 finding | What changed | My check | Status |
|---|---|---|---|
| 1. A sentence in an action slot | `_plan_action` (`view.py`) refuses the plan when a name or argument name is not a short snake-case key (`actions.is_snake_key`: at most 3 words and 32 characters, ASCII lower case). It also refuses any argument value that is not reference-shaped (`actions.is_reference`: a route the manifest lists, a draft kind, or a `<known prefix>-<1 to 4 lower-case ASCII letters>` handle). It bounds an action to 4 arguments and a list to 16 items. The live schema now enumerates each argument value from the manifest (`ARG_IDS`); an argument with no reference on offer is left out, and lists carry `maxItems`. The rule 5 docstring and packet §3 now state what is enforced. | Both of my probe sentences are refused at plan level: 6a `ARGUMENT_NOT_A_REFERENCE: route` and 6b `ACTION_NAME_NOT_A_KEY`. So are the new test `test_a_sentence_in_an_action_slot_refuses_the_plan` and its snake-case variant. In the schema built from a rendered request, all 9 argument properties have an enum and none is a free string (probe S1). | **closed** (one nit remains, see below) |
| 2. Stability compares action names only | `_arrangement` compares `{action, args}` | Probe 8 (`open /register` against `open /models`) now gives `stable: false`, and identical repeats stay `stable: true` (S4). The test `test_repeats_that_open_different_pages_are_recorded_unstable` passes. The bake's bytes changed only in `arrangements` (now carrying the action arguments) and in the request digest. The plans did not change, and `--check` reproduces them. | **closed** |
| 3. One reason list for two slots | `LEFT_OUT_REASONS` and `ACTION_REASONS` do not overlap. The request's `reason_keys` is `{not_shown, actions}`, checked by `_request_shape`, and each slot has its own enum in the schema. `REASONS` remains the sentence table. | Probe 5e (`opens_the_page` on a left-out part) is now `REASON_NOT_IN_CATALOGUE: opens_the_page`. Probe N12 (`needs_sign_in` on an action) and N14 (the refusal key `not_in_catalogue` on an action) are refused. N13 (`needs_sign_in` on a left-out part) is accepted, as designed. S2 and S3 show the per-slot enums and request keys. | **closed** |
| 4. Record nit | Packet §1, §4 and §6 now name the two files as owned by DOCK-5 and DOCK-2, and state the pin's assumption about how DOCK-5 widens the constant. | Read in the diff. | **closed** |

### Probes: round 1's 30, run again, and 17 new ones (plus four schema and stability checks)

Round 1's probes that still refuse, or are still recorded refusals, keep the same outcomes: 1a–1e, 2a–2d, 3a, 3c, 3d, 4a–4e, 5a–5d, 7a–7d, 9, 10 and 11a–11c. Some outcomes changed, all toward refusing the whole plan:

- 2e (`Open`) is now `ACTION_NAME_NOT_A_KEY`.
- 3b (`Route`) is now `ARGUMENT_NOT_A_REFERENCE`.
- 4f (route traversal) is now `ARGUMENT_NOT_A_REFERENCE: route`.
- 5e is now `REASON_NOT_IN_CATALOGUE`.
- 6a and 6b are now refused at plan level.
- 6c and 6d are now `MODEL_INVALID_RESPONSE` (the list bound).
- 8 is now unstable.

| # | New probe | Outcome |
|---|---|---|
| N1 | Action name `sell_now_please` (a three-word snake key) | composes; recorded `not_in_catalogue`; never runs |
| N2 | Argument name `prices_will_spike` with value `record-a` | composes; recorded `argument_not_in_manifest`; the key is kept verbatim in `receipt.actions.proposed[].args` |
| N3 | Handle `record-dump` (a four-letter word) | recorded `argument_not_in_manifest` |
| N4, N5 | A route in a record slot; the draft kind `case` as a route | recorded `argument_not_in_manifest` |
| N6 | Empty list argument | `MODEL_INVALID_RESPONSE` |
| N7, N15 | A boolean or an object as an argument value | `ARGUMENT_NOT_A_REFERENCE: route` |
| N8, N9, N11 | Handle letters `á` or full-width `ａ`; a handle padded with a leading space | `ARGUMENT_NOT_A_REFERENCE: record_id` |
| N10 | The raw question text as `question_id` | `ARGUMENT_NOT_A_REFERENCE: question_id` |
| N12, N14 | `needs_sign_in` or `not_in_catalogue` as an action reason | `REASON_NOT_IN_CATALOGUE` |
| N13 | `needs_sign_in` on a left-out part | composes (a left-out key) |
| N16 | Five arguments on one action | `MODEL_INVALID_RESPONSE` |
| N17 | Sixteen copies of one handle | recorded `argument_not_in_manifest` (duplicates) |
| S1–S4 | The schema's argument enums; the per-slot reason enums; the request's `reason_keys`; stability of identical repeats | all argument properties have an enum; per-slot enums as above; `{not_shown, actions}`; `stable: true` |

### Findings, round 2

| # | Severity | Location | Bears on | Mechanism and evidence | Correction |
|---|---|---|---|---|---|
| R2-1 | nit (no rework needed) | `src/judgment/actions.py` (`is_snake_key`, `is_reference`); `src/judgment/actions.py:273` (`action_record` copies `args`) | acceptance line 1 | The shape rule still lets a short fragment through, and a refused action keeps it verbatim in the receipt. Examples: an action name or argument name of up to three snake-case words and 32 characters (N1 `sell_now_please`, N2 `prices_will_spike`), or a four-letter word in a handle (N3 `record-dump`). The docstring now states this bound honestly ("no string slot longer than a short key"). The live schema closes the slot for a model: action names and argument names are enums with `additionalProperties: false`, and argument values are manifest enums. So only a hand-built or non-schema backend can produce such a fragment, it never runs, and it never reaches `view.text` or `not_shown`. | For DOCK-2: render a refused action by its catalogue reason sentence (`REASONS[reason_key]`) and its catalogue name only. Show the raw `args` and an unknown name only inside the receipt's detail. |

### Verdict, round 2

**Accept** for head `a422de03`. All three minor findings and the record nit of round 1 are closed. The probes and the new tests prove each fix, and no major finding stands. Acceptance lines 1 to 4 are proved as in round 1, and the tightened validator makes line 1 stronger.

Acceptance line 5 holds in two parts:

- **Proved:** no assertion was removed, and no live call is made.
- **Conditional:** "the full offline suite passes" holds once the two named hand-backs land, DOCK-5 widening `VIEW_RECEIPT_KEYS` by `actions` (shown sufficient in memory) and DOCK-2 moving the 13 `test_grid_ask_page` pins. Every red in the 2710-test run is one of those two or the `pypdf` environment limit.

Finding R2-1 is a nit for the DOCK-2 brief.
