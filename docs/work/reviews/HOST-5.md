
## Designated review 1 (GPT Sol, independent, commit `bdb227f`, 2026-10-14)

> Independent review of `bdb227fb941aca0b25bc1d946ab8f891bd1efc2b` against `feat/h1-api-persistence`; inspected all three commits and the full diff. No files edited.
> 
> Executed verification:
> 
> - `/usr/bin/python3 -m unittest tests.test_hosted_config -v` — 103 tests, OK, 7 skipped.
> - `/usr/bin/python3 scripts/plan.py scope HOST-5 feat/h1-api-persistence` — OK.
> - `/usr/bin/python3 -m unittest discover -s tests` — 741 tests, OK, 18 skipped.
> - `plan.py check` — OK; `repo.py check` — PASS.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | All acceptance demonstrated | **No.** Full-reference success and different-digest refusal pass. Ready wait and platform resolution are unchanged and their tests pass. Additional stub runs reject empty values and empty suffixes, but accept references containing tabs or newlines and proceed to traffic update. |
> | 2 | Changes within allowed paths | **Yes.** Scope printed OK; only deployment script, hosted tests, and digest packet changed. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** No frozen contracts or acceptance text changed; no tests weakened or skipped by this diff. |
> | 4 | No unauthorized dependencies or effects | **Yes.** No added dependency, service, credential, network call or cloud effect. Review runs used offline stubs. |
> | 5 | Truthful mode labels | **Yes.** Tests identify synthetic/stub inputs; packet distinguishes historical live evidence from offline verification. |
> | 6 | Unknowns remain unknown | **Yes.** No invented case facts, receipts or numerical results introduced. |
> | 7 | Complete execution packet | **No.** Packet records interpreter, commands and historical results, but lacks explicit unfinished items and next action; task and progress still say `pending`. |
> | 8 | Consistent with product/domain invariants | **Yes.** Digest-only comparison preserves content identity without changing domain contracts. Malformed-input failure is recorded below. |
> 
> Findings, all unresolved:
> 
> - **important | scripts/deploy/deploy.sh:216 |** Validation rejects literal spaces but permits tabs and newlines in the image name, allowing malformed references to authorize traffic updates. **Evidence:** stub releases with `example.invalid/bad\timage@sha256:synthetic-platform-digest` and the newline equivalent both exited 0 and recorded `services update-traffic`. **Correction:** reject all whitespace/control characters in the image-name portion and add refusal tests asserting no traffic update.
> - **minor | docs/work/hosting/digest-ref.md:17 |** Handoff is incomplete: verification is attributed to an earlier PR head, and unfinished items/next action are absent. **Evidence:** packet ends with a reviewer note; `tasks.json:2056` and `PROGRESS.md:91` retain HOST-5 as pending. **Correction:** record verification for the task branch, unresolved findings and exact next action; synchronize task/progress state when requesting re-review.
> 
> **Verdict: rework.** Malformed references can pass verification and trigger traffic updates, so the required malformed-input acceptance item is not met.
**Verdict: rework.** deploy.sh: reject any whitespace/control character in the image name before @, with refusal tests asserting no update-traffic (tab, newline); packet: verification on the task branch, findings, next action Address every blocking/important row above; dispose of minors explicitly.

## Designated review 2 (GPT Sol, independent, commit `a2243ec`, 2026-10-14)

> Independent review of `a2243ec8e1a5c05470427170c61baf24d98b1c4e` against `feat/h1-api-persistence`; inspected the full diff and all five commits. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **No.** Full-reference success, different-digest refusal, missing-value refusal, platform resolution and Ready tests passed. Additional stub runs accepted malformed image names and updated traffic. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside HOST-5 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff changes six allowed files; no frozen contract or acceptance text changed, and no tests weakened or newly skipped. |
> | 4 | No unauthorized dependencies or effects | **Yes.** No new dependencies or external operations introduced. Review execution used offline stubs. |
> | 5 | Truthful mode labels | **Yes.** Tests label synthetic inputs; packet separates offline verification from historical live evidence and pending live proof. |
> | 6 | Unknowns stayed unknown | **Yes.** No invented case facts, receipts or results introduced. Live proof remains explicitly unfinished. |
> | 7 | Complete execution packet | **Yes.** `digest-ref.md` records interpreter, commands, results, finding dispositions, unfinished live proof and next review action; task/progress states agree. |
> | 8 | Consistent with product/domain invariants | **Yes.** Digest comparison preserves content identity; domain contracts and evidence distinctions are unchanged. Input-validation failure is listed below. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_hosted_config -v` — **105 tests, OK (skipped=7)**.
> - `/usr/bin/python3 scripts/plan.py scope HOST-5 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **743 tests, OK (skipped=18)**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 59 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> Finding:
> 
> **important | scripts/deploy/deploy.sh:219 |** Image-name validation accepts malformed repository paths whenever the digest suffix matches. **Evidence:** additional runs through `DeployScriptTests`’ existing release stubs with `/@sha256:synthetic-platform-digest` and `example.invalid//image@sha256:synthetic-platform-digest` both exited **0**, recorded `services update-traffic`, and recorded `deploy --only hosting`. Neither name is a valid image repository path. **Correction:** validate image-reference name syntax before accepting its digest, including rejecting empty path components; add regression tests asserting refusal before traffic and Hosting release. **Disposition:** unresolved.
> 
> **Verdict: rework.** Malformed references still authorize release actions, so the required malformed-value acceptance item is unmet.
**Verdict: rework.** Stop pattern-matching malformed names: when status.imageDigest carries a name before @, require it to equal $REMOTE_IMAGE exactly (the repository this run pushed, deploy.sh:88), else refuse before traffic and Hosting; keep the bare-digest form; tests: the reviewer's '/@…' and '//image@…', another repository with the same digest, plus the existing tab/newline/space cases, all refused with no update-traffic and no deploy --only hosting; the stub's full reference uses REMOTE_IMAGE Address every blocking/important row above; dispose of minors explicitly.

## Designated review (GPT Sol, independent, commit `6df2846`, 2026-10-14)

> Independent review of `6df2846aa671` against `feat/h1-api-persistence`, including the eight commits, full diff and clean working tree. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Every acceptance item demonstrated | **Yes.** Executed tests demonstrate full-reference success, different-digest refusal, malformed/missing-value refusal, platform resolution and Ready waiting. Additional stub runs confirmed bare-digest success and refusal of the correct repository with a different digest, empty suffix or duplicate `@`, before traffic and Hosting. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside HOST-5 allowed paths`; seven files changed. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** No frozen contract or acceptance text changed; no tests weakened, deleted or newly skipped. |
> | 4 | No unauthorized dependencies or effects | **Yes.** No new dependency, service, credential or external operation introduced. Verification used offline stubs. |
> | 5 | Truthful mode labels | **Yes.** Tests identify synthetic inputs; packet distinguishes offline verification, historical live evidence and pending live proof. |
> | 6 | Unknowns stayed unknown | **Yes.** No invented case facts or receipts introduced; deployed behavior remains explicitly unverified. |
> | 7 | Complete execution packet | **Yes.** `digest-ref.md` records interpreter, commands, results, prior finding dispositions, unfinished live proof and exact next action. Task/progress states agree. |
> | 8 | Consistent with product/domain invariants | **Yes.** The change preserves image identity and release checks without changing domain contracts, evidence distinctions or authorization boundaries. |
> 
> Executed checks:
> 
> - `/usr/bin/python3 -m unittest tests.test_hosted_config -v` — **106 tests, OK (skipped=7)**.
> - `/usr/bin/python3 scripts/plan.py scope HOST-5 feat/h1-api-persistence` — **OK**.
> - `/usr/bin/python3 -m unittest discover -s tests` — **744 tests, OK (skipped=18)**.
> - `/usr/bin/python3 scripts/plan.py check` — **OK: 59 tasks, 7 gates**.
> - `/usr/bin/python3 scripts/repo.py check` — **PASS**.
> 
> Findings: **None unresolved.** Prior malformed-reference and packet findings are resolved.
> 
> **Verdict: accept.** All required acceptance items were demonstrated by executed offline checks, with no blocking or important findings; live deployment proof remains pending.
**Verdict: accept.** independent accept; live proof at the next deploy
