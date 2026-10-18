# Evaluation: not run

**No baseline and no assisted session were run on this case.** The matched manual baseline
protocol exists ([baseline-protocol.md](../../work/probe-bundle/baseline-protocol.md), task
EVAL-6), but the analyst session that would execute it on a real episode (EVAL-7) is **cut** in
the task graph ([tasks.json](../../work/tasks.json)) by the 2026-10-14 strategy refresh, and no
analyst time was committed. This file records that absence rather than a result.

## What is measured

Nothing on this case: no correctness score, no effort, no review time, no comparison of
assisted and unassisted work. The only outputs here are the case records and the deterministic
scripted readings recorded in [review.md](review.md) and
[tests/fixtures/pedc-u2-2026-09-21/case.json](../../../tests/fixtures/pedc-u2-2026-09-21/case.json),
which are a fixture backend's — **not** a model's, **not** an analyst's, and not a measurement
of either.

## Live probe run on this case (recorded elsewhere)

One live recording exists for this case, made by the orchestrator seat, not by this task:
`docs/work/grid-desk/live-run-2026-10-14.md` on the integration branch
`feat/h1-api-persistence` (it is not part of this branch, so it is named here rather than
linked). The orchestrator ran the two `t1` compiles of this same case through live Gemini
(Vertex AI, two calls, owner-authorized, guard lift recorded). **Both live compiles composed
`challenges`**; the fixture's scripted reading composes `challenges` at trip/T1 and **`supports`
at return/T1**. The two readings of the return cutoff disagree, and the difference is a
question for the owner (whether bundle v6 should ask the event question of the latest passage
only), **not a change made here**: this fixture's scripted labels stay exactly as run, and
neither reading is a measurement of model or analyst performance on this case. What the live
run does establish, for the workflow, is that the event page can carry a model reading
(`challenges`) against which the analyst decides — which is the desk's design, not a score.

## What would have to exist to conclude anything

1. An analyst session that freezes its question and works the case without assistance
   (the protocol's baseline arm), with its effort recorded.
2. A second session with the desk's assistance enabled, under the same protocol.
3. Enough episodes for the comparison not to rest on one case; the protocol's thresholds would
   have to be frozen before additional cases are evaluated.

## Boundaries

Fixture results elsewhere in the repository (the ablation report,
[evaluation.md](../../work/probe-bundle/evaluation.md)) are separate measurements on synthetic
pairs and must not be read as statements about this case, this unit or any backend. The live
probe run above is one recording of two compiles, not an evaluation of this case.
