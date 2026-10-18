
## Designated review (GPT Sol, independent, commit `74be7fd`, 2026-10-16 01:05, overnight round 1)

> Independent review of commit `74be7fd29423c5c545ebc1b5a9a1e55d0a195856` against `feat/atg-overnight`. Inspected the requested log and diff; working tree was clean. No files edited.
> 
> Checklist:
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **No** | Gap tables exist and repo check passes, but inventory completeness and supported claims fail the findings below. |
> | 2 | **Yes** | `plan.py scope ATG-1 feat/atg-overnight` printed `OK`; only the research record, tasks.json and PROGRESS.md changed. |
> | 3 | **Yes** | Diff changes no frozen contract, existing acceptance text or test. Section 5 explicitly proposes future acceptance text. |
> | 4 | **Yes** | Documentation/state changes only; no dependency, service or execution code added. |
> | 5 | **Yes** | Sections 2.2–2.4 distinguish replay, stored model run, real fixtures and synthetic fixtures. Bake check reproduced the recorded outputs. |
> | 6 | **No** | The unsupported corpus absence claim converts an unknown into a negative fact; see finding below. |
> | 7 | **Yes** | Sections 7–8 record interpreter, commands, results, unfinished work and next actions. The claimed passing suite was not independently reproduced here. |
> | 8 | **No** | The proposed profile statement about corpus contents violates the invariant that unknowns remain unknown. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/atg/research/catalog-and-assets.md:81` | Wildcard/grouped entries do not deliver the required inventory of every dataset with schema and units. ATG-4 cannot reconstruct complete catalog entries from this handoff. | External tables are collapsed into `ext_<folder>` with an ellipsis; loaded tables use another wildcard. Rows 99–100 group multiple outputs without their individual schemas. | Enumerate the named datasets individually, with required metadata; explicitly label unavailable fields and their reasons. |
> | important | `docs/work/atg/research/catalog-and-assets.md:265` | Lack of a site index is presented as proof that no corpus document names a site, authorizing an unsupported profile claim. | The cited CORP-0 register inventories source families and document metadata; it does not demonstrate an exhaustive site-name search. The claim recurs at line 408. | State “site associations have not been established” until document-level evidence demonstrates presence or absence. |
> | important | `docs/work/atg/research/catalog-and-assets.md:96` | Incorrect cadence would propagate into the catalog’s coverage and schema description. | The inventory says `features` is hourly; `scripts/data/sql/09_features.sql:1` explicitly defines one row per **five-minute interval and region**. | Correct cadence to five-minute and cite that SQL definition. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 381 Markdown files, 2,414 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-1 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, 8 gates.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **exit 0**, nine files, zero violations; 617 sites, 492 located.
> - `/usr/bin/python3 -m unittest discover -s tests -v` — **failed**, 895 tests, 201 errors, 29 skips; sandbox prevented temporary-directory creation. This does not demonstrate a branch regression or reproduce the packet’s claimed 908-test pass.
> 
> **Verdict: rework** — the inventory needs complete dataset metadata, corrected cadence and an evidence-preserving corpus statement before downstream implementation can rely on it.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `d11c87c`, 2026-10-16 01:19, overnight round 2)

> Independent review of `d11c87c3517b` against `feat/atg-overnight`, covering commits `74be7fd`, `eb01491`, and `d11c87c`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **No.** Gap tables and proposed slices exist; repo check passes. Inventory accuracy still fails the findings below. |
> | 2 | Allowed paths only | **Yes.** Scope command printed `OK`; all four changed files are allowed. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Diff changes research, review and coordination records only; no frozen contract, existing acceptance text or test changed. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Documentation/state changes only; no service, credential, network, model or cloud execution added. |
> | 5 | Truthful mode labels | **Yes.** Sections 2.2–2.4 distinguish replay, recorded judgments, real samples and synthetic fixtures; bake check reproduced recorded counts. |
> | 6 | Unknowns preserved | **No.** Section 2.1 infers dataset-wide absence of views from local SQL searches. |
> | 7 | Complete verification/handoff record | **Yes.** Sections 7–9 identify interpreter, commands, results, unfinished work and next action. The recorded suite pass was not independently reproduced. |
> | 8 | Consistent with authority and invariants | **No.** The unsupported absence claim violates the requirement that unknowns remain unknown; the technology exclusion also contradicts an existing source profile. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/atg/research/catalog-and-assets.md:401` | Declares technology and operator information unavailable, incorrectly excluding supported asset-profile possibilities. | `docs/work/foundation-review-2026-10-13/sources/03-registered-capacity-list.md` records 549 rows with `market_participant_name`, `facility_name`, `type`, `classification`, Pmax/Pmin and ramp rate, including battery, solar and wind types. The inventory mentions this snapshot but omits its documented metadata; the exclusion propagates into lines 446–455. | Inventory source 03 completely. Distinguish documented attributes from fields already baked, preserving mapping, coverage and permission limits; revise the gap table accordingly. |
> | minor | `docs/work/atg/research/catalog-and-assets.md:88` | Converts absence of local view-creation statements into proof that no views exist in any dataset. | The cited grep checks repository SQL, not an exhaustive recorded dataset inventory. | State that no view definitions were found in the inspected scripts; leave broader existence unknown without recorded evidence. |
> | minor | `docs/work/atg/research/catalog-and-assets.md:210` | Describes a nonexistent `embargo` column, making the catalog schema inaccurate. | `scripts/data/sql/09_features.sql` emits `'embargo'` as a value of `split`; its final SELECT emits no separate `embargo` column. | Describe embargo as a `split` value and align the schema description with the final SELECT. |
> 
> Executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 382 Markdown files, 2,415 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-1 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, eight gates.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **exit 0**, nine files, zero violations; 617 sites, 492 located.
> - `/usr/bin/python3 -m unittest discover -s tests -v` — **failed**, 895 tests, 201 errors, 29 skips; sandbox has no usable temporary directory. A passing full suite was not demonstrated here.
> 
> **Verdict: rework** — correct the registration-snapshot omission and unsupported inventory statements before downstream tasks rely on this handoff.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `1075710`, 2026-10-16 09:18, overnight round 1)

> Independent review of `1075710393b9` against `feat/atg-overnight`. Reviewed the requested diff and log: one commit, two changed files. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Gap tables, proposed slices and owner questions exist; repository verification passes. The revised inventory still misstates facility-name coverage, and the claimed full-suite pass was not reproduced. |
> | 2 | Allowed paths only | **Yes.** Scope printed `OK`; only the research record and `PROGRESS.md` changed. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contract, task acceptance text or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Documentation changes only; no executable dependency, service or external call introduced. |
> | 5 | Truthful mode labels | **Yes.** The record distinguishes replay, stored judgments, real samples and synthetic fixtures. Bake verification reproduced nine files and zero violations. |
> | 6 | Unknowns preserved; no unsupported numbers | **No.** Line 618 converts a distinct-name count into a field-coverage count; the cited source does not support that interpretation. |
> | 7 | Complete verification and handoff record | **No.** Interpreter, results, unfinished work and next action are present, but two new verification commands contain ellipses instead of the exact executed code. |
> | 8 | Consistent with governing direction and invariants | **Yes.** The revised proposals preserve permission limits, unreviewed mappings and unknown corpus associations; no architectural or scope contradiction identified. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/atg/research/catalog-and-assets.md:618` | Misstates facility-name availability, giving downstream profiles an unsupported missing-data count. | Source 03 says **524 distinct names over 525 registered rows**; its nulls table assigns missing facility names to the 24 unregistered rows. It does not say only 524 registered nodes have names. | Preserve “524 distinct facility names over 525 registered rows”; remove the unsupported coverage interpretation. |
> | minor | `docs/work/atg/research/catalog-and-assets.md:854` | New verification evidence cannot be reproduced from the packet. | Both `python3 -c` commands at lines 854 and 858 contain descriptive ellipses; the asserted 61-string check has no executable body. | Record the exact commands, including the checked strings, or a repository script reference. |
> | minor | `docs/work/atg/research/catalog-and-assets.md:217` | The features entry breaks into multiple Markdown table rows, detaching its schema explanation from its metadata. | Lines 218–220 continue the cell using raw newlines without table delimiters. | Keep the table entry on one physical line or move the explanation into a paragraph. |
> 
> Commands executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 396 Markdown files, 2,480 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-1 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, eight gates.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **exit 0**, nine files, zero violations; 617 sites, 492 located.
> - `/usr/bin/python3 -m unittest discover -s tests` — **FAILED**, 1,096 tests, two errors, 45 skips. Both browser setup classes failed parsing empty output as JSON. This does not establish a documentation-change regression, but a passing suite was not demonstrated here.
> 
> **Verdict: rework** — correct the unsupported facility-name coverage claim and repair the verification record before accepting the research handoff.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `1e357eb`, 2026-10-16 09:32, overnight round 2)

> Independent review of `1e357eb3e0c4` against `feat/atg-overnight`: inspected the four-commit log and three-file diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Research §§2–3 inventory datasets and entities with source references; §4 provides the six-column gap tables; §5 proposes acceptance text; §6 lists owner questions. Research remains under the required directory; repo check passes. |
> | 2 | Allowed paths only | **Yes.** Scope prints OK; changes are limited to the research record, `PROGRESS.md` and the allowed review record. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contract, task acceptance text or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Documentation-only diff; no dependency, executable call or service introduced. |
> | 5 | Truthful mode labels | **Yes.** The inventory distinguishes synthetic fixtures, real samples, replay data and recorded judgments. Bake check confirms nine files with zero violations. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** Snapshot attributes are distinguished from baked fields; permission and corpus associations remain unresolved. Source 03 confirms the corrected “524 distinct names over 525 registered rows.” The recorded 74-string check reproduces zero missing strings. |
> | 7 | Complete verification and handoff record | **Yes.** §§8–11 record interpreter, exact commands, results and rework; §7 records unfinished items and next actions. |
> | 8 | Consistent with governing direction and invariants | **Yes.** Proposals preserve replay timestamps, permission boundaries, unreviewed mappings and unknown associations. No unsupported live-data or forecast claim identified. |
> 
> Executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 396 Markdown files, 2,481 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-1 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, eight gates.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,109 tests, OK (skipped=58)**. Environment-guarded skips are accepted under the supplied review instructions; no browser execution claimed.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **exit 0**, nine files, zero violations; 617 sites, 492 located, 125 placeholders.
> 
> Findings: **None unresolved.** The prior important finding and two minor findings are corrected.
> 
> **Verdict: accept** — the research handoff demonstrates the required acceptance items, and verification passes with the permitted environment skips.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `3e18b3d`, 2026-10-16)

> Independent review of `1e357eb3e0c4` against `feat/atg-overnight`: inspected the four-commit log and three-file diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Research §§2–3 inventory datasets and entities with source references; §4 provides the six-column gap tables; §5 proposes acceptance text; §6 lists owner questions. Research remains under the required directory; repo check passes. |
> | 2 | Allowed paths only | **Yes.** Scope prints OK; changes are limited to the research record, `PROGRESS.md` and the allowed review record. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contract, task acceptance text or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Documentation-only diff; no dependency, executable call or service introduced. |
> | 5 | Truthful mode labels | **Yes.** The inventory distinguishes synthetic fixtures, real samples, replay data and recorded judgments. Bake check confirms nine files with zero violations. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** Snapshot attributes are distinguished from baked fields; permission and corpus associations remain unresolved. Source 03 confirms the corrected “524 distinct names over 525 registered rows.” The recorded 74-string check reproduces zero missing strings. |
> | 7 | Complete verification and handoff record | **Yes.** §§8–11 record interpreter, exact commands, results and rework; §7 records unfinished items and next actions. |
> | 8 | Consistent with governing direction and invariants | **Yes.** Proposals preserve replay timestamps, permission boundaries, unreviewed mappings and unknown associations. No unsupported live-data or forecast claim identified. |
> 
> Executed through `rtk proxy`:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 396 Markdown files, 2,481 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-1 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, eight gates.
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,109 tests, OK (skipped=58)**. Environment-guarded skips are accepted under the supplied review instructions; no browser execution claimed.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **exit 0**, nine files, zero violations; 617 sites, 492 located, 125 placeholders.
> 
> Findings: **None unresolved.** The prior important finding and two minor findings are corrected.
> 
> **Verdict: accept** — the research handoff demonstrates the required acceptance items, and verification passes with the permitted environment skips.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
