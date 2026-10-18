# Video shot list and narration

Document control. This is the REL-3 output for the AI Builder Cup 2026 submission: the timed
shot list and the caption text for the demonstration video that REL-6 records, plus the
narration each shot carries. It derives from the main demo table in the
[story and script](story-and-script.md) (revised 2026-10-15 to the journey the deployed product
offers) and names only screens the deployed application serves and only the execution-mode
labels the [working paper](../../product/working-paper-2026-10-11.md) section 4.2 defines and
the [deck](deck.md) uses. Every claim about a screen, a label or a timing carries the record it
was read from; no number in this file was measured by this task.

The competition limit is E8, strictly under 180 seconds
([requirements](requirements.md)); this plan totals **168 seconds**, under the 170 the task
requires and 12 seconds inside the limit. The budget and its check are in
[Timing](#timing-and-the-check).

## Where it is recorded, and in which runtime mode

One browser, one continuous session. The first screen is the sign-in screen: shot 1 opens on it
for two seconds, signed in with the judges' account named in the submission form (REL-7), then
the grid page (the owner keeps the sign-in wall; [board](../../work/coordination/board.md) rows R11
and R12, [PROGRESS](../../work/PROGRESS.md) row 'Batch release 22' (2026-10-18); changed 2026-10-18, POLISH-2 item 11; the live build is release 23 since 2026-10-18, PROGRESS row 'Batch release 23', product name InGRID on every page).

| | |
|---|---|
| URL | `https://ingrid-desk.web.app` (Firebase Hosting in front of Cloud Run, `asia-southeast1`). If the owner's network blocks `web.app`, the same revision is served at `https://grid-nowcast-adcri4pd6q-as.a.run.app`; record from one of the two and name it in the receipt |
| Runtime mode | `hosted` — the mode label `select_mode` resolves for the deployed container (`NOWCAST_ENV=hosted`; `GET /health` answers `{"mode": "hosted"}`). Source: [src/api/hosted.py](../../../src/api/hosted.py) `LOCAL_MODE/DEMO_MODE/HOSTED_MODE` and the deploy environment in [scripts/deploy/README.md](../../../scripts/deploy/README.md) section "Modes". Hosted mode is what makes the session real: a Firebase anonymous judge and Firestore hold the decision |
| Revision | Read it at recording time (`gcloud run services describe`) and put it in the REL-6 receipt and the REL-4 manifest; this file does not pin one |
| Browser | 1280 px or wider, one window, visible address bar, readable cursor, captions burned in (the story's recording discipline) |
| Same screens in | `demo` mode (the same image with `NOWCAST_ENV` unset) serves both pages and records a decision from an in-process store; `local` mode is the seat's emulator mode and is never recorded. If any shot is ever captured in `demo` mode it must say so on screen; the plan is one `hosted` take |

## Screens used (both are served; nothing else is shown)

| Screen | Route | Rendered by | Served by |
|---|---|---|---|
| Grid page | `/` | [src/grid/index.html](../../../src/grid/index.html), [grid.js](../../../src/grid/grid.js) | Hosting file (page shell) plus `/grid-data/<build>/…` replay files; the route also exists on Cloud Run |
| Event review page | `/event/pedc-u2-2026-09-21` | [src/grid/event.html](../../../src/grid/event.html), [event-api.js](../../../src/grid/event-api.js), [event.js](../../../src/grid/event.js) | Cloud Run route, hosted mode; its baked view is a `/grid-data/<build>/events/…` file |
| (data, not a screen) | `/grid-data/<build>/…` | read by the two pages | Hosting files, `immutable`; the baked replay and the event view |

Not in the video: the desk at `/desk`, the private tenant routes, the emulators, any terminal,
and any screen that is not listed above. The PEDC event case the decision lands on is the real
case (`synthetic: false`, `permission_ref perm:wesm-company-copy:2026-10-13`), so
`synthetic_fixture` appears nowhere in the video; if a take ever shows a labelled synthetic
fixture instead, the caption must say so (story rule 7).

## Mode labels used (working paper section 4.2)

The deck pins the vocabulary: `live_inference`, `stored run`, `retrospective replay`,
`deterministic`, `synthetic_fixture` ([deck](deck.md), "Mode labels"). This video uses four of
the five, and names the fifth only to deny it:

| Label | What carries it in this video |
|---|---|
| `retrospective replay` | Both pages: the WESM five-minute copy and the NGCP messages replayed at a fixed window. The grid page's caption names the source and the replay day; the chip beside the clock reads `Replay`. The market copy behind the replay ends 2026-09-29 23:55 ([strategy refresh](../../work/strategy-refresh-2026-10-14/strategy.md), the BigQuery intervals row) — spoken by the narrator in shot 7, not printed on the pages |
| `deterministic` | The narrative paragraph, the grids table, the map colours, the chart, the timeline and the market figures: written by code from the figures, with no model in the path. The grid page's own as-of line says "written by code from the figures above"; the decision in shot 6 is recorded by the application's routes, not proposed by a model |
| `stored run` | The Gemini judgment card in shot 5: a call recorded on the real case on 2026-10-14 and stored in the baked view ([live run](../../work/grid-desk/live-run-2026-10-14.md)). Its by-line ends `· live` because the recorded call *was* a live inference when it was made; the card is a stored run now, and the video says so. No model call happens while the video plays |
| `live_inference` | Not used. The narration says in one sentence that the judgment is a stored run, not a call made for the video |
| `synthetic_fixture` | Not shown: the grid replay is the company's own market copy and the PEDC case is real. The video does not use the fictional corpus at all |

The source line version 2 requires for public display is the footer caption each page already
carries; both captions are held on screen at least once (shots 1, 4 and 7).
Permission: [company WESM copy, version 2](../../work/permissions/2026-10-13-wesm-company-copy.md)
approved public display "on the deployed demo, in the video and in the deck … with a source
line".

## Shots

| # | Start | End | s | Screen | Mode label |
|---|---|---|---|---|---|
| 1 | 0:00 | 0:16 | 16 | Grid page `/` — the brief and the replay clock | retrospective replay · deterministic |
| 2 | 0:16 | 0:35 | 19 | Grid page `/` — grids table, map, HVDC flows | retrospective replay · deterministic |
| 3 | 0:35 | 0:51 | 16 | Grid page `/` — Operator messages and Reviews | retrospective replay |
| 4 | 0:51 | 1:16 | 25 | Event review page `/event/pedc-u2-2026-09-21` — advisory, what followed, the market, the assumption | retrospective replay · deterministic |
| 5 | 1:16 | 1:46 | 30 | Event review page `/event/pedc-u2-2026-09-21` — the Judgment card | stored run |
| 6 | 1:46 | 2:11 | 25 | Event review page `/event/pedc-u2-2026-09-21` — the Decision form and the History card | deterministic |
| 7 | 2:11 | 2:26 | 15 | Grid page `/` caption, then event review page `/event/pedc-u2-2026-09-21` caption | retrospective replay |
| 8 | 2:26 | 2:41 | 15 | Grid page `/` at the Hosting URL; the by-line on `/event/pedc-u2-2026-09-21` | stored run (line reused from shot 5) |
| 9 | 2:41 | 2:48 | 7 | Grid page `/` — close | retrospective replay |

Total **168 s**, ending at 2:48. The check below parses this table.

### Shot 1 — Open on the grid (0:00–0:16, 16 s)

Screen: Grid page `/`. Runtime: `hosted`. Mode labels: `retrospective replay` (the data),
`deterministic` (the paragraph).

On screen, all page-computed — read it, do not type it into the narration:

- The sign-in screen first, held for two seconds, signed in with the judges' account from the
  submission form; then the grid page opens with no dialog, no badge; Visayas is the pressed grid.
- The clock reads the replay day and 13:40 PHT, the chip beside it reads `Replay`.
- The brief card is titled "What's happening in Visayas"; its paragraph is one sentence per
  figure, each with the time; the line under it reads "Replay of … 21 Sep 2026, 13:40 Manila
  time · written by code from the figures above" (the day and year are the page's own locale
  formatting; read the line, do not restate it).
- The footer caption names the source, the replay day and the site count: "Source: WESM
  five-minute market data (company copy) and NGCP system-operator messages · replay of
  21 Sep 2026, Manila time · prices in ₱/MWh · 492 of 619 sites located, 127 shown at pending
  positions" (the located count is the page's own arithmetic over the baked site table, by the
  caption formula in [grid.js](../../../src/grid/grid.js) `setCaption`; 492 of 619 and 127 are counted
  from the release 22 build's `sites.json` with that rule (recounted 2026-10-18); the live build is release 23, stamp `8e48b553cd692e60`,
  [PROGRESS](../../work/PROGRESS.md) row 'Batch release 23' (2026-10-18), whose bake gives the 127 unplaced sites approximate
  positions (0 placeholders), so the caption's own words are read off the screen before the take; the 2026-10-14 image check read 37 of 617 off this
  line in the release-4 bake — [grid-desk implementation](../../work/grid-desk/implementation.md).
  In the one-year build the span clause reads `replay 18 Oct 2025 to 14 Oct 2026, showing …` by
  the same formula; read the line, do not restate it).

Caption (burned in): `InGRID · replay, not live · Philippine grid, Visayas, 21 Sep 2026 13:40 Manila`

Narration: "Who answers for a decision made with AI? AI is about to do most of the reading and
drafting. People still decide, so the bottleneck moves to trust and traceability: properties of
records, not models. For an energy analyst, the hard question is what a grid change means for the
outlook they own."
(Aligned 2026-10-17 to the narration draft of the story and script after REL-4; 46 words against
43 before. Re-aligned the same day to the
[meta framing record](../../work/meta-framing-2026-10-17/strategy.md): 53 words. The timing is
REL-6's to measure against the 165 to 170 second target.)

### Shot 2 — The grids table, the map, the HVDC flows (0:16–0:35, 19 s)

Screen: Grid page `/`. Runtime: `hosted`. Mode labels: `retrospective replay`, `deterministic`.

On screen:

- The "Grids" table: Luzon, Visayas, Mindanao with demand MW, median price ₱/MWh, flow MW and
  reserve, and its as-of line "At 13:40 · demand MW · median generator price · flow MW, + import".
  The active grid's row is marked.
- The map: site marks coloured by node price against the legend "Node price, ₱/MWh" with its
  ticks to the ₱32,000 cap; the layer buttons `Prices`, `Interconnectors`, `Load nodes`; the
  grid names drawn on the land. Hover one located site to show the tooltip (site code, kind,
  price, scheduled MW, replay time).
- Both HVDC links, each labelled with its name and its MW and direction
  (`Leyte–Luzon HVDC`, `Mindanao–Visayas HVDC`).
- The pending matrix beside the grid it belongs to, labelled "position pending · coloured by
  price": these are the sites without a located position, drawn as such and never as a real
  location (the owner's coordinate file replaces them with no code change).

Caption (burned in): `Every figure carries its as-of time · 492 of 619 sites located, 127 at pending positions · company WESM copy`

Narration: "This is the Philippine grid on 21 September 2026, replayed from the market's own
five-minute data. Visayas demand, the price, the reserve condition, the flows on both HVDC
links: every figure carries its time. 492 of 619 sites are located; 127 are shown as pending
positions, and the caption says so."

(Count changed 2026-10-18: counted from the release 21 build's `sites.json` and recounted unchanged from the release 22 build's `sites.json` with the page's own rule,
live build stamp `52827b20a53faeab` per PROGRESS row 'Batch release 22' (2026-10-18); on release 23 (stamp `8e48b553cd692e60`) the 127 are approximate positions, not pending, so the spoken count is re-read off the caption before the take; the word count is unchanged within one.)

### Shot 3 — The operator's message (0:35–0:51, 16 s)

Screen: Grid page `/`, the "Operator messages" card and the "Reviews" card. Runtime: `hosted`.
Mode label: `retrospective replay`.

On screen:

- The feed header "Operator messages" with its count and the filter `This grid` / `All grids`.
- Step the replay clock back one step and forward one step (the clock buttons move it five
  minutes): at 13:35 the 13:39 message is not yet in the feed, and stepping forward to 13:40
  brings it back — the clock, not a live feed, decides what the page shows. The message is the
  kind chip `Trip`, the line "Visayas · V133937", the time `13:39`, the operator's own text
  rendered "PEDC U2 Tripped at 13:34 (Unplanned Outage)" (the stored message reads `1334H`), and
  the link "Review impact →".
- The "Reviews" card above it, once the event is open: "PEDC Unit 2 trip · Visayas", "PEDC
  Unit 2 available capacity · NGCP V133937 at 13:39", "Review impact →".
- The map rings the tripped unit's site while the event is within 90 minutes of the clock.

Do not claim a highlight unless the page shows one: a page loaded at 13:40 has already seen the
message, and the feed marks "new" only a message the page has not seen within five minutes of the
clock. The honest move that does show it: open the page at `/#t=13:35&g=CVIS` (the page's own
hash), then press forward five minutes and the message arrives highlighted. Either way, click
"Review impact →" to leave for the event page.

Caption (burned in): `NGCP advisory V133937, posted 21 Sep 2026 13:39 · the operator's own text`

Narration: "At 13:39 the system operator posts that PEDC Unit 2 tripped. The message is the
operator's own text; the clock is the replay's."

### Shot 4 — The event page: advisory, what followed, the market, the assumption (0:51–1:16, 25 s)

Screen: Event review page `/event/pedc-u2-2026-09-21`. Runtime: `hosted`. Mode labels:
`retrospective replay` (the message, timeline and market), `deterministic` (the chart, figures
and layout).

On screen:

- Title "PEDC Unit 2 trip · Visayas"; the meta line "NGCP V133937 posted 21 Sep 2026 13:39 ·
  event at 13:34 · Visayas grid"; the back link to the grid at the event's minute.
- The four-step rail `Advisory · Assumption · Judgment · Decision`, with the steps before the
  decision marked done.
- The Advisory card: the quoted message "PEDC U2 Tripped at 13:34 (Unplanned Outage)" and its
  as-of line "Message V133937 as received 21 Sep 2026 13:39 Manila time".
- "What followed on the grid": the timeline of real messages — the load dropping at 13:38 caused
  by the trip, the yellow alert for 17:00–20:00, the unit re-online at 15:07 — each entry with
  its time and source.
- "Visayas around the event": the chart with the `Price ₱/MWh` and `Import MW` labels, the
  reserve-shortfall label and the event marks (the trip and the re-online), the
  five-minute-interval line, and the figure row under it.
- The "Outlook assumption" card: `83.7 MW`, "The registered maximum available capacity of
  08PEDC_U02 holds for 2026-09-21", and the register key-values (IEMOP registration list,
  permission version 2).
- The footer caption: "Source: NGCP system-operator messages, IEMOP registered capacity and
  WESM five-minute data (company copy) · replay in Manila time".

Caption (burned in): `Advisory → assumption → judgment → decision · the company's WESM copy under signed permission v2`

Narration: "Open the event. Here is the advisory, what followed on the grid, and the market
around it. Here is the outlook assumption it touches: the unit's available capacity from the
register, 83.7 megawatts."

### Shot 5 — The recorded judgment (1:16–1:46, 30 s)

Screen: Event review page, the Judgment card. Runtime: `hosted`. Mode label: **`stored run`**.

On screen:

- The by-line `gemini-3.8-flash · Vertex AI · recorded 14 Oct 2026` (changed from `· live` on
  2026-10-17 after a cold read took the word for a live call): the stored call was a live inference
  when it was made; nothing is live now.
- The verdict chip `challenges` and the fired rule `outage_or_later: Q2=forced_outage,
  Q3=same on an availability kind`.
- The eight question rows, each with its four-phrasing agreement pips and its answer
  (identity `08PEDC_U02`, forced outage, same, no, no, yes, yes, challenges).
- The receipt line: `4 phrasings × 8 questions · max flip rate 0 · 9,743 tokens in, 1,784 out ·
  11.1 s · request 512a7faa6554… · probe:e575d3c9e91a6e…` — the digests are the run's own
  ([live run](../../work/grid-desk/live-run-2026-10-14.md), and the same receipt was read off
  the deployed page in [grid-desk event](../../work/grid-desk/event.md)).
- Hold on the question table long enough to read three rows.

Say the label out loud, in one sentence, early in the shot. Do not call the judgment "live";
do not say Gemini is running now; do not re-run the model during recording (a call made now
would be a different input shown as this one's success).

Caption (burned in): `Stored run — recorded on the real case, 14 Oct 2026 · no model call during this video`

Narration: "Gemini has already judged this case: four phrasings of the same questions,
citations, and a stability receipt. It reads the set as a forced outage and challenges the
assumption. That is a stored run, recorded on the real case on 14 October — no model call
happens while this video plays; the receipt is on the screen."

### Shot 6 — The analyst decides (1:46–2:11, 25 s)

Screen: Event review page, the Decision card and then the History card. Runtime: `hosted`.
Mode label: `deterministic` (the application's routes compose and record the decision; the
model only proposed).

On screen:

- Choose `Retain`, keep the accepted value, type a reason, and press `Record decision`. The
  button stays disabled until a choice and a reason exist.
- The status line while it saves, then the saved answer with the receipt key
  `Saved · receipt event:pedc-u2-2026-09-21:retain:1` (the key is the page's own; a second
  decision in the same open page would be `…:2`).
- The rail completes; the History card appears with one entry: `You (this session)`, the
  review instant in Manila time, "Retained 83.7 MW", and the reason that was typed.
- The sandbox: the judge session is created silently on the first action (`POST /demo/session`)
  after the sign-in of shot 1; the decision lands on the signed-in judge's own copy of the real case
  (`pedc-<16 hex>`) in Firestore, and the history is read back from that copy.
- Never show a second browser, a terminal or a console. A retake reloads the page, which opens a
  fresh sandbox and a fresh case, so the take is one session start to finish.

Caption (burned in): `Saved on the signed-in judge's own copy of the real case`

Narration: "The analyst decides. Retain the assumption, with a reason, and save. The decision
lands on the signed-in judge's own copy of the case, and the history shows it."

(Sign-in wording changed 2026-10-18, POLISH-2 item 11: the wall stays, board row R12.)

### Shot 7 — The honest limits (2:11–2:26, 15 s)

Screen: the two footer caption lines, the grid page's then the event page's, with the event
page's market panel behind them. Runtime: `hosted`. Mode label: `retrospective replay`.

On screen: the caption lines, unmodified and legible (shot 1's line and shot 4's line). Nothing
else is required on screen for this shot. Each spoken limit is read from the record in the table
below it.

Narration: "What this is not: live data — the market copy behind this replay ends 29 September 2026. Not a
computed consequence: nothing here simulates what the trip cost. And where Gemini and the case's
own reading disagree, the disagreement is recorded, not hidden."

| Limit | Record |
|---|---|
| replay, not live; the copy ends 2026-09-29 23:55 | [strategy refresh](../../work/strategy-refresh-2026-10-14/strategy.md) (the BigQuery intervals row); the pages' own caption lines name the source and the replay |
| consequences are not computed | no screen computes an impact or a counterfactual; the what-if contract's `consequences: "uncomputed"` label is the repository's own statement of it ([what-if intent](../../work/whatif/intent.md)) |
| the return-cutoff disagreement | [live run](../../work/grid-desk/live-run-2026-10-14.md): at the return cutoff Gemini composed `challenges` while the case reading composes `supports`; recorded as an open finding, EVAL-8 |

Caption (burned in): `Limits: replay, not live · consequences not computed · one disagreement recorded, not hidden`

### Shot 8 — Where it runs (2:26–2:41, 15 s)

Screen: the grid page at the deployed URL, address bar visible; then the Judgment card's by-line
(line reused from shot 5). Runtime: `hosted`. Mode labels: `stored run` (the line shown),
`deterministic` (the pages).

On screen: the address bar on `ingrid-desk.web.app` (or the Cloud Run address, whichever was
recorded); the grid page served with its `/grid-data/<build>/…` files; the judgment by-line
naming `Vertex AI`.

Numbers, from the [performance baseline](../../work/performance/baseline.md) only — never a
number that is not in it:

- The grid page and all seven data files arrive from Firebase Hosting in **0.85 s** with the
  Cloud Run instance cold (run 3, 2026-10-14); repeat loads p50 0.22 s over 70 `x-cache: HIT`
  answers. Run 4 shows the same page ready in 0.86 s while the instance was still cold.
- The decision path after the session: p50 **1.68 s** (run 7, Cloud Build, five sessions).
- If a render measurement is quoted at all, it is run 5's cold browser visit: largest contentful
  paint **2.86 s** from Manila, and the baseline records the under-2 s intent as unmet at that
  location. Do not claim a rendering time that was not measured.
- Optional honest beat if there is room: the event page is a Cloud Run route and pays the
  instance start once (run 4 measured 6.51 s cold); after that it is warm.

Caption (burned in): `Firebase Hosting → Cloud Run · Artifact Registry · Firestore · Firebase Authentication · Vertex AI Gemini · BigQuery · grid page + data 0.85 s from Hosting, instance cold (baseline run 3)`

Narration: "It runs on Google Cloud: Firebase Hosting, Cloud Run, Artifact Registry, Firestore and
Firebase Authentication carry the site. Vertex AI Gemini ran on the real case. Measured: the grid
page and its data arrive from Hosting in 0.85 seconds, instance cold."

(Services aligned 2026-10-18 to the one [services table](../../work/polish-2026-10-18/services-table.md),
row order and state words, POLISH-2 item 11; 41 words against 39 before, trimmed from 55 in the
POLISH-2 rework round 1 after review finding 2: the burned-in caption carries BigQuery; the timing is REL-6's.)

### Shot 9 — Close (2:41–2:48, 7 s)

Screen: Grid page `/`, one held frame. Runtime: `hosted`. Mode label: `retrospective replay`.

On screen: the grid page as it was left; the caption line still legible.

Caption (burned in): `A justified no-change is a success`

Narration: "A justified no-change is a success."

No end-card claim about impact, forecast skill or savings: the closing frame and the spoken
close carry only the sentence above (the story's "no unsupported impact or forecast-skill
claim" rule, and [deck](deck.md) Appendix E).

## Timing and the check

- Windows tile from 0:00 and the plan ends at **2:48 = 168 s**, 2 s inside the task's 170 s and
  12 s inside E8's 180 s. The check below asserts all of that against this file.
- Narration is about 330 words: roughly 130 s of speech in a 168 s film, so most shots have a
  beat where the screen speaks for itself. Hold the frame rather than speeding up the delivery.
- Overrun rule, in order: shorten shot 5's table read (hold two rows instead of three), then
  shot 2's hover, then shot 3's clock step. Never cut shot 7 or shot 8; never extend past 2:48
  and never let the encoded duration reach 170 s.
- REL-6 measures the encoded duration rather than trusting the plan: `ffprobe -v error -show_entries
  format=duration -of default=nw=1:nk=1 <file>` and records it, with the transcript and the
  public link, in `video-receipt.md` and the REL-4 manifest. If the measured duration is not
  under 170 s, the fix is a re-cut inside the rule above, not a changed number here.

Check this file (run in this task; the results are in [Verification](#verification)):

```sh
/usr/bin/python3 - <<'PY'
import re
t = open('docs/competition/ai-builder-cup-2026/video-shotlist.md', encoding='utf-8').read()
rows = re.findall(r'^\| (\d+) \| (\d+):(\d\d) \| (\d+):(\d\d) \| (\d+) \| (.+?) \| (.+?) \|$', t, re.M)
assert [int(r[0]) for r in rows] == list(range(1, len(rows) + 1)), 'shot numbers are not 1..n'
secs = [int(r[5]) for r in rows]
end = [int(r[3]) * 60 + int(r[4]) for r in rows]
assert end[0] == secs[0] == 16, 'the first window does not start at 0:00'
assert all(end[i] - end[i - 1] == secs[i] for i in range(1, len(rows))), 'windows do not tile'
assert end[-1] == sum(secs) == 168 < 170, (end[-1], sum(secs))
modes = r'retrospective replay|deterministic|stored run'
bad = [r[0] for r in rows if '/' not in r[6] or not re.search(modes, r[7])]
assert not bad, f'a shot names no screen route or no mode label: {bad}'
lines, words, i = t.splitlines(), 0, 0
while i < len(lines):
    if lines[i].startswith('Narration:'):
        block = [lines[i].split(':', 1)[1].strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '```')):
            block.append(lines[i].strip())
            i += 1
        words += len(' '.join(block).split())
    i += 1
print(f'{len(rows)} shots, {sum(secs)} s, ends {end[-1] // 60}:{end[-1] % 60:02d}, narration {words} words')
PY
```

## Recording discipline (carried from the story; musts for REL-6)

1. One continued take of the deployed build. Never splice a success from a different input or a
   different session as though it were the displayed run.
2. Every model output on screen is shown with its stored-run label and its receipt (shot 5), and
   the narration states it is a recorded run. Never call the stored judgment live.
3. Captions burned in, readable cursor, no window toggling that hides the address bar.
4. Read figures off the screen; pre-typed numbers in the narration or captions are limited to the
   ones this file pins with a source (the receipt digests, 83.7 MW, 492 of 619 and 127, the baseline
   timings).
5. The phrase "justified no-change" is the deck's and the story's; the video does not add an
   impact, savings, blackout or forecast-skill claim.
6. Before the take, check the mode and the landing frame, and stop if either is wrong instead of
   recording a substitute:

```sh
curl -s https://ingrid-desk.web.app/health                  # {"status":"ok","mode":"hosted",...}
```

   then open `/` and confirm: Visayas pressed; clock at 21 Sep 2026 13:40; the brief card and its
   "written by code" line; the caption's located count; the Reviews card with PEDC; the map
   legend and the pending matrix; then open `/event/pedc-u2-2026-09-21` and confirm the judgment
   card carries `challenges` with its receipt, and the Decision form's button is enabled by a
   reason. If any of these is missing, hand back to the orchestrator rather than recording a
   different screen.

## Deviations from the story table, for the reviewer

1. **Timing.** The story's nine rows sum to exactly 170 s; this plan trims shot 3 to 16 s and
   shot 9 to 7 s so the total is 168 s and "under 170 s" holds with margin. The journey, the
   screens and the content are the story's.
2. **The 29 September end of the market copy is spoken, not printed.** The pages' caption lines
   carry the source and the replay day (21 Sep 2026) but no end date; putting the dataset's end
   on screen would be a design-file change, which is outside this task's paths (the design files
   belong to the orchestrator). Shot 7 therefore attributes that limit to the narration and to
   the strategy record.
3. **The Judgment by-line reads `· live`.** That is the stored run's own label for the transport
   it was made with; the video labels the card a *stored run* and says no call happens during
   recording. Both statements are true of the artifact; the shot list keeps them together so a
   reviewer can check neither is a mislabel.
4. **The `Retain` value.** The video retains the register value (83.7 MW), the case's accepted
   value; the story's row 105-130 says the same. A revise take would be a different decision and
   would need a reason and a new value typed on screen.

## Verification

Run in this worktree on 2026-10-15 with `/usr/bin/python3` 3.14.4, before the commit on
`task/REL-3`:

```sh
$ /usr/bin/python3 scripts/repo.py check
Checked 342 Markdown files, 2150 local links, 8 skills; bootstrap 1392 words.
PASS

$ /usr/bin/python3 -m unittest discover -s tests
Ran 863 tests in 14.801s

OK (skipped=35)

$ /usr/bin/python3 scripts/plan.py scope REL-3 feat/h1-api-persistence
OK: all changed files inside REL-3 allowed paths

$ /usr/bin/python3 - <<'PY' … the shot-table check above …
9 shots, 168 s, ends 2:48, narration 329 words
```

Re-run 2026-10-18 (POLISH-2 rework round 1, review finding 2) on this file with the same script:
`9 shots, 168 s, ends 2:48, narration 377 words`. The count rose from 329 with the sign-in,
located-count and services wording of 2026-10-18; the three dated notes under shots 2, 6 and 8
are separated from the narration by a blank line so the script does not count them.

The `repo.py check` run is the task's verify command; it proves the new file's links resolve and
the repository's rules hold. The check above proves the two acceptance items this file owns:
nine shots, each naming a screen route and a mode label, totalling 168 s (under 170). Its
non-vacuity was exercised too: a copy with one row's mode label removed fails it (row 5), a copy
with one row's route removed fails it (row 9), and a copy whose last window is stretched to 169 s
fails the total. Nothing here is a claim about a runtime; the recorded-video evidence is REL-6's.

### Post-commit verification

The verify command, the full suite and the scope check were re-run on the committed tree (commit
`8351dd8`, the deliverable commit on `task/REL-3`) and again on the final tip, with the same
results:

```sh
$ /usr/bin/python3 scripts/repo.py check                    → PASS (342 Markdown files, 2150 local links)
$ /usr/bin/python3 -m unittest discover -s tests            → Ran 863 tests … OK (skipped=35)
$ /usr/bin/python3 scripts/plan.py scope REL-3 feat/h1-api-persistence
                                                            → OK: all changed files inside REL-3 allowed paths
```

## Unfinished items and the exact next action

- Nothing in this task's acceptance is unfinished: every shot names a screen and mode label from
  the tables above, and the total is 168 s.
- The next action is **independent review of `task/REL-3`**, then **REL-6 records the video**
  against this file. REL-4 should carry the measured duration and the revision from the REL-6
  receipt; if the recording finds the deployed revision no longer serves the landing frame (for
  example after PERF-4's staged draw), stop and hand back here rather than adapting the shots.
- Standing hand-backs to the orchestrator: the owner's plant coordinate file will change the
  located count in the caption (492 of 619, 127 pending, recounted from the release 22 build's `sites.json`) and the pending matrix; the design files are
  the orchestrator's, so any on-screen wording change (e.g. printing the replay's end date) is a
  new design decision, not a shot-list edit.
