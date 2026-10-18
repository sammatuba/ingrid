# Review: CORE-1 S1 bundle renderer, composition and receipt

Change range `feat/h1-api-persistence..664fa97` on `task/CORE-1`; reviewed 2026-10-11.
Independent: reviewer GPT Astra (`gpt-6-astra`, effort low) through `codex exec -s read-only`;
author was the executor seat (DeepSeek V4.1 Flash) plus an orchestrator test fix. Scope
inspected: full diff and log against the integration branch, brief, working paper 5.3.
`scripts/seats/reviewer.sh` failed (`codex review` rejects `--base` with a prompt), so the
same prompt ran through `codex exec`; raw output kept under ignored `.local/reviews/`.

## Findings

| Severity | Path | Failure and evidence | Correction | Disposition |
|---|---|---|---|---|
| important | `src/judgment/bundle.py:256` | Noul flip rate compares form tops against the thresholded mean probability, not the modal top; Q6 probabilities `[0.49,0.49,0.49,1.0]` give flip rate 0.75 and instability where modal flip rate is 0.25 | Compute the receipt reference from modal form tops; add this counterexample; route any unspecified tie policy to intent | open |
| important | `src/judgment/bundle.py:151` | Form F3 only says "reverse order" in the instruction; passages are never reversed, so passage-order sensitivity is not exercised | Render a genuinely reversed passage presentation and test the sequence; if the frozen request cannot carry it, stop for intent revision | open |
| important | `src/judgment/bundle.py:147` | Option permutation lives only in dict insertion order, which canonical serialization erases; digests of F0 and F1 are indistinguishable on order | Encode presentation order explicitly in the permitted request structure; test serialization and digest sensitivity | open |
| important | `docs/work/probe-bundle/implementation.md:218` | Scope note lists five exception paths; scope reports six (omits `docs/work/FEEDBACK.md`) and does not print OK | List all six with dispositions; reconcile owner seat files with the integration branch through the owner | open |

Reviewer verification: targeted suite 13 OK; full suite 241 run with 30 errors from the
read-only sandbox's unwritable temp directories (no assertion failures); `plan.py check` and
`repo.py check` pass; scope fails with six paths. Orchestrator run of the full suite outside
the sandbox: 241 OK.

## Verification and fidelity

All six brief acceptance items are demonstrated by executed tests. Checklist items 2, 3
(behavioural divergence from section 5.3, not a contract edit), 7 and 8 answered no. Mode
labels, dependencies and unknowns are clean.

## Outcome and next action

**Verdict: rework.** Task stays `in_progress`. Executor fixes the three `bundle.py` findings on
`task/CORE-1` (or stops if F3 needs an intent revision); the orchestrator corrects the scope
note; the owner decides how the seat files from `e3bdcd9` reach `feat/h1-api-persistence`.
Then re-review on the same branch. This verdict implies no external approval or deployment.

## Re-review 1 (2026-10-11, commit `72d5b69`, independent, GPT Astra via `codex exec -s read-only`)

Prior findings 1-4 resolved: modal receipt reference, explicit passage and option order,
scope prints OK after the rebase onto `feat/h1-api-persistence`. Checklist items 1, 2, 4-7
yes; 3 and 8 no. Reviewer full suite: 246 run, 30 sandbox temp-dir errors; orchestrator run
outside the sandbox: 246 OK.

| Severity | Path | Failure and evidence | Correction | Disposition |
|---|---|---|---|---|
| important | `src/judgment/bundle.py:287` | Noul composition still aggregates Q6 by mean probability: `[0.49, 0.49, 0.49, 1.0]` has modal top `no` and flip rate 0.25 (stable), yet mean 0.6175 fires `earlier_observation`; working paper 5.2 and the frozen intent compose on the modal top; the regression test at `tests/test_probe_bundle.py:331` encodes the divergence | Use the modal Q6 top for the observation predicate; expect fall-through to `insufficient` for that fixture; any wish to keep mean-based noul composition goes to the guardian as an intent clarification | open |

**Verdict: rework.** Task stays `in_progress`.

## Re-review 2 (2026-10-11, commit `ae25419`, independent, GPT Astra via `codex exec -s read-only`)

Re-review 1 finding resolved (modal top for every noul predicate). Checklist items 1-7 yes;
8 no. Reviewer full suite: 247 run, 30 sandbox temp-dir errors; orchestrator outside the
sandbox: 247 OK.

| Severity | Path | Failure and evidence | Correction | Disposition |
|---|---|---|---|---|
| important | `src/judgment/bundle.py:309` | Noul probabilities are rounded before tops are chosen: Q3 `before` with every Q6 at `0.4999996` reports Q6 `yes`, `supports`; true tops are `no`, so fall-through `insufficient` | Choose tops from unrounded values; boundary regression test | open |
| important | `src/judgment/bundle.py:321` | Rounded polarity gaps are compared to the strict threshold: Q4 `[0.4000004, 0.1, 0.1, 0.1]` has gap `0.3000004 > tau_pol 0.3`, receipt reports `0.3`, stable, `supports` | Compare unrounded gaps; round only presented values; threshold-boundary test | open |

**Verdict: rework.** Task stays `in_progress`.

## Re-review 3 (2026-10-11, commit `52ee4f0`, independent, GPT Astra via `codex exec -s read-only`)

All prior findings resolved: modal composition, explicit presentation order, rounding only
at receipt presentation with boundary tests. Checklist items 1-8 all yes. Reviewer ran the
22 targeted tests (pass), scope (OK), `plan.py check` (OK), `repo.py check` (PASS); its full
suite hit 30 sandbox temp-dir errors and no assertion failures. Orchestrator full suite
outside the sandbox at the same commit: 251 OK.

Findings: none outstanding.

**Verdict: accept.** Reviewed commit `52ee4f0`. CORE-1 becomes `done`. This verdict implies
no merge, push, external approval or deployment.
