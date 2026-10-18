# Review: REL-1 public export audit script and provenance log

Change range `feat/h1-api-persistence..task/REL-1` on `task/REL-1`: the audit tool, allowlist,
install template and tests (at `108ee9c`), then the provenance log, `PROGRESS.md`/`tasks.json`
state and this record, then a fail-closed guard for shallow clones in the tool and its tests;
reviewed 2026-10-11.
**Self-review**: the executor seat (DeepSeek V4.1 Flash, this session) both authored and
reviewed the change, so this section is labelled self-review and offers no verdict. An
independent reviewer must replace it with the checklist record before REL-1 can be `done`.

Scope inspected: the full diff against `feat/h1-api-persistence`, the brief, the
[submission checklist](../../competition/ai-builder-cup-2026/submission-checklist.md) and
[requirements](../../competition/ai-builder-cup-2026/requirements.md), `.gitignore`.

## What was built

`scripts/release/export.py` (Python 3.11+ stdlib only) decides every path tracked at a Git
revision against `scripts/release/allowlist.json`: include rules carry a note, exclude rules
and scan findings carry a reason. Included candidates are checked for first commits before
the 2026-09-07 build-window cutoff, for secret patterns, private-data markers and internal
locations, and for allowlisted paths whose worktree differs from the audited revision. A
finding blocks the export, and so does a shallow clone, where first-commit dates cannot be
established at all. `--dry-run` prints every decision; `--dest` writes a clean export
with a generated README (from `scripts/release/clean-install.md`), `PROVENANCE.md` and
`EXPORT-AUDIT.json`; `--write-provenance` writes the repository copy of the provenance log.
Matched values never appear in any output, only rule, path and line.

## Verification and fidelity

Interpreter `/usr/bin/python3` (Python 3.14.4), worktree clean at `108ee9c` unless stated.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_release_audit -v` | `Ran 13 tests in 1.125s ... OK`, exit 0 (13 at `108ee9c`; the shallow-clone test below is the 14th) |
| `/usr/bin/python3 scripts/release/export.py --dry-run` | exit 0; `tracked 571, included 60, excluded 511, findings 0`; 619-line report; every tracked path appears once, each excluded path under a rule with its reason |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 264 tests ... OK` at `108ee9c` (251 before this task) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS`, 239 Markdown files, 993 local links |
| `/usr/bin/python3 scripts/release/export.py --dest .local/export/grid-nowcast-public --as-of 2026-10-11` | exit 0, `wrote export of 60 paths`; export file set equals the audited include set plus the three generated files, no excluded prefix present |
| `cd .local/export/grid-nowcast-public && /usr/bin/python3 -m unittest discover -s tests -v` | `Ran 242 tests in 1.926s ... OK` — the clean-install instruction in the exported README, executed on the export |
| `/usr/bin/python3 scripts/release/export.py --write-provenance docs/competition/ai-builder-cup-2026/provenance-log.md --as-of 2026-10-11` | exit 0, log written for the 60 included paths; dates read from `git log`, e.g. `src/review/records.py` first commit 2026-10-05 `818de084c67f`, last 2026-10-06 `f3c796287090` |

Re-run at the branch head, worktree clean: the verify command again gave `Ran 14 tests ... OK`
and `--dry-run` exit 0 with `tracked 573, included 60, excluded 513, findings 0` (the two
added paths are the provenance log and this record, both excluded); `discover -s tests` gave
`Ran 265 tests ... OK`; `plan.py check` `OK: 41 tasks, 7 gates`; `repo.py check` `PASS`;
`plan.py scope REL-1 feat/h1-api-persistence` printed `OK: all changed files inside REL-1
allowed paths`. `git diff --name-only 108ee9c -- src scripts/repo.py requirements` is empty
and the only changed path under `tests/` is this task's own excluded test file, so the 60
included paths the [provenance log](../../competition/ai-builder-cup-2026/provenance-log.md)
dates are byte-identical at the audited revision and at the head: the log stays valid.

Acceptance, each with the check that was actually run:

1. **Dry run reports every excluded path with a reason** — the 619-line report groups 511
   exclusions under 30 rules, each header carrying the reviewed reason; an unmatched path is
   excluded as `unmatched` with its own reason. Asserted by
   `DryRunReport.test_every_excluded_path_is_reported_once_with_a_nonempty_reason`.
2. **A planted secret and a planted old file are caught by tests** —
   `PlantedFindings.test_planted_secret_is_excluded_and_its_value_never_printed` plants an
   AWS-example key and a PEM header in throwaway repositories: both files are excluded as
   findings, the run exits 1, and the planted values are asserted absent from the output.
   `test_planted_old_file_is_excluded_with_its_commit_date` plants a commit dated 2026-08-20:
   excluded as `history-pre-cutoff` with that date in the detail.
3. **Clean install instructions verified on the export** — the exported README's command was
   run inside the written export (`Ran 242 tests ... OK`, row above), and
   `ExportWrites.test_clean_install_instructions_run_on_the_export` runs the same documented
   command inside a fixture export.

Self-review readings and limits:

- The allowlist was reviewed rule by rule against the 571 tracked paths. `src/dashboard`
  (private GCS bucket), the workspace preview, internal planning, research dossiers, archive,
  experiments and the seat launchers are excluded with reasons; `docs/` is excluded wholesale
  because REL-2 and REL-5 own the public document set. The public surface is deliberately
  narrower than the final submission and is a REL-5 decision, not this task's.
- One reviewed content exception exists: `src/demo/__init__.py` carries one hit of
  `credential-assignment` in the labelled fictional seed. The exception records the count; a
  second hit in that file stops the export (tested).
- `tests/test_release_audit.py` and the release tooling are themselves excluded from the
  export, so a modified worktree in those paths does not block it; the report notes such
  paths by count instead. Nothing that can enter the export can be uncommitted without a
  finding.
- A shallow clone (the default CI checkout) yields one blocker naming `git fetch --unshallow`
  instead of 500-odd misleading `history-unrecorded` findings.
  `test_shallow_history_blocks_the_export` writes `.git/shallow` and asserts the block, and
  the live-repository test asserts that same refusal when the clone is shallow rather than
  skipping itself.
- Not run, and not claimed: `requirements/h1.lock` was not installed (no network use is
  authorised in REL-1), and rights/IP clearance, the deck, video and publication remain
  REL-5/REL-6 items behind GATE-5.

## Findings

None raised by this self-review. Open items for the independent reviewer and for REL-5:

- Independent review of the allowlist contents is the substantive check this task cannot
  perform on itself.
- REL-5 must decide whether `scripts/release/**` (currently excluded) ships in the public
  export, and must extend the allowlist with the reviewed document set.

## Outcome and next action

Both deliverables exist at `108ee9c`: the audit tool with its 13 tests, and the
[provenance log](../../competition/ai-builder-cup-2026/provenance-log.md) for that revision.
Task state is `in_progress` in `docs/work/tasks.json` and `PROGRESS.md`, set in the same
commit as this record. Next action: independent review on `task/REL-1` (reviewer GPT Astra via
`codex exec -s read-only`), after which the reviewer replaces this section with the checklist
record and its verdict; only an `accept` verdict sets REL-1 `done`. No stop condition fired
and no work is left unfinished inside the brief's allowed paths. This record implies no
publication, deployment or merge.

## Review round 2026-10-11 evening (commit `2965411`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `29654110c36d3866a15087eced68370d64df8c1e` against `feat/h1-api-persistence`. Reviewed all three commits: `108ee9c`, `5ad9beb`, `2965411`. No files edited; working tree remains clean.
> 
> Verification used `/usr/bin/python3` 3.14.4:
> 
> - Requested verify command attempted: 14 tests, 10 errors because the sandbox provides no writable temporary directory. Its chained dry run therefore did not execute.
> - Dry run executed separately: exit 0; **573 tracked, 60 included, 513 excluded, 0 findings**.
> - `scripts/plan.py scope REL-1 feat/h1-api-persistence`: **OK**.
> - `scripts/plan.py check`: **OK**, 41 tasks, 7 gates.
> - `scripts/repo.py check`: **PASS**.
> - Full offline suite attempted: 265 tests, 40 errors from unavailable temporary directories. This is not a passing verification result.
> - Actual export creation and clean-install rerun were **not run** under this sandbox.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **No** | Current dry run demonstrated exclusion reporting. Planted-file tests could not execute their fixtures; clean install was not independently rerun. The packet records earlier passing runs, but this review cannot confirm all acceptance items. |
> | 2 | Changes stay within allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside REL-1 allowed paths`. |
> | 3 | Frozen contracts, acceptance text and existing tests preserved | **Yes** | Eight-file diff changes release tooling, adds tests and provenance, and updates coordination records; task acceptance and frozen files are unchanged. |
> | 4 | No unauthorized dependencies or external effects | **Yes** | New tooling uses Python standard library and local Git subprocesses; no added service, dependency installation or network operation. |
> | 5 | Mode labels truthful | **Yes** | Tests explicitly identify synthetic planted values; packet labels author verification as self-review and disclaims live/cloud/publication results. |
> | 6 | Unknowns preserved; no invented facts or receipts | **Yes** | Provenance derives from Git; shallow history blocks export; rights and publication remain unresolved. No invented case or model results found. |
> | 7 | Packet records execution and handoff | **Yes** | `docs/work/reviews/REL-1.md:30–68` records interpreter, commands and results; closing section records outstanding review and next action. |
> | 8 | Consistent with governing direction and invariants | **No** | The two audit bypasses below undermine the required exclusion of credentials and inspection of every exported file. |
> 
> Findings, both **open**:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/release/export.py:313` | A reviewed exception authorizes any matching value up to the recorded hit count, rather than the reviewed placeholder. Replacing the placeholder with a credential leaves one match and passes. | Read-only, in-memory reproduction supplied a synthetic replacement password for `src/demo/__init__.py`: `included=True`, zero findings, one “reviewed exception” note. Existing test only checks an additional match. | Bind exceptions to exact reviewed content or a digest; reject changed matches. Add a same-count replacement regression test. |
> | important | `scripts/release/export.py:548` | Exported README bytes come directly from the current worktree template after auditing. That template is excluded from both content scanning and relevant dirty-worktree blocking, so unaudited content can enter an otherwise clean export. | In-memory filesystem reproduction substituted a synthetic credential assignment in the template: audit had zero findings and the writer emitted that content as `README.md`. No files were written by this reproduction. | Read the template from the audited revision, include it in provenance and content checks, and scan final generated artifacts before writing. Add a regression test proving altered template content blocks export. |
> 
> **Verdict: rework** — two demonstrated audit bypasses remain, and full acceptance verification must be completed in a writable test environment.
**Verdict: rework.** Executor rework next session: an exception must pin the reviewed placeholder value, not a hit count; the exported README template must be audited like other content.

## Rework 2026-10-11 (executor, task/REL-1)

Executor rework of the two `important` findings in the review round above; both were audit
bypasses and both are closed and pinned by tests. No frozen contract, acceptance text or
another task's state changed, no test was weakened, and nothing was pushed, merged, deployed
or published; no model, network or cloud call was made.

### Finding 1 — an exception now pins the reviewed match, not a hit count

`content_exceptions` entries carry `match_sha256`: the sha256 of the exact matched text of
every reviewed hit. `apply_exceptions` covers a path and rule only while the multiset of the
digests of *all* its hits equals that list, so a changed value — including a same-count
replacement — and any added hit is flagged and blocks the export. `validate_config` fails
closed on the old `hits` key, on an empty or non-`[0-9a-f]{64}` digest list and on duplicate
path+rule pairs. The reviewed entry for `src/demo/__init__.py` pins
`f2d6c43988a01f25ddd8d658207dcb7ad725e644749605e5f41f5ea1e5f5eede`, the digest of the labelled
placeholder at line 6; matched values are still never printed — notes and findings carry rule,
line and count only.

The review's reproduction, rerun against the fixed tool (read-only, in memory, no writes;
`.local/rel1-probe.py`, real allowlist and real `src/demo/__init__.py` with the placeholder
replaced by a planted value at the same hit count):

```
as reviewed : 1 hit(s), covered by the exception
replaced    : 1 hit(s), flagged [('credential-assignment', [6])]
```

Regression tests: `PlantedFindings.test_reviewed_exception_pins_the_reviewed_match` (reviewed
placeholder passes; a same-count replacement is a finding and its value is asserted absent
from the output; a second copy of the placeholder is a finding) and
`ExportWrites.test_a_reviewed_exception_covers_the_template_like_any_other_content` (the
exception is keyed on the template path and does not cover a different key in the same file).

### Finding 2 — the generated export files are audited content

`plan_artifacts` reads the `--template` path with `git cat-file` **at the audited revision**
and builds the three generated files before anything is written; `scan_artifacts` scans those
exact bytes with the same content rules, with exceptions keyed on the content source (the
template path for `README.md`). A finding on any generated file blocks the run before any
write — the destination is asserted not to exist afterwards. The template is recorded in the
provenance log and in `EXPORT-AUDIT.json` with its first and last commit, and a worktree
template that differs from the audited revision is reported as a note instead of being
exported. `--template PATH` must be repository-relative; `.`/`..` segments and a path absent
from the audited revision are refused with exit 2. Regression tests:
`ExportWrites.test_altered_template_at_the_audited_revision_blocks_the_export` (a credential
committed into the template yields `content:aws-access-key-id` on `README.md`, exit 1, nothing
written, the value never printed),
`test_worktree_template_edit_cannot_reach_the_export` (an uncommitted credential edit is not
exported; the audited bytes are) and
`test_a_template_outside_or_absent_from_the_audited_revision_is_refused`.

### Commands and results

Interpreter `/usr/bin/python3` (3.14.4); worktree carries the rework edits, audited revision
`1d5eaf2` unless stated.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_release_audit -v && /usr/bin/python3 scripts/release/export.py --dry-run` | requested verify command: `Ran 19 tests in 2.383s … OK` (18 before this rework) then dry run exit 0; report `tracked 590, included 60, excluded 530, generated 3, findings 0`, 646 lines, 30 exclusion rule groups |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 280 tests in 3.745s … FAILED (failures=1)` — the one failure is pre-existing and not this task's; see below |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` — 253 Markdown files, 1098 local links |
| `/usr/bin/python3 scripts/plan.py scope REL-1 feat/h1-api-persistence` | `OK: all changed files inside REL-1 allowed paths` |
| `/usr/bin/python3 scripts/release/export.py --dest .local/export/rel1-rework --force --as-of 2026-10-11` | exit 0, `wrote export of 60 paths`; `diff <(git show HEAD:scripts/release/clean-install.md) .local/export/rel1-rework/README.md` empty |
| `cd .local/export/rel1-rework && /usr/bin/python3 -m unittest discover -s tests` | `Ran 252 tests in 1.718s … OK` — the clean-install instruction in the exported README, executed on the export |
| `/usr/bin/python3 .local/rel1-probe.py` | the two lines quoted under finding 1 |

Acceptance, each with the check actually run in this rework:

1. **Dry run reports every excluded path with a reason** — 530 excluded paths under 30 rule
   groups, each header carrying its reviewed reason, plus unmatched paths with their own
   reason; 646-line report; asserted by
   `DryRunReport.test_every_excluded_path_is_reported_once_with_a_nonempty_reason`, which
   compares the reported set with `git ls-tree -r` for every tracked path.
2. **A planted secret and a planted old file are caught by tests** —
   `PlantedFindings.test_planted_secret_is_excluded_and_its_value_never_printed` and
   `test_planted_old_file_is_excluded_with_its_commit_date` still pass, and the rework adds
   two plantings that previously passed silently: a credential at the reviewed hit count
   (now a finding) and a credential in the committed template (now a finding on `README.md`).
3. **Clean install instructions verified on the export** — the exported README's command run
   inside the written export gave `Ran 252 tests … OK` (row above), and
   `ExportWrites.test_clean_install_instructions_run_on_the_export` runs the same documented
   command inside a fixture export.

Pre-existing failure, not caused by and not fixed by this rework: `tests/test_plan.py`
`test_progress_record_matches_task_states` fails on `CORE-7 state differs between PROGRESS.md
and tasks.json` — `docs/work/tasks.json` has `CORE-7` `done` (with the accepted review record)
while `docs/work/PROGRESS.md` row 46 still reads `in_progress`. Evidence that it predates the
rework: `git diff --stat HEAD -- docs/work/PROGRESS.md docs/work/tasks.json tests/test_plan.py`
is empty, and the same pair of values is present at `b43773a`, so the earlier packet entry
reporting `Ran 265 tests … OK` at this head does not reproduce now. Fixing the mismatch means
editing another task's state row, which this task's rails do not authorise. Exact next action
for the orchestrator: set `CORE-7`'s PROGRESS.md row to `done` (or rerun the check after
doing so).

Not run, and not claimed: `requirements/h1.lock` was not installed (no network use is
authorised in REL-1), and rights/IP clearance, the deck, video and publication remain
REL-5/REL-6 items behind GATE-5.

### Re-run at the rework head

The rework commit is `53ff901`. Re-run there:
`/usr/bin/python3 -m unittest tests.test_release_audit -v` → `Ran 19 tests in 1.873s … OK`;
`/usr/bin/python3 scripts/release/export.py --dry-run` → exit 0, `tracked 590, included 60,
excluded 530, generated 3, findings 0`; `plan.py check` `OK: 41 tasks, 7 gates`;
`repo.py check` `PASS` (253 Markdown files, 1099 local links);
`plan.py scope REL-1 feat/h1-api-persistence` → `OK: all changed files inside REL-1 allowed
paths`.

The [provenance log](../../competition/ai-builder-cup-2026/provenance-log.md) was regenerated
at that head (`… --write-provenance docs/competition/ai-builder-cup-2026/provenance-log.md
--as-of 2026-10-11` → exit 0, `wrote provenance log for 60 included paths`). It now records
`53ff901`, adds the generated-export-files table and corrects two stale readings in the
previous copy:

- its audited revision `108ee9c` is not an ancestor of the branch head
  (`git merge-base --is-ancestor 108ee9c HEAD` → not an ancestor; `108ee9c` is the pre-rebase
  twin of `cd5da40`, and the reviewed `2965411` the twin of `b43773a`), so the branch was
  rebased between sessions and the recorded revision no longer existed in its history;
- consequently the last-commit column for the six included paths the merged CORE-7 work
  touched — the five `src/adapters/gemini/*` files and `tests/test_gemini_transport.py` —
  was stale (`f3c796287090`, 2026-10-06); the regenerated log records `c38fb91e8041` /
  `19c25f76598e` on 2026-10-11. First-commit dates are unchanged for all 60 paths.

The follow-up commit carries only excluded paths (this record and the log itself), so the 60
included paths are unchanged and the log still describes the exported content. State stays
`in_progress`; next action is independent re-review on `task/REL-1`.

## Interim review (orchestrator seat, Fable, commit e12e3b5, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated
re-review is required before `done`. Reviewer did not author any part of the change. Range
reviewed: `feat/h1-api-persistence..e12e3b5` (six commits, eight files); worktree clean; no
file edited other than this record. Interpreter `/usr/bin/python3` (3.14.4), run from the
`task/REL-1` worktree.

### Verification (run by this reviewer)

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_release_audit -v && /usr/bin/python3 scripts/release/export.py --dry-run` | `Ran 19 tests in 2.237s … OK`; dry run exit 0, `tracked 591, included 60, excluded 531, generated 3, findings 0`, 646 lines, 30 exclusion rule groups, 1 note (the reviewed `src/demo/__init__.py` exception) |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 280 tests in 5.491s … OK` (the CORE-7 PROGRESS/tasks mismatch the rework packet reported at `53ff901` no longer reproduces at `e12e3b5`) |
| `/usr/bin/python3 scripts/plan.py scope REL-1 feat/h1-api-persistence` | `OK: all changed files inside REL-1 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` — 253 Markdown files, 1101 local links |
| `/usr/bin/python3 scripts/release/export.py --dest <scratchpad>/export --as-of 2026-10-12` (outside the repository) | exit 0, `wrote export of 60 paths`; 63 files = 60 included + `README.md`, `PROVENANCE.md`, `EXPORT-AUDIT.json`; `diff <(git show HEAD:scripts/release/clean-install.md) README.md` empty |
| `cd <scratchpad>/export && /usr/bin/python3 -m unittest discover -s tests` | `Ran 252 tests in 3.816s … OK` — the README's clean-install command, executed on the export |

### The two reviewed loopholes

Both are closed by construction, not by a narrower fixture:

1. **Exception by hit count** — `apply_exceptions` (`scripts/release/export.py:346-366`) covers a
   path and rule only while the sorted list of sha256 digests of *every* hit equals the reviewed
   `match_sha256` list; `match_hits` (:329-343) digests `found.group(0)`, the exact matched text
   including the credential-like name. A same-count replacement, an added hit, or a hit on any
   other rule is flagged. `validate_config` (:199-218) refuses the old `hits` key, empty or
   non-hex digests and duplicate path+rule pairs. Exceptions are keyed on the exact source path
   (:359), not a prefix, so moving the file drops coverage. Test
   `test_reviewed_exception_pins_the_reviewed_match` asserts the same-count replacement is a
   finding and its value is absent from the output.
2. **Template escaping the scan** — `plan_artifacts` (:431-458) reads the template with `git
   cat-file` at the audited revision, builds all three generated files first, and
   `scan_artifacts` (:403-428) scans those exact bytes with the content rules before anything is
   written; `write_export` (:709-710) writes those same bytes. The worktree copy is never read
   (`note_template_state`, :390-400, only reports a difference). Tests
   `test_altered_template_at_the_audited_revision_blocks_the_export` and
   `test_worktree_template_edit_cannot_reach_the_export` pin both paths.

Further bypasses considered and found closed: symlinks, submodules and unusual modes become a
`not-a-regular-file` finding (:499-502); `write_export` iterates `report.included` after the
scan and nothing mutates the list between (:703, :741-756); blobs are read at the immutable
audited revision, so a worktree edit cannot enter (:706); a NUL in the first 8 KiB fails closed
as `binary-content` (:375, :413); control characters in a path leave it absent from `git log`
output and it fails closed as `history-unrecorded` (:515-519); a shallow clone is a blocker
(:505-511). Two adjacent gaps were found and are reported below.

### Checklist

| # | Item | Answer | Evidence |
|---|---|---|---|
| 1 | Every acceptance item met by a check actually run | **Yes** | (1) dry run: 531 excluded paths each under a rule header with a reason, asserted against `git ls-tree -r` by `test_every_excluded_path_is_reported_once_with_a_nonempty_reason`; (2) `test_planted_secret_is_excluded_and_its_value_never_printed` and `test_planted_old_file_is_excluded_with_its_commit_date` pass in 19/19; (3) export written and the README command run inside it, `Ran 252 tests … OK` (table above). Note: the real history has 0 commits before 2026-09-07 (`git rev-list --count --before=2026-09-07T00:00:00 HEAD` → 0), so the cutoff gate is exercised by fixture only today. |
| 2 | No file outside allowed paths | **Yes** | `plan.py scope REL-1 feat/h1-api-persistence` → OK; `git diff --stat` shows the eight allowed files only. |
| 3 | No frozen contract, acceptance text or test weakened | **Yes** | Diff touches no `src/`, no `docs/work/probe-bundle/intent.md`, no working paper; REL-1 acceptance text in `tasks.json` unchanged (only `state`); `grep -n "skip\|expectedFailure" tests/test_release_audit.py` → none; 19 tests, up from 13. |
| 4 | No new dependency, service, credential, network, model or cloud effect | **Yes** | stdlib imports only (`export.py:39-48`); subprocess calls are `git` in the local repository; no push, merge or publication in the log. |
| 5 | Mode labels truthful | **Yes** | Fixtures labelled synthetic (`PLANTED_SECRET` is the AWS documentation example key); the packet labels its first section self-review and the rework as executor work; no live or stored-run claim. |
| 6 | Unknowns stayed unknown | **Yes** | Dates read from `git log`; unrecorded history and shallow clones fail closed; rights/IP and publication left to REL-5/REL-6; the packet corrected its own stale `108ee9c` reading after the rebase. |
| 7 | Packet records interpreter, commands, results, unfinished items, next action | **Yes** | Rework section and "Re-run at the rework head" above; the one discrepancy (full suite 279/280 at `53ff901` vs 280/280 now) is explained by the CORE-7 row having been fixed upstream. |
| 8 | Nothing contradicts blueprint, strategy, working paper or invariants | **No** | Finding 1: the tool's own docstring (`export.py:21-25`) and the exported `PROVENANCE.md` (:567-570) claim the generated files are "content like any other", but the README's source skips the history gate and may be redirected to any tracked path, so that claim is not yet true. |

### Findings

Reproductions used a throwaway repository under a temp directory; no tracked file was written.
Fixture: one commit dated 2026-08-01 adding `private/old-notes.md` and `private/old-module.py`,
then a 2026-10-05 commit adding `templates/clean-install.md`, `src/app.py`, `tests/test_app.py`,
then `git mv private/old-module.py src/legacy.py` committed 2026-10-05; allowlist includes
`src`, `tests`, excludes `private` (reason "rights not cleared") and `templates`, cutoff
2026-09-07.

| severity | path:line | failure mechanism | evidence | correction |
|---|---|---|---|---|
| important | `scripts/release/export.py:438-443` (`plan_artifacts`), `:596` (history fetched for display only) | The README's source is subject to the content scan but not to the history gate: the template's first-commit entry is read for `PROVENANCE.md` but never compared with `report.cutoff`, and an absent entry is not a `history-unrecorded` finding. `--template` accepts any path present at the audited revision, so a pre-cutoff or excluded file can be redirected into the export as `README.md` with exit 0. | `export.py --root <fixture> --allowlist <fixture>/allowlist.json --template private/old-notes.md --dest <tmp>/outA` → exit 0, `tracked 5, included 3, excluded 2, generated 3, findings 0`, `FINDINGS (block the export) (0)`; `<tmp>/outA/README.md` holds the 2026-08-01 excluded text. Default template is unaffected (`scripts/release/clean-install.md` first commit 2026-10-11 `f4bca10`). | In `plan_artifacts`, apply the same checks a candidate gets to the template's history entry: missing → `history-unrecorded` finding on `README.md`; `first.date < cutoff` → `history-pre-cutoff` finding on `README.md`, both blocking before any write. Constrain `--template` to `scripts/release/` (or a key in the allowlist) so it cannot name an arbitrary tracked path. Add a test planting a pre-cutoff template and asserting exit 1, nothing written. |
| minor | `scripts/release/export.py:294-310` (`history_map`) | First-commit dates are per path name from one `git log --name-only` pass with no rename or copy tracking, so pre-cutoff content moved into an included tree after the cutoff gets the move date as its first commit; the cutoff gate and the provenance log are both wrong for it. No present exposure: the audited history contains 0 commits before 2026-09-07 and no included blob appears in a pre-cutoff commit. | Fixture dry run: `src/legacy.py` included, `findings 0`; audit record `history.first = 2026-10-05 13861d33d3b1` while `git log --follow -- src/legacy.py` ends at `2026-08-01 34e9f8b` and `git rev-parse HEAD:src/legacy.py` equals `HEAD~1:private/old-module.py` (`1a033c1f…`). | Add a blob-level check: collect the blob ids introduced by every commit before the cutoff (`git log --before=<cutoff> --raw --no-renames --format=`), and flag an included path whose blob id is in that set as `history-pre-cutoff` (content). Record the limitation in the provenance "Not covered" section until then. |
| minor | `scripts/release/export.py:629-630` (`audit_record` → exported `EXPORT-AUDIT.json`) | The exported machine-readable record lists every excluded path by name, including 93 `docs/research` dossier filenames, 9 case-pack names and 53 archive names (155 of 531). Content rules find no hits in them, but third-party titles and internal structure are disclosed in the public export. The template documents this as design, so it is a REL-5 decision, not an escape. | `--dry-run --json` record: 93 `docs/research/` paths in `excluded`; the generated `EXPORT-AUDIT.json` (135,118 bytes) carries them; `PROVENANCE.md` carries per-rule counts only. | Ship per-rule counts and reasons in the exported copy (as `PROVENANCE.md` already does) and keep the full path list in the repository copy, or have REL-5 explicitly accept the disclosure. |

**Interim verdict: rework.** The two reviewed loopholes are closed by construction and all three
acceptance items were independently re-verified, but the generated README's source still escapes
the history gate and can be redirected to any tracked path, so the tool's own "content like any
other" guarantee is not yet true; one `important` finding keeps the task `in_progress` pending
the executor's fix and the designated independent re-review.

## Rework 3 2026-10-12 (executor, task/REL-1, commit `70964f9`)

Executor rework of the interim review's findings at `e12e3b5`: one `important` (the generated
README's source skipped the history gate and could name any tracked path) and two `minor`
(first-commit dates blind to renames; excluded path names in the shipped `EXPORT-AUDIT.json`).
All three are fixed and pinned by tests. No frozen contract, acceptance text or another task's
state changed; no test was weakened; nothing was pushed, merged, deployed or published; no
model, network or cloud call was made.

### Finding 1 (important) — the README source passes the history gate and cannot leave `scripts/release/`

`stale_history` (`scripts/release/export.py:356`) is now the single cutoff decision for any
path, and `plan_artifacts` (`:528`) applies it to the `--template` path: a template absent from
the audited history is a `history-unrecorded` finding on `README.md`; a pre-cutoff template
path, or a template whose bytes were already committed before the cutoff, is
`history-pre-cutoff` on `README.md`; both block before anything is written. `--template` must
be a repository-relative path under `scripts/release/` (`:513`), so the README source cannot be
redirected to a pre-cutoff or excluded file elsewhere, and `BlobReader.blob` (`:106`) refuses a
tree or gitlink spec instead of reading it as file content. `scan_artifacts` (`:481`) keeps the
first finding on a generated file instead of overwriting it with a later content hit.

Regression tests: `test_a_pre_cutoff_template_blocks_the_export`
(`tests/test_release_audit.py:459`),
`test_a_template_holding_pre_cutoff_content_blocks_the_export` (`:470`),
`test_a_template_without_a_recorded_history_blocks_the_export` (`:483`) and
`test_a_template_outside_the_reviewed_directory_is_refused` (`:448` — a tracked, fresh,
content-clean file elsewhere in the tree is refused with exit 2 and nothing written).

### Finding 2 (minor) — blob-level cutoff check closes the rename bypass

`precutoff_blob_map` (`:332`) collects, in one `git log --raw --no-renames --no-abbrev` pass
over the same author dates the cutoff gate reads, every blob present at a commit dated before
the cutoff; `stale_history` then flags an included path whose current blob id is in that set as
`history-pre-cutoff`. `git log --raw` abbreviates object names by default (7-character ids
against full `ls-tree` ids), so the first draft of this pass matched nothing; the probe caught
it and `--no-abbrev` is the fix. The residual limit — content edited after such a move keeps
the later date — is now stated in the provenance log's "Not covered" section. Regression test
`test_pre_cutoff_content_moved_into_an_included_path_is_caught` (`:290`, the review's rename
fixture; a genuinely new file still passes) and the template variant `:470`.

### Finding 3 (minor) — the shipped record no longer publishes excluded path names

`plan_artifacts` writes `audit_record(report, disclose_excluded_paths=False)` (`:704`) into the
export's `EXPORT-AUDIT.json`: excluded content is recorded as rule, reason and path count per
rule (30 entries, counts summing to 531), not as path names. The repository-side `--json`
record keeps every excluded path (`excluded_disclosure: "paths"`) and the dry run still names
every excluded path with its reason, which is what acceptance 1 checks. At `70964f9` the
shipped record is 25,600 bytes and contains none of `docs/research/`, `docs/cases/`,
`archive/`, `docs/work/` or `tests/test_release_audit`; the full repository-side record is
135,152 bytes. `scripts/release/clean-install.md`, shipped as `README.md`, now describes the
shipped form honestly. Tests: `test_export_carries_only_audited_paths_and_records_them`
(`:344`) and `test_the_repository_json_record_keeps_every_excluded_path` (`:492`).

### The reviewer's fixture, rerun against the fixed tool

Read-only, in memory, no tracked file written; `.local/rel1-probe-r3.py` builds the review's
fixture (pre-cutoff `private/` module moved into `src/` by `git mv`, templates outside and
inside `scripts/release/`) with a throwaway allowlist:

```
excluded pre-cutoff template : exit 2 | export audit error: template must be a repository-relative path under scripts/release/ inside the audited revision, not 'private/old-notes.md'
                            outA written: False
template outside scripts/   : exit 2 | export audit error: template must be a repository-relative path under scripts/release/ inside the audited revision, not 'templates/clean-install.md'
pre-cutoff template in dir  : exit 1 | ['[history-pre-cutoff] — content first committed 2026-08-01 in a0e6a43babe1']
                            outC written: False
moved pre-cutoff content    : included False | rule history-pre-cutoff | content first committed 2026-08-01 in a0e6a43babe1
fresh source file           : included True
fresh template, blocked run : exit 1 | ['src/legacy.py: identical content was committed 2026-08-01, before the 2026-09-07 freshness cutoff']
fresh template, clean run   : exit 0 | wrote export of 2 paths to /tmp/rel1probe-5y8namxm/outE
```

The interim review's reproduction (`--template private/old-notes.md`) exited 0 with the
excluded pre-cutoff text as `README.md`; it now exits 2 and writes nothing, and every variant
of the bypass fails closed.

### Commands and results

Interpreter `/usr/bin/python3` (3.14.4); worktree clean at `70964f9` unless stated.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_release_audit -v && /usr/bin/python3 scripts/release/export.py --dry-run` | requested verify command: `Ran 25 tests in 5.502s … OK` (19 before this rework, +6 new); dry run exit 0, `tracked 591, included 60, excluded 531, generated 3, findings 0`, 646-line report, 30 exclusion rule groups, 1 note (the reviewed `src/demo/__init__.py` exception) |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 286 tests in 8.988s … OK` (280 before this rework; the CORE-7 PROGRESS/tasks mismatch the previous rework reported no longer reproduces) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` — 253 Markdown files, 1102 local links |
| `/usr/bin/python3 scripts/plan.py scope REL-1 feat/h1-api-persistence` | `OK: all changed files inside REL-1 allowed paths` |
| `/usr/bin/python3 scripts/release/export.py --dest .local/export/rel1-rework3b --as-of 2026-10-12` | exit 0, `wrote export of 60 paths`; 63 files = 60 included + `README.md`, `PROVENANCE.md`, `EXPORT-AUDIT.json`; `README.md` equals `git show HEAD:scripts/release/clean-install.md` |
| `cd .local/export/rel1-rework3b && /usr/bin/python3 -m unittest discover -s tests` | `Ran 252 tests in 3.048s … OK` — the README's clean-install command, executed on the export |
| `/usr/bin/python3 scripts/release/export.py --write-provenance docs/competition/ai-builder-cup-2026/provenance-log.md --as-of 2026-10-12` | exit 0, `wrote provenance log for 60 included paths`; the log now records `70964f9`, the blob-level history pass and the "Not covered" rename limit; the 60 included paths' first/last commits are unchanged |
| `/usr/bin/python3 .local/rel1-probe-r3.py` | the reviewer's fixture, output above |

Acceptance, each with the check actually run in this rework:

1. **Dry run reports every excluded path with a reason** — the 646-line report groups 531
   excluded paths under 30 rule groups, each header carrying its reviewed reason, plus
   unmatched/generated decisions with their own reasons; asserted against `git ls-tree -r` by
   `DryRunReport.test_every_excluded_path_is_reported_once_with_a_nonempty_reason`.
2. **A planted secret and a planted old file are caught by tests** —
   `test_planted_secret_is_excluded_and_its_value_never_printed` and
   `test_planted_old_file_is_excluded_with_its_commit_date` still pass, and the rework adds
   plantings of the three bypasses it closes: an excluded pre-cutoff template, a template
   whose bytes predate the cutoff, and pre-cutoff content moved into an included path.
3. **Clean install instructions verified on the export** — the exported README's command run
   inside the written export gave `Ran 252 tests … OK` (row above), and
   `ExportWrites.test_clean_install_instructions_run_on_the_export` runs the same documented
   command inside a fixture export.

Not run, and not claimed: `requirements/h1.lock` was not installed (no network use is
authorised in REL-1), and rights/IP clearance, the deck, video and publication remain REL-5/REL-6
items behind GATE-5. Whether `scripts/release/**` ships in the export stays the REL-5 decision
the interim review recorded; this rework confines `--template` to that directory rather than
changing what is allowed to be exported.

Task state is `in_progress` in `docs/work/tasks.json` (unchanged — it was already set by the
previous round) and its `PROGRESS.md` row is updated in the same commit as this record. The
follow-up commit carries only excluded paths (this record, the regenerated log, the PROGRESS
row), so the 60 included paths are unchanged and the log still describes the exported content.
Next action: independent re-review by the designated reviewer (GPT Astra) on `task/REL-1`;
only an `accept` verdict sets REL-1 `done`. No stop condition fired and no work inside the
brief's allowed paths is unfinished. This record implies no publication, deployment or merge.

## Designated review 1 (GPT Astra, independent, commit `784f29f`, 2026-10-12)

> Independent review of `784f29f2eb45` against `feat/h1-api-persistence`, covering the requested diff and all 10 branch commits. No repository files edited; working tree remains clean.
> 
> Verification using `/usr/bin/python3` 3.14.4:
> 
> - Requested verify command: **25 tests passed**, dry run exit **0**; 628 tracked, 89 included, 539 excluded, 3 generated, 0 findings.
> - Requested scope command: **OK**.
> - `plan.py check`: **OK**; `repo.py check`: **PASS**.
> - Full offline suite: **286 tests passed**.
> - Fresh temporary export: exit **0**; exported README’s clean-install command: **252 tests passed**.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes** | Exclusion-reporting and planted secret/old-file tests passed; actual export’s documented clean-install command passed. |
> | 2 | Only allowed paths changed | **Yes** | Eight-file diff; requested scope command printed `OK`. |
> | 3 | Frozen contracts, acceptance text and tests preserved | **Yes** | Frozen files untouched; tasks.json changes only REL-1 state; no existing tests weakened or skipped. |
> | 4 | No unauthorized dependencies or external effects | **Yes** | Standard-library implementation and local Git subprocesses; no network, model or cloud operation added. |
> | 5 | Mode labels truthful | **Yes** | Plantings explicitly use synthetic fixtures; author verification is labelled self-review; no live-run claim. |
> | 6 | Unknowns preserved | **Yes** | Missing/shallow history blocks export; rights, hosting and publication remain unverified. |
> | 7 | Packet records execution and handoff | **Yes** | Packet records interpreter, commands, results, limitations and next action; its current-content assertion needs correction below. |
> | 8 | Consistent with domain invariants | **No** | Reproduced a content-scan bypass that exports a planted credential-shaped value inside binary content. |
> 
> Findings, both unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | **important** | `scripts/release/export.py:444` and `:484` | Binary rejection checks only the first 8 KiB. Later NUL bytes survive decoding and interrupt secret-pattern matching, allowing unscannable content into the export. | Temporary fixture containing 8,192 ASCII spaces followed by a UTF-16LE AWS example key exported unchanged: exit **0**, **0 findings**. | Validate the entire payload before scanning; reject NUL-containing or unsupported text encodings consistently for source and generated files. Add regression tests for both routes. |
> | **minor** | `docs/competition/ai-builder-cup-2026/provenance-log.md:8`; `docs/work/reviews/REL-1.md:475` | Checked-in provenance no longer covers every currently included path; the packet’s assertion that included content is unchanged is stale. | Log records **60** included paths; HEAD exports **89**. All **29** additional `tests/fixtures/probe-bundle/` paths lack log entries. | Regenerate provenance against the reviewed revision and update the packet’s counts and content-continuity assertion. |
> 
> **Verdict: rework.** The explicit acceptance checks pass, but the reproduced binary-content bypass leaves an important confidentiality finding unresolved.
**Verdict: rework.** a binary-content bypass of the secret scan was reproduced; close it by construction (scan bytes, not only decoded text). Address every blocking/important row above; dispose of minors explicitly.

## Rework 4 2026-10-12 (executor, task/REL-1, commit `ce7d2dc`)

Executor rework of the designated review's findings at `784f29f`: one `important` (the secret
scan read only the first 8 KiB, so a UTF-16LE credential behind a longer NUL-free prefix
exported unscanned) and one `minor` (the checked-in provenance log covered 60 included paths
while the head exported 89, and the packet's content-continuity assertion was stale). Both are
fixed and pinned by tests. No frozen contract, acceptance text or another task's state changed;
no test was weakened; nothing was pushed, merged, deployed or published; no model, network or
cloud call was made. Detection note for the record: a second executor session (`rel-1-42`) was
launched into this same worktree for the same rework; it detected the collision, handed the
worktree over and stood down before any commit — it had written the `scannable_text` helper
retained below. Every edit, command and commit recorded here is this session's.

### Finding 1 (important) — the content scan validates the whole payload

`scannable_text` (`scripts/release/export.py:440`) now reads the *entire* payload before any
pattern runs: one NUL byte anywhere, or bytes with no UTF-8 reading, is unscannable content and
becomes a blocking `binary-content` finding rather than a scan. `scan_content` (`:456`) and
`scan_artifacts` (`:492`, the generated README.md / PROVENANCE.md / EXPORT-AUDIT.json route) call
the same helper, and both match against the decoded text — not `decode("utf-8", "replace")`,
whose replacement characters broke every pattern. The prefix test `b"\x00" in data[:8192]` is
gone from both call sites; the module docstring states the whole-payload rule.

The reviewer's reproduction, rerun in a throwaway fixture (`.local/rel1-probe-r4.py`, read-only;
the reviewed tool is extracted with `git show HEAD:scripts/release/export.py` into the temp dir;
both routes carry 8,192 ASCII bytes then `KEY = 'AKIA…EXAMPLE'` encoded UTF-16LE):

```text
== tracked source file (src/notes.py), 8 KiB prefix then UTF-16LE key
   reviewed HEAD tool   exit 0 | tracked 3, included 2, excluded 1, generated 3, findings 0 | out written: True | planted payload in export: True | key value printed: False
   rework worktree tool exit 1 | tracked 3, included 1, excluded 2, generated 3, findings 1 | finding binary-content | out written: False | planted payload in export: False | key value printed: False
== generated README.md (template), same payload
   reviewed HEAD tool   exit 0 | tracked 1, included 0, excluded 1, generated 3, findings 0 | out written: True | planted payload in export: True | key value printed: False
   rework worktree tool exit 1 | tracked 1, included 0, excluded 1, generated 3, findings 1 | finding binary-content | out written: False | planted payload in export: False | key value printed: False
```

Regression tests, three new (28 total, from 25):
`PlantedFindings.test_a_secret_after_a_long_binary_prefix_is_blocked_not_scanned`
(`tests/test_release_audit.py:269` — the decision, exit 1, nothing written, value never printed),
`PlantedFindings.test_a_payload_that_is_not_valid_utf8_is_blocked` (`:293` — one non-UTF-8 byte
stands for "unsupported encoding") and
`ExportWrites.test_binary_content_in_the_template_blocks_the_generated_readme` (`:430` — the
generated-file route, exit 1, nothing written).

### Finding 2 (minor) — provenance covers every included path again

The log was regenerated at this rework's head:
`628 tracked, 89 included, 539 excluded, 3 generated, 0 findings`, with a first/last commit row
for each of the 89 included paths. The previous copy recorded 60 included paths at `70964f9`;
the 29 paths added since are all under `tests/fixtures/probe-bundle/` (the EVAL-1 fixtures merged
after that log). The reviewed revision `784f29f` already exported 89 paths, so the old log was
stale there too.

Correction of the earlier continuity assertions: the paragraphs above stating that a follow-up
commit "carries only excluded paths … so the 60 included paths are unchanged and the log still
describes the exported content" (the "Re-run at the rework head" paragraph) are superseded by
this section. They were true of `70964f9` and the commits immediately after it, not of the head
the reviewer audited. Measured now: the included set is identical at `784f29f` and at `ce7d2dc`
(89 paths), and the only paths changed between the two revisions are `docs/work/PROGRESS.md`,
`docs/work/reviews/REL-1.md`, `scripts/release/export.py` and `tests/test_release_audit.py`,
each decided excluded by the allowlist (`internal-planning`, `release-tooling`,
`release-audit-tests`), so every included path is byte-identical and the regenerated log
describes the exported content.

### Commands and results

Interpreter `/usr/bin/python3` (3.14.4); worktree clean at `ce7d2dc` unless stated.

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest tests.test_release_audit -v && /usr/bin/python3 scripts/release/export.py --dry-run` | requested verify command: `Ran 28 tests in 3.372s … OK` (25 before this rework) then dry run exit 0, `tracked 628, included 89, excluded 539, generated 3, findings 0` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 289 tests in 5.376s … OK` (286 before this rework) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` (41 at the review; the extra task was added to the plan by another session, not by REL-1) |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` — 259 Markdown files, 1164 local links, 8 skills |
| `/usr/bin/python3 scripts/plan.py scope REL-1 feat/h1-api-persistence` | `OK: all changed files inside REL-1 allowed paths` |
| `/usr/bin/python3 scripts/release/export.py --dest .local/export/rel1-rework4 --force --as-of 2026-10-12` | exit 0, `wrote export of 89 paths`; 92 files = 89 included + `README.md`, `PROVENANCE.md`, `EXPORT-AUDIT.json`; `README.md` equals `git show HEAD:scripts/release/clean-install.md` |
| `cd .local/export/rel1-rework4 && /usr/bin/python3 -m unittest discover -s tests` | `Ran 252 tests in 2.390s … OK` — the clean-install command in the exported README, executed on the export |
| `/usr/bin/python3 scripts/release/export.py --write-provenance docs/competition/ai-builder-cup-2026/provenance-log.md --as-of 2026-10-12` | exit 0, `wrote provenance log for 89 included paths`; the log records `ce7d2dc` |
| `/usr/bin/python3 .local/rel1-probe-r4.py` | the reviewer's two routes, output above |
| `/usr/bin/python3 .local/rel1-check-report.py` | dry run exit 0; the 628 reported paths equal `git ls-tree -r` path for path; 4 include and 30 exclude rule groups, none with an empty reason; 89 included, 539 excluded |

Acceptance, each with the check actually run in this rework:

1. **Dry run reports every excluded path with a reason** — 539 excluded paths under 30 rule
   groups, each header carrying its reviewed reason, plus unmatched paths with their own reason;
   the reported set equals `git ls-tree -r` path for path (last table row, and asserted by
   `DryRunReport.test_every_excluded_path_is_reported_once_with_a_nonempty_reason`).
2. **A planted secret and a planted old file are caught by tests** —
   `test_planted_secret_is_excluded_and_its_value_never_printed` and
   `test_planted_old_file_is_excluded_with_its_commit_date` still pass, and this rework adds the
   planting the designated review used — a credential behind 8 KiB of NUL-free prefix — on both
   the source and the generated-file route.
3. **Clean install instructions verified on the export** — the exported README's command run
   inside the written export gave `Ran 252 tests … OK` (table row above), and
   `ExportWrites.test_clean_install_instructions_run_on_the_export` runs the same documented
   command inside a fixture export.

Not run, and not claimed: `requirements/h1.lock` was not installed (no network use is authorised
in REL-1), and rights/IP clearance, the deck, video and publication remain REL-5/REL-6 items
behind GATE-5. Whether `scripts/release/**` ships in the export stays the REL-5 decision recorded
above.

State stays `in_progress`: `docs/work/tasks.json` already carries that state for REL-1 (checked
before this commit; no other field of it was touched) and `docs/work/PROGRESS.md` gets the
matching log row in the same commit. The follow-up commit carries only excluded paths — this
record, the regenerated log and the `PROGRESS.md` row — so the 89 included paths are unchanged
and the log still describes the exported content. Next action: designated independent re-review
on `task/REL-1`; only an `accept` verdict sets REL-1 `done`. No stop condition fired and no work
inside the brief's allowed paths is unfinished. This record implies no publication, deployment
or merge.

### Re-run at the record head

The rework commits are `ce7d2dc` (the tool and its tests) and `95f098d` (this record, the
regenerated log and the `PROGRESS.md` row). Re-run at `95f098d` with a clean worktree:
`/usr/bin/python3 -m unittest tests.test_release_audit -v` → `Ran 28 tests in 3.176s … OK`;
`/usr/bin/python3 scripts/release/export.py --dry-run` → exit 0, `tracked 628, included 89,
excluded 539, generated 3, findings 0`, 1 note (the reviewed `src/demo/__init__.py` exception);
`/usr/bin/python3 -m unittest discover -s tests` → `Ran 289 tests in 12.069s … OK`;
`/usr/bin/python3 scripts/plan.py check` → `OK: 42 tasks, 7 gates`;
`/usr/bin/python3 scripts/repo.py check` → `PASS` (259 Markdown files, 1166 local links);
`/usr/bin/python3 scripts/plan.py scope REL-1 feat/h1-api-persistence` → `OK: all changed files
inside REL-1 allowed paths`. Every commit after `ce7d2dc` carries only excluded paths
(`docs/competition/ai-builder-cup-2026/provenance-log.md`, `docs/work/PROGRESS.md`,
`docs/work/reviews/REL-1.md`), so the 89 included paths and the regenerated log that dates them
are unchanged.

## Designated review (GPT Astra, independent, commit `dd387a0`, 2026-10-12)

> Independent review of `dd387a084fe2`, using the requested diff and commit log against `feat/h1-api-persistence`. No files edited.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | All acceptance items demonstrated | Yes | Requested verify command passed: 28 tests; dry run reported all 632 tracked paths, including 543 exclusions with reasons. Planted-secret and old-file tests passed. A fresh export’s documented clean-install command passed 252 tests. |
> | 2 | Changes within allowed paths | Yes | `scope REL-1 feat/h1-api-persistence` printed `OK: all changed files inside REL-1 allowed paths`. |
> | 3 | Contracts and acceptance unchanged; tests not weakened | Yes | Eight-file diff changes only release tooling, new tests, provenance and coordination records. Frozen contracts and acceptance text unchanged. |
> | 4 | No unauthorized dependencies or external effects | Yes | Implementation uses standard-library code and local Git subprocesses. No new service, credential, network or cloud operation introduced. |
> | 5 | Truthful mode labels | Yes | Tests label planted values and synthetic fixtures explicitly; clean-install instructions describe offline synthetic execution. |
> | 6 | Unknowns preserved | Yes | Provenance derives from Git history; shallow history blocks export. Rights, hosted installation and publication remain explicitly unverified. |
> | 7 | Complete verification and handoff record | Yes | `docs/work/reviews/REL-1.md` records interpreter, commands, results, limitations and independent re-review as the next action. Historical counts are tied to their recorded revisions. |
> | 8 | Consistent with direction and domain invariants | Yes | Export preserves source bytes, excludes internal material, blocks audit findings and performs no publication. Provenance contains entries for all 89 included paths. |
> 
> Additional verification: full offline suite **289 tests passed**; `plan.py check` **OK**; `repo.py check` **PASS**. Python **3.14.4**.
> 
> Findings: none.
> 
> **Verdict: accept** — all three acceptance items were demonstrated, the prior scan bypass is covered by passing regressions, and no blocking or important findings remain.
**Verdict: accept.** 
