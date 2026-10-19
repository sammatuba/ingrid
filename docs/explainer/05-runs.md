# Where it runs

This chapter follows one visit to the site through Google Cloud. You need no cloud knowledge.
Every time value comes from the performance baseline, named at the end.

## The pieces

| Piece | What it does | Google service |
|---|---|---|
| The grid files | The September data, turned into small files by a script before each deploy. | Firebase Hosting |
| The pages | The grid page and the event page, as plain HTML, CSS and JavaScript. | Firebase Hosting |
| The app server | Makes your copy of the case, saves your decisions, returns the history. Written in Python. | Cloud Run, Singapore |
| The database | Holds every visitor's copy of the case and the decisions. | Firestore |
| The sign-in service | Gives you a private identity on your first action. No password, no form. | Firebase Authentication |
| The AI model | Answered the eight questions once, on 14 October 2026. The site shows the saved answers. | Vertex AI, Gemini |
| The company copy | The market data behind the grid files. The build script reads it before each deploy. The alerts page reads it too (built, no run record). | BigQuery |

The company data lives only in the grid files and in the server's container image. It is never in
Git. The owner's signed permission record allows it on the demo site and in the submission, and
nowhere else.

## One visit, step by step

<!-- widget: request-walk -->

Two things in that walk deserve a closer look.

**The first screen does not wait for the server.** Firebase Hosting serves the grid files from a
location near you. The grid page draws in stages: the figures first, then the map, then the
chart. When no app server is running, Google starts one. That took 6.7 seconds in our tests. You
do not notice, because you are reading the grid page while it happens.

**The event page is explorable too.** Click a notice on the timeline and the judgment at that
notice's cutoff opens: the readings before and after it, with their rules and receipts. Click
the big value for where the assumption came from and when the desk accepted it. Click a
judgment row for the question in plain words and the four answers. Click a saved decision for
what its record carries. The limits line at the bottom expands to the full list.

**Your copy is private.** On your first action, the sign-in service gives you an identity, and the
server makes your own copy of the case in one step. A decision you save changes only your copy.
If your copy changed under you, the server refuses the save and tells you. That is the same rule
that protects two analysts who work on one case.

## What the site does not do

- The event page makes no live call to any AI model. Its judgment is the recorded run.
- Since release 23, a signed-in visitor can ask Ingrid live in the command bar.
- It has no live data feed. The replay ends on 14 October 2026.
- It computes no price or cost consequence of the trip. The site says "not computed" where that applies.
- It shows no feature that is not connected. No placeholder badges.

## How a new version reaches the site

The owner runs one deploy script. It builds the container image, pushes it, deploys it to Cloud
Run, and compares the fingerprint of the deployed image with the fingerprint it built. It then
publishes the grid files to Hosting. If anything goes wrong, the previous version is one command
away. Deploys are rare: one per batch of finished work. The [status page](../status.md) names the
live version.

<!-- quiz -->
Q: You open the event page and see Gemini's judgment. What did the site just do?
- It called Gemini and waited for the answer
- [x] It showed the answers that Gemini gave once on 14 October 2026
- It asked a smaller model to guess
Why: The deployed app has no model connected. The judgment is a recorded run, and the receipt on the page says so.
<!-- /quiz -->

## Sources for this chapter

- Times: the [performance baseline](../work/performance/baseline.md), runs 3 to 9.
- The pieces and the deploy script: the [hosting record](../work/hosting/implementation.md).
- The recorded run and the live path: the [status page](../status.md) and the [live run record](../work/grid-desk/live-run-2026-10-14.md).
