"""BigQuery over its REST API, with the runtime's own identity (google-auth, already in the lock).

No new dependency: jobs are inserted and read with `google.auth.transport.requests.AuthorizedSession`.
Every job carries `maximumBytesBilled` and the `work=alerts` label, and its billed bytes are read back
so each run reports what it cost. Errors keep BigQuery's reason code only, never row data.
"""
import time
import uuid

API = 'https://bigquery.googleapis.com/bigquery/v2/projects/%s'
SCOPES = ('https://www.googleapis.com/auth/bigquery',)


class QueryFailed(Exception):
    """A job failed, was refused, or could not be reached; `reason` is BigQuery's code or ours."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def parameter(name, value, kind='STRING'):
    """A named query parameter; `kind` 'ARRAY<STRING>' takes a list."""
    if kind == 'ARRAY<STRING>':
        return {'name': name, 'parameterType': {'type': 'ARRAY', 'arrayType': {'type': 'STRING'}},
                'parameterValue': {'arrayValues': [{'value': v} for v in value]}}
    return {'name': name, 'parameterType': {'type': kind}, 'parameterValue': {'value': str(value)}}


def _cell(value, field):
    if value is None:
        return None
    kind = field.get('type')
    if kind in ('FLOAT', 'FLOAT64', 'NUMERIC', 'BIGNUMERIC'):
        return float(value)
    if kind in ('INTEGER', 'INT64'):
        return int(value)
    if kind in ('BOOLEAN', 'BOOL'):
        return value == 'true'
    return value


def rows_from(result):
    """Flat rows from a getQueryResults answer: scalar columns only (complex results travel as JSON text)."""
    fields = result.get('schema', {}).get('fields', [])
    return [{f['name']: _cell(c.get('v'), f) for f, c in zip(fields, row.get('f', []))}
            for row in result.get('rows', [])]


class BigQueryRest:
    def __init__(self, project, location, session=None, clock=time.monotonic, sleep=time.sleep):
        self.project, self.location = project, location
        self._session, self.clock, self.sleep = session, clock, sleep

    def session(self):
        if self._session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials, _ = google.auth.default(scopes=SCOPES)
            self._session = AuthorizedSession(credentials)
        return self._session

    def _request(self, method, path, **kwargs):
        import requests
        try:
            response = self.session().request(method, (API % self.project) + path, timeout=30, **kwargs)
        except requests.RequestException:
            raise QueryFailed('unreachable') from None
        if response.status_code >= 400:
            try:
                reason = response.json()['error']['errors'][0]['reason']
            except (ValueError, KeyError, IndexError, TypeError):
                reason = 'http_%d' % response.status_code
            raise QueryFailed(reason)
        return response.json()

    def start(self, sql, params=(), max_bytes=1_000_000_000, labels=None):
        """Insert a query (or script) job and return its id without waiting."""
        job_id = 'alerts_' + uuid.uuid4().hex
        body = {'jobReference': {'projectId': self.project, 'location': self.location, 'jobId': job_id},
                'configuration': {'labels': dict(labels or {}, work='alerts'),
                                  'query': {'query': sql, 'useLegacySql': False, 'parameterMode': 'NAMED',
                                            'queryParameters': list(params),
                                            'maximumBytesBilled': str(int(max_bytes))}}}
        self._request('POST', '/jobs', json=body)
        return job_id

    def status(self, job_id):
        """{'state': 'PENDING'|'RUNNING'|'DONE', 'error': reason or None, 'bytes_billed': int}."""
        job = self._request('GET', '/jobs/%s' % job_id, params={'location': self.location})
        status = job.get('status', {})
        error = status.get('errorResult')
        billed = job.get('statistics', {}).get('query', {}).get('totalBytesBilled') or 0
        return {'state': status.get('state', 'PENDING'), 'error': (error or {}).get('reason') if error else None,
                'bytes_billed': int(billed)}

    def rows(self, job_id):
        result = self._request('GET', '/queries/%s' % job_id,
                               params={'location': self.location, 'maxResults': 10000, 'timeoutMs': 10000})
        if not result.get('jobComplete', True):
            raise QueryFailed('not_complete')
        return rows_from(result)

    def wait(self, job_id, seconds):
        """Poll until DONE or `seconds` pass; returns the last status."""
        deadline = self.clock() + seconds
        while True:
            state = self.status(job_id)
            if state['state'] == 'DONE' or self.clock() >= deadline:
                return state
            self.sleep(1.0)

    def query(self, sql, params=(), max_bytes=1_000_000_000, labels=None, seconds=30):
        """Run and read a small query synchronously: (rows, bytes_billed)."""
        job_id = self.start(sql, params, max_bytes, labels)
        state = self.wait(job_id, seconds)
        if state['state'] != 'DONE':
            raise QueryFailed('timeout')
        if state['error']:
            raise QueryFailed(state['error'])
        return self.rows(job_id), state['bytes_billed']
