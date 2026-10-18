# EVAL-3: Ablation report on fixtures

Review record for [EVAL-3](../tasks.json) (`Ablation report on fixtures`, lane EVAL, milestone M4,
`route: review`). The executor packet is [evaluation.md](../probe-bundle/evaluation.md); the
designated independent review (GPT Astra through Codex) has not been written yet, and only it sets
the task `done`.

## Interim review (orchestrator seat, Fable, commit c7033f4, 2026-10-12)

Interim review by the orchestrator seat (Claude Fable), which did not author the change. The
designated reviewer is out of credits and the owner decided building continues on interim reviews;
this section is the review-first list for the designated reviewer. It does **not** set the task
`done`. The designated independent review, when it is written, supersedes this one.

Read in order: `plan.py show EVAL-3` and `plan.py brief EVAL-3` (rails and allowed paths), the
process document (`docs/engineering/review-and-feedback.md`), the EVAL-2 interim review and its
six minor notes ([EVAL-2.md](EVAL-2.md)), working paper sections 5.2 and 6, the frozen annotation
policy's `earlier_return` and `contestable_rule` entries, `compose` in `src/judgment/bundle.py`
(read, not edited), the diff `e3531b3...c7033f4` (4 files, no untracked files), and the packet
`docs/work/probe-bundle/evaluation.md` in full.

### Commands run (worktree `.local/wt/EVAL-3`, `/usr/bin/python3`, no network, no model call)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/repo.py check` (the brief's verify command) | `Checked 262 Markdown files, 1241 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 295 tests in 3.165s` — `OK` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-3 e3531b3` | `OK: all changed files inside EVAL-3 allowed paths` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-3 feat/h1-api-persistence` | Lists `docs/work/reviews/CORE-2.md` and `docs/work/reviews/EVAL-2.md` only — the stacked parents' review records, as the packet's scope note says; `tests/test_eval_probe_bundle.py` is inside the allowed paths because EVAL-3 inherits its ancestors' owned paths (`plan.py brief` lists it) |
| `git diff e3531b3...HEAD --stat` | `PROGRESS.md` (+2 −1), `probe-bundle/evaluation.md` (+272), `tasks.json` (state only), `tests/test_eval_probe_bundle.py` (+76, three tests added, none removed or weakened) |
| `/usr/bin/python3 scripts/eval/probe_bundle.py --fixtures tests/fixtures/probe-bundle --out <scratch>/report.json` | Same console line as the packet; SHA-256 `508f5b258782c40330397d5ccf83363627a1b67dec4a1636036ba3c950b0253b`, 59,874 bytes — identical to `.local/eval/report.json` in this worktree and to the digest the packet and EVAL-2 record |
| Python cross-check over `.local/eval/report.json` (independent of the added tests) | Reproduces every figure and compile list in sections 1–5: split sizes 16/18 and 9/10; matched coverage 24/16/8; per-split accuracy and abstentions for all four conditions; matched-coverage selective accuracy 22/24 ×3 and 19/24; abstention, wrong-definite, missed-challenge and challenge-abstention lists per condition; empty unsupported revisions; A1 differing compiles 9 (bundle closer on `pb-cc-1/2/3`, `pb-ng-2`, `pb-tc-3`; baseline closer on `pb-cl-3`, `pb-er-1`, `pb-na-1`, `pb-na-3`); A2 differs on `pb-ng-2/t1` only, test split empty; A3 `identifiable: false`, no differing compile; `earlier_observation` fires on exactly `pb-er-1/2/3/4 /t1`; contestable block 14 = 10 + 4 with bundle 10/14 and baseline 13/14; the four atomic rows of the section-4 table; 8 threshold candidates all `(15, 1)`, `tuned: false`, chosen = intent initial values; sensitivity 21/28 with abstentions `pb-na-1`, `pb-na-3`, `pb-ng-2`; `composition_matches_frozen_expectation` 28/28; flip-rate distribution a single `0.0` bucket for all eight questions; test-split bundle answers 8 and is right on 8 |
| Counterfactual reading (section 4) checked against `compose` lines 430–444 | For `pb-er-1/t1` and `pb-er-2/t1` (`q3 = before`, `q4 = no`, `q6 = yes`): with the row restricted away, `conditional_support` needs `_yes(q4) >= tau_cond` (0 < 0.5, fails), `time_not_stated` needs `q3 = not_stated` (fails), so `fall_through` → `insufficient`; `missed_challenges` 2 → 0, `wrong_definite` empty, accuracy unchanged at 23/28. The packet's reading is right and is labelled a reading, not a run |
| `grep -n FixtureSystemOne src scripts tests` | `src/judgment/systemone.py:149 class FixtureSystemOne` exists at this base (CORE-2 merged); `scripts/eval/probe_bundle.py` references it only in its docstring ("not built on this branch"), which is stale here — see finding 2 |

### Checks the brief for this review asked for

- **Numbers reproduce from the report file.** Yes, by the cross-check above and by the three added
  tests, which rebuild the report in process and compare the two tables cell by cell. The
  per-compile *lists* in the second table of section 2 are not pinned by a test but reproduce.
- **A1 to A3 as the working paper defines them.** Section 2's preamble matches the section-6 table
  (A1 single-render Q8-only vs full bundle; A2 bundle with/without the Q7 gate; A3 with/without the
  stability downgrade) and the toggles are the EVAL-2 thresholds inside `[0, 1]`, frozen `compose`
  unchanged. One wording carry-over from EVAL-2 (finding 3).
- **Contestable row decided, not silently resolved.** Section 4 decides it (restrict to the
  supply-outlook kind, keep for that kind, do not delete), gives the per-compile evidence on the four
  compiles the row actually decides, the proposed replacement wording, the counterfactual, and
  explicitly sends the stronger alternative (a `challenges` row for an observed earlier return against
  a return-date assumption) to intent rather than deciding it on two compiles. It also states that the
  change is a frozen-contract edit (`BUNDLE_VERSION` bump, re-freeze of `expected_composition`) and so
  cannot be applied in EVAL-3. This is the escalation the process asks for, recorded in the packet.
- **"Section-4 decision to intent" is clear enough for the guardian.** Yes: the guardian is asked to
  open an intent revision that restricts the `earlier_observation` row to
  `assumed_available_capacity` (with the proposed text at lines 149–150) and to decide whether a
  `challenges` row for the return-date kind is added; both require a new bundle version and a fixture
  re-freeze.
- **Stand-in backend limitation disclosed.** Partly: section 5's first bullet discloses "a script, not
  a model" and section 1 names the backend as a scripted replay. What it does not say is that the
  intent's own fixture backend (`FixtureSystemOne`, slice S2) exists on this branch and was not the
  backend measured (finding 2).
- **No claim exceeds the synthetic fixture.** Every result sentence is scoped to the fixture set; the
  `synthetic_fixture` label, `kind: fixture`, `live_calls: 0` and the not-analyst-validation statement
  are present and pinned by `test_document_is_labelled_synthetic_and_carries_the_frozen_identity`; the
  Visayas case pack is named only to say nothing is claimed about it.
- **Links resolve.** `repo.py check` PASS.
- **Frozen contracts, fixtures, source.** Nothing under `src/`, `tests/fixtures/` or the intent
  changed; `tasks.json` change is the task's own state; no network, model, credential or dependency.

### Findings

| Severity | Location | What | Why / correction |
|---|---|---|---|
| important | `docs/work/probe-bundle/evaluation.md:73-76` and `:85-88` | The A1 mechanism prose says the baseline reads `pb-tc-3/t1` as `supports` ("`pb-cc-1/t1`, `pb-cc-2/t1`, `pb-cc-3/t1` and `pb-tc-3/t1`, where the baseline reads a conditional statement as `supports`"; "the four statements the baseline reads as an unconditional `supports`"). The report's `comparisons.A1.all.labels['pb-tc-3/t1'].single_render` is `challenges` (atomic `q8 = challenges`), the compile's edge class is `testing_vs_commercial`, and the document's own second table (line 58) lists it as a wrong definite consistent with `challenges`. | A misquoted report label in the one paragraph a reader uses for the A1 mechanism is the acceptance item "numbers match the report file" failing in narrative; the three added tests pin the tables, not this prose, so nothing caught it. No number changes. Correction (two sentences): say the baseline reads the three conditional-clause compiles as `supports` and `pb-tc-3/t1` (a testing-vs-commercial statement with a conditional clause, `q4 = yes`) as `challenges`, while the bundle composes `mixed` through `conditional_support` on `pb-cc-1/2` and `pb-tc-3` and through `time_not_stated` (Q3 `not_stated`, Q8 `supports`) on `pb-cc-3/t1`. Disposition: rework on the same branch; re-run the verify command and `tests.test_eval_probe_bundle` after the edit. |
| minor | `evaluation.md:174-178` (section 5, first bullet); `scripts/eval/probe_bundle.py:23-25`; `report.json` `backend.note` | The document leans on the report's own notes for the backend limit, and those notes say intent slice S2 (`FixtureSystemOne`) "is not built"; at this base (`e3531b3` includes CORE-2) `src/judgment/systemone.py:149` defines it. The measured backend is EVAL-2's scripted stand-in, not the intent's fixture backend. | Not false in the document itself (line 19 says "scripted replay"), but stale by inheritance and the gap EVAL-2's sixth note asked a follow-up to carry. Add one sentence to section 5: the intent's fixture backend exists at the base, the ablation measured EVAL-2's stand-in, which replays the same frozen per-form answers `FixtureSystemOne` would be fed (so the figures would not differ), and the swap is a follow-up EVAL task. Do not fix the script docstring or report note inside EVAL-3: it changes the report bytes and breaks the byte-identical claim in section 1. |
| minor | `evaluation.md:37` | `single_render` is described as "the one-shot Q8 answer"; the script reads the modal Q8 across the four perturbed forms (EVAL-2 interim finding 1, addressed to EVAL-3). | Identical on this backend (all forms agree), so no number changes; state it as a limitation in section 5 so A1 on a flipping backend is not misread as a true single render. |
| minor | `evaluation.md:21` | The tie-break is described as "smallest L1 distance from the initial values"; the report's tie-break has four keys (calibration accuracy, fewer incorrect abstentions, L1 distance, lexicographic). | The first two keys tie across all eight candidates, so the sentence is correct here; name the full order so the method is not misread as distance-first. Wording only. |
| minor | `evaluation.md:7` | "It runs nothing itself" — the task did regenerate the report and run the suite (sections 1 and 7 say so). | Means "no new measurement code"; say that. Wording only. |

No blocking findings. One important finding, with a two-sentence correction that changes no number.

### Acceptance items

| Item | Verdict | Evidence |
|---|---|---|
| Numbers match the report file | met for every figure and table; **not met for one prose label** (finding 1) | Cross-check and `EvaluationDocumentTests` reproduce every number, list and table cell at digest `508f5b25…0253b`; the A1 mechanism paragraph misquotes the baseline's label on `pb-tc-3/t1` |
| Labelled synthetic; no analyst-validation claim | met | `synthetic_fixture`, `kind: fixture`, `live_calls: 0`, "not analyst validation" present in section 1 and pinned by test; no model, analyst or real-case claim anywhere in the document |
| Outputs: per-condition table | met | Section 2, two tables, all four conditions, all six metric families |
| Outputs: decision on the contestable composition row | met | Section 4: decided (restrict to `assumed_available_capacity`), evidenced on the four deciding compiles, counterfactual read against `compose`, stronger alternative explicitly escalated to intent, implementation path named as a frozen-contract change |
| Outputs: limitations | met | Section 5, eight bullets; one disclosure gap (finding 2) |

Checklist: 1 yes; 2 yes (OK against `e3531b3`; the default base lists only the stacked parents'
review records); 3 yes (no frozen contract, acceptance text or test changed; three tests added); 4
yes; 5 yes; 6 yes for numbers, no for one label (finding 1); 7 yes (interpreter, commands, results,
unfinished items and next action recorded, post-commit re-run at `d319082`); 8 yes.

Guardian decision the packet asks for: open an intent revision that restricts the
`earlier_observation` row to supply-outlook assumptions (`assumed_available_capacity`) with a
`BUNDLE_VERSION` bump and a re-freeze of the fixtures' `expected_composition`, and decide whether a
`challenges` row is added for an observed earlier return against a return-date assumption.

**Verdict: rework.** Every number, list and table reproduces from the report and the contestable row is decided and escalated properly, but the A1 mechanism paragraph misquotes the baseline's label on `pb-tc-3/t1` (`challenges` in the report, `supports` in the prose), a two-sentence fix on the same branch after which this reviewer would accept; the designated independent review supersedes this interim one and alone sets `done`.

## Interim re-review of the rework (orchestrator seat, Fable, commit ee867a5, 2026-10-12)

Second interim review by the orchestrator seat (Claude Fable), which did not author the change,
re-reviewing the rework `952223c` (plus the record-only commits `ea711b1` and `ee867a5`) against the
first interim review above. The designated reviewer (GPT Astra through Codex) is still out of
credits; this section does **not** set the task `done`, and the designated independent review,
when it is written, supersedes both interim sections.

Read: the first interim review above and its five findings; `git show 952223c --stat` and the
full diff (`PROGRESS.md` +1 row, `evaluation.md` +93 −18, `tests/test_eval_probe_bundle.py` +30,
one test added); `ea711b1` and `ee867a5` (packet section 10 and the PROGRESS row only); the
current `docs/work/probe-bundle/evaluation.md` in full; `condition_labels`, `TIE_BREAK` and the
module docstring of `scripts/eval/probe_bundle.py`; `FixtureSystemOne` in
`src/judgment/systemone.py` (read, not edited). `docs/work/probe-bundle/live-run.md` is on
`task/CORE-5`, not this branch, and was not read.

### Commands run (worktree `.local/wt/EVAL-3`, `/usr/bin/python3`, no network, no model call)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/repo.py check` (the brief's verify command) | `Checked 263 Markdown files, 1249 local links, 8 skills; bootstrap 1293 words.` `PASS` (before this section was appended) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 -m unittest tests.test_eval_probe_bundle -v` | `Ran 14 tests in 0.617s` — `OK`; `test_a1_mechanism_prose_quotes_the_report` listed and `ok` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 296 tests in 5.579s` — `OK` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-3 e3531b3` | `OK: all changed files inside EVAL-3 allowed paths`, exit 0 |
| `/usr/bin/python3 scripts/plan.py scope EVAL-3 feat/h1-api-persistence` | Lists `docs/work/reviews/CORE-2.md` and `docs/work/reviews/EVAL-2.md`, exit 1 — the stacked parents' review records, the same artefact the packet and the first review record; unchanged by the rework |
| `/usr/bin/python3 scripts/eval/probe_bundle.py --fixtures tests/fixtures/probe-bundle --out <scratch>/report.json` | Same console line as the packet; SHA-256 `508f5b258782c40330397d5ccf83363627a1b67dec4a1636036ba3c950b0253b`, 59,874 bytes — identical to `.local/eval/report.json` in this worktree (file dated 12:12, before the rework). The packet's own `sha256sum` row only shows that file was not touched; this regeneration from script and fixtures is the check that the rework changed no report byte |
| Cross-check over the regenerated report (independent of the added test) | `single_render.label`: `pb-cc-1/t1` `supports`, `pb-cc-2/t1` `supports`, `pb-cc-3/t1` `supports`, `pb-tc-3/t1` `challenges`; `bundle.label` `mixed` on all four; `bundle.fired_rule` `conditional_support: …` on `pb-cc-1/t1`, `pb-cc-2/t1`, `pb-tc-3/t1` and `time_not_stated: Q3=not_stated and Q8=supports` on `pb-cc-3/t1`; atomic `pb-cc-3/t1` `q3 = not_stated`, `q8 = supports`; `comparisons.A1.all.labels['pb-tc-3/t1']` = `{bundle: mixed, single_render: challenges}`; `comparisons.A2.all.differing_compiles` = `['pb-ng-2/t1']`, bundle `insufficient` via `sufficiency_gate`; `thresholds.tie_break` = the four keys in the order the packet now names, `tuned: false`; `backend.note` still says S2 "is not built" (left as is, as the first review directed) |
| Negative control 1: copy of the packet with `` `pb-tc-3/t1` as `challenges` `` changed back to `supports`, `EvaluationDocumentTests.DOCUMENT` pointed at the copy, the new test run alone | `FAILED (failures=1)`; the diff shows `('pb-tc-3/t1', 'challenges') != ('pb-tc-3/t1', 'supports')` — the exact defect of the first review's finding 1 |
| Negative control 2: copy with `` through `time_not_stated` on `pb-cc-3/t1` `` changed to `conditional_support` | `failures: 1, errors: 0` — the firing-row clause is pinned too |
| `scripts/eval/probe_bundle.py` lines 306–319 | `single_render` is `atomic['q8']` from `compose(...)['atomic']`, the per-form modal aggregate, so the "modal Q8" wording in sections 2 and 5 describes the script correctly |
| `git diff e3531b3...HEAD -- tests \| grep -c '^-[^-]'` | `0` — no test line removed or changed on the branch; 4 tests added in total |
| `git diff e52acfe...HEAD --stat -- docs/work/reviews/EVAL-3.md` | empty — the executor did not edit this record |
| `git show 952223c` hunks | header (lines 7–11), section 1 tie-break row, section 2 definition, section 3 both A1 paragraphs, section 5 first bullet plus one new bullet, new section 10. Section 4 (the contestable row, lines 116–176) is untouched |

### Disposition of the first review's items

| First-review item | Severity | Disposition | Evidence |
|---|---|---|---|
| A1 prose read the baseline on `pb-tc-3/t1` as `supports` where the report says `challenges` (`evaluation.md:73-76`, `:85-88`) | important | **closed** | Lines 88–93 now read `pb-cc-1/t1`, `pb-cc-2/t1`, `pb-cc-3/t1` as `supports` and `pb-tc-3/t1` as `challenges`, bundle `mixed` on all four through `conditional_support` on `pb-cc-1/2` and `pb-tc-3` and `time_not_stated` on `pb-cc-3/t1` (Q3 `not_stated`, Q8 `supports`); every clause matches the regenerated report. The summary sentence at lines 77–79 now says "the baseline's single reading differs", which is vague rather than wrong. Pinned by `test_a1_mechanism_prose_quotes_the_report` (two negative controls above). No number changed |
| Stale "S2 not built" note leaned on for the backend disclosure | minor | **closed** | Section 5 first bullet now says `FixtureSystemOne` exists at this base, the measured backend is EVAL-2's stand-in, and the swap is a follow-up. The statement that the figures "would not differ" is a conditional about construction (`FixtureSystemOne.decide` returns the `answers` dict it was built with, `src/judgment/systemone.py:149-176`), hedged with "would", not a demonstrated run; honest. Script docstring and `backend.note` left as they were, so the report bytes are unchanged |
| "one-shot Q8" vs modal Q8 | minor | **closed** | Section 2 definition names the modal reading; new section 5 bullet states the limitation and why no figure changes here; matches `condition_labels` |
| Tie-break described as L1-distance only | minor | **closed** | Section 1 names all four keys in the report's order and says the third key decides because the first two tie; matches `TIE_BREAK` and `thresholds.tie_break` |
| "It runs nothing itself" | minor | **closed** | Header now reads "adds no new measurement code — it regenerates the report and runs the suite (section 7)" |

### Findings on the rework

| Severity | Location | What | Why / correction |
|---|---|---|---|
| minor | `evaluation.md:302` (section 10 disposition) and the `PROGRESS.md` rework row: "rebuilds every claim of that paragraph from the report" | The test pins the four baseline labels (exact list), the firing-row *names* for the four compiles, and the A2 "turns `pb-ng-2/t1` into an abstention" sentence. It does not pin the bundle label `mixed` on the four compiles or the Q3/Q8 parenthetical on `pb-cc-3/t1`; both reproduce by the cross-check above. | A slight overstatement in a self-description, not in a result; "machine-checked" is true for the labels and rows that the first finding was about. Wording only; no rework needed. Not corrected here because this record is the only file this review edits. |

No blocking and no important findings.

### Acceptance items

| Item | Verdict | Evidence |
|---|---|---|
| Numbers match the report file | met | Every figure, list and table cell reproduced at `508f5b25…0253b` in the first review; the one prose label that failed is corrected and now pinned by a fourth document test with a working negative control |
| Labelled synthetic; no analyst-validation claim | met | Unchanged by the rework; `test_document_is_labelled_synthetic_and_carries_the_frozen_identity` still passes |
| Outputs: per-condition table | met | Unchanged; `test_condition_table_matches_the_report` passes |
| Outputs: decision on the contestable composition row | met | Section 4 untouched by the rework (no hunk in `952223c`): decision at lines 145–151 (restrict the `earlier_observation` row to `assumed_available_capacity`, keep for that kind, do not delete), proposed wording at 155–156, counterfactual labelled a reading at 158–165, the stronger `challenges` row for return-date assumptions sent to intent at 166–169, implementation path as a frozen-contract change at 171–176 |
| Outputs: limitations | met | Section 5 now nine bullets; the disclosure gap of the first review's finding 2 is closed |

Checklist: 1 yes; 2 yes (`scope EVAL-3 e3531b3` OK; the default base lists only the stacked
parents' review records, unchanged); 3 yes (no frozen contract, acceptance text or test changed;
zero removed test lines on the branch; one test added); 4 yes (prose plus one in-process test, no
dependency, service, credential, network or model call); 5 yes; 6 yes (the misquoted label is
gone and every clause of the mechanism paragraph reproduces from the report); 7 yes (section 10
records interpreter, commands, results, the negative control, the post-commit re-run at `952223c`
and a labelled self-review; `ee867a5` leaves the review record untouched); 8 yes.

Guardian decision the packet asks for, still stated clearly and unchanged by the rework: open an
intent revision that restricts the `earlier_observation` row (`Q3 = before and Q6 = yes ->
supports`) to supply-outlook assumptions (`assumed_available_capacity`) with a `BUNDLE_VERSION`
bump and a re-freeze of the fixtures' `expected_composition`, and decide whether a `challenges`
row is added for an observed earlier return against a return-date assumption.

Context only, not acceptance evidence for EVAL-3: the orchestrator reports that CORE-5's
authorized live run (recorded in `docs/work/probe-bundle/live-run.md` on `task/CORE-5`, not read
here) observed the same `earlier_observation` row composing `supports` on a supply-outlook
assumption while the model's Q8 said `challenges`. That is one live render on one compile, in
the same direction as the fixture finding in section 4; it gives the intent question live
evidence to weigh but does not settle the row by itself.

The designated independent review supersedes this section and alone sets the task `done`.

**Verdict: accept.** The important finding is closed with prose that matches the regenerated report clause by clause and a test that fails on the old label, the four minors are dispositioned honestly without changing a report byte, and the contestable-row decision stands unchanged for the guardian; one minor wording note on the "every claim" self-description needs no rework.

## Designated review 1 (GPT Sol, independent, commit `aded542`, 2026-10-13)

> Independent review of `task/EVAL-2...b819885`, including `git log task/EVAL-2..HEAD`. No files edited.
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 scripts/repo.py check`: **PASS**, 263 Markdown files, 1,250 local links.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-3 task/EVAL-2`: **FAIL**, exit 1; 19 disallowed paths.
> - `/usr/bin/python3 scripts/plan.py check`: **PASS**, 42 tasks, 7 gates.
> - `/usr/bin/python3 -m unittest discover -s tests`: **PASS**, 296 tests.
> - In-process report regeneration: equals stored `.local/eval/report.json`; 59,874 bytes, SHA-256 `508f5b258782c40330397d5ccf83363627a1b67dec4a1636036ba3c950b0253b`.
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1 | **No** | Measured tables match the regenerated report, and synthetic labelling passes; the section 4 counterfactual and proposed decision conflict, as finding 2 explains. |
> | 2 | **No** | Requested scope check fails on 19 paths, including hosting documents, seat scripts and `src/workspace/`. The log identifies inherited changes; checking against `e3531b3` does not demonstrate scope compliance against the requested base. |
> | 3 | **Yes** | Frozen composition code, working-paper definitions and existing JudgmentArtifact contract are unchanged; record changes are additive. No acceptance item was relaxed or test skipped/weakened. |
> | 4 | **No** | The complete requested range includes CORE-6’s live Vertex attempt records in `docs/work/m3-live-gemini/implementation.md`, beyond this fixture-report packet. EVAL-3’s own additions introduce no external call. |
> | 5 | **Yes** | `evaluation.md:24–29` explicitly labels synthetic scripted results and disclaims analyst/model validation; regenerated report records `synthetic_fixture` and zero live calls. |
> | 6 | **No** | Recorded measurements reproduce, but the proposed restriction cannot preserve both supply-outlook successes or leave accuracy unchanged as claimed. |
> | 7 | **Yes** | `evaluation.md:230–346` records interpreter, commands, results, limitations, unfinished work and the next review/intent action. |
> | 8 | **Yes** | The report preserves proposal authority, distinguishes synthetic evidence, and routes composition changes through a new intent (`evaluation.md:171–176`). |
> 
> Findings:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | `docs/work/probe-bundle/evaluation.md:246` | The union base hides changes outside EVAL-3’s allowed scope relative to the requested review base. | Scope exits 1 with 19 disallowed files; `git log` includes unrelated UI, hosting, seat and live-run commits. | Have the orchestrator isolate the task changes onto an appropriate dependency baseline, document the reviewed range, and obtain a passing scope check. |
> | important | `docs/work/probe-bundle/evaluation.md:155` | Proposed predicate excludes a supply-outlook success that the decision claims to retain, invalidating the counterfactual accuracy. | Proposed row requires Q2=`commercial_availability`; `pb-er-4/t1` has Q2=`synchronisation`, Q3=`before`, Q4=`no`, Q6=`yes`. It would fall through to `insufficient`, losing a correct answer: 22/28 rather than the claimed unchanged 23/28. | Align proposed wording with the assumption-kind-only decision, or revise the rationale and counterfactual to include this lost success. Keep runtime changes deferred to intent. |
> 
> **Verdict: rework.** The measured report reproduces, but the requested branch scope fails and the contestable-row proposal contradicts its stated fixture consequences.
**Verdict: rework.** The branch was rebuilt by the orchestrator from feat/h1-api-persistence (now carrying the accepted EVAL-2 rework) with only the seven eval-3 commits; scope is OK. (1) Regenerate .local/eval/report.json with the merged EVAL-2 script and bring every figure in evaluation.md to it; test_condition_table_matches_the_report currently fails because selective accuracy now counts answered cases only. (2) Owner ruling Round 9 (docs/work/foundation-review-2026-10-13/strategy.md): the earlier-observation question is settled by bundle v5 (milestone_mismatch on any availability field; row 10 gated on direction); withdraw EVAL-3's own row proposal and point to v5 instead, which also disposes of the 22-vs-23-of-28 finding. Re-measure at the new tip. Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `c411d31`, 2026-10-14)

> Independent review of `c411d314b3bf` against `feat/h1-api-persistence`, including the requested diff and commit log. Working tree clean; no files edited.
> 
> | # | Checklist item | Answer | Evidence |
> |---|---|---|---|
> | 1 | Acceptance demonstrated | **Yes** | Executed document tests compare condition and contestable-row tables with the rebuilt report. Stored report is byte-identical to the current producer: 60,028 bytes, SHA-256 `d9e78502…fee8`. Synthetic labelling and disclaimer checks pass. |
> | 2 | Changes within allowed paths | **Yes** | Requested scope command prints `OK: all changed files inside EVAL-3 allowed paths`; the diff contains five allowed files. |
> | 3 | Contracts, acceptance and tests preserved | **Yes** | Diff adds documentation, coordination records and 130 test lines; no runtime contract, fixture or acceptance text changes, and no tests removed or weakened. |
> | 4 | No unapproved dependencies or external effects | **Yes** | Changes introduce no dependency or service integration; evaluation uses deterministic offline fixture replay. |
> | 5 | Truthful mode labels | **Yes** | `evaluation.md:26–31` explicitly labels synthetic results and disclaims analyst validation and measured model accuracy; report records zero live calls. |
> | 6 | Unknowns preserved; no invented results | **Yes** | Report reproduces exactly. `evaluation.md:119–126` leaves A3 unidentified; sections 4–5 distinguish measured v4 results from the deferred v5 rerun. |
> | 7 | Complete execution packet | **Yes** | `evaluation.md:377–453` records interpreter, commands, results, finding dispositions, remaining limits and exact next action. Historical counts are labelled by revision. |
> | 8 | Consistent with product and domain authority | **Yes** | Contestable-row evidence covers both assumption kinds; `evaluation.md:155–183` withdraws the proposal and follows the owner’s Round 9 ruling and bundle v5 intent without changing frozen runtime contracts. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 282 Markdown files, 1,358 local links.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-3 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 45 tasks, 7 gates.
> - `/usr/bin/python3 -m unittest discover -s tests` — **OK**, 420 tests.
> - In-process report comparison — **byte-identical** to `.local/eval/report.json`.
> 
> Findings: none; no unresolved blocking, important or minor findings.
> 
> **Verdict: accept.** Both acceptance items are demonstrated, scope passes, and the previous material findings are resolved without changing frozen contracts.
**Verdict: accept.** v4 figures; refreshed to v5 after CORE-8 merges.
