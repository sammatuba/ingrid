#!/usr/bin/env python3
"""Score the PRICE-2 baselines against the exported price series (stdlib only).

Reads the PRICE-1 exports under ``.local/price/``, checks them against
``digests.json``, and writes the scorecard record: bias, MAE, RMSE and pinball at
p10/p50/p90 per series and horizon, with every excluded origin under a reason.

    /usr/bin/python3 scripts/price/baselines.py \
        --regional .local/price/lwap_final_hourly.csv \
        --nodal .local/price/portfolio_nodal_hourly_deid.csv \
        --digests .local/price/digests.json \
        --out .local/price/scorecard.json

The record is deterministic: the same bytes and configuration give the same
JSON, and the printed ``content_digest`` is the SHA-256 of those bytes. The file
is written as the canonical JSON itself, with no trailing newline, so the digest
is the digest of the file exactly. No price value, node name or portfolio volume
is written into the repository.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.price.baselines import HORIZONS, default_baselines  # noqa: E402
from src.price.scorecard import MARKET, build_scorecard  # noqa: E402
from src.price.series import (  # noqa: E402
    Series,
    SeriesError,
    digest_file,
    load_digests,
    load_nodal,
    load_regional,
    verify_inputs,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regional", required=True, help="the regional hourly export")
    parser.add_argument("--nodal", help="the de-identified load-node export (optional)")
    parser.add_argument("--digests", help="the export digest record to check against")
    parser.add_argument("--out", help="write the scorecard JSON here")
    parser.add_argument("--series", choices=("regional", "nodal", "both"), default="both")
    parser.add_argument("--horizons", default=",".join(HORIZONS))
    parser.add_argument("--embargo-hours", type=int, default=24)
    parser.add_argument("--min-fan-samples", type=int, default=12)
    parser.add_argument("--summary-series", default="regional",
                        help="which series the printed table covers (regional, nodal, both, none)")
    return parser.parse_args(argv)


def collect(args: argparse.Namespace) -> tuple[list[Series], list[dict]]:
    """Load the requested series and check the exported bytes by digest."""
    wanted: list[str] = []
    inputs: list[dict] = []
    digests = load_digests(args.digests) if args.digests else None
    if args.series in ("regional", "both"):
        wanted.append(args.regional)
    if args.series in ("nodal", "both") and args.nodal:
        if Path(args.nodal).exists():
            wanted.append(args.nodal)
        else:
            print(f"note: {args.nodal} is not present; scoring the regional series only",
                  file=sys.stderr)
    if digests is not None:
        inputs = verify_inputs(wanted, digests)
    else:
        inputs = [{"file": Path(path).name, "sha256": digest_file(path)} for path in wanted]

    series: list[Series] = []
    if args.series in ("regional", "both"):
        series.extend(load_regional(args.regional))
    if args.series in ("nodal", "both") and args.nodal and Path(args.nodal).exists():
        series.extend(load_nodal(args.nodal))
    return series, inputs


def print_summary(scorecard, which: str) -> None:
    """One block per series and horizon: counts, then one line per baseline."""
    print(f"{scorecard.version}: {len(scorecard.series)} series, "
          f"embargo {scorecard.embargo_hours} h, min fan {scorecard.min_fan_samples}")
    for entry in scorecard.inputs:
        print(f"input {entry['file']} sha256 {entry['sha256'][:16]}... rows {entry.get('rows')}")
    for report in scorecard.series:
        if which != "both" and report.kind != which:
            continue
        print(f"\n{report.key} [{report.kind}] {report.label} ({report.rows} hourly rows)")
        marks = report.marks
        if marks.absent_months or marks.short_months or marks.irregular_days:
            print(f"  marks: absent {list(marks.absent_months)} short {list(marks.short_months)} "
                  f"irregular days {list(marks.irregular_days)}")
        print(f"  administered pricing: all {list(marks.ap_all_months)} "
              f"mixed {list(marks.ap_mixed_months)}")
        for horizon in report.horizons:
            scored = dict(horizon.scored)
            excluded = ", ".join(f"{code} {count}" for code, count in horizon.excluded) or "none"
            print(f"  {horizon.horizon:5} window {horizon.window_hours} h "
                  f"candidates {horizon.candidates} scored {scored.get(MARKET, 0)} market "
                  f"/ {scored.get('ap', 0)} ap | excluded: {excluded}")
            for baseline in horizon.baselines:
                for slice_name, metrics in baseline.slices.items():
                    if not metrics.count:
                        continue
                    print(f"    {baseline.name:31} {slice_name:6} n={metrics.count:5} "
                          f"bias={metrics.bias:10.3f} mae={metrics.mae:10.3f} "
                          f"rmse={metrics.rmse:10.3f} pinball p10={metrics.pinball_p10:10.3f} "
                          f"p50={metrics.pinball_p50:10.3f} p90={metrics.pinball_p90:10.3f}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    horizons = tuple(name for name in args.horizons.split(",") if name)
    try:
        series, inputs = collect(args)
        scorecard = build_scorecard(
            series,
            baselines=default_baselines(),
            horizons=horizons,
            inputs=inputs,
            embargo_hours=args.embargo_hours,
            min_fan_samples=args.min_fan_samples,
        )
    except SeriesError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.summary_series != "none":
        print_summary(scorecard, args.summary_series)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Exactly the canonical JSON whose SHA-256 is printed below, with no
        # trailing newline: the digest is the digest of the file's bytes.
        out.write_text(scorecard.to_json(), encoding="utf-8")
        print(f"\nwrote {out} ({out.stat().st_size} bytes)")
    print(f"content_digest {scorecard.content_digest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
