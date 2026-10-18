
## Designated review (GPT Sol, independent, commit `dc212c3`, 2026-10-16)

> 
> ## Designated review (GPT Sol, independent, commit `dc212c3`, 2026-10-16)
> 

**Verdict: accept.** <your one line>

## Designated review (GPT Sol, independent, commit `2bf60ca`, 2026-10-16 00:46, overnight round 1)

> Independent review of `feat/corpus-overnight...2bf60ca7e4b0`; inspected all four commits in `git log feat/corpus-overnight..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** All 30 index entries reproduced from local PDFs; four register consistency tests passed. Required synthetic PDF tests and full-suite success could not be demonstrated in this sandbox. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope CORP-0 feat/corpus-overnight` printed OK; nine changed files. |
> | 3 | Contracts/acceptance unchanged; no tests weakened or skipped | **No.** Frozen contracts and acceptance text are unchanged, but the final commit adds a skip guard around the required index tests. |
> | 4 | No effects beyond the packet | **Yes.** Indexing uses the authorized local pypdf copy; documented urllib acquisition is within the packet. No added cloud/model execution. |
> | 5 | Truthful mode labels | **Yes.** Tests identify their synthetic fixture; the walk distinguishes fetched evidence, unavailable ERC text and proposed page states. |
> | 6 | Unknowns preserved; no invented facts | **No.** ERC availability and legal basis remain explicitly unknown, but the asserted post-suspension change in reserve-series meaning lacks supporting evidence. |
> | 7 | Complete verification and handoff record | **Yes.** Walk §10 records interpreter, commands and results; §§7–9 record unknowns and next actions. Its historical results were not independently reproduced here. |
> | 8 | Consistent with product/domain invariants | **No.** The unsupported series reinterpretation compromises quantity semantics; the placeholder acceptance record compromises review provenance. |
> 
> Executed verification:
> 
> - Requested verify command: repository check **PASS**; focused tests **FAILED**, four tests ran and one setup error occurred because no temporary directory is writable.
> - Requested scope command: **OK**.
> - `plan.py check`: **OK: 71 tasks, 8 gates**.
> - Full offline suite: **FAILED**, 899 tests, 202 errors, 29 skipped; sandbox restrictions prevent confirming a green suite.
> - Read-only reproduction: all **30 document entries matched** the committed index; all **eight fetched HTML fingerprints matched** their bytes.
> 
> Findings below are unresolved.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/corpus/spike-reserve-market.md:237` | Changes `short[]` from shortfall to requirement/procurement outcome without evidence. | `src/grid/grid.js:715` defines reserve shortfall and requirement separately; the quoted suspension passage describes procurement arrangements, not a measurement-definition change. | Preserve shortfall semantics; record any post-suspension coverage or interpretation uncertainty separately, supported by series documentation. |
> | important | `tests/test_corpus_index.py:79` | Missing pypdf can yield a green run while skipping the required synthetic PDF checks. | Final commit adds `skipUnless(PYPDF, …)`; the brief explicitly stops work when a test must be skipped to pass. | Require the declared dependency for acceptance verification; fail clearly when absent and demonstrate all eight tests in a writable environment. |
> | important | `docs/work/reviews/CORP-0.md:8` | An unfilled template asserts independent acceptance without an evidenced review. | `**Verdict: accept.** <your one line>` names earlier commit `dc212c3`; `tasks.json:2646` retains that acceptance metadata despite the current `in_progress` state. | Mark the placeholder acceptance invalid/superseded and reconcile review metadata with an actual review of the deliverables. |
> 
> **Verdict: rework.** Unsupported series semantics, a required-test skip guard and invalid acceptance metadata remain unresolved, and passing acceptance verification has not been demonstrated in this review environment.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `b4f1903`, 2026-10-16 00:54, overnight round 2)

> Independent review of `feat/corpus-overnight...b4f19032a806`, including all six commits in `git log feat/corpus-overnight..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** All 30 document index entries reproduced exactly; register consistency checks passed; fetched quotations matched. Required synthetic PDF tests and a passing full suite were not demonstrated here. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside CORP-0 allowed paths`; nine files changed. |
> | 3 | Contracts and acceptance unchanged; tests not weakened/skipped | **Yes.** Frozen contracts and acceptance text are unchanged. The required-test skip guard was removed; missing pypdf now fails explicitly. |
> | 4 | No effects beyond the packet | **Yes.** Changes use the authorized local pypdf dependency and document permitted urllib acquisition; no added model or cloud execution. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures, fetched evidence and proposed event-page behavior are distinguished. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** ERC text, legal basis, amendment completeness and series coverage remain explicitly unknown. Both operative quotations matched fetched bytes; eight HTML fingerprints matched. |
> | 7 | Complete verification and handoff record | **Yes.** Walk §§9–11 record interpreter, commands, historical results, unfinished work and next actions. Historical green runs were not reproduced here. |
> | 8 | Consistent with product/domain invariants | **No.** The proposed pre-event judgment cites evidence that the same table excludes at its information cutoff. |
> 
> Executed checks:
> 
> - Requested verify command: repository check **PASS**; focused tests **FAILED**—six tests ran, with one setup error because the sandbox provides no writable temporary directory.
> - Requested scope command: **OK**.
> - `plan.py check`: **OK: 71 tasks, 8 gates**.
> - Full offline suite: **FAILED**, 901 tests, 202 errors, 29 skipped; sandbox restrictions prevent confirming acceptance.
> - Read-only reproduction: **30/30 index entries identical**, **8/8 HTML fingerprints matched**, both operative quotations verified verbatim.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/corpus/spike-reserve-market.md:239` | Proposed judgment uses unavailable evidence before its cutoff. | Line 235 excludes the suspension passage on current availability evidence, but line 239 supplies a review aid cited to those passages; lines 253–254 also describe the announcement as known before the action. | Make the pre-event judgment blocked/insufficient and exclude announcement-derived proposals until availability is evidenced. |
> | important | `docs/work/corpus/spike-reserve-market.md:225` | The required day-after comparison is replaced with a later, evidence-permitting cutoff. | Suspension starts October 14; the column labelled “One day after” uses October 16. | Include October 15 as the day-after state, preserving unavailable evidence as unavailable; retain October 16 as an additional post-fetch state. |
> | minor | `docs/work/reviews/CORP-0.md:8` | The review artifact still contains an unqualified placeholder acceptance. | `**Verdict: accept.** <your one line>` remains; PROGRESS invalidates it and task metadata correctly records rework. | Mark the placeholder invalid/superseded directly in the review record. |
> 
> **Verdict: rework.** The cutoff comparison remains inconsistent with the brief and known-then evidence rules, and passing acceptance verification remains unconfirmed.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `889d555`, 2026-10-16 09:18, overnight round 1)

> Independent review of `889d555b3132` against `feat/corpus-overnight`; inspected the requested diff and log: one commit, three changed files. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Reproduced the complete 30-document index exactly; all 30 Markdown register fingerprints match; four-family register tests pass; eight fetched HTML digests and both operative quotations match bytes. ERC fetch failure and retry actions, and ontology types/gaps, are documented. Required synthetic PDF tests pass, but the full suite fails. |
> | 2 | Only allowed paths changed | **Yes.** `plan.py scope CORP-0 feat/corpus-overnight` prints `OK: all changed files inside CORP-0 allowed paths`. |
> | 3 | Frozen contracts/acceptance unchanged; tests not weakened or skipped | **Yes.** Diff changes only the walk, progress log and task review metadata; no test or contract changes. |
> | 4 | No effects beyond the packet | **Yes.** No new dependencies or external calls introduced by this commit; existing local pypdf indexing and recorded urllib acquisition are authorized. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures, captured evidence and proposed page behavior are distinguished. October 16 is now explicitly “Post-fetch.” |
> | 6 | Unknowns preserved; no invented facts | **Yes.** ERC text, legal basis, amendment completeness and series coverage remain unknown with reasons. Both briefed cutoffs exclude the unavailable announcement and block judgment. |
> | 7 | Complete verification and handoff record | **Yes.** Walk §12 records interpreter, commands, historical results, unresolved items and next actions. The historical full-suite success was not reproduced here. |
> | 8 | Consistent with product/domain invariants | **Yes.** Revised §6 preserves known-then evidence boundaries and shortfall semantics; no runtime or frozen-contract change. The review-record defect below remains. |
> 
> Executed with Python 3.14.4:
> 
> - Requested verify command: **PASS**; repository check passes, **10 focused tests OK**, none skipped.
> - Requested scope command: **OK**.
> - `scripts/plan.py check`: **OK: 71 tasks, 8 gates**.
> - Full offline suite: **FAILED — 1123 tests, 2 errors, 29 skipped**. `test_explainer.ExplainerInTheBrowser` and `test_grid_page.BrowserPage` fail in setup while parsing empty browser stdout as JSON. The underlying browser failure was not established.
> - `git diff --check`: passes; working tree clean.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/corpus/spike-reserve-market.md:495` | Required full-suite acceptance remains unconfirmed on the reviewed head. | Current run fails in two browser setup classes; the packet records an earlier green run. This does not establish a regression caused by this diff. | Diagnose browser subprocess failures and demonstrate the unchanged full suite passing in a supported environment; retain exact results. |
> | minor | `docs/work/reviews/CORP-0.md:8` | Placeholder acceptance leaves contradictory review provenance. | `**Verdict: accept.** <your one line>` remains unqualified, although subsequent reviews and current task metadata say rework. | Mark that placeholder invalid/superseded directly in the review record. |
> 
> **Verdict: rework.** The two earlier cutoff findings are corrected, but the required passing full offline suite has not been demonstrated.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `e52608e`, 2026-10-16 09:28, overnight round 2)

> Independent review of `e52608e7596c` against `feat/corpus-overnight`: inspected the requested diff and all three branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Reproduced all 30 index entries; matched 30 Markdown fingerprints, eight fetched HTML digests and both operative quotations. Register tests confirm four families. ERC fetch failure, retry actions and ontology gaps are documented. Required tests and full suite pass. |
> | 2 | Only allowed paths changed | **Yes.** Four changed files; requested scope command printed `OK: all changed files inside CORP-0 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes.** Diff changes documentation and review metadata only. Browser skips are existing environment guards, as specified for this review. |
> | 4 | No effects beyond the packet | **Yes.** No new dependency or external execution introduced; existing pypdf indexing and recorded urllib acquisition fall within the brief. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures, fetched evidence and proposed page states are distinguished; October 16 is explicitly post-fetch. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Both briefed cutoffs exclude unavailable announcement evidence. ERC wording, legal basis, series coverage and amendment completeness remain unknown with reasons. |
> | 7 | Complete verification and handoff record | **Yes.** Walk §§12–13 record interpreter, commands, results, unresolved items and next actions. Retained logs demonstrate the author’s browser run. |
> | 8 | Consistent with product/domain invariants | **Yes.** Revised cutoff states preserve known-then boundaries and shortfall semantics; no frozen runtime contracts changed. |
> 
> Executed with Python 3.14.4:
> 
> - Requested verify command: **PASS**; 10 focused tests, none skipped.
> - Requested scope command: **OK**.
> - `scripts/plan.py check`: **OK: 71 tasks, 8 gates**.
> - Full offline suite: **1,138 tests, OK (skipped=44)**, including the expected 15 browser-test skips.
> - `git diff --check`: **PASS**.
> - Retained author logs: full suite **OK (skipped=29)**; browser classes **15 tests, OK**.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/reviews/CORP-0.md:8` | Placeholder acceptance leaves contradictory review provenance within the review artifact. | `**Verdict: accept.** <your one line>` remains, although the packet explicitly invalidates it and current task metadata records rework. | Mark the placeholder invalid/superseded directly in the review file. |
> 
> **Verdict: accept.** All required acceptance checks are demonstrated, the earlier substantive findings are corrected, and only a minor review-record cleanup remains.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `3f992a0`, 2026-10-16)

> Independent review of `e52608e7596c` against `feat/corpus-overnight`: inspected the requested diff and all three branch commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Reproduced all 30 index entries; matched 30 Markdown fingerprints, eight fetched HTML digests and both operative quotations. Register tests confirm four families. ERC fetch failure, retry actions and ontology gaps are documented. Required tests and full suite pass. |
> | 2 | Only allowed paths changed | **Yes.** Four changed files; requested scope command printed `OK: all changed files inside CORP-0 allowed paths`. |
> | 3 | Contracts/acceptance unchanged; tests not weakened or skipped | **Yes.** Diff changes documentation and review metadata only. Browser skips are existing environment guards, as specified for this review. |
> | 4 | No effects beyond the packet | **Yes.** No new dependency or external execution introduced; existing pypdf indexing and recorded urllib acquisition fall within the brief. |
> | 5 | Mode labels truthful | **Yes.** Synthetic fixtures, fetched evidence and proposed page states are distinguished; October 16 is explicitly post-fetch. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Both briefed cutoffs exclude unavailable announcement evidence. ERC wording, legal basis, series coverage and amendment completeness remain unknown with reasons. |
> | 7 | Complete verification and handoff record | **Yes.** Walk §§12–13 record interpreter, commands, results, unresolved items and next actions. Retained logs demonstrate the author’s browser run. |
> | 8 | Consistent with product/domain invariants | **Yes.** Revised cutoff states preserve known-then boundaries and shortfall semantics; no frozen runtime contracts changed. |
> 
> Executed with Python 3.14.4:
> 
> - Requested verify command: **PASS**; 10 focused tests, none skipped.
> - Requested scope command: **OK**.
> - `scripts/plan.py check`: **OK: 71 tasks, 8 gates**.
> - Full offline suite: **1,138 tests, OK (skipped=44)**, including the expected 15 browser-test skips.
> - `git diff --check`: **PASS**.
> - Retained author logs: full suite **OK (skipped=29)**; browser classes **15 tests, OK**.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/reviews/CORP-0.md:8` | Placeholder acceptance leaves contradictory review provenance within the review artifact. | `**Verdict: accept.** <your one line>` remains, although the packet explicitly invalidates it and current task metadata records rework. | Mark the placeholder invalid/superseded directly in the review file. |
> 
> **Verdict: accept.** All required acceptance checks are demonstrated, the earlier substantive findings are corrected, and only a minor review-record cleanup remains.
**Verdict: accept.** Owner accept after the round-3 Sol accept of 2026-10-16.
