# InGRID

Who answers for a decision made with AI? InGRID lets people decide with AI and answer for the
decision later. Every judgment, assumption and decision is a record with a time, an owner and its evidence.
We test it as a review desk for energy analysts who write outlooks for the Philippine grid: when the grid
changes, the desk finds the assumption the change touches, asks a model for a cited judgment, and keeps
the analyst's decision. Ingrid, the desk's assistant, proposes; the person decides.

Live site: https://ingrid-desk.web.app (the same build also answers at https://grid-nowcast.web.app).
It replays recorded grid data to 14 October 2026. A signed-in user gets a live Gemini answer in the
command bar, with the steps the model took; an anonymous visitor gets the composed answer. The product's
name was Grid Nowcast until release 23 (18 October 2026); the Google Cloud project, the Cloud Run service
and the data buckets keep that first name, so `grid-nowcast` in the deploy scripts and the SQL is the
cloud project, not the product.

This repository is a filtered export of the private working repository, written by the release tool from
a reviewed allowlist. `EXPORT-AUDIT.json` lists every exported path and names the source commit and date
(`source_revision`, `source_date`); `PROVENANCE.md` records the first and last commit of each path.
Nothing is edited here. The work records (plans, progress, task packets) and the private market data (the
company's WESM copy) stay in the private repository and never enter Git.
Clone: `git clone https://github.com/sammatuba/ingrid`.

## Licence and attribution

Proprietary: all rights reserved, published for the AI Builder Cup 2026 evaluation only (`LICENSE`).
Sam Matuba wrote the paper. Sam Matuba and Ericka Formanes wrote the codebase (the private history holds her commits; each public commit names her as co-author). Jayden Cacayan gathered
the feedback and refined the use cases as the user representative (`ATTRIBUTION.md`).

## Start reading

1. `docs/START-HERE.md`, then `docs/status.md` and the
   glossary (`docs/glossary.md`).
2. The theoretical foundation (`docs/architecture/theoretical-foundation.md`) and the
   framework and architecture (`docs/architecture/meta-thesis-and-framework.md`).
3. The paper (`docs/product/paper-accountable-ai-decisions-2026-10-17.md`) and the
   explainer (`docs/explainer/README.md`) (27 chapters; also served at /explain).
4. The competition pages (`docs/competition/ai-builder-cup-2026/requirements.md`) and the
   review records (`docs/work/reviews/README.md`), one per accepted task.
5. `AGENTS.md` for the authority chain and the directory map; `src/README.md`
   for the code layout.

## The four theories, in one paragraph

The desk stands on four established bodies of work, each mapped to a record kind: belief revision and
bitemporal data (Doyle 1979; Alchourrón, Gärdenfors and Makinson 1985; Jensen and Snodgrass 1999) give
justified beliefs with sources, the two clocks and the snapshot at a cutoff; decision theory (Howard 1966;
Howard and Matheson 1984; Murphy 1993; Gneiting and Raftery 2007) gives impact in the organization's own
units, the materiality line and the scorecard; coordination theory and human-automation research (Malone
and Crowston 1994; Parasuraman, Sheridan and Wickens 2000; Lee and See 2004) give owners, the
proposal-review-accept chain and "the model proposes, a person accepts"; organizational learning (Argyris
and Schön 1978) gives scoring receipts and attribution as the single loop. Where each is thin today is
stated in the foundation page's section 7 and the paper's section 8.

## Google Cloud services

State words: running, ran once, built (not run live), set up (no run record), designed.

| Service | What it does here | State |
|---|---|---|
| Firebase Hosting | Serves the first screen and the grid files. Sends every other path to Cloud Run. | running |
| Cloud Run (asia-southeast1) | The app server: visitor copies, decisions, the ask service, the command bar search and answers, alerts, journal and book pages. | running |
| Artifact Registry | Holds each release image. | running |
| Firestore | Each visitor's copy of the case and decisions; the alerts, ask and journal data. | running |
| Firebase Authentication | Anonymous visitor identity; sign-in for the editors; the sign-in screen. | running |
| Vertex AI Gemini | Eight fixed questions on one evidence and assumption pair; the planner; cited extraction. | question set ran once on the real case (2026-10-14, two calls at two cutoffs) and once on the synthetic case (2026-10-11); planner and extraction built, not run live |
| BigQuery | The company copy. Read when the grid files are built and by the alerts page. | ran at each build; alerts read built, no run record |
| Cloud Storage | The company copy and the anonymised portfolio draft. | data location |
| Secret Manager | The mail password and the search key for the alerts. | set up, no run record |
| Cloud Scheduler | The automatic alerts check when new data lands. | built, no run record |
| Cloud Build | Ran the hosting checks once (2026-10-14). Not in the deploy path. | ran once |

## What is generic and what is a plug-in

| Generic (the framework) | Domain plug-in (this instance) |
|---|---|
| the seven record kinds and their invariants (`src/review`, `src/outlook`) | the WESM ontology profile: resources, nodes, regions, billing month (`src/adapters/wesm`) |
| two clocks, cutoffs, replay (`src/review`) | the posting and effect times of NGCP and PEMC records |
| the belief register with layers and owners (`src/outlook/register.py`) | the three families: demand, supply, rules |
| the compiler and the bounded question set contract (`src/judgment`) | the eight questions and their event vocabulary |
| the judgment ports: questions, cited extraction, numbers (`src/adapters/systemone`, `src/adapters/gemini`) | Gemini on Vertex; System One; the price baselines (`src/price`) |
| impact in own units with a materiality line (`src/price/impact.py`, `src/book`) | pesos on a retail portfolio against settlement prices |
| scoring against settled truth with attribution (`src/outlook/records.py`) | final settlement prices on the billing-month clock |
| the desk pages and the plain-language rules (`src/grid/shell.js`) | the grid page, the event page, the ask service (`src/agent`) and the command bar, the alerts and book pages |

A second domain changes the right column only. That is the test of the framework and it has not been run;
it is a hypothesis (framework page, section 4).

## Run the tests

Python 3.11 or newer and nothing else; the exported suite uses the standard library only. No network,
credential, cloud project or model call is needed. From this directory:

    python3 -m unittest discover -s tests

Expect `Ran 1614 tests` and `OK` with skips: the browser checks, the hosted wire checks
(FastAPI is not installed), the tests that read the baked grid data or the private archives, and the
tests that read `scripts/deploy/deploy.sh` or `scripts/ontology/sql` skip with their reason. The hosted
API's pinned third-party dependencies are listed in `requirements/h1.lock`; installing them is a separate
step and not part of this check.

## What is withheld

These test files stay in the private repository, by allowlist rule, because they run scripts or read
records that stay private. No test is edited to pass; a withheld file is left out whole. Counts are
test methods (`def test_`) in each file: 52 files, 1998 test methods.

| Test file | Methods | Why it stays private |
|---|---|---|
| `tests/test_plan.py` | 8 | checks internal plan records |
| `tests/test_release_audit.py` | 32 | audits the private repository's history and allowlist |
| `tests/test_grid_data.py` | 127 | checks the private Git state and the baked grid data |
| `tests/test_build_register.py` | 6 | tests the private data register builder |
| `tests/test_price_fuel.py` | 14 | runs the parquet export over the private bucket |
| `tests/test_wesm_sources.py` | 41 | runs the private WESM export script |
| `tests/test_outage_checks_norm.py` | 2 | reads the private data SQL |
| `tests/test_coverage_objects.py` | 2 | imports the private data pipeline |
| `tests/test_corpus_acquire.py` | 39 | imports the corpus fetch script, which names the company bucket |
| `tests/test_corpus_index.py` | 10 | imports the corpus index and BigQuery load scripts |
| `tests/test_corpus_extract.py` | 54 | imports the live extraction runner |
| `tests/test_corpus_store.py` | 71 | imports the passage store over the company copy |
| `tests/test_event_candidates.py` | 8 | imports the grid lane scripts (private BigQuery export and bake) |
| `tests/test_grid_asset.py` | 61 | imports the grid lane scripts and needs the real bake |
| `tests/test_grid_catalog.py` | 83 | imports the grid lane scripts |
| `tests/test_grid_map_page.py` | 28 | imports the grid lane scripts |
| `tests/test_grid_outages.py` | 29 | runs the grid lane scripts |
| `tests/test_grid_register_page.py` | 32 | imports the grid lane scripts |
| `tests/test_grid_outlook.py` | 70 | imports the grid lane scripts |
| `tests/test_grid_outlooks_page.py` | 37 | imports the grid lane scripts |
| `tests/test_judgment_view.py` | 124 | imports the grid lane scripts at module level |
| `tests/test_grid_page.py` | 102 | runs the grid lane scripts |
| `tests/test_grid_work_page.py` | 37 | reads the private task register and product-gap records |
| `tests/test_portfolio_import.py` | 13 | imports the portfolio import script, which names the private bucket |
| `tests/test_corpus_retrieve.py` | 25 | imports and runs the corpus passage and retrieval scripts |
| `tests/test_outlook_register.py` | 60 | reads the private data SQL and data-foundation work records |
| `tests/test_price_response.py` | 70 | reads the event-study query over the company copy and a work record |
| `tests/test_price_availability.py` | 49 | runs the known-outages query over the company copy; imports the grid lane scripts |
| `tests/test_grid_briefs.py` | 68 | loads the grid lane scripts |
| `tests/test_grid_ask_page.py` | 88 | loads the grid lane scripts |
| `tests/test_alerts_explain.py` | 16 | imports the grid lane alert explainer |
| `tests/test_alerts_ontology_live.py` | 14 | imports the alerts explain test (above) |
| `tests/test_grid_event.py` | 105 | reads a case pack and corpus records that stay private |
| `tests/test_event_prepare.py` | 15 | imports the grid event test (above) |
| `tests/test_grid_models_page.py` | 21 | imports the grid page test (above) |
| `tests/test_hosting_stage.py` | 53 | loads the release tool and imports two withheld tests |
| `tests/test_grid_ui.py` | 12 | reads the design-system work record at import, a withheld record |
| `tests/test_integration_contract.py` | 35 | imports the hosting stage test (above) |
| `tests/test_judgment_actions.py` | 18 | imports the hosting stage test (above) |
| `tests/test_agent_service.py` | 75 | nine cases import the judgment view test (above) |
| `tests/test_eval_probe_bundle.py` | 17 | reads a work record outside this export |
| `tests/test_explainer.py` | 23 | checks links into work records outside this export |
| `tests/test_book_generate.py` | 17 | reads the private repository ignore rules |
| `tests/test_ontology_bake_panel.py` | 5 | reads the private repository ignore rules |
| `tests/test_book_records.py` | 19 | imports the book generate test (above) |
| `tests/test_build_all_swap.py` | 3 | loads the grid lane bake script |
| `tests/test_build_all_saved_ontology.py` | 8 | imports the grid lane bake script (main 2dcb1e24) |
| `tests/test_desk_live.py` | 21 | one case imports the excluded live recorder `scripts/desk/record_prompts.py` (PR #102) |
| `tests/test_register_gaps.py` | 9 | loads the grid lane bake script |
| `tests/test_cache_headers.py` | 54 | one class runs the grid lane bake script |
| `tests/test_grid_alerts.py` | 43 | imports the cache headers test (above) |
| `tests/test_journal.py` | 25 | one case imports the cache headers test (above) |

A row marked "(above)" is a test file that imports another withheld test file; its own cases need
nothing private and return once that import is guarded.

Four cases in `tests/test_alerts.py` and two classes in `tests/test_hosted_config.py` are exported but
skip here: they run or read `scripts/deploy/deploy.sh` (which names the service accounts and the project)
or compare `scripts/ontology/sql` (warehouse SQL); both stay private.

Links from the exported pages into `docs/work/` records that are not in this export, and into
`scripts/grid`, `scripts/data` and `src/workspace-preview`, do not resolve here; the private repository
holds them.

## What this export is not

It is not a maintained second application. Rights and clearance, the deck and the video, and
publication itself are handled in the private repository's release records.
