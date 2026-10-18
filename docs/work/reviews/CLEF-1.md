# Task record: CLEF-1 — Clef-flash container with /v1/systemone and local smoke test

Branch `task/CLEF-1`, commit is the head of this task branch (the commit that carries this
packet). Executor seat (DeepSeek V4.1 Flash) on 2026-10-12; **self-review, not independent** —
no reviewer has signed this record, so the task stays `in_progress`. Read-first files:
[AGENTS.md](../../../AGENTS.md), [milestones](../milestones.md),
[research 30](../../research/30-decision-models-and-energy-2026-10-11.md),
[probe-bundle intent](../probe-bundle/intent.md). Measurements and the fuller run account are
in [notes.md](../clef/notes.md).

## Changes

| Path | What |
|---|---|
| `scripts/clef/Dockerfile` | Multi-stage image; `LLAMA_CPP_REF=v0.6.0` pinned, `llama-server` built from `tools/`, static libs, non-root `clef` user, `/models` volume, healthcheck on `/health`, no credential accepted |
| `scripts/clef/docker-entrypoint.sh` | Resolves the single non-mmproj `*.gguf` (or `MODEL_FILE`) and execs `llama-server`; batch, context, GPU-layer and extra args from the environment |
| `scripts/clef/smoke.sh` | The verify command: offline checks by default; `--fetch`, `--post URL`, `--live` add network and container steps |
| `scripts/clef/smoke_check.py` | Request builder, frozen-contract validator, stub round trip, health wait, live POST, measurement writer (stdlib only) |
| `scripts/clef/build_native.py` | Builds the same pinned tag natively for a seat with a compiler but no container runtime |
| `scripts/clef/README.md` | How to run each path and what is live versus not |
| `docs/work/clef/notes.md` | Measured memory and latency, the recorded container stop, findings for other lanes |
| `docs/work/clef/smoke/request.json` | The saved System One request (synthetic placeholder state) |
| `docs/work/clef/smoke/response.json` | The saved System One response, 365 bytes, from the local run |
| `docs/work/clef/smoke/timing.json`, `measurements.json` | Latency, peak RSS, host facts, model identity and digests |
| `docs/work/tasks.json`, `docs/work/PROGRESS.md` | State `pending` → `in_progress` plus the log entry, same commit |

Weights are not in any of these paths: they live in `.local/clef/` (ignored), and the check
fails if a weight file is tracked or appears anywhere in the tree.

## Acceptance

| Item | Result | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | **Met by the first branch**: HTTP 200 in 13.7074 s from a real Clef-flash Q8_0 load, saved as [response.json](../clef/smoke/response.json); the container path that could not run in this seat is recorded in [notes.md](../clef/notes.md) | `POST http://127.0.0.1:8080/v1/systemone -> HTTP 200 in 13.707 s (364 bytes)`; `smoke_check.py check` prints `live response: 365 bytes, model='clef-flash', 2 answers, 0 contract errors` |
| Weights not committed | Met | `check` reports `[ok] weights not committed to the repository`; `git status --porcelain` lists only the four task paths |

The response is a real receipt: `q2_event_f0` choice `planned_outage` (p = 0.96497) and
`q7_sufficiency_f0` noul 0.05096 on a state that is explicitly synthetic and easy. It is not
evidence of model quality, and nothing here is case material.

## Verification (exact commands and results)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/clef/smoke_check.py check` (the body of the verify command `bash scripts/clef/smoke.sh`) | Seven `[ok]` checks, then `OK: offline checks pass and a saved live response is contract-valid` |
| `/usr/bin/python3 scripts/clef/smoke_check.py local-run --binary .local/clef/build/llama.cpp-0.6.0/build/bin/llama-server --ctx 8192` | `health: ready after 2.0 s`; `POST http://127.0.0.1:8080/v1/systemone -> HTTP 200 in 13.707 s (364 bytes)`; `OK: valid System One response saved …; peak RSS 10078996 KiB, latency 13.7074 s` |
| `/usr/bin/python3 scripts/clef/build_native.py --jobs 8` | `binary: …/build/bin/llama-server (17872 bytes)`, `version: 0.6.0-dev (build 97, commit 7534465)` |
| `/usr/bin/python3 scripts/clef/smoke_check.py fetch-weights` | `weights: …Clef-Flash-Q8_0.gguf (9657260192 bytes, sha256:87a232aa…)`; stalled once at 4.56 GB, completed on the Range-resume path |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests` … `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 41 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` (253 Markdown files, 1116 local links); the first run after the log entry caught a relative link in `PROGRESS.md` (`../clef/…` from `docs/work/`), fixed before the final run |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |

Every command in this table was re-run on the committed tree; the suite, `plan.py check`,
`repo.py check` and `scope` results above are from that final pass.

`bash scripts/clef/smoke.sh` itself could not be executed by this seat: the seat may invoke
only `/usr/bin/python3`, `git` and `scripts/h1/test.sh`, and a `bash` invocation returns
"This command requires approval" without running. The command above is the same code path
(`smoke.sh` execs `smoke_check.py` for every mode except `--live`), and the offline check is
what the verify command runs on a host without a container runtime. This is recorded as a seat
limit, not claimed as a pass of the shell wrapper.

## Findings and limits

1. **Frozen-shape mismatch (for the guardian, not patched here).** llama.cpp v0.6.0 answers
   `/v1/systemone` with `{"model", "answers", "usage"}`; the frozen port in the probe-bundle
   intent says `{'answers', 'model_version'}`. Per-question answers match, with `type` and
   `confidence` as extras. `HttpSystemOne` (CORE-3) needs a two-line mapping, or the port shape
   needs a new intent. No frozen file was touched; the validator accepts either identity field
   and prints which one it saw so the gap stays visible.
2. **The image was not built or run.** No docker daemon in this seat (no socket; only the
   Windows CLI) and no permission to call it. `--live` is unproven code.
3. **No GPU number.** Host has no GPU; L4 memory and latency stay UNKNOWN until CLEF-2.
4. **Pre-build flag corrections found by building for real:** `LLAMA_BUILD_TOOLS=OFF` removes
   the `llama-server` target in this release (tools/ holds it), and `LLAMA_USE_PREBUILT_UI`
   defaults to ON, downloading a UI bundle from a Hugging Face bucket; both are fixed in the
   Dockerfile and documented there.

## Unfinished items and next action

Unfinished: the container build/run and a real container memory measurement; a bundle-sized
latency measurement (32 questions, batch/ubatch sizing); the CORE-3 mapping decision above.

Exact next action: on a host with a Docker daemon run `bash scripts/clef/smoke.sh --live`
(weights already fetched) and then `/usr/bin/python3 scripts/clef/smoke_check.py check`, which
will validate the container's response and replace the native measurement. Review of this
record by anyone other than the author is the gate for `done`.

## Orchestrator run of `smoke.sh --live` (local Docker Desktop host, 2026-10-12)

The executor seat could not run docker; the orchestrator seat ran `bash scripts/clef/smoke.sh --live --no-fetch --port 18090`
from this worktree at `9ec21d0` on the owner's Docker Desktop (engine 29.6.1, 8 CPUs, no GPU, 19.5 GiB visible to the engine).

| Step | Result |
| --- | --- |
| image build (llama.cpp `v0.6.0`, multi-stage) | OK; `nowcast-clef:local` `sha256:b62457d5…` |
| container start, `/health` | 503 while loading, then healthy (`docker ps` shows `(healthy)`) |
| `POST /v1/systemone` with the saved request (`sha256:d8fa1805…`) | HTTP 200, 364 bytes, **46.7446 s** on CPU; `docs/work/clef/smoke/response.json` rewritten and contract-valid (`smoke.sh` offline check: `OK: offline checks pass and a saved live response is contract-valid`) |
| container memory (`docker stats`) | 1.761 GiB / 19.53 GiB (9.01 %); the 9.66 GB GGUF is mmapped from the read-only volume, so RSS understates the working set compared with the native run's 10.08 GB peak |
| cleanup | `scripts/clef/smoke.sh` aborted at line 81 with `keep: unbound variable` (the `cleanup` trap read a `local` of `live()` after `set -u`), leaving `clef-smoke-381720` running; the orchestrator stopped it by hand and changed that one line to `"${keep:-0}"`. The reviewer should confirm the trap now removes the container on both paths. |

Acceptance item 2 (container answers the smoke request) is therefore demonstrated on a host with a container runtime;
measurements are in `docs/work/clef/smoke/measurements.json` and `timing.json`. The llama.cpp answer-shape finding for
CORE-3 (`{"model","answers","usage"}` vs the frozen `{"answers","model_version"}`) stands and is left to CORE-3's review.

## Interim review (orchestrator seat, Fable, commit c74a73d, 2026-10-12)

Independent of the author (executor seat wrote the code; the orchestrator seat ran `--live` and patched one line). Interim because the
designated reviewer (codex) is out of credits; **this section is a review-first list for the owner and does not set the task `done`.
The designated review supersedes it.** Reviewed in the worktree on `task/CLEF-1` at `c74a73d`; no docker, no network, no file
edited except this append.

### Commands run

| Command | Result |
|---|---|
| `bash scripts/clef/smoke.sh` (verify command, offline) | exit 0; seven `[ok]`; `live response: 365 bytes, model='clef-flash', 2 answers, 0 contract errors`; `measurements: mode live_inference, runtime docker, memory 1.761GiB / 19.53GiB, latency 46.7446 s`; `OK: offline checks pass and a saved live response is contract-valid` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests in 3.698s` `OK` |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` (packet says 41: the base branch gained a task since; not a finding) |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` (262 Markdown files, 1203 local links) |
| `git diff feat/h1-api-persistence...HEAD --stat` | 14 files, all under `scripts/clef/`, `docs/work/clef/`, plus the permitted `tasks.json`/`PROGRESS.md` state change and this packet |
| `git show --stat c74a73d` | the orchestrator commit touched `measurements.json`, `timing.json`, this packet and one line of `smoke.sh`; **`response.json` is unchanged**, so the container reproduced the native run's answer byte for byte (same request digest `d8fa1805…`) |
| `grep -rn HttpSystemOne src tests` | no hits: the port adapter (CORE-3) does not exist yet, so no `model` → `model_version` mapping exists anywhere |
| Scratchpad reproduction of `live()`/`cleanup`/`trap EXIT` with `docker` stubbed (bash 5.3.9) | success path: `name: unbound variable`, rc 1, no `docker rm`; `exit 1` inside `live()`: cleanup runs, container removed; `--keep` on the success path: same unbound error |

### Findings

| Severity | Location | What | Why it matters |
|---|---|---|---|
| important | `scripts/clef/smoke.sh:80-87` (trap) | The `${keep:-0}` patch moves the fault, it does not remove it. `cleanup` is defined inside `live()`, `trap cleanup EXIT` fires after `live()` returns on the success path, by which time the `local` variables are gone; under `set -u` the trap now dies on `"$name"` (lines 82 and 84) instead of `keep`. Reproduced in the scratchpad: on the success path (the one that produced the committed response) the script prints OK, then aborts with `name: unbound variable`, exits 1 and leaves the container running; `--keep` is also ignored there because `keep` falls back to 0. Only the failure path (`exit 1` inside `live()`, lines 90-94) cleans up, because the trap fires while the locals are still in scope. The patch was committed untested: the orchestrator's run was at `9ec21d0`, before the change. | A successful `--live` leaves a container holding a 9.66 GB mmapped model running on the owner's host and returns non-zero after success. Correction: declare `name` and `keep` at script level before calling `live`, or bind the values into the trap (`trap "cleanup '$name' '$keep'" EXIT` with `cleanup` reading `$1`/`$2`), and re-run `--live --no-build` once to show the container is gone on the success path. |
| important | `docs/work/clef/notes.md:10-26, 48-65, 102-114` | `notes.md` is a named task output ("measured memory and latency") and now contradicts its cited source. Its Measurements table says "every number below is read from measurements.json" and lists `llama_server_native`, 13.7074 s, peak RSS 10,078,996 KiB, `server.load_seconds` 2.008 s; `c74a73d` rewrote `measurements.json`/`timing.json` to the container run (`runtime: docker`, 46.7446 s, 1.761 GiB, no RSS or load time) without touching `notes.md`. "Recorded stop: the container path did not run" and "Next action: run `--live`" are superseded by the orchestrator run recorded above. | Checklist items 5 and 7: the record must match what the files say. Correction: add a dated container-run section to `notes.md` with the `docker` numbers, attribute the native numbers to commit `9ec21d0` (where that `measurements.json` is still in history), mark the recorded stop as superseded, and state why the container is 3.4x slower on the same host (the image builds with `GGML_NATIVE=OFF`, the native build did not; this is the likely cause and should be recorded as such, not as fact, until measured). |
| minor | `scripts/clef/smoke_check.py:167-195, 859, 870` | "Contract-valid" means: the four frozen rejection rules (missing question, unknown option, value outside [0, 1], over 64 KiB) pass. It does **not** mean the envelope matches the frozen shape: llama.cpp returns `{"model","answers","usage"}`, the port says `{"answers","model_version"}`, and the validator was deliberately widened to accept either identity field (it prints the mismatch note, which is good). No mapping exists in the codebase (CORE-3 pending). Per-answer extras `type` and `confidence` are silently ignored and never reported. | The `[ok] saved response conforms to the frozen response contract` label and the final `OK … contract-valid` line overstate. Correction: rename the label to "saved response passes the four frozen rejection rules" and append the envelope note to the OK line; report ignored per-answer keys the same way `extra response keys` are reported. Disposition for the shape gap itself: CORE-3 or a new intent, as the packet already says; not this task's defect. |
| minor | `scripts/clef/Dockerfile:19-21, 25, 35, 56` | `FROM ubuntu:24.04` is tag-pinned, not digest-pinned; `git clone --branch v0.6.0` is a mutable tag (the native build identified commit `7534465`, so a SHA pin is available); apt packages are unpinned; `build_native.py` fetches the tag tarball without a checksum. | Fine for a local smoke; for CLEF-2 (Cloud Run) the image is not reproducible by construction. Record the resolved digest of `ubuntu:24.04` and the llama.cpp commit in `measurements.json` or the Dockerfile comment, and pin the clone by SHA. Non-root user (uid 10001), read-only mount (`:ro` in `smoke.sh`, documented in the Dockerfile header; `VOLUME` cannot enforce it), and absence of any credential-shaped `ENV`/`ARG` are confirmed. |
| minor | `scripts/clef/docker-entrypoint.sh:12-13` vs `smoke_check.py:745-753` | The entrypoint counts every `*.gguf` under `/models`; `single_model_file` excludes `mmproj*`. Harmless today (fetch pulls one file) but a projector file beside the weights would make the container refuse to start while the native path runs. | Align the two filters. |
| minor | `scripts/clef/docker-entrypoint.sh:41-52`, Dockerfile `LLAMA_CURL=ON` | `LLAMA_ARGS` is passed unquoted by design and the binary has curl support, so any flag including a remote model fetch (`-hf`) can be injected from the host environment. | Acceptable for a local image; note it for CLEF-2 so the deployed container does not take `LLAMA_ARGS` from an untrusted source. |
| minor | packet, `notes.md` | No start time or elapsed time is recorded, so the 4 h timebox cannot be verified from evidence (weights `fetched_at_utc` 2026-10-11T17:22:51Z = 01:22 +0800, first commit 01:29 +0800; the fetch alone took ~20 min plus a stall). What was cut is clear and recorded: in-seat container build/run (done later by the orchestrator), bundle-sized latency, GPU numbers, the CORE-3 mapping. | Record the timebox start and end in the packet, even approximately, so "timebox respected" is a checked fact. |
| minor | `docs/work/clef/smoke/response.json` | The response file carries no synthetic label of its own; the label lives in `request.json` (`state_kind`, `disclaimer`), `measurements.json` (`execution_mode`) and `notes.md`. | Acceptable as is; the surrounding files make the status unambiguous. No change required. |

### Acceptance items

| Item | Verdict | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | **Met, with the qualification in the minor finding on "contract-valid"**: a real Clef-flash Q8_0 answer was produced twice (native 13.7 s at `9ec21d0`, container 46.7 s at `c74a73d`), byte-identical, passing the four frozen rejection rules; envelope shape differs from the frozen port and is disclosed | `response.json`, `timing.json`, `measurements.json`, verify command output above |
| Weights not committed | **Met** | `[ok] weights not committed to the repository`; `git ls-files` has no weight suffix; weights in ignored `.local/clef/` |
| Dockerfile for llama.cpp >= 0.6.0 serving the Q8_0 GGUF (output) | Met; built and run once by the orchestrator (image `sha256:b62457d5…`), healthcheck went healthy | packet "Orchestrator run" section |
| Smoke request and response saved (output) | Met | `docs/work/clef/smoke/` |
| notes.md with measured memory and latency (output) | **Not met at this commit**: the file describes measurements that are no longer in the files it cites | important finding 2 |

Checklist: 1 yes; 2 yes (scope OK); 3 yes (no frozen file touched, no test weakened); 4 yes beyond the packet (network and docker only behind `--fetch`/`--live`, disclosed); 5 partly (mode labels in JSON are truthful; `notes.md` is stale); 6 yes (synthetic state labelled, GPU numbers kept UNKNOWN); 7 partly (interpreter, commands and results recorded; timebox not recorded); 8 yes.

**Verdict: rework.** Two important findings: the `cleanup` trap still aborts on the success path and leaves the container running, and `notes.md` no longer matches the measurements it cites; both are small, same-branch fixes, after which an accept is expected.

## Rework (executor seat, DeepSeek V4.1 Flash, `task/CLEF-1`, 2026-10-12)

Trigger: the interim review above (commit `06322fd`), two important and five minor findings. All
fixes stay inside the task's allowed paths; no frozen contract, acceptance text or test was
changed, and nothing was written in `docs/work/reviews/` other than this append.

| Finding | Disposition |
|---|---|
| important 1 — `smoke.sh` cleanup trap dies after a successful run and leaves the container | **Fixed.** `cleanup()` moved to script level and reads only `CONTAINER_NAME` / `CONTAINER_KEEP`, published before `docker run` (trap armed before the container exists, so a failed `docker run` is cleaned too); the decision is delegated to a new `smoke_check.py cleanup` subcommand. Two guards in the offline check: a static one that fails on the old shape (trap over `live()`'s locals) and a stubbed-docker one that requires removal on the success path and no `docker` call at all under `--keep`. The trap line itself was **not** executed: this seat cannot invoke `bash` (see Limits); the live re-run is the first next action. |
| important 2 — `notes.md` cites numbers the committed `measurements.json` no longer holds | **Fixed.** Measurements are split into the committed container run (`runtime: docker`, 46.7446 s, 1.761 GiB / 9.01 %, image `sha256:b62457d5…`) and the native run attributed to commit `9ec21d0`; the recorded stop is marked superseded; the 3.4x slowdown is stated as an unmeasured hypothesis (`GGML_NATIVE=OFF` and the Docker Desktop VM), not as fact. A new offline check fails when `notes.md` does not carry the runtime and latency of the committed `measurements.json`, so this class of staleness cannot ship silently again. |
| minor — "contract-valid" overstates | Fixed. The label is now "saved response passes the four frozen rejection rules" and the closing `OK` line carries the envelope note; per-answer keys the port ignores (`type`, `confidence`) are printed next to the envelope's `usage`, with a negative test that the stub's exact frozen shape still reports none. The CORE-3 mapping decision stays where the packet left it. |
| minor — mutable tag, unpinned base, unpinned apt | Addressed as far as this seat allows: the `git clone` of a mutable tag is replaced by the release **source archive pinned by its sha256** (`ARG LLAMA_CPP_SHA256`, checked with `sha256sum -c`), the same digest `build_native.py` now verifies on every run. The `ubuntu:24.04` **digest could not be read** (no docker daemon, and Docker Hub is not a dependency the packet names), so it is recorded as a CLEF-2 action in the Dockerfile comment and in notes.md finding 8 rather than guessed. |
| minor — entrypoint counts `mmproj*.gguf`, harness excludes it | Fixed: `find … ! -name 'mmproj*'`, with a new offline check that runs the entrypoint's own filter against a temporary weights+projector directory and requires agreement with `single_model_file()`. It failed before the change and passes after. |
| minor — `LLAMA_ARGS` can inject a remote fetch (`-hf`) | Recorded, not changed: entrypoint comment plus notes.md finding 7, flagged for CLEF-2. The behaviour is what the local smoke needs. |
| minor — timebox start/end not recorded | Recorded below, from commit and file timestamps. |
| minor — `response.json` has no synthetic label of its own | No change, as the review concluded. |

### A wrong pin caught by running it, not reading it

The first attempt at pinning added `ARG LLAMA_CPP_COMMIT=7534465`, read from the
`llama-server --version` banner of the first native build. Re-running `build_native.py` to test
the new digest check printed `version: 0.6.0-dev (build 161, commit 06322fd)`: `06322fd` is
**this repository's** HEAD. In the native build the generated `build-info.cpp` takes the commit
from the enclosing git repository and the build number from its commit count (the extracted
release archive has no `.git`); `7534465` was a Grid Nowcast commit as well, not a llama.cpp one.
That pin would have failed the image build. The Dockerfile pins the source archive by digest
instead, and the trap is documented as notes.md finding 9 for the other lanes.

### Commands run (this worktree, `/usr/bin/python3` 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/clef/smoke_check.py check` (the body of the verify command `bash scripts/clef/smoke.sh`; see Limits) | Ten `[ok]`, then `OK: offline checks pass; the saved live response passes the four frozen rejection rules (response envelope: model identity in 'model' ('clef-flash'))`; notes list `q2_event_f0: answer keys ignored by the port: ['confidence', 'type']`, `q7_sufficiency_f0: … ['type']`, `measurements: mode live_inference, runtime docker, memory 1.761GiB / 19.53GiB, latency 46.7446 s` |
| `/usr/bin/python3 scripts/clef/build_native.py --jobs 8` | `tarball: sha256 09b36dba235fcac180efff18514da7038e65d8e5b9e4aefa59238468abfdec12 (matches the recorded digest for v0.6.0)`; incremental re-link of `llama-server` (17,872 bytes) |
| scratchpad negative tests of the three new guards (`/usr/bin/python3 -I /tmp/clef_guard_test.py`) | old trap shape → `smoke.sh has no cleanup() at script level…`; top-level trap reading a local → `cleanup() reads $name, which is not script-level state`; stale notes → `notes.md does not carry the recorded latency 46.7446 s from measurements.json` and `… does not carry the recorded runtime 'docker' …` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests in 2.087s` … `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` (262 Markdown files, 1208 local links, 8 skills) |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |
| `git status --porcelain` before the rework commit | only the allowed paths: `scripts/clef/`, `docs/work/clef/`, `docs/work/tasks.json`, `docs/work/PROGRESS.md`, `docs/work/reviews/CLEF-1.md` |

### Acceptance

| Item | Verdict | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | **Met**, and now described accurately: the container answered `POST /v1/systemone` HTTP 200 in 46.7446 s at `c74a73d` (image `sha256:b62457d5…`), the native server in 13.7074 s at `9ec21d0`, both 364 bytes for request digest `sha256:d8fa1805…`; `response.json` is contract-valid under the four frozen rejection rules and its envelope gap is reported, not glossed | verify output above; `docs/work/clef/smoke/*.json`; notes.md |
| Weights not committed | **Met** | `[ok] weights not committed to the repository`; weights in ignored `.local/clef/` |
| Output: Dockerfile for llama.cpp >= 0.6.0 serving the Q8_0 GGUF | Met; the source pin changed from tag-only to tag + archive digest. **The reworked Dockerfile has not been built**: this seat has no daemon, and the digest pin must be proven by CLEF-2's first build | Dockerfile; notes.md finding 8 |
| Output: smoke request and response saved | Met, unchanged | `docs/work/clef/smoke/request.json`, `response.json` |
| Output: notes.md with measured memory and latency | **Met at this commit** (the review's only non-met item): container and native numbers both recorded and attributed, and the offline check now enforces notes/measurement consistency | notes.md; `[ok] notes.md carries measurements or the recorded stop reason` |

### Limits, and stop conditions

- `bash scripts/clef/smoke.sh` (the verify command) and any `docker` call return "This command
  requires approval" in this seat and do not execute. The command above is the same Python body
  `smoke.sh` execs for every mode except `--live`, so the offline verify is covered; the `--live`
  path is not, and no result is claimed for it here.
- The reworked `cleanup` trap was therefore not executed end to end. What it delegates to is
  executed in-seat with a stubbed docker, and the trap's shape is guarded statically.
- No stop condition was hit. No frozen contract, acceptance text or test was changed; no file
  outside the allowed paths was touched; commits stay on `task/CLEF-1`. State stays `in_progress`
  — this is a self-review, and only an independent reviewer sets `done`.

### Timebox

First pass: 2026-10-12 00:54 +0800 (worktree created) to 01:29:28 +0800 (first commit) — about
35 minutes of recorded wall clock, of which the 9.66 GB weight fetch took ~20 minutes
(`fetched_at_utc` 2026-10-11T17:22:51Z = 01:22:51 +0800). The rest of the 4 h estimate was not
spent because the seat's blocked `bash`/`docker` paths pushed the container steps to the
orchestrator seat, not because the work was cut; the unfinished items are listed in notes.md.
Rework round: 2026-10-12 11:23 to 11:31 +0800 (≈8 min of wall clock; the packet was written as
the round ran).

### Next action

1. On a host that can run bash and has a Docker daemon: `bash scripts/clef/smoke.sh --live
   --no-build --no-fetch --port 18090` must print `container clef-smoke-<pid> removed` and exit 0
   with no container left in `docker ps -a`; the same with `--keep` must leave it running and say
   so. That is the one piece of this rework this seat could not execute.
2. Then re-run `bash scripts/clef/smoke.sh` on that host (offline, unchanged) and, on the first
   Docker build of the reworked Dockerfile, confirm the archive digest check passes.
3. CLEF-2: record the `ubuntu:24.04` digest and pin `FROM` by digest; measure the container
   slowdown; keep `LLAMA_ARGS` out of untrusted hands; CORE-3 owns the `model` → `model_version`
   mapping.
4. Independent review of this record is the gate for `done`.

## Orchestrator rerun of `smoke.sh --live` after the rework (local Docker Desktop host, 2026-10-12)

`bash scripts/clef/smoke.sh --live --no-build --no-fetch --port 18090` from this worktree at `8920d1c`, image
`nowcast-clef:local` reused. Exit 0; `POST /v1/systemone` HTTP 200 in **23.7974 s** (page cache warm from the earlier
run; the first run measured 46.7446 s cold), container memory 3.77 GiB / 19.53 GiB; the script printed
`container clef-smoke-442693 removed` and `docker ps -a` shows no `clef-smoke-*` container afterwards, so the success-path
cleanup the interim review asked for now works. `measurements.json` and `timing.json` were rewritten by the run and are
committed with this note; the earlier stopped container from the first run was removed by hand.

## Interim re-review of the rework (orchestrator seat, Fable, commit 5de71c7, 2026-10-12)

Independent of the author of the rework (executor seat wrote `8920d1c`; the orchestrator seat ran the live rerun `5de71c7`).
Interim because the designated reviewer (codex) is still out of credits: **this section is a review-first list for the owner and
does not set the task `done`. The designated review supersedes it.** Reviewed in the worktree on `task/CLEF-1` at `5de71c7`;
no docker, no network, no download; the only file edited is this record (this append). `git status --short` was clean before
and after every command below.

### Commands run

| Command | Result |
|---|---|
| `bash scripts/clef/smoke.sh` (the verify command, offline) | **exit 1.** Nine `[ok]`, one `[FAIL] notes.md carries measurements or the recorded stop reason` / `notes.md does not carry the recorded latency 23.7974 s from measurements.json`; notes line `measurements: mode live_inference, runtime docker, memory 3.77GiB / 19.53GiB, latency 23.7974 s`; `FAILED: 1 check(s) failed` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests in 2.328s` `OK` |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` (262 Markdown files, 1209 local links, 8 skills) |
| `git diff feat/h1-api-persistence...HEAD --stat -- docs/work/probe-bundle src tests docs/research docs/engineering` | empty: no frozen contract, test or research file changed on the branch |
| `git show 8920d1c --stat`, `git show 8920d1c`, `git show 5de71c7` | rework: 9 files, all in `scripts/clef/`, `docs/work/clef/`, `PROGRESS.md` and this record; rerun: `measurements.json` (46.7446 s → 23.7974 s, 1.761 GiB → 3.77 GiB), `timing.json`, this record |
| `git show 9ec21d0:docs/work/clef/smoke/measurements.json`, `git show c74a73d:...` | native numbers cited in notes.md (13.7074 s, RSS 9,602,604 KiB, VmHWM 10,078,996 KiB, `load_seconds` 2.008, runtime `llama_server_native`) are exactly what `9ec21d0` holds; the cold container numbers (46.7446 s, 1.761 GiB / 9.01 %) are exactly what `c74a73d` holds |
| `sha256sum .local/clef/build/llama.cpp-v0.6.0.tar.gz` (cached archive, no download) | `09b36dba235fcac180efff18514da7038e65d8e5b9e4aefa59238468abfdec12`, equal to `ARG LLAMA_CPP_SHA256` in the Dockerfile and `TARBALL_SHA256["v0.6.0"]` in `build_native.py` |
| Scratchpad reproduction of `smoke.sh --live --no-build --no-fetch` (bash 5.3.9) with the whole `scripts/clef/` and `docs/work/clef/` tree copied under a scratch root, a `docker` PATH shim that logs every call and whose `run` starts a loopback stub server (`smoke_check._StubHandler` plus `/health`) on the published port and whose `rm` stops it | see the table below; the repository tree was not written to (the copy's `ROOT` is the scratch root) |

Scratchpad lifecycle results:

| Path | Exit | `docker` calls after `run` | Cleanup line printed | Server still listening after exit |
|---|---|---|---|---|
| success (`--port 18555`) | 0 | `logs`, `stats`, `inspect`, `exec`, **`rm -f clef-smoke-<pid>`** | `container clef-smoke-445788 removed` | no |
| success with `--keep` (`--port 18557`) | 0 | `logs`, `stats`, `inspect`, `exec`, **no `rm`** | `container clef-smoke-445839 left running (--keep)` | yes (stopped by hand) |
| failure inside `live()`: `/health` never ready (`--timeout 3`, no server) | 1 | `logs`, **`rm -f`** | `container clef-smoke-445669 removed` | no |
| failure of `docker run` itself (shim exits 125) | 125 | **`rm -f`** (trap armed before `run`) | `container clef-smoke-445884 removed` | no |
| port already bound before the run | 1 | none (`info` only) | none; correct, the trap is not yet armed and no container exists | n/a |

What the stub cannot show: a real `docker rm -f` on a container that never got created (the `docker run` failure path) returns 1;
`cleanup_container` prints that and still returns 0 under `|| true`, which is the intended behaviour but was not exercised against a
daemon. The orchestrator's real rerun at `8920d1c` (`container clef-smoke-442693 removed`, exit 0, `docker ps -a` empty) covers the
success path against a daemon; `--keep` and the failure paths against a daemon are not covered by any run.

### Findings

| Severity | Location | What | Why it matters |
|---|---|---|---|
| **blocking** | `docs/work/clef/notes.md:13-32, 44, 76` vs `docs/work/clef/smoke/measurements.json`, `timing.json` at `5de71c7` | The verify command fails at the reviewed commit. The rework (`8920d1c`) rewrote notes.md around the cold container run (46.7446 s, 1.761 GiB / 9.01 %, "the committed measurements.json and timing.json are the **container** run" at `c74a73d`) and added `check_notes`, which requires notes.md to carry the committed latency and runtime. The orchestrator's rerun commit `5de71c7` then rewrote `measurements.json` and `timing.json` to the warm run (23.7974 s, 3.77 GiB / 19.30 %, `generated_at_utc` 03:35:48Z) without touching notes.md and without re-running `bash scripts/clef/smoke.sh` (the rework's own Next action 2). The guard fired exactly as designed: `[FAIL] notes.md does not carry the recorded latency 23.7974 s`. notes.md line 15-17 is now literally false (the committed files are the `5de71c7` rerun, not the `c74a73d` run), and line 28/32 cite a memory figure the committed file no longer holds. Second occurrence of the same pattern (a measurement-rewriting commit without the notes), this time by the orchestrator seat; per the feedback-loop rule it belongs in FEEDBACK.md (orchestrator's action, not written here). | `verify` exits non-zero at HEAD, so acceptance cannot be read from the committed tree, and the named output "notes.md with measured memory and latency" again describes numbers that are not the committed ones. Correction (one pass, notes.md only, orchestrator seat as the author of `5de71c7`): add the warm rerun as the committed run (`5de71c7`, literal `23.7974` s and `docker`, 3.77 GiB / 19.30 %, image id unchanged `sha256:b62457d5…`, `--no-build`), move the cold numbers (46.7446 s, 1.761 GiB) to a row attributed to `c74a73d`, keep both with no causal claim for the memory difference (page cache attributed to the container cgroup is a hypothesis), and restate the "3.4x slower" paragraph: cold container 46.7 s vs native 13.7 s is cold-vs-warm; warm-vs-warm is 23.8 s vs 13.7 s, about 1.7x, with `GGML_NATIVE=OFF` and the Docker Desktop VM still the candidates. Then run `bash scripts/clef/smoke.sh` and paste its ten `[ok]` into the packet. |
| minor | `docs/work/clef/notes.md:140-142` (finding 9) | "Inside the container the check is different (`git clone` gives `/src/llama.cpp` its own repository)" describes the pre-rework Dockerfile. At `8920d1c` the image also extracts the release archive, so there is no `.git` in `/src/llama.cpp` either and the banner commit inside the container will be `unknown` (or whatever CMake falls back to), not the tag's commit. | Stale sentence; CLEF-2 would look for a commit the image cannot report. Correction: say the container build carries no `.git` either and that the tag's commit, if wanted, must be resolved outside the image (`git ls-remote --tags` or the GitHub release page) and written into a comment or label. |
| minor | `docs/work/clef/smoke/measurements.json` `image_id` vs `scripts/clef/Dockerfile` at `8920d1c` | Both committed container runs reused image `sha256:b62457d5…`, built at `9ec21d0` from the pre-rework Dockerfile (`git clone --branch v0.6.0`). The reworked Dockerfile (archive download, `sha256sum -c`, duplicated `ARG` in the runtime stage) has never been built; the rerun used `--no-build`. The executor disclosed this ("The reworked Dockerfile has not been built"). | The committed measurement does not correspond to the committed Dockerfile. Acceptable for this task as long as the record says so (it does); the first real `docker build` is CLEF-2's proof step and should record the image id it produces. The archive digest itself is verified offline here (see Commands). |
| minor | `scripts/clef/smoke.sh:113` | The `docker exec … find … -name "*.gguf" | head -1` that fills `model_file` for `measurements.json` does not exclude `mmproj*`, while the entrypoint and `single_model_file()` now do. | With a projector file beside the weights the recorded `model.file` could name the projector while the server serves the weights. Cosmetic today (one file in the volume); align the filter when the line is next touched. |
| minor | packet "Orchestrator rerun" section | Memory doubled between the cold and warm run (1.761 GiB → 3.77 GiB) and the section does not say so or offer a reason; `docker stats` counts page cache attributed to the container cgroup, which a warm run would plausibly show. | Record as an observation with a hypothesis, not as a measured cause; folds into the blocking correction. |

### Disposition of the first-review items

| First-review item | Disposition at `5de71c7` |
|---|---|
| important 1: `cleanup` trap aborted on the success path, left the container running | **Closed.** `cleanup()` is at script level, reads `CONTAINER_NAME`/`CONTAINER_KEEP` only (both published before `docker run`, trap armed before the container exists), and delegates to `smoke_check.py cleanup`, which always returns 0. Shown by the scratchpad reproduction on all five paths above and by the orchestrator's real success-path run at `8920d1c`. The two offline guards (`check_smoke_sh_trap`, `check_cleanup_dispatch`) pass. |
| important 2: notes.md cited numbers measurements.json no longer held | **Closed at `8920d1c`, reopened at `5de71c7`.** The rework made notes.md consistent with the `c74a73d` files and attributed native vs container numbers to commits correctly (verified against `git show 9ec21d0:…` and `c74a73d:…`). The orchestrator's rerun then replaced the committed measurements again without the notes, and the new guard fails the verify command. Blocking finding above. |
| minor: "contract-valid" overstated | **Closed.** Label is `saved response passes the four frozen rejection rules`; the OK line carries the envelope note; per-answer keys ignored by the port (`type`, `confidence`) are printed; `stub_round_trip` fails if the stub's exact frozen shape produces any note. The `model`/`model_version` gap stays a CORE-3 finding, correctly. |
| minor: pins (base image, tag, apt, tarball) | **Improved and recorded.** Source is pinned by the release-archive sha256 in the image build and in `build_native.py` (digest verified offline here against the cached archive); `ubuntu:24.04` digest and apt pins are recorded as CLEF-2 actions in the Dockerfile and notes.md finding 8, not guessed. The wrong-commit pin caught by rebuilding (finding 9) is a genuine lesson, with the stale `git clone` sentence noted above. |
| minor: entrypoint vs `single_model_file` filter | **Closed.** `find … ! -name 'mmproj*'`; `check_model_selection` runs the entrypoint's own filter against a temp weights+projector directory and passes. One residual filter on `smoke.sh:113` noted above. |
| minor: `LLAMA_ARGS` / `LLAMA_CURL` | **Recorded, not changed**, as the first review asked: entrypoint comment and notes.md finding 7 flag it for CLEF-2. |
| minor: timebox evidence | **Recorded.** First pass 00:54–01:29:28 +0800 (tarball on disk at 00:55 and `fetched_at_utc` 17:22:51Z = 01:22:51 +0800 are consistent with it), rework 11:23–11:31 +0800; what was cut is listed. |
| minor: response.json carries no label of its own | No change required, as agreed. |

### Acceptance items

| Item | Verdict | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | Met in substance: three live answers (native 13.7074 s at `9ec21d0`, container cold 46.7446 s at `c74a73d`, container warm 23.7974 s at `5de71c7`), same request digest `d8fa1805…`, same 364 bytes, passing the four frozen rejection rules with the envelope gap disclosed. **Not readable from the verify command at HEAD**, which exits 1 (blocking finding) | `response.json`, `timing.json`, verify output above |
| Weights not committed | **Met** | `[ok] weights not committed to the repository`; weights in ignored `.local/clef/` |
| Output: Dockerfile for llama.cpp >= 0.6.0 serving the Q8_0 GGUF | Met as a file and pinned by digest; the reworked Dockerfile is unbuilt (minor finding) | Dockerfile; cached archive digest |
| Output: smoke request and response saved | **Met**, unchanged since `9ec21d0` | `docs/work/clef/smoke/` |
| Output: notes.md with measured memory and latency | **Not met at this commit**: notes.md describes the `c74a73d` numbers while the committed measurements are the `5de71c7` rerun | blocking finding |

Checklist: 1 no (the verify command fails at HEAD); 2 yes (scope OK); 3 yes (frozen-path diff empty, no test weakened); 4 yes (network and docker only behind `--fetch`/`--live`, disclosed; the new `cleanup` subcommand calls `docker rm` only when invoked by the trap); 5 partly (JSON mode labels truthful; notes.md cites the wrong committed run); 6 yes (synthetic state labelled, GPU and slowdown cause kept unmeasured); 7 partly (interpreter, commands, timebox recorded; the rerun section omits the memory change and the verify re-run); 8 yes.

**Verdict: rework.** The trap fix is real and the rework closed every first-review item, but the orchestrator's rerun commit `5de71c7` rewrote the committed measurements without updating notes.md, so the verify command fails at HEAD; one notes.md pass (warm run as the committed run, cold and native runs attributed to `c74a73d` and `9ec21d0`, slowdown ratio restated) followed by a green `bash scripts/clef/smoke.sh` closes it.

## Designated review 1 (GPT Sol, independent, commit `5585b58`, 2026-10-13)

> Independent review of `5585b5803695` against `feat/h1-api-persistence`; inspected the requested diff and all eight branch commits. Working tree clean. No files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Saved request, response and receipts document local HTTP 200 inference: 23.7974 s, Q8_0 weights. Saved-response validation passes. Weight exclusion check passes. This demonstrates endpoint operation, not model quality or frozen-port integration. |
> | 2 | Changes within allowed paths | **Yes.** Requested scope command printed `OK: all changed files inside CLEF-1 allowed paths`. |
> | 3 | Frozen contracts, acceptance and tests preserved | **Yes.** Diff contains no frozen-contract or existing test changes; acceptance text unchanged. |
> | 4 | Dependencies and effects within packet | **Yes.** llama.cpp build, model download and local inference support the named container/smoke task; no cloud deployment or credential addition appears. |
> | 5 | Truthful mode labels | **Yes.** Receipts distinguish `live_inference`/`docker`; stub identifies itself separately. Notes disclose that the recorded image predates the Dockerfile rework. |
> | 6 | Unknowns preserved | **No.** Model metadata can attribute the cached weight digest to a different selected file; see finding below. GPU performance and slowdown causes otherwise remain explicitly unmeasured. |
> | 7 | Complete packet and handoff | **Yes.** Packet records Python 3.14.4, commands, results, timebox, limitations and next actions. Some handoff prose remains stale. |
> | 8 | Direction and invariants preserved | **No.** The model metadata attribution defect violates the lineage invariant. No product-direction conflict identified. |
> 
> Verification actually run:
> 
> - `bash scripts/clef/smoke.sh`: **exit 1**, sandbox denied socket creation in the loopback stub (`PermissionError`). This is an execution limitation, not evidence of a functional regression.
> - Requested scope command: **OK**.
> - `plan.py check`: **OK**, 42 tasks, 7 gates.
> - `repo.py check`: **PASS**.
> - Full offline suite: **261 tests passed**.
> - Separately executed saved-response, notes, trap and cleanup checks: passed. No live model call or Docker build performed during review.
> 
> Findings, all unresolved:
> 
> | Severity | Path:line | Failure mechanism | Evidence | Correction |
> |---|---|---|---|---|
> | important | `scripts/clef/smoke_check.py:855` | Metadata attaches cached weight provenance without verifying that it describes the model served. | `model_metadata()` copies `.local/clef/weights.json` digest, size and URL regardless of `model_file`; `--models-dir` permits another directory. At `smoke.sh:113`, discovery also includes projectors despite the entrypoint excluding them. | Identify the actual selected model consistently and verify its bytes against the provenance record; otherwise record identity/digest as unknown. |
> | minor | `docs/work/clef/notes.md:153` | Documentation describes a build mechanism that no longer exists. | Says container uses `git clone`; current Dockerfile extracts a pinned archive. | Correct the build description. |
> | minor | `docs/work/clef/notes.md:170` | Handoff requests cleanup confirmation already recorded as completed. | Warm-run receipt records successful removal; next action still describes the trap as unexecuted. | Update remaining actions to distinguish completed cleanup verification from the unbuilt revised Dockerfile. |
> 
> **Verdict: rework.** The saved local response and weight exclusion are demonstrated, but model provenance can be falsely attributed and must be corrected before acceptance.
**Verdict: rework.** Record weight provenance only when the served model file's bytes match it; otherwise record identity and digest as unknown; exclude projectors from discovery consistently.

## Rework (executor seat, DeepSeek V4.1 Flash, `task/CLEF-1`, 2026-10-13)

Trigger: the designated review above, commit `4af942c`, verdict **rework** — one important finding
(model provenance can be falsely attributed) and two minor ones (a `git clone` the Dockerfile no
longer does; a handoff asking for a cleanup confirmation already recorded as done). All fixes are
inside the task's allowed paths; no frozen contract, acceptance text or test was changed, and
nothing under `docs/work/reviews/` was edited except this append. State stays `in_progress`: this
is a self-review, and only an independent reviewer sets `done`.

| Finding | Disposition |
|---|---|
| **important** — `scripts/clef/smoke_check.py:855` copied `.local/clef/weights.json` (`sha256`, `size_bytes`, `url`, `fetched_at_utc`) onto whatever file the container listing named, `--models-dir` could point elsewhere, and `smoke.sh:113` discovery counted the projector | **Fixed.** The digest is now recorded only for a verified byte match, and the listing and the projector exclusion live in one place, in the harness. Details below. |
| minor — `notes.md:153` describes `git clone` giving `/src/llama.cpp` its own repository | Fixed: the paragraph now says the image unpacks the same release archive, so the container build carries no `.git` either, and a commit pin must be resolved outside the image (`git ls-remote` or the release page) and written into a comment or label. |
| minor — `notes.md:170` asks for a cleanup confirmation that is already recorded | Fixed: the run is marked done with the receipt (`container clef-smoke-442693 removed`, exit 0, no `clef-smoke-*` left), and the items that are genuinely not covered (`--keep` and the `docker run` failure path against a daemon, the unbuilt reworked Dockerfile) are named as what remains. |
| minor — `notes.md:170` third item and the 2026-10-13 checklist "handoff prose remains stale" | Same pass: the paragraph under the superseded stop no longer claims the reworked cleanup still needs a host, and the Next action is four numbered items instead of a request already satisfied. |

### What changed

- `smoke_check.py`
  - `is_model_file()` is the single non-mmproj predicate; `single_model_file()` uses it.
  - `container_model_listing(name)` lists the running container's model directory itself, with
    `docker exec … sh -c` (`MODEL_LISTING_SH`). The fragment exits non-zero only when the directory
    is unreadable; an empty directory is an empty listing, not a failure.
  - `pick_model_file(names)` chooses the served file, or `""` when zero or more than one non-mmproj
    `.gguf` is present.
  - `model_metadata(model_file, models_dir, record_path)` attaches the record's `sha256`,
    `size_bytes`, `url` and `fetched_at_utc` **only** when the served basename is the fetched file,
    that file is readable on the host, and its bytes hash to the recorded sha256 — then it writes
    `identity: verified` and the check performed. Every other case (projector named as the model,
    another directory, same size but different bytes, missing record, nothing identifiable) writes
    `identity`, `sha256` and `size_bytes` as `unknown` with a `provenance` reason and no URL.
  - `record-live` takes `--container` and `--models-dir` instead of a pre-picked `--model-file`, and
    appends a listing failure to the provenance reason.
  - Two new offline checks: `check_model_provenance` (placeholder bytes: a matching file verified;
    projector, other directory, same-size-different-bytes, missing record and unidentified file all
    `unknown`, URL-free) and `check_container_model_listing` (runs the listing fragment through a
    real `sh` via a `docker` stub: weights + projector picks the weights, an empty directory lists
    nothing and does not error, a failing `docker exec` is reported; plus a static guard that
    `smoke.sh` does not filter model files in shell). The offline check now prints twelve `[ok]`.
- `smoke.sh` no longer runs a shell `.gguf` filter; it hands `--container "$name"` to `record-live`.
- `README.md`: the harness's provenance verification is named in the file table and in "What is
  live and what is not".
- `notes.md`: a new subsection "Model provenance is verified, not assumed" (with the disclosure
  that the committed `measurements.json` was written by the pre-review code and has no `identity`
  field), the two stale handoff passages, and the intro line for this second rework.
- `tasks.json`: a `note` on CLEF-1 recording the self-review and the fact that the state stays
  `in_progress` (the `state` field is unchanged, no acceptance text and no other task touched);
  `PROGRESS.md`: one log row for this rework.

Two things are worth recording as they happened rather than as they were planned. First, the new
listing check failed on my own first version of the fragment: an empty model directory made the
`for` loop's last command fail, so `docker exec` returned 1 and the harness reported a listing
failure instead of an empty listing. The fragment now ends with `exit 0` (a failing `cd` still
exits 1). Second, the two guards were run against the reviewed code as negative controls: the
reviewed `model_metadata` produces 10 guard errors (including the projector receiving the weights
digest, size and URL) and the reviewed `smoke.sh` produces the listing guard's error. Nothing was
executed against a model in this rework.

### Commands run (this worktree, `/usr/bin/python3` 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/clef/smoke_check.py check` (the body of the verify command `bash scripts/clef/smoke.sh`; see Limits) | twelve `[ok]`, then `OK: offline checks pass; the saved live response passes the four frozen rejection rules (response envelope: model identity in 'model' ('clef-flash'))` |
| `bash scripts/clef/smoke.sh` (the verify command itself) and `sh -c 'echo …'` | neither executes in this seat: `This command requires approval`. Recorded as a seat limit, not claimed as a pass |
| `/usr/bin/python3 -I /tmp/clef1_rework_test.py` (scratch driver outside the repo: scratch tree under `/tmp`, stub `docker` on `PATH`) | four `record-live` cases, exit 0 each: weights + projector → `identity: verified` with the record's digest and URL; projector only → `unknown`, no URL; container lists the weights but the host directory holds other bytes → `unknown` with the byte mismatch in `provenance`; `docker exec` exit 3 → `unknown` with the exec error in `provenance`. Negative controls: 10 guard errors on the reviewed `model_metadata`, 1 on the reviewed `smoke.sh` |
| `/usr/bin/python3 -I -c "… model_metadata('Clef-Flash-Q8_0.gguf', .local/clef/models)"` (read-only, no model call) | `identity: verified`, `sha256:87a232aa…`, `size_bytes` 9,657,260,192, 11.9 s of hashing; the record describes the file the container mounts |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 261 tests` … `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 42 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | `PASS` |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |
| `git status --porcelain` before the commit | `M docs/work/PROGRESS.md`, `M docs/work/clef/notes.md`, `M docs/work/reviews/CLEF-1.md`, `M docs/work/tasks.json`, `M scripts/clef/README.md`, `M scripts/clef/smoke.sh`, `M scripts/clef/smoke_check.py` — all allowed paths, no weight file |

### Acceptance

| Item | Verdict | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | **Met**, unchanged by this rework: the response and receipts at `c74a73d`/`5de71c7` are untouched; the verify body passes at HEAD | `docs/work/clef/smoke/response.json`, `timing.json`, `measurements.json`; verify output above |
| Weights not committed | **Met** | `[ok] weights not committed to the repository`; weights in ignored `.local/clef/` |
| Output: Dockerfile for llama.cpp >= 0.6.0 serving the Q8_0 GGUF | Met as a file, digest-pinned; still **not built** (no daemon in this seat) — an unresolved item, CLEF-2's proof step | `scripts/clef/Dockerfile`; notes.md |
| Output: smoke request and response saved | Met, unchanged | `docs/work/clef/smoke/request.json`, `response.json` |
| Output: notes.md with measured memory and latency | Met; the numbers still match the committed files, and the model-provenance rule is now documented there | notes.md; `[ok] notes.md carries measurements or the recorded stop reason` |
| Designated review's correction: provenance only when the bytes match, otherwise identity/digest unknown, projector excluded consistently | **Met, with one disclosed residue**: the code and the offline checks implement it and the record now says so. The committed `measurements.json` keeps the pre-rework `model` block (no `identity` field) because rewriting it would mean editing a receipt that no run produced in that shape; the next live run rewrites it. Disclosed in notes.md and here. | `smoke_check.py`; verify output; notes.md |

### Limits and stop conditions

- The seat cannot invoke `bash` or `sh`: `bash scripts/clef/smoke.sh` returns "This command
  requires approval" without running (verified again this round). The verify command's body is the
  Python check above; the `--live` shell path is not executed here and no result is claimed for it.
  To keep that path from being untested code, the one shell fragment this rework adds was moved
  into the harness and is executed by the offline check through a stubbed `docker`.
- No docker daemon, no network call, no model call, and no new dependency in this round.
- The committed container measurement and image predate the reworked Dockerfile; unchanged from
  the previous round's disclosure.
- No stop condition was hit: no frozen contract, acceptance text or test was changed; no file
  outside the allowed paths was touched; the only commit is on `task/CLEF-1`.

### Timebox

2026-10-13, session start 21:36 to 22:03 +0800 (≈27 minutes of wall clock; the start is the
`__pycache__` mtime the first command of this session wrote in this worktree, the end is `date`
before this packet was committed). Well inside the task's 4 h estimate; the first pass and the
first rework are timed in the earlier sections.

### Next action

1. On a host with a daemon and bash: `bash scripts/clef/smoke.sh --live --no-fetch --port 18090`.
   This is the first build of the archive-pinned Dockerfile and the first live run of the new
   `record-live` (it lists the container's model directory, hashes the served 9.66 GB file and
   should write `identity: verified`; ~12 s of hashing here). It also confirms the `sha256sum -c`
   source pin.
2. `bash scripts/clef/smoke.sh` on that host — the twelve offline checks.
3. CLEF-2: pin `FROM` by digest, measure the container slowdown, keep `LLAMA_ARGS` out of
   untrusted hands, resolve the llama.cpp tag commit outside the image.
4. Independent review of this record is the gate for `done`. Address every blocking/important row above; dispose of minors explicitly.

## Orchestrator finding before re-review (2026-10-13, orchestrator seat, not a designated review)

After rebasing onto `feat/h1-api-persistence`, the orchestrator ran
`bash scripts/clef/smoke.sh --live --no-fetch --port 18090` on Docker Engine 29.6.1: exit 0, health
ready after 14.0 s, `POST /v1/systemone` HTTP 200 in 20.105 s (364 bytes), memory 2.646 GiB / 19.53 GiB,
image `sha256:b7f955e3…`, model identity `verified` against `weights.json`. The run's measurement files
were not committed, for one important reason:

| Severity | Path | Mechanism | Evidence | Correction |
|---|---|---|---|---|
| important | `scripts/clef/smoke_check.py` (the code that writes `model.provenance`) | The provenance string embeds the absolute host path of the weights file, so a committed `docs/work/clef/smoke/measurements.json` would carry the operator's home directory and worktree layout into the repository and the public export (REL-1 blocks internal locations) | Live run wrote `"provenance": "sha256 of /home/<user>/projects/…/.local/wt/CLEF-1/.local/clef/models/Clef-Flash-Q8_0.gguf matches weights.json"` | Record only the file name (or a path relative to the models directory) in provenance; add a test that no absolute path or home directory reaches `measurements.json`. Keep the `notes.md` check: after the fix the orchestrator re-runs the live smoke and records the new measurements in `notes.md` before committing |

Do not edit `docs/work/clef/smoke/*.json` by hand; the orchestrator regenerates them with the live run.

## Rework (executor seat, DeepSeek V4.1 Flash, `task/CLEF-1`, 2026-10-13)

Trigger: the orchestrator finding above (commit `581ad1d`; not a designated review) — the recorded
model provenance embedded the served weights file's absolute host path, so the live run that
exposed it could not be committed. The designated review 1 findings were disposed at `26306e1`
and are unchanged by this round. All fixes are inside the task's allowed paths; no frozen
contract, acceptance text or test was changed, and nothing under `docs/work/reviews/` was edited
except this append. State stays `in_progress`: this is a self-review, and only an independent
reviewer sets `done`.

| Finding | Disposition |
|---|---|
| **important** — `scripts/clef/smoke_check.py`: `model.provenance` copied the weights file's absolute host path into `measurements.json`; committed, it would carry the operator's home directory and worktree layout into the repository and the public export (REL-1 blocks internal locations) | **Fixed.** The writer records the file name only: verified → `sha256 of Clef-Flash-Q8_0.gguf matches weights.json`; a byte mismatch, a file missing from the models directory and a missing record all name the file, never a directory or absolute path. |
| minor (same class, found while fixing it) — `local_run` recorded `server.command` and `server.binary` as absolute host paths | Fixed: `recorded_path()` records a path relative to the repository root (the file name when outside it) and `recorded_server_command()` applies it to the binary and model arguments. The executed command keeps absolute paths; only the receipt is relative. |
| the correction's control — "add a test that no absolute path or home directory reaches measurements.json" | Two guards. `check_model_provenance` now scans every metadata case it produces (the case list gained "a file missing from the models directory", which exercises the unreadable branch), and the new `check_measurement_paths` reads back the committed `measurements.json` and `timing.json` and fails on the home directory, the repository root or an absolute path (URLs and the frozen `/v1/...` route are not read as paths), and exercises the recorded native command. |
| also on this branch — `repo.py check` failed at HEAD before this round | The rebase onto `feat/h1-api-persistence` left two byte-identical copies of the 2026-10-12 "CLEF-1 implemented" log row in `docs/work/PROGRESS.md`, one of them carrying a `../clef/smoke/response.json` link that breaks from `docs/work/`. The broken duplicate was removed (one line); `repo.py check` went from `Broken local link: docs/work/PROGRESS.md: ../clef/smoke/response.json` to `PASS`. |

### Negative controls (scratch driver, `/tmp/clef1-rework3/driver.py`, outside the repo)

The driver imports this worktree's `smoke_check.py` and a scratch copy whose three provenance
strings are restored to the reviewed code (commit `581ad1d`), and checks both directions:

| Expectation | Result |
|---|---|
| the fixed writer's output is clean; `check_measurement_paths` passes on this worktree | ok |
| the pre-fix writer produces `sha256 of /tmp/…/models/Clef-Flash-Q8_0.gguf matches weights.json`; the scanner flags it | 1 scanner error; the guards report 4 errors |
| a scratch copy of the committed smoke directory whose `model` block is the pre-fix writer's output for the real models directory (read-only hashing of the cached 9.66 GB file: `identity: verified`) | the file guard flags it — `docs/work/clef/smoke/measurements.json: the home directory appears in 'sha256 of /home/…/Clef-Flash-Q8_0.gguf matches weights.json'` |
| the untouched committed copy scans clean; the recorded native command has no absolute part; the pre-fix recording (absolute binary and model) is flagged | ok |
| totals | 12/12 expectations hold |

The string in the third row is the reviewed `model_metadata` run against the real
`.local/clef/models` and `.local/clef/weights.json` — the same form the finding quotes — not a
string written by hand.

### Commands run (this worktree, `/usr/bin/python3` 3.14.4)

| Command | Result |
|---|---|
| `/usr/bin/python3 scripts/clef/smoke_check.py check` (the body of the verify command `bash scripts/clef/smoke.sh`; see Limits) | thirteen `[ok]`, including `no host path or home directory reaches the measurement files`, then `OK: offline checks pass; the saved live response passes the four frozen rejection rules (response envelope: model identity in 'model' ('clef-flash'))` |
| `bash scripts/clef/smoke.sh` (the verify command itself) | does not execute in this seat: `This command requires approval`. Recorded as a seat limit, not claimed as a pass |
| `/usr/bin/python3 -I /tmp/clef1-rework3/driver.py` | 12/12 expectations hold; `OK: 12 expectations hold; the reviewed writer produces 1 scanner error(s) and 4 guard error(s)` |
| `/usr/bin/python3 -m unittest discover -s tests` | `Ran 320 tests in 5.787s` … `OK` |
| `/usr/bin/python3 scripts/plan.py check` | `OK: 45 tasks, 7 gates` |
| `/usr/bin/python3 scripts/repo.py check` | first run at HEAD: `Broken local link: docs/work/PROGRESS.md: ../clef/smoke/response.json` (exit 1); final run, after the row repair and this append: `PASS` (278 Markdown files, 1325 local links, 8 skills) |
| `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` | `OK: all changed files inside CLEF-1 allowed paths` |
| `git status --porcelain` before the commit | `M docs/work/PROGRESS.md`, `M docs/work/clef/notes.md`, `M docs/work/tasks.json`, `M scripts/clef/README.md`, `M scripts/clef/smoke_check.py` — all allowed paths; no file under `docs/work/clef/smoke/`, no weight file |

### Acceptance

| Item | Verdict | Evidence |
|---|---|---|
| One valid System One response locally, or a recorded stop at the timebox | **Met**, unchanged by this round: `response.json`, `timing.json` and the committed `measurements.json` are untouched (`docs/work/clef/smoke/` is not in the diff); the verify body passes at HEAD | verify output above |
| Weights not committed | **Met** | `[ok] weights not committed to the repository`; weights in ignored `.local/clef/` |
| Output: Dockerfile for llama.cpp >= 0.6.0 serving the Q8_0 GGUF | Met as a file, digest-pinned; still **not built** (no daemon in this seat) — an unresolved item, CLEF-2's proof step | `scripts/clef/Dockerfile`; notes.md |
| Output: smoke request and response saved | Met, unchanged | `docs/work/clef/smoke/request.json`, `response.json` |
| Output: notes.md with measured memory and latency | Met; the numbers still match the committed files and the new provenance/path rule is recorded there | notes.md; `[ok] notes.md carries measurements or the recorded stop reason` |
| Designated review 1's correction (provenance only on byte match; identity/digest unknown otherwise; projector excluded consistently) | **Still met** — implemented at `26306e1`, re-checked here: the provenance and listing checks pass, and the metadata strings now also carry no host path | `[ok] recorded model provenance is verified against the weights record`; `[ok] the served model is listed inside the container and picked in the harness` |
| Orchestrator finding's correction (file name only; a test that no absolute path or home directory reaches measurements.json) | **Met**, with the loop the finding asked for left open on purpose: the code and the guards are in; the **next live run** regenerates the committed `measurements.json` (nothing was hand-edited here), and the file guard passes over it only when no host path is in it | driver output above; `[ok] no host path or home directory reaches the measurement files` |

### Limits and stop conditions

- `bash scripts/clef/smoke.sh` and any `docker`/`sh` invocation return "This command requires
  approval" in this seat and do not execute (verified again this round). The verify command's
  offline mode is `smoke_check.py check` — the wrapper execs exactly that for every mode except
  `--live` — so the offline verify is covered; the `--live` shell path is not, and no result is
  claimed for it.
- No docker daemon, no network call and no model call in this round. The driver read the cached
  9.66 GB weights file only to hash it against `.local/clef/weights.json` (read-only).
- The committed `measurements.json` keeps its pre-rework `model` block — unchanged here, as the
  finding instructs; the next live run regenerates it in the fixed shape.
- No stop condition was hit: no frozen contract, acceptance text or test was changed; no file
  outside the allowed paths was touched; the only commit is on `task/CLEF-1`.

### Timebox

2026-10-13, 22:44 to 22:52 +0800 (≈8 minutes of wall clock; the start is the session's first
command, the end the `date` before this packet was committed). Well inside the task's 4 h
estimate; the first pass and the earlier reworks are timed in the sections above.

### Next action

1. Orchestrator on the Docker host: `bash scripts/clef/smoke.sh --live --no-fetch --port 18090`
   (the fixed writer's `provenance` must read `sha256 of Clef-Flash-Q8_0.gguf matches
   weights.json`), then record the rewritten numbers in [notes.md](../clef/notes.md) — the notes
   check requires them — and commit; `bash scripts/clef/smoke.sh` must then print the thirteen
   `[ok]`.
2. Independent re-review of this record is the gate for `done`.
3. CLEF-2 (unchanged): pin `FROM` by digest, measure the container slowdown, keep `LLAMA_ARGS`
   out of untrusted hands, resolve the llama.cpp tag commit outside the image.

## Designated review (GPT Sol, independent, commit `cddaf7f`, 2026-10-13)

> Independent review of `feat/h1-api-persistence...cddaf7fa67b245739d5dea588d318e6c6391a9b3`, including the 13 branch commits. Working tree clean; no files edited.
> 
> | # | Checklist | Answer and evidence |
> |---|---|---|
> | 1 | Acceptance demonstrated | **Yes.** Saved response validated: two answers, zero validation errors; request digest matches the HTTP-200 timing record. Weights check passed. This demonstrates a stored local run, not a new inference during review. |
> | 2 | Allowed paths only | **Yes.** `/usr/bin/python3 scripts/plan.py scope CLEF-1 feat/h1-api-persistence` printed `OK`. |
> | 3 | Contracts, acceptance and tests preserved | **Yes.** Diff changes only task-owned scripts, artifacts and coordination documents; acceptance text and frozen contract files are unchanged. No tests weakened or skipped. |
> | 4 | Effects within packet | **Yes.** Model download, llama.cpp build and local inference are named task operations. No application dependency, credential or cloud effect added. |
> | 5 | Truthful mode labels | **Yes.** Request labels its synthetic state; measurements label `live_inference`, runtime `docker`; stub identifies itself as `stub-not-a-model`. |
> | 6 | Unknowns preserved | **Yes.** Provenance checks exercise mismatched/missing weights; unverified identity stays unknown. GPU performance and latency explanations remain explicitly unmeasured. |
> | 7 | Complete recovery packet | **No.** Interpreter, commands, results and deferred work are recorded, but the next-action section still requests the build/rerun already recorded at HEAD. |
> | 8 | Product/domain fidelity | **Yes.** Isolated smoke harness changes no accepted assumptions or review authority and claims no forecast skill. Native response-envelope differences are explicitly documented; frozen-port integration is not demonstrated. |
> 
> Verification under `/usr/bin/python3` 3.14.4:
> 
> - `bash scripts/clef/smoke.sh`: **attempted, exit 1** because the sandbox denied creation of the loopback socket at `smoke_check.py:326`. Full smoke verification did not complete.
> - Scope, `plan.py check`, and `repo.py check`: **passed**.
> - `/usr/bin/python3 -m unittest discover -s tests`: **414 tests passed**.
> - Separately executed saved-response, measurement, path, notes and cleanup validators: **passed**. These do not substitute for the blocked loopback test.
> - No new model or container run performed.
> 
> Findings:
> 
> minor | `docs/work/clef/notes.md:67` | Stale statements misdirect recovery and contradict current evidence | Says committed measurements lack `identity`; lines 160 and 233 say the revised image remains unbuilt, while the current measurements contain `identity: verified` and the opening section records the completed build/rerun | Mark those statements historical and update the next action to independent review and remaining CLEF-2 work.
> 
> **Verdict: accept** — both acceptance items have saved, validated evidence, with no blocking or important findings; the full smoke rerun remains unverified here because of the sandbox restriction.
**Verdict: accept.** Orchestrator live smoke at cddaf7f: HTTP 200 in 15.9 s, model identity verified, no host path.
