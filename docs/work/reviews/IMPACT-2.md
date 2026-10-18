
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `68249cea`, 2026-10-17 13:28, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> # IMPACT-2 review: accept
> 
> Opus 5.5 reviewed this in the session, under the owner's 2026-10-17 allowance for the Codex outage. I did not write the change and I edited no files. I reviewed head `68249cea` against `feat/product-refine`. The branch has two commits: `429b4dea` and `68249cea`.
> 
> ## Commands I ran
> - **Verify:** `/usr/bin/python3 -m unittest tests.test_price_impact` ran 68 tests, all OK.
> - **Full offline suite:** `/usr/bin/python3 -m unittest discover -s tests` ran 1956 tests, OK (skipped=47). The browser-guarded classes skip by design here.
> - **Scope:** `/usr/bin/python3 scripts/plan.py scope IMPACT-2 feat/product-refine` printed `OK: all changed files inside IMPACT-2 allowed paths`.
> - **Plan check:** `plan.py check` printed `OK: 97 tasks, 8 gates`.
> - **Repo check:** `repo.py check` passed (500 Markdown files, 3375 links).
> - **Regenerated record:** `.local/price/impact.json` is 560,099 bytes, and its SHA-256 is `01fd520604c4…1775e95072`, which is the digest the packet records. The record's `label` and `direction_check.label` are the same text. That text names `lwap_final_hourly.csv 184036 rows sha256 3b3b0b66` and `portfolio_nodal_hourly_deid.csv 517164 rows sha256 30ebab15`. The direction check is still 19,468 of 82,080 changes material.
> - **Git hygiene:** `git ls-files .local` returns nothing, and the working tree is clean.
> 
> ## Checklist
> 1. **Acceptance items met by checks that ran: yes.**
>    - `demonstration_label(inputs)` builds the label inside `build_impact_record` from the same `verify_inputs` rows (`src/price/impact.py:118`, `:416`).
>    - The only fixed text left is the synthetic-portfolio sentence. No "pre-backfill" text and no export.md reference remain in `src/price/impact.py`.
>    - Tests prove that different digests or row counts give different labels. The RealExports test builds the label from the real verified inputs.
>    - `impact.md` records the new digest beside the two earlier ones. I confirmed that `ac7ef38f…` is real in the refresh record, section 2.
>    - The packet quotes the direction-check figures again, and the regenerated record confirms them.
> 2. **Nothing changed outside the allowed paths: yes.** Scope printed OK.
> 3. **No frozen contract or acceptance text changed, no test weakened: no, with a justified exception.**
>    - No frozen contract and no acceptance text changed.
>    - Three existing assertions were removed. Two pinned the old constant in `NoPortfolioByteInGit`, and one did so in `DemonstrationLabel`. The brief's Outputs section requires that constant to go, so the assertions could not be kept.
>    - Each removed assertion is replaced by a stronger check. RealExports keeps all of its assertions and adds one.
> 4. **No new dependency, service, credential, network call, model call or cloud effect: yes.** Standard library only. The only write is the authorized regeneration under `.local`.
> 5. **Mode labels are truthful: yes.** The label now names the bytes that were read. Every figure is still labelled as synthetic.
> 6. **Unknowns stayed unknown: yes.** The quoted figures match the regenerated record.
> 7. **Packet records interpreter, commands, results and next action: yes, with stale details.** See findings 2 and 3.
> 8. **No contradiction with the blueprint, strategy, working paper or invariants: yes.** The runner still states the materiality line before it scores anything.
> 
> ## Findings
> - **minor | `tests/test_price_impact.py:309`, `:749`**
>   - **What happened:** three assertions that pinned `DEMONSTRATION_LABEL` were removed, against the acceptance text "every existing assertion … is kept".
>   - **Evidence:** the brief's Outputs section removes that constant, and the diff shows the replacement checks.
>   - **Correction:** none needed in the code. The packet should say "three" where it says "two", in `impact.md`, "IMPACT-2 verification".
> - **minor | `docs/work/price-outlook/impact.md`, "IMPACT-2 verification"**
>   - **What happened:** the packet says the committed-tree runs were on `c62c619`, a commit that is not on the branch. It reports 1942 tests; I measured 1956.
>   - **Cause:** the branch was rebased after those runs, so the packet's commit id and count belong to an older base.
>   - **Evidence:** `git log feat/product-refine..HEAD` shows only `429b4dea` and `68249cea`.
>   - **Correction:** cite `68249cea` and the 1956-test run.
> - **minor | `docs/work/price-outlook/impact.md` acceptance table, and the `docs/work/tasks.json` note**
>   - **What happened:** the short form of the digest is written `01fd5206…50e95072`. The digest actually ends `…75e95072`.
>   - **Evidence:** the SHA-256 of the file and the full digest in the record table above it both end in `75e95072`.
>   - **Correction:** change it to `…75e95072`.
> 
> The text "pre-backfill" is still in `scripts/price/challengers.py:105` and in the grid page tests. Those files are outside this task's scope, so this is not a finding.
> 
> ## Verdict: accept
> Every acceptance item is demonstrated by checks I ran myself. The label is now built from the inputs the run verified, the regenerated record's digest is confirmed, and all three findings are minor fixes to the packet text.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
