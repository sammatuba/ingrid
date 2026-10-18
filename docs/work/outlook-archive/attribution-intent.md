# Intent: attribution on the scoring receipt (ARCH-4)

Plan note, 2026-10-17, orchestrator seat, on the owner's direction of the same afternoon ("proceed
autonomously … refining the product … focus on codebase and interface"). The framework page's rule:
no new record kind or field without a reviewed intent. The
[framework](../../architecture/meta-thesis-and-framework.md) row 6 and the
[foundation](../../architecture/theoretical-foundation.md) section 7 both say attribution is a designed
field with no intent record; this note is that record. It is reviewed before anything is built.
Independent review 1 (Claude Opus 5.5 in-session, 2026-10-17): rework on the storage key, the share
rule, the author rule, a write path that did not exist, the page list and the demonstration root; this
revision answers each point where it stands. Review 2 (same reviewer, on 4a3f065): **accept**, all nine
closed; three minor wording items (the two foundation sentences at acceptance, the `data` example against
the new-receipt rule, the key's encoding) corrected in the acceptance commit.

## Outcome

When a scoring receipt exists for an issued outlook, a person can attach to that receipt one or more
**attributions**: a statement that a named part of the miss is owed to a belief that was wrong, a
signal that arrived late, or the method. The attribution is a record of its own, appended beside the
receipt, never inside it (the receipt is sealed by its digest and is never edited). The desk's review
reads attributions to answer "what did we believe on the day, and which belief, signal or method
explains the miss", which is the single learning loop of the foundation page (Argyris and Schön's first
loop). Nothing in this intent scores a month: no real month has settled for an issued outlook, and the
first real pair is November to December 2026. The field is therefore **built and unexercised** on
delivery, and every page says so.

## The record

`Attribution`, one JSON document per statement, stored at `<root>/attributions/<key>.json` in the
ignored runtime archive. The key is derived from the record's own content, as the stale mark's is
(`dependency.py`, `_key_of`): the sha256 of `receipt_digest`, `cause`, the cause's reference
(`assumption_id`, the signal's `source` and `available_at`, or `method_ref`), `attributed_by`,
`statement` and `synthetic`, encoded as the module's `canonical_dumps` of a dict with every absent
reference field present as null, exactly as `_key_of` does for the stale mark. A reader rebuilds the key from the stored record and reports
`ARCHIVE_TAMPERED` when the file name differs; the store refuses a duplicate key by exclusive create,
with no scan before the write (the scan-then-write defect ARCH-1 round 2 refused is not repeated: there
is no sequence number and no "next" to compute). Two statements that differ in one word are two
records, by design; the review reads them side by side. Fields, all required unless marked:

| Field | Type | Rule |
|---|---|---|
| `schema_version`, `kind` | fixed | `kind` is `Attribution` |
| `outlook_id`, `outlook_digest` | id, digest | the outlook the receipt scored; read from the stored receipt, never typed |
| `receipt_digest` | digest | the exact receipt bytes this explains |
| `cause` | one of `belief`, `signal`, `method` | the foundation page's three causes, no other value |
| `assumption_id` | register id, optional | required when `cause` is `belief`; must be one of the outlook's `assumption_ids` (an attribution cannot blame a belief the outlook did not rest on) |
| `signal_ref` | object, optional | required when `cause` is `signal`: `source`, `available_at`, `effective_at` (the two clocks); `available_at` after the outlook's `information_cutoff` (a late signal is one the outlook could not have read), `available_at` at or before `attributed_at`, and `effective_at` before the receipt's `window.end` (a signal that takes effect after the scored window cannot explain its miss) |
| `method_ref` | text, optional | required when `cause` is `method`: equal to the outlook's `model_version`, nothing else (a named rule is not a closed set and is not accepted) |
| `share` | decimal text in [0, 1], optional | the part of the miss the author attributes to this cause, written as a decimal string through the module's `_decimal_text` so the digest is stable; absent means "not quantified". The sum over one receipt's attributions is **not** refused at write time (one exclusive create cannot see its siblings); `verify()` reports a sum above 1 as a problem, and the desk shows the problem beside the receipt |
| `statement` | non-blank text | one sentence in the author's words |
| `attributed_by` | actor text | non-blank; the validator checks no more than that. "The author is a person" is a process rule, not a validator rule: the only write path is the person-driven CLI below, no model path calls `append_attribution`, and a model's proposed attribution lives in a judgment record, never here (the authority principle) |
| `attributed_at` | instant | at or after the receipt's `scored_at` |
| `synthetic` | boolean | inherited: a real attribution cannot be linked to a synthetic receipt |
| `content_digest` | digest | sealed over the canonical bytes, as the other two kinds |

Invariants enforced by the validator and the store, from the attribution, its receipt and its outlook
alone: a record is never edited; the key is the record's own content; an attribution names the exact
receipt bytes and the receipt's outlook; the three causes are closed; a belief cause names a belief the
outlook rested on; a signal cause is dated after the cutoff, before the attribution and effective
before the window's end; a method cause names the outlook's model version; `synthetic` inherits one
way (a real attribution cannot sit on a synthetic receipt). Checked by `verify()` over the whole archive,
not at write time: the shares of one receipt sum to at most one. Process rule, not checked by code:
the author is a person.

## What is built in ARCH-4

- `src/outlook/records.py`: `build_attribution(receipt, outlook, *, cause, statement, attributed_by,
  attributed_at, synthetic, assumption_id=None, signal_ref=None, method_ref=None, share=None)`,
  `validate_attribution`, the cross-record check, and `OutlookArchive.append_attribution`,
  `attributions(outlook_id=None)`, with `verify()` counting attributions and their problems.
- `src/outlook/dependency.py`: `walk` is pure and takes no archive today; it gains keyword arguments
  `receipts` and `attributions` (lists the caller reads from the archive) and reports, per outlook, its
  receipts and their attributions grouped by cause, so the desk view can show them.
- `scripts/outlook/attribute.py` (new, standard library): the person-driven write path. It reads a
  stored receipt by `outlook_id` and `final_series_version`, takes the cause, its reference, the
  statement, the author and the share as arguments, builds the record through `build_attribution` and
  appends it; it refuses to run without `--attributed-by`, prints the key and the digest, and never
  issues or scores anything. No such CLI exists today (the first outlook was issued by a helper outside
  Git); this is the first write path in the repository.
- `scripts/grid/build_data.py` and `src/grid/event.js`: the price-outlook card lists a receipt's
  attributions in one sentence each when any exist, and otherwise says nothing new (no empty
  section). On delivery the real archive has no receipt and no attribution; the sentence appears only
  in fixture tests.
- Tests: every invariant refused on a fixture through the real builder; a labelled synthetic
  demonstration (synthetic outlook, synthetic receipt, one attribution per cause) proves the chain end
  to end **in a fixture archive under a temporary root with the workspace fallback the reviewer
  sandbox needs**, never in the real archive at `.local/outlook-archive`. Nothing synthetic is issued
  into the real archive by this task: an issue is permanent, it would appear in `issue_ids()` and on
  the card, and a demonstration receipt on a real outlook would take that outlook's receipt key for
  good (`receipt_stem` leaves `synthetic` out).
- Pages, in two steps, the evidence ledger first each time (the foundation page's section 7 says a
  closing record is named in the ledger before that page changes):
  - **at the acceptance of this intent**: the ledger gains a row naming this note; the framework's
    invariants bullet "attribution's intent is not yet written" becomes "attribution's intent is written
    and reviewed (this note); the field is not built"; the foundation's section 4 Outcome row and
    section 7 sentence, which say "a designed field with no intent record", say "a designed field whose
    intent is reviewed (this note), not built".
  - **after delivery**: the ledger row moves to "built, unexercised"; the foundation section 4 Outcome
    row and section 6 Learning step say "attribution built as a record of its own, no attribution on
    a real receipt"; the framework row 6 and its step 8 ("the scoring receipt … attributes any miss")
    say that a person attributes in a separate record beside the receipt; the framework's "seven record
    kinds" sentence says the attribution is the receipt's companion record, the eighth kind, and why
    the seven-record framing keeps its shape (the receipt "with attribution" is the receipt plus its
    attributions); the explainer's Ideas 4 thin spot and the miss-cause widget follow. All of these are
    orchestrator commits after the merge, on DOC and architecture paths outside ARCH-4's.

## Not in scope

Scoring itself (the receipt exists since ARCH-1 and waits for a settled month); any model proposing
attributions; any page or form for writing an attribution (the CLI above is the only write path); the
second learning loop (changing goals) stays a project-level act; the framework's proposition 1 test
(the share of misses attributable to a belief that changed before the cutoff), which needs a join from
a belief attribution to the stale marks' `marked_at` and is a later, reviewed step once real
attributions exist.

## Direction check ARCH-4

The number recorded on delivery is the count of attributions in the real archive
(`.local/outlook-archive`), expected 0 because it holds no receipt, beside the count in the fixture
demonstration run by the tests, expected 3 (one per cause); the first non-zero real count can come no
earlier than the first scored month.

## Material unknowns and what would change this

- Whether the three causes are enough once a real month is scored. A gap in the final series itself
  is already a receipt matter: `coverage.skipped` records the skipped intervals with reasons, so a
  `data` cause would be for a miss on intervals that **were** scored but whose final values were later
  corrected; since a corrected series version is a new receipt (records note, section 11), that
  attribution attaches to the receipt of the earlier version, beside the new receipt. If the first scoring finds one, `cause` gains `data` by a reviewed change to this note,
  not by a free text value.
- Whether `share` should be required. It is optional here because the first attributions will be
  qualitative; the scorecard metrics make a quantified share possible later.
