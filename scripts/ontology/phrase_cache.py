"""A cache of verified AI phrasings (ericka-desk events-ai), so an unchanged request is never sent twice.

The key is the SHA-256 of the canonical JSON of four things: the composed facts text, the prompt
version, the model id and the generation config. Any change to a fact changes the composed text and so
the key; a changed prompt, model or config does too. Only a phrasing that passed ``phrase_card.verify``
is stored; ``get`` returns that saved record or None. Records live under the ignored ``.local/``
(they hold model output over company data: never in Git), one file per key, mode 0600.

No network: this module reads and writes local files only. The config must not carry a secret; a key
whose name looks like one (token, credential, secret, password, authorization) is refused.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / '.local' / 'ontology' / 'gemini' / 'cache'
KEY = re.compile(r'[0-9a-f]{64}\Z')
SECRETISH = re.compile(r'(?:^|_)(?:token|credential\w*|secret|password|authori[sz]ation\w*|api_?key)(?:$|_)', re.I)


def cache_key(composed_text: str, prompt_version, model_id: str, config: dict) -> str:
    if not isinstance(composed_text, str) or not composed_text:
        raise ValueError('composed text required')
    if not isinstance(model_id, str) or not model_id:
        raise ValueError('model id required')
    if not isinstance(config, dict):
        raise ValueError('config must be a dict')
    bad = sorted(k for k in config if SECRETISH.search(str(k)))
    if bad:
        raise ValueError(f'config keys look like secrets and are not keyed: {bad}')
    raw = json.dumps({'text': composed_text, 'prompt_version': prompt_version, 'model': model_id,
                      'config': config}, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class PhraseCache:
    def __init__(self, directory: Path | str = DEFAULT_DIR):
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise ValueError('not a cache key')
        return self.directory / f'{key}.json'

    def get(self, key: str):
        """The saved verified record for `key`, or None (absent, unreadable or not verified)."""
        path = self._path(key)  # a malformed key is a caller error, raised, not a miss
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        if not isinstance(record, dict) or record.get('key') != key or record.get('problems') != [] \
                or not isinstance(record.get('text'), str):
            return None
        return record

    def put(self, key: str, text: str, problems: list, **extra) -> bool:
        """Store a verified phrasing; a phrasing with problems is not stored (returns False)."""
        path = self._path(key)
        if problems or not isinstance(text, str) or not text.strip():
            return False
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.directory, 0o700)
        except OSError:
            pass
        record = dict(extra, key=key, text=text, problems=[])
        tmp = path.with_suffix('.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, indent=1, ensure_ascii=False)
            stream.write('\n')
        os.replace(tmp, path)
        return True
