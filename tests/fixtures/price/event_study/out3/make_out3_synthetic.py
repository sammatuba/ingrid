#!/usr/bin/env python3
"""Write the OUT-3 synthetic fixtures: known outages, demand before the cutoff, a response record.

Every unit (SYN_K*), MW figure, demand and response number here is invented. None comes from an
export. The response cells imitate the real run's shape (each spread straddles zero, one exploratory
cell, no cell for CVIS 300+ MW) with round invented numbers, so the arithmetic is easy to check by
hand (docs/work/outlook-archive/third-outlook.md, "Fixture loop"). Run from the repository root:

    /usr/bin/python3 tests/fixtures/price/event_study/out3/make_out3_synthetic.py

tests/test_price_availability.py rebuilds the same bytes and compares them with the committed files.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABEL = ("synthetic fixture: invented outages, invented demand and an invented response; a method "
         "demonstration, not a measurement")
KNOWN_HEADER = ("run,resource_name,region_code,status,outage_class,mw_lost,start_manila,end_manila,"
                "start_utc,end_utc,first_seen_manila,first_seen_utc,last_seen_manila,revision_no,n_revisions")
UNITS = "PHP/MWh per unit of rated MW lost over mean regional demand"
BASIS = "final hourly regional settlement series; the real-time series was not read"

#: (unit, region, class, MW, start, end, first seen, last seen): invented. A forced record known at
#: the cutoff for November is one in progress at the cutoff (first seen after its start) with a
#: stated end inside the window.
OUTAGES = (
    ("SYN_K01", "CLUZ", "forced", 350.0, "2026-10-10 06:00:00", "2026-10-26 06:00:00",
     "2026-10-10 06:20:00", "2026-10-14 23:55:00"),
    ("SYN_K02", "CVIS", "planned", 150.0, "2026-11-02 08:00:00", "2026-11-02 20:30:00",
     "2026-10-12 00:00:00", "2026-10-14 23:55:00"),
    ("SYN_K03", "CLUZ", "forced", 210.0, "2026-10-14 10:00:00", "2026-10-26 03:00:00",
     "2026-10-14 10:05:00", "2026-10-14 23:55:00"),
    ("SYN_K04", "CMIN", "forced", 120.0, "2026-10-13 00:00:00", "2026-10-26 12:00:00",
     "2026-10-13 00:30:00", "2026-10-14 23:55:00"),
    ("SYN_K05", "CVIS", "forced", 350.0, "2026-10-14 00:00:00", "2026-10-27 00:00:00",
     "2026-10-14 00:20:00", "2026-10-14 23:55:00"),
    ("SYN_K06", "CLUZ", "planned", 160.0, "2026-10-25 20:00:00", "2026-10-26 00:30:00",
     "2026-10-14 12:00:00", "2026-10-14 23:55:00"),
)
#: invented regional demand, MW: (weekday, weekend); the shares of the three regions are 0.7, 0.15
#: and 0.15 on every day, so the load-share weight is easy to check by hand
DEMAND = {"CLUZ": (7000.0, 5600.0), "CVIS": (1500.0, 1200.0), "CMIN": (1500.0, 1200.0)}
DEMAND_FIRST_DAY = date(2026, 9, 16)
DEMAND_LAST_DAY = date(2026, 10, 14)
#: rows after the cutoff (2026-10-15 00:00 Manila) with a value no proxy may ever read
AFTER_CUTOFF_HOURS = 6
AFTER_CUTOFF_MW = 99999.0

#: (region, size class, low, high, count, median, p10, p90): invented, each spread straddles zero
CELLS = (
    ("CLUZ", "150 to 300 MW", 150.0, 300.0, 15, 20000.0, -80000.0, 120000.0),
    ("CLUZ", "300+ MW", 300.0, None, 14, -8000.0, -36000.0, 54000.0),
    ("CVIS", "150 to 300 MW", 150.0, 300.0, 11, 500.0, -50000.0, 15000.0),
    ("CMIN", "50 to 150 MW", 50.0, 150.0, 4, 10000.0, -8000.0, 200000.0),
)


def utc(text):
    return (datetime.fromisoformat(text) - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")


def known_outages_text():
    lines = [KNOWN_HEADER]
    for unit, region, kind, mw, start, end, first, last in OUTAGES:
        lines.append(",".join([
            "WAP", unit, region, "OUT", kind, f"{mw:.1f}", start, end, utc(start), utc(end), first,
            utc(first), last, "1", "1"]))
    return "\n".join(lines) + "\n"


def demand_text():
    lines = ["region_name,hour_start,n5,demand_mw_mean"]
    for region in ("CLUZ", "CVIS", "CMIN"):
        day = DEMAND_FIRST_DAY
        while day <= DEMAND_LAST_DAY:
            value = DEMAND[region][1 if day.weekday() >= 5 else 0]
            for hour in range(24):
                lines.append(f"{region},{day.isoformat()} {hour:02d}:00:00,12,{value:.3f}")
            day += timedelta(days=1)
        for hour in range(AFTER_CUTOFF_HOURS):
            lines.append(f"{region},2026-10-15 {hour:02d}:00:00,12,{AFTER_CUTOFF_MW:.3f}")
    return "\n".join(lines) + "\n"


def response_record():
    cells = []
    for region, size, low, high, count, median, p10, p90 in CELLS:
        small = count < 10
        cells.append({"region": region, "size_class": size, "mw_low": low, "mw_high": high, "count": count,
                      "median": median, "p10": p10, "p90": p90, "small_sample": small, "min_events": 10,
                      "label": "exploratory" if small else "measured", "units": UNITS, "basis": BASIS,
                      "measured_hours": 6})
    return {
        "kind": "price-availability-response",
        "version": "out-2.1",
        "label": LABEL,
        "basis": BASIS,
        "normalization": "per_share_of_demand",
        "units": UNITS,
        "denominator": "invented: the fixture states no measured denominator",
        "mw_lost_basis": "invented rated MW of invented units",
        "inputs": [
            {"role": "outages", "path": "tests/fixtures/price/event_study/outages_forced-synthetic.csv",
             "file": "outages_forced-synthetic.csv", "rows": 25,
             "sha256": "5f89a0e425fb8df4afc18cf59501b14132abdec2c04c9c87ed750e9ab057577a"},
            {"role": "final_series", "path": "tests/fixtures/price/event_study/lwap_final_hourly-synthetic.csv",
             "file": "lwap_final_hourly-synthetic.csv", "rows": 8640,
             "sha256": "c6dcc38c11fd42336e0f640421723f9e095696a719e0f62fbc8c41ab11596707"},
            {"role": "demand", "path": "tests/fixtures/price/event_study/demand_hourly-synthetic.csv",
             "file": "demand_hourly-synthetic.csv", "rows": 6480,
             "sha256": "d75aa1195923fcaca3031c3416fea9f21572b381e7d62561bd82cc5b2c0b1ecf"},
        ],
        "parameters": {"min_mw": 50.0, "hours_after": 6, "baseline_weeks": 4, "min_events_per_cell": 10,
                       "size_edges": [50.0, 150.0, 300.0]},
        "counts": {"events_read": 44, "events_used": 44, "events_excluded": {}},
        "cells": cells,
        "limits": {"note": "invented cells; no limits measured"},
        "timing_check": "not run: invented cells",
        "expectation": ("A multi-hour outage against a billing-month mean moves the mean by a small delta. "
                        "The materiality line, not the mechanism, decides whether it reaches the board."),
    }


def response_text():
    return json.dumps(response_record(), indent=1) + "\n"


FILES = {
    "known_outages-synthetic.csv": known_outages_text,
    "demand_hourly-synthetic.csv": demand_text,
    "response-synthetic.json": response_text,
}


def label_text():
    return json.dumps({"label": LABEL, "written_by": "tests/fixtures/price/event_study/out3/make_out3_synthetic.py",
                       "files": sorted(FILES)}, indent=1) + "\n"


def main():
    for name, text in FILES.items():
        (HERE / name).write_text(text(), encoding="utf-8")
    (HERE / "synthetic-label.json").write_text(label_text(), encoding="utf-8")


if __name__ == "__main__":
    main()
