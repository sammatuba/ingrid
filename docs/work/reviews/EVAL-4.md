# Review: EVAL-4

Reviewed commit `1a290e7` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of `1a290e7a6c1d` against `feat/h1-api-persistence`. Inspected the requested diff and both commits (`fe99f35`, `1a290e7`). Working tree clean; no files edited.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **No** | Executed assertions confirm all 16 chronology items have research-30 URLs, permitted flags and null first availability; no sources registered or statements verified. Seven filenames exist, but provenance structure is incomplete (finding 1). |
> | 2 | Changes confined to allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EVAL-4 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests unchanged | **Yes** | Diff changes only seven pack files, task state, progress and self-review record. |
> | 4 | No unauthorized dependencies or external effects | **Yes** | Documentation-only diff; no dependency, executable integration or external-effect receipt added. |
> | 5 | Truthful mode labels | **Yes** | Pack consistently says skeleton, unreviewed, unregistered and uncomputed; no live-run claim. |
> | 6 | Unknowns preserved; no invented facts or numbers | **No** | Scenario assigns an unresolved capacity magnitude and precise start convention; BESS quantity loses its inequality (findings 2–3). |
> | 7 | Complete verification and handoff record | **Yes** | `docs/work/reviews/EVAL-4.md:9` records interpreter, commands and results; line 51 records unfinished work and next action. Author’s suite success was not reproduced here. |
> | 8 | Consistent with governing direction and invariants | **No** | Unsupported numerical precision conflicts with preserving unknown capacity kinds and dates. Other review and execution boundaries remain explicit. |
> 
> Checks executed:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 244 Markdown files, 1048 local links.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-4 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**, 41 tasks, 7 gates.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -v` — **251 tests, 30 errors**; reported errors include unavailable writable temporary directories in this sandbox. Not a passing run.
> - Read-only JSON assertions — **PASS** for chronology flags, availability, URL membership, registration state and seven filenames.
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/cases/visayas-2026-09/evidence-manifest.json:24` | Seven filenames are treated as complete structural validation despite missing provenance slots. | Chronology records contain URLs and summaries but no immutable version reference or exact-passage/numerical-lineage field, required by `first-case.md`. Self-review claims these exist. | Add explicit pending/null provenance fields and capture requirements; validate field coverage and correct the self-review claim. Originals need not be captured for this skeleton. |
> | important | `docs/cases/visayas-2026-09/scenario-proposal.md:35` | Converts unresolved source information into a specified numerical path. | Research 30 supplies “150 MW” without capacity kind and “last week of October”; the proposal assigns 150 MW available capacity starting on that window’s first day. `mappings.json` explicitly leaves capacity representation unresolved. | Keep magnitude and precise alternative start unresolved, naming the field and reported window only until supported construction is reviewed. |
> | minor | `docs/cases/visayas-2026-09/mappings.json:154` | Structured quantity drops a material qualifier. | Source token says “over 250 MW”; `recorded_quantity.value` is exactly `"250"` with no comparator. | Preserve `>250` using an explicit qualifier, or leave the numeric quantity null and retain the source wording. |
> 
> **Verdict: rework** — incomplete provenance structure and unsupported numerical specificity prevent acceptance of the skeleton as submitted.
## Outcome and next action

**Verdict: rework.**
Executor adds explicit pending provenance fields, removes the numerical path the sources do not support, keeps the `>250 MW` qualifier; then re-review.

## Review round 2026-10-11 evening (commit `7286da1`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `7286da182209` against `feat/h1-api-persistence`, including the requested diff and all five branch commits. Working tree clean; no files edited.
> 
> | # | Checklist | Answer | Evidence |
> |---|---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes** | Executed assertions confirm all 16 chronology items carry research-30 URLs, permitted flags, null first availability and unregistered status. Manual inspection confirms all seven first-case artifacts contain their required fields or explicit pending slots; no verification claim exists. |
> | 2 | Changes confined to allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside EVAL-4 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests unchanged | **Yes** | Diff contains only case documentation, review record, progress and task state. |
> | 4 | No unauthorized dependencies or external effects | **Yes** | Documentation-only change; no integration, dependency or external execution added. |
> | 5 | Truthful mode labels | **Yes** | Case artifacts explicitly identify skeleton, unreviewed, unregistered and uncomputed states. |
> | 6 | Unknowns preserved; no invented facts or numbers | **Yes** | Provenance slots remain null; mappings remain unresolved; scenario magnitude and precise alternative start remain unspecified; BESS retains `>` qualifier. |
> | 7 | Complete verification and handoff record | **Yes** | `packet.md:71–104` records interpreter, commands, results, unfinished work and next action. Author’s passing suite result was not reproduced here. |
> | 8 | Consistent with governing direction and invariants | **Yes** | Scenario names `assumed_available_capacity`, preserves mapping and approval blocks, and leaves consequences uncomputed, consistent with working-paper §5.6. |
> 
> Checks executed:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**; 245 Markdown files, 1,052 local links.
> - `/usr/bin/python3 scripts/plan.py scope EVAL-4 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK**; 41 tasks, 7 gates.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -v` — **251 tests, 30 errors** caused by unavailable writable temporary directories; not a passing run.
> - Read-only inline JSON assertions — **PASS** for chronology, provenance, URL membership, registration state, unresolved mappings, BESS qualifier and required files.
> 
> Findings: **none outstanding**. Previous findings concerning missing provenance slots, unsupported numerical specificity and the dropped BESS qualifier are fixed.
> 
> **Verdict: accept** — the bounded skeleton acceptance criteria are demonstrated and all previous findings are resolved; the sandbox-limited suite run does not establish a regression.
**Verdict: accept.** Accepted; task done.
