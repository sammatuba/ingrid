"""The SQL the checks run: new-interval detection, the threshold test and the live driver card.

Times: `grid_curated.labels.interval_start` stores Manila civil time in a TIMESTAMP (the sources'
convention), so the threshold queries take civil-time parameters written as UTC. The ontology's table
functions take a real instant: the 13:40 Manila interval is TIMESTAMP '2026-09-21 13:40:00+08'.

The live card is `grid_ontology.card_summary`'s own SQL (vendored byte for byte in
src/alerts/sql/06_card_summary.sql; tests/test_alerts.py keeps the copy identical to
scripts/ontology/sql/06_card_summary.sql) run over this interval's `driver_card` and `likely_drivers`
in temporary tables. The recorded function reads only the checked demo cards, and calling the two
table functions inside it exceeds BigQuery's planner, so one script computes both first.
Measured on the PEDC case (CVIS, 21 Sep 2026 13:40, assumed): 388 MB billed, about 36 s.
"""
from pathlib import Path

PROJECT = 'grid-nowcast'
LABELS = '`grid-nowcast.grid_curated.labels`'
CARD_SUMMARY_SQL = Path(__file__).resolve().parent / 'sql' / '06_card_summary.sql'
RECORDED_CARDS = '`grid-nowcast.grid_ontology.recorded_cards`'
RECORDED_DRIVERS = '`grid-nowcast.grid_ontology.recorded_drivers`'
FINAL_SELECT = '\nSELECT card_region AS region, card_mode AS mode,'
BASELINE_DAYS = 28

LATEST_INTERVAL = (f"SELECT FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M', MAX(interval_start)) AS latest FROM {LABELS} "
                   f"WHERE price_capped_median IS NOT NULL")

# Prices in (after, until] for the regions, each with its baseline: the median of the same region at the
# same Manila time of day on the 28 days before (the likely-drivers ranking's baseline window).
THRESHOLD = f"""
WITH cand AS (
  SELECT interval_start, region_code, price_capped_median AS price, price_band
  FROM {LABELS}
  WHERE interval_start > @after AND interval_start <= @until AND region_code IN UNNEST(@regions)
    AND price_capped_median IS NOT NULL
),
base AS (
  SELECT c.interval_start, c.region_code,
    APPROX_QUANTILES(b.price_capped_median, 2)[OFFSET(1)] AS baseline_median, COUNT(b.price_capped_median) AS baseline_n
  FROM cand AS c JOIN {LABELS} AS b
    ON b.region_code = c.region_code
   AND b.interval_start >= TIMESTAMP_SUB(@after, INTERVAL {BASELINE_DAYS + 1} DAY) AND b.interval_start < @until
   AND EXTRACT(TIME FROM b.interval_start) = EXTRACT(TIME FROM c.interval_start)
   AND b.interval_start < c.interval_start
   AND b.interval_start >= TIMESTAMP_SUB(c.interval_start, INTERVAL {BASELINE_DAYS} DAY)
  GROUP BY 1, 2
)
SELECT FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M', c.interval_start) AS interval_manila, c.region_code AS region,
  c.price, c.price_band, b.baseline_median, IFNULL(b.baseline_n, 0) AS baseline_n
FROM cand AS c LEFT JOIN base AS b USING (interval_start, region_code)
ORDER BY interval_manila, region
"""


def civil(interval_manila):
    """'2026-09-21T13:40' as the labels table's civil-time TIMESTAMP literal value."""
    return interval_manila.replace('T', ' ') + ':00+00:00'


def instant(interval_manila):
    """'2026-09-21T13:40' as the real instant the ontology functions take."""
    return interval_manila.replace('T', ' ') + ':00+08:00'


def card_script():
    """The live card script: params @region STRING, @t TIMESTAMP (an instant), @mode STRING.

    Its one result row holds `alert_json`, a JSON string with the summary row and the ranked
    likely-driver rows.
    """
    source = CARD_SUMMARY_SQL.read_text(encoding='utf-8')
    body = source[source.index('\nAS\nWITH\n') + len('\nAS\n'):]
    cut = body.index(FINAL_SELECT)
    ctes, final = body[:cut], body[cut + 1:].rstrip().rstrip(';')
    if ctes.count(RECORDED_CARDS) != 1 or ctes.count(RECORDED_DRIVERS) != 1:
        raise ValueError('card_summary no longer reads the recorded tables once each; re-derive the live card')
    ctes = ctes.replace(RECORDED_CARDS, 'alert_card').replace(RECORDED_DRIVERS, 'alert_drv')
    return f"""DECLARE card_region STRING DEFAULT @region;
DECLARE t TIMESTAMP DEFAULT @t;
DECLARE card_mode STRING DEFAULT @mode;
CREATE TEMP TABLE alert_card AS SELECT card_region AS region, 'live' AS case_id, *
  FROM `grid-nowcast.grid_ontology.driver_card`(card_region, t, card_mode);
CREATE TEMP TABLE alert_drv AS SELECT card_region AS region, 'live' AS case_id, *
  FROM `grid-nowcast.grid_ontology.likely_drivers`(card_region, t, card_mode);
{ctes.rstrip()},
summary AS (
{final}
)
SELECT TO_JSON_STRING(STRUCT(s AS summary,
  ARRAY(SELECT AS STRUCT rank, family, family_score, status, indicator, value_at_t, baseline_median, indicator_score
        FROM alert_drv WHERE rank IS NOT NULL ORDER BY rank, indicator_score DESC, indicator) AS drivers)) AS alert_json
FROM summary AS s;
"""
