#!/usr/bin/env python3
"""Write the synthetic outlook vintages the book's impact tests and the book page price against.

    /usr/bin/python3 scripts/book/vintages.py            # write tests/fixtures/book/vintages/
    /usr/bin/python3 scripts/book/vintages.py --check    # compare, write nothing, exit 1 on a difference

Each vintage is an ``OutlookRecord`` issued through the real archive (``src.outlook.records``), never
typed by hand, and a values file in the shape ``src/outlook/scoring.py`` reads: a ``series`` key and one
``{hour_start, value, p10, p50, p90}`` row per local hour. The record cites the values file by its
SHA-256, so a test can tie the band to the record by digest.

Every price here is invented by the stated band rule below. Both vintages declare ``synthetic: true``.
No real price, node, outlook or portfolio value is read. Stdlib only, no network.

BOOK-2 wrote the two Visayas vintages. BOOK-3 adds one Luzon and one Mindanao vintage for the same day, so
the book page can price every region of the book against a regional band. A rule without a ``series`` key
is a Visayas rule, so the first two records keep their bytes and their digests.
"""
import argparse
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contracts.jsonutil import canonical_dumps  # noqa: E402
from src.outlook.records import OutlookArchive, build_outlook  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "book" / "vintages"
HINT = "tests/fixtures/book/vintages/values/%s.json"
DAY = "2026-10-19"
PEAK = range(8, 22)
LABEL = ("Synthetic outlook vintage for the book's impact tests. A stated band rule invents every price "
         "in it, a method demonstration.")

#: The band rule of each vintage, in PHP/MWh: p50 off-peak and peak, and the distance of p10 and p90
#: from p50. The second vintage raises the peak hours, as a re-issue after a synthetic unit trip would.
RULES = {
    "book-demo-2026-10-19-cvis": {"p50_offpeak": 5200, "p50_peak": 7400, "p10_below": 1200,
                                     "p90_above": 2600, "issued_at": "2026-10-18T02:00:00Z",
                                     "information_cutoff": "2026-10-14T16:00:00Z"},
    "book-demo-2026-10-19-cvis-v2": {"p50_offpeak": 5200, "p50_peak": 8900, "p10_below": 1700,
                                        "p90_above": 3500, "issued_at": "2026-10-18T06:00:00Z",
                                        "information_cutoff": "2026-10-18T00:00:00Z"},
    # BOOK-3: one vintage per other region, so every account of the book has a regional band.
    "book-demo-2026-10-19-cluz": {"series": "CLUZ", "p50_offpeak": 4900, "p50_peak": 6800, "p10_below": 1100,
                                     "p90_above": 2400, "issued_at": "2026-10-18T02:00:00Z",
                                     "information_cutoff": "2026-10-14T16:00:00Z", "issuer": "BOOK-3 fixture"},
    "book-demo-2026-10-19-cmin": {"series": "CMIN", "p50_offpeak": 5600, "p50_peak": 7900, "p10_below": 1300,
                                     "p90_above": 2900, "issued_at": "2026-10-18T02:00:00Z",
                                     "information_cutoff": "2026-10-14T16:00:00Z", "issuer": "BOOK-3 fixture"},
}


def values_document(outlook_id: str) -> dict:
    rule = RULES[outlook_id]
    hours = []
    for hour in range(24):
        p50 = rule["p50_peak"] if hour in PEAK else rule["p50_offpeak"]
        hours.append({"hour_start": f"{DAY}T{hour:02d}:00:00", "value": p50,
                      "p10": p50 - rule["p10_below"], "p50": p50, "p90": p50 + rule["p90_above"]})
    return {"series": rule.get("series", "CVIS"), "horizon": "day", "day": DAY, "source": "scripts/book/vintages.py band rule",
            "synthetic": True, "label": LABEL, "hours": hours}


def values_bytes(outlook_id: str) -> bytes:
    return (canonical_dumps(values_document(outlook_id)) + "\n").encode("utf-8")


def outlook_fields(outlook_id: str) -> dict:
    rule = RULES[outlook_id]
    data = values_bytes(outlook_id)
    rule_digest = hashlib.sha256(canonical_dumps(rule).encode("utf-8")).hexdigest()
    return dict(
        outlook_id=outlook_id,
        issued_at=rule["issued_at"],
        information_cutoff=rule["information_cutoff"],
        horizon={"label": "day", "start": "2026-10-18T16:00:00Z", "end": "2026-10-19T16:00:00Z"},
        target_series_ref={"table": "fixture_book.synthetic_regional_price", "column": "price",
                           "version": f"fixture-day-{DAY}"},
        inputs=[{"name": "scripts/book/vintages.py band rule " + outlook_id, "digest": rule_digest}],
        assumption_ids=["availability:syn-bay-unit-2"],
        model_version="book fixture band rule",
        values_ref={"path_hint": HINT % outlook_id, "sha256": hashlib.sha256(data).hexdigest(),
                    "rows": len(values_document(outlook_id)["hours"])},
        issuer=rule.get("issuer", "BOOK-2 fixture"),
        synthetic=True,
    )


def _scratch():
    """The system temp dir, else an ignored repository path (a review sandbox may have no writable /tmp)."""
    try:
        return tempfile.TemporaryDirectory(prefix="book-vintages-")
    except OSError:
        fallback = ROOT / ".local" / "test-scratch"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix="book-vintages-", dir=fallback)


def files() -> dict:
    """``{relative name: bytes}`` of every fixture file, the records written by the real archive."""
    out = {}
    with _scratch() as scratch:
        archive = OutlookArchive(Path(scratch))
        for outlook_id in RULES:
            archive.issue(build_outlook(**outlook_fields(outlook_id)))
        for path in sorted(Path(scratch).rglob("*.json")):
            out[str(path.relative_to(scratch))] = path.read_bytes()
    for outlook_id in RULES:
        out[f"values/{outlook_id}.json"] = values_bytes(outlook_id)
    return out


def check() -> list:
    expected = files()
    problems = []
    for name, data in sorted(expected.items()):
        path = OUT / name
        if not path.is_file():
            problems.append(f"missing {name}")
        elif path.read_bytes() != data:
            problems.append(f"{name} differs from the builder")
    if OUT.is_dir():
        extra = sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()
                       and str(p.relative_to(OUT)) not in expected)
        problems += [f"unexpected {name}" for name in extra]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when a file differs")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        print("\n".join(problems) if problems else f"OK: {len(files())} vintage fixture files reproduce")
        return 1 if problems else 0
    written = files()
    shutil.rmtree(OUT, ignore_errors=True)
    for name, data in sorted(written.items()):
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"{name} {len(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
