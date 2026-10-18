# `tests/fixtures/grid/plants/` — plant status fixture (synthetic)

Synthetic and hand-written for ericka-desk slice 6 (E8, E18, E29;
`docs/work/ericka-desk-2026-10-18/intent.md`). No real WESM row, plant, operator message or
outage record is here. The five site codes are the asset fixture's own (`../asset/payload`), so
the asset pages' harness (`../asset/render.mjs --bake tests/fixtures/grid/plants`) reads these
shared records beside that payload.

| File | What it holds |
|---|---|
| `sites.json` | The five fixture sites; two carry a name that states a technology, which the pages must leave out. |
| `advisories.json` | Eight notices: an event-mapped trip and a return for `08PEDC`; a trip, a return and a second trip for `04GEN`; a derating for `08SAMPLE`; one trip whose words fit both `08SAMPLE` and `04GEN` (Unclear for both, counted for neither); one `03LUZ` trip whose text states a technology and a fuel. |
| `events.json` | The one event, mapping `V133937` to `08PEDC`. |
| `outages.json` | Three outage-bake records in the shape slice 4 writes: one sure with a lag, one below 50% match confidence (Unclear), one sure with no lag (`null`). |
