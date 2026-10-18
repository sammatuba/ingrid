#!/usr/bin/env python3
"""Write the synthetic book fixture from the recorded seed (BOOK-1).

    /usr/bin/python3 scripts/book/generate.py [--seed N] [--out FILE] [--force] [--check]

The fixture is tests/fixtures/book/book-v1.json. The book is invented end to end, a method
demonstration. The command refuses to overwrite a fixture whose content digest differs from the one it
would write, unless --force. --check writes nothing and exits 1 when the file differs. Stdlib only, no
network.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.book import generate, records  # noqa: E402

DEFAULT_OUT = ROOT / "tests" / "fixtures" / "book" / "book-v1.json"


def existing_digest(path):
    """The stored digest of a fixture on disk, or None when absent or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("content_digest") if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=generate.SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true", help="overwrite a fixture whose digest differs")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when the file differs")
    args = parser.parse_args(argv)
    record = records.build_book(args.seed)
    text = records.dumps(record)
    out = args.out
    if out.exists():
        if out.read_text(encoding="utf-8") == text:
            print(f"unchanged: {out} digest {record['content_digest']}")
            return 0
        if args.check:
            print(f"DIFFERS: {out}", file=sys.stderr)
            return 1
        old = existing_digest(out)
        if old != record["content_digest"] and not args.force:
            print(f"refused: {out} holds digest {old}, this run would write {record['content_digest']}; "
                  "pass --force to overwrite", file=sys.stderr)
            return 2
    elif args.check:
        print(f"MISSING: {out}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    c = record["counts"]
    print(f"wrote {out}: {c['accounts']} accounts, {c['nodes']} nodes, {c['contracts']} contracts, "
          f"{c['profiles']} profiles, digest {record['content_digest']}; {records.LABEL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
