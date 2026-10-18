"""The availability response record (OUT-2): its validator, its use on a band, its model card.

The record is written by ``scripts/price/event_study.py`` from two exports, each cited by
SHA-256: the forced outage records (``outages_forced.csv``, from ``scripts/price/event_study.sql``)
and the final hourly regional series (``lwap_final_hourly.csv``). It holds, per region and size
class, the pooled response of the final regional price to a forced outage: the median, p10 and
p90 of the per-event change against the same-hour baseline, per MW lost, with the count.

Basis, never mixed
==================
The level comes from the final hourly regional settlement series only. The real-time series is
used, if ever, only to check the timing of a response, never for a level; this record's runner
does not read it at all, and the record says so in :data:`BASIS`.

Small samples travel
====================
A cell with fewer events than the record's stated minimum is ``small_sample`` and labelled
``exploratory``. :func:`apply` refuses such a cell unless the caller passes
``allow_exploratory=True``, and then the label travels into the result.

Nothing here reads a file, calls a model or touches the network.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

KIND = "price-availability-response"
VERSION = "out-2.1"
BASIS = "final hourly regional settlement series; the real-time series was not read"
FINAL_SERIES = "lwap_final_hourly.csv"
OUTAGE_EXPORT = "outages_forced.csv"
NORMALIZATIONS = {
    "per_mw_lost": "PHP/MWh per MW of rated capacity lost",
    "per_share_of_demand": "PHP/MWh per unit of rated MW lost over mean regional demand",
}
#: what "MW lost" means (rework round 1, finding 4)
MW_LOST_BASIS = (
    "p_max, the rated capacity of each unit in the IEMOP unit list of 2026-09-11 "
    "(grid_ref.units), applied to every event from 2021 to 2026; a derated or part-loaded unit "
    "is overstated, so the response per MW is understated"
)
#: where the denominator comes from (orchestrator decision, rework round 1)
DEMAND_SOURCE = (
    "grid_curated.intervals en_requirement_mw, the energy market requirement of "
    "RTD_Regional_Summaries, hourly mean per region"
)
CARD_BASIS = ("It reads the final hourly regional settlement series. "
              "It never reads the real-time series.")
CARD_SYNTHETIC_LABEL = ("Synthetic fixture. Invented outages and invented prices. "
                        "A method demonstration, not a measurement.")
CARD_MEASURED_LABEL = "Measured on the snapshot exports, each cited by its digest."
LABEL_MEASURED = "measured"
LABEL_EXPLORATORY = "exploratory"
SYNTHETIC_LABEL = (
    "synthetic fixture: invented outages and invented prices; a method demonstration, "
    "not a measurement"
)
EXPECTATION = (
    "A multi-hour outage against a billing-month mean moves the mean by a small delta. "
    "The materiality line, not the mechanism, decides whether it reaches the board."
)
QUANTILES = ("p10", "median", "p90")
BAND_KEYS = ("p10", "p50", "p90")
CELL_FIELDS = (
    "region", "size_class", "mw_low", "mw_high", "count", "median", "p10", "p90",
    "small_sample", "min_events", "label", "units", "basis", "measured_hours",
)
RECORD_FIELDS = (
    "kind", "version", "label", "basis", "normalization", "units", "denominator",
    "mw_lost_basis", "inputs", "parameters", "counts", "cells", "limits", "timing_check",
    "expectation",
)
CARD_RECORD = "docs/work/desk-agent-and-book-2026-10-18/event-study.md"


class ResponseError(Exception):
    """A malformed record or cell, or a use the record does not allow."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --- canonical bytes --------------------------------------------------------


def record_text(record: Mapping) -> str:
    """Canonical JSON in the record's own key order, no trailing newline."""
    return json.dumps(record, sort_keys=False, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def record_digest(record: Mapping) -> str:
    return hashlib.sha256(record_text(record).encode("utf-8")).hexdigest()


# --- the validator ------------------------------------------------------------


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_cell(cell: Mapping, min_events: int | None = None) -> None:
    """Refuse a cell that is missing a field, mixes bases or hides a small sample."""
    if not isinstance(cell, Mapping):
        raise ResponseError("MALFORMED_CELL", "a cell is not an object")
    missing = [name for name in CELL_FIELDS if name not in cell]
    if missing:
        raise ResponseError("MALFORMED_CELL", f"no field {missing[0]}")
    if cell["basis"] != BASIS:
        raise ResponseError("WRONG_BASIS", str(cell["basis"]))
    if cell["units"] not in NORMALIZATIONS.values():
        raise ResponseError("MALFORMED_CELL", f"units {cell['units']!r}")
    count = cell["count"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ResponseError("MALFORMED_CELL", "count must be a positive integer")
    for name in QUANTILES:
        if not _number(cell[name]):
            raise ResponseError("MALFORMED_CELL", f"{name} is not a number")
    if not cell["p10"] <= cell["median"] <= cell["p90"]:
        raise ResponseError("MALFORMED_CELL", "p10 <= median <= p90 does not hold")
    if not isinstance(cell["small_sample"], bool):
        raise ResponseError("MALFORMED_CELL", "small_sample is not a boolean")
    expected_label = LABEL_EXPLORATORY if cell["small_sample"] else LABEL_MEASURED
    if cell["label"] != expected_label:
        raise ResponseError("LABEL_MISMATCH", f"{cell['label']!r} with small_sample "
                                              f"{cell['small_sample']}")
    own = cell["min_events"]
    if not isinstance(own, int) or isinstance(own, bool) or own < 1:
        raise ResponseError("MALFORMED_CELL", "min_events must be a positive integer")
    if min_events is not None and own != min_events:
        raise ResponseError("LABEL_MISMATCH", f"cell minimum {own} against record {min_events}")
    if cell["small_sample"] != (count < own):
        raise ResponseError("LABEL_MISMATCH", f"count {count} against minimum {own}")
    if not isinstance(cell["measured_hours"], int) or cell["measured_hours"] < 1:
        raise ResponseError("MALFORMED_CELL", "measured_hours must be a positive integer")


def validate(record: Mapping) -> Mapping:
    """Refuse a record that is not a well-formed response record; return it unchanged."""
    if not isinstance(record, Mapping):
        raise ResponseError("MALFORMED_RECORD", "not an object")
    missing = [name for name in RECORD_FIELDS if name not in record]
    if missing:
        raise ResponseError("MALFORMED_RECORD", f"no field {missing[0]}")
    if record["kind"] != KIND:
        raise ResponseError("NOT_A_RESPONSE_RECORD", str(record["kind"]))
    if record["version"] != VERSION:
        raise ResponseError("UNKNOWN_VERSION", str(record["version"]))
    if record["basis"] != BASIS:
        raise ResponseError("WRONG_BASIS", str(record["basis"]))
    if record["normalization"] not in NORMALIZATIONS:
        raise ResponseError("MALFORMED_RECORD", f"normalization {record['normalization']!r}")
    if record["units"] != NORMALIZATIONS[record["normalization"]]:
        raise ResponseError("MALFORMED_RECORD", "units do not match the normalization")
    inputs = record["inputs"]
    roles = {entry.get("role") for entry in inputs} if isinstance(inputs, list) else set()
    wanted = {"outages", "final_series"}
    if record["normalization"] == "per_share_of_demand":
        wanted = wanted | {"demand"}
    if roles != wanted or len(inputs) != len(wanted):
        raise ResponseError("MALFORMED_RECORD",
                            "inputs must be the outages, the final series and, for a demand "
                            "denominator, the demand export")
    for entry in inputs:
        for name in ("role", "path", "file", "rows", "sha256"):
            if name not in entry:
                raise ResponseError("MALFORMED_RECORD", f"input without {name}")
        if entry["role"] == "final_series" and "real" in entry["file"].lower():
            raise ResponseError("WRONG_BASIS", entry["file"])
    parameters = record["parameters"]
    min_events = parameters.get("min_events_per_cell") if isinstance(parameters, Mapping) else None
    if not isinstance(min_events, int) or min_events < 1:
        raise ResponseError("MALFORMED_RECORD", "parameters.min_events_per_cell missing")
    cells = record["cells"]
    if not isinstance(cells, list):
        raise ResponseError("MALFORMED_RECORD", "cells is not a list")
    seen = set()
    for cell in cells:
        validate_cell(cell, min_events)
        if cell["units"] != record["units"]:
            raise ResponseError("MALFORMED_RECORD", "a cell's units differ from the record's")
        key = (cell["region"], cell["size_class"])
        if key in seen:
            raise ResponseError("DUPLICATE_CELL", f"{key}")
        seen.add(key)
    return record


def find_cell(record: Mapping, region: str, mw: float) -> Mapping:
    """The record's cell for a region and an outage size; refused when none exists."""
    for cell in record["cells"]:
        high = cell["mw_high"]
        if cell["region"] == region and cell["mw_low"] <= mw and (high is None or mw < high):
            return cell
    raise ResponseError("NO_CELL", f"{region} {mw} MW")


# --- applying a cell to a band ------------------------------------------------------


def _band_values(band: Mapping | Sequence) -> tuple[float, float, float]:
    if isinstance(band, Mapping):
        try:
            values = tuple(band[key] for key in BAND_KEYS)
        except KeyError as error:
            raise ResponseError("MALFORMED_BAND", f"no {error.args[0]}") from error
    else:
        values = tuple(band)
    if len(values) != 3 or not all(_number(value) for value in values):
        raise ResponseError("MALFORMED_BAND", "a band is (p10, p50, p90)")
    if not values[0] <= values[1] <= values[2]:
        raise ResponseError("MALFORMED_BAND", "p10 <= p50 <= p90 does not hold")
    return values  # type: ignore[return-value]


def apply(
    band: Mapping | Sequence,
    response_cell: Mapping,
    outage_mw: float,
    hours: float,
    *,
    window_hours: float | None = None,
    demand_mw: float | None = None,
    allow_exploratory: bool = False,
) -> dict:
    """Shift a (p10, p50, p90) band by the response for an outage's stated duration.

    Each band quantile moves by the cell's matching quantile (p10 by p10, p50 by the median,
    p90 by p90) times the outage's MW lost (over ``demand_mw`` when the cell is normalized by
    regional demand). When ``window_hours`` is given the band is a mean over that window (a
    billing month has about 720 hours), so the shift is diluted by the share of the window the
    outage covers: ``min(hours, window_hours) / window_hours``. Without it the band is the band of
    the outage hours themselves. A duration past the cell's measured hours assumes the measured
    per-hour response persists; the result says by how many hours.
    """
    validate_cell(response_cell)
    if response_cell["small_sample"] and not allow_exploratory:
        raise ResponseError(
            "EXPLORATORY_CELL",
            f"{response_cell['region']} {response_cell['size_class']}: "
            f"{response_cell['count']} events; pass allow_exploratory=True and show the label",
        )
    if not _number(outage_mw) or outage_mw <= 0:
        raise ResponseError("MALFORMED_OUTAGE", "outage_mw must be positive")
    if not _number(hours) or hours <= 0:
        raise ResponseError("MALFORMED_OUTAGE", "hours must be positive")
    if window_hours is not None and (not _number(window_hours) or window_hours <= 0):
        raise ResponseError("MALFORMED_BAND", "window_hours must be positive")
    per_demand = response_cell["units"] == NORMALIZATIONS["per_share_of_demand"]
    if per_demand:
        if demand_mw is None or not _number(demand_mw) or demand_mw <= 0:
            raise ResponseError("DEMAND_REQUIRED", "the cell is normalized by regional demand")
        size = outage_mw / demand_mw
    else:
        size = float(outage_mw)
    share = 1.0 if window_hours is None else min(hours, window_hours) / window_hours
    before = _band_values(band)
    shift = tuple(response_cell[name] * size * share for name in QUANTILES)
    after = tuple(value + delta for value, delta in zip(before, shift))
    label = response_cell["label"]
    if response_cell["small_sample"]:
        label = (f"{LABEL_EXPLORATORY}: {response_cell['count']} events in "
                 f"{response_cell['region']} {response_cell['size_class']}, below the minimum")
    return {
        "band_before": dict(zip(BAND_KEYS, before)),
        "band_after": dict(zip(BAND_KEYS, after)),
        "shift": dict(zip(BAND_KEYS, shift)),
        "cell": {"region": response_cell["region"], "size_class": response_cell["size_class"],
                 "count": response_cell["count"]},
        "label": label,
        "small_sample": response_cell["small_sample"],
        "basis": BASIS,
        "units": response_cell["units"],
        "outage_mw": outage_mw,
        "demand_mw": demand_mw if per_demand else None,
        "hours": hours,
        "window_hours": window_hours,
        "window_share": share,
        "measured_hours": response_cell["measured_hours"],
        "hours_beyond_measured": max(0.0, float(hours) - response_cell["measured_hours"]),
    }


# --- the model card --------------------------------------------------------------


def _figure(label: str, value: object, figure: str) -> dict:
    if isinstance(value, float):
        text = f"{value:,.2f}"
    elif isinstance(value, int):
        text = f"{value:,}"
    else:
        text = str(value)
    return {"label": label, "value": text, "figure": figure, "record": CARD_RECORD}


def model_card(record: Mapping) -> dict:
    """The card the models page reads, from a validated record.

    The field names follow the four cards of ``src/grid/models.html`` (MODELS-1): ``id``,
    ``title`` (the ``h2``), ``status_word`` (``.md-status-word``) and ``status`` (the rest of
    that line, which never repeats the word), ``lines`` (``.md-line``), ``figures``
    (``data-figure``, ``data-record``, a label of three words or fewer) and ``as_of`` (the record
    paths). The board's request R4 asks MODELS for the contract; until it lands these are
    assumed. The card adds the five statements the brief names: ``method``, ``inputs``,
    ``sample``, ``spread`` and ``basis``, and the honest ``expectation``. Every string on the card
    keeps the plain-language rules: no semicolon, sentences under 20 words.
    """
    validate(record)
    synthetic = record["label"].startswith("synthetic")
    parameters = record["parameters"]
    cells = record["cells"]
    measured = [cell for cell in cells if not cell["small_sample"]]
    exploratory = [cell for cell in cells if cell["small_sample"]]
    events = sum(cell["count"] for cell in cells)
    per_demand = record["normalization"] == "per_share_of_demand"
    status = ("on a synthetic fixture, not on the snapshot." if synthetic
              else "on the snapshot exports.")
    method = (
        f"It takes each forced outage of {parameters['min_mw']:g} MW or more. "
        f"MW lost is the unit's rated capacity in the IEMOP list of 11 September 2026. "
        f"It reads the final regional price for the first {parameters['hours_after']} clock hours. "
        f"It compares each hour with the same hour on similar days nearby. "
        f"Those days share the weekday class and lie in the {parameters['baseline_weeks']} weeks "
        f"around that hour's week. "
        + ("It divides the change by the MW lost over the mean regional demand. "
           if per_demand else "It divides the change by the MW lost. ")
        + "It leaves out an outage that overlaps another in its region. "
        "It pools the results per region and size class."
    )
    inputs = [{"role": entry["role"], "file": entry["file"], "rows": entry["rows"],
               "sha256": entry["sha256"]} for entry in record["inputs"]]
    sample = {
        "events": events,
        "cells": len(cells),
        "measured_cells": len(measured),
        "exploratory_cells": len(exploratory),
        "min_events_per_cell": parameters["min_events_per_cell"],
    }
    spread = [{"region": cell["region"], "size_class": cell["size_class"], "count": cell["count"],
               "p10": cell["p10"], "median": cell["median"], "p90": cell["p90"],
               "label": cell["label"]} for cell in cells]
    lines = [
        "It reads the final hourly regional settlement series. It never reads the real-time series.",
        f"It counts {events} forced outages in {len(cells)} region and size groups.",
        f"A group with fewer than {parameters['min_events_per_cell']} outages is exploratory.",
        "A multi-hour outage moves a billing-month mean by a small amount.",
        "The materiality line decides whether that amount reaches the board.",
    ]
    if synthetic:
        lines.insert(0, "Every figure here comes from invented outages and invented prices.")
    figures = [
        _figure("Outages counted", events, "availability-events"),
        _figure("Measured groups", len(measured), "availability-measured-cells"),
        _figure("Exploratory groups", len(exploratory), "availability-exploratory-cells"),
        _figure("Hours after", parameters["hours_after"], "availability-hours-after"),
        _figure("Baseline weeks", parameters["baseline_weeks"], "availability-baseline-weeks"),
        _figure("Minimum size, MW", float(parameters["min_mw"]), "availability-min-mw"),
    ]
    return {
        "id": "availability",
        "title": "Availability response",
        "status_word": "Measured once",
        "status": status,
        "lines": lines,
        "figures": figures,
        "as_of": [CARD_RECORD],
        "label": CARD_SYNTHETIC_LABEL if synthetic else CARD_MEASURED_LABEL,
        "method": method,
        "inputs": inputs,
        "sample": sample,
        "spread": spread,
        "units": record["units"],
        "basis": CARD_BASIS,
        "expectation": EXPECTATION,
        "record_digest": record_digest(record),
    }


__all__ = [
    "BASIS",
    "CARD_BASIS",
    "CARD_MEASURED_LABEL",
    "CARD_RECORD",
    "CARD_SYNTHETIC_LABEL",
    "DEMAND_SOURCE",
    "CELL_FIELDS",
    "EXPECTATION",
    "FINAL_SERIES",
    "KIND",
    "LABEL_EXPLORATORY",
    "LABEL_MEASURED",
    "MW_LOST_BASIS",
    "NORMALIZATIONS",
    "OUTAGE_EXPORT",
    "RECORD_FIELDS",
    "ResponseError",
    "SYNTHETIC_LABEL",
    "VERSION",
    "apply",
    "find_cell",
    "model_card",
    "record_digest",
    "record_text",
    "validate",
    "validate_cell",
]
