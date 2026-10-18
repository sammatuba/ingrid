# ARCH-4: attribution of a miss as a record of its own beside the scoring receipt

Task record, written 2026-10-17 by the ARCH-4 executor seat on branch `task/ARCH-4` from
`23d837e9` (`feat/product-refine`, the same commit as `main`). Offline throughout: no model,
network, cloud, credential or clock call, and every instant below is a caller-supplied field.
The reviewed intent this task implements is [the attribution intent](attribution-intent.md)
(Claude Opus 5.5 in-session, two rounds, **accept** on `4a3f065`); it was built as written and
was not changed.

**Read first, in the brief's order.** [AGENTS.md](../../../AGENTS.md);
[milestones](../milestones.md); [the attribution intent](attribution-intent.md);
[the archive records](records.md) (ARCH-1); `src/outlook/records.py`, `src/outlook/dependency.py`;
[the first outlook](first-outlook.md) (ARCH-3); [the bake builder](../../../scripts/grid/build_data.py);
[the event page](../../../src/grid/event.js); [the desk record](../price-outlook/desk.md) (DESK-1);
[the 14 October strategy refresh](../strategy-refresh-2026-10-14/strategy.md);
[the dependency tests](../../../tests/test_outlook_dependency.py).

## 1. What was built

| Path | What it is |
|---|---|
| `src/outlook/records.py` | The `Attribution` kind: `build_attribution`, `validate_attribution`, `_check_attribution_against_records`, the content-derived `attribution_key`, `OutlookArchive.ATTRIBUTIONS`, `append_attribution`, `attributions(outlook_id=None)`, and `verify()` counting attributions, rebuilding each key (`ARCHIVE_TAMPERED` on a mismatch) and reporting a share sum above one per receipt (`SHARE_OVER_ONE` on the receipt's file). Standard library only, plus the repository's canonical JSON. |
| `src/outlook/dependency.py` | `walk` gains keyword arguments `receipts` and `attributions` and reports, per outlook, the receipts naming its exact issued bytes and their attributions grouped by cause — `{"receipt": {...}, "attributions": {"belief": [...], "signal": [...], "method": [...]}}`. `walk_archive` reads both from the archive. Every existing walk result field is unchanged. |
| `scripts/outlook/attribute.py` | **New, standard library, the first write path in the repository.** Reads a stored receipt by `--outlook-id` and `--final-series-version` from `--archive`; takes `--cause` and its reference (`--assumption-id`, `--signal-source`/`--available-at`/`--effective-at`, or `--method-ref`), `--statement`, `--attributed-by` (required), `--attributed-at` (required; no clock is read), `--share` and `--synthetic`; builds through `build_attribution`, appends, prints `key:` and `digest:`. It never issues or scores an outlook, calls no model, and refuses an unknown receipt. |
| `scripts/grid/build_data.py` | The outlook view gains `receipts` on an outlook that has a stored receipt: each receipt's own digest, final series version, scored instant, window and provenance, its `share_problem` (the archive's verify finding for that file) and its attributions as records. The view rebuilds on no receipt — the DESK-1/DESK-2 bytes stand — and the contract checks the new shape, the reference of each cause, the share range and the share-problem rule. |
| `src/grid/event.js` | `attributionSentence` / `receiptHtml`: one sentence per attribution composed from record fields (the statement, the cause and its reference, the share when present, the author, the attributed instant with its date in UTC, and the record's own `synthetic` flag), the receipt named by its own fields, and the archive's `SHARE_OVER_ONE` finding shown beside that receipt. An outlook with no receipt draws nothing new. |
| `src/grid/event.css` | Three muted rules for the receipt line, the attribution sentences and the share-problem line; no new colour. |
| `tests/test_outlook_attribution.py` | **New, 39 tests.** The record and its refusals, the store's exclusive key, tamper evidence, the share rule, the walk's grouping, the CLI end to end, the direction check and the stdlib-only rule. |
| `tests/test_outlook_records.py`, `tests/test_outlook_dependency.py` | The three exact `verify()` dictionaries gain `"attributions": 0`; every other assertion is unchanged. |
| `tests/test_grid_outlook.py` | **9 new tests** (58 from 49): the receipt-and-attribution view through the real builder, the share problem carried beside the receipt and the contract's refusal to quiet it, the empty-list refusal, the page source, the rendered sentences and the rendered share problem, and the real archive's zero receipts/attributions. |
| `docs/work/outlook-archive/attribution.md` | This record. |

Nothing else was touched: no route was added, `tests/test_cache_headers.py` is unchanged,
`events/<id>.json` is still copied byte for byte, and the register and the archive are read,
never written.

## 2. The record, field for field

`build_attribution(receipt, outlook, *, cause, statement, attributed_by, attributed_at,
synthetic, assumption_id=None, signal_ref=None, method_ref=None, share=None)` reads
`outlook_id`, `outlook_digest` and `receipt_digest` from the stored receipt — they are never
typed — seals the canonical `content_digest` and validates. The key set is closed and every key
is always present; an optional reference field is present as JSON `null` (the archive's
closed-key convention, ARCH-1), which is also what the key dict carries.

| Field | Shape | Rule, as implemented |
|---|---|---|
| `schema_version`, `kind` | fixed | `outlook.v1`, `Attribution` |
| `outlook_id`, `outlook_digest` | id, digest | read from the receipt; checked equal to the receipt's own and, through it, the stored outlook's |
| `receipt_digest` | digest | the exact receipt bytes this explains; checked equal to the stored receipt's `content_digest` |
| `cause` | one of `belief`, `signal`, `method` | closed; no other value, and the other two reference fields must be null |
| `assumption_id` | register id, null unless `belief` | a belief required it, and it must be one of the outlook's `assumption_ids` |
| `signal_ref` | `{source, available_at, effective_at}`, null unless `signal` | required for a signal; `available_at` strictly after the outlook's `information_cutoff` and at or before `attributed_at`; `effective_at` strictly before the receipt's `window.end` |
| `method_ref` | text, null unless `method` | required for a method; equal to the outlook's `model_version`, nothing else |
| `share` | decimal text in [0, 1], or null | written as a decimal string through `_decimal_text`; the record stores the caller's text (the receipt metrics' convention), so two spellings of one value are two records |
| `statement` | non-blank text | one sentence in the author's words |
| `attributed_by` | non-blank text | the validator checks no more than non-blank; "the author is a person" is a process rule and the CLI is the only write path |
| `attributed_at` | instant | at or after the receipt's `scored_at`; offset-bearing, normalized to UTC `Z` at build time |
| `synthetic` | boolean | inherited one way: a real attribution cannot sit on a synthetic receipt; a synthetic attribution may sit on either |
| `content_digest` | digest | sealed over the canonical bytes, as the other two kinds |

**Recorded readings, none of them silent deviations.** (1) The intent marks the three reference
fields "optional"; here "optional" is a null value in an always-present key, because every record
kind in this archive has a closed key set (`validate_outlook`, `validate_receipt`). (2) The key's
signal reference is the source and `available_at`, exactly as the intent's parenthetical lists
them; `effective_at` is not in the key, so two attributions that differ only in `effective_at`
are one identity and the second is refused `ATTRIBUTION_DUPLICATE` — a consequence of the
reviewed key rule, recorded here for the reviewer. (3) `share` is validated, not normalized: the
record stores the decimal string the author typed, so `0.5` and `0.50` are two records by the
same "two statements that differ in one word are two records" rule.

## 3. The key, and the store

`attribution_key(record)` is the SHA-256 of the module's `canonical_dumps` of the record's own
identity — `receipt_digest`, `cause`, `assumption_id`, the signal's `source` and `available_at`,
`method_ref`, `attributed_by`, `statement`, `synthetic` — with every absent reference present as
`null`, exactly the stale mark's `_key_of` pattern. The signal's fields are carried under
`signal_source` and `signal_available_at` in that dict; the shape is fixed in one function, so a
reader rebuilds it from the stored record.

`append_attribution(record)` validates, reads the stored outlook, finds the stored receipt the
attribution cites (a read of that outlook's receipts — the cross-record check needs the receipt
itself), checks the three-record rules, then writes `<root>/attributions/<key>.json` with
`O_EXCL`. **The duplicate rule is the exclusive create**: there is no sequence number, no "next"
to compute, and no scan of the attributions directory before the write. The only scan is the
read that resolves the cited receipt, which the intent's cross-record check requires.

`verify()` returns `{"outlooks", "receipts", "attributions", "problems"}`. For each stored
attribution it rebuilds the key from the file's own fields (a renamed or copied file is
`ARCHIVE_TAMPERED`), checks the cited receipt (`RECEIPT_UNKNOWN` when it is gone) and the
outlook, and then, per receipt, sums the shares it read: a sum above one is reported as
`<receipt file>: SHARE_OVER_ONE`. That is a problem of the desk's arithmetic, not evidence of an
edit, so the bake treats only that code as non-blocking (see §5) and shows it.

## 4. The write path

`scripts/outlook/attribute.py` is the person-driven command the intent calls the first write path
in the repository. It imports only the standard library and `src.outlook.records`, reads the
receipt from the archive by its `(outlook_id, final_series_version)` pair, builds through
`build_attribution`, appends through `append_attribution`, and prints the storage key and the
content digest. `--attributed-by` is `required=True`, so the command refuses to run without it
(exit 2); `--attributed-at` is required too, because no clock is read anywhere in this archive.
An unknown receipt is refused with its own message and exit 1; an invalid record is refused with
its `OutlookError` code and exit 1. It never issues or scores an outlook and never calls a model.

## 5. The baked view and the card

`price_outlook_document` reads the archive through `read_outlook_archive`, which now returns the
stored receipts and attributions and the verify findings. A `SHARE_OVER_ONE` line is the one
finding that does not stop the bake — the intent says the desk shows it beside the receipt — and
every other verify or marks problem still stops the build by name. An outlook with at least one
receipt gains `receipts`:

```json
"receipts": [{"receipt_digest": "…", "final_series_version": "…", "scored_at": "…",
              "window": {"start": "…", "end": "…"}, "synthetic": true,
              "share_problem": false,
              "attributions": [{"cause": "belief", "assumption_id": "…", "signal_ref": null,
                                "method_ref": null, "share": "0.2", "statement": "…",
                                "attributed_by": "…", "attributed_at": "…", "synthetic": true,
                                "content_digest": "…"}]}]
```

The entry is ordered by `scored_at` and each receipt's attributions by `attributed_at` (parsed,
the digest only a tie-break), so the same archive always bakes the same bytes. An outlook with
no receipt carries no `receipts` key at all — the DESK-1/DESK-2 view stands byte for byte and the
card shows nothing new. The page composes one sentence per attribution from those fields only:

> The synthetic unit was assumed available for the whole month. — belief, assumption
> availability:syn-bay-unit-2, share 0.2 of the miss; attributed by Fixture analyst at 27 Nov
> 2026 00:00 UTC (synthetic).

and shows *"The shares attributed to this receipt sum above one; the archive's verify reports
SHARE_OVER_ONE."* beside a receipt whose shares exceed one. The receipt itself is named by its
final series version, scored instant and record digest. The contract checks the new shape and
refuses a view whose `share_problem` disagrees with its own shares.

The real archive holds no receipt (no month has settled for an issued outlook), so the real
view carries no `receipts` key on any outlook and the card shows nothing new; that is pinned by
`tests/test_grid_outlook.py`'s `RealArchive.test_the_real_archive_carries_no_receipt_and_no_attribution`
and the rendered real-archive page test is unchanged.

## 6. Tests

`tests/test_outlook_attribution.py` (39) proves every invariant through the real builder and the
real archive on a labelled synthetic fixture: the sealed digest and closed keys; the closed
causes; each cause carrying its own reference and no other; a belief not among the outlook's
assumptions; a signal before the cutoff, after the statement, or effective at/after the window
end; a method that is not the model version; a share outside [0, 1] or not a decimal string; a
real attribution on a synthetic receipt; a wrong receipt digest (`RECEIPT_UNKNOWN`) and another
outlook's bytes (`ATTRIBUTION_INVALID`); a duplicate key and a one-word-different twin; a renamed
or copied file (`ARCHIVE_TAMPERED`); the share sum above one (stored, reported by `verify()`,
never refused at write); the walk's grouping; and the CLI (attaches and prints key and digest,
refuses without `--attributed-by`, refuses an unknown receipt, reads a signal reference, never
touches an outlook or a receipt, refuses the same statement twice, imports only the standard
library and the archive module).

`tests/test_outlook_records.py` and `tests/test_outlook_dependency.py` change exactly three
assertions: the two exact `verify()` dictionaries in the first and the one in the second gain
`"attributions": 0`. Nothing was deleted, skipped or weakened.

`tests/test_grid_outlook.py` (49 → 58) adds the view's receipt/attribution shape, the share
problem carried from `verify()` and the contract's refusal to quiet it, the empty-receipt-list
refusal, the page-source composition, the rendered sentences at the clean and over-one fixtures,
and the real archive's zero counts.

## 7. Direction check ARCH-4

The intent's check, recorded on delivery: the count of attributions in the real archive
(`.local/outlook-archive`) is **0**, expected because it holds no receipt; the count in the
fixture demonstration run by the tests is **3**, one per cause (belief, signal, method). The
first non-zero real count can come no earlier than the first scored month. Measured after this
task's own test run:

```sh
/usr/bin/python3 -c "from src.outlook.records import OutlookArchive; print(OutlookArchive('.local/outlook-archive').verify())"
# {'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}
```

and the fixture count is `Demonstration.test_one_attribution_per_cause_is_stored` (3) and
`DirectionCheck.test_the_fixture_demonstration_holds_one_attribution_per_cause` (3). Nothing
synthetic and no receipt or attribution was written into the real archive by this task or its
tests.

## 8. Commands and results

Run from the worktree root with `/usr/bin/python3` on this tree:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_outlook_attribution tests.test_outlook_records tests.test_outlook_dependency tests.test_grid_outlook` (the brief's verify command) | `Ran 225 tests in 2.521s` / **OK** |
| `/usr/bin/python3 -m unittest discover -s tests` (the full offline suite) | `Ran 2004 tests in 189.832s` / **OK (skipped=47)** |
| `/usr/bin/python3 -m unittest tests.test_outlook_attribution` | `Ran 39 tests in 0.810s` / **OK** |
| `/usr/bin/python3 -m unittest tests.test_outlook_records tests.test_outlook_dependency` | `Ran 128 tests in 0.229s` / **OK** |
| `/usr/bin/python3 -m unittest tests.test_grid_outlook` | `Ran 58 tests in 1.409s` / **OK** |
| `/usr/bin/python3 -m unittest tests.test_grid_data tests.test_grid_event` | `Ran 147 tests in 5.609s` / **OK (skipped=3)** |
| `/usr/bin/python3 -m unittest tests.test_grid_page tests.test_grid_catalog` | `Ran 153 tests in 26.636s` / **OK (skipped=5)** |
| `/usr/bin/python3 scripts/grid/build_all.py --data <fresh temporary directory>` then `... --check --data <same>` | write exit 0, check exit 0, `"violations": []` |
| `node --check src/grid/event.js` | exit 0 |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 98 tasks, 8 gates` |
| `/usr/bin/python3 scripts/plan.py scope ARCH-4 feat/product-refine` | `OK: all changed files inside ARCH-4 allowed paths` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 506 Markdown files, 3409 local links, 5 skills; bootstrap 1399 words.` **PASS** |

The 47 skips are the repository's existing environment guards (node, browser, Firestore emulator,
wire and server-library classes), the same configuration other lanes record. The archive's real
counts after the test run are the direction check's line above.

Every command in the table was then run again on the committed tree, `158b03f`, with a clean
`git status`: the verify command `Ran 225 tests in 1.389s` / **OK**, the full suite
`Ran 2004 tests in 218.199s` / **OK (skipped=47)**, `plan.py check` `OK: 98 tasks, 8 gates`,
`plan.py scope ARCH-4 feat/product-refine` `OK: all changed files inside ARCH-4 allowed paths`,
and `repo.py check` **PASS** (506 Markdown files, 3409 local links).

## 9. Acceptance

| Acceptance item | Where it is proved |
|---|---|
| the record matches the reviewed intent field for field and invariant for invariant; any deviation is written in the record as a hand-back, never silently | §2's table is the intent's table one for one; the three recorded readings are stated there, not hidden. The reviewer should judge whether the null-valued optional fields and the `effective_at` consequence are readings or deviations. |
| the key is rebuilt from the stored record and a renamed or copied file is reported `ARCHIVE_TAMPERED`; no sequence number and no scan before a write anywhere | `ArchiveWrites.test_a_renamed_or_copied_file_is_archive_tampered` (read and `verify()`), `Demonstration.test_each_stored_key_is_rebuilt_from_the_record`, `attribution_key` + `_read_record`; the duplicate rule is the `O_EXCL` create (`test_a_duplicate_key_is_refused_and_one_record_is_stored`); no sequence number exists in the module. The one read before the write resolves the cited receipt for the cross-record check (§3); the attributions directory is never scanned. |
| nothing synthetic and no receipt or attribution is written into `.local/outlook-archive`; `OutlookArchive(.local/outlook-archive).verify()` reports 2 outlooks, 0 receipts, 0 attributions, 0 problems after the task's own test run | §7's measured line; `DirectionCheck.test_the_real_archive_holds_no_attribution`, `RealArchive.test_the_real_archive_carries_no_receipt_and_no_attribution`, and the demonstrations run only under a temporary root with the workspace fallback. |
| every existing assertion in `tests/test_outlook_records.py`, `tests/test_outlook_dependency.py` and the three grid test files is kept; the full offline suite passes; `build_all.py --check` passes on a fresh bake into a temporary `--data` directory | §6 lists the three moved assertions (each still exact, now counting the new kind); the suite and the fresh-bake run are in §8. |
| the CLI refuses to run without `--attributed-by` and never calls a model; no new route; the card shows nothing new on the real archive (pinned by the real-archive test) | `CommandLine.test_the_command_refuses_to_run_without_the_author`, `CommandLine.test_the_command_never_issues_or_scores_anything`, `StdlibOnly` (imports only the standard library and `src.outlook.records`), `ThePageReadsTheBakedFile.test_no_route_was_added_for_the_file` (unchanged), `RealArchive.test_the_real_archive_carries_no_receipt_and_no_attribution`. |
| direction check ARCH-4 recorded with its two counts | §7: **0** in the real archive, **3** in the fixture, each with the test that reads it. |

## 10. Self-review, and what a reviewer should probe

* The record is built where the intent puts it: the builder reads the links from the receipt, the
  validator owns the record-only rules, and one cross-record function owns the rules that need all
  three records — every path that stores or reads an attribution goes through it.
* The key is derived from the record's own fields in one function, and both the writer and the
  reader compute it, so a file under any other name is refused rather than read. There is no
  sequence number and the duplicate rule is the exclusive create.
* The share rule is enforced where the intent puts it: not at write time (one create cannot see
  its siblings), in `verify()`, and on the card beside the receipt. The bake deliberately lets
  that one verify finding through; every other problem still stops it by name.
* The CLI is the only write path and is proven so: the module has no model path, the tests parse
  its imports, and nothing else in the repository calls `append_attribution`.
* **What a reviewer should probe:** (1) whether the null-valued optional fields are the right
  reading of "optional" (the alternative is an omitted key, which the archive's closed-key
  convention refuses); (2) whether leaving `effective_at` out of the key is right when the intent
  lists only source and `available_at` — two records differing only there collide by design; (3)
  whether the receipt-resolution read in `append_attribution` is compatible with "no scan before
  a write anywhere" (it is a required read for the cross-record check, not a duplicate test); (4)
  whether the card's extra "Receipt for final series …" line is the right way to show the share
  problem "beside the receipt" (the receipt is otherwise only a digest in the view).
* **Not claimed:** no attribution exists on a real receipt, no month has settled, and no skill,
  impact or decision claim is made anywhere. No page outside this task's paths was changed; the
  framework and foundation page updates the intent lists are the orchestrator's after the merge.

## 11. Unfinished items and the exact next action

* The first real attribution waits for the first scored month: a receipt for the 2026-11 outlook
  can be written once billing month 2026-11 settles, and only then can the CLI attach a statement
  to it. Nothing to do before then.
* The desk shows attributions on the event page; the orchestrator's page work (framework row 6
  and step 8, foundation sections 4 and 6, explainer Ideas 4) is after the merge and outside this
  task's paths.
* Exact next action: the independent review of this packet under `docs/work/reviews/ARCH-4.md`
  (reviewer only; not self-assigned), then, on accept, the merge of `task/ARCH-4` and the
  orchestrator's page updates.
