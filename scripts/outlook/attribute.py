#!/usr/bin/env python3
"""Attach one attribution to a stored scoring receipt — the person-driven write path (ARCH-4).

An attribution is a person's statement that a named part of a miss is owed to a belief that was
wrong, a signal that arrived late, or the method. It is a record of its own, appended beside the
sealed receipt it explains; the receipt is never edited. This command is the only write path:
there is no model path that calls ``append_attribution``, and a model's proposed attribution
belongs in a judgment record, never here.

The receipt is read from the archive by its ``outlook_id`` and ``final_series_version`` — never
typed in — and the record is built by the archive module's own ``build_attribution``, so every
cross-record rule (the exact receipt bytes, the receipt's outlook, the closed causes, the belief
the outlook rested on, the signal's two clocks, the model version, the share range and the
inherited provenance) is checked before anything is written. ``--attributed-at`` is required:
no clock is read here, exactly as no other timestamp in this archive is. The command never
issues or scores an outlook; it refuses an unknown receipt.

    /usr/bin/python3 scripts/outlook/attribute.py --archive .local/outlook-archive \\
        --outlook-id outlook-2026-11-system --final-series-version final-bmonth-2026-11 \\
        --cause belief --assumption-id price:final_settlement_lmp \\
        --statement "The settlement basis was read too late." \\
        --attributed-by "a named analyst" --attributed-at 2026-11-26T09:00:00Z [--share 0.4]

``--share`` is an optional decimal string in [0, 1]; the shares of one receipt are not refused
at write time (one exclusive create cannot see its siblings), and the archive's ``verify()``
reports a sum above one, which the desk shows beside the receipt. ``--synthetic`` declares the
attribution a labelled demonstration; a real attribution is refused on a synthetic receipt.
On success the command prints the record's storage key and its content digest.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # run as a script: the archive lives under src/
    sys.path.insert(0, str(ROOT))

from src.outlook.records import (  # noqa: E402
    CAUSES,
    OutlookArchive,
    OutlookError,
    attribution_key,
    build_attribution,
)

DEFAULT_ARCHIVE = ROOT / ".local" / "outlook-archive"


def parser() -> argparse.ArgumentParser:
    """The command line: the receipt, the cause and its reference, the statement and the author."""
    parse = argparse.ArgumentParser(
        description="Attach one attribution to a stored scoring receipt (ARCH-4).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parse.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                       help="the outlook archive holding the receipt (default: "
                            ".local/outlook-archive)")
    parse.add_argument("--outlook-id", required=True,
                       help="the issued outlook whose receipt is being explained")
    parse.add_argument("--final-series-version", required=True,
                       help="the final series version the receipt was scored against")
    parse.add_argument("--cause", required=True, choices=CAUSES,
                       help="belief, signal or method — the foundation page's three causes")
    parse.add_argument("--assumption-id",
                       help="the register row a belief cause names (one of the outlook's ids)")
    parse.add_argument("--signal-source",
                       help="the source a signal cause names")
    parse.add_argument("--available-at",
                       help="when the signal became available (offset-bearing instant)")
    parse.add_argument("--effective-at",
                       help="when the signal took effect (offset-bearing instant)")
    parse.add_argument("--method-ref",
                       help="the model version a method cause names (the outlook's own)")
    parse.add_argument("--share",
                       help="the part of the miss this cause explains, a decimal in [0, 1]")
    parse.add_argument("--statement", required=True,
                       help="one sentence in the author's words")
    parse.add_argument("--attributed-by", required=True,
                       help="the person making the statement (required; non-blank)")
    parse.add_argument("--attributed-at", required=True,
                       help="when the statement was made (offset-bearing instant; no clock is read)")
    parse.add_argument("--synthetic", action="store_true",
                       help="declare this attribution a labelled demonstration")
    return parse


def main(argv=None) -> int:
    """Build the attribution through the archive's own builder, append it, print its key and digest."""
    args = parser().parse_args(argv)
    archive = OutlookArchive(args.archive)
    try:
        outlook = archive.outlook(args.outlook_id)
        receipt = next((record for record in archive.receipts(args.outlook_id)
                        if record["final_series_version"] == args.final_series_version), None)
        if receipt is None:
            print("attribute.py: no stored receipt for outlook %s against final series %r"
                  % (args.outlook_id, args.final_series_version), file=sys.stderr)
            return 1
        signal_ref = None
        if (args.signal_source is not None or args.available_at is not None
                or args.effective_at is not None):
            signal_ref = {"source": args.signal_source, "available_at": args.available_at,
                          "effective_at": args.effective_at}
        attribution = build_attribution(
            receipt, outlook, cause=args.cause, statement=args.statement,
            attributed_by=args.attributed_by, attributed_at=args.attributed_at,
            synthetic=args.synthetic, assumption_id=args.assumption_id,
            signal_ref=signal_ref, method_ref=args.method_ref, share=args.share)
        archive.append_attribution(attribution)
    except OutlookError as error:
        print("attribute.py: %s: %s" % (error.code, error), file=sys.stderr)
        return 1
    print("key: %s" % attribution_key(attribution))
    print("digest: %s" % attribution["content_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
