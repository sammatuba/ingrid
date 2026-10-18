"""Run the plain-language rules of scripts/repo.py on the files named on the command line.
Usage: python3 scripts/docs/check_plain.py docs/work/showcase-2026-10-18/*.md"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repo import plain_language_errors, read_json  # noqa: E402
ROOT = Path(__file__).resolve().parents[2]
config = read_json(ROOT, "docs/routes.json").get("plain_language", {})
errors = []
for name in sys.argv[1:]:
    errors += plain_language_errors(ROOT, (ROOT / name).resolve(), config)
print("\n".join(errors))
print(f"{len(errors)} plain-language errors in {len(sys.argv) - 1} files")
sys.exit(1 if errors else 0)
