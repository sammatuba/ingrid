"""Amendment lineage: the clause in force at a cutoff, from supplied records."""
import hashlib
import unittest
from pathlib import Path

from src.regulatory.lineage import (Amendment, AmendmentChange, ANCESTOR_NOT_IN_FORCE,
                                    AVAILABILITY_IMPRECISE, EFFECTIVITY_IMPRECISE,
                                    EFFECTIVITY_UNKNOWN, NOT_YET_EFFECTIVE, RuleRegister)
from src.regulatory.structure import DateMetadata, Locator, Source, StructureError

FIXTURES = Path(__file__).parent / 'fixtures' / 'regulatory'

BASE = FIXTURES / 'synthetic_rule_base.txt'
AMENDMENT = FIXTURES / 'synthetic_rule_amendment.txt'
LINEAGE_FIXTURES = ('synthetic_rule_base.txt', 'synthetic_rule_amendment.txt')

# The replacement a change supplies is by default the version at the head of the
# clause's chain at the time the record was built — the id a reviewer read off
# the register.  No test relies on the register filling it in.
_HEAD = object()


def source(raw, source_id='synthetic-document', **kwargs):
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    return Source(source_id, 'v1', hashlib.sha256(raw).hexdigest(), raw, **kwargs)


def day(value):
    return DateMetadata(value, 'day', None)


def unknown(reason='no record attests when this version became available'):
    return DateMetadata(None, None, reason)


def locator_for(src, text):
    start = src.text.index(text)
    return Locator(src.source_id, src.source_revision, src.digest, start, start + len(text))


class LineageFixtureTests(unittest.TestCase):
    def test_fixtures_do_not_claim_authority(self):
        for name in LINEAGE_FIXTURES:
            with self.subTest(name=name):
                text = (FIXTURES / name).read_text(encoding='utf-8')
                self.assertTrue(text.startswith('SYNTHETIC'))
                self.assertIn('no legal authority', text)


class LineageTestCase(unittest.TestCase):
    def setUp(self):
        self.base = source(BASE.read_bytes(), 'synthetic-rule-base')
        self.amending = source(AMENDMENT.read_bytes(), 'synthetic-amendment-1')
        self.register = RuleRegister('wesm_rules')
        self.baseline = self.register.add_baseline(
            self.base, day('2026-01-01'), effective=day('2026-01-01'))

    def head(self, label='1.1.1.1'):
        chain = self.register.versions(label)
        return chain[-1].version_id if chain else None

    def amendment(self, ref='amendment-1', *, label='1.1.1.1',
                  text='The fictional notice period is ten fictional days.',
                  effective=None, availability=None, adds_clause=False,
                  source=None, replaces=_HEAD):
        src = source if source is not None else self.amending
        if replaces is _HEAD:
            replaces = None if adds_clause else self.head(label)
        return Amendment(
            src, ref, effective if effective is not None else day('2026-05-15'),
            availability if availability is not None else day('2026-06-01'),
            (AmendmentChange(label, locator_for(src, text), text, replaces, adds_clause),))


class BaselineTests(LineageTestCase):
    def test_baseline_registers_one_version_per_clause(self):
        self.assertEqual(self.register.labels(), ('1.1.1.1', '1.1.1.2', '1.2.1.1'))
        self.assertEqual(len(self.baseline), 3)
        clauses = {version.clause_label: version for version in self.baseline}
        self.assertEqual(clauses['1.1.1.1'].text,
                         '1.1.1.1 The fictional notice period is five fictional days.\n')
        self.assertEqual(clauses['1.2.1.1'].text,
                         '1.2.1.1 The fictional fee is one hundred fictional pesos.\n')
        for version in self.baseline:
            self.assertIsNone(version.replaces)
            self.assertIsNone(version.amendment_ref)
            self.assertEqual(version.first_availability, day('2026-01-01'))
            self.assertEqual(version.effective, day('2026-01-01'))
            self.assertEqual(version.locator.source_id, 'synthetic-rule-base')
            self.assertTrue(version.version_id.startswith('rv-'))
        self.assertEqual([version.version_id for version in self.baseline],
                         [version.version_id for version in
                          RuleRegister('wesm_rules').add_baseline(
                              self.base, day('2026-01-01'), effective=day('2026-01-01'))])

    def test_baseline_dates_are_supplied_or_unknown(self):
        register = RuleRegister('wesm_rules')
        versions = register.add_baseline(self.base, unknown())
        self.assertIsNone(versions[0].first_availability.value)
        self.assertIsNone(versions[0].effective.value)
        self.assertEqual(versions[0].effective.unknown_reason,
                         'no effectivity metadata was supplied with the source')
        supplied = DateMetadata('2026-01', 'month', None)
        versions = RuleRegister('wesm_rules').add_baseline(self.base, day('2026-01-01'),
                                                           effective=supplied)
        self.assertIs(versions[0].effective, supplied)

    def test_a_baseline_without_effectivity_is_never_assumed_in_force(self):
        register = RuleRegister('wesm_rules')
        register.add_baseline(self.base, day('2026-01-01'))
        result = register.in_force('1.1.1.1', day('2026-03-01'))
        self.assertIsNone(result.version)
        self.assertEqual(result.chain, ())
        self.assertEqual([item.reason for item in result.excluded], [EFFECTIVITY_UNKNOWN])

    def test_baseline_refuses_missing_inputs(self):
        with self.assertRaises(StructureError):
            self.register.add_baseline('not a source', day('2026-01-01'))
        with self.assertRaises(StructureError):
            RuleRegister('wesm_rules').add_baseline(self.base, '2026-01-01')
        with self.assertRaises(StructureError):
            RuleRegister('wesm_rules').add_baseline(self.base, day('2026-01-01'),
                                                    kinds=('resolved',))
        with self.assertRaises(StructureError):
            RuleRegister('wesm_rules').add_baseline(self.base, day('2026-01-01'),
                                                    kinds='clause')

    def test_a_second_baseline_cannot_branch_one_lineage(self):
        other = source(BASE.read_bytes(), 'synthetic-rule-base-again')
        with self.assertRaises(StructureError):
            self.register.add_baseline(other, day('2026-02-01'), effective=day('2026-02-01'))
        self.assertEqual(self.register.versions('1.1.1.1'), (self.baseline[0],))

    def test_baseline_refuses_two_clauses_with_one_label(self):
        text = ('1.1 SCOPE\n'
                '1.1.1.1 The first fictional provision.\n'
                '1.1.1.1 The second fictional provision with the same label.\n')
        with self.assertRaises(StructureError):
            RuleRegister('wesm_rules').add_baseline(source(text, 'twice'),
                                                    day('2026-01-01'))

    def test_contents_lines_are_not_clauses(self):
        text = ('1.1 SCOPE\n'
                '1.1.1.1 The fictional provision. ................ 12\n'
                '1.1.1.1 The fictional provision.\n')
        register = RuleRegister('wesm_rules')
        versions = register.add_baseline(source(text, 'contents'), day('2026-01-01'))
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].text, '1.1.1.1 The fictional provision.\n')
        with self.assertRaises(StructureError):
            RuleRegister('wesm_rules').add_baseline(source(text, 'contents'),
                                                    day('2026-01-01'), exclude_toc=False)


class AmendmentTests(LineageTestCase):
    def test_one_amendment_changes_the_clause_at_two_cutoffs(self):
        amended = self.register.apply(self.amendment())
        self.assertEqual(len(amended), 1)
        self.assertEqual(amended[0].clause_label, '1.1.1.1')
        self.assertEqual(amended[0].replaces, self.baseline[0].version_id)
        self.assertEqual(amended[0].amendment_ref, 'amendment-1')
        self.assertEqual(amended[0].text,
                         'The fictional notice period is ten fictional days.')
        self.assertEqual(amended[0].effective, day('2026-05-15'))
        self.assertEqual(amended[0].first_availability, day('2026-06-01'))

        before = self.register.in_force('1.1.1.1', day('2026-03-01'))
        self.assertIs(before.version, self.baseline[0])
        self.assertEqual(before.chain, (self.baseline[0],))
        self.assertEqual(len(before.excluded), 1)
        self.assertIs(before.excluded[0].version, amended[0])
        self.assertEqual(before.excluded[0].reason, 'after_cutoff')

        after = self.register.in_force('1.1.1.1', day('2026-07-01'))
        self.assertIs(after.version, amended[0])
        self.assertEqual(after.chain, (self.baseline[0], amended[0]))
        self.assertEqual(after.excluded, ())
        # Every version in the chain is the supplied replacement of the one
        # before it, so the chain never points at a version the cutoff excluded.
        self.assertIsNone(after.chain[0].replaces)
        self.assertEqual(after.chain[1].replaces, after.chain[0].version_id)
        self.assertIn('five fictional days', before.version.text)
        self.assertIn('ten fictional days', after.version.text)
        self.assertNotEqual(before.version.version_id, after.version.version_id)

    def test_a_clause_the_amendment_does_not_name_does_not_change(self):
        self.register.apply(self.amendment())
        early = self.register.in_force('1.2.1.1', day('2026-03-01'))
        late = self.register.in_force('1.2.1.1', day('2026-07-01'))
        self.assertIs(early.version, late.version)
        self.assertEqual(early.version.text, late.version.text)
        self.assertIn('one hundred fictional pesos', late.version.text)
        self.assertEqual(late.excluded, ())

    def test_words_in_the_amendment_change_nothing(self):
        text = AMENDMENT.read_text(encoding='utf-8')
        self.assertIn('Clause 1.2.1.1 is hereby amended', text)
        self.assertIn('Clause 9.9.9.1', text)
        self.register.apply(self.amendment())
        late = self.register.in_force('1.2.1.1', day('2027-01-01'))
        self.assertIn('one hundred fictional pesos', late.version.text)
        self.assertNotIn('9.9.9.1', self.register.labels())
        with self.assertRaises(StructureError):
            self.register.in_force('9.9.9.1', day('2027-01-01'))

    def test_effectivity_words_never_become_dates(self):
        version = self.register.apply(self.amendment(effective=unknown(
            'the amending circular states no effectivity date')))[0]
        self.assertIsNone(version.effective.value)
        self.assertEqual(version.effective.unknown_reason,
                         'the amending circular states no effectivity date')
        self.assertEqual(version.first_availability, day('2026-06-01'))
        # The amending text says the substitution takes effect, and still no date
        # is read out of it: an unknown effectivity is reported, never guessed, so
        # the cutoff query keeps the old text and names the reason.
        self.assertIn('ten fictional days', self.amending.text)
        result = self.register.in_force('1.1.1.1', day('2026-07-01'))
        self.assertIs(result.version, self.baseline[0])
        self.assertEqual([(item.reason, item.version.amendment_ref) for item in result.excluded],
                         [(EFFECTIVITY_UNKNOWN, 'amendment-1')])

    def test_a_future_effective_amendment_waits_for_its_effectivity(self):
        amended = self.register.apply(self.amendment(
            availability=day('2026-02-01'), effective=day('2026-12-01')))[0]
        # Available in February, but not yet in force: the old text is returned.
        early = self.register.in_force('1.1.1.1', day('2026-03-01'))
        self.assertIs(early.version, self.baseline[0])
        self.assertEqual([(item.reason, item.version) for item in early.excluded],
                         [(NOT_YET_EFFECTIVE, amended)])
        on_the_day = self.register.in_force('1.1.1.1', day('2026-12-01'))
        self.assertIs(on_the_day.version, amended)
        self.assertEqual(on_the_day.excluded, ())

    def test_a_coarse_effectivity_is_not_placed_mid_period(self):
        month = DateMetadata('2026-06', 'month', None)
        amended = self.register.apply(self.amendment(
            availability=day('2026-05-01'), effective=month))[0]
        for cutoff in ('2026-06-01', '2026-06-15', '2026-06-29'):
            with self.subTest(cutoff=cutoff):
                result = self.register.in_force('1.1.1.1', day(cutoff))
                self.assertIs(result.version, self.baseline[0])
                self.assertEqual(result.excluded[0].reason, EFFECTIVITY_IMPRECISE)
        elapsed = self.register.in_force('1.1.1.1', day('2026-06-30'))
        self.assertIs(elapsed.version, amended)
        self.assertEqual(elapsed.version.effective, month)

    def test_effective_before_available_keeps_the_old_text(self):
        self.register.apply(self.amendment())
        between = self.register.in_force('1.1.1.1', day('2026-05-20'))
        self.assertIs(between.version, self.baseline[0])
        self.assertEqual(between.excluded[0].reason, 'after_cutoff')

    def test_unknown_availability_is_excluded_not_guessed(self):
        self.register.apply(self.amendment(availability=unknown()))
        result = self.register.in_force('1.1.1.1', day('2027-01-01'))
        self.assertIs(result.version, self.baseline[0])
        self.assertEqual([(item.reason, item.version.amendment_ref) for item in result.excluded],
                         [('availability_unknown', 'amendment-1')])
        self.assertEqual(len(self.register.versions('1.1.1.1')), 2)

    def test_a_coarse_availability_is_not_admitted_mid_period(self):
        month = DateMetadata('2026-06', 'month', None)
        self.register.apply(self.amendment(availability=month))
        amended = self.register.versions('1.1.1.1')[-1]
        for cutoff in ('2026-06-01', '2026-06-15', '2026-06-29'):
            with self.subTest(cutoff=cutoff):
                result = self.register.in_force('1.1.1.1', day(cutoff))
                self.assertIs(result.version, self.baseline[0])
                self.assertEqual(result.excluded[0].reason, 'availability_imprecise')
        # The month has run its course by its last day, so the version is placed.
        elapsed = self.register.in_force('1.1.1.1', day('2026-06-30'))
        self.assertIs(elapsed.version, amended)
        self.assertEqual(elapsed.version.first_availability, month)
        self.assertIs(self.register.in_force('1.1.1.1', day('2026-07-01')).version, amended)

    def test_a_february_effectivity_ends_on_the_real_calendar_last_day(self):
        # The review's reproduction: February 2026 is not a leap February, so the
        # month has fully elapsed on the 28th and the amendment is placed there —
        # no fabricated 29th delays it.
        month = DateMetadata('2026-02', 'month', None)
        amended = self.register.apply(self.amendment(
            availability=day('2026-02-01'), effective=month))[0]
        for cutoff in ('2026-02-01', '2026-02-27'):
            with self.subTest(cutoff=cutoff):
                result = self.register.in_force('1.1.1.1', day(cutoff))
                self.assertIs(result.version, self.baseline[0])
                self.assertEqual(result.excluded[0].reason, EFFECTIVITY_IMPRECISE)
        placed = self.register.in_force('1.1.1.1', day('2026-02-28'))
        self.assertIs(placed.version, amended)
        self.assertEqual(placed.version.effective, month)
        # A leap February ends on the 29th: imprecise on the 28th, placed on the 29th.
        leap = RuleRegister('wesm_rules')
        leap.add_baseline(self.base, day('2028-01-01'), effective=day('2028-01-01'))
        month = DateMetadata('2028-02', 'month', None)
        amended = leap.apply(self.amendment(
            ref='amendment-leap', availability=day('2028-02-01'), effective=month,
            replaces=leap.versions('1.1.1.1')[-1].version_id))[0]
        before = leap.in_force('1.1.1.1', day('2028-02-28'))
        self.assertIs(before.version, leap.versions('1.1.1.1')[0])
        self.assertEqual(before.excluded[0].reason, EFFECTIVITY_IMPRECISE)
        self.assertIs(leap.in_force('1.1.1.1', day('2028-02-29')).version, amended)

    def test_a_february_availability_ends_on_the_real_calendar_last_day(self):
        # The same rule for first availability: the month runs its course on the
        # 28th in 2026 and the 29th in the leap year 2028, never a fabricated day.
        for year, mid, last in (('2026', '2026-02-27', '2026-02-28'),
                                ('2028', '2028-02-28', '2028-02-29')):
            with self.subTest(year=year):
                register = RuleRegister('wesm_rules')
                register.add_baseline(self.base, day(f'{year}-01-01'),
                                      effective=day(f'{year}-01-01'))
                month = DateMetadata(f'{year}-02', 'month', None)
                amended = register.apply(self.amendment(
                    ref=f'amendment-february-{year}', availability=month,
                    effective=day(f'{year}-02-01'),
                    replaces=register.versions('1.1.1.1')[-1].version_id))[0]
                before = register.in_force('1.1.1.1', day(mid))
                self.assertIs(before.version, register.versions('1.1.1.1')[0])
                self.assertEqual(before.excluded[0].reason, AVAILABILITY_IMPRECISE)
                placed = register.in_force('1.1.1.1', day(last))
                self.assertIs(placed.version, amended)
                self.assertEqual(placed.version.first_availability, month)

    def test_a_new_clause_needs_the_record_that_says_so(self):
        with self.assertRaises(StructureError):
            self.register.apply(self.amendment(label='1.3.1.1'))
        added = self.register.apply(self.amendment(label='1.3.1.1', adds_clause=True))
        self.assertIsNone(added[0].replaces)
        self.assertEqual(added[0].clause_label, '1.3.1.1')
        early = self.register.in_force('1.3.1.1', day('2026-03-01'))
        self.assertIsNone(early.version)
        self.assertEqual(early.chain, ())
        self.assertEqual(early.excluded[0].reason, 'after_cutoff')
        late = self.register.in_force('1.3.1.1', day('2026-07-01'))
        self.assertIs(late.version, added[0])
        with self.assertRaises(StructureError):
            self.register.apply(self.amendment(label='1.1.1.1', adds_clause=True))

    def test_amendment_validation(self):
        base_id = self.baseline[0].version_id
        change = AmendmentChange('1.1.1.1', locator_for(
            self.amending, 'ten fictional days.'), 'The fictional notice period is five days.',
            base_id)
        with self.assertRaises(StructureError):
            Amendment(self.amending, 'amendment-1', day('2026-05-15'), day('2026-06-01'),
                      (change,))
        other = source(b'SYNTHETIC - another document\n', 'other-document')
        locator = locator_for(self.amending, 'ten fictional days.')
        with self.assertRaises(StructureError):
            Amendment(other, 'amendment-1', day('2026-05-15'), day('2026-06-01'),
                      (AmendmentChange('1.1.1.1', locator, 'ten fictional days.', base_id),))
        good = AmendmentChange('1.1.1.1', locator, 'ten fictional days.', base_id)
        for changes in ((), (good, good)):
            with self.subTest(changes=len(changes)), self.assertRaises(StructureError):
                Amendment(self.amending, 'amendment-1', day('2026-05-15'),
                          day('2026-06-01'), changes)
        for effective, availability in ((DateMetadata('2026-13-01', 'day', None), day('2026-06-01')),
                                        (DateMetadata('2026', 'month', None), day('2026-06-01')),
                                        (day('2026-05-15'), DateMetadata('2026-06', 'day', None))):
            with self.subTest(effective=effective), self.assertRaises(StructureError):
                Amendment(self.amending, 'amendment-1', effective, availability, (good,))
        with self.assertRaises(StructureError):
            Amendment(self.amending, '', day('2026-05-15'), day('2026-06-01'), (good,))
        with self.assertRaises(StructureError):
            self.register.apply('not an amendment')

    def test_a_change_must_supply_the_version_it_replaces(self):
        locator = locator_for(self.amending, 'ten fictional days.')
        with self.assertRaises(StructureError):
            AmendmentChange('1.1.1.1', locator, 'ten fictional days.')
        with self.assertRaises(StructureError):
            AmendmentChange('1.1.1.1', locator, 'ten fictional days.', '', False)
        with self.assertRaises(StructureError):
            AmendmentChange('1.1.1.1', locator, 'ten fictional days.',
                            self.baseline[0].version_id, True)

    def test_a_replacement_of_an_older_version_is_refused(self):
        first = self.register.apply(self.amendment())[0]
        # The February record names the version it really replaced — the baseline —
        # not the version the register happens to call the head.  A change can only
        # extend the chain it was supplied against, so this is a conflict.
        late = source(AMENDMENT.read_bytes(), 'synthetic-amendment-february')
        with self.assertRaises(StructureError):
            self.register.apply(self.amendment(
                ref='amendment-february', source=late, availability=day('2026-02-01'),
                effective=day('2026-02-15'), replaces=self.baseline[0].version_id))
        with self.assertRaises(StructureError):
            self.register.apply(self.amendment(
                ref='amendment-unknown', source=late, replaces='rv-0000000000000000'))
        self.assertEqual(self.register.versions('1.1.1.1'), (self.baseline[0], first))

    def test_an_amendment_cannot_predate_the_version_it_replaces(self):
        # The reviewer's August-then-February case: a document first available in
        # February cannot replace one first available in August, whatever it says.
        august = self.register.apply(self.amendment(availability=day('2026-08-01')))[0]
        february = source(AMENDMENT.read_bytes(), 'synthetic-amendment-february')
        with self.assertRaises(StructureError):
            self.register.apply(self.amendment(
                ref='amendment-february', source=february, availability=day('2026-02-01'),
                effective=day('2026-02-15'), replaces=august.version_id))
        self.assertEqual(self.register.versions('1.1.1.1'), (self.baseline[0], august))
        # A coarse availability period that overlaps the replaced version's own
        # period is not contradictory (the metadata cannot say more) and is kept.
        overlapping = self.register.apply(self.amendment(
            ref='amendment-august-coarse', source=february,
            availability=DateMetadata('2026-08', 'month', None),
            effective=day('2026-08-15'), replaces=august.version_id))[0]
        self.assertEqual(overlapping.replaces, august.version_id)

    def test_chain_across_two_amendments(self):
        first = self.register.apply(self.amendment())
        second_source = source(AMENDMENT.read_bytes(), 'synthetic-amendment-2')
        second = self.register.apply(self.amendment(
            ref='amendment-2', source=second_source,
            text='The fictional notice period is ten fictional days.',
            availability=day('2026-09-01')))
        chain = self.register.versions('1.1.1.1')
        self.assertEqual(len(chain), 3)
        self.assertEqual([version.replaces for version in chain],
                         [None, self.baseline[0].version_id, first[0].version_id])
        self.assertEqual(second[0].replaces, first[0].version_id)
        for cutoff, expected in (('2026-03-01', chain[0]), ('2026-07-01', chain[1]),
                                 ('2026-10-01', chain[2])):
            with self.subTest(cutoff=cutoff):
                self.assertIs(self.register.in_force('1.1.1.1', day(cutoff)).version,
                              expected)
        middle = self.register.in_force('1.1.1.1', day('2026-07-01'))
        self.assertEqual(middle.chain, tuple(chain[:2]))
        self.assertEqual([item.reason for item in middle.excluded], ['after_cutoff'])

    def test_identical_registration_is_idempotent(self):
        amendment = self.amendment()
        first = self.register.apply(amendment)
        again = self.register.apply(amendment)
        self.assertEqual(first, again)
        self.assertEqual(len(self.register.versions('1.1.1.1')), 2)
        later_ref = source(AMENDMENT.read_bytes(), 'synthetic-amendment-1-again')
        repeat = self.amendment(ref='amendment-1', source=later_ref)
        self.register.apply(self.amendment(ref='amendment-2', source=later_ref,
                                           availability=day('2026-09-01')))
        with self.assertRaises(StructureError):
            self.register.apply(repeat)

    def test_a_resubmission_with_changed_metadata_is_refused(self):
        # The review's reproduction: the same amendment ref, locator and text,
        # resubmitted with a different supplied effectivity, must not silently
        # return the version already stored.
        first = self.register.apply(self.amendment())[0]
        recorded = self.baseline[0].version_id
        with self.assertRaisesRegex(StructureError, 'resubmission supplies'):
            self.register.apply(self.amendment(effective=day('2026-12-01'),
                                               replaces=recorded))
        with self.assertRaisesRegex(StructureError, 'resubmission supplies'):
            self.register.apply(self.amendment(availability=day('2026-12-01'),
                                               replaces=recorded))
        self.assertEqual(self.register.versions('1.1.1.1'), (self.baseline[0], first))
        # A resubmission that repeats every field, in freshly built objects, is
        # still idempotent; the stored record keeps its own supplied dates, so the
        # clause is placed from 2026-05-15, never from the refused 2026-12-01.
        same = self.register.apply(self.amendment(effective=day('2026-05-15'),
                                                  availability=day('2026-06-01'),
                                                  replaces=recorded))
        self.assertEqual(same, (first,))
        result = self.register.in_force('1.1.1.1', day('2026-07-01'))
        self.assertIs(result.version, first)
        self.assertEqual(first.effective, day('2026-05-15'))
        self.assertEqual(first.first_availability, day('2026-06-01'))

    def test_register_and_cutoff_refusals(self):
        with self.assertRaises(StructureError):
            RuleRegister('wesm')
        with self.assertRaises(StructureError):
            self.register.in_force('9.9.9.9', day('2026-01-01'))
        with self.assertRaises(StructureError):
            self.register.in_force('1.1.1.1', unknown())
        self.assertEqual(self.register.family, 'wesm_rules')
        self.assertEqual(self.register.versions('1.1.1.1'), (self.baseline[0],))


class ChainAtCutoffTests(LineageTestCase):
    def test_the_chain_never_points_at_an_excluded_version(self):
        first = self.register.apply(self.amendment())[0]
        second = self.register.apply(self.amendment(
            ref='amendment-2', availability=day('2026-09-01'),
            effective=unknown('the second circular states no effectivity date')))[0]
        result = self.register.in_force('1.1.1.1', day('2026-10-01'))
        self.assertIs(result.version, first)
        self.assertEqual(result.chain, (self.baseline[0], first))
        self.assertEqual([(item.reason, item.version) for item in result.excluded],
                         [(EFFECTIVITY_UNKNOWN, second)])
        self.assertNotIn(second, result.chain)

    def test_a_version_below_an_unplaceable_one_is_not_in_force(self):
        first = self.register.apply(self.amendment(effective=unknown(
            'the first circular states no effectivity date')))[0]
        second = self.register.apply(self.amendment(
            ref='amendment-2', availability=day('2026-07-01'),
            effective=day('2026-07-01')))[0]
        self.assertEqual(second.replaces, first.version_id)
        result = self.register.in_force('1.1.1.1', day('2026-08-01'))
        self.assertIs(result.version, self.baseline[0])
        self.assertEqual(result.chain, (self.baseline[0],))
        self.assertEqual([(item.reason, item.version) for item in result.excluded],
                         [(ANCESTOR_NOT_IN_FORCE, second), (EFFECTIVITY_UNKNOWN, first)])


if __name__ == '__main__':
    unittest.main()
