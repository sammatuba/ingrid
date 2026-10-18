# OUT-1 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Field | Value |
|---|---|
| Task | OUT-1: the issue and re-issue commands for the outlook archive |
| Branch | `task/OUT-1` (worktree `.local/wt/OUT-1`) |
| Commit under review | `b1a31599` |
| Base | `971885b0` (`origin/main` merged into the branch at `7d018902`; `origin/main` has since moved to `8d20c523`, BOOK-1, and the scope check is OK against both) |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author (the owner's rule of 17 October while the Codex seat has no credits) |
| Verdict | **accept** (four minor findings, two nits; no major finding) |

Interpreter `/usr/bin/python3`. No network, model or cloud call. The reviewer wrote only this file. Every
scratch archive lived in the session scratchpad, outside the repository. The real archive was read
only.

### What I verified by running

| Check | Result |
|---|---|
| `git diff 971885b0..HEAD`, read in full | 9 files: `src/outlook/records.py`, `src/outlook/reissue.py` (new), `scripts/outlook/issue.py` (new), `tests/test_outlook_reissue.py` (new), `docs/work/outlook-archive/reissue.md` (new), `records.md` §12, the task record `out-1.md`, `tasks.json`, `PROGRESS.md` |
| SHA-256 of every file under `.local/outlook-archive` (5 files), before my first command and after the full suite and my own runs | identical. The directory tree and the modification times are identical too, so no directory was created |
| `OutlookArchive('.local/outlook-archive').verify()` after the full suite | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`; `StaleMarks(...).verify(archive)` gives `{'marks': 1, 'problems': []}` |
| The two real vintages: stored `content_digest` against `compute_content_digest`, with the base `src` (`git archive 971885b0`) and with the head `src` | `outlook-2026-11-system` `24ef4704…` and `-v2` `f26f902e…` recompute unchanged under both; `validate_outlook` accepts both; the key set is exactly `OUTLOOK_KEYS`; a rebuild of each through the new `build_outlook` (no `supersedes`) gives the same digest |
| `/usr/bin/python3 scripts/plan.py check && /usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` (the verify command, the full offline suite) | `OK: 135 tasks, 9 gates`; `Ran 2661 tests in 201.871s`, **OK (skipped=115)**; no `FAIL` or `ERROR` line. No pypdf error: `.local/pylib` is linked in this worktree |
| `python3 -m unittest tests.test_outlook_reissue` | `Ran 37 tests`, OK, no skip |
| `python3 -m unittest tests.test_outlook_records tests.test_outlook_dependency` | `Ran 128 tests`, OK. Both files and `src/outlook/dependency.py` have no diff against the base |
| `python3 scripts/plan.py scope OUT-1 origin/main` and `... scope OUT-1 971885b0` | `OK: all changed files inside OUT-1 allowed paths` (both) |
| `python3 scripts/repo.py check` | `Checked 602 Markdown files, 3847 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check 971885b0..HEAD` | clean |
| `git status --short` in the worktree after all runs | clean |

**The delta by hand.** The fixture: previous 100, 200.5, 300, 400; new 110, 190.5, 330, 400. The
differences are 10, −10, 30, 0. The mean is 30/4 = 7.5, the mean absolute is 50/4 = 12.5, the
minimum is −10 and the maximum is 30. The test pins `7.500000`, `12.500000`, `-10.000000` and
`30.000000`. My own scratch run: previous 50, 60.25, 70, 80; new 55.5, 60.25, 65, 100.1. The
differences are 5.5, 0, −5, 20.1, so the mean is 20.6/4 = 5.15, the mean absolute is 30.6/4 = 7.65,
the minimum is −5 and the maximum is 20.1. The command printed `mean 5.150000, mean abs 7.650000,
min -5.000000, max 20.100000`, and the stored block carries the same figures and both values
digests.

**The whole loop through the command, on a scratch archive** (reviewer scripts `e2e.py` and
`e2e2.py` in the session scratchpad):

| Step or misuse | Result |
|---|---|
| first issue from a method record | exit 0; the stored keys are exactly the first-issue set |
| `dependency.mark_stale` (real mark), then `--from-stale mark.json --preview-out draft.json` | exit 0; the preview names the mark digest, `rules:billing_month_clock`, the predecessor id and digest, the method record by path and SHA-256, the cutoff and the delta; `not confirmed: nothing issued`; the archive holds one vintage |
| `--preview draft.json --confirm reviewer-confirmation-1` | exit 0; `supersedes` names `rev-v1` by digest, the mark, the changed belief, the delta and `confirmation_ref`; `verify()` gives 2 outlooks and no problems; the mark store verifies clean |
| the same confirmed issue again | exit 1, refused (`NOT_LATEST_VINTAGE` from the rebuild; the archive's exclusive create stands behind it) |
| a second re-issue of `rev-v1` under another id, run after the first | exit 1 `NOT_LATEST_VINTAGE` |
| misuse: no `--cutoff`; no `--method-record` | exit 2, argparse names the missing flag |
| misuse: `--cutoff` other than the method record's (direct and through `--preview`) | exit 1 `CUTOFF_MISMATCH` |
| misuse: preview edited after saving, not resealed | exit 1 `PREVIEW_INVALID` |
| misuse: preview edited and resealed: `delta` mean, a mark's `new_revision`, `predecessor.issued_at` | exit 1 `PREVIEW_STALE`, nothing written |
| misuse: preview edited and resealed: `outlook.issuer` or `outlook.outlook_id` | **exit 0, issued** (finding 1) |
| misuse: `--confirm ""` and `--confirm "   "` | exit 1 `CONFIRMATION_MISSING` |
| misuse: `--preview` without `--confirm`; `--preview` with another method file of the same content | exit 2; exit 1 `PREVIEW_STALE` |
| misuse: `--issued-at` before the predecessor's issue; after the horizon start | exit 1 `SUPERSEDES_INVALID`; exit 1 `OUTLOOK_INVALID` |
| misuse: a mark file against an archive whose store does not hold it | exit 1 `MARK_UNKNOWN` |
| equal values digests; the same hourly values in other bytes (the bytes differ, as checked); a first issue repeating the newest vintage | exit 1 `REPEATS_PREDECESSOR` in all three |
| a real method record re-issued from a demonstration mark | exit 1 `SYNTHETIC_ONE_WAY` |

**`verify()` against a tampered `supersedes` block** (the stored successor edited in place, then
restored): an edit without a reseal gives `ARCHIVE_TAMPERED`. A resealed wrong predecessor digest
gives `OUTLOOK_DIGEST_MISMATCH`. A resealed wrong previous values digest gives
`SUPERSEDES_INVALID`. A predecessor replaced after the re-issue gives `OUTLOOK_DIGEST_MISMATCH`, and
the module's test pins it. Resealed edits of the marks' assumption (to one the predecessor rests
on) and of `changed_assumption_ids`, of a delta figure, `confirmation_ref` set to null, or the whole
block removed: **no problem reported** (finding 2).

**Provenance one way.** At the preview (`SYNTHETIC_ONE_WAY`), at the records layer
(`_validate_supersedes` refuses a demonstration mark on a real record; `check_supersedes` refuses a
real successor of a synthetic predecessor), and through the command. A synthetic re-issue on all
four combinations issues and verifies clean (the test).

### Acceptance, line by line

| Acceptance line | Proved |
|---|---|
| nothing written into `.local/outlook-archive`; `verify()` reports 2 outlooks, 0 receipts, 0 problems after the test run | yes: the hashes, the tree and the modification times are identical before and after the full suite; `verify()` as quoted above |
| a re-issue names the stale mark, the previous vintage by digest and the changed assumptions | yes: the stored block, the preview, and the rebuild refuse a forged mark, a forged predecessor or forged changed beliefs (`MARK_UNKNOWN`, `PREDECESSOR_CHANGED`, `PREVIEW_STALE`) |
| the delta is computed from the two values files by digest and refused when the predecessor's digest is the same | yes: hand-recomputed twice; `VALUES_DIGEST_MISMATCH` on either file; `REPEATS_PREDECESSOR` on equal digests, at the preview, the records layer and the command. The all-zero refusal is stricter than the text and follows the strategy record ("a vintage that would repeat its predecessor is not issued"); I endorse it |
| the command refuses to run without an explicit cutoff and method record; synthetic inheritance one way as in the records module | yes: exit 2 for both missing flags in every mode; `CUTOFF_MISMATCH`; one way at both layers |
| every existing assertion in the touched test files is kept; the full offline suite passes; no live call | yes: no existing test file is touched; 2661 tests OK; the new modules import only the standard library and `src` (a test pins it), and I found no network, model or clock call except the one printed clock reading of `issue.py` when `--issued-at` is not given |

### Findings

1. **minor (record)**: `src/outlook/reissue.py:550-553`; the claims at
   `docs/work/desk-agent-and-book-2026-10-18/out-1.md:74` ("a stale or edited preview is refused")
   and `docs/work/outlook-archive/reissue.md:86` ("It does not trust the preview"). Acceptance line:
   a re-issue names the stale mark, the previous vintage and the changed assumptions (not broken).
   `issue_confirmed` rebuilds the preview with `outlook_id`, `issuer`, `method_record.path_hint` and
   `information_cutoff` taken from the preview itself, and derives everything else again. So a
   preview whose `outlook.issuer` or `outlook.outlook_id` is edited and resealed is a new valid
   preview, and the command issues it. Repro: my first scratch run issued `rev-v2` under the issuer
   "someone else" with `--confirm c`, and the second run also issued `rev-forged-id`. The
   mark, the predecessor, the changed beliefs and the delta cannot be forged this way: every such
   edit came back `PREVIEW_STALE`. On the command the file belongs to the person who confirms. The
   binding of a confirmation to one preview digest is DOCK-3's (hand-back 2). Correction: state in
   both places which four fields the preview supplies and that a resealed edit of them is a new
   preview. Add one test that pins that a resealed `issuer` edit issues, so the limit is recorded
   rather than found later.
2. **minor (record)**: `src/outlook/records.py:941-954` (the `verify()` loop) and
   `docs/work/outlook-archive/reissue.md:105` ("`verify()` repeats the check on read"). Acceptance
   line: a re-issue names the stale mark and the changed assumptions. `verify()` runs
   `check_supersedes`, which checks the link to the predecessor. It does not check the block's marks
   against the mark store, and it does not compute the delta again from the values files. Resealed
   edits pass: the marks' assumption changed to another belief of the predecessor, a delta figure,
   `confirmation_ref` set to null, or the block removed. This is the archive's existing threat model
   (records sealed by their own digest, cross-record links checked), and the issue path checks all
   of it before the write. Correction: one scope sentence in `reissue.md` ("verify re-checks the
   link to the predecessor, not the marks against the store or the delta against the files"). A
   re-issue verifier in `reissue.py` is an optional follow-on.
3. **minor**: `src/outlook/records.py:419`. Strategy decision 10; `reissue.md:85` ("no re-issue is
   written without a recorded decision"). The records layer accepts `confirmation_ref: null`, so
   `OutlookArchive.issue` writes a re-issue with no confirmation. Repro: the second scratch run,
   case C, stored `confirmation_ref: None` and `verify()` reported no problems. The rule is kept on
   the documented writer (`issue_confirmed` refuses a blank reference). The null exists only so that
   `validate_preview` can build the record in a dry run. Correction (optional): require text at the
   records layer, and let `validate_preview` pass a placeholder reference. If not, state in
   `reissue.md` that the rule lives in `issue_confirmed`.
4. **minor (hand-back 5, record only)**: `src/outlook/reissue.py:403-419` (`_predecessor`, the
   newest-vintage scan). A run after a re-issue is closed: I proved that a second re-issue of
   `rev-v1` gives `NOT_LATEST_VINTAGE`. What remains is a race between the scan and the exclusive
   create, on an archive that one person writes from a local checkout. It does not block. A cheap
   follow-on: `verify()` reports two successors that name one predecessor (a fork).
5. **nit**: `src/outlook/reissue.py:505-508`. The comment says that the predecessor's issue instant
   stands in for the issue instant. The code passes the candidate's `horizon.start`.
6. **nit**: `scripts/outlook/issue.py:144,157,167,173`. A relative `--method-record` path is read
   from the repository root (documented). `--from-stale`, `--preview` and `--preview-out` are read
   from the current directory, and the record does not say so. One line in the docstring is enough.

### Judgments the orchestrator asked for

**`--from-stale` previews, `--confirm` issues.** This is a sound reading, not a deviation.
Strategy decision 10 and the §2 answer ("an action that writes is executed only after the person's
confirmation, and the confirmation is recorded as the person's decision") require a confirmation
before any vintage is written. The `reissue_outlook` action takes the preview's draft id. The
brief's output line is met literally: `--from-stale <mark> --confirm <ref>` re-issues in one
command, with the supersedes block, the changed ids and the delta. Without `--confirm` the command
writes nothing, which is the confirmation rule.

**Hand-back 1 (OUT-3 cannot re-issue from the real archive).** The facts I read: both real vintages
rest on the same five beliefs, `price:final_settlement_lmp`, `price:regional_reference_series`,
`price:one_day_embargo`, `rules:billing_month_clock` and `rules:marked_months_never_filled`. Both
have the model `seasonal_average_billing_month price-2.1`. The one mark is a demonstration on
`rules:billing_month_clock` of the first vintage. The question that decides it: does OUT-3's
availability term **revise a register row among those five at a real revision**, or does it only
**add** beliefs and change the method?
- If it revises one, a real `mark_stale` is honest and the path that exists works. Note that it
  also marks the first vintage, and that mark previews as `NOT_LATEST_VINTAGE`, which is correct.
- If it only adds beliefs, no real mark is honest. A mark written only to open the path would be an
  invented record, which is a stop condition. Also, `check_supersedes` requires the changed beliefs
  to be among the predecessor's beliefs (`records.py:472`), so the block cannot express a new
  belief.

The strategy record's third vintage ("carries the availability term ... its values differ from the
second vintage by the stated delta") reads as the second case. **Recommendation: a
`--supersedes <id> --reason method_changed` path**, a small additive follow-on. The reason takes a
closed vocabulary (`belief_changed` needs marks; `method_changed` allows an empty mark list and
needs a `method_version` that differs from the predecessor's `model_version`). The delta,
`REPEATS_PREDECESSOR`, the newest-vintage rule, provenance and the confirmation stay as built. No
stored bytes move, because no real record carries the block yet. This is a gap between the brief
and the strategy for the orchestrator to settle, not an OUT-1 defect. Today OUT-3 could also issue
a third vintage on the first-issue path, as the second vintage was issued, but that vintage would
carry no stored link and no delta. Whichever path is chosen, OUT-3 needs
`tests/test_outlook_reissue.py` granted (hand-back 6) to move the three real-archive pins.

**Hand-back 5 (no concurrency guard)**: minor, not blocking (finding 4).

**Hand-back 7 is a calendar fact for now.** The existing rule `issued_at <= horizon.start` closes
the November 2026 issue window at 2026-10-25T16:00Z, one week from this review. The hand-back 1
path and OUT-3 must land before then, or the third vintage cannot be issued for November.

**Copy rules.** They do not apply. The diff has no public screen and no plain-language page
(`docs/routes.json` `plain_language.pages` does not list `docs/work`). `repo.py check` PASS is the
prose gate that applies.

### Verdict

**Accept.** Every acceptance line is proved by a check I ran. The real archive is byte-identical
and verifies at 2 outlooks, 0 receipts, 0 attributions and 0 problems. The real vintages' digests
recompute unchanged. The full offline suite is 2661 tests OK (skipped=115). Scope, plan, repo and
diff checks pass. No major finding stands.

Follow-ups for the orchestrator. None of them blocks `done`; they can be one small record commit:
1. Finding 1: correct `out-1.md:74` and `reissue.md:86` to name the four fields the preview
   supplies, and add the one pinning test for a resealed `issuer` edit.
2. Finding 2: add the one scope sentence on `verify()` to `reissue.md`.
3. Finding 3: either require text for `confirmation_ref` at the records layer, or state that the
   rule lives in `issue_confirmed`.
4. Decide hand-back 1 (recommended: `--reason method_changed`) and grant OUT-3
   `tests/test_outlook_reissue.py`, before 2026-10-25T16:00Z.

## Round 2 (Claude Opus 5.5 in-session subagent, read-only, independent; 2026-10-18)

| Field | Value |
|---|---|
| Task | OUT-1 (rework round 1) |
| Branch | `task/OUT-1` (worktree `.local/wt/OUT-1`) |
| Commit under review | `48e5cad9` (rework `28e93c64`, merge of `origin/main` `8d20c523` at `a8bbf7f6`, record `48e5cad9`) |
| Base | `b1a31599` (round 1) for the rework; `origin/main` `8d20c523` for scope |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author |
| Verdict | **accept** (one minor finding, not blocking) |

I read `git diff b1a31599..48e5cad9` in full. For OUT-1 that is `src/outlook/records.py`,
`src/outlook/reissue.py`, `scripts/outlook/issue.py`, `tests/test_outlook_reissue.py`,
`reissue.md`, `out-1.md`, `PROGRESS.md` and `tasks.json`. The BOOK-1 files arrive through the merge
and are not reviewed here. Interpreter `/usr/bin/python3`. No network, model or cloud call. The only
file I wrote is this one. Every scratch archive lived in the session scratchpad.

### What I verified by running

| Check | Result |
|---|---|
| SHA-256 of the 5 files under `.local/outlook-archive`, before round 2 and after the full suite and my runs | identical to each other and to round 1; the tree and the modification times are identical |
| `OutlookArchive('.local/outlook-archive').verify()` before and after the full suite | `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}` both times; the mark store gives `{'marks': 1, 'problems': []}` |
| `plan.py check && unittest discover -s tests -p "test_*.py"` | `OK: 135 tasks, 9 gates`; `Ran 2707 tests in 251.113s`, **OK (skipped=115)**; no `FAIL` or `ERROR` line |
| `unittest tests.test_outlook_reissue` / `test_outlook_records test_outlook_dependency` / all three | 47 OK / 128 OK / 175 OK; the records and dependency tests and `dependency.py` still have no diff against `971885b0` |
| Existing assertions of `test_outlook_reissue.py` | kept: the round-1 tests change only their call site (`fixture.confirm`, which passes the four caller-stated values) and the command loop's argument order; every assertion stands |
| `plan.py scope OUT-1 origin/main` | `OK: all changed files inside OUT-1 allowed paths` |
| `repo.py check` | `Checked 605 Markdown files, 3852 local links, 5 skills; bootstrap 1399 words. PASS` |
| `git diff --check b1a31599..HEAD` and in the worktree | clean |

**The round-1 misuse table again, through the command** (reviewer script `e2e3.py`):

| Case | Result |
|---|---|
| no `--cutoff`; no `--method-record`; `--preview` without `--outlook-id` | exit 2 |
| cutoff not the method record's | exit 1 `CUTOFF_MISMATCH` |
| preview edited, not resealed | `PREVIEW_INVALID` |
| resealed `issuer` edit; resealed `outlook_id` edit (the run states its own) | **`PREVIEW_MISMATCH`** (round 1: issued) |
| resealed `issuer` edit, the run states that same issuer (`--dry-run`) | passes: the person who confirms states the issuer, which is the intended rule |
| resealed delta edit | `PREVIEW_STALE` |
| resealed `reason` edit to `method_changed`, marks kept | `PREVIEW_INVALID` |
| resealed: marks dropped and reason `method_changed`, same method version | `METHOD_UNCHANGED` |
| `--confirm ""`, `--confirm "   "` | `CONFIRMATION_MISSING` |
| `--preview` without `--confirm` | exit 2 |
| `--preview` with another method file of the same content | `PREVIEW_MISMATCH` |
| issued before the predecessor | `SUPERSEDES_INVALID` |
| a mark not in this archive's store | `MARK_UNKNOWN` |
| the confirmed issue | exit 0; block `reason: belief_changed`, `confirmation_ref` kept, delta `5.150000` as in round 1; `verify()` clean |
| a second re-issue of `rev-v1`, from the mark and mark-free | `NOT_LATEST_VINTAGE` both |
| `verify()` on a resealed stored successor: `confirmation_ref` null; reason unknown; `method_changed` or `inputs_refreshed` with nothing changed | `ARCHIVE_TAMPERED`; `ARCHIVE_TAMPERED`; `SUPERSEDES_INVALID`; `SUPERSEDES_INVALID` |

**The mark-free path:**

| Case | Result |
|---|---|
| `--supersedes` without `--reason`; `--reason` without `--supersedes`; `--reason belief_changed` | exit 2 (all three) |
| `belief_changed` without a mark: preview API; records layer | `REASON_INVALID`; `OUTLOOK_INVALID` |
| `method_changed` with the same method version | `METHOD_UNCHANGED` (and `SUPERSEDES_INVALID` at the archive, pinned by a test) |
| `inputs_refreshed` with the same input digests | `INPUTS_UNCHANGED` |
| unknown predecessor id | `PREDECESSOR_UNKNOWN` |
| `method_changed` whose values file is the predecessor's | `REPEATS_PREDECESSOR` |
| `method_changed` preview | `reason: method_changed`, `changed assumptions: none`, the delta as hand-computed in round 1 (mean 5.15, mean abs 7.65, min −5, max 20.1) |
| resealed `issuer` edit of a mark-free preview | `PREVIEW_MISMATCH` |
| blank confirmation | `CONFIRMATION_MISSING` |
| confirmed `method_changed` | exit 0; block `method_changed`, `[]` marks, `[]` changed ids, the reference; `verify()` clean |
| `inputs_refreshed`, a new input digest, the same method version | exit 0; `verify()` clean |
| a record built directly with `reason: method_changed` and a mark list, through `OutlookArchive.issue` | **written; `verify()` reports nothing** (finding R2-1) |

### Round-1 findings against the code

1. **Finding 1: closed.** `issue_confirmed` takes `outlook_id`, `issuer`, `method_record` and
   `cutoff` from the confirming call, refuses a preview that names others with `PREVIEW_MISMATCH`,
   and rebuilds the preview with the caller's values. The command makes `--outlook-id` and
   `--issuer` required in every mode. The claims in `out-1.md` §4 and `reissue.md` step 4 are
   corrected, and two tests pin the refusal (the API, and the command loop).
2. **Finding 2: closed.** `reissue.md` now states the scope of `verify()`: the link to the
   predecessor, not the marks against the store or the delta against the files.
3. **Finding 3: closed.** `_validate_supersedes` requires non-blank text for `confirmation_ref`.
   `validate_preview` builds its check record with the labelled `PREVIEW_CHECK_REF`. The real
   vintages carry no block, so their bytes still validate (pinned read-only).
4. **Finding 4 (hand-back 5): stands as recorded,** not blocking.
5. **Nits 5 and 6: closed** (the comment, and the path rules in the docstring and the help).

### Finding of round 2

R2-1. **minor**: `src/outlook/records.py:418`, against `src/outlook/reissue.py:548` and the claim
at `docs/work/outlook-archive/reissue.md:71` ("a mark list cannot travel with the other two
reasons"). The rule bears on the orchestrator's decision (the mark-free path is "without a mark")
and on the round-1 finding 3 principle (the records layer holds what the writer holds). The preview
requires marks exactly when the reason is `belief_changed`. The records layer requires marks for
`belief_changed`, but it does not refuse marks for `method_changed` or `inputs_refreshed`. Repro: a
record built directly with `reason: method_changed`, one mark digest that no store holds and
`changed_assumption_ids: ["rules:billing_month_clock"]` passes `build_outlook`. `OutlookArchive.issue`
writes it, and `verify()` reports no problem. The documented writer (`issue_confirmed`, through
`validate_preview`) cannot produce it. Correction (one line): write the records-layer rule as
`bool(marks) == (block["reason"] == "belief_changed")`, and add one test. Not blocking.

Note for the merge: `out-1.md` links `../reviews/OUT-1.md`, and this record is not yet committed on
the branch. Commit it with the merge, or the link breaks on a clean checkout.

### Judgment: `inputs_refreshed` (another input digest, the same method allowed)

**A sound reading.** The orchestrator's note said "a different method version" for the mark-free
path. Applied to `inputs_refreshed`, that rule would refuse what the reason names. The real history
is the case: the second vintage re-issued the first with the same model
(`seasonal_average_billing_month price-2.1`), a refreshed input and a later cutoff, and no belief
changed. The rule compares the name-to-digest map of the inputs, so something recorded must have
moved. The delta and `REPEATS_PREDECESSOR` still refuse a refresh that changes no value. Both
reasons refuse a re-issue in which only the cutoff moved, with the same inputs and the same method.
That is correct: different values from identical recorded inputs and method would mean that
something unrecorded changed. A renamed input counts as a refresh. This is acceptable, because the
digest map is what the record cites.

### Verdict

**Accept** for `48e5cad9`. Every acceptance line still holds on a check I ran. The real archive is
byte-identical and verifies at 2/0/0/0 before and after the full suite. The full suite is 2707 tests
OK (skipped=115). The three outlook modules are 175 OK. The scope, plan, repo and diff checks pass.
Round-1 findings 1 to 3 and both nits are closed. The orchestrator's decision on hand-back 1 is
implemented, at both layers for the reason rules. One minor finding remains (R2-1, a one-line
records-layer tightening plus a test); it can go in a follow-on commit and does not block `done`.
