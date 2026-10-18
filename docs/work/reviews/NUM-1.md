# Task NUM-1 packet

Executor seat (DeepSeek V4.1 Flash) record for `task/NUM-1`, implement route, verified on commit
`e7c4165` against `feat/h1-api-persistence` (base `1af705c`). The independent reviewer's record
is appended below the executor sections; this heading block is the packet.
(Rebase note, Rework 1: `e7c4165` and the `1dd1a67` tip named below are pre-rebase siblings and
are not ancestors of the current branch — the branch was rebased onto `7534465` before the
interim review, whose reviewed tip was `eddc697`. The Rework 1 section below records the current
tip; the designated reviewer names the commit it actually reviews.)

## What changed

| File | Change |
|---|---|
| `src/adapters/bigquery/whatif.py` | New. Covariate path from the reviewed `ScenarioProposal` delta under the one civil-time rule, two `AI.FORECAST` statements rendered from validated literals, limit validation with typed errors, ordered-context history digest, result parser, pair difference, labels and the uncomputed fallback. |
| `src/adapters/bigquery/__init__.py` | New. Public names of the package. |
| `src/adapters/bigquery/README.md` | New. Contract summary, limits, error codes, the execution seam and what stays unverified against the engine. |
| `src/adapters/bigquery/fixtures/whatif_statements.json` | New. Golden fixture: the intent's boundary example, the two expected SQL texts, path, digests, labels and covariate basis. |
| `tests/test_whatif.py` | New. 34 offline tests: golden SQL, limits, delta field/window/time rules, context history, parser refusals, pair difference, labels, static no-credential check. |
| `docs/work/reviews/NUM-1.md` | This packet. |
| `docs/work/tasks.json`, `docs/work/PROGRESS.md` | State `in_progress` and the matching row/log entry, in the packet commit. |
| `docs/work/whatif/work.json` | Phase `implement`, next action updated. |

No frozen contract, acceptance text, test or `docs/work/whatif/intent.md` line was changed. The
proposal's own `consequences: "uncomputed"` is never overwritten: `run_pair` returns a
`PairResult` whose `proposal_consequences` is exactly that frozen value.

## Readings and decisions

- **Horizon is exactly W.** `build_covariate_path` requires the first future step `H0+1` to lie
  inside `valid_period` (`[start, end)`), counts the steps below `end` up to the requested `N`,
  and records `N_eff` plus `horizon_clipped`. The intent's boundary example (date-only
  2026-10-03…2026-10-05, `H0 = 2026-10-02T23:00:00`, `N = 72`) gives `N_eff = 48`, the step
  `2026-10-05T00:00:00` staying end-exclusive; only `N_eff` reaches SQL.
- **One line differs between the calls.** The context rows carry the constructed `L_new` in both
  statements; the future rows carry `L_old` in A and `L_new` in B. The test pins this
  structurally: exactly one line differs, it is the `assumed_available_capacity_mw` line inside
  `future_rows`, and target and past-covariate columns are `CAST(NULL AS …)` there.
- **Time rule.** Date-only bounds normalize to `T00:00:00`; a bound, anchor or hour carrying
  `Z`, an offset or a zone name is refused as `WHATIF_CONFIG_INVALID`; comparison happens in the
  stored civil space and `timezone_convention` is recorded as
  `assumed Asia/Manila, unverified (scripts/data/sql/02_intervals.sql:2-3)`.
- **history_digest** hashes the complete ordered context rows as supplied to the model —
  including the constructed covariate — plus `covariate_past_basis`, `series_id`, `H0`, `K`,
  requested `N`, `N_eff`, `timezone_convention`, `confidence_level` and the model literal. A
  changed constructed value or basis label changes it, and `compare_calls` then refuses with
  `WHATIF_HISTORY_MISMATCH`; the test fires exactly that case.
- **`path_digest`** covers window, `N`, `N_eff`, clipping, series, relation and the call's level,
  so two identical paths (for example `old_value == new_value`) are refused as
  `WHATIF_RESULT_INCOMPATIBLE` — nothing to compare — instead of reporting a zero difference.
- **Injected transport.** `run_pair(path, transport, observed_rows, execution_mode=…)` calls
  `transport(statement)` once per statement and parses the `bq query --format=json` rows (a list
  of objects or its JSON text). The module imports only stdlib and `src.contracts.jsonutil`;
  a static test over the module source pins the absence of `os`, `socket`, `subprocess`,
  `urllib`, `requests`, `google.cloud` and environment lookups.
- **Unverified by construction** (recorded in the README and the intent, resolved by S3 against
  the engine, not invented here): the exact target STRUCT column name in the AI.FORECAST result
  and the call's keyword spelling exceptions. NUM-1 requires the intent's shape — target struct
  under `price_php_mwh` with `value`, the two prediction-interval bounds and an empty
  `ai_forecast_status` — and refuses anything else with a reason rather than guessing.

## Acceptance

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met | `GoldenStatementTests.test_golden_sql_matches_the_fixture`: both statements byte-identical to `fixtures/whatif_statements.json`; the fixture's path, statement digests, path digests, covariate basis and labels are re-derived and compared (`test_golden_path_digests_and_labels_match_the_fixture`), and rendering is deterministic (`test_rendered_statements_are_deterministic`). |
| Limit violations raise typed errors | met | `LimitTests`: horizon 0, -1, 1025, 2048, 64.0, `'64'`, `True`, `None` → `WHATIF_HORIZON_RANGE` at `$.horizon`; context window 0, 32, 63, 65, 97, 2080, 2112, `'64'`, `True`, `None` → `WHATIF_CONTEXT_WINDOW` at `$.context_window`; 1 and 1024, 64/96/2048 accepted. `DeltaTests`: wrong field/kind/unit → `WHATIF_DELTA_FIELD`; offset- or zone-carrying bound/anchor → `WHATIF_CONFIG_INVALID`; `W` not beginning at `H0+1` → `WHATIF_DELTA_WINDOW`. Every error carries code, field path and rule. |
| Incompatible result refused with reason | met | `ParserTests.test_incompatible_results_are_refused_with_a_reason` (10 mutations: short row list, nonempty `ai_forecast_status`, off-grid minute, whole grid shifted one hour, unordered bounds, missing struct field, wrong model literal, wrong series id, duplicate hour, non-numeric value) → `WHATIF_RESULT_INCOMPATIBLE` with a nonempty rule and a field path; `PairTests.test_a_history_mismatch_is_refused` → `WHATIF_HISTORY_MISMATCH`; `test_two_identical_paths_are_refused` → `WHATIF_RESULT_INCOMPATIBLE`. |

Brief outputs: two statements over one identical history with NULL-target future rows
(`test_target_and_past_covariate_are_null_on_future_rows`,
`test_context_rows_carry_the_constructed_accepted_level_in_both_calls`); horizon ≤ 1024 and
context multiple of 32 ≤ 2048 validated (`LimitTests`); parser to per-step difference with
Preview and directional labels (`PairTests.test_pair_difference_aggregates_and_labels`,
`labels()` refuses an unlabelled or contradictory result); injected transport, no credentials
(`test_run_pair_rejects_a_missing_transport`, the static source check).

## Verification log (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 34 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 295 tests` / `OK`; the same discovery filtered to exclude this task's module reports `261 tests` / `OK`, so the branch baseline is unchanged and the 34 new tests all pass |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 252 Markdown files, 1091 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

Run on commit `e7c4165` plus this packet; the targeted and full-suite runs were repeated after
the fixture was regenerated and the digest test was fixed. The Markdown/link counts above are the
final ones, measured with this packet and the PROGRESS entry in place; the run before this packet
existed reported 251 files and 1089 links, exactly the difference this packet and its two links
make. No model, cloud, network or credential was used anywhere: every result above is a local
offline run. Branch tip at hand-off: `1dd1a67` (this packet commit); the only commit after it adds
this line, and re-running the four commands above on it gave the same results.

## Limits, stop conditions and unfinished items

No stop condition fired. Nothing was weakened, skipped or deleted to pass; no test outside this
task's allowed paths was touched. Not done here and deliberately left to their tasks: the series
table and dry-run (NUM-2, behind GATE-3), the two real calls, receipts, the synthetic
counterfactual check and the result fixture for UI-3 (NUM-3, behind GATE-3). The engine-side
shape assumptions above stay unverified until S3 and are recorded, not asserted as fact.

**Exact next action:** independent review of `task/NUM-1` at `e7c4165` (reviewer appends the
record below; `done` is only set by that review under `docs/work/reviews/NUM-1.md`). After
accept: NUM-2 when GATE-3 opens, then NUM-3.

### Self-review (executor, not independent)

Read the brief's acceptance items one by one against the tests above, and the intent's SQL
contract, limits, typed-error, parser, label and receipt sections line by line against the code.
Every number in this packet was measured in this session by the commands recorded; the golden
fixture's boundary values (`N_eff = 48`, `N = 72` clipped, date-only 2026-10-03…2026-10-05,
`H0 = 2026-10-02T23:00:00`) come from the intent's own boundary example, and its series id,
relation and covariate levels are labelled synthetic placeholders, not case facts. Nothing was
invented and no frozen contract or acceptance text was touched. Known weaknesses recorded rather
than hidden: the AI.FORECAST keyword spelling and the result STRUCT name are unverified against
the engine (S3); `mean_delta_w` is the mean of the per-step `Δvalue` over the horizon (which is
W) and is named as the intent names it. This is self-review, not an independent review. State is
`in_progress` pending review.

## Interim review (orchestrator seat, Fable, commit eddc697, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated
re-review is required before `done`. Reviewed `task/NUM-1` at `eddc697` (log `4aa714f`,
`3f88236`, `eddc697`; merge-base `7534465` with `feat/h1-api-persistence`, whose tip is
`2ec4197`) against the brief, `docs/work/whatif/intent.md` and the executor packet above. The
reviewer did not author the change and edited no file but this section. Offline only: no
BigQuery, cloud, model or network command was run.

### Checklist

| # | Item | Answer | Evidence |
|---|---|---|---|
| 1 | Every acceptance item met by an observable check that was run | yes | Verify `/usr/bin/python3 -m unittest tests.test_whatif -v`: `Ran 34 tests` / `OK`. Golden SQL: `test_golden_sql_matches_the_fixture`; the rendered statement A was also diffed by the reviewer against the intent's SQL template with slots substituted (`difflib.unified_diff`) → identical. Typed limits: `LimitTests` (horizon 0/-1/1025/2048/64.0/`'64'`/`True`/`None`; context 0/32/63/65/97/2080/2112/`'64'`/`True`/`None`). Incompatible result: `ParserTests.test_incompatible_results_are_refused_with_a_reason` (10 mutations, each asserting code, nonempty rule and `$.` field path). |
| 2 | No file outside allowed paths | yes | `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` → `OK: all changed files inside NUM-1 allowed paths`; `git diff --stat feat/h1-api-persistence...HEAD` lists only the nine allowed files. |
| 3 | No frozen contract, acceptance text or test changed/weakened | yes | Diff touches no `src/review/records.py`, `src/judgment/`, probe-bundle intent or working paper; `tasks.json` change is the `state` line only; `tests/test_whatif.py` is new, no existing test modified; suite grew 261 → 295 with 34 new. |
| 4 | No new dependency, service, credential, network, model or cloud effect | yes | `whatif.py` imports stdlib + `src.contracts.jsonutil` only (lines 20-29); `test_no_credential_client_or_network_import_in_the_module` pins the absence of `os`, `socket`, `subprocess`, `urllib`, `requests`, `google.cloud`, `getenv`; execution is the injected `transport` callable (`run_pair`, line 706). |
| 5 | Mode labels truthful | yes | `labels()` (line 459) refuses any `execution_mode` outside the four working-paper modes; fixture and tests use `synthetic fixture`; the fixture's relation `synthetic-project.whatif.price_hourly_fixture` and levels are labelled synthetic placeholders. |
| 6 | Unknowns stayed unknown; no invented facts/numbers | yes, with one gap (finding 1) | Parser refuses fewer/extra/duplicate/off-grid rows (`parse_forecast_rows` lines 573-613) so no step is ever filled; aggregates are computed only over a complete pair; `uncomputed()` returns reason + labels and no number; identical paths refused rather than reporting a zero delta. `mean_delta_w` is the arithmetic mean the intent itself specifies (intent line 231); no other average is used anywhere. Gap: `available_at`/`availability_basis` are validated for shape then dropped, so "unknown" availability does not reach the result (finding 1). |
| 7 | Packet records interpreter, commands, results, unfinished items, next action | partially | Interpreter (`/usr/bin/python3` = 3.14.4), five commands, results, unfinished items (NUM-2/NUM-3, engine-shape unknowns) and next action are present. But the packet and PROGRESS log name commits `e7c4165` and `1dd1a67`, which are pre-rebase siblings, not ancestors of the reviewed branch (`git merge-base --is-ancestor` rc=1 for both; `git diff --stat e7c4165 4aa714f` differs only in `scripts/seats/verify.sh` from the new base). The reviewed tip is `eddc697` (finding 4). |
| 8 | Nothing contradicts blueprint, strategy, working paper or invariants | yes | Model literal `'TimesFM 3.0'` only via `AI.FORECAST`; proposal's frozen `consequences: "uncomputed"` is re-verified on input (line 212) and carried unchanged as `PairResult.proposal_consequences`; `timezone_convention` and `covariate_past_basis` are the intent's exact strings (`test_contract_constants_are_the_frozen_ones`). |

### Verification run by the reviewer (worktree `.local/wt/NUM-1`, `/usr/bin/python3`)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` | `Ran 34 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 295 tests` / `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 252 Markdown files, 1091 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

### Adversarial cases run by the reviewer (scratch script, not committed; re-runnable from the test helpers)

Using `tests/test_whatif.py` helpers (`path_for()`, `observed()`, `hour_text()`, `result_rows()`):

| Case | Input | Outcome |
|---|---|---|
| Future leakage 1 | 64 rows shifted forward one hour so the last row is `H0+1` with price 9999 | refused `WHATIF_HISTORY at $.context_rows[0].hour_start: contiguous hourly context ending at H0; expected 2026-09-30T08:00:00` |
| Future leakage 2 | the 64 valid rows plus one extra row at `H0+1` | refused `WHATIF_HISTORY at $.context_rows: the context window is the latest run of 64 consecutive non-NULL hours ending at H0` |
| Future leakage 3 | row 30 replaced by an hour at `H0+5` | refused `WHATIF_HISTORY at $.context_rows[30].hour_start` |
| Known-after-cutoff | all 64 rows with `available_at = H0+3`, `availability_basis = 'published later'` | **accepted**; no refusal, no record (finding 1) |
| Engine rows with `+08:00` offset | `result_rows(stamp='{hour}+08:00')` | refused `WHATIF_RESULT_INCOMPATIBLE at $.rows[0].forecast_timestamp` |
| Non-whole-hour anchor | `anchor='2026-10-02T23:30:00'` | accepted by `build_covariate_path`; SQL renders a `:30` grid (finding 3) |
| Negative level | `old='-5'` | accepted (`prior_mw='-5'`); intent only requires a finite decimal (question, not a finding) |
| SQL template | intent SQL block with slots substituted vs rendered statement A | identical |

The leakage cases confirm the builder excludes any observation after `H0` by refusing the whole
context rather than dropping rows silently; the test suite itself has no case with an hour later
than `H0` inside the list (finding 5).

### Findings

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| important | `src/adapters/bigquery/whatif.py:421-426` (`context_rows`) | A series row whose `available_at` is later than `H0` — information the estate records as known only after the cutoff — passes validation and enters the model history unflagged; `available_at`/`availability_basis` are then discarded, so neither `CovariatePath`, `CallResult` nor `PairResult` can carry the intent's per-call receipt field `availability_basis` (intent lines 143-146, 262) and an "unknown" basis never reaches the result. | Adversarial "known-after-cutoff" case above accepted; `history_digest` rows (line 452) contain no availability field; `CallResult.as_dict` (line 531) has no availability key. | Refuse `available_at > H0` as `WHATIF_HISTORY` at `$.context_rows[i].available_at` ("known at or before the cutoff"); summarise `availability_basis` on the path or call result (e.g. `availability_basis: "unknown"` when any row is unknown) so NUM-3 can copy it into the receipt; add both as table-driven cases. If the executor reads the intent as assigning this to NUM-3, say so in the packet with the intent line — do not leave it implicit. |
| minor | `src/adapters/bigquery/whatif.py:381-394` (`context_rows`) | The intent's contiguity rule says that when the context crosses a gap "the builder walks the anchor back and reduces K to the largest multiple of 32 that fits, recording the choice (`WHATIF_HISTORY` when none does)" (intent lines 147-150). NUM-1 only refuses; no walk-back or recorded K reduction exists. Refusal is the intent's safe fallback, so this is not a contradiction, but the receipt field `series_ref.gaps excluded and why` has no source. | `len(observed) != path.context_window` → `WHATIF_HISTORY` (line 392); no code path changes `h0` or `context_window`. | Either implement the walk-back with the recorded reduced K and gap reason, or state in the packet/README that NUM-1 refuses and NUM-3 chooses the anchor; raise the ambiguity ("the builder" = path builder or series builder?) as a FEEDBACK.md note for the guardian. |
| minor | `src/adapters/bigquery/whatif.py:241` (`build_covariate_path`) | A non-whole-hour anchor (`23:30:00`) is accepted; `render_statements` then emits a `GENERATE_TIMESTAMP_ARRAY` grid at `:30` and a context window misaligned with the hourly series. `run_pair` fails later at `context_rows`, but a direct `render_statements` caller gets runnable SQL on the wrong grid. | Adversarial case: `path_for(anchor='2026-10-02T23:30:00')` returns `h0='2026-10-02T23:30:00'`, `horizon_effective=48`. | Refuse minutes/seconds ≠ 0 with `WHATIF_CONFIG_INVALID` at `$.anchor` ("the last complete context hour"); add to `DeltaTests`. |
| minor | `docs/work/reviews/NUM-1.md:3-4,84-90`; `docs/work/PROGRESS.md` log row 2026-10-12 executor | Packet and log name commits `e7c4165` (verified) and `1dd1a67` (tip) that are not ancestors of the reviewed branch after the rebase onto `7534465`; a reader cannot check out the stated commit from `task/NUM-1`. | `git merge-base --is-ancestor e7c4165 HEAD` rc=1; same for `1dd1a67`; branch log is `4aa714f`, `3f88236`, `eddc697`. | On the next packet edit, record the rebased tip (`eddc697` or later) and note the rebase; the designated reviewer names the commit actually reviewed. |
| minor | `tests/test_whatif.py:308-321` | The history-error table has short, gapped, duplicate, NULL, foreign-region, unknown-column and space-separated cases but none where an hour later than `H0` is present in the list, so the no-future-leakage property is only indirectly covered. | Reviewer's leakage cases 1-3 above all refuse; none is in the suite. | Add the three leakage inputs as rows in the `cases` table (expected `WHATIF_HISTORY`). |
| minor | `src/adapters/bigquery/whatif.py:113-124, 581` | `_hour` strips a trailing `Z`/` UTC` from engine timestamps while the input rule refuses them; this is consistent only under the assumption that BigQuery reads the zone-less `TIMESTAMP '<H0>'` literal as UTC and echoes UTC text, so no conversion occurs. The model check fires only when a `model` key is present in the row. Both are engine-shape assumptions. | `_hour` line 119; `'model' in row and …` line 581. | Add both to the README's "not yet verified against the engine" list so NUM-3 confirms them against the recorded result shape. |

Questions (no evidence of harm): is a negative `assumed_available_capacity_mw` ever meaningful,
or should the builder refuse `< 0` as `WHATIF_DELTA_FIELD`? The intent says only "finite decimal".

Not applicable to NUM-1: bytes/cost limits — the scan is bounded by the `WHERE hour_start >
TIMESTAMP_SUB(... INTERVAL K HOUR) AND hour_start <= H0` clause over K ≤ 2,048 hours and `N_eff`
generated rows; `--maximum_bytes_billed` belongs to NUM-3's execution packet (intent line 315).
Identifiers: no user text reaches SQL unvalidated — series id `^[A-Z][A-Z0-9_]{0,15}$`, relation
`^[a-z][a-z0-9-]{4,62}(\.[A-Za-z_][A-Za-z0-9_]*){2}$` (no backtick possible), decimal
`^[+-]?\d+(\.\d+)?$`, civil timestamps `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$`; the intent
specifies validated literals, not query parameters, and the rendering matches it byte for byte.

### Outcome and next action

Brief acceptance is met and verified. One important intent-level gap (known-after-cutoff rows and
the dropped `availability_basis`) plus five minor items. Executor fixes on `task/NUM-1`, re-runs
the verify and full suite, updates the packet with the rebased tip, and re-requests review; the
designated independent reviewer then decides `done`. This verdict implies no external approval,
publication or deployment.

**Interim verdict: rework.** One important finding: `context_rows` accepts a row whose
`available_at` is after `H0` and drops `availability_basis`, so late-known data can enter the model
history unflagged and the intent's availability receipt field has no source.

## Rework 1 (executor, 2026-10-12, after the interim review)

Rework of the interim review's findings on `task/NUM-1`, alone on this branch. The branch was
rebased onto the current `feat/h1-api-persistence` tip before the review, so the commits the
first sections of this packet name (verified `e7c4165`, tip `1dd1a67`) are pre-rebase siblings,
not ancestors of `task/NUM-1`; the rebased log is `4aa714f`, `3f88236`, `eddc697` and this rework
commit, whose parent is the reviewed tip `eddc697`. The header block carries the same note.

**Finding 1 (important) — late-known rows and the dropped availability receipt field — fixed in
`src/adapters/bigquery/whatif.py`:**

- `context_rows` (through the shared validator `_series_rows`) now refuses `available_at > H0` as
  `WHATIF_HISTORY` at `$.context_rows[i].available_at`, rule "known at or before the cutoff H0; a
  row known only later cannot inform the model history", instead of admitting the row unflagged.
  A row available exactly at `H0` is accepted (a boundary case in the tests).
- The availability pair is no longer discarded. The new `availability_summary(observed, path)`
  returns `{'availability_basis': …, 'known_rows': n, 'unknown_rows': m}` over the same validated
  rows: any row whose availability is unknown makes the summary `unknown` — the intent's receipt
  value when the estate records no real first-availability time (intent lines 143-146, 262) —
  else the recorded bases are summarised as their sorted distinct labels joined by `'; '` (a
  summary of recorded labels, never a fabricated single basis).
- `run_pair` computes the summary once from the same rows as the history digest and passes it to
  `parse_forecast_rows(..., availability_basis=…)`; `CallResult` now carries `availability_basis`
  and `as_dict` exposes it, so NUM-3 can copy it into the receipt. A direct parser caller defaults
  to `unknown`, because an unvalidated series cannot claim a known-then input. `compare_calls` also
  refuses two calls whose summaries differ (`WHATIF_RESULT_INCOMPATIBLE` at
  `$.calls[].availability_basis`), so the pair cannot silently compare two different availabilities.
- A refused history still stops before the transport is called: the new test asserts the injected
  transport recorded zero calls on the late-known input.

**Finding 2 (minor) — the contiguity walk-back — recorded, not implemented.** NUM-1 refuses a
short or gapped context with `WHATIF_HISTORY` and never changes `H0` or `K`; the intent's walk-back
needs the observed series, which `build_covariate_path` does not take, and the reviewer allowed
recording instead of implementing. The README now says so and points at NUM-3 selecting the anchor
and `K` for a gapped series (or recording the fallback). The ambiguity the reviewer surfaced — "the
builder" in the intent's series contract means the series builder or the path builder — is a
guardian question; `docs/work/FEEDBACK.md` is outside this task's allowed paths, so it is recorded
here and in the PROGRESS log row for the orchestrator to raise rather than edited there.

**Finding 3 (minor) — the non-whole-hour anchor — fixed.** `build_covariate_path` refuses a minute
or second ≠ 0 as `WHATIF_CONFIG_INVALID` at `$.anchor` ("the last complete context hour: minute and
second are zero"), and `_check_path` applies the same rule to `$.h0`, so a hand-built `CovariatePath`
cannot render the runnable `:30` grid the reviewer obtained from a direct `render_statements`
caller. Date-only anchors still normalize to civil `T00:00:00` (checked).

**Finding 4 (minor) — the packet named pre-rebase commits — fixed** by the header note above and
the commit records in this section and the PROGRESS log row.

**Finding 5 (minor) — the missing future-leakage cases — fixed.** The `cases` table in
`test_short_gapped_null_or_unknown_series_rows_are_history_errors` now carries the reviewer's three
leakage inputs (every row shifted an hour so the last is `H0+1`; the valid run plus one extra row
at `H0+1`; one row replaced by an hour after `H0`), plus the all-rows-known-after-the-cutoff input;
the late case additionally gets a dedicated test pinning code, field path and rule.

**Finding 6 (minor) — the unverified engine shapes — fixed in the README,** whose "not yet
verified against the engine" list now also names the `_hour` trailing `Z`/` UTC` stripping
assumption (the zone-less `TIMESTAMP` literal echoed as UTC text) and the conditional `'model' in
row` check, for NUM-3 to confirm against the recorded result shape.

**Question (negative level), answered without a code change.** The intent's limit table says only
"finite decimal, MW" for `assumed_available_capacity_mw`, so a negative literal is accepted; no
sign rule was invented here and no test asserts one. Whether `< 0` should be refused as
`WHATIF_DELTA_FIELD` stays a guardian question with the intent's own text, recorded, not decided.

No frozen contract, acceptance text, test or `docs/work/whatif/intent.md` line was changed, and no
existing test was weakened; the module's suite grew 34 → 43. Files this rework touched:
`src/adapters/bigquery/whatif.py`, `src/adapters/bigquery/__init__.py`,
`src/adapters/bigquery/README.md`, `tests/test_whatif.py`, this packet, `docs/work/PROGRESS.md` and
`docs/work/whatif/work.json`. The golden fixture was not edited: the rework changes no rendered
SQL, no path field and no digest, and `test_golden_sql_matches_the_fixture` still passes against it
unchanged.

### Acceptance re-check after the rework

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — same fixture, unedited. |
| Limit violations raise typed errors | met, extended | `LimitTests` unchanged; `DeltaTests` adds `test_the_anchor_must_be_the_last_complete_context_hour` (three `:30`/`:59` anchors → `WHATIF_CONFIG_INVALID` at `$.anchor`) and `test_a_hand_built_path_off_the_hour_is_refused_before_rendering` (`$.h0`). |
| Incompatible result refused with reason | met, extended | `ParserTests.test_incompatible_results_are_refused_with_a_reason` (10 mutations) unchanged; new `test_the_receipt_defaults_to_an_unknown_availability` (four invalid summary values → typed refusal) and `PairTests.test_a_pair_with_two_availability_summaries_is_refused`. |

Brief outputs re-checked: the two statements over one identical history with NULL-target future
rows are unchanged; horizon/context limits unchanged; the parser still yields the per-step
difference with Preview and directional labels; the transport stays injected, with no credential,
client, network or subprocess import (the static test still passes).

### Verification run for this rework (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 43 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 304 tests` / `OK` (295 before this rework; the 9 new tests are all in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 252 Markdown files, 1094 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

Adversarial inputs re-run against the fixed module (scratch script over the test helpers, not
committed): the reviewer's three leakage inputs refuse with the same `WHATIF_HISTORY` field paths
as reviewed; the known-after-cutoff input refuses at `$.context_rows[0].available_at`; an
`available_at` exactly at `H0` is accepted; `23:30:00` and `23:00:30` anchors refuse at `$.anchor`;
a date-only anchor still normalizes and builds.

**Tip record.** All five commands above were re-run on the committed branch after the rework
commit, giving the same results (`Ran 43 tests` / `OK`, `Ran 304 tests` / `OK`, `PASS`, `OK: 41
tasks, 7 gates`, scope `OK`). The rework commit is `2bad9c3`, parent `eddc697`; the Markdown
counts are the ones with this Rework section and the PROGRESS row in place, and applying the same
counting to the pre-rework tree (`23fe1bc`) gives 1092, so this rework's two new links (the
README's new `intent` link and the PROGRESS row's new `packet` link) account exactly for the
difference to 1094. The first-pass packet's recorded 1091 is one lower than that same count at
`23fe1bc`; this rework does not rewrite that record and offers no cause for it. Branch tip at
hand-off: `2bad9c3`, the rework commit; the commit that adds this paragraph follows it and
re-ran the five commands on it with the same results.

### Limits, stop conditions and unfinished items (rework)

No stop condition fired: every fix stayed inside the allowed paths, no frozen contract or
acceptance text needed changing, and no new dependency, service, credential or network call was
introduced (the module still imports stdlib plus `src.contracts.jsonutil` only). Deliberately left
open, with owners: the contiguity walk-back and the anchor/`K` choice (NUM-3, README now states
it), the two guardian questions (negative level; "the builder" in the intent's series contract —
for the orchestrator to raise in `docs/work/FEEDBACK.md`, which this task may not edit), and the
engine-shape assumptions (NUM-3). Nothing was weakened, skipped or deleted to pass.

**Exact next action:** re-request review of the rework commit (its SHA and the post-commit
verification numbers are in the tip-record commit that follows it); the designated independent
reviewer decides `done` under this file. After accept: NUM-2 when GATE-3 opens, then NUM-3.

## Designated review 1 (GPT Astra, independent, commit `3bf2bd9`, 2026-10-12)

> Independent review of `3bf2bd9f298a01e97023b503e0580ae98e4494f4`, using the requested diff and seven-commit log against `feat/h1-api-persistence`. No files edited; working tree remains clean.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | Golden SQL passes, but additional probes expose limit-validation bypasses and an untyped parser failure below. |
> | 2. Changes within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside NUM-1 allowed paths`. |
> | 3. Frozen contracts and acceptance unchanged; tests not weakened | **Yes** | Diff leaves contracts and acceptance text unchanged; tests are additive. |
> | 4. No unauthorized dependency or external effect | **Yes** | Adapter uses stdlib and existing JSON utilities; transport is injected. No cloud execution performed. |
> | 5. Mode labels truthful | **No** | `compare_calls` accepts synthetic/stored inputs and labels their pair `live inference`. |
> | 6. Unknowns preserved; no invented case evidence | **Yes** | Fixtures explicitly identify synthetic values; availability defaults to unknown; late-known rows are rejected. Engine assumptions remain documented as unverified. |
> | 7. Packet records verification and handoff | **Yes** | Packet records interpreter, commands, results, unfinished engine/contiguity questions and next action. Historical commit references predate the current rebase. |
> | 8. Consistent with intent and domain invariants | **No** | Renderer can forecast beyond the disputed window; pair labels can contradict their constituent calls. |
> 
> All findings below remain open.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/bigquery/whatif.py:329` | Public renderer incompletely revalidates constructed paths, allowing invalid horizons and forecasts outside W. | Executed `render_statements(replace(path_for(), ...))`: requested horizon `1025` accepted; effective horizon `1.5` rendered; effective horizon `72` rendered despite the fixture’s 48-hour W. | Validate both horizons as bounded integers; recompute/check effective horizon, clipping and last step against W before rendering. Add regression tests. |
> | important | `src/adapters/bigquery/whatif.py:765` | Pair execution mode is caller-controlled without checking constituent modes. | Parsed A as `synthetic fixture`, B as `stored run`; comparison with `execution_mode='live inference'` returned `compatible=True` and that live label. | Validate mode compatibility and derive or constrain the pair label from the calls; refuse contradictory labels with a typed reason. |
> | important | `src/adapters/bigquery/whatif.py:113` | Optional seconds match the timestamp regex, but `int(None)` raises an uncaught `TypeError`. | Both anchor `2026-10-02T23:00` and forecast timestamp `2026-10-03T00:00 UTC` reproduced the exception. | Normalize absent seconds to zero, or reject this format through the appropriate typed error; test builder and parser paths. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_whatif -v` — **43 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` — **OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **304 tests, OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 42 tasks, 7 gates**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> - Additional in-memory probes reproduced all three findings.
> 
> **Verdict: rework** — unresolved validation and labeling defects violate the intended contract despite the passing existing suite.
**Verdict: rework.** validation and labelling defects against the what-if intent remain despite the passing suite. Address every blocking/important row above; dispose of minors explicitly.

## Rework 2 (executor, 2026-10-12, after the designated review)

Rework of the three important rows of the designated review above, alone on this branch, parent
`a99e35c` (the designated-review commit; the reviewed tip is `3bf2bd9`, the merge-base with
`feat/h1-api-persistence` is `36e2117`, whose tip is `f2ea7f7`). Each finding was reproduced first
against the reviewed module — an in-memory probe script under `/tmp`, not committed — and the
same probe was re-run after the fix; the outcomes are recorded per finding below. No frozen
contract, acceptance text, `docs/work/whatif/intent.md` line or test was changed or weakened, and
the golden fixture was not edited (this rework changes no rendered SQL, no path field and no
digest; `test_golden_sql_matches_the_fixture` still passes against it unchanged).

**Finding 1 (important, `render_statements` incompletely revalidates) — fixed in
`src/adapters/bigquery/whatif.py`, `_check_path`.** The revalidation now rebuilds what
`build_covariate_path` enforces instead of checking only `N_eff`:

- `horizon_requested` and `horizon_effective` are both bounded integers
  (`WHATIF_HORIZON_RANGE` at `$.horizon_requested` / `$.horizon_effective`).
- `horizon_clipped` must be a bool **and** equal `N_eff < N` (`WHATIF_CONFIG_INVALID` at
  `$.horizon_clipped`) — the flag is a result of the clipping, not a caller's claim.
- `W` is re-read as the horizon: the first step must lie inside `W` (`WHATIF_DELTA_WINDOW` at
  `$.window`), `N_eff` is recomputed as the number of requested steps inside `W`
  (`WHATIF_DELTA_WINDOW` at `$.horizon_effective`, so a horizon reaching past `W`'s last step can
  never render), and `window_last_step` must equal `H0 + N_eff` (`WHATIF_CONFIG_INVALID` at
  `$.window_last_step`).
- `path_digest` revalidates the path too, so an inconsistent path is refused rather than digested;
  `series_id`/`series_relation` are type-guarded before their pattern match.

Reviewer's probes, re-run: `horizon_requested = 1025` → `WHATIF_HORIZON_RANGE` at
`$.horizon_requested`; `horizon_effective = 1.5` → `WHATIF_HORIZON_RANGE` at `$.horizon_effective`;
`horizon_effective = 72` over the fixture's 48-hour `W` → refused (at `$.horizon_clipped` when the
flag is left inconsistent, at `$.horizon_effective` when it is set consistently); a valid path
still renders. Tests: `DeltaTests.test_a_hand_built_path_is_fully_revalidated_before_rendering`
(12 broken paths × the three public readers `render_statements`, `covariate_basis`, `path_digest`,
each asserting code, field path and rule);
`test_a_hand_built_path_off_the_hour_is_refused_before_rendering` now covers `path_digest` too.

**Finding 2 (important, caller-controlled pair label) — fixed in `compare_calls`.** Each call's
own `labels.execution_mode` is read and validated, the two calls must carry the same one, and the
`execution_mode` argument must equal it; a contradiction is `WHATIF_RESULT_INCOMPATIBLE` at
`$.calls[].labels.execution_mode` ("the two calls must be one execution…" / "the pair label is the
calls' execution mode … never relabelled"). A call whose `steps` do not cover its `horizon_effective`
is refused at `$.calls[].steps`, so a truncated step list can no longer be silently zip-truncated
into a short difference. Reviewer's probe, re-run: A parsed as `synthetic fixture`, B as
`stored run`, compared with `execution_mode='live inference'` → refused at
`$.calls[].labels.execution_mode`; two calls of one mode still produce a pair labelled with that
mode. Tests: `PairTests.test_a_pair_label_cannot_contradict_its_calls`,
`test_a_call_with_a_mismatched_step_count_is_refused`.

**Finding 3 (important, untyped `TypeError`) — fixed in `_civil`.** The seconds group of the civil
form is optional; an omitted one is zero (`parts = [int(part or 0) …]`, `datetime(*parts)`), so a
seconds-less timestamp is normalized instead of reaching `int(None)`. Reviewer's probes, re-run:
anchor `2026-10-02T23:00` builds `h0 = 2026-10-02T23:00:00` and renders; forecast timestamp
`2026-10-03T00:00 UTC`, the same without the suffix, and a `Z` variant all parse onto the requested
grid; seconds-less context hours build too. Impossible or malformed values (`:99`, hour `24`,
`…T23:00:00.5`, `…T23`) are now typed refusals, not exceptions. Tests:
`DeltaTests.test_the_civil_seconds_field_is_optional_and_impossible_times_are_refused`,
`ParserTests.test_a_seconds_less_forecast_timestamp_parses_on_the_grid`, plus the
`impossible_timestamp` and `missing_timestamp` rows in
`ParserTests.test_incompatible_results_are_refused_with_a_reason` (now 12 mutations).

**Hardening recorded, not a review finding (same defect family, cheap).** `parse_forecast_rows`
now refuses a `history_digest_value` that is not a lowercase 64-hex digest
(`WHATIF_CONFIG_INVALID` at `$.history_digest`) — two calls carrying the same unvalidated value
could otherwise pass the `WHATIF_HISTORY_MISMATCH` check — and type-guards `statement.sql` before
`.strip()`. Tests: `ParserTests.test_the_history_digest_argument_must_be_a_digest` (four values).

**Disposition of the open minors.** The interim review's five minors were disposed in Rework 1
(leakage rows, whole-hour anchor, rebased-commit naming, `README` engine-shape assumptions); the
contiguity walk-back stays NUM-1-refuses / NUM-3-chooses, and the two guardian questions (negative
level; "the builder" in the series contract) stay recorded, not decided — `docs/work/FEEDBACK.md`
is outside this task's allowed paths. The designated review's checklist rows 5 and 8 (mode labels,
consistency with the intent) are disposed by findings 2 and 1 respectively. No new dependency,
service, credential, network call or engine assumption was introduced: the module still imports
stdlib plus `src.contracts.jsonutil` only, and the static no-credential test still passes.

### Acceptance re-check after Rework 2

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — same fixture, unedited (this rework changes no rendered SQL). |
| Limit violations raise typed errors | met, extended | `LimitTests` unchanged; `DeltaTests` now also refuses hand-built horizon, clipping, window and literal violations with code, field path and rule (`test_a_hand_built_path_is_fully_revalidated_before_rendering`), and a malformed or impossible civil time is typed (`test_the_civil_seconds_field_is_optional_and_impossible_times_are_refused`). |
| Incompatible result refused with reason | met, extended | `ParserTests.test_incompatible_results_are_refused_with_a_reason` (12 mutations) and `ParserTests.test_a_seconds_less_forecast_timestamp_parses_on_the_grid` unchanged rows still refuse typed; new `test_the_history_digest_argument_must_be_a_digest`, `PairTests.test_a_pair_label_cannot_contradict_its_calls`, `test_a_call_with_a_mismatched_step_count_is_refused`. |

Brief outputs re-checked, unchanged: two `AI.FORECAST` statements over one identical history with
NULL-target future rows; horizon ≤ 1,024 and context a multiple of 32 ≤ 2,048 validated before
rendering; the parser still yields the per-step difference with Preview and directional labels;
execution stays an injected transport with no credential, client, network or subprocess import.

### Verification run for Rework 2 (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 49 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 310 tests` / `OK` (304 before this rework; the 6 new tests are in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 258 Markdown files, 1157 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

The link count is the one measured with this section and the PROGRESS row in place; the same
command run earlier in this session, with the module, README and tests edited but before this
section and the row existed, reported `1156 local links`, and this section adds no link.

Files this rework touched: `src/adapters/bigquery/whatif.py`, `src/adapters/bigquery/README.md`,
`tests/test_whatif.py`, this packet, `docs/work/PROGRESS.md`. `docs/work/tasks.json` needed no
edit: NUM-1's `state` is already `in_progress` and no other key was touched. The module suite grew
43 → 49 and the full suite 304 → 310, so no existing test was weakened, skipped or deleted. The
Markdown counts above are the ones with this section and the PROGRESS row in place; they are not
comparable with Rework 1's 252/1094 because the branch has since merged the designated review
record and other lanes' commits at `36e2117`.

**Tip record.** All five commands above were re-run on the committed branch after the Rework 2
commit, giving the same results (`Ran 49 tests` / `OK`, `Ran 310 tests` / `OK`,
`Checked 258 Markdown files, 1157 local links, 8 skills; bootstrap 1293 words.` / `PASS`,
`OK: 42 tasks, 7 gates`, scope `OK`). The rework commit is `72ed208`, whose parent is the
designated-review commit `a99e35c`; `25e0aee` records those post-commit numbers and `c1aba40` adds
the self-review note above. The branch tip at hand-off is this commit, whose parent is `424ccbb`
(it also carries the `docs/work/whatif/work.json` `next_action` update); the five commands were
run once more on it with the same results. Working tree clean.

### Limits, stop conditions and unfinished items (Rework 2)

No stop condition fired: every fix stayed inside the allowed paths, no frozen contract or
acceptance text needed changing, no test was weakened, and no new dependency, service, credential,
network call, model call or cloud effect was introduced or needed. Deliberately left open, with
owners: the contiguity walk-back and the anchor/`K` choice for a gapped series (NUM-3; stated in
the README), the engine-shape assumptions — the target STRUCT name, the `AI.FORECAST` keyword
spelling, the `_hour` zone-text echo and the conditional `model` key check (NUM-3, README), and
the two guardian questions above (orchestrator, `docs/work/FEEDBACK.md`).

**Exact next action:** independent re-review of the Rework 2 commit `72ed208` (parent `a99e35c`;
the post-commit verification numbers are in the tip-record commit `25e0aee`); the designated
independent reviewer decides `done` under this file. After accept: NUM-2 when
GATE-3 opens, then NUM-3.

### Self-review (executor, not independent)

Each of the reviewer's three important findings was reproduced against the module as reviewed
(`git diff --stat 3bf2bd9 a99e35c` changes only `PROGRESS.md` and this packet, so the code under
probe is the reviewed code) with an in-memory probe run under `/tmp`, not committed, and the same
probe was re-run after each fix: the outcomes printed by that probe are the ones recorded per
finding above. The review's rows were re-read one by one: row 1 (acceptance items) — the three
acceptance items each have a test that was run on the committed tree; rows 2-4 (scope, frozen
contracts, no external effect) — `plan.py scope` prints OK, the diff touches no contract file and
the static no-credential test still passes; rows 5 and 8 — disposed by findings 2 and 1; rows 6
and 7 — no unknown was filled and a verifiable commit is named. Every number in this section was
measured in this session by the commands in its table; no case fact, receipt or engine result is
asserted. Known limit recorded rather than hidden: these fixes tighten the module's internal
consistency — a hand-built path, statement or call can no longer carry a value the builder would
not have produced — and they do not verify the engine's result shape, which stays NUM-3's against
a recorded engine response. This is self-review, not an independent review; state stays
`in_progress`.

## Rework 2 verification (second executor session after a duplicate launch, 2026-10-12)

Process record and independent check, not a second rework. Two `claude -p` sessions were started
from the same `scripts/seats/rework.sh NUM-1 --print` into this one worktree: the first (PID
310081) was already editing `whatif.py` and `tests/test_whatif.py` when this session (PID 311776)
read the review above, so this session wrote nothing while the first was alive, watched it finish
(`72ed208` and its five tip-record commits, last `9cf8cfd`), and then verified the committed state.
The rework itself is the Rework 2 section above; this section only records the second session's
commands and probes on the tip the first left. `git diff --stat a99e35c..9cf8cfd` lists only the
six allowed files, and `docs/work/tasks.json` is untouched (NUM-1 was already `in_progress`).

| Command (run by this session on `9cf8cfd` plus this record's two edits, `/usr/bin/python3` = Python 3.14.4) | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` | `Ran 49 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 310 tests` / `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 258 Markdown files, 1158 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

The link count is the one with this section and the PROGRESS row in place: at `9cf8cfd` alone the
same command reported 1157, and this record adds exactly its one PROGRESS `[packet]` link.

Independent probes (scratch scripts under `/tmp`, not committed, run against the committed
module): the reviewer's three probes now refuse typed — `horizon_requested = 1025` →
`WHATIF_HORIZON_RANGE` at `$.horizon_requested`; `horizon_effective = 1.5` →
`WHATIF_HORIZON_RANGE` at `$.horizon_effective`; `horizon_effective = 72` over the fixture's
48-hour `W` → `WHATIF_CONFIG_INVALID` at `$.horizon_clipped` (flag left `true`) or
`WHATIF_DELTA_WINDOW` at `$.horizon_effective` (flag set consistently). A tampered
`window_last_step` refuses at `$.window_last_step`, a `W` moved off `H0+1` refuses at `$.window`,
`path_digest` revalidates, and a valid path still renders with both statements and the path
matching the golden fixture byte for byte. A pair of a `synthetic fixture` call with a `stored
run` call, compared as `live inference`, refuses at `$.calls[].labels.execution_mode`, and two
calls of one mode still produce a pair labelled with that mode. Seconds-less civil text (anchor
`2026-10-02T23:00`, timestamp `2026-10-03T00:00 UTC`) normalizes instead of raising `TypeError`,
while impossible values (`23:00:99`, hour `24`) refuse typed. A junk-typed-field battery (22 bad
path fields × the five public readers, plus `history_digest_value`, `statement`, `rows`, `labels`
and `execution_mode` junk) produced 0 uncaught exceptions.

Acceptance re-checked on `9cf8cfd`: all three items hold — the golden fixture is unchanged and
matching, the 12-mutation incompatible-result table and the new typed hand-built-path rows pass,
and hand-built horizons, clipping, window and civil time refuse with code, field path and rule.
Stop conditions: none for the verified state; the only hazard was the duplicate launch itself,
recorded here and in the PROGRESS row (`docs/work/FEEDBACK.md` is outside this task's allowed
paths). This record commit adds this section and the PROGRESS row only: no code, test, fixture,
contract, acceptance text or `tasks.json` line is touched, and the re-review target below is
unchanged apart from this record sitting on top of it.

**Exact next action:** unchanged — designated independent re-review of the Rework 2 commit
`72ed208` (parent `a99e35c`), whose tree is the one verified above; this section's commit is the
only commit after `9cf8cfd`.

## Designated review 2 (GPT Astra, independent, commit `44858f9`, 2026-10-12)

> Independent review of `feat/h1-api-persistence...44858f9febb3`, including the commit log. No files edited.
> 
> All executed checks passed on Python 3.14.4:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_whatif -v` | 49 tests, OK |
> | `/usr/bin/python3 -m unittest discover -s tests` | 310 tests, OK |
> | `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | OK: all changed files inside allowed paths |
> | `/usr/bin/python3 scripts/plan.py check` | OK: 42 tasks, 7 gates |
> | `/usr/bin/python3 scripts/repo.py check` | PASS: 261 Markdown files, 1,184 local links, 8 skills |
> 
> The eight checklist answers:
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | Golden SQL and typed limit errors are demonstrated by the passing tests. Incompatible-result refusal remains incomplete: the independent probe below accepted statements belonging to another covariate path. |
> | 2. Changes within allowed paths | **Yes** | Requested scope command printed OK; nine changed files. |
> | 3. Frozen contracts, acceptance and tests preserved | **Yes** | Diff changes no frozen contract or acceptance text; adds the what-if test module without weakening existing tests. |
> | 4. No unauthorized dependency or external effect | **Yes** | Adapter uses standard library and existing JSON utilities; execution uses an injected callable. Tests use a local fake transport. |
> | 5. Truthful mode labels | **Yes** | Tests demonstrate refusal of mixed call modes and contradictory pair modes; Preview/directional labels remain present. No live execution was demonstrated or credited. |
> | 6. Unknowns preserved; no invented evidence | **Yes** | Availability defaults to unknown; late-known rows are refused; fixtures explicitly identify synthetic values. Engine assumptions remain documented as unverified. |
> | 7. Packet records verification and handoff | **Yes** | `docs/work/reviews/NUM-1.md` records interpreter, commands, results, outstanding questions and next action. Historical revision references require reading its rebase notes. |
> | 8. Consistent with intent and domain invariants | **No** | Statement/path mismatches can produce accepted comparisons, and numerically identical covariate paths evade the required refusal. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/bigquery/whatif.py:657` | Parser checks only that a statement contains nonempty SQL, then combines its metadata with an independently supplied path without checking their correspondence. | Built path levels `100/0`, supplied statements rendered for `200/50`, parsed both and compared them: returned `compatible=True`, with receipt levels `200/50`. | Verify statement call, role, level, SQL and path digest against the canonical statement rendered from the supplied path. Add a cross-path refusal test. |
> | important | `src/adapters/bigquery/whatif.py:398` | Path digests hash decimal spelling rather than the numerical covariate supplied to the model, so equivalent paths appear different. | `old='0', new='0.0'` passed `run_pair`; the existing fake transport yielded an accepted mean difference of `5.0`. Both SQL literals represent the same FLOAT64 value. | Compare canonical numerical paths and refuse equivalent model inputs; retain original decimal strings separately for provenance. Test equivalent spellings. |
> | minor | `src/adapters/bigquery/whatif.py:807` | Finite input forecasts can overflow during subtraction or aggregation, producing a computed result containing infinities. | Parsed forecasts at `1e308` and `-1e308` produced `delta_value=-inf`, `mean_delta_w=-inf`, and `max_abs_delta=inf`. | Check derived values for finiteness and return a typed refusal; use overflow-safe averaging where possible. |
> 
> **Verdict: rework.** The passing suite demonstrates substantial coverage, but statement/path compatibility and equivalent-path refusal remain important correctness gaps.
**Verdict: rework.** Close the statement/path compatibility gap and refuse equivalent paths, with regressions. Address every blocking/important row above; dispose of minors explicitly.

## Rework 3 (executor, 2026-10-12, after the designated review 2)

Rework of the designated review 2's two important rows and its one minor row, alone on this branch,
parent `dc45bdf` (the designated-review commit; the reviewed tip is `44858f9`, the merge-base with
`feat/h1-api-persistence` stays `36e2117`). Each finding was reproduced first against the module as
reviewed — the reviewed revision piped from `git show dc45bdf:src/adapters/bigquery/whatif.py` into
a probe under `/tmp` that executes that source as a module, so the probe ran the reviewed code, not
the worktree copy — and the same probe was re-run against the fixed worktree module; the outputs are
quoted per finding. A `/proc` scan before any write found only this session's own process tree in
this worktree (the `claude -p` process, its MCP helpers and its own subshells), so no duplicate-launch
yield applied at that point.

**Commit topology and a duplicate launch (recorded, 2026-10-12).** This session (PID 380971) did the
fix and the tests in the working tree and measured every number below on it; before it could commit,
a second `claude -p` rework session (PID 401216, started later from the same rework prompt) committed
the working tree's `src/adapters/bigquery/whatif.py`, `README.md`, `tests/test_whatif.py` and one
`docs/work/whatif/work.json` line as commit `5b8525d` under the message "seats: seat liveness check
by worktree cwd", whose content is this rework and whose message does not describe it. HEAD is
therefore `5b8525d`, parent `dc45bdf`, and `git diff dc45bdf 5b8525d` is exactly this rework's code
and test change (262 insertions, 16 deletions over those four files) — a reviewer should read it as
the Rework 3 change, not as a seats change. This session's record commit adds this packet section,
its `docs/work/PROGRESS.md` row and the file-count line of `docs/work/whatif/work.json`; it changes
no code, test, fixture, contract or acceptance text. Every command below was run on that same
content (working tree equal to `5b8525d` for `src/` and `tests/`), and the five commands were re-run
after this session's record commit with the same results (see the tip record).

No frozen contract, acceptance text, `docs/work/whatif/intent.md` line or reviewed test expectation
was changed or weakened, and the golden fixture was not edited: this rework changes no rendered SQL,
and the canonical-level change leaves the fixture's `100`/`0` level digests byte-identical, so
`test_golden_sql_matches_the_fixture` and `test_golden_path_digests_and_labels_match_the_fixture`
still pass against it unchanged.

**Finding 1 (important, `parse_forecast_rows` combined a statement with an unrelated path) — fixed
in `src/adapters/bigquery/whatif.py`.** The parser now verifies its statement against the supplied
path before it touches the rows: the call (`$.statement.call`), the role (`$.statement.role`), the
covariate level (`$.statement.level_mw`), the SQL text (`$.statement.sql`, re-rendered from this
path and call) and the path digest (`$.statement.path_digest`, recomputed) must equal the canonical
rendering of that path for that call. A mismatch is `WHATIF_CONFIG_INVALID` — the intent's code for
malformed records/params, because a statement is an input argument, not the engine result — and the
`CallResult` now carries the recomputed `path_digest`. The reviewer's probe, re-run: path levels
`100/0` with statements rendered for `200/50` refused at `$.statement.level_mw` (before:
`ACCEPTED -> 200`, and both parsed calls compared to `compatible=True` with receipt levels
`['200', '50']`); a statement of another path with the *same* levels but a moved anchor and window
refuses at `$.statement.sql`. Tests: `ParserTests.test_a_statement_of_another_path_is_refused`
(three statements) and `test_a_statement_is_verified_field_by_field_against_this_path` (seven broken
statements, each asserting code, field path and rule, plus both valid statements still parsing).

**Finding 2 (important, path digests hashed spelling rather than value) — fixed.** `path_digest`
digests the covariate level through the new `_canonical_level` (`Decimal.normalize()` plus
exponent-free formatting, zeros folded), so the digest describes the FLOAT64 value the model
receives; the reviewed spelling is kept for provenance in `prior_mw`/`accepted_mw`, in the statement
text, in `delta_refs` and in each call receipt's `level_mw`. `compare_calls` adds a second check on
the numerical levels themselves, so a hand-built call carrying stale digests still cannot pass one
number off as two paths. The reviewer's probe, re-run: `old='0', new='0.0'` — before `ACCEPTED ->
{'n_steps': 48, 'mean_delta_w': 5.0, 'max_abs_delta': 5.0}` (the fake transport's artificial shift,
with both model inputs identical); after, the two path digests are equal and `run_pair` refuses
`WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].path_digest` ("the covariate levels are numerically equal,
so there is no difference to compare"). Tests:
`PairTests.test_equivalent_covariate_spellings_are_one_model_input_and_refused` (six spelling pairs:
`0`/`0.0`, `0`/`00`, `100`/`100.0`, `100`/`0100`, `5`/`+5.000`, `1.5`/`1.50`),
`test_the_reviewed_level_spelling_is_kept_for_provenance` (`100.50` / `+0.0` still render and record
their spellings, and numerically different levels still compare) and
`test_a_hand_built_pair_whose_levels_are_one_number_is_refused` (a stale-digest call, plus four junk
`level_mw` values).

**Finding 3 (minor, finite forecasts could be reported as infinities) — fixed.** Every derived
difference is read through the new `_finite_number` (a finite `int`/`float`, so a huge integer is
refused rather than converted blindly) and checked finite, refusing at
`$.difference[i].delta_value` / `.delta_lower` / `.delta_upper`; the mean is computed overflow-safe
— each difference is divided by the step count before summing — and checked finite at
`$.aggregates.mean_delta_w`. The reviewer's probes, re-run: `A=-1e308, B=1e308` — before
`{'n_steps': 48, 'mean_delta_w': inf, 'max_abs_delta': inf}`; after, refused at
`$.difference[0].delta_value`; the isolated `delta_lower` and `delta_upper` overflows (`±1.797e308`)
— before `inf` each, after refused at their own field paths; and 48 finite differences of `1e308`,
whose naive sum overflows — before `mean_delta_w: inf, max_abs_delta: 1e+308`, after
`mean_delta_w: 1e+308` (finite, so the pair stands with no infinity reported). Test:
`PairTests.test_an_overflowing_difference_is_refused_and_the_mean_never_overflows` (three field
paths plus the finite-mean case).

**Hardening recorded, not a review finding (same family, cheap).** A junk-typed-field battery over
the statement, call and step fields (159 cases) found seven uncaught `TypeError`s on the first fixed
version and none after two guards: a non-string `statement.call` (the new `CALL_ROLES` membership
would raise on an unhashable value) and a call whose `steps` is not a sequence (the existing
`len(call.steps)` check). Both now refuse typed at `$.statement.call` and `$.calls[].steps`, and a
pair of two all-empty calls is refused there too. Tests: the call-type and role-type rows in the
statement table above and `PairTests.test_a_hand_built_step_with_a_junk_value_or_no_steps_is_refused`
(junk step values, non-sequence `steps`, all-empty pair). Final battery: 159 cases, 0 uncaught
exceptions.

**Disposition of the minors.** The designated review 2's one minor (the overflow) is fixed above.
The earlier rounds' dispositions stand: the interim review's five minors were disposed in Rework 1
(leakage rows, whole-hour anchor, rebased-commit naming, the README engine-shape list, and the
contiguity walk-back left to NUM-3 with the README stating it), and the designated review 1's three
important rows were fixed in Rework 2 with their regression tests. The two guardian questions (a
negative `assumed_available_capacity`; "the builder" in the intent's series contract) remain
recorded, not decided, because `docs/work/FEEDBACK.md` is outside this task's allowed paths. The
engine-shape assumptions (target STRUCT name, keyword spelling, `_hour` zone-text echo, conditional
`model` key) stay NUM-3's against a recorded engine response, as the README says.

### Acceptance re-check after Rework 3

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — same fixture, unedited (this rework changes no rendered SQL). |
| Limit violations raise typed errors | met, extended | `LimitTests` unchanged; `ParserTests` now also refuses a statement that does not belong to this path (seven broken statements, each with code, field path and rule), and `PairTests` refuses a numerically equal level pair, a non-sequence or empty `steps` and an overflowing difference, each typed. |
| Incompatible result refused with reason | met, extended | `ParserTests.test_incompatible_results_are_refused_with_a_reason` (12 mutations) unchanged; new `test_a_statement_of_another_path_is_refused` and `test_a_statement_is_verified_field_by_field_against_this_path`; new `PairTests` rows for the equivalent-spelling table, the hand-built level/step cases and the overflow table. |

Brief outputs re-checked, unchanged: two `AI.FORECAST` statements over one identical history with
NULL-target future rows; horizon ≤ 1,024 and context a multiple of 32 ≤ 2,048 validated before
rendering; the parser still yields the per-step difference with Preview and directional labels;
execution stays an injected transport with no credential, client, network or subprocess import (the
static test still passes).

### Verification run for Rework 3 (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 56 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 317 tests` / `OK` (310 before this rework; the 7 new tests are in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1185 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

**Tip record.** All five commands above were re-run on the committed branch after this session's
record commit `829d790` (parent `5b8525d`; it stages this packet, the PROGRESS row and the
file-count line of `work.json` only), giving the same results — `Ran 56 tests` / `OK`,
`Ran 317 tests` / `OK`, `Checked 261 Markdown files, 1185 local links, 8 skills; bootstrap 1293
words.` / `PASS`, `OK: 42 tasks, 7 gates`, scope `OK` — with the working tree clean. The duplicate
rework session (PID 401216) was still live in this worktree when this paragraph was written: it had
committed `5b8525d` and made no further file change at that point (`git status` clean; the doc-file
mtimes were this session's own edits), so this section is the rework's account from the session that
authored the change, and any later section from that session is its own record.

Files this rework touched: `src/adapters/bigquery/whatif.py`, `src/adapters/bigquery/README.md`,
`tests/test_whatif.py`, this packet, `docs/work/PROGRESS.md` and `docs/work/whatif/work.json`.
`docs/work/tasks.json` needed no edit: NUM-1's `state` is already `in_progress` and no other key was
touched. The module suite grew 49 → 56 and the full suite 310 → 317; every line this rework adds to
the reviewed test module is new (new methods, new helper functions and new table rows — an
additive diff), so no reviewed test was weakened, skipped or deleted.

### Limits, stop conditions and unfinished items (Rework 3)

No stop condition fired: every fix stayed inside the allowed paths, no frozen contract or acceptance
text needed changing, no test was weakened, and no new dependency, service, credential, network
call, model call or cloud effect was introduced or needed (the module still imports stdlib plus
`src.contracts.jsonutil` only, and the static no-credential test still passes). Deliberately left
open, with owners: the contiguity walk-back and the anchor/`K` choice for a gapped series (NUM-3;
stated in the README), the engine-shape assumptions (NUM-3, README), and the two guardian questions
above (orchestrator, `docs/work/FEEDBACK.md`).

**Exact next action:** independent re-review of the Rework 3 change in `5b8525d` (parent `dc45bdf`;
this packet section, the PROGRESS row and the post-commit numbers are in this session's record
commit on top of it); the designated independent reviewer decides `done` under this file. After
accept: NUM-2 when GATE-3 opens, then NUM-3.

### Self-review (executor, not independent)

Each of the reviewer's three findings was reproduced against the code as reviewed and re-probed
after the fix with the same probe (commands and outputs above). The reviewer's rows were re-read one
by one: row 1 (acceptance) — each acceptance item has a test run on the committed tree; row 2
(scope) — `plan.py scope` prints OK; row 3 (frozen contracts, tests) — the diff touches no contract
file, the fixture and every reviewed test are untouched, and this module's tests are additive; row 4
(no external effect) — the static no-credential test still passes and no new import was added; row 5
(mode labels) — untouched by this rework, Rework 2's constraints and their tests still pass; rows 6
and 8 — no unknown was filled, the canonical level *is* the value the model receives while the
reviewed spelling is kept as provenance rather than discarded, and every numeric artifact that
cannot be represented is refused rather than reported; row 7 — the commit graph and the post-commit
numbers are recorded in the tip-record commit. Every number in this section was measured in this
session by the commands in its table or by the probes quoted; no case fact, receipt or engine result
is asserted. Known limits recorded rather than hidden: these fixes tighten what the module accepts
and reports and do not verify the engine's result shape (NUM-3, against a recorded engine response);
the `$.statement.*` code choice (`WHATIF_CONFIG_INVALID` for an input-argument mismatch rather than
`WHATIF_RESULT_INCOMPATIBLE`, which the intent reserves for the engine result of the wrong shape) is
stated above rather than left implicit. This is self-review, not an independent review; state stays
`in_progress`.

## Rework 3 verification (second executor session, after the duplicate launch, 2026-10-12)

**Process.** Two `claude -p` rework sessions ran from the same `scripts/seats/rework.sh NUM-1` prompt
in this one worktree: the session that authored the Rework 3 section above (PID 380971) and this one
(PID 401216, started later). A `/proc` scan at the start of this session found the other session live
in this worktree, so this session wrote no file while it lived: before the other session exited, the
commands this session ran were the `git status` / `git log` / `git diff` reads, the `/proc` scan and
two runs of the probe script quoted below. After the other session exited (tip `c5c614c`, on top of
its record commit `829d790` and the code commit `5b8525d`), this session verified that tip, added the
one hardening described below, and wrote this section, the PROGRESS row and the `work.json`
next-action line. This session issued no git write before that point.

**Attribution correction (recorded, not edited in the section above).** The Rework 3 section records
that "a second `claude -p` rework session (PID 401216 …) committed the working tree's … as commit
`5b8525d`". That attribution is wrong: this session never ran `git add`, `git commit` or any other
git write before the other session exited. The verifiable facts: `5b8525d` (committed 11:09:36
+0800, parent `dc45bdf`) carries exactly the other session's diff — `git diff dc45bdf 5b8525d` is
`src/adapters/bigquery/whatif.py`, `src/adapters/bigquery/README.md`, `tests/test_whatif.py` and one
`docs/work/whatif/work.json` line (262 insertions, 16 deletions); its message names a seats liveness
check; and no script under `scripts/seats/` contains that phrase. The commit was therefore created
by a process outside both rework sessions — the message points at the orchestrator's seat liveness
check, and the reflog shows `task/NUM-1` checked out in this worktree at 11:08:51, 45 seconds before
the commit. The hazard is real whatever its origin and is recorded here for the orchestrator
(`docs/work/FEEDBACK.md` is outside this task's allowed paths): an outside `git commit -a` in a live
seat's worktree captures that seat's uncommitted work, and this branch now has a commit whose message
does not describe it. Nothing was lost — the diff *is* the Rework 3 change and the later commits
carry the records — but a reader should take `git show --stat 5b8525d` as the Rework 3 change, not as
a seats change.

**Verification of the other session's tip `c5c614c` (all five commands, `/usr/bin/python3` = 3.14.4).**
Run by this session on the committed tree before its hardening, with the working tree clean:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 56 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 317 tests` / `OK` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1185 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

**Independent probes (`/usr/bin/python3 /tmp/num1-rework3-probe/probe.py`, a scratch script under
`/tmp` importing this task's test helpers, not committed).** Findings 1 and 3 re-checked as fixed: a
statement rendered for a path of levels `200/50` fed to the `100/0` path refuses
`WHATIF_CONFIG_INVALID` at `$.statement.level_mw`; a same-level statement from a moved window refuses
at `$.statement.sql`; hand-broken `call`, `role`, `sql` and `path_digest` each refuse at their own
`$.statement.*` field, and the canonical statement still parses 48 steps. `1e308` vs `-1e308`
forecasts refuse at `$.difference[0].delta_value`, an overflow confined to a prediction-interval
bound refuses at `$.difference[0].delta_lower`, 48 finite differences of `1e308` average
`mean_delta_w = 1e+308` (finite), and a non-finite row value refuses at
`$.rows[0].price_php_mwh.value`.

**One residual in finding 2, found by this session's probe and fixed here.** The Rework 3 fix
canonicalised the level with `Decimal` arithmetic, which unifies spellings but not different
decimals that land on one FLOAT64: the probe's `old='0.1', new='0.1000000000000000000000001'` pair
was still **admitted** (`compatible=True`, the fake transport's `mean_delta_w = 5.0`), the same
failure the review describes — "Path digests hash decimal spelling rather than the numerical
covariate supplied to the model … Both SQL literals represent the same FLOAT64 value" — for a
narrower spelling difference, since the statement's `CAST(… AS FLOAT64)` hands the model one number.
Fixed in `src/adapters/bigquery/whatif.py`: `_canonical_level` now returns the FLOAT64 value itself
(`format(float(number), '.17g')`, which names one FLOAT64 exactly) with zeros still folded to `0`,
and `compare_calls`'s second-line level check compares the same canonical text, so a hand-built call
cannot pass one FLOAT64 off as two paths either. Its rule text became "the two covariate levels are
one number; there is nothing to compare" and the reviewed assertion that pinned the old wording was
updated to `nothing to compare` — same refusal, code, field path and typed rule, no property
weakened. A decimal with no finite FLOAT64 value (beyond the type's range) keeps its normalized
digits instead of raising, so no untyped `OverflowError` can escape and no limit the intent does not
state is invented. Re-probed after the fix: the same-FLOAT64 pair now refuses at
`$.calls[].path_digest`; every spelling pair and every other probe outcome above is unchanged.

Tests for the hardening, all in `tests/test_whatif.py`: the spelling table in
`test_equivalent_covariate_spellings_are_one_model_input_and_refused` grew two same-FLOAT64 pairs
(`0.1` / `0.1000000000000000000000001`, `2` / `2.000000000000000000000000001`),
`test_a_hand_built_pair_whose_levels_are_one_number_is_refused` now forges three spellings of the
same number (plus the four junk levels), and the new
`test_a_level_with_no_float64_value_keeps_a_stable_digest` builds a 401-digit level, asserts a
64-hex digest that is stable across calls and differs from call B's, and pins the spelling in the
SQL text and the receipt. The golden fixture is unedited and still matches byte for byte: for its
levels (`100`, `0`) the canonical text is unchanged, so its statement SQL, statement digests and
path digests all still compare equal (probe rows "regression golden fixture match: OK" and
"regression golden path digests match: OK").

**Verification run for this session's content (the same five commands).**

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 57 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 318 tests` / `OK` (317 before the hardening; the one new test is in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1186 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

The link count is the one measured with this section and the PROGRESS row in place; the same command
run on `c5c614c` before this session's edits reported 1185, and this section plus the PROGRESS row add
exactly the one `[packet]` link the row carries (this section adds none).

**Tip record.** All five commands above were re-run on the committed branch after this session's
commit `c3c4f49` (parent `c5c614c`; it carries the hardening, this section, the PROGRESS row and the
`work.json` next-action line), giving the same results — `Ran 57 tests` / `OK`, `Ran 318 tests` /
`OK`, `Checked 261 Markdown files, 1186 local links, 8 skills; bootstrap 1293 words.` / `PASS`,
`OK: 42 tasks, 7 gates`, scope `OK` — with the working tree clean. The branch tip at hand-off is the
commit that adds this paragraph, whose only change over `c3c4f49` is this paragraph itself; the five
commands were run once more on it with the same results.

### Acceptance re-check on this session's content

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — fixture unedited, and the probe compares both statements byte for byte against it. |
| Limit violations raise typed errors | met, extended | `LimitTests` unchanged; the Rework 3 `ParserTests` / `PairTests` rows above still pass, and the hardening adds the same-FLOAT64 refusal at `$.calls[].level_mw` and `$.calls[].path_digest` plus the beyond-FLOAT64 digest row, each with code, field path and rule. |
| Incompatible result refused with reason | met, extended | The 12-mutation `test_incompatible_results_are_refused_with_a_reason` table, the seven-statement path-mismatch table and the overflow table all still pass on the hardened module; no reviewed row was changed except the rule-text assertion named above. |

Brief outputs re-checked, unchanged: two `AI.FORECAST` statements over one identical history with
NULL-target future rows; horizon ≤ 1,024 and context a multiple of 32 ≤ 2,048; the parser yields the
per-step difference with Preview and directional labels; execution stays an injected transport with
no credential, client, network or subprocess import (the static test still passes).

### Limits, stop conditions and unfinished items (Rework 3 verification)

No stop condition fired: the hardening stayed inside the allowed paths, no frozen contract,
acceptance text or `docs/work/whatif/intent.md` line was changed, no test was weakened (one
assertion follows a rule text this session changed; its property is unchanged), and no new
dependency, service, credential, network call, model call or cloud effect was introduced or needed.
The duplicate launch and the mislabelled outside commit are the two process hazards, recorded above
and in the PROGRESS row; `docs/work/FEEDBACK.md` is outside this task's allowed paths. Deliberately
left open, with owners: the contiguity walk-back and the anchor/`K` choice for a gapped series
(NUM-3, stated in the README), the engine-shape assumptions (NUM-3, README), and the two guardian
questions (orchestrator, `docs/work/FEEDBACK.md`).

**Exact next action:** designated independent re-review of `task/NUM-1` at this session's commit on
top of `c5c614c` (it carries the hardening, this section and the PROGRESS row); the reviewer decides
`done` under this file, and only that review sets `done`. After accept: NUM-2 when GATE-3 opens,
then NUM-3.

## Interim re-review of rework 3 (orchestrator seat, Fable, commit c79fd62, 2026-10-12)

Interim re-review, not the designated independent review (GPT Astra through Codex, out of credits).
It is the review-first list for the owner and does **not** set the task `done`; the designated review
supersedes it. Reviewed `task/NUM-1` at `c79fd62` (merge-base `36e2117` with `feat/h1-api-persistence`)
against the brief, `docs/work/whatif/intent.md`, designated review 2 and the executor's Rework 3 and
"Rework 3 verification" sections above. The reviewer did not author the change and edited no file but
this section. Offline only: no BigQuery, cloud, model or network command was run; the adapter was
exercised through its builders and parsers with the test module's fake transport.

**Commit mapping for the designated reviewer.** The SHAs the Rework 3 sections cite (`5b8525d`,
`829d790`, `c5c614c`, `c3c4f49`) are no longer ancestors of the branch (`git merge-base --is-ancestor`
rc=1 for all four): the orchestrator reworded the mislabelled outside commit, so the branch after the
designated-review commit `dc45bdf` is `1bbd901` (the Rework 3 code and tests, `git diff dc45bdf 1bbd901`
= 4 files, 262 insertions, 16 deletions, exactly the stat the packet gives for `5b8525d`), `7333201`,
`62a2a39` (records), `30bf76a` (the second session's FLOAT64 hardening: `_canonical_level` via
`format(float, '.17g')`, plus its record) and `c79fd62` (tip record). Gap (b) below is closed only by
`1bbd901` and `30bf76a` together: `1bbd901` alone canonicalised with `Decimal.normalize()`, which the
second session found insufficient for two decimals that cast to one FLOAT64.

### Commands run (worktree `.local/wt/NUM-1`, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 57 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 318 tests` / `OK` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1186 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `git diff 44858f9 HEAD -- tests/test_whatif.py \| grep '^-'` (lines removed or changed since the reviewed commit) | none: the test diff since designated review 2 is purely additive (+167 lines) |
| `git diff 44858f9 HEAD -- src/adapters/bigquery/fixtures/ docs/work/tasks.json docs/work/whatif/intent.md` | empty: golden fixture, task state and intent untouched |
| `git diff feat/h1-api-persistence...HEAD --stat` | the nine allowed files only; `tasks.json` changes the `state` line only |

### Adversarial probes (scratch script over the test helpers, not committed)

| # | Input | Outcome |
|---|---|---|
| P1 | Two `CovariatePath`s differing **only** in `series_relation`; A parsed from path 1, B from path 2, one `history_digest_value` supplied for both; `compare_calls` | **accepted**, `compatible=True`, `mean_delta_w 5.0` (finding 1) |
| P1b | `history_digest(context_rows(observed(), p), p)` for the two relations | **equal**: the history digest never includes the relation, so honest digests do not separate the two tables |
| P4 | levels `9007199254740992` / `9007199254740993` (one FLOAT64) | refused `WHATIF_RESULT_INCOMPATIBLE at $.calls[].path_digest` |
| P11 | levels `-0.0` / `0` | refused at `$.calls[].path_digest` |
| P12 | this path's A statement carrying B's SQL text | refused `WHATIF_CONFIG_INVALID at $.statement.sql` |
| P9 | forged `series_id` on call B | refused at `$.calls[].series_id` |
| P5 | level `1` followed by 400 zeros | builds, renders `CAST(10…0 AS FLOAT64)` (1,623-character statement), `run_pair` proceeds with the fake transport (finding 3) |
| P6 | level `10000000000000000000` (20 digits, no decimal point) | renders as an unquoted integer literal (finding 3) |
| P7 | level `-5` | accepted; the open guardian question, not re-opened |
| P10 | rendered context CTE | carries no `available_at` predicate; it matches the intent's template byte for byte (finding 4) |

### Disposition of designated review 2's gaps

| Gap | Disposition | Evidence |
|---|---|---|
| (a) statement/path compatibility: the covariate builder, SQL builder and result parser agree on the statement and column path shapes | **closed, with tests** | `parse_forecast_rows` (`whatif.py:701-725`) re-renders the SQL from the supplied path and call and requires `call`, `role`, `level_mw`, `sql` and `path_digest` to equal that canonical rendering, refusing `WHATIF_CONFIG_INVALID` at `$.statement.*`; the `CallResult` carries the recomputed digest (`:784`). Tests `ParserTests.test_a_statement_of_another_path_is_refused` (the reviewer's 100/0 vs 200/50 probe plus a same-level moved-window statement) and `test_a_statement_is_verified_field_by_field_against_this_path` (seven broken statements, both valid ones still parse). Probe P12 confirms a swapped SQL text refuses. |
| (b) equivalent-path refusal: two spellings of one path, or two decimals that are one FLOAT64, are refused rather than silently merged | **closed, with tests** | `_canonical_level` (`whatif.py:151-171`) digests the level as the FLOAT64 value (`format(float, '.17g')`, zeros folded) in `path_digest` (`:443`), and `compare_calls` repeats the check on the receipts' own `level_mw` (`:861-865`) so a stale-digest hand-built call cannot pass one number off as two. Tests `PairTests.test_equivalent_covariate_spellings_are_one_model_input_and_refused` (eight pairs incl. `0.1`/`0.1000000000000000000000001`), `test_a_hand_built_pair_whose_levels_are_one_number_is_refused`, `test_the_reviewed_level_spelling_is_kept_for_provenance`, `test_a_level_with_no_float64_value_keeps_a_stable_digest`. Probes P4 and P11 confirm the 2^53 boundary and negative zero. The reviewed spelling stays in `prior_mw`/`accepted_mw`, the SQL text and the receipt; the golden fixture (`100`/`0`) is unedited and matches. |
| minor (overflow to infinity) | closed, with test | `_finite_number` and the per-field finiteness checks (`whatif.py:884-902`), overflow-safe mean; `test_an_overflowing_difference_is_refused_and_the_mean_never_overflows`. |

Checklist, briefly: 1 yes (three acceptance items each have a test that ran; see table above); 2 yes
(scope OK); 3 yes (no frozen contract, acceptance text, fixture or reviewed test changed; test diff
additive); 4 yes (imports unchanged: stdlib plus `src.contracts.jsonutil`; static no-credential test
passes; execution stays the injected transport); 5 yes (`labels()` and `compare_calls` mode
constraints untouched by this rework, their tests pass); 6 yes (no number is filled or invented: a
non-representable difference refuses; the canonical level is the value the model receives, the
spelling is kept as provenance); 7 partially (interpreter, commands, results, unfinished items and
next action present, but the cited SHAs are not on the branch — finding 2); 8 yes for the two gaps,
with one recurrence of the same mismatch family at the pair level (finding 1). No SQL is built from
unvalidated text: every literal passes a fixed regex before rendering and the rendering matches the
intent's template. No time leakage was found in the Python-side history validation (rows after `H0`
and rows known after `H0` are refused before the transport is called); the SQL-side observation is
finding 4.

### Findings

| severity | path:line | what | why |
|---|---|---|---|
| important | `src/adapters/bigquery/whatif.py:866-875` (`compare_calls` `equal` tuple), `:576-580` (`history_digest` inputs), `:633-665` (`CallResult`) | Two calls parsed from two paths that differ only in `series_relation` compare `compatible=True` (probe P1). `CallResult` carries no relation, the `equal` tuple does not compare one, and `history_digest` does not include the relation, so honest digests are equal across two tables (P1b). The `path_digest` inequality check cannot catch it because the digests are expected to differ (the level differs). | Same failure family designated reviews 1 and 2 rated important (a pair that reports compatible while its receipts cannot reveal the mismatch); `compare_calls` is the exported seam NUM-3 will call on two stored `CallResult`s, and a two-table pair would then carry the "one identical model history" verdict. Unreachable through `run_pair` (one path), so no wrong number is produced from one path; it is a hand-built/stored-receipt gap. Correction, either: carry `series_relation` on `CallResult` (and `as_dict`) and add it to the `equal` tuple, or fold `series_relation` into the `history_digest` inputs (the golden fixture pins `path_digest` and `statement_digest` only, so neither breaks the fixture); add P1 as a regression test asserting `WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].series_relation` (or `WHATIF_HISTORY_MISMATCH`). |
| minor | `docs/work/reviews/NUM-1.md` Rework 3 and "Rework 3 verification" sections; `docs/work/PROGRESS.md` last two NUM-1 rows; `docs/work/whatif/work.json` | The cited commits `5b8525d`, `829d790`, `c5c614c`, `c3c4f49` are not ancestors of `task/NUM-1` after the orchestrator's reword (`git merge-base --is-ancestor` rc=1 for each); a reader cannot check them out. | Recurrence of the interim review's finding 4. The mapping is in the header of this section; on the next packet edit record `1bbd901` (code), `30bf76a` (hardening) and the reviewed tip, and note the reword. |
| minor / question | `src/adapters/bigquery/whatif.py:162-171` (`_canonical_level`), `:137-148` (`_decimal`) | A level with no finite FLOAT64 value (P5, 401 digits) or an integer spelling of 20+ digits with no decimal point (P6) builds, renders as an unquoted literal and runs through the transport. Whether GoogleSQL accepts such literals is not verifiable offline; a value with no FLOAT64 cannot be the FLOAT64 covariate the intent's column table declares (intent line 33), so refusing it typed would add no limit beyond the column type. | The executor chose to keep digits "so no limit the intent does not state is invented"; this is a defensible reading of "finite decimal" (intent line 210), so it is a question, not a defect: either refuse a non-finite `float(level)` as `WHATIF_CONFIG_INVALID` at the value path, or add "literal shapes beyond FLOAT64/INT64 range" to the README's "not yet verified against the engine" list for NUM-3. |
| minor / guardian question | `src/adapters/bigquery/whatif.py:401-423` (`_statement_sql`), intent SQL template lines 163-166 | The context CTE selects by `hour_start` only; the known-after-cutoff refusal (`_series_rows`, `:504-514`) guards the caller-supplied `observed` rows, not what the engine reads from the relation. If the relation holds a row with `hour_start <= H0` and `available_at > H0`, the engine's history differs from the validated, digested one. | The SQL matches the intent byte for byte, so this is intent-level, not a NUM-1 defect; recorded for the guardian alongside the two open questions. For NUM-3: supply `observed` as exactly the rows the relation returns under the same `hour_start` predicate, or the intent adds an availability predicate (which would change the golden fixture through a new intent revision, never in place). |
| minor | `src/adapters/bigquery/README.md` "Results, difference and labels" | The FLOAT64 unification assumes BigQuery's literal-to-FLOAT64 conversion rounds as Python's `float()` does (both IEEE round-to-nearest-even). Reasonable, but it is an engine assumption. | One line in the README's "not yet verified against the engine" list so NUM-3 confirms it against a recorded result. |

Already recorded by the executor, no new finding: the duplicate `rework.sh NUM-1` launch and the
outside commit that captured a live seat's uncommitted work (process hazards for the orchestrator's
ledger); the negative-level and "the builder" guardian questions.

### Outcome

Both of designated review 2's important gaps are closed with regression tests, the minor is closed, no
test was weakened, and the acceptance items hold on the committed tree. One new important finding of the
same mismatch family at the pair level (finding 1), with a one-line correction and a regression test to
add; the executor fixes on `task/NUM-1`, re-runs the verify and full suite, records the current SHAs,
and the designated independent reviewer decides `done`. This interim record sets no state and implies
no external approval, publication or deployment; the designated review supersedes it.

**Verdict: rework.** Designated review 2's two gaps are closed with tests, but `compare_calls` still accepts two calls from paths that differ only in `series_relation`, because neither the `CallResult`, the `equal` tuple nor the history digest carries the relation.

Correction to the header of this section (appended, not edited in place): the merge-base of `task/NUM-1`
with `feat/h1-api-persistence` is `f2ea7f7` (`git merge-base feat/h1-api-persistence HEAD`, run by this
reviewer), not `36e2117`, which was copied from the Rework 3 section and is stale.

## Rework 4 (executor, 2026-10-12, after the interim re-review of rework 3)

Rework of the interim re-review's one important finding and its four minor rows, alone on this branch,
parent `b5c9d8d` (the interim-re-review commit; the reviewed tip is `c79fd62`). The reviewer's
merge-base correction is confirmed here by the same command: `git merge-base feat/h1-api-persistence
HEAD` prints `f2ea7f7845f3ca7678c18aa33d1687725175c0e6`. A `/proc` scan before any write found only this
session's own process tree in this worktree (this `claude -p` process, its MCP helpers and its own
subshell), so no duplicate-launch yield applied. The important finding was reproduced first against the
reviewed revision and the same probe was re-run against the fixed worktree module; the outputs are
quoted per finding below.

No frozen contract, acceptance text, `docs/work/whatif/intent.md` line or reviewed test expectation was
changed, and the golden fixture was not edited: this rework changes no rendered SQL and no path field,
so its statements, statement digests and path digests still compare equal (probe rows "golden
statements match: True", "golden path digests match: True", "golden path as_dict match: True" on both
revisions). The test diff is purely additive (`git diff -- tests/test_whatif.py | grep '^-'` is empty).

**Finding 1 (important, `compare_calls` accepted two calls whose paths differ only in
`series_relation`) — fixed in `src/adapters/bigquery/whatif.py`.** `CallResult` now carries
`series_relation` (set from the path in `parse_forecast_rows`, exposed in `as_dict`), the pair's `equal`
tuple compares `('series_relation', …)` next to `series_id` (so a mismatch refuses
`WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].series_relation`, and the verdict's `checks` carries the
relation), and each call's relation is pattern-validated (`RELATION`) before the comparison, so a
hand-built receipt cannot carry a junk relation. This is the reviewer's first correction option, and
it also fills a receipt field the intent's receipt contract already requires (`series_ref` = relation,
anchor, first/last context hour, …; intent "Receipt fields"). `history_digest` is deliberately
unchanged — it digests the ordered rows, and the relation is provenance, not a row — so the refusal
comes from the receipt field the pair will carry. Evidence from the reviewer's P1, re-run with the
probe script at `/tmp/num1-rework4-probe/probe.py` (not committed; it executes a given source file as
a module and uses only the test module's plain-data helpers): on the reviewed revision
(`git show c79fd62:src/adapters/bigquery/whatif.py`) the noisy facts the review named reproduce —
honest history digests equal across the two relations (`P1b … True`), path digests differ, and
`compare_calls` of A from path 1 with B from path 2 returns `ACCEPTED, compatible = True` (with the
per-call rows used by the review, `mean_delta_w = 5.0`, the number the review records). On the fixed
module the same inputs refuse `WHATIF_RESULT_INCOMPATIBLE at $.calls[].series_relation: the two calls
must agree`, both for the same-row parse and for the per-call-rows parse, while a valid pair still
returns `compatible True, mean_delta_w 5.0` with `receipt relation
synthetic-project.whatif.price_hourly_fixture`. Junk relations (`None`, `7`, `''`,
`'synthetic-project.whatif'`, and a backtick-carrying relation) refuse at the same field path with the
rule "each call carries the validated project.dataset.table relation it ran over"; on the reviewed
revision the same probe could not even forge the field (`CallResult.__init__() got an unexpected
keyword argument 'series_relation'`), which is the same missing-receipt-field evidence. Tests:
`PairTests.test_the_receipts_carry_the_relation_of_their_path` (both receipts and the pair verdict
carry the relation) and `test_a_pair_of_two_relations_is_refused` (the P1 case, asserting the honest
digests are equal and the path digests differ before the refusal, plus the five junk relations).

**Finding 2 (minor, the cited SHAs are not on the branch) — fixed by the mapping above and in this
section.** The reviewer's correction is adopted: after the orchestrator's reword, the Rework 3 change
is `1bbd901` (code and tests; `git diff dc45bdf 1bbd901` is the four files and the same 262/16 stat the
Rework 3 section gives for `5b8525d`), the records are `7333201` and `62a2a39`, the second session's
FLOAT64 hardening is `30bf76a`, the tip record is `c79fd62`, and the reviewed tip is `b5c9d8d` (the
interim-re-review commit), whose parent is `c79fd62`. The `5b8525d`/`829d790`/`c5c614c`/`c3c4f49`
references in the Rework 3 sections stay as the history they are, with this mapping as the pointer.

**Finding 3 (minor / question, literal shapes beyond FLOAT64/INT64 range) — disposed as the
reviewer's second option, recorded for NUM-3, no limit invented.** The README's "not yet verified
against the engine" list now names the admitted shapes (a decimal with no finite FLOAT64 value; an
integer spelling of 20+ digits with no decimal point, rendered unquoted) and states that the value
cannot be the FLOAT64 covariate the intent's column table declares, consistent with the executor's
earlier decision not to add a limit the intent does not state ("finite decimal", intent line 210).
The existing test `test_a_level_with_no_float64_value_keeps_a_stable_digest` still passes unchanged.

**Finding 4 (minor / guardian question, the SQL-side availability predicate) — recorded, not
changed.** The README's availability section now states that NUM-3 must supply `observed` as exactly
the rows the relation returns under the statement's own `hour_start` predicate (the SQL matches the
intent's template byte for byte, so an availability predicate there would be an intent revision, not
a NUM-1 edit), and this section records the question for the guardian alongside the two open
questions, because `docs/work/FEEDBACK.md` is outside this task's allowed paths.

**Finding 5 (minor, the FLOAT64 unification is an engine assumption) — fixed in the README,** whose
"not yet verified against the engine" list now also names the assumption that BigQuery's
literal-to-FLOAT64 conversion rounds as Python's `float()` does (both IEEE round-to-nearest-even).

### Acceptance re-check after Rework 4

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — same fixture, unedited (no rendered SQL changed); the probe compares both revisions' statements, path digests and `path.as_dict()` against it, all matching. |
| Limit violations raise typed errors | met, extended | `LimitTests` and `DeltaTests` unchanged and passing; the new pair rule refuses a hand-built receipt's junk relation typed at `$.calls[].series_relation`. |
| Incompatible result refused with reason | met, extended | `ParserTests` unchanged; new `PairTests.test_a_pair_of_two_relations_is_refused` refuses the reviewer's P1 pair with code, field path and rule, and `test_the_receipts_carry_the_relation_of_their_path` pins the new receipt field. |

Brief outputs re-checked, unchanged: two `AI.FORECAST` statements over one identical history with
NULL-target future rows; horizon ≤ 1,024 and context a multiple of 32 ≤ 2,048; the parser yields the
per-step difference with Preview and directional labels; execution stays an injected transport with no
credential, client, network or subprocess import (the static test still passes).

### Verification run for Rework 4 (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 59 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 320 tests` / `OK` (318 before this rework; the 2 new tests are in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1187 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

The link count is measured with the module, README, tests and this section in place but before the
PROGRESS row (which adds one `[packet]` link). For the record: the interim review's table reports
1186 for its own tree; re-measuring `b5c9d8d` (HEAD, with the README at its committed content) in this
session gives 1187 by the same command, and the README edit changes no link count (both old and new
README carry the same two relative links), so this record states the numbers it measured and offers no
cause for the one-lower record — the first packet noted the same phenomenon for its 1091.

**Tip record.** All five commands above were re-run on the committed branch after the Rework 4 commit
`5abf3e9` (parent `b5c9d8d`), with the working tree clean, giving the same results — `Ran 59 tests` /
`OK`, `Ran 320 tests` / `OK`, `Checked 261 Markdown files, 1188 local links, 8 skills; bootstrap 1293
words.` / `PASS`, `OK: 42 tasks, 7 gates`, scope `OK`. The link count is the one with this section and
the PROGRESS row in place: 1187 before the row, plus the row's one `[packet]` link. The branch tip at
hand-off is the commit that adds this paragraph, whose only changes over `5abf3e9` are this paragraph and the self-review line in the PROGRESS row;
the five commands were run once more on it with the same results.

### Limits, stop conditions and unfinished items (Rework 4)

No stop condition fired: every fix stayed inside the allowed paths, no frozen contract or acceptance
text needed changing, no test was weakened (the module suite grew 57 → 59 and the diff to
`tests/test_whatif.py` is additive), and no new dependency, service, credential, network call, model
call or cloud effect was introduced or needed (the module still imports stdlib plus
`src.contracts.jsonutil` only, and the static no-credential test still passes). `docs/work/tasks.json`
needed no edit: NUM-1's `state` is already `in_progress` and no other key was touched. Deliberately
left open, with owners: the contiguity walk-back and the anchor/`K` choice for a gapped series (NUM-3;
README), the engine-shape assumptions including the two new README lines (NUM-3, against a recorded
engine response), and the now three guardian questions — a negative `assumed_available_capacity`,
"the builder" in the intent's series contract, and the SQL-side availability predicate (orchestrator,
`docs/work/FEEDBACK.md`).

**Exact next action:** designated independent re-review of `task/NUM-1` at this rework's commit on top
of `b5c9d8d` (the post-commit numbers are in the tip-record commit that follows it); the designated
independent reviewer decides `done` under this file, and only that review sets `done`. After accept:
NUM-2 when GATE-3 opens, then NUM-3.

### Self-review (executor, not independent)

Each of the reviewer's rows was handled one by one: finding 1 reproduced against the revision as
reviewed (the exact source piped from `git show c79fd62:…` and executed as a module, so the probe ran
the reviewed code, not the worktree copy) and re-probed after the fix with the same script — the
outputs quoted above are the ones it printed; finding 2 recorded with the branch's current SHAs;
findings 3 and 5 given README lines in the "not yet verified against the engine" list; finding 4
recorded for the guardian and for NUM-3 in the README. Every number in this section was measured in
this session by the commands in its table or by the probe's printed output; no case fact, receipt or
engine result is asserted. Known limits recorded rather than hidden: the pair rule now requires the
two receipts to agree on the relation *and* the relation to be a well-formed `project.dataset.table`
string — it does not compare a `h0` field directly (the two calls carry no anchor field; the equal
`window_start`/`window_end`/`context_window` entries plus the per-step grid check in the difference
loop pin the hours instead) and it does not compare the gaps recorded in the intent's `series_ref`,
which stays NUM-3's receipt material; and these fixes tighten the module's internal
consistency without verifying the engine's result shape, which stays NUM-3's against a recorded engine
response. This is self-review, not an independent review; state stays `in_progress`.

## Interim re-review of rework 4 (orchestrator seat, Fable, commit c665700, 2026-10-12)

Interim re-review, not the designated independent review (GPT Astra through Codex, still out of
credits). It is the review-first list for the owner and does **not** set the task `done`; the
designated review supersedes it. Reviewed `task/NUM-1` at `c665700` (rework 4 code and tests in
`5abf3e9`, tip record in `c665700`; merge-base `f2ea7f7` with `feat/h1-api-persistence`, confirmed by
`git merge-base`) against the brief, `docs/work/whatif/intent.md` (receipt fields, lines 246-268), the
"Interim re-review of rework 3" section and the executor's Rework 4 section above. The reviewer did not
author the change and edited no file but this section. Offline only: no BigQuery, cloud, model or
network command was run; the adapter was exercised through its builders and parsers with the test
module's plain-data helpers and fake transport.

### Commands run (worktree `.local/wt/NUM-1`, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 59 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 320 tests` / `OK` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1188 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `git diff b5c9d8d HEAD -- tests/test_whatif.py \| grep -c '^-[^-]'` | `0`: the test diff since the rework-3 re-review is purely additive (+41 lines, two `PairTests` methods) |
| `git diff b5c9d8d HEAD --stat -- src/adapters/bigquery/fixtures/ docs/work/tasks.json docs/work/whatif/intent.md` | empty: golden fixture, task state and intent untouched |
| `git show 5abf3e9 --stat`, `git show c665700 --stat` | six files (PROGRESS row, this packet, `work.json` next action, README, `whatif.py` +21/-8 incl. docstring, tests +41); tip record touches PROGRESS and this packet only |
| `grep -rn "CallResult(" src/ tests/ scripts/` | one constructor call (`whatif.py:780`, `parse_forecast_rows`), so the new required field breaks no other caller; `src/adapters/bigquery/__init__.py` only re-exports the class |

### Adversarial probes (scratch script over the test helpers, not committed)

| # | Input | Outcome |
|---|---|---|
| Q1 | path 1 with the B statement rendered for path 2 (differs only in the `FROM` relation) through `parse_forecast_rows` | refused `WHATIF_CONFIG_INVALID at $.statement.sql` (the rework-3 statement/path check already pins the relation inside the SQL text) |
| Q2 | the rework-3 P1 pair: A parsed from path 1, B from path 2, equal honest history digests | refused `WHATIF_RESULT_INCOMPATIBLE at $.calls[].series_relation`, rule "the two calls must agree" — the finding's case now refuses with code, field path and rule |
| Q3 | B from path 2 with its receipt's `series_relation` edited (frozen dataclass `replace`) to equal A's | **accepted** `compatible=True`; B's own `path_digest` and `statement_digest` still encode relation 2, so the receipt is self-inconsistent and an auditor recomputing the digest from the stored path catches it (finding 1 below, minor) |
| Q4 | B's relation upper-cased | refused at `$.calls[].series_relation` (the `RELATION` pattern requires a lower-case project id) |
| Q5 | valid pair through `run_pair` | `compatible=True`; both receipts and `verdict['checks']['series_relation']` carry `synthetic-project.whatif.price_hourly_fixture`; `as_dict()` exposes the field |

### Disposition of the rework-3 re-review items

| Item | Disposition | Evidence |
|---|---|---|
| important: `compare_calls` accepted two calls whose paths differ only in `series_relation` | **closed, with tests** | `CallResult.series_relation` (`whatif.py:639`), set from the path in `parse_forecast_rows` (`:781`) and exposed in `as_dict` (`:659`); per-call `RELATION.fullmatch` validation before any comparison (`:845-847`) so a junk relation (`None`, `7`, `''`, two-part, backticked) refuses at `$.calls[].series_relation`; `('series_relation', …)` in the `equal` tuple next to `series_id` (`:875`), so two relations refuse `WHATIF_RESULT_INCOMPATIBLE at $.calls[].series_relation` with the rule text. `history_digest` deliberately unchanged (`:576-580`): the reviewer offered either correction; carrying the relation on the receipt is the one that also fills the intent's `series_ref` relation field. Regression tests `PairTests.test_a_pair_of_two_relations_is_refused` (asserts the honest history digests are equal and the path digests differ *before* the refusal, then the five junk relations) and `test_the_receipts_carry_the_relation_of_their_path`. Probe Q2 reproduces the refusal; Q1 shows the swapped-statement route is closed too. The golden fixture is unedited and still matches (no rendered SQL or path field changed; the fixture's two `series_relation` keys are the path's, not a receipt's). |
| minor: stale SHAs (`5b8525d`, `829d790`, `c5c614c`, `c3c4f49`) | **disposed honestly** | the mapping (`1bbd901` code, `7333201`/`62a2a39` records, `30bf76a` hardening, `c79fd62` tip record) is recorded in the Rework 4 section and the PROGRESS row; the historical references stay as history, which is the right treatment of an append-only packet. One wording slip remains (finding 2 below). |
| minor / question: non-finite or 20+-digit integer level spelling | **disposed as the reviewer's option 2** | README "not yet verified against the engine" list (`README.md:130-135`) names both shapes, states the value cannot be the FLOAT64 covariate the intent declares, and that NUM-1 invents no limit beyond "finite decimal"; the existing digest-stability test is unchanged. Honest: a question recorded for NUM-3, not hidden. |
| minor / guardian question: SQL-side availability predicate | **recorded, not changed** | README `:76-82` tells NUM-3 to supply `observed` as exactly the rows the relation returns under the statement's own `hour_start` predicate and names the intent revision route; the packet lists it as the third guardian question. `FEEDBACK.md` correctly left alone (outside allowed paths); the orchestrator carries it. |
| minor: README engine-assumption line (FLOAT64 rounding) | **closed** | README `:135-137`: the unification assumes BigQuery's literal-to-FLOAT64 conversion rounds as Python's `float()` (IEEE round-to-nearest-even), in the "not yet verified" list for NUM-3. |

Checklist, briefly: 1 yes (the three acceptance items each have tests that ran: golden fixture tests,
`LimitTests`/`DeltaTests`, `ParserTests` plus the two new `PairTests`); 2 yes (scope OK on the reviewed
branch); 3 yes (no frozen contract, acceptance text, intent line, fixture or reviewed test changed;
test diff has zero removed lines); 4 yes (`whatif.py` imports unchanged: stdlib plus
`src.contracts.jsonutil`; the static no-credential test still passes; execution stays the injected
transport); 5 yes (`labels()` and the pair's execution-mode constraints untouched, tests pass); 6 yes
(no number invented: the relation carried is the path's own validated string; the P1 probe's `5.0` is
the fake transport's); 7 yes (interpreter, commands, results, the current SHAs, unfinished items and the
exact next action are recorded; the reproduce-first-then-fix evidence is quoted); 8 yes (the receipt now
carries the relation the intent's `series_ref` requires; nothing contradicts the blueprint or the domain
invariants — one pair is one region in one relation).

Nothing regressed or weakened: the rework adds one required field to a frozen dataclass with a single
constructor site, one validation and one tuple entry; the 57 earlier tests pass unchanged and the
golden fixture, path digests and statement digests are byte-identical across the two revisions.

### Findings

| severity | path:line | what | why |
|---|---|---|---|
| minor / NUM-3 note | `src/adapters/bigquery/whatif.py:845-847`, `:874-886` (`compare_calls`) | A hand-built receipt whose `series_relation` (or any other `equal`-tuple field: `series_id`, `window_*`, …) is edited to agree with the other call passes, although its own `path_digest` and `statement_digest` still encode the original path (probe Q3). `compare_calls` does not recompute `path_digest` from the receipt's fields (it cannot: the receipt carries no `h0`, as the executor's self-review notes). | Not the reviewed finding's shape: the finding was *honest* receipts that compare compatible while revealing nothing; here the receipt is self-inconsistent and reveals the forgery to anyone recomputing the digest from the stored path, and the same forge-to-match property held for every `equal` field through designated reviews 1 and 2 without being raised. Correction for NUM-3, not NUM-1: when loading stored receipts, recompute `path_digest` from the stored `CovariatePath` and refuse a receipt whose fields disagree with it (or carry `h0` on the receipt so `compare_calls` can). |
| minor | `docs/work/reviews/NUM-1.md` Rework 4 header vs its "Finding 2" paragraph | The header says "parent `b5c9d8d` … the reviewed tip is `c79fd62`"; Finding 2 says "the reviewed tip is `b5c9d8d` (the interim-re-review commit), whose parent is `c79fd62`". Both SHAs are on the branch, but the two sentences name different commits as the reviewed tip. | Same family as the rework-3 minor on SHA accuracy. The rework-3 re-review reviewed `c79fd62` (its header) and was committed as `b5c9d8d`; so the header's reading is right and Finding 2's is a slip. One appended line on the next packet edit; no code effect. |
| minor / naming note | `src/adapters/bigquery/whatif.py:639`, intent line 261 | The intent's receipt groups the relation under `series_ref` (relation, anchor, first/last context hour, gaps); the receipt carries it flat as `series_relation`, matching the path's field name. | Consistent with the module's path naming and with `path.as_dict()`; NUM-3 assembles the full `series_ref` (anchor and gaps are NUM-3 material, as the self-review says). Recorded so the designated reviewer does not read it as a missing field. |

Already recorded by the executor, no new finding: the three guardian questions (negative level, "the
builder", SQL-side availability predicate) and the two process hazards from rework 3.

### Outcome

The rework-3 re-review's one important finding is closed with regression tests on the reviewed tree,
its four minors are dispositioned honestly (two README lines, one NUM-3 instruction, one SHA mapping),
no test was weakened, no frozen contract or fixture changed, and the acceptance items hold on the
committed tree. The three findings here are minor and need no code change on this task. The designated
independent reviewer decides `done`; this interim record sets no state and implies no external
approval, publication or deployment.

**Verdict: accept.** Two calls from paths that differ only in `series_relation` now refuse `WHATIF_RESULT_INCOMPATIBLE` at `$.calls[].series_relation` because the receipt carries the validated relation and the pair compares it, with the P1 regression test and the golden fixture intact; the designated review supersedes this interim one.

## Designated review 3 (GPT Sol, independent, commit `646385b`, 2026-10-13)

> Independent review of `646385b4c08a` against `feat/h1-api-persistence`, including the requested diff and commit log. Working tree clean; no files edited.
> 
> Verification executed with Python 3.14.4:
> 
> - `/usr/bin/python3 -m unittest tests.test_whatif -v`: **59 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence`: **OK**
> - Full offline suite: **320 tests, OK**
> - `plan.py check`: **OK: 42 tasks, 7 gates**
> - `repo.py check`: **PASS**
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | All acceptance demonstrated | **No** | Golden SQL and typed limit tests pass; an additional incompatible numeric-result probe raises an untyped exception, detailed below. |
> | 2 | Changes within allowed paths | **Yes** | Explicit-base scope command printed OK; all nine changed files are allowed. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes** | Diff changes no frozen contract or acceptance text; the new test module contains no skipped tests. |
> | 4 | No unauthorized dependency or external effect | **Yes** | Standard-library implementation with injected transport; static boundary test passes. Reviewed changes introduce no credential or network execution. |
> | 5 | Truthful mode labels | **Yes** | Fixtures identify synthetic data; mode-consistency tests pass; README explicitly records engine behavior as unverified. |
> | 6 | Unknowns preserved; no invented facts | **Yes** | Availability defaults to unknown; late-known rows are refused; timezone remains explicitly unverified. Fixture numbers are labelled synthetic. |
> | 7 | Complete verification and handoff packet | **Yes** | Rework 4 packet records interpreter, exact commands/results, open guardian questions and next action; task remains `in_progress`. |
> | 8 | Consistent with product direction and invariants | **Yes** | Identical-history construction, NULL future targets, Preview/directional labels and additive results preserve the proposal’s uncomputed state and §5.6 method. |
> 
> Findings:
> 
> **important | src/adapters/bigquery/whatif.py:764; src/adapters/bigquery/whatif.py:498 | Numeric validation can escape the typed refusal boundary: `math.isfinite()` converts an arbitrarily large integer to float and raises `OverflowError`. | Executed probes setting a forecast’s `value` to `10**400`, and separately an observed context price to `10**400`, both produced `OverflowError: int too large to convert to float`, not `WhatIfError`. Thus an incompatible result lacks the required code, field path and rule. | Guard float conversion and overflow before testing finiteness; return `WHATIF_RESULT_INCOMPATIBLE` for forecast fields and `WHATIF_HISTORY` for context prices, with regression coverage for both paths. Disposition: unresolved.**
> 
> **Verdict: rework.** The passing suite does not establish the required typed refusal for incompatible numeric results, and the executed probe demonstrates an unresolved important defect.
**Verdict: rework.** Guard float conversion so oversized integers return the typed WhatIfError with code, field path and rule; tests for forecast value and context price. Address every blocking/important row above; dispose of minors explicitly.

## Rework 5 (executor, 2026-10-13, after the designated review 3)

Rework of the designated review 3's one important row, alone on this branch, parent `de3ee20` (the
designated-review commit; the reviewed tip is `646385b`, the merge-base with
`feat/h1-api-persistence` is `f2ea7f7`, whose tip is `f8fc579`). The finding was reproduced first
against the code as reviewed — the reviewed revision taken with
`git show 646385b:src/adapters/bigquery/whatif.py` and executed as a module by a probe under
`/tmp` (registered in `sys.modules` so its dataclasses resolve, path built by the reviewed module
itself) — and the same probes were re-run against the fixed worktree module; both outputs are
quoted below. A `/proc` scan before any write found only this session's own process tree in this
worktree (PID 704387, the `claude -p` process, its MCP helpers and its own subshells), so no
duplicate-launch yield applied.

**Finding (important, numeric validation could escape the typed refusal boundary) — fixed in
`src/adapters/bigquery/whatif.py`.** `math.isfinite(value)` converts its argument to float, so an
arbitrarily large `int` — which the `type(value) not in (int, float)` guard admits — raised an
uncaught `OverflowError` before the finiteness test, in the parser's STRUCT-field loop
(`src/adapters/bigquery/whatif.py:764` as reviewed) and in the context-row target price
(`:498` as reviewed). The conversion is now guarded and every failure is the typed refusal of its
own path:

- `_finite_number` (line 180) takes the caller's `code` and `rule` and wraps the `float()`
  conversion, so an integer too large to convert, a non-number and a non-finite value all refuse
  with code, field path and rule. The parser's three forecast fields (`value`,
  `prediction_interval_lower_bound`, `prediction_interval_upper_bound`) call it unchanged for every
  value that used to pass — `WHATIF_RESULT_INCOMPATIBLE` at `$.rows[i].price_php_mwh.<field>`, rule
  "a finite numeric value" — and `_series_rows` calls it for the context price — `WHATIF_HISTORY`
  at `$.context_rows[i].price_php_mwh`, rule "non-NULL finite target value".
- The reviewer's probes, re-run on the reviewed revision and on the fix:

| Probe | Reviewed (`646385b`, executed as a module) | Fixed worktree |
|---|---|---|
| forecast `price_php_mwh.value = 10**400` | `UNTYPED OverflowError: int too large to convert to float` | `WHATIF_RESULT_INCOMPATIBLE at $.rows[0].price_php_mwh.value: a finite numeric value` |
| observed context price `10**400` through `run_pair` | `UNTYPED OverflowError: int too large to convert to float` | `WHATIF_HISTORY at $.context_rows[0].price_php_mwh: non-NULL finite target value` |
| forecast `prediction_interval_lower_bound = 10**400` | same untyped `OverflowError` | `WHATIF_RESULT_INCOMPATIBLE at $.rows[0].price_php_mwh.prediction_interval_lower_bound: a finite numeric value` |

**Same defect family, found while fixing and closed (recorded here, not a review row).** Two
further untyped escapes of the same kind existed and would have been the next probe:

- the *constructed* context covariate: `float(Decimal(path.accepted_mw))` returns `inf` — no
  exception — for a level beyond FLOAT64, so `context_rows` built rows carrying an infinity and
  `run_pair` then died inside canonical JSON (`UNTYPED CanonicalizationError: artifact content
  could not be canonicalized`). The new `_constructed_level` (line 199) converts the level as the
  FLOAT64 the statement casts and refuses a level with no finite FLOAT64 value:
  `WHATIF_CONFIG_INVALID` at `$.accepted_mw`, from `context_rows`, `availability_summary` and
  `run_pair`, before any statement is rendered or transported. `build_covariate_path`,
  `render_statements`, `path_digest` and `covariate_basis` still admit such a level and keep its
  spelling (the intent's limit is "finite decimal"; this is Rework 3's reviewed stance and the
  README's), and `test_a_level_with_no_float64_value_keeps_a_stable_digest` is untouched and still
  passes — no limit is added where the value is only rendered and digested. The refusal sits at
  the point where the value would have to *be* the FLOAT64 model input, and its rule says so. A
  huge *prior* level behaves as before (it is never a context row): a run renders it into call A's
  literal and the offline pair still computes (`mean_delta_w 5.0` on the fake transport); the
  engine's acceptance of that literal stays the README's recorded unverified engine-shape item.
- hand-built context rows fed to the public `history_digest`: a row carrying `inf`, `nan`, a string
  price, a float count or a non-string id/`hour_start` raised `UNTYPED CanonicalizationError` from
  the canonical serializer. `history_digest` now revalidates every row as the row builder does (the
  five model-input columns, the series id, the hour text, finite numbers) and refuses
  `WHATIF_HISTORY` at `$.context_rows[i].<column>` — typed, before anything is digested.
- A 1,501-case junk-typed battery (every forecast STRUCT and row field, every observed-series
  field, hand-built digest rows, hand-built steps/levels/horizons, every path field × the three
  public readers, and JSON text carrying an out-of-range literal) reports 0 uncaught exceptions
  after the fix; the same battery surfaced the two extra cases above. `n_resources_out_hour` is
  deliberately unchanged: a huge `int` count serializes as a JSON integer and escapes nothing, and
  bounding it would invent an INT64 limit the intent does not state — the count's range belongs to
  NUM-3's engine run, not to this validation.

**Tests (module 59 → 63, suite 320 → 324; additive only).**
`ParserTests.test_an_oversized_integer_in_a_forecast_field_is_refused_typed` (the three STRUCT
fields, each asserting code, field path and rule) plus an `oversized_value` mutation added to the
`test_incompatible_results_are_refused_with_a_reason` table (now 13 mutations);
`ContextHistoryTests.test_an_oversized_integer_in_a_context_price_is_refused_typed` (`context_rows`
and `run_pair`, the injected transport asserted uncalled);
`test_a_constructed_level_with_no_float64_value_is_refused_typed` (three public readers, the
rendered SQL and the path digest still produced, the 1e308 boundary still building);
`test_a_hand_built_row_with_a_non_finite_value_is_refused_by_the_digest` (eight values, each at
its own column path).

**README** updated in the same commit: the guarded numeric reader and the revalidated digest rows
are described in "Results, difference and labels", and the "not yet verified against the engine"
paragraph now says a beyond-FLOAT64 level is admitted by the builder, renderer and digest but
refused typed by a run.

No frozen contract, acceptance text, `docs/work/whatif/intent.md` line or reviewed test expectation
was changed or weakened, and the golden fixture was not edited: this rework changes no rendered SQL
for any valid path, and `test_golden_sql_matches_the_fixture` still passes against it unchanged.

### Acceptance re-check after Rework 5

| Acceptance item | Result | Evidence |
|---|---|---|
| SQL text matches a golden fixture | met, unchanged | `test_golden_sql_matches_the_fixture`, `test_golden_path_digests_and_labels_match_the_fixture`, `test_rendered_statements_are_deterministic` — same fixture (unedited); the new constructed-level test also asserts the rendered SQL and digest are still produced for a beyond-FLOAT64 level. |
| Limit violations raise typed errors | met, extended | `LimitTests` and `DeltaTests` unchanged; a forecast field or context price carrying an arbitrarily large integer is now a typed `WHATIF_RESULT_INCOMPATIBLE` / `WHATIF_HISTORY` with field path and rule instead of an uncaught `OverflowError`, and a non-finite value in a hand-built digest row is a typed `WHATIF_HISTORY`. |
| Incompatible result refused with reason | met, extended | `ParserTests.test_incompatible_results_are_refused_with_a_reason` (13 mutations, the new row still asserting code, nonempty rule and `$.` field path) and the untouched typed rows; `test_an_oversized_integer_in_a_forecast_field_is_refused_typed` adds the numeric-escape case. |

Brief outputs re-checked, unchanged: two `AI.FORECAST` statements over one identical history with
NULL-target future rows; horizon ≤ 1,024 and context a multiple of 32 ≤ 2,048 validated before
rendering; the parser still yields the per-step difference with Preview and directional labels;
execution stays an injected transport with no credential, client, network or subprocess import (the
static test still passes).

### Verification run for Rework 5 (exact commands, `/usr/bin/python3` = Python 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_whatif -v` (the packet verify) | `Ran 63 tests` / `OK` |
| `/usr/bin/python3 -m unittest discover -s tests` (full offline suite) | `Ran 324 tests` / `OK` (320 before this rework; the 4 new tests are in this task's module) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 261 Markdown files, 1190 local links, 8 skills; bootstrap 1293 words.` / `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` | `OK: all changed files inside NUM-1 allowed paths` |

The link count 1190 was measured with this rework's code, README and test edits in place but
before this section and the PROGRESS row existed, so it is the count the branch already had at
HEAD; this section and the row are re-measured and recorded in the tip record below.

**Tip record.** All five commands above were re-run on the committed branch at `037ebdf` (the
Rework 5 commit; parent `de3ee20`, the designated-review commit), giving the same results —
`Ran 63 tests` / `OK`, `Ran 324 tests` / `OK`, `Checked 261 Markdown files, 1191 local links,
8 skills; bootstrap 1293 words.` / `PASS`, `OK: 42 tasks, 7 gates`, scope
`OK: all changed files inside NUM-1 allowed paths` — with the working tree clean. The 1191 is the
count with this section and the PROGRESS row in place (1190 without them, the number quoted above);
this tip-record paragraph adds no link. The commit carries the module, its README, the test module,
this packet, the PROGRESS row and the `work.json` next action; `docs/work/tasks.json` is untouched
(NUM-1 is already `in_progress`). Branch tip at hand-off after this paragraph's commit is the only
commit after `037ebdf`: it changes this packet alone, adds no link, and the five commands were
re-run on it with the results above.

Files this rework touched: `src/adapters/bigquery/whatif.py`, `src/adapters/bigquery/README.md`,
`tests/test_whatif.py`, this packet, `docs/work/PROGRESS.md` and the `next_action` line of
`docs/work/whatif/work.json`. `docs/work/tasks.json` needed no edit: NUM-1's `state` is already
`in_progress` and no other key was touched; the PROGRESS task-table row is unchanged for the same
reason, only the log gains one row.

### Limits, stop conditions and unfinished items (Rework 5)

No stop condition fired: every fix stayed inside the allowed paths, no frozen contract, acceptance
text or intent line needed changing, no test was weakened, skipped or deleted, and no new
dependency, service, credential, network call, model call or cloud effect was introduced or needed
(the module still imports stdlib plus `src.contracts.jsonutil` only, and the static no-credential
test still passes). Deliberately left open, with owners: the contiguity walk-back and the
anchor/`K` choice for a gapped series (NUM-3; stated in the README); the engine-shape assumptions —
the target STRUCT name, the `AI.FORECAST` keyword spelling, the `_hour` zone-text echo, the
conditional `model` key check, the FLOAT64 rounding assumption and the GoogleSQL acceptance of a
beyond-FLOAT64 literal (NUM-3, README); and the three guardian questions recorded by earlier
reworks (a negative `assumed_available_capacity`; "the builder" in the intent's series contract;
whether the intent's SQL should gain an availability predicate — orchestrator, since
`docs/work/FEEDBACK.md` is outside this task's allowed paths).

**Exact next action:** independent re-review of the Rework 5 commit (its SHA and the post-commit
numbers are in the tip record below, on top of it); the designated independent reviewer decides
`done` under this file. After accept: NUM-2 when GATE-3 opens, then NUM-3.

### Self-review (executor, not independent)

The reviewer's probe was reproduced against the reviewed revision executed as a module (output
quoted above), fixed, and re-probed — the modules' own `math.isfinite` conversion is now guarded at
every site that touches an input (Rework 3's `_canonical_level` already carried its own guard). The
review's row was re-read: the mandated codes and field paths are exactly
`WHATIF_RESULT_INCOMPATIBLE` at `$.rows[i].price_php_mwh.<field>` for forecast fields and
`WHATIF_HISTORY` at `$.context_rows[i].price_php_mwh` for context prices, both with their rule, and
both have regression tests. The two extra same-family cases are recorded above with their
before/after outputs; the one behaviour deliberately not changed (`n_resources_out_hour` range) is
recorded with its reason. Every number in this section was measured in this session by the commands
and probes in its tables; no case fact, receipt, engine result or model output is asserted, and the
engine-shape items stay unverified for NUM-3. Known limit recorded rather than hidden: the fixes
treat the numbers *supplied to* the module and do not verify what the engine returns or accepts.
This is self-review, not an independent review; state stays `in_progress`.

## Orchestrator re-measure after rebase onto the integration branch (2026-10-13)

Rebased onto `feat/h1-api-persistence` (which now carries the accepted CORE-2 and CORE-4); earlier commit citations in this packet name pre-rebase commits. At `44d60dd`: full offline suite `Ran 383 tests in 5.013s` OK; task tests `Ran 63 tests in 0.089s` OK; `plan.py scope NUM-1 feat/h1-api-persistence` OK: all changed files inside NUM-1 allowed paths; `plan.py check` OK; `repo.py check` PASS. Run by the orchestrator seat; ready for the designated re-review.

## Designated review (GPT Sol, independent, commit `6437735`, 2026-10-13)

> Independent review of `64377359df0c`, using `git diff feat/h1-api-persistence...HEAD` and `git log feat/h1-api-persistence..HEAD`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** All 63 what-if tests passed, including golden SQL equality, typed limit refusals, and incompatible-result refusals with reasons. |
> | 2 | Allowed paths respected | **Yes.** Requested scope command printed `OK: all changed files inside NUM-1 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes no frozen contract or acceptance text; tests are additive, with no skips or weakened existing tests. |
> | 4 | Dependencies and external effects within scope | **Yes.** Adapter uses stdlib and existing JSON utilities; transport is injected. No credential/client setup or external execution added. |
> | 5 | Truthful mode labels | **Yes.** Fixtures explicitly identify synthetic execution; tests enforce Preview/directional labels and reject contradictory pair modes. |
> | 6 | Unknowns remain unknown | **Yes.** Availability defaults to `unknown`; late-known rows are refused. Constructed covariates and unverified timezone assumptions are explicitly labelled. |
> | 7 | Complete verification and handoff packet | **Yes.** Packet records interpreter, commands, results, unfinished engine checks and next action; its final section records post-rebase verification. |
> | 8 | Product and domain consistency | **Yes.** Implementation preserves proposal consequences as `uncomputed`, separates simulation outputs, and makes no forecast-skill or event-probability claim. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_whatif -v` — **63 tests, OK**
> - `/usr/bin/python3 scripts/plan.py scope NUM-1 feat/h1-api-persistence` — **OK**
> - `/usr/bin/python3 -m unittest discover -s tests` — **383 tests, OK**
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 45 tasks, 7 gates**
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**
> 
> Findings:
> 
> minor | `docs/work/whatif/work.json:13` | Resume pointer references pre-rebase commits and obsolete verification counts | `next_action` names `de3ee20` and 324 tests; current packet records the rebase and the executed suite contains 383 tests | Refresh the pointer to the reviewed revision and current verification evidence.
> 
> **Verdict: accept** — All NUM-1 acceptance items were demonstrated, with no blocking or important findings; BigQuery execution and engine compatibility remain explicitly unverified NUM-3 work.
**Verdict: accept.** Re-review after the rebase; BigQuery execution remains NUM-3 work.
