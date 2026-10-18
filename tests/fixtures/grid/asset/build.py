#!/usr/bin/env python3
"""Regenerate the asset fixture's payload with the real builder (ATG-7).

The inputs are the bake fixture `tests/fixtures/grid/catalog/bake` — the files the **real**
`scripts/grid/build_data.py` writes over the synthetic grid inputs, already used by
`tests/test_grid_catalog.py` — and this directory's own location material (`geo/sites.csv`,
`geo/crosswalk.csv`). The output is `payload/assets/index.json` and `payload/assets/<code>.json`,
the two payloads `scripts/grid/build_assets.py` writes.

The payload names its records by ATG-4's catalog dataset ids, so it is built with the real
register (`scripts/grid/catalog.json`); a register rename is a reason to run this file again,
which is what `--check` tells a reader:

    /usr/bin/python3 tests/fixtures/grid/asset/build.py           # write payload/
    /usr/bin/python3 tests/fixtures/grid/asset/build.py --check   # rebuild in memory, compare

No network, no clock: the same inputs write the same bytes.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BAKE = ROOT / "tests" / "fixtures" / "grid" / "catalog" / "bake"
GEO = HERE / "geo"
REGISTER = ROOT / "scripts" / "grid" / "catalog.json"
PAYLOAD = HERE / "payload"

SPEC = importlib.util.spec_from_file_location("grid_build_assets", ROOT / "scripts" / "grid" / "build_assets.py")
build_assets = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_assets
SPEC.loader.exec_module(build_assets)


def files():
    built, _ = build_assets.build(BAKE, GEO, REGISTER)
    return built


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="rebuild in memory and compare every byte; write nothing")
    args = parser.parse_args()
    built = files()
    violations = build_assets.contract(built)
    if violations:
        print("build.py: %d contract violation(s)" % len(violations), file=sys.stderr)
        for line in violations:
            print("  " + line, file=sys.stderr)
        return 1
    if args.check:
        problems = []
        for name, data in sorted(built.items()):
            path = PAYLOAD / name
            if not path.is_file():
                problems.append("%s: missing" % path.relative_to(ROOT))
            elif path.read_bytes() != data:
                problems.append("%s: differs from the builder's bytes" % path.relative_to(ROOT))
        for path in sorted(PAYLOAD.rglob("*.json")):
            if path.relative_to(PAYLOAD).as_posix() not in built:
                problems.append("%s: no builder output names this file" % path.relative_to(ROOT))
        print("build.py --check: %d file(s), %d problem(s)" % (len(built), len(problems)))
        for line in problems:
            print("  " + line, file=sys.stderr)
        return 1 if problems else 0
    for name, data in sorted(built.items()):
        path = PAYLOAD / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print("build.py: wrote %d file(s) under %s" % (len(built), PAYLOAD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
