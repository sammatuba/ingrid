#!/usr/bin/env python3
"""Write the OUT-2 synthetic fixtures: invented outages and an invented final price series.

Every number here is invented for the test. Nothing is read from an export. The price series
has the exact header of the PRICE-1 regional export so the real reader loads it, and the
outage file has the exact header of ``scripts/price/event_study.sql``. The prices carry a
known response: during every outage hour the region's price rises by ``SLOPE[region]`` PHP/MWh
per MW lost, so the study must recover about that slope. ``test_price_response`` checks that
this script reproduces the committed bytes.

    /usr/bin/python3 tests/fixtures/price/event_study/make_synthetic.py
"""
from __future__ import annotations

import csv
import io
import math
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIES = HERE / "lwap_final_hourly-synthetic.csv"
OUTAGES = HERE / "outages_forced-synthetic.csv"
DEMAND = HERE / "demand_hourly-synthetic.csv"
REALTIME_NAMED = HERE / "rtd_regional_prices-realtime-synthetic.csv"
REALTIME_SHAPED = HERE / "prices_interval_shape-synthetic.csv"

FIRST_HOUR = datetime(2026, 1, 26)          # billing month 2026-02 opens
LAST_DAY = datetime(2026, 4, 25)            # billing month 2026-04 (administered) closes
REGIONS = ("CLUZ", "CVIS", "CMIN", "SYSTEM")
BASE = {"CLUZ": 5000.0, "CVIS": 6000.0, "CMIN": 4500.0, "SYSTEM": 5200.0}
WEEKEND_OFFSET = -400.0
#: the invented response, PHP/MWh per MW lost, per region
SLOPE = {"CLUZ": 2.0, "CVIS": 8.0, "CMIN": 5.0}
#: the invented regional demand, MW, constant: a response per MW over demand is SLOPE x DEMAND
DEMAND_MW = {"CLUZ": 10000.0, "CVIS": 2000.0, "CMIN": 2500.0}

# (region, unit, MW lost, start, hours, minutes after start first seen)
EVENTS = (
    # CLUZ, 300+ MW: twelve events, a measured cell
    ("CLUZ", "SYN_L01", 420.0, "2026-02-03 09:20:00", 8, 15),
    ("CLUZ", "SYN_L02", 350.0, "2026-02-07 14:00:00", 6, 5),
    ("CLUZ", "SYN_L03", 500.0, "2026-02-11 02:45:00", 10, 40),
    ("CLUZ", "SYN_L04", 310.0, "2026-02-15 18:10:00", 7, 20),
    ("CLUZ", "SYN_L05", 600.0, "2026-02-19 11:00:00", 9, 10),
    ("CLUZ", "SYN_L06", 450.0, "2026-02-23 07:30:00", 6, 30),
    ("CLUZ", "SYN_L07", 380.0, "2026-02-27 20:05:00", 8, 25),
    ("CLUZ", "SYN_L08", 520.0, "2026-03-03 13:15:00", 7, 5),
    ("CLUZ", "SYN_L09", 330.0, "2026-03-07 04:00:00", 12, 90),
    ("CLUZ", "SYN_L10", 410.0, "2026-03-11 16:50:00", 6, 15),
    ("CLUZ", "SYN_L11", 470.0, "2026-03-15 10:00:00", 8, 35),
    ("CLUZ", "SYN_L12", 360.0, "2026-03-19 22:40:00", 9, 20),
    # CVIS, 150 to 300 MW: four events, exploratory
    ("CVIS", "SYN_V01", 160.0, "2026-02-09 08:00:00", 6, 10),
    ("CVIS", "SYN_V02", 220.0, "2026-02-21 15:30:00", 7, 25),
    ("CVIS", "SYN_V03", 290.0, "2026-03-05 03:10:00", 8, 150),
    ("CVIS", "SYN_V04", 180.0, "2026-03-17 12:00:00", 6, 15),
    # CMIN, 50 to 150 MW: three events, exploratory
    ("CMIN", "SYN_M01", 80.0, "2026-02-13 10:00:00", 6, 20),
    ("CMIN", "SYN_M02", 120.0, "2026-02-28 17:20:00", 8, 10),
    ("CMIN", "SYN_M03", 60.0, "2026-03-13 06:00:00", 7, 30),
    # left out, one per reason
    ("CMIN", "SYN_M04", 45.0, "2026-03-01 09:00:00", 6, 15),     # below the minimum size
    ("CLUZ", "SYN_L13", 400.0, "2026-03-09 09:10:00", 0.5, 5),   # no whole clock hour
    ("CVIS", "SYN_V05", 200.0, "2026-04-08 10:00:00", 6, 10),    # administered month 2026-04
    ("CLUZ", "SYN_L14", 400.0, "2026-01-12 10:00:00", 6, 10),    # before the series starts
    # an overlapping pair (rework round 1): each would take the other's price change, so both
    # are left out as overlapping_outage, and the CLUZ cell keeps the invented slope
    ("CLUZ", "SYN_L15", 350.0, "2026-03-23 10:00:00", 6, 10),
    ("CLUZ", "SYN_L16", 350.0, "2026-03-23 12:00:00", 6, 10),
)
UTC = timedelta(hours=8)
STAMP = "%Y-%m-%d %H:%M:%S"


def noise(seed: int) -> float:
    """A deterministic value in [-50, 50): an integer hash, no random module."""
    value = (seed * 2654435761 + 97531) % 4294967296
    return (value / 4294967296.0) * 100.0 - 50.0


def events():
    for region, unit, mw, start, hours, seen_after in EVENTS:
        begin = datetime.strptime(start, STAMP)
        end = begin + timedelta(hours=hours)
        seen = begin + timedelta(minutes=seen_after)
        yield region, unit, mw, begin, end, seen


def bump(region: str, hour: datetime) -> float:
    if region == "SYSTEM":
        return 0.0
    total = 0.0
    for event_region, _, mw, begin, end, _ in events():
        if event_region == region and hour < end and hour + timedelta(hours=1) > begin:
            total += SLOPE[region] * mw
    return total


def billing_month(hour: datetime) -> tuple[int, int]:
    shifted = hour.date() - timedelta(days=25)
    year, month = shifted.year, shifted.month + 1
    return (year + 1, 1) if month == 13 else (year, month)


def series_text() -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("byear", "bmonth", "region_name", "hour_start", "n5", "lwap_mean",
                     "lwap_min", "lwap_max"))
    last = LAST_DAY + timedelta(hours=23)
    for index, region in enumerate(REGIONS):
        hour, step = FIRST_HOUR, 0
        while hour <= last:
            shape = 600.0 * math.sin((hour.hour - 6) / 24.0 * 2.0 * math.pi)
            weekend = WEEKEND_OFFSET if hour.weekday() >= 5 else 0.0
            mean = BASE[region] + shape + weekend + noise(step * 7 + index) + bump(region, hour)
            year, month = billing_month(hour)
            writer.writerow((year, month, region, hour.strftime(STAMP), 12, f"{mean:.2f}",
                             f"{mean - 300.0:.2f}", f"{mean + 300.0:.2f}"))
            hour += timedelta(hours=1)
            step += 1
    return out.getvalue()


def outages_text() -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("run", "resource_name", "region_code", "status", "outage_class", "mw_lost",
                     "start_manila", "end_manila", "start_utc", "end_utc", "first_seen_manila",
                     "first_seen_utc", "first_seen_any_run_manila", "lead_hours",
                     "duration_hours", "n_revisions"))
    for region, unit, mw, begin, end, seen in sorted(events(), key=lambda e: (e[0], e[3], e[1])):
        lead = (begin - seen).total_seconds() / 3600.0
        duration = (end - begin).total_seconds() / 3600.0
        writer.writerow(("RTD", unit, region, "OUT", "forced", f"{mw:.1f}", begin.strftime(STAMP),
                         end.strftime(STAMP), (begin - UTC).strftime(STAMP),
                         (end - UTC).strftime(STAMP), seen.strftime(STAMP),
                         (seen - UTC).strftime(STAMP), seen.strftime(STAMP), f"{lead:.3f}",
                         f"{duration:.3f}", 1))
    return out.getvalue()


def demand_text() -> str:
    """The demand export's shape: region, hour, interval count and mean demand; no price."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("region_name", "hour_start", "n5", "demand_mw_mean"))
    last = LAST_DAY + timedelta(hours=23)
    for region in ("CLUZ", "CVIS", "CMIN"):
        hour = FIRST_HOUR
        while hour <= last:
            writer.writerow((region, hour.strftime(STAMP), 12, f"{DEMAND_MW[region]:.3f}"))
            hour += timedelta(hours=1)
    return out.getvalue()


def realtime_named_text() -> str:
    """A file with the final header but a real-time name: refused by its name."""
    return ("byear,bmonth,region_name,hour_start,n5,lwap_mean,lwap_min,lwap_max\n"
            "2026,2,CLUZ,2026-01-26 00:00:00,12,1.00,0.00,2.00\n")


def realtime_shaped_text() -> str:
    """The five-minute real-time interval shape: refused by its header."""
    return ("interval_end,region_name,lmp,lmp_smp,lmp_loss,lmp_congestion\n"
            "2026-01-26 00:05:00,CLUZ,1.00,1.00,0.00,0.00\n")


FILES = {
    SERIES: series_text,
    OUTAGES: outages_text,
    DEMAND: demand_text,
    REALTIME_NAMED: realtime_named_text,
    REALTIME_SHAPED: realtime_shaped_text,
}


def main() -> int:
    for path, make in FILES.items():
        path.write_text(make(), encoding="utf-8")
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
