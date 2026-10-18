# AI Builder Cup 2026: verified requirements and release gates

Reviewed 2026-10-04; project state column updated 2026-10-14, row E5 on 2026-10-18. See
[primary-source register](../../research/28-research-grounding-2026-10-04.md), C1-C5.
Portal submission and participant eligibility are not verified until REL-7's receipt exists. Terms control over
promotional inconsistencies. Confirm the exact deadline clock/time zone in the portal.

| ID | Requirement | Evidence | Project state |
|---|---|---|---|
| E1 | 2-4 eligible JAPAC professionals, each 21+; no students | C3/C4 | Owner confirmation outstanding |
| E2 | Team/registration locked by October 11 | C1 | Registration confirmed by the owner 2026-10-11 (GATE-1 open); portal receipt at REL-7 |
| E3 | Fresh work in the official build window | C3/C4 | [Provenance log](provenance-log.md) from REL-1; regenerated at REL-5 |
| E4 | One theme; select Future of Work & Enterprise Productivity | C2/C3 | Portal selection unverified |
| E5 | Primarily Google Cloud; meaningful required Google AI | C2/C4 | Firebase Hosting, Cloud Run (asia-southeast1), Artifact Registry, Firestore, Firebase Authentication serve the site; Vertex AI Gemini ran once on the real case (2026-10-14, two calls at two cutoffs, [record](../../work/grid-desk/live-run-2026-10-14.md)) and once on the synthetic case (2026-10-11); BigQuery reads at build time and on the alerts page; Secret Manager and Cloud Scheduler are configured for the alerts check (no run record). One [services table](../../work/polish-2026-10-18/services-table.md) (updated 2026-10-18) |
| E6 | Working end-to-end deployed URL | C3/C4 | `https://ingrid-desk.web.app` ([release record](../../work/grid-desk/release-poc-2026-10-14.md), [HOST-2](../../work/reviews/HOST-2.md)) |
| E7 | Public GitHub source | C3/C4 | Current working repository private |
| E8 | Public video strictly under 180 seconds | C3/C4 | Shot list is REL-3, recording is REL-6; not done |
| E9 | English deck/PPT converted to PDF | C2 | [Deck](deck.md) accepted (REL-2); PDF export at REL-4 |
| E10 | Submit by October 18, 2026 | C1 | REL-7, owner; portal clock and time zone unknown |
| E11 | Rights to submitted code, assets, data and disclosures | C4 | Owner/legal/data review required |

## Publication is not a routine git push

A private review push is different from making a submission repository public. A public branch
is not a confidentiality boundary: changing repository visibility can expose history, other refs,
issues and attachments. Do not simply flip this repository public.

Audit all intended content and history. Keep one implementation source of truth. A source-only
public release export can be generated from reviewed paths after owner approval; it is not a
second maintained application. Do not publish any such export automatically. Its eligibility
and historical-code provenance still need review; a new repository date does not make old work new.

## Rights and terms review

The terms snapshot reviewed in this session includes a six-month right of first refusal for
exclusive licensing/acquisition of submitted materials, a 30-day organizer response period,
and broad promotional permissions. This is commercially significant; have the relevant owner
and qualified counsel review the exact current language before agreeing or submitting.

Use C4 as the controlling document. Record employer/code/data ownership, permitted publication,
model/service licenses, originality dates and the owner's acceptance of submission-related IP
conditions. Obtain appropriate legal review for business/IP consequences. Do not use a secrecy
expectation for anything included in the public demo, public source, deck or video.

## Ambiguities to resolve with the organizer

The themes page later lists an older category set, while its main list gives six current themes.
Record the actual portal category and organizer confirmation. Fresh-work wording coexists with
boilerplate about existing applications; follow the stricter fresh-work rule unless clarified.
Ask about permitted prior datasets and open-source dependencies, not just prior application code.

The supporting email draft is provided separately; it has not been sent.

## Retrieval consistency note

Public retrieval returned both an older early-registration homepage (1-4 people, dates not yet
announced) and a newer indexed homepage (2-4 people, dated October schedule). The newer main
page and the reviewed FAQ/terms informed this checklist. Some repeat direct fetches returned
cache misses. Treat portal receipts and the current controlling terms as the final authority;
confirm team size, deadline clock, selected category and IP terms at submission.
