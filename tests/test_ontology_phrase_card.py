"""The driver card in words (scripts/ontology/phrase_card.py): the composed paragraph and its validator.

Synthetic rows only, shaped like the recorded card and ranking; no company data.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phrase_card', ROOT / 'scripts/ontology/phrase_card.py')
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

CASE = 'pedc-u2-2026-09-21'
CARD = [
    {'section': 'fact', 'predicate': 'price_capped_median', 'value_num': 29919.2},
    {'section': 'fact', 'predicate': 'mention_tripped', 'value_text': 'UNIT X', 'match_confidence': 'confirmed',
     'known_by_utc': '2026-09-21 05:39:37'},
    {'section': 'fact', 'predicate': 'scheduled_outage', 'subject_label': 'RES_A'},
    {'section': 'unconfirmed', 'predicate': 'mention_derated', 'value_text': 'PLANT Y', 'match_confidence': 'unconfirmed'},
    {'section': 'withheld', 'n_withheld': 21},
]
DRIVERS = [
    {'rank': 1, 'family': 'S', 'status': 'scored', 'indicator': 'import_share', 'value_at_t': 0.105,
     'baseline_median': 0.068, 'indicator_score': 0.7768},
    {'rank': 2, 'family': 'F', 'status': 'scored', 'indicator': 'coal_driver', 'value_at_t': 140.5,
     'baseline_median': 141.0, 'indicator_score': 0.473},
    {'rank': None, 'family': 'O', 'status': 'no data', 'indicator': 'linked_derated_mw'},
]


class ComposeAndVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cards = Path(self.tmp.name)
        (cards / f'{CASE}-card-assumed.json').write_text(json.dumps(CARD))
        (cards / f'{CASE}-drivers-assumed.json').write_text(json.dumps(DRIVERS))
        self.old, pc.CARDS = pc.CARDS, cards
        self.addCleanup(setattr, pc, 'CARDS', self.old)

    def test_composed_text_carries_the_facts_and_hides_fuel(self):
        c = pc.compose(CASE)
        self.assertIn('29,919 PHP/MWh', c['text'])
        self.assertIn('evidence, not proof', c['text'])
        self.assertIn('fuel context available', c['text'])
        self.assertNotIn('140.5', c['text'])          # the fuel value stays internal
        self.assertIn('No data for outages', c['text'])
        self.assertIn('1 unconfirmed plant matches are listed, not counted', c['text'])
        self.assertNotIn('PLANT Y', c['text'])        # an unconfirmed match is never named as a fact
        self.assertIn('21 facts were withheld', c['text'])
        self.assertIsNone(pc.CAUSAL.search(c['text']))

    def test_the_composed_text_verifies_against_itself(self):
        c = pc.compose(CASE)
        self.assertEqual([], pc.verify(c, c['text']))

    def test_causal_wording_is_refused_and_likely_driver_allowed(self):
        c = pc.compose(CASE)
        self.assertTrue(any('causal' in p for p in pc.verify(c, c['text'] + ' This was caused by imports.')))
        self.assertTrue(any('causal' in p for p in pc.verify(c, c['text'] + ' Prices rose because of imports.')))
        self.assertEqual([], pc.verify(c, c['text'] + ' Supply is the likely driver.'))

    def test_a_dropped_or_invented_figure_or_name_fails(self):
        c = pc.compose(CASE)
        self.assertTrue(any('missing' in p for p in pc.verify(c, c['text'].replace('29,919', 'thirty thousand'))))
        self.assertTrue(any('not in the card' in p for p in pc.verify(c, c['text'] + ' Reserves were 99 MW.')))
        self.assertTrue(any('UNIT X' in p for p in pc.verify(c, c['text'].replace('UNIT X', 'a unit'))))

    def test_figures_are_compared_with_their_repeats(self):
        c = pc.compose(CASE)
        self.assertTrue(any('not in the card' in p for p in pc.verify(c, c['text'] + ' Again 29,919 PHP/MWh.')))
        repeated = dict(c, text=c['text'] + ' The price was 29,919 PHP/MWh.')
        self.assertTrue(any('missing' in p for p in pc.verify(repeated, c['text'])))

    def test_unconfirmed_must_stay_unconfirmed(self):
        c = pc.compose(CASE)
        self.assertTrue(any('unconfirmed' in p for p in pc.verify(c, c['text'].replace('unconfirmed', 'matched'))))

    def test_family_fact_lines_name_the_comparison_and_hide_fuel_values(self):
        lines = {i['family']: i['facts'] for i in pc.family_facts(CASE)}
        self.assertEqual(['S', 'F'], list(lines))
        self.assertIn('import share 0.105 against a median of 0.068, higher than 78% of the five-minute intervals '
                      'from 13:00 to 14:00 on the last 28 days', lines['S'])
        self.assertIn('about usual (47%, in the middle of its own monthly history)', lines['F'])
        self.assertNotIn('140.5', lines['F'])

    def test_an_explanation_with_a_new_figure_a_claim_or_three_sentences_is_dropped(self):
        lines = {i['family']: i['facts'] for i in pc.family_facts(CASE)}
        facts = lines['S']
        ok = 'The import share of 0.105 was higher than 78% of the same hour, well above its median.'
        self.assertEqual([], pc.verify_explanation(facts, ok))
        self.assertEqual([], pc.verify_explanation(facts, 'The import share was higher than usual, not lower.'))
        if 'price cap bound' in lines.get('Rules', ''):
            self.assertEqual([], pc.verify_explanation(lines['Rules'], 'The price cap bound was recorded at the interval.'))
        self.assertTrue(any('figure' in p for p in pc.verify_explanation(facts, ok.replace('78%', '90%'))))
        self.assertTrue(any('causal' in p for p in pc.verify_explanation(facts, ok + ' It drove the spike.')))
        self.assertTrue(any('claim' in p for p in pc.verify_explanation(facts, 'Imports pushed the price up.')))
        self.assertTrue(any('claim' in p for p in pc.verify_explanation(facts, 'Traders should buy.')))
        self.assertTrue(any('two sentences' in p for p in pc.verify_explanation(facts, 'One. Two. Three.')))
        # any effect on price, in any wording, is refused: the general note is fixed text in code, and every
        # model word must come from the fact line or the plain-word list
        for claim in ('Leaning on imports can push prices up.', 'Imports push prices up.',
                      'This will push prices up.', 'The import share affected the price.',
                      'Imports can raise prices.', 'Imports may raise prices.', 'Imports could push prices up.',
                      'Imports alter prices.', 'Imports weigh on prices.', 'Imports shape prices.',
                      'Imports alter the market rate.', 'Imports move the spot rate.', 'Imports set the market rate.',
                      'The import share tilted the clearing level.', 'The import share nudged what buyers paid.',
                      'Imports made power dearer.', 'The import share was higher, so energy got expensive.',
                      'Imports tend to matter.'):
            self.assertTrue(pc.verify_explanation(facts, claim), claim)
        # a flag name is allowed only whole and only in the family whose facts carry it
        self.assertTrue(pc.verify_explanation(facts, 'The price cap bound at the interval.'))
        self.assertTrue(pc.verify_explanation(lines.get('Rules', ''), 'The price was high.'))

    def test_the_effect_notes_are_general_and_use_the_owner_phrase_only(self):
        self.assertEqual(set(pc.FAMILY), set(pc.EFFECT_NOTE))
        for fam, note in pc.EFFECT_NOTE.items():
            self.assertTrue(note.startswith('In general, '), fam)
            self.assertRegex(note, r'can push prices (up|down)')
            self.assertIsNone(pc.CAUSAL.search(note), fam)
            self.assertIsNone(pc.CLAIM.search(note), fam)
            self.assertIsNone(pc.NUMBER.search(note), fam)

    def test_an_explanation_off_the_allowlist_is_not_requested(self):
        other = 'cvis-2026-06-25-0910'
        cards = pc.CARDS
        (cards / f'{other}-drivers-assumed.json').write_text(json.dumps(DRIVERS))
        runs, pc.RUNS = pc.RUNS, Path(self.tmp.name) / 'runs'
        self.addCleanup(setattr, pc, 'RUNS', runs)
        self.assertEqual(0, pc.explain(other, Path('/nonexistent/config.json')))
        out = json.loads((pc.RUNS / other / 'explain.json').read_text())
        self.assertEqual({}, out['explanations'])

    def test_a_case_off_the_allowlist_keeps_its_template_without_a_call(self):
        self.assertNotIn('cvis-2026-06-25-0910', pc.TRANSMITTABLE)
        from src.adapters.gemini.transport import REAL_CASE_ALLOWLIST
        self.assertLessEqual(pc.TRANSMITTABLE, set(REAL_CASE_ALLOWLIST))


if __name__ == '__main__':
    unittest.main()
