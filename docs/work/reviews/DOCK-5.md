# DOCK-5 review record

## Round 1 (Claude Opus 5.5 in-session subagent, read-only, independent of the author; 2026-10-18)

| Field | Value |
|---|---|
| Task | DOCK-5: the shared files for the owner's lanes (agent routes mounted and classified private, the same-origin session, the book page route, staging and bake, the Firestore rules, the Book entry on the pages no pending task owns) |
| Branch | `task/DOCK-5` |
| Commit | `7ef9e4b2` (code at `3eb751d2`; the two later commits change the task record only) |
| Base | `259d77f6` (`origin/main`, merged in; `git merge-base HEAD origin/main` = `259d77f6`) |
| Reviewer | Claude Opus 5.5 in-session subagent, read-only, not the author |
| Verdict | **accept** (no major finding; three minor findings and one nit, none blocking; release conditions listed below) |

The record holds the task to `scripts/plan.py brief DOCK-5` and its note (the orchestrator's seven
additions), strategy decisions 3, 10 and 13 and sections 1, 3 and 6, agent contract sections 4 and 6,
the DOCK-2, DOCK-3, BOOK-3 and BOOK-4 records and reviews (their hand-backs to DOCK-5), `src/alerts/auth.py`,
`src/alerts/routes.py` and `docs/work/alerts-portfolio-2026-10-17/contract.md`.

### Commands run and results

All from the worktree `.local/wt/DOCK-5` with `/usr/bin/python3` unless stated. No network, model,
cloud, Firebase or deploy call. `/tmp` is writable in this sandbox, so no test errored for want of a
temporary directory.

| Command | Result |
|---|---|
| `git diff 259d77f6..HEAD` | read in full: 47 files, `+1829 −81` (every file the brief names, the packet, `tasks.json` state `in_progress`, the `PROGRESS.md` row edited in place and one log row) |
| `python3 scripts/plan.py check && python3 -m unittest discover -s tests -p "test_*.py"` (the brief's verify) | `OK: 142 tasks, 9 gates`; `Ran 3193 tests in 234.727s`, **OK (skipped=62)** |
| `.local/h1-venv/bin/python -m unittest tests.test_cache_headers tests.test_hosted_config tests.test_agent_service tests.test_grid_page tests.test_hosting_stage` (the main checkout's FastAPI 0.115.12 / Starlette 0.46.2 venv, run by absolute path) | `Ran 381 tests in 35.053s`, **OK**, no skip: the `Wire` and `HTTPContractTests` classes that the bare interpreter skips ran on the real server library |
| `python3 -m unittest tests.test_grid_book_page tests.test_hosting_stage tests.test_agent_service tests.test_hosted_config tests.test_cache_headers` | `Ran 338 tests`, OK (skipped=15: the FastAPI-only classes above) |
| `python3 scripts/plan.py scope DOCK-5 origin/main` | `OK: all changed files inside DOCK-5 allowed paths` |
| `python3 scripts/repo.py check` | `Checked 626 Markdown files, 3937 local links, 5 skills; bootstrap 1399 words.` `PASS` (before this record was written) |
| `git diff --check 259d77f6..HEAD` | clean |
| `python3 tests/fixtures/grid/catalog/build.py --check` | `OK: 20 fixture bake files reproduce` |
| `python3 scripts/grid/build_map_page.py --check` | `the map page carries a fresh render of the integration contract` |
| `python3 scripts/book/bake_book.py --check` | `OK: 2 book page files reproduce` |
| `build_all.py --check` over the fixture inputs (`--data tests/fixtures/grid/catalog/bake`, the fixture snapshot, geo, events, `catalog/inputs/spike.json`, the outlook register and archive, absent impact and scorecard), four ways: as is; `--no-book`; `--views <scratch copy of the six fixture view.v4 sets, no index.json>`; both | exit 0 each, `violations: []`, all four checks (`build_data`, `build_catalog`, `briefs`, `build_assets`) exit 0 each time. `build_data` gets `--book` and reports `book` exactly when the book is on; the six plan-set keys (`ask`, `home`, `models`, `outlooks`, `register`, `syn-bay-unit-2-trip`) exactly when `--views` is given |
| Structural JSON diff of the six regenerated fixture plan sets against `259d77f6` | only `views/i/receipt/request_digest` and `views/i/components/4/fields/receipt_digest` move, three views per file; no other key, value or list length |
| `git diff --name-only 259d77f6..HEAD` against every task not `done` in `tasks.json` (`owned_paths`) | no changed file is owned by a task that is not done (RAG-5, DOCK-4, DOCK-6 among the 40 checked) |
| Removed lines in `tests/`: `+    def test_` 40, `-    def test_` 0; every removed `assert` line | the nine removed assertions are BOOK-3's three "no Book yet" pins, the shared ten-link pin and BOOK-3's browser nav pins, each replaced by the inverted pin the note requires |
| Probes (scratchpad scripts, outside the tree): `AgentSessions` with labelled fake verifiers; a real FastAPI app with `BodyLimit`, the agent routes and the session routes through `starlette.testclient`; `demo_application({})` over the fixture bake; `BookAdapter` with no vintage archive; `PlanSets` over a scratch copy of `.local/grid-snapshot/views` | results in the attack table |
| Headless Chromium (`~/.cache/ms-playwright/chromium-1234`, playwright-core from `.local/deckcheck`) on scratch copies of the pages at `259d77f6` and at HEAD, 1280 and 390 wide, with and without the fixture bake served | results under finding 2 |
| Owner data, before and after all runs: `sha256sum` of every file under `.local/outlook-archive` and `.local/price`; `OutlookArchive('.local/outlook-archive').verify()` | before: 30 files; `{'outlooks': 2, 'receipts': 0, 'attributions': 0, 'problems': []}`. After: 36 files; `{'outlooks': 3, 'receipts': 0, 'attributions': 0, 'problems': []}`. See "Owner data" below |
| `git status --short` after all runs | clean apart from this record |

### Owner data

The archive changed during the review window, and not from this review. Between 12:17:26 and
12:18:44 (+08:00) a third vintage was issued into the shared `.local` tree:
`outlooks/outlook-2026-11-system-v3.json`, `values/outlook-2026-11-system-v3.json` and
`.availability.json`, and in `.local/price` the files `known_outages.csv`,
`method-2026-11-system-v3.json` and `preview-2026-11-system-v3.json`, with `digests.json` gaining
the `known_outages.csv` row. The writers are `scripts/outlook/issue.py` and
`scripts/outlook/availability.py` (OUT-3's issue flow). I ran neither. None of my commands or probes
imports `src.outlook` writers or `src.price` builders, and the only outlook inputs the probes built
were `None` or scratch. The 29 other pre-existing files are byte-identical before and after.
`verify()` reports no problem. The orchestrator should confirm that the third vintage was the owner's
OUT-3 run. The expected `2/0/0/0` no longer holds for that reason.

### Attack checks

| Check | Result |
|---|---|
| (a) The cookie | `Set-Cookie: __session=<value>; Max-Age=432000; Path=/; HttpOnly; Secure; SameSite=Lax` on a real FastAPI answer (probe), five days. Every read goes through `GoogleUsers(read_cookie)` with `verify_session_cookie(..., check_revoked=True)` (pinned in `test_hosted_config`). Forged, expired and revoked cookies (the fake reader raises) and a cookie for an unverified Google account or the anonymous provider: `user` None, `require` raises `NotSignedIn` (401), `whoami` `signed_in: false`, on every path. Two `__session` cookies: the first wins. A value with a space or comma: not a cookie. No script reads it (`alerts.js` holds no `document.cookie`, pinned) |
| (b) CSRF | A POST takes the cookie only with `Sec-Fetch-Site: same-origin`, or without fetch metadata when `Origin` is a listed origin (trailing slash tolerated). Rejected: no header, `same-site`, `none`, `cross-site` with a listed `Origin` (metadata wins), a foreign origin, `null`, the prefix trick `https://grid-nowcast.web.app.evil.example`. A spoofed listed `Origin` with no metadata is accepted, which no browser can send cross-site; a non-browser client that can forge headers must already hold the cookie. Session start and end make the same check (403 `CROSS_SITE`). Real stack (my probe on FastAPI with `BodyLimit`): a cross-site ask with a valid cookie answers `signed_in: false`, a same-origin one `signed_in: true`, an `Origin`-only one from a listed origin `signed_in: true`, and an anonymous confirm answers 401. On the test app (`TheSameOriginSession`): the cross-site ask refuses its write under `needs_sign_in`, and a cross-site confirm with the cookie answers 401. No GET writes: the six GET handlers (`threads`, `threads/{id}`, `cases`, `drafts`, `queue`, `whoami`) only read the store; a cross-site GET with the cookie reads (Lax sends it only on a top-level navigation, and CORS keeps the answer from the other site) |
| (c) The editor rule on `ask` | See the judgements |
| (d) Token verification and privacy | The ID token is verified by the alerts' `GoogleUsers.hosted` (`verify_id_token(..., check_revoked=True)`) before `create_session_cookie(expires_in=timedelta(seconds=432000))`; the cookie by `verify_session_cookie(..., check_revoked=True)`. No `logging` or `print` in `src/agent`; the request middleware logs a request id and status only. Owners are `sha256('agent-owner|' + uid)[:32]`, so no email or token names a document. The email goes back only to its own caller (`session`, `whoami`) |
| (e) `__session` and the rewrite | Sound: Firebase Hosting forwards only the cookie named `__session` to Cloud Run; the template's `"**"` rewrite already sends `/api/agent/*` and `/book` to the service. Whether the rewrite forwards `Sec-Fetch-Site` is unverified (release condition); a same-origin `fetch` POST carries `Origin`, so the fallback covers `web.app` |
| (f) Classification | The seven contract routes and the three session routes are in `AGENT_ROUTES`, called anonymously (401, 422, 403, 503 refusals and a 200 ask) and pinned `no-store`; `/book` revalidates. Hosted mode mounts the same functions through the same `_assemble`, as the alerts routes are. Real stack: every agent and session answer `Cache-Control: no-store` (a 405 too); `GET /book` 200 `no-cache` |
| (g) Anonymous asks from the plan sets only | `ask` replays when the owner is None and a `recorded_answers` provider exists; the served service always passes `PlanSets.answers`, and its records provider has no base set, so signed-in asks replay too. No match is `insufficient` under `no_record`. `live_backend` is None: the planner and the day meter never run in the served service. Real stack: a recorded wording answers `composed`, `budget` None; an unrecorded question answers `no_record` |
| (h) The book wiring | `query_impact` calls `impact(account_ids, outlook_id, window, cutoff)` (pinned with a recording double). A real adapter refusal is a refused receipt under the adapter's key (`window_required`), with no result. The fallback table has the four arguments, and `catalogue.load()` reads `src.judgment.actions`, which has them too. `AgentRecords` adds `adapter.vintages()` to the outlook record (tested with a base set; inert in the served service, which has none). Probe without an archive: `vintages() == []`, `impact` refuses `vintage_unknown`, `exposure` still answers |
| (i) The book page | `/book` served like `/outlooks`, in `GRID_FILES`, `book/` in `GRID_DATA_NAME`, staged, in both `SITE_ROUTES` (pinned equal), classified; the bake runs `bake_book.files()` on the synthetic inputs only, and the bytes equal the committed fixture by digest. BOOK-3's no-route test is replaced as BOOK-3 asked. The Book entry is on exactly `index`, `catalog`, `assets`, `asset`, `alerts` and `book` (current on `book`). For the CSS change see finding 2 |
| (j) Firestore rules | Two `match` blocks, each `allow read, write: if false`, with no `request.auth`; `firestore.json` names the file beside it. `deploy.sh` step 9a deploys it after the stage check and before Hosting; a rollback deploys no rules (pinned). For the ordering see finding 1 |
| (k) Other lanes' bake output | Unchanged: the four-way bake test holds every non-book file byte-identical; the fixture plan sets' diff is the two digests only (`SITE_ROUTES` grew) |
| (l) Pages a pending task owns | `event.html` (RAG-5), `ask.html` (DOCK-6), COPY-1's `outlooks`, `register` and `models` pages, and the generated `explain` and `paper` pages are unchanged. `map.html` changes only in the generated contract block (`build_map_page.py --check` passes) |
| (m) Contract and capability rows | See finding 3 and the judgements |
| (n) Copy | The three capability notes are short, plain sentences; `repo.py check` passes. The nav entry is the one word "Book" |

### Findings

1. **minor. The rules ship after the revision that serves the agent is live.** `scripts/deploy/deploy.sh:425-430`
   (step 9a) against `:395` (step 6, `update-traffic ... =100`). Bears on note item (3) and on
   the step's own comment: "The rules ship before the site, so no release serves the agent while
   its store is writable from a browser". The Cloud Run revision that mounts `/api/agent/*` takes
   all traffic at step 6. The template's existing `"**"` rewrite already targets that service, so
   `web.app` serves the agent routes from step 6 on, before step 9a publishes the rules. This is minor
   because the service writes with the Admin SDK only, no client Firestore SDK is in the tree, and the
   window lasts only for the deploy, if the project's current rules allow client writes at all. Fix
   (both files are in the allowed paths): move 9a before the image deploy or the traffic shift and move
   the order pin in `test_the_release_ships_the_firestore_rules_that_deny_every_client_write`, or
   correct the comment and state the window.

2. **minor. The header claim holds only on an empty page.** `src/grid/grid.css:51` and `:59-62`;
   packet section 1 (`grid.css` row). Bears on the note's Book entry and on the packet's stated proof.
   The packet says the old padding made the eleven-entry grid page 19 px wider than 1280 and that the
   new values "keep the eleven on that line". Headless Chromium, home page, 1280 wide:

   | Page state | `259d77f6`, 10 entries | HEAD, 11 entries | HEAD HTML with the old `grid.css` |
   |---|---|---|---|
   | no replay data (the clock shows a dash) | 1 row, no overflow | 1 row, no overflow | 2 rows |
   | fixture bake served (the clock shows the date and time) | 2 rows, `scrollWidth` 1297 | 2 rows, `scrollWidth` 1291 | 2 rows, 1315 |

   With data loaded, the header already wraps and runs 17 px past the viewport on main. After this
   change it runs 11 px past. That is a 6 px improvement, not a regression, but the CSS comment and
   the packet overstate it. At 390 nothing changes: the alerts, book and home pages wrap to two rows
   with no horizontal scroll before and after. The catalog page's 2 px overflow at 390 is the same
   before and after. Hand to DOCK-6, whose contract section 6 item is the dock's side placement with a
   browser check at 390 and 1280: the header line has to be solved with the clock present.

3. **minor. Q10 `forecast_and_exposure` drops a rung and a caveat.** `docs/product/integration-contract.json:481-486`
   (and the `.md` row and the `map.html` cell). Bears on the brief's output line "a row per new
   answer surface with its ladder step". `asked` rises from selected design to tests executed on the
   dock (`src/grid/ask.js`, `tests/test_grid_ask_page.py`). That is sound: the fixture `home` plan
   set answers "What is exposed?". `forecast_and_exposure` moves from *recorded run*
   (`docs/work/price-outlook/impact.md`, an impact on a synthetic book) to *tests executed* (the book
   page). The ladder permits it, because the word never rises above its record. But the cell now sits
   below the evidence the project already holds (the capability map ticks the Impact record up to
   deployed), and it drops "no customer or contract record exists". Reading: acceptable as a surface
   change. Recommendation for the orchestrator (not blocking): keep the impact record as the cell with
   its caveat and name the book page in the capability row until the page is deployed, or keep the
   book page and restore the caveat sentence.

4. **nit. Four test names now say the opposite of their bodies.**
   `tests/test_grid_book_page.py:431` (`..._no_entry_current_and_no_book_entry`), `:441`
   (`test_no_other_page_gains_a_book_entry`), `:453` (`test_the_application_has_no_book_route_yet`),
   `tests/test_cache_headers.py:1031` (`..._the_same_ten_links_...`). The docstrings say the pins moved.
   Rename them the next time each file is touched.

### Judgements asked of the reviewer

- **(c) The editor rule on `ask`: accept.** `hosted_alerts` reads `NOWCAST_ALERT_EDITORS` from the
  environment, and `deploy.sh` sets none. Unset means every signed-in Google (verified) or team password
  account, the judges' accounts included. So decision 13 ("signed-in users only, judges included")
  holds as deployed. The rule closes DOCK-3's observation 2: an account outside a set list cannot write
  drafts, pins or search receipts it cannot read back. Condition: if the list is ever set, the judges'
  accounts go in it. `whoami` returns `editor`, so DOCK-6 can word the signed-in non-editor state. Today
  that user's ask answers `signed_in: false`, which the dock shows as "sign in to ask live".
- **The session design: sound.** See attack rows (a), (b), (d) and (e). One advisory beyond the
  packet's residual risk (1), which covers `auth_time` only: sign-out clears the cookie but revokes
  nothing on the server, so a copied `__session` value stays valid to day five. `revoke_refresh_tokens`
  on sign-out would make `check_revoked` end it, at the cost of signing out every device.
- **Q10 at "tests executed".** See finding 3: permitted, recommendation recorded.
- **The packet's hand-backs to the orchestrator, judged as recorded conditions.** (a) The rules deploy
  replaces the project's current rules with deny-all: correct and necessary. Check that no client reads
  Firestore and that the deploying credential may publish rules. (b) `createSessionCookie` on the
  runtime account (`datastore.user`, `firebaseauth.viewer`) is unverified. Until it is granted, session
  start answers 401 and pages stay signed out without an error page (the code path is a refusal, read).
  (c) The optional settings, and both outlook writes refuse `no_write_path` in the image: correct. (d) No
  book vintages in the image, so a served `query_impact` refuses `vintage_unknown` (probed) and the book
  page is unaffected: correct. (e) `build_all.py` bakes the book by default, and the Dockerfile's one
  `COPY build/grid-data` carries it: correct. (f) `agent-contract.md` section 4 should list the three
  session routes: agreed (outside these paths). (g) The capability map's "Generated view" row is stale,
  but `tests/test_grid_map_page.py` pins it: agreed. (h) Board rows R5 (answered) and R7 (open on CASE;
  `save_decision` has its port over `commit_review`, no actor mapping, refuses `no_write_path`):
  accurate.
- **Scope deviations, on the orchestrator's own record, not findings.** The brief's output "refuses
  view.v3 plan sets with text" was not met, by the orchestrator's `d5f172fe`, which keeps accepting
  view.v3 while the live snapshot's staged sets are view.v3. "Copied by digest from the snapshot"
  became "built by `bake_book.files()` from the synthetic inputs", per note item (5).

### Release conditions (before any release that serves this branch)

1. Verify on a deployed revision that the Hosting rewrite forwards `Sec-Fetch-Site`. The `Origin`
   fallback covers `web.app` if it does not.
2. A direct visit to the Cloud Run `run.app` URL gets 403 `CROSS_SITE` on session start when the
   browser sends no fetch metadata (that origin is not listed). Accept this, or add the URL through
   `NOWCAST_PUBLIC_URL` (one origin only).
3. Grant `createSessionCookie` to the runtime service account, or accept that every page stays
   signed out.
4. Confirm the deploying credential may publish Firestore rules and that no client reads or writes
   Firestore today. Prefer the rules before the traffic shift (finding 1).
5. The image holds no book vintages, so a served `query_impact` refuses `vintage_unknown`. Bake the
   synthetic vintages into the image, or accept the refusal.
6. **The live staged plan sets cover only `ask` and `syn-bay-unit-2-trip`.** `PlanSets` over a scratch
   copy of `.local/grid-snapshot/views` reads both view.v3 files (3 views each, cutoff
   `2026-10-17T00:00:00Z`), but `home`, `models`, `outlooks` and `register` have no set. On the served
   site an anonymous or signed-in ask from the home page (page key `home`, thread `desk`) answers
   `insufficient` under `no_record` for every question. Only the `/ask` panel and the synthetic event's
   thread have recorded answers. This is not a DOCK-5 defect: the fixture bake proves the wiring. It is
   a condition for DOCK-4 (record the page plan sets under view.v4) or for the orchestrator (stage the
   page sets) before the dock is released.
7. The owner should confirm the third vintage issued during this review (see "Owner data").

### Verdict

**accept** at `7ef9e4b2` (code `3eb751d2`). Every acceptance line is proved:

| Acceptance line | Proved by |
|---|---|
| every new route classified, `/book` in SITE_ROUTES, anonymous writes 401 `SIGN_IN_REQUIRED`, anonymous asks served recorded answers | `RouteTable` and `SectionNavigation` in `test_cache_headers` (also on the real server library), both `SITE_ROUTES` pinned equal, `TheSameOriginSession`, `RecordedAnswers`, `AgentWiringTests`; the real-stack probe (401 on confirm, queue and cases; 200 `composed` on a recorded wording) |
| `build_all.py --check` with and without the plan sets and the book; no other lane's output changes | my four `--check` runs; `BuildAllTests.test_a_fresh_bake_passes_with_and_without_the_agent_plan_sets_and_the_book` and `BookPageFiles` (byte identity); the plan-set diff is two digests only |
| no page of DESK-8 or COPY-1 changes; the Book entry waits on their pages; `open` reaches `/book` everywhere | the changed-file list against `owned_paths`; `test_no_other_page_gains_a_book_entry`; `SITE_ROUTES` with `/book` read by `open` |
| every existing assertion kept; the full offline suite passes; no live call | 40 methods added, none removed; the removed assertions are the BOOK-3 pins the note moves; `Ran 3193`, OK; no network, model or cloud call in any test or probe |

No major finding stands. Findings 1 to 3 are minor and finding 4 is a nit; none needs rework before
the merge. The orchestrator should schedule finding 1 (the rules order) before the next release, pass
finding 2 to DOCK-6's layout check, rule on finding 3, and carry release conditions 1 to 7.
