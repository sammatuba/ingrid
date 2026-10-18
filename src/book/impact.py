"""BOOK-2: the impact of an outlook vintage's band on the synthetic book, per account and node.

This is the IMPACT-1 formula (:mod:`src.price.impact`) applied to the book's own rows. Every figure
is a method demonstration on the synthetic book. None of them is a business number.

The formula
===========
For one node and one window hour ``h``, with ``u(h)`` the uncovered MWh of :mod:`src.book.exposure`,
``r(h)`` the reference price and ``b_q(h)`` the vintage's band level at quantile ``q``::

    impact_q(h) = u(h) x (b_q(h) - r(h))          for q in p10, p50, p90

A node's figure is the sum over the window's hours. An account's figure is the sum over its nodes. The
sign is kept, as IMPACT-1 keeps it: where the band sits below the reference price, the uncovered
volume costs less than the contracted price, which is a gain and shows as a negative.

The three sums are a band, not a probability statement. A sum of per-hour quantiles is the quantile of
the sum only when the hours move together. IMPACT-1 sums the levels the same way.

The reference price: contract-weighted, never a benchmark
=========================================================
``r(h)`` is the MW-weighted price of the contracts that cover that node and hour::

    r(h) = sum(mw_c x price_c) / sum(mw_c)       over the covering contracts c

Why: the uncovered volume is the part of the hour the account did not hedge. The contracts that cover
the rest of that hour state what the account pays for hedged power at that node and hour, so the band
is measured against that price. IMPACT-1 measures against the one contract price its portfolio file
states. No benchmark price exists in any record the book or the archive holds. A benchmark would be an
invented number, so none is used: an hour with uncovered volume and no covering contract is refused
(``NO_COVERING_CONTRACT``). ``r(h)`` is rounded to centavos (two decimals) and the rounded value is
the one multiplied, so the record's own numbers reproduce every hour figure. Hour figures are rounded
to centavos, and the node and account figures are sums of the stored hour figures.

The band is the vintage's, tied by digest
==========================================
A band is read only through :func:`tie_band` or :func:`load_vintage`. They refuse unless:

* the outlook record validates as an ``OutlookRecord`` (:func:`src.outlook.records.validate_outlook`,
  which recomputes its ``content_digest``) and that digest equals the one the caller names;
* the SHA-256 of the values file's bytes equals the record's ``values_ref.sha256`` and the row count
  equals ``values_ref.rows``;
* every row is a whole local hour inside the record's horizon, once, with ``p10``, ``p50`` and ``p90``
  all present or all absent (the shape :mod:`src.outlook.scoring` reads).

A values file with the mid value only gives a zero-width band (p10 = p50 = p90 = the value), the
scoring module's rule, and the record states it. The band's series is the node's region code or
``SYSTEM``. A system band on a regional node is used and the record names that basis. A band for
another region is refused. Every window hour must have a band row (``WINDOW_OUTSIDE_VINTAGE``).
Nothing is filled. A window of several whole days is priced hour by hour over every day, with the
profile repeated per day, so a month total is the sum over the window's days. It must lie inside the
vintage's horizon.

A tied band resists change in the process. Its levels are a read-only mapping. ``tie_band`` seals the
band with an HMAC over its identity fields and levels, keyed by a random key made when this module
loads. :func:`build_impact` recomputes the seal and refuses a band whose seal does not match
(``BAND_NOT_TIED``): a hand-built band, a ``dataclasses.replace`` copy with other levels, or one changed
through ``object.__setattr__``. A deep copy is refused with ``BAND_NOT_COPYABLE``. The seal stops every
accidental path. It is not a security boundary: code in the same process that reads the private key
can reseal a band on purpose. The seal is never written to a record.

The vintage must be known at the question's cutoff
==================================================
An impact rests on a vintage only when the vintage was issued at or before the question's cutoff
(orchestrator decision at the BOOK-2 review). An instant cutoff closes at itself. A date cutoff closes
at the next Manila midnight. A later vintage is refused (``VINTAGE_AFTER_CUTOFF``). The record states
both instants under ``as_of``.

The materiality line comes first
================================
:func:`build_impact` and :func:`compare_impacts` require a :class:`src.price.impact.MaterialityPolicy`
and have no default, so no figure is written and no change is classified before a line is stated. The
``materiality`` block is the first key of every record here, and :func:`record_text` keeps the key
order. A change is the later vintage's mid band (p50) minus the earlier one's, for the same book,
window, cutoff, accounts and nodes, and it is material when it reaches the stated line.
:func:`verify_record` recomputes every change and every verdict of a change record from its own
stated threshold and comparator, so a stored change record proves its own verdicts.

Versions are append-only
========================
:class:`ImpactStore` writes each record once, under its own content digest, with an exclusive create.
A new vintage gives a new impact record beside the old one. Nothing is replaced. The store refuses a
root inside the repository tree outside ``.local/``, because a record priced against a real vintage
carries that vintage's band levels.

This module imports :mod:`src.price.impact` and never edits it. It does not define an alias pattern and
never calls its portfolio loader or its pairing check: the book's rows are keyed by the book's node id.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from pathlib import Path

from src.outlook.records import OutlookArchive, OutlookError, validate_outlook
from src.price import impact as price_impact
from src.price.impact import MaterialityPolicy
from src.price.series import REGIONAL_KEYS

from .exposure import MANILA, ExposureError, Window, cutoff_close, exposure, region_name
from .records import LABEL as BOOK_LABEL

KIND = "BookImpact"
CHANGE_KIND = "BookImpactChange"
VERSION = "book-impact-1"
ROOT = Path(__file__).resolve().parents[2]
BAND_KEYS = ("p10", "p50", "p90")
SYSTEM = "SYSTEM"
#: The key of the in-process band seal. It is made when the module loads and is never written anywhere.
_SEAL_KEY = secrets.token_bytes(32)

#: The method strings go into every record, and the book page shows them. They follow the site's
#: plain-language rules: short active sentences, no semicolons, no banned words.
METHOD_IMPACT = (
    "For one node, hour and band level, the impact equals uncovered MWh times (band level minus reference "
    "price). A node's figure is the sum over the window's hours. An account's figure is the sum over its "
    "nodes. The sign stays, so a negative figure is a gain."
)
METHOD_REFERENCE = (
    "The reference price is the MW-weighted price of the contracts that cover the node and hour, in "
    "centavos. The uncovered volume is the unhedged part of the hour. The covering contracts state the "
    "price of the hedged part. No record holds a benchmark price. So the method refuses an hour with "
    "uncovered volume and no covering contract."
)
METHOD_BAND = (
    "The band is the vintage's three levels at each window hour. The method reads them only when the "
    "outlook record is valid and its record id matches the named id. The SHA-256 of the values file must "
    "match the record too. A file with the middle value only gives a band of zero width."
)
METHOD_SUM = (
    "The three sums form a band, not a probability. A sum of hourly quantiles is the quantile of the sum "
    "only when the hours move together. IMPACT-1 sums them the same way."
)
BOOK_RULE = (
    "A change is the account's middle impact figure under the later vintage minus the one under the "
    "earlier vintage. Both use the same book, window, cutoff, accounts and nodes. The change is in pesos. "
    "It is material when its size reaches the threshold by the comparator."
)
BOOK_STATEMENT = (
    "The materiality line comes before any figure. Every call that writes a figure or classifies a change "
    "needs it. It is the first block of every record."
)
BOOK_BASIS = (
    "This line is a policy of the method demonstration. The owner has not given a line. It is never a "
    "business limit."
)
AS_OF_RULE = (
    "A vintage can price a question only when its issue time is at or before the question's cutoff. A "
    "date cutoff closes at the next Manila midnight."
)
BAND_ZERO = "zero: the vintage states the middle value only, so all three levels are equal"
BAND_FULL = "the vintage states three levels per hour"


class BookImpactError(ExposureError):
    """A refused impact question; ``code`` is stable and names the rule that refused it."""


# --- the vintage's band -------------------------------------------------------


@dataclass(frozen=True)
class VintageBand:
    """The band of one issued outlook vintage, tied to the record by digest."""

    outlook_id: str
    outlook_digest: str
    values_sha256: str
    series: str
    synthetic: bool
    issued_at: str
    information_cutoff: str
    horizon: dict
    model_version: str
    target_series_ref: dict
    zero_width: bool
    levels: MappingProxyType = field(repr=False)
    seal: str = field(default="", repr=False, compare=False)

    def at(self, hour: datetime) -> tuple[float, float, float]:
        try:
            return self.levels[hour]
        except KeyError:
            raise BookImpactError("WINDOW_OUTSIDE_VINTAGE",
                                  f"{hour.isoformat()} has no band row in {self.outlook_id}") from None

    def reference(self) -> dict:
        return {"outlook_id": self.outlook_id, "outlook_digest": self.outlook_digest,
                "values_sha256": self.values_sha256, "series": self.series, "synthetic": self.synthetic,
                "issued_at": self.issued_at, "information_cutoff": self.information_cutoff,
                "horizon": dict(self.horizon), "model_version": self.model_version,
                "target_series_ref": dict(self.target_series_ref),
                "band_width": BAND_ZERO if self.zero_width else BAND_FULL}

    def __deepcopy__(self, memo):
        raise BookImpactError("BAND_NOT_COPYABLE",
                              "a tied band is not copied; tie the vintage again with tie_band or load_vintage")

    def _expected_seal(self) -> str:
        """The HMAC this band's fields and levels give under the module's key."""
        identity = [self.outlook_id, self.outlook_digest, self.values_sha256, self.series, self.synthetic,
                    self.issued_at, self.information_cutoff, self.horizon, self.model_version,
                    self.target_series_ref, self.zero_width]
        levels = [[hour.isoformat(), list(band)] for hour, band in sorted(dict(self.levels).items())]
        text = json.dumps([identity, levels], sort_keys=True, separators=(",", ":"))
        return hmac.new(_SEAL_KEY, text.encode("utf-8"), hashlib.sha256).hexdigest()


def check_band(vintage) -> "VintageBand":
    """Refuse a band that ``tie_band`` did not seal, or one changed after the seal."""
    if not isinstance(vintage, VintageBand) or not isinstance(vintage.levels, MappingProxyType):
        raise BookImpactError("BAND_NOT_TIED", "the band was not read through tie_band or load_vintage")
    if not hmac.compare_digest(vintage.seal, vintage._expected_seal()):
        raise BookImpactError("BAND_NOT_TIED", "the band does not match the seal tie_band gave it")
    return vintage


def _finite(value) -> float:
    if type(value) is bool or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BookImpactError("BAND_SHAPE", "a band value is not a finite number")
    return float(value)


def _horizon_local(outlook: dict) -> tuple[datetime, datetime]:
    edges = []
    for edge in ("start", "end"):
        instant = datetime.fromisoformat(outlook["horizon"][edge].replace("Z", "+00:00"))
        edges.append(instant.astimezone(MANILA).replace(tzinfo=None))
    return edges[0], edges[1]


def tie_band(outlook: dict, values_bytes: bytes, outlook_digest: str) -> VintageBand:
    """The band of a vintage, refused unless it ties to the named record by digest."""
    try:
        validate_outlook(outlook)
    except OutlookError:
        raise BookImpactError("VINTAGE_NOT_A_RECORD", "the outlook does not validate as an OutlookRecord") from None
    if type(outlook_digest) is not str or outlook["content_digest"] != outlook_digest:
        raise BookImpactError("VINTAGE_DIGEST_MISMATCH", "the outlook record is not the one named by digest")
    if not isinstance(values_bytes, (bytes, bytearray)):
        raise BookImpactError("BAND_UNREADABLE", "the values are not bytes")
    sha = hashlib.sha256(bytes(values_bytes)).hexdigest()
    if sha != outlook["values_ref"]["sha256"]:
        raise BookImpactError("BAND_DIGEST_MISMATCH",
                              f"the values file is not the one {outlook['outlook_id']} cites by SHA-256")
    try:
        payload = json.loads(bytes(values_bytes).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise BookImpactError("BAND_UNREADABLE", "the values file does not parse") from None
    if type(payload) is not dict or type(payload.get("hours")) is not list:
        raise BookImpactError("BAND_SHAPE", "the values file has no hours list")
    rows = payload["hours"]
    if len(rows) != outlook["values_ref"]["rows"]:
        raise BookImpactError("BAND_ROWS_MISMATCH", "the row count differs from the record's values_ref")
    series = payload.get("series")
    if series not in REGIONAL_KEYS:
        raise BookImpactError("BAND_SERIES_UNSUPPORTED", repr(series))
    start, end = _horizon_local(outlook)
    levels = {}
    zero_width = True
    for row in rows:
        if type(row) is not dict or "hour_start" not in row or "value" not in row:
            raise BookImpactError("BAND_SHAPE", "a row lacks hour_start or value")
        try:
            hour = datetime.fromisoformat(row["hour_start"])
        except (TypeError, ValueError):
            raise BookImpactError("BAND_SHAPE", "an hour does not parse") from None
        if hour.tzinfo is not None or (hour.minute, hour.second, hour.microsecond) != (0, 0, 0):
            raise BookImpactError("BAND_SHAPE", "an hour is not a whole naive local hour")
        if hour in levels or not start <= hour < end:
            raise BookImpactError("BAND_SHAPE", "an hour repeats or lies outside the record's horizon")
        point = _finite(row["value"])
        present = [key for key in BAND_KEYS if key in row]
        if present and len(present) != len(BAND_KEYS):
            raise BookImpactError("BAND_SHAPE", "a row carries part of the band")
        if present:
            zero_width = False
            levels[hour] = tuple(sorted(_finite(row[key]) for key in BAND_KEYS))
        else:
            levels[hour] = (point, point, point)
    if not levels:
        raise BookImpactError("BAND_SHAPE", "the values file has no rows")
    band = VintageBand(outlook_id=outlook["outlook_id"], outlook_digest=outlook["content_digest"],
                       values_sha256=sha, series=series, synthetic=outlook["synthetic"],
                       issued_at=outlook["issued_at"], information_cutoff=outlook["information_cutoff"],
                       horizon=dict(outlook["horizon"]), model_version=outlook["model_version"],
                       target_series_ref=dict(outlook["target_series_ref"]), zero_width=zero_width,
                       levels=MappingProxyType(dict(levels)))
    object.__setattr__(band, "seal", band._expected_seal())
    return band


def load_vintage(archive_root, outlook_id: str, outlook_digest: str, values_file=None) -> VintageBand:
    """Read a vintage from an archive by id and digest and tie its band.

    The values file is the record's ``values_ref.path_hint`` (absolute as stored, else from the
    repository root) unless ``values_file`` names another copy; either way its bytes must match the
    record's SHA-256.
    """
    try:
        outlook = OutlookArchive(archive_root).outlook(outlook_id)
    except OutlookError as error:
        code = "VINTAGE_UNKNOWN" if error.code == "OUTLOOK_UNKNOWN" else "VINTAGE_NOT_A_RECORD"
        raise BookImpactError(code, repr(outlook_id)) from None
    hint = Path(outlook["values_ref"]["path_hint"])
    path = Path(values_file) if values_file is not None else (hint if hint.is_absolute() else ROOT / hint)
    try:
        data = path.read_bytes()
    except OSError:
        raise BookImpactError("BAND_UNREADABLE", path.name) from None
    return tie_band(outlook, data, outlook_digest)


# --- the label and the materiality block --------------------------------------


def impact_label(vintage: VintageBand) -> str:
    """The label every figure carries: the book's label and the vintage it was priced against."""
    kind = ("the synthetic vintage " + vintage.outlook_id if vintage.synthetic
            else "the issued vintage " + vintage.outlook_id + ", which declares real inputs")
    return (f"{BOOK_LABEL} Priced against {kind}, record id {vintage.outlook_digest[:12]}, values "
            f"{vintage.values_sha256[:12]}. Every peso figure is a method demonstration on the synthetic "
            "book, never a business number.")


def materiality_block(policy) -> dict:
    if not isinstance(policy, MaterialityPolicy):
        raise BookImpactError("POLICY_REQUIRED", type(policy).__name__)
    stated = policy.to_dict()
    return {"threshold_php": stated["threshold_php"], "comparator": stated["comparator"],
            "rule": BOOK_RULE, "statement": BOOK_STATEMENT, "basis": BOOK_BASIS,
            "policy": "src.price.impact.MaterialityPolicy"}


# --- the impact ---------------------------------------------------------------


def _cents(value: float) -> float:
    return round(value + 0.0, 2) + 0.0


def reference_price(row: dict):
    """The contract-weighted price of an exposure row's covering contracts, in centavos, or None."""
    contracts = row["covering_contracts"]
    mw = sum(c["mw"] for c in contracts)
    if not contracts or mw <= 0:
        if row["uncovered_mwh"] > 0:
            raise BookImpactError("NO_COVERING_CONTRACT",
                                  f"{row['node_id']} at {row['hour_start']}: uncovered volume and no contract "
                                  "price to measure it against; no benchmark price is in any record")
        return None
    return _cents(sum(c["mw"] * c["price_php_mwh"] for c in contracts) / mw)


def band_basis(vintage: VintageBand, region_code: str) -> str:
    if vintage.series == region_code:
        return "regional: the vintage's series is the node's region"
    if vintage.series == SYSTEM:
        return "system: the vintage states no regional series, so its system band prices the regional node"
    raise BookImpactError("BAND_REGION_MISMATCH",
                          f"{vintage.outlook_id} prices {vintage.series}, the node is in {region_code}")


def _hour_block(row: dict, vintage: VintageBand, label: str) -> dict:
    hour = datetime.fromisoformat(row["hour_start"])
    levels = vintage.at(hour)
    reference = reference_price(row)
    block = {"hour_start": row["hour_start"], "uncovered_mwh": row["uncovered_mwh"],
             "reference_php_mwh": reference, "covering_contracts": [c["id"] for c in row["covering_contracts"]],
             "band_php_mwh": dict(zip(BAND_KEYS, levels))}
    for key, level in zip(BAND_KEYS, levels):
        block[f"{key}_php"] = 0.0 if reference is None else _cents(row["uncovered_mwh"] * (level - reference))
    block.update({"synthetic": True, "label": label})
    return block


def _sums(blocks: list[dict]) -> dict:
    return {f"{key}_php": _cents(sum(b[f"{key}_php"] for b in blocks)) for key in BAND_KEYS}


def build_impact(book: dict, vintage: VintageBand, window: Window, cutoff, policy, *,
                 accounts=None, nodes=None, region=None) -> dict:
    """The impact record per account and node over a window, against one vintage's band.

    ``policy`` is required and has no default. The record's first key is ``materiality``. The
    exposure is :func:`src.book.exposure.exposure` of the same window and cutoff, so every refusal of
    that function applies here first.
    """
    stated = materiality_block(policy)
    check_band(vintage)
    as_of = as_of_block(vintage, cutoff)
    record = exposure(book, window, cutoff, accounts=accounts, nodes=nodes, region=region)
    for hour in window.hours:
        vintage.at(hour)
    label = impact_label(vintage)
    account_blocks = []
    for account in record["accounts"]:
        node_blocks = []
        for node_id in account["nodes"]:
            rows = [r for r in record["rows"] if r["node_id"] == node_id]
            basis = band_basis(vintage, rows[0]["region_code"])
            hours = [_hour_block(r, vintage, label) for r in rows]
            node_blocks.append({"node_id": node_id, "region": rows[0]["region"],
                                "region_code": rows[0]["region_code"], "band_basis": basis,
                                "reference_basis": "contract_weighted",
                                "uncovered_mwh": round(sum(r["uncovered_mwh"] for r in rows), 3) + 0.0,
                                **_sums(hours), "hours": hours, "synthetic": True, "label": label})
        account_blocks.append({"account_id": account["account_id"], "name": account["name"],
                               "region": account["region"], "region_code": account["region_code"],
                               "uncovered_mwh": account["uncovered_mwh"], **_sums(node_blocks),
                               "nodes": node_blocks, "synthetic": True, "label": label})
    out = {
        "materiality": stated,
        "kind": KIND,
        "version": VERSION,
        "synthetic": True,
        "label": label,
        "book": record["book"],
        "vintage": vintage.reference(),
        "window": record["window"],
        "cutoff": record["cutoff"],
        "as_of": as_of,
        "method": {"impact": METHOD_IMPACT, "reference": METHOD_REFERENCE, "band": METHOD_BAND,
                   "sum": METHOD_SUM, "uncovered": record["method"]["uncovered"],
                   "cover": record["method"]["cover"]},
        "units": {"impact": "PHP, a method demonstration", "uncovered_mwh": "MWh, a method demonstration",
                  "price": "PHP/MWh, a method demonstration"},
        "accounts": account_blocks,
        "totals": {"uncovered_mwh": record["totals"]["uncovered_mwh"], **_sums(account_blocks),
                   "synthetic": True, "label": label},
    }
    out["content_digest"] = record_digest(out)
    return out


def _z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def as_of_block(vintage: VintageBand, cutoff) -> dict:
    """Refuse a vintage issued after the question's cutoff; state both instants."""
    closes = cutoff_close(cutoff)
    issued = datetime.fromisoformat(vintage.issued_at.replace("Z", "+00:00"))
    date_cutoff = not isinstance(cutoff, datetime) and (not isinstance(cutoff, str) or len(cutoff) == 10)
    if issued > closes or (date_cutoff and issued == closes):
        raise BookImpactError("VINTAGE_AFTER_CUTOFF",
                              f"{vintage.outlook_id} was issued {vintage.issued_at}, after the cutoff {_z(closes)}")
    return {"question_cutoff": cutoff if isinstance(cutoff, str) else str(cutoff),
            "question_cutoff_closes": _z(closes), "vintage_issued_at": vintage.issued_at,
            "vintage_information_cutoff": vintage.information_cutoff, "rule": AS_OF_RULE}


def affected_impact(book: dict, region: str, window: Window, cutoff, vintage: VintageBand, policy) -> dict:
    """The impact on the affected part of the book: every account and node of the region."""
    return build_impact(book, vintage, window, cutoff, policy, region=region_name(region))


def query_impact(book: dict, archive_root, outlook_id: str, outlook_digest: str, window: Window, cutoff,
                 policy, accounts=None) -> dict:
    """The dock's query: accounts and a vintage named by id and digest, priced over a window."""
    vintage = load_vintage(archive_root, outlook_id, outlook_digest)
    return build_impact(book, vintage, window, cutoff, policy, accounts=accounts)


# --- records, changes and the store -------------------------------------------


def record_text(record: dict) -> str:
    """Canonical JSON in the record's own key order (:func:`src.price.impact.record_text`)."""
    return price_impact.record_text(record)


def record_digest(record: dict) -> str:
    """SHA-256 of the record's text without its ``content_digest`` key."""
    return price_impact.record_digest({k: v for k, v in record.items() if k != "content_digest"})


def verify_record(record: dict, kind: str = KIND) -> dict:
    if type(record) is not dict or record.get("kind") != kind or record.get("synthetic") is not True:
        raise BookImpactError("RECORD_INVALID", "not a synthetic impact record of this kind")
    if next(iter(record)) != "materiality":
        raise BookImpactError("RECORD_INVALID", "the materiality block is not the record's first block")
    if record.get("content_digest") != record_digest(record):
        raise BookImpactError("RECORD_DIGEST_MISMATCH", "the record does not match its own content digest")
    if kind == CHANGE_KIND:
        _check_verdicts(record)
    return record


def _check_verdicts(record: dict) -> None:
    """Every change and verdict of a change record follows from its own figures and stated line."""
    try:
        block = record["materiality"]
        policy = MaterialityPolicy(block["threshold_php"], block["comparator"])
        rows = record["accounts"]
        for row in rows:
            if row["change_php"] != _cents(row["p50_after_php"] - row["p50_before_php"]):
                raise BookImpactError("RECORD_INVALID", f"{row['account_id']}: the change does not follow")
            if row["material"] is not policy.is_material(row["change_php"]):
                raise BookImpactError("RECORD_INVALID", f"{row['account_id']}: the verdict does not follow the line")
        if record["summary"]["material"] != sum(1 for row in rows if row["material"]):
            raise BookImpactError("RECORD_INVALID", "the material count does not follow")
    except (KeyError, TypeError, price_impact.ImpactError):
        raise BookImpactError("RECORD_INVALID", "the change record lacks a field or states no valid line") from None


def compare_impacts(before: dict, after: dict, policy) -> dict:
    """Classify the change of each account's mid band between two vintages' impact records.

    ``policy`` is required. Both records must state the same line, and must price the same book,
    window, cutoff, accounts and nodes of each account. Otherwise the change is refused rather than
    computed.
    """
    stated = materiality_block(policy)
    for record in (before, after):
        verify_record(record)
        if record["materiality"] != stated:
            raise BookImpactError("POLICY_MISMATCH", "a record states another materiality line")
    for key in ("book", "window", "cutoff"):
        if before[key] != after[key]:
            raise BookImpactError("CHANGE_NOT_COMPARABLE", f"the two records differ in {key}")
    if [a["account_id"] for a in before["accounts"]] != [a["account_id"] for a in after["accounts"]]:
        raise BookImpactError("CHANGE_NOT_COMPARABLE", "the two records price different accounts")
    for old, new in zip(before["accounts"], after["accounts"]):
        if [n["node_id"] for n in old["nodes"]] != [n["node_id"] for n in new["nodes"]]:
            raise BookImpactError("CHANGE_NOT_COMPARABLE",
                                  f"the two records price different nodes of {old['account_id']}")
    label = (f"{BOOK_LABEL} The change between {before['vintage']['outlook_id']} and "
             f"{after['vintage']['outlook_id']}. Every peso figure is a method demonstration, never a "
             "business number.")
    rows = []
    for old, new in zip(before["accounts"], after["accounts"]):
        change = _cents(new["p50_php"] - old["p50_php"])
        rows.append({"account_id": old["account_id"], "nodes": [n["node_id"] for n in old["nodes"]],
                     "p50_before_php": old["p50_php"],
                     "p50_after_php": new["p50_php"], "change_php": change,
                     "material": policy.is_material(change), "synthetic": True, "label": label})
    out = {
        "materiality": stated,
        "kind": CHANGE_KIND,
        "version": VERSION,
        "synthetic": True,
        "label": label,
        "book": before["book"],
        "window": before["window"],
        "cutoff": before["cutoff"],
        "before": {"vintage": before["vintage"]["outlook_id"], "outlook_digest": before["vintage"]["outlook_digest"],
                   "impact_digest": before["content_digest"]},
        "after": {"vintage": after["vintage"]["outlook_id"], "outlook_digest": after["vintage"]["outlook_digest"],
                  "impact_digest": after["content_digest"]},
        "accounts": rows,
        "summary": {"compared": len(rows), "material": sum(1 for r in rows if r["material"]),
                    "synthetic": True, "label": label},
    }
    out["content_digest"] = record_digest(out)
    return out


class ImpactStore:
    """Impact and change records, each written once under its content digest; nothing is replaced."""

    def __init__(self, root) -> None:
        try:
            self.root = price_impact.refuse_output_inside_the_tree(root)
        except price_impact.ImpactError:
            raise BookImpactError("WRITE_INTO_REPOSITORY", str(root)) from None

    def path_of(self, record: dict) -> Path:
        return self.root / record["kind"] / f"{record['content_digest']}.json"

    def append(self, record: dict) -> Path:
        verify_record(record, record.get("kind") if record.get("kind") in (KIND, CHANGE_KIND) else KIND)
        path = self.path_of(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(record_text(record))
        except FileExistsError:
            raise BookImpactError("RECORD_EXISTS", "that record is already stored; versions are append-only") from None
        return path

    def read(self, kind: str, digest: str) -> dict:
        path = self.root / kind / f"{digest}.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise BookImpactError("RECORD_UNKNOWN", digest) from None
        return verify_record(record, kind)

    def digests(self, kind: str = KIND) -> tuple[str, ...]:
        return tuple(sorted(p.stem for p in (self.root / kind).glob("*.json")))


__all__ = ["BAND_KEYS", "BookImpactError", "CHANGE_KIND", "as_of_block", "check_band", "ImpactStore", "KIND", "VERSION", "VintageBand",
           "affected_impact", "band_basis", "build_impact", "compare_impacts", "impact_label", "load_vintage",
           "materiality_block", "query_impact", "record_digest", "record_text", "reference_price", "tie_band",
           "verify_record"]
