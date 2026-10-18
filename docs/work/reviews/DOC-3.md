# DOC-3 review record

Task: the explainer's deeper tier and its page at /explain. Plan note: [intent](../docs-for-people/intent.md). Task record: [implementation](../docs-for-people/implementation.md#task-record-doc-3).

## Designated review 1 (GPT Sol, independent, commit `4191241`, 2026-10-15 15:39 Manila)

> Independent review of `41912418f719`, against `feat/h1-api-persistence`. Reviewed all three commits and the branch diff; working tree was clean. No files edited.
>
> Verification:
>
> - Required verify command **ran**: `repo.py check` passed; unittest ran 43 tests, with **5 errors and 7 skips**. Errors arose because the read-only sandbox prevents temporary-directory creation. The browser test skipped.
> - `/usr/bin/python3 scripts/plan.py scope DOC-3 feat/h1-api-persistence`: **OK**.
> - `plan.py check`: **OK: 64 tasks, 7 gates**.
> - `build_explainer.py --check`: all four generated files match.
> - Full offline suite: **889 tests, 195 errors, 38 skips** in this sandbox; no passing-suite claim follows.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Plain-language and rebuild checks pass. Browser runs are recorded in the packet but were not reproduced here. Owner/teammate acceptance remains pending at `implementation.md:143`. Content discrepancies below also prevent acceptance. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed OK. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened/skipped | **Yes.** Frozen files remain unchanged; added task acceptance matches the supplied brief. Existing assertions remain, with asset expectations expanded and widget prose split at table-cell boundaries. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Builder uses the standard library; browser tooling is optional local tooling. No added production service, model call or cloud effect. |
> | 5 | Truthful mode labels | **Yes.** Chapters distinguish synthetic evaluation, recorded Gemini answers, replay data and the event-map experiment; no live inference is claimed. |
> | 6 | Unknowns preserved; no invented facts/numbers | **No.** Chapter 11’s “none of the 28” claim contradicts its cited evaluation record. |
> | 7 | Complete verification and handoff record | **No.** Packet records a failed full suite without identifying the failure or giving its correction and exact next action. It omits the required combined verify result. |
> | 8 | Consistent with governing method and invariants | **No.** The rule simulator and stability quiz contradict the implemented composition and threshold semantics. |
>
> Findings—all unresolved:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/docs/build_explainer.py:896` | The “whole rule table” teaches obsolete composition behavior. | It returns `supports` for earlier observed evidence regardless of Q8. `src/judgment/bundle.py:480` routes Q8=`challenges` to `mixed`. The widget also treats synchronization as testing and omits current event categories and availability guards. | Align widget choices, predicates and displayed rows with bundle v5; verify representative cases against the real composer, then regenerate outputs. |
> | important | `docs/explainer/11-rules-and-receipt.md:33` | A false evaluation claim hides measured failures of the contestable rule. | Says the row decided none of 28 compiles. Cited `evaluation.md:153` records three `earlier_observation` outcomes plus one `direction_conflict`, including wrong return-date outcomes. | Describe those recorded outcomes accurately and rebuild both page forms. |
> | important | `docs/explainer/11-rules-and-receipt.md:60` | The quiz marks the wrong stability interpretation as correct. | A flip rate of exactly 0.25 does **not** exceed 0.25. Runtime comparison is strict `>` at `src/judgment/bundle.py:380`; the chapter’s simulator also reports this case stable. Other unspecified answers prevent a unique final label. | Ask whether this rate alone causes instability, or provide complete inputs and a correct expected label. |
> | important | `docs/work/docs-for-people/implementation.md:143` | Required human acceptance remains undemonstrated. | Owner and teammate reading is listed as future work; no acceptance statements are recorded. | Obtain and record both readers’ conclusions on layers, flow and grounding. |
> | important | `docs/work/docs-for-people/implementation.md:139` | Verification handoff leaves a known suite failure unresolved. | Packet records `FAILED (failures=1, skipped=38)` without the failing test, diagnosis or disposition; no required combined verify result appears. | Identify and resolve the failure, run required checks in a writable environment, and record exact results and remaining actions. |
>
> **Verdict: rework.** Material explanations contradict committed runtime/evaluation evidence, required human acceptance is pending, and passing verification has not been demonstrated.

**Verdict: rework.** Orchestrator disposition: the rule-table widget now mirrors the fourteen rows of
`src/judgment/bundle.py` in the code's order with the availability guard and the direction-conflict row; the
contestable row's account states the comparison's recorded outcomes; the stability threshold is described as strict
everywhere, and the quiz asks about two differing wordings; the first commit's suite failure is named and its fix
recorded, with the current suite result; the owner's screenshot review of the explorable pages is recorded and the
reading of the deeper tier by the owner and the teammate stays pending, not claimed. Review 2 requested.

## Designated review 2 (GPT Sol, independent, commit `7dd9945`, 2026-10-15 16:07 Manila)

> Independent review of **`7dd99458e207`** against `feat/h1-api-persistence`, including all five branch commits and the diff. Working tree clean; no files edited.
>
> Verification actually run:
>
> - Required verify command: repository check **PASS**; **43 tests, 5 errors, 7 skips**. The errors concern temporary-directory creation denied by the read-only sandbox. Browser verification skipped.
> - `/usr/bin/python3 scripts/plan.py scope DOC-3 feat/h1-api-persistence`: **OK**.
> - `plan.py check`: **OK: 64 tasks, 7 gates**.
> - `build_explainer.py --check`: **all four generated files match**.
> - Full offline suite: **889 tests, 195 errors, 38 skips** in this sandbox; no passing-suite claim.
>
> | # | Checklist item | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Rebuild and chapter checks pass; browser runs are recorded but skipped here. Owner and teammate acceptance explicitly remains pending at `implementation.md:158–159`. |
> | 2 | All changes within allowed paths | **Yes.** Requested scope command printed OK. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened or skipped | **Yes.** Frozen definitions are unchanged; existing assertions remain, with asset expectations expanded and widget prose separated at table-cell boundaries. Browser skips depend on local tooling availability. |
> | 4 | No unauthorized dependency or external effect | **Yes.** No added production dependency, service, credential, model call or cloud effect appears in the diff. |
> | 5 | Truthful mode labels | **Yes.** Synthetic evaluation, stored Gemini results, replay data and illustrative vectors are identified as such. |
> | 6 | Unknowns preserved; no invented facts, receipts or numbers | **No.** The cutoff widget treats notices as known before their recorded posting seconds; see finding below. |
> | 7 | Complete verification and handoff record | **No.** The packet records suite results and pending human review, but omits the required combined verify command’s result for the current revision. |
> | 8 | Consistent with governing method and domain invariants | **No.** Early notice admission contradicts strict known-then filtering. The vector explanation also contradicts its implemented arithmetic. |
>
> Findings, all **open**:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/docs/build_explainer.py:398` | Cutoff filtering loses seconds and admits future evidence. | V133937 is assigned minute `819`, so cutoff **13:39** admits a notice posted **13:39:37**. The return notice similarly enters at **15:55**, before **15:55:56**. The committed case brief explicitly distinguishes the seconds before and after these postings. | Compare exact timestamps, or conservatively round availability up when retaining minute-only controls. Verify both sides of each posting boundary and rebuild all outputs. |
> | important | `scripts/docs/build_explainer.py:971` | The widget teaches that event order is irrelevant despite clipping the accumulated state after each event. | Reproducing its arithmetic gives **(45.64, 71.64)** for four “load dropping” events followed by “return to service”, versus **(54.19, 71.86)** in reverse order. | Explain that repeated clipping makes order matter. Qualify the related simple per-event linear attribution claim and verify an example that crosses the clipping limit. |
> | important | `docs/work/docs-for-people/implementation.md:158` | Required human acceptance remains undemonstrated. | The packet explicitly says the owner and teammate’s deeper-tier reading is pending. Screenshot approval concerns the explorable pages. | Obtain and record both readers’ assessments of the layers, flow and grounding before acceptance. |
> | minor | `docs/work/docs-for-people/implementation.md:163` | Current verification evidence omits a required command/result. | The updated entry reports the full suite, repository check, plan check and scope, but no result for the combined DOC-3 verify command. | Run that command in a writable environment and record its exact result, revision and any skips. |
>
> **Verdict: rework.** Required human acceptance remains pending, and the cutoff and vector explanations contain demonstrated correctness errors.

**Verdict: rework.** Orchestrator disposition: the cutoff slider now moves second by second over 13:20:00 to
16:06:40, so a notice posted at 13:39:37 is admitted at 13:39:37 and not at 13:39:00, and its caption names the
desk's one-second pairs; the vector-sum widget and chapter 13 say that the order does not matter below the clip and
does matter once it engages, with approximate shares; the combined verify command's result is recorded. The reading
of the deeper tier by the owner and the teammate is still theirs to give. Review 3 requested.

## Designated review 3 (GPT Sol, independent, commit `48ebdd9`, 2026-10-15 16:14 Manila)

> Independent review of `48ebdd95cc63` against `feat/h1-api-persistence`; inspected all six commits and the branch diff. Working tree clean. No files edited.
>
> Verification actually run:
>
> - Required verify: repository check **PASS**; **43 tests, 5 errors, 7 skips**. Errors reflect sandbox denial of temporary-directory creation; browser test skipped.
> - Requested scope command: **OK**, all changed files allowed.
> - `plan.py check`: **OK: 64 tasks, 7 gates**.
> - Explainer build check: **all four generated files match**.
> - Full offline suite: **889 tests, 195 errors, 38 skips** in this sandbox. No passing-suite claim.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Chapter plain-language and rebuild checks pass. Browser runs are recorded at `implementation.md:126`, but skipped here. Both human readings remain pending at line 173. |
> | 2 | All changes within allowed paths | **Yes.** `plan.py scope DOC-3 feat/h1-api-persistence` printed OK. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened or skipped | **Yes.** Frozen definitions remain unchanged; task acceptance matches the brief. Existing assertions remain; browser skips depend on tooling availability. |
> | 4 | No unauthorized dependency or external effect | **Yes.** No added production dependency, service, credential, model call or cloud effect appears in the diff. |
> | 5 | Truthful mode labels | **Yes.** Chapters distinguish synthetic evaluation, recorded Gemini results, replay data and illustrative vectors. |
> | 6 | Unknowns preserved; no invented facts or numbers | **No.** The claim-checker reports two correct abstentions, contradicting its committed evaluation record. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreter, commands, results, fixes and remaining human readings; lines 171–173 record the combined verify result and outstanding action. |
> | 8 | Consistent with governing method and invariants | **No.** Chapter 4’s quiz contradicts the implemented strict stability threshold and its own revised prose. |
>
> Findings, all **open**:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/explainer/04-judgment.md:76` | The quiz teaches that one differing wording out of four necessarily makes the judgment unstable. | Lines 78–80 mark that answer correct. This gives flip rate **0.25**; `src/judgment/bundle.py:378` requires **greater than 0.25**. Chapter 4’s revised prose also says one difference stays stable. | Use two differing wordings with otherwise stable inputs, correct the explanation, and regenerate both pages. |
> | important | `scripts/docs/build_explainer.py:941` | The claim-checker endorses an inflated evaluation result. | It says “two correct abstentions”; `docs/work/probe-bundle/evaluation.md`, sections 2–3, records **four abstentions, one correct**, with the gate’s effect confined to `pb-ng-2/t1`. Chapter 12’s table correctly reports one. | Change the widget to one correct abstention and regenerate all outputs. |
> | important | `docs/work/docs-for-people/implementation.md:173` | Required human acceptance remains undemonstrated. | The packet explicitly states that owner and teammate readings are pending. Screenshot approval does not demonstrate this acceptance item. | Obtain and record both readers’ assessments of the deeper tier’s layers, flow and grounding. |
>
> **Verdict: rework.** Two demonstrated teaching errors remain, and the required owner and teammate acceptance has not occurred.

**Verdict: rework.** Orchestrator disposition: chapter 4's quiz now asks about two differing wordings (flip rate 0.5,
above the strict 0.25); the claim checker states the comparison's abstentions as recorded, four with one correct,
kept by the sufficiency check. The reading of the deeper tier by the owner and the teammate stays theirs to give.
Review 4 requested.

## Designated review 4 (GPT Sol, independent, commit `e6339b9`, 2026-10-15 16:20 Manila)

> Independent review of `e6339b947167` against `feat/h1-api-persistence`, including all seven commits and the branch diff. Working tree clean; no files edited.
>
> Verification actually run:
>
> - Required verify command: repository check **PASS**; **43 tests, 5 errors, 7 skipped**. Errors arose because the read-only sandbox cannot create temporary directories. Browser checks skipped.
> - Requested scope command: **OK**, all changed files allowed.
> - `plan.py check`: **OK: 64 tasks, 7 gates**.
> - Explainer build check: **all four generated files match**.
> - Full offline suite: **889 tests, 195 errors, 38 skipped**; no passing-suite claim.
>
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Chapter plain-language and rebuild checks pass. Browser runs are recorded in the packet but skipped here. Both required human readings remain pending at `implementation.md:179`. |
> | 2 | All changes within allowed paths | **Yes.** Requested scope command printed OK. |
> | 3 | Frozen contracts and acceptance unchanged; no tests weakened or skipped | **Yes.** Frozen contracts remain unchanged; acceptance matches the brief. Existing assertions remain, with asset expectations expanded. Browser skips depend on tooling availability. |
> | 4 | No unauthorized dependency or external effect | **Yes.** No added production dependency, service, credential, model call or cloud effect appears in the diff. |
> | 5 | Truthful mode labels | **Yes.** Synthetic evaluation, recorded Gemini results, replay data and illustrative vectors are distinguished. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes.** Revised abstention counts match the committed evaluation; cutoff handling preserves posting seconds. No invented case facts identified. |
> | 7 | Complete verification and handoff record | **Yes.** Packet records interpreter, commands, results, corrections and outstanding human readings. |
> | 8 | Consistent with governing method and invariants | **Yes.** Inspected explanations preserve analyst authority, strict cutoffs, evidence distinctions and limits on forecast claims. |
>
> Findings, both **open**:
>
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/docs-for-people/implementation.md:179` | Required human acceptance remains undemonstrated. | Packet explicitly states that owner and teammate readings remain pending. Screenshot approval does not demonstrate assessment of the deeper tier. | Record both readers’ assessments of the layers, flow and grounding before acceptance. |
> | minor | `scripts/repo.py:245` | Ignoring a false passive match suppresses later genuine passive voice in the same sentence. | For “The desk is open and the record is stored.”, the regex finds both matches, but the revised check discards `is open` and reports nothing. Reproduced in memory. | Iterate matches and report a qualifying passive after excluding non-participles; add a regression case. |
>
> **Verdict: rework.** The required owner and teammate acceptance remains pending, so all acceptance items have not been demonstrated.

**Verdict: rework, on one item.** Every content finding of reviews 1 to 3 is closed; the one open acceptance item is
the reading of the deeper tier by the owner and the teammate, which only they can give. The orchestrator requests no
further AI review until that reading is recorded.

