# Start here

Read this page first. It takes five minutes. It tells you what InGRID is, what you can see
today, and where to go next. Its name was Grid Nowcast until release 23 (18 October 2026). Every special word on this page is in the [glossary](glossary.md).
AI agents start at [AGENTS.md](../AGENTS.md) instead.

## What InGRID is

Who answers for a decision made with AI? AI can now read every signal and draft every change.
People still decide, and people still answer for the result. Which AI judgment did we accept, and
why? Without a record, an organization holds AI back or uses it blind. InGRID keeps that
record.

We test it on the Philippine grid. Under the record sits a simple idea: work keeps a set of beliefs
up to date. Every forecast rests on assumptions. The assumption that nobody owns is the one that
goes out of date.

An energy analyst writes an outlook: a forecast of supply, demand or prices. One assumption in
it: "PEDC Unit 2 can supply 83.7 MW on 21 September." When something happens on the grid, some
assumptions become wrong. The analyst must find out which ones, and fast.

InGRID is a review desk for that job. It reads new evidence, such as an operator notice.
It finds the assumption that the evidence touches. It asks an AI model for a judgment with
citations.

Then the analyst decides: keep the assumption, change it, or ask for more review. A
kept assumption with a good reason counts as a success. The AI never decides.

## What you can see today

Open `https://ingrid-desk.web.app`. The same app also answers at `https://grid-nowcast.web.app`.
Some office networks block every `web.app` address. Then use
`https://grid-nowcast-adcri4pd6q-as.a.run.app` instead.

You meet a sign-in screen first on every page. The submission form will name the judges'
account. The site opens on the grid page and the event page. One top bar reaches the other pages:
outlooks, register, models, plants, notices, alerts, book, journal, the explainer and the paper.
The site serves one build, release 27. It covers 18 October 2025 to 14 October 2026.

The site changed on 18 October 2026 (GitHub PR #102, live since release 22). Release 23 added
the InGRID name and one design system on every page. Release 25 fixed the map Key toggle and made
the state card's link rows and alert counts into links.

The map
fills the first screen of the grid page, with a "Grid now" card over it. The top bar carries a
strip of grid prices, undersea link congestion and alert counts. A command bar sits at the
bottom of every page except the ask page. It searches the site and takes questions. Each answer
says where it comes from: a recorded run or the records.

Since release 23 the bar answers a signed-in visitor live on Vertex AI, with a "live" label and a trace. The trace steps show as the model works, or with the answer where the hosting buffers them. Anonymous visitors get answers composed from records. A citation mark sits right after each figure, so copied text can glue the two together. Read figures from the table. The floating ask panel is gone.

1. **The grid page.** It shows the Philippine grid on 21 September 2026. You see the demand,
   the price and the reserve of each grid. You see a map of plant sites and the flows on the two
   undersea links. You see the operator's messages and one chart. A clock lets you replay the
   day. The data is real and recorded. Nothing is live.
2. **The event page.** At 13:34 that day, PEDC Unit 2 in Visayas tripped. The page shows the
   operator's notice and the assumption it touches: 83.7 MW. It shows the recorded AI judgment
   with its eight answers. It has a decision form. Save a decision, and the site keeps it in your
   own copy of the case and shows the history.

After sign-in, the site creates a private copy for you when you first act.

## How it works

A script turns the recorded grid data into files. Firebase Hosting serves those files. Cloud Run
runs the app server for the other pages. Firestore stores your copy of the case and your
decisions.

The AI judgment on the event page is a recorded run. On 14 October 2026, Gemini answered through
Vertex AI at two cutoffs, and we saved the answers. The site makes no live call to any AI model.

The Google services, in one table. The state words: running, ran once, built (not run live), set
up (no run record), designed.

| Service | What it does here | State |
|---|---|---|
| Firebase Hosting | Serves the first screen and the grid files. Sends every other path to Cloud Run. | running |
| Cloud Run (asia-southeast1) | The app server: visitor copies, decisions, the ask service, the command bar search and answers, alerts, journal and book pages. | running |
| `Artifact Registry` | Holds each release image. | running |
| Firestore | Each visitor's copy of the case and decisions. The alerts, ask and journal data. | running |
| Firebase Authentication | Anonymous visitor identity. Sign-in for the editors. The sign-in screen. | running |
| Vertex AI Gemini | Eight fixed questions on one evidence and assumption pair. The planner. Cited extraction. | Question set: ran once on the real case (2026-10-14, two calls at two cutoffs) and once on the synthetic case (2026-10-11). Planner and extraction: built, not run live. |
| BigQuery | The company copy. Read at each grid file build and by the alerts page. | Ran at each build. Alerts read: built, no run record. |
| Cloud Storage | The company copy and the anonymised portfolio draft. | data location |
| Secret Manager | The mail password and the search key for the alerts. | set up, no run record |
| Cloud Scheduler | The automatic alerts check when new data lands. | built, no run record |
| Cloud Build | Ran the hosting checks once (2026-10-14). Not in the deploy path. | ran once |

## Where the project stands

- **Finished.** The review method. The grid page and the event page. The live site. The real
  PEDC case. Saved decisions and histories. The speed work. The pitch deck, the video shot
  list and the release file list. The ask service and the synthetic book.
- **In progress.** The onboarding pages you are reading.
- **Waiting on the owner.** The walkthrough by someone new to the project. The rights approval
  for the public export. The video. The competition entry.

The [status page](status.md) has the exact list. We keep no internal deadlines. The one external
date is the competition's, in the [requirements](competition/ai-builder-cup-2026/requirements.md).

## Who does what

- **Sam, the owner.** Decisions, approvals, deploys, money and the submission.
- **Ericka, the teammate.** The data foundation in BigQuery and the first replay dashboard.
  Any task, through the normal path.
- **Three AI helpers.** One coordinates, one builds, one reviews. A person or an AI that did not
  write a change reviews it. [How we work](engineering/how-we-work.md) explains the path.

## Where to go next

- **Understand the ideas.** The [explainer](explainer/README.md) opens on the four questions
  behind the desk. Then it shows the system that carries them: one map of everything in place, a
  path through the chapters, and the two Gemini roles. Then it walks through every layer, with
  pictures and small exercises. It is also on the site, at
  `https://ingrid-desk.web.app/explain`.
- **Look up a word.** The [glossary](glossary.md).
- **Contribute.** [How we work](engineering/how-we-work.md) has the setup steps and the rules.
- **Check what is true today.** The [status page](status.md).

## Three commands

```sh
git clone https://github.com/sammatuba/ingrid
cd grid-nowcast
/usr/bin/python3 -m unittest discover -s tests
```

The last command runs the tests on your computer. It needs Python 3.11 or newer and nothing
else. Type the full path `/usr/bin/python3` as shown. The short name `python` does not work on
the owner's computer. More than a hundred tests skip when a browser, a local service copy or the
company data is absent. That is normal.

## Rules that never change

- Keep every document in this repository. Do not publish outside it.
- Keep the company data, passwords and keys out of Git.
- Do not invent a number, a time or a result. Unknown stays unknown.
- Do not report a command that you did not run.
