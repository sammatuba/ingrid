
## Designated review (GPT Sol, independent, commit `8a57b41`, 2026-10-16 02:44, overnight round 1)

> Independent review of `8a57b410bb87` against `feat/corpus-overnight`, covering the seven commits and 20-file diff. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **No.** Neither cutoff places any governing clause. The DOM shim passes, but browser cleanliness and passing suites were not confirmed in this sandbox. |
> | 2 | Changes within allowed paths | **Yes.** `/usr/bin/python3 scripts/plan.py scope CORP-5 feat/corpus-overnight` printed `OK: all changed files inside CORP-5 allowed paths`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen-contract or acceptance changes found. Existing PEDC assertions remain; new tests were added. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Builders use existing modules and local records; no new service, credential, model call or cloud write appears in the diff. |
> | 5 | Mode labels truthful | **No.** Available announcement passages are labelled “in force”; publication time is presented as receipt time. |
> | 6 | Unknowns preserved; facts not invented | **No.** Missing order, clause availability and analyst acceptance remain explicit, but the page asserts an unsupported receipt date. |
> | 7 | Packet contains required handoff evidence | **Yes.** `docs/work/corpus/case.md` records interpreter, commands, reported results, unfinished work and exact next actions. Reported green runs remain author evidence. |
> | 8 | Consistent with direction and domain invariants | **No.** The page conflates availability with legal force and publication with receipt; the earlier cutoff displays later evidence text. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | `scripts/grid/build_rules.py:313` | The required clause-in-force demonstration is absent. | All seven clauses return `not_placed / availability_unknown` at both cutoffs; the packet acknowledges this. | Supply valid availability evidence or a clearly labelled fixture demonstrating the complete required path. Keep real unknowns unresolved; do not count refusal alone as satisfying acceptance. |
> | important | `src/grid/event.js:238` | The earlier cutoff renders excluded announcement quotes. | `ruleNoticeHtml` renders `n.quote` regardless of status; the passing shim shows four `after_cutoff` notices in the day-before state. | Show exclusion metadata without later passage content in the earlier state; test absence of that content. |
> | important | `src/grid/event.js:205` | Passage availability becomes an assertion of legal force. | Both `placed` and `in_force` render “in force at this cutoff”; the builder derives announcement placement solely from `passages_at`. | Label announcements “available at this cutoff”; reserve “in force” for demonstrated rule applicability. Update assertions accordingly. |
> | important | `scripts/grid/build_rules.py:388` | Publication date is presented as receipt date. | Advisory `t` is `2026-10-13`; `event.js:69` prints “as received.” The manifest records capture at `2026-10-15T16:20:12Z`. | Carry publication and first availability separately and render each with its recorded meaning. |
> 
> Verification actually run:
> 
> - Requested verify command: **failed**, 74 tests, 3 errors, 3 skips. Errors include unavailable writable temporary directories and browser-report parsing.
> - Full offline suite: **failed**, 1,104 tests, 234 errors, 29 skips; extensive temporary-directory failures under the read-only sandbox.
> - Scope: **OK**. `plan.py check`: **OK**. `repo.py check`: **PASS**.
> - `build_rules.py --check`: **current**.
> - Reserve-market DOM shim: **`ok: true`, `errors: []`**. This does not establish a clean real-browser run.
> 
> **Verdict: rework.** The required governing-clause path remains undemonstrated, and the rendered page makes materially incorrect time and force claims.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `6582694`, 2026-10-16 03:05, overnight round 2)

> Independent review of `6582694d1aa6` against `feat/corpus-overnight`, including the 11 commits and branch diff. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** The labelled fixture demonstrates clause placement under the DOM shim, but cutoff leakage remains elsewhere on the page. Browser cleanliness and passing suites were not independently established. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-5 allowed paths`. Working tree clean. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen-contract or acceptance edits found; existing tests remain, with additional coverage. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Changes use existing modules and local records; no added service, credential, model call or cloud write found. |
> | 5 | Mode labels truthful | **Yes.** The invented demonstration is explicitly labelled synthetic; prepared decisions and absent live loads are disclosed. |
> | 6 | Unknowns preserved; facts not invented | **No.** Unknown clause availability is rendered as “not in force,” converting an unresolved applicability question into a negative assertion. |
> | 7 | Packet records required handoff evidence | **Yes.** `docs/work/corpus/case.md` records interpreter, commands, reported results, unfinished items and next actions. Green results remain author-reported evidence. |
> | 8 | Consistent with direction and domain invariants | **No.** Later evidence remains visible while the earlier cutoff is selected, and unknown applicability becomes an assertion about legal force. |
> 
> Findings, both unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/grid/build_rules.py:446` | Cutoff filtering applies to the rules block but leaves later announcement text visible in the advisory and timeline. | Executed inspection of both built views: the initial cutoff’s notice has `status: not_placed` and `quote: null`, while `advisory.text` contains its full quote and `timeline[0].text` contains its opening. `event.js:81` and `:88` render those unconditionally; changing the rules tab does not update them. | Apply the selected cutoff to announcement content throughout the page. Add a test asserting excluded text is absent from the entire rendered page at the earlier cutoff. |
> | important | `src/grid/event.js:222` | A retrieval refusal is presented as proof that a clause was legally inactive. | All seven real-case clauses have `availability_unknown`, but their chips read “not in force at this cutoff.” The missing access evidence establishes inability to determine force, not absence of force. Browser assertions currently require this wording. | Render “not placed; force undetermined” for unknown availability or applicability. Keep the exclusion reason and test that unknowns never become negative legal conclusions. |
> 
> Verification actually run:
> 
> - `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_explainer`: **failed**, 89 tests, 3 errors, 3 skips. Errors included unavailable writable temporary directories and browser-report JSON parsing.
> - `/usr/bin/python3 -m unittest discover -s tests`: **failed**, 1,119 tests, 234 errors, 29 skips; extensive temporary-directory failures under this read-only sandbox.
> - `/usr/bin/python3 scripts/plan.py scope CORP-5 feat/corpus-overnight`: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Both rules-view `--check` commands: **current**.
> - Synthetic event DOM shim: **`ok: true`, `errors: []`**; this does not prove real-browser cleanliness.
> 
> **Verdict: rework.** Two important correctness findings remain, and the required passing verification has not been independently demonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `511c8f4`, 2026-10-16 10:24, overnight round 1)

> Independent review of `511c8f4a7e56` against `feat/corpus-overnight`, covering all three commits and the nine-file diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed store, builder and DOM-shim tests demonstrate the clause/amendment/announcement path using the explicitly labelled synthetic fixture. Real-case gaps remain disclosed. Citation checks and plain-language repository checks pass. The packet records clean browser runs at both widths. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-5 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen-contract or acceptance edits. Changed wording assertions correct the prior defect; coverage expands without adding skips. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Diff introduces no dependency, service, credential, network request, model call or cloud effect. |
> | 5 | Mode labels truthful | **Yes.** Synthetic demonstration, prepared decisions and absent live loads remain explicitly labelled in the fixture and packet. |
> | 6 | Unknowns preserved; facts not invented | **Yes.** `event.js:255` renders unknown availability as “not placed; force undetermined”; tests reject “not in force.” Missing real-case evidence remains unresolved. |
> | 7 | Required handoff evidence recorded | **Yes.** `docs/work/corpus/case.md` records interpreter, commands, results, reviewed code commit, unfinished work and exact next actions. |
> | 8 | Consistent with direction and domain invariants | **Yes.** Selected-cutoff withholding now covers advisory, timeline and rules content; availability remains distinct from legal force. Regression checks preserve the PEDC flow. |
> 
> Checks actually run:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_explainer` | 92 tests; **OK (skipped=5)** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 1,161 tests; **OK (skipped=44)** |
> | `/usr/bin/python3 scripts/plan.py scope CORP-5 feat/corpus-overnight` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK: 71 tasks, 8 gates** |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | Both real-case and synthetic rules-view `--check` commands | **current** |
> 
> Browser classes skipped as specified; browser-run evidence comes from the task packet, not a browser execution in this review.
> 
> Findings: **None.** Both prior important findings are resolved.
> 
> **Verdict: accept.** The rework fixes cutoff leakage and unsupported force wording, with passing verification and demonstrated fixture behavior while preserving real-case unknowns.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `394485b`, 2026-10-16)

> Independent review of `511c8f4a7e56` against `feat/corpus-overnight`, covering all three commits and the nine-file diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed store, builder and DOM-shim tests demonstrate the clause/amendment/announcement path using the explicitly labelled synthetic fixture. Real-case gaps remain disclosed. Citation checks and plain-language repository checks pass. The packet records clean browser runs at both widths. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-5 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen-contract or acceptance edits. Changed wording assertions correct the prior defect; coverage expands without adding skips. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Diff introduces no dependency, service, credential, network request, model call or cloud effect. |
> | 5 | Mode labels truthful | **Yes.** Synthetic demonstration, prepared decisions and absent live loads remain explicitly labelled in the fixture and packet. |
> | 6 | Unknowns preserved; facts not invented | **Yes.** `event.js:255` renders unknown availability as “not placed; force undetermined”; tests reject “not in force.” Missing real-case evidence remains unresolved. |
> | 7 | Required handoff evidence recorded | **Yes.** `docs/work/corpus/case.md` records interpreter, commands, results, reviewed code commit, unfinished work and exact next actions. |
> | 8 | Consistent with direction and domain invariants | **Yes.** Selected-cutoff withholding now covers advisory, timeline and rules content; availability remains distinct from legal force. Regression checks preserve the PEDC flow. |
> 
> Checks actually run:
> 
> | Command | Result |
> |---|---|
> | `/usr/bin/python3 -m unittest tests.test_grid_event tests.test_explainer` | 92 tests; **OK (skipped=5)** |
> | `/usr/bin/python3 -m unittest discover -s tests` | 1,161 tests; **OK (skipped=44)** |
> | `/usr/bin/python3 scripts/plan.py scope CORP-5 feat/corpus-overnight` | **OK** |
> | `/usr/bin/python3 scripts/plan.py check` | **OK: 71 tasks, 8 gates** |
> | `/usr/bin/python3 scripts/repo.py check` | **PASS** |
> | Both real-case and synthetic rules-view `--check` commands | **current** |
> 
> Browser classes skipped as specified; browser-run evidence comes from the task packet, not a browser execution in this review.
> 
> Findings: **None.** Both prior important findings are resolved.
> 
> **Verdict: accept.** The rework fixes cutoff leakage and unsupported force wording, with passing verification and demonstrated fixture behavior while preserving real-case unknowns.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
