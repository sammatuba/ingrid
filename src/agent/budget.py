"""The day meter: live planner calls charged to the Manila day, refused past about 5 USD.

Owner decision 13 (strategy 2026-10-18): live access for signed-in users only, under a budget of
about 5 USD a day. The meter charges one stated per-call estimate for each live planner call before
the call is made; a call that would pass the day's line is refused. A refusal is an outcome the dock
shows ("the day's live budget is spent; the answer is from the recorded plans"), never an exception
to the page: `charge` returns the outcome in every case, including a store that cannot be reached.

The per-call figure is an estimate the meter states, not a measured cost; the receipt of a live run
(DOCK-4) records the measured one. The Manila day is UTC+8 (no daylight saving in the Philippines).
Nothing here logs.
"""
from datetime import datetime, timedelta, timezone

MANILA = timezone(timedelta(hours=8))
DAY_LINE_USD = 5.0
#: Stated estimate for one planner call (one wording, flash model, thinking budget zero): an
#: upper reading for a request of a few thousand tokens and a bounded plan. Not a measured cost.
PER_CALL_USD = 0.02

ALLOWED, REFUSED = 'allowed', 'refused'
BUDGET_EXHAUSTED = 'budget_exhausted'
BUDGET_UNAVAILABLE = 'budget_unavailable'


def manila_day(instant):
    """The Manila calendar day (`YYYY-MM-DD`) of an offset-bearing ISO instant."""
    parsed = datetime.fromisoformat(instant.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('an instant with an offset is required')
    return parsed.astimezone(MANILA).date().isoformat()


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class DayMeter:
    def __init__(self, store, line_usd=DAY_LINE_USD, per_call_usd=PER_CALL_USD, clock=_utc_now):
        self.store, self.line_usd, self.per_call_usd, self.clock = store, float(line_usd), float(per_call_usd), clock

    def estimate(self, calls=1):
        return round(self.per_call_usd * calls, 6)

    def _outcome(self, outcome, day, doc, reason_key, calls):
        doc = doc or {'day': day, 'calls': 0, 'usd_estimate': 0.0}
        return {'outcome': outcome, 'refused': outcome == REFUSED, 'reason_key': reason_key, 'day': day,
                'calls': doc['calls'],
                'usd_estimate': doc['usd_estimate'], 'line_usd': self.line_usd,
                'call_usd': self.per_call_usd, 'calls_asked': calls}

    def charge(self, calls=1):
        """Charge `calls` live calls to today's line as one batch; refuse the batch that passes it.

        Returns the outcome `{outcome, reason_key, day, calls, usd_estimate, line_usd, call_usd,
        calls_asked, refused}` with the day's totals after the charge (unchanged when refused). Any
        store error is a refusal too (`budget_unavailable`): no live call runs uncounted. The meter
        counts live planner calls only; search calls join it when the live search exists.
        """
        day = manila_day(self.clock())
        try:
            allowed, doc = self.store.charge_budget(day, calls, self.estimate(calls), self.line_usd)
        except Exception:  # noqa: BLE001 - any store failure is a refusal: no live call runs uncounted
            return self._outcome(REFUSED, day, None, BUDGET_UNAVAILABLE, calls)
        return self._outcome(ALLOWED if allowed else REFUSED, day, doc, None if allowed else BUDGET_EXHAUSTED, calls)

    def today(self):
        """The day's record for the dock's budget line (never raises)."""
        day = manila_day(self.clock())
        try:
            doc = self.store.get_budget(day)
        except Exception:  # noqa: BLE001 - the budget line is shown, never an exception
            return self._outcome(REFUSED, day, None, BUDGET_UNAVAILABLE, 0)
        doc = doc or {'day': day, 'calls': 0, 'usd_estimate': 0.0}
        spent = doc['usd_estimate'] + self.per_call_usd > self.line_usd + 1e-9
        return self._outcome(REFUSED if spent else ALLOWED, day, doc, BUDGET_EXHAUSTED if spent else None, 0)
