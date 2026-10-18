"""BOOK-1: the book record, its content digest and its validator.

One record, ``book.v1``: the version, the seed, the counts, every account, node, contract and profile
row, and a content digest. Digests are lowercase SHA-256 hex over the canonical JSON of the record with
the top-level ``content_digest`` key removed (:mod:`src.contracts.jsonutil`), as the outlook archive does.
Every row carries ``synthetic: true``. The record carries the label sentence. Every peso and MW in it is a
method demonstration on an invented book. The digest proves the bytes did not change, not that the book
means anything.
"""
from __future__ import annotations

import re
from datetime import date

from src.contracts.jsonutil import CanonicalizationError, canonical_dumps, compute_content_digest

from . import generate as gen

SCHEMA_VERSION = "book.v1"
KIND = "SyntheticBook"
VERSION = "book-v1"
LABEL = "Synthetic book, a method demonstration: no account, contract, node or volume in it is real."
UNITS = {"price": "PHP/MWh, a method demonstration", "demand": "MW, a method demonstration",
         "contract_volume": "MW, a method demonstration"}
METHOD = ("src/book/generate.py: a keyed SHA-256 stream from the seed; accounts from an invented name list; "
          "nodes dealt to accounts in turn; shaped hourly profiles; contracts sized as a share of the lowest "
          "demand in their hours")
ALIAS_FORM = re.compile(r"\d{2}" + gen.ALIAS_MARK + r"[A-Z]{2}_L\d{2}\Z")
TOP_KEYS = frozenset({"schema_version", "kind", "version", "seed", "counts", "synthetic", "label", "units",
                      "method", "regions", "accounts", "nodes", "contracts", "profiles", "content_digest"})
ROW_GROUPS = ("accounts", "nodes", "contracts", "profiles")


class BookError(ValueError):
    """A refused or malformed book record; ``code`` is stable."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)


def seal(record: dict) -> dict:
    """Attach the canonical ``content_digest`` of everything else in the record."""
    try:
        record["content_digest"] = compute_content_digest(record)
    except CanonicalizationError:
        raise BookError("BOOK_INVALID", "the record could not be canonicalized") from None
    return record


def counts_of(rows: dict) -> dict:
    per_region = {group: {r: sum(1 for row in rows[group] if row["region"] == r) for r in gen.REGIONS}
                  for group in ("accounts", "nodes")}
    by_kind = {k: sum(1 for c in rows["contracts"] if c["kind"] == k) for k in gen.KINDS}
    return {"accounts": len(rows["accounts"]), "nodes": len(rows["nodes"]),
            "contracts": len(rows["contracts"]), "profiles": len(rows["profiles"]),
            "accounts_by_region": per_region["accounts"], "nodes_by_region": per_region["nodes"],
            "contracts_by_kind": by_kind}


def build_book(seed: int = gen.SEED, counts=None) -> dict:
    """The sealed book record for a seed and counts; the same inputs give the same bytes."""
    rows = gen.generate_rows(seed, counts)
    record = {"schema_version": SCHEMA_VERSION, "kind": KIND, "version": VERSION, "seed": seed,
              "counts": counts_of(rows), "synthetic": True, "label": LABEL, "units": dict(UNITS),
              "method": METHOD, "regions": [{"name": r, "code": gen.REGION_CODES[r]} for r in gen.REGIONS],
              **rows}
    seal(record)
    validate_book(record)
    return record


def dumps(record: dict) -> str:
    """The fixture's bytes: sorted keys, two-space indent, one final newline."""
    import json
    return json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _need(condition, detail):
    if not condition:
        raise BookError("BOOK_INVALID", detail)


def validate_book(record) -> None:
    """Raise BookError unless the record is a well-formed, correctly sealed synthetic book.

    A row that lacks a field, or holds a field of the wrong type, raises BookError and never KeyError.
    """
    try:
        _validate(record)
    except (KeyError, TypeError, AttributeError, IndexError):
        raise BookError("BOOK_INVALID", "a row lacks a field or holds one of the wrong type") from None


def _validate(record) -> None:
    _need(isinstance(record, dict) and set(record) == TOP_KEYS, "top-level keys")
    _need(record["schema_version"] == SCHEMA_VERSION and record["kind"] == KIND, "schema or kind")
    _need(record["synthetic"] is True and record["label"] == LABEL, "label or synthetic flag")
    _need(type(record["seed"]) is int, "seed")
    for group in ROW_GROUPS:
        _need(isinstance(record[group], list) and record[group], f"{group} is a non-empty list")
        for row in record[group]:
            _need(isinstance(row, dict) and row.get("synthetic") is True, f"{group} row without synthetic: true")
        ids = [row.get("id") for row in record[group]]
        _need(all(type(i) is str for i in ids) and len(set(ids)) == len(ids), f"{group} ids are unique text")
    accounts = {a["id"]: a for a in record["accounts"]}
    nodes = {n["id"]: n for n in record["nodes"]}
    for a in accounts.values():
        _need(a["region"] in gen.REGIONS and a["region_code"] == gen.REGION_CODES[a["region"]], "account region")
    for n in nodes.values():
        _need(n["region"] in gen.REGIONS and n["region_code"] == gen.REGION_CODES[n["region"]], "node region")
        _need(n["account_id"] in accounts and accounts[n["account_id"]]["region"] == n["region"], "node account")
        _need(ALIAS_FORM.match(n["alias"]) is not None, "node alias form")
        low, high = gen.PREFIX_RANGE[n["region"]]
        _need(low <= int(n["alias"][:2]) <= high, "node alias prefix is outside the node's region")
    _need(len({n["alias"] for n in nodes.values()}) == len(nodes), "node aliases are unique")
    for p in record["profiles"]:
        _need(p["node_id"] in nodes and p["account_id"] == nodes[p["node_id"]]["account_id"], "profile node")
        mw = p["mw_by_hour"]
        _need(isinstance(mw, list) and len(mw) == 24 and all(type(v) in (int, float) and v >= 0 for v in mw),
              "profile has 24 non-negative hours")
    for c in record["contracts"]:
        _need(c["kind"] in gen.KINDS, "contract kind")
        _need(c["node_id"] in nodes and c["account_id"] == nodes[c["node_id"]]["account_id"], "contract node")
        _need(type(c["price_php_mwh"]) in (int, float) and c["price_php_mwh"] > 0, "contract price")
        _need(type(c["mw"]) in (int, float) and c["mw"] > 0, "contract mw")
        hours = c["hours"]
        _need(isinstance(hours, list) and hours == sorted(set(hours)) and hours
              and all(type(h) is int and 0 <= h <= 23 for h in hours), "contract hours")
        try:
            start, end = date.fromisoformat(c["term_start"]), date.fromisoformat(c["term_end"])
        except (TypeError, ValueError):
            raise BookError("BOOK_INVALID", "contract term dates") from None
        _need(start < end, "contract term order")
    _need(record["counts"] == counts_of(record), "counts do not match the rows")
    _need(record["content_digest"] == compute_content_digest(record), "content digest does not recompute")
