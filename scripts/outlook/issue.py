#!/usr/bin/env python3
"""Issue an outlook vintage from a method record, or re-issue one from a stale mark (OUT-1).

First issue. The method run's record names the method version, its inputs by
path and digest, the information cutoff, the assumption ids, the target series,
the horizon and the values file by path and digest. The command re-reads every
input and the values file, compares each with its digest, and issues the vintage
through the archive's own ``OutlookArchive.issue`` (issued once per id)::

    /usr/bin/python3 scripts/outlook/issue.py \\
        --archive .local/outlook-archive \\
        --method-record .local/price/method-2026-11.json \\
        --cutoff 2026-10-14T16:00:00Z \\
        --outlook-id outlook-2026-11-system-v3 \\
        --issuer "Sam (owner)"

Re-issue. ``--from-stale <mark file>`` (repeatable; every mark must name one
vintage) builds the re-issue preview from a mark stored in the archive's mark
store: the marked vintage by id and digest is the predecessor, the marks' beliefs
are the changed assumptions, and the delta is computed from the predecessor's and
the new values files, each read by digest. Without ``--confirm`` the command
prints the preview (and writes it to ``--preview-out`` when given) and issues
nothing. With ``--confirm <confirmation reference>`` — the desk agent's
confirmation id, or the reference a person gives for their own decision — the
preview is rebuilt from the live archive and the vintage is issued with its
``supersedes`` block. ``--preview <file>`` issues a preview written earlier (the
dock's draft) instead of building one; it still needs ``--confirm``, and the
preview must name the ``--outlook-id``, ``--issuer``, ``--method-record`` and
``--cutoff`` this run gives (``PREVIEW_MISMATCH`` otherwise).

Re-issue without a mark. A method change or an input refresh writes no stale
mark: ``--supersedes <outlook id> --reason method_changed`` (the method version
must differ from the predecessor's) or ``--reason inputs_refreshed`` (an input
digest must differ) names the predecessor directly. The preview, the delta, the
``REPEATS_PREDECESSOR`` and newest-vintage rules and ``--confirm`` work as above;
the mark list and the changed assumptions are empty::

    /usr/bin/python3 scripts/outlook/issue.py --archive .local/outlook-archive \
        --method-record <method.json> --cutoff <instant> \
        --outlook-id outlook-2026-11-system-v3 --issuer "<person>" \
        --supersedes outlook-2026-11-system-v2 --reason method_changed --confirm <ref>

Paths. ``--method-record`` and every path inside a method record (inputs,
values) are read from the repository root when relative, the rule
``score.py`` uses for a values ``path_hint``; ``--archive``, ``--from-stale``,
``--preview`` and ``--preview-out`` are relative to the current directory.

``--cutoff`` and ``--method-record`` are required in every mode: no vintage is
issued without an explicit information cutoff and the method record it came
from, and the cutoff must be the method record's own. A vintage whose values
repeat its predecessor's is refused ``REPEATS_PREDECESSOR`` and nothing is
written. ``--issued-at`` is the instant of the issue; when it is omitted the
command reads the clock once, prints it, and uses it, as ``score.py`` does.
``--dry-run`` builds and prints the record but writes nothing.

Exit status 0 on an issue, a printed preview or a dry run; 1 on a refusal (the
code and its fixed text on stderr); 2 on a usage error. No model call, no
network; the only write is the issued vintage (and the ``--preview-out`` file).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # run as a script: the modules live under src/
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.outlook import reissue  # noqa: E402
from src.outlook.dependency import DependencyError  # noqa: E402
from src.outlook.records import OutlookArchive, OutlookError  # noqa: E402

DEFAULT_ARCHIVE = ROOT / ".local" / "outlook-archive"


def parser() -> argparse.ArgumentParser:
    """The command line; the cutoff and the method record are required in every mode."""
    parse = argparse.ArgumentParser(
        description="Issue an outlook vintage from a method record, or re-issue one from a "
                    "stale mark (OUT-1). The cutoff and the method record are always required.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parse.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                       help="the outlook archive (default: .local/outlook-archive)")
    parse.add_argument("--method-record", required=True,
                       help="the method run's record (JSON): required, no vintage without one; "
                            "a relative path is read from the repository root")
    parse.add_argument("--cutoff", required=True,
                       help="the information cutoff (offset-bearing instant): required, and it "
                            "must be the method record's own")
    parse.add_argument("--outlook-id", required=True, help="the new vintage's id")
    parse.add_argument("--issuer", required=True, help="who issues it")
    parse.add_argument("--issued-at",
                       help="the instant of the issue (offset-bearing); default: the clock, printed")
    parse.add_argument("--from-stale", action="append", type=Path, metavar="MARK",
                       help="re-issue from this stored stale mark (repeatable; relative to the "
                            "current directory)")
    parse.add_argument("--supersedes", metavar="OUTLOOK_ID",
                       help="re-issue this vintage without a stale mark; needs --reason")
    parse.add_argument("--reason", choices=("method_changed", "inputs_refreshed"),
                       help="why a mark-free re-issue is made (with --supersedes only)")
    parse.add_argument("--preview", type=Path,
                       help="issue this re-issue preview (the dock's draft); needs --confirm; "
                            "relative to the current directory")
    parse.add_argument("--preview-out", type=Path,
                       help="write the re-issue preview here (JSON; relative to the current directory)")
    parse.add_argument("--confirm", metavar="REF",
                       help="the confirmation reference of the person's decision; a re-issue "
                            "is written only with one")
    parse.add_argument("--dry-run", action="store_true",
                       help="build and print the record but write nothing")
    return parse


def _now():
    """The one clock reading: the run's instant in UTC ``Z`` form."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _refuse(error):
    print("issue.py: %s: %s" % (getattr(error, "code", "ISSUE_FAILED"), error), file=sys.stderr)
    return 1


def _print_preview(preview):
    print("preview: %s" % preview["content_digest"])
    print("reason: %s" % preview["reason"])
    print("predecessor: %s %s" % (preview["predecessor"]["outlook_id"],
                                  preview["predecessor"]["outlook_digest"]))
    for mark in preview["stale_marks"]:
        print("stale mark: %s %s at %s%s" % (mark["content_digest"], mark["assumption_id"],
                                             mark["new_revision"],
                                             " (demonstration)" if mark["synthetic"] else ""))
    print("changed assumptions: %s" % (", ".join(preview["changed_assumption_ids"]) or "none"))
    print("method record: %s %s" % (preview["method_record"]["path_hint"],
                                    preview["method_record"]["sha256"]))
    print("cutoff: %s" % preview["information_cutoff"])
    delta = preview["delta"]
    print("delta: %s -> %s" % (delta["previous_values_digest"], delta["new_values_digest"]))
    for item in delta["horizons"]:
        print("  %s %s -> %s: %d hours, mean %s, mean abs %s, min %s, max %s" % (
            item["label"], item["start"], item["end"], item["hours"], item["mean_difference"],
            item["mean_abs_difference"], item["min_difference"], item["max_difference"]))


def _issued(record):
    print("issued: %s" % record["outlook_id"])
    print("digest: %s" % record["content_digest"])
    if "supersedes" in record:
        print("supersedes: %s %s" % (record["supersedes"]["outlook_id"],
                                     record["supersedes"]["outlook_digest"]))


def main(argv=None) -> int:
    """One issue, one preview, or one confirmed re-issue; refusals exit 1 with their code."""
    parse = parser()
    args = parse.parse_args(argv)
    named = [flag for flag, value in (("--preview", args.preview), ("--from-stale", args.from_stale),
                                      ("--supersedes", args.supersedes)) if value]
    if len(named) > 1:
        parse.error("%s name one re-issue in different ways; give one" % " and ".join(named))
    if (args.supersedes is None) != (args.reason is None):
        parse.error("--supersedes and --reason go together: a mark-free re-issue states its reason")
    if args.preview is not None and args.confirm is None:
        parse.error("--preview issues a confirmed preview; give --confirm")
    archive = OutlookArchive(args.archive)
    issued_at = args.issued_at if args.issued_at is not None else _now()
    print("issued_at: %s" % issued_at)
    try:
        method, _digest = reissue.load_method_record(reissue.resolve(args.method_record))
        reissue.check_cutoff(method, args.cutoff)
        if args.preview is None and not args.from_stale and args.supersedes is None:
            record = reissue.build_issue(method, outlook_id=args.outlook_id, issued_at=issued_at,
                                         issuer=args.issuer, cutoff=args.cutoff, archive=archive)
            if args.dry_run:
                print("record: %s" % canonical_dumps(record))
                print("dry run: nothing issued")
                return 0
            _issued(archive.issue(record))
            return 0
        if args.preview is not None:
            try:
                preview = json.loads(args.preview.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
                raise reissue.ReissueError("PREVIEW_INVALID") from None
            reissue.validate_preview(preview)
        else:
            marks = [reissue.read_mark_file(path) for path in (args.from_stale or [])]
            preview = reissue.build_preview(archive, marks, args.method_record,
                                            outlook_id=args.outlook_id, issuer=args.issuer,
                                            cutoff=args.cutoff, supersedes=args.supersedes,
                                            reason=args.reason)
        _print_preview(preview)
        if args.preview_out is not None:
            args.preview_out.write_text(canonical_dumps(preview) + "\n", encoding="utf-8")
            print("preview written: %s" % args.preview_out)
        if args.confirm is None:
            print("not confirmed: nothing issued (give --confirm <reference> to issue)")
            return 0
        if args.dry_run:
            print("dry run: nothing issued")
            return 0
        # The id, issuer, method record and cutoff are this run's own flags; a
        # preview that names others is refused (PREVIEW_MISMATCH).
        record = reissue.issue_confirmed(archive, preview, issued_at=issued_at,
                                         confirmation_ref=args.confirm,
                                         outlook_id=args.outlook_id, issuer=args.issuer,
                                         method_record=args.method_record, cutoff=args.cutoff)
        _issued(record)
        return 0
    except (reissue.ReissueError, OutlookError, DependencyError) as error:
        return _refuse(error)
    except OSError:
        print("issue.py: ISSUE_IO: a file could not be written", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
