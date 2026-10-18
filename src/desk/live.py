"""Gemini as the desk's planner and writer, held to the records (docs/work/ui-refinement-2026-10-18/desk-api.md).

The loop, bounded: at most four tool rounds, then one final call that writes the answer as JSON in
the `blocks` shape. The tools are the deterministic layer (`answer.py`): each one runs one intent
at the request's own clock (`at` is never a tool argument, so the model cannot move it), and
returns its sentences, its numbered citations with their tables and the entities it named. Each
tool call adds its ontology steps to the trace, so the trace is the path the model chose. An
optional `on_step` callback receives each trace step once its tool call has run (the streaming
route sends it on as it happens); the result is the same with or without it.

The server checks the model's answer before it is returned: every `num` part's figure is in a
table the part cites, every cite resolves, every entity was returned by a tool, a table block is
rebuilt from the citation it names, and a text part carries no figure (clock times aside). Any
failure (a model error, a timeout, a refused budget, an invalid answer, no configuration) returns
None with a reason, and the route serves the recorded run or the composed answer instead.

A recorded run is the same result written by `scripts/desk/record_prompts.py` into the bake
(`desk/recorded/<prompt_id>@<YYYY-MM-DDTHHMM>.json`), checked again by the same rules when served.
"""
import json
import re
import time
from datetime import datetime, timezone

from . import answer as answers
from .bake import AT, GRIDS
from .gemini import PROVIDER, ModelError, request_digest
from .search import search
from .words import MONTHS

MAX_ROUNDS = 4
MAX_CALLS_PER_ROUND = 4
DEADLINE_SECONDS = 20.0
TOOL_TOKENS = 512
FINAL_TOKENS = 2048
MAX_BLOCKS = 12
MAX_TABLE_ROWS = 12
PERMISSION_REF = 'perm:wesm-company-copy:2026-10-13'
LIVE_BASIS = ('Planned and written by Gemini on Vertex AI from the baked records at the replay clock. '
              'Every figure was checked against its cited table.')
RECORDED_BASIS = ('A recorded Gemini run over the baked records at the replay clock. '
                  'Every figure was checked against its cited table.')
TIME_IN_TEXT = re.compile(r'\b\d{1,2}:\d{2}\b|\b\d{1,2} (?:' + '|'.join(MONTHS) + r')\b')
FIGURE = re.compile(r'-?\d[\d,]*(?:\.\d+)?')
RECORDED_NAME = re.compile(r'([a-z0-9][a-z0-9-]{0,80})@(\d{4}-\d{2}-\d{2}T\d{4})\.json\Z')

SYSTEM = (
    'You are the Grid Nowcast desk for the Philippine grid (Luzon, Visayas, Mindanao). Answer the '
    "analyst's question only from tool results. Every tool reads the baked replay at the replay clock, "
    'which you never choose. Call the tools you need, then write the answer. Rules for the answer: '
    '(1) every figure goes in a num part, copied exactly as a tool result prints it, citing the citation '
    'numbers n whose table shows it; (2) text parts carry no digits except clock times such as 13:40; '
    '(3) name plants, regions, HVDC links, events and notices with entity parts, using kind and id from '
    'the tool results; (4) to show a table, add a table block that cites one citation n; (5) short plain '
    'sentences of 20 words or fewer, no em dash, no semicolons; (6) say plainly what is not on record; '
    '(7) never claim a cause: records near a price are on record, not causes.')
FINAL_TURN = ('Write the final answer now as JSON matching the schema. Use only citation numbers and '
              'entity ids from the tool results above.')

GRID_ENUM = {'type': 'STRING', 'enum': list(GRIDS), 'description': 'CLUZ Luzon, CVIS Visayas, CMIN Mindanao'}
# A tool with no argument carries no `parameters` (Vertex refuses an OBJECT with no properties).
TOOLS = [
    {'name': 'search_entities', 'description': 'Find plants, events, regions, HVDC links, notices or datasets by name or code.',
     'parameters': {'type': 'OBJECT', 'properties': {'query': {'type': 'STRING'}}, 'required': ['query']}},
    {'name': 'grid_state', 'description': 'The three grids at the clock: median price, usual, demand, reserve shortfall, net import.'},
    {'name': 'region_price_context',
     'description': "One grid's price against its usual, its HVDC links, notices and events in the last two hours, and its highest-priced locations.",
     'parameters': {'type': 'OBJECT', 'properties': {'grid': GRID_ENUM}, 'required': ['grid']}},
    {'name': 'unusual_nodes', 'description': 'The locations furthest from their grid median at the clock, and notices naming them.'},
    {'name': 'hvdc_state', 'description': 'Both HVDC links: flow, direction, congested state and since when.'},
    {'name': 'plant_status', 'description': "One plant's registered capacity, price, dispatch, and the notices and events naming it.",
     'parameters': {'type': 'OBJECT', 'properties': {'code': {'type': 'STRING', 'description': 'the site code'}},
                    'required': ['code']}},
    {'name': 'recent_notices', 'description': 'Operator notices and events in the last six hours by severity, for one grid or all.',
     'parameters': {'type': 'OBJECT', 'properties': {'grid': GRID_ENUM}}},
]
TOOL_INTENTS = {'grid_state': 'grid_overview', 'region_price_context': 'region_price_why', 'unusual_nodes': 'unusual_nodes',
                'hvdc_state': 'hvdc_congestion', 'plant_status': 'plant_status', 'recent_notices': 'recent_events'}
PART_SCHEMA = {'type': 'object', 'properties': {
    't': {'type': 'string', 'enum': ['text', 'num', 'entity']}, 'v': {'type': 'string'},
    'cite': {'type': 'array', 'items': {'type': 'integer'}}, 'kind': {'type': 'string'}, 'id': {'type': 'string'}},
    'required': ['t']}
ANSWER_SCHEMA = {'type': 'object', 'properties': {'blocks': {'type': 'array', 'maxItems': MAX_BLOCKS, 'items': {
    'type': 'object', 'properties': {
        'type': {'type': 'string', 'enum': ['p', 'table']},
        'parts': {'type': 'array', 'items': PART_SCHEMA},
        'caption': {'type': 'string'},
        'cite': {'type': 'array', 'items': {'type': 'integer'}}},
    'required': ['type']}}}, 'required': ['blocks']}


class Invalid(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


# ------------------------------------------------------------------------------- the tools

class Ledger:
    """What the tools have returned so far: citations (numbered 1..n), their rows, entities, trace."""

    def __init__(self, bake, at, question, on_step=None):
        self.bake, self.at, self.question = bake, at, question
        self.citations, self.rows, self.entities, self.trace = [], {}, {}, []
        self.calls = 0
        self.on_step = on_step

    def add(self, steps):
        """Steps of a tool call that has run: onto the trace, then to `on_step` (never before)."""
        for step in steps:
            self.trace.append(step)
            if self.on_step is not None:
                self.on_step(step)

    def merge(self, c):
        offset = len(self.citations)
        for citation in c.citations:
            self.citations.append(dict(citation, n=citation['n'] + offset))
            self.rows[citation['n'] + offset] = c.rows.get(citation['n'], [])
        for key, entity in c._entities.items():
            self.entities.setdefault(key, entity)
        self.add(c.trace)
        return offset

    def run(self, name, args):
        """One tool call: the deterministic layer at the request's clock; a compact result."""
        self.calls += 1
        args = args if isinstance(args, dict) else {}
        if name == 'search_entities':
            query = str(args.get('query') or '')[:80]
            found = search(self.bake, query, self.at, limit=4)
            items = [i for g in found['groups'] for i in g['items'] if g['kind'] != 'page']
            for i in items:
                key = (i['kind'], i['id'])
                self.entities.setdefault(key, {'kind': i['kind'], 'id': i['id'], 'label': i['title'], 'href': i['href']})
            self.add([{'op': 'resolve', 'label': f'Looked up "{query}"', 'rows': len(items)}])
            return {'entities': [{'kind': i['kind'], 'id': i['id'], 'label': i['title'], 'subtitle': i['subtitle']}
                                 for i in items]}
        intent = TOOL_INTENTS.get(name)
        if intent is None:
            return {'error': 'unknown tool'}
        entity = None
        if intent in ('region_price_why', 'recent_events'):
            entity = args.get('grid') if args.get('grid') in GRIDS else None
            if intent == 'region_price_why' and entity is None:
                return {'error': 'grid must be one of CLUZ, CVIS, CMIN'}
        if intent == 'plant_status':
            entity = str(args.get('code') or '')
            if self.bake.site(entity) is None:
                return {'error': 'no plant with that code; try search_entities'}
        c = answers.compose(self.bake, self.at, self.question, intent, entity, with_followups=False)
        offset = self.merge(c)
        return {'summary': _flatten(c, offset),
                'citations': [{'n': x['n'] + offset, 'title': x['title'], 'filter': x['filter'],
                               'columns': x['table']['columns'], 'rows': x['table']['rows'][:MAX_TABLE_ROWS]}
                              for x in c.citations],
                'entities': [{'kind': e['kind'], 'id': e['id'], 'label': e['label']} for e in c._entities.values()]}


def _flatten(c, offset):
    out = []
    for block in c.blocks:
        if block['type'] == 'p':
            words = []
            for part in block['parts']:
                if part['t'] == 'num':
                    words.append(part['v'] + ' [' + ','.join(str(n + offset) for n in part['cite']) + ']')
                elif part['t'] == 'entity':
                    words.append(f"{part['label']} {{{part['kind']}:{part['id']}}}")
                else:
                    words.append(part['v'])
            out.append(''.join(words))
        else:
            out.append(f"Table [{','.join(str(n + offset) for n in block['cite'])}]: {block['caption']}")
    return ' '.join(out)


# ------------------------------------------------------------------------------- validation

def _clean_text(value):
    if type(value) is not str or len(value) > 600:
        raise Invalid('text_shape')
    text = value.replace('—', ', ').replace(';', '.')
    if FIGURE.search(TIME_IN_TEXT.sub('', text)):
        raise Invalid('figure_in_text')
    return text


def _cells(citation):
    return {cell for row in citation['table']['rows'] for cell in row}


def normalise(raw, ledger):
    """The model's blocks, checked against the ledger and rebuilt in the contract's shape."""
    if type(raw) is not dict or type(raw.get('blocks')) is not list or not raw['blocks']:
        raise Invalid('no_blocks')
    by_n = {c['n']: c for c in ledger.citations}
    blocks = []
    for block in raw['blocks'][:MAX_BLOCKS]:
        if type(block) is not dict:
            raise Invalid('block_shape')
        if block.get('type') == 'table':
            cite = block.get('cite')
            if type(cite) is not list or len(cite) != 1 or cite[0] not in by_n:
                raise Invalid('table_cite')
            n = cite[0]
            try:
                caption = _clean_text(block.get('caption')) if block.get('caption') else by_n[n]['filter']
            except Invalid:  # a caption is the model's words: one with a figure gives way to the record's own
                caption = by_n[n]['filter']
            blocks.append({'type': 'table', 'caption': caption, 'columns': by_n[n]['table']['columns'],
                           'rows': ledger.rows[n], 'cite': [n]})
            continue
        if block.get('type') != 'p' or type(block.get('parts')) is not list or not block['parts']:
            raise Invalid('block_shape')
        parts = []
        for part in block['parts']:
            kind = part.get('t') if type(part) is dict else None
            if kind == 'text':
                parts.append({'t': 'text', 'v': _clean_text(part.get('v'))})
            elif kind == 'num':
                value, cite = part.get('v'), part.get('cite')
                if type(value) is not str or len(value) > 40 or type(cite) is not list or not cite:
                    raise Invalid('num_shape')
                if any(type(n) is not int or n not in by_n for n in cite):
                    raise Invalid('cite_unresolved')
                figure = FIGURE.search(value)
                if figure is None or not any(figure.group(0) in _cells(by_n[n]) for n in cite):
                    raise Invalid('figure_not_in_citation')
                number = float(figure.group(0).replace(',', ''))
                parts.append({'t': 'num', 'v': value, 'n': int(number) if number.is_integer() else number,
                              'cite': list(cite)})
            elif kind == 'entity':
                key = (part.get('kind'), part.get('id'))
                if key not in ledger.entities:
                    raise Invalid('entity_unknown')
                e = ledger.entities[key]
                parts.append({'t': 'entity', 'kind': e['kind'], 'id': e['id'], 'label': e['label']})
            else:
                raise Invalid('part_shape')
        blocks.append({'type': 'p', 'parts': parts})
    return blocks


def check(result):
    """The served answer's own consistency (a live result and a recorded file alike)."""
    by_n = {c['n']: c for c in result.get('citations') or []}
    entities = {(e['kind'], e['id']) for e in result.get('entities') or []}
    for block in result.get('blocks') or []:
        if block.get('type') == 'table':
            if not block.get('cite') or any(n not in by_n for n in block['cite']):
                raise Invalid('table_cite')
            cited = set().union(*(_cells(by_n[n]) for n in block['cite']))
            for row in block['rows']:
                for cell in row:
                    if isinstance(cell, dict):
                        if (cell.get('kind'), cell.get('id')) not in entities:
                            raise Invalid('entity_unknown')
                    elif cell not in cited:
                        raise Invalid('cell_not_in_citation')
            continue
        for part in block.get('parts') or []:
            if part['t'] == 'num':
                if not part.get('cite') or any(n not in by_n for n in part['cite']):
                    raise Invalid('cite_unresolved')
                figure = FIGURE.search(part['v'])
                if figure is None or not any(figure.group(0) in _cells(by_n[n]) for n in part['cite']):
                    raise Invalid('figure_not_in_citation')
            elif part['t'] == 'entity':
                if (part['kind'], part['id']) not in entities:
                    raise Invalid('entity_unknown')
            elif part['t'] == 'text':
                _clean_text(part['v'])
    return result


# ------------------------------------------------------------------------------- the loop

def _generation(tokens, schema=None):
    config = {'candidateCount': 1, 'maxOutputTokens': tokens, 'temperature': 0,
              # Vertex bills hidden thinking against maxOutputTokens unless pinned to zero
              # (src/judgment/view.py): unpinned, a bounded request ends at MAX_TOKENS.
              'thinkingConfig': {'thinkingBudget': 0}}
    if schema is not None:
        config['responseFormat'] = {'text': {'mimeType': 'APPLICATION_JSON', 'schema': schema}}
    return config


def _content(response):
    candidates = response.get('candidates') if isinstance(response, dict) else None
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise ModelError('MODEL_INVALID_RESPONSE')
    content = candidates[0].get('content')
    if not isinstance(content, dict) or not isinstance(content.get('parts'), list):
        raise ModelError('MODEL_INVALID_RESPONSE')
    return content


def _usage(response, tokens):
    usage = response.get('usageMetadata') if isinstance(response, dict) else None
    if isinstance(usage, dict):
        for key, name in (('in', 'promptTokenCount'), ('out', 'candidatesTokenCount')):
            if type(usage.get(name)) is int and usage[name] >= 0:
                tokens[key] += usage[name]


def run(bake, at, question, page, client, config, meter=None, clock=time.monotonic, deadline=DEADLINE_SECONDS,
        on_step=None):
    """`(result, None)` for a checked live answer, or `(None, reason)`; never raises.

    `on_step(step)`, when given, is called with each trace step as its tool call completes, in
    trace order. A callback that raises ends the run like any other failure (`model_unavailable`).
    """
    started = clock()
    tokens = {'in': 0, 'out': 0}
    bodies, version = [], None
    ledger = Ledger(bake, at, question, on_step)

    def call(body):
        nonlocal version
        if meter is not None:
            outcome = meter.charge(1)
            if outcome.get('refused'):
                raise ModelError(outcome.get('reason_key') or 'budget_exhausted')
        remaining = deadline - (clock() - started)
        if remaining < 0.5:
            raise ModelError('MODEL_TIMEOUT')
        bodies.append(body)
        response = client(body, min(remaining, deadline))
        if clock() - started > deadline:
            raise ModelError('MODEL_TIMEOUT')
        _usage(response, tokens)
        if isinstance(response, dict) and isinstance(response.get('modelVersion'), str):
            version = response['modelVersion'][:80]
        return response

    contents = [{'role': 'user', 'parts': [{'text': json.dumps(
        {'question': question, 'replay_clock': at, 'page': page or None}, ensure_ascii=False)}]}]
    system = {'parts': [{'text': SYSTEM}]}
    try:
        for _ in range(MAX_ROUNDS):
            response = call({'systemInstruction': system, 'contents': contents,
                             'tools': [{'functionDeclarations': TOOLS}],
                             'toolConfig': {'functionCallingConfig': {'mode': 'AUTO'}},
                             'generationConfig': _generation(TOOL_TOKENS)})
            content = _content(response)
            asked = [p['functionCall'] for p in content['parts']
                     if isinstance(p, dict) and isinstance(p.get('functionCall'), dict)]
            if not asked:
                break
            # the model's own turn goes back as it came (Gemini's thought signatures included)
            contents.append({'role': 'model', 'parts': content['parts']})
            replies = []
            for fc in asked[:MAX_CALLS_PER_ROUND]:
                name = str(fc.get('name') or '')
                replies.append({'functionResponse': {'name': name, 'response': ledger.run(name, fc.get('args'))}})
            for fc in asked[MAX_CALLS_PER_ROUND:]:
                replies.append({'functionResponse': {'name': str(fc.get('name') or ''),
                                                     'response': {'error': 'too many calls in one round'}}})
            contents.append({'role': 'user', 'parts': replies})
        if ledger.calls == 0:
            return None, 'no_tool_call'
        contents.append({'role': 'user', 'parts': [{'text': FINAL_TURN}]})
        final = call({'systemInstruction': system, 'contents': contents,
                      'generationConfig': _generation(FINAL_TOKENS, ANSWER_SCHEMA)})
        text = ''.join(p.get('text', '') for p in _content(final)['parts'] if isinstance(p, dict))
        try:
            raw = json.loads(text)
        except ValueError:
            return None, 'invalid_json'
        blocks = normalise(raw, ledger)
    except ModelError as exc:
        return None, exc.code.lower()
    except Invalid as exc:
        return None, exc.reason
    except Exception:  # noqa: BLE001 - a live failure is a fallback, never an error page
        return None, 'model_unavailable'
    used = {(p['kind'], p['id']) for b in blocks for p in b.get('parts', []) if p['t'] == 'entity'}
    used |= {(c['kind'], c['id']) for b in blocks if b['type'] == 'table' for row in b['rows'] for c in row
             if isinstance(c, dict)}
    intent, _ = answers.match(bake, question)
    result = {'status': 'answered', 'question': question, 'at': at, 'intent': intent, 'trace': ledger.trace,
              'blocks': blocks, 'citations': ledger.citations,
              'entities': [e for k, e in ledger.entities.items() if k in used],
              'followups': [{'text': p['text'], 'prompt_id': p['id']} for p in answers.prompts(bake, at, page)][:3],
              'basis': LIVE_BASIS}
    try:
        check(result)
    except Invalid as exc:
        return None, exc.reason
    latency = int(round((clock() - started) * 1000))
    result['model'] = badge(config.model, 'live', latency_ms=latency, tokens=dict(tokens))
    result['receipt'] = {'provider': PROVIDER, 'model': config.model, 'model_version': version,
                         'tokens': dict(tokens), 'latency_ms': latency, 'calls': len(bodies),
                         'tool_calls': ledger.calls,
                         'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                         'request_digest': request_digest(bodies), 'permission_ref': PERMISSION_REF}
    return result, None


def badge(name, mode, latency_ms=None, tokens=None, recorded_at=None, fallback_reason=None):
    if mode == 'live':
        label = 'Gemini on Vertex AI, live'
    elif mode == 'recorded':
        label = f'Recorded Gemini run, {_date_words(recorded_at)}'
    else:
        label = 'Composed from the records. No model call.'
    return {'provider': PROVIDER, 'name': name, 'mode': mode, 'latency_ms': latency_ms, 'tokens': tokens,
            'recorded_at': recorded_at, 'fallback_reason': fallback_reason, 'label': label}


def _date_words(instant):
    try:
        d = datetime.fromisoformat(str(instant).replace('Z', '+00:00'))
    except ValueError:
        return 'date not recorded'
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}'


# ------------------------------------------------------------------------------- recorded runs

def recorded_name(prompt_id, at):
    return f"{prompt_id}@{at.replace(':', '')}.json"


def recorded_path(directory, prompt_id, at):
    from pathlib import Path
    name = recorded_name(prompt_id, at)
    return Path(directory) / 'desk' / 'recorded' / name if RECORDED_NAME.fullmatch(name) else None


def write_recorded(directory, prompt_id, at, result):
    path = recorded_path(directory, prompt_id, at)
    if path is None or result.get('model', {}).get('mode') != 'live':
        raise ValueError('only a checked live result is recorded')
    record = {'v': 1, 'prompt_id': prompt_id, 'at': at, 'receipt': result['receipt'],
              'answer': {k: v for k, v in result.items() if k != 'receipt'}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return path


def load_recorded(bake, prompt_id, at):
    """The recorded run for this prompt and clock as a served answer, or None (absent or not valid)."""
    if not prompt_id or not AT.fullmatch(at):
        return None
    path = recorded_path(bake.directory, prompt_id, at)
    if path is None:
        return None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if (type(record) is not dict or record.get('v') != 1 or record.get('prompt_id') != prompt_id
            or record.get('at') != at or type(record.get('answer')) is not dict or type(record.get('receipt')) is not dict):
        return None
    result, receipt = dict(record['answer']), record['receipt']
    if result.get('at') != at or not isinstance(receipt.get('run_at'), str):
        return None
    try:
        check(result)
    except (Invalid, KeyError, TypeError, AttributeError):
        return None
    for t in re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', json.dumps(result.get('citations'))):
        if t > at:
            return None
    tokens = receipt.get('tokens') if isinstance(receipt.get('tokens'), dict) else None
    result['model'] = badge(str(receipt.get('model') or ''), 'recorded', latency_ms=receipt.get('latency_ms'),
                            tokens=tokens, recorded_at=receipt['run_at'])
    result['basis'] = RECORDED_BASIS
    return result


__all__ = ['run', 'badge', 'check', 'load_recorded', 'write_recorded', 'recorded_path', 'TOOLS']
