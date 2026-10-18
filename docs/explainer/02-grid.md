# The Philippine grid and the market

This chapter gives you the facts about the grid that the rest of the explainer needs. Every number
comes from a committed record, named at the end.

## Three grids

The Philippines has three grids: Luzon, Visayas and Mindanao. Two undersea direct-current links
join them. Power flows across a link in either direction, as the market schedules it. Each grid
has its own demand, its own price and its own reserve at every moment.

<!-- widget: three-grids -->

## The operator and the market

NGCP operates the grid. When something happens, NGCP posts a short notice. We call it an
advisory. One example from 21 September 2026: "PEDC Unit 2 tripped at 13:34." A trip is a sudden
shutdown. NGCP also posts a yellow alert when the reserve is low, and drops some load for a short
time when it must protect the grid.

The market is WESM, the Wholesale Electricity Spot Market. Every five minutes it records a price
and a schedule for every plant and every load point. On 21 September 2026 the data covered 566
generating resources at 330 sites and 653 load points at 378 sites. The company copy that the
project uses now ends on 14 October 2026. The site replays 21 to 29 September 2026. It is not live.

A register lists every plant unit and the power it can supply. The desk reads the assumption
"PEDC Unit 2 supplies 83.7 MW" from that register. Nobody typed the number.

## The day we replay

The site shows 21 September 2026, with the clock set just after the trip. Move the clock below.
The events are the four notices of that day.

<!-- widget: pedc-clock -->

The unit was off for 93 minutes. The notices do not say how much power the unit supplied during
the outage or right after it. That gap is why the analyst, not the AI, makes the final call.

## What the grid page shows

The first screen of the site is the grid page. It shows, for the chosen grid and the chosen time:

- One paragraph of plain text. Code writes it from the figures. Every clause has a number and a time.
- A table of the three grids: demand, price, reserve condition, shortfall and imports.
- A map of plant sites, coloured by price. The caption says how many sites have a real position.
- The flows on the two undersea links.
- The operator's messages, each with a button to review its impact.
- One 24-hour chart with a source line.
- A replay clock from 21 to 29 September 2026.

One caption line holds every disclaimer: the data source, the replay date, and the count of sites
without a real position. The site never shows a feature that is not connected.

Every element is explorable. Click a figure and the chart shows that series with its source.
Click a plant site and a detail card opens with its code, capacity, position, two sparklines and
the messages that name it. Click a message and the clock moves to its time, the site it names
lights up, and its detail opens. Click an undersea link for its flow and its block notices.

Hover the chart for a value and click it to move the clock. Beside the chart, a small panel
draws the day as a path: each typed message adds its learned vector. Chapter 26 explains it.

<!-- quiz -->
Q: What does the site show when you open it?
- Live data from the grid right now
- [x] Recorded data from September 2026, with a replay clock
- A forecast for next week
Why: The site replays recorded days from September 2026. Every time on the site is a replay time and says so.
<!-- /quiz -->

## Sources for this chapter

- The notices, their times and the 83.7 MW: the [PEDC case brief](../cases/pedc-u2-2026-09-21/brief.md).
- The resource and site counts, the data span, and the copy rules for the grid page: the
  [strategy refresh of 14 October](../work/strategy-refresh-2026-10-14/strategy.md).
- The map count: the [status page](../status.md).
