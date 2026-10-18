"""IMPACT-1: the synthetic portfolio against the outlook price band and the contract price.

The chain this module closes: an outlook's price band meets the portfolio's
uncovered volume and becomes an impact in pesos; the movement of that impact
between outlooks is compared with a stated materiality line; only a change at or
above the line reaches the board
([problem and thesis](../../docs/work/thesis-challenge-2026-10-16/problem-and-thesis.md)).

Method, in one paragraph
========================
For one de-identified load node, one horizon and one baseline of the PRICE-2
scorecard: every scored market origin of that node's series carries a price band
``(p10, p50, p90)`` — the three levels whose pinball losses the PRICE-2 record
reports. The uncovered volume of a window is the synthetic portfolio's 24-hour
profile read at each window hour's clock hour, and the impact of one hour is
``uncovered MWh at that hour × (band price − contract price)``. A horizon's
impact band is the sum of those products over the window's hours: it is a band,
not a single number, because the outlook prices the window as a band. The change
between two consecutive scored origins is material when the absolute change of
its mid band (p50) is at or above the stated line.

The band is the PRICE-2 scorecard's own
=======================================
The record keeps the pinball losses of its three quantiles, not their levels, so
the levels are taken from the code path that produced the record: the caller
re-runs :func:`src.price.scorecard.build_scorecard` on the same exported bytes
with a :class:`~src.price.scorecard.ScoredBand` sink, and refuses
(``SCORECARD_NOT_REPRODUCED``) unless the rebuilt record's digest equals the
SHA-256 of the scorecard file it was handed. The bands are therefore the record's
bands, proved by the record's own bytes, and no level is inferred or fitted.

The materiality line is stated before any change is scored
==========================================================
:data:`MATERIALITY_THRESHOLD_PHP` and :data:`DEFAULT_MATERIALITY` exist before
any input is read. :func:`build_impact_record` requires a
:class:`MaterialityPolicy` and has no default, so no run can classify a change
without declaring the line first; the record's first block after its identity is
the ``materiality`` block, written ahead of every impact value; and the runner
prints the line before it opens an input. The line is a stated policy of this
method demonstration: it is not measured from the changes it classifies, and it
is not a business limit.

Synthetic, and never a business number
======================================
The portfolio is synthetic (owner 2026-10-16, ``portfolio-synthetic.json``):
invented volumes and contract prices, and the node aliases ``N01`` to ``N12``.
Every peso figure this module computes is a method demonstration on that
synthetic position and is labelled as one in the record and in the runner's
output; none of them is a business number. The record carries portfolio volumes
and contract prices, so it lives under the ignored ``.local/`` only: the runner
refuses to write a record into the repository tree.

The data label is composed, never a constant
============================================
The record's ``label`` is :func:`demonstration_label` of the inputs
:func:`src.price.series.verify_inputs` checked in the run: the fixed synthetic
statement plus every input file by name, its data-row count and the first eight
hex digits of the digest the run verified. The exports under ``.local/price`` are
regenerated in place (step D of
``docs/work/data-foundation/refresh-brief-2026-10-16.md``), so a fixed dataset
description would go stale the first time the bytes changed; the run that reads
the files is the one that labels them, and two runs over different bytes compose
two different labels.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .baselines import HORIZONS, window_for
from .scorecard import AP, MARKET, ScoredBand, metrics_from
from .series import HOURS_PER_DAY, digest_file

KIND = "price-portfolio-impact"
VERSION = "impact-1.0"

#: The materiality line, in Philippine pesos, stated before any change is scored.
#: A change of one node's horizon impact at or above this line is material. The
#: value is a policy of this method demonstration, chosen so that the line sits
#: between the day horizon's ordinary origin-to-origin movement and the week and
#: month horizons'; the owner's real line has not been given. It is never
#: measured from the changes it classifies.
MATERIALITY_THRESHOLD_PHP = 1_000_000.0

#: How a change is compared with the line: at or above it is material.
MATERIALITY_COMPARATOR = "at_or_above"

MATERIALITY_RULE = (
    "the change of one (node, horizon, baseline) impact is the mid band (p50) of "
    "one scored origin minus the mid band of the previous scored origin, in pesos; "
    "a change is material when its absolute value is at or above the threshold; "
    "the threshold is a stated policy of this method demonstration, not a measured "
    "quantity and not a business limit"
)

MATERIALITY_STATEMENT = (
    "the materiality threshold is stated before any change is scored: it is the "
    "module constant MATERIALITY_THRESHOLD_PHP, it is a required argument of the "
    "scoring call, and the record states it ahead of every impact value"
)

#: The fixed half of the demonstration label: what the record is, independent of
#: which files the run read. The data half is composed by
#: :func:`demonstration_label` from the inputs the run verified, so the label
#: describes the bytes actually read rather than a fixed dataset description.
SYNTHETIC_STATEMENT = (
    "method demonstration on the synthetic portfolio (invented volumes and contract "
    "prices, node aliases only, owner 2026-10-16); every figure here is a method "
    "demonstration, never a business number"
)


def demonstration_label(inputs: Iterable[Mapping[str, object]]) -> str:
    """The data label: the fixed statement plus every input the run verified.

    Each input entry is one :func:`src.price.series.verify_inputs` report row,
    which carries the file's name, the SHA-256 the run checked and the file's
    data-row count; the label names the file, its row count and the first eight
    hex digits of that digest. Entries without a row count (the scorecard, the
    portfolio) are not described as exports. Two runs over different bytes, or
    over different files, therefore compose two different labels, and a run that
    verifies no input says exactly that instead of naming a dataset.
    """
    described = []
    for entry in inputs:
        name = entry.get("file")
        digest = entry.get("sha256")
        rows = entry.get("rows")
        if not isinstance(name, str) or not isinstance(digest, str):
            continue
        if isinstance(rows, bool) or not isinstance(rows, int):
            continue
        described.append(f"{name} {rows} rows sha256 {digest[:8]}")
    if not described:
        return f"{SYNTHETIC_STATEMENT}; no exported input verified in this run"
    return (f"{SYNTHETIC_STATEMENT}; read from the inputs this run verified: "
            + ", ".join(described))


METHOD_IMPACT = (
    "impact of one hour = uncovered MWh at that hour's clock hour × (band price − "
    "contract price); a horizon's impact band is the sum over the window's hours"
)

METHOD_BAND = (
    "the band is the (p10, p50, p90) triple the PRICE-2 scorecard reports for one "
    "scored origin, taken as levels from the scorecard's own code path and proved "
    "against its record by digest"
)

METHOD_PROFILE = (
    "the synthetic portfolio carries one 24-hour profile per node, read at each "
    "window hour's clock hour and repeated over the window's days"
)

#: Node aliases are the only node identifiers allowed near this record: the
#: synthetic file's own aliases, never a company load-node code.
ALIAS_PATTERN = re.compile(r"N\d{2}\Z")


class ImpactError(Exception):
    """A refused input, an unproved band or a refused output path."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# --- the materiality line -------------------------------------------------


@dataclass(frozen=True)
class MaterialityPolicy:
    """The stated line a change has to reach, and the direction of the comparison.

    Built from constants, never from scored changes: :func:`build_impact_record`
    requires one of these, so a run cannot classify a change before the line has
    been declared, and no statistic of the impacts can become the line.
    """

    threshold_php: float = MATERIALITY_THRESHOLD_PHP
    comparator: str = MATERIALITY_COMPARATOR

    def __post_init__(self) -> None:
        if isinstance(self.threshold_php, bool) or not isinstance(self.threshold_php, (int, float)):
            raise ImpactError("THRESHOLD_NOT_A_NUMBER", repr(self.threshold_php))
        if not self.threshold_php > 0:
            raise ImpactError("THRESHOLD_NOT_POSITIVE", repr(self.threshold_php))
        if self.comparator not in ("at_or_above", "above"):
            raise ImpactError("UNKNOWN_COMPARATOR", self.comparator)

    def is_material(self, change_php: float) -> bool:
        """Whether one signed change reaches the line."""
        if self.comparator == "at_or_above":
            return abs(change_php) >= self.threshold_php
        return abs(change_php) > self.threshold_php

    def to_dict(self) -> dict:
        return {
            "threshold_php": self.threshold_php,
            "comparator": self.comparator,
            "rule": MATERIALITY_RULE,
            "statement": MATERIALITY_STATEMENT,
            "basis": (
                "a stated policy of this method demonstration; the owner's materiality "
                "line has not been given, so this value is a demonstration input and "
                "never a business limit"
            ),
        }


DEFAULT_MATERIALITY = MaterialityPolicy()


# --- the synthetic portfolio ----------------------------------------------


@dataclass(frozen=True)
class NodePosition:
    """One synthetic load node: its alias, region, contract price and hourly profile."""

    node: str
    region: str
    contract_price_php_mwh: float
    uncovered_mwh_by_hour: tuple[float, ...]

    def uncovered_mwh(self, hours: Iterable) -> float:
        """The uncovered volume of a window: the profile read at each hour's clock hour."""
        return sum(self.uncovered_mwh_by_hour[hour.hour] for hour in hours)

    def impact_php(self, hours: Iterable, band_php_mwh: float) -> float:
        """One band price against the window: the per-hour product, summed.

        Negative where the band sits below the contract price: an uncovered buyer
        pays less than the contract for that volume, which is a gain on the
        position, and the sign is kept.
        """
        return sum(self.uncovered_mwh_by_hour[hour.hour] * (band_php_mwh - self.contract_price_php_mwh)
                   for hour in hours)


def _number(value: object, code: str, detail: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ImpactError(code, detail)
    return float(value)


def load_portfolio(path: str | Path) -> tuple[NodePosition, ...]:
    """Read the synthetic portfolio, refusing anything not labelled synthetic.

    The file is the only place a portfolio volume or a contract price lives; a
    missing ``synthetic: true`` (top level and per node), a node key that is not
    an alias, a profile that is not 24 hours, a negative volume or a
    non-positive contract price all refuse the run rather than being repaired.
    """
    path = Path(path)
    if not path.exists():
        raise ImpactError("MISSING_PORTFOLIO", str(path))
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise ImpactError("MALFORMED_PORTFOLIO", f"{path.name}: {error}") from error
    if not isinstance(loaded, dict) or loaded.get("synthetic") is not True:
        raise ImpactError("NOT_SYNTHETIC", path.name)
    entries = loaded.get("portfolio")
    if not isinstance(entries, list) or not entries:
        raise ImpactError("MALFORMED_PORTFOLIO", f"{path.name}: no portfolio list")
    positions: list[NodePosition] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ImpactError("MALFORMED_PORTFOLIO", "an entry is not an object")
        node = entry.get("node")
        if not isinstance(node, str) or not ALIAS_PATTERN.match(node):
            raise ImpactError("NODE_NOT_AN_ALIAS", repr(node))
        if node in seen:
            raise ImpactError("DUPLICATE_NODE", node)
        seen.add(node)
        if entry.get("synthetic") is not True:
            raise ImpactError("NOT_SYNTHETIC", f"{path.name}: node {node}")
        region = entry.get("region")
        if not isinstance(region, str) or not region.strip():
            raise ImpactError("MALFORMED_PORTFOLIO", f"{node}: no region")
        price = _number(entry.get("contract_price_php_mwh"), "CONTRACT_PRICE", node)
        if not price > 0:
            raise ImpactError("CONTRACT_PRICE", f"{node}: {price}")
        profile = entry.get("uncovered_mwh_by_hour")
        if not isinstance(profile, list) or len(profile) != HOURS_PER_DAY:
            raise ImpactError("PROFILE_LENGTH", f"{node}: {len(profile) if isinstance(profile, list) else None}")
        volumes = tuple(_number(value, "MALFORMED_PORTFOLIO", f"{node} hour {index}")
                        for index, value in enumerate(profile))
        if any(volume < 0 for volume in volumes):
            raise ImpactError("NEGATIVE_VOLUME", node)
        positions.append(NodePosition(node=node, region=region.strip(), contract_price_php_mwh=price,
                                      uncovered_mwh_by_hour=volumes))
    return tuple(positions)


# --- rows, changes, and the record ----------------------------------------


@dataclass(frozen=True)
class ImpactRow:
    """One scored origin's impact for one node, horizon and baseline.

    Peso values are rounded to two decimals when the row is built, and the
    materiality verdict is reached from the stored values, so the record's own
    numbers reproduce the record's verdicts. The uncovered volume is the exact
    sum of the profile, never rounded: it is the volume the pesos were computed
    from.
    """

    origin: str
    window_hours: int
    uncovered_mwh: float
    p10_php: float
    p50_php: float
    p90_php: float
    settled_php: float

    def to_dict(self) -> dict:
        return {
            "origin": self.origin,
            "window_hours": self.window_hours,
            "uncovered_mwh": self.uncovered_mwh,
            "p10_php": self.p10_php,
            "p50_php": self.p50_php,
            "p90_php": self.p90_php,
            "settled_php": self.settled_php,
        }


def bands_of(rows: Sequence[ScoredBand], series: str, horizon: str, baseline: str,
             slice_name: str = MARKET) -> tuple[ScoredBand, ...]:
    """The scored bands of one (series, horizon, baseline, slice), in origin order.

    The rows arrive in the scorecard's own scoring order, which is chronological.
    """
    return tuple(row for row in rows
                 if row.series == series and row.horizon == horizon
                 and row.baseline == baseline and row.slice == slice_name)


def impact_rows(position: NodePosition, bands: Sequence[ScoredBand]) -> tuple[ImpactRow, ...]:
    """Price one node's uncovered profile against one band per scored origin.

    The window of an origin is the horizon's own window
    (:func:`src.price.baselines.window_for`), so the profile is read at the clock
    hour of every hour the scorecard scored, and the window's length follows the
    billing month for the month horizon.
    """
    rows = []
    for band in bands:
        window = window_for(band.horizon, date.fromisoformat(band.origin))
        rows.append(ImpactRow(
            origin=band.origin,
            window_hours=len(window.hours),
            uncovered_mwh=position.uncovered_mwh(window.hours),
            p10_php=round(position.impact_php(window.hours, band.p10), 2),
            p50_php=round(position.impact_php(window.hours, band.p50), 2),
            p90_php=round(position.impact_php(window.hours, band.p90), 2),
            settled_php=round(position.impact_php(window.hours, band.realized), 2),
        ))
    return tuple(rows)


def classify_changes(rows: Sequence[ImpactRow], policy: MaterialityPolicy) -> dict:
    """Compare consecutive scored origins of one (node, horizon, baseline).

    The first scored origin has no predecessor and is not a change; the record
    says so by counting ``compared`` one below the origin count.
    """
    changes = []
    for previous, current in zip(rows, rows[1:]):
        change = round(current.p50_php - previous.p50_php, 2)
        changes.append((current.origin, change))
    material = [(origin, change) for origin, change in changes if policy.is_material(change)]
    largest = max((abs(change) for _, change in changes), default=None)
    largest_origin = next((origin for origin, change in changes if abs(change) == largest), None)
    return {
        "compared": len(changes),
        "material": len(material),
        "material_changes": [[origin, change] for origin, change in material],
        "largest_abs_change_php": largest,
        "largest_change_origin": largest_origin,
    }


def build_impact_record(
    positions: Sequence[NodePosition],
    bands: Sequence[ScoredBand],
    policy: MaterialityPolicy,
    inputs: Sequence[Mapping[str, object]],
    horizons: Sequence[str] = HORIZONS,
    baselines: Sequence[str] | None = None,
) -> dict:
    """The whole record, with the materiality line ahead of every impact value.

    The key order is the record's own statement of the direction check: identity,
    then ``materiality``, then the method and the inputs, then the node blocks and
    the direction check. ``policy`` is required, so no change is scored before a
    line has been declared. The ``label`` is composed from ``inputs`` by
    :func:`demonstration_label`, so the record names the bytes the run verified.
    ``baselines`` names the scorecard's baselines and is reported even where a
    node's horizon scored no origin, so an empty block says which baseline was
    empty rather than disappearing.
    """
    if not isinstance(policy, MaterialityPolicy):
        raise ImpactError("POLICY_REQUIRED", type(policy).__name__)
    label = demonstration_label(inputs)
    if baselines is None:
        baselines = tuple(sorted({band.baseline for band in bands}))
    node_blocks = []
    pooled_compared = 0
    pooled_material = 0
    nodes_with_material = 0
    for position in positions:
        horizon_blocks = []
        node_has_material = False
        for horizon in horizons:
            here = [band for band in bands
                    if band.series == position.node and band.horizon == horizon]
            ap_origins = len({band.origin for band in here if band.slice == AP})
            blocks = []
            origins = 0
            for name in baselines:
                rows = impact_rows(position, bands_of(bands, position.node, horizon, name))
                summary = classify_changes(rows, policy)
                pooled_compared += summary["compared"]
                pooled_material += summary["material"]
                node_has_material = node_has_material or bool(summary["material"])
                latest = rows[-1] if rows else None
                origins = len(rows)
                blocks.append({
                    "baseline": name,
                    "origins": len(rows),
                    "latest": latest.to_dict() if latest else None,
                    "changes": summary,
                })
            horizon_blocks.append({
                "horizon": horizon,
                "origins": origins,
                "ap_origins_excluded": ap_origins,
                "baselines": blocks,
            })
        if node_has_material:
            nodes_with_material += 1
        node_blocks.append({
            "node": position.node,
            "region": position.region,
            "synthetic": True,
            "method_demonstration": True,
            "contract_price_php_mwh": position.contract_price_php_mwh,
            "horizons": horizon_blocks,
        })
    return {
        "kind": KIND,
        "version": VERSION,
        "synthetic": True,
        "label": label,
        "materiality": policy.to_dict(),
        "method": {
            "impact": METHOD_IMPACT,
            "band": METHOD_BAND,
            "profile": METHOD_PROFILE,
            "slice": MARKET,
            "horizons": list(horizons),
            "scorecard_replay": (
                "the bands are produced by re-running the PRICE-2 scorecard on the same "
                "exported bytes and refused unless the rebuilt record's digest equals the "
                "SHA-256 of the scorecard file"
            ),
        },
        "inputs": [dict(entry) for entry in inputs],
        "nodes": node_blocks,
        "direction_check": {
            "id": "IMPACT-1",
            "statement": MATERIALITY_STATEMENT,
            "label": label,
            "changes_compared": pooled_compared,
            "material_changes": pooled_material,
            "nodes_with_a_material_change": nodes_with_material,
        },
    }


def resolve_output(out: str | Path) -> Path:
    """The output path: a relative path resolves against the repository root.

    The runner is a repository tool, so ``--out .local/price/impact.json`` names
    the same file whatever the caller's working directory is; this is also the
    path the repository-tree guard checks.
    """
    path = Path(out)
    return path.resolve() if path.is_absolute() else (Path(__file__).resolve().parents[2] / path).resolve()


def refuse_output_inside_the_tree(out: str | Path) -> Path:
    """The record carries volumes and contract prices, so it never enters Git.

    A path inside the repository tree that is not under the ignored ``.local/``
    is refused; a path outside the tree (a scratch directory, for instance) is
    the caller's own business. Returns the resolved path.
    """
    root = Path(__file__).resolve().parents[2]
    resolved = resolve_output(out)
    if resolved.is_relative_to(root) and not resolved.is_relative_to(root / ".local"):
        raise ImpactError("WRITE_INTO_REPOSITORY", str(out))
    return resolved


def record_text(record: dict) -> str:
    """Canonical JSON, in the record's own key order, with no trailing newline."""
    text = json.dumps(record, sort_keys=False, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return text


def record_digest(record: dict) -> str:
    return hashlib.sha256(record_text(record).encode("utf-8")).hexdigest()


# --- pairing the portfolio with the scorecard's series ---------------------


def node_series(bands: Sequence[ScoredBand]) -> tuple[str, ...]:
    """The nodal series keys the bands came from, in first-seen order."""
    seen: list[str] = []
    for band in bands:
        if band.kind == "nodal" and band.series not in seen:
            seen.append(band.series)
    return tuple(seen)


def verify_bands_against_record(bands: Sequence[ScoredBand], record: Mapping) -> int:
    """Check the band levels against the metrics the scorecard file itself states.

    The replay proves the bands come from the record's configuration and bytes;
    this second, independent check proves the sink rows are the values the record
    scores: for every (series, horizon, baseline, slice) group, the pinball
    losses recomputed from the band levels must equal the losses in the record
    file, and the sample counts must agree. Returns the number of cells compared.
    """
    indexed: dict[tuple, list[ScoredBand]] = {}
    for band in bands:
        indexed.setdefault((band.series, band.horizon, band.baseline, band.slice), []).append(band)
    checked = 0
    for series_entry in record["series"]:
        for horizon_entry in series_entry["horizons"]:
            for baseline_entry in horizon_entry["baselines"]:
                for slice_name, metrics in baseline_entry["slices"].items():
                    key = (series_entry["key"], horizon_entry["horizon"],
                           baseline_entry["name"], slice_name)
                    rows = [(band.realized, band.point, band.p10, band.p50, band.p90)
                            for band in indexed.get(key, ())]
                    recomputed = metrics_from(rows).to_dict()
                    for name, stated in metrics.items():
                        mine = recomputed.get(name)
                        if stated is None and mine is None:
                            checked += 1
                            continue
                        if stated is None or mine is None or abs(mine - stated) > 1e-9:
                            raise ImpactError(
                                "BANDS_DO_NOT_MATCH",
                                f"{key}: {name} {mine} != {stated}",
                            )
                        checked += 1
    return checked


def pair_positions(positions: Sequence[NodePosition], bands: Sequence[ScoredBand]) -> None:
    """Refuse a portfolio node the scorecard has no scored band for.

    The synthetic file's aliases and the de-identified export's series keys are
    the same set; a node without a series cannot be priced, and this is a refusal
    rather than a silent skip.
    """
    available = set(node_series(bands))
    for position in positions:
        if position.node not in available:
            raise ImpactError("NODE_WITHOUT_SERIES", position.node)


__all__ = [
    "ALIAS_PATTERN",
    "DEFAULT_MATERIALITY",
    "SYNTHETIC_STATEMENT",
    "ImpactError",
    "ImpactRow",
    "KIND",
    "MATERIALITY_RULE",
    "MATERIALITY_STATEMENT",
    "MATERIALITY_THRESHOLD_PHP",
    "MaterialityPolicy",
    "NodePosition",
    "VERSION",
    "bands_of",
    "build_impact_record",
    "classify_changes",
    "demonstration_label",
    "impact_rows",
    "load_portfolio",
    "node_series",
    "pair_positions",
    "record_digest",
    "record_text",
    "refuse_output_inside_the_tree",
    "resolve_output",
    "verify_bands_against_record",
]
