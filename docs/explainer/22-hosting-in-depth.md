# Behind the prototype: where it runs

<!-- paper: 3.3 15 -->

Chapter 10 followed one visit. This chapter opens the hosting. It shows how a build gets its
name and why the first screen never waits for a server. It shows what each answer may cache, how
a release stays pinned, and what keeps a visitor's copy private.

## The services, in one table

Every Google service the project touches, with its state on 18 October 2026. The state words:
running, ran once, built (not run live), set up (no run record), designed. The one text for this
table is the [services table](../work/polish-2026-10-18/services-table.md).

| Service | What it does here | State |
|---|---|---|
| Firebase Hosting | Serves the first screen and the grid files. Sends every other path to Cloud Run. | running |
| Cloud Run (asia-southeast1) | The app server: visitor copies, decisions, the ask service, the command bar search and answers, alerts, journal and book pages. | running |
| `Artifact Registry` | Holds each release image. | running |
| Firestore | Each visitor's copy of the case and decisions. The alerts, ask and journal data. | running |
| Firebase Authentication | Anonymous visitor identity. Sign-in for the editors, and the sign-in screen. | running |
| Vertex AI Gemini | Eight fixed questions on one evidence and assumption pair. The planner. Cited extraction. | question set ran once on the real case (2026-10-14, two calls at two cutoffs) and once on the synthetic case (2026-10-11). Planner and extraction built, not run live |
| BigQuery | The company copy. Read at each build of the grid files, and by the alerts page. | ran at each build. Alerts read built, no run record |
| Cloud Storage | The company copy and the anonymised portfolio draft. | data location |
| Secret Manager | The mail password and the search key for the alerts. | set up, no run record |
| Cloud Scheduler | The automatic alerts check when new data lands. | built, no run record |
| Cloud Build | Ran the hosting checks once (2026-10-14). Not in the deploy path. | ran once |

## One stamp names a build

At start, the server computes one 64-bit fingerprint over the replay files and the design
files. That stamp goes into every versioned URL and into the page's meta tag. A changed byte of
data or of design changes the stamp. So a browser can keep a file under a stamp for a year and
never hold a wrong one. The image and the build folder it came from derive the same stamp, and a
test proves it.

## Three cache classes

<!-- widget: cache-classes -->

## The staged draw

The grid page asks for seven small files and one heavy file at the same moment. The small
files draw everything with words and figures: the paragraph, the table, the feed, the chart, the
map outline. The heavy node file carries one thing, the prices behind the dots' colours, and it
lands second. Until it lands, a price shows as unknown, never as a figure. The vector table for
the day's path comes last, after the first paint, with the warm-up call.

## What a visitor waits for

<!-- widget: cold-timeline -->

The service keeps no warm server by policy. The first service request pays the cold start. The
page sends that request itself after the first paint, so a visitor reads the grid while the
server wakes. The baseline measured it from Singapore and from a browser in Manila. It read the
server state from the Cloud Run log rather than guessing it from latency.

## A release, pinned

The deploy script builds the image, pushes it, resolves the pushed fingerprint, and deploys the
fingerprint, never a tag. It then compares the fingerprint the service runs with the one it
built, routes the version it verified, and publishes the Hosting files. The previous version
stays one command away. Every release records its version, its fingerprint and its Hosting
build in the repository. Deploys are rare: one per batch of finished work.

## A visitor's copy

The demo namespace is separate from any private case. On the first action, the sign-in service
gives the visitor an anonymous identity. The server then creates the visitor's own copy of the
case in one step, from fixed test data with a recorded fingerprint. The browser never writes the
database directly.

An operator command removes sessions older than a policy age. It refuses to touch any namespace
but the demo one. It never deletes a session with a non-anonymous provider.

## The headers every answer carries

The content security policy admits scripts and styles only from the site itself, with no inline
code, and connections only to the same origin. That is why the site serves this explainer as
three files rather than one. Every answer also carries no-sniff and no-referrer. The hosting
harness serves the pages with the same policy. A clean console in the tests means a clean
console in production.

<!-- quiz -->
Q: Why can a browser keep a replay file under the stamp for a year?
- Because the data never changes
- [x] Because a changed byte changes the stamp, and with it the URL, so nobody asks for the old file again
- Because Firebase Hosting refreshes it daily
Why: The stamp is a content fingerprint. New content means a new URL. The old URL simply never comes up again.
<!-- /quiz -->

## Sources for this chapter

- The stamp and the cache classes: the [stamp and cache record](../work/performance/perf-1.md).
- The staged draw and the first-screen order: the [staged draw record](../work/performance/perf-4.md) and the [first-screen record](../work/performance/perf-5.md).
- The cold-start populations: the [performance baseline](../work/performance/baseline.md), run 10 and its correlated section.
- The release, rollback and cleanup: the [hosting record](../work/hosting/implementation.md).
- The security rules: [decision system v1](../architecture/decision-system-v1.md), sections 9 and 10.
