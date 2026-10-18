#!/usr/bin/env python3
"""Run the method seasonal_plus_availability for a re-issue and print its preview (OUT-3).

The method run reads the predecessor vintage's values file by digest through the
archive, the response record, the known-outages export and the demand export
(``src/price/availability.py`` states every rule). It writes, each once and never
over an existing file:

* the values file ``<--out>/<outlook id>.json`` and its sidecar, the run record
  ``<--out>/<outlook id>.availability.json``;
* the method record ``--method-out`` that ``scripts/outlook/issue.py`` consumes.

Then it builds the re-issue preview through ``src.outlook.reissue.build_preview``
with ``--supersedes <predecessor> --reason method_changed`` and prints the delta.
It never issues: the issue is ``scripts/outlook/issue.py ... --confirm <ref>``, a
person's recorded decision. For the November 2026 vintage (the orchestrator runs
this; the executor never writes the real archive)::

    /usr/bin/python3 scripts/outlook/availability.py \\
        --archive .local/outlook-archive \\
        --predecessor outlook-2026-11-system-v2 \\
        --response .local/price/response.json \\
        --known-outages .local/price/known_outages.csv \\
        --demand .local/price/demand_hourly.csv \\
        --cutoff 2026-10-14T16:00:00Z \\
        --outlook-id outlook-2026-11-system-v3 --issuer "<person>" \\
        --out .local/outlook-archive/values \\
        --method-out .local/price/method-2026-11-system-v3.json \\
        --predecessor-input .local/price/lwap_final_hourly.csv \\
        [--outage-class forced] [--allow-exploratory]

Every flag is required except ``--outage-class`` (default ``forced``),
``--predecessor-input`` (each file the predecessor cites; the run refuses
``PREDECESSOR_INPUT_MISSING`` without them) and ``--allow-exploratory``: an exploratory
response cell applies only with it, and its label then travels into the values file, the
run record and the method version; without it the outage is listed as not applied. ``--print-query`` prints the known-outages statement of
``scripts/outlook/known_outages.sql`` and exits. Relative paths are relative to the
current directory; the method record names paths under the repository root relative
to it (the rule ``issue.py`` reads them back with).

Exit status 0 on a written run and its printed preview; 1 on a refusal (the code and
its text on stderr; nothing is written when the method run itself refuses, and a
preview refusal after the write says which files exist); 2 on a usage error. No
model call, no network, no BigQuery call.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # run as a script: the modules live under src/
    sys.path.insert(0, str(ROOT))

from src.outlook import reissue  # noqa: E402
from src.outlook.dependency import DependencyError  # noqa: E402
from src.outlook.records import OutlookArchive, OutlookError  # noqa: E402
from src.price import availability  # noqa: E402

SQL_PATH = ROOT / "scripts" / "outlook" / "known_outages.sql"


def known_outages_query(path=SQL_PATH):
    """The statement between the BEGIN and END markers of the SQL file."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = lines.index("-- BEGIN known_outages")
    end = lines.index("-- END known_outages")
    return "\n".join(lines[start + 1:end]) + "\n"


def parser():
    parse = argparse.ArgumentParser(
        description="Run seasonal_plus_availability for a re-issue and print its preview (OUT-3).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parse.add_argument("--print-query", action="store_true",
                       help="print the known-outages statement and exit")
    for flag, text in (
            ("--archive", "the outlook archive"),
            ("--predecessor", "the vintage to supersede (its values file is read by digest)"),
            ("--response", "the response record (OUT-2)"),
            ("--known-outages", "the known-outages export (scripts/outlook/known_outages.sql)"),
            ("--demand", "the demand export (OUT-2's demand_hourly.csv)"),
            ("--cutoff", "the information cutoff (offset-bearing instant)"),
            ("--outlook-id", "the new vintage's id (names the values file)"),
            ("--issuer", "who will issue it (for the preview)"),
            ("--out", "the directory the values file and its run record are written to"),
            ("--method-out", "the method record path the issue command reads")):
        parse.add_argument(flag, help=text + " (required)")
    parse.add_argument("--outage-class", choices=("forced", "planned"), default="forced",
                       help="the known outages that apply (default forced, the class the response was "
                            "measured on; planned only as a second, labelled run)")
    parse.add_argument("--predecessor-input", action="append", default=[], metavar="FILE",
                       help="a file the predecessor cites (by name and digest), carried forward into the "
                            "method record; repeat for each (the November vintage cites lwap_final_hourly.csv)")
    parse.add_argument("--allow-exploratory", action="store_true",
                       help="let an exploratory response cell apply; its label travels (without it the "
                            "outage is listed as not applied)")
    return parse


def _refuse(error):
    print("availability.py: %s: %s" % (getattr(error, "code", "RUN_FAILED"), error), file=sys.stderr)
    return 1


def main(argv=None):
    parse = parser()
    args = parse.parse_args(argv)
    if args.print_query:
        sys.stdout.write(known_outages_query())
        return 0
    missing = [flag for flag in ("archive", "predecessor", "response", "known_outages", "demand", "cutoff",
                                 "outlook_id", "issuer", "out", "method_out")
               if getattr(args, flag) is None]
    if missing:
        parse.error("required: " + ", ".join("--" + name.replace("_", "-") for name in missing))
    archive = OutlookArchive(args.archive)
    try:
        result = availability.run_method(
            archive=archive, predecessor_id=args.predecessor, response_path=Path(args.response),
            known_outages_path=Path(args.known_outages), demand_path=Path(args.demand),
            cutoff=args.cutoff, outage_class=args.outage_class,
            allow_exploratory=args.allow_exploratory,
            predecessor_inputs=[Path(item) for item in args.predecessor_input])
        method_out = Path(args.method_out)
        if method_out.exists():
            raise availability.AvailabilityError("OUTPUT_EXISTS", method_out.name)
        written = availability.write_run(result, Path(args.out), args.outlook_id)
        record = availability.method_record(result, written, cutoff=args.cutoff)
        method_digest = availability.write_method_record(record, method_out)
    except availability.AvailabilityError as error:
        return _refuse(error)
    run = result["run"]
    print("method: %s" % result["method_version"])
    print("label: %s" % run["label"])
    print("statement: %s" % run["zero_statement"])
    print("response: %s" % run["response"]["sha256"])
    print("values: %s %s rows %d" % (written["values"]["path"], written["values"]["sha256"],
                                     written["values"]["rows"]))
    print("run record: %s %s" % (written["run"]["path"], written["run"]["sha256"]))
    print("method record: %s %s" % (method_out, method_digest))
    counts = run["counts"]
    print("outage class: %s" % run["outage_class"])
    print("known outages: %d, applied %d (forced %d, planned %d), not applied %d (other class %d, "
          "exploratory %d), shifted hours %d of %d" % (
              counts["known_outages"], counts["applied"], counts["applied_forced"], counts["applied_planned"],
              counts["not_applied"], counts["not_applied_other_class"], counts["not_applied_exploratory"],
              counts["shifted_hours"], counts["window_hours"]))
    if run["load_shares"]:
        print("load shares: %s" % ", ".join("%s %s" % item for item in run["load_shares"]["shares"].items()))
    expected = run["expected_delta"]["mean_shift"]
    print("expected mean shift: p10 %s, p50 %s, p90 %s" % (expected["p10"], expected["p50"], expected["p90"]))
    try:
        preview = reissue.build_preview(archive, [], method_out.resolve(), outlook_id=args.outlook_id,
                                        issuer=args.issuer, cutoff=args.cutoff,
                                        supersedes=args.predecessor, reason="method_changed")
    except (reissue.ReissueError, OutlookError, DependencyError) as error:
        print("availability.py: the files above are written; the preview is refused", file=sys.stderr)
        return _refuse(error)
    print("preview: %s" % preview["content_digest"])
    print("predecessor: %s %s" % (preview["predecessor"]["outlook_id"], preview["predecessor"]["outlook_digest"]))
    delta = preview["delta"]
    print("delta: %s -> %s" % (delta["previous_values_digest"], delta["new_values_digest"]))
    for item in delta["horizons"]:
        print("  %s %s -> %s: %d hours, mean %s, mean abs %s, min %s, max %s" % (
            item["label"], item["start"], item["end"], item["hours"], item["mean_difference"],
            item["mean_abs_difference"], item["min_difference"], item["max_difference"]))
    print("not issued: run scripts/outlook/issue.py --method-record %s --cutoff %s --outlook-id %s "
          "--issuer <person> --supersedes %s --reason method_changed --confirm <ref>" % (
              availability.path_text(method_out), args.cutoff, args.outlook_id, args.predecessor))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
