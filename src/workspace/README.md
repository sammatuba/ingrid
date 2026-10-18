# Connected local change desk

This workspace uses the [H1 API](../../scripts/h1/README.md), Firebase Auth emulator and
Firestore emulator. It is separate from the [fictional reference preview](../workspace-preview/README.md).
Evidence and model suggestions remain proposals; only explicit human review changes an accepted input.

From the Git root, with the existing [H1 dependencies](../../scripts/h1/README.md) installed:

```sh
bash scripts/m3/serve.sh
```

Open `http://127.0.0.1:18001/desk` (the root `/` serves the grid page). Sign in with `analyst@example.test` and
`synthetic-local-only`. These are public fictional emulator credentials, not a real account.
The default workspace/case is `synthetic-tenant` / `synthetic-case`. To inspect blocked identity,
sign out and use case `synthetic-ambiguous`. No Google credentials or model key is needed.
Keep these emulators on loopback. The server rejects hosted/production emulator configuration.

Prepare a review, open exact evidence, select retain/revise/reject/defer/investigate and save a
reason. Refresh or sign in again to recover saved history. A lost response exposes a retry of
the identical request; changed heads return a conflict, requiring a refreshed review. Review
baseline and current accepted input are displayed separately. Proposal export never computes
consequences or grants execution authority. Sources and model text render as text, not HTML.

## Probe bundle view (UI-1)

The probe bundle panel shows a saved `ProbeBundleArtifact` for the compiled task: the composed
relation label, the rule that fired, the eight atomic answers per form, the perturbation-stability
receipt with its thresholds, the instability flag and the escalation, the bundle metadata and
digests, and the passages the probes refer to. It renders text only; every value is written with
`textContent`, and no probe field is interpreted as markup. A bundle is a proposal: it changes no
accepted value and grants no authority.

Availability follows the frozen contract's `bundle_available`, the sibling of `model_available`.
With the backend absent or the flag false, the panel says so, the request button stays disabled
and manual review, dispositions and the cited brief are unchanged. With the flag true, the button
saves a bundle through `POST /tenants/{t}/cases/{c}/probe-bundles` and the workspace projection's
`probe_bundles` entries (`task_ref`, `actor_id`, `idempotency_key`, `questions`, `answers`,
`composed`, `receipt`, `metadata`, `review_state`, `synthetic`) are rendered next to the cited
brief. Nothing in this view calls a model by itself.

`src/workspace/app.js` carries two synthetic UI contract fixtures matching working-paper
appendix A (a stable `challenges` bundle) and the intent's instability case (Q2 flipping on two
of four forms). They were generated with `src/judgment/bundle.py` itself and are never a model
run or a case record. Open `http://127.0.0.1:18001/desk?probe-fixture=appendix-a` (or
`?probe-fixture=unstable`) after signing in to preview one; the panel states that it is a
contract fixture. The rest of the desk keeps working from the live emulator case.

## Cutoff pair view (UI-2)

The pair panel derives the read-only diff of two saved probe bundles: the composed label on
each side with its information cutoff, the questions whose atomic answers moved and the
passages only the later cutoff carries. It calls the frozen
`GET /v1/tenants/{t}/cases/{c}/probe-bundles/pair` route with the two saved references the
analyst chooses. Nothing is stored, no accepted value changes and no consequence is computed.

Two saved bundles are needed. With fewer than two compiled reviews for the selected assumption
the panel says so and the compare control stays disabled, so there is no pair when only one
task exists. A refusal is shown as text — the typed code and its sentence
(`PAIR_CUTOFF_ORDER`, `PAIR_ASSUMPTION_MISMATCH`, `PAIR_SNAPSHOT_MISMATCH`,
`PAIR_NOT_A_BUNDLE`, `PAIR_NO_ATOMIC_ANSWERS`) — never as a numeric status. The refusals the
panel can reach with its own choices are `PAIR_SNAPSHOT_MISMATCH` (the two chosen bundles'
tasks were not compiled from the same snapshot) and `PAIR_CUTOFF_ORDER` (the "after" side is
not strictly later than its "before" side); it lists bundles for one assumption only, so an
assumption mismatch cannot be chosen.
The view is rendered from a saved `ProbeBundleArtifact` pair only; like the probe panel it
writes every value with `textContent` and interprets no field as markup.

Open `?pair-fixture=moved` (a pair with one new passage and two moved atomic answers),
`?pair-fixture=refused` (the same two saved bundles with the later one on the before side) or
`?pair-fixture=single` (one compiled review, so no pair) after signing in to preview a
synthetic UI contract fixture. Each was derived by `src/review/pairing.pair` itself over the
CORE-4 view test's own records; the generator and the field-by-field checks that reconstruct
the embedded projection are recorded in the [UI-2 review record](../../docs/work/reviews/UI-2.md).
The rest of the desk keeps working from the live emulator case.

The token lives only in browser memory. Reload requires another sign-in. The server controls
membership; there is no browser Firestore write or membership endpoint. Sign-out/access loss
clears private views and ignores in-flight responses. Private HTTP responses use `no-store`.
The login proxy is explicitly local-emulator-only; it is not a production authentication flow.

Records survive app/client reconnects while the Firestore emulator is running. Stopping the
emulator clears this walkthrough: no disk export/import is configured. Hosting and the real case
are recorded elsewhere ([HOST-2](../../docs/work/reviews/HOST-2.md), [EVAL-5](../../docs/work/reviews/EVAL-5.md));
this desk is the local analyst view, reached hosted only as the drill-down behind the grid page.

## Verification

```sh
bash scripts/h1/test.sh
node scripts/m3/browser-check.mjs /absolute/path/to/chromium
```

The browser check requires a running local walkthrough and Playwright Core installed under
`.local/deckcheck` (the session used its existing lockfile, version 1.63.0). It saves screenshots
and a synthetic proposal under ignored `.local/m3-browser/`. The browser assertions cover
390/768/1440 widths, source and judgment HTML escaping, citation navigation, response-loss
retry, persisted history, stale browser conflicts, cutoff/mapping blocks and sign-out races.
Its injected judgment is explicitly a UI contract fixture. Emulator tests independently verify
judgment persistence; no test fixture is a Gemini run. AI is disabled in the default app.
UI-5 (probe-view and pair-view browser assertions) was cut on 2026-10-14; both views are
checked by hand from the fixture URLs above, and the pair panel's request path is pinned
offline by `tests/test_pairing.py` and the route's own integration tests. See the
[workspace work packet](../../docs/work/m3-workspace/implementation.md), the
[UI-1 review record](../../docs/work/reviews/UI-1.md) and the
[UI-2 review record](../../docs/work/reviews/UI-2.md).

The separate [bounded Gemini runner](../adapters/gemini/README.md) prepares a task offline and
runs it through the Vertex AI transport (CORE-7) when explicitly configured. It does not enable
AI in this workspace.
