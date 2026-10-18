#!/usr/bin/env bash
# HOST-1: build the image and run safe demo mode with no environment and no credential.
# The walkthrough is then at http://127.0.0.1:18001/ (the same port scripts/m3/serve.sh uses).
set -euo pipefail
cd "$(dirname "$0")/../.."

IMAGE="${IMAGE:-grid-nowcast}"
PORT="${PORT:-18001}"

docker build -t "$IMAGE" .
# No --env, no --env-file and no -e: NOWCAST_ENV unset selects demo mode over the labelled
# fictional fixtures with everything held in process memory. --read-only is the container
# contract from the hosting intent: the image writes nothing (no bytecode, no disk state), so
# the filesystem stays read-only and /tmp is the only writable scratch space.
exec docker run --rm --read-only --tmpfs /tmp --publish "${PORT}:8080" "$IMAGE"
