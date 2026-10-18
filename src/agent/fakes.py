"""Labelled fakes for the records the dock reads before the teammate's lanes land them.

Contract section 5 and strategy section 6: two synthetic cases (the synthetic unit trip and an empty
case) until CASE C1 and C2; a two-claim chain until CASE C3; the EVIDENCE search receipt, by name,
until EVIDENCE V1; a model card dictionary with the models page's fields until MODELS X1; and the
book adapter until BOOK-2. Every fake carries `synthetic: true` and a `label` the dock shows.

No fake carries a figure: a field that a real record will fill with a number is `None` here, with
the label saying which lane fills it, so nothing on a page can read a fake as a measurement.
"""
import copy
import hashlib

LABEL_PREFIX = 'Synthetic fake'


def _label(what, lane):
    return f'{LABEL_PREFIX}. {what[0].upper()}{what[1:]}. The {lane} replaces it with its own record.'


FAKE_CASES = (
    {'case_id': 'case-syn-unit-trip', 'title': 'Synthetic unit trip', 'state': 'open',
     'event_id': 'syn-bay-unit-2-trip', 'opened_at': '2026-10-18T00:00:00Z', 'claim_chain_id': 'chain-syn-unit-trip',
     'synthetic': True, 'label': _label('an invented case around the synthetic unit trip', 'case lane')},
    {'case_id': 'case-syn-empty', 'title': 'Empty synthetic case', 'state': 'open', 'event_id': None,
     'opened_at': '2026-10-18T00:00:00Z', 'claim_chain_id': None,
     'synthetic': True, 'label': _label('an invented case with no records yet', 'case lane')},
)

FAKE_CLAIM_CHAIN = {
    'chain_id': 'chain-syn-unit-trip', 'case_id': 'case-syn-unit-trip',
    'claims': [
        {'claim_id': 'claim-syn-1', 'position': 1, 'statement_key': 'unit_tripped',
         'source_ref': 'syn-bay-unit-2-trip', 'reviewed': False, 'synthetic': True,
         'label': _label('an invented claim that the unit tripped', 'case lane')},
        {'claim_id': 'claim-syn-2', 'position': 2, 'statement_key': 'capacity_belief_touched',
         'source_ref': 'claim-syn-1', 'reviewed': False, 'synthetic': True,
         'label': _label('an invented claim that the trip touches the capacity belief', 'case lane')},
    ],
    'synthetic': True, 'label': _label('an invented chain of two claims', 'case lane'),
}

MODEL_CARD = {
    'card_id': 'card-syn-availability-term', 'name': 'Availability term (fake card)',
    'status_word': 'Not built', 'status_line': 'This card is a placeholder. The models lane fills it.',
    'method': None, 'inputs': [], 'basis': None,
    'figures': [{'label': 'sample size', 'value': None, 'as_of': None, 'record_id': None}],
    'as_of': None, 'synthetic': True, 'label': _label('a model card with the models page fields', 'models lane'),
}


def fake_search_receipt(question_id, cutoff):
    """The EVIDENCE search receipt fake (strategy: query, time, engine id, result list, bytes, cost)."""
    key = hashlib.sha256(f'fake-search|{question_id}|{cutoff}'.encode('utf-8')).hexdigest()[:32]
    return {'receipt_id': 'search-' + key, 'question_id': question_id, 'cutoff': cutoff,
            'engine_id': 'fake-engine', 'results': [{'url': 'https://example.invalid/fake-source',
                                                       'title': 'Fake source page', 'tier': None}],
            'bytes': None, 'cost_usd': None, 'synthetic': True,
            'label': _label('no search was run and this receipt is invented', 'evidence lane')}


class FakeSearch:
    """The `search` adapter the service calls: `search(question_id, cutoff) -> receipt`."""
    synthetic = True
    label = _label('the search adapter', 'evidence lane')

    def search(self, question_id, cutoff):
        return fake_search_receipt(question_id, cutoff)


class FakeBook:
    """The `book` adapter the two queries call until BOOK-2: rows named, figures left empty."""
    synthetic = True
    label = _label('the synthetic book queries', 'book lane')

    def exposure(self, account_ids, node_ids, window, cutoff):
        return {'record_id': 'exposure-fake', 'rows': [
            {'account_id': a, 'node_id': n, 'window': window, 'uncovered_mwh': None}
            for a in account_ids for n in node_ids], 'cutoff': cutoff, 'synthetic': True, 'label': self.label}

    def impact(self, account_ids, outlook_id, window=None, cutoff=None):
        # BOOK-4's call shape: the window and the cutoff travel with the vintage id.
        return {'record_id': 'impact-fake', 'outlook_id': outlook_id, 'window': window, 'cutoff': cutoff,
                'materiality': None,
                'rows': [{'account_id': a, 'band_php': None} for a in account_ids],
                'synthetic': True, 'label': self.label}


def open_cases(owner=None):
    """The open-cases list the dock shows (every owner sees the same two fakes)."""
    return [copy.deepcopy(c) for c in FAKE_CASES if c['state'] == 'open']


#: Every fake by name, so another module (and the EVIDENCE contract's readers) can ask for one.
FAKES = {
    'cases': FAKE_CASES,
    'claim_chain': FAKE_CLAIM_CHAIN,
    'model_card': MODEL_CARD,
    'search_receipt': fake_search_receipt('fake-question', '2026-10-14T23:59:59+08:00'),
    'search': FakeSearch,
    'book': FakeBook,
}


def fake(name):
    """One fake by name (a copy for records; the class itself for adapters)."""
    value = FAKES[name]
    return value if isinstance(value, type) else copy.deepcopy(value)
