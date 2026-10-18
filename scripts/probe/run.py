#!/usr/bin/env python3
"""Prepare offline by default; --config selects an explicitly authorized fictional live run."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.systemone.run import load_config, prepare_probe, run_case, write_private_json
from src.judgment import JudgmentUnavailable


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Trusted local service/case/request-bound authorization JSON; never a source record')
    args = parser.parse_args(argv)
    output_root = ROOT / '.local/probe'
    try:
        if args.config is None:
            path = output_root / 'prepared.json'
            write_private_json(path, prepare_probe())
            result = {'status': 'offline_preparation', 'inference_performed': False, 'artifact': str(path)}
        else:
            config = load_config(args.config)
            status = run_case(config, output_root)['status']
            result = {'status': status, 'synthetic_case': True,
                'artifact': str(output_root / config.run_id / 'result.json')}
        print(json.dumps(result))
        return 0
    except JudgmentUnavailable as exc:
        print(json.dumps({'status': exc.code, 'inference_verified': False}))
        return 1
    except (OSError, ValueError, UnicodeError):
        print(json.dumps({'status': 'LOCAL_RUN_UNAVAILABLE', 'inference_verified': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
