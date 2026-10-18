# The third outlook: November 2026 with the availability term (OUT-3)

**State of this record: the fixture loop is done, and the real third vintage `outlook-2026-11-system-v3`
was issued by the orchestrator on 2026-10-18 (see "Real run", "What the real run recorded").**
Every figure in the fixture sections comes from labelled synthetic inputs: invented outages, demand,
response and band values. None of those figures is a measurement of the Philippine market. Revised in
review round 1 (rework): forced outages only by default, exploratory outages listed instead of
refusing the run, the load-share weight on the system band, the bake's header facts in the values
file, the predecessor's input citations carried forward.

Decision: [strategy record](../desk-agent-and-book-2026-10-18/strategy.md), decisions 4 and 12, and
section 2 ("Can a decision move the outlook honestly?", "Is the event study on the right series?").
Task record: [out-3.md](../desk-agent-and-book-2026-10-18/out-3.md); the review record is
`docs/work/reviews/OUT-3.md`. The response comes from
[event-study.md](../desk-agent-and-book-2026-10-18/event-study.md) (OUT-2). The re-issue loop is
[reissue.md](reissue.md) (OUT-1). Code: `src/price/availability.py` (the method),
`scripts/outlook/availability.py` (the method run and its preview), `scripts/outlook/known_outages.sql`
(the export), `scripts/outlook/issue.py` (the issue).

## The method in one paragraph

`seasonal_plus_availability out-3.2` takes the second vintage's band and adds the measured response for
each **forced** outage record known at the 14 October cutoff for the November window (decision b; a
planned run is a second, labelled run). A known outage has a region, its MW lost and its whole clock
hours inside the window. Its response cell is the response record's cell for that region and size. For
each of its hours, the band's p50 moves by the cell's median times the MW lost over the regional mean
demand, times the region's load share; p10 moves by the cell's p10 and p90 by the cell's p90 in the
same way. The load share is the region's demand over the three regions' demand in the four weeks before
the cutoff: the vintage predicts the system price, and a regional move reaches it in proportion to the
region's load. Hours without a known outage keep the second vintage's band. The delta block is the mean
over the 744 hours, so a shift on a few hours moves the month by little. The demand of a November hour
is not known at the cutoff, so the method reads the same clock hour and weekday class in the four weeks
before it; that is a seasonal limit, stated in the run record. An outage in an exploratory cell is
listed as not applied unless the run allows exploratory cells.

## Fixture loop

The fixture predecessor has the real second vintage's shape: series `SYSTEM`, a month horizon from
2026-10-25T16:00Z to 2026-11-25T16:00Z, 744 hourly rows of `hour_start` and `value` only, and the same
header keys (`origin`, `cutoff_local`, `source`, `input` among them). The real values file has the same
shape, read-only: point values only, so the band is zero-width (p10 = p50 = p90 = value). Read-only,
every one of its 744 values reads back through `json.loads` and `json.dumps` to the same decimal text,
so an hour the method leaves alone shows a zero difference in the delta. The inputs are committed under
`tests/fixtures/price/event_study/out3/`, written by `make_out3_synthetic.py` and listed by its
`synthetic-label.json`.

The commands, run from the repository root (the documented root `.local/out3/fixture-loop` is ignored;
under it every stored path is relative, so the digests below reproduce):

```sh
F=tests/fixtures/price/event_study/out3
/usr/bin/python3 -c "import sys; sys.path.insert(0, '.'); import tests.test_price_availability as t; \
  print(t.build_predecessor('.local/out3/fixture-loop/archive')['content_digest'])"
/usr/bin/python3 scripts/outlook/availability.py --archive .local/out3/fixture-loop/archive \
    --predecessor fixture-2026-11-system-v2 --response $F/response-synthetic.json \
    --known-outages $F/known_outages-synthetic.csv --demand $F/demand_hourly-synthetic.csv \
    --cutoff 2026-10-14T16:00:00Z --outlook-id fixture-2026-11-system-v3 --issuer "OUT-3 test person" \
    --out .local/out3/fixture-loop/archive/values --method-out .local/out3/fixture-loop/method.json \
    --predecessor-input tests/fixtures/price/event_study/lwap_final_hourly-synthetic.csv
/usr/bin/python3 scripts/outlook/issue.py --archive .local/out3/fixture-loop/archive \
    --method-record .local/out3/fixture-loop/method.json --cutoff 2026-10-14T16:00:00Z \
    --outlook-id fixture-2026-11-system-v3 --issuer "OUT-3 test person" --issued-at 2026-10-20T00:00:00Z \
    --supersedes fixture-2026-11-system-v2 --reason method_changed --preview-out .local/out3/fixture-loop/preview.json
# the same command with --confirm fixture-confirmation-out3 (and without --preview-out) issues the vintage
```

### Inputs

| Input | Rows | SHA-256 |
|---|---|---|
| `known_outages-synthetic.csv` | 6 | `07b723851e591da3532f83de25dff7d2a3ad0cd1dba6e1c063068285b73fd94c` |
| `demand_hourly-synthetic.csv` | 2,106 | `236221986afcffefef018e47977c953bcc9c0112a216f58b5e76476f6f024abb` |
| `response-synthetic.json` (validates with `src.price.response.validate`) | 4 cells | `9fee91d5242d2c51967fa5d5d4cdbd9c6140d9ed284a7ffaafff2b898091655d` |
| `synthetic-label.json` | the label | `a08330cac56f88b114461842b5a99969b924a8a51258eaa10ffb001c38dac2be` |
| predecessor values `fixture-2026-11-system-v2.json` | 744 | `f8d94834f2d2e74399acefc45e8513e4faf6f8373659954284a310ce714624cd` |
| carried forward: `lwap_final_hourly-synthetic.csv` (OUT-2's fixture, the predecessor's input) | 8,640 | `c6dcc38c11fd42336e0f640421723f9e095696a719e0f62fbc8c41ab11596707` |

The demand fixture carries rows from 2026-10-15 00:00 to 05:00 Manila, after the cutoff, at an invented
99,999 MW. No proxy and no load share reads them; a test proves it. Its invented regional demand gives
the shares 0.7 (CLUZ), 0.15 (CVIS) and 0.15 (CMIN) on every day.

### Records written

| Record | Id | SHA-256 or content digest |
|---|---|---|
| predecessor (issued by the builder above, synthetic) | `fixture-2026-11-system-v2` | `ccf0db0851386e535d0b0c0e777c1b151c034cd8658b15903376d9ee57f43020` |
| values file, 744 rows | `fixture-2026-11-system-v3.json` | `c9ac6a87281db2e0b3e2555b24642a2b5b3b77042cb9f87b3fe3f1b7831190a9` |
| run record (the values file's sidecar) | `fixture-2026-11-system-v3.availability.json` | `aeadb0a3d98626ee71909744cc2c84955ef38097aea3fd993164773ff4f1abaa` |
| method record | `method.json` | `323f72d60d940da7f38711a92149e0955a60e12a446ec7834d9409bbc4601b40` |
| re-issue preview (its content digest; the command's `--preview-out` file) | `preview.json` | `33c519056d99b5d73a0f74bd195319cce613a12d0d00d5d4af5a3eb05bfb7c09` |
| third vintage, issued by `issue.py --confirm` | `fixture-2026-11-system-v3` | `0f62a24d82dc9eb7b6a43a537002d4afb0ff01f7b73b82cb9e8fdf3247bb71df` |

The values file and the run record carry no path and no unit name, so their two digests do not depend on
where they sit; `tests/test_price_availability.py` (`DocumentedDigests`) recomputes them and the input
digests in a scratch archive and finds them in this page. The other digests depend on the stored paths and
reproduce from the documented root. `verify()` on the fixture archive after the issue:
`{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`.

The third vintage's method version is `seasonal_plus_availability out-3.2 (forced outages)`; the
second's is `seasonal_average_billing_month price-2.1`, so `method_changed` holds. Its inputs cite, by
digest and first, the predecessor's own input under its own name (`lwap_final_hourly-synthetic.csv`),
then the predecessor's values file, the response record, the known outages, the demand and the run
record. Its belief set is the second vintage's five ids (task record, hand-back 1).

The values file states every header fact the site's data build requires: `series`, `series_label`,
`billing_month`, `horizon`, `origin`, `cutoff_local`, `window_start_hour_local`,
`window_end_hour_local`, `baseline`, `baseline_version`, `source`, and `input` as a file and a digest.
`origin` is the predecessor's (the window's first local day). `cutoff_local` is this run's cutoff in
Manila time (2026-10-15T00:00:00); `predecessor_cutoff_local` keeps the cutoff the baseline band was read
at. `source` and `input` name the predecessor's values file, the band these values rest on.
`TheValuesHeaderIsTheBakesAndTheBakePasses` bakes the fixture archive through `outlook_index_files` and
finds the third vintage current, superseding the second, with its band.

### What was applied, by hand

The forced run (the default; no exploratory cell allowed):

| Line | Unit | Region | Class | MW | Cell | Hours in window | Demand, MW | Regional shift: p10, p50, p90 | Weighted (share) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | SYN_K01 | CLUZ | forced | 350 | CLUZ 300+ MW, 14 events, measured | 6 (26 Oct 00:00 to 05:00) | 7,000 | -1,800, -400, +2,700 | -1,260, -280, +1,890 (0.7) |
| 4 | SYN_K03 | CLUZ | forced | 210 | CLUZ 150 to 300 MW, 15 events, measured | 3 (26 Oct 00:00 to 02:00) | 7,000 | -2,400, +600, +3,600 | -1,680, +420, +2,520 (0.7) |
| 5 | SYN_K04 | CMIN | forced | 120 | CMIN 50 to 150 MW, 4 events, **exploratory** | not applied: exploratory cell | | | |
| 6 | SYN_K05 | CVIS | forced | 350 | none: no CVIS 300+ MW cell | not applied | | | |
| 3 | SYN_K02 | CVIS | planned | 150 | | not applied: planned | | | |
| 7 | SYN_K06 | CLUZ | planned | 160 | | not applied: planned | | | |

Line 2: 350 MW over 7,000 MW is 0.05; the median -8,000 times 0.05 is -400, and CLUZ's load share 0.7
makes it -280 on the system band. In the hours 26 Oct 00:00 to 02:00 lines 2 and 4 both apply and the
shifts sum: p50 +140, p10 -2,940, p90 +4,410. The run record states the load shares and the factor an
unweighted shift would carry (CLUZ 1.428571, CVIS and CMIN 6.666667). The cells' spread straddles zero
in every applied cell, like the real run.

Two more runs are tested, not issued: with `--allow-exploratory` line 5 applies (size 0.08, regional
+800, -640, +16,000; weighted 0.15: +120, -96, +2,400 on 26 Oct 00:00 to 11:00) and the mean is
1,020 / 744 = 1.370968; with `--outage-class planned` only line 3 applies (CVIS 150 MW over 1,500 MW,
cell CVIS 150 to 300 MW, weighted p50 +7.5, p10 -750, p90 +225 on 12 hours of 2 Nov) and the mean is
90 / 744 = 0.120968.

### The delta against the predecessor

The sum of the p50 shifts is 3 × 140 + 3 × (-280) = -420 over 744 hours. The delta block of
`fixture-2026-11-system-v3` (`supersedes.delta`, previous values `f8d948…24cd`, new values
`c9ac6a…90a9`):

| Horizon | Hours | Mean difference | Mean absolute difference | Min | Max |
|---|---|---|---|---|---|
| month, 2026-10-25T16:00Z to 2026-11-25T16:00Z | 744 | -0.564516 | 1.693548 | -280.000000 | 140.000000 |

The run record's expected mean shift: p10 -16.935484, p50 -0.564516, p90 25.403226. The dilution, not
the response, sets the monthly figure.

### Stale marks answered

None. The third vintage is a mark-free re-issue (`reason: method_changed`, `stale_marks: []`,
`changed_assumption_ids: []`), OUT-3 decision (a). A method change changes no belief the second
vintage rests on, so no mark is honest.

### The labels travel

| Where | What it says |
|---|---|
| response record (cell) | CMIN 50 to 150 MW: `small_sample: true`, `label: exploratory` |
| run record (`.availability.json`) | `outage_class: forced`; `exploratory: false`; label "synthetic fixture run, a method demonstration; forced outages; measured cells only, 1 exploratory outage(s) not applied; response not distinguishable from zero at p10 and p90"; line 5 listed as not applied with its cell and count |
| values file | the same label, the class and the zero statement |
| vintage | `model_version` names the class: `seasonal_plus_availability out-3.2 (forced outages)`; with exploratory cells applied it reads `(forced outages, exploratory cells applied)` (tested); `synthetic: true`; the run record cited by digest |
| site data build | `outlook/index.json` carries the third vintage's `model_version` and band (tested, with the exploratory label) |
| vintage comparison | `availability.label` and `exploratory`, read back from the run record by digest |
| this page | this table |

The run record states in words: "The response is not distinguishable from zero at p10 and p90 in any
applied cell: in CLUZ 150 to 300 MW, CLUZ 300+ MW the p10 is below zero and the p90 above it, so the
sign of the shift is not settled." It names the response record by its SHA-256 (`9fee91d5…655d` here). A
cell of one event, or any small-sample cell, has no spread, so it is never counted as distinguishable
from zero: the statement names it as "too few events to tell" (tested on the real record's one-event
shape).

### Impact per account on the fixture book

BOOK-2's `load_vintage`, `build_impact` and `compare_impacts` (merged from `task/BOOK-2` at `38101319`,
BOOK-2 done) on the committed synthetic book `tests/fixtures/book/book-v1.json`. The materiality line,
stated first: 1,000,000 PHP, `at_or_above`, on the change of an account's p50 figure. Window: 26 October
to 1 November 2026, seven whole days inside the horizon, holding all 6 shifted hours. Question cutoff:
the date 2026-10-20, which closes at 2026-10-20T16:00Z; the third vintage was issued at
2026-10-20T00:00Z, so both vintages may price it. With the cutoff 2026-10-19 the third vintage is refused
`VINTAGE_AFTER_CUTOFF` (tested).

Records (documented root): impact against the predecessor
`e10c624209703ce0b23ec82f91338b252c7af93618481386c4750dc8fb50e6e3`, against the third vintage
`0dfacc363a9fa4c87e4cc90aadff2b77e085c5af1fcf28e2d223c45b719bc7d5`, the change record
`d041f1a92af4e64811a467266686d51dc2b360866f2da602508ab00fc0430706`.

Every peso figure is a method demonstration on the synthetic book, never a business number.

| Account | p50 before, PHP | p50 after, PHP | Change, PHP | Material |
|---|---|---|---|---|
| ACC-LUZ01 | -3,477,085.91 | -3,482,553.47 | -5,467.56 | no |
| ACC-LUZ02 | -3,918,768.68 | -3,923,162.57 | -4,393.89 | no |
| ACC-LUZ03 | -4,030,692.50 | -4,032,901.00 | -2,208.50 | no |
| ACC-LUZ04 | -1,829,666.83 | -1,832,418.95 | -2,752.12 | no |
| ACC-VIS01 | -4,665,909.64 | -4,674,582.07 | -8,672.43 | no |
| ACC-VIS02 | -4,657,650.37 | -4,659,177.77 | -1,527.40 | no |
| ACC-VIS03 | -796,059.30 | -797,654.04 | -1,594.74 | no |
| ACC-MIN01 | -4,849,209.88 | -4,856,218.14 | -7,008.26 | no |
| ACC-MIN02 | -2,131,540.09 | -2,136,205.18 | -4,665.09 | no |
| ACC-MIN03 | -4,331,483.48 | -4,334,366.36 | -2,882.88 | no |

No account reaches the line (material: 0 of 10). Before, the band is zero-width, so p10, p50 and p90 are
one figure (book total -34,688,066.68). After, the book total is p10 -35,838,515.55, p50 -34,729,239.55,
p90 -32,962,393.35: the spread comes from the response cells, not from the baseline. A system band prices
every node, regional or not (BOOK-2's `band_basis`). `ImpactPerAccountOnTheFixtureBook` recomputes this
table and finds each row here.

### The vintage comparison

`src.price.availability.compare_vintages(archive, "fixture-2026-11-system-v3")` composes, from the archive
only: both vintages (id, digest, method version, cutoff, issue instant, values digest, provenance), the
reason, the stale marks and changed beliefs (none here), the stored delta block, the confirmation
reference, and the run record's labels read back by digest (an edited run record is reported unread).
That is the archive side of acceptance line 3; the composer component and the dock renderer are DOCK-6's
(decision m).

## Real run

To be run by the orchestrator, from the main checkout's root, after OUT-3 merges. The executor ran none of
these commands against the real archive and wrote nothing into `.local/price` or `.local/outlook-archive`.
The same method run, issue, bake and suite were run on a scratch copy of the real archive (task record,
"Rework round 1").

**Deadline.** The archive's rule `issued_at <= horizon.start` means the November vintage must be issued
before **2026-10-25T16:00Z** (26 October 00:00 Manila). It must also be issued after the second vintage
(2026-10-17T03:00Z), with a cutoff no earlier than the second's (2026-09-25T16:00Z).

```sh
# 1. the known-outages export: a free dry run first, then the run under the cap
/usr/bin/python3 scripts/outlook/availability.py --print-query | bq query --use_legacy_sql=false --dry_run
/usr/bin/python3 scripts/outlook/availability.py --print-query \
    | bq query --use_legacy_sql=false --maximum_bytes_billed=1000000000 --format=csv --max_rows=100000 \
    > .local/price/known_outages.csv
sha256sum .local/price/known_outages.csv          # add it to .local/price/digests.json

# 2. the method run, forced outages, no exploratory cell (the defaults): writes the values file and its
#    run record into the archive's values folder, and the method record; prints the preview; issues nothing
/usr/bin/python3 scripts/outlook/availability.py --archive .local/outlook-archive \
    --predecessor outlook-2026-11-system-v2 --response .local/price/response.json \
    --known-outages .local/price/known_outages.csv --demand .local/price/demand_hourly.csv \
    --cutoff 2026-10-14T16:00:00Z --outlook-id outlook-2026-11-system-v3 --issuer "<person>" \
    --out .local/outlook-archive/values --method-out .local/price/method-2026-11-system-v3.json \
    --predecessor-input .local/price/lwap_final_hourly.csv --outage-class forced

# 3. the preview through the issue command, kept as the draft
/usr/bin/python3 scripts/outlook/issue.py --archive .local/outlook-archive \
    --method-record .local/price/method-2026-11-system-v3.json --cutoff 2026-10-14T16:00:00Z \
    --outlook-id outlook-2026-11-system-v3 --issuer "<person>" \
    --supersedes outlook-2026-11-system-v2 --reason method_changed \
    --preview-out .local/price/preview-2026-11-system-v3.json

# 4. the confirmed issue (the person's decision; issued-at before 2026-10-25T16:00Z)
/usr/bin/python3 scripts/outlook/issue.py --archive .local/outlook-archive \
    --method-record .local/price/method-2026-11-system-v3.json --cutoff 2026-10-14T16:00:00Z \
    --outlook-id outlook-2026-11-system-v3 --issuer "<person>" --issued-at <instant> \
    --supersedes outlook-2026-11-system-v2 --reason method_changed --confirm <confirmation reference>

# 5. the checks: verify, the full offline suite and a bake
/usr/bin/python3 -c "from src.outlook.records import OutlookArchive; print(OutlookArchive('.local/outlook-archive').verify())"
#    expected: {'outlooks': 3, 'receipts': 0, 'attributions': 0, 'problems': []}
/usr/bin/python3 scripts/plan.py check && /usr/bin/python3 -m unittest discover -s tests -p "test_*.py"
/usr/bin/python3 scripts/grid/build_all.py --data .local/out3/bake-check --force
#    expected: exit 0 and "violations": []; outlook/index.json lists the third vintage as current
```

The `--predecessor-input` file must be the export the second vintage cites, by name and digest
(`lwap_final_hourly.csv`, `3b3b0b66…2bc19`); the run refuses `PREDECESSOR_INPUT_MISSING` otherwise.
Outages in an exploratory cell (CLUZ 50 to 150 MW, CMIN 150 to 300 MW in the real record) are listed as
not applied and counted. A rerun with `--allow-exploratory` is the owner's decision, and the label then
travels; CMIN 150 to 300 MW has one event, and the run record names it "too few events to tell". A
planned run (`--outage-class planned`) is a second, labelled run, never the first.

Step 2 writes the values file, its run record and the method record before anyone confirms; each is an
exclusive create. If the owner stops after the preview and the run must be repeated, remove those three
files first (or choose another `--outlook-id`), or the rerun refuses `OUTPUT_EXISTS`.

If step 2 refuses `REPEATS_PREDECESSOR`, no known forced outage shifts any November hour. Then nothing is
written and no third vintage is issued; record the refusal here with the export's digest and row count.
That is the honest result the acceptance line allows ("or the issue is refused and recorded").

### What the real run recorded

Run by the orchestrator on 2026-10-18 with the commands above; recorded here from the records
themselves, read through the worktree's links (aggregates and digests only; no unit name, no row).

| Item | Value |
|---|---|
| `known_outages.csv` | 6 rows, SHA-256 `ae46e9599957531f5928ebaa7f5aadaf5abc0caea383e483efd06fabd286f980` (in `.local/price/digests.json`); classes: 1 forced, 5 planned; regions CMIN (5) and CVIS (1); dry-run upper bound 1,410,448 bytes, under a tenth of a cent (the bound stands in for billed bytes) |
| method run | `seasonal_plus_availability out-3.2 (forced outages)`, cutoff 2026-10-14T16:00:00Z, `--predecessor-input lwap_final_hourly.csv`, no `--allow-exploratory` |
| known outages | applied 1 (forced 1, planned 0); not applied 5 (other class 5, exploratory 0, no cell 0, no whole hour 0); shifted hours 455 of 744 |
| the applied outage | CMIN, forced, cell CMIN 50 to 150 MW (13 events, measured; p10 below zero, p90 above it), 455 hours in the window, 449 of them beyond the 6 measured hours; load share 0.143733 |
| load shares (run record) | CLUZ 0.71329, CVIS 0.142977, CMIN 0.143733, over 648 hours carrying all three regions; an unweighted shift would carry 1.401955, 6.994136 and 6.957326 |
| exploratory outages not applied | none; no owner decision needed |
| zero statement | "The response is not distinguishable from zero at p10 and p90 in any applied cell: in CMIN 50 to 150 MW the p10 is below zero and the p90 above it, so the sign of the shift is not settled." |
| label | "real inputs by digest; forced outages; measured cells only; response not distinguishable from zero at p10 and p90" |
| values file | `.local/outlook-archive/values/outlook-2026-11-system-v3.json`, 744 rows, SHA-256 `e0c9d164a6b7abe342064d5b6c81bbfa59b2b0dfb83c0f507dbc7da56f79033a` |
| run record | `outlook-2026-11-system-v3.availability.json`, SHA-256 `a8eceeb82fefa1d0d86054ee3936aec4266d4fa4d29fd85c94094de607346e84` |
| method record | `.local/price/method-2026-11-system-v3.json`, SHA-256 `3be526f222dda4b60addb88d8c42b0c9dca69672c04acd137c53ce3b66b98bdd` |
| preview digest | `3315dbcc67d141277627c5450e406a74215e009123f8ac5601bb2bfb80b42838` |
| third vintage | `outlook-2026-11-system-v3`, content digest `cc40eaa534e08aa772ca3d0739d6960033f7741c1460291277bab18d0e5e13e9`, issued 2026-10-18T04:18:44Z by "Sam", confirmation reference `owner-confirmation-2026-10-18-v3` (the owner's decision), `synthetic: false`; supersedes `outlook-2026-11-system-v2` (`f26f902e3ad865d649dc5cc7bd2c86aa5b3bcacb0278aff825e710f068231396`), reason `method_changed`, no stale mark; inputs cite `lwap_final_hourly.csv` first (carried forward), then the predecessor's values file, `response.json`, `known_outages.csv`, `demand_hourly.csv` and the run record |
| delta | `903437f3…f3dd` to `e0c9d164…033a`; month 2026-10-25T16:00Z to 2026-11-25T16:00Z: 744 hours, mean 33.650629, mean absolute 33.650629, min 0.000000, max 55.024326 PHP/MWh |
| expected mean shift (run record) | p10 -26.06138, p50 33.65063, p90 633.02708 |
| `verify()` | `{'outlooks': 3, 'receipts': 0, 'attributions': 0, 'problems': []}` (read again by the executor after the record) |
| full suite and bake | added by the orchestrator |

**Reading it.** One forced outage was known to be in progress at the cutoff, in Mindanao, with a stated end
inside November. It moves 455 of the 744 hours by the same weighted shift, 55.02 PHP/MWh at the median
(the maximum of the delta; the hours outside the outage move by zero), so the month moves by 33.65
PHP/MWh at the median. The spread is wide and straddles zero: the expected month shift runs from -26.06
at p10 to +633.03 at p90. Two limits weigh more here than on the fixture. First, 449 of the 455 hours lie
beyond the 6 measured hours: the run applies a six-hour response to about 19 days of one outage, as the run record
states (`hours_beyond_measured`). Second, the outage is a forced record known at the cutoff only because it
was in progress; its stated end is the end known on 14 October. The five planned records are listed,
not applied, as decision (b) requires.

**One record detail for the orchestrator.** The real vintage's `values_ref.path_hint` and most paths in
its method record are absolute paths of the main checkout (the run passed absolute paths that do not sit
under the running checkout's root, so `path_text` kept them absolute). The vintage reads back clean
here, because the main checkout's path exists on this machine. On another machine or checkout location
the bake would find no values file for the vintage and the scorer would not find it by its path hint.
The record is issued once and is not edited; a later re-issue, or a path rule that resolves the link,
can carry a relative hint (hand-back 8 in the task record).

### Impact per account on the fixture book, real second against real third

BOOK-2's `load_vintage`, `build_impact` and `compare_impacts` on the committed synthetic book, the real
second and third vintages read from the archive by digest. The stated line: 1,000,000 PHP,
`at_or_above`. Window: 1 to 7 November 2026, seven whole days inside the horizon; all 168 of its hours are
shifted. Question cutoff: the date 2026-10-18, which closes at 2026-10-18T16:00Z, after the third
vintage's issue at 04:18:44Z; with the cutoff 2026-10-17 the third vintage is refused
`VINTAGE_AFTER_CUTOFF`. Records, computed in the process and not stored: impact against the second
`7d4a515cbb243a7545208bdf2c630c92ed4c708c60cec3ddf81fa364e7d28050`, against the third
`1d50f0f45c45ee35617e05ec7d2d2f93e93056f0816bbfd33b58c743938a23c3`, the change record
`1d6256103f4467c1d7c6cf8aed10e52654f9c99caefe6fc579f51c0d1492ed2c`.

Only the change is shown: the before and after levels are the real band times invented volumes, and they
stay out of the repository. The change is the shift times each account's uncovered MWh in the window.
Every peso figure is a method demonstration on the synthetic book, never a business number.

| Account | Change of the p50 figure, PHP | Material |
|---|---|---|
| ACC-LUZ01 | 134,802.92 | no |
| ACC-LUZ02 | 105,685.58 | no |
| ACC-LUZ03 | 104,676.25 | no |
| ACC-LUZ04 | 66,997.63 | no |
| ACC-VIS01 | 210,946.61 | no |
| ACC-VIS02 | 94,724.35 | no |
| ACC-VIS03 | 33,191.97 | no |
| ACC-MIN01 | 185,439.10 | no |
| ACC-MIN02 | 88,867.94 | no |
| ACC-MIN03 | 112,876.89 | no |

No account reaches the line (material: 0 of 10); the ten changes sum to 1,138,209.24 PHP. The materiality
line, not the mechanism, decides: the third vintage moves the book, and no account crosses the line.

### The honest reading, written before the run

The real response cells are noisy (event-study.md, "Real run"). In every cell with more than one event
the p10 is negative and the p90 positive, so the spread straddles zero; the median of CLUZ 300+ MW is
negative. Applied to known outages, the November mean will move by a small amount whose sign is not
settled, and the vintage says so in its run record. No cell exists for CVIS or CMIN at 300 MW and above,
so such an outage is listed as not applied. The materiality line, not the mechanism, decides whether the
delta reaches the board.

Three limits of the real run, stated before it happens. First, the load-share weight reads the other
regions' prices as unmoved by the outage. From the real demand export the method's shares over the four
weeks before the cutoff are 0.713 (CLUZ), 0.143 (CVIS) and 0.144 (CMIN), over the 648 hours that carry
all three regions (computed read-only on a scratch copy; the run record states them). Second, a forced outage known at the cutoff for November is one in progress at
the cutoff with a stated end inside the window, so the forced set may be small or empty. Third, the
demand stand-in reads September and October demand for November hours.
