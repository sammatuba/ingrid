# Probe-bundle fixtures

Labeled synthetic evidence-assumption pairs for the probe bundle (EVAL-1). All content is
fictional: no real unit, operator, market, document or analyst appears here.

- The annotation policy, the frozen digests and the pair tables:
  [docs/work/probe-bundle/fixtures.md](../../../docs/work/probe-bundle/fixtures.md).
- One pair per `pb-*.json` file; each is self-contained `h0.v1` records plus the declared
  cutoffs, expected atomic answers, frozen label and rationale.
- [manifest.json](manifest.json) indexes the classes, the per-file digests and the fixture digest.
- [build.py](build.py) regenerates and validates the set: run
  `/usr/bin/python3 tests/fixtures/probe-bundle/build.py` to write, or
  `/usr/bin/python3 tests/fixtures/probe-bundle/build.py --check` to verify an unchanged tree.
  It is a fixture tool, not a test and not a runtime dependency.

Frozen 2026-10-11 before any backend run. Do not edit a label to match a backend; a re-freeze
needs a new digest and an intent-level decision.
