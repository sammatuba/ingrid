"""BOOK-1: the deterministic generator of the synthetic retailer's book.

Every account, node, contract and volume here is invented. Every peso and every MW is a method
demonstration. No real customer, contract, meter, node code or volume is read or approximated.

The rule, in words
==================
* Randomness comes from one keyed hash stream (SHA-256 over the seed, a label and a counter), so the
  output does not depend on the Python version or on any global state.
* Accounts are named from a fixed list of invented names, grouped by region in the order Luzon,
  Visayas, Mindanao. Each account has a load shape: office, factory, cold chain or residential mix.
* Nodes get aliases in the WESM resource-name form, ``NNSYNxx_Lnn``. The two-digit prefix sits inside
  the profile's range for the node's region (Luzon 01-03, Visayas 04-08, Mindanao 09-14), so
  ``src.adapters.wesm.registry.region_of`` returns the node's region. The ``SYN`` marker keeps an alias
  apart from a real node code and from the ``N01`` to ``N12`` aliases of the private list.
* Nodes are dealt to the accounts of their region in turn, so every account has at least one node when
  the region has at least as many nodes as accounts.
* A node's demand profile is its account's shape times a peak size, with a small hourly wobble.
* Contracts follow the node's position in the region: the first node gets one fixed-price contract, the
  second a peak and an off-peak time-of-use block, the third a fixed contract and a peak block. The
  pattern then repeats. Each contract's MW is a share of the lowest demand in its own hours, so a
  contract never exceeds the node's demand and some demand stays uncovered.
* Where two contracts cover the same hours, each takes a smaller share, so their sum stays under demand.
* Prices are whole tens of PHP/MWh. Terms are whole months, end on a month's last day and never end before 31 December 2026.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

REGIONS = ("Luzon", "Visayas", "Mindanao")
REGION_CODES = {"Luzon": "CLUZ", "Visayas": "CVIS", "Mindanao": "CMIN"}
#: The profile's prefix ranges (src/adapters/wesm/registry.py REGIONS), restated so this module stays
#: free of the adapter; a test proves the two agree through ``region_of``.
PREFIX_RANGE = {"Luzon": (1, 3), "Visayas": (4, 8), "Mindanao": (9, 14)}
SEED = 20261018
DEFAULT_COUNTS = {
    "accounts": {"Luzon": 4, "Visayas": 3, "Mindanao": 3},
    "nodes": {"Luzon": 5, "Visayas": 5, "Mindanao": 4},
}
KIND_FIXED = "fixed_price"
KIND_TOU = "tou_block"
KINDS = (KIND_FIXED, KIND_TOU)
PEAK_HOURS = list(range(8, 22))
OFFPEAK_HOURS = [h for h in range(24) if h not in PEAK_HOURS]
ALL_HOURS = list(range(24))

NAMES = {
    "Luzon": ("Kawayan Cold Chain", "Bituin Steel Works", "Sampaguita Retail Group", "Lakan Paper Mills"),
    "Visayas": ("Dalisay Bottling", "Mabini Mall Holdings", "Tangub Seafood Cooperative"),
    "Mindanao": ("Banaag Coconut Processing", "Silangan Cement Works", "Hiraya Residential Estates"),
}
# Hour-of-day shape factors, 0..1 of the node's peak; one list of 24 per load shape.
SHAPES = {
    "office": [.35, .33, .32, .32, .33, .38, .5, .68, .86, .96, 1.0, 1.0, .93, .97, 1.0, .98, .93, .84, .7, .56, .46, .41, .38, .36],
    "factory": [.78, .77, .76, .76, .78, .84, .93, 1.0, 1.0, .99, .98, .97, .92, .96, 1.0, .99, .97, .94, .9, .86, .83, .81, .8, .79],
    "cold_chain": [.88, .87, .86, .86, .87, .88, .9, .93, .96, .98, 1.0, 1.0, 1.0, 1.0, 1.0, .99, .97, .95, .93, .92, .91, .9, .89, .88],
    "residential": [.42, .38, .35, .34, .36, .45, .6, .66, .58, .52, .5, .52, .55, .53, .52, .56, .64, .78, .93, 1.0, .99, .92, .75, .56],
}
SHAPE_ORDER = {"Luzon": ("cold_chain", "factory", "office", "factory"),
               "Visayas": ("cold_chain", "office", "cold_chain"),
               "Mindanao": ("factory", "factory", "residential")}
TERM_STARTS = (date(2025, 7, 1), date(2026, 1, 1), date(2026, 4, 1), date(2026, 7, 1))
TERM_MONTHS = (12, 24, 36)
#: No term ends before this day: the data snapshot ends 14 October 2026, so every contract is live then.
TERM_FLOOR = date(2026, 12, 31)
#: The suffix pattern a synthetic alias carries; the tests restate it.
ALIAS_MARK = "SYN"


class Stream:
    """A keyed, version-independent stream of floats in [0, 1)."""

    def __init__(self, seed: int, label: str) -> None:
        self._key = f"{int(seed)}|{label}|".encode()
        self._n = 0

    def unit(self) -> float:
        digest = hashlib.sha256(self._key + str(self._n).encode()).digest()
        self._n += 1
        return int.from_bytes(digest[:8], "big") / 2**64

    def between(self, low: float, high: float) -> float:
        return low + (high - low) * self.unit()

    def pick(self, items):
        return items[int(self.unit() * len(items)) % len(items)]


def _tens(value: float) -> int:
    return int(round(value / 10.0)) * 10


def _last_day_after(start: date, months: int) -> date:
    total = start.year * 12 + (start.month - 1) + months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1) - timedelta(days=1)


def alias_for(region: str, index: int) -> str:
    """The synthetic node alias: region prefix, the SYN mark, a letter pair and a load number."""
    low, high = PREFIX_RANGE[region]
    prefix = low + (index % (high - low + 1))
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    pair = letters[(index * 7 + len(region)) % len(letters)] + letters[(index * 5 + 3) % len(letters)]
    return f"{prefix:02d}{ALIAS_MARK}{pair}_L{index + 1:02d}"


def validate_counts(counts) -> dict:
    out = {}
    for group in ("accounts", "nodes"):
        entry = counts.get(group)
        if not isinstance(entry, dict) or set(entry) != set(REGIONS):
            raise ValueError(f"counts.{group} needs exactly the regions {', '.join(REGIONS)}")
        for region in REGIONS:
            n = entry[region]
            if type(n) is not int or n < 1:
                raise ValueError(f"counts.{group}.{region} must be a whole number of at least 1")
        out[group] = {region: entry[region] for region in REGIONS}
    for region in REGIONS:
        if out["accounts"][region] > len(NAMES[region]):
            raise ValueError(f"at most {len(NAMES[region])} accounts in {region}: the invented name list ends")
        if out["nodes"][region] < out["accounts"][region]:
            raise ValueError(f"{region} needs at least as many nodes as accounts")
        if out["nodes"][region] > 14:
            raise ValueError(f"at most 14 nodes in {region}")
    return out


def generate_rows(seed: int = SEED, counts=None) -> dict:
    """The book's rows: accounts, nodes, contracts, profiles. Every row carries ``synthetic: true``."""
    counts = validate_counts(counts or DEFAULT_COUNTS)
    accounts, nodes, contracts, profiles = [], [], [], []
    for region in REGIONS:
        code = REGION_CODES[region][1:]
        region_accounts = []
        for i in range(counts["accounts"][region]):
            account = {"id": f"ACC-{code}{i + 1:02d}", "name": NAMES[region][i], "region": region,
                       "region_code": REGION_CODES[region],
                       "shape": SHAPE_ORDER[region][i % len(SHAPE_ORDER[region])], "synthetic": True}
            region_accounts.append(account)
            accounts.append(account)
        for j in range(counts["nodes"][region]):
            account = region_accounts[j % len(region_accounts)]
            node = {"id": f"NODE-{code}{j + 1:02d}", "alias": alias_for(region, j), "region": region,
                    "region_code": REGION_CODES[region], "account_id": account["id"], "synthetic": True}
            nodes.append(node)
            stream = Stream(seed, node["id"])
            peak = round(stream.between(6.0, 38.0), 1)
            wobble = Stream(seed, node["id"] + "|profile")
            mw = [round(peak * f * wobble.between(0.96, 1.04), 3) for f in SHAPES[account["shape"]]]
            profiles.append({"id": f"PROF-{node['id'][5:]}", "account_id": account["id"], "node_id": node["id"],
                             "mw_by_hour": mw, "peak_mw": max(mw), "synthetic": True})
            contracts.extend(_contracts_for(seed, node, account, j, mw))
    return {"accounts": accounts, "nodes": nodes, "contracts": contracts, "profiles": profiles}


def _contracts_for(seed, node, account, position, mw):
    stream = Stream(seed, node["id"] + "|contracts")
    # (kind, hours, share range of the lowest demand in those hours). Overlapping contracts take
    # smaller shares, so their sum stays under the node's demand in every hour.
    plan = [(KIND_FIXED, ALL_HOURS, (0.5, 0.85))] if position % 3 == 0 else (
        [(KIND_TOU, PEAK_HOURS, (0.5, 0.85)), (KIND_TOU, OFFPEAK_HOURS, (0.5, 0.85))] if position % 3 == 1
        else [(KIND_FIXED, ALL_HOURS, (0.35, 0.5)), (KIND_TOU, PEAK_HOURS, (0.15, 0.3))])
    out = []
    for n, (kind, hours, share) in enumerate(plan, start=1):
        floor = min(mw[h] for h in hours)
        size = max(0.5, int(floor * stream.between(*share) * 2) / 2)
        if kind == KIND_FIXED:
            price = _tens(stream.between(4800, 6800))
        elif hours == PEAK_HOURS:
            price = _tens(stream.between(6000, 8200))
        else:
            price = _tens(stream.between(3800, 5200))
        start = stream.pick(TERM_STARTS)
        months = stream.pick(TERM_MONTHS)
        end = _last_day_after(start, months)
        while end < TERM_FLOOR:
            months += 12
            end = _last_day_after(start, months)
        out.append({"id": f"CT-{node['id'][5:]}-{n}", "account_id": account["id"], "node_id": node["id"],
                    "kind": kind, "price_php_mwh": price, "mw": size, "hours": list(hours),
                    "term_start": start.isoformat(), "term_end": end.isoformat(), "synthetic": True})
    return out
