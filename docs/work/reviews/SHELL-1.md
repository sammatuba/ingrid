# SHELL-1 review record

Reviewer: GPT through Codex (`./meos review`), read-only, not the author. Base `origin/main`
(`ca8b0846`). The reviewer's sandbox could not open loopback listeners or temporary files, so it
ran no browser check; it judged those from the harness code and the author's recorded runs.
Each round's report is copied below as the reviewer wrote it.

## Round 1 (branch at `02d9b384`): rework

> - important | `src/grid/ask.css:173` | A populated phone dock can cover the pinned navigation. | The phone rule replaces the header-aware height limit with `85vh`; at the tested 900px height, a full panel starts at 135px, above the packet’s documented 221px bar. The browser harness returns 404 for all data, so it does not exercise populated answers. | Retain a header-aware maximum height and test a long answer at phone sizes.
> 
> Scope check, repository check and plan check passed. The tracked working tree is clean; no files were edited. No credentials or unrelated changes were found.
> 
> Verification attempted: full suite ran 3,290 tests with 4 failures, 790 errors and 124 skips; sandbox restrictions on temporary files and loopback listeners prevent a usable acceptance result. Four shell source checks passed; browser verification could not run (`listen EPERM`). The reported baseline failures were not independently confirmed.
> 
> The phone layout needs correction and populated-browser verification before acceptance.
> VERDICT: rework
Author's response: fixed in `eb1cff97` (see the task record, review round 1).

## Round 2 (branch at `eb1cff97`): accept

> - minor | docs/work/desk-agent-and-book-2026-10-18/shell-1.md:87 | Verification coverage is overstated | The long-answer assertion skips widths ≥1400; it covers 390 and 1280, not 1440 | Correct the record or extend the harness.
> 
> R1 is resolved by the bar-aware height limit, supported by the harness and supplied old-rule/fixed-rule browser results.
> 
> Scope, repository, task-graph and whitespace checks pass; 17 focused tests pass. Full suite attempted: 3,290 tests, 4 failures, 790 errors, 124 skipped, with sandbox restrictions preventing complete verification. Browser checks could not run here; the 11 known baseline failures remain separately documented.
> 
> Working tree clean; no files edited. No blocking findings.
> 
> VERDICT: accept
> The fix addresses R1 within scope, with sufficient recorded browser evidence and only a minor coverage-description correction remaining.
Author's response: the record corrected (the long-answer check runs at 390 and 1280).
