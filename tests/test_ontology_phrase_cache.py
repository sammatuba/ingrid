"""The verified-phrasing cache (scripts/ontology/phrase_cache.py). Synthetic text only; no network."""
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phrase_cache', ROOT / 'scripts/ontology/phrase_cache.py')
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

TEXT = 'At 10:00 on 1 January 2026, the Region X capped median price was 1,000 PHP/MWh.'
CONFIG = {'api': 'synthetic', 'max_output_tokens': 256, 'candidate_count': 1}


class KeyTests(unittest.TestCase):
    def test_same_inputs_same_key(self):
        a = pc.cache_key(TEXT, 1, 'model-a', CONFIG)
        self.assertEqual(a, pc.cache_key(TEXT, 1, 'model-a', dict(reversed(list(CONFIG.items())))))
        self.assertRegex(a, r'^[0-9a-f]{64}$')

    def test_any_change_gives_a_new_key(self):
        base = pc.cache_key(TEXT, 1, 'model-a', CONFIG)
        changed = {
            pc.cache_key(TEXT.replace('1,000', '1,001'), 1, 'model-a', CONFIG),  # a changed fact
            pc.cache_key(TEXT, 2, 'model-a', CONFIG),
            pc.cache_key(TEXT, 1, 'model-b', CONFIG),
            pc.cache_key(TEXT, 1, 'model-a', dict(CONFIG, max_output_tokens=512)),
        }
        self.assertEqual(4, len(changed))
        self.assertNotIn(base, changed)

    def test_secret_looking_config_is_refused(self):
        for k in ('access_token', 'credential_env', 'authorization_ref', 'api_key'):
            with self.subTest(k=k), self.assertRaises(ValueError):
                pc.cache_key(TEXT, 1, 'model-a', dict(CONFIG, **{k: 'x'}))

    def test_bad_inputs(self):
        for args in (('', 1, 'm', {}), (TEXT, 1, '', {}), (TEXT, 1, 'm', [])):
            with self.subTest(args=args), self.assertRaises(ValueError):
                pc.cache_key(*args)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = pc.PhraseCache(Path(self.tmp.name) / 'cache')
        self.key = pc.cache_key(TEXT, 1, 'model-a', CONFIG)

    def tearDown(self):
        self.tmp.cleanup()

    def test_miss_then_hit(self):
        self.assertIsNone(self.cache.get(self.key))
        self.assertTrue(self.cache.put(self.key, 'Phrased.', [], case='synthetic-case'))
        got = self.cache.get(self.key)
        self.assertEqual('Phrased.', got['text'])
        self.assertEqual('synthetic-case', got['case'])
        mode = stat.S_IMODE(os.stat(self.cache.directory / f'{self.key}.json').st_mode)
        self.assertEqual(0o600, mode)

    def test_unverified_is_not_stored(self):
        self.assertFalse(self.cache.put(self.key, 'Phrased.', ['figure 7 not in the card']))
        self.assertFalse(self.cache.put(self.key, '  ', []))
        self.assertIsNone(self.cache.get(self.key))

    def test_changed_fact_misses(self):
        self.cache.put(self.key, 'Phrased.', [])
        other = pc.cache_key(TEXT.replace('10:00', '10:05'), 1, 'model-a', CONFIG)
        self.assertIsNone(self.cache.get(other))

    def test_tampered_or_foreign_record_is_none(self):
        self.cache.put(self.key, 'Phrased.', [])
        path = self.cache.directory / f'{self.key}.json'
        path.write_text('{"key": "%s", "text": "x", "problems": ["bad"]}' % self.key)
        self.assertIsNone(self.cache.get(self.key))
        path.write_text('not json')
        self.assertIsNone(self.cache.get(self.key))

    def test_key_shape_is_checked(self):
        for k in ('../x', 'ABC', '0' * 63):
            with self.subTest(k=k), self.assertRaises(ValueError):
                self.cache.get(k)


if __name__ == '__main__':
    unittest.main()
