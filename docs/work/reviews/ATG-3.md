
## Designated review (GPT Sol, independent, commit `5ae5541`, 2026-10-16 01:34, overnight round 1)

> Independent review of `feat/atg-overnight...5ae5541f4383707888f1f82a27f3d4046b774521`, including commits `5180560` and `5ae5541`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Required gap table and proposals exist, and repo check passes, but several data claims fail verification below. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope ATG-3 feat/atg-overnight` printed `OK`; only the research record, tasks.json and PROGRESS.md changed. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contract, existing acceptance text or test changed; section 6 explicitly proposes future acceptance text. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Diff contains documentation/state changes only; no added dependency, service or external call. |
> | 5 | Truthful mode labels | **Yes.** Replay, stored vectors and unmeasured canvas performance are explicitly distinguished from live inference. |
> | 6 | Unknowns preserved; no unsupported facts | **No.** Congestion totals and map reachability claims are unsupported or contradicted by the named records. |
> | 7 | Complete verification and handoff record | **No.** Commands, interpreter and next actions are recorded, but the passing-suite claim does not describe the reviewed tree, and the recorded commit is stale. |
> | 8 | Consistent with product/domain invariants | **No.** Incorrect attributed figures breach the evidence requirement; other boundaries, including unknown coordinates and replay labeling, are preserved. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/PROGRESS.md:117` | Duplicate task rows overwrite correct states when parsed, breaking repository verification. | Added ATG-1/ATG-2 rows say `pending`; existing rows and tasks.json say `in_progress`. `tests.test_plan` fails on ATG-1. | Remove duplicate rows and update the original ATG-3 row; rerun the suite and correct its recorded result. |
> | important | `docs/work/atg/research/map-and-views.md:466` | Proposed view publishes incorrect congestion totals. | Record says VISLUZ1 **625**, MINVIS1 **277**. Fresh in-memory build gives **1,060** and **531** congested intervals respectively. | Recompute from baked `congested` arrays and replace the figures. |
> | important | `docs/work/atg/research/map-and-views.md:222` | Coordinate duplication is treated as demonstrated click inaccessibility. | Scratch calculation is `sum(n−1)`, not hit testing. Different circle radii (`grid.js:152`) allow exposed portions of underlying circles. Also, view 12 says **299** sites share coordinates; actual shared-coordinate membership is **401**. | Distinguish 193 positions, 401 members of stacks and 299 excess sites; remove or demonstrate the exact unreachable count. |
> | important | `docs/work/atg/research/map-and-views.md:429` | Preservation checklist omits existing interactions, then becomes ATG-6’s acceptance boundary. | Section 3.8 omits chart-point click/hover and day-path click/hover from `docs/work/explore/intent.md`; acceptance item 7 requires only rows of 3.8. | Include those interactions explicitly in the preservation checklist and proposed acceptance. |
> | minor | `docs/work/atg/research/map-and-views.md:578` | Handoff identifies a commit outside the reviewed change history. | Record names `146d2ac`; requested branch log contains `5180560` and `5ae5541`. | Record the actual implementation commit and review range. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 385 Markdown files, 2,448 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-3 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, 8 gates.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **PASS**, nine files, zero contract violations.
> - `/usr/bin/python3 -m unittest discover -s tests` — **FAILED**, 895 tests, 1 failure, 201 errors, 29 skips. Errors include read-only sandbox temporary-directory failures; the task-state failure is independently reproducible.
> - `/usr/bin/python3 -B -m unittest tests.test_plan -v` — **FAILED**, eight tests, one failure on duplicate progress states.
> 
> **Verdict: rework.** Incorrect research figures and a reproducible task-state regression leave material acceptance and closing requirements unmet.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `b93db49`, 2026-10-16 01:46, overnight round 2)

> Independent review of `feat/atg-overnight...b93db49`. Inspected all five commits from `git log feat/atg-overnight..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Research, proposals and the required gap table exist; repo check passes. Exact map-reachability claims remain unsupported as stated. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK`; all four changed files are allowed. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Diff changes research, coordination and review records only. ATG-6 acceptance is explicitly proposed text. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** No runtime changes or added services; research names local inputs. |
> | 5 | Truthful mode labels | **Yes.** Replay, stored vectors and unmeasured canvas performance are distinguished explicitly. |
> | 6 | Unknowns preserved; no unsupported facts | **No.** The exact click-accessibility total ignores overlap between distinct coordinates; proposed link hit testing assigns temporal intervals to spatial marks without a supporting mapping. |
> | 7 | Verification and handoff recorded | **Yes.** Sections 7–8 name the interpreter, commands, results, corrections, unresolved decisions and next action. The recorded passing suite could not be reproduced in this sandbox. |
> | 8 | Consistent with product and domain invariants | **No.** The unsupported accessibility total and spatial interpretation of interval flags breach the requirement to keep claims within their evidence. Other boundaries are preserved. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/atg/research/map-and-views.md:229` | Counts same-coordinate occlusion as the exact total of sites inaccessible by map click. | `atg3-reach.py` checks only concentric circles. `grid.js:153` projects and rounds screen positions, so distinct coordinates also overlap. Applying its projection, radii and paint order gives **297** circles fully covered by a single later circle at a 1280×700 map box, and **303** at 390×700—already exceeding 257. Acceptance item 2 consequently overstates that 235 sites are clickable. | Describe 257 as the same-coordinate subset or lower bound; remove the exact clickable complement. An exact total requires viewport-specific hit testing that includes other positions and layers. |
> | important | `docs/work/atg/research/map-and-views.md:378` | Treats temporal congestion flags as spatially identifiable marks along a cable. | `hvdc.json` supplies `congested[interval]`, with no spatial congestion location. Existing `grid.js:443–447` places interval marks on the **chart’s time axis**. Thirty-two curve samples cannot identify which of 2,304 intervals a spatial mark represents. | Draw the selected interval’s flag on the map; retain interval-specific marks and selection on the time chart, or explicitly define a separately labelled encoding. |
> | minor | `docs/work/atg/research/map-and-views.md:42` | Labels a partial primitive count as the total SVG child count. | The sum omits the six group elements created at `grid.js:122,135–139`, the title, and clock-dependent event rings; most counted primitives are descendants. | Label 753 as the counted drawing primitives, excluding containers, title and event rings. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 386 Markdown files, 2,447 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-3 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, 8 gates.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — **PASS**, nine files, zero contract violations.
> - Local recheck scripts reproduced the corrected congestion totals and principal data counts.
> - `/usr/bin/python3 -B -m unittest discover -s tests` — **FAILED**, 895 tests, 201 errors, 29 skips; errors include unavailable writable temporary directories in the read-only sandbox. This does not demonstrate a passing full suite.
> 
> **Verdict: rework.** Material research claims still exceed their demonstrated evidence and would carry incorrect assumptions into ATG-6.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `0dabe08`, 2026-10-16 09:36, overnight round 1)

> Independent review of `feat/atg-overnight...0dabe080527b`, covering both commits (`59b6de9`, `0dabe08`). No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Research sections 1–4 attribute data claims to files/report fields; section 5 contains all six required gap-table columns; section 6 proposes ATG-6 acceptance. Local rechecks reproduced the principal figures; repo check passed. |
> | 2 | Only allowed paths changed | **Yes.** Scope printed `OK`; only `map-and-views.md` and `PROGRESS.md` changed. Working tree is clean. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Documentation-only diff; no frozen contract, existing task acceptance or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** No runtime changes, dependencies or external calls added. Counts derive from local records. |
> | 5 | Truthful mode labels | **Yes.** Replay, stored vectors, proposed rendering and unmeasured performance remain explicitly distinguished. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Revised coverage counts are qualified bounds; congestion flags retain their temporal meaning. Missing coordinates and unavailable datasets remain unknown. |
> | 7 | Verification and handoff recorded | **Yes.** Sections 7–9 record interpreter, commands, results, unfinished decisions and next action; one minor commit-reference defect remains below. |
> | 8 | Consistent with product/domain invariants | **Yes.** Proposal preserves fail-closed locations, baked-data provenance, replay labeling and EXPL-1 interactions; ATG intent authorizes the map direction. |
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/atg/research/map-and-views.md:838` | Handoff names a commit outside the reviewed branch ancestry. | Text names `61196d6`; branch log contains rework commit `59b6de9` followed by `0dabe08`. `61196d6` exists but is not an ancestor of HEAD. | Name `59b6de9`, or explicitly identify `61196d6` as the original pre-transplant commit. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 396 Markdown files, 2,488 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-3 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, 8 gates.
> - `/usr/bin/python3 -B -m unittest discover -s tests` — **OK**, 1,109 tests, 58 skips. Browser-guarded skips are accepted per your review instructions; no browser run claimed here.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — nine files, zero violations.
> - Recorded local recheck scripts reproduced coverage counts **257**, **297/303**, principal data counts and congestion totals **1,060/531**.
> 
> **Verdict: accept.** Required research outputs and verification are demonstrated, prior material findings are resolved, and only a minor historical commit-reference correction remains.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `f1ac019`, 2026-10-16)

> Independent review of `feat/atg-overnight...0dabe080527b`, covering both commits (`59b6de9`, `0dabe08`). No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Research sections 1–4 attribute data claims to files/report fields; section 5 contains all six required gap-table columns; section 6 proposes ATG-6 acceptance. Local rechecks reproduced the principal figures; repo check passed. |
> | 2 | Only allowed paths changed | **Yes.** Scope printed `OK`; only `map-and-views.md` and `PROGRESS.md` changed. Working tree is clean. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Documentation-only diff; no frozen contract, existing task acceptance or test changed. |
> | 4 | No unauthorized dependency or external effect | **Yes.** No runtime changes, dependencies or external calls added. Counts derive from local records. |
> | 5 | Truthful mode labels | **Yes.** Replay, stored vectors, proposed rendering and unmeasured performance remain explicitly distinguished. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Revised coverage counts are qualified bounds; congestion flags retain their temporal meaning. Missing coordinates and unavailable datasets remain unknown. |
> | 7 | Verification and handoff recorded | **Yes.** Sections 7–9 record interpreter, commands, results, unfinished decisions and next action; one minor commit-reference defect remains below. |
> | 8 | Consistent with product/domain invariants | **Yes.** Proposal preserves fail-closed locations, baked-data provenance, replay labeling and EXPL-1 interactions; ATG intent authorizes the map direction. |
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/atg/research/map-and-views.md:838` | Handoff names a commit outside the reviewed branch ancestry. | Text names `61196d6`; branch log contains rework commit `59b6de9` followed by `0dabe08`. `61196d6` exists but is not an ancestor of HEAD. | Name `59b6de9`, or explicitly identify `61196d6` as the original pre-transplant commit. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 396 Markdown files, 2,488 links.
> - `/usr/bin/python3 scripts/plan.py scope ATG-3 feat/atg-overnight` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 79 tasks, 8 gates.
> - `/usr/bin/python3 -B -m unittest discover -s tests` — **OK**, 1,109 tests, 58 skips. Browser-guarded skips are accepted per your review instructions; no browser run claimed here.
> - `/usr/bin/python3 scripts/grid/build_data.py --check` — nine files, zero violations.
> - Recorded local recheck scripts reproduced coverage counts **257**, **297/303**, principal data counts and congestion totals **1,060/531**.
> 
> **Verdict: accept.** Required research outputs and verification are demonstrated, prior material findings are resolved, and only a minor historical commit-reference correction remains.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
