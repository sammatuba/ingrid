"""Change-only run builder for the registered-capacity register (company copy).

Rows are JSON lines from ``grid_raw.ext_others_regcap_generation``, exported by
``scripts/data/wesm/export.sh`` (orchestrator seat). The actual copy columns are
``trading_day_id, tp_name, resource_name, maximum_capacity, byear, bmonth``; the
source profile's labels (``trading_day``, ``participant``, ``capacity_mw``,
``resource_type``, ``region``) are read onto them: ``tp_name`` is the trading
participant, ``maximum_capacity`` the registered maximum in MW, and the region is
derived from the resource-name prefix (01-03 Luzon, 04-08 Visayas, 09-14
Mindanao), never guessed. This module reads local bytes only.

Rules fixed by ``docs/work/real-sources/intent.md`` and the source profile
``docs/work/foundation-review-2026-10-13/sources/02-registered-capacity.md``:

* change-only versions: consecutive trading days with the same
  ``(participant, maximum_capacity)`` for one resource form one run. A run is one
  ``SourceVersion`` whose ``original_text`` is the canonical JSON of the run
  (first day, last day, the register fields) and whose ``known_at`` is the first
  trading day at 00:00 +08:00 with a ``feed_logged_at`` basis. The copy carries
  no publication instant, so ``published_at`` repeats the stamp and is labelled
  ``published_at_approximate: true`` — an approximation, never a stated
  publication (owner ruling, round 9);
* every run yields one ``MappingRevision`` candidate with one ``GeneratingUnit``
  entity, ``cardinality: one_to_one``, ``valid_period`` the run's days as a
  half-open date interval, ``status: unreviewed``, and ``representation_id`` and
  ``input_field`` supplied by the case — the register supplies the unit, not the
  model;
* a resource under two participants on the same day yields two candidates and
  both are ``ambiguous``: the free-text identity step cannot choose between them;
* the 2025 hole (2024-10-26 to 2026-02-04 in this copy) is a gap in runs, not a
  run: the same triple on either side is two versions, and nothing is
  interpolated;
* a resource outside the region map, a row without the export columns and a
  malformed trading day are refused (``MALFORMED_ROW``) and counted in the
  export report, never repaired.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta

from src.contracts.jsonutil import canonical_dumps
from src.review.records import make_record, reference

#: The signed permission record every record produced here cites.
PERMISSION_REF = "perm:wesm-company-copy:2026-10-13"
PUBLISHER = "IEMOP WESM market data copy"
BASIS_REF = "grid_raw.ext_others_regcap_generation.trading_day_id"
BASIS_NOTE = "Asia/Manila, measured 2026-10-13"
SOURCE_TABLE = "grid_raw.ext_others_regcap_generation"
MANILA_OFFSET = "+08:00"

COLUMNS = ("trading_day_id", "tp_name", "resource_name", "maximum_capacity", "byear", "bmonth")
RESOURCE = re.compile(r"^(?P<prefix>[0-9]{2})[A-Z0-9]+_[A-Z0-9]+$")
REGIONS = (("Luzon", 1, 3), ("Visayas", 4, 8), ("Mindanao", 9, 14))


class RegisterError(ValueError):
    """A refused row; the code is stable and the detail names the row."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code)


@dataclass(frozen=True)
class RegisterRun:
    """One change-only run: the facts and the identity of its two records."""

    resource_name: str
    participant: str
    capacity_mw: str
    region: str
    first_day: date
    last_day: date
    days: int
    status: str  # "unreviewed" or "ambiguous"

    @property
    def source_id(self):
        return "regcap:%s:%s:%s:%s" % (self.resource_name, self.participant, self.capacity_mw,
                                       self.first_day.isoformat())

    @property
    def mapping_id(self):
        return "mapping:" + self.source_id

    @property
    def valid_period(self):
        """The run's days as a half-open date interval: the day after the last day."""
        return {"start": self.first_day.isoformat(), "end": (self.last_day + timedelta(days=1)).isoformat()}

    def fields(self):
        """The register fields the run carries, first and last day included."""
        return {"resource_name": self.resource_name, "tp_name": self.participant,
                "maximum_capacity": self.capacity_mw, "region": self.region,
                "first_day": self.first_day.isoformat(), "last_day": self.last_day.isoformat(),
                "trading_days": self.days}


def region_of(resource_name):
    """The resource-name prefix's region per the profile; ``None`` when outside it."""
    match = RESOURCE.fullmatch(resource_name)
    if match is None:
        return None
    prefix = int(match.group("prefix"))
    for region, first, last in REGIONS:
        if first <= prefix <= last:
            return region
    return None


def day_of(value):
    """The trading day of a copy stamp (``YYYY-MM-DD`` or with a time part)."""
    text = value.strip() if type(value) is str else ""
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}:\d{2})?", text)
    if match is None:
        raise RegisterError("MALFORMED_ROW", "trading day is not a copy stamp: %r" % (value,))
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        raise RegisterError("MALFORMED_ROW", "trading day is not a calendar date: %r" % (value,)) from None


def _read_row(row):
    if type(row) is not dict or any(column not in row for column in COLUMNS):
        raise RegisterError("MALFORMED_ROW", "row does not carry the export columns")
    resource = row["resource_name"]
    participant = row["tp_name"]
    capacity = row["maximum_capacity"]
    if not (type(resource) is str and type(participant) is str
            and type(capacity) is str and participant.strip() and capacity.strip()):
        raise RegisterError("MALFORMED_ROW", "resource, participant or capacity is missing")
    region = region_of(resource)
    if region is None:
        raise RegisterError("MALFORMED_ROW", "resource prefix outside the region map: %s" % resource)
    return resource, participant, capacity, region, day_of(row["trading_day_id"])


def build_runs(rows):
    """Build the change-only runs of an export; returns ``(runs, rejected)``.

    Rows that agree completely on (resource, day, participant, capacity) collapse:
    the copy repeats a day at a billing-month boundary. A day carrying two
    participants marks every run that covers it ``ambiguous``.
    """
    grouped, ambiguous, rejected = {}, {}, []
    for row in rows:
        try:
            resource, participant, capacity, region, day = _read_row(row)
        except RegisterError as exc:
            rejected.append((row if type(row) is dict else {"row": row}, exc.code, exc.detail))
            continue
        grouped.setdefault((resource, participant, capacity, region), set()).add(day)
        ambiguous.setdefault(resource, {}).setdefault(day, set()).add(participant)
    flagged = {resource: {day for day, participants in per_day.items() if len(participants) > 1}
               for resource, per_day in ambiguous.items()}
    runs = []
    for (resource, participant, capacity, region) in sorted(grouped):
        days = sorted(grouped[(resource, participant, capacity, region)])
        start = previous = days[0]
        spans = []
        for day in days[1:]:
            if day != previous + timedelta(days=1):
                spans.append((start, previous))
                start = day
            previous = day
        spans.append((start, previous))
        for first, last in spans:
            span_days = (last - first).days + 1
            status = "ambiguous" if any(first + timedelta(days=offset) in flagged[resource]
                                        for offset in range(span_days)) else "unreviewed"
            runs.append(RegisterRun(resource_name=resource, participant=participant, capacity_mw=capacity,
                                    region=region, first_day=first, last_day=last, days=span_days,
                                    status=status))
    return tuple(runs), tuple(rejected)


def source_payload(run, permission_ref=PERMISSION_REF):
    """The run's SourceVersion payload; ``original_text`` is the canonical run JSON."""
    text = canonical_dumps(run.fields())
    data = text.encode("utf-8")
    stamp = run.first_day.isoformat() + "T00:00:00" + MANILA_OFFSET
    return {
        "source_id": run.source_id,
        "source_version": "1",
        "lineage_id": run.source_id,
        "publisher": PUBLISHER,
        "access_policy_ref": permission_ref,
        "original_text": text,
        "source_byte_digest": hashlib.sha256(data).hexdigest(),
        # The copy carries no separate publication instant; the run's first
        # trading-day stamp is the only time the row itself records. It is kept
        # as the stand-in the record requires and labelled an approximation,
        # never a stated publication (owner ruling, round 9).
        "published_at": stamp,
        "published_at_approximate": True,
        "known_at": stamp,
        "availability_basis": {"basis_kind": "feed_logged_at", "basis_ref": BASIS_REF, "note": BASIS_NOTE},
        "unknown_reason": None,
        "copied_from": None,
        "synthetic": False,
        "permission_ref": permission_ref,
    }


def mapping_payload(run, source_record, *, representation_id, input_field, permission_ref=PERMISSION_REF):
    """The run's unreviewed MappingRevision candidate over its SourceVersion."""
    if not (type(representation_id) is str and representation_id.strip()
            and type(input_field) is str and input_field.strip()):
        raise RegisterError("MALFORMED_ROW", "representation_id and input_field are supplied by the case")
    return {
        "entities": [{"entity_id": run.resource_name, "entity_type": "GeneratingUnit"}],
        "representation_id": representation_id,
        "input_field": input_field,
        "cardinality": "one_to_one",
        "valid_period": run.valid_period,
        "status": run.status,
        "reviewer": None,
        "reviewed_at": None,
        "source_refs": [reference(source_record)],
        "synthetic": False,
        "permission_ref": permission_ref,
    }


def records(runs, tenant_id, case_id, recorded_at, *, representation_id, input_field, permissions=None):
    """Build the h0.v2 records for runs: one SourceVersion and one candidate each."""
    built = []
    for run in runs:
        source = make_record("SourceVersion", tenant_id, case_id, run.source_id, "1",
                             recorded_at, source_payload(run), permissions=permissions)
        built.append(source)
        built.append(make_record("MappingRevision", tenant_id, case_id, run.mapping_id, "1", recorded_at,
                                 mapping_payload(run, source, representation_id=representation_id,
                                                 input_field=input_field), permissions=permissions))
    return built


def main(argv=None):
    """``python3 -m src.adapters.wesm.registry FILE.jsonl`` prints run counts."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: registry.py FILE.jsonl")
    with open(argv[0], encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    runs, rejected = build_runs(rows)
    print(json.dumps({
        "source": SOURCE_TABLE,
        "permission_ref": PERMISSION_REF,
        "counts": {"rows": len(rows), "rejected": len(rejected), "runs": len(runs),
                   "resources": len({run.resource_name for run in runs}),
                   "unreviewed": sum(1 for run in runs if run.status == "unreviewed"),
                   "ambiguous": sum(1 for run in runs if run.status == "ambiguous")},
        "rejected": [{"code": code, "detail": detail} for _, code, detail in rejected],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
