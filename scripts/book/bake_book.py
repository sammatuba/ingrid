#!/usr/bin/env python3
"""Build the two files the book page reads: ``book/index.json`` and ``book/exposure.json`` (BOOK-3).

    /usr/bin/python3 scripts/book/bake_book.py --out <dir>     # write <dir>/book/index.json and exposure.json
    /usr/bin/python3 scripts/book/bake_book.py --check         # compare with tests/fixtures/grid/book/bake

Inputs: the synthetic book (``tests/fixtures/book/book-v1.json``, BOOK-1) and the synthetic outlook
vintages (``tests/fixtures/book/vintages``, built by ``scripts/book/vintages.py``). Every figure goes
through the real modules: :func:`src.book.exposure.exposure` for the uncovered MWh and
:func:`src.book.impact.build_impact` for the impact band. A band is read only through
:func:`src.book.impact.load_vintage`, which reads the archive (BOOK-2 review, note C).

The page does no arithmetic. So every figure it shows is in these files, and so are the two things a
page would otherwise compute: the shade step of each heat cell and the clock-hour runs of each
contract. Both follow a rule stated in the file.

``book/index.json`` holds the book record as BOOK-1 sealed it, unchanged, and the contract hour runs.
``book/exposure.json`` holds, in this order: the materiality block, the window and the cutoff, the
vintage chosen for each region, the heat steps, the exposure record of the whole book for the day, and
one impact record per region. The impact record's ``content_digest`` is the record id the page shows.
The exposure record has no digest of its own, so its figures cite the book record and the cutoff.

Deterministic: the same inputs give the same bytes. Stdlib only, no network, no clock. The real bake
wiring (``scripts/grid/build_data.py``) belongs to DOCK-5, not to this script.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.book import impact as im  # noqa: E402
from src.book.exposure import FIXTURE as BOOK_FIXTURE, Window, exposure, load_book  # noqa: E402
from src.outlook.records import OutlookArchive  # noqa: E402
from src.price.impact import DEFAULT_MATERIALITY  # noqa: E402

KIND = "BookPage"
INDEX_KIND = "BookPageIndex"
VERSION = "book-page-1"
VINTAGES = ROOT / "tests" / "fixtures" / "book" / "vintages"
FIXTURE_OUT = ROOT / "tests" / "fixtures" / "grid" / "book" / "bake"
NAMES = ("book/index.json", "book/exposure.json")
#: The question the page answers: the whole book over one local day, at one date cutoff.
DAY = date(2026, 10, 19)
CUTOFF = "2026-10-18"
SHADES = 4

#: The rules the files state. They follow the site's plain-language rules: short active sentences,
#: no semicolons, no banned words. The test module checks them.
SELECTION_RULE = (
    "The data build picks one vintage per region. It takes the newest vintage of that region issued at "
    "or before the cutoff. A region with none takes the newest system vintage."
)
HEAT_RULE = (
    "Shade 0 holds no uncovered MWh. Shades 1 to 4 split the day's largest cell into four equal steps. "
    "A cell takes the first step whose edge reaches its value."
)
HOURS_RULE = (
    "Each run lists the first and the last clock hour of a block of hours the contract covers."
)


class BakeError(ValueError):
    """A refused build; ``code`` is stable."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)


def hour_runs(hours: list[int]) -> list[list[int]]:
    """``[0, 1, 2, 22, 23]`` to ``[[0, 2], [22, 23]]``: first and last clock hour of each run."""
    runs: list[list[int]] = []
    for hour in hours:
        if runs and hour == runs[-1][1] + 1:
            runs[-1][1] = hour
        else:
            runs.append([hour, hour])
    return runs


def index_record(book: dict) -> dict:
    return {
        "kind": INDEX_KIND,
        "version": VERSION,
        "synthetic": True,
        "label": book["label"],
        "book": book,
        "contract_hours": {"rule": HOURS_RULE,
                           "runs": {c["id"]: hour_runs(c["hours"]) for c in book["contracts"]}},
    }


def archive_bands(archive_root) -> list:
    """Every vintage of the archive, each tied through :func:`load_vintage` by its record id."""
    archive = OutlookArchive(archive_root)
    bands = []
    for outlook_id in archive.issue_ids():
        digest = archive.outlook(outlook_id)["content_digest"]
        bands.append(im.load_vintage(archive_root, outlook_id, digest))
    return bands


def _known_at_cutoff(band, cutoff) -> bool:
    try:
        im.as_of_block(band, cutoff)
    except im.BookImpactError as error:
        if error.code == "VINTAGE_AFTER_CUTOFF":
            return False
        raise
    return True


def choose(bands: list, region_code: str, cutoff):
    """The newest vintage of the region known at the cutoff, else the newest system one, else None."""
    for series in (region_code, im.SYSTEM):
        known = [b for b in bands if b.series == series and _known_at_cutoff(b, cutoff)]
        if known:
            newest = max(b.issued_at for b in known)
            chosen = [b for b in known if b.issued_at == newest]
            if len(chosen) > 1:
                raise BakeError("VINTAGE_TIE", f"{region_code}: {', '.join(b.outlook_id for b in chosen)}")
            return chosen[0], [b.outlook_id for b in known]
    return None, []


def heat_block(record: dict) -> dict:
    """The shade step of every exposure row, by the stated rule, and the edges it used."""
    largest = max(row["uncovered_mwh"] for row in record["rows"])
    edges = [round(largest * step / SHADES, 3) for step in range(1, SHADES + 1)]
    edges[-1] = largest

    def shade(value: float) -> int:
        if value <= 0:
            return 0
        return next(step for step, edge in enumerate(edges, start=1) if value <= edge)

    nodes = list(dict.fromkeys(row["node_id"] for row in record["rows"]))
    rows = []
    for node_id in nodes:
        cells = [row for row in record["rows"] if row["node_id"] == node_id]
        rows.append({"node_id": node_id, "account_id": cells[0]["account_id"], "region": cells[0]["region"],
                     "hours": [row["hour_start"] for row in cells],
                     "shades": [shade(row["uncovered_mwh"]) for row in cells]})
    return {"rule": HEAT_RULE, "largest_mwh": largest, "edges_mwh": edges, "rows": rows,
            "synthetic": True, "label": record["label"]}


def exposure_page(book: dict, archive_root=VINTAGES, day: date = DAY, cutoff: str = CUTOFF,
                  policy=DEFAULT_MATERIALITY) -> dict:
    window = Window(day, 0, 24)
    record = exposure(book, window, cutoff)
    bands = archive_bands(archive_root)
    selection, impacts = [], []
    for region in book["regions"]:
        band, considered = choose(bands, region["code"], cutoff)
        entry = {"region": region["name"], "region_code": region["code"], "considered": considered}
        if band is None:
            entry.update({"outlook_id": None, "impact_record_id": None})
        else:
            impact = im.build_impact(book, band, window, cutoff, policy, region=region["name"])
            impacts.append(impact)
            entry.update({"outlook_id": band.outlook_id, "outlook_digest": band.outlook_digest,
                          "series": band.series, "issued_at": band.issued_at,
                          "impact_record_id": impact["content_digest"]})
        selection.append(entry)
    return {
        "materiality": im.materiality_block(policy),
        "kind": KIND,
        "version": VERSION,
        "synthetic": True,
        "label": book["label"],
        "book": record["book"],
        "window": record["window"],
        "cutoff": record["cutoff"],
        "selection": {"rule": SELECTION_RULE, "regions": selection},
        "heat": heat_block(record),
        "exposure": record,
        "impacts": impacts,
    }


def text(record: dict) -> bytes:
    """Compact JSON in the record's own key order, so the materiality block stays first."""
    return (json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def files(book_path=BOOK_FIXTURE, archive_root=VINTAGES) -> dict:
    """``{published name: bytes}`` of the two files, under ``book/``."""
    book = load_book(book_path)
    return {"book/index.json": text(index_record(book)),
            "book/exposure.json": text(exposure_page(book, archive_root))}


def write(out: Path, built: dict) -> None:
    for name, data in built.items():
        path = Path(out) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def check(out: Path = FIXTURE_OUT) -> list:
    built = files()
    problems = []
    for name, data in built.items():
        path = Path(out) / name
        if not path.is_file():
            problems.append(f"missing {name}")
        elif path.read_bytes() != data:
            problems.append(f"{name} differs from the builder")
    folder = Path(out) / "book"
    if folder.is_dir():
        extra = sorted(f"book/{p.name}" for p in folder.iterdir() if f"book/{p.name}" not in built)
        problems += [f"unexpected {name}" for name in extra]
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path, help="the directory to write book/index.json and book/exposure.json into")
    group.add_argument("--check", action="store_true", help="compare with the committed outputs, write nothing")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        print("\n".join(problems) if problems else f"OK: {len(NAMES)} book page files reproduce")
        return 1 if problems else 0
    built = files()
    write(args.out, built)
    for name, data in built.items():
        print(f"{name} {len(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
