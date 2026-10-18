#!/usr/bin/env python3
"""Score an issued outlook against the settled final series and append its receipt (SCORE-1).

The receipt is the archive's record that one issued outlook was scored against one
final series version once its window settled. This command is the person-run path
that produces one: it reads the outlook and its values file from ``--archive``,
reads the *final* regional export named by ``--regional``, checks it against the
digest record named by ``--digests``, refuses a window that has not settled, and
appends the sealed receipt through the archive's own ``append_receipt`` — the
store refuses a second receipt for the same
``(outlook_id, final_series_version)`` pair (``RECEIPT_DUPLICATE``).

    /usr/bin/python3 scripts/outlook/score.py \\
        --archive .local/outlook-archive \\
        --outlook-id outlook-2026-11-system \\
        --regional .local/price/lwap_final_hourly.csv \\
        --digests .local/price/digests.json \\
        --final-series-version final-bmonth-2026-11 \\
        --scored-at 2026-11-26T09:00:00Z

``--final-series-version`` is required: a receipt names the settled vintage it was
scored against, and no default is honest. ``--scored-at`` is the instant the run
is made; when it is omitted the command reads the clock once, prints it, and uses
that instant, so a dry run and the real run of the same minute carry the same
``scored_at``. ``--dry-run`` builds and prints the receipt but appends nothing.

The command prints the effective ``scored_at``, the window, the coverage, and the
receipt's storage key and content digest. It never issues an outlook, never writes
an attribution, calls no model and opens no network connection; the only files it
reads are the archive, the outlook's values file and the final export (checked
against its digest record).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # run as a script: the modules live under src/
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.outlook.records import (  # noqa: E402
    OutlookArchive,
    OutlookError,
    receipt_stem,
)
from src.outlook.scoring import ScoringError, score_outlook  # noqa: E402
from src.price.series import SeriesError, load_digests  # noqa: E402

DEFAULT_ARCHIVE = ROOT / ".local" / "outlook-archive"


def parser() -> argparse.ArgumentParser:
    """The command line: the outlook, the final export's digest record and the vintage."""
    parse = argparse.ArgumentParser(
        description="Score an issued outlook against the settled final series (SCORE-1).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parse.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                       help="the outlook archive holding the issued outlook (default: "
                            ".local/outlook-archive)")
    parse.add_argument("--outlook-id", required=True,
                       help="the issued outlook to score")
    parse.add_argument("--regional", required=True, type=Path,
                       help="the final regional price export (the settled vintage)")
    parse.add_argument("--digests", required=True, type=Path,
                       help="the export digest record the final export must match")
    parse.add_argument("--final-series-version", required=True,
                       help="the settled vintage's name, written into the receipt")
    parse.add_argument("--scored-at",
                       help="the instant of this run (offset-bearing); default: the clock, printed")
    parse.add_argument("--dry-run", action="store_true",
                       help="build and print the receipt but append nothing")
    return parse


def _now():
    """The one clock reading: the run's instant in UTC ``Z`` form."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _values_path(outlook):
    """The values file the outlook cites: absolute as stored, else from the repository root."""
    hint = Path(outlook["values_ref"]["path_hint"])
    return hint if hint.is_absolute() else ROOT / hint


def main(argv=None) -> int:
    """Score through the archive's own builder, append unless dry-running, print key and digest."""
    args = parser().parse_args(argv)
    archive = OutlookArchive(args.archive)
    scored_at = args.scored_at if args.scored_at is not None else _now()
    print("scored_at: %s" % scored_at)
    try:
        outlook = archive.outlook(args.outlook_id)
    except OutlookError as error:
        print("score.py: %s: %s" % (error.code, error), file=sys.stderr)
        return 1
    try:
        digests = load_digests(args.digests)
    except (OSError, ValueError, SeriesError):
        print("score.py: DIGESTS_UNREADABLE: the export digest record could not be read",
              file=sys.stderr)
        return 1
    try:
        receipt = score_outlook(outlook, _values_path(outlook), args.regional, digests,
                                scored_at=scored_at,
                                final_series_version=args.final_series_version)
        if args.dry_run:
            print("receipt: %s" % canonical_dumps(receipt))
        else:
            archive.append_receipt(receipt)
    except (OutlookError, ScoringError, SeriesError) as error:
        print("score.py: %s: %s" % (getattr(error, "code", "SCORE_FAILED"), error),
              file=sys.stderr)
        return 1
    skipped = sum(item["count"] for item in receipt["coverage"]["skipped"])
    print("window: %s -> %s" % (receipt["window"]["start"], receipt["window"]["end"]))
    print("coverage: %d scored, %d skipped" % (receipt["coverage"]["scored"], skipped))
    print("key: %s" % receipt_stem(receipt))
    print("digest: %s" % receipt["content_digest"])
    if args.dry_run:
        print("dry run: nothing appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
