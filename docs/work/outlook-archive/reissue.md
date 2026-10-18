# The re-issue loop: mark, preview, confirm, issue (OUT-1)

Written 2026-10-18 by the OUT-1 executor seat on `task/OUT-1`. The decision this record implements is
the [strategy record](../desk-agent-and-book-2026-10-18/strategy.md), section 2 ("Can a decision move
the outlook honestly?"), decision 4, and the `mark_stale` and `reissue_outlook` actions of section 3;
the dock's side is the [agent contract](../desk-agent-and-book-2026-10-18/agent-contract.md)
(`draft(reissue)`, `reissue_outlook`, the confirmation record). The task record is
[out-1.md](../desk-agent-and-book-2026-10-18/out-1.md).

Before OUT-1 no command issued a vintage: the two vintages in `.local/outlook-archive` were issued by
hand through `OutlookArchive.issue`. After it, a vintage is issued by
[`scripts/outlook/issue.py`](../../../scripts/outlook/issue.py) from a method record, and a re-issue
runs the loop below. The code is [`src/outlook/reissue.py`](../../../src/outlook/reissue.py) and one
optional key of the outlook record in [`src/outlook/records.py`](../../../src/outlook/records.py).

## The loop

| Step | Record | Who writes it | Where |
|---|---|---|---|
| 1. mark | `StaleMark` (ARCH-3, exists): the changed assumption, the revision, the marked vintage's exact bytes, the provenance | `dependency.mark_stale`, on a belief change (the dock's `mark_stale` action, confirmed); no mark for a method change or an input refresh (see "A re-issue without a mark") | `<archive>/stale/` |
| 2. preview | `ReissuePreview` (OUT-1): what the re-issue will write | `reissue.build_preview` (the dock's `draft(reissue)`; the command without `--confirm`) | nowhere in the archive: the dock's draft in the person's private copy, or the command's `--preview-out` file |
| 3. confirm | the person's confirmation (DOCK-3's `Confirmation`, state `confirmed`), or the reference a person gives `--confirm` | the person, one click or one flag | DOCK-3's store; its id travels into step 4 |
| 4. issue | `OutlookRecord` with `supersedes` | `reissue.issue_confirmed`, called by the command and by the dock's `reissue_outlook` | `<archive>/outlooks/<id>.json`, written once |

Nothing in steps 1 to 3 writes an outlook. Step 4 is the archive's existing exclusive create; there
is no new write path into the archive.

## Step 2: the preview

`build_preview(archive, marks, method_record_path, outlook_id=, issuer=, cutoff=)` reads:

- **the marks**, each of which must be stored in the archive's own mark store (found by its
  `content_digest`; a mark file copied from elsewhere or edited is `MARK_UNKNOWN`), and all of which
  must name one vintage's exact bytes (`MARKS_DISAGREE`);
- **the predecessor**, the vintage the marks name, which must still be stored with those bytes
  (`PREDECESSOR_CHANGED`) and must be the newest issued vintage of its target, same series table and
  column and same horizon (`NOT_LATEST_VINTAGE`: a changed belief marks every vintage resting on it,
  and the answer is to re-issue the current one);
- **the method record**, with the command's explicit cutoff, which must be the record's own
  (`CUTOFF_MISMATCH`); every input and the values file are re-read and compared with their digests
  (`INPUT_DIGEST_MISMATCH`, `VALUES_DIGEST_MISMATCH`); the method must predict the predecessor's
  series and horizon (`TARGET_MISMATCH`).

The preview record has a closed key set and a sealed `content_digest`:

| Key | What it holds |
|---|---|
| `predecessor` | `outlook_id`, `outlook_digest`, `values_digest`, `issued_at` |
| `reason` | `belief_changed` (from marks), `method_changed` or `inputs_refreshed` (without a mark) |
| `stale_marks` | per mark: `content_digest`, `assumption_id`, `new_revision`, `marked_at`, `synthetic` |
| `changed_assumption_ids` | the marks' assumptions, sorted, each once; empty without a mark |
| `method_record` | `path_hint`, `sha256`, `method_version` |
| `information_cutoff` | the method record's cutoff (the command's `--cutoff`) |
| `outlook` | the candidate vintage: every field the issue writes except `issued_at` and `supersedes` |
| `delta` | the delta block (below) |

`validate_preview` checks the shape, the digest and that the parts agree with each other, and it
builds the vintage the preview would write and runs the archive's own validator on it.

## A re-issue without a mark (rework round 1)

A method change (OUT-3's availability term) or an input refresh changes no belief the predecessor
rests on, so no stale mark is honest. The orchestrator's decision of rework round 1 adds a second way
to name the predecessor: `build_preview(..., supersedes=<outlook id>, reason=...)`, on the command
`--supersedes <outlook id> --reason method_changed | inputs_refreshed`.

- `method_changed` needs a method version that differs from the predecessor's `model_version`
  (`METHOD_UNCHANGED`); `inputs_refreshed` needs an input digest that differs (`INPUTS_UNCHANGED`).
  The records layer holds the same two rules (`SUPERSEDES_INVALID`).
- The mark list and `changed_assumption_ids` are empty; `belief_changed` still needs at least one
  mark, and a mark list cannot travel with the other two reasons (`REASON_INVALID` at the preview;
  the records layer holds the same rule on its own, `OUTLOOK_INVALID`, since rework round 2).
- The delta, `REPEATS_PREDECESSOR`, the newest-vintage rule (`NOT_LATEST_VINTAGE`), provenance and
  the confirmation are unchanged. A predecessor id that is not issued is `PREDECESSOR_UNKNOWN`.

## The delta rule

The two values files are read by digest: the predecessor's at its `values_ref.path_hint` against its
`values_ref.sha256`, the new one at the method record's `values.path` against `values.sha256`.

1. Equal digests: refused `REPEATS_PREDECESSOR` before anything else is read.
2. Both files must carry the same `hour_start` set, and the same `series` header when both name one
   (`HOURS_MISMATCH`).
3. Per hour, `new - previous` on the point `value`. If every difference is zero the file differs only
   outside the hours (a header moved), and the vintage would still repeat its predecessor: refused
   `REPEATS_PREDECESSOR`. This is stricter than the digest rule on purpose; the strategy record says
   that a vintage that would repeat its predecessor is not issued.
4. The block is `{previous_values_digest, new_values_digest, horizons}`, and `horizons` holds one entry
   per horizon label of the vintage (one today): `label`, `start`, `end`, `hours`, `mean_difference`,
   `mean_abs_difference`, `min_difference`, `max_difference`, as decimal strings at six places,
   computed exactly in `Decimal` from the JSON numbers.

Band levels (`p10`, `p50`, `p90`) are not part of the delta; the point value is.

A first issue (no `--from-stale`) is checked once too: when the archive already holds a vintage of
the same target, a new record whose values digest equals the newest one's is refused
`REPEATS_PREDECESSOR`. A first issue carries no `supersedes` block and no delta.

## Step 4: the confirmed issue

`issue_confirmed(archive, preview, issued_at=, confirmation_ref=, outlook_id=, issuer=,
method_record=, cutoff=)` refuses a blank `confirmation_ref` (`CONFIRMATION_MISSING`). The records
layer requires the reference too: a record with a `supersedes` block and no non-blank
`confirmation_ref` is refused, so no re-issue record exists without a recorded decision on any path,
`OutlookArchive.issue` included.

Four fields of a preview are what a person states, not what the archive derives: the vintage id, the
issuer, the method record path and the cutoff. A preview edited in those fields and resealed is a
valid preview on its own. So `issue_confirmed` takes the four from the confirming call (the command's
own `--outlook-id`, `--issuer`, `--method-record` and `--cutoff`; the dock's confirmation arguments)
and refuses a preview that names others (`PREVIEW_MISMATCH`). For the rest it does not trust the
preview: it finds the marks in the store again, rebuilds the preview from the live archive and the
method record with those four values, and refuses with the rebuild's own code (a newer vintage, a
moved input) or `PREVIEW_STALE` when the rebuilt digest differs from the confirmed one. What binds one
confirmation to one preview digest is DOCK-3's confirmation record. The vintage it writes is the
candidate plus one key:

```json
"supersedes": {
  "outlook_id": "<predecessor id>",
  "outlook_digest": "<predecessor content digest>",
  "reason": "belief_changed",
  "stale_marks": [{"content_digest": "...", "assumption_id": "...", "synthetic": false}],
  "changed_assumption_ids": ["..."],
  "delta": {"previous_values_digest": "...", "new_values_digest": "...", "horizons": ["..."]},
  "confirmation_ref": "<the confirmation id>"
}
```

`OutlookArchive.issue` checks the block against the stored predecessor before its exclusive create
(`check_supersedes`): the predecessor's bytes and values digest, the same series table and column and
the same horizon, the changed assumptions among those the predecessor rested on, the successor
issued after the predecessor with a cutoff no earlier, the reason's own rule, and provenance.
`verify()` repeats that check on read, so a predecessor replaced after the re-issue is reported on the
successor. Its scope is the link to the predecessor: `verify()` does not check the block's marks
against the mark store, and it does not compute the delta again from the values files; the issue path
checks both before the write.

## Provenance, one way

As for receipts in the records module: a re-issue that rests on a synthetic predecessor or on a
demonstration mark must itself be `synthetic`. The method record declares the flag and the command
never raises it silently (`SYNTHETIC_ONE_WAY` at the preview; `OUTLOOK_INVALID` or
`SUPERSEDES_INVALID` from the records module on its own). A synthetic re-issue may rest on either.

## What the real archive allows today

`.local/outlook-archive` holds two real vintages of November 2026 and one stale mark. The mark is a
labelled demonstration (`synthetic: true`) on the first vintage, and the second vintage is newer. So
no re-issue can start from the real archive today: the preview stops at `NOT_LATEST_VINTAGE` (a
read-only test pins it), and a mark on the second vintage would have to be real for a real third
vintage. A third vintage from a method change takes the mark-free path instead
(`--supersedes outlook-2026-11-system-v2 --reason method_changed`). OUT-3 owns the third vintage; see
the hand-backs in the task record.
