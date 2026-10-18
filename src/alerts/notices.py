"""The operator notices around a replay alert, never claimed as its cause (ericka-desk).

An alert only has a cause when a recorded event explains it (src/alerts/replay.py). Most alerts
have none, so the desk also lists the region's outage, trip and grid-alert notices around the
alert, each with how sure the plant match is and why. Owner rule: under 50% sure a name matches,
it is not matched; the uncertainty is flagged and shown. So a notice here is "around this alert
(not a confirmed cause)", never the cause.

The naming, kind, clock and scoring rules are the ones the event-candidates script uses
(scripts/grid/event_candidates.py imports them from here), which port the page's own rules
(src/grid/asset.js hitsFor, src/grid/shell.js opText):

* a notice names a plant when one of the plant code's letter groups (three letters or more) is a
  whole word of its text, the numbers agree, and no other plant of the notice's grid fits it;
  two or more fits are Unclear, no plant is picked;
* a unit notice (trip, forced shutdown, derating) is scored by the stated trigger rule (`score`);
  under MATCH_AT it is said to be under it; at or over it, no event is recorded, so it is still
  not a confirmed cause;
* nothing posted after the replay clock is used (no look-ahead); technology words are withheld
  from the text; no peso figure, no forecast.

`NoticeIndex` reads every notice once per bake and keeps each region's candidates in time order,
so an alert's list is two bisects, not a scan.
"""
import bisect
import re
from datetime import datetime, timedelta

LOOKBACK_MINUTES = 120  # the trigger rule's window before the first interval
MATCH_AT = 0.5
AROUND_MINUTES = 360  # the notices listed: from six hours before the first interval to the last
MAX_LISTED = 20

REGION_NAMES = {'CLUZ': 'Luzon', 'CVIS': 'Visayas', 'CMIN': 'Mindanao'}
REGION_OF_NAME = {v.lower(): k for k, v in REGION_NAMES.items()}

# The page's own rules (src/grid/asset.js, src/grid/shell.js: same expressions).
TECH_WORDS = re.compile(r'\b(?:geo-?thermal\w*|thermal|solar|photo-?voltaic|pv|hydro\w*|hepp?|coal(?:-fired)?|'
                        r'diesel|bunker|fuel|oil|gas|lng|ccgt|combined[- ]cycle|wind|biomass|bio\w*|battery|bess|'
                        r'nuclear|pumped[- ]storage|steam|hfo|cfpp|[dgsw]ppi?)\b', re.I)
EQUIPMENT = re.compile(r'\b(?:line|l\d|tr\d*|transformer|substation|ss|svc|hvdc|capacitor|reactor|bus|breaker)\b', re.I)
# A forced shutdown or going off-line is a unit outage like a trip; a reserve shutdown is not.
SHUTDOWN = re.compile(r'\b(?:shut\s*down|shutdown|off-?line|cut-?out)\b', re.I)
RESERVE = re.compile(r'\breserved?\s+shut\s*down\b', re.I)
UNPLANNED = re.compile(r'\b(?:unplanned|forced?|emergency)\b', re.I)
EVENT_CLOCK = re.compile(r'\bat\s+([01]\d|2[0-3])([0-5]\d)H?\b')
MW = re.compile(r'(\d+(?:\.\d+)?)\s*MW\b', re.I)
# Grid equipment out of service (not a return): tripped or de-energized.
EQUIPMENT_OUT = re.compile(r'\b(?:auto-?)?tripped\b|\bde-?energi[sz]ed\b', re.I)
# An interconnection notice: "Ormoc-Naga 350kV HVDC (Visayas-Luzon) blocked at 0903H ...".
LINK = re.compile(r'\bHVDC\b[^()]*\((Luzon|Visayas|Mindanao)\s*-\s*(Luzon|Visayas|Mindanao)\)', re.I)
LINK_OUT = re.compile(r'(?<![-\w])(?:auto-?)?blocked\b', re.I)

KIND_LABEL = {'trip': 'Unit trip', 'shutdown': 'Forced shutdown', 'derate': 'Derating',
              'equipment': 'Grid equipment out', 'link': 'Interconnection blocked',
              'grid_alert': 'Grid alert', 'load_drop': 'Load dropping'}
UNIT_KINDS = ('trip', 'shutdown', 'derate')
RULE = ('Listed: the region\'s unit trips, forced shutdowns, deratings, grid equipment out, interconnection '
        'blocks and grid alerts from six hours before the alert\'s first interval to its last, posted by the '
        'replay time. A notice names a plant when the plant code\'s letters appear in its text and no other '
        'plant of that grid fits; two or more fits are Unclear and no plant is picked. None is a confirmed cause.')


def withheld(text):
    out = TECH_WORDS.sub('[…]', str(text or ''))
    return re.sub(r'\[…\](?:[\s-]*\[…\])+', '[…]', out)


def op_text(text):
    """shell.js opText: technology words withheld, 1334H -> 13:34, runs of spaces collapsed."""
    out = re.sub(r'\b([01]\d|2[0-3])([0-5]\d)H\b', r'\1:\2', withheld(text))
    return re.sub(r'\s{2,}', ' ', out)


def site_tokens(code):
    return [t.upper() for t in re.findall(r'[A-Za-z]{3,}', str(code))]


def digits_agree(code, up):
    """Stricter than the page: a code whose letters carry a number (06PGPP2) does not name a text that
    writes the same letters with another number (PGPP1); that plant is not the one named."""
    for letters, number in re.findall(r'([A-Za-z]{3,})(\d+)', code[2:] if code[:2].isdigit() else code):
        for m in re.finditer('(?:^|[^A-Z])' + re.escape(letters.upper()) + r'(\d+)', up):
            if m.group(1) != number:
                return False
    return True


def token_table(sites):
    """{grid: {token: [site code, ...]}} for `named_sites`; built once per site list."""
    table = {}
    for s in sites or []:
        if not isinstance(s, dict) or not s.get('s'):
            continue
        for t in set(site_tokens(s['s'])):
            table.setdefault(s.get('g'), {}).setdefault(t, []).append(str(s['s']))
    return table


def named_sites(text, grid, sites, table=None):
    """asset.js hitsFor: the sites of `grid` one of whose letter groups is a whole word of the text
    (a maximal run of letters A to Z in the upper-cased text), and whose numbers agree. In site-list order."""
    table = token_table(sites) if table is None else table
    up = str(text).upper()
    words = set(re.findall(r'[A-Z]+', up))
    grid_table = table.get(grid) or {}
    found = {code for w in words for code in grid_table.get(w, ())}
    if not found:
        return []
    order = [str(s['s']) for s in sites or [] if isinstance(s, dict) and s.get('s') in found] if sites is not None \
        else sorted(found)
    return [code for code in order if digits_agree(code, up)]


def unit_kind(notice):
    """trip, derate or shutdown for a notice about a unit; None for grid equipment or anything else."""
    text = notice['text']
    if EQUIPMENT.search(text):
        return None
    if notice['kind'] == 'trip':
        return 'trip'
    if re.search(r'derat', text, re.I):
        return 'derate'
    if SHUTDOWN.search(text) and not RESERVE.search(text) and UNPLANNED.search(text):
        return 'shutdown'
    return None


def link_regions(text):
    """The two regions an interconnection notice names, or ()."""
    m = LINK.search(str(text))
    return tuple(sorted({REGION_OF_NAME[m.group(1).lower()], REGION_OF_NAME[m.group(2).lower()]})) if m else ()


def notice_kind(notice):
    """What the list calls a notice (KIND_LABEL), or None for a return, a weather note or anything else.
    The unit kinds are `unit_kind`'s; the rest are the region-wide or equipment ones."""
    unit = unit_kind(notice)
    if unit:
        return unit
    kind, text = notice.get('kind'), str(notice.get('text') or '')
    if kind in ('yellow', 'red'):
        return 'grid_alert'
    if kind == 'mld':
        return 'load_drop'
    if link_regions(text):
        return 'link' if LINK_OUT.search(text) else None
    if EQUIPMENT.search(text) and (kind == 'trip' or EQUIPMENT_OUT.search(text)):
        return 'equipment'
    return None


def event_time(notice):
    """The clock the text gives ("at 1334H"), on the posting day or the day before; else the posting minute."""
    posted = notice['t']
    m = EVENT_CLOCK.search(notice['text'])
    if not m:
        return posted
    t = f'{posted[:10]}T{m.group(1)}:{m.group(2)}'
    if t > posted:
        t = (datetime.fromisoformat(t) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
    return t


def minutes_between(a, b):
    return int((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() // 60)


def plus(t, minutes):
    return (datetime.fromisoformat(t) + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M')


def ceil5(t):
    d = datetime.fromisoformat(t[:16])
    if d.minute % 5 or len(t) > 16 and t[17:19] not in ('', '00'):
        d = d.replace(second=0) + timedelta(minutes=5 - d.minute % 5)
    return d.strftime('%Y-%m-%dT%H:%M')


def score(alert, notice, others, unclear, short_before, short_at):
    """(confidence, [reasons]) for one named unit notice before an alert. The rule, stated:

    0.35 a unit trip, forced shutdown or derating, named to exactly one plant of the region, before
         the alert; + timing: 0.25 within 30 minutes of the first interval, 0.15 within 60, 0.05 within 120;
    + 0.10 the notice states 50 MW or more; + 0.10 the reserve shortfall at the alert's first interval is
    larger than at the notice's interval; - 0.15 for each other named unit notice in the same window and
    - 0.10 for each notice in the window that fits two or more plants (each could be the trigger instead).
    """
    lag = minutes_between(notice['event_t'], alert['first'])
    reasons = [f"{notice['kind']} named to one plant of the region ({notice['site']})"]
    conf = 0.35
    if lag <= 30:
        conf += 0.25
        reasons.append(f'{lag} minutes before the first interval')
    elif lag <= 60:
        conf += 0.15
        reasons.append(f'{lag} minutes before the first interval')
    else:
        conf += 0.05
        reasons.append(f'{lag} minutes before the first interval (weak timing)')
    mw = [float(x) for x in MW.findall(notice['raw'])]
    if mw and max(mw) >= 50:
        conf += 0.10
        reasons.append(f'notice states {max(mw):g} MW')
    if type(short_before) in (int, float) and type(short_at) in (int, float) and short_at > short_before:
        conf += 0.10
        reasons.append(f'reserve shortfall rose from {short_before:,.0f} to {short_at:,.0f} MW (WESM RTD)')
    if others:
        conf -= 0.15 * others
        reasons.append(f'{others} other named unit notice(s) in the same window')
    if unclear:
        conf -= 0.10 * unclear
        reasons.append(f'{unclear} notice(s) in the window fit two or more plants')
    return round(max(conf, 0.0), 2), reasons


class NoticeIndex:
    """Each region's listable notices, matched once, in event-time order.

    advisories: the bake's notices as Replay reads them ([{t, id, grid, kind, text}], oldest first).
    sites: sites.json's list, or None when it could not be read (then no notice is matched to a plant:
    each unit or equipment notice is Unclear). events: events.json's index (an event that names a notice
    maps it to its site, as asset.js does).
    """

    def __init__(self, advisories, sites, events=()):
        self.sites_read = isinstance(sites, list)
        table = token_table(sites) if self.sites_read else {}
        known = {str(s.get('s')) for s in sites or [] if isinstance(s, dict)}
        by_notice = {}
        for e in events or []:
            if isinstance(e, dict) and e.get('advisory') and e.get('site') in known:
                by_notice.setdefault(str(e['advisory']), str(e['site']))
        self.by_region = {code: [] for code in REGION_NAMES}
        seen = {code: set() for code in REGION_NAMES}
        for a in advisories or []:
            kind = notice_kind(a)
            if kind is None:
                continue
            raw = a['text']
            n = {'id': a['id'], 'grid': a['grid'], 'posted': a['t'], 'event_t': event_time(a), 'kind': kind,
                 'raw': raw, 'text': op_text(raw)}
            if kind in ('link', 'grid_alert', 'load_drop'):
                n.update(hits=[], how='region')
            elif a['id'] in by_notice:
                n.update(hits=[by_notice[a['id']]], how='event record')
            elif not self.sites_read:
                n.update(hits=[], how='no sites')
            else:
                n['hits'] = named_sites(raw, a['grid'], sites, table)
                n['how'] = 'code' if len(n['hits']) == 1 else 'unclear' if n['hits'] else 'none'
            n['site'] = n['hits'][0] if n['how'] in ('code', 'event record') else None
            regions = set(link_regions(raw)) if kind == 'link' else set()
            regions.add(a['grid'])
            for code in regions:
                if code not in self.by_region:
                    continue
                key = (n['event_t'], n['text'])  # one link notice is filed under both of its regions
                if key in seen[code]:
                    continue
                seen[code].add(key)
                self.by_region[code].append(n)
        for code, rows in self.by_region.items():
            rows.sort(key=lambda n: (n['event_t'], n['posted'], n['id']))
        self.times = {code: [n['event_t'] for n in rows] for code, rows in self.by_region.items()}

    def around(self, alert, at, series=None, times=None):
        """The notices around one alert as the page lists them, with counts; nothing posted after `at`.

        alert: {region, region_label?, direction, first, last}. series/times: the region's replay series and
        the interval axis, for the trigger rule's reserve figures (None leaves them out of the score)."""
        code = alert['region']
        rows = self.by_region.get(code) or []
        lo_t = plus(alert['first'], -AROUND_MINUTES)
        hi_t = min(alert['last'], at) if at else alert['last']
        ts = self.times.get(code) or []
        window = [n for n in rows[bisect.bisect_left(ts, lo_t):bisect.bisect_right(ts, hi_t)]
                  if n['posted'] <= (at or n['posted'])]
        spike = alert.get('direction') != 'collapse'
        start = plus(alert['first'], -LOOKBACK_MINUTES)
        before = [n for n in window if n['kind'] in UNIT_KINDS and start <= n['event_t'] <= alert['first']]
        named = [n for n in before if n['site']]
        unclear_before = [n for n in before if len(n['hits']) > 1]
        def index(t):  # the interval axis is in time order: a bisect, not a table per alert
            if times is None or series is None:
                return None
            i = bisect.bisect_left(times, t)
            return i if i < len(times) and times[i] == t else None
        region = REGION_NAMES.get(code, code)
        items = []
        for n in window:
            item = {'t': n['event_t'], 'posted': n['posted'], 'id': n['id'], 'filed_under': n['grid'],
                    'kind': n['kind'], 'kind_label': KIND_LABEL[n['kind']], 'text': n['text'],
                    'timing': 'during' if n['event_t'] >= alert['first'] else 'before',
                    'plant': None, 'plant_href': None, 'claimed': False,
                    'notice_href': f"/notices?at={n['posted'][:16]}#adv-{n['id']}"}
            if n['kind'] == 'equipment' and n['how'] in ('code', 'unclear'):
                # A line or transformer names the stations at its ends; a station sharing a plant's
                # code letters is not shown to be that plant (owner rule: no uncertain match).
                codes = ', '.join(n['hits'][:5]) + (f" and {len(n['hits']) - 5} more" if len(n['hits']) > 5 else '')
                item.update(match='unclear', match_label='Unclear',
                            reason=f"Grid equipment (a line, transformer or substation) at a place whose name fits "
                                   f"{codes}; a station is not shown to be the plant, so no plant is matched")
            elif n['how'] in ('code', 'event record'):
                item.update(match='plant', match_label='Names a plant in this region', plant=n['site'],
                            plant_href='/plant/' + n['site'],
                            reason=(f"The event record maps it to {n['site']}" if n['how'] == 'event record' else
                                    f"Its text carries {n['site']}'s code letters and no other {region} plant fits"))
            elif n['how'] == 'unclear':
                codes = ', '.join(n['hits'][:5]) + (f" and {len(n['hits']) - 5} more" if len(n['hits']) > 5 else '')
                item.update(match='unclear', match_label='Unclear',
                            reason=f"Its words fit {len(n['hits'])} {region} plants ({codes}); no plant is picked")
            elif n['how'] == 'no sites':
                item.update(match='unclear', match_label='Unclear',
                            reason='The plant list could not be read, so no plant is matched')
            elif n['kind'] == 'link':
                pair = '–'.join(REGION_NAMES[c] for c in link_regions(n['raw']))
                item.update(match='link', match_label='Names the link to this region',
                            reason=f'An interconnection notice ({pair}); it names a link, not a plant'
                                   + (f"; filed under {REGION_NAMES.get(n['grid'], n['grid'])}" if n['grid'] != code else ''))
            elif n['kind'] in ('grid_alert', 'load_drop'):
                item.update(match='region', match_label='Region-wide notice',
                            reason=f'A {region} grid notice; it names no plant')
            else:
                item.update(match='none', match_label='Plant not matched',
                            reason=f'No {region} plant code appears in its text; any plant it names by name is not matched')
            if spike and n in named:
                ni, ai = index(ceil5(n['event_t'])), index(alert['first'])
                short = series.get('dr_short_mw') if series else None
                conf, why = score(alert, n, len(named) - 1, len(unclear_before),
                                  short[ni] if short and ni is not None else None,
                                  short[ai] if short and ai is not None else None)
                item['rule_score'] = conf
                item['rule_reasons'] = why
                item['rule_text'] = (f'Trigger rule score {conf:.2f}, under {MATCH_AT:.2f}: not matched' if conf < MATCH_AT
                                     else f'Trigger rule score {conf:.2f} (at least {MATCH_AT:.2f}), but no event is '
                                          'recorded for it: not confirmed')
            items.append(item)
        counts = {'plant': 0, 'unclear': 0, 'link': 0, 'region': 0, 'none': 0}
        for item in items:
            counts[item['match']] += 1
        shown = items[-MAX_LISTED:]  # the ones nearest the alert
        return {'from': lo_t, 'to': hi_t, 'minutes_before': AROUND_MINUTES, 'count': len(items),
                'before': sum(1 for i in items if i['timing'] == 'before'),
                'during': sum(1 for i in items if i['timing'] == 'during'),
                'counts': counts, 'sites_read': self.sites_read, 'shown': len(shown),
                'confirmed': False, 'rule': RULE, 'items': shown}


def driver_text(found):
    """The main-driver line of an alert with no recorded event, from its notices around it."""
    n = found['count'] if found else 0
    if not n:
        return 'None on record: no recorded event explains this alert'
    return (f"None on record; {n} outage, trip or grid notice{'s' if n != 1 else ''} from 6 hours before "
            'to its last interval (not confirmed as the cause)')
