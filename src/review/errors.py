"""Stable, non-disclosing domain failures."""

MESSAGES = {
    "INVALID_RECORD": "record does not satisfy h0.v1 or h0.v2",
    "INVALID_SOURCE": "source bytes or passage binding is invalid",
    "MALFORMED_TIME": "time must have explicit precision and offset",
    "ACCESS_DENIED": "operation is not permitted",
    "REVISION_CONFLICT": "immutable revision already has different content",
    "UNKNOWN_AVAILABILITY": "historical availability is unknown",
    "LATER_AVAILABILITY": "source was available after the information cutoff",
    "UNRESOLVED_MAPPING": "reviewed typed mapping is unresolved",
    "AMBIGUOUS_MAPPING": "multiple mappings cover the affected period",
    "TRUNCATED_CONTEXT": "permitted context exceeds the policy limit",
    "MISSING_INPUT": "required permitted input is missing",
    "STALE_DEPENDENCY": "task dependency has changed",
    "STALE_HEAD": "accepted head does not match the request",
    "IDEMPOTENCY_CONFLICT": "idempotency key already binds a different request",
    "BLOCKED_TASK": "task permits only defer or investigate",
}


class ReviewError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(MESSAGES[code])

    def as_dict(self):
        return {"code": self.code, "message": str(self)}


def require(condition, code="INVALID_RECORD"):
    if not condition:
        raise ReviewError(code)
