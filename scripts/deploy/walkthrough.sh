#!/usr/bin/env bash
# HOST-1: build the image, run it read-only with no environment, and walk the demo service
# through its published port.
#
# `run-demo.sh` opens the walkthrough for a person; this script proves it end to end and prints
# the record: the page and the assets, the documented fictional sign-in, the compiled and saved
# disposition with its receipt (and the idempotent replay), a password-free judge session, the
# cross-session and private-case 404s, and the session-local reset with its token rotation.
# Nothing reaches a cloud service, a model or a credential: the only contact is the demo mode
# on 127.0.0.1, and the walkthrough program needs only /usr/bin/python3.
#
# Needs a working Docker daemon, so the orchestrator runs it (the executor seat cannot run
# docker); its output is recorded in docs/work/reviews/HOST-1.md.
set -euo pipefail
cd "$(dirname "$0")/../.."

IMAGE="${IMAGE:-grid-nowcast}"
PORT="${PORT:-18001}"
NAME="${NAME:-grid-nowcast-walkthrough}"

docker build -t "$IMAGE" .
docker rm --force "$NAME" >/dev/null 2>&1 || true
# No --env, no --env-file and no -e: NOWCAST_ENV unset selects demo mode. The same container
# contract run-demo.sh uses: read-only, /tmp as the only writable scratch space.
docker run --detach --rm --read-only --tmpfs /tmp --publish "${PORT}:8080" --name "$NAME" "$IMAGE" >/dev/null
cleanup() { docker stop "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

/usr/bin/python3 scripts/deploy/walkthrough.py --port "$PORT"
