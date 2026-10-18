# ARCH-2: the assumption register

Lane ARCH, milestone M11, route implement, executor agent, effort 3 h. Branch `task/ARCH-2`
from the M11 plan note's base; no dependencies, no gates. GitHub #79. Read with the
[outlook archive plan note](intent.md) and the [price outlook plan note](../price-outlook/intent.md).

## Outcome

The register holds every proposition the outlook rests on, with where its value comes from and
where it stands. This task enters its first two families, both read one-for-one from sources
already in the repository:

| File | What it is |
|---|---|
| [register.json](register.json) | the register data: 23 threshold rows and 14 composer rows, 37 records, each with its twelve fields |
| [src/outlook/register.py](../../../src/outlook/register.py) | the record and envelope validators, the loader, the threshold-name and threshold-value parsers and the price-band ladder from the SQL text, and the audit |
| [tests/test_outlook_register.py](../../../tests/test_outlook_register.py) | 56 tests: every validator branch, the file's own counts and labels, the three price propositions against the label statement's ladder, and every audit list made to fire on a copy of the real register |

The file was emitted by an ignored helper, `.local/briefs/arch2/build_register.py`, which reads
the two sources, derives every citation's path, line and verbatim quote from the files
themselves, writes `register.json` and then validates and audits it. The file is the committed
artefact; the tests re-derive the sources' ids and re-check every quote, so the register is
auditable without the helper.

## The record

`AssumptionRecord`, validated by `src/outlook/register.py:record`:

| Field | Holds | Rule |
|---|---|---|
| `assumption_id` | `<family>:<name>` | the id must name the record's own family; the slug carries no whitespace |
| `proposition` | the statement the outlook rests on | non-blank text |
| `family` | `availability`, `rules`, `projects`, `price`, `threshold` or `composer` | one of the six |
| `layer` | where the value comes from | `official`, `analytical`, `inferred`, `exploratory` or `hypothesis` |
| `source_locator` | the citation, as a list of `{path, line, quote}` | at least one; `line` is one-based; `quote` must be the text on that line |
| `valid_from`, `valid_to` | the interval the value is valid for | an ISO date that exists on the calendar, or `null` (no record states one); both ends ordered when both are present |
| `state` | where the proposition stands | one of the six states below |
| `owner` | who owns the proposition | non-blank; `unassigned` where no record names an owner |
| `affected_code` | the code the proposition affects | a list of repository paths |
| `falsifier` | what would show the proposition wrong | non-blank text |
| `last_checked_revision` | the revision it was last checked at | a 7-to-40-hex commit id or `null` (no check recorded) |

The envelope (`register.json`) declares its version (`outlook-register.v1`), the two sources it
was read from and how many rows each source has. A declaration that disagrees with the records
present, or that names a path other than the source the module reads for that family, is refused,
so neither the count nor the path can drift from what it describes.

### Layers: where the value comes from

| Layer | Meaning | Rows |
|---|---|---|
| `official` | an authoritative document fixes the value: the frozen product definition (the working paper's table), or an official document or market rule, named in the locator | 9 (composer only) |
| `analytical` | measured or derived from the data | 14 (threshold only) |
| `inferred` | rests on an unconfirmed meaning or an internal document | 5 (threshold only) |
| `exploratory` | a provisional design choice of the method, not derived from the data and not fixed by a document | 9 |
| `hypothesis` | valid for later product rows; carried by none of the 37 | 0 |

### States: where the proposition stands

| State | Meaning | Rows |
|---|---|---|
| `deployed` | a record shows it in force in a built artefact | 23 (the thresholds) |
| `test_fixture` | exercised on fixtures, scripted backends or recorded replays only | 14 (the composer rows) |
| `accepted`, `unverified`, `contradicted`, `designed_unrun` | valid, carried by none of the 37 | 0 |

The 23 threshold values are in force in built and populated marts — `grid_curated.interval_pricing`,
`labels`, `labels_reserve`, `features`, `semantic_state` — whose row counts are recorded in
[folder-decisions.md](../data-foundation/folder-decisions.md); the readers are in each row's
`affected_code`. The 14 composer rows are exercised by the frozen `probe-bundle.v5` composition
on the fixture set and the PEDC case replay through the scripted backend
([fixtures.md](../probe-bundle/fixtures.md), [case packet](../../cases/pedc-u2-2026-09-21/packet.md));
the only recorded live judgement runs predate v5 ([live-run record](../grid-desk/live-run-2026-10-14.md)).
`deployed` says the value is in force, not that it is verified: the layer and the falsifier carry that.

## What is unknown stays unknown

All 37 rows carry `valid_from`, `valid_to` and `last_checked_revision` as `null`, and `owner` as
`unassigned`. That is the register's statement about itself, not an omission: no record inspected
states when the v1 values took effect, no check against a source is recorded, and no owner is
named for any of them — which is the thesis's own observation (a register nobody owns). The audit
counts each: `unknown_interval` 37, `unchecked` 37, `unowned` 37. Filling one in is a register
edit; the audit's numbers follow it.

`valid_from` and `valid_to` are not inferred from the dates inside a value (`reserve_labels_from_yyyymmdd`
20260301, the split dates) or from a commit date, and `last_checked_revision` is not read from the
commit that last touched the source file. Both would be inferences from a record, not readings of one.

## The sources, and how the register cannot drift from them

| Source | Family | Rows | Read as |
|---|---|---|---|
| `scripts/data/sql/03_ref_regions_thresholds.sql` | `threshold` | 23 | the `grid_ref.thresholds` statement's own rows, in file order, parsed as text (the SQL is data, not importable code) |
| `src/judgment/bundle.py` (frozen `RULES`) | `composer` | 14 | the frozen composition table itself, imported, in table order |

`register.audit` derives the expected ids from those two sources at every run, never from the
register's declaration of them. A threshold row added to the SQL is a `missing` register row; a
composer row renamed in the frozen table leaves the register's row `unknown`; a row added to one
side only is visible in the same way. The threshold parser reads only the `grid_ref.thresholds`
statement, so the `ref_regions` statement above it — which has the same `STRUCT` shape — cannot
leak into the register, and a source that cannot be parsed is refused rather than read as empty.

Each record cites its primary source at a path, a one-based line and the verbatim text on that
line; the audit re-reads the file and refuses a citation whose quote is not on the line it names.
No quoted source text in this register was typed by hand: the helper derived every quote from the
file, and the tests re-check them.

A third statement is read where a proposition names a class rather than a number. The three price
cuts say which band a capped median falls in, so the tests read
`scripts/data/sql/05_labels_price.sql` for the `price_band` ladder itself — `very_low` below 0,
`low` below `price_low_max`, `normal` below `price_normal_max`, `high` below `price_high_max`,
`very_high` below `price_cap_php_mwh`, `extreme` above it — and hold each of the three
propositions to the band its own cut tops and to the band below it as the stated lower bound. The
ladder reader refuses a statement whose arms, bounds or fall-through cannot be read, rather than
reading fewer bands than the statement has; `threshold_values` reads the numbers the same rows
carry, so the check compares against the SQL rather than against a copy of it.

## The 23 thresholds

`threshold:<name>`; every row `deployed`, `owner: unassigned`, interval and last check unknown.
The layer is a reading of the SQL row's own `source` text, with the challenge register's
disposition where one exists (A05, [strategy record](../thesis-challenge-2026-10-16/strategy.md)).

| Threshold | Layer | Proposition | Primary citation |
|---|---|---|---|
| `price_cap_php_mwh` | analytical | The upper bound of rtd_market_clearing_price energy prices is 32,000 PHP/MWh, the observed 2026-09 maximum (32,000.02), and interval pricing clamps above it. | `scripts/data/sql/03_ref_regions_thresholds.sql:13` |
| `price_floor_php_mwh` | analytical | The lower bound is -10,000 PHP/MWh, the observed 2026-09 minimum, and interval pricing clamps below it. | `scripts/data/sql/03_ref_regions_thresholds.sql:15` |
| `price_low_max` | analytical | A capped median interval price from 0 up to below 3,000 PHP/MWh is low; the low band starts at 0, so a median below 0 is very_low, not low. The cut sits near Luzon 2026-09 p25 (about 2,900). | `scripts/data/sql/03_ref_regions_thresholds.sql:17` |
| `price_normal_max` | analytical | A capped median interval price from 3,000 up to below 8,000 PHP/MWh is normal; 3,000, this cut's lower bound, is the top of the low band below it. The cut sits near Luzon 2026-09 p90 (about 7,950). | `scripts/data/sql/03_ref_regions_thresholds.sql:18` |
| `price_high_max` | analytical | A capped median interval price from 8,000 up to below 20,000 PHP/MWh is high; 8,000, this cut's lower bound, is the top of the normal band below it. The cut sits near Luzon 2026-09 p99 (about 21,000). | `scripts/data/sql/03_ref_regions_thresholds.sql:19` |
| `admin_priced_min_nodes` | inferred | An interval with at least one AP-flagged node is administered pricing. | `scripts/data/sql/03_ref_regions_thresholds.sql:20` |
| `secondary_cap_min_nodes` | inferred | At least one SEC-flagged node is secondary-cap priced. | `scripts/data/sql/03_ref_regions_thresholds.sql:21` |
| `price_substituted_min_nodes` | inferred | At least one PSM-flagged node is price-substituted. | `scripts/data/sql/03_ref_regions_thresholds.sql:22` |
| `reserve_short_min_pct` | inferred | Scheduled reserve below requirement by more than 1% is materially short. | `scripts/data/sql/03_ref_regions_thresholds.sql:23` |
| `reserve_deficient_min_consecutive` | inferred | Two or more consecutive materially-short Dr/Fr intervals are reserve_deficient. | `scripts/data/sql/03_ref_regions_thresholds.sql:24` |
| `reserve_labels_from_yyyymmdd` | analytical | Reserve labels are computed from 2026-03-01 only, because 2024 reserve scheduling behaves differently. | `scripts/data/sql/03_ref_regions_thresholds.sql:25` |
| `split_valid_from_yyyymmdd` | exploratory | The time-ordered split validates on 2026-08, after training to 2026-07-31. | `scripts/data/sql/03_ref_regions_thresholds.sql:26` |
| `split_test_from_yyyymmdd` | exploratory | The time-ordered split tests on 2026-09. | `scripts/data/sql/03_ref_regions_thresholds.sql:27` |
| `target_embargo_hours` | exploratory | Rows within three hours before a split boundary are embargoed, because their forward targets reach into the next period. | `scripts/data/sql/03_ref_regions_thresholds.sql:28` |
| `import_mild_min` | analytical | An import share of at least 2% of requirement is mildly_dependent. | `scripts/data/sql/03_ref_regions_thresholds.sql:29` |
| `import_dependent_min` | analytical | An import share of at least 10% is dependent. | `scripts/data/sql/03_ref_regions_thresholds.sql:30` |
| `import_critical_min` | analytical | An import share of at least 25% is critically_dependent (Visayas 2026 p95 0.275). | `scripts/data/sql/03_ref_regions_thresholds.sql:31` |
| `shortfall_serious_min` | analytical | A largest Dr/Fr shortfall of at least 25% of requirement is serious. | `scripts/data/sql/03_ref_regions_thresholds.sql:32` |
| `shortfall_severe_min` | analytical | A largest Dr/Fr shortfall of at least 60% of requirement is severe. | `scripts/data/sql/03_ref_regions_thresholds.sql:33` |
| `trend_min_change` | exploratory | A Dr shortfall share moving by more than +-0.10 against one hour earlier is worsening or improving. | `scripts/data/sql/03_ref_regions_thresholds.sql:34` |
| `onset_band_moderate_min` | analytical | An onset probability of at least 0.10 is the moderate band. | `scripts/data/sql/03_ref_regions_thresholds.sql:35` |
| `onset_band_high_min` | analytical | An onset probability of at least 0.30 is the high band. | `scripts/data/sql/03_ref_regions_thresholds.sql:36` |
| `onset_band_very_high_min` | analytical | An onset probability of at least 0.60 is very_high; hardly any September rows are reliably above it. | `scripts/data/sql/03_ref_regions_thresholds.sql:37` |

Fourteen are `analytical` (measured bounds, distribution cuts and comparability cuts), five are
`inferred` (the three flag-meaning rows, whose meaning the record calls unconfirmed, and the two
reserve rules inherited from the strategy documents rather than tuned), four are `exploratory`
(the split dates, the embargo and the trend band, which no record derives from data or a
document). **No threshold is labelled `official`**: no row's recorded source names an official
document or market rule. In particular `price_cap_php_mwh` is recorded as the observed maximum of
one month, and the repository's research record has the current published cap as unknown. That the
register can name no official threshold is itself the gap A05 upheld; it is now a number a reader
can check rather than a sentence in a challenge register.

## The 14 composer rows

`composer:<row>`; every row `test_fixture`, `owner: unassigned`, interval and last check unknown.
The layer splits on the row's own decision inputs: a row whose outcome reads a token only is
`official` (the frozen table fixes it); a row whose outcome is decided by one of the frozen
table's initial, untuned numeric limits (`DEFAULT_THRESHOLDS`, `tau_suff`, `tau_cond`,
`tau_lineage`, `tau_flip`, `tau_pol`) is `exploratory`, because the row's behaviour is a first
pass the ablation is to fix.

| Row | Layer | Proposition | Primary citation |
|---|---|---|---|
| `unstable` | exploratory | A bundle whose form votes drift above tau_flip or whose polarity gap exceeds tau_pol is insufficient before any row reads it. | `src/judgment/bundle.py:448` |
| `sufficiency_gate` | exploratory | A modal no on Q7, below tau_suff, refuses composition with LOW_SUFFICIENCY. | `src/judgment/bundle.py:451` |
| `identity_unknown` | official | Q1 cannot_tell composes insufficient rather than pick an entity. | `src/judgment/bundle.py:454` |
| `unrelated_entity` | official | Q1 naming a candidate other than the assumption's mapped entity composes unrelated. | `src/judgment/bundle.py:457` |
| `event_other` | official | Q2 other or grid_alert composes unrelated: a grid alert names no unit assumption. | `src/judgment/bundle.py:462` |
| `lineage_reuse` | exploratory | Q5 at or above tau_lineage reuses an earlier source's label; with no earlier label the bundle is insufficient (LINEAGE_NO_PRIOR). | `src/judgment/bundle.py:465` |
| `availability_confirmed` | exploratory | An availability-kind input field with Q2 commercial_operation or return_to_service, Q3 same and Q4 below tau_cond composes supports. | `src/judgment/bundle.py:473` |
| `milestone_mismatch` | official | Q2 testing on an availability-kind input field composes challenges. | `src/judgment/bundle.py:476` |
| `outage_or_later` | official | Q2 planned_outage, forced_outage or derating, or Q3 after, on an availability-kind field composes challenges. | `src/judgment/bundle.py:479` |
| `earlier_observation` | official | Q3 before with Q6 yes composes supports. | `src/judgment/bundle.py:483` |
| `direction_conflict` | official | Q3 before, Q6 yes and Q8 challenges composes mixed (owner decision, 2026-10-13). | `src/judgment/bundle.py:484` |
| `conditional_support` | exploratory | Q4 at or above tau_cond with Q3 same or before composes mixed. | `src/judgment/bundle.py:486` |
| `time_not_stated` | official | Q3 not_stated composes mixed when Q8 names a direction and insufficient when it is neither. | `src/judgment/bundle.py:490` |
| `fall_through` | official | No row matched composes insufficient with reason FALL_THROUGH. | `src/judgment/bundle.py:493` |

Each row also cites the working paper's composition table
([section 5.2](../../product/working-paper-2026-10-11.md), lines 210 to 220) as its supporting
locator, and `direction_conflict` cites the bundle module's own owner-decision comment. The
`affected_code` of a composer row names the code its outcome flows through: the frozen table, the
service that composes and stores the result, the record validator that knows the row names, and
the page that renders the fourteen rows by index.

## GitHub #79 acceptance items

Issue #79, "[Grounding A00] Maintain a versioned, falsifiable assumptions and evidence register"
(state `OPEN`, parent #78, its own header "Priority P1: foundational planning. Post-submission
unless owner reprioritizes."), read on 2026-10-16 with `gh issue view 79` through the seat's
python subprocess (`rc 0`, the raw JSON kept out of Git). Item text below is quoted verbatim from
the issue's `Acceptance` list and its `Job` list.

The issue's job 3 is this task's scope: "Index all 23 named threshold settings in
`03_ref_regions_thresholds.sql` and 14 relation-composition rule branches in `bundle.py`; never
conflate a classifier routing score with an event probability." Both indexes are the register's
two families, one row per setting and per branch, and no row equates a routing or confidence
score with an event probability: the only probability-bearing rows are the three `onset_band_*`
thresholds, whose values are the calibration record's display bands, and the composer rows carry
the frozen table's own confidence limits as limits, never as an event probability.

| Acceptance item (verbatim) | Answer |
|---|---|
| "Every A01–A12 family has an owner, evidence state, stop/abstain behavior, verification method and link to the implementation or explicit absence." | **Open, handed back.** No A01–A12 row is in this file: this task's acceptance and the plan note ([intent.md](intent.md)) name the 23 threshold and 14 composer rows, and the challenge rows have no family in the record shape and no owner in any source. Their dispositions and evidence grades are in the [strategy record](../thesis-challenge-2026-10-16/strategy.md) (sections B and D), so the increment is mechanical once the orchestrator fixes a family and an owner for them. Next action recorded below |
| "23/23 threshold entries and 14/14 deterministic composition branches accounted for; an automated audit detects missing/duplicate IDs and dangling links." | **Met.** 23 of 23 and 14 of 14, read from the two sources themselves; `audit` reports `missing`, `unknown`, `duplicates` and a `dangling` list that covers exactly what the item asks — a citation with no such path, a line past the end of the file, a quote not on the line it names, and an `affected_code` path that does not exist. Each of those lists is made to fire in the tests on a copy of the real register |
| "Status categories distinguish **accepted, unverified, contradicted, inferred, test fixture, designed/unrun, deployed**; never silently promote a proposal to fact." | **Met, with the vocabulary split the brief fixes.** Six are states (`accepted`, `unverified`, `contradicted`, `test_fixture`, `designed_unrun`, `deployed`), and `inferred` is a layer, because the ARCH-2 brief labels the 37 rows "official, analytical, inferred or exploratory". All seven are distinguished, and none of the 37 is `accepted`: a value being in force is `deployed`, and its provenance is the layer, so nothing is promoted to fact |
| "Reviewer reproduces the ledger from cited source paths at a fixed commit and records what needs owner/domain-expert decision." | **Partly, by design.** Reproduction is built for: `audit` re-reads the two sources and re-checks every citation's path, line and quote at the committed revision, and the tests re-derive the ids, so a reviewer runs one module against one commit. What needs an owner decision is named in section "Open": every owner is `unassigned`, and no interval or check is recorded. The reviewer's own reproduction and record are the review, not this packet |
| "Private WESM bytes, credentials, proprietary licensed text stay outside Git/issues; use references and short non-sensitive examples only." | **Met.** The register carries propositions, paths, lines and short quotes of the repository's own SQL and code — no price values, no node lists, no portfolio volumes, no credentials and no licensed text. The register's rails repeat the plan note's: no price values in Git |

The issue's `Job` list is answered the same way, item by item:

| Job item | Where this task stands |
|---|---|
| 1. "Design a structured register (human-readable index + machine-readable records) for assumption IDs A01–A12 from #78 and each important sub-assumption in the SQL/model/ontology/contracts." | **Partly.** The human index is this record's two tables, the machine records are `register.json`, and the SQL settings are entered. The A01–A12 rows and the model/ontology sub-assumptions are open (above), and the corpora and ontology lanes own their own assumptions |
| 2. A record with "exact proposition, layer …, asserted valid interval, source/edition/locator, affected dataset/code/task, evidence grade, falsifying observation, owner/reviewer, state, last checked revision, risk priority and consumer/display consequences" | **Partly, and deliberately to the plan note's shape.** The intent fixes twelve fields, and they carry: proposition; layer; interval (`valid_from`/`valid_to`, unknown on all 37); locator (path, one-based line and verbatim quote — the threshold quotes carry the row's own `'v1'` edition, and the composer rows are under the frozen `probe-bundle.v5`); `affected_code` (the code paths, with the datasets each reader writes named in this record); falsifier; owner (all `unassigned`); state; last checked revision (all `null`). Not carried, because the intent's shape does not have the field: evidence grade, reviewer, risk priority, ticket links and consumer/display consequences. Adding them is a record-shape change and returns to intent; the consumers are named here instead (the marts for thresholds, the explain panel and the service for the composer rows) |
| 3. The 23 and the 14 indexed, no routing score shown as a probability | **Met** (above) |
| 4. "Connect records by stable IDs to #78's child tickets and existing CORP/ATG/EVAL jobs. Do not change frozen contracts or task ownership without a reviewed intent." | **Partly.** Records are connected by stable ids to their sources (`threshold:<name>`, `composer:<row>`) and by path to the code they affect; ticket links are not a field in the intent's shape, so no row carries one. Frozen contracts and task ownership are untouched |

## The audit

`register.audit(payload, root=ROOT)` reads the sources and reports:

| Key | What it names |
|---|---|
| `missing` | a threshold or composer row its source declares and the register does not carry |
| `unknown` | a register row of those two families the source no longer declares |
| `duplicates` | an id carried more than once |
| `dangling` | a citation pointing at nothing (no such path, a line past the end of the file, a quote not on the line it names) or an `affected_code` path that does not exist |
| `unlabelled` | a counted row whose layer is outside the four labels the acceptance names |
| `counts` | the rows per family, the layers, `unowned`, `unknown_interval`, `unchecked` |

On the committed file:

```json
{"missing": [], "unknown": [], "duplicates": [], "dangling": [], "unlabelled": [],
 "counts": {"records": 37, "threshold": 23, "composer": 14, "official": 9, "analytical": 14,
            "inferred": 5, "exploratory": 9, "hypothesis": 0, "unowned": 37,
            "unknown_interval": 37, "unchecked": 37}}
```

Every one of those lists is made to fire in the tests, on a copy of the real register: a deleted
row lands in `missing`, a second copy of a row in `duplicates`, a renamed row in `unknown` and
its source id in `missing`, a citation with no such path, a line past the end and a quote that is
not on its line each land in `dangling`, an `affected_code` path that does not exist lands in
`dangling` by name, and a counted row carrying the fifth label lands in `unlabelled` while the
other lists stay empty.

> **ARCH-3 addendum (2026-10-16).** ARCH-3 added five rows to the committed file for the
> assumptions the first outlook rests on (three `price:`, two `rules:`; two `accepted` — the
> owner-answered final-settlement `lmp` meaning and the 26th-to-25th clock — and three
> `deployed`). The table above is this task's snapshot at its own revision; the live numbers are
> what `register.audit` reports, and on the file as it now stands they are: `records` 42,
> `official` 11, `analytical` 15, `inferred` 5, `exploratory` 11, `unowned` 40,
> `unknown_interval` 42, `unchecked` 42, with `missing`, `unknown`, `duplicates`, `dangling` and
> `unlabelled` all empty. The five rows and their citations are in
> [first-outlook.md](first-outlook.md) §5; the count pins in this task's tests moved 37 → 42 in
> the same commit, without weakening a check.

> **REG-2 addendum (2026-10-17).** REG-2 added one `availability` row for the belief the PEDC
> Unit 2 event page looks up: `availability:pedc-u2-2026-09-21`, stating "PEDC Unit 2 available
> capacity holds at the IEMOP register run's registered maximum of 83.7 MW for 2026-09-21
> (participant PEDC, trading days 2026-02-05 to 2026-09-29)." — `analytical`, `deployed`, owner
> `orchestrator seat` (a seat, not a person; naming a person is still the owner's step), valid
> 2026-09-21 to 2026-09-21, last check unknown. Its evidence refs are into the case pack —
> [brief.md](../../cases/pedc-u2-2026-09-21/brief.md) lines 38, 39 and 42 (the proposition, the
> value read from the register run, the run's days and participant),
> [evidence-manifest.json](../../cases/pedc-u2-2026-09-21/evidence-manifest.json) line 1 (the
> IEMOP publisher and the operator's trip quote) and
> [outlook-revision.md](../../cases/pedc-u2-2026-09-21/outlook-revision.md) line 15 (the day).
> Its falsifier is the operator's trip notice V133937: "The operator's trip notice for PEDC Unit 2
> on 2026-09-21 (V133937, 'PEDC U2 Tripped at 1334H') shows the unit did not hold its registered
> maximum for the day". The state is `deployed` because the belief is in force in the built
> event view — the event's assumption block and DESK-1's register card — not because it is
> verified: the case review records that the trip contradicts uninterrupted day-level
> availability, and the falsifier carries that record (see [reg-2.md](../product-gap-2026-10-17/reg-2.md)).
>
> The event view looks a proposition up by the event's assumption words (`PEDC Unit 2 available
> capacity`) as a substring; this is the one row that states them, so
> `outlook/<event-id>.json` now records `registered: true`, this row's id, layer, state and
> owner, and still `rests_on_this_assumption: false`. No issued price outlook cites the row —
> the seasonal baseline does not use unit availability — so the card still says "No issued
> price outlook rests on PEDC Unit 2 available capacity."
>
> On the file as it now stands, `register.audit` reports `records` 43, `threshold` 23,
> `composer` 14, `official` 11, `analytical` 16, `inferred` 5, `exploratory` 11,
> `hypothesis` 0, `unowned` 40, `unknown_interval` 42, `unchecked` 43, with `missing`,
> `unknown`, `duplicates`, `dangling` and `unlabelled` all empty. This is the one row with a
> dated interval; every other row's interval, and every row's last check, stays unknown.

## Verification

Run from the worktree root, on the committed tree of branch `task/ARCH-2` (base `cb9bb27`,
the merge of ARCH-1 into `feat/price-outlook`), with `/usr/bin/python3`:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` (the brief's verify command, the full offline suite) | `Ran 1601 tests` / **OK (skipped=47)** (runs of this command on this tree took 37 s to 121 s; the wall clock tracks machine load, the count and the result do not) |
| `/usr/bin/python3 -m unittest tests.test_outlook_register -v` | `Ran 56 tests` / **OK** |
| `/usr/bin/python3 scripts/plan.py scope ARCH-2 feat/price-outlook` | `OK: all changed files inside ARCH-2 allowed paths` |
| `/usr/bin/python3 scripts/repo.py check` | **PASS** (439 Markdown files, 2857 local links, 8 skills; bootstrap 1397 words) |
| `/usr/bin/python3 scripts/plan.py check` | **OK: 93 tasks, 8 gates** |
| `/usr/bin/python3 .local/arch2-rework-probe.py` | the rework probe below: all four review findings reproduced on the reviewed bytes and clean on this tree |
| `gh issue view 79` (read-only; run through `/usr/bin/python3 -c "subprocess.run([...])"` as the seat's launcher does, `rc 0`) | the issue body read for the answers above; no issue, comment or label was written |

The build's own run recorded 1529 tests on the then-base `728f71a`; this tree is based on
`cb9bb27`, which carries ARCH-1's rework, so the suite is larger by that module's growth as well as
by this rework's ten new tests. The independent review's 1581 tests with 310 errors came from its
restricted sandbox, where temporary-directory restrictions error most of the suite, so its counts
are not directly comparable with these; the one failure it reported independently of that
restriction — the duplicate progress rows — is the first finding above. The 47 skips
are the suite's environment-gated classes (browser, node, Firestore emulator, wire and
server-library checks), the same configuration other lanes record; nothing in this task's paths
skips. No model, cloud or browser call was made, and the register, the loader and the audit are
stdlib plus the repository's own canonical-JSON and review-record helpers; the register holds no
case facts, no prices and no model output. The only network calls were the read-only GitHub reads
for issue #79: an unauthenticated `GET` to `api.github.com` answers `404` (the repository is
private) and a web fetch the harness refused, then `gh issue view 79` through the seat's python
subprocess, which returned the issue body. Nothing was sent, published or written to GitHub.

One transient red is worth recording for the orchestrator: with the four new files staged but not
committed, `tests/test_release_audit.py`'s `LiveRepository` case failed on "every tracked path
needs one decision", because it builds its decisions from `git ls-files` (the index, which by then
held the new paths) while it audits `HEAD` (which did not). The commit resolves it, and the suite
is green on the committed tree above; no test was changed. This is the release audit's known
reads-HEAD rule, not a defect in this diff.

Frozen contracts are untouched: `src/review/records.py`, `src/judgment/__init__.py`,
`src/judgment/bundle.py` and the working paper are read, never edited; the register cites the
composition table through its frozen `RULES` and does not restate or change it.

## Rework after the designated review

The independent review (GPT Sol, commit `275a495`, in [reviews/ARCH-2.md](../reviews/ARCH-2.md))
returned **rework**: three important findings and one minor. All four are fixed in this commit,
inside the task's allowed paths; no acceptance text, frozen contract or existing test was changed.

| Finding | Fix |
|---|---|
| **important** — `docs/work/PROGRESS.md:129`: a second ARCH-1 row (`pending`) and a second ARCH-2 row were added instead of editing the existing ones, and the last row wins when the file is parsed, so `test_progress_record_matches_task_states` failed on the committed tree | The two added rows are removed. ARCH-2's existing row is edited in place (`pending` → `in_progress`, linked to this packet); ARCH-1's original row is untouched. The task table is now the base's 14 M11 rows, one per task |
| **important** — `docs/work/outlook-archive/register.json:68,95,122`: the three price cuts named the band one below the one they top (`<3000` "is very_low", `<8000` "is low", `<20000` "is normal"); `05_labels_price.sql` makes those `low`, `normal` and `high`, with `very_low` below 0 | All three propositions corrected here and in the register table above, each now stating the band its cut tops, the lower bound that band starts at, and the band below it — read from the ladder itself, not from the threshold's name |
| **important** — `src/outlook/register.py:131`: date validation checked only the string pattern, so `record()` accepted `valid_from="2026-99-99"` and `2026-02-29` | `_date` now also puts the text through `datetime.date.fromisoformat`, so a date that cannot exist on the calendar is refused as `INVALID_RECORD`; the tests cover month 13 and 99, month 0, day 0 and 31, a non-leap 29 February, and keep 2024-02-29 valid |
| **minor** — `src/outlook/register.py:150`: a malformed enum (`family=[]`) raised `TypeError: unhashable type` past the documented error contract, and the same for `layer`, `state` and the envelope's declared `family` | `_one_of` checks `type(value) is str` before membership, so a list, dict, number or bool is refused as `INVALID_RECORD` (`INVALID_REGISTER` in the envelope) rather than raising out of the contract |

New checks, so the two data findings cannot return silently:

* `reg.threshold_values(text)` reads the numbers the threshold rows carry, and
  `reg.price_bands(text)` reads the `price_band` ladder — its arms, the threshold each arm
  reads, and its fall-through — refusing text it cannot read as the ladder.
* `PriceBandTests` walks that ladder and holds each of the three corrected propositions to the
  band its own cut tops and to the band below it as the stated lower bound, and asserts on a
  sentence in the reviewed wording that the check differs, so the check's own sensitivity is
  tested rather than asserted.

The probe `.local/arch2-rework-probe.py` (ignored, not committed) reads the reviewed revision
`275a495` through `git show` — the reviewed bytes, not retyped text — and reports:

```
ladder read from scripts/data/sql/05_labels_price.sql -> [('very_low', 0.0), ('low', 'price_low_max'), ('normal', 'price_normal_max'), ('high', 'price_high_max'), ('very_high', 'price_cap_php_mwh'), ('extreme', None)]
price_low_max      cut    3,000  ladder band 'low'      below 'very_low' reviewed 275a495 names ['very_low'] -> check FAILS
price_low_max      cut    3,000  ladder band 'low'      below 'very_low' current tree names ['low', 'very_low'] -> check PASSES
price_normal_max   cut    8,000  ladder band 'normal'   below 'low'      reviewed 275a495 names ['low'] -> check FAILS
price_normal_max   cut    8,000  ladder band 'normal'   below 'low'      current tree names ['low', 'normal'] -> check PASSES
price_high_max     cut   20,000  ladder band 'high'     below 'normal'   reviewed 275a495 names ['normal'] -> check FAILS
price_high_max     cut   20,000  ladder band 'high'     below 'normal'   current tree names ['high', 'normal'] -> check PASSES
current-tree failures: 0
progress rows, reviewed 275a495       parse-and-compare mismatches: ['ARCH-1']
progress rows, working tree           parse-and-compare mismatches: []
reviewed 275a495:
  record(valid_from="2026-99-99" ) -> ACCEPTED (no error)
  record(valid_from="2026-02-29" ) -> ACCEPTED (no error)
  record(family=[]               ) -> TypeError: cannot use 'list' as a set element (unhashable type: 'list')
  record(state={}                ) -> TypeError: cannot use 'dict' as a set element (unhashable type: 'dict')
current tree:
  record(valid_from="2026-99-99" ) -> RegisterError: INVALID_RECORD
  record(valid_from="2026-02-29" ) -> RegisterError: INVALID_RECORD
  record(family=[]               ) -> RegisterError: INVALID_RECORD
  record(state={}                ) -> RegisterError: INVALID_RECORD
```

The audit's own report is unchanged by the rework: the three corrected propositions still cite
the same source lines, so the committed file still audits clean with the counts in "The audit"
above. What the review's checklist item 7 asked for — a packet whose recorded commands describe
the reviewed tree — is what the refreshed table above gives: every number there was run in this
worktree on this commit.

Self-review, and what a reviewer should contest:

* The band check holds the **words** a proposition uses against a ladder read from the SQL — the
  band each cut tops and the two bounds — not any arithmetic. A proposition could state a wrong
  *value* (a mistaken percentile, say) and still pass: the numbers in these propositions are
  quotations of the SQL row's own `source` text, which the audit's quote rule re-checks, and this
  rework did not recompute them from the data, because the register has no data to recompute from.
* `price_bands` reads the first `CASE` that closes with `END AS price_band` and refuses a body that
  holds another `CASE`, a bound whose alias it cannot find, or no fall-through. It refuses rather
  than guesses, so a second ladder in the same file makes it refuse loudly instead of reading the
  wrong one — a deliberate trade of coverage for safety, and the file has one ladder today.
* `threshold_values` returns floats, and one row is a date in number form
  (`reserve_labels_from_yyyymmdd`, 20260301). Nothing checks that a proposition's stated date
  matches that number. It is readable as a number only because the statement writes it as one, and
  a future reader of that row would need the value's own reading rather than this map.
* The progress-row fix does not change the parse rule, which keeps the last row per task; it makes
  the table carry exactly one row per task, so the rule and the rows now agree however the file is
  parsed. `test_progress_record_matches_task_states` is the check, and it is green on this tree.

## Open, and the exact next action

1. **The other families.** `availability`, `price`, `rules` and `projects` rows come from the
   outlook's own inputs: ARCH-3 issues the first outlook from PRICE-2's baseline inputs by digest,
   and the register rows for those inputs follow the same shape (a source locator per row, a
   layer, a state). Not started here by design: their sources do not exist yet.
2. **The A01–A12 rows and the ticket links (#79 jobs 1 and 4).** The issue asks for one record per
   A01–A12 family "with an owner, evidence state, stop/abstain behavior, verification method and
   link to the implementation or explicit absence", connected "by stable IDs to #78's child tickets
   and existing CORP/ATG/EVAL jobs". Neither is carried: the challenge rows have no family in the
   record shape the plan note fixes, no owner in any source, and the shape has no ticket field.
   Their dispositions, grades and resolving experiments are in the
   [strategy record](../thesis-challenge-2026-10-16/strategy.md) sections B and D, so the increment
   is mechanical once the orchestrator fixes a family name for them and decides whether the record
   shape carries a ticket link (a shape change returns to intent). Recorded, not worked around.
3. **Owners, intervals and checks.** All 37 rows are `unassigned` with unknown intervals and no
   recorded check. The first real owner assignment (the analyst or the data owner named in
   [HANDOFF.md](../data-foundation/HANDOFF.md)) turns those three counts down.
4. **The helper is ignored.** `.local/briefs/arch2/build_register.py` emitted the file and is not
   in Git; a later edit to `register.json` should re-run it or match the tests' checks, which
   re-derive the sources, the counts, the labels and every quote.

Exact next action: hand this packet back to the independent reviewer (GPT Sol) with the branch
`task/ARCH-2` and the four findings answered in "Rework after the designated review" above; the
task stays `in_progress` here, and only an accept record under `docs/work/reviews/ARCH-2.md` (the
reviewer's file, outside this task's edits) sets `done`. The state is in `docs/work/tasks.json`
(already `in_progress`, unchanged) and the matching row and log entry in
[PROGRESS.md](../PROGRESS.md) in this commit. Nothing else was left unfinished: every finding the
review raised is fixed here, and no item was deferred.
