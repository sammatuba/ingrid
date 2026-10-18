#!/usr/bin/env python3
"""Price the synthetic portfolio against the PRICE-2 outlook bands (stdlib only).

Reads the PRICE-1 exports under ``.local/price/`` (checked against
``digests.json``), re-runs the PRICE-2 scorecard on the same bytes with a band
sink, and refuses unless the rebuilt record's digest equals the SHA-256 of the
scorecard file it was handed. Then, per de-identified load node and horizon, it
prices the synthetic portfolio's uncovered hours against each baseline's band and
the node's contract price, and classifies the change between consecutive scored
origins against the materiality line:

    /usr/bin/python3 scripts/price/impact.py \
        --portfolio .local/price/portfolio-synthetic.json \
        --scorecard .local/price/scorecard.json \
        --regional .local/price/lwap_final_hourly.csv \
        --nodal .local/price/portfolio_nodal_hourly_deid.csv \
        --digests .local/price/digests.json \
        --out .local/price/impact.json

The materiality line is stated before any change is scored: the run prints it
first, and the record carries it as its first block after its identity. Every
peso figure is a method demonstration on the synthetic portfolio, labelled as
such, and never a business number. The data label is composed at run time from
the inputs the run verified — each file by name, its row count and the first
eight hex digits of its digest — so it describes the exported bytes actually
read: the fixed synthetic statement prints before any input, and the composed
label prints once the exports are verified and carries the record. The record
holds portfolio volumes and contract prices, so it is written under ``.local/``
only: a path inside the repository tree outside ``.local/`` is refused. The same
command regenerates the record after the data refresh (step D of
``docs/work/data-foundation/refresh-brief-2026-10-16.md``).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.price.baselines import default_baselines  # noqa: E402
from src.price.impact import (  # noqa: E402
    KIND,
    MATERIALITY_RULE,
    SYNTHETIC_STATEMENT,
    VERSION,
    ImpactError,
    MaterialityPolicy,
    build_impact_record,
    load_portfolio,
    pair_positions,
    record_digest,
    record_text,
    refuse_output_inside_the_tree,
    verify_bands_against_record,
)
from src.price.scorecard import ScoredBand, build_scorecard  # noqa: E402
from src.price.series import (  # noqa: E402
    SeriesError,
    digest_file,
    load_digests,
    load_nodal,
    load_regional,
    verify_inputs,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--portfolio", required=True, help="the synthetic portfolio JSON")
    parser.add_argument("--scorecard", required=True, help="the PRICE-2 scorecard record")
    parser.add_argument("--regional", required=True, help="the regional hourly export")
    parser.add_argument("--nodal", required=True, help="the de-identified load-node export")
    parser.add_argument("--digests", help="the export digest record to check against")
    parser.add_argument("--threshold", type=float, default=None,
                        help="override the stated materiality line, in pesos")
    parser.add_argument("--out", help="write the impact record JSON here (under .local/)")
    parser.add_argument("--summary", choices=("node", "none"), default="node")
    return parser.parse_args(argv)


def read_record(path: Path) -> dict:
    """The scorecard record, refused unless it carries what the replay needs."""
    if not path.exists():
        raise ImpactError("MISSING_SCORECARD", str(path))
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise ImpactError("MALFORMED_SCORECARD", f"{path.name}: {error}") from error
    if not isinstance(record, dict) or record.get("kind") != "price-baseline-scorecard":
        raise ImpactError("NOT_A_SCORECARD", path.name)
    series = record.get("series")
    if (not isinstance(series, list) or not series or not isinstance(series[0], dict)
            or not series[0].get("horizons") or not isinstance(record.get("baselines"), list)
            or not isinstance(record.get("embargo_hours"), int)
            or not isinstance(record.get("min_fan_samples"), int)
            or not isinstance(record.get("version"), str)):
        raise ImpactError("MALFORMED_SCORECARD", f"{path.name}: configuration or series missing")
    return record


def replay_scorecard(args: argparse.Namespace, record: dict) -> tuple[list[ScoredBand], list[dict]]:
    """Rebuild the PRICE-2 record from the exports and prove it against the file.

    The bands this run prices are the record's bands only if the rebuild
    reproduces the record's bytes: the rebuilt digest is compared with the
    SHA-256 of the scorecard file, and a mismatch refuses the run.
    """
    digests = load_digests(args.digests) if args.digests else None
    wanted = [args.regional, args.nodal]
    if digests is not None:
        inputs = verify_inputs(wanted, digests)
    else:
        inputs = [{"file": Path(path).name, "sha256": digest_file(path)} for path in wanted]
    series = list(load_regional(args.regional)) + list(load_nodal(args.nodal))
    horizons = tuple(entry["horizon"] for entry in record["series"][0]["horizons"])
    bands: list[ScoredBand] = []
    rebuilt = build_scorecard(
        series,
        baselines=default_baselines(),
        horizons=horizons,
        inputs=inputs,
        embargo_hours=record["embargo_hours"],
        min_fan_samples=record["min_fan_samples"],
        band_sink=bands,
    )
    on_disk = digest_file(args.scorecard)
    if rebuilt.content_digest() != on_disk:
        raise ImpactError(
            "SCORECARD_NOT_REPRODUCED",
            f"{Path(args.scorecard).name}: rebuilt {rebuilt.content_digest()[:16]}... "
            f"is not the file's {on_disk[:16]}...",
        )
    scorecard_input = {
        "file": Path(args.scorecard).name,
        "sha256": on_disk,
        "content_digest": rebuilt.content_digest(),
        "version": record["version"],
    }
    return bands, inputs + [scorecard_input]


def print_summary(record: dict) -> None:
    for node in record["nodes"]:
        for horizon in node["horizons"]:
            parts = []
            for block in horizon["baselines"]:
                changes = block["changes"]
                parts.append(f"{block['baseline']} material {changes['material']}/{changes['compared']}")
            print(f"  {node['node']} {node['region']:8} {horizon['horizon']:5} "
                  f"origins {horizon['origins']:5} ap-excluded {horizon['ap_origins_excluded']:4} | "
                  + " | ".join(parts))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # The line is stated here, before any input is read and before any change is
    # scored; the record carries the same line as its first block.
    policy = MaterialityPolicy() if args.threshold is None else MaterialityPolicy(threshold_php=args.threshold)
    print(f"{KIND} {VERSION} - materiality stated before any change is scored")
    print(f"materiality: change at or above {policy.threshold_php:,.2f} PHP is material "
          f"(comparator {policy.comparator})")
    print(f"rule: {MATERIALITY_RULE}")
    # The synthetic statement is fixed and prints before any input is read. The
    # data half of the label can only be composed from the inputs the run
    # verifies, so it prints again, composed, once the replay has checked them.
    print(f"label: {SYNTHETIC_STATEMENT}")
    try:
        out = Path(args.out) if args.out else None
        if out is not None:
            # the guard returns the resolved path, so what is written is exactly
            # what was checked
            out = refuse_output_inside_the_tree(out)
        positions = load_portfolio(args.portfolio)
        record_file = read_record(Path(args.scorecard))
        bands, inputs = replay_scorecard(args, record_file)
        cells = verify_bands_against_record(bands, record_file)
        baseline_names = tuple(entry["name"] for entry in record_file["baselines"])
        pair_positions(positions, bands)
        portfolio_input = {
            "file": Path(args.portfolio).name,
            "sha256": digest_file(args.portfolio),
            "synthetic": True,
            "nodes": len(positions),
        }
        record = build_impact_record(positions, bands, policy, inputs + [portfolio_input],
                                     baselines=baseline_names)
    except (SeriesError, ImpactError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"label: {record['label']}")
    print(f"scorecard {record_file['version']} reproduced from the exported bytes: "
          f"{len(bands)} scored bands, {cells} metric cells recomputed from the band levels "
          f"and equal to the record's")
    if args.summary != "none":
        print_summary(record)
    check = record["direction_check"]
    print(f"direction check IMPACT-1: {check['material_changes']} of {check['changes_compared']} "
          f"changes material at the stated line, in {check['nodes_with_a_material_change']} of "
          f"{len(positions)} nodes")
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        # Exactly the canonical JSON whose SHA-256 is printed below, with no
        # trailing newline: the digest is the digest of the file's bytes.
        out.write_text(record_text(record), encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size} bytes)")
    print(f"content_digest {record_digest(record)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
