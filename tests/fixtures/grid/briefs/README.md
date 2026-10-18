# Briefings and findings fixture (synthetic)

A small, **entirely synthetic** bake of the four files `scripts/grid/briefs.py` reads:
`regions.json`, `hvdc.json`, `advisories.json` and `events.json`, in the shapes
`scripts/grid/build_data.py` writes. `tests/test_grid_briefs.py` runs the composer over it offline:
no real WESM row, no real plant name and no real operator message appears here.

The fixture is one replay day of twelve five-minute intervals, 21 September 2026, 13:00 to 13:55,
built so that every declared rule of `scripts/grid/findings_rules.json` fires exactly where the
test says it does. Its timestamps use the real bake's own shapes — `YYYY-MM-DDTHH:MM` on the two
interval axes, `YYYY-MM-DDTHH:MM:SS` on the messages and the event — so the tests read the strings
production reads, and the last message is posted before the day's last interval, as a fed message
is:

| Path | What it exercises |
|---|---|
| `bake/regions.json` | Luzon's median price at the page's declared cap value on the last interval (F1, F2) and above the fixture's own p90 (F4); Visayas at the replay's lowest median price (F3) and below its p10 (F5); a Mindanao reserve shortfall holding three intervals (F8); a Visayas curtailment holding two (F9); **every Mindanao price null**, so the price rules stay silent there and the briefing writes the not-stated clause (C6) |
| `bake/hvdc.json` | a congested run of three intervals on Mindanao–Visayas (F6) and a reversed flow of three on Visayas–Luzon (F7), the direction read from the sign |
| `bake/advisories.json` | five marked messages — two trips (one carrying no grid header), a load dropping, a yellow and a red alert (F10) — a return to service (F11), and a notice the briefing never quotes |
| `bake/events.json` | the reviewable event the trip message opened, so the briefing of 21 September names it with its time and links `/event/syn-bay-unit-2-trip` (F12) |

`panel-harness.mjs` is not data: it is the panel's own click path run on a small DOM, offline — no
browser, no network, no library. It mounts `src/grid/briefs.js` over the two composed files and
checks that one click on a chip draws the feed once however many redraws ran before it (the chips
persist, so a handler bound per node would stack), and that an entity and the event link still
reach the page's callbacks after `setGrid` has replaced the briefing paragraph. Its shim models
the browser's own dispatch (a listener added while an event runs does not run for that event) and
throws on a selector it does not know, so a gap is a failure rather than a silent pass.
`tests/test_grid_briefs.py` runs it where node exists.

Run the fixture through the composer with:

```sh
/usr/bin/python3 scripts/grid/briefs.py --check --data tests/fixtures/grid/briefs/bake
```

Run the panel harness over the composed files with:

```sh
node tests/fixtures/grid/briefs/panel-harness.mjs --module src/grid/briefs.js \
     --briefs <briefs.json> --findings <findings.json>
```

The real bake is company WESM data: it lives in `build/grid-data/` inside the deployed image,
never in Git and never under `tests/fixtures/`.
