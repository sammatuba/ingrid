# DOC-5 review record

Task: the explainer opens on the ideas, a tier of four theory chapters before the systems map.
Branch `task/DOC-5` against `feat/entry-framing` (merge-base a95db82). Reviewer: Claude Opus 5.5, an
in-session subagent of the orchestrator, read-only, independent of the author (the DeepSeek executor
seat; the orchestrator for rework round 2); the owner's fallback on 2026-10-17 while the Codex
workspace that runs the usual GPT reviewer is out of credits. The runner's own review rounds returned
`none` for that reason and merged the branch into `feat/entry-framing` on a green verify; that merge is
runner-green, not a reviewer accept, and the rework goes on top of it.

## Designated review 1 (Opus 5.5, 2026-10-17, commit 8eedb42)

Checks reproduced by the reviewer in the worktree: `repo.py check` PASS; `build_explainer.py --check`
exit 0; `tests.test_explainer tests.test_cache_headers tests.test_grid_page` 143 tests OK (skipped=12,
server-library checks); the full suite `Ran 1932` OK (skipped=47); `plan.py scope DOC-5 a95db82` OK;
`plan.py check` OK; the DOC-4 packet byte-identical to the base; banned-word, status-word, number and
inline-code greps clean; the served page links no Markdown, the single-file copy does; every test
change accounted for (none weakened).

| Severity | Path | Finding | Correction |
|---|---|---|---|
| important | 00-ideas-1-know.md:29, 00-ideas-4-learn.md:26 | the "desk's word" sentences contradict the brief and the new glossary (belief: assumption; outcome: the settled month) | say "the desk calls a belief an assumption"; "the desk calls the outcome the settled month" |
| important | build_explainer.py:679 (miss-cause note) | says the cause of a miss "has a field of its own"; the foundation page says attribution is a designed field with no intent record | say the field is designed only and no month has been scored |
| important | build_explainer.py:666, :1722 (loop widget) | states the unbuilt learning edge as working ("the settled month scores the judgment and the belief") | say the settled month scores the forecast, first real pair November to December 2026, nothing reads the score yet |
| important | 00-ideas-4-learn.md:43-49 (the bridge) | drops section 6's per-step status and adds belief scoring | call it a proposed walk no case has run whole; give each step its status; drop "and the belief" |
| important | 00-ideas-4-learn.md:18-20 vs the widget | the chapter and its widget define the two loops in opposite ways | first loop corrects the action or belief; second changes the method or the goal |
| minor | 00-ideas-4-learn.md:30 | "no real month has settled" is wrong; none has been scored | reword |
| minor | 00-ideas-4-learn.md:14-15 | "quiet Monday … Tuesday is heavy" | Monday |
| minor | 00-ideas-4-learn.md:56 | a late signal can show a belief wrong; it cannot fault the decision at the cutoff | reword to the decision |
| minor | decision-line widget | "the desk leaves the position alone" implies position management | "the change does not count as material" |
| minor | 00-ideas-1, 00-ideas-2 | "claim" never explained; "the scorecard" and the value-of-timely-information half missing | add in plain words |
| minor | CHAPTER_ADD for Ideas 4 | its adds were already added by Ideas 2 | give it a component of its own |
| minor (brief) | tasks.json DOC-5 outputs | "four tiers" where the ruling and acceptance say three | orchestrator fixes the brief text |

Reading as a newcomer: Ideas 1 to 3 understandable without the grid; Ideas 4 not as written (the loops,
the day error, the overclaims). Acceptance items 1, 2, 4 and 5 demonstrated; 3 partial (the status
words in widget prose and the bridge); 6 is the owner's reading, open.

**Verdict: rework** (the desk's words, and the learning loop stated more strongly than section 7).

## Rework round 2 (orchestrator, 2026-10-17)

All twelve points answered in owned files, recorded in the task record's "Rework round 2" section;
the plain-language check forced four further rewordings (passive voice, sentence length, a semicolon,
a seven-sentence paragraph). Review 2 follows.

## Designated review 2 (Opus 5.5, 2026-10-17, commit 0652350)

All twelve findings fixed in the text as it stands; the builder check, `repo.py check` PASS (489 files),
the verify command (143 tests OK, skipped=12) and `plan.py scope` all pass; a newcomer can now follow
Ideas 4 without the grid (consistent example, the two loops defined once, the thin spot and the bridge
say what has not run). The loop widget's note understates slightly (section 7 says one input, the
scoring receipt, is built); understating is allowed. Two minor notes, wording only: (A) one wrong quiz
option in Ideas 4 half-agreed with the explanation (corrected in the accept commit: "The decision,
because the signal proves it wrong"); (B) the Ideas 4 strip adds "Local boosted trees", which a reader
could take for machine learning in a chapter about organisational learning (kept: it is the model the
scorecard scores out of sample, and the strip must add a component no earlier chapter added).

**Verdict: accept.** Acceptance item 6, the owner reading Ideas 1 to 4 cold, stays open and is the
owner's; the state stays `in_progress` until it is recorded, as DOC-4's did.

## Owner reading (2026-10-17)

The owner read Ideas 1 to 4 cold and answered "Accepted, it starts from the ideas" (in session, through
the question tool): acceptance item 6 is met. State `done`. The owner also called the batch deploy
that carries the chapters to the site.
