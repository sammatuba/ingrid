
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `8102b700`, 2026-10-17 14:03, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> Still waiting on the full suite; the monitor will tell me when the output lands.
> 
> # ARCH-4 review: accept
> 
> I reviewed commits `158b03fd` and `8102b700` against `feat/product-refine`. This is an independent review: I did not write the change. I edited no files and wrote nothing to `.local/outlook-archive`; my probes used temporary directories that were cleaned up.
> 
> ## Commands I ran
> 
> | Command | Result |
> |---|---|
> | Verify: `/usr/bin/python3 -m unittest tests.test_outlook_attribution tests.test_outlook_records tests.test_outlook_dependency tests.test_grid_outlook` | `Ran 225 tests` · **OK** |
> | `/usr/bin/python3 scripts/plan.py scope ARCH-4 feat/product-refine` | `OK: all changed files inside ARCH-4 allowed paths` |
> | `/usr/bin/python3 -m unittest discover -s tests` (full suite) | `Ran 2004 tests in 186.338s` · **OK (skipped=47)**, the same count the packet records |
> | `/usr/bin/python3 scripts/plan.py check` | `OK: 98 tasks, 8 gates` |
> | `/usr/bin/python3 scripts/repo.py check` | PASS (506 Markdown files, 3409 links, bootstrap 1399 words) |
> | `build_all.py --data <fresh temp dir>`, then `--check` on the same directory | both exit 0, `"violations": []` |
> | `OutlookArchive('.local/outlook-archive').verify()` after the suite ran | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}` |
> | `-v tests.test_grid_outlook.RealArchive tests.test_grid_outlook.RenderedPageWithAttributions` | 9 ran, OK. The real-archive pin and the two node-rendered attribution tests really ran here; they were not skipped. |
> | My own probe: edit a stored attribution's statement, reseal it, keep its file name | `verify()` reports `ARCHIVE_TAMPERED` |
> 
> ## Checklist
> 
> 1. **Every acceptance item met by a check that was run: yes.**
>    - **Record matches the intent field for field:** the builder, validator and cross-record check match the intent's table line for line (`src/outlook/records.py:433-546`). The task record lists three readings, as the acceptance requires (§2): optional fields as null, `effective_at` not in the key, `share` validated but not normalized.
>    - **Key rebuilt from the stored record; renamed or copied file is `ARCHIVE_TAMPERED`:**
>      - The key is rebuilt on every read (`_read_record` with `attribution_key`).
>      - `test_a_renamed_or_copied_file_is_archive_tampered` covers the renamed and copied file; my resealed-edit probe confirmed the rest.
>      - Duplicates are refused by an `O_EXCL` create, and there is no sequence number.
>    - **Nothing written to the real archive:** the archive reads 2 / 0 / 0 / 0 after my own suite run.
>    - **Existing assertions kept, suite and fresh bake pass:**
>      - The only edits to existing tests are three exact `verify()` dictionaries that gain `"attributions": 0`. That makes them stricter, not weaker.
>      - No grid test file lost a line, and `test_grid_data` / `test_grid_event` are untouched.
>    - **CLI, routes and the real-archive card:**
>      - `--attributed-by` is `required=True`; the test expects exit 2 and that no write happens.
>      - The CLI imports only the standard library and `src.outlook.records`.
>      - No new route was added.
>      - `RealArchive.test_the_real_archive_carries_no_receipt_and_no_attribution` ran.
>    - **Direction check:** recorded as 0 in the real archive and 3 in the fixture (§7). `DirectionCheck` and `Demonstration` prove the 3 under a temporary root with the workspace fallback.
> 2. **No file outside the allowed paths: yes.** The scope check printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened or skipped: yes.** The diff touches no frozen contract file. The new skip guards on the real-archive tests follow the existing `RealArchive` pattern, and they ran here.
> 4. **No new dependency, service, credential, network, model or cloud effect: yes.** Standard library only, no clock read (`--attributed-at` is required), no route.
> 5. **Mode labels truthful: yes.**
>    - The fixture outlook, receipt and attributions are all `synthetic: True`, and the card prints "(synthetic)" from the record's own flag.
>    - A real attribution on a synthetic receipt is refused (`test_provenance_is_inherited_one_way`).
> 6. **Unknowns stayed unknown: yes.** No real receipt or attribution was written. §11 states that the first real count waits for the first settled month.
> 7. **Packet records interpreter, commands, results, unfinished items and next action: yes.**
>    - §8 covers the interpreter, every command and the re-run on the committed tree.
>    - §11 has the unfinished items and the exact next action.
>    - The `PROGRESS.md` row was edited in place, not duplicated.
> 8. **Nothing contradicts the blueprint, strategy, working paper or domain invariants: yes.**
>    - Attribution is a separate record beside the sealed receipt, never inside it.
>    - A person writes it through the CLI, which is the only write path; no model path exists.
>    - The page updates are left to the orchestrator after the merge, as the brief says.
> 
> ## Findings
> 
> None are blocking or important.
> 
> - **minor** | `src/outlook/records.py:725-735` (`_receipt_of`) | Before writing, `append_attribution` reads every receipt file to find the one the attribution cites. It therefore refuses with `ARCHIVE_TAMPERED` if any unrelated receipt is corrupt. | The packet discloses this read (§3, probe item 3). It is a read for the cross-record check, not a duplicate or sequence scan, so it does not break "no scan before a write". | No change needed now. Optionally, the CLI could pass the receipt it has already resolved.
> - **minor** | `src/outlook/records.py:450-473` (`attribution_key`) | `share`, `attributed_at` and `effective_at` are not part of the key, so an edit to only those fields, resealed with a new digest, still verifies clean. My probe resealed `share` from 0.3 to 0.9 and `verify()` reported no problems. | This follows from the reviewed intent's key rule, the same way `marked_at` sits outside the stale mark's `_key_of`. It is not a departure by the executor. | No rework. If the owner wants those fields protected, that is an intent revision, not a change to this task.
> - **minor** | `src/outlook/records.py:399-402` | `share` accepts a leading sign, so `"+0.5"` and `"-0"` are stored as typed. | Both values pass `DECIMAL`; the packet records the "validated, not normalized" reading (§2, reading 3). | Optional: refuse a sign in the share field.
> 
> ## Verdict
> 
> **accept.** Every acceptance item was shown by a check I ran myself (the verify command, the full suite, the scope check, the fresh bake and `--check`, and the real archive's 2/0/0/0), and nothing blocking or important is open.


Verdict recorded by the overnight runner: **none**. The orchestrator reads this record after the run.

## Orchestrator reading (2026-10-17 14:10)

The runner recorded **none** because the reviewer's output puts the verdict under a `## Verdict` heading
as "**accept.**", a form the runner's pattern did not match (hardened the same hour on main). The quoted
output above is an accept: every acceptance item shown by checks the reviewer ran (verify command, full
suite, scope, a fresh bake with `--check`, the real archive at 2 outlooks, 0 receipts, 0 attributions, 0
problems), nothing blocking or important open, three minor notes: `append_attribution` reads the stored
receipts to find the one the attribution cites before the exclusive create (a read, not the
scan-then-write race the intent refuses; the key stays content-derived); `share`, `attributed_at` and
`effective_at` are not part of the key, so two statements differing only there are one record (as the
intent's key list says; widening the key is an intent revision, not a task change); `share` accepts a
leading sign (optional tightening). **Verdict: accept.** State `done`.
