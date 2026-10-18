# Plan note: the outlook archive and the assumption register (ARCH-1 to ARCH-3)

Written 2026-10-16 by the orchestrator seat under the [price outlook plan](../price-outlook/intent.md).
Owner facts: no archived forecast vintage exists in the company; the archive is built from now on.

## Outcome

Every outlook issued is a record that cannot change: when it was issued, what information cutoff it
used, which inputs by name and digest, which accepted assumptions by id, which model version, which
horizon, and where its values sit (a digest of a file under `.local/`, never price values in Git). When
final prices arrive, a scoring receipt is appended that names the series version scored against and the
metrics. An assumption register holds every proposition the outlook rests on, with its layer and state.
A change to an accepted assumption marks the outlooks that used it stale; it erases nothing.

## Records (ARCH-1, ARCH-2)

`src/outlook/records.py`, stdlib only, validators in the style of `src/review/records.py`:

- **OutlookRecord**: `outlook_id`, `issued_at`, `information_cutoff`, `horizon`, `target_series_ref`
  (table, column, version), `inputs` (list of `{name, digest}`), `assumption_ids`, `model_version`,
  `values_ref` (`{path_hint, sha256, rows}`), `issuer`, `synthetic`. Immutable after issue.
- **ScoringReceipt**: `outlook_id`, `scored_at`, `final_series_version`, `metrics` (per horizon and
  slice, AP slice separate), `coverage` (intervals scored, intervals skipped with reasons).
- **AssumptionRecord** (`src/outlook/register.py`): `assumption_id`, `proposition`, `family`
  (`availability`, `rules`, `projects`, `price`, `threshold`, `composer`), `layer` (`official`,
  `analytical`, `inferred`, `exploratory`, `hypothesis`), `source_locator`, `valid_from`, `valid_to`,
  `state` (`accepted`, `unverified`, `contradicted`, `test_fixture`, `designed_unrun`, `deployed`),
  `owner`, `affected_code`, `falsifier`, `last_checked_revision`.
- The register data file `docs/work/outlook-archive/register.json` carries the 23 thresholds of
  `scripts/data/sql/03_ref_regions_thresholds.sql` and the 14 composer rows of `src/judgment/bundle.py`,
  each with its layer; an audit function reports missing or duplicate ids and dangling links.

## Dependency (ARCH-3)

`src/outlook/dependency.py`: `outlook -> assumption_ids -> evidence refs`; `mark_stale(assumption_id,
new_revision)` returns the outlook ids affected and appends a `StaleMark` record; the first outlook is
issued from PRICE-2's baseline inputs by digest and recorded in `first-outlook.md` with direction check
ARCH-3 (share of assumptions changed between monthly outlooks).

## Rails

No price values, portfolio volumes or node lists of the company in Git. Frozen contracts untouched;
`src/review` is not edited (a later task links the two). Records carry `synthetic` truthfully. Unknown
first availability stays unknown. Tests cover every validator branch and the immutability rule.
