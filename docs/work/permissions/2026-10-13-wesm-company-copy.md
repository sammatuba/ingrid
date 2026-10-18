# Permission record: company WESM copy and SO advisory feed for Grid Nowcast

Status: **signed**, 2026-10-13. Drafted the same day by the orchestrator seat from the owner's
decision in the [foundation review](../foundation-review-2026-10-13/strategy.md), round 2, and
signed by the owner below. Records may cite it from this date.

Permission identifier (the `permission_ref` value records cite): `perm:wesm-company-copy:2026-10-13`

## What is permitted

| Dataset | Location | Use |
|---|---|---|
| System operator advisories (MPI message service copy) | `gs://grid-nowcast-fivemin/wesm/FiveMin`, BigQuery `grid-nowcast.grid_raw.ext_others_mpi_advisories` | Capture as source versions and passages; quoting message text in records, fixtures, tests, the workspace and the working paper |
| Registered capacity (generation, ancillary) | same bucket; `grid_raw.ext_others_regcap_*` | Candidate identity mappings; capacity values as assumptions' prior values |
| Dispatch, prices and schedules (RTD, DAP, HAP, WAP) | same bucket; `grid_raw.ext_*` | Corroboration and numerical baselines; never counted as evidence known at a cutoff while `RUN_TIME` is absent |
| Registered Capacity List (IEMOP registration snapshot) | `gs://mecores/wesm/Misc/Registration_Registered_Capacity_List/data.parquet` (company account) | Unit attributes, plant grouping by node prefix, prior capacity values |
| Outage schedules | same bucket; `grid_raw.ext_rtd_outage_schedules` and variants | Corroboration; absence of a row is not evidence of availability |

Purpose: the Grid Nowcast change-review desk, its evaluation, the Google Cloud AI Builder Cup
2026 submission and the follow-on research record. Period: from the signature date until
revoked in a later version of this file.

## What is not permitted

- Redistribution of the bulk copy or any extract beyond the repository, the deployed demo and
  the submission materials.
- Any credential, bucket key or project configuration in Git.
- Use of any dataset not listed here without a new version of this record.

## Signature

Owner: Sam Matuba, project owner   Date: 2026-10-13

Revision history: 2026-10-13 draft (orchestrator seat); 2026-10-13 signed by the owner, registration-list path added.

## Version 2 (2026-10-14): public display on the demo

Approved by the owner in session on 2026-10-14, in answer to "May the public demo show the company WESM data: regional
prices, demand, reserves, and NGCP advisory text?": "yes all of it". Signed by the owner in session on 2026-10-14 ("data permission ok"); records may
cite version 2 from this date. The identifier is unchanged (`perm:wesm-company-copy:2026-10-13`); this section widens the use column.

| Dataset | Added use |
|---|---|
| Dispatch, prices and schedules (RTD, DAP, HAP, WAP), including per-resource LMPs, HVDC schedules, congestions and outage schedules | Public display on the deployed demo, in the video and in the deck: regional and per-node figures over 21–29 September 2026 as a labelled replay, with a source line |
| System operator advisories | Public display of advisory text and times on the demo, in the video and in the deck |
| Registered capacity | Public display of unit names and capacities on the demo |

Still not permitted: the bulk copy or any extract in Git or in the public source export; data files ship only inside the
deployed image and are excluded from the release export.

New public sources (not company data), each row carrying its own provenance in the location crosswalk:
Natural Earth administrative boundaries (public domain); plant locations from public pages (DOE plant lists,
operator pages, OpenStreetMap under ODbL with attribution, Wikipedia/Wikidata), cited per row.

Owner signature (version 2): Sam Matuba, project owner, in session ("data permission ok")   Date: 2026-10-14
