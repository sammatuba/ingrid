# Grid Nowcast — one image serving the API and the workspace in safe demo mode.
#
# Started with no environment at all, the image serves the labelled fictional fixtures from the
# in-process demo store: no credential, no emulator and no cloud service. NOWCAST_ENV=hosted
# selects the deployed assembly (Firebase Auth and Firestore), which HOST-2 configures.
#
# No credential, key file, environment file or .local/ content is copied into the image; every
# value arrives at run time as an environment name. See scripts/deploy/README.md.
#
# Base interpreter: Python 3.14.4, the interpreter requirements/h1.lock was resolved and
# verified on, pinned by tag and registry digest. The digest was resolved with `docker buildx
# imagetools inspect python:3.14.4-slim-bookworm` and the image was built and run read-only on
# 2026-10-12; the build, the run and the digest are recorded in the HOST-1 packet
# (docs/work/reviews/HOST-1.md). Re-resolving the tag at deploy time is HOST-2's step.
FROM python:3.14.4-slim-bookworm@sha256:fc74d22ffd0d5ac395a4b7bdda75a4539758862c49ebf3005647084631e63789

# No bytecode and no pip cache: the runtime filesystem is never written, so the container can
# run read-only. PYTHONPATH makes `src.api.hosted` importable from the console-script entry point.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies come from the existing lock; this image adds no dependency of its own.
COPY requirements/h1.lock ./requirements/h1.lock
RUN pip install --no-cache-dir --no-compile -r requirements/h1.lock

# The application and the workspace assets it serves (`/`, `/assets/*`).
COPY src ./src

# The grid replay snapshot GRID-1 bakes with scripts/grid/build_data.py: one JSON file per
# contract file, served by the grid page from /grid-data/. It is company WESM data, so it is
# never committed — `build/grid-data/` must be present in the build context (the builder
# writes it; scripts/release/allowlist.json excludes it from the public export) and the data
# ships inside the image only. The builder follows this line's destination.
#
# ATG-8: the same line carries everything the desk reads, not only the seven GRID-1 files —
# the bake is one directory and `scripts/grid/build_all.py` writes all of it there: the nine
# ATG-1/EXPL-2 contract files, ATG-4's `catalog.json`, ATG-5's `briefs.json` and
# `findings.json`, and ATG-7's `assets/` directory of site profiles. One `COPY` of the
# directory is what makes every one of them reachable under the build stamp the `/data`,
# `/assets`, `/asset/<code>` and `/` pages name; a second per-family line would be a second
# copy of the same tree and is refused by tests/test_grid_data.py.
COPY build/grid-data ./src/grid/grid-data

# The signed permission records, and nothing else from docs/. A judge session seeds its own copy
# of the real PEDC event case (GRID-3), and the review core refuses a real record whose
# `permission_ref` is not an identifier of a signed file under `docs/work/permissions/`
# (src/review/records.py); without this line the image serves the demo without event cases.
COPY docs/work/permissions ./docs/work/permissions

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 nowcast
USER nowcast

EXPOSE 8080
# --factory: the entry point reads and validates the environment before building any client; an
# inconsistent environment exits non-zero instead of serving. No access log: the app logs
# request correlation ids itself.
CMD ["sh", "-c", "exec uvicorn src.api.hosted:app --factory --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
