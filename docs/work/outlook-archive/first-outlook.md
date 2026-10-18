# ARCH-3: the dependency walk, the first outlook, and stale marking

Task record, written 2026-10-16 by the ARCH-3 executor seat on branch `task/ARCH-3` from
`016ae92` (`feat/price-outlook`, the merge of PRICE-2). Offline throughout: no model call, no
network, no cloud write and no clock — every instant below is a caller-supplied field, and no
price value, node name or portfolio volume appears in this repository. The values file the outlook
points at carries the forecast and stays in the ignored `.local/` archive, cited by digest and row
count only.

**Read first, in the brief's order.** [AGENTS.md](../../../AGENTS.md);
[milestones](../milestones.md); [the outlook archive records](records.md) (ARCH-1);
[the PRICE-2 baselines](../price-outlook/baselines.md); [the register](register.md) (ARCH-2). The
intent this task implements is the plan note [the outlook archive and the assumption register](intent.md),
section "Dependency (ARCH-3)"; its shape is followed exactly and it was not changed.

## 1. What was built

| Path | What it is |
|---|---|
| `src/outlook/dependency.py` | The dependency walk (`outlook -> assumption_ids -> evidence refs`), the `StaleMark` record and its store, `mark_stale`, and `direction_share`, the ARCH-3 direction check. Standard library only, plus the archive's own record kinds, the register and `src/contracts/jsonutil.py`. |
| `tests/test_outlook_dependency.py` | 60 tests, all offline: the walk and its unknown ids, every `StaleMark` validator branch, the marking rules (accepted, unknown, duplicate, later-revision, demonstration, and the rework regressions of §12), the erasure checks against the outlook bytes, the direction check and its refusals, and the stdlib-only rule. |
| `docs/work/outlook-archive/first-outlook.md` | This record. |
| `docs/work/outlook-archive/register.json` | **Five rows added** for the assumptions the first outlook rests on (two owner-accepted, three in force), inside the rows ARCH-2 entered. |
| `docs/work/outlook-archive/register.md` | A labelled **addendum** under ARCH-2's audit block with the register's live counts, so that record's snapshot of 37 rows is not read as today's file. |
| `src/outlook/records.py` | **One integration fix**: an `assumption_id` now takes the register's own `<family>:<slug>` form (`ASSUMPTION_ID`), while `outlook_id` keeps the strict file-name rule. See §5. |
| `tests/test_outlook_records.py` | One test added for that id form; no existing test changed. |
| `tests/test_outlook_register.py` | The register's count pins moved from 37 to 42 (four assertions) and the family check narrowed to the counted families — no test weakened. |

Nothing else was touched: `src/price/` was read, never edited; `src/review/`, the frozen
contracts, the h0 kinds and the API are unchanged; no route or page reads the archive yet
(DESK-1).

## 2. The walk: outlook -> assumptions -> evidence

`dependency.walk(outlook, register_payload=...)` follows one issued outlook's `assumption_ids`
into the register and returns, per assumption, its family, layer, state, the proposition it
asserts, its **evidence refs** — the `source_locator` citations (path, one-based line, verbatim
quote) the register row was read from — and the `affected_code` paths its value flows through. An
id the register does not carry is reported under `unknown` with `known: false` and no evidence,
never resolved by guesswork; the register's own refusals pass through as `RegisterError` rather
than being re-coded here. `walk_archive` walks every issued outlook of an archive.

The walk of the first outlook resolves all five of its assumptions:

| Assumption | Family | Layer | State | Evidence refs | Affected code |
|---|---|---|---|---|---|
| `price:final_settlement_lmp` | price | analytical | accepted | target-contract.md:9; price-basis.md:81; coverage.md:46 | `src/price/series.py`, `src/price/baselines.py`, `scripts/price/baselines.py` |
| `price:regional_reference_series` | price | exploratory | deployed | coverage.md:43; target-contract.md:10 | `src/price/series.py`, `scripts/price/baselines.py` |
| `price:one_day_embargo` | price | exploratory | deployed | target-contract.md:23,17 | `src/price/baselines.py`, `src/price/scorecard.py` |
| `rules:billing_month_clock` | rules | official | accepted | target-contract.md:14; price-basis.md:46; coverage.md:5 | `src/price/series.py`, `src/price/baselines.py` |
| `rules:marked_months_never_filled` | rules | official | deployed | target-contract.md:19; coverage.md:42 | `src/price/series.py`, `src/price/scorecard.py` |

Every quote is re-checked by the register's audit on every run, so a citation that drifts from its
line fails the register's own test rather than this record. The walk's `unknown` list is empty.

## 3. Stale marking: changing an accepted assumption marks dependents, and erases nothing

`mark_stale(archive, assumption_id, new_revision, marked_at=..., register_payload=..., synthetic=...)`
scans the issued outlooks, takes every one whose `assumption_ids` contain the changed assumption
and whose issue precedes the marking instant, and appends one `StaleMark` per affected outlook to
`<root>/stale/`. It returns the affected ids, sorted. Nothing on that path writes an outlook.

A mark is a record of the same archive, sealed like the others (`content_digest` over its fields,
closed key set) and carrying: the assumption id, the revision the change landed at, the outlook
id and **the exact issued bytes** it affects (`outlook_digest`), the assumption's register state
at marking (`accepted` for an accepted assumption), the marking instant, and `synthetic`. Two
rules keep the set honest:

* **Written once per `(assumption_id, new_revision, outlook_digest, synthetic)`.** The file name
  is that key's digest, so a duplicate is refused atomically by `O_EXCL` — not by a scan a
  concurrent write could slip past (the pattern ARCH-1's first review corrected for receipts).
  Provenance is part of a mark's identity because it is part of what the mark asserts: a
  demonstration and a real mark of one change are two statements, so they stand in two files, and
  a labelled demonstration can never refuse the real mark a change lands (§12, finding 1).
* **Provenance runs one way, as in the archive.** A real mark (`synthetic: false`) declares a
  change; a demonstration (`synthetic: true`) declares itself one. `stale_outlooks()` reports the
  real stale set only, `demonstration_outlooks()` and `marks_of()` read the rest back, so a
  demonstration is visible and labelled rather than hidden — and never makes a healthy outlook
  read as stale.

### The run on the real archive

The first outlook was issued and then marked (the run is §6). The mark stored:

```json
{
  "assumption_id": "rules:billing_month_clock",
  "assumption_state": "accepted",
  "content_digest": "15d17197c327b3357483826652048d81743d4e1f367f2fc7469ef34b73328bf2",
  "kind": "StaleMark",
  "marked_at": "2026-10-16T00:00:00Z",
  "new_revision": "016ae92",
  "outlook_digest": "24ef4704e5245886ebfea82dba5d02fa378e0a1d93e63e2f30d46e5380f59c7e",
  "outlook_id": "outlook-2026-11-system",
  "schema_version": "outlook.v1",
  "synthetic": true
}
```

Stated plainly, because it matters: **`synthetic` is `true` here.** No accepted assumption has
changed since the first outlook was issued — there has been no evidence event — so this mark is a
labelled demonstration of the marking path, and it declares itself one. The real readings after it
are `stale_outlooks() == ()` (the archive holds no stale outlook) and
`demonstration_outlooks() == ("outlook-2026-11-system",)`. The outlook's file bytes are identical
before and after (digest `24ef4704…`), the archive's `verify()` reports no problem, and the marks
store's own `verify()` reports none either. When the first real change lands, the mark is written
with `synthetic: false` and the outlook reads stale from that instant — beside this demonstration,
not refused by it (§12, finding 1). The demonstration's stored *file name* is the digest of its
identity under the current rule; when provenance joined the key, that one file was renamed to the
new identity name and its bytes were not touched (§12).

## 4. The first outlook

`outlook-2026-11-system`, issued 2026-10-16T00:00:00Z, on the **month** horizon of billing month
2026-11 (the 26th of October to the 25th of November, 744 hours), targeting
`grid_raw.ext_pmr_lwap_final.lwap` — the public regional reference series, the first baseline
target of the [price target contract](../price-outlook/target-contract.md) — for `SYSTEM`. Its
values are the `seasonal_average_billing_month` baseline (PRICE-2, `price-2.1`) over that window.

**Why that baseline, and why that horizon.** The outlook is issued forward: its first hour is
after its issue instant. Of PRICE-2's three baselines only the seasonal average can serve a
forward billing month from this export, because it reads the same billing month of *earlier*
years — `2024-11`, `2023-11`, `2022-11` and `2021-11`, 124 samples over four seasons for every
hour — while persistence and `last week same interval` need recent weeks, and the export's last
hour is billing month 2026-08 (the embargo cutoff at the origin is 2026-10-25T00:00 local). The
run refused nothing: 744 of 744 hours were forecast. PRICE-2's record calls the seasonal average
the weakest of the three over the day and week horizons; this outlook therefore carries **no
skill claim** and inherits PRICE-2's own position that the archive and the register are the
product until a challenger beats the baselines. The month horizon is the cadence the ARCH-3
direction check measures between.

**The region is named here, not in the record.** `target_series_ref` is `{table, column,
version}` — the ARCH-1 shape — so the record cannot carry the region; it is `SYSTEM`, and the
values file names it (`"series": "SYSTEM"`). A reader of the archive alone must read the values
file's header for it. Recorded as a limitation, not worked around.

**The record as stored** (`<root>/outlooks/outlook-2026-11-system.json`, canonical one-line JSON,
1,040 bytes; pretty-printed here):

```json
{
  "assumption_ids": [
    "price:final_settlement_lmp",
    "price:regional_reference_series",
    "price:one_day_embargo",
    "rules:billing_month_clock",
    "rules:marked_months_never_filled"
  ],
  "content_digest": "24ef4704e5245886ebfea82dba5d02fa378e0a1d93e63e2f30d46e5380f59c7e",
  "horizon": {
    "end": "2026-11-25T16:00:00Z",
    "label": "month",
    "start": "2026-10-25T16:00:00Z"
  },
  "information_cutoff": "2026-08-25T16:00:00Z",
  "inputs": [
    {
      "digest": "b094bc47852a5982fdb02c15b297d1667978a021610dae4075005d3f19652054",
      "name": "lwap_final_hourly.csv"
    }
  ],
  "issued_at": "2026-10-16T00:00:00Z",
  "issuer": "Grid Nowcast executor seat (ARCH-3)",
  "kind": "OutlookRecord",
  "model_version": "seasonal_average_billing_month price-2.1",
  "outlook_id": "outlook-2026-11-system",
  "schema_version": "outlook.v1",
  "synthetic": false,
  "target_series_ref": {
    "column": "lwap",
    "table": "grid_raw.ext_pmr_lwap_final",
    "version": "final-bmonth-2026-11"
  },
  "values_ref": {
    "path_hint": ".local/outlook-archive/values/outlook-2026-11-system.json",
    "rows": 744,
    "sha256": "cb2144ac1312e275711e26a8b869b767ca7a73a597df1494946788c0a1043ae7"
  }
}
```

**The inputs, by digest.** `lwap_final_hourly.csv` —
`b094bc47852a5982fdb02c15b297d1667978a021610dae4075005d3f19652054`, 169,348 rows — is PRICE-2's
regional input, read by the same `verify_inputs` check PRICE-2's runner uses; that digest is the
one PRICE-2's record carries. PRICE-2's other input, `portfolio_nodal_hourly_deid.csv`
(`30ebab15…426d36`), is **not cited**: this outlook targets the regional series and does not rest
on the nodal export, and an inputs list that named a file the values never read would be a false
dependency. The values file (`cb2144ac…4ae7`, 744 rows) holds the forecast under `.local/`; no
value, node name or volume enters Git. `synthetic` is `false`, truthfully: the inputs are the real
exported settlement data and the model is PRICE-2's real baseline — this is the first real vintage
of an archive built from now on, which is what the owner's 2026-10-16 answer ("no archived
forecast vintage exists") asks for. It will be scoreable when billing month 2026-11 settles; no
receipt exists yet, and none can: `build_receipt` refuses a `scored_at` before the window closes.

## 5. The five register rows, and one integration fix

The register holds "every proposition the outlook rests on" (plan note), and the five rows above
are those propositions, entered with the same shape ARCH-2 fixed: a proposition, a family, a
layer, at least one verbatim citation, an interval and a check revision where a record states one
(here nothing states them, so both stay `null`, as they do for ARCH-2's rows), a state, an owner,
the code the value flows through, and a falsifier. Two are **accepted** — the owner answered both
on 2026-10-16 (`lmp` is the final settlement price, price-basis.md:81 and the plan note's "Open
with the owner"; the billing-month clock, price-basis.md:46) — and three are **deployed**, in
force in PRICE-2's built scorecard. All five are `unassigned` or `project owner`: no row is
promoted to fact, and no owner, interval or checked revision is invented.

**The integration fix.** ARCH-1's outlook validator required `assumption_ids` to match the
archive's file-name-safe identifier pattern, which has no `:`; ARCH-2's register ids are
`<family>:<slug>`; so the first outlook could not name a single register row. ARCH-1's own record
says what the field is for — "`assumption_ids` are its ids" (§9 of
[records.md](records.md)) — so the field's pattern now accepts the register's id form
(`ASSUMPTION_ID` in `src/outlook/records.py`), and only that field: `outlook_id` still doubles as
a file name and keeps the strict pattern, so nothing can escape the archive directory. One test
was added to `tests/test_outlook_records.py`; no existing test was weakened, and the three ARCH-1
acceptance items are untouched.

## 6. Direction check ARCH-3, as restated 2026-10-16

**The check that decides, restated 2026-10-16** — the guardian's page
[the problem and the thesis](../thesis-challenge-2026-10-16/problem-and-thesis.md), "Direction
checks, restated in pesos", carried into the plan note's
[direction checks](../price-outlook/intent.md) and into this task's acceptance: *the desk earns its
place if an accepted assumption change moves the portfolio impact past the stated materiality
threshold at least once in the scored months.* The deciding measurement is therefore **IMPACT-1's**
— the synthetic portfolio against the outlook price band and the contract price, per node and
horizon, with the materiality threshold stated before any change is scored (plan note; the thesis
page's IMPACT-1 line) — and it is **not this task's**, is not claimed here, and has no number yet.
What this task records is the mechanism (§3), the first outlook (§4), and the earlier count, which
under the restatement **stays recorded but no longer decides**. The first real pair — the pair the
count is read over, and the first months the deciding measurement is read over once they are
scored — is named below: **2026-11 → 2026-12**.

**The count, and what it is not.** `dependency.direction_share(first, second, marks)` records the
count: the denominator is the union of the assumption ids two month-horizon outlooks of one target
series cite; the numerator is the assumptions with a **real** mark (`synthetic: false`) whose
`marked_at` falls between the two issue instants; a demonstration never moves it; and a pair that is
not two *distinct* monthly outlooks of one series — an outlook compared with itself included — or
that is not strictly ordered (equal issue instants carry no interval to measure) is refused rather
than measured. Those last two refusals are the designated review's finding 2, fixed in §12.

**The single-vintage count today: 0 of 5 (0.0 %)** — an **open number**, read for exactly what it
is: the real changes among the five assumptions the one issued outlook cites, counted from the
archive's real marks, of which there are none. **It is not a monthly measurement and this record
does not claim one as fulfilled:** only one monthly outlook exists, so the pair the count is read
over does not exist yet, `direction_share` refuses a pair that does not exist, and the number stands
open until the second monthly issue lands. Nothing turns on reading it as a verdict — it no longer
decides — and the deciding measurement is IMPACT-1's, over the scored months. The count's own
earlier trigger was one change in ten — half an assumption of five — so a single real change among
the five would read 1 of 5 (20.0 %); that sensitivity is why the count is recorded rather than
leaned on, and why the measurement that decides waits for the **2026-11 → 2026-12** pair, the first
monthly pair this archive can hold (`outlook-2026-11-system` is the first vintage issued from now
on).

Two further readings, labelled so they cannot be confused with the count — both are
demonstrations of the counting rule, and neither is a monthly measurement:

* **The demonstration reading is 1 of 5 (20.0 %)** — the labelled demonstration mark in §3 moves
  a numerator by construction, not by evidence. It is not a real change and the check ignores it
  (`test_a_demonstration_change_never_moves_the_check`).
* **The register moved by five rows today** (37 → 42, its own construction by this task), which is
  a change to the register, not the monthly change the check measures.

## 7. Acceptance

| Acceptance item | Where it is proved |
|---|---|
| changing an accepted assumption marks dependent outlooks stale | `AcceptedChange.test_a_change_to_an_accepted_assumption_marks_the_outlook_stale` (the mark carries `assumption_state: accepted` and the outlook's exact digest), `test_two_outlooks_that_cite_it_are_both_marked`, `test_a_later_change_to_the_same_assumption_is_a_new_mark`, `test_a_change_no_outlook_cites_marks_nothing`, `test_an_unknown_assumption_is_refused_and_nothing_is_marked`, `test_the_same_change_for_the_same_outlook_is_refused_once`, `test_an_outlook_issued_after_the_marking_instant_is_left_alone`, `test_a_real_mark_of_the_same_change_stands_beside_its_demonstration` and `test_each_provenance_of_one_change_is_still_written_once` (§12, finding 1), and the real-archive reading in `FirstOutlook.test_the_first_outlook_is_not_stale_and_any_mark_on_it_is_labelled` |
| …without erasing them | `NothingIsErased.test_the_outlook_bytes_and_digest_are_unchanged_by_the_mark`, `test_the_marked_outlook_still_validates_and_still_carries_its_assumptions` (the archive's own `verify()` stays clean), `test_the_mark_is_stored_beside_the_outlook_not_on_it`, `test_a_tampered_mark_file_is_reported_by_the_store`, `test_a_mark_whose_outlook_is_gone_is_reported` |
| the first outlook cites PRICE-2 inputs by digest | `FirstOutlook.test_the_record_cites_the_price_2_export_by_digest` (the cited digest equals the SHA-256 of `.local/price/lwap_final_hourly.csv`), `test_every_assumption_the_record_cites_is_a_register_row`, `test_the_record_is_a_monthly_outlook_that_runs_forward_from_its_issue`, `test_the_packet_carries_the_record_as_stored` (this record's JSON block equals the stored record) |
| direction check ARCH-3 **as restated 2026-10-16**: the mechanism and the first outlook recorded, the single-vintage count stated as an open number, the monthly measurement assigned to IMPACT-1, the first real pair named | §6 quotes the restatement from its two sources, records the mechanism (§3) and the first outlook (§4), states today's count — **0 of 5 (0.0 %)**, the real changes among the five assumptions the one issued outlook cites — as an **open number**, and states plainly that the monthly measurement is **IMPACT-1's**, not this task's, and is left unfulfilled here: no second monthly outlook exists, so no pair and no monthly share can be produced, and §6 does not present the single-vintage count as the measurement. The first real pair is named: **2026-11 → 2026-12**. The recorder is `DirectionShare` (10 tests: the counting rules, the demonstration rule, and five refusals — not monthly, another target series, self-comparison, equal issue instants, unordered) |

## 8. Commands and results

Run from the worktree root with `/usr/bin/python3`, on this tree:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` (the brief's verify command, the full offline suite) | `Ran 1752 tests in 44.590s` / **OK (skipped=47)** |
| `/usr/bin/python3 -m unittest tests.test_outlook_dependency` | `Ran 56 tests` / **OK** |
| `/usr/bin/python3 -m unittest tests.test_outlook_records tests.test_outlook_register` | `Ran 119 tests` / **OK** (ARCH-1's 62, ARCH-2's 56, the one id-form test added here) |
| `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` | `OK: all changed files inside ARCH-3 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 93 tasks, 8 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 453 Markdown files, 2985 local links, 8 skills; bootstrap 1397 words.` **PASS** |
| `/usr/bin/python3 .local/briefs/arch3/issue_first_outlook.py` (the ignored helper that issued the record and ran the demonstration; not in Git) | the run below |

All six were then run again on the committed tree, `c3b9021`, with a clean `git status` (the
helper, which issues once, read its stored bytes back and found them identical): the suite
`Ran 1752 tests in 44.129s` / **OK (skipped=47)**, `plan.py scope ARCH-3 feat/price-outlook` OK,
`plan.py check` `OK: 93 tasks, 8 gates`, `repo.py check` **PASS** (453 Markdown files, 2985 local
links). At the branch tip, `7938b53` (the register addendum and this record's own note), the same
four read: `Ran 1752 tests in 45.368s` / **OK (skipped=47)**, scope OK, `plan.py check`
`OK: 93 tasks, 8 gates`, `repo.py check` **PASS** (453 Markdown files, 2986 local links).

The suite is the base count of 1695 on `016ae92` plus this module's 56 tests and the one added to
`tests/test_outlook_records.py`. The 47 skips are the repository's existing environment guards
(node, browser, Firestore emulator, wire and server-library classes), the same configuration other
lanes record; nothing in this task's paths skips — `FirstOutlook` ran here, because the runtime
archive and the PRICE-1 export are linked into `.local/`, and it skips with its own reason where
they are not.

The helper's output, trimmed to the lines that carry the record's facts (its values are price
values and are not quoted). This is the issuing run; the committed-tree run prints
`already issued; stored bytes equal the record built here`, `demo mark already stored:
STALE_DUPLICATE`, and the same verification lines:

```
input check: [{"file": "lwap_final_hourly.csv", "sha256": "b094bc47…52054", "rows": 169348}]
hours: 744 values: 744 detail: {'samples': 124, 'seasons': 4}
window: 2026-10-26T00:00:00 -> 2026-11-26T00:00:00
values: .local/outlook-archive/values/outlook-2026-11-system.json cb2144ac…043ae7
issued: ... "content_digest": "24ef4704…f59c7e" ...
walk: ... "unknown": [] ... five assumptions, each with its evidence refs
archive verify: {"outlooks": 1, "receipts": 0, "problems": []}
store verify: {"marks": 0, "problems": []}
stale before demo: ()
demo affected: ('outlook-2026-11-system',)
outlook bytes unchanged: True digest: 24ef4704…f59c7e
stale after demo: ()
demonstration outlooks: ('outlook-2026-11-system',)
store verify after demo: {"marks": 1, "problems": []}
archive verify after demo: {"outlooks": 1, "receipts": 0, "problems": []}
```

The digests are abbreviated in the block above and given in full in §3 and §4; the helper prints
them in full. A second run of the helper refuses to re-issue (the archive's own `OUTLOOK_IMMUTABLE`
rule) and reads the stored bytes back instead.

## 9. Rails and honest limits

* **No price values, node names or volumes in Git.** The forecast, the realized inputs and the
  scorecard stay under `.local/`; the record cites them by digest and row count, and this record
  quotes no value.
* **The demonstration mark is labelled** (`synthetic: true`), the real stale set is empty, and the
  first real change will be marked `synthetic: false` when it lands.
* **The first outlook carries no skill claim**, and its model is the weakest of PRICE-2's three on
  the horizons PRICE-2 scored; the values rest on four earlier seasons of one billing month.
* **The region is not in the record shape** (§4) and the values file carries it.
* **The direction check's number is an open count** until the second monthly issue, and it no longer
  decides (restated 2026-10-16, §6): today's 0 of 5 is the single-vintage count, not a month of desk
  change, and the measurement that decides is in pesos and is IMPACT-1's, over the scored months.
* **No clock, network, model or cloud call** exists in the module, the tests or the helper; every
  instant is supplied.

## 10. Self-review, and what a reviewer should probe

* **The marking path is enforced where the rule lives.** The link from a change to an outlook runs
  through the outlook's own `assumption_ids` (no second registry of dependencies), the mark binds
  the exact issued bytes, and the store refuses a duplicate by construction rather than by a scan.
  A reviewer should probe whether the "issued at or before the marking instant" boundary (the
  outlook issued after the change is not invalidated by it) is the right reading, and whether
  `assumption_state` should also gate the marking when a change lands on an assumption the
  register has marked `contradicted`.
* **Two readings are deliberately kept apart**: `stale_outlooks()` (real marks) and
  `demonstration_outlooks()`/`marks_of()` (all marks). The rule is ARCH-1's one-way provenance
  rule applied to marks; if a reviewer reads the plan note as requiring a mark to be real
  whenever an outlook is real, that is a one-line change and a reviewable one.
* **The direction check's number is the pair's numerator** (§6), not a monthly share; the second
  monthly issue is what completes it.
* **The register edit is additive and audited.** Five rows, each citation re-derived and
  re-checked; the audit's `missing`, `unknown`, `duplicates`, `dangling` and `unlabelled` lists
  stay empty, and the count pins in ARCH-2's tests moved 37 → 42 without weakening a check.
* **The `assumption_ids` pattern change** (§5) is the smallest change that lets an outlook name a
  register row; it is confined to that field, and the file-name rule for `outlook_id` is
  unchanged and still tested.
* **What is not claimed.** No skill, no scoring, no receipt: nothing has settled. No analyst or
  owner accepted the outlook itself — it is the seat's first vintage, and the archive is where a
  decision on it will be recorded.

## 11. Unfinished items and the exact next action

* The first receipt is a machine event: when billing month 2026-11 settles (the final statement
  arrives after the month closes), `build_receipt` and `append_receipt` score this outlook against
  the settled window. Nothing to do before then.
* DESK-1 is the reader: the register and the outlook on the event page, evidence → assumption →
  outlook → decision.
* The demonstration mark stays in the archive as a labelled demonstration; the first real change
  will be marked with `synthetic: false`. If the orchestrator prefers a clean real archive, the
  `stale/` directory can be emptied before the first real mark — nothing else reads it.
* The direction check's deciding measurement is **IMPACT-1's** (§6): the count this task records
  stays open until the archive's first monthly pair, **2026-11 → 2026-12**, and the measurement in
  pesos runs over the scored months at IMPACT-1's stated threshold. This task produces no number for
  it and claims none.
* Exact next action: the re-review of the reworked branch under `docs/work/reviews/ARCH-3.md` — the
  two important round-1 findings and the minor one are fixed and proved in §12, and the round-2
  escalate is answered by the guardian's restatement recorded in §13 — then IMPACT-1 (the monthly
  measurement it owns), DESK-1 or PRICE-3 as the orchestrator takes them.

## 12. Rework after the designated review

The designated review ([review record](../reviews/ARCH-3.md), GPT Sol, tip `a76f6d4`, 2026-10-16)
returned **rework** with two important findings and one minor. All three are fixed inside this
task's allowed paths. No acceptance text, frozen contract, review file or pre-existing test rule
was changed apart from the one test assertion named below; the task state stays `in_progress`.

### Finding 1 (important) — a demonstration could refuse the real mark of the same change

*What the review found.* A mark's file name was the digest of
`(assumption_id, new_revision, outlook_digest)` alone, so a stored demonstration and the real mark
of the identical change collided on the name: the real mark was refused `STALE_DUPLICATE` and
`stale_outlooks()` stayed empty — a labelled exercise could stop a real change from marking its
dependent outlook stale.

*The fix.* Provenance is now part of a mark's identity: the file name is the digest of
`(assumption_id, new_revision, outlook_digest, synthetic)` (`_key_of`, with its two call sites in
`_read_mark` and `StaleMarks.append`). One change with one provenance is still written once — the
`O_EXCL` refusal is unchanged — while a demonstration and a real mark of one change now stand as
two records in two files. Nothing was made rewritable: there is still no update, edit or delete
method, and the reader derives the name from the record's own fields, so a file under any other
name is refused `STALE_INVALID` rather than read under a name it does not own.

*Evidence, before and after.* `.local/briefs/arch3/rework_probe.py` (ignored, not in Git) drives
the review's own reproduction against the reviewed module
(`.local/briefs/arch3/reviewed_dependency.py`, extracted from `3f6afe3`) and against this tree:

```
[reviewed 3f6afe3] finding 1 (synthetic then real, identical triple): real mark refused: STALE_DUPLICATE; marks stored=1; stale_outlooks=()
[fixed]            finding 1 (synthetic then real, identical triple): real mark accepted, affected=('outlook-2026-11-system',); marks stored=2; stale_outlooks=('outlook-2026-11-system',)
```

*Regression tests.* `AcceptedChange.test_a_real_mark_of_the_same_change_stands_beside_its_demonstration`
(both records stored, both naming the outlook's exact digest, the outlook reads stale, the
demonstration stays labelled and out of the real set, the store's `verify()` clean with two marks)
and `test_each_provenance_of_one_change_is_still_written_once` (the same change with one provenance,
appended twice, is still refused `STALE_DUPLICATE` — once for each provenance).

*One existing test assertion changed.* `test_a_later_change_to_the_same_assumption_is_a_new_mark`
compared the stored revisions as `["016ae92", "beefbee"]` — file-name (hash) order, which the
identity change reorders and which was never a property of the store. It now asserts what that
test is about: both changes are stored, one mark each, both naming the outlook's exact digest. No
test was skipped, deleted or had a rule removed.

*The one stored mark.* The archive holds a single mark, the labelled demonstration from §3. Its
file was renamed from `35f36b17…089156.json` to `9a099908…74d719.json` — the digest of its identity
under the new rule — with its bytes untouched, by `.local/briefs/arch3/migrate_mark_identity.py`
(ignored, not in Git; it requires the old name to equal the old key, writes the same bytes under
the new name, re-reads them through `_read_mark`, and only then removes the old file):

```
stored marks: ['35f36b17a67a56e0a8df0cf15d8567b6da97ec80feeb17993f85fb681e089156.json']
moved: 35f36b17…089156.json -> 9a099908…74d719.json synthetic: True
store verify: {'marks': 1, 'problems': []}
marks: 1
stale outlooks: ()
demonstration outlooks: ('outlook-2026-11-system',)
```

Re-running the issuing helper on the migrated archive prints `demo mark already stored:
STALE_DUPLICATE`, `outlook bytes unchanged: True digest: 24ef4704…f59c7e`, `archive verify:
{"outlooks": 1, "receipts": 0, "problems": []}` and `store verify: {"marks": 1, "problems": []}`.
The real stale set is still empty: no accepted assumption has changed, so no real mark is written.

### Finding 2 (important) — the direction check accepted an outlook compared with itself

*What the review found.* `direction_share(o, o)` returned `share: 0.0`: the ordering guard
permitted equal issue instants, so one outlook compared with itself produced an unsupported
monthly result.

*The fix.* `direction_share` now requires two *distinct* outlooks — a pair sharing one
`outlook_id` is refused `NOT_MONTHLY`, because the archive never issues two records under one id —
and a strictly ordered pair (`start < end`, refused `NOT_ORDERED`), so the interval the numerator
is counted over is never empty.

*Evidence, before and after* (the same probe, its second line):

```
[reviewed 3f6afe3] finding 2 (direction_share(o, o)): accepted, share=0.0
[fixed]            finding 2 (direction_share(o, o)): refused: NOT_MONTHLY
```

*Regression tests.* `DirectionShare.test_an_outlook_compared_with_itself_is_refused` and
`test_two_outlooks_issued_at_the_same_instant_are_refused` (a twin issued at the first outlook's own
instant, refused in both directions). The counting tests and the four earlier refusals are
unchanged.

### Finding 3 (minor) — the acceptance table read the provisional count as the monthly measurement

*What the review found.* The acceptance table (§7) presented the single-vintage 0 of 5 as the
required monthly direction measurement.

*The fix.* §6 now separates the two: the recorded number is the real changes among the one issued
outlook's assumptions, explicitly *not* a pair measurement, and the row in §7 states that the
monthly measurement is **left unfulfilled** because the pair does not exist yet. No acceptance text
was changed — the item asks for the check recorded with its number, and the record now says plainly
what that number is and what remains pending.

### Commands and results

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` (the brief's verify command) | `Ran 1756 tests in 44.321s` / **OK (skipped=47)** (1752 at the build, +4 rework regressions; the same run on the tree before this section's own document edits read `Ran 1756 tests in 44.165s` / **OK (skipped=47)**) |
| `/usr/bin/python3 -m unittest tests.test_outlook_dependency` | `Ran 60 tests` / **OK** (56 at the build) |
| `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` | `OK: all changed files inside ARCH-3 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 93 tasks, 8 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 454 Markdown files, 2989 local links, 8 skills; bootstrap 1397 words.` **PASS** (2986 before this section's own links) |
| `/usr/bin/python3 .local/briefs/arch3/rework_probe.py` | the before/after block under finding 1 and finding 2 |
| `/usr/bin/python3 .local/briefs/arch3/migrate_mark_identity.py` | the migration block under finding 1 |
| `/usr/bin/python3 .local/briefs/arch3/issue_first_outlook.py` | the archive check lines under finding 1 |

Every command above was then run again on the committed rework tree, `57e810a`, with a clean
`git status`: the suite `Ran 1756 tests in 44.128s` / **OK (skipped=47)**, the module `Ran 60
tests` / **OK**, `plan.py scope ARCH-3 feat/price-outlook` OK, `plan.py check` `OK: 93 tasks, 8
gates`, `repo.py check` **PASS** (454 Markdown files, 2989 local links).

### Self-review of the rework

* The identity rule is enforced where the write happens: one `_key_of` computes the name, and both
  the writer and the reader derive it from the record's own fields, so a file under a name the
  record does not own is refused rather than read.
* The demonstration keeps its one-way provenance reading: visible through `marks_of` and
  `demonstration_outlooks`, never counted by `stale_outlooks` or `direction_share`.
* Nothing was invented for the pending monthly measurement: the check is recorded with the
  provisional numerator it has, and §7 leaves the monthly measurement unfulfilled.
* What a reviewer should probe: whether `NOT_MONTHLY` for the self-comparison and `NOT_ORDERED`
  for equal instants are the right codes, and whether renaming the stored mark (bytes identical)
  is the right treatment of a mark whose identity rule changed.

## 13. Rework, round 2 — the escalate and the guardian's restatement

The second designated review ([review record](../reviews/ARCH-3.md), GPT Sol, tip `6b0be8b`,
2026-10-16 19:03) returned **escalate**, with one important finding and one correction: the required
monthly direction-check number did not exist, a single-vintage count cannot demonstrate change
between monthly outlooks, and *"Guardian must resolve the timing mismatch through intent
clarification, or leave acceptance pending until a genuine second monthly outlook supports the
measurement. Do not substitute a fixture or provisional count."*

**The escalation is answered at the level it belongs to.** The guardian restated the check and this
task's acceptance was updated to the restatement before this round began — the orchestrator's
[rework decisions](../price-outlook/rework-2026-10-16.md), ARCH-3 row, and the acceptance item now
printed in `tasks.json`. **No acceptance text, intent, frozen contract or review file was changed by
this seat**, and the change below is inside the allowed paths; the seat's job this round is to make
the record say what the restatement says.

**The restatement, from its two sources.** [The plan note](../price-outlook/intent.md), "Direction
checks": *"ARCH-3, restated 2026-10-16: the desk earns its place if an accepted assumption change
moves the portfolio impact past the stated threshold at least once in the scored months; the
one-in-ten count stays recorded but no longer decides."* [The problem and the
thesis](../thesis-challenge-2026-10-16/problem-and-thesis.md), "Direction checks, restated in pesos",
says the same and gives IMPACT-1 the materiality threshold. §6 quotes both and draws the
consequences: the count this task records is an **open number**; the measurement that decides is
**IMPACT-1's**; the first real pair is **2026-11 → 2026-12**.

**What changed in this round, all of it documentation; no behaviour changed, so no test was added,
skipped or altered and the module's 60 cases stand:**

| Where | What it now says |
|---|---|
| §6 | retitled "as restated 2026-10-16": the deciding check and its IMPACT-1 assignment lead, `direction_share` is the recorder of the count, the 0 of 5 is an **open number** that no longer decides, and the first real pair is named |
| §7, row 3 | the row is the restated acceptance item, and states the count is open, the monthly measurement is IMPACT-1's and is left unfulfilled here, and the pair is named |
| §9 | the rails bullet reads "an open count … no longer decides", with the deciding measurement in pesos named as IMPACT-1's |
| §11 | an unfinished item records the IMPACT-1 assignment and the pair; the next action names the restatement |
| `src/outlook/dependency.py` | module docstring: the section is retitled "The direction check (ARCH-3, as restated 2026-10-16)" and states the restatement, the IMPACT-1 assignment and the pair, so a reader of the module alone cannot take the count as deciding; `direction_share`'s docstring carries the same note in one sentence. Imports, standards and behaviour unchanged |

**Deliberately not changed, and why.** `docs/work/outlook-archive/intent.md` is left as the dated
plan note it is (the header's line "it was not changed" stands): its line that ARCH-3 records "the
share of assumptions changed between monthly outlooks" remains true — the count *is* recorded — and
the note sits under the plan note that carries the restatement, so nothing there is superseded in
its own scope. The register, the issued outlook, the values file and the one stored mark were not
touched.

**Commands and results.** Run from the worktree root with `/usr/bin/python3`:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` (the brief's verify command) | `Ran 1766 tests in 90.036s` / **OK (skipped=47)** on the reworked tree; the same run on the tree at the tip `e0fe0e3` before these edits read `Ran 1766 tests in 65.822s` / **OK (skipped=47)** (the count is not comparable with the previous round's 1756: the base advanced under this branch). The 47 skips are the repository's existing environment guards, the same configuration the build and the previous round recorded |
| `/usr/bin/python3 -m unittest tests.test_outlook_dependency` | `Ran 60 tests in 0.048s` / **OK** — unchanged by this round (it is a documentation round) |
| `/usr/bin/python3 scripts/plan.py scope ARCH-3 feat/price-outlook` | `OK: all changed files inside ARCH-3 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 94 tasks, 8 gates` (the graph carried 93 tasks at the build; `IMPACT-1`, the task the restatement gives the measurement to, was registered on the base between `6b0be8b` and `cfbd7de`) |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 461 Markdown files, 3082 local links, 8 skills; bootstrap 1397 words.` **PASS** (3073 links before this round's links were added) |
| `/usr/bin/python3 .local/briefs/arch3/issue_first_outlook.py` (ignored helper; read-only when the record is already issued) | `input check: … b094bc47…52054 … rows 169348`; `values: … cb2144ac…043ae7`; `already issued; stored bytes equal the record built here`; `archive verify: {"outlooks": 1, "receipts": 0, "problems": []}`; `store verify: {"marks": 1, "problems": []}`; `stale before demo: ()`; `demo mark already stored: STALE_DUPLICATE`; `outlook bytes unchanged: True digest: 24ef4704…f59c7e`; `demonstration outlooks: ('outlook-2026-11-system',)`; both `verify()`s still clean |

The table is one uninterrupted run with the whole of §13 and the PROGRESS log row in the tree; the
rows' numbers are that run's. Every command was then run once more on the committed tree, `52327ae`,
with a clean `git status`: the suite `Ran 1766 tests in 91.176s` / **OK (skipped=47)**, the module
`Ran 60 tests in 0.049s` / **OK**, `plan.py scope ARCH-3 feat/price-outlook` OK, `plan.py check`
`OK: 94 tasks, 8 gates`, `repo.py check` **PASS** (461 Markdown files, 3082 local links).

The archive read-back is the same check §4 and §12 report: the record rebuilt from this tree's
bytes equals the stored one, so the documentation edits cannot have moved the archive or its
digests — as expected, since nothing on the issued path or the marking path changed.

**Self-review of round 2.**

* The record now says, in the first paragraph of §6, that the check that decides is IMPACT-1's and
  that the count is recorded but no longer decides; a reader cannot take 0 of 5 as the verdict.
* The count is still recorded faithfully, as an open number, with the pair it will be read over
  named; nothing was substituted for the missing measurement, which is the review's correction.
* The module carries the same statement, so the claim travels with the code and not only with the
  packet.
* What a reviewer should probe: whether leaving `docs/work/outlook-archive/intent.md` unchanged is
  the right reading of "no plan note changed", and whether the IMPACT-1 assignment is stated
  precisely enough for IMPACT-1's own packet to pick up.
