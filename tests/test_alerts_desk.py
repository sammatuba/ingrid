"""ericka-desk slice 9 (E21 to E25): per-region levels, the replay's alerts, the inbox (alert assignment was removed: no assignee anywhere).

Every price, event and address here is SYNTHETIC (made up for the test, example.invalid); nothing is
read from the real bake, except one link check (RealBakeLinks) that runs only when a real bake is
present (GRID_DATA_DIR, else build/grid-data) and is skipped otherwise. Offline: an in-memory store, no BigQuery, no SMTP. The HTTP checks need
FastAPI and are skipped without it.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.alerts import model, replay
from src.alerts.auth import GoogleUsers, SchedulerAuth
from src.alerts.service import AlertService, UnknownAlert, group_alerts, inbox_order
from src.alerts.store import MemoryAlertStore

try:
    from fastapi.testclient import TestClient
    FASTAPI = True
except ImportError:
    FASTAPI = False

USER = {'uid': 'u-1', 'email': 'analyst@example.invalid'}
OTHER = {'uid': 'u-2', 'email': 'risk@example.invalid'}
DAY1 = '2026-09-21'


def synthetic_bake(directory, days=3, spikes=(), events=(), notices=()):
    """A SYNTHETIC replay: every region at 5,000 PHP/MWh all day, every 5 minutes, for `days` days.

    spikes: (region, 'YYYY-MM-DDTHH:MM', price) overrides. events: (id, region, event_at, last_t).
    notices: (id, region, 'YYYY-MM-DDTHH:MM:SS', kind, text) written to advisories.json.
    """
    start = datetime.fromisoformat(DAY1 + 'T00:00')
    times = [(start + timedelta(minutes=5 * i)).strftime('%Y-%m-%dT%H:%M') for i in range(days * 288)]
    grids = {code: {'lmp_median': [5000] * len(times), 'demand_mw': [1000] * len(times),
                    'dr_short_mw': [0] * len(times), 'curtailed_mw': [0] * len(times)} for code in model.REGIONS}
    for code, t, price in spikes:
        grids[code]['lmp_median'][times.index(t)] = price
    directory = Path(directory)
    (directory / 'regions.json').write_text(json.dumps({'synthetic': True, 't': times, 'grids': grids}))
    (directory / 'events').mkdir(exist_ok=True)
    index = []
    for eid, code, at, last in events:
        index.append({'id': eid, 't': at, 'advisory': 'SYN-1', 'title': 'Synthetic unit trip ' + eid})
        (directory / 'events' / f'{eid}.json').write_text(json.dumps({
            'synthetic': True, 'id': eid, 'title': 'Synthetic unit trip ' + eid, 'grid': code, 'event_at': at,
            'advisory': {'id': 'SYN-1', 't': at, 'text': 'synthetic notice'},
            'timeline': [{'t': at, 'kind': 'notice', 'text': 'synthetic'}, {'t': last, 'kind': 'restored', 'text': 'synthetic'}]}))
    (directory / 'events.json').write_text(json.dumps(index))
    (directory / 'advisories.json').write_text(json.dumps(
        [{'id': i, 'grid': g, 't': t, 'kind': k, 'text': x} for i, g, t, k, x in notices]))
    return times


def rules(**over):
    body = {'enabled': True, 'threshold': {'mode': 'absolute', 'value': 15000}, 'regions': ['CLUZ', 'CVIS', 'CMIN'],
            'min_severity': 'high', 'recipients': []}
    body.update(over)
    return body


def portfolio():
    return {'effective_from': '2026-09-01', 'note': 'synthetic test portfolio', 'benchmark_php_mwh': 6000,
            'regions': {'CVIS': {'demand_mw_by_hour': [50] * 24}}, 'contracts': [], 'nodes': []}


class Levels(unittest.TestCase):
    def test_per_region_levels_are_validated_and_stored(self):
        out = model.validate_rules(rules(levels={
            'CVIS': {'spike': {'mode': 'absolute', 'value': 20000}, 'collapse': {'mode': 'absolute', 'value': 0}},
            'CMIN': {'spike': {'mode': 'ratio_to_baseline', 'value': 3}, 'collapse': None}}))
        self.assertEqual({'mode': 'absolute', 'value': 20000}, out['levels']['CVIS']['spike'])
        self.assertEqual({'spike': {'mode': 'absolute', 'value': 15000}, 'collapse': None}, model.levels_for(out, 'CLUZ'))
        self.assertEqual('collapse', model.crossing(model.levels_for(out, 'CVIS'), -5, None))
        self.assertIsNone(model.crossing(model.levels_for(out, 'CVIS'), 18000, None))
        self.assertEqual('spike', model.crossing(model.levels_for(out, 'CLUZ'), 18000, None))

    def test_bad_levels_are_refused_with_the_field(self):
        cases = [({'XX': {'spike': None, 'collapse': None}}, 'levels'),
                 ({'CVIS': {'spike': {'mode': 'ratio_to_baseline', 'value': 0.5}, 'collapse': None}}, 'levels.CVIS.spike.value'),
                 ({'CVIS': {'spike': None, 'collapse': {'mode': 'ratio_to_baseline', 'value': 2}}}, 'levels.CVIS.collapse.value'),
                 ({'CVIS': {'spike': None, 'collapse': {'mode': 'absolute', 'value': 20000}}}, 'levels.CVIS.collapse.value'),
                 ({'CVIS': {'spike': {'mode': 'peso', 'value': 1}, 'collapse': None}}, 'levels.CVIS.spike.mode'),
                 ({'CVIS': {'spike': None, 'collapse': None, 'other': 1}}, 'levels.CVIS')]
        for levels, field in cases:
            with self.subTest(field=field), self.assertRaises(model.InvalidInput) as caught:
                model.validate_rules(rules(levels=levels))
            self.assertEqual(field, caught.exception.field)

    def test_a_rule_set_without_levels_reads_as_before(self):
        old = model.validate_rules(rules())
        self.assertNotIn('levels', old)
        self.assertEqual({'spike': old['threshold'], 'collapse': None}, model.levels_for(old, 'CVIS'))


class Usual(unittest.TestCase):
    def test_usual_comes_from_earlier_days_only(self):
        times = ['2026-09-21T10:00', '2026-09-21T10:05', '2026-09-22T10:00', '2026-09-23T10:00', '2026-09-23T11:00']
        prices = [100, 300, 9999, 500, 700]
        table = replay.usual_table(times, prices)
        self.assertEqual((None, 0), table[0])  # day 1: no earlier day
        self.assertEqual((None, 0), table[1])  # not even its own day's earlier interval
        self.assertEqual((200, 1), table[2])   # day 2 sees day 1 only, never its own 9,999
        self.assertEqual((300, 2), table[3])   # median of 100, 300, 9999
        self.assertEqual((None, 0), table[4])  # no earlier day had hour 11

    def test_a_ratio_level_cannot_fire_on_day_one(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_bake(d, spikes=[('CVIS', DAY1 + 'T10:00', 30000), ('CVIS', '2026-09-22T10:00', 30000)])
            ratio = rules(levels={'CVIS': {'spike': {'mode': 'ratio_to_baseline', 'value': 3}, 'collapse': None}},
                          regions=['CVIS'])
            alerts = replay.Replay(d).alerts(ratio)
        self.assertEqual(['2026-09-22T10:00'], [a['first'] for a in alerts])
        self.assertEqual(5000, alerts[0]['usual_php_mwh'])


class ReplayAlerts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        synthetic_bake(self.tmp.name, spikes=[
            ('CVIS', '2026-09-22T13:40', 32000), ('CVIS', '2026-09-22T13:45', 20000),
            ('CVIS', '2026-09-22T15:00', 18000),
            ('CLUZ', '2026-09-22T09:00', 16000), ('CMIN', '2026-09-23T03:00', -10000)],
            events=[('syn-trip', 'CVIS', '2026-09-22T13:35', '2026-09-22T16:00')])
        self.replay = replay.Replay(self.tmp.name)
        self.rules = rules(levels={code: {'spike': None, 'collapse': {'mode': 'absolute', 'value': 0}} for code in model.REGIONS})

    def test_runs_of_crossings_are_one_alert_and_respect_the_clock(self):
        alerts = self.replay.alerts(self.rules)
        self.assertEqual(4, len(alerts))
        first = next(a for a in alerts if a['first'] == '2026-09-22T13:40')
        self.assertEqual((2, 32000, 'extreme'), (first['intervals'], first['price_php_mwh'], first['severity']))
        collapse = next(a for a in alerts if a['direction'] == 'collapse')
        self.assertEqual(('CMIN', 'high'), (collapse['region'], collapse['severity']))
        early = self.replay.alerts(self.rules, '2026-09-22T13:40')
        self.assertEqual(['2026-09-22T13:40', '2026-09-22T09:00'], [a['first'] for a in early])
        self.assertEqual('2026-09-22T13:40', early[0]['last'])  # the 13:45 interval is past the clock

    def test_the_cause_is_a_recorded_event_known_by_the_clock_or_none(self):
        alerts = {a['first']: a for a in self.replay.alerts(self.rules)}
        self.assertEqual('syn-trip', alerts['2026-09-22T13:40']['cause']['id'])
        self.assertEqual('/event/syn-trip', alerts['2026-09-22T15:00']['href'])
        self.assertIsNone(alerts['2026-09-22T09:00']['cause'])
        self.assertTrue(alerts['2026-09-22T09:00']['main_driver'].startswith('None on record'))
        before = self.replay.alerts(self.rules, '2026-09-22T13:34')
        self.assertTrue(all(a['cause'] is None for a in before))

    def test_no_technology_or_fuel_words(self):
        text = json.dumps(self.replay.alerts(self.rules)).lower()
        for word in ('coal', 'hydro', 'solar', 'geothermal', 'diesel', 'natural gas', 'fuel'):
            self.assertNotIn(word, text)


class Inbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        synthetic_bake(self.tmp.name, spikes=[
            ('CVIS', '2026-09-22T13:40', 32000), ('CVIS', '2026-09-22T15:00', 18000),
            ('CLUZ', '2026-09-22T09:00', 16000), ('CMIN', '2026-09-23T03:00', -10000),
            ('CLUZ', '2026-09-23T20:00', 15500), ('CLUZ', '2026-09-23T05:00', 0)],
            events=[('syn-trip', 'CVIS', '2026-09-22T13:35', '2026-09-22T16:00')])
        self.store = MemoryAlertStore()
        self.svc = AlertService(self.store, replay=replay.Replay(self.tmp.name), clock=lambda: '2026-10-18T00:00:00Z')

    def keys(self, out):
        return [a['first'] for g in out['groups'] for a in g['alerts']]

    def test_ordered_by_severity_then_impact_and_grouped_by_cause(self):
        out = self.svc.inbox(USER)
        self.assertTrue(out['default_levels'])
        severities = [g['severity'] for g in out['groups']]
        self.assertEqual(sorted(severities, key=lambda s: -model.severity_rank(s)), severities)
        trip = next(g for g in out['groups'] if g['cause'])
        self.assertEqual(('event:syn-trip', 2), (trip['id'], len(trip['alerts'])))
        self.assertEqual(['2026-09-22T13:40', '2026-09-22T15:00'], [a['first'] for a in trip['alerts']])
        self.assertEqual(5, len(out['groups']))
        self.assertTrue(all(g['next_step'] for g in out['groups']))

    def test_impact_breaks_ties_and_a_figure_comes_before_none(self):
        a = [{'key': 'a', 'severity': 'high', 'financial_impact': {'status': 'Needs your portfolio'}, 'last': '2026-09-22T10:00'},
             {'key': 'b', 'severity': 'high', 'financial_impact': {'php': -900.0}, 'last': '2026-09-21T10:00'},
             {'key': 'c', 'severity': 'high', 'financial_impact': {'php': 100.0}, 'last': '2026-09-23T10:00'},
             {'key': 'd', 'severity': 'extreme', 'financial_impact': {'status': 'Needs your portfolio'}, 'last': '2026-09-20T10:00'},
             {'key': 'e', 'severity': 'high', 'financial_impact': {'status': 'Needs your portfolio'}, 'last': '2026-09-23T10:00'}]
        self.assertEqual(['d', 'b', 'c', 'e', 'a'], [x['key'] for x in sorted(a, key=inbox_order)])

    def test_no_peso_without_a_portfolio(self):
        out = self.svc.inbox(USER)
        for g in out['groups']:
            self.assertEqual({'status': 'Needs your portfolio'}, g['financial_impact'])
            for a in g['alerts']:
                self.assertNotIn('php', a['financial_impact'])

    def test_peso_from_the_portfolio_summed_and_hidden_when_signed_out(self):
        self.store.add_version('portfolio', dict(model.validate_portfolio(portfolio()), saved_by=USER['email']))
        out = self.svc.inbox(USER)
        trip = next(g for g in out['groups'] if g['cause'])
        lead = trip['alerts'][0]
        # 50 MW unhedged x (32,000 - 6,000) x 5/60 h
        self.assertAlmostEqual(50 * 26000 * 5 / 60, lead['financial_impact']['php'], places=2)
        self.assertIn('php', trip['financial_impact'])
        luzon = next(g for g in out['groups'] if g['regions'] == ['CLUZ'])
        self.assertNotIn('php', luzon['financial_impact'])  # the portfolio has no Luzon demand
        anon = self.svc.inbox(None)
        trip = next(g for g in anon['groups'] if g['cause'])
        self.assertEqual({'hidden': True}, trip['financial_impact'])
        self.assertEqual({'hidden': True}, trip['alerts'][0]['financial_impact'])

    def test_filters_all_and_high_only(self):
        everything = self.keys(self.svc.inbox(USER, view='all'))
        high = self.svc.inbox(USER, view='high')
        self.assertTrue(all(model.severity_rank(a['severity']) >= 2 for g in high['groups'] for a in g['alerts']))
        self.assertLess(len(self.keys(high)), len(everything))
        for view in ('mine', 'unread'):
            with self.assertRaises(model.InvalidInput):
                self.svc.inbox(USER, view=view)

    def test_the_clock_filters_the_inbox(self):
        self.assertEqual(['2026-09-22T09:00'], self.keys(self.svc.inbox(USER, at='2026-09-22T12:00')))
        self.assertEqual([], self.keys(self.svc.inbox(USER, at='2026-09-21T23:55')))
        with self.assertRaises(model.InvalidInput):
            self.svc.inbox(USER, at='tomorrow')

    def test_no_alert_carries_an_assignee(self):
        # Alert assignment is gone: no assignee field signed in or not, and no assign method.
        for user in (USER, None):
            alerts = [a for g in self.svc.inbox(user)['groups'] for a in g['alerts']]
            self.assertTrue(alerts)
            self.assertFalse(any('assignee' in a for a in alerts))
        self.assertFalse(hasattr(self.svc, 'assign'))
        self.assertFalse(hasattr(self.store, 'assignments') or hasattr(self.store, 'set_assignment'))

    def test_saved_levels_drive_the_inbox(self):
        self.store.add_version('rules', dict(model.validate_rules(rules(levels={
            'CVIS': {'spike': {'mode': 'absolute', 'value': 30000}, 'collapse': None}})), saved_by=USER['email']))
        out = self.svc.inbox(USER)
        self.assertFalse(out['default_levels'])
        firsts = self.keys(out)
        self.assertNotIn('2026-09-22T15:00', firsts)  # 18,000 is under Visayas's own 30,000
        self.assertIn('2026-09-22T09:00', firsts)  # Luzon keeps the shared 15,000
        self.assertNotIn('2026-09-23T03:00', firsts)  # no collapse level saved for Mindanao

    def test_groups_keep_alerts_without_a_cause_apart(self):
        alerts = [{'key': 'x', 'region': 'CVIS', 'region_label': 'Visayas', 'interval_manila': 't', 'severity': 'high',
                   'cause': None, 'financial_impact': {}, 'next_step': 's'},
                  {'key': 'y', 'region': 'CVIS', 'region_label': 'Visayas', 'interval_manila': 't', 'severity': 'high',
                   'cause': None, 'financial_impact': {}, 'next_step': 's'}]
        self.assertEqual(2, len(group_alerts(alerts)))


class AlertPage(unittest.TestCase):
    """ericka-desk: an alert with no recorded event has its own page, built from the bake on request."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        synthetic_bake(self.tmp.name, spikes=[
            ('CVIS', '2026-09-22T13:40', 32000), ('CVIS', '2026-09-22T13:45', 20000),
            ('CLUZ', '2026-09-22T09:00', 16000), ('CLUZ', '2026-09-22T20:00', 16000)],
            events=[('syn-trip', 'CVIS', '2026-09-22T13:35', '2026-09-22T16:00')],
            notices=[('N-IN', 'CLUZ', '2026-09-22T08:30:10', 'trip', 'SYNTHETIC Unit 1 tripped at 0829H'),
                     ('N-AFTER', 'CLUZ', '2026-09-22T09:40:00', 'notice', 'SYNTHETIC later notice'),
                     ('N-EARLY', 'CLUZ', '2026-09-22T06:00:00', 'notice', 'SYNTHETIC too early'),
                     ('N-LATE', 'CLUZ', '2026-09-22T11:30:00', 'notice', 'SYNTHETIC too late'),
                     ('N-OTHER', 'CVIS', '2026-09-22T08:45:00', 'notice', 'SYNTHETIC other region')])
        self.replay = replay.Replay(self.tmp.name)
        self.svc = AlertService(MemoryAlertStore(), replay=self.replay)
        alerts = self.replay.alerts(replay.DEFAULT_RULES)
        self.lone = next(a for a in alerts if a['first'] == '2026-09-22T09:00')
        self.caused = next(a for a in alerts if a['first'] == '2026-09-22T13:40')
        self.late = next(a for a in alerts if a['first'] == '2026-09-22T20:00')

    def test_an_alert_without_an_event_links_its_own_page(self):
        # `/alert/<key>` for an alert no recorded event explains; `/event/` is for recorded events only
        self.assertEqual('/alert/' + self.lone['key'], self.lone['href'])
        self.assertRegex(self.lone['key'], r'^[0-9a-f]{24}$')
        self.assertIsNone(self.lone['cause'])
        self.assertEqual('/event/syn-trip', self.caused['href'], 'a recorded event keeps its baked page')
        self.assertEqual('/event/syn-trip', self.caused['cause']['href'])

    def test_a_valid_key_answers_the_alert_its_series_and_the_region_notices(self):
        out = self.svc.alert(None, self.lone['key'], '2026-09-22T10:00')
        self.assertEqual('ok', out['status'])
        a, w = out['alert'], out['around']
        self.assertEqual((self.lone['key'], 'CLUZ', 16000), (a['key'], a['region'], a['price_php_mwh']))
        self.assertIn('next_step', a)
        self.assertNotIn('points', a)
        self.assertEqual(('2026-09-22T07:00', '2026-09-22T10:00'), (w['from'], w['to']))
        self.assertEqual(w['t'][0], '2026-09-22T07:00')
        self.assertEqual(w['t'][-1], '2026-09-22T10:00')
        n = len(w['t'])
        for name in ('price', 'usual', 'level', 'reserve_short_mw', 'curtailed_mw', 'demand_mw'):
            self.assertEqual(n, len(w[name]), name)
        self.assertEqual(16000, w['price'][w['t'].index('2026-09-22T09:00')])
        self.assertEqual(15000, w['level'][0])
        self.assertEqual(5000, w['usual'][0], 'usual from the earlier day only')
        # the region's notices in the window, nothing from another region or outside it
        self.assertEqual(['N-IN', 'N-AFTER'], [x['id'] for x in w['notices']])
        self.assertEqual('2026-09-22T08:30', w['notices'][0]['t'])

    def test_nothing_after_the_clock(self):
        out = self.svc.alert(None, self.lone['key'], '2026-09-22T09:20')
        w = out['around']
        self.assertEqual('2026-09-22T09:20', w['to'])
        self.assertTrue(all(t <= '2026-09-22T09:20' for t in w['t']))
        self.assertEqual(['N-IN'], [x['id'] for x in w['notices']], 'the 09:40 notice is after the clock')
        self.assertNotIn('09:40', json.dumps(out))

    def test_an_alert_after_the_clock_says_so_with_its_start_only(self):
        out = self.svc.alert(None, self.late['key'], '2026-09-22T10:00')
        self.assertEqual({'status': 'after_clock', 'at': '2026-09-22T10:00', 'key': self.late['key'], 'region': 'CLUZ',
                          'region_label': 'Luzon', 'direction': 'spike', 'first': '2026-09-22T20:00'}, out)

    def test_unknown_and_bad_keys_and_a_bad_clock(self):
        with self.assertRaises(UnknownAlert):
            self.svc.alert(None, '0' * 24)
        for bad in ('x', 'A' * 24, '0' * 23, None, '../' + '0' * 21):
            with self.assertRaises(UnknownAlert):
                self.svc.alert(None, bad)
        with self.assertRaises(model.InvalidInput):
            self.svc.alert(None, self.lone['key'], '2026-09-22 10:00')
        with self.assertRaises(UnknownAlert):
            AlertService(MemoryAlertStore()).alert(None, self.lone['key'])

    def test_a_key_of_other_saved_levels_is_unknown(self):
        store = MemoryAlertStore()
        svc = AlertService(store, replay=self.replay)
        svc.save_rules(USER, rules(threshold={'mode': 'absolute', 'value': 31000}))
        with self.assertRaises(UnknownAlert):
            svc.alert(None, self.lone['key'])


class EmailDriver(unittest.TestCase):
    def test_each_email_names_the_main_driver_from_records(self):
        base = {'region': 'CVIS', 'interval_manila': '2026-09-21T13:40', 'price_php_mwh': 20000, 'severity': 'high',
                'threshold_text': 't', 'financial_impact': {'status': model.NO_PORTFOLIO}, 'event_url': 'https://x'}
        _, text, _ = model.email_message(dict(base, likely_drivers=[{'family': 'S', 'family_label': 'Supply', 'score': 0.7, 'why': 'reserve short'}]))
        self.assertIn('Main driver: Supply (reserve short)', text)
        _, text, _ = model.email_message(dict(base, likely_drivers=[]))
        self.assertIn('Main driver: None on record', text)


@unittest.skipUnless(FASTAPI, 'needs FastAPI (run in the image)')
class Http(unittest.TestCase):
    def setUp(self):
        from src.api import hosted
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        synthetic_bake(self.tmp.name, spikes=[('CVIS', '2026-09-22T13:40', 32000)])
        runtime = hosted.demo_runtime({})
        svc = AlertService(MemoryAlertStore(), replay=replay.Replay(self.tmp.name))
        users = GoogleUsers(lambda token: {'uid': 'u', 'email': USER['email'], 'email_verified': True,
                                           'firebase': {'sign_in_provider': 'google.com'}} if token == 'good' else {})
        runtime.alerts = hosted.AlertsWiring(svc, users, SchedulerAuth(), None)
        self.client = TestClient(runtime.application())
        self.auth = {'Authorization': 'Bearer good'}

    def test_inbox_is_public_and_has_no_assigning(self):
        r = self.client.get('/api/alerts/inbox?at=2026-09-23T00:00')
        self.assertEqual((200, 'no-store'), (r.status_code, r.headers['cache-control']))
        key = r.json()['groups'][0]['alerts'][0]['key']
        self.assertEqual(422, self.client.get('/api/alerts/inbox?at=x').status_code)
        self.assertEqual(422, self.client.get('/api/alerts/inbox?view=mine', headers=self.auth).status_code)
        signed = self.client.get('/api/alerts/inbox?at=2026-09-23T00:00', headers=self.auth).json()
        self.assertNotIn('assignee', json.dumps(signed))
        self.assertNotIn('assignee', r.text)
        for headers in ({}, self.auth):
            self.assertIn(self.client.put('/api/alerts/assign/' + key, json={'assignee': 'me'}, headers=headers).status_code,
                          (404, 405))

    def test_one_alert_is_public_no_store_and_validated(self):
        inbox = self.client.get('/api/alerts/inbox?at=2026-09-23T00:00').json()
        key = inbox['groups'][0]['alerts'][0]['key']
        r = self.client.get(f'/api/alerts/alert/{key}?at=2026-09-23T00:00')
        self.assertEqual((200, 'no-store', 'ok'), (r.status_code, r.headers['cache-control'], r.json()['status']))
        self.assertEqual(key, r.json()['alert']['key'])
        self.assertEqual('after_clock', self.client.get(f'/api/alerts/alert/{key}?at=2026-09-21T00:00').json()['status'])
        self.assertEqual(404, self.client.get('/api/alerts/alert/' + '0' * 24).status_code)
        self.assertEqual(404, self.client.get('/api/alerts/alert/not-a-key').status_code)
        self.assertEqual(422, self.client.get(f'/api/alerts/alert/{key}?at=x').status_code)


class RealBakeLinks(unittest.TestCase):
    """ericka-desk: on the real bake, the PEDC alert keeps its recorded event's page and every other
    alert opens its own page at `/alert/<key>`. Skipped when no real bake is present."""

    def test_the_pedc_alert_links_its_event_and_the_rest_their_own_pages(self):
        bake = Path((os.environ.get('GRID_DATA_DIR') or '').strip() or ROOT / 'build' / 'grid-data')
        if not (bake / 'events' / 'pedc-u2-2026-09-21.json').is_file():
            self.skipTest('no real bake with the PEDC event (GRID_DATA_DIR or build/grid-data)')
        r = replay.Replay(str(bake))
        # DATA-4: the clock is the event's own end (its last timeline entry, from the event file),
        # not the bake's last interval: on the year bake the newest MAX_ALERTS alerts at the last
        # interval reach back only to 26 Sep, and the PEDC alert ranks below them.
        event = next(e for e in r.data()['events'] if e['id'] == 'pedc-u2-2026-09-21')
        at = event['end']
        for clock in (at, None):
            alerts = r.alerts(replay.DEFAULT_RULES, clock)
            for a in alerts:
                if a['cause'] and a['cause']['id'] == 'pedc-u2-2026-09-21':
                    self.assertEqual('/event/pedc-u2-2026-09-21', a['href'])
                if not a['cause']:
                    self.assertEqual('/alert/' + a['key'], a['href'])
            if clock == at:
                pedc = [a for a in alerts if a['cause'] and a['cause']['id'] == 'pedc-u2-2026-09-21']
                self.assertTrue(pedc, 'the PEDC alert is in the replay')
        # DATA-4: looked up over the whole bake (its own page's path), it keeps its event's page.
        for a in pedc:
            found = r.find(replay.DEFAULT_RULES, a['key'])
            self.assertEqual('pedc-u2-2026-09-21', found['cause']['id'])
            self.assertEqual('/event/pedc-u2-2026-09-21', found['href'])


def reference_usual(times, prices):
    """The usual rule as first written (statistics.median over every earlier day, per interval)."""
    import statistics
    out = {}
    for i, t in enumerate(times):
        vals = [prices[k] for k, u in enumerate(times) if u[:10] < t[:10] and u[11:13] == t[11:13] and prices[k] is not None]
        days = {u[:10] for k, u in enumerate(times) if u[:10] < t[:10] and u[11:13] == t[11:13] and prices[k] is not None}
        out[i] = (statistics.median(vals), len(days)) if vals else (None, 0)
    return out


def reference_alerts(r, rules_, at=None):
    """The replay's alerts as first written: one scan from the first interval to the clock, every
    episode built, sorted, the newest MAX_ALERTS kept (the replay-year cache must equal it)."""
    d = r.data()
    times = d['t']
    at = at or times[-1]
    last = max((i for i, t in enumerate(times) if t <= at), default=-1)
    out = []
    for code in sorted(rules_.get('regions') or model.REGIONS):
        series = d['regions'].get(code)
        if series is None:
            continue
        levels = model.levels_for(rules_, code)
        current = None
        for i in range(last + 1):
            price = series['price'][i]
            usual, days = series['usual'].get(i, (None, 0))
            direction = model.crossing(levels, price, usual, days >= 1)
            if direction is None:
                continue
            t = times[i]
            if current and current['direction'] == direction and replay._minutes(t) - replay._minutes(current['last']) <= replay.GAP_MINUTES:
                current['points'].append((i, t, price, usual))
                current['last'] = t
                continue
            current = {'region': code, 'direction': direction, 'first': t, 'last': t, 'points': [(i, t, price, usual)]}
            out.append(current)
    alerts = [r._alert(e, rules_, d, at) for e in out]
    alerts.sort(key=lambda a: (a['last'], a['key']), reverse=True)
    return alerts[:replay.MAX_ALERTS]


class ReplayYear(unittest.TestCase):
    """replay-year: the replay over a year of days. The episodes are found once per levels and cut
    at the clock; the answers equal the first scan's exactly (SYNTHETIC bakes only)."""

    def bake(self, days, spikes):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        synthetic_bake(tmp.name, days=days, spikes=spikes,
                       events=[('syn-a', 'CVIS', '2026-09-22T13:35', '2026-09-22T16:00')])
        return replay.Replay(tmp.name)

    def test_the_sorted_usual_equals_statistics_median(self):
        import random
        rnd = random.Random(7)
        start = datetime.fromisoformat('2026-01-01T00:00')
        times = [(start + timedelta(minutes=5 * i)).strftime('%Y-%m-%dT%H:%M') for i in range(6 * 288)]
        prices = [None if rnd.random() < 0.05 else rnd.choice([rnd.randint(-500, 32000), rnd.uniform(0, 9000)]) for _ in times]
        self.assertEqual(reference_usual(times, prices), replay.usual_table(times, prices))

    def test_the_cut_equals_one_scan_at_every_clock(self):
        import random
        rnd = random.Random(11)
        spikes = []
        for day in range(12):
            for _ in range(6):
                t = (datetime.fromisoformat(DAY1 + 'T00:00') + timedelta(days=day, minutes=5 * rnd.randrange(288)))
                for k in range(rnd.randint(1, 4)):  # runs, some with a quiet interval inside
                    if rnd.random() < 0.8:
                        spikes.append((rnd.choice(sorted(model.REGIONS)), (t + timedelta(minutes=5 * k)).strftime('%Y-%m-%dT%H:%M'),
                                       rnd.choice([16000, 32000, -100, 25000])))
        r = self.bake(12, spikes)
        absolute = rules(levels={code: {'spike': None, 'collapse': {'mode': 'absolute', 'value': 0}} for code in model.REGIONS})
        ratio = rules(levels={'CVIS': {'spike': {'mode': 'ratio_to_baseline', 'value': 2}, 'collapse': None}})
        times = r.data()['t']
        clocks = [None, times[0], times[300], '2026-09-22T13:40', '2026-09-22T13:37', times[len(times) // 2], times[-2]]
        clocks += [s[1] for s in spikes[::9]]  # clocks that land inside a run
        for rules_ in (absolute, ratio, replay.DEFAULT_RULES):
            for at in clocks:
                self.assertEqual(reference_alerts(r, rules_, at), r.alerts(rules_, at), (rules_.get('levels'), at))

    def test_keys_and_find_cover_alerts_older_than_the_newest_shown(self):
        spikes = [('CVIS', (datetime.fromisoformat(DAY1 + 'T00:00') + timedelta(minutes=30 * i)).strftime('%Y-%m-%dT%H:%M'), 32000)
                  for i in range(7 * 48)] + [('CLUZ', '2026-09-26T10:00', 32000)]
        r = self.bake(7, spikes)
        absolute = rules()
        shown = r.alerts(absolute)
        self.assertEqual(replay.MAX_ALERTS, len(shown))
        keys = r.keys(absolute)
        self.assertEqual(7 * 48 + 1, len(keys))
        self.assertTrue({a['key'] for a in shown} <= keys)
        oldest = model.alert_key('CVIS', DAY1 + 'T00:00', 'replay-spike')
        self.assertIn(oldest, keys)
        self.assertNotIn(oldest, {a['key'] for a in shown})
        found = r.find(absolute, oldest)
        self.assertEqual((DAY1 + 'T00:00', 'CVIS'), (found['first'], found['region']))
        self.assertIsNone(r.find(absolute, '0' * 24))

    def test_a_year_answers_quickly(self):
        import time
        spikes = [('CVIS', (datetime.fromisoformat(DAY1 + 'T00:00') + timedelta(days=d, hours=13)).strftime('%Y-%m-%dT%H:%M'), 32000)
                  for d in range(0, 365, 3)]
        r = self.bake(365, spikes)
        began = time.perf_counter()
        r.data()
        loaded = time.perf_counter() - began
        began = time.perf_counter()
        for at in (None, '2026-12-01T13:00', '2027-03-01T00:00', '2027-09-01T13:05', None):
            r.alerts(rules(), at)
        answered = time.perf_counter() - began
        self.assertLess(loaded, 30, 'loading a year of replay')
        self.assertLess(answered, 2.5, 'five inbox answers over a year')


if __name__ == '__main__':
    unittest.main()
