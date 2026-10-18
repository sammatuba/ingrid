# OUT-3 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Field | Value |
|---|---|
| Task | OUT-3: the availability term and the third vintage (the method `seasonal_plus_availability`, the known-outages export, the method command, the fixture loop, the impact per account on the fixture book) |
| Branch | `task/OUT-3` (worktree `.local/wt/OUT-3`) |
| Commit under review | `2cbeb848` |
| Base | `c4a92460`, with `task/BOOK-2` merged at its accepted head `38101319` (commit `df4b67da`); that tree equals `origin/main` at `2fee0054`. `origin/main` has since moved to `d5f172fe` (the DOCK batch); the scope check is OK against both |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author (the owner's rule of 17 October while the Codex seat has no credits) |
| Verdict | **rework** (three major findings, five minor; the code is careful and the fixture evidence is complete, but the real issue as prepared would break the site bake and the offline suite, and the method cannot follow decision (b) without a code change) |

Interpreter `/usr/bin/python3`. No network, model, BigQuery or cloud call. The reviewer wrote only this
file. Every scratch archive lived in the session scratchpad, outside the repository. The real archive
and `.local/price` were read only: the real archive was copied into the scratchpad for the
before-and-after probes, and nothing was written back.

### What I verified by running

| Check | Result |
|---|---|
| `git diff 2fee0054..HEAD`, read in full | 15 files: `src/price/availability.py`, `scripts/outlook/availability.py`, `scripts/outlook/known_outages.sql`, `tests/test_price_availability.py`, the moved pins in `tests/test_outlook_reissue.py`, the five files under `tests/fixtures/price/event_study/out3/`, `third-outlook.md`, `out-3.md`, the one list entry in `tests/test_price_baselines.py`, `tasks.json`, `PROGRESS.md` |
| SHA-256 of every file under `.local/price` and `.local/outlook-archive` (30 files), before my first command and after the full suite and every probe | identical |
| `OutlookArchive('.local/outlook-archive').verify()` after all runs | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`; `StaleMarks(...).verify(archive)` gives `{'marks': 1, 'problems': []}` |
| `/usr/bin/python3 scripts/plan.py check && /usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` | `OK: 135 tasks, 9 gates`; `Ran 2898 tests in 174.230s`, **OK (skipped=115)** |
| `python3 -m unittest tests.test_price_availability` / `tests.test_outlook_reissue` / `tests.test_price_response` / `tests.test_price_baselines` | 39 OK / 49 OK / 70 OK / 88 OK |
| `python3 scripts/plan.py scope OUT-3 origin/main` and `... scope OUT-3 2fee0054` | `OK: all changed files inside OUT-3 allowed paths` (both) |
| `python3 scripts/repo.py check` | `Checked 612 Markdown files, 3886 local links, 5 skills; bootstrap 1399 words. PASS` (before this file) |
| `git diff --check 2fee0054..HEAD`; `git status --short` after all runs | clean; clean |

**One outage hour by hand.** The fixture's line 2: CLUZ, forced, 400 MW, 26 October 00:00 to 06:00
Manila. I read the demand fixture with my own reader. For each of the six hours, the same clock hour on
the weekdays of the 28 days before 15 October gives 20 samples of 10,000 MW, so the regional demand is
10,000 MW. The cell is CLUZ 300+ MW (median -8,000, p10 -36,000, p90 54,000). The size is 400 / 10,000 =
0.04, so the shift is p50 -320, p10 -1,440 and p90 +2,160. The written row at 26 October 00:00 is
4,011.25 before, and p10 2,571.25, p50 3,691.25 and p90 6,171.25 after. **The mean by hand:** the
differences of the 744 point values, read as decimals from both files, sum to 14,680. Exactly 42
hours are nonzero, and the mean is 19.7311827…, which the stored delta block gives as `19.731183`.
In the other 702 hours the value is the predecessor's own decimal text, and p10 = p50 = p90 = value.
So the month moves only through the mean. `apply` is called once per outage with share 1, and nothing
else is diluted.

**The demand proxy, discriminated.** The fixture's demand does not vary by clock hour, so I probed
`demand_at` with demand set to 1,000 × the clock hour, plus a weekend step, plus a step for rows older
than 28 days. A Monday 09:00 gave 9,000 and a Saturday 09:00 gave 109,000. A mid-day cutoff excluded
the rows after it. The rule works as the record states it.

**The full loop through both commands, on a scratch archive** (the test helper `build_predecessor`, then
the commands exactly as `third-outlook.md` prints them, with the paths in the scratchpad):

| Step | Result |
|---|---|
| `availability.py` without `--allow-exploratory` | exit 1 `EXPLORATORY_CELL (CMIN 50 to 150 MW)`; nothing written (the values folder still holds only the predecessor; no method record) |
| the same with `--allow-exploratory` | exit 0. Values `e249ea4e…ea50` and run record `0ea5774c…9dc2`: both equal the page's path-independent digests. Counts: 6 known, 4 applied (1 forced, 3 planned), 2 not applied, 42 of 744 hours shifted. The preview delta has mean `19.731183`, mean absolute `24.892473`, min `-320.000000` and max `600.000000` |
| the same again | exit 1 `OUTPUT_EXISTS`; nothing replaced (every write is `open("xb")`) |
| `issue.py --supersedes fixture-2026-11-system-v2 --reason method_changed --preview-out`, then `--confirm fixture-confirmation-out3` | exit 0 and exit 0. The `supersedes` block names the predecessor by id and digest, `method_changed`, `stale_marks: []`, the delta, and the confirmation. `verify()` gives `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`. `model_version` is `seasonal_plus_availability out-3.1 (exploratory cells applied)` and `synthetic` is true |
| `compare_vintages(archive, "fixture-2026-11-system-v3")` | `availability.read: true`, the label, `exploratory: true`, the zero statement and the response digest are read back from the run record by digest |
| a known-outages file of only lines 6 and 7 (no cell; no whole hour) | exit 1 `REPEATS_PREDECESSOR`; no file is written |
| `read_known_outages` and `read_demand` on files named `rtd_…` or `…realtime…` | `REAL_TIME_REFUSED`, before the header is read |
| the executor's documented root `.local/out3/fixture-loop` (read only) | method record `d9fba4f5…a2cb`, preview `2c8a04ad…7719`, predecessor `9a380389…21aa2`, third vintage `08fb7116…1f96`: each equals the page. `verify()` is clean |

**The impact per account (BOOK-2), reproduced.** I used BOOK-2's `load_vintage`, `build_impact` and
`compare_impacts` on my own scratch archive, with the committed book, the window 1 to 7 November, the
question cutoff `2026-10-20` and the line 1,000,000 PHP `at_or_above`. All ten rows of the page's
table come back byte for byte, and none is material. On the documented root the three record digests
reproduce: `fd9dabef…d8ad`, `e3b494e7…b232` and `641e4ac6…794f`. With the cutoff `2026-10-19` the
third vintage is refused `VINTAGE_AFTER_CUTOFF`.

**The known-outages SQL.** Every column it reads is defined by `scripts/data/sql/12_outage_events.sql`:
`run`, `resource_name`, `status`, `start_manila`, `end_manila`, `start_utc`, `end_utc`,
`first_seen_manila`, `first_seen_utc`, `last_seen_manila`, `revision_no`, `n_revisions`,
`superseded_at_manila`, `region_code` and `p_max`. Its output columns are `KNOWN_OUTAGES_HEADER`
exactly, in order. The cutoff `TIMESTAMP '2026-10-15 00:00:00'` is 2026-10-14T16:00Z in Manila time.
The window is 26 October 00:00 to 26 November 00:00. `ROW_NUMBER` is filtered after the `WHERE`, so
the pick is among the in-force rows. The forced rule is OUT-2's. The statement was not run.

**A third vintage on an archive shaped like the real one.** I made two copies of the real archive in the
scratchpad. In one I issued `outlook-2026-11-system-v3` through both commands. Its inputs were the real
`response.json`, the real `demand_hourly.csv` and the fixture's six outages under a plain name, so the
vintage is not synthetic, as the real one will not be. The run on the real second vintage's values
shifted 42 hours. The line 2 shift on real demand is p50 -371.871238, from 8,956.87 MW. The other 702
hours keep their decimal text exactly. Then I ran every test module that reads `REAL_ARCHIVE`, with
`REAL_ARCHIVE` pointed at each copy:

| Module | Without a third vintage | With a third vintage |
|---|---|---|
| `tests.test_outlook_reissue` (the five moved pins and the scratch class) | OK | OK |
| `tests.test_price_availability` | OK | OK |
| `tests.test_grid_outlooks_page` | OK | **error**: `TheRealArchive.setUpClass`, `BuildInputError: the values file … does not state origin, cutoff_local, source` (finding 1) |
| `tests.test_grid_outlook` | OK | **2 failures** (finding 2) |
| `tests.test_grid_event` | OK | **1 failure** (finding 2) |
| `tests.test_outlook_scoring` | OK | **1 failure** (finding 2) |
| `tests.test_outlook_attribution` | OK | **1 failure** (finding 2) |
| `tests.test_outlook_dependency` | OK | **1 failure** (finding 2) |
| `tests.test_grid_register_page` | OK | **1 failure** (finding 2) |

The five moved pins hold in both states. The old assertions, run the same way, hold before the third
vintage. After it, the old count, "no `supersedes`" and key-set assertions go red, as the executor said.
The old real-archive `NOT_LATEST_VINTAGE` assertion still holds after it (finding 5).

### Acceptance, line by line

| Acceptance line | Proved |
|---|---|
| the third vintage exists in .local/outlook-archive with verify() clean, issued by the command, superseding the second, with the delta block; the values differ from the second vintage by the stated response or the issue is refused and recorded | **fixture: yes**, by the commands, on a scratch archive (above). **Real: not yet, and not ready.** It waits on the orchestrator's export, method run and confirmed issue before 2026-10-25T16:00Z. As prepared, that issue would break the bake (finding 1) and the suite (finding 2), and it cannot follow decision (b) (finding 3) |
| every figure in third-outlook.md ties to a record by digest; the small-sample label travels from the response to the vintage and to the page | **figures: yes**, each recomputed. **Label:** the label reaches the values file, the run record, the method version and `compare_vintages`. It does not reach the site's outlooks page, because the bake refuses the third vintage's values file (finding 1). The zero statement can contradict decision (b) on the real record's one-event cell (finding 4) |
| the dock's "What does this trip do to the outlook?" on the PEDC event composes the vintage comparison from the archive (tests executed on the fixture archive) | **half**: `compare_vintages` exists and is tested on the fixture archive. The dock is on `origin/main` since `0a71d80a`, after this base. It composes in `src/judgment/view.py`, which is outside OUT-3's allowed paths. The executor recorded this as hand-back 4, correctly under the stop conditions (finding 6) |
| every existing assertion in the touched test files is kept; the full offline suite passes; no live call | **today: yes**: 2898 OK, and the new modules use the standard library and `src` only. **After the real issue: no**: eight tests in seven modules go red (finding 2), and one granted move removed an assertion that still holds (finding 5) |

### Findings

1. **major**: `src/price/availability.py:149-150` (`VALUES_HEADER_KEYS`) and `:722-738` (the values
   payload), against `scripts/grid/build_data.py:1210-1212` (`VALUES_HEADER_TEXT`) and the input
   check in `values_block` (`:1536-1541`). Acceptance lines 1, 2 ("to the page") and 4. The
   bake resolves every vintage's values file by `path_hint` and stops the build unless the header
   states all of `series`, `series_label`, `billing_month`, `horizon`, `origin`, `cutoff_local`,
   `window_start_hour_local`, `window_end_hour_local`, `baseline`, `baseline_version` and `source`,
   and an `input` object `{file, sha256}`. The method keeps eight of those keys. It drops `origin`,
   `cutoff_local` and `source` and writes no `input` (commit `bdfb10ec`, "the values header kept to
   window and series"). Repro: `outlook_index_files(DEFAULT_REGISTER, <copy with a third vintage>,
   [])` raises `BuildInputError: the values file …/outlook-2026-11-system-v3.json does not state origin,
   cutoff_local, source`. With those three added it raises `… does not name its input by file and
   digest`. With `input` also added, `values_block` accepts the file and copies the band. The claim at
   `third-outlook.md:236` and `out-3.md:200` ("no reader in … `scripts/grid` lists that folder, so it
   misleads none") is true, but it does not answer the question. The bake does not list the folder: it
   reads the file the record names. Once the real third vintage is issued, the next bake fails, and so
   does the deploy. Correction: write the eleven header keys and `input` with stated meanings.
   Suggestion: `origin` is the window's first local day. `cutoff_local` is the new information cutoff
   in Manila time, or the predecessor's embargo cutoff if the band's baseline is read as unchanged;
   choose one and state it. `source` and `input` name the file the values rest on: the predecessor's
   values file by digest, or the run record. Add a test that bakes the fixture-loop archive through
   `outlook_index_files` and finds the third vintage, its `model_version` (with the exploratory suffix
   when one applies) and its band.
2. **major**: the real-archive pins outside `tests/test_outlook_reissue.py`. Acceptance line 4, and
   the executor's own standard that the pins "hold both before and after". Once a non-synthetic third
   vintage exists, these go red (proved on a real-shaped copy, table above):
   - Inside OUT-3's allowed paths: `tests/test_grid_outlook.py:919` (the second vintage as the
     current one) and `:967`; `tests/test_grid_event.py:1236` ("current · issued 17 Oct 2026 03:00
     UTC"); `tests/test_outlook_scoring.py:616` (`(outlooks, receipts) == (2, 0)`);
     `tests/test_outlook_attribution.py:623`; `tests/test_outlook_dependency.py:675`.
   - Outside them: `tests/test_grid_outlooks_page.py:590` (the class errors at `setUpClass`, by
     finding 1) and `tests/test_grid_register_page.py:384` (the archive's vintage list).

   The `test_outlook_dependency` pin needs a decision. It requires that "the newest issued vintage of
   the same series must cite the export as it is now", and the third vintage cites the predecessor's
   values file, the response, the outages, the demand and the run record, but not
   `lwap_final_hourly.csv`. The third vintage's values do rest on that export, through the
   predecessor. So the honest fix is to carry the predecessor's input citations forward in
   `method_record`. The other choice is to scope the pin to the newest first issue.
   `third-outlook.md:226-229` ("5. the checks") runs only two modules. With it, the orchestrator
   would issue the vintage and leave the suite red on main. Correction: move the six pins inside the
   allowed paths so that they hold for 2 vintages, or for 3 with the third superseding the second.
   Keep every assertion for the two first issues. Prove the move on a real-shaped scratch archive, as
   done here. Hand the two outside files to the orchestrator for a path grant, or for a pin move at the
   merge. Change step 5 to run the full offline suite and the bake.
3. **major**: `src/price/availability.py:562-629` (no outage-class filter) and
   `scripts/outlook/known_outages.sql:93`. Decision (b) ("for every forced outage record known at the
   14 October cutoff") and strategy decision 12 ("for every forced outage above a stated size … applied
   to the band for the outage's stated duration"). The method applies forced and planned records alike
   and has no switch. The recorded decision can be followed only by a code edit, or by a hand edit of
   the export, which breaks the export-by-digest chain. The executor recorded the deviation and asked
   (deviation 4, hand-back 3). That is the correct process, but the real run still cannot follow (b)
   as built. Correction: a class selection that defaults to forced (`--outage-class forced|both`, or
   `--include-planned`). Planned records stay under `not_applied` with the reason "planned: the
   response was measured on forced outages". The selection travels like the exploratory flag: in the
   run record, the label and the method version.
4. **minor**: `src/price/availability.py:525-535` (`zero_statement`) and `:665-670` (`run_label`).
   Decision (b) ("the vintage states that the response is not distinguishable from zero at p10 and
   p90"). The real response record's CMIN 150 to 300 MW cell has one event, so p10 = median = p90 =
   13,631.28. Repro: `zero_statement([CLUZ 300+ MW, CMIN 150 to 300 MW])` on the real cells returns
   "The response is distinguishable from zero at p10 and p90 only in CMIN 150 to 300 MW; …". When that
   statement applies, the run label leaves out the zero clause, because it is written only when every
   cell straddles zero. A cell of one event has no spread: it cannot show that the response is
   distinguishable from zero. The path is reached only with `--allow-exploratory`, but the sentence
   would go into an append-only record. Correction: never count a small-sample cell (or one with
   p10 = p90) as distinguishable. Name it "exploratory: too few events to tell". Always write a zero
   clause in the label. Add a test on a one-event cell.
5. **minor**: `tests/test_outlook_reissue.py:794-797`; the base's `:770-780` removed. Acceptance line
   4 ("every existing assertion … is kept"). The base's real-archive assertion, that the
   demonstration mark gives `NOT_LATEST_VINTAGE`, holds unchanged after a third vintage. The newest
   vintage is then the third, which is still newer than the marked first. I proved it on the
   real-shaped copy. Note (d) allowed the move. But the move swaps a check of the owner's archive for
   a scratch analogue, and it was not needed. Correction: restore the base assertion in the
   real-archive class, verbatim, and keep `NotLatestVintageOnTheRealArchiveShape` as well.
6. **minor (orchestrator decision; not counted toward the rework)**: acceptance line 3. The record
   side is done and tested (`compare_vintages`). The composer in `src/judgment/view.py` (DOCK, on
   `origin/main` since `0a71d80a`) is outside the allowed paths, so the executor stopped and handed it
   back, as the rules require. The orchestrator must either grant `src/judgment/view.py` and
   `tests/test_judgment_view.py` for the rework, or move the line to a follow-on task and record the
   amendment. The executor's note on hand-back 4 also applies: the PEDC trip does not change the
   third vintage's beliefs. So the comparison that the question shows is the method change, and the
   dock's words must say that.
7. **minor (deviation judged; accept with a record)**: the system basis
   (`src/price/availability.py:153-157`). From the real demand export, the regional shares of system
   demand over the four weeks before the cutoff are CLUZ 0.713, CVIS 0.143 and CMIN 0.144. When only
   the outage's own region moves, an unweighted CVIS or CMIN shift overstates the system shift by
   about 7 times, and a CLUZ shift by about 1.4 times. "An upper bound" holds only if the other regions
   move less than the outage's own region. The method already reads the demand that a known-at
   load-share weight needs, so the weight is not an invented input. Recommendation: the orchestrator
   decides before the real run. My preference is the load-share weight from the same proxy, as a
   stated method version. If it is not used, the run record should state the factor per region
   (`1 / share`), not only "an upper bound".
8. **minor (deviations judged; accepted)**:
   - The demand stand-in (the same clock hour and weekday class in the four weeks before the cutoff)
     is the honest reading, because the export ends on 14 October. I probed it and it is correct. It
     measures September and October demand for November hours: state that seasonal limit in the
     rules. Add one test whose demand varies by clock hour (the committed fixture cannot catch a
     wrong hour).
   - No register rows: accepted as hand-back 1. The register test pins 43 rows. The consequence is
     that a later change to the response record or to the outage schedule cannot mark the third
     vintage stale through the dependency path until the two rows exist; record it.
   - The fixtures under `tests/fixtures/price/event_study/out3/`: accepted. The path is allowed, and
     the folder is OUT-2's own.
   - Prose: the work records keep the house style, and `repo.py check` passes.

### Judgments the orchestrator asked for

**Forced only, or both classes, for the real run: forced only.** Decision (b) and strategy decision 12
say "forced", and the response was measured on forced outages: the price over the first six hours
after an unannounced start. Planned outages are announced, so their price effect is partly priced in.
The seasonal baseline averages past billing months that held their own planned maintenance, so adding
the known planned schedule on top counts part of it twice. The executor's observation is right: a forced
record known at the cutoff for November is one already in progress on 15 October with an end after
26 October, so the forced set may be small or empty. If it is empty, the run refuses
`REPEATS_PREDECESSOR`. That is the honest result the acceptance line allows ("or the issue is refused
and recorded"). If a planned schedule is wanted, the orchestrator should decide it in writing as a
second, labelled run. It should not be the default of the first.

**`--allow-exploratory` for the real run: no, by default.** In the real record the exploratory cells
are CLUZ 50 to 150 MW (9 events, straddles zero) and CMIN 150 to 300 MW (1 event). If the run refuses
on the CLUZ cell, allowing it is a defensible owner decision, with the label carried. If it refuses on
the CMIN cell, do not allow it. One event is no spread, and with today's code it would put a false
"distinguishable from zero" sentence in the vintage (finding 4). A third behavior is worth considering
in the rework: without the flag, list an exploratory outage under `not_applied` ("exploratory cell,
not applied") instead of refusing the whole run. Many Luzon units fall in 50 to 150 MW, so a refusal
there is likely.

### What waits on the orchestrator's real run (recorded conditions, after the rework)

- the known-outages export (dry run, then the run under the cap; its row count and SHA-256 added to
  `.local/price/digests.json`);
- the method run on the real inputs with the chosen class selection and exploratory choice;
- the preview and the confirmed issue with a confirmation reference, issued before
  **2026-10-25T16:00Z** and after 2026-10-17T03:00Z;
- `verify()` with 3 outlooks, 0 receipts and no problems; the full offline suite and a bake after the
  issue;
- the filled "Real run" table in `third-outlook.md`, or the recorded `REPEATS_PREDECESSOR` refusal with
  the export's digest and row count.

### Verdict and exact rework

**rework.** Required:

1. Write the full values header (`origin`, `cutoff_local`, `source` and an `input {file, sha256}`, with
   stated meanings) so that `scripts/grid/build_data.py` bakes the third vintage. Add a test that bakes
   the fixture-loop archive and finds the third vintage, its `model_version` and its band (finding 1).
2. Move the six real-archive pins inside the allowed paths so that they hold for 2 vintages, or 3 with
   the third superseding the second. Keep every assertion for the first two. Decide the
   `test_outlook_dependency` export pin (carry the predecessor's input citations forward, or scope the
   pin), and prove all of it on a real-shaped scratch archive. List the two outside files for the
   orchestrator. Change "Real run" step 5 to the full offline suite and a bake (finding 2).
3. Add the outage-class selection, forced by default, carried in the run record, the label and the
   method version (finding 3).
4. Fix the zero statement for small-sample and one-event cells, always carry a zero clause in the
   label, and test it (finding 4).
5. Restore the base's real-archive `NOT_LATEST_VINTAGE` assertion verbatim (finding 5).
6. Record the orchestrator's decisions on findings 6 and 7 in `out-3.md` once they are made. Add the
   seasonal limit of the demand proxy to the rules, and a test with demand that varies by clock hour
   (finding 8).

Then run the verify command and the full suite, `plan.py scope OUT-3 origin/main`, `repo.py check` and
`git diff --check`, and request round 2.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Field | Value |
|---|---|
| Commit under review | `93050c90` (rework round 1: `5312520d`, `30f6229c`, `93050c90`, on top of the merge `dadaef1a` of `origin/main` `d14946ab`) |
| Base | `origin/main`, now `b6f86cc9`; the scope check is OK against it |
| Brief | the OUT-3 note with decisions (h) to (m) of 2026-10-18; acceptance line 3 narrowed to the archive side (the composer is DOCK-6's); `tests/test_grid_outlooks_page.py` and `tests/test_grid_register_page.py` granted |
| Verdict | **accept**. The code and fixture evidence are complete. The real issue remains the orchestrator's recorded condition: it must be issued before 2026-10-25T16:00Z |

I read `git diff 2cbeb848..93050c90` in full. The OUT-3 part is `git diff dadaef1a..93050c90`: 16 files. The
rest is the DOCK batch and `scripts/grid/build_data.py`'s receipt change, both from `origin/main`. As in
round 1, I wrote only this file. Every probe ran on copies in the session scratchpad.

### What I verified by running

| Check | Result |
|---|---|
| `plan.py check && unittest discover` (the verify command, the full offline suite) in the worktree | `OK: 135 tasks, 9 gates`; `Ran 3069 tests in 175.302s`, **OK (skipped=115)** |
| `tests.test_price_availability` / `tests.test_outlook_reissue` | 49 OK / 50 OK |
| The seven moved-pin modules: `test_grid_outlook`, `test_grid_event`, `test_grid_outlooks_page`, `test_grid_register_page`, `test_outlook_attribution`, `test_outlook_scoring`, `test_outlook_dependency` | 70 OK; 94 OK (3 skipped); 47 OK (21 skipped); 38 OK (16 skipped); 39 OK; 42 OK; 60 OK |
| `plan.py scope OUT-3 origin/main` (`b6f86cc9`); `plan.py check`; `repo.py check`; `git diff --check 2cbeb848..HEAD` | OK; OK; PASS (619 Markdown files, 3903 local links); clean |
| SHA-256 of the 30 files under `.local/price` and `.local/outlook-archive`, after every round 2 run | identical to round 1's first snapshot |
| `OutlookArchive('.local/outlook-archive').verify()`; the mark store | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`; `{'marks': 1, 'problems': []}` |

**Two real-shaped copies, each with the full suite.** I copied the real archive twice into the
scratchpad. In the second copy I issued `outlook-2026-11-system-v3` through both commands. The inputs
were the real `response.json` and `demand_hourly.csv`, the fixture outages under a plain name, and
`--predecessor-input .local/price/lwap_final_hourly.csv` (`3b3b0b66…`, the digest the second vintage
cites). The result is not synthetic: 3 forced outages applied, 2 planned listed as not applied, 12 of
744 hours shifted, mean 0.981196. `verify()` gives 3 outlooks and no problems. I extracted `git archive
HEAD` twice into the scratchpad, linked the copies as `.local/outlook-archive`, and ran the full suite in
each tree. Both ran 3069 tests. Each failed the same 16 tests, failures=13 and errors=3, and the 16 are
identical in both trees. Every one of the 16 needs a git checkout (`git ls-files` or `check-ignore`):
release audit, tracked-path refusals, plan scope, integration contract. An extracted tree has no git
checkout, so the 16 fail with or without a third vintage. The third vintage adds no failure. The seven
moved-pin modules and both OUT-3 modules pass in both trees.

**The bake.** I ran `build_all.py --force --data <scratch> --outlook-archive <copy>` with the main
checkout's geo and vector inputs. Without a third vintage: exit 0, `"violations": []`. With it: exit 0,
`"violations": []`. The baked `outlook/index.json` lists `outlook-2026-11-system-v3` as current and as
superseding `-v2`, with `model_version` `seasonal_plus_availability out-3.2 (forced outages)`. Its rows
carry p10, p50, p90 and value, and its input is `outlook-2026-11-system-v2.json` `903437f3…`. The values
header states all eleven of `VALUES_HEADER_TEXT` and `input`. The new test pins that
`av.BAKE_HEADER_KEYS == build_data.VALUES_HEADER_TEXT`. It also runs `outlook_index_files` and
`outlook_index_problems` on the fixture-loop archive, whose predecessor has the real second vintage's
shape.

**The refreshed fixture loop, through both commands.** I ran it on my own scratch archive.

| Step | Result |
|---|---|
| without `--predecessor-input` | exit 1 `PREDECESSOR_INPUT_MISSING (lwap_final_hourly-synthetic.csv)`; nothing written |
| the defaults (forced, no exploratory flag) | values `c9ac6a87…`, run record `aeadb0a3…`, predecessor values `f8d94834…` (each equals the page). 6 known; 2 applied (forced); 4 not applied: 2 planned "planned: this run applies forced outages, …", 1 "exploratory cell CMIN 50 to 150 MW (4 events, below the minimum): not applied without allow_exploratory", 1 with no cell. Load shares CLUZ 0.7, CVIS 0.15, CMIN 0.15 over 672 hours, factors 1.43 / 6.67 / 6.67. Delta mean `-0.564516`, min `-280`, max `140` |
| `issue.py --supersedes … --reason method_changed --confirm` | issued; `verify()` 2 outlooks, no problems. `model_version` is `… out-3.2 (forced outages)`. The inputs cite `lwap_final_hourly-synthetic.csv` first, under its own name |
| the documented root `.local/out3/fixture-loop` (read only) | method record `323f72d6…`, preview `33c51905…`, predecessor `ccf0db08…`, third vintage `0f62a24d…`: each is in the page; `verify()` clean |

**By hand** (my own reader, outside the module): the fixture shares are CLUZ 0.7 over 672 complete hours.
Line 2: CLUZ forced 350 MW; the demand stand-in is 7,000 MW over the six hours; the cell is CLUZ 300+ MW.
The shift is p50 -8,000 × 350 / 7,000 × 0.7 = -280, p10 -1,260 and p90 +1,890, as in the run record.
The differences of the two values files, read as decimals, give a mean of -0.5645161…, over 6 nonzero
hours. In the other 738 hours the value is the predecessor's text, and p10 = p90 = value. **One real
share, aggregates only:** over the 648 hours before the cutoff that carry all three regions,
`demand_hourly.csv` gives CLUZ 0.713290, CVIS 0.142977 and CMIN 0.143733. These match the run record and
the page.

### The round 1 findings, one by one

| Round 1 finding | Round 2 |
|---|---|
| 1 (major) the bake refuses the values file | **closed**: the eleven header keys and `input` are written, with stated meanings (`HEADER_RULE`; `predecessor_cutoff_local` keeps the baseline's own cutoff). The test bakes the fixture loop, and my `build_all.py --force` on a real-shaped copy with a third vintage exits 0 with no violations |
| 2 (major) real-archive pins in seven modules | **closed**: the pins hold for 2 vintages, or for 3 with the third superseding the second. In the two-vintage state every old assertion still reads as before (`[[], []]` becomes `[[]] * len`, `(2, 0, 0)` becomes the count). The dependency pin holds because `--predecessor-input` carries the second vintage's `lwap_final_hourly.csv` citation forward, by name and digest. Proved by the full suite in both trees. "Real run" step 5 now runs `verify()`, the full suite and `build_all.py --force` |
| 3 (major) no outage-class filter | **closed**: `--outage-class` defaults to `forced`; `OUTAGE_CLASS_INVALID` outside forced and planned. The reader keeps both classes and marks `selected`. The other class is listed and counted (`not_applied_other_class`). The class is in the run record (`outage_class`, `rules.outage_class`), the label ("forced outages"), the values file and the method version (`… (forced outages)`, `… (planned outages, exploratory cells applied)`). A planned run adds the stated extension sentence |
| 4 (minor) the one-event cell called distinguishable | **closed**: `distinguishable` is false for a small-sample cell, a cell of one event, or p10 = p90. On the real CMIN 150 to 300 MW cell the statement reads "… has too few events to tell, so it is not counted as distinguishable". The label always carries a zero clause (`zero_clause`). A cell with a real one-sided spread is still named (probed) |
| 5 (minor) the removed `NOT_LATEST_VINTAGE` assertion | **closed**: restored verbatim in the real-archive class; the scratch class is kept. It holds in both of my copies |
| 6 (minor) the dock line | **closed by the orchestrator**: acceptance line 3 is now the archive side (`compare_vintages`, tested); the composer is DOCK-6's |
| 7 (minor) the system basis | **closed**: decision (k). The shift is weighted by the region's known-at load share from the same demand stand-in. The run record states the shares, the hours behind them and the unweighted factor per region (`load_shares`). It also states that the basis reads the other regions' prices as unmoved |
| 8 (minor) the demand stand-in | **closed**: the seasonal limit is in `DEMAND_RULE` and the module docstring. A new test uses demand that varies by clock hour, weekday class and age, and a noon cutoff. The register rows stay a recorded hand-back; the fixture folder is accepted |
| (j) exploratory cells | an outage in an exploratory cell is listed as not applied and counted (`not_applied_exploratory`) unless `--allow-exploratory`. The label says "1 exploratory outage(s) not applied" |

### Findings, round 2

No major or minor finding remains. Two nits, neither blocking:

1. **nit**: `src/price/availability.py:241`. `EXPLORATORY_CELL` stays in `MESSAGES`, but no path raises it
   since decision (j). Remove it, or note that it is kept for an older caller.
2. **nit**: `src/price/availability.py:607-610`. With two or more cells of too few events, the sentence
   reads "A (4 events), B (1 event) has too few events to tell"; "have" would fit. The wording is
   correct for one cell, which is the real record's case.

### What waits on the orchestrator's real run (recorded condition)

- The known-outages export: dry run first, then the run under the cap. Record its rows by class and its
  SHA-256 in `.local/price/digests.json`.
- The method run with the defaults (`--outage-class forced`, no `--allow-exploratory`) and
  `--predecessor-input .local/price/lwap_final_hourly.csv`. The run refuses
  `PREDECESSOR_INPUT_MISSING` if that export changes before the run (today it is `3b3b0b66…`, the digest
  the second vintage cites).
- The preview, then the confirmed issue, between 2026-10-17T03:00Z and **2026-10-25T16:00Z**.
- `verify()` with 3 outlooks; the full suite; `build_all.py --force` with no violations.
- The filled "Real run" table, or a recorded `REPEATS_PREDECESSOR` refusal (a likely result if no forced
  outage known at the cutoff reaches November), with the export's digest and row count.

### Verdict

**accept** for `93050c90`. Every acceptance line is met on the fixture archive, and the real-shaped proof
holds. The real third vintage remains the orchestrator's recorded condition, due before
2026-10-25T16:00Z.
