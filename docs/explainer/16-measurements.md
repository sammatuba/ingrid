# Measurements, step by step

<!-- paper: 7.2 7.3 -->

The paper reports two measurements on the market's own data. One asks how late the operator's
schedule is. The other asks whether simple forecasts beat simple baselines. This chapter walks each
protocol in the order the authors ran it.

## How late is the schedule?

When the system operator posts an outage advisory, how long until its own outage schedule shows the
outage? A planner would use that schedule as a belief, so its lag decides how long a belief can stay
out of date.

<!-- widget: lag-walk -->

The schedule and the advisory feed mostly describe different outages. The schedule carries planned
outages that the operator does not announce. The advisories announce trips that the schedule rarely
records. The paper draws no claim about money from these numbers.

## A milestone, read two ways

The energy department's list of committed projects, "as of July 2026", shows a 350 MW coal unit
still in testing. It targets commercial operation for August 2026. The market data shows the same
unit registered at 315 MW on 16 May 2026. In the September billing month it dispatched in 8,927 of
8,928 intervals.

The two sources do not contradict each other, because a unit in testing can dispatch. But a planner who reads only the list
would not know that the unit already delivers energy. Whether test output counts as supply is a
belief, and it needs an owner.

## Does a simple forecast beat the baselines?

Three baselines and two challengers forecast 16 price series at day, week and month horizons. The
information cutoff sits 24 hours before each forecast origin. The challengers read fourteen inputs
from rows that ended before that cutoff, and the authors fitted them in six blocked folds with a
one-day gap.

A group is a series, a horizon, a slice and a challenger: 192 in all. A group claims skill only when
it passes six rules that the authors stated first. Pick a group and read each rule.

<!-- widget: skill-test -->

28 of 192 groups claim skill: 27 at the day horizon and one at the week horizon. None claims skill
on the administered slice, and none at the month horizon.

## The month horizon, kept apart

A retailer's contracting decisions sit at the month horizon. There, three things hold at once. The
observed gains are mostly positive. Their uncertainty is too wide to exclude zero on 27 origins. And
the rules make a claim impossible with so few origins.

So the paper says that no month claim is possible under this test, not that the month has no skill.
Either way, decisions there rest on beliefs rather than on a demonstrated model. That is the second
reason the paper gives for building the records first.

<!-- quiz -->
Q: 1,232 of 1,275 generator advisories have no schedule row within six hours. What does that number measure?
- How late the schedule is
- [x] A coverage gap: advisories the schedule does not reflect at all under the matching rule
- How much money the lag cost
Why: The lag comes from the 27 matched rows, with a median of 8.5 hours. The 96.6% counts advisories with no match at all, and it says nothing about delay.
<!-- /quiz -->

## Sources for this chapter

- The schedule lag, its protocol and the milestone: the [working paper](../product/paper-accountable-ai-decisions-2026-10-17.md), section 7.2.
- The baselines, the challengers, the six rules and tables 10 and 11: the same paper, section 7.3.
- Why the records come first: the same paper, section 13.3.
