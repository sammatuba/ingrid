# DOC-4 review record

Task: the explainer opens on the whole system. Plan note: [intent](../docs-for-people/intent.md#doc-4-plan-note-2026-10-15). Task record: [implementation](../docs-for-people/implementation.md).

## Designated review 1 (GPT Sol, independent, commit `b485a9e` on `task/DOC-4`, 2026-10-15 22:39 Manila)

> Independent review of `b485a9ee6b6c` against `feat/h1-api-persistence`. Inspected the three commits, full branch diff and task records. Working tree was clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Owner acceptance remains explicitly pending in `implementation.md:270`. Map source links also fail the hosted-page reachability requirement described below. Browser and full-suite success could not be reproduced in this sandbox. |
> | 2 | Changes confined to allowed paths | **Yes.** `plan.py scope DOC-4 feat/h1-api-persistence` printed `OK: all changed files inside DOC-4 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened or skipped | **Yes.** The diff changes explainer content, builder, generated files, tests and coordination records. Frozen files and acceptance text are unchanged; browser coverage was extended. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Added builder code uses the standard library; browser tools already existed. New page controls use local DOM/storage operations. No deployment or model-call change appears in the diff. |
> | 5 | Truthful mode labels | **Yes.** System One is labelled recorded; System Two is explicitly designed with no live task; the scenario bridge is designed and unrun. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** All 18 node IDs and primary statuses match the inventory. PEDC disagreement, retain decision and token figures match the live-run record. Hero counts derive from node data. |
> | 7 | Complete implementation packet | **Yes.** The DOC-4 record names `/usr/bin/python3` 3.14.4, commands, reported results, unfinished owner acceptance and next action. The later orchestrator note records reading the reference page. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** The content preserves code/model/analyst authority, recorded-run distinctions and uncomputed consequences. No method contract change was found. |
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/docs/build_explainer.py:1505` | Map records cannot be reached from hosted `/explain`. | Source URLs are copied unchanged from repository-relative paths. For example, `../architecture/ontology-profile-v1.md` resolves to `/architecture/ontology-profile-v1.md`; neither application routes nor Hosting staging serve it. The browser harness checks that an anchor exists, but never follows it. | Provide reachable record destinations for the hosted output while preserving disk navigation; verify every map source destination through the served page. |
> | important | `docs/work/docs-for-people/implementation.md:270` | Required owner acceptance is absent. | The packet explicitly states the owner’s chapter-0 read is still open; the later reference-page note does not close it. | Obtain and record the owner’s assessment that chapter 0 shows the systems in place and how they fit the foundation. |
> 
> Verification executed:
> 
> - Requested verify command: repository check **PASS**; unittest portion **failed**, 102 tests, 14 errors, 10 skipped. Temporary-directory creation was denied; browser subprocesses returned no JSON. This does not establish a product failure or a passing browser check.
> - Scope: **OK**.
> - Plan integrity: **OK**, 65 tasks, 7 gates.
> - Four-file rebuild check: **PASS**, committed outputs match.
> - Full offline suite: **failed**, 893 tests, 201 errors, 29 skipped, with sandbox restrictions including unavailable writable temporary directories. The packet’s reported passing run was not independently reproduced.
> 
> **Verdict: rework.** Hosted map record navigation needs correction, and the required owner acceptance remains undemonstrated.

## Orchestrator reading of review 1 (2026-10-15)

- **Finding 1 (important) stands, and it is wider than the map.** Every repository-relative link on the served page fails on the site: the chapters carry them too (20 links to the working paper, 10 to decision system v1, 8 to the TimesFM and TabFM record, 5 to the status page, and more), since DOC-3. The single-file copy under `docs/explainer/` opens from the repository and those links work there; the site serves no Markdown. **Correction for the rework, builder only:** the site output (`site_page`, and the data attributes the map and the flow read) turns each repository-relative target (a `href` that is not `http(s)`, `#` or `/`) into a non-link reference that shows the link text and the repository path, with one visible note on the page that the records live in the repository; the single-file copy keeps its working links. The map detail and the `numbers` source render a link only when the `href` is non-empty. No external URL enters the served page (the release audit refuses the private repository address). Pin it: a test that the served `explain.html` carries no `href` to a `.md` target, and that `index.html` still does.
- **Finding 2 (owner acceptance) is the human item,** acceptance item 6, and the only one that needs the owner. It is not a rework item. The owner reads chapter 0 after the rework.
- **The reviewer's test errors are its sandbox** (no writable temporary directory; browser subprocesses could not start). The orchestrator's own run in this worktree after the rebase (`verify.sh`, commit `4084a36`): scope OK, plan OK, repo PASS, full suite `OK (skipped=29)`, verify `Ran 115 tests OK (skipped=10)`.

**Verdict recorded: rework** (finding 1).

## Orchestrator note after the rework (2026-10-15)

The full suite after the rework commit `9601300` failed one test outside the verify command: `tests/test_release_audit.py` flagged the new pin in `tests/test_explainer.py`, which held the private repository address as a literal (the audit scans every tracked file at HEAD). Orchestrator commit: the pin now asserts no code-host link at all. Suite after it: `OK (skipped=29)`.

## Designated review 2 (GPT Sol, independent, commit `6e04cd0` on `task/DOC-4`, 2026-10-15 22:54 Manila)

> Independent review of `6e04cd058ca0` against `feat/h1-api-persistence`, including the seven commits and branch diff. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Hosted map records remain unreachable; owner acceptance is explicitly pending. Browser and full-suite success could not be reproduced in this sandbox. |
> | 2 | Changes stay within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside DOC-4 allowed paths`. |
> | 3 | Contracts and acceptance unchanged; tests not weakened | **No.** Frozen contracts and acceptance text are unchanged, but the browser assertion now requires zero source links (`tests/test_explainer.py:337`), accepting behavior contrary to the record-access requirement. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Diff adds standard-library builder logic and browser interactions; no new runtime dependency, model call or cloud effect. |
> | 5 | Mode labels truthful | **Yes.** System One is labelled recorded; System Two designed; the PEDC example identifies the recorded run. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Node statuses follow the inventory; hero counts derive from node data; PEDC disagreement matches the committed live-run record. |
> | 7 | Packet records verification and handoff | **Yes.** Implementation packet names interpreter, commands, results, unfinished owner acceptance and next action. Its successful runs are author-reported evidence. |
> | 8 | Consistent with product and domain invariants | **Yes.** Code, model and analyst authority remain distinct; scenario bridge stays designed and unrun; no forecast-skill claim added. |
> 
> Checks executed:
> 
> - Requested verify command: repository check **PASS**; unittest **FAILED**, 104 tests, 14 errors, 10 skips. Errors included unavailable writable temporary directories and browser subprocess failures.
> - Full offline suite: **FAILED**, 895 tests, 201 errors, 29 skips, with sandbox-related temporary-directory and subprocess failures.
> - `plan.py scope DOC-4 feat/h1-api-persistence`: **OK**.
> - `plan.py check`: **OK**.
> - Builder `--check`: **PASS**, all four committed outputs match regeneration.
> 
> These sandbox failures do not establish application defects, but they do not demonstrate passing browser or full-suite acceptance here.
> 
> Findings, both unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/docs/build_explainer.py:883` | Hosted map deliberately removes every repository record destination, so readers cannot reach component records from the map. | `record_attrs()` returns an empty target for site output; `tests/test_explainer.py:337` requires zero detail anchors. Displaying a private repository path does not provide record access. | Provide accessible record destinations/content and test navigation to them. If that cannot fit the authorized scope, return the requirement to intent. |
> | important | `docs/work/docs-for-people/implementation.md:365` | Required owner confirmation has not occurred. | “The owner reads chapter 0” remains under “Still open”; no acceptance statement is recorded. | Obtain and record the owner’s reading and confirmation before requesting acceptance. |
> 
> **Verdict: rework.** Record access remains unmet and required owner acceptance has not been demonstrated.

## Orchestrator reading of review 2 and escalation (2026-10-15)

- **Finding 1 is a conflict inside the acceptance text, not a defect.** Item 1 says the reader can reach every component's record from the map. Review 1 showed that a repository link on the served page is a dead link, and the rework removed them as review 1's correction asked. The records are private repository files; the site serves no Markdown and the release audit refuses the private repository address, so no reachable target exists on the hosted page today. The single-file copy in the repository reaches every record (65 working links, pinned by test). **Escalated to the owner:** either item 1 is reworded ("from the repository copy; the served page names each record's path"), or a public copy of the records becomes a later task (the export decision, REL-5) and item 1 waits for it. The orchestrator recommends the rewording.
- **Finding 2 is the owner's reading** (item 6), still open.
- The reviewer's suite errors are its sandbox again (no writable temporary directory). Orchestrator run on `6e04cd0`: scope OK, plan OK, repo PASS, full suite `OK (skipped=29)`.

**Verdict recorded: rework, escalated** (acceptance wording, owner decision).

## Owner decision (2026-10-15)

The owner chose: keep acceptance item 1 as written and tie it to the export decision, REL-5. DOC-4 stays `in_progress` until a public copy of the cited records exists and the map can link to it; the served page names each record's repository path until then. The branch merges into `feat/h1-api-persistence` for the owner's read and the next batch deploy, as DOC-1 to DOC-3 did, with the state unchanged.

## Owner reading (2026-10-16)

The owner read chapter 0 and said "doc accepted": acceptance item 6 is met. Item 1 still waits for the public copy of the records (REL-5), by the owner's decision of 2026-10-15, so the state stays `in_progress` and the formal accept is recorded when REL-5 lands. The chapter goes to the site in the batch deploy of 2026-10-16.
