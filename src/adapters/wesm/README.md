# WESM source readers (advisories, registered capacity)

Two additive, read-only adapters that turn orchestrator-exported JSON lines from the company
WESM copy into h0.v2 records. They read local bytes only: no network, credential, clock or
calendar beyond what a row carries. The export is
[`scripts/data/wesm/export.sh`](../../../scripts/data/wesm/export.sh), which runs in the
orchestrator seat with the repo-local `gcloud` configuration; the executor seat never runs it.
Permission: [`perm:wesm-company-copy:2026-10-13`](../../../docs/work/permissions/2026-10-13-wesm-company-copy.md).

| Module | Input | Output |
|---|---|---|
| `advisories.py` | `grid_raw.ext_others_mpi_advisories` rows | one `SourceVersion` and, when the message grammar matches, one `Passage` per advisory |
| `registry.py` | `grid_raw.ext_others_regcap_generation` rows | one `SourceVersion` per change-only run and one unreviewed `MappingRevision` candidate per run |

## Advisories

Naive copy timestamps are Asia/Manila. `interval_start` is `known_at` with a typed
`feed_logged_at` basis; the in-text header clock is `published_at` and must be within 15
minutes of the posting instant or the row is refused `CLOCK_DISAGREEMENT`; `adv_sdate` and
`adv_tran_type` are read but not used (owner, 2026-10-13). `source_id` is
`nso-advisory:<posting date>:<adv_id>`, `source_version` is `1`. Identical body text within 24
hours is one lineage: the earliest `source_id` is the `lineage_id`, and a byte-identical repost
cites it through `copied_from`; the same text more than 24 hours later is a new lineage. The
passage is the body between the grid header and the `  [WEBSMS]` tag, held as UTF-8 byte
offsets into `original_text`; a message that does not match the grammar yields its source
version with no passage and is counted in the report, never repaired.

The passage payload also carries parser metadata, which the validator does not know and the
compiler never reads: `event_at` (the `at HHMMH` clock, on the header date unless it is later
than the header clock, then the previous day; `null` when the message carries none),
`event_time_flag` (`"review"` when the header-to-event gap exceeds six hours or the stamp is
not a time) and `category` (a deterministic keyword map to the bundle v5 event tokens, for
selection only; the model is never told it).

## Registered capacity

Actual copy columns are `trading_day_id, tp_name` (participant), `resource_name,
maximum_capacity, byear, bmonth`; the region is derived from the resource-name prefix (01-03
Luzon, 04-08 Visayas, 09-14 Mindanao) and a row outside that map is refused rather than
guessed. Consecutive calendar days with the same `(participant, maximum_capacity)` form one
change-only run: one `SourceVersion` whose `original_text` is the canonical JSON of the run
(`resource_name, tp_name, maximum_capacity, region, first_day, last_day, trading_days`) and
whose `known_at` is the first trading day at 00:00 +08:00. Rows that agree completely on
(resource, day, participant, capacity) collapse — the copy repeats a day at a billing-month
boundary — and the copy's 2025 hole is a gap between runs, never interpolated.

Every run yields one `MappingRevision` candidate: one `GeneratingUnit` entity named by
`resource_name`, `cardinality: one_to_one`, `valid_period` the run's days as a half-open date
interval, `status: unreviewed`, with `representation_id` and `input_field` supplied by the case
(the register supplies the unit, not the model). A resource under two participants on the same
day yields two candidates and both are `ambiguous`. The free-text name to resource-code link
("PEDC U2" to `08PEDC_U02`) is the case's identity step; these candidates never make it.

Two readings are recorded for the reviewer: `published_at` on a register run is the run's first
trading-day stamp, because the copy carries no separate publication instant; and the category
map's rule order is fixed in `CATEGORY_RULES` (returns and alert wording are read before the
"(Planned/Unplanned Outage)" parentheticals they carry).

## Running and checking

```sh
/usr/bin/python3 -m src.adapters.wesm.advisories tests/fixtures/wesm/advisories-sample.jsonl
/usr/bin/python3 -m src.adapters.wesm.registry   tests/fixtures/wesm/registry-pedc-sample.jsonl
/usr/bin/python3 -m unittest tests.test_wesm_sources -v
```

The committed fixtures under `tests/fixtures/wesm/` are real sample rows cited to the
permission record; see their [README](../../../tests/fixtures/wesm/README.md) for what each
row exercises and which counterexamples the tests construct because the real feed cannot
provide them.
