# BOOK-1 review record

## Round 1: accept

- Task: BOOK-1, the synthetic book (lane BOOK, milestone M15).
- Branch: `task/BOOK-1`. Commit under review: `19b48b1d`. Task commit `e792743c`, merge of origin/main `9f0675f0`.
- Base: `971885b0` (origin/main, merged into the branch). The task commit was built from `876ae432`.
- Reviewer: Claude Opus 5.5 in-session subagent, read-only, independent of the author (the executor). The owner's rule of 17 October allows this seat while the Codex reviewer has no credits.
- Worktree: `.local/wt/BOOK-1`, interpreter `/usr/bin/python3`. No network, model or cloud call. The only file written is this record.
- Verdict: **accept**. Every acceptance line is proved by a check I ran. No major finding stands. Five minor findings follow, with the changes I recommend.

### Commands and results

| Command | Result |
|---|---|
| `python3 scripts/plan.py brief BOOK-1` | Brief printed. Allowed paths: `src/book/`, `scripts/book/`, `tests/fixtures/book/`, the two test files, the packet, `tasks.json`, `PROGRESS.md`, this record |
| `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` | `Ran 2650 tests in 272.405s`, `FAILED (errors=1, skipped=115)`. The one error is `setUpClass (test_corpus_index.IndexScriptTests)`: `ModuleNotFoundError: No module named 'pypdf'`. This is a known environment limit, and BOOK-1 touches no corpus file. The numbers equal the packet's post-merge row |
| `/usr/bin/python3 -m unittest -v tests.test_book_generate tests.test_book_records` | `Ran 30 tests`, **OK**, none skipped. The exact private-list comparison ran, because `.local/price` links to the main checkout here |
| `python3 scripts/plan.py scope BOOK-1 971885b0` | `OK: all changed files inside BOOK-1 allowed paths`, exit 0. Note: `plan.py scope BOOK-1 --base 971885b0` is not a form the tool accepts. It passes `--base` to `git diff` as the base and prints git's help |
| `git diff --name-status 971885b0..HEAD` | 8 added files (`src/book/` 3, `scripts/book/generate.py`, the fixture, two new test files, the packet), 2 modified coordination files (`PROGRESS.md`, `tasks.json`). No existing test file changed |
| `git show --stat 9f0675f0` | The files outside the allowed paths arrive only through the merge of origin/main |
| `python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `python3 scripts/repo.py check` | `Checked 601 Markdown files, 3838 local links, 5 skills; bootstrap 1399 words.` **PASS** (before this record) |
| `PYTHONHASHSEED=1 … scripts/book/generate.py --out <scratch>/a.json` and `PYTHONHASHSEED=987 … --out <scratch>/b.json` | Both write digest `f04af8d4…bfc1`. `sha256sum` of a, b and the committed fixture: all `c27c1440e7c6…7c68`. `cmp` says identical |
| `scripts/book/generate.py --check` | `unchanged`, exit 0 |
| `scripts/book/generate.py --seed 7 --out <scratch>/a.json` over the seed-20261018 file | `refused`, exit 2, file kept |
| `git ls-files \| grep -i private` | no file. `.gitignore` holds `.local/` |
| `grep -rEoh '[0-9]{2}SYN…'` over the main checkout's `.local` data (csv, jsonl, json) | 1196 distinct resource-form names. The only `\d\dSYN` names are the fixture's 14 aliases, found in worktree copies under `.local/wt/`. No real resource name in the local data has a `SYN` stem |
| In-memory comparison of the fixture with `.local/price/portfolio-nodes-private.csv`, `portfolio-alias-private.json` and `portfolio-synthetic.json` (no string printed) | No alias, account name or node code of the private files is in the fixture. The only shared tokens are generic words: `region`, `price`, `contract`, `nodes`, `synthetic` |
| `grep -rIil` of the ten account names over `.local` (worktrees excluded) | Four hits (Kawayan, Lakan, Mabini, Silangan), all inside public place names in DOE project lists, a WESM manual and a Natural Earth province file. None is in a company file |
| Probes of `records.validate_book` on hand-edited records | See findings 2 and 3 |
| `repo.PASSIVE` over `records.LABEL`, `UNITS` and `METHOD` | `LABEL` hits "is invented". See finding 4 |
| `grep` for `urllib`, `requests`, `socket`, `http` in `src/book`, `scripts/book`, the two tests | no hit. The code is stdlib only |

### Acceptance lines

1. **Deterministic from the seed, byte-identical fixtures (tests executed). `synthetic: true` on every account, contract, node and profile row.** Proved. The stream is SHA-256 over seed, label and counter (`src/book/generate.py:71-87`), so it has no global state. I ran the command twice under two hash seeds, and both outputs equal the committed fixture byte for byte. `Determinism.test_two_runs_give_byte_identical_output` and `test_script_writes_the_committed_fixture_bytes` pass. Every row sets `synthetic: True` (`src/book/generate.py:140,146,153,183`). `validate_book` refuses a row without it even after a reseal (`tests/test_book_records.py:77-82`).
2. **No real customer, contract, meter, node code or volume. Aliases follow the profile's form. A test checks that none equals an alias of the private list. The private list is absent from the repository.** Proved. Every alias passes `src/adapters/wesm/registry.py` `RESOURCE` and `region_of` returns its region (`tests/test_book_generate.py:159-170`). No alias matches `ALIAS_PATTERN` (`N\d{2}`). The exact comparison against the private file ran and passed here. `git ls-files` lists no private file. Names, prices, MW and terms come from a stated rule and an invented name list. My sweeps found no company string in the fixture.
3. **Shaped like a retailer's book: at least 8 accounts over three regions, at least 12 load nodes, both contract kinds, hours and terms stated. Every peso and MW labelled a method demonstration.** Proved. The fixture holds 10 accounts (4, 3, 3), 14 nodes (5, 5, 4), 22 contracts (9 fixed price, 13 time-of-use block) and 14 profile rows of 24 hours. Every contract states `hours`, `term_start` and `term_end`. The record carries `units` with "a method demonstration" for price, demand and contract volume, and the label sentence. `Shape` and `Record` tests pass. Contracted MW never exceeds demand in any hour, and I read the arithmetic in `_contracts_for` (`src/book/generate.py:158-184`).
4. **Existing assertions kept, the full suite passes, no live call.** Proved. BOOK-1 touched no existing test file. The suite is green apart from the pypdf limit. No network import exists in the new code.

### Findings

| # | Severity | Location | Acceptance line | Finding | Recommended change |
|---|---|---|---|---|---|
| 1 | minor | `docs/work/desk-agent-and-book-2026-10-18/book-1.md:82-84` | 2 (and the BOOK-2 hand-off) | The alias choice is sound. A `SYN` stem inside the WESM resource form passes `RESOURCE` and `region_of`. No real local resource name has that stem. It stays apart from the private `N01` to `N12` aliases. But the note to BOOK-2 is wrong. It says "BOOK-2 owns `src/price/impact.py` and must widen the pattern". The BOOK-2 brief in `docs/work/tasks.json` does not list `src/price/impact.py` in its owned paths. Its acceptance says "src/price/impact.py is imported, never edited". The epic record (`docs/work/platform-epics-2026-10-17/strategy.md:269`) lists the file under BOOK, but the task graph governs. Also, a wider pattern would not help: `pair_positions` (`src/price/impact.py:577`) asks for each node in the nodal series of the scored bands, and those series are the private aliases. So the note hands BOOK-2 a stop condition. | Keep the alias form. Rewrite the note: BOOK-2 builds `NodePosition` rows (or its own equivalent) in `src/book/impact.py`, keyed by the book's node id and priced against the regional band of the vintage (p10, p50, p90 by digest). It never edits `ALIAS_PATTERN` and never calls `load_portfolio` or `pair_positions` on the book. The orchestrator can carry this sentence into the BOOK-2 brief. |
| 2 | minor | `src/book/records.py:96-122` | 1, 2 | `validate_book` says it raises `BookError` for a malformed record. A row without `region`, `kind`, `mw_by_hour` or `alias` raises `KeyError` instead. I probed each one on a resealed copy of the fixture. | Read row fields with `.get` or catch `KeyError` and `TypeError` and raise `BookError("BOOK_INVALID", …)`. Add one refusal test for a missing field. |
| 3 | minor | `src/book/records.py:103` | 2 | The validator checks the alias form only. A Mindanao node with a Luzon prefix (`01SYNZZ_L09`) passes `validate_book`. The fixture is safe because `test_the_profile_maps_each_alias_to_its_region` checks it, but a hand-edited book is not. | Also require that the alias's two-digit prefix lies in `PREFIX_RANGE` of the node's region. |
| 4 | minor | `src/book/records.py:22` and the packet | advisory (BOOK-3 carries the copy rules) | The label sentence "… every account, contract, node and volume is invented" trips the repository's own passive rule (`scripts/repo.py:162`). The digest seals the label and the validator pins it. BOOK-3 must show this label on every screen under the copy rules. So a change later costs a new fixture digest. The packet also has six semicolons in table cells (lines 14, 67, 69, 71, 73, 99), six rule sentences of 20 words or more (lines 23-24, 29-31, 34-35, 39, 40-41, 42-43) and passive forms (lines 7, 44, 73, 116). BOOK-1 has no copy-rule acceptance line, and `repo.py check` passes. No text uses "stale". | Change the label now, before BOOK-2 and BOOK-3 read the digest. For example: "Synthetic book, a method demonstration: no account, contract, node or volume in it is real." Regenerate with `--force`, update the digest in the packet and the label pin in `tests/test_book_records.py:21`. The packet prose may stay as it is. |
| 5 | minor | `tests/test_book_generate.py:201-206`, packet line 78 | 2 | The packet says "The test never prints a string from it". On a failure, `assertNotIn(alias, strings)` prints the whole set of private strings, and `assertNotIn(s, text)` prints the private string. A red run would put private node codes into a log. The test passes now, so nothing leaked. Also, `test_every_contract_is_live_on_the_snapshot_end_day` (`:143-145`) checks only the end date. The start dates are early enough by construction (`TERM_STARTS` ends 2026-07-01). | Use `assertFalse(alias in strings, "an alias equals a private-list string")` and the same for the text check, so a failure names no private string. Add `term_start <= "2026-10-14"` to the live-contract test. |

### Notes, not findings

- Profile rows are per node and carry `account_id`. The title asks for "a 24-hour demand profile per account and node". An account's profile is the sum of its nodes' rows (packet line 86). BOOK-2 can derive it, and no acceptance line asks for a separate account row.
- Peak and off-peak blocks share the kind `tou_block` and differ only by `hours`. BOOK-3 will need to name them from the hours.

### Verdict

**accept.** Every acceptance line is proved by a check I ran. All findings are minor. I recommend that the orchestrator fix finding 1 (the BOOK-2 note) and finding 4 (the label) before BOOK-2 starts, because both decide what BOOK-2 and BOOK-3 build on. Findings 2, 3 and 5 can go in the same small follow-up commit on `task/BOOK-1`, or into BOOK-2.

## Round 2: accept

- Commit under review: `c57a9350` (rework of the round 1 findings, one commit over `19b48b1d`). Base: `971885b0`.
- Reviewer: the same Claude Opus 5.5 in-session subagent, read-only, independent of the author. Worktree `.local/wt/BOOK-1`, interpreter `/usr/bin/python3`. No network, model or cloud call.
- Verdict: **accept**. All five round 1 findings are closed in the code and the tests. No finding of any weight remains.

### Commands and results

| Command | Result |
|---|---|
| `git diff 19b48b1d..c57a9350` (read in full) | 5 files: `src/book/records.py`, `tests/test_book_generate.py`, `tests/test_book_records.py`, the fixture (label and digest lines only) and the packet. `tasks.json` and `PROGRESS.md` do not change |
| `/usr/bin/python3 -m unittest -v tests.test_book_generate tests.test_book_records` | `Ran 36 tests in 0.068s`, **OK**, none skipped (30 before, 6 new in `MalformedRows`) |
| `/usr/bin/python3 -m unittest discover -s tests -p "test_*.py"` | `Ran 2656 tests in 310.478s`, `FAILED (errors=1, skipped=115)`. The one error is `setUpClass (test_corpus_index.IndexScriptTests)`, `No module named 'pypdf'`, the known environment limit. 2656 is round 1's 2650 plus the 6 new tests |
| `python3 scripts/plan.py scope BOOK-1 971885b0` | `OK: all changed files inside BOOK-1 allowed paths` |
| `python3 scripts/plan.py check` | `OK: 135 tasks, 9 gates` |
| `python3 scripts/repo.py check` | `Checked 602 Markdown files, 3839 local links, 5 skills; bootstrap 1399 words.` **PASS** |
| `git diff --check 971885b0..HEAD` | clean, exit 0 |
| `/usr/bin/python3 scripts/book/generate.py` | `unchanged: … digest bfa951be548462eff9f50f6e51cf5ede43c02fe002d4eea9c48c4eae4c9874a1`, exit 0 |
| The command run twice more to scratch files under `PYTHONHASHSEED` 3 and 4242 | Both files and the committed fixture: sha256 `ff3d5691df29…160e` |
| `compute_content_digest` of the committed fixture | `bfa951be…74a1`, equal to the stored `content_digest` and to the packet |
| Probes of `validate_book` on resealed copies with `region`, `region_code`, `kind`, `mw_by_hour`, `alias` or `term_start` removed, or an integer alias | each one raises `BookError` |
| A Mindanao node given the alias `01SYNZZ_L09` | `BookError`: "node alias prefix is outside the node's region" |
| `repo.PASSIVE` over the new `LABEL` | no hit |

### The five findings, checked again

1. **Closed.** The BOOK-2 note (`book-1.md:82-85`) now says BOOK-2 does not own `src/price/impact.py`, must not widen `ALIAS_PATTERN`, builds its own rows in `src/book/impact.py` keyed by node id, and never calls `load_portfolio` or `pair_positions` on the book. This agrees with the BOOK-2 brief in `tasks.json`.
2. **Closed.** `validate_book` (`src/book/records.py:84-93`) wraps the checks and turns `KeyError`, `TypeError`, `AttributeError` and `IndexError` into `BookError("BOOK_INVALID", …)`. `MalformedRows` tests a missing region, kind, `mw_by_hour` and alias, and a wrong type. My own probes agree.
3. **Closed.** `src/book/records.py:114-115` checks the alias prefix against `PREFIX_RANGE` of the node's region. The form check runs first, so the `int()` call always gets two digits. `test_an_alias_prefix_outside_the_nodes_region_is_refused` tests it.
4. **Closed.** The label is now "Synthetic book, a method demonstration: no account, contract, node or volume in it is real." It passes the repository's passive rule. The label pin, the fixture and the digest agree. The packet's table cells have no semicolons now, and the long rule sentences are split.
5. **Closed.** Both private-list checks use `assertFalse` with a fixed message, so a failure names no private string. The snapshot-day test checks `term_start <= "2026-10-14"` as well as the end date.

The edits in the two test files change only BOOK-1's own new tests. Each changed check is at least as strict as before, and no other test file changed. So the line "every existing assertion in the touched test files is kept" still holds.

### Note, not a finding

- `book-1.md:60` quotes the label with a doubled full stop: `…is real.". The`. This is cosmetic. It can be fixed in any later commit to the packet.

### Verdict

**accept** for `c57a9350`. Every acceptance line is proved by a check I ran, in round 1 and again here. The orchestrator may set BOOK-1 to done.
