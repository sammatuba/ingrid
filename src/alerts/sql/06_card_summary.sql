-- grid_ontology.card_summary(region, t, mode) (ontology intent, owner decision of 2026-10-17 from the
-- trading desk): one row on top of the driver card with the five alert attributes the desk asked for.
-- Every field is derived here, in SQL, from the recorded and checked card and ranking of that cutoff and
-- mode of that region (grid_ontology.recorded_cards and recorded_drivers, keyed by region, written by
-- scripts/ontology/record_cards.sh once ontology_checks.sql passes); nothing is typed per case. A cutoff that was not recorded gives
-- no facts, so severity is unrated and confidence Low.
--
-- severity (High, Medium, Low, or unrated):
--   unrated  the card has no price band at t in this mode (the inputs are not known), never a guess;
--   High     price band very_high or extreme (at or above the high-price bound of
--            03_ref_regions_thresholds.sql), or reserves deficient, or a red alert in the card's window;
--   Medium   price band high, or reserves thinning, or a yellow alert, or a likely-driver score >= 0.9;
--   Low      otherwise.
-- financial_impact: always "Not available: needs portfolio data (positions, contracts, load nodes)".
--   No peso figure is ever computed: there is no portfolio data, and the owner's rule is never to assume.
-- confidence (High, Medium, Low) with its counts:
--   High     at least half the shown facts evidence-known, none withheld, no unconfirmed match;
--   Low      no facts, more facts withheld than shown, or under 10% evidence-known with more than 10
--            withheld or more than 5 unconfirmed;
--   Medium   otherwise.
-- relationship_trail: the top two ranked likely drivers, plus every tripped-unit message, as chains ending
--   at the price. A unit reaches its region through its accepted locatedIn; its plant grouping (partOf,
--   proposed in 01_entities_relations.sql) is shown only as "plant grouping ... proposed, unreviewed",
--   never as a confirmed link; a message reaches its plant only through an accepted alias, and a link
--   through an uncertain alias is marked "unconfirmed".
-- what_to_check: one to three factual follow-ups from the same drivers and messages. Never trading
--   advice: no buy, sell, hedge or contract wording (checked).

CREATE OR REPLACE TABLE FUNCTION `grid-nowcast.grid_ontology.card_summary`(card_region STRING, t TIMESTAMP, card_mode STRING)
OPTIONS (description = 'One summary row for the driver card: severity, financial_impact (always not available), confidence, relationship_trail, what_to_check. Rules in scripts/ontology/sql/06_card_summary.sql.')
AS
WITH
-- the recorded, checked card and ranking for this cutoff and mode (scripts/ontology/record_cards.sh):
-- calling driver_card and likely_drivers inside this function exceeds BigQuery's query planner
card AS (SELECT * EXCEPT (case_id, region) FROM `grid-nowcast.grid_ontology.recorded_cards`
         WHERE region = card_region AND mode = card_mode AND cutoff_utc = TIMESTAMP_ADD(t, INTERVAL 5 MINUTE)),
drv AS (SELECT * EXCEPT (case_id, region) FROM `grid-nowcast.grid_ontology.recorded_drivers`
        WHERE region = card_region AND mode = card_mode AND cutoff_utc = TIMESTAMP_ADD(t, INTERVAL 5 MINUTE)),
rel AS (SELECT * FROM `grid-nowcast.grid_ontology.relations`),
ent AS (SELECT entity_id, public_label FROM `grid-nowcast.grid_ontology.entities`),
reg AS (SELECT public_label AS region_label FROM ent WHERE entity_id = CONCAT('region:', card_region)),
f AS (SELECT * FROM card WHERE section = 'fact'),
price AS (
  SELECT ANY_VALUE(IF(predicate = 'price_capped_median', value_num, NULL)) AS price,
    ANY_VALUE(IF(predicate = 'price_band', value_text, NULL)) AS band,
    ANY_VALUE(IF(predicate = 'reserve_condition', value_text, NULL)) AS reserves,
    LOGICAL_OR(predicate = 'grid_alert' AND REGEXP_CONTAINS(value_text, r'(^|; )red ')) AS red,
    LOGICAL_OR(predicate = 'grid_alert' AND REGEXP_CONTAINS(value_text, r'(^|; )yellow ')) AS yellow
  FROM f
),
top AS (SELECT MAX(family_score) AS score FROM drv WHERE rank IS NOT NULL),
ranked AS (  -- the top two families, each with its strongest indicator
  SELECT rank, family, indicator, value_at_t, baseline_median, indicator_score
  FROM drv WHERE rank IS NOT NULL AND rank <= 2 AND status = 'scored'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY family ORDER BY indicator_score DESC, indicator) = 1
),
counts AS (
  SELECT COUNTIF(section = 'fact') AS n_fact,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'evidenced') AS n_evidenced,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'assumed') AS n_assumed,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'assumed' AND availability_assumption = 'A-RT') AS n_rt,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'assumed' AND availability_assumption = 'A-RUN') AS n_run,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'assumed' AND availability_assumption = 'A-FUEL') AS n_fuel,
    COUNTIF(section = 'fact' AND availability_at_cutoff = 'after_cutoff') AS n_late,
    IFNULL(SUM(n_withheld), 0) AS n_withheld,
    COUNTIF(section = 'unconfirmed') AS n_unconfirmed
  FROM card
),
-- tripped-unit messages: confirmed ones through the accepted plant, unconfirmed ones marked
trips AS (
  SELECT k.value_text, k.match_confidence,
    IF(k.match_confidence = 'confirmed', k.object_id, k.candidate_id) AS plant_id,
    REPLACE(IF(k.match_confidence = 'confirmed', k.object_id, k.candidate_id), 'plant:', '') AS plant_label
  FROM card AS k
  WHERE k.predicate = 'mention_tripped' AND k.section IN ('fact', 'unconfirmed')
    AND k.match_confidence IN ('confirmed', 'unconfirmed')
),
links AS (  -- congested HVDC links connected to the region
  SELECT DISTINCT REPLACE(subject_id, 'hvdc:', '') AS link FROM f
  WHERE predicate = 'hvdc_congested' AND value_text = 'Y'
),
outage_units AS (
  SELECT DISTINCT f.object_id AS unit_id, REPLACE(f.object_id, 'unit:', '') AS unit, r.dst_id AS plant_id
  FROM f LEFT JOIN rel AS r ON r.src_id = f.object_id AND r.relation = 'partOf'
  WHERE f.predicate = 'scheduled_outage' AND f.object_id IS NOT NULL
),
segments AS (
  SELECT 0 AS ord, CONCAT(t.value_text, ' (message) → ', IFNULL(t.plant_label, '?'), ' (plant',
    IF(t.match_confidence = 'confirmed', '', ', unconfirmed'), ') → ', reg.region_label) AS seg
  FROM trips AS t CROSS JOIN reg
  UNION ALL
  SELECT r.rank, CASE
      WHEN r.family = 'S' AND r.indicator = 'hvdc_links_congested' AND (SELECT COUNT(*) FROM links) > 0
        THEN CONCAT((SELECT STRING_AGG(link, ', ' ORDER BY link) FROM links), ' (HVDC) congested → ', reg.region_label)
      WHEN r.family = 'S' AND r.indicator = 'import_share'
        THEN CONCAT('import share ', FORMAT('%.3f', r.value_at_t), ' (28-day median ', FORMAT('%.3f', r.baseline_median), ')',
                    IF((SELECT COUNT(*) FROM links) > 0, CONCAT(' over ', (SELECT STRING_AGG(link, ', ' ORDER BY link) FROM links), ' (HVDC, congested)'), ''),
                    ' → ', reg.region_label)
      WHEN r.family = 'S' THEN CONCAT('reserve shortfall ', FORMAT('%.0f', r.value_at_t), ' MW → ', reg.region_label)
      WHEN r.family = 'D' THEN CONCAT('demand ', FORMAT("%'.0f", r.value_at_t), ' MW (28-day median ', FORMAT("%'.0f", r.baseline_median), ' MW) → ', reg.region_label)
      WHEN r.family = 'O' AND r.indicator = 'linked_derated_mw'
        THEN CONCAT('derated plants in the latest grid update, accepted matches only, ', FORMAT("%'.0f", r.value_at_t),
                    ' MW (28-day median ', FORMAT("%'.0f", r.baseline_median), ' MW) → ', reg.region_label)
      WHEN r.family = 'O' THEN CONCAT(IFNULL((SELECT STRING_AGG(DISTINCT CONCAT(u.unit, ' (unit', IF(u.plant_id IS NULL, '', CONCAT('; plant grouping ', REPLACE(u.plant_id, 'plant:', ''), ' proposed, unreviewed')), ')'), '; ')
                                             FROM outage_units AS u), 'no unit linked'),
                                      ' → ', reg.region_label, ', ', FORMAT("%'.0f", r.value_at_t), ' MW scheduled out')
      WHEN r.family = 'F' THEN CONCAT('fuel cost baseline (percentile ', FORMAT('%.0f', 100 * r.indicator_score), ') → ', reg.region_label)
    END
  FROM ranked AS r CROSS JOIN reg
),
checks AS (
  SELECT 0 AS ord, CONCAT('check the return time of ', value_text, ' in later operator messages and the outage schedule',
                          IF(match_confidence = 'confirmed', '', ' (plant match unconfirmed)')) AS item
  FROM trips
  UNION ALL
  SELECT r.rank, CASE
      WHEN r.family = 'S' AND (SELECT COUNT(*) FROM links) > 0
        THEN CONCAT('watch ', (SELECT STRING_AGG(link, ', ' ORDER BY link) FROM links), ' congestion in the next intervals')
      WHEN r.family = 'S' THEN 'check the reserve margin and import flow in the next intervals'
      WHEN r.family = 'D' THEN 'check demand in the next intervals against its 28-day median at this hour'
      WHEN r.family = 'O' AND r.indicator = 'linked_derated_mw' THEN 'check the derated list in the next grid update'
      WHEN r.family = 'O' THEN 'check the schedule records of the units out for revisions'
      WHEN r.family = 'F' THEN 'check the next monthly fuel price publication'
    END
  FROM ranked AS r
)
SELECT card_region AS region, card_mode AS mode, (SELECT ANY_VALUE(cutoff_utc) FROM card) AS cutoff_utc,
  CASE
    WHEN p.band IS NULL THEN 'unrated'
    WHEN p.band IN ('very_high', 'extreme') OR p.reserves = 'deficient' OR p.red THEN 'High'
    WHEN p.band = 'high' OR p.reserves = 'thinning' OR p.yellow OR tp.score >= 0.9 THEN 'Medium'
    ELSE 'Low'
  END AS severity,
  IF(p.band IS NULL, 'the price band at t is not known in this mode',
     CONCAT('price band ', p.band, IF(p.price IS NULL, '', CONCAT(' (', FORMAT("%'.0f", p.price), ' PHP/MWh)')),
            '; reserves ', IFNULL(p.reserves, 'not stated'),
            '; alert ', CASE WHEN p.red THEN 'red' WHEN p.yellow THEN 'yellow' ELSE 'none' END,
            '; top likely-driver score ', IFNULL(FORMAT('%.2f', tp.score), 'none'))) AS severity_reason,
  'Not available: needs portfolio data (positions, contracts, load nodes)' AS financial_impact,
  CASE
    WHEN c.n_fact = 0 OR c.n_withheld > c.n_fact
      OR (SAFE_DIVIDE(c.n_evidenced, c.n_fact) < 0.1 AND (c.n_withheld > 10 OR c.n_unconfirmed > 5)) THEN 'Low'
    WHEN SAFE_DIVIDE(c.n_evidenced, c.n_fact) >= 0.5 AND c.n_withheld = 0 AND c.n_unconfirmed = 0 THEN 'High'
    ELSE 'Medium'
  END AS confidence,
  FORMAT('%d of %d facts evidence-known, %d assumption-known (A-RT %d, A-RUN %d, A-FUEL %d), %d shown after the cutoff (hindsight); %d withheld; %d unconfirmed matches listed',
         c.n_evidenced, c.n_fact, c.n_assumed, c.n_rt, c.n_run, c.n_fuel, c.n_late, c.n_withheld, c.n_unconfirmed) AS confidence_reason,
  IF((SELECT COUNT(*) FROM segments WHERE seg IS NOT NULL) = 0, 'no ranked driver in this mode',
     CONCAT((SELECT STRING_AGG(seg, '; ' ORDER BY ord, seg) FROM segments WHERE seg IS NOT NULL),
            IF(p.price IS NULL, '', CONCAT(' → price ', FORMAT("%'.0f", p.price), ' PHP/MWh')))) AS relationship_trail,
  ARRAY(SELECT item FROM checks WHERE item IS NOT NULL ORDER BY ord, item LIMIT 3) AS what_to_check,
  c.n_fact, c.n_evidenced, c.n_assumed, c.n_withheld, c.n_unconfirmed
FROM price AS p CROSS JOIN top AS tp CROSS JOIN counts AS c;
