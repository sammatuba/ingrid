
## Designated review (GPT Sol, independent, commit `b3a3910`, 2026-10-16 17:43, overnight round 1)

> Independent review of `feat/price-outlook...b3a3910f2c7e`, including all four commits in `git log feat/price-outlook..HEAD`. No files edited.
> 
> Verification executed:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1,685 tests, OK (skipped=62)**. Expected browser skips are not failures.
> - `/usr/bin/python3 scripts/plan.py scope PRICE-2 feat/price-outlook` — **OK**.
> - `plan.py check` — **OK**; `repo.py check` — **PASS**.
> - Read-only replay of all 16 exported series — canonical scorecard bytes match; digest `15d5b4bd510fdbc46ad51686cbc0db3b193565616db12b8f17108990797bdf79`.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Stdlib imports and digest replay pass; marked short months still supply scored origins, demonstrated below. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed OK; working tree clean. |
> | 3 | Frozen contracts, acceptance and existing tests preserved | **Yes.** Diff adds baseline tests; no frozen contract, acceptance text or existing test changed. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** Implementation uses stdlib and local exports; no service, credential, model or cloud call introduced. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures and historical exported data are identified; no live inference claimed. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** Historical first availability remains explicitly unknown; stored scorecard reproduces from digest-verified exports. |
> | 7 | Complete verification and handoff packet | **Yes.** Packet records interpreter, commands, results, limitations and next action. |
> | 8 | Consistent with direction and domain invariants | **No.** Scoring origins inside marked short months contradicts the required exclusion rule. |
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/price/scorecard.py:426` | Fan stores `forecast − realized`, then adds its quantiles to the forecast, reversing the residual correction and corrupting p10/p90 scores. | Executed synthetic probe: constant actual 100 and forecast 80 produce both fan arms at 60; p10/p90 losses become 4/36. Historical outcomes require residual offsets toward 100. | Store `realized − forecast`, or correctly negate and reverse error quantiles; test asymmetric residuals and quantile ordering, then regenerate the scorecard. |
> | important | `src/price/scorecard.py:388` | Exclusion checks only the target window’s completeness; it never rejects an origin because its billing month is marked short. | Executed probe removes one hour on 2025-07-03. `derive_marks` marks `2025-07` short, yet origins June 26–July 2 and July 4 still score. | Exclude origins in marked short months explicitly; add day/week/month regression coverage and regenerate results. |
> | important | `src/price/baselines.py:272` | Weekly sampling is anchored to the embargo cutoff, shifting the requested “last week same interval” baseline by an extra day. | For target August 9, the executed probe reads August 1 as its first sample. The existing test at `tests/test_price_baselines.py:348` pins this eight-day lag. | Align samples to target clock intervals seven days earlier, repeating the weekly pattern for longer horizons while respecting cutoff availability; update tests and regenerate results. |
> 
> **Verdict: rework.** Required marked-month exclusion fails, and the quantile fan and weekly alignment produce incorrect baseline scorecard results.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `db5ebd9`, 2026-10-16 18:04, overnight round 2)

> Independent review of `feat/price-outlook...db5ebd9`, including all seven commits in `git log feat/price-outlook..HEAD`. No files edited.
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1695 tests, OK (skipped=62)**; browser skips accepted as instructed.
> - `/usr/bin/python3 scripts/plan.py scope PRICE-2 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 93 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 -m unittest tests.test_price_baselines.RealExports -v` — **7 tests, OK**, including digest verification and deterministic reconstruction.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed tests cover marked-month exclusion without filling, stdlib imports, and reconstruction from digest-verified exports. |
> | 2 | Only allowed paths changed | **Yes.** Scope command printed OK; working tree clean. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen contract or acceptance changes; added tests and corrections to task-owned baseline tests. |
> | 4 | No unauthorized dependency or external effect | **Yes.** Stdlib implementation, local inputs; no added service, credential, network, model or cloud call. |
> | 5 | Truthful mode labels | **Yes.** Synthetic fixtures and historical exports identified; no live inference claimed. |
> | 6 | Unknowns preserved; no invented facts | **Yes.** First availability remains explicitly unknown; real-export checks passed. |
> | 7 | Complete verification and handoff packet | **Yes.** Packet records interpreter, commands, results, limitations and next action. |
> | 8 | Consistent with intent and domain invariants | **No.** The reported p10/p50/p90 forecasts can cross, undermining the quantile scorecard. |
> 
> Findings, both unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `src/price/scorecard.py:450` | Residual-adjusted p10/p90 surround an unadjusted point forecast labelled p50, allowing `p10 > p50` or `p50 > p90`. These cannot describe one predictive distribution. | Executed constant-residual probe produces `(p10,p50,p90) = (100,80,100)`. Existing `FanSign` tests demonstrate this same case but check only endpoint losses. | Enforce coherent quantile ordering. Keep point-forecast metrics separate if estimating the median from residuals; add positive/negative residual ordering regressions and regenerate the scorecard. |
> | minor | `scripts/price/baselines.py:135` | Written file includes a newline excluded from `content_digest`, despite documentation describing the digest as SHA-256 of file bytes. | Writer appends `"\n"`; `Scorecard.content_digest()` hashes canonical JSON without it. The CLI test strips the newline before hashing. | Hash exactly the written bytes, or explicitly document and test the canonical-JSON digest convention. |
> 
> **Verdict: rework.** The previous three findings are corrected, but crossed quantile forecasts remain an important scorecard correctness defect.

Verdict recorded by the overnight runner: **rework**. The orchestrator reads this record after the run.

## Designated review (GPT Sol, independent, commit `b481b13`, 2026-10-16 20:33, overnight round 1)

> Independent review of `b481b136c50c60600d756ff559a4cb2dc555f907` against `feat/price-outlook` (`2539d5e`). Inspected the requested diff and log, task brief, intent, rework decisions, implementation and verification packet. Working tree was clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Executed tests cover absent/short-month origin exclusion without filling, stdlib-only imports, digest validation and reproducibility. An independent replay of all 16 exported series exactly reproduced the stored scorecard. |
> | 2 | Changes within allowed paths | **Yes.** `plan.py scope PRICE-2 feat/price-outlook` printed `OK: all changed files inside PRICE-2 allowed paths`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contract or acceptance text changed. Test expectations changed to match the explicitly authorized quantile-ordering rule; coverage increased without added skips. |
> | 4 | No unauthorized dependencies or effects | **Yes.** Diff adds no dependency, service, credential, network/model call or cloud effect. |
> | 5 | Truthful mode labels | **Yes.** Tests identify synthetic fixtures; the packet identifies exported settlement data and a stored offline scorecard, without claiming live inference. |
> | 6 | Unknowns preserved | **Yes.** Missing windows remain excluded; empty metrics remain null. First availability remains explicitly unknown, with the embargo documented as a proxy. |
> | 7 | Complete verification and handoff packet | **Yes.** Packet records `/usr/bin/python3`, commands, results, limitations, `in_progress` state and re-review as the next action. One numerical typo remains below. |
> | 8 | Consistent with direction and invariants | **Yes.** Market/AP slices remain separate, lineage uses export digests, point metrics remain distinct from quantile losses, and no forecast-skill claim is made. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest discover -s tests` — **1705 tests, OK (skipped=62)**, including the expected browser skips.
> - `/usr/bin/python3 scripts/plan.py scope PRICE-2 feat/price-outlook` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 94 tasks, 8 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - In-memory replay of all 16 series — **3,783,620 bytes, identical to stored scorecard**, SHA-256 `41ea65218584435e77e75f6d800855ecd5b220f0fe66f4c6941ab858db98a305`.
> 
> Finding:
> 
> minor | `docs/work/price-outlook/baselines.md:520` | Incorrect explanatory loss value | Says the overforecast triple’s losses are `0 / 0 / 18`; the adjacent probe and implemented pinball formula give `0 / 0 / 2` | Replace `18` with `2`; documentation correction remains open.
> 
> **Verdict: accept.** All acceptance items were demonstrated, both prior findings are corrected, and the remaining documentation typo does not affect runtime behavior or the scorecard.

Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
