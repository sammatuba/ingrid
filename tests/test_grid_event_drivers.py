"""O5 (ontology): the likely-drivers card on the event page.

The card's file is baked by the real ``scripts/ontology/bake_panel.py`` from synthetic exports (no
company row is committed), written beside the committed event fixture in a temporary directory, and
the real page is rendered by ``tests/fixtures/grid/event/render.mjs``. Without the file the card
stays off and the page reads as before."""
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_FIXTURE = ROOT / 'tests' / 'fixtures' / 'grid' / 'event'
NODE = shutil.which('node')
spec = importlib.util.spec_from_file_location('bake_panel', ROOT / 'scripts/ontology/bake_panel.py')
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)

CASE = 'pedc-u2-2026-09-21'
HEADING = 'Likely drivers (ranked by how unusual each was against the last 28 days at this hour; evidence, not proof)'


def card(mode):
    rows = [{'section': 'fact', 'mode': mode, 'cutoff_utc': '2026-09-21 05:45:00', 'family': 'D', 'public': 'true',
             'predicate': 'demand_mw', 'value_num': 1000.0, 'unit': 'MW', 'availability_at_cutoff': 'assumed',
             'availability_assumption': 'A-RT', 'assumed_known_by_utc': '2026-09-21 05:45:00'},
            {'section': 'fact', 'mode': mode, 'cutoff_utc': '2026-09-21 05:45:00', 'family': 'S', 'public': 'true',
             'predicate': 'scheduled_outage_mw', 'value_num': 21.0, 'unit': 'MW', 'availability_at_cutoff': 'assumed',
             'availability_assumption': 'A-RUN', 'assumed_known_by_utc': '2026-09-21 05:00:00'},
            {'section': 'fact', 'mode': mode, 'family': 'F', 'public': 'false', 'predicate': 'fuel_price',
             'value_num': 140.5, 'fuel_role': 'coal_driver', 'availability_at_cutoff': 'assumed',
             'availability_assumption': 'A-FUEL', 'assumed_known_by_utc': '2026-09-01 00:00:00',
             'known_by_utc': '2026-10-16 23:43:00'},
            {'section': 'withheld', 'mode': mode, 'family': 'O', 'withheld_reason': 'known only after the cutoff', 'n_withheld': 2},
            {'section': 'withheld', 'mode': mode, 'family': 'O', 'withheld_reason': 'a later revision', 'n_withheld': 3}]
    if mode == 'strict':
        rows[0].update(availability_at_cutoff='evidenced', availability_assumption=None,
                       assumed_known_by_utc=None, known_by_utc='2026-09-21 05:41:00')
        del rows[1]  # strict keeps only evidence-known facts
    if mode == 'hindsight':
        rows.append({'section': 'unconfirmed', 'mode': mode, 'predicate': 'mention_derated', 'value_text': 'SYN PLANT',
                     'match_reason': 'uncertain: synthetic test', 'candidate_id': 'plant:SYNX'})
    return rows


def drivers():
    return [{'heading': HEADING, 'rank': 1, 'family': 'S', 'status': 'scored', 'indicator': 'import_share',
             'family_score': 0.8, 'indicator_score': 0.8, 'value_at_t': 0.2, 'baseline_median': 0.1, 'unit': 'fraction'},
            {'heading': HEADING, 'rank': 2, 'family': 'F', 'status': 'scored', 'indicator': 'coal_driver',
             'family_score': 0.5, 'indicator_score': 0.5, 'value_at_t': 140.5, 'baseline_median': 141.0, 'unit': 'USD/tonne'},
            {'heading': HEADING, 'rank': None, 'family': 'P', 'status': 'context', 'indicator': 'price_capped_median',
             'indicator_score': 0.7, 'value_at_t': 9000.0, 'baseline_median': 5000.0, 'unit': 'PHP/MWh'},
            {'heading': HEADING, 'rank': None, 'family': 'O', 'status': 'no data', 'indicator': None},
            {'heading': HEADING, 'rank': 3, 'family': 'Rules', 'status': 'scored', 'indicator': 'congested_elements',
             'family_score': 0.12, 'indicator_score': 0.12, 'value_at_t': 0.0, 'baseline_median': 1.0, 'unit': 'elements'},
            {'heading': HEADING, 'rank': None, 'family': 'Rules', 'status': 'present', 'indicator': 'cap_bound',
             'value_text': 'true', 'unit': 'flag'},
            {'heading': HEADING, 'rank': None, 'family': 'Rules', 'status': 'flag count',
             'indicator': 'unlinked_congested_elements', 'value_at_t': 2.0, 'unit': 'elements'}]


def report(fixture):
    run = subprocess.run([NODE, str(EVENT_FIXTURE / 'render.mjs'), '--root', str(ROOT), '--legacy-cards', '--fixture', str(fixture)],
                         capture_output=True, text=True, cwd=ROOT, timeout=300)
    try:
        return json.loads(run.stdout)
    except ValueError:
        raise AssertionError('render.mjs printed no report: %s %s' % (run.stdout[-400:], run.stderr[-800:]))


def text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def scratch(prefix):
    try:
        return tempfile.TemporaryDirectory(prefix=prefix)
    except OSError:  # a sandbox may mount no writable system temp dir
        fallback = ROOT / '.local' / 'test-scratch'
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(prefix=prefix, dir=fallback)


@unittest.skipUnless(NODE, 'the page harness runs on node; this interpreter has none')
class DriversCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = scratch('o5-drivers-')
        cls.addClassCleanup(cls.temp.cleanup)
        where = Path(cls.temp.name)
        cards = where / 'cards'
        cards.mkdir()
        for mode in bp.MODES:
            (cards / f'{CASE}-card-{mode}.json').write_text(json.dumps(card(mode)))
        (cards / f'{CASE}-drivers-assumed.json').write_text(json.dumps(drivers()))
        (cards / 'recorded_summary.json').write_text(json.dumps([{
            'case_id': CASE, 'mode': 'assumed', 'severity': 'High', 'severity_reason': 'synthetic',
            'confidence': 'Low', 'confidence_reason': 'synthetic',
            'financial_impact': 'Not available: needs portfolio data (positions, contracts, load nodes)',
            'relationship_trail': 'SYN message → SYN plant → Visayas', 'what_to_check': ['the synthetic return time']}]))
        baked = bp.bake_case(CASE, cards)
        # The O4 result is local to the owner's machine, so the test supplies a labelled one.
        baked['paragraph'] = {'text': 'Synthetic paragraph about the drivers.', 'kind': 'phrased by Gemini, verified',
                              'model': 'gemini-synthetic'}
        baked['explanations'] = {'mode': 'assumed', 'kind': 'explained by Gemini, checked against the facts',
                                 'model': 'gemini-synthetic',
                                 'items': {'S': 'Synthetic: the import share was higher than usual.'},
                                 'notes': {'S': bp.phrase_module().EFFECT_NOTE['S']},
                                 'notes_kind': bp.phrase_module().EFFECT_NOTE_KIND}
        assert bp.validate(baked) == [], bp.validate(baked)
        cls.baked = baked
        fixture = where / 'fixture'
        fixture.mkdir()
        for name in ('view.json', 'flow.json', 'outlook.json'):
            shutil.copy(EVENT_FIXTURE / name, fixture / name)
        (fixture / 'ontology.json').write_text(json.dumps(baked))
        cls.with_file = report(fixture)
        cls.without_file = report(EVENT_FIXTURE)
        # Malformed bakes: an object whose lists are not lists, and one whose modes are not an object.
        cls.malformed = []
        modes = baked['modes']
        bad_bakes = (
            {**baked, 'modes': {**modes, 'assumed': {**modes['assumed'], 'facts': 3}}},
            {**baked, 'modes': {**modes, 'hindsight': {**modes['hindsight'], 'unconfirmed': {}}}},
            {**baked, 'modes': {**modes, 'strict': 'x'}},
            {**baked, 'modes': ['assumed']},
            {**baked, 'modes': {}},
            {**baked, 'drivers': {'assumed': 'not a list'}},
            {**baked, 'drivers': {'assumed': [1, 2]}},
            {**baked, 'summary': {**baked['summary'], 'what_to_check': 7}},
            {**baked, 'paragraph': 'text'},
            {**baked, 'paragraph': None},   # well formed: the card renders without a paragraph
        )
        for n, bad in enumerate(bad_bakes):
            where_bad = where / f'bad{n}'
            where_bad.mkdir()
            for name in ('view.json', 'flow.json', 'outlook.json'):
                shutil.copy(EVENT_FIXTURE / name, where_bad / name)
            (where_bad / 'ontology.json').write_text(json.dumps(bad))
            cls.malformed.append(report(where_bad))

    def test_the_card_is_drawn_from_the_bake_with_the_assumed_mode_first(self):
        r = self.with_file
        self.assertTrue(r['ok'], r)
        self.assertEqual([], r['errors'])
        d = r['drivers']
        self.assertFalse(d['hidden'])
        self.assertIn('evidence, not proof', d['heading'])
        self.assertEqual(['assumed', 'hindsight', 'strict'], [m['mode'] for m in d['modes']])
        assumed = text(d['modes'][0]['html'])
        self.assertLess(assumed.index('Supply and interconnection'), assumed.index('Fuel cost baseline'))
        self.assertIn('Supply and interconnection — 80% higher than 80% of the five-minute intervals from 13:00 to 14:00 '
                      'on the last 28 days', assumed)
        self.assertIn('import share: 20.0% against a 28-day median of 10.0% higher than 80% of the five-minute '
                      'intervals from 13:00 to 14:00 on the last 28 days', assumed)
        self.assertIn('Rules and grid constraints — 12% lower than usual: only 12% of the five-minute intervals '
                      'from 13:00 to 14:00 on the last 28 days were lower', assumed)
        self.assertIn('Fuel cost baseline — 50% about usual (50%, in the middle of its own monthly history)', assumed)
        self.assertIn('Rules flags at the interval (listed, not scored): price cap bound', assumed)
        self.assertIn('2 congested elements at stations with no area code (any region): not linked to a region '
                      'and not counted', assumed)
        self.assertNotIn('percentile', assumed)
        self.assertIn('fuel cost baseline: fuel context available (monthly series)', assumed)
        self.assertIn('Context, not ranked: capped median price 9,000 PHP/MWh', assumed)
        self.assertIn('5 facts withheld as not yet known at the cutoff (Outages 5)', assumed)
        self.assertIn('GET /grid-data/ontology/' + CASE + '.json', r['calls'])

    def test_a_checked_explanation_shows_under_its_family_with_its_label_in_its_mode_only(self):
        assumed = text(self.with_file['drivers']['modes'][0]['html'])
        self.assertIn('Synthetic: the import share was higher than usual. explained by Gemini, checked against the facts', assumed)
        self.assertIn('limited links can push prices up. general note written by the team, not a finding about this interval', assumed)
        self.assertLess(assumed.index('Synthetic: the import share'), assumed.index('Fuel cost baseline'))
        for other in self.with_file['drivers']['modes'][1:]:
            self.assertNotIn('Synthetic: the import share', text(other['html']))

    def test_the_how_to_read_box_explains_percent_rank_rules_withheld_and_tabs(self):
        # The help fold went with the old card; the legacy-cards fixture keeps it for its renderer.
        page = text((ROOT / 'tests' / 'fixtures' / 'grid' / 'event' / 'legacy-cards.html').read_text(encoding='utf-8'))
        for words in ('How to read this', 'same clock hour on the last 28 days', 'about 50% is normal',
                      'Context, not ranked.', 'Rules flags.', 'Withheld facts.', 'evidence, not proof',
                      'As known at the time: each market run is assumed available at the end of its interval',
                      'Strict: only facts with evidence', 'Hindsight: everything, including facts recorded later'):
            self.assertIn(words, page)

    def test_every_fact_shows_when_it_was_known_and_its_assumption_id(self):
        assumed = text(self.with_file['drivers']['modes'][0]['html'])
        self.assertIn('2 facts at this cutoff, with when each was known', assumed)
        self.assertIn('demand: 1,000 MW assumed known by 2026-09-21 05:45:00 UTC (A-RT)', assumed)
        self.assertIn('capacity scheduled out: 21 MW assumed known by 2026-09-21 05:00:00 UTC (A-RUN)', assumed)
        # an assumed fact whose evidence was recorded later is labelled by its assumption, not by that later time
        self.assertIn('fuel row (value not shown) assumed known by 2026-09-01 00:00:00 UTC (A-FUEL); '
                      'evidence recorded 2026-10-16 23:43:00 UTC', assumed)
        self.assertNotIn('known by 2026-10-16 23:43:00 UTC (evidence)', assumed)
        strict = text(self.with_file['drivers']['modes'][2]['html'])
        self.assertIn('known by 2026-09-21 05:41:00 UTC (evidence)', strict)
        self.assertNotIn('(A-RT)', strict)

    def test_no_fuel_value_or_internal_field_reaches_the_page(self):
        page = json.dumps(self.with_file['drivers'])
        for word in ('140.5', 'USD/tonne', 'coal_driver', 'fuel_price', 'fuel_group', 'technology', 'SYNX'):
            self.assertNotIn(word, page)
            self.assertNotIn(word, json.dumps(self.baked))

    def test_unconfirmed_matches_are_listed_and_not_counted(self):
        hindsight = text(self.with_file['drivers']['modes'][1]['html'])
        self.assertIn('No ranking was recorded for this mode.', hindsight)
        self.assertIn('Unconfirmed matches (not counted) SYN PLANT: uncertain: synthetic test', hindsight)

    def test_the_summary_carries_the_five_fields_and_no_peso_figure(self):
        summary = text(self.with_file['drivers']['summary'])
        for field in ('Severity High', 'Financial impact Not available: needs portfolio data',
                      'Confidence Low', 'Relationship trail SYN message → SYN plant → Visayas',
                      'What to check the synthetic return time'):
            self.assertIn(field, summary)
        paragraph = text(self.with_file['drivers']['paragraph'])
        self.assertEqual('Synthetic paragraph about the drivers. phrased by Gemini, verified · gemini-synthetic', paragraph)
        self.assertIn('No trading advice', self.with_file['drivers']['source'])

    def test_a_malformed_bake_leaves_the_card_off_and_the_page_whole(self):
        base = self.without_file
        for n, r in enumerate(self.malformed[:-1]):
            self.assertTrue(r['ok'], r)
            self.assertTrue(r['drivers']['hidden'], (n, r['drivers']))
            self.assertEqual([], r['drivers']['modes'], n)
            for key in ('title', 'advisory', 'afterLoad', 'rules', 'limits', 'priceOutlook', 'decision_form',
                        'decision', 'history', 'assumption'):
                self.assertEqual(base[key], r[key], (n, key))
        self.assertFalse(self.malformed[-1]['drivers']['hidden'])
        self.assertEqual('', self.malformed[-1]['drivers']['paragraph'])

    def test_without_the_file_the_card_stays_off_and_the_page_is_unchanged(self):
        a, b = self.without_file, self.with_file
        self.assertTrue(a['ok'], a)
        self.assertTrue(a['drivers']['hidden'])
        self.assertEqual([], a['drivers']['modes'])
        for key in ('title', 'advisory', 'afterLoad', 'rules', 'limits', 'priceOutlook', 'decision_form',
                    'decision', 'history', 'assumption'):
            self.assertEqual(a[key], b[key], key)

    def test_the_desk_line_and_the_folds_do_not_depend_on_the_drivers_card(self):
        """DESK-7: the desk line, the record disclosures, the figure tiles and the save-wait
        text are drawn from the baked view model, so the likely-drivers file's presence
        changes none of them. This event's fixture view carries no judgment, so the AI card
        says exactly that in both runs."""
        for key in ('desk', 'folds', 'tiles', 'saving'):
            self.assertEqual(self.without_file[key], self.with_file[key], key)
        self.assertEqual('No judgment is recorded for this event.',
                         self.without_file['desk']['ai']['run'])
        self.assertEqual('No analyst decision is recorded on the real case. What you record '
                         'goes to your own copy.', self.without_file['afterLoad']['person'])
        self.assertEqual({'outlook': 'Show the records', 'impact': 'Show the records',
                          'judgment': 'Show the records'}, self.without_file['folds'])


if __name__ == '__main__':
    unittest.main()
