# Review: CORE-7

Reviewed commit `7b42a92` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of `feat/h1-api-persistence...7b42a9228b57`, including commits `0f93092` and `7b42a92`. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **No.** Configuration and provider-body checks passed in isolated, filesystem-free execution; eight worker tests passed, including exact Vertex destination and headers. README inspected. End-to-end judgment/receipt and failure-file secret checks were blocked by temporary-directory setup failures; the packet reports prior passes, but I could not independently confirm them. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CORE-7 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes no frozen contract or acceptance text; existing test assertions remain, with nine tests added. |
> | 4 | No effects beyond packet | **Yes.** Added destination and environment-token mechanism match the intent; no new dependency or credential discovery. Review executed no external calls. |
> | 5 | Truthful mode labels | **Yes.** Vertex fixtures explicitly identify synthetic text and numbers; packet distinguishes these from the pending CORE-6 live run. |
> | 6 | Unknowns remain unknown | **Yes.** Synthetic metadata is labelled; semantic review remains pending and consequences uncomputed. |
> | 7 | Complete implementation record | **Yes.** Packet records Python 3.14.4, commands/results, limitations and exact next action. |
> | 8 | Consistent with product/domain invariants | **Yes.** Diff preserves citation validation, proposal-only behavior and analyst authority. The intent discrepancy below concerns transport failure behavior. |
> 
> Verification:
> 
> - Targeted command: **30 tests, 22 setup errors, eight passed**. Errors: no writable temporary directory in this sandbox.
> - Full offline suite: **260 tests, 36 errors**, all `FileNotFoundError` from temporary-directory setup.
> - `plan.py scope CORE-7 feat/h1-api-persistence`, `plan.py check`, and `repo.py check`: **passed**.
> - Two filesystem-independent config/provider test methods: **passed**, with temporary-directory setup omitted; this does not constitute a passing targeted suite.
> 
> Findings, both unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/adapters/gemini/transport.py:199` | Missing Vertex token exits before reserving the attempt and returns a different error from the specified failure contract. | Direct mocked-ledger execution produced `MODEL_CREDENTIAL_MISSING`, zero reservation calls and no receipt. Intent lines 66–67 require `MODEL_AUTH_FAILED` or `MODEL_CONFIG_INVALID` and a consumed attempt. | Implement the specified Vertex missing-token behavior and test its error, consumed allowance and receipt, preserving Developer behavior. |
> | minor | `src/adapters/gemini/README.md:90` | Operator documentation incorrectly says a missing token consumes the attempt. | Credential validation raises at transport line 201; reservation occurs at line 207. | Align documentation with the corrected, verified behavior. |
> 
> **Verdict: rework** — the Vertex missing-token path contradicts the intent, and end-to-end acceptance verification still needs a passing run in a writable environment.
## Outcome and next action

**Verdict: rework.**
Finding 1 resolved by an orchestrator correction to the intent (missing token refuses before reservation with `MODEL_CREDENTIAL_MISSING`, matching the Developer path). Executor fixes the README minor finding; then re-review.

## Review round 2026-10-11 evening (commit `716d3a0`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `feat/h1-api-persistence...716d3a02269d`, including all four branch commits. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Config checks, both provider bodies, exact Vertex destination/headers and worker stdout hygiene passed. README documents both configurations and token setup. Verified judgment/receipt and failure-file hygiene tests could not execute past sandbox setup. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope CORE-7 feat/h1-api-persistence` printed `OK: all changed files inside CORE-7 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen contract or acceptance-list changes; existing tests retain their assertions. The intent explicitly records the orchestrator’s missing-token correction. |
> | 4 | No effects beyond packet | **Yes.** The added Vertex host and environment-token mechanism match the packet; no SDK, credential discovery or automatic refresh added. |
> | 5 | Truthful mode labels | **Yes.** Vertex fixtures explicitly label synthetic text and counts; tests assert `synthetic_fixture`. Live execution remains CORE-6. |
> | 6 | Unknowns remain unknown | **Yes.** Missing response metadata remains null; synthetic judgments remain proposed with semantic review pending. |
> | 7 | Complete implementation record | **Yes.** Packet records interpreter, commands, results, limitations and next action. Its reported passes are distinguished from this review’s results below. |
> | 8 | Product/domain invariants preserved | **Yes.** Diff preserves citation validation, analyst authority, bounded attempts and proposal-only behavior. |
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest tests.test_gemini_transport -v`: **31 tests; eight passed, 23 setup errors**.
> - `/usr/bin/python3 -m unittest discover -s tests`: **261 tests; 37 setup errors**.
> - Both suites encountered `FileNotFoundError: No usable temporary directory found` under the read-only sandbox.
> - Requested scope check, `plan.py check`, and `repo.py check`: **passed**.
> - Three filesystem-independent config/provider test methods executed directly: **passed**. This does not constitute a passing targeted suite.
> 
> The previous missing-token implementation finding is resolved by the corrected intent; the README now matches that behavior. No additional production defect was established.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `tests/test_gemini_transport.py:475` | Acceptance verification remains incomplete because runner tests fail before exercising judgment receipts and failure-file secret hygiene. | Both required Vertex runner tests stopped in `TemporaryDirectory()` setup; the packet’s reported passes could not be independently reproduced. | Run the unchanged targeted and full offline suites on this commit in a writable test environment and provide reviewer-verifiable results. No production change is implied by this environment limitation. |
> 
> **Verdict: rework** — the prior code/documentation findings are resolved, but required end-to-end acceptance checks remain unverified in this review.
**Verdict: rework.** The only finding is that the reviewer's read-only sandbox cannot create temp directories, so two runner tests could not run there; the orchestrator ran the same suite outside the sandbox: 31 tests OK at this commit. Next session: re-review with a sandbox that permits temp directories, then CORE-6 live run.

## Re-review 2 (GPT Astra, independent, commit `fc7b47d`, sandbox with temp directories)

> HEAD confirmed: `fc7b47d105e35d2159ae965bc64477947e456c8a`. Working tree remained clean; no tracked files edited.
> 
> The diff `716d3a02269d..HEAD` is **not limited to review/packet records**: its 20 files include case documents and `scripts/seats/{rework,verify}.sh`, introduced by integration-history commit `b219fd0`. There are **no changes under `src/`, `tests/`, or `scripts/m3/`**.
> 
> | Requested check | Result |
> |---|---|
> | `unittest tests.test_gemini_transport -v` | **31 passed**, zero failures/errors |
> | `unittest discover -s tests` | **261 passed**, zero failures/errors |
> | `plan.py scope CORE-7 feat/h1-api-persistence` | **OK**, all changed files inside allowed paths |
> 
> Both Vertex runner tests passed:
> 
> - `test_vertex_recorded_shape_response_yields_verified_judgment_and_receipt`
> - `test_synthetic_vertex_token_never_reaches_receipt_failure_file_or_stdout`
> 
> No new defect findings. The previous verification finding is resolved.
> 
> **Verdict: accept** — the unchanged CORE-7 production and test code passes both required suites, including the previously blocked judgment-receipt and secret-hygiene checks.
**Verdict: accept.** The only open finding (suites not runnable in a read-only sandbox) is resolved: the reviewer ran both suites itself, 31/31 targeted and 261/261 full, including the Vertex judgment-receipt and token-hygiene runner tests. The diff since `716d3a0` beyond review records is integration history from the rebase (no `src/`, `tests/` or `scripts/m3/` change). CORE-7 is done; CORE-6 is unblocked.
