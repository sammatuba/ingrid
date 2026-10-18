"""ericka-desk: the full ontology driver card saved per replay alert (src/alerts/ontology.py) and shown on
the alert page (src/grid/spike.js ontologyView).

Every row here is SYNTHETIC (made up for the test). Offline: no BigQuery, no model.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.alerts import explain, ontology  # noqa: E402

NODE = shutil.which('node')
ALERT = {'key': 'ab' * 12, 'region': 'CMIN', 'region_label': 'Mindanao', 'direction': 'spike',
         'interval_manila': '2026-10-05T13:35'}


def rows():
    """Decoded alert_json as the query returns it (synthetic)."""
    cards, drivers, summary = [], [], []
    for mode in ontology.MODES:
        cards += [
            {'mode': mode, 'section': 'fact', 'family': 'D', 'subject_label': 'Mindanao', 'predicate': 'demand_mw',
             'value_num': 2489.0, 'unit': 'MW', 'known_by_utc': '2026-10-05 05:35:00', 'public': True,
             'availability_at_cutoff': 'evidenced', 'cutoff_utc': '2026-10-05T05:40:00Z'},
            {'mode': mode, 'section': 'fact', 'family': 'F', 'subject_label': 'x', 'predicate': 'fuel_group',
             'value_num': 99.0, 'public': True, 'availability_at_cutoff': 'evidenced'},
            {'mode': mode, 'section': 'fact', 'family': 'O', 'subject_label': 'secret', 'predicate': 'p',
             'public': False, 'availability_at_cutoff': 'evidenced'},
            {'mode': mode, 'section': 'withheld', 'family': 'O', 'withheld_reason': 'known only after the cutoff', 'n_withheld': 2},
            {'mode': mode, 'section': 'unconfirmed', 'value_text': 'Some Geothermal Unit 2', 'predicate': 'outage',
             'match_reason': 'two plants share the name'},
        ]
        drivers += [
            {'mode': mode, 'rank': 1, 'family': 'D', 'status': 'scored', 'indicator': 'demand_mw', 'family_score': 0.9,
             'indicator_score': 0.9, 'value_at_t': 2489.0, 'baseline_median': 2445.0, 'unit': 'MW', 'baseline_n': 324,
             'heading': 'Likely drivers (evidence, not proof)'},
            {'mode': mode, 'rank': 2, 'family': 'F', 'status': 'scored', 'indicator': 'coal_driver', 'family_score': 0.6,
             'indicator_score': 0.6, 'value_at_t': 123.0, 'baseline_median': 100.0, 'unit': 'USD/t', 'baseline_n': 12},
            {'mode': mode, 'rank': None, 'family': 'P', 'status': 'context', 'indicator': 'price_capped_median',
             'value_at_t': 32000, 'baseline_median': 13600, 'unit': 'PHP/MWh'},
            {'mode': mode, 'rank': None, 'family': 'Rules', 'status': 'present', 'indicator': 'cap_bound', 'unit': 'flag'},
            {'mode': mode, 'rank': None, 'family': 'Rules', 'status': 'absent', 'indicator': 'admin_priced', 'unit': 'flag'},
        ]
        summary.append({'mode': mode, 'severity': 'High', 'confidence': 'Medium', 'financial_impact': 'Not available',
                        'relationship_trail': 'demand 2,489 MW → Mindanao → price', 'what_to_check': ['check demand']})
    return {'cards': cards, 'drivers': drivers, 'summary': summary}


class Query(unittest.TestCase):
    def test_read_only_parameterised_script_with_temp_tables_only(self):
        sql, params = ontology.card_query('CMIN', '2026-10-05 05:35:00')
        self.assertEqual({'region', 't'}, {p['name'] for p in params})
        self.assertEqual('CMIN', next(p for p in params if p['name'] == 'region')['parameterValue']['value'])
        self.assertNotIn('CMIN', sql)
        self.assertIsNone(re.search(r'CREATE\s+(OR\s+REPLACE\s+)?(?!TEMP)', sql, re.I))
        self.assertIsNone(re.search(r'^\s*(DELETE|MERGE|UPDATE|DROP|TRUNCATE)\s', sql, re.I | re.M))
        for mode in ontology.MODES:
            self.assertIn(f"'{mode}'", sql)

    def test_manila_interval_is_turned_into_utc(self):
        self.assertEqual('2026-10-05 05:35:00', ontology.t_utc_of('2026-10-05T13:35'))
        with self.assertRaises(ValueError):
            ontology.card_query('XX', '2026-10-05 05:35:00')


class Shape(unittest.TestCase):
    def test_fuel_values_and_private_rows_never_reach_the_card(self):
        card = ontology.shape(rows(), ALERT, made_at_utc='2026-10-18 00:00:00')
        self.assertEqual([], ontology.problems(card))
        block = card['modes']['assumed']
        self.assertEqual(['D'], [f['family'] for f in block['facts']])
        self.assertEqual(1, block['fuel_context'])
        self.assertEqual('2026-10-05 05:40:00', block['cutoff_utc'])
        f = next(r for r in card['drivers']['assumed'] if r['family'] == 'F')
        self.assertEqual(('fuel cost baseline', None, None, None), (f['indicator'], f['value_at_t'], f['baseline_median'], f['unit']))
        text = json.dumps(card)
        for word in ('coal_driver', 'fuel_group', 'secret', 'grid_ontology'):
            self.assertNotIn(word, text)
        self.assertEqual(card['summaries']['assumed'], card['summary'])

    def test_problems_catch_fuel_values_internal_names_and_figures(self):
        card = ontology.shape(rows(), ALERT)
        bad = json.loads(json.dumps(card))
        bad['drivers']['assumed'][1]['value_at_t'] = 5
        bad['summary']['financial_impact'] = 'PHP 1,000,000'
        bad['modes']['assumed']['facts'][0]['subject_label'] = 'grid_ontology.facts'
        got = ' | '.join(ontology.problems(bad))
        for part in ('fuel value', 'financial impact', 'internal name'):
            self.assertIn(part, got)


class Load(unittest.TestCase):
    def test_load_card_returns_the_card_only_for_its_own_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ontology.load_card(tmp, ALERT['key'], ALERT))
            card = ontology.shape(rows(), ALERT)
            path = ontology.card_path(tmp, ALERT['key'])
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(card))
            self.assertEqual(card, ontology.load_card(tmp, ALERT['key'], ALERT))
            self.assertEqual(card, ontology.load_card(tmp, ALERT['key']))
            self.assertIsNone(ontology.load_card(tmp, ALERT['key'], dict(ALERT, region='CVIS')))
            self.assertIsNone(ontology.load_card(tmp, ALERT['key'], dict(ALERT, interval_manila='2026-10-05T13:40')))
            path.write_text('{not json')
            self.assertIsNone(ontology.load_card(tmp, ALERT['key'], ALERT))
            for bad in ('../' + 'a' * 21, 'x'):
                with self.assertRaises(ValueError):
                    ontology.card_path(tmp, bad)

    def test_the_explain_answer_carries_the_card_or_null(self):
        a = dict(ALERT, price_php_mwh=32000, usual_php_mwh=13600)
        card = ontology.shape(rows(), ALERT)
        self.assertIsNone(explain.answer(a, None)['ontology'])
        self.assertEqual(card, explain.answer(a, None, None, card)['ontology'])


@unittest.skipUnless(NODE, 'node not installed')
class Page(unittest.TestCase):
    def view(self, card, mode):
        js = ("const api=require(process.argv[1]);const c=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "process.stdout.write(JSON.stringify(api.ontologyView(c, process.argv[2])));")
        r = subprocess.run([NODE, '-e', js, str(ROOT / 'src' / 'grid' / 'spike.js'), mode], input=json.dumps(card),
                           capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_the_page_ranks_from_the_card_and_says_no_data_never_a_value(self):
        card = ontology.shape(rows(), ALERT)
        card['drivers']['strict'] = [r for r in card['drivers']['strict'] if r['family'] == 'P']
        v = self.view(card, 'assumed')
        self.assertEqual(['assumed', 'strict', 'hindsight'], [m['key'] for m in v['modes']])
        self.assertEqual(['D', 'F'], [f['family'] for f in v['families'][:2]])
        self.assertEqual((90, 'Unusual'), (v['families'][0]['pct'], v['families'][0]['state']))
        self.assertIn('2,489 MW', v['families'][0]['text'])
        self.assertIn('Values not shown', v['families'][1]['text'])
        rules = next(f for f in v['families'] if f['family'] == 'Rules')
        self.assertIsNone(rules['pct'])
        self.assertIn('offer cap bound set', ' '.join(rules['signals']))
        self.assertIn('context, never a driver', v['context'])
        self.assertEqual(['Some […] Unit 2: two plants share the name'], v['unconfirmed'])
        strict = self.view(card, 'strict')
        self.assertTrue(all(f['pct'] is None and f['state'] == 'No data' for f in strict['families']))
        text = json.dumps([v, strict])
        self.assertNotIn('USD', text)
        self.assertIsNone(re.search(r'grid_ontology|\.sql\b|\.py\b|A-FUEL', text))
        self.assertIn('Evidence', json.dumps(card['basis']))


if __name__ == '__main__':
    unittest.main()
