# How we work

This chapter explains how a change reaches the site, and who does what. It is the short version
of [how we work](../engineering/how-we-work.md), which has the commands.

## The people and the AI helpers

Two people own the project. Sam, the owner, makes the decisions, gives the approvals, deploys, and
submits. Ericka, the teammate, built the data foundation in BigQuery and the first replay
dashboard. The hosted grid page reused its structure.

Three AI helpers do most of the typing. The coordinator AI picks tasks, writes briefs, runs the
checks and merges on the owner's word. The builder AI builds one task at a time on its own
branch. The reviewer AI reads a finished task and answers accept or rework. A fourth, used rarely,
reviews big decisions.

The one rule that always holds: nobody merges their own work. A person or an AI that did not
write a change reviews it.

## The life of a task

<!-- widget: task-life -->

Every task has an ID, such as `PERF-3`. The task lists the files it may change, its acceptance
checks and a verify command. The builder writes the commands it ran and the results it saw into
the task record. A reviewer reads that record, not a summary. The state of every task lives in two
files, and the tests fail when the two disagree.

## What "done" means

A task counts as done when three things are true.

1. The repository check, the plan check and the test suite pass on its branch.
2. An independent reviewer wrote "accept" into the review record.
3. The owner recorded the accept, and the state changed in both files in one commit.

Documentation is not proof. A recorded run is evidence of that run only. We never report a
command that did not run or a number that nobody measured.

## No deadlines, one order

The team keeps no internal deadlines. The remaining work is one ordered chain. The next task is
always the head of the chain, and the live list is one command away. The one external date is the
competition's.

## Where to read next

- [Start here](../START-HERE.md) for the five-minute version.
- The [glossary](../glossary.md) for every word on these pages.
- [How we work](../engineering/how-we-work.md) for the commands and the rules.
- The [status page](../status.md) for what is true today.

<!-- quiz -->
Q: The builder AI finishes a task and all checks pass. What happens next?
- The builder merges it into the shared line
- [x] Someone who did not write it reviews it
- The owner deploys it
Why: Nothing merges on the author's word. A reviewer answers accept or rework first. Deploys come later, once per batch.
<!-- /quiz -->

## Sources for this chapter

- The roles and the path: [how we work](../engineering/how-we-work.md) and the
  [review and feedback process](../engineering/review-and-feedback.md).
- The order of the remaining work: [milestones](../work/milestones.md).
