# SCORE-1: the scoring command, exercised on fixtures until the first month settles

Task record, written 2026-10-17 by the SCORE-1 executor seat on branch `task/SCORE-1` from
`87560739` (`feat/product-refine`, the same commit as `main`). Offline throughout: no model,
network, cloud, credential or clock call; every instant is a caller-supplied field, and the one
clock reading is the command's own printed default when `--scored-at` is omitted. The values files
and the final export stay under the ignored `.local/`: no price value, node name or volume enters
this repository, and this record quotes none.

**Read first, in the brief's order.** [AGENTS.md](../../../AGENTS.md);
[milestones](../milestones.md); [the archive records](records.md) (ARCH-1);
[`src/outlook/records.py`](../../../src/outlook/records.py);
[the scorecard](../../../src/price/scorecard.py); [the series reader](../../../src/price/series.py);
[the baselines](../../../src/price/baselines.py); [the first outlook](first-outlook.md) (ARCH-3);
[the attribution record](attribution.md) (ARCH-4); [`scripts/outlook/attribute.py`](../../../scripts/outlook/attribute.py);
[the price target contract](../price-outlook/target-contract.md).

## 1. What was built

| Path | What it is |
|---|---|
| `src/outlook/scoring.py` | `score_outlook(outlook, values_file, regional_export, digests, *, scored_at, final_series_version)`: reads the outlook's values file (checked by digest and row count), reads the final regional export only when its bytes match the digest record, refuses a window that has not settled (`WINDOW_NOT_SETTLED`), skips marked intervals with reasons, computes the six contract metrics with the scorecard's own `metrics_from`, and returns the receipt sealed by `records.build_receipt`. Standard library only, plus the repository's price and archive modules. |
| `scripts/outlook/score.py` | **New command.** `--archive`, `--outlook-id`, `--regional`, `--digests`, `--final-series-version` (required), `--scored-at` (default the clock, printed), `--dry-run`. Builds through `score_outlook`, appends through `OutlookArchive.append_receipt` (so `RECEIPT_DUPLICATE` is the store's), and prints the effective instant, the window, the coverage, and the receipt's storage key and digest. It never issues an outlook and never writes an attribution. |
| `tests/test_outlook_scoring.py` | **New, 42 tests.** Every refusal by code on labelled synthetic fixtures under a scratch root (workspace fallback), the metrics against `metrics_from` on the same pairs, the marked intervals in `coverage.skipped`, the CLI end to end including `--dry-run`, and the real archive's refusal with the current export. |
| `docs/work/outlook-archive/scoring.md` | This record. |

Nothing else was touched: `src/outlook/records.py`, `src/price/` and the other outlook test files
are read, never edited; no route, page, frozen contract or acceptance text changed.

## 2. The scoring rule, field by field

`score_outlook` takes the issued outlook (re-validated with `validate_outlook`), the values file
its `values_ref` cites, the final regional export, the export digest record, the run instant and
the settled vintage's name.

| Step | Rule, as implemented |
|---|---|
| Settled instant | `scored_at` at or after `horizon.end`; otherwise `WINDOW_NOT_SETTLED`. No clock is read in the module. |
| The series | `target_series_ref` must be the target contract's regional reference series (`grid_raw.ext_pmr_lwap_final`, column `lwap`); the values file's `series` key selects the region (`CLUZ`, `CVIS`, `CMIN`, `SYSTEM`) in the export. Another target is `SERIES_UNSUPPORTED`. |
| Values file | Bytes read once; SHA-256 must equal `values_ref.sha256` (`VALUES_DIGEST_MISMATCH`), the hour count must equal `values_ref.rows` (`VALUES_ROWS_MISMATCH`), and every hour must carry `hour_start` and `value` (`VALUES_SHAPE`). `hour_start` is a naive whole Asia/Manila hour, the export's own clock. |
| Covering the horizon | The values' local hours must be exactly the outlook's horizon hours — no gap, no duplicate, nothing outside (`VALUES_INCOMPLETE`). A partial file is a hand-back, never a partial score. |
| Final export | `verify_inputs([regional_export], digests)` runs before the bytes are parsed: an unrecorded file is `EXPORT_DIGEST_NOT_RECORDED` and a changed file is `EXPORT_DIGEST_MISMATCH`. `final_series_digest` is the export's own SHA-256. A real-time copy has no recorded digest, so it has no path through the command. |
| Settled window | The selected series' last exported hour must reach the horizon end (+1 h); an export that stops earlier is `WINDOW_NOT_SETTLED`. |
| Marks | `derive_marks` on the final series, the scorecard's own marks. An hour on an irregular day (interval count not 288) is skipped as `irregular day <date>`; an hour in an all-administered billing month as `administered pricing <month>`; an hour in a mixed month as `administered pricing mixed <month>`. Each skipped hour is counted once in `coverage.skipped` under its reason; nothing is filled. |
| The band | A values row may carry `p10`, `p50`, `p90` (all or none). Present, they are read and sorted ascending (the scorecard's rearrangement rule) and scored as the quantiles; `value` stays the point forecast for bias, MAE and RMSE. Absent, the scorecard's quantile rule is applied with an empty residual fan: the point forecast at all three quantiles, a zero-width band. Nothing is invented; §5 records the reading. |
| Metrics | `metrics_from` on the `(realized, point, p10, p50, p90)` rows of each slice, exactly as PRICE-2 computes them; one row per horizon label and slice, its six numbers as decimal strings. `coverage.scored` counts the hourly values scored. |
| The receipt | `build_receipt(outlook, ...)`, so `outlook_id`, `outlook_digest`, the window-inside-horizon rule and `scored_at >= window.end` are the archive's own; `synthetic` is inherited from the outlook, one way. `final_series_version` is the caller's text. |

**The window is the whole horizon.** The command scores the interval the outlook predicted, which
the receipt's link rules allow; a slice option is not offered, so no caller can choose a flattering
window.

**The unit.** The values file is hourly and the realized side is the export row's mean, already the
interval-weighted mean of that hour (the scorecard's own aggregation reduces to it for one hour), so
the scored unit is the hour, and `intervals` on a metric row and `coverage.scored` count hourly
values. ARCH-1's receipt examples count a 744-hour month as 744.

## 3. The command that will score the first real pair

The first real pair is **November to December 2026**: `outlook-2026-11-system-v2` (and the first
vintage `outlook-2026-11-system`) predicted billing month 2026-11, whose settled final statement
arrives after 2026-11-25. When the final export is refreshed for that month and
`.local/price/digests.json` names the new bytes, this is the command, run from the repository root:

```sh
/usr/bin/python3 scripts/outlook/score.py \
    --archive .local/outlook-archive \
    --outlook-id outlook-2026-11-system-v2 \
    --regional .local/price/lwap_final_hourly.csv \
    --digests .local/price/digests.json \
    --final-series-version final-bmonth-2026-11 \
    --scored-at 2026-11-26T09:00:00Z
```

`--final-series-version` is the settled vintage's own name, required and never defaulted;
`--scored-at` must be at or after `2026-11-25T16:00:00Z` and is the operator's instant (the example
is the morning after the billing month closes). A dry run first prints the receipt and appends
nothing:

```sh
/usr/bin/python3 scripts/outlook/score.py \
    --archive .local/outlook-archive \
    --outlook-id outlook-2026-11-system-v2 \
    --regional .local/price/lwap_final_hourly.csv \
    --digests .local/price/digests.json \
    --final-series-version final-bmonth-2026-11 \
    --scored-at 2026-11-26T09:00:00Z --dry-run
```

The same command with `--outlook-id outlook-2026-11-system` scores the first vintage; the two are
different outlook ids, so both may be scored against the same final series version. Running a pair
twice is refused `RECEIPT_DUPLICATE` by the archive's exclusive storage key.

## 4. Direction check SCORE-1

The brief's check: **0 receipts appended to the real archive today; the first real receipt when
billing month 2026-11 settles.** Measured after this task's own test run:

```sh
/usr/bin/python3 -c "from src.outlook.records import OutlookArchive; print(OutlookArchive('.local/outlook-archive').verify())"
# {'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}
```

Both vintages are refused today with `WINDOW_NOT_SETTLED` at a `scored_at` of
`2026-12-01T00:00:00Z` — after their window closed — so the refusal is the export's, not the
clock's: the current export's last hour is `2026-09-25T23:00` local (billing month 2026-09), and
the outlook's window ends at `2026-11-26T00:00` local. The fixture demonstration appends exactly one
receipt for one settled window and refuses the second append `RECEIPT_DUPLICATE`; the fixture lives
under a scratch root and writes nothing into `.local/outlook-archive`.

## 5. Decisions a reviewer should see

1. **The band of a mid-only vintage.** The first vintage's values carry one `value` per hour and no
   quantiles. The scorecard's quantile rule is applied with an empty residual fan, which yields the
   same point at p10, p50 and p90 — a zero-width band — and the pinball terms are then those of the
   point forecast (`pinball_p50` is exactly half the MAE). The alternative would be to read earlier
   residuals from `.local/price/scorecard.json`, which the brief's signature does not name and
   which would mix a baseline's fan with this outlook's own forecast; that is not done. Values files
   that carry `p10`/`p50`/`p90` are read and scored directly; both paths are tested.
2. **Administered-pricing intervals are skipped, not scored in the `ap` slice.** The brief names
   "administered pricing and the irregular days" among the intervals skipped into
   `coverage.skipped`, and this command follows that reading. The receipt's `ap` slice stays in the
   contract; the regional export carries no per-hour pricing flag, so a mixed month cannot be split
   and is skipped with `administered pricing mixed <month>`. The first real window (2026-11) has no
   AP mark, so its receipt carries one `market` row either way.
3. **The local offset is one constant.** The export's `hour_start` is Asia/Manila local time, naive
   in the files (the target contract's "Interval" row); the Philippines has observed no daylight
   saving time since 1978, so `+08:00` is exact and no time-zone database is consulted.
4. **The target series is checked, not inferred.** The command reads only the regional export, so it
   refuses a `target_series_ref` other than the regional final series rather than guessing a
   mapping. A nodal outlook is `SERIES_UNSUPPORTED` today.
5. **The values must cover the horizon exactly.** A values file with a gap, a duplicate or an extra
   hour is refused rather than scored on the intersection; the outlook's record names its row count,
   and the two must agree with the horizon.

## 6. Commands and results

Run from the worktree root with `/usr/bin/python3` on this tree:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_outlook_scoring tests.test_outlook_records tests.test_outlook_dependency tests.test_outlook_attribution` (the brief's verify command) | `Ran 209 tests in 3.198s` / **OK** |
| `/usr/bin/python3 -m unittest tests.test_outlook_scoring` | `Ran 42 tests in 2.721s` / **OK** |
| `/usr/bin/python3 -m unittest discover -s tests` (the full offline suite) | `Ran 2232 tests in 248.913s` / **OK (skipped=58)** |
| `/usr/bin/python3 -c "from src.outlook.records import OutlookArchive; print(OutlookArchive('.local/outlook-archive').verify())"` | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 105 tasks, 8 gates` |
| `/usr/bin/python3 scripts/plan.py scope SCORE-1 feat/product-refine` | `OK: all changed files inside SCORE-1 allowed paths` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 534 Markdown files, 3532 local links, 5 skills; bootstrap 1400 words.` **PASS** |

The 58 skips are the repository's existing environment guards (node, real-browser, Firestore
emulator, wire and server-library classes), the same configuration other lanes record; nothing in
this task's paths skips, and the real-archive case ran because the runtime archive and the PRICE-2
export are linked into `.local/`.

Every command above was then run again on the committed tree, `a201d78`, with a clean
`git status`: the verify command `Ran 209 tests in 3.037s` / **OK**, the full suite
`Ran 2232 tests in 184.663s` / **OK (skipped=58)**, `plan.py check` `OK: 105 tasks, 8 gates`,
`plan.py scope SCORE-1 feat/product-refine` `OK: all changed files inside SCORE-1 allowed paths`,
`repo.py check` **PASS** (534 Markdown files, 3532 local links), and the archive's `verify()` still
`{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`.

## 7. Acceptance

| Acceptance item | Where it is proved |
|---|---|
| no receipt is appended to `.local/outlook-archive` by this task (`verify()`: 2 outlooks, 0 receipts, 0 problems after the test run); the real-archive test proves the refusal with the current export | §4's measured line; `RealArchive.test_both_november_vintages_are_refused_until_the_month_settles` (both ids, `WINDOW_NOT_SETTLED` at an instant after the window, the export's last hour asserted before the horizon end, and `verify()` unchanged at 2/0/0 with no problems) |
| the receipt built on the fixture validates against `records.validate_receipt` and the link rules (window inside the horizon, `scored_at` at or after `window.end`, synthetic inherited one way) and its metrics equal `src.price.scorecard.metrics_from` on the same `(realized, p10, p50, p90)` pairs | `SettledWindow.test_a_settled_window_scores_and_appends_once`, `test_the_receipt_s_window_is_the_whole_horizon_and_lies_inside_it`; `MetricsAgreement.test_the_metrics_equal_the_scorecard_on_the_same_pairs`, `test_the_zero_width_band_makes_pinball_p50_half_the_mae`; `Band.test_an_explicit_band_is_read_and_scored`, `test_a_crossed_band_is_reported_in_ascending_order`; `Provenance` (both directions) |
| final and real-time truth never mix: the command reads only the final export named by digest; marked intervals are skipped with reasons, never filled | `Settlement.test_an_export_without_a_recorded_digest_is_refused`, `test_an_export_that_does_not_match_its_digest_is_refused`; `Marks.test_marked_intervals_land_in_coverage_with_their_reasons` (96 administered hours and 24 irregular-day hours, each under its reason, 48 scored, the three counts summing to the 168-hour window), `test_the_irregular_day_is_excluded_from_the_metrics`, `test_a_window_entirely_in_an_administered_month_has_nothing_to_score` |
| the CLI refuses to run without `--final-series-version` and never calls a model or the network; standard library only | `CommandLine.test_the_command_refuses_to_run_without_the_final_series_version`, `test_the_command_never_issues_an_outlook_or_writes_an_attribution`, `test_the_command_scores_and_prints_the_key_and_digest`, `test_a_second_run_is_refused_as_a_duplicate`, `test_dry_run_prints_the_receipt_and_appends_nothing`, `test_the_command_defaults_scored_at_to_the_clock_and_prints_it`; `StdlibOnly` (imports only the standard library and the named repository modules) |
| every existing assertion in the outlook test files is kept; the full offline suite passes | no existing test file was edited; §6's suite run is green, and the outlook test files run together at 209 tests |

## 8. Self-review, and what a reviewer should probe

* **The rule is enforced where it lives.** The digest checks run before any bytes are parsed; the
  settlement check runs before any metric; the marks are the scorecard's own `derive_marks`; the
  metrics are the scorecard's own `metrics_from`; and the receipt is the archive's own
  `build_receipt`, so the link rules cannot drift from ARCH-1.
* **Nothing is filled.** A missing hour is marked through its day and skipped, a marked month is
  skipped with its reason, and a values gap is a refusal. No interpolation, carry-forward or
  neighbour value exists in the module.
* **The final series is the digest-recorded one.** `verify_inputs` matches by file name and compares
  the bytes; a real-time export cannot pass unless it is in the digest record, which names only the
  final export.
* **No clock in the module.** The command reads the clock once, prints it, and writes exactly the
  instant it used, so a dry run and the append of the same minute agree.
* **What a reviewer should probe:** (1) the zero-width band reading of a mid-only values file (§5.1)
  — the alternative is a refusal, and the owner's note explicitly allows the quantile rule; (2)
  whether skipping administered-pricing intervals instead of emitting an `ap` row is the right
  reading of the brief's parenthetical (§5.2); (3) the hard-coded regional target table/column and
  the `+08:00` offset (§5.3, §5.4); (4) the strict "values cover the horizon exactly" rule; (5)
  whether `coverage.scored` counting hours (not five-minute intervals) matches the receipt's
  intended unit.
* **Not claimed:** no real receipt exists, no skill or impact claim is made, and the `ap` slice and
  a nodal outlook path are unexercised.

## 9. Unfinished items and the exact next action

* **The first real receipt** waits for billing month 2026-11 to settle: refresh
  `.local/price/lwap_final_hourly.csv` and `.local/price/digests.json`, then run §3's command (dry
  run first). Nothing else is needed; the outlooks are issued and the command is built.
* The command scores the regional series only; a nodal outlook is refused `SERIES_UNSUPPORTED`
  until a later task extends the input. The `ap` slice is unexercised for the same reason.
* Exact next action: the independent review of this packet under `docs/work/reviews/SCORE-1.md`
  (reviewer only; not self-assigned), then, on accept, the merge of `task/SCORE-1` and the
  2026-11 scoring run when the month settles.
