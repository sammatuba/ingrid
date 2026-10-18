"""The store's queries, offline: one implementation in memory, one in sqlite.

Both backends hold the same rows — the shapes :mod:`~src.adapters.corpus.store.records`
builds — and answer the same questions, so the cutoff rule is proved by tests without a cloud
call. `scripts/corpus/bq/queries/` holds the same questions as BigQuery SQL; the sqlite
statements here are the same SQL in the dialect sqlite speaks, and both run against the same
columns, so a change to one that is not made to the other shows up as a back-end disagreement
in `tests/test_corpus_store.py`.

| Question | Method | BigQuery file |
|---|---|---|
| passages first available at or before a cutoff | `passages_at` | `passages_at_cutoff.sql` |
| the same, ranked by embedding distance | `vector_search` | `vector_search.sql` |
| what changed since a cutoff | `what_changed` | `what_changed.sql` |
| clauses in force at a cutoff, with the chain | `clauses_in_force`, `clauses_at_cutoff` | `clauses_in_force.sql` |
| which assumptions depend on a challenged input | `dependents` | `dependents_of_challenged.sql` |
| independent or copied sources | `independence` | `source_independence.sql` |

**The cutoff rule is not repeated here.** Every query compares the single column
``availability_until`` against the cutoff's end, and the row shapes carry the reason a version
was excluded. Retrieval returns candidates; it confers no acceptance, so every method that can
answer with a proposed row says so in the row's ``review_state``.

**A stored row is the store's.** Every write keeps its own copy of the row it validates —
nested values included, because a supplied ``availability_basis`` or ``corpus_record`` object
travels through normalization by reference — and every read hands out another one. A caller
that mutates the row it passed, or the row it was given back, changes nothing the store holds
or answers, and the two backends cannot drift apart over a value a caller changed.

**Embeddings.** `vector_search` ranks with cosine distance. BigQuery computes it with
``ML.DISTANCE(...)`` over the filtered rows; sqlite has no vector function, so the same cosine
is computed in Python over the rows its own SQL already filtered — the filter, which is the
part the cutoff rule governs, is SQL in both. :func:`hash_embedding` is the deterministic
stand-in the tests and any offline ranking use; it is a bag-of-words hash, not a semantic
model, and nothing may present it as one.
"""
from __future__ import annotations

import copy
import hashlib
import math
import json
import re
import sqlite3
import weakref
from dataclasses import dataclass

from . import records

#: The sqlite statements, one per question. ``{states}`` and ``{kinds}`` are filled from
#: validated tuples of names; nothing else in a statement is built at run time.
SQLITE_SQL = {
    "passages_at": """
        SELECT passage_id, source_id, source_version, issuer, page, start_offset, end_offset,
               quote, quote_digest, availability_until
          FROM passages
         WHERE availability_until IS NOT NULL
           AND availability_until <= :cutoff_until
           AND (:issuer IS NULL OR issuer = :issuer)
           AND (:contains IS NULL OR instr(quote, :contains) > 0)
         ORDER BY availability_until DESC, passage_id ASC
         LIMIT :limit
    """,
    "vector_candidates": """
        SELECT passage_id, source_id, source_version, issuer, page, start_offset, end_offset,
               quote, quote_digest, availability_until, embedding
          FROM passages
         WHERE availability_until IS NOT NULL
           AND availability_until <= :cutoff_until
           AND (:issuer IS NULL OR issuer = :issuer)
           AND embedding IS NOT NULL
    """,
    "clause_chain": """
        WITH RECURSIVE chain(version_id, replaces, depth) AS (
            SELECT version_id, replaces, 0
              FROM rule_versions
             WHERE clause_label = :label AND replaces IS NULL
            UNION ALL
            SELECT r.version_id, r.replaces, c.depth + 1
              FROM rule_versions r JOIN chain c ON r.replaces = c.version_id
        )
        SELECT c.version_id, c.replaces, c.depth,
               CASE
                   WHEN r.availability_until IS NULL THEN 'availability_unknown'
                   WHEN r.availability_from >= :cutoff_until THEN 'after_cutoff'
                   WHEN r.availability_until > :cutoff_until THEN 'availability_imprecise'
                   WHEN r.event_time_end IS NULL THEN 'effectivity_unknown'
                   WHEN r.event_time_start >= :cutoff_until THEN 'not_yet_effective'
                   WHEN r.event_time_end > :cutoff_until THEN 'effectivity_imprecise'
                   ELSE NULL
               END AS reason
          FROM chain c JOIN rule_versions r ON r.version_id = c.version_id
         ORDER BY c.depth
    """,
    "labels_at_cutoff": """
        WITH RECURSIVE placed(clause_label, version_id, replaces, depth) AS (
            SELECT clause_label, version_id, replaces, 0
              FROM rule_versions
             WHERE family = :family AND replaces IS NULL
               AND availability_until IS NOT NULL AND availability_until <= :cutoff_until
               AND event_time_end IS NOT NULL AND event_time_end <= :cutoff_until
            UNION ALL
            SELECT r.clause_label, r.version_id, r.replaces, p.depth + 1
              FROM rule_versions r JOIN placed p ON r.replaces = p.version_id
             WHERE r.availability_until IS NOT NULL AND r.availability_until <= :cutoff_until
               AND r.event_time_end IS NOT NULL AND r.event_time_end <= :cutoff_until
        )
        SELECT p.clause_label, p.version_id
          FROM placed p
         WHERE p.depth = (SELECT MAX(q.depth) FROM placed q WHERE q.clause_label = p.clause_label)
         ORDER BY p.clause_label
    """,
    "changed": """
        SELECT * FROM (
            SELECT 'claims' AS record_kind, claim_id || '@' || claim_revision AS ref,
                   availability_until, review_state, subject_ref || ' ' || predicate AS label
              FROM claims
             WHERE availability_until IS NOT NULL
               AND claim_revision = (SELECT MAX(head.claim_revision) FROM claims head
                                      WHERE head.claim_id = claims.claim_id
                                        AND head.availability_until <= :until_until)
            UNION ALL
            SELECT 'rule_versions', version_id, availability_until, review_state, clause_label
              FROM rule_versions
             WHERE availability_until IS NOT NULL
            UNION ALL
            SELECT 'relations', relation_id, availability_until, review_state, relation_kind
              FROM relations
             WHERE availability_until IS NOT NULL
            UNION ALL
            SELECT 'passages', passage_id, availability_until, review_state, passage_id
              FROM passages
             WHERE availability_until IS NOT NULL
            UNION ALL
            SELECT 'source_versions', source_id || '@' || source_version, availability_until,
                   review_state, issuer
              FROM source_versions
             WHERE availability_until IS NOT NULL
        )
         WHERE availability_until > :since_until AND availability_until <= :until_until
         ORDER BY availability_until DESC, record_kind, ref
    """,
    # ``{kinds}`` and ``{states}`` are the only built parts. Every parameter of these two
    # statements is positional, in the order it appears, so no statement mixes ``?`` with a
    # named binding.
    "dependents": """
        WITH RECURSIVE walk(ref, ref_type, depth, path, relation_id) AS (
            SELECT ?, ?, 0, ',' || ? || ',', NULL
            UNION ALL
            SELECT r.from_ref, r.from_type, w.depth + 1, w.path || r.from_ref || ',',
                   r.relation_id
              FROM walk w JOIN relations r ON r.to_ref = w.ref
             WHERE r.relation_kind IN ({kinds})
               AND r.review_state IN ({states})
               AND r.availability_until IS NOT NULL
               AND r.availability_until <= ?
               AND w.depth < ?
               AND instr(w.path, ',' || r.from_ref || ',') = 0
        )
        SELECT ref, ref_type, depth, relation_id FROM walk WHERE depth > 0 ORDER BY depth, ref
    """,
    "lineage_up": """
        WITH RECURSIVE up(ref, depth, path) AS (
            SELECT ?, 0, ',' || ? || ','
            UNION ALL
            SELECT r.to_ref, u.depth + 1, u.path || r.to_ref || ','
              FROM up u JOIN relations r ON r.from_ref = u.ref
             WHERE r.relation_kind IN ({kinds})
               AND u.depth < ?
               AND instr(u.path, ',' || r.to_ref || ',') = 0
        )
        SELECT ref, MAX(depth) AS depth FROM up GROUP BY ref
         ORDER BY MAX(depth) DESC, ref ASC LIMIT 1
    """,
}

#: The keys each table is identified by, from the record shapes; a repeated key never
#: overwrites a row.
KEYS = records.KEYS

_LIST_COLUMNS = ("passage_id", "source_id", "source_version", "issuer", "page", "start_offset",
                 "end_offset", "quote", "quote_digest", "availability_until")

#: The passage columns its source version owns. ``records.passage_row`` derives every one of
#: them from the version the passage belongs to, so a passage that arrives stating its own
#: availability, issuer or publication is refused rather than stored: a caller-supplied date
#: must never decide when a document may be read.
_SOURCE_OWNED = ("issuer", "availability_value", "availability_precision", "availability_from",
                 "availability_until", "availability_basis", "published_value",
                 "published_precision", "published_on", "published_at", "synthetic",
                 "permission_ref")


class StoreError(ValueError):
    """A refused write or query. The code is stable; the detail names the cause."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


@dataclass(frozen=True)
class Cutoff:
    """A cutoff as a supplied value and its precision; ``until`` is the exclusive end.

    The instant-or-date arithmetic is :func:`records.cutoff_interval`, the one derivation the
    rest of the store uses; a cutoff is never the system clock.
    """

    value: str
    precision: str

    def __post_init__(self):
        start, end = records.cutoff_interval(self.value, self.precision)
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "until", end)

    def label(self):
        return "%s (%s)" % (self.value, self.precision)


def hash_embedding(text, dimension=64):
    """A deterministic bag-of-words embedding, for tests and offline ranking only.

    Each lower-cased word votes for one bucket of ``dimension``, the vector is L2-normalised,
    and the same text always gives the same vector. This is **not** a semantic model: it knows
    nothing about meaning, and no claim about retrieval quality may rest on it. A real run
    supplies vectors from the embedding model the register names, through
    ``load.py --embeddings``.
    """
    if dimension < 1:
        raise StoreError("INVALID_DIMENSION", "dimension must be positive")
    vector = [0.0] * dimension
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        bucket = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16) % dimension
        vector[bucket] += 1.0
    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        return vector
    return [component / norm for component in vector]


def cosine_distance(left, right):
    """``1 - cos`` between two vectors of one length; both must be non-zero."""
    if len(left) != len(right):
        raise StoreError("EMBEDDING_DIMENSION_MISMATCH",
                         "query vector has %d components, the rows have %d" % (len(left), len(right)))
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise StoreError("ZERO_VECTOR", "cosine distance is undefined for a zero vector")
    return 1.0 - dot / (left_norm * right_norm)


def _states(states):
    if not states or any(state not in records.REVIEW_STATES for state in states):
        raise StoreError("INVALID_REVIEW_STATE", "unknown review state in %r" % (tuple(states),))
    return tuple(states)


def _kinds(kinds):
    if not kinds or any(kind not in records.RELATION_KINDS for kind in kinds):
        raise StoreError("UNKNOWN_RELATION", "unknown relation kind in %r" % (tuple(kinds),))
    return tuple(kinds)


class _Base:
    """The writes and the shared query semantics; the two backends differ in storage only."""

    def __init__(self):
        self._rows = {table: [] for table in records.TABLES}
        self._keys = {table: {} for table in records.TABLES}
        self._embedding_dimension = None

    # -- writes ------------------------------------------------------------------
    def key_of(self, table, row):
        return tuple(row[name] for name in KEYS[table])

    def add(self, table, row):
        """One validated row; an identical re-add is idempotent, a conflicting one refused.

        The store keeps **its own copy**, nested values included, and hands back another: a
        caller that goes on holding the row it passed, or the row this returns, must not be
        able to change what the store holds or answers. ``records.normalize`` builds a fresh
        mapping but carries some of its values through by reference — a supplied
        ``availability_basis`` object, an acquisition's ``corpus_record`` — so a shallow
        handover would leave the stored row reachable from outside the store.
        """
        if table not in records.TABLES:
            raise StoreError("UNKNOWN_TABLE", "no table named %r" % (table,))
        normalized = copy.deepcopy(records.normalize(table, row))
        if table == "passages":
            self._check_embedding(normalized)
            self._check_passage(normalized)
        if table == "claims":
            self._check_claim(normalized)
        key = self.key_of(table, normalized)
        held = self._keys[table].get(key)
        if held is not None:
            if held == normalized:
                return copy.deepcopy(held)
            raise StoreError("ROW_CONFLICT",
                             "%s key %s is already held with different content"
                             % (table, "/".join(str(part) for part in key)))
        self._keys[table][key] = normalized
        self._rows[table].append(normalized)
        self._write(table, normalized)
        return copy.deepcopy(normalized)

    def extend(self, table, rows):
        """Every row, or the refusal naming the first row that fails; the rest are not added."""
        added = []
        for row in rows:
            added.append(self.add(table, row))
        return added

    def _check_embedding(self, row):
        embedding = row.get("embedding")
        if embedding is None:
            if row.get("embedding_model") is not None:
                raise StoreError("INVALID_EMBEDDING", "an embedding_model without an embedding")
            return
        if row.get("embedding_model") is None:
            raise StoreError("INVALID_EMBEDDING",
                             "an embedding is recorded with the model that produced it")
        if self._embedding_dimension is None:
            self._embedding_dimension = len(embedding)
        elif len(embedding) != self._embedding_dimension:
            raise StoreError("EMBEDDING_DIMENSION_MISMATCH",
                             "an embedding of %d components arrives where the store holds %d"
                             % (len(embedding), self._embedding_dimension))

    def _check_passage(self, row):
        """A passage is its source version's, and the store refuses one that says otherwise.

        The version must be held here and ``compilable``, and the issuer, the availability
        interval and the publication the row carries must be the version's own values — the
        ones ``records.passage_row`` derives. Without this, a row written by hand could
        supply its own first availability and be retrieved at a cutoff its document was not
        available at, which is the one thing the cutoff rule exists to prevent.
        """
        source = self.rows_one("source_versions", ("source_id", "source_version"),
                               (row["source_id"], row["source_version"]))
        if source is None:
            raise StoreError("UNKNOWN_SOURCE",
                             "passage %s names source %s %s, which this store does not hold"
                             % (row["passage_id"], row["source_id"], row["source_version"]))
        if source["state"] != "compilable":
            raise StoreError("SOURCE_EXCLUDED",
                             "%s %s is excluded from every cutoff: %s"
                             % (source["source_id"], source["source_version"],
                                source["availability_unknown_reason"]))
        for name in _SOURCE_OWNED:
            if row.get(name) != source.get(name):
                raise StoreError("SOURCE_MISMATCH",
                                 "passage %s states %s %r where its source version %s %s "
                                 "states %r" % (row["passage_id"], name, row.get(name),
                                                row["source_id"], row["source_version"],
                                                source.get(name)))

    def _verify_chains(self):
        """A rule-version lineage is linear and complete, or the store says why it is not.

        Every ``replaces`` must resolve inside the store, no version may be replaced by two,
        and no chain may cycle: each of the three would make "the version in force" ambiguous,
        and an ambiguous answer is refused rather than picked from. Both backends call this, so
        the SQL walk and the Python walk fail on the same data.
        """
        by_id, children = {}, {}
        for row in self._rows["rule_versions"]:
            by_id[row["version_id"]] = row
        for row in self._rows["rule_versions"]:
            if row["replaces"] is None:
                continue
            if row["replaces"] not in by_id:
                raise StoreError("UNRESOLVED_REPLACEMENT",
                                 "version %s replaces %s, which the store does not hold"
                                 % (row["version_id"], row["replaces"]))
            children.setdefault(row["replaces"], []).append(row["version_id"])
        for parent, replaced_by in children.items():
            if len(replaced_by) > 1:
                raise StoreError("CHAIN_BRANCH",
                                 "version %s is replaced by %d versions; a chain is linear"
                                 % (parent, len(replaced_by)))
        for row in self._rows["rule_versions"]:
            seen, current = set(), row
            while current is not None and current["version_id"] not in seen:
                seen.add(current["version_id"])
                current = by_id.get(current["replaces"])
            if current is not None:
                raise StoreError("CHAIN_CYCLE",
                                 "the chain through %s is not a chain" % row["version_id"])

    def _check_claim(self, row):
        """A claim's citation must resolve in this store; nothing is repaired or guessed.

        Two things a claim may not say about itself. Its citation names **one** document
        version: the passage it quotes and the source it names must be that version's, so a
        claim cannot quote one record's text under another record's identity. And the claim is
        **no earlier than its evidence**, at either end of its availability interval: an
        interval starting or ending before the document it rests on is not a claim about that
        document, and it would answer a cutoff at which nothing carrying it could be read — the
        one thing the cutoff rule exists to prevent. An unknown claim availability is left
        alone, because it places the claim at no cutoff.
        """
        evidence = None
        if row.get("passage_id") is not None:
            passage = self.rows_one("passages", ("passage_id",), (row["passage_id"],))
            if passage is None:
                raise StoreError("UNKNOWN_PASSAGE",
                                 "claim %s cites passage %s, which this store does not hold"
                                 % (row["claim_id"], row["passage_id"]))
            if row.get("quote_digest") is not None and row["quote_digest"] != passage["quote_digest"]:
                raise StoreError("CITATION_MISMATCH",
                                 "claim %s cites passage %s with another quote"
                                 % (row["claim_id"], row["passage_id"]))
            if (passage["source_id"], passage["source_version"]) != (row["source_id"],
                                                                     row["source_version"]):
                raise StoreError("CITATION_MISMATCH",
                                 "claim %s names source %s %s but cites passage %s of %s %s; a "
                                 "claim and its citation name one document version"
                                 % (row["claim_id"], row["source_id"], row["source_version"],
                                    passage["passage_id"], passage["source_id"],
                                    passage["source_version"]))
            evidence = passage
        source = self.rows_one("source_versions", ("source_id", "source_version"),
                               (row["source_id"], row["source_version"]))
        if source is None:
            raise StoreError("UNKNOWN_SOURCE",
                             "claim %s names source %s %s, which this store does not hold"
                             % (row["claim_id"], row["source_id"], row["source_version"]))
        self._check_claim_availability(row, source if evidence is None else evidence)

    def _check_claim_availability(self, row, evidence):
        """A claim is never first available before the evidence that carries it.

        The claim's first availability is a supplied record of when the claim could be known;
        the evidence's is a record of when its document could be read. Both ends of the two
        intervals are compared, because the cutoff compares the end: the claim's interval must
        start no earlier than its evidence's — a claim is not known before the document it
        rests on — and must end no earlier either. The end is the column every cutoff query
        compares, so a claim whose interval ends before its evidence's would answer a cutoff
        that excludes the evidence; a finer precision on the claim is what lets the two starts
        agree while its interval ends first. An evidence row with no availability places
        nothing, so a claim that states an availability over it is refused as excluded rather
        than stored.
        """
        if row["availability_until"] is None:
            return
        if evidence["availability_until"] is None:
            raise StoreError("SOURCE_EXCLUDED",
                             "claim %s states a first availability but cites %s %s, which is "
                             "excluded from every cutoff: %s"
                             % (row["claim_id"], evidence["source_id"],
                                evidence["source_version"],
                                evidence.get("availability_unknown_reason",
                                             "no first availability is recorded")))
        if row["availability_from"] < evidence["availability_from"]:
            raise StoreError("AVAILABILITY_BEFORE_EVIDENCE",
                             "claim %s is first available %s but the evidence it cites (%s) is "
                             "first available %s; a claim is known no earlier than the "
                             "document it rests on"
                             % (row["claim_id"], row["availability_from"],
                                evidence.get("passage_id", evidence["source_id"]),
                                evidence["availability_from"]))
        if row["availability_until"] < evidence["availability_until"]:
            raise StoreError("AVAILABILITY_BEFORE_EVIDENCE",
                             "claim %s is placed at a cutoff ending %s but the evidence it "
                             "cites (%s) is placed only from %s; a claim may not become "
                             "cutoff-admissible before the document it rests on"
                             % (row["claim_id"], row["availability_until"],
                                evidence.get("passage_id", evidence["source_id"]),
                                evidence["availability_until"]))

    # -- reads -------------------------------------------------------------------
    # Every read hands out a copy, nested values included. The rows a caller receives are
    # information about the store, never a handle on it: without this, changing a value in a
    # row ``rows`` returned changed what the store answered, and the two backends stopped
    # agreeing, because the memory backend answers from the very objects it hands out.
    def rows(self, table):
        if table not in records.TABLES:
            raise StoreError("UNKNOWN_TABLE", "no table named %r" % (table,))
        return copy.deepcopy(self._rows[table])

    def rows_one(self, table, names, values):
        for row in self._rows[table]:
            if tuple(row.get(name) for name in names) == tuple(values):
                return copy.deepcopy(row)
        return None

    def count(self, table):
        return len(self._rows[table])

    def source_of(self, source_id, source_version):
        return self.rows_one("source_versions", ("source_id", "source_version"),
                             (source_id, source_version))

    def passage(self, passage_id):
        return self.rows_one("passages", ("passage_id",), (passage_id,))

    def entity(self, entity_id):
        return self.rows_one("entities", ("entity_id",), (entity_id,))

    def entities_of(self, entity_type=None):
        rows = [copy.deepcopy(row) for row in self._rows["entities"]
                if entity_type is None or row["entity_type"] == entity_type]
        return sorted(rows, key=lambda row: row["entity_id"])

    # -- the questions -----------------------------------------------------------
    def passages_at(self, cutoff, issuer=None, contains=None, limit=None):
        """Passages first available at or before the cutoff, freshest first."""
        return self._passages(cutoff, issuer, contains, limit)

    def vector_search(self, query_embedding, cutoff, issuer=None, top_k=10):
        """The nearest passages by cosine distance among those placed at the cutoff."""
        candidates = self._vector_candidates(cutoff, issuer)
        if not candidates:
            return []
        for candidate in candidates:
            if len(candidate["embedding"]) != len(query_embedding):
                raise StoreError("EMBEDDING_DIMENSION_MISMATCH",
                                 "query vector has %d components, the rows have %d"
                                 % (len(query_embedding), len(candidate["embedding"])))
        ranked = [(cosine_distance(query_embedding, row["embedding"]), row) for row in candidates]
        ranked.sort(key=lambda item: (item[0], item[1]["passage_id"]))
        return [dict({key: row[key] for key in _LIST_COLUMNS}, distance=distance)
                for distance, row in ranked[:top_k]]

    def clauses_in_force(self, clause_label, cutoff):
        """The version in force at a cutoff, its placed chain, and every exclusion.

        A label the store does not hold answers with no version and an empty chain: absence is
        reported as absence, never as "nothing changed", and the caller that needs to know which
        of the two it is reads the chain.
        """
        return self._clauses(clause_label, cutoff)

    def clauses_at_cutoff(self, family, cutoff):
        """Every clause of one family with a version placed at the cutoff.

        A label whose chain the cutoff cannot place is absent: an answer that is missing a
        clause is the honest one, and the exclusion reasons live in :meth:`clauses_in_force`.
        """
        return self._clauses_at(family, cutoff)

    def what_changed(self, since, until):
        """Rows first available after ``since`` and at or before ``until`` (head claims only).

        A claim that was revised returns its head revision at ``until``; the superseded
        revision stays in the store and is reachable by its own key, as the profile requires.
        """
        return self._changed(since, until)

    def dependents(self, ref, cutoff, kinds=("dependsOn", "usesAssumption"),
                   review_states=("accepted",), budget=8):
        """The records that depend on one input, transitively, with the traversal budget.

        The walk follows ``dependsOn`` and ``usesAssumption`` edges backwards from the input;
        every edge must be placed at the cutoff and in an allowed review state. ``truncated``
        is true when the walk stopped at the budget, so a capped answer is never presented as
        complete.
        """
        kinds, states = _kinds(kinds), _states(review_states)
        reached = self._dependents(ref, cutoff, kinds, states, budget)
        truncated = self._walk_hit_budget(ref, cutoff, kinds, states, budget)
        return {"ref": ref, "rows": reached, "truncated": truncated, "budget": budget}

    def independence(self, refs, kinds=("copiedFrom", "derivedFrom"), budget=8):
        """Group references by the origin their declared lineage reaches.

        Two references in one group are not independent corroboration. This verifies declared
        lineage only: it does not detect undeclared copying, and it makes no claim about a
        reference with no lineage record, which is its own group.
        """
        kinds = _kinds(kinds)
        refs = list(refs)
        groups = {}
        for ref in refs:
            groups.setdefault(self._lineage_root(ref, kinds, budget), []).append(ref)
        ordered = [{"root": root, "refs": sorted(members)}
                   for root, members in sorted(groups.items())]
        return {"groups": ordered, "independent": len(ordered), "refs": len(refs)}


class MemoryStore(_Base):
    """The store held in Python lists; the semantics are the reference for the sqlite one."""

    backend = "memory"

    def _write(self, table, row):
        return None

    def _passages(self, cutoff, issuer, contains, limit):
        rows = [row for row in self._rows["passages"]
                if records.known_by(row, cutoff.until)
                and (issuer is None or row["issuer"] == issuer)
                and (contains is None or contains in row["quote"])]
        # Two stable sorts: passage id ascending, then availability descending, which is the
        # statement's ``ORDER BY availability_until DESC, passage_id ASC``.
        rows.sort(key=_list_sort_key)
        rows.sort(key=lambda row: row["availability_until"], reverse=True)
        limited = rows if limit is None else rows[:limit]
        return [{key: row[key] for key in _LIST_COLUMNS} for row in limited]

    def _vector_candidates(self, cutoff, issuer):
        rows = [row for row in self._rows["passages"]
                if records.known_by(row, cutoff.until)
                and (issuer is None or row["issuer"] == issuer)
                and row.get("embedding") is not None]
        return sorted(rows, key=lambda row: row["passage_id"])

    def _clauses(self, clause_label, cutoff):
        chain = self._chains().get(clause_label, [])
        admitted, excluded = [], []
        for row in chain:
            reason = _placement_reason(row, cutoff.until)
            if reason is None and excluded:
                reason = "ancestor_not_in_force"
            if reason is None:
                admitted.append(row)
            else:
                excluded.append({"version_id": row["version_id"], "reason": reason})
        head = admitted[-1] if admitted else None
        return {"clause_label": clause_label, "cutoff": cutoff.label(),
                "version_id": None if head is None else head["version_id"],
                "chain": [row["version_id"] for row in admitted],
                "excluded": list(reversed(excluded))}

    def _clauses_at(self, family, cutoff):
        placed = []
        for label, chain in sorted(self._chains().items()):
            admitted = None
            for row in chain:
                if row["family"] != family or _placement_reason(row, cutoff.until) is not None:
                    break  # the chain is a placed prefix: the first refusal ends it
                admitted = row
            if admitted is not None:
                placed.append({"clause_label": label, "version_id": admitted["version_id"]})
        return placed

    def _changed(self, since, until):
        rows = []
        for table in records.TABLES:
            for row in self._rows[table]:
                if row.get("availability_until") is None:
                    continue
                if not (since.until < row["availability_until"] <= until.until):
                    continue
                if table == "claims" and not _is_head_claim(self._rows["claims"], row, until.until):
                    continue
                rows.append(_change_entry(table, row))
        # The statement's ``ORDER BY availability_until DESC, record_kind, ref``: two stable
        # sorts, because a later key can always be negated but a string cannot.
        rows.sort(key=lambda entry: (entry["record_kind"], entry["ref"]))
        rows.sort(key=lambda entry: entry["availability_until"], reverse=True)
        return rows

    def _dependents(self, ref, cutoff, kinds, states, budget):
        frontier = [(ref, ref, 0)]
        seen = {ref}
        out = []
        while frontier:
            current, current_type, depth = frontier.pop(0)
            if depth >= budget:
                continue
            for row in self._rows["relations"]:
                if row["relation_kind"] not in kinds or row["to_ref"] != current:
                    continue
                if row["review_state"] not in states:
                    continue
                if not records.known_by(row, cutoff.until):
                    continue
                if row["from_ref"] in seen:
                    continue
                seen.add(row["from_ref"])
                out.append({"ref": row["from_ref"], "ref_type": row["from_type"],
                            "depth": depth + 1, "relation_id": row["relation_id"]})
                frontier.append((row["from_ref"], row["from_type"], depth + 1))
        out.sort(key=lambda entry: (entry["depth"], entry["ref"]))
        return out

    def _walk_hit_budget(self, ref, cutoff, kinds, states, budget):
        """Whether any allowed edge starts a step the budget refuses to take."""
        reached = {entry["ref"] for entry in self._dependents(ref, cutoff, kinds, states, budget)}
        reached.add(ref)
        for row in self._rows["relations"]:
            if row["relation_kind"] in kinds and row["review_state"] in states \
                    and row["to_ref"] in reached and records.known_by(row, cutoff.until):
                if row["from_ref"] not in reached:
                    return True
        return False

    def _lineage_root(self, ref, kinds, budget):
        """The deepest reference the declared lineage reaches, ties taken by the smallest id.

        The same rule the sqlite statement states (``ORDER BY MAX(depth) DESC, ref ASC LIMIT
        1``), so the backends cannot disagree about an origin even when a reference was copied
        from more than one place.
        """
        reached, frontier = {}, [(ref, 0, (ref,))]
        while frontier:
            current, depth, path = frontier.pop()
            if reached.get(current, -1) >= depth:
                continue
            reached[current] = depth
            if depth >= budget:
                continue
            for row in self._rows["relations"]:
                if row["relation_kind"] in kinds and row["from_ref"] == current \
                        and row["to_ref"] not in path:
                    frontier.append((row["to_ref"], depth + 1, path + (row["to_ref"],)))
        return min(reached.items(), key=lambda item: (-item[1], item[0]))[0]

    def _chains(self):
        """The rule-version chains, ordered by the supplied ``replaces`` links only."""
        self._verify_chains()
        children = {}
        for row in self._rows["rule_versions"]:
            if row["replaces"] is not None:
                children.setdefault(row["replaces"], row)
        chains = {}
        for head in [row for row in self._rows["rule_versions"] if row["replaces"] is None]:
            chain, current = [], head
            while current is not None:
                chain.append(current)
                current = children.get(current["version_id"])
            chains[head["clause_label"]] = chain
        return chains


def _list_sort_key(row):
    return row["passage_id"]


def _placement_reason(row, cutoff_until):
    return records.availability_reason(row, cutoff_until) or records.effectivity_reason(row, cutoff_until)


def _is_head_claim(claims, row, cutoff_until):
    heads = [item["claim_revision"] for item in claims
             if item["claim_id"] == row["claim_id"] and records.known_by(item, cutoff_until)]
    return bool(heads) and row["claim_revision"] == max(heads)


def _change_entry(table, row):
    if table == "claims":
        return {"record_kind": "claims", "ref": "%s@%s" % (row["claim_id"], row["claim_revision"]),
                "availability_until": row["availability_until"], "review_state": row["review_state"],
                "label": "%s %s" % (row["subject_ref"], row["predicate"])}
    if table == "rule_versions":
        return {"record_kind": "rule_versions", "ref": row["version_id"],
                "availability_until": row["availability_until"], "review_state": row["review_state"],
                "label": row["clause_label"]}
    if table == "relations":
        return {"record_kind": "relations", "ref": row["relation_id"],
                "availability_until": row["availability_until"], "review_state": row["review_state"],
                "label": row["relation_kind"]}
    if table == "passages":
        return {"record_kind": "passages", "ref": row["passage_id"],
                "availability_until": row["availability_until"], "review_state": row["review_state"],
                "label": row["passage_id"]}
    if table == "source_versions":
        return {"record_kind": "source_versions",
                "ref": "%s@%s" % (row["source_id"], row["source_version"]),
                "availability_until": row["availability_until"], "review_state": row["review_state"],
                "label": row["issuer"]}
    return {"record_kind": table, "ref": row.get("entity_id"),
            "availability_until": row["availability_until"], "review_state": row["review_state"],
            "label": row.get("label")}


class SqliteStore(_Base):
    """The same rows in sqlite; every question is a statement, not a Python loop."""

    backend = "sqlite"

    def __init__(self, path=":memory:"):
        super().__init__()
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        # Closed when the store is collected as well as by ``close``, so a test that drops one
        # does not leave a handle behind; ``finalize`` never keeps the store alive.
        self._finalizer = weakref.finalize(self, self._db.close)
        self._create()

    def close(self):
        self._finalizer()
        self._db.close()

    def _create(self):
        from . import schema
        for table in records.TABLES:
            self._db.execute(schema.sqlite_create(table))
        self._db.commit()

    def _write(self, table, row):
        from . import schema
        names = schema.sqlite_columns(table)
        self._db.execute(
            "INSERT INTO %s (%s) VALUES (%s)" % (table, ", ".join(names),
                                                ", ".join("?" for _ in names)),
            [_sqlite_value(row.get(name)) for name in names])
        self._db.commit()

    def _statement(self, name, **values):
        return SQLITE_SQL[name].format(
            kinds=", ".join("?" for _ in values.get("kinds", ())),
            states=", ".join("?" for _ in values.get("states", ())))

    def _passages(self, cutoff, issuer, contains, limit):
        # sqlite reads ``LIMIT -1`` as no limit; a NULL limit is a datatype error there, where
        # BigQuery wants an integer parameter. Both spell "every row" for the caller.
        cursor = self._db.execute(SQLITE_SQL["passages_at"], {
            "cutoff_until": cutoff.until, "issuer": issuer, "contains": contains,
            "limit": -1 if limit is None else limit})
        return [{key: row[key] for key in _LIST_COLUMNS} for row in cursor.fetchall()]

    def _vector_candidates(self, cutoff, issuer):
        cursor = self._db.execute(SQLITE_SQL["vector_candidates"],
                                  {"cutoff_until": cutoff.until, "issuer": issuer})
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            item["embedding"] = json.loads(item["embedding"])
            rows.append(item)
        return rows

    def _clauses(self, clause_label, cutoff):
        self._verify_chains()
        cursor = self._db.execute(SQLITE_SQL["clause_chain"],
                                  {"label": clause_label, "cutoff_until": cutoff.until})
        admitted, excluded = [], []
        for row in cursor.fetchall():
            reason = row["reason"]
            if reason is None and excluded:
                reason = "ancestor_not_in_force"
            if reason is None:
                admitted.append(row["version_id"])
            else:
                excluded.append({"version_id": row["version_id"], "reason": reason})
        return {"clause_label": clause_label, "cutoff": cutoff.label(),
                "version_id": admitted[-1] if admitted else None, "chain": admitted,
                "excluded": list(reversed(excluded))}

    def _clauses_at(self, family, cutoff):
        self._verify_chains()
        cursor = self._db.execute(SQLITE_SQL["labels_at_cutoff"],
                                  {"family": family, "cutoff_until": cutoff.until})
        placed = {}
        for row in cursor.fetchall():
            placed.setdefault(row["clause_label"], row["version_id"])
        return [{"clause_label": label, "version_id": placed[label]} for label in sorted(placed)]

    def _changed(self, since, until):
        cursor = self._db.execute(SQLITE_SQL["changed"],
                                  {"since_until": since.until, "until_until": until.until})
        return [dict(row) for row in cursor.fetchall()]

    def _dependents(self, ref, cutoff, kinds, states, budget):
        statement = self._statement("dependents", kinds=kinds, states=states)
        cursor = self._db.execute(statement, (ref, ref, ref, *kinds, *states,
                                              cutoff.until, budget))
        return [{"ref": row["ref"], "ref_type": row["ref_type"], "depth": row["depth"],
                 "relation_id": row["relation_id"]} for row in cursor.fetchall()]

    def _walk_hit_budget(self, ref, cutoff, kinds, states, budget):
        reached = {entry["ref"] for entry in
                   self._dependents(ref, cutoff, kinds, states, budget)}
        reached.add(ref)
        placeholders = ", ".join("?" for _ in reached)
        cursor = self._db.execute(
            "SELECT from_ref, to_ref FROM relations WHERE relation_kind IN (%s) "
            "AND review_state IN (%s) AND availability_until IS NOT NULL "
            "AND availability_until <= ?"
            % (", ".join("?" for _ in kinds), ", ".join("?" for _ in states)),
            (*kinds, *states, cutoff.until))
        for row in cursor.fetchall():
            if row["to_ref"] in reached and row["from_ref"] not in reached:
                return True
        return False

    def _lineage_root(self, ref, kinds, budget):
        statement = self._statement("lineage_up", kinds=kinds)
        rows = self._db.execute(statement, (ref, ref, *kinds, budget)).fetchall()
        return rows[0]["ref"] if rows else ref

    def _chains(self):
        raise StoreError("UNSUPPORTED",
                         "the sqlite backend answers the clause questions in SQL; use "
                         "clauses_in_force or clauses_at_cutoff")


def _sqlite_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def load(store, tables):
    """Add every row of a ``{table: [row, ...]}`` mapping, in table order."""
    for table in records.TABLES:
        for row in tables.get(table, ()):
            store.add(table, row)
    return store


def open_store(backend="memory", **kwargs):
    """The store for a backend name: ``memory`` (the default) or ``sqlite``."""
    if backend == "memory":
        return MemoryStore()
    if backend == "sqlite":
        path = kwargs.get("path", ":memory:")
        sqlite_store = SqliteStore(path)
        for table in records.TABLES:
            for row in kwargs.get("rows", {}).get(table, ()):
                sqlite_store.add(table, row)
        return sqlite_store
    raise StoreError("UNKNOWN_BACKEND", "no backend named %r" % (backend,))


__all__ = ["Cutoff", "KEYS", "MemoryStore", "SQLITE_SQL", "SqliteStore", "StoreError",
           "cosine_distance", "hash_embedding", "load", "open_store"]
