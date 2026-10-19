# Public export provenance log

Generated 2026-10-19 by `scripts/release/export.py` as part of REL-1 (public export audit). This copy ships inside the export as `PROVENANCE.md`.

- Audited revision: `146a502a6fdaee478c816e159cc19bc5b8224a1e` (committed 2026-10-19), branch `integ/pp`
- Freshness cutoff: 2026-09-07 — the build-window start; first commits before it are excluded
- Allowlist: `scripts/release/allowlist.json`, reviewed 2026-10-19
- Decisions: 1684 tracked paths audited, 748 included, 936 excluded, 3 generated export files, 0 findings

## Method

Every path tracked at the audited revision receives one decision: an allowlist include rule,
or an exclusion with the rule and reason below. Included candidates are then checked against
the history cutoff and the content rules. First and last commit dates come from the repository
history (`git log --reverse --name-only`), never from inference, and content matches are
reported as rule and line only — matched values are never printed or copied into this log.
A second, blob-level history pass flags an included path whose current bytes were already
committed before the cutoff, so pre-cutoff content moved or copied unchanged into an included
tree after the cutoff is caught even though its path name is new.
Generated export files are content like any other: each is built from the audited revision,
scanned with the same rules and put through the same history gate before it is written, and
`README.md` is the clean-install template read at that revision rather than from the working
tree. The template is confined to `scripts/release/` and cannot be redirected to a pre-cutoff
or excluded file elsewhere. A content exception never exempts a path: it pins the sha256
digest of every reviewed match, so changed content stops the export.

Content rules applied (category: rule ids):

- secret: private-key-block, aws-access-key-id, google-api-key, github-token, slack-token, bearer-token, credential-assignment
- private-data: personal-email, ph-mobile-number
- internal-location: gcs-location, absolute-home-path, private-ipv4, private-repo-url, cloud-project-id

## Included content

| Rule | Paths |
|---|---|
| `licence` | 1 |
| `attribution` | 1 |
| `app-source` | 227 |
| `app-tests` | 276 |
| `repository-check-tool` | 1 |
| `dependency-inventory` | 1 |
| `container` | 1 |
| `container-ignore` | 1 |
| `deploy-lane` | 10 |
| `docs-build-scripts` | 4 |
| `ontology-scripts` | 4 |
| `outlook-scripts` | 4 |
| `price-scripts` | 4 |
| `book-scripts` | 3 |
| `probe-runner` | 1 |
| `eval-runner` | 1 |
| `corpus-excerpt` | 0 |
| `agent-entry` | 1 |
| `docs-entry` | 1 |
| `docs-status` | 1 |
| `docs-glossary` | 1 |
| `docs-index` | 1 |
| `docs-routes` | 1 |
| `docs-architecture` | 7 |
| `docs-product` | 12 |
| `docs-competition` | 11 |
| `docs-explainer` | 29 |
| `docs-engineering-people` | 1 |
| `docs-engineering-lifecycle` | 1 |
| `docs-engineering-review` | 1 |
| `case-pedc` | 8 |
| `case-first` | 1 |
| `review-records` | 107 |
| `permission-record` | 1 |
| `live-run-record` | 1 |
| `event-record` | 1 |
| `val-1` | 1 |
| `evidence-ledger` | 6 |
| `attribution-records` | 10 |
| `platform-lanes` | 1 |
| `meta-framing` | 1 |
| `systems-inventory` | 1 |
| `timesfm-note` | 1 |

## Excluded content

| Rule | Paths | Reason |
|---|---|---|
| `agent-config` | 5 | agent skills and repository lifecycle entry points |
| `agent-service-test` | 1 | nine of its cases import tests/test_judgment_view.py, a withheld test module; a guard after the submission brings the other 66 back (POLISH-2 export run) |
| `alerts-explain-test` | 1 | imports scripts/grid/explain_alerts.py, the excluded grid lane (POLISH-2 export run) |
| `alerts-live-check` | 1 | live check against the deployed service with the owner's identity |
| `alerts-ontology-live-test` | 1 | imports tests/test_alerts_explain.py and through it scripts/grid/explain_alerts.py, the excluded grid lane (POLISH-2 export run) |
| `book-generate-test` | 1 | reads .gitignore, excluded by ignore-rules (POLISH-2 export run) |
| `book-records-test` | 1 | imports tests/test_book_generate.py, a withheld test module (POLISH-2 export run) |
| `build-all-saved-ontology-test` | 1 | imports scripts/grid/build_all.py, the excluded grid lane bake script (arrived on main 2dcb1e24; withheld 2026-10-18 after the release 22 export run) |
| `build-all-swap-test` | 1 | loads scripts/grid/build_all.py, the excluded grid lane (POLISH-2 export run after the merge of main 49ec2958) |
| `cache-headers-test` | 1 | one class runs scripts/grid/build_all.py, the excluded grid lane, for a fresh bake; the route classification it also carries returns with a guard after the submission (POLISH-2 export run after the merge of main 49ec2958) |
| `campaign-archive` | 54 | historical campaign material from earlier, unrelated work |
| `case-reserve-market` | 5 | case pack outside the reading path; rights not reviewed (GATE-5) |
| `case-visayas` | 8 | skeleton case pack with nothing registered; rights not reviewed (GATE-5) |
| `clef-scripts` | 6 | self-hosted model experiments; never a runtime dependency |
| `codex-config` | 2 | local harness configuration |
| `consolidated-map-html` | 1 | owner's consolidated map, a working HTML page outside the reading path; stays with the private product records until reviewed |
| `contribution-guide` | 1 | contribution rules referencing excluded internal records |
| `corpus-extract-test` | 1 | imports scripts/corpus/extract.py, the live extraction runner |
| `corpus-index-test` | 1 | imports scripts/corpus/index_compendium.py and bq/load.py over the company project |
| `corpus-retrieve-test` | 1 | imports scripts/corpus/passages.py and runs scripts/corpus/retrieve.py, the excluded corpus scripts over the company copy (POLISH-2 export run) |
| `corpus-scripts` | 15 | fetch, upload and BigQuery load of the rule documents name the company bucket and project; only excerpt.py is included, by its own rule above |
| `corpus-store-test` | 1 | imports scripts/corpus/passages.py over the company copy |
| `corpus-tests-private` | 1 | imports scripts/corpus/fetch.py, which names the company bucket |
| `coverage-objects-test` | 1 | imports scripts/data/coverage_objects.py, the private data pipeline |
| `dashboard-lane` | 6 | dashboard lane reads private GCS data; internal data location and private inputs |
| `deploy-readme` | 1 | names the runtime service-account address in the deploy command (personal-email, line 118); the configuration files beside it stay (export-proposal.md disposition 7) |
| `deploy-script` | 1 | names the runtime and scheduler service-account addresses, the project and the region (personal-email, lines 49, 102, 116); the tests that run or read it are guarded by skipUnless(deploy.sh exists) (export-proposal.md disposition 8) |
| `desk-live-test` | 1 | one case imports scripts/desk/record_prompts.py, the excluded live recorder (GitHub PR #102; withheld 2026-10-18 after the release 22 export run; a skipUnless guard after the submission returns the file) |
| `engineering-migrations` | 1 | internal migration notes |
| `engineering-rest` | 1 | internal model workflow for the seats |
| `engineering-seats` | 1 | the AI helper launchers and their local harness gotchas; names local paths and the credential environment |
| `engineering-templates` | 5 | internal record templates |
| `eval-probe-bundle-test` | 1 | reads docs/work/probe-bundle/evaluation.md, a work record outside the exported reading path (POLISH-2 export run) |
| `event-candidates-test` | 1 | imports scripts/grid/event_candidates.py, the excluded grid lane |
| `event-prepare-test` | 1 | imports tests/test_grid_event.py, a withheld test module (POLISH-2 export run) |
| `experiments` | 74 | isolated research and historical proofs of concept; never a runtime dependency |
| `explainer-test` | 1 | checks that every record the served explainer links exists; docs/work/probe-bundle/evaluation.md and docs/work/product-shape-2026-10-17/strategy.md are work records outside the exported reading path (POLISH-2 export run) |
| `features-html` | 1 | working features page dated today, unreviewed; outside the reading path |
| `fuel-scripts` | 5 | fuel data pipeline over restricted sources |
| `gemini-helpers` | 2 | model launcher helpers; reference the credential environment |
| `grid-alerts-test` | 1 | imports tests/test_cache_headers.py at module level, a withheld test module (POLISH-2 export run after the merge of main 49ec2958) |
| `grid-ask-page-test` | 1 | loads scripts/grid/build_data.py, the excluded grid lane (POLISH-2 export run) |
| `grid-asset-test` | 1 | imports scripts/grid/build_assets.py, the excluded grid lane, and needs the real bake |
| `grid-briefs-test` | 1 | loads scripts/grid/briefs.py and phrase_brief.py, the excluded grid lane (POLISH-2 export run) |
| `grid-catalog-test` | 1 | imports scripts/grid/build_catalog.py, the excluded grid lane |
| `grid-data-tests` | 1 | checks the private tree's Git state, allowlist and Dockerfile for the baked grid snapshot; it needs the excluded builder and reads no public contract the exported suite covers |
| `grid-event-test` | 1 | reads docs/cases/reserve-market/evidence-manifest.json (an excluded case pack) and docs/work/corpus records at module level (POLISH-2 export run) |
| `grid-lane-scripts` | 20 | BigQuery export and snapshot builder for the grid replay; the queries name the private company copy |
| `grid-map-page-test` | 1 | imports scripts/grid/build_map_page.py, the excluded grid lane |
| `grid-models-page-test` | 1 | imports tests/test_grid_page.py, a withheld test module (POLISH-2 export run) |
| `grid-outages-test` | 1 | runs scripts/grid/build_outages.py, the excluded grid lane |
| `grid-outlook-tests` | 1 | imports scripts/grid/build_data.py, the excluded grid lane |
| `grid-outlooks-page-test` | 1 | imports scripts/grid/build_data.py, the excluded grid lane |
| `grid-page-test` | 1 | runs scripts/grid/briefs.py and build_outages.py, the excluded grid lane |
| `grid-register-page-test` | 1 | imports scripts/grid/build_data.py, the excluded grid lane |
| `grid-ui-test` | 1 | reads docs/work/platform-polish-2026-10-18/design-system.md at import, a withheld work record (release 23 export run, 2026-10-18); returns with the record or a guard after the submission |
| `harness-instructions` | 1 | harness instructions for the private repository |
| `hosted-lane-scripts` | 8 | hosted-lane project configuration and issue publishing |
| `hosting-stage-test` | 1 | loads scripts/release/export.py (excluded release tooling) and imports tests/test_grid_page.py and tests/test_grid_data.py, withheld test modules (POLISH-2 export run) |
| `ideas` | 16 | three earlier product ideas, superseded; history, not the entry |
| `ignore-rules` | 1 | ignore rules for private and generated paths of the working repository |
| `integration-contract-test` | 1 | imports tests/test_hosting_stage.py, a withheld test module (POLISH-2 export run) |
| `journal-test` | 1 | one case imports tests/test_cache_headers.py, a withheld test module; the other 24 return with a guard after the submission (POLISH-2 export run after the merge of main 49ec2958) |
| `judgment-actions-test` | 1 | imports tests/test_hosting_stage.py, a withheld test module (POLISH-2 export run) |
| `judgment-scripts` | 1 | live judgment runners over the company copy |
| `judgment-view-test` | 1 | imports scripts/grid/build_data.py, the excluded grid lane (see export-proposal.md: a guard is the better fix after submission) |
| `meos-bootstrap` | 1 | MEOS session bootstrap script |
| `meos-state` | 3 | MEOS runtime and session state |
| `ontology-bake-panel-test` | 1 | its tracked-path check reads .gitignore, excluded by ignore-rules (POLISH-2 export run) |
| `ontology-build` | 1 | runs the warehouse SQL above |
| `ontology-checks` | 6 | checks over the warehouse tables |
| `ontology-record-cards` | 1 | runs the warehouse SQL above |
| `ontology-sql` | 7 | warehouse SQL over the company copy's tables (src/alerts/sql carries the one vendored card summary the test compares) |
| `outage-checks-test` | 1 | reads scripts/data SQL over the company copy |
| `outlook-register-test` | 1 | reads scripts/data/sql/03_ref_regions_thresholds.sql and 05_labels_price.sql (the excluded private data pipeline), scripts/grid/events.json and docs/work/data-foundation records (POLISH-2 export run) |
| `outlook-sql` | 1 | query naming the company copy's tables |
| `perf-scripts` | 13 | performance measurement harness against the live service |
| `plan-tests` | 1 | validates internal plan records that this export excludes |
| `plan-tool` | 1 | internal task-graph tool; reads the excluded plan and progress records |
| `portfolio-import-script` | 1 | reads the private bucket (gcs-location, line 34); a test is never made to pass by exporting a private location (export-proposal.md disposition 6) |
| `portfolio-import-test` | 1 | imports scripts/alerts/portfolio_import.py, the excluded private-bucket reader (export-proposal.md disposition 6) |
| `price-availability-test` | 1 | runs scripts/outlook/availability.py over scripts/outlook/known_outages.sql, the excluded query, and imports scripts/grid/build_data.py (POLISH-2 export run) |
| `price-event-sql` | 1 | event-study query naming the company copy's tables |
| `price-fuel-test` | 1 | runs the excluded parquet export over the private bucket |
| `price-parquet-export` | 1 | reads the private bucket; the test that runs it (tests/test_price_fuel.py) is withheld |
| `price-response-test` | 1 | reads scripts/price/event_study.sql, the excluded event-study query, and docs/work/desk-agent-and-book-2026-10-18/event-study.md (POLISH-2 export run) |
| `price-sql` | 1 | export query naming the company copy's tables |
| `private-data-tools` | 56 | private data pipeline, SQL and analysis over restricted sources |
| `private-data-tools-test` | 1 | the test of the private data register builder (scripts/data/build_register.py, excluded above): its fixture is a listing of the company bucket, so it leaves the export with the script it tests (added 2026-10-17 by the orchestrator when the release audit flagged the bucket location) |
| `private-readme` | 1 | private working-repository readme; the export writes its own README |
| `publish-saved-script` | 1 | uploads the saved alert material to the private data bucket (gcs-location, line 8); the bake downloads it by default, so the export's bake works from a local --saved-ontology folder only (added 2026-10-18 on main 2dcb1e24) |
| `register-gaps-test` | 1 | loads scripts/grid/build_assets.py and reads scripts/grid/register_gaps.json, the excluded grid lane (POLISH-2 export run after the merge of main 49ec2958) |
| `release-audit-tests` | 1 | audits this private repository's history and allowlist; not part of the public application suite |
| `release-tooling` | 3 | release audit tooling and allowlist; publishing them is a REL-5 decision after GATE-5 |
| `repository-metadata` | 1 | repository tooling metadata |
| `research-dossiers` | 93 | third-party research downloads; rights not cleared |
| `research-tools` | 1 | research download helpers |
| `review-desk-5` | 1 | dated review record quoting a workstation path (absolute-home-path, lines 55 and 137); records are not edited (export-proposal.md disposition 4) |
| `review-found-1` | 1 | dated review record quoting workstation paths (absolute-home-path, line 15); records are not edited (same disposition as DESK-5 and HOST-1; found at the POLISH-2 merge of main 49ec2958) |
| `review-host-1` | 1 | dated review record carrying a cloud project id, workstation paths and its own quote of a synthetic credential-shaped literal; excluded rather than excepted (export-proposal.md disposition 5) |
| `review-polish-2` | 1 | the review record quotes a company-domain fragment as a scan pattern; records are never edited, so this one record stays private |
| `seat-launchers` | 14 | internal model-seat launchers; reference local harnesses and credential environment |
| `strategy-history` | 14 | earlier strategy history; the direction of record is cited from the architecture pages |
| `unmatched` | 405 | no reviewed include rule covers this path |
| `validation-scripts` | 2 | the VAL-1 query over the company copy; the record is included, the query names the private tables |
| `wesm-sources-test` | 1 | runs scripts/data/wesm/export.sh, the private export; the readers it covers are also covered by tests/test_review_case.py |
| `whiteboard-photo` | 1 | a photograph of the team whiteboard: a binary the content rules cannot read, with handwriting that may name people |
| `work-page-test` | 1 | reads docs/work/tasks.json and product-gap records this export excludes |
| `workspace-lane-scripts` | 5 | local runner, seeding and browser-check scripts for the internal workspace lane |
| `workspace-preview` | 2 | static interaction reference held for REL-5 review; its README links to product documents this export excludes |

`scripts/release/export.py --dry-run` prints every excluded path with its rule and
reason; this table is the per-rule summary of the same run.

## First and last commit per included path

| Path | First commit | Last commit |
|---|---|---|
| `.dockerignore` | 2026-10-12 `0a5c4851a367` | 2026-10-16 `0fccc3d2f4a2` |
| `AGENTS.md` | 2026-10-03 `2e7fa37d4999` | 2026-10-18 `f57cec174d21` |
| `ATTRIBUTION.md` | 2026-10-19 `ed4e45a409f0` | 2026-10-19 `40fc1778b1b1` |
| `Dockerfile` | 2026-10-12 `0a5c4851a367` | 2026-10-16 `0fccc3d2f4a2` |
| `LICENSE` | 2026-10-19 `ed4e45a409f0` | 2026-10-19 `ed4e45a409f0` |
| `docs/README.md` | 2026-10-03 `77f2895235c8` | 2026-10-15 `7f54bc8cc608` |
| `docs/START-HERE.md` | 2026-10-14 `7b949424588a` | 2026-10-19 `2262f4899cad` |
| `docs/architecture/README.md` | 2026-10-03 `77f2895235c8` | 2026-10-16 `dcc2ab2722e4` |
| `docs/architecture/building-blocks.md` | 2026-10-03 `45c29311cc1a` | 2026-10-03 `45c29311cc1a` |
| `docs/architecture/decision-system-v1.md` | 2026-10-04 `af242f8b0680` | 2026-10-11 `258a074a230b` |
| `docs/architecture/meta-thesis-and-framework.md` | 2026-10-16 `949e587cf708` | 2026-10-18 `933692b5cca4` |
| `docs/architecture/ontology-profile-v1.md` | 2026-10-04 `af242f8b0680` | 2026-10-17 `87b8fd069ef6` |
| `docs/architecture/platform-contracts.md` | 2026-10-03 `45c29311cc1a` | 2026-10-03 `45c29311cc1a` |
| `docs/architecture/theoretical-foundation.md` | 2026-10-16 `dcc2ab2722e4` | 2026-10-19 `ed4e45a409f0` |
| `docs/cases/first-case.md` | 2026-10-03 `77f2895235c8` | 2026-10-04 `f2ea4e85e4df` |
| `docs/cases/pedc-u2-2026-09-21/brief.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/evaluation.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/evidence-manifest.json` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/mappings.json` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/outlook-revision.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/packet.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/review.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/cases/pedc-u2-2026-09-21/scenario-proposal.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `docs/competition/ai-builder-cup-2026/deck.md` | 2026-10-12 `76d9b27f9a41` | 2026-10-19 `ed4e45a409f0` |
| `docs/competition/ai-builder-cup-2026/future-of-work-case.md` | 2026-10-16 `5fbc22751998` | 2026-10-17 `83091d0055cd` |
| `docs/competition/ai-builder-cup-2026/organizer-questions.md` | 2026-10-04 `af242f8b0680` | 2026-10-19 `ed4e45a409f0` |
| `docs/competition/ai-builder-cup-2026/provenance-log.md` | 2026-10-11 `364a8ae39c1d` | 2026-10-12 `a873be062578` |
| `docs/competition/ai-builder-cup-2026/release-manifest.json` | 2026-10-17 `ae78a52b87ae` | 2026-10-19 `dce95129b306` |
| `docs/competition/ai-builder-cup-2026/release-manifest.template.json` | 2026-10-04 `af242f8b0680` | 2026-10-04 `f2ea4e85e4df` |
| `docs/competition/ai-builder-cup-2026/requirements.md` | 2026-10-04 `af242f8b0680` | 2026-10-19 `ed4e45a409f0` |
| `docs/competition/ai-builder-cup-2026/scorecard.md` | 2026-10-04 `af242f8b0680` | 2026-10-18 `933692b5cca4` |
| `docs/competition/ai-builder-cup-2026/story-and-script.md` | 2026-10-04 `af242f8b0680` | 2026-10-19 `ed4e45a409f0` |
| `docs/competition/ai-builder-cup-2026/submission-checklist.md` | 2026-10-04 `af242f8b0680` | 2026-10-19 `cce286efbfb4` |
| `docs/competition/ai-builder-cup-2026/video-shotlist.md` | 2026-10-15 `8527446e1a6f` | 2026-10-19 `ed4e45a409f0` |
| `docs/engineering/how-we-work.md` | 2026-10-15 `45a2386aed04` | 2026-10-19 `2262f4899cad` |
| `docs/engineering/lifecycle.md` | 2026-10-03 `77f2895235c8` | 2026-10-14 `7b949424588a` |
| `docs/engineering/review-and-feedback.md` | 2026-10-11 `d8a00a90792e` | 2026-10-14 `7b949424588a` |
| `docs/explainer/00-ideas-1-know.md` | 2026-10-17 `53ed5b432345` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/00-ideas-2-do.md` | 2026-10-17 `53ed5b432345` | 2026-10-17 `286be8d8c461` |
| `docs/explainer/00-ideas-3-who.md` | 2026-10-17 `53ed5b432345` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/00-ideas-4-learn.md` | 2026-10-17 `53ed5b432345` | 2026-10-19 `ed4e45a409f0` |
| `docs/explainer/00-system.md` | 2026-10-15 `b166482a01d5` | 2026-10-19 `ed4e45a409f0` |
| `docs/explainer/01-why.md` | 2026-10-15 `9ba75dedf354` | 2026-10-19 `ed4e45a409f0` |
| `docs/explainer/02-grid.md` | 2026-10-15 `9ba75dedf354` | 2026-10-18 `089de63e396a` |
| `docs/explainer/03-evidence.md` | 2026-10-15 `9ba75dedf354` | 2026-10-15 `7f54bc8cc608` |
| `docs/explainer/04-judgment.md` | 2026-10-15 `9ba75dedf354` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/05-runs.md` | 2026-10-15 `9ba75dedf354` | 2026-10-19 `2262f4899cad` |
| `docs/explainer/06-work.md` | 2026-10-15 `9ba75dedf354` | 2026-10-15 `7f54bc8cc608` |
| `docs/explainer/07-paper-guide.md` | 2026-10-17 `73211b8c82b6` | 2026-10-19 `ed4e45a409f0` |
| `docs/explainer/08-time-contract.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/09-signal-to-decision.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/10-driver-card.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/11-judgment-showcase.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/12-compiler-and-transaction.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/13-rules-and-receipt.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/14-methods-and-models.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/15-requirements.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/16-measurements.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/17-layers-and-records.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/18-generated-views.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/19-grounding.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/20-evaluation-and-honesty.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/21-data-and-event-map.md` | 2026-10-17 `73211b8c82b6` | 2026-10-17 `73211b8c82b6` |
| `docs/explainer/22-hosting-in-depth.md` | 2026-10-17 `73211b8c82b6` | 2026-10-18 `933692b5cca4` |
| `docs/explainer/README.md` | 2026-10-15 `45a2386aed04` | 2026-10-19 `ed4e45a409f0` |
| `docs/explainer/index.html` | 2026-10-15 `9ba75dedf354` | 2026-10-19 `2262f4899cad` |
| `docs/glossary.md` | 2026-10-15 `45a2386aed04` | 2026-10-17 `73211b8c82b6` |
| `docs/product/capability-map.md` | 2026-10-17 `611746f52ebc` | 2026-10-18 `089de63e396a` |
| `docs/product/definitive-blueprint-2026-10-04.md` | 2026-10-04 `af242f8b0680` | 2026-10-19 `ed4e45a409f0` |
| `docs/product/integration-contract.json` | 2026-10-17 `611746f52ebc` | 2026-10-18 `089de63e396a` |
| `docs/product/integration-contract.md` | 2026-10-17 `611746f52ebc` | 2026-10-18 `089de63e396a` |
| `docs/product/interface-and-demo-v1.md` | 2026-10-04 `af242f8b0680` | 2026-10-14 `7b949424588a` |
| `docs/product/market-factors-2026-10-17.md` | 2026-10-17 `2681d7d59a9b` | 2026-10-17 `538fef5bd6f1` |
| `docs/product/paper-accountable-ai-decisions-2026-10-17.md` | 2026-10-17 `19de338e183b` | 2026-10-19 `2262f4899cad` |
| `docs/product/problem-statement-2026-10-17.md` | 2026-10-17 `7cf1a9edf29c` | 2026-10-17 `87b8fd069ef6` |
| `docs/product/project-thesis.md` | 2026-10-05 `2066d2d0a04f` | 2026-10-19 `ed4e45a409f0` |
| `docs/product/strategy.md` | 2026-10-03 `77f2895235c8` | 2026-10-14 `7b949424588a` |
| `docs/product/user-stories-2026-10-17.md` | 2026-10-17 `19de338e183b` | 2026-10-17 `87b8fd069ef6` |
| `docs/product/working-paper-2026-10-11.md` | 2026-10-11 `258a074a230b` | 2026-10-19 `ed4e45a409f0` |
| `docs/routes.json` | 2026-10-03 `77f2895235c8` | 2026-10-17 `f177805be561` |
| `docs/status.md` | 2026-10-03 `77f2895235c8` | 2026-10-19 `2262f4899cad` |
| `docs/work/data-foundation/timesfm-tabfm.md` | 2026-10-03 `99208db9b7e7` | 2026-10-03 `b31463b94e22` |
| `docs/work/docs-for-people/systems-inventory-2026-10-15.md` | 2026-10-15 `c6555020234e` | 2026-10-19 `ed4e45a409f0` |
| `docs/work/grid-desk/event.md` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-14 `8bb2d81a4a85` |
| `docs/work/grid-desk/live-run-2026-10-14.md` | 2026-10-14 `ced6ce6b44d7` | 2026-10-14 `ddac6e8e2be0` |
| `docs/work/meta-framing-2026-10-17/strategy.md` | 2026-10-17 `e1ee29a3e858` | 2026-10-17 `87b8fd069ef6` |
| `docs/work/outlook-archive/attribution-intent.md` | 2026-10-17 `e7654d8bec26` | 2026-10-17 `23d837e9e637` |
| `docs/work/outlook-archive/attribution.md` | 2026-10-17 `158b03fd7373` | 2026-10-17 `4a141ec794b5` |
| `docs/work/outlook-archive/first-outlook.md` | 2026-10-16 `754daceccc6f` | 2026-10-16 `a19f25a45a97` |
| `docs/work/outlook-archive/intent.md` | 2026-10-16 `728f71a9e35c` | 2026-10-16 `728f71a9e35c` |
| `docs/work/outlook-archive/records.md` | 2026-10-16 `df35a11872c1` | 2026-10-18 `089de63e396a` |
| `docs/work/outlook-archive/register.json` | 2026-10-16 `275a49565eb7` | 2026-10-17 `0a9184e061de` |
| `docs/work/outlook-archive/register.md` | 2026-10-16 `275a49565eb7` | 2026-10-17 `0a9184e061de` |
| `docs/work/outlook-archive/reissue.md` | 2026-10-18 `f4a9c45d1c99` | 2026-10-18 `089de63e396a` |
| `docs/work/outlook-archive/scoring.md` | 2026-10-17 `a201d7891d5f` | 2026-10-17 `b48d5ba42323` |
| `docs/work/outlook-archive/third-outlook.md` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `docs/work/permissions/2026-10-13-wesm-company-copy.md` | 2026-10-13 `eec179e35e6f` | 2026-10-14 `8ea54c27da92` |
| `docs/work/platform-epics-2026-10-17/strategy.md` | 2026-10-18 `34f6c23a2e77` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/ARCH-1.md` | 2026-10-16 `9e03e1c097fb` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/ARCH-2.md` | 2026-10-16 `9e62b982ecd7` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/ARCH-3.md` | 2026-10-16 `069c85f7a3a5` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/ARCH-4.md` | 2026-10-17 `f09799c9d520` | 2026-10-17 `4a141ec794b5` |
| `docs/work/reviews/ASK-2.md` | 2026-10-18 `3276f9a21065` | 2026-10-18 `3276f9a21065` |
| `docs/work/reviews/ATG-1.md` | 2026-10-16 `eb01491bb440` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-2.md` | 2026-10-16 `57b7759f6aba` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-3.md` | 2026-10-16 `312c119e10b2` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-4.md` | 2026-10-16 `b7d2c66a070d` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-5.md` | 2026-10-16 `aad8fcdce886` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-6.md` | 2026-10-16 `0d5fbfa597eb` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-7.md` | 2026-10-16 `868d1186a6a5` | 2026-10-16 `0fccc3d2f4a2` |
| `docs/work/reviews/ATG-8.md` | 2026-10-16 `fbfda2cf9f57` | 2026-10-16 `be80e5affabc` |
| `docs/work/reviews/BAKE-1.md` | 2026-10-17 `344f8037f6e3` | 2026-10-17 `7f3ad083a04e` |
| `docs/work/reviews/BOOK-1.md` | 2026-10-18 `b00603e78fe4` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/BOOK-2.md` | 2026-10-18 `38101319c85f` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/BOOK-3.md` | 2026-10-18 `b75e5069cadd` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/BOOK-4.md` | 2026-10-18 `b13f36a79bf7` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/CAP-1.md` | 2026-10-17 `00f4d6c3e4ea` | 2026-10-17 `ef19fb8036f5` |
| `docs/work/reviews/CLEF-1.md` | 2026-10-12 `9b23bd0fedaa` | 2026-10-13 `8cf6e75935a6` |
| `docs/work/reviews/COPY-1.md` | 2026-10-18 `cfa0f74d7a2a` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/COPY-2.md` | 2026-10-18 `1d9b177d9f13` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/CORE-1.md` | 2026-10-11 `2b249e9dc0b8` | 2026-10-11 `83e181f25fc6` |
| `docs/work/reviews/CORE-10.md` | 2026-10-16 `9945741f8cc5` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/CORE-2.md` | 2026-10-11 `d0b8c48fa287` | 2026-10-13 `b27d85718981` |
| `docs/work/reviews/CORE-3.md` | 2026-10-12 `833c2b534549` | 2026-10-13 `b6fd54f43525` |
| `docs/work/reviews/CORE-4.md` | 2026-10-12 `88e0cfd51ff1` | 2026-10-13 `df716a32d771` |
| `docs/work/reviews/CORE-5.md` | 2026-10-16 `15166159520a` | 2026-10-16 `15166159520a` |
| `docs/work/reviews/CORE-6.md` | 2026-10-12 `b7d766fa1271` | 2026-10-12 `aec43f99823c` |
| `docs/work/reviews/CORE-7.md` | 2026-10-11 `0b2809440db9` | 2026-10-11 `dc5ad0071b14` |
| `docs/work/reviews/CORE-8.md` | 2026-10-13 `b67b634b54c3` | 2026-10-14 `fde1477e61ce` |
| `docs/work/reviews/CORE-9.md` | 2026-10-13 `3e3cfd22f6c8` | 2026-10-14 `058a970b211f` |
| `docs/work/reviews/CORP-0.md` | 2026-10-16 `42e41b785cc6` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/CORP-1.md` | 2026-10-16 `88089c11dbbc` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/CORP-2.md` | 2026-10-16 `b23f908e9b48` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/CORP-3.md` | 2026-10-16 `4345a2a2709a` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/CORP-4.md` | 2026-10-16 `25dbd21e89aa` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/CORP-5.md` | 2026-10-16 `9cfd2a70c89f` | 2026-10-16 `9ba846dce8e1` |
| `docs/work/reviews/DATA-1.md` | 2026-10-13 `f62f53903140` | 2026-10-14 `d5cef3622966` |
| `docs/work/reviews/DESK-1.md` | 2026-10-17 `ba3084bf94c3` | 2026-10-17 `9715125f46d8` |
| `docs/work/reviews/DESK-2.md` | 2026-10-17 `dcbbac8c4668` | 2026-10-17 `b8b2096c87f5` |
| `docs/work/reviews/DESK-3.md` | 2026-10-17 `77af13348bea` | 2026-10-17 `afe0c7a38db1` |
| `docs/work/reviews/DESK-4.md` | 2026-10-17 `6973d929c196` | 2026-10-17 `afe0c7a38db1` |
| `docs/work/reviews/DESK-6.md` | 2026-10-17 `e86db9f6f286` | 2026-10-17 `b48d5ba42323` |
| `docs/work/reviews/DESK-7.md` | 2026-10-17 `80208aec7dd8` | 2026-10-17 `e08329fcef34` |
| `docs/work/reviews/DESK-8.md` | 2026-10-18 `12f09442c4d6` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/DM-batch-2026-10-18.md` | 2026-10-18 `684e1ce22e5f` | 2026-10-18 `933692b5cca4` |
| `docs/work/reviews/DOC-3.md` | 2026-10-15 `4bfb44f1f8d8` | 2026-10-15 `15edd65717b2` |
| `docs/work/reviews/DOC-4.md` | 2026-10-15 `ace336b8bf5c` | 2026-10-16 `9dd3d3117b94` |
| `docs/work/reviews/DOC-5.md` | 2026-10-17 `0652350d3bc3` | 2026-10-17 `2841027a4880` |
| `docs/work/reviews/DOCK-1.md` | 2026-10-18 `c34b2c5714ce` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/DOCK-2.md` | 2026-10-18 `86507c25c90c` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/DOCK-3.md` | 2026-10-18 `0c21041645cd` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/DOCK-5.md` | 2026-10-18 `13ba9aacd3e3` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/EVAL-1.md` | 2026-10-11 `d4cfd4b31a68` | 2026-10-12 `b02fb4a008af` |
| `docs/work/reviews/EVAL-2.md` | 2026-10-12 `e302f0c204d2` | 2026-10-13 `5b6fc1fa2db1` |
| `docs/work/reviews/EVAL-3.md` | 2026-10-12 `112798bd87d3` | 2026-10-14 `43bac832c862` |
| `docs/work/reviews/EVAL-4.md` | 2026-10-11 `fe99f3507b7b` | 2026-10-11 `ea45a6c9736d` |
| `docs/work/reviews/EVAL-5.md` | 2026-10-14 `2c2fe344d413` | 2026-10-14 `51dadb71f966` |
| `docs/work/reviews/EVAL-6.md` | 2026-10-11 `27f9831a3f85` | 2026-10-12 `b6bc2bf1220b` |
| `docs/work/reviews/EVAL-8.md` | 2026-10-16 `06cb6bbd2a80` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/EXPL-1.md` | 2026-10-15 `d91c87a8d530` | 2026-10-15 `adf520642fcb` |
| `docs/work/reviews/EXPL-2.md` | 2026-10-15 `cf616e91f128` | 2026-10-15 `c0da37badc90` |
| `docs/work/reviews/FRONT-1.md` | 2026-10-17 `c4a7cd400007` | 2026-10-17 `d0a2ed9ef08a` |
| `docs/work/reviews/GRID-1.md` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `docs/work/reviews/GRID-2.md` | 2026-10-14 `57fc294ddf73` | 2026-10-14 `0307e48fac96` |
| `docs/work/reviews/GRID-3.md` | 2026-10-14 `008fde0a3f35` | 2026-10-14 `8bb2d81a4a85` |
| `docs/work/reviews/HOST-0.md` | 2026-10-11 `df4b7a35c050` | 2026-10-12 `36e2117aa6cc` |
| `docs/work/reviews/HOST-2.md` | 2026-10-13 `0a3350d48dc5` | 2026-10-14 `51dadb71f966` |
| `docs/work/reviews/HOST-4.md` | 2026-10-14 `a4d25c3de402` | 2026-10-14 `aea5846e3d53` |
| `docs/work/reviews/HOST-5.md` | 2026-10-14 `97ef439254f8` | 2026-10-14 `f311ee685fe5` |
| `docs/work/reviews/IMPACT-1.md` | 2026-10-16 `3c8d02edc1ec` | 2026-10-17 `e179472b8632` |
| `docs/work/reviews/IMPACT-2.md` | 2026-10-17 `aa0d96202870` | 2026-10-17 `b8b2096c87f5` |
| `docs/work/reviews/MAP-1.md` | 2026-10-18 `839dd8845fe7` | 2026-10-18 `983f0bdc1490` |
| `docs/work/reviews/MODELS-1.md` | 2026-10-17 `e199fded1731` | 2026-10-18 `ed88d7aee791` |
| `docs/work/reviews/NAV-1.md` | 2026-10-17 `c56e4768c144` | 2026-10-17 `538fef5bd6f1` |
| `docs/work/reviews/NUM-0.md` | 2026-10-11 `2d8c310d7614` | 2026-10-11 `527d8df88891` |
| `docs/work/reviews/NUM-1.md` | 2026-10-12 `fb0f42852abd` | 2026-10-13 `1d46182f9bab` |
| `docs/work/reviews/OUT-1.md` | 2026-10-18 `f9011be0d2a6` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/OUT-2.md` | 2026-10-18 `15c7b8387d84` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/OUT-3.md` | 2026-10-18 `86f49ec148d5` | 2026-10-18 `089de63e396a` |
| `docs/work/reviews/OUTLOOK-7.md` | 2026-10-17 `b92e3144104d` | 2026-10-17 `cf1db6343044` |
| `docs/work/reviews/PERF-0.md` | 2026-10-15 `f4166de07cab` | 2026-10-15 `110a26ad9b81` |
| `docs/work/reviews/PERF-1.md` | 2026-10-14 `3e75c6879003` | 2026-10-14 `e0a7c05da372` |
| `docs/work/reviews/PERF-2.md` | 2026-10-14 `485fbabfc6c3` | 2026-10-14 `53532191798c` |
| `docs/work/reviews/PERF-3.md` | 2026-10-15 `122e02472c1b` | 2026-10-15 `4a51e36d20b3` |
| `docs/work/reviews/PERF-4.md` | 2026-10-15 `4bd94bc3cd2d` | 2026-10-15 `840bb2a71492` |
| `docs/work/reviews/PERF-5.md` | 2026-10-14 `60ae50cf13b2` | 2026-10-15 `a4d95d989300` |
| `docs/work/reviews/PRICE-2.md` | 2026-10-16 `fed0c2a32379` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/PRICE-3.md` | 2026-10-16 `d0bde4518098` | 2026-10-17 `e179472b8632` |
| `docs/work/reviews/PROJ-2.md` | 2026-10-16 `64a41300aecf` | 2026-10-16 `a19f25a45a97` |
| `docs/work/reviews/README.md` | 2026-10-11 `d8a00a90792e` | 2026-10-11 `d8a00a90792e` |
| `docs/work/reviews/REG-2.md` | 2026-10-17 `2fdddec08e46` | 2026-10-17 `0a9184e061de` |
| `docs/work/reviews/REL-1.md` | 2026-10-11 `364a8ae39c1d` | 2026-10-12 `a873be062578` |
| `docs/work/reviews/REL-2.md` | 2026-10-13 `500542d0394d` | 2026-10-14 `ea63d8dfa87b` |
| `docs/work/reviews/REL-3.md` | 2026-10-15 `26025eedf2a1` | 2026-10-15 `c35399bb3723` |
| `docs/work/reviews/REL-4.md` | 2026-10-17 `cc63e4af60e5` | 2026-10-17 `627b655bedc6` |
| `docs/work/reviews/ROUTES-1.md` | 2026-10-17 `a216e7219213` | 2026-10-17 `4ce586ab9297` |
| `docs/work/reviews/SCORE-1.md` | 2026-10-17 `08e38368b60f` | 2026-10-17 `b48d5ba42323` |
| `docs/work/reviews/SHELL-1.md` | 2026-10-18 `710b68caeadd` | 2026-10-18 `710b68caeadd` |
| `docs/work/reviews/SYNC-1.md` | 2026-10-14 `7871de234587` | 2026-10-14 `6cf7b82dc82c` |
| `docs/work/reviews/UI-1.md` | 2026-10-11 `0bc830d9df9c` | 2026-10-12 `c4087b31ff75` |
| `docs/work/reviews/UI-2.md` | 2026-10-12 `80f2efc0a2ba` | 2026-10-14 `2ca63f8f0b95` |
| `docs/work/reviews/VIEW-0.md` | 2026-10-17 `c8fc79c6308b` | 2026-10-17 `cc3d1c3d3724` |
| `docs/work/reviews/VIEW-1.md` | 2026-10-17 `53374f08382e` | 2026-10-18 `da14c4705446` |
| `docs/work/reviews/WORK-1.md` | 2026-10-17 `17b2c90d19ba` | 2026-10-18 `27c6a541a898` |
| `docs/work/reviews/first-screen-2026-10-18.md` | 2026-10-18 `f226c2729f78` | 2026-10-18 `089de63e396a` |
| `docs/work/thesis-challenge-2026-10-16/coverage.md` | 2026-10-16 `dcaffe2372d1` | 2026-10-17 `7605484e2f48` |
| `docs/work/thesis-challenge-2026-10-16/estate-inventory.md` | 2026-10-16 `15166159520a` | 2026-10-16 `15166159520a` |
| `docs/work/thesis-challenge-2026-10-16/evidence-ledger.md` | 2026-10-16 `15166159520a` | 2026-10-17 `7ebcc8288130` |
| `docs/work/thesis-challenge-2026-10-16/price-basis.md` | 2026-10-16 `dcaffe2372d1` | 2026-10-16 `4fa33ad7cec6` |
| `docs/work/thesis-challenge-2026-10-16/problem-and-thesis.md` | 2026-10-16 `2c113386d162` | 2026-10-17 `83091d0055cd` |
| `docs/work/thesis-challenge-2026-10-16/strategy.md` | 2026-10-16 `15166159520a` | 2026-10-16 `e10c5cc58c3a` |
| `docs/work/validation/outage-lag.md` | 2026-10-16 `d417278d94c8` | 2026-10-18 `933692b5cca4` |
| `requirements/h1.lock` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `scripts/book/bake_book.py` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `scripts/book/generate.py` | 2026-10-18 `e792743caf5b` | 2026-10-18 `089de63e396a` |
| `scripts/book/vintages.py` | 2026-10-18 `e05f78669e37` | 2026-10-18 `089de63e396a` |
| `scripts/deploy/cleanup.py` | 2026-10-13 `16bdb610b3ff` | 2026-10-14 `51dadb71f966` |
| `scripts/deploy/firebase.json` | 2026-10-13 `16bdb610b3ff` | 2026-10-18 `b22c44a717f8` |
| `scripts/deploy/firestore.json` | 2026-10-18 `d82d69cf2f87` | 2026-10-18 `089de63e396a` |
| `scripts/deploy/firestore.rules` | 2026-10-18 `d82d69cf2f87` | 2026-10-18 `089de63e396a` |
| `scripts/deploy/platform_digest.py` | 2026-10-14 `17ebf89c1aae` | 2026-10-14 `aea5846e3d53` |
| `scripts/deploy/read_stamp.py` | 2026-10-18 `ca4c1a2b9eb5` | 2026-10-18 `933692b5cca4` |
| `scripts/deploy/run-demo.sh` | 2026-10-12 `0a5c4851a367` | 2026-10-13 `c2cf64a009b8` |
| `scripts/deploy/stage_hosting.py` | 2026-10-14 `b93a527c3d21` | 2026-10-18 `b22c44a717f8` |
| `scripts/deploy/walkthrough.py` | 2026-10-13 `5e19ceec7394` | 2026-10-18 `809840e3db5c` |
| `scripts/deploy/walkthrough.sh` | 2026-10-13 `5e19ceec7394` | 2026-10-13 `c2cf64a009b8` |
| `scripts/docs/build_explainer.py` | 2026-10-15 `9ba75dedf354` | 2026-10-19 `ed4e45a409f0` |
| `scripts/docs/build_paper.py` | 2026-10-17 `6de9789caa8c` | 2026-10-19 `a15b9e064ee4` |
| `scripts/docs/build_showcase.py` | 2026-10-18 `0d5053706fb2` | 2026-10-18 `00a5f1d26b81` |
| `scripts/docs/check_plain.py` | 2026-10-18 `3a39fb4b66ec` | 2026-10-18 `00a5f1d26b81` |
| `scripts/eval/probe_bundle.py` | 2026-10-12 `e302f0c204d2` | 2026-10-13 `5b6fc1fa2db1` |
| `scripts/ontology/alert_cards.py` | 2026-10-18 `0929fb54ec8c` | 2026-10-18 `933692b5cca4` |
| `scripts/ontology/bake_panel.py` | 2026-10-17 `affeddd93966` | 2026-10-18 `089de63e396a` |
| `scripts/ontology/phrase_cache.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `scripts/ontology/phrase_card.py` | 2026-10-17 `affeddd93966` | 2026-10-17 `83091d0055cd` |
| `scripts/outlook/attribute.py` | 2026-10-17 `158b03fd7373` | 2026-10-17 `4a141ec794b5` |
| `scripts/outlook/availability.py` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `scripts/outlook/issue.py` | 2026-10-18 `f4a9c45d1c99` | 2026-10-18 `089de63e396a` |
| `scripts/outlook/score.py` | 2026-10-17 `a201d7891d5f` | 2026-10-17 `b48d5ba42323` |
| `scripts/price/baselines.py` | 2026-10-16 `9d343aade9d2` | 2026-10-16 `a19f25a45a97` |
| `scripts/price/challengers.py` | 2026-10-16 `526464ecc2fa` | 2026-10-17 `7605484e2f48` |
| `scripts/price/event_study.py` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `scripts/price/impact.py` | 2026-10-16 `35264df94616` | 2026-10-17 `b8b2096c87f5` |
| `scripts/probe/run.py` | 2026-10-12 `1f50a20c5e69` | 2026-10-13 `b6fd54f43525` |
| `scripts/repo.py` | 2026-10-03 `77f2895235c8` | 2026-10-17 `e5a24f93b404` |
| `src/README.md` | 2026-10-03 `77f2895235c8` | 2026-10-18 `933692b5cca4` |
| `src/adapters/bigquery/README.md` | 2026-10-12 `8b2c230e4c8e` | 2026-10-13 `1d46182f9bab` |
| `src/adapters/bigquery/__init__.py` | 2026-10-12 `8b2c230e4c8e` | 2026-10-13 `1d46182f9bab` |
| `src/adapters/bigquery/fixtures/whatif_statements.json` | 2026-10-12 `8b2c230e4c8e` | 2026-10-13 `1d46182f9bab` |
| `src/adapters/bigquery/whatif.py` | 2026-10-12 `8b2c230e4c8e` | 2026-10-13 `1d46182f9bab` |
| `src/adapters/corpus/README.md` | 2026-10-16 `c172d592f4fb` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/__init__.py` | 2026-10-16 `03ec7668b441` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/acquire.py` | 2026-10-16 `03ec7668b441` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/extract/README.md` | 2026-10-16 `7f98e5755862` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/extract/__init__.py` | 2026-10-16 `99996c9adfba` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/extract/check.py` | 2026-10-16 `99996c9adfba` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/extract/run.py` | 2026-10-16 `7f98e5755862` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/extract/schema.py` | 2026-10-16 `99996c9adfba` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/retrieve.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `src/adapters/corpus/store/__init__.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/store/local.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/store/records.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/store/schema.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/store/sqlcheck.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/corpus/text.py` | 2026-10-16 `03ec7668b441` | 2026-10-16 `9ba846dce8e1` |
| `src/adapters/firestore/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `src/adapters/gemini/README.md` | 2026-10-06 `f3c796287090` | 2026-10-16 `a19f25a45a97` |
| `src/adapters/gemini/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-16 `a19f25a45a97` |
| `src/adapters/gemini/run.py` | 2026-10-06 `f3c796287090` | 2026-10-16 `a19f25a45a97` |
| `src/adapters/gemini/transport.py` | 2026-10-06 `f3c796287090` | 2026-10-18 `089de63e396a` |
| `src/adapters/gemini/worker.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `dc5ad0071b14` |
| `src/adapters/identity/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-06 `f3c796287090` |
| `src/adapters/systemone/__init__.py` | 2026-10-12 `1f50a20c5e69` | 2026-10-13 `b6fd54f43525` |
| `src/adapters/systemone/run.py` | 2026-10-12 `1f50a20c5e69` | 2026-10-13 `b6fd54f43525` |
| `src/adapters/wesm/README.md` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `src/adapters/wesm/__init__.py` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `src/adapters/wesm/advisories.py` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `src/adapters/wesm/registry.py` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `src/agent/__init__.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/budget.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/catalogue.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/fakes.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/routes.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/service.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/session.py` | 2026-10-18 `d6fc1ce1691a` | 2026-10-19 `ed4e45a409f0` |
| `src/agent/store.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `src/agent/wiring.py` | 2026-10-18 `d6fc1ce1691a` | 2026-10-18 `089de63e396a` |
| `src/alerts/__init__.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `1ebe1996596c` |
| `src/alerts/auth.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `538fef5bd6f1` |
| `src/alerts/bigquery.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `1ebe1996596c` |
| `src/alerts/draft.py` | 2026-10-17 `5ceb8b39c743` | 2026-10-17 `c4f768c486e2` |
| `src/alerts/drivers.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `933692b5cca4` |
| `src/alerts/explain.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `933692b5cca4` |
| `src/alerts/mail.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `1ebe1996596c` |
| `src/alerts/model.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-19 `ed4e45a409f0` |
| `src/alerts/notices.py` | 2026-10-18 `0929fb54ec8c` | 2026-10-18 `933692b5cca4` |
| `src/alerts/ontology.py` | 2026-10-18 `0929fb54ec8c` | 2026-10-18 `933692b5cca4` |
| `src/alerts/ontology_live.py` | 2026-10-18 `85fd16848ba1` | 2026-10-18 `933692b5cca4` |
| `src/alerts/replay.py` | 2026-10-18 `8080f2ac9b06` | 2026-10-18 `933692b5cca4` |
| `src/alerts/routes.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-18 `933692b5cca4` |
| `src/alerts/service.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-19 `ed4e45a409f0` |
| `src/alerts/sql.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `1ebe1996596c` |
| `src/alerts/sql/06_card_summary.sql` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-17 `1ebe1996596c` |
| `src/alerts/store.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-18 `933692b5cca4` |
| `src/api/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-18 `b22c44a717f8` |
| `src/api/hosted.py` | 2026-10-12 `0a5c4851a367` | 2026-10-18 `933692b5cca4` |
| `src/api/local.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `src/book/__init__.py` | 2026-10-18 `e792743caf5b` | 2026-10-18 `089de63e396a` |
| `src/book/adapter.py` | 2026-10-18 `54f8940ba91c` | 2026-10-18 `089de63e396a` |
| `src/book/exposure.py` | 2026-10-18 `e05f78669e37` | 2026-10-18 `089de63e396a` |
| `src/book/generate.py` | 2026-10-18 `e792743caf5b` | 2026-10-18 `089de63e396a` |
| `src/book/impact.py` | 2026-10-18 `e05f78669e37` | 2026-10-18 `089de63e396a` |
| `src/book/records.py` | 2026-10-18 `e792743caf5b` | 2026-10-18 `089de63e396a` |
| `src/contracts/__init__.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `src/contracts/errors.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `src/contracts/jsonutil.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `src/contracts/validators.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `src/demo/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-14 `53532191798c` |
| `src/demo/pedc-case.json` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-14 `8bb2d81a4a85` |
| `src/demo/pedc.py` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-14 `53532191798c` |
| `src/desk/__init__.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `c7a8c567d89e` |
| `src/desk/answer.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `c7a8c567d89e` |
| `src/desk/bake.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `c7a8c567d89e` |
| `src/desk/gemini.py` | 2026-10-18 `16805f90e5f8` | 2026-10-18 `c7a8c567d89e` |
| `src/desk/live.py` | 2026-10-18 `16805f90e5f8` | 2026-10-18 `e022b7658324` |
| `src/desk/routes.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `e022b7658324` |
| `src/desk/search.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `c7a8c567d89e` |
| `src/desk/words.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `c7a8c567d89e` |
| `src/grid/alerts.css` | 2026-10-17 `c174dfbe82c3` | 2026-10-18 `809840e3db5c` |
| `src/grid/alerts.html` | 2026-10-17 `c174dfbe82c3` | 2026-10-18 `809840e3db5c` |
| `src/grid/alerts.js` | 2026-10-17 `c174dfbe82c3` | 2026-10-19 `ed4e45a409f0` |
| `src/grid/apple-touch-icon.png` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/ask.css` | 2026-10-17 `22674824d51d` | 2026-10-18 `fa9ecf8785c9` |
| `src/grid/ask.html` | 2026-10-17 `22674824d51d` | 2026-10-18 `809840e3db5c` |
| `src/grid/ask.js` | 2026-10-17 `22674824d51d` | 2026-10-18 `809840e3db5c` |
| `src/grid/asset.css` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `src/grid/asset.html` | 2026-10-16 `f13267d32afa` | 2026-10-18 `809840e3db5c` |
| `src/grid/asset.js` | 2026-10-16 `f13267d32afa` | 2026-10-18 `809840e3db5c` |
| `src/grid/assets.html` | 2026-10-16 `f13267d32afa` | 2026-10-18 `809840e3db5c` |
| `src/grid/book.css` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/book.html` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `809840e3db5c` |
| `src/grid/book.js` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/briefs.css` | 2026-10-16 `6e9974a2e6e7` | 2026-10-17 `d0a2ed9ef08a` |
| `src/grid/briefs.js` | 2026-10-16 `6e9974a2e6e7` | 2026-10-18 `809840e3db5c` |
| `src/grid/catalog.css` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `809840e3db5c` |
| `src/grid/catalog.html` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `809840e3db5c` |
| `src/grid/catalog.js` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `809840e3db5c` |
| `src/grid/command.css` | 2026-10-18 `b097f60c2bcb` | 2026-10-19 `169fb23b3a2f` |
| `src/grid/command.js` | 2026-10-18 `b097f60c2bcb` | 2026-10-19 `146a502a6fda` |
| `src/grid/dash-alerts.js` | 2026-10-18 `91707f3dfb6c` | 2026-10-18 `933692b5cca4` |
| `src/grid/dash-map.js` | 2026-10-18 `a7fc74a5cc8b` | 2026-10-18 `47b9ec807438` |
| `src/grid/dashboard.css` | 2026-10-18 `91707f3dfb6c` | 2026-10-19 `d3784d9bc411` |
| `src/grid/event-api.js` | 2026-10-14 `d812d416732d` | 2026-10-18 `933692b5cca4` |
| `src/grid/event-desk.css` | 2026-10-18 `d8165059d831` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/event-desk.js` | 2026-10-18 `d8165059d831` | 2026-10-18 `061078f367fc` |
| `src/grid/event.css` | 2026-10-14 `d812d416732d` | 2026-10-18 `061078f367fc` |
| `src/grid/event.html` | 2026-10-14 `d812d416732d` | 2026-10-18 `db5cb5cfc78f` |
| `src/grid/event.js` | 2026-10-14 `d812d416732d` | 2026-10-18 `061078f367fc` |
| `src/grid/explain.css` | 2026-10-15 `c3587c7d405b` | 2026-10-18 `809840e3db5c` |
| `src/grid/explain.html` | 2026-10-15 `c3587c7d405b` | 2026-10-19 `2262f4899cad` |
| `src/grid/explain.js` | 2026-10-15 `c3587c7d405b` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/favicon.ico` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/favicon.svg` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/firebase-app-compat.js` | 2026-10-17 `c174dfbe82c3` | 2026-10-17 `87b8fd069ef6` |
| `src/grid/firebase-auth-compat.js` | 2026-10-17 `c174dfbe82c3` | 2026-10-17 `87b8fd069ef6` |
| `src/grid/flow.css` | 2026-10-18 `089de63e396a` | 2026-10-18 `809840e3db5c` |
| `src/grid/flow.js` | 2026-10-18 `089de63e396a` | 2026-10-18 `809840e3db5c` |
| `src/grid/fonts/OFL-IBMPlex.txt` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/OFL-Inter.txt` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/ibm-plex-mono-latin-400-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/ibm-plex-mono-latin-500-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-400-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-500-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-600-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-ext-400-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-ext-500-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/fonts/inter-latin-ext-600-normal.woff2` | 2026-10-14 `0d6b5fdcd395` | 2026-10-14 `0307e48fac96` |
| `src/grid/grid.css` | 2026-10-14 `0d6b5fdcd395` | 2026-10-19 `c140f7ecf15f` |
| `src/grid/grid.js` | 2026-10-14 `0d6b5fdcd395` | 2026-10-19 `d3784d9bc411` |
| `src/grid/icon-192.png` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/icon-512.png` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/icon-maskable-512.png` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/index.html` | 2026-10-14 `0d6b5fdcd395` | 2026-10-18 `809840e3db5c` |
| `src/grid/ingrid-logo.svg` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/ingrid-mark.svg` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/journal-box.js` | 2026-10-18 `afcccae4599c` | 2026-10-18 `809840e3db5c` |
| `src/grid/journal.css` | 2026-10-18 `afcccae4599c` | 2026-10-18 `809840e3db5c` |
| `src/grid/journal.html` | 2026-10-18 `afcccae4599c` | 2026-10-18 `809840e3db5c` |
| `src/grid/journal.js` | 2026-10-18 `afcccae4599c` | 2026-10-18 `809840e3db5c` |
| `src/grid/map.css` | 2026-10-16 `a26a3b6b9e81` | 2026-10-19 `c140f7ecf15f` |
| `src/grid/map.html` | 2026-10-17 `22674824d51d` | 2026-10-19 `40fc1778b1b1` |
| `src/grid/map.js` | 2026-10-16 `a26a3b6b9e81` | 2026-10-19 `c140f7ecf15f` |
| `src/grid/models.css` | 2026-10-17 `22674824d51d` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/models.html` | 2026-10-17 `22674824d51d` | 2026-10-18 `809840e3db5c` |
| `src/grid/models.js` | 2026-10-17 `22674824d51d` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/notices.css` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/notices.html` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/notices.js` | 2026-10-18 `7b84e0acd431` | 2026-10-19 `5dbfde79a9af` |
| `src/grid/outages.css` | 2026-10-18 `90aee9e829ba` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/outages.js` | 2026-10-18 `90aee9e829ba` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/outlooks.css` | 2026-10-17 `5c4353539151` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/outlooks.html` | 2026-10-17 `5c4353539151` | 2026-10-18 `809840e3db5c` |
| `src/grid/outlooks.js` | 2026-10-17 `5c4353539151` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/overview.css` | 2026-10-18 `2153ce0dc47b` | 2026-10-19 `c140f7ecf15f` |
| `src/grid/overview.js` | 2026-10-18 `2153ce0dc47b` | 2026-10-19 `c140f7ecf15f` |
| `src/grid/paper.css` | 2026-10-17 `6de9789caa8c` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/paper.html` | 2026-10-17 `6de9789caa8c` | 2026-10-19 `2262f4899cad` |
| `src/grid/projectmap.css` | 2026-10-18 `c3786d7716c8` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/reading.js` | 2026-10-18 `c3786d7716c8` | 2026-10-18 `809840e3db5c` |
| `src/grid/register.css` | 2026-10-17 `d99d3037b2ab` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/register.html` | 2026-10-17 `d99d3037b2ab` | 2026-10-18 `809840e3db5c` |
| `src/grid/register.js` | 2026-10-17 `d99d3037b2ab` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/settings.css` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/settings.html` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/shell.css` | 2026-10-18 `b6cbc0210a0c` | 2026-10-19 `4eb8a492a197` |
| `src/grid/shell.js` | 2026-10-18 `b6cbc0210a0c` | 2026-10-19 `4eb8a492a197` |
| `src/grid/site.webmanifest` | 2026-10-18 `5ef60936b6f6` | 2026-10-18 `b22c44a717f8` |
| `src/grid/spike.css` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/spike.html` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/spike.js` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `809840e3db5c` |
| `src/grid/ui.css` | 2026-10-18 `1eb7d11b4b79` | 2026-10-18 `809840e3db5c` |
| `src/grid/ui.js` | 2026-10-18 `1eb7d11b4b79` | 2026-10-18 `809840e3db5c` |
| `src/grid/work.css` | 2026-10-17 `22674824d51d` | 2026-10-18 `11bf3bb12e88` |
| `src/grid/work.html` | 2026-10-17 `22674824d51d` | 2026-10-18 `809840e3db5c` |
| `src/grid/work.js` | 2026-10-17 `22674824d51d` | 2026-10-18 `11bf3bb12e88` |
| `src/journal/__init__.py` | 2026-10-18 `afcccae4599c` | 2026-10-18 `5d85ee50358a` |
| `src/journal/model.py` | 2026-10-18 `afcccae4599c` | 2026-10-18 `5d85ee50358a` |
| `src/journal/routes.py` | 2026-10-18 `afcccae4599c` | 2026-10-18 `5d85ee50358a` |
| `src/journal/service.py` | 2026-10-18 `afcccae4599c` | 2026-10-18 `5d85ee50358a` |
| `src/journal/store.py` | 2026-10-18 `afcccae4599c` | 2026-10-18 `5d85ee50358a` |
| `src/judgment/README.md` | 2026-10-06 `f3c796287090` | 2026-10-14 `7b949424588a` |
| `src/judgment/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `src/judgment/actions.py` | 2026-10-18 `b2718e7bc073` | 2026-10-18 `11bf3bb12e88` |
| `src/judgment/bundle.py` | 2026-10-11 `8fad260d7955` | 2026-10-14 `fde1477e61ce` |
| `src/judgment/systemone.py` | 2026-10-11 `d69dcbe27b4d` | 2026-10-13 `f4a8366d4f47` |
| `src/judgment/view.py` | 2026-10-17 `dc7c923fef91` | 2026-10-18 `089de63e396a` |
| `src/modeling/__init__.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `src/modeling/errors.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `src/modeling/evaluation.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `src/modeling/providers.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `src/modeling/records.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `src/outlook/__init__.py` | 2026-10-16 `df35a11872c1` | 2026-10-16 `a19f25a45a97` |
| `src/outlook/dependency.py` | 2026-10-16 `754daceccc6f` | 2026-10-17 `4a141ec794b5` |
| `src/outlook/records.py` | 2026-10-16 `df35a11872c1` | 2026-10-18 `089de63e396a` |
| `src/outlook/register.py` | 2026-10-16 `275a49565eb7` | 2026-10-16 `a19f25a45a97` |
| `src/outlook/reissue.py` | 2026-10-18 `f4a9c45d1c99` | 2026-10-18 `089de63e396a` |
| `src/outlook/scoring.py` | 2026-10-17 `a201d7891d5f` | 2026-10-17 `b48d5ba42323` |
| `src/price/__init__.py` | 2026-10-16 `9d343aade9d2` | 2026-10-17 `e179472b8632` |
| `src/price/availability.py` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `src/price/baselines.py` | 2026-10-16 `9d343aade9d2` | 2026-10-16 `a19f25a45a97` |
| `src/price/challengers.py` | 2026-10-16 `526464ecc2fa` | 2026-10-17 `7605484e2f48` |
| `src/price/fuel.py` | 2026-10-17 `244716270ca6` | 2026-10-17 `7605484e2f48` |
| `src/price/impact.py` | 2026-10-16 `35264df94616` | 2026-10-17 `b8b2096c87f5` |
| `src/price/response.py` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `src/price/scorecard.py` | 2026-10-16 `9d343aade9d2` | 2026-10-17 `e179472b8632` |
| `src/price/series.py` | 2026-10-16 `9d343aade9d2` | 2026-10-16 `a19f25a45a97` |
| `src/regulatory/README.md` | 2026-10-16 `cbf62f549ecd` | 2026-10-16 `9ba846dce8e1` |
| `src/regulatory/__init__.py` | 2026-10-05 `363abe438040` | 2026-10-05 `6e8ad519e664` |
| `src/regulatory/grammars.py` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `src/regulatory/lineage.py` | 2026-10-16 `70c1a16aa596` | 2026-10-16 `9ba846dce8e1` |
| `src/regulatory/structure.py` | 2026-10-05 `363abe438040` | 2026-10-05 `6e8ad519e664` |
| `src/review/README.md` | 2026-10-05 `818de084c67f` | 2026-10-15 `4a51e36d20b3` |
| `src/review/__init__.py` | 2026-10-05 `818de084c67f` | 2026-10-05 `818de084c67f` |
| `src/review/errors.py` | 2026-10-05 `818de084c67f` | 2026-10-14 `058a970b211f` |
| `src/review/pairing.py` | 2026-10-12 `88e0cfd51ff1` | 2026-10-13 `df716a32d771` |
| `src/review/records.py` | 2026-10-05 `818de084c67f` | 2026-10-14 `058a970b211f` |
| `src/review/repository.py` | 2026-10-05 `818de084c67f` | 2026-10-15 `4a51e36d20b3` |
| `src/review/storage.py` | 2026-10-05 `8e0583bb6750` | 2026-10-15 `4a51e36d20b3` |
| `src/workspace/README.md` | 2026-10-06 `f3c796287090` | 2026-10-14 `7b949424588a` |
| `src/workspace/app.js` | 2026-10-06 `f3c796287090` | 2026-10-14 `6cf7b82dc82c` |
| `src/workspace/index.html` | 2026-10-06 `f3c796287090` | 2026-10-19 `ed4e45a409f0` |
| `src/workspace/style.css` | 2026-10-06 `f3c796287090` | 2026-10-14 `2ca63f8f0b95` |
| `tests/fixtures/book/book-v1.json` | 2026-10-18 `e792743caf5b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/outlooks/book-demo-2026-10-19-cluz.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/outlooks/book-demo-2026-10-19-cmin.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/outlooks/book-demo-2026-10-19-cvis-v2.json` | 2026-10-18 `2489ef21946f` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/outlooks/book-demo-2026-10-19-cvis.json` | 2026-10-18 `2489ef21946f` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/values/book-demo-2026-10-19-cluz.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/values/book-demo-2026-10-19-cmin.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/values/book-demo-2026-10-19-cvis-v2.json` | 2026-10-18 `2489ef21946f` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/book/vintages/values/book-demo-2026-10-19-cvis.json` | 2026-10-18 `2489ef21946f` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/contracts/dataset_snapshot.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/contracts/duplicate_key.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/contracts/malformed.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/contracts/non_finite.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/contracts/prediction_artifact.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/contracts/provision_candidate.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/corpus/README.md` | 2026-10-16 `03ec7668b441` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/extract/README.md` | 2026-10-16 `7f98e5755862` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/extract/synthetic-notice.txt` | 2026-10-16 `7f98e5755862` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/extract/synthetic-response.json` | 2026-10-16 `7f98e5755862` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/retrieve/README.md` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/archive.bin` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/documents/Synthetic_Alpha_Manual_1.0_final.txt` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/documents/Synthetic_Beta_Manual_2.0_final.txt` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/documents/Synthetic_Delta_Manual_05Mar2026_final.txt` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/documents/Synthetic_Epsilon_Manual_1.0_final.txt` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/documents/Synthetic_Gamma_Notes_final.txt` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/retrieve/register.json` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/corpus/store/README.md` | 2026-10-16 `2cf576ed102e` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/store/build.py` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/store/reserve-market.json` | 2026-10-16 `c5583eb91929` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/corpus/synthetic-listing.html` | 2026-10-16 `03ec7668b441` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/decision-system-v1/case.json` | 2026-10-04 `af242f8b0680` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/explainer/browser.mjs` | 2026-10-15 `c3587c7d405b` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/README.md` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/alerts/browser.mjs` | 2026-10-17 `881bb4b519cc` | 2026-10-18 `11bf3bb12e88` |
| `tests/fixtures/grid/alerts/serve.py` | 2026-10-17 `c174dfbe82c3` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/asset/README.md` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/asset/build.py` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/geo/crosswalk.csv` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/geo/sites.csv` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/payload/assets/03LUZ.json` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/payload/assets/04GEN.json` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/payload/assets/08PEDC.json` | 2026-10-16 `f13267d32afa` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/asset/payload/assets/08PLACE.json` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/asset/payload/assets/08SAMPLE.json` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/asset/payload/assets/index.json` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/asset/render.mjs` | 2026-10-16 `f13267d32afa` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/book/bake/book/exposure.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/book/bake/book/index.json` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/book/browser.mjs` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/briefs/README.md` | 2026-10-16 `6e9974a2e6e7` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/briefs/bake/advisories.json` | 2026-10-16 `6e9974a2e6e7` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/briefs/bake/events.json` | 2026-10-16 `6e9974a2e6e7` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/briefs/bake/hvdc.json` | 2026-10-16 `6e9974a2e6e7` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/briefs/bake/regions.json` | 2026-10-16 `6e9974a2e6e7` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/briefs/panel-harness.mjs` | 2026-10-16 `aa7dd2c9de86` | 2026-10-17 `d0a2ed9ef08a` |
| `tests/fixtures/grid/catalog/README.md` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/catalog/ask-render.mjs` | 2026-10-17 `7a0f83d3184c` | 2026-10-18 `809840e3db5c` |
| `tests/fixtures/grid/catalog/bake/advisories.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/advisories/2026-09.json` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/catalog/bake/days/2026-09-21.json` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/catalog/bake/events.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/events/syn-bay-unit-2-trip.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-17 `7f3ad083a04e` |
| `tests/fixtures/grid/catalog/bake/hvdc.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/nodes-2026-09-21.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/ontology/sample-event-2026-09-21.json` | 2026-10-17 `dd24e0d5ced1` | 2026-10-17 `538fef5bd6f1` |
| `tests/fixtures/grid/catalog/bake/outlook/index.json` | 2026-10-17 `5c4353539151` | 2026-10-17 `afe0c7a38db1` |
| `tests/fixtures/grid/catalog/bake/outlook/sample-event-2026-09-21.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/catalog/bake/ph.geojson` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/regions.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/register/index.json` | 2026-10-17 `d99d3037b2ab` | 2026-10-17 `2141d440714a` |
| `tests/fixtures/grid/catalog/bake/replay.json` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/catalog/bake/sites.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `47b9ec807438` |
| `tests/fixtures/grid/catalog/bake/vectors.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/bake/views/ask.json` | 2026-10-17 `7a0f83d3184c` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/bake/views/home.json` | 2026-10-17 `e6f08998555d` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/bake/views/index.json` | 2026-10-17 `e6f08998555d` | 2026-10-18 `da14c4705446` |
| `tests/fixtures/grid/catalog/bake/views/models.json` | 2026-10-17 `7a0f83d3184c` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/bake/views/outlooks.json` | 2026-10-17 `7a0f83d3184c` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/bake/views/register.json` | 2026-10-17 `7a0f83d3184c` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/bake/views/syn-bay-unit-2-trip.json` | 2026-10-17 `e6f08998555d` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/catalog/browser.mjs` | 2026-10-18 `e70993e996e2` | 2026-10-18 `b39fc7d6813d` |
| `tests/fixtures/grid/catalog/build.py` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/catalog/inputs/events/syn-bay-unit-2-trip.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/inputs/spike.json` | 2026-10-16 `2c7ea6e292e4` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/catalog/render.mjs` | 2026-10-16 `2c7ea6e292e4` | 2026-10-18 `933692b5cca4` |
| `tests/fixtures/grid/catalog/v3/views/ask.json` | 2026-10-18 `c7899ca46b93` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/desk-1-view-two-targets.json` | 2026-10-17 `cf4e7c6f2da1` | 2026-10-17 `b8b2096c87f5` |
| `tests/fixtures/grid/desk-1-view.json` | 2026-10-17 `dd93c24c8a2e` | 2026-10-17 `b8b2096c87f5` |
| `tests/fixtures/grid/event/README.md` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/event/build.py` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/event/flow.json` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-15 `4a51e36d20b3` |
| `tests/fixtures/grid/event/legacy-cards.html` | 2026-10-18 `7b84e0acd431` | 2026-10-18 `edfbaf46d3a1` |
| `tests/fixtures/grid/event/outlook.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/event/render.mjs` | 2026-10-14 `35d649b23d0c` | 2026-10-18 `db5cb5cfc78f` |
| `tests/fixtures/grid/event/reserve-market/view.json` | 2026-10-16 `97c179100ca4` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/grid/event/retrieval/view.json` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/grid/event/rules-in-force/build.py` | 2026-10-16 `cd9f68576aa6` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/grid/event/rules-in-force/evidence-manifest.json` | 2026-10-16 `cd9f68576aa6` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/grid/event/rules-in-force/view.json` | 2026-10-16 `cd9f68576aa6` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/grid/event/run.mjs` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-15 `4a51e36d20b3` |
| `tests/fixtures/grid/event/view.json` | 2026-10-14 `4f29b1a9b4b2` | 2026-10-14 `8bb2d81a4a85` |
| `tests/fixtures/grid/events.json` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/geo/crosswalk.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/geo/ph.geojson` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/geo/sites.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/map/README.md` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/build.py` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/advisories.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/events.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/hvdc.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/nodes-2026-09-21.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/ph.geojson` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/regions.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/data/sites.json` | 2026-10-16 `a26a3b6b9e81` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/map/harness.mjs` | 2026-10-16 `a26a3b6b9e81` | 2026-10-18 `11bf3bb12e88` |
| `tests/fixtures/grid/models/summary.mjs` | 2026-10-17 `4994eafe36ab` | 2026-10-18 `ed88d7aee791` |
| `tests/fixtures/grid/monitor/browser.mjs` | 2026-10-18 `554080094e1d` | 2026-10-18 `11bf3bb12e88` |
| `tests/fixtures/grid/outages/README.md` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outages/bake/advisories.json` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outages/bake/events.json` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outages/bake/regions.json` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outages/bake/sites.json` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outages/export.json` | 2026-10-18 `b00ddf1297da` | 2026-10-18 `27f9c4ec584f` |
| `tests/fixtures/grid/outlook/archive/outlooks/outlook-fixture-2026-11-system.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/outlook/archive/stale/951810a004d88fe4f2496b5d85bc50937bc4013e3c055477cfb48fd4c9078610.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/outlook/build.py` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/outlook/register.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/outlooks/browser.mjs` | 2026-10-17 `5c4353539151` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/page/README.md` | 2026-10-14 `2abec1625fa7` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/page/browser.mjs` | 2026-10-14 `2abec1625fa7` | 2026-10-19 `d3784d9bc411` |
| `tests/fixtures/grid/page/build.py` | 2026-10-14 `2abec1625fa7` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/page/data/advisories.json` | 2026-10-14 `2abec1625fa7` | 2026-10-15 `c0da37badc90` |
| `tests/fixtures/grid/page/data/briefs.json` | 2026-10-16 `eb2921ac6fd0` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/page/data/events.json` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/data/findings.json` | 2026-10-16 `eb2921ac6fd0` | 2026-10-16 `0fccc3d2f4a2` |
| `tests/fixtures/grid/page/data/hvdc.json` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/data/nodes-2026-09-21.json` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/data/ontology/fixture-rules-in-force.json` | 2026-10-17 `dd24e0d5ced1` | 2026-10-17 `538fef5bd6f1` |
| `tests/fixtures/grid/page/data/ontology/reserve-market-2026-10-14.json` | 2026-10-17 `dd24e0d5ced1` | 2026-10-17 `538fef5bd6f1` |
| `tests/fixtures/grid/page/data/ontology/syn-bay-unit-2-trip.json` | 2026-10-17 `dd24e0d5ced1` | 2026-10-17 `538fef5bd6f1` |
| `tests/fixtures/grid/page/data/outlook/fixture-rules-in-force.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/page/data/outlook/reserve-market-2026-10-14.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/page/data/outlook/syn-bay-unit-2-trip.json` | 2026-10-17 `c9b43216c00c` | 2026-10-17 `9715125f46d8` |
| `tests/fixtures/grid/page/data/ph.geojson` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/data/regions.json` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/data/sites.json` | 2026-10-14 `2abec1625fa7` | 2026-10-14 `0307e48fac96` |
| `tests/fixtures/grid/page/render.mjs` | 2026-10-14 `2abec1625fa7` | 2026-10-18 `11bf3bb12e88` |
| `tests/fixtures/grid/page/views/events/syn-bay-unit-2-trip.json` | 2026-10-15 `ea7e1f6a4eb7` | 2026-10-15 `adf520642fcb` |
| `tests/fixtures/grid/page/views/vectors.json` | 2026-10-15 `ade0ca8ddf43` | 2026-10-15 `c0da37badc90` |
| `tests/fixtures/grid/plants/README.md` | 2026-10-18 `47064695d308` | 2026-10-18 `71e82c7da6ee` |
| `tests/fixtures/grid/plants/advisories.json` | 2026-10-18 `47064695d308` | 2026-10-18 `71e82c7da6ee` |
| `tests/fixtures/grid/plants/events.json` | 2026-10-18 `47064695d308` | 2026-10-18 `71e82c7da6ee` |
| `tests/fixtures/grid/plants/outages.json` | 2026-10-18 `47064695d308` | 2026-10-18 `71e82c7da6ee` |
| `tests/fixtures/grid/plants/sites.json` | 2026-10-18 `47064695d308` | 2026-10-18 `71e82c7da6ee` |
| `tests/fixtures/grid/register/browser.mjs` | 2026-10-17 `d99d3037b2ab` | 2026-10-18 `b22c44a717f8` |
| `tests/fixtures/grid/shell/browser.mjs` | 2026-10-18 `ce97df8470e6` | 2026-10-18 `809840e3db5c` |
| `tests/fixtures/grid/snapshot/advisories.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/snapshot/hvdc_5min.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/snapshot/nodes_0921_5min.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/snapshot/regions_5min.csv` | 2026-10-14 `7a7b36c49772` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/grid/ui/browser.mjs` | 2026-10-18 `e3f37089b9d7` | 2026-10-18 `fa9ecf8785c9` |
| `tests/fixtures/grid/ui/kitchen-sink.html` | 2026-10-18 `e3f37089b9d7` | 2026-10-18 `809840e3db5c` |
| `tests/fixtures/grid/ui/kitchen-sink.js` | 2026-10-18 `e3f37089b9d7` | 2026-10-18 `d55dae74a576` |
| `tests/fixtures/modeling/synthetic_multi_season.json` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/modeling/synthetic_two_origin.json` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `tests/fixtures/pedc-u2-2026-09-21/README.md` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/pedc-u2-2026-09-21/build.py` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/pedc-u2-2026-09-21/case.json` | 2026-10-14 `6c691d73781a` | 2026-10-14 `51dadb71f966` |
| `tests/fixtures/price/event_study/demand_hourly-synthetic.csv` | 2026-10-18 `8a9c8fe9f667` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/lwap_final_hourly-synthetic.csv` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/make_synthetic.py` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/out3/demand_hourly-synthetic.csv` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/out3/known_outages-synthetic.csv` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/out3/make_out3_synthetic.py` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/out3/response-synthetic.json` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/out3/synthetic-label.json` | 2026-10-18 `ace3efbe9e3b` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/outages_forced-synthetic.csv` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/prices_interval_shape-synthetic.csv` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/rtd_regional_prices-realtime-synthetic.csv` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/price/event_study/synthetic-label.json` | 2026-10-18 `2ff672ae6c05` | 2026-10-18 `089de63e396a` |
| `tests/fixtures/probe-bundle/README.md` | 2026-10-11 `c98a2a3f22f6` | 2026-10-12 `b02fb4a008af` |
| `tests/fixtures/probe-bundle/annotation-policy.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/build.py` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/manifest.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cl-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cl-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-cl-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-er-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-er-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-er-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-er-4.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-lc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-lc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-lc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-na-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-na-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-na-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-ng-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-ng-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-ng-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-po-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-po-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-po-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-tc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-tc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/probe-bundle/pb-tc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-14 `fde1477e61ce` |
| `tests/fixtures/regulatory/excerpts.json` | 2026-10-16 `bfd643fd6f0a` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_crlf.txt` | 2026-10-05 `363abe438040` | 2026-10-05 `6e8ad519e664` |
| `tests/fixtures/regulatory/synthetic_doe_circular.txt` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_erc_resolution.txt` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_lf.txt` | 2026-10-05 `363abe438040` | 2026-10-05 `6e8ad519e664` |
| `tests/fixtures/regulatory/synthetic_market_manual.txt` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_rule_amendment.txt` | 2026-10-16 `70c1a16aa596` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_rule_base.txt` | 2026-10-16 `70c1a16aa596` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/regulatory/synthetic_wesm_rules.txt` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `tests/fixtures/review/case.json` | 2026-10-05 `818de084c67f` | 2026-10-05 `818de084c67f` |
| `tests/fixtures/wesm/README.md` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `tests/fixtures/wesm/advisories-sample.jsonl` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `tests/fixtures/wesm/registry-pedc-sample.jsonl` | 2026-10-13 `f655bdaa2027` | 2026-10-14 `d5cef3622966` |
| `tests/integration/test_gemini_wire.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `tests/integration/test_h1.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `tests/integration/test_m3.py` | 2026-10-06 `f3c796287090` | 2026-10-18 `809840e3db5c` |
| `tests/integration/test_probe_bundle_api.py` | 2026-10-11 `d69dcbe27b4d` | 2026-10-14 `fde1477e61ce` |
| `tests/test_agent_fakes.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `tests/test_agent_store.py` | 2026-10-18 `fbbce64374b1` | 2026-10-18 `089de63e396a` |
| `tests/test_alert_notices.py` | 2026-10-18 `0929fb54ec8c` | 2026-10-18 `933692b5cca4` |
| `tests/test_alerts.py` | 2026-10-17 `1dc8bb1f06bb` | 2026-10-19 `ed4e45a409f0` |
| `tests/test_alerts_desk.py` | 2026-10-18 `8080f2ac9b06` | 2026-10-18 `933692b5cca4` |
| `tests/test_alerts_ontology.py` | 2026-10-18 `0929fb54ec8c` | 2026-10-18 `933692b5cca4` |
| `tests/test_artifact_contracts.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `f2ea4e85e4df` |
| `tests/test_book_exposure.py` | 2026-10-18 `e05f78669e37` | 2026-10-18 `089de63e396a` |
| `tests/test_book_impact.py` | 2026-10-18 `e05f78669e37` | 2026-10-18 `089de63e396a` |
| `tests/test_book_views.py` | 2026-10-18 `54f8940ba91c` | 2026-10-18 `089de63e396a` |
| `tests/test_brand_assets.py` | 2026-10-18 `cbbf4be9778b` | 2026-10-18 `b22c44a717f8` |
| `tests/test_cutoff_rewind.py` | 2026-10-18 `4bca5ccefad0` | 2026-10-18 `933692b5cca4` |
| `tests/test_demo_session_batch.py` | 2026-10-14 `aa20f4270924` | 2026-10-14 `53532191798c` |
| `tests/test_desk_api.py` | 2026-10-18 `36b4fd32381c` | 2026-10-18 `47b9ec807438` |
| `tests/test_gemini_transport.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `dc5ad0071b14` |
| `tests/test_grid_book_page.py` | 2026-10-18 `28c1d0ab681a` | 2026-10-18 `809840e3db5c` |
| `tests/test_grid_dashboard.py` | 2026-10-18 `91707f3dfb6c` | 2026-10-18 `47b9ec807438` |
| `tests/test_grid_event_desk.py` | 2026-10-18 `d8165059d831` | 2026-10-18 `edfbaf46d3a1` |
| `tests/test_grid_event_drivers.py` | 2026-10-17 `ee7f01eb40dc` | 2026-10-18 `7b84e0acd431` |
| `tests/test_grid_flow.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `11bf3bb12e88` |
| `tests/test_grid_map.py` | 2026-10-16 `a26a3b6b9e81` | 2026-10-18 `47b9ec807438` |
| `tests/test_grid_notices.py` | 2026-10-18 `64999cbe9f97` | 2026-10-19 `2262f4899cad` |
| `tests/test_grid_overview.py` | 2026-10-18 `2153ce0dc47b` | 2026-10-19 `c140f7ecf15f` |
| `tests/test_grid_plants.py` | 2026-10-18 `47064695d308` | 2026-10-18 `11bf3bb12e88` |
| `tests/test_grid_shell.py` | 2026-10-18 `ce97df8470e6` | 2026-10-19 `5dbfde79a9af` |
| `tests/test_hosted_config.py` | 2026-10-12 `0a5c4851a367` | 2026-10-18 `809840e3db5c` |
| `tests/test_judgment.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `tests/test_modeling_baselines.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `f2ea4e85e4df` |
| `tests/test_ontology_phrase_cache.py` | 2026-10-18 `089de63e396a` | 2026-10-18 `089de63e396a` |
| `tests/test_ontology_phrase_card.py` | 2026-10-17 `affeddd93966` | 2026-10-17 `83091d0055cd` |
| `tests/test_outlook_attribution.py` | 2026-10-17 `158b03fd7373` | 2026-10-18 `089de63e396a` |
| `tests/test_outlook_dependency.py` | 2026-10-16 `754daceccc6f` | 2026-10-17 `4a141ec794b5` |
| `tests/test_outlook_records.py` | 2026-10-16 `df35a11872c1` | 2026-10-17 `4a141ec794b5` |
| `tests/test_outlook_reissue.py` | 2026-10-18 `f4a9c45d1c99` | 2026-10-18 `089de63e396a` |
| `tests/test_outlook_scoring.py` | 2026-10-17 `a201d7891d5f` | 2026-10-18 `089de63e396a` |
| `tests/test_pairing.py` | 2026-10-12 `88e0cfd51ff1` | 2026-10-14 `2ca63f8f0b95` |
| `tests/test_paper_page.py` | 2026-10-17 `6de9789caa8c` | 2026-10-18 `11bf3bb12e88` |
| `tests/test_price_baselines.py` | 2026-10-16 `9d343aade9d2` | 2026-10-18 `089de63e396a` |
| `tests/test_price_challengers.py` | 2026-10-16 `526464ecc2fa` | 2026-10-17 `e179472b8632` |
| `tests/test_price_impact.py` | 2026-10-16 `35264df94616` | 2026-10-17 `b8b2096c87f5` |
| `tests/test_probe_bundle.py` | 2026-10-11 `8fad260d7955` | 2026-10-14 `fde1477e61ce` |
| `tests/test_regulatory_grammars.py` | 2026-10-16 `58901961ebeb` | 2026-10-16 `9ba846dce8e1` |
| `tests/test_regulatory_lineage.py` | 2026-10-16 `70c1a16aa596` | 2026-10-16 `9ba846dce8e1` |
| `tests/test_regulatory_structure.py` | 2026-10-05 `363abe438040` | 2026-10-05 `6e8ad519e664` |
| `tests/test_repo.py` | 2026-10-03 `77f2895235c8` | 2026-10-17 `621498d64e96` |
| `tests/test_review_case.py` | 2026-10-05 `818de084c67f` | 2026-10-14 `fde1477e61ce` |
| `tests/test_systemone_adapters.py` | 2026-10-12 `1f50a20c5e69` | 2026-10-14 `fde1477e61ce` |
| `tests/test_transport_permission.py` | 2026-10-16 `27dd1b60be7e` | 2026-10-18 `089de63e396a` |
| `tests/test_whatif.py` | 2026-10-12 `8b2c230e4c8e` | 2026-10-13 `1d46182f9bab` |

## Generated export files

| File | Content source | First commit | Last commit |
|---|---|---|---|
| `README.md` | `scripts/release/clean-install.md` at the audited revision | 2026-10-11 `7bc88a976071` | 2026-10-19 `40fc1778b1b1` |
| `PROVENANCE.md` | written by this tool from the audit of the audited revision | — `—` | — `—` |
| `EXPORT-AUDIT.json` | machine-readable record of this audit, written by this tool | — `—` | — `—` |

## Content-scan notes and reviewed exceptions

- reviewed exception: docs/work/permissions/2026-10-13-wesm-company-copy.md matches gcs-location at line(s) [13, 16]; each of the 2 match(es) hashes to a reviewed digest — Reviewed 2026-10-18 (POLISH-2, owner input 2, option a): the signed permission record of the WESM company copy names the two Cloud Storage bucket locations of its dataset table at lines 13 and 16; the owner's board note says the record can be published, a signed record is never edited, the review core needs it for every real record (src/review/records.py) and the Dockerfile copies it into the served image. Each digest above is sha256 of the exact matched text (export.py's documented rule, recomputed independently in the POLISH-2 phase-2 report). The exception covers those two values only: a changed or added location changes a digest and stops the export until it is reviewed anew.
- reviewed exception: src/demo/__init__.py matches credential-assignment at line(s) [6]; each of the 1 match(es) hashes to a reviewed digest — Reviewed 2026-10-11: the single hit is the literal placeholder constant of the labelled fictional seed used by the local walkthrough and its tests, and the digest above is sha256 of that exact matched text. It is a synthetic value in a synthetic-only module, not a credential. The exception covers that content only: replacing it with anything else — even at the same hit count — changes a digest and stops the export until the new content is reviewed.
- reviewed binary: src/grid/apple-touch-icon.png is not UTF-8 text, so the content rules cannot read it, and its 2564 bytes hash to a reviewed digest — Reviewed 2026-10-18 for the InGRID brand (platform-polish batch): a raster icon drawn by scripts/brand/build_icons.py from the SVG mark in src/grid (favicon.svg, ingrid-mark.svg), which the content rules do read. The PNG and ICO bytes are pinned by sha256; a redraw changes the digest and stops the export until the new bytes are reviewed. No data, text or credential is inside: the tile colours are the shell tokens and the mark is the 3x3 trace path.
- reviewed binary: src/grid/favicon.ico is not UTF-8 text, so the content rules cannot read it, and its 2503 bytes hash to a reviewed digest — Reviewed 2026-10-18 for the InGRID brand (platform-polish batch): a raster icon drawn by scripts/brand/build_icons.py from the SVG mark in src/grid (favicon.svg, ingrid-mark.svg), which the content rules do read. The PNG and ICO bytes are pinned by sha256; a redraw changes the digest and stops the export until the new bytes are reviewed. No data, text or credential is inside: the tile colours are the shell tokens and the mark is the 3x3 trace path.
- reviewed binary: src/grid/fonts/ibm-plex-mono-latin-400-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 14812 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/ibm-plex-mono-latin-500-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 14988 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-400-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 23692 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-500-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 24368 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-600-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 24304 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-ext-400-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 30676 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-ext-500-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 31760 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/fonts/inter-latin-ext-600-normal.woff2 is not UTF-8 text, so the content rules cannot read it, and its 31968 bytes hash to a reviewed digest — Reviewed 2026-10-14 for GRID-2: the grid desk vendors its own faces so the content security policy can stay 'self' with no CDN. The eight woff2 files are Inter (latin and latin-ext, weights 400/500/600) and IBM Plex Mono (latin, 400/500) — the SIL Open Font License text for each is beside them in fonts/OFL-Inter.txt and fonts/OFL-IBMPlex.txt. A font is a binary, so the content rules cannot read it; each file is pinned by the sha256 of its whole content instead. Adding a face, replacing one, or removing a pinned one changes or strands a digest and stops the export until the new bytes are reviewed.
- reviewed binary: src/grid/icon-192.png is not UTF-8 text, so the content rules cannot read it, and its 4446 bytes hash to a reviewed digest — Reviewed 2026-10-18 for the InGRID brand (platform-polish batch): a raster icon drawn by scripts/brand/build_icons.py from the SVG mark in src/grid (favicon.svg, ingrid-mark.svg), which the content rules do read. The PNG and ICO bytes are pinned by sha256; a redraw changes the digest and stops the export until the new bytes are reviewed. No data, text or credential is inside: the tile colours are the shell tokens and the mark is the 3x3 trace path.
- reviewed binary: src/grid/icon-512.png is not UTF-8 text, so the content rules cannot read it, and its 12477 bytes hash to a reviewed digest — Reviewed 2026-10-18 for the InGRID brand (platform-polish batch): a raster icon drawn by scripts/brand/build_icons.py from the SVG mark in src/grid (favicon.svg, ingrid-mark.svg), which the content rules do read. The PNG and ICO bytes are pinned by sha256; a redraw changes the digest and stops the export until the new bytes are reviewed. No data, text or credential is inside: the tile colours are the shell tokens and the mark is the 3x3 trace path.
- reviewed binary: src/grid/icon-maskable-512.png is not UTF-8 text, so the content rules cannot read it, and its 6989 bytes hash to a reviewed digest — Reviewed 2026-10-18 for the InGRID brand (platform-polish batch): a raster icon drawn by scripts/brand/build_icons.py from the SVG mark in src/grid (favicon.svg, ingrid-mark.svg), which the content rules do read. The PNG and ICO bytes are pinned by sha256; a redraw changes the digest and stops the export until the new bytes are reviewed. No data, text or credential is inside: the tile colours are the shell tokens and the mark is the 3x3 trace path.
- worktree: 27 uncommitted path(s) under excluded rules cannot reach the export and did not block it

## Findings

- none

## Not covered by this log

- Rights and IP clearance, the hosted-lane dependency installation and the published
  endpoint are REL-5 items behind GATE-5; this log records source provenance and the
  audit decisions only.
- The audit shows what was filtered and when each included path entered the repository.
  It claims no originality beyond those commit dates.
- First and last commit dates are per path name, so a path that entered the tree by a
  rename or copy is dated by the move, not by the first time its content appeared. The
  blob-level pass catches pre-cutoff content that moved unchanged; content edited after
  such a move keeps the later date, and no commit-date check can date it further.
