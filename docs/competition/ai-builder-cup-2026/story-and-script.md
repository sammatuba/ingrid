# Story and demonstration script

## Positioning

Title: InGRID (Grid Nowcast until release 23, 18 October 2026).
Subtitle: From market signals to trustworthy, traceable decisions.
Category: Future of Work & Enterprise Productivity.

The general claim first: who answers for a decision made with AI? AI is about to do most of the
reading and drafting; people still decide and still answer for the result. An organization that cannot
show which AI judgment it trusted, and why, holds AI back or uses it blind. The bottleneck is trust and
traceability, and both are properties of records, not of models. The mechanism underneath is belief
maintenance. Knowledge work that produces positions fails on
beliefs that go out of date, not on information or models. Evidence that changes an assumption arrives every day, cluttered, and nothing
connects it to the decision that depends on it. The product is the owned record of those assumptions,
the versioned outlook built on them, the impact in the organization's own units, and the decision
kept with its reasons. The AI does the evidence legwork under a cutoff; people keep acceptance.

Then the instance: a retailer in the Philippine wholesale electricity market, where the evidence is
public and time-stamped, the semantics are regulated, and the truth settles every month, so the claim
can be scored. One-sentence pitch: InGRID connects new grid evidence to the assumptions behind
an analyst's outlook, then makes each retained or revised position traceable and reviewable.

The emotional problem is a stale assumption, not a lack of charts. The hero is the analyst. The
outcome is a better-supported decision, not an unproven claim of fewer blackouts. The full case for
the category, with evidence grades, is in [future-of-work-case.md](future-of-work-case.md).

## 30-second pitch

Who answers for a decision made with AI? AI is about to do most of the reading and drafting, but
people still decide and still answer for the result, so the bottleneck moves to trust and
traceability, both properties of records, not of models. InGRID is a desk for that problem, tested on the Philippine power market: it shows what changed, which assumption it affects, and exactly why an analyst
should review it, with the AI's judgment cited and the analyst's decision kept. Nothing
silently becomes truth. You can open the source, compare the alternatives, and see a defensible
outlook revision, including the decision not to change. The operator's own records lag a plant
trip by a median eight and a half hours; the desk reads the advisory the minute it posts.

## Main demo: target 165-170 seconds, never 180

Revised 2026-10-15 to the journey the deployed product actually offers (the
[2026-10-14 strategy refresh](../../work/strategy-refresh-2026-10-14/strategy.md): the Philippine grid first, the
change desk as the drill-down from one real event). Every screen below is live at `https://ingrid-desk.web.app`;
the earlier desk-first table is superseded. The shot list (REL-3) derives from this table.

| Time | Screen | What must be real in the final recording |
|---|---|---|
| 0-15 | Grid page `/`, Visayas selected, replay clock at 21 Sep 2026 13:40 | The narrative paragraph written by code from the figures; the caption line names the source and the replay date; the sign-in screen first, two seconds, then the grid page (the judges' account from the submission form) |
| 15-35 | Grids table, map, HVDC flows | Real demand, price and reserve figures with as-of times; 492 of 619 sites located, 127 at pending positions, said in the caption (recounted 2026-10-18 from the release 22 build's `sites.json` with the page's own rule; since release 23, live build stamp `8e48b553cd692e60` per PROGRESS row 'Batch release 23' (2026-10-18), the 127 unplaced sites have approximate positions and 0 placeholders remain, so the caption's wording is re-read off the screen before the take) |
| 35-50 | Operator messages feed; "PEDC U2 Tripped at 13:34" with "Review impact" | The real NGCP advisory text and time (V133937); the replay control moving the clock |
| 50-75 | Event page `/event/pedc-u2-2026-09-21`: advisory, what followed on the grid, the market around the event | Timeline and figures from the company's WESM copy under the signed permission record; the assumption card: PEDC Unit 2 available capacity 83.7 MW from the IEMOP register |
| 75-105 | The recorded Gemini judgment: four phrasings, eight questions, the stability receipt, the challenge | The stored-run label and receipt digests visible; say it is a recorded run on the real case, not a live call |
| 105-130 | The decision form: retain 83.7 MW with a reason; save; history shows the saved decision on the judge's own copy | The anonymous judge session created on the first action; the saved disposition and its history read back from Firestore |
| 130-145 | The honest limits, on screen | Replay as of 29 Sep 2026, not live; consequences uncomputed; the return-cutoff disagreement between Gemini and the case reading named as an open finding |
| 145-160 | Where it runs | The services in the one [services table](../../work/polish-2026-10-18/services-table.md) order and state words: Firebase Hosting, Cloud Run, Artifact Registry, Firestore and Firebase Authentication running; Vertex AI Gemini ran on the real case (recorded); BigQuery ran at each build; the first screen served without waiting on the instance; measured numbers from the performance baseline only |
| 160-170 | Close | A justified no-change is a success; no unsupported impact or forecast-skill claim |

## Narration draft

Who answers for a decision made with AI? AI is about to do most of the reading and drafting. People
still decide, so the bottleneck moves to trust and traceability: properties of records, not models. For an energy
analyst, the hard question is what a grid change means for the outlook they own.

This is the Philippine grid on 21 September 2026, replayed from the market's own five-minute
data. Visayas demand, the price, the reserve condition, the flows on both HVDC links: every
figure carries its time. At 13:39 the system operator posts that PEDC Unit 2 tripped.

Open the event. Here is the advisory, what followed on the grid, and the market around it. Here
is the outlook assumption it touches: the unit's available capacity from the register.

Gemini has already judged this case, four phrasings of the same questions, with citations and a
stability receipt. It reads the set as a forced outage and challenges the assumption. That is a
recorded run on the real case; the receipt is on the screen.

The analyst decides. Retain the assumption, with a reason, and save. The decision lands on the
judge's own copy of the case, and the history shows it. A justified no-change is a success.

What this is not: not live data, the replay ends on 29 September; not a computed consequence;
and where Gemini and the case reading disagree, the disagreement is recorded, not hidden.

It runs on Google Cloud: Firebase Hosting serves the first screen, Cloud Run, Artifact Registry,
Firestore and Firebase Authentication carry the site and hold the review, Vertex AI ran Gemini on
the real case, BigQuery fed each build. InGRID does not ask AI to run the grid. It helps people
see when their outlook needs to change, and makes the reason visible.

## Recording discipline

Use the final hosted build, not the standalone concept HTML, for the required functional demo.
Where model calls are stored for repeatability, display stored-run labels and receipts. Use an
actual permitted case or explicitly say fictional demonstration. Never splice a success from a
different input as though it were the displayed run. Include captions and a readable cursor.
Measure encoded duration and keep end cards inside the limit. The PDF deck carries details
that would make a short video unreadable.

## Deck narrative

1. The foundation: four questions, and the claim that follows (who answers for a decision made with AI; trust and traceability are properties of records; belief maintenance is the mechanism).
2. One analyst, one decision, one reviewable outcome.
3. The evidence-to-outlook loop.
4. Live demonstration / interaction view, clearly labeled.
5. The model division of labor and meaningful Gemini role.
6. Ontology-to-task compilation and dependency tracing.
7. What existing experiments establish - and do not.
8. Safety, time, identity and approval boundaries.
9. User value and pilot measurement plan.
10. GCP architecture and deployment evidence.
11. Delivery status / near-term scope and research frontier.
12. Why this is not a dashboard or PDF chatbot.
Appendix: research, evaluation and release gates.
