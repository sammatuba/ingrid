# The event fixture: the recorded judge flow and the two harnesses

`tests/test_grid_event.py` covers the event adapter (`src/grid/event-api.js`) and the page's
own scripts through these files and two runners, all built by the real code, never typed by
hand:

| File | What it is |
|---|---|
| `build.py` | The builder: writes `view.json`, `flow.json` and (DESK-1) `outlook.json`; `--check` compares the committed bytes with a fresh build and exits non-zero on any drift (the tests call it that way). Standard library only, no model, network or credential. |
| `view.json` | The shape the adapter reads. The page's own baked view model is written by the orchestrator's converter (`docs/work/grid-desk/reference/event_judgment.py`); this file carries the fields the adapter reads, taken from `src/demo/pedc-case.json`. |
| `flow.json` | The recorded flow (`grid-event-flow.v2`): the session answer `POST /demo/session` returns, and per decision the one prepare request the adapter sends (PERF-3), the case heads, the snapshot at the state instant that decision audits, the compiled task, the review request the adapter sends, the receipt, the accepted outlook the adapter reads back, and the history after it — every one the object the real repository returned. |
| `outlook.json` | DESK-1: the event page's register-and-price-outlook view for this event, written by the real builder (`scripts/grid/build_data.py`) from the synthetic register and archive beside the grid fixture (`tests/fixtures/grid/outlook/`) and the event's assumption text in `scripts/grid/events.json`. The fixture register carries no row for that text, so the page shows the honest reading: not registered, and no issued price outlook rests on it. `render.mjs` serves it as the page's `/grid-data/outlook/<id>.json` read. |
| `run.mjs` | The adapter harness: it loads `src/grid/event-api.js` into a node VM and runs the three decisions with their history, a deployment without `/demo/session`, a route refusal, the three history failures (401, 503, 200-not-a-list), and the three read-back failures that follow a saved decision (an HTTP refusal, a transport error, a malformed body) — printing one JSON report. |
| `render.mjs` | The page harness: it builds a DOM from `src/grid/event.html`, runs `event-api.js` and the design file `event.js` against the recorded flow, submits the decision through the page's own form and prints what the page rendered — the history card after the save, and, with `--history-failure`, the refusal that must appear there instead of nothing; with `--refresh-failure` the read-back fails instead and the status line must keep the saved receipt with the failure named beside it. With `--stamp <16 hex>` the shim's page carries that build stamp in `meta#nowcast-build` and the adapter reads the view model under the versioned prefix the application serves (`/grid-data/<stamp>/events/<id>.json`); the report says which stamp it ran with. With `--fixture <dir>` it renders that directory's `view.json` instead, and when the directory holds no `flow.json` (CORP-5's reserve-market and rules-in-force views, whose decisions are prepared in their case packs instead of filed through the judge's routes) it renders the page, reports the `rules` card — every cutoff tab's state, reached by clicking the page's own tab button — the caption's limits, the advisory's as-of line and the decision form's state, and drives no decision. The shim parses the HTML the page writes into elements (`innerHTML`), so a click on a drawn node reaches the page's own handler. |
| `reserve-market/view.json` | CORP-5: the reserve-market case's event view, built by `scripts/grid/build_rules.py` from `docs/cases/reserve-market/evidence-manifest.json` and the corpus store — the 'rules in force' block is the store's own answers at the case's two cutoffs. It is a second fixture directory rather than a second file here because the harnesses read `<fixture>/view.json`. Regenerated and checked by the builder, never typed by hand: `/usr/bin/python3 scripts/grid/build_rules.py [--check]`. |
| `rules-in-force/` | CORP-5: the **labelled synthetic fixture**. The reserve-market copies carry no first-availability evidence, so no cutoff can place a clause version there and a refusal alone demonstrates nothing; this directory keeps the case's shape with invented records that do carry it, so the complete path — the clause in force at a cutoff, the version that replaced it refused and not quoted, the announcement that changed it, and the accepted dependency the real pack cannot show — is demonstrated once, end to end, in the shim and in a real browser. `build.py` writes `evidence-manifest.json` (every digest computed there) and `view.json` (through `scripts/grid/build_rules.py --case`); `--check` proves both reproduce. Every record says it is invented, in the manifest's `fixture` block, the view's title, its first limit line and its `fixture_note`. |
| `retrieval/view.json` | RAG-5: the **labelled synthetic fixture** for the event page's "What the system read" card: a minimal event view whose `retrieval` block has the contract's shape (`docs/work/retrieval-2026-10-18/intent.md`, section Contracts) with two states (`hindsight`, `known-then`), invented passages, distances, counts and digests, and a judgment that cites three ranks. Typed by hand because no recorder has run yet (RAG-4 writes the real block); every label starts `[fixture]` and `fixture_note` says it is invented. `tests/test_grid_event.py::RetrievalCard` reads it. |

How the fixture is tied to the real code:

* `build.py` provisions a **pinned** sandbox session through `src.api.hosted._provision` (the
  function `POST /demo/session` calls) with a fixed uid and instant, so the case ids and the
  records are reproducible. Its `id_token` is the short label `fixture`: the real token is
  minted per session by the sandbox identity and names nothing here.
* The recorded decisions are the same calls the frozen routes make (`prepare_task` — the
  repository port behind the additive `POST .../prepare`, which answers the heads, the snapshot
  and the compiled task in one call — `commit_review` and `read`), and the routes return those
  objects unchanged. The snapshot and the task the prepare call writes are the records the
  separate `build_snapshot` and `compile_task` calls wrote before PERF-3, byte for byte: this
  fixture's own `--check` proves it, because every other recorded object is unchanged.
* The snapshot each decision audits is the adapter's rule, replayed rather than restated: the
  **seeding instant** for the first decision, and the `recorded_at` of the outlook the previous
  decision was accepted as for every later one. The three decisions are retain, revise and
  retain, so a decision after a revision is covered.
* In recorded mode the harness **refuses any request body that differs from the recorded one**
  — including the snapshot's audit cutoff and the read's record — so the adapter cannot pass on
  a transport that answers anything: what it sends is what the review core accepted when the
  fixture was built.
* In the read-back failure scenarios the first `/read` — the one that follows a saved decision —
  answers the injected failure and the next decision's retry is answered normally, so the run
  proves both halves: the first decision's answer keeps its receipt and names the failure, and
  the second decision re-reads the accepted outlook before it sends anything (its snapshot body
  must still be the recorded state instant — a stale cutoff is a recorded problem).
* With `--base http://127.0.0.1:<port>` `run.mjs` talks to a running server instead (the demo
  container, or `NOWCAST_ENV=demo .local/h1-venv/bin/python -m uvicorn src.api.hosted:app
  --factory`), and `tests/test_grid_event.py::LiveServer` runs exactly that and checks the
  decisions landed on the judge's own case.
* PERF-1: `src/grid/event.html` carries `__NOWCAST_STAMP__` where the application writes its
  build stamp. This harness builds its DOM from that source, so **without `--stamp` the token
  is not stamp-shaped** and the adapter reads the unversioned `/grid-data/events/<id>.json` —
  the recorded flow above, and a name the server serves with `no-store`. The same harness run
  with `--stamp` reads the versioned name; `tests/test_cache_headers.py::Scripts` runs both
  halves, so neither is an assumption.

Regenerate after any change to the flow, the case data or the routes:

```sh
/usr/bin/python3 tests/fixtures/grid/event/build.py            # rewrite both files
/usr/bin/python3 tests/fixtures/grid/event/build.py --check    # compare, write nothing
node tests/fixtures/grid/event/run.mjs --root .                # the adapter report
node tests/fixtures/grid/event/render.mjs --root .             # the page report
node tests/fixtures/grid/event/render.mjs --root . --history-failure storage
node tests/fixtures/grid/event/render.mjs --root . --refresh-failure transport
# the two rules views, through the same page
/usr/bin/python3 scripts/grid/build_rules.py [--check]
/usr/bin/python3 tests/fixtures/grid/event/rules-in-force/build.py [--check]
node tests/fixtures/grid/event/render.mjs --root . \
  --fixture tests/fixtures/grid/event/rules-in-force --event fixture-rules-in-force
```
