"""Read the build stamp one half of the site names, for deploy.sh's split-site checks (DATA-2).

The site is two releases: the Cloud Run image, which serves every page and data file under the
stamp it derives from its baked data and design files, and the Hosting stage, which serves the
first screen under the stamp the stager derived from build/grid-data and src/grid. On
2026-10-18 the two came from two different bakes and nothing noticed. deploy.sh now reads the
stamp each half names and refuses a release where they differ:

    read_stamp.py config FILE   the generated Hosting config: the one stamp its stamped header
                                rules (/grid/<stamp>/**, /grid-data/<stamp>/**) carry
    read_stamp.py health        stdin is a /health answer (JSON): its "stamp"
    read_stamp.py page          stdin is the grid page: its nowcast-build meta element's content

It prints the 16-hex stamp and exits 0, or names what it could not read on stderr and exits 1,
so the caller fails closed instead of comparing against nothing. No network call: the caller
fetches, this module only reads.
"""
import json
import re
import sys

STAMP = re.compile(r'[0-9a-f]{16}\Z')
RULE = re.compile(r'/grid(?:-data)?/([0-9a-f]{16})/\*\*\Z')
META = re.compile(r'<meta\b[^>]*\bid="nowcast-build"[^>]*>', re.IGNORECASE)
CONTENT = re.compile(r'\bcontent="([^"]*)"')


class StampError(Exception):
    pass


def from_config(text):
    try:
        config = json.loads(text)
        headers = config['hosting']['headers']
    except (ValueError, KeyError, TypeError):
        raise StampError('the Hosting config is not JSON with hosting.headers') from None
    stamps = {match.group(1) for rule in headers if isinstance(rule, dict)
              for match in [RULE.fullmatch(str(rule.get('source', '')))] if match}
    if len(stamps) != 1:
        raise StampError('the Hosting config names %s stamps in its header rules, not one'
                         % (len(stamps) or 'no'))
    return stamps.pop()


def from_health(text):
    try:
        body = json.loads(text)
    except ValueError:
        raise StampError('the /health answer is not JSON') from None
    stamp = body.get('stamp') if isinstance(body, dict) else None
    if not isinstance(stamp, str) or not STAMP.match(stamp):
        raise StampError('the /health answer names no build stamp (stamp: %r); the service '
                         'runs an image from before DATA-2 or no bake' % (stamp,))
    return stamp


def from_page(text):
    meta = META.search(text)
    content = CONTENT.search(meta.group(0)) if meta else None
    stamp = content.group(1) if content else None
    if stamp is None or not STAMP.match(stamp):
        raise StampError('the page carries no nowcast-build stamp (%r)' % (stamp,))
    return stamp


def main(argv):
    try:
        if len(argv) == 2 and argv[0] == 'config':
            with open(argv[1], encoding='utf-8') as handle:
                stamp = from_config(handle.read())
        elif len(argv) == 1 and argv[0] == 'health':
            stamp = from_health(sys.stdin.read())
        elif len(argv) == 1 and argv[0] == 'page':
            stamp = from_page(sys.stdin.read())
        else:
            print('usage: read_stamp.py config FILE | health | page', file=sys.stderr)
            return 2
    except (OSError, StampError) as exc:
        print('read_stamp.py: %s' % exc, file=sys.stderr)
        return 1
    print(stamp)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
