
## Designated review (reviewer seat, independent; the quoted output names the reviewer; commit `6de6e1e4`, 2026-10-17 22:07, overnight round 1)

> Reviewer: Claude Opus 5.5 (claude-opus-5-5) through the claude CLI in print mode, read-only, independent of the author; fallback while the Codex reviewer is unavailable.
> 
> **Verdict: accept.** I reviewed `6de6e1e4`. All three acceptance items hold, and I re-ran every check myself. The one important finding is a naming clash in MAP-1's brief, not in this branch, but it should be fixed before MAP-1 starts.
> 
> ## Commands run in this seat
> | Command | Result |
> |---|---|
> | Verify command (`tests.test_cache_headers … tests.test_paper_page`) | `Ran 219 tests in 22.098s` · **OK (skipped=12)** |
> | `/usr/bin/python3 -m unittest discover -s tests` | `Ran 2332 tests in 205.388s` · **OK (skipped=62)** |
> | `/usr/bin/python3 scripts/plan.py scope ROUTES-1 feat/product-gap-d` | `OK: all changed files inside ROUTES-1 allowed paths` |
> | `build_explainer.py --check` / `build_paper.py --check` | both exit 0 |
> | `plan.py check` / `repo.py check` | `OK: 117 tasks, 8 gates` / **PASS** (563 files, 3623 links) |
> 
> There is no browser here, so I did not re-run the 1280 and 390 px page checks. No runner log for ROUTES-1 exists under `.local/logs` in this worktree, so the browser runs rest on the record (§7 rows 6–9) alone.
> 
> ## Checklist
> 1. **Acceptance items met by checks that ran: yes, with one caveat.**
>    - Routes classified: `test_cache_headers.py:921-926` and `LOCAL_ROUTES`.
>    - Routes staged: the new staging test checks all twelve file names and that the staged home page has no `/ask` link.
>    - Builder `--check` runs pass and the full suite is green.
>    - The shells carry one sentence each ("This page is being built.").
>    - Item 3 (the orchestrator removes a nav entry if a page brief does not land) is written down in §6. It is an orchestrator action, so there is nothing to demonstrate yet.
>    - Caveat: "every existing assertion kept" is not literally true. See finding 2.
> 2. **Scope: yes.** `plan.py scope … feat/product-gap-d` printed OK. All new `src/grid/*` and `tests/fixtures/*` files fall under the allowed prefixes `src/grid/`, `tests/fixtures/grid/` and `tests/fixtures/explainer/`.
> 3. **No frozen contract or acceptance text changed: yes. Tests weakened: no.**
>    - One assertion was replaced because the outputs require it: `test_paper_page.py` `assertNotIn("<script")` became "no inline script, plus the exact `ask.js` tag". The paper page must now load `ask.js`.
>    - The server's policy allows it: `CONTENT_SECURITY_POLICY` has `script-src 'self'` (`src/api/__init__.py:70`).
>    - The record states the change in §5.
> 4. **No new dependency, service or call: yes.** The shells are comment-only; the routes reuse `page_response` and `declaring`.
> 5. **Mode labels: n.a.** No data or model output is shown.
> 6. **Unknowns stayed unknown: yes.** No numbers appear beyond command results. The DESK-7 placement is recorded as drift, not invented.
> 7. **The record has interpreter, commands, results, unfinished items and next action: yes.** See §7, §10 and the post-commit table.
> 8. **No contradiction with the strategy or plan: yes for this work.** The plan itself has a clash, in finding 1.
> 
> ## Findings
> 1. **important** | `src/grid/map.html:12,14` and MAP-1's brief in `docs/work/tasks.json`
>    - **Failure:** The brief told ROUTES-1 to make shells for "the eight js and css files the page briefs will create", but `map.js` and `map.css` already exist. They are the home page's map canvas (`index.html:11,14`, `window.GridMap`). So `map.html` loads the home canvas instead of shells. MAP-1's brief says "map.html, map.js, map.css replacing the shell", so following it would overwrite the canvas.
>    - **Evidence:** `tests/test_grid_map.py:62-63` reads `map.js` and `map.css` and pins their values in plain Python, without node. An overwrite would fail loudly in any seat, so nothing breaks silently. But MAP-1 cannot run without touching shared files, which is the point of ROUTES-1. The record (§1) notes the two files already existed but does not warn MAP-1.
>    - **Correction:** before MAP-1 starts, the orchestrator revises MAP-1's brief. Either give the page its own file names, and add their shells to both `GRID_FILES` lists, the staging test and `test_grid_page`'s table, or have MAP-1 add to `map.js` rather than replace it. This cannot be fixed on `task/ROUTES-1` without choosing for the plan.
> 2. **minor** | `tests/test_paper_page.py:291-294`
>    - **Failure:** The new check would let a second external script through unnoticed.
>    - **Correction:** `assertEqual(['/grid/__NOWCAST_STAMP__/ask.js'], re.findall(r'<script[^>]*\bsrc="([^"]+)"', page))`.
> 3. **minor** | `src/grid/event.html:55-58`, record §3
>    - **Failure:** The record says "When DESK-7 lands, the mount is still after the desk line". That is an assumption. DESK-7 puts the desk line "under the title, before the tabs", and the tabs are inside `ev-main` (`event.html:82,111`). So DESK-7 could add its block between `ev-head` and the mount. VIEW-1 also expects the panel under DESK-7's AI reader card.
>    - **Correction:** add a line to DESK-7's brief: place the desk line before `#ask`.
> 4. **minor** | `src/grid/grid.css:58-61`, `src/grid/catalog.css:58-60`
>    - **Failure:** The nav padding change (8 px to 6 px) affects the nav on every page. The 1280 px measurement in the record is for the home page only, and I could not check any page in a browser here.
>    - **Correction:** before the batch deploy, re-run the page browser tests on the deploy build.
> 5. **minor (plan)** | ROUTES-1's `depends_on` lists DESK-7, which is still `pending`. The record states this; the orchestrator should note that the task ran ahead of one of its dependencies.
> 
> **Reason:** every acceptance item is met and re-run green in this seat. The one important finding is a file-name clash in MAP-1's brief, which the suite would catch loudly and which only the orchestrator can resolve. Fix it before MAP-1 is cut from this branch.


Verdict recorded by the overnight runner: **accept**. The orchestrator reads this record after the run.
