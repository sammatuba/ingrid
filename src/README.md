# Application code: the layout as it is

[START-HERE](../docs/START-HERE.md) orients a person; [status](../docs/status.md) says what exists.
This page maps the tree. It describes, it does not refactor. Dated 2026-10-18 (POLISH-2, F-20).

## Seventeen packages

| Package | What it holds |
|---|---|
| `contracts/` | Shared errors, JSON helpers and validators. Stdlib only. |
| `review/` | The record core: records, pairing, repository and transactional storage ([README](review/README.md)). |
| `judgment/` | The cited judgment boundary: the question set, the view planner and the action catalogue ([README](judgment/README.md)). |
| `outlook/` | The belief register, outlook records, re-issue, scoring and dependencies. |
| `price/` | Price series, baselines, challengers, impact and the scorecard. |
| `modeling/` | Model providers, evaluation and their records. |
| `regulatory/` | Rule-document grammars, structure and source trail ([README](regulatory/README.md)). |
| `adapters/` | Ports to the outside: `wesm` readers, `gemini` on Vertex AI ([README](adapters/gemini/README.md)), `systemone`, `firestore`, `identity`, `bigquery`, `corpus`. |
| `api/` | `hosted.py` assembles the hosted app's routes over the shared ones in `__init__.py`; `local.py` the local Uvicorn factory. |
| `grid/` | The served pages: the grid page (map first, with the "Grid now" card), the event page, outlooks, register, models, plants, notices, alerts, book, journal, ask, explain, paper, settings, the shared `shell.js` top bar with its live strip, and the command bar (`command.js`; `ask.js` drives the ask service through it). The floating dock panel was removed on 2026-10-18 (GitHub PR #102). |
| `agent/` | The ask service (built as the dock, DOCK-1 to DOCK-5): sessions, the queue, the budget meter, the recorded plan sets, `/api/agent/*`. |
| `desk/` | The command bar's search, previews, prompts and answers over the baked replay (`/api/desk/*`), added 2026-10-18 (GitHub PR #102). Its Gemini loop is built and tested with a fake transport; no Gemini call has run through it. |
| `alerts/` | The alerts page: BigQuery reads, driver cards, notices, mail, the sign-in and scheduler checks. |
| `journal/` | The trader's journal: model, store, service and `/api/journal`. |
| `book/` | The synthetic portfolio book: generation, exposure, impact, records. |
| `demo/` | Seeds each visitor's copy of the real PEDC case (`pedc-case.json`). |
| `workspace/` | The connected local workspace, still reachable at `/desk` ([README](workspace/README.md)). |

`workspace-preview/` is a historical interaction mock from 2026-10-04 with fictional data. It is
not served and not part of the product; it is excluded from the public export.

## Generic against plug-in

The framework page (section 4) separates the generic desk from the domain plug-in. In the tree:

| Generic (the framework) | Domain plug-in (this instance) |
|---|---|
| the record kinds and their invariants (`review/`, `outlook/`) | the WESM profile: resources, nodes, regions, billing month (`adapters/wesm`) |
| two clocks, cutoffs, replay (`review/`) | the posting and effect times of NGCP and PEMC records |
| the belief register with layers and owners (`outlook/register.py`) | the three families: demand, supply, rules |
| the compiler and the bounded question set (`judgment/`) | the eight questions and their event vocabulary |
| the judgment ports (`adapters/systemone`, `adapters/gemini`) | Gemini on Vertex AI; System One; the price baselines (`price/`) |
| impact in own units with a materiality line (`price/impact.py`, `book/`) | pesos on a retail portfolio against settlement prices |
| scoring against settled truth with attribution (`outlook/records.py`) | final settlement prices on the billing-month clock |
| the desk pages and the plain-language rules (`grid/shell.js`) | the grid page, the event page, the ask service (`agent/`) and the command bar (`desk/`), the alerts and book pages |

A second domain changes the right column only. That is a hypothesis; it has not been run.
The five core packages (`review`, `judgment`, `regulatory`, `outlook`, `price`) import no model or
cloud SDK; `api/hosted.py` imports the cloud libraries inside its factories.

## What is served

`api/hosted.py` serves the pages in `grid/` behind Firebase Hosting, with Firestore for each
visitor's copy and Firebase Authentication for the sign-in screen. The event page replays the
recorded Gemini run of 2026-10-14; the site makes no live model call. The command bar's live
path is off until the owner turns it on, and no call has run through it (GitHub PR #102). Runtime adapter
dependencies are pinned in `requirements/h1.lock`; the record core and judgment validation stay
stdlib-only. Python 3.11 or newer.

Keep domain records and validation independent of model and cloud SDKs. Create code directories
with working modules, not empty service scaffolding. The teammate's static dashboard prototype
lives in `archive/dashboard/`. Experiments and sibling research repositories are context, not
production imports.
