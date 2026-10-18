"""Portfolio settings and email alerts (docs/work/alerts-portfolio-2026-10-17/).

Offline: a fake BigQuery, an in-memory store and mailer, fictional portfolio values and addresses
(example.invalid). No network, no SMTP, no cloud write. The HTTP checks need FastAPI and run in the
image (`docker run ... python -m unittest tests.test_alerts`); they are skipped without it.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.alerts import model, sql
from src.alerts.auth import GoogleUsers, NotAllowed, NotSignedIn, SchedulerAuth, parse_editors
from src.alerts.mail import MemoryMailer, SmtpMailer, mailer_from
from src.alerts.service import AlertService, ChecksUnavailable, NoRules, drivers_from
from src.alerts.store import MemoryAlertStore

try:
    from fastapi.testclient import TestClient
    FASTAPI = True
except ImportError:
    FASTAPI = False

USER = {'uid': 'u-1', 'email': 'analyst@example.invalid'}


def portfolio(**over):
    body = {'effective_from': '2026-09-01', 'note': 'fictional test portfolio', 'benchmark_php_mwh': 6000,
            'regions': {'CVIS': {'demand_mw_by_hour': [50] * 24}},
            'contracts': [{'name': 'Contract A', 'region': 'CVIS', 'mw': 30, 'price_php_mwh': 5000,
                           'hours': list(range(8, 20)), 'start': '2026-01-01', 'end': '2026-12-31'}],
            'nodes': []}
    body.update(over)
    return body


def rules(**over):
    body = {'enabled': True, 'threshold': {'mode': 'absolute', 'value': 15000}, 'regions': ['CVIS', 'CLUZ'],
            'min_severity': 'medium',
            'recipients': [{'email': 'Desk@Example.invalid', 'regions': ['CVIS'], 'min_severity': 'high'},
                           {'email': 'risk@example.invalid', 'regions': [], 'min_severity': None}]}
    body.update(over)
    return body


CARD = {'summary': {'severity': 'High', 'severity_reason': 'price band very_high (29,919 PHP/MWh)',
                    'confidence': 'Low', 'confidence_reason': '2 of 41 facts evidence-known',
                    'relationship_trail': 'demand → Visayas → price 29,919 PHP/MWh',
                    'what_to_check': ['check demand in the next intervals'],
                    'financial_impact': 'Not available: needs portfolio data (positions, contracts, load nodes)'},
        'drivers': [{'rank': 1, 'family': 'S', 'family_score': 0.7768, 'status': 'scored', 'indicator': 'import_share',
                     'value_at_t': 0.105, 'baseline_median': 0.065, 'indicator_score': 0.7768},
                    {'rank': 1, 'family': 'S', 'family_score': 0.7768, 'status': 'scored', 'indicator': 'hvdc_links_congested',
                     'value_at_t': 1, 'baseline_median': 1, 'indicator_score': 0.4},
                    {'rank': 2, 'family': 'D', 'family_score': 0.7708, 'status': 'scored', 'indicator': 'demand_mw',
                     'value_at_t': 2502, 'baseline_median': 2382, 'indicator_score': 0.7708},
                    {'rank': None, 'family': 'Rules', 'family_score': None, 'status': 'listed', 'indicator': 'cap_bound',
                     'value_at_t': None, 'baseline_median': None, 'indicator_score': None}]}


def value(params, name):
    for p in params:
        if p['name'] == name:
            v = p['parameterValue']
            return [x['value'] for x in v['arrayValues']] if 'arrayValues' in v else v['value']


class FakeBigQuery:
    """Labels rows keyed by (interval_manila, region); cards finish after `polls` status reads."""

    def __init__(self, prices, latest=None, card=CARD, polls=1, fail_card=None):
        self.prices, self.latest, self.card, self.polls, self.fail_card = prices, latest, card, polls, fail_card
        self.started, self.reads, self.queries = [], {}, []

    def query(self, text, params=(), max_bytes=0, labels=None, seconds=30):
        self.queries.append((text, params, max_bytes))
        if text == sql.LATEST_INTERVAL:
            return [{'latest': self.latest}], 10_485_760
        after = value(params, 'after')[:16].replace(' ', 'T')
        until = value(params, 'until')[:16].replace(' ', 'T')
        regions = value(params, 'regions')
        rows = [dict(r, interval_manila=t, region=g) for (t, g), r in sorted(self.prices.items())
                if after < t <= until and g in regions]
        return rows, 10_485_760

    def start(self, text, params=(), max_bytes=0, labels=None):
        job = 'job-%d' % len(self.started)
        self.started.append((job, text, params, max_bytes))
        self.reads[job] = 0
        return job

    def status(self, job):
        self.reads[job] += 1
        done = self.reads[job] >= self.polls
        return {'state': 'DONE' if done else 'RUNNING', 'error': self.fail_card if done else None,
                'bytes_billed': 388_000_000 if done else 0}

    def rows(self, job):
        return [{'alert_json': json.dumps(self.card)}]


def service(prices=None, latest=None, mailer=None, **kw):
    bq = FakeBigQuery(prices or {}, latest, **kw)
    mail = MemoryMailer() if mailer is None else mailer
    clock = iter('2026-10-17T08:%02d:00+00:00' % i for i in range(60))
    return AlertService(MemoryAlertStore(), bq, mail, clock=lambda: next(clock)), bq, mail


PEDC = {('2026-09-21T13:40', 'CVIS'): {'price': 29919.2025, 'price_band': 'very_high',
                                       'baseline_median': 6000.0, 'baseline_n': 28}}


class Validation(unittest.TestCase):
    def test_a_portfolio_is_validated_and_normalised(self):
        out = model.validate_portfolio(portfolio())
        self.assertEqual([50] * 24, out['regions']['CVIS']['demand_mw_by_hour'])
        self.assertEqual(list(range(8, 20)), out['contracts'][0]['hours'])

    def test_refusals_name_the_field(self):
        cases = [
            (portfolio(regions={'CVIS': {'demand_mw_by_hour': [1] * 23}}), 'regions.CVIS.demand_mw_by_hour'),
            (portfolio(regions={'XX': {'demand_mw_by_hour': [1] * 24}}), 'regions'),
            (portfolio(benchmark_php_mwh=-1), 'benchmark_php_mwh'),
            (portfolio(effective_from='17/10/2026'), 'effective_from'),
            (dict(portfolio(), version=9), 'portfolio'),
            (portfolio(regions={}, contracts=[]), 'regions'),
            (portfolio(contracts=[{'name': 'A', 'region': 'CVIS', 'mw': 1, 'price_php_mwh': 1, 'hours': [24],
                                   'start': '2026-01-01', 'end': '2026-12-31'}]), 'contracts[0].hours'),
            (portfolio(contracts=[{'name': 'A', 'region': 'CVIS', 'mw': 1, 'price_php_mwh': 1, 'hours': [1],
                                   'start': '2026-12-31', 'end': '2026-01-01'}]), 'contracts[0].end'),
        ]
        for body, field in cases:
            with self.subTest(field=field), self.assertRaises(model.InvalidInput) as ctx:
                model.validate_portfolio(body)
            self.assertEqual(field, ctx.exception.field)

    def test_rules_lower_case_emails_and_fill_recipient_defaults(self):
        out = model.validate_rules(rules())
        self.assertEqual('desk@example.invalid', out['recipients'][0]['email'])
        self.assertEqual(['CLUZ', 'CVIS'], out['recipients'][1]['regions'])
        self.assertEqual('medium', out['recipients'][1]['min_severity'])
        for body, field in ((rules(threshold={'mode': 'absolute', 'value': 0}), 'threshold.value'),
                            (rules(min_severity='urgent'), 'min_severity'),
                            (rules(recipients=[{'email': 'not-an-email'}]), 'recipients[0].email'),
                            (rules(recipients=[{'email': 'a@example.invalid'}, {'email': 'A@example.invalid'}]),
                             'recipients[1].email')):
            with self.subTest(field=field), self.assertRaises(model.InvalidInput) as ctx:
                model.validate_rules(body)
            self.assertEqual(field, ctx.exception.field)

    def test_extreme_is_a_high_card_in_an_extreme_price_band(self):
        self.assertEqual('extreme', model.alert_severity('High', 'extreme'))
        self.assertEqual('high', model.alert_severity('High', 'very_high'))
        self.assertEqual('medium', model.alert_severity('Medium', 'extreme'))
        self.assertEqual('unrated', model.alert_severity(None, 'extreme'))
        self.assertTrue(model.passes('extreme', 'high'))
        self.assertFalse(model.passes('high', 'extreme'))
        self.assertFalse(model.passes('unrated', 'low'))

    def test_interval_must_be_a_five_minute_manila_start(self):
        self.assertEqual(datetime(2026, 9, 21, 13, 40), model.parse_interval('2026-09-21T13:40'))
        for bad in ('2026-09-21T13:42', '2026-09-21 13:40', '2026-13-01T00:00', None):
            with self.subTest(bad=bad), self.assertRaises(model.InvalidInput):
                model.parse_interval(bad)


class Impact(unittest.TestCase):
    def setUp(self):
        self.p = dict(model.validate_portfolio(portfolio()), version=3)

    def test_the_contract_formula(self):
        at = datetime(2026, 9, 21, 13, 40)
        out = model.impact(self.p, 'CVIS', at, 29919.2025)
        self.assertEqual(20, out['unhedged_mw'])  # 50 demand - 30 contracted at 13:00
        self.assertAlmostEqual(20 * (29919.2025 - 6000) / 12, out['php'], places=2)
        self.assertEqual('Estimate from portfolio v3, effective 2026-09-01', out['basis'])

    def test_outside_contract_hours_all_demand_is_unhedged(self):
        self.assertEqual(50, model.impact(self.p, 'CVIS', datetime(2026, 9, 21, 22, 0), 8000)['unhedged_mw'])

    def test_price_below_benchmark_is_a_signed_gain(self):
        out = model.impact(self.p, 'CVIS', datetime(2026, 9, 21, 13, 40), 3000)
        self.assertLess(out['php'], 0)
        self.assertIn('gain', model.impact_line(out))

    def test_over_contracted_is_stated(self):
        p = dict(self.p, regions={'CVIS': {'demand_mw_by_hour': [10] * 24}})
        out = model.impact(p, 'CVIS', datetime(2026, 9, 21, 13, 40), 20000)
        self.assertEqual(-20, out['unhedged_mw'])
        self.assertIn('over-contracted by 20 MW', out['note'])

    def test_no_portfolio_or_no_region_is_never_a_number(self):
        self.assertEqual({'status': model.NO_PORTFOLIO}, model.impact(None, 'CVIS', datetime(2026, 9, 21), 1))
        self.assertNotIn('php', model.impact(self.p, 'CLUZ', datetime(2026, 9, 21), 1))

    def test_the_version_in_force_is_the_latest_effective_on_the_day(self):
        versions = [{'version': 1, 'effective_from': '2026-01-01'}, {'version': 2, 'effective_from': '2026-10-01'}]
        self.assertEqual(1, model.latest_portfolio(versions, datetime(2026, 9, 21).date())['version'])
        self.assertEqual(2, model.latest_portfolio(versions, datetime(2026, 10, 2).date())['version'])
        self.assertIsNone(model.latest_portfolio(versions, datetime(2025, 1, 1).date()))


SOURCE = {'kind': 'import', 'built_at': '2026-10-17T09:00:00Z',
          'window': {'first': '2026-09-09', 'last': '2026-10-06', 'days': 28},
          'units': {'mq': 'kWh', 'bcq': 'MWh', 'stated_by': 'fictional desk'}}
DRAFT = {'kind': 'portfolio-draft', 'built_at': SOURCE['built_at'], 'window': SOURCE['window'], 'units': SOURCE['units'],
         'regions': {'CVIS': {'demand_mw_by_hour': [50] * 24, 'contracted_mw_by_hour': [20] * 24, 'intervals': 8064}},
         'left_out': {'bcq_nodes_without_meters': 1, 'bcq_mw_without_meters': 3.0, 'unmapped_nodes': 0,
                      'regions_missing_hours': []}, 'quality': {}}


class FakeDraft:
    def __init__(self, draft=DRAFT, fail=False):
        self.draft, self.fail = draft, fail

    def read(self):
        if self.fail:
            from src.alerts.draft import DraftUnavailable
            raise DraftUnavailable('storage answered 403')
        return self.draft


class Imported(unittest.TestCase):
    """The portfolio import (docs/work/portfolio-import-2026-10-17): a contracted-by-hour profile and a tag."""

    def test_the_profile_adds_to_the_listed_contracts(self):
        body = portfolio(regions={'CVIS': {'demand_mw_by_hour': [50] * 24, 'contracted_mw_by_hour': [5] * 24}}, source=SOURCE)
        p = dict(model.validate_portfolio(body), version=4)
        out = model.impact(p, 'CVIS', datetime(2026, 9, 21, 13, 40), 6000 + 120)
        self.assertEqual((35, 15), (out['contracted_mw'], out['unhedged_mw']))  # 30 listed + 5 profile
        self.assertEqual(15 * 120 / 12, out['php'])
        self.assertEqual('Estimate from portfolio v4 (imported, BCQ/MQ to 2026-10-06), effective 2026-09-01', out['basis'])
        self.assertEqual(45, model.impact(p, 'CVIS', datetime(2026, 9, 21, 22, 0), 1)['unhedged_mw'])

    def test_profile_and_tag_are_validated(self):
        for bad, field in ((portfolio(regions={'CVIS': {'demand_mw_by_hour': [1] * 24, 'contracted_mw_by_hour': [1] * 23}}),
                            'regions.CVIS.contracted_mw_by_hour'),
                           (portfolio(regions={'CVIS': {'demand_mw_by_hour': [1] * 24, 'contracted_mw_by_hour': [-1] + [1] * 23}}),
                            'regions.CVIS.contracted_mw_by_hour[0]'),
                           (portfolio(source=dict(SOURCE, kind='typed')), 'source.kind'),
                           (portfolio(source=dict(SOURCE, units={'mq': 'MW', 'bcq': 'MWh'})), 'source.units'),
                           (portfolio(source=dict(SOURCE, extra=1)), 'source')):
            with self.assertRaises(model.InvalidInput) as cm:
                model.validate_portfolio(bad)
            self.assertEqual(field, cm.exception.field)

    def test_without_the_new_fields_a_portfolio_is_as_before(self):
        out = model.validate_portfolio(portfolio())
        self.assertNotIn('source', out)
        self.assertNotIn('contracted_mw_by_hour', out['regions']['CVIS'])

    def test_the_draft_is_off_unless_wired(self):
        from src.alerts.service import ImportOff, NoDraft
        svc, _, _ = service()
        self.assertFalse(svc.config(USER)['import_available'])
        with self.assertRaises(ImportOff):
            svc.portfolio_draft(USER)
        svc.draft = FakeDraft(draft=None)
        self.assertTrue(svc.config(None)['import_available'])
        with self.assertRaises(NoDraft):
            svc.portfolio_draft(USER)
        svc.draft = FakeDraft()
        self.assertEqual(DRAFT, svc.portfolio_draft(USER))
        self.assertEqual([], svc.store.versions('portfolio'))  # reading the draft never saves a version

    def test_the_bucket_reader(self):
        from src.alerts.draft import DraftUnavailable, GcsDraft

        class Answer:
            def __init__(self, status, content=b''):
                self.status_code, self.content = status, content

        class Session:
            def __init__(self, answer):
                self.answer, self.urls = answer, []

            def get(self, url, timeout):
                self.urls.append(url)
                return self.answer

        ok = Session(Answer(200, json.dumps(DRAFT).encode()))
        self.assertEqual(DRAFT, GcsDraft(session=ok).read())
        self.assertEqual('https://storage.googleapis.com/storage/v1/b/grid-nowcast-data/o/'
                         'raw%2Fportfolio%2Fderived%2Fdraft-latest.json?alt=media', ok.urls[0])
        self.assertIsNone(GcsDraft(session=Session(Answer(404))).read())
        for answer in (Answer(403), Answer(200, b'not json'), Answer(200, b'{"kind": "other"}')):
            with self.assertRaises(DraftUnavailable):
                GcsDraft(session=Session(answer)).read()

    def test_the_switch_is_on_only_when_exactly_on(self):
        source = (ROOT / 'src/api/hosted.py').read_text(encoding='utf-8')
        self.assertIn("(env.get('NOWCAST_PORTFOLIO_IMPORT') or '').strip() == 'on'", source)


class Email(unittest.TestCase):
    def test_the_message_carries_the_five_fields_and_escapes(self):
        alert = {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40', 'price_php_mwh': 29919.2,
                 'severity': 'high', 'severity_reason': '<b>very_high</b>', 'confidence': 'Low',
                 'confidence_reason': 'r', 'relationship_trail': 'a → b', 'what_to_check': ['x', 'y'],
                 'likely_drivers': drivers_from(CARD['drivers']), 'threshold_text': 't',
                 'financial_impact': {'status': model.NO_PORTFOLIO}, 'event_url': 'https://x/alerts?alert="k"'}
        subject, text, html = model.email_message(alert)
        self.assertEqual('[InGRID] HIGH · Visayas 29,919 PHP/MWh · 21 Sep 2026 13:40 Manila', subject)
        for needle in ('Severity:', 'Financial impact: Not available: no portfolio entered', 'Confidence: Low',
                       'Relationship trail: a → b', 'What to check: x; y', model.DISCLAIMER, 'Supply 0.78'):
            self.assertIn(needle, text)
        self.assertIn('&lt;b&gt;very_high&lt;/b&gt;', html)
        self.assertNotIn('<b>very_high', html)
        self.assertIn('href="https://x/alerts?alert=&quot;k&quot;"', html)
        for word in ('buy', 'sell', 'hedge now'):
            self.assertNotIn(word, text.lower().replace('nothing here is trading advice', ''))

    def test_drivers_take_each_familys_strongest_indicator_in_rank_order(self):
        out = drivers_from(CARD['drivers'])
        self.assertEqual(['S', 'D'], [d['family'] for d in out])
        self.assertEqual('import share 0.105 vs 28-day median 0.065', out[0]['why'])

    def test_the_mailer_never_shows_its_password(self):
        self.assertNotIn('secret-value', repr(SmtpMailer('a@example.invalid', 'secret-value')))
        self.assertIsNone(mailer_from({'NOWCAST_SMTP_USER': 'a@example.invalid'}))


class Store(unittest.TestCase):
    def test_versions_are_append_only_and_numbered(self):
        store = MemoryAlertStore()
        self.assertEqual(1, store.add_version('portfolio', {'a': 1}))
        self.assertEqual(2, store.add_version('portfolio', {'a': 2}))
        self.assertEqual([1, 2], [v['version'] for v in store.versions('portfolio')])
        self.assertEqual(2, store.latest('portfolio')['a'])

    def test_an_alert_key_is_created_once(self):
        store = MemoryAlertStore()
        self.assertTrue(store.create_alert('k', {'key': 'k', 'n': 1}))
        self.assertFalse(store.create_alert('k', {'key': 'k', 'n': 2}))
        self.assertEqual(1, store.get_alert('k')['n'])


class ManualRun(unittest.TestCase):
    def test_no_rules_no_check(self):
        svc, _, _ = service(PEDC)
        with self.assertRaises(NoRules):
            svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})

    def test_demo_mode_has_no_checks(self):
        svc = AlertService(MemoryAlertStore())
        svc.save_rules(USER, rules())
        with self.assertRaises(ChecksUnavailable):
            svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})

    def test_the_pedc_check_records_one_alert_and_emails_each_recipient_once(self):
        svc, bq, mail = service(PEDC, polls=2)
        svc.save_portfolio(USER, portfolio())
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        self.assertEqual('running', run['status'])
        self.assertEqual(1, len(bq.started))
        job, text, params, max_bytes = bq.started[0]
        self.assertEqual('2026-09-21 13:40:00+08:00', value(params, 't'))
        self.assertEqual('assumed', value(params, 'mode'))
        self.assertEqual(2_000_000_000, max_bytes)
        self.assertEqual('running', svc.poll_run(run['id'])['status'])
        done = svc.poll_run(run['id'])
        self.assertEqual('done', done['status'])
        alert = done['alerts'][0]
        self.assertEqual('high', alert['severity'])
        self.assertTrue(alert['crossed'])
        self.assertEqual('Estimate from portfolio v1, effective 2026-09-01', alert['financial_impact']['basis'])
        self.assertEqual(['desk@example.invalid', 'risk@example.invalid'], alert['emailed_to'])
        self.assertEqual(2, len(mail.outbox))
        self.assertEqual(done['bytes_billed'], 10_485_760 + 388_000_000)
        # Polling a finished run or checking the same interval again never emails twice.
        svc.poll_run(run['id'])
        again = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        svc.poll_run(again['id']), svc.poll_run(again['id'])
        self.assertEqual(2, len(mail.outbox))
        self.assertEqual(1, len(svc.store.recent_alerts()))

    def test_the_run_answer_waits_for_its_card_when_it_can_sleep(self):
        svc, bq, mail = service(PEDC, polls=3)
        naps = []
        svc.sleep = naps.append
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        self.assertEqual('done', run['status'])
        self.assertEqual([2, 2, 2], naps)
        self.assertEqual(1, len(run['alerts']))
        self.assertEqual(2, run['emailed'])

    def test_below_threshold_shows_the_card_but_records_and_sends_nothing(self):
        svc, bq, mail = service(PEDC, polls=1)
        svc.save_rules(USER, rules(threshold={'mode': 'absolute', 'value': 40000}))
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        done = svc.poll_run(run['id'])
        self.assertFalse(done['alerts'][0]['crossed'])
        self.assertEqual([], mail.outbox)
        self.assertEqual([], svc.store.recent_alerts())

    def test_ratio_threshold_uses_the_baseline(self):
        svc, _, _ = service(PEDC, polls=1)
        svc.save_rules(USER, rules(threshold={'mode': 'ratio_to_baseline', 'value': 4.0}))
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        self.assertTrue(run['candidates'][0]['crossed'])  # 29,919 >= 4 x 6,000
        self.assertIn('4 x the 28-day median', run['candidates'][0]['threshold_text'])

    def test_no_portfolio_says_not_available(self):
        svc, _, _ = service(PEDC, polls=1)
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        self.assertEqual({'status': model.NO_PORTFOLIO}, svc.poll_run(run['id'])['alerts'][0]['financial_impact'])

    def test_mail_failure_is_recorded_not_raised(self):
        svc, _, _ = service(PEDC, polls=1, mailer=MemoryMailer(fail=True))
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        alert = svc.poll_run(run['id'])['alerts'][0]
        self.assertEqual([], alert['emailed_to'])
        self.assertIn('mail server', alert['email_error'])

    def test_a_failed_card_is_reported(self):
        svc, _, _ = service(PEDC, polls=1, fail_card='bytesBilledLimitExceeded')
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        done = svc.poll_run(run['id'])
        self.assertEqual('done', done['status'])
        self.assertEqual('bytesBilledLimitExceeded', done['candidates'][0]['error'])


class Concurrency(unittest.TestCase):
    def test_concurrent_polls_email_each_recipient_once(self):
        class SlowMailer(MemoryMailer):
            def send(self, messages):
                time.sleep(0.05)  # a slow server: every poller is inside _email at once
                return super().send(messages)
        svc, bq, mail = service(PEDC, polls=1, mailer=SlowMailer())
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        bq.reads = {k: 10 for k in bq.reads}  # the card is done for every poller
        start = threading.Barrier(8)

        def poll():
            start.wait()
            svc.poll_run(run['id'])
        threads = [threading.Thread(target=poll) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(['desk@example.invalid', 'risk@example.invalid']), sorted(m[0] for m in mail.outbox))
        self.assertEqual(sorted(['desk@example.invalid', 'risk@example.invalid']),
                         sorted(svc.store.recent_alerts()[0]['emailed_to']))

    def test_a_failed_send_is_released_for_a_later_retry(self):
        mailer = MemoryMailer(fail=True)
        svc, _, _ = service(PEDC, polls=1, mailer=mailer)
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        svc.poll_run(run['id'])
        mailer.fail = False
        again = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        svc.poll_run(again['id'])
        self.assertEqual(2, len(mailer.outbox))
        self.assertIsNone(svc.store.recent_alerts()[0]['email_error'])

    def test_a_run_uses_the_rules_it_started_with(self):
        svc, _, mail = service(PEDC, polls=2)
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        svc.poll_run(run['id'])  # still running
        svc.save_rules(USER, rules(recipients=[{'email': 'late@example.invalid'}], enabled=False))
        done = svc.poll_run(run['id'])
        self.assertEqual(1, done['rules_version'])
        self.assertEqual(['desk@example.invalid', 'risk@example.invalid'], sorted(m[0] for m in mail.outbox))


DEPLOY_SCRIPT = ROOT / 'scripts' / 'deploy' / 'deploy.sh'
CARD_SUMMARY_SOURCE = ROOT / 'scripts' / 'ontology' / 'sql' / '06_card_summary.sql'


@unittest.skipUnless(DEPLOY_SCRIPT.exists(), 'scripts/deploy/deploy.sh is withheld from the public export')
class DeployLine(unittest.TestCase):
    """The alerts settings travel only when configured; otherwise the line is the one before them."""

    def line(self, **env):
        # DATA-2: a release refuses a bake without build_all.py's manifest, even in a dry run (which
        # checks only that the file is there); the dry run reads a temporary directory holding one.
        with tempfile.TemporaryDirectory() as baked:
            Path(baked, 'manifest.json').write_text('{"schema": "bake-manifest/1"}', encoding='utf-8')
            result = subprocess.run(['bash', 'scripts/deploy/deploy.sh', '--dry-run'], cwd=ROOT, capture_output=True,
                                    text=True, env=dict(os.environ, GRID_DATA=baked, **env), timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)
        return [l for l in result.stdout.splitlines() if 'gcloud run deploy' in l][0]

    def test_absent_or_off_is_todays_line(self):
        today = "FIREBASE_WEB_API_KEY=<from .local/hosting/firebase-web-api-key> --format 'value(status.latestCreatedRevisionName)'"
        for env in ({'ALERTS_SMTP_USER_FILE': '/nonexistent/smtp-user'}, {'ALERTS': 'off'}):
            with self.subTest(env=env):
                line = self.line(**env)
                self.assertTrue(line.endswith(today), line)
                self.assertNotIn('NOWCAST_ALERT', line)

    def test_a_sender_file_adds_the_secret_and_never_prints_the_address(self):
        with tempfile.TemporaryDirectory() as directory:
            sender = Path(directory) / 'smtp-user'
            sender.write_text('sender@example.invalid\n', encoding='utf-8')
            line = self.line(ALERTS_SMTP_USER_FILE=str(sender))
        self.assertIn('--set-secrets NOWCAST_SMTP_PASSWORD=nowcast-smtp-password:latest', line)
        self.assertIn('NOWCAST_ALERT_SCHEDULER_AUDIENCE=https://grid-nowcast-adcri4pd6q-as.a.run.app/api/alerts/scheduled', line)
        self.assertNotIn('sender@example.invalid', line)


    def test_the_import_switch_travels_only_when_on(self):
        self.assertNotIn('PORTFOLIO_IMPORT', self.line(ALERTS='off'))
        self.assertNotIn('PORTFOLIO_IMPORT', self.line(ALERTS='off', PORTFOLIO_IMPORT='yes'))
        line = self.line(ALERTS='off', PORTFOLIO_IMPORT='on')
        self.assertIn(',NOWCAST_PORTFOLIO_IMPORT=on --format', line)


class ScheduledRun(unittest.TestCase):
    def prices(self):
        rows = {}
        for minute, price in ((0, 9000), (5, 18000), (10, 21000), (15, 12000)):
            rows[('2026-10-14T19:%02d' % minute, 'CVIS')] = {'price': price, 'price_band': 'high',
                                                              'baseline_median': 7000.0, 'baseline_n': 28}
            rows[('2026-10-14T19:%02d' % minute, 'CLUZ')] = {'price': price / 2, 'price_band': 'normal',
                                                              'baseline_median': 7000.0, 'baseline_n': 28}
        return rows

    def test_first_run_checks_the_last_hour_and_cards_one_parent_event_per_region(self):
        svc, bq, mail = service(self.prices(), latest='2026-10-14T19:15', polls=1)
        svc.save_rules(USER, rules())
        out = svc.scheduled()
        self.assertEqual(1, len(bq.started), 'one region crossed: one card')
        self.assertEqual([{'region': 'CVIS', 'intervals_above': 2, 'first': '2026-10-14T19:05',
                           'last': '2026-10-14T19:10'}], out['events'])
        self.assertEqual('2026-10-14T19:10', out['candidates'][0]['interval_manila'], 'the peak is carded')
        self.assertEqual('2026-10-14T19:15', svc.store.get_state('last_checked')['interval_manila'])
        again = svc.scheduled()
        self.assertEqual('no new data', again['status'])
        self.assertEqual([out['id']], again['finished_runs'], 'the pending run is finished first')
        self.assertEqual(1, len(svc.store.recent_alerts()))
        self.assertEqual(['desk@example.invalid', 'risk@example.invalid'], svc.store.recent_alerts()[0]['emailed_to'])

    def test_disabled_or_missing_rules_check_nothing(self):
        svc, bq, _ = service(self.prices(), latest='2026-10-14T19:15')
        self.assertEqual('no rules saved', svc.scheduled()['status'])
        svc.save_rules(USER, rules(enabled=False))
        self.assertEqual('notifications disabled', svc.scheduled()['status'])
        self.assertEqual([], bq.started)

    def test_cards_per_run_are_capped(self):
        prices = {('2026-10-14T19:15', r): {'price': 30000, 'price_band': 'very_high', 'baseline_median': 1.0,
                                             'baseline_n': 28} for r in ('CLUZ', 'CVIS', 'CMIN')}
        svc, bq, _ = service(prices, latest='2026-10-14T19:15')
        svc.max_cards = 2
        svc.save_rules(USER, rules(regions=['CLUZ', 'CVIS', 'CMIN']))
        out = svc.scheduled()
        self.assertEqual(2, len(bq.started))
        self.assertIn('1 more regions crossed', out['notes'][0])


class Visibility(unittest.TestCase):
    def test_not_signed_in_sees_no_portfolio_numbers_recipients_or_estimates(self):
        svc, _, _ = service(PEDC, polls=1)
        svc.save_portfolio(USER, portfolio())
        svc.save_rules(USER, rules())
        run = svc.start_run(USER, {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'})
        svc.poll_run(run['id'])
        public = svc.config(None)
        self.assertEqual({'present': True, 'version': 1, 'effective_from': '2026-09-01'}, public['portfolio'])
        self.assertEqual(2, public['rules']['recipients_count'])
        self.assertNotIn('recipients', public['rules'])
        text = json.dumps([public, svc.history(None)])
        for secret in ('desk@example.invalid', 'risk@example.invalid', 'Contract A', '"php"'):
            self.assertNotIn(secret, text)
        self.assertIn('php', svc.history(USER)[0]['financial_impact'])

    def test_test_email_lists_the_rule_and_says_test(self):
        svc, _, mail = service()
        svc.save_rules(USER, rules())
        self.assertEqual(['desk@example.invalid', 'risk@example.invalid'], svc.test_email(USER)['sent_to'])
        self.assertTrue(all('TEST' in m[1] and 'no alert was raised' in m[2] for m in mail.outbox))


class Auth(unittest.TestCase):
    def claims(self, **over):
        c = {'uid': 'u', 'email': 'A@Example.invalid', 'email_verified': True, 'firebase': {'sign_in_provider': 'google.com'}}
        c.update(over)
        return c

    def test_a_verified_google_or_a_password_sign_in_counts(self):
        good = GoogleUsers(lambda token: self.claims())
        self.assertEqual('a@example.invalid', good.user('Bearer t')['email'])
        self.assertEqual('google.com', good.user('Bearer t')['provider'])
        self.assertIsNone(good.user(None))
        self.assertIsNone(good.user('Basic t'))
        # Email and password accounts are made by the team (Admin SDK), so no verified email is needed.
        for claims in (self.claims(firebase={'sign_in_provider': 'password'}),
                       self.claims(firebase={'sign_in_provider': 'password'}, email_verified=False)):
            user = GoogleUsers(lambda token, c=claims: c).require('Bearer t')
            self.assertEqual(('a@example.invalid', 'password'), (user['email'], user['provider']))
        for claims in (self.claims(firebase={'sign_in_provider': 'anonymous'}),
                       self.claims(firebase={'sign_in_provider': 'custom'}),
                       self.claims(firebase={'sign_in_provider': 'phone'}),
                       self.claims(firebase={}),
                       self.claims(email_verified=False),
                       self.claims(firebase={'sign_in_provider': 'password'}, email=None),
                       self.claims(firebase={'sign_in_provider': 'password'}, email='  ')):
            self.assertIsNone(GoogleUsers(lambda token, c=claims: c).user('Bearer t'))

        def broken(token):
            raise ValueError('expired')
        self.assertIsNone(GoogleUsers(broken).user('Bearer t'))
        with self.assertRaises(NotSignedIn):
            GoogleUsers().require('Bearer t')

    def test_editors_narrow_editing_only_when_set(self):
        self.assertEqual(('a@x.invalid', '@y.invalid'), parse_editors('a@x.invalid; @y.invalid'))
        users = GoogleUsers(lambda token: self.claims(), editors=('@other.invalid',))
        with self.assertRaises(NotAllowed):
            users.require('Bearer t')
        self.assertEqual('a@example.invalid', GoogleUsers(lambda t: self.claims(), ('@example.invalid',)).require('Bearer t')['email'])
        pw = self.claims(firebase={'sign_in_provider': 'password'}, email='judge@other.invalid')
        with self.assertRaises(NotAllowed):
            GoogleUsers(lambda t: pw, ('@example.invalid',)).require('Bearer t')

    def test_the_scheduler_token_must_name_the_account_and_audience(self):
        aud = 'https://svc.example.invalid/api/alerts/scheduled'
        ok = {'email': 'sched@example.invalid', 'email_verified': True, 'aud': aud}
        self.assertTrue(SchedulerAuth('sched@example.invalid', aud, lambda t, a: ok).check('Bearer t'))
        self.assertFalse(SchedulerAuth('sched@example.invalid', aud, lambda t, a: dict(ok, email='x@example.invalid')).check('Bearer t'))
        self.assertFalse(SchedulerAuth('sched@example.invalid', aud, lambda t, a: dict(ok, aud='other')).check('Bearer t'))
        self.assertFalse(SchedulerAuth('', aud, lambda t, a: ok).check('Bearer t'), 'unconfigured refuses')


class LiveCardSql(unittest.TestCase):
    @unittest.skipUnless(CARD_SUMMARY_SOURCE.exists(), 'scripts/ontology/sql is withheld from the public export')
    def test_the_vendored_card_summary_is_the_ontologys_own(self):
        self.assertEqual((ROOT / 'scripts/ontology/sql/06_card_summary.sql').read_bytes(), sql.CARD_SUMMARY_SQL.read_bytes())

    def test_the_live_card_reads_this_intervals_card_not_the_recorded_ones(self):
        script = sql.card_script()
        self.assertNotIn('recorded_cards', script)
        self.assertNotIn('recorded_drivers', script)
        for needle in ('DECLARE card_region STRING DEFAULT @region;', 'DECLARE t TIMESTAMP DEFAULT @t;',
                       'grid_ontology.driver_card`(card_region, t, card_mode)',
                       'grid_ontology.likely_drivers`(card_region, t, card_mode)', 'AS alert_json'):
            self.assertIn(needle, script)
        self.assertEqual('2026-09-21 13:40:00+08:00', sql.instant('2026-09-21T13:40'))
        self.assertEqual('2026-09-21 13:40:00+00:00', sql.civil('2026-09-21T13:40'))


@unittest.skipUnless(FASTAPI, 'FastAPI is not installed; run in the image')
class Http(unittest.TestCase):
    def setUp(self):
        from src.api import hosted
        runtime = hosted.demo_runtime({})
        svc, self.bq, self.mail = service(PEDC, polls=1)
        self.service = svc
        users = GoogleUsers(lambda token: {'uid': 'u', 'email': USER['email'], 'email_verified': True,
                                           'firebase': {'sign_in_provider': 'google.com'}} if token == 'good' else {})
        runtime.alerts = hosted.AlertsWiring(svc, users, SchedulerAuth(), {'apiKey': 'k', 'authDomain': 'd', 'projectId': 'p'})
        self.client = TestClient(runtime.application())
        self.auth = {'Authorization': 'Bearer good'}

    def test_signed_out_reads_but_cannot_write(self):
        r = self.client.get('/api/alerts/config')
        self.assertEqual(200, r.status_code)
        self.assertFalse(r.json()['signed_in'])
        self.assertEqual('no-store', r.headers['cache-control'])
        self.assertEqual(401, self.client.put('/api/alerts/rules', json=rules()).status_code)
        self.assertEqual(401, self.client.post('/api/alerts/run', json={}).status_code)
        self.assertEqual(401, self.client.post('/api/alerts/scheduled', json={}).status_code)

    def test_save_run_poll_and_history(self):
        self.assertEqual({'version': 1}, self.client.put('/api/alerts/rules', json=rules(), headers=self.auth).json())
        bad = self.client.put('/api/alerts/portfolio', json=portfolio(benchmark_php_mwh='x'), headers=self.auth)
        self.assertEqual((422, 'benchmark_php_mwh'), (bad.status_code, bad.json()['field']))
        self.assertEqual('benchmark_php_mwh: a number', bad.json()['message'])
        self.assertEqual('Sign in to do this.', self.client.put('/api/alerts/rules', json=rules()).json()['message'])
        run = self.client.post('/api/alerts/run', json={'region': 'CVIS', 'interval_manila': '2026-09-21T13:40'},
                               headers=self.auth)
        self.assertEqual(202, run.status_code)
        done = self.client.get('/api/alerts/runs/' + run.json()['id'], headers=self.auth).json()
        self.assertEqual('done', done['status'])
        self.assertEqual(1, len(self.client.get('/api/alerts/history').json()['alerts']))
        self.assertEqual(404, self.client.get('/api/alerts/runs/' + 'f' * 32, headers=self.auth).status_code)

    def test_pages_carry_the_sign_in_policy_and_the_api_keeps_the_default(self):
        # ericka-desk D1: every page carries the sign-in policy; API answers keep the default.
        from src.api import CONTENT_SECURITY_POLICY, SIGN_IN_POLICY
        page = self.client.get('/alerts')
        self.assertEqual(200, page.status_code)
        self.assertEqual(SIGN_IN_POLICY, page.headers['content-security-policy'])
        self.assertEqual('no-cache', page.headers['cache-control'])
        self.assertEqual(CONTENT_SECURITY_POLICY, self.client.get('/api/alerts/config').headers['content-security-policy'])
        self.assertEqual(SIGN_IN_POLICY, self.client.get('/').headers['content-security-policy'])

    def test_the_import_draft_route(self):
        off = self.client.get('/api/alerts/portfolio/draft', headers=self.auth)
        self.assertEqual((404, 'IMPORT_OFF', 'no-store'), (off.status_code, off.json()['code'], off.headers['cache-control']))
        self.assertEqual(401, self.client.get('/api/alerts/portfolio/draft').status_code)
        self.service.draft = FakeDraft()
        self.assertEqual(401, self.client.get('/api/alerts/portfolio/draft').status_code)
        on = self.client.get('/api/alerts/portfolio/draft', headers=self.auth)
        self.assertEqual((200, 'no-store'), (on.status_code, on.headers['cache-control']))
        self.assertEqual(DRAFT['regions'], on.json()['regions'])
        self.service.draft = FakeDraft(draft=None)
        self.assertEqual('NO_DRAFT', self.client.get('/api/alerts/portfolio/draft', headers=self.auth).json()['code'])
        self.service.draft = FakeDraft(fail=True)
        self.assertEqual(503, self.client.get('/api/alerts/portfolio/draft', headers=self.auth).status_code)

    def test_client_config_and_demo_mode(self):
        self.assertEqual('k', self.client.get('/api/alerts/client-config').json()['apiKey'])
        from src.api import hosted
        demo = TestClient(hosted.demo_runtime({}).application())
        self.assertEqual(503, demo.get('/api/alerts/client-config').status_code)
        self.assertFalse(demo.get('/api/alerts/config').json()['checks_available'])


if __name__ == '__main__':
    unittest.main()
