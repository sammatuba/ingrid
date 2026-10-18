"""The alerts service: configuration, saves, checks, emails and history, independent of HTTP.

A check is a *run*. Starting one tests the threshold synchronously (a small query) and starts one
live driver card per crossing (a BigQuery script of about 40 s); the run is then advanced by polling,
because Firebase Hosting ends a proxied request at 60 s. Each poll reads the card jobs that finished,
records their alerts (idempotent by alert key) and emails the matching recipients once each.

The scheduled check finds intervals newer than the last one it checked in `grid_curated.labels`,
groups each region's crossings into one parent event (its highest-price interval is carded, the
count and window are stated), caps the cards per run, and finishes pending runs first.
"""
import json
import re
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import Lock

from . import model, sql
from . import replay as replay_mod
from .bigquery import QueryFailed, parameter
from .mail import MailUnavailable

FAMILY_LABELS = {'D': 'Demand', 'S': 'Supply', 'P': 'Price', 'O': 'Outage', 'F': 'Fuel', 'Rules': 'Rules'}
CARD_MODE = 'assumed'
MAX_CARDS_PER_RUN = 3
MAX_BYTES_SMALL = 200_000_000
MAX_BYTES_CARD = 2_000_000_000
SCHEDULED_WINDOW = timedelta(hours=24)
FIRST_WINDOW = timedelta(hours=1)
HIDDEN = {'hidden': True}
EXPLAIN_CACHE = 256  # alerts whose explanation is kept in memory


class NoRules(Exception):
    """A check was asked for before any notification settings were saved (409)."""


class ImportOff(Exception):
    """The portfolio import is switched off (NOWCAST_PORTFOLIO_IMPORT is not `on`)."""


class NoDraft(Exception):
    """The import is on but no draft has been uploaded yet."""


class ChecksUnavailable(Exception):
    """No BigQuery in this mode (demo), or BigQuery refused (503); `reason` says which."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _why(row):
    name = (row.get('indicator') or '').replace('_', ' ')
    value, base = row.get('value_at_t'), row.get('baseline_median')
    fmt = (lambda v: f'{v:.3f}') if row.get('indicator') == 'import_share' else (lambda v: f'{v:,.0f}')
    if value is None:
        return name
    return f'{name} {fmt(value)}' + (f' vs 28-day median {fmt(base)}' if base is not None else '')


def drivers_from(rows):
    """One entry per ranked family, its strongest indicator, in rank order."""
    out, seen = [], set()
    for row in sorted(rows, key=lambda r: (r.get('rank') or 99, -(r.get('indicator_score') or 0))):
        family = row.get('family')
        if family in seen or row.get('status') != 'scored':
            continue
        seen.add(family)
        out.append({'family': family, 'family_label': FAMILY_LABELS.get(family, family),
                    'score': round(row.get('family_score') or 0.0, 4), 'indicator': row.get('indicator'),
                    'why': _why(row)})
    return out


def _usual_ok(row):
    base = row.get('baseline_median')
    return base is not None and base > 0 and row.get('baseline_n', 0) >= 7


def direction_of(rules, row):
    """'spike', 'collapse' or None: the row's price against its region's levels (model.levels_for).

    Usual here is the 28-day same-time median before the interval (sql.THRESHOLD), so it only ever
    reads earlier days; a multiple-of-usual level needs at least 7 of them.
    """
    return model.crossing(model.levels_for(rules, row.get('region')), row.get('price'),
                          row.get('baseline_median'), _usual_ok(row))


def threshold_text(rules, row, direction=None):
    levels = model.levels_for(rules, row.get('region'))
    direction = direction or direction_of(rules, row) or 'spike'
    level = levels.get(direction) or levels['spike']
    if level is not levels.get(direction):
        direction = 'spike'
    return model.level_text(direction, level, row.get('baseline_median') if level['mode'] != 'absolute' else None,
                            'the 28-day median at this time of day')


def crosses(rules, row):
    return direction_of(rules, row) is not None


class AlertService:
    def __init__(self, store, bigquery=None, mailer=None, public_url='https://grid-nowcast.web.app',
                 clock=_utc_now, sleep=None, max_cards=MAX_CARDS_PER_RUN, draft=None, replay=None, cards=None):
        self.store, self.bigquery, self.mailer = store, bigquery, mailer
        self.cards = cards  # the full driver card on open (src/alerts/ontology_live.py); None: baked cards only
        self._explain_cache, self._explain_lock = OrderedDict(), Lock()
        self.replay = replay  # the baked replay's alerts (src/alerts/replay.py); None: none on this server
        self.draft = draft  # the portfolio import's reader (src/alerts/draft.py); None: switched off
        self.public_url, self.clock, self.max_cards = public_url.rstrip('/'), clock, max_cards
        self.sleep = sleep

    # ------------------------------------------------------------------------- configuration
    @property
    def email_status(self):
        return 'configured' if self.mailer is not None else 'not configured'

    def config(self, user):
        portfolios, rules = self.store.versions('portfolio'), self.store.latest('rules')
        latest = portfolios[-1] if portfolios else None
        out = {'signed_in': user is not None, 'email': user['email'] if user else None,
               'email_status': self.email_status, 'checks_available': self.bigquery is not None,
               'import_available': self.draft is not None}
        if user is None:
            out['portfolio'] = ({'present': True, 'version': latest['version'],
                                 'effective_from': latest['effective_from']} if latest else None)
            out['rules'] = (dict({k: rules[k] for k in ('version', 'enabled', 'threshold', 'regions', 'min_severity')},
                                 levels=rules.get('levels') or {}, recipients_count=len(rules['recipients']))
                            if rules else None)
            return out
        out['portfolio'] = ({'latest': latest, 'versions': [
            {k: v.get(k) for k in ('version', 'effective_from', 'saved_by', 'saved_at', 'note')} for v in portfolios]}
            if latest else None)
        out['rules'] = rules
        return out

    def save_portfolio(self, user, body):
        doc = dict(model.validate_portfolio(body), saved_by=user['email'], saved_at=self.clock())
        return {'version': self.store.add_version('portfolio', doc)}

    def portfolio_draft(self, user):
        """The import's draft for a signed-in user (the route requires one); never saved here."""
        if self.draft is None:
            raise ImportOff()
        draft = self.draft.read()
        if draft is None:
            raise NoDraft()
        return draft

    def save_rules(self, user, body):
        doc = dict(model.validate_rules(body), saved_by=user['email'], saved_at=self.clock())
        return {'version': self.store.add_version('rules', doc)}

    # ----------------------------------------------------------------------------- the checks
    def _need_bigquery(self):
        if self.bigquery is None:
            raise ChecksUnavailable('checks are not available in this mode (no BigQuery)')

    def _threshold_rows(self, regions, after, until):
        rows, billed = self.bigquery.query(sql.THRESHOLD, [
            parameter('after', sql.civil(after), 'TIMESTAMP'), parameter('until', sql.civil(until), 'TIMESTAMP'),
            parameter('regions', regions, 'ARRAY<STRING>')], max_bytes=MAX_BYTES_SMALL)
        return rows, billed

    def _start_card(self, candidate):
        candidate['job_id'] = self.bigquery.start(sql.card_script(), [
            parameter('region', candidate['region']),
            parameter('t', sql.instant(candidate['interval_manila']), 'TIMESTAMP'),
            parameter('mode', CARD_MODE)], max_bytes=MAX_BYTES_CARD, labels={'alerts': 'card'})
        candidate['state'] = 'running'

    def _new_run(self, source, requested_by, rules, send):
        return {'id': uuid.uuid4().hex, 'status': 'running', 'source': source, 'requested_by': requested_by,
                'created_at': self.clock(), 'finished_at': None, 'rules_version': rules['version'],
                'send': bool(send), 'checked': 0, 'candidates': [], 'events': [], 'bytes_billed': 0,
                'alerts': [], 'emailed': 0, 'notes': []}

    def start_run(self, user, body, wait_seconds=48):
        """`POST /api/alerts/run`: one interval (region + interval_manila), checked and carded.

        The answer waits for the card up to `wait_seconds` (a card takes about 40 s; Firebase Hosting
        ends a proxied request at 60 s), so the page usually gets the finished run in one call. A run
        still going then comes back `running`; `GET /api/alerts/runs/<id>` finishes and reads it.
        """
        self._need_bigquery()
        model._keys(body, {'region', 'interval_manila', 'send'}, 'run')
        region = body.get('region')
        model._require(region in model.REGIONS, 'region', 'one of ' + ', '.join(model.REGIONS))
        at = model.parse_interval(body.get('interval_manila'))
        send = body.get('send', True)
        model._require(type(send) is bool, 'send', 'true or false')
        rules = self.store.latest('rules')
        if rules is None:
            raise NoRules()
        interval = at.strftime('%Y-%m-%dT%H:%M')
        run = self._new_run('manual', user['email'], rules, send)
        try:
            rows, billed = self._threshold_rows([region], (at - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M'), interval)
            run['bytes_billed'] += billed
            run['checked'] = len(rows)
            if not rows:
                run.update(status='done', finished_at=self.clock())
                run['notes'].append(f'no price for {model.REGIONS[region]} at {interval} in grid_curated.labels')
                self.store.put_run(run['id'], run)
                return self.public_run(run)
            row = rows[0]
            # A manual check always shows the card of the interval asked for; it records an alert and
            # emails only when the interval crosses the saved threshold.
            direction = direction_of(rules, row)
            candidate = dict(row, crossed=direction is not None, direction=direction or 'spike',
                             threshold_text=threshold_text(rules, row, direction),
                             event={'intervals_above': 1 if direction else 0,
                                    'first': interval, 'last': interval})
            self._start_card(candidate)
            run['candidates'].append(candidate)
        except QueryFailed as exc:
            raise ChecksUnavailable('BigQuery: ' + exc.reason) from None
        self.store.put_run(run['id'], run)
        if self.sleep is not None:
            for _ in range(int(wait_seconds // 2)):
                self.sleep(2)
                run = self._advance(run)
                if run['status'] != 'running':
                    break
            if run['status'] == 'running':
                run['notes'].append('the card is still being built: read GET /api/alerts/runs/' + run['id'] + ' to finish')
                self.store.put_run(run['id'], run)
        return self.public_run(run)

    def poll_run(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            return None
        if run['status'] == 'running':
            run = self._advance(run)
        return self.public_run(run)

    def _advance(self, run):
        # The rules the run started with decide recipients and `enabled`, never a later save.
        rules = self.store.version('rules', run['rules_version'])
        for candidate in run['candidates']:
            if candidate.get('state') != 'running':
                continue
            try:
                state = self.bigquery.status(candidate['job_id'])
                if state['state'] != 'DONE':
                    continue
                run['bytes_billed'] += state['bytes_billed']
                if state['error']:
                    candidate.update(state='failed', error=state['error'])
                    continue
                result = json.loads(self.bigquery.rows(candidate['job_id'])[0]['alert_json'])
            except QueryFailed as exc:
                candidate.update(state='failed', error=exc.reason)
                continue
            except (IndexError, KeyError, ValueError):
                candidate.update(state='failed', error='unreadable card result')
                continue
            alert = self._alert(run, candidate, result)
            candidate.update(state='done', alert_key=alert['key'] if candidate['crossed'] else None)
            if candidate['crossed']:
                created = self.store.create_alert(alert['key'], alert)
                if not created:
                    alert = self.store.get_alert(alert['key'])
                if run['send'] and rules and rules.get('enabled'):
                    alert = self._email(alert, rules, run)
            run['alerts'].append(alert)
        if all(c.get('state') in ('done', 'failed') for c in run['candidates']):
            run.update(status='done', finished_at=self.clock())
        self.store.put_run(run['id'], run)
        return run

    def _alert(self, run, candidate, result):
        summary = result.get('summary') or {}
        interval, region = candidate['interval_manila'], candidate['region']
        at = datetime.fromisoformat(interval)
        portfolio = model.latest_portfolio(self.store.versions('portfolio'), at.date())
        key = model.alert_key(region, interval, run['rules_version'])
        return {'key': key, 'region': region, 'region_label': model.REGIONS[region], 'interval_manila': interval,
                'price_php_mwh': candidate['price'], 'price_band': candidate.get('price_band'),
                'baseline_median_php_mwh': candidate.get('baseline_median'),
                'crossed': candidate['crossed'], 'direction': candidate.get('direction') or 'spike',
                'threshold_text': candidate['threshold_text'],
                'event': candidate.get('event'),
                'severity': model.alert_severity(summary.get('severity'), candidate.get('price_band')),
                'severity_reason': summary.get('severity_reason'),
                'confidence': summary.get('confidence'), 'confidence_reason': summary.get('confidence_reason'),
                'likely_drivers': drivers_from(result.get('drivers') or []),
                'relationship_trail': summary.get('relationship_trail'),
                'what_to_check': list(summary.get('what_to_check') or []),
                'financial_impact': model.impact(portfolio, region, at, candidate['price']),
                'mode': CARD_MODE, 'evidence_note': model.DISCLAIMER,
                'event_url': f'{self.public_url}/alerts?alert={key}',
                'emailed_to': [], 'sent_at': None, 'email_error': None,
                'source': run['source'], 'run_id': run['id'], 'rules_version': run['rules_version'],
                'created_at': self.clock()}

    def _email(self, alert, rules, run):
        """Send to each matching recipient at most once per alert, even under concurrent polls.

        Each (alert, recipient) is claimed atomically in the store before sending; only the caller that
        made the claim sends, and a recipient whose send failed is released so a later poll may retry.
        """
        key = alert['key']
        due = [e for e in model.recipients_for(rules, alert['region'], alert['severity'])
               if e not in alert['emailed_to']]
        if not due:
            return alert
        if self.mailer is None:
            self.store.add_emailed(key, [], None, 'email not configured')
            return self.store.get_alert(key)
        claimed = [e for e in due if self.store.claim_delivery(key, e)]
        if not claimed:
            return self.store.get_alert(key)
        subject, text, html = model.email_message(alert)
        try:
            sent = self.mailer.send([(e, subject, text, html) for e in claimed])
            error = None if len(sent) == len(claimed) else 'some recipients failed'
        except MailUnavailable:
            sent, error = [], 'the mail server refused or could not be reached'
        for email in claimed:
            if email not in sent:
                self.store.release_delivery(key, email)
        self.store.add_emailed(key, sent, self.clock(), error)
        run['emailed'] += len(sent)
        return self.store.get_alert(key)

    def scheduled(self, wait_seconds=45):
        """`POST /api/alerts/scheduled` (the Cloud Scheduler job): finish pending runs, then check new data."""
        self._need_bigquery()
        finished = [self._advance(r)['id'] for r in self.store.pending_runs()]
        rules = self.store.latest('rules')
        if rules is None or not rules['enabled']:
            return {'status': 'no rules saved' if rules is None else 'notifications disabled', 'finished_runs': finished}
        try:
            rows, billed = self.bigquery.query(sql.LATEST_INTERVAL, max_bytes=MAX_BYTES_SMALL)
        except QueryFailed as exc:
            raise ChecksUnavailable('BigQuery: ' + exc.reason) from None
        latest = rows[0]['latest'] if rows else None
        if latest is None:
            return {'status': 'no data', 'finished_runs': finished, 'bytes_billed': billed}
        state = self.store.get_state('last_checked') or {}
        last = state.get('interval_manila')
        latest_at = datetime.fromisoformat(latest)
        if last is None:
            last = (latest_at - FIRST_WINDOW).strftime('%Y-%m-%dT%H:%M')
        if latest <= last:
            return {'status': 'no new data', 'latest': latest, 'finished_runs': finished, 'bytes_billed': billed}
        after = max(datetime.fromisoformat(last), latest_at - SCHEDULED_WINDOW).strftime('%Y-%m-%dT%H:%M')
        run = self._new_run('scheduler', 'scheduler', rules, True)
        run['bytes_billed'] = billed
        if after != last:
            run['notes'].append(f'intervals from {last} to {after} were older than {SCHEDULED_WINDOW} and not checked')
        try:
            rows, billed = self._threshold_rows(rules['regions'], after, latest)
        except QueryFailed as exc:
            raise ChecksUnavailable('BigQuery: ' + exc.reason) from None
        run['bytes_billed'] += billed
        run['checked'] = len(rows)
        self.store.set_state('last_checked', {'interval_manila': latest, 'at': self.clock()})
        # One parent event per region and direction: a spike's peak is its highest price, a
        # collapse's its lowest. Spikes are carded first, the highest first.
        events = {}
        for row in rows:
            direction = direction_of(rules, row)
            if direction:
                event = events.setdefault((row['region'], direction), {
                    'region': row['region'], 'direction': direction, 'intervals_above': 0,
                    'first': row['interval_manila'], 'peak': row})
                event['intervals_above'] += 1
                event['last'] = row['interval_manila']
                peak = event['peak']['price']
                if (row['price'] > peak) if direction == 'spike' else (row['price'] < peak):
                    event['peak'] = row
        ranked = sorted(events.values(), key=lambda e: (e['direction'] != 'spike',
                                                        -e['peak']['price'] if e['direction'] == 'spike' else e['peak']['price']))
        for event in ranked[:self.max_cards]:
            peak = event['peak']
            candidate = dict(peak, crossed=True, direction=event['direction'],
                             threshold_text=threshold_text(rules, peak, event['direction']),
                             event={'intervals_above': event['intervals_above'], 'first': event['first'],
                                    'last': event['last']})
            try:
                self._start_card(candidate)
            except QueryFailed as exc:
                candidate.update(state='failed', error=exc.reason)
            run['candidates'].append(candidate)
        if len(ranked) > self.max_cards:
            run['notes'].append(f'{len(ranked) - self.max_cards} more regions crossed; carded next run only if still new')
        run['events'] = [dict({k: e[k] for k in ('region', 'intervals_above', 'first', 'last')},
                              **({'direction': 'collapse'} if e['direction'] == 'collapse' else {})) for e in ranked]
        if not run['candidates']:
            run.update(status='done', finished_at=self.clock())
        self.store.put_run(run['id'], run)
        if run['status'] == 'running' and self.sleep is not None:
            for _ in range(int(wait_seconds // 5)):
                self.sleep(5)
                run = self._advance(run)
                if run['status'] != 'running':
                    break
        return dict(self.public_run(run), finished_runs=finished)

    # ----------------------------------------------------------------------- reading results
    def public_run(self, run):
        out = {k: run[k] for k in ('id', 'status', 'source', 'created_at', 'finished_at', 'checked',
                                   'bytes_billed', 'emailed', 'notes', 'rules_version')}
        out['events'] = run.get('events', [])
        out['candidates'] = [{k: c.get(k) for k in ('region', 'interval_manila', 'price', 'crossed', 'direction', 'state',
                                                    'error', 'alert_key', 'threshold_text', 'event')}
                             for c in run['candidates']]
        out['alerts'] = run['alerts']
        return out

    def history(self, user, limit=50):
        alerts = self.store.recent_alerts(limit)
        if user is not None:
            return alerts
        hidden = []
        for alert in alerts:
            fi = alert.get('financial_impact') or {}
            alert = dict(alert, emailed_to=len(alert.get('emailed_to') or []),
                         financial_impact=(dict(HIDDEN) if 'php' in fi else {'status': fi.get('status')}))
            hidden.append(alert)
        return hidden

    def run_for(self, user, run):
        """A run as the caller may see it: estimates and recipients hidden when not signed in."""
        if user is not None or run is None:
            return run
        run = dict(run)
        run['alerts'] = [dict(a, emailed_to=len(a.get('emailed_to') or []),
                              financial_impact=dict(HIDDEN) if 'php' in (a.get('financial_impact') or {})
                              else a.get('financial_impact')) for a in run['alerts']]
        return run

    # ------------------------------------------------------------------ the inbox (E24)
    def _rules_for_replay(self):
        rules = self.store.latest('rules')
        return (rules, False) if rules else (replay_mod.DEFAULT_RULES, True)

    def _replay_impact(self, alert, versions):
        """The alert's estimate summed over its intervals, from the saved portfolio only."""
        total, last = 0.0, None
        for t, price in alert['points']:
            at = datetime.fromisoformat(t)
            fi = model.impact(model.latest_portfolio(versions, at.date()), alert['region'], at, price)
            if 'php' not in fi:
                return {'status': NEEDS_PORTFOLIO} if fi.get('status') == model.NO_PORTFOLIO else fi
            total, last = total + fi['php'], fi
        return {'php': round(total, 2), 'intervals': len(alert['points']), 'basis': last['basis'],
                'benchmark_php_mwh': last['benchmark_php_mwh']}

    def inbox(self, user, at=None, view='all'):
        """`GET /api/alerts/inbox`: the alerts up to the clock, grouped by recorded cause, worst first.

        view: 'all' or 'high' (high and extreme only).
        """
        if view not in INBOX_VIEWS:
            raise model.InvalidInput('view', 'one of ' + ', '.join(INBOX_VIEWS))
        if at is not None and not (type(at) is str and model.INTERVAL.fullmatch(at)):
            raise model.InvalidInput('at', 'a Manila time YYYY-MM-DDTHH:MM')
        rules, defaults = self._rules_for_replay()
        alerts = [dict(a) for a in (self.replay.alerts(rules, at) if self.replay is not None else [])]
        versions = self.store.versions('portfolio')
        for a in alerts:
            a['financial_impact'] = self._replay_impact(a, versions)
        for a in self.store.recent_alerts(50):
            if at is None or a.get('interval_manila', '') <= at:
                fi = a.get('financial_impact') or {}
                alerts.append(dict(a, source=a.get('source') or 'check', main_driver=model.main_driver(a),
                                   first=(a.get('event') or {}).get('first') or a['interval_manila'],
                                   last=(a.get('event') or {}).get('last') or a['interval_manila'],
                                   cause=None, href=f"/alerts?alert={a['key']}",
                                   financial_impact={'status': NEEDS_PORTFOLIO} if fi.get('status') == model.NO_PORTFOLIO else fi))
        for a in alerts:
            a['next_step'] = next_step(a)
        if view == 'high':
            alerts = [a for a in alerts if model.severity_rank(a.get('severity')) >= model.SEVERITIES.index('high')]
        alerts.sort(key=inbox_order)
        groups = group_alerts(alerts)
        if user is None:
            for g in groups:
                for a in g['alerts']:
                    a['financial_impact'] = (dict(HIDDEN) if 'php' in a['financial_impact'] else a['financial_impact'])
                    if 'emailed_to' in a:
                        a['emailed_to'] = len(a.get('emailed_to') or [])
                g['financial_impact'] = (dict(HIDDEN) if 'php' in g['financial_impact'] else g['financial_impact'])
        for g in groups:
            for a in g['alerts']:
                a.pop('points', None)
                # The inbox carries the counts and the notices nearest the alert; its page has them all.
                # Only what a card shows: the reasons and the rule are on the alert page.
                around = a.get('notices_around')
                if around:
                    items = (around.get('items') or [])[-INBOX_NOTICES:]
                    a['notices_around'] = dict({k: around.get(k) for k in INBOX_AROUND_KEYS},
                                               shown=len(items),
                                               items=[{k: x.get(k) for k in INBOX_NOTICE_KEYS} for x in items])
        span = self.replay.span if self.replay is not None else None
        return {'at': at, 'view': view, 'signed_in': user is not None, 'default_levels': defaults,
                'rules_version': rules.get('version'), 'replay_span': list(span) if span else None,
                'count': len(alerts), 'groups': groups,
                'order': 'severity (extreme, high, medium, low), then the peso impact, then the latest first'}

    def alert(self, user, key, at=None):
        """`GET /api/alerts/alert/{key}`: one replay alert as the inbox shows it at the clock, plus the
        region's five-minute series and operator notices around it (src/alerts/replay.py `around`).

        Built on request from the bake: no BigQuery, no model. An alert that starts after the clock
        answers {'status': 'after_clock', ...} with its start only; a key the current rules do not
        raise is UnknownAlert (404).
        """
        if not (type(key) is str and ALERT_KEY.fullmatch(key)):
            raise UnknownAlert()
        if at is not None and not (type(at) is str and model.INTERVAL.fullmatch(at)):
            raise model.InvalidInput('at', 'a Manila time YYYY-MM-DDTHH:MM')
        if self.replay is None:
            raise UnknownAlert()
        found = next((a for g in self.inbox(user, at)['groups'] for a in g['alerts']
                      if a['key'] == key and a.get('source') == 'replay'), None)
        rules, defaults = self._rules_for_replay()
        if found is None:
            later = self.replay.find(rules, key)  # replay-year: any alert of the bake, not only the newest shown
            if later is None:
                raise UnknownAlert()
            return {'status': 'after_clock', 'at': at, 'key': key, 'region': later['region'],
                    'region_label': later['region_label'], 'direction': later['direction'],
                    'first': later['first']}
        if 'notices_around' in found:
            found['notices_around'] = self.replay.notices_around(found, at)
        from . import ontology as ontology_mod
        return {'status': 'ok', 'at': at, 'default_levels': defaults, 'rules_version': rules.get('version'),
                'alert': found, 'around': self.replay.around(rules, found, at),
                'ontology': ontology_mod.load_card(self.replay.directory, key, found)}

    def explain(self, user, key, at=None):
        """`GET /api/alerts/explain/{key}`: the alert's likely drivers, summary and paragraph, computed
        here from the replay data when the alert is opened (src/alerts/drivers.py, src/alerts/explain.py).
        No model call. A saved AI phrasing is shown only for the same facts. The result is kept in memory
        per alert (least recently used, EXPLAIN_CACHE entries) while the replay data is unchanged. An
        alert after the clock answers as `alert` does.

        `ontology` is the full BigQuery driver card (src/alerts/ontology.py schema) or None, and
        `ontology_status` says where it came from (src/alerts/ontology_live.py): baked, else saved in
        Firestore, else computed for a signed-in user on this open (capped bytes, then saved); for an
        anonymous caller or on a failure it says so and the code-only explanation stands."""
        from . import drivers as drivers_mod, explain as explain_mod, ontology as ontology_mod
        found = self.alert(user, key, at)
        if found.get('status') != 'ok':
            return found
        a = found['alert']
        d = self.replay.data()
        with self._explain_lock:
            hit = self._explain_cache.get(key)
            if hit is not None and hit[0] is d and hit[1] == a['interval_manila']:
                self._explain_cache.move_to_end(key)
                return dict(hit[2], memo='hit', **self._ontology(user, a))
        result = drivers_mod.likely_drivers(d, a['region'], a['interval_manila'])
        out = explain_mod.answer(a, result, explain_mod.load_saved(self.replay.directory, a),
                                 ontology_mod.load_card(self.replay.directory, key, a))
        with self._explain_lock:
            self._explain_cache[key] = (d, a['interval_manila'], out)
            self._explain_cache.move_to_end(key)
            while len(self._explain_cache) > EXPLAIN_CACHE:
                self._explain_cache.popitem(last=False)
        return dict(out, memo='computed', **self._ontology(user, a))

    def _ontology(self, user, alert):
        from . import ontology_live
        cards = self.cards if self.cards is not None else ontology_live.LiveCards()
        return cards.block(user, alert, self.replay.directory)

    def test_email(self, user):
        rules = self.store.latest('rules')
        if rules is None:
            raise NoRules()
        recipients = [r['email'] for r in rules['recipients']]
        if not recipients:
            raise model.InvalidInput('recipients', 'add at least one recipient first')
        if self.mailer is None:
            raise MailUnavailable()
        t = rules['threshold']
        rule = (f"price at or above {t['value']:,.0f} PHP/MWh" if t['mode'] == 'absolute'
                else f"price at or above {t['value']:g} x the 28-day median at that time of day")
        own = [f"{model.REGIONS[code]}: " + '; '.join(model.level_text(d, lv[d], None, 'usual', tail=False) for d in model.DIRECTIONS if lv.get(d))
               for code, lv in sorted((rules.get('levels') or {}).items()) if lv.get('spike') or lv.get('collapse')]
        if own:
            rule += ' (own levels: ' + ' | '.join(own) + ')'
        regions = ', '.join(model.REGIONS[r] for r in rules['regions'])
        subject = '[InGRID] TEST · notifications are set up'
        text = (f"TEST MESSAGE: no alert was raised.\n\nSent by {user['email']} from the Grid Nowcast alerts page.\n"
                f"Notifications: {'on' if rules['enabled'] else 'off'}; {rule}; regions {regions}; "
                f"minimum severity {rules['min_severity']}.\n\nA real alert carries the severity, the financial impact "
                f"(from the saved portfolio, or 'not available'), the confidence, the relationship trail and what to "
                f"check.\n{model.DISCLAIMER}\n{self.public_url}/alerts\n")
        from html import escape
        html = '<div style="font-family:Arial,sans-serif;font-size:14px">' + ''.join(
            f'<p>{escape(p)}</p>' for p in text.strip().split('\n') if p) + '</div>'
        sent = self.mailer.send([(e, subject, text, html) for e in recipients])
        return {'sent_to': sent}


INBOX_VIEWS = ('all', 'high')
INBOX_NOTICES = 3  # notices around an alert the inbox carries (the nearest); the alert page lists them all
INBOX_AROUND_KEYS = ('from', 'to', 'count', 'counts', 'confirmed')
INBOX_NOTICE_KEYS = ('t', 'posted', 'id', 'kind', 'kind_label', 'text', 'match', 'match_label', 'plant',
                     'plant_href', 'notice_href', 'claimed')
NEEDS_PORTFOLIO = 'Needs your portfolio'
ALERT_KEY = re.compile(r'[0-9a-f]{24}\Z')


class UnknownAlert(Exception):
    """No stored or replay alert has that key; the route answers 404."""


def _php(alert):
    fi = alert.get('financial_impact') or {}
    return abs(fi['php']) if type(fi.get('php')) in (int, float) else None


def _desc(text):
    return tuple(-ord(c) for c in text)


def inbox_order(alert):
    """Severity first (extreme to low, unrated last), then the peso impact (larger first, any figure
    before none), then the latest first."""
    php = _php(alert)
    return (-model.severity_rank(alert.get('severity')), php is None, -(php or 0),
            _desc(alert.get('last') or alert.get('interval_manila') or ''))


def group_alerts(alerts):
    """Parent risk events: alerts that share one recorded cause sit under it; any other alert is its own.

    `alerts` must already be in inbox order, so a group takes its first (worst) alert's place. Its peso
    impact is the sum only when every member has one from the portfolio.
    """
    groups, by_cause = [], {}
    for a in alerts:
        cause = a.get('cause')
        if cause and cause.get('id'):
            group = by_cause.get(cause['id'])
            if group is None:
                group = by_cause[cause['id']] = {'id': 'event:' + cause['id'], 'cause': cause, 'alerts': []}
                groups.append(group)
            group['alerts'].append(a)
        else:
            groups.append({'id': 'alert:' + a['key'], 'cause': None, 'alerts': [a]})
    for g in groups:
        lead = g['alerts'][0]
        g['severity'] = lead.get('severity')
        g['title'] = g['cause']['title'] if g['cause'] else f"{lead.get('region_label')} {lead.get('direction') or 'spike'}"
        g['regions'] = sorted({a['region'] for a in g['alerts']})
        g['first'] = min(a.get('first') or a['interval_manila'] for a in g['alerts'])
        g['last'] = max(a.get('last') or a['interval_manila'] for a in g['alerts'])
        figures = [_php(a) is not None for a in g['alerts']]
        if all(figures):
            g['financial_impact'] = {'php': round(sum(a['financial_impact']['php'] for a in g['alerts']), 2)}
        elif not any(figures):
            g['financial_impact'] = dict(lead.get('financial_impact') or {'status': NEEDS_PORTFOLIO})
        else:
            g['financial_impact'] = {'status': 'Partly estimated: some alerts need your portfolio'}
        g['next_step'] = lead['next_step']
    return groups


def next_step(alert):
    """A stated next step from what is on record; never a trade instruction."""
    if alert.get('cause'):
        return f"Open the event ({alert['cause']['title']}) and check its timeline against your position."
    if (alert.get('financial_impact') or {}).get('status') == NEEDS_PORTFOLIO:
        return 'Open the alert to review the interval and the notices around it.'
    if alert.get('direction') == 'collapse':
        return 'Review the low-price interval: check curtailment and whether your load can take more.'
    if model.severity_rank(alert.get('severity')) >= model.SEVERITIES.index('high'):
        return 'Open the alert and check reserves and the operator notices around it.'
    return 'Watch the next intervals; no recorded event explains this yet.'
