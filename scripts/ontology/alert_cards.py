#!/usr/bin/env python3
"""Save the full ontology driver card for replay alerts (ericka-desk): the card the PEDC event page shows,
for every replay alert whose window touches the chosen Manila dates.

Each alert (src/alerts/replay.py, default rules, as of the bake's last interval) is taken at its peak
interval and region. One read-only BigQuery script per alert, built by src/alerts/ontology.py
``card_query`` (the three modes' driver card and ranking in temporary tables, then card_summary's SQL
over them; nothing is created or replaced in the dataset), runs through the bq CLI. The decoded rows are
kept in a private directory (company data, never in Git) and shaped by ``ontology.shape`` into
``<data>/ontology/cards/<key>.json`` once ``ontology.problems`` finds nothing; GET /api/alerts/explain/{key}
reads that file. The page never calls BigQuery. Safe to rerun.

    alert_cards.py --data D --dates 2026-10-05 2026-04-18 --list           # the alerts, no query
    CLOUDSDK_CORE_ACCOUNT=<account> alert_cards.py --data D --dates ... --dry-run --only KEY
    CLOUDSDK_CORE_ACCOUNT=<account> alert_cards.py --data D --dates ... [--only KEY ...] [--jobs 4]
    alert_cards.py --data D --dates ... --shape-only                        # re-shape the saved rows

Exit codes: 0 done, 1 a query or check failed, 2 usage or input error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.alerts import ontology  # noqa: E402
from src.alerts.replay import DEFAULT_RULES, Replay  # noqa: E402

PROJECT, LOCATION = 'grid-nowcast', 'asia-southeast1'
MAX_BYTES = 5_000_000_000
BILLED = re.compile(r'"totalBytesBilled"\s*:\s*"?(\d+)')


def select_alerts(data_dir, dates):
    """The replay alerts (default rules, whole bake) whose first..last window touches a Manila date."""
    rep = Replay(data_dir)
    d = rep.data()
    if not d:
        return []
    out = [rep._alert(e, DEFAULT_RULES, d, d['t'][-1]) for e in rep._cut(d, DEFAULT_RULES, len(d['t']) - 1)
           if any(e['first'][:10] <= day <= e['last'][:10] for day in dates)]
    out.sort(key=lambda a: (a['first'], a['region']))
    return out


def bq_args(params):
    """bigquery.parameter dicts as bq CLI --parameter flags."""
    return [f"--parameter={p['name']}:{p['parameterType']['type']}:{p['parameterValue']['value']}" for p in params]


def bq(sql, params, *, dry_run=False):
    cmd = ['bq', f'--project_id={PROJECT}', f'--location={LOCATION}', 'query', '--use_legacy_sql=false',
           f'--maximum_bytes_billed={MAX_BYTES}', '--label=work:ontology', '--format=json', *bq_args(params)]
    if dry_run:
        cmd.append('--dry_run')
    r = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-800:])
    return r.stdout


def parse_rows(stdout):
    """The script's last result, [{"alert_json": "..."}], decoded."""
    start = stdout.rfind('[{"alert_json"')
    if start < 0:
        raise RuntimeError('no alert_json row in the output')
    rows, _ = json.JSONDecoder().raw_decode(stdout[start:])
    return json.loads(rows[0]['alert_json'])


def write_private(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=1, ensure_ascii=False)
        stream.write('\n')
    os.replace(tmp, path)


def tracked(path: Path) -> bool:
    """True when Git would track `path` in this repository (company data must never be)."""
    r = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(path)], capture_output=True)
    return r.returncode != 0 and str(path.resolve()).startswith(str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--dates', nargs='+', required=True)
    ap.add_argument('--raw', type=Path, default=ROOT / '.local' / 'ontology' / 'alert-cards')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--shape-only', action='store_true')
    ap.add_argument('--skip-done', action='store_true', help='skip alerts whose rows are already saved')
    a = ap.parse_args(argv)
    if any(not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) for d in a.dates):
        print('dates: YYYY-MM-DD (Manila)', file=sys.stderr)
        return 2
    alerts = [x for x in select_alerts(a.data, a.dates) if not a.only or x['key'] in a.only]
    if a.list:
        for x in alerts:
            print(x['key'], x['region'], x['direction'], x['first'], x['last'], 'peak', x['interval_manila'])
        print(len(alerts), 'alerts')
        return 0
    if a.dry_run:
        for x in alerts:
            sql, params = ontology.card_query(x['region'], ontology.t_utc_of(x['interval_manila']))
            print(x['key'], bq(sql, params, dry_run=True).strip()[-300:])
        return 0
    out = a.data.joinpath(*ontology.CARD_DIR)
    if tracked(out / 'x.json') or tracked(a.raw / 'x.json'):
        print('refusing to write company data into a path Git would track', file=sys.stderr)
        return 2
    a.raw.mkdir(parents=True, exist_ok=True)
    os.chmod(a.raw, 0o700)
    failed = 0
    if not a.shape_only:
        todo = [x for x in alerts if not (a.skip_done and (a.raw / f"{x['key']}.json").exists())]

        def one(x):
            try:
                sql, params = ontology.card_query(x['region'], ontology.t_utc_of(x['interval_manila']))
                write_private(a.raw / f"{x['key']}.json", {'alert': {k: x[k] for k in (
                    'key', 'region', 'region_label', 'direction', 'interval_manila')}, 'rows': parse_rows(bq(sql, params))})
                return x['key'], None
            except Exception as exc:  # one alert's failure leaves the others
                return x['key'], str(exc)
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
            for key, err in pool.map(one, todo):
                print(key, 'ok' if err is None else 'FAILED: ' + err, flush=True)
                failed += err is not None
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    for x in alerts:
        try:
            saved = json.loads((a.raw / f"{x['key']}.json").read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        card = ontology.shape(saved['rows'], x)
        bad = ontology.problems(card)
        if bad:
            print(x['key'], 'not written:', '; '.join(bad), file=sys.stderr)
            failed += 1
            continue
        (out / f"{x['key']}.json").write_text(json.dumps(card, ensure_ascii=False, allow_nan=False, indent=1) + '\n',
                                             encoding='utf-8')
        written += 1
    print(f'wrote {written} of {len(alerts)} alert cards to {out}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
