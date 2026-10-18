
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `0cf7ade7`, 2026-10-17 12:57, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> **Verdict: rework.** One acceptance claim is broader than what the code does: an archive holding two targets, each with one outlook, comes out in a different order than DESK-1 produced. The branch's own new test asserts that new order. Everything else checks out, and the fix is small. I edited no files, and the worktree is still clean.
> 
> **Checks I ran in this sandbox**
> - **Verify command:** 194 tests, OK (3 skipped).
> - **`plan.py scope DESK-2 feat/product-refine`:** `OK: all changed files inside DESK-2 allowed paths`.
> - **Full offline suite (`unittest discover -s tests`):** 1949 tests in 172.0 s, OK (47 skipped). This matches the packet's count.
> - **`build_all.py` on a fresh temporary `--data` directory:** the write and the `--check` both exit 0 with `violations []`, and `outlook/pedc-u2-2026-09-21.json` is in the bake.
> - **Is the frozen DESK-1 fixture real?** I loaded the base builder from `feat/product-refine` and baked the fixture archive with it. Its bytes equal `tests/fixtures/grid/desk-1-view.json` and the new builder's bytes.
> - **Real archive:** old and new builders give the same view once the three new fields are removed.
> - **Regeneration record:** the cutoff, input, values and v2 id in the real-archive test match lines 26–27 and 62–67 of the record.
> 
> **Checklist**
> 1. **Every acceptance item met by a check that was run: partly.** All five items are shown except the "bakes byte-for-byte as DESK-1" part of item 2. That holds only for a one-outlook archive (finding 1).
> 2. **Scope: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract, acceptance text or test weakened: yes.** The test diff only adds. `tests/test_cache_headers.py` and the copy path for `events/<id>.json` are untouched.
> 4. **No new dependency, network call, model call or cloud effect: yes.** New tests write only to temporary archives.
> 5. **Mode labels truthful: yes.** The fixture records are built by `build_outlook` with `synthetic=True`.
> 6. **Nothing invented: yes.** Every diff entry is read from the two records. The values digest comes from the record; the values file is never opened.
> 7. **Packet complete: yes.** `desk-2.md` lists the commands, results, the contestable reading (§8) and the next action.
> 8. **No contradiction of strategy or invariants: yes.** "Current" is a word, not a badge. Every time shows its date and UTC. The card keeps one caption line. On a single-vintage target, the executor followed the acceptance's byte-for-byte rule instead of the Outputs' "current true", and recorded that choice. I agree with that reading.
> 
> **Findings**
> 
> 1. **Important | `scripts/grid/build_data.py:768`**
>    - **Mechanism:** groups are emitted in `sorted(groups)` order, sorted by table, column, version and horizon label. DESK-1 emitted outlooks in `archive.issue_ids()` order, which is sorted by id. So an archive with two targets, each with one outlook, comes out reordered. That falsifies the docstring at `:121-122` ("an archive that was never revised bakes as it always did") and the Output's "a single-vintage archive bakes exactly as DESK-1 did".
>    - **Evidence:** I baked a probe archive (`fixture-vintage-z-first`, month; `fixture-vintage-a-second`, week) with both builders. Base order: `[a-second, z-first]`. Branch order: `[z-first, a-second]`. Bytes equal: False. The new test `test_a_second_target_is_its_own_single_vintage_group` (`tests/test_grid_outlook.py:557`) asserts the branch order. The byte-for-byte proof only covers a one-outlook archive.
>    - **Correction:**
>      - Order the groups by their smallest `outlook_id` (`sorted(groups, key=lambda k: min(o["outlook_id"] for o in groups[k]))`). Inside each group, keep the `issued_at` order.
>      - Update that new test to expect DESK-1's order.
>      - Add a byte-equality check for a multi-target, all-single-vintage archive.
> 
> 2. **Minor | `scripts/grid/build_data.py:62-64` and `:373-374`**
>    - **Mechanism:** `issued_at` is compared as text in both the builder and the contract check. Records are stored in `Z` form, but microseconds appear only when they are non-zero. `…:00.5Z` sorts before `…:00Z` even though it is later.
>    - **Evidence:** `src/outlook/records.py:192-193` normalises with `isoformat()`. A `.` (0x2E) sorts before `Z` (0x5A).
>    - **Correction:** sort and compare parsed instants (`records._instant` or `datetime.fromisoformat`), not strings.
> 
> **Note for the record:** the sentence adds a `values cb2144ac… to 903437f3…` clause that the brief's example does not have. It follows the owner's note in the brief, so I accept it as correct.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `63617d16`, 2026-10-17 13:15, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # DESK-2 independent review (round 2)
> 
> **Reviewer:** Claude Opus 5.5 (claude-opus-5-5), in-session, read-only. I am not the author. The owner allows this fallback while Codex is unavailable.
> **Reviewed:** `task/DESK-2` at `63617d16`, compared with `feat/product-refine` (7 commits, 12 files). I edited no files. My probes ran inline or wrote to temporary directories only.
> 
> **Verdict: accept.** All five acceptance items are shown by checks I ran myself, both findings from round 1 are fixed and tested, and nothing blocking or important is left.
> 
> ## Commands I ran in this sandbox
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_outlook tests.test_grid_event` | `Ran 196 tests in 9.035s`, **OK (skipped=3)** |
> | `/usr/bin/python3 scripts/plan.py scope DESK-2 feat/product-refine` | `OK: all changed files inside DESK-2 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 97 tasks, 8 gates` |
> | Full suite: `/usr/bin/python3 -m unittest discover -s tests` | `Ran 1951 tests in 214.774s`, **OK (skipped=47)**, exit 0. The browser-guarded classes skip by design. |
> | `build_all.py` write, then `--check`, into a fresh temporary `--data` directory, with the fixture archive (`.local/desk2-buildall.py`) | write exit 0, check exit 0, all four checks 0, `violations []` |
> | The same `build_all.py` run with the committed register and the real two-vintage archive (`.local/outlook-archive`: `outlook-2026-11-system`, `-v2`) | write exit 0, check exit 0, `violations []`. The sha256 values of the archive and register files were the same before and after: `True` |
> | Base builder taken from `feat/product-refine`, loaded from a temp directory with the repo root, baked over the same archives | the two-target bake equals `desk-1-view-two-targets.json`: **True**. The one-vintage bake equals `desk-1-view.json`: **True**. The branch builder's two-target bake equals the frozen file: **True** |
> | `vintageSentence` extracted from `src/grid/event.js` and run under node with every kind of change (cutoff unchanged, input added and removed, model, assumptions added and removed, horizon edge) | Every word of the output comes from the change fields, the id, `issued_at` or `supersedes`, and every time carries "UTC" |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by an observable check that was run: yes.**
>    - **Sentence composed from the records:** the rendered pin in `tests/test_grid_event.py` covers the real archive's sentence, and my node probe covered the other branches. Every digest comes from a record, and every time goes through `utcWhen`, so it shows its date and UTC.
>    - **Ordering, current flag and the DESK-1 shape:** the order is by parsed `issued_at`, and exactly one vintage is `current`. A single-vintage target bakes the DESK-1 bytes: the one-vintage and two-target frozen fixtures both match the base builder's own output, which I reproduced myself.
>    - **No new route or file changes:** `events/<id>.json` and `tests/test_cache_headers.py` are not in the diff, and no route was added. The archive and register were not written, and no outlook was issued.
>    - **Copy rules:** "current" is a word in the head line, not a badge. The change sentence sits in a `po-change` div and does not add a caption line.
>    - **Existing assertions, suite and bake check:** all existing assertions are kept, the suite passes, and the `build_all --check` passed on fresh temporary bakes.
> 2. **Scope: yes.** `plan.py scope` printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: yes.** The test diff only adds lines. The one ordering expectation that changed was added earlier on this branch and was corrected because of finding 1 in round 1.
> 4. **No new dependency, network call, model call or cloud effect: yes.** The only new import is `datetime`, and the tests write only to scratch archives.
> 5. **Mode labels truthful: yes.** The fixture records are built by `build_outlook(..., synthetic=True)`, and the real records declare `synthetic: false`.
> 6. **Nothing invented: yes.** The changes are computed from the two records only, and the values digest comes from `values_ref.sha256`; the values file is never opened. The real-archive diff matches lines 27 and 65–67 of `refresh-regeneration-2026-10-17.md`.
> 7. **Packet complete: yes.** Section 10 of `desk-2.md` records the interpreter, the commands, the results, the self-review and the exact next action.
> 8. **No contradiction of the strategy or the invariants: yes.** The values clause follows the owner's note. A single-vintage target carries no `current` key; the acceptance requires those bytes to be unchanged, which overrides the Outputs' "current true", and that choice is recorded in section 8 of the packet.
> 
> ## Round 1 findings
> 
> - **Important, target order:** fixed at `scripts/grid/build_data.py:281`. Targets are now emitted by their smallest `outlook_id`, and the bytes are proved against the base builder's output.
> - **Minor, instants compared as text:** fixed by `issued_instant()` and `vintage_order()`, and by the contract's ordering check. `test_issue_instants_are_compared_as_times_not_text` pins it.
> 
> ## Findings
> 
> 1. **minor** | `tests/test_grid_outlook.py:869` (covering `src/grid/event.js:249`)
>    - **Failure mechanism:** the sentence's model, assumption, horizon, input-added, input-removed and "cutoff unchanged" branches are checked only by substring matches on the page source. A wording or field mix-up in those branches would still pass.
>    - **Evidence:** the only rendered pin is the real archive's sentence. My node probe shows those branches are correct today.
>    - **Correction:** in a later task, render the two-vintage fixture where every field changes, and pin the sentence.
>    - **Disposition:** does not block accept.
> 2. **minor** | `tests/test_grid_event.py` (the rendered pin's `Sep(?:t)?`)
>    - **Failure mechanism:** the page prints "25 Sept 2026" (the browser's date formatter), but the brief's example says "25 Sep 2026". The test's regex accepts both forms.
>    - **Evidence:** the date line quoted in `desk-2.md` reads "25 Sept 2026". The same allowance was recorded for DESK-1.
>    - **Correction:** none needed for DESK-2.
>    - **Disposition:** recorded only.
> 
> **Note on mixed archives:** if one target has several vintages and another has one, the single-vintage entry's bytes are unchanged, but its place in the file can move. The revised target's vintages are kept next to each other, so this cannot be avoided, and the acceptance asks for the target's bytes, not the file order.
> 
> **Verdict: accept.** The orchestrator still has to write this record into `docs/work/reviews/DESK-2.md` and set `done`. I did not touch either.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
