# REL-4 review record

Task: release manifest and submission checklist; the entry's openings aligned to the theory-first
framing. Branch `task/REL-4` against `feat/entry-framing`. Reviewer: Claude Opus 5.5, an in-session
subagent of the orchestrator, read-only, independent of the author (the DeepSeek executor seat and,
for round 2, the orchestrator); the owner's fallback on 2026-10-17 while the Codex workspace that runs
the usual GPT reviewer is out of credits. The runner's own review rounds returned `none` for that
reason and its summary says NOT merged on RED verifies that were the shared price-export pins
(regenerated on main b5d2a36), not this task's.

## Designated review 1 (Opus 5.5, 2026-10-17, branch rebased onto feat/entry-framing a95db82)

Checks reproduced by the reviewer in the worktree: manifest JSON loads; `repo.py check` PASS (484
files, 3,298 links); `tests.test_release_audit` 32 tests OK; `plan.py scope REL-4 feat/entry-framing`
OK; 12 nulls in the manifest, each matching a `pending_receipts` key; 0 missing artifact paths in the
acceptance matrix; twelve `## Slide` headings. The full suite was left to the orchestrator (it ran
`Ran 1932 tests` OK (skipped=47) in the same worktree).

| Severity | Path | Finding | Correction |
|---|---|---|---|
| blocking | deck.md:3, :45, :65 | the cover front matter was never aligned: tagline, positioning line and cover notes ("Open on the analyst and the decision") still open on the old desk framing; acceptance item 3 names the cover | rewrite the cover to open on the belief-maintenance claim and quote it in the record |
| important | deck.md:79-80, :101-102, Appendix B row 53 | `[FOUND]` does not resolve for the records claim; the foundation page states the four questions, the case page states the claim | drop FOUND from that sentence and the row; keep FOW |
| important | Appendix B row 53 | graded E; the case page (section 8), the strategy record and the foundation page call every productivity sentence a hypothesis until experiment 3 | mark the sentence as the entry's claim and grade to match |
| important | story-and-script.md:57-60 | the narration opening grew from 43 to 60 words for the 0 to 15 second slot; the pitch from 104 to 122 | cut to about 40 words or record the timing hand-back to REL-6 |
| minor | story-and-script.md:57 | "with AI doing" versus the case page's "about to" | align the tense |
| minor | story-and-script.md:95 vs deck.md:75 | narrative line 1 and the slide 1 heading agree in substance only | align the wording |
| minor | release-manifest.json:7-8, :117; implementation.md | commit ids from before the runner's rebase (7605484, 6d6ad19, 733b283, cff2290) | restate against the current base and branch |
| minor (note) | release-manifest.json | five of the twelve nulls are outputs of later tasks, each named in `pending_receipts` | none; recorded |

Acceptance checklist as the reviewer read it: items 1, 2, 5 and 6 demonstrated; item 3 not (the
cover); item 4 partly (the marker and the grade). Scope inside owned paths; no invented number,
credential, private node or refused address; mode labels truthful.

**Verdict: rework** (acceptance item 3; the marker and the grade in the same pass).

## Rework round 2 (orchestrator, 2026-10-17)

All eight points answered in the task record's "Rework round 2" section: the cover opens on the
theory; FOUND dropped from the records claim; the claim graded F and worded as the hypothesis it is;
narration cut to 46 words, pitch shortened, "proven" corrected to "tested", "about to"; narrative
line 1 matches the slide heading; manifest ids restated against the rebased base and the green suite.
Review 2 follows.

## Designated review 2 (Opus 5.5, 2026-10-17, commit cc63e4a)

All eight findings closed: the cover opens on the theory in tagline, positioning line and notes and the
record quotes all three; FOUND gone from the records claim, FOW resolves to the case page; row 53 graded
F and worded as a hypothesis until experiment 3; narration opening 47 words (43 at the base), the REL-6
timing hand-back judged sufficient; tense aligned; narrative line 1 matches the slide heading word for
word; manifest ids restated. Two minor notes, both corrected in the accept commit: the manifest's
`test_report` history fields still described the red state (now labelled history and the verify
result restated on cc63e4a); one "own wording" phrase in the record (now "in line with"). The
reviewer re-ran the manifest load, `repo.py check` PASS (485 files, 3,299 links), `tests.test_release_audit`
32 OK, `plan.py scope` OK, twelve slide headings; the full suite is the orchestrator's run.

**Verdict: accept.**
