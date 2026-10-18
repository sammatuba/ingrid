"""HOST-1: walk the demo container through its published port, step by step and offline.

Run by scripts/deploy/walkthrough.sh against the image started with no environment at all. The
standard library only (urllib), so the Docker host needs nothing installed and no container
command is needed — the walkthrough goes through the port the image publishes, exactly as a
stranger's browser would. Every check prints one line with its expected and observed value, so
the output is the record that goes into the HOST-1 packet. Nothing here reaches a cloud service,
a model or a credential: the only contact is the demo mode on 127.0.0.1.

The walkthrough is the acceptance path: the page and assets load, the documented fictional
account signs in, a review is compiled and saved as a disposition with its receipt, a judge
session is opened with no credentials, and `POST /demo/reset` restores that session and rotates
only its token. Any failure prints FAIL and the exit status is non-zero.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

AUDIT_CUTOFF = '2026-10-01T10:00:00+08:00'
INFORMATION_CUTOFF = '2026-10-05T10:00:00+08:00'
REFERENCE_KEYS = ('record_kind', 'record_id', 'revision_id', 'content_digest')
EMAIL, PASSWORD = 'analyst@example.test', 'synthetic-local-only'
FIXTURE_TENANT, FIXTURE_CASE = 'synthetic-tenant', 'synthetic-case'
JUDGE_TENANT = 'demo-judge'
# `/` is the public grid desk (GRID-2); the change desk it replaced is served at `/desk` and
# keeps its own marker, its assets and its sign-in.
PAGE_MARKER = 'InGRID · Philippine grid'
DESK_MARKER = 'SYNTHETIC WALKTHROUGH'
# GRID-3: the event review page of the first real case, and the event case each judge session
# seeds for itself. The page is the design file's; the case is built by `src.demo.pedc`.
EVENT_ID = 'pedc-u2-2026-09-21'
EVENT_MARKER = 'InGRID · Event review'
REPLAY_FILES = ('regions.json', 'hvdc.json', 'nodes-2026-09-21.json', 'advisories.json',
                'sites.json', 'ph.geojson')
# PERF-1's first cache class: a public file under its content-derived build stamp.
IMMUTABLE = 'public, max-age=31536000, immutable'


def reference(record):
    """The four-key reference the API takes back, the same projection src/review/records.py uses."""
    return {key: record[key] for key in REFERENCE_KEYS}


class Record:
    """One line per check, with the reason attached to a failure."""

    def __init__(self):
        self.checks, self.failed = 0, 0

    def check(self, name, ok, detail=''):
        self.checks += 1
        self.failed += 0 if ok else 1
        print(f'{"PASS" if ok else "FAIL"}  {name}{"  — " + detail if detail else ""}')
        return ok

    def report(self):
        print(f'\n{self.checks - self.failed}/{self.checks} checks passed on the container port')
        return self.failed == 0


class Client:
    """A minimal JSON client that returns (status, payload) instead of raising on 4xx/5xx."""

    def __init__(self, base):
        self.base = base

    def request(self, method, path, body=None, token=None):
        """`(status, payload bytes, response headers)` for one call, refusals included."""
        data = None if body is None else json.dumps(body).encode('utf-8')
        headers = {}
        if body is not None:
            headers['content-type'] = 'application/json'
        if token is not None:
            headers['authorization'] = 'Bearer ' + token
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.read(), dict(error.headers)

    def call(self, method, path, body=None, token=None, raw=False):
        status, payload, _ = self.request(method, path, body, token)
        if raw:
            return status, payload.decode('utf-8', 'replace')
        try:
            return status, json.loads(payload) if payload else None
        except ValueError:
            return status, payload[:200].decode('utf-8', 'replace')

    def probe(self, path):
        """`(status, headers)` for the cache-class checks; nothing is parsed."""
        status, _, headers = self.request('GET', path)
        return status, headers

    def case_url(self, tenant, case):
        return f'/v1/tenants/{tenant}/cases/{case}'


def wait_for_health(client, record, attempts=60):
    """The container may still be starting; the first response is the readiness signal."""
    for attempt in range(attempts):
        try:
            status, payload = client.call('GET', '/health')
        except (urllib.error.URLError, OSError) as error:
            if attempt == attempts - 1:
                record.check('GET /health', False, f'the port never answered: {error}')
                return False
            time.sleep(0.25)
            continue
        return record.check('GET /health', status == 200 and payload == {
            'status': 'ok', 'mode': 'demo', 'storage_checked': False},
            f'{status} {payload}')
    return False


def review_body(client, tenant, case, token, key):
    """Compile the walkthrough's disposition from the served state, exactly as the app does."""
    status, snapshot = client.call('POST', client.case_url(tenant, case) + '/snapshots',
                                   {'audit_cutoff': AUDIT_CUTOFF}, token)
    if status != 200:
        return None, f'the snapshot is {status} {snapshot}'
    status, task = client.call('POST', client.case_url(tenant, case) + '/compile',
                               {'snapshot_ref': reference(snapshot), 'assumption_id': 'capacity-assumption',
                                'information_cutoff': INFORMATION_CUTOFF}, token)
    if status != 200:
        return None, f'the compile is {status} {task}'
    _, heads = client.call('GET', client.case_url(tenant, case), None, token)
    return dict(request_id=key, idempotency_key=key, task_ref=reference(task),
                snapshot_digest=task['payload']['snapshot_ref']['content_digest'],
                expected_assumption_head=task['payload']['assumption_ref'],
                expected_outlook_head=heads['outlook'], disposition='retain',
                rationale='Fictional analyst retained the accepted input', new_value=None), ''


def run(base):
    record, client = Record(), Client(base)
    print(f'HOST-1 container walkthrough through {base}: demo mode, no environment, no credential\n')
    if not wait_for_health(client, record):
        return record.report()

    status, page = client.call('GET', '/', raw=True)
    record.check('GET / serves the public grid desk', status == 200 and PAGE_MARKER in page,
                 f'{status}, {len(page)} bytes, marker {PAGE_MARKER!r} present: {PAGE_MARKER in page}')
    status, desk = client.call('GET', '/desk', raw=True)
    record.check('GET /desk still serves the change desk', status == 200 and DESK_MARKER in desk,
                 f'{status}, marker {DESK_MARKER!r} present: {DESK_MARKER in desk}')
    status, _ = client.call('GET', '/grid/grid.js')
    record.check('GET /grid/grid.js is served', status == 200, str(status))
    status, event_page = client.call('GET', '/event/' + EVENT_ID, raw=True)
    record.check('GET /event/<id> serves the event review page',
                 status == 200 and EVENT_MARKER in event_page,
                 f'{status}, marker {EVENT_MARKER!r} present: {EVENT_MARKER in event_page}')
    status, _ = client.call('GET', '/grid/event-api.js')
    record.check('GET /grid/event-api.js is served', status == 200, str(status))
    for name in REPLAY_FILES:
        status, _ = client.call('GET', '/grid-data/' + name)
        record.check(f'GET /grid-data/{name} serves the baked replay snapshot', status == 200,
                     f'{status} — the image is built from a context holding build/grid-data, which '
                     f'scripts/grid/build_data.py writes')
    status, _ = client.call('GET', '/assets/app.js')
    record.check('GET /assets/app.js is served', status == 200, str(status))

    # PERF-1: the three cache classes. The page revalidates and names this build; the
    # versioned files it points at are immutable for a year; an unknown stamp is a 404 and
    # never a fallback to the current files; the private and health answers stay no-store.
    match = re.search(r'id="nowcast-build"[^>]*content="([0-9a-f]{16})"', page)
    stamp = match.group(1) if match else ''
    record.check('GET / writes a build stamp into its asset and data URLs', bool(stamp),
                 f'stamp {stamp or "absent"}')
    status, headers = client.probe('/')
    record.check('GET / revalidates (cache-control: no-cache)',
                 status == 200 and headers.get('cache-control') == 'no-cache',
                 f'{status}, cache-control {headers.get("cache-control")!r}')
    status, headers = client.probe('/health')
    record.check('GET /health stays no-store', headers.get('cache-control') == 'no-store',
                 f'{status}, cache-control {headers.get("cache-control")!r}')
    if stamp:
        status, headers = client.probe(f'/grid/{stamp}/grid.js')
        record.check('GET /grid/<stamp>/grid.js is served immutable for a year',
                     status == 200 and headers.get('cache-control') == IMMUTABLE,
                     f'{status}, cache-control {headers.get("cache-control")!r}')
        status, headers = client.probe(f'/grid/{stamp}/fonts/inter-latin-400-normal.woff2')
        record.check('GET /grid/<stamp>/fonts/*.woff2 is served immutable for a year',
                     status == 200 and headers.get('cache-control') == IMMUTABLE,
                     f'{status}, cache-control {headers.get("cache-control")!r}')
        status, headers = client.probe(f'/grid-data/{stamp}/regions.json')
        record.check('GET /grid-data/<stamp>/regions.json is served immutable for a year',
                     status == 200 and headers.get('cache-control') == IMMUTABLE,
                     f'{status}, cache-control {headers.get("cache-control")!r}')
        status, headers = client.probe(f'/grid-data/{"0" * 16}/regions.json')
        record.check('an unknown build stamp is a 404, not a fallback',
                     status == 404 and headers.get('cache-control') == 'no-store',
                     f'{status}, cache-control {headers.get("cache-control")!r}')

    status, signed = client.call('POST', '/session', {'email': EMAIL, 'password': PASSWORD})
    token = signed.get('id_token') if isinstance(signed, dict) else None
    record.check('POST /session signs in the documented fictional account', status == 200 and bool(token),
                 f'{status}, token: {bool(token)}')
    status, _ = client.call('POST', '/session', {'email': EMAIL, 'password': 'not-the-password'})
    record.check('POST /session refuses any other password', status == 401, str(status))
    status, _ = client.call('GET', client.case_url(FIXTURE_TENANT, FIXTURE_CASE))
    record.check('the fixture case needs a token', status == 401, str(status))

    fixture = client.case_url(FIXTURE_TENANT, FIXTURE_CASE)
    status, _ = client.call('GET', fixture, None, token)
    record.check('the fixture case reads with the fixture token', status == 200, str(status))
    status, workspace = client.call('GET', fixture + '/workspace', None, token)
    assumptions = workspace.get('assumptions', []) if isinstance(workspace, dict) else []
    record.check('the fixture workspace holds the labelled assumption',
                 status == 200 and [a.get('record_id') for a in assumptions] == ['capacity-assumption'],
                 f'{status}, assumptions {[a.get("record_id") for a in assumptions]}')

    body, why = review_body(client, FIXTURE_TENANT, FIXTURE_CASE, token, 'walkthrough-review')
    if not record.check('the fixture source compiles to a review task', body is not None, why):
        return record.report()
    status, receipt = client.call('POST', fixture + '/reviews', body, token)
    record.check('the review saves a disposition with its receipt',
                 status == 200 and receipt.get('decision_ref', {}).get('record_kind') == 'ReviewDecision'
                 and len(str(receipt.get('request_digest'))) == 64,
                 f'{status}, decision {receipt.get("decision_ref", {}).get("record_id") if isinstance(receipt, dict) else receipt}')
    status, replay = client.call('POST', fixture + '/reviews', body, token)
    record.check('the same review replays idempotently', status == 200 and replay == receipt,
                 f'{status}, identical receipt: {replay == receipt}')
    status, history = client.call('GET', fixture + '/history', None, token)
    record.check('the fixture case history holds the saved review', status == 200 and len(history) == 1,
                 f'{status}, history {len(history) if isinstance(history, list) else history}')

    status, judge = client.call('POST', '/demo/session')
    judge_token = judge.get('id_token') if isinstance(judge, dict) else None
    record.check('POST /demo/session opens a judge session with no credentials',
                 status == 200 and judge.get('mode') == 'demo' and judge.get('tenant') == JUDGE_TENANT
                 and len(str(judge.get('fixture_digest'))) == 64 and bool(judge_token),
                 f'{status}, tenant {judge.get("tenant") if isinstance(judge, dict) else None}, '
                 f'case {judge.get("case") if isinstance(judge, dict) else None}')
    record.check('the judge session seeds its own copy of the real PEDC event case',
                 isinstance(judge, dict) and judge.get('event_case') and judge.get('event_seeded_at'),
                 f'event case {judge.get("event_case") if isinstance(judge, dict) else None}, '
                 f'seeded {judge.get("event_seeded_at") if isinstance(judge, dict) else None}')
    status, event_case = client.call('GET', client.case_url(JUDGE_TENANT, judge['event_case']),
                                     None, judge_token)
    record.check('the judge token reads its own copy of the event case',
                 status == 200 and 'assumption:08PEDC_U02:2026-09-21' in (event_case.get('assumptions') or {}),
                 f'{status}, assumptions {list((event_case.get("assumptions") or {}).keys())}')
    status, second = client.call('POST', '/demo/session')
    record.check('a second judge session gets its own case',
                 status == 200 and second.get('case') != judge.get('case'),
                 f'{status}, cases {judge.get("case")} and {second.get("case")}')
    status, _ = client.call('GET', client.case_url(JUDGE_TENANT, second['case']), None, judge_token)
    record.check('the first judge token is 404 on the second judge case', status == 404, str(status))
    status, _ = client.call('GET', client.case_url(JUDGE_TENANT, judge['event_case']), None, second['id_token'])
    record.check("the second judge token is 404 on the first judge's event case", status == 404, str(status))
    status, _ = client.call('GET', fixture, None, judge_token)
    record.check('a judge token is 404 on the private-shaped fixture case', status == 404, str(status))

    judge_case = client.case_url(JUDGE_TENANT, judge['case'])
    judge_body, why = review_body(client, JUDGE_TENANT, judge['case'], judge_token, 'judge-review')
    status, judge_receipt = client.call('POST', judge_case + '/reviews', judge_body, judge_token)
    record.check('the judge saves a disposition on its own case',
                 status == 200 and judge_receipt.get('decision_ref', {}).get('record_kind') == 'ReviewDecision',
                 f'{status}, decision {judge_receipt.get("decision_ref", {}).get("record_id") if isinstance(judge_receipt, dict) else judge_receipt}')

    status, _ = client.call('POST', '/demo/reset')
    record.check('POST /demo/reset needs the caller\'s own token', status == 401, str(status))
    status, reset = client.call('POST', '/demo/reset', None, judge_token)
    record.check('POST /demo/reset restores the calling session',
                 status == 200 and reset.get('reset') is True and reset.get('case') == judge.get('case')
                 and reset.get('fixture_digest') == judge.get('fixture_digest'),
                 f'{status}, reset {reset.get("reset")}, same case {reset.get("case") == judge.get("case")}, '
                 f'same digest {reset.get("fixture_digest") == judge.get("fixture_digest")}')
    status, _ = client.call('GET', judge_case, None, judge_token)
    record.check('the pre-reset judge token is refused after the reset', status == 401, str(status))
    status, _ = client.call('GET', judge_case, None, reset['id_token'])
    record.check('the fresh reset token reads the restored case', status == 200, str(status))
    status, history = client.call('GET', judge_case + '/history', None, reset['id_token'])
    record.check('the reset case history is empty again', status == 200 and history == [],
                 f'{status}, history {history}')
    status, _ = client.call('GET', client.case_url(JUDGE_TENANT, second['case']), None, second['id_token'])
    record.check('the other judge session still reads its own case', status == 200, str(status))

    return record.report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18001)
    options = parser.parse_args(argv)
    return 0 if run(f'http://{options.host}:{options.port}') else 1


if __name__ == '__main__':
    sys.exit(main())
