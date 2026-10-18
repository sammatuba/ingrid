# Review: HOST-0

Reviewed commit `39c941d` against `feat/h1-api-persistence` on 2026-10-11. Independent: GPT Astra
(`gpt-6-astra`) via `codex exec -s read-only` (`scripts/seats/reviewer.sh`); author was the executor seat
(DeepSeek V4.1 Flash). Orchestrator checks before review: scope OK, `plan.py check` OK,
`repo.py check` PASS, full offline suite OK outside the sandbox. The reviewer's own full-suite run
hits read-only-sandbox temp-dir errors; that is an environment limit, not a finding.

## Reviewer output

> Independent review of `39c941d6a172` against `feat/h1-api-persistence`: one commit, four documentation/coordination files changed. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance items demonstrated | **No.** Diff inspection shows no added credential, and `src/demo/__init__.py:21–29` confirms fixture labels. The anonymous endpoint is specified, but its browser entry and case authorization remain incomplete, as detailed below. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside HOST-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance text and tests unchanged | **Yes.** The diff changes only hosting documents, HOST-0 state and its progress entry. |
> | 4 | No unplanned dependency or external effect | **Yes.** Documentation-only change; proposed services are named in the packet. No runtime dependency or service call added. |
> | 5 | Truthful mode labels | **Yes.** Intent distinguishes synthetic fixtures from future hosted evidence; lines 295–301 explicitly disclaim runtime completion. |
> | 6 | Unknowns remain unknown | **Yes.** Region, provisioning, retention and reset cadence remain open; no hosted measurements or receipts claimed. |
> | 7 | Complete verification and handoff record | **Yes.** Lines 260–301 record open items, next action, Python 3.14.4 and author-run commands/results. The author's passing suite was **not independently reproduced**. |
> | 8 | Consistent with governing direction and invariants | **Yes, at the stated policy level.** Synthetic labeling, private-case denial, human review and deployment gates are preserved. Execution gaps below prevent readiness acceptance. |
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 scripts/plan.py scope HOST-0 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 41 tasks, 7 gates**.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests` — **251 tests, 30 errors**; reported errors arise from unavailable writable temporary directories in this sandbox.
> - `git diff --check feat/h1-api-persistence...HEAD` — passed.
> 
> All findings remain open.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/hosting/intent.md:126` | The promised password-free browser walkthrough has no defined browser entry. | Unchanged `src/workspace/app.js:139–142` requires email/password and calls `/session`; it never calls `/demo/session`. The intent defers that integration as optional. | Make browser session creation a required, assigned dependency, or specify a complete compatible entry mechanism and its browser acceptance check. |
> | important | `docs/work/hosting/intent.md:118` | Anonymous Firebase scope alone cannot authorize the shared seeded case. | `create_app` resolves stored membership (`src/api/__init__.py:172–173`). The seed permits only its seeding actor (`src/demo/__init__.py:21`), enforced by `src/review/repository.py:89`. No anonymous UID-to-membership-and-case policy is specified. | Define the identity, membership and case authorization mapping without bypassing existing checks; require successful reads/reviews for two distinct anonymous sessions and private-case denial. |
> | important | `docs/work/hosting/intent.md:40` | Promised unchanged adapter reuse cannot construct the specified hosted configuration. | Both adapter constructors invoke `local_configuration`, which rejects hosted mode. `FirestoreStore` additionally requires `synthetic-*` namespaces and defaults to `AnonymousCredentials` (`src/adapters/firestore/__init__.py:21–25`). | Specify hosted adapter construction within owned paths, including ADC, verified identity and namespace routing; distinguish reusable transaction logic from emulator-only initialization. |
> 
> **Verdict: rework.** HOST-0’s delivered intent needs these integration decisions before it can serve as an executable hosting handoff.
## Outcome and next action

**Verdict: rework.**
Executor revises the hosting intent: browser demo-session entry, anonymous identity to membership and case policy, hosted adapter construction; then re-review.

## Review round 2026-10-11 evening (commit `6eb84ce`, independent, GPT Astra via `codex exec -s read-only`)

> Independent review of `6eb84ceaec9e` against `feat/h1-api-persistence`, covering commits `39c941d`, `306d47f`, and `6eb84ce`. Five files changed; working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes, at HOST-0’s intent scope.** Diff inspection found no added credential; `src/demo/__init__.py:21–29` confirms synthetic labels. Intent lines 128–184 define anonymous identity, membership, case access and browser entry. Container and hosted behavior remain unverified. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside HOST-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance text and tests unchanged | **No.** Frozen contracts and tests are unchanged, but `docs/work/tasks.json:743` adds UI-5 acceptance text. HOST-0 acceptance is unchanged; the supplied rework note acknowledges the UI-5 extension. |
> | 4 | No dependency or external effect beyond packet | **Yes.** Documentation/coordination changes only; proposed services are named. No runtime dependency or cloud operation added. |
> | 5 | Truthful mode labels | **Yes.** Intent lines 404–409 distinguish intent definitions from unbuilt container and hosted behavior. |
> | 6 | Unknowns remain unknown | **Yes.** Intent lines 373–376 retain provisioning, region, retention and reset cadence as open inputs; no hosted measurements claimed. |
> | 7 | Verification and handoff recorded | **Yes.** Intent’s rework verification section records Python 3.14.4, commands/results and next actions; `work.json` requests re-review. Author’s passing suite was not independently reproduced. |
> | 8 | Consistent with governing direction and invariants | **No.** Global judge reset contradicts the architecture’s session-local reset requirement; see finding below. |
> 
> Executed with Python 3.14.4:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> - `/usr/bin/python3 scripts/plan.py scope HOST-0 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 42 tasks, 7 gates**.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests` — **251 tests, 30 errors**, caused by unavailable writable temporary directories in this sandbox.
> - `git diff --check feat/h1-api-persistence...HEAD` — **failed**, trailing whitespace in the prior review record.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `docs/work/hosting/intent.md:268` | One judge’s reset destroys every other judge’s case, membership and token. | Lines 268–272 explicitly discard every session; line 311 exposes this through `/demo/reset`. `docs/architecture/decision-system-v1.md:157` requires session-local reset and prohibits writes outside the scoped session. | Bind HTTP reset to a verified session and reset only its state. Keep global reset operator-only; require a two-session check proving the other session’s token, history and work survive. |
> | minor | `docs/work/hosting/intent.md:414` | The rework audit inaccurately claims no acceptance text changed. | `docs/work/tasks.json:743` adds UI-5 acceptance text, also acknowledged by intent line 432. | State explicitly that HOST-0 acceptance stayed unchanged while UI-5 acceptance was extended. |
> 
> Both findings remain open. The prior review’s browser-entry, membership/case and adapter-construction omissions are addressed as intent definitions.
> 
> **Verdict: rework.** The reset contract must preserve session isolation before this intent is ready for implementation.
**Verdict: rework.** Executor rework next session: demo reset must be per-session, not global.

Orchestrator note (2026-10-11): this branch's executor also added task UI-6 to `tasks.json`
and edited UI-5's `depends_on`, `owned_paths` and acceptance text. Executors may change only
their own task state; acceptance text is never edited by a worker. The proposal answers
review finding 1 and may be right, but it is not adopted: next session the orchestrator either
re-applies it as an orchestrator plan change on the integration branch or the executor
reverts it, before HOST-0 can be accepted.

## Orchestrator disposition (2026-10-12)

The UI-6 plan edit is **adopted** as an orchestrator plan change with the owner's approval
(PROGRESS 2026-10-12): no revert. Rework scope is therefore only the demo-reset finding
(reset must be scoped to one judge's session, never to all users). Do not edit `tasks.json`
beyond this task's own state.

## Rework 2 (2026-10-12, executor agent, review verdict rework)

Executor record for the second rework, on top of `aae64c0`/`5e3627a` on `task/HOST-0`. Findings
addressed: the important demo-reset finding and the minor audit-wording finding from the
2026-10-11 evening review above; the orchestrator disposition of 2026-10-12 adopted UI-6 and
scoped this rework to the reset.

### What changed

- `docs/work/hosting/intent.md` — Reset policy rewritten: `POST /demo/reset` requires the
  caller's session token (the unchanged `create_app` verification path) and resets only that
  session — its case contents are discarded and the same case id is re-seeded for the same uid
  and stored membership, only its own tokens rotate (pre-reset tokens are 401), and the
  response returns a fresh token in the `POST /demo/session` shape. Global resets are
  operator-only: process restart in demo mode, and the HOST-2 command in `scripts/deploy/`
  under Admin credentials (never a browser or judge token, demo namespace only). Hosted mode
  keeps 404 on `/demo/reset`. The additive-surface row and the HOST-1 checks table now carry
  the session-local reset and the two-session isolation row the reviewer required (session B's
  token, case id, proposals, reviews and receipts survive A's reset and B still reads and
  saves). The denial rules add: reset without a valid session token is 401. The 2026-10-11
  rework audit no longer claims no acceptance text changed — corrected in place to HOST-0's
  acceptance staying unchanged while UI-5's was extended when UI-6 was added and adopted.
- `docs/work/hosting/work.json` — next action now points at re-review, then HOST-1.
- `docs/work/PROGRESS.md` — one log row (below the 2026-10-11 review row).
- No code, test, frozen contract or acceptance text changed; nothing outside the allowed
  paths. `docs/work/tasks.json` needed no edit: HOST-0's own state was already `in_progress`
  and stays so.

### Commands and results (rework-2 tree, `/usr/bin/python3` 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/repo.py check` | `Checked 252 Markdown files, 1122 local links, 8 skills; bootstrap 1293 words.` then `PASS` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests in 2.429s` — `OK` (final re-run on the finished tree) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/plan.py scope HOST-0 feat/h1-api-persistence` | `OK: all changed files inside HOST-0 allowed paths` |
| `git diff --check feat/h1-api-persistence...HEAD` | still flags trailing whitespace on the empty blockquote lines (`> `) of the reviewer's text above; left unedited because the reviewer's record is append-only for the executor — orchestrator action if wanted |

### Acceptance re-check

| Criterion | After rework 2 |
|---|---|
| No credential in Git; demo mode uses labelled fixtures | Unchanged and still met as a definition: this rework adds no credential and narrows, not widens, the reset surface |
| Anonymous judge access path defined | Met; the reset is now defined as part of the judge path's scope: session-bound, verified token, no cross-session effect |

No stop condition fired. State stays `in_progress`; only a reviewer sets `done`. Exact next
action: re-review this commit against the two findings of the 2026-10-11 evening round, then
dispatch HOST-1 (`plan.py brief HOST-1`) followed by UI-6; HOST-2 and HOST-3 wait for GATE-3.

## Interim review (orchestrator seat, Fable, commit f34d07d, 2026-10-12)

Interim review, not the designated independent reviewer (GPT Astra, no credits); a designated
re-review is required before `done`. Reviewed `f34d07d` against `feat/h1-api-persistence`
(commits `9c905ce`..`f34d07d`; five files, all documentation and coordination). Author: DeepSeek
executor seat. No file edited except this append. `docs/research` not read; no credential search.

| # | Checklist | Answer and evidence |
|---|---|---|
| 1 | Acceptance items demonstrated | **Yes, at intent scope.** No credential added (diff of all five files inspected); fixture labels are `src/demo/__init__.py:7-9,25-29` constants (`synthetic: True`, `Fictional advisory — not a real plant report.`, `availability_basis: 'Labeled local fixture'`). Anonymous judge path defined at `intent.md:130-187` (identity → membership → case → scope → denial → required checks → browser entry). |
| 2 | Only allowed paths changed | **Yes.** `plan.py scope HOST-0 feat/h1-api-persistence` → `OK: all changed files inside HOST-0 allowed paths`. |
| 3 | Frozen contracts, acceptance text, tests unchanged | **Contracts and tests yes; acceptance text changed.** `tasks.json:726-745` extends UI-5 `depends_on`, `read_first`, `outputs`, `acceptance`; UI-6 added at `:751-784`. Adopted as an orchestrator plan change with owner approval (PROGRESS 2026-10-12 row, disposition section above), so not a finding. HOST-0's own acceptance text is unchanged. |
| 4 | No dependency or external effect beyond the packet | **Yes.** Intent-only; `intent.md:89` adds no dependency; proposed services named and gated behind GATE-3. |
| 5 | Truthful mode labels | **Yes.** Runtime claims are placed in the HOST-1 checks table (`intent.md:358-374`) and the "Later evidence" column (`:353-356`); `:423-427` and `:95-96` state nothing was built, deployed or measured. Model calls stay disabled unless configured (`:62-63,72-76`). |
| 6 | Unknowns stayed unknown | **Yes.** Region, provisioning, retention, reset cadence, base-image digest, construction eagerness are open items (`:85-87,212-214,247-249,388-392`). |
| 7 | Packet records interpreter, commands, results, next action | **Yes.** Rework-2 section above and `intent.md:411-421,525-532`; `work.json.next_action` names re-review then HOST-1. |
| 8 | Consistent with blueprint and invariants (reset by construction) | **Yes.** Session identity is the uid carried by the verified token (`demo-<32 hex>` in demo, Firebase anonymous uid in hosted, `intent.md:137-144`); membership and case are per-uid (`:145-157`, `permitted_actors == [uid]`); `:281` "no request field selects a session, so a token can only ever reset its own"; no token → 401 (`:165-166, :325`); hosted `/demo/reset` → 404 (`:285-287`); global reset operator-only (`:271-272, :287-290`). Matches `decision-system-v1.md:157` ("no write capability outside its scoped session. Reset is session-local"). Two-session isolation is a required HOST-1 row (`:370`). |

Verification, this worktree, `/usr/bin/python3` 3.14.4:

| Command | Result |
|---|---|
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests in 3.148s` — `OK` (includes `test_progress_record_matches_task_states`) |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `Checked 252 Markdown files, 1122 local links, 8 skills; bootstrap 1293 words.` `PASS` |
| `/usr/bin/python3 scripts/plan.py scope HOST-0 feat/h1-api-persistence` | `OK: all changed files inside HOST-0 allowed paths` |
| `git diff --check feat/h1-api-persistence...HEAD` | trailing whitespace only, on `> ` blockquote lines of this record |

UI-6 definition: `depends_on [UI-4, HOST-1]` (route must exist first, matches intent S0/S1),
`owned_paths [src/workspace/]` (matches `intent.md:53-55`), acceptance names the control, the
no-credential disposition and the unchanged fictional/emulator paths; HOST-1 `owned_paths`
equal the five paths at `intent.md:40-41`. PROGRESS state table: UI-6 `pending`, HOST-0
`in_progress`, both equal to `tasks.json`.

| Severity | Path:line | Failure mechanism | Evidence | Correction |
|---|---|---|---|---|
| minor | `docs/work/hosting/intent.md:279-280` vs `:325` | Reset response shape stated two ways; HOST-1 could implement either. | `:279-280` "same shape as `POST /demo/session`"; `:325` adds `"reset": true`. | State once: session shape plus `reset: true`. |
| minor | `docs/work/hosting/intent.md:155-156` | "session id" is undefined; only the uid is defined, so the case-id derivation is ambiguous. | `:137-138` defines uid `demo-<32 hex>`; `:155-156` hashes "the session id". | Write "SHA-256 of the uid" or define the session id. |
| minor | `docs/work/tasks.json:776-781` (UI-6) | `verify` and acceptance require `docker run`; the executor seat can run only python3 and git, so UI-6 would stall in-seat. | UI-6 `verify`: `docker run --rm -p 18001:8080 grid-nowcast then manual check`. | Orchestrator plan edit: accept `uvicorn src.api.hosted:app --factory` in demo mode on 18001 as the equivalent server for UI-6's check. |
| minor | `docs/work/tasks.json:720-745` | UI-5 (M4) now depends on UI-6 → HOST-1 (M5): an M4 task gated on M5 work. | `depends_on [UI-4, UI-6]`; UI-6 `milestone M5`. | Adopted with owner approval; note it when ordering the UI lane, or move UI-5 to M5. |
| minor | `docs/work/reviews/HOST-0.md:12,23,25,…` | Trailing whitespace on empty blockquote lines fails `git diff --check`. | Output above. | Orchestrator strips `> ` → `>`; this seat is append-only. |
| minor | `docs/work/PROGRESS.md:118-123` | 2026-10-11 log rows appended below the 2026-10-12 owner-decisions row. | Diff of PROGRESS.md. | Cosmetic; reorder if the log is read chronologically. |

**Interim verdict: accept.** Both round-2 findings are fixed as the reviewer specified (session-bound reset, operator-only global reset, two-session isolation row, audit wording), and the remaining items are wording and plan hygiene; `done` still waits for the designated independent accept.

## Designated review (GPT Astra, independent, commit `465640f`, 2026-10-12)

> Independent review of `465640f6fb88be3619836e6a9bbf6e4b2fe7b3b4` against `feat/h1-api-persistence`, including the requested diff and commit log. Five documentation/coordination files changed. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes, at HOST-0’s intent scope.** Diff inspection found no added credential. `src/demo/__init__.py:21–29` confirms synthetic labels. Intent lines 130–187 define anonymous identity, stored membership, isolated case and browser entry. Container and hosted behavior remain unverified. |
> | 2 | Only allowed paths changed | **Yes.** Requested scope command printed `OK: all changed files inside HOST-0 allowed paths`. |
> | 3 | Frozen contracts, acceptance text and tests unchanged | **No.** UI-5 acceptance was extended and UI-6 added. The review record’s orchestrator disposition explicitly adopts this plan change with owner approval. HOST-0 acceptance, frozen contracts and tests are unchanged. |
> | 4 | No unplanned dependency or external effect | **Yes.** Documentation-only diff; proposed services are named in the packet and deployment remains gated. |
> | 5 | Truthful mode labels | **Yes.** Intent lines 351–356 separate present document checks from future runtime evidence; lines 423–427 explicitly disclaim building or deploying anything. |
> | 6 | Unknowns stayed unknown | **Yes.** Provisioning, region, retention and reset cadence remain open at intent lines 388–393; no hosted measurements or receipts invented. |
> | 7 | Verification and handoff recorded | **Yes.** Rework-2 record includes Python 3.14.4, commands/results and next action; `work.json` requests re-review then HOST-1. Author-reported suite success was not independently reproduced. |
> | 8 | Consistent with governing direction and invariants | **Yes, at intent scope.** Intent lines 269–294 now require session-local HTTP reset and operator-only global reset; lines 369–370 require reset isolation checks. Human review, fixture labels and private namespace boundaries remain explicit. |
> 
> Checks executed with Python 3.14.4:
> 
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**, 252 Markdown files, 1123 links.
> - `/usr/bin/python3 scripts/plan.py scope HOST-0 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 42 tasks, 7 gates**.
> - `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests` — **261 tests, 37 errors** caused by unavailable writable temporary directories. This is not a passing run.
> - `git diff --check feat/h1-api-persistence...HEAD` — **failed**, trailing whitespace in prior review quotations.
> 
> Findings below remain open; none is blocking or important.
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | minor | `docs/work/hosting/intent.md:280` | Reset response has two definitions, permitting inconsistent implementation. | “Same shape” as session response, while line 325 adds `reset: true`. | Specify session response fields plus `reset: true` consistently. |
> | minor | `docs/work/hosting/intent.md:156` | Case-ID derivation references an undefined identifier. | Hashes “session id”; lines 137–144 define only the uid. | Explicitly hash the uid, or define the session identifier. |
> | minor | `docs/work/reviews/HOST-0.md:12` | Quoted review formatting fails whitespace verification. | `git diff --check` reports twelve trailing-whitespace lines. | Remove trailing spaces from empty blockquote lines. |
> 
> **Verdict: accept.** HOST-0’s intent acceptance is demonstrated by document and source inspection, the previous material findings are resolved, and remaining findings are minor; this does not accept future container or hosted runtime behavior.
**Verdict: accept.** Intent accepted by document and source inspection; does not accept future container or hosted runtime behaviour.
