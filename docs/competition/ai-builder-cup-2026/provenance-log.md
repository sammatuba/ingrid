# Public export provenance log

Generated 2026-10-12 by `scripts/release/export.py` as part of REL-1 (public export audit). This is the repository copy of the generated log.

- Audited revision: `ce7d2dc4452292c6e97aaa335d48a15ba39aa831` (committed 2026-10-12), branch `task/REL-1`
- Freshness cutoff: 2026-09-07 — the build-window start; first commits before it are excluded
- Allowlist: `scripts/release/allowlist.json`, reviewed 2026-10-11
- Decisions: 628 tracked paths audited, 89 included, 539 excluded, 3 generated export files, 0 findings

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
| `app-source` | 35 |
| `app-tests` | 52 |
| `repository-check-tool` | 1 |
| `dependency-inventory` | 1 |

## Excluded content

| Rule | Paths | Reason |
|---|---|---|
| `agent-config` | 8 | agent skills and repository lifecycle entry points |
| `agent-entry` | 1 | agent entry point linking to excluded internal planning records |
| `campaign-archive` | 53 | historical campaign material from earlier, unrelated work |
| `case-packs` | 9 | analyst case packs pending rights review (GATE-5) |
| `ci-workflow` | 1 | CI runs repository-governance checks whose records this export excludes |
| `codex-config` | 2 | local harness configuration |
| `contribution-guide` | 1 | contribution rules referencing excluded internal records |
| `dashboard-lane` | 5 | dashboard lane reads private GCS data; internal data location and private inputs |
| `dashboard-launcher` | 1 | launcher for the excluded dashboard lane |
| `experiments` | 74 | isolated research and historical proofs of concept; never a runtime dependency |
| `harness-config` | 1 | local harness configuration |
| `harness-instructions` | 1 | harness instructions for the private repository |
| `hosted-lane-scripts` | 8 | hosted-lane project configuration and issue publishing |
| `ignore-rules` | 1 | ignore rules for private and generated paths of the working repository |
| `internal-planning` | 154 | internal planning packets, gate evidence, reviews and progress records |
| `meos-bootstrap` | 1 | MEOS session bootstrap script |
| `meos-state` | 3 | MEOS runtime and session state |
| `plan-tests` | 1 | validates internal plan records that this export excludes |
| `plan-tool` | 1 | internal task-graph tool; reads the excluded plan and progress records |
| `private-data-tools` | 33 | private data pipeline, SQL and analysis over restricted sources |
| `private-readme` | 1 | private working-repository readme; the export writes its own README |
| `public-docs` | 61 | documentation set pending reviewed public release; REL-2 and REL-5 own the public documents |
| `release-audit-tests` | 1 | audits this private repository's history and allowlist; not part of the public application suite |
| `release-tooling` | 3 | release audit tooling and allowlist; publishing them is a REL-5 decision after GATE-5 |
| `repository-metadata` | 1 | repository tooling metadata |
| `research-dossiers` | 93 | third-party research downloads; rights not cleared |
| `research-tools` | 1 | research download helpers |
| `seat-launchers` | 12 | internal model-seat launchers; reference local harnesses and credential environment |
| `workspace-lane-scripts` | 5 | local runner, seeding and browser-check scripts for the internal workspace lane |
| `workspace-preview` | 2 | static interaction reference held for REL-5 review; its README links to product documents this export excludes |

`scripts/release/export.py --dry-run` prints every excluded path with its rule and
reason; this table is the per-rule summary of the same run.

## First and last commit per included path

| Path | First commit | Last commit |
|---|---|---|
| `requirements/h1.lock` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `scripts/repo.py` | 2026-10-03 `77f2895235c8` | 2026-10-04 `562277009a44` |
| `src/README.md` | 2026-10-03 `77f2895235c8` | 2026-10-06 `f3c796287090` |
| `src/adapters/firestore/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `src/adapters/gemini/README.md` | 2026-10-06 `f3c796287090` | 2026-10-11 `c38fb91e8041` |
| `src/adapters/gemini/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `19c25f76598e` |
| `src/adapters/gemini/run.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `19c25f76598e` |
| `src/adapters/gemini/transport.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `19c25f76598e` |
| `src/adapters/gemini/worker.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `19c25f76598e` |
| `src/adapters/identity/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-06 `f3c796287090` |
| `src/api/__init__.py` | 2026-10-05 `8e0583bb6750` | 2026-10-06 `f3c796287090` |
| `src/api/local.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `src/contracts/__init__.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `src/contracts/errors.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `src/contracts/jsonutil.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `src/contracts/validators.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `src/demo/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `src/judgment/README.md` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `src/judgment/__init__.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `src/judgment/bundle.py` | 2026-10-11 `8fad260d7955` | 2026-10-11 `3cd29718f700` |
| `src/modeling/__init__.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `src/modeling/errors.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `src/modeling/evaluation.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `src/modeling/providers.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `src/modeling/records.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `src/regulatory/__init__.py` | 2026-10-05 `363abe438040` | 2026-10-05 `363abe438040` |
| `src/regulatory/structure.py` | 2026-10-05 `363abe438040` | 2026-10-05 `363abe438040` |
| `src/review/README.md` | 2026-10-05 `818de084c67f` | 2026-10-06 `f3c796287090` |
| `src/review/__init__.py` | 2026-10-05 `818de084c67f` | 2026-10-05 `818de084c67f` |
| `src/review/errors.py` | 2026-10-05 `818de084c67f` | 2026-10-05 `818de084c67f` |
| `src/review/records.py` | 2026-10-05 `818de084c67f` | 2026-10-06 `f3c796287090` |
| `src/review/repository.py` | 2026-10-05 `818de084c67f` | 2026-10-06 `f3c796287090` |
| `src/review/storage.py` | 2026-10-05 `8e0583bb6750` | 2026-10-06 `f3c796287090` |
| `src/workspace/README.md` | 2026-10-06 `f3c796287090` | 2026-10-11 `0bc830d9df9c` |
| `src/workspace/app.js` | 2026-10-06 `f3c796287090` | 2026-10-11 `4561f26fc7f0` |
| `src/workspace/index.html` | 2026-10-06 `f3c796287090` | 2026-10-11 `0bc830d9df9c` |
| `src/workspace/style.css` | 2026-10-06 `f3c796287090` | 2026-10-11 `9c8f9be0aa16` |
| `tests/fixtures/contracts/dataset_snapshot.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/contracts/duplicate_key.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/contracts/malformed.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/contracts/non_finite.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/contracts/prediction_artifact.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/contracts/provision_candidate.json` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/fixtures/decision-system-v1/case.json` | 2026-10-04 `af242f8b0680` | 2026-10-04 `af242f8b0680` |
| `tests/fixtures/modeling/synthetic_multi_season.json` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `tests/fixtures/modeling/synthetic_two_origin.json` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `tests/fixtures/probe-bundle/README.md` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `c98a2a3f22f6` |
| `tests/fixtures/probe-bundle/annotation-policy.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `c98a2a3f22f6` |
| `tests/fixtures/probe-bundle/build.py` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/manifest.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cl-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cl-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-cl-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-er-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-er-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-er-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-er-4.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-lc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-lc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-lc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-na-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-na-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-na-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-ng-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-ng-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-ng-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-po-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-po-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-po-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-tc-1.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-tc-2.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/probe-bundle/pb-tc-3.json` | 2026-10-11 `c98a2a3f22f6` | 2026-10-11 `4b470ffb2abc` |
| `tests/fixtures/regulatory/synthetic_crlf.txt` | 2026-10-05 `363abe438040` | 2026-10-05 `363abe438040` |
| `tests/fixtures/regulatory/synthetic_lf.txt` | 2026-10-05 `363abe438040` | 2026-10-05 `363abe438040` |
| `tests/fixtures/review/case.json` | 2026-10-05 `818de084c67f` | 2026-10-05 `818de084c67f` |
| `tests/integration/test_gemini_wire.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `tests/integration/test_h1.py` | 2026-10-05 `8e0583bb6750` | 2026-10-05 `8e0583bb6750` |
| `tests/integration/test_m3.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `tests/test_artifact_contracts.py` | 2026-10-04 `e373f9a34a6b` | 2026-10-04 `e373f9a34a6b` |
| `tests/test_gemini_transport.py` | 2026-10-06 `f3c796287090` | 2026-10-11 `c38fb91e8041` |
| `tests/test_judgment.py` | 2026-10-06 `f3c796287090` | 2026-10-06 `f3c796287090` |
| `tests/test_modeling_baselines.py` | 2026-10-04 `2009748672a0` | 2026-10-04 `2009748672a0` |
| `tests/test_probe_bundle.py` | 2026-10-11 `8fad260d7955` | 2026-10-11 `3cd29718f700` |
| `tests/test_regulatory_structure.py` | 2026-10-05 `363abe438040` | 2026-10-05 `363abe438040` |
| `tests/test_repo.py` | 2026-10-03 `77f2895235c8` | 2026-10-04 `562277009a44` |
| `tests/test_review_case.py` | 2026-10-05 `818de084c67f` | 2026-10-05 `8e0583bb6750` |

## Generated export files

| File | Content source | First commit | Last commit |
|---|---|---|---|
| `README.md` | `scripts/release/clean-install.md` at the audited revision | 2026-10-11 `83ddecb61a3a` | 2026-10-12 `72fea46ca694` |
| `PROVENANCE.md` | written by this tool from the audit of the audited revision | — `—` | — `—` |
| `EXPORT-AUDIT.json` | machine-readable record of this audit, written by this tool | — `—` | — `—` |

## Content-scan notes and reviewed exceptions

- reviewed exception: src/demo/__init__.py matches credential-assignment at line(s) [6]; each of the 1 match(es) hashes to a reviewed digest — Reviewed 2026-10-11: the single hit is the literal placeholder constant of the labelled fictional seed used by the local walkthrough and its tests, and the digest above is sha256 of that exact matched text. It is a synthetic value in a synthetic-only module, not a credential. The exception covers that content only: replacing it with anything else — even at the same hit count — changes a digest and stops the export until the new content is reviewed.

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
