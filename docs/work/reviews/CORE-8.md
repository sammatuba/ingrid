
## Designated review 1 (GPT Sol, independent, commit `6198781`, 2026-10-13)

> Independent review of `8e8bad830e50108890930005a3e2bb8e24cce54b` against `task/CORE-9`, including the three commits from `git log task/CORE-9..HEAD`. Working tree was clean; no files edited.
> 
> | # | Checklist item | Answer and evidence |
> |---|---|---|
> | 1 | Every brief acceptance item demonstrated | **Yes.** The executed 305-test suite covers all 14 composition rows and `testing` against `available_capacity`. Fixture `--check` passes with new digests. Direct comparison confirms 20 Q2 changes, zero frozen-label changes, and two documented composition-label changes. |
> | 2 | All changes within allowed paths | **Yes against the requested CORE-9 base:** scope prints OK. **No for the checklist’s literal integration-base check:** that command lists nine inherited ancestor files and exits 1; these are outside this task’s diff. |
> | 3 | Frozen contracts and acceptance preserved; tests not weakened | **Yes.** Changes implement the v5 intent; artifact/API/receipt shapes remain untouched. The corpus version assertion changes from exact `h0.v1` to exact `h0.v2`; separate v1 coverage remains. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** The diff introduces no dependency, service, credential, model call or cloud effect. Fixture construction remains local. |
> | 5 | Truthful mode labels | **Yes.** Fixtures explicitly identify fictional synthetic inputs and annotation answers; no inference or forecast-skill claim is made. |
> | 6 | Unknowns preserved; no invented facts | **No.** The new annotation policy infers a forced outage solely from an absent plan, although affected passages only establish unavailability. |
> | 7 | Complete implementation packet | **Yes, with a documentation finding below.** It records interpreter, commands, results, unavailable ablation script and exact next action. |
> | 8 | Consistent with direction and domain invariants | **No.** Treating unspecified outage cause as forced conflicts with preserving unknowns and the brief’s prohibition on inferring case facts. |
> 
> Commands actually run:
> 
> - `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` — **OK:** 25 pairs, eight edge classes, 28 frozen labels; policy digest `0c2f32ea…b5483c`, fixture digest `4d95a1b4…1f6076`.
> - `/usr/bin/python3 scripts/plan.py scope CORE-8 task/CORE-9` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **305 tests, OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 45 tasks, seven gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 scripts/plan.py scope CORE-8 feat/h1-api-persistence` — **exit 1**, nine inherited paths listed.
> 
> The emulator suite was not rerun in this review; its passing result is packet-reported evidence.
> 
> Findings:
> 
> - **important | tests/fixtures/probe-bundle/build.py:150 | Unsupported outage classification becomes frozen evaluation truth | Policy maps “no plan stated” to `forced_outage`; `pb-po-2` at lines 279–288 merely says “out of service and remains unavailable.” The same inference affects `pb-na-2`, `pb-cl-3`, and `pb-lc-2/t0` | Require affirmative evidence of forced/unplanned outage. Record and hand back the unspecified-outage vocabulary gap under the stop condition; obtain an intent decision before another freeze.**
> - **minor | docs/work/probe-bundle/fixtures.md:672 | Incorrect verification evidence | The document reports integration-base scope as OK, but the executed command exits 1 and lists nine ancestor paths; implementation.md:97 correctly acknowledges this | Correct the fixture document to distinguish passing CORE-9 scope from failing integration-base scope.**
> 
> **Verdict: rework.** The acceptance checks pass mechanically, but the frozen annotations introduce unsupported forced-outage facts that must be resolved before acceptance.
**Verdict: rework.** Owner ruling Round 9 (docs/work/foundation-review-2026-10-13/strategy.md): keep inferring forced_outage when a notice states no plan; cite that ruling in fixtures.md for pb-po-2, pb-na-2, pb-cl-3 and pb-lc-2/t0 instead of changing them. Owner ruling on CORE-5: under v5 the live run reads challenges; re-check the pb-er-3/-4 human annotations under v5 and record any label that v5 now composes differently. The orchestrator rebuilt this branch on the accepted CORE-9 (only the three core-8 commits) on top of the merged EVAL-2 and CORE-3: the full suite now has 17 errors (tests.test_eval_probe_bundle fails to import with ReviewError 'record does not satisfy h0.v1 or h0.v2'; tests.test_systemone_adapters errors the same way). Make the whole offline suite green from inside your allowed paths (fixtures, bundle.py, test_probe_bundle); if a fix needs scripts/eval or tests/test_systemone_adapters.py, stop and report the exact change instead. Address every blocking/important row above; dispose of minors explicitly.

## Orchestrator decision on the stop condition (2026-10-13, orchestrator seat, not a designated review)

The handed-back changes are consequences of the owner-approved v5 vocabulary and rules, so CORE-8 now depends on
CORE-3 and EVAL-2 in `tasks.json` (both done and already in this branch's base), which puts
`tests/test_systemone_adapters.py` and `tests/test_eval_probe_bundle.py` inside its allowed paths. Apply exactly the two
changes recorded in the packet: the `ATOMIC['q2']` rename in the adapter tests, and the nine pinned counts plus the
`pb-er-1/t1` label (`supports` to `mixed`, via `direction_conflict`) in the evaluation test, each read off the measured v5
report, not edited to pass. Then the full offline suite must be green on this branch. Do not touch `scripts/eval/`.
State the new v5 evaluation figures in the packet: EVAL-3's report and REL-2's deck carry v4 figures and are refreshed
after CORE-8 merges.

## Orchestrator re-measure after rework 2 (2026-10-13, at `02341f5`)

On `task/CORE-8` (rebuilt on the accepted CORE-9, with CORE-3 and EVAL-2 now declared dependencies): full offline suite `Ran 432 tests in 6.012s` **OK**; `bash scripts/h1/test.sh` `Ran 71 tests` OK; `plan.py scope CORE-8 task/CORE-9` OK; plan and repository checks OK; `scripts/eval/` unchanged. With this branch the h0.v2 fixture coupling recorded on CORE-9 is resolved. Ready for the designated re-review against `task/CORE-9`.

## Designated review (GPT Sol, independent, commit `3faebeb`, 2026-10-14)

> Independent review of `3faebeb087895492d94a77fd69e1d319ee49f521` against `task/CORE-9`, using the requested diff and commit log. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed suite exercises all 14 composition rows and `testing` against `available_capacity`. Fixture check passes. Direct comparison confirms 20 Q2 changes, zero frozen-label changes, and two documented composition-label changes matching the v5 intent. |
> | 2 | Changes inside allowed paths | **No for the literal integration-base checklist; yes for this task’s diff.** CORE-9 scope prints OK. Integration-base scope exits 1 listing only inherited `docs/work/reviews/CORE-9.md`. |
> | 3 | Frozen contracts, acceptance and test strength preserved | **Yes.** Composer changes follow the approved v5 intent; h0.v2 fixture changes follow CORE-9. Tests retain behavioral assertions; evaluation expectations reflect measured results. |
> | 4 | No unauthorized dependencies or external effects | **Yes.** Diff adds no dependency, service, credential, network/model call or cloud effect. |
> | 5 | Truthful mode labels | **Yes.** Fixtures declare synthetic inputs and annotations; h0.v2 payloads carry `(synthetic=True, permission_ref=None)`. |
> | 6 | Unknowns preserved; no invented facts or results | **Yes.** Previously disputed forced-outage annotations now cite the explicit Round 9 owner ruling at `fixtures.md:615–621`. Frozen labels remain unchanged. |
> | 7 | Complete execution and handoff evidence | **Yes, with the minor inconsistency below.** Packet records interpreter, commands, results, deferred report refresh and independent re-review as next action. |
> | 8 | Consistent with product direction and invariants | **Yes.** Availability classification reads model representation; lineage, identity, cutoff and authorization boundaries remain intact. Domain readings follow the approved intent and owner ruling. |
> 
> Commands actually run:
> 
> - `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` — **OK:** 25 pairs, eight edge classes, 28 frozen labels; policy `0c2f32ea…b5483c`, fixtures `ce6cddf0…a979a996`.
> - `/usr/bin/python3 scripts/plan.py scope CORE-8 task/CORE-9` — **OK**.
> - `/usr/bin/python3 scripts/plan.py scope CORE-8 feat/h1-api-persistence` — **exit 1**, inherited CORE-9 review record only.
> - `/usr/bin/python3 -m unittest discover -s tests` — **432 tests, OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 45 tasks, seven gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> The emulator suite was not rerun; its 71-test passing result is packet-reported evidence.
> 
> Findings:
> 
> - **minor | docs/work/bundle-v5/implementation.md:446 | Contradictory handoff status says ablation numbers remain unavailable | Lines 374–397 already report measured v5 evaluation figures, and the executed evaluation tests pass | Say the downstream EVAL-3 report and REL-2 deck refresh remain pending; remove the claim that the numbers are unavailable.**
> 
> **Verdict: accept.** All acceptance items are demonstrated, the previous important finding has an explicit owner disposition, and only a minor documentation inconsistency remains.
**Verdict: accept.** Suite green and emulator 71 OK at 3faebeb; resolves the h0.v2 fixture coupling. Merges with CORE-9 and DATA-1.
