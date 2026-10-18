# Review records

One file per reviewed task, named `<TASK-ID>.md`, written by the reviewer role using the
[review template](../../engineering/templates/review.md). Each record names the reviewed
commit, whether the review was independent or self-review, the checklist answers, findings
with dispositions, and the verdict (`accept`, `rework`, `escalate`). A task reaches `done`
in `tasks.json` only when its record here carries `accept`. Process:
[review and feedback](../../engineering/review-and-feedback.md).
