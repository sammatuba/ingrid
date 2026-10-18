"""BOOK-2: the uncovered volume of the synthetic book per account, node and hour.

Every figure here comes from the synthetic book (``tests/fixtures/book/book-v1.json``, BOOK-1) and is
a method demonstration. No account, contract, node or volume in it is real.

The rule, in words
==================
* The book is validated first (:func:`src.book.records.validate_book`): a record whose digest does
  not recompute, or a row without ``synthetic: true``, is refused before any figure is read.
* A **window** is part of one local day, a half-open range of clock hours ``[start_hour, end_hour)``
  with ``0 <= start_hour < end_hour <= 24``, or a run of whole days from one local midnight to a later
  one. The clock is the price target contract's: naive Asia/Manila hours (UTC+8, no daylight saving).
  The book's demand profile is one 24-hour day, read at each hour's clock hour and repeated once per day
  of the window, as IMPACT-1 reads its profile. A window that crosses a midnight inside a day (23:00 to
  01:00, or 13:00 to 15:00 the next day) reaches outside the profile's day and is refused
  (``WINDOW_OUTSIDE_PROFILE``). It is never wrapped. (Orchestrator decision at the BOOK-2 review.)
* A **cutoff** is the information cutoff of the question: a date or an instant, read as the local date.
  The book records when a contract's term starts, not when the contract was signed. A cutoff before
  the term start of a contract in the question's scope is therefore refused
  (``CUTOFF_BEFORE_TERM_START``), naming the contract. The book cannot say whether that contract was
  known at the cutoff, and the answer does not guess.
* A contract **covers** a node and an hour when the contract is on that node, the hour's clock hour is
  one of its ``hours`` and the hour's own date lies inside ``[term_start, term_end]``. A fixed-price
  contract lists all 24 hours. A time-of-use block lists its own hours.
* **Uncovered MWh** of one node and one hour is ``max(0, demand MW - contracted MW)`` times one hour.
  It is never negative. Contracted MW above demand is reported as ``over_contracted_mw`` and is not
  netted against another hour or node. Each row names the contracts that cover it.
* An account's figure is the sum of its nodes' rows. Figures are rounded to three decimals, the
  precision of the profile, so the written-out arithmetic in the tests is exact.
* The **affected part of the book** for a region and window is every account and node of that region,
  their covering contracts and their exposure rows (:func:`affected_part`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import generate as gen
from .records import LABEL, BookError, validate_book

KIND = "BookExposure"
VERSION = "book-exposure-1"
#: The price target contract's clock: naive Asia/Manila hours, one fixed offset.
MANILA = timezone(timedelta(hours=8))
CLOCK = "naive Asia/Manila local hours (UTC+8, no daylight saving), the price target contract's clock"
FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "book" / "book-v1.json"
DECIMALS = 3

#: The method strings go into every record, and the book page shows them. They follow the site's
#: plain-language rules: short active sentences, no semicolons, no banned words.
METHOD_UNCOVERED = (
    "Uncovered MWh for a node and hour is demand MW minus covering contract MW, times one hour. "
    "It is never below zero. An account's figure is the sum of its nodes."
)
METHOD_COVER = (
    "A contract covers a node and hour when it is on that node and lists that clock hour. "
    "The contract must be in term on the hour's own date. A fixed-price contract lists all 24 hours. "
    "A time-of-use block lists its own hours."
)
METHOD_PROFILE = (
    "The book holds one 24-hour demand profile per node. Each window hour reads the profile at its clock "
    "hour. A window of whole days repeats the profile once per day, as IMPACT-1 does. The book refuses a "
    "window that crosses a midnight inside a day."
)
METHOD_CUTOFF = (
    "The book records the day a contract term starts, not the day of signing. The book refuses a cutoff "
    "before the term start of a contract in scope. It cannot say if anyone knew that contract then."
)


class ExposureError(BookError):
    """A refused exposure question; ``code`` is stable and names the rule that refused it."""


# --- the window and the cutoff ----------------------------------------------


@dataclass(frozen=True)
class Window:
    """Local clock hours: part of one day, or a run of whole days.

    ``Window(day, start_hour, end_hour)`` is one day and a half-open range of its clock hours.
    ``Window(day, 0, 24, days=n)`` is ``n`` whole days from ``day``. A window of several days must
    start and end at local midnight. The 24-hour profile then repeats once per day, as IMPACT-1 reads
    it (``docs/work/price-outlook/impact.md``, "read by clock hour"). Any other window that crosses a
    midnight reaches outside the profile's day and is refused.
    """

    day: date
    start_hour: int
    end_hour: int
    days: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.day, date) or isinstance(self.day, datetime):
            raise ExposureError("WINDOW_INVALID", "the day is not a date")
        for name in ("start_hour", "end_hour", "days"):
            value = getattr(self, name)
            if type(value) is not int:
                raise ExposureError("WINDOW_INVALID", f"{name} is not a whole number")
        if self.days < 1:
            raise ExposureError("WINDOW_INVALID", "a window holds at least one day")
        if not (0 <= self.start_hour <= 23 and 1 <= self.end_hour <= 24):
            raise ExposureError("WINDOW_OUTSIDE_PROFILE",
                                f"hours {self.start_hour} to {self.end_hour} reach outside the profile's day")
        if self.start_hour >= self.end_hour:
            raise ExposureError("WINDOW_INVALID", "the window is empty or runs backwards")
        if self.days > 1 and (self.start_hour, self.end_hour) != (0, 24):
            raise ExposureError("WINDOW_OUTSIDE_PROFILE",
                                "a window of several days must start and end at local midnight")

    @classmethod
    def between(cls, start: str, end: str) -> "Window":
        """The window from two hour instants, half-open: ``[start, end)``.

        An instant without an offset is a local hour. An offset-bearing instant is converted to local
        time first. Inside one day any hours are allowed, and the next day's 00:00 may close the day.
        From one local midnight to a later one is a run of whole days. Any other window that crosses a
        midnight reaches outside the profile's day and is refused.
        """
        first, last = _local_hour(start), _local_hour(end)
        if last <= first:
            raise ExposureError("WINDOW_INVALID", "the window is empty or runs backwards")
        if last.date() == first.date():
            return cls(first.date(), first.hour, last.hour)
        if last == datetime.combine(first.date() + timedelta(days=1), datetime.min.time()):
            return cls(first.date(), first.hour, 24)
        if first.hour == 0 and last.hour == 0:
            return cls(first.date(), 0, 24, days=(last.date() - first.date()).days)
        raise ExposureError("WINDOW_OUTSIDE_PROFILE", "the window crosses a midnight inside a day")

    @property
    def clock_hours(self) -> tuple[int, ...]:
        """The clock hours of one day of the window."""
        return tuple(range(self.start_hour, self.end_hour))

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(self.day + timedelta(days=n) for n in range(self.days))

    @property
    def hours(self) -> tuple[datetime, ...]:
        """The naive local hour starts of the window, in order, day by day."""
        return tuple(datetime.combine(d, datetime.min.time()) + timedelta(hours=h)
                     for d in self.dates for h in self.clock_hours)

    def to_dict(self) -> dict:
        return {"day": self.day.isoformat(), "last_day": self.dates[-1].isoformat(), "days": self.days,
                "start_hour": self.start_hour, "end_hour": self.end_hour, "hours": len(self.hours),
                "clock": CLOCK}


def _local_hour(value: str) -> datetime:
    if type(value) is not str:
        raise ExposureError("WINDOW_INVALID", "an hour is not text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ExposureError("WINDOW_INVALID", "an hour does not parse") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(MANILA).replace(tzinfo=None)
    if (parsed.minute, parsed.second, parsed.microsecond) != (0, 0, 0):
        raise ExposureError("WINDOW_INVALID", "an hour is not on the hour")
    return parsed


def cutoff_date(cutoff) -> date:
    """The cutoff as a local date: a ``date``, an ISO date, or an instant (naive is local)."""
    if isinstance(cutoff, datetime):
        return (cutoff.astimezone(MANILA) if cutoff.tzinfo else cutoff).date()
    if isinstance(cutoff, date):
        return cutoff
    if type(cutoff) is not str:
        raise ExposureError("CUTOFF_INVALID", "the cutoff is not a date or an instant")
    try:
        if len(cutoff) == 10:
            return date.fromisoformat(cutoff)
        parsed = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    except ValueError:
        raise ExposureError("CUTOFF_INVALID", "the cutoff does not parse") from None
    return (parsed.astimezone(MANILA) if parsed.tzinfo else parsed).date()


def cutoff_close(cutoff) -> datetime:
    """The instant a cutoff closes, in UTC.

    An instant closes at itself (a naive instant is local). A date closes at the next local midnight,
    so the whole of that Manila day is inside the cutoff.
    """
    if isinstance(cutoff, datetime):
        moment = cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=MANILA)
        return moment.astimezone(timezone.utc)
    if isinstance(cutoff, date) or (type(cutoff) is str and len(cutoff) == 10):
        day = cutoff_date(cutoff)
        return datetime.combine(day + timedelta(days=1), datetime.min.time(), MANILA).astimezone(timezone.utc)
    if type(cutoff) is not str:
        raise ExposureError("CUTOFF_INVALID", "the cutoff is not a date or an instant")
    try:
        moment = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    except ValueError:
        raise ExposureError("CUTOFF_INVALID", "the cutoff does not parse") from None
    return (moment if moment.tzinfo else moment.replace(tzinfo=MANILA)).astimezone(timezone.utc)


# --- the book -----------------------------------------------------------------


def load_book(path: str | Path = FIXTURE) -> dict:
    """Read and validate a book record; the committed fixture by default."""
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise ExposureError("BOOK_UNREADABLE", Path(path).name) from None
    validate_book(record)
    return record


def book_reference(book: dict) -> dict:
    return {"version": book["version"], "content_digest": book["content_digest"], "label": book["label"]}


def region_name(region: str) -> str:
    """``Visayas`` or ``CVIS`` to ``Visayas``; anything else is refused."""
    for name, code in gen.REGION_CODES.items():
        if region in (name, code):
            return name
    raise ExposureError("UNKNOWN_REGION", repr(region))


def scope(book: dict, accounts=None, nodes=None, region=None) -> list[dict]:
    """The nodes a question covers, in book order; unknown ids are refused, never skipped."""
    by_account = {a["id"]: a for a in book["accounts"]}
    by_node = {n["id"]: n for n in book["nodes"]}
    for account_id in accounts or ():
        if account_id not in by_account:
            raise ExposureError("UNKNOWN_ACCOUNT", repr(account_id))
    for node_id in nodes or ():
        if node_id not in by_node:
            raise ExposureError("UNKNOWN_NODE", repr(node_id))
    name = region_name(region) if region is not None else None
    chosen = [n for n in book["nodes"]
              if (not accounts or n["account_id"] in accounts)
              and (not nodes or n["id"] in nodes)
              and (name is None or n["region"] == name)]
    if not chosen:
        raise ExposureError("EMPTY_SCOPE", "no node of the book matches the question")
    return chosen


def check_cutoff(book: dict, node_ids, cutoff) -> date:
    """Refuse a cutoff before the term start of any contract on the nodes in scope."""
    day = cutoff_date(cutoff)
    wanted = set(node_ids)
    for contract in book["contracts"]:
        if contract["node_id"] in wanted and day < date.fromisoformat(contract["term_start"]):
            raise ExposureError("CUTOFF_BEFORE_TERM_START",
                                f"{contract['id']} starts {contract['term_start']}, after the cutoff {day.isoformat()}")
    return day


def covering(book: dict, node_id: str, hour_start: datetime) -> list[dict]:
    """The contracts on this node that cover this local hour, in book order.

    The hour's own date is checked against each term, so a window of several days drops a contract on
    the days after its term ends.
    """
    day = hour_start.date()
    return [c for c in book["contracts"]
            if c["node_id"] == node_id and hour_start.hour in c["hours"]
            and date.fromisoformat(c["term_start"]) <= day <= date.fromisoformat(c["term_end"])]


def _round(value: float) -> float:
    return round(value + 0.0, DECIMALS) + 0.0


def exposure_row(book: dict, node: dict, hour_start: datetime) -> dict:
    """One node and one local hour: demand, contracted MW, uncovered MWh and the covering contracts.

    The demand is the node's 24-hour profile read at the hour's clock hour.
    """
    clock_hour = hour_start.hour
    profile = next(p for p in book["profiles"] if p["node_id"] == node["id"])
    demand = profile["mw_by_hour"][clock_hour]
    contracts = covering(book, node["id"], hour_start)
    contracted = _round(sum(c["mw"] for c in contracts))
    return {
        "account_id": node["account_id"],
        "node_id": node["id"],
        "region": node["region"],
        "region_code": node["region_code"],
        "hour_start": hour_start.isoformat(),
        "clock_hour": clock_hour,
        "demand_mw": demand,
        "contracted_mw": contracted,
        "uncovered_mwh": _round(max(0.0, demand - contracted)),
        "over_contracted_mw": _round(max(0.0, contracted - demand)),
        "covering_contracts": [{"id": c["id"], "kind": c["kind"], "mw": c["mw"],
                                "price_php_mwh": c["price_php_mwh"]} for c in contracts],
        "synthetic": True,
        "label": LABEL,
    }


def _account_block(account: dict, rows: list[dict]) -> dict:
    return {
        "account_id": account["id"],
        "name": account["name"],
        "region": account["region"],
        "region_code": account["region_code"],
        "nodes": sorted({r["node_id"] for r in rows}),
        "demand_mwh": _round(sum(r["demand_mw"] for r in rows)),
        "covered_mwh": _round(sum(min(r["contracted_mw"], r["demand_mw"]) for r in rows)),
        "uncovered_mwh": _round(sum(r["uncovered_mwh"] for r in rows)),
        "synthetic": True,
        "label": LABEL,
    }


def exposure(book: dict, window: Window, cutoff, accounts=None, nodes=None, region=None) -> dict:
    """The exposure record of a window and cutoff: one row per account, node and hour.

    ``accounts``, ``nodes`` and ``region`` narrow the scope; with none, the whole book is in scope.
    The cutoff is checked against every contract on the nodes in scope before any row is built.
    """
    validate_book(book)
    if not isinstance(window, Window):
        raise ExposureError("WINDOW_INVALID", "the window is not a Window")
    chosen = scope(book, accounts, nodes, region)
    day = check_cutoff(book, [n["id"] for n in chosen], cutoff)
    rows = [exposure_row(book, node, hour) for node in chosen for hour in window.hours]
    by_account = {a["id"]: a for a in book["accounts"]}
    account_ids = list(dict.fromkeys(n["account_id"] for n in chosen))
    blocks = [_account_block(by_account[a], [r for r in rows if r["account_id"] == a]) for a in account_ids]
    return {
        "kind": KIND,
        "version": VERSION,
        "synthetic": True,
        "label": LABEL,
        "book": book_reference(book),
        "window": window.to_dict(),
        "cutoff": day.isoformat(),
        "method": {"uncovered": METHOD_UNCOVERED, "cover": METHOD_COVER, "profile": METHOD_PROFILE,
                   "cutoff": METHOD_CUTOFF},
        "units": {"demand_mw": "MW, a method demonstration", "uncovered_mwh": "MWh, a method demonstration"},
        "rows": rows,
        "accounts": blocks,
        "totals": {"uncovered_mwh": _round(sum(r["uncovered_mwh"] for r in rows)),
                   "rows": len(rows), "synthetic": True, "label": LABEL},
    }


def account_hour(book: dict, account_id: str, hour_start: str, cutoff) -> dict:
    """The uncovered volume of one account for one hour, as one call.

    ``hour_start`` names the hour (a local hour, or an instant with an offset). The answer is the
    account block of a one-hour window with its node rows under ``rows``.
    """
    first = _local_hour(hour_start)
    window = Window(first.date(), first.hour, first.hour + 1)
    record = exposure(book, window, cutoff, accounts=[account_id])
    block = dict(record["accounts"][0])
    block["hour_start"] = first.isoformat()
    block["cutoff"] = record["cutoff"]
    block["book"] = record["book"]
    block["rows"] = record["rows"]
    return block


def affected_part(book: dict, region: str, window: Window, cutoff) -> dict:
    """The affected part of the book for an event's region and window.

    Every account and node of the region, the contracts that cover any of the window's hours, and the
    exposure record of that region and window. The region is a name (``Visayas``) or a code (``CVIS``).
    """
    record = exposure(book, window, cutoff, region=region)
    node_ids = {r["node_id"] for r in record["rows"]}
    contract_ids = sorted({c["id"] for r in record["rows"] for c in r["covering_contracts"]})
    return {
        "kind": "BookAffectedPart",
        "version": VERSION,
        "synthetic": True,
        "label": LABEL,
        "region": region_name(region),
        "region_code": gen.REGION_CODES[region_name(region)],
        "accounts": [a["account_id"] for a in record["accounts"]],
        "nodes": sorted(node_ids),
        "contracts": contract_ids,
        "exposure": record,
    }


__all__ = ["CLOCK", "ExposureError", "FIXTURE", "KIND", "MANILA", "VERSION", "Window", "account_hour",
           "affected_part", "book_reference", "check_cutoff", "covering", "cutoff_close", "cutoff_date", "exposure",
           "exposure_row", "load_book", "region_name", "scope"]
