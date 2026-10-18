# Case brief: PEDC Unit 2 trip and return, 2026-09-21

**Status: worked real case, assembled and replayed (task EVAL-5); its review is open.** Every
record is real company-copy data cited to
[`perm:wesm-company-copy:2026-10-13`](../../work/permissions/2026-10-13-wesm-company-copy.md);
the judgment is a deterministic script and is labelled so; no disposition is pre-written. Pack:
[evidence-manifest.json](evidence-manifest.json), [mappings.json](mappings.json),
[review.md](review.md), [outlook-revision.md](outlook-revision.md),
[scenario-proposal.md](scenario-proposal.md), [evaluation.md](evaluation.md); task record:
[packet.md](packet.md). Machine fixture:
[tests/fixtures/pedc-u2-2026-09-21/case.json](../../../tests/fixtures/pedc-u2-2026-09-21/case.json).

## Assembly and timeline (what is real and what is reconstruction)

The case was **assembled on 2026-10-14 by the EVAL-5 case assembly** (`eval-5-case-assembly`,
the orchestrator and executor seats) from the company copy — the case record's `assembly`
block, the reviewed mapping's `reconstruction` block and the seed's rationale each say so.
Within the case: every **source** keeps the clock it really carries — the four advisories'
posting instants (`known_at`), the register run's first trading day. The desk's own acts and
the replay's derived records sit on the **2026-09-21 timeline as a reconstruction** at the
positions the compile replay requires (the reviewed mapping and the seed must precede the pair
cutoffs, so a real 2026-10-14 position would block every compile). No analyst session ran; the
desk's disposition at each cutoff is left to the demo's judge or the analyst, and this pack
records no disposition of its own.

## Question and user

Does the 2026-09-21 forced outage of generating unit `08PEDC_U02` change the desk's accepted
available-capacity position for that unit and day, and what does the evidence support at each
information cutoff? User: the Grid Nowcast review desk, working the day's advisory feed for the
Visayas grid.

## Prior assumption (the before-state)

| Field | Value |
|---|---|
| Entity | `08PEDC_U02`, `GeneratingUnit` |
| Proposition | The registered maximum available capacity of `08PEDC_U02` holds for 2026-09-21 |
| Value | 83.7 MW (`quantity_kind: available_capacity`, unit MW) — **read from the register run**, never typed by hand |
| Valid period | 2026-09-21 (half-open: 2026-09-21 to 2026-09-22) |
| Mapping | `mapping:regcap:08PEDC_U02:PEDC:83.7:2026-02-05` revision 2, **reviewed** by the case assembly (2026-10-14) at the reconstructed `reviewed_at` position 2026-09-21 00:05 (+08:00), evidenced by the register run’s source version |
| Accepted | Seeded by the case assembly on 2026-10-14 at the reconstructed day-start position 2026-09-21 00:10 (+08:00) from the register run (2026-02-05 to 2026-09-29, 83.7 MW, participant PEDC) |

The seeded position is the desk's **assumed** day-level availability; it is not a claim that the
unit was available for the whole day. The evidence below tells against that reading.

## Evidence scope: advisory-only

Advisory-only: the case's evidence is the four NGCP advisories of 2026-09-21 registered in
[evidence-manifest.json](evidence-manifest.json) — V133937 (trip at 1334H), V135622 (MLD at
1338H), V141257 (yellow alert 1700H–2000H) and V155556 (re-online at 1507H). **No external
document was supplied**, so none is part of the case; if the owner supplies one it becomes a
fifth source with its own version, passage and first-availability record. The dispatch
corroboration is attached but is never counted as evidence at a cutoff
(`RUN_TIME absent from the copy`; its publication instant is unknown and its `published_at` is
a labelled approximation).

## Cutoffs and horizon

Two cutoff pairs (working paper 5.4): **trip** T0 2026-09-21 13:39:36 → T1 13:39:37 (+08:00,
around V133937's posting), and **return** T0 15:55:55 → T1 15:55:56 around V155556's. Horizon:
the case day; the paired diff is the observable. Exact instants and the per-cutoff omissions
are in [evidence-manifest.json](evidence-manifest.json).

## Baseline workflow and disposition

Baseline workflow: the desk reads the day's advisories, resolves the unit's identity against
the register, compares the evidence with the assumed position and records a disposition. **This
case records no disposition**: both pairs end judged by the scripted backend
([review.md](review.md#model-assisted-readings-as-run)) and the decision at each cutoff is made
by the demo's judge or the analyst on their own copy (review 1, 2026-10-14). A matched manual
baseline session for this case (EVAL-7) is **cut**; none was run —
[evaluation.md](evaluation.md) states what that leaves unmeasured, and records the live probe
run the orchestrator made on this case on 2026-10-14.
