# Review: NUM-0

Reviewed commit `86223b5` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of commit `86223b5578b3069c0d440a15983a7c1fae6c59e6`, using the requested diff and log against `feat/h1-api-persistence`. One commit, four changed files; working tree clean. No files edited.
> 
> | Check | Result | Evidence |
> |---|---|---|
> | 1. Every brief acceptance item demonstrated | **yes** | Document inspection confirms the template’s five sections, exact field `assumed_available_capacity` in MW, target `price_php_mwh` in PHP/MWh, and explicit BigQuery-only TimesFM 3.0 restriction. These are intent-level checks; downstream SQL/model execution remains undemonstrated. |
> | 2. Changes confined to allowed paths | **yes** | Requested scope command printed `OK: all changed files inside NUM-0 allowed paths`. |
> | 3. Frozen contracts, acceptance and tests unchanged | **yes** | Diff contains only the new what-if packet and NUM-0 coordination updates; no contract, acceptance-text or test changes. |
> | 4. No effects or dependencies beyond the packet | **yes** | Documentation-only change; future BigQuery execution remains gated. |
> | 5. Mode labels truthful | **yes** | Intent lines 190–199 define explicit modes and Preview/directional labels; downstream checks are expressly unexecuted. No live receipt claimed. |
> | 6. Unknowns preserved; no invented facts | **no** | Intent line 98 promotes the estate’s tentative timezone interpretation to a fact; source SQL explicitly says it needs verification. |
> | 7. Packet records commands, results and handoff | **yes** | Intent lines 277–317 record open inputs, next action, interpreter and verification results. The author’s full-suite pass was not reproduced in this sandbox. |
> | 8. Consistent with governing documents and invariants | **no** | The path extends a validity-bounded accepted value beyond its reviewed period, and the history digest omits a model-input covariate. See findings. |
> 
> Executed verification:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 239 Markdown files, 1,007 local links, eight skills.
> - `/usr/bin/python3 scripts/plan.py scope NUM-0 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 41 tasks, 7 gates**.
> - `/usr/bin/python3 -B -m unittest discover -s tests` — **251 tests, FAILED (errors=30)**. Errors include inability to create temporary directories under the read-only sandbox. This does not establish a regression, but the suite was not green here.
> 
> Findings—all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/whatif/intent.md:79` | A value accepted for one validity period becomes the “accepted” capacity outside that period without supporting records. | Both paths use `L_new` outside W. In the document’s delayed-return example, `L_new = 0`, so both paths remain zero after the revised return date if the horizon extends past W. The history receives the same extrapolation, albeit labelled assumed. | Require a separately reviewed common path outside W, or restrict the supported horizon and return uncomputed where coverage is absent. Distinguish constructed context values from accepted assumptions throughout receipts. |
> | important | `docs/work/whatif/intent.md:98` | An unverified timezone becomes authoritative, while comparison of civil-time storage with date/instant validity bounds lacks an explicit normalization rule. This can shift which hours receive the delta. | `scripts/data/sql/02_intervals.sql:2–3` says the timestamps merely **suggest** Asia/Manila and require verification. Intent lines 73–74 interpret bounds in Asia/Manila, while lines 97–99 preserve unconverted stored timestamps. | Preserve timezone uncertainty; require verified provenance or an explicitly labelled assumption before execution. Define one normalization rule for storage, anchor and both date/instant bounds, with boundary examples. |
> | important | `docs/work/whatif/intent.md:205` | Equal history digests do not prove identical model history. | Digest inputs use the series-contract column set, which excludes `assumed_available_capacity_mw`; SQL line 122 adds that covariate to context rows. Different context covariate values can therefore retain the same history digest. | Hash the complete ordered context actually supplied to the model, including the constructed capacity covariate and its construction basis. Require a mismatch check when only that covariate changes. |
> 
> **Verdict: escalate.** The unresolved findings concern the proposed intent’s covariate, time and receipt contracts, so the guardian should resolve an intent revision before NUM-1 proceeds.
## Outcome and next action

**Verdict: escalate.**
Escalated: findings are in the what-if intent's covariate, time-zone and history-digest contracts. Marked blocked; the guardian rules whether they are corrected as NUM-0 rework or need a strategy question. NUM-1 waits. Off the critical path.

## Guardian ruling (2026-10-11, Claude Fable, read-only)

All three findings are correctable inside NUM-0's own intent; no owner question.
**Disposition: rework NUM-0 with these corrections.**

1. L_new outside W: forecast only W. Require W to begin at H0+1 and clip N to W's end
   (`horizon_clipped: true`); any other shape is `WHATIF_DELTA_WINDOW` (uncomputed), never
   extrapolated. Delete the "horizon outside W" row (intent line 79). Context rows stay
   identical on both paths but are labelled `covariate_past_basis: "constructed: level held
   constant; not observed, not an accepted assumption"`; receipts distinguish constructed
   from accepted values.
2. Time zone: stop asserting Asia/Manila (intent lines 73-74, 97-99, 230). One normalization
   rule in the stored civil-time space; `timezone_convention` becomes `assumed Asia/Manila,
   unverified (scripts/data/sql/02_intervals.sql:2-3)`; date-only bounds map to 00:00 in that
   civil space; instant bounds with an offset are refused (`WHATIF_CONFIG_INVALID`) until NUM-2
   verifies the zone; write out one boundary example.
3. History digest: hash the ordered `context_rows` exactly as supplied to the model, including
   `assumed_available_capacity_mw` and `covariate_past_basis`. The identical-digest acceptance
   and `WHATIF_HISTORY_MISMATCH` stay unchanged.

## Review round 2026-10-11 evening (commit `0211e45`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `0211e45f8ffae8d2125171226a487e6d005fd6c3` against `feat/h1-api-persistence`: four commits, five changed files. Inspected the requested diff/log and clean working tree. No files edited.
> 
> | Checklist item | Result | Evidence |
> |---|---|---|
> | 1. Every brief acceptance item demonstrated | **yes** | Document inspection confirms all five intent-template sections; exact fields and units at `intent.md:29`; BigQuery-only TimesFM 3.0 restriction at `intent.md:195`. These establish intent acceptance only. |
> | 2. Changes confined to allowed paths | **yes** | Requested scope command printed `OK: all changed files inside NUM-0 allowed paths`. |
> | 3. Frozen contracts, acceptance and tests unchanged | **yes** | Diff contains only the what-if packet, review record and NUM-0 coordination updates. |
> | 4. No effects or dependencies beyond the packet | **yes** | Documentation-only change; model calls and cloud writes remain gated (`intent.md:14`). |
> | 5. Mode labels truthful | **yes** | Explicit execution modes and Preview/directional labels (`intent.md:235`); downstream execution checks expressly remain unexecuted. |
> | 6. Unknowns preserved; no invented facts | **yes** | Timezone remains assumed/unverified (`intent.md:107`); constructed context is distinguished from accepted assumptions (`intent.md:102`); availability may remain unknown. |
> | 7. Packet records commands, results and handoff | **yes** | Verification logs, unresolved inputs and exact next action appear in the recovery and rework sections. Author-reported suite success was not reproduced here. |
> | 8. Consistent with governing documents and invariants | **yes** | Forecasts are confined to W; complete model context enters the history digest; proposal records remain unchanged; failures produce uncomputed results. These follow §5.6 and the recorded guardian ruling. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 240 Markdown files, 1,011 local links, eight skills.
> - `/usr/bin/python3 scripts/plan.py scope NUM-0 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 41 tasks, 7 gates**.
> - `/usr/bin/python3 -B -m unittest discover -s tests` — **251 tests, FAILED (errors=30)**; temporary-directory creation fails under the read-only sandbox. This run does not demonstrate a green suite.
> 
> Findings: **none outstanding**. The three previously reported important findings are resolved in the revised intent; runtime implementation and BigQuery execution remain undemonstrated downstream work.
> 
> **Verdict: accept.** NUM-0’s three intent-level acceptance items are demonstrated, and the guardian-directed corrections leave no unresolved blocking or important findings.
**Verdict: accept.** Accepted after the guardian-ruled rework; task done. NUM-1 is unblocked.
