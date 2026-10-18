
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `6a96bd21`, 2026-10-17 22:51, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # REG-2 review: rework
> 
> **Verdict: rework.** The register row, the event lookup and the missing dependency are all correct, and I ran every acceptance check myself. One important finding remains: once this merges, three committed product records will say "there is no PEDC register row", and the packet doesn't pass that on as a follow-up. The fix is one added paragraph in the packet's own file.
> 
> I edited no files. The base is `feat/product-gap-f` at `e08329fc`, which is also the merge-base. The branch has two commits, `94279082` and `6a96bd21`. `register.json` changed from blob `49a57ae9` to `4b7e94fc`.
> 
> ## Commands run in this environment
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_outlook_register` (the verify command) | `Ran 60 tests` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope REG-2 feat/product-gap-f` | exit 0, `OK: all changed files inside REG-2 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (569 Markdown files, 3689 links) |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2433 tests in 213.972s` · **OK (skipped=62)**, the same as the packet |
> | The real-archive test classes, run verbosely | 20 tests, OK. `RenderedPageWithTheRealArchive` ran through the node harness and passed; it was not skipped. |
> | `register.audit` on the committed file | records 43, threshold 23, composer 14, official 11, analytical 16, inferred 5, exploratory 11, hypothesis 0, unowned 40, unknown_interval 42, unchecked 43; all five problem lists empty. This matches register.md. |
> 
> My first suite attempt used `-t .` and failed on import setup before running any test. The run above uses the packet's own command, with no other change.
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **The lookup resolves:** the real builder returns `registered: true` with the row's id. The rendered real page now reads "…is register row availability:pedc-u2-2026-09-21: analytical, deployed, orchestrator seat…".
>    - **No dependency is invented:** the chain sentence still starts "No issued price outlook rests on…". `rests_on_this_assumption` is false at the document level and on each outlook, and neither vintage's `assumption_ids` contains the new id.
>    - **The validator passes:** `load_register` and `audit` both run clean.
> 2. **Only allowed paths changed: yes.** The scope check printed OK.
> 3. **No frozen contract, acceptance text or test weakened: yes.** The count pins moved from 42 to 43, and the dated-row assertion was added, not removed. The fixture pin at `tests/test_grid_event.py:853` still correctly says "not a register row", because it reads the synthetic fixture register, which has no such row.
> 4. **No new dependency, call or cloud effect: yes.**
> 5. **Mode labels truthful: yes.** Synthetic fixtures and the real archive are kept separate.
> 6. **No invented facts: yes.** I checked every quote against its source: `brief.md` lines 38, 39 and 42, `outlook-revision.md:15`, and both quotes in `evidence-manifest.json`.
> 7. **Packet records interpreter, commands, results and next action: partly.** The commands and results are there, but §9 is missing the follow-up below.
> 8. **Nothing contradicts the committed records: no.** See finding 1.
> 
> ## Findings
> 
> **1. Important**
> - **Where:** `docs/work/product-gap-2026-10-17/reg-2.md:242`
> - **What goes wrong:** after merge, the product's own records state the opposite of what the baked view shows, and the packet doesn't hand that over to the orchestrator.
> - **Evidence:**
>   - `docs/product/integration-contract.json` says the register holds no PEDC row in three answers:
>     - Q2 at line 88: "The register holds no row for the PEDC availability assumption."
>     - Q3 at line 136: the notice touches an availability belief, and the register holds no row for the unit.
>     - Q9 at line 427: "The event page looks up the PEDC assumption and finds no register row."
>   - The generated `docs/product/integration-contract.md` carries the same answers.
>   - `docs/product/capability-map.md:28` lists "The PEDC assumption is not a register row" as unresolved.
>   - `tests/test_integration_contract.py:76` pins that unresolved item.
>   - All of these are outside REG-2's allowed paths, and the suite stays green because the test pins those strings, not the register. §5 reports "none went red" and leaves out these now-false records.
> - **Fix:** add one bullet to §9 naming those three answers, the generated `.md`, the capability-map row and the test pin, with the next step: "the orchestrator refreshes CAP-1's records after merge". No file outside the allowed paths should be edited.
> 
> **2. Minor (observation)**
> - **Where:** `docs/work/outlook-archive/register.json:43`
> - **What goes wrong:** the brief's wording "trading days 1 to 29" doesn't match the row's "2026-02-05 to 2026-09-29".
> - **Evidence:** the row's range is read from `brief.md:42`. No event page or source file shows a "1 to 29" range.
> - **Fix:** none needed; reading the range from a cited line is correct. One line in the packet saying the brief's phrase could not be traced to a source would close it.
> 
> **3. Minor (observation)**
> - **Where:** `register.json` `valid_to`
> - **What goes wrong:** the row ends on the day itself, 2026-09-21, while the case brief gives the day as the half-open range to 2026-09-22.
> - **Evidence:** the register's date fields have no way to mark a range as half-open. The packet already explains this in §2 and raises it for review in §8.
> - **Fix:** none.
> 
> The state `deployed`, rather than `contradicted`, is not a finding. The brief fixes `deployed`, and `src/outlook/register.py:19-23` defines it as in force in a built artefact, not verified. The falsifier carries the trip notice.
> 
> Once the §9 addition is committed, this should be an accept.


Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `5c2cb9e4`, 2026-10-17 23:11, overnight round 2)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> The suite is still running. I'll write the verdict once it reports.
> 
> # REG-2 review: accept
> 
> **Verdict: accept.** All three acceptance items pass on checks I ran myself. The one important finding from round 1 (the after-merge handover) is now in the packet with accurate line references, and nothing blocking or important is left.
> 
> I reviewed `5c2cb9e4` against `feat/product-gap-f`, which is `e08329fc` and also the merge-base. There are five commits on the branch, and I edited no files.
> 
> ## Commands run here
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_outlook_register` (the verify command) | `Ran 60 tests` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope REG-2 feat/product-gap-f` | `OK: all changed files inside REG-2 allowed paths` |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 117 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** (570 Markdown files, 3691 links) |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2433 tests in 240.122s` · **OK (skipped=62)**, exit 0. The browser classes skip here by design. |
> | The six real-data classes, run verbosely (`RenderedPageWithTheRealArchive`, `RealArchive`, `LookupOnTheCommittedRegister`, `TheRealArchive`, `TheRealRegister`, `TheAvailabilityRow`) | 24 tests, all **ok**, none skipped |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **The lookup resolves.** `assumption_lookup` (`scripts/grid/build_data.py:698`) now finds exactly one matching row on the committed register. The real rendered page reads "…is register row availability:pedc-u2-2026-09-21: analytical, deployed, orchestrator seat…" (`tests/test_grid_event.py:1205`). That is the `event.js:556` branch, which replaces the "not a register row" sentence at `:557`.
>    - **No dependency is invented.** `rests_on_this_assumption` is false for the event and for each outlook. The new id is absent from both outlooks' rows (`test_grid_outlook.py:227-231`) and from both vintages' `assumption_ids` (`test_grid_outlooks_page.py:548-550`). The chain sentence still says "No issued price outlook rests on…" (`event.js:593`).
>    - **The validator passes.** `load_register` and `audit` run clean: 43 records, and the missing, unknown, duplicates, dangling and unlabelled lists are all empty.
> 2. **Only allowed paths changed: yes.** The scope check printed OK. Every changed test file is in the printed allowed list.
> 3. **No frozen contract or acceptance text changed, and no test weakened: yes.** The count pins moved from 42 to 43, and assertions were added: the dated-row check and the per-outlook absence checks. The removed "not registered" assertions on the committed register are still covered on the synthetic fixture (`test_grid_outlook.py:518`, `test_grid_event.py:853`).
> 4. **No new dependency, call or cloud effect: yes.** The change is data, docs and tests only, with no runtime code.
> 5. **Mode labels truthful: yes.** The real archive and the synthetic fixtures stay separate, and the fixture pins are unchanged.
> 6. **No invented facts: yes.** I checked each quote against its source. `brief.md:38`, `:39` and `:42` match. `outlook-revision.md:15` reads "83.7 MW for 2026-09-21". The single-line `evidence-manifest.json` contains both the publisher string and "PEDC U2 Tripped at 1334H (Unplanned Outage)". The brief's phrase "trading days 1 to 29" does not appear in any source, so the packet's §2 note on it is correct.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.** These are §7, §9, the rework table and the post-commit blocks. Every §9 stale-record line I re-read matches: integration-contract.json lines 88, 136 and 427, the generated .md, `capability-map.md:28` and `test_integration_contract.py:76`.
> 8. **Nothing contradicts the committed records: yes, for this change.** The records that go stale after merge are named in §9 as the orchestrator's CAP-1 refresh. They are outside this task's paths and were correctly not edited. The register's own definition of `deployed` supports the chosen state, and the falsifier carries the trip notice.
> 
> ## Findings
> 
> | Severity | Location | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/outlook-archive/register.json` (the new row's `valid_to`) | The row ends on the day itself, while the case brief states the period as half-open, 2026-09-21 to 2026-09-22. | `brief.md:40`. The register's date fields cannot mark a range as half-open, and packet §2 and §8 explain this. | None needed; the reading is recorded. |
> | minor | the new row's `affected_code` | The row does not list `src/demo/pedc.py`, which seeds the case's own copy of 83.7 MW. | Packet §8, probe 3. The runtime seed does not read the register. | None needed now. The orchestrator can decide whether to add it at the CAP-1 refresh. |
> | minor (not caused by this change) | full-suite output | A line, `cvis-2026-06-25-0910: none (not transmittable)`, prints after `OK`. | The suite tail. No file this branch changed prints it. The runner gates on exit status since `c155006`, so it does not cause a false red. | None for REG-2. |
> 
> ## Verdict
> 
> **accept**: every acceptance item is shown by a check I ran, scope, plan and repo checks all passed, the full suite is OK with only the expected skips, and the round-1 important finding is fixed accurately.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
