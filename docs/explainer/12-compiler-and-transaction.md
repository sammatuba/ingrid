# The compiler and the review transaction

<!-- paper: 9.2 9.3 9.5 -->

This chapter follows one decision through the code: from the compiled task to the atomic commit
that writes it. It is the layer the event page's decision form sits on.

## The compiler

The compiler takes six inputs. They are an authenticated actor, a case, an assumption version, an
information cutoff, an audit cutoff and the accepted snapshot. It applies its filters in a fixed
order. Access comes first, then availability, then reviewed identity, then context and type
checks. Then it selects the relevant passages and series, groups them by source trail, draws a
bounded task and computes the single fingerprint.

The output is one immutable task. The task excludes access scope, membership data and unrelated
case state. The model never sees who may read what.

## One call to prepare

The event page asks the server to prepare a decision in one call. The answer carries the case
heads, the belief snapshot at the audit cutoff, and the task compiled at the notice's information
cutoff. That is one request instead of three.

## The atomic commit

The commit is where the desk refuses to lose a decision or to overwrite a newer one. Step through
it. Then switch the race on and step through it again.

<!-- widget: transaction-race -->

The commit compares the expected heads with the current heads. It binds an idempotency key to the
tenant, the case, the actor and the request fingerprint. It appends the decision, the head change
and the audit entry in one transaction. An identical retry returns the original receipt. A
conflicting head fails without a partial write.

## State changes the desk allows

A candidate starts proposed. Revise accepts a new value. Retain records a reviewed no-change
against the current head. Reject closes the candidate. Defer and investigate keep the accepted
head and open work.

Changing evidence marks dependent drafts out of date. It never erases accepted history. It never
asserts that every dependent conclusion is wrong.

## What the API refuses

Every write carries a server-authenticated actor, a request id, an idempotency key and the
expected heads. The server checks case and tenant ownership on every read and write. No route
runs arbitrary SQL, fetches arbitrary URLs, edits a production model or executes a shell command.
No route runs the production forecast or dispatches an operational action.

Execution would need a separate approval bound to an input fingerprint, an expiry, a model
identity and an actor. It is outside this version.

## The refusal codes you can meet

The page shows every refusal as its code and one sentence. A visitor can meet four of them.

| Code | Meaning |
|---|---|
| 401 | The session is no longer valid. Reload the page. |
| 404 | The case or route was not found. Another session's case answers this way too. |
| 409, STALE_HEAD | The case moved since the page loaded. Reload and decide again. |
| 422, INVALID_RECORD | The desk did not accept the decision as a record. |

The hosting review exercised each one live and recorded the answer.

<!-- quiz -->
Q: Two tabs of the same visitor save a decision on the same copy within a second. What happens to the second?
- It overwrites the first
- [x] The server refuses it with STALE_HEAD, 409, and writes nothing
- The desk writes both and the later one wins
Why: The commit compares expected heads with current heads inside one transaction. An out-of-date head fails without a partial write.
<!-- /quiz -->

## Sources for this chapter

- The compiled task and the invariants: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), sections 9.2, 9.3 and 9.5.
- The compiler's six inputs and the commit in more detail: the [earlier working paper](../product/working-paper-2026-10-11.md), sections 5.1 and 5.8.
- The ports and their contracts: the [review core](../../src/review/README.md).
- The state changes and the API boundary: [decision system v1](../architecture/decision-system-v1.md), sections 6 and 7.
- The refusal paths exercised live: the [hosting record](../work/hosting/implementation.md).
