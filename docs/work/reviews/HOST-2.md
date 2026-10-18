# HOST-2 review record

## Orchestrator findings from the first live deploy (2026-10-13, orchestrator seat, not a designated review)

Evidence: `docs/work/hosting/implementation.md`, "Orchestrator live evidence, first deploy". Address both rows, keep every
existing test green, and do not run any cloud command (the orchestrator re-runs the live steps).

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/deploy/cleanup.py` (`identity_state`) and its fake Auth client in `tests/test_hosted_config.py` | A real Firebase anonymous user has an empty `provider_data`; the rule requires `['anonymous']`, so every real judge session is kept as "not anonymous" and the command can never delete one. The fake client encodes the wrong shape, so the tests pass | Admin SDK on the two real judge users: `provider_id='firebase'`, `provider_data=[]`, no email; dry run kept both as "not anonymous (kept): 2" | Anonymous = no provider entries and no email and no phone number; anything else stays `unexpected`. Make the fake return the real shape (empty `provider_data`) and add a test that a user with a password provider or an email is kept |
| important | `scripts/deploy/deploy.sh` | After `--rollback`, Cloud Run traffic stays pinned to the old revision, so the next release deploys a revision that receives no traffic, silently | Live: after the rollback to `grid-nowcast-00001-ht2`, traffic remained pinned until the orchestrator ran `update-traffic --to-latest` | After `gcloud run deploy`, route 100% to the revision just deployed (`update-traffic --to-revisions <new>=100` or `--to-latest`), print the resulting traffic, and fail if the served revision is not the deployed one; cover it in the dry-run test |

## Orchestrator finding from the live re-run (2026-10-14, orchestrator seat, not a designated review)

Cleanup is fixed (2 sessions and 2 anonymous users deleted live). The rollback-traffic fix exposed a race:

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/deploy/deploy.sh` (step 5 and the traffic routing) | The script takes the revision to route from `status.latestReadyRevisionName` right after `gcloud run deploy`. With traffic pinned, the new revision is not yet the latest *ready* one at that moment, so the script routes 100% to the **previous** revision and reports success while serving old code | Live: new revision `grid-nowcast-00003-7m9` (new image) created; script routed to `grid-nowcast-00002-wtk` (old image); `implementation.md`, "Deploy after a rollback" | Take the revision this deploy created (`gcloud run deploy ... --format 'value(status.latestCreatedRevisionName)'` or describe `latestCreatedRevisionName`), wait until that revision is Ready, check that its image digest is the digest just pushed, then route 100% to it and fail loudly on any mismatch. Cover the selection in the dry-run test |

## Designated review 1 (GPT Sol, independent, commit `a0bd05b`, 2026-10-14)

> Reviewed independently: `a0bd05b98cd20f3c0e48114738af02f98441558a`, using `git diff feat/h1-api-persistence...HEAD` and `git log feat/h1-api-persistence..HEAD`. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Hosting session isolation and private-response `no-store` remain outstanding ([implementation.md:192](../hosting/implementation.md)). Direct Cloud Run checks cannot satisfy them. Rollback and successful cleanup have recorded live evidence. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside HOST-2 allowed paths`. |
> | 3 | Frozen contracts and acceptance unchanged; tests not weakened | **Yes.** Nine changed files; no frozen-contract edits or acceptance changes. Test diff adds coverage; existing dependency skips are unchanged. |
> | 4 | No additions beyond packet’s dependencies/services/effects | **Yes.** Scripts use the intent’s named Docker, Artifact Registry, Cloud Run, Firebase Hosting/Auth and Firestore tooling; no dependency files changed. |
> | 5 | Truthful mode labels | **Yes.** Tests identify synthetic stubs; the packet distinguishes offline execution from orchestrator live runs and explicitly identifies the judge checks as direct Cloud Run checks. |
> | 6 | Unknowns preserved; no invented facts or receipts | **Yes.** Cleanup retains unknown-age and unreadable-identity sessions; pending Hosting checks are explicitly outstanding. No invented case facts found. |
> | 7 | Interpreter, commands, results, unfinished work and next action recorded | **Yes.** Implementation packet includes verification tables, self-review notes, pending Hosting checks and the required release rerun. |
> | 8 | Consistent with product direction and domain invariants | **Yes.** No product or method contract changes; demo/private namespaces remain distinct and judgments/reviews retain their existing boundaries. |
> 
> Verification executed:
> 
> - `bash scripts/deploy/deploy.sh --dry-run`: **passed**.
> - `gcloud run services describe grid-nowcast --region asia-southeast1`: **attempted, failed** before contacting the service because the sandbox makes gcloud’s credential database read-only.
> - `/usr/bin/python3 scripts/plan.py scope HOST-2 feat/h1-api-persistence`: **OK**.
> - Repository check: **PASS**; plan check: **OK**, 49 tasks, 7 gates.
> - Full offline suite: **574 tests, OK, 7 existing skips**.
> - Hosted configuration module: **85 tests, OK, 7 existing skips**.
> - Additional venv run stalled during HTTP tests and was interrupted; no passing result claimed.
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | blocking | `docs/work/hosting/implementation.md:192` | Two required acceptance checks have no demonstrated result through Firebase Hosting. | Packet explicitly says the two-session checks ran against Cloud Run; final rework section still leaves Hosting session isolation and private-response caching pending. | Run both checks through `https://grid-nowcast.web.app`, recording two isolated sessions, saved reviews, cross-session/private denials and authenticated private-response `Cache-Control: no-store`. |
> | important | `scripts/deploy/cleanup.py:202` | Membership deletion precedes Auth deletion. If Auth deletion fails, the surviving user loses its discovery record and subsequent cleanup cannot retry it. | Executed an injected Auth-deletion failure: case and membership deletion occurred, Auth user remained, one failure was recorded. `iter_memberships` discovers only surviving membership documents. Existing failure coverage tests case deletion failing first. | Preserve the membership until case and Auth cleanup finish, treating an already-absent user idempotently; add a failure-and-retry test proving the next run removes the surviving user. |
> 
> **Verdict: rework.** Required Hosting acceptance evidence is missing, and cleanup can permanently strand anonymous Auth users after a transient deletion failure.
**Verdict: rework.** Yours: the cleanup ordering. Keep the membership until the case and the anonymous Auth user are both gone, treat an already-absent user as done, and add a failure-then-retry test proving a later run finishes the job. The blocking Hosting-URL evidence is the orchestrator's: this machine's network cannot reach Firebase Hosting, so the orchestrator runs the two-session and no-store checks from Google Cloud Build against https://grid-nowcast.web.app and records them in docs/work/hosting/implementation.md. Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `f13f21a`, 2026-10-14)

> Independent review of `f13f21a`, using the diff and commit log against `feat/h1-api-persistence`. No files edited.
> 
> | # | Answer | Evidence |
> |---|---|---|
> | 1. All acceptance checks demonstrated | **Yes** | [Hosting evidence](../../../docs/work/hosting/implementation.md) records 24/24 checks: two anonymous sessions, saved dispositions, cross-session/private-case 404s, and authenticated `no-store`. Line 657 records session-response `no-store`. Lines 232–233 demonstrate rollback; lines 357–377 record live cleanup of two cases, memberships and anonymous users. |
> | 2. Changes inside allowed paths | **Yes** | Requested scope command printed `OK: all changed files inside HOST-2 allowed paths`; working tree clean. |
> | 3. Contracts and acceptance unchanged; tests preserved | **Yes** | Diff changes deployment tooling, tests and coordination records; no frozen-contract or acceptance edits. Existing tests were not removed or weakened. |
> | 4. No effects beyond the packet | **Yes** | Firebase Hosting/Auth, Firestore, Artifact Registry and Cloud Run are named in the hosting packet. Recorded cloud checks are attributed to the orchestrator; no new runtime dependency. |
> | 5. Truthful mode labels | **Yes** | Stubbed release tests explicitly use synthetic values; packet distinguishes offline tests, live hosted checks and executor self-review. |
> | 6. Unknowns preserved | **Yes** | Cleanup retains unknown-age sessions and unreadable identities; tests exercise both. Health remains `storage_checked: False`. |
> | 7. Complete verification and handoff record | **Yes** | Packet records interpreter, exact commands/results, prior failures, rework and next actions; later Hosting evidence resolves the earlier outstanding checks. |
> | 8. Domain and product fidelity | **Yes** | Judge/private namespaces remain distinct; authorization, record contracts and model semantics are unchanged. Budget alerts are correctly distinguished from caps. |
> 
> Verification run:
> 
> - `bash scripts/deploy/deploy.sh --dry-run`: **passed**.
> - `gcloud run services describe grid-nowcast --region asia-southeast1`: **attempted; failed** because the sandbox makes gcloud’s credential database read-only. No live service result claimed.
> - `/usr/bin/python3 scripts/plan.py scope HOST-2 feat/h1-api-persistence`: **OK**.
> - Repository check: **PASS**; plan check: **OK — 49 tasks, 7 gates**.
> - Full offline suite: **576 tests, OK, 7 skips**.
> 
> Findings: **None unresolved.** The previous cleanup failure is corrected: membership deletion occurs last, and the failure-and-retry test proves a subsequent run can finish cleanup. Live acceptance conclusions rely on the recorded orchestrator evidence.
> 
> **Verdict: accept.** All four acceptance items have recorded executed evidence, scope and offline checks pass, and the prior blocking and important findings are resolved.
**Verdict: accept.** Hosting-URL evidence by the orchestrator from Cloud Build (24/24 and session no-store).
