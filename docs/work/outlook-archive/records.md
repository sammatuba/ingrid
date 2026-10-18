# Outlook records: issued once, scored when prices settle (ARCH-1)

Task record, written 2026-10-16 by the ARCH-1 executor seat on branch `task/ARCH-1` from
`728f71a` (`feat/price-outlook`). No model call, no cloud call, no network and no clock: every
command below runs offline, and no price value, node name or portfolio volume appears in this
repository — a record cites its values file by path hint, digest and row count only.

**Read first, in the brief's order.** [AGENTS.md](../../../AGENTS.md);
[milestones](../milestones.md); [the price outlook plan note](../price-outlook/intent.md);
[`src/review/records.py`](../../../src/review/records.py);
[the ontology profile](../../architecture/ontology-profile-v1.md). The intent this task
implements is the plan note [the outlook archive and the assumption register](intent.md)
(orchestrator, `728f71a`), section "Records (ARCH-1, ARCH-2)"; its field list is followed
exactly and it was not changed.

## 1. What was built

| Path | What it is |
|---|---|
| `src/outlook/records.py` | The `OutlookRecord` and `ScoringReceipt` kinds: builders that seal a canonical `content_digest`, validators, and `OutlookArchive`, a directory-backed archive whose writes are once-only. Standard library only, plus the repository's own [`src/contracts/jsonutil.py`](../../../src/contracts/jsonutil.py) canonical JSON and digest. |
| `src/outlook/__init__.py` | The package marker, docstring only: no re-exports, so ARCH-2's `src/outlook/register.py` and ARCH-3's `src/outlook/dependency.py` are imported explicitly and neither has to edit this file. |
| `tests/test_outlook_records.py` | 62 tests, all offline: every refusal by code, the archive's issue-once behaviour, tamper evidence, and the stdlib-only check. |
| `docs/work/outlook-archive/records.md` | This record. |

Nothing else was touched: `src/review/records.py` (frozen, read for style only), the h0 kinds and
the API are unchanged, and no route or page reads the archive yet (that is DESK-1, after ARCH-3).

## 2. The outlook record

`build_outlook` takes the named fields and returns a sealed, validated record; `validate_outlook`
re-checks one envelope. The key set is closed — an invented key is refused, and so is a missing
one:

| Field | Shape | Rule |
|---|---|---|
| `outlook_id` | one path segment, `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` | doubles as the file name, so an id with `/` or a leading dot is refused |
| `issued_at`, `information_cutoff` | offset-bearing instant | `information_cutoff <= issued_at`: no outlook cites information from after it was issued |
| `horizon` | `{label, start, end}` | `label` is `day`, `week` or `month` (the price target contract's horizons); `start < end`; `issued_at <= start`, so the horizon runs forward from the issue |
| `target_series_ref` | `{table, column, version}` | the series the outlook targets, from [the target contract](../price-outlook/target-contract.md) |
| `inputs` | list of `{name, digest}` | at least one; names unique; each digest lowercase SHA-256 hex, the input file's bytes |
| `assumption_ids` | list of ids | at least one; unique; the register rows (ARCH-2) the outlook rests on |
| `model_version` | non-blank text | which model or baseline produced the values |
| `values_ref` | `{path_hint, sha256, rows}` | where the values live, by hint and digest and row count; the values never enter Git |
| `issuer` | non-blank text | who issued it |
| `synthetic` | boolean | declared truthfully, as the plan note's rails require |

Timestamps are offset-bearing instants; the builders write them in UTC `Z` form, so two records
that name the same instants have the same bytes and the same digest whatever offset the caller
typed. The validator accepts any offset and never rewrites what it checks.

## 3. The scoring receipt

`build_receipt(outlook, ...)` reads `outlook_id` and `outlook_digest` from the issued record, so a
receipt cannot name some other revision by accident. Fields:

| Field | Shape | Rule |
|---|---|---|
| `outlook_id`, `outlook_digest` | id and digest | the exact issued bytes it scores |
| `scored_at` | instant | `scored_at >= window.end`: the settled window is closed before the receipt is written, so "once prices settle" is a checked relation, not a claim |
| `final_series_version` | non-blank text | **the acceptance item**: it names the final series version the run was scored against; with `outlook_id` it is the receipt's storage key (§11) |
| `final_series_digest` | SHA-256 hex | that series export's bytes |
| `window` | `{start, end}` | the settled interval scored; it must lie inside the outlook's horizon — the whole predicted interval or any slice of it, never a window that reaches outside it (review finding 2, fixed in the [rework](#10-rework-after-the-designated-review-round-1)) |
| `metrics` | rows | one row per `(horizon, slice)`, no pair twice; `slice` is `market` or `ap` (administered-pricing intervals are a separate slice); `intervals >= 1`; `bias`, `mae`, `rmse`, `pinball_p10`, `pinball_p50`, `pinball_p90` are decimal strings, all non-negative except `bias` |
| `coverage` | `{scored, skipped}` | `scored >= 0`; each skipped entry is `{count >= 1, reason}` — a silent skip is not coverage |
| `synthetic` | boolean | declared truthfully; a receipt marked real is refused when it is linked to a synthetic outlook, so a fixture forecast can never be scored as if it were real, while a synthetic receipt may score either outlook (review finding 1, fixed in the [rework](#10-rework-after-the-designated-review-round-1)) |

The metric key set is closed to the six the [target contract](../price-outlook/target-contract.md)
fixes; a new metric is a reviewable change to this module, not a free-form row.

## 4. The archive: issued once, and the evidence when that is broken

`OutlookArchive(root)` holds `<root>/outlooks/<outlook_id>.json` and
`<root>/receipts/<outlook_id>.<version key>.json`. The root is a runtime directory
(`.local/outlook-archive/` for real records); nothing here writes into the repository tree.

- `issue(record)` validates first, then writes with `O_EXCL`. A second issue for the same
  `outlook_id` is refused (`OUTLOOK_IMMUTABLE`) and the stored bytes are unchanged; there is no
  update, edit, replace, amend or delete method on the class.
- `append_receipt(record)` re-reads the *stored* outlook, checks the receipt cites its digest, and
  writes it under its `(outlook_id, final_series_version)` pair's own file name with `O_EXCL`
  (`RECEIPT_DUPLICATE` if that pair's file already exists). The duplicate rule is the exclusive
  create itself — there is no scan a concurrent writer could pass (review round 2, §11). A
  different final series version — a corrected statement, later — is a new receipt, and two
  different outlooks may be scored against one series version.
- `verify()` re-reads every stored file and reports `{"outlooks", "receipts", "problems"}`. A
  record edited after issue fails its own digest (`ARCHIVE_TAMPERED`); an editor who recomputes
  the digest still breaks the receipts that cite the issued bytes
  (`OUTLOOK_DIGEST_MISMATCH`); a receipt whose outlook is missing is reported (`OUTLOOK_UNKNOWN`);
  a record stored under a file name other than its own key is reported (`ARCHIVE_TAMPERED`); and a
  stored receipt that contradicts its linked outlook — a real receipt on a synthetic outlook, or a
  window that reaches outside the predicted horizon — is reported as `RECEIPT_INVALID` on read, not
  only refused at write time.

What this does and does not claim, stated plainly: a digest proves the bytes did not change, not
that the outlook was any good, and a person with write access to the archive directory can always
edit a file — what the archive guarantees is that the edit is *visible* on the next read or
`verify()`, and that the API offers no path to change an issued record. Unknown input digests
stays unknown: nothing here fetches or invents the inputs themselves.

## 5. Decisions a reviewer should see

1. **A third record kind was not invented.** The plan note names two; the archive holds exactly
   those. Stale marks are ARCH-3's (`src/outlook/dependency.py`).
2. **`assumption_ids` must be non-empty.** An outlook that rests on no assumption has no basis to
   audit; the plan note's language ("which accepted assumptions by id") is read as at least one.
3. **`inputs` digests are file digests of the exported inputs** (for example PRICE-2's baseline
   inputs), the same lowercase hex convention the h0 records use; two digests forms would be a
   hazard, so `sha256:` prefixes are refused.
4. **Horizon labels are the target contract's** `day`/`week`/`month`, not free text, so ARCH-3's
   first outlook and PRICE-2's scorecard rows can be read against each other.
5. **UTC normalization happens at build time only.** A stored record keeps exactly what was
   issued; validation never rewrites content, which the tests pin.
6. **No clock is read anywhere.** Every timestamp is a caller-supplied field; the "once prices
   settle" rule is a relation between `scored_at` and the window, not a wall-clock check.
7. **The provenance rule runs one way** (added in the rework): a real receipt may not be linked to
   a synthetic outlook, and a synthetic receipt may score either outlook, because that receipt
   declares its own metrics are a fixture. Making the flags strictly equal would refuse the honest
   direction too; if a reviewer reads the plan note's "truthfully" as requiring equality, that is a
   one-line change and a reviewable one.

## 6. Commands and results

```sh
/usr/bin/python3 -m unittest tests.test_outlook_records
# Ran 56 tests in 0.025s — OK

/usr/bin/python3 -m unittest discover -s tests
# Ran 1539 tests in 48.619s — OK (skipped=47)

/usr/bin/python3 scripts/repo.py check
# Checked 436 Markdown files, 2831 local links, 8 skills; bootstrap 1397 words.
# PASS

/usr/bin/python3 scripts/plan.py check
# OK: 93 tasks, 8 gates

/usr/bin/python3 scripts/plan.py scope ARCH-1 feat/price-outlook
# OK: all changed files inside ARCH-1 allowed paths
```

Recorded honestly: the 47 skips are the repository's existing environment guards (node and
real-browser classes), unchanged before and after this task — the baseline run recorded for this
task, taken before any file changed, read `Ran 1483 tests … OK (skipped=47)`. One intermediate
suite run failed `tests/test_plan.py` on the PROGRESS/tasks.json state row while the two
co-edited files differed for a moment mid-update; both files are settled in this commit and the
final run above is green. These are the original round's numbers; the post-rework runs — 62 tests
in this module, 1545 in the suite — are in §10.

## 7. Acceptance

| Acceptance item | Where it is proved |
|---|---|
| an outlook cannot be edited after issue | `IssueOnce.test_second_issue_of_the_same_id_is_refused_and_changes_nothing` (bytes unchanged), `IssueOnce.test_the_archive_offers_no_mutation_entry_point`, and `TamperEvidence` — read and `verify()` reports an edit, digest recomputed or not |
| a scoring receipt names the final series version it was scored against | `ReceiptContract.test_receipt_names_the_final_series_version_it_was_scored_against`, `test_missing_or_blank_final_series_version_is_refused`, `test_final_series_version_must_be_named_wherever_the_record_is_read`, and the archive's duplicate rule `Receipts.test_the_same_final_series_version_is_scored_once` |
| stdlib only | `StdlibOnly.test_the_archive_modules_import_only_the_standard_library` parses the import lines of `src/outlook/records.py`, `src/outlook/__init__.py` and their one repository dependency `src/contracts/jsonutil.py` against `sys.stdlib_module_names` |

## 8. Self-review

Read against the plan note and the frozen contracts. Checked: the field lists match the plan
note's "Records (ARCH-1, ARCH-2)" section one for one; `src/review/records.py`,
`src/judgment/__init__.py`, the h0 kinds, the probe-bundle contract and working-paper section 5
are untouched; no new dependency, service, credential, clock or network call exists in the module
or the tests; no price value, node name or volume is written anywhere; every test that fails a
refusal asserts the stable code and the message table is closed. Two weak spots found in my own
pass and fixed: the receipt metric helper raised the outlook code instead of the receipt code, and
a redundant cross-check was unreachable because the other rules already imply it — both corrected
before this record was written. What a reviewer should probe: whether requiring one receipt per
`(outlook_id, final_series_version)` matches the plan note's "a scoring receipt" (read as once per
settled series version, many over time), and whether `assumption_ids` being non-empty is the right
reading while ARCH-2's register is still unbuilt.

## 9. Unfinished items and the exact next action

- The archive has no reader wired into any page or route: DESK-1 is where it appears.
- ARCH-2 builds `src/outlook/register.py` against this module's vocabulary (`assumption_ids` are
  its ids); ARCH-3 issues the first outlook from PRICE-2's inputs and marks dependents stale.
- Exact next action: ARCH-2 (assumption register records), or the independent review of this
  packet under `docs/work/reviews/ARCH-1.md`, whichever the orchestrator takes first.

## 10. Rework after the designated review (round 1)

The [designated review](../reviews/ARCH-1.md) (GPT Sol, independent, `df35a11`) returned **rework**
with two important findings; checklist rows 5 and 8 failed on the same two rules, and row 1 failed
only because the review sandbox has no writable system temporary directory, so the archive tests
could not execute there. Neither finding needed a frozen contract, the acceptance text or a plan
note changed; both are fixed inside `src/outlook/records.py` with new tests.

### What changed

1. **Finding 1, receipt provenance** (`_check_receipt_against_outlook`). The link rules now refuse
   a receipt whose `synthetic` is `False` when the outlook it cites was issued with
   `synthetic=True`, so a fixture forecast can never be scored as a real result. The rule runs one
   way on purpose: a receipt marked `synthetic` is honest about its own metrics and may score
   either outlook (decision 7 above). Tests: `ReceiptContract.test_a_real_receipt_cannot_score_a_synthetic_outlook`,
   `ReceiptContract.test_provenance_is_inherited_one_way`,
   `Receipts.test_a_real_receipt_cannot_be_appended_to_a_synthetic_outlook` (archive write path),
   `TamperEvidence.test_verify_reports_a_stored_receipt_that_contradicts_its_outlook` (read path).
2. **Finding 2, scoring window** (`_check_receipt_against_outlook`). Overlap (`a < d and c < b`)
   became containment (`c <= a and b <= d`): a scoring window is the whole predicted half-open
   interval or any slice of it, and a window that opens before the horizon or runs past its end is
   refused. Tests: `ReceiptContract.test_window_must_lie_inside_the_horizon_the_outlook_predicted`
   (both boundary violations, plus wholly before and wholly after),
   `ReceiptContract.test_the_horizon_edges_and_the_whole_horizon_are_scorable` (both edges and the
   whole horizon stay scorable), the retained
   `ReceiptContract.test_a_scored_window_can_be_an_inner_slice_of_the_horizon`, and
   `Receipts.test_a_receipt_whose_window_left_the_horizon_is_refused_by_the_archive`.
3. **Test scratch directory** (`scratch_directory()` in the test module). Checklist row 1 failed
   because the review sandbox mounts no writable system temporary directory; the helper keeps
   `tempfile.TemporaryDirectory` as the primary path and falls back to the ignored
   `.local/test-scratch/` inside the workspace when the system path cannot be created. This is a
   test-harness change only: the module, its guarantees and the offline/stdlib-only rules are
   unchanged (the fallback uses the already-imported `tempfile` and `Path`).

### Commands and results

The reproduction probe lives outside Git at `.local/arch1-rework-repro.py` (ignored, not
committed). It was run against the fixed worktree and, with `src/outlook/records.py` restored from
`df35a11` in a scratch copy, against the pre-fix module, so the before/after is measured, not
asserted:

```sh
/usr/bin/python3 .local/arch1-rework-repro.py          # fixed worktree
# REFUSED  finding 1: real receipt on a synthetic outlook: RECEIPT_INVALID
# REFUSED  finding 2: window 2026-01-01 -> 2027-01-01 on a 2026-10-17 one-day horizon: RECEIPT_INVALID
# ACCEPTED whole horizon window={'start': '2026-10-17T00:00:00Z', 'end': '2026-10-18T00:00:00Z'}
# ACCEPTED inner slice window={'start': '2026-10-17T12:00:00Z', 'end': '2026-10-17T13:00:00Z'}
# ACCEPTED synthetic receipt on a real outlook: synthetic=True
# ACCEPTED real receipt on a real outlook: synthetic=False
# exit 0

# the same probe with src/outlook/records.py at df35a11 in a scratch copy of src/
# ACCEPTED finding 1: real receipt on a synthetic outlook: unexpected -> synthetic=False window=...
# ACCEPTED finding 2: window 2026-01-01 -> 2027-01-01 on a 2026-10-17 one-day horizon: unexpected -> ...
# exit 1

/usr/bin/python3 -m unittest tests.test_outlook_records
# Ran 62 tests in 0.025s — OK

/usr/bin/python3 -m unittest discover -s tests
# Ran 1545 tests in 37.763s — OK (skipped=47)

/usr/bin/python3 scripts/plan.py check
# OK: 93 tasks, 8 gates

/usr/bin/python3 scripts/plan.py scope ARCH-1 feat/price-outlook
# OK: all changed files inside ARCH-1 allowed paths

/usr/bin/python3 scripts/repo.py check
# Checked 437 Markdown files, 2836 local links, 8 skills; bootstrap 1397 words.
# PASS
```

The 47 skips are the repository's existing node and real-browser environment guards, the same count
the pre-task baseline recorded.

### Acceptance, state and self-review

All three acceptance items still hold, with the same named tests as §7 plus the rework tests above;
no acceptance text, frozen contract, plan note or `docs/work/reviews/` file was touched. Self-review
of this rework: the two findings are fixed at their mechanism (the link rule, not a caller
convention), both are enforced on every path that reaches the link check — builder, archive append
and `verify()` on read — and each has a regression test pinned both to the builder and to the
archive. The one rule I chose to interpret narrowly is the provenance direction (decision 7): the
review's correction names only the false claim, so the symmetric case is allowed and documented as
the contestable point. State is `in_progress` in `docs/work/tasks.json` and
`docs/work/PROGRESS.md` (tasks.json required no edit: it already read `in_progress`); the row and
one new log entry are in the same commit as this rework on `task/ARCH-1`.

Next action: re-review of this packet under `docs/work/reviews/ARCH-1.md` (reviewer only; not
self-assigned), then ARCH-2 on the same vocabulary.

## 11. Rework after the designated review (round 2)

The [designated review](../reviews/ARCH-1.md) round 2 (GPT Sol, independent, `1afd1f0`) returned
**rework** with one important finding: receipt uniqueness was not atomic — duplicate detection
scanned existing receipts before writing a filename derived from receipt content, so two concurrent
receipts for one `(outlook_id, final_series_version)` pair could both pass the scan and write two
files. The orchestrator's [rework decision](../price-outlook/rework-2026-10-16.md) names the fix:
the exclusive storage key is the pair itself, written with `O_EXCL` on a name derived from it, plus
the concurrent regression test. No frozen contract, acceptance text or plan note changed; the fix
is inside `src/outlook/records.py` with new tests.

The overnight runner has since merged the first two commits into `feat/price-outlook` and rebuilt
this branch at that base `e10c5cc`; this rework is the single commit of `task/ARCH-1` on top of it.

### What changed

1. **The receipt's file name is its storage key** (`receipt_stem`, new). The name was
   `<content_digest>.json`, so two receipts for one pair with different bytes named two files and
   the duplicate rule had to be a scan of stored receipts — exactly the window the reviewer
   synchronized to get two same-version receipts accepted with two distinct exclusive-write paths.
   The name is now `<outlook_id>.<sha256 of the version text>.json`: one path per pair under every
   interleaving, and `append_receipt` no longer scans — the exclusive create it always did is the
   whole rule. The version is arbitrary text that may contain `/` or `..`, so it enters the name
   hashed; the identifier was already one safe path segment.
2. **Read and `verify()` check the same key.** `_read_record` now compares a receipt file's stem
   with `receipt_stem` of its own fields, so a receipt stored under a name that is not its pair is
   reported `ARCHIVE_TAMPERED`, the way a record edited after issue is already reported.

### Tests

| New test | What it pins |
|---|---|
| `ReceiptStorageKey.test_the_stem_names_the_pair_and_not_the_content` | one pair, one file whatever the bytes; another version, another file |
| `ReceiptStorageKey.test_a_version_text_stays_one_safe_path_segment` | `../../x`, `a/b`, `..` and a non-ASCII version each land as one file directly inside `receipts/` |
| `ReceiptStorageKey.test_a_second_receipt_for_a_pair_is_refused_whatever_its_bytes` | a well-formed second receipt for a scored pair is refused `RECEIPT_DUPLICATE`; one file stored |
| `ReceiptStorageKey.test_concurrent_appends_for_one_pair_leave_exactly_one_receipt` | 8 threads released together, different bytes each: exactly one stores, seven are refused `RECEIPT_DUPLICATE`, one file, `verify()` clean |
| `TamperEvidence.test_a_receipt_stored_under_another_name_is_reported` | a receipt copied to a name that is not its pair reads as `ARCHIVE_TAMPERED` |

`tests/test_outlook_records.py` is 67 tests (62 before), all offline; the round-1 tests are
unchanged except for the stored-name they compute.

### Commands and results

The before/after probe is `.local/arch1-rework2-repro.py` (ignored, not committed). It builds two
receipts for one pair with different bytes and, in the reviewed module, synchronizes both writers
at the scan — both read the empty store, then both write — and reports what was stored. Run against
the reviewed module `1afd1f0` (extracted under `.local/arch1-rework2/old/`; its `records.py` is
byte-identical to `git show 1afd1f0:src/outlook/records.py`, sha256 `0c7f5bc3…dd15`) it reproduces
the finding; against this worktree (`src/outlook/records.py`, sha256 `3c8e4583…d4f4`) it is
refused:

```sh
/usr/bin/python3 .local/arch1-rework2-repro.py --old --root .local/arch1-rework2/old
# writers=2 stored=2 refused=[] files=2
# writers share one storage key: False
# REPRODUCED: the scan race stores two receipts for one (outlook, version) pair
# exit 0

/usr/bin/python3 .local/arch1-rework2-repro.py
# writers=2 stored=1 refused=['RECEIPT_DUPLICATE'] files=1
# file names: outlook-2026-10-16-01.bd0d64bd…9ac3ca.json
# writers share one storage key: True
# REFUSED: the exclusive pair key admits exactly one receipt
# exit 0

/usr/bin/python3 -m unittest tests.test_outlook_records
# Ran 67 tests in 0.030s — OK

/usr/bin/python3 -m unittest discover -s tests
# Ran 1700 tests in 44.141s — OK (skipped=47)

/usr/bin/python3 scripts/plan.py check
# OK: 94 tasks, 8 gates

/usr/bin/python3 scripts/plan.py scope ARCH-1 feat/price-outlook
# OK: all changed files inside ARCH-1 allowed paths

/usr/bin/python3 scripts/repo.py check
# Checked 459 Markdown files, 3002 local links, 8 skills; bootstrap 1397 words.
# PASS
```

The suite reads 1,700 on base `e10c5cc`: the 1,695 of that base plus the five new tests here. The
47 skips are the repository's existing node and real-browser environment guards, the same count the
pre-task baseline recorded. The round-2 review could not execute the archive tests because its
sandbox has no writable temporary directory (system or workspace fallback) — recorded here as an
environment limit of that sandbox, not a property of this module; in a writable scratch directory
the module and the suite are green, and the suite was also run with the workspace fallback in
`.local/test-scratch/` during round 1.

### Acceptance, state and self-review

All three acceptance items still hold with the tests §7 names, unchanged: the outlook is issued
once and edit-visible (`IssueOnce`, `TamperEvidence`), the receipt names the final series version
and is stored once per pair (`ReceiptContract`, `Receipts`, `ReceiptStorageKey`), and the modules
stay stdlib-only (`StdlibOnly`). No acceptance text, frozen contract, plan note, review file or
file outside the allowed paths was touched (`plan.py scope` above). Self-review of this rework: the
finding is fixed at its mechanism — the storage key — so there is no check-then-write window left
to race, and the fix is enforced at the same three places the round-1 fixes were: the builder path
is untouched (the key is derived, not declared), the archive write is a single exclusive create,
and `verify()` checks stored names against their own fields as well as their digests. The
contestable point: the storage key uses the *pair*, not the cited outlook digest, so re-scoring
one outlook id after an impossible re-issue would collide — but re-issue is refused by
`OUTLOOK_IMMUTABLE`, so a pair has exactly one issue by construction. State stays `in_progress` in
`docs/work/tasks.json`. The `PROGRESS.md` row is unchanged (`in_progress`, matching tasks.json) and
this rework adds one log entry, in the same commit as this section.

Next action: re-review of this packet under `docs/work/reviews/ARCH-1.md` (reviewer only; not
self-assigned), then ARCH-3 issues the first outlook on this vocabulary.

## 12. Addendum (OUT-1, 2026-10-18): the optional `supersedes` key

Written by the OUT-1 executor seat. An `OutlookRecord` had no field naming the vintage it replaces
(the view's `supersedes` is derived by `scripts/grid/build_data.py` from issue order, not stored).
OUT-1 adds **one optional key**, `supersedes`, through this module: a record carries the §2 key set
exactly, or that set plus `supersedes`. A record without the key keeps its bytes and its digest, so
both vintages issued before the key existed read and verify as they did. The block names the
predecessor by id and digest, the stale marks, the changed assumption ids, the delta and the
confirmation reference; `OutlookArchive.issue` and `verify()` check it against the stored
predecessor (`check_supersedes`), and two codes join the closed table: `SUPERSEDES_INVALID` and
`REPEATS_PREDECESSOR`. The loop and the delta rule are in [reissue.md](reissue.md).
