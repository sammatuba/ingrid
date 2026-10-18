# Submission evidence checklist

Status: release checklist, updated 2026-10-17 at REL-4 against the repository records; the Hosting
and #38 rows carry batch release 23 since 2026-10-18 (RELEASE-23 records, PROGRESS row 'Batch release 23' (2026-10-18); release 22 before it, RELEASE-22 records on task/POLISH-2, POLISH-2 item 10). Never
mark a row complete without an artifact/receipt and reviewer. Treat every unspecified value as
unknown. The machine-readable release facts are in [release-manifest.json](release-manifest.json);
every null there is named with its owner in its `pending_receipts`.

| Gate | Required artifact | Owner role | State |
|---|---|---|---|
| Eligibility | Roster, registration receipt, eligibility attestation | Product owner | Open. Registration confirmed in session 2026-10-11 (GATE-1); the portal receipt is REL-7 and eligibility is not attested ([requirements](requirements.md) E1, E2) |
| Freshness / IP | Commit and original-asset log; rights review | Product owner | [Provenance log](provenance-log.md) from REL-1 (designated accept), regenerated at REL-5 from the frozen revision; rights review open (GATE-5, E11) |
| Data clearance | Permitted source/derived-output/publication manifest | Data owner | The company WESM copy is signed, version 2, for public display on the deployed demo, in the video and in the deck with a source line ([permission record](../../work/permissions/2026-10-13-wesm-company-copy.md)); the public data manifest is REL-5 after GATE-5 |
| Core workflow | Source -> review -> saved outlook, with no-change and refusal paths | App lead | Live on the PEDC event page ([GRID-3](../../work/reviews/GRID-3.md); the deployed read-back in [grid-desk event](../../work/grid-desk/event.md): a judge retained 83.7 MW and the history shows it). The stranger walkthrough is deferred by the owner 2026-10-17 (HOST-3) |
| Google AI | Actual model receipt, prompt/task revision, output and checks | AI lead | [CORE-6](../../work/reviews/CORE-6.md) synthetic cited receipt, designated accept; the real-case run of 2026-10-14, two Vertex AI calls with receipts ([record](../../work/grid-desk/live-run-2026-10-14.md)) |
| Models | Reproducible numerical/S1 evaluations and task limitations | Modeling lead | [EVAL-3 ablation report](../../work/probe-bundle/evaluation.md): A1 to A3 over 25 pairs / 28 compiles, label `synthetic_fixture`, scripted backend, `tuned: false`; the manual baseline is a protocol only (EVAL-6; EVAL-7 cut) |
| Security | Denied-access, injection, stale-head and sandbox tests | Reviewer | Offline core rows in the [H0 packet](../../work/h0-review-case/implementation.md) and the [H1 self-review](../../work/h1-api-persistence/review.md); API denial, revocation, actor-field and conflict tests in the [CORE-2 packet](../../work/probe-bundle/implementation.md); judge sandbox isolation in [PERF-2](../../work/reviews/PERF-2.md) |
| Hosting | URL, service/revision, image digest, cold-start and anonymous test | App lead | `https://ingrid-desk.web.app`, batch release 27 from main `5b7147db`: Cloud Run revision `grid-nowcast-00049-78l`, platform digest `sha256:f9c0bafc15a313929abad1454917716b8fee4ff0060ee5d84cd6031872409844` (full form from the release 27 deploy log, `.local/wt/INTEG-PP/.local-deploy27.log`, on the owner's machine, ignored path, 2026-10-19; REL-5 re-reads it with `gcloud run revisions describe grid-nowcast-00047-lnt --region asia-southeast1 --format='value(status.imageDigest)'`), live build stamp `10c1942669d71a9b` on Hosting, the first screen and Cloud Run `/health`, rollback `bash scripts/deploy/deploy.sh --rollback grid-nowcast-00046-vl5` ([HOST-2](../../work/reviews/HOST-2.md), [HOST-5](../../work/reviews/HOST-5.md), [batch release log](../../work/PROGRESS.md) row 'Batch release 25' (2026-10-19); release 22, `grid-nowcast-00044-fpr`, before it); the first screen is the sign-in screen; the judges' account is named in the submission form (REL-7); cold start measured in the [baseline](../../work/performance/baseline.md); the first screen is served from Hosting ([PERF-5](../../work/reviews/PERF-5.md)); sessions hold no credentials ([PERF-2](../../work/reviews/PERF-2.md)) |
| Public source | Approved allowlist and history review; working clean install | Release owner | Allowlist reviewed 2026-10-11 and history audited by REL-1; the export's clean-install command runs inside the release-audit tests. Publication is REL-5 behind GATE-5 (E7) |
| Story | Final deck PDF, English copy, matched implemented claims | Product owner | [Deck](deck.md) accepted at REL-2; slide 1 aligned to the theory-first framing at REL-4; the PDF is built from the frozen revision by [Appendix C](deck.md#appendix-c-pdf-build-steps) steps, at REL-5/REL-7 |
| Video | Public link, measured duration, transcript, visible modes | Demo owner | Shot list and narration supplied ([REL-3](../../work/reviews/REL-3.md), 168 s plan under E8's 180 s); recording and the measured duration are REL-6 (owner) |
| Final submission | Portal category, uploaded artifacts and receipt | Product owner | REL-7 (owner). E10: submit by October 18, 2026; the portal clock and time zone are not confirmed (#47) |

## GitHub milestone issues #37 to #47

Reconciled 2026-10-17 by REL-4 against the repository records, as the task note asks. Closing
an issue on GitHub is an outward action; this task does not perform it, and the dispositions
below are the evidence for the orchestrator or the owner to close with. Issue bodies were read
read-only with `gh issue view` (the task record quotes the commands).

| Issue | Title | Disposition | Evidence |
|---|---|---|---|
| #37 | Confirm authorized project, IAM, region, quota and spend bounds | Recorded; ready to close | GATE-3 row ([PROGRESS](../../work/PROGRESS.md)); deploy with IAM and spend-limit evidence in [HOST-2](../../work/reviews/HOST-2.md) |
| #38 | Deploy bounded Cloud Run, Firebase and Firestore demonstration | Satisfied; ready to close | Live at `https://ingrid-desk.web.app`, batch release 27: revision `grid-nowcast-00049-78l`, platform digest `sha256:f9c0bafc15a313929abad1454917716b8fee4ff0060ee5d84cd6031872409844` (full form from the release 27 deploy log, `.local/wt/INTEG-PP/.local-deploy27.log`, on the owner's machine, ignored path, 2026-10-19; REL-5 re-reads it with `gcloud run revisions describe grid-nowcast-00047-lnt --region asia-southeast1 --format='value(status.imageDigest)'`), live build stamp `10c1942669d71a9b`, rollback `bash scripts/deploy/deploy.sh --rollback grid-nowcast-00046-vl5` ([status](../../status.md), [batch release log](../../work/PROGRESS.md) row 'Batch release 25' (2026-10-19)); [HOST-2](../../work/reviews/HOST-2.md) accept |
| #39 | Verify judge sandbox isolation, clean install and rollback | Partly recorded; stays open | Isolation ([PERF-2](../../work/reviews/PERF-2.md)) and the recorded rollback command ([session report](../../work/session-report-2026-10-16.md)); the clean install of the published export is REL-5 |
| #40 | Run unfamiliar-user end-to-end walkthrough and fix material defects | Stays open | HOST-3 is deferred by the owner 2026-10-17 ([milestones](../../work/milestones.md), M5 row) |
| #41 | Diagnose GitHub Actions startup failure and restore hosted gates | Stays open | CI does not start ([status](../../status.md), [realignment](../../work/realignment-2026-10-14.md)) |
| #42 | [Epic] M6 — Freeze and submission evidence | Stays open | REL-4 is this pass; the freeze (REL-5), video (REL-6) and portal receipt (REL-7) are open |
| #43 | Confirm public artifact rights, allowlist and source audit | Partly recorded; stays open | Allowlist and history audit from REL-1; rights approval is GATE-5, open |
| #44 | Freeze release and collect final verification receipts | Partly recorded; stays open | This manifest and checklist are the receipt groundwork; the freeze itself is REL-5 |
| #45 | Produce submission PDF with truthful demonstrated claims | Stays open | No PDF exists; the build steps are [deck Appendix C](deck.md#appendix-c-pdf-build-steps) |
| #46 | Produce video under 180 seconds from verified workflow | Stays open | The plan is the shot list (REL-3); the recording is REL-6 (owner) |
| #47 | Confirm closing clock, eligibility and submission receipt | Stays open | E10 (submit by October 18, 2026) with the clock unconfirmed, and E1 unattested ([requirements](requirements.md)) |

## Public release allowlist

Release only reviewed fresh application code, safe test fixtures, essential run instructions,
dependency/licenses inventory, and permitted demonstration records. Exclude private series,
derived results without clearance, internal source locations, credentials, research downloads,
personal contact information, unreviewed archive material and historical unrelated projects.

Inspect the Git history and every file included in the public endpoint, not just current .gitignore.
A screenshot, a model response and a derived aggregate can disclose data too. Synthetic fixtures
must be clearly marked and must not masquerade as a real operator statement or real model run.

## Final handover

Capture deployed URL, source commit, released source location, PDF hash, video URL/duration,
model versions, fixture/real-case IDs, test report, release reviewer and submission receipt.
[release-manifest.json](release-manifest.json) holds every one of those facts that exists today,
with its source record named beside it, and names each remaining null and its owner in
`pending_receipts`; `release-manifest.template.json` is the empty starting shape.
