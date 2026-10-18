# EVAL-2: Offline ablation script A1 to A3

Executor packet, written by the executor seat (DeepSeek). It is labelled as executor work and is
not a review; a reviewer's section, if any, follows below. Task:
[EVAL-2](../tasks.json) (`Offline ablation script A1-A3`, lane EVAL, milestone M4,
`route: implement`). Branch `task/EVAL-2`, stacked on `task/EVAL-1` per the 2026-10-12
[PROGRESS](../PROGRESS.md) log; base for the scope check is therefore `task/EVAL-1`.
Interpreter `/usr/bin/python3` (`Python 3.14.4`). No model, transport, credential, service or
network call exists in or is reached by this work.

## What was built

| Path | What it is |
|---|---|
| `scripts/eval/probe_bundle.py` | The offline ablation: replays the frozen fixture set, renders the bundle, answers it with the fixture backend, scores the four conditions and writes the JSON report |
| `tests/test_eval_probe_bundle.py` | Ten tests: determinism, CLI/file equality, fixture-digest integrity with a tamper control, the split rule, the calibration-before-test order, the frozen-composition cross-check, one-mechanism-per-toggle, the Q8 baseline path, the pinned counts, and the contestable-row comparison for both assumption kinds |
| `.local/eval/report.json` | The generated report (ignored path, not committed), 59,874 bytes on the frozen set |

Conditions, exactly the four the brief names: `single_render` (the model's own one-shot Q8 answer
mapped to a relation label — the A1 baseline), `bundle` (composition with the Q7 sufficiency gate
and the stability downgrade), `bundle_no_gate` (A2, `tau_suff` 0.0 so the gate row cannot fire),
`bundle_no_receipt` (A3, `tau_flip` and `tau_pol` 1.0 so no flip rate or polarity gap can exceed
them). The toggles are named thresholds inside `[0, 1]`, so the frozen `compose` is called
unchanged and nothing in `src/judgment/bundle.py` was edited.

## What the report measures, and what it does not

**The fixture backend is a script, not a model.** Intent slice S2 (the System One port and
`FixtureSystemOne`) is not built on this branch — `src/judgment/systemone.py` does not exist and is
outside EVAL-2's paths — so the only backend available offline is a deterministic script whose
answers are the frozen annotated atomic answers of each pair (one answer per form, at the frozen
probability EVAL-1 recorded its composition with). The report is labelled `synthetic_fixture` for
that reason, and every headline number below is a statement about **the composition table and the
ablation wiring on annotated synthetic evidence**: not analyst validation, not model accuracy and
not evidence about any backend. This is also why the `bundle` condition reproduces the fixtures'
`expected_composition` column on all 28 compiles — a cross-check between the two packets, not an
independent result.

**Truth and abstention.** The frozen per-compile label is the annotated truth; a condition abstains
when it labels a compile `insufficient`. `neither` (the Q8 answer "leave unchanged") is not one of
the five frozen labels and the baseline is not given an abstain primitive (working paper section 6:
decision models "have no abstain primitive"), so it is scored as `unrelated` — evidence that does
not bear on the proposition. That is an executor reading, so the report carries a sensitivity block
with the alternative (`neither` as an abstention) and every definition in
`report['metric_definitions']`.

## Split and thresholds

- Split rule, fixed in the script and never reading a label: pair-id suffix 1 or 2 is calibration,
  3 or 4 is test. Compiles are split by pair, so both compiles of a later-than-cutoff pair stay on
  one side. Result: **16 calibration pairs / 18 compiles, 9 test pairs / 10 compiles**, every edge
  class present on both sides.
- Thresholds are fixed on the calibration split only: a declared candidate grid (8 candidates over
  `tau_suff`, `tau_flip`, `tau_pol`; `tau_cond` and `tau_lineage` have one defensible value each)
  is scored on the calibration compiles, one candidate is chosen under the declared tie-break, and
  the test compiles are not read before that choice is made.
- On this scripted backend the candidates tie: noul tops are hard yes/no, so `tau_suff`/`tau_cond`/
  `tau_lineage` cannot separate them, and every flip rate is 0, so `tau_flip`/`tau_pol` cannot
  either. All eight score 15/18 with 1 incorrect abstention on calibration; the tie-break resolves
  to the smaller L1 distance from the intent's initial values, i.e. the working paper's initial
  thresholds, and `tuned` is `false`. The report records that as an outcome instead of claiming a
  tuned result.

## Results on the frozen set (fixture digest `2455c0a6…0eec89`)

| Condition | correct / 28 (all) | calibration | test | abstentions (correct) | selective acc. (own answers) | sel. acc. at matched coverage |
|---|---|---|---|---|---|---|
| `single_render` | 22 (0.785714) | 14/18 | 8/10 | 0 | 22/28 | 19/24 (0.791667) |
| `bundle` | 23 (0.821429) | 15/18 | 8/10 | 4 (1) | 23/24 (0.958333) | 22/24 (0.916667) |
| `bundle_no_gate` | 22 (0.785714) | 14/18 | 8/10 | 3 (0) | 22/25 (0.88) | 22/24 (0.916667) |
| `bundle_no_receipt` | 23 (0.821429) | 15/18 | 8/10 | 4 (1) | 23/24 | 22/24 |

- Matched coverage (the compiles every condition answers, so all four are read at one coverage):
  24 of 28 overall, 16 of 18 calibration, 8 of 10 test.
- `bundle` abstains on `pb-cl-3/t1`, `pb-na-1/t1`, `pb-na-3/t1` (frozen labels `challenges`,
  `unrelated`, `unrelated` — the three deliberate conservative abstentions the fixture set
  documents) and on `pb-ng-2/t1` (frozen `insufficient` — the one correct abstention).
- Missed challenges (frozen `challenges`, definite non-challenge answer): `bundle`
  `[pb-er-1/t1, pb-er-2/t1]`, `single_render` `[pb-er-2/t1]`. Challenge that abstained instead:
  `pb-cl-3/t1` (`bundle`). Unsupported revisions (`challenges`/`mixed` where the frozen label is
  `supports`, `unrelated` or `insufficient`): **none under any condition** on this set.
- Identity mismatches (`q1` not the mapped entity, `cannot_tell` included): `pb-na-1/t1`,
  `pb-na-3/t1` — the single-candidate mapping cannot express the sister unit, exactly as the
  fixture packet says.
- A2: the gate's only effect on this set is turning one definite wrong answer into a correct
  abstention — `pb-ng-2/t1`, `insufficient` with the gate versus `unrelated` without it. It is a
  calibration-split compile, so A2 shows no difference on the test split at all. Accuracy is 1
  better with the gate; unsupported revisions and missed challenges are unchanged.
- A3: every compile is stable (flip rate 0 on all eight questions and all 28 compiles; the
  flip-rate distribution is the single zero bucket), the downgrade never fires,
  `bundle_no_receipt` equals `bundle` and `identifiable` is `false`. Measured instability cannot
  predict errors when no instability is measured; the frozen label disagreements are
  stable-and-wrong rows of the composition table, not receipt cases. A3 stays undecided until a
  backend that actually flips exists.
- A1 contestable rule (`Q3 = before and Q6 = yes -> supports`): 14 compiles carry the pattern (10
  `commercial_availability_from`, 4 `assumed_available_capacity`). `bundle` agrees with the frozen
  label on 10 of 14, `single_render` on 13 of 14. The decisive earlier-observed-return pairs:
  `pb-er-1/t1` and `pb-er-2/t1` (return-date kind) are frozen `challenges`, the table composes
  `supports` and gets both wrong; `single_render` gets `pb-er-1/t1` right (`challenges`) and
  `pb-er-2/t1` wrong (`supports`). `pb-er-3/t1` and `pb-er-4/t1` (supply-outlook kind) are frozen
  `supports` and both conditions agree. The decision on the row is EVAL-3's; this packet supplies
  the numbers and the reading.
- Sensitivity of the `neither` reading: with `neither` scored as an abstention instead, the
  baseline is 21/28 with 3 abstentions (`pb-na-1/t1`, `pb-na-3/t1`, `pb-ng-2/t1`) instead of 22/28
  with none.

## Commands and results

Run from the worktree root, `/usr/bin/python3` (`Python 3.14.4`); nothing touches the network, a
model or a credential.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_eval_probe_bundle -v` | `Ran 10 tests in 1.165s` — `OK` |
| `/usr/bin/python3 scripts/eval/probe_bundle.py --fixtures tests/fixtures/probe-bundle --out .local/eval/report.json` | `synthetic_fixture: 16 calibration pairs, 9 test pairs, 28 compiles; bundle 23/28 correct (4 abstentions), single_render 22/28 correct (0 abstentions) -> .local/eval/report.json` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 271 tests in 4.584s` — `OK` (261 before this task) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 253 Markdown files, 1103 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 feat/h1-api-persistence` | Lists `docs/work/reviews/EVAL-1.md` — see the scope note below |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 task/EVAL-1` | `OK: all changed files inside EVAL-2 allowed paths` |

Negative controls exercised while building: a tampered copy of the fixture directory (one frozen
label flipped) is refused by the digest check — `FixtureProblem: pb-tc-1.json: digest differs from
the manifest; fixture digest differs from the manifest` — and the CLI exits `1` with that message
on stderr; an unknown pair-id suffix raises `FixtureProblem`; a compile whose replayed task, digest,
cutoffs or context differs from the file's `expected_*` fields stops the run instead of being
scored.

**Scope note.** The brief's closing rule asks for `plan.py scope <ID>` to print OK. With the default
base it cannot here: EVAL-2's branch is stacked on `task/EVAL-1` (both the orchestration log and the
worktree say so), so `git diff feat/h1-api-persistence...HEAD` includes EVAL-1's own review record,
which is inside EVAL-1's allowed paths and not inside EVAL-2's. Nothing of EVAL-2's touches it; the
same command with the parent branch as base prints OK, and `git status --short` inside the task
shows only `docs/work/PROGRESS.md`, `docs/work/tasks.json`, `scripts/eval/` and
`tests/test_eval_probe_bundle.py`. The same stacking artefact was recorded for CORE-1 and EVAL-1.

Also in this commit, as an allowed coordination edit requested by the EVAL-1 interim review
("Move the three EVAL-1 rows above the 2026-10-12 row at the next coordination commit"): the three
2026-10-11 EVAL-1 log rows in `docs/work/PROGRESS.md` now sit before the 2026-10-12 row, so the log
is in date order again. No task state, table row or test depends on line order.

Post-commit re-run at `a199e63` (working tree clean, `/usr/bin/python3`, `Python 3.14.4`):
`-m unittest tests.test_eval_probe_bundle` `Ran 10 tests … OK`; the CLI printed the same summary
line and wrote a byte-identical report (59,874 bytes, SHA-256
`508f5b258782c40330397d5ccf83363627a1b67dec4a1636036ba3c950b0253b`, the same digest before and
after the re-run, which is the determinism claim in one number); full suite `Ran 271 tests … OK`;
`plan.py check` `OK: 41 tasks, 7 gates`; `repo.py check` `PASS` (254 Markdown files, 1,107 local
links); `plan.py scope EVAL-2 task/EVAL-1` prints `OK`, and the default-base scope prints only
`docs/work/reviews/EVAL-1.md` as described above. No command touches the network.

## Acceptance

| Acceptance item | Evidence |
|---|---|
| `scripts/eval/probe_bundle.py` with conditions `single_render`, `bundle`, `bundle_no_gate`, `bundle_no_receipt` | The script defines exactly those four (`CONDITIONS`), each with its definition in the report; the one-mechanism-per-toggle test pins the toggles (gate off changes only `pb-ng-2/t1`; receipt off changes nothing on a stable backend) |
| JSON report under `.local/eval/` with accuracy, abstention rate, selective accuracy at matched coverage, missed challenges, unsupported revisions, flip-rate distribution | `.local/eval/report.json` carries all six per condition per split (`metrics.{all,calibration,test}.conditions.<condition>`, `matched_coverage`, `selective_accuracy_at_matched_coverage`, `flip_rate_distribution`), each defined in `metric_definitions` |
| Deterministic report for the fixture backend | The determinism test builds twice and compares canonical JSON; the report records no clock, interpreter or environment value; the CLI writes byte-identical content to the in-process report |
| Report labelled `synthetic_fixture` | `report['report_label']` and `report['backend']['execution_mode']`, pinned by the determinism test; the backend block records `live_calls: 0` and the notes carry the not-analyst-validation statement |
| Thresholds fixed on a calibration split before the test split | `thresholds.fixed_on == 'calibration'`; every candidate's score block holds only calibration counts and only calibration compiles (18); the ranking is recomputed in the test from the recorded candidates; the chosen candidate is the intent's initial values with `tuned: false` |

## Self-review (executor, labelled as such; not an independent review)

- Scope: only `scripts/eval/`, `tests/test_eval_probe_bundle.py`, `docs/work/PROGRESS.md`,
  `docs/work/tasks.json` and this record were written. `src/judgment/bundle.py`,
  `tests/test_probe_bundle.py` and `tests/fixtures/probe-bundle/` (all inside the allowed paths)
  were read and left untouched: no frozen contract, no fixture label, no digest and no test text
  changed. No dependency, service or credential was added; the script imports stdlib and the
  existing repository/judgment modules only.
- The reading most worth a reviewer's eye is the one the report is built on: the fixture backend
  replays the frozen annotated answers, so `bundle` cannot disagree with `expected_composition`,
  and the ablation's value on this set is the composition table's standing against the annotation
  plus the A2 toggle. If the reviewer holds that an ablation must not read the answers it scores,
  the answer is S2: CORE-2 builds the port and `FixtureSystemOne`, and the condition code here
  needs only its answers argument replaced — but that backend does not exist on this branch and
  EVAL-2's paths do not reach it.
- Second: the `neither -> unrelated` mapping is an executor reading of the frozen text, mirrored in
  the sensitivity block rather than hidden. Third: the split rule is a construction, not a
  standard; it is declared in the script and in the report so any reader can re-derive the numbers.
- Anything I could not check: the report's numbers are only as good as the frozen annotations,
  which are project-authored synthetic labels and not analyst validation.

## Limits, unfinished items and exact next action

- The report is a measurement of the composition table and of the ablation wiring on annotated
  synthetic evidence. It is not model accuracy and does not transfer to a live backend.
- A3 is not identified on this backend, and A2 is identified by one compile that sits in the
  calibration split, so its effect does not appear in the test-split numbers.
- The thresholds are untuned (the grid ties); no claim of a calibrated method is made anywhere.
- Unfinished: nothing in this task's outputs. Next action: EVAL-3 (`Ablation report on fixtures`)
  reads `.local/eval/report.json`, writes `docs/work/probe-bundle/evaluation.md` with the
  per-condition table and the decision on the contestable row; the numbers there must match this
  report file. Then the designated independent review of EVAL-2 sets `done`.

## Interim review (orchestrator seat, Fable, commit 6db38fa, 2026-10-12)

Interim review by the orchestrator seat (Claude Fable), which did not author the change. The
designated reviewer (GPT Astra through Codex) is out of credits; this section is the review-first
list for the owner and the designated reviewer. It does **not** set the task `done`. The
designated independent review, when it is written, supersedes this one.

Read in order: the brief (`plan.py show EVAL-2`, `plan.py brief EVAL-2` for the rails), the intent
(`docs/work/probe-bundle/intent.md`, slice S5) and the working paper sections 5.2, 5.3 and 6, the
diff `feat/h1-api-persistence...HEAD` (5 files, no untracked files), the packet above. The frozen
baseline-protocol document the brief for this review referred to does not exist on this branch
(`docs/work/probe-bundle/` holds `fixtures.md`, `implementation.md`, `intent.md`, `work.json`), so the
ablation definitions were checked against the working paper table in section 6 and intent S5.

### Commands run (worktree `.local/wt/EVAL-2`, `/usr/bin/python3`, no network, no model call)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_eval_probe_bundle -v` | `Ran 10 tests in 0.531s` — `OK` |
| `/usr/bin/python3 scripts/eval/probe_bundle.py --fixtures tests/fixtures/probe-bundle --out .local/eval/report.json` | `synthetic_fixture: 16 calibration pairs, 9 test pairs, 28 compiles; bundle 23/28 correct (4 abstentions), single_render 22/28 correct (0 abstentions)`; 59,874 bytes, SHA-256 `508f5b258782c40330397d5ccf83363627a1b67dec4a1636036ba3c950b0253b` |
| Same command a second time to a scratch path | SHA-256 identical (`508f5b25…0253b`): the determinism claim re-measured at `6db38fa`, same digest the packet reports |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 271 tests in 2.556s` — `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 254 Markdown files, 1108 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 feat/h1-api-persistence` | `OK: all changed files inside EVAL-2 allowed paths` (EVAL-1 has since merged, so the default base is clean too) |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 task/EVAL-1` | `OK` |
| `grep -i 'urllib\|requests\|http\|socket\|vertex\|genai\|anthropic\|os.environ\|getenv'` over the two new files | no match: stdlib plus `src.*` imports only, no network, environment or model reach |
| Report cross-check (python over `.local/eval/report.json` and `manifest.json`) | every figure in the packet's results table and bullets reproduces: per-split accuracy/abstentions, matched coverage 24/16/8, selective accuracy at matched coverage 22/24 vs 19/24, missed challenges, no unsupported revisions, identity mismatches `pb-na-1/t1` `pb-na-3/t1`, A2 differing compile `pb-ng-2/t1` only, A3 `identifiable: false`, all 8 candidates `(15, 1)`, `tuned: false`, sensitivity 21/28 with 3 abstentions, contestable block 14 compiles (10 + 4) with 10/14 vs 13/14; all eight edge classes present on both splits; the five `agrees_with_frozen_label: false` compiles equal `manifest.frozen_label_disagreements` |

### Checks against the intent and the frozen table

- **A1–A3 are what section 6 defines.** `single_render` is the Q8-only baseline mapped to a label
  with no gate and no receipt; `bundle` is the frozen `compose` at the chosen thresholds; A2 switches
  only the sufficiency gate (`tau_suff` 0.0; `_yes` is a hard 0.0/1.0 so `0.0 < 0.0` never fires);
  A3 switches only the stability downgrade (`tau_flip`/`tau_pol` 1.0 against strict `>`
  comparisons on values bounded by 1.0). Both toggles pass `_thresholds` validation (`[0, 1]`) and
  leave `src/judgment/bundle.py` untouched. The one-mechanism-per-toggle test pins the observable
  effect.
- **Scripted-answer polarity is right.** `scripted_answers` inverts the probability for the negated
  noul form exactly as `_values` un-negates it, so every form's top is the frozen answer and the
  flip rate is 0 by construction. This is why A3 is unidentified, and the report says so instead of
  implying the receipt was tested.
- **Contestable row (`Q3 = before and Q6 = yes -> supports`).** Not silently decided. The report's
  `comparisons.A1.contestable_rule` lists all 14 compiles carrying the pattern by assumption kind,
  shows every condition's label beside the frozen label, and the test pins the decisive four:
  `pb-er-1/t1`, `pb-er-2/t1` (return-date kind) frozen `challenges`, table `supports` (wrong);
  `pb-er-3/t1`, `pb-er-4/t1` (supply-outlook kind) frozen `supports`, table `supports`. The
  packet hands the keep/drop decision to EVAL-3 and states that `bundle` cannot disagree with
  `expected_composition` on this backend. That is the honest framing.
- **Calibration before test.** `candidate_scores` receives only the calibration list and
  `choose_thresholds` runs before any test compile is read (`build_report` lines 517–523); the test
  recomputes the ranking from the recorded candidate scores. The grid ties by construction (hard
  0/1 nouls, zero flip rates), so "fixed on calibration" is procedurally true but uninformative
  here; the report records `tuned: false` rather than claiming a calibrated result.
- **No live call.** `backend.live_calls: 0`; nothing imports a transport; the fixture backend is a
  replay of recorded annotations, and every number traces to a record (no invented figures).
- **Scope.** `docs/work/PROGRESS.md` and `docs/work/tasks.json` are outside `owned_paths` but are
  declared `coordination_files` in `tasks.json`, which is why `plan.py scope` accepts them; the
  tasks.json change is the task's own state only. No frozen contract, fixture label, digest or
  existing test changed.

### Findings

| Severity | Location | What | Why / correction |
|---|---|---|---|
| minor | `scripts/eval/probe_bundle.py:311-318` | `single_render` reads the **modal** Q8 across the four perturbed forms (via `compose` with the receipt off), not a single render. | Identical on this backend (all forms agree), so no number changes. On a backend that flips, the "single-render" baseline would inherit the perturbation set's majority vote and A1 would understate the bundle's benefit. When S2 lands, read the canonical form's Q8 (`q8_direction_f0`, un-aliased) for this condition; note for CORE-2/EVAL-3, not a rework here. |
| minor | packet, "Post-commit re-run at `a199e63`" | `a199e63` is reachable from no ref (the branch was rebased to `5945790`/`30607d5`/`6db38fa`). | The claim stands on a real commit now: this review re-measured the same digest `508f5b25…0253b` at `6db38fa`. Say so at the next packet edit. |
| minor | packet, "Scope note" and the PROGRESS.md log row | States that the default-base scope lists `reviews/EVAL-1.md`. | Superseded, not wrong: EVAL-1 is merged into `feat/h1-api-persistence`, and both bases print OK today. |
| minor | `scripts/eval/probe_bundle.py:36-38`, packet "Truth and abstention" | Attributes "have no abstain primitive" to working paper section 6. | The sentence is in section 1 (line 59, citing D30). Citation only. |
| minor | `scripts/eval/probe_bundle.py:129-135` | `CALIBRATION_GRID` cannot separate any candidate on this backend (`tau_suff`/`tau_cond`/`tau_lineage` compare against hard 0/1; all flip rates are 0). | Already disclosed in the docstring, the report note and the packet. Recorded here so EVAL-3 does not read "fixed on calibration" as evidence of calibration; no change requested. |
| minor | intent S5 vs `tasks.json` | Intent lists S2 (`FixtureSystemOne`) as an S5 dependency; `tasks.json` EVAL-2 depends only on CORE-1 and EVAL-1, so the executor built a scripted stand-in. | No stop condition covers an unbuilt dependency, the stand-in reads only recorded fixture values, and it is labelled on every surface; disclosed, outside EVAL-2's paths to fix. Plan-level note for the orchestrator: the swap to the S2 backend belongs to CORE-2 or a follow-up EVAL task. |

No blocking or important findings.

### Acceptance items

| Item | Verdict | Evidence |
|---|---|---|
| Deterministic report for the fixture backend | met | Two CLI runs at `6db38fa` give the same SHA-256; `test_report_is_deterministic_labelled_and_offline` compares two in-process builds; no clock, interpreter, environment value or absolute path in the report |
| Report labelled `synthetic_fixture` | met | `report_label` and `backend.execution_mode` both `synthetic_fixture`, `backend.kind: fixture`, `live_calls: 0`, notes carry the not-analyst-validation statement; pinned by test |
| Thresholds fixed on a calibration split before the test split | met | Split rule fixed by pair-id suffix without reading labels; `candidate_scores(calibration)` and `choose_thresholds` run before any test compile is scored; each candidate score holds only the 18 calibration compiles; chosen = intent initial values, `tuned: false` |
| Outputs: four named conditions; JSON report under `.local/eval/` with accuracy, abstention rate, selective accuracy at matched coverage, missed challenges, unsupported revisions, flip-rate distribution | met | `CONDITIONS` is exactly the four; all six metrics present per condition per split with `metric_definitions` |

Checklist: 1 yes; 2 yes (both bases OK); 3 yes; 4 yes; 5 yes; 6 yes; 7 yes (interpreter, commands,
results, limits and next action recorded); 8 yes.

**Verdict: accept.** All acceptance items are met by checks this reviewer ran, every packet number reproduces at `6db38fa`, and the six findings are minor; the designated independent review supersedes this interim one and alone sets `done`.

## Designated review 1 (GPT Sol, independent, commit `7a69540`, 2026-10-13)

> Independent review of `7a69540`, against `feat/h1-api-persistence`. Reviewed the five-file diff and all four branch commits. No files edited.
> 
> Verification on Python 3.14.4:
> 
> - Task verify: attempted; 8 tests passed, 2 errored on read-only filesystem writes. The chained report-writing command **was not run**.
> - Full offline suite: 271 tests, 39 errors involving unavailable writable files/directories; not passing.
> - Scope: **OK: all changed files inside EVAL-2 allowed paths**.
> - `plan.py check`: **OK**. `repo.py check`: **PASS**.
> - Read-only report builds: two canonical reports were identical and labelled `synthetic_fixture`.
> 
> | Checklist | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | **No** | In-memory determinism, label and calibration ordering demonstrated; CLI file-output verification blocked by sandbox. |
> | 2. Changes stay within allowed paths | **Yes** | Required scope command printed OK. |
> | 3. Frozen contracts/acceptance unchanged; tests not weakened | **Yes** | Diff adds evaluation code/tests and coordination records; frozen files and existing tests unchanged. |
> | 4. No unauthorized dependency or external effect | **Yes** | Uses stdlib and existing repository functions; no transport, service or model invocation. |
> | 5. Truthful mode labels | **Yes** | Report explicitly identifies scripted synthetic annotations, zero live calls and unidentifiable A3. |
> | 6. Unknowns remain unknown; no invented facts/receipts | **Yes** | Inputs come from frozen fixture records; `model_version` remains null and scripted probability is disclosed. |
> | 7. Packet contains required handoff evidence | **Yes** | Packet records interpreter, commands, results, limitations and next action; historical scope claims are superseded by the interim review. |
> | 8. Consistent with product/method/domain invariants | **No** | A1’s `single_render` condition uses modal Q8 across four forms, contradicting its stated single-render baseline. |
> 
> Findings, all unresolved:
> 
> - **important | scripts/eval/probe_bundle.py:363 | Selective accuracy includes correct abstentions in its numerator but excludes them from its denominator | Executed report gives bundle 23/24 = 0.958333; counting only answered cases gives 22/24 = 0.916667 | Count correct predictions only among answered cases; correct the pinned test and packet numbers.**
> - **important | scripts/eval/probe_bundle.py:311 | `single_render` inherits four-form majority voting, confounding A1 | Executed in-memory control changed canonical Q8 to `supports` while the other forms remained `challenges`; baseline still returned `challenges` | Read canonical `q8_direction_f0` directly and add a disagreement test. Existing stable fixtures mask this defect.**
> 
> **Verdict: rework.** Two important evaluation defects remain, and file-output verification must be demonstrated in a writable sandbox before acceptance.
**Verdict: rework.** Fix selective accuracy (answered cases only) and make A1 read canonical q8_direction_f0 directly, with a disagreement test; re-pin numbers. Children EVAL-3, REL-2 and UI-4 re-run after. Address every blocking/important row above; dispose of minors explicitly.

## Rework (executor seat, DeepSeek, labelled executor work, 2026-10-13)

Rework of designated review 1, on `task/EVAL-2`. Two files changed:
`scripts/eval/probe_bundle.py` and `tests/test_eval_probe_bundle.py`. The sections above are the
reviewed record and were not edited; where a number or a citation below replaces one of theirs,
this section says so and supersedes it. No other review record was touched, and no frozen
contract, fixture label, digest or existing test outside EVAL-2's two files was changed.

### Disposition of every finding

| Finding | Where filed | Disposition |
|---|---|---|
| **important** — selective accuracy put correct abstentions in the numerator while excluding them from the denominator (bundle 23/24 = 0.958333; answered-only is 22/24) | designated review 1, `scripts/eval/probe_bundle.py:363` | **Fixed.** `measure` now computes `answered_correct = [key for key in answered if labels[key] == frozen[key]]` and uses it for `selective_accuracy.correct` and `.rate`; `METRIC_DEFINITIONS['selective_accuracy']` states the rule. Re-measured: bundle 22/24 = 0.916667 (was 23/24), `bundle_no_receipt` the same; `bundle_no_gate` 22/25 = 0.88 and `single_render` 22/28 are unchanged. The test re-pins all three. |
| **important** — `single_render` inherited the four-form modal vote, confounding A1 | designated review 1, `scripts/eval/probe_bundle.py:311` | **Fixed.** New `single_render_answer()` reads the canonical `q8_direction_f0` question and un-aliases its token through that form's criteria; `single_render` and the `neither` sensitivity block read it, while `bundle`, both toggled conditions and `atomic` keep calling `compose`, whose modal-over-forms convention is the frozen table's. New test `test_single_render_reads_only_the_canonical_form` writes the canonical form's answer as `supports` while the other three stay `challenges` and pins baseline `supports` against atomic modal `challenges`. On the frozen set every form agrees, so no label and no accuracy number moves. |
| review note — "file-output verification must be demonstrated in a writable sandbox before acceptance" | designated review 1, verification block | **Demonstrated here.** The brief's verify command ran in this writable worktree: the CLI wrote `.local/eval/report.json` (60,028 bytes) and `test_cli_writes_the_same_report_bytes` passed. The reviewer's 8-pass / 2-error result is its read-only sandbox, not the code. |
| minor — baseline read the modal Q8, not one render | interim review | Fixed with the important finding above. |
| minor — `a199e63` is reachable from no ref | interim review, packet "Post-commit re-run" | **Superseded.** This rework re-measures the determinism claim at the current commit: two CLI runs write one identical SHA-256, recorded below. |
| minor — scope note said the default base lists `reviews/EVAL-1.md` | interim review, packet "Scope note" and PROGRESS row | **Superseded.** EVAL-1 is merged; `plan.py scope EVAL-2 feat/h1-api-persistence` and the parent base both print `OK` today, recorded below. |
| minor — the "have no abstain primitive" citation said working paper section 6 | interim review, `scripts/eval/probe_bundle.py:36-38` | **Fixed in the script**: the docstring now cites section 1 (D30), where the sentence is (line 59). The same wrong citation in this packet's "Truth and abstention" paragraph above is superseded by this note. |
| minor — `CALIBRATION_GRID` cannot separate any candidate on this backend | interim review | No change requested and none made; the disclosure already sits in the module docstring, the report's `thresholds.note` and this packet. |
| minor — intent S5 lists S2 (`FixtureSystemOne`) as a dependency that `tasks.json` does not | interim review | Outside EVAL-2's paths and unchanged; the plan-level note stands (the S2 swap belongs to CORE-2 or a follow-up EVAL task). |

### Corrected results table (supersedes the table under "Results on the frozen set" above)

Only the two `selective acc. (own answers)` cells for `bundle` and `bundle_no_receipt` change;
every other figure, including `selective_accuracy_at_matched_coverage`, is unchanged, and the
report keeps both readings apart so a reader can see they now coincide for the bundle (its own
answered set on this fixture set is exactly the matched set).

| Condition | correct / 28 (all) | calibration | test | abstentions (correct) | selective acc. (own answers) | sel. acc. at matched coverage |
|---|---|---|---|---|---|---|
| `single_render` | 22 (0.785714) | 14/18 | 8/10 | 0 | 22/28 (0.785714) | 19/24 (0.791667) |
| `bundle` | 23 (0.821429) | 15/18 | 8/10 | 4 (1) | **22/24 (0.916667)** | 22/24 (0.916667) |
| `bundle_no_gate` | 22 (0.785714) | 14/18 | 8/10 | 3 (0) | 22/25 (0.88) | 22/24 (0.916667) |
| `bundle_no_receipt` | 23 (0.821429) | 15/18 | 8/10 | 4 (1) | **22/24 (0.916667)** | 22/24 (0.916667) |

Everything else in the earlier reading of the set stands: the missed challenges, the empty
unsupported-revision lists, the A2 difference on `pb-ng-2/t1` (calibration side only), A3
unidentified, the contestable-row comparison, and the `neither` sensitivity block (now 20/25 =
0.8 selective, 21/28 accuracy, 3 abstentions, read from the same report).

The regenerated report is 60,028 bytes, SHA-256
`d9e785024ee1569a2b07b43f209e3c9350d07c35e98b628d6a1e83177d87fee8` (the earlier 59,874-byte
`508f5b25…0253b` report is superseded). The byte change is the two corrected cells in every
split plus the `selective_accuracy` definition string and the `single_render` condition
definition; no label, threshold or count moved.

### Commands and results

Run from the worktree root, `/usr/bin/python3` (`Python 3.14.4`); nothing touches the network, a
model or a credential.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_eval_probe_bundle -v` | `Ran 11 tests in 0.570s` — `OK` (10 before; the disagreement test is new) |
| `/usr/bin/python3 scripts/eval/probe_bundle.py --fixtures tests/fixtures/probe-bundle --out .local/eval/report.json` | `synthetic_fixture: 16 calibration pairs, 9 test pairs, 28 compiles; bundle 23/28 correct (4 abstentions), single_render 22/28 correct (0 abstentions) -> .local/eval/report.json` |
| the same command a second time to a scratch path | SHA-256 identical (`d9e78502…7fee8`): the determinism claim re-measured after the rework |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 272 tests in 2.705s` — `OK` (271 before) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 254 Markdown files, 1110 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 feat/h1-api-persistence` | `OK: all changed files inside EVAL-2 allowed paths` |
| `/usr/bin/python3 scripts/plan.py scope EVAL-2 task/EVAL-1` | `OK: all changed files inside EVAL-2 allowed paths` |
| `grep -icE 'urllib\|requests\|http\|socket\|vertex\|genai\|anthropic\|os.environ\|getenv' scripts/eval/probe_bundle.py tests/test_eval_probe_bundle.py` | `0` on each file: stdlib plus `src.*` imports only, no network, environment or model reach |

Negative controls executed (read-only, under the ignored `.local/eval/`):

- `.local/eval/rework-control.py`, over the frozen `pb-er-1/t1` render with the canonical Q8
  answer overwritten to `supports` and the three perturbed forms left at `challenges`: the
  pre-rework reading (`compose(...)['atomic']['q8']`, the modal vote) returns `challenges` while
  the new `single_render_answer()` returns `supports` — the reviewer's control reproduces, and
  the new test fails against the old code.
- The same run reads the regenerated report: bundle `accuracy.correct` 23 with 4 abstentions of
  which 1 is correct, so the answered-only numerator is 23 − 1 = 22 over 24 answered → 0.916667;
  the old numerator (every label match) would have been 23 → 0.958333.

### Acceptance, self-review, stop conditions, next action

| Acceptance item | Status | Evidence |
|---|---|---|
| Deterministic report for the fixture backend | met | Two CLI runs give one SHA-256; the determinism test is green |
| Report labelled `synthetic_fixture` | met | `report_label` and `backend.execution_mode` unchanged, pinned by test |
| Thresholds fixed on a calibration split before the test split | met | Unchanged: `fixed_on: calibration`, `tuned: false`, test recomputes the ranking from the recorded candidate scores |
| Outputs: four named conditions; JSON report under `.local/eval/` with the six metrics | met | The selective-accuracy cell is corrected and re-pinned; the other five metrics are untouched |

Self-review (executor, labelled as such; not an independent review): the diff is two files and
their tests; `src/judgment/bundle.py`, the fixtures and `tests/test_probe_bundle.py` were read
and left untouched; no test was weakened, skipped or deleted — one test was added and three pins
tightened; no dependency, service, credential or network call was added. The claims above were
read from the executed report and the executed control, not inferred. The residual limit is
unchanged: the fixture backend is a script, so on this set every form agrees and the A1 fix is
demonstrated by the disagreement control rather than by any frozen-set number moving.

Stop conditions: none hit. No change outside the allowed paths was needed, no acceptance text or
frozen contract was touched, and nothing was invented.

Unfinished items and exact next action: nothing in this task's outputs. `docs/work/tasks.json`
and the PROGRESS.md row keep state `in_progress` (no state edit was needed — both already said
`in_progress`). Next: the designated reviewer re-runs `7a69540`'s checks against the new commit
and, on accept, sets `done`; EVAL-3, REL-2 and UI-4 re-run after, reading the regenerated
`.local/eval/report.json` (digest `d9e78502…7fee8`), whose numbers supersede the ones in this
packet's earlier sections.

## Orchestrator re-measure after rebase onto the integration branch (2026-10-13)

Rebased onto `feat/h1-api-persistence` (which now carries the accepted CORE-2 and CORE-4); earlier commit citations in this packet name pre-rebase commits. At `53ba218`: full offline suite `Ran 331 tests in 5.202s` OK; task tests `Ran 11 tests in 0.445s` OK; `plan.py scope EVAL-2 feat/h1-api-persistence` OK: all changed files inside EVAL-2 allowed paths; `plan.py check` OK; `repo.py check` PASS. Run by the orchestrator seat; ready for the designated re-review.

## Designated review (GPT Sol, independent, commit `8d10620`, 2026-10-13)

> Independent review of `8d10620fc375` against `feat/h1-api-persistence`; inspected the five-file diff and seven branch commits. No source or documentation files edited.
> 
> Executed on Python 3.14.4:
> 
> - Exact task verify command: **PASS**, 11 tests; report written.
> - Required scope command: **OK**, all changed files allowed.
> - Full offline suite: **PASS**, 331 tests.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Repeated CLI output: identical 60,028 bytes, SHA-256 `d9e785024ee1569a2b07b43f209e3c9350d07c35e98b628d6a1e83177d87fee8`.
> 
> | Checklist item | Answer | Evidence |
> |---|---|---|
> | 1. Every acceptance item demonstrated | yes | Executed determinism and mode-label tests; calibration-only candidate ranking selects thresholds before test scoring (`probe_bundle.py:550–554`). All four conditions and required metrics appear in the written report. |
> | 2. Changes within allowed paths | yes | Required `scope EVAL-2 feat/h1-api-persistence` printed OK. |
> | 3. Frozen contracts and acceptance unchanged; no tests weakened | yes | Diff adds evaluator/tests and coordination records; frozen files and existing tests unchanged. |
> | 4. No unauthorized dependency or external effect | yes | Evaluator uses stdlib and existing repository functions; no network, model or cloud invocation. |
> | 5. Truthful mode labels | yes | Report uses `synthetic_fixture`, records zero live calls, and explicitly identifies annotation-driven scoring and unidentifiable A3. |
> | 6. Unknowns preserved; no invented facts or receipts | yes | Inputs replay frozen records; scripted probability is disclosed; model version remains null. |
> | 7. Packet contains verification and handoff | yes | Packet records interpreter, commands, results, prior-finding dispositions, limitations and next action; latest remeasurement records 331 passing tests. |
> | 8. Consistent with product, method and domain invariants | yes | Canonical Q8 baseline, gate/receipt ablations, cutoff preservation and separate synthetic reporting follow the evaluation design. Earlier selective-accuracy and baseline defects are fixed and exercised by passing tests. |
> 
> Findings:
> 
> - **minor | scripts/eval/probe_bundle.py:576 | Generated report inaccurately says System One slice S2 is unbuilt after the rebase | `src/judgment/systemone.py:149` contains `FixtureSystemOne`, and line 196 contains `SystemOneService` | Describe the evaluator’s local scripted backend and state that it does not use the implemented System One service.** Unresolved; documentation-only impact.
> 
> **Verdict: accept.** All acceptance items were demonstrated, prior important findings are fixed, and the remaining finding is minor.
**Verdict: accept.** One minor finding recorded for the follow-up.
