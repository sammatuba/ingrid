"""BOOK-4: the book adapter the desk agent's two read actions call.

The agent service (``src/agent/service.py``, DOCK-3) runs ``query_exposure`` and ``query_impact``
through a ``book`` adapter handed in: ``book.exposure(account_ids, node_ids, window, cutoff)`` and
``book.impact(account_ids, outlook_id, ...)``. :class:`BookAdapter` is that adapter over BOOK-2's
functions. It is given the book (the committed synthetic fixture by default), the archive that holds
the vintages (the fixture vintages by default) and a stated materiality policy. It holds no other
state and writes nothing.

* **Exposure.** :meth:`BookAdapter.exposure` answers with :func:`src.book.exposure.exposure` over
  the named accounts and nodes, a window and the question's cutoff.
* **Impact.** :meth:`BookAdapter.impact` resolves the vintage id to its record digest in the archive
  and calls :func:`src.book.impact.query_impact`, which reads the band through ``load_vintage``
  (BOOK-2 review, note C: a band is reached only through the archive). The window must lie inside
  the vintage's horizon and the vintage must be issued at or before the cutoff. The policy is the
  adapter's stated line; there is no default.

Identifiers, never values. A window is named by an identifier ``<start>/<end>`` of two local hours,
half-open (``2026-10-19T13:00/2026-10-19T15:00``), read by :meth:`src.book.exposure.Window.between`;
:func:`window_id` writes it. A cutoff is the question's own cutoff string. A record is named by its
record id, the content digest :func:`src.judgment.view.book_record_id` shows beside every figure:
the impact record's own ``content_digest``, and for the exposure record the canonical digest the
adapter stamps on it (:func:`exposure_record`).

Every answer is a dictionary. An answered query is ``{'status': 'answered', 'kind', 'record_id',
'record', 'synthetic': True, 'label'}`` (an impact answer adds ``vintage``, ``window``, ``cutoff`` and
``materiality``). A refused one is ``{'status': 'refused', 'code', 'reason_key', 'record_id': None,
'synthetic': True, 'label'}`` with BOOK-2's stable code (``VINTAGE_UNKNOWN``,
``WINDOW_OUTSIDE_VINTAGE``, ``WINDOW_OUTSIDE_PROFILE``, ``CUTOFF_BEFORE_TERM_START``,
``VINTAGE_AFTER_CUTOFF``, ``BAND_DIGEST_MISMATCH`` and the rest), its lower-case form as the reason
key and no error text, so nothing of a path or a value leaves the adapter. A window or a cutoff the
service does not pass is refused (``WINDOW_REQUIRED``, ``CUTOFF_REQUIRED``), never defaulted.

Every figure is a method demonstration on the synthetic book; the answer carries the book's label.
Stdlib and repository modules only; no web layer, no network.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from src.contracts.jsonutil import compute_content_digest
from src.outlook.records import OutlookArchive, OutlookError
from src.price.impact import MaterialityPolicy

from .exposure import FIXTURE, ExposureError, Window, exposure, load_book
from .impact import KIND as IMPACT_KIND
from .impact import BookImpactError, query_impact
from .records import LABEL, BookError, validate_book

#: The committed fixture vintages' archive (BOOK-2, ``scripts/book/vintages.py``).
FIXTURE_ARCHIVE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "book" / "vintages"
EXPOSURE_KIND = "BookExposure"
#: The separator of a window identifier's two hours.
WINDOW_SEPARATOR = "/"


class AdapterError(BookError):
    """A query the adapter refuses before BOOK-2 is called; ``code`` is stable."""


def window_id(window: Window) -> str:
    """The identifier of a window: its first hour and its end hour, local, half-open."""
    if not isinstance(window, Window):
        raise AdapterError("WINDOW_INVALID", "not a Window")
    start = window.hours[0]
    end = window.hours[-1] + timedelta(hours=1)
    return start.strftime("%Y-%m-%dT%H:%M") + WINDOW_SEPARATOR + end.strftime("%Y-%m-%dT%H:%M")


def parse_window(value) -> Window:
    """A window from its identifier (or a Window as it is); anything else is refused."""
    if isinstance(value, Window):
        return value
    if value is None:
        raise AdapterError("WINDOW_REQUIRED", "the query names no window")
    if type(value) is not str or value.count(WINDOW_SEPARATOR) != 1:
        raise AdapterError("WINDOW_INVALID", "a window is two hours joined by a slash")
    start, end = value.split(WINDOW_SEPARATOR)
    return Window.between(start, end)


def _cutoff(value):
    if value is None:
        raise AdapterError("CUTOFF_REQUIRED", "the query names no cutoff")
    if type(value) is not str or not value.strip():
        raise AdapterError("CUTOFF_INVALID", "the cutoff is not text")
    return value


def _ids(value, what):
    if type(value) not in (list, tuple) or not value or any(type(v) is not str or not v for v in value):
        raise AdapterError("ARGUMENT_INVALID", f"{what} must be a non-empty list of identifiers")
    return list(value)


def stamp_exposure(record: dict) -> dict:
    """The exposure record with its canonical ``content_digest``, the record id the view shows."""
    stamped = dict(record)
    stamped.pop("content_digest", None)
    stamped["content_digest"] = compute_content_digest(stamped)
    return stamped


class BookAdapter:
    """The ``book`` adapter: the two queries over a book, an archive of vintages and a stated line."""

    synthetic = True
    label = LABEL

    def __init__(self, policy, book=None, archive_root=FIXTURE_ARCHIVE):
        if not isinstance(policy, MaterialityPolicy):
            raise BookImpactError("POLICY_REQUIRED", type(policy).__name__)
        self.policy = policy
        self.book = load_book(FIXTURE) if book is None else book
        validate_book(self.book)
        self.archive_root = Path(archive_root)

    # --- the records the composer is handed --------------------------------------------

    def exposure_record(self, window, cutoff, accounts=None, nodes=None, region=None) -> dict:
        """The exposure record of a window and cutoff, stamped with its record id (raises)."""
        return stamp_exposure(exposure(self.book, parse_window(window), _cutoff(cutoff),
                                       accounts=accounts, nodes=nodes, region=region))

    def vintage_digest(self, outlook_id: str) -> str:
        """The record digest of a vintage in the archive, by id (raises ``VINTAGE_UNKNOWN``)."""
        if type(outlook_id) is not str or not outlook_id:
            raise BookImpactError("VINTAGE_UNKNOWN", "no vintage id")
        try:
            return OutlookArchive(self.archive_root).outlook(outlook_id)["content_digest"]
        except OutlookError as error:
            code = "VINTAGE_UNKNOWN" if error.code == "OUTLOOK_UNKNOWN" else "VINTAGE_NOT_A_RECORD"
            raise BookImpactError(code, repr(outlook_id)) from None

    def vintages(self) -> list:
        """The archive's issued vintages, as the composer's outlook record lists them."""
        archive = OutlookArchive(self.archive_root)
        return [archive.outlook(outlook_id) for outlook_id in archive.issue_ids()]

    def impact_record(self, outlook_id, window, cutoff, accounts=None) -> dict:
        """The impact record against a vintage named by id, through the archive (raises)."""
        return query_impact(self.book, self.archive_root, outlook_id, self.vintage_digest(outlook_id),
                            parse_window(window), _cutoff(cutoff), self.policy, accounts=accounts)

    def manifest_ids(self, exposure_record=None, windows=()) -> dict:
        """The identifiers the composer's action manifest offers for the book, never a value.

        With an exposure record: its accounts, its nodes and its window. Without one: every account
        and node of the book. ``windows`` adds window identifiers (or Windows). The vintage ids reach
        the manifest through the outlook record the composer is handed (:meth:`vintages`).
        """
        if exposure_record is not None:
            accounts = [block["account_id"] for block in exposure_record["accounts"]]
            nodes = list(dict.fromkeys(row["node_id"] for row in exposure_record["rows"]))
            found = [window_id(Window.between(*_window_bounds(exposure_record["window"])))]
        else:
            accounts = [account["id"] for account in self.book["accounts"]]
            nodes = [node["id"] for node in self.book["nodes"]]
            found = []
        for window in windows:
            # Round-trip every window through its parser (BOOK-4 rework round 1, finding 4):
            # anything that is not a window identifier is refused, never passed through.
            identifier = window_id(parse_window(window))
            if type(window) is str and identifier != window:
                raise AdapterError("WINDOW_INVALID", "not a window identifier")
            if identifier not in found:
                found.append(identifier)
        ids = {"accounts": accounts, "nodes": nodes}
        if found:
            ids["windows"] = found
        return ids

    # --- the two queries the agent service runs ------------------------------------------

    def _answer(self, kind, record, **extra) -> dict:
        record_id = record["content_digest"]
        return dict({"status": "answered", "kind": kind, "record_id": record_id, "record": record,
                     "synthetic": True, "label": record["label"]}, **extra)

    def _refused(self, error) -> dict:
        code = getattr(error, "code", "QUERY_REFUSED")
        return {"status": "refused", "code": code, "reason_key": code.lower(), "record_id": None,
                "synthetic": True, "label": self.label}

    def exposure(self, account_ids, node_ids, window, cutoff) -> dict:
        """``query_exposure``: the uncovered MWh of the named accounts and nodes over a window."""
        try:
            record = self.exposure_record(window, cutoff, accounts=_ids(account_ids, "account_ids"),
                                          nodes=_ids(node_ids, "node_ids"))
        except (BookError, ExposureError) as error:
            return self._refused(error)
        return self._answer(EXPOSURE_KIND, record)

    def impact(self, account_ids, outlook_id, window=None, cutoff=None) -> dict:
        """``query_impact``: p10, p50 and p90 PHP per account against a vintage named by id."""
        try:
            accounts = _ids(account_ids, "account_ids")
            parsed, stated = parse_window(window), _cutoff(cutoff)
            record = self.impact_record(outlook_id, parsed, stated, accounts=accounts)
        except (BookError, ExposureError) as error:
            return self._refused(error)
        vintage = record["vintage"]
        return self._answer(IMPACT_KIND, record,
                            vintage={"outlook_id": vintage["outlook_id"],
                                     "outlook_digest": vintage["outlook_digest"],
                                     "values_sha256": vintage["values_sha256"]},
                            window=window_id(parsed), cutoff=stated,
                            materiality=record["materiality"])


def _window_bounds(window: dict) -> tuple:
    """The two local hours of a record's window block (``src.book.exposure.Window.to_dict``)."""
    day = window["day"]
    start = f"{day}T{window['start_hour']:02d}:00"
    last = window["last_day"]
    if window["end_hour"] == 24:
        end_day = (date.fromisoformat(last) + timedelta(days=1)).isoformat()
        return start, f"{end_day}T00:00"
    return start, f"{last}T{window['end_hour']:02d}:00"


__all__ = ["AdapterError", "BookAdapter", "EXPOSURE_KIND", "FIXTURE_ARCHIVE", "WINDOW_SEPARATOR",
           "parse_window", "stamp_exposure", "window_id"]
